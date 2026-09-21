"""Compare complete-outcome scoring with installed, unmodified R WINS.

This checks 200 finite fixtures and two fixed-n point summaries, not confidence
intervals, sequential inference, relative tolerances, or the live adapter.
Run: python experiments/audit_open_source_wins.py
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.winstats import Tier, compare, summary


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / "reviews/evidence/open_source_wins_probe_20260921.json"
    with tempfile.TemporaryDirectory(prefix="wins-reference-") as tmp:
        scratch = Path(tmp)
        subprocess.run(["Rscript", "--vanilla", str(Path(__file__).with_suffix(".R")),
                        str(scratch)], check=True, capture_output=True, text=True)
        external = json.loads((scratch / "external.json").read_text())
        with (scratch / "pair_scores.csv").open() as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 200
        for row in rows:
            a = [float(row["a_success"]), float(row["a_cost"])]
            b = [float(row["b_success"]), float(row["b_cost"])]
            score, tier = compare(
                a, b, [Tier("success"), Tier("cost", higher_better=False,
                                          absolute_tolerance=float(row["tolerance"]))],
                eligible=[True, a[0] == b[0] == 1])
            assert int(score) == int(row["score"]), row
            assert int(tier) == int(row["tier"]), row
        a = np.array([[1, 1], [1, 2], [1, 3], [0, 0]])
        b = np.array([[1, .5], [1, 1], [0, 0], [0, 0]])
        point_checks = {}
        for name, first, second in [("A_vs_B", a, b), ("B_vs_A", b, a)]:
            first = np.repeat(first, len(second), axis=0)
            second = np.tile(second, (len(a), 1))
            eligible = np.stack([np.ones(len(first), dtype=bool),
                                 (first[:, 0] == 1) & (second[:, 0] == 1)], axis=-1)
            score, _ = compare(first, second, [Tier("success"),
                                Tier("cost", higher_better=False)], eligible=eligible)
            point_checks[name] = summary(score)
            for key, value in point_checks[name].items():
                assert np.isclose(value, external["aggregate"][name][key],
                                  atol=1e-12, rtol=0), (name, key)
        receipt = {
            "assessment_date_utc": "2026-09-21",
            "result": "PASS",
            "scope": "Complete outcomes, success-first/tie-on-joint-failure, absolute cost tolerances; fixed-n all-pairs point summaries only.",
            "excluded": ["relative tolerance", "censoring", "pending outcomes",
                         "paired/cluster inference", "confidence intervals", "live adapter",
                         "optional stopping", "power or calibration"],
            "external": external,
            "CRAN_source_mirror": "https://github.com/cran/WINS/tree/6fec397f2ad1185ac3140b39d4eb2158d0f8d9a7",
            "source_identity_boundary": "Installed version 1.5.1 matches source-mirror metadata; compiled package is not asserted byte-identical to that repository.",
            "pair_scores_checked": len(rows), "score_mismatches": 0,
            "decisive_tier_mismatches": 0, "fixed_n_point_checks": point_checks,
            "underlying_observations_per_aggregate": 8,
            "dependent_all_pairs_per_aggregate": 16,
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                              [Path(__file__), Path(__file__).with_suffix(".R"),
                               ROOT / "src/winstats.py"]},
            "installed_public_strategy_deparse_sha256": sha(scratch / "installed_strategy.txt"),
            "external_pair_csv_sha256": sha(scratch / "pair_scores.csv"),
            "random_draws": 0, "model_calls": 0,
            "package_installations": 0,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: 200 scores and decisive tiers, two fixed-n point summaries; {output}")


if __name__ == "__main__":
    main()
