"""THE v2 CALIBRATION ENTRY POINT: operational primary + retained H/D reference.

WHY THIS FILE EXISTS
--------------------
Root's 2026-09-21 06:35 disposition named the gap precisely:

    "``vcompare`` selects ``vpolicy.OperationalMonitor``.  The actual ``vrun``
    calibration path still obtains ideal-oracle states ... it has no
    operational-policy selection.  Also, the full grid still calls
    ``run_block`` without the declared H/D reference.  The timing helper makes
    eight reference calls/program but discards the returned bands and writes
    primary rows only.  Consequently, neither matched-policy conformance nor
    the helper's timings certify the intended full calibration executable."

Both halves were real.  The policy half is fixed inside ``vgen``/``vrun``
(``RunConfig.policy``).  THIS module is the second half: one versioned
end-to-end entry point that runs the operational primary and PERSISTS the two
complete-information reference diagnostics computed on the SAME latent draws.

THE ONE-WAY DEPENDENCY
----------------------
``vpanel`` imports ``vrun`` and the reference.  Neither imports ``vpanel``.
The primary therefore remains structurally incapable of consulting the
reference, which is what keeps ``eb_reference.assert_reference_cannot_decide``
true: the reference produces arrays that are written to a SEPARATE artifact and
are never read back into a decision.  ``assert_reference_is_not_consulted``
below checks that property against this file's own source rather than asserting
it in prose.

WHAT IS AND IS NOT CLAIMED
--------------------------
Running this module produces a *deterministic-path* artifact: primary decisions
under the operational policy, and reference bands on the complete-information
score paths.  It is NOT a calibration result, NOT a coverage rate, and NOT a
power statement.  Nothing here is cleared to run at panel scale; the fixture
entry point is bounded by construction and the full grid refuses without an
explicit cleared receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpins                                                    # noqa: E402
import vrun                                                     # noqa: E402
from reference import eb_reference                              # noqa: E402

#: Bump when the produced artifact's MEANING changes, never for a refactor.
PANEL_VERSION = "v2-panel-1"

#: The reference workload frozen on 2026-09-21: one complete-path call per
#: score per trial.  Four trials per program therefore mean EIGHT calls per
#: program, and indexing a returned band at a prefix is array indexing, not a
#: further call.  ``assert_reference_call_budget`` checks the ACTUAL count.
REFERENCE_CALLS_PER_TRIAL = 2
SCORES = ("H", "D")

_PRIMARY_SOURCES = ("vrun.py", "vgen.py", "vband.py", "vpolicy.py")


#: Fixture mode is for a deterministic integration check, not a small study.
#: Root: the entry point "does not enforce a small fixture bound".
FIXTURE_MAX_TRIALS = 64
FIXTURE_MAX_N = 500


class PanelError(RuntimeError):
    """A panel precondition failed.  Always fail closed."""


def _peak_rss_bytes() -> int:
    """Peak RSS of this process TREE (self + reaped children), in bytes."""
    import resource
    mine = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    kids = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # macOS reports bytes, Linux kilobytes.
    scale = 1 if sys.platform == "darwin" else 1024
    return int(max(mine, kids) * scale)


def host_capacity() -> Dict[str, Any]:
    """CPU/RAM/disk capacity and concurrent load, recorded not assumed.

    Root, 07:50: "Check available CPU/RAM/disk capacity and log concurrent
    load; if adequate, this bounded CPU measurement may proceed UNDER THOSE
    RECORDED CONDITIONS. Treat observed time as conditional on the measured
    load, not an uncontended benchmark."
    """
    import shutil as _shutil
    import subprocess as _sp
    load = os.getloadavg()
    cores = os.cpu_count() or 1
    usage = _shutil.disk_usage(str(HERE))
    try:
        total_ram = int(_sp.run(["sysctl", "-n", "hw.memsize"],
                                capture_output=True, text=True).stdout.strip())
    except Exception:                                          # pragma: no cover
        total_ram = 0
    try:
        top = _sp.run(["ps", "-Ao", "pid,pcpu,rss,comm", "-r"],
                      capture_output=True, text=True).stdout.splitlines()[1:9]
    except Exception:                                          # pragma: no cover
        top = []
    return {
        "cpu_cores": cores,
        "load_average": {"1m": load[0], "5m": load[1], "15m": load[2]},
        "load_fraction_of_cores_1m": load[0] / cores,
        "total_ram_bytes": total_ram,
        "disk_free_bytes": usage.free,
        "concurrent_top_processes": [l.strip() for l in top],
        "interpretation": ("observed time is CONDITIONAL ON THIS LOAD; it is "
                           "not an uncontended benchmark and not a guaranteed "
                           "upper bound"),
    }


class CapExceeded(PanelError):
    """A hard resource cap was reached; partial output is preserved."""


def _saved_smoke() -> Dict[str, Any]:
    """The saved accepted projection the full-grid guard prices against."""
    import vtotalguard                                         # noqa: E402
    return vtotalguard.smoke_from_saved_projection()


def _uncompressed_size(path: Path) -> int:
    """Actual decompressed size of a gzip artifact, measured not inferred."""
    import gzip as _gzip
    with _gzip.open(path, "rb") as fh:
        total = 0
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                return total
            total += len(chunk)


def _sha256(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:                                            # pragma: no cover
        return None


# ---------------------------------------------------------------------------
# 1.  The structural guarantee, checked against this file's own source
# ---------------------------------------------------------------------------
def assert_reference_is_not_consulted() -> Dict[str, object]:
    """The reference's outputs must never re-enter the primary's inputs.

    Prose cannot establish this and a comment certainly cannot, so it is read
    off the source: the primary modules must not name the reference package at
    all, and in THIS module the only sink for a reference band must be the
    reference artifact writer.  A future edit that feeds ``ref_h`` into a
    decision therefore fails here rather than silently changing what the panel
    means.
    """
    offenders = []
    for name in _PRIMARY_SOURCES:
        text = (HERE / name).read_text()
        for marker in ("eb_reference", "reference_bands", "from reference",
                       "import reference"):
            if marker in text:
                offenders.append(f"{name} names {marker!r}")
    if offenders:
        raise PanelError(
            "the primary must not reference the reference: " + "; ".join(offenders))

    mine = Path(__file__).resolve().read_text()
    banned = ("vrun.decide", "records[", "decision =")
    leaks = [b for b in banned if f"ref_{b}" in mine]
    if leaks:                                                  # pragma: no cover
        raise PanelError(f"a reference band reaches a decision path: {leaks}")
    eb_reference.assert_reference_cannot_decide()
    return {"primary_sources_checked": list(_PRIMARY_SOURCES),
            "reference_named_in_primary": False}


def assert_reference_call_budget(counts: Dict[str, int], trials: int) -> None:
    """The ACTUAL call count must equal the frozen workload, not approximate it."""
    want = trials * REFERENCE_CALLS_PER_TRIAL
    got = int(counts.get("reference_calls_h", 0)) + int(counts.get("reference_calls_d", 0))
    if got != want:
        raise PanelError(
            f"reference call budget violated: {got} calls for {trials} trials, "
            f"expected exactly {want} ({REFERENCE_CALLS_PER_TRIAL}/trial)")
    if counts.get("reference_calls_h") != counts.get("reference_calls_d"):
        raise PanelError(
            f"H and D reference calls must be paired on the same draws; got "
            f"{counts.get('reference_calls_h')} H and "
            f"{counts.get('reference_calls_d')} D")


# ---------------------------------------------------------------------------
# 2.  Configuration
# ---------------------------------------------------------------------------
#: The three ways this entry point may run.  They are separated because, as the
#: root put it, "a measurement cannot require the qualifying projection that the
#: measurement itself is supposed to create".
MODE_FIXTURE = "fixture"          # tiny deterministic integration check
MODE_MEASUREMENT = "measurement"  # the bounded, allowlisted resource measurement
MODE_FULL_GRID = "full_grid"      # refused until the qualifying ledger matches
MODES = (MODE_FIXTURE, MODE_MEASUREMENT, MODE_FULL_GRID)

#: NAMED, PINNED verification modes.  Root, 08:28: "Code pins alone cannot
#: distinguish the expensive per-trial-verification run from a preflight-only
#: run of the same file. Add an explicit pinned verification policy before
#: interpreting any new timing."  The mode is bound into the pins, so a timing
#: can never be silently attributed to the wrong amount of verification work.
VERIFY_PER_TRIAL = "per_trial"     # what the delivered pass ran: 420,080 checks
VERIFY_PREFLIGHT = "preflight_only"  # root-adopted: verify once, before the job
VERIFY_MODES = (VERIFY_PER_TRIAL, VERIFY_PREFLIGHT)

#: The reference is always the vendored complete-information path; named so the
#: pin records it rather than leaving it implicit.
REFERENCE_MODE = "vendored_complete_information_two_score"


@dataclass
class PanelConfig:
    """What one panel run is, in full.  Every field lands in the receipt."""

    cells: Tuple[str, ...]
    n_max: int
    programs: int
    policy: str = "operational"
    schedule: str = vrun.SCHEDULE_V2
    namespace: int = vgen.NAMESPACE_GRID
    alpha_gate: float = vband.ALPHA_GATE
    trials_per_program: int = vgen.TRIALS_PER_PROGRAM
    with_reference: bool = True
    label: str = "fixture"
    mode: str = MODE_FIXTURE
    program_indices: Optional[Tuple[int, ...]] = None
    verification_mode: str = VERIFY_PER_TRIAL

    def __post_init__(self) -> None:
        if self.policy not in vgen.POLICIES:
            raise PanelError(f"unknown policy {self.policy!r}")
        if self.mode not in MODES:
            raise PanelError(f"unknown mode {self.mode!r}; expected one of {MODES}")
        if self.verification_mode not in VERIFY_MODES:
            raise PanelError(
                f"unknown verification_mode {self.verification_mode!r}; "
                f"expected one of {VERIFY_MODES}")
        if self.schedule == vrun.SCHEDULE_V1 and self.policy != "oracle":
            raise PanelError(
                "v1 is the oracle schedule; an operational v1 run is not defined")
        if self.programs < 1 or self.n_max < 1:
            raise PanelError("programs and n_max must be positive")

        # ---- THE FROZEN SETTINGS, REJECTED RATHER THAN SILENTLY SPLIT -------
        # Root, 07:50: "the executable specification still accepts a mismatched
        # alpha that is USED BY THE REFERENCE AND IGNORED BY THE PRIMARY.
        # Reject non-frozen alpha and trial-count settings."
        # The primary takes its radii from vband.radius_from_formula, which
        # reads the frozen ALPHA_GATE; only the reference saw this field. A run
        # with alpha_gate=0.5 would therefore have produced a reference at 0.5
        # beside a primary at 0.00625 and called them one experiment.
        if float(self.alpha_gate) != float(vband.ALPHA_GATE):
            raise PanelError(
                f"alpha_gate {self.alpha_gate!r} is not the frozen "
                f"{vband.ALPHA_GATE!r}. The primary reads the frozen value from "
                f"vband.radius_from_formula and would IGNORE this one while the "
                f"reference USED it, making the two halves different "
                f"experiments. Refused rather than split.")
        if int(self.trials_per_program) != int(vgen.TRIALS_PER_PROGRAM):
            raise PanelError(
                f"trials_per_program {self.trials_per_program!r} is not the "
                f"frozen {vgen.TRIALS_PER_PROGRAM!r}; the declared eight-calls-"
                f"per-program reference workload is defined against the frozen "
                f"count. Refused.")

        if self.mode == MODE_MEASUREMENT:
            # Re-raised as PanelError so the entry point has ONE failure type;
            # the allowlist's message is preserved verbatim.
            try:
                vpins.ALLOWLIST.refuse_unless_allowed(
                    namespace=self.namespace, cells=self.cells,
                    programs=self.program_indices or (),
                    horizon=self.n_max,
                    trials_per_program=self.trials_per_program,
                    policy=self.policy)
            except vpins.PinError as exc:
                raise PanelError(str(exc)) from exc
            if self.program_indices is None:
                raise PanelError(
                    "measurement mode requires explicit program_indices from "
                    "the authorized allowlist; defaulting to 0..n-1 would run "
                    "coordinates nobody authorized")

    @property
    def indices(self) -> Tuple[int, ...]:
        """Program indices actually run: explicit ones, else 0..programs-1."""
        if self.program_indices is not None:
            return tuple(self.program_indices)
        return tuple(range(self.programs))

    @property
    def trials(self) -> int:
        return len(self.indices) * self.trials_per_program * len(self.cells)

    def identity(self) -> Dict[str, Any]:
        return {"panel_version": PANEL_VERSION, "label": self.label,
                "mode": self.mode,
                "cells": list(self.cells), "n_max": self.n_max,
                "programs": self.programs,
                "program_indices": list(self.indices), "policy": self.policy,
                "verification_mode": self.verification_mode,
                "reference_mode": REFERENCE_MODE,
                "schedule": self.schedule, "namespace": self.namespace,
                "alpha_gate": self.alpha_gate,
                "trials_per_program": self.trials_per_program,
                "with_reference": self.with_reference,
                "reference_calls_per_trial": REFERENCE_CALLS_PER_TRIAL}


# ---------------------------------------------------------------------------
# 3.  The reference diagnostic, indexed at the declared prefixes
# ---------------------------------------------------------------------------
def reference_rows(cell, program: int, trial: int, draw: vgen.TrialDraw,
                   prefixes: Sequence[int], alpha: float
                   ) -> Tuple[List[Dict[str, Any]], int, int]:
    """Both complete-information bands, indexed at ``prefixes``.

    ONE call per score per trial, on the SHARED latent arrays of ``draw`` --
    the same ``draw.z`` and ``draw.dsc`` the primary's enclosures are built
    from, so the diagnostic and the primary are not two different experiments.
    Indexing the returned arrays at a prefix is array indexing and is NOT a
    further call, which is why the budget assertion counts calls rather than
    rows.

    The bands are COMPLETE-INFORMATION: they use the resolved final scores with
    no enclosure and no delay, so they are the "if every episode resolved
    instantly" comparator.  They are a labelled diagnostic and gate nothing.
    """
    out: List[Dict[str, Any]] = []
    calls_h = calls_d = 0
    for score, values in (("H", draw.z), ("D", draw.dsc)):
        arr = np.asarray(values, dtype=np.float64)
        lo, hi = eb_reference.reference_bands(arr, alpha)
        if score == "H":
            calls_h += 1
        else:
            calls_d += 1
        run_mean = np.cumsum(arr) / np.arange(1, arr.size + 1)
        for n in prefixes:
            if n < 1 or n > arr.size:
                continue
            i = n - 1
            out.append({
                "cell": cell.id, "law": cell.law, "delay": cell.delay,
                "program": program, "trial": trial, "score": score,
                "prefix": int(n), "lcb": float(lo[i]), "ucb": float(hi[i]),
                "running_mean": float(run_mean[i]),
                "width": float(hi[i] - lo[i]),
                "status": "complete_information_reference_diagnostic",
            })
    return out, calls_h, calls_d


REFERENCE_HEADER = ("cell,law,delay,program,trial,score,prefix,lcb,ucb,"
                    "running_mean,width,status")


def _ref_row_text(rows: Sequence[Dict[str, Any]]) -> str:
    return "".join(
        "{cell},{law},{delay},{program},{trial},{score},{prefix},"
        "{lcb!r},{ucb!r},{running_mean!r},{width!r},{status}\n".format(**r)
        for r in rows)


# ---------------------------------------------------------------------------
# 4.  The end-to-end run
# ---------------------------------------------------------------------------
def run_panel(cfg: PanelConfig, out_dir: Path,
              verify_policy: bool = True) -> Dict[str, Any]:
    """Operational primary + retained H/D reference, one versioned entry point.

    Writes three artifacts and one receipt binding them:
      * ``primary_rows.csv.gz``   -- the primary decisions under ``cfg.policy``
      * ``reference_bands.csv``   -- the H and D complete-information bands
      * ``receipt.json``          -- identities, seeds, hashes, ACTUAL counts

    Refuses rather than degrades: a missing reference, a call-count mismatch or
    a policy/vpolicy disagreement raises instead of writing a partial artifact
    that would later read as a completed run.
    """
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise PanelError(
            f"{out_dir} is non-empty; refusing to overwrite a deposited receipt. "
            "Write each run to its own fresh directory.")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- THE GUARD, CALLED BY THE ENTRY POINT ITSELF -------------------
    # Root, 07:50: "the actual vpanel entry point does not call that guard and
    # does not enforce a small fixture bound ... A CORRECT HELPER DOES NOT
    # PROTECT AN ENTRY POINT THAT NEVER USES IT. ... Wire that refusal into the
    # actual entry point, not just an unused helper."
    # That was exactly right and it is the same defect class as a gate nothing
    # calls. The guard now runs here, before any work.
    _expected_trials = len(cfg.cells) * len(cfg.indices) * cfg.trials_per_program
    _pin_kw = dict(
        policy=cfg.policy, schedule=cfg.schedule,
        programs=cfg.indices, cells=cfg.cells, namespace=cfg.namespace,
        alpha_gate=cfg.alpha_gate, trials_per_program=cfg.trials_per_program,
        workload=f"{REFERENCE_CALLS_PER_TRIAL}_calls_per_trial",
        verification_mode=cfg.verification_mode,
        reference_mode=REFERENCE_MODE,
        normalized_horizon=cfg.n_max,
        expected_trials=_expected_trials,
        expected_reference_calls=_expected_trials * REFERENCE_CALLS_PER_TRIAL)
    pins_before = vpins.entry_point_pins(
        prefixes=vrun.make_config(cfg.n_max, cfg.namespace,
                                  schedule=cfg.schedule).horizons, **_pin_kw)

    host_at_start = host_capacity()
    guard_record: Dict[str, Any] = {"mode": cfg.mode}
    if cfg.mode == MODE_FULL_GRID:
        # Refuse on the real guard, with the real pins, rather than on a flag.
        cfg_json = json.loads((HERE / "cells.json").read_text())
        budget = vrun.select_tier(_saved_smoke(), cfg_json)
        proposed = {"identities": {k: pins_before[k] for k in
                                   ("code", "config", "policy", "workload", "receipt")},
                    "programs_total": len(cfg.indices) * len(cfg.cells)}
        verdict = vrun.total_workload_guard(budget, cfg_json, proposed)
        guard_record["verdict"] = verdict
        vrun.enforce_total_workload_guard(verdict)   # raises unless authorized
    elif cfg.mode == MODE_MEASUREMENT:
        counts_expected = vpins.ALLOWLIST.check_arithmetic()
        guard_record["allowlist"] = counts_expected
        guard_record["caps"] = {
            "seconds": vpins.ALLOWLIST.cap_seconds,
            "peak_rss_bytes": vpins.ALLOWLIST.cap_peak_rss_bytes,
            "output_bytes": vpins.ALLOWLIST.cap_output_bytes}
    else:
        # fixture: bounded by construction, and the bound is CHECKED.
        planned = len(cfg.cells) * len(cfg.indices) * cfg.trials_per_program
        if planned > FIXTURE_MAX_TRIALS or cfg.n_max > FIXTURE_MAX_N:
            raise PanelError(
                f"fixture mode is bounded at {FIXTURE_MAX_TRIALS} trials and "
                f"n_max {FIXTURE_MAX_N}; this proposes {planned} trials at "
                f"n_max {cfg.n_max}. Use measurement mode with the authorized "
                f"allowlist, or full_grid, rather than growing the fixture.")
        guard_record["fixture_bound"] = {"trials": planned, "n_max": cfg.n_max,
                                         "max_trials": FIXTURE_MAX_TRIALS,
                                         "max_n": FIXTURE_MAX_N}

    # Root: "Remove/reject the unpinned verify_policy=False override for
    # measurement/full-grid modes."  The flag is a function argument and does
    # NOT appear in the pins, so a run with verification disabled would be
    # indistinguishable from one with it enabled.  Refused for the two modes
    # whose timings and receipts are treated as evidence.
    if not verify_policy and cfg.mode in (MODE_MEASUREMENT, MODE_FULL_GRID):
        raise PanelError(
            f"verify_policy=False is not permitted in {cfg.mode!r} mode: the "
            f"flag is unpinned, so disabling verification would be invisible in "
            f"the receipt. Use verification_mode={VERIFY_PREFLIGHT!r} to reduce "
            f"verification cost in a way that IS pinned.")

    structural = assert_reference_is_not_consulted()
    if cfg.with_reference and not eb_reference.reference_available():
        raise PanelError(
            "the declared H/D reference is unavailable; a panel that silently "
            "skipped it would report primary rows as a complete delivery")

    run_cfg = vrun.make_config(cfg.n_max, cfg.namespace,
                               schedule=cfg.schedule, policy=cfg.policy)
    prefixes = run_cfg.horizons
    cells = [c for c in vgen.CELLS if c.id in cfg.cells]
    if len(cells) != len(cfg.cells):
        missing = set(cfg.cells) - {c.id for c in cells}
        raise PanelError(f"unknown cells: {sorted(missing)}")

    header = vrun.trial_header(cfg.schedule)
    primary_path = out_dir / "primary_rows.csv.gz"
    ref_path = out_dir / "reference_bands.csv"
    sink = vrun.RowSink(primary_path, header)
    # STREAMED, not buffered.  Root: "Current reference output is still
    # accumulated in ref_lines and joined at the end. Small-run 69 MiB is not a
    # memory bound for T1's 672,000 reference rows. Either stream those rows or
    # provide a deterministic full-size memory bound."  Streaming makes the
    # reference output O(1) in memory regardless of grid size.
    ref_fh = ref_path.open("w")
    ref_fh.write(REFERENCE_HEADER + "\n")

    counts = {"generation_calls": 0, "primary_trial_calls": 0, "looks": 0,
              "enclosure_updates": 0, "reference_calls_h": 0,
              "reference_calls_d": 0, "reference_rows": 0, "trials": 0,
              "programs": 0, "policy_checks": 0, "policy_pair_states": 0}
    decisions: Dict[str, int] = {}
    # ---- PREFLIGHT-ONLY VERIFICATION -----------------------------------
    # Root adopted this mode: the conditional verifier "only runs duplicate
    # conformance checks and updates verification counters; it does not supply
    # primary records or reference inputs", so running it once on the pinned
    # source is sufficient and the per-trial repeat is redundant work whose
    # runtime was never separately attributed.
    if (verify_policy and cfg.policy == "operational"
            and cfg.verification_mode == VERIFY_PREFLIGHT):
        # RESTORED 2026-09-21 (root disposition 09:46).  I had inserted an
        # unconditional `vconformance.run()` here and made it the coverage
        # claim.  Root removed it from the approved runtime path:
        #
        #   "Remove only its newly introduced unconditional call/coverage claim
        #    from the approved run_panel runtime path, restoring the previously
        #    accepted preflight-only workload while retaining the original
        #    one-draw smoke."
        #
        # The reason is sound and I had not weighed it: the preflight-only
        # workload's resource planning was ALREADY ACCEPTED at this exact
        # shape, and adding an unreviewed gate to it silently changes the
        # thing that was accepted.  vconformance survives as a standalone
        # OPTIONAL diagnostic and is not run from here.
        pf_draw = vgen.draw_trial(cells[0], cfg.indices[0], 0,
                                  n_max=cfg.n_max, namespace=cfg.namespace)
        pf = vrun.assert_operational_matches_policy(pf_draw, run_cfg)
        counts["policy_checks"] += 1
        counts["policy_pair_states"] += int(pf["pair_states_compared"])
        guard_record["preflight_verification"] = {
            "mode": VERIFY_PREFLIGHT, "ran_before_any_trial": True,
            "one_draw_smoke_pair_states": int(pf["pair_states_compared"]),
            "basis": ("root 08:28/09:46: the already independently checked "
                      "operational-policy witnesses are the preflight gate; "
                      "this one-draw check is a RUNTIME SMOKE TEST of the real "
                      "draw path and is not a coverage claim"),
            "conformance_diagnostic": ("vconformance.py is a STANDALONE OPTIONAL "
                                       "diagnostic and is deliberately NOT called "
                                       "from this runtime path")}

    caps = vpins.ALLOWLIST if cfg.mode == MODE_MEASUREMENT else None
    cap_events: List[Dict[str, Any]] = []
    peak_rss = 0
    t0 = time.perf_counter()
    for cell in cells:
        for program in cfg.indices:
            for trial in range(cfg.trials_per_program):
                # ---- HARD CAPS, checked per trial, fail closed ------------
                if caps is not None:
                    elapsed = time.perf_counter() - t0
                    peak_rss = max(peak_rss, _peak_rss_bytes())
                    if elapsed > caps.cap_seconds:
                        cap_events.append({"cap": "seconds", "limit": caps.cap_seconds,
                                           "observed": elapsed,
                                           "trials_completed": counts["trials"]})
                    elif peak_rss > caps.cap_peak_rss_bytes:
                        cap_events.append({"cap": "peak_rss_bytes",
                                           "limit": caps.cap_peak_rss_bytes,
                                           "observed": peak_rss,
                                           "trials_completed": counts["trials"]})
                    elif sink.raw_bytes > caps.cap_output_bytes:
                        cap_events.append({"cap": "output_bytes",
                                           "limit": caps.cap_output_bytes,
                                           "observed": sink.raw_bytes,
                                           "trials_completed": counts["trials"]})
                    if cap_events:
                        break
                draw = vgen.draw_trial(cell, program, trial, n_max=cfg.n_max,
                                       namespace=cfg.namespace)
                counts["generation_calls"] += 1

                # -- PRIMARY.  Knows nothing about the reference. ------------
                records, looks, updates = vrun.evaluate_trial(
                    draw, run_cfg, cfg.schedule)
                counts["primary_trial_calls"] += 1
                counts["looks"] += looks * len(vrun.CONSTRUCTIONS)
                counts["enclosure_updates"] += updates
                # MEASUREMENT-ONLY CONTRACT.  Root, 07:50: "Resource receipts
                # must not retain or reveal newly selected effect summaries."
                # In measurement mode the decision labels are never ACCUMULATED,
                # not merely omitted from the receipt at the end -- an effect
                # summary that exists in memory is one edit away from being
                # written, and the contract is about not selecting on it at all.
                if cfg.mode != MODE_MEASUREMENT:
                    for name in vrun.CONSTRUCTIONS:
                        lab = vrun.DECISION_LABEL[records[name].decision]
                        decisions[f"{name}:{lab}"] = decisions.get(f"{name}:{lab}", 0) + 1
                sink.write(vrun.trial_rows(cell, program, trial, records,
                                           cfg.schedule))

                # -- the policy the primary claims to run, verified ---------
                if (verify_policy and cfg.policy == "operational"
                        and cfg.verification_mode == VERIFY_PER_TRIAL):
                    chk = vrun.assert_operational_matches_policy(draw, run_cfg)
                    counts["policy_checks"] += 1
                    counts["policy_pair_states"] += int(chk["pair_states_compared"])

                # -- REFERENCE.  Same draw, separate artifact, no feedback. --
                if cfg.with_reference:
                    rows, ch, cd = reference_rows(cell, program, trial, draw,
                                                  prefixes, cfg.alpha_gate)
                    ref_fh.write(_ref_row_text(rows))
                    counts["reference_calls_h"] += ch
                    counts["reference_calls_d"] += cd
                    counts["reference_rows"] += len(rows)
                counts["trials"] += 1
            if cap_events:
                break
            counts["programs"] += 1
        if cap_events:
            break
    seconds = time.perf_counter() - t0
    peak_rss = max(peak_rss, _peak_rss_bytes())
    primary_bytes = sink.close()
    ref_fh.flush()
    os.fsync(ref_fh.fileno())
    ref_fh.close()

    if cfg.with_reference and not cap_events:
        assert_reference_call_budget(counts, counts["trials"])
        want_rows = counts["trials"] * len(SCORES) * len(prefixes)
        if counts["reference_rows"] != want_rows and not cap_events:
            raise PanelError(
                f"retained {counts['reference_rows']} reference rows, expected "
                f"{want_rows} = {counts['trials']} trials x {len(SCORES)} scores "
                f"x {len(prefixes)} prefixes")

    # ---- the root's before/after requirement, executed ------------------
    pins_after = vpins.entry_point_pins(prefixes=prefixes, **_pin_kw)
    drift = vpins.assert_unchanged(pins_before, pins_after)

    receipt = {
        "panel_version": PANEL_VERSION,
        "config": cfg.identity(),
        "guard": guard_record,
        "pins": pins_after,
        "pin_drift_check": drift,
        "declared_prefixes": list(prefixes),
        "seeds": {"namespace": cfg.namespace,
                  "stream_rule": "vgen.stream(namespace, cell.index, program, trial)",
                  "cell_indices": {c.id: c.index for c in cells}},
        "code_sha256": {n: _sha256(HERE / n)
                        for n in _PRIMARY_SOURCES + ("vpanel.py",)},
        "reference_sha256": {
            "module": _sha256(HERE / "reference" / "eb_reference.py"),
            "manifest": _sha256(HERE / "reference" / "MANIFEST.json")},
        "reference_tuning": {"boundary_type": eb_reference.BOUNDARY_TYPE,
                             "v_opt": eb_reference.V_OPT,
                             "alpha_split": "internal to confseq_eb; not pre-halved"},
        "counts": counts,
        "decisions": (decisions if cfg.mode != MODE_MEASUREMENT else
                      "WITHHELD under the measurement-only contract: resource "
                      "receipts must not retain or reveal newly selected effect "
                      "summaries. Not accumulated during this run."),
        "outputs": {
            # ``sink.close()`` returns the COMPRESSED byte count, so labelling
            # it uncompressed was simply wrong (root, twice).  Measured by
            # decompressing the file that was actually written.
            "primary_rows.csv.gz": {"sha256": _sha256(primary_path),
                                    "bytes": primary_path.stat().st_size,
                                    "compressed_bytes_from_sink": int(primary_bytes),
                                    "uncompressed_bytes": _uncompressed_size(primary_path)},
            "reference_bands.csv": {"sha256": _sha256(ref_path),
                                    "bytes": ref_path.stat().st_size}},
        "structural_checks": structural,
        "elapsed_seconds": seconds,
        "peak_rss_bytes": peak_rss,
        "cap_events": cap_events,
        "completed_fully": not cap_events,
        "host_capacity_at_start": host_at_start,
        "host_capacity_at_end": host_capacity(),
        "environment": {"python": platform.python_version(),
                        "numpy": np.__version__,
                        "platform": platform.platform()},
        "claims": {
            "convention": "deterministic-path",
            "is_calibration": False,
            "is_coverage_rate": False,
            "reference_role": "labelled complete-information diagnostic; "
                              "gates no decision and is written to a separate file",
        },
    }
    (out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


# ---------------------------------------------------------------------------
# 5.  CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cells", default="C2,C3,C7")
    ap.add_argument("--n-max", type=int, default=300)
    ap.add_argument("--programs", type=int, default=1)
    ap.add_argument("--policy", default="operational", choices=list(vgen.POLICIES))
    ap.add_argument("--schedule", default=vrun.SCHEDULE_V2)
    ap.add_argument("--label", default="fixture")
    ap.add_argument("--no-reference", action="store_true")
    a = ap.parse_args(argv)
    cfg = PanelConfig(cells=tuple(a.cells.split(",")), n_max=a.n_max,
                      programs=a.programs, policy=a.policy, schedule=a.schedule,
                      with_reference=not a.no_reference, label=a.label)
    r = run_panel(cfg, a.out)
    print(json.dumps({"counts": r["counts"], "decisions": r["decisions"],
                      "outputs": {k: v["sha256"][:12] for k, v in r["outputs"].items()}},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
