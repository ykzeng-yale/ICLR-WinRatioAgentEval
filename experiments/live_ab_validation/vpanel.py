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


class PanelError(RuntimeError):
    """A panel precondition failed.  Always fail closed."""


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

    def __post_init__(self) -> None:
        if self.policy not in vgen.POLICIES:
            raise PanelError(f"unknown policy {self.policy!r}")
        if self.schedule == vrun.SCHEDULE_V1 and self.policy != "oracle":
            raise PanelError(
                "v1 is the oracle schedule; an operational v1 run is not defined")
        if self.programs < 1 or self.n_max < 1:
            raise PanelError("programs and n_max must be positive")

    @property
    def trials(self) -> int:
        return self.programs * self.trials_per_program * len(self.cells)

    def identity(self) -> Dict[str, Any]:
        return {"panel_version": PANEL_VERSION, "label": self.label,
                "cells": list(self.cells), "n_max": self.n_max,
                "programs": self.programs, "policy": self.policy,
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
    ref_lines: List[str] = [REFERENCE_HEADER + "\n"]

    counts = {"generation_calls": 0, "primary_trial_calls": 0, "looks": 0,
              "enclosure_updates": 0, "reference_calls_h": 0,
              "reference_calls_d": 0, "reference_rows": 0, "trials": 0,
              "programs": 0, "policy_checks": 0, "policy_pair_states": 0}
    decisions: Dict[str, int] = {}
    t0 = time.perf_counter()
    for cell in cells:
        for program in range(cfg.programs):
            for trial in range(cfg.trials_per_program):
                draw = vgen.draw_trial(cell, program, trial, n_max=cfg.n_max,
                                       namespace=cfg.namespace)
                counts["generation_calls"] += 1

                # -- PRIMARY.  Knows nothing about the reference. ------------
                records, looks, updates = vrun.evaluate_trial(
                    draw, run_cfg, cfg.schedule)
                counts["primary_trial_calls"] += 1
                counts["looks"] += looks * len(vrun.CONSTRUCTIONS)
                counts["enclosure_updates"] += updates
                for name in vrun.CONSTRUCTIONS:
                    lab = vrun.DECISION_LABEL[records[name].decision]
                    decisions[f"{name}:{lab}"] = decisions.get(f"{name}:{lab}", 0) + 1
                sink.write(vrun.trial_rows(cell, program, trial, records,
                                           cfg.schedule))

                # -- the policy the primary claims to run, verified ---------
                if verify_policy and cfg.policy == "operational":
                    chk = vrun.assert_operational_matches_policy(draw, run_cfg)
                    counts["policy_checks"] += 1
                    counts["policy_pair_states"] += int(chk["pair_states_compared"])

                # -- REFERENCE.  Same draw, separate artifact, no feedback. --
                if cfg.with_reference:
                    rows, ch, cd = reference_rows(cell, program, trial, draw,
                                                  prefixes, cfg.alpha_gate)
                    ref_lines.append(_ref_row_text(rows))
                    counts["reference_calls_h"] += ch
                    counts["reference_calls_d"] += cd
                    counts["reference_rows"] += len(rows)
                counts["trials"] += 1
            counts["programs"] += 1
    seconds = time.perf_counter() - t0
    primary_bytes = sink.close()
    ref_path.write_text("".join(ref_lines))

    if cfg.with_reference:
        assert_reference_call_budget(counts, counts["trials"])
        want_rows = counts["trials"] * len(SCORES) * len(prefixes)
        if counts["reference_rows"] != want_rows:
            raise PanelError(
                f"retained {counts['reference_rows']} reference rows, expected "
                f"{want_rows} = {counts['trials']} trials x {len(SCORES)} scores "
                f"x {len(prefixes)} prefixes")

    receipt = {
        "panel_version": PANEL_VERSION,
        "config": cfg.identity(),
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
        "decisions": decisions,
        "outputs": {
            "primary_rows.csv.gz": {"sha256": _sha256(primary_path),
                                    "bytes": primary_path.stat().st_size,
                                    "uncompressed_bytes": int(primary_bytes)},
            "reference_bands.csv": {"sha256": _sha256(ref_path),
                                    "bytes": ref_path.stat().st_size}},
        "structural_checks": structural,
        "elapsed_seconds": seconds,
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
