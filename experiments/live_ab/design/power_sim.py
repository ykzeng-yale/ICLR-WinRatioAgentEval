#!/usr/bin/env python
"""R4: pilot-based power simulation for the prospective, physically randomized,
single-exposure, live-stopped A/B trial (CPU only, no model calls).

PILOT DATA (read-only): results/local_stream/episodes_flat.csv, 591 tasks x 2 arms
(single_shot, self_test_repair), one run per task and arm.

LIBRARY (read-only import from src/winstats.py, root-owned):
  Tier, compare                -> hierarchical pair score (success > latency 10% > tokens 10%,
                                  lower tiers eligible only when both episodes succeeded,
                                  exactly as experiments/build_open_coding_results.py::score)
  betting_log_e_ternary        -> fixed-stake-grid betting e-process (paper thm:betting,
                                  prop:bet_running)
  normal_mixture_radius        -> two-sided normal-mixture confidence sequence (thm:normal_cs)
Nothing is re-implemented from the library.  What is implemented here (because the library
has no such function) is only: the trial simulator, the first-crossing logic of the guarded
rule (paper eq:deploy_rule, current-look implementation), and a 2-worker timing model.

SIMULATED DESIGN
  * tasks arrive in a random order (perm: the 591 pilot tasks, each once; boot: tasks drawn
    with replacement from the pilot, N=591 or N=1138);
  * physical randomization, two variants:
      pair_coin    : ROOT design (paper sec. "A randomized disjoint-pair design", thm:pair_id):
                     consecutive disjoint arrival pairs, ONE fair coin per pair gives the
                     orientation; exactly floor(N/2) pairs (295 / 569);
      arrival_coin : coordinator wording: one fair coin per arrival, pair k = k-th candidate
                     arrival with k-th incumbent arrival; the number of pairs is random
                     (min(nA,nB) < N/2);
    every task is executed under ONE arm only; the outcome is the pilot outcome of that task
    under that arm (resampling plug-in);
  * monitor = completed enrollment prefix of pairs; looks at every pair n >= min_n;
      (i)  win   : betting_log_e_ternary(pos, neg, n, 0)          H0: NB <= 0
      (ii) guard : betting_log_e_ternary(qpos, qneg, n, -delta)   H0: success diff <= -delta
      (iii) harm : betting_log_e_ternary(neg, pos, n, 0)          H0: NB >= 0
    guarded deploy at the first look where (i) and (ii) are both >= their thresholds
    (current look, as in the paper); harm stop at the first look where (iii) crosses.
    A second monitor family uses the root normal-mixture CS (rho=100) the same way.
  * live stopping: after the decision every arrival not yet started runs under the decided
    arm.  Timing: W=2 workers, arrival i starts when a worker is free, duration = pilot
    latency; decision time = time at which the prefix of tau pairs is fully resolved.

ALPHA SCHEMES (a_win, a_guard, a_harm), alpha = 0.05
  nosplit_iut     (.05, .05, .05)      paper thm:iut, stationary conjunction (pilot's rule)
  deploy_bonf2    (.025,.025,.05)      paper thm:drift_gate (running-average targets)
  twosided_equal  (.025,.025,.025)     equal split deploy direction / harm direction
  bonf3           (.05/3 each)         Bonferroni over the three monitored processes
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]   # <repo>/experiments/live_ab/design/power_sim.py
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / 'src'))
from winstats import Tier, compare, betting_log_e_ternary, normal_mixture_radius  # noqa: E402

TIERS = (Tier('success', True, 0.0, 0.0),
         Tier('latency_s', False, 0.0, 0.10),
         Tier('completion_tokens', False, 0.0, 0.10))
ALPHA = 0.05
SCHEMES = {
    'nosplit_iut': (ALPHA, ALPHA, ALPHA),
    'deploy_bonf2': (ALPHA / 2, ALPHA / 2, ALPHA),
    'twosided_equal': (ALPHA / 2, ALPHA / 2, ALPHA / 2),
    'bonf3': (ALPHA / 3, ALPHA / 3, ALPHA / 3),
}
DELTAS = (0.03, 0.05, 0.10, 0.15)
MIN_NS = (10, 20)
RHO = 100.0
WORKERS = 2
TRIALS = {  # name: (incumbent arm, candidate arm, inferior arm role or None)
    'T1': ('self_test_repair', 'single_shot', 'incumbent'),
    'T2': ('single_shot', 'self_test_repair', 'candidate'),
    'T4': ('single_shot', 'single_shot', None),
}
BASE_SEED = 20260919


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_pilot():
    d = pd.read_csv(REPO / 'results/local_stream/episodes_flat.csv')
    assert len(d) == 1182 and d.task_id.nunique() == 591
    tasks = np.sort(d.task_id.unique())
    arms = {}
    for arm in ('single_shot', 'self_test_repair'):
        s = d[d.variant == arm].set_index('task_id').loc[tasks]
        assert len(s) == 591
        arms[arm] = dict(succ=s.success.astype(int).to_numpy(),
                         lat=s.latency_s.astype(float).to_numpy(),
                         tok=s.completion_tokens.astype(float).to_numpy())
    return d, tasks, arms


def pair_scores(sc, lc, tc, si, li, ti):
    """Candidate-vs-incumbent hierarchical score and success difference (library compare)."""
    a = np.stack([sc, lc, tc], -1).astype(float)
    b = np.stack([si, li, ti], -1).astype(float)
    both = (sc > 0) & (si > 0)
    elig = np.stack([np.ones_like(both), both, both], -1)
    z, _ = compare(a, b, TIERS, elig)
    return z.astype(np.int8), (sc - si).astype(np.int8)


def check_against_root(d):
    """Reproduce the root E1 counts (69 wins, 18 ties, 208 losses of B vs A, pass-1 pairs)."""
    p1 = d[(d['pass'] == 1) & d.pair_index.notna()]
    a = p1[p1.variant_letter == 'A'].set_index('pair_index').sort_index()
    b = p1[p1.variant_letter == 'B'].set_index('pair_index').sort_index()
    idx = a.index.intersection(b.index)
    a, b = a.loc[idx], b.loc[idx]
    z, _ = pair_scores(b.success.astype(int).to_numpy(), b.latency_s.to_numpy(), b.completion_tokens.to_numpy(),
                       a.success.astype(int).to_numpy(), a.latency_s.to_numpy(), a.completion_tokens.to_numpy())
    got = (int((z > 0).sum()), int((z == 0).sum()), int((z < 0).sum()))
    assert got == (69, 18, 208), got
    return got


def population_targets(arms):
    """Plug-in population values over ordered pairs of DIFFERENT tasks."""
    out = {}
    n = 591
    off = ~np.eye(n, dtype=bool)
    for name, (inc, cand, _) in TRIALS.items():
        c, i = arms[cand], arms[inc]
        z, dd = pair_scores(c['succ'][:, None] * np.ones((1, n), int), c['lat'][:, None] * np.ones((1, n)),
                            c['tok'][:, None] * np.ones((1, n)),
                            i['succ'][None, :] * np.ones((n, 1), int), i['lat'][None, :] * np.ones((n, 1)),
                            i['tok'][None, :] * np.ones((n, 1)))
        z, dd = z[off], dd[off]
        out[name] = dict(p_win=float((z > 0).mean()), p_tie=float((z == 0).mean()), p_loss=float((z < 0).mean()),
                         net_benefit=float(z.mean()), success_diff=float(dd.mean()),
                         p_succdiff_pos=float((dd > 0).mean()), p_succdiff_neg=float((dd < 0).mean()))
    return out


def oracle_growth(pp, pn, c, grid=np.geomspace(1e-4, .99, 4000)):
    """Best constant-stake expected log growth for ternary score, H0 mean <= c (analytic check)."""
    lam = grid[grid < .99 / (1 + c)]
    g = pp * np.log1p(lam * (1 - c)) + pn * np.log1p(lam * (-1 - c)) + (1 - pp - pn) * np.log1p(-lam * c)
    j = g.argmax()
    return float(g[j]), float(lam[j])


def first_true(cond):
    idx = cond.argmax(1)
    return np.where(cond.any(1), idx, -1)


def simulate_chunk(rng, r, arms, trial, design, resample, N, shift, timing=True):
    """Return per-chunk arrays needed to evaluate every monitoring configuration."""
    inc_arm, cand_arm, _ = TRIALS[trial]
    P = 591
    H = N // 2
    if resample == 'perm':
        assert N == P
        tasks = np.argsort(rng.random((r, P)), axis=1)
    else:
        tasks = rng.integers(0, P, (r, N))
    ar = np.arange(r)
    if design == 'pair_coin':
        c = rng.random((r, H)) < .5                      # True: first position -> candidate
        cand = np.zeros((r, N), bool)
        cand[:, 0:2 * H:2] = c
        cand[:, 1:2 * H:2] = ~c
        if N % 2:
            cand[:, -1] = rng.random(r) < .5
        even = np.arange(0, 2 * H, 2)[None, :]
        pos_c = np.where(c, even, even + 1)
        pos_i = np.where(c, even + 1, even)
        K = np.full(r, H)
    else:
        cand = rng.random((r, N)) < .5
        pos_c = np.argsort(~cand, axis=1, kind='stable')[:, :H]
        pos_i = np.argsort(cand, axis=1, kind='stable')[:, :H]
        nc = cand.sum(1)
        K = np.minimum(nc, N - nc)
    C, I = arms[cand_arm], arms[inc_arm]
    s_c_all, s_i_all = C['succ'][tasks].copy(), I['succ'][tasks]
    # sensitivity: shift the candidate's true success rate (independent flips per episode)
    if shift is not None:
        sh = shift if np.ndim(shift) else np.full(r, float(shift))
        p_c = C['succ'].mean()
        u = rng.random((r, N))
        down = (sh < 0)[:, None] & (s_c_all == 1) & (u < (np.abs(sh) / p_c)[:, None])
        up = (sh > 0)[:, None] & (s_c_all == 0) & (u < (np.abs(sh) / (1 - p_c))[:, None])
        s_c_all[down] = 0
        s_c_all[up] = 1
    l_c_all, l_i_all = C['lat'][tasks], I['lat'][tasks]
    t_c_all, t_i_all = C['tok'][tasks], I['tok'][tasks]
    g = lambda x, pos: np.take_along_axis(x, pos, 1)
    z, dd = pair_scores(g(s_c_all, pos_c), g(l_c_all, pos_c), g(t_c_all, pos_c),
                        g(s_i_all, pos_i), g(l_i_all, pos_i), g(t_i_all, pos_i))
    valid = np.arange(H)[None, :] < K[:, None]
    z = np.where(valid, z, 0)
    dd = np.where(valid, dd, 0)
    out = dict(z=z, d=dd, valid=valid, K=K, cand=cand, N=N, H=H)
    if timing:
        lat = np.where(cand, l_c_all, l_i_all)
        free = np.zeros((r, WORKERS))
        start = np.empty((r, N))
        for i in range(N):
            w = free.argmin(1)
            st = free[ar, w]
            start[:, i] = st
            free[ar, w] = st + lat[:, i]
        finish = start + lat
        pair_done = np.maximum(g(finish, pos_c), g(finish, pos_i))
        pair_done = np.where(valid, pair_done, np.inf)
        out.update(start=start, prefix_done=np.maximum.accumulate(pair_done, axis=1),
                   cs_lat=np.cumsum(lat, 1), cs_lc=np.cumsum(l_c_all, 1), cs_li=np.cumsum(l_i_all, 1))
    return out


def monitors(ch):
    """All monitored statistics, library functions only."""
    z, dd, valid = ch['z'], ch['d'], ch['valid']
    n = np.minimum(np.arange(1, ch['H'] + 1)[None, :], np.maximum(ch['K'], 1)[:, None])
    pos, neg = np.cumsum(z > 0, 1), np.cumsum(z < 0, 1)
    qp, qn = np.cumsum(dd > 0, 1), np.cumsum(dd < 0, 1)
    m = dict(n=n,
             le_win=betting_log_e_ternary(pos, neg, n, 0.0),
             le_harm=betting_log_e_ternary(neg, pos, n, 0.0),
             le_guard={dl: betting_log_e_ternary(qp, qn, n, -dl) for dl in DELTAS},
             mean_z=(pos - neg) / n, mean_d=(qp - qn) / n)
    return m


def evaluate(ch, m, trial, methods=('betting', 'normal_mixture'), timing=True):
    """First-crossing decisions for every configuration; returns dict key -> per-replicate arrays."""
    res = {}
    n, valid = m['n'], ch['valid']
    r, N, H = valid.shape[0], ch['N'], ch['H']
    ar = np.arange(r)
    inferior = TRIALS[trial][2]
    cs_c = np.cumsum(ch['cand'], 1)
    for method in methods:
        for sname, (aw, ag, ah) in SCHEMES.items():
            if method == 'betting':
                win = m['le_win'] >= np.log(1 / aw)
                harm = m['le_harm'] >= np.log(1 / ah)
            else:
                win = m['mean_z'] - normal_mixture_radius(n, aw, RHO) > 0
                harm = m['mean_z'] + normal_mixture_radius(n, ah, RHO) < 0
            for dl in DELTAS:
                if method == 'betting':
                    guard = m['le_guard'][dl] >= np.log(1 / ag)
                else:
                    guard = m['mean_d'] - normal_mixture_radius(n, ag, RHO) > -dl
                for mn in MIN_NS:
                    ok = valid & (n >= mn)
                    t_dep = first_true(win & guard & ok)
                    t_harm = first_true(harm & ok)
                    # retained-evidence variant (paper: optional, stationary claims only)
                    t_dep_ret = first_true(np.maximum.accumulate(win & ok, 1) & np.maximum.accumulate(guard & ok, 1))
                    big = H + 5
                    td = np.where(t_dep < 0, big, t_dep)
                    th = np.where(t_harm < 0, big, t_harm)
                    dec = np.where((td == big) & (th == big), 0, np.where(th <= td, -1, 1)).astype(np.int8)
                    tau = np.where(dec == 0, -1, np.minimum(td, th))
                    tdr = np.where(t_dep_ret < 0, big, t_dep_ret)
                    dec_ret = np.where((tdr == big) & (th == big), 0, np.where(th <= tdr, -1, 1)).astype(np.int8)
                    rec = dict(dec=dec, tau=tau.astype(np.int32), dec_ret=dec_ret,
                               win_ever=(win & ok).any(1), guard_ever=(guard & ok).any(1),
                               harm_ever=(harm & ok).any(1))
                    if timing:
                        tstar = np.where(dec == 0, np.inf, ch['prefix_done'][ar, np.maximum(tau, 0)])
                        started = (ch['start'] < tstar[:, None]).sum(1)           # arrivals already exposed
                        remaining = N - started
                        ncand_started = np.where(started > 0, cs_c[ar, np.maximum(started - 1, 0)], 0)
                        rem_cand = cs_c[:, -1] - ncand_started                     # counterfactual coins
                        rem_inc = remaining - rem_cand
                        if inferior == 'incumbent':      # correct decision = deploy
                            saved = np.where(dec == 1, rem_inc, np.where(dec == -1, -rem_cand, 0))
                            n_inferior_nostop = N - cs_c[:, -1]
                        elif inferior == 'candidate':    # correct decision = harm stop
                            saved = np.where(dec == -1, rem_cand, np.where(dec == 1, -rem_inc, 0))
                            n_inferior_nostop = cs_c[:, -1]
                        else:
                            saved = np.zeros(r)
                            n_inferior_nostop = np.zeros(r)
                        tot = ch['cs_lat'][:, -1]
                        idx = np.maximum(started - 1, 0)
                        pre = np.where(started > 0, ch['cs_lat'][ar, idx], 0.)
                        post_c = ch['cs_lc'][:, -1] - np.where(started > 0, ch['cs_lc'][ar, idx], 0.)
                        post_i = ch['cs_li'][:, -1] - np.where(started > 0, ch['cs_li'][ar, idx], 0.)
                        with_stop = np.where(dec == 0, tot, pre + np.where(dec == 1, post_c, post_i))
                        rec.update(started=started, remaining=remaining, saved=saved,
                                   n_inferior_nostop=n_inferior_nostop, lat_nostop=tot, lat_stop=with_stop)
                    res[(method, sname, dl, mn)] = rec
    return res


def summarize(key, recs, meta, R):
    method, sname, dl, mn = key
    cat = {k: np.concatenate([x[k] for x in recs]) for k in recs[0]}
    dec, tau = cat['dec'], cat['tau'] + 1          # 1-based pair index
    H = meta['horizon_pairs']
    aw, ag, ah = SCHEMES[sname]
    p_dep, p_harm = float((dec == 1).mean()), float((dec == -1).mean())
    stopped = dec != 0
    cens = np.where(stopped, tau, H + 1).astype(float)
    q = lambda x, p: float(np.quantile(x, p)) if len(x) else np.nan
    cq = [np.quantile(cens, p) for p in (.25, .5, .75)]
    cq = [float(v) if v <= H else np.nan for v in cq]        # nan = quantile lies beyond the horizon
    row = dict(meta)
    row.update(method=method, alpha_scheme=sname, alpha_win=aw, alpha_guard=ag, alpha_harm=ah, delta=dl, min_n=mn,
               reps=R, p_deploy=p_dep, p_harm_stop=p_harm, p_any_decision=float(stopped.mean()),
               se_p_deploy=float(np.sqrt(p_dep * (1 - p_dep) / R)), se_p_harm=float(np.sqrt(p_harm * (1 - p_harm) / R)),
               p_deploy_retained_variant=float((cat['dec_ret'] == 1).mean()),
               p_win_gate_ever=float(cat['win_ever'].mean()), p_guard_gate_ever=float(cat['guard_ever'].mean()),
               p_harm_gate_ever=float(cat['harm_ever'].mean()),
               stop_pair_q25_given_stop=q(tau[stopped], .25), stop_pair_median_given_stop=q(tau[stopped], .5),
               stop_pair_q75_given_stop=q(tau[stopped], .75),
               stop_pair_q25_censored=cq[0], stop_pair_median_censored=cq[1], stop_pair_q75_censored=cq[2],
               deploy_pair_median=q(tau[dec == 1], .5), harm_pair_median=q(tau[dec == -1], .5))
    if 'saved' in cat:
        N = meta['n_tasks']
        row.update(mean_frac_arrivals_after_decision=float(cat['remaining'].mean() / N),
                   exp_frac_arrivals_saved_from_inferior=float(cat['saved'].mean() / N),
                   exp_frac_of_inferior_exposures_avoided=(float(cat['saved'].mean() / cat['n_inferior_nostop'].mean())
                                                           if cat['n_inferior_nostop'].mean() > 0 else np.nan),
                   exp_frac_latency_saved=float(1 - cat['lat_stop'].mean() / cat['lat_nostop'].mean()),
                   median_arrivals_started_at_decision_given_stop=q(cat['started'][stopped], .5))
    return row


def run_cell(arms, trial, design, resample, N, shift, shift_label, R, chunk, seed_words, methods, pred_se=None):
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED] + list(seed_words)))
    recs = {}
    Ks = []
    done = 0
    while done < R:
        r = min(chunk, R - done)
        sh = shift
        if shift_label == 'predictive':
            sh = rng.normal(0., pred_se, r)
        ch = simulate_chunk(rng, r, arms, trial, design, resample, N, sh)
        m = monitors(ch)
        for k, v in evaluate(ch, m, trial, methods).items():
            recs.setdefault(k, []).append(v)
        Ks.append(ch['K'])
        done += r
    Ks = np.concatenate(Ks)
    meta = dict(trial=trial, incumbent=TRIALS[trial][0], candidate=TRIALS[trial][1], design=design,
                resample=resample, n_tasks=N, horizon_pairs=N // 2, success_shift=shift_label,
                mean_pairs_available=float(Ks.mean()), min_pairs_available=int(Ks.min()))
    return [summarize(k, v, meta, R) for k, v in recs.items()]


def required_horizon(arms, R, H, chunk, deltas=DELTAS):
    """T1, pair_coin, bootstrap, betting: quantiles of the first guarded-deploy look on a long horizon."""
    rows = []
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED, 777, H]))
    taus = {(s, dl): [] for s in SCHEMES for dl in deltas}
    gaus = {(s, dl): [] for s in SCHEMES for dl in deltas}
    done = 0
    while done < R:
        r = min(chunk, R - done)
        ch = simulate_chunk(rng, r, arms, 'T1', 'pair_coin', 'boot', 2 * H, None, timing=False)
        m = monitors(ch)
        ok = m['n'] >= 20
        for s, (aw, ag, ah) in SCHEMES.items():
            win = m['le_win'] >= np.log(1 / aw)
            for dl in deltas:
                guard = m['le_guard'][dl] >= np.log(1 / ag)
                taus[(s, dl)].append(first_true(win & guard & ok))
                gaus[(s, dl)].append(first_true(guard & ok))
        done += r
    for (s, dl), v in taus.items():
        t = np.concatenate(v).astype(float) + 1
        t[t == 0] = np.inf
        gq = np.concatenate(gaus[(s, dl)]).astype(float) + 1
        gq[gq == 0] = np.inf
        qs = {f'pairs_for_power_{int(p * 100)}': (float(np.quantile(t, p)) if np.quantile(t, p) < np.inf else np.nan)
              for p in (.5, .8, .9)}
        rows.append(dict(trial='T1', design='pair_coin', resample='boot', method='betting', alpha_scheme=s, delta=dl,
                         min_n=20, reps=R, max_horizon_pairs=H, p_deploy_by_max_horizon=float(np.isfinite(t).mean()),
                         **qs))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', required=True, choices=['T1', 'T2', 'T4', 'sens', 'long', 'merge'])
    ap.add_argument('--reps', type=int, default=10000)
    ap.add_argument('--chunk', type=int, default=500)
    ap.add_argument('--long-reps', type=int, default=2000)
    ap.add_argument('--long-horizon', type=int, default=8000)
    a = ap.parse_args()
    t0 = time.time()
    if a.part == 'merge':
        parts = [pd.read_csv(OUT / f'power_part_{p}.csv') for p in ('T1', 'T2', 'T4', 'sens')]
        pd.concat(parts, ignore_index=True).to_csv(OUT / 'power_results.csv', index=False)
        print('merged', sum(len(p) for p in parts), 'rows')
        return
    d, tasks, arms = load_pilot()
    e1 = check_against_root(d)
    disc = pd.crosstab(d[d.variant == 'single_shot'].set_index('task_id').success,
                       d[d.variant == 'self_test_repair'].set_index('task_id').success)
    b, c = int(disc.loc[True, False]), int(disc.loc[False, True])
    pred_se = float(np.sqrt(b + c) / 591)
    cells = [('perm', 591), ('boot', 591), ('boot', 1138)]
    rows = []
    if a.part in TRIALS:
        ti = list(TRIALS).index(a.part)
        for di, design in enumerate(('pair_coin', 'arrival_coin')):
            for ci, (resample, N) in enumerate(cells):
                rows += run_cell(arms, a.part, design, resample, N, None, 'none', a.reps, a.chunk,
                                 [ti, di, ci, 0], ('betting', 'normal_mixture'))
                print(a.part, design, resample, N, f'{time.time() - t0:.0f}s', flush=True)
        pd.DataFrame(rows).to_csv(OUT / f'power_part_{a.part}.csv', index=False)
    elif a.part == 'sens':
        shifts = [(-0.03, 'cand_-0.03'), (-0.02, 'cand_-0.02'), (0.02, 'cand_+0.02'), (None, 'predictive')]
        for ti, trial in enumerate(('T1', 'T2')):
            for ci, (resample, N) in enumerate(cells[1:]):
                for si, (sh, lab) in enumerate(shifts):
                    rows += run_cell(arms, trial, 'pair_coin', resample, N, sh, lab, a.reps, a.chunk,
                                     [ti, 9, ci, si + 1], ('betting',), pred_se=pred_se)
                    print('sens', trial, resample, N, lab, f'{time.time() - t0:.0f}s', flush=True)
        pd.DataFrame(rows).to_csv(OUT / 'power_part_sens.csv', index=False)
    elif a.part == 'long':
        lr = required_horizon(arms, a.long_reps, a.long_horizon, 100)
        pd.DataFrame(lr).to_csv(OUT / 'power_required_horizon.csv', index=False)
        pop = population_targets(arms)
        p = arms['single_shot']['succ'].mean()
        q = p * (1 - p)
        orc = []
        for dl in DELTAS:
            gstar, lam = oracle_growth(q, q, -dl)
            for s, (aw, ag, ah) in SCHEMES.items():
                orc.append(dict(delta=dl, alpha_scheme=s, alpha_guard=ag, oracle_growth_per_pair=gstar,
                                oracle_lambda=lam, pairs_oracle=float(np.log(1 / ag) / gstar),
                                pairs_grid_mixture_upper=float((np.log(1 / ag) + np.log(40)) / gstar)))
        summary = dict(pilot_episodes_flat_sha256=sha256(REPO / 'results/local_stream/episodes_flat.csv'),
                       pilot_episodes_jsonl_sha256=sha256(REPO / 'results/local_stream/episodes.jsonl'),
                       winstats_sha256=sha256(REPO / 'src/winstats.py'),
                       root_e1_counts_reproduced=e1, pilot_success={k: int(v['succ'].sum()) for k, v in arms.items()},
                       pilot_same_task_discordant=dict(ss_only=b, str_only=c), predictive_se_success_diff=pred_se,
                       population_targets_cross_task=pop, guard_oracle=orc, base_seed=BASE_SEED,
                       workers=WORKERS, rho=RHO, alpha=ALPHA, schemes=SCHEMES)
        (OUT / 'power_summary.json').write_text(json.dumps(summary, indent=2))
    print('done', a.part, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
