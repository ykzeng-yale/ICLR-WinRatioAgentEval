"""EB1a focused tests: the real server start, its identity and the golden objects.

Repair contract EB1 (session 60, after root's 20:40 NO-GO,
``reviews/prerun_bundle_go_nogo_20260923_2040.md`` item 1, route (a)).  Every check below has
a NEGATIVE CONTROL beside it: the same call on an input the check must refuse, asserted to be
refused, so no check here can pass by being unable to fail.

What runs, and what does not:

* ``lab_server.start`` / ``restart`` launch a real child process, but the "launcher" is a
  two-line shell script that is never a model: by default it ``exec``s
  ``eb1c_llama_shim.py``, so the CHILD ITSELF binds the frozen port and serves ``/health``,
  ``/props``, ``/v1/models`` and the smoke completion through ``lab_mock_server`` (the
  scenario is written to the shim's state directory by :func:`served`); a few tests use a
  bare ``exit 3`` launcher.  ``lab_server.start`` accepts a server only when the child is
  the port's one listener (EB1 fix, reviewers 1 and 2), so the fixture that used to answer
  from a thread of THIS process beside an ``exec sleep 30`` child -- the "two servers on one
  port" case -- is gone; :func:`mock_server` (an in-thread listener) remains only as the
  FOREIGN listener that must be refused.  No llama-server, no model, no network beyond
  127.0.0.1.
* The orchestrator is exercised through ``preflight``, ``make_context``, ``World.start_servers``
  and ``run_trial`` on the mock freeze tree of ``dryrun_live_ab``.  The subprocess controls
  that run ``lab_orchestrator.main`` end to end are repair step EB1c, not this file.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement):
this file is not a harness file and does not move the harness pin.
"""
from __future__ import annotations

import contextlib
import copy
import json
import os
import shutil
import signal
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import dryrun_live_ab as dry                                            # noqa: E402
import eb1c_llama_shim as shim                                          # noqa: E402
import lab_client                                                       # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_mock_server                                                  # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_server                                                       # noqa: E402
import lab_verify_log                                                   # noqa: E402
from lab_common import sha256_canonical, sha256_file, sha256_text      # noqa: E402

COMMIT = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'
SAMPLING = {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0,
            "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
            "mirostat": 0, "max_tokens": 1024, "cache_prompt": False, "stream": False,
            "verbose": True}


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return int(s.getsockname()[1])


def basic_scenario() -> dict:
    return json.loads((LIVE / 'testdata' / 'scenario_basic.json').read_text('utf-8'))


def golden_generation_settings(scenario: dict) -> dict:
    """What the pre-freeze smoke would have captured from this mock (as tests_lab_serving)."""
    gen = dict(scenario.get('defaults') or {})
    for key in ('temperature', 'top_p', 'top_k', 'min_p', 'typical_p', 'repeat_penalty',
                'presence_penalty', 'frequency_penalty', 'mirostat'):
        gen[key] = SAMPLING[key]
    gen['n_predict'] = SAMPLING['max_tokens']
    return gen


@contextlib.contextmanager
def served(host: 'Host', scenario: dict):
    """A free loopback port whose server will be the CHILD ``lab_server.start`` launches:
    the shim serves ``scenario`` there (every launch, whatever its start count).  Yields
    ``(port, None)`` in the shape :func:`mock_server` used to."""
    (host.state / 'scenarios.json').write_text(json.dumps([scenario]), encoding='utf-8')
    yield free_port(), None


@contextlib.contextmanager
def mock_server(scenario: dict, port: int = 0):
    """A listener in a thread of THIS process -- never the launched child.  Used only as the
    foreign listener ``lab_server.start`` must refuse."""
    srv, port = lab_mock_server.make_server(scenario, port=port)
    thread = threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.01},
                              daemon=True)
    thread.start()
    try:
        yield port, srv
    finally:
        with contextlib.suppress(Exception):
            srv.shutdown()
        with contextlib.suppress(Exception):
            srv.server_close()
        thread.join(timeout=5)


class Host:
    """A temporary 'host': a dummy GGUF, a shell-script launcher, one library beside it and
    the serving manifest that names them.  The default launcher ``exec``s the EB1c shim, which
    serves the scenario :func:`served` wrote to ``state`` on the port of the argv it got."""

    def __init__(self, root: Path, *, launcher_body: str | None = None) -> None:
        self.root = root
        self.bin = root / 'build' / 'bin'
        self.bin.mkdir(parents=True)
        self.state = root / 'shim_state'
        self.state.mkdir(parents=True)
        self.gguf = root / 'weights.gguf'
        self.gguf.write_bytes(b'GGUF' + b'\0' * 252)
        self.launcher = self.bin / 'llama-server'
        self.write_launcher(launcher_body if launcher_body is not None else
                            "%s='%s' exec '%s' '%s' \"$@\""
                            % (shim.STATE_ENV, self.state, sys.executable,
                               HERE / 'eb1c_llama_shim.py'))
        self.lib = self.bin / 'libfake.0.dylib'
        self.lib.write_bytes(b'not a real library')
        self.manifest = {
            'llama_cpp_commit': COMMIT,
            'launcher_sha256': sha256_file(self.launcher),
            'libraries': [{'name': 'libfake.0.dylib', 'sha256': sha256_file(self.lib)}],
            'props_build_info': 'b6000-4fea119d',
        }

    def write_launcher(self, body: str) -> None:
        self.launcher.write_text('#!/bin/sh\n%s\n' % body, encoding='utf-8')
        self.launcher.chmod(self.launcher.stat().st_mode | stat.S_IXUSR)

    @property
    def manifest_sha(self) -> str:
        return sha256_canonical(self.manifest)

    def spec(self, port: int, **kw) -> lab_server.ServerSpec:
        scenario = basic_scenario()
        params = dict(server_id='coder', port=port, alias=scenario['alias'],
                      gguf_path=self.gguf, gguf_bytes=self.gguf.stat().st_size,
                      gguf_sha256=sha256_file(self.gguf), llama_bin=self.launcher,
                      llama_commit=COMMIT, args=(), log_path=self.root / 'logs' / 'llama.log',
                      n_slots=2, n_ctx=16384)
        params.update(kw)
        return lab_server.ServerSpec(**params)

    def scenario(self) -> dict:
        """The mock serves the RAW /props a real server would: the absolute model path."""
        sc = basic_scenario()
        sc['props'] = dict(sc['props'], model_path=str(self.gguf))
        return sc


class ServerCase(unittest.TestCase):
    """Every test gets a fresh host and must leave no child behind."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='eb1_'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.host = Host(self.tmp)
        self.children_before = set(lab_server._CHILDREN)
        self.addCleanup(self._no_orphans)

    def _no_orphans(self) -> None:
        leaked = set(lab_server._CHILDREN) - self.children_before
        for pid in leaked:
            lab_server.stop(pid, grace_s=1.0)
        self.assertEqual(leaked, set(), 'a test left a child running')

    def golden(self, scenario: dict) -> dict:
        return {'props': lab_server.tokenized_props(scenario['props']),
                'generation_settings': golden_generation_settings(scenario),
                'mask': ['seed'], 'float_tolerance': 1e-6}

    def start(self, spec, scenario, **kw):
        golden = kw.pop('golden', None) or self.golden(scenario)
        params = dict(golden_props=golden['props'], golden=golden, sampling=dict(SAMPLING),
                      timeout_s=10.0, serving_manifest=self.host.manifest,
                      serving_manifest_sha256=self.host.manifest_sha)
        params.update(kw)
        return lab_server.start(spec, **params)

    def failure(self, fn, *args, **kw) -> dict:
        with self.assertRaises(lab_common.ServerStartFailed) as caught:
            fn(*args, **kw)
        record = caught.exception.record
        lab_eventlog.validate_event('server_start_failed', record)
        return record


# --------------------------------------------------------------------------- #
# 1. start: success, and every failure stops the child and carries the record
# --------------------------------------------------------------------------- #
class StartTests(ServerCase):

    def test_a_good_start_returns_an_observed_body_and_a_live_child(self):
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _srv):
            body = self.start(self.host.spec(port), sc)
            try:
                lab_eventlog.validate_event('server_started', body)
                self.assertIsNone(lab_server.exit_status(body['pid']), 'the child runs')
                self.assertIs(body['props_matches_golden'], True)
                self.assertIs(body['smoke']['ok'], True)
                self.assertIs(body['smoke']['receipt_matches_golden'], True)
                self.assertGreater(body['load_seconds'], 0.0)
                self.assertEqual(body['gguf']['sha256'], sha256_file(self.host.gguf))
            finally:
                lab_server.stop(body['pid'])
        self.assertIsNotNone(lab_server.exit_status(body['pid']))

    def test_control_a_golden_that_differs_is_refused_and_the_child_is_stopped(self):
        sc = self.host.scenario()
        golden = self.golden(sc)
        golden['props'] = dict(golden['props'], total_slots=3)
        with served(self.host, sc) as (port, _srv):
            rec = self.failure(self.start, self.host.spec(port), sc, golden=golden)
        self.assertEqual((rec['stage'], rec['findings']), ('identity', ['props_mismatch']))
        self.assertGreater(rec['pid'], 0)
        self.assertEqual(lab_server.exit_status(rec['pid']), rec['returncode'])
        self.assertIsNotNone(rec['returncode'], 'the stop observed the child end')
        self.assertEqual(rec['kind'], 'start')
        self.assertEqual(rec['restart_index'], 0)
        self.assertEqual(rec['props_sha256'],
                         sha256_canonical(lab_server.tokenized_props(sc['props'])))

    def test_a_child_that_exits_before_healthy_is_process_exited_not_build_info(self):
        self.host.write_launcher('exit 3')
        self.host.manifest['launcher_sha256'] = sha256_file(self.host.launcher)
        rec = self.failure(self.start, self.host.spec(free_port()), self.host.scenario())
        self.assertEqual((rec['stage'], rec['findings']), ('launch', ['process_exited']))
        self.assertEqual(rec['returncode'], 3)
        self.assertNotIn('build_info', rec['findings'])

    def test_control_a_live_child_that_never_answers_is_a_health_timeout(self):
        sc = self.host.scenario()
        sc['_shim'] = {'never_listen': True}            # alive, never binds the port
        with served(self.host, sc) as (port, _srv):
            rec = self.failure(self.start, self.host.spec(port), sc, timeout_s=0.6)
        self.assertEqual((rec['stage'], rec['findings']), ('health', ['health_timeout']))
        self.assertEqual(rec['returncode'], -signal.SIGTERM, 'stopped by lab_server.stop')
        self.assertIsNone(rec['props_sha256'])

    def test_gguf_failures_are_stage_gguf_and_launch_nothing(self):
        port = free_port()
        for kw, finding in (({'gguf_bytes': 1}, 'gguf_bytes'),
                            ({'gguf_sha256': '0' * 64}, 'gguf_sha256'),
                            ({'gguf_path': self.tmp / 'missing.gguf'}, 'gguf_bytes')):
            with self.subTest(finding=finding):
                before = dict(lab_server._CHILDREN)
                rec = self.failure(self.start, self.host.spec(port, **kw),
                                   self.host.scenario())
                self.assertEqual((rec['stage'], rec['findings']), ('gguf', [finding]))
                self.assertEqual((rec['pid'], rec['returncode']), (0, None))
                self.assertEqual(dict(lab_server._CHILDREN), before)
                self.assertFalse((self.tmp / 'logs' / 'llama.log').exists())

    def test_the_serving_manifest_is_reverified_and_an_absent_one_refused(self):
        spec = self.host.spec(free_port())
        self.assertEqual(lab_server.serving_manifest_problems(
            spec, self.host.manifest, self.host.manifest_sha), [], 'the control passes')
        bad_lib = copy.deepcopy(self.host.manifest)
        bad_lib['libraries'][0]['sha256'] = '1' * 64
        cases = {
            'absent': (None, None),
            'digest': (self.host.manifest, '2' * 64),
            'commit': (dict(self.host.manifest, llama_cpp_commit='0' * 40), None),
            'library_sha256:libfake.0.dylib': (bad_lib, None),
            'libraries_empty': (dict(self.host.manifest, libraries=[]), None),
        }
        for label, (manifest, digest) in cases.items():
            with self.subTest(label=label):
                digest = digest or (sha256_canonical(manifest) if manifest else None)
                self.assertIn(label, lab_server.serving_manifest_problems(
                    spec, manifest, digest))
                rec = self.failure(self.start, spec, self.host.scenario(),
                                   serving_manifest=manifest,
                                   serving_manifest_sha256=digest)
                self.assertEqual((rec['stage'], rec['findings'], rec['pid']),
                                 ('serving_manifest', ['serving_manifest'], 0))

    def test_an_edited_launcher_or_a_bare_launcher_name_is_refused(self):
        spec = self.host.spec(free_port())
        self.host.write_launcher('exec sleep 31')                  # one byte moved
        self.assertIn('launcher_sha256', lab_server.serving_manifest_problems(
            spec, self.host.manifest, self.host.manifest_sha))
        bare = self.host.spec(free_port(), llama_bin=Path('llama-server'))
        self.assertIn('launcher_not_explicit', lab_server.serving_manifest_problems(
            bare, self.host.manifest, self.host.manifest_sha))


# --------------------------------------------------------------------------- #
# 2. identity: raw per-field checks, then the tokenized whole-object comparison
# --------------------------------------------------------------------------- #
class IdentityTests(ServerCase):

    def test_raw_absolute_path_passes_and_the_tokenized_object_is_compared(self):
        sc = self.host.scenario()
        spec = self.host.spec(8091)
        tok = lab_server.tokenized_props(sc['props'])
        self.assertTrue(tok['model_path'].startswith('<TMP>/'), tok['model_path'])
        self.assertEqual(lab_server.identity_findings(spec, sc['props'], None, tok), [])
        # control: the golden object carrying the ABSOLUTE path is not the golden form
        self.assertEqual(lab_server.identity_findings(spec, sc['props'], None,
                                                      dict(sc['props'])),
                         ['props_mismatch'])

    def test_a_raw_props_that_is_already_tokenized_cannot_be_realpath_checked(self):
        sc = basic_scenario()                        # serves '<HF_CACHE>/...' as model_path
        spec = self.host.spec(8091)
        self.assertIn('model_path', lab_server.identity_findings(
            spec, sc['props'], None, dict(sc['props'])))
        # control: the same object with the real absolute path passes the per-field check
        good = dict(sc['props'], model_path=str(self.host.gguf))
        self.assertEqual(lab_server.identity_findings(spec, good, None, None), [])

    def test_the_realpath_check_refuses_another_file(self):
        other = self.tmp / 'other.gguf'
        other.write_bytes(self.host.gguf.read_bytes())
        props = dict(self.host.scenario()['props'], model_path=str(other))
        self.assertEqual(lab_server.identity_findings(self.host.spec(8091), props),
                         ['model_path'])

    def test_props_sha256_is_the_tokenized_digest(self):
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _srv):
            body = self.start(self.host.spec(port), sc)
            lab_server.stop(body['pid'])
        self.assertEqual(body['props_sha256'],
                         sha256_canonical(lab_server.tokenized_props(sc['props'])))
        self.assertNotEqual(body['props_sha256'], sha256_canonical(sc['props']),
                            'control: the raw object has a different digest')

    def test_a_start_against_an_already_tokenized_props_fails_identity(self):
        sc = basic_scenario()
        golden = {'props': dict(sc['props']),          # already tokenized: nothing to do
                  'generation_settings': golden_generation_settings(sc),
                  'mask': ['seed'], 'float_tolerance': 1e-6}
        with served(self.host, sc) as (port, _srv):
            rec = self.failure(self.start, self.host.spec(port), sc, golden=golden)
        self.assertEqual(rec['stage'], 'identity')
        self.assertIn('model_path', rec['findings'])


# --------------------------------------------------------------------------- #
# 3. smoke: projected onto the closed key sets; missing is a finding, never 0
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data


class SmokeTests(ServerCase):

    def _reply(self, **over) -> dict:
        data = {'model': basic_scenario()['alias'],
                'usage': {'prompt_tokens': 5, 'completion_tokens': 2, 'total_tokens': 7,
                          'prompt_tokens_details': {'cached_tokens': 0}},
                'timings': {'cache_n': 0, 'prompt_n': 5, 'prompt_ms': 1.0, 'predicted_n': 2,
                            'predicted_ms': 3, 'predicted_per_second': 9.0,
                            'prompt_per_second': 1.0},
                '__verbose': {'generation_settings': dict(
                    golden_generation_settings(basic_scenario()), seed=1)}}
        data.update(over)
        return data

    def _attempt(self, data):
        golden = self.golden(self.host.scenario())
        with mock.patch.object(lab_server.requests, 'post', lambda *a, **k: data):
            return lab_server._smoke_attempt('http://127.0.0.1:1', self.host.spec(1),
                                             golden, SAMPLING)

    def test_the_body_is_projected_onto_the_schema_key_sets(self):
        out, findings = self._attempt(_Resp(self._reply()))
        self.assertEqual(findings, [])
        self.assertEqual(set(out['usage']), set(lab_eventlog.USAGE.fields))
        self.assertEqual(set(out['timings']), set(lab_eventlog.TIMINGS.fields))
        self.assertIsInstance(out['timings']['predicted_ms'], float, 'int 3 became 3.0')
        self.assertEqual(out['usage']['cached_tokens'], 0)

    def test_cached_tokens_falls_back_to_tokens_cached(self):
        data = self._reply(usage={'prompt_tokens': 5, 'completion_tokens': 2,
                                  'total_tokens': 7})
        data['__verbose'] = dict(data['__verbose'], tokens_cached=0)
        out, findings = self._attempt(_Resp(data))
        self.assertEqual((findings, out['usage']['cached_tokens']), ([], 0))
        # control: neither source present is a finding, and no zero is invented
        data['__verbose'].pop('tokens_cached')
        out, findings = self._attempt(_Resp(data))
        self.assertIsNone(out)
        self.assertIn('smoke_no_usage', findings)

    def test_a_missing_timings_key_is_smoke_no_usage(self):
        data = self._reply()
        data['timings'] = {k: v for k, v in data['timings'].items() if k != 'predicted_n'}
        out, findings = self._attempt(_Resp(data))
        self.assertIsNone(out)
        self.assertIn('smoke_no_usage', findings)

    def test_transport_and_non_200_are_smoke_transport(self):
        def refuse(*a, **k):
            raise lab_server.requests.ConnectionError('refused')
        golden = self.golden(self.host.scenario())
        with mock.patch.object(lab_server.requests, 'post', refuse):
            self.assertEqual(lab_server._smoke_attempt(
                'http://127.0.0.1:1', self.host.spec(1), golden, SAMPLING),
                (None, ['smoke_transport']))
        self.assertEqual(self._attempt(_Resp({'error': 1}, status=500)),
                         (None, ['smoke_transport']))

    def test_through_start_a_receipt_fault_and_a_no_usage_fault_fail_stage_smoke(self):
        for fault, finding in (({'do': 'receipt', 'set': {'temperature': 0.9}},
                                'generation_settings_value'),
                               ({'do': 'no_usage'}, 'smoke_no_usage'),
                               ({'do': 'http', 'status': 500}, 'smoke_transport')):
            with self.subTest(finding=finding):
                sc = self.host.scenario()
                sc['faults'] = [dict(fault, match={'kind': 'smoke'})]
                with served(self.host, sc) as (port, _srv):
                    rec = self.failure(self.start, self.host.spec(port), sc)
                self.assertEqual(rec['stage'], 'smoke')
                self.assertIn(finding, rec['findings'])
                self.assertIsNotNone(rec['props_sha256'], 'identity had passed')

    def test_the_receipt_codes_agree_with_lab_client(self):
        self.assertEqual(lab_server.RECEIPT_FINDINGS, lab_client.RECEIPT_FINDINGS)


# --------------------------------------------------------------------------- #
# 4 and 5. restart and exit_status
# --------------------------------------------------------------------------- #
class RestartTests(ServerCase):

    def test_restart_refuses_while_the_old_pid_lives_then_compares_with_previous(self):
        sc = self.host.scenario()
        golden = self.golden(sc)
        with served(self.host, sc) as (port, _srv):
            spec = self.host.spec(port)
            first = self.start(spec, sc)
            kw = dict(golden=golden, sampling=dict(SAMPLING), timeout_s=10.0,
                      serving_manifest=self.host.manifest,
                      serving_manifest_sha256=self.host.manifest_sha)
            before = set(lab_server._CHILDREN)
            with self.assertRaises(lab_common.PreflightError):
                lab_server.restart(spec, golden['props'], previous_pid=first['pid'],
                                   previous_props_sha256=first['props_sha256'], **kw)
            self.assertEqual(set(lab_server._CHILDREN), before, 'nothing was launched')
            lab_server.stop(first['pid'])
            with self.assertRaises(lab_common.PreflightError):          # no digest
                lab_server.restart(spec, golden['props'], previous_pid=first['pid'], **kw)
            again = lab_server.restart(spec, golden['props'], previous_pid=first['pid'],
                                       previous_props_sha256=first['props_sha256'],
                                       restart_index=2, **kw)
            lab_server.stop(again['pid'])
            other = lab_server.restart(spec, golden['props'], previous_pid=again['pid'],
                                       previous_props_sha256='3' * 64, **kw)
            lab_server.stop(other['pid'])
        lab_eventlog.validate_event('server_restarted', again)
        self.assertIs(again['props_equal_previous'], True)
        self.assertIs(other['props_equal_previous'], False,
                      'control: a different previous digest is not "equal"')

    def test_a_failed_restart_records_kind_restart_and_its_index(self):
        sc = self.host.scenario()
        golden = self.golden(sc)
        sc['_shim'] = {'never_listen': True}
        with served(self.host, sc) as (port, _srv):
            rec = self.failure(lab_server.restart, self.host.spec(port), golden['props'],
                               previous_pid=1 << 22,
                               previous_props_sha256='4' * 64, golden=golden,
                               sampling=dict(SAMPLING), timeout_s=0.5,
                               serving_manifest=self.host.manifest,
                               serving_manifest_sha256=self.host.manifest_sha,
                               restart_index=3)
        self.assertEqual((rec['kind'], rec['restart_index'], rec['stage']),
                         ('restart', 3, 'health'))

    def test_exit_status(self):
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _srv):
            body = self.start(self.host.spec(port), sc)
        self.assertIsNone(lab_server.exit_status(body['pid']))
        os.killpg(body['pid'], signal.SIGKILL)                  # dies behind our back
        deadline = time.monotonic() + 5
        while lab_server.exit_status(body['pid']) is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(lab_server.exit_status(body['pid']), -signal.SIGKILL)
        lab_server.stop(body['pid'])
        self.assertEqual(lab_server.exit_status(body['pid']), -signal.SIGKILL,
                         'still answered after stop reaped it')
        with self.assertRaises(lab_common.LabError):
            lab_server.exit_status(1 << 22)                     # never started here


# --------------------------------------------------------------------------- #
# 6. trial mode refuses a start that cannot compare
# --------------------------------------------------------------------------- #
class TrialModeTests(ServerCase):

    def test_trial_mode_refuses_without_golden_or_sampling(self):
        spec = self.host.spec(free_port())
        base = dict(serving_manifest=self.host.manifest,
                    serving_manifest_sha256=self.host.manifest_sha)
        golden = self.golden(self.host.scenario())
        for missing in ('golden_props', 'golden', 'sampling'):
            with self.subTest(missing=missing):
                kw = dict(base, golden_props=golden['props'], golden=golden,
                          sampling=dict(SAMPLING))
                kw[missing] = None
                before = dict(lab_server._CHILDREN)
                with self.assertRaises(lab_common.PreflightError):
                    lab_server.start(spec, **kw)
                self.assertEqual(dict(lab_server._CHILDREN), before)
        self.assertFalse((self.tmp / 'logs' / 'llama.log').exists(), 'nothing launched')

    def test_control_capture_mode_may_omit_them_and_its_body_is_not_a_start(self):
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _srv):
            body = lab_server.start(self.host.spec(port), mode='capture', timeout_s=10.0,
                                    serving_manifest=self.host.manifest,
                                    serving_manifest_sha256=self.host.manifest_sha)
            lab_server.stop(body['pid'])
        self.assertIsNone(body['props_matches_golden'])
        self.assertIsNone(body['smoke'])
        self.assertEqual(body['props_tokenized'], lab_server.tokenized_props(sc['props']))
        with self.assertRaises(lab_common.SchemaError):
            lab_eventlog.validate_event('server_started', body)


# --------------------------------------------------------------------------- #
# EB1 fix (reviewers 1 and 2): the listener must be the child; malformed answers are
# recorded failures; the manifest build string; no copied digest in trial mode
# --------------------------------------------------------------------------- #
class ForeignListenerTests(ServerCase):
    """Reviewer 1 finding 6 / reviewer 2 finding 1: ``lab_server.start`` used to take
    ``/health``, ``/props`` and the smoke from WHATEVER listened on the frozen port, and
    returned a success-valued body naming a launched pid that never served."""

    def test_a_foreign_listener_is_never_taken_as_the_childs_health(self):
        sc = self.host.scenario()
        never = dict(sc, _shim={'never_listen': True})     # the child never binds
        with served(self.host, never) as (port, _unused):
            with mock_server(sc, port=port):                 # someone ELSE answers there
                self.assertTrue(lab_server.health(self.host.spec(port).base_url)['ok'],
                                'the foreign listener answers /health 200')
                rec = self.failure(self.start, self.host.spec(port), sc, timeout_s=1.5)
        self.assertEqual((rec['stage'], rec['findings']), ('health', ['health_timeout']))
        self.assertIsNone(rec['props_sha256'], 'no /props of the foreign process recorded')

    def test_a_child_that_cannot_bind_a_held_port_is_process_exited(self):
        """The reviewer's repro: a launch that never binds and exits 7, beside a listener."""
        self.host.write_launcher('sleep 1.0; exit 7')
        self.host.manifest['launcher_sha256'] = sha256_file(self.host.launcher)
        sc = self.host.scenario()
        with mock_server(sc) as (port, _srv):
            rec = self.failure(self.start, self.host.spec(port), sc, timeout_s=10.0)
        self.assertEqual((rec['stage'], rec['findings'], rec['returncode']),
                         ('launch', ['process_exited'], 7))

    def test_control_the_child_as_the_ports_only_listener_is_accepted(self):
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _unused):
            body = self.start(self.host.spec(port), sc)
            try:
                self.assertEqual(lab_server.listening_pids(port), {body['pid']})
            finally:
                lab_server.stop(body['pid'])
        self.assertIs(body['props_matches_golden'], True)


class _BadResp:
    def __init__(self, data):
        self._data, self.status_code = data, 200

    def json(self):
        return self._data


class MalformedAnswerTests(ServerCase):
    """Reviewer 1 finding 7: a malformed HTTP-200 answer used to raise a plain TypeError /
    AttributeError out of ``lab_server.start``; it is now a recorded failure of its stage,
    and the child is stopped either way."""

    def test_a_models_listing_that_is_not_a_list_is_the_models_endpoint_finding(self):
        sc = self.host.scenario()
        real_probe = lab_server.probe

        def bad_probe(base_url, **kw):
            got = real_probe(base_url, **kw)
            return dict(got, models={'data': 5})
        with served(self.host, sc) as (port, _unused), \
                mock.patch.object(lab_server, 'probe', bad_probe):
            rec = self.failure(self.start, self.host.spec(port), sc)
        self.assertEqual((rec['stage'], rec['findings']), ('identity', ['models_endpoint']))
        self.assertIsNotNone(rec['returncode'], 'the child was stopped')
        # control: the pure check on the well-formed listing finds nothing
        spec = self.host.spec(port)
        self.assertNotIn('models_endpoint', lab_server.identity_findings(
            spec, sc['props'], {'data': [{'id': spec.alias}]}))

    def test_a_smoke_whose_timings_is_not_an_object_is_a_smoke_failure(self):
        golden = self.golden(self.host.scenario())
        data = {'model': basic_scenario()['alias'],
                'usage': {'prompt_tokens': 5, 'completion_tokens': 2, 'total_tokens': 7,
                          'prompt_tokens_details': {'cached_tokens': 0}},
                'timings': [1],
                '__verbose': {'generation_settings': dict(
                    golden_generation_settings(basic_scenario()), seed=1)}}
        with mock.patch.object(lab_server.requests, 'post', lambda *a, **k: _BadResp(data)):
            out, findings = lab_server._smoke_attempt('http://127.0.0.1:1',
                                                      self.host.spec(1), golden, SAMPLING)
        self.assertIsNone(out)
        self.assertIn('smoke_no_usage', findings)
        self.assertIn('cache_n_nonzero', findings)
        # and through start: a recorded smoke failure, the child stopped
        sc = self.host.scenario()
        with served(self.host, sc) as (port, _unused), \
                mock.patch.object(lab_server.requests, 'post',
                                  lambda *a, **k: _BadResp(data)):
            rec = self.failure(self.start, self.host.spec(port), sc)
        self.assertEqual(rec['stage'], 'smoke')
        self.assertIsNotNone(rec['returncode'])

    def test_an_unanticipated_exception_is_a_recorded_failure_of_its_stage(self):
        sc = self.host.scenario()
        golden = self.golden(sc)

        def boom(props):
            raise RuntimeError('a check this function did not model')
        with served(self.host, sc) as (port, _unused), \
                mock.patch.object(lab_server, 'tokenized_props', boom):
            rec = self.failure(self.start, self.host.spec(port), sc, golden=golden)
        self.assertEqual((rec['stage'], rec['findings']), ('identity', ['props_mismatch']))
        self.assertGreater(rec['pid'], 0)
        self.assertEqual(lab_server.exit_status(rec['pid']), rec['returncode'])
        self.assertIsNotNone(rec['returncode'], 'the child was stopped before the raise')

    def test_control_an_interrupt_still_stops_the_child_and_propagates(self):
        class Interrupt(BaseException):
            pass
        sc = self.host.scenario()
        seen: list = []

        def interrupted(base_url, **kw):
            seen.append(max(lab_server._CHILDREN))
            raise Interrupt()
        with served(self.host, sc) as (port, _unused), \
                mock.patch.object(lab_server, 'probe', interrupted):
            with self.assertRaises(Interrupt):
                self.start(self.host.spec(port), sc)
        self.assertEqual(len(seen), 1)
        self.assertNotIn(seen[0], lab_server._CHILDREN, 'stopped and reaped')
        self.assertIsNotNone(lab_server.exit_status(seen[0]))

    def test_health_never_raises_on_a_malformed_slots_listing(self):
        class _R:
            status_code = 200

            def __init__(self, data):
                self._d = data

            def json(self):
                return self._d
        answers = {'/health': _R({}), '/slots': _R([1, 'x', {'is_processing': True}])}

        def get(url, timeout=5.0):
            return answers[url[url.rindex('/'):]]
        with mock.patch.object(lab_server.requests, 'get', get):
            got = lab_server.health('http://127.0.0.1:1')
        self.assertEqual((got['ok'], got['slots_busy']), (True, 1),
                         'only the one object slot that is processing is busy')


class ManifestBuildInfoTests(ServerCase):
    """Reviewer 2 finding 3: the raw ``build_info`` is compared with the manifest's
    ``props_build_info`` -- a check the per-field commit-prefix test does not make."""

    def test_a_build_string_other_than_the_manifests_is_refused(self):
        sc = self.host.scenario()
        other = dict(self.host.manifest, props_build_info='b6001-4fea119d')
        spec = self.host.spec(free_port())
        self.assertEqual(lab_server.serving_manifest_problems(
            spec, other, sha256_canonical(other)), [],
            'the manifest itself re-verifies: the commit prefix is in both strings')
        self.assertNotIn('build_info', lab_server.identity_findings(
            spec, sc['props'], None, None), 'the per-field check alone passes it')
        with served(self.host, sc) as (port, _unused):
            rec = self.failure(self.start, self.host.spec(port), sc,
                               serving_manifest=other,
                               serving_manifest_sha256=sha256_canonical(other))
        self.assertEqual((rec['stage'], rec['findings']), ('identity', ['build_info']))
        # control: the manifest's own string (the fixture's) starts -- test_a_good_start


class CopiedDigestTests(ServerCase):
    """Reviewer 1 finding 9: trial mode may not skip the GGUF recomputation."""

    def test_trial_mode_refuses_a_copied_gguf_digest_and_launches_nothing(self):
        spec = self.host.spec(free_port(), gguf_sha256='f' * 64)
        golden = self.golden(self.host.scenario())
        before = dict(lab_server._CHILDREN)
        with self.assertRaises(lab_common.PreflightError):
            lab_server.start(spec, golden_props=golden['props'], golden=golden,
                             sampling=dict(SAMPLING), recompute_gguf_sha256=False,
                             serving_manifest=self.host.manifest,
                             serving_manifest_sha256=self.host.manifest_sha)
        self.assertEqual(dict(lab_server._CHILDREN), before)
        with self.assertRaises(lab_common.PreflightError):
            lab_server.restart(spec, golden['props'], previous_pid=1 << 22,
                               previous_props_sha256='4' * 64, golden=golden,
                               sampling=dict(SAMPLING), recompute_gguf_sha256=False,
                               serving_manifest=self.host.manifest,
                               serving_manifest_sha256=self.host.manifest_sha)
        self.assertEqual(dict(lab_server._CHILDREN), before)
        # control: recomputing, the wrong digest is observed and refused at stage gguf
        rec = self.failure(lab_server.start, spec, golden_props=golden['props'],
                           golden=golden, sampling=dict(SAMPLING),
                           serving_manifest=self.host.manifest,
                           serving_manifest_sha256=self.host.manifest_sha)
        self.assertEqual((rec['stage'], rec['findings']), ('gguf', ['gguf_sha256']))


# --------------------------------------------------------------------------- #
# the event schema additions
# --------------------------------------------------------------------------- #
class SchemaTests(unittest.TestCase):

    def test_vocabularies_agree_with_the_modules_that_produce_them(self):
        self.assertEqual(set(lab_eventlog.E_SERVER_START_FINDING.enum),
                         set(lab_server.IDENTITY_FINDINGS) | set(lab_client.RECEIPT_FINDINGS)
                         | set(lab_server.START_FINDINGS))
        self.assertEqual(lab_eventlog.E_SERVER_START_STAGE.enum, lab_server.START_STAGES)
        self.assertEqual(set(lab_server.SMOKE_USAGE_KEYS), set(lab_eventlog.USAGE.fields))
        self.assertEqual(set(lab_server.SMOKE_TIMINGS_INT_KEYS
                             + lab_server.SMOKE_TIMINGS_FLOAT_KEYS),
                         set(lab_eventlog.TIMINGS.fields))
        self.assertIn('server_restart_cap', lab_eventlog.E_ABORT_REASON.enum)
        self.assertIn('golden_objects', lab_eventlog.E_PREFLIGHT.enum)
        self.assertIn('server_start_failed', lab_eventlog.TRIAL_ONLY_TYPES)

    def test_the_record_schema_refuses_an_open_vocabulary(self):
        good = {'server_id': 'coder', 'kind': 'start', 'stage': 'identity',
                'findings': ['props_mismatch'], 'pid': 12, 'returncode': -15,
                'argv_sha256': '5' * 64, 'props_sha256': None, 'load_seconds': 1.0,
                'restart_index': 0}
        lab_eventlog.validate_event('server_start_failed', good)
        for key, bad in (('findings', ['it looked wrong']), ('stage', 'warmup'),
                         ('kind', 'reload'), ('returncode', 'unknown')):
            with self.subTest(key=key):
                with self.assertRaises(lab_common.SchemaError):
                    lab_eventlog.validate_event('server_start_failed', dict(good, **{key: bad}))


# --------------------------------------------------------------------------- #
# 7. preflight: golden objects, the serving manifest, runtime overlays
# --------------------------------------------------------------------------- #
class _Tree:
    """The mock freeze tree of dryrun_live_ab (which now deposits golden files and a
    serving manifest) and a context built the way make_context builds one."""

    def __init__(self, trial: str = 'T4') -> None:
        self.root = Path(tempfile.mkdtemp(prefix='eb1_tree_'))
        self.results = self.root / 'results'
        self.work = self.root / 'work'
        self.trial = trial
        self.built = dry.build_mock_freeze(self.results, n_pairs=2, trial=trial)
        self.freeze = self.results / 'freeze'
        self.bundle_sha = self.built['bundle_sha']

    def cfg(self, **rt) -> dict:
        cfg = json.loads((self.freeze / 'config.json').read_text('utf-8'))
        cfg['_runtime'] = dict({
            'results_root': str(self.results), 'work_root': str(self.work),
            'bundle_sha': self.bundle_sha, 'free_disk_floor_gb': 0.0,
            'clock_window_s': 0.01, 'preflight_mode': 'offline_fixture',
            'anchor_mode': 'mock', 'blocking_wait_s': 0.3, 'poll_interval_ms': 0,
            'worktree_check_s': 1e9, 'max_pairs': 2,
            'tasks_path': str(self.freeze / 'tasks.json')}, **rt)
        return cfg

    def ctx(self, **rt):
        return orch.make_context(self.trial, self.cfg(**rt), results_root=self.results,
                                 work_root=self.work, inv=uuid.uuid4().hex)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class PreflightTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tree = _Tree()
        self.addCleanup(self.tree.close)

    def refusal(self, ctx) -> tuple[set, set]:
        with self.assertRaises(lab_common.PreflightError) as caught:
            orch.preflight(ctx)
        drift = list(getattr(caught.exception, 'drift', []))
        for row in drift:                        # every row is writable to the chain
            lab_eventlog.validate_event('preflight_refused',
                                        {'trial': 'T4', 'checks_failed': [],
                                         'drift': [row]})
        return set(str(caught.exception).split(',')), {r['item'] for r in drift}

    def sim(self):
        return mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld)

    def test_control_the_untouched_mock_tree_passes_on_the_simulated_path(self):
        with self.sim():
            self.assertEqual(orch.preflight(self.tree.ctx(sim=True)), [])

    def test_a_missing_edited_unreadable_or_null_golden_file_is_refused(self):
        name = 'golden_props_coder.json'
        cases = {
            'missing': lambda p: p.unlink(),
            'edited': lambda p: p.write_text(json.dumps(dict(
                json.loads(p.read_text('utf-8')), total_slots=9)), encoding='utf-8'),
            'unreadable': lambda p: p.write_text('{not json', encoding='utf-8'),
        }
        for label, damage in cases.items():
            with self.subTest(label=label):
                tree = _Tree()
                try:
                    damage(tree.freeze / name)
                    with self.sim():
                        codes, items = self.refusal(tree.ctx(sim=True))
                    self.assertIn('golden_objects', codes)
                    self.assertIn('golden_props_sha256.coder', items)
                finally:
                    tree.close()
        # null in the configuration
        tree = _Tree()
        try:
            path = tree.freeze / 'config.json'
            cfg = json.loads(path.read_text('utf-8'))
            cfg['receipt']['golden_generation_settings_sha256']['coder'] = None
            path.write_text(lab_common.canonical_json(cfg) + '\n', encoding='utf-8')
            with self.sim():
                codes, items = self.refusal(tree.ctx(sim=True))
            self.assertIn('golden_objects', codes)
            self.assertIn('golden_generation_settings_sha256.coder', items)
        finally:
            tree.close()

    def test_a_golden_props_with_an_absolute_model_path_is_refused(self):
        path = self.tree.freeze / 'golden_props_coder.json'
        obj = json.loads(path.read_text('utf-8'))
        obj['model_path'] = '/Users/someone/weights.gguf'
        path.write_text(lab_common.canonical_json(obj), encoding='utf-8')
        cfg_path = self.tree.freeze / 'config.json'
        cfg = json.loads(cfg_path.read_text('utf-8'))
        cfg['receipt']['golden_props_sha256']['coder'] = sha256_canonical(obj)
        cfg_path.write_text(lab_common.canonical_json(cfg), encoding='utf-8')
        golden, rows = orch.load_golden_objects(self.tree.freeze, cfg, ['coder'])
        self.assertNotIn('coder', golden)
        self.assertEqual([r['item'] for r in rows], ['golden_props_model_path.coder'])

    def test_a_missing_serving_manifest_is_refused(self):
        (self.tree.freeze / orch.SERVING_MANIFEST_FILE).unlink()
        with self.sim():
            codes, items = self.refusal(self.tree.ctx(sim=True))
        self.assertIn('serving_manifest', codes)
        self.assertIn('serving_manifest_sha256', items)

    def test_runtime_golden_and_sim_are_refused_on_the_real_path_only(self):
        override = {'coder': {'props': {}, 'generation_settings': {}, 'mask': ['seed'],
                              'float_tolerance': 1e-6}}
        codes, items = self.refusal(self.tree.ctx(sim=True, golden=override))
        self.assertIn('golden_objects', codes)
        self.assertIn('preflight_rule_failed', codes)
        self.assertIn('runtime_golden_override', items)
        self.assertIn('runtime_sim_without_substitute_world', items)
        # control: with a substitute world installed the same overlay is the harness's own
        with self.sim():
            self.assertEqual(orch.preflight(self.tree.ctx(sim=True, golden=override)), [])

    def test_a_runtime_golden_is_refused_with_a_substitute_world_but_no_sim(self):
        """Reviewer 1 finding 8: a substitute world with ``sim`` unset supervises its servers
        live; the overlay may not replace the frozen golden objects there."""
        override = {'coder': {'props': {'model_path': '<TMP>/x'}, 'generation_settings': {},
                              'mask': ['seed'], 'float_tolerance': 1e-6}}
        with self.sim():
            ctx = self.tree.ctx(golden=override)             # sim NOT set
            self.assertIsNot(ctx.golden, override)
            self.assertNotEqual(ctx.golden.get('coder'), override['coder'],
                                'make_context kept the frozen golden objects')
            codes, items = self.refusal(ctx)
        self.assertIn('golden_objects', codes)
        self.assertIn('runtime_golden_override', items)
        # control: the same overlay with sim set is the simulated harness's own
        with self.sim():
            ctx = self.tree.ctx(sim=True, golden=override)
            self.assertEqual(ctx.golden, override)
            self.assertEqual(orch.preflight(ctx), [])

    def _golden_with_model_path(self, model_path: str) -> None:
        """Rewrite the coder golden /props with ``model_path`` and bind the config to it."""
        path = self.tree.freeze / 'golden_props_coder.json'
        obj = dict(json.loads(path.read_text('utf-8')), model_path=model_path)
        path.write_text(lab_common.canonical_json(obj), encoding='utf-8')
        cfg_path = self.tree.freeze / 'config.json'
        cfg = json.loads(cfg_path.read_text('utf-8'))
        cfg['receipt']['golden_props_sha256']['coder'] = sha256_canonical(obj)
        cfg_path.write_text(lab_common.canonical_json(cfg), encoding='utf-8')

    def test_a_weights_path_the_golden_model_path_does_not_name_is_refused(self):
        """Reviewer 1 finding 3: the golden /props carries tokenize_path(-m); the same file
        under another spelling passes the bytes/SHA check and used to fail only at the
        first start's identity stage, after seq 0."""
        tmp = Path(tempfile.mkdtemp(prefix='eb1_spell_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        blob = tmp / 'blobs' / 'weights.gguf'
        blob.parent.mkdir()
        blob.write_bytes(b'GGUF' + b'\0' * 60)
        link = tmp / 'snapshot' / 'weights.gguf'
        link.parent.mkdir()
        os.symlink(blob, link)
        self._golden_with_model_path(lab_common.tokenize_path(str(link)))
        # the trial names the blob: same bytes, other spelling -> refused before seq 0
        codes, items = self.refusal(self.tree.ctx(gguf_paths={'coder': str(blob)}))
        self.assertIn('golden_objects', codes)
        self.assertIn('golden_model_path.coder', items)
        # control: the spelling the golden object was captured with is not refused for it
        codes, items = self.refusal(self.tree.ctx(gguf_paths={'coder': str(link)}))
        self.assertNotIn('golden_model_path.coder', items)

    def test_a_busy_port_is_refused_before_seq_0(self):
        """Reviewers 1 and 2 (foreign listener): a port another process holds is
        ``port_busy`` before seq 0, never a first start after it."""
        with mock_server(basic_scenario()) as (port, _srv):
            codes, items = self.refusal(self.tree.ctx(ports={'coder': port}))
        self.assertIn('port_busy', codes)
        self.assertIn('port.coder', items)
        # control: a free port is not refused for that reason
        codes, items = self.refusal(self.tree.ctx(ports={'coder': free_port()}))
        self.assertNotIn('port_busy', codes)
        self.assertNotIn('port.coder', items)

    def test_the_real_path_needs_explicit_weights_and_a_verified_launcher(self):
        codes, items = self.refusal(self.tree.ctx())
        self.assertIn('weights_hash', codes)
        self.assertIn('gguf.coder', items)
        self.assertIn('serving_manifest', codes)
        self.assertIn('serving_manifest.coder.launcher_not_explicit', items)

    def test_gguf_drift_rows(self):
        tmp = Path(tempfile.mkdtemp(prefix='eb1_gguf_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        gguf = tmp / 'w.gguf'
        gguf.write_bytes(b'x' * 64)
        spec = Host(tmp).spec(8091, gguf_path=gguf, gguf_bytes=64,
                              gguf_sha256=sha256_file(gguf))
        self.assertIsNone(orch._gguf_drift('coder', spec), 'control: the frozen file')
        for kw in ({'gguf_bytes': 65}, {'gguf_sha256': '6' * 64},
                   {'gguf_path': Path('w.gguf')}):
            with self.subTest(kw=list(kw)):
                bad = lab_server.ServerSpec(**dict(spec.__dict__, **kw))
                self.assertEqual(orch._gguf_drift('coder', bad)['item'], 'gguf.coder')

    def test_each_server_gets_its_own_gguf_path(self):
        tree = _Tree('T3')
        try:
            with self.sim():
                ctx = tree.ctx(sim=True, gguf_paths={'coder': '/a/coder.gguf',
                                                     't3': '/b/t3.gguf'},
                               llama_bin='/c/llama-server')
            self.assertEqual({k: str(v.gguf_path) for k, v in ctx.servers.items()},
                             {'coder': '/a/coder.gguf', 't3': '/b/t3.gguf'})
            self.assertEqual({str(v.llama_bin) for v in ctx.servers.values()},
                             {'/c/llama-server'})
            # control: the retired shared key no longer gives both servers one file
            with self.sim():
                shared = tree.ctx(sim=True, gguf_path='/a/shared.gguf')
            self.assertNotIn('/a/shared.gguf',
                             {str(v.gguf_path) for v in shared.servers.values()})
        finally:
            tree.close()

    def test_observed_members_hash_the_golden_files(self):
        bundle = json.loads((self.tree.freeze / 'freeze_bundle.json').read_text('utf-8'))
        observed = orch.observed_bundle_members(self.tree.freeze, trial='T4', bundle=bundle)
        self.assertEqual(lab_common.verify_bundle_members(bundle, observed), [], 'control')
        path = self.tree.freeze / 'golden_generation_settings_t3.json'
        path.write_text(lab_common.canonical_json(dict(json.loads(path.read_text('utf-8')),
                                                       temperature=0.1)), encoding='utf-8')
        observed = orch.observed_bundle_members(self.tree.freeze, trial='T4', bundle=bundle)
        rows = lab_common.verify_bundle_members(bundle, observed)
        self.assertEqual([r['item'] for r in rows], ['golden_generation_settings_sha256.t3'],
                         'the file moved while the config did not: only a file read sees it')

    def test_trial_started_never_substitutes_a_null_golden_digest(self):
        with self.sim():
            ctx = self.tree.ctx(sim=True)
        ctx.cfg['receipt']['golden_props_sha256']['t3'] = None
        world = orch.World(ctx)
        body = orch.trial_started_body(ctx, world)
        self.assertNotIn('t3', body['golden_props_sha256'])
        self.assertNotIn(sha256_text('t3'), body['golden_props_sha256'].values())
        self.assertIn('coder', body['golden_props_sha256'], 'control: a real digest stays')


# --------------------------------------------------------------------------- #
# 8 and 10. start_servers and run_trial
# --------------------------------------------------------------------------- #
def _record(stage: str, findings: list, server_id: str = 'coder') -> dict:
    return {'server_id': server_id, 'kind': 'start', 'stage': stage, 'findings': findings,
            'pid': 4321, 'returncode': -15, 'argv_sha256': '7' * 64, 'props_sha256': None,
            'load_seconds': 0.5, 'restart_index': 0}


def _started_body(server_id: str, pid: int) -> dict:
    return {'server_id': server_id, 'pid': pid, 'port': 8091, 'argv_sha256': '8' * 64,
            'gguf': {'bytes': 10, 'sha256': '9' * 64}, 'props_sha256': 'a' * 64,
            'props_matches_golden': True, 'total_slots': 2, 'n_ctx': 8192,
            'load_seconds': 1.5,
            'smoke': {'request_sha256': 'b' * 64, 'receipt_matches_golden': True,
                      'usage': {'prompt_tokens': 1, 'completion_tokens': 1,
                                'total_tokens': 2, 'cached_tokens': 0},
                      'timings': {'cache_n': 0, 'prompt_n': 1, 'prompt_ms': 1.0,
                                  'predicted_n': 1, 'predicted_ms': 1.0,
                                  'predicted_per_second': 1.0}, 'ok': True}}


class StartServersTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tree = _Tree('T3')                               # two servers
        self.addCleanup(self.tree.close)
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            self.ctx = self.tree.ctx()                         # real path: sim not set
        self.ctx.paths.mkdirs()
        self.world = orch.World(self.ctx)
        self.world.open_chain(create=True)
        self.addCleanup(lambda: self.world.log.close())
        self.stopped: list = []
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(orch.lab_server, 'stop', lambda pid, **k: (
            self.stopped.append(pid) or {'returncode': -15, 'seconds': 0.1})).start()

    def types(self) -> list:
        return [e['type'] for e in self.world.log.events]

    def test_success_appends_the_returned_body_and_sets_pids(self):
        bodies = {'coder': _started_body('coder', 111), 't3': _started_body('t3', 222)}
        calls = []

        def fake_start(spec, **kw):
            calls.append((spec.server_id, kw['mode'], kw['golden_props'] is not None,
                          kw['serving_manifest'] is not None))
            return bodies[spec.server_id]
        with mock.patch.object(orch.lab_server, 'start', fake_start):
            self.world.start_servers()
        self.assertEqual(self.world.server_pids, {'coder': 111, 't3': 222})
        started = [e['body'] for e in self.world.log.events if e['type'] == 'server_started']
        self.assertEqual(started, [bodies['coder'], bodies['t3']])
        self.assertEqual(calls, [('coder', 'trial', True, True), ('t3', 'trial', True, True)])

    def test_control_a_failed_second_start_stops_the_first_and_aborts(self):
        def fake_start(spec, **kw):
            if spec.server_id == 't3':
                raise lab_common.ServerStartFailed(_record('smoke', ['seed_mismatch'], 't3'))
            return _started_body('coder', 111)
        with mock.patch.object(orch.lab_server, 'start', fake_start):
            with self.assertRaises(lab_common.AbortTrial) as caught:
                self.world.start_servers()
        self.assertEqual(caught.exception.reason, 'receipt_mismatch')
        self.assertEqual(self.types(), ['server_started', 'server_start_failed',
                                        'server_stopped'])
        self.assertEqual(self.stopped, [111])
        self.assertEqual(self.world.server_pids, {})

    def test_the_abort_reason_follows_the_stage(self):
        for stage, reason in orch.START_FAILURE_REASON.items():
            with self.subTest(stage=stage):
                self.world.server_pids.clear()
                with mock.patch.object(orch.lab_server, 'start', side_effect=
                                       lab_common.ServerStartFailed(
                                           _record(stage, ['process_exited']))):
                    with self.assertRaises(lab_common.AbortTrial) as caught:
                        self.world.start_servers()
                self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(set(orch.START_FAILURE_REASON), set(lab_server.START_STAGES))

    def test_an_unexpected_exception_stops_the_first_and_is_a_harness_defect(self):
        """Reviewer 1 finding 7: an exception that is neither ``ServerStartFailed`` nor
        ``PreflightError`` used to escape start_servers after trial_started."""
        def fake_start(spec, **kw):
            if spec.server_id == 't3':
                raise TypeError("'int' object is not iterable")
            return _started_body('coder', 111)
        with mock.patch.object(orch.lab_server, 'start', fake_start):
            with self.assertRaises(lab_common.AbortTrial) as caught:
                self.world.start_servers()
        self.assertEqual(caught.exception.reason, 'harness_defect')
        self.assertEqual(self.types(), ['server_started', 'server_stopped'])
        self.assertEqual(self.stopped, [111])
        self.assertEqual(self.world.server_pids, {})

    def test_the_sim_body_claims_no_comparison(self):
        body = self.world.sim_server_started_body('coder', self.ctx.servers['coder'])
        lab_eventlog.validate_event('server_started', body)
        self.assertTrue(lab_eventlog.is_sim_server_body(body))
        self.assertEqual((body['props_matches_golden'], body['smoke']['receipt_matches_golden'],
                          body['smoke']['ok']), (False, False, False))
        live = _started_body('coder', 111)
        self.assertFalse(lab_eventlog.is_sim_server_body(live), 'control: a live body')
        self.assertFalse(lab_eventlog.is_sim_server_body(dict(body, pid=5)))
        flipped = dict(body, props_matches_golden=True)
        self.assertTrue(lab_eventlog.is_sim_server_body(flipped),
                        'the predicate does not read the comparison flags')
        events = [{'type': 'server_started', 'body': body}]
        self.assertEqual(lab_verify_log.server_start_kind(events), 'simulated')
        self.assertEqual(lab_verify_log.server_start_kind(
            [{'type': 'server_started', 'body': live}]), 'live')
        self.assertEqual(lab_verify_log.server_start_kind(
            events + [{'type': 'server_started', 'body': live}]), 'mixed')

    def test_the_live_placeholder_body_is_gone(self):
        src = (LIVE / 'lab_orchestrator.py').read_text('utf-8')
        self.assertNotIn("sha256_text('mock')", src)
        self.assertNotIn("'props_matches_golden': True", src)
        self.assertNotIn("'receipt_matches_golden': True", src)
        self.assertNotIn('v or sha256_text(k)', src)


class RunTrialTests(unittest.TestCase):
    """The production run_trial path with the start failing: the chain gets trial_aborted
    with the record before it, and nothing escapes."""

    def _run(self, start_effect, trial='T4'):
        tree = _Tree(trial)
        self.addCleanup(tree.close)
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld), \
                mock.patch.object(orch, 'host_quiescence_gate', lambda ctx: None), \
                mock.patch.object(orch.lab_server, 'start', side_effect=start_effect), \
                mock.patch.object(orch.lab_server, 'metrics',
                                  lambda *a, **k: {'ok': False}):
            ctx = tree.ctx()
            status = orch.run_trial(ctx, resume=False)
        events = lab_eventlog.read_chain(tree.results / trial / 'events', trial,
                                         tree.bundle_sha).events
        return status, events

    def test_a_failed_start_ends_in_trial_aborted(self):
        status, events = self._run(lab_common.ServerStartFailed(
            _record('identity', ['props_mismatch'])))
        types = [e['type'] for e in events]
        self.assertEqual(status, 'aborted')
        self.assertEqual(types[0], 'trial_started')
        self.assertIn('server_start_failed', types)
        self.assertNotIn('server_started', types)
        self.assertNotIn('server_stopped', types, 'nothing was started, nothing stopped')
        aborted = [e['body'] for e in events if e['type'] == 'trial_aborted']
        self.assertEqual([b['reason'] for b in aborted], ['server_identity'])

    def test_control_a_refused_start_call_is_a_harness_defect(self):
        status, events = self._run(lab_common.PreflightError('no golden'))
        self.assertEqual(status, 'aborted')
        self.assertNotIn('server_start_failed', [e['type'] for e in events])
        self.assertEqual([e['body']['reason'] for e in events
                          if e['type'] == 'trial_aborted'], ['harness_defect'])

    def test_the_backstop_catches_lab_server_errors_after_trial_started(self):
        for exc, reason in ((lab_common.ReceiptMismatch('seed_mismatch'), 'receipt_mismatch'),
                            (lab_common.ServerIdentityError('alias'), 'server_identity')):
            with self.subTest(reason=reason):
                with mock.patch.object(orch.World, 'start_servers', side_effect=exc):
                    status, events = self._run(None)
                self.assertEqual(status, 'aborted')
                self.assertEqual([e['body']['reason'] for e in events
                                  if e['type'] == 'trial_aborted'], [reason])

    def test_an_unexpected_start_exception_ends_in_trial_aborted(self):
        """Reviewer 1 finding 7: run_trial with the start raising a plain TypeError used to
        RAISE, leaving a chain of ['trial_started'] with no terminal event."""
        status, events = self._run(TypeError("'int' object is not iterable"))
        self.assertEqual(status, 'aborted')
        self.assertEqual([e['body']['reason'] for e in events
                          if e['type'] == 'trial_aborted'], ['harness_defect'])

    def test_an_exception_that_escapes_run_trial_still_stops_the_held_server(self):
        """Reviewer 2 finding 3: the ``finally`` of run_trial stops every server still held
        when an exception escapes; nothing else would."""
        tree = _Tree('T4')
        self.addCleanup(tree.close)
        stopped: list = []

        class Escape(Exception):
            pass

        def scrape(world, point, **kw):
            if point == 'trial_start':
                raise Escape('after the start, before anything else')
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld), \
                mock.patch.object(orch, 'host_quiescence_gate', lambda ctx: None), \
                mock.patch.object(orch.lab_server, 'start',
                                  lambda spec, **kw: _started_body(spec.server_id, 555)), \
                mock.patch.object(orch.lab_server, 'stop', lambda pid, **k: (
                    stopped.append(pid) or {'returncode': -15, 'seconds': 0.1})), \
                mock.patch.object(orch.World, 'scrape', scrape):
            ctx = tree.ctx()
            with self.assertRaises(Escape):
                orch.run_trial(ctx, resume=False)
        self.assertEqual(stopped, [555], 'the held server was stopped on the way out')
        events = lab_eventlog.read_chain(tree.results / 'T4' / 'events', 'T4',
                                         tree.bundle_sha).events
        self.assertEqual([e['type'] for e in events][-1], 'server_started',
                         'control: nothing was written on the way out, and nothing stopped '
                         'it before the escape')


if __name__ == '__main__':
    unittest.main()
