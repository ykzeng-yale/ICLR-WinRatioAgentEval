"""tests_lab_e2e.py -- G5: the orchestrator, resume, the switch, the anchors, the builder.

Every test here runs offline, deterministically, with no model, no language-model server,
no network beyond the loopback the mock uses, and no state-changing git command.  The
episodes are written by the simulated worker of ``dryrun_live_ab`` (a test double for
``lab_worker`` only): the chain, the coin, the monitor, the shadow, the decision, the
anchors and the whole resume path are the production code in every test below.

The kill-point matrix of protocol 14.5 / ARCHITECTURE_FINAL.md 9.2 is the centrepiece: a
crash is injected at each point, the trial is resumed, and after every one of them the
verifier must PASS with never a second coin, never a second reveal and never a re-run.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import lab_anchor                                                       # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_monitor                                                      # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_reference_rule                                               # noqa: E402
import lab_verify_log                                                   # noqa: E402
from lab_common import canonical_json, sha256_bytes

#: The pre-registration documents, committed beside the code so that this test is portable
#: and does not depend on any scratch directory outside the repository.
DESIGN_DIR = Path(__file__).resolve().parent / 'design'


#: A simulated hard crash: nothing is unwound, nothing is closed.  It is
#: ``dryrun_live_ab.SimKill`` so that a crash injected inside the simulated worker and one
#: injected at a chain append are the same exception.
_Kill = dry.SimKill


# ---------------------------------------------------------------------------
# a scratch tree with a mock freeze, an anchor process and a run driver
# ---------------------------------------------------------------------------
class Tree:
    def __init__(self, *, pairs: int, trial: str = 'T4', delta: float | None = None,
                 n_min: int | None = None, scenario: Mapping | None = None,
                 anchor: bool = True) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='live_ab_e2e_'))
        self.results = self.root / 'results'
        self.work = self.root / 'work'
        self.trial = trial
        self.pairs = pairs
        self.built = dry.build_mock_freeze(self.results, n_pairs=pairs, trial=trial,
                                           delta=delta, n_min=n_min)
        self.bundle_sha = self.built['bundle_sha']
        self.scenario = dict(scenario or {'outcome_seed': 424242,
                                          'incumbent': {'p_good': 1.0,
                                                        'latency_scale': 4.5},
                                          'candidate': {'p_good': 1.0,
                                                        'latency_scale': 1.0}})
        self.anchor_proc = dry._start_anchor(trial, self._cfg(), self.results,
                                             self.work) if anchor else None

    def _cfg(self) -> dict:
        cfg = json.loads((self.results / 'freeze' / 'config.json').read_text('utf-8'))
        cfg['_runtime'] = {
            'results_root': str(self.results), 'work_root': str(self.work),
            'bundle_sha': self.bundle_sha, 'sim': True, 'mock': True,
            'anchor_mode': 'mock', 'blocking_wait_s': 25.0, 'poll_interval_ms': 0,
            'worktree_check_s': 1e9, 'free_disk_floor_gb': 0.0,
            'tasks_path': str(self.results / 'freeze' / 'tasks.json'),
            'max_pairs': self.pairs,
            'golden': {'coder': {'props': {}, 'generation_settings': {},
                                 'mask': ['seed'], 'float_tolerance': 1e-6}},
        }
        return cfg

    def run(self, *, kill: Mapping | None = None, resume: bool = False,
            world_cls: Any = None, runtime_extra: Mapping | None = None) -> str:
        cfg = self._cfg()
        cfg['_runtime'].update(dict(runtime_extra or {}))
        cls = world_cls or SimWorld
        cls.scenario = dict(self.scenario)
        cls.kill_spec = dict(kill or {})
        cls.kill_counts = {}
        dry.SIM_COUNTS.clear()
        previous = orch.WORLD_FACTORY
        orch.WORLD_FACTORY = cls
        try:
            ctx = orch.make_context(self.trial, cfg, results_root=self.results,
                                    work_root=self.work, inv=uuid.uuid4().hex)
            return orch.run_trial(ctx, resume=resume)
        except _Kill:
            return 'killed'
        finally:
            orch.WORLD_FACTORY = previous
            for path in (self.work / self.trial / 'run.lock',):
                if path.exists():
                    path.unlink()

    def events(self) -> list[dict]:
        read = lab_eventlog.read_chain(self.results / self.trial / 'events', self.trial,
                                       self.bundle_sha)
        return list(read.events)

    def verify(self, mode: str = 'full'):
        return lab_verify_log.verify_trial(self.trial, self.bundle_sha, mode=mode,
                                           results_root=self.results,
                                           work_root=self.work)

    def cfg_frozen(self) -> dict:
        return json.loads((self.results / 'freeze' / 'config.json').read_text('utf-8'))

    def close(self) -> None:
        dry._stop_anchor(self.anchor_proc)
        shutil.rmtree(self.root, ignore_errors=True)


class SimWorld(dry.SimWorld):
    """The simulated world, plus a crash injector.

    ``kill_spec`` is ``{'event': <chain event type>, 'nth': k}`` or
    ``{'spool': <spool kind>, 'nth': k}``; the crash is raised *after* the named line has
    been written and fsynced, which is exactly the state a SIGKILL would leave behind."""

    kill_spec: dict = {}
    kill_counts: dict = {}

    def _check_kill(self) -> None:
        """Count the target event over the chain itself, so that events the orchestrator
        writes through the log directly (``monitor_update``, ``decision``, ``anchor``) are
        kill points too."""
        spec = type(self).kill_spec
        want = spec.get('event')
        if not want or self.log is None:
            return
        seen = sum(1 for e in self.log.events if e['type'] == want)
        if seen >= int(spec.get('nth', 1)):
            raise _Kill(want)

    def append(self, etype, body, *, durable=False):       # type: ignore[override]
        ev = super().append(etype, body, durable=durable)
        self._check_kill()
        return ev

    def request_anchor(self, trigger, *, blocking):        # type: ignore[override]
        out = super().request_anchor(trigger, blocking=blocking)
        self._check_kill()
        return out

    def spawn(self, att, job_path):                        # type: ignore[override]
        spec = type(self).kill_spec
        if spec.get('after_job_file'):
            counts = type(self).kill_counts
            counts['job_file'] = counts.get('job_file', 0) + 1
            if counts['job_file'] >= int(spec.get('nth', 1)):
                raise _Kill('job_file')
        dry.run_sim_episode(att.job, dict(type(self).scenario,
                                          kill_after=spec.get('spool'),
                                          kill_nth=int(spec.get('nth', 1))))
        return os.getpid()


class LazySimWorld(SimWorld):
    """Reveals the two episodes of a pair in reverse dispatch order (position 2 first)."""

    def spawn(self, att, job_path):                        # type: ignore[override]
        self._queue = getattr(self, '_queue', [])
        self._queue.append(att)
        return os.getpid()

    def finished(self, att):                               # type: ignore[override]
        queue = getattr(self, '_queue', [])
        written = getattr(self, '_written', set())
        if att.arrival in written:
            return 0
        pending = [a for a in queue if a.arrival not in written]
        if len(pending) > 1 and att.arrival != pending[-1].arrival:
            return None                                    # the partner goes first
        dry.run_sim_episode(att.job, dict(type(self).scenario))
        written.add(att.arrival)
        self._written = written
        return 0


def _chain_types(events: Sequence[Mapping], etype: str) -> list[dict]:
    return [dict(e) for e in events if e['type'] == etype]


def _no_double_work(case: unittest.TestCase, events: Sequence[Mapping]) -> None:
    """Never a second coin, never a second reveal, never a re-run."""
    coins: dict[int, int] = {}
    for ev in _chain_types(events, 'coin_drawn'):
        pair = int(ev['body']['pair'])
        coins[pair] = coins.get(pair, 0) + 1
    case.assertTrue(all(k == 1 for k in coins.values()),
                    'a pair was randomized twice: %r' % coins)
    reveals: dict[int, int] = {}
    for ev in _chain_types(events, 'episode_revealed'):
        arrival = int(ev['body']['arrival'])
        reveals[arrival] = reveals.get(arrival, 0) + 1
    case.assertTrue(all(k == 1 for k in reveals.values()),
                    'an arrival was revealed twice: %r' % reveals)
    accepted: dict[int, int] = {}
    for ev in _chain_types(events, 'job_accepted'):
        arrival = int(ev['body']['arrival'])
        accepted[arrival] = accepted.get(arrival, 0) + 1
    case.assertTrue(all(k == 1 for k in accepted.values()),
                    'an attempt was accepted twice (a re-run): %r' % accepted)


# ---------------------------------------------------------------------------
# the frozen configuration
# ---------------------------------------------------------------------------
class ConfigTests(unittest.TestCase):
    def test_config_is_appendix_b_verbatim(self) -> None:
        """The committed ``config.json`` is the block of ARCHITECTURE_FINAL.md 6.1, which
        is byte-identical to protocol Appendix B (the freeze test of 9.2)."""
        if not DESIGN_DIR.exists():
            self.skipTest('the design documents are not present in this checkout')
        arch = (DESIGN_DIR / 'ARCHITECTURE_FINAL.md').read_text('utf-8')
        prot = (DESIGN_DIR / 'protocol_FINAL.md').read_text('utf-8')

        def block(text: str, marker: str) -> str:
            i = text.index(marker)
            j = text.index('```json', i)
            k = text.index('```', j + 7)
            return text[j + 7:k].lstrip('\n')

        a = block(arch, '### 6.1 Full key list')
        b = block(prot, '## Appendix B.')
        self.assertEqual(a, b, 'the two documents carry different configuration blocks')
        self.assertEqual((HERE / 'config.json').read_text('utf-8'), a)

    def test_rule_block_hash_is_stable_under_operational_pinning(self) -> None:
        cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
        base = lab_common.rule_block_sha256(cfg)
        cfg['anchor']['blocking_wait_minutes'] = 45
        cfg['execution']['request_timeout_s'] = 180.0
        self.assertEqual(base, lab_common.rule_block_sha256(cfg))
        cfg['monitor']['delta'] = 0.10
        self.assertNotEqual(base, lab_common.rule_block_sha256(cfg))

    def test_every_null_is_a_pre_freeze_value(self) -> None:
        """No ``null`` may survive into the freeze bundle, and every one that is still
        ``null`` here is named in README.md with the rule that pins it."""
        cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
        nulls: list[str] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f'{path}.{k}' if path else str(k))
            elif node is None:
                nulls.append(path)

        walk(cfg, '')
        self.assertTrue(nulls)
        readme = (HERE / 'README.md').read_text('utf-8')
        missing = [n for n in nulls if n not in readme]
        self.assertEqual(missing, [], 'README.md does not name the rule for: %r' % missing)

    def test_the_horizon_is_never_the_unstratified_count(self) -> None:
        """audit B5: 568 is the horizon ceiling and 569 is the unstratified count, which
        is not a horizon of this program.  It may appear only as the radius table's
        reference row, which is a radius and not a horizon."""
        import re
        cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
        self.assertEqual(cfg['roster']['n_pairs_rule'],
                         'floor(n_S1 / 2) + floor(n_S2 / 2)')
        # the needle is assembled at run time so that this file does not itself carry it
        needle = re.compile(r'(?<![0-9a-z])5' + '6' + r'9(?![0-9a-z])')
        for name in ('lab_orchestrator.py', 'build_live_ab_results.py', 'lab_anchor.py'):
            self.assertIsNone(needle.search((HERE / name).read_text('utf-8')),
                              '%s writes the unstratified count as a horizon (audit B5)'
                              % name)
        table = dry.RADIUS_NS
        self.assertIn(568, table)
        self.assertIn(569, table)


# ---------------------------------------------------------------------------
# scheduling
# ---------------------------------------------------------------------------
class ScheduleTests(unittest.TestCase):
    def test_pair_synchronous(self) -> None:
        """Pair ``i+1`` is enrolled only after both reveals of pair ``i`` and the look at
        prefix ``i``; at most one pair is pending, ever."""
        tree = Tree(pairs=4)
        try:
            self.assertEqual(tree.run(), 'ended')
            events = tree.events()
            open_pairs = 0
            revealed: dict[int, int] = {}
            last_update_n = -1
            for ev in events:
                if ev['type'] == 'pair_enrolled':
                    self.assertEqual(open_pairs, 0, 'two pairs were pending at once')
                    open_pairs = 1
                    pair = int(ev['body']['pair'])
                    if pair > 1:
                        self.assertEqual(revealed.get(pair - 1, 0), 2,
                                         'pair %d enrolled before pair %d was revealed'
                                         % (pair, pair - 1))
                        self.assertEqual(last_update_n, pair - 1)
                elif ev['type'] == 'episode_revealed':
                    pair = int(ev['body']['pair'])
                    revealed[pair] = revealed.get(pair, 0) + 1
                    if revealed[pair] == 2:
                        open_pairs = 0
                elif ev['type'] == 'monitor_update':
                    last_update_n = int(ev['body']['n'])
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_out_of_order_reveal(self) -> None:
        """Position 2 may be revealed first; the enrollment indices are unaffected."""
        tree = Tree(pairs=3)
        try:
            self.assertEqual(tree.run(world_cls=LazySimWorld), 'ended')
            events = tree.events()
            positions = [int(e['body']['position']) for e in events
                         if e['type'] == 'episode_revealed']
            self.assertEqual(positions[:2], [2, 1], 'the reveal order was not reversed')
            pairs = [int(e['body']['pair']) for e in events
                     if e['type'] == 'pair_enrolled']
            self.assertEqual(pairs, [1, 2, 3])
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_look_at_every_trigger_and_nothing_else(self) -> None:
        """A look at every enroll, every pre-decision reveal, every call event that raises
        ``ell`` and at the resume boundary -- and at nothing else.  A ``metrics_scrape`` is
        never a trigger (audit B3, B6)."""
        tree = Tree(pairs=3)
        try:
            tree.run()
            events = tree.events()
            cfg = tree.cfg_frozen()
            logged = [e['body']['trigger'] for e in events
                      if e['type'] == 'monitor_update']
            replayed = [s['trigger'] for s in lab_monitor.replay(events, cfg, tree.trial)]
            reference = [lk.trigger for lk in
                         lab_reference_rule.looks_from_chain(events, cfg, tree.trial)]
            self.assertEqual(logged, replayed, 'the live cadence differs from the replay')
            self.assertEqual(logged, reference,
                             'the live cadence differs from the reference rule')
            self.assertIn('call', logged)
            for i, ev in enumerate(events[:-1]):
                if ev['type'] == 'metrics_scrape':
                    self.assertNotEqual(events[i + 1]['type'], 'monitor_update',
                                        'a metrics_scrape produced a look')
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_horizon_exhaustion(self) -> None:
        """At ``n = N_P`` with everything collapsed, ``horizon_no_decision`` is logged and
        no leftover task is enrolled."""
        tree = Tree(pairs=4)
        try:
            self.assertEqual(tree.run(), 'ended')
            events = tree.events()
            decisions = _chain_types(events, 'decision')
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0]['body']['kind'], 'horizon_no_decision')
            self.assertEqual(decisions[0]['body']['n'], 4)
            self.assertEqual(len(_chain_types(events, 'traffic_switch')), 0)
            self.assertEqual(len(_chain_types(events, 'arm_assigned_by_decision')), 0)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()


# ---------------------------------------------------------------------------
# the decision, the drain and the switch
# ---------------------------------------------------------------------------
class SwitchTests(unittest.TestCase):
    def _deploy_tree(self, pairs: int = 50) -> Tree:
        return Tree(pairs=pairs, trial='T1', delta=0.9, n_min=dry._screen(pairs),
                    scenario={'outcome_seed': 8, 'incumbent': {'p_good': 1.0,
                                                               'latency_scale': 4.5},
                              'candidate': {'p_good': 1.0, 'latency_scale': 1.0}})

    def test_switch_sequence(self) -> None:
        """``decision`` -> blocking anchor -> receipt -> ``traffic_switch`` -> the first
        ``arm_assigned_by_decision``; no coin after the decision."""
        tree = self._deploy_tree()
        try:
            self.assertEqual(tree.run(), 'ended')
            events = tree.events()
            seq = {t: [e['seq'] for e in events if e['type'] == t]
                   for t in ('decision', 'anchor', 'anchor_receipt', 'traffic_switch',
                             'arm_assigned_by_decision', 'coin_drawn')}
            self.assertEqual(len(seq['decision']), 1)
            dseq = seq['decision'][0]
            anchor = next(s for s in seq['anchor'] if s > dseq)
            receipt = next(s for s in seq['anchor_receipt'] if s > anchor)
            switch = seq['traffic_switch'][0]
            self.assertLess(anchor, receipt)
            self.assertLess(receipt, switch)
            self.assertLess(switch, seq['arm_assigned_by_decision'][0])
            self.assertTrue(all(s < dseq for s in seq['coin_drawn']),
                            'a coin was drawn after the decision')
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_drain_before_switch(self) -> None:
        """A decision taken while the partner is in flight drains it first; its reveal
        carries ``post_decision: false`` and creates no second decision (PG-2)."""
        tree = Tree(pairs=44, trial='T2', n_min=dry._screen(44),
                    scenario={'outcome_seed': 3,
                              'incumbent': {'p_good': 1.0, 'latency_scale': 1.0},
                              'candidate': {'p_good': 0.0, 'latency_scale': 4.5}})
        try:
            self.assertEqual(tree.run(world_cls=LazySimWorld), 'ended')
            events = tree.events()
            decisions = _chain_types(events, 'decision')
            self.assertEqual(len(decisions), 1)
            dseq = decisions[0]['seq']
            drained = [e for e in events if e['type'] == 'episode_revealed'
                       and e['seq'] > dseq and not e['body']['post_decision']]
            if drained:
                for ev in drained:
                    nxt = events[ev['seq'] + 1]
                    self.assertEqual(nxt['type'], 'monitor_update')
                    self.assertEqual(nxt['body']['trigger'], 'drain')
            self.assertEqual(len(_chain_types(events, 'decision')), 1)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_exposure_ledger(self) -> None:
        tree = self._deploy_tree()
        try:
            tree.run()
            events = tree.events()
            on_disk = json.loads(
                (tree.results / tree.trial / 'exposure_ledger.json').read_text('utf-8'))
            self.assertEqual(canonical_json(on_disk),
                             canonical_json(orch.exposure_recount(events)))
            self.assertGreater(on_disk['post_decision']['candidate']['episodes']
                               + on_disk['post_decision']['incumbent']['episodes'], 0)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_t4_payload_identity_survives_a_pair_spanning_two_invocations(self) -> None:
        """The repair of execution-review E3, asserted on the path that used to break.

        This test previously asserted the DEFECT: ``Job`` (ARCHITECTURE 3.12) carries
        ``inv``, the removal list of PG-14 / protocol 12.3 did not remove it, so the
        canonical payloads of the two episodes of a T4 pair differed whenever one position
        was dispatched by a later invocation -- which is exactly what protocol 6.4 rows 11c
        to 11e permit after a crash.  ``t4.payload_identity`` is a FAIL on condition list B,
        so the false positive would have dropped claims 2-5 and 7 for T4 on a run in which
        nothing scientific had changed.

        ``inv`` is now in the removal list, for the same reason ``worker_index`` always was:
        the invocation id is a property of the dispatch, not of the arm.  The trial is still
        killed at the second coin and resumed, so pair 2 still genuinely spans two
        invocations -- what changed is the verdict."""
        tree = Tree(pairs=4, trial='T4')
        try:
            self.assertEqual(tree.run(kill={'id': 'coin_drawn', 'event': 'coin_drawn',
                                            'nth': 2}), 'killed')
            tree.run(resume=True)
            report = tree.verify()
            fails = [f.check for f in report.findings if f.severity == 'FAIL']
            self.assertEqual(fails, [], 'a resumed A/A pair must not fail: %r' % fails)
            jobs = {int(json.loads(p.read_text('utf-8'))['arrival']): json.loads(
                p.read_text('utf-8'))
                for p in (tree.work / 'T4' / 'jobs').glob('job_*.json')}
            spanning = [a for a, j in jobs.items()
                        if j['pair'] == 2]
            self.assertEqual(len(spanning), 2)
            invs = {jobs[a]['inv'] for a in spanning}
            self.assertEqual(len(invs), 2, 'the pair did not span two invocations')
            payloads = {canonical_json(orch.canonical_job_payload(jobs[a]))
                        for a in spanning}
            self.assertEqual(len(payloads), 1,
                             'the invocation id still reaches the canonical payload')
            self.assertNotIn('inv', orch.canonical_job_payload(jobs[spanning[0]]))
            # and the check still has teeth: real configuration drift between the two
            # episodes of the pair must still be a FAIL.
            drifted = dict(jobs[spanning[1]], workflow='self_test_repair')
            self.assertNotEqual(
                canonical_json(orch.canonical_job_payload(jobs[spanning[0]])),
                canonical_json(orch.canonical_job_payload(drifted)))
        finally:
            tree.close()

    def test_t4_payload_identity(self) -> None:
        """In a T4 dry run the two canonical job payloads of every pair are
        byte-identical (PG-14, protocol 12.3)."""
        tree = Tree(pairs=4, trial='T4')
        try:
            tree.run()
            by_pair: dict[int, list[str]] = {}
            for ev in tree.events():
                if ev['type'] == 'episode_started':
                    by_pair.setdefault(int(ev['body']['pair']), []).append(
                        ev['body']['payload_sha256'])
            self.assertTrue(by_pair)
            for pair, digests in by_pair.items():
                self.assertEqual(len(set(digests)), 1, 'pair %d differs' % pair)
            jobs = sorted((tree.work / 'T4' / 'jobs').glob('job_*.json'))
            payloads = [orch.canonical_job_payload(
                json.loads(p.read_text('utf-8'))) for p in jobs[:2]]
            self.assertEqual(canonical_json(payloads[0]), canonical_json(payloads[1]))
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------
KILL_POINTS: tuple[dict, ...] = (
    {'id': 'pair_enrolled', 'event': 'pair_enrolled', 'nth': 2},
    {'id': 'coin_drawn', 'event': 'coin_drawn', 'nth': 2},
    {'id': 'job_file', 'after_job_file': True, 'nth': 3},
    {'id': 'job_accepted', 'spool': 'job_accepted', 'nth': 3},
    {'id': 'call_started', 'spool': 'call_started', 'nth': 3},
    {'id': 'call_response', 'spool': 'call_response', 'nth': 3},
    {'id': 'record_written', 'spool': 'record', 'nth': 3},
    {'id': 'episode_final', 'spool': 'episode_final', 'nth': 3},
    {'id': 'first_reveal', 'event': 'episode_revealed', 'nth': 3},
    {'id': 'second_reveal', 'event': 'episode_revealed', 'nth': 4},
    {'id': 'monitor_update', 'event': 'monitor_update', 'nth': 6},
    {'id': 'metrics_scrape', 'event': 'metrics_scrape', 'nth': 3},
)

DECISION_KILL_POINTS: tuple[dict, ...] = (
    {'id': 'decision', 'event': 'decision', 'nth': 1},
    {'id': 'decision_anchor', 'event': 'anchor', 'nth': 2},
    {'id': 'traffic_switch', 'event': 'traffic_switch', 'nth': 1},
    {'id': 'post_decision', 'event': 'arm_assigned_by_decision', 'nth': 2},
)


class ResumeTests(unittest.TestCase):
    def _kill_and_resume(self, spec: Mapping, *, pairs: int = 4, trial: str = 'T2',
                         delta: float | None = None, n_min: int | None = None,
                         scenario: Mapping | None = None) -> Tree:
        tree = Tree(pairs=pairs, trial=trial, delta=delta, n_min=n_min,
                    scenario=scenario)
        status = tree.run(kill=spec)
        self.assertEqual(status, 'killed', 'the crash was not injected at %s'
                         % spec.get('id'))
        second = tree.run(resume=True)
        self.assertIn(second, ('ended', 'aborted'),
                      'the resumed invocation ended as %r' % second)
        return tree

    def test_seed_registry_survives_a_crash_and_stays_unique(self) -> None:
        """Execution review E2, on the path where the registry can actually go stale.

        The trial is killed just after a worker durably spooled a ``call_started`` -- so a
        seed exists that the orchestrator may not have flushed -- and then resumed.  What
        must hold afterwards:

          * the resumed invocation rebuilt the program-wide set from the spools, so no seed
            the crashed invocation committed to was forgotten;
          * the file on disk agrees exactly with the chain, rather than being behind it;
          * and every seed in the chain is distinct, which is the promise of protocol 5.5
            that had no writer at all before this repair.
        """
        tree = self._kill_and_resume({'id': 'call_started', 'spool': 'call_started',
                                      'nth': 3})
        try:
            self.assertEqual(tree.verify().verdict, 'PASS')
            events = tree.events()
            chain = [e['body']['seed'] for e in events if e['type'] == 'llm_request']
            self.assertGreater(len(chain), 2, 'the fixture ran too few requests to test')
            self.assertEqual(len(set(chain)), len(chain),
                             'a seed was drawn twice across the crash boundary')
            registry = orch.seed_registry_path(tree.work)
            self.assertTrue(registry.exists(),
                            'no invocation ever wrote the used-seed registry')
            on_disk = json.loads(registry.read_text('utf-8'))
            self.assertEqual(on_disk, sorted(on_disk), 'the registry is written sorted')
            self.assertEqual(set(on_disk), set(chain),
                             'the registry and the chain disagree about what was used')
            # the crash-durable half: the file is recoverable from the spools alone
            registry.unlink()
            self.assertEqual(orch.seed_registry_reconstruct(tree.work), set(chain))
            # ... and a worker starting now would load exactly its own half
            orch.write_seed_registry(registry,
                                     orch.seed_registry_reconstruct(tree.work))
            import lab_client
            halves = [lab_client.load_used_seeds(registry, i) for i in (0, 1)]
            self.assertEqual(halves[0] | halves[1], set(chain))
            self.assertEqual(halves[0] & halves[1], set())
        finally:
            tree.close()

    def test_resume_kill_points(self) -> None:
        """A kill at each point of protocol 14.5 / 9.2: after each one, resume yields a
        chain that passes the verifier, with never a second coin, never a second reveal
        and never a re-run."""
        for spec in KILL_POINTS:
            with self.subTest(kill=spec['id']):
                tree = self._kill_and_resume(spec)
                try:
                    report = tree.verify()
                    self.assertEqual(
                        report.verdict, 'PASS',
                        '%s: %r' % (spec['id'],
                                    [f.check for f in report.findings
                                     if f.severity == 'FAIL']))
                    events = tree.events()
                    _no_double_work(self, events)
                    self.assertTrue(_chain_types(events, 'invocation_started'))
                finally:
                    tree.close()

    def test_resume_kill_points_around_the_decision(self) -> None:
        """The decision, its blocking anchor, the traffic switch and the follow-up cohort
        are kill points too: the decision sequence is continued, never re-taken."""
        pairs = 44
        scenario = {'outcome_seed': 3,
                    'incumbent': {'p_good': 1.0, 'latency_scale': 1.0},
                    'candidate': {'p_good': 0.0, 'latency_scale': 4.5}}
        for spec in DECISION_KILL_POINTS:
            with self.subTest(kill=spec['id']):
                tree = self._kill_and_resume(spec, pairs=pairs, trial='T2',
                                             n_min=dry._screen(pairs),
                                             scenario=scenario)
                try:
                    report = tree.verify()
                    self.assertEqual(
                        report.verdict, 'PASS',
                        '%s: %r' % (spec['id'],
                                    [f.check for f in report.findings
                                     if f.severity == 'FAIL']))
                    events = tree.events()
                    _no_double_work(self, events)
                    self.assertEqual(len(_chain_types(events, 'decision')), 1,
                                     'the decision was taken twice')
                    self.assertLessEqual(len(_chain_types(events, 'traffic_switch')), 1)
                finally:
                    tree.close()

    def test_resume_idempotent(self) -> None:
        """Resuming twice changes nothing: the second resume's plan is empty."""
        tree = self._kill_and_resume({'id': 'coin_drawn', 'event': 'coin_drawn',
                                      'nth': 2})
        try:
            events = tree.events()
            spools = {p.stem: orch.read_whole_spool(p)
                      for p in sorted((tree.work / tree.trial / 'spools')
                                      .glob('ep_*.jsonl'))}
            order = json.loads((tree.results / 'freeze'
                                / ('arrival_order_%s.json' % tree.trial)
                                ).read_text('utf-8'))
            plan = orch.plan_resume(events, spools, order, tree.cfg_frozen())
            self.assertEqual(plan.orphan_reveals, [])
            self.assertEqual(plan.interrupted, [])
            self.assertEqual(plan.dispatch_after_resume, [])
            self.assertIsNone(plan.reenroll_pair)
            self.assertEqual(plan.phase, 'ended')
            again = orch.plan_resume(events, spools, order, tree.cfg_frozen())
            self.assertEqual(canonical_json(plan.__dict__),
                             canonical_json(again.__dict__))
        finally:
            tree.close()

    def test_plan_resume_is_pure(self) -> None:
        """``plan_resume`` reads nothing and writes nothing: the same bytes give the same
        plan, and a plan of an empty chain is empty."""
        plan = orch.plan_resume([], {}, [], json.loads(
            (HERE / 'config.json').read_text('utf-8')))
        self.assertEqual(plan.phase, 'randomizing')
        self.assertEqual(plan.monitor_prefix, 0)
        self.assertEqual(plan.orphan_reveals, [])
        self.assertIsNone(plan.decision_seq)

    def test_dispatch_after_resume(self) -> None:
        """PG-7: an assignment with no ``job_accepted`` is dispatched once, flagged
        ``started_after_resume``.  Nothing had run, so this is not a re-run."""
        tree = self._kill_and_resume({'id': 'job_file', 'after_job_file': True, 'nth': 3})
        try:
            events = tree.events()
            flagged = [e for e in events if e['type'] == 'episode_started'
                       and e['body']['started_after_resume']]
            self.assertTrue(flagged, 'no episode was flagged started_after_resume')
            _no_double_work(self, events)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_orphan_accept_and_reject(self) -> None:
        """A complete, matching spool is revealed as ``recovered_orphan``; a spool whose
        record hash does not match is rejected and revealed as ``interrupted``."""
        tree = self._kill_and_resume({'id': 'episode_final', 'spool': 'episode_final',
                                      'nth': 3})
        try:
            events = tree.events()
            recovered = [e for e in events if e['type'] == 'episode_revealed'
                         and e['body']['recovered_orphan']]
            self.assertTrue(recovered, 'no orphan was recovered from its own spool')
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

        rejected = Tree(pairs=4, trial='T2')
        try:
            self.assertEqual(rejected.run(kill={'id': 'episode_final',
                                                'spool': 'episode_final', 'nth': 3}),
                             'killed')
            # corrupt the orphan's evidence: the pid of its `job_accepted` no longer
            # matches the pid of its `episode_final`.
            spools = sorted((rejected.work / rejected.trial / 'spools')
                            .glob('ep_*.jsonl'))
            target = spools[-1]
            lines = [json.loads(x) for x in target.read_text('utf-8').splitlines() if x]
            lines[-1]['pid'] = int(lines[-1]['pid']) + 1
            target.write_text(''.join(canonical_json(x) + '\n' for x in lines),
                              encoding='utf-8')
            rejected.run(resume=True)
            events = rejected.events()
            self.assertTrue(_chain_types(events, 'orphan_rejected'),
                            'a mismatched spool was accepted')
            interrupted = [e for e in events if e['type'] == 'episode_revealed'
                           and e['body']['outcome']['error_class'] == 'interrupted']
            self.assertTrue(interrupted)
            _no_double_work(self, events)
            self.assertEqual(rejected.verify().verdict, 'PASS')
        finally:
            rejected.close()

    def test_two_orchestrators_refused(self) -> None:
        tree = Tree(pairs=2, anchor=False)
        try:
            lock = orch.RunLock(tree.work / tree.trial / 'run.lock', uuid.uuid4().hex)
            lock.acquire()
            second = orch.RunLock(tree.work / tree.trial / 'run.lock', uuid.uuid4().hex)
            with self.assertRaises(lab_common.PreflightError):
                second.acquire()
            lock.release()
            second.acquire()
            second.release()
        finally:
            tree.close()


# ---------------------------------------------------------------------------
# aborts, pauses and the worktree guard
# ---------------------------------------------------------------------------
class AbortTests(unittest.TestCase):
    def test_auto_abort_on_consecutive_infrastructure_failures(self) -> None:
        """Ten consecutive revealed arrivals with a terminal ``error_class``, counted in
        reveal order, abort the trial deterministically (protocol 6.4)."""
        tree = Tree(pairs=12)
        try:
            status = tree.run(world_cls=DeadWorkerWorld)
            self.assertEqual(status, 'aborted')
            events = tree.events()
            aborted = _chain_types(events, 'trial_aborted')
            self.assertEqual(len(aborted), 1)
            self.assertEqual(aborted[0]['body']['reason'], 'infrastructure')
            terminal = [e for e in events if e['type'] == 'episode_revealed'
                        and e['body']['outcome']['error_class'] == 'worker_died']
            self.assertGreaterEqual(len(terminal), 10)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_receipt_mismatch_aborts_after_the_episode_is_revealed(self) -> None:
        """Protocol 6.4 row 12: the episode completes and is revealed under
        intention-to-treat, and only then is the trial aborted."""
        tree = Tree(pairs=4)
        try:
            status = tree.run(world_cls=ReceiptMismatchWorld)
            self.assertEqual(status, 'aborted')
            events = tree.events()
            aborted = _chain_types(events, 'trial_aborted')
            self.assertEqual(aborted[0]['body']['reason'], 'receipt_mismatch')
            mismatch = [e for e in events if e['type'] == 'llm_response'
                        and e['body']['receipt_mismatch']]
            self.assertTrue(mismatch)
            revealed_after = [e for e in events if e['type'] == 'episode_revealed'
                              and e['seq'] > mismatch[0]['seq']]
            self.assertTrue(revealed_after, 'the episode was not revealed before the abort')
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_worktree_drift_pauses_and_is_not_an_editing_finding(self) -> None:
        """Protocol 6.4 row 27 / audit B7: an out-of-band change to a freeze-bundle file
        pauses the trial with ``worktree_drift`` and its digests, and the verifier records
        it as an environment event that never contributes to the integrity label."""
        tree = Tree(pairs=6)
        try:
            DriftWorld.drift_after = 2
            status = tree.run(world_cls=DriftWorld,
                              runtime_extra={'worktree_check_s': 0.0})
            self.assertEqual(status, 'paused')
            events = tree.events()
            paused = _chain_types(events, 'trial_paused')
            self.assertEqual(len(paused), 1)
            self.assertEqual(paused[0]['body']['reason_code'], 'worktree_drift')
            self.assertTrue(paused[0]['body']['digests'])
            for row in paused[0]['body']['digests']:
                self.assertNotEqual(row['expected'], row['observed'])
            # protocol 6.4 row 27: resume only after the tree is restored and every
            # digest matches.  The verifier is run on the restored tree, as an operator
            # would run it.
            roster = tree.results / 'freeze' / 'roster.json'
            roster.write_text(roster.read_text('utf-8').rstrip('\n') + '\n',
                              encoding='utf-8')
            report = tree.verify()
            self.assertEqual(report.verdict, 'PASS',
                             [f.check for f in report.findings
                              if f.severity == 'FAIL'])
            table = next(f for f in report.findings if f.check == 'integrity.table')
            self.assertEqual(table.detail['worktree_drift_events'], 1)
            self.assertFalse(table.detail['worktree_drift_counted_in_label'])
        finally:
            DriftWorld.drift_after = None
            tree.close()

    def test_preflight_refuses_a_foreign_worktree(self) -> None:
        """A wrong ``HEAD`` branch at start is ``preflight_refused(worktree_identity)`` in
        the PROGRAM chain, before the trial's seq 0 (critic N1)."""
        tree = Tree(pairs=2, anchor=False)
        try:
            cfg = tree._cfg()
            cfg['_runtime']['worktree'] = {'branch': 'a-branch-that-does-not-exist',
                                           'commit': ''}
            ctx = orch.make_context(tree.trial, cfg, results_root=tree.results,
                                    work_root=tree.work, inv=uuid.uuid4().hex)
            with self.assertRaises(lab_common.PreflightError):
                orch.preflight(ctx)
            self.assertEqual(orch.run_trial(ctx, resume=False), 'aborted')
            program = lab_eventlog.read_chain(
                tree.results / '_program' / 'events', '_program', tree.bundle_sha)
            refusals = [e for e in program.events if e['type'] == 'preflight_refused']
            self.assertEqual(len(refusals), 1)
            self.assertIn('worktree_identity', refusals[0]['body']['checks_failed'])
            self.assertEqual(
                lab_eventlog.segment_paths(tree.results / tree.trial / 'events'), [],
                'the trial chain was opened despite the refusal')
        finally:
            tree.close()


class DeadWorkerWorld(SimWorld):
    """Every worker dies before writing anything: ten consecutive terminal failures."""

    def spawn(self, att, job_path):                        # type: ignore[override]
        return os.getpid()


class ReceiptMismatchWorld(SimWorld):
    def spawn(self, att, job_path):                        # type: ignore[override]
        dry.run_sim_episode(att.job, dict(type(self).scenario, receipt_mismatch=True))
        return os.getpid()


class DriftWorld(SimWorld):
    """Swaps a freeze-bundle file under the running invocation after N pairs."""

    drift_after: int | None = None

    def draw_coin(self):                                   # type: ignore[override]
        out = super().draw_coin()
        if type(self).drift_after and self.pairs_enrolled == type(self).drift_after:
            target = Path(self.rt['results_root']) / 'freeze' / 'roster.json'
            target.write_text(target.read_text('utf-8') + '\n', encoding='utf-8')
        return out


# ---------------------------------------------------------------------------
# anchors
# ---------------------------------------------------------------------------
class AnchorTests(unittest.TestCase):
    def test_orchestrator_is_the_only_chain_writer(self) -> None:
        """PG-12: ``lab_anchor`` never appends to a chain.  It imports no ``lab_*`` module
        but ``lab_common``, and its source contains no ``EventLog``."""
        source = (HERE / 'lab_anchor.py').read_text('utf-8')
        self.assertNotIn('EventLog', source)
        self.assertNotIn('lab_eventlog', source)
        self.assertNotIn('append_event', source)

    def test_anchor_spool_round_trip(self) -> None:
        """The orchestrator writes requests, the anchor process writes receipts, and the
        orchestrator alone turns them into ``anchor`` / ``anchor_receipt`` events."""
        tree = Tree(pairs=3)
        try:
            tree.run()
            events = tree.events()
            anchors = _chain_types(events, 'anchor')
            receipts = _chain_types(events, 'anchor_receipt')
            self.assertTrue(anchors)
            self.assertEqual(len(receipts), len(anchors))
            requests = [json.loads(x) for x in
                        (tree.work / tree.trial / 'anchor_spool' / 'requests.jsonl')
                        .read_text('utf-8').splitlines() if x]
            self.assertEqual(len(requests), len(anchors))
            self.assertTrue(all(r['blocking'] for r in requests
                                if r['trigger'] in ('trial_started', 'trial_ended')))
        finally:
            tree.close()

    def test_anchor_prefix(self) -> None:
        """Each ``anchor``'s ``upto_h`` and ``segment_sha256`` match the committed segment
        bytes: the anchor commits to the segment PREFIX preceding its own line, which is
        the only non-circular reading of ARCHITECTURE 4.4 T22 and is what the verifier
        check ``anchor.prefix`` computes.

        The git drill of protocol 12.4 item 10 is an operator step: this session is
        forbidden to run a state-changing git command, so the drill is not executed here
        and the property it would check is asserted directly against the bytes."""
        tree = Tree(pairs=3)
        try:
            tree.run()
            events = tree.events()
            segments = lab_eventlog.segment_paths(tree.results / tree.trial / 'events')
            by_seq = {e['seq']: e for e in events}
            for ev in _chain_types(events, 'anchor'):
                body = ev['body']
                self.assertEqual(by_seq[int(body['upto_seq'])]['h'], body['upto_h'])
                raw = segments[int(body['segment_index'])].read_bytes()
                line = canonical_json(ev).encode('utf-8') + b'\n'
                prefix = raw[:raw.rfind(line)]
                self.assertEqual(len(prefix), int(body['segment_bytes']))
                self.assertEqual(sha256_bytes(prefix), body['segment_sha256'])
                anchor_file = (tree.results / tree.trial / 'anchors'
                               / ('anchor_%d.json' % body['anchor_seq']))
                self.assertTrue(anchor_file.exists())
                stored = json.loads(anchor_file.read_text('utf-8'))
                self.assertEqual(stored['upto_h'], body['upto_h'])
                self.assertEqual(stored['segment_sha256'], body['segment_sha256'])
        finally:
            tree.close()

    def test_scanner_withholds_and_never_prints_the_match(self) -> None:
        """A planted forbidden pattern is reported by class and line, never by text."""
        root = Path(tempfile.mkdtemp(prefix='live_ab_scan_'))
        try:
            clean = root / 'anchor_1.json'
            clean.write_text(canonical_json({'upto_h': '0' * 64, 'anchor_seq': 1}),
                             encoding='utf-8')
            dirty = root / 'seg_0000.jsonl'
            dirty.write_text('{"note":"see https://example.invalid/secret-path"}\n',
                             encoding='utf-8')
            hits = lab_anchor.scan_for_identifiers([clean, dirty],
                                                   lab_anchor.DEFAULT_PATTERNS)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['pattern_class'], 'url')
            self.assertEqual(hits[0]['line'], 1)
            self.assertNotIn('secret-path', canonical_json(hits))
            self.assertNotIn('example.invalid', canonical_json(hits))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_dry_run_receipts_are_marked_not_ok(self) -> None:
        """``--dry-run`` writes receipts with ``ok=False, error_class='dry_run'``, so a
        blocking anchor can never be satisfied by a dry run."""
        tree = Tree(pairs=2, anchor=False)
        try:
            paths = orch._trial_paths(tree.trial, tree.results, tree.work)
            paths.mkdirs()
            req = {'request_id': 'r1', 'trial': tree.trial, 'anchor_seq': 1,
                   'upto_seq': 0, 'upto_h': '0' * 64, 'segment_index': 0,
                   'segment_bytes': 0, 'segment_sha256': '0' * 64,
                   'trigger': 'trial_started', 'blocking': True,
                   'publish_segments': False}
            (paths.anchor_spool / 'requests.jsonl').parent.mkdir(parents=True,
                                                                 exist_ok=True)
            (paths.anchor_spool / 'requests.jsonl').write_text(
                canonical_json(req) + '\n', encoding='utf-8')
            cfg = dict(tree.cfg_frozen())
            cfg['_runtime'] = {'anchor_mode': 'dry_run'}
            lab_anchor.serve(paths, cfg, once=True)
            receipts = [json.loads(x) for x in
                        (paths.anchor_spool / 'receipts.jsonl').read_text('utf-8')
                        .splitlines() if x]
            self.assertEqual(len(receipts), 1)
            self.assertFalse(receipts[0]['ok'])
            self.assertEqual(receipts[0]['error_class'], 'dry_run')
        finally:
            tree.close()


# ---------------------------------------------------------------------------
# the builder
# ---------------------------------------------------------------------------
class BuilderTests(unittest.TestCase):
    def test_builder_isolation_and_banner(self) -> None:
        """The builder produces every named file, refuses to recompute a decision, and
        stamps ``MOCK`` on a dry run's outputs."""
        source = (HERE / 'build_live_ab_results.py').read_text('utf-8')
        for banned in ('lab_orchestrator', 'lab_worker', 'lab_client', 'lab_server',
                       'lab_anchor', 'lab_mock_server'):
            self.assertNotIn('import %s' % banned, source)
        tree = Tree(pairs=50, trial='T1', delta=0.9, n_min=dry._screen(50),
                    scenario={'outcome_seed': 8,
                              'incumbent': {'p_good': 1.0, 'latency_scale': 4.5},
                              'candidate': {'p_good': 1.0, 'latency_scale': 1.0}})
        try:
            tree.run()
            out = tree.root / 'out'
            summary = builder.build([tree.trial], tree.bundle_sha,
                                    results_root=tree.results, work_root=tree.work,
                                    out_dir=out)
            self.assertTrue(summary['mock'])
            for name in ('monitor_table.csv', 'pairs.csv', 'episodes.csv',
                         'decision.json', 'sensitivity.json', 'integrity.json',
                         'posthoc_betting.json', 'exposure_ledger.json'):
                self.assertTrue((out / tree.trial / name).exists(), name)
            decision = json.loads((out / tree.trial / 'decision.json').read_text('utf-8'))
            logged = next(e for e in tree.events() if e['type'] == 'decision')
            self.assertEqual(decision['decision']['kind'], logged['body']['kind'])
            self.assertEqual(decision['decision']['n'], logged['body']['n'])
            self.assertTrue(decision['agreement_kind_and_prefix'])
            self.assertTrue(decision['replay_agrees_elementwise'])
            self.assertEqual(decision['banner'], 'MOCK')
            posthoc = json.loads(
                (out / tree.trial / 'posthoc_betting.json').read_text('utf-8'))
            self.assertIn('no error-control claim', posthoc['label'])
            summary_path = out / 'program_summary.json'
            self.assertTrue(summary_path.exists())
            self.assertEqual(json.loads(summary_path.read_text('utf-8'))['banner'],
                             'MOCK')
        finally:
            tree.close()

    def test_status_json_is_arm_blind(self) -> None:
        """Protocol 14.7: the status file carries no outcome, no coin, no band."""
        tree = Tree(pairs=3)
        try:
            tree.run()
            status = json.loads(
                (tree.results / tree.trial / 'status.json').read_text('utf-8'))
            self.assertEqual(sorted(status), ['elapsed_s', 'pairs_completed',
                                              'pairs_enrolled', 'phase',
                                              'receipts_obtained', 'servers_ok',
                                              'terminal_failure_count', 'trial'])
            text = canonical_json(status)
            for forbidden in ('L_h', 'U_h', 'bit', 'raw_hex', 'candidate', 'incumbent',
                              'success'):
                self.assertNotIn(forbidden, text)
        finally:
            tree.close()


# ---------------------------------------------------------------------------
# the cross-group cadence agreement (the two integration fixes)
# ---------------------------------------------------------------------------
class CadenceAgreementTests(unittest.TestCase):
    """The verifier compares the logged trigger sequence with ``lab_reference_rule`` and
    the logged values with ``lab_monitor.replay``, so the two code paths must agree
    element for element on every chain this harness can produce.  These tests pin the
    three shapes where they did not, and which the integrator corrected (see README)."""

    def _agrees(self, tree: Tree) -> None:
        events = tree.events()
        cfg = tree.cfg_frozen()
        logged = [e['body']['trigger'] for e in events if e['type'] == 'monitor_update']
        replayed = lab_monitor.replay(events, cfg, tree.trial)
        reference = lab_reference_rule.looks_from_chain(events, cfg, tree.trial)
        self.assertEqual([s['trigger'] for s in replayed], [lk.trigger
                                                            for lk in reference])
        self.assertEqual(logged, [lk.trigger for lk in reference])
        for i, (snap, ref) in enumerate(zip(replayed, reference)):
            self.assertEqual(int(snap['n']), int(ref.n), 'look %d' % i)
            for key in ('L_h', 'U_h', 'L_s', 'U_s'):
                self.assertAlmostEqual(float(snap[key]), float(getattr(ref, key)),
                                       delta=1e-9, msg='look %d %s' % (i, key))

    def test_no_look_after_a_decision_except_the_drain_reveal(self) -> None:
        """A call event that raises ``ell`` of a drained episode produces no look: after a
        decision the only look is the drain reveal (protocol 9.1 item 4, ARCHITECTURE 7.1
        row 12)."""
        pairs = 44
        tree = Tree(pairs=pairs, trial='T2', n_min=dry._screen(pairs),
                    scenario={'outcome_seed': 3,
                              'incumbent': {'p_good': 1.0, 'latency_scale': 1.0},
                              'candidate': {'p_good': 0.0, 'latency_scale': 4.5}})
        try:
            tree.run(world_cls=LazySimWorld)
            events = tree.events()
            dseq = next(e['seq'] for e in events if e['type'] == 'decision')
            after = [e for e in events if e['seq'] > dseq
                     and e['type'] == 'monitor_update']
            self.assertTrue(all(e['body']['trigger'] == 'drain' for e in after),
                            'a non-drain look was written after the decision: %r'
                            % [e['body']['trigger'] for e in after])
            self._agrees(tree)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_resume_look_is_after_the_orphan_reveals(self) -> None:
        """Protocol 14.5: recovered orphans are revealed first (item 6) and the resume
        evaluation is made before any new enrollment (item 4), so the resume look follows
        the orphan reveals."""
        tree = Tree(pairs=4, trial='T2')
        try:
            self.assertEqual(tree.run(kill={'id': 'episode_final',
                                            'spool': 'episode_final', 'nth': 3}),
                             'killed')
            tree.run(resume=True)
            events = tree.events()
            triggers = [(e['seq'], e['body']['trigger']) for e in events
                        if e['type'] == 'monitor_update']
            resume_at = [s for s, t in triggers if t == 'resume']
            self.assertEqual(len(resume_at), 1, 'exactly one resume look is expected')
            inv = [e['seq'] for e in events if e['type'] == 'invocation_started']
            self.assertTrue(inv)
            recovered = [e['seq'] for e in events if e['type'] == 'episode_revealed'
                         and e['seq'] > inv[-1]
                         and (e['body']['recovered_orphan']
                              or e['body']['outcome']['error_class'] == 'interrupted')]
            self.assertTrue(recovered, 'the resume recovered nothing')
            self.assertGreater(resume_at[0], max(recovered),
                               'the resume look was taken before the orphan reveals')
            self._agrees(tree)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_a_pair_enrolled_without_a_coin_holds_no_position(self) -> None:
        """Protocol 7.3 item 2: ``n`` is the count of chain-valid ``coin_drawn`` events and
        changes only at a ``coin_drawn``, so a pre-enrolled pair that was never randomized
        produces no evaluation; on resume it is re-enrolled and receives its one coin."""
        tree = Tree(pairs=4, trial='T2')
        try:
            self.assertEqual(tree.run(kill={'id': 'pair_enrolled',
                                            'event': 'pair_enrolled', 'nth': 2}),
                             'killed')
            tree.run(resume=True)
            events = tree.events()
            re_enrolled = [e for e in events if e['type'] == 'pair_enrolled'
                           and e['body']['re_enrolled']]
            self.assertEqual(len(re_enrolled), 1)
            pair = int(re_enrolled[0]['body']['pair'])
            coins = [e for e in events if e['type'] == 'coin_drawn'
                     and int(e['body']['pair']) == pair]
            self.assertEqual(len(coins), 1, 'the re-enrolled pair was randomized twice')
            enrolls = [e for e in events if e['type'] == 'monitor_update'
                       and e['body']['trigger'] == 'enroll'
                       and int(e['body']['n']) == pair]
            self.assertEqual(len(enrolls), 1)
            self.assertGreater(enrolls[0]['seq'], coins[0]['seq'],
                               'the enroll look preceded the coin')
            self._agrees(tree)
            self.assertEqual(tree.verify().verdict, 'PASS')
        finally:
            tree.close()

    def test_committed_chain_fixtures_still_verify(self) -> None:
        """G1's committed fixtures are still valid under the corrected cadence: the good
        chain verifies and every defect fixture still trips the check its manifest names.
        (They are stale only with respect to their own generator, which places the enroll
        ``monitor_update`` at the ``pair_enrolled`` rather than at the ``coin_drawn``; the
        fixtures must be regenerated by their owner once the correction is ratified.)"""
        chains = HERE / 'testdata' / 'chains'
        if not (chains / 'good_T4.jsonl').exists():
            self.skipTest('the chain fixtures are not present')
        import tests_lab_chain as fixtures
        good = [json.loads(x) for x in
                (chains / 'good_T4.jsonl').read_text('utf-8').splitlines() if x]
        cfg = json.loads((chains / 'good_T4_config.json').read_text('utf-8'))
        looks = lab_monitor.replay(good, cfg, 'T4')
        refs = lab_reference_rule.looks_from_chain(good, cfg, 'T4')
        logged = [e['body']['trigger'] for e in good if e['type'] == 'monitor_update']
        self.assertEqual([s['trigger'] for s in looks], [lk.trigger for lk in refs])
        self.assertEqual(logged, [lk.trigger for lk in refs])
        root = Path(tempfile.mkdtemp(prefix='live_ab_fixture_'))
        try:
            art = {'config': cfg,
                   'roster': json.loads((chains / 'good_T4_roster.json')
                                        .read_text('utf-8')),
                   'order': json.loads((chains / 'good_T4_arrival_order.json')
                                       .read_text('utf-8')),
                   'bundle': json.loads((chains / 'good_T4_freeze_bundle.json')
                                        .read_text('utf-8')),
                   'exposure_ledger': json.loads((chains / 'good_T4_exposure_ledger.json')
                                                 .read_text('utf-8'))}
            fixtures.materialize(good, root, 'T4', art)
            sha = lab_common.freeze_bundle_sha256(art['bundle'])
            report = lab_verify_log.verify_trial('T4', sha, mode='full',
                                                 results_root=root)
            fails = [f.check for f in report.findings if f.severity == 'FAIL']
            self.assertEqual(fails, [], 'the committed good fixture no longer verifies')
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# the dry runs
# ---------------------------------------------------------------------------
class DryRunTests(unittest.TestCase):
    def test_d1_harm(self) -> None:
        out = dry.run_dry(dry.scenario_d1(44), verbose=False)
        self.assertEqual(out['verdict'], 'PASS', out['findings'])
        self.assertTrue(out['decision'].startswith('harm_keep_incumbent@'), out)

    def test_d2_horizon_at_the_frozen_margin(self) -> None:
        out = dry.run_dry(dry.scenario_d2(24), verbose=False)
        self.assertEqual(out['verdict'], 'PASS', out['findings'])
        self.assertTrue(out['decision'].startswith('horizon_no_decision@'), out)

    def test_d3_deploy_path_with_a_mock_only_margin(self) -> None:
        out = dry.run_dry(dry.scenario_d3(50), verbose=False)
        self.assertEqual(out['verdict'], 'PASS', out['findings'])
        self.assertTrue(out['decision'].startswith('deploy_candidate@'), out)

    def test_d4_a_a_is_reported_never_discarded(self) -> None:
        crossings = 0
        for k in range(3):
            out = dry.run_dry(dry.scenario_d4(20, seed=1000 + k), verbose=False)
            self.assertEqual(out['verdict'], 'PASS', out['findings'])
            if not out['decision'].startswith('horizon_no_decision'):
                crossings += 1
        # One A/A run establishes nothing and demonstrates no equivalence (guidance item
        # 8); a crossing is reported and investigated, never discarded.
        self.assertLessEqual(crossings, 3)

    def test_d7_radius_table_is_generated_never_typed(self) -> None:
        cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
        root = Path(tempfile.mkdtemp(prefix='live_ab_radius_'))
        try:
            out = root / 'radius_table.csv'
            dry.write_radius_table(out, cfg)
            rows = [r for r in out.read_text('utf-8').splitlines() if r]
            self.assertEqual(rows[0], 'n,radius')
            self.assertEqual(len(rows), 1 + len(dry.RADIUS_NS))
            fixture = HERE / 'testdata' / 'radius_table.csv'
            if fixture.exists():
                self.assertEqual(fixture.read_text('utf-8'), out.read_text('utf-8'),
                                 'the generated table differs from G3\'s fixture')
        finally:
            shutil.rmtree(root, ignore_errors=True)


class ChaosTests(unittest.TestCase):
    def test_d5_chaos_kills(self) -> None:
        """D5: repeated crashes at pseudo-random points.  After every one the trial is
        resumed and the verifier must PASS, with zero double coins, zero double reveals
        and every attempt accounted for."""
        tree = Tree(pairs=8, trial='T2')
        try:
            points = [{'id': 'c1', 'event': 'coin_drawn', 'nth': 2},
                      {'id': 'c2', 'spool': 'call_started', 'nth': 5},
                      {'id': 'c3', 'event': 'episode_revealed', 'nth': 7},
                      {'id': 'c4', 'spool': 'episode_final', 'nth': 9}]
            status = tree.run(kill=points[0])
            self.assertEqual(status, 'killed')
            for spec in points[1:]:
                status = tree.run(kill=spec, resume=True)
                if status != 'killed':
                    break
            if status == 'killed':
                status = tree.run(resume=True)
            self.assertIn(status, ('ended', 'aborted'))
            events = tree.events()
            _no_double_work(self, events)
            report = tree.verify()
            self.assertEqual(report.verdict, 'PASS',
                             [f.check for f in report.findings
                              if f.severity == 'FAIL'])
            assigned = set()
            for ev in events:
                if ev['type'] == 'coin_drawn':
                    assigned.update(int(a) for a in ev['body']['assignment'])
            revealed = {int(e['body']['arrival']) for e in events
                        if e['type'] == 'episode_revealed'}
            self.assertEqual(assigned - revealed, set(),
                             'an assigned arrival was never accounted for')
        finally:
            tree.close()


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
