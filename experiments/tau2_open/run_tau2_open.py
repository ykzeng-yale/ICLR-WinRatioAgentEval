"""Orchestrate the tau2 open-model stream: llama-server processes, tau2 batches per arm, raw copies, manifest.

Arms (protocol.md): A = agent qwen2.5-7b-instruct, B = agent qwen3-4b-instruct-2507; the user simulator is
qwen2.5-7b-instruct for BOTH arms and is always served on port 8081 by the 7B server. Arm A's agent uses the same
7B server (8081); arm B's agent uses the Qwen3-4B server on 8082. Routing per role: tau2 forwards --agent-llm-args /
--user-llm-args as litellm.completion kwargs and litellm honours `api_base` per call (verified on tau2 commit
b7ea907 with litellm 1.81.11: a completion with api_base=http://127.0.0.1:8081/v1 reached the llama-server),
so no proxy or multi-model router is needed. Sampling: agent temperature 0.3 in both arms, user simulator 0.0,
sent per request in the llm args (tau2 also forwards its per-trial seed in every request; see protocol section 5). `--hallucination-retries 0` is passed
explicitly so no review model can be invoked.

Sequence per invocation: pre-flight refusals -> servers -> smoke completion per server (non-task prompt) ->
`tau2 run` for arm A then arm B (tau2 executes trial-major in task order; the prespecified ARRIVAL order lives
in design.json and is only used by the analysis) -> copy data/simulations/<save-to>/results.json to
results/tau2_open/raw/ (canonical copy tau2_open_arm<X>.json, overwritten on resume, PLUS a per-invocation copy
tau2_open_arm<X>.<invocation_id>.json that is never overwritten) -> stop the servers this invocation started ->
build episodes.csv when both arms are complete. Resumable: `tau2 run --auto-resume` skips (trial, task, seed)
units already in results.json (tau2 drops INFRASTRUCTURE_ERROR records and re-runs those units; their count per
invocation is recorded in the manifest and the dropped records survive in the per-invocation copies), and an arm
whose raw copy already holds all units is skipped here.

Pre-flight refusals (before any tau2 call): config hash != design.config_hash; task list hash != design; tau2 or
llama.cpp checkout commit != expected (read from .git files, no git command); GGUF size/sha256 mismatch; airline
data file hash mismatch; a running server on a needed port whose alias / context size / slots differ from the
config (unless --accept-running-server, logged); another invocation holds run.lock. The harness starts the
servers it needs itself, with the frozen settings, and stops those it started. Execution never stops early on
outcomes; the run manifest is append-only (one record per invocation).
"""
from __future__ import annotations
import argparse, json, os, shutil, signal, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

from common import (ARMS, RESULTS_DIR, append_jsonl, canonical_json, gguf_record, hardware_info, harness_git_hash, harness_hashes, iso,
                    load_config, now_ts, package_versions, process_rss_bytes, sha256_file)
from design import A, B, check_pairing_invariants, load_design, task_list_sha256, write_design

MANIFEST_SCHEMA = 'tau2_open/run_manifest-v1 (append-only invocations)'
SMOKE_PROMPT = 'Reply with the single word: pong'


# ---------------------------------------------------------------- provenance helpers

def git_head(repo: Path) -> str:
    try:
        head = (repo / '.git' / 'HEAD').read_text().strip()
        if head.startswith('ref:'):
            ref = head.split(' ', 1)[1].strip()
            p = repo / '.git' / ref
            if p.exists():
                return p.read_text().strip()
            packed = repo / '.git' / 'packed-refs'
            if packed.exists():
                for line in packed.read_text().splitlines():
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == ref:
                        return parts[0]
            return 'unknown(ref=%s)' % ref
        return head
    except OSError:
        return 'unknown'


def http_json(url: str, data: dict | None = None, timeout: float = 30.0):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer sk-local'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def server_probe(port: int) -> dict | None:
    """/props and /v1/models of a llama-server on the port, or None when nothing answers."""
    try:
        props = http_json('http://127.0.0.1:%d/props' % port, timeout=5)
        models = http_json('http://127.0.0.1:%d/v1/models' % port, timeout=5)
    except Exception:
        return None
    gen = props.get('default_generation_settings') or {}
    return dict(alias=props.get('model_alias'), model_path=props.get('model_path'), n_ctx=gen.get('n_ctx'), total_slots=props.get('total_slots'),
                build_info=props.get('build_info'), chat_template_caps=props.get('chat_template_caps'),
                model_ids=[m.get('id') for m in models.get('data', [])], meta=[m.get('meta') for m in models.get('data', [])])


def server_command(cfg: dict, alias: str, port: int) -> list:
    m = cfg['models'][alias]
    first = os.path.expanduser(m['gguf_files'][0]['path'])
    return [cfg['llama_server'], '-m', first, '--alias', alias, '--port', str(port), '-c', str(cfg['llama_ctx_size']), '-np', str(cfg['llama_parallel'])] + list(cfg['llama_extra_args'])


class Servers:
    """Start the llama-server processes an invocation needs; stop only those it started."""

    def __init__(self, cfg: dict, results_dir: Path, accept_running: bool = False):
        self.cfg, self.results_dir, self.accept_running = cfg, results_dir, accept_running
        self.started = {}   # port -> Popen
        self.records = {}   # port -> record

    def ensure(self, alias: str, port: int) -> dict:
        if port in self.records:
            return self.records[port]
        probe = server_probe(port)
        rec = dict(alias=alias, port=port, command=None, pid=None, reused=False, started_at=None, probe=None, mismatch=None)
        if probe is not None:
            mism = []
            if probe.get('alias') != alias:
                mism.append('alias %r != %r' % (probe.get('alias'), alias))
            if probe.get('n_ctx') != self.cfg['llama_ctx_size']:
                mism.append('n_ctx %r != %r' % (probe.get('n_ctx'), self.cfg['llama_ctx_size']))
            if probe.get('total_slots') != self.cfg['llama_parallel']:
                mism.append('slots %r != %r' % (probe.get('total_slots'), self.cfg['llama_parallel']))
            exp_path = os.path.realpath(os.path.expanduser(self.cfg['models'][alias]['gguf_files'][0]['path']))
            if probe.get('model_path') and os.path.realpath(probe['model_path']) != exp_path:
                mism.append('model_path %r != expected gguf' % probe.get('model_path'))
            if mism and not self.accept_running:
                raise SystemExit('a server already listens on port %d but does not match the config (%s); stop it or pass --accept-running-server' % (port, '; '.join(mism)))
            rec.update(reused=True, probe=probe, mismatch=mism or None, pids=[p['pid'] for p in process_rss_bytes('--port %d' % port)])
            self.records[port] = rec
            return rec
        cmd = server_command(self.cfg, alias, port)
        logdir = self.results_dir / 'logs'; logdir.mkdir(parents=True, exist_ok=True)
        log = open(logdir / ('llama_server_%d.log' % port), 'a')
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.started[port] = proc
        t0 = time.time()
        while time.time() - t0 < 600:
            if proc.poll() is not None:
                raise SystemExit('llama-server on port %d exited with code %s during start-up (see %s)' % (port, proc.returncode, log.name))
            probe = server_probe(port)
            if probe is not None and probe.get('alias') == alias:
                break
            time.sleep(2.0)
        else:
            raise SystemExit('llama-server on port %d did not become ready within 600 s' % port)
        rec.update(command=cmd, pid=proc.pid, started_at=iso(now_ts()), probe=probe, load_seconds=time.time() - t0)
        self.records[port] = rec
        return rec

    def stop_started(self):
        for port, proc in list(self.started.items()):
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=60)
                except Exception:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except Exception:
                        pass
            self.records[port]['stopped_at'] = iso(now_ts()); self.records[port]['returncode'] = proc.returncode
            del self.started[port]


def smoke_check(alias: str, port: int) -> dict:
    """One tiny non-task completion: records the served model id and whether usage is returned; refuses a mismatch."""
    t0 = time.time()
    try:
        r = http_json('http://127.0.0.1:%d/v1/chat/completions' % port, dict(model=alias, messages=[dict(role='user', content=SMOKE_PROMPT)], temperature=0.0, max_tokens=5), timeout=300)
    except Exception as e:
        raise SystemExit('smoke completion on port %d failed: %s' % (port, e))
    usage = r.get('usage') or {}
    rec = dict(port=port, alias=alias, prompt=SMOKE_PROMPT, response_model=r.get('model'), text=(r['choices'][0]['message'].get('content') or '')[:100],
               usage=dict(prompt_tokens=usage.get('prompt_tokens'), completion_tokens=usage.get('completion_tokens')), call_seconds=time.time() - t0,
               ok=(r.get('model') == alias) and usage.get('completion_tokens') is not None)
    if not rec['ok']:
        raise SystemExit('served model %r / usage %r on port %d does not match alias %r or lacks usage' % (r.get('model'), usage, port, alias))
    return rec


# ---------------------------------------------------------------- tau2

def save_name(arm: str) -> str:
    return 'tau2_open_arm%s' % arm


def agent_llm_args(cfg: dict, arm: str) -> dict:
    return dict(temperature=cfg['agent_temperature'], api_base='http://127.0.0.1:%d/v1' % cfg['arms'][arm]['port'])


def user_llm_args(cfg: dict) -> dict:
    return dict(temperature=cfg['user_temperature'], api_base='http://127.0.0.1:%d/v1' % cfg['user_port'])


def tau2_command(cfg: dict, arm: str) -> list:
    arm_cfg = cfg['arms'][arm]
    return (['uv', 'run', 'tau2', 'run', '--domain', cfg['domain'], '--agent', 'llm_agent', '--agent-llm', 'openai/' + arm_cfg['alias'],
             '--agent-llm-args', json.dumps(agent_llm_args(cfg, arm)), '--user', 'user_simulator', '--user-llm', 'openai/' + cfg['user_alias'],
             '--user-llm-args', json.dumps(user_llm_args(cfg)), '--num-trials', str(cfg['num_trials']), '--task-ids'] + list(cfg['task_ids']) +
            ['--max-steps', str(cfg['max_steps']), '--max-errors', str(cfg['max_errors']), '--max-concurrency', str(cfg['max_concurrency']),
             '--hallucination-retries', str(cfg['hallucination_retries']), '--seed', str(cfg['tau2_seed']), '--save-to', save_name(arm),
             '--auto-resume', '--log-level', 'WARNING'])


def tau2_results_path(cfg: dict, arm: str) -> Path:
    return Path(cfg['tau2_dir']) / 'data' / 'simulations' / save_name(arm) / 'results.json'


def units_done(results_path: Path) -> set:
    if not results_path.exists():
        return set()
    d = json.loads(results_path.read_text())
    return {(str(s['task_id']), int(s.get('trial', 0))) for s in d.get('simulations') or []}


def expected_units(cfg: dict) -> set:
    return {(t, tr) for t in cfg['task_ids'] for tr in range(cfg['num_trials'])}


def count_infra_errors(results_path: Path) -> int:
    if not results_path.exists():
        return 0
    d = json.loads(results_path.read_text())
    return sum((s.get('termination_reason') == 'infrastructure_error') for s in d.get('simulations') or [])


def check_results_info(results_path: Path, cfg: dict, arm: str) -> list:
    """Compare the tau2 info block and the served model ids with the frozen configuration; returns a list of mismatches.

    Checks: agent/user llm names, agent/user llm_args temperature (0.3 / 0.0), max_steps, num_trials, seed, git_commit, the
    per-trial seeds, the served model id (raw_data.model) of every ASSISTANT message (must be the arm's agent alias) and of
    every USER message (must be the user-simulator alias; a single-model llama-server answers with its own alias, so a
    misrouted role is caught here).
    """
    d = json.loads(results_path.read_text()); info = d.get('info') or {}
    mism = []
    if info.get('agent_info', {}).get('llm') != 'openai/' + cfg['arms'][arm]['alias']:
        mism.append('agent llm %r' % info.get('agent_info', {}).get('llm'))
    if info.get('user_info', {}).get('llm') != 'openai/' + cfg['user_alias']:
        mism.append('user llm %r' % info.get('user_info', {}).get('llm'))
    a_t = (info.get('agent_info', {}).get('llm_args') or {}).get('temperature'); u_t = (info.get('user_info', {}).get('llm_args') or {}).get('temperature')
    if a_t != cfg['agent_temperature']:
        mism.append('agent temperature %r != %r' % (a_t, cfg['agent_temperature']))
    if u_t != cfg['user_temperature']:
        mism.append('user temperature %r != %r' % (u_t, cfg['user_temperature']))
    for key, exp in (('max_steps', cfg['max_steps']), ('num_trials', cfg['num_trials']), ('seed', cfg['tau2_seed']), ('git_commit', cfg['tau2_commit_expected'])):
        if info.get(key) != exp:
            mism.append('%s %r != %r' % (key, info.get(key), exp))
    seeds = sorted({int(s['seed']) for s in d.get('simulations') or [] if s.get('seed') is not None})
    if seeds and not set(seeds) <= set(cfg['tau2_trial_seeds_expected']):
        mism.append('trial seeds %r not in expected %r' % (seeds, cfg['tau2_trial_seeds_expected']))
    served = {'assistant': set(), 'user': set()}
    for s in d.get('simulations') or []:
        for m in s.get('messages') or []:
            mdl = (m.get('raw_data') or {}).get('model')
            if mdl and m.get('role') in served:
                served[m['role']].add(mdl)
    if served['assistant'] and served['assistant'] != {cfg['arms'][arm]['alias']}:
        mism.append('served agent models %r != %r' % (sorted(served['assistant']), cfg['arms'][arm]['alias']))
    if served['user'] and served['user'] != {cfg['user_alias']}:
        mism.append('served user-simulator models %r != %r' % (sorted(served['user']), cfg['user_alias']))
    return mism


def store_raw(results_dir: Path, arm: str, src: Path, invocation_id: str) -> dict:
    """Canonical raw copy (overwritten on resume) plus a per-invocation copy that is never overwritten."""
    raw = results_dir / 'raw'; raw.mkdir(parents=True, exist_ok=True)
    dst = raw / (save_name(arm) + '.json')
    inv = raw / ('%s.%s.json' % (save_name(arm), invocation_id))
    if inv.exists():
        raise SystemExit('refusing to overwrite the per-invocation raw copy %s' % inv)
    shutil.copy2(src, inv)
    shutil.copy2(src, dst)
    return dict(raw_copy=str(dst), raw_sha256=sha256_file(dst), raw_bytes=dst.stat().st_size, raw_copy_invocation=str(inv), raw_invocation_sha256=sha256_file(inv))


def run_arm(cfg: dict, arm: str, results_dir: Path, env: dict, invocation_id: str) -> dict:
    cmd = tau2_command(cfg, arm)
    logdir = results_dir / 'logs'; logdir.mkdir(parents=True, exist_ok=True)
    logp = logdir / ('tau2_arm%s.log' % arm)
    rp = tau2_results_path(cfg, arm)
    infra_before = count_infra_errors(rp)  # tau2 --auto-resume drops these records and re-runs the units
    t0 = time.time()
    with open(logp, 'a') as log:
        log.write('\n=== %s\n%s\n' % (iso(now_ts()), ' '.join(cmd))); log.flush()
        proc = subprocess.run(cmd, cwd=cfg['tau2_dir'], env=env, stdout=log, stderr=subprocess.STDOUT)
    done = units_done(rp); missing = sorted(expected_units(cfg) - done)
    rec = dict(arm=arm, command=cmd, returncode=proc.returncode, elapsed_s=time.time() - t0, log=str(logp), results_path=str(rp),
               n_units_done=len(done), n_units_missing=len(missing), missing_units=missing[:10],
               n_infrastructure_error_rerun_on_resume=infra_before, n_infrastructure_error_now=count_infra_errors(rp),
               info_mismatches=check_results_info(rp, cfg, arm) if rp.exists() else ['results.json missing'])
    if rp.exists():
        rec.update(store_raw(results_dir, arm, rp, invocation_id))
    return rec


# ---------------------------------------------------------------- dry run (mock tau2 output, pipeline test only)

def mock_results(cfg: dict, arm: str, tasks: list) -> dict:
    """Deterministic mock results.json in the tau2 schema (never a result)."""
    import numpy as np
    rng = np.random.default_rng(hash_seed(arm))
    p_succ = 0.45 if arm == A else 0.30
    sims = []
    for tr in range(cfg['num_trials']):
        for t in tasks:
            n_calls = int(rng.integers(4, 14)); succ = bool(rng.random() < p_succ)
            msgs = [dict(role='assistant', content='Hi! How can I help you today?', tool_calls=None, turn_idx=0, usage=None, raw_data=None, generation_time_seconds=None)]
            for c in range(n_calls):
                msgs.append(dict(role='user', content='mock user %d' % c, tool_calls=None, turn_idx=len(msgs), usage=dict(completion_tokens=int(rng.integers(10, 60)), prompt_tokens=int(rng.integers(400, 1200))), raw_data=dict(model=cfg['user_alias'])))
                is_tc = rng.random() < (0.45 if arm == A else 0.30)
                base = 60 if arm == A else 40
                msgs.append(dict(role='assistant', content='' if is_tc else 'mock agent %d' % c, tool_calls=[dict(id='c%d' % c, name='get_user_details', arguments={'user_id': 'x'})] if is_tc else None,
                                 turn_idx=len(msgs), usage=dict(completion_tokens=int(rng.integers(base // 2, base * 2)), prompt_tokens=int(rng.integers(4500, 7000))),
                                 raw_data=dict(model=cfg['arms'][arm]['alias']), generation_time_seconds=float(rng.uniform(1, 8))))
                if is_tc:
                    msgs.append(dict(role='tool', content='{"ok": true}', tool_calls=None, turn_idx=len(msgs), usage=None, raw_data=None))
            term = 'user_stop' if rng.random() < 0.85 else 'max_steps'
            sims.append(dict(id=uuid.uuid4().hex, task_id=t, trial=tr, seed=cfg['tau2_trial_seeds_expected'][tr], duration=float(rng.uniform(40, 300)),
                             termination_reason=term, agent_cost=0.0, user_cost=0.0, reward_info=dict(reward=1.0 if succ else 0.0), messages=msgs,
                             start_time=iso(now_ts()), end_time=iso(now_ts())))
    info = dict(git_commit=cfg['tau2_commit_expected'], num_trials=cfg['num_trials'], max_steps=cfg['max_steps'], seed=cfg['tau2_seed'],
                agent_info=dict(implementation='llm_agent', llm='openai/' + cfg['arms'][arm]['alias'], llm_args=agent_llm_args(cfg, arm)),
                user_info=dict(implementation='user_simulator', llm='openai/' + cfg['user_alias'], llm_args=user_llm_args(cfg)), mock=True)
    return dict(timestamp=iso(now_ts()), info=info, tasks=[dict(id=t) for t in tasks], simulations=sims)


def hash_seed(s: str) -> int:
    import hashlib
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------- lock and manifest

class RunLock:
    def __init__(self, results_dir: Path):
        self.path = results_dir / 'run.lock'

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    f.write(json.dumps(dict(pid=os.getpid(), at=iso(now_ts()), argv=sys.argv[1:])))
                return self
            except FileExistsError:
                try:
                    pid = int(json.loads(self.path.read_text()).get('pid', -1))
                except Exception:
                    pid = -1
                alive = False
                if pid > 0:
                    try:
                        os.kill(pid, 0); alive = True
                    except ProcessLookupError:
                        alive = False
                    except PermissionError:
                        alive = True
                if alive:
                    raise SystemExit('another run_tau2_open.py (pid %d) holds %s; refusing a concurrent run' % (pid, self.path))
                self.path.unlink(missing_ok=True)
        raise SystemExit('could not acquire %s' % self.path)

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except OSError:
            pass


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return dict(schema=MANIFEST_SCHEMA, experiment='tau2_open', created_at=iso(now_ts()), invocations=[])
    return json.loads(path.read_text())


def _write_manifest(path: Path, m: dict):
    tmp = path.with_suffix('.json.tmp'); tmp.write_text(json.dumps(m, indent=2, default=str)); os.replace(tmp, path)


def append_invocation(results_dir: Path, record: dict) -> str:
    path = results_dir / 'run_manifest.json'
    m = _load_manifest(path)
    record = dict(record, invocation_id=uuid.uuid4().hex)
    m['invocations'].append(record); _write_manifest(path, m)
    return record['invocation_id']


def complete_invocation(results_dir: Path, invocation_id: str, **fields):
    path = results_dir / 'run_manifest.json'
    m = _load_manifest(path)
    for inv in m['invocations']:
        if inv.get('invocation_id') == invocation_id:
            for k, v in fields.items():
                if k in inv and k != 'status':
                    raise SystemExit('refusing to overwrite manifest field %r of invocation %s' % (k, invocation_id))
                inv[k] = v
            break
    _write_manifest(path, m)


# ---------------------------------------------------------------- pre-flight

def preflight(cfg: dict, design: dict, results_dir: Path, args) -> dict:
    if cfg['_config_hash'] != design['config_hash']:
        raise SystemExit('config hash %s differs from the frozen design config_hash %s' % (cfg['_config_hash'], design['config_hash']))
    if task_list_sha256(cfg) != design['task_list_sha256']:
        raise SystemExit('task list sha256 differs from the frozen design')
    check_pairing_invariants(design, cfg)
    rec = dict(config_hash=cfg['_config_hash'], design_sha256=(results_dir / 'design.sha256').read_text().split()[0], task_list_sha256=design['task_list_sha256'])
    if args.dry_run:
        return rec
    tau2_dir = Path(cfg['tau2_dir'])
    rec['tau2_commit'] = git_head(tau2_dir)
    if rec['tau2_commit'] != cfg['tau2_commit_expected']:
        raise SystemExit('tau2-bench checkout %s != expected %s' % (rec['tau2_commit'], cfg['tau2_commit_expected']))
    rec['llama_cpp_commit'] = git_head(Path(cfg['llama_server']).parents[2])
    if rec['llama_cpp_commit'] != cfg['llama_cpp_commit_expected']:
        raise SystemExit('llama.cpp checkout %s != expected %s' % (rec['llama_cpp_commit'], cfg['llama_cpp_commit_expected']))
    if not Path(cfg['llama_server']).exists():
        raise SystemExit('llama-server binary missing: %s' % cfg['llama_server'])
    rec['airline_data'] = {}
    for name, exp in cfg['airline_data_sha256'].items():
        h = sha256_file(tau2_dir / 'data' / 'tau2' / 'domains' / cfg['domain'] / name)
        rec['airline_data'][name] = h
        if h != exp:
            raise SystemExit('airline data file %s sha256 %s != frozen %s' % (name, h, exp))
    rec['gguf'] = {alias: gguf_record(m, verify_hash=not args.skip_gguf_hash) for alias, m in cfg['models'].items()}
    bad = [a for a, r in rec['gguf'].items() if not r['ok']]
    if bad:
        raise SystemExit('GGUF check failed for %s: %s' % (bad, json.dumps({a: rec['gguf'][a]['files'] for a in bad}, indent=1)))
    return rec


# ---------------------------------------------------------------- main

def run(args) -> dict:
    cfg = load_config(args.config)
    results_dir = Path(args.results_dir)
    with RunLock(results_dir):
        if not (results_dir / 'design.json').exists():
            if args.dry_run:
                print('dry-run: generating design', write_design(results_dir, cfg), flush=True)
            else:
                raise SystemExit('design.json missing: run design.py first (the design must be frozen before outcomes)')
        design = load_design(results_dir)
        pre = preflight(cfg, design, results_dir, args)
        arms = list(ARMS) if args.arm == 'both' else [args.arm]
        env = dict(os.environ)
        env.setdefault('OPENAI_API_KEY', 'sk-local-llama-server')  # litellm requires a key string; the local server ignores it
        env['OPENAI_API_BASE'] = 'http://127.0.0.1:%d/v1' % cfg['user_port']  # fallback only; api_base is set per role in the llm args
        servers = Servers(cfg, results_dir, args.accept_running_server) if not args.dry_run else None
        record = dict(started_at=iso(now_ts()), argv=sys.argv[1:], dry_run=bool(args.dry_run), arms=arms, preflight=pre, config=dict((k, v) for k, v in cfg.items() if not k.startswith('_')),
                      harness_git_hash=harness_git_hash(), harness_file_sha256=harness_hashes(), hardware=hardware_info(), packages=package_versions(),
                      execution_order_note='tau2 executes each arm as a batch, trial-major in task order; the prespecified arrival order/orientation (design.json) is used only by the analysis',
                      tau2_commands={arm: tau2_command(cfg, arm) for arm in arms}, server_commands={arm: server_command(cfg, cfg['arms'][arm]['alias'], cfg['arms'][arm]['port']) for arm in arms},
                      env_note='OPENAI_API_KEY placeholder if unset; OPENAI_API_BASE=user server; per-role api_base and temperature in --agent-llm-args/--user-llm-args',
                      sampling_note=cfg.get('sampling_note'))
        inv_id = append_invocation(results_dir, record)
        status = 'completed'; arm_records = []; server_records = {}; smokes = {}
        t0 = time.time()
        try:
            for arm in arms:
                raw = results_dir / 'raw' / (save_name(arm) + '.json')
                if raw.exists() and units_done(raw) >= expected_units(cfg) and not args.dry_run:
                    arm_records.append(dict(arm=arm, skipped='raw copy already complete', raw_copy=str(raw), raw_sha256=sha256_file(raw)))
                    continue
                if args.dry_run:
                    tasks = cfg['task_ids'][:args.limit_tasks] if args.limit_tasks else cfg['task_ids']
                    tmp = results_dir / 'logs' / ('mock_%s.json' % save_name(arm)); tmp.parent.mkdir(parents=True, exist_ok=True)
                    tmp.write_text(json.dumps(mock_results(cfg, arm, tasks)))
                    rec = dict(arm=arm, mock=True, n_units_done=len(units_done(tmp)), info_mismatches=check_results_info(tmp, cfg, arm))
                    rec.update(store_raw(results_dir, arm, tmp, inv_id)); tmp.unlink()
                    arm_records.append(rec)
                    continue
                for alias, port in ((cfg['user_alias'], cfg['user_port']), (cfg['arms'][arm]['alias'], cfg['arms'][arm]['port'])):
                    server_records[port] = servers.ensure(alias, port)
                    if port not in smokes:
                        smokes[port] = smoke_check(alias, port)
                rss_start = process_rss_bytes('llama-server')
                rec = run_arm(cfg, arm, results_dir, env, inv_id)
                rec.update(server_rss_start=rss_start, server_rss_end=process_rss_bytes('llama-server'))
                arm_records.append(rec)
                if rec['info_mismatches']:
                    status = 'completed with info mismatches'
                if rec['n_units_missing']:
                    status = 'incomplete (re-run to resume)'
            raws = {a: results_dir / 'raw' / (save_name(a) + '.json') for a in ARMS}
            raw_ok = all(p.exists() and (args.dry_run or units_done(p) >= expected_units(cfg)) for p in raws.values())
            if raw_ok:
                import build_episodes
                rows = build_episodes.build(results_dir, cfg)
                record_ep = dict(n_episodes=len(rows), episodes_csv=str(results_dir / 'episodes.csv'))
            else:
                record_ep = dict(n_episodes=None, note='episodes.csv is built when both arms are complete')
        except KeyboardInterrupt:
            status = 'interrupted'
            raise
        finally:
            if servers is not None and not args.keep_servers:
                servers.stop_started()
            complete_invocation(results_dir, inv_id, status=status, finished_at=iso(now_ts()), elapsed_s=time.time() - t0, arm_runs=arm_records,
                                servers=server_records if servers is None else servers.records, smoke_checks=smokes, episodes=locals().get('record_ep'))
    summary = dict(status=status, arms=arm_records, episodes=locals().get('record_ep'))
    print(json.dumps(summary, indent=2, default=str))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=None)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--arm', default='both', choices=('both', 'A', 'B'))
    ap.add_argument('--dry-run', action='store_true', help='mock tau2 output in the tau2 schema; no server, no tau2 call (scratch results dir only)')
    ap.add_argument('--limit-tasks', type=int, default=None, help='dry-run only: first N tasks')
    ap.add_argument('--skip-gguf-hash', action='store_true', help='check GGUF sizes only (sha256 takes ~1 min for 6.8 GB); recorded in the manifest')
    ap.add_argument('--accept-running-server', action='store_true', help='reuse a running server whose alias matches even if n_ctx/slots differ (logged as a deviation)')
    ap.add_argument('--keep-servers', action='store_true', help='do not stop the llama-server processes this invocation started')
    args = ap.parse_args(argv)
    if args.dry_run and Path(args.results_dir).resolve() == RESULTS_DIR.resolve():
        raise SystemExit('refusing a dry run into the primary results directory; use --results-dir results/tau2_open/dryrun')
    if args.limit_tasks and not args.dry_run:
        raise SystemExit('--limit-tasks is for dry runs only; the frozen design runs all tasks')
    run(args)


if __name__ == '__main__':
    main()
