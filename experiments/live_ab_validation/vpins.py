"""WHOLE-FILE pins for the COMPLETE entry point, and the bounded-measurement contract.

Root ruling, 2026-09-21 (`reviews/v2_panel_root_disposition_20260921_0750.md`):

    "For automatic execution binding, use exact immutable source/config/workload and
     loaded-reference/binary/environment pins for the actual complete entry point.
     WHOLE-FILE PINS ARE ADEQUATE AND SIMPLER HERE. Include the orchestrator, primary
     modules, reference bridge and relevant vendored implementation, output/accumulator
     code and guard, with explicit policy/schedule/prefix/program identities. Verify the
     same inputs before and after measurement."

This replaces `videntity.identities()`, which the root refuted and which is now removed.
The contrast is deliberate: a whole-file pin moves when a comment moves, and that is
accepted. The root's remedy for a documentation-only change is *"an explicit bounded
review linking the prior receipt to the new commit without remeasurement"* -- a human
decision on the record -- **not** an automatic call-graph gate that decides for itself
which edits matter. A pin that is occasionally too strict is recoverable by review; a
fingerprint that silently misses a changed constant is not.

Nothing here measures anything or authorizes anything on its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

#: THE COMPLETE ENTRY POINT, by role, exactly as the root enumerated it.  A file
#: that executes during a measured pass and is absent here is a hole in the pin,
#: so the roles are spelled out rather than globbed.
PINNED_SOURCES: Dict[str, Tuple[str, ...]] = {
    "orchestrator": ("vpanel.py",),
    "primary": ("vrun.py", "vgen.py", "vband.py", "vpolicy.py"),
    "reference_bridge": ("reference/eb_reference.py", "reference/vendor.py"),
    "output_accumulator": ("vpanel.py", "vrun.py"),     # RowSink + band writer
    "guard": ("vrun.py", "vtotalguard.py", "vresource_check.py", "vpins.py"),
    "diagnostic_not_authorizing": ("videntity.py",),
}

#: The vendored reference implementation actually loaded.  The compiled artifact
#: is pinned by digest too: a rebuilt .so is a different implementation even when
#: every .py above is byte-identical.
PINNED_VENDORED = ("reference/MANIFEST.json",)
PINNED_BINARY_GLOBS = ("reference/_build/*.so",)

PINNED_CONFIG = ("cells.json", "PROTOCOL_V2.md")


class PinError(RuntimeError):
    """A pin could not be formed, or drifted across a measurement."""


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(("git",) + args, cwd=str(REPO_ROOT),
                              capture_output=True, text=True).stdout.strip()
    except OSError:                                            # pragma: no cover
        return ""


def source_pins() -> Dict[str, Any]:
    """Whole-file digests for every role, plus the vendored binary."""
    files: Dict[str, str] = {}
    roles: Dict[str, List[str]] = {}
    for role, names in PINNED_SOURCES.items():
        roles[role] = list(names)
        for name in names:
            p = HERE / name
            if not p.is_file():
                raise PinError(f"pinned source missing: {p}")
            files[name] = _sha256(p)
    for name in PINNED_VENDORED:
        p = HERE / name
        if not p.is_file():
            raise PinError(f"pinned vendored file missing: {p}")
        files[name] = _sha256(p)
    binaries: Dict[str, str] = {}
    for pattern in PINNED_BINARY_GLOBS:
        for p in sorted(HERE.glob(pattern)):
            binaries[str(p.relative_to(HERE))] = _sha256(p)
    if not binaries:
        raise PinError(
            "no compiled reference artifact found; the loaded implementation "
            "would be unpinned and a rebuilt binary would be invisible")
    config = {name: _sha256(HERE / name) for name in PINNED_CONFIG
              if (HERE / name).is_file()}
    missing_cfg = [n for n in PINNED_CONFIG if not (HERE / n).is_file()]
    if missing_cfg:
        raise PinError(f"pinned config missing: {missing_cfg}")
    return {"roles": roles, "files": files, "binaries": binaries,
            "config": config,
            "aggregate_sha256": _aggregate({**files, **binaries, **config})}


def _aggregate(d: Dict[str, str]) -> str:
    h = hashlib.sha256()
    for k in sorted(d):
        h.update(f"{k}:{d[k]}\n".encode())
    return h.hexdigest()


def environment_pins() -> Dict[str, Any]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "executable_sha256_note": "interpreter not hashed; version pinned above",
    }


def repo_pins() -> Dict[str, Any]:
    dirty = _git("status", "--porcelain", "--",
                 "experiments/live_ab_validation")
    return {"head": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "validation_tree_dirty": bool(dirty),
            "dirty_paths": dirty.splitlines()}


def entry_point_pins(policy: str, schedule: str,
                     prefixes: Sequence[int],
                     programs: Sequence[int],
                     cells: Sequence[str],
                     namespace: int,
                     alpha_gate: float,
                     trials_per_program: int,
                     workload: str) -> Dict[str, Any]:
    """The five guard identities plus everything the root enumerated.

    ``code`` is the WHOLE-FILE aggregate over the complete entry point, not a
    call-graph fingerprint.
    """
    src = source_pins()
    run_identity = {
        "policy": policy, "schedule": schedule,
        "prefixes": list(prefixes), "programs": list(programs),
        "cells": list(cells), "namespace": namespace,
        "alpha_gate": alpha_gate, "trials_per_program": trials_per_program,
    }
    return {
        "code": src["aggregate_sha256"],
        "config": _aggregate(src["config"]),
        "policy": policy,
        "workload": workload,
        "receipt": _aggregate({"run": json.dumps(run_identity, sort_keys=True)}),
        "detail": {"source": src, "environment": environment_pins(),
                   "repo": repo_pins(), "run_identity": run_identity},
        "binding_method": "whole_file_pins_of_complete_entry_point",
        "not_used": ("videntity call-graph fingerprint; refuted 2026-09-21 and "
                     "retained only as an exploratory source-difference diagnostic"),
    }


def assert_unchanged(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """The root's before/after requirement, executed rather than promised.

    Returns the comparison so a caller cannot mistake "I did not check" for
    "nothing moved".
    """
    keys = ("code", "config", "policy", "workload", "receipt")
    moved = [k for k in keys if before.get(k) != after.get(k)]
    b_files = before.get("detail", {}).get("source", {}).get("files", {})
    a_files = after.get("detail", {}).get("source", {}).get("files", {})
    moved_files = sorted(k for k in set(b_files) | set(a_files)
                         if b_files.get(k) != a_files.get(k))
    if moved or moved_files:
        raise PinError(
            f"source or identity drifted ACROSS the measurement: "
            f"identities {moved}, files {moved_files}. The timing therefore "
            f"does not describe a single fixed executable and is discarded.")
    return {"identities_compared": list(keys),
            "files_compared": sorted(set(b_files) | set(a_files)),
            "drift": False}


# ---------------------------------------------------------------------------
# The bounded-measurement contract, transcribed from the root's authorization
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MeasurementAllowlist:
    """The ONLY coordinates a measurement-mode run may touch.

    Transcribed verbatim from the 07:50 authorization:

        "namespace 1, cells C1 and C2, program indices 1000-1004, horizons 1000
         and 2000, all four trials, operational policy and the declared all-tick
         schedule. These are 20 cell/program/horizon units with ten distinct
         seed-program identities. Perform one complete pass initially: 80 trial
         evaluations and 160 reference calls"

    Frozen. A run that proposes anything else is refused, not clamped: silently
    pricing one workload and running another is the defect this exists to stop.
    """

    namespace: int = 1
    cells: Tuple[str, ...] = ("C1", "C2")
    programs: Tuple[int, ...] = (1000, 1001, 1002, 1003, 1004)
    horizons: Tuple[int, ...] = (1000, 2000)
    trials_per_program: int = 4
    policy: str = "operational"
    expected_units: int = 20
    expected_trial_evaluations: int = 80
    expected_reference_calls: int = 160

    #: Hard caps, no larger than existing project caps.
    cap_seconds: float = 300.0
    cap_peak_rss_bytes: int = 2 * 1024 ** 3
    cap_output_bytes: int = 200 * 1024 ** 2

    def check_arithmetic(self) -> Dict[str, int]:
        units = len(self.cells) * len(self.programs) * len(self.horizons)
        trials = units * self.trials_per_program
        refs = trials * 2
        seeds = len(self.cells) * len(self.programs)
        if (units != self.expected_units
                or trials != self.expected_trial_evaluations
                or refs != self.expected_reference_calls):
            raise PinError(
                f"the allowlist does not reproduce the authorized counts: "
                f"units {units} vs {self.expected_units}, trials {trials} vs "
                f"{self.expected_trial_evaluations}, reference calls {refs} vs "
                f"{self.expected_reference_calls}")
        return {"units": units, "trial_evaluations": trials,
                "reference_calls": refs, "seed_program_identities": seeds}

    def refuse_unless_allowed(self, *, namespace: int, cells: Sequence[str],
                              programs: Sequence[int], horizon: int,
                              trials_per_program: int, policy: str) -> None:
        bad: List[str] = []
        if namespace != self.namespace:
            bad.append(f"namespace {namespace} (allowed {self.namespace})")
        extra = sorted(set(cells) - set(self.cells))
        if extra:
            bad.append(f"cells {extra} (allowed {list(self.cells)})")
        p_extra = sorted(set(programs) - set(self.programs))
        if p_extra:
            bad.append(f"programs {p_extra} (allowed {list(self.programs)})")
        if horizon not in self.horizons:
            bad.append(f"horizon {horizon} (allowed {list(self.horizons)})")
        if trials_per_program != self.trials_per_program:
            bad.append(f"trials_per_program {trials_per_program}")
        if policy != self.policy:
            bad.append(f"policy {policy!r} (allowed {self.policy!r})")
        if bad:
            raise PinError(
                "MEASUREMENT ALLOWLIST REFUSED: " + "; ".join(bad)
                + ". The authorized development coordinates are fixed; a run "
                  "outside them is not the authorized measurement and is not "
                  "clamped into it.")


ALLOWLIST = MeasurementAllowlist()


def main(argv: Optional[List[str]] = None) -> int:      # pragma: no cover
    print(json.dumps(entry_point_pins(
        policy="operational", schedule="v2_tick_batched", prefixes=[100, 500],
        programs=list(ALLOWLIST.programs), cells=list(ALLOWLIST.cells),
        namespace=ALLOWLIST.namespace, alpha_gate=0.00625,
        trials_per_program=4, workload="eight_call"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
