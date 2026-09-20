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
def decision_object(events: Sequence[Mapping], cfg: Mapping, trial: str) -> dict:
    """The logged decision, with the reference rule's own result beside it.

    The builder does not decide: it prints what the chain carries and whether the second
    code path and the replay agree with it (protocol 8.9)."""
    logged = next((dict(e['body'], seq=int(e['seq'])) for e in events
                   if e['type'] == 'decision'), None)
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
    return {
        'trial': trial,
        'decision': logged,
        'reference_rule': reference,
        'agreement_kind_and_prefix': bool(agreement),
        'replay_agrees_elementwise': bool(replay_agrees),
        'n_shadow_mismatches': sum(1 for u in updates
                                   if u['body']['shadow']['mismatch']),
        'primary_result': ('LIVE_DECISION_INVALID (harness defect)' if not agreement
                           else (logged['kind'] if logged else 'none')),
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
    label = (coin_adjacent >= int(rule.get('coin_adjacent_events', 1))
             or len(pairs_with_terminal) >= int(rule.get('pairs_with_terminal_failure', 3)))
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
        'label_rule': rule,
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
    mock output can never be mistaken for a trial's."""
    results_root = Path(results_root)
    work_root = Path(work_root)
    out_dir = Path(out_dir)
    cfg_path = results_root / 'freeze' / 'config.json'
    cfg = _read(cfg_path) if cfg_path.exists() else {}
    mock = bool(mock or cfg.get('mock') or cfg.get('mock_overrides'))
    summary: dict = {'trials': {}, 'bundle_sha256': bundle_sha, 'files': {}}
    for trial in trials:
        events_dir = results_root / trial / 'events'
        if not events_dir.exists():
            summary['trials'][trial] = {'status': 'not_started'}
            continue
        read = lab_eventlog.read_chain(events_dir, trial, bundle_sha)
        events = read.events
        tdir = out_dir / trial
        pairs = pair_rows(events, cfg)
        episodes = episode_rows(events)
        files = {
            'monitor_table.csv': _write_csv(tdir / 'monitor_table.csv',
                                            monitor_rows(events), mock),
            'pairs.csv': _write_csv(tdir / 'pairs.csv', pairs, mock),
            'episodes.csv': _write_csv(tdir / 'episodes.csv', episodes, mock),
            'decision.json': _write_json(tdir / 'decision.json',
                                         decision_object(events, cfg, trial), mock),
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
        terminal = next((e for e in reversed(events)
                         if e['type'] in ('trial_ended', 'trial_aborted')), None)
        summary['trials'][trial] = {
            'status': terminal['body']['status'] if terminal else 'open',
            'final_head': read.events[-1]['h'] if read.events else None,
            'pairs_enrolled': sum(1 for e in events if e['type'] == 'pair_enrolled'
                                  and not e['body'].get('re_enrolled')),
            'episodes_revealed': sum(1 for e in events
                                     if e['type'] == 'episode_revealed'),
            'decision': next((e['body']['kind'] for e in events
                              if e['type'] == 'decision'), 'none'),
        }
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
