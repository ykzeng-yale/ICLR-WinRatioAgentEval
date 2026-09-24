"""EB5 model-free controls: every permitted worker resolved before the terminal record.

Repair contract EB5 (session 60; root 20:40 item 3: "A successful loaded phase must demonstrate
all permitted workers resolved before its terminal acceptance; preserve any unresolved attempt
as a failed/incomplete phase"; root 21:15 item 3: "Unresolved workers/usage make the phase
incomplete, not zero"; root 21:14: "killing/reaping does not turn unknown historical usage into
zero").  The pre-EB5 mechanisms these controls exercise are those of
``git show b049307:experiments/live_ab/lab_orchestrator.py`` (the pump, the abort and pause
paths, resume); the controls are numbered C1-C9 as in the session's EB5 design map, and this
file runs C1-C6, C8 and C9 (C7, ``lab_load``, is not run here: the ``lab_load`` controls are
``tests_lab_load_resolution.py``).

What runs:

* **The production entry point, as a subprocess** -- ``lab_orchestrator.main`` with
  ``WORLD_FACTORY`` unset: the real ``World``, the real preflight and host gate, the real
  ``lab_server.start`` / ``stop``, **real ``lab_worker`` subprocesses** (through
  ``eb1c_worker_entry``, which only relocates the host lock pin) and the real verifier CLI --
  on the EB1c temporary host of ``tests_eb1_entry.EntryTree`` (the compiled ``sm_fixture``
  launcher, a dummy GGUF, THE serving manifest of that build, the mock anchor).
* **The server is ``lab_mock_server`` on loopback**, behind ``eb5_llama_shim`` (the EB1c shim
  plus one ``posts.jsonl`` line per task POST, so a control can count the POSTs a worker made).
  Holds are the mock's own ``timeout`` fault (``sleep_s``); the abort trigger is its
  ``receipt`` fault.
* **Timing** (``mock_overrides`` of the temporary tree, runtime overlay of the invocation):
  ``execution.request_timeout_s`` 3 s (frozen: >= 180), the hard cap 8 s
  (``_runtime.episode_hard_cap_s``; frozen: its formula), the close's server-idle bound
  ``_runtime.resolution_idle_wait_s`` per control (frozen: ``request_timeout_s``).  One pair
  per trial; every run is bounded and asserted to take at most :data:`RUN_BOUND_S`.
* **Mutations** (``eb5_mutant_entry.py``) restore one pre-EB5 mechanism each, so a control
  run through one shows that THIS mechanism produced what the control asserts.
* **Observer**: where a POST could only be seen after the orchestrator has stopped its server
  (a late POST), the control binds a fresh ``lab_mock_server`` on the frozen port after the run
  and counts what arrives there.

Every control asserts that no process outlives it: no worker (every ``episode_started`` pid),
no launched shim, nothing in the orchestrator's process group, no listener on the port.  A
worker a MUTATION deliberately leaves running is asserted alive first, then killed by the
control, and only then is "nothing outlives" asserted.

**Run this file alone, on a quiescent host**, as ``tests_eb1_entry`` (the real host gate).

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_hostcheck                                                    # noqa: E402
import lab_mock_server                                                  # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_server                                                       # noqa: E402
import lab_verify_log                                                   # noqa: E402
import tests_eb1_entry as eb1                                           # noqa: E402
from lab_common import canonical_json, sha256_bytes, sha256_text        # noqa: E402

PY = sys.executable
HARD_CAP_S = 8.0
REQUEST_TIMEOUT_S = 3.0
RUN_BOUND_S = 60.0
MUTANT = HERE / 'eb5_mutant_entry.py'
GATE_RETRIES = 5


def setUpModule() -> None:
    eb1.setUpModule()


def tearDownModule() -> None:
    eb1.tearDownModule()


# --------------------------------------------------------------------------- #
# the temporary host
# --------------------------------------------------------------------------- #
class Tree(eb1.EntryTree):
    """``tests_eb1_entry.EntryTree`` with the POST-logging shim, one pair, the EB5 timing, a
    barrier directory for ``eb5_worker_entry`` and a non-blocking runner."""

    def __init__(self, name: str, *, n_pairs: int = 1) -> None:
        super().__init__('eb5_%s' % name, n_pairs=n_pairs)
        self.shim_token = 'eb5_llama_shim'
        self.fixture.set_shim(HERE / 'eb5_llama_shim.py')
        self.barrier = self.root / 'barrier'
        self.barrier.mkdir()
        self.log_index = 0
        self.first_procs: list = []
        self.refusals_at_launch = 0

    def setup(self, *, idle_wait_s: float = 20.0, barrier: bool = False,
              execution: dict | None = None) -> 'Tree':
        """Build the tree with the EB5 timing; :meth:`serve` then names the faults."""
        runtime = {'episode_hard_cap_s': HARD_CAP_S, 'resolution_idle_wait_s': idle_wait_s}
        ex = {'request_timeout_s': REQUEST_TIMEOUT_S}
        ex.update(execution or {})
        self.build(runtime=runtime, execution=ex)
        if barrier:
            self.runtime['worker_cmd'] = [PY, str(HERE / 'eb5_worker_entry.py'),
                                          '--harness-config', str(self.freeze / 'config.json'),
                                          '--barrier-dir', str(self.barrier)]
            self.write_run_config()
        order = json.loads((self.freeze / 'arrival_order_T4.json').read_text('utf-8'))
        slot = order[0]
        self.a1, self.a2 = (int(a) for a in slot['arrivals'])
        self.u1, self.u2 = (str(u) for u in slot['uids'])
        self.serve([])
        return self

    def serve(self, faults: list, *, after: int = 0) -> None:
        """The first server start serves ``faults``; ``after`` further starts serve none."""
        self.set_scenarios([dict(self.good_scenario, faults=list(faults))]
                           + [dict(self.good_scenario)] * int(after))

    # -- running -------------------------------------------------------------------------
    def gate_refusals(self) -> int:
        """How many ``preflight_refused(host_not_quiescent)`` the program chain holds."""
        return sum(1 for e in self.program_chain() if e['type'] == 'preflight_refused'
                   and 'host_not_quiescent' in (e['body'].get('checks_failed') or []))

    def start(self, *, mutation: str | None = None, resume: bool = False):
        """Launch the entry point once the host is quiescent, and return once it is PAST the
        real host gate (its trial chain grew, or it already exited).  A launch the gate
        refused before seq 0 -- another suite's llama-server-shaped shim appeared between the
        quiescence check and the gate (``tests_eb1_entry``: "run alone on a quiescent host")
        -- changed nothing in the trial chain and is launched again, at most
        :data:`GATE_RETRIES` times; the refusals stay in the program chain."""
        for _ in range(GATE_RETRIES):
            wait_for_quiescent_host()
            before = self.gate_refusals()
            grown_from = len(self.safe_chain())
            self._launch(mutation=mutation, resume=resume)
            self.refusals_at_launch = before
            while True:
                if self.gate_refusals() > before:
                    self.proc.wait(timeout=60)
                    dry._stop_anchor(self.anchor)
                    break
                if len(self.safe_chain()) > grown_from or self.proc.poll() is not None:
                    return self.proc
                time.sleep(0.05)
        raise AssertionError('the host gate refused %d launches in a row' % GATE_RETRIES)

    def _launch(self, *, mutation: str | None, resume: bool):
        cfg = json.loads(self.run_config.read_text('utf-8'))
        self.anchor = dry._start_anchor(self.trial, cfg, self.results, self.work)
        argv = self.argv() + (['--resume'] if resume else [])
        script = [str(MUTANT), '--mutation', mutation] if mutation else \
            [str(LIVE / 'lab_orchestrator.py')]
        self.log_index += 1
        self.out_path = self.work / ('invocation_%d.log' % self.log_index)
        with open(self.out_path, 'wb') as out:
            self.proc = subprocess.Popen([PY] + script + argv, cwd=str(LIVE),
                                         env=eb1.child_env(), stdout=out,
                                         stderr=subprocess.STDOUT, start_new_session=True)
        self.t_start = time.monotonic()
        self.returncode = None
        return self.proc

    def finish(self, case: unittest.TestCase) -> int | None:
        """Wait for the running invocation (bounded), stop the anchor, and assert the run
        was neither refused by the host gate nor longer than :data:`RUN_BOUND_S`."""
        try:
            try:
                self.proc.wait(timeout=RUN_BOUND_S + 30)
                self.returncode = self.proc.returncode
            except subprocess.TimeoutExpired:
                eb1.with_group_kill(self.proc)
                self.proc.wait(timeout=30)
                self.returncode = None
        finally:
            dry._stop_anchor(self.anchor)
        elapsed = time.monotonic() - self.t_start
        self.stdout = self.out_path.read_text('utf-8', 'replace')
        if self.gate_refusals() > self.refusals_at_launch:
            raise AssertionError(eb1.host_refusal(self.program_chain()))
        case.assertIsNotNone(self.returncode, 'the run had to be killed:\n' + self.stdout[-3000:])
        case.assertLessEqual(elapsed, RUN_BOUND_S, 'a control run took %.1f s' % elapsed)
        return self.returncode

    def kill_orchestrator(self) -> None:
        """The dispatcher dies (SIGKILL of the orchestrator process ONLY): its workers and its
        server, each in its own session, survive -- as in tests_lab_serving.py:1434."""
        os.kill(self.proc.pid, signal.SIGKILL)
        self.proc.wait(timeout=30)
        dry._stop_anchor(self.anchor)
        self.first_procs.append(self.proc)

    # -- reading ------------------------------------------------------------------------
    def spool(self, arrival: int) -> list[dict]:
        path = self.work / self.trial / 'spools' / ('ep_%d_1.jsonl' % arrival)
        out: list[dict] = []
        if not path.exists():
            return out
        for line in path.read_bytes().split(b'\n'):
            try:
                row = json.loads(line.decode('utf-8'))
            except ValueError:
                continue
            if isinstance(row, dict):
                out.append(row)
        return out

    def spool_path(self, arrival: int) -> Path:
        return self.work / self.trial / 'spools' / ('ep_%d_1.jsonl' % arrival)

    def worker_pid(self, arrival: int) -> int | None:
        rows = [r for r in self.spool(arrival) if r.get('kind') == 'job_accepted']
        return int(rows[0]['pid']) if rows else None

    def posts(self, uid: str | None = None) -> list[dict]:
        path = self.state / 'posts.jsonl'
        if not path.exists():
            return []
        rows = [json.loads(line) for line in path.read_text('utf-8').splitlines() if line]
        return [r for r in rows if uid is None or r.get('uid') == uid]

    def safe_chain(self) -> list[dict]:
        try:
            return self.chain()
        except (lab_common.ChainError, ValueError, OSError):
            return []


def wait_for_quiescent_host(timeout: float = 1200.0) -> None:
    """Block until the real host gate would pass for this process (read only: ps / lsof)."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            lab_hostcheck.preflight_host_quiescent(orch.own_harness_pids())
            return
        except lab_hostcheck.HostNotQuiescent:
            if time.monotonic() >= deadline:
                raise AssertionError('the host never became quiescent')
            time.sleep(2.0)


def wait_for(cond, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        got = cond()
        if got:
            return got
        time.sleep(0.05)
    raise AssertionError('timed out waiting for: %s' % what)


def hold(uid: str, sleep_s: float) -> dict:
    """The mock holds EVERY try of ``uid``'s code call for ``sleep_s`` (lab_mock_server's
    ``timeout`` fault), counting it busy in ``/metrics`` and ``/slots`` meanwhile."""
    return {'match': {'uid': uid, 'kind': 'code'}, 'do': 'timeout', 'sleep_s': float(sleep_s)}


def receipt_fault(uid: str) -> dict:
    """``uid``'s code call is answered with a changed sampler setting: a receipt mismatch, so
    the orchestrator aborts ``receipt_mismatch`` (protocol 6.4 row 12)."""
    return {'match': {'uid': uid, 'kind': 'code'}, 'do': 'receipt',
            'set': {'temperature': 0.123}}


def of(events, etype: str) -> list[dict]:
    return [e for e in events if e['type'] == etype]


def by_arrival(events, etype: str, arrival: int) -> list[dict]:
    return [e for e in events if e['type'] == etype and int(e['body']['arrival']) == arrival]


def terminal(events) -> dict:
    ends = [e for e in events if e['type'] in ('trial_ended', 'trial_aborted')]
    assert len(ends) == 1, [e['type'] for e in ends]
    return ends[0]


class Observer:
    """A fresh ``lab_mock_server`` bound on the frozen port AFTER the orchestrator stopped its
    own server: whatever POST reaches it was sent after the terminal record."""

    def __init__(self, tree: Tree) -> None:
        self.srv, _port = lab_mock_server.make_server(dict(tree.good_scenario),
                                                      port=tree.port)
        self.thread = threading.Thread(target=self.srv.serve_forever,
                                       kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()

    def n(self) -> int:
        return int(self.srv.state.snapshot()['n_requests'])

    def close(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()


def verifier_findings(tree: Tree, check: str) -> list[dict]:
    """The verifier CLI's findings of one check (FAIL severity), with the work root."""
    report = tree.verify()
    return [f for f in report['findings'] if f['check'] == check and f['severity'] == 'FAIL']


# --------------------------------------------------------------------------- #
# the base case
# --------------------------------------------------------------------------- #
class Case(unittest.TestCase):

    def tree(self, name: str, **kw) -> Tree:
        t = Tree(name, n_pairs=kw.pop('n_pairs', 1))
        self.addCleanup(t.cleanup)
        self.addCleanup(self._kill_leftovers, t)
        return t.setup(**kw)

    def _kill_leftovers(self, t: Tree) -> None:
        """Cleanup only (a failed control): any worker of the tree still alive is killed."""
        for arrival in (getattr(t, 'a1', None), getattr(t, 'a2', None)):
            if arrival is None:
                continue
            pid = t.worker_pid(arrival)
            if pid and eb1.pid_alive(pid) and 'worker_entry' in eb1.pid_command(pid):
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass

    def assertNoOrphans(self, t: Tree) -> None:
        """No worker, no shim, nothing in any orchestrator's group, no listener on the port."""
        deadline = time.monotonic() + 10
        pids = {p for p in (t.worker_pid(t.a1), t.worker_pid(t.a2)) if p}
        pids |= {int(e['body']['worker_pid']) for e in of(t.safe_chain(), 'episode_started')}

        def alive() -> list:
            return [p for p in pids
                    if eb1.pid_alive(p) and 'worker_entry' in eb1.pid_command(p)]
        while alive() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertEqual(alive(), [], 'a worker outlived the control')
        for row in t.launches():
            self.assertFalse(eb1.pid_alive(row['pid'])
                             and t.shim_token in eb1.pid_command(row['pid']),
                             'server shim pid %d survived' % row['pid'])
        for proc in [t.proc] + list(t.first_procs):
            self.assertEqual(eb1.group_members(proc.pid), set(),
                             'a process of an orchestrator\'s group outlived the run')
        self.assertEqual(lab_server.listening_pids(t.port), set(),
                         'something still listens on the frozen port')

    def assertResolvedBefore(self, events, arrival: int, state: str, etype: str) -> dict:
        """``arrival``'s worker has a ``worker_resolved`` of ``state`` at a LOWER seq than
        its first ``etype`` event; returns that record."""
        recs = by_arrival(events, 'worker_resolved', arrival)
        self.assertTrue(recs, 'arrival %d has no worker_resolved' % arrival)
        target = [e for e in events if e['type'] == etype
                  and int(e['body'].get('arrival', -1)) == arrival] if etype != 'terminal' \
            else [terminal(events)]
        self.assertTrue(target, 'no %s for arrival %d' % (etype, arrival))
        self.assertEqual(recs[0]['body']['state'], state)
        self.assertLess(recs[0]['seq'], target[0]['seq'])
        return recs[0]['body']

    def assertTruthfulRecord(self, t: Tree) -> None:
        """The verifier's workers.resolved recount agrees with the terminal record (it has no
        FAIL finding): the chain says what happened, whatever the verdict."""
        self.assertEqual(verifier_findings(t, 'workers.resolved'), [])


# --------------------------------------------------------------------------- #
# pure: the verdict, the verifier's recount, the ledger (in process, no subprocess)
# --------------------------------------------------------------------------- #
def _ev(seq: int, etype: str, body: dict) -> dict:
    return {'seq': seq, 'type': etype, 'body': body}


RID = [sha256_text('eb5-rid-%d' % i)[:32] for i in range(8)]
SHA_EMPTY = sha256_bytes(b'')


def _chain(state1='exited', state2='exited', *, answer2=True, extra=()):
    """Two started arrivals; arrival 2's call unanswered unless ``answer2``."""
    ev = [_ev(0, 'episode_started', {'arrival': 1}), _ev(1, 'episode_started', {'arrival': 2}),
          _ev(2, 'llm_request', {'arrival': 1, 'attempt': 1, 'request_id': RID[0]}),
          _ev(3, 'llm_response', {'arrival': 1, 'attempt': 1, 'request_id': RID[0],
                                  'usage': {'prompt_tokens': 5, 'completion_tokens': 7}}),
          _ev(4, 'llm_request', {'arrival': 2, 'attempt': 1, 'request_id': RID[1]})]
    if answer2:
        ev.append(_ev(5, 'llm_error', {'arrival': 2, 'attempt': 1, 'request_id': RID[1],
                                       'usage_known': False}))
    seq = len(ev)
    for arrival, state in ((1, state1), (2, state2)):
        if state is None:
            continue
        ev.append(_ev(seq, 'worker_resolved', {
            'arrival': arrival, 'attempt': 1, 'pid': 100 + arrival, 'state': state,
            'returncode': 0, 'spool_bytes_at_resolution': 0,
            'spool_sha256_at_resolution': SHA_EMPTY}))
        seq += 1
    for e in extra:
        ev.append(dict(e, seq=seq))
        seq += 1
    return ev


IDLE = {'coder': {'held': True, 'observed': True, 'requests_processing': 0, 'slots_busy': 0}}
SPOOLS = {'ep_1_1': {'bytes': 0, 'prefix_sha256': SHA_EMPTY},
          'ep_2_1': {'bytes': 0, 'prefix_sha256': SHA_EMPTY}}


class VerdictTests(unittest.TestCase):
    """``lab_orchestrator.phase_resolution_verdict``: each rule refuses its input and the same
    call on the corrected input passes (the negative control of every rule)."""

    def verdict(self, events, spools=SPOOLS, servers=IDLE) -> dict:
        return orch.phase_resolution_verdict(events, spools, servers)

    def test_positive_every_worker_resolved_every_call_accounted_server_idle(self):
        v = self.verdict(_chain())
        self.assertEqual((v['verdict'], v['problems']), ('PASS', []))
        self.assertEqual(v['unresolved_attempts'], [])
        self.assertEqual(v['unfinished_calls'], [])

    def test_rule1_a_worker_without_a_resolving_record(self):
        for state in (None, 'alive_unresolved', 'liveness_unknown'):
            with self.subTest(state=state):
                v = self.verdict(_chain(state2=state))
                self.assertEqual(v['verdict'], 'FAIL')
                self.assertIn('worker_unresolved', v['problems'])
                self.assertEqual(v['unresolved_attempts'],
                                 [{'arrival': 2, 'attempt': 1,
                                   'state': state or 'no_record'}])
        self.assertEqual(self.verdict(_chain(state2='killed_reaped'))['verdict'], 'PASS')

    def test_an_unresolved_record_is_never_undone_by_a_later_resolution(self):
        late = _ev(0, 'worker_resolved', {
            'arrival': 2, 'attempt': 1, 'pid': 102, 'state': 'killed_reaped',
            'returncode': None, 'spool_bytes_at_resolution': 0,
            'spool_sha256_at_resolution': SHA_EMPTY})
        v = self.verdict(_chain(state2='alive_unresolved', extra=[late]))
        self.assertEqual(v['verdict'], 'FAIL')
        self.assertEqual(v['unresolved_attempts'][0]['state'], 'alive_unresolved')

    def test_rule2_an_unfinished_call_is_listed_null_usage_and_refused_only_if_unresolved(self):
        v = self.verdict(_chain(answer2=False))
        self.assertEqual(v['verdict'], 'PASS', 'a call of a RESOLVED worker is not a failure')
        self.assertEqual(v['unfinished_calls'],
                         [{'arrival': 2, 'attempt': 1, 'request_id': RID[1],
                           'worker_state': 'exited', 'usage': None}])
        v = self.verdict(_chain(state2=None, answer2=False))
        self.assertIn('call_unresolved', v['problems'])
        self.assertEqual(v['unfinished_calls'][0]['worker_state'], 'no_record')

    def test_rule3_a_spool_past_its_resolution_offset(self):
        grown = dict(SPOOLS, ep_2_1={'bytes': 9, 'prefix_sha256': SHA_EMPTY})
        v = self.verdict(_chain(), spools=grown)
        self.assertEqual((v['verdict'], v['problems']), ('FAIL', ['spool_grew']))
        self.assertEqual(v['late_spools'], [{'arrival': 2, 'attempt': 1,
                                             'bytes_at_resolution': 0, 'bytes_found': 9}])
        changed = dict(SPOOLS, ep_2_1={'bytes': 0, 'prefix_sha256': '0' * 64})
        self.assertEqual(self.verdict(_chain(), spools=changed)['problems'], ['spool_changed'])
        unread = dict(SPOOLS, ep_2_1={'bytes': None, 'prefix_sha256': None})
        self.assertEqual(self.verdict(_chain(), spools=unread)['problems'],
                         ['spool_unreadable'])

    def test_rule4_a_held_server_busy_or_unobserved(self):
        busy = {'coder': dict(IDLE['coder'], requests_processing=1)}
        self.assertEqual(self.verdict(_chain(), servers=busy)['problems'], ['server_busy'])
        slots = {'coder': dict(IDLE['coder'], slots_busy=1)}
        self.assertEqual(self.verdict(_chain(), servers=slots)['problems'], ['server_busy'])
        unseen = {'coder': {'held': True, 'observed': False, 'requests_processing': None,
                            'slots_busy': None}}
        self.assertEqual(self.verdict(_chain(), servers=unseen)['problems'],
                         ['server_unobserved'])
        gone = {'coder': dict(unseen['coder'], held=False)}
        self.assertEqual(self.verdict(_chain(), servers=gone)['verdict'], 'PASS',
                         'a server not held (stopped) runs no request')

    def test_the_record_validates_against_the_terminal_schema(self):
        rec = self.verdict(_chain(state2='alive_unresolved', answer2=False),
                           servers={'coder': dict(IDLE['coder'], requests_processing=2)})
        rec['unfinished_calls'][0]['request_id'] = RID[1]
        lab_eventlog._check_field(lab_eventlog.RESOLUTION, rec, 'resolution')
        with self.assertRaises(lab_common.SchemaError):
            lab_eventlog._check_field(lab_eventlog.RESOLUTION,
                                      dict(rec, unfinished_calls=[dict(
                                          rec['unfinished_calls'][0], usage=0)]),
                                      'resolution')


class VerifierRecountTests(unittest.TestCase):
    """The verifier's ``workers.resolved`` recount is written separately; it must agree with
    the orchestrator's verdict on every input above, and its check must refuse a terminal
    record that claims more than the chain shows."""

    def test_the_two_implementations_agree(self):
        cases = [_chain(), _chain(state2=None), _chain(state2='alive_unresolved'),
                 _chain(answer2=False), _chain(state2=None, answer2=False),
                 _chain(state2='liveness_unknown', answer2=False)]
        for servers in (IDLE, {'coder': dict(IDLE['coder'], slots_busy=2)}):
            for events in cases:
                a = orch.phase_resolution_verdict(events, SPOOLS, servers)
                b = lab_verify_log._resolution_recount(events, a['servers'], a['late_spools'])
                for key in ('verdict', 'problems', 'unresolved_attempts', 'unfinished_calls'):
                    self.assertEqual(canonical_json(a[key]), canonical_json(b[key]), key)

    def _findings(self, events):
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_workers_resolved(col, events, None)
        self.assertIn('workers.resolved', col.seen)
        return [f.detail.get('rule') for f in col.findings]

    def _term(self, events, etype='trial_ended', reason=None, record=None):
        rec = record if record is not None else orch.phase_resolution_verdict(
            events, SPOOLS, IDLE)
        return events + [_ev(len(events), etype, {'reason': reason, 'resolution': rec})]

    def test_ended_over_an_unresolved_worker_fails_and_the_resolved_chain_passes(self):
        self.assertEqual(self._findings(self._term(_chain())), [])
        self.assertIn('ended_unresolved', self._findings(self._term(_chain(state2=None))))
        self.assertEqual(self._findings(self._term(
            _chain(state2=None), 'trial_aborted', 'unresolved_worker')), [])
        self.assertIn('wrong_reason', self._findings(self._term(
            _chain(state2=None), 'trial_aborted', 'receipt_mismatch')))

    def test_a_fabricated_pass_record_is_refused(self):
        fake = {'verdict': 'PASS', 'problems': [], 'unresolved_attempts': [],
                'unfinished_calls': [], 'late_spools': [], 'servers': [],
                'superseded_reason': None}
        self.assertIn('resolution_record', self._findings(
            self._term(_chain(state2='alive_unresolved'), record=fake)))
        self.assertIn('resolution_record', self._findings(
            _chain() + [_ev(99, 'trial_ended', {'reason': None})]))

    def test_an_interrupted_reveal_needs_an_earlier_resolution(self):
        reveal = {'type': 'episode_revealed', 'body': {
            'arrival': 2, 'outcome': {'error_class': 'interrupted'},
            'usage_complete': False, 'unknown_usage_calls': 1}}
        before = _chain(state2=None) + [dict(reveal, seq=6)]
        self.assertIn('reveal_before_resolution', self._findings(before))
        after = _chain() + [dict(reveal, seq=8)]
        self.assertNotIn('reveal_before_resolution', self._findings(after))

    def test_usage_fields_are_recounted(self):
        good = _chain() + [{'seq': 8, 'type': 'episode_revealed', 'body': {
            'arrival': 2, 'outcome': {'error_class': None}, 'usage_complete': False,
            'unknown_usage_calls': 1}}]
        self.assertNotIn('usage_fields', self._findings(good))
        bad = [dict(e) for e in good]
        bad[-1] = dict(bad[-1], body=dict(bad[-1]['body'], usage_complete=True,
                                          unknown_usage_calls=0))
        self.assertIn('usage_fields', self._findings(bad))

    def test_usage_of_lines(self):
        lines = [{'kind': 'call_started', 'body': {'request_id': 'a'}},
                 {'kind': 'call_response', 'body': {'request_id': 'a'}},
                 {'kind': 'call_started', 'body': {'request_id': 'b'}},
                 {'kind': 'call_error', 'body': {'request_id': 'b'}},
                 {'kind': 'call_started', 'body': {'request_id': 'c'}}]
        self.assertEqual(orch.usage_of_lines(lines), (False, 2))
        self.assertEqual(orch.usage_of_lines(lines[:2]), (True, 0))


def _old_ledger_unknown(events) -> int:
    """The pre-EB5 attribution (b049307 lab_orchestrator.py:460-464): an unknown-usage call
    counts only when its arrival was revealed -- the negative control of "nothing dropped"."""
    arm = {int(e['body']['arrival']) for e in events if e['type'] == 'episode_revealed'}
    return sum(1 for a in orch.unknown_usage_by_request(events).values() if a in arm)


class LedgerTests(unittest.TestCase):

    def test_unrevealed_calls_stay_in_the_ledger_and_totals_are_null(self):
        events = [_ev(0, 'episode_started', {'arrival': 3}),
                  _ev(1, 'llm_request', {'arrival': 3, 'attempt': 1, 'request_id': RID[2]}),
                  _ev(2, 'llm_request', {'arrival': 3, 'attempt': 1, 'request_id': RID[3]}),
                  _ev(3, 'llm_response', {'arrival': 3, 'attempt': 1, 'request_id': RID[3],
                                          'usage': {'prompt_tokens': 11,
                                                    'completion_tokens': 13}})]
        a = orch.exposure_recount(events)
        b = lab_verify_log._recount_exposure(events)
        self.assertEqual(canonical_json(a), canonical_json(b))
        self.assertEqual(a['unrevealed'], {'episodes': 1, 'prompt_tokens': 11,
                                           'completion_tokens': 13, 'unknown_usage_calls': 1,
                                           'tokens_are_lower_bound': True})
        self.assertEqual(a['totals'], {'prompt_tokens': None, 'completion_tokens': None,
                                       'unknown_usage_calls': 1,
                                       'null_reason': 'unknown_usage'})
        self.assertEqual(_old_ledger_unknown(events), 0, 'the old ledger dropped the call')
        known = events[:1] + events[2:]
        c = orch.exposure_recount(known)
        self.assertEqual(c['totals'], {'prompt_tokens': 11, 'completion_tokens': 13,
                                       'unknown_usage_calls': 0, 'null_reason': None})


class BuilderLabelTests(unittest.TestCase):
    """``build_live_ab_results.episode_rows``: ``completion_tokens`` (the known tokens, not
    scored) is never presented as a complete count when the episode's usage is not."""

    def rows(self, **fields):
        body = {'arrival': 1, 'pair': 1, 'position': 1, 'arm': 'incumbent',
                'reveal_index': 0, 'post_decision': False, 'sandbox_lock_wait_s': 0.0,
                'certified_ell': 0.0, 'recovered_orphan': False,
                'overlap': {'seconds_with_partner': 0.0},
                'outcome': {'completion_tokens': 240, 'success': 1}}
        body.update(fields)
        return builder.episode_rows([{'seq': 0, 'type': 'episode_revealed', 'body': body}])

    def test_the_label_follows_usage_complete(self):
        (row,) = self.rows(usage_complete=False, unknown_usage_calls=2)
        self.assertEqual((row['completion_tokens'], row['completion_tokens_status'],
                          row['unknown_usage_calls']), (240, 'lower_bound', 2))
        (row,) = self.rows(usage_complete=True, unknown_usage_calls=0)
        self.assertEqual(row['completion_tokens_status'], 'complete')
        (row,) = self.rows()
        self.assertEqual(row['completion_tokens_status'], 'unknown',
                         'a pre-EB5 reveal carries no flag and is not read as complete')


# --------------------------------------------------------------------------- #
# the kill and the probe (a real process, in this process)
# --------------------------------------------------------------------------- #
def _sleeper(job_name: str = 'job_7_1.json') -> subprocess.Popen:
    """A process whose command line names a job file, in its own session (as a worker)."""
    return subprocess.Popen([PY, '-c', 'import time; [time.sleep(0.2) for _ in iter(int, 1)]',
                             '--job', '/nonexistent/%s' % job_name], start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _reap(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)


class _Att:
    def __init__(self, proc, arrival=7):
        self.proc, self.pid, self.arrival, self.attempt = proc, proc.pid if proc else 0, \
            arrival, 1


class KillAndProbeTests(unittest.TestCase):

    def test_kill_returns_true_only_when_the_exit_is_confirmed(self):
        proc = _sleeper()
        self.addCleanup(_reap, proc)
        self.assertIs(orch.World.kill(object.__new__(orch.World), _Att(proc)), True)
        self.assertIsNotNone(proc.returncode)
        # negative control: the same kill whose reap cannot be confirmed says so
        proc2 = _sleeper()
        self.addCleanup(_reap, proc2)
        with mock.patch.object(subprocess.Popen, 'wait',
                               side_effect=subprocess.TimeoutExpired('x', 5)):
            self.assertIs(orch.World.kill(object.__new__(orch.World), _Att(proc2)), False)
        proc2.wait(timeout=10)                        # it WAS signalled; now reaped here

    def test_finished_without_a_process_is_unknown_never_exited(self):
        world = object.__new__(orch.World)
        self.assertIs(orch.World.finished(world, _Att(None)), orch.WORKER_UNKNOWN)
        self.assertIsNot(orch.WORKER_UNKNOWN, 0)
        proc = _sleeper()
        self.addCleanup(_reap, proc)
        self.assertIsNone(orch.World.finished(world, _Att(proc)))
        proc.kill()
        proc.wait(timeout=10)
        self.assertIsNotNone(orch.World.finished(world, _Att(proc)))

    def test_probe_reads_identity_not_the_pid_alone(self):
        proc = _sleeper('job_7_1.json')
        self.addCleanup(_reap, proc)
        now = time.time_ns()
        self.assertEqual(orch.probe_worker(proc.pid, 'job_7_1.json', not_after_ns=now),
                         'alive')
        self.assertEqual(orch.probe_worker(proc.pid, 'job_8_1.json'), 'gone',
                         'the pid names another job: a reused pid is not our worker')
        self.assertEqual(orch.probe_worker(proc.pid, 'job_7_1.json',
                                           not_after_ns=now - int(60e9)), 'gone',
                         'a process started after the dispatch is not our worker')
        self.assertEqual(orch.probe_worker(os.getpid(), 'job_7_1.json'), 'gone')
        with mock.patch.object(orch, '_ps_process', return_value=('unknown', None)):
            self.assertEqual(orch.probe_worker(proc.pid, 'job_7_1.json'), 'unknown')
        state, _rc = orch.kill_orphan_worker(proc.pid, 'job_7_1.json', not_after_ns=now)
        self.assertEqual(state, 'killed_reaped')
        self.assertEqual(orch.probe_worker(proc.pid, 'job_7_1.json'), 'gone')

    def test_an_orphan_kill_that_cannot_be_confirmed_is_alive_unresolved(self):
        proc = _sleeper('job_9_1.json')
        self.addCleanup(_reap, proc)
        with mock.patch.object(os, 'killpg'), mock.patch.object(os, 'kill'):
            state, _rc = orch.kill_orphan_worker(proc.pid, 'job_9_1.json', wait_s=0.5)
        self.assertEqual(state, 'alive_unresolved')
        self.assertIsNone(proc.poll(), 'nothing was signalled')


# --------------------------------------------------------------------------- #
# C8: no hold -- the check does not refuse vacuously
# --------------------------------------------------------------------------- #
class C8NoHold(Case):
    """C8: the same host, timing and entry path with NO hold: ``trial_ended``, verdict PASS,
    every worker ``exited`` (its exit observed AFTER its own final line's reveal), every
    episode's usage complete, the ledger totals non-null, the verifier PASS.  The negative
    control of C1-C6 (their refusals are not produced by the setup)."""

    def test_c8_a_clean_pair_passes(self):
        t = self.tree('C8', )
        t.start()
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        end = terminal(events)
        self.assertEqual(end['type'], 'trial_ended')
        res = end['body']['resolution']
        self.assertEqual((res['verdict'], res['problems']), ('PASS', []))
        self.assertEqual(res['unfinished_calls'], [])
        self.assertEqual([(s['held'], s['observed'], s['requests_processing'],
                           s['slots_busy']) for s in res['servers']], [(True, True, 0, 0)])
        for arrival in (t.a1, t.a2):
            rec = self.assertResolvedBefore(events, arrival, 'exited', 'terminal')
            self.assertEqual(rec['returncode'], 0)
            reveal = by_arrival(events, 'episode_revealed', arrival)[0]
            self.assertLess(reveal['seq'], by_arrival(events, 'worker_resolved', arrival)[0]
                            ['seq'], 'the exit is confirmed after the final line')
            self.assertEqual((reveal['body']['usage_complete'],
                              reveal['body']['unknown_usage_calls']), (True, 0))
            raw = t.spool_path(arrival).read_bytes()
            self.assertEqual((len(raw), sha256_bytes(raw)),
                             (rec['spool_bytes_at_resolution'],
                              rec['spool_sha256_at_resolution']))
        ledger = end['body']['exposure_ledger']
        self.assertIsNotNone(ledger['totals']['completion_tokens'])
        self.assertEqual(of(events, 'deposit_sealed')[0]['body']['late_unread'], [])
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C1: a hold past the hard cap
# --------------------------------------------------------------------------- #
class C1HoldPastTheHardCap(Case):
    """C1: the mock holds every try of position 2's code call.  The worker is killed at the
    hard cap and its exit confirmed (``killed_reaped``) BEFORE its ``episode_timeout`` reveal;
    its outstanding call is listed unfinished with usage ``null``; its episode reads
    ``usage_complete: false``; the ledger's totals are ``null``.  The server still decodes the
    killed client's requests: (a) with an idle bound longer than the hold, ``trial_ended`` is
    written only once ``/metrics requests_processing`` is 0 and ``/slots`` idle; (b) with a
    bound shorter than the hold the verdict refuses -- ``trial_aborted(unresolved_worker)``,
    ``server_busy``, no ``trial_ended``.  C8 is the negative control of both; C9 bypasses the
    verdict on (b)."""

    SLEEP_A = 14.0

    def check_killed_at_the_cap(self, t: Tree, events) -> None:
        rec = self.assertResolvedBefore(events, t.a2, 'killed_reaped', 'episode_revealed')
        self.assertIsNotNone(rec['returncode'])
        reveal = by_arrival(events, 'episode_revealed', t.a2)[0]['body']
        self.assertEqual(reveal['outcome']['error_class'], 'episode_timeout')
        self.assertIs(reveal['usage_complete'], False)
        self.assertGreaterEqual(reveal['unknown_usage_calls'], 1)
        started = by_arrival(events, 'episode_started', t.a2)[0]
        self.assertLess(started['seq'], reveal and by_arrival(events, 'episode_revealed',
                                                              t.a2)[0]['seq'])
        answered = {e['body']['request_id'] for e in events
                    if e['type'] in ('llm_response', 'llm_error')}
        open_calls = [e['body']['request_id'] for e in by_arrival(events, 'llm_request', t.a2)
                      if e['body']['request_id'] not in answered]
        self.assertEqual(len(open_calls), 1,
                         'precondition: the kill landed inside a held POST (the worker '
                         'reached its first POST within 3 s of dispatch)')
        res = terminal(events)['body']['resolution']
        self.assertIn({'arrival': t.a2, 'attempt': 1, 'request_id': open_calls[0],
                       'worker_state': 'killed_reaped', 'usage': None},
                      res['unfinished_calls'])
        ledger = terminal(events)['body']['exposure_ledger']
        self.assertEqual((ledger['totals']['completion_tokens'],
                          ledger['totals']['null_reason']), (None, 'unknown_usage'))
        self.assertResolvedBefore(events, t.a1, 'exited', 'terminal')

    def test_c1a_trial_ended_only_after_the_server_is_idle(self):
        t = self.tree('C1a', idle_wait_s=30.0)
        t.serve([hold(t.u2, self.SLEEP_A)])
        t.start()
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        self.check_killed_at_the_cap(t, events)
        end = terminal(events)
        self.assertEqual(end['type'], 'trial_ended')
        self.assertEqual(end['body']['resolution']['verdict'], 'PASS')
        self.assertEqual([(s['requests_processing'], s['slots_busy'])
                          for s in end['body']['resolution']['servers']], [(0, 0)])
        last_hold_end = max(p['t_wall'] for p in t.posts(t.u2)) + self.SLEEP_A
        self.assertGreaterEqual(end['t_wall_ns'] / 1e9, last_hold_end - 0.5,
                                'trial_ended was written while the mock still held a POST')
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)

    def test_c1b_the_verdict_refuses_while_the_mock_still_holds(self):
        t = self.tree('C1b', idle_wait_s=2.0)
        t.serve([hold(t.u2, 45.0)])
        t.start()
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        self.check_killed_at_the_cap(t, events)
        self.assertEqual(of(events, 'trial_ended'), [])
        end = terminal(events)
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        res = end['body']['resolution']
        self.assertEqual((res['verdict'], res['problems']), ('FAIL', ['server_busy']))
        self.assertGreaterEqual(res['servers'][0]['requests_processing'], 1)
        self.assertIsNone(res['superseded_reason'])
        self.assertTruthfulRecord(t)
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C2: an abort with the partner held
# --------------------------------------------------------------------------- #
class C2AbortWithThePartnerHeld(Case):
    """C2: position 1's response is a receipt mismatch (the orchestrator aborts
    ``receipt_mismatch``) while position 2 is held at the mock.  The abort first runs the
    BOUNDED drain: the partner is killed at the hard cap, confirmed, revealed, and its calls
    stay in the ledger under its arm (nothing dropped), and only then ``trial_aborted``.  The
    mutation ``drain_disabled`` (the pre-EB5 abort) closes at once over the running partner:
    the verdict refuses -- ``trial_aborted(unresolved_worker)`` superseding
    ``receipt_mismatch`` -- and the partner's call is still in the ledger, in the
    ``unrevealed`` cell, where the pre-EB5 ledger would have dropped it."""

    def faults(self, t: Tree) -> list:
        return [receipt_fault(t.u1), hold(t.u2, 10.0)]

    def test_c2_bounded_drain_then_the_abort(self):
        t = self.tree('C2', idle_wait_s=20.0)
        t.serve(self.faults(t))
        t.start()
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        end = terminal(events)
        self.assertEqual((end['type'], end['body']['reason']),
                         ('trial_aborted', 'receipt_mismatch'))
        self.assertEqual(end['body']['resolution']['verdict'], 'PASS')
        self.assertResolvedBefore(events, t.a2, 'killed_reaped', 'episode_revealed')
        reveal = by_arrival(events, 'episode_revealed', t.a2)[0]
        self.assertEqual(reveal['body']['outcome']['error_class'], 'episode_timeout')
        self.assertLess(reveal['seq'], end['seq'], 'the partner is revealed before the abort')
        ledger = end['body']['exposure_ledger']
        arm = reveal['body']['arm']
        self.assertGreaterEqual(ledger['randomizing'][arm]['unknown_usage_calls'], 1)
        self.assertEqual(ledger['unrevealed']['episodes'], 0)
        self.assertEqual(verifier_findings(t, 'episode.one_reveal'), [],
                         'every assigned arrival is revealed (pre-EB5 this FAILed)')
        self.assertTruthfulRecord(t)
        self.assertNoOrphans(t)

    def test_c2_mutation_drain_disabled_is_refused_and_drops_nothing(self):
        t = self.tree('C2MUT', idle_wait_s=2.0)
        t.serve(self.faults(t))
        t.start(mutation='drain_disabled')
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        end = terminal(events)
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        res = end['body']['resolution']
        self.assertEqual(res['superseded_reason'], 'receipt_mismatch')
        self.assertIn({'arrival': t.a2, 'attempt': 1, 'state': 'no_record'},
                      res['unresolved_attempts'])
        self.assertEqual(by_arrival(events, 'episode_revealed', t.a2), [])
        ledger = end['body']['exposure_ledger']
        self.assertEqual(ledger['unrevealed']['episodes'], 1)
        self.assertGreaterEqual(ledger['unrevealed']['unknown_usage_calls'], 1)
        self.assertEqual(_old_ledger_unknown(events[:end['seq']])
                         - sum(ledger[p][a]['unknown_usage_calls']
                               for p in ('randomizing', 'post_decision')
                               for a in ('incumbent', 'candidate')), 0)
        self.assertLess(_old_ledger_unknown(events[:end['seq']]),
                        ledger['totals']['unknown_usage_calls'],
                        'the pre-EB5 attribution drops the partner\'s call')
        self.assertTruthfulRecord(t)
        pid = t.worker_pid(t.a2)
        self.assertTrue(eb1.pid_alive(pid), 'the pre-EB5 abort left the partner running')
        os.killpg(pid, signal.SIGKILL)
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C3: a garbage spool line into a live worker
# --------------------------------------------------------------------------- #
class C3GarbageSpoolLine(Case):
    """C3: while position 2 is held inside its POST, the control appends a garbage line to its
    spool.  The orchestrator's next ingest raises ``SpoolError``: the worker is killed and its
    exit confirmed BEFORE the ``interrupted`` reveal, and it makes no further POST -- none at
    the trial's server, none at an observer bound on the port after the run.  The mutation
    ``spool_error_no_kill`` (the pre-EB5 path: reveal ``interrupted``, never poll again)
    leaves it running: it keeps sending (the observer counts its POST), the verdict refuses
    (``trial_aborted(unresolved_worker)``) and the verifier FAILs the reveal."""

    def inject(self, t: Tree) -> int:
        wait_for(lambda: t.posts(t.u2), 30, 'position 2 inside its POST')
        wait_for(lambda: any(r.get('kind') == 'episode_final' for r in t.spool(t.a1)), 30,
                 'position 1 finished')
        n = len(t.posts(t.u2))
        with open(t.spool_path(t.a2), 'ab') as fh:
            fh.write(b'{"this is": not json\n')
        return n

    def test_c3_kill_and_reap_before_the_interrupted_reveal(self):
        t = self.tree('C3', idle_wait_s=40.0)
        t.serve([hold(t.u2, 6.0)])
        t.start()
        n_at_injection = self.inject(t)
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        self.assertResolvedBefore(events, t.a2, 'killed_reaped', 'episode_revealed')
        reveal = by_arrival(events, 'episode_revealed', t.a2)[0]['body']
        self.assertEqual(reveal['outcome']['error_class'], 'interrupted')
        self.assertEqual(len(t.posts(t.u2)), n_at_injection, 'a POST after the kill')
        obs = Observer(t)
        try:
            time.sleep(6.0)
            self.assertEqual(obs.n(), 0, 'the killed worker sent after the run')
        finally:
            obs.close()
        self.assertEqual(terminal(events)['type'], 'trial_ended')
        self.assertEqual(verifier_findings(t, 'workers.resolved'), [])
        self.assertNoOrphans(t)

    def test_c3_mutation_no_kill_keeps_sending_and_is_refused(self):
        t = self.tree('C3MUT', idle_wait_s=2.0)
        t.serve([hold(t.u2, 6.0)])
        t.start(mutation='spool_error_no_kill')
        self.inject(t)
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(by_arrival(events, 'worker_resolved', t.a2), [])
        self.assertEqual(terminal(events)['body']['reason'], 'unresolved_worker')
        rules = [f['detail'].get('rule') for f in verifier_findings(t, 'workers.resolved')]
        self.assertIn('reveal_before_resolution', rules)
        pid = t.worker_pid(t.a2)
        obs = Observer(t)
        try:
            wait_for(lambda: obs.n() >= 1, 25, 'the unkilled worker\'s next POST')
        finally:
            obs.close()
        self.assertTrue(eb1.pid_alive(pid))
        os.killpg(pid, signal.SIGKILL)
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C4: the kill's reap is never confirmed
# --------------------------------------------------------------------------- #
class C4ReapNeverConfirmed(Case):
    """C4: with the mutation ``wait_times_out`` a worker's ``Popen.wait`` raises
    ``TimeoutExpired``: at the hard cap the SIGKILL is sent and its exit is NOT confirmed.  The
    attempt is recorded ``alive_unresolved`` (the old ``kill`` swallowed that and the reveal
    followed as if the process had exited), nothing further is enrolled, and the close refuses:
    ``trial_aborted(unresolved_worker)``, no ``trial_ended``.  The process was really killed, so
    nothing outlives the run.  C9 removes the verdict from this run."""

    def test_c4_alive_unresolved_refusal_no_trial_ended(self):
        t = self.tree('C4', idle_wait_s=20.0)
        t.serve([hold(t.u2, 9.0)])
        t.start(mutation='wait_times_out')
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        rec = self.assertResolvedBefore(events, t.a2, 'alive_unresolved', 'episode_revealed')
        self.assertIsNone(rec['returncode'])
        self.assertEqual(of(events, 'trial_ended'), [])
        end = terminal(events)
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        res = end['body']['resolution']
        self.assertEqual(res['unresolved_attempts'],
                         [{'arrival': t.a2, 'attempt': 1, 'state': 'alive_unresolved'}])
        self.assertIn('worker_unresolved', res['problems'])
        self.assertTruthfulRecord(t)
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C5: a file barrier between call_started and the POST
# --------------------------------------------------------------------------- #
class C5FileBarrier(Case):
    """C5 (understand_eb5 section 1: no witness existed of a POST entered after the snapshot):
    position 2 runs ``eb5_worker_entry``, which stops between its durable ``call_started`` and
    its POST until the control releases it; position 1's receipt mismatch aborts the trial.

    * released BEFORE the snapshot (while the abort drains): the POST reaches the trial's
      server, the call is answered, the worker exits on its own; nothing arrives later.
    * released AFTER the snapshot, with the EB5 drain: the worker was killed at the barrier at
      the hard cap (``killed_reaped``), its call is unfinished with usage ``null``, the verdict
      passes; the release then sends NOTHING (an observer on the port counts 0).
    * released after the snapshot with ``drain_disabled`` (pre-EB5): the terminal record is
      written over the live worker -- its call's row reads ``worker_state: no_record``, i.e.
      a USED PERMIT whose POST may still come (the run_smoke label) -- the verdict refuses
      (``trial_aborted(unresolved_worker)``), and the release sends the late POST, which the
      observer counts."""

    def arm(self, t: Tree) -> None:
        (t.barrier / ('hold_%d' % t.a2)).write_text('1', encoding='utf-8')

    def release(self, t: Tree) -> None:
        (t.barrier / ('release_%d' % t.a2)).write_text('1', encoding='utf-8')

    def at_barrier(self, t: Tree) -> None:
        wait_for(lambda: (t.barrier / ('at_%d' % t.a2)).exists(), 30,
                 'position 2 at the barrier')
        self.assertTrue(any(r.get('kind') == 'call_started' for r in t.spool(t.a2)),
                        'call_started is spooled before the barrier')

    def setup_tree(self, name: str) -> Tree:
        t = self.tree(name, barrier=True, idle_wait_s=20.0)
        t.serve([receipt_fault(t.u1)])
        self.arm(t)
        return t

    def test_c5_released_before_the_snapshot(self):
        t = self.setup_tree('C5pre')
        t.start()
        self.at_barrier(t)
        wait_for(lambda: any(r.get('kind') == 'episode_final' for r in t.spool(t.a1)), 30,
                 'position 1 (the receipt mismatch) finished')
        self.release(t)
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(terminal(events)['body']['reason'], 'receipt_mismatch')
        self.assertEqual(len(t.posts(t.u2)), 1, 'the released POST reached the server')
        self.assertResolvedBefore(events, t.a2, 'exited', 'terminal')
        self.assertEqual(terminal(events)['body']['resolution']['unfinished_calls'], [])
        obs = Observer(t)
        try:
            time.sleep(3.0)
            self.assertEqual(obs.n(), 0)
        finally:
            obs.close()
        self.assertTruthfulRecord(t)
        self.assertNoOrphans(t)

    def test_c5_released_after_the_snapshot_the_design_killed_it_first(self):
        t = self.setup_tree('C5post')
        t.start()
        self.at_barrier(t)
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        end = terminal(events)
        self.assertEqual(end['body']['reason'], 'receipt_mismatch')
        self.assertResolvedBefore(events, t.a2, 'killed_reaped', 'episode_revealed')
        (row,) = [r for r in end['body']['resolution']['unfinished_calls']
                  if r['arrival'] == t.a2]
        self.assertEqual((row['worker_state'], row['usage']), ('killed_reaped', None))
        self.assertEqual(end['body']['resolution']['verdict'], 'PASS')
        self.assertEqual(t.posts(t.u2), [], 'the held POST never reached the server')
        obs = Observer(t)
        try:
            self.release(t)
            time.sleep(4.0)
            self.assertEqual(obs.n(), 0, 'a killed worker sends no late POST')
        finally:
            obs.close()
        self.assertTruthfulRecord(t)
        self.assertNoOrphans(t)

    def test_c5_mutation_the_late_post_arrives_and_acceptance_refuses(self):
        t = self.setup_tree('C5mut')
        t.start(mutation='drain_disabled')
        self.at_barrier(t)
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        end = terminal(events)
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        self.assertEqual(of(events, 'trial_ended'), [])
        (row,) = [r for r in end['body']['resolution']['unfinished_calls']
                  if r['arrival'] == t.a2]
        self.assertEqual((row['worker_state'], row['usage']), ('no_record', None),
                         'the row is a used permit of an unresolved worker')
        pid = t.worker_pid(t.a2)
        self.assertTrue(eb1.pid_alive(pid))
        obs = Observer(t)
        try:
            self.release(t)
            wait_for(lambda: obs.n() >= 1, 20, 'the late POST at the observer')
        finally:
            obs.close()
        self.assertGreater(time.time_ns(), end['t_wall_ns'])
        self.assertTruthfulRecord(t)
        try:
            os.killpg(pid, signal.SIGKILL)               # it may have finished by itself
        except OSError:
            pass
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C6: the dispatcher exits mid-episode, then the resume
# --------------------------------------------------------------------------- #
class C6DispatcherExitsMidEpisode(Case):
    """C6: the orchestrator is SIGKILLed while position 2 is inside a held POST (as in
    tests_lab_serving.py:1434: its workers, in their own sessions, survive).  The resume reads
    the worker's pid AND identity, kills its process group and confirms it gone
    (``worker_resolved(killed_reaped)`` in the resumed invocation) BEFORE it reveals the attempt
    ``interrupted``; the trial ends; nothing reaches the port afterwards.  Mutation
    ``no_orphan_resolution`` (pre-EB5: ``finished()`` read 0, no liveness check) reveals the live
    orphan ``interrupted`` -- it keeps sending (an observer counts its POST), the verdict refuses
    and the verifier FAILs the reveal.  Mutation ``orphan_kill_fails``: the resume REFUSES --
    ``invocation_ended(refused)``, exit 3, no reveal, no server start -- and a later resume, once
    the orphan is gone, completes the trial."""

    def first_invocation(self, name: str) -> Tree:
        t = self.tree(name, idle_wait_s=20.0, execution={'max_connection_retries': 4})
        t.serve([hold(t.u2, 60.0)], after=3)
        t.start()
        wait_for(lambda: t.posts(t.u2), 30, 'position 2 inside its POST')
        wait_for(lambda: any(r.get('kind') == 'episode_final' for r in t.spool(t.a1)), 30,
                 'position 1 finished')
        t.kill_orchestrator()
        self.orphan = t.worker_pid(t.a2)
        self.assertTrue(eb1.pid_alive(self.orphan), 'the worker survived its dispatcher')
        self.first_len = len(t.chain())
        return t

    def resumed(self, events, first_len: int) -> list:
        return events[first_len:]

    def test_c6_the_orphan_is_killed_and_reaped_before_the_interrupted_reveal(self):
        t = self.first_invocation('C6')
        t.start(resume=True)
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        second = self.resumed(events, self.first_len)
        self.assertEqual(second[0]['type'], 'invocation_started')
        rec = self.assertResolvedBefore(second, t.a2, 'killed_reaped', 'episode_revealed')
        self.assertEqual(rec['pid'], self.orphan)
        self.assertEqual(by_arrival(second, 'episode_revealed', t.a2)[0]['body']['outcome']
                         ['error_class'], 'interrupted')
        self.assertFalse(eb1.pid_alive(self.orphan) and 'worker_entry'
                         in eb1.pid_command(self.orphan))
        self.assertEqual(terminal(events)['type'], 'trial_ended')
        new_pids = {r['pid'] for r in t.launches()[1:]}
        self.assertEqual([p for p in t.posts(t.u2) if p['pid'] in new_pids], [],
                         'the orphan sent nothing to the resumed server')
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)

    def test_c6_mutation_no_resolution_reveals_a_live_orphan(self):
        t = self.first_invocation('C6mut')
        t.start(mutation='no_orphan_resolution', resume=True)
        self.assertEqual(t.finish(self), 1, t.stdout[-3000:])
        events = t.chain()
        second = self.resumed(events, self.first_len)
        self.assertEqual(by_arrival(second, 'worker_resolved', t.a2), [])
        self.assertEqual(by_arrival(second, 'episode_revealed', t.a2)[0]['body']['outcome']
                         ['error_class'], 'interrupted')
        self.assertEqual(terminal(events)['body']['reason'], 'unresolved_worker')
        rules = [f['detail'].get('rule') for f in verifier_findings(t, 'workers.resolved')]
        self.assertIn('reveal_before_resolution', rules)
        self.assertTrue(eb1.pid_alive(self.orphan), 'revealed interrupted while alive')
        obs = Observer(t)
        try:
            wait_for(lambda: obs.n() >= 1, 25, 'the live orphan\'s next POST')
        finally:
            obs.close()
        os.killpg(self.orphan, signal.SIGKILL)
        self.assertNoOrphans(t)

    def test_c6_mutation_the_kill_fails_so_the_resume_refuses(self):
        t = self.first_invocation('C6ref')
        t.start(mutation='orphan_kill_fails', resume=True)
        self.assertEqual(t.finish(self), 3, t.stdout[-3000:])
        events = t.chain()
        second = [e for e in self.resumed(events, self.first_len)
                  if e['type'] != 'log_recovery']
        # the partner (gone) may be recorded exited; the orphan is NOT recorded, nothing is
        # revealed, started or dispatched: the invocation ends refused
        self.assertEqual(second[0]['type'], 'invocation_started')
        self.assertEqual(second[-1]['type'], 'invocation_ended')
        self.assertEqual([(e['type'], e['body']['arrival'], e['body']['state'])
                          for e in second[1:-1]],
                         [('worker_resolved', t.a1, 'exited')][:len(second) - 2])
        self.assertEqual(second[-1]['body']['status'], 'refused')
        self.assertEqual(second[-1]['body']['counts']['workers_alive_unresolved'], 1)
        self.assertEqual(len(t.launches()), 1, 'the refused resume started no server')
        self.assertTrue(eb1.pid_alive(self.orphan), 'the orphan is still running')
        os.killpg(self.orphan, signal.SIGKILL)            # the operator's manual step
        wait_for(lambda: orch.probe_worker(self.orphan, 'job_%d_1.json' % t.a2) == 'gone',
                 10, 'the orphan gone')
        t.first_procs.append(t.proc)
        t.start(resume=True)
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        starts = [i for i, e in enumerate(events) if e['type'] == 'invocation_started']
        third = events[starts[-1]:]
        rec = self.assertResolvedBefore(third, t.a2, 'exited', 'episode_revealed')
        self.assertIsNone(rec['returncode'])
        self.assertEqual(terminal(events)['type'], 'trial_ended')
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C9: without the verdict, trial_ended
# --------------------------------------------------------------------------- #
class C9TheVerdictIsWhatRefuses(Case):
    """C9: the mutation ``bypass_verdict`` replaces ``phase_resolution_verdict`` with a PASS
    record and changes nothing else.  C1(b)'s run then writes ``trial_ended`` over a busy
    server, and C4's writes ``trial_ended`` over an ``alive_unresolved`` worker: the refusals of
    C1(b) and C4 are the verdict's.  The verifier's ``workers.resolved`` then FAILs both chains
    (the fabricated record disagrees with its recount; C4's recount finds the unresolved
    worker) -- except the busy server itself, which the verifier cannot observe."""

    def test_c9_on_c1b_inputs(self):
        t = self.tree('C9c1', idle_wait_s=2.0)
        t.serve([hold(t.u2, 45.0)])
        t.start(mutation='bypass_verdict')
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(terminal(events)['type'], 'trial_ended')
        rules = [f['detail'].get('rule') for f in verifier_findings(t, 'workers.resolved')]
        self.assertIn('resolution_record', rules)
        self.assertNoOrphans(t)

    def test_c9_on_c4_inputs(self):
        t = self.tree('C9c4', idle_wait_s=20.0)
        t.serve([hold(t.u2, 9.0)])
        t.start(mutation='wait_times_out,bypass_verdict')
        self.assertEqual(t.finish(self), 0, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(terminal(events)['type'], 'trial_ended')
        self.assertEqual(by_arrival(events, 'worker_resolved', t.a2)[0]['body']['state'],
                         'alive_unresolved')
        rules = [f['detail'].get('rule') for f in verifier_findings(t, 'workers.resolved')]
        self.assertIn('ended_unresolved', rules)
        self.assertNoOrphans(t)


if __name__ == '__main__':
    unittest.main()
