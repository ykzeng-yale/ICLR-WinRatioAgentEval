"""Sequential replay of real agent runs as randomized evaluation streams.

Streams are built from historical offline runs (tau2-bench, HAL airline); each
replay draws tasks in random order. Two observation designs are replayed:
  * paired (shadow): both systems run the SAME task (one random run each);
  * cross-arrival: each arrival's pair uses independent task draws for A and B.
At every arrival the guarded betting e-processes (net benefit > 0 AND success
non-inferiority at margin 0.03) are updated; stopping times and decisions are
recorded over many random orders. Results describe statistical operation under
replay of a finite pool; they are not live production A/B outcomes.
A semi-synthetic 'completion-order' stress test multiplies failure durations of
one arm to show the selection bias of analysing pairs in completion order.
"""
import json, sys, hashlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare, betting_log_e_ternary
from wincs import betting_cs_ternary
SRC = ROOT / 'work' / 'empirical_sources'; OUT = ROOT / 'results' / 'replay'; OUT.mkdir(parents=True, exist_ok=True)
ALPHA = 0.05; MARGIN = 0.03


def load_tau2():
    df = pd.read_csv(SRC / 'tau2_runs.csv')
    df = df[(df.config == 'default') & df.domain.isin(['airline', 'retail', 'telecom'])].copy()
    df['success'] = (df.reward >= 1 - 1e-9).astype(float)
    df = df.rename(columns={'agent_cost': 'cost', 'n_assistant_tool_calls': 'steps'})
    return df


def pools(df, model, domains):
    d = df[(df.model == model) & df.domain.isin(domains)]
    out = {}
    for (dom, t), g in d.groupby(['domain', 'task_id']):
        out[(dom, t)] = g[['success', 'cost', 'steps', 'duration']].to_numpy(float)
    return out


TIERS = [Tier('success'), Tier('cost', False, relative_tolerance=0.05), Tier('steps', False)]


def score_pairs(A, B):
    """A, B: (n, 4) outcome rows -> hierarchical ternary score and success diff."""
    elig = np.ones((len(A), 3), bool); both = (A[:, 0] > .5) & (B[:, 0] > .5); elig[:, 1:] = both[:, None]
    z, _ = compare(A[:, :3], B[:, :3], TIERS, elig)
    return z.astype(int), (A[:, 0] - B[:, 0]).astype(int)


def stream(rng, PA, PB, n, design):
    keys = sorted(set(PA) & set(PB))
    idx = rng.integers(0, len(keys), n)
    A = np.stack([PA[keys[i]][rng.integers(0, len(PA[keys[i]]))] for i in idx])
    if design == 'paired':
        B = np.stack([PB[keys[i]][rng.integers(0, len(PB[keys[i]]))] for i in idx])
    else:
        jdx = rng.integers(0, len(keys), n)
        B = np.stack([PB[keys[j]][rng.integers(0, len(PB[keys[j]]))] for j in jdx])
    return A, B


def run_guarded(z, dq, alpha=ALPHA, margin=MARGIN, min_n=50):
    n = np.arange(1, len(z) + 1)
    pos = np.cumsum(z > 0); neg = np.cumsum(z < 0); qp = np.cumsum(dq > 0); qn = np.cumsum(dq < 0)
    e_win = betting_log_e_ternary(pos, neg, n, 0.0) >= np.log(1 / alpha)
    e_gate = betting_log_e_ternary(qp, qn, n, -margin) >= np.log(1 / alpha)
    # NB harmful check (two-sided reporting): e-process for H0: nb >= 0
    e_harm = betting_log_e_ternary(neg, pos, n, 0.0) >= np.log(1 / alpha)
    ok = (n >= min_n)
    dep = np.where(e_win & e_gate & ok)[0]; harm = np.where(e_harm & ok)[0]
    return dict(deploy_time=int(dep[0] + 1) if dep.size else None, harm_time=int(harm[0] + 1) if harm.size else None,
                win_time=int(np.where(e_win & ok)[0][0] + 1) if (e_win & ok).any() else None,
                gate_time=int(np.where(e_gate & ok)[0][0] + 1) if (e_gate & ok).any() else None)


def replay(df, a, b, domains, n=2000, reps=500, seed=0, label=''):
    PA = pools(df, a, domains); PB = pools(df, b, domains)
    rows = []
    for design in ['paired', 'cross_arrival']:
        rng = np.random.default_rng([seed, hash(design) % 1000])
        res = []
        for r in range(reps):
            A, B = stream(rng, PA, PB, n, design)
            z, dq = score_pairs(A, B)
            out = run_guarded(z, dq); out['final_nb'] = float(np.mean(z)); out['final_success_diff'] = float(np.mean(dq)); res.append(out)
        dep = [x['deploy_time'] for x in res]; harm = [x['harm_time'] for x in res]
        rows.append(dict(label=label, A=a, B=b, domains='+'.join(domains), design=design, reps=reps, max_pairs=n,
                         deploy_rate=np.mean([d is not None for d in dep]), harm_rate=np.mean([h is not None for h in harm]),
                         median_deploy_time=float(np.median([d for d in dep if d is not None])) if any(d is not None for d in dep) else None,
                         q25_deploy_time=float(np.percentile([d for d in dep if d is not None], 25)) if any(d is not None for d in dep) else None,
                         q75_deploy_time=float(np.percentile([d for d in dep if d is not None], 75)) if any(d is not None for d in dep) else None,
                         median_harm_time=float(np.median([h for h in harm if h is not None])) if any(h is not None for h in harm) else None,
                         mean_final_nb=float(np.mean([x['final_nb'] for x in res])), sd_final_nb=float(np.std([x['final_nb'] for x in res])),
                         mean_final_success_diff=float(np.mean([x['final_success_diff'] for x in res]))))
        print(rows[-1], flush=True)
    return rows


def null_replay(df, a, domains, n=2000, reps=500, seed=1):
    """Same system vs itself (disjoint trials): population null; false deployment rate."""
    P = pools(df, a, domains); rows = []
    keys = sorted(P)
    rng = np.random.default_rng(seed); dep = 0; harm = 0
    for r in range(reps):
        idx = rng.integers(0, len(keys), n)
        A = []; B = []
        for i in idx:
            runs = P[keys[i]]; pick = rng.permutation(len(runs))[:2]
            A.append(runs[pick[0]]); B.append(runs[pick[1]])
        z, dq = score_pairs(np.stack(A), np.stack(B))
        out = run_guarded(z, dq); dep += out['deploy_time'] is not None; harm += out['harm_time'] is not None
    return dict(label='self_null', A=a, B=a, domains='+'.join(domains), design='paired_disjoint_trials', reps=reps, max_pairs=n,
                deploy_rate=dep / reps, harm_rate=harm / reps)


def completion_order_stress(df, a, domains, n=1500, reps=300, seed=2, slow_factor=4.0):
    """Semi-synthetic: A vs A (null) but arm B's FAILED runs take slow_factor x longer.
    Analysing pairs in order of pair completion (both runs done) instead of
    arrival order creates early over-representation of pairs where B failed
    slowly... i.e. pairs where B succeeded quickly are seen first => A looks
    worse early. We record false 'harm' and false 'deploy' rates under both orders."""
    P = pools(df, a, domains); keys = sorted(P); rng = np.random.default_rng(seed)
    out = {'arrival_order': [0, 0], 'completion_order': [0, 0]}
    for r in range(reps):
        idx = rng.integers(0, len(keys), n); A = []; B = []
        for i in idx:
            runs = P[keys[i]]; pick = rng.permutation(len(runs))[:2]; A.append(runs[pick[0]]); B.append(runs[pick[1]])
        A = np.stack(A); B = np.stack(B).copy()
        B[:, 3] = np.where(B[:, 0] < .5, B[:, 3] * slow_factor, B[:, 3])
        z, dq = score_pairs(A, B)
        arrival = rng.exponential(1.0, n).cumsum() * 10  # arrivals every ~10 s
        done = arrival + np.maximum(A[:, 3], B[:, 3])
        order = np.argsort(done)
        for name, zz, dd in [('arrival_order', z, dq), ('completion_order', z[order], dq[order])]:
            o = run_guarded(zz, dd)
            out[name][0] += o['deploy_time'] is not None; out[name][1] += o['harm_time'] is not None
    rows = [dict(label='completion_order_stress', A=a, B=a + ' (failures slowed x%g)' % slow_factor, domains='+'.join(domains), design=k, reps=reps, max_pairs=n,
                 deploy_rate=v[0] / reps, harm_rate=v[1] / reps) for k, v in out.items()]
    for r in rows: print(r, flush=True)
    return rows


def main():
    df = load_tau2(); rows = []
    rows += replay(df, 'o4-mini-2025-04-16', 'gpt-4.1-2025-04-14', ['airline', 'retail', 'telecom'], label='tau2_o4mini_vs_gpt41_all')
    rows += replay(df, 'o4-mini-2025-04-16', 'gpt-4.1-2025-04-14', ['retail'], label='tau2_o4mini_vs_gpt41_retail')
    rows += replay(df, 'claude-3-7-sonnet-20250219', 'gpt-4.1-2025-04-14', ['airline', 'retail', 'telecom'], label='tau2_claude37_vs_gpt41_all')
    rows.append(null_replay(df, 'gpt-4.1-2025-04-14', ['airline', 'retail', 'telecom']))
    rows += completion_order_stress(df, 'gpt-4.1-2025-04-14', ['airline', 'retail', 'telecom'])
    pd.DataFrame(rows).to_csv(OUT / 'replay_results.csv', index=False)
    # One illustrative stream with CS trajectory for a figure
    rng = np.random.default_rng(123)
    PA = pools(df, 'o4-mini-2025-04-16', ['airline', 'retail', 'telecom']); PB = pools(df, 'gpt-4.1-2025-04-14', ['airline', 'retail', 'telecom'])
    A, B = stream(rng, PA, PB, 2000, 'paired'); z, dq = score_pairs(A, B)
    n = np.arange(1, 2001); pos = np.cumsum(z > 0); neg = np.cumsum(z < 0); tie = n - pos - neg
    looks = np.arange(25, 2001, 25)
    lo, hi = betting_cs_ternary(pos[looks - 1], tie[looks - 1], neg[looks - 1], ALPHA)
    qp = np.cumsum(dq > 0); qn = np.cumsum(dq < 0); glo, ghi = betting_cs_ternary(qp[looks - 1], n[looks - 1] - qp[looks - 1] - qn[looks - 1], qn[looks - 1], ALPHA)
    pd.DataFrame(dict(n=looks, nb_hat=((pos - neg) / n)[looks - 1], nb_lo=lo, nb_hi=hi, succ_hat=((qp - qn) / n)[looks - 1], succ_lo=glo, succ_hi=ghi)).to_csv(OUT / 'example_stream_cs.csv', index=False)
    (OUT / 'manifest.json').write_text(json.dumps(dict(alpha=ALPHA, margin=MARGIN, min_n=50, code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                                     note='Replay of historical tau2-bench runs; synthetic arrival process; not live A/B outcomes.'), indent=2))
    print('done')


if __name__ == '__main__':
    main()
