"""Timing pilot: both variants on 6 tasks that are NOT in the frozen design.

Purpose: measure per-episode latency and tokens on this host so the coordinator
can project the runtime of the 1,182-episode stream. The six tasks come from the
FULL MBPP release (google-research `mbpp.jsonl`, 974 problems) and are chosen
deterministically among problems that are NOT in the sanitized set: disjoint by
task_id AND by (normalised) prompt text, asserted at run time against
work/local_stream/data/tasks.json. They never enter the analysis: everything is
written to results/local_stream/timing_pilot/ only (never episodes.jsonl of the
stream), and analysis.py never reads that directory.

The pilot runs the real pre-flight checks (snapshot revision, served model id)
and the same run_episode code path as the stream, so it also exercises the
sandbox on real model output.
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

import numpy as np
import requests

from common import RESULTS_DIR, canonical_json, harness_hashes, hardware_info, iso, load_config, now_ts, sha256_bytes, sha256_text
from data import load_tasks, mbpp_entry_point
from agent import OpenAICompatModel, MockModel, run_episode
from run_stream import check_snapshot, smoke_check_model, A, B
from sandbox import sandbox_info

FULL_MBPP_URL = 'https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl'
PILOT_DIR = RESULTS_DIR / 'timing_pilot'
N_TASKS = 6
PILOT_SEED = 20260920  # unrelated to the design seeds 20260918 / 20260919


def _norm(text: str) -> str:
    return re.sub(r'\W+', ' ', text.lower()).strip()


def fetch_full_mbpp(cache: Path | None = None) -> tuple:
    """Download the full MBPP release into memory (about 560 KB); only URL/bytes/sha256 are recorded.

    The raw file is not stored under results/ (third-party data stays out of the
    repository); pass ``cache`` to keep a copy elsewhere.
    """
    if cache is not None and cache.exists():
        data = cache.read_bytes(); cached = True
    else:
        r = requests.get(FULL_MBPP_URL, timeout=120); r.raise_for_status()
        data = r.content; cached = False
        if cache is not None:
            cache.write_bytes(data)
    rows = [json.loads(l) for l in data.decode('utf-8').splitlines() if l.strip()]
    return rows, dict(url=FULL_MBPP_URL, bytes=len(data), sha256=sha256_bytes(data), cached=cached, n_rows=len(rows), fetched_at=iso(now_ts()))


def select_pilot_tasks(full_rows: list, stream_tasks: list, n: int = N_TASKS, seed: int = PILOT_SEED) -> list:
    """Deterministic choice of n full-MBPP problems disjoint (task_id and prompt text) from the stream's tasks."""
    stream_ids = {t['source_task_id'] for t in stream_tasks if t['benchmark'] == 'mbpp'}
    stream_prompts = {_norm(t['prompt']) for t in stream_tasks}
    eligible = [r for r in full_rows if int(r['task_id']) not in stream_ids and _norm(r['text']) not in stream_prompts
                and r.get('test_list') and r.get('code')]
    eligible.sort(key=lambda r: int(r['task_id']))
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    picks = [eligible[int(i)] for i in sorted(rng.choice(len(eligible), n, replace=False))]
    tasks = []
    for r in picks:
        rec = dict(task_id=int(r['task_id']), prompt=r['text'].strip(), code=r['code'], test_list=list(r['test_list']),
                   challenge_test_list=list(r.get('challenge_test_list') or []))
        setup = (r.get('test_setup_code') or '').strip()
        tasks.append(dict(uid='mbpp_full/%d' % rec['task_id'], benchmark='mbpp', source_task_id=rec['task_id'], prompt=rec['prompt'],
                          entry_point=mbpp_entry_point(rec), reference=rec['code'], test_imports=[setup] if setup else [],
                          test_list=rec['test_list'], challenge_test_list=rec['challenge_test_list'], origin='full MBPP (not sanitized); timing pilot only'))
    assert_disjoint(tasks, stream_tasks)
    return tasks


def assert_disjoint(pilot_tasks: list, stream_tasks: list):
    stream_ids = {t['source_task_id'] for t in stream_tasks if t['benchmark'] == 'mbpp'}
    stream_uids = {t['uid'] for t in stream_tasks}
    stream_prompts = {_norm(t['prompt']) for t in stream_tasks}
    for t in pilot_tasks:
        if t['source_task_id'] in stream_ids or t['uid'] in stream_uids:
            raise AssertionError('pilot task %s shares a task_id with the frozen design' % t['uid'])
        if _norm(t['prompt']) in stream_prompts:
            raise AssertionError('pilot task %s shares its prompt text with a design task' % t['uid'])


def run_pilot(args):
    cfg = load_config(args.config)
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.resolve() == RESULTS_DIR.resolve() or out_dir.resolve() == (RESULTS_DIR / 'dryrun').resolve():
        raise SystemExit('the pilot must write to its own directory, never the stream results')
    stream_tasks = load_tasks()
    full_rows, dl = fetch_full_mbpp(Path(args.cache_full) if args.cache_full else None)
    pilot = select_pilot_tasks(full_rows, stream_tasks, args.n, PILOT_SEED)
    (out_dir / 'pilot_tasks.json').write_text(canonical_json(pilot))
    model = MockModel(cfg, pilot) if args.dry_run else OpenAICompatModel(cfg)
    snapshot = None if args.dry_run else check_snapshot(cfg)
    smoke = smoke_check_model(model, cfg)
    ep_path = out_dir / 'episodes.jsonl'
    if ep_path.exists() and not args.append:
        ep_path.unlink()
    recs = []
    t0 = time.time()
    for i, t in enumerate(pilot):
        for variant in (A, B) if i % 2 == 0 else (B, A):  # alternate order so warm-up affects both arms
            rec = run_episode(t, variant, model, cfg, dict(trial=0, arrival_index=None, pair_index=None, orientation=None, **{'pass': 0}))
            rec['pilot'] = True
            recs.append(rec)
            with open(ep_path, 'a') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            print('%-14s %-17s success=%d lat=%.2fs verify=%.2fs calls=%d ptoks=%d ctoks=%d err=%s' % (
                t['uid'], variant, rec['success'], rec['latency_s'], rec['verify_seconds'], rec['n_llm_calls'], rec['prompt_tokens'],
                rec['completion_tokens'], (rec['error'] or '')[:40]), flush=True)
    summary = dict(generated_at=iso(now_ts()), dry_run=bool(args.dry_run), model=model.model, config_hash=cfg['_config_hash'], n_tasks=len(pilot),
                   pilot_task_ids=[t['uid'] for t in pilot], full_mbpp_download=dl, model_snapshot={k: v for k, v in (snapshot or {}).items() if k != 'files'},
                   smoke_check=smoke, sandbox={k: v for k, v in sandbox_info().items() if k != 'profile'}, hardware=hardware_info(),
                   harness_file_sha256=harness_hashes(), elapsed_s=time.time() - t0, per_variant={})
    for v in (A, B):
        e = [r for r in recs if r['variant'] == v]
        summary['per_variant'][v] = dict(n=len(e), success=int(sum(r['success'] for r in e)),
                                         latency_s_mean=float(np.mean([r['latency_s'] for r in e])), latency_s_max=float(max(r['latency_s'] for r in e)),
                                         verify_seconds_mean=float(np.mean([r['verify_seconds'] for r in e])),
                                         completion_tokens_mean=float(np.mean([r['completion_tokens'] for r in e])),
                                         prompt_tokens_mean=float(np.mean([r['prompt_tokens'] for r in e])),
                                         n_llm_calls_mean=float(np.mean([r['n_llm_calls'] for r in e])), repair_rounds_mean=float(np.mean([r['repair_rounds'] for r in e])),
                                         llm_seconds_mean=float(np.mean([sum(r['llm_call_seconds']) for r in e])))
    per_task_pair = summary['per_variant'][A]['latency_s_mean'] + summary['per_variant'][B]['latency_s_mean'] + \
        summary['per_variant'][A]['verify_seconds_mean'] + summary['per_variant'][B]['verify_seconds_mean']
    summary['projection'] = dict(n_stream_tasks=len(stream_tasks), episodes=2 * len(stream_tasks), seconds_per_task_both_variants=per_task_pair,
                                 projected_hours=per_task_pair * len(stream_tasks) / 3600.0,
                                 note='mean latency (A+B) + mean verify time, times 591 tasks; monitoring/IO overhead excluded')
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(dict(per_variant=summary['per_variant'], projection=summary['projection']), indent=2))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=None)
    ap.add_argument('--out-dir', default=str(PILOT_DIR))
    ap.add_argument('--n', type=int, default=N_TASKS)
    ap.add_argument('--dry-run', action='store_true', help='mock model (pipeline test only)')
    ap.add_argument('--append', action='store_true', help='keep an existing episodes.jsonl in the pilot directory')
    ap.add_argument('--cache-full', default=None, help='optional path (outside results/) to cache the full MBPP download')
    args = ap.parse_args(argv)
    run_pilot(args)


if __name__ == '__main__':
    main()
