"""Round 10 owner handoff for the tau2 open-model stream: all-attempt accounting, per-unit policy flags,
post hoc omit-five sensitivity, orientation-randomization reading of the replay array, and what the saved
artifacts can and cannot verify about the settings in force.

POST HOC. Written 2026-09-19 after the collection and after the root session's Round 10 audit. Reads only saved
artifacts (tau2 logs, llama-server logs, raw tau2 JSONs, run_manifest.json, design.json, episodes.csv) and the frozen
analysis functions (imported, never modified). No model, API or git call. Never writes into raw/, logs/, or any frozen
or deposited output; it writes four new files in the results directory:

    all_attempt_accounting.csv     one row per attempt (tau2-level), every arm, unit and invocation
    unit_policy_flags.csv          one row per canonical unit: invocation, pre/post amendment, settings in force
    round10_handoff_numbers.json   every number quoted by all_attempt_accounting.md, deviation_1_erratum.md,
                                   protocol_addendum_round10.md and the Round 10 addendum of report_final.md

Usage:  .venv/bin/python experiments/tau2_open/make_round10_handoff.py [--results-dir results/tau2_open]
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, json, math, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import analysis as AN  # noqa: E402  (frozen; imported read-only)
from common import load_config, sha256_file  # noqa: E402
from design import load_design  # noqa: E402

LOCAL_UTC_OFFSET_H = -4  # tau2 and loguru print naive local time; the machine ran at UTC-4 (EDT). Checked below against the manifest.
ARMS = ('A', 'B')

RE_SEG = re.compile(r'^=== (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s*$')
RE_TS = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) \| ')
RE_RUN = re.compile(r'Running task (\d+), trial (\d+)')
RE_SKIP = re.compile(r'Skipping task (\d+), trial (\d+) because it has already been run')
RE_RESUME = re.compile(r'Resuming run from (\d+) runs\. (\d+) runs remaining')
RE_FAIL = re.compile(r'run_with_retry:97 - Task (\d+) failed \(attempt (\d+)/(\d+)\): (.*)$')
RE_FAIL_FINAL = re.compile(r'run_with_retry:101 - Task (\d+) failed after (\d+) attempts: (.*)$')
RE_TRUNC = re.compile(r'generate:427 - Output might be incomplete due to token limit!')
RE_OK_RETRY = re.compile(r'Task (\d+) succeeded on retry (\d+)')
RE_DONE = re.compile(r'Successfully completed all simulations!')
RE_CTX = re.compile(r'request \((\d+) tokens\) exceeds the available context size \((\d+) tokens\)')
RE_SRV_T = re.compile(r'^(\d+)\.(\d\d)\.(\d{3})\.(\d{3}) ')
RE_SRV_CANCEL = re.compile(r'stop: cancel task, id_task = (\d+)')
RE_SRV_ERR = re.compile(r'send_error: task id = (\d+), error: (.*)$')
RE_SRV_RELEASE = re.compile(r'release: id\s+\d+ \| task (\d+) \| stop processing: n_tokens = (\d+), truncated = (\d+)')
RE_SRV_NGEN = re.compile(r'print_timing: id\s+\d+ \| task (\d+) \| n_gen =\s+(\d+)')
RE_SRV_EVAL = re.compile(r'print_timing: id\s+\d+ \| task (\d+) \|\s+eval time =\s+[\d.]+ ms /\s+(\d+) tokens')
RE_SRV_BANNER = re.compile(r'common_params_print_info')
RE_SRV_LAUNCH = re.compile(r'launch_slot_: id\s+\d+ \| task (\d+) \| processing task')


def parse_local(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f')


def parse_iso_local(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


def to_utc(t: dt.datetime) -> dt.datetime:
    return t - dt.timedelta(hours=LOCAL_UTC_OFFSET_H)


def utc_from_ts(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).replace(tzinfo=None)


def isoz(t: dt.datetime | None) -> str:
    return '' if t is None else t.strftime('%Y-%m-%dT%H:%M:%SZ')


def classify(msg: str) -> str:
    if msg is None:
        return ''
    if 'Timeout' in msg or 'timed out' in msg:
        return 'request_timeout (litellm.Timeout: APITimeoutError)'
    if 'exceeds the available context size' in msg:
        return 'context_window_overflow (litellm.BadRequestError)'
    if 'Unterminated string' in msg:
        return 'json_decode_error_after_truncation (JSONDecodeError)'
    return 'other'


# ------------------------------------------------------------------------------------------------ tau2 logs

def parse_tau2_log(path: Path) -> list:
    """Return the invocation segments of one tau2 log: each a dict(start_utc, command, attempts, skipped, resumed, completed).

    Concurrency is 1, so the log is strictly sequential: a `Running task` line opens a unit and its attempt 1; a
    `run_with_retry:97` line closes the current attempt as failed and the next attempt opens; `run_with_retry:101`
    closes the last attempt as failed and tau2 writes the infrastructure_error placeholder. An attempt that is still
    open when the next unit opens (or when `Successfully completed all simulations!` appears) produced the saved record.
    An attempt still open at the end of a segment that never printed the completion line was interrupted.
    """
    segs = []; seg = None; cur = None; last_ts = None
    lines = path.read_text(errors='replace').splitlines()
    for ln, line in enumerate(lines, 1):
        m = RE_SEG.match(line)
        if m:
            if seg is not None:
                _close_segment(seg, cur, last_ts)
            seg = dict(log=path.name, start_marker_utc=m.group(1), command=lines[ln] if ln < len(lines) else '', attempts=[], skipped=[], resumed=None, completed=False,
                       first_line=ln)
            segs.append(seg); cur = None; last_ts = None
            continue
        if seg is None:
            continue
        t = RE_TS.match(line)
        if t:
            last_ts = parse_local(t.group(1))
            if cur is not None and cur['first_ts'] is None:
                cur['first_ts'] = last_ts
        m = RE_RESUME.search(line)
        if m:
            seg['resumed'] = dict(done=int(m.group(1)), remaining=int(m.group(2)))
        m = RE_SKIP.search(line)
        if m:
            seg['skipped'].append((m.group(1), int(m.group(2)) - 1))
        m = RE_RUN.search(line)
        if m:
            if cur is not None:
                cur.update(status='completed: produced the saved record', end_ts=last_ts, last_line=ln - 1); seg['attempts'].append(cur)
            cur = dict(task=m.group(1), trial=int(m.group(2)) - 1, attempt=1, first_line=ln, first_ts=None, n_trunc=0, trunc_lines=[], ctx=None, message='', status=None,
                       end_ts=None, max_attempts=None)
            continue
        if cur is None:
            continue
        if RE_TRUNC.search(line):
            cur['n_trunc'] += 1; cur['trunc_lines'].append(ln)
        m = RE_CTX.search(line)
        if m:
            cur['ctx'] = (int(m.group(1)), int(m.group(2)))
        m = RE_FAIL.search(line)
        if m:
            assert m.group(1) == cur['task'] and int(m.group(2)) == cur['attempt'], (path, ln, line)
            cur.update(status='failed: discarded, no simulation record', message=m.group(4).strip(), end_ts=last_ts, last_line=ln, max_attempts=int(m.group(3)))
            seg['attempts'].append(cur)
            cur = dict(task=cur['task'], trial=cur['trial'], attempt=cur['attempt'] + 1, first_line=ln + 1, first_ts=None, n_trunc=0, trunc_lines=[], ctx=None, message='',
                       status=None, end_ts=None, max_attempts=int(m.group(3)))
            continue
        m = RE_FAIL_FINAL.search(line)
        if m:
            assert m.group(1) == cur['task'] and int(m.group(2)) == cur['attempt'], (path, ln, line)
            cur.update(status='failed: discarded, no simulation record; last allowed attempt, tau2 then saved an infrastructure_error placeholder',
                       message=m.group(3).strip(), end_ts=last_ts, last_line=ln, max_attempts=int(m.group(2)), exhausted=True)
            seg['attempts'].append(cur); cur = None
            continue
        if RE_DONE.search(line):
            seg['completed'] = True
            if cur is not None:
                cur.update(status='completed: produced the saved record', end_ts=last_ts, last_line=ln - 1); seg['attempts'].append(cur); cur = None
    if seg is not None:
        seg['last_line'] = len(lines)
        _close_segment(seg, cur, last_ts)
    return segs


def _close_segment(seg, cur, last_ts):
    if cur is not None and cur.get('status') is None:
        cur.update(status='interrupted: tau2 process stopped by the owner while the attempt was running; no failure line, no simulation record', end_ts=last_ts,
                   message='(no tau2 failure line; process terminated)', interrupted=True)
        seg['attempts'].append(cur)
    seg['last_log_ts'] = last_ts


# ------------------------------------------------------------------------------------------------ llama-server logs

def parse_server_log(path: Path) -> list:
    """Server sessions (one per llama-server process; the harness appends). Relative clock = time since process start."""
    sessions = []; s = None; ngen = {}; errs = {}; launch = {}
    for ln, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        if RE_SRV_BANNER.search(line):
            s = dict(first_line=ln, cancels=[], n_requests=0, eval_tokens=0, seed_word=0); sessions.append(s); ngen = {}; errs = {}; launch = {}
        if s is None:
            continue
        if 'seed' in line.lower():
            s['seed_word'] += 1
        t = RE_SRV_T.match(line)
        rel = (int(t.group(1)) * 60 + int(t.group(2)) + int(t.group(3)) / 1e3) if t else None
        m = RE_SRV_LAUNCH.search(line)
        if m:
            launch[m.group(1)] = rel
        m = RE_SRV_NGEN.search(line)
        if m:
            ngen[m.group(1)] = int(m.group(2))
        m = RE_SRV_ERR.search(line)
        if m:
            errs[m.group(1)] = m.group(2).strip()
        m = RE_SRV_EVAL.search(line)
        if m and 'prompt eval' not in line:
            s['n_requests'] += 1; s['eval_tokens'] += int(m.group(2))
            s.setdefault('first_request_tokens', int(m.group(2)))
        m = RE_SRV_CANCEL.search(line)
        if m:
            s['cancels'].append(dict(line=ln, rel_s=rel, id_task=m.group(1), last_n_gen_logged=ngen.get(m.group(1)), server_error=errs.get(m.group(1)), slot_n_tokens=None,
                                     request_seconds=(rel - launch[m.group(1)]) if m.group(1) in launch else None))
        m = RE_SRV_RELEASE.search(line)
        if m:
            for c in s['cancels']:
                if c['id_task'] == m.group(1):
                    c['slot_n_tokens'] = int(m.group(2))
        s['last_line'] = ln
    return sessions


# ------------------------------------------------------------------------------------------------ raw JSON

def load_raw(path: Path) -> dict:
    r = json.loads(path.read_text())
    units = {}
    for s in r['simulations']:
        key = (str(s['task_id']), int(s['trial']))
        assert key not in units, key
        fin = collections.Counter(); maxc = collections.Counter(); length_tok = []; served = collections.Counter(); calls = collections.Counter(); tok = collections.Counter()
        mism = 0
        for m in s['messages']:
            role = {'assistant': 'agent', 'user': 'user'}.get(m['role'])
            if role is None or not m.get('usage'):
                continue
            rd = m.get('raw_data') or {}
            f = (rd.get('choices') or [{}])[0].get('finish_reason')
            fin['%s:%s' % (role, f)] += 1; calls[role] += 1
            c = m['usage']['completion_tokens']; tok[role + '_completion'] += c; tok[role + '_prompt'] += m['usage']['prompt_tokens']
            maxc[role] = max(maxc[role], c)
            served['%s:%s' % (role, rd.get('model'))] += 1
            if f == 'length':
                length_tok.append((role, c))
            tm = rd.get('timings') or {}
            if tm.get('predicted_n') != c or (rd.get('usage') or {}).get('completion_tokens') != c:
                mism += 1
        units[key] = dict(sim_id=s['id'], seed=s['seed'], start=parse_iso_local(s['start_time']), end=parse_iso_local(s['end_time']), duration=s['duration'],
                          termination_reason=s['termination_reason'], reward=(s['reward_info'] or {}).get('reward') if s.get('reward_info') else None,
                          info=s.get('info'), finish=dict(fin), max_completion=dict(maxc), length_responses=length_tok, served=dict(served), calls=dict(calls),
                          tokens=dict(tok), usage_timing_mismatch=mism, n_messages=len(s['messages']))
    return dict(info=r['info'], units=units)


# ------------------------------------------------------------------------------------------------ inference pieces

def r1_radius(n: int, rho: float = 100.0, alpha: float = 0.05) -> float:
    return math.sqrt((n + rho) * math.log((n + rho) / (rho * alpha ** 2))) / n


def orientation_reading(design, episodes, cfg) -> dict:
    """Orientation-randomization reading of the OBSERVED replay array (Round 10 audit, Finding 3).

    Pair k consists of two fixed (task, trial) units u1 (first arrival) and u2. Both arms were collected on both units,
    so both orientation outcomes are fixed numbers: R=1 -> z = score(B on u2 versus A on u1); R=0 -> z = score(B on u1
    versus A on u2). The realized coin selects one of them. Conditional on the full outcome array and the matching, the
    pair scores are independent, bounded in [-1, 1], with conditional mean m_k = (z_k(R=1) + z_k(R=0)) / 2.
    """
    tiers = AN.tiers_from_config(cfg)
    by = {(e['arm'], e['task_id'], e['trial']): e for e in episodes}
    pairs = collections.defaultdict(dict)
    for a in design['arrivals']:
        pairs[a['pair_index']][a['position_in_pair']] = a
    rows = []
    for k in sorted(pairs):
        a1, a2 = pairs[k][1], pairs[k][2]
        u1, u2 = (a1['task_id'], a1['trial']), (a2['task_id'], a2['trial'])
        R = a1['orientation']; assert R == a2['orientation']
        z1, _, d1 = AN.pair_scores([by[('A',) + u1]], [by[('B',) + u2]], tiers)   # R = 1
        z0, _, d0 = AN.pair_scores([by[('A',) + u2]], [by[('B',) + u1]], tiers)   # R = 0
        assert (a1['pass1_arm'] == 'A') == (R == 1)
        rows.append(dict(pair=k, R=R, z_R1=int(z1[0]), z_R0=int(z0[0]), dq_R1=int(d1[0]), dq_R0=int(d0[0]), z_obs=int(z1[0] if R == 1 else z0[0]),
                         dq_obs=int(d1[0] if R == 1 else d0[0])))
    out = {}
    for label, n in (('all_pairs_49', 49), ('block1_pairs_1_24', 24)):
        sub = rows[:n]; rad = r1_radius(n)
        for nm, ko, k1, k0 in (('net_benefit', 'z_obs', 'z_R1', 'z_R0'), ('success_difference', 'dq_obs', 'dq_R1', 'dq_R0')):
            obs = float(np.mean([r[ko] for r in sub])); target = float(np.mean([(r[k1] + r[k0]) / 2 for r in sub]))
            out.setdefault(label, {})[nm] = dict(n=n, observed_running_mean=obs, radius=rad, interval_unclipped=(obs - rad, obs + rad),
                                                 interval_clipped=(max(-1.0, obs - rad), min(1.0, obs + rad)),
                                                 orientation_averaged_target_computed_from_observed_array=target,
                                                 target_inside_interval=bool(obs - rad <= target <= obs + rad),
                                                 n_pairs_where_the_two_orientations_differ=int(sum(r[k1] != r[k0] for r in sub)))
    # the time-uniform path: is the known target inside the running interval at every n >= 1?
    zs = np.array([r['z_obs'] for r in rows], float); ms = np.array([(r['z_R1'] + r['z_R0']) / 2 for r in rows], float)
    n = np.arange(1, len(zs) + 1); rad = np.array([r1_radius(int(i)) for i in n])
    run_obs = np.cumsum(zs) / n; run_tar = np.cumsum(ms) / n
    out['path_check_net_benefit'] = dict(max_abs_running_mean_minus_running_target=float(np.max(np.abs(run_obs - run_tar))),
                                         target_inside_at_every_n=bool(np.all(np.abs(run_obs - run_tar) <= rad)), smallest_radius=float(rad[-1]),
                                         first_n_with_radius_below_1=int(n[np.argmax(rad < 1)]))
    out['n_for_radius_0p03'] = next(i for i in range(1, 200000) if r1_radius(i) <= 0.03)
    out['pairs'] = rows
    return out


def omit_five(design, episodes, cfg, five) -> dict:
    """POST HOC sensitivity: what happens to E1/E2 if the five pre-amendment arm-A units are not used."""
    base_on = AN.online_analysis(design, episodes, cfg); base_sh = AN.shadow_analysis(episodes, cfg); base_c = AN.component_effects(episodes, design, cfg)
    keyset = {('A', t, tr) for (t, tr) in five}
    tasks5 = {t for (t, _) in five}
    ep_units = [e for e in episodes if (e['arm'], e['task_id'], e['trial']) not in keyset]
    ep_tasks = [e for e in episodes if e['task_id'] not in tasks5]
    idx_all, eA, eB, _ = AN.completed_pairs(design, episodes)
    hit_unit = [k for k, a in zip(idx_all, eA) if ('A', a['task_id'], a['trial']) in keyset]
    hit_task = [k for k, a, b in zip(idx_all, eA, eB) if a['task_id'] in tasks5 or b['task_id'] in tasks5]

    def pack(eps, label, note):
        on = AN.online_analysis(design, eps, cfg); sh = AN.shadow_analysis(eps, cfg); c = AN.component_effects(eps, design, cfg)['same_task_paired']['success']
        nA = sum(e['arm'] == 'A' for e in eps); nB = sum(e['arm'] == 'B' for e in eps)
        return dict(label=label, note=note, n_units=dict(A=nA, B=nB), success=dict(A=int(sum(e['success'] for e in eps if e['arm'] == 'A')), B=int(sum(e['success'] for e in eps if e['arm'] == 'B'))),
                    E1=dict(n_pairs=on['n_pairs'], wins=on.get('wins', None), net_benefit=on['net_benefit'], nb_cs=on['nb_cs'], success_diff=on['success_diff_hat'],
                            success_diff_cs=on['success_diff_cs'], ties=on['ties'], guarded_decision=on['guarded_decision'], r1_radius=r1_radius(on['n_pairs']),
                            wtl=_wtl(design, eps, cfg)),
                    E2=dict(n_tasks=sh['n_tasks'], net_benefit=sh['net_benefit'], nb_ci=sh['nb_ci'], p_win=sh['p_win'], p_tie=sh['p_tie'], p_loss=sh['p_loss'],
                            decision=sh['decision_hierarchical'], success_diff=c['mean'], success_diff_ci=c['ci'], success_diff_n_tasks=c['n']))

    out = dict(
        label='POST HOC omit-five sensitivity. It does not replace the planned denominator (196 units, 49 pairs, 49 task clusters), which stays the analysis of record.',
        five_units=[dict(arm='A', task=t, trial=tr) for (t, tr) in five],
        five_units_design_role=[dict(task=e['task_id'], trial=e['trial'], design_pass=e['pass'], pair_index=e['pair_index'], reward=e['reward'],
                                     enters_E1=bool(e['pass'] == 1)) for e in episodes if (e['arm'], e['task_id'], e['trial']) in keyset],
        E1_pairs_dropped_variant_a=hit_unit, E1_pairs_dropped_variant_b=hit_task,
        planned=dict(E1=dict(n_pairs=base_on['n_pairs'], net_benefit=base_on['net_benefit'], nb_cs=base_on['nb_cs'], success_diff=base_on['success_diff_hat'],
                             success_diff_cs=base_on['success_diff_cs'], wtl=_wtl(design, episodes, cfg), r1_radius=r1_radius(base_on['n_pairs'])),
                     E2=dict(n_tasks=base_sh['n_tasks'], net_benefit=base_sh['net_benefit'], nb_ci=base_sh['nb_ci'], success_diff=base_c['same_task_paired']['success']['mean'],
                             success_diff_ci=base_c['same_task_paired']['success']['ci'])),
        variant_a=pack(ep_units, 'a: omit the five arm-A units only',
                       'E1 loses every prespecified pair whose arm-A member is one of the five units (the arm-B partner of such a pair is then unused). E2 keeps all 49 task '
                       'clusters; for tasks 1-5 arm A contributes trial 1 only, so the task score averages 2 comparisons (A trial 1 versus B trials 0 and 1) instead of 4, and '
                       'the same-trial (shared-seed) comparison A0-B0 is among those removed. The success difference for tasks 1-5 is mean(B trials 0,1) - A trial 1.'),
        variant_b=pack(ep_tasks, 'b: omit tasks 1-5 entirely (both arms, both trials)',
                       'E1 loses every prespecified pair with a member (either arm) on tasks 1-5. E2 has 44 task clusters. This removes 20 units, 15 of which were collected '
                       'under the amended settings, so it discards more than the amendment touches; shown only to bracket variant a.'))
    return AN._clean(out)


def _wtl(design, eps, cfg):
    idx, eA, eB, _ = AN.completed_pairs(design, eps)
    z, _, _ = AN.pair_scores(eA, eB, AN.tiers_from_config(cfg))
    return [int((z > 0).sum()), int((z == 0).sum()), int((z < 0).sum())]


# ------------------------------------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(ROOT / 'results' / 'tau2_open'))
    args = ap.parse_args(argv)
    rd = Path(args.results_dir); logs = rd / 'logs'
    cfg = load_config(); design = load_design(rd); episodes = AN.load_episodes(rd / 'episodes.csv')
    manifest = json.loads((rd / 'run_manifest.json').read_text())
    invs = manifest['invocations']
    assert len(invs) == 2 and 'config_amendment' not in invs[0] and invs[1]['config_amendment']['id'] == 1
    inv_start = [dt.datetime.strptime(i['started_at'], '%Y-%m-%dT%H:%M:%SZ') for i in invs]
    amendment = invs[1]['config_amendment']

    # ---- tau2 logs -> segments -> invocations
    segA = parse_tau2_log(logs / 'tau2_armA.log'); segB = parse_tau2_log(logs / 'tau2_armB.log'); segP = parse_tau2_log(logs / 'tau2_armA.invocation1_preamendment.log')
    assert len(segA) == 2 and len(segB) == 1 and len(segP) == 1
    pre = (logs / 'tau2_armA.invocation1_preamendment.log').read_bytes(); full = (logs / 'tau2_armA.log').read_bytes()
    pre_is_prefix = full[:len(pre)] == pre
    assert [(a['task'], a['trial'], a['attempt'], a['status']) for a in segP[0]['attempts']] == [(a['task'], a['trial'], a['attempt'], a['status']) for a in segA[0]['attempts']]

    def seg_invocation(seg):
        t = dt.datetime.strptime(seg['start_marker_utc'], '%Y-%m-%dT%H:%M:%SZ')
        cands = [i for i, s in enumerate(inv_start) if s <= t]
        return max(cands)
    seg_list = [('A', segA[0]), ('A', segA[1]), ('B', segB[0])]
    for arm, seg in seg_list:
        seg['arm'] = arm; seg['inv'] = seg_invocation(seg)
    assert [s['inv'] for _, s in seg_list] == [0, 1, 1]

    # local clock check: the first timestamped tau2 line of a segment is within a few seconds of the segment's UTC marker
    clock = []
    for arm, seg in seg_list:
        first = next(a['first_ts'] for a in seg['attempts'] if a['first_ts'] is not None)
        clock.append((to_utc(first) - dt.datetime.strptime(seg['start_marker_utc'], '%Y-%m-%dT%H:%M:%SZ')).total_seconds())
    assert all(0 <= c < 60 for c in clock), clock

    raw = {arm: load_raw(rd / 'raw' / ('tau2_open_arm%s.json' % arm)) for arm in ARMS}
    planned = [(arm, t, tr) for arm in ARMS for tr in range(cfg['num_trials']) for t in sorted(cfg['task_ids'], key=lambda x: (len(x), x))]
    assert len(planned) == 196

    # ---- llama-server sessions (8081 has one session per invocation; 8082 exists only in invocation 2)
    srv81 = parse_server_log(logs / 'llama_server_8081.log'); srv82 = parse_server_log(logs / 'llama_server_8082.log')
    assert len(srv81) == 2 and len(srv82) == 1
    for s, i in ((srv81[0], 0), (srv81[1], 1)):
        s['inv'] = i
        for c in s['cancels']:
            c['utc'] = inv_start[i] + dt.timedelta(seconds=c['rel_s'])   # server process starts with the invocation; alignment checked below
            c['kind'] = ('context_window_overflow_rejected' if c['server_error'] else
                         ('client_timeout_after_about_600s' if (c['request_seconds'] or 0) >= 590 else 'aborted_when_the_owner_stopped_invocation_1'))

    # ---- attempts table
    att_rows = []; per_unit = collections.defaultdict(list)
    for arm, seg in seg_list:
        prev_end = None
        for a in seg['attempts']:
            a['arm'] = arm; a['inv'] = seg['inv']
            a['win_start'] = prev_end if prev_end is not None else a['first_ts']
            prev_end = a['end_ts']
            per_unit[(arm, a['task'], a['trial'])].append(a)
    align = []
    for arm, seg in seg_list:
        if arm != 'A':
            continue
        sess = srv81[seg['inv']]
        for a in seg['attempts']:
            lo = to_utc(a['win_start']) + dt.timedelta(seconds=3) if (a['win_start'] and a['attempt'] > 1) else (to_utc(a['win_start']) if a['win_start'] else None)
            hi = to_utc(a['end_ts']) + dt.timedelta(seconds=3) if a['end_ts'] else None
            if a.get('interrupted'):
                hi = None
            cs = [c for c in sess['cancels'] if (lo is None or c['utc'] > lo) and (hi is None or c['utc'] <= hi)]
            if a['status'].startswith('completed'):
                assert not cs, (a['task'], a['trial'], cs)
            a['srv_cancels'] = cs
            if a.get('interrupted') and cs:
                a['end_ts_utc_override'] = cs[-1]['utc']; a['end_basis'] = 'last llama-server event of the invocation (tau2 printed no timestamped line after the retry started)'
            if cs and not a.get('interrupted'):
                align.append((to_utc(a['end_ts']) - cs[-1]['utc']).total_seconds())
    n_assigned = sum(len(a.get('srv_cancels', [])) for _, seg in seg_list for a in seg['attempts'])
    assert n_assigned == sum(len(s['cancels']) for s in srv81), (n_assigned, [len(s['cancels']) for s in srv81])

    for (arm, task, trial), atts in per_unit.items():
        rec = raw[arm]['units'][(task, trial)]
        for j, a in enumerate(atts, 1):
            last = j == len(atts)
            cs = a.get('srv_cancels', [])
            att_rows.append(dict(
                arm=arm, task=task, trial=trial, tau2_seed=rec['seed'], invocation_index=a['inv'] + 1, invocation_id=invs[a['inv']]['invocation_id'],
                settings='pre-amendment (no max_tokens, no --timeout)' if a['inv'] == 0 else 'amendment 1 (max_tokens=1024 both roles, --timeout 1800)',
                attempt_in_invocation=a['attempt'], attempt_overall=j, n_attempts_overall=len(atts), tau2_max_attempts=a.get('max_attempts') or 4,
                attempt_status=a['status'], failure_class=classify(a['message']) if not a['status'].startswith('completed') and not a.get('interrupted') else ('owner_stop_of_invocation_1' if a.get('interrupted') else ''),
                failure_message=a['message'] if not a['status'].startswith('completed') else '',
                context_request_tokens=a['ctx'][0] if a['ctx'] else '', context_limit_tokens=a['ctx'][1] if a['ctx'] else '',
                truncation_warnings_in_attempt=a['n_trunc'], truncation_warning_log_lines=' '.join(map(str, a['trunc_lines'])),
                server_side_cancelled_requests=len(cs), server_side_cancel_kinds=';'.join(sorted({c['kind'] for c in cs})),
                server_side_max_generated_tokens_at_cancel=max([c['last_n_gen_logged'] or 0 for c in cs], default=''),
                server_side_requests_timed_out_at_600s=sum(c['kind'].startswith('client_timeout') for c in cs),
                server_side_requests_aborted_at_owner_stop=sum(c['kind'].startswith('aborted') for c in cs),
                server_side_requests_rejected_context_overflow=sum(c['kind'].startswith('context') for c in cs),
                attempt_start_utc_approx=isoz(to_utc(a['win_start'])) if a['win_start'] else '',
                attempt_end_utc=isoz(a.get('end_ts_utc_override') or (to_utc(a['end_ts']) if a['end_ts'] else None)),
                attempt_wall_clock_s_approx=round(((a.get('end_ts_utc_override') or to_utc(a['end_ts'])) - to_utc(a['win_start'])).total_seconds(), 1) if (a['win_start'] and a['end_ts']) else '',
                attempt_end_basis=a.get('end_basis', 'tau2 log timestamp (local time + 4 h)'), log_file=('tau2_arm%s.log' % arm), log_first_line=a['first_line'],
                is_canonical_record_source=bool(last and a['status'].startswith('completed')),
                canonical_termination_reason=rec['termination_reason'], canonical_reward='' if rec['reward'] is None else rec['reward'],
                canonical_record_basis=('this attempt' if (last and a['status'].startswith('completed')) else
                                        ('placeholder written by tau2 after this attempt (attempts exhausted)' if (last and a.get('exhausted')) else 'a later attempt'))))
    att_rows.sort(key=lambda r: (r['arm'], r['trial'], int(r['task']), r['attempt_overall']))

    # ---- reconciliation
    canon = {(arm, t, tr) for arm in ARMS for (t, tr) in raw[arm]['units']}
    assert canon == set(planned) and set(per_unit) == set(planned)
    n_attempts = len(att_rows)
    by_status = collections.Counter('completed' if r['attempt_status'].startswith('completed') else ('interrupted' if r['attempt_status'].startswith('interrupted') else 'failed') for r in att_rows)
    by_class = collections.Counter(r['failure_class'] for r in att_rows if r['failure_class'])
    within_inv_retries = sum(1 for r in att_rows if r['attempt_in_invocation'] > 1)
    cross_inv_reruns = sum(1 for (k, atts) in per_unit.items() if len({a['inv'] for a in atts}) > 1)
    units_multi = {('%s task %s trial %d' % k): len(v) for k, v in per_unit.items() if len(v) > 1}
    trunc_canon_log = sum(r['truncation_warnings_in_attempt'] for r in att_rows if r['is_canonical_record_source'])
    trunc_disc_log = sum(r['truncation_warnings_in_attempt'] for r in att_rows if not r['is_canonical_record_source'])
    trunc_raw = {arm: {('task %s trial %d' % k): v['length_responses'] for k, v in raw[arm]['units'].items() if v['length_responses']} for arm in ARMS}
    n_trunc_raw = sum(len(v) for arm in ARMS for v in trunc_raw[arm].values())
    # per-unit agreement between log warnings in the record-producing attempt and finish_reason=length in the raw record
    for r in att_rows:
        if r['is_canonical_record_source']:
            assert r['truncation_warnings_in_attempt'] == len(raw[r['arm']]['units'][(r['task'], r['trial'])]['length_responses']), r
    term = {arm: dict(collections.Counter(v['termination_reason'] for v in raw[arm]['units'].values())) for arm in ARMS}
    infra = [dict(arm=arm, task=k[0], trial=k[1], error_type=v['info'].get('error_type'), error=v['info'].get('error'), failed_after_attempts=v['info'].get('failed_after_attempts'),
                  placeholder_written_local=v['start'].isoformat(), n_messages=v['n_messages'], duration=v['duration'])
             for arm in ARMS for k, v in raw[arm]['units'].items() if v['termination_reason'] == 'infrastructure_error']
    resumed = {('%s inv %d' % (arm, seg['inv'] + 1)): dict(resumed=seg['resumed'], skipped=len(seg['skipped']), completed=seg['completed'], n_attempts=len(seg['attempts']))
               for arm, seg in seg_list}
    arm_runs = {r['arm']: r for r in invs[1].get('arm_runs', [])}
    recon = dict(
        planned_units=len(planned), unique_canonical_units=len(canon), missing_outcomes=len(set(planned) - canon), duplicate_units=0,
        total_attempts_started=n_attempts, attempts_by_arm={arm: sum(r['arm'] == arm for r in att_rows) for arm in ARMS},
        attempts_by_invocation={str(i + 1): sum(r['invocation_index'] == i + 1 for r in att_rows) for i in range(2)},
        attempts_that_produced_the_saved_trajectory_record=by_status['completed'], attempts_discarded=by_status['failed'] + by_status['interrupted'],
        discarded_failed_with_tau2_failure_line=by_status['failed'], discarded_interrupted_by_owner_stop=by_status['interrupted'],
        discarded_by_cause=dict(by_class), extra_attempts_beyond_one_per_unit=n_attempts - len(planned), tau2_within_invocation_retries=within_inv_retries,
        cross_invocation_reruns_of_a_unit_without_record=cross_inv_reruns, units_with_more_than_one_attempt=units_multi,
        tau2_TIMEOUT_terminations=sum(term[a].get('timeout', 0) for a in ARMS), termination_reasons=term,
        request_level_timeouts_seen_by_llama_server_invocation1=sum(1 for c in srv81[0]['cancels'] if c['kind'].startswith('client_timeout')),
        requests_aborted_by_owner_stop_invocation1=sum(1 for c in srv81[0]['cancels'] if c['kind'].startswith('aborted')),
        request_level_context_rejections_seen_by_llama_server_invocation2=sum(1 for c in srv81[1]['cancels'] if c['kind'].startswith('context')),
        server_cancel_detail_invocation1=[dict(rel_s=c['rel_s'], utc=isoz(c['utc']), kind=c['kind'], request_seconds=c['request_seconds'], last_n_gen_logged=c['last_n_gen_logged'],
                                               slot_n_tokens_prompt_plus_generated=c['slot_n_tokens']) for c in srv81[0]['cancels']],
        server_cancels_8082=len(srv82[0]['cancels']), server_clock_alignment_s=dict(max_abs=max(abs(x) for x in align), values=align),
        truncated_responses_in_canonical_records=n_trunc_raw, truncated_responses_in_canonical_records_detail=trunc_raw,
        truncation_warnings_in_logs_total=trunc_canon_log + trunc_disc_log, truncation_warnings_in_record_producing_attempts=trunc_canon_log,
        truncation_warnings_in_discarded_attempts=trunc_disc_log,
        truncation_warnings_in_discarded_attempts_detail=[dict(arm=r['arm'], task=r['task'], trial=r['trial'], invocation=r['invocation_index'], attempt=r['attempt_in_invocation'],
                                                               n=r['truncation_warnings_in_attempt']) for r in att_rows if not r['is_canonical_record_source'] and r['truncation_warnings_in_attempt']],
        infrastructure_error_units=infra, n_infrastructure_error_units=len(infra), units_with_missing_reward=sum(v['reward'] is None for a in ARMS for v in raw[a]['units'].values()),
        infrastructure_error_units_rerun_after_invocation2=0,
        manifest_n_infrastructure_error_rerun_on_resume={a: arm_runs.get(a, {}).get('n_infrastructure_error_rerun_on_resume') for a in ARMS},
        log_segments=resumed, preamendment_log_is_byte_prefix_of_armA_log=bool(pre_is_prefix), tau2_clock_vs_marker_s=clock)
    assert recon['truncation_warnings_in_record_producing_attempts'] == n_trunc_raw

    # ---- unit policy flags
    five = [(u['task'], int(u['trial'])) for u in amendment['pre_amendment_units']]
    flag_rows = []
    for arm, t, tr in planned:
        v = raw[arm]['units'][(t, tr)]
        start_utc = to_utc(v['start'])
        inv_i = 0 if start_utc < inv_start[1] else 1
        atts = per_unit[(arm, t, tr)]
        if v['termination_reason'] != 'infrastructure_error':
            assert atts[-1]['inv'] == inv_i
        prea = inv_i == 0
        assert prea == (arm == 'A' and (t, tr) in five)
        e = next(x for x in episodes if (x['arm'], x['task_id'], x['trial']) == (arm, t, tr))
        flag_rows.append(dict(
            arm=arm, task=t, trial=tr, tau2_seed=v['seed'], invocation_index=inv_i + 1, invocation_id=invs[inv_i]['invocation_id'], invocation_started_utc=invs[inv_i]['started_at'],
            pre_amendment=str(prea).lower(), amendment_in_force='none' if prea else '1',
            agent_max_tokens='not sent' if prea else amendment['agent_llm_args_extra']['max_tokens'], user_max_tokens='not sent' if prea else amendment['user_llm_args_extra']['max_tokens'],
            tau2_simulation_timeout_s='none' if prea else amendment['tau2_extra_flags'][1], runner_sha256=invs[inv_i]['harness_file_sha256']['run_tau2_open.py'],
            n_attempts_all_invocations=len(atts), n_discarded_attempts=len(atts) - (0 if v['termination_reason'] == 'infrastructure_error' else 1) if len(atts) > 1 or v['termination_reason'] == 'infrastructure_error' else 0,
            canonical_termination_reason=v['termination_reason'], reward='' if v['reward'] is None else v['reward'], success=str(bool(e['success'])).lower(),
            record_start_utc=isoz(start_utc), record_end_utc=isoz(to_utc(v['end'])), duration_s=round(v['duration'], 3),
            max_agent_completion_tokens=v['max_completion'].get('agent', 0), max_user_completion_tokens=v['max_completion'].get('user', 0),
            n_agent_responses_finish_length=sum(1 for r, _ in v['length_responses'] if r == 'agent'), n_user_responses_finish_length=sum(1 for r, _ in v['length_responses'] if r == 'user'),
            unit_design_pair_index=e['pair_index'], this_arm_episode_design_pass=e['pass'], this_arm_episode_enters_E1_pairs=str(e['pass'] == 1).lower()))
    assert sum(r['pre_amendment'] == 'true' for r in flag_rows) == 5

    # ---- settings verification from artifacts
    def agg(arm, keys):
        c = collections.Counter()
        for k in keys:
            c.update(raw[arm]['units'][k]['served'])
        return dict(c)
    all_keys = {arm: list(raw[arm]['units']) for arm in ARMS}
    preA = [k for k in all_keys['A'] if k in five]; postA = [k for k in all_keys['A'] if k not in five]

    def maxc(arm, keys, role):
        return max([raw[arm]['units'][k]['max_completion'].get(role, 0) for k in keys] or [0])
    cmds = {i + 1: {a: invs[i]['tau2_commands'][a] for a in ARMS} for i in range(2)}

    def flagval(cmd, flag):
        return cmd[cmd.index(flag) + 1] if flag in cmd else None
    settings = dict(
        served_model_ids={arm: agg(arm, all_keys[arm]) for arm in ARMS},
        info_block_llm_args={arm: dict(agent=raw[arm]['info']['agent_info']['llm_args'], user=raw[arm]['info']['user_info']['llm_args'], seed=raw[arm]['info'].get('seed')) for arm in ARMS},
        info_block_note='tau2 try_resume() returns the PREVIOUS Results object when it resumes (checkpoint.py), so arm A keeps the invocation-1 info block; the config diff '
                        "was logged at resume: \"dictionary_item_added: root['user_info']['llm_args']['max_tokens'], root['agent_info']['llm_args']['max_tokens']\"",
        cap=dict(length_finished_responses={arm: [dict(unit='task %s trial %d' % k, role=r, completion_tokens=c) for k, v in raw[arm]['units'].items() for r, c in v['length_responses']] for arm in ARMS},
                 max_completion_tokens=dict(A_pre_amendment=dict(agent=maxc('A', preA, 'agent'), user=maxc('A', preA, 'user')),
                                            A_post_amendment=dict(agent=maxc('A', postA, 'agent'), user=maxc('A', postA, 'user')),
                                            B=dict(agent=maxc('B', all_keys['B'], 'agent'), user=maxc('B', all_keys['B'], 'user'))),
                 n_responses_above_1024_post_amendment=sum(1 for arm, keys in (('A', postA), ('B', all_keys['B'])) for k in keys for role in ('agent', 'user')
                                                           if raw[arm]['units'][k]['max_completion'].get(role, 0) > 1024)),
        timeout=dict(flag_in_manifest_command={str(i): {a: flagval(cmds[i][a], '--timeout') for a in ARMS} for i in cmds},
                     max_tokens_in_manifest_command={str(i): {a: dict(agent=json.loads(flagval(cmds[i][a], '--agent-llm-args')).get('max_tokens'),
                                                                      user=json.loads(flagval(cmds[i][a], '--user-llm-args')).get('max_tokens')) for a in ARMS} for i in cmds},
                     executed_command_in_log={('%s inv %d' % (arm, seg['inv'] + 1)): dict(has_timeout_1800='--timeout 1800' in seg['command'], has_max_tokens_1024=seg['command'].count('"max_tokens": 1024'))
                                              for arm, seg in seg_list},
                     timeout_terminations=recon['tau2_TIMEOUT_terminations'], longest_simulation_s={arm: max(v['duration'] for v in raw[arm]['units'].values()) for arm in ARMS}),
        seed=dict(unit_seed_counts={arm: dict(collections.Counter(v['seed'] for v in raw[arm]['units'].values())) for arm in ARMS},
                  seed_by_trial={arm: {str(tr): sorted({v['seed'] for k, v in raw[arm]['units'].items() if k[1] == tr}) for tr in (0, 1)} for arm in ARMS},
                  seed_key_in_info_llm_args={arm: dict(agent='seed' in raw[arm]['info']['agent_info']['llm_args'], user='seed' in raw[arm]['info']['user_info']['llm_args']) for arm in ARMS},
                  occurrences_of_word_seed_in_llama_server_logs=dict(port8081=sum(s['seed_word'] for s in srv81), port8082=sum(s['seed_word'] for s in srv82)),
                  request_bodies_saved=False),
        tokens=dict(episodes_tokens_source=dict(collections.Counter(e['tokens_source'] for e in episodes)), episodes_tokens_estimated_calls=int(sum(e['tokens_estimated_calls'] or 0 for e in episodes)),
                    responses_where_usage_differs_from_llamacpp_timings_predicted_n={arm: sum(v['usage_timing_mismatch'] for v in raw[arm]['units'].values()) for arm in ARMS},
                    raw_totals={arm: dict(sum((collections.Counter(v['tokens']) for v in raw[arm]['units'].values()), collections.Counter())) for arm in ARMS},
                    raw_calls={arm: dict(sum((collections.Counter(v['calls']) for v in raw[arm]['units'].values()), collections.Counter())) for arm in ARMS},
                    llama_server_8082_log=dict(n_completed_requests=srv82[0]['n_requests'], generated_tokens=srv82[0]['eval_tokens'],
                                               note='port 8082 served only the arm-B agent plus one 2-token smoke completion'),
                    llama_server_8081_log=[dict(invocation=s['inv'] + 1, n_completed_requests=s['n_requests'], generated_tokens=s['eval_tokens']) for s in srv81]))
    b = settings['tokens']
    b['check_8082_equals_armB_agent_plus_smoke'] = dict(
        requests=(srv82[0]['n_requests'], b['raw_calls']['B']['agent'] + 1), tokens=(srv82[0]['eval_tokens'], b['raw_totals']['B']['agent_completion'] + invs[1]['smoke_checks']['8082']['usage']['completion_tokens']))
    assert b['check_8082_equals_armB_agent_plus_smoke']['requests'][0] == b['check_8082_equals_armB_agent_plus_smoke']['requests'][1]
    assert b['check_8082_equals_armB_agent_plus_smoke']['tokens'][0] == b['check_8082_equals_armB_agent_plus_smoke']['tokens'][1]

    # ---- failure-inclusive operational accounting (tokens and wall-clock), separate from the canonical analysis
    def retained(arm, keys, roles):
        return sum(raw[arm]['units'][k]['tokens'].get(r + '_completion', 0) for k in keys for r in roles)
    ret1 = retained('A', preA, ('agent', 'user')); ret2 = retained('A', postA, ('agent', 'user')) + retained('B', all_keys['B'], ('user',))
    smoke2 = invs[1]['smoke_checks']['8081']['usage']['completion_tokens']
    canc1 = [c for c in srv81[0]['cancels']]
    arm_wall = {r['arm']: r.get('elapsed_s') for r in invs[1].get('arm_runs', [])}
    operational = dict(
        note='Failure-inclusive. Port 8081 served the arm-A agent and the user simulator of both arms; port 8082 served only the arm-B agent. llama-server prints a '
             'generated-token count for every COMPLETED request; a cancelled request prints none, so its generated tokens are taken from the last n_gen progress line '
             '(printed about every 3 s: a lower bound).',
        invocation1_port8081=dict(completed_requests=srv81[0]['n_requests'], generated_tokens_completed_requests=srv81[0]['eval_tokens'],
                                  smoke_tokens_first_request=srv81[0].get('first_request_tokens'), retained_in_canonical_records=ret1,
                                  generated_in_completed_requests_of_discarded_attempts=srv81[0]['eval_tokens'] - ret1 - srv81[0].get('first_request_tokens', 0),
                                  cancelled_requests=len(canc1), generated_tokens_in_cancelled_requests_lower_bound=sum(c['last_n_gen_logged'] or 0 for c in canc1),
                                  wall_clock_s=(srv81[0]['cancels'][-1]['utc'] - inv_start[0]).total_seconds(),
                                  retained_simulation_seconds=sum(raw['A']['units'][k]['duration'] for k in preA)),
        invocation2_port8081=dict(completed_requests=srv81[1]['n_requests'], generated_tokens_completed_requests=srv81[1]['eval_tokens'], smoke_tokens=smoke2,
                                  retained_in_canonical_records=ret2, generated_in_completed_requests_of_discarded_attempts=srv81[1]['eval_tokens'] - ret2 - smoke2,
                                  rejected_requests_context_overflow=len(srv81[1]['cancels'])),
        invocation2_port8082=dict(completed_requests=srv82[0]['n_requests'], generated_tokens_completed_requests=srv82[0]['eval_tokens'],
                                  retained_in_canonical_records=retained('B', all_keys['B'], ('agent',)), discarded=0),
        invocation2_arm_wall_clock_s=arm_wall,
        invocation2_retained_simulation_seconds=dict(A=sum(raw['A']['units'][k]['duration'] for k in postA), B=sum(v['duration'] for v in raw['B']['units'].values())),
        discarded_attempts=[dict(arm=r['arm'], task=r['task'], trial=r['trial'], invocation=r['invocation_index'], attempt=r['attempt_in_invocation'],
                                 start_utc_approx=r['attempt_start_utc_approx'], end_utc=r['attempt_end_utc'], wall_clock_s_approx=r['attempt_wall_clock_s_approx'])
                            for r in att_rows if not r['is_canonical_record_source']],
        discarded_attempt_wall_clock_s_approx_total={str(i): round(sum(r['attempt_wall_clock_s_approx'] or 0 for r in att_rows if not r['is_canonical_record_source'] and r['invocation_index'] == i), 1) for i in (1, 2)},
        canonical_attempt_wall_clock_minus_recorded_duration_s=dict(
            max_abs=max(abs(r['attempt_wall_clock_s_approx'] - raw[r['arm']]['units'][(r['task'], r['trial'])]['duration']) for r in att_rows if r['is_canonical_record_source'] and r['attempt_wall_clock_s_approx'] != ''),
            note='log-derived attempt windows (first/last timestamped tau2 line) versus the duration stored in the raw record; shows how approximate the windows are'))

    # ---- pre-amendment five: what was visible at decision time
    five_detail = [dict(task=t, trial=tr, reward=raw['A']['units'][(t, tr)]['reward'], termination_reason=raw['A']['units'][(t, tr)]['termination_reason'],
                        duration_s=raw['A']['units'][(t, tr)]['duration'], max_agent_completion=raw['A']['units'][(t, tr)]['max_completion'].get('agent'),
                        max_user_completion=raw['A']['units'][(t, tr)]['max_completion'].get('user')) for (t, tr) in five]
    am_path = HERE / 'config_amendment_1.json'
    erratum = dict(amendment_file_sha256=sha256_file(am_path), amendment_sha256_in_manifest=None, amendment_decided_utc_as_recorded=amendment['decided_utc'],
                   amendment_file_mtime_utc=isoz(utc_from_ts(am_path.stat().st_mtime)),
                   deviation_note_mtime_utc=isoz(utc_from_ts((HERE / 'deviation_1_runaway_generation.md').stat().st_mtime)),
                   runner_mtime_utc=isoz(utc_from_ts((HERE / 'run_tau2_open.py').stat().st_mtime)),
                   invocation1_started_utc=invs[0]['started_at'], invocation2_started_utc=invs[1]['started_at'],
                   invocation1_last_tau2_log_line_utc=isoz(to_utc(segA[0]['last_log_ts'])),
                   invocation1_last_server_event_utc=isoz(srv81[0]['cancels'][-1]['utc']),
                   runner_sha256=dict(invocation1=invs[0]['harness_file_sha256']['run_tau2_open.py'], invocation2=invs[1]['harness_file_sha256']['run_tau2_open.py'],
                                      on_disk=sha256_file(HERE / 'run_tau2_open.py')),
                   other_harness_hashes_identical={k: invs[0]['harness_file_sha256'][k] == invs[1]['harness_file_sha256'][k] for k in invs[0]['harness_file_sha256'] if k != 'run_tau2_open.py'},
                   harness_git_hash=dict(invocation1=invs[0]['harness_git_hash'], invocation2=invs[1]['harness_git_hash']), five_units=five_detail)
    mtxt = json.dumps(invs[1])
    erratum['amendment_sha256_in_manifest'] = erratum['amendment_file_sha256'] if erratum['amendment_file_sha256'] in mtxt else 'NOT FOUND in invocation-2 record'
    erratum['amendment_content_embedded_in_manifest_equals_file'] = bool({k: v for k, v in amendment.items() if not k.startswith('_') and k != 'sha256'} ==
                                                                        {k: v for k, v in json.loads(am_path.read_text()).items() if k in amendment and k != 'sha256'})

    numbers = AN._clean(dict(
        generated_by='experiments/tau2_open/make_round10_handoff.py', post_hoc=True, generated_at=isoz(utc_from_ts(__import__('time').time())),
        inputs_sha256={str(p.relative_to(rd)): sha256_file(p) for p in [rd / 'raw' / 'tau2_open_armA.json', rd / 'raw' / 'tau2_open_armB.json', rd / 'episodes.csv', rd / 'design.json',
                                                                        rd / 'run_manifest.json', logs / 'tau2_armA.log', logs / 'tau2_armA.invocation1_preamendment.log',
                                                                        logs / 'tau2_armB.log', logs / 'llama_server_8081.log', logs / 'llama_server_8082.log']},
        wincs_sha256_at_run=sha256_file(ROOT / 'src' / 'wincs.py'), reconciliation=recon, operational_accounting_failure_inclusive=operational, settings_verification=settings, erratum_facts=erratum,
        omit_five_sensitivity_POST_HOC=omit_five(design, episodes, cfg, five), orientation_randomization_reading=orientation_reading(design, episodes, cfg)))

    with open(rd / 'all_attempt_accounting.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(att_rows[0].keys())); w.writeheader(); w.writerows(att_rows)
    with open(rd / 'unit_policy_flags.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(flag_rows[0].keys())); w.writeheader(); w.writerows(flag_rows)
    (rd / 'round10_handoff_numbers.json').write_text(json.dumps(numbers, indent=2, default=str))
    print(json.dumps({k: recon[k] for k in ('planned_units', 'unique_canonical_units', 'missing_outcomes', 'total_attempts_started', 'attempts_by_arm', 'attempts_discarded',
                                            'discarded_by_cause', 'tau2_within_invocation_retries', 'cross_invocation_reruns_of_a_unit_without_record',
                                            'truncated_responses_in_canonical_records', 'truncation_warnings_in_discarded_attempts', 'n_infrastructure_error_units',
                                            'tau2_TIMEOUT_terminations', 'request_level_timeouts_seen_by_llama_server_invocation1', 'requests_aborted_by_owner_stop_invocation1',
                                            'request_level_context_rejections_seen_by_llama_server_invocation2')}, indent=2, default=str))


if __name__ == '__main__':
    main()
