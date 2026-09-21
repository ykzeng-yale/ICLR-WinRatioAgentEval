"""T1 SHARD EXECUTOR and the immutable completed-shard receipt contract.

Implements the root's 10:22 specification verbatim.  Execution of the scientific grid
remains UNCLEARED; this is the runnable source returned for review.

THE CONTRACT, in the root's words
---------------------------------
    "Write each shard into an attempt-specific partial directory.  Only after both data
     files close successfully, counts/coordinate coverage reconcile, and hashes are
     computed, atomically publish a completion receipt and finalized shard directory.
     Never overwrite an existing completed receipt or delete an incomplete attempt.
     Root reads finalized shards only.  A receipt is valid only with its matching files
     and complete status; a mutable live-progress file is not a completion receipt."

and on failure:

    "On a cap/error, stop the entire attempt, publish its failure receipt and partial
     inventory, and return it to root without retry/resume or tier change."

WHY THE RUNNER IS INJECTABLE
----------------------------
``run_shard`` takes the per-shard work as a callable.  The real one calls the existing
primary/reference logic; the tests pass synthetic stub records.  That is how root's
"bounded orchestration tests ... must not run the scientific grid or call native/model
references" is satisfied without a parallel mock of the orchestration itself -- the
orchestration under test is the real one.

WHAT THIS DOES NOT DO
---------------------
It does not decide anything scientific, does not read an effect value, and does not
adjust design, order or stopping from any interim outcome.  Shard order is fixed by the
root's plan and is independent of results.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

#: The root's machine-readable plan.  Read, never regenerated here.
SHARD_PLAN_PATH = REPO_ROOT / "evidence" / "t1_shard_plan_20260921_1022.json"

RECEIPT_SCHEMA = "live_ab_validation_v2.completed_shard_receipt.1"
JOB_SCHEMA = "live_ab_validation_v2.t1_job_receipt.1"

#: Directory names.  A partial attempt keeps its own name forever; publication is a
#: rename of a fully-written directory, which is atomic within a filesystem.
PARTIAL_PREFIX = "partial"
FINAL_PREFIX = "shard"


class ShardError(RuntimeError):
    pass


class ShardPlanError(ShardError):
    pass


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _uncompressed_size(p: Path) -> int:
    if p.suffix != ".gz":
        return p.stat().st_size
    import gzip
    total = 0
    with gzip.open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            total += len(chunk)
    return total


def load_plan(path: Path = SHARD_PLAN_PATH) -> Dict[str, Any]:
    """Load the root's plan and verify it against its own declared totals."""
    plan = json.loads(Path(path).read_text())
    shards = plan["shards"]
    if len({s["id"] for s in shards}) != len(shards):
        raise ShardPlanError("shard ids are not unique")
    seqs = sorted(s["sequence"] for s in shards)
    if seqs != list(range(1, len(shards) + 1)):
        raise ShardPlanError("shard sequence numbers are not 1..N exactly once")
    covered = set()
    for s in shards:
        for prog in range(s["program_start_inclusive"], s["program_stop_exclusive"]):
            key = (s["cell"], prog)
            if key in covered:
                raise ShardPlanError(f"duplicate coordinate {key}")
            covered.add(key)
    alloc = plan["allocation"]
    for cell, n in alloc.items():
        want = {(cell, i) for i in range(n)}
        if not want <= covered:
            raise ShardPlanError(f"cell {cell} coverage has gaps")
    if len(covered) != plan["total_programs"]:
        raise ShardPlanError(
            f"coverage {len(covered)} != declared total {plan['total_programs']}")
    return plan


def admit_shard(plan: Dict[str, Any], shard_id: str) -> Dict[str, Any]:
    """SHARD-AWARE admission: membership in the reviewed plan, by identity.

    Root: "connect this route to the actual shard-aware admission check instead
    of the old smoke proxy or an unrestricted bypass."  A shard runs only if its
    id is in the reviewed plan and its coordinates match that plan entry.
    """
    for s in plan["shards"]:
        if s["id"] == shard_id:
            return s
    raise ShardError(
        f"shard {shard_id!r} is not in the reviewed plan; refusing. Admission is "
        f"membership in the plan, not a flag and not a proxy.")


@dataclass
class JobCounters:
    """CUMULATIVE across the whole job.  Root: do not reset per shard."""

    started_perf: float = 0.0
    shards_completed: int = 0
    trials: int = 0
    reference_calls: int = 0
    primary_rows: int = 0
    reference_rows: int = 0
    output_bytes: int = 0

    def snapshot(self) -> Dict[str, Any]:
        return {"elapsed_seconds": time.perf_counter() - self.started_perf,
                "shards_completed": self.shards_completed,
                "trials": self.trials, "reference_calls": self.reference_calls,
                "primary_rows": self.primary_rows,
                "reference_rows": self.reference_rows,
                "output_bytes": self.output_bytes}


@dataclass
class ShardOutcome:
    """What a shard runner returns.  Counts are OBSERVED, never planned values."""

    primary_path: Path
    reference_path: Path
    observed: Dict[str, int]
    unique_coordinates: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    #: The exact (cell, program) pairs emitted, for coordinate reconciliation.
    coordinates: Optional[Sequence[Tuple[str, int]]] = None
    attempted: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0


def run_shard(spec: Dict[str, Any], out_root: Path, runner: Callable[..., ShardOutcome],
              *, job: JobCounters, attempt: str, job_id: str,
              context: Optional[Dict[str, Any]] = None,
              prior_failed_attempt: Optional[str] = None) -> Dict[str, Any]:
    """Run one shard into a partial directory, then atomically publish it.

    Returns the completion receipt.  Raises ``ShardError`` without publishing if
    anything fails to reconcile -- an unreconciled shard is not a completed one.
    """
    out_root = Path(out_root)
    final_dir = out_root / f"{FINAL_PREFIX}_{spec['sequence']:03d}_{spec['id']}"
    partial_dir = out_root / f"{PARTIAL_PREFIX}_{attempt}_{spec['sequence']:03d}_{spec['id']}"
    if final_dir.exists():
        raise ShardError(
            f"{final_dir} already exists; a completed shard receipt is never "
            f"overwritten")
    if partial_dir.exists():
        raise ShardError(
            f"{partial_dir} already exists; an incomplete attempt is never "
            f"deleted or reused")
    partial_dir.mkdir(parents=True)

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.perf_counter()
    outcome = runner(spec=spec, out_dir=partial_dir)
    elapsed = time.perf_counter() - t0
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ---- reconcile BEFORE publishing ------------------------------------
    obs = dict(outcome.observed)
    planned = {"programs": spec["expected_programs"],
               "trials": spec["expected_trials"],
               "reference_calls": spec["expected_reference_calls"],
               "primary_rows": spec["expected_primary_rows"],
               "reference_rows": spec["expected_reference_rows"]}
    mismatches = {k: {"planned": v, "observed": obs.get(k)}
                  for k, v in planned.items() if obs.get(k) != v}
    if mismatches:
        raise ShardError(
            f"shard {spec['id']} counts do not reconcile: {mismatches}. Partial "
            f"attempt retained at {partial_dir}; not published.")
    if outcome.unique_coordinates != spec["expected_programs"]:
        raise ShardError(
            f"shard {spec['id']} unique coordinate coverage "
            f"{outcome.unique_coordinates} != {spec['expected_programs']}")

    # THE EXACT COORDINATES, not a cardinality.  Root: "Reconcile actual
    # emitted coordinates against each exact shard plan entry, not only a
    # claimed cardinality."  A shifted range of the right SIZE passed before.
    want_coords = {(spec["cell"], i) for i in
                   range(spec["program_start_inclusive"],
                         spec["program_stop_exclusive"])}
    if outcome.coordinates is not None:
        got = set(outcome.coordinates)
        if got != want_coords:
            extra = sorted(got - want_coords)[:3]
            missing = sorted(want_coords - got)[:3]
            raise ShardError(
                f"shard {spec['id']} emitted the wrong coordinates: "
                f"{len(got)} emitted, extra e.g. {extra}, missing e.g. {missing}")

    # ATTEMPT ACCOUNTING MUST BE CONSISTENT.  Root: "A failed outcome with
    # completed=0 and failed=4 currently publishes as complete when its claimed
    # row totals match."  It did -- only `observed` was reconciled.
    if outcome.attempted != outcome.completed + outcome.failed + outcome.skipped:
        raise ShardError(
            f"shard {spec['id']} attempt accounting is inconsistent: attempted "
            f"{outcome.attempted} != completed {outcome.completed} + failed "
            f"{outcome.failed} + skipped {outcome.skipped}")
    if outcome.failed or outcome.skipped:
        raise ShardError(
            f"shard {spec['id']} has {outcome.failed} failed and "
            f"{outcome.skipped} skipped trials; a shard with any failure is "
            f"NOT complete and is not published")
    if outcome.completed != spec["expected_trials"]:
        raise ShardError(
            f"shard {spec['id']} completed {outcome.completed} of "
            f"{spec['expected_trials']} expected trials")

    # REQUIRED PINS must be present and match the frozen context.
    ctx_check = dict(context or {})
    required = ("source_commit", "manifest_digest", "pins", "namespace",
                "horizon", "policy", "schedule", "alpha_gate", "exposure_label")
    absent = [k for k in required if ctx_check.get(k) in (None, "", {})]
    if absent:
        raise ShardError(
            f"shard {spec['id']} is missing required pinned context {absent}; "
            f"a receipt without its bindings cannot be reproduced")
    for p in (outcome.primary_path, outcome.reference_path):
        if not p.is_file():
            raise ShardError(f"shard {spec['id']} data file missing: {p}")

    files = {}
    for p in (outcome.primary_path, outcome.reference_path):
        files[p.name] = {"relative_name": p.name,
                         "compressed_bytes": p.stat().st_size,
                         "uncompressed_bytes": _uncompressed_size(p),
                         "sha256": _sha256_file(p),
                         "status": "complete"}
    shard_bytes = sum(f["compressed_bytes"] for f in files.values())
    job.trials += obs["trials"]
    job.reference_calls += obs["reference_calls"]
    job.primary_rows += obs["primary_rows"]
    job.reference_rows += obs["reference_rows"]
    job.output_bytes += shard_bytes
    job.shards_completed += 1

    ctx = dict(context or {})
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "complete",
        "job_id": job_id, "attempt_id": attempt,
        "shard_id": spec["id"], "sequence": spec["sequence"],
        "source_commit": ctx.get("source_commit"),
        "manifest_digest": ctx.get("manifest_digest"),
        "root_clearance_reference": ctx.get("root_clearance_reference"),
        "pins": ctx.get("pins"),
        "coordinates": {
            "cell": spec["cell"], "namespace": ctx.get("namespace"),
            "program_start_inclusive": spec["program_start_inclusive"],
            "program_stop_exclusive": spec["program_stop_exclusive"],
            "trial_indices": list(spec["trial_indices"]),
            "horizon": ctx.get("horizon"), "prefixes": ctx.get("prefixes"),
            "policy": ctx.get("policy"), "schedule": ctx.get("schedule"),
            "alpha_gate": ctx.get("alpha_gate"),
            "reference_modes": ctx.get("reference_modes"),
            "exposure_label": ctx.get("exposure_label"),
        },
        "planned": planned,
        "observed": obs,
        "unique_coordinate_coverage": outcome.unique_coordinates,
        "attempt_counts": {"attempted": outcome.attempted,
                           "completed": outcome.completed,
                           "failed": outcome.failed,
                           "skipped": outcome.skipped,
                           "missing": max(0, planned["trials"] - outcome.completed)},
        "errors": outcome.errors,
        "imputation": "NONE; missing or failed trials are not imputed into complete rows",
        "timing": {"started_utc": started, "ended_utc": ended,
                   "elapsed_seconds": elapsed,
                   "cumulative_job": job.snapshot()},
        "resources": {
            "per_shard_peak_memory": "unknown",
            "why_unknown": ("the supervisor samples the whole process tree for the "
                            "whole job; a per-shard figure is NOT derived from the "
                            "whole-job maximum because that would attribute another "
                            "shard's peak to this one"),
            "sampled_scope": ("parent-sampled simultaneous process-tree RSS, "
                              "job-level, recorded in SUPERVISION.json"),
            "cumulative_output_bytes": job.output_bytes,
            "this_shard_output_bytes": shard_bytes,
        },
        "files": files,
        "prior_failed_attempt": prior_failed_attempt,
        "prior_attempt_rerun": False,
    }
    # published_dir MUST be inside the serialized bytes.  It was set AFTER the
    # write and the rename, so the ON-DISK receipt never carried it and
    # finalize_job could not resolve any file path -- an ordinary successful
    # publication could never finalize.  Root found this; it is a real bug and
    # every stub test passed straight over it because they read the returned
    # dict rather than the file.
    receipt["published_dir"] = final_dir.name
    (partial_dir / "COMPLETED_SHARD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    _fsync_dir(partial_dir)
    os.rename(partial_dir, final_dir)          # ATOMIC publication
    _fsync_dir(out_root)
    return receipt


def _fsync_dir(p: Path) -> None:
    try:
        fd = os.open(str(p), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:                                            # pragma: no cover
        pass


def write_failure_receipt(out_root: Path, job_id: str, attempt: str,
                          reason: str, detail: Dict[str, Any],
                          job: JobCounters) -> Dict[str, Any]:
    """Publish the failure and its partial inventory.  No retry, no resume."""
    out_root = Path(out_root)
    inventory = sorted(str(p.relative_to(out_root))
                       for p in out_root.rglob("*") if p.is_file())
    rec = {
        "schema": "live_ab_validation_v2.t1_failure_receipt.1",
        "status": "failed_incomplete_study",
        "job_id": job_id, "attempt_id": attempt,
        "reason": reason, "detail": detail,
        "cumulative_job": job.snapshot(),
        "partial_inventory": inventory,
        "disposition": ("returned to root as an INCOMPLETE STUDY. No retry, no "
                        "resume, no tier change, and no completed subset selected "
                        "by outcome."),
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out_root / "T1_FAILURE_RECEIPT.json").write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n")
    return rec


def finalize_job(out_root: Path, plan: Dict[str, Any], job: JobCounters,
                 supervision: Optional[Dict[str, Any]] = None,
                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The final job receipt, with every condition root named, each checked.

    ``within_caps`` or exit zero alone is explicitly insufficient.
    """
    out_root = Path(out_root)
    receipts = []
    for d in sorted(out_root.glob(f"{FINAL_PREFIX}_*")):
        rp = d / "COMPLETED_SHARD_RECEIPT.json"
        if rp.is_file():
            receipts.append(json.loads(rp.read_text()))

    expected_ids = [s["id"] for s in plan["shards"]]
    seen_ids = [r["shard_id"] for r in receipts]
    ids_exactly_once = sorted(seen_ids) == sorted(expected_ids)

    covered: Dict[Tuple[str, int], int] = {}
    for r in receipts:
        c = r["coordinates"]
        for prog in range(c["program_start_inclusive"], c["program_stop_exclusive"]):
            covered[(c["cell"], prog)] = covered.get((c["cell"], prog), 0) + 1
    disjoint = all(v == 1 for v in covered.values())
    complete_cover = len(covered) == plan["total_programs"]

    # ALL FOUR totals.  reference_rows was omitted, so a shard emitting none
    # of them reconciled.  Root named exactly that witness.
    expected_totals = {
        "trials": plan.get("total_trials", 112_000),
        "reference_calls": plan["total_reference_calls"],
        "primary_rows": plan["total_primary_rows"],
        "reference_rows": plan.get("total_reference_rows", 672_000),
    }
    observed_totals = {k: sum(r["observed"].get(k, 0) for r in receipts)
                       for k in expected_totals}
    counts_ok = observed_totals == expected_totals

    # Coordinates must match the PLAN ENTRY for each shard id, not merely be
    # disjoint among themselves: a uniformly shifted set is disjoint too.
    plan_by_id = {s["id"]: s for s in plan["shards"]}
    coords_match_plan = True
    for r in receipts:
        entry = plan_by_id.get(r["shard_id"])
        c = r["coordinates"]
        if (entry is None
                or c.get("cell") != entry["cell"]
                or c.get("program_start_inclusive") != entry["program_start_inclusive"]
                or c.get("program_stop_exclusive") != entry["program_stop_exclusive"]):
            coords_match_plan = False

    hashes_ok = bool(receipts)
    for r in receipts:
        pub = r.get("published_dir")
        if not pub:
            hashes_ok = False
            continue
        d = out_root / pub
        for name, meta in r["files"].items():
            path = d / name
            if not path.is_file() or _sha256_file(path) != meta["sha256"]:
                hashes_ok = False

    # A null pin set is not a consistent pin set.
    pin_blobs = {json.dumps(r.get("pins"), sort_keys=True) for r in receipts}
    pins_present = all(r.get("pins") for r in receipts)
    pins_ok = bool(receipts) and pins_present and len(pin_blobs) == 1

    # Every shard must itself claim complete status with clean attempt counts.
    statuses_ok = bool(receipts) and all(
        r.get("status") == "complete"
        and r["attempt_counts"]["failed"] == 0
        and r["attempt_counts"]["skipped"] == 0
        and r["attempt_counts"]["missing"] == 0
        for r in receipts)
    sup_ok = bool(supervision and supervision.get("within_caps"))
    no_cap_event = bool(supervision and supervision.get("breach") is None)

    conditions = {
        "all_expected_shard_ids_exactly_once": ids_exactly_once,
        "coordinate_coverage_disjoint": disjoint,
        "coordinate_coverage_complete": complete_cover,
        "counts_reconciled": counts_ok,
        "coordinates_match_plan_entries": coords_match_plan,
        "hashes_reconciled": hashes_ok,
        "pins_present_and_consistent": pins_ok,
        "every_shard_complete_with_clean_attempts": statuses_ok,
        "supervisor_completed_successfully": sup_ok,
        "no_cap_event": no_cap_event,
    }
    complete = all(conditions.values())
    return {
        "schema": JOB_SCHEMA,
        "job_id": context.get("job_id") if context else None,
        "scientific_completion": complete,
        "conditions": conditions,
        "shards_published": len(receipts),
        "shards_expected": len(expected_ids),
        "missing_shard_ids": sorted(set(expected_ids) - set(seen_ids)),
        "unique_coordinates": len(covered),
        "expected_totals": expected_totals,
        "observed_totals": observed_totals,
        "cumulative_job": job.snapshot(),
        "supervision": supervision,
        "insufficiency_note": ("within_caps or process exit zero alone is NOT "
                               "scientific completion; every condition above must "
                               "hold. Final paper/calibration acceptance remains "
                               "independent of successful execution."),
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
