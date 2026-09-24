"""EB1b focused tests: supervision, the restart cap, reconciliation, pause/resume, the
verifier's ``server.lifecycle`` check and the results builder's reportability label.

Repair contract EB1 (session 60, after root's 20:40 NO-GO,
``reviews/prerun_bundle_go_nogo_20260923_2040.md`` items 1 and 4).  Every check below has a
NEGATIVE CONTROL beside it -- the same code on an input it must treat differently, asserted to
be treated differently -- so no check here can pass by being unable to fail.

What runs, and what does not:

* ``lab_server`` is replaced IN PROCESS by :class:`FakeServers` (start, restart, stop,
  exit_status, health, metrics, orphan_server): each "process" is a dict, nothing is launched,
  nothing listens.  The subprocess controls of ``lab_orchestrator.main`` are repair step EB1c.
  The one exception is :class:`OrphanProbeTests`, which runs the real
  ``lab_server.orphan_server`` against a socket THIS test process opens on 127.0.0.1 (lsof,
  no network).
* The orchestrator is the production ``run_trial`` / ``World`` on the mock freeze tree of
  ``dryrun_live_ab`` with ``sim`` NOT set (so supervision is live), and with
  :class:`SupWorld` installed as ``WORLD_FACTORY``: as ``dryrun_live_ab.SimWorld`` it replaces
  only the worker process (episodes are ``dryrun_live_ab.run_sim_episode``); it additionally
  runs each episode lazily at its first reap check (so a pair is IN FLIGHT when a server dies),
  receipts anchors in process, skips the host scan and lets a test act before each health
  poll.  No model, no llama-server, no network.
* **What these tests cannot see** (EB1 fix, reviewer 2 finding 4): by default
  :class:`SupWorld` makes EVERY pump poll ``/health`` (``force_poll``), which is what lets a
  test crash a server at an exact point -- and which also hides every defect that depends on
  the frozen ``execution.health_poll_s`` cadence (a server that exits between two polls).
  :class:`CadenceTests` runs with ``force_poll`` off and the frozen cadence kept, as the one
  in-process control of that class of defect; the production cadence on the real entry path
  is covered by the EB1c controls ``C4bExitBetweenPairs`` and ``C6RestartCap``.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
"""
from __future__ import annotations

import contextlib
import copy
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_server                                                       # noqa: E402
import lab_verify_log                                                   # noqa: E402
from lab_common import canonical_json, sha256_canonical, sha256_text    # noqa: E402

CAP = 3
PROPS_SHA = sha256_text('eb1b: the tokenized golden /props digest')
SMOKE_USAGE = {'prompt_tokens': 20, 'completion_tokens': 3, 'total_tokens': 23,
               'cached_tokens': 0}
FINDING_OF_STAGE = {'gguf': 'gguf_sha256', 'serving_manifest': 'serving_manifest',
                    'launch': 'process_exited', 'health': 'health_timeout',
                    'identity': 'props_mismatch', 'smoke': 'seed_mismatch'}
SCENARIO = {'outcome_seed': 424242,
            'incumbent': {'p_good': 1.0, 'latency_scale': 4.5},
            'candidate': {'p_good': 1.0, 'latency_scale': 1.0}}


class Crash(BaseException):
    """The orchestrator process dying: nothing in run_trial catches a BaseException."""


# --------------------------------------------------------------------------- #
# the in-process lab_server
# --------------------------------------------------------------------------- #
class FakeServers:
    """What the orchestrator asks of ``lab_server``, answered by dicts.

    ``script``: outcomes of successive start/restart calls -- ``None`` succeeds, a stage name
    raises ``ServerStartFailed`` for that stage.  ``overrides``: fields forced into the NEXT
    successful body (to make the orchestrator write a body ``lab_server`` never would).
    Usage of an episode is added to the counters of the process serving its server at the
    time (:meth:`count`), as a real server counts what it serves."""

    NAMES = ('start', 'restart', 'stop', 'exit_status', 'health', 'metrics', 'orphan_server')

    def __init__(self) -> None:
        self.procs: dict[int, dict] = {}
        self.current: dict[str, int] = {}
        self.next_pid = 70001
        self.script: list = []
        self.overrides: dict = {}
        self.calls: list = []
        self.stopped: list = []
        self.foreign_alive: set = set()
        self.survive_stop = False
        self.restart_raises: type | None = None

    # -- process table ---------------------------------------------------------
    def _sid_of(self, base_url: str) -> str:
        port = int(str(base_url).rstrip('/').rsplit(':', 1)[-1])
        return {8091: 'coder', 8092: 't3'}[port]

    def _proc(self, base_url: str) -> dict | None:
        return self.procs.get(self.current.get(self._sid_of(base_url), -1))

    def alive(self, pid: int) -> bool:
        p = self.procs.get(int(pid))
        return bool(p and p['alive']) or int(pid) in self.foreign_alive

    def crash(self, sid: str, rc: int = 3) -> None:
        p = self.procs[self.current[sid]]
        p['alive'], p['rc'] = False, rc

    def hang(self, sid: str) -> None:
        self.procs[self.current[sid]]['healthy'] = False

    def count(self, sid: str, prompt: int, predicted: int) -> None:
        p = self.procs.get(self.current.get(sid, -1))
        if p and p['alive']:
            p['prompt'] += int(prompt)
            p['predicted'] += int(predicted)

    # -- the lab_server surface -----------------------------------------------
    def _launch(self, spec, kw: dict, kind: str) -> dict:
        self.calls.append((kind, spec.server_id, dict(kw)))
        outcome = self.script.pop(0) if self.script else None
        argv_sha = sha256_canonical(lab_server.server_argv(spec))
        if outcome is not None:
            raise lab_common.ServerStartFailed({
                'server_id': spec.server_id, 'kind': kind, 'stage': outcome,
                'findings': [FINDING_OF_STAGE[outcome]], 'pid': 0, 'returncode': None,
                'argv_sha256': argv_sha, 'props_sha256': None, 'load_seconds': 0.1,
                'restart_index': int(kw.get('restart_index') or 0)})
        pid = self.next_pid
        self.next_pid += 1
        # A start that matched the golden object carries ITS digest: lab_server.start hashes
        # the tokenized observation, which equals the golden object exactly then (and the
        # verifier's verified_start now checks it against config.receipt, EB1c).
        golden_props = kw.get('golden_props')
        props_sha = (sha256_canonical(golden_props) if isinstance(golden_props, dict)
                     else PROPS_SHA)
        self.procs[pid] = {'server_id': spec.server_id, 'alive': True, 'rc': None,
                           'healthy': True, 'prompt': SMOKE_USAGE['prompt_tokens'],
                           'predicted': SMOKE_USAGE['completion_tokens']}
        self.current[spec.server_id] = pid
        body = {
            'server_id': spec.server_id, 'pid': pid, 'port': int(spec.port),
            'argv_sha256': argv_sha, 'gguf': {'bytes': 1024, 'sha256': '9' * 64},
            'props_sha256': props_sha, 'props_matches_golden': True, 'total_slots': 2,
            'n_ctx': 8192, 'load_seconds': 0.5,
            'smoke': {'request_sha256': sha256_text('eb1b smoke'),
                      'receipt_matches_golden': True, 'usage': dict(SMOKE_USAGE),
                      'timings': {'cache_n': 0, 'prompt_n': 20, 'prompt_ms': 5.0,
                                  'predicted_n': 3, 'predicted_ms': 9.0,
                                  'predicted_per_second': 333.0},
                      'ok': True}}
        for key, value in self.overrides.items():
            if key.startswith('smoke.'):
                body['smoke'][key[6:]] = value
            else:
                body[key] = value
        self.overrides = {}
        return body

    def start(self, spec, **kw):
        return self._launch(spec, kw, 'start')

    def restart(self, spec, golden_props, **kw):
        if self.restart_raises is not None:
            raise self.restart_raises('the orchestrator died inside a restart')
        prev = kw.get('previous_pid')
        if prev is None or self.alive(int(prev)):
            raise lab_common.PreflightError('the previous server is still running')
        prev_sha = kw.get('previous_props_sha256')
        if not (isinstance(prev_sha, str) and len(prev_sha) == 64):
            raise lab_common.PreflightError('previous_props_sha256 is not a digest')
        body = self._launch(spec, dict(kw, golden_props=golden_props), 'restart')
        body['props_equal_previous'] = body['props_sha256'] == prev_sha
        return body

    def stop(self, pid, grace_s=10.0):
        self.stopped.append(int(pid))
        p = self.procs.get(int(pid))
        if p is None or self.survive_stop:
            return {'returncode': None, 'seconds': 0.0}
        if p['alive']:
            p['alive'], p['rc'] = False, -15
        return {'returncode': p['rc'], 'seconds': 0.01}

    def exit_status(self, pid):
        p = self.procs.get(int(pid))
        if p is None:
            raise lab_common.LabError('pid %d was not started by lab_server' % pid)
        return None if p['alive'] else p['rc']

    def health(self, base_url, timeout=5.0):
        p = self._proc(base_url)
        ok = bool(p and p['alive'] and p['healthy'])
        return {'ok': ok, 'slots_busy': 0, 'status': 'ok' if ok else 'no_answer'}

    def metrics(self, base_url, timeout=5.0, tries=3):
        p = self._proc(base_url)
        if not (p and p['alive'] and p['healthy']):
            out = {k: None for k in orch.COUNTER_KEYS}
            out.update(ok=False, tries=int(tries))
            return out
        return {'ok': True, 'tries': 1, 'prompt_tokens_total': p['prompt'],
                'tokens_predicted_total': p['predicted'],
                'n_decode_total': p['predicted'], 'requests_processing': 0,
                'requests_deferred': 0}

    def orphan_server(self, pid, port, timeout_s=10.0):
        if int(pid) in self.foreign_alive:
            return False
        p = self.procs.get(int(pid))
        return bool(p and p['alive'])

    @contextlib.contextmanager
    def patched(self):
        with contextlib.ExitStack() as stack:
            for name in self.NAMES:
                stack.enter_context(mock.patch.object(orch.lab_server, name,
                                                      getattr(self, name)))
            yield self


# --------------------------------------------------------------------------- #
# the world and the tree
# --------------------------------------------------------------------------- #
class SupWorld(dry.SimWorld):
    """``dryrun_live_ab.SimWorld`` (only the worker process is replaced) run on the LIVE
    supervision path (``sim`` unset), with lazy episodes, in-process anchor receipts, no host
    scan, and ``hook(world)`` called before every health poll, which always fires unless
    ``force_poll`` is off (then the frozen ``execution.health_poll_s`` cadence is kept)."""

    fake: FakeServers | None = None
    hook = None
    scenario: dict = {}
    force_poll: bool = True
    #: pairs whose episodes never finish (their worker hangs until the hard-cap kill)
    stuck_pairs: frozenset = frozenset()

    def spawn(self, att, job_path):                          # type: ignore[override]
        self.__dict__.setdefault('_lazy', {})[att.arrival] = att
        return os.getpid()

    def finished(self, att):                                 # type: ignore[override]
        lazy = self.__dict__.setdefault('_lazy', {})
        if att.arrival in lazy and att.pair in type(self).stuck_pairs:
            return None
        if att.arrival in lazy:
            del lazy[att.arrival]
            dry.run_sim_episode(att.job, self.scenario or SCENARIO)
            lines, _ = orch.read_spool_lines(att.spool, 0)
            for row in lines:
                if row.get('kind') == 'call_response':
                    usage = (row.get('body') or {}).get('usage') or {}
                    type(self).fake.count(att.server_id, usage.get('prompt_tokens', 0),
                                          usage.get('completion_tokens', 0))
            return None
        return 0

    def health_poll(self):
        if type(self).force_poll:
            self.last_health = float('-inf')
        if type(self).hook is not None:
            type(self).hook(self)
        super().health_poll()

    def host_scan(self, point):
        return None

    def request_anchor(self, trigger, *, blocking):
        super().request_anchor(trigger, blocking=blocking)
        req = self.pending_anchor
        path = self.ctx.paths.anchor_spool / 'receipts.jsonl'
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(canonical_json({
                'request_id': req['request_id'], 'ok': True, 'commit': None,
                'branch': None, 'pushed': False, 'comment_id': None, 'created_at': None,
                'updated_at': None, 'receipt_sha256': sha256_text(req['request_id']),
                'error_class': None}) + '\n')


class Tree:
    """A mock freeze tree (``dryrun_live_ab.build_mock_freeze``, which carries the contract's
    ``server_supervision`` block) and contexts built the way ``make_context`` builds one."""

    def __init__(self, trial: str = 'T4', pairs: int = 6, **freeze_kw) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='eb1b_'))
        self.results = self.root / 'results'
        self.work = self.root / 'work'
        self.trial = trial
        self.pairs = pairs
        self.built = dry.build_mock_freeze(self.results, n_pairs=pairs, trial=trial,
                                           **freeze_kw)
        self.freeze = self.results / 'freeze'
        self.bundle_sha = self.built['bundle_sha']

    def edit_config(self, fn) -> None:
        """Change the frozen configuration and re-bind the bundle to it, as a new freeze
        would (the bundle records the configuration's digest)."""
        path = self.freeze / 'config.json'
        cfg = json.loads(path.read_text('utf-8'))
        fn(cfg)
        path.write_text(canonical_json(cfg) + '\n', encoding='utf-8')
        bundle = dry._mock_bundle(self.freeze, cfg, self.built['roster'])
        (self.freeze / 'freeze_bundle.json').write_text(canonical_json(bundle) + '\n',
                                                        encoding='utf-8')
        self.bundle_sha = lab_common.freeze_bundle_sha256(bundle)

    def cfg(self, **rt) -> dict:
        cfg = json.loads((self.freeze / 'config.json').read_text('utf-8'))
        cfg['_runtime'] = dict({
            'results_root': str(self.results), 'work_root': str(self.work),
            'bundle_sha': self.bundle_sha, 'free_disk_floor_gb': 0.0,
            'clock_window_s': 0.01, 'preflight_mode': 'offline_fixture',
            'anchor_mode': 'mock', 'blocking_wait_s': 5.0, 'poll_interval_ms': 0,
            'worktree_check_s': 1e9, 'max_pairs': self.pairs,
            'tasks_path': str(self.freeze / 'tasks.json')}, **rt)
        return cfg

    def ctx(self, **rt):
        return orch.make_context(self.trial, self.cfg(**rt), results_root=self.results,
                                 work_root=self.work, inv=uuid.uuid4().hex)

    def events(self) -> list:
        return list(lab_eventlog.read_chain(self.results / self.trial / 'events',
                                            self.trial, self.bundle_sha).events)

    def verify_fails(self) -> list:
        report = lab_verify_log.verify_trial(self.trial, self.bundle_sha, mode='full',
                                             results_root=self.results,
                                             work_root=self.work)
        return [(f.check, f.detail) for f in report.findings if f.severity == 'FAIL']

    def frozen_cfg(self) -> dict:
        return json.loads((self.freeze / 'config.json').read_text('utf-8'))

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def run(tree: Tree, fake: FakeServers, *, hook=None, resume: bool = False,
        scenario: dict | None = None, stuck_pairs=(), force_poll: bool = True, **rt) -> str:
    """The production ``run_trial`` on the live supervision path with ``fake`` as lab_server."""
    SupWorld.fake = fake
    SupWorld.hook = hook
    SupWorld.force_poll = bool(force_poll)
    SupWorld.scenario = dict(scenario or SCENARIO)
    SupWorld.stuck_pairs = frozenset(stuck_pairs)
    with fake.patched(), mock.patch.object(orch, 'WORLD_FACTORY', SupWorld), \
            mock.patch.object(orch, 'host_quiescence_gate', lambda ctx: None):
        ctx = tree.ctx(**rt)
        assert not orch.runtime(ctx.cfg).get('sim')
        try:
            return orch.run_trial(ctx, resume=resume)
        except Crash:
            return 'crashed'


class CrashPlan:
    """Kill the server at the first health poll that sees a pair in flight, once per listed
    pair (randomized phase), and ``post`` times in the follow-up cohort."""

    def __init__(self, fake: FakeServers, pairs=(), *, post: int = 0, sid: str = 'coder',
                 how: str = 'exit') -> None:
        self.fake, self.pairs, self.post, self.sid, self.how = fake, set(pairs), post, sid, how
        self.done: set = set()
        self.post_done = 0

    def fire(self) -> None:
        if self.fake.alive(self.fake.current[self.sid]):
            (self.fake.crash if self.how == 'exit' else self.fake.hang)(self.sid)

    def __call__(self, world) -> None:
        if not world.open_arrivals or world.pending_abort or world.pending_pause:
            return
        if world.decision is None:
            pair = world.pairs_enrolled
            if pair in self.pairs and pair not in self.done:
                self.done.add(pair)
                self.fire()
        elif world.phase == 'post_decision' and self.post_done < self.post:
            self.post_done += 1
            self.fire()


def types(events, *wanted) -> list:
    return [e['type'] for e in events if not wanted or e['type'] in wanted]


def bodies(events, etype) -> list:
    return [e['body'] for e in events if e['type'] == etype]


def first_seq(events, etype, **match) -> int | None:
    for e in events:
        if e['type'] == etype and all(e['body'].get(k) == v for k, v in match.items()):
            return int(e['seq'])
    return None


def assigned_arrivals(events) -> set:
    out = set()
    for e in events:
        if e['type'] == 'coin_drawn':
            out |= {int(a) for a in e['body']['assignment']}
        elif e['type'] == 'arm_assigned_by_decision':
            out.add(int(e['body']['arrival']))
    return out


class TreeCase(unittest.TestCase):
    trial = 'T4'
    pairs = 6

    def setUp(self) -> None:
        self.tree = Tree(self.trial, self.pairs)
        self.addCleanup(self.tree.close)
        self.fake = FakeServers()


# --------------------------------------------------------------------------- #
# 1. the frozen supervision inputs: read, and refused before seq 0 when absent
# --------------------------------------------------------------------------- #
GOOD_BLOCK = {'max_supervised_restarts_per_server_per_trial': 3,
              'on_exceeding': 'abort_trial_incomplete'}


class SupervisionConfigTests(TreeCase):

    def test_the_cap_is_read_and_every_malformed_block_refused(self):
        self.assertEqual(lab_common.server_supervision_cap({'server_supervision': GOOD_BLOCK}),
                         3)
        self.assertEqual(lab_common.server_supervision_cap(
            {'server_supervision': dict(GOOD_BLOCK,
                                        max_supervised_restarts_per_server_per_trial=0)}), 0)
        bad = {
            'absent': {},
            'null': {'server_supervision': None},
            'not_object': {'server_supervision': [3]},
            'cap_str': {'server_supervision': dict(
                GOOD_BLOCK, max_supervised_restarts_per_server_per_trial='3')},
            'cap_bool': {'server_supervision': dict(
                GOOD_BLOCK, max_supervised_restarts_per_server_per_trial=True)},
            'cap_negative': {'server_supervision': dict(
                GOOD_BLOCK, max_supervised_restarts_per_server_per_trial=-1)},
            'unknown_member': {'server_supervision': dict(GOOD_BLOCK, extra=1)},
            'missing_member': {'server_supervision': {
                'max_supervised_restarts_per_server_per_trial': 3}},
            'other_policy': {'server_supervision': dict(GOOD_BLOCK,
                                                        on_exceeding='restart_forever')},
        }
        for label, cfg in bad.items():
            with self.subTest(label=label):
                with self.assertRaises(lab_common.FrozenMismatch):
                    lab_common.server_supervision_cap(cfg)

    def _refusal(self, ctx) -> tuple[set, set]:
        with self.assertRaises(lab_common.PreflightError) as caught:
            orch.preflight(ctx)
        return (set(str(caught.exception).split(',')),
                {r['item'] for r in getattr(caught.exception, 'drift', [])})

    def test_the_mock_freeze_carries_the_contract_block_outside_the_rule_block(self):
        cfg = self.tree.frozen_cfg()
        self.assertEqual(cfg['server_supervision'], GOOD_BLOCK)
        self.assertNotIn('server_supervision', lab_common.RULE_BLOCK_KEYS)
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            self.assertEqual(orch.preflight(self.tree.ctx()), [],
                             'control: a live-path preflight with the block passes')

    def test_a_live_run_without_or_with_a_malformed_block_is_refused_before_seq_0(self):
        for label, edit in (('absent', lambda c: c.pop('server_supervision')),
                            ('malformed', lambda c: c['server_supervision'].update(
                                max_supervised_restarts_per_server_per_trial='three'))):
            with self.subTest(label=label):
                tree = Tree()
                try:
                    tree.edit_config(edit)
                    with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
                        codes, items = self._refusal(tree.ctx())
                        self.assertIn('preflight_rule_failed', codes)
                        self.assertIn('server_supervision', items)
                        # control: a simulated run supervises nothing and needs no cap
                        self.assertEqual(orch.preflight(tree.ctx(sim=True)), [])
                    # and through run_trial: refused in the program chain, no trial chain
                    status = run(tree, self.fake)
                    self.assertEqual(status, 'aborted')
                    self.assertEqual(lab_eventlog.segment_paths(
                        tree.results / tree.trial / 'events'), [])
                    self.assertEqual(self.fake.calls, [], 'no server was started')
                finally:
                    tree.close()

    def test_the_health_threshold_is_required_and_read(self):
        self.tree.edit_config(lambda c: c['execution'].pop('health_failures_to_down'))
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            codes, items = self._refusal(self.tree.ctx())
        self.assertIn('execution.health_failures_to_down', items)
        self.assertEqual(orch.health_failures_to_down(
            {'execution': {'health_failures_to_down': 2}}), 2)
        for bad in (0, -1, True, '3', None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                orch.health_failures_to_down({'execution': {'health_failures_to_down': bad}})


# --------------------------------------------------------------------------- #
# 2. health_poll supervision, unit level (one World, no episodes)
# --------------------------------------------------------------------------- #
class HealthPollTests(TreeCase):

    def world(self, tree: Tree | None = None):
        tree = tree or self.tree
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            ctx = tree.ctx()
        ctx.paths.mkdirs()
        world = orch.World(ctx)
        world.open_chain(create=True)
        self.addCleanup(lambda: world.log.close())
        return world

    @staticmethod
    def poll(world) -> None:
        world.last_health = float('-inf')
        world.health_poll()

    def test_an_exited_server_is_down_by_exit_then_stopped_restarted_and_scraped(self):
        world = self.world()
        with self.fake.patched():
            world.start_servers()
            old = world.server_pids['coder']
            self.poll(world)
            self.assertEqual(types(world.log.events), ['server_started', 'server_health'],
                             'control: a live server is only polled')
            self.fake.crash('coder', rc=3)
            self.poll(world)
        evs = world.log.events[2:]
        self.assertEqual(types(evs), ['server_down', 'server_stopped', 'server_restarted',
                                      'metrics_scrape'])
        down = evs[0]['body']
        self.assertEqual((down['detected_by'], down['returncode'], down['counters_lost']),
                         ('exit', 3, True))
        self.assertEqual(evs[1]['body']['pid'], old)
        restarted = evs[2]['body']
        self.assertTrue(restarted['props_equal_previous'])
        self.assertEqual(evs[3]['body']['point'], 'restart')
        self.assertEqual(world.restarts, {'coder': 1})
        self.assertNotEqual(world.server_pids['coder'], old)
        kind, _, kw = self.fake.calls[-1]
        self.assertEqual(kind, 'restart')
        golden_sha = self.tree.frozen_cfg()['receipt']['golden_props_sha256']['coder']
        self.assertEqual((kw['previous_pid'], kw['previous_props_sha256'], kw['timeout_s'],
                          kw['restart_index']), (old, golden_sha, 180.0, 1))
        self.assertIsNotNone(kw['golden_props'])
        for ev in world.log.events:
            lab_eventlog.validate_event(ev['type'], ev['body'])

    def test_a_hung_server_is_down_on_the_third_consecutive_failure_only(self):
        world = self.world()
        with self.fake.patched():
            world.start_servers()
            self.fake.hang('coder')
            self.poll(world)
            self.poll(world)
            self.assertNotIn('server_down', types(world.log.events), 'two failures: up')
            self.poll(world)
        self.assertEqual(types(world.log.events, 'server_down', 'server_restarted'),
                         ['server_down', 'server_restarted'])
        down = bodies(world.log.events, 'server_down')[0]
        self.assertEqual((down['detected_by'], down['returncode']), ('health', None))
        self.assertEqual([b['ok'] for b in bodies(world.log.events, 'server_health')],
                         [False, False, False])

    def test_control_a_good_poll_resets_the_failure_count(self):
        world = self.world()
        with self.fake.patched():
            world.start_servers()
            for healthy in (False, False, True, False, False, True, False, False):
                self.fake.procs[self.fake.current['coder']]['healthy'] = healthy
                self.poll(world)
        self.assertNotIn('server_down', types(world.log.events))

    def test_the_threshold_is_the_frozen_key(self):
        tree = Tree()
        self.addCleanup(tree.close)
        tree.edit_config(lambda c: c['execution'].update(health_failures_to_down=2))
        world = self.world(tree)
        with self.fake.patched():
            world.start_servers()
            self.fake.hang('coder')
            self.poll(world)
            self.poll(world)
        self.assertIn('server_down', types(world.log.events),
                      'health_failures_to_down=2 is read: down after two failures')

    def test_the_restart_count_reaches_the_cap_and_the_next_down_restarts_nothing(self):
        world = self.world()
        with self.fake.patched():
            world.start_servers()
            for _ in range(CAP):
                self.fake.crash('coder')
                self.poll(world)
            self.assertEqual(world.restarts, {'coder': CAP})
            self.assertIsNone(world.pending_abort, 'control: three restarts are allowed')
            n_restart_calls = sum(1 for c in self.fake.calls if c[0] == 'restart')
            self.fake.crash('coder')
            self.poll(world)
        self.assertEqual(world.pending_abort, 'server_restart_cap')
        self.assertEqual(sum(1 for c in self.fake.calls if c[0] == 'restart'),
                         n_restart_calls, 'no fourth restart was attempted')
        self.assertNotIn('coder', world.server_pids)
        self.assertEqual(types(world.log.events)[-2:], ['server_down', 'server_stopped'])
        with self.assertRaises(lab_common.AbortTrial) as caught:
            world.raise_pending()
        self.assertEqual(caught.exception.reason, 'server_restart_cap')

    def test_failed_restarts_owe_a_pause_or_an_abort_by_stage(self):
        expect = {'launch': ('pause', 'server_unrecoverable'),
                  'health': ('pause', 'server_unrecoverable'),
                  'identity': ('abort', 'server_identity'),
                  'serving_manifest': ('abort', 'server_identity'),
                  'gguf': ('abort', 'server_identity'),
                  'smoke': ('abort', 'receipt_mismatch')}
        for stage, (what, reason) in expect.items():
            with self.subTest(stage=stage):
                tree = Tree()
                self.addCleanup(tree.close)
                fake = FakeServers()
                world = self.world(tree)
                with fake.patched():
                    world.start_servers()
                    fake.script = [stage]
                    fake.crash('coder')
                    self.poll(world)
                failed = bodies(world.log.events, 'server_start_failed')
                self.assertEqual([(b['kind'], b['stage'], b['restart_index'])
                                  for b in failed], [('restart', stage, 1)])
                self.assertEqual(world.restarts, {'coder': 1}, 'a failed restart counts')
                exc = lab_common.PauseTrial if what == 'pause' else lab_common.AbortTrial
                with self.assertRaises(exc) as caught:
                    world.raise_pending()
                self.assertEqual(caught.exception.reason, reason)

    def test_a_refused_restart_call_owes_a_harness_defect_abort(self):
        world = self.world()
        with self.fake.patched():
            world.start_servers()
            self.fake.survive_stop = True          # the hung process will not die ...
            self.fake.hang('coder')
            for _ in range(3):
                self.poll(world)                   # ... so lab_server.restart refuses
        self.assertEqual(world.pending_abort, 'harness_defect')
        self.assertNotIn('server_restarted', types(world.log.events))


# --------------------------------------------------------------------------- #
# 3. the production run_trial with servers dying in flight
# --------------------------------------------------------------------------- #
class SupervisedRunTests(TreeCase):
    pairs = 6

    def test_restarts_below_the_cap_keep_the_trial_and_reconcile_exactly(self):
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(1, 2, 3)))
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        self.assertEqual(len(bodies(events, 'server_restarted')), CAP)
        self.assertNotIn('trial_aborted', types(events))
        # every server_down listed the pair in flight, and those reveals carry infra_flag
        downs = bodies(events, 'server_down')
        inflight = {r['arrival'] for d in downs for r in d['inflight']}
        self.assertEqual(len(downs), 3)
        self.assertTrue(all(len(d['inflight']) == 2 for d in downs))
        for body in bodies(events, 'episode_revealed'):
            self.assertIs(body['outcome']['infra_flag'], body['arrival'] in inflight,
                          'control: an arrival of a pair without a crash keeps False')
        # reconciliation: a window per process; the cut ones lost, the rest exact
        recs = bodies(events, 'usage_reconciliation')
        self.assertEqual([(r['window'], r['counters_lost']) for r in recs],
                         [('restart', True)] * 3 + [('restart', False)])
        self.assertFalse(any(r['reconciliation_defect'] for r in recs))
        self.assertEqual(recs[-1]['residual'], {'prompt': 0, 'predicted': 0})
        # the restart scrape follows every restart
        for i, ev in enumerate(events):
            if ev['type'] == 'server_restarted':
                self.assertEqual((events[i + 1]['type'], events[i + 1]['body']['point']),
                                 ('metrics_scrape', 'restart'))
        self.assertEqual(self.tree.verify_fails(), [])

    def test_control_no_crash_is_one_trial_window_with_the_smoke_in_it(self):
        status = run(self.tree, self.fake)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        recs = bodies(events, 'usage_reconciliation')
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual((rec['window'], rec['counters_lost'], rec['reconciliation_defect']),
                         ('trial', False, False))
        responses = sum(b['usage']['prompt_tokens'] for b in bodies(events, 'llm_response'))
        self.assertEqual(rec['client_usage_sum']['prompt'],
                         responses + SMOKE_USAGE['prompt_tokens'],
                         'the SERVER_SMOKE usage is in the identity')
        self.assertTrue(all(b['outcome']['infra_flag'] is False
                            for b in bodies(events, 'episode_revealed')))
        self.assertEqual(self.tree.verify_fails(), [])

    def test_a_fourth_down_drains_reveals_and_aborts_with_the_restart_cap(self):
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(1, 2, 3, 4)))
        events = self.tree.events()
        self.assertEqual(status, 'aborted')
        self.assertEqual(len(bodies(events, 'server_restarted')), CAP)
        aborted = bodies(events, 'trial_aborted')
        self.assertEqual([b['reason'] for b in aborted], ['server_restart_cap'])
        cap_down = [e for e in events if e['type'] == 'server_down'][-1]
        abort_seq = first_seq(events, 'trial_aborted')
        after = events[cap_down['seq'] + 1:]
        self.assertNotIn('episode_started', types(after), 'nothing dispatched after the cap')
        self.assertNotIn('server_restarted', types(after), 'no fourth restart')
        self.assertNotIn('pair_enrolled', types(after), 'no replacement, no extra pair')
        self.assertEqual(len(bodies(events, 'pair_enrolled')), 4)
        # the pair in flight at the fourth down was drained and revealed before the abort
        drained = {r['arrival'] for r in cap_down['body']['inflight']}
        self.assertEqual(len(drained), 2)
        reveal_seq = {int(e['body']['arrival']): int(e['seq']) for e in events
                      if e['type'] == 'episode_revealed'}
        self.assertEqual(set(reveal_seq), assigned_arrivals(events),
                         'every enrolled attempt is retained and revealed once')
        self.assertTrue(all(reveal_seq[a] > cap_down['seq'] and reveal_seq[a] < abort_seq
                            for a in drained))
        self.assertTrue(all(b['outcome']['infra_flag'] for b in bodies(
            events, 'episode_revealed') if b['arrival'] in drained))
        self.assertEqual(self.tree.verify_fails(), [])

    def test_the_cap_drain_is_bounded_by_the_hard_cap_kill(self):
        # pair 4's two workers hang: the drain after the fourth down cannot wait for them
        # forever -- the ordinary hard-cap kill reveals them as episode_timeout, then abort
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(1, 2, 3, 4)),
                     stuck_pairs=(4,), episode_hard_cap_s=2.0)
        events = self.tree.events()
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['server_restart_cap'])
        cap_down = [e for e in events if e['type'] == 'server_down'][-1]
        drained = {r['arrival'] for r in cap_down['body']['inflight']}
        reveals = [e for e in events if e['type'] == 'episode_revealed'
                   and e['body']['arrival'] in drained]
        self.assertEqual(len(reveals), 2)
        self.assertEqual({e['body']['outcome']['error_class'] for e in reveals},
                         {'episode_timeout'})
        self.assertTrue(all(e['seq'] < first_seq(events, 'trial_aborted') for e in reveals))
        # control: the abort WAITED for the kill instead of abandoning the attempts
        waited_ns = (events[first_seq(events, 'trial_aborted')]['t_mono_ns']
                     - cap_down['t_mono_ns'])
        self.assertGreater(waited_ns, 1.5e9)
        self.assertEqual(self.tree.verify_fails(), [])

    def test_a_failed_restart_that_never_became_healthy_pauses_after_the_pair(self):
        self.fake.script = [None, 'health']       # the start succeeds, the restart does not
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(2,)))
        events = self.tree.events()
        self.assertEqual(status, 'paused')
        self.assertEqual([b['reason_code'] for b in bodies(events, 'trial_paused')],
                         ['server_unrecoverable'])
        failed_seq = first_seq(events, 'server_start_failed')
        pause_seq = first_seq(events, 'trial_paused')
        between = events[failed_seq + 1:pause_seq]
        self.assertNotIn('episode_started', types(between))
        self.assertEqual(len(types(between, 'episode_revealed')), 2,
                         'the pair in flight finished and was revealed first')
        self.assertEqual(len(bodies(events, 'pair_enrolled')), 2)
        self.assertEqual(self.tree.verify_fails(), [])

    def test_control_a_failed_restart_that_is_an_identity_failure_aborts_after_the_drain(
            self):
        for stage, reason in (('identity', 'server_identity'), ('smoke', 'receipt_mismatch')):
            with self.subTest(stage=stage):
                tree = Tree(pairs=4)
                self.addCleanup(tree.close)
                fake = FakeServers()
                fake.script = [None, stage]
                status = run(tree, fake, hook=CrashPlan(fake, pairs=(2,)))
                events = tree.events()
                self.assertEqual(status, 'aborted')
                self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                                 [reason])
                self.assertEqual(set(int(b['arrival']) for b in bodies(
                    events, 'episode_revealed')), assigned_arrivals(events))
                self.assertEqual(tree.verify_fails(), [])


class PauseStopsServersTests(TreeCase):
    trial = 'T3'                                   # two servers: coder and t3
    pairs = 4

    def test_pause_stops_every_server_it_holds_before_trial_paused(self):
        self.fake.script = [None, None, 'launch']  # both start; coder's restart fails
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(1,)))
        events = self.tree.events()
        self.assertEqual(status, 'paused')
        t3_pid = bodies(events, 'server_started')[1]['pid']
        pause_seq = first_seq(events, 'trial_paused')
        stopped = [e for e in events if e['type'] == 'server_stopped']
        self.assertIn(('t3', t3_pid), [(e['body']['server_id'], e['body']['pid'])
                                        for e in stopped if e['seq'] < pause_seq])
        self.assertFalse(self.fake.alive(t3_pid), 'no server outlives a paused invocation')
        self.assertEqual({p for p, v in self.fake.procs.items() if v['alive']}, set())

    def test_control_a_run_that_ends_also_stops_them_but_after_reconciliation(self):
        status = run(self.tree, self.fake)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        self.assertEqual(sorted(b['server_id'] for b in bodies(events, 'server_stopped')),
                         ['coder', 't3'])
        self.assertEqual(len(bodies(events, 'usage_reconciliation')), 2)
        self.assertEqual(self.tree.verify_fails(), [])


# --------------------------------------------------------------------------- #
# 4. resume: orphans, a fresh verified start before any dispatch, carried state
# --------------------------------------------------------------------------- #
class ResumeTests(TreeCase):
    pairs = 5

    def kill_at(self, pair: int, *, leave_servers: bool = True):
        def hook(world):
            if world.open_arrivals and world.pairs_enrolled == pair:
                self.fake.survive_stop = leave_servers   # SIGKILL: no finally ran
                raise Crash()
        return hook

    def invocation_slice(self, events, n: int) -> list:
        starts = [i for i, e in enumerate(events) if e['type'] == 'invocation_started']
        return events[starts[n - 1]:]

    def test_resume_stops_the_live_orphan_then_starts_and_verifies_before_dispatch(self):
        self.assertEqual(run(self.tree, self.fake, hook=self.kill_at(2)), 'crashed')
        orphan = self.fake.current['coder']
        self.assertTrue(self.fake.alive(orphan))
        self.fake.survive_stop = False
        status = run(self.tree, self.fake, resume=True)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        second = self.invocation_slice(events, 1)
        order = types(second, 'server_stopped', 'server_started', 'episode_started')
        self.assertEqual(order[:2], ['server_stopped', 'server_started'])
        self.assertEqual(order[2], 'episode_started', 'the start precedes every dispatch')
        self.assertEqual(second[[e['type'] for e in second].index('server_stopped')]
                         ['body']['pid'], orphan)
        self.assertFalse(self.fake.alive(orphan))
        started = [e for e in second if e['type'] == 'server_started'][0]
        nxt = second[second.index(started) + 1]
        self.assertEqual((nxt['type'], nxt['body']['point']), ('metrics_scrape', 'restart'))
        self.assertFalse(any(r['reconciliation_defect']
                             for r in bodies(events, 'usage_reconciliation')))
        self.assertEqual(self.tree.verify_fails(), [])

    def test_control_a_recorded_pid_that_is_no_longer_ours_is_never_signalled(self):
        self.assertEqual(run(self.tree, self.fake, hook=self.kill_at(2)), 'crashed')
        orphan = self.fake.current['coder']
        self.fake.procs[orphan]['alive'] = False     # our server is gone ...
        self.fake.foreign_alive.add(orphan)          # ... and the OS reused its pid
        self.fake.survive_stop = False
        stopped_before = list(self.fake.stopped)
        status = run(self.tree, self.fake, resume=True)
        self.assertEqual(status, 'ended')
        second = self.invocation_slice(self.tree.events(), 1)
        self.assertNotIn(orphan, [b['pid'] for b in bodies(second, 'server_stopped')])
        self.assertNotIn(orphan, self.fake.stopped[len(stopped_before):])

    def test_restarts_are_rebuilt_from_the_chain_so_the_cap_spans_invocations(self):
        hook_1 = CrashPlan(self.fake, pairs=(1, 2))
        killer = self.kill_at(3, leave_servers=False)

        def first(world):
            hook_1(world)
            killer(world)
        self.assertEqual(run(self.tree, self.fake, hook=first), 'crashed')
        self.assertEqual(len(bodies(self.tree.events(), 'server_restarted')), 2)
        self.fake.survive_stop = False
        seen = {}

        def second(world):
            seen.setdefault('restarts', dict(world.restarts))
            CrashPlan.__call__(plan_2, world)
        plan_2 = CrashPlan(self.fake, pairs=(3, 4))
        status = run(self.tree, self.fake, hook=second, resume=True)
        events = self.tree.events()
        self.assertEqual(seen['restarts'], {'coder': 2}, 'rebuilt from the chain')
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['server_restart_cap'])
        self.assertEqual(len(bodies(events, 'server_restarted')), CAP,
                         'one restart after resume, then the cap: 2 + 1, never 2 + 2')
        self.assertEqual(self.tree.verify_fails(), [])

    def test_a_crash_inside_supervision_is_answered_by_a_restart_on_resume(self):
        plan = CrashPlan(self.fake, pairs=(2,))
        self.fake.restart_raises = Crash
        self.assertEqual(run(self.tree, self.fake, hook=plan), 'crashed')
        events = self.tree.events()
        self.assertEqual(types(events)[-2:], ['server_down', 'server_stopped'])
        state = orch.supervision_state(events, CAP)
        self.assertEqual(list(state.unresolved_down), ['coder'])
        # control: at a cap of 0 the same chain owes the cap abort, not a restart
        self.assertEqual(orch.supervision_state(events, 0).pending_abort,
                         'server_restart_cap')
        self.fake.restart_raises = None
        status = run(self.tree, self.fake, resume=True)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        second = self.invocation_slice(events, 1)
        self.assertEqual(types(second, 'server_restarted', 'server_started',
                               'episode_started')[0], 'server_restarted',
                         'the unresolved down is answered by a restart, before dispatch')
        self.assertEqual(bodies(second, 'server_restarted')[0]['props_equal_previous'], True)
        self.assertEqual(self.tree.verify_fails(), [])

    def test_a_failed_start_on_resume_follows_the_supervision_rules(self):
        for stage, status_want, reason in (('health', 'paused', 'server_unrecoverable'),
                                           ('identity', 'aborted', 'server_identity')):
            with self.subTest(stage=stage):
                tree = Tree(pairs=4)
                self.addCleanup(tree.close)
                fake = FakeServers()
                self.fake = fake
                self.assertEqual(run(tree, fake, hook=self.kill_at(2, leave_servers=False)),
                                 'crashed')
                fake.script = [stage]
                status = run(tree, fake, resume=True)
                events = tree.events()
                second = self.invocation_slice(events, 1)
                self.assertEqual(status, status_want)
                self.assertNotIn('episode_started', types(second), 'nothing dispatched')
                self.assertEqual([(b['kind'], b['stage']) for b in bodies(
                    second, 'server_start_failed')], [('start', stage)])
                terminal = bodies(second, 'trial_paused') or bodies(second, 'trial_aborted')
                self.assertEqual([b.get('reason_code') or b.get('reason')
                                  for b in terminal], [reason])
                self.assertEqual(tree.verify_fails(), [])


# --------------------------------------------------------------------------- #
# 5. the pure functions: supervision state and reconciliation windows
# --------------------------------------------------------------------------- #
def ev(seq: int, etype: str, **body) -> dict:
    body.setdefault('server_id', 'coder')
    return {'seq': seq, 'type': etype, 'body': body}


def started(seq, etype='server_started', usage=None, **kw):
    return ev(seq, etype, props_sha256=PROPS_SHA,
              smoke={'usage': dict(usage or SMOKE_USAGE)}, **kw)


def scrape(seq, point, prompt, predicted, ok=True):
    return ev(seq, 'metrics_scrape', point=point, ok=ok,
              counters={'prompt_tokens_total': prompt if ok else None,
                        'tokens_predicted_total': predicted if ok else None,
                        'n_decode_total': None, 'requests_processing': None,
                        'requests_deferred': None})


def resp(seq, prompt, completion):
    return ev(seq, 'llm_response', usage={'prompt_tokens': prompt,
                                          'completion_tokens': completion})


class SupervisionStateTests(unittest.TestCase):

    def test_attempted_restarts_count_failed_restarts_but_not_failed_starts(self):
        events = [started(0), ev(1, 'server_down', inflight=[]),
                  started(2, 'server_restarted', props_equal_previous=True),
                  ev(3, 'server_down', inflight=[]),
                  ev(4, 'server_start_failed', kind='restart', stage='launch'),
                  ev(5, 'trial_paused'), ev(6, 'server_start_failed', kind='start',
                                            stage='launch'), ev(7, 'trial_paused')]
        state = orch.supervision_state(events, CAP)
        self.assertEqual(state.restarts, {'coder': 2})
        self.assertIsNone(state.pending_pause, 'a pause discharges an owed pause')

    def test_the_cap_binds_on_the_down_that_finds_the_server_at_it(self):
        base = [started(0)]
        seq = 1
        for _ in range(CAP):
            base += [ev(seq, 'server_down', inflight=[{'arrival': seq, 'arm': 'incumbent'}]),
                     started(seq + 1, 'server_restarted', props_equal_previous=True)]
            seq += 2
        control = orch.supervision_state(base, CAP)
        self.assertEqual((control.pending_abort, control.cap_required), (None, False))
        state = orch.supervision_state(base + [ev(seq, 'server_down', inflight=[])], CAP)
        self.assertEqual((state.pending_abort, state.cap_required),
                         ('server_restart_cap', True))
        self.assertEqual(state.unresolved_down, {})
        self.assertEqual(state.down_overlap, frozenset({1, 3, 5}))
        # a simulated run (cap None) is never bound
        self.assertIsNone(orch.supervision_state(
            base + [ev(seq, 'server_down', inflight=[])], None).pending_abort)

    def test_an_owed_abort_survives_a_pause_and_an_abort_discharges_it(self):
        events = [started(0), ev(1, 'server_down', inflight=[]),
                  ev(2, 'server_start_failed', kind='restart', stage='identity'),
                  ev(3, 'trial_paused')]
        self.assertEqual(orch.supervision_state(events, CAP).pending_abort,
                         'server_identity')
        self.assertIsNone(orch.supervision_state(events + [ev(4, 'trial_aborted')],
                                                 CAP).pending_abort)

    def test_props_not_equal_previous_owes_server_identity(self):
        events = [started(0), ev(1, 'server_down', inflight=[]),
                  started(2, 'server_restarted', props_equal_previous=False)]
        self.assertEqual(orch.supervision_state(events, CAP).pending_abort, 'server_identity')
        events[2]['body']['props_equal_previous'] = True
        self.assertIsNone(orch.supervision_state(events, CAP).pending_abort, 'control')


class ReconciliationTests(unittest.TestCase):

    def windows(self, events):
        out = orch.reconciliation_windows(events, ['coder'])
        for body in out:
            lab_eventlog.validate_event('usage_reconciliation', body)
        return out

    def test_the_smoke_is_in_the_identity(self):
        events = [started(1), scrape(2, 'trial_start', 20, 3), resp(3, 100, 10),
                  scrape(4, 'pair_boundary', 120, 13), scrape(5, 'trial_end', 120, 13)]
        (w,) = self.windows(events)
        self.assertEqual((w['window'], w['counters_lost'], w['reconciliation_defect']),
                         ('trial', False, False))
        self.assertEqual(w['residual'], {'prompt': 0, 'predicted': 0})
        # negative controls: one token off is a defect; leaving the smoke OUT of the identity
        # (the pre-EB1b rule) turns this correct run into a defect
        off = copy.deepcopy(events)
        off[-1] = scrape(5, 'trial_end', 121, 13)
        self.assertTrue(self.windows(off)[0]['reconciliation_defect'])
        no_smoke = copy.deepcopy(events)
        no_smoke[0] = started(1, usage={'prompt_tokens': 0, 'completion_tokens': 0})
        self.assertEqual(self.windows(no_smoke)[0]['residual'], {'prompt': 20, 'predicted': 3})

    def test_a_restart_splits_the_windows_and_the_cut_one_is_lost(self):
        events = [started(1), scrape(2, 'trial_start', 20, 3), resp(3, 100, 10),
                  scrape(4, 'pair_boundary', 120, 13), resp(5, 50, 5),
                  ev(6, 'server_down', inflight=[]),
                  started(8, 'server_restarted', props_equal_previous=True),
                  scrape(9, 'restart', 20, 3), resp(10, 70, 7),
                  scrape(11, 'pair_boundary', 90, 10), scrape(12, 'trial_end', 90, 10)]
        cut, after = self.windows(events)
        self.assertEqual((cut['window'], cut['counters_lost'], cut['residual'],
                          cut['reconciliation_defect'], cut['window_to_seq']),
                         ('restart', True, {'prompt': None, 'predicted': None}, False, 6))
        self.assertEqual((after['window'], after['window_from_seq'], after['counters_lost'],
                          after['reconciliation_defect']), ('restart', 8, False, False))
        self.assertEqual(after['client_usage_sum'], {'prompt': 90, 'predicted': 10})
        # negative control: the same chain read as ONE window (no split: the restart body
        # relabelled a plain start event is not enough -- remove the down and the restart) is
        # a defect, because the counter restarted at 0
        unsplit = [e for e in events if e['type'] not in ('server_down', 'server_restarted')]
        self.assertTrue(self.windows(unsplit)[0]['reconciliation_defect'])
        off = copy.deepcopy(events)
        off[-1] = scrape(12, 'trial_end', 90, 11)
        self.assertTrue(self.windows(off)[1]['reconciliation_defect'],
                        'control: the post-restart window is still checked')

    def test_the_restart_scrape_closes_no_window(self):
        events = [started(1), scrape(2, 'restart', 20, 3)]
        (w,) = self.windows(events)
        self.assertTrue(w['counters_lost'])
        control = self.windows(events + [scrape(3, 'trial_end', 20, 3)])
        self.assertEqual((control[0]['counters_lost'], control[0]['reconciliation_defect']),
                         (False, False))

    def test_a_failed_last_scrape_reconciles_at_the_last_exact_one(self):
        events = [started(1), scrape(2, 'trial_start', 20, 3), resp(3, 100, 10),
                  scrape(4, 'pair_boundary', 120, 13), scrape(5, 'trial_end', 0, 0, ok=False)]
        (w,) = self.windows(events)
        self.assertEqual((w['window_to_seq'], w['counters_lost'], w['reconciliation_defect']),
                         (4, False, False))
        none_ok = [started(1), resp(2, 100, 10), scrape(3, 'trial_end', 0, 0, ok=False)]
        self.assertTrue(self.windows(none_ok)[0]['counters_lost'],
                        'no exact scrape: unreconciled, never a residual against 0')


# --------------------------------------------------------------------------- #
# 6. the verifier: server.lifecycle
# --------------------------------------------------------------------------- #
def lifecycle(events, cfg) -> list:
    """The FAILED ``server.lifecycle`` rules.  (Its one INFO row, the restart-cap case label
    of root's 21:14 ruling, is not a failure; :func:`lifecycle_info` reads it.)"""
    col = lab_verify_log._Collector(trial='T4', mode='full')
    lab_verify_log._check_server_lifecycle(col, events, cfg)
    assert 'server.lifecycle' in col.seen
    return [f.detail.get('rule') for f in col.findings
            if f.check == 'server.lifecycle' and f.severity != 'INFO']


def lifecycle_info(events, cfg) -> list:
    col = lab_verify_log._Collector(trial='T4', mode='full')
    lab_verify_log._check_server_lifecycle(col, events, cfg)
    return [dict(f.detail) for f in col.findings
            if f.check == 'server.lifecycle' and f.severity == 'INFO']


class LifecycleVerifierTests(unittest.TestCase):
    """Real chains written by the production orchestrator, then mutated one rule at a time
    (the check is called on the event list; the wiring test below reads a chain from disk)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def make(**kw):
            tree = Tree(pairs=kw.pop('pairs', 5))
            cls.trees.append(tree)
            fake = FakeServers()
            fake.script = kw.pop('script', [])
            status = run(tree, fake, hook=CrashPlan(fake, pairs=kw.pop('crash', ())))
            return status, tree.events(), tree.frozen_cfg()
        cls.restarted = make(crash=(1, 2, 3))           # ended, 3 restarts
        cls.capped = make(crash=(1, 2, 3, 4))           # aborted(server_restart_cap)
        cls.failed = make(crash=(2,), script=[None, 'identity'])   # aborted(server_identity)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_the_real_chains_pass(self):
        self.assertEqual([s for s, _, _ in (self.restarted, self.capped, self.failed)],
                         ['ended', 'aborted', 'aborted'])
        for _, events, cfg in (self.restarted, self.capped, self.failed):
            self.assertEqual(lifecycle(events, cfg), [])
        # the capped chain is labelled (INFO) with its case of root's 21:14 ruling; the
        # chains the cap never bound in carry no label (negative control)
        _, capped, cfg = self.capped
        self.assertEqual([(r['rule'], r['case']) for r in lifecycle_info(capped, cfg)],
                         [('restart_cap_case', 'before_decision')])
        for _, events, cfg in (self.restarted, self.failed):
            self.assertEqual(lifecycle_info(events, cfg), [])

    @staticmethod
    def mutate(events, fn) -> list:
        out = copy.deepcopy(events)
        fn(out)
        return out

    def test_verified_start(self):
        _, events, cfg = self.restarted
        for etype, path in (('server_started', ('props_matches_golden',)),
                            ('server_restarted', ('smoke', 'ok')),
                            ('server_restarted', ('smoke', 'receipt_matches_golden'))):
            with self.subTest(etype=etype, path=path):
                def flip(evs, etype=etype, path=path):
                    body = next(e['body'] for e in evs if e['type'] == etype)
                    holder = body
                    for key in path[:-1]:
                        holder = holder[key]
                    holder[path[-1]] = False
                self.assertIn('verified_start', lifecycle(self.mutate(events, flip), cfg))

    def test_down_answered(self):
        _, events, cfg = self.restarted
        i = next(i for i, e in enumerate(events) if e['type'] == 'server_restarted')
        dropped = events[:i] + events[i + 1:]
        self.assertIn('down_answered', lifecycle(dropped, cfg))
        j = next(i for i, e in enumerate(events) if e['type'] == 'server_down')
        episode = next(e for e in events if e['type'] == 'episode_started')
        dispatched = events[:j + 1] + [copy.deepcopy(episode)] + events[j + 1:]
        self.assertIn('down_answered', lifecycle(dispatched, cfg))
        # control: a chain that is not terminal and simply ends after the down is pending
        self.assertEqual(lifecycle(events[:j + 1], cfg), [])

    def test_cap(self):
        _, events, cfg = self.restarted
        tight = copy.deepcopy(cfg)
        tight['server_supervision']['max_supervised_restarts_per_server_per_trial'] = 2
        self.assertIn('cap', lifecycle(events, tight))
        missing = {k: v for k, v in cfg.items() if k != 'server_supervision'}
        self.assertIn('cap', lifecycle(events, missing), 'an unreadable cap is not a pass')
        # control: a chain with no restart does not need the cap
        no_restart = [e for e in events if e['type'] not in ('server_down',
                                                             'server_restarted')]
        self.assertEqual(lifecycle(no_restart, missing), [])

    def test_failure_answered(self):
        _, events, cfg = self.failed
        i = next(i for i, e in enumerate(events) if e['type'] == 'server_start_failed')
        episode = next(e for e in events if e['type'] == 'episode_started')
        dispatched = events[:i + 1] + [copy.deepcopy(episode)] + events[i + 1:]
        self.assertIn('failure_answered', lifecycle(dispatched, cfg))

        def ended(evs):
            for e in evs:
                if e['type'] == 'trial_aborted':
                    e['type'] = 'trial_ended'
        self.assertIn('failure_answered', lifecycle(self.mutate(events, ended), cfg))

    def test_cap_abort_iff_required(self):
        _, capped, cfg = self.capped

        def other_reason(evs):
            next(e for e in evs if e['type'] == 'trial_aborted')['body']['reason'] = \
                'infrastructure'
        self.assertIn('cap_abort_iff_required',
                      lifecycle(self.mutate(capped, other_reason), cfg))
        _, restarted, _ = self.restarted

        def cap_abort(evs):
            for e in evs:
                if e['type'] == 'trial_ended':
                    e['type'] = 'trial_aborted'
                    e['body'].update(status='aborted', reason='server_restart_cap')
        self.assertIn('cap_abort_iff_required',
                      lifecycle(self.mutate(restarted, cap_abort), cfg))

    def test_simulated_chains_are_skipped_and_mixed_ones_fail(self):
        sim = {'server_id': 'coder', 'pid': 0, 'props_sha256': lab_eventlog.SIM_SERVER_SHA256,
               'gguf': {'bytes': 0, 'sha256': lab_eventlog.SIM_SERVER_SHA256},
               'props_matches_golden': False,
               'smoke': {'request_sha256': lab_eventlog.SIM_SERVER_SHA256,
                         'receipt_matches_golden': False, 'ok': False}}
        events = [{'seq': 0, 'type': 'server_started', 'body': sim}]
        # skipped only under a DRY-RUN configuration (EB1 fix, reviewer 1 finding 5): the
        # sentinels are values the chain writer controls
        self.assertEqual(lifecycle(events, {'mock': True}), [],
                         'a simulated start under a dry-run configuration claims nothing')
        self.assertEqual(lifecycle(events, {'mock_overrides': {'x': 1}}), [])
        self.assertEqual(lifecycle(events, {}), ['simulated_under_live_config'],
                         'negative control: the same chain under a live configuration')
        live = [copy.deepcopy(e) for e in self.restarted[1] if e['type'] == 'server_started']
        self.assertIn('mixed', lifecycle(events + live, {}))


class LifecycleWiringTests(TreeCase):
    pairs = 3

    def test_a_body_lab_server_never_returns_fails_the_full_verifier(self):
        self.fake.overrides = {'smoke.receipt_matches_golden': False}
        self.assertEqual(run(self.tree, self.fake), 'ended')
        fails = self.tree.verify_fails()
        self.assertIn(('server.lifecycle', 'verified_start'),
                      [(c, d.get('rule')) for c, d in fails])

    def test_control_the_same_run_with_a_true_body_passes(self):
        self.assertEqual(run(self.tree, self.fake), 'ended')
        self.assertEqual(self.tree.verify_fails(), [])
        self.assertTrue(lab_verify_log.plumbing_allows('server.lifecycle'))
        self.assertEqual(lab_verify_log.CHECK_SEVERITY['server.lifecycle'], 'FAIL')


# --------------------------------------------------------------------------- #
# 7. the results builder: root's 21:14 restart-cap ruling, case (b)
# --------------------------------------------------------------------------- #
class ReportabilityTests(unittest.TestCase):
    """Root's 21:14 ruling (``reviews/restart_cap_estimand_ruling_20260923_2114.md``), which
    WITHDREW the repair contract's reportability default this class used to pin ("no
    decision from a cap-aborted trial"): a deploy decision logged in the randomized phase and
    externally receipted (the decision anchor's chained receipt, in process), then a fourth
    ``server_down`` in the follow-up cohort -- case (b).  ``trial_aborted(server_restart_cap)``;
    the decision and its original tau STAND and are reported; the follow-up is truncated and
    its unrun arrivals are counted in the terminal record and the results.  Negative controls:
    the same trial without the fourth down (``trial_ended``, nothing truncated, case
    ``none``), and the capped chain with the decision's receipt removed (a local decision
    event alone is provisional: case (c) label, not reportable, and the verifier FAILs the
    switch that no longer follows a receipt)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def make(post: int):
            # dryrun_live_ab's D3 setting (mock-only delta 0.9, n_min 25 of 50 pairs): the
            # candidate is faster at equal success, and the monitor deploys at n = 44
            tree = Tree('T4', pairs=50, delta=0.9, n_min=25)
            cls.trees.append(tree)
            fake = FakeServers()
            status = run(tree, fake, hook=CrashPlan(fake, pairs=(1, 2, 3), post=post))
            out = tree.root / 'built'
            summary = builder.build([tree.trial], tree.bundle_sha,
                                    results_root=tree.results, work_root=tree.work,
                                    out_dir=out, mock=True)
            decision = json.loads((out / tree.trial / 'decision.json').read_text('utf-8'))
            return status, tree.events(), summary, decision, tree
        cls.capped = make(post=1)
        cls.complete = make(post=0)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_case_b_the_receipted_decision_stands_and_the_follow_up_is_truncated(self):
        status, events, summary, decision, tree = self.capped
        self.assertEqual(status, 'aborted')
        logged = bodies(events, 'decision')
        self.assertEqual([(b['kind'], b['n']) for b in logged], [('deploy_candidate', 44)],
                         'the fixture must log a deployment decision before the abort')
        (aborted,) = bodies(events, 'trial_aborted')
        self.assertEqual(aborted['reason'], 'server_restart_cap')
        required = lab_eventlog.restart_cap_required_seq(events, CAP)
        receipt = lab_eventlog.decision_receipt(events, mock=True)
        self.assertLess(first_seq(events, 'decision'), receipt['receipt_seq'])
        self.assertLess(receipt['receipt_seq'], required)
        self.assertLess(first_seq(events, 'traffic_switch'), required)
        self.assertLess(required, first_seq(events, 'trial_aborted'))
        # nothing post-switch after the cap was required, and no second decision
        self.assertEqual([e for e in events if e['seq'] > required and e['type'] in (
            'arm_assigned_by_decision', 'episode_started', 'decision', 'traffic_switch')], [])
        # the terminal record counts the truncation
        comp = aborted['completion']
        self.assertEqual((comp['restart_cap_case'], comp['cap_required_seq'],
                          comp['decision_status'], comp['decision_seq']),
                         ('after_receipted_decision', required, 'receipted',
                          first_seq(events, 'decision')))
        never_assigned = 100 - len(assigned_arrivals(events))
        self.assertGreater(never_assigned, 0, 'the follow-up was truncated')
        self.assertEqual(comp['follow_up_not_run'], never_assigned)
        self.assertEqual(comp['follow_up_run'], len(types(events, 'arm_assigned_by_decision')))
        self.assertEqual(comp['arrivals_total'], 100)
        self.assertEqual(comp['arrivals_not_run'],
                         100 - len({b['arrival'] for b in bodies(events, 'episode_started')}))
        # the builder reports the decision at its original tau, labelled
        self.assertEqual((decision['primary_result'], decision['reportable'],
                          decision['decision']['kind'], decision['decision']['n']),
                         ('deploy_candidate', True, 'deploy_candidate', 44))
        self.assertEqual(decision['restart_cap']['case'], 'after_receipted_decision')
        self.assertTrue(decision['decision_label'].startswith(
            'decision stands at tau=44; follow-up truncated by the restart cap (%d '
            % never_assigned), decision['decision_label'])
        row = summary['trials']['T4']
        self.assertEqual((row['decision'], row['reportable'], row['restart_cap_case'],
                          row['follow_up_not_run']),
                         ('deploy_candidate', True, 'after_receipted_decision',
                          never_assigned))
        self.assertNotIn('logged_decision', row)
        # the verifier: no failure, and the case labelled
        self.assertEqual(tree.verify_fails(), [])
        self.assertEqual([(r['rule'], r['case']) for r in
                          lifecycle_info(events, tree.frozen_cfg())],
                         [('restart_cap_case', 'after_receipted_decision')])

    def test_control_the_same_trial_without_the_fourth_down_is_complete(self):
        status, events, summary, decision, tree = self.complete
        self.assertEqual(status, 'ended')
        self.assertEqual(decision['primary_result'], 'deploy_candidate')
        self.assertIs(decision['reportable'], True)
        self.assertIsNone(decision['decision_label'])
        self.assertEqual(decision['restart_cap']['case'], 'none')
        (ended,) = bodies(events, 'trial_ended')
        self.assertEqual((ended['completion']['restart_cap_case'],
                          ended['completion']['follow_up_not_run'],
                          ended['completion']['arrivals_not_run']), ('none', 0, 0))
        self.assertEqual(summary['trials']['T4']['decision'], 'deploy_candidate')
        self.assertNotIn('logged_decision', summary['trials']['T4'])
        self.assertEqual(tree.verify_fails(), [])

    def test_control_only_the_cap_makes_a_case_whatever_the_abort_reason(self):
        """The case is fixed by the ``server_down`` that found the cap reached, never by an
        abort's reason (the check the removed ``restart_cap_incomplete`` test made): the
        complete run's chain relabelled ``trial_aborted(<reason>)`` is case ``none`` and its
        receipted decision stays reportable; the capped chain is case (b) whatever reason its
        terminal record carries."""
        _, complete, _, _, tree = self.complete
        _, capped, _, _, _ = self.capped
        cfg = tree.frozen_cfg()
        for reason in ('server_restart_cap', 'infrastructure', 'server_identity'):
            with self.subTest(reason=reason):
                evs = copy.deepcopy(complete)
                term = next(e for e in reversed(evs) if e['type'] == 'trial_ended')
                term['type'] = 'trial_aborted'
                term['body'].update(status='aborted', reason=reason)
                obj = builder.decision_object(evs, cfg, 'T4')
                self.assertEqual((obj['restart_cap']['case'], obj['reportable'],
                                  obj['primary_result']),
                                 ('none', True, 'deploy_candidate'))
                evs = copy.deepcopy(capped)
                next(e for e in reversed(evs)
                     if e['type'] == 'trial_aborted')['body']['reason'] = reason
                self.assertEqual(builder.decision_object(evs, cfg, 'T4')['restart_cap']['case'],
                                 'after_receipted_decision')

    def test_control_without_its_receipt_the_same_decision_is_provisional(self):
        _, events, _, _, tree = self.capped
        receipt = lab_eventlog.decision_receipt(events, mock=True)
        stripped = [e for e in events if e['seq'] != receipt['receipt_seq']]
        cfg = tree.frozen_cfg()
        self.assertEqual(lab_eventlog.restart_cap_case(stripped, CAP, mock=True)['case'],
                         'decision_provisional')
        obj = builder.decision_object(stripped, cfg, 'T4')
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision_status']),
                         (builder.PROVISIONAL_LABEL, False, 'provisional'))
        self.assertIn('switch_before_decision_receipt', lifecycle(stripped, cfg))
        # and a receipt WITHOUT the external server time counts only in a MOCK tree
        live_cfg = {k: v for k, v in cfg.items() if k not in ('mock', 'mock_overrides')}
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=False)['status'],
                         'provisional')
        self.assertIn('switch_before_decision_receipt', lifecycle(events, live_cfg))


# --------------------------------------------------------------------------- #
# 8. lab_server.orphan_server against a real loopback listener (lsof; no network)
# --------------------------------------------------------------------------- #
@unittest.skipUnless(shutil.which('lsof'), 'lsof is not available')
class OrphanProbeTests(unittest.TestCase):

    def test_a_live_pid_listening_on_the_port_is_ours_and_nothing_else_is(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.bind(('127.0.0.1', 0))
        sock.listen(1)
        port = int(sock.getsockname()[1])
        self.assertIs(lab_server.orphan_server(os.getpid(), port), True)
        other = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        other.bind(('127.0.0.1', 0))
        free_port = int(other.getsockname()[1])
        other.close()
        self.assertIs(lab_server.orphan_server(os.getpid(), free_port), False,
                      'alive but not listening there: a reused pid, never signalled')
        dead = subprocess.Popen([sys.executable, '-c', 'pass'])
        dead.wait()
        self.assertIs(lab_server.orphan_server(dead.pid, port), False, 'not alive')
        self.assertIs(lab_server.orphan_server(0, port), False)

    def test_an_unreadable_listener_table_is_unknown_not_yes(self):
        with mock.patch.object(lab_server.subprocess, 'run',
                               side_effect=OSError('no lsof')):
            self.assertIsNone(lab_server.listening_pids(8091))
            self.assertIsNone(lab_server.orphan_server(os.getpid(), 8091))


# --------------------------------------------------------------------------- #
# 9. schema and vocabulary
# --------------------------------------------------------------------------- #
class VocabularyTests(unittest.TestCase):

    def test_the_owed_outcomes_are_closed_schema_values(self):
        aborts = set(lab_eventlog.E_ABORT_REASON.enum)
        self.assertIn('server_restart_cap', aborts)
        self.assertTrue(set(orch.START_FAILURE_REASON.values()) <= aborts)
        self.assertIn('harness_defect', aborts)
        self.assertIn('server_unrecoverable', lab_eventlog.E_TRIAL_PAUSE.enum)
        self.assertTrue(orch.NEVER_HEALTHY_STAGES <= set(lab_server.START_STAGES))
        self.assertIn('restart', lab_eventlog.E_SCRAPE_POINT.enum)
        self.assertEqual(set(orch.QUIESCENT_SCRAPE_POINTS) - set(
            lab_eventlog.E_SCRAPE_POINT.enum), set())


# --------------------------------------------------------------------------- #
# 10. EB1 fix (two adversarial reviews of EB1a-c): each class names its finding
# --------------------------------------------------------------------------- #
def _kill_at(fake: FakeServers, pair: int, *, leave_servers: bool = True):
    def hook(world):
        if world.open_arrivals and world.pairs_enrolled == pair:
            fake.survive_stop = leave_servers          # SIGKILL: no finally ran
            raise Crash()
    return hook


class FirstStartReplayTests(TreeCase):
    """Reviewer 1 finding 1: a failed FIRST start is trial_aborted live
    (``START_FAILURE_REASON``); its replay used to owe a PAUSE for launch/health, so a crash
    between the durable ``server_start_failed`` and ``trial_aborted`` let a resume run the
    whole trial the live rules had aborted."""
    pairs = 3

    def test_the_replay_of_a_first_start_owes_its_abort_at_every_stage(self):
        for stage, reason in orch.START_FAILURE_REASON.items():
            with self.subTest(stage=stage):
                events = [ev(0, 'trial_started'),
                          ev(1, 'server_start_failed', kind='start', stage=stage)]
                state = orch.supervision_state(events, CAP)
                self.assertEqual((state.pending_abort, state.pending_pause), (reason, None))
        # control: the same record written by a RESUMED invocation follows the supervision
        # rules (never healthy -> pause), as World.resume_servers does
        resumed = [ev(0, 'trial_started'), ev(1, 'invocation_started'),
                   ev(2, 'server_start_failed', kind='start', stage='launch')]
        state = orch.supervision_state(resumed, CAP)
        self.assertEqual((state.pending_abort, state.pending_pause),
                         (None, 'server_unrecoverable'))

    def test_a_crash_after_a_failed_first_start_is_resumed_into_its_abort(self):
        self.fake.script = ['launch']                  # the first start never becomes healthy

        def die(world, status):                        # power loss inside close_trial
            raise Crash()
        with mock.patch.object(orch.World, 'close_trial', die):
            self.assertEqual(run(self.tree, self.fake), 'crashed')
        events = self.tree.events()
        self.assertEqual(types(events)[-2:], ['trial_started', 'server_start_failed'])
        status = run(self.tree, self.fake, resume=True)
        events = self.tree.events()
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['infrastructure'])
        for etype in ('trial_paused', 'server_started', 'pair_enrolled', 'episode_started'):
            self.assertNotIn(etype, types(events))
        self.assertEqual(self.tree.verify_fails(), [])


class FirstStartVerifierTests(unittest.TestCase):
    """Reviewer 1 finding 1, the verifier half: ``failure_answered`` used to accept ANY
    pause or abort after a first start's failure."""

    def chain(self, answer, *, resumed: bool = False, stage: str = 'launch') -> list:
        out = [ev(0, 'trial_started')]
        if resumed:
            out.append(ev(1, 'invocation_started'))
        out.append(ev(len(out), 'server_start_failed', kind='start', stage=stage))
        out.append(ev(len(out), *answer[:1], **answer[1]))
        return out

    def test_a_first_start_failure_is_answered_by_its_abort_reason_only(self):
        self.assertEqual(lab_verify_log.FIRST_START_ABORT_REASON, orch.START_FAILURE_REASON)
        paused = self.chain(('trial_paused', {'reason_code': 'server_unrecoverable'}))
        self.assertEqual(lifecycle(paused, {}), ['failure_answered'])
        wrong = self.chain(('trial_aborted', {'reason': 'server_identity'}))
        self.assertEqual(lifecycle(wrong, {}), ['failure_answered'])
        # controls: the live rule's own answer; and a RESUMED start's failure may pause
        right = self.chain(('trial_aborted', {'reason': 'infrastructure'}))
        self.assertEqual(lifecycle(right, {}), [])
        smoke = self.chain(('trial_aborted', {'reason': 'receipt_mismatch'}), stage='smoke')
        self.assertEqual(lifecycle(smoke, {}), [])
        resumed = self.chain(('trial_paused', {'reason_code': 'server_unrecoverable'}),
                             resumed=True)
        self.assertEqual(lifecycle(resumed, {}), [])


class VerifiedStartScopeTests(unittest.TestCase):
    """Reviewer 2 finding 2: what ``verified_start`` can and cannot detect, pinned so that
    the docstring's scope cannot drift into a claim the check does not perform."""

    def test_a_fabricated_body_carrying_the_golden_digest_is_not_detectable(self):
        golden = sha256_text('the golden tokenized /props')
        cfg = {'receipt': {'golden_props_sha256': {'coder': golden}}}
        body = {'server_id': 'coder', 'pid': 4242, 'props_sha256': golden,
                'props_matches_golden': True, 'gguf': {'sha256': '9' * 64},
                'smoke': {'request_sha256': sha256_text('mock'),
                          'receipt_matches_golden': True, 'ok': True}}
        events = [ev(0, 'trial_started', golden_props_sha256={'coder': golden}),
                  {'seq': 1, 'type': 'server_started', 'body': body}]
        self.assertEqual(lifecycle(events, cfg), [],
                         'the stated limit: copied digest + true flags pass')
        # control: the b049307 placeholder hashed the RAW /props -- that is rejected
        raw = copy.deepcopy(events)
        raw[1]['body']['props_sha256'] = sha256_text('the raw /props')
        self.assertEqual(lifecycle(raw, cfg), ['verified_start'])
        doc = lab_verify_log._check_server_lifecycle.__doc__
        self.assertIn('CANNOT detect', doc)


class ReconciliationOpenAttemptTests(unittest.TestCase):
    """Reviewer 1 finding 4: a scrape at a 'quiescent' point name was taken as exact even
    with attempts open on the server (``trial_end`` after a mid-pair abort)."""

    def windows(self, events):
        out = orch.reconciliation_windows(events, ['coder'])
        for body in out:
            lab_eventlog.validate_event('usage_reconciliation', body)
        return out

    PREFIX = [started(1), scrape(2, 'trial_start', 20, 3),
              ev(3, 'episode_started', arrival=1), resp(4, 100, 10),
              ev(5, 'episode_revealed', arrival=1), scrape(6, 'pair_boundary', 120, 13),
              ev(7, 'episode_started', arrival=3), ev(8, 'episode_started', arrival=4)]

    def test_a_scrape_with_an_attempt_open_on_the_server_is_not_exact(self):
        # the server already counted 80/9 of arrival 3 that the chain has not ingested
        events = self.PREFIX + [scrape(9, 'trial_end', 200, 22)]
        (w,) = self.windows(events)
        self.assertEqual((w['window_to_seq'], w['counters_lost'], w['reconciliation_defect'],
                          w['residual']), (6, False, False, {'prompt': 0, 'predicted': 0}),
                         'reconciled at the last EXACT scrape, the pair boundary')
        # control: the same trial_end scrape once both attempts are revealed IS exact
        closed = self.PREFIX + [resp(9, 80, 9), ev(10, 'episode_revealed', arrival=3),
                                ev(11, 'episode_revealed', arrival=4),
                                scrape(12, 'trial_end', 200, 22)]
        (w,) = self.windows(closed)
        self.assertEqual((w['window_to_seq'], w['reconciliation_defect']), (12, False))
        off = closed[:-1] + [scrape(12, 'trial_end', 201, 22)]
        self.assertTrue(self.windows(off)[0]['reconciliation_defect'],
                        'control: the exact scrape is still checked')

    def test_an_attempt_open_on_another_server_does_not_count(self):
        events = self.PREFIX[:6] + [ev(7, 'episode_started', arrival=3, server_id='t3'),
                                    scrape(8, 'trial_end', 120, 13)]
        (w,) = self.windows(events)
        self.assertEqual(w['window_to_seq'], 8)


class FollowUpQuiescentScrapeTests(TreeCase):
    """Reviewer 1 finding 4: the follow-up cohort's 'quiescent' scrape used to be taken right
    AFTER dispatching the 50th arrival, with it open."""

    def test_the_quiescent_scrape_follows_the_drain_before_the_next_dispatch(self):
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            ctx = self.tree.ctx()
        ctx.paths.mkdirs()
        w = orch.World(ctx)
        w.open_chain(create=True)
        self.addCleanup(lambda: w.log.close())
        w.decision_seq, w.decided_arm, w.phase = 1, 'candidate', 'post_decision'
        w.post_decision_dispatched = 48
        seen: list = []
        w.build_job = lambda **k: {'workflow': 'x', 'server': {'server_id': 'coder'},
                                   'task_uid': 'u'}

        def dispatch(att):
            w.attempts[att.arrival] = att
            w.open_arrivals.append(att.arrival)
        w.dispatch = dispatch
        w.scrape = lambda point, **k: seen.append((point, list(w.open_arrivals)))
        self.assertTrue(w.dispatch_follow_up())
        self.assertTrue(w.dispatch_follow_up())            # the 50th of the cohort
        self.assertEqual((w.post_decision_dispatched, seen), (50, []),
                         'no scrape while the 50th is open')
        w.open_arrivals.remove(w.open_arrivals[0])
        self.assertFalse(w.dispatch_follow_up(), 'the 51st waits for the drain')
        self.assertEqual(seen, [])
        w.open_arrivals.clear()                             # drained
        self.assertTrue(w.dispatch_follow_up())
        self.assertEqual(seen, [('quiescent', [])], 'taken with nothing open')
        self.assertEqual((w.post_decision_dispatched, len(w.open_arrivals)), (51, 1))


class OwedAbortPrecedenceTests(TreeCase):
    """Reviewer 2 finding 3: 'While an abort is owed _auto_abort is not consulted' had no
    control.  The automatic-abort rules are instrumented to fire once armed."""
    pairs = 6

    def run_armed(self, arm_when, plan=None) -> tuple[str, list]:
        armed = {'on': False}
        real = orch.World._auto_abort

        def auto_abort(world):
            if armed['on']:                             # a rule 12/13 or ten-failure hit
                raise lab_common.AbortTrial('infrastructure')
            real(world)

        def hook(world):
            if plan is not None:
                plan(world)
            if arm_when(world):
                armed['on'] = True
        with mock.patch.object(orch.World, '_auto_abort', auto_abort):
            status = run(self.tree, self.fake, hook=hook)
        return status, self.tree.events()

    def test_no_automatic_abort_preempts_the_owed_restart_cap(self):
        status, events = self.run_armed(
            lambda w: w.pending_abort == orch.RESTART_CAP_REASON,
            plan=CrashPlan(self.fake, pairs=(1, 2, 3, 4)))
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['server_restart_cap'])
        self.assertEqual(self.tree.verify_fails(), [])

    def test_control_the_armed_rule_aborts_when_nothing_is_owed(self):
        status, events = self.run_armed(lambda w: w.pairs_enrolled == 2 and w.open_arrivals)
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['infrastructure'])


class IngestBeforeDownTests(TreeCase):
    """Reviewer 2 finding 3: 'ingests every open spool first' (supervise_down) had no
    control.  The pair's episodes have RUN (their spools are written, the old process
    counted them) but are not yet ingested when the down is detected."""
    pairs = 4

    def test_responses_the_dying_process_served_land_in_its_own_window(self):
        state: dict = {}

        def hook(world):
            if state or world.pairs_enrolled != 2 or not world.open_arrivals:
                return
            lazy = world.__dict__.get('_lazy', {})
            if any(a in lazy for a in world.open_arrivals):
                return                                  # an episode has not run yet
            state['arrivals'] = set(world.open_arrivals)
            self.fake.crash('coder')
        status = run(self.tree, self.fake, hook=hook)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        self.assertEqual(len(state['arrivals']), 2)
        down = first_seq(events, 'server_down')
        restarted = first_seq(events, 'server_restarted')
        served = [e['seq'] for e in events if e['type'] == 'llm_response'
                  and e['body']['arrival'] in state['arrivals']]
        self.assertTrue(served)
        self.assertTrue(all(seq < down for seq in served),
                        'every response of the dying process precedes its server_down')
        recs = bodies(events, 'usage_reconciliation')
        after = [r for r in recs if r['window_from_seq'] == restarted]
        self.assertEqual([(r['counters_lost'], r['reconciliation_defect']) for r in after],
                         [(False, False)], 'the new process window reconciles exactly')
        self.assertEqual(self.tree.verify_fails(), [])


class CadenceTests(TreeCase):
    """Reviewer 2 finding 4: with ``force_poll`` off the frozen health-poll cadence is kept,
    so an exit between two polls is visible only to the pair-boundary exit check."""
    pairs = 4

    def test_an_exit_between_pairs_is_answered_before_the_next_pair(self):
        self.tree.edit_config(lambda cfg: cfg['execution'].update(health_poll_s=3600))
        state: dict = {}
        real_reveal = orch._reveal

        def reveal(world, att, **kw):
            real_reveal(world, att, **kw)
            if att.pair == 2 and not state and all(
                    world.attempts[a].revealed for a in world.pair_arrivals()):
                state['pid'] = self.fake.current['coder']
                self.fake.crash('coder', rc=9)          # no request in flight
        with mock.patch.object(orch, '_reveal', reveal):
            status = run(self.tree, self.fake, force_poll=False)
        events = self.tree.events()
        self.assertEqual(status, 'ended')
        self.assertIn('pid', state)
        downs = [e for e in events if e['type'] == 'server_down']
        self.assertEqual([(d['body']['detected_by'], d['body']['returncode'])
                          for d in downs], [('exit', 9)])
        pair_3 = next(e['seq'] for e in events
                      if e['type'] == 'pair_enrolled' and e['body']['pair'] == 3)
        self.assertLess(downs[0]['seq'], pair_3, 'answered before the next pair')
        self.assertLessEqual(len(bodies(events, 'server_health')), 1,
                             'control: the periodic poll kept its cadence')
        self.assertEqual(self.tree.verify_fails(), [])


class RestartEscapeTests(TreeCase):
    """Reviewer 1 finding 7 (restart half): an exception out of lab_server.restart that is
    not ``ServerStartFailed`` used to escape run_trial mid-pair, leaving the down
    unanswered and no terminal event."""
    pairs = 4

    def test_an_unexpected_restart_exception_owes_a_harness_defect_abort(self):
        self.fake.restart_raises = TypeError
        status = run(self.tree, self.fake, hook=CrashPlan(self.fake, pairs=(2,)))
        events = self.tree.events()
        self.assertEqual(status, 'aborted')
        self.assertEqual([b['reason'] for b in bodies(events, 'trial_aborted')],
                         ['harness_defect'])
        down = first_seq(events, 'server_down')
        self.assertNotIn('episode_started', types([e for e in events if e['seq'] > down]))
        self.assertEqual({b['arrival'] for b in bodies(events, 'episode_revealed')},
                         assigned_arrivals(events), 'drained and revealed, not abandoned')
        self.assertEqual(self.tree.verify_fails(), [])


class ResumeGateTests(TreeCase):
    """Reviewer 1 finding 2: the hard host gate runs before a resume opens the chain and
    allowlisted only the new orchestrator, so the orphan the resume exists to stop was a
    foreign consumer.  (The real gate with a real orphan: tests_eb1_entry.C10.)"""
    pairs = 3

    def test_the_gate_allowlists_a_recorded_server_that_is_still_ours(self):
        self.assertEqual(run(self.tree, self.fake, hook=_kill_at(self.fake, 2)), 'crashed')
        orphan = self.fake.current['coder']
        with mock.patch.object(orch, 'WORLD_FACTORY', SupWorld):
            ctx = self.tree.ctx()
        seen: list = []
        with self.fake.patched(), mock.patch.object(
                orch.lab_hostcheck, 'preflight_host_quiescent',
                lambda own, **kw: seen.append(set(own))):
            orch.host_quiescence_gate(ctx)
            self.fake.procs[orphan]['alive'] = False      # our server is gone ...
            self.fake.foreign_alive.add(orphan)           # ... and the OS reused its pid
            orch.host_quiescence_gate(ctx)
        self.assertIn(os.getpid(), seen[0])
        self.assertIn(orphan, seen[0])
        self.assertNotIn(orphan, seen[1], 'control: a pid no longer that server stays foreign')

    def test_control_a_fresh_trial_allowlists_only_the_orchestrator(self):
        with mock.patch.object(orch, 'WORLD_FACTORY', SupWorld):
            ctx = self.tree.ctx()
        self.assertEqual(orch.chain_orphan_server_pids(ctx), set())


class BuilderMockTests(unittest.TestCase):
    """Reviewer 1 finding 5, the builder half: the MOCK banner was decided by the
    configuration alone, so a simulated chain under a live configuration had none."""

    def run_tree(self, *, sim: bool) -> Tree:
        tree = Tree(pairs=2)
        self.addCleanup(tree.close)
        fake = FakeServers()
        if sim:
            SupWorld.fake, SupWorld.hook, SupWorld.force_poll = fake, None, True
            SupWorld.scenario, SupWorld.stuck_pairs = dict(SCENARIO), frozenset()
            with mock.patch.object(orch, 'WORLD_FACTORY', SupWorld):
                self.assertEqual(orch.run_trial(tree.ctx(sim=True), resume=False), 'ended')
        else:
            self.assertEqual(run(tree, fake), 'ended')
        path = tree.freeze / 'config.json'
        cfg = json.loads(path.read_text('utf-8'))
        cfg.pop('mock', None)
        cfg.pop('mock_overrides', None)                 # a configuration that is not a dry run
        path.write_text(canonical_json(cfg) + '\n', encoding='utf-8')
        return tree

    def build(self, tree: Tree) -> dict:
        return builder.build([tree.trial], tree.bundle_sha, results_root=tree.results,
                             work_root=tree.work, out_dir=tree.root / 'built', mock=False)

    def test_a_simulated_chain_carries_the_banner_whatever_the_configuration_says(self):
        tree = self.run_tree(sim=True)
        self.assertEqual(lab_verify_log.server_start_kind(tree.events()), 'simulated')
        summary = self.build(tree)
        self.assertIs(summary['mock'], True)
        decision = json.loads((tree.root / 'built' / tree.trial / 'decision.json')
                              .read_text('utf-8'))
        self.assertEqual(decision.get('banner'), builder.BANNER)
        self.assertEqual(lifecycle(tree.events(), tree.frozen_cfg()),
                         ['simulated_under_live_config'])

    def test_control_a_live_chain_under_the_same_configuration_is_not_forced(self):
        tree = self.run_tree(sim=False)
        self.assertEqual(lab_verify_log.server_start_kind(tree.events()), 'live')
        self.assertIs(self.build(tree)['mock'], False)

if __name__ == '__main__':
    unittest.main()
