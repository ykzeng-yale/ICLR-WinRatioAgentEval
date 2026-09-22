#!/usr/bin/env python3
"""Reproduce the bounded foreign-manifest witness; no model/server/test suite.

Exact source: 7c9818edfdecabad4756e4cd228582f5a2d3be87.
Run from any directory with: python3 THIS_FILE --repo /path/to/agent_win_eval
Requires the review interpreter dependencies, including NumPy. Exports immutable
Python blobs to a temporary directory; never imports mutable repo source.
The witness body below is the body already executed during the 05:37 review.
This evidence script itself was recorded afterward and was not rerun.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = "7c9818edfdecabad4756e4cd228582f5a2d3be87"
OBSERVED = {
    "witness": "foreign_records_and_matching_foreign_manifest_local_verifier",
    "producer_bound": True,
    "lifecycle_complete": True,
    "coverage_valid": True,
    "observer_host": "host:bb",
    "expected_host": "host:FOREIGN",
    "binary_pin": None,
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    def git(*tail):
        return subprocess.check_output(["git", "-C", str(args.repo), *tail])
    assert git("rev-parse", SOURCE).decode().strip() == SOURCE
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix="lifecycle_foreign_manifest_") as tmp:
        root = Path(tmp)
        for folder in ("experiments/live_ab", "experiments/local_stream", "src"):
            for name in git("ls-tree", "-r", "--name-only", SOURCE, folder).decode().splitlines():
                if name.endswith(".py"):
                    dest = root / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(git("show", SOURCE + ":" + name))
        sys.path.insert(0, str(root / "experiments/live_ab"))
        import tests_lab_design as t
        fixture = t.LifecycleReaderWitnessTests()
        fixture.setUp()
        try:
            foreign = dict(fixture.expected,
                           host_id="host:FOREIGN", boot_id="boot:FOREIGN")
            for slot in (0, 1):
                fixture._emit(slot_id=slot, task_id=11 + slot,
                              host_id="host:FOREIGN", boot_id="boot:FOREIGN")
            observation = t.lab_lifecycle.observe(
                fixture.log, provenance=fixture.prov, expected=foreign)
            helper = t.ServerLifecycleProducerConsumerTests()
            verdict = t.lab_prepare._coverage_verdict(
                observation, helper._attempt(100, 100.5))
            result = {
                "witness": OBSERVED["witness"],
                "producer_bound": observation["producer_bound"],
                "lifecycle_complete": observation["lifecycle_complete"],
                "coverage_valid": verdict["valid"],
                "observer_host": observation["host_id"],
                "expected_host": observation["expected_manifest"]["host_id"],
                "binary_pin": observation["expected_manifest"]["binary_sha256"],
            }
            print(json.dumps({"source_commit": SOURCE, "result": result,
                              "matches_recorded_review_output": result == OBSERVED}, indent=2))
            assert result == OBSERVED
        finally:
            fixture.doCleanups()

if __name__ == "__main__":
    main()
