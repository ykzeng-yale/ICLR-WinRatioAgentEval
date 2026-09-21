"""Read-only diagnosis of retained coding evidence; no model calls or simulations.

These are post-hoc descriptions of one archived schedule. They do not estimate
causal repair effects, population error rates, or prospective study power.
"""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/scientific_diagnostics/diagnosis.json"
INPUTS = [
    "results/open_coding/episode_metrics.jsonl",
    "results/open_coding/same_task_scores.csv",
    "results/open_coding/first_pass_pairs.csv",
    "results/open_airline/replay_scores.csv",
    "evidence/open_coding_collection/agent.py.txt",
]


def radius(n):
    return math.sqrt((n + 100) * math.log((n + 100) / (100 * .00625**2))) / n


def read_csv(path):
    with (ROOT / path).open() as handle:
        return list(csv.DictReader(handle))


def decomposition(rows, score_key="score", success_key="success_difference"):
    n = len(rows)
    h = sum(int(r[score_key]) for r in rows)
    d = sum(int(r[success_key]) for r in rows)
    tiers = Counter((int(r["decisive_tier_zero_based"]), int(r[score_key])) for r in rows)
    # Success-tier scores equal the binary success difference; later tiers
    # have zero success difference in the retained hierarchy.
    for r in rows:
        tier = int(r["decisive_tier_zero_based"])
        assert int(r[success_key]) == (int(r[score_key]) if tier == 0 else 0)
    resource_sum = sum(sign * count for (tier, sign), count in tiers.items() if tier > 0)
    assert h == d + resource_sum
    return {"n": n, "hierarchy_sum": h, "success_difference_sum": d,
            "resource_tier_sum": resource_sum, "net_benefit": h / n,
            "tier_counts": [{"tier": t, "score": s, "count": count}
                            for (t, s), count in sorted(tiers.items())]}


def main():
    episodes = [json.loads(x) for x in (ROOT / INPUTS[0]).read_text().splitlines()]
    by_task = {}
    for row in episodes:
        task = by_task.setdefault(row["task_id"], {})
        assert row["variant_letter"] not in task
        task[row["variant_letter"]] = row
    assert len(episodes) == 1182 and len(by_task) == 591
    assert all(set(pair) == {"A", "B"} for pair in by_task.values())
    transitions = Counter((p["A"]["success"], p["B"]["success"]) for p in by_task.values())
    b = [r for r in episodes if r["variant_letter"] == "B"]
    assert all(type(r["self_test_passed"]) is bool for r in b)
    assert all(not r["error_present"] for r in b)
    self_test = Counter((r["self_test_passed"], r["success"]) for r in b)
    repairs = Counter((r["repair_rounds"], r["success"]) for r in b)
    resources = {}
    for arm in ("A", "B"):
        rows = [r for r in episodes if r["variant_letter"] == arm]
        resources[arm] = {
            "workflow_seconds": sum(r["latency_s"] for r in rows),
            "completion_tokens": sum(r["completion_tokens"] for r in rows),
            "total_tokens": sum(r["completion_tokens"] + r["prompt_tokens"] for r in rows),
        }
    first = next(n for n in range(1, 100001) if radius(n) < .03)
    report = {
        "scope": "Post-hoc deterministic descriptions of existing accepted projections; not new study outcomes or causal repair estimates.",
        "source_baseline": "0775cbc847d8084b0e0a5197123026dcd90cabe8",
        "inputs_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS},
        "coding_success_transitions": [{"a_success": a, "b_success": b_, "count": n}
                                       for (a, b_), n in sorted(transitions.items())],
        "coding_final_self_test_vs_hidden_verifier": [{"self_test_passed": a, "hidden_success": b_, "count": n}
                                                    for (a, b_), n in sorted(self_test.items())],
        "coding_repair_rounds_vs_hidden_verifier": [{"repair_rounds": r, "hidden_success": h, "count": n}
                                                   for (r, h), n in sorted(repairs.items())],
        "coding_same_task": decomposition(read_csv(INPUTS[1])),
        "coding_first_pass": decomposition(read_csv(INPUTS[2])),
        "coding_resources": resources,
        "coding_b_to_a_resource_ratios": {k: resources["B"][k] / resources["A"][k] for k in resources["A"]},
        "airline_replay": decomposition(read_csv(INPUTS[3]), "observed_score", "observed_success_difference"),
        "prospective_planning_arithmetic_not_power": {
            "alpha_gate": .00625, "rho": 100, "success_margin": .03,
            "complete_score_rows": [{"n": n, "radius": radius(n),
                                     "strict_required_observed_success_difference": radius(n) - .03,
                                     "minimum_integer_net_success_count": math.floor(n * (radius(n) - .03)) + 1}
                                    for n in (100, 565, 1000, 2000, 17097)],
            "first_n_allowing_exactly_zero_observed_success_difference": first,
            "caveat": "Complete-score algebra only, not a power probability or universal abstention claim; pending data can widen bounds."
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
