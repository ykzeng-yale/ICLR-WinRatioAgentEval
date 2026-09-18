"""Session-60 publication figures (PDF + PNG) for the replay / benchmark /
online-methods / CS-width results, plus a small "price of the simplex"
simulation.  Writes to plots/session60/.  Read-only on every input.

Run:  .venv/bin/python experiments/session60_figures.py
"""
import sys, json, hashlib, importlib.util, time
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path('/Users/yukangzengcmac/ICLR-WinRatioAgentEvals')
sys.path.insert(0, str(ROOT / 'src'))
from wincs import ternary_log_eprocess_nb
from winstats import betting_log_e_ternary

RES = ROOT / 'results'; OUT = ROOT / 'plots' / 'session60'; OUT.mkdir(parents=True, exist_ok=True)
ALPHA = 0.05; LOG20 = np.log(1 / ALPHA)

# ---------------------------------------------------------------- style
# Validated categorical palette (dataviz skill, adjacent-order CVD check passes):
C_BLUE, C_ORANGE, C_AQUA, C_YELLOW = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
C_VIOLET, C_RED = '#4a3aa7', '#e34948'
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8984', '#e6e5e1'
W = 5.5  # ICLR single-column text width in inches
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 8, 'xtick.labelsize': 7.5,
    'ytick.labelsize': 7.5, 'legend.fontsize': 7.5, 'axes.edgecolor': INK2, 'axes.linewidth': 0.6,
    'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK, 'axes.labelcolor': INK,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': False,
    'legend.frameon': False, 'lines.linewidth': 1.4, 'savefig.dpi': 300, 'pdf.fonttype': 42,
    'ps.fonttype': 42, 'figure.dpi': 120,
})


def save(fig, name):
    fig.savefig(OUT / f'{name}.pdf', bbox_inches='tight', pad_inches=0.02)
    fig.savefig(OUT / f'{name}.png', bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print('wrote', name, flush=True)


def grid(ax, axis='y'):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


KEY = {}  # numbers used in README


# ------------------------------------------------------------------ fig 1
def fig_replay_stopping():
    """Stopping-time distributions, paired vs cross-arrival, o4-mini vs GPT-4.1 (all domains).

    replay_results.csv stores only summary quantiles, so the per-replicate
    distribution is re-simulated here by importing the functions of
    experiments/run_replay.py (same pools, same scoring, same guarded rule,
    500 random orders, fresh seeds).  Deployment rates and medians from the
    canonical CSV are annotated and cross-checked against the re-run.
    """
    rr = pd.read_csv(RES / 'replay' / 'replay_results.csv')
    sub = rr[rr.label == 'tau2_o4mini_vs_gpt41_all'].set_index('design')
    spec = importlib.util.spec_from_file_location('run_replay', ROOT / 'experiments' / 'run_replay.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    df = mod.load_tau2(); doms = ['airline', 'retail', 'telecom']
    PA = mod.pools(df, 'o4-mini-2025-04-16', doms); PB = mod.pools(df, 'gpt-4.1-2025-04-14', doms)
    reps, n = 500, 2000
    times = {}
    for k, design in enumerate(['paired', 'cross_arrival']):
        rng = np.random.default_rng([60, k])
        t = []
        for r in range(reps):
            A, B = mod.stream(rng, PA, PB, n, design)
            z, dq = mod.score_pairs(A, B)
            t.append(mod.run_guarded(z, dq)['deploy_time'])
        times[design] = np.array([x if x is not None else np.nan for x in t], float)
    rerun = {d: dict(deploy_rate=float(np.mean(~np.isnan(v))), median=float(np.nanmedian(v)) if np.any(~np.isnan(v)) else None)
             for d, v in times.items()}
    KEY['replay_rerun'] = rerun
    KEY['replay_csv'] = {d: dict(deploy_rate=float(sub.loc[d, 'deploy_rate']), median=float(sub.loc[d, 'median_deploy_time']),
                                 q25=float(sub.loc[d, 'q25_deploy_time']), q75=float(sub.loc[d, 'q75_deploy_time']),
                                 harm_rate=float(sub.loc[d, 'harm_rate'])) for d in ['paired', 'cross_arrival']}

    fig, ax = plt.subplots(figsize=(W, 2.6))
    lab = {'paired': 'Paired (shadow) design', 'cross_arrival': 'Cross-arrival design'}
    col = {'paired': C_BLUE, 'cross_arrival': C_ORANGE}
    grid_n = np.arange(0, n + 1)
    for d in ['paired', 'cross_arrival']:
        v = times[d]; ok = np.sort(v[~np.isnan(v)])
        ecdf = np.searchsorted(ok, grid_n, side='right') / reps  # fraction of replicates deployed by n
        ax.step(grid_n, ecdf, where='post', color=col[d], lw=1.6, zorder=3)
        med_r = rerun[d]['median']
        ax.plot([med_r, med_r], [0, np.searchsorted(ok, med_r, side='right') / reps], color=col[d], lw=0.8, ls=':', zorder=2)
        ax.text(n + 25, ecdf[-1], f'{lab[d]}\n{100*ecdf[-1]:.1f}% deployed', color=col[d], fontsize=7.3, va='center', weight='bold')
    grid(ax, 'both')
    ax.set_xlim(0, n); ax.set_ylim(0, 1.0)
    ax.set_yticks([0, .25, .5, .75, 1]); ax.set_yticklabels(['0', '25%', '50%', '75%', '100%'])
    ax.set_xlabel('Pairs observed n')
    ax.set_ylabel('Replicates deployed by n')
    c = KEY['replay_csv']
    note = ('Canonical run (replay_results.csv, 500 orders):\n'
            f'paired: {100*c["paired"]["deploy_rate"]:.1f}% deployed, median stop {c["paired"]["median"]:.0f} '
            f'(IQR {c["paired"]["q25"]:.0f}\u2013{c["paired"]["q75"]:.0f}), harm flags {100*c["paired"]["harm_rate"]:.1f}%\n'
            f'cross-arrival: {100*c["cross_arrival"]["deploy_rate"]:.1f}% deployed, median stop {c["cross_arrival"]["median"]:.0f} '
            f'(IQR {c["cross_arrival"]["q25"]:.0f}\u2013{c["cross_arrival"]["q75"]:.0f}), harm flags {100*c["cross_arrival"]["harm_rate"]:.1f}%\n'
            'Curves: independent re-run of the same replay (fresh seeds); dotted = re-run median stop')
    ax.text(0.0, -0.22, note, transform=ax.transAxes, fontsize=6.4, color=INK2, va='top', ha='left', linespacing=1.3)
    ax.set_title('Guarded betting e-process, o4-mini vs GPT-4.1 (tau2-bench, all domains): time to deployment', loc='left', fontsize=8)
    save(fig, 'fig_replay_stopping')


# ------------------------------------------------------------------ fig 2
def fig_example_stream():
    ex = pd.read_csv(RES / 'replay' / 'example_stream_cs.csv')
    KEY['example_stream'] = dict(n_final=int(ex.n.iloc[-1]), nb_hat=float(ex.nb_hat.iloc[-1]), nb_lo=float(ex.nb_lo.iloc[-1]),
                                 nb_hi=float(ex.nb_hi.iloc[-1]), succ_hat=float(ex.succ_hat.iloc[-1]),
                                 succ_lo=float(ex.succ_lo.iloc[-1]), succ_hi=float(ex.succ_hi.iloc[-1]),
                                 first_n_nb_lo_pos=int(ex.n[ex.nb_lo > 0].min()) if (ex.nb_lo > 0).any() else None,
                                 first_n_succ_lo_above=int(ex.n[ex.succ_lo > -0.03].min()) if (ex.succ_lo > -0.03).any() else None)
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.3), sharex=True, gridspec_kw=dict(wspace=0.28))
    panels = [('nb', 'Hierarchical net benefit', C_BLUE, 0.0, 'H$_0$ boundary: 0'),
              ('succ', 'Success-rate difference', C_ORANGE, -0.03, 'guardrail: $-$0.03')]
    for ax, (k, title, c, thr, thr_lab) in zip(axes, panels):
        ax.fill_between(ex.n, ex[f'{k}_lo'], ex[f'{k}_hi'], color=c, alpha=0.18, lw=0, zorder=2)
        ax.plot(ex.n, ex[f'{k}_lo'], color=c, lw=0.7, zorder=3); ax.plot(ex.n, ex[f'{k}_hi'], color=c, lw=0.7, zorder=3)
        ax.plot(ex.n, ex[f'{k}_hat'], color=c, lw=1.4, zorder=4)
        ax.axhline(thr, color=INK, lw=0.8, ls='--', zorder=3)
        ax.text(1990, thr + 0.012 if k == 'nb' else thr - 0.012, thr_lab, ha='right', va='bottom' if k == 'nb' else 'top', fontsize=7, color=INK)
        grid(ax)
        ax.set_title(title, loc='left')
        ax.set_ylim(-0.35, 0.45); ax.set_xlim(0, 2000)
        ax.set_xlabel('Pairs observed')
        last = ex.iloc[-1]
        ax.annotate(f'{last[f"{k}_hat"]:+.3f}\n[{last[f"{k}_lo"]:+.3f}, {last[f"{k}_hi"]:+.3f}]', xy=(2000, last[f'{k}_hat']),
                    xytext=(1150, 0.36), fontsize=7, color=INK2, ha='left', va='center',
                    arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.5))
    axes[0].set_ylabel('Running estimate')
    fig.suptitle('One replayed paired stream, o4-mini vs GPT-4.1 (tau2-bench, all domains): running estimate and 95% betting CS',
                 fontsize=7.5, color=INK2, y=1.04)
    save(fig, 'fig_example_stream')


# ------------------------------------------------------------------ fig 3
def fig_ranking_disagreement():
    rk = pd.read_csv(RES / 'benchmarks' / 'tau2_rankings.csv')
    crit = [('rank_success', 'Success'), ('rank_pass_all4', 'pass\nall-4'), ('rank_nb_sum', 'Net\nbenefit'),
            ('rank_scalar_lambda1', 'Succ.\n$-$cost'), ('rank_scalar_lambda0p3', 'Succ.\n$-$.3cost')]
    models = [('o4-mini-2025-04-16', 'o4-mini', C_BLUE), ('gpt-4.1-2025-04-14', 'GPT-4.1', C_ORANGE),
              ('claude-3-7-sonnet-20250219', 'Claude 3.7', C_AQUA)]
    doms = ['airline', 'retail', 'telecom']
    fig, axes = plt.subplots(1, 3, figsize=(W, 2.5), sharey=True, gridspec_kw=dict(wspace=0.08))
    x = np.arange(len(crit))
    top_changes = {}
    for ax, dom in zip(axes, doms):
        d = rk[rk.domain == dom].set_index('model')
        winners = [d[c].idxmin() for c, _ in crit]
        top_changes[dom] = [dict(zip([m for m, _, _ in models], [s for _, s, _ in models]))[w] for w in winners]
        n_unique = len(set(winners))
        for m, short, c in models:
            y = d.loc[m, [c for c, _ in crit]].to_numpy(float)
            ax.plot(x, y, color=c, lw=1.6, zorder=3, marker='o', ms=5, mec='white', mew=0.8)
            if dom == doms[-1]:
                ax.text(x[-1] + 0.12, y[-1], short, color=c, fontsize=6.6, va='center', ha='left', weight='bold', clip_on=False)
        # highlight where the top model changes across criteria
        for i in range(1, len(crit)):
            if winners[i] != winners[i - 1]:
                ax.axvline(i - 0.5, color=C_RED, lw=0.9, ls=':', zorder=1)
        ax.set_xticks(x); ax.set_xticklabels([l.replace('\n', ' ') for _, l in crit], fontsize=6, rotation=35, ha='right', rotation_mode='anchor')
        ax.set_facecolor('none')
        ax.set_yticks([1, 2, 3]); ax.set_ylim(3.35, 0.65)
        title = f'{dom}' + ('  (top model agrees)' if n_unique == 1 else f'  ({n_unique} different #1s)')
        ax.set_title(title, loc='left', fontsize=8, color=INK if n_unique > 1 else INK2)
        ax.set_xlim(-0.3, len(crit) - 0.6 if dom != doms[-1] else len(crit) + 0.6)
        grid(ax)
        for s in ['left']:
            ax.spines[s].set_visible(False)
        ax.tick_params(axis='y', length=0)
    axes[0].set_ylabel('Rank (1 = best)')
    axes[0].legend(handles=[Line2D([], [], color=c, marker='o', ms=4, lw=1.6, label=sh) for _, sh, c in models],
                   loc='lower left', bbox_to_anchor=(0.0, 1.13), ncol=3, fontsize=6.8, handlelength=1.6, columnspacing=1.0)
    fig.suptitle('tau2-bench: per-domain rank of three models under five criteria (dotted red: the #1 model changes)',
                 fontsize=7.5, color=INK2, y=1.2)
    KEY['top_by_domain'] = top_changes
    save(fig, 'fig_ranking_disagreement')


# ------------------------------------------------------------------ fig 4
def fig_hal_latency():
    hc = pd.read_csv(RES / 'benchmarks' / 'hal_contrasts.csv')
    short = {'HAL Generalist Agent (claude-3-7-sonnet-20250219)': 'Generalist / Claude 3.7',
             'HAL Generalist Agent (gpt-4.1-2025-04-14)': 'Generalist / GPT-4.1',
             'HAL Generalist Agent (o4-mini-2025-04-16 high)': 'Generalist / o4-mini',
             'Taubench ToolCalling (claude-3.7-sonnet)': 'ToolCalling / Claude 3.7',
             'Taubench ToolCalling (gpt-4.1-2025-04-14)': 'ToolCalling / GPT-4.1',
             'Taubench ToolCalling (o4-mini-2025-04-16 high)': 'ToolCalling / o4-mini'}
    p = hc[hc.label == 'primary'].reset_index(drop=True); q = hc[hc.label == 'success_latency_cost'].reset_index(drop=True)
    assert len(p) == 15 and len(q) == 15 and (p.A.values == q.A.values).all() and (p.B.values == q.B.values).all()
    order = np.argsort(-p.net_benefit.to_numpy())
    fig, ax = plt.subplots(figsize=(W, 3.6))
    y = np.arange(len(order))
    off = 0.18
    changed = []
    for i, j in enumerate(order):
        pa, pb = p.loc[j], q.loc[j]
        ax.plot([pa.nb_lo, pa.nb_hi], [i + off, i + off], color=C_BLUE, lw=1.2, zorder=3)
        ax.plot(pa.net_benefit, i + off, 'o', color=C_BLUE, ms=4.5, mec='white', mew=0.6, zorder=4)
        ax.plot([pb.nb_lo, pb.nb_hi], [i - off, i - off], color=C_ORANGE, lw=1.2, zorder=3)
        ax.plot(pb.net_benefit, i - off, 's', color=C_ORANGE, ms=4.2, mec='white', mew=0.6, zorder=4)
        if abs(pa.net_benefit - pb.net_benefit) > 1e-9:
            changed.append((short[pa.A], short[pa.B], float(pa.net_benefit), float(pb.net_benefit)))
            ax.text(0.86, i, f'{pa.net_benefit:+.2f} → {pb.net_benefit:+.2f}'.replace('-', '−'), fontsize=6.6, va='center', ha='left', color=INK2)
    ax.axvline(0, color=INK, lw=0.8, zorder=2)
    ax.set_yticks(y); ax.set_yticklabels([f'{short[p.loc[j].A]}  vs  {short[p.loc[j].B]}' for j in order], fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xlim(-0.8, 1.15)
    ax.set_xticks(np.arange(-0.8, 0.81, 0.4))
    ax.set_xlabel('Net benefit P(A wins) $-$ P(B wins), 95% CI  (A vs B, positive favours A)')
    grid(ax, 'x')
    ax.tick_params(axis='y', length=0)
    handles = [Line2D([], [], color=C_BLUE, marker='o', ms=4.5, lw=1.2, label='success > cost > steps (primary)'),
               Line2D([], [], color=C_ORANGE, marker='s', ms=4.2, lw=1.2, label='success > latency > cost')]
    ax.legend(handles=handles, loc='lower left', fontsize=7, handlelength=1.8, bbox_to_anchor=(0.0, 1.0), ncol=2, columnspacing=1.2)
    ax.text(0.86, -0.75, 'change (primary → latency)', fontsize=6.6, color=INK2, ha='left', va='center', style='italic')
    fig.suptitle('HAL taubench-airline: 6 agent configurations, 15 pairwise contrasts, two hierarchies', fontsize=8, x=0.5, y=0.99)
    KEY['hal_changed'] = changed
    save(fig, 'fig_hal_latency')


# ------------------------------------------------------------------ fig 5
def fig_cs_width():
    cw = pd.read_csv(RES / 'cs_width.csv')
    meth = [('betting_mixture_cs', 'Betting mixture CS', C_BLUE, '-'), ('normal_mixture_cs', 'Normal-mixture CS', C_ORANGE, '-'),
            ('multinomial_dirichlet_cs', 'Multinomial Dirichlet CS', C_AQUA, '-'),
            ('fixed_wald_ci_invalid_sequentially', 'Fixed-n Wald CI (not sequentially valid)', MUTED, '--')]
    fig, ax = plt.subplots(figsize=(W, 2.6))
    ratios = {}
    for m, lab, c, ls in meth:
        d = cw[cw.method == m].sort_values('n_pairs')
        ax.plot(d.n_pairs, d.mean_width, color=c, ls=ls, lw=1.5, marker='o', ms=3.5, mec='white', mew=0.5, zorder=3)
        ax.text(d.n_pairs.iloc[-1] * 1.12, d.mean_width.iloc[-1], lab, color=c if c != MUTED else INK2, fontsize=7, va='center')
        ratios[m] = {int(n): float(w) for n, w in zip(d.n_pairs, d.mean_width)}
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlim(80, 10000 * 6.5)
    ax.set_xticks([100, 250, 500, 1000, 2000, 5000, 10000]); ax.set_xticklabels(['100', '250', '500', '1k', '2k', '5k', '10k'])
    ax.set_yticks([0.03, 0.05, 0.1, 0.2, 0.4, 0.8]); ax.set_yticklabels(['0.03', '0.05', '0.1', '0.2', '0.4', '0.8'])
    ax.minorticks_off()
    grid(ax, 'both')
    ax.set_xlabel('Pairs observed n'); ax.set_ylabel('Mean 95% interval width for net benefit')
    ax.set_title('Confidence-sequence width vs sample size (200 replicates per n)', loc='left')
    KEY['cs_width'] = ratios
    save(fig, 'fig_cs_width')


# ------------------------------------------------------------------ fig 6
def fig_simplex_price(reps=400, nmax=10000, seed=60):
    streams = [('Rare-event compliance gate', (0.004975, 0.99005, 0.004975), -0.01),
               ('Success gate', (0.1875, 0.625, 0.1875), -0.03)]
    checkpoints = np.unique(np.round(np.geomspace(10, nmax, 60)).astype(int))
    rng = np.random.default_rng(seed)
    curves = {}
    for name, p, thr in streams:
        # cumulative counts at checkpoints for every replicate
        draws = rng.choice(3, size=(reps, nmax), p=p)
        cw = np.cumsum(draws == 0, 1)[:, checkpoints - 1]; cl = np.cumsum(draws == 2, 1)[:, checkpoints - 1]
        n = np.broadcast_to(checkpoints, cw.shape); ct = n - cw - cl
        out = {}
        out['Dirichlet (1,1,1)'] = ternary_log_eprocess_nb(cw, ct, cl, thr, (1, 1, 1)).mean(0)
        out['Dirichlet (½,½,½)'] = ternary_log_eprocess_nb(cw, ct, cl, thr, (0.5, 0.5, 0.5)).mean(0)
        out['Betting (40 bets)'] = betting_log_e_ternary(cw, cl, n, thr).mean(0)
        # first checkpoint at which the mean log e-process exceeds log(1/alpha)
        out_first = {k: (int(checkpoints[np.argmax(v >= LOG20)]) if (v >= LOG20).any() else None) for k, v in out.items()}
        curves[name] = (out, out_first)
    KEY['simplex'] = {name: dict(first_cross={k: v for k, v in f.items()}, at_n10000={k: float(v[-1]) for k, v in o.items()})
                      for name, (o, f) in curves.items()}
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.4), gridspec_kw=dict(wspace=0.3))
    cols = {'Betting (40 bets)': C_BLUE, 'Dirichlet (1,1,1)': C_ORANGE, 'Dirichlet (½,½,½)': C_AQUA}
    for ax, (name, p, thr) in zip(axes, streams):
        out, first = curves[name]
        for k, v in out.items():
            ax.plot(checkpoints, v, color=cols[k], lw=1.5, zorder=3)
        ax.axhline(LOG20, color=INK, lw=0.8, ls='--', zorder=2)
        ax.text(11, LOG20 + 0.25, r'log(1/$\alpha$) = log 20', fontsize=7, va='bottom')
        ax.set_xscale('log'); grid(ax, 'both')
        ax.set_title(f'{name}\n(win, tie, loss) = ({p[0]:.3g}, {p[1]:.3g}, {p[2]:.3g})\nH$_0$: net benefit $\\leq$ {str(thr).replace("-", chr(8722))}', loc='left', fontsize=6.8)
        ax.set_xlabel('Pairs observed n')
        ax.set_xlim(10, nmax)
        ax.minorticks_off(); ax.set_xticks([10, 100, 1000, 10000]); ax.set_xticklabels(['10', '100', '1k', '10k'])
    ymax = max(np.nanmax(v) for o, _ in curves.values() for v in o.values())
    ymin = min(np.nanmin(v) for o, _ in curves.values() for v in o.values())
    for ax in axes:
        ax.set_ylim(min(ymin, -1) - 0.5, ymax + 1.5)
    axes[0].set_ylabel('Mean log e-process (400 replicates)')
    # legend with direct labels on the second panel (all curves visible)
    out, _ = curves[streams[1][0]]
    handles = [Line2D([], [], color=cols[k], lw=1.5, label=k) for k in out]
    axes[1].legend(handles=handles, loc='upper left', fontsize=7, handlelength=1.6)
    save(fig, 'fig_simplex_price')


# ------------------------------------------------------------------ fig 7
def fig_online_methods():
    om = pd.read_csv(RES / 'online_methods_results.csv', keep_default_na=False)  # scenario 'null' must stay a string
    methods = [('guarded_betting', 'Guarded betting'), ('guarded_multinomial', 'Guarded Dirichlet-multinomial'),
               ('guarded_normal_mixture', 'Guarded normal-mixture'), ('guarded_group_bonferroni_wald', 'Guarded group-Bonferroni Wald'),
               ('guarded_repeated_wald', 'Guarded repeated Wald (naive)'), ('guarded_fixed_wald', 'Guarded fixed-n Wald')]
    scen_ok = ['efficiency_gain', 'joint_gain', 'tie_heavy_efficiency', 'weak_gain']
    scen_bad = ['null', 'tie_heavy_null', 'success_regression', 'safety_regression']
    nice = {'efficiency_gain': 'Efficiency gain', 'joint_gain': 'Joint gain', 'tie_heavy_efficiency': 'Tie-heavy efficiency gain',
            'weak_gain': 'Weak gain (nb = 0.01)', 'null': 'Null', 'tie_heavy_null': 'Tie-heavy null',
            'success_regression': 'Success regression', 'safety_regression': 'Safety regression'}
    fig, axes = plt.subplots(4, 2, figsize=(W, 4.6), sharex=True, gridspec_kw=dict(wspace=0.16, hspace=0.45))
    y = np.arange(len(methods))[::-1]
    table = {}
    for col, (scens, colour, head) in enumerate([(scen_ok, C_AQUA, 'Admissible: should deploy'),
                                                  (scen_bad, C_RED, 'Inadmissible: should NOT deploy')]):
        for row, s in enumerate(scens):
            ax = axes[row, col]
            d = om[om.scenario == s].set_index('method')
            rates = d.loc[[m for m, _ in methods], 'deployment_rate'].to_numpy(float)
            lo = d.loc[[m for m, _ in methods], 'rate_ci_lower'].to_numpy(float); hi = d.loc[[m for m, _ in methods], 'rate_ci_upper'].to_numpy(float)
            table[s] = {m: float(r) for (m, _), r in zip(methods, rates)}
            ax.barh(y, rates, color=colour, height=0.62, zorder=3)
            ax.errorbar(rates, y, xerr=[np.clip(rates - lo, 0, None), np.clip(hi - rates, 0, None)], fmt='none', ecolor=INK2, elinewidth=0.6, capsize=0, zorder=4)
            for yy, r, h in zip(y, rates, hi):
                xt = max(h + 0.015, 0.075) if col == 1 else h + 0.015
                ax.text(xt if r < 0.85 else r - 0.02, yy, f'{100*r:.1f}%', fontsize=6.3, va='center',
                        ha='left' if r < 0.85 else 'right', color=INK if r < 0.85 else 'white')
            if col == 1:
                ax.axvline(0.05, color=INK, lw=0.7, ls='--', zorder=2)
            ax.set_xlim(0, 1.0); ax.set_yticks(y)
            ax.set_yticklabels([l for _, l in methods] if col == 0 else [], fontsize=6.6)
            ax.tick_params(axis='y', length=0)
            ax.set_title(nice[s], loc='left', fontsize=7.5, pad=2)
            grid(ax, 'x')
            ax.spines['left'].set_visible(False)
        axes[0, col].text(0, 1.45, head, transform=axes[0, col].transAxes, fontsize=8, weight='bold',
                          color=colour if col == 0 else C_RED)
    for ax in axes[-1]:
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_xticklabels(['0', '25%', '50%', '75%', '100%'])
    fig.text(0.5, 0.045, r'Deployment rate with 95% CI (2000 replicates, cap 10 000 pairs); dashed line = nominal $\alpha$ = 5%', ha='center', fontsize=7.5)
    KEY['online'] = table
    save(fig, 'fig_online_methods')


def main():
    t0 = time.time()
    inputs = ['results/replay/replay_results.csv', 'results/replay/example_stream_cs.csv', 'results/benchmarks/tau2_rankings.csv',
              'results/benchmarks/hal_contrasts.csv', 'results/cs_width.csv', 'results/online_methods_results.csv']
    hashes0 = {p: sha(ROOT / p) for p in inputs}
    fig_example_stream(); fig_ranking_disagreement(); fig_hal_latency(); fig_cs_width(); fig_online_methods()
    fig_simplex_price(); fig_replay_stopping()
    hashes1 = {p: sha(ROOT / p) for p in inputs}
    changed = [p for p in inputs if hashes0[p] != hashes1[p]]
    if changed:  # inputs regenerated by a background job during the run -> redo
        print('inputs changed during run, regenerating:', changed, flush=True)
        return main()
    (OUT / 'figure_numbers.json').write_text(json.dumps(dict(inputs_sha256=hashes1, key_numbers=KEY, seconds=time.time() - t0), indent=2, default=str))
    print('done in %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
