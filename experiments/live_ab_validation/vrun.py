"""vrun.py -- the grid runner of PROTOCOL sections 7 to 9.

Issue #12 (independent CPU validation).  One command, writing only inside its
own output directory:

    .venv/bin/python experiments/live_ab_validation/vrun.py --out results/live_ab_validation

It runs, in this order and no other:

  1. the deterministic fixture gate (section 11), by invoking the frozen
     fixture command in a subprocess and depositing ``fixtures_report.json``;
  2. the one 20-program smoke run of section 8.1, which measures **runtime,
     peak memory, output bytes and counts and nothing else**, from the
     discarded namespace 1, and whose effect columns are never formed into a
     record, never written and never read;
  3. the budget ladder of section 8.2, written to ``budget.json`` BEFORE the
     reported grid starts, with the measured scaling exponent ``beta``;
  4. the reported grid of section 7 from namespace 0, three constructions on
     every simulated path -- the partial-data ADAPTER under test, the matched
     completed-prefix CPREFIX, and the completed-only NAIVE rule, which is
     **INVALID under informative delay** and is labelled so in every row it
     appears in;
  5. the determinism assertion: one cell block is re-run and its records are
     compared byte for byte;
  6. every reported quantity of section 9 with its exact estimator and its
     Wilson score interval, and the precommitted positive control of 9.4.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read: PROTOCOL.md, cells.json, vband.py, vgen.py, vfixtures.py and src/winstats.py.
Deliberately NOT read, opened or imported: the #11 monitor and enclosure
modules, and the pinned read-only copy of them that sits beside this file.  The
comparison module is the only module permitted to load those, and only after
this one has finished.

WHAT THIS MODULE MAY NOT DO
---------------------------
It may not change a cell, a weight, a delay rule, a seed, an estimator, a flag
rule, a threshold or the positive control; all of those are frozen in
PROTOCOL.md and cells.json and are read from there.  It retains every
unfavourable and inconclusive row (section 13.4).  An unflagged result is
reported as "no exceedance was detected at this resolution", never as "the
bound holds".

CPU only.  No model call, no API call, no network, no new dependency.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math

import platform
import resource
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import vband
import vgen

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CELLS_JSON = HERE / "cells.json"
PROTOCOL_MD = HERE / "PROTOCOL.md"
CANONICAL_OUT = REPO_ROOT / "results" / "live_ab_validation"
GUIDANCE_DOC = REPO_ROOT / "reviews" / "arxiv_live_design_guidance.md"
PINNED_PRIMITIVE = REPO_ROOT / "src" / "winstats.py"

# ---------------------------------------------------------------------------
# PROTOCOL 3: the three compared constructions
# ---------------------------------------------------------------------------
ADAPTER, CPREFIX, NAIVE = "ADAPTER", "CPREFIX", "NAIVE"
CONSTRUCTIONS = (ADAPTER, CPREFIX, NAIVE)
CONSTRUCTION_STATUS = {
    ADAPTER: "the object under test",
    CPREFIX: "valid for its own running target",
    NAIVE: "INVALID under informative delay",
}
CONSTRUCTION_INDEX = {
    ADAPTER: "n = enrolled pairs",
    CPREFIX: "k = longest fully resolved prefix",
    NAIVE: "m = count completed",
}

NO_DECISION, DEPLOY, RETAIN_INCUMBENT, CONFLICT = 0, 1, 2, 3
DECISION_LABEL = {NO_DECISION: "NO_DECISION", DEPLOY: "DEPLOY",
                  RETAIN_INCUMBENT: "RETAIN_INCUMBENT", CONFLICT: "CONFLICT"}

# ---------------------------------------------------------------------------
# PROTOCOL 9: the Wilson score interval, at the frozen z
# ---------------------------------------------------------------------------
WILSON_Z = 1.959963984540054


def wilson(x: int, n: int) -> Tuple[float, float, float]:
    """``(rate, lower, upper)`` of the Wilson score 95% interval.

    These intervals quantify Monte Carlo error of this simulation only.  They
    are not confidence intervals for the statistical guarantee, and a Wilson
    interval lying below a nominal level is not a proof that the level holds.
    """
    if n <= 0:
        return (float("nan"), 0.0, 1.0)
    z = WILSON_Z
    z2 = z * z
    centre = (x + z2 / 2.0) / (n + z2)
    half = z / (n + z2) * math.sqrt(x * (n - x) / n + z2 / 4.0)
    return (x / n, max(0.0, centre - half), min(1.0, centre + half))


def is_flagged(lower: float, nominal: Optional[float]) -> bool:
    """PROTOCOL 9.3: FLAG iff the LOWER Wilson limit exceeds the nominal bound."""
    return nominal is not None and lower > nominal


# ---------------------------------------------------------------------------
# The write guard
# ---------------------------------------------------------------------------
class WriteGuard:
    """Refuses, and aborts on, any write outside the run's own directory.

    PROTOCOL 13.1: the run "writes only inside ``results/live_ab_validation/``;
    a guard refuses any path outside that directory and the run aborts rather
    than writing elsewhere".  Two layers: the directory itself must be a
    ``results/live_ab_validation`` directory, and the REPORTED grid must be the
    repository's own one -- an ad-hoc run is forbidden from writing there at
    all, so a shakedown can never be mistaken for the study.
    """

    def __init__(self, out_dir: Path, reported: bool) -> None:
        resolved = Path(out_dir).expanduser().resolve()
        if resolved.name != "live_ab_validation" or resolved.parent.name != "results":
            raise SystemExit(
                f"write guard: refusing to run with --out {resolved}; the output "
                f"directory must be a 'results/live_ab_validation' directory")
        if reported and resolved != CANONICAL_OUT.resolve():
            raise SystemExit(
                f"write guard: a reported grid run must write to {CANONICAL_OUT}, "
                f"not {resolved}")
        if not reported and resolved == CANONICAL_OUT.resolve():
            raise SystemExit(
                "write guard: this run carries grid overrides, so it is NOT the "
                "reported grid and is refused write access to the reported "
                "results directory; give it another --out")
        self.root = resolved
        self.reported = reported
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        target = self.root.joinpath(*parts)
        resolved = target.resolve() if target.exists() else \
            (target.parent.resolve() / target.name)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise SystemExit(f"write guard: refusing to write outside "
                             f"{self.root}: {target}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def write_text(self, name: str, text: str) -> Path:
        p = self.path(name)
        p.write_text(text)
        return p

    def write_json(self, name: str, payload) -> Path:
        return self.write_text(name, json.dumps(payload, indent=2,
                                                sort_keys=True) + "\n")

    def total_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())


class _ByteCounter(io.RawIOBase):
    """A sink that counts what is written to it and keeps none of it."""

    def __init__(self) -> None:
        self.count = 0

    def writable(self) -> bool:
        return True

    def write(self, payload) -> int:                     # type: ignore[override]
        self.count += len(payload)
        return len(payload)

    def tell(self) -> int:
        return self.count


class RowSink:
    """Per-trial records, appended incrementally, never held in memory in full.

    A window of the uncompressed stream can be retained so that the determinism
    assertion of PROTOCOL 13.1 can re-run one cell block and compare byte for
    byte.  ``discard`` writes nowhere at all and only counts, which is how the
    smoke run measures output bytes without ever forming a per-trial effect
    record on disk (PROTOCOL 8.1).  ``mtime=0`` keeps the gzip container itself
    byte-identical between runs.
    """

    def __init__(self, path: Optional[Path], header: str, discard: bool = False):
        self.discard = discard
        self.raw_bytes = 0
        self._retain: Optional[List[bytes]] = None
        self._fh = _ByteCounter() if discard else open(path, "wb")
        self._gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._fh,
                                 mtime=0)
        if header:
            self.write(header)

    def write(self, text: str) -> None:
        payload = text.encode()
        self.raw_bytes += len(payload)
        if self._retain is not None:
            self._retain.append(payload)
        self._gz.write(payload)

    def start_retaining(self) -> None:
        self._retain = []

    def stop_retaining(self) -> bytes:
        out = b"".join(self._retain or [])
        self._retain = None
        return out

    def close(self) -> int:
        self._gz.close()
        size = self._fh.tell()
        self._fh.close()
        return int(size)


def peak_rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw) if sys.platform == "darwin" else int(raw) * 1024


# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------
@dataclass
class RunConfig:
    n_max: int
    namespace: int
    radius: np.ndarray                  # radius[i] = r(i); radius[0] = inf
    n_min: int = vband.N_MIN
    delta: float = vband.DELTA
    trials_per_program: int = vgen.TRIALS_PER_PROGRAM

    @property
    def horizons(self) -> Tuple[int, ...]:
        """PROTOCOL 7.1: n = 100, 500 and N_max (100 / 500 / 1,000 under T4)."""
        return tuple(sorted({h for h in (100, 500, self.n_max)
                             if h <= self.n_max}))

    @property
    def finalization_tick(self) -> int:
        return self.n_max + vgen.DRAIN_W


def make_config(n_max: int, namespace: int) -> RunConfig:
    """Radii come from ``vband.radius_from_formula``, i.e. from the pinned primitive."""
    radius = np.empty(n_max + 1)
    radius[0] = math.inf
    for n in range(1, n_max + 1):
        radius[n] = vband.radius_from_formula(n)
    return RunConfig(n_max=n_max, namespace=namespace, radius=radius)


# ---------------------------------------------------------------------------
# One trial: the three constructions, every look, every reported quantity
# ---------------------------------------------------------------------------
@dataclass
class Series:
    index: np.ndarray       # the construction's own index at each look
    prefix: np.ndarray      # the ENROLLED prefix at each look
    l_h: np.ndarray
    u_h: np.ndarray
    l_s: np.ndarray
    u_s: np.ndarray


def _band(sum_lo: np.ndarray, sum_hi: np.ndarray, index: np.ndarray,
          radius: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """``clip(sum/index -+ r(index), -1, 1)``; at index 0 the full range shows.

    Every enclosure endpoint is an integer, so ``sum`` is exact and this is the
    same IEEE arithmetic ``vband.normal_mixture_band`` performs.
    """
    safe = np.maximum(index, 1).astype(np.float64)
    r = radius[index]
    return (np.clip(sum_lo / safe - r, -1.0, 1.0),
            np.clip(sum_hi / safe + r, -1.0, 1.0))


def build_series(draw: vgen.TrialDraw, cfg: RunConfig
                 ) -> Tuple[Dict[str, Series], np.ndarray, np.ndarray, int]:
    """All three constructions at all 2,001 looks of one trial."""
    n = cfg.n_max
    fin_tick = cfg.finalization_tick
    sums = vgen.adapter_prefix_sums(draw, n)
    resolved, revealed, cprefix, running_max = vgen.resolution_counts(draw, n)
    cum_z, cum_d = vgen.prefix_sums_of_scores(draw)
    naive_h = vgen.completed_sums(draw, draw.z, n)
    naive_s = vgen.completed_sums(draw, draw.dsc, n)
    fin_state = vgen.state_at_age(draw, vgen.finalization_ages(draw, n))
    done_final = draw.resolution_tick <= fin_tick

    prefix = np.append(np.arange(1, n + 1, dtype=np.int64), n)

    # -- ADAPTER: the current full enrolled prefix, enclosures and all -------
    idx_a = prefix
    a_h_lo = np.append(sums.h_lo[1:], float(fin_state.h_lo.sum(dtype=np.int64)))
    a_h_hi = np.append(sums.h_hi[1:], float(fin_state.h_hi.sum(dtype=np.int64)))
    a_s_lo = np.append(sums.s_lo[1:], float(fin_state.s_lo.sum(dtype=np.int64)))
    a_s_hi = np.append(sums.s_hi[1:], float(fin_state.s_hi.sum(dtype=np.int64)))
    l_h, u_h = _band(a_h_lo, a_h_hi, idx_a, cfg.radius)
    l_s, u_s = _band(a_s_lo, a_s_hi, idx_a, cfg.radius)
    out = {ADAPTER: Series(idx_a, prefix, l_h, u_h, l_s, u_s)}

    # -- CPREFIX: the longest fully resolved prefix --------------------------
    k_fin = int(np.searchsorted(running_max, fin_tick, side="right"))
    idx_k = np.append(cprefix[1:], k_fin)
    k_h = cum_z[idx_k]
    k_s = cum_d[idx_k]
    l_h, u_h = _band(k_h, k_h, idx_k, cfg.radius)
    l_s, u_s = _band(k_s, k_s, idx_k, cfg.radius)
    out[CPREFIX] = Series(idx_k, prefix, l_h, u_h, l_s, u_s)

    # -- NAIVE: completed-only.  INVALID under informative delay -------------
    idx_m = np.append(resolved[1:], int(done_final.sum()))
    m_h = np.append(naive_h[1:], float(draw.z[done_final].sum(dtype=np.int64)))
    m_s = np.append(naive_s[1:], float(draw.dsc[done_final].sum(dtype=np.int64)))
    l_h, u_h = _band(m_h, m_h, idx_m, cfg.radius)
    l_s, u_s = _band(m_s, m_s, idx_m, cfg.radius)
    out[NAIVE] = Series(idx_m, prefix, l_h, u_h, l_s, u_s)
    return out, resolved, revealed, sums.updates


def _look_fractions(draw: vgen.TrialDraw, cfg: RunConfig, look: int,
                    cache: Dict[int, Tuple[float, float, float, float, int, int]]
                    ) -> Tuple[float, float, float, float, int, int]:
    """Resolution quantities at one look (PROTOCOL 9.5), by its look index."""
    if look in cache:
        return cache[look]
    if look < cfg.n_max:
        tick, prefix = look + 1, look + 1
    else:
        tick, prefix = cfg.finalization_tick, cfg.n_max
    ages = tick - np.arange(1, prefix + 1, dtype=np.int64)
    sub = vgen.TrialDraw(
        cell=draw.cell, namespace=draw.namespace,
        program_index=draw.program_index, trial_index=draw.trial_index,
        n=prefix, atom=draw.atom[:prefix], z=draw.z[:prefix],
        dsc=draw.dsc[:prefix], d=draw.d[:prefix], f=draw.f[:prefix],
        cand_first=draw.cand_first[:prefix], s_rev=draw.s_rev[:prefix],
        c_rev=draw.c_rev[:prefix], c_pend=draw.c_pend[:prefix],
        a_narrow=draw.a_narrow[:prefix], a_collapse=draw.a_collapse[:prefix])
    st = vgen.state_at_age(sub, ages)
    n_res = int(st.resolved.sum())
    n_unrev = int(st.unrevealed.sum())
    n_point_cost = int(st.cost_collapsed.sum())
    n_narrow = int(st.cost_narrowed.sum())
    value = ((prefix - n_res) / prefix, n_unrev / prefix,
             n_point_cost / prefix, n_narrow / prefix,
             n_res, n_res + n_point_cost)
    cache[look] = value
    return value


@dataclass
class TrialRecord:
    decision: int = NO_DECISION
    tau: int = 0
    decided_at_finalization: bool = False
    ever_below_h: bool = False
    ever_above_h: bool = False
    ever_below_s: bool = False
    ever_above_s: bool = False
    ever_miscover_h_elig: bool = False
    ever_miscover_s_elig: bool = False
    never_conjunct: bool = False
    never_conjunct_all_looks: bool = False
    unresolved_fraction: float = 0.0
    unrevealed_fraction: float = 0.0
    cost_collapsed_fraction: float = 0.0
    cost_narrowed_fraction: float = 0.0
    n_certified: int = 0
    n_point_resolved: int = 0
    look_prefix: int = 0
    horizon: Dict[int, Tuple[float, ...]] = field(default_factory=dict)

    @property
    def ever_miscover_h(self) -> bool:
        return self.ever_below_h or self.ever_above_h

    @property
    def ever_miscover_s(self) -> bool:
        return self.ever_below_s or self.ever_above_s


def evaluate_trial(draw: vgen.TrialDraw, cfg: RunConfig
                   ) -> Tuple[Dict[str, TrialRecord], int, int]:
    """Every reported quantity of PROTOCOL section 9 for one trial."""
    series, resolved, revealed, updates = build_series(draw, cfg)
    mu_h, mu_s = draw.cell.mu_h, draw.cell.mu_s
    n = cfg.n_max
    cache: Dict[int, Tuple] = {}
    out: Dict[str, TrialRecord] = {}
    n_looks = n + 1
    for name in CONSTRUCTIONS:
        s = series[name]
        rec = TrialRecord()
        below_h = mu_h < s.l_h
        above_h = mu_h > s.u_h
        below_s = mu_s < s.l_s
        above_s = mu_s > s.u_s
        rec.ever_below_h = bool(below_h.any())
        rec.ever_above_h = bool(above_h.any())
        rec.ever_below_s = bool(below_s.any())
        rec.ever_above_s = bool(above_s.any())

        eligible = s.index >= cfg.n_min
        rec.ever_miscover_h_elig = bool((eligible & (below_h | above_h)).any())
        rec.ever_miscover_s_elig = bool((eligible & (below_s | above_s)).any())

        deploy_cond = s.l_h > 0.0
        guard_cond = s.l_s > -cfg.delta
        harm_cond = s.u_h < 0.0
        deploy = eligible & deploy_cond & guard_cond
        harm = eligible & harm_cond
        fired = deploy | harm
        # PROTOCOL 9.2: the same-look conjunction, read out directly.  Both the
        # decision-eligible reading and the literal all-looks reading are kept,
        # because 9.2 states the event over "some look" while every other row of
        # its table is gated at n_min.
        both = eligible & deploy_cond & guard_cond
        rec.never_conjunct = bool((eligible & deploy_cond).any()
                                  and (eligible & guard_cond).any()
                                  and not both.any())
        rec.never_conjunct_all_looks = bool(
            deploy_cond.any() and guard_cond.any()
            and not (deploy_cond & guard_cond).any())

        if fired.any():
            i = int(np.argmax(fired))
            if deploy[i] and harm[i]:
                rec.decision = CONFLICT
            elif deploy[i]:
                rec.decision = DEPLOY
            else:
                rec.decision = RETAIN_INCUMBENT
            rec.tau = int(s.prefix[i])
            rec.decided_at_finalization = (i == n_looks - 1)
            report_look = i
        else:
            rec.decision = NO_DECISION
            rec.tau = int(cfg.n_max)          # the capped decision prefix rule
            report_look = n_looks - 1

        (rec.unresolved_fraction, rec.unrevealed_fraction,
         rec.cost_collapsed_fraction, rec.cost_narrowed_fraction,
         rec.n_certified, rec.n_point_resolved) = _look_fractions(
            draw, cfg, report_look, cache)
        rec.look_prefix = int(s.prefix[report_look])

        first_fire = int(np.argmax(fired)) if fired.any() else n_looks
        for h in cfg.horizons:
            i = h - 1
            unres = 1.0 - resolved[h] / h
            unrev = 1.0 - revealed[h] / h
            rec.horizon[h] = (
                float(s.l_h[i]), float(s.u_h[i]), float(s.l_s[i]), float(s.u_s[i]),
                float(bool((below_h[:h] | above_h[:h]).any())),
                float(bool((below_s[:h] | above_s[:h]).any())),
                float(first_fire < h and rec.decision == DEPLOY),
                float(first_fire < h and rec.decision == RETAIN_INCUMBENT),
                float(unres), float(unrev))
        out[name] = rec
    return out, n_looks, int(updates)


# ---------------------------------------------------------------------------
# Accumulators
# ---------------------------------------------------------------------------
TRIAL_FIELDS = ("decision", "tau", "decided_at_finalization",
                "ever_below_h", "ever_above_h", "ever_miscover_h",
                "ever_below_s", "ever_above_s", "ever_miscover_s",
                "ever_miscover_h_elig", "ever_miscover_s_elig",
                "never_conjunct", "never_conjunct_all_looks",
                "unresolved_fraction", "unrevealed_fraction",
                "cost_collapsed_fraction", "cost_narrowed_fraction",
                "n_certified", "n_point_resolved", "look_prefix")
HORIZON_FIELDS = ("L_h", "U_h", "L_s", "U_s", "miscover_h_so_far",
                  "miscover_s_so_far", "deploy_by", "retain_by",
                  "unresolved_fraction", "unrevealed_fraction")


class CellAccumulator:
    """Per-cell arrays; the per-trial CSV rows themselves stream to disk."""

    def __init__(self, cell: vgen.CellSpec, n_trials: int, horizons):
        self.cell = cell
        self.n_trials = n_trials
        self.horizons = tuple(horizons)
        self.i = 0
        self.data = {c: {f: np.zeros(n_trials) for f in TRIAL_FIELDS}
                     for c in CONSTRUCTIONS}
        self.hor = {c: {h: {f: np.zeros(n_trials) for f in HORIZON_FIELDS}
                        for h in self.horizons} for c in CONSTRUCTIONS}

    def add(self, records: Dict[str, TrialRecord]) -> None:
        i = self.i
        for c in CONSTRUCTIONS:
            rec = records[c]
            d = self.data[c]
            d["decision"][i] = rec.decision
            d["tau"][i] = rec.tau
            d["decided_at_finalization"][i] = rec.decided_at_finalization
            d["ever_below_h"][i] = rec.ever_below_h
            d["ever_above_h"][i] = rec.ever_above_h
            d["ever_miscover_h"][i] = rec.ever_miscover_h
            d["ever_below_s"][i] = rec.ever_below_s
            d["ever_above_s"][i] = rec.ever_above_s
            d["ever_miscover_s"][i] = rec.ever_miscover_s
            d["ever_miscover_h_elig"][i] = rec.ever_miscover_h_elig
            d["ever_miscover_s_elig"][i] = rec.ever_miscover_s_elig
            d["never_conjunct"][i] = rec.never_conjunct
            d["never_conjunct_all_looks"][i] = rec.never_conjunct_all_looks
            d["unresolved_fraction"][i] = rec.unresolved_fraction
            d["unrevealed_fraction"][i] = rec.unrevealed_fraction
            d["cost_collapsed_fraction"][i] = rec.cost_collapsed_fraction
            d["cost_narrowed_fraction"][i] = rec.cost_narrowed_fraction
            d["n_certified"][i] = rec.n_certified
            d["n_point_resolved"][i] = rec.n_point_resolved
            d["look_prefix"][i] = rec.look_prefix
            for h in self.horizons:
                vals = rec.horizon[h]
                for f, v in zip(HORIZON_FIELDS, vals):
                    self.hor[c][h][f][i] = v
        self.i += 1


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def _fmt(v: float) -> str:
    if isinstance(v, (bool, np.bool_)):
        return "1" if v else "0"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    f = float(v)
    if math.isnan(f):
        return "NA"
    if math.isinf(f):
        return "inf" if f > 0 else "-inf"
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return repr(f)


TRIAL_HEADER = ("cell,law,delay,program,trial,construction,construction_status,"
                "decision,tau,decided_at_finalization,ever_below_h,ever_above_h,"
                "ever_miscover_h,ever_below_s,ever_above_s,ever_miscover_s,"
                "ever_miscover_h_decision_eligible,ever_miscover_s_decision_eligible,"
                "never_conjunct,never_conjunct_all_looks,unresolved_fraction,"
                "unrevealed_fraction,cost_collapsed_fraction,cost_narrowed_fraction,"
                "n_certified,n_point_resolved,look_prefix\n")


def trial_rows(cell, program, trial, records: Dict[str, TrialRecord]) -> str:
    out = []
    for c in CONSTRUCTIONS:
        r = records[c]
        out.append(",".join([
            cell.id, cell.law, cell.delay, str(program), str(trial), c,
            CONSTRUCTION_STATUS[c], DECISION_LABEL[r.decision], str(r.tau),
            _fmt(r.decided_at_finalization), _fmt(r.ever_below_h),
            _fmt(r.ever_above_h), _fmt(r.ever_miscover_h), _fmt(r.ever_below_s),
            _fmt(r.ever_above_s), _fmt(r.ever_miscover_s),
            _fmt(r.ever_miscover_h_elig), _fmt(r.ever_miscover_s_elig),
            _fmt(r.never_conjunct), _fmt(r.never_conjunct_all_looks),
            _fmt(r.unresolved_fraction), _fmt(r.unrevealed_fraction),
            _fmt(r.cost_collapsed_fraction), _fmt(r.cost_narrowed_fraction),
            str(r.n_certified), str(r.n_point_resolved), str(r.look_prefix),
        ]) + "\n")
    return "".join(out)


@dataclass
class BlockCounts:
    programs: int = 0
    trials: int = 0
    pairs: int = 0
    looks: int = 0
    band_evaluations: int = 0
    enclosure_updates: int = 0

    def add(self, other: "BlockCounts") -> None:
        self.programs += other.programs
        self.trials += other.trials
        self.pairs += other.pairs
        self.looks += other.looks
        self.band_evaluations += other.band_evaluations
        self.enclosure_updates += other.enclosure_updates

    def as_dict(self) -> Dict[str, int]:
        return {"programs": self.programs, "trials": self.trials,
                "enrolled_pairs": self.pairs, "looks": self.looks,
                "band_evaluations": self.band_evaluations,
                "enclosure_updates": self.enclosure_updates}


def run_block(cell: vgen.CellSpec, programs: Sequence[int], cfg: RunConfig,
              sink: Optional[RowSink],
              accum: Optional[CellAccumulator]) -> BlockCounts:
    """One (cell, block of programs).  Records stream out; nothing is buffered."""
    counts = BlockCounts()
    for program in programs:
        for trial in range(cfg.trials_per_program):
            draw = vgen.draw_trial(cell, program, trial, n_max=cfg.n_max,
                                   namespace=cfg.namespace)
            records, n_looks, updates = evaluate_trial(draw, cfg)
            counts.trials += 1
            counts.pairs += cfg.n_max
            counts.looks += n_looks
            counts.band_evaluations += n_looks * len(CONSTRUCTIONS) * 2
            counts.enclosure_updates += updates
            if sink is not None:
                sink.write(trial_rows(cell, program, trial, records))
            if accum is not None:
                accum.add(records)
        counts.programs += 1
    return counts


# ---------------------------------------------------------------------------
# PROTOCOL 9: the reported tables
# ---------------------------------------------------------------------------
NOMINAL_EVER_MISCOVER = vband.ALPHA_GATE            # 0.00625
NOMINAL_TRIAL_ERROR = vband.ALPHA_PER_TRIAL         # 0.0125
NOMINAL_FAMILY = vband.PROGRAM_ALPHA                # 0.05


def _rate_row(cell, construction, extra: Dict[str, object], x: int, n: int,
              nominal: Optional[float]) -> Dict[str, object]:
    rate, lo, hi = wilson(int(x), int(n))
    row = {"cell": cell.id, "law": cell.law, "law_name": cell.law_name,
           "delay": cell.delay, "construction": construction,
           "construction_status": CONSTRUCTION_STATUS[construction]}
    row.update(extra)
    row.update({"x": int(x), "N": int(n), "rate": rate,
                "wilson_lo": lo, "wilson_hi": hi,
                "nominal": "" if nominal is None else nominal,
                "flagged": int(is_flagged(lo, nominal))})
    return row


def miscoverage_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        for gate, mu, below, above, elig in (
                ("hierarchy", cell.mu_h, d["ever_below_h"], d["ever_above_h"],
                 d["ever_miscover_h_elig"]),
                ("success", cell.mu_s, d["ever_below_s"], d["ever_above_s"],
                 d["ever_miscover_s_elig"])):
            miscover = (below > 0) | (above > 0)
            for event, vec in (("ever_miscover", miscover),
                               ("ever_below", below > 0),
                               ("ever_above", above > 0)):
                rows.append(_rate_row(
                    cell, c, {"gate": gate, "mu": mu, "looks": "all",
                              "event": event},
                    int(vec.sum()), n, NOMINAL_EVER_MISCOVER))
            rows.append(_rate_row(
                cell, c, {"gate": gate, "mu": mu,
                          "looks": "decision_eligible", "event": "ever_miscover"},
                int((elig > 0).sum()), n, NOMINAL_EVER_MISCOVER))
    return rows


def decision_rows(acc: CellAccumulator, delta: float) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    truth_deploy_correct = (cell.mu_h > 0.0) and (cell.mu_s > -delta)
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        dec = d["decision"]
        deploy = dec == DEPLOY
        retain = dec == RETAIN_INCUMBENT
        conflict = dec == CONFLICT
        none = dec == NO_DECISION
        false_deploy = deploy & (not truth_deploy_correct)
        correct_deploy = deploy & truth_deploy_correct
        false_harm = retain & (cell.mu_h >= 0.0)
        any_err = false_deploy | false_harm
        # PROTOCOL 9.2's two identities, asserted as this tabulates
        if int(false_harm.sum()) != int(retain.sum()):
            raise AssertionError(
                f"{cell.id}/{c}: mu_h = {cell.mu_h} >= 0, so every "
                f"RETAIN_INCUMBENT must be a false harm")
        if truth_deploy_correct:
            if int(false_deploy.sum()) != 0:
                raise AssertionError(
                    f"{cell.id}/{c}: false_deploy must be exactly 0 where DEPLOY "
                    f"is the correct decision")
        elif int(false_deploy.sum()) != int(deploy.sum()):
            raise AssertionError(
                f"{cell.id}/{c}: every DEPLOY in this cell is an error")
        family = any_err.reshape(-1, vgen.TRIALS_PER_PROGRAM).any(axis=1)
        for quantity, vec, unit, nominal in (
                ("false_deploy", false_deploy, "trial", NOMINAL_EVER_MISCOVER),
                ("false_harm", false_harm, "trial", NOMINAL_EVER_MISCOVER),
                ("any_erroneous_trial", any_err, "trial", NOMINAL_TRIAL_ERROR),
                ("correct_deploy", correct_deploy, "trial", None),
                ("deploy", deploy, "trial", None),
                ("retain_incumbent", retain, "trial", None),
                ("no_decision", none, "trial", None),
                ("conflict", conflict, "trial", None),
                ("never_conjunct", d["never_conjunct"] > 0, "trial", None),
                ("never_conjunct_all_looks", d["never_conjunct_all_looks"] > 0,
                 "trial", None),
                ("decided_at_finalization", d["decided_at_finalization"] > 0,
                 "trial", None)):
            rows.append(_rate_row(cell, c, {"quantity": quantity, "unit": unit},
                                  int(np.count_nonzero(vec)), n, nominal))
        rows.append(_rate_row(
            cell, c, {"quantity": "family_any_erroneous", "unit": "program"},
            int(family.sum()), len(family), NOMINAL_FAMILY))
    return rows


def _quartiles(v: np.ndarray) -> Tuple[float, float, float]:
    if v.size == 0:
        return (float("nan"),) * 3
    q = np.percentile(v, [25, 50, 75])
    return (float(q[0]), float(q[1]), float(q[2]))


def decision_time_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        decided = d["decision"] != NO_DECISION
        capped = d["tau"]
        cond = d["tau"][decided]
        cq = _quartiles(capped)
        kq = _quartiles(cond)
        rows.append({
            "cell": cell.id, "law": cell.law, "law_name": cell.law_name,
            "delay": cell.delay, "construction": c,
            "construction_status": CONSTRUCTION_STATUS[c],
            "unit": "enrolled pairs (never wall clock)",
            "n_trials": acc.n_trials, "n_deciding": int(decided.sum()),
            "deciding_fraction": float(decided.mean()),
            "capped_fraction": float(1.0 - decided.mean()),
            "capped_q1": cq[0], "capped_median": cq[1], "capped_q3": cq[2],
            "conditional_q1": kq[0], "conditional_median": kq[1],
            "conditional_q3": kq[2]})
    return rows


def unresolved_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        for quantity in ("unresolved_fraction", "unrevealed_fraction",
                         "cost_collapsed_fraction", "cost_narrowed_fraction",
                         "n_certified", "n_point_resolved", "look_prefix"):
            v = d[quantity]
            q = _quartiles(v)
            rows.append({
                "cell": cell.id, "law": cell.law, "law_name": cell.law_name,
                "delay": cell.delay, "construction": c,
                "construction_status": CONSTRUCTION_STATUS[c],
                "quantity": quantity, "N": acc.n_trials, "mean": float(v.mean()),
                "q1": q[0], "median": q[1], "q3": q[2]})
    return rows


def horizon_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    rate_fields = {"miscover_h_so_far": NOMINAL_EVER_MISCOVER,
                   "miscover_s_so_far": NOMINAL_EVER_MISCOVER,
                   "deploy_by": None, "retain_by": None}
    for c in CONSTRUCTIONS:
        for h in acc.horizons:
            for f in HORIZON_FIELDS:
                v = acc.hor[c][h][f]
                base = {"cell": cell.id, "law": cell.law,
                        "law_name": cell.law_name, "delay": cell.delay,
                        "construction": c,
                        "construction_status": CONSTRUCTION_STATUS[c],
                        "horizon": h, "quantity": f, "N": n}
                if f in rate_fields:
                    x = int(np.count_nonzero(v))
                    rate, lo, hi = wilson(x, n)
                    nominal = rate_fields[f]
                    base.update({"kind": "rate", "mean": rate, "q1": "",
                                 "median": "", "q3": "", "x": x, "rate": rate,
                                 "wilson_lo": lo, "wilson_hi": hi,
                                 "nominal": "" if nominal is None else nominal,
                                 "flagged": int(is_flagged(lo, nominal))})
                else:
                    q = _quartiles(v)
                    base.update({"kind": "distribution", "mean": float(v.mean()),
                                 "q1": q[0], "median": q[1], "q3": q[2],
                                 "x": "", "rate": "", "wilson_lo": "",
                                 "wilson_hi": "", "nominal": "", "flagged": 0})
                rows.append(base)
    return rows


def write_csv(guard: WriteGuard, name: str, rows: List[Dict[str, object]],
              note: str) -> None:
    if not rows:
        guard.write_text(name, f"# {note}\n")
        return
    cols = list(rows[0].keys())
    lines = [f"# {note}"]
    lines.append(",".join(cols))
    for r in rows:
        lines.append(",".join(_fmt(r[c]) if not isinstance(r[c], str)
                              else r[c] for c in cols))
    guard.write_text(name, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# PROTOCOL 8.1: the smoke run, and 8.2: the budget ladder
# ---------------------------------------------------------------------------
SMOKE_PERMITTED_FILES = ("timing.json",)
SMOKE_PERMITTED_KEYS = {
    "protocol_smoke", "namespace", "points", "cell", "programs", "N_max",
    "seconds", "seconds_per_program", "peak_rss_bytes", "output_bytes",
    "record_bytes_measured_not_written", "trials", "enrolled_pairs", "looks",
    "band_evaluations", "enclosure_updates", "enclosure_updates_per_pair",
    "measures_only", "seeds", "note", "total_seconds", "total_programs",
}


def run_smoke(guard: WriteGuard, programs: int,
              verbose: bool = True) -> Dict[str, object]:
    """PROTOCOL 8.1: exactly one 20-program smoke run, measuring only.

    Its seeds come from namespace 1 and are discarded.  Its effect columns are
    computed (they are what makes the timing representative) but are never
    formed into a per-trial record on disk and are never read: the only values
    that leave this function are seconds, bytes, memory and counts.
    """
    half = programs // 2
    split = ((vgen.CELL_BY_ID["C1"], max(half, 1), 2000),
             (vgen.CELL_BY_ID["C2"], programs - max(half, 1), 1000))
    points = []
    total_seconds = 0.0
    for cell, n_programs, n_max in split:
        if n_programs <= 0:
            continue
        cfg = make_config(n_max, vgen.NAMESPACE_SMOKE)
        sink = RowSink(None, TRIAL_HEADER, discard=True)
        t0 = time.perf_counter()
        counts = run_block(cell, range(n_programs), cfg, sink, None)
        seconds = time.perf_counter() - t0
        record_bytes = sink.close()
        total_seconds += seconds
        points.append({
            "cell": cell.id, "programs": n_programs, "N_max": n_max,
            "seconds": seconds, "seconds_per_program": seconds / n_programs,
            "record_bytes_measured_not_written": int(record_bytes),
            "trials": counts.trials, "enrolled_pairs": counts.pairs,
            "looks": counts.looks, "band_evaluations": counts.band_evaluations,
            "enclosure_updates": counts.enclosure_updates,
            "enclosure_updates_per_pair":
                counts.enclosure_updates / max(counts.pairs, 1)})
        if verbose:
            print(f"  smoke {cell.id} N_max={n_max}: {n_programs} programs in "
                  f"{seconds:.2f}s ({seconds / n_programs:.3f}s/program)")
    record = {
        "protocol_smoke": programs == 20,
        "namespace": vgen.NAMESPACE_SMOKE,
        "measures_only": ["wall_clock_seconds", "peak_rss", "output_bytes",
                          "counts"],
        "seeds": "discarded, never reused",
        "note": ("effect columns are never formed into a record here and are "
                 "never read; they play no part in choosing anything"),
        "points": points,
        "total_seconds": total_seconds,
        "total_programs": sum(p["programs"] for p in points),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    guard.write_json("smoke/timing.json", record)
    return record


def assert_smoke_holds_no_effect_record(guard: WriteGuard) -> None:
    """PROTOCOL 8.1's own requirement on this module, checked before the grid."""
    smoke_dir = guard.path("smoke")
    present = sorted(p.name for p in smoke_dir.iterdir() if p.is_file())
    unexpected = [p for p in present if p not in SMOKE_PERMITTED_FILES]
    if unexpected:
        raise SystemExit(f"the smoke directory holds files that are not a "
                         f"timing record: {unexpected}")
    for name in present:
        payload = json.loads((smoke_dir / name).read_text())
        stack = [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    if k not in SMOKE_PERMITTED_KEYS:
                        raise SystemExit(
                            f"the smoke record carries the key {k!r}, which is "
                            f"not a timing, memory, byte or count field")
                    stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)


def select_tier(smoke: Dict[str, object], cfg_json: dict) -> Dict[str, object]:
    """PROTOCOL 8.2: the ladder, from runtime and memory measurements alone."""
    limits = cfg_json["budget"]["hard_limits"]
    points = {p["N_max"]: p for p in smoke["points"]}
    if 2000 not in points or 1000 not in points:
        return {"beta": None, "selected_tier": None, "paused": True,
                "ladder": [], "hard_limits": limits,
                "note": "the smoke run did not produce both horizon points, so "
                        "the scaling exponent cannot be measured and no tier "
                        "may be selected"}
    s_2000 = points[2000]["seconds_per_program"]
    s_1000 = points[1000]["seconds_per_program"]
    beta = math.log(s_2000 / s_1000) / math.log(2.0)
    record_bytes = sum(p["record_bytes_measured_not_written"] for p in
                       smoke["points"])
    bytes_per_program = record_bytes / max(int(smoke["total_programs"]), 1)
    ladder = []
    selected = None
    for tier in cfg_json["budget"]["ladder"]:
        total = tier["programs_total"]
        n_max = tier["N_max"]
        seconds = s_2000 * total * (n_max / 2000.0) ** beta
        out_bytes = bytes_per_program * total
        entry = {"tier": tier["tier"], "programs_total": total, "N_max": n_max,
                 "seconds_projected": seconds,
                 "bytes_projected": out_bytes,
                 "peak_rss_projected": int(smoke["peak_rss_bytes"]),
                 "within_seconds": seconds <= limits["seconds"],
                 "within_bytes": out_bytes <= limits["output_bytes"],
                 "within_peak_rss":
                     int(smoke["peak_rss_bytes"]) <= limits["peak_rss_bytes"]}
        entry["admissible"] = bool(entry["within_seconds"]
                                   and entry["within_bytes"]
                                   and entry["within_peak_rss"])
        ladder.append(entry)
        if selected is None and entry["admissible"]:
            selected = tier["tier"]
    return {"beta": beta, "s_per_program_2000": s_2000,
            "s_per_program_1000": s_1000,
            "bytes_per_program": bytes_per_program,
            "ladder": ladder, "selected_tier": selected,
            "paused": selected is None,
            "selection_rule": cfg_json["budget"]["selection_rule"],
            "hard_limits": limits}


def assert_incremental(smoke: Dict[str, object]) -> Dict[str, object]:
    """PROTOCOL 8.1: the running sums are maintained incrementally, not recomputed."""
    worst = 0.0
    for p in smoke["points"]:
        per_pair = p["enclosure_updates_per_pair"]
        worst = max(worst, per_pair)
        if per_pair > vgen.BREAKPOINTS_PER_PAIR:
            raise SystemExit(
                f"the enclosure sums are not incremental: {per_pair:.2f} updates "
                f"per pair, above the {vgen.BREAKPOINTS_PER_PAIR} a pair can "
                f"logically make")
    return {"enclosure_updates_per_pair_max": worst,
            "bound_per_pair": vgen.BREAKPOINTS_PER_PAIR,
            "incremental": True}


# ---------------------------------------------------------------------------
# The fixture gate and the manifest
# ---------------------------------------------------------------------------
def run_fixture_gate(guard: WriteGuard) -> Dict[str, object]:
    """PROTOCOL 11: run the frozen fixture command and deposit its report.

    The fixtures are run in a SUBPROCESS, exactly as the frozen command runs
    them, so that this module's own interpreter never loads anything the
    independence rule keeps out of it.
    """
    cmd = [sys.executable, str(HERE / "vfixtures.py")]
    done = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    cases: Dict[str, str] = {}
    for line in done.stdout.splitlines():
        if line.startswith("ok   "):
            cases[line[5:].strip()] = "pass"
        elif line.startswith("FAIL "):
            cases[line[5:].strip()] = "fail"
    report = {"command": "vfixtures.py", "returncode": done.returncode,
              "cases": cases, "passed": sum(1 for v in cases.values()
                                            if v == "pass"),
              "total": len(cases),
              "stderr_tail": done.stderr.strip()[-2000:]}
    guard.write_json("fixtures_report.json", report)
    return report


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_commit() -> str:
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=30)
        return done.stdout.strip() if done.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):       # pragma: no cover
        return "unknown"


def write_manifest(guard: WriteGuard, tier: Optional[str], cfg: RunConfig,
                   grid: Dict[str, int]) -> None:
    sources = {}
    for p in sorted(HERE.glob("*.py")):
        sources[p.name] = sha256_file(p)
    for p in (CELLS_JSON, PROTOCOL_MD, PINNED_PRIMITIVE, GUIDANCE_DOC):
        if p.exists():
            sources[str(p.relative_to(REPO_ROOT))] = sha256_file(p)
    guard.write_json("manifest.json", {
        "study": "live_ab_validation (issue 12)",
        "protocol_version": json.loads(CELLS_JSON.read_text())["version"],
        "master_seed": vgen.MASTER_SEED,
        "grid_namespace": cfg.namespace,
        "namespace_of_the_reported_grid": vgen.NAMESPACE_GRID,
        "sha256": sources,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repo_commit": repo_commit(),
        "selected_budget_tier": tier,
        "N_max": cfg.n_max,
        "programs_per_cell": grid,
        "reported_grid": guard.reported,
        "coverage_target_boundary": json.loads(
            CELLS_JSON.read_text())["coverage_target_boundary"],
    })


# ---------------------------------------------------------------------------
# Correctness cross-checks (no output files, nothing reported)
# ---------------------------------------------------------------------------
def _drive_vband(draw: vgen.TrialDraw, n_pairs: int):
    """Replay a whole trial through ``vband.ValidationMonitor``, event by event."""
    mon = vband.ValidationMonitor(cost_cap=vgen.COST_CAP)
    s_c, s_i = vgen.ATOM_SC[draw.atom], vgen.ATOM_SI[draw.atom]
    looks = []
    for n in range(1, n_pairs + 1):
        mon.enroll(n, "AB", (n, "C"), (n, "I"))
        for j in range(1, n + 1):
            k, age = j - 1, n - j
            first = (j, "C") if draw.cand_first[k] else (j, "I")
            second = (j, "I") if draw.cand_first[k] else (j, "C")
            s_first = int(s_c[k] if draw.cand_first[k] else s_i[k])
            s_second = int(s_i[k] if draw.cand_first[k] else s_c[k])
            if age >= draw.f[k]:
                mon.finalize(first, s_first, float(draw.c_rev[k]))
            elif draw.f[k] > 0:
                mon.observe_elapsed_cost(
                    first, (float(draw.c_rev[k]) * age) / int(draw.f[k]))
            if age >= draw.d[k]:
                mon.finalize(second, s_second, float(draw.c_pend[k]))
            elif draw.d[k] > 0:
                mon.observe_elapsed_cost(
                    second, (float(draw.c_pend[k]) * age) / int(draw.d[k]))
        looks.append(mon.look())
    return mon, looks


def selfcheck_brute_force(n_pairs: int = 300, verbose: bool = True) -> List[str]:
    """The incremental machinery against a direct look-by-look recomputation.

    ``vband`` covers the ADAPTER only.  This covers what it cannot: the
    difference-array running sums at a realistic prefix, the CPREFIX index
    ``k(t) = max{k : every pair 1..k is fully resolved}``, the completed count
    ``m`` and the completed-only sums, each recomputed from scratch at every
    look by the definition in PROTOCOL 3.
    """
    fails: List[str] = []
    cfg = make_config(n_pairs, vgen.NAMESPACE_SMOKE)
    for cell in vgen.CELLS[:4]:
        draw = vgen.draw_trial(cell, 11, 1, n_max=n_pairs,
                               namespace=vgen.NAMESPACE_SMOKE)
        sums = vgen.adapter_prefix_sums(draw, n_pairs)
        resolved, revealed, cprefix, _rm = vgen.resolution_counts(draw, n_pairs)
        naive_h = vgen.completed_sums(draw, draw.z, n_pairs)
        for n in range(1, n_pairs + 1):
            positions = np.arange(1, n + 1, dtype=np.int64)
            sub = vgen.TrialDraw(
                cell=cell, namespace=draw.namespace, program_index=11,
                trial_index=1, n=n, atom=draw.atom[:n], z=draw.z[:n],
                dsc=draw.dsc[:n], d=draw.d[:n], f=draw.f[:n],
                cand_first=draw.cand_first[:n], s_rev=draw.s_rev[:n],
                c_rev=draw.c_rev[:n], c_pend=draw.c_pend[:n],
                a_narrow=draw.a_narrow[:n], a_collapse=draw.a_collapse[:n])
            st = vgen.state_at_age(sub, n - positions)
            done = draw.d[:n] <= (n - positions)
            m = int(done.sum())
            k = 0
            for j in range(n):
                if not done[j]:
                    break
                k = j + 1
            if float(sums.h_lo[n]) != float(st.h_lo.sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: incremental h_lo sum differs")
            if float(sums.s_hi[n]) != float(st.s_hi.sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: incremental s_hi sum differs")
            if int(resolved[n]) != m:
                fails.append(f"{cell.id} n={n}: completed count {resolved[n]} != {m}")
            if int(cprefix[n]) != k:
                fails.append(f"{cell.id} n={n}: CPREFIX index {cprefix[n]} != {k}")
            if float(naive_h[n]) != float(draw.z[:n][done].sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: completed-only sum differs")
            if int(revealed[n]) != int((draw.f[:n] <= (n - positions)).sum()):
                fails.append(f"{cell.id} n={n}: revealed count differs")
            if fails:
                return fails
    if verbose:
        print(f"  brute-force: {4 * n_pairs} looks recomputed from the "
              f"definitions, 0 mismatch(es)")
    return fails


def selfcheck(n_pairs: int = 35, programs: int = 2,
              verbose: bool = True) -> List[str]:
    """The accelerator is exactly ``vband``, or these numbers are void.

    Drives ``vband.ValidationMonitor`` over whole trials, event by event, and
    asserts STRICT FLOAT EQUALITY of every band endpoint, every enclosure
    endpoint and every decision at every look against the vectorized path this
    module runs the grid with.  Also re-runs one trial twice and asserts the
    streams are identical, and checks the radius table against
    ``vband.radius_from_formula`` at strict equality.
    """
    fails: List[str] = []
    cfg = make_config(n_pairs, vgen.NAMESPACE_SMOKE)
    checked = 0
    for cell in vgen.CELLS:
        for program in range(programs):
            draw = vgen.draw_trial(cell, program, 0, n_max=n_pairs,
                                   namespace=vgen.NAMESPACE_SMOKE)
            sums = vgen.adapter_prefix_sums(draw, n_pairs)
            idx = np.arange(1, n_pairs + 1)
            l_h, u_h = _band(sums.h_lo[1:], sums.h_hi[1:], idx, cfg.radius)
            l_s, u_s = _band(sums.s_lo[1:], sums.s_hi[1:], idx, cfg.radius)
            mon, looks = _drive_vband(draw, n_pairs)
            for i, look in enumerate(looks):
                checked += 1
                pairs = ((sums.h_lo[i + 1], look.hierarchy.sum_lower, "sum_h_lo"),
                         (sums.h_hi[i + 1], look.hierarchy.sum_upper, "sum_h_hi"),
                         (sums.s_lo[i + 1], look.success.sum_lower, "sum_s_lo"),
                         (sums.s_hi[i + 1], look.success.sum_upper, "sum_s_hi"),
                         (l_h[i], look.hierarchy.lower, "L_h"),
                         (u_h[i], look.hierarchy.upper, "U_h"),
                         (l_s[i], look.success.lower, "L_s"),
                         (u_s[i], look.success.upper, "U_s"))
                for got, want, name in pairs:
                    if float(got) != float(want):
                        fails.append(f"{cell.id}/p{program} look n={i + 1} "
                                     f"{name}: vectorized {got!r} != vband {want!r}")
                decision = vband.decide(look.hierarchy, look.success)
                mine = DEPLOY if (idx[i] >= cfg.n_min and l_h[i] > 0
                                  and l_s[i] > -cfg.delta) else (
                    RETAIN_INCUMBENT if (idx[i] >= cfg.n_min and u_h[i] < 0)
                    else NO_DECISION)
                if DECISION_LABEL[mine].replace("NO_DECISION", "CONTINUE") != \
                        decision:
                    fails.append(f"{cell.id}/p{program} look n={i + 1}: decision "
                                 f"{DECISION_LABEL[mine]} != vband {decision}")
            state = vgen.state_at_age(draw, n_pairs - np.arange(1, n_pairs + 1))
            for k, pair in enumerate(mon.pairs):
                got = (pair.hierarchy.lo, pair.hierarchy.hi,
                       pair.success.lo, pair.success.hi)
                want = (float(state.h_lo[k]), float(state.h_hi[k]),
                        float(state.s_lo[k]), float(state.s_hi[k]))
                if got != want:
                    fails.append(f"{cell.id}/p{program} pair {k + 1} enclosure "
                                 f"{got} != vband {want}")
            last = looks[-1]
            n_res = int(state.resolved.sum())
            if last.n_certified != n_res:
                fails.append(f"{cell.id}/p{program}: certified {last.n_certified}"
                             f" != {n_res}")
            if last.n_point_resolved != n_res + int(state.cost_collapsed.sum()):
                fails.append(f"{cell.id}/p{program}: point-resolved count differs")
    # the radius table is the pinned primitive, at strict equality
    for n in sorted({1, 2, max(n_pairs // 2, 1), n_pairs}):
        if cfg.radius[n] != vband.radius_from_formula(n):
            fails.append(f"radius({n}) differs from vband")
    # two draws of the same stream are identical
    a = vgen.draw_trial(vgen.CELLS[3], 7, 2, n_max=200,
                        namespace=vgen.NAMESPACE_SMOKE)
    b = vgen.draw_trial(vgen.CELLS[3], 7, 2, n_max=200,
                        namespace=vgen.NAMESPACE_SMOKE)
    for name in ("atom", "d", "f", "cand_first"):
        if not np.array_equal(getattr(a, name), getattr(b, name)):
            fails.append(f"the stream is not reproducible in {name}")
    if verbose:
        print(f"  cross-checked {checked} looks against vband.ValidationMonitor "
              f"at strict float equality: {len(fails)} mismatch(es)")
    return fails


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def positive_control(rows: List[Dict[str, object]]) -> Dict[str, object]:
    """PROTOCOL 9.4, precommitted and frozen before any outcome existed."""
    cells = ("C2", "C4", "C6")
    flagged = []
    for r in rows:
        if (r["construction"] == NAIVE and r.get("gate") == "hierarchy"
                and r.get("event") == "ever_miscover"
                and r.get("looks") == "all" and r["cell"] in cells):
            if r["flagged"]:
                flagged.append(r["cell"])
    passed = bool(flagged)
    return {
        "statement": ("NAIVE's hierarchy ever-miscoverage must be FLAGGED in at "
                      "least one of C2, C4, C6"),
        "flagged_cells": flagged,
        "passed": passed,
        "consequence_if_failed": (
            "the measurement apparatus itself is reported as unvalidated, the "
            "ADAPTER results of this run are reported as uninterpretable, and "
            "the cause is investigated before any of them is cited"),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--smoke", type=int, default=None, metavar="N",
                    help="run only the measurement-only smoke run, with N programs")
    ap.add_argument("--selfcheck", action="store_true",
                    help="cross-check the accelerator against vband and stop")
    ap.add_argument("--cells", default=None,
                    help="ad-hoc: restrict to these cell ids")
    ap.add_argument("--programs", type=int, default=None,
                    help="ad-hoc: programs per cell")
    ap.add_argument("--n-max", type=int, default=None, help="ad-hoc: horizon")
    ap.add_argument("--tier", default=None, help="ad-hoc: force a budget tier")
    args = ap.parse_args(argv)

    if args.selfcheck:
        print("vrun selfcheck: the vectorized path against vband, event by event")
        fails = selfcheck()
        fails += selfcheck_brute_force()
        for f in fails[:20]:
            print(f"  MISMATCH {f}")
        print(f"\nvgen against the frozen PROTOCOL 6 tables:")
        report = vgen.selfcheck_report(verbose=False)
        print(f"  boundary states between the 2.5 readings: "
              f"{report['boundary_states']} (PROTOCOL 2.5 states 128)")
        for reading in vgen.READINGS:
            print(f"  {reading}: {len(report[reading])} disagreement(s)")
        return 1 if fails else 0

    overrides = (args.cells is not None or args.programs is not None
                 or args.n_max is not None or args.tier is not None
                 or (args.smoke is not None and args.smoke != 20))
    reported = not overrides
    # An ad-hoc run never draws from namespace 0.  The reported grid's streams
    # stay unseen until the reported grid runs (PROTOCOL 5, 8.1).
    grid_namespace = vgen.NAMESPACE_GRID if reported else vgen.NAMESPACE_SMOKE
    guard = WriteGuard(Path(args.out), reported=reported)
    cfg_json = json.loads(CELLS_JSON.read_text())
    started = time.time()
    print(f"live_ab_validation grid runner -> {guard.root}")
    print(f"  reported grid: {reported} (grid namespace {grid_namespace})")

    # ---- 1. the fixture gate ------------------------------------------------
    # The gate is FAIL-CLOSED FOR THE REPORTED GRID and carries no exemption for
    # any case.  It is evaluated here and enforced at step 4, immediately before
    # the grid draws its first namespace-0 stream, because the measurement-only
    # smoke run of PROTOCOL 8.1 produces no reported quantity and 8.2 requires
    # budget.json to be written BEFORE the grid starts.  Deferring the raise by
    # two measurement-only steps is not an exemption: no failing case ever lets
    # the grid run.
    fixtures = None
    fixture_failures: List[str] = []
    if reported:
        print("\n[1/6] fixture gate (PROTOCOL 11)")
        fixtures = run_fixture_gate(guard)
        fixture_failures = sorted(k for k, v in fixtures["cases"].items()
                                  if v != "pass")
        if fixtures["returncode"] != 0 and not fixture_failures:
            fixture_failures = ["<the fixture command failed without naming a case>"]
        print(f"  {fixtures['passed']}/{fixtures['total']} fixtures passed")
        if fixture_failures:
            print(f"  GATE CLOSED: {fixture_failures}")
            print("  The reported grid does not run until they pass. The gate "
                  "carries no exemption for any case, because a gate with an "
                  "exemption is the defect this study exists to find. The "
                  "measurement-only steps 2 and 3 still run, and budget.json "
                  "records the gate as closed.")

    # ---- 2. the smoke run ---------------------------------------------------
    n_smoke = args.smoke if args.smoke is not None else 20
    print(f"\n[2/6] smoke run (PROTOCOL 8.1), namespace {vgen.NAMESPACE_SMOKE}, "
          f"{n_smoke} programs, measuring runtime and memory only")
    smoke = run_smoke(guard, n_smoke)
    assert_smoke_holds_no_effect_record(guard)
    incremental = assert_incremental(smoke)
    print(f"  peak RSS {smoke['peak_rss_bytes'] / 2**20:.0f} MiB; "
          f"{incremental['enclosure_updates_per_pair_max']:.2f} enclosure "
          f"updates per pair (bound {vgen.BREAKPOINTS_PER_PAIR})")

    # ---- 3. the budget ladder ----------------------------------------------
    print("\n[3/6] budget ladder (PROTOCOL 8.2), written before the grid runs")
    budget = select_tier(smoke, cfg_json)
    budget["incremental_property"] = incremental
    budget["smoke"] = smoke
    budget["protocol_smoke"] = smoke["protocol_smoke"]
    budget["fixture_gate"] = {
        "ran": fixtures is not None,
        "passed": None if fixtures is None else fixtures["passed"],
        "total": None if fixtures is None else fixtures["total"],
        "failing_cases": fixture_failures,
        "closed": bool(fixture_failures),
        "fail_closed_for_the_reported_grid": True,
        "exemptions": [],
    }
    budget["grid_may_start"] = bool(not fixture_failures
                                    and not budget["paused"])
    if overrides:
        budget["reported_grid"] = False
        budget["note"] = ("this run carries grid overrides; it is a shakedown, "
                          "not the reported grid, and its tier is not a "
                          "PROTOCOL 8.2 selection")
    guard.write_json("budget.json", budget)
    if budget["beta"] is not None:
        print(f"  beta = {budget['beta']:.3f}; "
              f"s/program at 2000 = {budget['s_per_program_2000']:.3f}")
    for entry in budget["ladder"]:
        print(f"  {entry['tier']}: {entry['seconds_projected'] / 60:8.1f} min, "
              f"{entry['bytes_projected'] / 2**20:7.1f} MiB -> "
              f"{'admissible' if entry['admissible'] else 'over budget'}")
    if args.smoke is not None:
        print(f"\nsmoke run complete; selected tier would be "
              f"{budget['selected_tier']}")
        return 0
    if budget["paused"] and not overrides:
        print("\nPAUSED: even T4 exceeds a hard limit. The run does not silently "
              "shrink further, does not drop a cell and does not reduce the "
              "number of constructions (PROTOCOL 8.2).")
        return 3

    # ---- 4. the reported grid ----------------------------------------------
    if fixture_failures:
        raise SystemExit(
            "the fixture gate is fail-closed and these cases did not pass: "
            f"{fixture_failures}. The reported grid does not run until they do. "
            "This module carries no exemption for any case, because a gate with "
            "an exemption is the defect this study exists to find. budget.json "
            "has been written with the PROTOCOL 8.1 measurement and the 8.2 "
            "projection, and records the gate as closed.")
    tier_name = args.tier or budget["selected_tier"]
    tier = next(t for t in cfg_json["budget"]["ladder"] if t["tier"] == tier_name)
    n_max = args.n_max if args.n_max is not None else tier["N_max"]
    cell_ids = (args.cells.split(",") if args.cells
                else [c["id"] for c in cfg_json["cells"]])
    grid = {cid: (args.programs if args.programs is not None
                  else tier["programs"][cid]) for cid in cell_ids}
    cfg = make_config(n_max, grid_namespace)
    write_manifest(guard, tier_name, cfg, grid)
    print(f"\n[4/6] the reported grid: tier {tier_name}, N_max {n_max}, "
          f"{sum(grid.values())} programs over {len(grid)} cells")

    sink = RowSink(guard.path("trials.csv.gz"), TRIAL_HEADER)
    totals = BlockCounts()
    per_cell_counts: Dict[str, Dict[str, int]] = {}
    mis_rows: List[Dict[str, object]] = []
    dec_rows: List[Dict[str, object]] = []
    time_rows: List[Dict[str, object]] = []
    unres_rows: List[Dict[str, object]] = []
    hor_rows: List[Dict[str, object]] = []
    determinism_block: Optional[Tuple[str, range, bytes]] = None
    limits = cfg_json["budget"]["hard_limits"]

    for cid in cell_ids:
        cell = vgen.CELL_BY_ID[cid]
        n_programs = grid[cid]
        acc = CellAccumulator(cell, n_programs * cfg.trials_per_program,
                              cfg.horizons)
        cell_counts = BlockCounts()
        t0 = time.perf_counter()
        for start in range(0, n_programs, 100):
            block = range(start, min(start + 100, n_programs))
            if determinism_block is None:
                sink.start_retaining()
            cell_counts.add(run_block(cell, block, cfg, sink, acc))
            if determinism_block is None:
                determinism_block = (cid, block, sink.stop_retaining())
            rss = peak_rss_bytes()
            if rss > limits["peak_rss_bytes"]:
                raise SystemExit(f"peak RSS {rss} exceeds the frozen 2 GiB limit; "
                                 f"the run stops and reports what it has")
            written = guard.total_bytes()
            if written > limits["output_bytes"]:
                raise SystemExit(f"output bytes {written} exceed the frozen "
                                 f"200 MiB limit; the run stops and reports")
        totals.add(cell_counts)
        per_cell_counts[cid] = cell_counts.as_dict()
        mis_rows.extend(miscoverage_rows(acc))
        dec_rows.extend(decision_rows(acc, cfg.delta))
        time_rows.extend(decision_time_rows(acc))
        unres_rows.extend(unresolved_rows(acc))
        hor_rows.extend(horizon_rows(acc))
        print(f"  {cid} {cell.law}/{cell.delay}: {n_programs} programs, "
              f"{cell_counts.trials} trials in {time.perf_counter() - t0:.1f}s")
        del acc
    sink.close()

    # ---- 5. determinism ------------------------------------------------------
    print("\n[5/6] determinism: re-running one cell block and comparing bytes")
    cid, block, first_bytes = determinism_block
    replay = RowSink(None, "", discard=True)
    replay.start_retaining()
    run_block(vgen.CELL_BY_ID[cid], block, cfg, replay, None)
    second_bytes = replay.stop_retaining()
    replay.close()
    identical = first_bytes == second_bytes
    print(f"  {cid} programs {block.start}-{block.stop - 1}: "
          f"{len(first_bytes)} bytes, identical = {identical}")
    if not identical:
        raise SystemExit("the run is not deterministic; its outputs are void")

    # ---- 6. the reported tables ---------------------------------------------
    print("\n[6/6] writing the reported tables")
    caption = ("Coverage here is coverage of a BOUNDED ARBITRARY-RUNNING-MEAN "
               "target of a synthetic stream and establishes nothing causal; "
               "NAIVE is INVALID under informative delay and is reported only "
               "to exhibit the failure mode; an unflagged row means no "
               "exceedance was detected at this resolution, never that the "
               "bound holds.")
    write_csv(guard, "miscoverage.csv", mis_rows, "PROTOCOL 9.1. " + caption)
    write_csv(guard, "decisions.csv", dec_rows, "PROTOCOL 9.2. " + caption)
    write_csv(guard, "decision_time.csv", time_rows,
              "PROTOCOL 9.5: decision prefixes in ENROLLED PAIRS, never wall "
              "clock, and never as a paired comparison between constructions.")
    write_csv(guard, "unresolved.csv", unres_rows,
              "PROTOCOL 9.5: resolution quantities at the deciding look, or at "
              "the finalization look for non-deciding trials.")
    write_csv(guard, "horizon_summaries.csv", hor_rows,
              "PROTOCOL 9.6. " + caption)
    control = positive_control(mis_rows)
    compute = {
        "timing": {"wall_clock_seconds": time.time() - started,
                   "started_unix": started},
        "peak_rss_bytes": peak_rss_bytes(),
        "output_bytes": guard.total_bytes(),
        "per_cell": per_cell_counts,
        "total": totals.as_dict(),
        "tier": tier_name,
        "N_max": n_max,
        "determinism_check": {
            "cell": cid, "programs": [block.start, block.stop - 1],
            "bytes_compared": len(first_bytes), "identical": identical,
            "scope": ("one cell block was re-run from its seed coordinates and "
                      "its per-trial records compared byte for byte"),
            "files_that_cannot_be_byte_identical_between_runs": [
                "compute.json (its timing fields)",
                "budget.json (it IS the smoke measurement and the projection)",
                "smoke/timing.json (the same measurement)"],
            "files_that_are_byte_identical_between_runs": [
                "trials.csv.gz", "miscoverage.csv", "decisions.csv",
                "decision_time.csv", "unresolved.csv", "horizon_summaries.csv",
                "manifest.json", "fixtures_report.json"]},
        "positive_control": control,
        "fixtures": None if fixtures is None else
        {"passed": fixtures["passed"], "total": fixtures["total"]},
        "reported_grid": reported,
    }
    guard.write_json("compute.json", compute)
    print(f"\npositive control (PROTOCOL 9.4): "
          f"{'PASSED' if control['passed'] else 'NOT MET'}; "
          f"flagged in {control['flagged_cells'] or 'no cell'}")
    if not control["passed"]:
        print("  " + control["consequence_if_failed"])
    print(f"wrote {guard.total_bytes() / 2**20:.1f} MiB to {guard.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
