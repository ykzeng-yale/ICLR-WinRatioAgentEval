"""Frozen informative-delay study; writes only results/async_* artifacts.

Partial evidence is a pathwise lower bound on latent complete-data e-values,
not a calendar-time martingale. See evidence/async_experiment_protocol.md.
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winstats import betting_log_e_ternary

SCENARIOS = {"identical_outcomes": 1.0, "cheaper_equal_success": 0.55}
METHODS = ("naive_completed_only", "complete_prefix", "partial_prefix_envelope")
LABELS = ("Completed only (biased)", "Complete prefixes", "Partial prefixes")
COLORS = ("#B54736", "#326B9B", "#248565")
CONFIG = dict(success_a=0.90, success_b=0.90, cost_log_sd=0.45,
              cost_tolerance=0.05, success_margin=0.03, alpha=0.05,
              maximum_pairs=6000, enrollment_per_tick=100, reveal_horizon=20,
              candidate_step=50, minimum_pairs=100, bets=40,
              cost_delay_cutoff=1.0, seed=2026091803)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k, n):
    q = norm.ppf(0.975)
    p = k / n
    den = 1 + q * q / n
    center = (p + q * q / (2 * n)) / den
    radius = q * np.sqrt(p * (1 - p) / n + q * q / (4 * n * n)) / den
    return max(0., center - radius), min(1., center + radius)


def exact_net_benefit(ratio):
    a = np.log(1 - CONFIG["cost_tolerance"])
    sd = np.sqrt(2) * CONFIG["cost_log_sd"]
    mu = np.log(ratio)
    return float(CONFIG["success_a"] - CONFIG["success_b"]
                 + CONFIG["success_a"] * CONFIG["success_b"]
                 * (norm.cdf((a - mu) / sd) - 1 + norm.cdf((-a - mu) / sd)))


def score_intervals(sa, sb, resource, known_a, known_b, known_cost):
    """Enumerate feasible success-bit completions; no timing-law inference."""
    amin = known_a & sa
    amax = (~known_a) | sa
    bmin = known_b & sb
    bmax = (~known_b) | sb
    dq_lower = amin.astype(np.int8) - bmax.astype(np.int8)
    dq_upper = amax.astype(np.int8) - bmin.astype(np.int8)
    h_lower = np.ones(sa.shape, np.int8)
    h_upper = -np.ones(sa.shape, np.int8)
    both_failure = (~amin) & (~bmin)
    h_lower[both_failure] = 0
    h_upper[both_failure] = 0
    can_lose = (~amin) & bmax
    can_win = amax & (~bmin)
    h_lower[can_lose] = -1
    h_upper[can_win] = 1
    both_success = amax & bmax
    cost_lower = np.where(known_cost, resource, -1)
    cost_upper = np.where(known_cost, resource, 1)
    h_lower = np.where(both_success, np.minimum(h_lower, cost_lower), h_lower)
    h_upper = np.where(both_success, np.maximum(h_upper, cost_upper), h_upper)
    return h_lower, h_upper, dq_lower, dq_upper


def prefix_log_e(z, candidates, threshold):
    pos = np.cumsum(z > 0, axis=1, dtype=np.int32)[:, candidates - 1]
    neg = np.cumsum(z < 0, axis=1, dtype=np.int32)[:, candidates - 1]
    return betting_log_e_ternary(pos, neg, candidates, threshold, CONFIG["bets"])


def generate(rng, batch, ratio):
    shape = (batch, CONFIG["maximum_pairs"])
    sa = rng.random(shape) < CONFIG["success_a"]
    sb = rng.random(shape) < CONFIG["success_b"]
    ca = ratio * rng.lognormal(0, CONFIG["cost_log_sd"], shape)
    cb = rng.lognormal(0, CONFIG["cost_log_sd"], shape)
    resource = np.where(np.abs(ca - cb) > CONFIG["cost_tolerance"] * np.maximum(ca, cb),
                        np.sign(cb - ca), 0).astype(np.int8)
    dq = sa.astype(np.int8) - sb.astype(np.int8)
    h = np.where(sa & sb, resource, dq).astype(np.int8)
    enrollment = 1 + np.arange(shape[1]) // CONFIG["enrollment_per_tick"]
    grade_a = enrollment + np.where(sa, 1, CONFIG["reveal_horizon"])
    grade_b = np.broadcast_to(enrollment + 1, shape)
    cost_a = enrollment + np.where(ca <= CONFIG["cost_delay_cutoff"], 2, CONFIG["reveal_horizon"])
    cost_b = np.broadcast_to(enrollment + 2, shape)
    complete_at = np.maximum(grade_a, grade_b)
    complete_at = np.where(sa & sb, np.maximum(complete_at, np.maximum(cost_a, cost_b)), complete_at)
    return sa, sb, ca, cb, resource, dq, h, grade_a, grade_b, cost_a, cost_b, complete_at


def simulate_batch(rng, batch, ratio, candidates, calendar_cap):
    sa, sb, ca, cb, resource, dq, h, ga, gb, ta, tb, complete_at = generate(rng, batch, ratio)
    latent_h_e = prefix_log_e(h, candidates, 0.)
    latent_q_e = prefix_log_e(dq, candidates, -CONFIG["success_margin"])
    boundary = np.log(1 / CONFIG["alpha"])
    latent_pass = (latent_h_e >= boundary) & (latent_q_e >= boundary)
    deployed = np.zeros((3, batch), bool)
    stop = np.full((3, batch), calendar_cap, np.int32)
    enrolled_stop = np.full((3, batch), CONFIG["maximum_pairs"], np.int32)
    complete_stop = enrolled_stop.copy()
    grades_stop = 2 * enrolled_stop.copy()
    known_cost_stop = np.broadcast_to((ca + cb).sum(axis=1), (3, batch)).copy()
    cumulative = np.zeros((3, calendar_cap), np.int64)
    max_domination_error = -np.inf
    for tick in range(1, calendar_cap + 1):
        enrolled = min(tick * CONFIG["enrollment_per_tick"], CONFIG["maximum_pairs"])
        sl = np.s_[:, :enrolled]
        ka, kb = ga[sl] <= tick, gb[sl] <= tick
        kca, kcb = ta[sl] <= tick, tb[sl] <= tick
        hl, hu, ql, qu = score_intervals(sa[sl], sb[sl], resource[sl], ka, kb, kca & kcb)
        if not (np.all(hl <= h[sl]) and np.all(h[sl] <= hu)
                and np.all(ql <= dq[sl]) and np.all(dq[sl] <= qu)):
            raise AssertionError("A partial interval excluded a latent true score")
        complete = complete_at[sl] <= tick
        if not np.array_equal(complete, (hl == hu) & (ql == qu)):
            raise AssertionError("Complete-score maturity disagrees with interval collapse")
        count = complete.sum(axis=1)
        naive_pass = count >= CONFIG["minimum_pairs"]
        for full, c in ((h[sl], 0.), (dq[sl], -CONFIG["success_margin"])):
            value = betting_log_e_ternary(((full > 0) & complete).sum(axis=1),
                                          ((full < 0) & complete).sum(axis=1), count, c)
            naive_pass &= value >= boundary
        prefix_size = np.where(complete.all(axis=1), enrolled, np.argmin(complete, axis=1))
        # Strong comparator: all completed candidate prefixes, not just the last.
        # This equalizes the two valid methods' prefix opportunities at reveal jumps.
        complete_pass = (latent_pass & (candidates[None, :] <= prefix_size[:, None])).any(axis=1)
        number_candidates = np.searchsorted(candidates, enrolled, side="right")
        selected = candidates[:number_candidates]
        partial_h_e = prefix_log_e(hl, selected, 0.)
        partial_q_e = prefix_log_e(ql, selected, -CONFIG["success_margin"])
        difference = max(float(np.max(partial_h_e - latent_h_e[:, :number_candidates])),
                         float(np.max(partial_q_e - latent_q_e[:, :number_candidates])))
        max_domination_error = max(max_domination_error, difference)
        if difference > 1e-8:
            raise AssertionError("Partial evidence exceeded corresponding latent e-value")
        partial_pass = ((partial_h_e >= boundary) & (partial_q_e >= boundary)).any(axis=1)
        if np.any(complete_pass & ~partial_pass):
            raise AssertionError("Partial envelope omitted an available completed prefix")
        if tick == calendar_cap:
            assert np.array_equal(hl, h) and np.array_equal(ql, dq)
        available_grades = ka.sum(axis=1) + kb.sum(axis=1)
        available_cost = np.where(kca, ca[sl], 0).sum(axis=1) + np.where(kcb, cb[sl], 0).sum(axis=1)
        for method, passes in enumerate((naive_pass, complete_pass, partial_pass)):
            new = passes & ~deployed[method]
            stop[method, new] = tick
            enrolled_stop[method, new] = enrolled
            complete_stop[method, new] = count[new]
            grades_stop[method, new] = available_grades[new]
            known_cost_stop[method, new] = available_cost[new]
            deployed[method] |= passes
            cumulative[method, tick - 1] = deployed[method].sum()
    assert np.all(stop[2] <= stop[1])
    assert np.all(~deployed[1] | deployed[2])
    assert np.array_equal(deployed[1], deployed[2])
    return dict(deployed=deployed, calendar=stop, enrolled_pairs=enrolled_stop,
                complete_pairs=complete_stop, revealed_grades=grades_stop,
                revealed_cost=known_cost_stop, cumulative=cumulative,
                max_domination_error=max_domination_error)


def verify_interval_enumeration():
    # Exhaust every latent success/sign value and every disclosure mask.
    from itertools import product
    checks = 0
    for av, bv, rv, ak, bk, ck in product((False, True), (False, True), (-1, 0, 1),
                                         (False, True), (False, True), (False, True)):
        array = lambda v: np.array([[v]])
        got = score_intervals(array(av), array(bv), array(rv), array(ak), array(bk), array(ck))
        hs, qs = [], []
        for aa, bb, rr in product((int(av),) if ak else (0, 1),
                                  (int(bv),) if bk else (0, 1), (rv,) if ck else (-1, 0, 1)):
            hs.append(rr if aa and bb else aa - bb)
            qs.append(aa - bb)
        assert [int(x.item()) for x in got] == [min(hs), max(hs), min(qs), max(qs)]
        checks += 1
    return checks


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_results(rows, paths, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for col, scenario in enumerate(SCENARIOS):
        ax = axes[0, col]
        for method, label, color in zip(METHODS, LABELS, COLORS):
            selected = [r for r in paths if r["scenario"] == scenario and r["method"] == method]
            ax.plot([r["calendar_tick"] for r in selected], [r["deployment_rate"] for r in selected],
                    label=label, color=color, linewidth=2)
        ax.set(title="Identical outcomes" if col == 0 else "Cheaper, equal success",
               xlabel="Calendar tick", ylabel="Cumulative deployment probability", ylim=(-.015, 1.02))
        if col == 0:
            ax.axhline(.05, color="0.5", linestyle=":", linewidth=1)
        ax.legend(fontsize=8, loc="best")
        ax = axes[1, col]
        selected = [next(r for r in rows if r["scenario"] == scenario and r["method"] == m) for m in METHODS]
        ax.bar(np.arange(3), [r["mean_calendar_time_capped"] for r in selected], color=COLORS,
               yerr=[1.96 * r["calendar_time_mcse"] for r in selected], capsize=3)
        ax.set(xticks=np.arange(3), xticklabels=("Completed\nonly", "Complete\nprefixes", "Partial\nprefixes"),
               ylabel="Mean capped calendar time", ylim=(0, 83))
    fig.savefig(output / "async_operating.png", dpi=200)
    fig.savefig(output / "async_operating.pdf")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=1000)
    parser.add_argument("--batch", type=int, default=25)
    args = parser.parse_args()
    if args.replicates < 1 or args.batch < 1:
        raise ValueError("Positive replication and batch counts required")
    started = time.perf_counter()
    enum_checks = verify_interval_enumeration()
    candidates = np.arange(CONFIG["minimum_pairs"], CONFIG["maximum_pairs"] + 1, CONFIG["candidate_step"])
    calendar_cap = CONFIG["maximum_pairs"] // CONFIG["enrollment_per_tick"] + CONFIG["reveal_horizon"]
    rows, path_rows, paired_rows = [], [], []
    max_error = -np.inf
    for scenario_index, (scenario, ratio) in enumerate(SCENARIOS.items()):
        rng = np.random.default_rng(np.random.SeedSequence([CONFIG["seed"], scenario_index]))
        batches = []
        for begin in range(0, args.replicates, args.batch):
            batches.append(simulate_batch(rng, min(args.batch, args.replicates - begin), ratio, candidates, calendar_cap))
        combined = {key: np.concatenate([b[key] for b in batches], axis=1)
                    for key in ("deployed", "calendar", "enrolled_pairs", "complete_pairs", "revealed_grades", "revealed_cost")}
        cumulative = sum(b["cumulative"] for b in batches)
        max_error = max(max_error, max(b["max_domination_error"] for b in batches))
        for idx, method in enumerate(METHODS):
            deployed = combined["deployed"][idx]
            times = combined["calendar"][idx]
            k = int(deployed.sum())
            lower, upper = wilson(k, args.replicates)
            rows.append(dict(scenario=scenario, method=method, replicates=args.replicates,
                             population_net_benefit=exact_net_benefit(ratio), population_success_difference=0.,
                             deployment_region_true=ratio < 1, deployments=k, deployment_rate=k / args.replicates,
                             rate_ci_lower=lower, rate_ci_upper=upper,
                             mean_calendar_time_capped=float(times.mean()),
                             calendar_time_mcse=float(times.std(ddof=1) / np.sqrt(args.replicates)) if args.replicates > 1 else 0.,
                             median_time_among_deployments=float(np.median(times[deployed])) if k else "",
                             mean_enrolled_pairs_at_stop=float(combined["enrolled_pairs"][idx].mean()),
                             mean_agent_executions_initiated=float(2 * combined["enrolled_pairs"][idx].mean()),
                             mean_complete_pairs_at_stop=float(combined["complete_pairs"][idx].mean()),
                             mean_revealed_success_grades=float(combined["revealed_grades"][idx].mean()),
                             mean_revealed_synthetic_cost=float(combined["revealed_cost"][idx].mean())))
            for tick in range(1, calendar_cap + 1):
                count = int(cumulative[idx, tick - 1])
                lo, hi = wilson(count, args.replicates)
                path_rows.append(dict(scenario=scenario, method=method, calendar_tick=tick,
                                      deployments=count, replicates=args.replicates,
                                      deployment_rate=count / args.replicates, ci_lower=lo, ci_upper=hi))
        gains = combined["calendar"][1] - combined["calendar"][2]
        paired_rows.append(dict(scenario=scenario, replicates=args.replicates,
                                partial_later_count=int((gains < 0).sum()),
                                partial_strictly_earlier_count=int((gains > 0).sum()),
                                partial_strictly_earlier_rate=float((gains > 0).mean()),
                                mean_capped_calendar_gain=float(gains.mean()),
                                gain_mcse=float(gains.std(ddof=1) / np.sqrt(args.replicates)) if args.replicates > 1 else 0.,
                                mean_initiated_execution_reduction=float(2 * (combined["enrolled_pairs"][1] - combined["enrolled_pairs"][2]).mean())))
        print(scenario, {m: int(combined["deployed"][i].sum()) for i, m in enumerate(METHODS)}, flush=True)
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    write_csv(output / "async_results.csv", rows)
    write_csv(output / "async_calendar_paths.csv", path_rows)
    write_csv(output / "async_paired_gains.csv", paired_rows)
    plot_results(rows, path_rows, output)
    manifest = dict(protocol="evidence/async_experiment_protocol.md", classification="synthetic informative-delay experiment; frozen before first results",
                    config=CONFIG, scenarios=SCENARIOS, arguments=vars(args), calendar_cap=calendar_cap,
                    candidate_prefixes=candidates.tolist(),
                    complete_prefix_rule="all fully completed candidate prefixes; same prefix for both gates",
                    partial_rule="all enrolled candidate prefixes with coordinatewise lower-score evidence; same prefix for both gates",
                    exact_targets={s: dict(net_benefit=exact_net_benefit(r), success_difference=0.) for s, r in SCENARIOS.items()},
                    checks=dict(exhaustive_interval_cases=enum_checks,
                                max_partial_minus_latent_log_e=max_error,
                                interval_containment="all prefixes/times/repetitions checked",
                                score_collapse="complete-score maturity checked against interval collapse",
                                pathwise_nonlater="asserted in every repetition",
                                equal_final_decisions="complete and partial envelopes equal after full revelation in every repetition"),
                    source_sha256=sha256(Path(__file__)), core_sha256=sha256(ROOT / "src" / "winstats.py"),
                    protocol_sha256=sha256(ROOT / "evidence" / "async_experiment_protocol.md"),
                    python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                    elapsed_seconds=time.perf_counter() - started,
                    outputs={p.name: sha256(p) for p in sorted(output.glob("async_*")) if p.suffix in (".csv", ".pdf", ".png")})
    (output / "async_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Completed in {manifest['elapsed_seconds']:.2f} seconds; all planned scenarios retained.", flush=True)


if __name__ == "__main__":
    main()
