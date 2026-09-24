"""EB1c model-free controls of the REAL production entry path.

Repair contract EB1, step EB1c (session 60, after root's 20:40 NO-GO,
``reviews/prerun_bundle_go_nogo_20260923_2040.md`` item 1: "Verify the real production entry
path with bounded model-free controls before returning it").

What runs:

* **The production entry point, as a subprocess**: ``python lab_orchestrator.py --trial T4
  --config <file> --results <dir> --work <dir> --llama-bin <launcher> --gguf coder=<dummy>``,
  i.e. ``lab_orchestrator.main`` with ``WORLD_FACTORY`` unset -- no ``SimWorld``, no in-process
  substitute: the real preflight (clock window, freeze-bundle members, golden objects, serving
  manifest, supervision config), the real host-quiescence gate (``ps``/``lsof``, read only),
  the real ``lab_server.start`` / ``restart`` / ``stop`` on a real child process, the real
  supervisor, the real worker processes (``lab_worker.main``) and the real verifier CLI.
* **The "llama-server" is** ``eb1c_llama_shim.py`` behind a two-line ``/bin/sh`` launcher: it
  accepts exactly the frozen argv of ``lab_server.server_argv`` and ``exec``s into
  ``lab_mock_server.main`` (unchanged) on the frozen port, serving the scenario of its start
  count.  The launcher and a dummy library beside it are what the temporary serving manifest
  pins; the "weights" are a dummy GGUF whose bytes and SHA-256 are the temporary config's
  ``servers.coder`` values; the mock serves the dummy's ABSOLUTE path as ``model_path``, so
  the realpath check and the tokenization of ``lab_server.tokenized_props`` both run.
* **The anchor** is ``lab_anchor.py --mock-receipt`` (no git, no network), as in the dry runs.

What is substituted, and why (each is recorded in the temporary tree's ``mock_overrides``):

* ``sandbox.host_work_root`` is a directory of the control, and the workers run through
  ``eb1c_worker_entry.py``, which points ``lab_common``'s cached harness configuration at the
  temporary frozen configuration before calling the unmodified ``lab_worker.main``: the repair
  contract forbids touching the main checkout, where the frozen pin's lock file lives.
* ``execution.server_recovery_s`` is 10 (frozen: 180).  It is both the supervised restart's
  ``timeout_s`` and a waiting client's recovery budget; at 180 every control that drains
  attempts whose server is gone (C5, C6, C7b) would wait three minutes per attempt.
  ``episode_hard_cap_s`` is recomputed from its frozen formula with it.  C4b alone also sets
  ``execution.health_poll_s`` to 60 (frozen: 5), so that the periodic poll cannot see its
  between-pairs exit before the pair boundary does.
* The task file (``_runtime.tasks_path``; the CLI has no flag for it) holds the mock roster's
  records mapped by ``lab_data.to_pilot_task``: the worker hands the file's records to the
  pilot unchanged, and the pilot knows no ``mbpp_full`` benchmark (reported, not repaired).
* Every control but C1 runs preflight with ``_runtime.preflight_mode = 'offline_fixture'``
  and a 0.01 s clock window (recorded by preflight as below the protocol window).  C1, the
  positive control, runs the PRODUCTION default (10 s window, no mode overlay).
* The roster is ``dryrun_live_ab``'s mock roster (3 or 5 pairs), so each trial ends at its
  horizon; the frozen ``n_min`` (100) is untouched, so no control can reach a decision.

Every control asserts the exact chain events it must produce, that no success-valued
``server_started`` / ``server_restarted`` body names a process the shim was scripted to fail,
and that nothing outlives the run: no launched server shim, no worker, no process left in the
orchestrator's PROCESS GROUP (``pgrep -g``; the entry point runs as a session and group
leader, so any descendant it left behind is found whatever its name -- EB1 fix, reviewer 2
finding 5: the old "orchestrator pid alive" clause could not fail, because the pid had been
reaped before it was asked), and no listener on the frozen port.  C1 is the negative control
of C2-C11 (the same tree, unmutated, is not refused) and each failure control is the negative
control of C1 (the same entry path does refuse).  :class:`MutationControl` restores the
pre-repair success placeholder: C2's assertions then FAIL -- the refusal C2 observes is
``lab_server.start``'s comparison -- and the verifier's ``server.lifecycle`` FAILs that
placeholder because it hashed the RAW ``/props``.  The verifier does NOT prove more than
that: a fabricated body that copies the golden digest and sets the flags true passes
``verified_start`` (EB1 fix, reviewer 2 finding 2; ``lab_verify_log._check_server_lifecycle``
states the limit and ``tests_eb1_supervision.VerifiedStartScopeTests`` pins it).
``C4bExitBetweenPairs`` and ``C10ResumeStopsTheOrphan`` have the same kind of mutation control
for the pair-boundary exit check EB1c added and for the resume gate the EB1 fix added.

**Run this file ALONE, on a quiescent host** (EB1 fix, reviewer 2 finding 6).  Every control
runs the real host-quiescence gate of protocol 5.7 (``ps`` / ``lsof``) and the real preflight;
another accelerator job, or another suite's servers and workers probed as foreign consumers,
refuses the run before seq 0 with ``preflight_refused(host_not_quiescent)``.  That is the
gate working, not a defect of the path under test, so :meth:`EntryTree.run` fails the control
AT ONCE with that reason (:func:`host_refusal`) instead of letting it fail later on an
assertion that does not name the cause.

Two defects of EB1a/EB1b these controls exposed are repaired in the same change:
``World.supervise_exits`` at IDLE (C6 showed a pair enrolled onto an exited server) and the
golden-digest clause of ``server.lifecycle``/``verified_start`` (the placeholder chain
verified PASS on its flags alone).

Bounded: <= 5 pairs per trial, one subprocess timeout per run, the whole file in a few minutes.
Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import eb1c_llama_shim as shim                                          # noqa: E402
import lab_common                                                       # noqa: E402
import lab_data                                                         # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_hostcheck                                                    # noqa: E402
import lab_mock_server                                                  # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_server                                                       # noqa: E402
import lab_verify_log                                                   # noqa: E402
from lab_common import canonical_json, sha256_canonical, sha256_file, sha256_text  # noqa: E402

PY = sys.executable
LIVE_CFG: dict = json.loads((LIVE / 'config.json').read_text(encoding='utf-8'))
LABSBX: str = lab_common.prescribed_tmpdir(LIVE_CFG)
TRIAL = 'T4'
BUILD_INFO = 'b6000-%s' % str(LIVE_CFG['llama_cpp']['commit'])[:8]
RECOVERY_S = 10
RUN_TIMEOUT_S = 240.0
#: The fault that kills a mock process on its first task call and never on the smoke: the
#: mock's ``exit`` fault is a real ``os._exit`` under ``lab_mock_server.main``.
CRASH_ON_CODE = {'match': {'kind': 'code'}, 'do': 'exit', 'code': 9}

_saved_env: dict = {}


def setUpModule() -> None:
    """Protocol 5.7 item 2: the workers refuse any TMPDIR but the prescribed one, and every
    ``<TMP>`` token (spool paths, the golden ``model_path``) must resolve identically in this
    process, the orchestrator and the workers -- so the module runs under it, as
    ``tests_lab_serving.WorkerTests`` does, and restores the ambient one afterwards."""
    os.makedirs(LABSBX, exist_ok=True)
    _saved_env['TMPDIR'] = os.environ.get('TMPDIR')
    _saved_env['tempdir'] = tempfile.tempdir
    os.environ['TMPDIR'] = LABSBX
    tempfile.tempdir = LABSBX


def tearDownModule() -> None:
    tempfile.tempdir = _saved_env.get('tempdir')
    if _saved_env.get('TMPDIR') is None:
        os.environ.pop('TMPDIR', None)
    else:
        os.environ['TMPDIR'] = _saved_env['TMPDIR']


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return int(s.getsockname()[1])


def pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def pid_command(pid: int) -> str:
    try:
        res = subprocess.run(['ps', '-o', 'command=', '-p', str(int(pid))],
                             capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return ''
    return res.stdout.strip()


def child_env() -> dict:
    """The environment of the orchestrator subprocess: this one (TMPDIR already the
    prescribed one) without any variable preflight refuses as an API credential."""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith(('ANTHROPIC', 'OPENAI')) and k.endswith(('KEY', 'TOKEN')))}
    env['TMPDIR'] = LABSBX
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


# --------------------------------------------------------------------------- #
# the temporary host and freeze tree
# --------------------------------------------------------------------------- #
class EntryTree:
    """One control's world: a temporary host (dummy GGUF, sh launcher of the shim, a dummy
    library, the shim's state directory, a relocated lock root) and a freeze tree built by
    ``dryrun_live_ab.build_mock_freeze`` and then bound to that host."""

    def __init__(self, name: str, *, n_pairs: int = 3, shim_as: str | None = None,
                 trial: str = TRIAL, freeze_kw: dict | None = None) -> None:
        self.name = name
        self.n_pairs = int(n_pairs)
        #: the trial run (T4 unless a control needs two different arms) and the MOCK-ONLY
        #: freeze overrides of ``dryrun_live_ab.build_mock_freeze`` (``n_min``, ``delta``),
        #: recorded by it in the tree's ``mock_overrides`` (tests_eb1_cap_estimand)
        self.trial = str(trial)
        self.freeze_kw = dict(freeze_kw or {})
        self.root = Path(tempfile.mkdtemp(prefix='eb1c_%s_' % name, dir=LABSBX))
        self.results = self.root / 'results'
        self.work = self.root / 'work'
        self.host = self.root / 'host'
        self.bin = self.host / 'bin'
        self.state = self.host / 'shim_state'
        self.lock_root = self.host / 'host_work'
        for d in (self.results, self.work, self.bin, self.state, self.lock_root):
            d.mkdir(parents=True, exist_ok=True)
        self.gguf = self.host / 'weights' / 'coder-dummy.gguf'
        self.gguf.parent.mkdir(parents=True)
        self.gguf.write_bytes(b'GGUF' + (b'eb1c dummy weights, not a model\n' * 32))
        self.launcher = self.bin / 'llama-server'
        self.launcher.write_text(
            "#!/bin/sh\n%s='%s' exec '%s' '%s' \"$@\"\n"
            % (shim.STATE_ENV, self.state, PY, HERE / 'eb1c_llama_shim.py'), encoding='utf-8')
        self.launcher.chmod(0o755)
        self.lib = self.bin / 'libmock.0.dylib'
        self.lib.write_bytes(b'eb1c: not a library, only a digest the manifest pins\n')
        #: the script name a launched shim's command line carries (cleanup, orphan checks)
        self.shim_token = shim_as or 'eb1c_llama_shim'
        if shim_as is not None:
            # the shim under another script name -- C10 gives it a name the host gate's
            # runner list matches (``llama-server.py``: lab_hostcheck.match_consumer reads
            # the dotted token's head), so a surviving shim IS a foreign llama-server to
            # the gate, exactly as a real orphaned llama-server would be
            alias = self.bin / shim_as
            os.symlink(HERE / 'eb1c_llama_shim.py', alias)
            self.launcher.write_text(
                "#!/bin/sh\n%s='%s' exec '%s' '%s' \"$@\"\n"
                % (shim.STATE_ENV, self.state, PY, alias), encoding='utf-8')
        self.port = free_port()
        self.anchor = None
        self.proc: subprocess.Popen | None = None
        self.returncode: int | None = None
        self.stdout = ''

    # -- the frozen objects ----------------------------------------------------
    def base_scenario(self) -> dict:
        """The mock a correct server would be: the RAW ``/props`` with the dummy's absolute
        path, the frozen alias, slots and per-slot context, the manifest's build string."""
        sc = json.loads((LIVE / 'testdata' / 'scenario_basic.json').read_text('utf-8'))
        sc['faults'] = []
        sc['alias'] = str(self.cfg['servers']['coder']['alias'])
        workers = int(self.cfg['execution']['workers'])
        n_ctx = int(orch._arg_value(self.cfg['llama_args'], '-c', 16384)) // workers
        props = dict(sc['props'])
        props.update({'model_alias': sc['alias'], 'model_path': str(self.gguf),
                      'total_slots': workers, 'n_ctx': n_ctx, 'build_info': BUILD_INFO,
                      'slot_prompt_similarity': 0.0})
        props['default_generation_settings'] = dict(props['default_generation_settings'],
                                                    n_ctx=n_ctx)
        sc['props'] = props
        sc['total_slots'] = workers
        sc['tasks'] = [dict(t) for t in self.roster['task_records']]
        return sc

    def golden_generation_settings(self, scenario: dict) -> dict:
        """What the pre-freeze smoke would have captured from this mock under the frozen
        sampling block (the mock echoes the request's sampling keys over its defaults)."""
        sampling = dict(self.cfg['sampling'])
        gen = dict(scenario.get('defaults') or {})
        for key in ('temperature', 'top_p', 'top_k', 'min_p', 'typical_p', 'repeat_penalty',
                    'presence_penalty', 'frequency_penalty', 'mirostat'):
            gen[key] = sampling[key]
        gen['n_predict'] = sampling['max_tokens']
        return gen

    def build(self, scenarios: list[dict] | None = None, *, runtime: dict | None = None,
              production_preflight: bool = False, golden_raw: bool = False,
              execution: dict | None = None) -> 'EntryTree':
        built = dry.build_mock_freeze(self.results, n_pairs=self.n_pairs, trial=self.trial,
                                      **self.freeze_kw)
        self.cfg = cfg = built['cfg']
        self.roster = built['roster']
        self.freeze = Path(built['freeze'])
        good = self.base_scenario()
        self.good_scenario = good
        # -- the host this tree is bound to ------------------------------------------------
        size = self.gguf.stat().st_size
        digest = sha256_file(self.gguf)
        cfg['servers']['coder'].update({'port': self.port, 'bytes': size,
                                        'sha256_expected': digest,
                                        'sha256_recomputed': digest})
        manifest = {'mock': True, 'llama_cpp_commit': str(cfg['llama_cpp']['commit']),
                    'launcher_sha256': sha256_file(self.launcher),
                    'libraries': [{'name': self.lib.name, 'sha256': sha256_file(self.lib)}],
                    'props_build_info': BUILD_INFO}
        (self.freeze / orch.SERVING_MANIFEST_FILE).write_text(
            canonical_json(manifest) + '\n', encoding='utf-8')
        cfg['llama_cpp']['serving_manifest_sha256'] = sha256_canonical(manifest)
        # the golden objects, TOKENIZED by the one rule (lab_server.tokenized_props)
        # (``golden_raw``: C8d's defect -- the RAW object deposited as golden, never tokenized)
        self.golden_props = (dict(good['props']) if golden_raw
                             else lab_server.tokenized_props(good['props']))
        self.golden_gen = self.golden_generation_settings(good)
        for member, obj in (('golden_props_sha256', self.golden_props),
                            ('golden_generation_settings_sha256', self.golden_gen)):
            name = orch.GOLDEN_FILES[member] % 'coder'
            (self.freeze / name).write_text(canonical_json(obj) + '\n', encoding='utf-8')
            cfg['receipt'][member]['coder'] = sha256_canonical(obj)
        # -- everything else from the live configuration, except what is stated -----------
        cfg['sandbox']['profile_sha256'] = LIVE_CFG['sandbox']['profile_sha256']
        cfg['sandbox']['host_work_root'] = str(self.lock_root)
        cfg['execution']['server_recovery_s'] = RECOVERY_S
        cfg['execution'].update(execution or {})
        cfg['execution']['episode_hard_cap_s'] = orch.episode_hard_cap_s(cfg['execution'])
        cfg.setdefault('mock_overrides', {}).update({
            'servers.coder': 'dummy GGUF bytes/sha256 and a free loopback port (EB1c)',
            'sandbox.host_work_root': 'relocated lock root: the main checkout is never '
                                      'touched (repair contract hard rule)',
            'execution.server_recovery_s': RECOVERY_S})
        for key, value in (execution or {}).items():
            cfg['mock_overrides']['execution.%s' % key] = value
        self.golden_sha = cfg['receipt']['golden_props_sha256']['coder']
        (self.freeze / 'config.json').write_text(canonical_json(cfg) + '\n', encoding='utf-8')
        bundle = dry._mock_bundle(self.freeze, cfg, self.roster)
        (self.freeze / 'freeze_bundle.json').write_text(canonical_json(bundle) + '\n',
                                                        encoding='utf-8')
        self.bundle_sha = lab_common.freeze_bundle_sha256(bundle)
        # -- the invocation ----------------------------------------------------------------
        # The worker hands the task file's records to the pilot unchanged, and the pilot's
        # verify.build_program knows 'mbpp' and 'humaneval' only; lab_data.to_pilot_task is
        # the mapping that makes an S2 ('mbpp_full') record runnable.  The mock roster's raw
        # records would make every S2 episode a worker death (ValueError('mbpp_full')) --
        # observed on this entry path and reported, not repaired here (not EB1).
        self.tasks_path = self.work / 'tasks_pilot_shape.json'
        self.tasks_path.write_text(canonical_json(
            [lab_data.to_pilot_task(t) for t in self.roster['task_records']]) + '\n',
            encoding='utf-8')
        rt = {'tasks_path': str(self.tasks_path),
              'worker_cmd': [PY, str(HERE / 'eb1c_worker_entry.py'), '--harness-config',
                             str(self.freeze / 'config.json')]}
        if not production_preflight:
            rt.update({'preflight_mode': 'offline_fixture', 'clock_window_s': 0.01})
        rt.update(runtime or {})
        self.runtime = rt
        self.write_run_config()
        self.set_scenarios(scenarios if scenarios is not None else [good])
        return self

    def write_run_config(self) -> None:
        """``--config``: the frozen configuration with the invocation's ``_runtime`` block
        (``lab_orchestrator.main`` keeps a ``_runtime`` found inside the file)."""
        cfg = json.loads((self.freeze / 'config.json').read_text(encoding='utf-8'))
        cfg['_runtime'] = dict(self.runtime)
        self.run_config = self.work / 'run_config.json'
        self.run_config.write_text(canonical_json(cfg) + '\n', encoding='utf-8')

    def set_scenarios(self, scenarios: list[dict]) -> None:
        self.scenarios = [copy.deepcopy(s) for s in scenarios]
        (self.state / 'scenarios.json').write_text(json.dumps(self.scenarios),
                                                  encoding='utf-8')

    def scenario(self, **props_update) -> dict:
        sc = copy.deepcopy(self.good_scenario)
        sc['props'].update(props_update)
        return sc

    def spec(self) -> lab_server.ServerSpec:
        """The ServerSpec ``lab_orchestrator.make_context`` builds for this tree's coder."""
        sc = self.cfg['servers']['coder']
        return lab_server.ServerSpec(
            server_id='coder', port=self.port, alias=str(sc['alias']), gguf_path=self.gguf,
            gguf_bytes=int(sc['bytes']), gguf_sha256=str(sc['sha256_expected']),
            llama_bin=self.launcher, llama_commit=str(self.cfg['llama_cpp']['commit']),
            args=tuple(str(a) for a in self.cfg['llama_args']),
            log_path=self.work / self.trial / 'logs' / ('llama_%d.log' % self.port),
            n_slots=int(self.cfg['execution']['workers']),
            n_ctx=int(orch._arg_value(self.cfg['llama_args'], '-c', 16384)))

    # -- running -------------------------------------------------------------------------
    def argv(self) -> list[str]:
        return ['--trial', self.trial, '--config', str(self.run_config),
                '--results', str(self.results), '--work', str(self.work),
                '--llama-bin', str(self.launcher), '--gguf', 'coder=%s' % self.gguf]

    def run(self, *, entry: Path | None = None, entry_args: tuple = (), anchor: bool = True,
            timeout_s: float = RUN_TIMEOUT_S, host_refusal_expected: bool = False) -> int:
        """Run the entry point to completion (or kill it at ``timeout_s``) and return its
        exit code.  ``entry`` defaults to ``lab_orchestrator.py`` itself; ``entry_args`` go
        before the orchestrator's own argv (the mutation entry's ``--mutation NAME``).

        Unless ``host_refusal_expected``, a run the host-quiescence gate refused raises
        ``AssertionError`` naming ``host_not_quiescent`` and the offenders' detectors
        (:func:`host_refusal`): the control could not run on this host."""
        if anchor:
            anchor_cfg = json.loads(self.run_config.read_text(encoding='utf-8'))
            self.anchor = dry._start_anchor(self.trial, anchor_cfg, self.results, self.work)
        script = entry or (LIVE / 'lab_orchestrator.py')
        try:
            self.proc = subprocess.Popen([PY, str(script)] + list(entry_args) + self.argv(),
                                         cwd=str(LIVE),
                                         env=child_env(), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, start_new_session=True)
            try:
                out, _ = self.proc.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                with_group_kill(self.proc)
                out, _ = self.proc.communicate(timeout=30)
                self.returncode = None
            else:
                self.returncode = self.proc.returncode
            self.stdout = (out or b'').decode('utf-8', 'replace')
        finally:
            dry._stop_anchor(self.anchor)
        if not host_refusal_expected:
            refused = host_refusal(self.program_chain())
            if refused is not None:
                raise AssertionError(refused)
        return self.returncode

    # -- reading ---------------------------------------------------------------------------
    def chain(self) -> list[dict]:
        events_dir = self.results / self.trial / 'events'
        if not lab_eventlog.segment_paths(events_dir):
            return []
        # the schema checks task uids against the INSTALLED roster (a module global that
        # the last make_context of any test in this process set): read this tree's chain
        # under this tree's roster
        lab_eventlog.load_roster_uids(self.freeze / 'roster.json')
        return list(lab_eventlog.read_chain(events_dir, self.trial, self.bundle_sha).events)

    def program_chain(self) -> list[dict]:
        events_dir = self.results / lab_common.PROGRAM_CHAIN_ID / 'events'
        if not lab_eventlog.segment_paths(events_dir):
            return []
        return list(lab_eventlog.read_chain(events_dir, lab_common.PROGRAM_CHAIN_ID,
                                            self.bundle_sha).events)

    def launches(self) -> list[dict]:
        path = self.state / 'launches.jsonl'
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text('utf-8').splitlines()
                if line.strip()]

    def verify(self) -> dict:
        """The verifier's own CLI (``lab_verify_log --mode full --json``)."""
        out = self.work / 'verify.json'
        res = subprocess.run([PY, str(LIVE / 'lab_verify_log.py'), '--trial', self.trial,
                              '--mode', 'full', '--results', str(self.results),
                              '--work', str(self.work), '--json', str(out)],
                             cwd=str(LIVE), env=child_env(), capture_output=True, text=True,
                             timeout=300, check=False)
        report = json.loads(out.read_text('utf-8'))
        report['_exit'] = res.returncode
        report['_stdout'] = res.stdout
        return report

    def cleanup(self) -> None:
        """Kill anything a failed control left behind, then remove the tree."""
        for row in self.launches():
            if pid_alive(row['pid']) and self.shim_token in pid_command(row['pid']):
                try:
                    os.killpg(int(row['pid']), signal.SIGKILL)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)


def host_refusal(program_events) -> str | None:
    """[pure] A message naming ``host_not_quiescent`` and the offenders' detectors when the
    PROGRAM chain carries the host gate's refusal, ``None`` otherwise (any other refusal is
    the control's own business)."""
    refused = [e for e in program_events if e['type'] == 'preflight_refused'
               and 'host_not_quiescent' in (e['body'].get('checks_failed') or [])]
    if not refused:
        return None
    detectors = sorted({str(f.get('detector')) for e in program_events
                        if e['type'] == 'host_quiescence_refused'
                        for f in (e['body'].get('findings') or [])})
    return ('host_not_quiescent: the real host gate refused this control before seq 0 '
            '(offending detectors %r) -- run tests_eb1_entry alone on a quiescent host'
            % (detectors,))


def group_members(pgid: int) -> set[int] | None:
    """The pids whose process GROUP is ``pgid`` (``pgrep -g``), ``None`` when that could not
    be read.  pgrep's exit 1 with no output is "none"."""
    try:
        res = subprocess.run(['pgrep', '-g', str(int(pgid))], capture_output=True,
                             text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    out = res.stdout.split()
    if res.returncode not in (0, 1) or (res.returncode == 1 and out):
        return None
    return {int(tok) for tok in out}


def with_group_kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass


def types(events) -> list[str]:
    return [e['type'] for e in events]


def of(events, etype: str) -> list[dict]:
    return [e for e in events if e['type'] == etype]


LIFECYCLE = ('server_started', 'server_start_failed', 'server_down', 'server_stopped',
             'server_restarted', 'trial_aborted', 'trial_paused', 'trial_ended')


def lifecycle(events) -> list[tuple]:
    """The lifecycle skeleton of a chain: the server events and the terminal event, with
    the few fields each control pins."""
    out: list[tuple] = []
    for e in events:
        b = e['body']
        t = e['type']
        if t == 'server_start_failed':
            out.append((t, b['kind'], b['stage'], tuple(b['findings'])))
        elif t == 'server_down':
            out.append((t, b['detected_by']))
        elif t == 'trial_aborted':
            out.append((t, b['reason']))
        elif t == 'trial_paused':
            out.append((t, b['reason_code']))
        elif t in LIFECYCLE:
            out.append((t,))
    return out


def lifecycle_findings(t: EntryTree) -> list:
    """Every ``server.lifecycle`` finding on the control's chain and frozen configuration,
    with the tree's frozen arrival order (so the ``completion_record`` recount runs too)."""
    col = lab_verify_log._Collector(trial=t.trial, mode='full')
    cfg = json.loads((t.freeze / 'config.json').read_text(encoding='utf-8'))
    order = json.loads((t.freeze / ('arrival_order_%s.json' % t.trial)).read_text('utf-8'))
    slots = order['pairs'] if isinstance(order, dict) else order
    lab_verify_log._check_server_lifecycle(col, t.chain(), cfg,
                                           [int(a) for s in slots for a in s['arrivals']])
    assert 'server.lifecycle' in col.seen
    return [f for f in col.findings if f.check == 'server.lifecycle']


def lifecycle_rules(t: EntryTree) -> list:
    """The verifier's ``server.lifecycle`` check run directly on the control's chain and
    frozen configuration: the violated rules, ``[]`` when it passes.  (The verifier CLI's
    JSON names findings, not the checks that passed; this shows the check RAN.)  The one
    INFO row -- the restart-cap case label of root's 21:14 ruling -- is not a violation:
    :func:`lifecycle_case` reads it."""
    return [f.detail.get('rule') for f in lifecycle_findings(t) if f.severity != 'INFO']


def lifecycle_case(t: EntryTree) -> str:
    """The verifier's restart-cap case label (``none`` when it wrote none)."""
    rows = [f.detail for f in lifecycle_findings(t)
            if f.severity == 'INFO' and f.detail.get('rule') == 'restart_cap_case']
    return str(rows[0]['case']) if rows else 'none'


# --------------------------------------------------------------------------- #
# the base case: every control's shared assertions
# --------------------------------------------------------------------------- #
class EntryCase(unittest.TestCase):

    n_pairs = 3

    def tree(self, name: str, **kw) -> EntryTree:
        t = EntryTree(name, n_pairs=kw.pop('n_pairs', self.n_pairs),
                      shim_as=kw.pop('shim_as', None))
        self.addCleanup(t.cleanup)
        t.build(**kw)
        return t

    def assertNoOrphans(self, t: EntryTree) -> None:
        """No launched server shim, no worker, nothing in the orchestrator's process group
        and no listener on the frozen port outlives the run."""
        self.assertIsNotNone(t.returncode, 'the entry point had to be killed:\n' + t.stdout)
        for row in t.launches():
            self.assertFalse(pid_alive(row['pid'])
                             and t.shim_token in pid_command(row['pid']),
                             'server shim pid %d survived' % row['pid'])
        for ev in of(t.chain(), 'episode_started'):
            pid = int(ev['body']['worker_pid'])
            self.assertFalse(pid_alive(pid) and 'eb1c_worker_entry' in pid_command(pid),
                             'worker pid %d survived' % pid)
        # the entry point ran as a session and group leader (start_new_session): whatever
        # it left running in its group -- a worker, a helper, the entry itself -- is here
        self.assertEqual(group_members(t.proc.pid), set(),
                         'a process of the orchestrator\'s group outlived the run')
        self.assertEqual(lab_server.listening_pids(t.port), set(),
                         'something still listens on the frozen port')

    def assertNoSuccessForBadLaunch(self, t: EntryTree, good_indices: set[int]) -> None:
        """Every ``server_started`` / ``server_restarted`` body names the pid of a launch
        the shim served a CORRECT scenario to, carries the frozen golden digest as its
        ``props_sha256`` and true comparison flags; no success-valued body exists for a
        process that was scripted to fail."""
        by_pid = {int(r['pid']): r for r in t.launches()}
        for ev in t.chain():
            if ev['type'] not in ('server_started', 'server_restarted'):
                continue
            b = ev['body']
            row = by_pid.get(int(b['pid']))
            self.assertIsNotNone(row, 'a server body names a pid the shim never launched')
            self.assertIn(row['scenario_index'], good_indices,
                          'a success-valued body for a launch scripted to fail: %r' % (b,))
            self.assertEqual(b['props_sha256'], t.golden_sha)
            self.assertIs(b['props_matches_golden'], True)
            self.assertIs(b['smoke']['ok'], True)
            self.assertIs(b['smoke']['receipt_matches_golden'], True)
            self.assertFalse(lab_eventlog.is_sim_server_body(b))


def first_start_refusal_problems(t: EntryTree, *, stage: str, findings: list[str],
                                 reason: str) -> list[str]:
    """What is wrong with a chain that should show a FIRST start refused at ``stage``: the
    exact lifecycle ``server_start_failed(start, stage, findings)`` then
    ``trial_aborted(reason)``, no ``server_started``, no pair enrolled, no episode dispatched,
    and a failure record naming the one launched pid.  ``[]`` when it is exactly that.
    Shared by C2, C3, C7a and the mutation control (which must make it non-empty)."""
    events = t.chain()
    problems: list[str] = []
    want = [('server_start_failed', 'start', stage, tuple(sorted(findings))),
            ('trial_aborted', reason)]
    if lifecycle(events) != want:
        problems.append('lifecycle %r != %r' % (lifecycle(events), want))
    for etype in ('server_started', 'pair_enrolled', 'coin_drawn', 'episode_started'):
        if of(events, etype):
            problems.append('%s present' % etype)
    launches = t.launches()
    failed = of(events, 'server_start_failed')
    if len(launches) != 1:
        problems.append('%d launches' % len(launches))
    elif failed and int(failed[0]['body']['pid']) != int(launches[0]['pid']):
        problems.append('the failure record names another pid')
    if t.returncode != 1:
        problems.append('exit code %r' % (t.returncode,))
    rules = lifecycle_rules(t)
    if rules:
        problems.append('server.lifecycle %r' % (rules,))
    return problems


# --------------------------------------------------------------------------- #
# C1: the positive control
# --------------------------------------------------------------------------- #
class C1PositiveRun(EntryCase):
    """The unmutated tree through the production entry point, with the PRODUCTION preflight
    (no mode overlay, the 10 s clock window): a verified start, three pairs, a verified stop,
    trial_ended, and the verifier's full mode PASS -- including ``server.lifecycle``."""

    def test_c1_positive_run_passes_the_verifier(self):
        t = self.tree('C1', production_preflight=True)
        self.assertEqual(t.run(), 0, t.stdout)
        events = t.chain()
        self.assertEqual(lifecycle(events), [('server_started',), ('server_stopped',),
                                             ('trial_ended',)])
        (launch,) = t.launches()
        self.assertEqual(launch['argv'], lab_server.server_argv(t.spec())[1:],
                         'the shim was launched with the frozen argv, verbatim')
        (started,) = of(events, 'server_started')
        b = started['body']
        self.assertEqual(int(b['pid']), int(launch['pid']))
        self.assertEqual(b['gguf'], {'bytes': t.gguf.stat().st_size,
                                     'sha256': sha256_file(t.gguf)})
        self.assertGreater(b['load_seconds'], 0.0)
        self.assertGreater(b['smoke']['usage']['prompt_tokens'], 0, 'a smoke was served')
        self.assertNoSuccessForBadLaunch(t, {0})
        (stopped,) = of(events, 'server_stopped')
        self.assertEqual(int(stopped['body']['pid']), int(launch['pid']))
        self.assertEqual(len(of(events, 'pair_enrolled')), 3)
        self.assertEqual(len(of(events, 'episode_revealed')), 6)
        self.assertEqual(len(of(events, 'server_health')) > 0, True, 'the supervisor polled')
        (rec,) = of(events, 'usage_reconciliation')
        self.assertEqual((rec['body']['window'], rec['body']['counters_lost'],
                          rec['body']['reconciliation_defect'], rec['body']['residual']),
                         ('trial', False, False, {'prompt': 0, 'predicted': 0}))
        rt = json.loads(t.run_config.read_text('utf-8'))['_runtime']
        self.assertNotIn('preflight_mode', rt, 'C1 runs the production preflight')
        self.assertNotIn('clock_window_s', rt)
        self.assertEqual(lifecycle_rules(t), [])
        # the negative control of every restart-cap case label (root's 21:14 ruling): the
        # cap never bound, nothing is truncated, and the verifier labels no case
        (ended,) = of(events, 'trial_ended')
        comp = ended['body']['completion']
        self.assertEqual((comp['restart_cap_case'], comp['cap_required_seq'],
                          comp['arrivals_total'], comp['arrivals_run'],
                          comp['arrivals_not_run']), ('none', None, 6, 6, 0))
        self.assertEqual(lifecycle_case(t), 'none')
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C2 / C3 / C7a: a FIRST start that must be refused
# --------------------------------------------------------------------------- #
class C2FirstStartIdentity(EntryCase):
    """A first start whose ``/props`` differs from the golden object is refused at the
    identity stage: ``server_start_failed(start, identity)`` and ``trial_aborted(
    server_identity)``, nothing enrolled or dispatched, the launched process stopped."""

    n_pairs = 1

    def run_c2(self, name: str, **props_update) -> EntryTree:
        t = self.tree(name)
        t.set_scenarios([t.scenario(**props_update)])
        t.run()
        return t

    def test_c2a_a_props_field_differs(self):
        t = self.run_c2('C2a', chat_template_sha256=sha256_text('another template'))
        self.assertEqual(first_start_refusal_problems(
            t, stage='identity', findings=['props_mismatch'], reason='server_identity'), [])
        (failed,) = of(t.chain(), 'server_start_failed')
        tok = lab_server.tokenized_props(t.scenarios[0]['props'])
        self.assertEqual(failed['body']['props_sha256'], sha256_canonical(tok))
        self.assertNotEqual(failed['body']['props_sha256'], t.golden_sha)
        self.assertNoSuccessForBadLaunch(t, set())
        self.assertNoOrphans(t)

    def test_c2b_the_server_reports_the_tokenized_path_not_its_absolute_one(self):
        """The golden object holds the TOKENIZED ``model_path``; a server reporting that
        token instead of its absolute path fails the realpath check (``model_path``) and
        cannot be tokenized (``props_mismatch``): tokenization is applied to the raw
        observation, never assumed."""
        t = EntryTree('C2b', n_pairs=1)
        self.addCleanup(t.cleanup)
        t.build()
        t.set_scenarios([t.scenario(model_path=t.golden_props['model_path'])])
        self.assertTrue(t.golden_props['model_path'].startswith('<TMP>/'))
        t.run()
        self.assertEqual(first_start_refusal_problems(
            t, stage='identity', findings=['model_path', 'props_mismatch'],
            reason='server_identity'), [])
        (failed,) = of(t.chain(), 'server_start_failed')
        self.assertIsNone(failed['body']['props_sha256'], 'an untokenizable object has none')
        self.assertNoOrphans(t)

    def test_c2c_an_absolute_path_to_another_copy_of_the_weights(self):
        """Same bytes, different file: the realpath check refuses it and its tokenized form
        is not the golden one."""
        t = EntryTree('C2c', n_pairs=1)
        self.addCleanup(t.cleanup)
        t.build()
        other = t.host / 'elsewhere' / t.gguf.name
        other.parent.mkdir()
        shutil.copyfile(t.gguf, other)
        t.set_scenarios([t.scenario(model_path=str(other))])
        t.run()
        self.assertEqual(first_start_refusal_problems(
            t, stage='identity', findings=['model_path', 'props_mismatch'],
            reason='server_identity'), [])
        self.assertNoOrphans(t)


class C3SmokeReceipt(EntryCase):
    """A smoke whose ``generation_settings`` differ from the golden object is refused at
    the smoke stage: ``server_start_failed(start, smoke)`` and ``trial_aborted(
    receipt_mismatch)``."""

    n_pairs = 1

    def test_c3_smoke_receipt_mismatch(self):
        t = self.tree('C3')
        sc = t.scenario()
        sc['faults'] = [{'match': {'kind': 'smoke'}, 'do': 'receipt',
                         'set': {'temperature': 0.9}}]
        t.set_scenarios([sc])
        t.run()
        self.assertEqual(first_start_refusal_problems(
            t, stage='smoke', findings=['generation_settings_value'],
            reason='receipt_mismatch'), [])
        (failed,) = of(t.chain(), 'server_start_failed')
        self.assertEqual(failed['body']['props_sha256'], t.golden_sha,
                         'identity passed; only the smoke failed')
        self.assertNoSuccessForBadLaunch(t, set())
        self.assertNoOrphans(t)


class C7aNeverHealthyAtFirstStart(EntryCase):
    """A first start that dies before ``/health`` answers: ``server_start_failed(start,
    launch, process_exited)`` with the child's return code and ``trial_aborted(
    infrastructure)`` (protocol 6.4 row 5)."""

    n_pairs = 1

    def test_c7a_first_start_exits_before_healthy(self):
        t = self.tree('C7a')
        sc = t.scenario()
        sc['_shim'] = {'exit_before_listen': 3}
        t.set_scenarios([sc])
        t.run()
        self.assertEqual(first_start_refusal_problems(
            t, stage='launch', findings=['process_exited'], reason='infrastructure'), [])
        (failed,) = of(t.chain(), 'server_start_failed')
        self.assertEqual(failed['body']['returncode'], 3)
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C4 / C5 / C6 / C7b: supervision of a server that dies mid-trial
# --------------------------------------------------------------------------- #
def crash_first(t: EntryTree, then: dict) -> list[dict]:
    """Launch 0 dies at its first task call (after a good smoke); launch 1+ serve ``then``."""
    crash = copy.deepcopy(t.good_scenario)
    crash['faults'] = [dict(CRASH_ON_CODE)]
    return [crash, then]


class C4CrashAndRestart(EntryCase):
    """A server that exits mid-pair is detected (``server_down(exit)``), stopped, restarted
    with the identical argv and verified again (``server_restarted``,
    ``props_equal_previous``), scraped at ``restart``; its in-flight arrivals are revealed
    with ``infra_flag``; the dead process's window is ``counters_lost`` and the restarted
    process's window reconciles with no defect; the verifier PASSes."""

    def test_c4_crash_then_supervised_restart(self):
        t = self.tree('C4')
        t.set_scenarios(crash_first(t, t.good_scenario))
        self.assertEqual(t.run(), 0, t.stdout)
        events = t.chain()
        self.assertEqual(lifecycle(events), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_restarted',), ('server_stopped',), ('trial_ended',)])
        first, second = t.launches()
        self.assertEqual(first['argv'], second['argv'], 'the identical argv')
        (down,) = of(events, 'server_down')
        self.assertEqual(down['body']['returncode'], CRASH_ON_CODE['code'])
        self.assertTrue(down['body']['counters_lost'])
        stopped = of(events, 'server_stopped')
        self.assertEqual([int(s['body']['pid']) for s in stopped],
                         [int(first['pid']), int(second['pid'])])
        (restarted,) = of(events, 'server_restarted')
        (started,) = of(events, 'server_started')
        rb = restarted['body']
        self.assertEqual(int(rb['pid']), int(second['pid']))
        self.assertIs(rb['props_equal_previous'], True)
        self.assertEqual(rb['argv_sha256'], started['body']['argv_sha256'])
        nxt = events[events.index(restarted) + 1]
        self.assertEqual((nxt['type'], nxt['body'].get('point')), ('metrics_scrape', 'restart'))
        self.assertNoSuccessForBadLaunch(t, {0, 1})
        # infra_flag exactly on the arrivals the down found in flight
        inflight = {int(r['arrival']) for r in down['body']['inflight']}
        self.assertTrue(inflight)
        flagged = {int(e['body']['arrival']) for e in of(events, 'episode_revealed')
                   if e['body']['outcome']['infra_flag']}
        self.assertEqual(flagged, inflight)
        # reconciliation: the cut window is lost, the restarted one reconciles exactly
        cut, after = [e['body'] for e in of(events, 'usage_reconciliation')]
        self.assertEqual((cut['window'], cut['counters_lost'], cut['reconciliation_defect'],
                          cut['window_to_seq']),
                         ('restart', True, False, int(down['seq'])))
        self.assertEqual((after['window'], after['window_from_seq'], after['counters_lost'],
                          after['reconciliation_defect'], after['residual']),
                         ('restart', int(restarted['seq']), False, False,
                          {'prompt': 0, 'predicted': 0}))
        self.assertGreater(after['client_usage_sum']['prompt'],
                           rb['smoke']['usage']['prompt_tokens'],
                           'the window holds the smoke AND the responses served after it')
        self.assertEqual(lifecycle_rules(t), [])
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


class C4bExitBetweenPairs(EntryCase):
    """A server that ANSWERED the last call of a pair and then exited (no request in flight)
    is detected at the pair boundary -- ``World.supervise_exits``, added by EB1c -- and
    restarted before the next pair is enrolled: ``server_down(exit)`` with an EMPTY
    ``inflight``, no ``infra_flag`` on any reveal, every ``pair_boundary`` scrape ``ok``.

    ``execution.health_poll_s`` is 60 in this tree (frozen: 5) so that the periodic poll
    cannot see the exit first; the mutation test beside it shows that without the boundary
    check the next pair is enrolled onto the dead process."""

    n_pairs = 2
    POLL = {'health_poll_s': 60}

    def scenarios(self, t: EntryTree) -> list[dict]:
        dies = copy.deepcopy(t.good_scenario)
        dies['_shim'] = {'exit_after_responses': 3, 'exit_code': 9}   # smoke + pair 1
        return [dies, t.good_scenario]

    def test_c4b_exit_between_pairs_is_restarted_before_the_next_pair(self):
        t = self.tree('C4b', execution=self.POLL)
        t.set_scenarios(self.scenarios(t))
        self.assertEqual(t.run(), 0, t.stdout)
        events = t.chain()
        self.assertEqual(lifecycle(events), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_restarted',), ('server_stopped',), ('trial_ended',)])
        (down,) = of(events, 'server_down')
        self.assertEqual((down['body']['inflight'], down['body']['returncode']), ([], 9))
        second_pair = of(events, 'pair_enrolled')[1]
        self.assertLess(events.index(of(events, 'server_restarted')[0]),
                        events.index(second_pair), 'restarted before the next pair')
        self.assertFalse(any(e['body']['outcome']['infra_flag']
                             for e in of(events, 'episode_revealed')))
        boundary = [e for e in of(events, 'metrics_scrape')
                    if e['body']['point'] == 'pair_boundary']
        self.assertTrue(boundary and all(e['body']['ok'] for e in boundary))
        self.assertNoSuccessForBadLaunch(t, {0, 1})
        self.assertEqual(lifecycle_rules(t), [])
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)

    def test_mutation_without_the_boundary_check_enrolls_onto_the_dead_server(self):
        t = self.tree('C4bMUT', execution=self.POLL)
        t.set_scenarios(self.scenarios(t))
        t.run(entry=HERE / 'eb1c_mutant_entry.py',
              entry_args=('--mutation', 'no_boundary_exit_check'))
        events = t.chain()
        second_pair = of(events, 'pair_enrolled')[1]
        before = events[:events.index(second_pair)]
        self.assertEqual(of(before, 'server_down'), [], 'the exit went unseen')
        self.assertEqual(before[-1]['type'], 'metrics_scrape')
        self.assertEqual((before[-1]['body']['point'], before[-1]['body']['ok']),
                         ('pair_boundary', False), 'the scrape failed and the pair came anyway')
        self.assertTrue(of(events[events.index(second_pair):], 'episode_started'),
                        'and was dispatched to the dead process')
        self.assertNoOrphans(t)


class C5RestartComesBackDifferent(EntryCase):
    """The restarted process serves a ``/props`` that differs from the golden object: the
    restart is refused at identity (``server_start_failed(kind=restart)``), nothing new is
    dispatched, the open attempts drain and are revealed, ``trial_aborted(server_identity)``."""

    def test_c5_restart_with_different_props_aborts(self):
        t = self.tree('C5')
        t.set_scenarios(crash_first(
            t, t.scenario(chat_template_sha256=sha256_text('a different build'))))
        self.assertEqual(t.run(), 1, t.stdout)
        events = t.chain()
        self.assertEqual(lifecycle(events), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_start_failed', 'restart', 'identity', ('props_mismatch',)),
            ('trial_aborted', 'server_identity')])
        first, second = t.launches()
        (failed,) = of(events, 'server_start_failed')
        fb = failed['body']
        self.assertEqual((int(fb['pid']), fb['restart_index']), (int(second['pid']), 1))
        self.assertNotEqual(fb['props_sha256'], t.golden_sha)
        self.assertNoSuccessForBadLaunch(t, {0})
        at = events.index(failed)
        self.assertEqual(of(events[at:], 'episode_started'), [], 'no dispatch after it')
        started = {int(e['body']['arrival']) for e in of(events, 'episode_started')}
        revealed = [int(e['body']['arrival']) for e in of(events, 'episode_revealed')]
        self.assertEqual(sorted(revealed), sorted(started), 'every attempt revealed once')
        self.assertEqual(lifecycle_rules(t), [])
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


class C6RestartCap(EntryCase):
    """Every process dies at its first task call.  Three supervised restarts are made; the
    fourth ``server_down`` finds the cap reached: nothing restarts, nothing new is dispatched,
    every open attempt drains and is revealed, ``trial_aborted(server_restart_cap)``; the
    results builder reports it incomplete -- root's 21:14 ruling, case (a): no decision, not a
    null -- and the terminal record counts the arrivals that did not run; the verifier PASSes
    (``cap_abort_iff_required``, ``completion_record``) and labels the case."""

    n_pairs = 5

    def test_c6_fourth_down_aborts_at_the_cap(self):
        t = self.tree('C6')
        crash = copy.deepcopy(t.good_scenario)
        crash['faults'] = [dict(CRASH_ON_CODE)]
        t.set_scenarios([crash])
        self.assertEqual(t.run(), 1, t.stdout)
        events = t.chain()
        skel = lifecycle(events)
        self.assertEqual(skel[-1], ('trial_aborted', 'server_restart_cap'))
        self.assertEqual([s for s in skel if s[0] == 'server_down'], [('server_down', 'exit')] * 4)
        self.assertEqual(len(of(events, 'server_restarted')), 3)
        self.assertEqual(of(events, 'server_start_failed'), [])
        self.assertEqual(skel[:1], [('server_started',)])
        # after the 4th down: its stop, then no restart and no dispatch
        fourth = of(events, 'server_down')[3]
        tail = events[events.index(fourth) + 1:]
        self.assertEqual(tail[0]['type'], 'server_stopped')
        self.assertEqual(of(tail, 'server_restarted') + of(tail, 'episode_started')
                         + of(tail, 'pair_enrolled'), [])
        self.assertEqual(len(t.launches()), 4, 'one start and exactly three restarts')
        boundary = [e for e in of(events, 'metrics_scrape')
                    if e['body']['point'] == 'pair_boundary']
        self.assertTrue(boundary and all(e['body']['ok'] for e in boundary),
                        'no pair was enrolled onto a server whose process had exited')
        enrolled = [a for e in of(events, 'pair_enrolled') for a in e['body']['arrivals']]
        revealed = [int(e['body']['arrival']) for e in of(events, 'episode_revealed')]
        self.assertEqual(sorted(revealed), sorted(int(a) for a in enrolled),
                         'every enrolled arrival revealed exactly once, none replaced')
        self.assertLessEqual(len(of(events, 'pair_enrolled')), t.n_pairs)
        self.assertNoSuccessForBadLaunch(t, {0})
        # root's 21:14 ruling, case (a): the cap bound before any decision -- the trial is
        # incomplete and reports no decision (none could be taken here: n_min is 100; the
        # control that CROSSES during a cap drain is tests_eb1_cap_estimand's case (a)).  The
        # terminal record counts the truncation.
        (aborted,) = of(events, 'trial_aborted')
        comp = aborted['body']['completion']
        self.assertEqual((comp['restart_cap_case'], comp['cap_required_seq'],
                          comp['decision_status'], comp['decision_seq'],
                          comp['follow_up_not_run']),
                         ('before_decision', int(fourth['seq']), 'none', None, None))
        started = {int(e['body']['arrival']) for e in of(events, 'episode_started')}
        self.assertEqual((comp['arrivals_total'], comp['arrivals_run'],
                          comp['arrivals_not_run']),
                         (2 * t.n_pairs, len(started), 2 * t.n_pairs - len(started)))
        self.assertGreater(comp['arrivals_not_run'], 0, 'the cap truncated the trial')
        out = builder.build([TRIAL], t.bundle_sha, results_root=t.results,
                            work_root=t.work, out_dir=t.root / 'derived')
        self.assertEqual(out['trials'][TRIAL]['decision'],
                         builder.RESTART_CAP_INCOMPLETE_LABEL)
        self.assertIs(out['trials'][TRIAL]['reportable'], False)
        self.assertEqual((out['trials'][TRIAL]['restart_cap_case'],
                          out['trials'][TRIAL]['arrivals_not_run']),
                         ('before_decision', comp['arrivals_not_run']))
        decision = json.loads((t.root / 'derived' / TRIAL / 'decision.json').read_text('utf-8'))
        self.assertEqual((decision['primary_result'], decision['reportable'],
                          decision['restart_cap']['case']),
                         (builder.RESTART_CAP_INCOMPLETE_LABEL, False, 'before_decision'))
        self.assertEqual(lifecycle_rules(t), [])
        self.assertEqual(lifecycle_case(t), 'before_decision')
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


class C7bRestartNeverHealthy(EntryCase):
    """The restarted process never answers ``/health``: after ``server_recovery_s`` the
    restart fails at the health stage (``server_start_failed(kind=restart, health,
    health_timeout)``), the open attempts drain, and the trial PAUSES
    ``server_unrecoverable`` (protocol 14.6, P:2789) -- exit code 2."""

    def test_c7b_restart_never_healthy_pauses(self):
        t = self.tree('C7b')
        never = t.scenario()
        never['_shim'] = {'never_listen': True}
        t.set_scenarios(crash_first(t, never))
        self.assertEqual(t.run(), 2, t.stdout)
        events = t.chain()
        self.assertEqual(lifecycle(events), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_start_failed', 'restart', 'health', ('health_timeout',)),
            ('trial_paused', 'server_unrecoverable')])
        first, second = t.launches()
        (failed,) = of(events, 'server_start_failed')
        self.assertEqual(int(failed['body']['pid']), int(second['pid']))
        self.assertGreaterEqual(failed['body']['load_seconds'], RECOVERY_S)
        at = events.index(failed)
        self.assertEqual(of(events[at:], 'episode_started'), [])
        started = {int(e['body']['arrival']) for e in of(events, 'episode_started')}
        revealed = [int(e['body']['arrival']) for e in of(events, 'episode_revealed')]
        self.assertEqual(sorted(revealed), sorted(started))
        self.assertNoSuccessForBadLaunch(t, {0})
        self.assertEqual(lifecycle_rules(t), [], 'answered by the pause; not yet terminal')
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# C8 / C9: refusals before seq 0
# --------------------------------------------------------------------------- #
class PreSeqZeroRefusals(EntryCase):
    """A refusal before seq 0 goes to the PROGRAM chain as ``preflight_refused`` naming its
    closed codes and drift rows; no trial chain exists and nothing was launched."""

    n_pairs = 1

    def refused(self, t: EntryTree) -> dict:
        t.run(anchor=False)
        self.assertEqual(t.returncode, 1, t.stdout)
        self.assertEqual(t.chain(), [], 'no trial chain before seq 0')
        self.assertEqual(t.launches(), [], 'nothing was launched')
        refusals = of(t.program_chain(), 'preflight_refused')
        self.assertEqual(len(refusals), 1)
        body = refusals[0]['body']
        self.assertEqual(body['trial'], TRIAL)
        self.assertNoOrphans(t)
        return body

    def items(self, body: dict) -> set[str]:
        return {str(r['item']) for r in body['drift']}

    # -- C8: the golden objects ----------------------------------------------------
    def test_c8a_null_golden_digest(self):
        t = self.tree('C8a')
        for path in (t.freeze / 'config.json', t.run_config):
            cfg = json.loads(path.read_text('utf-8'))
            cfg['receipt']['golden_props_sha256']['coder'] = None
            path.write_text(canonical_json(cfg) + '\n', encoding='utf-8')
        body = self.refused(t)
        self.assertIn('golden_objects', body['checks_failed'])
        row = next(r for r in body['drift'] if r['item'] == 'golden_props_sha256.coder')
        self.assertEqual(row['expected'], lab_common.MEMBER_ABSENT)

    def test_c8b_missing_golden_file(self):
        t = self.tree('C8b')
        (t.freeze / (orch.GOLDEN_FILES['golden_props_sha256'] % 'coder')).unlink()
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['golden_objects'])
        self.assertIn('golden_props_sha256.coder', self.items(body))

    def test_c8c_mismatched_golden_file(self):
        t = self.tree('C8c')
        path = t.freeze / (orch.GOLDEN_FILES['golden_generation_settings_sha256'] % 'coder')
        obj = json.loads(path.read_text('utf-8'))
        obj['temperature'] = 0.8
        path.write_text(canonical_json(obj) + '\n', encoding='utf-8')
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['golden_objects'])
        self.assertIn('golden_generation_settings_sha256.coder', self.items(body))

    def test_c8d_golden_props_with_an_absolute_model_path(self):
        """A golden ``/props`` deposited RAW (absolute ``model_path``) with a consistent
        digest: protocol 13.2 (P:2586) captures it tokenized, so it could never equal an
        observation; refused before seq 0, not at the first start."""
        t = self.tree('C8d', golden_raw=True)
        self.assertTrue(t.golden_props['model_path'].startswith('/'))
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['golden_objects'])
        self.assertIn('golden_props_model_path.coder', self.items(body))

    def test_c8e_runtime_golden_override_on_the_production_path(self):
        t = self.tree('C8e', runtime={'golden': {'coder': {
            'props': {}, 'generation_settings': {}, 'mask': ['seed'],
            'float_tolerance': 1e-6}}})
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['golden_objects'])
        self.assertIn('runtime_golden_override', self.items(body))

    # -- C9: 'sim' from the configuration file ---------------------------------------
    def test_c9_sim_from_the_config_file_is_refused(self):
        t = self.tree('C9', runtime={'sim': True})
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['preflight_rule_failed'])
        self.assertIn('runtime_sim_without_substitute_world', self.items(body))


# --------------------------------------------------------------------------- #
# C10 / C11 (EB1 fix): the resume gate with a real orphan; a foreign listener
# --------------------------------------------------------------------------- #
class C10ResumeStopsTheOrphan(EntryCase):
    """Reviewer 1 finding 2.  An invocation's process group dies mid-trial (SIGKILL of the
    orchestrator and its workers); its server -- in its own session -- survives, and under
    the name ``llama-server.py`` the REAL host gate identifies it as a llama-server.  The
    resume must pass the real gate (the chain records that pid as this trial's server and it
    still listens on the frozen port: ``chain_orphan_server_pids``), stop it with a durable
    ``server_stopped`` before anything else, start and verify a new server, finish the trial
    and PASS the verifier.  The mutation control restores the pre-fix gate (only the
    orchestrator allowlisted): the same resume is refused ``host_not_quiescent`` naming a
    llama-server, and the orphan is never stopped."""

    n_pairs = 3

    def kill_mid_trial(self, t: EntryTree) -> int:
        """Run the entry point until a pair is dispatched, then SIGKILL its process GROUP
        (the orchestrator and its workers; the server has its own session).  Returns the
        surviving server's pid."""
        anchor = dry._start_anchor(TRIAL, json.loads(t.run_config.read_text('utf-8')),
                                   t.results, t.work)
        log_path = t.work / 'killed_invocation.log'
        dispatched = False
        try:
            with open(log_path, 'wb') as log:
                proc = subprocess.Popen([PY, str(LIVE / 'lab_orchestrator.py')] + t.argv(),
                                        cwd=str(LIVE), env=child_env(), stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    events = t.chain()
                except (lab_common.ChainError, ValueError, OSError):
                    events = []                         # a line mid-write
                if of(events, 'episode_started'):
                    dispatched = True
                    break
                time.sleep(0.1)
            with_group_kill(proc)
            proc.wait(timeout=30)
        finally:
            dry._stop_anchor(anchor)
        output = log_path.read_text('utf-8', 'replace')
        refused = host_refusal(t.program_chain())
        if refused is not None:
            raise AssertionError(refused)
        self.assertTrue(dispatched, 'the first invocation never dispatched (returncode %r):\n%s'
                        % (proc.returncode, output[-3000:]))
        deadline = time.monotonic() + 10
        while group_members(proc.pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertEqual(group_members(proc.pid), set(), 'the killed group is gone')
        (launch,) = t.launches()
        orphan = int(launch['pid'])
        self.assertTrue(pid_alive(orphan), 'the server survived its orchestrator')
        self.assertEqual(lab_server.listening_pids(t.port), {orphan})
        self.assertEqual(lab_hostcheck.match_consumer(pid_command(orphan)), 'llama-server',
                         'the gate reads the orphan as a llama-server')
        types_1 = types(t.chain())
        self.assertIn('server_started', types_1)
        self.assertNotIn('server_stopped', types_1)
        return orphan

    def resume_argv(self, t: EntryTree) -> None:
        base = t.argv
        t.argv = lambda: base() + ['--resume']

    def test_c10_the_resume_passes_the_real_gate_and_stops_the_orphan_first(self):
        t = self.tree('C10', shim_as='llama-server.py')
        orphan = self.kill_mid_trial(t)
        # what the gate sees: the orphan alone is refused; allowlisted it is not
        with self.assertRaises(lab_hostcheck.HostNotQuiescent) as caught:
            lab_hostcheck.preflight_host_quiescent(orch.own_harness_pids())
        self.assertIn(orphan, [int(f['pid']) for f in caught.exception.findings])
        self.resume_argv(t)
        self.assertEqual(t.run(), 0, t.stdout)
        self.assertEqual(of(t.program_chain(), 'preflight_refused'), [])
        events = t.chain()
        self.assertEqual(lifecycle(events), [
            ('server_started',), ('server_stopped',), ('server_started',),
            ('server_stopped',), ('trial_ended',)])
        resumed = [i for i, e in enumerate(events) if e['type'] == 'invocation_started']
        second = events[resumed[0]:]
        stopped = of(second, 'server_stopped')[0]
        self.assertEqual(int(stopped['body']['pid']), orphan, 'the resume stopped the orphan')
        self.assertLess(second.index(stopped), second.index(of(second, 'server_started')[0]))
        first_dispatch = of(second, 'episode_started')
        if first_dispatch:
            self.assertLess(second.index(stopped), second.index(first_dispatch[0]))
        self.assertFalse(pid_alive(orphan) and t.shim_token in pid_command(orphan))
        self.assertEqual(len(t.launches()), 2)
        self.assertNoSuccessForBadLaunch(t, {0})
        self.assertEqual(lifecycle_rules(t), [])
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)

    def test_mutation_the_pre_fix_gate_refuses_the_resume_and_leaves_the_orphan(self):
        t = self.tree('C10MUT', shim_as='llama-server.py')
        orphan = self.kill_mid_trial(t)
        before = len(t.chain())
        self.resume_argv(t)
        t.run(entry=HERE / 'eb1c_mutant_entry.py',
              entry_args=('--mutation', 'gate_without_chain_orphans'),
              anchor=False, host_refusal_expected=True)
        self.assertEqual(t.returncode, 1, t.stdout)
        program = t.program_chain()
        self.assertEqual([e['body']['checks_failed'] for e in of(program, 'preflight_refused')],
                         [['host_not_quiescent']])
        (refusal,) = of(program, 'host_quiescence_refused')
        self.assertIn('llama-server',
                      [f['detector'] for f in refusal['body']['findings']])
        self.assertEqual(len(t.chain()), before, 'the trial chain was not touched')
        self.assertTrue(pid_alive(orphan), 'and the orphan was never stopped')
        os.killpg(orphan, signal.SIGKILL)                  # the operator's manual step
        deadline = time.monotonic() + 10
        while lab_server.listening_pids(t.port) and time.monotonic() < deadline:
            time.sleep(0.1)


class C11ForeignListenerOnThePort(EntryCase):
    """Reviewers 1 and 2 (foreign listener): a process that is not the harness's holds the
    frozen port before the first start.  The run is refused BEFORE seq 0 with ``port_busy``
    (protocol 6.4 row 21) -- nothing launched, no trial chain -- instead of a first start
    that would take the foreign process's answers (pre-fix: a success-valued
    ``server_started`` naming a launched pid that never served, verifier PASS).  C1 is the
    negative control: the same tree with the port free runs."""

    n_pairs = 1

    def test_c11_a_foreign_listener_is_port_busy_before_seq_0(self):
        t = self.tree('C11')
        never = t.scenario()
        never['_shim'] = {'never_listen': True}             # the reviewer's repro
        t.set_scenarios([never])
        srv, port = lab_mock_server.make_server(t.good_scenario, port=t.port)
        thread = threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.01},
                                  daemon=True)
        thread.start()
        try:
            t.run(anchor=False)
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=5)
        self.assertEqual(t.returncode, 1, t.stdout)
        self.assertEqual(t.chain(), [], 'no trial chain before seq 0')
        self.assertEqual(t.launches(), [], 'nothing was launched')
        (refused,) = of(t.program_chain(), 'preflight_refused')
        self.assertEqual(refused['body']['checks_failed'], ['port_busy'])
        self.assertIn('port.coder', {r['item'] for r in refused['body']['drift']})
        self.assertNoOrphans(t)


# --------------------------------------------------------------------------- #
# the mutation control
# --------------------------------------------------------------------------- #
class MutationControl(EntryCase):
    """C2's scenario through ``eb1c_mutant_entry.py``, which restores the pre-repair
    success placeholder in place of ``lab_server.start``.  C2's assertions must now FAIL (a
    ``server_started`` claiming a golden match is appended and the trial dispatches): the
    refusal C2 observes is therefore ``lab_server.start``'s comparison, not an artefact of
    the entry path.  The verifier's ``server.lifecycle`` FAILs this chain too
    (``verified_start``), and for a narrower reason: this placeholder hashed the RAW
    ``/props``, so its ``props_sha256`` is not the frozen golden digest.  A placeholder that
    copied the golden digest would pass the verifier -- it reads no server (reviewer 2
    finding 2; stated in ``lab_verify_log._check_server_lifecycle``)."""

    n_pairs = 1

    def test_mutation_restoring_the_placeholder_defeats_c2_and_fails_the_verifier(self):
        t = self.tree('MUT')
        t.set_scenarios([t.scenario(chat_template_sha256=sha256_text('another template'))])
        t.run(entry=HERE / 'eb1c_mutant_entry.py', entry_args=('--mutation', 'placeholder'))
        problems = first_start_refusal_problems(
            t, stage='identity', findings=['props_mismatch'], reason='server_identity')
        self.assertTrue(problems, 'C2 must not pass under the placeholder')
        events = t.chain()
        (started,) = of(events, 'server_started')
        self.assertIs(started['body']['props_matches_golden'], True, 'the placeholder claim')
        self.assertTrue(of(events, 'episode_started'), 'and the trial dispatched')
        report = t.verify()
        self.assertEqual(report['verdict'], 'FAIL', report['_stdout'])
        rules = [(f['check'], (f.get('detail') or {}).get('rule'))
                 for f in report['findings'] if f['severity'] == 'FAIL']
        self.assertIn(('server.lifecycle', 'verified_start'), rules)
        self.assertEqual(lifecycle_rules(t), ['verified_start'])
        self.assertNoOrphans(t)



# --------------------------------------------------------------------------- #
# pure checks of the fixtures and of the verifier rule the mutation control relies on
# --------------------------------------------------------------------------- #
class ShimArgvTests(unittest.TestCase):
    """The shim knows exactly the frozen argv's vocabulary, and refuses a drifted one."""

    def spec(self) -> lab_server.ServerSpec:
        return lab_server.ServerSpec(
            server_id='coder', port=8091, alias='a', gguf_path=Path('/x/w.gguf'),
            gguf_bytes=1, gguf_sha256='0' * 64, llama_bin=Path('/x/llama-server'),
            llama_commit='4fea119de30f6a923992780f6fd5ccb0bee5d47d', args=(),
            log_path=Path('/x/l.log'), n_slots=2, n_ctx=16384)

    def test_the_vocabulary_is_the_frozen_argv(self):
        argv = lab_server.server_argv(self.spec())[1:]
        flags = {tok for tok in argv if tok.startswith('-') and not tok[1:2].isdigit()}
        self.assertEqual(flags, set(shim.VALUE_FLAGS) | set(shim.BARE_FLAGS))
        parsed = shim.parse_argv(argv)
        self.assertEqual((parsed['--port'], parsed['--alias'], parsed['-m']),
                         ('8091', 'a', '/x/w.gguf'))

    def test_a_drifted_argv_is_refused(self):
        argv = lab_server.server_argv(self.spec())[1:]
        self.assertIsNone(shim.parse_argv(argv + ['--flash-attn']), 'unknown flag')
        self.assertIsNone(shim.parse_argv(argv + ['--port', '1']), 'a flag twice')
        self.assertIsNone(shim.parse_argv(argv[:-1] + ['--log-file']), 'no value')
        self.assertIsNone(shim.parse_argv([]), 'no --port, --alias or -m')
        self.assertIsNotNone(shim.parse_argv(argv), 'control: the frozen argv parses')


class VerifiedStartDigestTests(unittest.TestCase):
    """``server.lifecycle`` / ``verified_start`` (lab_verify_log, extended in EB1c): a live
    body must carry the frozen golden digest, not only true flags."""

    GOLDEN = sha256_text('eb1c golden props')

    def rules(self, props_sha256: str, cfg: dict | None, opened: dict | None = None) -> list:
        body = {'server_id': 'coder', 'pid': 4242, 'props_sha256': props_sha256,
                'gguf': {'bytes': 1, 'sha256': '1' * 64}, 'props_matches_golden': True,
                'smoke': {'request_sha256': '2' * 64, 'receipt_matches_golden': True,
                          'ok': True}}
        events = [{'seq': 1, 'type': 'server_started', 'body': body}]
        if opened is not None:
            events.insert(0, {'seq': 0, 'type': 'trial_started',
                              'body': {'golden_props_sha256': opened}})
        col = lab_verify_log._Collector(trial=TRIAL, mode='full')
        lab_verify_log._check_server_lifecycle(col, events, cfg)
        return [f.detail.get('rule') for f in col.findings if f.check == 'server.lifecycle']

    def cfg(self, value) -> dict:
        return {'receipt': {'golden_props_sha256': {'coder': value}}}

    def test_the_golden_digest_passes(self):
        self.assertEqual(self.rules(self.GOLDEN, self.cfg(self.GOLDEN)), [])

    def test_true_flags_under_another_digest_fail(self):
        self.assertEqual(self.rules(sha256_text('raw /props'), self.cfg(self.GOLDEN)),
                         ['verified_start'])

    def test_an_unreadable_golden_digest_fails_every_live_start(self):
        for cfg in ({}, None, self.cfg(None), self.cfg('not-a-digest')):
            self.assertEqual(self.rules(self.GOLDEN, cfg), ['verified_start'], cfg)

    def test_the_chains_own_trial_started_digest_is_a_source_too(self):
        other = sha256_text('raw /props')
        self.assertEqual(self.rules(self.GOLDEN, {}, {'coder': self.GOLDEN}), [])
        self.assertEqual(self.rules(other, {}, {'coder': self.GOLDEN}), ['verified_start'])
        # both present: the body must match each (a disagreement cannot pass)
        self.assertEqual(self.rules(self.GOLDEN, self.cfg(self.GOLDEN),
                                    {'coder': self.GOLDEN}), [])
        self.assertEqual(self.rules(self.GOLDEN, self.cfg(other), {'coder': self.GOLDEN}),
                         ['verified_start'])


class EntryHelperTests(unittest.TestCase):
    """The two helpers the EB1 fix gave every control, each with its negative control."""

    def test_group_members_finds_a_survivor_of_a_dead_group_leader(self):
        """Reviewer 2 finding 5: the orphan check must be able to FAIL.  A group leader that
        exits leaving a background child behind is found by its group id."""
        leader = subprocess.Popen(['/bin/sh', '-c', 'sleep 30 & exit 0'],
                                  start_new_session=True)
        leader.wait(timeout=10)
        try:
            survivors = group_members(leader.pid)
            self.assertTrue(survivors, 'the survivor is found although its leader is gone')
            self.assertNotIn(leader.pid, survivors)
        finally:
            with_group_kill(leader)
        deadline = time.monotonic() + 5
        while group_members(leader.pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(group_members(leader.pid), set(), 'control: an empty group is empty')

    def test_host_refusal_names_the_gate_and_nothing_else(self):
        """Reviewer 2 finding 6: a control the host gate refused says so."""
        gate = [{'type': 'preflight_refused',
                 'body': {'trial': TRIAL, 'checks_failed': ['host_not_quiescent'],
                          'drift': []}},
                {'type': 'host_quiescence_refused',
                 'body': {'findings': [{'detector': 'llama-server'}]}}]
        message = host_refusal(gate)
        self.assertIn('host_not_quiescent', message)
        self.assertIn('llama-server', message)
        other = [{'type': 'preflight_refused',
                  'body': {'trial': TRIAL, 'checks_failed': ['golden_objects'], 'drift': []}}]
        self.assertIsNone(host_refusal(other), 'control: another refusal is the control\'s')
        self.assertIsNone(host_refusal([]))

if __name__ == '__main__':
    unittest.main()
