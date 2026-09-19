"""Verifier/label-noise sensitivity of hierarchical net benefit on tau2-bench.

Randomly flips recorded success labels (nondifferential: same flip rate in
both systems; differential: flips only in one system) at rates 1%, 5%, 10%,
recomputes the primary hierarchical net benefit (12 off-diagonal pairs) and the
success difference, and reports the mean shift and the fraction of the 200
contaminated replicates whose decision (95% CI excludes 0) changes.
Compares to the theoretical bound |NB_h - NB_g| <= 2 P(h differs from g).
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'experiments'))
from wincs import task_level_scores, clustered_summary
from analyze_benchmarks import hierarchy, absorbing, runs_dict, SRC, OUT

df = pd.read_csv(SRC / 'tau2_runs.csv')
df = df[(df.config == 'default') & df.domain.isin(['airline', 'retail', 'telecom'])].copy()
df['success'] = (df.reward >= 1 - 1e-9).astype(float)
df = df.rename(columns={'agent_cost': 'cost', 'n_assistant_tool_calls': 'steps'})
cols = ['success', 'cost', 'steps']; tiers = hierarchy()
pairs = [('o4-mini-2025-04-16', 'gpt-4.1-2025-04-14'), ('claude-3-7-sonnet-20250219', 'gpt-4.1-2025-04-14'), ('claude-3-7-sonnet-20250219', 'o4-mini-2025-04-16')]
rng = np.random.default_rng(2026); rows = []
def nb_of(dA, dB):
    s = task_level_scores(runs_dict(dA, cols), runs_dict(dB, cols), tiers, eligible=absorbing, pairing='offdiagonal')
    c = clustered_summary(s['win'], s['loss']); return c['net_benefit'], c['nb_ci']
for dom in ['airline', 'retail', 'telecom']:
    for a, b in pairs:
        dA0 = df[(df.model == a) & (df.domain == dom)].reset_index(drop=True); dB0 = df[(df.model == b) & (df.domain == dom)].reset_index(drop=True)
        nb0, ci0 = nb_of(dA0, dB0); dec0 = np.sign(nb0) if (ci0[0] > 0 or ci0[1] < 0) else 0
        for mode in ['nondifferential', 'differential_A_only']:
            for rate in [0.01, 0.05, 0.10]:
                nbs = []; decs = []
                for r in range(200):
                    dA = dA0.copy(); dB = dB0.copy()
                    fa = rng.random(len(dA)) < rate; dA.loc[fa, 'success'] = 1 - dA.loc[fa, 'success']
                    if mode == 'nondifferential':
                        fb = rng.random(len(dB)) < rate; dB.loc[fb, 'success'] = 1 - dB.loc[fb, 'success']
                    nb, ci = nb_of(dA, dB); nbs.append(nb); decs.append(np.sign(nb) if (ci[0] > 0 or ci[1] < 0) else 0)
                nbs = np.array(nbs); decs = np.array(decs)
                rows.append(dict(domain=dom, A=a, B=b, mode=mode, flip_rate=rate, nb_clean=nb0, nb_mean=nbs.mean(), nb_sd=nbs.std(),
                                 max_abs_shift=float(np.abs(nbs - nb0).max()), bound_2p=2 * (1 - (1 - rate)**2) if mode == 'nondifferential' else 2 * rate,
                                 decision_clean=int(dec0), frac_decision_changed=float((decs != dec0).mean())))
                print(rows[-1], flush=True)
out = pd.DataFrame(rows); out.to_csv(OUT / 'label_noise_sensitivity.csv', index=False)
print(out.groupby(['mode', 'flip_rate'])[['max_abs_shift', 'frac_decision_changed']].max())
