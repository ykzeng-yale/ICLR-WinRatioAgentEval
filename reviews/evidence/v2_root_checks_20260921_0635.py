"""Read-only bounded audit of the 63be271 exact export; no native reference calls.

Usage: python v2_root_checks_20260921_0635.py EXPORTED_REPO
"""
import csv
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
val = root / 'experiments/live_ab_validation'
sys.path[:0] = [str(val/'pinned_v2'), str(val), str(root/'src')]
import lab_enclosure as live
import vband
import vpolicy
import vcompare
import numpy as np

results = root/'results/live_ab_validation_v2'
with (results/'comparison_v2_alllook_oracle/comparison_defects.csv').open() as f:
    rows = [r for r in csv.DictReader(f)
            if r['defect_class'] == 'per_pair_enclosure_endpoint' and int(r['tick']) > 2000]
checks = []
for r in rows:
    arm = r['revealed_arm']
    other = 'candidate' if arm == 'incumbent' else 'incumbent'
    ell, cost = float(r['ell']), float(r['revealed_cost'])
    a = {arm: live.EpisodeView.reveal(arm, 1, cost, 0),
         other: live.EpisodeView.pending(other, ell=ell)}
    b = {arm: vband.Episode.pending(arm, 100).finalized(1, cost),
         other: vband.Episode.pending(other, 100).with_elapsed_cost(ell)}
    enclosure = live.hierarchy_enclosure(a['candidate'], a['incumbent'], vband.TIERS)
    oracle = vband.hierarchy_bounds(b['candidate'], b['incumbent'])
    operational = vpolicy.operational_hierarchy_bounds(b['candidate'], b['incumbent'])
    assert list(oracle) == [float(r['enc12_lo']), float(r['enc12_hi'])]
    assert list(operational) == [enclosure.lo, enclosure.hi] == [float(r['enc11_lo']), float(r['enc11_hi'])]
    assert enclosure.lo <= oracle[0] <= oracle[1] <= enclosure.hi
    checks.append({'cell': r['cell'], 'tick': int(r['tick']), 'oracle': oracle,
                   'operational': operational, 'contained': True})
assert len(checks) == 3

vcompare.select_snapshot('v2')
generator = vcompare.FrozenGenerator(vcompare.load_frozen_config())
receipt = json.loads((results/'reference_width_diagnostic_descriptive_correction.json').read_text())
count = 0
for cell in range(1, 9):
    z = np.asarray(generator.build('C'+str(cell), 0, 0).z_true)
    centers = np.concatenate(([0.], np.cumsum(z)[:-1]/np.arange(1, len(z))))
    clock = np.maximum(1., np.cumsum((z-centers)**2))
    for r in receipt['rows']:
        if r['cell'] != 'C'+str(cell):
            continue
        n = r['n']
        assert abs(np.sum((z[:n]-np.mean(z[:n]))**2)-r['prefix_centered_sum_of_squares']) < 1e-8
        assert abs(clock[n-1]-r['reference_clock_V_n']) < 1e-8
        count += 1
assert count == 48
print(json.dumps({'drain_states': checks, 'prefix_variance_and_clock_rows': count}, indent=2))
