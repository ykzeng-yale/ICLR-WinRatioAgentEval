"""The supervisor's ACTUAL entry point, driven with everything external mocked.

Root, 2026-09-23 12:04, answering the question I put to it:

    "Yes: establish the bounded mocked actual-main harness next, as the test
     scaffold for the existing repair batch. Exercise the known failures and a
     valid control through the actual entry point; mock child processes, HTTP,
     signals and time. Keep real serialization/retention/finalization against
     unique temporary closed artifacts, and assert the persisted files
     independently of their self-reported flags."

WHY THIS MODULE EXISTS -- a correction to how I test, not a new feature.

Every defect root found in this contract was invisible to my helper-level tests
and obvious from the entry point:

  * `Deadline.bounded()` was correct and the dispatch path never called it. My
    tests proved the arithmetic, which was never in doubt.
  * `child_confirmed_stopped` was recorded and the files were read anyway.
  * the receipt forwarded the old byte counter beside the newly measured hash.
  * a broken barrier still sent both requests.

A helper tested in isolation says nothing about whether anything calls it. Root
was supplying the harness I lacked, which made my green suites carry less
information than they appeared to.

THE RULE HERE: every assertion is against the receipt READ BACK FROM DISK, never
against the in-memory dict the code just built and never against a flag the code
set about itself. Root: "assert the persisted files independently of their
self-reported flags."

WHERE IT LIVES. Beside `run_smoke.py` and deliberately NOT in
`experiments/live_ab/`, whose `*.py` glob is `lab_common.HARNESS_FILES` and
feeds the `harness_file_sha256` freeze pin. Adding a test there would move a
freeze pin, which is defect D8 from 2026-09-21.

Adapted from root's six-case reproduction fixture
`reviews/evidence/request_delta_harness_20260923_1204.py`, supplied "for
adaptation into owner tests ... a reproducibility fixture, not production code".
The mocking strategy is root's; the cases and the read-back assertions are this
module's own.

WHAT IS AND IS NOT ISOLATED -- corrected 2026-09-23 12:42, because the first
version of this docstring overstated it.

The first version said "no child process ... no real clock". Both were wrong in
the same delivery that reported them:

  * `fake_popen` DELEGATED every non-launcher command to the real `Popen`, so
    `lab_data.boot_identity` did spawn real `sysctl` processes. Root: "The
    owner's report says sysctl subprocesses were used while also saying no child
    process ran." Now an unexpected process raises instead of executing, and the
    existing `clock_provenance` mock removes the reason it was ever needed.
  * the module did NOT patch the monotonic clock, despite claiming to.
    `Deadline` binds `time.monotonic` as a default argument, so patching the
    module afterwards would not have reached it. One explicit fake clock is now
    injected, including through the constructor.

Root asked that the phase wording distinguish reported prior behaviour, possible
fallback behaviour and independently observed guarded behaviour; that is what
this note does, and no sysctl was run to settle it.

WHAT RUNS NOW: no child process (attempts are denied and fail the test), no
HTTP, no signal, no real monotonic clock, no server, no model, no network, no
build. Serialization, retention and finalization are REAL, against fresh
temporary files. The saved smoke fixtures are a dependency: if they are absent
these cases SKIP, and a skipped case is not a passing one.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))


def _load_run_smoke():
    spec = importlib.util.spec_from_file_location(
        'run_smoke_under_test', HERE / 'run_smoke.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Proc:
    """A child that never existed. `returncode` stays None until reaped."""

    pid = 987654

    def __init__(self, *, exit_code=0, stdout=b'synthetic diagnostic\n', reaps=True):
        self.returncode = None
        self._exit_code = exit_code
        self._reaps = reaps
        self.stdout = io.BytesIO(stdout)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if not self._reaps:
            raise RuntimeError('mock child refuses to be reaped')
        self.returncode = self._exit_code
        return self.returncode


class _Resp:
    def __init__(self, payload):
        self._p = payload
        self.status_code = 200
        self.content = json.dumps(payload).encode()

    def json(self):
        return self._p


OK_BODY = {'usage': {'completion_tokens': 10, 'prompt_tokens': 3},
           'choices': [{'finish_reason': 'stop', 'message': {'content': 'ok'}}]}


class SupervisorEntryPointTests(unittest.TestCase):

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.rs = _load_run_smoke()
        smoke = REPO / 'results/live_ab/SMOKE_RECEIPT_smoke_4167e395ccfd.json'
        man = REPO / 'results/live_ab/SMOKE_LAUNCH_MANIFEST_smoke_4167e395ccfd.json'
        cls.have = smoke.is_file() and man.is_file()
        if cls.have:
            cls.saved = json.loads(smoke.read_text('utf-8'))
            cls.manifest = json.loads(man.read_text('utf-8'))

    def setUp(self):
        if not self.have:
            self.skipTest('the saved smoke fixtures are not in this checkout')
        td = tempfile.TemporaryDirectory(prefix='sup_entry_')
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.results = self.root / 'results'
        self.results.mkdir()
        self.log = self.root / 'lifecycle.jsonl'
        lines = [json.loads(s) for s in self.saved['raw_log_lines']]
        lines[-1]['sidecar_failures'] = 0
        self.log.write_text(''.join(json.dumps(s) + '\n' for s in lines), encoding='utf-8')
        self.binary = self.root / 'launcher'
        self.binary.write_bytes(b'LAUNCHER BYTES')
        self.model = self.root / 'weights.gguf'
        self.model.write_bytes(b'WEIGHT BYTES')
        m = copy.deepcopy(self.manifest)
        m.setdefault('launcher', {})['sha256'] = hashlib.sha256(
            self.binary.read_bytes()).hexdigest()
        m.setdefault('model', {})['sha256'] = hashlib.sha256(
            self.model.read_bytes()).hexdigest()
        m['model']['file'] = 'weights.gguf'
        # THE IMPLEMENTATION LIBRARIES, declared and present. Root, 11:16: "the
        # small launcher is not the implementation"; a manifest that declares no
        # non-system closure now refuses before Popen. The fixture declares one
        # rather than the rule being relaxed to fit it.
        self.libs = {}
        for name, blob in (('libllama-server-impl.dylib', b'IMPL BYTES'),
                           ('libggml-base.0.dylib', b'GGML BYTES')):
            (self.root / name).write_bytes(blob)
            self.libs[name] = {'sha256': hashlib.sha256(blob).hexdigest()}
        m['non_system_library_closure'] = copy.deepcopy(self.libs)
        self.man_path = self.root / 'manifest.json'
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        # THE TOKEN AND PROVENANCE MUST BE THE ONES THE SAVED RECORDS CARRY.
        # My first attempt used a fresh token, so every record in the saved log
        # was refused as belonging to another run and the "control" refused for
        # a reason that had nothing to do with the case. A control that fails
        # for an unrelated reason is worse than no control.
        self.token = self.saved['run_token']
        self.prov = {k: self.saved['observation'][k]
                     for k in ('host_id', 'boot_id', 'host_source', 'boot_source')}
        m2 = json.loads(self.man_path.read_text('utf-8'))
        m2['host_id'] = self.prov['host_id']
        m2['boot_id'] = self.prov['boot_id']
        self.man_path.write_text(json.dumps(m2), encoding='utf-8')
        self.pointer = self.root / 'pointer.txt'
        self._write_pointer(self.man_path)

    def _write_pointer(self, manifest_path, token=None):
        self.pointer.write_text(
            '%s\n%s\n%s\n' % (manifest_path, self.log, token or self.token),
            encoding='utf-8')

    # -- the harness ---------------------------------------------------------
    def _run(self, *, proc=None, bodies=None, break_barrier=False,
             popen_raises=None, no_pointer=False, post_hook=None):
        rs = self.rs
        proc = proc if proc is not None else _Proc()
        bodies = bodies if bodies is not None else [OK_BODY, OK_BODY]
        posted = []

        def fake_post(url, json=None, timeout=None, **kw):
            posted.append({'url': url, 'timeout': timeout})
            if post_hook is not None:
                return post_hook(url, json=json, timeout=timeout, **kw)
            payload = bodies[min(len(posted) - 1, len(bodies) - 1)]
            if isinstance(payload, Exception):
                raise payload
            return _Resp(payload)

        class _Barrier:
            def __init__(self, n):
                pass

            def wait(self, timeout=None):
                if break_barrier:
                    raise RuntimeError('broken barrier')

        class _Thread:
            def __init__(self, target, args=(), kwargs=None, daemon=None, name=None):
                self.target, self.args, self.kwargs = target, args, kwargs or {}
                self.name = name

            def start(self):
                self.target(*self.args, **self.kwargs)

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return False

        self.denied = []

        def fake_popen(args, *a, **k):
            # NO UNRESTRICTED FALLBACK. Root, 2026-09-23 12:42: "The shipped
            # `fake_popen` delegates every non-launcher command to real `Popen`
            # ... reject unexpected process creation rather than letting it
            # execute."
            #
            # It delegated because `rs.subprocess` IS the subprocess module, so
            # a blanket patch also broke `lab_data.boot_identity`, which shells
            # out to sysctl. Root's answer is better than mine: the existing
            # `clock_provenance` mock already removes that need, so an
            # unexpected process is a TEST FAILURE, not something to execute.
            if not (args and str(args[0]) == str(self.binary)):
                self.denied.append([str(x) for x in (args or [])])
                raise AssertionError(
                    'the suite attempted an unexpected process: %r. Nothing but '
                    'the launcher may be created here.' % (args,))
            if popen_raises is not None:
                raise popen_raises
            return proc

        fake_requests = type('R', (), {
            'post': staticmethod(fake_post),
            'get': staticmethod(lambda *a, **k: _Resp({'status': 'ok'}))})

        # A READ SPY. Root, 12:42: "Reading a receipt back from disk verifies
        # persistence. A receipt lacking `raw_log` or carrying `observation=null`
        # does not independently prove the lifecycle file was never read ... spy
        # on the relevant lifecycle/sidecar reads and observer calls after
        # fixture setup, and require zero premature reads."
        #
        # Right: my unreapable-child test INFERRED absence from missing receipt
        # fields, which is the self-report this module exists not to trust.
        self.reads = []
        self.observer_calls = []
        watched = {str(self.log), str(self.log) + '.error'}
        real_open = Path.open
        real_read_bytes = Path.read_bytes

        def spy_open(pself, *a, **k):
            if str(pself) in watched:
                self.reads.append(('open', str(pself)))
            return real_open(pself, *a, **k)

        def spy_read_bytes(pself, *a, **k):
            if str(pself) in watched:
                self.reads.append(('read_bytes', str(pself)))
            return real_read_bytes(pself, *a, **k)

        real_observe = rs.lab_lifecycle.observe

        def spy_observe(*a, **k):
            self.observer_calls.append(str(a[0]) if a else None)
            return real_observe(*a, **k)

        real_read_text = Path.read_text
        pointer = self.pointer

        def reader(p, *a, **k):
            if str(p) in watched:
                self.reads.append(('read_text', str(p)))
            if str(p) == '/tmp/lab_smoke_manifest.txt':
                if no_pointer or not pointer.exists():
                    raise FileNotFoundError('no pointer')
                return real_read_text(pointer, *a, **k)
            return real_read_text(p, *a, **k)

        # ONE EXPLICIT FAKE CLOCK. Root, 12:42: "The shipped test module does
        # not patch the monotonic clock or inject `Deadline(now=...)`, despite
        # the clock-mocked claim. Use one explicit fake clock, including the
        # constructor's bound default."
        #
        # My docstring said the clock was mocked. It was not: `Deadline` binds
        # `time.monotonic` as a default argument, so patching the module
        # afterwards would not have reached it either. The claim was false and
        # is corrected here rather than in the wording alone.
        self.clock = [1000.0]
        fake_monotonic = lambda: self.clock[0]
        real_deadline = rs.Deadline

        def clocked_deadline(budget_s, *, reserve_s=rs.CLEANUP_RESERVE_S, now=None):
            return real_deadline(budget_s, reserve_s=reserve_s, now=fake_monotonic)

        import lab_data
        with mock.patch.object(rs, 'Deadline', clocked_deadline), \
                mock.patch.object(rs.time, 'monotonic', fake_monotonic), \
                mock.patch.object(lab_data, 'clock_provenance', lambda: dict(self.prov)), \
                mock.patch.object(rs, 'BIN', self.binary), \
                mock.patch.object(rs.lab_common, 'RESULTS_ROOT', str(self.results)), \
                mock.patch.object(rs.subprocess, 'Popen', fake_popen), \
                mock.patch.object(rs.threading, 'Thread', _Thread), \
                mock.patch.object(rs.threading, 'Barrier', _Barrier), \
                mock.patch.object(rs.os, 'killpg', lambda *a: None), \
                mock.patch.object(rs.os, 'getpgid', lambda p: p), \
                mock.patch.object(Path, 'read_text', reader), \
                mock.patch.object(Path, 'open', spy_open), \
                mock.patch.object(Path, 'read_bytes', spy_read_bytes), \
                mock.patch.object(rs.lab_lifecycle, 'observe', spy_observe), \
                mock.patch.dict(sys.modules, {'requests': fake_requests}), \
                mock.patch('glob.glob', lambda *a, **k: [str(self.model)]):
            status = rs.main()
        self.posted = posted
        return status, self._persisted()

    def _persisted(self):
        """The receipt READ BACK FROM DISK. Never the in-memory dict."""
        files = sorted(self.results.glob('SMOKE_RECEIPT_*.json'))
        self.assertLessEqual(len(files), 1,
                             'at most one terminal receipt, found %r'
                             % [f.name for f in files])
        return json.loads(files[0].read_text('utf-8')) if files else None

    # -- cases ---------------------------------------------------------------
    def test_a_valid_run_writes_one_receipt_and_returns_zero(self):
        """THE CONTROL. Without it every refusal below is consistent with a
        supervisor that refuses everything."""
        status, receipt = self._run()
        self.assertIsNotNone(receipt, 'a terminal receipt must exist on disk')
        self.assertEqual(len(self.posted), 2)
        self.assertEqual(receipt['submitted_requests'], 2)
        self.assertEqual(receipt['generated_tokens_total'], 20)
        self.assertTrue(receipt['token_cap_respected'])
        self.assertEqual(receipt['supervisor_problems'], [])
        self.assertEqual(status, 0)

    def test_a_broken_barrier_sends_NOTHING_and_refuses(self):
        """Root's witness, now mine: the early-broken-barrier case used to make
        both POST calls and return success."""
        status, receipt = self._run(break_barrier=True)
        self.assertEqual(self.posted, [], 'no request may be sent uncoordinated')
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['submitted_requests'], 0)
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertIsNone(receipt['token_cap_respected'])
        self.assertTrue(receipt['supervisor_problems'])
        self.assertEqual(status, 1)
        for row in receipt['requests']:
            self.assertIn('not_dispatched', row)
            self.assertIn('barrier_error', row)

    def test_a_failed_process_creation_leaves_ONE_receipt_on_disk(self):
        """The runs that failed worst used to leave the least evidence."""
        status, receipt = self._run(popen_raises=OSError('no exec'))
        self.assertIsNotNone(receipt, 'a Popen failure must still persist a receipt')
        self.assertFalse(receipt['child_started'])
        self.assertIsNone(receipt['loaded_a_model'],
                          'loading is unobserved before the child exists')
        self.assertTrue(receipt['attempted'])
        self.assertEqual(self.posted, [])
        self.assertEqual(status, 1)

    def test_a_missing_pointer_leaves_ONE_receipt_on_disk(self):
        status, receipt = self._run(no_pointer=True)
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt['child_started'])
        self.assertTrue(any('manifest' in p for p in receipt['supervisor_problems']))
        self.assertEqual(status, 1)

    def test_negative_usage_is_unusable_on_the_ROW_as_well_as_the_total(self):
        """Root, 12:04: "its request rows still label completion_tokens=-1 as
        usage_known=true ... derive both row and total usability from the same
        nonnegative, non-boolean integer rule." The aggregate was strict while
        the row it summarised was not, so the receipt disagreed with itself."""
        bad = {'usage': {'completion_tokens': -1},
               'choices': [{'finish_reason': 'stop', 'message': {'content': 'x'}}]}
        status, receipt = self._run(bodies=[bad, bad])
        self.assertIsNotNone(receipt)
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertIsNone(receipt['token_cap_respected'])
        for row in receipt['requests']:
            self.assertFalse(row['usage_known'])
            self.assertIn('usage_unusable_reason', row)
            self.assertEqual(row['usage']['completion_tokens'], -1,
                             'the original value must be preserved, not coerced')
        self.assertEqual(status, 1)

    def test_a_genuine_zero_from_a_real_response_is_a_measurement(self):
        zero = {'usage': {'completion_tokens': 0},
                'choices': [{'finish_reason': 'stop', 'message': {'content': ''}}]}
        status, receipt = self._run(bodies=[zero, zero])
        self.assertEqual(receipt['generated_tokens_total'], 0)
        self.assertTrue(receipt['token_cap_respected'])
        self.assertEqual(status, 0)

    def test_an_unreapable_child_reads_NOTHING_and_refuses(self):
        """The gate root asked for: a later nonzero verdict cannot undo reading
        a file that may still be written."""
        status, receipt = self._run(proc=_Proc(reaps=False))
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt['child_confirmed_stopped'])
        # OBSERVED, not inferred. Root, 12:42: "A receipt lacking `raw_log` or
        # carrying `observation=null` does not independently prove the lifecycle
        # file was never read." The spy records every open/read of the lifecycle
        # file and its sidecar, and every call to the observer.
        self.assertEqual(self.reads, [],
                         'the lifecycle log and sidecar must not have been read; '
                         'the spy saw %r' % (self.reads,))
        self.assertEqual(self.observer_calls, [],
                         'the observer must not have been called at all')
        self.assertIsNone(receipt['observation'])
        self.assertIn('acquisition_not_analyzed', receipt)
        self.assertEqual(status, 1)

    def test_the_read_spy_DOES_see_reads_on_the_healthy_path(self):
        """The control for the spy itself. Without it, 'zero reads observed'
        is equally consistent with a spy that observes nothing."""
        status, receipt = self._run()
        self.assertEqual(status, 0)
        self.assertTrue(self.reads,
                        'a completed acquisition must read the lifecycle file')
        self.assertTrue(self.observer_calls,
                        'a completed acquisition must call the observer')

    def test_request_intent_is_ON_DISK_before_any_transport(self):
        """Root, 2026-09-23 11:16: "`out['planned_request_intent'] = planned` is
        only memory until terminal finalization. In the actual-main witness,
        both barriers and both POST calls observe zero durable writes."

        Asserted by reading the intent FILE, and by checking during the POST
        that it already existed -- a receipt field saying "persisted" would be
        exactly the self-report this module exists not to trust.
        """
        seen = []

        def watcher(url, json=None, timeout=None, **kw):
            # at the moment of transport, what is on disk?
            seen.append(sorted(q.name for q in self.log.parent.glob('*.intent.json')))
            return _Resp(OK_BODY)

        status, receipt = self._run(post_hook=watcher)
        self.assertTrue(seen, 'the transport was never invoked')
        for snapshot in seen:
            self.assertEqual(snapshot, ['%s.intent.json' % self.token],
                             'the intent file must exist BEFORE the POST')

        art = receipt['request_intent_artifact']
        self.assertTrue(art['persisted'])
        on_disk = json.loads((self.log.parent
                              / ('%s.intent.json' % self.token)).read_text('utf-8'))
        self.assertEqual(len(on_disk['planned_requests']), 2)
        self.assertEqual(on_disk['run_token'], self.token)
        for row in on_disk['planned_requests']:
            self.assertIn('request_id', row)
            self.assertIn('payload_sha256', row)
            self.assertIn('payload', row)
        # the terminal receipt must NOT have erased it
        self.assertTrue((self.log.parent / ('%s.intent.json' % self.token)).exists())
        self.assertEqual(status, 0)

    def test_a_timed_out_request_is_ATTEMPTED_with_unknown_delivery(self):
        """Root: "a request that was attempted and then timed out still counts
        as unsubmitted ... records submitted_requests=0 and incorrectly calls
        both 'never submitted'. Record transport invocation before the call and
        response receipt afterward; preserve timeout and unknown server
        receipt/usage without claiming no request was sent."
        """
        boom = RuntimeError('read timed out')
        status, receipt = self._run(bodies=[boom, boom])
        self.assertEqual(len(self.posted), 2, 'the transport WAS invoked twice')
        self.assertEqual(receipt['transport_attempted_requests'], 2)
        self.assertEqual(receipt['submitted_requests'], 0)
        self.assertEqual(receipt['requests_with_unknown_delivery'], 2)
        for row in receipt['requests']:
            self.assertTrue(row['transport_attempted'])
            self.assertFalse(row['response_received'])
            self.assertEqual(row['delivery'], 'unknown_server_receipt')
            self.assertNotIn('not_dispatched', row,
                             'an attempted request was not "never dispatched"')
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertEqual(status, 1)

    def test_the_WHOLE_response_body_is_on_disk_not_just_a_preview(self):
        """Root: "Length, hash and a 4,000-character preview cannot recover the
        omitted bytes. Valid responses longer than 9 KB return supervisor
        success while their tail bytes are absent from every persisted file."
        """
        long_content = 'y' * 12000
        big = {'usage': {'completion_tokens': 5},
               'choices': [{'finish_reason': 'stop',
                            'message': {'content': long_content}}]}
        status, receipt = self._run(bodies=[big, big])
        self.assertEqual(status, 0)
        for row in receipt['requests']:
            rr = row['raw_response']
            self.assertTrue(rr['retained'])
            self.assertTrue(rr['complete'])
            self.assertTrue(rr['preview_truncated'],
                            'the preview IS shortened -- that is the point')
            # the FILE, not the receipt's description of it
            f = self.log.parent / ('%s.response' % row['request_id'])
            self.assertTrue(f.exists())
            blob = f.read_bytes()
            self.assertEqual(len(blob), rr['bytes'])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), rr['sha256'])
            self.assertIn(long_content.encode(), blob,
                          'the tail bytes must be recoverable from the artifact')
            self.assertGreater(len(blob), rr['preview_chars_cap'])

    def test_a_CHANGED_IMPLEMENTATION_LIBRARY_refuses_before_launch(self):
        """Root, 2026-09-23 11:16: "the actual `non_system_library_closure`
        declaration can name a sibling implementation library whose bytes have
        changed and still receive verified=true ... The small launcher is not
        the implementation."

        The built launcher is 33,472 bytes; every line of instrumented server
        code lives in `libllama-server-impl.dylib` and the ggml backends beside
        it. A two-file launcher/model check could pass while the code that
        actually runs had changed.
        """
        # the launcher and model are untouched; one sibling library is not
        (self.root / 'libllama-server-impl.dylib').write_bytes(b'TAMPERED IMPL')
        status, receipt = self._run()
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt['launch_verification']['verified'])
        self.assertTrue(any('libllama-server-impl' in p
                            for p in receipt['launch_verification']['problems']))
        self.assertFalse(receipt['child_started'],
                         'nothing may launch once an input fails its pin')
        self.assertEqual(self.posted, [])
        self.assertEqual(status, 1)

    def test_a_manifest_with_NO_declared_closure_refuses(self):
        """A missing required input refuses before Popen; the launcher alone is
        not acceptance of the candidate instrument."""
        m = json.loads(self.man_path.read_text('utf-8'))
        del m['non_system_library_closure']
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        self.assertFalse(receipt['launch_verification']['verified'])
        self.assertTrue(any('no non-system library closure' in p
                            for p in receipt['launch_verification']['problems']))
        self.assertFalse(receipt['child_started'])
        self.assertEqual(status, 1)

    def test_a_producer_that_refused_itself_invalidates_a_clean_log(self):
        """Exit 93 beside a readable seal full of zeros must still refuse."""
        status, receipt = self._run(proc=_Proc(exit_code=93))
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['server_exit_code'], 93)
        self.assertTrue(receipt['acquisition_invalidated_by_process_outcome'])
        self.assertEqual(status, 1)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
