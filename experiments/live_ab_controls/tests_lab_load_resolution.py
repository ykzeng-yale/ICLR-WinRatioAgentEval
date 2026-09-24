"""EB5 controls for loaded background streams (``lab_load``) and sweep acceptance (``lab_prepare``).

Root 2026-09-23 20:40 item 3 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:18``): "A successful
loaded phase must demonstrate all permitted workers resolved before its terminal acceptance; preserve
any unresolved attempt as a failed/incomplete phase."

``lab_mock_server`` has no streaming endpoint, so the controls that need a real socket and real
``requests`` run a TEST-ONLY SSE stub on loopback (``_SseStub``), no model.  DEVIATION, recorded for
root: the repair contract's hard rule allows network only as loopback to ``lab_mock_server``; this stub
is a second loopback server.  It was disclosed in the EB5 commit but not stopped and reported as the
contract asks; it is reported now.  The controls added after the 2026-09-23 review use in-process
sessions instead (``_FakeSession``, a ``socket.socketpair``): no server, no port.

Every guard has a negative control that must be refused or must detect the defect, and the resolution
reasons are checked as EXACT SETS per state (``ResolutionReasonTests``), so removing any one reason's
guard changes the set even where another reason would still leave the source unresolved.
"""
from __future__ import annotations

import http.server
import json
import shutil
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import requests                                                # noqa: E402

import lab_common                                              # noqa: E402
import lab_data                                                # noqa: E402
import lab_load                                                # noqa: E402
import lab_prepare                                             # noqa: E402

USAGE = {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}


class _SseStub:
    """A loopback OpenAI-style SSE endpoint with three behaviours, for tests only.

    ``clean``: role chunk, three content chunks 20 ms apart, a finish chunk carrying ``USAGE``,
    ``[DONE]``.  ``hold_headers``: sends NOTHING until ``release`` (the POST blocks in the client).
    ``hold_stream``: role chunk, then nothing until ``release``.  Every POST is recorded with its
    arrival time on this process's monotonic clock, the clock the ledger stamps.
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.release = threading.Event()
        self.posts: list = []
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):                     # silence
                pass

            def _chunk(self, payload: bytes) -> None:
                self.wfile.write(b'%x\r\n%s\r\n' % (len(payload), payload))
                self.wfile.flush()

            def do_POST(self):
                n = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(n)
                stub.posts.append((time.monotonic(), json.loads(body.decode('utf-8'))))
                try:
                    if stub.mode == 'hold_headers':
                        stub.release.wait(30)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Transfer-Encoding', 'chunked')
                    self.end_headers()
                    self._chunk(b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n')
                    if stub.mode == 'hold_stream':
                        stub.release.wait(30)
                    for tok in (b'a', b'b', b'c'):
                        time.sleep(0.02)
                        self._chunk(b'data: {"choices":[{"delta":{"content":"%s"}}]}\n\n' % tok)
                    self._chunk(b'data: {"choices":[{"delta":{},"finish_reason":"length"}],'
                                b'"usage":' + json.dumps(USAGE).encode() + b'}\n\n')
                    self._chunk(b'data: [DONE]\n\n')
                    self.wfile.write(b'0\r\n\r\n')
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

        class Server(http.server.ThreadingHTTPServer):
            def handle_error(self, request, client_address):   # a reset after an abort is
                pass                                           # the point, not a stub error

        self.server = Server(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = 'http://127.0.0.1:%d' % self.server.server_address[1]

    def close(self) -> None:
        self.release.set()
        self.server.shutdown()
        self.server.server_close()


def _wait(pred, timeout: float = 10.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


def _ledger(path: Path) -> list:
    return [json.loads(x) for x in path.read_text('utf-8').splitlines() if x.strip()]


def _observer():
    """A valid server-lifecycle observation covering the stub attempt (as in tests_lab_design)."""
    return {'window_id': 'w1', 'active': True, 'resolution_ms': 50,
            'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
            'clock': 'clock_gettime(CLOCK_MONOTONIC)', 'boot_id': 'boot:aa', 'host_id': 'host:bb',
            'concurrency_required': 2,
            'active_windows': [{'start': 99.0, 'end': 101.0, 'identity': 'slot0/req_a'},
                               {'start': 99.0, 'end': 101.0, 'identity': 'slot1/req_b'}]}


def _stub_sweep(before=None):
    """One verifier attempt through the sink (no sandbox, no task); ``before`` runs first."""
    def sweep(tasks, cfg, *, on_progress=None, on_attempt=None):
        if before is not None:
            before()
        payload = {'success': False, 'sentinel_seen': False, 'timed_out': False,
                   'entry_point_defined': True, 'sandbox_flag': False, 'verify_seconds': 0.2,
                   'run': {'passed': False, 'returncode': 1, 'stdout_tail': 'o', 'stderr': 'e',
                           'timed_out': False}}
        rec = lab_data.attempt_record(
            't/1', 0, payload, verification_started_monotonic=100.0,
            verification_ended_monotonic=100.5, verification_started_posix_ns=100_000_000_000,
            verification_ended_posix_ns=100_500_000_000, boot_id='boot:aa', host_id='host:bb',
            boot_source='sysctl kern.bootsessionuuid', host_source='platform.node')
        on_attempt(rec)
        return [lab_data._exclusion('t/1', 'reference_fails_verify',
                                    lab_data.detail_from_attempts([rec]))]
    return sweep


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='eb5_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def stub(self, mode: str) -> _SseStub:
        s = _SseStub(mode)
        self.addCleanup(s.close)
        return s

    def source(self, stub: _SseStub, *, name: str = 'srcA', join: float = 2.0,
               session_factory=None) -> lab_load.StreamingHttpLoad:
        src = lab_load.StreamingHttpLoad(base_url=stub.base_url, model='m', prompt='p',
                                         source_id=name, ledger_path=self.tmp / (name + '.jsonl'),
                                         stop_join_timeout_s=join,
                                         session_factory=session_factory)
        self.addCleanup(lambda: (stub.release.set(), src._thread and src._thread.join(5)))
        return src

    def sweep(self, src, before=None):
        return lab_prepare.run_reference_sweep(
            [], {}, ledger_path=self.tmp / 'sweep.jsonl', load_observer=_observer,
            enforce_tmpdir=False, sweep_fn=_stub_sweep(before), load_sources=[src])


# ------------------------------------------------------------------------------------------------
class BlockedStreamTests(_Base):
    def test_a_blocked_stream_is_unresolved_and_the_sweep_is_refused(self) -> None:
        stub = self.stub('hold_headers')
        src = self.source(stub, join=0.3)
        src.start(lambda gid, t: None)
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            self.sweep(src, before=lambda: _wait(lambda: len(stub.posts) == 1))
        self.assertIn('not resolved', str(ctx.exception))
        res = src.resolution()
        self.assertFalse(res['resolved'])
        self.assertTrue(res['thread_alive'])
        self.assertEqual(res['unterminated_intents'], ['srcA/gen_000000'])
        self.assertIsNotNone(src._thread, 'a live thread must never be forgotten')
        rows = _ledger(self.tmp / 'srcA.jsonl')
        self.assertEqual([r['kind'] for r in rows], ['load_intent'])
        # the thread ends later; the stop that found it alive is still remembered
        stub.release.set()
        self.assertTrue(_wait(lambda: not src._thread.is_alive()))
        later = src.resolution()
        self.assertFalse(later['resolved'])
        self.assertFalse(later['thread_alive'])
        self.assertTrue(any('never forgotten' in r for r in later['reasons']))
        self.assertEqual(_ledger(self.tmp / 'srcA.jsonl')[-1]['state'], 'abandoned_by_stop')

    def test_stop_aborts_a_live_mid_stream_response(self) -> None:
        stub = self.stub('hold_stream')
        src = self.source(stub, join=2.0)
        src.start(lambda gid, t: None)
        self.assertTrue(_wait(lambda: 'srcA/gen_000000' in src._live))
        t0 = time.monotonic()
        res = src.stop()
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertTrue(res['resolved'], res['reasons'])
        self.assertEqual(res['stop_records'][0]['aborted_live_responses'][0]['abort'],
                         'socket_shutdown')
        term = _ledger(self.tmp / 'srcA.jsonl')[-1]
        self.assertEqual((term['kind'], term['state'], term['usage']),
                         ('load_terminal', 'abandoned_by_stop', None))
        self.assertIn('no usage chunk', term['usage_null_reason'])

    def test_negative_without_the_abort_the_same_stream_stays_unresolved(self) -> None:
        stub = self.stub('hold_stream')
        src = self.source(stub, join=0.3)
        src.start(lambda gid, t: None)
        self.assertTrue(_wait(lambda: 'srcA/gen_000000' in src._live))
        with mock.patch.object(lab_load, '_abort_response', lambda resp: 'disabled_by_test'):
            res = src.stop()
        self.assertFalse(res['resolved'])
        self.assertTrue(res['thread_alive'])


class CleanRunTests(_Base):
    def test_negative_control_a_clean_run_is_accepted(self) -> None:
        stub = self.stub('clean')
        src = self.source(stub)
        src.start(lambda gid, t: None)
        out = self.sweep(src, before=lambda: _wait(
            lambda: sum(1 for r in _ledger(self.tmp / 'srcA.jsonl')
                        if r['kind'] == 'load_terminal') >= 2))
        self.assertTrue(out['receipt']['completed'])
        (res,) = out['receipt']['load_resolution']
        self.assertTrue(res['resolved'], res['reasons'])
        self.assertTrue(res['ledger']['complete'])
        rows = _ledger(self.tmp / 'srcA.jsonl')
        terminals = [r for r in rows if r['kind'] == 'load_terminal']
        self.assertEqual(len(terminals), len([r for r in rows if r['kind'] == 'load_intent']))
        done = [r for r in terminals if r['state'] == 'done']
        self.assertGreaterEqual(len(done), 2)
        self.assertTrue(all(r['usage'] == USAGE for r in done))
        self.assertEqual(len(stub.posts), len(terminals))
        self.assertFalse(src.healthy())


class GateTests(_Base):
    """A stop that lands between the gate and the POST cannot produce an untracked POST."""

    def _held_session(self):
        entered, go = threading.Event(), threading.Event()

        class Held:
            def __init__(self):
                self._s = requests.Session()

            def post(self, *a, **kw):
                entered.set()
                go.wait(10)
                return self._s.post(*a, **kw)
        return Held, entered, go

    @staticmethod
    def untracked_posts(stub: _SseStub, ledger: Path) -> int:
        """POSTs the server saw that cannot be matched, one to one, with a durable intent
        written BEFORE them (same process, same monotonic clock)."""
        intents = sorted(r['t_monotonic'] for r in _ledger(ledger)
                         if r['kind'] == 'load_intent') if ledger.exists() else []
        untracked = 0
        for t_post, _ in sorted(stub.posts, key=lambda x: x[0]):
            match = next((t for t in intents if t < t_post), None)
            if match is None:
                untracked += 1
            else:
                intents.remove(match)
        return untracked

    def test_a_stop_between_the_gate_and_the_post_is_tracked(self) -> None:
        """What is guaranteed is NOT "no POST after the stop" (the EB5 commit message said so, and
        that was false): the one POST already permitted IS made after the stop.  Guaranteed: no POST
        without a prior durable intent, no new permit after the stop, and the late POST is tracked
        and keeps the phase unresolved (root item 3: "This is not a proof that late sends cannot
        happen")."""
        stub = self.stub('clean')
        Held, entered, go = self._held_session()
        src = self.source(stub, join=0.3, session_factory=Held)
        src.start(lambda gid, t: None)
        self.assertTrue(entered.wait(5))
        self.assertEqual(len(stub.posts), 0)                       # gate passed, POST not made
        self.assertEqual([r['kind'] for r in _ledger(self.tmp / 'srcA.jsonl')], ['load_intent'])
        t_stop = time.monotonic()
        res = src.stop()                                           # stop lands here
        self.assertFalse(res['resolved'])
        self.assertEqual(res['unterminated_intents'], ['srcA/gen_000000'])
        go.set()                                                   # the permitted POST goes out
        self.assertTrue(_wait(lambda: not src._thread.is_alive()))
        self.assertEqual(len(stub.posts), 1)
        self.assertGreater(stub.posts[0][0], t_stop, 'the permitted POST is made AFTER the stop')
        self.assertEqual(self.untracked_posts(stub, self.tmp / 'srcA.jsonl'), 0)
        time.sleep(0.3)
        self.assertEqual(len(stub.posts), 1, 'no second POST: the gate grants no permit after the '
                                             'stop')
        rows = _ledger(self.tmp / 'srcA.jsonl')
        self.assertEqual([r['kind'] for r in rows], ['load_intent', 'load_terminal'])
        self.assertEqual(rows[1]['state'], 'abandoned_by_stop')
        self.assertTrue(rows[1]['after_stop'])
        self.assertFalse(src.resolution()['resolved'], 'the late POST keeps the phase unresolved')

    def test_the_gate_refuses_after_stop_without_an_intent(self) -> None:
        stub = self.stub('clean')
        src = self.source(stub)
        src.stop()
        self.assertFalse(src._one_generation(requests.Session(), 'srcA/late', lambda g, t: None))
        self.assertEqual(len(stub.posts), 0)
        self.assertFalse((self.tmp / 'srcA.jsonl').exists())

    def test_negative_a_gate_that_skips_the_intent_is_detected(self) -> None:
        stub = self.stub('clean')
        src = self.source(stub)
        with mock.patch.object(src, '_permit', lambda gid, body_sha256: True):
            src._one_generation(requests.Session(), 'srcA/x', lambda g, t: None)
        self.assertEqual(len(stub.posts), 1)
        self.assertEqual(self.untracked_posts(stub, self.tmp / 'srcA.jsonl'), 1)

    def test_negative_a_gate_that_ignores_the_terminal_flag_posts_after_stop(self) -> None:
        stub = self.stub('clean')
        src = self.source(stub)
        src.stop()
        src._terminal = False                                      # the mutation
        src._one_generation(requests.Session(), 'srcA/late', lambda g, t: None)
        self.assertEqual(len(stub.posts), 1, 'without the flag check a POST follows the stop')


class LedgerAndLifetimeTests(_Base):
    def test_ledger_reader_refuses_every_incomplete_shape(self) -> None:
        def rec(kind, gid, **kw):
            return json.dumps(dict({'schema': lab_load.LOAD_LEDGER_SCHEMA, 'kind': kind,
                                    'gid': gid}, **kw))
        good = rec('load_intent', 'g') + '\n' + rec('load_terminal', 'g', state='done',
                                                    usage=None) + '\n'
        cases = {'complete': (good, True),
                 'torn': (good + '{"schema"', False),
                 'unterminated': (rec('load_intent', 'g') + '\n', False),
                 'orphan': (rec('load_terminal', 'g', state='done') + '\n', False),
                 'duplicate': (good + rec('load_intent', 'g') + '\n', False),
                 'bad_state': (rec('load_intent', 'g') + '\n'
                               + rec('load_terminal', 'g', state='fine') + '\n', False)}
        for name, (text, complete) in cases.items():
            with self.subTest(case=name):
                p = self.tmp / (name + '.jsonl')
                p.write_text(text, 'utf-8')
                self.assertEqual(lab_load.read_load_ledger(p)['complete'], complete)

    def test_usage_is_parsed_or_null_with_a_reason_never_zero(self) -> None:
        self.assertEqual(lab_load.parse_usage(USAGE), (USAGE, None))
        for bad in ({'total_tokens': 5}, {'completion_tokens': -1}, {'completion_tokens': '3'},
                    None):
            with self.subTest(bad=bad):
                usage, reason = lab_load.parse_usage(bad)
                self.assertIsNone(usage)
                self.assertTrue(reason)

    def test_a_source_needs_a_new_ledger_and_has_one_lifetime(self) -> None:
        stub = self.stub('clean')
        nolog = lab_load.StreamingHttpLoad(base_url=stub.base_url, model='m', prompt='p')
        with self.assertRaises(lab_load.LoadRefused):
            nolog.start(lambda g, t: None)
        (self.tmp / 'srcA.jsonl').write_text('', 'utf-8')
        src = self.source(stub)
        with self.assertRaises(lab_load.LoadRefused):
            src.start(lambda g, t: None)                           # ledger exists already
        other = self.source(stub, name='srcB')
        other.start(lambda g, t: None)
        other.stop()
        with self.assertRaises(lab_load.LoadRefused):
            other.start(lambda g, t: None)                         # no second lifetime

    def test_negative_a_loaded_sweep_without_sources_is_refused_before_any_attempt(self) -> None:
        attempted = []
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            lab_prepare.run_reference_sweep(
                [], {}, ledger_path=self.tmp / 'sweep.jsonl', load_observer=_observer,
                enforce_tmpdir=False, sweep_fn=lambda *a, **k: attempted.append(1) or [])
        self.assertIn('load_sources', str(ctx.exception))
        self.assertEqual(attempted, [])
        with self.assertRaises(lab_prepare.PreparationRefused):
            lab_prepare.run_reference_sweep(
                [], {}, ledger_path=self.tmp / 'sweep2.jsonl', load_observer=_observer,
                enforce_tmpdir=False, sweep_fn=lambda *a, **k: attempted.append(1) or [],
                load_sources=[object()])
        self.assertEqual(attempted, [])

    def test_a_source_whose_resolution_raises_is_unresolved(self) -> None:
        class Broken:
            def stop(self):
                return None

            def resolution(self):
                raise RuntimeError('boom')
        (res,) = lab_prepare.stop_and_resolve([Broken()])
        self.assertFalse(res['resolved'])
        with self.assertRaises(lab_prepare.PreparationRefused):
            self.sweep(Broken())


# ------------------------------------------------------------------------------------------------
# In-process sessions: no server, no port (added after the 2026-09-23 review).
class _FakeResp:
    """A complete stream: one content chunk, a usage chunk, ``[DONE]``."""
    status_code = 200

    def iter_lines(self):
        time.sleep(0.005)
        return iter([b'data: {"choices":[{"delta":{"content":"a"}}]}',
                     b'data: {"choices":[],"usage":' + json.dumps(USAGE).encode() + b'}',
                     b'data: [DONE]'])

    def close(self) -> None:
        pass


class _FakeSession:
    """``post`` returns ``_FakeResp``; with ``hold``, the FIRST post blocks until ``go`` is set."""

    def __init__(self, *, hold: bool = False, on_post=None, resp_factory=_FakeResp) -> None:
        self.hold, self.on_post, self.resp_factory = hold, on_post, resp_factory
        self.entered, self.go = threading.Event(), threading.Event()
        self.posts = 0

    def __call__(self):                                   # used as the session_factory
        return self

    def post(self, *a, **kw):
        self.posts += 1
        if self.on_post is not None:
            self.on_post()
        if self.hold and self.posts == 1:
            self.entered.set()
            self.go.wait(10)
        return self.resp_factory()


REASONS = {'stop() has not been called': 'not_stopped', 'still alive': 'alive',
           'have no terminal line': 'unterminated', 'never forgotten': 'unresolved_at_stop',
           'ledger is missing': 'ledger_missing', 'ledger is incomplete': 'ledger_incomplete',
           'in-memory record disagree': 'ledger_disagrees'}


def reason_set(res: dict) -> set:
    out = set()
    for text in res['reasons']:
        keys = [v for k, v in REASONS.items() if k in text]
        assert len(keys) == 1, text
        out.add(keys[0])
    return out


class _InProc(_Base):
    def fake_source(self, session: _FakeSession, *, name: str = 'srcF', join: float = 0.3):
        src = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:9', model='m', prompt='p',
                                         source_id=name, ledger_path=self.tmp / (name + '.jsonl'),
                                         stop_join_timeout_s=join, session_factory=session)
        self.addCleanup(lambda: (session.go.set(), src._thread and src._thread.join(5)))
        return src

    def ran_clean(self, name: str = 'srcF'):
        session = _FakeSession()
        src = self.fake_source(session, name=name)
        src.start(lambda gid, t: None)
        self.assertTrue(_wait(lambda: src.generations >= 1))
        return src


class ResolutionReasonTests(_InProc):
    """Every reason of ``StreamingHttpLoad.resolution`` on its own condition, as an EXACT set."""

    def test_never_started_is_only_not_stopped(self) -> None:
        src = self.fake_source(_FakeSession())
        res = src.resolution()
        self.assertEqual((res['resolved'], reason_set(res)), (False, {'not_stopped'}))

    def test_blocked_then_finished_later(self) -> None:
        session = _FakeSession(hold=True)
        src = self.fake_source(session)
        src.start(lambda gid, t: None)
        self.assertTrue(session.entered.wait(5))
        res = src.stop()
        self.assertEqual(reason_set(res),
                         {'alive', 'unterminated', 'unresolved_at_stop', 'ledger_incomplete'})
        session.go.set()
        self.assertTrue(_wait(lambda: not src._thread.is_alive()))
        later = src.resolution()
        self.assertEqual((later['resolved'], reason_set(later)), (False, {'unresolved_at_stop'}))

    def test_clean_stop_then_each_durable_ledger_defect_alone(self) -> None:
        src = self.ran_clean()
        res = src.stop()
        self.assertEqual((res['resolved'], res['reasons']), (True, []))
        path = self.tmp / 'srcF.jsonl'
        good = path.read_bytes()

        def rec(kind, **kw):
            return json.dumps(dict({'schema': lab_load.LOAD_LEDGER_SCHEMA, 'kind': kind,
                                    'gid': 'srcF/injected'}, **kw)).encode() + b'\n'
        cases = {'torn_line': (good + b'{"schema"', {'ledger_incomplete'}),
                 'extra_complete_pair': (good + rec('load_intent')
                                         + rec('load_terminal', state='done'),
                                         {'ledger_disagrees'}),
                 'missing': (None, {'ledger_missing'})}
        for name, (data, want) in cases.items():
            with self.subTest(defect=name):
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
                got = src.resolution()
                self.assertEqual((got['resolved'], reason_set(got)), (False, want))
                path.write_bytes(good)
                self.assertTrue(src.resolution()['resolved'])     # restored: resolved again

    def test_a_thread_alive_after_a_clean_stop_is_only_alive(self) -> None:
        src = self.ran_clean()
        self.assertTrue(src.stop()['resolved'])
        src._thread = types.SimpleNamespace(is_alive=lambda: True,   # e.g. a thread not joined
                                            join=lambda timeout=None: None)
        res = src.resolution()
        self.assertEqual((res['resolved'], reason_set(res)), (False, {'alive'}))


class LateResponseAbortTests(_InProc):
    """A stop that lands while ``post()`` is in progress has no response to abort; the worker must
    abort the response itself when ``post()`` returns (``_one_generation``, ``stop_landed``)."""

    def _run(self, patch_abort: bool) -> tuple:
        a, b = socket.socketpair()
        self.addCleanup(b.close)
        self.addCleanup(a.close)

        class _SockResp:                    # headers received, body never arrives
            status_code = 200
            raw = types.SimpleNamespace(_fp=types.SimpleNamespace(fp=types.SimpleNamespace(
                raw=types.SimpleNamespace(_sock=a))))

            def iter_lines(self):
                while True:
                    try:
                        data = a.recv(4096)
                    except OSError:
                        return
                    if not data:
                        return
                    yield from data.split(b'\n')

            def close(self):
                pass
        session = _FakeSession(hold=True, resp_factory=_SockResp)
        src = self.fake_source(session, join=0.2)
        src.start(lambda gid, t: None)
        self.assertTrue(session.entered.wait(5))
        ctx = mock.patch.object(lab_load, '_abort_response', lambda resp: 'disabled_by_test') \
            if patch_abort else mock.MagicMock()
        with ctx:
            self.assertEqual(src.stop()['stop_records'][0]['aborted_live_responses'], [])
            session.go.set()                                      # post() returns AFTER the stop
            ended = _wait(lambda: not src._thread.is_alive(), timeout=1.5)
        return src, a, b, ended

    def test_the_late_response_is_aborted_by_the_worker(self) -> None:
        src, a, b, ended = self._run(patch_abort=False)
        self.assertTrue(ended, 'the worker must not block on a response that arrived after stop()')
        b.settimeout(2.0)
        self.assertEqual(b.recv(1), b'', 'the socket was shut down')
        last = _ledger(self.tmp / 'srcF.jsonl')[-1]
        self.assertEqual((last['kind'], last['state'], last['after_stop']),
                         ('load_terminal', 'abandoned_by_stop', True))

    def test_negative_without_the_abort_the_worker_blocks(self) -> None:
        src, a, b, ended = self._run(patch_abort=True)
        self.assertFalse(ended)
        self.assertTrue(src._thread.is_alive())
        b.close()                                                 # release it
        self.assertTrue(_wait(lambda: not src._thread.is_alive()))


class DurableIntentTests(_InProc):
    def test_the_intent_is_fsynced_before_the_post(self) -> None:
        syncs, at_post = [], []
        real = lab_common.fullsync
        session = _FakeSession(on_post=lambda: at_post.append(len(syncs)))
        with mock.patch.object(lab_common, 'fullsync', lambda fd: (syncs.append(fd), real(fd))):
            src = self.fake_source(session)
            src.start(lambda gid, t: None)
            self.assertTrue(_wait(lambda: len(at_post) >= 2))
            src.stop()
        self.assertEqual(at_post[0], 1, 'exactly the first intent is durable before the first POST')
        self.assertEqual(at_post[1], 3, 'intent, terminal, intent: all durable before POST 2')

    def test_negative_a_non_durable_append_is_detected(self) -> None:
        syncs, at_post = [], []
        real_append = lab_common.append_line_durable
        session = _FakeSession(on_post=lambda: at_post.append(len(syncs)))
        with mock.patch.object(lab_common, 'fullsync', lambda fd: syncs.append(fd)), \
                mock.patch.object(lab_common, 'append_line_durable',
                                  lambda fd, line, durable: real_append(fd, line, durable=False)):
            src = self.fake_source(session)
            src.start(lambda gid, t: None)
            self.assertTrue(_wait(lambda: len(at_post) >= 1))
            src.stop()
        self.assertEqual(at_post[0], 0)


class SweepAcceptanceTests(_InProc):
    """EB5 acceptance binds to REAL, TRACKED load (review 2026-09-23, finding 2)."""

    def sweep_with(self, sources, observer=_observer, sweep_fn=None, name='sweep.jsonl'):
        return lab_prepare.run_reference_sweep(
            [], {}, ledger_path=self.tmp / name, load_observer=observer, enforce_tmpdir=False,
            sweep_fn=sweep_fn or _stub_sweep(), load_sources=sources)

    def test_a_tracked_resolved_source_is_accepted(self) -> None:
        out = self.sweep_with([self.ran_clean()])
        self.assertTrue(out['receipt']['completed'])
        self.assertGreaterEqual(out['receipt']['load_resolution'][0]['intents'], 1)

    def test_negative_a_fixture_handed_over_while_the_real_load_runs_is_refused(self) -> None:
        """The reviewer's reproduction, without a network: a real source is blocked in post() with
        an unterminated intent while a ScriptedLoad is handed over.  It was accepted."""
        session = _FakeSession(hold=True)
        real = self.fake_source(session, name='real')
        real.start(lambda gid, t: None)
        self.assertTrue(session.entered.wait(5))
        with self.assertRaisesRegex(lab_prepare.PreparationRefused, 'made no tracked load POST'):
            self.sweep_with([lab_load.ScriptedLoad([])])
        self.assertFalse(real.resolution()['resolved'])

    def test_negative_a_source_that_never_sent_is_refused(self) -> None:
        never = self.fake_source(_FakeSession(), name='never')
        self.assertTrue(never.stop()['resolved'])                 # resolved, but no load at all
        with self.assertRaisesRegex(lab_prepare.PreparationRefused, 'made no tracked load POST'):
            self.sweep_with([never])

    def test_negative_an_observer_whose_source_is_not_handed_over_is_refused_first(self) -> None:
        observed = self.ran_clean(name='observed')
        other = self.ran_clean(name='other')
        obs = lab_load.ContinuousLoadObserver(observed)
        attempted = []
        with self.assertRaisesRegex(lab_prepare.PreparationRefused, 'not among load_sources'):
            self.sweep_with([other], observer=obs.observe,
                            sweep_fn=lambda *a, **k: attempted.append(1) or [])
        self.assertEqual(attempted, [])
        self.assertFalse((self.tmp / 'sweep.jsonl').exists())
        # positive control of the binding: with the observed source handed over the sweep starts
        # (and is then refused for coverage: a client-stream observer never certifies)
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            self.sweep_with([observed, other], observer=obs.observe, name='sweep2.jsonl')
        self.assertNotIn('not among load_sources', str(ctx.exception))
        kinds = [r.get('schema') for r in _ledger(self.tmp / 'sweep2.jsonl')]
        self.assertIn(lab_data.ATTEMPT_RECORD_SCHEMA, kinds)

    def test_a_failed_sweep_still_stops_every_source(self) -> None:
        class Spy:
            kind, source_id = 'spy', 'spy'

            def __init__(self):
                self.stops = 0

            def stop(self):
                self.stops += 1

            def resolution(self):
                return {'source_id': 'spy', 'kind': 'spy', 'resolved': self.stops > 0,
                        'intents': 1, 'reasons': []}
        spies = [Spy(), Spy()]

        def failing(tasks, cfg, *, on_progress=None, on_attempt=None):
            raise RuntimeError('the sweep failed')
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            self.sweep_with(spies, sweep_fn=failing)
        self.assertEqual([s.stops for s in spies], [1, 1])
        self.assertIn('"load_resolution"', str(ctx.exception))

    def test_stop_and_resolve_treats_a_raising_stop_and_a_non_dict_as_unresolved(self) -> None:
        class Raises:
            source_id = 'raises'

            def stop(self):
                raise RuntimeError('stop failed')

            def resolution(self):
                return {'resolved': True, 'intents': 1}

        class NotADict:
            source_id = 'nondict'

            def stop(self):
                return None

            def resolution(self):
                return True
        got = lab_prepare.stop_and_resolve([Raises(), NotADict()])
        self.assertEqual([type(r) for r in got], [dict, dict])
        self.assertEqual([r['resolved'] for r in got], [False, False])
        self.assertIn('stop() raised RuntimeError', got[0]['reasons'][0])
        self.assertIn('returned bool', got[1]['reasons'][0])
        for src in (Raises(), NotADict()):
            with self.subTest(source=src.source_id):
                with self.assertRaisesRegex(lab_prepare.PreparationRefused, 'not resolved'):
                    self.sweep_with([src], name=src.source_id + '.jsonl')


if __name__ == '__main__':
    unittest.main()
