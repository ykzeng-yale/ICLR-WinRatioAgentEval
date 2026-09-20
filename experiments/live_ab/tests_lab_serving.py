"""Tests for lab_client, lab_server, lab_mock_server and lab_worker (group G4).

Every test here runs offline and deterministically against ``lab_mock_server``: **no test in
this file starts a language-model server, and none may ever be changed so that it does**
(ARCHITECTURE_FINAL.md 9.2 / protocol Appendix C).

Run with::

    ./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lab_common                                                          # noqa: E402
import lab_client                                                          # noqa: E402
import lab_mock_server                                                     # noqa: E402
import lab_server                                                          # noqa: E402
import lab_worker                                                          # noqa: E402
from lab_client import (GoldenReceipt, LlamaClient, Spool, read_spool)     # noqa: E402

lab_common.add_import_paths()
import agent                                                               # noqa: E402
import sandbox                                                             # noqa: E402
import verify as verify_mod                                                # noqa: E402

# The pilot classes are re-run unchanged (ARCHITECTURE_FINAL.md 9.2, last G4 row): the
# sandbox, the verifier and the agent are reused byte-identically, so their own tests are
# part of this group's evidence.
from tests_local_stream import (AgentTests, SandboxTests,                  # noqa: E402,F401
                                VerifyTests)

TESTDATA = HERE / 'testdata'

#: The pristine, unwrapped ``run_program``.  Installing the execution lock is a monkeypatch
#: by design (protocol 5.7 item 1), so every test that installs it restores this afterwards
#: and the reused pilot test classes never inherit a wrapper bound to a closed spool.
_PRISTINE_RUN_PROGRAM = sandbox.run_program


def _restore_run_program() -> None:
    sandbox.run_program = _PRISTINE_RUN_PROGRAM
    agent.run_program = _PRISTINE_RUN_PROGRAM
    verify_mod.run_program = _PRISTINE_RUN_PROGRAM

#: Digests of the reused pilot files.  ``agent.py`` in particular must stay byte-identical:
#: ``LlamaClient`` exists precisely so that it can (ARCHITECTURE_FINAL.md 3.9).  The freeze
#: bundle carries the authoritative copy of these values; this test pins them from now on.
REUSED_SHA256 = {
    'agent.py': '3cf2056330c72ebd5d2884f48d6ec2daa706fcc685ad67e3c2609d809ff75b64',
    'sandbox.py': 'd461570937ddbe1fb241288721a1a06b44bd41dd72ccdc2e2ffa2f144184c6ff',
    'verify.py': '7473678b1990ca2a5a1900b45251fddcd2882f2b371d76d3a59fe669a607dbb6',
    'common.py': 'cdee8821250c315b183769806d84495f3055cad14e0e70809c33aab8a6458a42',
    'data.py': 'ae630675f43786bcf7483ff90d4c641ab9a6c7c16202de456d96b03f19321405',
}

SAMPLING = {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0,
            "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
            "mirostat": 0, "max_tokens": 1024, "cache_prompt": False, "stream": False,
            "verbose": True}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def load_scenario(name: str) -> dict:
    return json.loads((TESTDATA / ('%s.json' % name)).read_text(encoding='utf-8'))


def golden_for(scenario: dict, sampling: dict = SAMPLING) -> GoldenReceipt:
    """The golden objects the pre-freeze smoke would have captured from this mock."""
    gen = dict(scenario.get('defaults') or {})
    for key in ('temperature', 'top_p', 'top_k', 'min_p', 'typical_p', 'repeat_penalty',
                'presence_penalty', 'frequency_penalty', 'mirostat'):
        gen[key] = sampling[key]
    gen['n_predict'] = sampling['max_tokens']
    return GoldenReceipt(props=dict(scenario.get('props') or {}), generation_settings=gen,
                         mask=('seed',), float_tolerance=1e-6)


@contextlib.contextmanager
def mock_server(scenario: dict):
    """A scripted mock on a free loopback port, served in a thread for the test's duration."""
    srv, port = lab_mock_server.make_server(scenario, port=0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.01},
                              daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d' % port, srv
    finally:
        with contextlib.suppress(Exception):
            srv.shutdown()
        with contextlib.suppress(Exception):
            srv.server_close()
        thread.join(timeout=5)


@contextlib.contextmanager
def no_backoff(record: list | None = None):
    """Record the frozen connection backoff instead of spending it.

    The client's wait is a module-level indirection precisely so that this patch cannot
    reach the mock server's own scripted sleeps, which share the ``time`` module."""
    real = lab_client._sleep
    lab_client._sleep = lambda s: (record.append(s) if record is not None else None)
    try:
        yield record
    finally:
        lab_client._sleep = real


def make_client(base_url: str, scenario: dict, spool: Spool, **kw) -> LlamaClient:
    params = dict(base_url=base_url + '/v1', alias=scenario['alias'], sampling=dict(SAMPLING),
                  spool=spool, golden=golden_for(scenario), request_timeout_s=5.0,
                  max_connection_retries=0, server_recovery_s=1.0, arrival=1, attempt=1,
                  trial='T4', worker_index=0)
    params.update(kw)
    return LlamaClient(**params)


def messages_for(task: dict) -> list[dict]:
    return [{'role': 'system', 'content': agent.SYSTEM_PROMPT},
            {'role': 'user', 'content': agent.build_user_prompt(task)}]


def task_of(scenario: dict, uid: str) -> dict:
    return next(t for t in scenario['tasks'] if t['uid'] == uid)


def spec_for(scenario: dict, gguf: Path, **kw) -> lab_server.ServerSpec:
    params = dict(server_id='coder', port=8091, alias=scenario['alias'], gguf_path=gguf,
                  gguf_bytes=gguf.stat().st_size if gguf.exists() else 0,
                  gguf_sha256=lab_common.sha256_file(gguf) if gguf.exists() else '',
                  llama_bin=Path('/nonexistent/llama-server'),
                  llama_commit='4fea119de30f6a923992780f6fd5ccb0bee5d47d',
                  args=(), log_path=gguf.parent / 'llama.log', n_slots=2, n_ctx=16384)
    params.update(kw)
    return lab_server.ServerSpec(**params)


def _reap(proc: subprocess.Popen) -> None:
    """Leave no worker process and no open pipe behind, whatever the test did to it."""
    if proc.poll() is None:
        with contextlib.suppress(OSError):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
    for stream in (proc.stdout, proc.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def terminal_lines(lines: list[dict], request_id: str) -> list[dict]:
    return [r for r in lines
            if r.get('kind') in ('call_response', 'call_error')
            and (r.get('body') or {}).get('request_id') == request_id]


# --------------------------------------------------------------------------- #
# the spool: one request line, exactly one terminal line
# --------------------------------------------------------------------------- #
class SpoolTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'spools').mkdir()
        self.addCleanup(self.tmp.cleanup)

    def spool(self, arrival: int = 1, attempt: int = 1) -> Spool:
        s = Spool(self.dir / 'spools' / ('ep_%d_%d.jsonl' % (arrival, attempt)))
        s.set_inv('a' * 32)
        self.addCleanup(s.close)
        return s

    def test_envelope_is_self_contained(self):
        s = self.spool(arrival=7, attempt=1)
        s.write('job_accepted', {'arm': 'candidate'}, durable=True)
        row = read_spool(s.path)[0]
        self.assertEqual(sorted(row), ['arrival', 'attempt', 'body', 'inv', 'kind', 'pid',
                                       'spool_seq', 't_mono_ns', 't_wall_ns'])
        self.assertEqual((row['arrival'], row['attempt'], row['inv']), (7, 1, 'a' * 32))
        self.assertEqual(row['pid'], os.getpid())

    def test_offsets_and_gapless_seq(self):
        s = self.spool()
        offsets = [s.write('sandbox_exec', {'i': i}, durable=False) for i in range(5)]
        raw = s.path.read_bytes()
        self.assertEqual(offsets[0], 0)
        for off, row in zip(offsets, read_spool(s.path)):
            self.assertTrue(raw[off:].startswith(b'{'))
            self.assertEqual(raw[off:off + 1], b'{')
        self.assertEqual([r['spool_seq'] for r in read_spool(s.path)], [0, 1, 2, 3, 4])

    def test_fsync_cost_is_carried_on_the_next_line(self):
        s = self.spool()
        s.write('call_started', {'a': 1}, durable=True)
        s.write('call_response', {'b': 2}, durable=True)
        rows = read_spool(s.path)
        self.assertEqual(rows[0]['body']['fsync_ms_prev'], 0.0)
        self.assertGreaterEqual(rows[1]['body']['fsync_ms_prev'], 0.0)

    def test_terminal_line_closes_the_spool_for_reopening(self):
        s = self.spool()
        s.write('episode_final', {'record_sha256': 'x'}, durable=True)
        s.close()
        with self.assertRaises(lab_common.SpoolError):
            Spool(s.path)

    def test_durable_write_calls_fullsync_before_returning(self):
        calls = []
        real = lab_common.fullsync

        def spy(fd):
            calls.append(fd)
            return real(fd)

        lab_common.fullsync = spy
        try:
            s = self.spool()
            s.write('call_started', {'a': 1}, durable=True)
            self.assertEqual(len(calls), 1)
            s.write('sandbox_exec', {'a': 1}, durable=False)
            self.assertEqual(len(calls), 1)
        finally:
            lab_common.fullsync = real


# --------------------------------------------------------------------------- #
# the client
# --------------------------------------------------------------------------- #
class ClientTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'spools').mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.basic = load_scenario('scenario_basic')
        self.faults = load_scenario('scenario_faults')

    def spool(self, arrival: int = 1) -> Spool:
        s = Spool(self.dir / 'spools' / ('ep_%d_1.jsonl' % arrival))
        s.set_inv('b' * 32)
        self.addCleanup(s.close)
        return s

    # -- one terminal line per request ------------------------------------- #
    def test_one_terminal_line_per_request(self):
        """Every ``call_started`` has exactly one ``call_response``/``call_error``."""
        with mock_server(self.faults) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.faults, s, max_connection_retries=2)
            with no_backoff():
                for uid, exc in (('mbpp/32', None),
                                 ('mbpp/20', lab_client.MalformedResponse),
                                 ('mbpp/14', lab_client.HttpError)):
                    task = task_of(self.faults, uid)
                    if exc is None:
                        client.chat(messages_for(task), {'kind': 'code'})
                    else:
                        with self.assertRaises(exc):
                            client.chat(messages_for(task), {'kind': 'code'})
            lines = read_spool(s.path)
        started = [r for r in lines if r['kind'] == 'call_started']
        self.assertGreaterEqual(len(started), 3)
        for row in started:
            rid = row['body']['request_id']
            self.assertEqual(len(terminal_lines(lines, rid)), 1,
                             'request %s has %d terminal lines' % (rid, len(terminal_lines(lines, rid))))
        self.assertEqual(len(started),
                         len([r for r in lines if r['kind'] in ('call_response', 'call_error')]))

    def test_spool_before_post(self):
        """The ``call_started`` line is on disk **and fsynced** before the socket is written."""
        observed = {}
        real_fullsync = lab_common.fullsync
        counter = {'n': 0}

        def spy(fd):
            counter['n'] += 1
            return real_fullsync(fd)

        with mock_server(self.basic) as (base, _srv):
            s = self.spool()

            class WatchingSession:
                def __init__(self, inner):
                    self.inner = inner

                def post(self, *a, **kw):
                    observed['bytes_on_disk'] = s.path.stat().st_size
                    observed['fsyncs'] = counter['n']
                    observed['lines'] = read_spool(s.path)
                    return self.inner.post(*a, **kw)

                def get(self, *a, **kw):
                    return self.inner.get(*a, **kw)

            import requests
            lab_common.fullsync = spy
            try:
                client = make_client(base, self.basic, s,
                                     session=WatchingSession(requests.Session()))
                client.chat(messages_for(task_of(self.basic, 'mbpp/32')), {'kind': 'code'})
            finally:
                lab_common.fullsync = real_fullsync
        self.assertGreater(observed['bytes_on_disk'], 0)
        self.assertGreaterEqual(observed['fsyncs'], 1)
        self.assertEqual(observed['lines'][-1]['kind'], 'call_started')

    # -- no estimation path -------------------------------------------------- #
    def test_no_estimation_path(self):
        """A 200 without ``usage`` is an error; no token estimate is ever produced."""
        src = (HERE / 'lab_client.py').read_text(encoding='utf-8')
        self.assertNotIn('AutoTokenizer', src)
        self.assertNotIn('_estimate_tokens', src)
        with mock_server(self.faults) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.faults, s)
            with self.assertRaises(lab_client.MalformedResponse):
                client.chat(messages_for(task_of(self.faults, 'mbpp/22')), {'kind': 'code'})
            out = client.chat(messages_for(task_of(self.faults, 'mbpp/32')), {'kind': 'code'})
        self.assertIsNone(out['tokens_estimated'])
        lines = read_spool(s.path)
        err = [r for r in lines if r['kind'] == 'call_error'][0]
        self.assertEqual(err['body']['error_class'], 'malformed')
        self.assertFalse(err['body']['usage_known'])

    # -- receipt ------------------------------------------------------------- #
    def _receipt_case(self, uid: str, expect: str):
        with mock_server(self.faults) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.faults, s)
            with self.assertRaises(lab_common.ReceiptMismatch):
                client.chat(messages_for(task_of(self.faults, uid)), {'kind': 'code'})
            lines = read_spool(s.path)
        resp = [r for r in lines if r['kind'] == 'call_response']
        self.assertEqual(len(resp), 1, 'the response is spooled before the mismatch raises')
        self.assertIn(expect, resp[0]['body']['receipt_mismatch'])
        return resp[0]

    def test_receipt_mismatch_changed_temperature(self):
        self._receipt_case('mbpp/26', 'generation_settings_value')

    def test_receipt_mismatch_unknown_key(self):
        self.faults['faults'] = [{'match': {'uid': 'mbpp/32', 'kind': 'code'},
                                  'do': 'receipt', 'set': {'xtc_probability': 0.5}}]
        self._receipt_case('mbpp/32', 'generation_settings_unknown_key')

    def test_receipt_mismatch_missing_key(self):
        self.faults['faults'] = [{'match': {'uid': 'mbpp/32', 'kind': 'code'},
                                  'do': 'receipt', 'unset': ['top_k']}]
        self._receipt_case('mbpp/32', 'generation_settings_missing_key')

    def test_receipt_mismatch_cache_n(self):
        self._receipt_case('mbpp/30', 'cache_n_nonzero')

    def test_receipt_mismatch_tokens_cached(self):
        self.faults['faults'] = [{'match': {'uid': 'mbpp/32', 'kind': 'code'},
                                  'do': 'cache_n', 'set': {'cache_n': 0, 'tokens_cached': 5}}]
        self._receipt_case('mbpp/32', 'tokens_cached_nonzero')

    def test_receipt_mismatch_foreign_alias(self):
        self._receipt_case('mbpp/28', 'model_alias_mismatch')

    def test_receipt_comparator_is_pure_and_total(self):
        golden = golden_for(self.basic)
        gen = dict(golden.generation_settings, seed=7)
        found, _ = lab_client.compare_generation_settings(
            gen, golden.generation_settings, mask=golden.mask,
            float_tolerance=golden.float_tolerance, seed_sent=7)
        self.assertEqual(found, [])
        found, _ = lab_client.compare_generation_settings(
            dict(gen, temperature=0.7 + 1e-9), golden.generation_settings, mask=golden.mask,
            float_tolerance=1e-6, seed_sent=7)
        self.assertEqual(found, [], 'float32 echo is compared within the frozen tolerance')
        found, _ = lab_client.compare_generation_settings(
            dict(gen, seed=8), golden.generation_settings, mask=golden.mask,
            float_tolerance=1e-6, seed_sent=7)
        self.assertEqual(found, ['seed_mismatch'])
        found, _ = lab_client.compare_generation_settings(
            None, golden.generation_settings, mask=golden.mask, float_tolerance=1e-6,
            seed_sent=7)
        self.assertEqual(found, ['generation_settings_absent'])

    def test_receipt_implementations_agree(self):
        """``lab_server``'s second implementation of the frozen rule finds the same things.

        The two paths exist because the isolation matrix forbids ``lab_server`` to import
        ``lab_client``; a silent divergence between them would make the server smoke a
        weaker check than the per-request one."""
        golden = golden_for(self.basic)
        with mock_server(self.basic) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.basic, s)
            client.chat(messages_for(task_of(self.basic, 'mbpp/32')), {'kind': 'code'})
            rid = [r for r in read_spool(s.path) if r['kind'] == 'call_response'][0]
        deposit = json.loads(_gunzip(next((self.dir / 'requests').glob('*.json.gz'))))
        data, seed = deposit['response'], deposit['request']['seed']
        self.assertEqual(rid['body']['receipt_mismatch'], [])
        self.assertEqual(lab_server.smoke_receipt_findings(data, golden, seed_sent=seed), [])
        bad = json.loads(json.dumps(data))
        bad['__verbose']['generation_settings']['temperature'] = 0.8
        client_found, _ = lab_client.compare_generation_settings(
            bad['__verbose']['generation_settings'], golden.generation_settings,
            mask=golden.mask, float_tolerance=golden.float_tolerance, seed_sent=seed)
        server_found = lab_server.smoke_receipt_findings(bad, golden, seed_sent=seed)
        self.assertIn('generation_settings_value', client_found)
        self.assertIn('generation_settings_value', server_found)

    # -- retries -------------------------------------------------------------- #
    def test_retry_policy(self):
        """Timeouts retry twice with the frozen backoff; 4xx/5xx never retry."""
        slept: list[float] = []
        with no_backoff(slept):
            with mock_server(self.faults) as (base, _srv):
                s = self.spool()
                client = make_client(base, self.faults, s, request_timeout_s=0.2,
                                     max_connection_retries=2)
                with self.assertRaises(lab_client.ConnectionFailure):
                    client.chat(messages_for(task_of(self.faults, 'mbpp/12')), {'kind': 'code'})
                lines = read_spool(s.path)
        self.assertEqual(len([r for r in lines if r['kind'] == 'call_started']), 3)
        errs = [r for r in lines if r['kind'] == 'call_error']
        self.assertEqual([e['body']['error_class'] for e in errs], ['timeout'] * 3)
        self.assertEqual([e['body']['will_retry'] for e in errs], [True, True, False])
        self.assertEqual(slept, [lab_client.backoff_seconds(0), lab_client.backoff_seconds(1)])
        self.assertEqual(slept, [2.0, 4.0])

    def test_http_error_is_not_retried(self):
        with mock_server(self.faults) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.faults, s, max_connection_retries=2)
            with self.assertRaises(lab_client.HttpError) as ctx:
                client.chat(messages_for(task_of(self.faults, 'mbpp/14')), {'kind': 'code'})
            lines = read_spool(s.path)
        self.assertEqual(ctx.exception.status, 500)
        self.assertEqual(len([r for r in lines if r['kind'] == 'call_started']), 1)
        self.assertEqual([r['body']['error_class'] for r in lines
                          if r['kind'] == 'call_error'], ['http_5xx'])

    def test_second_server_down_in_one_call_fails_the_call(self):
        """``max_recovery_waits_per_call = 1``: a second ``server_down`` fails the call (row 1)."""
        with mock_server(self.basic) as (base, srv):
            s = self.spool()
            client = make_client(base, self.basic, s, max_connection_retries=2,
                                 server_recovery_s=0.2, request_timeout_s=0.5)
            srv.shutdown()                      # the server is gone for the whole call
            srv.server_close()                  # ... including its listening socket
            t0 = time.perf_counter()
            with self.assertRaises(lab_client.ConnectionFailure):
                client.chat(messages_for(task_of(self.basic, 'mbpp/32')), {'kind': 'code'})
            elapsed = time.perf_counter() - t0
            lines = read_spool(s.path)
        self.assertLess(elapsed, 5.0, 'one recovery wait, not one per try')
        self.assertEqual(client.stats()['recovery_waits'], 1)
        self.assertEqual(len([r for r in lines if r['kind'] == 'call_started']), 2)

    # -- seeds ---------------------------------------------------------------- #
    def test_seed_drawn_and_logged_before_the_post(self):
        with mock_server(self.basic) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.basic, s)
            client.chat(messages_for(task_of(self.basic, 'mbpp/32')), {'kind': 'code'})
            lines = read_spool(s.path)
        started = [r for r in lines if r['kind'] == 'call_started'][0]
        resp = [r for r in lines if r['kind'] == 'call_response'][0]
        self.assertLess(started['spool_seq'], resp['spool_seq'])
        seed = started['body']['seed']
        self.assertIsInstance(seed, int)
        self.assertNotEqual(seed, lab_client.SEED_FORBIDDEN)
        deposit = json.loads(_gunzip(next((self.dir / 'requests').glob('*.json.gz'))))
        self.assertEqual(deposit['request']['seed'], seed)
        self.assertEqual(deposit['response']['__verbose']['generation_settings']['seed'], seed)

    def test_seed_partition(self):
        """The low bit equals ``worker_index``: a cross-worker collision is impossible."""
        for worker_index in (0, 1):
            seeds = [lab_client.draw_seed(worker_index) for _ in range(20000)]
            self.assertTrue(all((s & 1) == worker_index for s in seeds))
            self.assertTrue(all(s != lab_client.SEED_FORBIDDEN for s in seeds))
            self.assertTrue(all(0 <= s <= 0x7FFFFFFF for s in seeds))
            self.assertGreater(len(set(seeds)), 19900, 'draws are from OS entropy')
        half0 = {lab_client.draw_seed(0) for _ in range(5000)}
        half1 = {lab_client.draw_seed(1) for _ in range(5000)}
        self.assertEqual(half0 & half1, set())

    def test_seed_redrawn_when_already_used(self):
        used = {lab_client.draw_seed(0) for _ in range(64)}
        for _ in range(200):
            s = lab_client.draw_seed(0, used)
            self.assertNotIn(s, used)
        self.assertEqual(lab_client.load_used_seeds(None, 0), set())
        p = self.dir / 'used.json'
        p.write_text(json.dumps([2, 3, 4, 5]))
        self.assertEqual(lab_client.load_used_seeds(p, 0), {2, 4})
        self.assertEqual(lab_client.load_used_seeds(p, 1), {3, 5})

    def test_seed_is_independent_of_the_arm(self):
        """The worker knows its arm, but the seed draw never reads it (protocol 5.5)."""
        src = (HERE / 'lab_client.py').read_text(encoding='utf-8')
        body = src[src.index('def draw_seed'):src.index('def load_used_seeds')]
        for forbidden in ('arm', 'incumbent', 'candidate', 'coin'):
            self.assertNotIn(forbidden, body)

    # -- body ---------------------------------------------------------------- #
    def test_body_is_the_frozen_sampling_block(self):
        with mock_server(self.basic) as (base, _srv):
            s = self.spool()
            client = make_client(base, self.basic, s)
            client.chat(messages_for(task_of(self.basic, 'mbpp/32')), {'kind': 'code'})
        deposit = json.loads(_gunzip(next((self.dir / 'requests').glob('*.json.gz'))))
        body = deposit['request']
        self.assertEqual(sorted(body), sorted(list(SAMPLING) + ['model', 'messages', 'seed']))
        for key, value in SAMPLING.items():
            self.assertEqual(body[key], value, key)
        self.assertFalse(body['stream'])
        self.assertFalse(body['cache_prompt'])
        self.assertTrue(body['verbose'])

    def test_loopback_is_hard_asserted(self):
        s = self.spool()
        with self.assertRaises(lab_common.PreflightError):
            make_client('http://10.0.0.1:8091', self.basic, s)


def _gunzip(path: Path) -> str:
    import gzip
    with gzip.open(path, 'rb') as fh:
        return fh.read().decode('utf-8')


# --------------------------------------------------------------------------- #
# the mock server itself
# --------------------------------------------------------------------------- #
class MockServerTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'spools').mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.basic = load_scenario('scenario_basic')
        self.faults = load_scenario('scenario_faults')

    def spool(self) -> Spool:
        s = Spool(self.dir / 'spools' / 'ep_1_1.jsonl')
        self.addCleanup(s.close)
        return s

    def test_endpoints(self):
        import requests
        with mock_server(self.basic) as (base, _srv):
            self.assertEqual(requests.get(base + '/health').json(), {'status': 'ok'})
            self.assertEqual(requests.get(base + '/props').json(), self.basic['props'])
            models = requests.get(base + '/v1/models').json()
            self.assertEqual(models['data'][0]['id'], self.basic['alias'])
            slots = requests.get(base + '/slots').json()
            self.assertEqual(len(slots), self.basic['total_slots'])
            parsed = lab_server.parse_metrics(requests.get(base + '/metrics').text)
        self.assertEqual(set(parsed), set(lab_server.METRIC_NAMES.values()))

    def test_kind_and_uid_recovery(self):
        tasks = self.basic['tasks']
        task = task_of(self.basic, 'mbpp/32')
        code_msgs = messages_for(task)
        self.assertEqual(lab_mock_server.classify_kind(code_msgs), 'code')
        self.assertEqual(lab_mock_server.recover_uid(code_msgs, tasks), 'mbpp/32')
        test_msgs = code_msgs + [
            {'role': 'user',
             'content': agent.TEST_PROMPT.format(entry_point=task['entry_point'])}]
        self.assertEqual(lab_mock_server.classify_kind(test_msgs), 'tests')
        repair_msgs = code_msgs + [
            {'role': 'user', 'content': agent.REPAIR_PROMPT.format(tests='x', trace='y')}]
        self.assertEqual(lab_mock_server.classify_kind(repair_msgs), 'repair')
        self.assertEqual(lab_mock_server.classify_kind(
            [{'role': 'user', 'content': lab_server.SMOKE_PROMPT}]), 'smoke')

    def test_mock_scenarios(self):
        """Every fault kind of section 8.2 produces the documented client-side effect."""
        cases = [
            ('mbpp/12', lab_client.ConnectionFailure, 'timeout'),
            ('mbpp/14', lab_client.HttpError, 'http_5xx'),
            ('mbpp/18', lab_client.ConnectionFailure, 'connection'),
            ('mbpp/20', lab_client.MalformedResponse, 'malformed'),
            ('mbpp/22', lab_client.MalformedResponse, 'malformed'),
            ('mbpp/26', lab_common.ReceiptMismatch, None),
            ('mbpp/28', lab_common.ReceiptMismatch, None),
            ('mbpp/30', lab_common.ReceiptMismatch, None),
        ]
        with mock_server(self.faults) as (base, _srv):
            for i, (uid, exc, error_class) in enumerate(cases):
                s = Spool(self.dir / 'spools' / ('ep_%d_1.jsonl' % (100 + i)))
                self.addCleanup(s.close)
                client = make_client(base, self.faults, s, request_timeout_s=0.5,
                                     server_recovery_s=0.2)
                with self.assertRaises(exc, msg=uid):
                    client.chat(messages_for(task_of(self.faults, uid)), {'kind': 'code'})
                lines = read_spool(s.path)
                if error_class is not None:
                    self.assertEqual([r['body']['error_class'] for r in lines
                                      if r['kind'] == 'call_error'], [error_class], uid)
                else:
                    self.assertEqual(len([r for r in lines if r['kind'] == 'call_response']),
                                     1, uid)
            # `length` is NOT an error: the text is used as is and truncation is recorded
            s = self.spool()
            client = make_client(base, self.faults, s)
            out = client.chat(messages_for(task_of(self.faults, 'mbpp/24')), {'kind': 'code'})
            self.assertEqual(out['finish_reason'], 'length')
            self.assertTrue(client.stats()['truncated_any'])

    def test_exit_fault_kills_the_server(self):
        scenario = dict(self.basic, faults=[{'match': {'after_requests': 1}, 'do': 'exit',
                                             'code': 1}])
        with mock_server(scenario) as (base, _srv):
            s = self.spool()
            client = make_client(base, scenario, s, server_recovery_s=0.2,
                                 request_timeout_s=0.5)
            with self.assertRaises(lab_client.ConnectionFailure):
                client.chat(messages_for(task_of(scenario, 'mbpp/32')), {'kind': 'code'})

    def test_outage_fault(self):
        import requests
        scenario = dict(self.basic, faults=[{'match': {'after_requests': 1}, 'do': 'outage',
                                             'seconds': 30}])
        with mock_server(scenario) as (base, _srv):
            s = self.spool()
            client = make_client(base, scenario, s)
            with self.assertRaises(lab_client.HttpError):
                client.chat(messages_for(task_of(scenario, 'mbpp/32')), {'kind': 'code'})
            self.assertEqual(requests.get(base + '/health').status_code, 503)
            self.assertFalse(lab_server.health(base)['ok'])

    def test_determinism_under_concurrency(self):
        """The scripted content is a function of (uid, kind, try), not of arrival order."""
        outs = []
        for _ in range(2):
            with mock_server(self.basic) as (base, _srv):
                results = {}

                def run(uid):
                    s = Spool(self.dir / 'spools' / ('ep_%s_1.jsonl'
                                                     % uid.replace('/', '_')))
                    client = make_client(base, self.basic, s)
                    results[uid] = client.chat(messages_for(task_of(self.basic, uid)),
                                               {'kind': 'code'})['text']
                    s.close()
                    os.unlink(s.path)

                threads = [threading.Thread(target=run, args=(u,))
                           for u in ('mbpp/32', 'mbpp/24', 'mbpp/26')]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                outs.append(dict(results))
        self.assertEqual(outs[0], outs[1])


# --------------------------------------------------------------------------- #
# /metrics accounting
# --------------------------------------------------------------------------- #
class MetricsTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'spools').mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.basic = load_scenario('scenario_basic')
        self.faults = load_scenario('scenario_faults')

    def test_metrics_parse(self):
        text = ('# HELP llamacpp:prompt_tokens_total x\n'
                '# TYPE llamacpp:prompt_tokens_total counter\n'
                'llamacpp:prompt_tokens_total 312\n'
                'llamacpp:tokens_predicted_total 128\n'
                'llamacpp:n_decode_total 128\n'
                'llamacpp:requests_processing 0\n'
                'llamacpp:requests_deferred 0\n'
                'some_other_metric 9\n')
        parsed = lab_server.parse_metrics(text)
        self.assertEqual(parsed['prompt_tokens_total'], 312)
        self.assertEqual(parsed['tokens_predicted_total'], 128)
        self.assertNotIn('some_other_metric', parsed)

    def test_metrics_timeout_does_not_raise(self):
        """A hanging ``/metrics`` returns ok=False after 3 tries; enrolment continues."""
        import requests
        real_get = requests.get

        def hanging(url, **kw):
            if url.endswith('/metrics'):
                raise requests.Timeout('scripted hang')
            return real_get(url, **kw)

        requests.get = hanging
        try:
            t0 = time.perf_counter()
            out = lab_server.metrics('http://127.0.0.1:1/', timeout=0.1, tries=3)
        finally:
            requests.get = real_get
        self.assertFalse(out['ok'])
        self.assertEqual(out['tries'], 3)
        self.assertIsNone(out['prompt_tokens_total'])
        self.assertLess(time.perf_counter() - t0, 15.0)

    def test_accounting_identity_on_a_clean_window(self):
        """Counter delta minus summed client usage is exactly 0 at a quiescent point."""
        with mock_server(self.basic) as (base, _srv):
            before = lab_server.metrics(base)
            s = Spool(self.dir / 'spools' / 'ep_1_1.jsonl')
            self.addCleanup(s.close)
            client = make_client(base, self.basic, s)
            outs = [client.chat(messages_for(task_of(self.basic, uid)), {'kind': 'code'})
                    for uid in ('mbpp/32', 'mbpp/24')]
            after = lab_server.metrics(base)
        self.assertTrue(before['ok'] and after['ok'])
        client_prompt = sum(o['prompt_tokens'] for o in outs)
        client_predicted = sum(o['completion_tokens'] for o in outs)
        self.assertEqual(after['prompt_tokens_total'] - before['prompt_tokens_total'],
                         client_prompt)
        self.assertEqual(after['tokens_predicted_total'] - before['tokens_predicted_total'],
                         client_predicted)

    def test_scrape_before_and_after_a_failed_try(self):
        """Protocol 13.1: the bracketing scrapes bound the cost of a try with no response."""
        scenario = dict(self.faults, count_cancelled_tokens=True)
        with mock_server(scenario) as (base, _srv):
            s = Spool(self.dir / 'spools' / 'ep_2_1.jsonl')
            self.addCleanup(s.close)
            client = make_client(base, scenario, s, request_timeout_s=0.3)
            before = lab_server.metrics(base)
            with self.assertRaises(lab_client.ConnectionFailure):
                client.chat(messages_for(task_of(scenario, 'mbpp/12')), {'kind': 'code'})
            after = lab_server.metrics(base)
            lines = read_spool(s.path)
        self.assertEqual([r for r in lines if r['kind'] == 'call_response'], [],
                         'a cancelled try has no usage; it is bounded, not measured')
        delta = after['tokens_predicted_total'] - before['tokens_predicted_total']
        self.assertGreater(delta, 0, 'this mock counts cancelled generations')
        self.assertLessEqual(delta, SAMPLING['max_tokens'],
                             'and the logical bound is max_tokens per request')

    def test_uncounted_cancelled_tokens_branch(self):
        scenario = dict(self.faults, count_cancelled_tokens=False)
        with mock_server(scenario) as (base, _srv):
            s = Spool(self.dir / 'spools' / 'ep_3_1.jsonl')
            self.addCleanup(s.close)
            client = make_client(base, scenario, s, request_timeout_s=0.3)
            before = lab_server.metrics(base)
            with self.assertRaises(lab_client.ConnectionFailure):
                client.chat(messages_for(task_of(scenario, 'mbpp/12')), {'kind': 'code'})
            after = lab_server.metrics(base)
        self.assertEqual(after['tokens_predicted_total'] - before['tokens_predicted_total'], 0)


# --------------------------------------------------------------------------- #
# lab_server identity
# --------------------------------------------------------------------------- #
class ServerIdentityTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.scenario = load_scenario('scenario_basic')
        self.gguf = self.dir / 'weights.gguf'
        self.gguf.write_bytes(b'gguf' * 64)
        self.spec = spec_for(self.scenario, self.gguf)
        self.props = dict(self.scenario['props'])
        self.props['model_path'] = str(self.gguf)
        self.models = {'object': 'list',
                       'data': [{'id': self.scenario['alias'], 'object': 'model'}]}

    def test_identity_accepts_the_frozen_server(self):
        lab_server.assert_identity(self.spec, self.props, self.models, self.props)

    def test_slot_prompt_similarity_asserted(self):
        """``server_argv`` carries the third cache switch and ``/props`` must report it."""
        argv = lab_server.server_argv(self.spec)
        self.assertIn('--slot-prompt-similarity', argv)
        self.assertEqual(argv[argv.index('--slot-prompt-similarity') + 1], '0.0')
        for switch in ('--no-cache-prompt', '--cache-ram', '--no-kv-unified', '--metrics',
                       '--no-context-shift', '--offline', '--jinja', '--log-timestamps'):
            self.assertIn(switch, argv)
        self.assertEqual(argv[argv.index('-c') + 1], '16384')
        self.assertEqual(argv[argv.index('-np') + 1], '2')
        bad = dict(self.props)
        bad.pop('slot_prompt_similarity')
        bad['default_generation_settings'] = dict(bad['default_generation_settings'])
        with self.assertRaises(lab_common.ServerIdentityError) as ctx:
            lab_server.assert_identity(self.spec, bad, self.models, None)
        self.assertIn('slot_prompt_similarity', str(ctx.exception))
        worse = dict(self.props, slot_prompt_similarity=0.1)
        with self.assertRaises(lab_common.ServerIdentityError):
            lab_server.assert_identity(self.spec, worse, self.models, None)

    def test_server_identity_refusals(self):
        cases = {
            'alias': dict(self.props, model_alias='other'),
            'total_slots': dict(self.props, total_slots=1),
            'n_ctx': dict(self.props, n_ctx=4096,
                          default_generation_settings={'n_ctx': 4096}),
            'model_path': dict(self.props, model_path=str(self.dir / 'other.gguf')),
            'build_info': dict(self.props, build_info='b6000-deadbee'),
        }
        for finding, props in cases.items():
            with self.assertRaises(lab_common.ServerIdentityError, msg=finding) as ctx:
                lab_server.assert_identity(self.spec, props, self.models, None)
            self.assertIn(finding, str(ctx.exception))
        with self.assertRaises(lab_common.ServerIdentityError) as ctx:
            lab_server.assert_identity(self.spec, self.props,
                                       {'object': 'list', 'data': []}, None)
        self.assertIn('models_endpoint', str(ctx.exception))
        with self.assertRaises(lab_common.ServerIdentityError) as ctx:
            lab_server.assert_identity(self.spec, self.props, self.models,
                                       dict(self.props, build_info='b6000-4fea119dX'))
        self.assertIn('props_mismatch', str(ctx.exception))

    def test_gguf_refusals(self):
        self.assertEqual(lab_server.assert_gguf(self.spec), self.spec.gguf_sha256)
        with self.assertRaises(lab_common.ServerIdentityError) as ctx:
            lab_server.assert_gguf(spec_for(self.scenario, self.gguf, gguf_bytes=1))
        self.assertIn('gguf_bytes', str(ctx.exception))
        with self.assertRaises(lab_common.ServerIdentityError) as ctx:
            lab_server.assert_gguf(spec_for(self.scenario, self.gguf, gguf_sha256='0' * 64))
        self.assertIn('gguf_sha256', str(ctx.exception))
        with self.assertRaises(lab_common.ServerIdentityError):
            lab_server.assert_gguf(spec_for(self.scenario, self.dir / 'missing.gguf'))

    def test_argv_is_a_pure_function(self):
        self.assertEqual(lab_server.server_argv(self.spec),
                         lab_server.server_argv(self.spec))

    def test_health_of_the_mock(self):
        with mock_server(self.scenario) as (base, _srv):
            h = lab_server.health(base)
            self.assertTrue(h['ok'])
            self.assertEqual(h['slots_busy'], 0)
            p = lab_server.probe(base)
            self.assertEqual(p['props'], self.scenario['props'])
        self.assertFalse(lab_server.health(base)['ok'])

    def test_no_test_starts_a_real_server(self):
        """The two functions that spawn a llama-server are never called from this file."""
        src = (HERE / 'tests_lab_serving.py').read_text(encoding='utf-8')
        for name in ('start', 'restart', 'smoke'):
            self.assertNotIn('lab_server.' + name + '(', src, name)


# --------------------------------------------------------------------------- #
# the execution lock
# --------------------------------------------------------------------------- #
LOCK_PROBE_SCRIPT = r'''
import json, sys, time
sys.path.insert(0, %(here)r)
import lab_worker
from lab_client import Spool
spool = Spool(%(spool)r)
spool.set_inv('c' * 32)
lab_worker.install_execution_lock(%(lock)r, spool, max_lock_wait_s=60.0)
import sandbox
sandbox.run_program('import time\ntime.sleep(%(sleep)s)\n', timeout_s=20)
spool.write('episode_final', {'record_sha256': 'x'}, durable=True)
spool.close()
'''


class ExecutionLockTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'spools').mkdir()
        self.lock = self.dir / 'sandbox.lock'
        self.addCleanup(self.tmp.cleanup)

    def test_execution_lock_serialises_two_workers(self):
        """Two workers never run a sandboxed program concurrently (protocol 5.7)."""
        procs, spools = [], []
        for i in (1, 2):
            spool = self.dir / 'spools' / ('ep_%d_1.jsonl' % i)
            spools.append(spool)
            script = LOCK_PROBE_SCRIPT % {'here': str(HERE), 'spool': str(spool),
                                          'lock': str(self.lock), 'sleep': 0.6}
            procs.append(subprocess.Popen([sys.executable, '-c', script],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        for p in procs:
            out, err = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, err.decode()[-2000:])
        windows = []
        waits = []
        for spool in spools:
            row = [r for r in read_spool(spool) if r['kind'] == 'sandbox_exec'][0]
            end = row['t_wall_ns']
            windows.append((end - int(row['body']['seconds'] * 1e9), end))
            waits.append(row['body']['lock_wait_s'])
        windows.sort()
        self.assertLessEqual(windows[0][1], windows[1][0],
                             'the two sandboxed executions overlapped')
        self.assertGreater(max(waits), 0.1, 'the second worker did not wait for the lock')
        self.assertLess(min(waits), 0.1, 'the first worker should not have waited')

    def test_every_run_program_call_path_holds_the_lock(self):
        """A sentinel installed *under* the wrapper raises unless the flock is held."""
        seen = []
        original = sandbox.run_program

        def sentinel(source, **kw):
            if not lab_worker.execution_lock_held():
                raise AssertionError('run_program called without the execution lock')
            fd = os.open(str(self.lock), os.O_RDWR | os.O_CREAT, 0o644)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    raise AssertionError('the execution lock was not actually held')
                except BlockingIOError:
                    pass
            finally:
                os.close(fd)
            seen.append(kw.get('timeout_s'))
            return {'passed': True, 'returncode': 0, 'stdout': '', 'stderr': '',
                    'stdout_tail': '', 'timed_out': False, 'seconds': 0.0, 'executed': True,
                    'flags': [], 'limits_applied': '', 'sandbox_kind': 'seatbelt',
                    'profile_sha256': 'p' * 64}

        sandbox.run_program = sentinel
        self.addCleanup(_restore_run_program)
        lab_worker.install_execution_lock(self.lock, None, max_lock_wait_s=10.0)
        self.assertIs(agent.run_program, sandbox.run_program)
        self.assertIs(verify_mod.run_program, sandbox.run_program)
        # both call paths: the agent's own self-test and the hidden-test verifier
        agent.run_program('print(1)', timeout_s=1.0)
        verify_mod.verify({'benchmark': 'mbpp', 'entry_point': 'f', 'test_list': ['assert 1'],
                           'test_imports': []}, 'def f():\n    return 1\n', timeout_s=2.0)
        self.assertEqual(len(seen), 2)
        self.assertFalse(lab_worker.execution_lock_held())

    def test_lock_wait_exceeded_is_a_sandbox_kill(self):
        """Protocol 6.4 row 7: a wait beyond ``max_lock_wait_s`` fails that execution."""
        holder = lab_worker.ExecutionLock(self.lock, max_lock_wait_s=5.0)
        self.addCleanup(_restore_run_program)
        with holder:
            proc = subprocess.Popen(
                [sys.executable, '-c',
                 'import sys; sys.path.insert(0, %r)\n'
                 'import json, lab_worker\n'
                 'w = lab_worker.install_execution_lock(%r, None, max_lock_wait_s=0.2)\n'
                 'import sandbox\n'
                 'print(json.dumps(sandbox.run_program("print(1)", timeout_s=5)))\n'
                 % (str(HERE), str(self.lock))],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, 0, err.decode()[-2000:])
        run = json.loads(out.decode().strip().splitlines()[-1])
        self.assertFalse(run['passed'])
        self.assertTrue(run['timed_out'])
        self.assertFalse(run['executed'])
        self.assertEqual(run['seconds'], 0.2)


# --------------------------------------------------------------------------- #
# the worker
# --------------------------------------------------------------------------- #
class WorkerTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for sub in ('spools', 'records', 'requests', 'jobs', 'logs'):
            (self.dir / sub).mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(_restore_run_program)   # run_job installs the lock wrapper in-process
        self.basic = load_scenario('scenario_basic')
        self.faults = load_scenario('scenario_faults')
        self.tasks_path = self.dir / 'tasks.json'
        self.tasks_path.write_text(json.dumps(self.basic['tasks']), encoding='utf-8')

    def make_job(self, base_url: str, scenario: dict, *, uid='mbpp/32',
                 workflow='single_shot', arrival=1, worker_index=0, **kw) -> dict:
        golden = golden_for(scenario)
        job = {
            'trial': 'T4', 'inv': 'd' * 32, 'arrival': arrival, 'attempt': 1,
            'pair': (arrival + 1) // 2, 'position': 1 if arrival % 2 else 2,
            'arm': 'candidate', 'workflow': workflow, 'task_uid': uid,
            'server': {'server_id': 'coder', 'base_url': base_url + '/v1',
                       'alias': scenario['alias']},
            'worker_index': worker_index,
            'sampling': dict(SAMPLING),
            'limits': {'request_timeout_s': 5.0, 'max_connection_retries': 0,
                       'server_recovery_s': 0.5, 'max_lock_wait_s': 30.0},
            'golden': {'props': golden.props, 'generation_settings': golden.generation_settings,
                       'mask': list(golden.mask), 'float_tolerance': golden.float_tolerance},
            'sandbox': {'timeout_s': 10.0, 'cpu_s': 10, 'output_cap_bytes': 65536,
                        'mem_bytes_requested_not_enforced_on_macos': 2147483648},
            'max_repair_rounds': 2,
            'config_sha256': 'e' * 64,
            'paths': {
                'spool': str(self.dir / 'spools' / ('ep_%d_1.jsonl' % arrival)),
                'records': str(self.dir / 'records'),
                'requests': str(self.dir / 'requests'),
                'tasks': str(self.tasks_path),
                'sandbox_lock': str(self.dir / 'sandbox.lock'),
            },
            'assignment_seq': 3,
        }
        job.update(kw)
        job['payload_sha256'] = lab_worker.payload_sha256(job)
        return job

    def write_job(self, job: dict) -> Path:
        p = self.dir / 'jobs' / ('job_%d_1.json' % job['arrival'])
        p.write_text(json.dumps(job), encoding='utf-8')
        return p

    def spawn(self, job: dict) -> subprocess.Popen:
        proc = subprocess.Popen(
            [sys.executable, str(HERE / 'lab_worker.py'), '--job', str(self.write_job(job))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self.addCleanup(_reap, proc)
        return proc

    # -- happy path ---------------------------------------------------------- #
    def test_agent_unchanged_and_runs_end_to_end(self):
        """``agent.py`` is byte-identical and ``run_episode`` runs against the mock."""
        for name, digest in REUSED_SHA256.items():
            self.assertEqual(lab_common.sha256_file(lab_common.LS_DIR / name), digest, name)
        with mock_server(self.basic) as (base, _srv):
            job = self.make_job(base, self.basic, uid='mbpp/32')
            outcome = lab_worker.run_job(job, sandbox_lock_path=self.dir / 'sandbox.lock')
            lines = read_spool(Path(job['paths']['spool']))
        self.assertEqual(lines[0]['kind'], 'job_accepted')
        self.assertEqual(lines[-1]['kind'], 'episode_final')
        self.assertEqual(outcome, lines[-1]['body']['outcome'])
        self.assertEqual(outcome['success'], 1)
        self.assertGreater(outcome['latency_s'], 0.0)
        self.assertEqual(outcome['n_llm_calls'], 1)
        self.assertEqual(outcome['n_verifier_executions'], 1)
        self.assertEqual(outcome['n_self_test_executions'], 0)
        self.assertFalse(outcome['infra_flag'])
        self.assertTrue(outcome['sentinel_seen'])
        record = self.dir / 'records' / ('%s.json' % lines[-1]['body']['record_sha256'])
        self.assertTrue(record.exists())
        self.assertEqual(lab_common.sha256_canonical(json.loads(record.read_text())),
                         lines[-1]['body']['record_sha256'])

    def test_self_test_repair_episode(self):
        with mock_server(self.basic) as (base, _srv):
            job = self.make_job(base, self.basic, uid='mbpp/12',
                                workflow='self_test_repair')
            outcome = lab_worker.run_job(job, sandbox_lock_path=self.dir / 'sandbox.lock')
            lines = read_spool(Path(job['paths']['spool']))
        self.assertGreaterEqual(outcome['n_llm_calls'], 2)
        self.assertGreaterEqual(outcome['n_self_test_executions'], 1)
        self.assertEqual(outcome['n_verifier_executions'], 1)
        kinds = [r['body'].get('kind') for r in lines if r['kind'] == 'call_started']
        self.assertEqual(kinds[0], 'code')
        self.assertEqual(kinds[1], 'tests')
        purposes = [r['body']['purpose'] for r in lines if r['kind'] == 'sandbox_exec']
        self.assertEqual(purposes[-1], 'verify')
        self.assertIn('self_test', purposes)

    def test_outcome_object_matches_the_event_schema(self):
        with mock_server(self.basic) as (base, _srv):
            job = self.make_job(base, self.basic)
            outcome = lab_worker.run_job(job, sandbox_lock_path=self.dir / 'sandbox.lock')
        self.assertEqual(sorted(outcome), sorted([
            'success', 'latency_s', 'completion_tokens', 'prompt_tokens', 'n_llm_calls',
            'n_failed_calls', 'connection_retries', 'n_self_test_executions',
            'n_verifier_executions', 'repair_rounds', 'self_test_passed',
            'request_timeout_any', 'episode_timeout', 'verifier_timeout', 'truncated_any',
            'sentinel_seen', 'entry_point_defined', 'error_class', 'infra_flag']))
        self.assertIsInstance(outcome['success'], int)
        self.assertIsInstance(outcome['latency_s'], float)

    # -- failure rows --------------------------------------------------------- #
    def test_client_failures_are_outcomes_not_exclusions(self):
        """6.4 rows 1, 2, 3, 12, 13: the episode completes and is revealed with success 0."""
        cases = {'mbpp/12': 'timeout', 'mbpp/14': 'http_5xx', 'mbpp/20': 'malformed',
                 'mbpp/22': 'malformed', 'mbpp/26': 'receipt_mismatch',
                 'mbpp/28': 'receipt_mismatch', 'mbpp/30': 'receipt_mismatch'}
        with mock_server(self.faults) as (base, _srv):
            for i, (uid, error_class) in enumerate(cases.items()):
                job = self.make_job(base, self.faults, uid=uid, arrival=10 + i)
                job['limits']['request_timeout_s'] = 0.5
                outcome = lab_worker.run_job(job,
                                             sandbox_lock_path=self.dir / 'sandbox.lock')
                self.assertEqual(outcome['success'], 0, uid)
                self.assertEqual(outcome['error_class'], error_class, uid)
                self.assertTrue(outcome['infra_flag'], uid)
                self.assertTrue(all(v == v for v in (outcome['latency_s'],)), uid)
                lines = read_spool(Path(job['paths']['spool']))
                self.assertEqual(lines[-1]['kind'], 'episode_final', uid)

    def test_truncation_is_not_an_error(self):
        with mock_server(self.faults) as (base, _srv):
            job = self.make_job(base, self.faults, uid='mbpp/24', arrival=30)
            outcome = lab_worker.run_job(job, sandbox_lock_path=self.dir / 'sandbox.lock')
        self.assertTrue(outcome['truncated_any'])
        self.assertIsNone(outcome['error_class'])
        self.assertEqual(outcome['success'], 1)

    def test_worker_death_is_terminal(self):
        """6.4 row 10: the arrival is revealed with success 0 and the certified elapsed time."""
        scenario = dict(self.faults)
        with mock_server(scenario) as (base, _srv):
            job = self.make_job(base, scenario, uid='mbpp/12', arrival=40)
            job['limits']['request_timeout_s'] = 30.0
            proc = self.spawn(job)
            spool = Path(job['paths']['spool'])
            deadline = time.time() + 30
            while time.time() < deadline:
                lines = read_spool(spool)
                if any(r['kind'] == 'call_started' for r in lines):
                    break
                time.sleep(0.02)
            time.sleep(0.2)
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=30)
            lines = read_spool(spool)
        self.assertTrue(any(r['kind'] == 'job_accepted' for r in lines))
        self.assertTrue(any(r['kind'] == 'call_started' for r in lines))
        self.assertFalse(any(r['kind'] == 'episode_final' for r in lines))
        reveal = lab_worker.terminal_reveal(lines, 'worker_died')
        self.assertEqual(reveal['outcome']['success'], 0)
        self.assertEqual(reveal['outcome']['error_class'], 'worker_died')
        self.assertGreaterEqual(reveal['certified_ell'], 0.0)
        self.assertEqual(reveal['outcome']['latency_s'], reveal['certified_ell'])
        self.assertEqual(reveal['tokens_known'], 0)
        self.assertTrue(reveal['outcome']['infra_flag'])

    def test_worker_death_before_the_first_request(self):
        """6.4 row 18 / critic N5: ``ell = 0.0`` and ``tokens_known = 0``, both finite."""
        s = Spool(self.dir / 'spools' / 'ep_99_1.jsonl')
        s.set_inv('f' * 32)
        s.write('job_accepted', {'arm': 'incumbent', 'workflow': 'single_shot',
                                 'task_uid': 'mbpp/32', 'job_sha256': 'a' * 64,
                                 'payload_sha256': 'b' * 64}, durable=True)
        s.close()
        lines = read_spool(s.path)
        for error_class in ('worker_died', 'interrupted'):
            reveal = lab_worker.terminal_reveal(lines, error_class)
            self.assertEqual(reveal['certified_ell'], 0.0)
            self.assertEqual(reveal['tokens_known'], 0)
            self.assertEqual(reveal['outcome']['latency_s'], 0.0)
            self.assertEqual(reveal['outcome']['completion_tokens'], 0)
            self.assertEqual(reveal['outcome']['success'], 0)
            self.assertEqual(reveal['outcome']['n_llm_calls'], 0)

    def test_hard_cap_is_computed_and_terminal(self):
        """PG-15: the cap is computed from the formula, never typed, and it is an endpoint."""
        execution = {'request_timeout_s': 180.0, 'server_recovery_s': 180.0,
                     'sandbox_timeout_s': 10.0, 'max_lock_wait_s': 120.0}
        cap = lab_worker.episode_hard_cap_s(execution)
        self.assertEqual(cap, 3354.0)
        self.assertEqual(lab_worker.request_timeout_s(30.0), 180.0)
        self.assertEqual(lab_worker.request_timeout_s(60.0), 240.0)
        self.assertEqual(lab_worker.request_timeout_s(46.0), 210.0)
        src = (HERE / 'lab_worker.py').read_text(encoding='utf-8')
        self.assertNotIn('3354', src, 'the cap is computed, never typed')

        with mock_server(self.faults) as (base, _srv):
            job = self.make_job(base, self.faults, uid='mbpp/12', arrival=41)
            job['limits']['request_timeout_s'] = 30.0
            proc = self.spawn(job)
            spool = Path(job['paths']['spool'])
            deadline = time.time() + 30
            while time.time() < deadline:
                if any(r['kind'] == 'call_started' for r in read_spool(spool)):
                    break
                time.sleep(0.02)
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)   # the orchestrator enforces it
            proc.wait(timeout=30)
            lines = read_spool(spool)
        reveal = lab_worker.terminal_reveal(lines, 'episode_timeout', hard_cap_s=cap)
        self.assertEqual(reveal['outcome']['latency_s'], cap)
        self.assertTrue(reveal['outcome']['episode_timeout'])
        self.assertEqual(reveal['outcome']['success'], 0)
        self.assertFalse(any(r['kind'] == 'episode_final' for r in lines))
        with self.assertRaises(lab_common.SpoolError):
            lab_worker.terminal_reveal(lines, 'episode_timeout')

    def test_worker_error_exits_three(self):
        """An exception outside ``run_episode`` is spooled and the process exits 3."""
        with mock_server(self.basic) as (base, _srv):
            blocker = self.dir / 'blocked'
            blocker.write_text('not a directory')
            job = self.make_job(base, self.basic, arrival=50)
            job['paths']['records'] = str(blocker / 'records')
            job['payload_sha256'] = lab_worker.payload_sha256(job)
            proc = self.spawn(job)
            _out, err = proc.communicate(timeout=120)
            lines = read_spool(Path(job['paths']['spool']))
        self.assertEqual(proc.returncode, lab_worker.WORKER_ERROR_EXIT, err.decode()[-2000:])
        errs = [r for r in lines if r['kind'] == 'worker_error']
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0]['body']['stage'], 'record')
        self.assertFalse(any(r['kind'] == 'episode_final' for r in lines))

    def test_no_rerun_of_any_kind(self):
        """``max_attempts = 1``: a completed attempt's spool refuses to be reopened."""
        with mock_server(self.basic) as (base, _srv):
            job = self.make_job(base, self.basic, arrival=60)
            lab_worker.run_job(job, sandbox_lock_path=self.dir / 'sandbox.lock')
        with self.assertRaises(lab_common.SpoolError):
            Spool(Path(job['paths']['spool']))
        src = (HERE / 'lab_worker.py').read_text(encoding='utf-8')
        self.assertNotIn('max_attempts = 2', src)
        self.assertIn('max_attempts = 1', src)

    def test_graceful_stop_drains_the_pair(self):
        """6.4 row 11b: a graceful stop drains, and a pause exists only between pairs.

        The worker-side content of the rule is protocol 5.1: a worker never blocks on the
        orchestrator, so when the process that dispatched the pair goes away mid-episode the
        two in-flight episodes still run to their frozen end, complete their spools and exit
        0 -- which is what makes "the in-flight pair finishes and is revealed" implementable
        at all.  Here the dispatcher exits immediately after spawning the pair, and the
        arrival it would have dispatched next never starts."""
        with mock_server(self.basic) as (base, _srv):
            jobs = [self.make_job(base, self.basic, uid=uid, arrival=70 + i, worker_index=i)
                    for i, uid in enumerate(('mbpp/32', 'mbpp/24'))]
            next_job = self.make_job(base, self.basic, uid='mbpp/26', arrival=80)
            self.write_job(next_job)
            script = (
                'import subprocess, sys, os\n'
                'for jf in %r:\n'
                '    subprocess.Popen([sys.executable, %r, "--job", jf],\n'
                '                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n'
                '                     start_new_session=True)\n'
                'os._exit(0)\n'
                % ([str(self.write_job(j)) for j in jobs], str(HERE / 'lab_worker.py')))
            dispatcher = subprocess.Popen([sys.executable, '-c', script])
            dispatcher.wait(timeout=60)
            self.assertEqual(dispatcher.returncode, 0)

            deadline = time.time() + 180
            spools = [Path(j['paths']['spool']) for j in jobs]
            while time.time() < deadline:
                if all(any(r['kind'] == 'episode_final' for r in read_spool(p))
                       for p in spools):
                    break
                time.sleep(0.05)
            for p in spools:
                lines = read_spool(p)
                self.assertEqual(lines[-1]['kind'], 'episode_final',
                                 'an in-flight episode did not drain after the stop')
                self.assertEqual(lines[0]['kind'], 'job_accepted')
                self.assertIn('outcome', lines[-1]['body'])
        self.assertFalse(Path(next_job['paths']['spool']).exists(),
                         'an arrival was dispatched after the stop was requested')

    # -- job payload ----------------------------------------------------------- #
    def test_t4_canonical_payload_identity(self):
        """PG-14: the two jobs of a T4 pair differ only in the removed keys."""
        with mock_server(self.basic) as (base, _srv):
            a = self.make_job(base, self.basic, uid='mbpp/32', arrival=1, worker_index=0)
            b = self.make_job(base, self.basic, uid='mbpp/24', arrival=2, worker_index=1)
        b['arm'] = 'incumbent'
        b['paths'] = dict(b['paths'], spool=str(self.dir / 'spools' / 'ep_2_1.jsonl'))
        pa, pb = (lab_worker.canonical_job_payload(a), lab_worker.canonical_job_payload(b))
        self.assertEqual(lab_common.canonical_json(pa), lab_common.canonical_json(pb))
        self.assertEqual(lab_worker.payload_sha256(a), lab_worker.payload_sha256(b))
        for key in lab_worker.CANONICAL_JOB_DROP:
            self.assertNotIn(key, pa)
        self.assertNotIn('task', pa, 'task content is loaded from the roster, not the job')

    def test_task_is_loaded_from_the_roster_file(self):
        job = {'task_uid': 'mbpp/32', 'paths': {'tasks': str(self.tasks_path)}}
        self.assertEqual(lab_worker.load_task(job)['uid'], 'mbpp/32')
        with self.assertRaises(lab_common.PreflightError):
            lab_worker.load_task({'task_uid': 'mbpp/32', 'paths': {}})
        with self.assertRaises(lab_common.PreflightError):
            lab_worker.load_task({'task_uid': 'nope/1',
                                  'paths': {'tasks': str(self.tasks_path)}})

    def test_token_paths_round_trip(self):
        p = lab_common.WORK_ROOT / 'T1' / 'records' / 'a.json'
        self.assertEqual(lab_worker.resolve_token_path(lab_common.tokenize_path(p)), p)
        self.assertEqual(lab_worker.resolve_token_path(str(self.dir / 'x')), self.dir / 'x')
        with self.assertRaises(lab_common.UntokenizablePath):
            lab_worker.resolve_token_path('<NOPE>/x')

    def test_certified_elapsed_is_monotone_in_the_spool(self):
        s = Spool(self.dir / 'spools' / 'ep_98_1.jsonl')
        s.write('job_accepted', {'a': 1}, durable=False)
        self.assertEqual(lab_worker.certified_ell(read_spool(s.path)), 0.0)
        s.write('call_started', {'t_c1_ns': 1_000_000_000, 't_send_ns': 1_500_000_000},
                durable=False)
        self.assertAlmostEqual(lab_worker.certified_ell(read_spool(s.path)), 0.5)
        s.write('call_response', {'t_recv_ns': 3_000_000_000,
                                  'usage': {'completion_tokens': 11, 'prompt_tokens': 3}},
                durable=False)
        s.close()
        lines = read_spool(s.path)
        self.assertAlmostEqual(lab_worker.certified_ell(lines), 2.0)
        self.assertEqual(lab_worker.tokens_known(lines), 11)


if __name__ == '__main__':
    unittest.main()
