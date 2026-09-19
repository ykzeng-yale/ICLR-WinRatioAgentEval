"""FROZEN design generator for the tau2 open-model stream: arrival order, disjoint pairs, orientation.

Units: the 98 (task, trial) episodes per arm (49 airline tasks "1".."49" x 2
tau2 trials; task "0" is excluded because the coordinator's smoke runs used it).
seed 20260918 -> numpy SeedSequence -> default_rng. Arrival order (config
``arrival_blocking = "by_trial"``): arrivals 1..49 are a random permutation of
the 49 trial-0 units (block 1), arrivals 50..98 a random permutation of the 49
trial-1 units (block 2); each block visits every task exactly once. Arrivals
(2k-1, 2k) (1-based) form pair k, k = 1..49. With an odd block size pair 25
straddles the two blocks (arrivals 49 and 50); the "block-1 subset" of the
analysis is the set of pairs whose two arrivals are both in block 1 = pairs
1..24 (48 distinct tasks), which covers min_n = 20. Orientation R_k ~
Bernoulli(1/2), fixed per pair: R_k = 1 means the first arrival of pair k is
observed under arm A (agent qwen2.5-7b-instruct) in the pass-1 single-exposure
stream and the second under arm B (agent qwen3-4b-instruct-2507); R_k = 0
reverses. The complementary arm's episode for the same (task, trial) unit is
the pass-2 (shadow) episode.

tau2 executes each arm as a batch (trial-major, task order 1..49), so the
EXECUTION order differs from the ARRIVAL order; the stream order and
orientation are prespecified here and the analysis uses only these prespecified
pairings (no adaptivity), so sequential validity refers to the prespecified
sequence. The design is written BEFORE any outcome exists; the generator
refuses to overwrite an existing design unless --force and no episode file
exists. Determinism does not depend on PYTHONHASHSEED (numpy RNG, sorted tasks).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

import numpy as np

from common import RESULTS_DIR, canonical_json, harness_git_hash, iso, load_config, now_ts, sha256_file, sha256_text

A, B = 'A', 'B'
PROVENANCE_KEYS = ('generated_at', 'generator_sha256', 'harness_git_hash')


def units(cfg: dict) -> list:
    """Canonical unit list: (task_id, trial) sorted by trial then numeric task id."""
    tasks = sorted(cfg['task_ids'], key=lambda t: (len(t), t))
    return [(t, tr) for tr in range(cfg['num_trials']) for t in tasks]


def task_list_sha256(cfg: dict) -> str:
    return sha256_text(canonical_json(dict(domain=cfg['domain'], task_ids=sorted(cfg['task_ids'], key=lambda t: (len(t), t)),
                                           num_trials=cfg['num_trials'], airline_data_sha256=cfg['airline_data_sha256'])))


def generate(cfg: dict, seed: int) -> dict:
    U = units(cfg)
    n = len(U)
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    if cfg.get('arrival_blocking', 'by_trial') == 'by_trial':
        order = []
        for tr in range(cfg['num_trials']):
            idx = [i for i, u in enumerate(U) if u[1] == tr]
            perm = rng.permutation(len(idx))
            order += [idx[int(p)] for p in perm]
    else:
        order = [int(p) for p in rng.permutation(n)]
    n_pairs = n // 2
    orientation = rng.integers(0, 2, size=n_pairs)
    leftover_first_A = int(rng.integers(0, 2)) if n % 2 else None
    arrivals = []
    for i, ui in enumerate(order):
        task_id, trial = U[ui]
        k = i // 2
        if k < n_pairs:
            R = int(orientation[k]); pos = i % 2
            v1 = A if (R == 1) == (pos == 0) else B
            pair_index, orient, pos_in_pair = k + 1, R, pos + 1
        else:
            v1 = A if leftover_first_A == 1 else B
            pair_index, orient, pos_in_pair = None, None, None
        arrivals.append(dict(arrival_index=i + 1, task_id=task_id, trial=trial, block=trial + 1, pair_index=pair_index, position_in_pair=pos_in_pair,
                             orientation=orient, pass1_arm=v1, pass2_arm=B if v1 == A else A))
    return dict(experiment='tau2_open', seed=seed, seed_mechanism='numpy.random.SeedSequence(seed) -> default_rng; per-trial-block permutation then Bernoulli(1/2) per pair',
                arrival_blocking=cfg.get('arrival_blocking', 'by_trial'), n_units=n, n_tasks=len(cfg['task_ids']), n_trials=cfg['num_trials'],
                n_pairs=n_pairs, n_unpaired=n - 2 * n_pairs, domain=cfg['domain'], task_list_sha256=task_list_sha256(cfg),
                arms=dict(A='agent %s' % cfg['arms']['A']['alias'], B='agent %s' % cfg['arms']['B']['alias'], user='%s (both arms)' % cfg['user_alias']),
                orientation_rule='R=1: first arrival of the pair -> arm A, second -> arm B in pass 1; R=0 reversed',
                execution_note='tau2 runs each arm as a batch (trial-major, task order); arrival order and orientation are prespecified and the analysis uses only these pairings',
                config_hash=cfg['_config_hash'], generator_sha256=sha256_file(Path(__file__)), harness_git_hash=harness_git_hash(),
                generated_at=iso(now_ts()), arrivals=arrivals)


def content_sha256(d: dict) -> str:
    return sha256_text(canonical_json({k: v for k, v in d.items() if k not in PROVENANCE_KEYS}))


def design_path(results_dir: Path) -> Path:
    return results_dir / 'design.json'


def write_design(results_dir: Path, cfg: dict, force=False) -> dict:
    results_dir.mkdir(parents=True, exist_ok=True)
    out = design_path(results_dir)
    if out.exists() and not force:
        raise FileExistsError('%s exists; the design is frozen (use --force only before any episode exists)' % out)
    if force and ((results_dir / 'episodes.csv').exists() or (results_dir / 'raw').exists()):
        raise RuntimeError('episodes.csv or raw/ exists in %s; refusing to regenerate a design after outcomes' % results_dir)
    d = generate(cfg, cfg['design_seed'])
    text = canonical_json(d)
    d_hash = sha256_text(text)
    out.write_text(text)
    out.with_suffix('.sha256').write_text(d_hash + '  ' + out.name + '\n')
    return dict(path=str(out), sha256=d_hash, content_sha256=content_sha256(d), n_units=d['n_units'], n_pairs=d['n_pairs'])


def load_design(results_dir: Path) -> dict:
    p = design_path(results_dir)
    d = json.loads(p.read_text())
    recorded = p.with_suffix('.sha256').read_text().split()[0]
    if sha256_text(canonical_json(d)) != recorded:
        raise RuntimeError('design file %s does not match its recorded sha256' % p)
    return d


def check_pairing_invariants(d: dict, cfg: dict):
    """Raise AssertionError if the design violates the pairing rules (used by tests and pre-flight)."""
    arr = d['arrivals']
    assert len(arr) == cfg['num_trials'] * len(cfg['task_ids']) == d['n_units']
    assert [a['arrival_index'] for a in arr] == list(range(1, len(arr) + 1))
    assert len({(a['task_id'], a['trial']) for a in arr}) == len(arr), 'each unit arrives exactly once'
    pairs = {}
    for a in arr:
        if a['pair_index'] is not None:
            pairs.setdefault(a['pair_index'], []).append(a)
    assert len(pairs) == d['n_pairs'] == len(arr) // 2
    for k, ps in pairs.items():
        assert len(ps) == 2 and [p['position_in_pair'] for p in ps] == [1, 2]
        assert ps[0]['arrival_index'] == 2 * k - 1 and ps[1]['arrival_index'] == 2 * k
        assert {ps[0]['pass1_arm'], ps[1]['pass1_arm']} == {A, B}
        assert (ps[0]['pass1_arm'] == A) == (ps[0]['orientation'] == 1)
        assert all(p['pass2_arm'] != p['pass1_arm'] for p in ps)
    if d.get('arrival_blocking') == 'by_trial':
        n_t = len(cfg['task_ids'])
        for tr in range(cfg['num_trials']):
            blk = arr[tr * n_t:(tr + 1) * n_t]
            assert all(a['trial'] == tr and a['block'] == tr + 1 for a in blk)
            assert sorted(a['task_id'] for a in blk) == sorted(cfg['task_ids']), 'each block visits every task once'
    per_task = {}
    for a in arr:
        per_task[a['task_id']] = per_task.get(a['task_id'], 0) + 1  # every task arrives num_trials times (once per trial block)
    assert set(per_task.values()) == {cfg['num_trials']} and set(per_task) == set(cfg['task_ids'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--config', default=None)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--print-sha-only', action='store_true', help='generate in memory and print the content sha256 (used by tests)')
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.print_sha_only:
        print(content_sha256(generate(cfg, cfg['design_seed'])))
        return
    info = write_design(Path(args.results_dir), cfg, args.force)
    d = load_design(Path(args.results_dir)); check_pairing_invariants(d, cfg)
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
