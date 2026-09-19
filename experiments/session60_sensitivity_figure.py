"""Hierarchy/threshold sensitivity figure from results/benchmarks/tau2_contrasts.csv
and a within-task vs cross-task (tau_star vs tau_pop) panel from decision_matrix.csv."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
t = pd.read_csv(ROOT / 'results/benchmarks/tau2_contrasts.csv')
short = {'gpt-4.1-2025-04-14': 'GPT-4.1', 'o4-mini-2025-04-16': 'o4-mini', 'claude-3-7-sonnet-20250219': 'Claude 3.7'}
configs = [('success_only', 'success only'), ('margin_0', 'cost margin 0%'), ('primary', 'cost margin 5% (primary)'), ('margin_10', 'cost margin 10%'), ('margin_20', 'cost margin 20%'),
           ('order_success_steps_cost', 'steps before cost'), ('lexicographic_nonabsorbing', 'rank joint failures'), ('with_duration_4th', '+ duration tier'), ('diagonal_shared_seed', 'same-seed pairs'), ('all_16_pairs', 'all 16 pairs')]
t = t[t.domain != 'all']
t['contrast'] = [f"{d}: {short[a]} vs {short[b]}" for a, b, d in zip(t.A, t.B, t.domain)]
contrasts = sorted(t.contrast.unique(), key=lambda s: (s.split(':')[0], s))
M = np.full((len(contrasts), len(configs)), np.nan); S = np.zeros_like(M, dtype=object)
for i, c in enumerate(contrasts):
    for j, (lab, _) in enumerate(configs):
        r = t[(t.contrast == c) & (t.label == lab)]
        if len(r):
            r = r.iloc[0]; M[i, j] = r.net_benefit
            S[i, j] = '*' if (r.nb_lo > 0 or r.nb_hi < 0) else ''
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw=dict(width_ratios=[2.6, 1]))
ax = axes[0]
im = ax.imshow(M, cmap='RdBu', vmin=-0.7, vmax=0.7, aspect='auto')
ax.set_xticks(range(len(configs))); ax.set_xticklabels([l for _, l in configs], rotation=35, ha='right', fontsize=8)
ax.set_yticks(range(len(contrasts))); ax.set_yticklabels(contrasts, fontsize=8)
for i in range(len(contrasts)):
    for j in range(len(configs)):
        if not np.isnan(M[i, j]):
            ax.text(j, i, f"{M[i,j]:+.2f}{S[i,j]}", ha='center', va='center', fontsize=6.5, color='white' if abs(M[i, j]) > 0.35 else 'black')
ax.set_title('τ²-bench net benefit under alternative comparison rules (* = 95% task-clustered CI excludes 0)', fontsize=9)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label('net benefit', fontsize=8)
# panel 2: tau_star vs tau_pop
d = pd.read_csv(ROOT / 'results/benchmarks/decision_matrix.csv'); d = d[d.source == 'tau2']
ax = axes[1]
ax.errorbar(d.tau_pop_nb, d.nb, xerr=[d.tau_pop_nb - d.tau_pop_lo, d.tau_pop_hi - d.tau_pop_nb], yerr=[d.nb - d.nb_lo, d.nb_hi - d.nb], fmt='o', color='#0072B2', ecolor='#999999', elinewidth=0.8, capsize=0, ms=4)
lim = [-0.7, 0.7]; ax.plot(lim, lim, '--', color='gray', lw=0.8); ax.axhline(0, color='k', lw=0.5); ax.axvline(0, color='k', lw=0.5)
ax.set_xlim(lim); ax.set_ylim(lim); ax.set_xlabel('cross-task contrast τ_pop (A vs B on different tasks)', fontsize=8); ax.set_ylabel('within-task contrast τ* (same task, off-diagonal runs)', fontsize=8)
ax.set_title('Offline vs online-style estimands (τ², 9 contrasts)', fontsize=9)
for r in d.itertuples():
    if np.sign(r.nb) != np.sign(r.tau_pop_nb):
        ax.annotate(f"{r.domain}: {short[r.A]} vs {short[r.B]}", (r.tau_pop_nb, r.nb), fontsize=6.5, xytext=(6, -10), textcoords='offset points')
plt.tight_layout()
for ext in ['pdf', 'png']:
    fig.savefig(ROOT / f'plots/session60/fig_sensitivity.{ext}', dpi=200, bbox_inches='tight')
print('saved')
