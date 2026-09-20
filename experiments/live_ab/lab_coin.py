"""The orientation coin, its write-ahead commit, and the per-request seed rule (G2).

Implements ARCHITECTURE_FINAL.md section 3.6 against protocol_FINAL.md section 4 (and 5.5 for seeds).

The whole of the randomization is here, and it is three lines long:

    raw = os.urandom(8)          # the only source of orientation randomness in the program
    bit = raw[0] & 1             # R_i
    log.append('coin_drawn', ..., durable=True)      # returns only after F_FULLFSYNC returned

Everything else in this module exists to make those three lines auditable:

* `draw_and_commit` is the **only** function the orchestrator may use to obtain an orientation, and it
  returns only after the coin's chain line is on the drive. Neither episode of the pair may be
  dispatched before it returns (protocol 4.2; state-machine rows 5 and 6).
* A coin is **never redrawn**. Every chain-valid `coin_drawn` line binds on resume, whether or not its
  fsync had returned; a coin is void only if its line fails chain verification, i.e. it lies inside a
  torn region (protocol 4.2 invariant v).
* `coin_ordering_findings` is the invariant checker for protocol 4.2 (i)-(iv) and (vii), as a pure
  function of the chain, so the orchestrator, the verifier and the tests all read the same rules.

`os.urandom` is the only randomness this module knows: `random`, `secrets` and `numpy` are deliberately
absent, and the import-isolation test whitelists `lab_coin` (orientation) and `lab_client` (seeds) as
the only call sites of `os.urandom` in the program.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Literal, Mapping, Sequence, TypedDict

import lab_common

if TYPE_CHECKING:                       # never imported at run time; see ARCHITECTURE 3.16
    from lab_eventlog import Event, EventLog


class PairSlot(TypedDict):
    """Structural mirror of `lab_design.PairSlot`.

    Declared here rather than imported: the isolation matrix forbids `lab_coin` from importing
    `lab_design`, and a `TypedDict` is a plain dict at run time, so a slot produced by
    `lab_design.arrival_order()` satisfies this declaration exactly.
    """

    pair: int
    stratum: Literal['S1', 'S2']
    arrivals: tuple[int, int]
    uids: tuple[str, str]


@dataclass(frozen=True)
class Coin:
    raw_hex: str          # 16 hex chars = the 8 bytes actually drawn
    bit: int              # raw[0] & 1
    source: str = 'os.urandom(8)'


ORIENTATION: dict[int, tuple[str, str]] = {
    1: ('candidate', 'incumbent'),      # bit 1 -> candidate at position 1
    0: ('incumbent', 'candidate'),
}

ENTROPY_SOURCE: str = 'os.urandom(8)'
COIN_EVENT: str = 'coin_drawn'

#: Per-request seed rule (protocol 5.5, PROTOCOL-GAP PG-8).
SEED_MASK: int = 0x7FFFFFFE
SEED_FORBIDDEN: int = 0xFFFFFFFF
SEED_MAX_REDRAWS: int = 64


def draw() -> Coin:
    """The ONLY call to os.urandom(8) in the orientation path. No other randomness enters an arm."""
    raw = os.urandom(8)
    if len(raw) != 8:
        raise lab_common.LabError('os.urandom(8) returned %d bytes' % len(raw))
    return Coin(raw_hex=raw.hex(), bit=raw[0] & 1)


def assignment(pair: PairSlot, coin: Coin) -> dict[int, str]:
    """[pure] `{arrival_at_position_1: arm, arrival_at_position_2: arm}` from `ORIENTATION[coin.bit]`."""
    if coin.bit not in ORIENTATION:
        raise lab_common.LabError('coin bit is %r, not 0 or 1' % (coin.bit,))
    arrivals = tuple(pair['arrivals'])
    if len(arrivals) != 2 or int(arrivals[0]) >= int(arrivals[1]):
        raise lab_common.LabError('pair %r has arrivals %r' % (pair.get('pair'), arrivals))
    first, second = ORIENTATION[coin.bit]
    return {int(arrivals[0]): first, int(arrivals[1]): second}


def coin_body(pair: PairSlot, coin: Coin, assigned: Mapping[int, str]) -> dict:
    """[pure] The `coin_drawn` event body of ARCHITECTURE 4.4 row T10."""
    return {'pair': int(pair['pair']), 'entropy_source': ENTROPY_SOURCE, 'raw_hex': coin.raw_hex,
            'bit': int(coin.bit), 'assignment': {str(int(a)): arm for a, arm in assigned.items()}}


def draw_and_commit(log: 'EventLog', pair: PairSlot) -> tuple[Coin, dict[int, str], 'Event']:
    """Write-ahead rule, normative (protocol 4.2; state-machine row 5).

    Draws the coin, appends `coin_drawn` with `durable=True`, and returns ONLY after `fullsync()` has
    returned. The caller may not dispatch either episode of the pair before this function returns, and
    this function performs no other side effect between the draw and the durable append: there is
    nothing in it that could observe the coin and act on it.

    Side effects: one `os.urandom` call, one durable append.
    """
    coin = draw()
    assigned = assignment(pair, coin)
    event = log.append(COIN_EVENT, coin_body(pair, coin, assigned), durable=True)
    return coin, assigned, event


def selftest_entropy(n: int = 10_000, lo: int = 4_850, hi: int = 5_150) -> dict:
    """Pre-freeze plumbing check on NON-design coins (phase=SMOKE).

    Returns `{'n': n, 'ones': k, 'ok': lo <= k <= hi}`. Never repeated silently on failure: the caller
    reports the result and stops (protocol 4.3). The test says nothing about the design coins.
    """
    ones = 0
    for _ in range(int(n)):
        ones += draw().bit
    return {'n': int(n), 'ones': ones, 'ok': bool(lo <= ones <= hi)}


# --------------------------------------------------------------------------------------------------
# Per-request seeds (protocol 5.5 / PROTOCOL-GAP PG-8)
# --------------------------------------------------------------------------------------------------


def draw_seed(worker_index: int, used: set[int] | None = None) -> int:
    """`(os.urandom(4) & 0x7FFFFFFE) | worker_index` — the low bit carries the worker index.

    The partition makes a cross-worker collision impossible, so each worker checks only its own half of
    the used-seed set. `0xFFFFFFFF` can never be produced (the mask clears bit 31 and bit 0, so the
    largest value is 0x7FFFFFFF). A value already in `used` is redrawn; `used` is updated in place.

    The draw reads nothing about the arm: `worker_index` is the slot (0 for position 1, 1 for position
    2), not the system under test (audit M1). Callers log the seed **before** the POST.
    """
    index = int(worker_index)
    if index not in (0, 1):
        raise lab_common.LabError('worker_index is %r, not 0 or 1' % (worker_index,))
    for _ in range(SEED_MAX_REDRAWS):
        seed = (int.from_bytes(os.urandom(4), 'big') & SEED_MASK) | index
        if seed == SEED_FORBIDDEN:              # the mask already forbids it; the check is one line
            continue
        if used is not None and seed in used:
            continue
        if used is not None:
            used.add(seed)
        return seed
    raise lab_common.LabError('no unused seed found for worker_index %d in %d draws'
                              % (index, SEED_MAX_REDRAWS))


def seed_half(seed: int) -> int:
    """[pure] The worker index a seed belongs to: its low bit."""
    return int(seed) & 1


# --------------------------------------------------------------------------------------------------
# Chain invariants of protocol 4.2
# --------------------------------------------------------------------------------------------------


def _pair_of_arrival(arrival: int) -> int:
    return (int(arrival) + 1) // 2


def coin_ordering_findings(events: Sequence[Mapping]) -> list[str]:
    """[pure] Protocol 4.2 invariants (i)-(iv) and (vii), over one trial chain in chain order.

    Returns one string per violation, `''` never. An empty list means the chain obeys, at this level:

    (i)   at most one chain-valid `coin_drawn` per pair;
    (ii)  a pair's coin follows its own `pair_enrolled`, both `episode_revealed` of the previous pair,
          and the reveal-triggered evaluation at prefix `i-1`;
    (iii) every `episode_started` of the randomized phase points at an earlier coin of its own pair,
          and carries the arm that coin assigned;
    (iv)  no coin after a `decision`, and none before the first `anchor_receipt` (the chained external
          receipt of the trial-start anchor, protocol 12.4);
    (vii) a re-enrollment is legal only before the pair's coin exists, and must be flagged
          `re_enrolled: true` (ARCHITECTURE 3.13 rule 2).

    The caller supplies already-verified events; this function does not re-verify hashes. It is
    deliberately independent of `lab_verify_log` so that the coin rules have a second reader.
    """
    findings: list[str] = []
    coin_seq: dict[int, int] = {}
    coin_map: dict[int, dict[int, str]] = {}
    enrolled: dict[int, int] = {}
    revealed_pairs: dict[int, set[int]] = {}
    second_reveal_seq: dict[int, int] = {}
    evaluated_prefixes: dict[int, int] = {}
    receipt_seq: int | None = None
    decision_seq: int | None = None
    for index, event in enumerate(events):
        etype = event.get('type')
        body = event.get('body') or {}
        seq = int(event.get('seq', index))
        if etype == 'anchor_receipt' and receipt_seq is None:
            receipt_seq = seq
        elif etype == 'decision' and decision_seq is None:
            decision_seq = seq
        elif etype == 'pair_enrolled':
            pair = int(body.get('pair', 0))
            if pair in enrolled:
                if not body.get('re_enrolled'):
                    findings.append('duplicate_enrollment_not_flagged:pair=%d,seq=%d' % (pair, seq))
                if pair in coin_seq:
                    findings.append('re_enrollment_after_coin:pair=%d,seq=%d' % (pair, seq))
            elif body.get('re_enrolled'):
                findings.append('re_enrolled_without_earlier_enrollment:pair=%d,seq=%d' % (pair, seq))
            enrolled[pair] = seq
        elif etype == 'episode_revealed':
            pair = int(body.get('pair', _pair_of_arrival(body.get('arrival', 0))))
            arrivals = revealed_pairs.setdefault(pair, set())
            arrivals.add(int(body.get('arrival', 0)))
            if len(arrivals) == 2 and pair not in second_reveal_seq:
                second_reveal_seq[pair] = seq
        elif etype == 'monitor_update':
            n = int(body.get('n', 0))
            if body.get('trigger') in ('reveal', 'enroll', 'call', 'resume', 'drain'):
                evaluated_prefixes[n] = seq
        elif etype == COIN_EVENT:
            pair = int(body.get('pair', 0))
            if pair in coin_seq:
                findings.append('duplicate_coin:pair=%d,seq=%d' % (pair, seq))
            coin_seq[pair] = seq
            coin_map[pair] = {int(a): arm for a, arm in (body.get('assignment') or {}).items()}
            if receipt_seq is None:
                findings.append('coin_before_start_receipt:pair=%d,seq=%d' % (pair, seq))
            if decision_seq is not None:
                findings.append('coin_after_decision:pair=%d,seq=%d' % (pair, seq))
            if pair not in enrolled:
                findings.append('coin_without_enrollment:pair=%d,seq=%d' % (pair, seq))
            if pair > 1:
                previous = pair - 1
                if len(revealed_pairs.get(previous, ())) < 2:
                    findings.append('coin_before_partner_reveals:pair=%d,seq=%d' % (pair, seq))
                # the evaluation invariant (ii) is about the look taken AFTER both reveals of
                # pair i-1, not about the earlier enroll-triggered update at the same prefix.
                # With pair i-1 still unresolved, `second_reveal_seq` defaults to this coin's own
                # seq, so no earlier update can satisfy the test.
                if evaluated_prefixes.get(previous, -1) <= second_reveal_seq.get(previous, seq):
                    findings.append('coin_before_evaluation:pair=%d,seq=%d' % (pair, seq))
            source = body.get('entropy_source')
            if source != ENTROPY_SOURCE:
                findings.append('foreign_entropy_source:pair=%d,seq=%d' % (pair, seq))
            raw_hex = str(body.get('raw_hex', ''))
            if len(raw_hex) != 16 or any(c not in '0123456789abcdef' for c in raw_hex):
                findings.append('malformed_raw_hex:pair=%d,seq=%d' % (pair, seq))
            elif (int(raw_hex[0:2], 16) & 1) != int(body.get('bit', -1)):
                findings.append('bit_not_from_raw:pair=%d,seq=%d' % (pair, seq))
        elif etype == 'episode_started':
            arrival = int(body.get('arrival', 0))
            pair = int(body.get('pair', _pair_of_arrival(arrival)))
            if body.get('arm') is not None and decision_seq is None:
                if pair not in coin_seq:
                    findings.append('dispatch_before_coin:arrival=%d,seq=%d' % (arrival, seq))
                elif coin_seq[pair] > seq:
                    findings.append('dispatch_before_coin:arrival=%d,seq=%d' % (arrival, seq))
                elif coin_map.get(pair, {}).get(arrival) != body.get('arm'):
                    findings.append('arm_not_from_coin:arrival=%d,seq=%d' % (arrival, seq))
    return findings


def assignments_from_chain(events: Iterable[Mapping]) -> dict[int, str]:
    """[pure] `{arrival: arm}` from every `coin_drawn` in the chain, in chain order."""
    out: dict[int, str] = {}
    for event in events:
        if event.get('type') == COIN_EVENT:
            for arrival, arm in ((event.get('body') or {}).get('assignment') or {}).items():
                out[int(arrival)] = str(arm)
    return out
