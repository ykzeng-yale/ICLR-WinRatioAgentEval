#!/usr/bin/env python3
"""vresource_check.py -- the BALANCED 20-program resource check (root disposition C).

WHY THIS FILE EXISTS.  PROTOCOL 8.1's smoke run split its 20 programs as
``C1`` at ``N_max = 2,000`` and ``C2`` at ``N_max = 1,000``.  That design
CONFOUNDS cell with horizon: the single ratio it produces is
``log(s(C1,2000) / s(C2,1000)) / log 2``, which is the horizon effect MINUS the
cell effect, and it cannot attribute cost to either.  The root's disposition
section C specifies the replacement, and this is it:

    C1 and C2 CROSSED with N_max in {1,000, 2,000}, five programs per group,
    twenty programs in total, for the AMENDED ALL-LOOK runner.

The v1 smoke receipts (``results/live_ab_validation/smoke/timing.json`` and
``budget.json``) are NOT touched, NOT recomputed and NOT replaced.  They are
read here only so that the two designs can be reported side by side, and this
file writes exclusively under ``results/live_ab_validation_v2/resource_check/``.

WHAT "AMENDED ALL-LOOK RUNNER" MEANS HERE.  Root disposition section B, and
coordinator ruling 68, require the v2 runner to

  (1) declare the legal event schedule and its simultaneous-event batching,
  (2) include EVERY required completion-index change through the fixed
      finalization window ``N_max + W``, and
  (3) record BOTH the enrollment prefix AND the elapsed decision time as
      separate quantities.

The v2 runner has not been written.  What is measured here is a faithful
implementation of the two candidate DECLARATIONS on the frozen ``vgen``/``vrun``
arithmetic, so that the coordinator can choose the declaration on the science
rather than have the budget choose it:

  ``v1_reduced``   the deposited runner exactly (``vrun.evaluate_trial``):
                   one look per enrollment prefix plus the finalization look,
                   ``N_max + 1`` looks per trial per construction.
  ``v2_all_ticks`` every tick ``1 .. N_max + W``, all three constructions,
                   simultaneous events batched to the end of their tick.
                   ``N_max + W`` looks per trial per construction.
  ``v2_finest``    ``v2_all_ticks`` plus every distinct intra-tick state: every
                   completion-index change of the two completed-data baselines
                   and every enclosure change of the adapter, read one event at
                   a time in enrollment-position order.

All three record the enrollment prefix and the elapsed tick as separate
columns, so requirement (3)'s byte cost is measured rather than assumed.

MEASURES ONLY.  Seconds, peak resident memory, bytes and counts.  No effect
column is formed into a record on disk and none is read; ``assert_resource_only``
walks the emitted JSON and refuses any key that is not a timing, memory, byte or
count field, exactly as ``vrun.assert_smoke_holds_no_effect_record`` does for the
v1 smoke.  Coordinates are namespace 1 (the resource namespace, whose seeds are
discarded and are never reused in any reported grid) at program indices
``1000-1004``, which are disjoint from the v1 smoke's ``0-9``: separate recorded
resource-only coordinates, as section C requires.

THIS FILE DOES NOT RUN A GRID.  It evaluates twenty programs.  Timing
replication re-measures those same twenty programs; it never draws a
twenty-first.

CPU only: no model call, no API call, no network, no download, no new
dependency.

    .venv/bin/python experiments/live_ab_validation/vresource_check.py --part all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

MODULE_DIR = "experiments/live_ab_validation"


# ---------------------------------------------------------------------------
# PIN THE MEASURED BYTES BEFORE IMPORTING THEM
# ---------------------------------------------------------------------------
# A resource measurement is worthless unless it names the bytes it timed, and
# this working tree is shared with sibling agents who are editing `vgen.py` and
# `vrun.py` right now (coordinator revision 62: parallel agents share one tree
# and observe each other).  Timing a tree that is being edited mid-flight would
# be unreproducible.  So by default this module imports `vband`/`vgen`/`vrun`
# from a read-only snapshot of a named commit, exported with `git archive`, and
# records each file's SHA-256 in the receipt.  `--pin tree` times the live
# working tree instead and says so.
# ---------------------------------------------------------------------------
def _snapshot_root() -> Path:
    root = os.environ.get("VRESOURCE_SNAPSHOT_ROOT")
    return Path(root) if root else Path(tempfile.gettempdir())


def _install_sources() -> Tuple[Path, str, Dict[str, str]]:
    """Put the measured modules on ``sys.path`` and identify their bytes."""
    pin = os.environ.get("VRESOURCE_PIN", "HEAD")
    if pin == "tree":
        src = HERE
        rev = "WORKING TREE (not pinned)"
    else:
        rev = subprocess.run(["git", "rev-parse", pin], cwd=REPO_ROOT,
                             capture_output=True, text=True,
                             check=True).stdout.strip()
        base = _snapshot_root() / f"vresource_pin_{rev[:12]}"
        src = base / MODULE_DIR
        if not (src / "vrun.py").exists():
            base.mkdir(parents=True, exist_ok=True)
            # `src/` comes too: `vband` imports the pinned primitives from it
            archive = subprocess.run(["git", "archive", rev, MODULE_DIR, "src"],
                                     cwd=REPO_ROOT, capture_output=True,
                                     check=True).stdout
            tar = base / "snapshot.tar"
            tar.write_bytes(archive)
            subprocess.run(["tar", "-xf", str(tar), "-C", str(base)],
                           check=True)
            tar.unlink()
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(src.glob("*.py"))
              if p.name in ("vband.py", "vgen.py", "vrun.py",
                            "vlastlook_check.py")}
    hashes["cells.json"] = hashlib.sha256(
        (src / "cells.json").read_bytes()).hexdigest()
    winstats = src.parents[1] / "src" / "winstats.py"
    if winstats.exists():
        hashes["winstats.py"] = hashlib.sha256(
            winstats.read_bytes()).hexdigest()
    if str(src) in sys.path:
        sys.path.remove(str(src))
    sys.path.insert(0, str(src))
    return src, rev, hashes


SOURCE_DIR, SOURCE_REV, SOURCE_HASHES = _install_sources()

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vrun                                                     # noqa: E402

V1_RESULTS = REPO_ROOT / "results" / "live_ab_validation"
OUT_DIR = REPO_ROOT / "results" / "live_ab_validation_v2" / "resource_check"

#: the balanced design of disposition C
CELLS = ("C1", "C2")
HORIZONS = (1000, 2000)
PROGRAMS_PER_GROUP = 5
PROGRAM_BASE = 1000                 # disjoint from the v1 smoke's 0-9
NAMESPACE = vgen.NAMESPACE_SMOKE    # 1: discarded, never reused in a grid

RUNNERS = ("v1_reduced", "v2_all_ticks", "v2_finest")

#: every key permitted to leave a worker.  Anything else is an effect column
#: and aborts the check.
RESOURCE_ONLY_KEYS = {
    # identification of the measured coordinate and of the measured bytes
    "schema", "generated_unix", "runner", "cell", "law", "delay", "N_max",
    "namespace", "program_base", "programs", "inner_reps", "rep", "group",
    "python", "numpy", "platform", "machine", "executable",
    "source_rev", "source_hashes", "vband.py", "vgen.py", "vrun.py",
    "vlastlook_check.py", "cells.json", "winstats.py",
    # time
    "seconds_each", "seconds_median", "seconds_min", "seconds_mean",
    "seconds_per_program", "total_seconds", "total_programs",
    # memory
    "peak_rss_bytes", "baseline_rss_bytes", "rss_delta_bytes",
    # bytes
    "record_bytes_measured_not_written", "bytes_per_program", "output_bytes",
    # counts
    "trials", "enrolled_pairs", "looks", "looks_per_trial",
    "band_evaluations", "enclosure_updates", "enclosure_updates_per_pair",
    # provenance of the measurement itself
    "measures_only", "seeds", "note", "points", "balanced", "design",
}


# ===========================================================================
# 0.  the amended all-look schedules, on the frozen arithmetic
# ===========================================================================
class AmendedSeries:
    """One construction's looks under an amended schedule.

    ``prefix`` is the ENROLLMENT PREFIX and ``tick`` is the ELAPSED time.  They
    are separate arrays because disposition B requires them to be separate
    reported quantities; under v1 they coincided at every look but the
    finalization one, which is exactly why they were conflated.
    """

    __slots__ = ("index", "prefix", "tick", "l_h", "u_h", "l_s", "u_s")

    def __init__(self, index, prefix, tick, l_h, u_h, l_s, u_s):
        self.index, self.prefix, self.tick = index, prefix, tick
        self.l_h, self.u_h, self.l_s, self.u_s = l_h, u_h, l_s, u_s


def _bands(sum_lo, sum_hi, index, radius):
    return vrun._band(np.asarray(sum_lo, dtype=np.float64),
                      np.asarray(sum_hi, dtype=np.float64),
                      np.asarray(index, dtype=np.int64), radius)


def build_series_all_ticks(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                           ) -> Tuple[Dict[str, AmendedSeries], np.ndarray,
                                      np.ndarray, int]:
    """All three constructions at EVERY tick ``1 .. N_max + W``.

    The enrolled prefix is ``min(tick, N_max)``; no pair enrolls after the cap,
    so extending ``vgen.adapter_prefix_sums``' difference array from ``N_max``
    to the finalization tick is the whole change for the adapter.  The
    incremental property of PROTOCOL 8.1 is therefore preserved: the per-pair
    breakpoints are unchanged and only the tick axis is longer.
    """
    n = cfg.n_max
    fin = cfg.finalization_tick
    ticks = np.arange(1, fin + 1, dtype=np.int64)
    prefix = np.minimum(ticks, n)

    sums = vgen.adapter_prefix_sums(draw, fin)
    resolved, revealed, cprefix, _ = vgen.resolution_counts(draw, fin)
    cum_z, cum_d = vgen.prefix_sums_of_scores(draw)
    naive_h = vgen.completed_sums(draw, draw.z, fin)
    naive_s = vgen.completed_sums(draw, draw.dsc, fin)

    out: Dict[str, AmendedSeries] = {}

    idx_a = prefix
    l_h, u_h = _bands(sums.h_lo[1:], sums.h_hi[1:], idx_a, cfg.radius)
    l_s, u_s = _bands(sums.s_lo[1:], sums.s_hi[1:], idx_a, cfg.radius)
    out[vrun.ADAPTER] = AmendedSeries(idx_a, prefix, ticks, l_h, u_h, l_s, u_s)

    idx_k = cprefix[1:]
    k_h, k_s = cum_z[idx_k], cum_d[idx_k]
    l_h, u_h = _bands(k_h, k_h, idx_k, cfg.radius)
    l_s, u_s = _bands(k_s, k_s, idx_k, cfg.radius)
    out[vrun.CPREFIX] = AmendedSeries(idx_k, prefix, ticks, l_h, u_h, l_s, u_s)

    idx_m = resolved[1:]
    m_h, m_s = naive_h[1:], naive_s[1:]
    l_h, u_h = _bands(m_h, m_h, idx_m, cfg.radius)
    l_s, u_s = _bands(m_s, m_s, idx_m, cfg.radius)
    out[vrun.NAIVE] = AmendedSeries(idx_m, prefix, ticks, l_h, u_h, l_s, u_s)

    return out, resolved, revealed, sums.updates


def _finest_baseline_states(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                            ) -> Dict[str, Tuple[np.ndarray, ...]]:
    """Every distinct completion-index state of the two baselines, with its tick."""
    fin = cfg.finalization_tick
    res_tick = draw.resolution_tick
    order = np.argsort(res_tick, kind="stable")
    rt = res_tick[order]
    keep = rt <= fin
    rt, order = rt[keep], order[keep]
    m = np.arange(1, len(rt) + 1, dtype=np.int64)
    cz = np.cumsum(draw.z[order].astype(np.float64))
    cd = np.cumsum(draw.dsc[order].astype(np.float64))
    running_max = np.maximum.accumulate(res_tick)
    k_fin = int(np.searchsorted(running_max, fin, side="right"))
    k = np.arange(1, k_fin + 1, dtype=np.int64)
    cum_z, cum_d = vgen.prefix_sums_of_scores(draw)
    k_tick = running_max[:k_fin] if k_fin else np.zeros(0, dtype=np.int64)
    return {vrun.NAIVE: (m, cz, cd, rt),
            vrun.CPREFIX: (k, cum_z[k], cum_d[k], k_tick)}


def _finest_adapter_states(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                           ) -> Tuple[np.ndarray, ...]:
    """Every distinct enclosure change of the adapter, one event at a time.

    A pair changes its enclosure at most ``vgen.BREAKPOINTS_PER_PAIR`` times.
    Ordering those events by ``(tick, enrollment position, breakpoint)`` and
    accumulating the deltas gives the adapter state after each individual
    event -- the one-event-at-a-time reading, with the same enrollment-position
    tie order the finest baseline reading uses.
    """
    n, fin = cfg.n_max, cfg.finalization_tick
    positions = np.arange(1, draw.n + 1, dtype=np.int64)
    ages = np.stack([np.zeros(draw.n, dtype=np.int64), draw.f,
                     draw.a_narrow, draw.a_collapse, draw.d])
    st = vgen.state_at_age(draw, ages)
    ticks = positions[None, :] + ages                      # (5, n)

    deltas = []
    for values in (st.h_lo, st.h_hi, st.s_lo, st.s_hi):
        v = values.astype(np.int64)
        d = v.copy()
        d[1:] -= v[:-1]
        deltas.append(d)
    changed = (deltas[0] != 0) | (deltas[1] != 0) | (deltas[2] != 0) | (deltas[3] != 0)
    changed[0] = True                                      # enrollment always enters
    live = changed & (ticks <= fin)

    t = ticks[live]
    pos = np.broadcast_to(positions[None, :], ticks.shape)[live]
    bp = np.broadcast_to(np.arange(5, dtype=np.int64)[:, None], ticks.shape)[live]
    key = (t * (draw.n + 1) + pos) * 5 + bp
    order = np.argsort(key, kind="stable")

    t = t[order]
    sums = [np.cumsum(d[live][order].astype(np.float64)) for d in deltas]
    prefix = np.minimum(t, n)
    return (prefix, prefix, t, sums[0], sums[1], sums[2], sums[3])


def build_series_finest(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                        ) -> Tuple[Dict[str, AmendedSeries], np.ndarray,
                                   np.ndarray, int]:
    """``v2_all_ticks`` plus every distinct intra-tick state, per construction."""
    series, resolved, revealed, updates = build_series_all_ticks(draw, cfg)
    fine_b = _finest_baseline_states(draw, cfg)

    for name in (vrun.CPREFIX, vrun.NAIVE):
        idx, s_h, s_s, tick = fine_b[name]
        base = series[name]
        all_idx = np.concatenate([base.index, idx])
        all_tick = np.concatenate([base.tick, tick])
        all_prefix = np.concatenate([base.prefix, np.minimum(tick, cfg.n_max)])
        l_h, u_h = _bands(s_h, s_h, idx, cfg.radius)
        l_s, u_s = _bands(s_s, s_s, idx, cfg.radius)
        order = np.argsort(all_tick * (cfg.n_max + 2) + all_idx, kind="stable")
        series[name] = AmendedSeries(
            all_idx[order], all_prefix[order], all_tick[order],
            np.concatenate([base.l_h, l_h])[order],
            np.concatenate([base.u_h, u_h])[order],
            np.concatenate([base.l_s, l_s])[order],
            np.concatenate([base.u_s, u_s])[order])

    a_idx, a_prefix, a_tick, ah_lo, ah_hi, as_lo, as_hi = \
        _finest_adapter_states(draw, cfg)
    base = series[vrun.ADAPTER]
    l_h, u_h = _bands(ah_lo, ah_hi, a_idx, cfg.radius)
    l_s, u_s = _bands(as_lo, as_hi, a_idx, cfg.radius)
    all_tick = np.concatenate([base.tick, a_tick])
    all_idx = np.concatenate([base.index, a_idx])
    order = np.argsort(all_tick * (cfg.n_max + 2) + all_idx, kind="stable")
    series[vrun.ADAPTER] = AmendedSeries(
        all_idx[order],
        np.concatenate([base.prefix, a_prefix])[order],
        all_tick[order],
        np.concatenate([base.l_h, l_h])[order],
        np.concatenate([base.u_h, u_h])[order],
        np.concatenate([base.l_s, l_s])[order],
        np.concatenate([base.u_s, u_s])[order])
    return series, resolved, revealed, updates


def _fractions_at(draw: vgen.TrialDraw, cfg: vrun.RunConfig, tick: int,
                  prefix: int, cache: Dict[Tuple[int, int], Tuple]) -> Tuple:
    """PROTOCOL 9.5 resolution quantities at an arbitrary (tick, prefix) look."""
    key = (int(tick), int(prefix))
    if key in cache:
        return cache[key]
    prefix = max(int(prefix), 1)
    ages = int(tick) - np.arange(1, prefix + 1, dtype=np.int64)
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
    cache[key] = value
    return value


class AmendedRecord(vrun.TrialRecord):
    """A v1 record plus the two quantities disposition B splits apart."""

    tau_tick: int = 0
    look_tick: int = 0


def evaluate_trial_amended(draw: vgen.TrialDraw, cfg: vrun.RunConfig,
                           finest: bool) -> Tuple[Dict[str, AmendedRecord], int, int]:
    """Every PROTOCOL 9 quantity, on the amended schedule, for one trial."""
    builder = build_series_finest if finest else build_series_all_ticks
    series, resolved, revealed, updates = builder(draw, cfg)
    mu_h, mu_s = draw.cell.mu_h, draw.cell.mu_s
    cache: Dict[Tuple[int, int], Tuple] = {}
    out: Dict[str, AmendedRecord] = {}
    total_looks = 0

    for name in vrun.CONSTRUCTIONS:
        s = series[name]
        total_looks += int(s.index.size)
        rec = AmendedRecord()
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
                rec.decision = vrun.CONFLICT
            elif deploy[i]:
                rec.decision = vrun.DEPLOY
            else:
                rec.decision = vrun.RETAIN_INCUMBENT
            rec.tau = int(s.prefix[i])            # ENROLLMENT PREFIX
            rec.tau_tick = int(s.tick[i])         # ELAPSED DECISION TIME
            rec.decided_at_finalization = bool(
                int(s.tick[i]) == cfg.finalization_tick)
            report = i
        else:
            rec.decision = vrun.NO_DECISION
            rec.tau = int(cfg.n_max)
            rec.tau_tick = int(cfg.finalization_tick)
            report = int(s.index.size) - 1

        (rec.unresolved_fraction, rec.unrevealed_fraction,
         rec.cost_collapsed_fraction, rec.cost_narrowed_fraction,
         rec.n_certified, rec.n_point_resolved) = _fractions_at(
            draw, cfg, int(s.tick[report]), int(s.prefix[report]), cache)
        rec.look_prefix = int(s.prefix[report])
        rec.look_tick = int(s.tick[report])

        first_fire_tick = int(s.tick[int(np.argmax(fired))]) if fired.any() \
            else cfg.finalization_tick + 1
        for h in cfg.horizons:
            at_h = np.searchsorted(s.tick, h, side="right") - 1
            through = s.tick <= h
            rec.horizon[h] = (
                float(s.l_h[at_h]), float(s.u_h[at_h]),
                float(s.l_s[at_h]), float(s.u_s[at_h]),
                float(bool((below_h & through).any())),
                float(bool((below_s & through).any())),
                float(first_fire_tick < h and rec.decision == vrun.DEPLOY),
                float(first_fire_tick < h and rec.decision == vrun.RETAIN_INCUMBENT),
                float(1.0 - resolved[h] / h), float(1.0 - revealed[h] / h))
        out[name] = rec
    return out, total_looks, int(updates)


#: the amended per-trial header: v1's columns plus the two that disposition B
#: requires to be recorded separately.
AMENDED_HEADER = (vrun.TRIAL_HEADER.rstrip("\n") + ",tau_tick,look_tick\n")


def amended_trial_rows(cell, program, trial, records) -> str:
    out = []
    base = vrun.trial_rows(cell, program, trial, records).rstrip("\n").split("\n")
    for line, c in zip(base, vrun.CONSTRUCTIONS):
        r = records[c]
        out.append(f"{line},{r.tau_tick},{r.look_tick}\n")
    return "".join(out)


# ===========================================================================
# 1.  deterministic checks: the amended runner is v1 plus looks, and it sees
#     the root's missed crossing
# ===========================================================================
def check_equivalence(programs: int = 3, n_max: int = 1000) -> Dict[str, object]:
    """On the shared looks the amended runner reproduces v1 exactly.

    The cost factor below is only meaningful if the two runners are doing the
    same arithmetic on different schedules rather than being two unrelated
    programs.  This asserts that: the amended tick schedule restricted to
    ``tick <= N_max`` plus the finalization tick reproduces v1's own band
    arrays bit for bit, for every construction of every trial checked.
    """
    cfg = vrun.make_config(n_max, NAMESPACE)
    fin = cfg.finalization_tick
    checked = 0
    for cell_id in CELLS:
        cell = vgen.CELL_BY_ID[cell_id]
        for program in range(PROGRAM_BASE, PROGRAM_BASE + programs):
            for trial in range(cfg.trials_per_program):
                draw = vgen.draw_trial(cell, program, trial, n_max=n_max,
                                       namespace=NAMESPACE)
                v1_series, _, _, v1_upd = vrun.build_series(draw, cfg)
                am_series, _, _, am_upd = build_series_all_ticks(draw, cfg)
                assert v1_upd == am_upd, "the incremental update count moved"
                for name in vrun.CONSTRUCTIONS:
                    a, b = v1_series[name], am_series[name]
                    keep = np.concatenate([np.arange(n_max), [fin - 1]])
                    for field in ("l_h", "u_h", "l_s", "u_s"):
                        lhs = getattr(a, field)
                        rhs = getattr(b, field)[keep]
                        if not np.array_equal(lhs, rhs):
                            raise SystemExit(
                                f"amended schedule disagrees with v1 on "
                                f"{cell_id}/{program}/{trial}/{name}/{field}")
                    if not np.array_equal(a.index, b.index[keep]):
                        raise SystemExit(f"index disagreement on {name}")
                checked += 1
    return {"trials_checked": checked, "n_max": n_max,
            "identical_on_the_shared_looks": True}


def check_root_witness() -> Dict[str, object]:
    """The amended schedule must SEE the crossing the deposited runner omits.

    Root disposition section B: at horizon 1,000 there is a permitted tick at
    which BOTH baseline lower bounds are +0.0133027164 and BOTH gates cross,
    and the v1 runner never evaluates it.  This is the regression that says the
    thing being costed is the thing that fixes the defect.
    """
    import vlastlook_check as vll                               # noqa: E402

    draw, meta = vll.build_witness(1000)
    cfg = vrun.make_config(1000, vgen.NAMESPACE_FIXTURE)
    v1, _, _ = vrun.evaluate_trial(draw, cfg)
    am, _, _ = evaluate_trial_amended(draw, cfg, finest=False)

    out: Dict[str, object] = {"n_max": 1000, "constructions": {}}
    for name in (vrun.CPREFIX, vrun.NAIVE):
        series, _, _, _ = build_series_all_ticks(draw, cfg)
        s = series[name]
        i = int(np.searchsorted(s.tick, 1010))
        out["constructions"][name] = {
            "v1_decision": vrun.DECISION_LABEL[v1[name].decision],
            "v1_ever_miscover_h": bool(v1[name].ever_miscover_h),
            "amended_decision": vrun.DECISION_LABEL[am[name].decision],
            "amended_ever_miscover_h": bool(am[name].ever_miscover_h),
            "amended_tau_prefix": int(am[name].tau),
            "amended_tau_tick": int(am[name].tau_tick),
            "index_at_tick_1010": int(s.index[i]),
            "L_h_at_tick_1010": float(s.l_h[i]),
            "L_s_at_tick_1010": float(s.l_s[i]),
        }
    out["witness_meta_ok"] = bool(meta is not None)
    return out


# ===========================================================================
# 2.  the measurement worker: one (runner, cell, N_max) group
# ===========================================================================
def _rss() -> int:
    return vrun.peak_rss_bytes()


def measure_group(runner: str, cell_id: str, n_max: int, programs: int,
                  program_base: int, inner: int) -> Dict[str, object]:
    """Time and size one group of the balanced design, ``inner`` times."""
    cell = vgen.CELL_BY_ID[cell_id]
    cfg = vrun.make_config(n_max, NAMESPACE)
    finest = runner == "v2_finest"
    amended = runner != "v1_reduced"
    header = AMENDED_HEADER if amended else vrun.TRIAL_HEADER

    # warm every code path once, OUTSIDE the timed region, so that the first
    # timed repetition is not measuring import-time lazy work
    warm = vgen.draw_trial(cell, program_base, 0, n_max=n_max, namespace=NAMESPACE)
    if amended:
        evaluate_trial_amended(warm, cfg, finest)
    else:
        vrun.evaluate_trial(warm, cfg)
    baseline_rss = _rss()

    seconds_each: List[float] = []
    counts = vrun.BlockCounts()
    record_bytes = 0
    for rep in range(inner):
        sink = vrun.RowSink(None, header, discard=True)
        counts = vrun.BlockCounts()
        t0 = time.perf_counter()
        for program in range(program_base, program_base + programs):
            for trial in range(cfg.trials_per_program):
                draw = vgen.draw_trial(cell, program, trial, n_max=n_max,
                                       namespace=NAMESPACE)
                if amended:
                    records, looks, updates = evaluate_trial_amended(
                        draw, cfg, finest)
                    sink.write(amended_trial_rows(cell, program, trial, records))
                else:
                    records, looks, updates = vrun.evaluate_trial(draw, cfg)
                    looks *= len(vrun.CONSTRUCTIONS)
                    sink.write(vrun.trial_rows(cell, program, trial, records))
                counts.trials += 1
                counts.pairs += cfg.n_max
                counts.looks += looks
                counts.band_evaluations += looks * 2
                counts.enclosure_updates += updates
            counts.programs += 1
        seconds_each.append(time.perf_counter() - t0)
        record_bytes = sink.close()

    seconds = statistics.median(seconds_each)
    return {
        "schema": "live_ab_validation_v2.resource_check.group.1",
        "runner": runner, "cell": cell.id, "law": cell.law,
        "delay": cell.delay, "N_max": n_max, "namespace": NAMESPACE,
        "program_base": program_base, "programs": programs,
        "inner_reps": inner,
        "seconds_each": seconds_each,
        "seconds_median": seconds,
        "seconds_min": min(seconds_each),
        "seconds_mean": statistics.fmean(seconds_each),
        "seconds_per_program": seconds / programs,
        "peak_rss_bytes": _rss(),
        "baseline_rss_bytes": baseline_rss,
        "rss_delta_bytes": _rss() - baseline_rss,
        "record_bytes_measured_not_written": int(record_bytes),
        "bytes_per_program": record_bytes / programs,
        "trials": counts.trials,
        "enrolled_pairs": counts.pairs,
        "looks": counts.looks,
        "looks_per_trial": counts.looks / max(counts.trials, 1),
        "band_evaluations": counts.band_evaluations,
        "enclosure_updates": counts.enclosure_updates,
        "enclosure_updates_per_pair":
            counts.enclosure_updates / max(counts.pairs, 1),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "source_rev": SOURCE_REV,
        "source_hashes": SOURCE_HASHES,
        "measures_only": ["wall_clock_seconds", "peak_rss", "output_bytes",
                          "counts"],
        "seeds": "namespace 1, discarded, never reused in any reported grid",
        "note": ("effect columns are formed only to make the timing "
                 "representative; they are never written and never read, and "
                 "no value other than time, memory, bytes and counts leaves "
                 "this function"),
    }


def assert_resource_only(payload) -> None:
    """Refuse any key that is not a timing, memory, byte or count field."""
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if k not in RESOURCE_ONLY_KEYS:
                    raise SystemExit(
                        f"the resource record carries the key {k!r}, which is "
                        f"not a timing, memory, byte or count field")
                stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)


# ===========================================================================
# 3.  the driver: the balanced design, replicated, one subprocess per group
# ===========================================================================
def _group_order(rep: int) -> List[Tuple[str, int]]:
    """A rotation, so no group sits in a fixed position across repetitions.

    Peak RSS from ``getrusage`` is a process high-water mark and never falls,
    so a group's memory can only be attributed if it owns its process; the
    groups therefore run in subprocesses and the rotation removes any
    systematic warm-up advantage from the time measurements as well.
    """
    groups = [(c, h) for c in CELLS for h in HORIZONS]
    r = rep % len(groups)
    return groups[r:] + groups[:r]


def run_design(reps: int, inner: int, programs: int, verbose: bool = True
               ) -> Dict[str, object]:
    points: List[Dict[str, object]] = []
    t0 = time.perf_counter()
    for rep in range(reps):
        for cell_id, n_max in _group_order(rep):
            for runner in RUNNERS:
                cmd = [sys.executable, str(Path(__file__).resolve()),
                       "--part", "worker", "--runner", runner,
                       "--cell", cell_id, "--n-max", str(n_max),
                       "--programs", str(programs),
                       "--program-base", str(PROGRAM_BASE),
                       "--inner", str(inner)]
                # pin the children to the SAME resolved commit, so that a
                # sibling's commit landing mid-run cannot move the measured
                # bytes underneath the design
                env = dict(os.environ)
                if not SOURCE_REV.startswith("WORKING"):
                    env["VRESOURCE_PIN"] = SOURCE_REV
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      check=True, env=env)
                rec = json.loads(proc.stdout.strip().splitlines()[-1])
                assert_resource_only(rec)
                rec["rep"] = rep
                rec["group"] = f"{cell_id}/{n_max}"
                points.append(rec)
                if verbose:
                    print(f"  rep {rep} {cell_id}/{n_max} {runner:<13} "
                          f"{rec['seconds_per_program'] * 1000:8.3f} ms/program "
                          f"peak {rec['peak_rss_bytes'] / 2**20:6.1f} MiB "
                          f"looks/trial {rec['looks_per_trial']:.0f}")
    return {
        "schema": "live_ab_validation_v2.resource_check.design.1",
        "design": ("balanced 2 x 2: cells C1, C2 crossed with N_max 1,000 and "
                   "2,000, five programs per group, twenty programs in total; "
                   "each group measured in its own subprocess so that peak RSS "
                   "is attributable"),
        "balanced": True,
        "programs": programs,
        "total_programs": programs * 4,
        "inner_reps": inner,
        "namespace": NAMESPACE,
        "program_base": PROGRAM_BASE,
        "points": points,
        "total_seconds": time.perf_counter() - t0,
        "measures_only": ["wall_clock_seconds", "peak_rss", "output_bytes",
                          "counts"],
        "seeds": "namespace 1, discarded, never reused in any reported grid",
        "source_rev": SOURCE_REV,
        "source_hashes": SOURCE_HASHES,
        "generated_unix": time.time(),
    }


# ===========================================================================
# 4.  analysis: marginal effects, the cost factor, the projection
# ===========================================================================
def _ci(values: Sequence[float]) -> Dict[str, float]:
    v = list(values)
    n = len(v)
    mean = statistics.fmean(v)
    sd = statistics.stdev(v) if n > 1 else 0.0
    sem = sd / math.sqrt(n) if n else 0.0
    return {"mean": mean, "sd": sd, "sem": sem, "n": n,
            "lo95": mean - 1.96 * sem, "hi95": mean + 1.96 * sem}


def analyse(design: Dict[str, object]) -> Dict[str, object]:
    pts = design["points"]
    reps = sorted({p["rep"] for p in pts})
    by: Dict[Tuple[str, str, int, int], Dict[str, object]] = {}
    for p in pts:
        by[(p["runner"], p["cell"], p["N_max"], p["rep"])] = p

    out: Dict[str, object] = {"runners": {}}

    for runner in RUNNERS:
        per_group = {}
        for cell_id in CELLS:
            for n_max in HORIZONS:
                s = [by[(runner, cell_id, n_max, r)]["seconds_per_program"]
                     for r in reps]
                rss = [by[(runner, cell_id, n_max, r)]["peak_rss_bytes"]
                       for r in reps]
                dl = [by[(runner, cell_id, n_max, r)]["rss_delta_bytes"]
                      for r in reps]
                any_pt = by[(runner, cell_id, n_max, reps[0])]
                per_group[f"{cell_id}/{n_max}"] = {
                    "seconds_per_program": _ci(s),
                    "peak_rss_bytes": _ci([float(x) for x in rss]),
                    "rss_delta_bytes": _ci([float(x) for x in dl]),
                    "looks_per_trial": any_pt["looks_per_trial"],
                    "bytes_per_program": any_pt["bytes_per_program"],
                    "enclosure_updates_per_pair":
                        any_pt["enclosure_updates_per_pair"],
                }

        # ---- the 2 x 2 marginal effects, per repetition, on log seconds ----
        cell_eff, hor_eff, inter, beta, confounded = [], [], [], [], []
        for r in reps:
            y = {(c, h): math.log(by[(runner, c, h, r)]["seconds_per_program"])
                 for c in CELLS for h in HORIZONS}
            ce = 0.5 * ((y[("C2", 1000)] - y[("C1", 1000)])
                        + (y[("C2", 2000)] - y[("C1", 2000)]))
            he = 0.5 * ((y[("C1", 2000)] - y[("C1", 1000)])
                        + (y[("C2", 2000)] - y[("C2", 1000)]))
            it = ((y[("C2", 2000)] - y[("C2", 1000)])
                  - (y[("C1", 2000)] - y[("C1", 1000)]))
            cell_eff.append(ce)
            hor_eff.append(he)
            inter.append(it)
            beta.append(he / math.log(2.0))
            # exactly the v1 smoke contrast, computed from balanced data
            confounded.append((y[("C1", 2000)] - y[("C2", 1000)]) / math.log(2.0))

        out["runners"][runner] = {
            "per_group": per_group,
            "marginal_effects_log_seconds_per_program": {
                "cell_C2_minus_C1": _ci(cell_eff),
                "horizon_2000_minus_1000": _ci(hor_eff),
                "interaction": _ci(inter),
                "cell_multiplicative_factor": math.exp(statistics.fmean(cell_eff)),
                "horizon_multiplicative_factor": math.exp(statistics.fmean(hor_eff)),
            },
            "beta_balanced": _ci(beta),
            "beta_confounded_v1_style": _ci(confounded),
        }

    # ---- the paired cost factor, amended over v1, on the same coordinates --
    factors: Dict[str, object] = {}
    for runner in ("v2_all_ticks", "v2_finest"):
        overall, per_h, per_c = [], {h: [] for h in HORIZONS}, {c: [] for c in CELLS}
        for r in reps:
            for c in CELLS:
                for h in HORIZONS:
                    f = math.log(by[(runner, c, h, r)]["seconds_per_program"]
                                 / by[("v1_reduced", c, h, r)]["seconds_per_program"])
                    overall.append(f)
                    per_h[h].append(f)
                    per_c[c].append(f)
        ov = _ci(overall)
        factors[runner] = {
            "log_factor": ov,
            "geometric_mean_factor": math.exp(ov["mean"]),
            "factor_lo95": math.exp(ov["lo95"]),
            "factor_hi95": math.exp(ov["hi95"]),
            "by_horizon": {str(h): {"geometric_mean_factor":
                                    math.exp(_ci(per_h[h])["mean"]),
                                    "lo95": math.exp(_ci(per_h[h])["lo95"]),
                                    "hi95": math.exp(_ci(per_h[h])["hi95"])}
                           for h in HORIZONS},
            "by_cell": {c: {"geometric_mean_factor":
                            math.exp(_ci(per_c[c])["mean"]),
                            "lo95": math.exp(_ci(per_c[c])["lo95"]),
                            "hi95": math.exp(_ci(per_c[c])["hi95"])}
                        for c in CELLS},
            "look_factor_per_trial": {
                f"{c}/{h}": (by[(runner, c, h, reps[0])]["looks_per_trial"]
                             / by[("v1_reduced", c, h, reps[0])]["looks_per_trial"])
                for c in CELLS for h in HORIZONS},
        }
    out["cost_factor_amended_over_v1"] = factors

    # ---- the projection against PROTOCOL 8.2's caps ------------------------
    cfg_json = json.loads((SOURCE_DIR / "cells.json").read_text())
    limits = cfg_json["budget"]["hard_limits"]
    projection = {"hard_limits": limits, "runners": {}}
    for runner in RUNNERS:
        blk = out["runners"][runner]
        s2000 = statistics.fmean(
            [blk["per_group"][f"{c}/2000"]["seconds_per_program"]["mean"]
             for c in CELLS])
        s2000_sem = math.sqrt(sum(
            blk["per_group"][f"{c}/2000"]["seconds_per_program"]["sem"] ** 2
            for c in CELLS)) / len(CELLS)
        s2000_worst = max(
            blk["per_group"][f"{c}/2000"]["seconds_per_program"]["mean"]
            for c in CELLS)
        beta = blk["beta_balanced"]["mean"]
        bpp = statistics.fmean(
            [blk["per_group"][f"{c}/{h}"]["bytes_per_program"]
             for c in CELLS for h in HORIZONS])
        peak = max(blk["per_group"][f"{c}/{h}"]["peak_rss_bytes"]["mean"]
                   for c in CELLS for h in HORIZONS)
        ladder = []
        for tier in cfg_json["budget"]["ladder"]:
            total, n_max = tier["programs_total"], tier["N_max"]
            scale = (n_max / 2000.0) ** beta
            sec = s2000 * total * scale
            sec_hi = (s2000 + 1.96 * s2000_sem) * total * scale
            sec_worst = s2000_worst * total * scale
            ob = bpp * total
            ladder.append({
                "tier": tier["tier"], "programs_total": total, "N_max": n_max,
                "seconds_projected": sec,
                "seconds_projected_hi95": sec_hi,
                "seconds_projected_worst_cell": sec_worst,
                "bytes_projected": ob,
                "peak_rss_projected": peak,
                "within_seconds": sec_worst <= limits["seconds"],
                "within_bytes": ob <= limits["output_bytes"],
                "within_peak_rss": peak <= limits["peak_rss_bytes"],
            })
            ladder[-1]["admissible"] = bool(ladder[-1]["within_seconds"]
                                            and ladder[-1]["within_bytes"]
                                            and ladder[-1]["within_peak_rss"])
        projection["runners"][runner] = {
            "s_per_program_2000_balanced": s2000,
            "s_per_program_2000_sem": s2000_sem,
            "s_per_program_2000_worst_cell": s2000_worst,
            "beta_balanced": beta,
            "bytes_per_program": bpp,
            "peak_rss_bytes": peak,
            "ladder": ladder,
            "highest_admissible_tier": next(
                (e["tier"] for e in ladder if e["admissible"]), None),
            "breaches_a_cap": not any(e["admissible"] for e in ladder),
        }
    out["projection"] = projection
    return out


# ===========================================================================
# 5.  reporting
# ===========================================================================
def print_report(design: Dict[str, object], an: Dict[str, object]) -> None:
    p = print
    p("")
    p("=" * 78)
    p("BALANCED RESOURCE CHECK -- disposition C")
    p("=" * 78)
    p(f"measured bytes: {SOURCE_REV}")
    for name, h in SOURCE_HASHES.items():
        p(f"                {name:<22} sha256 {h}")
    p(f"design        : {design['design']}")
    p(f"programs      : {design['total_programs']} "
      f"(namespace {design['namespace']}, program indices "
      f"{design['program_base']}-{design['program_base'] + design['programs'] - 1})")
    p(f"repetitions   : {len(set(x['rep'] for x in design['points']))} outer "
      f"(one subprocess each) x {design['inner_reps']} inner")
    p(f"harness time  : {design['total_seconds']:.1f} s")

    for runner in RUNNERS:
        blk = an["runners"][runner]
        p("")
        p(f"--- {runner} " + "-" * (74 - len(runner)))
        p(f"{'group':<12} {'ms/program':>22} {'peak RSS MiB':>14} "
          f"{'looks/trial':>12} {'bytes/prog':>11}")
        for c in CELLS:
            for h in HORIZONS:
                g = blk["per_group"][f"{c}/{h}"]
                s = g["seconds_per_program"]
                p(f"{c + '/' + str(h):<12} "
                  f"{s['mean'] * 1000:10.4f} +- {s['sem'] * 1000:7.4f} "
                  f"{g['peak_rss_bytes']['mean'] / 2**20:14.1f} "
                  f"{g['looks_per_trial']:12.0f} "
                  f"{g['bytes_per_program']:11.1f}")
        me = blk["marginal_effects_log_seconds_per_program"]
        p(f"  marginal effect of CELL    (C2 - C1, log s): "
          f"{me['cell_C2_minus_C1']['mean']:+.4f} "
          f"+- {me['cell_C2_minus_C1']['sem']:.4f}   "
          f"(x{me['cell_multiplicative_factor']:.4f})")
        p(f"  marginal effect of HORIZON (2000 - 1000)   : "
          f"{me['horizon_2000_minus_1000']['mean']:+.4f} "
          f"+- {me['horizon_2000_minus_1000']['sem']:.4f}   "
          f"(x{me['horizon_multiplicative_factor']:.4f})")
        p(f"  interaction                                : "
          f"{me['interaction']['mean']:+.4f} +- {me['interaction']['sem']:.4f}")
        b = blk["beta_balanced"]
        cf = blk["beta_confounded_v1_style"]
        p(f"  beta, BALANCED (horizon effect / log 2)    : "
          f"{b['mean']:.4f} +- {b['sem']:.4f}   [{b['lo95']:.4f}, {b['hi95']:.4f}]")
        p(f"  beta, v1-STYLE CONFOUNDED contrast         : "
          f"{cf['mean']:.4f} +- {cf['sem']:.4f}  "
          f"(= horizon effect - cell effect, over log 2)")

    p("")
    p("--- cost of the corrected all-look schedule, paired on the same "
      "coordinates ---")
    for runner, f in an["cost_factor_amended_over_v1"].items():
        p(f"  {runner:<13} x{f['geometric_mean_factor']:.3f}  "
          f"95% CI [{f['factor_lo95']:.3f}, {f['factor_hi95']:.3f}]   "
          f"(geometric mean over 4 groups x reps)")
        for h in HORIZONS:
            e = f["by_horizon"][str(h)]
            p(f"      N_max={h:<5} x{e['geometric_mean_factor']:.3f} "
              f"[{e['lo95']:.3f}, {e['hi95']:.3f}]")
        p(f"      looks per trial vs v1: "
          + ", ".join(f"{k} x{v:.2f}" for k, v in
                      f["look_factor_per_trial"].items()))

    p("")
    p("--- projection against PROTOCOL 8.2's caps "
      "(5,400 s / 2.0 GiB / 200 MiB) ---")
    for runner in RUNNERS:
        pr = an["projection"]["runners"][runner]
        p(f"  {runner}: s/program@2000 = {pr['s_per_program_2000_balanced'] * 1000:.4f} ms"
          f"  beta = {pr['beta_balanced']:.4f}")
        for e in pr["ladder"]:
            p(f"      {e['tier']}  {e['programs_total']:>6} programs "
              f"N_max {e['N_max']:>5}  "
              f"{e['seconds_projected']:9.1f} s "
              f"(worst cell {e['seconds_projected_worst_cell']:9.1f} s)  "
              f"{e['bytes_projected'] / 2**20:7.2f} MiB  "
              f"{e['peak_rss_projected'] / 2**20:6.1f} MiB  "
              f"{'OK' if e['admissible'] else 'BREACH'}")
        p(f"      highest admissible tier: {pr['highest_admissible_tier']}")
    p("")


# ===========================================================================
# 6.  entry point
# ===========================================================================
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", default="all",
                    choices=("all", "check", "measure", "worker"))
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--inner", type=int, default=20)
    ap.add_argument("--programs", type=int, default=PROGRAMS_PER_GROUP)
    ap.add_argument("--runner", default="v1_reduced", choices=RUNNERS)
    ap.add_argument("--cell", default="C1")
    ap.add_argument("--n-max", type=int, default=2000)
    ap.add_argument("--program-base", type=int, default=PROGRAM_BASE)
    ap.add_argument("--pin", default=os.environ.get("VRESOURCE_PIN", "HEAD"),
                    help="the commit whose bytes are measured, or 'tree' for "
                         "the live working tree (default: HEAD)")
    ap.add_argument("--write", action="store_true",
                    help=f"deposit the receipt under {OUT_DIR}")
    args = ap.parse_args(argv)

    if args.pin != os.environ.get("VRESOURCE_PIN", "HEAD"):
        # the pin has to be in force BEFORE vgen/vrun are imported
        env = dict(os.environ, VRESOURCE_PIN=args.pin)
        os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve())]
                  + list(argv if argv is not None else sys.argv[1:]), env)

    if args.part == "worker":
        rec = measure_group(args.runner, args.cell, args.n_max, args.programs,
                            args.program_base, args.inner)
        assert_resource_only(rec)
        print(json.dumps(rec))
        return 0

    if args.part in ("all", "check"):
        print("deterministic checks (no timing, no grid)")
        eq = check_equivalence()
        print(f"  amended == v1 on the shared looks: "
              f"{eq['trials_checked']} trials, {eq['identical_on_the_shared_looks']}")
        wit = check_root_witness()
        for name, blk in wit["constructions"].items():
            print(f"  root witness {name}: v1 {blk['v1_decision']} / "
                  f"miscover {blk['v1_ever_miscover_h']}  ->  amended "
                  f"{blk['amended_decision']} at prefix {blk['amended_tau_prefix']}, "
                  f"tick {blk['amended_tau_tick']} / miscover "
                  f"{blk['amended_ever_miscover_h']}")
            print(f"      index at tick 1010 = {blk['index_at_tick_1010']}, "
                  f"L_h = {blk['L_h_at_tick_1010']:.10f}, "
                  f"L_s = {blk['L_s_at_tick_1010']:.10f}")
        if args.part == "check":
            return 0

    print("")
    print(f"balanced 20-program measurement: {args.reps} outer repetitions x "
          f"{args.inner} inner, 3 runners, 4 groups")
    design = run_design(args.reps, args.inner, args.programs)
    an = analyse(design)
    print_report(design, an)

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        assert_resource_only(design)
        (OUT_DIR / "balanced_timing.json").write_text(
            json.dumps(design, indent=2, sort_keys=True) + "\n")
        (OUT_DIR / "balanced_analysis.json").write_text(
            json.dumps(an, indent=2, sort_keys=True) + "\n")
        print(f"wrote {OUT_DIR / 'balanced_timing.json'}")
        print(f"wrote {OUT_DIR / 'balanced_analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
