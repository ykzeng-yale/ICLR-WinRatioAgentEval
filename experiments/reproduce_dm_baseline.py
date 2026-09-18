"""Reproduce only the eight complete-data scenarios of run_online_methods.

This isolated rerun deliberately never imports wincs or runs width_study.
The eight scenarios and original seed/batching are retained for comparison
with already-existing contributed results; this is a reproduction, not a
new prospective protocol. See evidence/dm_baseline.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'experiments'))
from ternary_dm import validated_log_eprocess
from run_simulations import SCENARIOS as BASE_SCENARIOS, generate, exact_targets, wilson
from run_simulations import evaluate as evaluate_original_baselines

SCENARIOS = dict(BASE_SCENARIOS)
SCENARIOS.update({
    'tie_heavy_null': (.995, .995, .30, .30, 1.),
    'tie_heavy_efficiency': (.995, .995, .30, .30, .55),
})
THRESHOLDS = (0., -.03, -.01)
PRIOR = (1., 1., 1.)
METHODS = (
    'win_only_betting', 'win_only_multinomial', 'guarded_betting',
    'guarded_multinomial', 'guarded_normal_mixture',
    'guarded_repeated_wald', 'guarded_group_bonferroni_wald',
    'guarded_fixed_wald',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(zs, looks, alpha):
    """Same scores, looks and contemporaneous gate conjunction for all rules."""
    out = evaluate_original_baselines(zs, looks, alpha)
    gates = []
    for z, c in zip(zs, THRESHOLDS):
        if not np.all(np.isin(z, [-1, 0, 1])):
            raise ValueError('This comparator requires complete ternary scores.')
        pos = np.cumsum(z > 0, axis=1)[:, looks - 1]
        neg = np.cumsum(z < 0, axis=1)[:, looks - 1]
        tie = looks - pos - neg
        log_e = validated_log_eprocess(pos, tie, neg, c, PRIOR)
        if np.isnan(log_e).any():
            raise FloatingPointError('NaN in Dirichlet-mixture evidence.')
        gates.append(log_e >= np.log(1 / alpha))
    out['win_only_multinomial'] = gates[0]
    out['guarded_multinomial'] = np.logical_and.reduce(gates)
    return {name: out[name] for name in METHODS}


def compare_reference(rows, reference_path):
    """Check every corresponding numeric/string field, allowing float roundoff."""
    with reference_path.open(newline='') as handle:
        reference = {(r['scenario'], r['method']): r for r in csv.DictReader(handle)}
    differences = []
    max_abs_difference = 0.0
    for row in rows:
        key = (row['scenario'], row['method'])
        old = reference.get(key)
        if old is None:
            differences.append({'row': key, 'field': '*', 'reason': 'Missing reference'})
            continue
        for field, value in row.items():
            other = old[field]
            if isinstance(value, (float, int, np.floating)) and not isinstance(value, bool):
                delta = abs(float(value) - float(other))
                max_abs_difference = max(max_abs_difference, delta)
                if not np.isclose(float(value), float(other), rtol=1e-11, atol=1e-11):
                    differences.append({'row': key, 'field': field, 'new': value, 'old': other})
            elif str(value) != other:
                differences.append({'row': key, 'field': field, 'new': value, 'old': other})
    return dict(reference_sha256=sha(reference_path), rows_checked=len(rows),
                exact_or_roundoff_equivalent=not differences,
                max_absolute_numeric_difference=max_abs_difference,
                differences=differences)


def optional_git_revision():
    """Source hashes remain available in standalone anonymous archives."""
    try:
        return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replicates', type=int, default=2000)
    parser.add_argument('--pairs', type=int, default=10000)
    parser.add_argument('--batch', type=int, default=25)
    parser.add_argument('--seed', type=int, default=20260918)
    args = parser.parse_args()
    if args.replicates < 2 or args.batch < 1 or args.pairs < 100 or args.pairs % 100:
        raise ValueError('Use >=2 repetitions, positive batch, and >=100 pairs divisible by 100.')
    start = time.time()
    looks = np.unique(np.r_[np.arange(100, args.pairs + 1, 50), args.pairs,
                            np.arange(1, 11) * (args.pairs // 10)])
    alpha = .05
    rows = []
    paired_rows = []
    for j, (name, params) in enumerate(SCENARIOS.items()):
        rng = np.random.default_rng(np.random.SeedSequence([args.seed, j]))
        targets = exact_targets(params)
        admissible = all(x > c for x, c in zip(targets, THRESHOLDS))
        accum = {}
        paired_gains = []
        for begin in range(0, args.replicates, args.batch):
            batch = min(args.batch, args.replicates - begin)
            decisions = evaluate(generate(rng, (batch, args.pairs), params), looks, alpha)
            batch_stops = {}
            for method, d in decisions.items():
                success = d.any(axis=1)
                stops = np.where(success, looks[np.argmax(d, axis=1)], args.pairs)
                batch_stops[method] = stops
                acc = accum.setdefault(method, {'deploy': 0, 'stop_sum': 0., 'stop_sq': 0., 'positive_stop': []})
                acc['deploy'] += int(success.sum())
                acc['stop_sum'] += float(stops.sum())
                acc['stop_sq'] += float((stops.astype(float) ** 2).sum())
                acc['positive_stop'].extend(stops[success].tolist())
            paired_gains.extend((batch_stops['guarded_multinomial'] - batch_stops['guarded_betting']).tolist())
        for method, acc in accum.items():
            low, high = wilson(acc['deploy'], args.replicates)
            mean = acc['stop_sum'] / args.replicates
            rows.append(dict(
                scenario=name, method=method, replicates=args.replicates, max_pairs=args.pairs,
                true_net_benefit=targets[0], true_success_difference=targets[1], true_safety_difference=targets[2],
                admissible=admissible, deployments=acc['deploy'], deployment_rate=acc['deploy'] / args.replicates,
                rate_ci_lower=low, rate_ci_upper=high, mean_pairs_used=mean,
                # Preserve contributed row definition for exact reproducibility.
                mean_pairs_mcse=np.sqrt(max(acc['stop_sq'] / args.replicates - mean * mean, 0) / args.replicates),
                median_pairs_among_deployments=float(np.median(acc['positive_stop'])) if acc['positive_stop'] else ''))
        gains = np.asarray(paired_gains, float)
        paired_rows.append(dict(scenario=name, replicates=args.replicates,
                                mean_dm_minus_betting_capped_pairs=float(gains.mean()),
                                paired_difference_mcse=float(gains.std(ddof=1) / np.sqrt(args.replicates))))
        print(name, {m: round(a['deploy'] / args.replicates, 4) for m, a in accum.items()}, flush=True)
    output = ROOT / 'results'
    for filename, table in [('dm_baseline_results.csv', rows), ('dm_baseline_paired.csv', paired_rows)]:
        with (output / filename).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=table[0].keys())
            writer.writeheader(); writer.writerows(table)
    reference = ROOT / 'results' / 'online_methods_results.csv'
    exact_args = vars(args) == dict(replicates=2000, pairs=10000, batch=25, seed=20260918)
    check = compare_reference(rows, reference) if exact_args and reference.exists() else {'skipped': 'Nonreference configuration or reference absent'}
    (output / 'dm_baseline_reproduction_check.json').write_text(json.dumps(check, indent=2))
    sources = [Path(__file__), ROOT / 'src/ternary_dm.py', ROOT / 'src/winstats.py', ROOT / 'experiments/run_simulations.py']
    manifest = dict(
        arguments=vars(args), alpha=alpha, thresholds=THRESHOLDS, dirichlet_prior=PRIOR,
        looks=looks.tolist(), scenarios=SCENARIOS, seconds=time.time() - start,
        python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        git_head_at_run=optional_git_revision(),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        output_sha256={p.name: sha(p) for p in output.glob('dm_baseline_*') if p.name != 'dm_baseline_manifest.json'},
        inference='Complete iid ternary score streams; alpha per gate controls a single stationary conjunction, not simultaneous component confidence coverage.',
        exclusion='No generic multinomial projections, confidence-width study, two-sided inversion helpers, or asynchronous lower-score substitution.',
        provenance='Reproduction of existing contributed eight-scenario results. Tie-heavy extensions were added after the original six scenarios. This rerun is not a new preregistration.',
        reproduction_check=check)
    (output / 'dm_baseline_manifest.json').write_text(json.dumps(manifest, indent=2))
    if check.get('differences'):
        raise AssertionError('Contributed complete-data rows did not reproduce; inspect the check artifact.')
    print('Reproduction finished:', check, flush=True)


if __name__ == '__main__':
    main()
