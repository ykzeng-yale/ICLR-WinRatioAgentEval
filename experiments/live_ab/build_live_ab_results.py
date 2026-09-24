"""build_live_ab_results.py -- tables and figures from the chain and the records (3.15).

G5.  Reporting code (protocol 14.3): a defect found after outcomes exist is repaired by the
versioned erratum of protocol 6.4 row 23, and **no erratum can alter a decision**, because
decisions come only from decision-defining code.

The builder **never recomputes a decision**.  It prints the logged ``decision``, the
reference rule's own first crossing beside it as the agreement flag of protocol 8.9, and
the replay's agreement.  It reads only deposited artifacts: the chains, the record files and
the frozen sidecars.  It imports neither the orchestrator nor the worker (a test asserts
it), never runs a model or a generated program, and writes timestamp-free outputs.

It runs only after the last trial has ended.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

import lab_common
import lab_enclosure
import lab_eventlog
import lab_monitor
import lab_reference_rule
from lab_common import ARMS, canonical_json, sha256_file

if str(lab_common.SRC_DIR) not in sys.path:
    sys.path.insert(0, str(lab_common.SRC_DIR))
import winstats                                                        # noqa: E402

BANNER: str = 'MOCK'

#: The exploratory success margins of protocol 8.8 item 1.  They are printed and they
#: decide nothing: `decide` never reads them and `exploratory_margins_decide` is false.
EXPLORATORY_MARGINS: tuple[float, ...] = (0.10, 0.15)


def _read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _stamp(obj: dict, mock: bool) -> dict:
    """Every derived file of a dry run carries the banner and the flag."""
    out = dict(obj)
    out['mock'] = bool(mock)
    if mock:
        out['banner'] = BANNER
    return out


def _write_json(path: Path, obj: dict, mock: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json(_stamp(obj, mock)) + '\n'
    path.write_text(text, encoding='utf-8')
    return lab_common.sha256_text(text)


def _write_csv(path: Path, rows: list[dict], mock: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if mock:
        frame.insert(0, 'mock', BANNER)
    frame.to_csv(path, index=False, lineterminator='\n')
    return sha256_file(path)


# ---------------------------------------------------------------------------
# the tables
# ---------------------------------------------------------------------------
def monitor_rows(events: Sequence[Mapping]) -> list[dict]:
    """One row per look: trigger, n, the sums, the radius, the band and the flags."""
    rows: list[dict] = []
    for ev in events:
        if ev['type'] != 'monitor_update':
            continue
        b = ev['body']
        rows.append({
            'seq': int(ev['seq']), 'trigger': b['trigger'], 'n': int(b['n']),
            'n_collapsed': int(b['n_collapsed']),
            'sum_lower_h': b['sum_lower_h'], 'sum_upper_h': b['sum_upper_h'],
            'sum_lower_s': b['sum_lower_s'], 'sum_upper_s': b['sum_upper_s'],
            'radius': b['radius'], 'L_h': b['L_h'], 'U_h': b['U_h'],
            'L_s': b['L_s'], 'U_s': b['U_s'],
            'n_min_ok': bool(b['flags']['n_min_ok']), 'harm': bool(b['flags']['harm']),
            'deploy': bool(b['flags']['deploy']),
            'success_guard_ok': bool(b['flags']['success_guard_ok']),
            'shadow_mismatch': bool(b['shadow']['mismatch']),
            'L_s_vs_010': b['readouts']['L_s_vs_010'],
            'L_s_vs_015': b['readouts']['L_s_vs_015'],
        })
    return rows


def episode_rows(events: Sequence[Mapping]) -> list[dict]:
    rows: list[dict] = []
    started = {int(e['body']['arrival']): e['body'] for e in events
               if e['type'] == 'episode_started'}
    for ev in events:
        if ev['type'] != 'episode_revealed':
            continue
        b = ev['body']
        out = b['outcome']
        row = {'seq': int(ev['seq']), 'arrival': int(b['arrival']), 'pair': int(b['pair']),
               'position': int(b['position']), 'arm': b['arm'],
               'reveal_index': int(b['reveal_index']),
               'phase': 'post_decision' if b.get('post_decision') else 'randomizing',
               'task_uid': str(started.get(int(b['arrival']), {}).get('task_uid', '')),
               'workflow': str(started.get(int(b['arrival']), {}).get('workflow', '')),
               'sandbox_lock_wait_s': float(b['sandbox_lock_wait_s']),
               'certified_ell': float(b['certified_ell']),
               'recovered_orphan': bool(b['recovered_orphan']),
               'started_after_resume': bool(
                   started.get(int(b['arrival']), {}).get('started_after_resume', False)),
               'overlap_s': float(b['overlap']['seconds_with_partner'])}
        row.update({k: out[k] for k in sorted(out)})
        # repair contract EB5 (root 21:15 item 3): ``completion_tokens`` is the KNOWN tokens
        # (not scored, protocol 1249); it is never presented as a complete count when a call
        # of the episode has no usage receipt.  A chain written before EB5 carries no flag:
        # its count is labelled ``unknown`` too, never ``complete``.
        complete = b.get('usage_complete')
        row['usage_complete'] = complete
        row['unknown_usage_calls'] = b.get('unknown_usage_calls')
        row['completion_tokens_status'] = ('complete' if complete is True else
                                           'lower_bound' if complete is False else 'unknown')
        rows.append(row)
    return rows


def pair_rows(events: Sequence[Mapping], cfg: Mapping) -> list[dict]:
    """One row per enrolled pair: the coin, the arms, the scores and the infra flags."""
    tiers = lab_enclosure.tiers_from_config(dict(cfg))
    enrolled: dict[int, dict] = {}
    coins: dict[int, dict] = {}
    outcomes: dict[int, dict] = {}
    lock_wait: dict[int, dict] = {}
    for ev in events:
        b = ev['body']
        if ev['type'] == 'pair_enrolled':
            enrolled.setdefault(int(b['pair']), dict(b))
        elif ev['type'] == 'coin_drawn':
            coins[int(b['pair'])] = dict(b)
        elif ev['type'] == 'episode_revealed' and int(b['pair']):
            outcomes.setdefault(int(b['pair']), {})[b['arm']] = dict(b)
            lock_wait.setdefault(int(b['pair']), {})[b['arm']] = \
                float(b['sandbox_lock_wait_s'])
    rows: list[dict] = []
    for pair in sorted(coins):
        body = enrolled.get(pair, {})
        arms = outcomes.get(pair, {})
        row = {
            'pair': pair, 'stratum': body.get('stratum'),
            'arrivals': ','.join(str(a) for a in body.get('arrivals', [])),
            'uids': ','.join(str(u) for u in body.get('task_uids', [])),
            'coin_bit': int(coins[pair]['bit']), 'coin_raw_hex': coins[pair]['raw_hex'],
            'arm_at_position_1': coins[pair]['assignment'].get(
                str(body.get('arrivals', [0, 0])[0])),
            'z': None, 'decisive_tier': None, 'd': None, 'collapsed': False,
            'infra_flag': False,
        }
        for arm in ARMS:
            row['lock_wait_%s' % arm] = (lock_wait.get(pair, {}) or {}).get(arm)
            row['latency_%s' % arm] = (arms.get(arm, {}).get('outcome') or {}).get(
                'latency_s')
            row['success_%s' % arm] = (arms.get(arm, {}).get('outcome') or {}).get(
                'success')
        if set(arms) == set(ARMS):
            views = {arm: lab_enclosure.EpisodeView.reveal(
                arm, int(arms[arm]['outcome']['success']),
                float(arms[arm]['outcome']['latency_s']),
                int(arms[arm]['outcome']['completion_tokens'])) for arm in ARMS}
            z, tier, d = lab_enclosure.final_scores(views['candidate'],
                                                    views['incumbent'], tiers)
            row.update({'z': int(z), 'decisive_tier': int(tier), 'd': int(d),
                        'collapsed': True,
                        'infra_flag': any(bool(arms[arm]['outcome']['infra_flag'])
                                          for arm in ARMS)})
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# the derived objects
# ---------------------------------------------------------------------------
#: Root's 21:14 ruling (``reviews/restart_cap_estimand_ruling_20260923_2114.md``) replaces
#: the repair contract's withdrawn reportability default ("no decision from any cap-aborted
#: trial").  The restart cap is phase-aware (``lab_eventlog.restart_cap_case``):
#:
#: * (a) ``before_decision`` -- a fourth restart was required before any decision: the trial
#:   is INCOMPLETE and reports no deploy/harm decision; it is not a null result and not a
#:   valid abstention (an arm-related crash remains possible), and it keeps every enrolled
#:   pair, attempt, band endpoint, failure and unknown usage;
#: * (b) ``after_receipted_decision`` -- required after a logged decision whose blocking
#:   anchor carries its chained external receipt: the decision and its original ``tau``
#:   stand and are reported; the follow-up cohort is truncated and its unrun arrivals are
#:   counted (protocol 6.4 "Aborts in the post-decision phase", 14.6);
#: * (c) ``decision_provisional`` -- required while the logged decision still awaited that
#:   receipt: no finalized claim until the existing receipt rules succeed.  If the chain
#:   later carries the receipt the decision is reported as in (b); if not, it stays
#:   :data:`PROVISIONAL_LABEL`.
#:
#: Root 00:22: a decision is externally receipted only by its own blocking anchor's chained
#: receipt, with the external server time outside a MOCK tree; a local decision event alone
#: is provisional -- for every trial, capped or not.
RESTART_CAP_INCOMPLETE_LABEL: str = ('incomplete: restart cap before any decision '
                                     '(no decision; not a null result, not an abstention)')
PROVISIONAL_LABEL: str = ('provisional: the logged decision has no chained external '
                          'receipt (no finalized claim)')
#: Protocol 6.4 ("An abort can only remove decisions, never create one"): the chain reached a
#: no-decision point other than the cap (``lab_eventlog.no_decision_point``: an owed or
#: triggered abort, an unresolved worker) before any decision, and a crossing was logged after
#: it and not acted on.  Review of 988baf7, reviewer 1 finding 2: such a trial used to be
#: reported ``LIVE_DECISION_INVALID (harness defect)``.
ABORT_INCOMPLETE_LABEL: str = ('incomplete: aborted before any decision; a crossing logged '
                               'after the abort point was not acted on (no decision; not a '
                               'null result, not an abstention)')
#: Protocol 8.9: the chain's decision (or its absence) is invalid -- a decision logged after the
#: no-decision point (the cap's included), a decision the reference rule's first crossing does
#: not agree with, or a reference crossing at an ELIGIBLE look with no decision.  Root 19:05
#: (``reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md``): it is NEVER reportable; the
#: summary's ``decision`` is this label and the logged decision is kept beside it
#: (``logged_decision``) -- at 03fe0ca / 7ebffad a decision after a non-cap point was labelled
#: invalid with ``reportable`` true, and the summary published the logged kind.
DECISION_INVALID_LABEL: str = 'LIVE_DECISION_INVALID (harness defect)'


def terminal_event(events: Sequence[Mapping]) -> Mapping | None:
    """The trial's terminal event (the last ``trial_ended`` / ``trial_aborted``), or None."""
    return next((e for e in reversed(list(events))
                 if e['type'] in ('trial_ended', 'trial_aborted')), None)


def restart_cap_reading(events: Sequence[Mapping], cfg: Mapping) -> dict:
    """[pure] The restart-cap case of a chain under the frozen configuration's cap, the
    decision's receipt state, and the terminal record's ``completion`` (arrivals not run,
    follow-up not run; recounted by the verifier's ``server.lifecycle``), or None when the
    chain has no terminal record carrying one."""
    cfg = dict(cfg or {})
    try:
        cap: int | None = lab_common.server_supervision_cap(cfg)
    except lab_common.FrozenMismatch:
        cap = None
    mock = bool(cfg.get('mock') or cfg.get('mock_overrides'))
    cc = lab_eventlog.restart_cap_case(list(events), cap, mock=mock)
    term = terminal_event(events)
    dec = cc['decision']
    return {'case': cc['case'], 'cap_required_seq': cc['cap_required_seq'],
            'decision_status': dec['status'], 'decision_seq': dec['decision_seq'],
            'decision_receipt_seq': dec['receipt_seq'],
            'decision_receipt_server_time': dec['server_time'],
            'decision_after_cap_seq': cc['decision_after_cap_seq'],
            'completion': (dict(term['body']['completion'])
                           if term is not None and term['body'].get('completion')
                           else None)}


def eligibility_object(events: Sequence[Mapping], cfg: Mapping, trial: str) -> dict:
    """THE decision-eligibility classification of the chain (``lab_eventlog.
    decision_eligibility`` -- the function the orchestrator calls before every look and the
    verifier's ``reference_rule.agreement`` calls; root 16:05 item 2) under the frozen cap and
    ten-failure count, with the reference rule's action at every logged look: the exclusion
    point, EVERY look classified eligible or not with its concrete reason (the unfiltered
    diagnostics), and the reference rule's unfiltered first crossing with its verdict."""
    cfg = dict(cfg or {})
    try:
        cap: int | None = lab_common.server_supervision_cap(cfg)
    except lab_common.FrozenMismatch:
        cap = None
    looks = lab_reference_rule.looks_from_chain(list(events), cfg, trial)
    return lab_eventlog.decision_eligibility(
        list(events), cap,
        failure_limit=int(((cfg.get('execution') or {}).get('auto_abort') or {})
                          .get('consecutive_infrastructure_failures', 10)),
        reference_actions=[lk.action for lk in looks])


def decision_object(events: Sequence[Mapping], cfg: Mapping, trial: str) -> dict:
    """The logged decision, with the reference rule's own result beside it.

    The builder does not decide: it prints what the chain carries and whether the second
    code path and the replay agree with it (protocol 8.9), and it labels the restart-cap
    case of root's 21:14 ruling (``restart_cap``).  The no-decision point of the chain
    (``lab_eventlog.no_decision_point``: the cap, an owed or triggered abort -- every abort
    path writes its ``abort_owed`` before its drain -- or an unresolved worker; review of
    988baf7, reviewer 1 findings 1 and 2; root 16:05) is read through
    :func:`eligibility_object`, the classification the orchestrator and the verifier share.

    ``primary_result`` is, first match wins:

    1. :data:`DECISION_INVALID_LABEL` -- a decision logged after the point (the cap's
       included: the verifier's ``decision_after_no_decision_point`` / ``decision_after_cap``;
       the orchestrator never writes one), a logged decision the reference rule's first
       crossing does not agree with (kind and ``n``), or a crossing at an ELIGIBLE look with no
       decision, however the trial ended (``missed``: no blanket exemption);
    2. :data:`RESTART_CAP_INCOMPLETE_LABEL` -- case (a) with no decision;
    3. :data:`ABORT_INCOMPLETE_LABEL` -- no decision, and the reference rule's crossing is at a
       look the classification makes NOT eligible (not acted on, with its concrete reason);
    4. :data:`PROVISIONAL_LABEL` -- a valid decision without its chained external receipt
       (any case);
    5. the logged decision's kind, or ``none`` with no decision and no crossing.

    ``reportable`` is true ONLY in 5, where the result IS the logged decision (root 19:05:
    "for any invalid post-boundary decision ... set ``reportable = false``, and make the
    summary's decision the invalidity label"); every label beginning "not reportable" is on a
    non-reportable result.  The logged event always stays under ``decision``, whatever the
    result; :func:`build` makes the summary's ``decision`` the ``primary_result`` and keeps the
    logged kind beside it (``logged_decision``) whenever it is not reportable.
    ``eligibility`` carries the whole classification: every look, eligible or not, and why."""
    logged = next((dict(e['body'], seq=int(e['seq'])) for e in events
                   if e['type'] == 'decision'), None)
    cap = restart_cap_reading(events, cfg)
    reference = lab_reference_rule.decide_from_chain(list(events), dict(cfg), trial)
    replayed = lab_monitor.replay(list(events), dict(cfg), trial)
    updates = [e for e in events if e['type'] == 'monitor_update']
    replay_agrees = len(replayed) == len(updates) and all(
        repr(float(s[k])) == repr(float(u['body'][k]))
        for s, u in zip(replayed, updates)
        for k in ('L_h', 'U_h', 'L_s', 'U_s', 'radius'))
    agreement = (logged is not None
                 and reference.get('kind') == logged['kind']
                 and reference.get('n') == int(logged['n']))
    if logged is None:
        agreement = reference.get('kind') == 'none'
    label: str | None = None
    not_acted_on: dict | None = None
    elig = eligibility_object(events, cfg, trial)
    point = elig['exclusion']
    crossing = elig['crossing']
    if logged is None and crossing is not None and crossing['verdict'] == 'not_acted_on':
        # the reference rule's first crossing is at a look the shared classification makes
        # NOT eligible: not acted on, with its concrete reason -- never a disagreement
        agreement = True
        not_acted_on = {'kind': str(reference.get('kind')), 'n': int(reference['n']),
                        'seq': int(crossing['seq']),
                        'no_decision_reason': str(crossing['reason']),
                        'reason_text': crossing.get('reason_text'),
                        'no_decision_seq': None if point is None else int(point['seq'])}
        if point is not None and point.get('abort_reason') is not None:
            not_acted_on.update(abort_reason=point['abort_reason'],
                                abort_source=point['source'])
    invalid: str | None = None
    if logged is not None and elig['decision_verdict'] == 'after_exclusion':
        # a decision logged after the point: an abort can only remove decisions (protocol
        # 6.4); the verifier FAILs it (``decision_after_no_decision_point``, or the cap's
        # ``decision_after_cap``)
        agreement = False
        if point['reason'] == 'server_restart_cap':
            invalid = ('not reportable: logged after the restart cap was required before any '
                       'decision (case a takes no new decision)')
        else:
            invalid = ('not reportable: logged after the no-decision point (%s at seq %d; an '
                       'abort can only remove decisions)' % (point['reason'], int(point['seq'])))
    elif not agreement and logged is not None:
        invalid = ('not reportable: the logged decision (%s at n=%d) does not agree with the '
                   "reference rule's first crossing (%s at n=%s; protocol 8.9)"
                   % (logged['kind'], int(logged['n']), reference.get('kind'),
                      reference.get('n')))
    elif not agreement:
        invalid = ("not reportable: no decision was logged, but the reference rule's first "
                   'crossing (%s at n=%s) is at a look eligible to carry it (crossing verdict '
                   '%s)' % (reference.get('kind'), reference.get('n'),
                            None if crossing is None else crossing['verdict']))
    if invalid is not None:
        # root 19:05: never reportable, whatever else holds; the logged event stays under
        # ``decision`` and beside the summary's result (``logged_decision``)
        primary, reportable, label = DECISION_INVALID_LABEL, False, invalid
    elif cap['case'] == 'before_decision':
        primary, reportable = RESTART_CAP_INCOMPLETE_LABEL, False
    elif not_acted_on is not None:
        # a crossing logged after an abort's point with no decision: not acted on (the
        # verifier's INFO), never a disagreement
        primary, reportable = ABORT_INCOMPLETE_LABEL, False
    elif logged is not None and cap['decision_status'] != 'receipted':
        primary, reportable = PROVISIONAL_LABEL, False
        label = PROVISIONAL_LABEL
    else:
        # the only reportable result: the valid logged decision (or none with no crossing)
        primary = logged['kind'] if logged else 'none'
        reportable = True
        if cap['case'] in ('after_receipted_decision', 'decision_provisional') \
                and logged is not None:
            not_run = (cap['completion'] or {}).get('follow_up_not_run')
            label = ('decision stands at tau=%d; follow-up truncated by the restart cap '
                     '(%s follow-up arrivals not run)%s'
                     % (int(logged['n']), 'unknown' if not_run is None else int(not_run),
                        '; provisional when the cap bound, receipted afterwards'
                        if cap['case'] == 'decision_provisional' else ''))
    return {
        'trial': trial,
        'decision': logged,
        'reference_rule': reference,
        'agreement_kind_and_prefix': bool(agreement),
        'replay_agrees_elementwise': bool(replay_agrees),
        'n_shadow_mismatches': sum(1 for u in updates
                                   if u['body']['shadow']['mismatch']),
        'primary_result': primary,
        'reportable': bool(reportable),
        'decision_label': label,
        'decision_status': cap['decision_status'],
        'restart_cap': cap,
        'crossing_not_acted_on': not_acted_on,
        'eligibility': elig,
        'margin_delta': float(dict(cfg)['monitor']['delta']),
        'alpha_gate': float(dict(cfg)['monitor']['alpha_gate']),
        'rho': float(dict(cfg)['monitor']['rho']),
        'n_min': int(dict(cfg)['monitor']['n_min']),
        'note': ('the decision certifies the running average of history-conditional pair '
                 'means at the logged prefix and nothing else'),
    }


def sensitivity_object(pairs: list[dict], episodes: list[dict]) -> dict:
    """The prespecified descriptive read-outs S-infra, S-int and S-lock (protocol 6.4,
    8.8 item 8).  Descriptive: none of them decides anything."""
    resolved = [p for p in pairs if p['collapsed']]
    def _mean(values: list[float]) -> float | None:
        return float(np.mean(values)) if values else None
    z_all = [float(p['z']) for p in resolved]
    d_all = [float(p['d']) for p in resolved]
    z_clean = [float(p['z']) for p in resolved if not p['infra_flag']]
    terminal = {int(e['pair']) for e in episodes
                if e.get('error_class') in ('worker_died', 'episode_timeout',
                                            'interrupted')}
    z_int = [0.0 if p['pair'] in terminal else float(p['z']) for p in resolved]
    d_int = [0.0 if p['pair'] in terminal else float(p['d']) for p in resolved]
    z_lock: list[float] = []
    for p in resolved:
        lat = {arm: (p.get('latency_%s' % arm) or 0.0) - (p.get('lock_wait_%s' % arm) or 0.)
               for arm in ARMS}
        suc = {arm: int(p.get('success_%s' % arm) or 0) for arm in ARMS}
        if suc['candidate'] != suc['incumbent']:
            z_lock.append(float(suc['candidate'] - suc['incumbent']))
        elif suc['candidate'] == 0:
            z_lock.append(0.0)
        else:
            tol = 0.05 * max(abs(lat['candidate']), abs(lat['incumbent']))
            diff = lat['incumbent'] - lat['candidate']
            z_lock.append(0.0 if abs(diff) <= tol else float(np.sign(diff)))
    return {
        'n_resolved_pairs': len(resolved),
        'Zbar': _mean(z_all), 'Dbar': _mean(d_all),
        'S_infra': {'label': 'without pairs containing an infra_flag episode',
                    'n': len(z_clean), 'Zbar': _mean(z_clean)},
        'S_int': {'label': 'every pair with a terminal-failure episode scored as a tie',
                  'n': len(z_int), 'Zbar': _mean(z_int), 'Dbar': _mean(d_int)},
        'S_lock': {'label': ('descriptive read-out of the execution-lock transfer; not a '
                             'decision, not a correction of the frozen hierarchy'),
                   'n': len(z_lock), 'Zbar': _mean(z_lock)},
        'exploratory_margins': list(EXPLORATORY_MARGINS),
        'exploratory_margins_decide': False,
    }


def integrity_object(events: Sequence[Mapping], cfg: Mapping) -> dict:
    """The six tables of protocol 12.6, printed whether or not they are empty."""
    rule = dict(dict(cfg).get('integrity_label_rule') or {})
    coin_adjacent = 0
    last_durable_coin: int | None = None
    accepted: set[int] = set()
    for ev in events:
        if ev['type'] == 'coin_drawn':
            last_durable_coin = int(ev['seq'])
        elif ev['type'] == 'job_accepted':
            accepted.add(int(ev['body']['arrival']))
            last_durable_coin = None
        elif ev['type'] == 'invocation_started' and last_durable_coin is not None:
            coin_adjacent += 1
    terminal = {'randomizing': {arm: 0 for arm in ARMS},
                'post_decision': {arm: 0 for arm in ARMS}}
    pairs_with_terminal: set[int] = set()
    for ev in events:
        if ev['type'] != 'episode_revealed':
            continue
        b = ev['body']
        if b['outcome'].get('error_class') in ('worker_died', 'episode_timeout',
                                               'interrupted'):
            phase = 'post_decision' if b.get('post_decision') else 'randomizing'
            terminal[phase][b['arm']] += 1
            if int(b['pair']):
                pairs_with_terminal.add(int(b['pair']))
    torn = [dict(e['body'], seq=int(e['seq'])) for e in events
            if e['type'] == 'log_recovery']
    drift = [{'seq': int(e['seq']), 'digests': e['body'].get('digests')}
             for e in events if e['type'] == 'trial_paused'
             and e['body']['reason_code'] == 'worktree_drift']
    anchors = [e for e in events if e['type'] == 'anchor']
    receipted = {int(e['body']['anchor_seq']) for e in events
                 if e['type'] in ('anchor_receipt', 'anchor_failed')}
    anchor_cfg = dict(dict(cfg).get('anchor') or {})
    sandwich = sandwich_audit(events,
                              anchor_cfg.get('sandwich_tolerance_s', 30),
                              anchor_cfg.get('posting_latency_p95_s'))
    gaps = gap_report(events, float(anchor_cfg.get('gap_report_s', 5)))
    latency = acceptance_latency(events)
    log_prefix = server_log_prefix(events)
    # THE THIRD LIMB, which this file declared in config and never evaluated.
    sandwich_limb = (sandwich['violations'] is not None
                     and len(sandwich['violations'])
                     >= int(rule.get('sandwich_violations', 1)))
    label = (coin_adjacent >= int(rule.get('coin_adjacent_events', 1))
             or sandwich_limb
             or len(pairs_with_terminal) >= int(rule.get('pairs_with_terminal_failure', 3)))
    # An UNCOMPUTABLE limb does not make the label False. If the sandwich audit
    # could not run, "not integrity-qualified" is not a conclusion this data
    # supports, and the report says so rather than presenting a clean label.
    label_determined = sandwich['computable'] or label
    return {
        'coin_adjacent_events': coin_adjacent,
        'coin_adjacency_scope': str(rule.get('coin_adjacency_scope',
                                             'randomized_phase_only')),
        'torn_regions': torn,
        'terminal_failures_by_phase_and_arm': terminal,
        'pairs_with_terminal_failure': sorted(pairs_with_terminal),
        'orphan_rejected': sum(1 for e in events if e['type'] == 'orphan_rejected'),
        'reconciliation_defects': sum(
            1 for e in events if e['type'] == 'usage_reconciliation'
            and e['body'].get('reconciliation_defect')),
        'environment_events_not_attributed_to_the_operator': drift,
        'anchors': len(anchors),
        'unreceipted_anchors': sum(1 for e in anchors
                                   if int(e['body']['anchor_seq']) not in receipted),
        'integrity_qualified': bool(label),
        'integrity_label_determined': bool(label_determined),
        'integrity_label_caveat': (None if label_determined else
                                   'the sandwich limb could not be evaluated, so '
                                   'a negative label is NOT established by this '
                                   'data'),
        'sandwich_audit': sandwich,
        'gap_report': gaps,
        'acceptance_latency': latency,
        'server_log_prefix': log_prefix,
        'label_rule': rule,
    }



# ---------------------------------------------------------------------------
# The time-sandwich audit and the gap report (protocol 12.6 item 4)
# ---------------------------------------------------------------------------
# THE LABEL RULE HAS THREE LIMBS AND THIS FILE EVALUATED TWO. config.json's
# integrity_label_rule declares coin_adjacent_events, sandwich_violations AND
# pairs_with_terminal_failure; the label computed below read the first and the
# third and never the second. A trial whose ONLY integrity signal was a sandwich
# violation would have been reported as not integrity-qualified -- a declared
# rule limb that no code evaluated.


def sandwich_audit(events: list, rule_tolerance_s, posting_latency_p95_s) -> dict:
    """Protocol 12.6 item 4, for consecutive anchor receipts k and k+1:

        | (created_at[k+1] - created_at[k]) - (t_wall[k+1] - t_wall[k]) |
            <= sandwich_tolerance_s + posting_latency_p95_s

    A CONSTANT clock offset cancels in the difference of differences, which is
    why the audit is stated on consecutive pairs rather than on levels.

    IF THE SECOND TERM IS NOT PINNED, THIS REFUSES TO COMPUTE. config carries
    anchor.posting_latency_p95_s = null until the drill's value is pinned in
    Appendix A. Treating null as zero would silently run the audit at a
    tolerance of 30 s instead of 30 + p95 -- tighter than the protocol, so it
    would manufacture violations rather than hide them, but it would still be a
    number the protocol did not authorise. Unknown is reported as unknown.
    """
    out: dict = {'tolerance_s_base': rule_tolerance_s,
                 'posting_latency_p95_s': posting_latency_p95_s}
    if posting_latency_p95_s is None:
        out.update(computable=False, violations=None, pairs_compared=0,
                   reason=('anchor.posting_latency_p95_s is not pinned, so the '
                           'tolerance 30 + p95 is undefined. The audit is NOT '
                           'run and its result is UNKNOWN, not zero.'))
        return out
    tol = float(rule_tolerance_s) + float(posting_latency_p95_s)
    receipts = [e for e in events if e['type'] == 'anchor_receipt']
    rows, violations = [], []
    for a, b in zip(receipts, receipts[1:]):
        ca, cb = a['body'].get('created_at'), b['body'].get('created_at')
        wa, wb = a.get('t_wall_ns'), b.get('t_wall_ns')
        if ca is None or cb is None or wa is None or wb is None:
            rows.append({'from': a.get('seq'), 'to': b.get('seq'),
                         'skipped': 'missing created_at or t_wall_ns'})
            continue
        import datetime as _dt
        try:
            sa = _dt.datetime.fromisoformat(str(ca).replace('Z', '+00:00')).timestamp()
            sb = _dt.datetime.fromisoformat(str(cb).replace('Z', '+00:00')).timestamp()
        except ValueError:
            rows.append({'from': a.get('seq'), 'to': b.get('seq'),
                         'skipped': 'unparsable created_at'})
            continue
        d_server = sb - sa
        d_wall = (int(wb) - int(wa)) / 1e9
        delta = abs(d_server - d_wall)
        row = {'from': a.get('seq'), 'to': b.get('seq'),
               'server_delta_s': d_server, 'wall_delta_s': d_wall,
               'difference_s': delta, 'tolerance_s': tol,
               'violation': delta > tol}
        rows.append(row)
        if row['violation']:
            violations.append(row)
    out.update(computable=True, tolerance_s=tol, pairs_compared=len(rows),
               rows=rows, violations=violations,
               violation_count=len(violations))
    return out


#: Openers mapped to EVERY event that closes them. Validated against the chain
#: vocabulary by ``_validate_coverage_map`` below, because the first version of
#: this map was INVENTED from the protocol's prose and three of its six names did
#: not exist in the schema at all:
#:
#:   llm_request / llm_response          real
#:   sandbox_started / sandbox_ended     NOT IN THE VOCABULARY
#:   metrics_scrape_started / _ended     NOT IN THE VOCABULARY
#:
#: A name that never matches fails SILENTLY and in opposite directions depending
#: on which half is wrong: a missing OPENER means the gap is never covered, so
#: the report over-reports; a missing CLOSER means the opener stays open for
#: ever, so every later gap reads as covered and the report UNDER-reports. The
#: second is the dangerous one, and `llm_error` -- a real closer I had omitted --
#: would have caused exactly it.
#: opener -> (closers, identity field). COVERAGE IS PAIRED BY IDENTITY, NOT
#: COUNTED BY TYPE. The first version kept one counter per event TYPE, so an
#: `orphan_rejected` for arrival 2 would close an `episode_started` for arrival 1,
#: and a stray terminal with no opener would drive a counter negative. With two
#: workers these interleave constantly.
#:
#: The authoritative pairing already exists in lab_verify_log: `calls.one_terminal`
#: keys llm_request against llm_response/llm_error BY request_id, and the episode
#: checks key by arrival. This mirrors that rather than inventing a second
#: convention -- the same mistake in a different form would be a second pairing
#: rule that disagrees with the verifier's.
COVERAGE_MAP: dict = {
    'llm_request': (('llm_response', 'llm_error'), 'request_id'),
    'episode_started': (('episode_revealed', 'orphan_rejected'), 'arrival'),
}

#: Coverers protocol 12.6 item 4 NAMES but the event vocabulary does not
#: represent as an interval. Recorded, not silently dropped.
UNREPRESENTED_COVERERS: dict = {
    'sandbox execution': ('the chain has no sandbox_started/sandbox_ended pair; a '
                          'sandbox run happens inside an episode, so '
                          'episode_started..episode_revealed is the nearest '
                          'interval the schema actually carries'),
    '/metrics scrape': ('metrics_scrape is a POINT event, not a pair, so an "open '
                        'scrape" has no representation to detect'),
}


def _validate_coverage_map(vocabulary) -> list:
    """Every name in COVERAGE_MAP must exist in the chain vocabulary.

    This is the guard that would have caught the invented names immediately
    instead of letting them never match.
    """
    known = set(vocabulary)
    bad = []
    for opener, (closers, key) in COVERAGE_MAP.items():
        if opener not in known:
            bad.append('opener %r is not a chain event type' % opener)
        for c in closers:
            if c not in known:
                bad.append('closer %r is not a chain event type' % c)
        if not key:
            bad.append('opener %r declares no identity field' % opener)
    return bad


def gap_report(events: list, gap_report_s: float = 5.0,
               vocabulary=None) -> dict:
    """Every gap above ``gap_report_s`` between consecutive events that is NOT
    covered by an open interval in ``COVERAGE_MAP``.

    Finding N3's false-FAIL case is the point: a 10 s sandbox run is a COVERED
    gap and reporting it would be a false alarm. But see UNREPRESENTED_COVERERS:
    two of the three coverers the protocol names have no interval in the event
    vocabulary, so this function CANNOT detect them and says so rather than
    reporting their gaps as though they were unexplained.
    """
    if vocabulary is None:
        import lab_eventlog as _el
        vocabulary = set(_el.TRIAL_ONLY_TYPES) | set(_el.PROGRAM_ONLY_TYPES)
    bad = _validate_coverage_map(vocabulary)
    if bad:
        return {'gap_report_s': gap_report_s, 'computable': False,
                'reason': 'the coverage map names events the chain does not have: '
                          + '; '.join(bad),
                'reported_gaps': None}

    closers: dict = {}
    for opener, (cs, key) in COVERAGE_MAP.items():
        for c in cs:
            closers.setdefault(c, []).append((opener, key))

    # opener type -> set of OPEN IDENTITIES, not a count
    open_ids: dict = {k: set() for k in COVERAGE_MAP}
    unmatched_terminals = []
    gaps = []
    prev = None
    for e in events:
        t = e.get('t_wall_ns')
        kind = e.get('type')
        body = e.get('body') or {}
        if prev is not None and t is not None and prev[1] is not None:
            delta = (int(t) - int(prev[1])) / 1e9
            if delta > gap_report_s:
                covered = sorted(k for k, ids in open_ids.items() if ids)
                gaps.append({'after_seq': prev[0], 'before_seq': e.get('seq'),
                             'seconds': delta, 'covered_by': covered,
                             'open_identities': {k: sorted(map(str, ids))
                                                 for k, ids in open_ids.items() if ids},
                             'reported': not covered})
        if kind in COVERAGE_MAP:
            key = COVERAGE_MAP[kind][1]
            ident = body.get(key)
            if ident is None:
                unmatched_terminals.append(
                    {'seq': e.get('seq'), 'type': kind,
                     'problem': 'opener carries no %r' % key})
            else:
                open_ids[kind].add(ident)
        for opener, key in closers.get(kind, ()):
            ident = body.get(key)
            if ident is None:
                unmatched_terminals.append(
                    {'seq': e.get('seq'), 'type': kind,
                     'problem': 'closer carries no %r' % key})
            elif ident in open_ids[opener]:
                open_ids[opener].discard(ident)
            else:
                # A terminal whose opener was never seen. Counting would have
                # decremented someone else's interval closed.
                unmatched_terminals.append(
                    {'seq': e.get('seq'), 'type': kind, 'identity': str(ident),
                     'problem': 'closer with no matching open %r' % opener})
        prev = (e.get('seq'), t)
    reported = [g for g in gaps if g['reported']]
    return {
        'gap_report_s': gap_report_s, 'computable': True,
        'coverage_map': {k: {'closers': list(v[0]), 'identity_field': v[1]}
                         for k, v in COVERAGE_MAP.items()},
        'paired_by': 'IDENTITY, mirroring lab_verify_log calls.one_terminal '
                     '(request_id) and the episode checks (arrival). Counting by '
                     'type would let one interval close another.',
        'unmatched_terminals': unmatched_terminals,
        'gaps_above_threshold': len(gaps),
        'covered_gaps': len(gaps) - len(reported),
        'reported_gaps': reported,
        'unrepresented_coverers': UNREPRESENTED_COVERERS,
        'limits': ('a gap covered by an open interval in COVERAGE_MAP is NOT '
                   'reported (finding N3 false-FAIL case). Coverage by a sandbox '
                   'execution or a /metrics scrape CANNOT be detected here -- the '
                   'vocabulary carries no interval for either -- so such a gap is '
                   'reported and must be read as UNEXPLAINED-BY-THIS-CHECK rather '
                   'than as unexplained.'),
        'still_open_at_end': {k: sorted(map(str, ids))
                              for k, ids in open_ids.items() if ids},
    }



def acceptance_latency(events: list, list_above_s: float = 1.0) -> dict:
    """Protocol 12.6 item 5: the distribution of ``job_accepted - coin_drawn`` on
    the monotonic clock, with every gap above 1 s listed.

    WHICH MONOTONIC CLOCK. Both timestamps are taken from the ENVELOPE's
    ``t_mono_ns``, which is stamped by whoever wrote the event into the chain --
    one writer, therefore one clock domain. ``job_accepted`` ALSO carries
    ``worker_t_mono_ns``, and that is a DIFFERENT PROCESS's monotonic clock with
    its own epoch; subtracting it from an orchestrator stamp would produce a
    number with no meaning. The worker reading is recorded here for reference and
    never differenced against the coin.

    PAIRING. ``coin_drawn`` keys by ``pair`` and carries an ``assignment`` map
    from ARRIVAL to arm; ``job_accepted`` keys by ``arrival``. The mapping is the
    one lab_verify_log already builds (``assign_seq_of_arrival``), reused rather
    than re-derived.
    """
    coin_at: dict = {}
    for ev in events:
        if ev.get('type') != 'coin_drawn':
            continue
        for a in (ev.get('body') or {}).get('assignment') or {}:
            coin_at.setdefault(int(a), ev)

    rows, unmatched = [], []
    for ev in events:
        if ev.get('type') != 'job_accepted':
            continue
        arrival = (ev.get('body') or {}).get('arrival')
        if arrival is None:
            unmatched.append({'seq': ev.get('seq'),
                              'problem': 'job_accepted carries no arrival'})
            continue
        coin = coin_at.get(int(arrival))
        if coin is None:
            unmatched.append({'seq': ev.get('seq'), 'arrival': int(arrival),
                              'problem': 'no coin_drawn assigns this arrival'})
            continue
        a_mono, c_mono = ev.get('t_mono_ns'), coin.get('t_mono_ns')
        if a_mono is None or c_mono is None:
            unmatched.append({'seq': ev.get('seq'), 'arrival': int(arrival),
                              'problem': 'missing envelope t_mono_ns'})
            continue
        rows.append({'arrival': int(arrival), 'coin_seq': coin.get('seq'),
                     'accept_seq': ev.get('seq'),
                     'seconds': (int(a_mono) - int(c_mono)) / 1e9,
                     'worker_t_mono_ns': (ev.get('body') or {}).get('worker_t_mono_ns')})

    xs = sorted(r['seconds'] for r in rows)
    def q(p):
        if not xs:
            return None
        k = max(1, min(len(xs), int(math.ceil(p * len(xs)))))
        return xs[k - 1]
    negatives = [r for r in rows if r['seconds'] < 0]
    return {
        'clock': 'envelope t_mono_ns (one writer, one domain)',
        'worker_clock_not_differenced': ('job_accepted.worker_t_mono_ns is a '
                                         'DIFFERENT process monotonic clock and is '
                                         'recorded, never subtracted from a coin '
                                         'stamp'),
        'n': len(rows),
        'min': xs[0] if xs else None, 'median': q(0.5),
        'p95': q(0.95), 'max': xs[-1] if xs else None,
        'above_threshold_s': list_above_s,
        'listed_above_threshold': [r for r in rows if r['seconds'] > list_above_s],
        'negative_latencies': negatives,
        'negative_note': ('a job accepted BEFORE its coin was drawn is a '
                          'write-ahead violation, not a small number; listed '
                          'separately so it cannot hide inside a distribution'),
        'unmatched': unmatched,
        'rows': rows,
    }


def server_log_prefix(events: list) -> dict:
    """Protocol 12.6 item 6: the prefix property of the server logs across anchors.

    Each ``anchor`` carries ``server_log_bytes`` and ``server_log_sha256``. Across
    consecutive anchors the log may only GROW, so the byte count must be
    non-decreasing.

    WHAT THIS CANNOT DO FROM THE CHAIN ALONE, stated rather than implied: the
    digest at anchor k is over the first ``server_log_bytes[k]`` bytes. Verifying
    that anchor k's digest really is the prefix of anchor k+1's log requires the
    LOG ITSELF, which is not in the chain. From the chain this checks
    monotonicity and reports the digests for an external check; it does not
    establish the prefix property.
    """
    anchors = [e for e in events if e.get('type') == 'anchor']
    rows, violations = [], []
    prev = None
    for a in anchors:
        b = a.get('body') or {}
        n, d = b.get('server_log_bytes'), b.get('server_log_sha256')
        row = {'anchor_seq': b.get('anchor_seq'), 'seq': a.get('seq'),
               'server_log_bytes': n, 'server_log_sha256': d}
        if prev is not None and isinstance(n, int) and isinstance(prev[0], int):
            row['grew_by'] = n - prev[0]
            if n < prev[0]:
                row['violation'] = 'server log SHRANK between anchors'
                violations.append(row)
            elif n == prev[0] and d != prev[1]:
                row['violation'] = ('same byte count, DIFFERENT digest: the log was '
                                    'rewritten, not appended to')
                violations.append(row)
        rows.append(row)
        if isinstance(n, int):
            prev = (n, d)
    return {
        'anchors': len(anchors), 'rows': rows, 'violations': violations,
        'violation_count': len(violations),
        'established': 'byte-count monotonicity and digest stability at equal length',
        'NOT_established': ('the prefix property itself. The digest at anchor k is '
                            'over the first server_log_bytes[k] bytes and the LOG '
                            'IS NOT IN THE CHAIN, so this cannot verify that '
                            "anchor k's digest is the prefix of anchor k+1's log. "
                            'An external check holding the log must do that.'),
    }


def posthoc_object(pairs: list[dict]) -> dict:
    """``winstats.betting_log_e_ternary`` on the FINAL complete scores only.

    Post hoc descriptive, no error-control claim, not the decision rule (protocol 8.8
    item 5, PG-16).  It is computed once, after the trial has ended, and it is never fed a
    partial score and never visible to the live monitor."""
    z = [int(p['z']) for p in pairs if p['collapsed']]
    d = [int(p['d']) for p in pairs if p['collapsed']]
    out: dict = {
        'label': ('post hoc descriptive, no error-control claim, not the decision rule'),
        'n': len(z),
    }
    for name, scores in (('hierarchy', z), ('success', d)):
        if not scores:
            out[name] = None
            continue
        pos = sum(1 for s in scores if s > 0)
        neg = sum(1 for s in scores if s < 0)
        out[name] = {
            'positive': pos, 'negative': neg, 'ties': len(scores) - pos - neg,
            'log_e': float(winstats.betting_log_e_ternary(pos, neg, len(scores))),
            'summary': {k: (float(v) if isinstance(v, (int, float)) else v)
                        for k, v in dict(winstats.summary(np.array(scores,
                                                                  dtype=float))).items()},
        }
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(trials: Sequence[str], bundle_sha: str, *, results_root: Path, work_root: Path,
          out_dir: Path, mock: bool = False) -> dict:
    """Read the chains and the record files and write every table of 3.15.

    ``mock`` is forced on when any input chain's configuration marks it a dry run, so a
    mock output can never be mistaken for a trial's -- and ALSO when any input chain
    carries a simulated server body (``lab_eventlog.is_sim_server_body``): a chain that
    started no server is a dry run whatever its configuration says (EB1 fix, reviewer 1
    finding 5; the verifier's ``server.lifecycle`` FAILs such a chain under a configuration
    that is not a dry run)."""
    results_root = Path(results_root)
    work_root = Path(work_root)
    out_dir = Path(out_dir)
    cfg_path = results_root / 'freeze' / 'config.json'
    cfg = _read(cfg_path) if cfg_path.exists() else {}
    mock = bool(mock or cfg.get('mock') or cfg.get('mock_overrides'))
    reads: dict = {}
    for trial in trials:
        events_dir = results_root / trial / 'events'
        if events_dir.exists():
            reads[trial] = lab_eventlog.read_chain(events_dir, trial, bundle_sha)
            mock = mock or any(
                e['type'] in ('server_started', 'server_restarted')
                and lab_eventlog.is_sim_server_body(e['body']) for e in reads[trial].events)
    summary: dict = {'trials': {}, 'bundle_sha256': bundle_sha, 'files': {}}
    for trial in trials:
        if trial not in reads:
            summary['trials'][trial] = {'status': 'not_started'}
            continue
        read = reads[trial]
        events = read.events
        tdir = out_dir / trial
        pairs = pair_rows(events, cfg)
        episodes = episode_rows(events)
        # ONE decision object: decision.json and the summary row below are the same reading
        dobj = decision_object(events, cfg, trial)
        files = {
            'monitor_table.csv': _write_csv(tdir / 'monitor_table.csv',
                                            monitor_rows(events), mock),
            'pairs.csv': _write_csv(tdir / 'pairs.csv', pairs, mock),
            'episodes.csv': _write_csv(tdir / 'episodes.csv', episodes, mock),
            'decision.json': _write_json(tdir / 'decision.json', dobj, mock),
            'sensitivity.json': _write_json(tdir / 'sensitivity.json',
                                            sensitivity_object(pairs, episodes), mock),
            'integrity.json': _write_json(tdir / 'integrity.json',
                                          integrity_object(events, cfg), mock),
            'posthoc_betting.json': _write_json(tdir / 'posthoc_betting.json',
                                                posthoc_object(pairs), mock),
        }
        ledger_src = results_root / trial / 'exposure_ledger.json'
        if ledger_src.exists():
            files['exposure_ledger.json'] = _write_json(
                tdir / 'exposure_ledger.json', _read(ledger_src), mock)
        terminal = terminal_event(events)
        logged_kind = next((e['body']['kind'] for e in events
                            if e['type'] == 'decision'), 'none')
        # root 19:05: the summary's ``decision`` IS decision.json's ``primary_result`` --
        # never the logged kind on its own authority (03fe0ca / 7ebffad kept the logged kind
        # unless ``reportable`` was false, and an invalid decision was flagged reportable).
        # ``primary_result`` is the logged kind only when the result is reportable
        # (:func:`decision_object`, case 5).
        summary['trials'][trial] = {
            'status': terminal['body']['status'] if terminal else 'open',
            'final_head': read.events[-1]['h'] if read.events else None,
            'pairs_enrolled': sum(1 for e in events if e['type'] == 'pair_enrolled'
                                  and not e['body'].get('re_enrolled')),
            'episodes_revealed': sum(1 for e in events
                                     if e['type'] == 'episode_revealed'),
            'decision': dobj['primary_result'],
            'restart_cap_case': dobj['restart_cap']['case'],
            'reportable': dobj['reportable'],
        }
        if not dobj['reportable']:
            # an invalid decision, case (a), a crossing not acted on, or a decision without
            # its chained external receipt: the logged decision (if any) is kept beside the
            # result -- never as the result
            summary['trials'][trial]['logged_decision'] = logged_kind
        completion = dobj['restart_cap']['completion']
        if completion is not None:
            summary['trials'][trial].update({
                'arrivals_not_run': completion['arrivals_not_run'],
                'follow_up_not_run': completion['follow_up_not_run']})
        summary['files'][trial] = files
    summary['program_alpha'] = float(cfg.get('monitor', {}).get('alpha_program', 0.05))
    summary['statement'] = (
        'no selection among the trials is made and no combined claim is formed, so by the '
        'union bound over four trials P{at least one false decision statement in the '
        'program} <= 0.05')
    _write_json(out_dir / 'program_summary.json', summary, mock)
    summary['mock'] = mock
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='build_live_ab_results')
    ap.add_argument('--trials', default=','.join(lab_common.TRIALS))
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--results', default=str(lab_common.RESULTS_ROOT))
    ap.add_argument('--work', default=str(lab_common.WORK_ROOT))
    ap.add_argument('--out', required=True)
    ap.add_argument('--mock', action='store_true')
    args = ap.parse_args(argv)
    out = build([t for t in args.trials.split(',') if t], args.bundle,
                results_root=Path(args.results), work_root=Path(args.work),
                out_dir=Path(args.out), mock=bool(args.mock))
    print(canonical_json({'trials': out['trials'], 'mock': out['mock']}))
    return 0


if __name__ == '__main__':                                   # pragma: no cover
    sys.exit(main())
