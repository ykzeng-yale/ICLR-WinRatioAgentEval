#!/usr/bin/env python3
"""Independently verify the archived trace-certificate results, read-only.

This packages the reviewer's already-executed raw-data reconstruction.
It does not import the original certificate engine, make network requests,
run agents, or modify any input/output artifact. The interval formula is
derived separately for the frozen ordinal terminal-marker schedule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
Q = D(".95")
NAMES = {
    "gpt-4.1-2025-04-14": "GPT-4.1",
    "o4-mini-2025-04-16": "o4-mini",
    "claude-3-7-sonnet-20250219": "Claude-3.7",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def final_sign(a, b):
    """Independent final rule: direct absolute 5% tolerance comparison."""
    if a[0] != b[0]:
        return a[0] - b[0]
    if not a[0]:
        return 0
    if abs(a[1] - b[1]) > D(".05") * max(a[1], b[1]):
        return 1 if a[1] < b[1] else -1
    return (b[2] > a[2]) - (b[2] < a[2])


def interval(a, b, tick, allowance):
    """Closed-form completion interval, without original engine functions.

    Episode tuple: final label, final cost, final calls, cumulative costs,
    cumulative calls, and seed. Cumulative arrays include their zero prefix.
    Thus their length equals the ordinal terminal tick L+1.
    """
    a_complete = tick >= len(a[3])
    b_complete = tick >= len(b[3])
    if a_complete and b_complete:
        return (final_sign(a, b),) * 2
    if not a_complete and not b_complete:
        return -1, 1

    # First reason in complete-episode minus pending-episode orientation.
    complete, pending = (a, b) if a_complete else (b, a)
    if not complete[0]:
        lo, hi = -1, 0
    else:
        exposed = min(tick, len(pending[3]) - 1)
        pending_cost = max(D(0), pending[3][exposed] - allowance)
        pending_calls = pending[4][exposed]
        # A resource loss is feasible through a cheaper pending completion,
        # or through cost equivalence and fewer pending issued calls.
        if (pending_cost < Q * complete[1]
                or (Q * pending_cost <= complete[1]
                    and pending_calls < complete[2])):
            lo = -1
        elif Q * pending_cost <= complete[1] and pending_calls <= complete[2]:
            lo = 0
        else:
            lo = 1
        hi = 1  # The pending episode can fail.
    return (lo, hi) if a_complete else (-hi, -lo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True,
                        help="Directory containing the nine pinned tau2 JSON archives")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "results/trace_certificate_manifest.json").read_text())
    allowance = D(manifest["cost_allowance"])
    assert allowance.is_finite() and allowance >= 0
    source_fields = {
        "source_code_sha256": "experiments/run_trace_certificates.py",
        "protocol_sha256": "evidence/trace_certificate_protocol.md",
        "comparator_sha256": "src/winstats.py",
        "public_manifest_sha256": "results/public_manifest.json",
    }
    for field, relative in source_fields.items():
        assert sha(ROOT / relative) == manifest[field], relative
    for name, digest in manifest["output_sha256"].items():
        assert sha(ROOT / "results" / name) == digest, name

    episodes = {}
    messages = 0
    max_error = D(0)
    source_checks = 0
    exact_products = 0
    assert len(manifest["source_files"]) == 9
    for source in manifest["source_files"]:
        path = args.raw_dir / source["file"]
        assert sha(path) == source["sha256"], source["file"]
        source_checks += 1
        data = json.loads(path.read_text(), parse_float=D)
        model = NAMES[data["info"]["agent_info"]["llm"]]
        domain = next(d for d in ("airline", "retail", "telecom")
                      if "_" + d + "_" in path.name)
        for run in data["simulations"]:
            costs = [D(0)]
            calls = [0]
            for message in run["messages"]:
                if message["role"] == "assistant":
                    increment = D(str(message["cost"]))
                    assert increment.is_finite() and increment >= 0
                    tools = message.get("tool_calls") or []
                    assert isinstance(tools, list)
                    costs.append(costs[-1] + increment)
                    calls.append(calls[-1] + len(tools))
                    messages += 1
            assert len(costs) > 1
            final_cost = D(str(run["agent_cost"]))
            label = D(str(run["reward_info"]["reward"]))
            assert final_cost.is_finite() and final_cost >= 0 and label in (0, 1)
            error = abs(final_cost - costs[-1])
            max_error = max(max_error, error)
            assert error <= D("1e-10") * (1 + abs(final_cost))
            assert max(costs) - allowance <= final_cost
            for value in [final_cost] + [max(D(0), x - allowance) for x in costs]:
                assert Fraction(Q * value) == Fraction(19, 20) * Fraction(value)
                exact_products += 1
            task = str(run["task_id"])
            task_hash = hashlib.sha256((domain + ":" + task).encode()).hexdigest()[:12]
            key = domain, model, task_hash, int(run["trial"])
            assert key not in episodes
            episodes[key] = (int(label), final_cost, calls[-1], costs, calls,
                             int(run["seed"]))

    with (ROOT / "results/trace_certificate_pairs.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    checks = early = before_messages = 0
    group_early = Counter()
    task_counts = defaultdict(Counter)
    unique_pairs = set()
    for row in rows:
        a_key = row["domain"], row["model_a"], row["task_hash"], int(row["trial_a"])
        b_key = row["domain"], row["model_b"], row["task_hash"], int(row["trial_b"])
        pair_key = a_key, b_key
        assert pair_key not in unique_pairs
        unique_pairs.add(pair_key)
        a, b = episodes[a_key], episodes[b_key]
        assert a[-1] != b[-1]
        assert a[-1] == int(row["seed_a"]) and b[-1] == int(row["seed_b"])
        truth = final_sign(a, b)
        last = max(len(a[3]), len(b[3]))
        first = None
        previous = -1, 1
        for tick in range(last + 1):
            lo, hi = interval(a, b, tick, allowance)
            assert lo <= truth <= hi
            assert lo >= previous[0] and hi <= previous[1]
            previous = lo, hi
            checks += 1
            if lo == hi and first is None:
                first = tick
        assert first is not None and previous == (truth, truth)
        expected = truth, last, first, last - first, last + 1
        fields = ("final_sign", "completion_only_tick", "certificate_tick",
                  "ordinal_resolution_lead", "prefixes_checked")
        assert expected == tuple(int(row[k]) for k in fields), pair_key
        assert (row["resolved_early"] == "True") == (first < last)
        early += first < last
        before_messages += last - first >= 2
        group = row["domain"], row["model_a"], row["model_b"]
        group_early[group] += first < last
        task_counts[group][row["task_hash"]] += 1

    assert all(n == 12 for group in task_counts.values() for n in group.values())
    assert len(episodes) == manifest["episodes"] == 3336
    assert messages == manifest["assistant_messages"] == 51247
    assert len(rows) == manifest["comparisons"] == 10008
    assert checks == manifest["every_prefix_containment_checks"] == 195171
    assert early == manifest["early_certificates"] == 3426
    assert before_messages == 2595
    with (ROOT / "results/trace_certificate_summary.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            group = row["domain"], row["model_a"], row["model_b"]
            assert group_early[group] == int(row["early_certificates"])

    print(json.dumps({
        "status": "PASS: independent read-only reconstruction",
        "raw_source_hash_checks": source_checks,
        "episodes": len(episodes), "assistant_messages": messages,
        "comparisons": len(rows), "prefix_checks": checks,
        "early_certificates": early,
        "certificates_with_actual_message_remaining": before_messages,
        "all_recorded_first_certificate_times_match": True,
        "maximum_decimal_cost_discrepancy": str(max_error),
        "exact_rational_threshold_product_checks": exact_products,
        "scope": "Fixed-archive ordinal replay; no statistical independence or latency claim",
    }, indent=2))


if __name__ == "__main__":
    main()
