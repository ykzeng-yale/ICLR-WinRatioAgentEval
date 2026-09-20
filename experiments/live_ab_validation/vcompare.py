#!/usr/bin/env python3
"""vcompare.py -- PROTOCOL.md section 12: the pinned comparison of #12 against #11.

This is the ONLY module of ``experiments/live_ab_validation/`` permitted to load the
pinned read-only copy of the #11 monitor (PROTOCOL 12.1 item 3, 13.0).  Every other
module of this directory is forbidden to reach it, and ``F16_import_graph_independence``
plus ``tests_validation.TestImportGraphIndependence`` enforce that mechanically, with
this file named as the single declared exception.  Nothing here is imported by any of
them.

WHAT THIS MODULE DOES
---------------------
1. Verifies every file in ``pinned/`` against ``pinned/PINNED.json`` by SHA-256 and
   REFUSES TO RUN if any digest differs, or if the manifest's file list is not exactly
   the set of Python sources present there.  Only then is the pinned copy imported.
2. Regenerates the frozen comparison streams of PROTOCOL 12.2 -- namespace 2, 25 per
   cell -- exactly as PROTOCOL sections 4 and 5 define them, and additionally captures
   the fixture streams of section 11 straight out of ``vfixtures`` without editing it.
3. Drives the #12 implementation (``vband``) and the pinned #11 implementation over the
   SAME event stream, each building its OWN objects with its OWN constructors.  Neither
   side is ever fed a state built by the other (PROTOCOL 12.2, "each side builds its own
   state").
4. Compares, at every look: the four band endpoints to the frozen absolute tolerance
   1e-12, the decision label EXACTLY under the frozen bijection, the decision prefix
   ``tau`` EXACTLY, and every per-pair enclosure endpoint to 1e-12.

WHAT A DISAGREEMENT MEANS -- PROTOCOL 12.3, IMPLEMENTED LITERALLY
-----------------------------------------------------------------
A disagreement is a DEFECT.  It is reported with its minimal reproducing stream, the two
disagreeing values, and the guidance clause each side appears to implement.  IT IS NEVER
RECONCILED BY EDITING EITHER SIDE -- not the band module, not the enclosure rules, not
the tolerance, not the fixture streams, not the protocol.  WHICH SIDE IS WRONG IS NOT
DECIDED HERE; it is escalated to the coordinator and the root with the reproducer.  Until
a disagreement is adjudicated, #11's results do not count as validated.

AGREEMENT IS REPORTED AS AGREEMENT AND NEVER AS CORRECTNESS.  The frozen sentence is
"the two implementations agree on these N streams to 1e-12", never "the monitor is
correct": two implementations of the same misreading of the guidance agree perfectly and
this comparison cannot detect that (PROTOCOL 12.3 item 6).  Agreement on the cost-tier
narrowing specifically is worth less than the rest, because PREREG_CHECK disclosed #11's
cost certificate to the #12 author before this comparison was specified (12.3 item 7).
Every wording rule above is enforced by the text this module emits.

OUT OF SCOPE, NAMED RATHER THAN SILENT
--------------------------------------
* The ``certified`` / ``collapsed`` FLAG is not compared (PROTOCOL 1.3 item 8, 12.2).  The
  two sides hold incompatible definitions and section 6.4 says the difference is common
  rather than exotic, so comparing it would report one definitional difference thousands
  of times as a numerical defect.  The per-pair enclosure ENDPOINTS are compared.
* No look is taken at ``n = 0`` on either side: #12 displays the full range there and #11
  raises.  That structural difference is excluded by construction, not adjudicated.

CPU only.  No model call, no API call, no network, no new dependency.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PINNED_DIR = HERE / "pinned"
PINNED_MANIFEST = PINNED_DIR / "PINNED.json"
CELLS_PATH = HERE / "cells.json"
PROTOCOL_PATH = HERE / "PROTOCOL.md"
SRC_DIR = REPO_ROOT / "src"
#: PROTOCOL 13.1: the comparison writes ONLY inside this directory and a guard refuses
#: any path outside it.
RESULTS_ROOT = REPO_ROOT / "results" / "live_ab_validation"

#: PROTOCOL 12.2, frozen: endpoints lie in [-1, 1], so an absolute criterion is the
#: meaningful one.  The tolerance covers floating-point summation order only and is
#: itself frozen (12.3 item 5).
TOL = 1e-12

#: PROTOCOL 12.2, the frozen decision-label bijection, fixed before any stream was
#: replayed.  Anything outside this map is a disagreement, not an unmapped case.
LABEL_BIJECTION: Dict[Optional[str], str] = {
    None: "CONTINUE",                       # no decision returned
    "deploy_candidate": "DEPLOY",
    "harm_keep_incumbent": "RETAIN_INCUMBENT",
    "horizon_no_decision": "CONTINUE",      # plus: the #12 trial must end in NO_DECISION
}

#: The guidance clause both sides claim, quoted from
#: reviews/arxiv_live_design_guidance.md item 5 (the pinned formula source).
GUIDANCE_ITEM_5 = (
    "Start unresolved hierarchy scores at [-1,1], enumerate feasible completions to "
    "narrow them, and collapse only with a valid final-score certificate."
)
GUIDANCE_ITEM_3 = (
    "Use the normal-mixture primitive with guaranteed partial bounds. At a look and a "
    "selected enrollment prefix n, for each score j, use ... (the band of PROTOCOL 2.3)."
)


# =============================================================================
# 0.  Write guard (PROTOCOL 13.1)
# =============================================================================
class ComparisonRefusal(SystemExit):
    """The comparison refuses to run or to write.  Never downgraded to a warning."""


def guarded_out_dir(raw: str) -> Path:
    """Resolve the output directory and refuse anything outside the results tree."""
    out = Path(raw).expanduser()
    if not out.is_absolute():
        out = (Path.cwd() / out)
    out = out.resolve()
    root = RESULTS_ROOT.resolve()
    if out != root and not str(out).startswith(str(root) + os.sep):
        raise ComparisonRefusal(
            f"REFUSING TO RUN: --out {out} lies outside {root}. PROTOCOL 13.1 fixes that "
            f"this step writes only inside results/live_ab_validation/.")
    out.mkdir(parents=True, exist_ok=True)
    return out


def guarded_path(out_dir: Path, name: str) -> Path:
    p = (out_dir / name).resolve()
    root = RESULTS_ROOT.resolve()
    if not str(p).startswith(str(root) + os.sep):
        raise ComparisonRefusal(f"REFUSING TO WRITE outside the results tree: {p}")
    return p


# =============================================================================
# 1.  The frozen configuration (cells.json is normative for every numeric value)
# =============================================================================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class FrozenConfig:
    """Every number this module uses, read from cells.json rather than retyped."""

    alpha_gate: float
    rho: float
    delta: float
    n_min: int
    n_max: int
    drain_w: int
    finalization_tick: int
    cost_cap: float
    master_seed: int
    namespace: int
    streams_per_cell: int
    streams_total: int
    cells: Tuple[Dict[str, Any], ...]
    laws: Dict[str, Dict[str, Any]]
    atom_order: Tuple[str, ...]
    atoms: Tuple[Dict[str, Any], ...]
    short_lo: int
    short_hi: int
    long_lo: int
    long_hi: int
    raw: Dict[str, Any] = field(repr=False, default_factory=dict)


def load_frozen_config() -> FrozenConfig:
    cfg = json.loads(CELLS_PATH.read_text())
    p = cfg["parameters"]
    cmp_ = cfg["comparison_to_live_ab"]
    # The tolerance is frozen in prose in the machine-readable twin; assert it rather
    # than silently adopting whatever this module happens to hold.
    for key in ("L_h_U_h_L_s_U_s", "per_pair_enclosure_endpoints"):
        text = cmp_["compared_at_every_look"][key]
        if "1e-12" not in text:
            raise ComparisonRefusal(
                f"REFUSING TO RUN: cells.json comparison tolerance for {key} is {text!r}, "
                f"which does not name the frozen 1e-12 this module implements.")
    if cmp_["loaded_by_only"] != "experiments/live_ab_validation/vcompare.py":
        raise ComparisonRefusal(
            "REFUSING TO RUN: cells.json does not name this module as the only loader "
            "of the pinned copy.")
    if int(cmp_["streams"]["namespace"]) != 2:
        raise ComparisonRefusal("REFUSING TO RUN: the comparison namespace is not 2.")
    blocks = cfg["delay_blocks"]
    return FrozenConfig(
        alpha_gate=float(p["alpha_gate"]),
        rho=float(p["rho"]),
        delta=float(p["delta"]),
        n_min=int(p["n_min"]),
        n_max=int(p["N_max"]),
        drain_w=int(p["drain_W"]),
        finalization_tick=int(p["finalization_tick"]),
        cost_cap=float(p["cost_model"]["cost_cap"]),
        master_seed=int(cfg["seeding"]["master_seed"]),
        namespace=int(cmp_["streams"]["namespace"]),
        streams_per_cell=int(cmp_["streams"]["per_cell"]),
        streams_total=int(cmp_["streams"]["count"]),
        cells=tuple(cfg["cells"]),
        laws=cfg["outcome_laws"],
        atom_order=tuple(cfg["outcome_atoms"]["order"]),
        atoms=tuple(cfg["outcome_atoms"]["definition"]),
        short_lo=int(blocks["SHORT"]["low"]),
        short_hi=int(blocks["SHORT"]["high"]),
        long_lo=int(blocks["LONG"]["low"]),
        long_hi=int(blocks["LONG"]["high"]),
        raw=cfg,
    )


# =============================================================================
# 2.  The pinned copy: verify by hash, then and only then import
# =============================================================================
@dataclass
class PinnedLoad:
    manifest: Dict[str, Any]
    digests: Dict[str, str]
    lab_monitor: Any
    lab_enclosure: Any
    lab_common_present: bool


def verify_and_load_pinned(verbose: bool = True) -> PinnedLoad:
    """Hash every pinned source, compare against PINNED.json, then import.

    Refuses to run if a digest differs, if the manifest lists a file that is absent, or
    if a Python source is present that the manifest does not list.  A pinned copy whose
    digest no longer matches the manifest is not pinned, and a comparison against an
    unpinned copy is not the comparison PROTOCOL 12 specifies.
    """
    if not PINNED_MANIFEST.is_file():
        raise ComparisonRefusal(f"REFUSING TO RUN: {PINNED_MANIFEST} is absent.")
    manifest = json.loads(PINNED_MANIFEST.read_text())
    listed = dict(manifest.get("files") or {})
    present = sorted(p.name for p in PINNED_DIR.glob("*.py"))
    if sorted(listed) != present:
        raise ComparisonRefusal(
            f"REFUSING TO RUN: PINNED.json lists {sorted(listed)} but the directory holds "
            f"{present}. The manifest's file list must be exactly the Python sources "
            f"present (PROTOCOL 11, F18).")
    digests: Dict[str, str] = {}
    bad: List[str] = []
    for name, want in sorted(listed.items()):
        got = sha256_file(PINNED_DIR / name)
        digests[name] = got
        if got != want:
            bad.append(f"{name}: manifest {want}, file {got}")
    if bad:
        raise ComparisonRefusal(
            "REFUSING TO RUN: the pinned copy no longer matches PINNED.json:\n  "
            + "\n  ".join(bad))
    if verbose:
        print(f"[pinned] {len(digests)} files verified against PINNED.json "
              f"(live_ab commit {manifest.get('source_commit', '?')[:7]})")

    for extra in (str(SRC_DIR), str(PINNED_DIR)):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    # The pinned copy is READ-ONLY (mode 444).  Importing it would otherwise drop a
    # __pycache__ directory into that tree, so bytecode writing is switched off for the
    # duration of these two imports: nothing this module does leaves a trace inside
    # pinned/, and its digests stay exactly what PINNED.json recorded.
    previously = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import lab_enclosure as _enc      # noqa: E402  (verified by hash above)
        import lab_monitor as _mon        # noqa: E402
    finally:
        sys.dont_write_bytecode = previously

    for mod in (_enc, _mon):
        f = getattr(mod, "__file__", "")
        if not str(Path(f).resolve()).startswith(str(PINNED_DIR.resolve()) + os.sep):
            raise ComparisonRefusal(
                f"REFUSING TO RUN: {mod.__name__} was imported from {f}, which is not the "
                f"pinned copy this comparison verified.")
    return PinnedLoad(manifest=manifest, digests=digests, lab_monitor=_mon,
                      lab_enclosure=_enc,
                      lab_common_present=bool(getattr(_enc, "_LAB_COMMON_PRESENT", False)))


# =============================================================================
# 3.  The frozen data-generating process (PROTOCOL sections 4 and 5)
# =============================================================================
@dataclass(frozen=True)
class Stream:
    """One frozen comparison stream: the facts of PROTOCOL 4.1 to 4.3, nothing derived."""

    stream_id: str
    kind: str                       # 'cell' or 'fixture'
    cell_id: str
    cell_index: int
    namespace: int
    program: int
    trial: int
    n_max: int
    finalization_tick: int
    atom: np.ndarray                # atom index per pair
    s_cand: np.ndarray
    s_inc: np.ndarray
    c_cand: np.ndarray
    c_inc: np.ndarray
    d: np.ndarray                   # full-resolution offset
    f: np.ndarray                   # first-reveal offset
    cand_first: np.ndarray          # bool: the candidate is revealed first
    z_true: np.ndarray
    d_true: np.ndarray

    @property
    def coords(self) -> str:
        return f"{self.cell_id}:ns{self.namespace}:p{self.program}:t{self.trial}"


class FrozenGenerator:
    """PROTOCOL 4.1-4.3 and 5, transcribed literally and vectorised with numpy.

    The five draws, their order and their sizes are part of the seed's meaning
    (PROTOCOL 5): changing any of them changes every stream, so they are written here
    exactly as the protocol writes them and are never reordered or shortened.

    ``vgen.py`` is specified by PROTOCOL 13.0 to own this process and does not exist at
    the freeze commit.  This class therefore implements it for the comparison streams
    only; if ``vgen.py`` later appears, :func:`crosscheck_vgen` compares the two array
    by array and reports any difference rather than preferring one silently.
    """

    def __init__(self, cfg: FrozenConfig) -> None:
        self.cfg = cfg
        self.atom_index = {a["atom"]: i for i, a in enumerate(cfg.atoms)}
        self.s_cand = np.array([int(a["s_candidate"]) for a in cfg.atoms], dtype=np.int64)
        self.s_inc = np.array([int(a["s_incumbent"]) for a in cfg.atoms], dtype=np.int64)
        self.c_cand = np.array([float(a["c_candidate"]) for a in cfg.atoms])
        self.c_inc = np.array([float(a["c_incumbent"]) for a in cfg.atoms])
        self.z_atom = np.array([int(a["Z"]) for a in cfg.atoms], dtype=np.int64)
        self.d_atom = np.array([int(a["D"]) for a in cfg.atoms], dtype=np.int64)
        if tuple(a["atom"] for a in cfg.atoms) != cfg.atom_order:
            raise ComparisonRefusal(
                "REFUSING TO RUN: the atom definition order differs from the frozen "
                "cumulative-threshold order in cells.json.")

    def cell(self, cell_id: str) -> Dict[str, Any]:
        for c in self.cfg.cells:
            if c["id"] == cell_id:
                return c
        raise ComparisonRefusal(f"REFUSING TO RUN: unknown cell {cell_id!r}")

    def build(self, cell_id: str, program: int, trial: int,
              namespace: Optional[int] = None) -> Stream:
        cfg = self.cfg
        cell = self.cell(cell_id)
        law = cfg.laws[cell["law"]]
        ns = cfg.namespace if namespace is None else int(namespace)
        n = cfg.n_max

        ss = np.random.SeedSequence(
            entropy=cfg.master_seed,
            spawn_key=(ns, int(cell["cell_index"]), int(program), int(trial)))
        rng = np.random.Generator(np.random.PCG64(ss))
        # --- the frozen draw order (PROTOCOL 5); all five at full length -------------
        u_atom = rng.integers(0, 10000, size=n)
        u_delay = rng.integers(0, 40000, size=n)
        u_len = rng.random(size=n)
        u_first = rng.random(size=n)
        u_coin = rng.random(size=n)

        weights = np.array([int(law["weights"][a]) for a in cfg.atom_order], dtype=np.int64)
        if int(weights.sum()) != 10000:
            raise ComparisonRefusal(
                f"REFUSING TO RUN: law {cell['law']} weights sum to {int(weights.sum())}, "
                f"not the frozen 10000 denominator.")
        cum = np.cumsum(weights)
        atom = np.searchsorted(cum, u_atom, side="right").astype(np.int64)

        z = self.z_atom[atom]
        dd = self.d_atom[atom]
        w_neg = int(law["w_neg"])
        if cell["delay"] == "N":
            long_i = u_delay < (3 * w_neg)
        elif cell["delay"] == "A":
            long_i = (z == -1) & (u_delay < 30000)
        else:                                                   # pragma: no cover
            raise ComparisonRefusal(f"REFUSING TO RUN: unknown delay rule {cell['delay']!r}")

        span_long = cfg.long_hi - cfg.long_lo + 1                # 600
        span_short = cfg.short_hi - cfg.short_lo + 1             # 20
        d_i = np.where(long_i,
                       cfg.long_lo + np.floor(u_len * span_long).astype(np.int64),
                       cfg.short_lo + np.floor(u_len * span_short).astype(np.int64))
        f_i = np.floor(u_first * (d_i + 1)).astype(np.int64)
        cand_first = u_coin < 0.5

        return Stream(
            stream_id=f"{cell_id}:ns{ns}:p{program}:t{trial}", kind="cell",
            cell_id=cell_id, cell_index=int(cell["cell_index"]), namespace=ns,
            program=int(program), trial=int(trial), n_max=n,
            finalization_tick=cfg.finalization_tick,
            atom=atom, s_cand=self.s_cand[atom], s_inc=self.s_inc[atom],
            c_cand=self.c_cand[atom], c_inc=self.c_inc[atom],
            d=d_i, f=f_i, cand_first=cand_first, z_true=z, d_true=dd)


def comparison_stream_coords(cfg: FrozenConfig, per_cell: int) -> List[Tuple[str, int, int]]:
    """The frozen 25-per-cell enumeration, taken in lexicographic order.

    PROTOCOL 12.2 fixes the COUNT (25 per cell, 200 in all) and the NAMESPACE (2); it
    does not write out which (program, trial) coordinates those 25 are.  This module
    takes the first ``per_cell`` coordinates in lexicographic order of
    ``(program_index, trial_index)`` with the trial index fastest -- a rule that cannot
    have been chosen after seeing a stream, because it depends on nothing but the count.
    The choice is declared here, in the CSV, and in the summary.
    """
    coords: List[Tuple[str, int, int]] = []
    for cell in cfg.cells:
        for s in range(per_cell):
            coords.append((cell["id"], s // 4, s % 4))
    return coords


def crosscheck_vgen(gen: FrozenGenerator, sample: Sequence[Stream]) -> Dict[str, Any]:
    """If ``vgen.py`` exists, check that it produces the same arrays; never prefer one.

    ``vgen.py`` does not exist at the freeze commit (PROTOCOL 13.0) and its API is not
    fixed by the protocol, so this is a best-effort probe: it reports what it found and
    what it could not check, and it never silently substitutes one generator for the
    other.  A disagreement here is a generator defect and is reported as one.
    """
    out: Dict[str, Any] = {"vgen_present": (HERE / "vgen.py").is_file(),
                           "status": "absent", "checked_streams": 0, "mismatches": []}
    if not out["vgen_present"]:
        return out
    try:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import vgen                                              # type: ignore
    except Exception as exc:                                     # noqa: BLE001
        out["status"] = f"import failed: {type(exc).__name__}: {exc}"
        return out
    fn = getattr(vgen, "draw_trial", None)
    cells = getattr(vgen, "CELLS", None)
    if not callable(fn) or not cells:
        out["status"] = ("present, but no draw_trial(cell, program, trial) entry point "
                         "with a CELLS registry was found; CROSS-CHECK SKIPPED")
        return out
    #: only the primitives both sides derive the same way are compared; anything either
    #: side precomputes on top of them is that side's own business.
    fields = ("atom", "d", "f", "cand_first")
    for st in sample:
        cell_obj = next((c for c in cells
                         if getattr(c, "index", None) == st.cell_index), None)
        if cell_obj is None:
            out["status"] = "present, but its CELLS registry has no cell index to match"
            return out
        try:
            got = fn(cell_obj, st.program, st.trial, n_max=st.n_max,
                     namespace=st.namespace)
        except Exception as exc:                                 # noqa: BLE001
            out["status"] = f"draw_trial raised {type(exc).__name__}: {exc}"
            return out
        probe = getattr(got, "atom", None)
        if probe is None or np.asarray(probe).shape != (st.n_max,):
            out["status"] = ("present, but draw_trial did not return an object carrying "
                             "a per-pair 'atom' array; CROSS-CHECK SKIPPED")
            return out
        for name in fields:
            theirs = getattr(got, name, None)
            if theirs is None:
                out.setdefault("fields_not_exposed", []).append(name)
                continue
            if not np.array_equal(np.asarray(theirs), np.asarray(getattr(st, name))):
                out["mismatches"].append(f"{st.stream_id}:{name}")
        out["checked_streams"] += 1
    out["status"] = ("agrees on " + ", ".join(fields)) if not out["mismatches"] \
        else "DISAGREES -- generator defect"
    return out


# =============================================================================
# 4.  The two sides, each driven through its own constructors
# =============================================================================
class Side12:
    """The #12 implementation under test: ``vband``, and nothing else."""

    def __init__(self, cfg: FrozenConfig) -> None:
        import vband                                             # noqa: E402
        self.vband = vband
        self.cfg = cfg
        self.mon = vband.ValidationMonitor(
            cost_cap=cfg.cost_cap, alpha_gate=cfg.alpha_gate, rho=cfg.rho,
            delta=cfg.delta, n_min=cfg.n_min)
        # Enrollment-indexed mirrors of the monitor's OWN enclosure endpoints, kept so
        # that the band can be assembled without rebuilding the list at every look.
        # ``normal_mixture_band`` below is the monitor's own band function and
        # ``verify_band`` asserts the mirror against ``ValidationMonitor.band`` bit for
        # bit at the checkpoints of the run.
        self.lo_h: List[float] = []
        self.hi_h: List[float] = []
        self.lo_s: List[float] = []
        self.hi_s: List[float] = []

    # -- events ---------------------------------------------------------------
    def enroll(self, pair: int, cost_cap: Optional[float] = None) -> None:
        self.mon.enroll(pair, "AB", ("C", pair), ("I", pair), cost_cap=cost_cap)
        self.lo_h.append(-1.0)
        self.hi_h.append(1.0)
        self.lo_s.append(-1.0)
        self.hi_s.append(1.0)

    def reveal(self, pair: int, arm: str, success: int, cost: float) -> None:
        self.mon.finalize((("C" if arm == "candidate" else "I"), pair), int(success),
                          float(cost))

    def elapsed(self, pair: int, arm: str, ell: float) -> None:
        self.mon.observe_elapsed_cost((("C" if arm == "candidate" else "I"), pair),
                                      float(ell))

    def refresh(self, pair: int) -> Tuple[float, float, float, float]:
        p = self.mon.pairs[pair - 1]
        i = pair - 1
        self.lo_h[i] = p.hierarchy.lo
        self.hi_h[i] = p.hierarchy.hi
        self.lo_s[i] = p.success.lo
        self.hi_s[i] = p.success.hi
        return (p.hierarchy.lo, p.hierarchy.hi, p.success.lo, p.success.hi)

    # -- look -----------------------------------------------------------------
    def look(self) -> Tuple[Any, Any, str]:
        n = len(self.lo_h)
        bh = self.vband.normal_mixture_band(self.lo_h, self.hi_h, n,
                                            alpha_gate=self.cfg.alpha_gate,
                                            rho=self.cfg.rho, name="hierarchy")
        bs = self.vband.normal_mixture_band(self.lo_s, self.hi_s, n,
                                            alpha_gate=self.cfg.alpha_gate,
                                            rho=self.cfg.rho, name="success")
        label = self.vband.decide(bh, bs, delta=self.cfg.delta, n_min=self.cfg.n_min)
        return bh, bs, label

    def verify_band(self) -> Optional[str]:
        """Assert the incremental mirror against the monitor's own ``band()``."""
        for score, lows, highs in (("hierarchy", self.lo_h, self.hi_h),
                                   ("success", self.lo_s, self.hi_s)):
            a = self.mon.band(score)
            b = self.vband.normal_mixture_band(lows, highs, len(lows),
                                               alpha_gate=self.cfg.alpha_gate,
                                               rho=self.cfg.rho, name=score)
            if (a.lower, a.upper, a.sum_lower, a.sum_upper) != \
               (b.lower, b.upper, b.sum_lower, b.sum_upper):
                return (f"the incremental #12 mirror differs from "
                        f"ValidationMonitor.band({score!r}) at n={a.n}")
        return None


class Side11:
    """The pinned #11 implementation, built through ITS OWN constructors only."""

    def __init__(self, cfg: FrozenConfig, pinned: PinnedLoad, n_max: int) -> None:
        self.cfg = cfg
        self.mon_mod = pinned.lab_monitor
        self.enc_mod = pinned.lab_enclosure
        frozen_rows = [dict(row) for row in self.enc_mod._FROZEN_HIERARCHY]
        cfg_dict = {
            "rule_id": self.mon_mod.RULE_ID,
            "hierarchy": frozen_rows,
            "eligibility_rule": "lower_tiers_require_both_success",
            "tie_rule": "strict_gt_tolerance_so_exact_equality_is_a_tie",
            "roster": {"n_pairs": int(n_max)},
            "monitor": {
                "alpha_gate": cfg.alpha_gate, "rho": cfg.rho, "delta": cfg.delta,
                "n_min": cfg.n_min, "n_max": int(n_max), "clip": [-1.0, 1.0],
                "construction": "winstats.normal_mixture_radius",
                "variance_process": "n", "prefix": "current_full_enrolled",
                "retention": False, "running_intersection": False,
                "prefix_envelope": False, "maximize_over_prefixes": False,
                "harm_tail": "hierarchy_upper_only",
                "deploy_if": "L_h_gt_0_and_L_s_gt_minus_delta_at_same_prefix",
                "harm_if": "U_h_lt_0", "exploratory_margins_decide": False,
                "decision_order": ["harm_keep_incumbent", "deploy_candidate"],
            },
        }
        # Both objects are built by #11's own validating constructors, from a config
        # carrying #11's own frozen hierarchy rows -- never from #12 state.
        self.tiers = self.enc_mod.tiers_from_config(cfg_dict)
        self.mc = self.mon_mod.MonitorConfig.from_config(cfg_dict, trial="live_ab_validation")
        self.state = self.mon_mod.MonitorState(self.mc)
        self._cand: Dict[int, Any] = {}
        self._inc: Dict[int, Any] = {}

    # -- events ---------------------------------------------------------------
    def enroll(self, pair: int) -> None:
        self.state.enroll(pair)
        self._cand[pair] = self.enc_mod.EpisodeView.pending("candidate")
        self._inc[pair] = self.enc_mod.EpisodeView.pending("incumbent")

    def reveal(self, pair: int, arm: str, success: int, cost: float) -> None:
        view = self.enc_mod.EpisodeView.reveal(arm, int(success), float(cost), 0)
        if arm == "candidate":
            self._cand[pair] = view
        else:
            self._inc[pair] = view

    def elapsed(self, pair: int, arm: str, ell: float) -> None:
        """Raise the certified elapsed lower bound of a still-pending episode.

        Two semantics are taken from #11's own code rather than invented here.  An
        elapsed report for an ALREADY REVEALED episode is a no-op, because a revealed
        ``EpisodeView`` carries its exact ``latency_s`` and #11 has no pending state to
        put it back into.  A report that is SMALLER than one already seen is also a
        no-op, because #11's own ``certified_elapsed`` takes the MAXIMUM over the
        spooled stamps, so a stale report can never lower ``ell`` on the #11 side
        either.  Both match #12's ``Episode.with_elapsed_cost``.
        """
        held = self._cand[pair] if arm == "candidate" else self._inc[pair]
        if held.revealed:
            return
        new = self.enc_mod.EpisodeView.pending(
            arm, ell=max(float(held.ell), float(ell)),
            tokens_known=int(held.tokens_known))
        if arm == "candidate":
            self._cand[pair] = new
        else:
            self._inc[pair] = new

    def refresh(self, pair: int) -> Tuple[float, float, float, float]:
        enc = self.enc_mod.pair_enclosure(self._cand[pair], self._inc[pair], self.tiers)
        self.state.update(pair, enc)
        return (enc.h.lo, enc.h.hi, enc.s.lo, enc.s.hi)

    # -- look -----------------------------------------------------------------
    def look(self) -> Tuple[Any, Any, Optional[str]]:
        bands = self.state.bands()
        if bands is None:                                        # n == 0, excluded
            raise self.mon_mod.MonitorError("no look is taken at n = 0")
        bh, bs = bands
        decision = self.mon_mod.decide(self.state, self.mc)
        return bh, bs, (None if decision is None else decision.kind)


# =============================================================================
# 5.  Defect bookkeeping
# =============================================================================
DEFECT_FIELDS = [
    "defect_class", "guidance_ref", "stream_id", "kind", "cell", "namespace",
    "program", "trial", "tick", "n", "finalization", "quantity",
    "value_12", "value_11", "abs_diff", "pair_position", "atom",
    "revealed_arm", "d", "f", "age", "ell", "revealed_cost",
    "enc12_lo", "enc12_hi", "enc11_lo", "enc11_hi",
    "label_12", "label_11_raw", "exception_side", "exception_type",
    "exception_message", "replay_command",
]

LOOK_FIELDS = [
    "stream_id", "kind", "cell", "cell_index", "namespace", "program", "trial",
    "tick", "n", "finalization",
    "L_h_12", "U_h_12", "L_s_12", "U_s_12",
    "L_h_11", "U_h_11", "L_s_11", "U_s_11",
    "d_L_h", "d_U_h", "d_L_s", "d_U_s", "endpoints_within_tol",
    "label_12", "label_11_raw", "label_11_mapped", "labels_agree",
    "pairs_compared", "pairs_within_tol", "max_abs_pair_diff", "first_bad_pair",
    "checkpoint", "status",
]



def _shape_key(row: Dict[str, Any]) -> str:
    """A legible bucket for one defect row.

    Endpoint VALUES are bucketed only when they are the small integers an enclosure can
    take; a band endpoint is a different float at every look, so those rows are bucketed
    by the quantity alone rather than producing one bucket per row.
    """
    q = str(row.get("quantity", ""))
    v12, v11 = row.get("value_12", ""), row.get("value_11", "")

    def small(v) -> bool:
        try:
            return float(v) in (-1.0, 0.0, 1.0)
        except (TypeError, ValueError):
            return isinstance(v, str) and v != ""
    if small(v12) and small(v11):
        return f"{q}: #12={v12} #11={v11}"
    return q or "(unlabelled)"


@dataclass
class DefectLedger:
    """Every disagreement, its class, and the first (minimal) reproducer of each class."""

    rows: List[Dict[str, Any]] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    first: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    streams_with: Dict[str, set] = field(default_factory=dict)
    #: class -> "quantity: #12 value vs #11 value" -> count, so that the shape of a
    #: defect is legible without reopening the CSV.
    shapes: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # PROTOCOL 12.3 item 5: within tolerance but nonzero is NOT silently accepted.
    noted_n: int = 0
    noted_max: float = 0.0
    noted_signs: Dict[str, int] = field(default_factory=dict)

    def add(self, row: Dict[str, Any]) -> None:
        cls = row["defect_class"]
        self.counts[cls] = self.counts.get(cls, 0) + 1
        self.streams_with.setdefault(cls, set()).add(row["stream_id"])
        if cls not in self.first:
            self.first[cls] = dict(row)
        key = _shape_key(row)
        by_class = self.shapes.setdefault(cls, {})
        if key in by_class or len(by_class) < 40:
            by_class[key] = by_class.get(key, 0) + 1
        self.rows.append(row)

    def note_within_tolerance(self, diffs: Iterable[float]) -> None:
        for dv in diffs:
            if dv == 0.0:
                continue
            self.noted_n += 1
            self.noted_max = max(self.noted_max, abs(dv))
            key = "positive" if dv > 0 else "negative"
            self.noted_signs[key] = self.noted_signs.get(key, 0) + 1


def replay_command(st: Stream) -> str:
    if st.kind != "cell":
        return (f".venv/bin/python experiments/live_ab_validation/vcompare.py "
                f"--out results/live_ab_validation --only-fixture {st.stream_id}")
    return (f".venv/bin/python experiments/live_ab_validation/vcompare.py "
            f"--out results/live_ab_validation --only-stream "
            f"{st.cell_id}:{st.program}:{st.trial}")


# =============================================================================
# 6.  The comparison of one stream
# =============================================================================
@dataclass
class StreamOutcome:
    stream_id: str
    kind: str
    cell: str
    looks: int = 0
    looks_agreeing: int = 0
    disagreeing_looks: int = 0
    tau_12: Optional[int] = None
    tau_11: Optional[int] = None
    label_12_endpoint: str = "NO_DECISION"
    saw_horizon_no_decision: bool = False
    aborted: Optional[str] = None
    seconds: float = 0.0
    enclosure_checkpoints: int = 0
    pair_endpoint_comparisons: int = 0
    defect_classes: Dict[str, int] = field(default_factory=dict)


def compare_cell_stream(st: Stream, cfg: FrozenConfig, pinned: PinnedLoad,
                        ledger: DefectLedger, look_writer, checkpoint_every: int,
                        verbose: bool = False) -> StreamOutcome:
    """Drive both sides over one frozen stream and compare at every look.

    The event stream is the one PROTOCOL 4.3 and cells.json fix: both episodes of a pair
    are dispatched at its enrollment tick; an episode reveals -- final success AND final
    cost together -- at its own offset; and every PENDING episode emits its elapsed lower
    bound ``ell(a) = (c * a) / D`` at every look, including before the first reveal.  The
    identical event is applied to both sides before either is read.
    """
    t0 = time.perf_counter()
    out = StreamOutcome(stream_id=st.stream_id, kind=st.kind, cell=st.cell_id)
    s12 = Side12(cfg)
    s11 = Side11(cfg, pinned, st.n_max)

    n_max = st.n_max
    d_arr = st.d.astype(np.int64)
    f_arr = st.f.astype(np.int64)
    # durations: the first-revealed episode has duration f, the second d (PROTOCOL 4.3)
    dur_c = np.where(st.cand_first, f_arr, d_arr)
    dur_i = np.where(st.cand_first, d_arr, f_arr)
    c_c = st.c_cand
    c_i = st.c_inc
    s_c = st.s_cand.astype(np.int64)
    s_i = st.s_inc.astype(np.int64)

    # per-pair mirrors of each side's own endpoints, compared vectorised at every look
    m12 = np.full((4, n_max), np.nan)
    m11 = np.full((4, n_max), np.nan)

    active: List[int] = []
    revealed_c = np.zeros(n_max + 1, dtype=bool)
    revealed_i = np.zeros(n_max + 1, dtype=bool)

    def apply_tick(t: int, enroll_new: bool) -> Optional[Dict[str, Any]]:
        """Apply every event of tick ``t`` to BOTH sides.  Returns a defect row or None."""
        nonlocal active
        if enroll_new and t <= n_max:
            try:
                s12.enroll(t)
            except Exception as exc:                             # noqa: BLE001
                return _exc_row(st, t, t, "enroll", "12", exc)
            try:
                s11.enroll(t)
            except Exception as exc:                             # noqa: BLE001
                return _exc_row(st, t, t, "enroll", "11", exc)
            m12[:, t - 1] = (-1.0, 1.0, -1.0, 1.0)
            m11[:, t - 1] = (-1.0, 1.0, -1.0, 1.0)
            active.append(t)

        for j in active:
            a = t - j
            i = j - 1
            changed = False
            # --- reveals (an episode's success and final cost arrive together) -------
            for arm, revealed, dur, succ, cost in (
                    ("candidate", revealed_c, dur_c, s_c, c_c),
                    ("incumbent", revealed_i, dur_i, s_i, c_i)):
                if revealed[j] or a < dur[i]:
                    continue
                try:
                    s12.reveal(j, arm, int(succ[i]), float(cost[i]))
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, f"reveal_{arm}", "12", exc)
                try:
                    s11.reveal(j, arm, int(succ[i]), float(cost[i]))
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, f"reveal_{arm}", "11", exc)
                revealed[j] = True
                changed = True
            # --- elapsed lower bound of every pending episode -----------------------
            for arm, revealed, dur, cost in (("candidate", revealed_c, dur_c, c_c),
                                             ("incumbent", revealed_i, dur_i, c_i)):
                if revealed[j]:
                    continue
                ell = (float(cost[i]) * a) / float(dur[i])
                try:
                    s12.elapsed(j, arm, ell)
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, f"elapsed_{arm}", "12", exc)
                try:
                    s11.elapsed(j, arm, ell)
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, f"elapsed_{arm}", "11", exc)
                changed = True
            if changed:
                try:
                    m12[:, i] = s12.refresh(j)
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, "enclosure", "12", exc)
                try:
                    m11[:, i] = s11.refresh(j)
                except Exception as exc:                         # noqa: BLE001
                    return _exc_row(st, t, j, "enclosure", "11", exc)
        active = [j for j in active if (t - j) < d_arr[j - 1]]
        return None

    def pair_facts(j: int, t: int) -> Dict[str, Any]:
        i = j - 1
        a = t - j
        cand_first = bool(st.cand_first[i])
        if not revealed_c[j] and revealed_i[j]:
            pend_arm, pend_c, pend_d, rev_arm, rev_c = "candidate", c_c[i], dur_c[i], "incumbent", c_i[i]
        elif revealed_c[j] and not revealed_i[j]:
            pend_arm, pend_c, pend_d, rev_arm, rev_c = "incumbent", c_i[i], dur_i[i], "candidate", c_c[i]
        else:
            pend_arm, rev_arm = "", ("both" if revealed_c[j] else "neither")
            pend_c = pend_d = rev_c = float("nan")
        ell = ((float(pend_c) * a) / float(pend_d)) if pend_arm else float("nan")
        return {"pair_position": j, "atom": st.atom[i], "revealed_arm": rev_arm,
                "d": int(d_arr[i]), "f": int(f_arr[i]), "age": a, "ell": ell,
                "revealed_cost": float(rev_c) if rev_arm in ("candidate", "incumbent") else "",
                "cand_first": cand_first}

    def _exc_row(stream: Stream, t: int, j: int, stage: str, side: str,
                 exc: BaseException) -> Dict[str, Any]:
        row = _blank_defect(stream, t, min(t, n_max))
        row.update({"defect_class": "exception_during_event_application",
                    "guidance_ref": "PROTOCOL 12.2 exception rule",
                    "quantity": stage, "pair_position": j,
                    "exception_side": side, "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:300]})
        return row

    def _blank_defect(stream: Stream, t: int, n: int) -> Dict[str, Any]:
        return {k: "" for k in DEFECT_FIELDS} | {
            "stream_id": stream.stream_id, "kind": stream.kind, "cell": stream.cell_id,
            "namespace": stream.namespace, "program": stream.program,
            "trial": stream.trial, "tick": t, "n": n,
            "finalization": (t == stream.finalization_tick),
            "replay_command": replay_command(stream)}

    # ---- the look loop ------------------------------------------------------
    ticks: List[Tuple[int, bool]] = [(t, True) for t in range(1, n_max + 1)]
    for t in range(n_max + 1, st.finalization_tick + 1):
        ticks.append((t, False))                                 # the drain: no enrollment

    for t, enroll_new in ticks:
        bad = apply_tick(t, enroll_new)
        if bad is not None:
            ledger.add(bad)
            out.aborted = f"{bad['defect_class']} at tick {t}"
            out.defect_classes[bad["defect_class"]] = \
                out.defect_classes.get(bad["defect_class"], 0) + 1
            break
        is_final = (t == st.finalization_tick)
        if t > n_max and not is_final:
            continue                                             # drain ticks take no look
        n = min(t, n_max)

        exc12 = exc11 = None
        try:
            bh12, bs12, label12 = s12.look()
        except Exception as exc:                                 # noqa: BLE001
            exc12 = exc
        try:
            bh11, bs11, raw11 = s11.look()
        except Exception as exc:                                 # noqa: BLE001
            exc11 = exc

        out.looks += 1
        if exc12 is not None or exc11 is not None:
            # PROTOCOL 12.2: an exception on one side where the other returns a value IS
            # a disagreement.  It is never a skip, a filter or a harness detail.
            side = "12" if exc12 is not None else "11"
            both = exc12 is not None and exc11 is not None
            row = _blank_defect(st, t, n)
            row.update({
                "defect_class": "both_sides_raised" if both else "exception_asymmetry",
                "guidance_ref": "PROTOCOL 12.2 exception rule", "quantity": "look",
                "exception_side": "both" if both else side,
                "exception_type": type(exc12 or exc11).__name__,
                "exception_message": str(exc12 or exc11)[:300]})
            ledger.add(row)
            out.disagreeing_looks += 1
            out.defect_classes[row["defect_class"]] = \
                out.defect_classes.get(row["defect_class"], 0) + 1
            look_writer.writerow(_look_row(st, t, n, is_final, None, None, None, None,
                                           "", raw11 if exc11 is None else "",
                                           "", False, n, 0, float("nan"), "",
                                           "EXCEPTION"))
            continue

        # ---- per-pair enclosure endpoints (all pairs, every look) ------------
        diff = np.abs(m12[:, :n] - m11[:, :n])
        out.enclosure_checkpoints += 1
        out.pair_endpoint_comparisons += 4 * n
        pair_ok = bool(np.all(diff <= TOL))
        max_pair = float(np.nanmax(diff)) if n else 0.0
        first_bad = ""
        if not pair_ok:
            cols = np.where(np.any(diff > TOL, axis=0))[0]
            first_bad = int(cols[0]) + 1
            for col in cols:
                j = int(col) + 1
                for k, quantity in enumerate(("hierarchy_lo", "hierarchy_hi",
                                              "success_lo", "success_hi")):
                    if diff[k, col] > TOL:
                        row = _blank_defect(st, t, n)
                        row.update({
                            "defect_class": "per_pair_enclosure_endpoint",
                            "guidance_ref": "guidance item 5 (enumerate feasible completions)",
                            "quantity": quantity,
                            "value_12": m12[k, col], "value_11": m11[k, col],
                            "abs_diff": float(diff[k, col]),
                            "enc12_lo": m12[0 if k < 2 else 2, col],
                            "enc12_hi": m12[1 if k < 2 else 3, col],
                            "enc11_lo": m11[0 if k < 2 else 2, col],
                            "enc11_hi": m11[1 if k < 2 else 3, col]})
                        row.update({kk: vv for kk, vv in pair_facts(j, t).items()
                                    if kk in DEFECT_FIELDS})
                        ledger.add(row)
                        out.defect_classes["per_pair_enclosure_endpoint"] = \
                            out.defect_classes.get("per_pair_enclosure_endpoint", 0) + 1

        # ---- band endpoints ---------------------------------------------------
        pairs12 = ((bh12.lower, bh11.lo, "L_h"), (bh12.upper, bh11.hi, "U_h"),
                   (bs12.lower, bs11.lo, "L_s"), (bs12.upper, bs11.hi, "U_s"))
        deltas = [v12 - v11 for v12, v11, _ in pairs12]
        band_ok = all(abs(dv) <= TOL for dv in deltas)
        ledger.note_within_tolerance([dv for dv in deltas if abs(dv) <= TOL])
        if not band_ok:
            for (v12, v11, name), dv in zip(pairs12, deltas):
                if abs(dv) > TOL:
                    row = _blank_defect(st, t, n)
                    row.update({"defect_class": "band_endpoint",
                                "guidance_ref": "guidance item 3 (the band) via item 5 "
                                                "(the enclosures it sums)",
                                "quantity": name, "value_12": v12, "value_11": v11,
                                "abs_diff": abs(dv)})
                    ledger.add(row)
                    out.defect_classes["band_endpoint"] = \
                        out.defect_classes.get("band_endpoint", 0) + 1

        # ---- decision label ----------------------------------------------------
        if raw11 in LABEL_BIJECTION:
            mapped11 = LABEL_BIJECTION[raw11]
        else:
            mapped11 = "UNMAPPED"
        if raw11 == "horizon_no_decision":
            out.saw_horizon_no_decision = True
        labels_ok = (mapped11 == label12) and mapped11 != "UNMAPPED"
        if not labels_ok:
            row = _blank_defect(st, t, n)
            row.update({
                "defect_class": ("unmapped_decision_label" if mapped11 == "UNMAPPED"
                                 else "decision_label"),
                "guidance_ref": "guidance item 6 (the frozen finite policy)",
                "quantity": "decision_label", "label_12": label12,
                "label_11_raw": "" if raw11 is None else raw11,
                "value_12": label12, "value_11": "" if raw11 is None else raw11})
            ledger.add(row)
            out.defect_classes[row["defect_class"]] = \
                out.defect_classes.get(row["defect_class"], 0) + 1

        if out.tau_12 is None and label12 != "CONTINUE":
            out.tau_12 = n
            out.label_12_endpoint = label12
        if out.tau_11 is None and mapped11 in ("DEPLOY", "RETAIN_INCUMBENT"):
            out.tau_11 = n

        agree = pair_ok and band_ok and labels_ok
        if agree:
            out.looks_agreeing += 1
        else:
            out.disagreeing_looks += 1
        look_writer.writerow(_look_row(
            st, t, n, is_final, (bh12, bs12), (bh11, bs11), deltas, band_ok,
            label12, "" if raw11 is None else raw11, mapped11, labels_ok,
            n, int(np.sum(np.all(diff <= TOL, axis=0))), max_pair, first_bad,
            "AGREE" if agree else "DISAGREE"))

        if checkpoint_every and (t % checkpoint_every == 0 or is_final):
            msg = s12.verify_band()
            if msg:
                raise ComparisonRefusal(f"REFUSING TO CONTINUE: {msg}")

    # ---- a check on THIS HARNESS, not on either side ------------------------
    # PROTOCOL 4.1 derives every pair's true (Z, D) by enumeration over the six atoms.
    # At the finalization look every fully resolved pair must hold exactly that point on
    # BOTH sides.  If it does not, the event stream this module built is mis-wired -- an
    # arm swapped, a cost mislabelled -- and the comparison above would be meaningless.
    # A failure here is a defect of vcompare.py, and it is reported rather than assumed
    # away.
    if out.aborted is None:
        ages = st.finalization_tick - np.arange(1, n_max + 1, dtype=np.int64)
        resolved = ages >= d_arr
        for side, mirror in (("12", m12), ("11", m11)):
            for k, (truth, name) in enumerate(((st.z_true, "hierarchy"),
                                               (st.d_true, "success"))):
                lo, hi = mirror[2 * k], mirror[2 * k + 1]
                bad = resolved & ((np.abs(lo - truth) > TOL) | (np.abs(hi - truth) > TOL))
                if bad.any():
                    col = int(np.where(bad)[0][0])
                    row = _blank_defect(st, st.finalization_tick, n_max)
                    row.update({
                        "defect_class": "harness_resolved_score_vs_atom_table",
                        "guidance_ref": "PROTOCOL 4.1 (the Z and D columns, by enumeration)",
                        "quantity": f"{name}_point_side_{side}",
                        "pair_position": col + 1, "atom": int(st.atom[col]),
                        "value_12" if side == "12" else "value_11":
                            f"[{mirror[2 * k, col]}, {mirror[2 * k + 1, col]}]",
                        "abs_diff": int(bad.sum())})
                    ledger.add(row)
                    out.defect_classes["harness_resolved_score_vs_atom_table"] = \
                        out.defect_classes.get("harness_resolved_score_vs_atom_table", 0) + 1

    # ---- trial-level comparisons -------------------------------------------
    if out.tau_12 != out.tau_11:
        row = _blank_defect(st, st.finalization_tick, st.n_max)
        row.update({"defect_class": "tau", "guidance_ref": "PROTOCOL 12.2 (tau exactly)",
                    "quantity": "tau_in_enrolled_pairs",
                    "value_12": "" if out.tau_12 is None else out.tau_12,
                    "value_11": "" if out.tau_11 is None else out.tau_11})
        ledger.add(row)
        out.defect_classes["tau"] = out.defect_classes.get("tau", 0) + 1
    if out.saw_horizon_no_decision and out.tau_12 is not None:
        row = _blank_defect(st, st.finalization_tick, st.n_max)
        row.update({"defect_class": "horizon_requires_no_decision",
                    "guidance_ref": "PROTOCOL 12.2 bijection, horizon row",
                    "quantity": "trial_endpoint", "value_12": out.label_12_endpoint,
                    "value_11": "horizon_no_decision"})
        ledger.add(row)
        out.defect_classes["horizon_requires_no_decision"] = \
            out.defect_classes.get("horizon_requires_no_decision", 0) + 1

    out.seconds = time.perf_counter() - t0
    if verbose:
        print(f"    {st.stream_id}: {out.looks} looks, "
              f"{out.looks_agreeing} agreeing, {out.disagreeing_looks} disagreeing, "
              f"{out.seconds:.1f}s")
    return out


def _look_row(st: Stream, t: int, n: int, is_final: bool, b12, b11, deltas, band_ok,
              label12, raw11, mapped11, labels_ok, pairs_compared, pairs_ok,
              max_pair, first_bad, status, checkpoint: str = "look") -> Dict[str, Any]:
    row = {
        "checkpoint": checkpoint,
        "stream_id": st.stream_id, "kind": st.kind, "cell": st.cell_id,
        "cell_index": st.cell_index, "namespace": st.namespace, "program": st.program,
        "trial": st.trial, "tick": t, "n": n, "finalization": is_final,
        "label_12": label12, "label_11_raw": raw11, "label_11_mapped": mapped11,
        "labels_agree": labels_ok, "pairs_compared": pairs_compared,
        "pairs_within_tol": pairs_ok, "max_abs_pair_diff": max_pair,
        "first_bad_pair": first_bad, "status": status,
    }
    if b12 is not None:
        bh12, bs12 = b12
        row.update({"L_h_12": repr(bh12.lower), "U_h_12": repr(bh12.upper),
                    "L_s_12": repr(bs12.lower), "U_s_12": repr(bs12.upper)})
    if b11 is not None:
        bh11, bs11 = b11
        row.update({"L_h_11": repr(bh11.lo), "U_h_11": repr(bh11.hi),
                    "L_s_11": repr(bs11.lo), "U_s_11": repr(bs11.hi)})
    if deltas is not None:
        row.update({"d_L_h": repr(deltas[0]), "d_U_h": repr(deltas[1]),
                    "d_L_s": repr(deltas[2]), "d_U_s": repr(deltas[3]),
                    "endpoints_within_tol": band_ok})
    for k in LOOK_FIELDS:
        row.setdefault(k, "")
    return row


# =============================================================================
# 7.  The fixture streams of section 11
# =============================================================================
def capture_fixture_streams(verbose: bool = True) -> List[Tuple[str, Tuple]]:
    """Capture every event script the section 11 fixtures actually replay.

    ``vfixtures`` does not export its streams, and transcribing them by hand would be
    writing new fixtures rather than replaying the frozen ones.  So the module's own
    ``replay`` helper is wrapped for the duration of one ``run_all()`` and every script
    it is handed is recorded verbatim.  ``vfixtures`` is not modified.
    """
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import vfixtures                                             # noqa: E402
    captured: List[Tuple[str, Tuple]] = []
    original = vfixtures.replay
    counter = {"i": 0}

    def recording_replay(events, *a, **kw):
        counter["i"] += 1
        captured.append((f"fixture_script_{counter['i']:03d}", tuple(events)))
        return original(events, *a, **kw)

    vfixtures.replay = recording_replay                          # type: ignore[assignment]
    try:
        results = vfixtures.run_all()
    finally:
        vfixtures.replay = original                              # type: ignore[assignment]
    failed = [name for name, fails in results if fails]
    if failed and verbose:
        print(f"[fixtures] WARNING: fixtures reporting failures while capturing: {failed}")
    if verbose:
        print(f"[fixtures] captured {len(captured)} replayed event scripts from "
              f"{len(results)} fixtures")
    return captured


#: Event kinds a #11 ``EpisodeView`` cannot represent, with the reason, so that an
#: exclusion is a named structural difference and never a silent skip.
_UNREPRESENTABLE = {
    "succeed": "a #11 EpisodeView carries no outcome field while pending, so 'success "
               "known, cost unknown' has no #11 representation",
    "fail": "same: a bare failure without a final cost has no #11 pending representation",
    "cost_upper": "#11 holds no cost upper bound below the cap",
    "switch": "the traffic switch is a #12/orchestrator concept; the #11 monitor has none",
    "followup": "the follow-up cohort is outside the #11 monitor's state",
}


def convert_fixture_script(name: str, events: Sequence[tuple],
                           cost_cap: float) -> Tuple[Optional[Dict[str, Any]], str]:
    """Turn one captured #12 event script into a stream both sides can be driven over."""
    pairs: List[Dict[str, Any]] = []
    index: Dict[Any, int] = {}
    slot_owner: Dict[Any, Tuple[int, str]] = {}
    ops: List[tuple] = []
    for ev in events:
        kind = ev[0]
        if kind in _UNREPRESENTABLE:
            return None, f"{kind}: {_UNREPRESENTABLE[kind]}"
        if kind == "enroll":
            pid, coin, first, second = ev[1], ev[2], ev[3], ev[4]
            cap = ev[5] if len(ev) > 5 else cost_cap
            if pid in index or coin not in ("AB", "BA") or first == second \
                    or first in slot_owner or second in slot_owner:
                return None, ("the script exercises a rejected enrollment, which is a "
                              "#12 protocol guard with no #11 counterpart")
            pos = len(pairs) + 1
            index[pid] = pos
            cand, inc = (first, second) if coin == "AB" else (second, first)
            slot_owner[cand] = (pos, "candidate")
            slot_owner[inc] = (pos, "incumbent")
            pairs.append({"pair_id": pid, "pos": pos, "cand": cand, "inc": inc,
                          "cap": float(cap)})
            ops.append(("enroll", pos))
        elif kind in ("final", "timeout"):
            slot = ev[1]
            if slot not in slot_owner:
                return None, "a fact for an unowned arrival position"
            pos, arm = slot_owner[slot]
            if kind == "final":
                ops.append(("reveal", pos, arm, int(ev[2]), float(ev[3])))
            else:
                ops.append(("reveal", pos, arm, 0, pairs[pos - 1]["cap"]))
        elif kind == "elapsed":
            slot = ev[1]
            if slot not in slot_owner:
                return None, "a fact for an unowned arrival position"
            pos, arm = slot_owner[slot]
            ops.append(("elapsed", pos, arm, float(ev[2])))
        elif kind == "look":
            ops.append(("look", ev[1]))
        else:
            return None, f"unknown event {kind!r}"
    if not pairs:
        return None, "the script enrolls no pair, so there is no look at n >= 1 to compare"
    caps = {p["cap"] for p in pairs}
    note = ""
    if caps != {cost_cap}:
        note = (f"the script uses per-pair cost caps {sorted(caps)}; #11 holds no cost "
                f"cap at all, which is a named structural difference")
    return {"name": name, "pairs": pairs, "ops": ops, "note": note}, ""


def compare_fixture_stream(conv: Dict[str, Any], cfg: FrozenConfig, pinned: PinnedLoad,
                           ledger: DefectLedger, look_writer) -> StreamOutcome:
    """Replay one converted fixture script through both sides and compare at each look."""
    t0 = time.perf_counter()
    name = conv["name"]
    st = Stream(stream_id=name, kind="fixture", cell_id="fixture", cell_index=-1,
                namespace=cfg.namespace, program=-1, trial=-1,
                n_max=len(conv["pairs"]), finalization_tick=-1,
                atom=np.zeros(0), s_cand=np.zeros(0), s_inc=np.zeros(0),
                c_cand=np.zeros(0), c_inc=np.zeros(0), d=np.zeros(0), f=np.zeros(0),
                cand_first=np.zeros(0, dtype=bool), z_true=np.zeros(0),
                d_true=np.zeros(0))
    out = StreamOutcome(stream_id=name, kind="fixture", cell="fixture")
    n_pairs = len(conv["pairs"])
    s12 = Side12(cfg)
    s11 = Side11(cfg, pinned, max(n_pairs, cfg.n_max))
    m12 = np.full((4, n_pairs), np.nan)
    m11 = np.full((4, n_pairs), np.nan)

    def blank(t: int, n: int) -> Dict[str, Any]:
        return {k: "" for k in DEFECT_FIELDS} | {
            "stream_id": name, "kind": "fixture", "cell": "fixture",
            "namespace": cfg.namespace, "program": -1, "trial": -1, "tick": t, "n": n,
            "finalization": False, "replay_command": replay_command(st)}

    def compare_enclosures(tick: int, checkpoint: str) -> bool:
        """Per-pair endpoint comparison, taken after EVERY event of a fixture script.

        PROTOCOL 12.2 compares per-pair enclosure endpoints "at every look".  Most
        section 11 fixture scripts declare no look at all -- they assert enclosures
        directly -- so comparing only at their declared looks would compare almost
        nothing.  Comparing after every event is a strict superset of their own look
        points and changes no criterion; the band and the decision label are still
        compared only at declared looks, where both sides have a look to take.
        """
        n = len(s12.lo_h)
        if n == 0:
            return True
        d_ = np.abs(m12[:, :n] - m11[:, :n])
        ok = bool(np.all(d_ <= TOL))
        out.enclosure_checkpoints += 1
        out.pair_endpoint_comparisons += 4 * n
        if not ok:
            for col in np.where(np.any(d_ > TOL, axis=0))[0]:
                for k, quantity in enumerate(("hierarchy_lo", "hierarchy_hi",
                                              "success_lo", "success_hi")):
                    if d_[k, col] > TOL:
                        row = blank(tick, n)
                        row.update({"defect_class": "per_pair_enclosure_endpoint",
                                    "guidance_ref": "guidance item 5 (enumerate feasible "
                                                    "completions)",
                                    "quantity": quantity, "pair_position": int(col) + 1,
                                    "value_12": m12[k, col], "value_11": m11[k, col],
                                    "abs_diff": float(d_[k, col])})
                        ledger.add(row)
                        out.defect_classes["per_pair_enclosure_endpoint"] = \
                            out.defect_classes.get("per_pair_enclosure_endpoint", 0) + 1
        look_writer.writerow(_look_row(
            st, tick, n, False, None, None, None, None, "", "", "", "", n,
            int(np.sum(np.all(d_ <= TOL, axis=0))), float(np.nanmax(d_)), "",
            "AGREE" if ok else "DISAGREE", checkpoint=checkpoint))
        return ok

    tick = 0
    for op in conv["ops"]:
        tick += 1
        side = "12"
        try:
            if op[0] == "enroll":
                pos = op[1]
                s12.enroll(pos, cost_cap=conv["pairs"][pos - 1]["cap"])
                side = "11"
                s11.enroll(pos)
                m12[:, pos - 1] = (-1.0, 1.0, -1.0, 1.0)
                m11[:, pos - 1] = (-1.0, 1.0, -1.0, 1.0)
                compare_enclosures(tick, "event:enroll")
                continue
            if op[0] == "reveal":
                _, pos, arm, succ, cost = op
                s12.reveal(pos, arm, succ, cost)
                side = "11"
                s11.reveal(pos, arm, succ, cost)
                m12[:, pos - 1] = s12.refresh(pos)
                m11[:, pos - 1] = s11.refresh(pos)
                compare_enclosures(tick, "event:reveal")
                continue
            if op[0] == "elapsed":
                _, pos, arm, ell = op
                s12.elapsed(pos, arm, ell)
                side = "11"
                s11.elapsed(pos, arm, ell)
                m12[:, pos - 1] = s12.refresh(pos)
                m11[:, pos - 1] = s11.refresh(pos)
                compare_enclosures(tick, "event:elapsed")
                continue
        except Exception as exc:                                 # noqa: BLE001
            row = blank(tick, len(s12.lo_h))
            row.update({"defect_class": "exception_during_event_application",
                        "guidance_ref": "PROTOCOL 12.2 exception rule",
                        "quantity": op[0], "exception_side": side,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:300]})
            ledger.add(row)
            out.aborted = f"{type(exc).__name__} at op {tick} (side {side})"
            out.defect_classes["exception_during_event_application"] = \
                out.defect_classes.get("exception_during_event_application", 0) + 1
            break

        # a look
        n = len(s12.lo_h)
        if n == 0:
            continue                    # PROTOCOL 12.2: no look at n = 0 on either side
        exc12 = exc11 = None
        try:
            bh12, bs12, label12 = s12.look()
        except Exception as exc:                                 # noqa: BLE001
            exc12 = exc
        try:
            bh11, bs11, raw11 = s11.look()
        except Exception as exc:                                 # noqa: BLE001
            exc11 = exc
        out.looks += 1
        if exc12 is not None or exc11 is not None:
            both = exc12 is not None and exc11 is not None
            row = blank(tick, n)
            row.update({"defect_class": "both_sides_raised" if both
                        else "exception_asymmetry",
                        "guidance_ref": "PROTOCOL 12.2 exception rule",
                        "quantity": "look",
                        "exception_side": "both" if both else ("12" if exc12 else "11"),
                        "exception_type": type(exc12 or exc11).__name__,
                        "exception_message": str(exc12 or exc11)[:300]})
            ledger.add(row)
            out.disagreeing_looks += 1
            out.defect_classes[row["defect_class"]] = \
                out.defect_classes.get(row["defect_class"], 0) + 1
            continue

        diff = np.abs(m12[:, :n] - m11[:, :n])
        pair_ok = bool(np.all(diff <= TOL))
        if not pair_ok:
            for col in np.where(np.any(diff > TOL, axis=0))[0]:
                for k, quantity in enumerate(("hierarchy_lo", "hierarchy_hi",
                                              "success_lo", "success_hi")):
                    if diff[k, col] > TOL:
                        row = blank(tick, n)
                        row.update({"defect_class": "per_pair_enclosure_endpoint",
                                    "guidance_ref": "guidance item 5 (enumerate feasible "
                                                    "completions)",
                                    "quantity": quantity, "pair_position": int(col) + 1,
                                    "value_12": m12[k, col], "value_11": m11[k, col],
                                    "abs_diff": float(diff[k, col])})
                        ledger.add(row)
                        out.defect_classes["per_pair_enclosure_endpoint"] = \
                            out.defect_classes.get("per_pair_enclosure_endpoint", 0) + 1
        band_pairs = ((bh12.lower, bh11.lo, "L_h"), (bh12.upper, bh11.hi, "U_h"),
                      (bs12.lower, bs11.lo, "L_s"), (bs12.upper, bs11.hi, "U_s"))
        deltas = [v12 - v11 for v12, v11, _ in band_pairs]
        band_ok = all(abs(dv) <= TOL for dv in deltas)
        ledger.note_within_tolerance([dv for dv in deltas if abs(dv) <= TOL])
        if not band_ok:
            for (v12, v11, nm), dv in zip(band_pairs, deltas):
                if abs(dv) > TOL:
                    row = blank(tick, n)
                    row.update({"defect_class": "band_endpoint",
                                "guidance_ref": "guidance item 3 via item 5",
                                "quantity": nm, "value_12": v12, "value_11": v11,
                                "abs_diff": abs(dv)})
                    ledger.add(row)
                    out.defect_classes["band_endpoint"] = \
                        out.defect_classes.get("band_endpoint", 0) + 1
        mapped11 = LABEL_BIJECTION.get(raw11, "UNMAPPED")
        if raw11 == "horizon_no_decision":
            out.saw_horizon_no_decision = True
        labels_ok = (mapped11 == label12) and mapped11 != "UNMAPPED"
        if not labels_ok:
            row = blank(tick, n)
            row.update({"defect_class": ("unmapped_decision_label"
                                         if mapped11 == "UNMAPPED" else "decision_label"),
                        "guidance_ref": "guidance item 6", "quantity": "decision_label",
                        "label_12": label12, "label_11_raw": raw11 or "",
                        "value_12": label12, "value_11": raw11 or ""})
            ledger.add(row)
            out.defect_classes[row["defect_class"]] = \
                out.defect_classes.get(row["defect_class"], 0) + 1
        if out.tau_12 is None and label12 != "CONTINUE":
            out.tau_12 = n
            out.label_12_endpoint = label12
        if out.tau_11 is None and mapped11 in ("DEPLOY", "RETAIN_INCUMBENT"):
            out.tau_11 = n
        agree = pair_ok and band_ok and labels_ok
        out.looks_agreeing += int(agree)
        out.disagreeing_looks += int(not agree)
        look_writer.writerow(_look_row(
            st, tick, n, False, (bh12, bs12), (bh11, bs11), deltas, band_ok,
            label12, raw11 or "", mapped11, labels_ok, n,
            int(np.sum(np.all(diff <= TOL, axis=0))),
            float(np.nanmax(diff)) if n else 0.0, "",
            "AGREE" if agree else "DISAGREE"))

    if out.tau_12 != out.tau_11:
        row = blank(tick, len(s12.lo_h))
        row.update({"defect_class": "tau", "guidance_ref": "PROTOCOL 12.2 (tau exactly)",
                    "quantity": "tau_in_enrolled_pairs",
                    "value_12": "" if out.tau_12 is None else out.tau_12,
                    "value_11": "" if out.tau_11 is None else out.tau_11})
        ledger.add(row)
        out.defect_classes["tau"] = out.defect_classes.get("tau", 0) + 1
    out.seconds = time.perf_counter() - t0
    return out


# =============================================================================
# 8.  Minimal reproducers
# =============================================================================
def minimal_reproducer(row: Dict[str, Any], pinned: PinnedLoad, cfg: FrozenConfig
                       ) -> Dict[str, Any]:
    """Reduce one enclosure defect to the single pair state that produces it.

    The reproducer is re-executed here, so the snippet in the summary is a fact and not
    a description: both sides are called on the one state and their answers recorded.
    """
    if row.get("defect_class") != "per_pair_enclosure_endpoint":
        return {}
    try:
        age = int(row["age"])
        d_off = int(row["d"])
        f_off = int(row["f"])
        ell = float(row["ell"])
        rev_arm = str(row["revealed_arm"])
        rev_cost = float(row["revealed_cost"])
        atom_i = int(row["atom"])
    except (KeyError, TypeError, ValueError):
        return {}
    if rev_arm not in ("candidate", "incumbent"):
        return {}
    atom = cfg.atoms[atom_i]
    rev_success = int(atom["s_candidate"] if rev_arm == "candidate" else atom["s_incumbent"])
    pend_arm = "incumbent" if rev_arm == "candidate" else "candidate"

    import vband                                                 # noqa: E402
    enc = pinned.lab_enclosure
    tiers = enc._frozen_tiers()
    rv = enc.EpisodeView.reveal(rev_arm, rev_success, rev_cost, 0)
    pv = enc.EpisodeView.pending(pend_arm, ell=ell)
    cand_view, inc_view = (rv, pv) if rev_arm == "candidate" else (pv, rv)
    h11 = enc.hierarchy_enclosure(cand_view, inc_view, tiers)
    s11 = enc.success_enclosure(cand_view, inc_view)

    rev_ep = vband.Episode.pending("rev", cfg.cost_cap).finalized(rev_success, rev_cost)
    pend_ep = vband.Episode.pending("pend", cfg.cost_cap).with_elapsed_cost(ell)
    ep_c, ep_i = (rev_ep, pend_ep) if rev_arm == "candidate" else (pend_ep, rev_ep)
    h12 = vband.hierarchy_bounds(ep_c, ep_i)
    s12 = vband.success_bounds(ep_c, ep_i)

    return {
        "state": {
            "atom": atom["atom"], "revealed_arm": rev_arm,
            "revealed_success": rev_success, "revealed_cost": rev_cost,
            "pending_arm": pend_arm, "pending_elapsed_ell": ell,
            "pair_age": age, "d": d_off, "f": f_off, "cost_cap": cfg.cost_cap,
        },
        "snippet": (
            "# both sides, on the one pair state, with nothing else in play\n"
            f"rev = EpisodeView.reveal({rev_arm!r}, {rev_success}, {rev_cost!r}, 0)\n"
            f"pen = EpisodeView.pending({pend_arm!r}, ell={ell!r})\n"
            "h11 = lab_enclosure.hierarchy_enclosure(candidate, incumbent, tiers)\n"
            f"# -> [{h11.lo}, {h11.hi}]\n"
            f"rev12 = vband.Episode.pending('rev', {cfg.cost_cap!r})"
            f".finalized({rev_success}, {rev_cost!r})\n"
            f"pen12 = vband.Episode.pending('pend', {cfg.cost_cap!r})"
            f".with_elapsed_cost({ell!r})\n"
            "h12 = vband.hierarchy_bounds(candidate, incumbent)\n"
            f"# -> [{h12[0]}, {h12[1]}]"),
        "hierarchy_11": [h11.lo, h11.hi],
        "hierarchy_12": list(h12),
        "success_11": [s11.lo, s11.hi],
        "success_12": list(s12),
        "reproduced": (h11.lo, h11.hi) != tuple(h12) or (s11.lo, s11.hi) != tuple(s12),
    }


def guidance_readings(defect_class: str) -> Dict[str, str]:
    """The clause each side appears to implement.  Neither is declared correct here."""
    if defect_class == "per_pair_enclosure_endpoint":
        return {
            "shared_clause": GUIDANCE_ITEM_5,
            "reading_12": (
                "vband.cost_order_possibilities enumerates the feasible signed cost-tier "
                "preferences separately: the pending arm's 'cheaper' branch dies when "
                "c - ell is no longer greater than rtol*max(c, ell), and the TIE branch "
                "dies later, at ell - c > rtol*max(c, ell). Between those two thresholds "
                "the feasible set is {0, +1} (for a revealed candidate), so the hierarchy "
                "enclosure is [0, +1]. #12 reads 'enumerate feasible completions' as an "
                "exhaustive enumeration whose result may be any subinterval."),
            "reading_11": (
                "lab_enclosure.hierarchy_enclosure implements a closed case list (its "
                "docstring cites protocol_FINAL 7.5 item 5): with one arm revealed and "
                "successful, the feasible set is the SINGLETON {sgn} when the cost "
                "certificate (1 - tol)*ell > L_r + 1e-9 holds, and the FULL set "
                "{-1, 0, +1} otherwise. There is no intermediate case, so the enclosure "
                "is either a point or [-1, +1]."),
            "note": (
                "Both readings agree on the point-collapse threshold and differ on "
                "whether the intermediate state exists. PROTOCOL 6.4 prices that "
                "intermediate state: it is the gap between the 'point' and 'narrowed' "
                "columns, which is nonzero in every cell at every horizon. Which side is "
                "wrong is NOT decided here (PROTOCOL 12.3 item 3)."),
        }
    if defect_class == "band_endpoint":
        return {
            "shared_clause": GUIDANCE_ITEM_3,
            "reading_12": "The band is the same formula on both sides; a band endpoint "
                          "difference is the per-pair enclosure difference summed over "
                          "the prefix and divided by n, not an independent defect.",
            "reading_11": "Same.",
            "note": "Check the per_pair_enclosure_endpoint class first: if it is "
                    "nonempty, this class is its consequence.",
        }
    if defect_class in ("decision_label", "tau", "horizon_requires_no_decision"):
        return {
            "shared_clause": "guidance item 6: deploy when L_h > 0 and L_success > -delta "
                             "at the same current prefix/look; harm as prespecified.",
            "reading_12": "vband.decide evaluates DEPLOY before RETAIN_INCUMBENT.",
            "reading_11": "lab_monitor.decide evaluates harm_keep_incumbent first and "
                          "carries a horizon_no_decision branch that #12 has no concept "
                          "of.",
            "note": "A label difference that follows a band difference is a consequence "
                    "of it, not an independent finding.",
        }
    return {}


# =============================================================================
# 9.  Main
# =============================================================================
def git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):                # pragma: no cover
        return "unknown"


def peak_rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="PROTOCOL 12: compare the #12 band arithmetic against the pinned "
                    "#11 monitor on the frozen namespace-2 streams.")
    ap.add_argument("--out", default=str(RESULTS_ROOT),
                    help="output directory; must lie inside results/live_ab_validation/")
    ap.add_argument("--streams-per-cell", type=int, default=None,
                    help="how many of the frozen 25 per cell to replay (default: all 25). "
                         "Fewer is a PARTIAL run and is labelled as one everywhere.")
    ap.add_argument("--cells", default="",
                    help="comma-separated cell ids to restrict to (default: all eight)")
    ap.add_argument("--only-stream", default="",
                    help="replay exactly one cell stream, as CELL:PROGRAM:TRIAL")
    ap.add_argument("--only-fixture", default="",
                    help="replay exactly one captured fixture script by name")
    ap.add_argument("--no-fixtures", action="store_true",
                    help="skip the section 11 fixture streams")
    ap.add_argument("--checkpoint-every", type=int, default=500,
                    help="ticks between self-checks of the incremental #12 mirror")
    ap.add_argument("--max-defect-rows", type=int, default=0,
                    help="0 (default) writes every disagreement; a positive value "
                         "truncates the CSV and records the truncation loudly")
    args = ap.parse_args(argv)

    out_dir = guarded_out_dir(args.out)
    cfg = load_frozen_config()
    print(f"[config] cells.json alpha_gate={cfg.alpha_gate} rho={cfg.rho} "
          f"delta={cfg.delta} n_min={cfg.n_min} N_max={cfg.n_max} "
          f"finalization_tick={cfg.finalization_tick} namespace={cfg.namespace}")
    pinned = verify_and_load_pinned()
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    gen = FrozenGenerator(cfg)

    per_cell = cfg.streams_per_cell if args.streams_per_cell is None \
        else int(args.streams_per_cell)
    coords = comparison_stream_coords(cfg, per_cell)
    if args.cells:
        wanted = {c.strip() for c in args.cells.split(",") if c.strip()}
        coords = [c for c in coords if c[0] in wanted]
    if args.only_stream:
        cell_id, prog, trial = args.only_stream.split(":")
        coords = [(cell_id, int(prog), int(trial))]
    partial = (len(coords) != cfg.streams_total) or bool(args.only_stream)

    t_start = time.perf_counter()
    ledger = DefectLedger()
    outcomes: List[StreamOutcome] = []

    look_path = guarded_path(out_dir, "comparison_vs_live_ab.csv")
    defect_path = guarded_path(out_dir, "comparison_defects.csv")
    summary_path = guarded_path(out_dir, "comparison_summary.json")

    with open(look_path, "w", newline="") as fh:
        look_writer = csv.DictWriter(fh, fieldnames=LOOK_FIELDS, extrasaction="ignore")
        look_writer.writeheader()

        streams: List[Stream] = []
        if not args.only_fixture:
            print(f"[streams] {len(coords)} cell streams"
                  f"{' (PARTIAL RUN)' if partial else ' (the frozen full set)'}")
            for cell_id, prog, trial in coords:
                streams.append(gen.build(cell_id, prog, trial))
            xcheck = crosscheck_vgen(gen, streams[:2])
            print(f"[vgen] {xcheck['status']}")
            for i, st in enumerate(streams, 1):
                print(f"  [{i}/{len(streams)}] {st.stream_id} ...", flush=True)
                outcomes.append(compare_cell_stream(
                    st, cfg, pinned, ledger, look_writer, args.checkpoint_every,
                    verbose=True))
        else:
            xcheck = {"status": "not probed (fixture-only run)", "vgen_present":
                      (HERE / "vgen.py").is_file(), "checked_streams": 0,
                      "mismatches": []}

        fixture_report: Dict[str, Any] = {"captured": 0, "comparable": 0,
                                          "not_comparable": []}
        if not args.no_fixtures:
            captured = capture_fixture_streams()
            fixture_report["captured"] = len(captured)
            for name, events in captured:
                if args.only_fixture and name != args.only_fixture:
                    continue
                conv, reason = convert_fixture_script(name, events, cfg.cost_cap)
                if conv is None:
                    fixture_report["not_comparable"].append(
                        {"script": name, "reason": reason})
                    continue
                fixture_report["comparable"] += 1
                if conv["note"]:
                    fixture_report.setdefault("notes", []).append(
                        {"script": name, "note": conv["note"]})
                outcomes.append(compare_fixture_stream(
                    conv, cfg, pinned, ledger, look_writer))
            print(f"[fixtures] {fixture_report['comparable']} comparable, "
                  f"{len(fixture_report['not_comparable'])} not comparable")

    # ---- defects CSV --------------------------------------------------------
    truncated = 0
    with open(defect_path, "w", newline="") as fh:
        dw = csv.DictWriter(fh, fieldnames=DEFECT_FIELDS, extrasaction="ignore")
        dw.writeheader()
        rows = ledger.rows
        if args.max_defect_rows and len(rows) > args.max_defect_rows:
            truncated = len(rows) - args.max_defect_rows
            rows = rows[:args.max_defect_rows]
        for r in rows:
            dw.writerow(r)

    seconds = time.perf_counter() - t_start
    cell_outcomes = [o for o in outcomes if o.kind == "cell"]
    total_looks = sum(o.looks for o in outcomes)
    agreeing = sum(o.looks_agreeing for o in outcomes)
    n_streams = len(outcomes)

    agreement_sentence = (
        f"The two implementations agree on {n_streams} streams "
        f"({agreeing} of {total_looks} compared looks) to {TOL:g}."
        if agreeing == total_looks else
        f"The two implementations DISAGREE: {total_looks - agreeing} of {total_looks} "
        f"compared looks, over {n_streams} streams, failed at least one frozen criterion.")

    summary: Dict[str, Any] = {
        "protocol": "experiments/live_ab_validation/PROTOCOL.md section 12",
        "version": "v1-cpu-validation",
        "run": {
            "partial": partial,
            "streams_run": n_streams,
            "cell_streams_run": len(cell_outcomes),
            "frozen_full_set": cfg.streams_total,
            "streams_per_cell_run": per_cell,
            "stream_coordinate_rule": (
                "the first N of each cell in lexicographic order of "
                "(program_index, trial_index), trial fastest; the protocol fixes the "
                "count and the namespace but not the enumeration, so the rule is "
                "declared here"),
            "namespace": cfg.namespace,
            "N_max": cfg.n_max,
            "finalization_tick": cfg.finalization_tick,
            "looks_compared": total_looks,
            "looks_agreeing": agreeing,
            "looks_disagreeing": total_looks - agreeing,
            "enclosure_checkpoints": sum(o.enclosure_checkpoints for o in outcomes),
            "pair_endpoint_comparisons": sum(
                o.pair_endpoint_comparisons for o in outcomes),
            "seconds": round(seconds, 2),
            "seconds_per_cell_stream": (
                round(sum(o.seconds for o in cell_outcomes) / len(cell_outcomes), 2)
                if cell_outcomes else None),
            "peak_rss_bytes": peak_rss_bytes(),
            "defect_rows_written": len(ledger.rows) - truncated,
            "defect_rows_truncated": truncated,
        },
        "ordering": {
            "rule": ("PROTOCOL 12.1 item 3: the pinned copy is loaded only by this "
                     "module, and only AFTER vrun.py has finished."),
            "vrun_py_exists": (HERE / "vrun.py").is_file(),
            "grid_outputs_present": guarded_path(out_dir, "trials.csv.gz").is_file(),
            "note": ("If the two flags above are false this comparison ran BEFORE the "
                     "reported grid, which is out of the protocol's order. The result is "
                     "still a fact about the two implementations, but it must not be "
                     "used to alter any #12 module: PROTOCOL 12.3 item 1 forbids editing "
                     "either side to make them agree, whenever the comparison ran."),
        },
        "provenance": {
            "repo_commit": git_commit(),
            "pinned_source_commit": pinned.manifest.get("source_commit"),
            "pinned_digests": pinned.digests,
            "pinned_manifest_verified": True,
            "lab_common_present": pinned.lab_common_present,
            "cells_json_sha256": sha256_file(CELLS_PATH),
            "protocol_sha256": sha256_file(PROTOCOL_PATH),
            "vband_sha256": sha256_file(HERE / "vband.py"),
            "winstats_sha256": sha256_file(SRC_DIR / "winstats.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "n_max_configured_on_the_pinned_monitor": cfg.n_max,
            "n_max_note": (
                "the pinned #11 MonitorConfig is configured at n_max = N_max = "
                f"{cfg.n_max}, the #12 study horizon. The #11 field is documented as the "
                "live roster size and carries no upper guard; this is declared rather "
                "than silent."),
        },
        "generator": {
            "owned_by_protocol_13_0": "vgen.py",
            "vgen_crosscheck": xcheck,
            "note": ("vgen.py does not exist at the freeze commit, so vcompare "
                     "implements PROTOCOL 4.1-4.3 and 5 for the comparison streams. If "
                     "vgen.py appears, the cross-check above compares the two array by "
                     "array and reports a difference as a generator defect."),
        },
        "criteria": {
            "band_endpoints": f"absolute difference <= {TOL:g}",
            "per_pair_enclosure_endpoints": f"absolute difference <= {TOL:g}",
            "decision_label": "exactly equal under the frozen bijection",
            "tau": "exactly equal",
            "bijection": {str(k): v for k, v in LABEL_BIJECTION.items()},
        },
        "out_of_scope_named_not_silent": {
            "certified_collapsed_flag": (
                "NOT compared (PROTOCOL 1.3 item 8, 12.2). #12 marks certified only on a "
                "valid final-score certificate; #11 requires its collapsed flag to be "
                "true exactly when both scores are points. The two definitions are "
                "incompatible and PROTOCOL 6.4 says the difference is common rather than "
                "exotic. NEITHER READING IS DECLARED CORRECT HERE; it is escalated with "
                "the rest under 12.3."),
            "look_at_n_equals_0": (
                "No look is taken at n = 0 on either side: #12 displays the full range "
                "and #11 raises. Excluded by construction, not adjudicated."),
        },
        "defects": {},
        "noted_numerical_differences": {
            "rule": ("PROTOCOL 12.3 item 5: a difference within tolerance but systematic "
                     "is reported with its magnitude, not silently accepted."),
            "band_endpoint_differences_within_tolerance": ledger.noted_n,
            "max_magnitude": ledger.noted_max,
            "signs": ledger.noted_signs,
        },
        "fixtures": fixture_report,
        "disposition": {
            "agreement_wording": agreement_sentence,
            "agreement_is_not_correctness": (
                "Agreement is reported as agreement and never as 'the monitor is "
                "correct': two implementations of the same misreading of the guidance "
                "agree perfectly and this comparison cannot detect that (PROTOCOL 12.3 "
                "item 6). The section 11 fixtures, derived from the guidance text rather "
                "than from either implementation, are the only check that addresses it, "
                "and they are weaker than a proof."),
            "cost_tier_agreement_is_worth_less": (
                "PROTOCOL 12.3 item 7: the pre-registration audit disclosed #11's cost "
                "certificate to the #12 author before this comparison was specified, so "
                "AGREEMENT on the cost-tier narrowing is agreement between two readings "
                "known to coincide, not two that arrived independently. Disagreement "
                "there would still be informative; agreement is not."),
            "disagreement_is_a_defect": (
                "A disagreement is a DEFECT and is reported as one. It is NEVER "
                "reconciled by editing either side. Which side is wrong is NOT decided "
                "here; it is escalated to the coordinator and the root with the "
                "reproducer (PROTOCOL 12.3 items 1-3)."),
            "until_adjudicated": (
                "Until a disagreement is adjudicated, #11's results do not count as "
                "validated, which is the whole purpose of this study."),
        },
        "streams": [
            {"stream_id": o.stream_id, "kind": o.kind, "cell": o.cell,
             "looks": o.looks, "agreeing": o.looks_agreeing,
             "disagreeing": o.disagreeing_looks, "tau_12": o.tau_12, "tau_11": o.tau_11,
             "enclosure_checkpoints": o.enclosure_checkpoints,
             "aborted": o.aborted, "seconds": round(o.seconds, 3),
             "defect_classes": o.defect_classes}
            for o in outcomes
        ],
    }
    for cls, count in sorted(ledger.counts.items(), key=lambda kv: -kv[1]):
        first = ledger.first[cls]
        summary["defects"][cls] = {
            "count": count,
            "streams_affected": len(ledger.streams_with.get(cls, ())),
            "first_occurrence": {k: (v if not isinstance(v, (np.integer, np.floating))
                                     else v.item())
                                 for k, v in first.items() if v != ""},
            "value_pair_histogram": dict(sorted(
                ledger.shapes.get(cls, {}).items(), key=lambda kv: -kv[1])),
            "guidance_clause_each_side_appears_to_implement": guidance_readings(cls),
            "minimal_reproducer": minimal_reproducer(first, pinned, cfg),
            "disposition": "DEFECT -- escalated, never reconciled by editing either side",
        }
    if not ledger.counts:
        summary["defects"] = {}

    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    # ---- stdout report ------------------------------------------------------
    print()
    print("=" * 78)
    print(f"PROTOCOL 12 comparison {'(PARTIAL RUN)' if partial else '(full frozen set)'}")
    print("=" * 78)
    print(agreement_sentence)
    if ledger.counts:
        print("\nDEFECT CLASSES (a disagreement is a defect; neither side is edited):")
        for cls, count in sorted(ledger.counts.items(), key=lambda kv: -kv[1]):
            print(f"  {cls:38s} {count:9d} rows, "
                  f"{len(ledger.streams_with[cls])} streams")
        print("\nWhich side is wrong is NOT decided here. Until adjudicated, #11's "
              "results do not count as validated.")
    else:
        print("\nNo disagreement at any compared look. This is AGREEMENT, not "
              "correctness: two implementations of the same misreading agree perfectly.")
    print(f"\nwrote {look_path}")
    print(f"wrote {defect_path}" + (f"  (TRUNCATED by {truncated} rows)" if truncated else ""))
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
