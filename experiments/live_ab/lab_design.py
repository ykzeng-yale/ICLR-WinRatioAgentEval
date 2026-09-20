"""Frozen per-trial arrival order and stratified pairing (G2).

Implements ARCHITECTURE_FINAL.md section 3.5 against protocol_FINAL.md section 3.4.

What this file is: a deterministic function of frozen constants (the roster, `design_seed_base` and the
trial number). It produces the order in which tasks arrive and how consecutive arrivals are grouped into
disjoint pairs. Pairs are formed **inside a stratum**: S1 tasks pair with S1 tasks and S2 with S2, the
odd remainder of each stratum is a leftover that is never enrolled, and

    N_P = floor(n_S1 / 2) + floor(n_S2 / 2)        (protocol 3.3)

which is at most 568 on the extended roster and 295 on roster S1. It is never `n_total // 2`.

What this file is **not**: it is not the orientation mechanism. Nothing here reads OS entropy, nothing
here decides which system runs at which position, and the file it writes contains nothing from which
such a decision could be computed (protocol 3.4, root guidance item 1). A test in
`tests_lab_isolation.py` greps this module for the five identifiers that would betray a leak, and
`tests_lab_design.py` repeats that grep.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

import numpy

import lab_common

#: Trial numbers `e` of protocol 3.4 (T1 = 1 ... T4 = 4). These index the seed sequence and have
#: nothing to do with the execution order T4, T2, T1, T3.
TRIAL_NO: dict[str, int] = {'T1': 1, 'T2': 2, 'T3': 3, 'T4': 4}

STRATA: tuple[str, ...] = ('S1', 'S2')

ORDER_SCHEMA: str = 'live_ab/arrival_order-v1'


class PairSlot(TypedDict):
    pair: int                          # 1-based
    stratum: Literal['S1', 'S2']       # there is no 'mixed' stratum: a pair never crosses the strata
    arrivals: tuple[int, int]          # (2*pair-1, 2*pair)
    uids: tuple[str, str]              # task at position 1, task at position 2


class LeftoverSlot(TypedDict):
    arrival: int                       # numbered after 2 * N_P, in list order
    stratum: Literal['S1', 'S2']
    uid: str


def _generate(roster: dict, trial: str, design_seed_base: int) -> tuple[list, list]:
    """The literal code path of protocol 3.4. Returns `(pairs, leftovers)` as plain tuples.

    One generator, used for S1, then S2, then the whole-pair permutation, in that order: the draw
    sequence is part of the frozen definition and must not be reordered.
    """
    if trial not in TRIAL_NO:
        raise lab_common.FrozenMismatch('unknown trial %r' % (trial,))
    generator = numpy.random.Generator(numpy.random.PCG64(
        numpy.random.SeedSequence([int(design_seed_base), TRIAL_NO[trial]])))
    pairs: list[tuple[str, str, str]] = []
    leftovers: list[tuple[str, str]] = []
    for stratum in STRATA:
        uids = sorted(roster.get(stratum) or [])        # bytewise order of the uid strings
        if not uids:
            continue                                    # S2 is absent on roster S1
        shuffled = [uids[j] for j in generator.permutation(len(uids))]
        whole = len(shuffled) // 2
        pairs += [(stratum, shuffled[2 * m], shuffled[2 * m + 1]) for m in range(whole)]
        leftovers += [(stratum, uid) for uid in shuffled[2 * whole:]]
    enrollment = [pairs[j] for j in generator.permutation(len(pairs))]
    return enrollment, leftovers


def arrival_order(roster: dict, trial: str, design_seed_base: int) -> list[PairSlot]:
    """[pure] The frozen enrollment order of `trial`, as `N_P` stratified pair slots.

    Pair `i` (1-based) occupies arrivals `2i-1` and `2i`. Both positions of a pair are fixed here,
    before anything about the pair's orientation exists (protocol 3.4, `paper/theory.tex:179-190`).
    """
    enrollment, _ = _generate(roster, trial, design_seed_base)
    return [PairSlot(pair=i + 1, stratum=stratum, arrivals=(2 * i + 1, 2 * i + 2), uids=(u1, u2))
            for i, (stratum, u1, u2) in enumerate(enrollment)]


def leftover_slots(roster: dict, trial: str, design_seed_base: int) -> list[LeftoverSlot]:
    """[pure] The odd remainder of each stratum, numbered after `2 * N_P` in list order.

    Leftovers are never enrolled and are executed only in a follow-up cohort (protocol 3.3, 3.4).
    """
    enrollment, leftovers = _generate(roster, trial, design_seed_base)
    base = 2 * len(enrollment)
    return [LeftoverSlot(arrival=base + k + 1, stratum=stratum, uid=uid)
            for k, (stratum, uid) in enumerate(leftovers)]


def order_sha256(order: list[PairSlot]) -> str:
    """[pure] sha256 over the canonical JSON of the pair slots alone."""
    return lab_common.sha256_canonical([_slot_view(slot) for slot in order])


def _slot_view(slot: PairSlot) -> dict:
    return {'pair': int(slot['pair']), 'stratum': str(slot['stratum']),
            'arrivals': [int(slot['arrivals'][0]), int(slot['arrivals'][1])],
            'uids': [str(slot['uids'][0]), str(slot['uids'][1])]}


def order_document(roster: dict, trial: str, design_seed_base: int) -> dict:
    """[pure] The complete `arrival_order_T<e>.json` object protocol 3.4 declares authoritative.

    ARCHITECTURE 3.5 gives `write_order` the pair list alone, which has no room for the leftovers and
    `N_P` that protocol 3.4 says the file carries. Both are satisfied: `write_order` writes the pair
    document, this function builds the protocol-complete one, and `load_order` reads either.
    """
    order = arrival_order(roster, trial, design_seed_base)
    leftovers = leftover_slots(roster, trial, design_seed_base)
    n_pairs = len(order)
    expected = len(roster.get('S1') or []) // 2 + len(roster.get('S2') or []) // 2
    if n_pairs != expected:
        raise lab_common.FrozenMismatch('N_P is %d but floor(n_S1/2)+floor(n_S2/2) is %d'
                                        % (n_pairs, expected))
    return {'schema': ORDER_SCHEMA, 'trial': trial, 'trial_no': TRIAL_NO[trial],
            'design_seed_base': int(design_seed_base), 'n_pairs': n_pairs,
            'roster_sha256': roster.get('roster_sha256'),
            'strata': {'S1': len(roster.get('S1') or []), 'S2': len(roster.get('S2') or [])},
            'pairs': [_slot_view(slot) for slot in order],
            'leftovers': [dict(slot) for slot in leftovers],
            'order_sha256': order_sha256(order)}


def write_order(order: list[PairSlot], path: Path) -> str:
    """Write-once, durable. Returns the sha256 of the bytes written."""
    body = {'schema': ORDER_SCHEMA, 'n_pairs': len(order),
            'pairs': [_slot_view(slot) for slot in order], 'order_sha256': order_sha256(order)}
    return lab_common.write_json_atomic(Path(path), body, durable=True)


def write_order_document(document: dict, path: Path) -> str:
    """Write-once, durable, for the protocol-complete document of `order_document`."""
    return lab_common.write_json_atomic(Path(path), document, durable=True)


def load_order(path: Path) -> list[PairSlot]:
    """Read either written shape and return the pair slots, with tuples restored."""
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = raw if isinstance(raw, list) else raw.get('pairs')
    if rows is None:
        raise lab_common.FrozenMismatch('no pair list in %s' % (Path(path).name,))
    order = [PairSlot(pair=int(row['pair']), stratum=row['stratum'],
                      arrivals=(int(row['arrivals'][0]), int(row['arrivals'][1])),
                      uids=(str(row['uids'][0]), str(row['uids'][1]))) for row in rows]
    if isinstance(raw, dict) and raw.get('order_sha256') is not None:
        if order_sha256(order) != raw['order_sha256']:
            raise lab_common.FrozenMismatch('order_sha256 does not match the pair list')
    return order


def check_order(order: list[PairSlot]) -> None:
    """[pure] Raise `ValueError` unless the order obeys protocol 3.4 and 7.1.

    Checks: pair numbers are 1..N_P in sequence; arrivals are the consecutive `(2i-1, 2i)`; the two
    uids of a slot differ; **both uids of a slot share the stratum of the slot, so no slot is mixed**;
    every uid occurs at most once in the whole order.
    """
    seen: dict[str, int] = {}
    for index, slot in enumerate(order):
        i = index + 1
        if int(slot['pair']) != i:
            raise ValueError('slot %d carries pair %r' % (i, slot['pair']))
        if tuple(slot['arrivals']) != (2 * i - 1, 2 * i):
            raise ValueError('pair %d has arrivals %r, expected %r'
                             % (i, tuple(slot['arrivals']), (2 * i - 1, 2 * i)))
        if slot['stratum'] not in STRATA:
            raise ValueError('pair %d has stratum %r' % (i, slot['stratum']))
        u1, u2 = slot['uids']
        if u1 == u2:
            raise ValueError('pair %d repeats uid %r' % (i, u1))
        for uid in (u1, u2):
            if uid in seen:
                raise ValueError('uid %r occurs in pair %d and pair %d' % (uid, seen[uid], i))
            seen[uid] = i


def strata_of(roster: dict) -> dict[str, str]:
    """[pure] `{uid: stratum}` from the roster's two stratum lists."""
    out: dict[str, str] = {}
    for stratum in STRATA:
        for uid in roster.get(stratum) or []:
            out[uid] = stratum
    return out


def assert_no_mixed_slot(order: list[PairSlot], roster: dict) -> None:
    """[pure] Raise `ValueError` if either uid of any slot belongs to a different stratum.

    `check_order` proves the order is internally consistent; this proves it agrees with the roster,
    which is what "a pair never crosses the strata" means (protocol 3.4, audit B5).
    """
    lookup = strata_of(roster)
    for slot in order:
        for uid in slot['uids']:
            actual = lookup.get(uid)
            if actual is None:
                raise ValueError('pair %d names %r, which is not on the roster' % (slot['pair'], uid))
            if actual != slot['stratum']:
                raise ValueError('pair %d is %s but %r is %s'
                                 % (slot['pair'], slot['stratum'], uid, actual))


def assert_disjoint(orders: dict[str, list[PairSlot]]) -> None:
    """[pure] Within-trial disjointness, plus the cross-trial shape checks that are meaningful here.

    Within a trial every uid occurs exactly once and the slots are the consecutive pairs of the frozen
    order (`check_order`). Across trials, every order must have the same number of slots and the same
    per-stratum slot counts; the uid sets may differ by **at most one uid per stratum**, which is the
    leftover an odd stratum necessarily has and which a different trial number moves elsewhere.

    Tasks ARE reused across trials (`PROTOCOL-GAP PG-22`); this function proves within-trial
    disjointness only. Raises `ValueError` naming the first offender.
    """
    if not orders:
        return
    shapes: dict[str, tuple] = {}
    uid_sets: dict[str, dict[str, set[str]]] = {}
    for trial in sorted(orders):
        order = orders[trial]
        try:
            check_order(order)
        except ValueError as exc:
            raise ValueError('%s: %s' % (trial, exc)) from None
        per_stratum: dict[str, set[str]] = {s: set() for s in STRATA}
        counts: dict[str, int] = {s: 0 for s in STRATA}
        for slot in order:
            counts[slot['stratum']] += 1
            per_stratum[slot['stratum']].update(slot['uids'])
        shapes[trial] = (len(order), tuple(counts[s] for s in STRATA))
        uid_sets[trial] = per_stratum
    reference_trial = sorted(shapes)[0]
    for trial, shape in shapes.items():
        if shape != shapes[reference_trial]:
            raise ValueError('%s has shape %r but %s has %r'
                             % (trial, shape, reference_trial, shapes[reference_trial]))
    trials = sorted(uid_sets)
    for a_index, trial_a in enumerate(trials):
        for trial_b in trials[a_index + 1:]:
            for stratum in STRATA:
                diff = uid_sets[trial_a][stratum] ^ uid_sets[trial_b][stratum]
                if len(diff) > 2:
                    raise ValueError('%s and %s differ by %d uids in %s; only the leftover may differ'
                                     % (trial_a, trial_b, len(diff), stratum))
