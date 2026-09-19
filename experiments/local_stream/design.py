"""FROZEN design generator: arrival order, disjoint pairs and per-pair orientation.

seed 20260918 -> numpy SeedSequence -> default_rng. Arrival order is a random
permutation of the canonical task list; arrivals (2k-1, 2k) (1-based) form pair
k; orientation R_k ~ Bernoulli(1/2) fixed per pair: R=1 means the first arrival
of the pair gets variant A (single_shot) in pass 1 and the second gets B
(self_test_repair); R=0 reverses this. With 591 tasks the last arrival (index
590) has no partner: it is still run in both passes and enters the same-task
shadow analysis but no cross-arrival pair; its pass-1 variant is one extra
Bernoulli draw. Pass 2 runs the complementary variant for every arrival in the
same order. The design is written BEFORE any outcome exists and the generator
refuses to overwrite an existing design (unless --force and no episodes exist).
Determinism does not depend on PYTHONHASHSEED (numpy RNG, sorted task list).
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np

from common import RESULTS_DIR, canonical_json, harness_git_hash, iso, load_config, now_ts, sha256_file, sha256_text
from data import load_tasks, task_list_sha256

A, B = 'single_shot', 'self_test_repair'


def generate(tasks: list, seed: int, cfg: dict, trial: int = 1) -> dict:
    n = len(tasks)
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    perm = rng.permutation(n)
    n_pairs = n // 2
    orientation = rng.integers(0, 2, size=n_pairs)
    leftover_first_A = int(rng.integers(0, 2)) if n % 2 else None
    arrivals = []
    for i, ti in enumerate(perm):
        t = tasks[int(ti)]
        k = i // 2
        if k < n_pairs:
            R = int(orientation[k]); pos = i % 2
            v1 = A if (R == 1) == (pos == 0) else B
            pair_index, orient, pos_in_pair = k + 1, R, pos + 1
        else:
            v1 = A if leftover_first_A == 1 else B
            pair_index, orient, pos_in_pair = None, None, None
        arrivals.append(dict(arrival_index=i + 1, task_id=t['uid'], benchmark=t['benchmark'], pair_index=pair_index,
                             position_in_pair=pos_in_pair, orientation=orient, pass1_variant=v1, pass2_variant=B if v1 == A else A))
    return dict(experiment='local_stream', trial=trial, seed=seed, seed_mechanism='numpy.random.SeedSequence(seed) -> default_rng; permutation then Bernoulli(1/2) per pair',
                n_tasks=n, n_pairs=n_pairs, n_unpaired=n - 2 * n_pairs, task_list_sha256=task_list_sha256(),
                strata=dict(mbpp=sum(t['benchmark'] == 'mbpp' for t in tasks), humaneval=sum(t['benchmark'] == 'humaneval' for t in tasks)),
                variants=dict(A=A, B=B), orientation_rule='R=1: first arrival of the pair -> A, second -> B in pass 1; R=0 reversed',
                config_hash=cfg['_config_hash'], generator_sha256=sha256_file(Path(__file__)), harness_git_hash=harness_git_hash(),
                generated_at=iso(now_ts()), arrivals=arrivals)


def design_path(results_dir: Path, trial: int = 1) -> Path:
    return results_dir / ('design.json' if trial == 1 else 'design_trial%d.json' % trial)


def write_design(results_dir: Path, seed: int, cfg: dict, trial: int = 1, force=False) -> dict:
    results_dir.mkdir(parents=True, exist_ok=True)
    out = design_path(results_dir, trial)
    if out.exists() and not force:
        raise FileExistsError('%s exists; the design is frozen (use --force only before any episode exists)' % out)
    if force and (results_dir / 'episodes.jsonl').exists():
        raise RuntimeError('episodes.jsonl exists in %s; refusing to regenerate a design after outcomes' % results_dir)
    d = generate(load_tasks(), seed, cfg, trial)
    text = canonical_json(d)
    d_hash = sha256_text(text)
    out.write_text(text)
    (out.with_suffix('.sha256')).write_text(d_hash + '  ' + out.name + '\n')
    return dict(path=str(out), sha256=d_hash, n_tasks=d['n_tasks'], n_pairs=d['n_pairs'])


def load_design(results_dir: Path, trial: int = 1) -> dict:
    p = design_path(results_dir, trial)
    d = json.loads(p.read_text())
    recorded = (p.with_suffix('.sha256')).read_text().split()[0]
    if sha256_text(canonical_json(d)) != recorded:
        raise RuntimeError('design file %s does not match its recorded sha256' % p)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--config', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--print-sha-only', action='store_true', help='generate in memory and print the sha256 (used by tests)')
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    seed = cfg['design_seed'] if args.trial == 1 else cfg['trial2_seed']
    if args.print_sha_only:
        print(sha256_text(canonical_json({k: v for k, v in generate(load_tasks(), seed, cfg, args.trial).items() if k not in ('generated_at', 'generator_sha256', 'harness_git_hash')})))
        return
    info = write_design(Path(args.results_dir), seed, cfg, args.trial, args.force)
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
