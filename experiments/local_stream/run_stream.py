"""Orchestrate the local stream: pass 1 in arrival order, then pass 2, with monitoring.

After each completed pass-1 pair the guarded betting e-processes are updated
(project rule, winstats.betting_log_e_ternary): pair score = hierarchical
comparison B vs A with tiers success > latency_s (rel. tol 0.10) >
completion_tokens (rel. tol 0.10), absorbing rule (lower tiers only if both
succeeded); win e-process H0: NB <= 0; harm e-process H0: NB >= 0; guardrail
e-process for the success difference (B-A) H0: diff <= -0.03; alpha 0.05,
min_n 20 pairs. E-values are logged for every pair to monitor_pass1.csv. The
run never stops early (all arrivals are completed for the fixed-horizon and
shadow analyses) but records first-crossing indices in monitor_state.json.
Resume is idempotent: episodes already present in episodes.jsonl (keyed by
task_id, variant, trial) are skipped.

Pre-flight refusals (all before any episode of the invocation):
  * config hash != design.config_hash, or != any existing episode's config_hash;
  * task list sha256 != design.task_list_sha256;
  * (real model) cached huggingface snapshot revision != config.model_revision_expected
    (files, sizes and sha256 are recorded), or the first completion's `model`
    field does not name the configured model;
  * another invocation holds results_dir/run.lock (pid alive);
  * --only-pass 2 while pass 1 is incomplete for the selected arrivals.
run_manifest.json is append-only: one record per invocation (appended at
start, completed at exit with the summary); earlier records and the top-level
fields are never modified.
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time, uuid
from pathlib import Path

import numpy as np

from common import (RESULTS_DIR, VARIANT_LETTER, append_jsonl, hardware_info, harness_git_hash, harness_hashes, hf_snapshot_record, iso,
                    load_config, now_ts, package_versions, process_rss_bytes, read_jsonl)
from data import load_tasks, task_list_sha256
from design import design_path, load_design, write_design
from agent import MockModel, OpenAICompatModel, run_episode
from sandbox import sandbox_info
from winstats import Tier, betting_log_e_ternary, compare

A, B = 'single_shot', 'self_test_repair'
MANIFEST_SCHEMA = 'local_stream/run_manifest-v2 (append-only invocations)'
SMOKE_PROMPT = 'Reply with the single word: pong'


def tiers_from_config(cfg, tolerance=None, order=None):
    """Tiers from config; tolerance/order overrides are for sensitivity analyses only."""
    spec = {t['name']: t for t in cfg['hierarchy']}
    names = order or [t['name'] for t in cfg['hierarchy']]
    out = []
    for nm in names:
        s = spec[nm]
        tol = s.get('relative_tolerance', 0.0) if (tolerance is None or nm == 'success') else tolerance
        out.append(Tier(nm, bool(s['higher_better']), relative_tolerance=float(tol)))
    return out


def outcome_vector(ep: dict, names) -> list:
    return [float(bool(ep['success'])) if nm == 'success' else float(ep[nm]) for nm in names]


def pair_scores(eps_A: list, eps_B: list, tiers, absorbing: bool = True) -> tuple:
    """B vs A hierarchical scores (+1 = B preferred) and success differences (B-A) for aligned episode lists.

    absorbing=True (frozen rule): non-success tiers are eligible only when both episodes
    succeeded. absorbing=False (H4 sensitivity, resource-first hierarchies): every tier is
    eligible for every pair (no mask).
    """
    names = [t.name for t in tiers]
    XA = np.array([outcome_vector(e, names) for e in eps_A], float).reshape(-1, len(names))
    XB = np.array([outcome_vector(e, names) for e in eps_B], float).reshape(-1, len(names))
    elig = np.ones(XA.shape, bool)
    if absorbing:
        both = (XA[:, names.index('success')] > .5) & (XB[:, names.index('success')] > .5)
        for k, nm in enumerate(names):
            if nm != 'success':
                elig[:, k] = both
    z, tier = compare(XB, XA, tiers, elig)
    dq = (XB[:, names.index('success')] - XA[:, names.index('success')]).astype(int)
    return z.astype(int), tier.astype(int), dq


def monitor_table(z, dq, cfg) -> list:
    alpha, margin, min_n = cfg['alpha'], cfg['success_margin'], cfg['min_n_pairs']
    n = np.arange(1, len(z) + 1)
    pos = np.cumsum(np.asarray(z) > 0); neg = np.cumsum(np.asarray(z) < 0); qp = np.cumsum(np.asarray(dq) > 0); qn = np.cumsum(np.asarray(dq) < 0)
    if len(z) == 0:
        return []
    le_win = betting_log_e_ternary(pos, neg, n, 0.0)
    le_harm = betting_log_e_ternary(neg, pos, n, 0.0)
    le_gate = betting_log_e_ternary(qp, qn, n, -margin)
    thr = np.log(1 / alpha)
    rows = []
    for i in range(len(z)):
        ok = n[i] >= min_n
        rows.append(dict(n=int(n[i]), z=int(z[i]), success_diff=int(dq[i]), n_win=int(pos[i]), n_loss=int(neg[i]), n_tie=int(n[i] - pos[i] - neg[i]),
                         n_succ_pos=int(qp[i]), n_succ_neg=int(qn[i]), nb_hat=float((pos[i] - neg[i]) / n[i]), succ_diff_hat=float((qp[i] - qn[i]) / n[i]),
                         log_e_win=float(le_win[i]), log_e_gate=float(le_gate[i]), log_e_harm=float(le_harm[i]),
                         e_win=float(np.exp(le_win[i])), e_gate=float(np.exp(le_gate[i])), e_harm=float(np.exp(le_harm[i])),
                         win_cross=bool(le_win[i] >= thr and ok), gate_cross=bool(le_gate[i] >= thr and ok),
                         deploy=bool(le_win[i] >= thr and le_gate[i] >= thr and ok), harm=bool(le_harm[i] >= thr and ok)))
    return rows


def first_index(rows, key):
    for r in rows:
        if r[key]:
            return r['n']
    return None


def completed_pairs(design: dict, episodes: list, trial: int):
    """Pairs whose two pass-1 episodes exist, in pair order. Returns (pair_indices, eps_A, eps_B)."""
    by_key = {(e['task_id'], e['variant'], e['trial']): e for e in episodes if e.get('pass') == 1}
    pairs = {}
    for a in design['arrivals']:
        if a['pair_index'] is None:
            continue
        e = by_key.get((a['task_id'], a['pass1_variant'], trial))
        if e is not None:
            pairs.setdefault(a['pair_index'], {})[a['pass1_variant']] = e
    idx = sorted(k for k, v in pairs.items() if A in v and B in v)
    return idx, [pairs[k][A] for k in idx], [pairs[k][B] for k in idx]


def write_monitor(results_dir: Path, design, episodes, cfg, trial):
    idx, eA, eB = completed_pairs(design, episodes, trial)
    tiers = tiers_from_config(cfg)
    rows = []
    if idx:
        z, tier, dq = pair_scores(eA, eB, tiers)
        rows = monitor_table(z, dq, cfg)
        for r, k, tk in zip(rows, idx, tier):
            r['pair_index'] = k; r['decisive_tier'] = int(tk)
    path = results_dir / ('monitor_pass1.csv' if trial == 1 else 'monitor_pass1_trial%d.csv' % trial)
    cols = ['pair_index', 'n', 'z', 'decisive_tier', 'success_diff', 'n_win', 'n_loss', 'n_tie', 'n_succ_pos', 'n_succ_neg', 'nb_hat', 'succ_diff_hat',
            'log_e_win', 'log_e_gate', 'log_e_harm', 'e_win', 'e_gate', 'e_harm', 'win_cross', 'gate_cross', 'deploy', 'harm']
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})
    state = dict(trial=trial, n_pairs_monitored=len(rows), alpha=cfg['alpha'], success_margin=cfg['success_margin'], min_n_pairs=cfg['min_n_pairs'],
                 first_win_cross=first_index(rows, 'win_cross'), first_gate_cross=first_index(rows, 'gate_cross'),
                 first_deploy=first_index(rows, 'deploy'), first_harm=first_index(rows, 'harm'),
                 note='execution never stops early; crossings are recorded for the anytime-valid analysis', updated_at=iso(now_ts()))
    (results_dir / ('monitor_state.json' if trial == 1 else 'monitor_state_trial%d.json' % trial)).write_text(json.dumps(state, indent=2))
    return state


# ---------------------------------------------------------------- pre-flight checks

def check_config_frozen(cfg: dict, design: dict, episodes: list):
    """Refuse when the loaded config differs from the frozen design or from any recorded episode."""
    if cfg['_config_hash'] != design['config_hash']:
        raise SystemExit('config hash %s differs from the frozen design config_hash %s; the design is frozen to its config' % (cfg['_config_hash'], design['config_hash']))
    other = sorted({e.get('config_hash') for e in episodes if e.get('config_hash') != cfg['_config_hash']})
    if other:
        raise SystemExit('config hash %s differs from existing episodes (%s); refusing to mix configurations in one results directory' % (cfg['_config_hash'], other))


def model_name_matches(cfg_model: str, response_model) -> bool:
    if not response_model:
        return False
    return response_model == cfg_model or cfg_model.split('/')[-1] in str(response_model)


def check_snapshot(cfg: dict, cache_dir=None) -> dict:
    rec = hf_snapshot_record(cfg['model'], cfg['model_revision_expected'], cache_dir)
    if not rec['ok']:
        raise SystemExit('model snapshot check failed: %s' % rec['error'])
    return rec


def smoke_check_model(model, cfg: dict) -> dict:
    """One tiny completion (not a task) before pass 1: records the served model id; refuses a mismatch."""
    if model.name == 'mock':
        return dict(kind='mock', response_model=model.model, ok=True)
    out = model.chat([dict(role='user', content=SMOKE_PROMPT)], dict(seed=0, kind='smoke'))
    rec = dict(kind='smoke', prompt=SMOKE_PROMPT, response_model=out.get('response_model'), text=(out.get('text') or '')[:100],
               completion_tokens=out.get('completion_tokens'), call_seconds=out.get('call_seconds'), ok=model_name_matches(cfg['model'], out.get('response_model')))
    if not rec['ok']:
        raise SystemExit('served model %r does not name the configured model %r' % (out.get('response_model'), cfg['model']))
    return rec


class RunLock:
    def __init__(self, results_dir: Path):
        self.path = results_dir / 'run.lock'

    def __enter__(self):
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    f.write(json.dumps(dict(pid=os.getpid(), at=iso(now_ts()), argv=sys.argv[1:])))
                return self
            except FileExistsError:
                try:
                    info = json.loads(self.path.read_text()); pid = int(info.get('pid', -1))
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
                    raise SystemExit('another run_stream.py (pid %d) holds %s; refusing a concurrent run' % (pid, self.path))
                self.path.unlink(missing_ok=True)  # stale lock from a dead process
        raise SystemExit('could not acquire %s' % self.path)

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- manifest (append-only)

def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return dict(schema=MANIFEST_SCHEMA, experiment='local_stream', created_at=iso(now_ts()), invocations=[])
    m = json.loads(path.read_text())
    if 'invocations' not in m or 'config' in m:
        raise SystemExit('%s has the pre-audit (mutable) shape; move it aside before running' % path)
    return m


def _write_manifest(path: Path, m: dict):
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(m, indent=2, default=str))
    os.replace(tmp, path)


def append_invocation(results_dir: Path, record: dict) -> str:
    """Append one invocation record; never modifies earlier records or top-level fields. Returns its id."""
    path = results_dir / 'run_manifest.json'
    m = _load_manifest(path)
    record = dict(record, invocation_id=uuid.uuid4().hex)
    m['invocations'].append(record)
    _write_manifest(path, m)
    return record['invocation_id']


def complete_invocation(results_dir: Path, invocation_id: str, **fields):
    """Fill the finishing fields of this invocation's own record (the only record ever touched after append)."""
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


def invocation_record(cfg, design, model, args, tasks, trial, snapshot, smoke, results_dir: Path) -> dict:
    sha_path = design_path(results_dir, trial).with_suffix('.sha256')
    return dict(at=iso(now_ts()), status='started', argv=sys.argv[1:], limit=args.limit, only_pass=args.only_pass, trial=trial, dry_run=bool(args.dry_run),
                config_path=cfg.get('_config_path'), config={k: v for k, v in cfg.items() if not k.startswith('_')}, config_hash=cfg['_config_hash'],
                design_sha256=sha_path.read_text().split()[0] if sha_path.exists() else None, design_config_hash=design['config_hash'],
                task_list_sha256=task_list_sha256(), n_tasks=len(tasks), model=model.model, model_kind=model.name,
                endpoint=cfg['base_url'] if model.name != 'mock' else 'mock', server_info=model.server_info(), model_snapshot=snapshot, smoke_check=smoke,
                sandbox={k: v for k, v in sandbox_info().items()}, hardware=hardware_info(), packages=package_versions(),
                harness_git_hash=harness_git_hash(), harness_file_sha256=harness_hashes(), python=sys.version,
                server_rss_start=process_rss_bytes('mlx_lm') if model.name != 'mock' else [])


# ---------------------------------------------------------------- main loop

def run(args, hf_cache_dir=None):
    cfg = load_config(args.config)
    results_dir = Path(args.results_dir); results_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(); by_uid = {t['uid']: t for t in tasks}
    trial = args.trial
    if trial == 2 and not cfg.get('trial2_enabled'):
        raise SystemExit('trial 2 is disabled in config')
    with RunLock(results_dir):
        if not design_path(results_dir, trial).exists():
            if args.dry_run:
                info = write_design(results_dir, cfg['design_seed'] if trial == 1 else cfg['trial2_seed'], cfg, trial)
                print('dry-run: generated design', info, flush=True)
            else:
                raise SystemExit('design.json missing: run design.py first (the design must be frozen before outcomes)')
        design = load_design(results_dir, trial)
        if design['task_list_sha256'] != task_list_sha256():
            raise SystemExit('task list sha256 differs from the frozen design')
        ep_path = results_dir / 'episodes.jsonl'
        episodes = read_jsonl(ep_path)
        check_config_frozen(cfg, design, episodes)
        done = {(e['task_id'], e['variant'], e['trial']) for e in episodes}
        arrivals = design['arrivals'][:args.limit] if args.limit else design['arrivals']
        passes = [1, 2] if args.only_pass == 0 else [args.only_pass]
        if passes == [2]:
            missing = [a['arrival_index'] for a in arrivals if (a['task_id'], a['pass1_variant'], trial) not in done]
            if missing:
                raise SystemExit('--only-pass 2 refused: pass 1 incomplete for %d selected arrivals (first: %s)' % (len(missing), missing[:5]))
        model = MockModel(cfg, tasks) if args.dry_run else OpenAICompatModel(cfg)
        snapshot = None if args.dry_run else check_snapshot(cfg, hf_cache_dir)
        smoke = smoke_check_model(model, cfg)
        inv_id = append_invocation(results_dir, invocation_record(cfg, design, model, args, tasks, trial, snapshot, smoke, results_dir))
        meta_common = dict(trial=trial, harness_git_hash=harness_git_hash())
        n_run = n_skip = 0; t0 = time.time(); status = 'completed'
        try:
            for p in passes:
                for a in arrivals:
                    variant = a['pass1_variant'] if p == 1 else a['pass2_variant']
                    key = (a['task_id'], variant, trial)
                    if key in done:
                        n_skip += 1
                        continue
                    meta = dict(meta_common, arrival_index=a['arrival_index'], pair_index=a['pair_index'], orientation=a['orientation'], **{'pass': p})
                    rec = run_episode(by_uid[a['task_id']], variant, model, cfg, meta)
                    served = [m for m in rec.get('response_models', []) if m is not None]
                    if model.name != 'mock' and served and not all(model_name_matches(cfg['model'], m) for m in served):
                        status = 'aborted: served model changed'
                        raise SystemExit('served model %r changed during the run; episode %s NOT recorded' % (served, key))
                    append_jsonl(ep_path, rec); episodes.append(rec); done.add(key); n_run += 1
                    print('[pass %d] arrival %4d/%d %-14s %-17s success=%d lat=%.2fs verify=%.2fs calls=%d ctoks=%d err=%s' % (
                        p, a['arrival_index'], len(design['arrivals']), a['task_id'], VARIANT_LETTER[variant] + ':' + variant, rec['success'], rec['latency_s'],
                        rec['verify_seconds'], rec['n_llm_calls'], rec['completion_tokens'], (rec['error'] or '')[:40]), flush=True)
                    if p == 1 and a['pair_index'] is not None and a['position_in_pair'] == 2:
                        st = write_monitor(results_dir, design, episodes, cfg, trial)
                        print('    monitor: pairs=%d first_deploy=%s first_harm=%s' % (st['n_pairs_monitored'], st['first_deploy'], st['first_harm']), flush=True)
        except KeyboardInterrupt:
            status = 'interrupted'
            raise
        finally:
            st = write_monitor(results_dir, design, episodes, cfg, trial)
            summary = dict(ran=n_run, skipped_completed=n_skip, elapsed_s=time.time() - t0, monitor=st, episodes_total=len(episodes))
            complete_invocation(results_dir, inv_id, status=status, finished_at=iso(now_ts()), summary=summary,
                                server_rss_end=process_rss_bytes('mlx_lm') if model.name != 'mock' else [])
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=None)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--dry-run', action='store_true', help='deterministic mock model; writes to the given results dir (use a scratch dir)')
    ap.add_argument('--limit', type=int, default=None, help='only the first N arrivals (both passes)')
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--only-pass', type=int, default=0, choices=(0, 1, 2), help='0 = pass 1 then pass 2; 2 requires pass 1 complete')
    args = ap.parse_args(argv)
    if args.dry_run and Path(args.results_dir).resolve() == RESULTS_DIR.resolve():
        raise SystemExit('refusing a dry run into the primary results directory; use --results-dir results/local_stream/dryrun')
    run(args)


if __name__ == '__main__':
    main()
