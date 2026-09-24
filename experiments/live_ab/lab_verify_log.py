"""The independent verifier of the live_ab chains (ARCHITECTURE_FINAL.md 3.3).

Group G1.  Permitted imports: stdlib + lab_common + lab_eventlog + lab_monitor +
lab_enclosure + lab_reference_rule + numpy + winstats.  Forbidden: lab_orchestrator,
lab_worker, lab_client, lab_server, lab_anchor, lab_mock_server, build_live_ab_results.

`_band_independent` below is a THIRD, deliberately naive implementation of the band: it
calls winstats.normal_mixture_radius directly in a Python loop and never touches
lab_monitor's band code.  The SECOND implementation is the live shadow,
lab_reference_rule (PROTOCOL-GAP PG-3).

CLI: python lab_verify_log.py --trial T1 [--mode plumbing|full] [--results DIR]
     [--work DIR] [--json OUT].  Exit 0 on PASS, 1 on FAIL, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Mapping, Sequence

import lab_common
import lab_eventlog
import lab_reference_rule
from lab_common import (ARMS, RESULTS_ROOT, SRC_DIR, TRIALS, WORK_ROOT, ChainError,
                        SchemaError, canonical_json, sha256_bytes, sha256_canonical,
                        sha256_file, sha256_text)
from lab_eventlog import (EVENT_SCHEMA, genesis_prev, event_hash, read_chain,
                          segment_paths, validate_event)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
import numpy as np                                                    # noqa: E402
import winstats                                                       # noqa: E402

# lab_monitor and lab_enclosure belong to G3 and are imported lazily: the verifier must be
# able to report on a chain even when the live statistical core cannot be loaded, and a
# module that cannot be loaded is itself a finding, never a silent PASS.
try:                                                                  # pragma: no cover
    import lab_monitor                                                # noqa: F401
except Exception:                                                     # pragma: no cover
    lab_monitor = None                                                # type: ignore
try:                                                                  # pragma: no cover
    import lab_enclosure                                              # noqa: F401
except Exception:                                                     # pragma: no cover
    lab_enclosure = None                                              # type: ignore


# ---------------------------------------------------------------------------
# the frozen check table of ARCHITECTURE_FINAL.md 3.3
# ---------------------------------------------------------------------------
CHECK_SEVERITY: dict[str, str] = {
    'chain.read': 'FAIL', 'chain.byte_identity': 'FAIL', 'chain.genesis': 'FAIL',
    'chain.segments': 'FAIL', 'chain.torn': 'DEFECT', 'schema.all': 'FAIL',
    'order.freeze_hashes': 'FAIL', 'order.enrollment': 'FAIL',
    'coin.one_per_pair': 'FAIL', 'coin.write_ahead': 'FAIL', 'coin.balance': 'INFO',
    'episode.one_reveal': 'FAIL', 'episode.record_match': 'FAIL',
    'episode.job_accepted': 'DEFECT', 'calls.one_terminal': 'FAIL',
    'seeds.unique': 'DEFECT', 'monitor.replay': 'FAIL', 'monitor.cadence': 'FAIL',
    'monitor.shadow': 'FAIL', 'monitor.independent_band': 'FAIL',
    'reference_rule.agreement': 'FAIL', 'monitor.first_crossing': 'FAIL',
    'enclosure.containment': 'FAIL', 'enclosure.monotone': 'FAIL',
    'worktree.integrity': 'FAIL', 'switch.phase': 'FAIL',
    'usage.reconciliation': 'DEFECT', 'exposure.ledger': 'FAIL',
    'anchor.prefix': 'FAIL', 'anchor.receipts': 'DEFECT', 'integrity.table': 'INFO',
    't4.payload_identity': 'FAIL', 'program.order': 'FAIL',
    # protocol 5.7, the host quiescence gate.  `host.record` is a FAIL because a scan
    # record that contradicts itself is a chain that lies about the host; `host.quiescence`
    # is a DEFECT because a foreign load observed DURING a trial is a fact the analysis
    # must carry, and what to do about it is the operator's decision, not the verifier's.
    'host.record': 'FAIL', 'host.quiescence': 'DEFECT',
    # repair contract EB1 (root 20:40 items 1 and 4): the live server lifecycle.  A FAIL,
    # because a chain whose server bodies claim comparisons that did not pass, whose crash
    # was never answered, or whose restarts exceed the frozen cap is not a chain a decision
    # may be read from.  See `_check_server_lifecycle`.
    'server.lifecycle': 'FAIL',
}

# Which verifier FAILs mean what between trials (protocol 6.4 rows 22a/22b, audit M5).
CONDITION_LIST_B: frozenset[str] = frozenset(
    {c for c in CHECK_SEVERITY if c.startswith('chain.')}
    | {'reference_rule.agreement', 't4.payload_identity'})
CONDITION_LIST_A: frozenset[str] = frozenset(
    {'usage.reconciliation', 'anchor.receipts', 'exposure.ledger'})

# Plumbing mode emits only these check ids: never a score, never a count by arm, never a
# table (ARCHITECTURE_FINAL.md 3.3).
_PLUMBING_PREFIXES: tuple[str, ...] = ('chain.', 'schema.', 'order.', 'coin.', 'episode.',
                                       'calls.', 'switch.', 'usage.', 'anchor.',
                                       'program.', 'worktree.', 't4.', 'host.',
                                       'server.')
_PLUMBING_EXTRA: frozenset[str] = frozenset({'monitor.replay', 'monitor.cadence',
                                             'monitor.shadow',
                                             'reference_rule.agreement'})


def plumbing_allows(check: str) -> bool:
    """The whitelist of ARCHITECTURE_FINAL.md 3.3, verbatim.  Everything it leaves out --
    every score, every count by arm and every table -- is structurally absent from a
    plumbing report, which is what makes the between-trial gate outcome-blind."""
    return check in _PLUMBING_EXTRA or check.startswith(_PLUMBING_PREFIXES)


def condition_list(check: str) -> str:
    if check in CONDITION_LIST_B:
        return 'B'
    if check in CONDITION_LIST_A:
        return 'A'
    return '-'


@dataclass(frozen=True)
class Finding:
    check: str
    severity: Literal['FAIL', 'DEFECT', 'INFO']
    trial: str
    seq: int | None
    detail: dict


@dataclass(frozen=True)
class VerifyReport:
    trial: str
    mode: Literal['plumbing', 'full']
    verdict: Literal['PASS', 'FAIL']
    findings: list[Finding]
    counts: dict[str, int]

    def to_json(self) -> dict:
        return {
            'trial': self.trial, 'mode': self.mode, 'verdict': self.verdict,
            'counts': dict(sorted(self.counts.items())),
            'findings': [{'check': f.check, 'severity': f.severity, 'trial': f.trial,
                          'seq': f.seq, 'condition_list': condition_list(f.check),
                          'detail': f.detail} for f in self.findings],
        }


# ---------------------------------------------------------------------------
# the third, naive band
# ---------------------------------------------------------------------------
def _band_independent(n: int, s_lower: float, s_upper: float, alpha_gate: float,
                      rho: float, clip_lo: float = -1.0,
                      clip_hi: float = 1.0) -> tuple[float, float, float]:
    """A deliberately naive re-implementation of protocol 8.2, in a Python loop, calling
    winstats.normal_mixture_radius directly.  Returns (radius, L, U)."""
    if n < 1:
        raise ValueError('n >= 1 required')
    r = float(winstats.normal_mixture_radius(n, alpha=alpha_gate, rho=rho,
                                             variance_process=n))
    lo = s_lower / n - r
    hi = s_upper / n + r
    if lo < clip_lo:
        lo = clip_lo
    if hi > clip_hi:
        hi = clip_hi
    return r, lo, hi


def _binom_two_sided_p(k: int, n: int) -> float:
    """Exact two-sided binomial p-value at p = 1/2, without scipy."""
    if n <= 0:
        return 1.0
    target = math.comb(n, k)
    total = sum(math.comb(n, i) for i in range(n + 1) if math.comb(n, i) <= target)
    return min(1.0, total / (2.0 ** n))


# ---------------------------------------------------------------------------
# collector
# ---------------------------------------------------------------------------
@dataclass
class _Collector:
    trial: str
    mode: str
    findings: list[Finding] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)

    def add(self, check: str, detail: dict, *, seq: int | None = None,
            severity: str | None = None) -> None:
        sev = severity or CHECK_SEVERITY[check]
        self.seen.add(check)
        if self.mode == 'plumbing' and not plumbing_allows(check):
            return
        self.findings.append(Finding(check=check, severity=sev, trial=self.trial,  # type: ignore[arg-type]
                                     seq=seq, detail=detail))

    def ok(self, check: str, detail: dict | None = None) -> None:
        """Record that a check ran and passed; PASS rows carry severity INFO and are not
        findings against the chain."""
        self.seen.add(check)


# ---------------------------------------------------------------------------
# helpers over a parsed chain
# ---------------------------------------------------------------------------
_ORDER_SLOT_KEYS = ('pair', 'stratum', 'arrivals', 'uids')


def _order_slots(doc: object) -> "list[dict] | None":
    """The pair slots of an arrival-order document, or None if the shape is unknown.

    D2 REPAIR (root 2026-09-21 18:54, ranked item 1).  Three shapes exist in this
    repository and the verifier must read the two the PRODUCTION writers emit:

      * a bare list of slots                       -- dryrun_live_ab.py only
      * {'schema', 'n_pairs', 'pairs', ...}        -- lab_design.write_order
      * the protocol-complete document with the same 'pairs' key
                                                   -- lab_design.write_order_document

    Returning None is a REFUSAL, not an empty result: the caller records an
    unsupported-document defect rather than passing a check it did not run.  A
    document whose declared ``n_pairs`` disagrees with the length of its own
    ``pairs`` list is also refused -- an internally inconsistent freeze artifact
    must not be silently read past.
    """
    if isinstance(doc, list):
        slots = doc
    elif isinstance(doc, dict):
        slots = doc.get('pairs')
        if not isinstance(slots, list):
            return None
        declared = doc.get('n_pairs')
        if isinstance(declared, int) and declared != len(slots):
            return None
    else:
        return None
    for slot in slots:
        if not isinstance(slot, dict) or any(k not in slot for k in _ORDER_SLOT_KEYS):
            return None
    return list(slots)


def _by_type(events: Sequence[Mapping], etype: str) -> list[Mapping]:
    return [e for e in events if e['type'] == etype]


def server_start_kind(events: Sequence[Mapping]) -> str:
    """Whether a trial chain's server starts are ``'simulated'``, ``'live'``, ``'mixed'`` or
    ``'none'`` (repair contract EB1 item 8).

    Decided by ``lab_eventlog.is_sim_server_body`` -- the pid-0 / sentinel-digest shape of the
    simulated body -- over every ``server_started`` and ``server_restarted`` body, and NEVER
    by the bodies' own ``props_matches_golden`` / ``receipt_matches_golden`` flags, which are
    the claims a lifecycle check exists to test.  ``'mixed'`` is itself a defect: no
    invocation both simulates and starts a server."""
    bodies = [e['body'] for e in events
              if e.get('type') in ('server_started', 'server_restarted')]
    if not bodies:
        return 'none'
    sim = [lab_eventlog.is_sim_server_body(b) for b in bodies]
    if all(sim):
        return 'simulated'
    if not any(sim):
        return 'live'
    return 'mixed'


#: The two events that answer a ``server_down`` or a ``server_start_failed`` for every server.
_LIFECYCLE_STOPS: tuple[str, ...] = ('trial_paused', 'trial_aborted')

#: ``trial_aborted.reason`` that must answer a FIRST start's ``server_start_failed``, by its
#: stage: ``lab_orchestrator.START_FAILURE_REASON``, transcribed because the isolation matrix
#: (ARCHITECTURE_FINAL.md 3.16) forbids this module to import the orchestrator;
#: ``tests_eb1_supervision`` asserts the two maps are equal.
FIRST_START_ABORT_REASON: dict[str, str] = {
    'gguf': 'server_identity', 'serving_manifest': 'server_identity',
    'identity': 'server_identity', 'smoke': 'receipt_mismatch',
    'launch': 'infrastructure', 'health': 'infrastructure',
}


def _config_is_mock(cfg: Mapping | None) -> bool:
    """Whether the FROZEN configuration marks its tree a dry run: the same rule as the
    results builder's MOCK banner (``mock`` or ``mock_overrides`` present and truthy)."""
    cfg = cfg or {}
    return bool(cfg.get('mock') or cfg.get('mock_overrides'))


def _answer_after(events: Sequence[Mapping], index: int, answers) -> str:
    """Scan forward from ``events[index]``: ``'answered'`` when an event ``answers(ev)``
    accepts comes first, ``'dispatched'`` when an ``episode_started`` comes first, and
    ``'open'`` when the chain ends with neither."""
    for later in events[index + 1:]:
        if answers(later):
            return 'answered'
        if later['type'] == 'episode_started':
            return 'dispatched'
    return 'open'


def _check_server_lifecycle(col: _Collector, events: Sequence[Mapping],
                            cfg: Mapping | None) -> None:
    """``server.lifecycle`` (FAIL; repair contract EB1 item 5): the server lifecycle of a
    NON-SIMULATED chain, read from the chain and the frozen configuration alone.

    Skipped (passed) only when every ``server_started`` / ``server_restarted`` body is the
    simulated one (``server_start_kind``, decided by the sentinel digests, never by the flags
    under test) AND the frozen configuration marks the tree a dry run (``mock`` or
    ``mock_overrides``, the results builder's MOCK rule).  A simulated chain under a
    configuration that is not a dry run FAILS (``simulated_under_live_config``): the
    sentinels are values the chain writer controls, so they alone may not switch the check
    off (EB1 fix, reviewer 1 finding 5).  A chain mixing simulated and live bodies fails.
    What it performs:

    1. ``verified_start``: every live ``server_started`` / ``server_restarted`` carries
       ``props_matches_golden: true`` and a smoke with ``receipt_matches_golden: true`` and
       ``ok: true``, AND its ``props_sha256`` is the golden digest of that server, as
       recorded by the chain's ``trial_started.golden_props_sha256`` and by the frozen
       ``config.receipt.golden_props_sha256`` (each that is present must match; the
       orchestrator writes the former from the latter at seq 0).  With neither golden
       digest present (or a non-digest value) every live start fails: nothing could be
       checked against it.  What this rejects: a body whose flags are not all true, and a
       body whose digest is not the frozen golden one -- such as the pre-repair placeholder
       (b049307), which hashed the RAW ``/props`` (``tests_eb1_entry.MutationControl``).
       What it CANNOT detect: a fabricated body that copies the golden digest and sets the
       flags true, whatever the server actually served -- the verifier reads no server and
       has no per-start observation of its own to compare with (EB1 fix, reviewer 2 finding
       2; ``tests_eb1_supervision.VerifiedStartScopeTests`` pins this limit).  That a live
       body came from ``lab_server.start``'s comparisons rests on the orchestrator code (the
       harness pin) and on the EB1c controls, not on this check.
    2. ``down_answered``: every ``server_down`` is followed by a ``server_restarted`` or
       ``server_start_failed`` of the same server, a ``trial_paused`` or a
       ``trial_aborted`` -- and by it BEFORE any further ``episode_started`` (a server that
       is down gets no new work).  A down still unanswered at the end of a chain that is not
       terminal (no ``trial_ended`` / ``trial_aborted``) is pending, not failed.
    3. ``cap``: attempted supervised restarts per server (``server_restarted`` plus
       ``server_start_failed`` with ``kind='restart'``) never exceed the frozen
       ``server_supervision`` cap (read by ``lab_common.server_supervision_cap``).  A chain
       with any restart, ``server_down`` or ``server_restart_cap`` abort whose configuration
       carries no well-formed cap fails: the cap could not be checked.
    4. ``failure_answered``: every ``server_start_failed`` is followed by ``trial_aborted``
       or ``trial_paused`` before any further ``episode_started`` (same pending rule as 2).
       A FIRST start's failure -- ``kind='start'`` before the chain's first
       ``invocation_started``, which only a resumed invocation writes -- must be answered
       by ``trial_aborted`` with the reason :data:`FIRST_START_ABORT_REASON` gives its stage
       (``state: 'wrong_answer'`` otherwise): a pause there would let a resume run the trial
       the live rules had aborted (EB1 fix, reviewer 1 finding 1).
    5. ``cap_abort_iff_required``: ``trial_aborted(server_restart_cap)`` exists IFF some
       ``server_down`` found its server's attempted restarts already at the cap (a restart
       beyond the cap would have been required); on a chain that is not yet terminal only the
       "if" direction is enforced.

    What it does NOT perform: it never re-derives a start's comparisons from a server (the
    verifier reads no server); it does not check pids against a process table."""
    check = 'server.lifecycle'
    events = list(events)
    kind = server_start_kind(events)
    if kind == 'simulated':
        if _config_is_mock(cfg):
            col.ok(check)
            return
        col.add(check, {'rule': 'simulated_under_live_config',
                        'error': 'simulated server bodies under a configuration that is '
                                 'not a dry run'})
    if kind == 'mixed':
        col.add(check, {'rule': 'mixed',
                        'error': 'simulated and live server bodies in one chain'})
    terminal = any(e['type'] in ('trial_ended', 'trial_aborted') for e in events)
    # the golden /props digests a live start must carry: the chain's own trial_started
    # record and the frozen configuration, each wherever it is present
    golden_sources: list[Mapping] = []
    opened = next((e['body'] for e in events if e['type'] == 'trial_started'), None)
    for source in ((opened or {}).get('golden_props_sha256'),
                   ((cfg or {}).get('receipt') or {}).get('golden_props_sha256')):
        if isinstance(source, Mapping):
            golden_sources.append(source)

    for ev in events:
        if ev['type'] not in ('server_started', 'server_restarted'):
            continue
        body = ev['body']
        if lab_eventlog.is_sim_server_body(body):
            continue
        smoke = body.get('smoke') if isinstance(body.get('smoke'), Mapping) else {}
        wants = [src.get(str(body.get('server_id'))) for src in golden_sources]
        is_golden = bool(wants) and all(
            isinstance(w, str) and len(w) == 64 and body.get('props_sha256') == w
            for w in wants)
        if not (body.get('props_matches_golden') is True
                and smoke.get('receipt_matches_golden') is True
                and smoke.get('ok') is True and is_golden):
            col.add(check, {'rule': 'verified_start', 'type': ev['type'],
                            'server_id': str(body.get('server_id')),
                            'props_sha256_is_golden': bool(is_golden)}, seq=ev['seq'])

    for i, ev in enumerate(events):
        if ev['type'] == 'server_down':
            sid = ev['body'].get('server_id')
            state = _answer_after(events, i, lambda e, sid=sid: (
                e['type'] in _LIFECYCLE_STOPS
                or (e['type'] in ('server_restarted', 'server_start_failed')
                    and e['body'].get('server_id') == sid)))
            if state == 'dispatched' or (state == 'open' and terminal):
                col.add(check, {'rule': 'down_answered', 'server_id': str(sid),
                                'state': state}, seq=ev['seq'])
        elif ev['type'] == 'server_start_failed':
            state = _answer_after(events, i, lambda e: e['type'] in _LIFECYCLE_STOPS)
            first_start = (ev['body'].get('kind') == 'start' and not any(
                e['type'] == 'invocation_started' for e in events[:i]))
            if state == 'answered' and first_start:
                answer = next(e for e in events[i + 1:] if e['type'] in _LIFECYCLE_STOPS)
                want = FIRST_START_ABORT_REASON.get(str(ev['body'].get('stage')))
                if answer['type'] != 'trial_aborted' \
                        or answer['body'].get('reason') != want:
                    state = 'wrong_answer'
            if state in ('dispatched', 'wrong_answer') or (state == 'open' and terminal):
                col.add(check, {'rule': 'failure_answered',
                                'server_id': str(ev['body'].get('server_id')),
                                'state': state}, seq=ev['seq'])

    cap_aborts = [e for e in events if e['type'] == 'trial_aborted'
                  and e['body'].get('reason') == 'server_restart_cap']
    relevant = cap_aborts or any(
        e['type'] in ('server_down', 'server_restarted')
        or (e['type'] == 'server_start_failed' and e['body'].get('kind') == 'restart')
        for e in events)
    try:
        cap: int | None = lab_common.server_supervision_cap(cfg or {})
        problem = ''
    except lab_common.FrozenMismatch as exc:
        cap, problem = None, str(exc)
    if cap is None:
        if relevant:
            col.add(check, {'rule': 'cap', 'error': 'the frozen restart cap is unreadable, '
                            'so the restarts of this chain could not be checked',
                            'problem': problem})
        col.ok(check)
        return
    restarts: dict = {}
    required: list[int] = []
    for ev in events:
        etype = ev['type']
        body = ev['body']
        sid = str(body.get('server_id'))
        if etype == 'server_down':
            if restarts.get(sid, 0) >= cap:
                required.append(int(ev['seq']))
        elif etype == 'server_restarted' or (etype == 'server_start_failed'
                                             and body.get('kind') == 'restart'):
            restarts[sid] = restarts.get(sid, 0) + 1
            if restarts[sid] > cap:
                col.add(check, {'rule': 'cap', 'server_id': sid,
                                'restarts': restarts[sid], 'cap': cap}, seq=ev['seq'])
    if cap_aborts and not required:
        col.add(check, {'rule': 'cap_abort_iff_required', 'required': 0,
                        'cap_aborts': len(cap_aborts)}, seq=cap_aborts[0]['seq'])
    if required and terminal and not cap_aborts:
        col.add(check, {'rule': 'cap_abort_iff_required', 'required': len(required),
                        'cap_aborts': 0}, seq=required[0])
    col.ok(check)


# The two closed vocabularies of the host-scan records, read off the schema itself so the
# verifier cannot drift away from what the log is allowed to contain.
HOST_DETECTORS: frozenset[str] = frozenset(
    EVENT_SCHEMA['foreign_load_detected']['findings'].item.fields['detector'].enum)
HOST_DEGRADED_CAUSES: frozenset[str] = frozenset(
    EVENT_SCHEMA['foreign_load_detected']['degraded'].item.fields['cause'].enum)


def _check_host_scans(col: _Collector, events: Sequence[Mapping], etype: str, *,
                      refusal: bool = False) -> None:
    """protocol 5.7: the host-quiescence records of one chain.

    Two separate questions.  `host.record` asks whether the record is internally honest --
    `clean` must be exactly "no findings and no degraded cause", because `clean` is the
    field a reader trusts and a chain that sets it while carrying offenders is worse than
    one that carries no scan at all.  `host.quiescence` then reports what was actually
    seen: a named foreign consumer, or a scan that could not establish quiescence.

    With `refusal=True` the records are trial-start refusals in the program chain.  Those
    carry offenders by construction -- that is why they exist -- so the contention rows are
    emitted at INFO: the gate refusing a trial is the gate working, not a defect in a
    trial's chain.  The consistency half still applies in full."""
    for ev in _by_type(events, etype):
        body = ev['body']
        findings = list(body.get('findings') or [])
        degraded = list(body.get('degraded') or [])
        if bool(body.get('clean')) != (not findings and not degraded):
            col.add('host.record',
                    {'type': etype, 'clean': bool(body.get('clean')),
                     'n_findings': len(findings), 'n_degraded': len(degraded),
                     'error': 'clean disagrees with the findings it carries'},
                    seq=ev['seq'])
        if int(body.get('scanned', 0)) < 0 or int(body.get('allowlisted', 0)) < 0:
            col.add('host.record', {'type': etype, 'error': 'negative count'},
                    seq=ev['seq'])
        for finding in findings:
            if finding.get('detector') not in HOST_DETECTORS:
                col.add('host.record',
                        {'type': etype, 'error': 'detector outside the closed vocabulary',
                         'detector': str(finding.get('detector'))}, seq=ev['seq'])
        for row in degraded:
            if row.get('cause') not in HOST_DEGRADED_CAUSES:
                col.add('host.record',
                        {'type': etype, 'error': 'degraded cause outside the closed '
                                                 'vocabulary',
                         'cause': str(row.get('cause'))}, seq=ev['seq'])
        severity = 'INFO' if refusal else None
        if findings:
            col.add('host.quiescence',
                    {'type': etype, 'point': str(body.get('point')),
                     'n_findings': len(findings),
                     'detectors': ','.join(sorted({str(f.get('detector'))
                                                   for f in findings})),
                     'max_elapsed_s': max(int(f.get('elapsed_s', 0)) for f in findings)},
                    seq=ev['seq'], severity=severity)
        if degraded:
            col.add('host.quiescence',
                    {'type': etype, 'point': str(body.get('point')),
                     'error': 'quiescence could not be established',
                     'causes': ','.join(sorted(str(r.get('cause')) for r in degraded))},
                    seq=ev['seq'], severity=severity)
    col.ok('host.record')
    col.ok('host.quiescence')


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _final_scores(cand: Mapping, inc: Mapping, tol: float) -> tuple[int, int, int]:
    """(z, decisive_tier, d) from two revealed outcomes, through winstats.compare only."""
    both = bool(cand['success']) and bool(inc['success'])
    tiers = [winstats.Tier('success'),
             winstats.Tier('cost', higher_better=False, relative_tolerance=tol)]
    z, tier = winstats.compare(
        np.asarray([float(cand['success']), float(cand['latency_s'])]),
        np.asarray([float(inc['success']), float(inc['latency_s'])]),
        tiers, eligible=np.asarray([True, both]))
    return (int(np.asarray(z).reshape(())[()]),
            int(np.asarray(tier).reshape(())[()]),
            int(cand['success']) - int(inc['success']))


# ---------------------------------------------------------------------------
# the trial verifier
# ---------------------------------------------------------------------------
def verify_trial(trial: str, freeze_bundle_sha256: str, *, mode: str = 'full',
                 results_root: Path | None = None,
                 work_root: Path | None = None) -> VerifyReport:
    saved_roster = lab_eventlog.roster_uids()
    try:
        return _verify_trial(trial, freeze_bundle_sha256, mode=mode,
                             results_root=results_root, work_root=work_root)
    finally:
        lab_eventlog.set_roster_uids(saved_roster)


def _verify_trial(trial: str, freeze_bundle_sha256: str, *, mode: str = 'full',
                  results_root: Path | None = None,
                  work_root: Path | None = None) -> VerifyReport:
    if mode not in ('plumbing', 'full'):
        raise ValueError("mode must be 'plumbing' or 'full'")
    rroot = Path(results_root) if results_root is not None else RESULTS_ROOT
    wroot = Path(work_root) if work_root is not None else None
    col = _Collector(trial=trial, mode=mode)
    events_dir = rroot / trial / 'events'
    freeze_dir = rroot / 'freeze'
    cfg = _load_json(freeze_dir / 'config.json')
    if not isinstance(cfg, dict):
        cfg = None

    # Task uids are string form (e) of protocol 12.2: the validator checks MEMBERSHIP in
    # roster.json, not merely the shape, so the roster is installed before any parse.
    roster = _load_json(freeze_dir / 'roster.json')
    if isinstance(roster, dict) and isinstance(roster.get('tasks'), list):
        lab_eventlog.set_roster_uids(
            [t if isinstance(t, str) else t.get('uid') for t in roster['tasks']])

    # ---- chain.read / chain.byte_identity / chain.segments -----------------
    try:
        read = read_chain(events_dir, trial, freeze_bundle_sha256)
    except ChainError as exc:
        col.add('chain.read', {'error': str(exc)})
        return _finish(col, trial, mode)
    col.ok('chain.read')
    events = read.events
    if not events:
        col.add('chain.read', {'skipped': 'the trial chain holds no event'},
                severity='INFO')
        return _finish(col, trial, mode)

    for idx, path in enumerate(read.segments):
        raw = path.read_bytes()
        rebuilt = b''
        for line in raw.split(b'\n'):
            if not line:
                continue
            try:
                ev = json.loads(line.decode('utf-8'))
            except Exception:
                continue
            if canonical_json(ev).encode('utf-8') != line:
                col.add('chain.byte_identity', {'segment': idx, 'bytes': len(line)})
    col.ok('chain.byte_identity')

    if events:
        want = genesis_prev(freeze_bundle_sha256, trial)
        if events[0]['prev'] != want:
            col.add('chain.genesis', {'found': events[0]['prev'], 'expected': want}, seq=0)
    col.ok('chain.genesis')

    for idx, path in enumerate(read.segments[:-1]):
        tail = path.read_bytes().rstrip(b'\n').rsplit(b'\n', 1)[-1]
        try:
            last = json.loads(tail.decode('utf-8'))
        except Exception:
            last = {}
        if last.get('type') != 'anchor':
            col.add('chain.segments', {'segment': idx, 'last_type': str(last.get('type'))})
    col.ok('chain.segments')

    if read.torn is not None:
        col.add('chain.torn', {'segment': read.torn.segment, 'offset': read.torn.offset,
                               'length': read.torn.length,
                               'is_event_prefix': read.torn.is_event_prefix,
                               'sha256': read.torn.sha256})
    col.ok('chain.torn')

    # ---- schema.all --------------------------------------------------------
    for ev in events:
        try:
            validate_event(ev['type'], ev['body'])
        except SchemaError as exc:
            col.add('schema.all', {'type': ev['type'], 'error': str(exc)}, seq=ev['seq'])
    col.ok('schema.all')

    started = _by_type(events, 'trial_started')
    if len(started) != 1 or started[0]['seq'] != 0:
        col.add('order.freeze_hashes',
                {'trial_started_count': len(started), 'error': 'trial_started must be seq 0'})
    ts = started[0]['body'] if started else {}

    # ---- order.freeze_hashes ----------------------------------------------
    if ts:
        if ts.get('freeze_bundle_sha256') != freeze_bundle_sha256:
            col.add('order.freeze_hashes', {'field': 'freeze_bundle_sha256',
                                            'found': str(ts.get('freeze_bundle_sha256')),
                                            'expected': freeze_bundle_sha256}, seq=0)
        checks = [('config_sha256', freeze_dir / 'config.json'),
                  ('roster_sha256', freeze_dir / 'roster.json'),
                  ('order_sha256', freeze_dir / f'arrival_order_{trial}.json')]
        for fieldname, path in checks:
            if path.exists():
                want = sha256_file(path)
                if ts.get(fieldname) != want:
                    col.add('order.freeze_hashes',
                            {'field': fieldname, 'found': str(ts.get(fieldname)),
                             'expected': want}, seq=0)
        wpath = SRC_DIR / 'winstats.py'
        if wpath.exists() and ts.get('winstats_sha256') != sha256_file(wpath):
            col.add('order.freeze_hashes', {'field': 'winstats_sha256',
                                            'found': str(ts.get('winstats_sha256')),
                                            'expected': sha256_file(wpath)}, seq=0)
    col.ok('order.freeze_hashes')

    # ---- order.enrollment --------------------------------------------------
    enrolls = [e for e in _by_type(events, 'pair_enrolled')
               if not e['body'].get('re_enrolled')]
    # D2 REPAIR, root 2026-09-21 18:54 ranked item 1: "Read and validate the actual
    # dict-format arrival-order document emitted by the production writer ... Never
    # mark a skipped comparison as passed."
    #
    # THE DEFECT: this block used to be guarded by `if isinstance(order, list):`.
    # BOTH production writers emit a DICT -- `write_order` writes
    # {schema, n_pairs, pairs, order_sha256} and `write_order_document` writes the
    # protocol-complete document (lab_design.py:146-155).  Only dryrun's bare-list
    # form entered the branch.  So on every real freeze the per-pair comparison was
    # skipped entirely while `col.ok('order.enrollment')` fired below regardless: a
    # trial that enrolled the wrong uids, the wrong arrivals or the wrong stratum
    # verified CLEAN.  The mock was checked and the real thing was not.
    order_doc = _load_json(freeze_dir / f'arrival_order_{trial}.json')
    slots = _order_slots(order_doc)
    if slots is None:
        # A shape we do not understand is a REFUSAL, never a silent pass.
        col.add('order.enrollment',
                {'unsupported_order_document': type(order_doc).__name__,
                 'reason': 'arrival order is missing, malformed, or not a '
                           'recognised list/dict document; the enrollment '
                           'comparison could not be performed and is NOT passed'})
        slots = []
    else:
        if len(enrolls) > len(slots):
            col.add('order.enrollment', {'enrolled': len(enrolls), 'order': len(slots)})
        for i, ev in enumerate(enrolls):
            if i >= len(slots):
                break
            want = slots[i]
            b = ev['body']
            if int(b['pair']) != int(want['pair']) \
                    or list(b['arrivals']) != list(want['arrivals']) \
                    or list(b['task_uids']) != list(want['uids']) \
                    or b['stratum'] != want['stratum']:
                col.add('order.enrollment', {'pair': int(b['pair']), 'index': i},
                        seq=ev['seq'])
    for i, ev in enumerate(enrolls):
        if int(ev['body']['pair']) != i + 1:
            col.add('order.enrollment',
                    {'pair': int(ev['body']['pair']), 'expected': i + 1}, seq=ev['seq'])
    col.ok('order.enrollment')

    # ---- coin.* ------------------------------------------------------------
    decision_events = _by_type(events, 'decision')
    decision_seq = decision_events[0]['seq'] if decision_events else None
    start_receipt_seq: int | None = None
    for ev in events:
        if ev['type'] == 'anchor_receipt':
            start_receipt_seq = ev['seq']
            break
    coins = _by_type(events, 'coin_drawn')
    per_pair: dict[int, int] = {}
    for ev in coins:
        p = int(ev['body']['pair'])
        per_pair[p] = per_pair.get(p, 0) + 1
        if per_pair[p] > 1:
            col.add('coin.one_per_pair', {'pair': p, 'count': per_pair[p]}, seq=ev['seq'])
        if decision_seq is not None and ev['seq'] > decision_seq:
            col.add('coin.one_per_pair', {'pair': p, 'after_decision': True}, seq=ev['seq'])
        if start_receipt_seq is not None and ev['seq'] < start_receipt_seq:
            col.add('coin.one_per_pair', {'pair': p, 'before_start_receipt': True},
                    seq=ev['seq'])
    col.ok('coin.one_per_pair')

    assign_seq_of_arrival: dict[int, int] = {}
    for ev in events:
        if ev['type'] == 'coin_drawn':
            for a in ev['body']['assignment']:
                assign_seq_of_arrival.setdefault(int(a), ev['seq'])
        elif ev['type'] == 'arm_assigned_by_decision':
            assign_seq_of_arrival.setdefault(int(ev['body']['arrival']), ev['seq'])
    for ev in _by_type(events, 'episode_started'):
        a = int(ev['body']['arrival'])
        aseq = assign_seq_of_arrival.get(a)
        if aseq is None or aseq >= ev['seq'] or int(ev['body']['assignment_seq']) != aseq:
            col.add('coin.write_ahead',
                    {'arrival': a, 'assignment_seq': int(ev['body']['assignment_seq']),
                     'found': -1 if aseq is None else aseq}, seq=ev['seq'])
    col.ok('coin.write_ahead')

    ones = sum(int(ev['body']['bit']) for ev in coins)
    col.add('coin.balance', {'n': len(coins), 'ones': ones,
                             'p_two_sided': _binom_two_sided_p(ones, len(coins))})

    # ---- episode.* ---------------------------------------------------------
    reveals = _by_type(events, 'episode_revealed')
    reveal_count: dict[int, int] = {}
    for ev in reveals:
        a = int(ev['body']['arrival'])
        reveal_count[a] = reveal_count.get(a, 0) + 1
        if reveal_count[a] > 1:
            col.add('episode.one_reveal', {'arrival': a, 'count': reveal_count[a]},
                    seq=ev['seq'])
    terminal_trial = any(e['type'] in ('trial_ended', 'trial_aborted') for e in events)
    if terminal_trial:
        for a in assign_seq_of_arrival:
            if reveal_count.get(a, 0) == 0:
                col.add('episode.one_reveal', {'arrival': a, 'count': 0})
    col.ok('episode.one_reveal')

    if wroot is None:
        col.add('episode.record_match', {'skipped': 'no work root supplied'},
                severity='INFO')
    else:
        rec_dir = Path(wroot) / trial / 'records'
        for ev in reveals:
            digest = ev['body']['record_sha256']
            path = rec_dir / f'{digest}.json'
            if not path.exists():
                col.add('episode.record_match',
                        {'arrival': int(ev['body']['arrival']), 'error': 'record missing'},
                        seq=ev['seq'])
                continue
            if sha256_file(path) != digest:
                col.add('episode.record_match',
                        {'arrival': int(ev['body']['arrival']),
                         'error': 'record does not re-hash to record_sha256'}, seq=ev['seq'])
                continue
            rec = _load_json(path)
            if isinstance(rec, dict) and isinstance(rec.get('outcome'), dict):
                if canonical_json(rec['outcome']) != canonical_json(ev['body']['outcome']):
                    col.add('episode.record_match',
                            {'arrival': int(ev['body']['arrival']),
                             'error': 'outcome differs from the hashed record'},
                            seq=ev['seq'])
    col.ok('episode.record_match')

    accepted = {int(e['body']['arrival']) for e in _by_type(events, 'job_accepted')}
    for ev in _by_type(events, 'episode_started'):
        a = int(ev['body']['arrival'])
        if a not in accepted and not ev['body'].get('started_after_resume'):
            col.add('episode.job_accepted', {'arrival': a}, seq=ev['seq'])
    col.ok('episode.job_accepted')

    # ---- calls.one_terminal / seeds.unique ---------------------------------
    requests: dict[str, int] = {}
    terminals: dict[str, int] = {}
    for ev in events:
        if ev['type'] == 'llm_request':
            rid = ev['body']['request_id']
            requests[rid] = requests.get(rid, 0) + 1
        elif ev['type'] in ('llm_response', 'llm_error'):
            rid = ev['body']['request_id']
            terminals[rid] = terminals.get(rid, 0) + 1
    terminal_arrivals = {int(e['body']['arrival']) for e in reveals
                         if e['body']['outcome'].get('error_class') in
                         ('worker_died', 'episode_timeout', 'interrupted')}
    for ev in _by_type(events, 'llm_request'):
        rid = ev['body']['request_id']
        got = terminals.get(rid, 0)
        if got > 1:
            col.add('calls.one_terminal', {'request_id': rid, 'terminals': got},
                    seq=ev['seq'])
        elif got == 0 and int(ev['body']['arrival']) not in terminal_arrivals:
            col.add('calls.one_terminal', {'request_id': rid, 'terminals': 0},
                    seq=ev['seq'])
    for rid, k in requests.items():
        if k > 1:
            col.add('calls.one_terminal', {'request_id': rid, 'requests': k})
    col.ok('calls.one_terminal')

    seeds: dict[int, int] = {}
    for ev in _by_type(events, 'llm_request'):
        s = int(ev['body']['seed'])
        if s == 0xFFFFFFFF:
            col.add('seeds.unique', {'seed': s, 'error': 'forbidden seed'}, seq=ev['seq'])
        seeds[s] = seeds.get(s, 0) + 1
        if seeds[s] > 1:
            col.add('seeds.unique', {'seed': s, 'count': seeds[s]}, seq=ev['seq'])
    col.ok('seeds.unique')

    # ---- the monitor block -------------------------------------------------
    updates = _by_type(events, 'monitor_update')
    looks: list[lab_reference_rule.RefLook] | None = None
    ref_error: str | None = None
    if cfg is None:
        ref_error = 'freeze/config.json is missing'
    else:
        try:
            looks = lab_reference_rule.looks_from_chain(events, cfg, trial)
        except Exception as exc:
            ref_error = f'{type(exc).__name__}: {exc}'

    if ref_error is not None:
        for check in ('monitor.cadence', 'reference_rule.agreement',
                      'monitor.first_crossing'):
            col.add(check, {'error': ref_error})
    else:
        assert looks is not None
        got = [u['body']['trigger'] for u in updates]
        want = [lk.trigger for lk in looks]
        if got != want:
            col.add('monitor.cadence',
                    {'logged': len(got), 'expected': len(want),
                     'first_difference': next((i for i in range(max(len(got), len(want)))
                                               if got[i:i + 1] != want[i:i + 1]), -1)})
        for ev in events:
            if ev['type'] == 'metrics_scrape':
                nxt = events[ev['seq'] + 1] if ev['seq'] + 1 < len(events) else None
                if nxt is not None and nxt['type'] == 'monitor_update' \
                        and nxt['body']['trigger'] not in ('enroll', 'reveal', 'call',
                                                           'resume', 'drain'):
                    col.add('monitor.cadence', {'error': 'update at a metrics_scrape'},
                            seq=ev['seq'])
    col.ok('monitor.cadence')

    for i, u in enumerate(updates):
        b = u['body']
        sh = b.get('shadow')
        if not isinstance(sh, dict):
            col.add('monitor.shadow', {'error': 'no shadow object'}, seq=u['seq'])
            continue
        # The shadow must be what the reference rule actually computes at that look, and
        # `mismatch` must be true whenever it differs from the live body beyond 1e-9
        # (protocol 8.9).  A shadow that merely asserts agreement proves nothing.
        if ref_error is None and looks is not None and i < len(looks):
            lk = looks[i]
            if int(sh.get('n', -1)) != lk.n:
                col.add('monitor.shadow', {'field': 'n', 'logged': int(sh.get('n', -1)),
                                           'reference': lk.n}, seq=u['seq'])
            for name, ref_val in (('L_h', lk.L_h), ('U_h', lk.U_h), ('L_s', lk.L_s),
                                  ('U_s', lk.U_s)):
                if abs(float(sh.get(name, 0.0)) - ref_val) > 1e-9:
                    col.add('monitor.shadow',
                            {'field': name, 'logged': float(sh.get(name, 0.0)),
                             'reference': ref_val}, seq=u['seq'])
            if sh.get('action') != lk.action:
                col.add('monitor.shadow', {'field': 'action',
                                           'logged': str(sh.get('action')),
                                           'reference': lk.action}, seq=u['seq'])
            # protocol 8.9 lists the comparison in full: `n`, a score, an enclosure
            # endpoint, a band endpoint beyond 1e-9, or the action.  The SUMS are in it,
            # because a band saturated at the clip can hide a wrong score.
            deltas = {k: abs(float(b[k]) - v) for k, v in
                      (('sum_lower_h', lk.sum_lower_h), ('sum_upper_h', lk.sum_upper_h),
                       ('sum_lower_s', lk.sum_lower_s), ('sum_upper_s', lk.sum_upper_s),
                       ('radius', lk.radius), ('L_h', lk.L_h), ('U_h', lk.U_h),
                       ('L_s', lk.L_s), ('U_s', lk.U_s))}
            worst = max(deltas, key=lambda k: deltas[k])
            differs = int(b['n']) != lk.n or deltas[worst] > 1e-9
            if differs and not sh.get('mismatch'):
                col.add('monitor.shadow',
                        {'error': 'the live monitor differs from the reference rule but '
                                  'mismatch is false', 'n': int(b['n']),
                         'field': worst, 'delta': deltas[worst]}, seq=u['seq'])
        if sh.get('mismatch'):
            later = [e for e in events if e['seq'] > u['seq']]
            paused = next((e for e in later if e['type'] == 'trial_paused'
                           and e['body']['reason_code'] == 'monitor_mismatch'), None)
            decided = next((e for e in later if e['type'] == 'decision'), None)
            if paused is None or (decided is not None and decided['seq'] < paused['seq']):
                col.add('monitor.shadow',
                        {'error': 'mismatch not followed by trial_paused(monitor_mismatch) '
                                  'before a decision'}, seq=u['seq'])
    col.ok('monitor.shadow')

    if cfg is not None:
        alpha_gate = float(cfg['monitor']['alpha_gate'])
        rho = float(cfg['monitor']['rho'])
        for u in updates:
            b = u['body']
            r, lo_h, hi_h = _band_independent(int(b['n']), float(b['sum_lower_h']),
                                              float(b['sum_upper_h']), alpha_gate, rho)
            _, lo_s, hi_s = _band_independent(int(b['n']), float(b['sum_lower_s']),
                                              float(b['sum_upper_s']), alpha_gate, rho)
            for name, mine, logged in (('radius', r, float(b['radius'])),
                                       ('L_h', lo_h, float(b['L_h'])),
                                       ('U_h', hi_h, float(b['U_h'])),
                                       ('L_s', lo_s, float(b['L_s'])),
                                       ('U_s', hi_s, float(b['U_s']))):
                if abs(mine - logged) > 1e-12:
                    col.add('monitor.independent_band',
                            {'field': name, 'independent': mine, 'logged': logged},
                            seq=u['seq'])
            if lab_monitor is not None:
                try:
                    mc = lab_monitor.MonitorConfig.from_config(cfg, trial)
                    bh = lab_monitor.band(int(b['n']), float(b['sum_lower_h']),
                                          float(b['sum_upper_h']), mc)
                    if abs(bh.lo - lo_h) > 1e-12 or abs(bh.hi - hi_h) > 1e-12:
                        col.add('monitor.independent_band',
                                {'field': 'lab_monitor.band', 'independent_lo': lo_h,
                                 'monitor_lo': float(bh.lo)}, seq=u['seq'])
                except Exception as exc:
                    col.add('monitor.independent_band',
                            {'error': f'{type(exc).__name__}: {exc}'}, seq=u['seq'])
    else:
        col.add('monitor.independent_band', {'error': 'freeze/config.json is missing'})
    col.ok('monitor.independent_band')

    if lab_monitor is None:
        col.add('monitor.replay', {'error': 'lab_monitor is not importable'})
    elif cfg is None:
        col.add('monitor.replay', {'error': 'freeze/config.json is missing'})
    else:
        try:
            snaps = lab_monitor.replay(events, cfg, trial)
        except Exception as exc:
            snaps = None
            col.add('monitor.replay', {'error': f'{type(exc).__name__}: {exc}'})
        if snaps is not None:
            if len(snaps) != len(updates):
                col.add('monitor.replay', {'replayed': len(snaps), 'logged': len(updates)})
            for i, (snap, u) in enumerate(zip(snaps, updates)):
                b = u['body']
                for key in ('n', 'n_collapsed'):
                    if key in snap and int(snap[key]) != int(b[key]):
                        col.add('monitor.replay', {'index': i, 'field': key},
                                seq=u['seq'])
                for key in ('sum_lower_h', 'sum_upper_h', 'sum_lower_s', 'sum_upper_s',
                            'radius', 'L_h', 'U_h', 'L_s', 'U_s'):
                    if key in snap and repr(float(snap[key])) != repr(float(b[key])):
                        col.add('monitor.replay', {'index': i, 'field': key},
                                seq=u['seq'])
    col.ok('monitor.replay')

    # ---- reference_rule.agreement / first crossing -------------------------
    if ref_error is None and cfg is not None:
        ref = lab_reference_rule.decide_from_chain(events, cfg, trial)
        if decision_events:
            d = decision_events[0]['body']
            if ref['kind'] != d['kind'] or ref['n'] != int(d['n']):
                col.add('reference_rule.agreement',
                        {'live_kind': d['kind'], 'live_n': int(d['n']),
                         'reference_kind': str(ref['kind']),
                         'reference_n': -1 if ref['n'] is None else int(ref['n']),
                         'consequence': 'LIVE_DECISION_INVALID'},
                        seq=decision_events[0]['seq'])
        elif ref['kind'] != 'none':
            col.add('reference_rule.agreement',
                    {'live_kind': 'none', 'reference_kind': str(ref['kind']),
                     'reference_n': -1 if ref['n'] is None else int(ref['n']),
                     'consequence': 'LIVE_DECISION_INVALID'})
        assert looks is not None
        if decision_events:
            d = decision_events[0]['body']
            crossing = next((lk for lk in looks if lk.action != 'none'), None)
            if crossing is None or crossing.n != int(d['n']):
                col.add('monitor.first_crossing',
                        {'decision_n': int(d['n']),
                         'first_crossing_n': -1 if crossing is None else crossing.n},
                        seq=decision_events[0]['seq'])
            # ordering invariant 7: the decision is immediately preceded by the
            # monitor_update it quotes, and no earlier update satisfied the rule.
            dseq = decision_events[0]['seq']
            mseq = int(d['monitor_seq'])
            before = next((e for e in events if e['seq'] == dseq - 1), None)
            if before is None or before['type'] != 'monitor_update' or mseq != dseq - 1:
                col.add('monitor.first_crossing',
                        {'error': 'decision does not immediately quote its monitor_update',
                         'monitor_seq': mseq, 'decision_seq': dseq}, seq=dseq)
    col.ok('reference_rule.agreement')
    col.ok('monitor.first_crossing')

    # ---- enclosure.monotone / enclosure.containment ------------------------
    tol = 0.05
    if cfg is not None:
        try:
            tol = float(cfg['hierarchy'][1]['relative_tolerance'])
        except Exception:
            tol = 0.05
    recorded: dict[int, list[tuple[int, list[float], list[float]]]] = {}
    for u in updates:
        b = u['body']
        pu = b.get('pair_updated')
        if pu is None:
            continue
        enc = b['pair_enclosure']
        recorded.setdefault(int(pu), []).append((u['seq'], list(enc['h']), list(enc['s'])))
    for pair, seqs in recorded.items():
        for (s0, h0, d0), (s1, h1, d1) in zip(seqs, seqs[1:]):
            if h1[0] < h0[0] - 1e-12 or h1[1] > h0[1] + 1e-12:
                col.add('enclosure.monotone', {'pair': pair, 'score': 'h'}, seq=s1)
            if d1[0] < d0[0] - 1e-12 or d1[1] > d0[1] + 1e-12:
                col.add('enclosure.monotone', {'pair': pair, 'score': 's'}, seq=s1)
    col.ok('enclosure.monotone')

    pair_of_arrival: dict[int, int] = {}
    for ev in _by_type(events, 'pair_enrolled'):
        for a in ev['body']['arrivals']:
            pair_of_arrival[int(a)] = int(ev['body']['pair'])
    outcomes: dict[int, dict[str, Mapping]] = {}
    for ev in reveals:
        if ev['body'].get('post_decision'):
            continue
        a = int(ev['body']['arrival'])
        p = pair_of_arrival.get(a)
        if p is None:
            continue
        outcomes.setdefault(p, {})[ev['body']['arm']] = ev['body']['outcome']
    for pair, arms in outcomes.items():
        if set(arms) != set(ARMS):
            continue
        z, _, d = _final_scores(arms['candidate'], arms['incumbent'], tol)
        for seq, h, s in recorded.get(pair, []):
            if not (h[0] - 1e-12 <= z <= h[1] + 1e-12):
                col.add('enclosure.containment',
                        {'pair': pair, 'score': 'h', 'final': z, 'lo': h[0], 'hi': h[1],
                         'consequence': 'protocol 6.4 row 24'}, seq=seq)
            if not (s[0] - 1e-12 <= d <= s[1] + 1e-12):
                col.add('enclosure.containment',
                        {'pair': pair, 'score': 's', 'final': d, 'lo': s[0], 'hi': s[1],
                         'consequence': 'protocol 6.4 row 24'}, seq=seq)
    col.ok('enclosure.containment')

    # ---- worktree.integrity -------------------------------------------------
    for ev in events:
        if ev['type'] == 'trial_paused' and ev['body']['reason_code'] == 'worktree_drift':
            digests = ev['body'].get('digests')
            if not digests:
                col.add('worktree.integrity', {'error': 'no digests on a worktree_drift pause'},
                        seq=ev['seq'])
                continue
            resumed = next((e for e in events if e['seq'] > ev['seq']
                            and e['type'] == 'trial_resumed'), None)
            if resumed is not None:
                rd = resumed['body'].get('digests') or []
                if any(x['expected'] != x['observed'] for x in rd):
                    col.add('worktree.integrity',
                            {'error': 'resumed before the digests matched'},
                            seq=resumed['seq'])
    col.ok('worktree.integrity')

    # ---- switch.phase -------------------------------------------------------
    if decision_events:
        dseq = decision_events[0]['seq']
        switches = _by_type(events, 'traffic_switch')
        if switches:
            sw = switches[0]
            receipts = [e for e in events if e['type'] == 'anchor_receipt'
                        and e['seq'] > dseq]
            if not receipts or receipts[0]['seq'] > sw['seq']:
                col.add('switch.phase',
                        {'error': 'traffic_switch does not follow the decision receipt'},
                        seq=sw['seq'])
            first_assigned = next((e for e in events
                                   if e['type'] == 'arm_assigned_by_decision'), None)
            if first_assigned is not None and first_assigned['seq'] < sw['seq']:
                col.add('switch.phase',
                        {'error': 'arm_assigned_by_decision before traffic_switch'},
                        seq=first_assigned['seq'])
        for ev in reveals:
            a = int(ev['body']['arrival'])
            post = bool(ev['body'].get('post_decision'))
            in_pair = a in pair_of_arrival
            if post and in_pair:
                col.add('switch.phase',
                        {'arrival': a,
                         'error': 'a pre-decision pair may not be marked post_decision'},
                        seq=ev['seq'])
            if not post and not in_pair:
                col.add('switch.phase',
                        {'arrival': a,
                         'error': 'a follow-up arrival must be marked post_decision'},
                        seq=ev['seq'])
    col.ok('switch.phase')

    # ---- usage.reconciliation ----------------------------------------------
    for ev in _by_type(events, 'usage_reconciliation'):
        if ev['body'].get('reconciliation_defect'):
            col.add('usage.reconciliation',
                    {'server_id': ev['body']['server_id'], 'window': ev['body']['window']},
                    seq=ev['seq'])
    col.ok('usage.reconciliation')

    # ---- exposure.ledger ----------------------------------------------------
    ledger_path = rroot / trial / 'exposure_ledger.json'
    recount = _recount_exposure(events)
    if ledger_path.exists():
        on_disk = _load_json(ledger_path)
        if canonical_json(on_disk) != canonical_json(recount):
            col.add('exposure.ledger', {'error': 'ledger differs from a recount',
                                        'recount_sha256': sha256_canonical(recount)})
    elif terminal_trial:
        col.add('exposure.ledger', {'error': 'exposure_ledger.json is missing'})
    else:
        col.add('exposure.ledger', {'skipped': 'trial has not ended'}, severity='INFO')
    col.ok('exposure.ledger')

    # ---- anchor.prefix / anchor.receipts ------------------------------------
    by_seq = {e['seq']: e for e in events}
    for ev in _by_type(events, 'anchor'):
        b = ev['body']
        upto = int(b['upto_seq'])
        target = by_seq.get(upto)
        if target is None or target['h'] != b['upto_h']:
            col.add('anchor.prefix', {'upto_seq': upto, 'error': 'upto_h does not match'},
                    seq=ev['seq'])
        idx = int(b['segment_index'])
        if idx < len(read.segments):
            raw = read.segments[idx].read_bytes()
            line = canonical_json(ev).encode('utf-8') + b'\n'
            cut = raw.rfind(line)
            prefix = raw[:cut] if cut >= 0 else raw
            if sha256_bytes(prefix) != b['segment_sha256'] \
                    or len(prefix) != int(b['segment_bytes']):
                col.add('anchor.prefix',
                        {'segment_index': idx, 'error': 'segment prefix bytes differ',
                         'expected_bytes': int(b['segment_bytes']),
                         'found_bytes': len(prefix)}, seq=ev['seq'])
        else:
            col.add('anchor.prefix', {'segment_index': idx, 'error': 'no such segment'},
                    seq=ev['seq'])
    col.ok('anchor.prefix')

    receipted = {int(e['body']['anchor_seq']) for e in events
                 if e['type'] in ('anchor_receipt', 'anchor_failed')}
    longest = 0
    for ev in _by_type(events, 'anchor'):
        if int(ev['body']['anchor_seq']) not in receipted:
            col.add('anchor.receipts', {'anchor_seq': int(ev['body']['anchor_seq'])},
                    seq=ev['seq'])
            longest += 1
    col.ok('anchor.receipts')

    # ---- t4.payload_identity -------------------------------------------------
    if trial == 'T4':
        payloads: dict[int, list[str]] = {}
        for ev in _by_type(events, 'episode_started'):
            payloads.setdefault(int(ev['body']['pair']), []).append(
                ev['body']['payload_sha256'])
        for pair, digests in payloads.items():
            if len(digests) == 2 and digests[0] != digests[1]:
                col.add('t4.payload_identity', {'pair': pair,
                                                'a': digests[0], 'b': digests[1]})
    col.ok('t4.payload_identity')

    # ---- host.record / host.quiescence (protocol 5.7) ------------------------
    _check_host_scans(col, events, 'foreign_load_detected')

    # ---- server.lifecycle (repair contract EB1) --------------------------------
    _check_server_lifecycle(col, events, cfg)

    # ---- integrity.table (INFO) ---------------------------------------------
    terminal_by_arm = {arm: 0 for arm in ARMS}
    for ev in reveals:
        if ev['body']['outcome'].get('error_class') in ('worker_died', 'episode_timeout',
                                                        'interrupted'):
            terminal_by_arm[ev['body']['arm']] += 1
    col.add('integrity.table', {
        'pairs_enrolled': len(enrolls),
        'episodes_revealed': len(reveals),
        'terminal_failures_incumbent': terminal_by_arm['incumbent'],
        'terminal_failures_candidate': terminal_by_arm['candidate'],
        'torn_recoveries': len(_by_type(events, 'log_recovery')),
        'worktree_drift_events': sum(
            1 for e in events if e['type'] == 'trial_paused'
            and e['body']['reason_code'] == 'worktree_drift'),
        'worktree_drift_counted_in_label': False,
        'unreceipted_anchors': longest,
    })
    return _finish(col, trial, mode)


def program_seed_collisions(trial: str, events: Sequence[Mapping],
                            seed_owner: dict[int, str]) -> list[dict]:
    """``seeds.unique`` ACROSS trial chains (protocol 5.5; execution review E2).

    The per-trial check in ``_verify_trial`` sees one chain and therefore cannot see the
    collision the program-wide seed registry exists to prevent: the same seed drawn again in
    a LATER trial of the same program.  ``seed_owner`` carries "seed -> first trial and
    request that used it" from one trial to the next and is MUTATED here, so calling this
    over the trials in frozen order reports each repeat once, against its first user.

    Severity is unchanged -- ``seeds.unique`` is a DEFECT, never a FAIL -- because seeds are
    not part of any guarantee and a collision never invalidates a trial (protocol 5.5 and
    6.4 row 19).  What changes is that the defect is detectable at all."""
    out: list[dict] = []
    for ev in events:
        if ev['type'] != 'llm_request':
            continue
        seed = int(ev['body']['seed'])
        here = '%s:%s' % (trial, ev['body']['request_id'])
        first = seed_owner.get(seed)
        if first is None:
            seed_owner[seed] = here
        else:
            out.append({'seed': seed, 'first': first, 'again': here,
                        'scope': 'program', 'seq': ev['seq']})
    return out


def _unknown_usage_requests(events: Sequence[Mapping]) -> dict[str, int]:
    """``request_id -> arrival`` for every started request with no complete usage receipt.

    The verifier's own reading of the same rule the orchestrator applies in
    ``lab_orchestrator.unknown_usage_by_request``; the two are written and maintained
    separately and their ledgers are compared byte for byte, so this one must not be edited
    into a copy of that one.  Per request id the chain can be in exactly one of three
    states, and only ``receipted`` means the consumed tokens are known:

      * ``receipted``  -- an ``llm_response`` (which always carries ``usage``), or an
                          ``llm_error`` declaring ``usage_known``;
      * ``unreceipted``-- an ``llm_error`` without ``usage_known``;
      * ``outstanding``-- an ``llm_request`` and nothing else, which is legal after
                          ``worker_died`` / ``episode_timeout`` / ``interrupted`` (see the
                          permission granted in ``_check_calls``) and which an earlier
                          version of this recount scored as zero tokens.

    The last two are both unknown.  Keying on the request id makes the count idempotent
    under repeated or duplicated events."""
    state: dict[str, str] = {}
    arrival_of: dict[str, int] = {}
    for ev in events:
        etype = ev['type']
        if etype not in ('llm_request', 'llm_response', 'llm_error'):
            continue
        body = ev['body']
        rid = str(body['request_id'])
        if 'arrival' in body:
            arrival_of.setdefault(rid, int(body['arrival']))
        if etype == 'llm_request':
            state.setdefault(rid, 'outstanding')
        elif etype == 'llm_response':
            state[rid] = 'receipted'
        elif body.get('usage_known', False):
            state[rid] = 'receipted'
        elif state.get(rid) != 'receipted':
            state[rid] = 'unreceipted'
    return {rid: arrival_of[rid] for rid, st in state.items()
            if st != 'receipted' and rid in arrival_of}


def _recount_exposure(events: Sequence[Mapping]) -> dict:
    """Per phase x arm: episodes, wall seconds, prompt/completion tokens, unknown-usage
    calls.  Recomputed from the chain alone.

    ``tokens_are_lower_bound`` is set whenever a call in that cell consumed tokens the
    chain cannot report, so the ledger states its own incompleteness instead of presenting
    an unknown as a zero."""
    out: dict = {phase: {arm: {'episodes': 0, 'wall_seconds': 0.0, 'prompt_tokens': 0,
                               'completion_tokens': 0, 'unknown_usage_calls': 0,
                               'tokens_are_lower_bound': False}
                         for arm in ARMS}
                 for phase in ('randomizing', 'post_decision')}
    arm_of_arrival: dict[int, str] = {}
    phase_of_arrival: dict[int, str] = {}
    for ev in events:
        if ev['type'] == 'episode_revealed':
            a = int(ev['body']['arrival'])
            arm = ev['body']['arm']
            phase = 'post_decision' if ev['body'].get('post_decision') else 'randomizing'
            arm_of_arrival[a] = arm
            phase_of_arrival[a] = phase
            row = out[phase][arm]
            row['episodes'] += 1
            row['wall_seconds'] += float(ev['body']['outcome']['latency_s'])
            row['prompt_tokens'] += int(ev['body']['outcome']['prompt_tokens'])
            row['completion_tokens'] += int(ev['body']['outcome']['completion_tokens'])
    for a in _unknown_usage_requests(events).values():
        arm = arm_of_arrival.get(a)
        phase = phase_of_arrival.get(a)
        if arm is not None and phase is not None:
            out[phase][arm]['unknown_usage_calls'] += 1
    for phase in out:
        for arm in out[phase]:
            out[phase][arm]['wall_seconds'] = round(out[phase][arm]['wall_seconds'], 6)
            out[phase][arm]['tokens_are_lower_bound'] = \
                out[phase][arm]['unknown_usage_calls'] > 0
    return out


def _finish(col: _Collector, trial: str, mode: str) -> VerifyReport:
    counts: dict[str, int] = {'FAIL': 0, 'DEFECT': 0, 'INFO': 0}
    for f in col.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    counts['checks_run'] = len(col.seen)
    verdict = 'FAIL' if counts['FAIL'] else 'PASS'
    return VerifyReport(trial=trial, mode=mode, verdict=verdict,  # type: ignore[arg-type]
                        findings=list(col.findings), counts=counts)


# ---------------------------------------------------------------------------
# the program chain
# ---------------------------------------------------------------------------
def verify_program(freeze_bundle_sha256: str, *,
                   results_root: Path | None = None) -> VerifyReport:
    rroot = Path(results_root) if results_root is not None else RESULTS_ROOT
    col = _Collector(trial='_program', mode='full')
    events_dir = rroot / '_program' / 'events'
    try:
        read = read_chain(events_dir, '_program', freeze_bundle_sha256)
    except ChainError as exc:
        col.add('chain.read', {'error': str(exc)})
        return _finish(col, '_program', 'full')
    col.ok('chain.read')
    events = read.events
    if events:
        want = genesis_prev(freeze_bundle_sha256, '_program')
        if events[0]['prev'] != want:
            col.add('chain.genesis', {'found': events[0]['prev'], 'expected': want}, seq=0)
        if events[0]['type'] != 'program_opened':
            col.add('program.order', {'error': 'seq 0 is not program_opened'}, seq=0)
    col.ok('chain.genesis')
    for ev in events:
        try:
            validate_event(ev['type'], ev['body'])
        except SchemaError as exc:
            col.add('schema.all', {'type': ev['type'], 'error': str(exc)}, seq=ev['seq'])
    col.ok('schema.all')

    opened = [e['body']['trial'] for e in events if e['type'] == 'trial_opened']
    closed = [e['body']['trial'] for e in events if e['type'] == 'trial_closed']
    frozen_order = list(TRIALS)
    if opened != frozen_order[:len(opened)]:
        col.add('program.order', {'opened': ','.join(opened),
                                  'expected': ','.join(frozen_order)})
    if closed != opened[:len(closed)]:
        col.add('program.order', {'closed': ','.join(closed), 'opened': ','.join(opened)})
    authorizations = {e['h'] for e in events if e['type'] == 'refreeze_authorization'}
    seed_owner: dict[int, str] = {}                 # seed -> "<trial>:<request id>"
    for trial in frozen_order:
        tdir = rroot / trial / 'events'
        if not tdir.exists():
            continue
        try:
            tread = read_chain(tdir, trial, freeze_bundle_sha256)
        except ChainError:
            continue
        if not tread.events:
            continue
        b = tread.events[0]['body']
        for h in b.get('refreezes_in_force', []):
            if h not in authorizations:
                col.add('program.order',
                        {'trial': trial, 'error': 'refreeze not authorized in the program '
                                                  'chain', 'refreeze': h})
        for body in program_seed_collisions(trial, tread.events, seed_owner):
            col.add('seeds.unique', {k: v for k, v in body.items() if k != 'seq'},
                    seq=body['seq'])
    col.ok('program.order')
    col.ok('seeds.unique')
    _check_host_scans(col, events, 'host_quiescence_refused', refusal=True)
    return _finish(col, '_program', 'full')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI: --trial T1 [--mode plumbing|full] [--results DIR] [--work DIR] [--json OUT].
    Exit code 0 on PASS, 1 on FAIL, 2 on a usage error.  Writes nothing but --json."""
    parser = argparse.ArgumentParser(prog='lab_verify_log', add_help=True)
    parser.add_argument('--trial', required=True)
    parser.add_argument('--bundle', default=None,
                        help='freeze bundle sha256; default: recomputed from '
                             '<results>/freeze/freeze_bundle.json')
    parser.add_argument('--mode', default='full', choices=['plumbing', 'full'])
    parser.add_argument('--results', default=None)
    parser.add_argument('--work', default=None)
    parser.add_argument('--json', dest='json_out', default=None)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    rroot = Path(args.results) if args.results else RESULTS_ROOT
    bundle = args.bundle
    if bundle is None:
        obj = _load_json(rroot / 'freeze' / 'freeze_bundle.json')
        if not isinstance(obj, dict):
            print('freeze_bundle.json is missing; pass --bundle', file=sys.stderr)
            return 2
        bundle = lab_common.freeze_bundle_sha256(obj)
    if args.trial in ('_program', 'program'):
        report = verify_program(bundle, results_root=rroot)
    elif args.trial in TRIALS:
        report = verify_trial(args.trial, bundle, mode=args.mode, results_root=rroot,
                              work_root=Path(args.work) if args.work else None)
    else:
        print(f'unknown trial {args.trial!r}', file=sys.stderr)
        return 2
    payload = report.to_json()
    if args.json_out:
        Path(args.json_out).write_text(canonical_json(payload) + '\n', encoding='utf-8')
    for f in report.findings:
        print(f'{f.severity:6s} [{condition_list(f.check)}] {f.check} '
              f'seq={f.seq} {canonical_json(f.detail)}')
    print(f'{report.trial} {report.mode}: {report.verdict} '
          f'({canonical_json(report.counts)})')
    return 0 if report.verdict == 'PASS' else 1


if __name__ == '__main__':                                            # pragma: no cover
    raise SystemExit(main())
