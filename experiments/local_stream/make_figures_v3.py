"""Figure 2 for the Round 10 report (results/local_stream/report_v3.md). POST HOC; make_figures.py and make_figures_v2.py are
kept unchanged, and results/local_stream/figures_v2/ is not overwritten.

Only the wording and the same-task reference band change relative to figures_v2/fig2_running_nb:
  * R1 legend: "running conditional mean" (the Round 9 legend said "design-based", a wording withdrawn in Round 10);
  * same-task reference: the task-level t interval is labelled MODEL-BASED, and the exact orientation-pair cluster
    Hoeffding interval of summary_v3.json (296 clusters) is drawn as a second, lighter band;
  * every plotted number is read from running_cs_v2.csv, monitor_pass1.csv, monitor_state.json and summary_v3.json.
Figures 1, 3 and 4 do not depend on the withdrawn wording and are not regenerated. No model call, no git command.

Usage: .venv/bin/python experiments/local_stream/make_figures_v3.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_figures_v2 as v2  # noqa: E402  (palette, rcParams, save)
from make_figures_v2 import plt, Line2D, BLUE, ORANGE, AQUA, INK, INK2, WIDTH, REPO  # noqa: E402


def fig2_running_nb_v3(mon: pd.DataFrame, run: pd.DataFrame, s3: dict, state: dict, out: Path):
    n = run['n'].values
    assert (n == mon['n'].values).all() and np.allclose(run['nb_hat'].values, mon['nb_hat'].values)
    r1, r2 = s3['e1']['R1'], s3['e1']['R2']
    # the running file is the Round 9 file; its last row must agree with the Round 10 summary
    assert np.allclose([run['r1_nb_lo'].values[-1], run['r1_nb_hi'].values[-1]], r1['nb_cs'])
    assert np.allclose([run['r2_nb_lo'].values[-1], run['r2_nb_hi'].values[-1]], r2['nb_cs'])
    e2 = s3['e2']['net_benefit']['estimate']
    task_t = s3['e2_old_vs_new']['v3']['task_t']; clus_h = s3['e2_old_vs_new']['v3']['cluster_hoeffding']
    first_harm = state['first_harm']
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.axhline(0, color=INK2, lw=0.6, zorder=1)
    ax.axhspan(clus_h[0], clus_h[1], color=ORANGE, alpha=0.09, lw=0, zorder=1)
    ax.axhspan(task_t[0], task_t[1], color=ORANGE, alpha=0.22, lw=0, zorder=1)
    ax.axhline(e2, color=ORANGE, lw=1.4, ls='--', zorder=2)
    ax.fill_between(n, run['r1_nb_lo'], run['r1_nb_hi'], color=AQUA, alpha=0.13, lw=0, zorder=2)
    ax.plot(n, run['r1_nb_lo'], color=AQUA, lw=1.0, ls='--', zorder=3); ax.plot(n, run['r1_nb_hi'], color=AQUA, lw=1.0, ls='--', zorder=3)
    ax.fill_between(n, run['r2_nb_lo'], run['r2_nb_hi'], color=BLUE, alpha=0.16, lw=0, zorder=2)
    ax.plot(n, run['r2_nb_lo'], color=BLUE, lw=0.8, zorder=3); ax.plot(n, run['r2_nb_hi'], color=BLUE, lw=0.8, zorder=3)
    ax.plot(n, run['nb_hat'].values, color=INK, lw=1.4, zorder=4)
    ax.set_xlim(0, n.max()); ax.set_ylim(-1.0, 0.62)
    ax.set_xlabel('pass-1 pair index k'); ax.set_ylabel('net benefit of B vs A')
    ax.text(n.max() + 2, -0.30, 'E1 NB = %.2f\nR2 [%.2f, %.2f]\nR1 [%.2f, %.2f]' % (r2['nb_hat'], *r2['nb_cs'], *r1['nb_cs']), color=INK, va='center', fontsize=6.3)
    ax.text(n.max() + 2, e2 - 0.04, 'E2 same-task\nNB = %.2f\nmodel-based t\n[%.2f, %.2f]\ncluster Hoeffding\n[%.2f, %.2f]' % (e2, *task_t, *clus_h),
            color=ORANGE, va='top', fontsize=6.3)
    marks = [(first_harm, ORANGE, 'harm e-process crossing, pair %s (descriptive under R1)' % first_harm, 0.60),
             (r2['first_n_nb_upper_below_0'], BLUE, 'R2 betting CS first below 0: pair %s' % r2['first_n_nb_upper_below_0'], 0.50),
             (r1['first_n_nb_upper_below_0'], AQUA, 'R1 normal-mixture CS below 0: pair %s' % r1['first_n_nb_upper_below_0'], 0.40)]
    for x, c, label, y in marks:
        if x is not None:
            ax.axvline(x, color=c, lw=0.8, ls=':', zorder=1)
            ax.text(x + 2, y, label, fontsize=6.3, color=INK2, va='top')
    ax.legend(handles=[Line2D([], [], color=INK, label='running NB (E1)'),
                       Line2D([], [], color=BLUE, label='R2: 95% corrected betting CS (iid-roster model)'),
                       Line2D([], [], color=AQUA, ls='--', label='R1: 95% normal-mixture CS, running conditional mean'),
                       Line2D([], [], color=ORANGE, ls='--', label='same-task NB (E2): model-based t band (dark), cluster Hoeffding (light)')],
              loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=6.0, columnspacing=1.2)
    v2.save(fig, out, 'fig2_running_nb')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(REPO / 'results/local_stream'))
    args = ap.parse_args(argv)
    rd = Path(args.results_dir); out = rd / 'figures_v3'
    fig2_running_nb_v3(pd.read_csv(rd / 'monitor_pass1.csv'), pd.read_csv(rd / 'running_cs_v2.csv'),
                       json.load(open(rd / 'summary_v3.json')), json.load(open(rd / 'monitor_state.json')), out)


if __name__ == '__main__':
    main()
