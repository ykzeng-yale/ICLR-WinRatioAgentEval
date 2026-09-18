"""Figures for the drift panel; reads results/drift_panel/results.csv only (no simulation)."""
import csv, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
import run_drift_panel as R

OUT = R.OUT / 'figures'; OUT.mkdir(parents=True, exist_ok=True)
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
C = ['#2a78d6', '#eb6834', '#1baf7a']
plt.rcParams.update({'font.size': 8, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED, 'xtick.color': MUTED,
                     'ytick.color': INK, 'text.color': INK, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 200})
rows = list(csv.DictReader(open(R.OUT / 'results.csv')))
S = R.build_scenarios()

# 1. design paths
names = [n for n in S if S[n]['family'] == 'B']
fig, axs = plt.subplots(3, 4, figsize=(11, 5.6), sharex=True, sharey='row')
for c, n in enumerate(names):
    for j in range(3):
        ax = axs[j, c]; run = S[n]['running'][j]; step = S[n]['step'][j]
        ax.plot(R.T, step, color=MUTED, lw=.8, ls=':', label='per-step conditional target')
        ax.plot(R.T[99:], run[99:], color=C[j], lw=2, label='running-average target')
        ax.axhline(R.THRESHOLDS[j], color=INK, lw=.8)
        v = run <= R.THRESHOLDS[j] + R.VIOL_TOL; v[:99] = False
        ax.fill_between(R.T, 0, 1, where=v, transform=ax.get_xaxis_transform(), color=C[j], alpha=.12, lw=0)
        ax.grid(color=GRID, lw=.5)
        if j == 0: ax.set_title(n, fontsize=8.5)
        if c == 0: ax.set_ylabel(f'{R.GATES[j]}\n(threshold {R.THRESHOLDS[j]:g})')
        if j == 2: ax.set_xlabel('pairs n')
axs[0, 0].legend(frameon=False, fontsize=7, loc='lower left')
fig.suptitle('Family B design: exact targets. Shaded = looks where that running target is at or below its threshold (deployment there is E_running)', fontsize=9)
fig.tight_layout(); fig.savefig(OUT / 'fig1_design_running_targets.png'); plt.close(fig)

# 2. error rates
cells = [n for n in S if S[n]['kind'] != 'power']
fig, axs = plt.subplots(2, 5, figsize=(13, 5.4), sharey=True)
for ax, n in zip(axs.ravel(), cells + [None]):
    if n is None: ax.axis('off'); continue
    rr = [r for r in rows if r['scenario'] == n][::-1]
    y = np.arange(len(rr)); p = np.array([float(r['E_running_any_rate']) for r in rr])
    lo = np.array([float(r['E_running_any_lo']) for r in rr]); hi = np.array([float(r['E_running_any_hi']) for r in rr])
    ax.hlines(y, lo, hi, color=C[0], lw=2); ax.plot(p, y, 'o', color=C[0], ms=5, mec=SURF, mew=1)
    ax.axvline(.05, color=INK, lw=.8, ls='--'); ax.set_xscale('symlog', linthresh=.01); ax.set_xlim(0, 6)
    ax.set_xticks([0, .01, .05, .3]); ax.set_xticklabels(['0', '.01', '.05', '.3'])
    ax.set_yticks(y); ax.set_yticklabels([r['rule'] for r in rr]); ax.grid(axis='x', color=GRID, lw=.5)
    ax.set_title(n, fontsize=8.5)
    for yy, pp, hh in zip(y, p, hi): ax.text(5.5, yy, f'{pp:.4f}', ha='right', va='center', fontsize=6.5, color=MUTED)
fig.suptitle('P(E_running_any): deployment condition holds at a look whose claimed running target is violated. Wilson 95% intervals, 10,000 replicates; dashed = 0.05.\n'
             'In A1-A3, C1, C2, B3a, B3b every look is violated for guarded rules, so this equals ever-false-deployment. Win-only rules claim net benefit only.', fontsize=8.5)
fig.tight_layout(); fig.savefig(OUT / 'fig2_error_rates.png'); plt.close(fig)

# 3. power and sample use
cells = [n for n in S if S[n]['kind'] == 'power']
fig, axs = plt.subplots(2, 3, figsize=(11, 5.2), sharey=True)
for c, n in enumerate(cells):
    rr = [r for r in rows if r['scenario'] == n][::-1]; y = np.arange(len(rr))
    for k, (key, lab) in enumerate([('ever_deploy', 'deployment rate (Wilson 95%)'), ('mean_pairs_used', 'mean capped pairs (+/- 2 MCSE); executions = 2x')]):
        ax = axs[k, c]
        if k == 0:
            p = np.array([float(r['ever_deploy_rate']) for r in rr]); lo = [float(r['ever_deploy_lo']) for r in rr]; hi = [float(r['ever_deploy_hi']) for r in rr]
            ax.hlines(y, lo, hi, color=C[0], lw=2); ax.plot(p, y, 'o', color=C[0], ms=5, mec=SURF, mew=1); ax.set_xlim(-.03, 1.03)
            ax.set_title(n, fontsize=8.5)
        else:
            m = np.array([float(r['mean_pairs_used']) for r in rr]); e = 2 * np.array([float(r['mean_pairs_mcse']) for r in rr])
            ax.hlines(y, 0, m, color=C[0], lw=3); ax.hlines(y, m - e, m + e, color=INK, lw=1)
            for yy, mm in zip(y, m): ax.text(mm + 150, yy, f'{mm:.0f}', va='center', fontsize=6.5, color=MUTED)
            ax.set_xlim(0, 11500)
        ax.set_xlabel(lab); ax.set_yticks(y); ax.set_yticklabels([r['rule'] for r in rr]); ax.grid(axis='x', color=GRID, lw=.5)
fig.suptitle('Common-drift power cells (2,000 replicates; max 10,000 pairs = 20,000 executions; non-deployment counts as 10,000 pairs)', fontsize=9)
fig.tight_layout(); fig.savefig(OUT / 'fig3_power_sample_use.png'); plt.close(fig)
