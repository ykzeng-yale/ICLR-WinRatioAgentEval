"""Audit deposited v1 CPU rows and arithmetic, without rerunning simulations.

Usage: python3 experiments/audit_cpu_v1_delivery.py SNAPSHOT_ROOT RECEIPT_JSON
The snapshot must contain the named files exported from SOURCE_COMMIT. This
checks saved-record consistency, not latent-stream validity or chronology.
"""
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_COMMIT = "57482e317c42e971e33871e7d879e6ca61c8eac0"


def csv_rows(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        yield from csv.DictReader(line for line in handle if not line.startswith("#"))


def wilson(x, n):
    z = 1.959963984540054
    p = x / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return max(0, center-half), min(1, center+half)


def main(snapshot, output):
    root = Path(snapshot)
    base = root / "results/live_ab_validation"
    manifest = json.loads((base / "manifest.json").read_text())
    hashes = {}
    for name, expected in manifest["sha256"].items():
        path = name if "/" in name else "experiments/live_ab_validation/" + name
        digest = hashlib.sha256((root/path).read_bytes()).hexdigest()
        assert digest == expected, path
        hashes[path] = digest
    identities = set()
    counts = Counter()
    aggregate = defaultdict(Counter)
    family_errors = set()
    for r in csv_rows(base / "trials.csv.gz"):
        cell, construction = r["cell"], r["construction"]
        program, trial = int(r["program"]), int(r["trial"])
        ident = (cell, program, trial, construction)
        assert ident not in identities, ident
        identities.add(ident)
        assert 0 <= program < manifest["programs_per_cell"][cell]
        assert 0 <= trial < 4
        assert construction in ("ADAPTER", "CPREFIX", "NAIVE")
        counts[cell, construction] += 1
        a = aggregate[cell, construction]
        for name in ("ever_below_h", "ever_above_h", "ever_miscover_h",
                     "ever_below_s", "ever_above_s", "ever_miscover_s",
                     "ever_miscover_h_decision_eligible", "ever_miscover_s_decision_eligible",
                     "never_conjunct", "never_conjunct_all_looks", "decided_at_finalization"):
            assert r[name] in ("0", "1"), name
            a[name] += int(r[name])
        decision = r["decision"]
        assert decision in ("DEPLOY", "RETAIN_INCUMBENT", "NO_DECISION", "CONFLICT")
        a[decision] += 1
        false_deploy = decision == "DEPLOY" and cell not in ("C7", "C8")
        false_harm = decision == "RETAIN_INCUMBENT"
        a["false_deploy"] += false_deploy
        a["false_harm"] += false_harm
        a["correct_deploy"] += decision == "DEPLOY" and cell in ("C7", "C8")
        a["any_erroneous_trial"] += false_deploy or false_harm
        if false_deploy or false_harm:
            family_errors.add((cell, construction, program))
    for cell, programs in manifest["programs_per_cell"].items():
        for construction in ("ADAPTER", "CPREFIX", "NAIVE"):
            assert counts[cell, construction] == programs*4
    verified_rows = {}
    selected = []
    for file in ("miscoverage.csv", "decisions.csv"):
        checked = 0
        for r in csv_rows(base/file):
            cell, construction = r["cell"], r["construction"]
            a = aggregate[cell, construction]
            n = counts[cell, construction]
            if file == "miscoverage.csv":
                field = r["event"] + ("_h" if r["gate"] == "hierarchy" else "_s")
                if r["looks"] == "decision_eligible":
                    field += "_decision_eligible"
                x = a[field]
            else:
                q = r["quantity"]
                if q == "family_any_erroneous":
                    n = manifest["programs_per_cell"][cell]
                    x = sum((cell, construction, p) in family_errors for p in range(n))
                else:
                    field = {"deploy": "DEPLOY", "retain_incumbent": "RETAIN_INCUMBENT",
                             "no_decision": "NO_DECISION", "conflict": "CONFLICT"}.get(q, q)
                    x = a[field]
            assert (int(r["x"]), int(r["N"])) == (x, n), r
            assert abs(float(r["rate"]) - x/n) < 1e-12, r
            lo, hi = wilson(x, n)
            assert abs(float(r["wilson_lo"]) - lo) < 1e-12, r
            assert abs(float(r["wilson_hi"]) - hi) < 1e-12, r
            if r["nominal"]:
                assert int(r["flagged"]) == int(lo > float(r["nominal"])), r
            checked += 1
            if file == "miscoverage.csv" and r["event"] == "ever_miscover" and r["looks"] == "all":
                selected.append({k: r[k] for k in ("cell", "construction", "gate", "x", "N", "rate", "flagged")})
        verified_rows[file] = checked
    compare = Counter()
    for r in csv_rows(base / "comparison_vs_live_ab.csv.gz"):
        compare["rows"] += 1
        compare["checkpoint:" + r["checkpoint"]] += 1
        if r["checkpoint"] == "look":
            compare["look:" + r["status"]] += 1
    defects = Counter()
    containment = Counter()
    for r in csv_rows(base / "comparison_defects.csv.gz"):
        defects[r["defect_class"]] += 1
        if r["defect_class"] == "per_pair_enclosure_endpoint":
            contains = (float(r["enc11_lo"]) <= float(r["enc12_lo"]) and
                        float(r["enc11_hi"]) >= float(r["enc12_hi"]))
            containment["contains" if contains else "not_contains"] += 1
    summary = json.loads((base/"comparison_summary.json").read_text())["run"]
    assert compare["checkpoint:look"] == summary["looks_compared"]
    assert compare["look:DISAGREE"] == summary["looks_disagreeing"]
    assert sum(defects.values()) == summary["defect_rows_written"]
    receipt = {
        "source_commit": SOURCE_COMMIT,
        "scope": "Saved-record accounting and arithmetic only; no latent-stream rerun, schedule approval or live validation.",
        "source_hashes_verified": hashes,
        "unique_trial_construction_rows": len(identities),
        "underlying_trial_coordinates": len({x[:3] for x in identities}),
        "underlying_program_coordinates": len({x[:2] for x in identities}),
        "verified_aggregate_rows": verified_rows,
        "comparison_status_counts": dict(compare),
        "disagreement_detail_classes": dict(defects),
        "pair_endpoint_row_containment": dict(containment),
        "selected_recorded_rates": selected,
        "output_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(base.iterdir()) if p.is_file()},
    }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in receipt.items()
                      if k not in ("source_hashes_verified", "output_hashes", "selected_recorded_rates")}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
