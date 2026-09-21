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
    # Root: "Add vmeasure.py, vsupervise.py and the final launcher/preflight
    # code to explicit whole-file pins."  These execute during a measured pass
    # and were omitted, so the pin described less than what ran.
    "supervisor_and_driver": ("vsupervise.py", "vmeasure.py"),
    # Root: "Include vshard.py and the final production runner in whole-file pins."
    "shard_executor_and_runner": ("vshard.py", "vprod.py"),
    "conformance_preflight": ("vconformance.py",),
    "launcher": ("vlaunch.py",),
    # Root's 15:14 provenance review: the pin method is CALLED
    # whole_file_pins_of_complete_entry_point, and its map omitted the actual
    # supervised entrypoint and the module that MUTATES vgen's runtime law
    # tables and constructs the cells.  An unchanged, pinned vgen.py does not
    # pin those runtime definitions -- so the pin named a completeness it did
    # not have.  That is this project's recurring defect shape, in the very
    # mechanism built to prevent it.
    "power_curve_entrypoint": ("vpowercurve.py", "run_powercurve.py"),
    # The certificate-ablation arm REPLACES a function inside the pinned
    # primary module at runtime.  An unchanged, pinned vgen.py does not describe
    # what evaluated the disabled arm -- the same hole the power-curve entry
    # point had -- so the operator and its driver are pinned by name here, and
    # `run_identity.variant` below records WHICH arm a receipt belongs to.
    "ablation_entrypoint": ("vablation.py", "run_ablation.py"),
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


#: Modules whose ACTUALLY LOADED files must be pinned, by import-name prefix.
#: Root: "hashing reference/MANIFEST.json does not check the actual vendored
#: Python it describes. Validate actual loaded comparecast/confseq Python files
#: and compiled module origins/digests, INCLUDING CACHED IMPORTS; do not merely
#: hash a glob of candidate binaries."
LOADED_MODULE_PREFIXES = ("comparecast", "confseq")


def loaded_reference_pins() -> Dict[str, Any]:
    """Digest every file the reference implementation is ACTUALLY loaded from.

    The previous pin hashed ``reference/MANIFEST.json`` (a description) and a
    GLOB of candidate ``.so`` files (candidates, not the loaded one). Neither
    establishes which bytes ran. This imports the reference, then reads
    ``sys.modules`` and pins each real ``__file__``, so a second copy on the
    path, a stale ``.pyc``, or a differently-built ``.so`` cannot hide.

    Raises rather than returning a partial map: an unpinned loaded module is a
    hole, and a hole that reports success is the defect this project keeps
    finding.
    """
    from reference import eb_reference                        # noqa: E402
    eb_reference.load_reference()                             # force the import

    files: Dict[str, str] = {}
    origins: Dict[str, str] = {}
    unpinnable: List[str] = []
    for name, mod in sorted(sys.modules.items()):
        if not any(name == p or name.startswith(p + ".")
                   for p in LOADED_MODULE_PREFIXES):
            continue
        f = getattr(mod, "__file__", None)
        if not f:
            unpinnable.append(f"{name} (no __file__)")
            continue
        path = Path(f)
        if not path.is_file():
            unpinnable.append(f"{name} -> {f} (missing)")
            continue
        files[name] = _sha256(path)
        origins[name] = str(path)
        # a cached bytecode file that shadows the source is pinned too
        cached = getattr(mod, "__cached__", None)
        if cached and Path(cached).is_file():
            files[f"{name}::__pycache__"] = _sha256(Path(cached))
            origins[f"{name}::__pycache__"] = str(cached)
    if unpinnable:
        raise PinError(
            f"loaded reference modules could not be pinned: {unpinnable}. "
            f"An unpinned loaded module means the executed bytes are unknown.")
    if not any(o.endswith(".so") or o.endswith(".pyd") for o in origins.values()):
        raise PinError(
            "no COMPILED reference module was found among the loaded modules; "
            "the vendored native boundary implementation must be pinned by the "
            "file actually imported, not by a glob of candidates")
    if not files:
        raise PinError("no reference module was loaded; nothing to pin")
    return {"files": files, "origins": origins,
            "module_count": len(origins),
            "aggregate_sha256": _aggregate(files),
            "method": "sys.modules __file__/__cached__ after forcing the import"}


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
    # Candidate binaries are recorded for completeness, but they are CANDIDATES.
    # What binds is `loaded_reference_pins()`, which pins the module actually
    # imported. A glob can match a file nothing loads and miss the one that ran.
    binaries: Dict[str, str] = {}
    for pattern in PINNED_BINARY_GLOBS:
        for p in sorted(HERE.glob(pattern)):
            binaries[str(p.relative_to(HERE))] = _sha256(p)
    loaded = loaded_reference_pins()
    config = {name: _sha256(HERE / name) for name in PINNED_CONFIG
              if (HERE / name).is_file()}
    missing_cfg = [n for n in PINNED_CONFIG if not (HERE / n).is_file()]
    if missing_cfg:
        raise PinError(f"pinned config missing: {missing_cfg}")
    return {"roles": roles, "files": files,
            "candidate_binaries_not_authoritative": binaries,
            "loaded_reference_modules": loaded,
            "config": config,
            "aggregate_sha256": _aggregate(
                {**files, **loaded["files"], **config})}


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
                     workload: str,
                     verification_mode: str = "unspecified",
                     reference_mode: str = "unspecified",
                     normalized_horizon: int = 0,
                     expected_trials: int = 0,
                     expected_reference_calls: int = 0,
                     variant: str = "original",
                     law_weights: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        # Root: "Code pins alone cannot distinguish the expensive
        # per-trial-verification run from a preflight-only run of the same
        # file. Add an explicit pinned verification policy before interpreting
        # any new timing."
        "verification_mode": verification_mode,
        "reference_mode": reference_mode,
        "normalized_horizon": int(normalized_horizon),
        "expected_trial_evaluations": int(expected_trials),
        "expected_reference_calls": int(expected_reference_calls),
        # WHICH ESTIMATOR ARM produced the receipt.  Two arms that share every
        # source file, every coordinate and every config differ only by a runtime
        # rebinding, so without this key their receipt digests would be equal and
        # a disabled-arm record would be indistinguishable from an original one.
        "variant": variant,
        # The laws P05/P10 are registered into vgen's RUNTIME tables by
        # vpowercurve; vgen.py's pinned bytes do not contain them.  Recording the
        # realised integer weights is what pins the law actually sampled.
        "law_weights": law_weights if law_weights is not None else {},
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
