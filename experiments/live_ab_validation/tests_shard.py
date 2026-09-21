"""BOUNDED ORCHESTRATION TESTS for the T1 shard executor.

Root, 10:22: "bounded orchestration tests using synthetic stub records to check shard
counts/uniqueness, atomic completion, a failed shard, and cumulative-cap behavior.
Those tests must not run the scientific grid or call native/model references."

Every runner below writes SYNTHETIC records.  No draw is generated, no band is
computed, no native reference is called, and no effect value exists anywhere in this
file.  The ORCHESTRATION under test is the real one.

Run:  python tests_shard.py
"""

from __future__ import annotations

import gzip
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vshard                                                   # noqa: E402


def stub_runner(spec, out_dir):
    """Write synthetic rows matching the plan's expected counts. No science."""
    p = Path(out_dir) / "primary_rows.csv.gz"
    r = Path(out_dir) / "reference_bands.csv"
    with gzip.GzipFile(filename="", mode="wb", fileobj=p.open("wb"), mtime=0) as fh:
        fh.write(b"stub_header\n")
        for i in range(spec["expected_primary_rows"]):
            fh.write(f"stub,{spec['id']},{i}\n".encode())
    with r.open("w") as fh:
        fh.write("stub_header\n")
        for i in range(spec["expected_reference_rows"]):
            fh.write(f"stub,{spec['id']},{i}\n")
    return vshard.ShardOutcome(
        primary_path=p, reference_path=r,
        observed={"programs": spec["expected_programs"],
                  "trials": spec["expected_trials"],
                  "reference_calls": spec["expected_reference_calls"],
                  "primary_rows": spec["expected_primary_rows"],
                  "reference_rows": spec["expected_reference_rows"]},
        unique_coordinates=spec["expected_programs"],
        attempted=spec["expected_trials"], completed=spec["expected_trials"])


def short_runner(spec, out_dir):
    """A shard that loses trials: counts must NOT reconcile."""
    o = stub_runner(spec, out_dir)
    o.observed["trials"] -= 1
    o.completed -= 1
    o.failed = 1
    o.errors = [{"message": "synthetic failure", "utc": "2026-09-21T00:00:00Z"}]
    return o


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.plan = vshard.load_plan()

    def test_the_plan_loads_and_self_verifies(self):
        self.assertEqual(len(self.plan["shards"]), 56)
        self.assertEqual(self.plan["total_programs"], 28_000)

    def test_shard_ids_are_unique_and_coverage_is_disjoint_and_complete(self):
        cov = set()
        for s in self.plan["shards"]:
            for prog in range(s["program_start_inclusive"],
                              s["program_stop_exclusive"]):
                key = (s["cell"], prog)
                self.assertNotIn(key, cov, "duplicate coordinate")
                cov.add(key)
        self.assertEqual(len(cov), 28_000)

    def test_per_shard_counts_match_the_declared_totals(self):
        sh = self.plan["shards"]
        self.assertEqual(sum(s["expected_trials"] for s in sh), 112_000)
        self.assertEqual(sum(s["expected_reference_calls"] for s in sh), 224_000)
        self.assertEqual(sum(s["expected_primary_rows"] for s in sh), 336_000)
        self.assertEqual(sum(s["expected_reference_rows"] for s in sh), 672_000)

    def test_admission_accepts_only_plan_members(self):
        self.assertEqual(vshard.admit_shard(self.plan, "C1-p0000-0499")["cell"], "C1")
        with self.assertRaises(vshard.ShardError):
            vshard.admit_shard(self.plan, "C1-p9999-9999")

    def test_a_tampered_plan_is_rejected(self):
        tmp = Path(tempfile.mkdtemp(prefix="plan_"))
        try:
            bad = json.loads(vshard.SHARD_PLAN_PATH.read_text())
            bad["shards"][1]["program_start_inclusive"] = \
                bad["shards"][0]["program_start_inclusive"]
            bad["shards"][1]["cell"] = bad["shards"][0]["cell"]
            p = tmp / "bad.json"
            p.write_text(json.dumps(bad))
            with self.assertRaises(vshard.ShardPlanError):
                vshard.load_plan(p)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAtomicCompletion(unittest.TestCase):
    def setUp(self):
        self.plan = vshard.load_plan()
        self.tmp = Path(tempfile.mkdtemp(prefix="shard_"))
        self.job = vshard.JobCounters(started_perf=0.0)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec(self, i=0):
        s = dict(self.plan["shards"][i])
        for k in ("expected_programs", "expected_trials", "expected_reference_calls",
                  "expected_primary_rows", "expected_reference_rows"):
            s[k] = {"expected_programs": 4, "expected_trials": 16,
                    "expected_reference_calls": 32, "expected_primary_rows": 48,
                    "expected_reference_rows": 96}[k]
        s["program_stop_exclusive"] = s["program_start_inclusive"] + 4
        return s

    def test_a_good_shard_publishes_atomically(self):
        r = vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J")
        pub = self.tmp / r["published_dir"]
        self.assertTrue(pub.is_dir())
        self.assertTrue((pub / "COMPLETED_SHARD_RECEIPT.json").is_file())
        self.assertEqual(r["status"], "complete")
        self.assertFalse(any(p.name.startswith("partial_") for p in self.tmp.iterdir()),
                         "no partial directory should survive a success")

    def test_a_failing_shard_is_NOT_published_and_its_partial_survives(self):
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, short_runner,
                             job=self.job, attempt="a1", job_id="J")
        partials = [p for p in self.tmp.iterdir() if p.name.startswith("partial_")]
        self.assertEqual(len(partials), 1, "the incomplete attempt must be retained")
        self.assertFalse(any(p.name.startswith("shard_") for p in self.tmp.iterdir()))
        self.assertFalse((partials[0] / "COMPLETED_SHARD_RECEIPT.json").exists())

    def test_a_completed_receipt_is_never_overwritten(self):
        vshard.run_shard(self._spec(), self.tmp, stub_runner,
                         job=self.job, attempt="a1", job_id="J")
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a2", job_id="J")

    def test_an_incomplete_attempt_is_never_reused(self):
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, short_runner,
                             job=self.job, attempt="a1", job_id="J")
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J")

    def test_the_receipt_carries_every_contracted_field(self):
        r = vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J",
                             context={"source_commit": "abc", "manifest_digest": "d",
                                      "namespace": 0, "horizon": 2000,
                                      "prefixes": [100, 500, 2000],
                                      "policy": "operational",
                                      "schedule": "v2_tick_batched",
                                      "alpha_gate": 0.00625,
                                      "reference_modes": ["H", "D"],
                                      "exposure_label": "replay, prior exposure"})
        for key in ("schema", "job_id", "attempt_id", "shard_id", "sequence",
                    "source_commit", "manifest_digest", "coordinates", "planned",
                    "observed", "unique_coordinate_coverage", "attempt_counts",
                    "errors", "timing", "resources", "files"):
            self.assertIn(key, r, key)
        self.assertEqual(r["resources"]["per_shard_peak_memory"], "unknown",
                         "per-shard memory must not be derived from a job maximum")
        for meta in r["files"].values():
            self.assertRegex(meta["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("uncompressed_bytes", meta)
        self.assertIn("cumulative_job", r["timing"])

    def test_the_recorded_hashes_are_the_published_bytes(self):
        r = vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J")
        pub = self.tmp / r["published_dir"]
        for name, meta in r["files"].items():
            self.assertEqual(vshard._sha256_file(pub / name), meta["sha256"])

    def test_counters_are_cumulative_across_shards(self):
        a = self._spec(0)
        b = self._spec(1)
        vshard.run_shard(a, self.tmp, stub_runner, job=self.job,
                         attempt="a1", job_id="J")
        first = self.job.trials
        vshard.run_shard(b, self.tmp, stub_runner, job=self.job,
                         attempt="a1", job_id="J")
        self.assertEqual(self.job.trials, first * 2)
        self.assertEqual(self.job.shards_completed, 2)
        self.assertGreater(self.job.output_bytes, 0)


class TestJobFinalisation(unittest.TestCase):
    def setUp(self):
        self.plan = vshard.load_plan()
        self.tmp = Path(tempfile.mkdtemp(prefix="job_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_partial_job_is_NOT_scientific_completion(self):
        job = vshard.JobCounters(started_perf=0.0)
        spec = dict(self.plan["shards"][0])
        for k, v in {"expected_programs": 4, "expected_trials": 16,
                     "expected_reference_calls": 32, "expected_primary_rows": 48,
                     "expected_reference_rows": 96}.items():
            spec[k] = v
        spec["program_stop_exclusive"] = spec["program_start_inclusive"] + 4
        vshard.run_shard(spec, self.tmp, stub_runner, job=job,
                         attempt="a1", job_id="J")
        final = vshard.finalize_job(self.tmp, self.plan, job,
                                    supervision={"within_caps": True, "breach": None},
                                    context={"job_id": "J"})
        self.assertFalse(final["scientific_completion"])
        self.assertFalse(final["conditions"]["all_expected_shard_ids_exactly_once"])
        self.assertEqual(final["shards_published"], 1)
        self.assertEqual(len(final["missing_shard_ids"]), 55)

    def test_within_caps_alone_is_insufficient(self):
        job = vshard.JobCounters(started_perf=0.0)
        final = vshard.finalize_job(self.tmp, self.plan, job,
                                    supervision={"within_caps": True, "breach": None},
                                    context={"job_id": "J"})
        self.assertTrue(final["supervision"]["within_caps"])
        self.assertFalse(final["scientific_completion"])
        self.assertIn("alone is NOT scientific completion",
                      final["insufficiency_note"])

    def test_a_cap_event_blocks_completion(self):
        job = vshard.JobCounters(started_perf=0.0)
        final = vshard.finalize_job(
            self.tmp, self.plan, job,
            supervision={"within_caps": False, "breach": {"cap": "seconds"}},
            context={"job_id": "J"})
        self.assertFalse(final["conditions"]["no_cap_event"])
        self.assertFalse(final["conditions"]["supervisor_completed_successfully"])
        self.assertFalse(final["scientific_completion"])

    def test_a_failure_receipt_records_an_incomplete_study(self):
        job = vshard.JobCounters(started_perf=0.0)
        rec = vshard.write_failure_receipt(
            self.tmp, "J", "a1", "cap breach",
            {"cap": "seconds", "limit": 5400.0}, job)
        self.assertEqual(rec["status"], "failed_incomplete_study")
        self.assertIn("No retry, no resume", rec["disposition"])
        self.assertTrue((self.tmp / "T1_FAILURE_RECEIPT.json").is_file())


if __name__ == "__main__":
    r = unittest.main(verbosity=2, exit=False).result
    print(f"\nran={r.testsRun} failures={len(r.failures)} errors={len(r.errors)}")
    raise SystemExit(1 if (r.failures or r.errors) else 0)
