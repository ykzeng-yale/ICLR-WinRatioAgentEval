"""Figures for the Round 9 report (results/local_stream/report_v2.md). POST HOC copy of make_figures.py (which is kept unchanged).

Reads the raw monitor file (monitor_pass1.csv, monitor_state.json), the v2 analysis outputs (summary_v2.json,
running_cs_v2.csv) and the CS-independent episodes_flat.csv, and writes PDF + PNG into
results/local_stream/figures_v2/. No model call, no git command.

  fig1_monitoring      log e-values of the win / gate / harm e-processes (unchanged paths; one-sided, not affected by the
                       two-sided fix). Status label: descriptive under R1, anytime-valid under the R2 iid-roster assumption.
  fig2_running_nb      running cross-arrival net benefit with BOTH the corrected hedged betting CS (R2, target theta_P under the
                       iid-roster assumption) and the normal-mixture CS for the running average mu_bar_n (R1, design-based);
                       same-task NB +- CI as reference
  fig3_tier_decomp     tier decomposition (wins / losses / ties) for E1 and E2 side by side
  fig4_latency_scatter per-task latency A vs B (log axes) coloured by success pattern

Usage: .venv/bin/python experiments/local_stream/make_figures_v2.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

# Colour-blind-safe palette (validated with the dataviz palette validator, light surface, all pairs).
BLUE, ORANGE, AQUA, RED, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#e34948', '#8c8b87'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e6e5e1'
WIDTH = 5.5  # inches; readable at column width

plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 8, 'legend.fontsize': 7, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
    'legend.frameon': False, 'pdf.fonttype': 42, 'savefig.dpi': 200, 'lines.linewidth': 1.6,
})


def save(fig, out_dir: Path, name: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf', 'png'):
        fig.savefig(out_dir / f'{name}.{ext}', bbox_inches='tight')
    plt.close(fig)
    print('wrote', out_dir / f'{name}.{{pdf,png}}')


# ------------------------------------------------------------------ fig 1

def fig1_monitoring(mon: pd.DataFrame, state: dict, out: Path):
    alpha, min_n = state['alpha'], state['min_n_pairs']
    thr = np.log(1 / alpha)
    n = mon['n'].values
    first_harm = state['first_harm']
    fig, (ax, axz) = plt.subplots(1, 2, figsize=(WIDTH, 2.6), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.32))
    series = [('win: H0 E[Z] <= 0', mon['log_e_win'].values, BLUE, '-'),
              ('gate: H0 E[D] <= -0.03', mon['log_e_gate'].values, AQUA, '--'),
              ('harm: H0 E[Z] >= 0', mon['log_e_harm'].values, ORANGE, '-')]
    for a, xmax in ((ax, n.max()), (axz, 60)):
        a.axvspan(0, min_n, color=GRID, alpha=0.6, lw=0, zorder=0)
        a.axhline(thr, color=INK2, lw=0.9, ls=':', zorder=1)
        a.axhline(0, color=INK2, lw=0.6, zorder=1)
        for label, y, c, ls in series:
            a.plot(n, y, color=c, ls=ls, label=label, zorder=3)
        a.set_xlim(0, xmax)
        a.set_xlabel('pass-1 pair index k')
    ax.set_ylabel('log e-value')
    ax.set_ylim(-3, 36)
    ax.text(n.max(), thr + 0.8, 'log(1/alpha) = %.2f' % thr, ha='right', va='bottom', fontsize=6.5, color=INK2)
    ax.text(min_n / 2, 34, 'n < %d:\nnot read' % min_n, ha='center', va='top', fontsize=6, color=INK2)
    ax.text(n.max(), mon['log_e_harm'].values[-1], ' harm', color=ORANGE, va='center', fontsize=7)
    ax.text(n.max(), mon['log_e_gate'].values[-1] + 1.2, ' gate', color=AQUA, va='center', fontsize=7)
    ax.text(n.max(), mon['log_e_win'].values[-1] - 1.2, ' win', color=BLUE, va='center', fontsize=7)
    ax.set_title('(a) all %d pairs' % n.max(), loc='left')
    # zoom
    axz.set_ylim(-1.5, 7)
    axz.set_title('(b) first 60 pairs', loc='left')
    if first_harm is not None:
        yh = mon.loc[mon['n'] == first_harm, 'log_e_harm'].values[0]
        for a in (ax, axz):
            a.plot([first_harm], [yh], marker='o', ms=6, mfc='white', mec=ORANGE, mew=1.4, zorder=5)
        axz.annotate('composite harm signal for B:\ncrossing at pair %d (log e = %.2f)' % (first_harm, yh), xy=(first_harm, yh),
                     xytext=(first_harm - 4, 6.0), fontsize=6.5, color=INK, ha='left', va='center',
                     arrowprops=dict(arrowstyle='-', color=INK2, lw=0.7))
    # exceedances before min_n are not read (pre-specified); mark the first one for transparency
    pre = mon[(mon['n'] < min_n) & (mon['log_e_harm'] >= thr)]
    if len(pre):
        k0, y0 = int(pre['n'].iloc[0]), float(pre['log_e_harm'].iloc[0])
        axz.plot([k0], [y0], marker='o', ms=5, mfc='none', mec=INK2, mew=0.9, ls='none', zorder=5)
        axz.annotate('above threshold at pair %d,\nbefore min_n = %d (not read)' % (k0, min_n), xy=(k0, y0), xytext=(31, 1.1), fontsize=6,
                     color=INK2, ha='left', va='center', arrowprops=dict(arrowstyle='-', color=INK2, lw=0.6))
    fig.legend(handles=[Line2D([], [], color=c, ls=ls, label=l) for l, _, c, ls in series], loc='upper center',
               bbox_to_anchor=(0.5, 1.06), ncol=3, handlelength=2.2, columnspacing=1.6)
    fig.text(0.5, -0.06, 'one-sided e-processes: descriptive under R1 (fixed roster); anytime-valid at alpha only under the R2 iid-roster assumption',
             ha='center', va='top', fontsize=6.3, color=INK2)
    save(fig, out, 'fig1_monitoring')


# ------------------------------------------------------------------ fig 2

def fig2_running_nb(mon: pd.DataFrame, run: pd.DataFrame, summ: dict, state: dict, out: Path):
    n = run['n'].values
    assert (n == mon['n'].values).all() and np.allclose(run['nb_hat'].values, mon['nb_hat'].values)
    sh = summ['shadow']; r1, r2 = summ['e1']['R1'], summ['e1']['R2']
    first_harm = state['first_harm']
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.axhline(0, color=INK2, lw=0.6, zorder=1)
    ax.axhspan(sh['nb_ci'][0], sh['nb_ci'][1], color=ORANGE, alpha=0.18, lw=0, zorder=1)
    ax.axhline(sh['net_benefit'], color=ORANGE, lw=1.4, ls='--', zorder=2)
    # R1: normal-mixture CS for the running average (design-based)
    ax.fill_between(n, run['r1_nb_lo'], run['r1_nb_hi'], color=AQUA, alpha=0.13, lw=0, zorder=2)
    ax.plot(n, run['r1_nb_lo'], color=AQUA, lw=1.0, ls='--', zorder=3); ax.plot(n, run['r1_nb_hi'], color=AQUA, lw=1.0, ls='--', zorder=3)
    # R2: corrected hedged betting CS (iid-roster assumption)
    ax.fill_between(n, run['r2_nb_lo'], run['r2_nb_hi'], color=BLUE, alpha=0.16, lw=0, zorder=2)
    ax.plot(n, run['r2_nb_lo'], color=BLUE, lw=0.8, zorder=3); ax.plot(n, run['r2_nb_hi'], color=BLUE, lw=0.8, zorder=3)
    ax.plot(n, run['nb_hat'].values, color=INK, lw=1.4, zorder=4)
    ax.set_xlim(0, n.max()); ax.set_ylim(-1.0, 0.62)
    ax.set_xlabel('pass-1 pair index k'); ax.set_ylabel('net benefit of B vs A')
    ax.text(n.max() + 2, -0.30, 'E1 NB = %.2f\nR2 [%.2f, %.2f]\nR1 [%.2f, %.2f]' % (r2['nb_hat'], *r2['nb_cs'], *r1['nb_cs']), color=INK, va='center', fontsize=6.3)
    ax.text(n.max() + 2, sh['net_benefit'] - 0.04, 'E2 same-task\nNB = %.2f\nCI [%.2f, %.2f]' % (sh['net_benefit'], *sh['nb_ci']), color=ORANGE, va='top', fontsize=6.3)
    marks = [(first_harm, ORANGE, 'harm e-process crossing, pair %s (descriptive under R1)' % first_harm, 0.60),
             (r2['first_n_nb_upper_below_0'], BLUE, 'R2 betting CS first below 0: pair %s' % r2['first_n_nb_upper_below_0'], 0.50),
             (r1['first_n_nb_upper_below_0'], AQUA, 'R1 normal-mixture CS below 0: pair %s' % r1['first_n_nb_upper_below_0'], 0.40)]
    for x, c, label, y in marks:
        if x is not None:
            ax.axvline(x, color=c, lw=0.8, ls=':', zorder=1)
            ax.text(x + 2, y, label, fontsize=6.3, color=INK2, va='top')
    ax.legend(handles=[Line2D([], [], color=INK, label='running NB (E1)'),
                       Line2D([], [], color=BLUE, label='R2: 95% corrected betting CS (iid-roster assumption)'),
                       Line2D([], [], color=AQUA, ls='--', label='R1: 95% normal-mixture CS for running average (design-based)'),
                       Line2D([], [], color=ORANGE, ls='--', label='same-task NB (E2), 95% task-level CI')],
              loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=6.2, columnspacing=1.4)
    save(fig, out, 'fig2_running_nb')


# ------------------------------------------------------------------ fig 3

def tier_counts_e1(summ: dict):
    td = summ['online']['tier_decomposition']
    rows = [(t, td[t]['wins'], td[t]['losses']) for t in ('success', 'latency_s', 'completion_tokens')]
    return rows, summ['online']['ties'], summ['online']['n_pairs']


def tier_counts_e2(ep: pd.DataFrame, summ: dict):
    """Recompute the same-task decomposition from episodes (one A and one B per task, frozen hierarchy)."""
    tiers = {t['name']: t for t in json.load(open(REPO / 'experiments/local_stream/config.json'))['hierarchy']}
    A = ep[ep['variant_letter'] == 'A'].set_index('task_id'); B = ep[ep['variant_letter'] == 'B'].set_index('task_id')
    B = B.loc[A.index]
    sA, sB = A['success'].astype(bool).values, B['success'].astype(bool).values
    tier = np.full(len(A), 'tie', dtype=object); z = np.zeros(len(A), int)
    z[sB & ~sA] = 1; z[sA & ~sB] = -1; tier[sB != sA] = 'success'
    both = sA & sB
    for name in ('latency_s', 'completion_tokens'):
        tol = tiers[name]['relative_tolerance']
        a, b = A[name].values, B[name].values
        d = b - a; und = both & (tier == 'tie') & (np.abs(d) > tol * np.maximum(np.abs(a), np.abs(b)))
        z[und] = np.where(d[und] < 0, 1, -1); tier[und] = name
    rows = [(t, int(((tier == t) & (z > 0)).sum()), int(((tier == t) & (z < 0)).sum())) for t in ('success', 'latency_s', 'completion_tokens')]
    n_tie = int((z == 0).sum())
    # cross-check with the frozen analysis
    assert abs(z.mean() - summ['shadow']['net_benefit']) < 1e-9, (z.mean(), summ['shadow']['net_benefit'])
    return rows, n_tie, len(A)


def fig3_tiers(summ: dict, ep: pd.DataFrame, out: Path):
    e1_rows, e1_tie, n1 = tier_counts_e1(summ)
    e2_rows, e2_tie, n2 = tier_counts_e2(ep, summ)
    labels = ['success', 'latency (10% tol.)', 'completion tokens\n(10% tol.)', 'tie']
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.5), sharey=True, gridspec_kw=dict(wspace=0.12))
    for ax, (rows, n_tie, n), title in zip(axes, ((e1_rows, e1_tie, n1), (e2_rows, e2_tie, n2)),
                                          ('(a) E1 cross-arrival, %d pairs' % n1, '(b) E2 same-task, %d tasks' % n2)):
        y = np.arange(len(labels))[::-1]
        wins = np.array([r[1] for r in rows] + [0]) / n; losses = np.array([r[2] for r in rows] + [0]) / n
        ties = np.array([0, 0, 0, n_tie]) / n
        ax.barh(y, wins, color=BLUE, height=0.55, zorder=3)
        ax.barh(y, -losses, color=RED, height=0.55, zorder=3)
        ax.barh(y, ties, left=-ties / 2, color=GRAY, height=0.55, zorder=3)  # ties centred on zero
        ax.axvline(0, color=INK2, lw=0.8, zorder=4)
        counts = [r[1] for r in rows] + [n_tie]; lcounts = [r[2] for r in rows] + [0]
        for yi, w, t, l, cw, cl in zip(y, wins, ties, losses, counts, lcounts):
            if cw:
                ax.text(max(w, t / 2) + 0.02, yi, str(cw), va='center', ha='left', fontsize=7, color=INK)
            if cl:
                ax.text(-l - 0.02, yi, str(cl), va='center', ha='right', fontsize=7, color=INK)
        nb = sum(r[1] - r[2] for r in rows) / n
        ax.set_title(title.replace(', ', '\n', 1) + ', NB = %.3f' % nb, loc='left', fontsize=8)
        ax.set_xlim(-0.78, 0.36)
        ax.set_xticks([-0.6, -0.4, -0.2, 0, 0.2]); ax.set_xticklabels(['60%', '40%', '20%', '0', '20%'])
        ax.set_xlabel('share of units      (B loses  |  B wins)')
        ax.grid(axis='y', visible=False)
    axes[0].set_yticks(np.arange(len(labels))[::-1]); axes[0].set_yticklabels(labels)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=RED), plt.Rectangle((0, 0), 1, 1, color=GRAY)],
               labels=['B wins (decided at this tier)', 'B loses (decided at this tier)', 'tie (both failed, or within tolerance)'],
               loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=3, columnspacing=1.2, handlelength=1.2)
    save(fig, out, 'fig3_tier_decomp')


# ------------------------------------------------------------------ fig 4

def fig4_latency_scatter(ep: pd.DataFrame, out: Path):
    A = ep[ep['variant_letter'] == 'A'].set_index('task_id'); B = ep[ep['variant_letter'] == 'B'].set_index('task_id').loc[A.index]
    sA, sB = A['success'].astype(bool).values, B['success'].astype(bool).values
    lA, lB = A['latency_s'].values, B['latency_s'].values
    groups = [('both succeed', sA & sB, BLUE, 'o'), ('A only', sA & ~sB, ORANGE, '^'), ('B only', ~sA & sB, AQUA, 's'), ('neither', ~sA & ~sB, GRAY, 'x')]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    lim = (0.4, 70)
    xs = np.array(lim)
    ax.fill_between(xs, 0.9 * xs, xs / 0.9, color=GRID, alpha=0.9, lw=0, zorder=1, label='tier-2 tie band (10%)')
    ax.plot(xs, xs, color=INK2, lw=0.8, zorder=2)
    for label, m, c, mk in groups:
        if mk == 'x':  # unfilled marker: colour is carried by `color`, not edgecolors
            ax.scatter(lA[m], lB[m], s=16, marker=mk, color=c, linewidths=0.8, alpha=0.85, zorder=3, label='%s (n = %d)' % (label, int(m.sum())))
        else:
            ax.scatter(lA[m], lB[m], s=13, marker=mk, facecolors='none', edgecolors=c, linewidths=0.8, alpha=0.85, zorder=3,
                       label='%s (n = %d)' % (label, int(m.sum())))
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(*lim); ax.set_ylim(*lim)
    ax.set_xlabel('latency of A single_shot (s, log)'); ax.set_ylabel('latency of B self_test_repair (s, log)')
    ax.text(0.45, 0.44, 'B faster', fontsize=6.5, color=INK2, va='bottom')
    ax.text(0.45, 50, 'B slower', fontsize=6.5, color=INK2)
    ax.text(0.55, 0.55 / 0.9 * 1.12, '10% tie band', fontsize=6.5, color=INK2, rotation=45, ha='left', va='bottom', rotation_mode='anchor')
    ax.legend(loc='lower right', markerscale=1.3)
    ax.set_aspect('equal')
    save(fig, out, 'fig4_latency_scatter')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(REPO / 'results/local_stream'))
    args = ap.parse_args(argv)
    rd = Path(args.results_dir); out = rd / 'figures_v2'
    mon = pd.read_csv(rd / 'monitor_pass1.csv')
    summ = json.load(open(rd / 'summary_v2.json'))
    run = pd.read_csv(rd / 'running_cs_v2.csv')
    state = json.load(open(rd / 'monitor_state.json'))
    ep = pd.read_csv(rd / 'episodes_flat.csv')
    fig1_monitoring(mon, state, out)
    fig2_running_nb(mon, run, summ, state, out)
    fig3_tiers(summ, ep, out)
    fig4_latency_scatter(ep, out)


if __name__ == '__main__':
    main()
