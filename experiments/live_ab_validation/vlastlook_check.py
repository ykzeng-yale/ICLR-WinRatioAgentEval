#!/usr/bin/env python3
"""vlastlook_check.py -- verify or refute the root's last-look witness (ruling 56).

The root's `reviews/arxiv_cpu_prereg_statistics_review.md` section 2 asserts that
PROTOCOL 7.1's last-look reduction -- keep only the final look at each enrolled
prefix -- does NOT preserve all-look miscoverage or the decision prefix for the
completed-data baselines `CPREFIX` and `NAIVE`, and supplies an exact witness
inside the `T4` horizon in the `L1/N` cell.  This script:

  A. rebuilds that witness pair for pair at `T4` (`N_max = 1,000`) and reports
     every number it turns on;
  B. rebuilds the same construction at `T1` (`N_max = 2,000`), which is the
     horizon the reported grid actually ran at;
  C. checks the reduction's validity for the `ADAPTER` -- the object under test
     -- both by its monotonicity argument and by brute force over every drain
     tick of a bounded sample of real grid trials;
  D. sweeps the ENTIRE frozen reported grid and counts, exactly, how many
     reported events the reduction misses, under two readings of the
     all-triggers rule, and recomputes every affected Wilson flag including the
     precommitted positive control.

It writes NOTHING.  Every number goes to stdout.  CPU only; no model call, no
API call, no network, no new dependency.  It imports the frozen `vgen`/`vrun`
and reuses their own band and event code, so the "reduced" column it prints is
the frozen run's own arithmetic and is checked against the deposited CSVs.

    .venv/bin/python experiments/live_ab_validation/vlastlook_check.py --part all
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vrun                                                     # noqa: E402

REPO_ROOT = HERE.parents[1]
RESULTS = REPO_ROOT / "results" / "live_ab_validation"

BASELINES = (vrun.CPREFIX, vrun.NAIVE)
GATES = ("hierarchy", "success")


# ===========================================================================
# helpers
# ===========================================================================
def make_draw(cell: vgen.CellSpec, atoms: Sequence[str], d, f,
              cand_first) -> vgen.TrialDraw:
    """A hand-built trial, post-processed exactly as ``vgen.draw_trial`` does.

    Only the five drawn arrays are supplied by hand; everything downstream
    (`s_rev`, the cost columns and the two cost-tier thresholds) is computed by
    the frozen code path, so the witness cannot be built out of a shortcut.
    """
    atom = np.array([vgen.ATOM_ORDER.index(a) for a in atoms], dtype=np.int8)
    d = np.asarray(d, dtype=np.int64)
    f = np.asarray(f, dtype=np.int64)
    cand_first = np.asarray(cand_first, dtype=bool)
    z, dsc = vgen.ATOM_Z[atom], vgen.ATOM_D[atom]
    s_c, s_i = vgen.ATOM_SC[atom], vgen.ATOM_SI[atom]
    c_c, c_i = vgen.ATOM_CC[atom], vgen.ATOM_CI[atom]
    s_rev = np.where(cand_first, s_c, s_i).astype(np.int8)
    c_rev = np.where(cand_first, c_c, c_i)
    c_pend = np.where(cand_first, c_i, c_c)
    code = (c_rev > 20.0).astype(np.int8) * 2 + (c_pend > 20.0).astype(np.int8)
    combo = np.where(s_rev == 1, vgen._COMBO_CODE[code], -1)
    safe = np.maximum(combo, 0)
    a_narrow = np.where(combo >= 0, vgen.THRESH_NARROW[safe, d], d)
    a_collapse = np.where(combo >= 0, vgen.THRESH_COLLAPSE[safe, d], d)
    return vgen.TrialDraw(
        cell=cell, namespace=vgen.NAMESPACE_FIXTURE, program_index=0,
        trial_index=0, n=len(atom), atom=atom, z=z, dsc=dsc, d=d, f=f,
        cand_first=cand_first, s_rev=s_rev, c_rev=c_rev, c_pend=c_pend,
        a_narrow=np.clip(a_narrow, f, d), a_collapse=np.clip(a_collapse, f, d))


def band_events(idx: np.ndarray, sum_h: np.ndarray, sum_s: np.ndarray,
                cfg: vrun.RunConfig, mu_h: float, mu_s: float) -> Dict[str, np.ndarray]:
    """The frozen band and every PROTOCOL 9.1/9.2 event at a set of looks."""
    lo_h, hi_h = vrun._band(sum_h, sum_h, idx, cfg.radius)
    lo_s, hi_s = vrun._band(sum_s, sum_s, idx, cfg.radius)
    elig = idx >= cfg.n_min
    below_h, above_h = mu_h < lo_h, mu_h > hi_h
    below_s, above_s = mu_s < lo_s, mu_s > hi_s
    deploy = elig & (lo_h > 0.0) & (lo_s > -cfg.delta)
    harm = elig & (hi_h < 0.0)
    return dict(lo_h=lo_h, hi_h=hi_h, lo_s=lo_s, hi_s=hi_s, elig=elig,
                below_h=below_h, above_h=above_h, below_s=below_s,
                above_s=above_s, deploy=deploy, harm=harm,
                fired=deploy | harm)


def drain_states(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                 ) -> Tuple[np.ndarray, Dict[str, Tuple[np.ndarray, ...]]]:
    """Baseline index and score sums at every drain tick the reduction skips.

    Ticks ``N_max+1 .. N_max+W-1``: the enrolled prefix is pinned at ``N_max``
    there, so the reduction takes no look at all between the cap and the
    finalization look, while completions keep arriving.
    """
    n, fin = cfg.n_max, cfg.finalization_tick
    ticks = np.arange(n + 1, fin, dtype=np.int64)
    res_tick = draw.resolution_tick
    order = np.argsort(res_tick, kind="stable")
    rt_sorted = res_tick[order]
    cz = np.concatenate([[0.0], np.cumsum(draw.z[order].astype(np.float64))])
    cd = np.concatenate([[0.0], np.cumsum(draw.dsc[order].astype(np.float64))])
    m = np.searchsorted(rt_sorted, ticks, side="right")
    k = np.searchsorted(np.maximum.accumulate(res_tick), ticks, side="right")
    cum_z, cum_d = vgen.prefix_sums_of_scores(draw)
    return ticks, {vrun.NAIVE: (m, cz[m], cd[m]),
                   vrun.CPREFIX: (k, cum_z[k], cum_d[k])}


def finest_states(draw: vgen.TrialDraw, cfg: vrun.RunConfig
                  ) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Every distinct completion-index state of the two baselines, with its tick.

    This is the all-triggers rule read one event at a time rather than batched
    per tick.  For ``CPREFIX`` the state is a function of ``k`` alone, so this
    set is exactly the union over every admissible tie order.  For ``NAIVE`` the
    partial sums depend on the order within a tick; the enrollment-position tie
    order is used, which is one admissible schedule, not a bound over all of
    them.
    """
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
    # the tick at which prefix k becomes complete
    k_tick = running_max[:k_fin] if k_fin else np.zeros(0, dtype=np.int64)
    return {vrun.NAIVE: (m, cz, cd, rt),
            vrun.CPREFIX: (k, cum_z[k], cum_d[k], k_tick)}


# ===========================================================================
# A / B -- the witness
# ===========================================================================
def build_witness(n_max: int) -> Tuple[vgen.TrialDraw, Dict[str, object]]:
    """The root's construction, scaled to the horizon.

    Structure (the root's own): a long block of exact ties that resolves
    instantly, then a `+1` block that completes at an early drain tick, then a
    `-1` block of the same size, then the rest -- all four blocks with
    ``f = d`` (first reveal == full reveal), which has positive probability
    under PROTOCOL 4.3.  The `+1` block alone carries the baselines' mean above
    their radius; the `-1` block cancels it again before the finalization look.
    """
    cell = next(c for c in vgen.CELLS if c.id == ("C1"))
    fin = n_max + vgen.DRAIN_W
    t_plus, t_minus = n_max + 10, n_max + 100        # the two drain ticks used
    if n_max == 1000:                                # the root's own witness
        blocks = [(1, 500, "BB0", 0),                # (lo, hi, atom, resolve tick)
                  (501, 600, "C>I", t_plus),
                  (601, 700, "I>C", t_minus),
                  (701, 1000, "BB0", fin)]
    elif n_max == 2000:                              # the horizon that RAN
        blocks = [(1, 1400, "BB0", 0),
                  (1401, 1600, "C>I", t_plus),
                  (1601, 1800, "I>C", t_minus),
                  (1801, 2000, "BB0", fin)]
    else:                                            # pragma: no cover
        raise ValueError(n_max)

    atoms: List[str] = [""] * n_max
    d = np.zeros(n_max, dtype=np.int64)
    for lo, hi, atom, tick in blocks:
        for j in range(lo, hi + 1):
            atoms[j - 1] = atom
            d[j - 1] = 0 if tick == 0 else tick - j
    f = d.copy()                                     # first reveal == full reveal
    cand_first = np.zeros(n_max, dtype=bool)
    cand_first[::2] = True                           # the coin is free here
    draw = make_draw(cell, atoms, d, f, cand_first)

    short_ok = bool(np.all((d[d < vgen.LONG_LOW] >= vgen.SHORT_LOW)
                           & (d[d < vgen.LONG_LOW] <= vgen.SHORT_HIGH)))
    long_d = d[d >= vgen.LONG_LOW]
    long_ok = bool(np.all((long_d >= vgen.LONG_LOW) & (long_d <= vgen.LONG_HIGH)))
    meta = {
        "cell": cell.id, "law": cell.law, "delay": cell.delay,
        "n_max": n_max, "finalization_tick": fin,
        "blocks": [(lo, hi, atom, tick) for lo, hi, atom, tick in blocks],
        "offsets_used": [int(long_d.min()), int(long_d.max())],
        "every_short_offset_in_support": short_ok,
        "every_long_offset_in_support": long_ok,
        "weights_all_positive": all(
            vgen.LAW_WEIGHTS[cell.law][a] > 0 for _, _, a, _ in blocks),
        "true_mu_h": cell.mu_h, "true_mu_s": cell.mu_s,
        "realized_sum_z": int(draw.z.sum()), "realized_sum_d": int(draw.dsc.sum()),
    }
    return draw, meta


def report_witness(n_max: int) -> Dict[str, object]:
    draw, meta = build_witness(n_max)
    cfg = vrun.make_config(n_max=n_max, namespace=vgen.NAMESPACE_FIXTURE)
    cell = draw.cell
    print(f"\n{'=' * 78}\nWITNESS at N_max = {n_max:,} "
          f"(finalization tick {cfg.finalization_tick:,}), cell {cell.id} "
          f"= {cell.law}/{cell.delay}\n{'=' * 78}")
    print(f"  blocks (enrollment positions -> atom -> full-reveal tick):")
    for lo, hi, atom, tick in meta["blocks"]:
        print(f"    {lo:>5,}-{hi:<5,}  {atom:<4}  Z={vgen.ATOM_TABLE[atom][4]:+d} "
              f"D={vgen.ATOM_TABLE[atom][5]:+d}  resolves at tick "
              f"{('enrollment' if tick == 0 else f'{tick:,}')}")
    print(f"  LONG offsets used: {meta['offsets_used'][0]}-{meta['offsets_used'][1]} "
          f"(support {vgen.LONG_LOW}-{vgen.LONG_HIGH}): "
          f"{'INSIDE' if meta['every_long_offset_in_support'] else 'OUTSIDE'}")
    print(f"  all four atoms carry positive weight under {cell.law}: "
          f"{meta['weights_all_positive']}")
    print(f"  realized sums over the whole trial: sum Z = {meta['realized_sum_z']}, "
          f"sum D = {meta['realized_sum_d']}  (truth mu_h = {cell.mu_h:+.4f}, "
          f"mu_s = {cell.mu_s:+.4f})")

    # ---- the reduction, exactly as the frozen runner takes it ----------
    recs, _, _ = vrun.evaluate_trial(draw, cfg)
    print("\n  [1] THE REDUCED SCHEDULE (what the frozen runner evaluates: one look at"
          "\n      every enrolled prefix 1..N_max, plus the finalization look)")
    for name in vrun.CONSTRUCTIONS:
        r = recs[name]
        print(f"      {name:<8} decision={vrun.DECISION_LABEL[r.decision]:<16} "
              f"ever_miscover_h={r.ever_miscover_h!s:<5} "
              f"ever_miscover_s={r.ever_miscover_s!s:<5}")

    # ---- the drain looks the reduction skips ---------------------------
    ticks, states = drain_states(draw, cfg)
    print("\n  [2] THE DRAIN LOOKS THE REDUCTION SKIPS "
          f"(ticks {ticks[0]:,}..{ticks[-1]:,}; the enrolled prefix is pinned at"
          f" {cfg.n_max:,})")
    out: Dict[str, object] = {"meta": meta, "reduced": {}, "drain": {}}
    for name in BASELINES:
        idx, sh, ss = states[name]
        ev = band_events(idx, sh, ss, cfg, cell.mu_h, cell.mu_s)
        hit = np.flatnonzero(ev["fired"] | ev["below_h"] | ev["above_h"]
                             | ev["below_s"] | ev["above_s"])
        r = recs[name]
        out["reduced"][name] = {
            "decision": vrun.DECISION_LABEL[r.decision],
            "ever_miscover_h": r.ever_miscover_h,
            "ever_miscover_s": r.ever_miscover_s}
        if not len(hit):
            print(f"      {name:<8} nothing fires and nothing miscovers in the drain")
            out["drain"][name] = None
            continue
        i = int(hit[0])
        print(f"      {name:<8} first event at tick {int(ticks[i]):,}: "
              f"index={int(idx[i]):,}  mean_h={sh[i] / idx[i]:.12f}  "
              f"r(index)={cfg.radius[int(idx[i])]:.12f}")
        print(f"               L_h={ev['lo_h'][i]:+.12f}  U_h={ev['hi_h'][i]:+.12f}  "
              f"L_s={ev['lo_s'][i]:+.12f}  U_s={ev['hi_s'][i]:+.12f}")
        print(f"               DEPLOY={bool(ev['deploy'][i])}  "
              f"RETAIN={bool(ev['harm'][i])}  "
              f"miscover_h={bool(ev['below_h'][i] or ev['above_h'][i])}  "
              f"miscover_s={bool(ev['below_s'][i] or ev['above_s'][i])}")
        print(f"               drain ticks with a decision: "
              f"{int(ev['fired'].sum())} of {len(ticks)};  "
              f"with hierarchy miscoverage: "
              f"{int((ev['below_h'] | ev['above_h']).sum())}")
        out["drain"][name] = {
            "tick": int(ticks[i]), "index": int(idx[i]),
            "mean_h": float(sh[i] / idx[i]),
            "radius": float(cfg.radius[int(idx[i])]),
            "L_h": float(ev["lo_h"][i]), "L_s": float(ev["lo_s"][i]),
            "deploy": bool(ev["deploy"][i]),
            "miscover_h": bool(ev["below_h"][i] or ev["above_h"][i]),
            "miscover_s": bool(ev["below_s"][i] or ev["above_s"][i])}

    # ---- the adapter over the same drain --------------------------------
    print("\n  [3] THE ADAPTER over the same drain ticks (the object under test)")
    ad = adapter_drain_scan(draw, cfg)
    print(f"      monotone sums over the drain: {ad['monotone']}   "
          f"events at a drain tick absent from the finalization look: "
          f"{ad['missed_events']}")
    print(f"      L_h at the first drain tick {ad['first_L_h']:+.12f} -> at "
          f"finalization {ad['final_L_h']:+.12f};  U_h {ad['first_U_h']:+.12f} -> "
          f"{ad['final_U_h']:+.12f}")
    out["adapter"] = ad
    return out


# ===========================================================================
# C -- the adapter
# ===========================================================================
def adapter_drain_scan(draw: vgen.TrialDraw, cfg: vrun.RunConfig) -> Dict[str, object]:
    """Brute force over every drain tick: is the finalization look dominant?

    At a fixed prefix the adapter's denominator and radius are frozen and each
    enclosure can only shrink, so the last look at that prefix must dominate.
    This evaluates the claim rather than assuming it: every tick from the cap to
    the finalization look, the full enclosure sums recomputed from the state.
    """
    n, fin = cfg.n_max, cfg.finalization_tick
    ticks = np.arange(n, fin + 1, dtype=np.int64)
    positions = np.arange(1, draw.n + 1, dtype=np.int64)
    ages = ticks[:, None] - positions[None, :]
    st = vgen.state_at_age(draw, ages)
    h_lo = st.h_lo.sum(axis=1, dtype=np.int64).astype(np.float64)
    h_hi = st.h_hi.sum(axis=1, dtype=np.int64).astype(np.float64)
    s_lo = st.s_lo.sum(axis=1, dtype=np.int64).astype(np.float64)
    s_hi = st.s_hi.sum(axis=1, dtype=np.int64).astype(np.float64)
    monotone = bool(np.all(np.diff(h_lo) >= 0) and np.all(np.diff(h_hi) <= 0)
                    and np.all(np.diff(s_lo) >= 0) and np.all(np.diff(s_hi) <= 0))
    idx = np.full(len(ticks), n, dtype=np.int64)
    lo_h, hi_h = vrun._band(h_lo, h_hi, idx, cfg.radius)
    lo_s, hi_s = vrun._band(s_lo, s_hi, idx, cfg.radius)
    mu_h, mu_s = draw.cell.mu_h, draw.cell.mu_s
    elig = idx >= cfg.n_min
    ev = (mu_h < lo_h) | (mu_h > hi_h) | (mu_s < lo_s) | (mu_s > hi_s) \
        | (elig & (lo_h > 0.0) & (lo_s > -cfg.delta)) | (elig & (hi_h < 0.0))
    missed = int(np.count_nonzero(ev[:-1] & ~ev[-1]))
    return {"monotone": monotone, "missed_events": missed,
            "first_L_h": float(lo_h[0]), "final_L_h": float(lo_h[-1]),
            "first_U_h": float(hi_h[0]), "final_U_h": float(hi_h[-1])}


def adapter_sample_check(programs: int, cfg: vrun.RunConfig) -> Dict[str, object]:
    """The same brute force over a bounded sample of REAL grid trials."""
    print(f"\n{'=' * 78}\nC. THE ADAPTER: brute force over every drain tick of "
          f"{programs} programs x 4 trials x 8 cells\n{'=' * 78}")
    tot = {"trials": 0, "nonmonotone": 0, "missed": 0}
    t0 = time.time()
    for cell in vgen.CELLS:
        cell_bad = 0
        for p in range(programs):
            for t in range(vgen.TRIALS_PER_PROGRAM):
                draw = vgen.draw_trial(cell, p, t, n_max=cfg.n_max,
                                       namespace=vgen.NAMESPACE_GRID)
                r = adapter_drain_scan(draw, cfg)
                tot["trials"] += 1
                if not r["monotone"]:
                    tot["nonmonotone"] += 1
                    cell_bad += 1
                tot["missed"] += int(r["missed_events"])
        print(f"  {cell.id}: {programs * 4} trials, "
              f"{cell_bad} with non-monotone drain sums")
    print(f"  TOTAL {tot['trials']:,} trials, "
          f"{tot['nonmonotone']} non-monotone, "
          f"{tot['missed']} adapter events at a drain tick that the finalization "
          f"look does not also carry   [{time.time() - t0:.1f}s]")
    return tot


# ===========================================================================
# D -- the whole frozen grid
# ===========================================================================
EVENT_KEYS = ("ever_miscover_h", "ever_below_h", "ever_above_h",
              "ever_miscover_s", "ever_below_s", "ever_above_s",
              "ever_miscover_h_elig", "ever_miscover_s_elig")
DECISION_KEYS = ("DEPLOY", "RETAIN_INCUMBENT", "NO_DECISION", "CONFLICT",
                 "decided_at_finalization", "false_deploy", "false_harm",
                 "any_erroneous", "never_conjunct")
SCHEDULES = ("reduced", "all_ticks", "finest")


#: liveness diagnostics: the added looks exist and carry events, whether or not
#: those events are NEW.  A zero here would mean the added-look machinery is
#: vacuous and the "nothing moves" verdict would be worthless.
LIVENESS = ("added_looks", "added_look_fires", "added_look_miscovers")


def _blank() -> Dict[str, int]:
    d = {f"{k}|{s}": 0 for k in EVENT_KEYS for s in SCHEDULES}
    d.update({f"{k}|{s}": 0 for k in DECISION_KEYS for s in SCHEDULES})
    d.update({f"family_any_erroneous|{s}": 0 for s in SCHEDULES})
    d.update({f"tau_sum|{s}": 0 for s in SCHEDULES})
    d.update({f"{k}|{s}": 0 for k in LIVENESS for s in SCHEDULES})
    d["trials"] = 0
    d["programs"] = 0
    return d


def sweep_grid(programs_per_cell: Dict[str, int], cfg: vrun.RunConfig,
               limit: Optional[int] = None, cells: Optional[Sequence[str]] = None
               ) -> Dict[Tuple[str, str], Dict[str, int]]:
    acc: Dict[Tuple[str, str], Dict[str, int]] = {}
    delta, n_min = cfg.delta, cfg.n_min
    n_max = cfg.n_max
    t0 = time.time()
    for cell in vgen.CELLS:
        if cells and cell.id not in cells:
            continue
        n_prog = programs_per_cell[cell.id] if limit is None else limit
        mu_h, mu_s = cell.mu_h, cell.mu_s
        for name in vrun.CONSTRUCTIONS:
            acc.setdefault((cell.id, name), _blank())
        for p in range(n_prog):
            fam = {name: {s: False for s in SCHEDULES} for name in vrun.CONSTRUCTIONS}
            for t in range(vgen.TRIALS_PER_PROGRAM):
                draw = vgen.draw_trial(cell, p, t, n_max=n_max,
                                       namespace=vgen.NAMESPACE_GRID)
                recs, _, _ = vrun.evaluate_trial(draw, cfg)
                ticks, dstates = drain_states(draw, cfg)
                fstates = finest_states(draw, cfg)
                # PROTOCOL 9.2's `never_conjunct` is the one reported column
                # that is NOT monotone in the look set: an added look can turn
                # a marginal condition on (making it true) or supply the
                # missing same-look conjunction (making it false).  Its two
                # components are recomputed here from the frozen series.
                series, _, _, _ = vrun.build_series(draw, cfg)
                for name in vrun.CONSTRUCTIONS:
                    a = acc[(cell.id, name)]
                    a["trials"] += 1
                    r = recs[name]
                    base = {
                        "ever_miscover_h": r.ever_miscover_h,
                        "ever_below_h": r.ever_below_h,
                        "ever_above_h": r.ever_above_h,
                        "ever_miscover_s": r.ever_miscover_s,
                        "ever_below_s": r.ever_below_s,
                        "ever_above_s": r.ever_above_s,
                        "ever_miscover_h_elig": r.ever_miscover_h_elig,
                        "ever_miscover_s_elig": r.ever_miscover_s_elig}
                    dec = {"reduced": (r.decision, r.tau,
                                       r.decided_at_finalization)}
                    ev_extra = {"all_ticks": {}, "finest": {}}
                    sr = series[name]
                    el0 = sr.index >= n_min
                    nc0 = (bool((el0 & (sr.l_h > 0.0)).any()),
                           bool((el0 & (sr.l_s > -delta)).any()),
                           bool((el0 & (sr.l_h > 0.0) & (sr.l_s > -delta)).any()))
                    if name in BASELINES:
                        idx, sh, ss = dstates[name]
                        e2 = band_events(idx, sh, ss, cfg, mu_h, mu_s)
                        fi, fh, fs, ftick = fstates[name]
                        e3 = band_events(fi, fh, fs, cfg, mu_h, mu_s)
                        ev_extra["all_ticks"] = e2
                        ev_extra["finest"] = e3
                    for s in SCHEDULES:
                        e = ev_extra.get(s) or {}
                        vals = dict(base)
                        if e:
                            a[f"added_looks|{s}"] += int(e["fired"].size)
                            a[f"added_look_fires|{s}"] += int(e["fired"].any())
                            a[f"added_look_miscovers|{s}"] += int(
                                (e["below_h"] | e["above_h"] | e["below_s"]
                                 | e["above_s"]).any())
                            vals["ever_below_h"] |= bool(e["below_h"].any())
                            vals["ever_above_h"] |= bool(e["above_h"].any())
                            vals["ever_below_s"] |= bool(e["below_s"].any())
                            vals["ever_above_s"] |= bool(e["above_s"].any())
                            vals["ever_miscover_h"] = (vals["ever_below_h"]
                                                       or vals["ever_above_h"])
                            vals["ever_miscover_s"] = (vals["ever_below_s"]
                                                       or vals["ever_above_s"])
                            vals["ever_miscover_h_elig"] |= bool(
                                (e["elig"] & (e["below_h"] | e["above_h"])).any())
                            vals["ever_miscover_s_elig"] |= bool(
                                (e["elig"] & (e["below_s"] | e["above_s"])).any())
                        for k in EVENT_KEYS:
                            if vals[k]:
                                a[f"{k}|{s}"] += 1
                        dep_any, gua_any, both_any = nc0
                        if e:
                            dep_any |= bool((e["elig"] & (e["lo_h"] > 0.0)).any())
                            gua_any |= bool(
                                (e["elig"] & (e["lo_s"] > -delta)).any())
                            both_any |= bool((e["elig"] & (e["lo_h"] > 0.0)
                                              & (e["lo_s"] > -delta)).any())
                        if dep_any and gua_any and not both_any:
                            a[f"never_conjunct|{s}"] += 1
                        # ---- decisions -------------------------------
                        # The decision is the FIRST crossing over the merged,
                        # chronologically ordered look set.  A look at enrolled
                        # prefix p sits at tick p; the finalization look sits at
                        # tick N_max + W.
                        decision, tau = r.decision, r.tau
                        at_fin = r.decided_at_finalization
                        if e:
                            order_tick = ticks if s == "all_ticks" else ftick
                            fired = np.flatnonzero(e["fired"])
                            if len(fired):
                                i = int(fired[0])
                                tick_i = int(order_tick[i])
                                if decision == vrun.NO_DECISION:
                                    red_tick = cfg.finalization_tick + 1
                                elif at_fin:
                                    red_tick = cfg.finalization_tick
                                else:
                                    red_tick = tau          # look at prefix tau
                                if tick_i < red_tick:
                                    decision = (vrun.CONFLICT
                                                if (e["deploy"][i] and e["harm"][i])
                                                else vrun.DEPLOY if e["deploy"][i]
                                                else vrun.RETAIN_INCUMBENT)
                                    tau = min(tick_i, n_max)
                                    at_fin = False
                        a[f"{vrun.DECISION_LABEL[decision]}|{s}"] += 1
                        if at_fin:
                            a[f"decided_at_finalization|{s}"] += 1
                        a[f"tau_sum|{s}"] += int(tau)
                        fd = (decision == vrun.DEPLOY
                              and not (mu_h > 0 and mu_s > -delta))
                        fh = (decision == vrun.RETAIN_INCUMBENT and mu_h >= 0)
                        if fd:
                            a[f"false_deploy|{s}"] += 1
                        if fh:
                            a[f"false_harm|{s}"] += 1
                        if fd or fh:
                            a[f"any_erroneous|{s}"] += 1
                            fam[name][s] = True
            for name in vrun.CONSTRUCTIONS:
                a = acc[(cell.id, name)]
                a["programs"] += 1
                for s in SCHEDULES:
                    if fam[name][s]:
                        a[f"family_any_erroneous|{s}"] += 1
        done = acc[(cell.id, vrun.ADAPTER)]["trials"]
        print(f"  {cell.id}: {done:,} trials swept   "
              f"[{time.time() - t0:.1f}s]", flush=True)
    return acc


# ===========================================================================
# reporting
# ===========================================================================
def frozen_miscoverage() -> Dict[Tuple[str, str, str, str, str], Tuple[int, int]]:
    """(cell, construction, gate, looks, event) -> (x, N) from the deposited CSV."""
    out = {}
    with open(RESULTS / "miscoverage.csv", newline="") as fh:
        rows = [r for r in fh if not r.startswith("#")]
    for r in csv.DictReader(rows):
        out[(r["cell"], r["construction"], r["gate"], r["looks"], r["event"])] = (
            int(r["x"]), int(r["N"]))
    return out


def frozen_decisions() -> Dict[Tuple[str, str, str], Tuple[int, int]]:
    out = {}
    with open(RESULTS / "decisions.csv", newline="") as fh:
        rows = [r for r in fh if not r.startswith("#")]
    for r in csv.DictReader(rows):
        out[(r["cell"], r["construction"], r["quantity"])] = (
            int(r["x"]), int(r["N"]))
    return out


def report_grid(acc, cfg) -> None:
    froz_m, froz_d = frozen_miscoverage(), frozen_decisions()
    print(f"\n{'=' * 78}\nD.1  FAITHFULNESS: the 'reduced' column against the "
          f"deposited CSVs\n{'=' * 78}")
    bad = 0
    checked = 0
    for (cell_id, name), a in sorted(acc.items()):
        for gate, keys in (("hierarchy", ("ever_miscover_h", "ever_below_h",
                                          "ever_above_h")),
                           ("success", ("ever_miscover_s", "ever_below_s",
                                        "ever_above_s"))):
            for key, event in zip(keys, ("ever_miscover", "ever_below", "ever_above")):
                ref = froz_m.get((cell_id, name, gate, "all", event))
                if ref is None:
                    continue
                checked += 1
                if ref[0] != a[f"{key}|reduced"] or ref[1] != a["trials"]:
                    bad += 1
                    print(f"  MISMATCH {cell_id} {name} {gate} {event}: "
                          f"frozen {ref} vs recomputed "
                          f"({a[f'{key}|reduced']}, {a['trials']})")
        for q, key in (("false_deploy", "false_deploy"), ("false_harm", "false_harm"),
                       ("any_erroneous_trial", "any_erroneous"),
                       ("family_any_erroneous", "family_any_erroneous"),
                       ("never_conjunct", "never_conjunct"),
                       ("deploy", "DEPLOY"), ("retain_incumbent", "RETAIN_INCUMBENT"),
                       ("no_decision", "NO_DECISION"), ("conflict", "CONFLICT"),
                       ("decided_at_finalization", "decided_at_finalization")):
            ref = froz_d.get((cell_id, name, q))
            if ref is None:
                continue
            checked += 1
            if ref[0] != a[f"{key}|reduced"]:
                bad += 1
                print(f"  MISMATCH {cell_id} {name} {q}: frozen {ref} vs "
                      f"recomputed {a[f'{key}|reduced']}")
    print(f"  {checked} deposited (x, N) pairs re-derived; {bad} mismatches.")

    print(f"\n{'=' * 78}\nD.2  WHAT THE REDUCTION MISSES, per cell and construction"
          f"\n     reduced = the frozen schedule; all_ticks = + every drain tick;"
          f"\n     finest  = + every distinct completion-index state"
          f"\n{'=' * 78}")
    hdr = (f"  {'cell':<5}{'constr':<9}{'quantity':<26}"
           f"{'N':>7}{'reduced':>9}{'all_ticks':>11}{'finest':>9}")
    print(hdr)
    any_move = []
    for (cell_id, name), a in sorted(acc.items()):
        for key in EVENT_KEYS + DECISION_KEYS + ("family_any_erroneous",
                                                 "tau_sum"):
            r, t2, t3 = (a[f"{key}|reduced"], a[f"{key}|all_ticks"],
                         a[f"{key}|finest"])
            if r == t2 == t3:
                continue
            N = a["programs"] if key == "family_any_erroneous" else a["trials"]
            print(f"  {cell_id:<5}{name:<9}{key:<26}{N:>7,}{r:>9,}{t2:>11,}{t3:>9,}")
            any_move.append((cell_id, name, key, N, r, t2, t3))
    if not any_move:
        print("  (nothing moves anywhere)")

    print(f"\n{'=' * 78}\nD.2b LIVENESS of the added looks: they exist and carry"
          f" events, new or not\n{'=' * 78}")
    print(f"  {'cell':<5}{'constr':<9}{'schedule':<11}{'added looks':>13}"
          f"{'trials where one fires':>24}{'...miscovers':>14}")
    for (cell_id, name), a in sorted(acc.items()):
        if name not in BASELINES:
            continue
        for s in ("all_ticks", "finest"):
            print(f"  {cell_id:<5}{name:<9}{s:<11}{a[f'added_looks|{s}']:>13,}"
                  f"{a[f'added_look_fires|{s}']:>24,}"
                  f"{a[f'added_look_miscovers|{s}']:>14,}")

    print(f"\n{'=' * 78}\nD.3  EVERY WILSON FLAG, recomputed under each schedule"
          f"\n{'=' * 78}")
    nominal = {"ever_miscover_h": 0.00625, "ever_miscover_s": 0.00625,
               "ever_below_h": 0.00625, "ever_above_h": 0.00625,
               "ever_below_s": 0.00625, "ever_above_s": 0.00625,
               "ever_miscover_h_elig": 0.00625, "ever_miscover_s_elig": 0.00625,
               "false_deploy": 0.00625, "false_harm": 0.00625,
               "any_erroneous": 0.0125, "family_any_erroneous": 0.05}
    flips = []
    for (cell_id, name), a in sorted(acc.items()):
        for key, nom in nominal.items():
            N = a["programs"] if key == "family_any_erroneous" else a["trials"]
            f = {}
            for s in SCHEDULES:
                x = a[f"{key}|{s}"]
                _, lo, _ = vrun.wilson(x, N)
                f[s] = vrun.is_flagged(lo, nom)
            if f["reduced"] != f["all_ticks"] or f["reduced"] != f["finest"]:
                flips.append((cell_id, name, key, f))
                print(f"  FLAG FLIP  {cell_id} {name} {key}: "
                      f"reduced={f['reduced']} all_ticks={f['all_ticks']} "
                      f"finest={f['finest']}")
    if not flips:
        print("  no flag changes state under any schedule.")

    print(f"\n{'=' * 78}\nD.4  THE PRECOMMITTED POSITIVE CONTROL (PROTOCOL 9.4)"
          f"\n     'NAIVE hierarchy ever-miscoverage must be FLAGGED in at least one"
          f" of C2, C4, C6'\n{'=' * 78}")
    for s in SCHEDULES:
        cells_flagged = []
        for cell_id in ("C2", "C4", "C6"):
            a = acc.get((cell_id, vrun.NAIVE))
            if a is None:
                continue
            x, N = a[f"ever_miscover_h|{s}"], a["trials"]
            _, lo, hi = vrun.wilson(x, N)
            fl = vrun.is_flagged(lo, 0.00625)
            print(f"  {s:<10} {cell_id} NAIVE hierarchy ever_miscover: "
                  f"x={x:,}/{N:,} rate={x / N:.6f} "
                  f"wilson_lo={lo:.6f} nominal=0.00625 flagged={fl}")
            if fl:
                cells_flagged.append(cell_id)
        print(f"  {s:<10} => positive control "
              f"{'PASSES' if cells_flagged else 'FAILS'} "
              f"(flagged in {cells_flagged})")


# ===========================================================================
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", default="all",
                    choices=("all", "witness", "adapter", "grid"))
    ap.add_argument("--limit", type=int, default=None,
                    help="programs per cell (default: the frozen grid's own)")
    ap.add_argument("--adapter-programs", type=int, default=25)
    ap.add_argument("--cells", default=None, help="comma-separated cell ids")
    args = ap.parse_args(argv)

    manifest = json.loads((RESULTS / "manifest.json").read_text())
    n_max = int(manifest["N_max"])
    per_cell = {k: int(v) for k, v in manifest["programs_per_cell"].items()}
    cfg = vrun.make_config(n_max=n_max, namespace=vgen.NAMESPACE_GRID)
    print(f"reported grid: tier {manifest['selected_budget_tier']}, "
          f"N_max {n_max:,}, drain W {vgen.DRAIN_W}, finalization tick "
          f"{cfg.finalization_tick:,}, programs per cell {per_cell}")
    print(f"python {sys.version.split()[0]}, numpy {np.__version__}")

    if args.part in ("all", "witness"):
        report_witness(1000)
        report_witness(n_max)
    if args.part in ("all", "adapter"):
        adapter_sample_check(args.adapter_programs, cfg)
    if args.part in ("all", "grid"):
        print(f"\n{'=' * 78}\nD. THE WHOLE FROZEN GRID\n{'=' * 78}")
        cells = args.cells.split(",") if args.cells else None
        acc = sweep_grid(per_cell, cfg, limit=args.limit, cells=cells)
        report_grid(acc, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
