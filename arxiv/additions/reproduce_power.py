"""Verify and summarize saved synthetic power/ablation records, using stdlib only.

Run ``python reproduce_power.py`` beside manifest.json. No simulations, model
calls, Git access, or installed project modules are used. Confidence intervals
are nominal pointwise Monte Carlo summaries, not post-selection guarantees.
Hashes verify archived bytes; they do not repair historical runtime provenance.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

Z95 = 1.959963984540054
DECISIONS = {"DEPLOY", "NO_DECISION", "RETAIN_INCUMBENT"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wilson(events, n):
    p = events / n
    denominator = 1 + Z95 * Z95 / n
    center = (p + Z95 * Z95 / (2 * n)) / denominator
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 * Z95 / (4 * n * n)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def marginal(events, n):
    lo, hi = wilson(events, n)
    return {"events": events, "n": n, "mean": events / n,
            "ci95_lo": lo, "ci95_hi": hi}


def paired_mean(values):
    n = len(values)
    require(n > 1, "paired interval needs at least two records")
    mean = sum(values) / n
    variance = math.fsum((x - mean) ** 2 for x in values) / (n - 1)
    se = math.sqrt(variance / n)
    return {"n": n, "mean": mean, "sd": math.sqrt(variance), "mc_se": se,
            "ci95_lo": mean - Z95 * se, "ci95_hi": mean + Z95 * se}


def newcombe(a, b):
    difference = a["mean"] - b["mean"]
    return {"difference": difference,
            "ci95_lo": difference - math.hypot(a["mean"] - a["ci95_lo"],
                                               b["ci95_hi"] - b["mean"]),
            "ci95_hi": difference + math.hypot(a["ci95_hi"] - a["mean"],
                                               b["mean"] - b["ci95_lo"])}


def check_expected(actual, expected, label="expected"):
    """Check the saved numeric subset; ignore extra explanatory output fields."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict), label + ": expected object")
        for key, value in expected.items():
            require(key in actual, label + ": missing " + key)
            check_expected(actual[key], value, label + "/" + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label)
        for i, value in enumerate(expected):
            check_expected(actual[i], value, label + "/" + str(i))
    elif isinstance(expected, float):
        require(math.isfinite(actual) and math.isclose(actual, expected,
                rel_tol=1e-12, abs_tol=1e-12), f"{label}: {actual} != {expected}")
    else:
        require(actual == expected, f"{label}: {actual} != {expected}")


def reproduce(manifest_path):
    root = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text())
    require(manifest["schema_version"] == 1, "unsupported manifest schema")
    panels = manifest["panels"]
    require(set(panels) == {"coarse", "fine", "disabled"}, "unexpected panel set")
    seen_paths, file_counts, validated = set(), Counter(), []
    # Validate every archived container before reading any outcomes.
    for item in manifest["primary_files"]:
        panel = item["panel"]
        require(panel in panels, "unknown panel: " + panel)
        require(item["source_commit"] == panels[panel]["source_commit"],
                "file/panel source-pin mismatch")
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts,
                "unsafe manifest path")
        path = (root / relative).resolve()
        require(path.is_relative_to(root), "file escapes archive root")
        require(str(relative) not in seen_paths, "duplicate primary-file path")
        seen_paths.add(str(relative))
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"],
                "SHA-256 mismatch: " + str(relative))
        file_counts[panel] += 1
        validated.append((panel, path))
    for panel, spec in panels.items():
        require(file_counts[panel] == spec["file_count"], panel + ": shard count")

    # Retain only ADAPTER decisions for pairing, while checking all row identities.
    seen = defaultdict(set)
    counts = defaultdict(Counter)
    adapters = defaultdict(dict)
    for panel, path in validated:
        spec = panels[panel]
        with gzip.open(path, "rt", newline="") as stream:
            for row in csv.DictReader(stream):
                cell, construction = row["cell"], row["construction"]
                program, trial = int(row["program"]), int(row["trial"])
                require(cell in spec["cells"], panel + ": unexpected cell")
                require(construction in spec["constructions"], "unexpected construction")
                require(0 <= program < spec["programs_per_cell"] and
                        0 <= trial < spec["trials_per_program"], "coordinate out of range")
                require(row["schedule"] == "v2_tick_batched", "unexpected schedule")
                require(row["law"] == cell[:-1] and row["delay"] == cell[-1],
                        "cell/law/delay mismatch")
                require(int(row["n_looks"]) == spec["finalization_tick"], "look horizon mismatch")
                require(row["decision"] in DECISIONS, "unknown decision")
                key = (cell, construction, program, trial)
                require(key not in seen[panel], "duplicate record: " + str(key))
                seen[panel].add(key)
                counts[(panel, cell, construction)][row["decision"]] += 1
                if construction == "ADAPTER":
                    adapters[(panel, cell)][(program, trial)] = row["decision"]
    result = {"panels": {}, "ablation": {"cells": {}, "contrasts": {}}}
    for panel, spec in panels.items():
        n = spec["programs_per_cell"] * spec["trials_per_program"]
        expected_rows = n * len(spec["cells"]) * len(spec["constructions"])
        require(len(seen[panel]) == expected_rows, panel + ": incomplete grid")
        result["panels"][panel] = {}
        for cell in spec["cells"]:
            for construction in spec["constructions"]:
                require(sum(counts[(panel, cell, construction)].values()) == n,
                        f"{panel}/{cell}/{construction}: incomplete grid")
            c = counts[(panel, cell, "ADAPTER")]
            result["panels"][panel][cell] = {
                "trials": n, "deploy": c["DEPLOY"], "retain": c["RETAIN_INCUMBENT"],
                "abstain": c["NO_DECISION"], "rate": c["DEPLOY"] / n,
                "wilson95": wilson(c["DEPLOY"], n)}

    for cell in panels["disabled"]["cells"]:
        original, disabled = adapters[("coarse", cell)], adapters[("disabled", cell)]
        require(original.keys() == disabled.keys(), "unpaired coordinates: " + cell)
        joint, differences = Counter(), []
        for key in sorted(original):
            a, b = original[key], disabled[key]
            joint[f"original={a} -> disabled={b}"] += 1
            differences.append(int(a == "DEPLOY") - int(b == "DEPLOY"))
        n = len(differences)
        result["ablation"]["cells"][cell] = {
            "paired_trials": n,
            "deploy_rate_original": marginal(sum(x == "DEPLOY" for x in original.values()), n),
            "deploy_rate_disabled": marginal(sum(x == "DEPLOY" for x in disabled.values()), n),
            "discordant_pairs": {"deploy_only_original": differences.count(1),
                                 "deploy_only_disabled": differences.count(-1),
                                 "concordant": differences.count(0)},
            "joint_first_decision_categories": dict(joint),
            "paired_difference_original_minus_disabled": paired_mean(differences)}
    for rung in ("05", "10"):
        a = result["ablation"]["cells"]["P" + rung + "A"]
        n = result["ablation"]["cells"]["P" + rung + "N"]
        pa, pn = a["paired_difference_original_minus_disabled"], n["paired_difference_original_minus_disabled"]
        difference, se = pa["mean"] - pn["mean"], math.hypot(pa["mc_se"], pn["mc_se"])
        result["ablation"]["contrasts"]["mu_h=0." + rung] = {
            "A_minus_N_original": newcombe(a["deploy_rate_original"], n["deploy_rate_original"]),
            "A_minus_N_disabled": newcombe(a["deploy_rate_disabled"], n["deploy_rate_disabled"]),
            "change_in_A_minus_N_deploy_contrast": {"difference": difference, "mc_se": se,
                "ci95_lo": difference - Z95 * se, "ci95_hi": difference + Z95 * se}}
    check_expected(result, manifest["expected"])
    result["verification"] = {"status": "PASS", "primary_files": len(validated),
        "records_by_panel": {p: len(seen[p]) for p in panels},
        "paired_ablation_coordinates": sum(len(adapters[("disabled", c)]) for c in panels["disabled"]["cells"]),
        "source_commits": {p: spec["source_commit"] for p, spec in panels.items()}}
    result["scope"] = ("Saved-record reconstruction only. Exploratory synthetic evidence; "
        "ablation reuses coarse coordinates. Intervals are nominal pointwise Monte Carlo "
        "summaries: Wilson marginals, independent-cell Newcombe contrasts, and normal "
        "paired-mean/gap-change intervals using sample variances. Historical source-binding "
        "and lost-attempt limitations are unchanged. No simulation or live trial was run.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().with_name("manifest.json"))
    parser.add_argument("--output", type=Path, help="optional JSON destination; otherwise print to stdout")
    args = parser.parse_args()
    output = json.dumps(reproduce(args.manifest), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
