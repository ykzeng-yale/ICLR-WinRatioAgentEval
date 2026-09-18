"""Frozen different-objective and grader-sensitivity ablations; CPU only.

Writes only results/decision_ablation_* and never modifies prior experiments.
Weighted utility, component gates, and win preference have different targets.
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
from numpy.polynomial.hermite import hermgauss
from scipy.special import expit, logsumexp
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winstats import Tier, compare, betting_log_e_ternary
from run_simulations import SCENARIOS, exact_targets

CONFIG = dict(seed=2026091804, pairs=6000, look_step=100, alpha=.05, bets=40,
              success_margin=.03, compliance_margin=.01, log_cost_sd=.45,
              cost_tolerance=.05, utility_weights=[.8, .1, .1])
DECISIONS = ("success_superiority", "guardrails_only", "guarded_win",
             "weighted_utility", "guarded_weighted_utility", "guarded_efficiency")
GRADING_METHODS = ("oracle_true_guarded_win", "measured_guarded_win", "bound_aware_measured_win")
GRADING = {
    "identical_nondifferential": ((.995, .995, .75, .75, 1.), (.05, .05, .05, .05)),
    "harm_favorable_labels": ((.995, .995, .71, .75, .4), (.05, 0., 0., .05)),
    "gain_adverse_labels": ((.995, .995, .75, .75, .55), (0., .05, .05, 0.)),
    "larger_harm_nondifferential": ((.995, .995, .65, .75, .4), (.05, .05, .05, .05)),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k, n):
    z = norm.ppf(.975)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0., center - radius), min(1., center + radius)


def efficiency_mean(scale, nodes=80):
    x, w = hermgauss(nodes)
    return float(np.sum(w * expit(-np.log(scale) - np.sqrt(2) * CONFIG["log_cost_sd"] * x)) / np.sqrt(np.pi))


def truth(params):
    sa, sb, pa, pb, ratio = params
    nb, success, compliance = exact_targets(params)
    if ratio == 1 and sa == sb and pa == pb:
        nb = 0.  # Exact exchangeability identity, not a numerically signed null.
    ea, eb = efficiency_mean(ratio), efficiency_mean(1.)
    assert abs(ea - efficiency_mean(ratio, 160)) < 1e-12
    assert abs(eb - efficiency_mean(1., 160)) < 1e-12
    utility = .8 * success + .1 * compliance + .1 * (ea - eb)
    cost_b = np.exp(CONFIG["log_cost_sd"] ** 2 / 2)
    no_worse = (success >= 0 and compliance >= 0 and ratio <= 1)
    strict = (success > 0 or compliance > 0 or ratio < 1)
    if success == 0 and compliance == 0 and ratio == 1:
        pareto = "equivalent"
    elif no_worse and strict:
        pareto = "A_dominates_B"
    elif success <= 0 and compliance <= 0 and ratio >= 1:
        pareto = "B_dominates_A"
    else:
        pareto = "tradeoff"
    guards = success > -.03 and compliance > -.01
    return dict(net_benefit=nb, success_difference=success, compliance_difference=compliance,
                success_a=pa, success_b=pb, compliance_a=sa, compliance_b=sb,
                mean_cost_a=float(ratio * cost_b), mean_cost_b=float(cost_b),
                mean_efficiency_a=ea, mean_efficiency_b=eb, efficiency_difference=ea - eb,
                weighted_utility_difference=utility, pareto_population=pareto,
                component_guardrails_true=guards, guarded_win_region_true=guards and nb > 0)


def raw_outcomes(rng, batch, params):
    sa, sb, pa, pb, ratio = params
    shape = (batch, CONFIG["pairs"])
    compliance_a = rng.random(shape) < sa
    compliance_b = rng.random(shape) < sb
    success_a = rng.random(shape) < pa
    success_b = rng.random(shape) < pb
    cost_a = ratio * rng.lognormal(0, CONFIG["log_cost_sd"], shape)
    cost_b = rng.lognormal(0, CONFIG["log_cost_sd"], shape)
    return compliance_a, compliance_b, success_a, success_b, cost_a, cost_b


def scores(raw):
    sa, sb, pa, pb, ca, cb = raw
    ds = sa.astype(np.int8) - sb.astype(np.int8)
    dq = pa.astype(np.int8) - pb.astype(np.int8)
    h = np.where(ds == 0, dq, ds).astype(np.int8)
    eligible = sa & sb & pa & pb
    decisive = eligible & (np.abs(ca - cb) > .05 * np.maximum(ca, cb))
    h[decisive] = np.sign(cb[decisive] - ca[decisive]).astype(np.int8)
    efficiency = 1 / (1 + ca) - 1 / (1 + cb)
    utility = .8 * dq + .1 * ds + .1 * efficiency
    return h, dq, ds, utility, efficiency


def ternary_log_e(z, looks, threshold):
    pos = np.cumsum(z > 0, axis=1, dtype=np.int32)[:, looks - 1]
    neg = np.cumsum(z < 0, axis=1, dtype=np.int32)[:, looks - 1]
    return betting_log_e_ternary(pos, neg, looks, threshold, CONFIG["bets"])


def bounded_log_e(z, looks, threshold=0.):
    if not np.all(np.isfinite(z)) or np.any(np.abs(z) > 1 + 1e-12):
        raise ValueError("Expected finite bounded scores in [-1,1]")
    lam = np.geomspace(1e-4, .99 / (1 + threshold), CONFIG["bets"])
    wealth = np.log1p((z[..., None] - threshold) * lam)
    np.cumsum(wealth, axis=1, out=wealth)
    return logsumexp(wealth[:, looks - 1, :], axis=-1) - np.log(CONFIG["bets"])


def decision_masks(z, looks):
    h, dq, ds, utility, efficiency = z
    cutoff = np.log(1 / CONFIG["alpha"])
    success_sup = ternary_log_e(dq, looks, 0.) >= cutoff
    guard = ((ternary_log_e(dq, looks, -.03) >= cutoff)
             & (ternary_log_e(ds, looks, -.01) >= cutoff))
    win = ternary_log_e(h, looks, 0.) >= cutoff
    weighted = bounded_log_e(utility, looks) >= cutoff
    efficient = bounded_log_e(efficiency, looks) >= cutoff
    return dict(zip(DECISIONS, (success_sup, guard, guard & win, weighted,
                               guard & weighted, guard & efficient)))


def guarded(z, looks, bias_bound=0.):
    h, dq, ds = z[:3]
    cutoff = np.log(1 / CONFIG["alpha"])
    return ((ternary_log_e(h, looks, 2 * bias_bound) >= cutoff)
            & (ternary_log_e(dq, looks, -.03 + bias_bound) >= cutoff)
            & (ternary_log_e(ds, looks, -.01) >= cutoff))


def own_objectives(t):
    guard = t["component_guardrails_true"]
    return dict(zip(DECISIONS, (t["success_difference"] > 0, guard,
                               t["guarded_win_region_true"], t["weighted_utility_difference"] > 0,
                               guard and t["weighted_utility_difference"] > 0,
                               guard and t["efficiency_difference"] > 0)))


def collect(accum, masks, looks):
    for method, mask in masks.items():
        decision = mask.any(axis=1)
        stop = np.where(decision, looks[np.argmax(mask, axis=1)], CONFIG["pairs"])
        acc = accum.setdefault(method, {"decisions": [], "stops": []})
        acc["decisions"].extend(decision.tolist())
        acc["stops"].extend(stop.tolist())


def summarize(phase, scenario, accum, true_t, measured_t, objectives):
    rows, trials = [], []
    for method, acc in accum.items():
        decision = np.asarray(acc["decisions"], bool)
        stop = np.asarray(acc["stops"])
        n = len(decision)
        k = int(decision.sum())
        lo, hi = wilson(k, n)
        rows.append(dict(phase=phase, scenario=scenario, method=method, replicates=n,
                         rule_objective_true=bool(objectives[method]),
                         true_guarded_win_region=bool(true_t["guarded_win_region_true"]),
                         measured_guarded_win_region=bool(measured_t["guarded_win_region_true"]),
                         positive_decisions=k, decision_rate=k / n, ci_lower=lo, ci_upper=hi,
                         mean_pairs_capped=float(stop.mean()),
                         pairs_mcse=float(stop.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.,
                         median_pairs_among_positives=float(np.median(stop[decision])) if k else ""))
        trials.extend(dict(phase=phase, scenario=scenario, method=method, replicate=i,
                           decision=bool(d), pairs_capped=int(s))
                      for i, (d, s) in enumerate(zip(decision, stop)))
    return rows, trials


def verify_implementation():
    z = np.array([[1, 0, -1, 1, 1, 0, -1], [-1, 0, 1, 0, 0, 1, -1]])
    looks = np.arange(1, z.shape[1] + 1)
    for c in (0., -.03, .2):
        assert np.allclose(bounded_log_e(z, looks, c), ternary_log_e(z, looks, c), atol=1e-11)
    rng = np.random.default_rng(31884)
    raw = raw_outcomes(rng, 1, SCENARIOS["success_regression"])
    sa, sb, pa, pb, ca, cb = raw
    a, b = np.stack([sa, pa, ca], axis=-1), np.stack([sb, pb, cb], axis=-1)
    eligibility = np.ones(a.shape, bool)
    eligibility[..., 2] = sa & sb & pa & pb
    exported = compare(a, b, [Tier("compliance"), Tier("success"), Tier("cost", False, relative_tolerance=.05)], eligibility)[0]
    assert np.array_equal(exported, scores(raw)[0])
    return dict(bounded_vs_count_betting="equal at every prefix for three thresholds",
                hierarchy_vs_exported_comparator="6000 comparisons equal",
                quadrature="80 versus160 nodes agree within1e-12")


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(rows, grade_truths, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    selected = [r for r in rows if r["phase"] == "objectives"]
    names = list(SCENARIOS)
    data = np.array([[next(r["decision_rate"] for r in selected if r["method"] == m and r["scenario"] == s)
                      for s in names] for m in DECISIONS])
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    im = ax.imshow(data, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    ax.set_xticks(range(6), ("Identical", "Efficiency\ngain", "Success\nregression", "Compliance\nregression", "Joint\ngain", "Weak\ngain"))
    ax.set_yticks(range(6), ("Success superiority", "Guardrails only", "Guarded win", "Weighted utility", "Guarded weighted utility", "Guarded efficiency"))
    ax.set_title("Positive decision rates: different objectives, not interchangeable tests")
    for i in range(6):
        for j in range(6):
            ax.text(j, i, f"{100 * data[i, j]:.1f}%", ha="center", va="center", color="white" if data[i, j] > .6 else "black")
    fig.colorbar(im, ax=ax, label="Decision probability")
    for ext in ("png", "pdf"):
        fig.savefig(output / f"decision_ablation_objectives.{ext}", dpi=200)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    x = np.arange(len(GRADING))
    colors = ("#326B9B", "#B54736", "#248565")
    for j, (method, label, color) in enumerate(zip(GRADING_METHODS, ("Oracle true labels", "Measured labels", "Known error bound"), colors)):
        rr = [next(r for r in rows if r["phase"] == "grading" and r["scenario"] == s and r["method"] == method) for s in GRADING]
        vals = np.array([r["decision_rate"] for r in rr])
        error = np.array([[r["decision_rate"] - r["ci_lower"] for r in rr], [r["ci_upper"] - r["decision_rate"] for r in rr]])
        error = np.maximum(error, 0.)  # Roundoff at p=0 can make the lower extent -1e-19.
        axes[0].bar(x + (j - 1) * .24, vals, .24, yerr=error, capsize=2, label=label, color=color)
    labels = ("Identical,\ncommon noise", "Harm,\nfavorable bias", "Gain,\nadverse bias", "Larger harm,\ncommon noise")
    axes[0].set(xticks=x, xticklabels=labels, ylabel="Guarded positive decision probability", ylim=(0, 1.08), title="Measurement error can change the decision")
    axes[0].legend(fontsize=8)
    for j, (field, label, color) in enumerate((("true_success_difference", "True success effect", "#326B9B"), ("measured_success_difference", "Measured success effect", "#B54736"))):
        axes[1].bar(x + (j - .5) * .3, [r[field] for r in grade_truths], .3, label=label, color=color)
    axes[1].axhline(-.03, color="black", linestyle="--", linewidth=1, label="-0.03 guardrail")
    axes[1].set(xticks=x, xticklabels=labels, ylabel="Population success-rate difference", title="True and measured targets differ")
    axes[1].legend(fontsize=8)
    for ext in ("png", "pdf"):
        fig.savefig(output / f"decision_ablation_grading.{ext}", dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=500)
    parser.add_argument("--batch", type=int, default=25)
    args = parser.parse_args()
    if args.replicates < 1 or args.batch < 1:
        raise ValueError("Positive counts required")
    started = time.perf_counter()
    checks = verify_implementation()
    looks = np.arange(CONFIG["look_step"], CONFIG["pairs"] + 1, CONFIG["look_step"])
    rows, trials, population, grade_truths = [], [], [], []
    for j, (scenario, params) in enumerate(SCENARIOS.items()):
        rng = np.random.default_rng(np.random.SeedSequence([CONFIG["seed"], 0, j]))
        t = truth(params)
        population.append(dict(scenario=scenario, **t))
        accum = {}
        for begin in range(0, args.replicates, args.batch):
            raw = raw_outcomes(rng, min(args.batch, args.replicates - begin), params)
            collect(accum, decision_masks(scores(raw), looks), looks)
        rr, tt = summarize("objectives", scenario, accum, t, t, own_objectives(t))
        rows.extend(rr)
        trials.extend(tt)
        print("objectives", scenario, {r["method"]: r["positive_decisions"] for r in rr}, flush=True)
    for j, (scenario, (params, rates)) in enumerate(GRADING.items()):
        fpa, fna, fpb, fnb = rates
        sa, sb, pa, pb, ratio = params
        pma, pmb = pa * (1 - fna) + (1 - pa) * fpa, pb * (1 - fnb) + (1 - pb) * fpb
        actual, measured = truth(params), truth((sa, sb, pma, pmb, ratio))
        error_bound = max(fpa, fna) + max(fpb, fnb)
        assert abs(measured["success_difference"] - actual["success_difference"]) <= error_bound + 1e-12
        assert abs(measured["net_benefit"] - actual["net_benefit"]) <= 2 * error_bound + 1e-12
        robust_truth = (measured["net_benefit"] > 2 * error_bound
                        and measured["success_difference"] > -.03 + error_bound
                        and measured["compliance_difference"] > -.01)
        grade_truths.append(dict(scenario=scenario, fp_a=fpa, fn_a=fna, fp_b=fpb, fn_b=fnb,
                                true_success_a=pa, true_success_b=pb, measured_success_a=pma, measured_success_b=pmb,
                                actual_error_probability_a=(1 - pa) * fpa + pa * fna,
                                actual_error_probability_b=(1 - pb) * fpb + pb * fnb,
                                assumed_error_probability_bound_sum=error_bound,
                                true_net_benefit=actual["net_benefit"], measured_net_benefit=measured["net_benefit"],
                                true_success_difference=actual["success_difference"], measured_success_difference=measured["success_difference"],
                                true_guarded_region=actual["guarded_win_region_true"], measured_guarded_region=measured["guarded_win_region_true"],
                                bound_aware_objective_true=robust_truth))
        rng = np.random.default_rng(np.random.SeedSequence([CONFIG["seed"], 1, j]))
        accum = {}
        for begin in range(0, args.replicates, args.batch):
            raw = raw_outcomes(rng, min(args.batch, args.replicates - begin), params)
            s_a, s_b, p_a, p_b, c_a, c_b = raw
            a_flip = rng.random(p_a.shape) < np.where(p_a, fna, fpa)
            b_flip = rng.random(p_b.shape) < np.where(p_b, fnb, fpb)
            true_scores = scores(raw)
            measured_scores = scores((s_a, s_b, p_a ^ a_flip, p_b ^ b_flip, c_a, c_b))
            masks = dict(zip(GRADING_METHODS, (guarded(true_scores, looks), guarded(measured_scores, looks),
                                              guarded(measured_scores, looks, error_bound))))
            collect(accum, masks, looks)
        rr, tt = summarize("grading", scenario, accum, actual, measured,
                           dict(zip(GRADING_METHODS, (actual["guarded_win_region_true"], measured["guarded_win_region_true"], robust_truth))))
        rows.extend(rr)
        trials.extend(tt)
        print("grading", scenario, {r["method"]: r["positive_decisions"] for r in rr}, flush=True)
    output = ROOT / "results"
    write_csv(output / "decision_ablation_results.csv", rows)
    write_csv(output / "decision_ablation_trials.csv", trials)
    write_csv(output / "decision_ablation_population.csv", population)
    write_csv(output / "decision_ablation_grader_truths.csv", grade_truths)
    plot(rows, grade_truths, output)
    manifest = dict(classification="prospectively specified internal synthetic extension; not external preregistration",
                    protocol="evidence/decision_ablation_protocol.md", config=CONFIG, arguments=vars(args), looks=looks.tolist(),
                    objective_scenarios=SCENARIOS, grading_scenarios=GRADING,
                    semantic_warning="Methods in objective ablation test different estimands; grader tests distinguish true and measured labels",
                    checks=checks, source_sha256=digest(Path(__file__)),
                    core_sha256=digest(ROOT / "src" / "winstats.py"),
                    reused_scenario_source_sha256=digest(ROOT / "experiments" / "run_simulations.py"),
                    protocol_sha256=digest(ROOT / "evidence" / "decision_ablation_protocol.md"),
                    python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                    elapsed_seconds=time.perf_counter() - started,
                    outputs={p.name: digest(p) for p in sorted(output.glob("decision_ablation_*")) if p.suffix in (".csv", ".png", ".pdf")})
    (output / "decision_ablation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"All ten frozen scenarios retained; completed in {manifest['elapsed_seconds']:.2f} seconds.", flush=True)


if __name__ == "__main__":
    main()
