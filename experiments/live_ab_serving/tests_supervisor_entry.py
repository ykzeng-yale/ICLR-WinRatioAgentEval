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
import os
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
        # A REAL OS PIPE, not a BytesIO. Root, 16:30: production main() must
        # require a verified usable non-blocking pipe, so the fixture child
        # gives it one: the bytes are written, the write end closed, and the
        # drain meets data then EOF through a real descriptor and select().
        # Well under the pipe buffer, so the write can never block.
        assert len(stdout) < 16384, 'fixture output must fit the pipe buffer'
        r, w = os.pipe()
        try:
            os.write(w, stdout)
        finally:
            os.close(w)
        self.stdout = self._pipe = os.fdopen(r, 'rb', buffering=0)

    def close(self):
        # Its OWN pipe, even when a test has swapped `stdout` for something else.
        try:
            self._pipe.close()
        except Exception:                                      # noqa: BLE001
            pass

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if not self._reaps:
            raise RuntimeError('mock child refuses to be reaped')
        self.returncode = self._exit_code
        return self.returncode


class _Suspend(BaseException):
    """A POST that has not returned while the supervisor looks."""


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
        # CANONICAL: on macOS the temporary root is under /var, a symlink to
        # /private/var, and the closure refuses a launcher path that is not
        # canonical -- as it should.
        self.root = Path(td.name).resolve()
        self.results = self.root / 'results'
        self.results.mkdir()
        self.log = self.root / 'lifecycle.jsonl'
        lines = [json.loads(s) for s in self.saved['raw_log_lines']]
        lines[-1]['sidecar_failures'] = 0
        self.log.write_text(''.join(json.dumps(s) + '\n' for s in lines), encoding='utf-8')
        # THE LAUNCHER LIVES IN ITS OWN DIRECTORY, the child's cwd and a loader
        # search location; logs and receipts sit OUTSIDE it, as root requires.
        self.bindir = self.root / 'bin'
        self.bindir.mkdir()
        self.binary = self.bindir / 'llama-server'
        self.binary.write_bytes(b'LAUNCHER BYTES')
        self.model = self.root / 'weights.gguf'
        self.model.write_bytes(b'WEIGHT BYTES')
        m = copy.deepcopy(self.manifest)
        m.setdefault('launcher', {})['sha256'] = hashlib.sha256(
            self.binary.read_bytes()).hexdigest()
        m.setdefault('model', {})['sha256'] = hashlib.sha256(
            self.model.read_bytes()).hexdigest()
        m['model']['file'] = 'weights.gguf'
        # DECLARED FIXTURE INPUT. The retained manifest predates the bound
        # limits, so the three it lacks are declared here -- as LITERALS, the
        # values root named, never copied from `rs.BOUND_LIMITS`: a fixture that
        # read the code's own constants would compare the code with itself.
        m['caps'].update({'cleanup_reserve_seconds': 90,
                          'dispatch_cutoff_seconds': 510,
                          'diagnostic_byte_budget': 8 * 1024 * 1024})
        # THE IMPLEMENTATION LIBRARIES, declared and present. Root, 11:16: "the
        # small launcher is not the implementation"; a manifest that declares no
        # non-system closure now refuses before Popen. The fixture declares one
        # rather than the rule being relaxed to fit it.
        self.libs = {}
        for name, blob in (('libllama-server-impl.dylib', b'IMPL BYTES'),
                           ('libggml-base.0.dylib', b'GGML BYTES')):
            (self.bindir / name).write_bytes(blob)
            self.libs[name] = {'sha256': hashlib.sha256(blob).hexdigest()}
        m.pop('non_system_library_closure', None)
        # THE WIRED LAUNCH RECORD (root 16:30, 17:52). A real v3 closure is
        # FROZEN over these fixture files -- synthetic load commands, but the
        # real filesystem, the real directory enumeration and the real realpath
        # -- and bound with a fixture patch, the real build-snapshot receipt and
        # the real code pins. Preflight re-derives it with the same readers.
        dc = self.rs.dc
        graph = {
            str(self.binary): {'refs': ['@rpath/libllama-server-impl.dylib'],
                               'rpaths': ['@loader_path']},
            str(self.bindir / 'libllama-server-impl.dylib'): {
                'refs': ['@rpath/libggml-base.0.dylib'], 'rpaths': ['@loader_path'],
                'id': '@rpath/libllama-server-impl.dylib'},
            str(self.bindir / 'libggml-base.0.dylib'): {
                'refs': [], 'id': '@rpath/libggml-base.0.dylib'},
        }

        def metadata(path):
            g = graph.get(path)
            if g is None:
                return {'error': 'no fixture metadata for %s' % path}
            return {'path': path, 'install_name': g.get('id'), 'rpaths': g['rpaths']
                    if 'rpaths' in g else [],
                    'load_references': [{'command': 'LC_LOAD_DYLIB', 'reference': r}
                                        for r in g['refs']]}
        self.dep_readers = {
            'metadata': metadata, 'exists': os.path.exists,
            'read_bytes': lambda p: Path(p).read_bytes(),
            'dynamic_loader': lambda p: {'dlopen': False},
            'enumerate_dir': dc.discovery_candidates, 'realpath': os.path.realpath}
        frozen = dc.derive_closure(
            str(self.binary), launch_context={
                'executable_invoked_path': str(self.binary), 'cwd': str(self.bindir),
                'compiled_backend_dir': None, 'environment': {}},
            **self.dep_readers)
        assert frozen['resolved'], frozen['unresolved']
        m['dependency_closure'] = frozen
        m['launcher']['sha256'] = frozen['files'][str(self.binary)]['sha256']
        self.patch_file = self.root / 'fixture.patch'
        self.patch_file.write_bytes(
            b'--- a/tools/server/server-common.h\n+++ b/tools/server/server-common.h\n'
            b'@@ -1 +1 @@\n-a\n+b\n'
            b'--- a/tools/server/server-context.cpp\n+++ b/tools/server/server-context.cpp\n'
            b'@@ -1 +1 @@\n-c\n+d\n')
        patch_sha = hashlib.sha256(self.patch_file.read_bytes()).hexdigest()
        m['patch_sha256'] = patch_sha
        snap = REPO / 'results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json'
        self.source_tree = json.loads(snap.read_text('utf-8'))['source_tree']
        self.head = 'a' * 40
        m['source_binding'] = {
            'source_tree': self.source_tree, 'head': self.head,
            'patch_path': str(self.patch_file), 'patch_sha256': patch_sha,
            'build_snapshot': {'path': 'results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json',
                               'sha256': hashlib.sha256(snap.read_bytes()).hexdigest()}}
        m['acquisition_code'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for name, path in self.rs.ACQUISITION_CODE.items()}
        # the fake git answers what a clean, patched tree would
        self.git_answers = {
            'rev-parse': (0, self.head + '\n', ''),
            'status': (0, ' M tools/server/server-common.h\n'
                          ' M tools/server/server-context.cpp\n', ''),
            'apply': (0, '', ''),
        }
        self.git_calls = []
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
             popen_raises=None, no_pointer=False, post_hook=None,
             barrier_hook=None, stray_command=None,
             drain_start_raises=False, drain_construct_raises=False,
             request_start_raises_at=None, request_join_raises=False,
             unfinished_request=None, unfinished_mode='not_yet_sent'):
        rs = self.rs
        proc = proc if proc is not None else _Proc()
        if hasattr(proc, 'close'):
            self.addCleanup(proc.close)
        bodies = bodies if bodies is not None else [OK_BODY, OK_BODY]
        posted = []

        def fake_post(url, json=None, timeout=None, **kw):
            posted.append({'url': url, 'timeout': timeout})
            # IN FLIGHT: the unfinished request's POST never returns while the
            # supervisor watches. A BaseException, so the worker's `except
            # Exception` cannot turn it into a finished record.
            if unfinished_mode == 'in_flight' and unfinished_request is not None \
                    and len(posted) == unfinished_request + 1:
                raise _Suspend()
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
                if barrier_hook is not None:
                    barrier_hook(timeout=timeout)
                if break_barrier:
                    raise RuntimeError('broken barrier')

        request_starts = [0]

        class _Thread:
            def __init__(self, target, args=(), kwargs=None, daemon=None, name=None):
                if drain_construct_raises and name == 'live_ab_smoke_drain':
                    raise RuntimeError('injected drain construction failure')
                self.target, self.args, self.kwargs = target, args, kwargs or {}
                self.name = name

            def start(self):
                if drain_start_raises and self.name == 'live_ab_smoke_drain':
                    raise RuntimeError('injected drain start failure')
                if self.name != 'live_ab_smoke_drain':
                    # SUPERVISOR-side failure: raised by Thread.start itself,
                    # AFTER earlier workers have already run and POSTed.
                    if request_start_raises_at is not None and \
                            request_starts[0] == request_start_raises_at:
                        raise RuntimeError('injected supervisor Thread.start '
                                           'failure')
                    request_starts[0] += 1
                    # AN UNFINISHED WORKER. 'not_yet_sent': the thread exists and
                    # is alive but has not run; it runs LATE, during reap, after
                    # the terminal snapshot. 'in_flight': it runs until its POST,
                    # which never returns.
                    if unfinished_request is not None and self.args \
                            and self.args[0] == unfinished_request:
                        self._alive = True
                        if unfinished_mode == 'not_yet_sent':
                            late.append(self)
                            return
                        try:
                            self.target(*self.args, **self.kwargs)
                        except _Suspend:
                            return
                        self._alive = False
                        return
                self.target(*self.args, **self.kwargs)

            def run_late(self):
                self.target(*self.args, **self.kwargs)
                self._alive = False

            def join(self, timeout=None):
                if request_join_raises and self.name != 'live_ab_smoke_drain':
                    raise RuntimeError('injected supervisor Thread.join failure')

            def is_alive(self):
                return getattr(self, '_alive', False)

        # A late worker runs when the child is reaped -- which is AFTER the
        # terminal snapshot -- so anything it does must not reach the receipt.
        late = []
        real_wait = proc.wait

        def wait_then_finish_late(timeout=None):
            while late:
                late.pop(0).run_late()
            return real_wait(timeout=timeout)
        proc.wait = wait_then_finish_late

        self.denied = []

        def fake_git(argv):
            self.git_calls.append(list(argv))
            verb = [a for a in argv if not a.startswith('-') and a != self.source_tree][0]
            return self.git_answers.get(verb, (1, '', 'unexpected git verb %s' % verb))

        self.popen_kwargs = None

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
            self.popen_kwargs = dict(k)
            return proc

        if stray_command is not None:
            # a deliberate stray process attempt, so the ledger has something to
            # record; without this control an empty ledger proves nothing
            try:
                fake_popen(stray_command)
            except AssertionError:
                pass

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
                mock.patch.object(rs, 'DEPENDENCY_READERS', self.dep_readers), \
                mock.patch.object(rs, 'SOURCE_READERS', {'git': fake_git}), \
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

    def tearDown(self):
        # THE LEDGER IS ENFORCED AFTER EVERY CASE. Root, 14:03: "Enforce the
        # denied-operation ledger after EVERY harness case, including
        # production-caught exceptions; the deliberate violation control must
        # assert harness failure, not just that its list is nonempty." Checking
        # it in one healthy test left every other case free to swallow a denied
        # command inside a production `except`.
        if getattr(self, '_expect_denied', False):
            return
        self.assertEqual(getattr(self, 'denied', []), [],
                         'a process attempt was denied and then swallowed: %r'
                         % (getattr(self, 'denied', []),))

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
        # the launcher and model are untouched; one sibling library is not.
        # The v3 closure, re-derived before Popen, is what catches it now.
        (self.bindir / 'libllama-server-impl.dylib').write_bytes(b'TAMPERED IMPL')
        status, receipt = self._run()
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt['dependency_verification']['verified'])
        self.assertTrue(any('changed bytes' in p and 'libllama-server-impl' in p
                            for p in receipt['dependency_verification']['problems']))
        self.assertFalse(receipt['child_started'],
                         'nothing may launch once an input fails its pin')
        self.assertEqual(self.posted, [])
        self.assertEqual(status, 1)

    def test_a_manifest_with_NO_declared_closure_refuses(self):
        """A missing required input refuses before Popen; the launcher alone is
        not acceptance of the candidate instrument."""
        m = json.loads(self.man_path.read_text('utf-8'))
        del m['dependency_closure']
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        self.assertFalse(receipt['manifest_validation']['usable'])
        self.assertTrue(any('dependency_closure' in p
                            for p in receipt['manifest_validation']['problems']))
        self.assertFalse(receipt['child_started'])
        self.assertEqual(status, 1)

    def test_an_incomplete_manifest_reaches_a_TERMINAL_RECEIPT(self):
        """Root, 2026-09-23 11:16: "A syntactically valid but incomplete
        manifest `{}` raises `KeyError('model')` with no terminal receipt."

        The script dereferenced manifest keys at four separate places, so an
        incomplete manifest failed at whichever one it reached first, throwing
        before any receipt existed.
        """
        self.man_path.write_text('{}', encoding='utf-8')
        status, receipt = self._run()
        self.assertIsNotNone(receipt, 'an incomplete manifest must still persist a receipt')
        self.assertFalse(receipt['manifest_validation']['usable'])
        self.assertTrue(any('model' in p
                            for p in receipt['manifest_validation']['problems']))
        self.assertFalse(receipt['child_started'])
        self.assertEqual(self.posted, [])
        self.assertEqual(status, 1)

    def test_manifest_domain_errors_are_named_not_thrown(self):
        m = json.loads(self.man_path.read_text('utf-8'))
        m['port'] = 99999                     # out of range
        m['request']['max_tokens'] = True     # a bool, not an int
        m['server_args'] = ['--ok', 7]        # a non-string
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        probs = ' '.join(receipt['manifest_validation']['problems'])
        self.assertIn('port', probs)
        self.assertIn('max_tokens', probs)
        self.assertIn('server_args', probs)
        self.assertEqual(status, 1)

    def test_an_UNDECODABLE_lifecycle_log_reaches_a_terminal_receipt(self):
        """Root: "The actual invalid-UTF8 lifecycle path still raises before the
        safe byte-retention helper and writes no receipt."

        I made this repair in the SIDECAR reader and left the MAIN log reader
        raising: `read_text('utf-8')` raises UnicodeDecodeError, a ValueError,
        which escaped every caller and took the receipt with it.
        """
        self.log.write_bytes(b'\xff\xfe not valid utf-8\n')
        status, receipt = self._run()
        self.assertIsNotNone(receipt, 'an undecodable log must still persist a receipt')
        self.assertIsNotNone(receipt['observation'])
        self.assertIn('not valid UTF-8', receipt['observation']['reason'])
        # the bytes are RETAINED by digest, not decoded with replacements
        self.assertTrue(receipt['raw_log']['present'])
        self.assertFalse(receipt['raw_log']['decodes_as_utf8'])
        self.assertEqual(receipt['raw_log']['bytes'], self.log.stat().st_size)
        self.assertEqual(status, 1)

    def test_no_POST_is_sent_if_the_cutoff_passes_during_the_barrier(self):
        """Root: "recheck the deadline immediately before every POST."

        The earlier check ran BEFORE the barrier wait, which can itself consume
        the remaining allowance -- so a request could pass the check and then sit
        at the barrier until the cutoff had gone by.
        """
        def burn_the_clock(timeout=None):
            self.clock[0] += 600.0            # the whole budget, at the barrier

        status, receipt = self._run(barrier_hook=burn_the_clock)
        self.assertEqual(self.posted, [], 'no POST may follow an expired cutoff')
        for row in receipt['requests']:
            self.assertIn('not_dispatched', row)
        self.assertEqual(status, 1)

    def test_the_drain_does_not_block_on_a_quiet_pipe(self):
        """Root kept this in the deadline task: "a clock check cannot interrupt
        a blocking drain read."

        The loop tested the clock and then entered `read()`, which blocks until
        data or EOF. A child that goes quiet WITHOUT EXITING parked the drain
        there forever and the deadline arithmetic above it was decoration.

        A real pipe, deliberately never written to and never closed.
        """
        import os as _os
        rfd, wfd = _os.pipe()
        reader = _os.fdopen(rfd, 'rb', buffering=0)   # takes ownership of rfd
        self.addCleanup(_os.close, wfd)
        self.addCleanup(reader.close)
        state = {}
        started = self.rs.time.monotonic
        t0 = started()
        self.rs.drain_to_artifact(reader, self.root / 'quiet.bin', state,
                                  deadline=t0 + 0.4)
        self.assertTrue(state['deadline_exhausted'],
                        'the drain must give up at its deadline, not block')
        self.assertFalse(state['raw_capture_complete'])
        self.assertTrue(state.get('nonblocking_reads'))

    def test_an_intent_COLLISION_creates_no_child_at_all(self):
        """Root, 2026-09-23 13:20: "a persistence failure or collision must
        create no child ... Current intent-write failure/collision produces zero
        stop/reap/drain-join calls and leaves the mocked child alive."

        That leak was mine: the intent was written AFTER Popen, so the refusal
        was described while the server it had started kept running. Preparation
        now happens before any child exists.
        """
        # a differing intent file already there: write_json_atomic refuses
        (self.log.parent / ('%s.intent.json' % self.token)).write_text(
            '{"schema":"earlier attempt"}', encoding='utf-8')
        proc = _Proc()
        status, receipt = self._run(proc=proc)
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt['child_started'],
                         'no child may be created once preparation has failed')
        self.assertIsNone(proc.returncode,
                          'the mock child was never started, so never reaped')
        self.assertEqual(self.posted, [])
        self.assertEqual(status, 1)

    def test_missing_consumed_fields_reach_a_terminal_receipt(self):
        """Root's four late witnesses: missing temperature left the started child
        unreaped with no intent or terminal receipt; missing host_id, boot_id or
        patch digest each permitted two POSTs and a reap, then raised without a
        terminal receipt.

        I had validated the keys I happened to LIST, not the fields the
        supervisor DEREFERENCES.
        """
        for field, mutate in (
                ('temperature', lambda d: d['request'].pop('temperature')),
                ('host_id', lambda d: d.pop('host_id')),
                ('boot_id', lambda d: d.pop('boot_id')),
                ('patch_sha256', lambda d: d.pop('patch_sha256'))):
            with self.subTest(missing=field):
                self.setUp()
                m = json.loads(self.man_path.read_text('utf-8'))
                mutate(m)
                self.man_path.write_text(json.dumps(m), encoding='utf-8')
                proc = _Proc()
                status, receipt = self._run(proc=proc)
                self.assertIsNotNone(receipt,
                                     'a missing consumed field must still '
                                     'persist a terminal receipt')
                self.assertFalse(receipt['manifest_validation']['usable'])
                self.assertTrue(any(field in p for p in
                                    receipt['manifest_validation']['problems']))
                self.assertFalse(receipt['child_started'])
                self.assertIsNone(proc.returncode, 'no child was started')
                self.assertEqual(self.posted, [])
                self.assertEqual(status, 1)

    def test_SAME_LENGTH_response_corruption_is_detected(self):
        """Root, 13:20: "the bounded same-length corruption fixture currently
        returns `complete=true` and success ... compare the read-back
        bytes/digest with the received bytes, not just length."

        A length check passes any corruption that preserves size, which is most
        of them. Injected validation evidence, not a claim about real storage.
        """
        rs = self.rs
        real_read_bytes_fn = Path.read_bytes

        def corrupting(pself, *a, **k):
            blob = real_read_bytes_fn(pself, *a, **k)
            if str(pself).endswith('.response') and blob:
                return b'X' + blob[1:]          # same length, different bytes
            return blob

        with mock.patch.object(Path, 'read_bytes', corrupting):
            status, receipt = self._run()
        self.assertIsNotNone(receipt)
        for row in receipt['requests']:
            rr = row['raw_response']
            self.assertFalse(rr['complete'],
                             'same-length corruption must not read as complete')
            self.assertIn('retention_mismatch', rr)
            self.assertNotEqual(rr['sha256'], rr['received_sha256'])
        self.assertEqual(status, 1)

    def test_a_parse_failure_after_200_keeps_response_received(self):
        """Root: "A parsing/shape failure after HTTP 200 must retain
        `response_received=true`; it cannot retroactively make transport
        delivery unknown." The response arrived; only its shape is wrong."""
        class _Garbage:
            status_code = 200
            content = b'not json at all'

            def json(self):
                raise ValueError('no JSON object could be decoded')

        status, receipt = self._run(post_hook=lambda *a, **k: _Garbage())
        for row in receipt['requests']:
            self.assertTrue(row['response_received'])
            self.assertEqual(row['delivery'], 'response_received')
            self.assertIn('body_unparsable', row)
            self.assertFalse(row['usage_known'])
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertEqual(status, 1)

    def test_no_process_attempt_was_swallowed_by_production_handlers(self):
        """Root, 13:20: "Denied commands can be caught by production exception
        handling without failing the test. Check the recorded violation ledger
        at test completion."

        The deny guard raises, but `run_smoke` catches broadly in several
        places, so a denied attempt could be absorbed and the suite still pass.
        The ledger is asserted here rather than relying on the raise.
        """
        status, receipt = self._run()
        self.assertEqual(self.denied, [],
                         'a process attempt was made and swallowed: %r'
                         % (self.denied,))
        self.assertEqual(status, 0)

    def test_the_deny_ledger_DOES_record_a_violation(self):
        """The negative control for the ledger itself: an empty ledger is
        otherwise equally consistent with a ledger that records nothing."""
        self._expect_denied = True
        status, receipt = self._run(stray_command=['/bin/echo', 'stray'])
        # the control asserts the HARNESS would have failed: tearDown's check,
        # run here explicitly, must raise on this ledger.
        with self.assertRaises(AssertionError):
            self.assertEqual(self.denied, [])
        self.assertTrue(self.denied,
                        'a deliberate stray command must appear in the ledger')
        self.assertIn('/bin/echo', self.denied[0][0])

    def test_a_drain_start_failure_still_reaps_and_leaves_a_receipt(self):
        """Root, 2026-09-23 14:03: "Drain startup remains before the protected
        block: injected `drain.start()` failure leaves the mock child unreaped
        and no receipt."

        The drain was built and started one line ABOVE the `try`, so a failure
        there escaped with the server already running.
        """
        proc = _Proc()
        status, receipt = self._run(proc=proc, drain_start_raises=True)
        self.assertIsNotNone(receipt, 'a drain-start failure must still persist a receipt')
        self.assertEqual(proc.returncode, 0, 'the child must still be reaped')
        self.assertIn('dispatch_failure', receipt)
        self.assertTrue(any('dispatch failed' in p
                            for p in receipt['supervisor_problems']),
                        'the failure must be in the VERDICT, not only a field')
        self.assertIn('traceback', receipt['dispatch_failure'])
        self.assertEqual(status, 1)

    def test_partial_dispatch_still_reports_request_state(self):
        """Root: "Partial-dispatch/start/join errors lose request summaries
        despite observed POSTs ... one/two observed POSTs are reported with no
        request/attempt summary, default submitted=0 and even 'usage not
        measurable for 0 requests'. Keep unknown usage unknown over the expected
        denominator."
        """
        boom = RuntimeError('the second worker exploded')
        status, receipt = self._run(bodies=[OK_BODY, boom])
        self.assertEqual(len(self.posted), 2)
        self.assertEqual(receipt['transport_attempted_requests'], 2)
        self.assertEqual(receipt['requests_expected'], 2,
                         'the denominator stays what was PLANNED')
        self.assertEqual(len(receipt['requests']), 2,
                         'both planned requests must appear in the summary')
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertEqual(status, 1)

    def test_explicit_null_temperature_refuses_before_any_POST(self):
        """Root: "Explicit `temperature: null` passes validation and returns
        success after two mock POSTs carrying null." `if temp is not None`
        treated a present-but-null field as absent-and-fine."""
        m = json.loads(self.man_path.read_text('utf-8'))
        m['request']['temperature'] = None
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        proc = _Proc()
        status, receipt = self._run(proc=proc)
        self.assertFalse(receipt['manifest_validation']['usable'])
        self.assertTrue(any('null' in p for p in
                            receipt['manifest_validation']['problems']))
        self.assertEqual(self.posted, [])
        self.assertIsNone(proc.returncode, 'no child was started')
        self.assertEqual(status, 1)

    def test_an_unrepresentable_temperature_refuses_without_raising(self):
        """Root: "temperature=10**400 raises OverflowError during validation,
        before launch but without a terminal receipt." `float()` on a huge int
        RAISES rather than returning inf, so the validator threw on exactly the
        input it exists to describe."""
        m = json.loads(self.man_path.read_text('utf-8'))
        m['request']['temperature'] = 10 ** 400
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        self.assertIsNotNone(receipt, 'validation must not raise past the receipt')
        self.assertTrue(any('too large' in p for p in
                            receipt['manifest_validation']['problems']))
        self.assertEqual(status, 1)

    def test_a_decoded_NON_OBJECT_body_keeps_delivery_received(self):
        """Root: "HTTP200 with decoded `[]` still becomes
        response_received=false/unknown delivery when `.get` raises." The body
        parsed; it is simply not an object, and the AttributeError was landing
        in the handler that means "the transport raised"."""
        class _ListBody:
            status_code = 200
            content = b'[]'

            def json(self):
                return []

        status, receipt = self._run(post_hook=lambda *a, **k: _ListBody())
        for row in receipt['requests']:
            self.assertTrue(row['response_received'])
            self.assertEqual(row['delivery'], 'response_received')
            self.assertIn('body_wrong_shape', row)
            self.assertFalse(row['usage_known'])
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertEqual(status, 1)

    def test_a_drain_that_was_NEVER_CREATED_is_not_a_finished_capture(self):
        """Root, 2026-09-23 14:41: "If constructing the drain raises, protection
        now catches the original error and reaps the child. But `drain_finished
        = not drain_thread.is_alive()` still dereferences None ... causing a
        secondary AttributeError and no receipt ... Do not describe a
        nonexistent drain as a completed capture."

        Two defects: the crash, and a later line that read `drain_thread is None`
        as FINISHED. "Not running" had been standing in for "ran to completion".
        """
        proc = _Proc()
        status, receipt = self._run(proc=proc, drain_construct_raises=True)
        self.assertIsNotNone(receipt, 'a drain-construction failure must still '
                                      'persist one refusal receipt')
        self.assertEqual(proc.returncode, 0, 'the child must still be reaped')
        pd = receipt['producer_diagnostics']
        self.assertEqual(pd['drain_state'], 'not_created')
        self.assertFalse(pd['drain_thread_finished'],
                         'a drain that never existed did not finish')
        self.assertFalse(pd['capture_exists'])
        self.assertIn('NO capture exists', pd['preview_unavailable'])
        self.assertIn('construction', receipt['dispatch_failure']['message'])
        self.assertTrue(any('no diagnostic capture exists' in p
                            for p in receipt['supervisor_problems']))
        self.assertEqual(status, 1)

    def test_a_drain_that_was_created_but_NEVER_STARTED(self):
        """A constructed drain whose start() raised is not alive either, so the
        old reading called it finished."""
        status, receipt = self._run(drain_start_raises=True)
        pd = receipt['producer_diagnostics']
        self.assertEqual(pd['drain_state'], 'not_started')
        self.assertFalse(pd['drain_thread_finished'])
        self.assertFalse(pd['capture_exists'])
        self.assertEqual(status, 1)

    def test_a_SUPERVISOR_Thread_start_failure_still_reconciles_requests(self):
        """Root: "The new owner test makes the second requests.post raise inside
        the request handler; it does not exercise failure of Thread.start or
        Thread.join in the supervisor. Use the original stage failures as
        controls."

        That is exactly right: my last test exercised the handler, a case I had
        already fixed. Here Thread.start itself raises for the SECOND worker,
        after the first has POSTed. The summary used to sit inside the `try`,
        so this jumped past it and the receipt said nothing was sent.
        """
        status, receipt = self._run(request_start_raises_at=1)
        self.assertEqual(len(self.posted), 1, 'the first worker did POST')
        self.assertEqual(receipt['transport_attempted_requests'], 1)
        self.assertEqual(receipt['submitted_requests'], 1)
        self.assertEqual(len(receipt['requests']), 2,
                         'EVERY planned id gets a row, including the unstarted one')
        states = sorted(r.get('state', 'recorded') for r in receipt['requests'])
        self.assertEqual(states, ['no_worker_record', 'recorded'])
        self.assertEqual(receipt['requests_expected'], 2)
        self.assertIsNone(receipt['generated_tokens_total'])
        self.assertFalse(any('never submitted' in p
                             for p in receipt['supervisor_problems']),
                         'an attempted request must not be called never submitted')
        self.assertTrue(any('had no transport attempt' in p
                            for p in receipt['supervisor_problems']))
        self.assertIn('Thread.start', receipt['dispatch_failure']['message'])
        self.assertEqual(status, 1)

    def test_a_SUPERVISOR_Thread_join_failure_still_reconciles_requests(self):
        """Both workers POSTed; the SUPERVISOR's join then raised. The request
        summary must still describe two attempted, two answered requests."""
        status, receipt = self._run(request_join_raises=True)
        self.assertEqual(len(self.posted), 2)
        self.assertEqual(receipt['transport_attempted_requests'], 2)
        self.assertEqual(receipt['submitted_requests'], 2)
        self.assertEqual(len(receipt['requests']), 2)
        self.assertEqual(receipt['requests_with_worker_record'], 2)
        self.assertFalse(any('never submitted' in p or 'no transport attempt' in p
                             for p in receipt['supervisor_problems']))
        self.assertIn('Thread.join', receipt['dispatch_failure']['message'])
        self.assertEqual(status, 1, 'the join failure itself still refuses')

    def test_a_producer_that_refused_itself_invalidates_a_clean_log(self):
        """Exit 93 beside a readable seal full of zeros must still refuse."""
        status, receipt = self._run(proc=_Proc(exit_code=93))
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['server_exit_code'], 93)
        self.assertTrue(receipt['acquisition_invalidated_by_process_outcome'])
        self.assertEqual(status, 1)

    # -- root 14:41 item 4: descriptor, elapsed boundary, bound limits -------
    def test_a_BLOCKING_production_descriptor_refuses_before_any_POST(self):
        """Root: "Refuse a production descriptor that cannot be made
        nonblocking." The drain used to fall back to a blocking read, which is
        the one read the deadline cannot interrupt.

        The descriptor is a number beyond the process limit, so
        `os.set_blocking` fails with EBADF deterministically; a closed-and-
        reused fd number could be silently valid again."""
        class _Unblockable:
            def fileno(self):
                return 1 << 20

            def read(self, n=-1):
                raise AssertionError('a blocking descriptor must not be read')
        proc = _Proc()
        proc.stdout = _Unblockable()
        status, receipt = self._run(proc=proc)
        self.assertEqual(status, 1)
        self.assertEqual(self.posted, [], 'nothing may be dispatched')
        self.assertEqual(receipt['capture_descriptor']['descriptor'], 'blocking')
        self.assertTrue(receipt['child_confirmed_stopped'], 'the child is reaped')
        self.assertEqual(receipt['producer_diagnostics']['drain_state'], 'not_created')
        verdict = ' '.join(receipt['supervisor_problems'])
        self.assertIn('could not be made non-blocking', verdict)

    def test_the_drain_ITSELF_refuses_a_blocking_descriptor(self):
        """The same rule inside the drain, so the function is safe on its own:
        nothing read, no artifact, capture incomplete by construction."""
        class _Unblockable:
            def fileno(self):
                return 1 << 20

            def read(self, n=-1):
                raise AssertionError('must not be read')
        state = {}
        art = self.root / 'blocked.bin'
        self.rs.drain_to_artifact(_Unblockable(), art, state)
        self.assertIn('could not be made non-blocking', state['error'])
        self.assertFalse(state['raw_capture_complete'])
        self.assertFalse(state['nonblocking_reads'])
        self.assertFalse(art.exists())

    def test_the_fixture_child_gives_main_a_REAL_nonblocking_pipe(self):
        """THE CONTROL for the refusals below: a valid run succeeds through a
        real descriptor, made non-blocking and drained to EOF."""
        status, receipt = self._run()
        self.assertEqual(status, 0)
        self.assertEqual(receipt['capture_descriptor']['descriptor'], 'nonblocking')
        self.assertTrue(receipt['producer_diagnostics']['raw_capture_complete'])

    def test_an_IN_MEMORY_stream_is_REFUSED_by_production_main(self):
        """Root, 16:30: descriptor-free leniency belongs to "an explicit offline
        helper fixture", never "a production dispatch path". At `c7bd714` a
        BytesIO reached dispatch labelled 'absent'."""
        proc = _Proc()
        proc.stdout.close()
        proc.stdout = io.BytesIO(b'in memory\n')
        status, receipt = self._run(proc=proc)
        self.assertEqual(status, 1)
        self.assertEqual(self.posted, [])
        self.assertEqual(receipt['capture_descriptor']['descriptor'],
                         'in_memory_fixture')
        self.assertTrue(receipt['child_confirmed_stopped'])

    def test_ROOTS_WITNESS_an_UNAVAILABLE_descriptor_refuses_with_NO_POST_or_read(self):
        """Root's exact injection: a non-memory stream whose `fileno()` raises
        OSError and whose `read()` only counts calls and returns EOF. At
        `c7bd714` it produced two POSTs, one read, return 0, no problems."""
        reads = []

        class _Lost:
            def fileno(self):
                raise OSError('synthetic descriptor lookup failure, not an '
                              'in-memory fixture')

            def read(self, n=-1):
                reads.append(n)
                return b''
        proc = _Proc()
        proc.stdout.close()
        proc.stdout = _Lost()
        status, receipt = self._run(proc=proc)
        self.assertEqual(status, 1)
        self.assertEqual(self.posted, [], 'no POST may be sent')
        self.assertEqual(reads, [], 'nothing may be read')
        self.assertEqual(receipt['capture_descriptor']['descriptor'], 'unavailable')
        self.assertIn('not a verified non-blocking pipe',
                      ' '.join(receipt['supervisor_problems']))
        self.assertTrue(receipt['child_confirmed_stopped'])

    def test_a_stream_with_NO_fileno_at_all_is_REFUSED_by_production_main(self):
        """The drain helper's offline-fixture path covers an object with no
        descriptor interface; production main() still refuses it."""
        class _NoFd:
            def read(self, n=-1):
                raise AssertionError('must not be read')
        proc = _Proc()
        proc.stdout = _NoFd()
        status, receipt = self._run(proc=proc)
        self.assertEqual(status, 1)
        self.assertEqual(self.posted, [])
        self.assertEqual(receipt['capture_descriptor']['descriptor'],
                         'in_memory_fixture')

    def test_a_fileno_that_returns_a_NON_DESCRIPTOR_is_unavailable(self):
        for bogus in (None, -1, True, '3'):
            with self.subTest(bogus=bogus):
                class _Odd:
                    def fileno(self, _b=bogus):
                        return _b
                self.assertEqual(self.rs.make_nonblocking(_Odd())['descriptor'],
                                 'unavailable')

    def test_the_DRAIN_HELPER_alone_keeps_the_in_memory_fixture_path(self):
        """The narrow leniency, where root allowed it: the drain called
        directly with an io.BytesIO (as the pinned design tests do) still
        captures -- and the same helper refuses an unavailable descriptor."""
        state = {}
        art = self.root / 'mem.bin'
        self.rs.drain_to_artifact(io.BytesIO(b'abc'), art, state)
        self.assertEqual(state['descriptor']['descriptor'], 'in_memory_fixture')
        self.assertTrue(state['raw_capture_complete'])

        class _Lost:
            def fileno(self):
                raise OSError('lost')

            def read(self, n=-1):
                raise AssertionError('must not be read')
        state2 = {}
        self.rs.drain_to_artifact(_Lost(), self.root / 'lost.bin', state2)
        self.assertIn('unavailable', state2['error'])
        self.assertFalse(state2['raw_capture_complete'])

    def test_ROOTS_WITNESS_crossing_the_budget_AT_FINALIZATION_refuses(self):
        """Root's exact injection: wrap the real finalize with only
        `clock += 601` before its call. At `c7bd714` a valid run returned 0
        with wall_cap_respected=false and supervisor_problems=[]."""
        rs = self.rs
        real = rs.finalize

        def late(*a, **k):
            self.clock[0] += 601.0
            return real(*a, **k)
        with mock.patch.object(rs, 'finalize', late):
            status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertFalse(receipt['wall_cap_respected'])
        self.assertTrue(any('wall budget was exceeded' in p
                            for p in receipt['supervisor_problems']))
        self.assertTrue(receipt['deadline']['single_reading'])
        self.assertEqual(receipt['deadline']['elapsed_s'],
                         receipt['wall_seconds_total'])

    def test_the_final_snapshot_UNDER_budget_does_not_refuse(self):
        """The control: 599 s at finalization is within budget."""
        rs = self.rs
        real = rs.finalize

        def late(*a, **k):
            self.clock[0] += 599.0
            return real(*a, **k)
        with mock.patch.object(rs, 'finalize', late):
            status, receipt = self._run()
        self.assertEqual(status, 0, receipt['supervisor_problems'])
        self.assertTrue(receipt['wall_cap_respected'])

    def test_the_2048_TOKENS_are_a_PROSPECTIVE_budget_before_any_child(self):
        """Root, 16:30: require the sum of per-request allocations over all
        planned wire attempts to be at most 2,048 before dispatch -- for two
        identical requests, at most 1,024 each."""
        for max_tokens, ok in ((1025, False), (4096, False), (1024, True)):
            with self.subTest(max_tokens=max_tokens):
                self.setUp()
                m = json.loads(self.man_path.read_text('utf-8'))
                m['request']['max_tokens'] = max_tokens
                self.man_path.write_text(json.dumps(m), encoding='utf-8')
                status, receipt = self._run()
                probs = ' '.join(receipt['manifest_validation']['problems'])
                if ok:
                    self.assertNotIn('acquisition budget', probs)
                else:
                    self.assertEqual(status, 1)
                    self.assertFalse(receipt['child_started'])
                    self.assertEqual(self.posted, [])
                    self.assertIn('acquisition budget', probs)

    def test_RESPONSES_RECEIVED_is_reported_beside_the_legacy_name(self):
        status, receipt = self._run()
        self.assertEqual(receipt['responses_received'], 2)
        self.assertEqual(receipt['submitted_requests'], 2)
        self.assertEqual(receipt['transport_attempted_requests'], 2)
        self.assertIn('LEGACY', receipt['submitted_requests_meaning'])

    def test_ELAPSED_is_measured_in_finalize_on_an_EARLY_refusal(self):
        """Root: "measure elapsed time through finalization with its boundary
        explicit." An early refusal used to carry no elapsed figure at all."""
        m = json.loads(self.man_path.read_text('utf-8'))
        del m['caps']['dispatch_cutoff_seconds']
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertIn('wall_seconds_total', receipt)
        self.assertIn('finalize()', receipt['elapsed_boundary']['to'])
        self.assertIn('main() entry', receipt['elapsed_boundary']['from'])
        self.assertEqual(receipt['deadline']['budget_s'], 600.0)

    def test_ELAPSED_counts_time_spent_AFTER_the_child_is_reaped(self):
        """Seven seconds pass while the lifecycle log is read, after reap. The
        attempt's elapsed figure must include them; the named reap mark must
        not."""
        rs = self.rs
        real = rs.lab_lifecycle.observe

        def slow_observe(*a, **k):
            self.clock[0] += 7.0
            return real(*a, **k)
        with mock.patch.object(rs.lab_lifecycle, 'observe', slow_observe):
            status, receipt = self._run()
        self.assertGreaterEqual(receipt['wall_seconds_total']
                                - receipt['seconds_to_child_reap'], 7.0)

    def test_a_manifest_LIMIT_that_disagrees_with_the_code_refuses_before_any_child(self):
        """Root: "bind 8 MiB/90-second/600-second/510-second limits across code,
        immutable configuration and finite costed plan." A manifest that
        declared a different limit was copied into the receipt beside a
        supervisor enforcing its own."""
        cases = [('wall_seconds_total', 601), ('cleanup_reserve_seconds', 89),
                 ('dispatch_cutoff_seconds', 509),
                 ('diagnostic_byte_budget', 8 * 1024 * 1024 + 1),
                 ('dispatch_cutoff_seconds', True),
                 ('diagnostic_byte_budget', '8388608'),
                 ('wall_seconds_total', float('nan')),
                 ('wall_seconds_total', 10 ** 400),          # float() RAISES
                 ('cleanup_reserve_seconds', None)]          # None = deleted
        for key, bad in cases:
            with self.subTest(key=key, bad=bad):
                self.setUp()            # a fresh directory: receipts are write-once
                m = json.loads(self.man_path.read_text('utf-8'))
                if bad is None:
                    del m['caps'][key]
                else:
                    m['caps'][key] = bad
                self.man_path.write_text(json.dumps(m), encoding='utf-8')
                status, receipt = self._run()
                self.assertEqual(status, 1)
                self.assertFalse(receipt['child_started'])
                self.assertEqual(self.posted, [])
                self.assertIn(key, ' '.join(receipt['manifest_validation']['problems']))

    def test_the_LITERAL_limits_root_named_are_what_the_code_enforces(self):
        """The control for the binding: the fixture declares 600/90/510/8 MiB
        as literals and a valid run is accepted, so agreement is between two
        independent statements, not the code and a copy of itself."""
        status, receipt = self._run()
        self.assertEqual(status, 0)
        self.assertEqual(receipt['manifest_validation']['problems'], [])
        self.assertEqual(self.rs.DISPATCH_CUTOFF_S, 510.0)

    # -- root 16:30: the unfinished-worker boundary -------------------------
    def test_all_workers_FINISHED_gives_a_consistent_count_table(self):
        """THE CONTROL: nothing unfinished, every count agrees."""
        status, receipt = self._run()
        self.assertEqual(status, 0)
        c = receipt['request_counts']
        self.assertEqual((c['planned'], c['transport_attempted'], c['responses_received'],
                          c['completed'], c['unfinished_at_terminal_snapshot'],
                          c['no_worker_record'], c['usage_known']),
                         (2, 2, 2, 2, 0, 0, 2))
        self.assertEqual(receipt['terminal_snapshot']['unfinished_workers'], [])

    def test_a_worker_ALIVE_after_join_is_UNFINISHED_and_may_NOT_SEND_later(self):
        """Root: "a worker still writing after bounded join remains unresolved.
        Use a stable terminal snapshot/explicit unfinished state." The second
        worker is alive but has not run; it runs during reap, AFTER the
        snapshot. It must not send, and nothing it does may reach the receipt."""
        status, receipt = self._run(unfinished_request=1,
                                    unfinished_mode='not_yet_sent')
        self.assertEqual(status, 1)
        self.assertEqual(len(self.posted), 1, 'the late worker must not send')
        rows = {r['index']: r for r in receipt['requests']}
        self.assertEqual(rows[1]['state'], 'unfinished_at_terminal_snapshot')
        self.assertEqual(receipt['transport_attempted_requests'], 1)
        self.assertEqual(receipt['responses_received'], 1)
        self.assertEqual(receipt['requests_unfinished_at_terminal_snapshot'], 1)
        self.assertTrue(any('had not finished at the terminal snapshot' in p
                            for p in receipt['supervisor_problems']))

    def test_an_IN_FLIGHT_worker_is_unfinished_and_its_ARTIFACT_is_never_read(self):
        """The worker invoked the transport and its POST has not returned: it is
        attempted, not responded, and unfinished -- not 'no worker record', not
        unsent. A half-written response file sits where it would write; the
        supervisor must not read it."""
        rid = '%s_req1' % self.token
        partial = self.root / ('%s.response' % rid)
        partial.write_bytes(b'{"usage": {"completion_tok')        # mid-write
        reads = []
        real_read = Path.read_bytes

        def spy(p, *a, **k):
            if str(p) == str(partial):
                reads.append(str(p))
            return real_read(p, *a, **k)
        with mock.patch.object(Path, 'read_bytes', spy):
            status, receipt = self._run(unfinished_request=1,
                                        unfinished_mode='in_flight')
        self.assertEqual(status, 1)
        rows = {r['index']: r for r in receipt['requests']}
        self.assertEqual(rows[1]['state'], 'unfinished_at_terminal_snapshot')
        self.assertEqual(receipt['transport_attempted_requests'], 2)
        self.assertEqual(receipt['responses_received'], 1)
        self.assertEqual(reads, [], 'an unfinished worker\'s artifact was read')
        self.assertEqual(receipt['request_counts']['usage_missing_or_unknown'], 1)

    # -- root 16:30/17:52: the wired launch ----------------------------------
    def test_the_WIRED_launch_runs_the_CLOSURE_ROOT_in_its_directory(self):
        """THE CONTROL for the wiring: the launcher is the frozen closure's root,
        cwd is its pinned parent, and every preflight check actually ran."""
        status, receipt = self._run()
        self.assertEqual(status, 0, receipt['supervisor_problems'])
        self.assertEqual(self.popen_kwargs['cwd'], str(self.bindir))
        env = self.popen_kwargs['env']
        self.assertFalse([k for k in env if k.startswith(('GGML_', 'DYLD_'))])
        self.assertEqual(env['LIVE_AB_RUN_TOKEN'], self.token)
        self.assertTrue(receipt['dependency_verification']['verified'])
        self.assertEqual(receipt['dependency_verification']['edges_checked'], 2)
        self.assertTrue(receipt['dependency_verification']['bounded'])
        self.assertTrue(receipt['source_binding_verification']['verified'])
        self.assertTrue(receipt['acquisition_code_verification']['verified'])
        self.assertTrue(receipt['acquisition_code_verification']['config_section']['agrees'])
        self.assertEqual({c[2] for c in self.git_calls}, {'rev-parse', 'status', 'apply'})
        self.assertTrue(receipt['launch_context']['verified_then_launched_unchanged'])

    def test_INHERITED_loader_names_are_REMOVED_and_recorded_by_NAME_only(self):
        """Root: "A variable's presence in the operator's environment alone is
        not a refusal condition" -- it is removed, and only its name recorded."""
        secret = '/secret/path/that/must/not/appear'
        with mock.patch.dict(os.environ, {'GGML_BACKEND_PATH': secret,
                                          'DYLD_LIBRARY_PATH': secret + '2'}):
            status, receipt = self._run()
        self.assertEqual(status, 0, receipt['supervisor_problems'])
        self.assertEqual(receipt['launch_context']['removed_environment_names'],
                         ['DYLD_LIBRARY_PATH', 'GGML_BACKEND_PATH'])
        self.assertNotIn('GGML_BACKEND_PATH', self.popen_kwargs['env'])
        self.assertNotIn('DYLD_LIBRARY_PATH', self.popen_kwargs['env'])
        written = (self.results / ('SMOKE_RECEIPT_%s.json' % self.token)).read_text()
        self.assertNotIn(secret, written, 'an environment VALUE reached the receipt')

    def test_a_backend_DROPPED_INTO_the_executable_directory_refuses_before_Popen(self):
        """Root: "Re-enumerate every applicable loader location at preflight;
        cwd choice alone is not proof of an empty search set." """
        (self.bindir / 'libggml-cuda.so').write_bytes(b'NOT FROZEN')
        status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertIsNone(self.popen_kwargs, 'no child may be created')
        self.assertFalse(receipt['dependency_verification']['verified'])
        self.assertTrue(any('not in the frozen closure' in p
                            for p in receipt['dependency_verification']['problems']))

    def test_an_environment_MUTATED_between_verification_and_Popen_refuses(self):
        """Root: "The same finalized environment dictionary and cwd must feed
        both preflight and Popen; no unverified mutation between them." """
        rs = self.rs
        real = rs.dc.verify_closure

        def verify_then_mutate(frozen, **kw):
            result = real(frozen, **kw)
            kw['launch_context']['environment']['LATE_ADDITION'] = '1'
            return result
        with mock.patch.object(rs.dc, 'verify_closure', verify_then_mutate):
            status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertIsNone(self.popen_kwargs)
        self.assertTrue(any('changed between its verification and the launch' in p
                            for p in receipt['supervisor_problems']))

    def test_a_broken_SOURCE_BINDING_refuses_before_any_child(self):
        for label, answers, expect in (
                ('wrong HEAD', {'rev-parse': (0, 'b' * 40 + '\n', '')}, 'HEAD'),
                ('an extra modified file',
                 {'status': (0, ' M tools/server/server-common.h\n'
                                ' M tools/server/server-context.cpp\n'
                                ' M ggml/src/ggml.c\n', '')}, 'not exactly the patch'),
                ('patch does not reverse-apply', {'apply': (1, '', 'does not apply')},
                 'reverse-apply')):
            with self.subTest(label):
                self.setUp()
                self.git_answers.update(answers)
                status, receipt = self._run()
                self.assertEqual(status, 1)
                self.assertIsNone(self.popen_kwargs)
                self.assertTrue(any(expect in p for p in
                                    receipt['source_binding_verification']['problems']),
                                receipt['source_binding_verification']['problems'])

    def test_a_WRONG_CODE_PIN_or_build_snapshot_digest_refuses(self):
        for label, mutate, where in (
                ('run_smoke.py pin', lambda m: m['acquisition_code'].__setitem__(
                    'experiments/live_ab_serving/run_smoke.py', 'f' * 64),
                 'acquisition_code_verification'),
                ('lab_data.py unpinned', lambda m: m['acquisition_code'].pop(
                    'experiments/live_ab/lab_data.py'), 'acquisition_code_verification'),
                ('snapshot digest', lambda m: m['source_binding']['build_snapshot']
                 .__setitem__('sha256', 'e' * 64), 'source_binding_verification')):
            with self.subTest(label):
                self.setUp()
                m = json.loads(self.man_path.read_text('utf-8'))
                mutate(m)
                self.man_path.write_text(json.dumps(m), encoding='utf-8')
                status, receipt = self._run()
                self.assertEqual(status, 1)
                self.assertIsNone(self.popen_kwargs)
                self.assertFalse(receipt[where]['verified'])

    def test_the_CONFIG_SECTION_must_equal_the_enforced_limits(self):
        """Config and code, two independent statements: if the code enforced a
        different wall, the configuration section would no longer agree."""
        pins = {n: hashlib.sha256(p.read_bytes()).hexdigest()
                for n, p in self.rs.ACQUISITION_CODE.items()}
        self.assertTrue(self.rs.verify_acquisition_code(pins)['verified'])
        with mock.patch.object(self.rs, 'BOUND_LIMITS',
                               dict(self.rs.BOUND_LIMITS, wall_seconds_total=601.0)):
            v = self.rs.verify_acquisition_code(pins)
        self.assertFalse(v['verified'])
        self.assertIn('wall_seconds_total', v['config_section']['problem'])

    def test_a_RELATIVE_log_path_refuses(self):
        self.pointer.write_text('%s\n%s\n%s\n' % (self.man_path, 'relative/life.jsonl',
                                                     self.token), encoding='utf-8')
        status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertIsNone(self.popen_kwargs)
        self.assertTrue(any('not absolute' in p for p in receipt['supervisor_problems']))

    def test_outputs_INSIDE_the_executable_directory_refuse(self):
        inner = self.bindir / 'logs' / 'life.jsonl'
        inner.parent.mkdir()
        inner.write_bytes(self.log.read_bytes())
        self.pointer.write_text('%s\n%s\n%s\n' % (self.man_path, inner, self.token),
                                encoding='utf-8')
        status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertIsNone(self.popen_kwargs)
        self.assertTrue(any('inside the executable directory' in p
                            for p in receipt['supervisor_problems']))

    def test_a_launcher_digest_that_is_NOT_the_closure_root_refuses(self):
        m = json.loads(self.man_path.read_text('utf-8'))
        m['launcher']['sha256'] = 'c' * 64
        self.man_path.write_text(json.dumps(m), encoding='utf-8')
        status, receipt = self._run()
        self.assertEqual(status, 1)
        self.assertTrue(any('closure root' in p
                            for p in receipt['manifest_validation']['problems']))


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
