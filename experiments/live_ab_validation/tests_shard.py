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
    coords = [(spec["cell"], i) for i in range(spec["program_start_inclusive"],
                                               spec["program_stop_exclusive"])]
    return vshard.ShardOutcome(
        primary_path=p, reference_path=r,
        observed={"programs": spec["expected_programs"],
                  "trials": spec["expected_trials"],
                  "reference_calls": spec["expected_reference_calls"],
                  "primary_rows": spec["expected_primary_rows"],
                  "reference_rows": spec["expected_reference_rows"]},
        unique_coordinates=spec["expected_programs"], coordinates=coords,
        attempted=spec["expected_trials"], completed=spec["expected_trials"])


def shifted_runner(spec, out_dir):
    """Right NUMBER of coordinates, wrong ones. Cardinality alone passed this."""
    o = stub_runner(spec, out_dir)
    o.coordinates = [(c, i + 100000) for (c, i) in o.coordinates]
    return o


def all_failed_runner(spec, out_dir):
    """completed=0, failed=all, but row totals match. Published as complete before."""
    o = stub_runner(spec, out_dir)
    o.completed = 0
    o.failed = spec["expected_trials"]
    o.errors = [{"message": "synthetic", "utc": "2026-09-21T00:00:00Z"}]
    return o


#: The pinned context every shard must carry.
CTX = {"source_commit": "abc123", "manifest_digest": "d0", "pins": {"code": "x"},
       "namespace": 0, "horizon": 2000, "prefixes": [100, 500, 2000],
       "policy": "operational", "schedule": "v2_tick_batched",
       "alpha_gate": 0.00625, "reference_modes": ["H", "D"],
       "exposure_label": "replay, prior development exposure"}


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
                             job=self.job, attempt="a1", job_id="J", context=CTX)
        pub = self.tmp / r["published_dir"]
        self.assertTrue(pub.is_dir())
        self.assertTrue((pub / "COMPLETED_SHARD_RECEIPT.json").is_file())
        self.assertEqual(r["status"], "complete")
        self.assertFalse(any(p.name.startswith("partial_") for p in self.tmp.iterdir()),
                         "no partial directory should survive a success")

    def test_a_failing_shard_is_NOT_published_and_its_partial_survives(self):
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, short_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)
        partials = [p for p in self.tmp.iterdir() if p.name.startswith("partial_")]
        self.assertEqual(len(partials), 1, "the incomplete attempt must be retained")
        self.assertFalse(any(p.name.startswith("shard_") for p in self.tmp.iterdir()))
        self.assertFalse((partials[0] / "COMPLETED_SHARD_RECEIPT.json").exists())

    def test_a_completed_receipt_is_never_overwritten(self):
        vshard.run_shard(self._spec(), self.tmp, stub_runner,
                         job=self.job, attempt="a1", job_id="J", context=CTX)
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a2", job_id="J", context=CTX)

    def test_an_incomplete_attempt_is_never_reused(self):
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, short_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)

    def test_the_receipt_carries_every_contracted_field(self):
        r = vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J",
                             context=CTX)
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
                             job=self.job, attempt="a1", job_id="J", context=CTX)
        pub = self.tmp / r["published_dir"]
        for name, meta in r["files"].items():
            self.assertEqual(vshard._sha256_file(pub / name), meta["sha256"])

    def test_shifted_coordinates_are_refused(self):
        """Right cardinality, wrong coordinates -- this passed before."""
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, shifted_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)

    def test_an_all_failed_shard_is_refused_even_when_row_totals_match(self):
        """Root: completed=0, failed=4 published as complete. Not any more."""
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(self._spec(), self.tmp, all_failed_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)

    def test_missing_pinned_context_is_refused(self):
        for drop in ("source_commit", "manifest_digest", "pins", "exposure_label"):
            ctx = {k: v for k, v in CTX.items() if k != drop}
            tmp = Path(tempfile.mkdtemp(prefix="pin_"))
            try:
                with self.assertRaises(vshard.ShardError, msg=drop):
                    vshard.run_shard(self._spec(), tmp, stub_runner,
                                     job=vshard.JobCounters(), attempt="a1",
                                     job_id="J", context=ctx)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_published_dir_is_inside_the_serialized_receipt(self):
        """It was set AFTER the write, so finalize could never resolve paths."""
        r = vshard.run_shard(self._spec(), self.tmp, stub_runner,
                             job=self.job, attempt="a1", job_id="J", context=CTX)
        on_disk = json.loads(
            (self.tmp / r["published_dir"] / "COMPLETED_SHARD_RECEIPT.json").read_text())
        self.assertIn("published_dir", on_disk)
        self.assertEqual(on_disk["published_dir"], r["published_dir"])

    def test_counters_are_cumulative_across_shards(self):
        a = self._spec(0)
        b = self._spec(1)
        vshard.run_shard(a, self.tmp, stub_runner, job=self.job,
                         attempt="a1", job_id="J", context=CTX)
        first = self.job.trials
        vshard.run_shard(b, self.tmp, stub_runner, job=self.job,
                         attempt="a1", job_id="J", context=CTX)
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
                         attempt="a1", job_id="J", context=CTX)
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


class TestRealOrchestrationRoundtrip(unittest.TestCase):
    """F14.  Root: "one positive roundtrip and refusal cases through the REAL
    orchestration with injected stub scientific functions."

    The orchestration here is the production one -- vprod.make_runner driving
    vshard.run_shard and vshard.finalize_job.  Only the four scientific
    functions are stubs, so no draw, band, native reference or effect exists.
    """

    HORIZON = 500          # yields prefixes (100, 500) -> 2 prefixes

    def setUp(self):
        import vprod, vrun
        self.vprod, self.vrun = vprod, vrun
        self.tmp = Path(tempfile.mkdtemp(prefix="round_"))
        self.n_constructions = len(vrun.CONSTRUCTIONS)
        cfg = vrun.make_config(self.HORIZON, 0, schedule="v2_tick_batched")
        self.prefixes = list(cfg.horizons)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stubs(self, fail_at=None):
        import numpy as np

        class Rec:
            decision = 0
            tau = 1

        def draw(cell, program, trial, n_max=None, namespace=None):
            class D:
                z = np.zeros(self.HORIZON)
                dsc = np.zeros(self.HORIZON)
            return D()

        def evaluate(d, cfg, sched):
            if fail_at is not None and fail_at == (getattr(d, "_p", None)):
                raise RuntimeError("synthetic shard failure")
            return ({c: Rec() for c in self.vrun.CONSTRUCTIONS}, 0, 0)

        def rows(cell, program, trial, records, sched):
            if fail_at is not None and program == fail_at:
                raise RuntimeError("synthetic trial failure")
            return "".join(f"stub,{cell.id},{program},{trial},{c}\n"
                           for c in self.vrun.CONSTRUCTIONS)

        def ref(values, alpha):
            n = len(values)
            return (np.full(n, -0.5), np.full(n, 0.5))

        return draw, evaluate, rows, ref

    def _plan(self, programs_per_shard=2, shards=2, trials=2):
        draw, evaluate, rows, ref = self._stubs()
        per_primary = programs_per_shard * trials * self.n_constructions
        per_ref_rows = programs_per_shard * trials * 2 * len(self.prefixes)
        plan = {"shards": [], "allocation": {"C1": programs_per_shard * shards},
                "total_programs": programs_per_shard * shards,
                "programs_per_shard": programs_per_shard,
                "total_trials": programs_per_shard * shards * trials,
                "total_reference_calls": programs_per_shard * shards * trials * 2,
                "total_primary_rows": per_primary * shards,
                "total_reference_rows": per_ref_rows * shards}
        for i in range(shards):
            a = i * programs_per_shard
            plan["shards"].append({
                "sequence": i + 1, "id": f"C1-p{a:04d}-{a + programs_per_shard - 1:04d}",
                "cell": "C1", "program_start_inclusive": a,
                "program_stop_exclusive": a + programs_per_shard,
                "trial_indices": list(range(trials)),
                "expected_programs": programs_per_shard,
                "expected_trials": programs_per_shard * trials,
                "expected_reference_calls": programs_per_shard * trials * 2,
                "expected_primary_rows": per_primary,
                "expected_reference_rows": per_ref_rows})
        return plan

    def _runner(self, trials=2, fail_at=None):
        draw, evaluate, rows, ref = self._stubs(fail_at=fail_at)
        return self.vprod.make_runner(
            horizon=self.HORIZON, namespace=0, policy="operational",
            schedule="v2_tick_batched", alpha_gate=0.00625,
            trials_per_program=trials, draw_fn=draw, evaluate_fn=evaluate,
            rows_fn=rows, reference_fn=ref, smoke_fn=None)

    def test_positive_roundtrip_reaches_scientific_completion(self):
        plan = self._plan()
        runner = self._runner()
        job = vshard.JobCounters(started_perf=0.0)
        for e in plan["shards"]:
            vshard.run_shard(e, self.tmp, runner, job=job, attempt="a1",
                             job_id="J", context=CTX)
        final = vshard.finalize_job(
            self.tmp, plan, job,
            supervision={"within_caps": True, "breach": None},
            context={"job_id": "J"})
        self.assertTrue(final["scientific_completion"],
                        [k for k, v in final["conditions"].items() if not v])
        self.assertEqual(final["observed_totals"], final["expected_totals"])
        self.assertEqual(final["shards_published"], 2)

    def test_the_published_receipts_resolve_their_own_files(self):
        """The published_dir bug made this impossible before."""
        plan = self._plan()
        runner = self._runner()
        job = vshard.JobCounters(started_perf=0.0)
        vshard.run_shard(plan["shards"][0], self.tmp, runner, job=job,
                         attempt="a1", job_id="J", context=CTX)
        d = next(p for p in self.tmp.iterdir() if p.name.startswith("shard_"))
        rec = json.loads((d / "COMPLETED_SHARD_RECEIPT.json").read_text())
        for name, meta in rec["files"].items():
            self.assertEqual(vshard._sha256_file(self.tmp / rec["published_dir"] / name),
                             meta["sha256"])

    def test_a_failing_trial_stops_the_shard_and_publishes_nothing(self):
        plan = self._plan()
        runner = self._runner(fail_at=0)
        job = vshard.JobCounters(started_perf=0.0)
        with self.assertRaises(vshard.ShardError):
            vshard.run_shard(plan["shards"][0], self.tmp, runner, job=job,
                             attempt="a1", job_id="J", context=CTX)
        self.assertFalse(any(p.name.startswith("shard_") for p in self.tmp.iterdir()))
        self.assertTrue(any(p.name.startswith("partial_") for p in self.tmp.iterdir()))

    def test_a_missing_shard_blocks_completion(self):
        plan = self._plan()
        runner = self._runner()
        job = vshard.JobCounters(started_perf=0.0)
        vshard.run_shard(plan["shards"][0], self.tmp, runner, job=job,
                         attempt="a1", job_id="J", context=CTX)
        final = vshard.finalize_job(
            self.tmp, plan, job,
            supervision={"within_caps": True, "breach": None},
            context={"job_id": "J"})
        self.assertFalse(final["scientific_completion"])
        self.assertFalse(final["conditions"]["counts_reconciled"])


if __name__ == "__main__":
    r = unittest.main(verbosity=2, exit=False).result
    print(f"\nran={r.testsRun} failures={len(r.failures)} errors={len(r.errors)}")
    raise SystemExit(1 if (r.failures or r.errors) else 0)
