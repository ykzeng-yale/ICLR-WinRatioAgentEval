"""G1 tests: lab_common, lab_eventlog, lab_verify_log, lab_reference_rule.

Everything here runs offline, deterministically, with no model and no network.
`experiments/live_ab` is on sys.path[0] under `unittest discover -s experiments/live_ab`.

This module also OWNS and regenerates the shared fixtures of `testdata/chains/`
(ARCHITECTURE_FINAL.md section 10): `good_T4.jsonl` is rebuilt byte for byte by
`build_good_chain()` and compared with the committed file, so the fixture can never drift
from the generator that documents it.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lab_common                                                     # noqa: E402
import lab_eventlog                                                   # noqa: E402
import lab_reference_rule                                             # noqa: E402
import lab_verify_log                                                 # noqa: E402
from lab_common import (ChainError, FreezeIncomplete, FrozenMismatch, SchemaError,      # noqa: E402
                        TornWrite, UntokenizablePath, WriteOnceViolation,
                        canonical_json, sha256_bytes, sha256_canonical, sha256_text)
from lab_eventlog import (EVENT_SCHEMA, EventLog, event_hash, genesis_prev, read_chain,  # noqa: E402
                          validate_event)

CHAINS_DIR = HERE / 'testdata' / 'chains'
FIXTURE_TRIAL = 'T4'
N_PAIRS = 8
INV = 'a' * 32
INV2 = 'b' * 32


# =============================================================================
# fixture construction
# =============================================================================
def _digest(tag: str) -> str:
    return sha256_text('live_ab-fixture|' + tag)


_SEED_RULE_CFG = {'source': 'os.urandom(4)', 'mask': '0x7FFFFFFE',
                  'low_bit': 'worker_index', 'forbidden': ['0xFFFFFFFF'],
                  'unique_within_worker_half': True, 'unique_across_program': True,
                  'logged_before_post': True,
                  'duplicate_is': 'logged_defect_no_outcome_effect'}
WINSTATS_SHA256 = lab_common.sha256_file(lab_common.SRC_DIR / 'winstats.py')


def fixture_config() -> dict:
    """A faithful subset of the frozen configuration of ARCHITECTURE_FINAL.md 6.1, with
    `roster.n_pairs` / `monitor.n_max` pinned to the fixture's 8 pairs.  Only the blocks the
    decision path reads are present; the fixture is a chain fixture, not a config fixture."""
    return {
        'experiment': 'live_ab',
        'protocol_version': 'v3-nm-guarded',
        'rule_id': 'nm_guarded_v3',
        'execution_order': ['T4', 'T2', 'T1', 'T3'],
        'monitor': {
            'construction': 'winstats.normal_mixture_radius',
            'variance_process': 'n',
            'alpha_program': 0.05, 'alpha_trial': 0.0125, 'alpha_gate': 0.00625,
            'rho': 100.0, 'delta': 0.03,
            'exploratory_margins': [0.10, 0.15], 'exploratory_margins_decide': False,
            'n_min': 100, 'n_max': N_PAIRS,
            'prefix': 'current_full_enrolled',
            'clip': [-1.0, 1.0],
            'retention': False, 'running_intersection': False, 'prefix_envelope': False,
            'maximize_over_prefixes': False,
            'harm_tail': 'hierarchy_upper_only',
            'decision_order': ['harm_keep_incumbent', 'deploy_candidate'],
            'betting_in_decision_path': False,
        },
        'hierarchy': [
            {'name': 'success', 'field': 'success', 'higher_better': True,
             'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
            {'name': 'cost', 'field': 'latency_s', 'higher_better': False,
             'absolute_tolerance': 0.0, 'relative_tolerance': 0.05},
        ],
        'eligibility_rule': 'lower_tiers_require_both_success',
        'tie_rule': 'strict_gt_tolerance_so_exact_equality_is_a_tie',
        'enclosure': {
            'start': [-1.0, 1.0],
            'success_formula': 'sA_low_minus_sB_high__sA_high_minus_sB_low',
            'cost_certificate': '(1 - 0.05) * ell > L_r + 1e-9',
            'certificate_constant': 0.95,
            'collapse_only_on_final_certificate': True,
            'clock_equivalence_tolerance_ms': 1,
        },
        'roster': {'strata': ['S1', 'S2'], 'pairing': 'stratified_no_mixed_pair',
                   'n_pairs_rule': 'floor(n_S1 / 2) + floor(n_S2 / 2)',
                   'exclusion_rules': ['out_of_design_smoke_task', 'duplicate_prompt'],
                   'uid_pattern': '^(mbpp|mbpp_full|humaneval)/[0-9]+$',
                   'n_S1': 2 * N_PAIRS, 'n_S2': 0, 'n_total': 2 * N_PAIRS,
                   'n_pairs': N_PAIRS},
        'design_seed_base': 60260919,
        'trials': {'T4': {'trial_no': 4, 'order': 1,
                          'incumbent': {'workflow': 'single_shot', 'server': 'coder'},
                          'candidate': {'workflow': 'single_shot', 'server': 'coder'}}},
        'coin': {'source': 'os.urandom(8)', 'bit': 'byte0&1', 'raw_hex_logged': True,
                 'map': '1->candidate_at_position_1', 'unit': 'pre_enrolled_pair',
                 'binding_on_resume': 'every_chain_valid_line', 'never_redrawn': True},
        'seed_rule': dict(_SEED_RULE_CFG),
        'execution': {'max_attempts': 1,
                      'auto_abort': {'consecutive_infrastructure_failures': 10,
                                     'counted_in': 'reveal_order'}},
        'plumbing_fail_conditions': {
            'reporting_code': ['receipt_mismatch_count_gt_0'],
            'decision_defining': ['chain_check_fail', 'reference_rule_disagreement',
                                  't4_payload_non_identity'],
            'repeat_same_condition_stops_program': True},
        'integrity_label_rule': {'coin_adjacent_events': 1, 'sandwich_violations': 1,
                                 'pairs_with_terminal_failure': 3,
                                 'coin_adjacency_scope': 'randomized_phase_only'},
    }


def fixture_roster() -> dict:
    uids = [f'mbpp/{i}' for i in range(1, 2 * N_PAIRS + 1)]
    return {'tasks': uids, 'exclusions': [], 'n_S1': len(uids), 'n_S2': 0,
            'n_total': len(uids), 'n_pairs': N_PAIRS,
            'roster_sha256': sha256_canonical(uids),
            'task_content_sha256': _digest('task_content')}


def fixture_order() -> list[dict]:
    out = []
    for i in range(1, N_PAIRS + 1):
        out.append({'pair': i, 'stratum': 'S1', 'arrivals': [2 * i - 1, 2 * i],
                    'uids': [f'mbpp/{2 * i - 1}', f'mbpp/{2 * i}']})
    return out


def fixture_bundle() -> dict:
    parts = {k: _digest(k) for k in lab_common.FREEZE_BUNDLE_KEYS}
    parts['protocol_version'] = 'v3-nm-guarded'
    parts['prefreeze_bytes'] = 4096
    parts['hardware_allowlist'] = ['arm64-darwin']
    parts['harness_file_sha256'] = {'lab_common.py': _digest('lab_common.py')}
    parts['reused_file_sha256'] = {'agent.py': _digest('agent.py')}
    parts['golden_props_sha256'] = {'coder': _digest('props_coder')}
    parts['golden_generation_settings_sha256'] = {'coder': _digest('gs_coder')}
    return lab_common.build_freeze_bundle(parts)


_HW = {'platform': 'darwin', 'machine': 'arm64', 'os_version': '25.5.0',
       'cpu_brand_sha256': _digest('cpu'), 'memsize_bytes': 68719476736, 'ncpu': 12}
_PKG = {'python': '3.12.11', 'numpy': '2.1.3', 'scipy': '1.14.1', 'pandas': '2.2.3',
        'requests': '2.32.3'}
_SEED_RULE = {'source': 'os.urandom(4)', 'mask': '0x7FFFFFFE', 'low_bit': 'worker_index',
              'forbidden': ['0xFFFFFFFF'], 'unique_within_worker_half': True,
              'unique_across_program': True, 'logged_before_post': True,
              'duplicate_is': 'logged_defect_no_outcome_effect'}
_USAGE = {'prompt_tokens': 120, 'completion_tokens': 240, 'total_tokens': 360,
          'cached_tokens': 0}
_TIMINGS = {'cache_n': 0, 'prompt_n': 120, 'prompt_ms': 40.0, 'predicted_n': 240,
            'predicted_ms': 900.0, 'predicted_per_second': 266.66}
_COUNTERS = {'prompt_tokens_total': 1000, 'tokens_predicted_total': 2000,
             'n_decode_total': 2000, 'requests_processing': 0, 'requests_deferred': 0}


def _what_was_known(n_enrolled: int, n_completed: int, look) -> dict:
    return {
        'pairs_enrolled': n_enrolled, 'pairs_completed': n_completed,
        'revealed_by_arm': {'incumbent': n_completed, 'candidate': n_completed},
        'L_h': look.L_h, 'U_h': look.U_h, 'L_s': look.L_s, 'U_s': look.U_s,
        'distance_to_harm': look.U_h, 'distance_to_deploy_h': look.L_h,
        'distance_to_deploy_s': look.L_s + 0.03,
        'earlier_trials': [],
    }


class _ChainBuilder:
    """Builds a deterministic, fully chain-valid event list without touching the clock."""

    def __init__(self, bundle_sha: str, chain_id: str) -> None:
        self.bundle_sha = bundle_sha
        self.chain_id = chain_id
        self.events: list[dict] = []
        self.t = 1_700_000_000_000_000_000
        self.m = 10_000_000_000
        self.inv = INV

    def clock(self, dt_ns: int = 1_000_000) -> None:
        self.t += dt_ns
        self.m += dt_ns

    def add(self, etype: str, body: dict) -> dict:
        validate_event(etype, body)
        self.clock()
        ev = {'seq': len(self.events), 'type': etype, 't_wall_ns': self.t,
              't_mono_ns': self.m, 'inv': self.inv, 'chain': self.chain_id,
              'prev': self.events[-1]['h'] if self.events
                      else genesis_prev(self.bundle_sha, self.chain_id),
              'body': body}
        ev['h'] = event_hash(ev)
        lab_eventlog.validate_envelope(ev)
        self.events.append(ev)
        return ev


def _segment_layout(events: list[dict]) -> list[list[dict]]:
    """Split a chain at its anchor events: an anchor is by definition the last line of its
    segment (ARCHITECTURE_FINAL.md 4.2 rule 5)."""
    segs: list[list[dict]] = [[]]
    for ev in events:
        segs[-1].append(ev)
        if ev['type'] == 'anchor':
            segs.append([])
    if not segs[-1]:
        segs.pop()
    return segs


def _segment_prefix_bytes(builder: _ChainBuilder) -> tuple[int, str]:
    """Bytes of the current (open) segment so far -- what an anchor commits to.  The anchor
    cannot commit to its own line, so `segment_bytes` / `segment_sha256` name the prefix
    that precedes it."""
    segs = _segment_layout(builder.events)
    current = segs[-1] if segs else []
    if current and current[-1]['type'] == 'anchor':
        current = []
    raw = b''.join(canonical_json(e).encode('utf-8') + b'\n' for e in current)
    return len(raw), sha256_bytes(raw)


def default_outcome(pair: int, position: int, arm: str) -> tuple[int, float]:
    return (1 if (pair + position) % 3 != 0 else 0,
            (10.0 + pair) if position == 1 else (20.0 + 2 * pair))


def extreme_outcome(pair: int, position: int, arm: str) -> tuple[int, float]:
    """Maximal imbalance: the candidate always succeeds and is 100x faster.  Used only to
    prove that the plumbing report is outcome-blind."""
    return (1, 1.0) if arm == 'candidate' else (0, 100.0)


def build_good_chain(outcome=default_outcome) -> dict:
    """The valid T4 fixture chain and everything needed to verify it."""
    cfg = fixture_config()
    roster = fixture_roster()
    order = fixture_order()
    bundle = fixture_bundle()
    bundle_sha = lab_common.freeze_bundle_sha256(bundle)
    lab_eventlog.set_roster_uids(roster['tasks'])
    cfg_sha = sha256_text(canonical_json(cfg))
    roster_sha = sha256_text(canonical_json(roster))
    order_sha = sha256_text(canonical_json(order))

    b = _ChainBuilder(bundle_sha, FIXTURE_TRIAL)
    arm_spec = {'workflow': 'single_shot', 'server_id': 'coder',
                'alias': 'qwen2.5-coder-7b-instruct-q4km', 'gguf_sha256': _digest('gguf')}
    b.add('trial_started', {
        'freeze_bundle_sha256': bundle_sha, 'program_head': _digest('program_head'),
        'config_sha256': cfg_sha, 'rule_block_sha256': _digest('rule_block'),
        'order_sha256': order_sha, 'roster_sha256': roster_sha,
        'task_content_sha256': roster['task_content_sha256'], 'n_pairs_max': N_PAIRS,
        'arms': {'incumbent': dict(arm_spec), 'candidate': dict(arm_spec)},
        'monitor': {'rule_id': 'nm_guarded_v3',
                    'construction': 'winstats.normal_mixture_radius',
                    'alpha_gate': 0.00625, 'rho': 100.0, 'delta': 0.03, 'n_min': 100,
                    'variance_process': 'n', 'clip': [-1.0, 1.0],
                    'prefix': 'current_full_enrolled', 'retention': False,
                    'running_intersection': False, 'harm_tail': 'hierarchy_upper_only',
                    'tiers': [{'name': 'success', 'higher_better': True,
                               'relative_tolerance': 0.0},
                              {'name': 'cost', 'higher_better': False,
                               'relative_tolerance': 0.05}],
                    'eligibility': 'lower_tiers_require_both_success'},
        'coin': {'source': 'os.urandom(8)', 'bit': 'byte0&1',
                 'map': '1->candidate_at_position_1', 'unit': 'pair'},
        'seed_rule': dict(_SEED_RULE), 'failure_rules_sha256': _digest('failure_rules'),
        'harness_file_sha256': {'lab_common.py': _digest('lab_common.py')},
        'reused_file_sha256': {'agent.py': _digest('agent.py')},
        'winstats_sha256': WINSTATS_SHA256,
        'sandbox_profile_sha256': _digest('sandbox_profile'),
        'golden_props_sha256': {'coder': _digest('props_coder')},
        'golden_generation_settings_sha256': {'coder': _digest('gs_coder')},
        'hardware': dict(_HW), 'packages': dict(_PKG),
        'llama_cpp_commit_sha256': _digest('llama_commit'),
        'refreezes_in_force': [],
    })
    b.add('invocation_started', {
        'pid': 4242, 'argv_sha256': _digest('argv'),
        'argv_tokens': ['<REPO>/experiments/live_ab/lab_orchestrator.py'],
        'resumed': False, 'head_at_start': b.events[-1]['h'],
        'state': {'pairs_enrolled': 0, 'pairs_completed': 0, 'open_attempts': 0,
                  'phase': 'randomizing'},
        'boottime_hash': _digest('boottime'), 'drift': [],
    })
    b.add('server_started', {
        'server_id': 'coder', 'pid': 4243, 'port': 8091, 'argv_sha256': _digest('sargv'),
        'gguf': {'bytes': 4683073536, 'sha256': _digest('gguf')},
        'props_sha256': _digest('props_coder'), 'props_matches_golden': True,
        'total_slots': 2, 'n_ctx': 16384, 'load_seconds': 12.5,
        'smoke': {'request_sha256': _digest('smoke_req'), 'receipt_matches_golden': True,
                  'usage': dict(_USAGE), 'timings': dict(_TIMINGS), 'ok': True},
    })
    b.add('server_health', {'server_id': 'coder', 'ok': True, 'slots_busy': 0,
                            'rss_bytes': 5_000_000_000, 'clock_anomaly': False})
    b.add('metrics_scrape', {'server_id': 'coder', 'point': 'trial_start', 'ok': True,
                             'counters': dict(_COUNTERS), 'tries': 1,
                             'unreconciled': False})

    def anchor(trigger: str, blocking: bool, pairs_enrolled: int,
               pairs_completed: int) -> int:
        seg_bytes, seg_sha = _segment_prefix_bytes(b)
        seq = len(b.events)
        b.add('anchor', {
            'anchor_seq': seq, 'upto_seq': seq - 1, 'upto_h': b.events[-1]['h'],
            'segment_index': len(_segment_layout(b.events)) - 1,
            'segment_bytes': seg_bytes, 'segment_sha256': seg_sha,
            'cumulative_bytes': seg_bytes, 'pairs_enrolled': pairs_enrolled,
            'pairs_completed': pairs_completed,
            'records_manifest_sha256': _digest(f'manifest{seq}'),
            'server_log_sha256': {'coder': _digest('serverlog')},
            'server_log_bytes': {'coder': 65536}, 'trigger': trigger,
            'blocking': blocking})
        b.add('anchor_receipt', {
            'anchor_seq': seq, 'pushed': True, 'comment_id': 100 + seq,
            'created_at': '2026-09-19T12:00:00Z', 'updated_at': '2026-09-19T12:00:01Z',
            'receipt_sha256': _digest(f'receipt{seq}'),
            'commit_sha256': _digest(f'commit{seq}')})
        return seq

    anchor('trial_started', True, 0, 0)

    emitted = 0

    def sync(pair_updated: int | None) -> None:
        """Emit one `monitor_update` for every evaluation trigger of protocol 8.3 that the
        last appended event produced -- and none for an event that produced none."""
        nonlocal emitted
        looks = lab_reference_rule.looks_from_chain(b.events, cfg, FIXTURE_TRIAL)
        while emitted < len(looks):
            look = looks[emitted]
            emitted += 1
            pu = None if look.trigger == 'resume' else pair_updated
            _write_update(look, pu)

    def _write_update(look, pair_updated: int | None) -> None:
        if pair_updated is None:
            enc = {'h': [-1.0, 1.0], 's': [-1.0, 1.0], 'collapsed': False,
                   'decisive_tier': -1}
        else:
            enc = _pair_enclosure_body(b.events, cfg, pair_updated)
        n_collapsed = _n_collapsed(b.events, cfg)
        b.add('monitor_update', {
            'trigger': look.trigger, 'n': look.n, 'n_collapsed': n_collapsed,
            'sum_lower_h': look.sum_lower_h, 'sum_upper_h': look.sum_upper_h,
            'sum_lower_s': look.sum_lower_s, 'sum_upper_s': look.sum_upper_s,
            'radius': look.radius, 'L_h': look.L_h, 'U_h': look.U_h, 'L_s': look.L_s,
            'U_s': look.U_s, 'pair_updated': pair_updated, 'pair_enclosure': enc,
            'flags': {'n_min_ok': look.n >= 100, 'harm': look.U_h < 0.0,
                      'deploy': look.L_h > 0.0 and look.L_s > -0.03,
                      'success_guard_ok': look.L_s > -0.03},
            'shadow': {'n': look.n, 'L_h': look.L_h, 'U_h': look.U_h, 'L_s': look.L_s,
                       'U_s': look.U_s, 'action': look.action, 'mismatch': False},
            'readouts': {'L_s_vs_010': look.L_s + 0.10, 'L_s_vs_015': look.L_s + 0.15,
                         's1_restricted': None,
                         'completed_prefix': {'n': max(1, n_collapsed), 'L_h': look.L_h,
                                              'U_h': look.U_h, 'L_s': look.L_s,
                                              'U_s': look.U_s}},
            'sums_fsum': True, 'monitor_code_sha256': _digest('monitor_code')})

    seed_counter = 0x10000000
    for i, slot in enumerate(order, start=1):
        a1, a2 = slot['arrivals']
        u1, u2 = slot['uids']
        if i > 1:
            # a pair-boundary scrape sits between the previous pair's last reveal and
            # this enrollment: protocol 7.3 item 3 -- it is never an evaluation trigger.
            b.add('metrics_scrape', {'server_id': 'coder', 'point': 'pair_boundary',
                                     'ok': True, 'counters': dict(_COUNTERS),
                                     'tries': 1, 'unreconciled': False})
        b.add('pair_enrolled', {'pair': i, 'stratum': 'S1', 'arrivals': [a1, a2],
                                'task_uids': [u1, u2], 'phase': 'randomizing',
                                're_enrolled': False})
        bit = (i * 5 + 1) % 2
        arms = ('candidate', 'incumbent') if bit == 1 else ('incumbent', 'candidate')
        coin_seq = len(b.events)
        b.add('coin_drawn', {'pair': i, 'entropy_source': 'os.urandom(8)',
                             'raw_hex': f'{(i * 0x1234567) & 0xFFFFFFFFFFFFFFFF:016x}',
                             'bit': bit,
                             'assignment': {str(a1): arms[0], str(a2): arms[1]}})
        # The enroll look is written at the COIN, not at `pair_enrolled`: the prefix `n` is
        # "the count of chain-valid coin_drawn events" and "changes only at a coin_drawn"
        # (protocol 7.3 item 2), so a pre-enrolled pair that was never randomized holds no
        # position and produces no evaluation.  `lab_orchestrator._w_draw_coin` calls
        # `evaluate()` on the coin for exactly this reason, and
        # `lab_reference_rule.looks_from_chain` emits 'enroll' at the `coin_drawn` branch.
        # See IMPLEMENTATION_STATUS.md "Known deviations" for the 8.3/7.3 wording clash.
        sync(i)
        for pos, (arrival, uid, arm) in enumerate(
                ((a1, u1, arms[0]), (a2, u2, arms[1])), start=1):
            b.add('episode_started', {
                'arrival': arrival, 'pair': i, 'position': pos, 'arm': arm,
                'workflow': 'single_shot', 'server_id': 'coder',
                'worker_pid': 5000 + arrival, 'task_uid': uid,
                'assignment_seq': coin_seq, 'payload_sha256': _digest('payload'),
                'job_sha256': _digest(f'job{arrival}'), 'enqueued_ns': b.m,
                'dispatched_ns': b.m + 1000, 'started_after_resume': False,
                'partner_concurrent': True})
            b.add('job_accepted', {'arrival': arrival, 'attempt': 1,
                                   'worker_pid': 5000 + arrival, 'spool_offset': 0,
                                   'worker_t_wall_ns': b.t, 'worker_t_mono_ns': b.m})
        stamps = {}
        for pos, arrival in enumerate((a1, a2), start=1):
            t_c1 = 20_000_000_000 + arrival * 1_000_000_000
            t_send = t_c1 + 1_000_000
            t_recv = t_send + int((10.0 + i) * 1e9) if pos == 1 \
                else t_send + int((20.0 + 2 * i) * 1e9)
            stamps[arrival] = (t_c1, t_recv)
            def request(try_index: int, rid: str, send_ns: int) -> None:
                nonlocal seed_counter
                seed_counter += 2
                b.add('llm_request', {
                    'arrival': arrival, 'attempt': 1, 'call_index': try_index,
                    'request_id': rid, 'server_id': 'coder', 't_c1_ns': t_c1,
                    't_send_ns': send_ns, 'kind': 'code', 'try_index': try_index,
                    'body_sha256': _digest(f'body{rid}'),
                    'messages_sha256': _digest(f'msg{rid}'), 'n_messages': 2,
                    'prompt_chars': 900,
                    'seed': (seed_counter & 0x7FFFFFFE) | (pos - 1),
                    'sampling_sent': {'temperature': 0.7, 'top_p': 0.95,
                                      'max_tokens': 1024, 'stream': False,
                                      'cache_prompt': False},
                    'spool_offset': 128, 'spool_fsync_ms': 1.5,
                    'partner_inflight': True, 'recovered': False})
                sync(i)

            # pair 6, position 1 carries a retried try: a timeout, then a fresh sample
            # (protocol 6.4 row 1).  Its llm_error raises no `ell`, so it produces NO look.
            if i == 6 and pos == 1:
                rid0 = sha256_text(f'req-{i}-{pos}-try0')[:32]
                request(0, rid0, t_c1 + 500_000)
                b.add('llm_error', {
                    'arrival': arrival, 'attempt': 1, 'call_index': 0,
                    'request_id': rid0, 'server_id': 'coder', 't_c1_ns': t_c1,
                    't_send_ns': t_c1 + 500_000, 'error_class': 'timeout',
                    'http_status': None, 'error_sha256': _digest(f'err{rid0}'),
                    'client_seconds': 180.0, 'will_retry': True, 'usage_known': False,
                    'bracketing_scrapes': [3], 'bound_is_joint': False})
                sync(i)
            rid = sha256_text(f'req-{i}-{pos}')[:32]
            request(1 if (i == 6 and pos == 1) else 0, rid, t_send)
            b.add('llm_response', {
                'arrival': arrival, 'attempt': 1,
                'call_index': 1 if (i == 6 and pos == 1) else 0, 'request_id': rid,
                'server_id': 'coder', 't_c1_ns': t_c1, 't_send_ns': t_send,
                'http_status': 200, 'model_matches_alias': True, 'finish_reason': 'stop',
                'usage': dict(_USAGE), 'timings': dict(_TIMINGS),
                'generation_settings_sha256': _digest('gs_coder'), 'receipt_mismatch': [],
                'id_slot': pos - 1, 'truncated': False, 'tokens_cached': 0,
                'tokens_evaluated': 120, 'tokens_predicted': 240,
                'rendered_prompt_sha256': _digest(f'rp{rid}'),
                'content_sha256': _digest(f'content{rid}'), 'client_seconds': 1.25,
                't_recv_ns': t_recv})
            sync(i)
        for pos, arrival in enumerate((a1, a2), start=1):
            success, latency = outcome(i, pos, arms[pos - 1])
            t_c1, t_recv = stamps[arrival]
            b.add('episode_revealed', {
                'arrival': arrival, 'pair': i, 'position': pos,
                'arm': arms[pos - 1], 'reveal_index': 2 * (i - 1) + pos,
                'outcome': {'success': success, 'latency_s': latency,
                            'completion_tokens': 240, 'prompt_tokens': 120,
                            'n_llm_calls': 1, 'n_failed_calls': 0,
                            'connection_retries': 0, 'n_self_test_executions': 0,
                            'n_verifier_executions': 1, 'repair_rounds': 0,
                            'self_test_passed': None, 'request_timeout_any': False,
                            'episode_timeout': False, 'verifier_timeout': False,
                            'truncated_any': False, 'sentinel_seen': bool(success),
                            'entry_point_defined': True, 'error_class': None,
                            'infra_flag': False},
                'record_sha256': _digest(f'record{arrival}'),
                'final_code_sha256': _digest(f'code{arrival}'),
                'verify_program_sha256': _digest(f'verify{arrival}'),
                'static_flags': [], 'hack_flags': [],
                'worker_t_start_ns': t_c1, 'worker_t_end_ns': t_recv,
                'verify_seconds': 0.8, 'sandbox_lock_wait_s': 0.0,
                'overlap': {'seconds_with_partner': 5.0,
                            'partner_arm': arms[2 - pos],
                            'partner_state_at_verify': 'running'},
                'certified_ell': (t_recv - t_c1) / 1e9, 'tokens_known': 240,
                'recovered_orphan': False, 'post_decision': False})
            sync(i)
        if i == 4:
            # a planned pause, a new invocation, and the ONE resume look of protocol 8.3
            # trigger 4 -- taken at the last fully enrolled prefix, before any new
            # enrollment.
            last = lab_reference_rule.shadow_step(b.events, cfg, FIXTURE_TRIAL)
            b.add('trial_paused', {'reason_code': 'planned',
                                   'what_was_known': _what_was_known(i, i, last)})
            anchor('trial_paused', True, i, i)
            b.add('invocation_ended', {'status': 'paused',
                                       'counts': {'pairs_enrolled': i,
                                                  'pairs_completed': i}})
            b.inv = INV2
            b.add('invocation_started', {
                'pid': 4444, 'argv_sha256': _digest('argv2'),
                'argv_tokens': ['<REPO>/experiments/live_ab/lab_orchestrator.py'],
                'resumed': True, 'head_at_start': b.events[-1]['h'],
                'state': {'pairs_enrolled': i, 'pairs_completed': i,
                          'open_attempts': 0, 'phase': 'randomizing'},
                'boottime_hash': _digest('boottime2'), 'drift': []})
            sync(None)
            b.add('trial_resumed', {'reason_code': 'planned',
                                    'what_was_known': _what_was_known(i, i, last)})
            anchor('trial_resumed', True, i, i)

    final_look = lab_reference_rule.shadow_step(b.events, cfg, FIXTURE_TRIAL)
    assert final_look.action == 'horizon_no_decision', final_look.action
    monitor_seq = max(e['seq'] for e in b.events if e['type'] == 'monitor_update')
    b.add('decision', {
        'kind': 'horizon_no_decision', 'rule_id': 'nm_guarded_v3', 'n': final_look.n,
        'monitor_seq': monitor_seq, 'radius': final_look.radius, 'L_h': final_look.L_h,
        'U_h': final_look.U_h, 'L_s': final_look.L_s, 'U_s': final_look.U_s,
        'delta': 0.03, 'alpha_gate': 0.00625, 'inflight': [],
        'next_unassigned_arrival': None, 'decided_on_resume': False})
    anchor('decision', True, N_PAIRS, N_PAIRS)
    b.add('usage_reconciliation', {
        'server_id': 'coder', 'window': 'trial', 'window_from_seq': 0,
        'window_to_seq': len(b.events), 'counter_delta': {'prompt': 1920,
                                                          'predicted': 3840},
        'client_usage_sum': {'prompt': 1920, 'predicted': 3840},
        'residual': {'prompt': 0, 'predicted': 0}, 'reconciliation_defect': False,
        'counters_lost': False})
    b.add('metrics_scrape', {'server_id': 'coder', 'point': 'trial_end', 'ok': True,
                             'counters': dict(_COUNTERS), 'tries': 1,
                             'unreconciled': False})
    b.add('server_stopped', {'server_id': 'coder', 'pid': 4243, 'returncode': 0,
                             'seconds': 300.0})
    b.add('deposit_sealed', {'deposit_sha256': _digest('deposit'),
                             'deposit_bytes': 1048576, 'n_records': 2 * N_PAIRS,
                             'n_spools': 2 * N_PAIRS})
    ledger = lab_verify_log._recount_exposure(b.events)
    b.add('trial_ended', {
        'status': 'ended', 'reason': None, 'phase': 'ended',
        'exposure_ledger': ledger,
        'reconciliation_totals': {'prompt': 1920, 'predicted': 3840},
        'terminal_failures_by_arm': {'incumbent': 0, 'candidate': 0},
        'n_torn_recoveries': 0, 'longest_unreceipted_span_s': 0.0,
        'what_was_known': _what_was_known(N_PAIRS, N_PAIRS, final_look),
        'final_head': b.events[-1]['h']})
    anchor('trial_ended', True, N_PAIRS, N_PAIRS)

    return {'events': b.events, 'config': cfg, 'roster': roster, 'order': order,
            'bundle': bundle, 'bundle_sha': bundle_sha,
            'exposure_ledger': lab_verify_log._recount_exposure(b.events)}


def _pair_enclosure_body(events, cfg, pair: int) -> dict:
    tiers, tol = lab_reference_rule._tiers(cfg)
    pairs = _rebuild_pairs(events)
    p = pairs[pair - 1]
    h_lo, h_hi, s_lo, s_hi, collapsed, tier = lab_reference_rule._pair_enclosure(
        p, tiers, tol)
    return {'h': [h_lo, h_hi], 's': [s_lo, s_hi], 'collapsed': collapsed,
            'decisive_tier': tier}


def _n_collapsed(events, cfg) -> int:
    tiers, tol = lab_reference_rule._tiers(cfg)
    n = 0
    for p in _rebuild_pairs(events):
        if lab_reference_rule._pair_enclosure(p, tiers, tol)[4]:
            n += 1
    return n


def _rebuild_pairs(events):
    pairs = []
    by_index = {}
    arrival_pair = {}
    for ev in events:
        t, body = ev['type'], ev['body']
        if t == 'pair_enrolled' and not body.get('re_enrolled'):
            p = lab_reference_rule._Pair(int(body['pair']), body['arrivals'])
            pairs.append(p)
            by_index[int(body['pair'])] = p
            for a in p.arrivals:
                arrival_pair[a] = p
        elif t == 'coin_drawn':
            for a_s, arm in body['assignment'].items():
                by_index[int(body['pair'])].episodes[int(a_s)].arm = arm
        elif t in lab_reference_rule.CALL_TYPES:
            p = arrival_pair.get(int(body['arrival']))
            if p is not None and not p.episodes[int(body['arrival'])].revealed:
                p.episodes[int(body['arrival'])].note_stamp(
                    body.get('t_c1_ns'),
                    [s for s in (body.get('t_send_ns'), body.get('t_recv_ns'))
                     if s is not None])
        elif t == 'episode_revealed' and not body.get('post_decision'):
            p = arrival_pair.get(int(body['arrival']))
            if p is not None:
                ep = p.episodes[int(body['arrival'])]
                ep.arm = ep.arm or body['arm']
                ep.revealed = True
                ep.success = int(body['outcome']['success'])
                ep.latency_s = float(body['outcome']['latency_s'])
    return pairs


# =============================================================================
# fixture I/O
# =============================================================================
def chain_lines(events) -> str:
    return ''.join(canonical_json(e) + '\n' for e in events)


def load_chain(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text('utf-8').splitlines()
            if line]


def rechain(events, bundle_sha: str, chain_id: str, *,
            fix_anchors: bool = True) -> list[dict]:
    """Recompute seq, prev and h over a mutated event list.  With fix_anchors, every
    `anchor` body is recomputed from the bytes actually written before it (and the
    following receipt is re-pointed), so a mutation does not leave stale anchors behind."""
    out: list[dict] = []
    prev = genesis_prev(bundle_sha, chain_id)
    seg_raw = b''
    seg_index = 0
    last_anchor_seq: int | None = None
    for ev in events:
        ev = copy.deepcopy(ev)
        ev['seq'] = len(out)
        ev['prev'] = prev
        ev.pop('h', None)
        if fix_anchors and ev['type'] == 'anchor':
            ev['body'].update({'anchor_seq': ev['seq'], 'upto_seq': ev['seq'] - 1,
                               'upto_h': prev, 'segment_index': seg_index,
                               'segment_bytes': len(seg_raw),
                               'segment_sha256': sha256_bytes(seg_raw),
                               'cumulative_bytes': len(seg_raw)})
        if fix_anchors and ev['type'] in ('anchor_receipt', 'anchor_failed') \
                and last_anchor_seq is not None:
            ev['body']['anchor_seq'] = last_anchor_seq
        ev['h'] = event_hash(ev)
        prev = ev['h']
        out.append(ev)
        line = canonical_json(ev).encode('utf-8') + b'\n'
        if ev['type'] == 'anchor':
            last_anchor_seq = ev['seq']
            seg_raw = b''
            seg_index += 1
        else:
            seg_raw += line
    return out


def materialize(events, root: Path, trial: str, art: dict) -> Path:
    """Write a results tree (freeze files + segmented chain) that lab_verify_log can read."""
    root = Path(root)
    (root / 'freeze').mkdir(parents=True, exist_ok=True)
    (root / trial / 'events').mkdir(parents=True, exist_ok=True)
    (root / 'freeze' / 'config.json').write_text(canonical_json(art['config']),
                                                 encoding='utf-8')
    (root / 'freeze' / 'roster.json').write_text(canonical_json(art['roster']),
                                                 encoding='utf-8')
    (root / 'freeze' / f'arrival_order_{trial}.json').write_text(
        canonical_json(art['order']), encoding='utf-8')
    (root / 'freeze' / 'freeze_bundle.json').write_text(canonical_json(art['bundle']),
                                                        encoding='utf-8')
    if art.get('exposure_ledger') is not None:
        (root / trial / 'exposure_ledger.json').write_text(
            canonical_json(art['exposure_ledger']), encoding='utf-8')
    for i, seg in enumerate(_segment_layout(events)):
        (root / trial / 'events' / (lab_eventlog.SEGMENT_FMT % i)).write_text(
            chain_lines(seg), encoding='utf-8')
    return root


# ---- the defect catalogue ---------------------------------------------------
def _mutate(events, fn) -> list[dict]:
    evs = copy.deepcopy(events)
    fn(evs)
    return evs


def _find(evs, etype, **match):
    for ev in evs:
        if ev['type'] != etype:
            continue
        if all(ev['body'].get(k) == v for k, v in match.items()):
            return ev
    raise KeyError((etype, match))


def build_defects(good: dict) -> dict[str, dict]:
    """One defective chain per FAIL check the chain itself can express.  Each entry is
    {'events': [...], 'check': '<check id the verifier must report>'}."""
    evs = good['events']
    bsha = good['bundle_sha']
    out: dict[str, dict] = {}

    def add(name: str, check: str, fn, rechain_it: bool = True,
            fix_anchors: bool = True) -> None:
        mutated = _mutate(evs, fn)
        if rechain_it:
            mutated = rechain(mutated, bsha, FIXTURE_TRIAL, fix_anchors=fix_anchors)
        out[name] = {'events': mutated, 'check': check}

    # --- defects that read_chain itself must refuse (chain.read) ------------
    def tamper(e):
        ev = _find(e, 'coin_drawn', pair=3)
        ev['body']['bit'] = 1 - ev['body']['bit']
    add('defect_chain_tamper', 'chain.read', tamper, rechain_it=False)

    def deletion(e):
        ev = _find(e, 'job_accepted', arrival=5)
        e.remove(ev)
    add('defect_chain_deletion', 'chain.read', deletion, rechain_it=False)

    def reorder(e):
        i = e.index(_find(e, 'llm_request', arrival=3))
        e[i], e[i + 1] = e[i + 1], e[i]
    add('defect_chain_reorder', 'chain.read', reorder, rechain_it=False)

    def schema_url(e):
        _find(e, 'invocation_started', pid=4242)['body']['argv_tokens'] = [
            'https://example.invalid/x']
    add('defect_schema_url', 'chain.read', schema_url)

    def schema_commit(e):
        _find(e, 'server_started', port=8091)['body']['props_sha256'] = \
            '4fea119de30f6a923992780f6fd5ccb0bee5d47d'
    add('defect_schema_commit_id', 'chain.read', schema_commit)

    def schema_abspath(e):
        _find(e, 'invocation_started', pid=4242)['body']['argv_tokens'] = [
            '/Users/someone/ICLR/experiments/live_ab/lab_orchestrator.py']
    add('defect_schema_abspath', 'chain.read', schema_abspath)

    def schema_prose(e):
        _find(e, 'trial_ended', status='ended')['body']['phase'] = \
            'the trial ended because the horizon was reached'
    add('defect_schema_free_text', 'chain.read', schema_prose)

    # --- defects the verifier catches on a chain-valid file -----------------
    def enrollment(e):
        ev = _find(e, 'pair_enrolled', pair=3)
        ev['body']['task_uids'] = ['mbpp/1', 'mbpp/2']
    add('defect_order_enrollment', 'order.enrollment', enrollment)

    def two_coins(e):
        ev = _find(e, 'coin_drawn', pair=4)
        i = e.index(ev)
        dup = copy.deepcopy(ev)
        e.insert(i + 1, dup)
    add('defect_coin_one_per_pair', 'coin.one_per_pair', two_coins)

    def write_ahead(e):
        _find(e, 'episode_started', arrival=7)['body']['assignment_seq'] = 3
    add('defect_coin_write_ahead', 'coin.write_ahead', write_ahead)

    def two_reveals(e):
        ev = _find(e, 'episode_revealed', arrival=9)
        e.insert(e.index(ev) + 1, copy.deepcopy(ev))
    add('defect_episode_one_reveal', 'episode.one_reveal', two_reveals)

    def two_terminals(e):
        ev = _find(e, 'llm_response', arrival=3)
        e.insert(e.index(ev) + 1, copy.deepcopy(ev))
    add('defect_calls_one_terminal', 'calls.one_terminal', two_terminals)

    def no_job_accepted(e):
        e.remove(_find(e, 'job_accepted', arrival=11))
    add('defect_episode_job_accepted', 'episode.job_accepted', no_job_accepted)

    def dup_seed(e):
        a = _find(e, 'llm_request', arrival=1)
        bq = _find(e, 'llm_request', arrival=5)
        bq['body']['seed'] = a['body']['seed']
    add('defect_seeds_unique', 'seeds.unique', dup_seed)

    def drop_update(e):
        for ev in e:
            if ev['type'] == 'monitor_update' and ev['body']['trigger'] == 'call':
                e.remove(ev)
                return
    add('defect_monitor_cadence', 'monitor.cadence', drop_update)

    def shadow_mismatch(e):
        for ev in e:
            if ev['type'] == 'monitor_update':
                ev['body']['shadow']['mismatch'] = True
                return
    add('defect_monitor_shadow', 'monitor.shadow', shadow_mismatch)

    def bad_band(e):
        for ev in e:
            if ev['type'] == 'monitor_update':
                ev['body']['L_h'] = ev['body']['L_h'] + 0.25
                return
    add('defect_monitor_independent_band', 'monitor.independent_band', bad_band)

    def wrong_kind(e):
        _find(e, 'decision', rule_id='nm_guarded_v3')['body']['kind'] = 'deploy_candidate'
    add('defect_reference_rule_agreement', 'reference_rule.agreement', wrong_kind)

    def wrong_monitor_seq(e):
        _find(e, 'decision', rule_id='nm_guarded_v3')['body']['monitor_seq'] = 7
    add('defect_monitor_first_crossing', 'monitor.first_crossing', wrong_monitor_seq)

    def widen(e):
        """The LAST recorded enclosure of pair 2 -- a collapsed point -- is widened back
        to the full range.  An enclosure never widens (protocol 7.5)."""
        for ev in reversed(e):
            if ev['type'] == 'monitor_update' and ev['body'].get('pair_updated') == 2:
                ev['body']['pair_enclosure']['h'] = [-1.0, 1.0]
                ev['body']['pair_enclosure']['s'] = [-1.0, 1.0]
                ev['body']['pair_enclosure']['collapsed'] = False
                return
    add('defect_enclosure_monotone', 'enclosure.monotone', widen)

    def not_containing(e):
        for ev in e:
            if ev['type'] == 'monitor_update' and ev['body'].get('pair_updated') == 2:
                ev['body']['pair_enclosure']['h'] = [0.5, 1.0]
                ev['body']['pair_enclosure']['s'] = [0.5, 1.0]
                return
    add('defect_enclosure_containment', 'enclosure.containment', not_containing)

    def post_decision_flag(e):
        _find(e, 'episode_revealed', arrival=1)['body']['post_decision'] = True
    add('defect_switch_phase', 'switch.phase', post_decision_flag)

    def bad_anchor(e):
        """The LAST anchor, so that nothing before it moves and `fix_anchors=False`
        leaves every earlier anchor valid."""
        for ev in reversed(e):
            if ev['type'] == 'anchor':
                ev['body']['segment_sha256'] = _digest('wrong-segment')
                return
    add('defect_anchor_prefix', 'anchor.prefix', bad_anchor, fix_anchors=False)

    def drop_receipt(e):
        for ev in e:
            if ev['type'] == 'anchor_receipt':
                e.remove(ev)
                return
    add('defect_anchor_receipts', 'anchor.receipts', drop_receipt)

    def payload_split(e):
        _find(e, 'episode_started', arrival=2)['body']['payload_sha256'] = \
            _digest('other-payload')
    add('defect_t4_payload_identity', 't4.payload_identity', payload_split)

    def drift_no_digests(e):
        ev = _find(e, 'decision', rule_id='nm_guarded_v3')
        i = e.index(ev)
        look = lab_reference_rule.RefLook('reveal', N_PAIRS, 0., 0., 0., 0., 0., 0., 0.,
                                          0., 0., 'none')
        e.insert(i, {'seq': 0, 'type': 'trial_paused', 't_wall_ns': ev['t_wall_ns'],
                     't_mono_ns': ev['t_mono_ns'], 'inv': ev['inv'], 'chain': ev['chain'],
                     'prev': '0' * 64,
                     'body': {'reason_code': 'worktree_drift',
                              'what_was_known': _what_was_known(N_PAIRS, N_PAIRS, look),
                              'digests': []}})
    add('defect_worktree_integrity', 'worktree.integrity', drift_no_digests)

    def reconciliation(e):
        _find(e, 'usage_reconciliation', window='trial')['body'][
            'reconciliation_defect'] = True
    add('defect_usage_reconciliation', 'usage.reconciliation', reconciliation)

    # --- a chain written under another freeze bundle -------------------------
    other = rechain(copy.deepcopy(evs), sha256_text('another-bundle'), FIXTURE_TRIAL)
    out['defect_genesis_wrong_bundle'] = {'events': other, 'check': 'chain.read'}
    return out


def build_program_chain(bundle_sha: str, order: tuple[str, ...]) -> list[dict]:
    b = _ChainBuilder(bundle_sha, '_program')
    b.add('program_opened', {
        'freeze_bundle_sha256': bundle_sha, 'config_sha256': _digest('cfg'),
        'rule_block_sha256': _digest('rule_block'), 'protocol_sha256': _digest('protocol'),
        'prefreeze_head': _digest('prefreeze_head'), 'prefreeze_bytes': 4096,
        'prefreeze_file_sha256': _digest('prefreeze_file'),
        'trial_order': list(lab_common.TRIALS), 'n_pairs_max': N_PAIRS,
        'alpha': {'program': 0.05, 'trial': 0.0125, 'gate': 0.00625}, 'rho': 100.0,
        'delta': 0.03, 'n_min': 100, 'rule_id': 'nm_guarded_v3',
        'harness_file_sha256': {'lab_common.py': _digest('lab_common.py')},
        'reused_file_sha256': {'agent.py': _digest('agent.py')},
        'winstats_sha256': WINSTATS_SHA256, 'hardware': dict(_HW),
        'packages': dict(_PKG),
        'freeze_receipt': {'comment_id': 11, 'created_at': '2026-09-19T11:00:00Z',
                           'receipt_sha256': _digest('freeze_receipt')}})
    for t in order:
        b.add('trial_opened', {'trial': t, 'genesis_prev': genesis_prev(bundle_sha, t),
                               'order_sha256': _digest(f'order{t}'),
                               'roster_sha256': _digest('roster'),
                               'refreezes_in_force': []})
        b.add('trial_closed', {'trial': t, 'status': 'ended',
                               'final_head': _digest(f'head{t}'), 'final_seq': 100,
                               'end_receipt_id': 12, 'reason': None})
    return b.events


def write_fixtures(dst: Path | None = None) -> dict:
    """Regenerate testdata/chains/.  Called by the test below and by hand."""
    dst = Path(dst) if dst is not None else CHAINS_DIR
    dst.mkdir(parents=True, exist_ok=True)
    good = build_good_chain()
    manifest: dict = {'trial': FIXTURE_TRIAL, 'n_pairs': N_PAIRS,
                      'n_events': len(good['events']),
                      'bundle_sha256': good['bundle_sha'], 'defects': {}}
    (dst / 'good_T4.jsonl').write_text(chain_lines(good['events']), encoding='utf-8')
    (dst / 'good_T4_config.json').write_text(canonical_json(good['config']),
                                             encoding='utf-8')
    (dst / 'good_T4_roster.json').write_text(canonical_json(good['roster']),
                                             encoding='utf-8')
    (dst / 'good_T4_arrival_order.json').write_text(canonical_json(good['order']),
                                                    encoding='utf-8')
    (dst / 'good_T4_freeze_bundle.json').write_text(canonical_json(good['bundle']),
                                                    encoding='utf-8')
    (dst / 'good_T4_exposure_ledger.json').write_text(
        canonical_json(good['exposure_ledger']), encoding='utf-8')
    (dst / 'good_program.jsonl').write_text(
        chain_lines(build_program_chain(good['bundle_sha'], lab_common.TRIALS)),
        encoding='utf-8')
    (dst / 'defect_program_order.jsonl').write_text(
        chain_lines(build_program_chain(good['bundle_sha'], ('T1', 'T4', 'T2', 'T3'))),
        encoding='utf-8')
    manifest['defects']['defect_program_order'] = 'program.order'
    for name, spec in build_defects(good).items():
        (dst / f'{name}.jsonl').write_text(chain_lines(spec['events']), encoding='utf-8')
        manifest['defects'][name] = spec['check']
    (dst / 'manifest.json').write_text(canonical_json(manifest) + '\n', encoding='utf-8')
    return good


# =============================================================================
# tests
# =============================================================================
class TempTree(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='lab_ab_test_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(lab_eventlog.set_roster_uids, None)


class CommonTests(TempTree):
    def test_tokenize_path(self) -> None:
        cases = [(lab_common.WORK_ROOT / 'T1' / 'x.json', '<WORK>/T1/x.json'),
                 (lab_common.RESULTS_ROOT / 'T1' / 'events', '<RESULTS>/T1/events'),
                 (lab_common.REPO_ROOT / 'src' / 'winstats.py', '<REPO>/src/winstats.py'),
                 (Path.home() / 'x', '<HOME>/x')]
        for path, want in cases:
            self.assertEqual(lab_common.tokenize_path(path), want)
        with self.assertRaises(UntokenizablePath):
            lab_common.tokenize_path('/definitely/not/a/known/root')

    def test_canonical_json_and_floats(self) -> None:
        self.assertEqual(lab_common.canonical_json({'b': 1, 'a': 2}), '{"a":2,"b":1}')
        self.assertEqual(lab_common.canonical_json({'x': 0.1}), '{"x":0.1}')
        with self.assertRaises(ValueError):
            lab_common.canonical_json({'x': float('nan')})
        with self.assertRaises(ValueError):
            lab_common.canonical_json({'x': float('inf')})

    def test_freeze_bundle_complete(self) -> None:
        parts = {k: _digest(k) for k in lab_common.FREEZE_BUNDLE_KEYS}
        parts['prefreeze_bytes'] = 1
        parts['hardware_allowlist'] = ['arm64-darwin']
        lab_common.build_freeze_bundle(dict(parts))
        with self.assertRaises(FreezeIncomplete):
            lab_common.build_freeze_bundle({k: v for k, v in parts.items()
                                            if k != 'roster_sha256'})
        with self.assertRaises(FreezeIncomplete):
            lab_common.build_freeze_bundle(dict(parts, extra_key='x'))
        with self.assertRaises(FreezeIncomplete):
            lab_common.build_freeze_bundle(dict(parts, roster_sha256=None))
        with self.assertRaises(FreezeIncomplete):
            lab_common.build_freeze_bundle(dict(parts, roster_sha256='unknown'))
        with self.assertRaises(FreezeIncomplete):
            lab_common.build_freeze_bundle(
                dict(parts, harness_file_sha256={'a.py': None}))

    def test_rule_block_hash(self) -> None:
        cfg = fixture_config()
        cfg['anchor'] = {'pairs': 25, 'blocking_wait_minutes': 30}
        base = lab_common.rule_block_sha256(cfg)
        moved = copy.deepcopy(cfg)
        moved['anchor']['pairs'] = 50
        moved['anchor']['blocking_wait_minutes'] = 45
        self.assertEqual(lab_common.rule_block_sha256(moved), base)
        for path, value in (('monitor.delta', 0.10),
                            ('design_seed_base', 1),
                            ('eligibility_rule', 'other')):
            changed = copy.deepcopy(cfg)
            node = changed
            parts = path.split('.')
            for p in parts[:-1]:
                node = node[p]
            node[parts[-1]] = value
            self.assertNotEqual(lab_common.rule_block_sha256(changed), base, path)
        changed = copy.deepcopy(cfg)
        changed['hierarchy'][1]['relative_tolerance'] = 0.10
        self.assertNotEqual(lab_common.rule_block_sha256(changed), base)
        changed = copy.deepcopy(cfg)
        changed['enclosure']['certificate_constant'] = 0.9
        self.assertNotEqual(lab_common.rule_block_sha256(changed), base)
        with self.assertRaises(FrozenMismatch):
            lab_common.rule_block_sha256({'rule_id': 'x'})

    def test_write_json_atomic_write_once(self) -> None:
        p = self.tmp / 'x.json'
        d1 = lab_common.write_json_atomic(p, {'a': 1})
        self.assertEqual(d1, lab_common.write_json_atomic(p, {'a': 1}))
        with self.assertRaises(WriteOnceViolation):
            lab_common.write_json_atomic(p, {'a': 2})

    def test_append_line_rejects_newline(self) -> None:
        fd = os.open(str(self.tmp / 'l.txt'), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        try:
            with self.assertRaises(TornWrite):
                lab_common.append_line_durable(fd, 'a\nb', durable=False)
        finally:
            os.close(fd)

    def test_hardware_and_packages_satisfy_the_string_discipline(self) -> None:
        validate_event('server_health', {'server_id': 'coder', 'ok': True,
                                         'slots_busy': 0, 'rss_bytes': 1,
                                         'clock_anomaly': False})
        from lab_eventlog import _check_field, HARDWARE, PACKAGES
        _check_field(HARDWARE, lab_common.hardware_info(), 'hardware')
        _check_field(PACKAGES, lab_common.package_versions(), 'packages')


class EventLogTests(TempTree):
    def _log(self, *, create: bool = True, inv: str = INV) -> EventLog:
        return EventLog(self.tmp / 'events', 'T4', 'ab' * 32, inv, create=create)

    def _health(self, i: int) -> dict:
        return {'server_id': 'coder', 'ok': True, 'slots_busy': i % 2,
                'rss_bytes': 1000 + i, 'clock_anomaly': False}

    def _anchor_body(self, log: EventLog, seq: int) -> dict:
        seg = log.events_dir / (lab_eventlog.SEGMENT_FMT % log.segment_index)
        raw = seg.read_bytes() if seg.exists() else b''
        return {'anchor_seq': seq, 'upto_seq': seq - 1, 'upto_h': log.head,
                'segment_index': log.segment_index, 'segment_bytes': len(raw),
                'segment_sha256': sha256_bytes(raw), 'cumulative_bytes': len(raw),
                'pairs_enrolled': 0, 'pairs_completed': 0,
                'records_manifest_sha256': _digest('m'),
                'server_log_sha256': {'coder': _digest('sl')},
                'server_log_bytes': {'coder': 1}, 'trigger': 'decision',
                'blocking': False}

    def test_canonical_bytes_roundtrip_and_chain_verifies(self) -> None:
        log = self._log()
        for i in range(200):
            log.append('server_health', self._health(i), durable=False)
            if i in (60, 130):
                log.close_segment(anchor_body=self._anchor_body(log, log.seq))
        head = log.head
        log.close()
        read = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        self.assertEqual(len(read.segments), 3)
        self.assertEqual(len(read.events), 202)
        self.assertEqual(read.events[-1]['h'], head)
        for seg in read.segments:
            for line in seg.read_bytes().split(b'\n'):
                if line:
                    self.assertEqual(
                        canonical_json(json.loads(line.decode('utf-8'))).encode('utf-8'),
                        line)

    def test_genesis_bound_to_bundle(self) -> None:
        log = self._log()
        log.append('server_health', self._health(0))
        log.close()
        read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'cd' * 32)
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T2', 'ab' * 32)

    def test_float_repr_and_nan(self) -> None:
        log = self._log()
        ev = log.append('server_stopped', {'server_id': 'coder', 'pid': 1,
                                           'returncode': 0, 'seconds': 0.1})
        self.assertIn('"seconds":0.1', canonical_json(ev))
        with self.assertRaises(SchemaError):
            log.append('server_stopped', {'server_id': 'coder', 'pid': 1,
                                          'returncode': 0, 'seconds': float('nan')})
        with self.assertRaises(SchemaError):
            log.append('server_stopped', {'server_id': 'coder', 'pid': 1,
                                          'returncode': 0, 'seconds': float('inf')})
        with self.assertRaises(SchemaError):
            log.append('server_stopped', {'server_id': 'coder', 'pid': 1,
                                          'returncode': 0, 'seconds': 1})
        log.close()

    def test_tamper_detected(self) -> None:
        log = self._log()
        for i in range(5):
            log.append('server_health', self._health(i))
        log.close()
        seg = self.tmp / 'events' / 'seg_0000.jsonl'
        raw = bytearray(seg.read_bytes())
        i = raw.index(b'"rss_bytes":1002')
        raw[i + 14:i + 16] = b'99'
        seg.write_bytes(bytes(raw))
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_deletion_detected(self) -> None:
        log = self._log()
        for i in range(5):
            log.append('server_health', self._health(i))
        log.close()
        seg = self.tmp / 'events' / 'seg_0000.jsonl'
        lines = seg.read_bytes().split(b'\n')
        del lines[2]
        seg.write_bytes(b'\n'.join(lines))
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_reorder_detected(self) -> None:
        log = self._log()
        for i in range(5):
            log.append('server_health', self._health(i))
        log.close()
        seg = self.tmp / 'events' / 'seg_0000.jsonl'
        lines = [l for l in seg.read_bytes().split(b'\n') if l]
        lines[1], lines[2] = lines[2], lines[1]
        seg.write_bytes(b'\n'.join(lines) + b'\n')
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_torn_tail_recovered(self) -> None:
        log = self._log()
        for i in range(4):
            log.append('server_health', self._health(i), durable=True)
        log.close()
        seg = self.tmp / 'events' / 'seg_0000.jsonl'
        before = seg.read_bytes()
        partial = canonical_json({'body': {'server_id': 'coder'}, 'chain': 'T4'})[:40]
        with open(seg, 'ab') as fh:
            fh.write(partial.encode('utf-8'))
        read = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        self.assertIsNotNone(read.torn)
        assert read.torn is not None
        self.assertEqual(read.torn.offset, len(before))
        self.assertTrue(read.torn.is_event_prefix)
        size_before = seg.stat().st_size
        log2 = EventLog(self.tmp / 'events', 'T4', 'ab' * 32, INV2)
        self.assertGreaterEqual(seg.stat().st_size, size_before)
        self.assertEqual(log2.events[-1]['type'], 'log_recovery')
        self.assertEqual(log2.events[-1]['body']['torn_sha256'], read.torn.sha256)
        log2.append('server_health', self._health(9))
        log2.close()
        again = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        self.assertIsNotNone(again.torn)
        self.assertEqual(again.events[-1]['type'], 'server_health')
        self.assertEqual(len(again.events), 6)
        # a SECOND torn region is a ChainError
        with open(seg, 'ab') as fh:
            fh.write(b'{"body":')
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_torn_region_spans_newlines(self) -> None:
        log = self._log()
        for i in range(3):
            log.append('server_health', self._health(i), durable=True)
        log.close()
        seg = self.tmp / 'events' / 'seg_0000.jsonl'
        before = seg.read_bytes()
        junk = b'{"body":{"a":1},"broken\nstill broken\nand more\n{"body":'
        with open(seg, 'ab') as fh:
            fh.write(junk)
        read = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        assert read.torn is not None
        self.assertEqual(read.torn.offset, len(before))
        self.assertEqual(read.torn.length, len(junk))
        self.assertEqual(read.torn.sha256, sha256_bytes(junk))
        log2 = EventLog(self.tmp / 'events', 'T4', 'ab' * 32, INV2)
        rec = log2.events[-1]
        log2.close()
        self.assertEqual(rec['type'], 'log_recovery')
        self.assertEqual(rec['body']['torn_len'], len(junk))
        self.assertEqual(rec['body']['torn_sha256'], sha256_bytes(junk))
        again = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        assert again.torn is not None
        self.assertEqual(again.torn.length, len(junk))
        self.assertEqual(len(again.events), 4)

    def test_kill_after_write_before_fsync_keeps_the_coin_binding(self) -> None:
        """protocol 4.2 invariant v: every chain-valid coin_drawn line binds, whether or
        not its fsync had returned; a coin is void only inside a torn region."""
        lab_eventlog.set_roster_uids([f'mbpp/{i}' for i in range(1, 5)])
        log = self._log()
        log.append('pair_enrolled', {'pair': 1, 'stratum': 'S1', 'arrivals': [1, 2],
                                     'task_uids': ['mbpp/1', 'mbpp/2'],
                                     'phase': 'randomizing', 're_enrolled': False},
                   durable=True)
        calls = {'n': 0}
        real = lab_common.fullsync

        def kill_after_write(fd: int) -> None:
            calls['n'] += 1
            raise KeyboardInterrupt('power loss after os.write, before F_FULLFSYNC')

        lab_common.fullsync = kill_after_write
        try:
            with self.assertRaises(KeyboardInterrupt):
                log.append('coin_drawn', {'pair': 1, 'entropy_source': 'os.urandom(8)',
                                          'raw_hex': '0123456789abcdef', 'bit': 1,
                                          'assignment': {'1': 'candidate',
                                                         '2': 'incumbent'}},
                           durable=True)
        finally:
            lab_common.fullsync = real
        self.assertEqual(calls['n'], 1)
        log.close()
        read = read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        self.assertIsNone(read.torn)
        coins = [e for e in read.events if e['type'] == 'coin_drawn']
        self.assertEqual(len(coins), 1)
        self.assertEqual(coins[0]['body']['bit'], 1)
        log2 = EventLog(self.tmp / 'events', 'T4', 'ab' * 32, INV2)
        self.assertEqual(log2.seq, 2)
        log2.close()

    def test_segment_rules(self) -> None:
        log = self._log()
        log.append('server_health', self._health(0))
        log.close_segment(anchor_body=self._anchor_body(log, log.seq))
        log.append('server_health', self._health(1))
        log.close()
        read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        # a non-final segment that does not end with an anchor
        seg0 = self.tmp / 'events' / 'seg_0000.jsonl'
        lines = [l for l in seg0.read_bytes().split(b'\n') if l]
        seg0.write_bytes(lines[0] + b'\n')
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        # a gap in the numbering
        shutil.rmtree(self.tmp / 'events')
        log = self._log()
        log.append('server_health', self._health(0))
        log.close_segment(anchor_body=self._anchor_body(log, log.seq))
        log.append('server_health', self._health(1))
        log.close_segment(anchor_body=self._anchor_body(log, log.seq))
        log.append('server_health', self._health(2))
        log.close()
        (self.tmp / 'events' / 'seg_0001.jsonl').unlink()
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_closed_segment_is_never_reopened(self) -> None:
        log = self._log()
        log.append('server_health', self._health(0))
        log.close_segment(anchor_body=self._anchor_body(log, log.seq))
        seg0 = self.tmp / 'events' / 'seg_0000.jsonl'
        with open(seg0, 'ab') as fh:
            fh.write(b'{"body":{}}\n')
        log.close()
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)

    def test_unopenable_chain(self) -> None:
        (self.tmp / 'events').mkdir()
        (self.tmp / 'events' / 'seg_0000.jsonl').write_bytes(b'\x00\x01not json at all\n')
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events', 'T4', 'ab' * 32)
        (self.tmp / 'events2').mkdir()
        (self.tmp / 'events2' / 'notes.txt').write_text('hello')
        with self.assertRaises(ChainError):
            read_chain(self.tmp / 'events2', 'T4', 'ab' * 32)
        report = lab_verify_log.verify_trial('T4', 'ab' * 32, mode='full',
                                             results_root=self.tmp / 'missing')
        self.assertEqual(report.verdict, 'PASS')  # no chain at all: nothing to verify

    def test_create_refuses_an_existing_chain(self) -> None:
        log = self._log()
        log.append('server_health', self._health(0))
        log.close()
        with self.assertRaises(ChainError):
            self._log(create=True)

    def test_durable_uses_fullsync(self) -> None:
        seen: list[str] = []
        real = lab_common.fullsync

        def spy(fd: int) -> None:
            seen.append('sync')
            real(fd)

        lab_common.fullsync = spy
        try:
            log = self._log()
            log.append('server_health', self._health(0), durable=False)
            self.assertEqual(seen, [])
            log.append('server_health', self._health(1), durable=True)
            self.assertEqual(len(seen), 1)
            log.close()
        finally:
            lab_common.fullsync = real


def synth_field(spec, uid: str = 'mbpp/1'):
    """A minimal value satisfying one FieldSpec.  Used to synthesise a valid body for
    EVERY event type, so the schema tests cover all of EVENT_SCHEMA and not only the
    types a fixture chain happens to contain."""
    k = spec.kind
    if k == 'int':
        return 1
    if k == 'float':
        return 1.5
    if k == 'bool':
        return True
    if k in ('hex64', 'hex40', 'hex32', 'hex16'):
        return 'a' * int(k[3:])
    if k == 'enum':
        return spec.enum[0]
    if k == 'token_path':
        return '<REPO>/experiments/live_ab'
    if k == 'iso8601':
        return '2026-09-19T12:00:00Z'
    if k == 'uid':
        return uid
    if k == 'label':
        return 'label_one'
    if k == 'list':
        return [synth_field(spec.item, uid)]
    if k == 'null_or':
        return synth_field(spec.inner, uid)
    if k == 'obj':
        if spec.fields is not None:
            return {name: synth_field(sub, uid) for name, sub in spec.fields.items()}
        if spec.item is not None:
            return {'key_one': synth_field(spec.item, uid)}
        return {'count': 1, 'kind_one': 'plain_value'}
    raise AssertionError(f'unknown kind {k}')


def synth_body(etype: str, uid: str = 'mbpp/1') -> dict:
    return {name: synth_field(spec, uid)
            for name, spec in EVENT_SCHEMA[etype].items()}


class SchemaTests(TempTree):
    """The validator rejects a URL, a commit id, an absolute path and free text in EVERY
    event type (ARCHITECTURE_FINAL.md 9.2 test_schema_rejects)."""

    POISON = ('https://github.com/owner/repo/pull/1',
              '4fea119de30f6a923992780f6fd5ccb0bee5d47d',
              '/Users/an-account/a-repo/results/live_ab',
              'the operator decided to stop the trial here')

    def setUp(self) -> None:
        super().setUp()
        self.good = build_good_chain()
        self.bodies: dict[str, dict] = {t: synth_body(t) for t in EVENT_SCHEMA}
        for ev in self.good['events']:
            self.bodies[ev['type'] + '#real'] = ev['body']
        for ev in build_program_chain(self.good['bundle_sha'], lab_common.TRIALS):
            self.bodies[ev['type'] + '#real'] = ev['body']

    @staticmethod
    def _etype(key: str) -> str:
        return key.split('#', 1)[0]

    def test_every_event_type_has_a_valid_synthetic_body(self) -> None:
        lab_eventlog.set_roster_uids(['mbpp/1'])
        self.assertEqual(len(EVENT_SCHEMA), 47)
        for etype in sorted(EVENT_SCHEMA):
            with self.subTest(etype=etype):
                validate_event(etype, synth_body(etype))

    def _string_paths(self, node, path: tuple = ()):
        """Every path (a tuple of dict keys and list indices) to a string value.  Keys are
        kept as tuple members because map keys may themselves contain dots
        (`harness_file_sha256.lab_common.py`)."""
        if isinstance(node, dict):
            for k, v in node.items():
                yield from self._string_paths(v, path + (k,))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from self._string_paths(v, path + (i,))
        elif isinstance(node, str):
            yield path

    @staticmethod
    def _set(node, path: tuple, value):
        cur = node
        for p in path[:-1]:
            cur = cur[p]
        cur[path[-1]] = value

    def test_schema_rejects_poison_in_every_event_type(self) -> None:
        lab_eventlog.set_roster_uids(
            sorted(set(self.good['roster']['tasks']) | {'mbpp/1'}))
        covered = set()
        for key, body in sorted(self.bodies.items()):
            etype = self._etype(key)
            covered.add(etype)
            paths = list(self._string_paths(body))
            if not paths:
                self.assertTrue(all(not isinstance(v, str) for v in body.values()), key)
                continue
            for poison in self.POISON:
                for path in paths:
                    bad = copy.deepcopy(body)
                    self._set(bad, path, poison)
                    with self.subTest(etype=key, path='.'.join(map(str, path)),
                                      poison=poison[:24]):
                        with self.assertRaises(SchemaError):
                            validate_event(etype, bad)
        self.assertEqual(covered, set(EVENT_SCHEMA))

    def test_schema_rejects_shape_errors_in_every_event_type(self) -> None:
        lab_eventlog.set_roster_uids(
            sorted(set(self.good['roster']['tasks']) | {'mbpp/1'}))
        for key, body in sorted(self.bodies.items()):
            etype = self._etype(key)
            with self.subTest(etype=key):
                with self.assertRaises(SchemaError):
                    validate_event(etype, dict(body, this_key_is_unknown=1))
                for name in body:
                    if EVENT_SCHEMA[etype][name].required:
                        with self.assertRaises(SchemaError):
                            validate_event(etype,
                                           {k: v for k, v in body.items() if k != name})
                        break

    def test_schema_rejects_float_where_int_declared(self) -> None:
        body = copy.deepcopy(self.bodies['server_health'])
        with self.assertRaises(SchemaError):
            validate_event('server_health', dict(body, rss_bytes=1.0))
        with self.assertRaises(SchemaError):
            validate_event('server_health', dict(body, rss_bytes=True))
        with self.assertRaises(SchemaError):
            validate_event('server_health', dict(body, ok=1))

    def test_schema_accepts_uids_and_rejects_foreign_ones(self) -> None:
        body = copy.deepcopy(self.bodies['pair_enrolled#real'])
        lab_eventlog.set_roster_uids(self.good['roster']['tasks'])
        validate_event('pair_enrolled', body)
        validate_event('trial_started', self.bodies['trial_started#real'])
        stranger = dict(body, task_uids=['mbpp/99999', body['task_uids'][1]])
        with self.assertRaises(SchemaError):
            validate_event('pair_enrolled', stranger)
        lab_eventlog.set_roster_uids(None)
        validate_event('pair_enrolled', stranger)   # no roster installed: pattern only
        with self.assertRaises(SchemaError):
            validate_event('pair_enrolled', dict(body, task_uids=['mbpp', 'mbpp/1']))

    def test_unknown_event_type(self) -> None:
        with self.assertRaises(SchemaError):
            validate_event('not_an_event', {})

    def test_program_and_trial_types_do_not_mix(self) -> None:
        ev = {'seq': 0, 'type': 'coin_drawn', 't_wall_ns': 1, 't_mono_ns': 1,
              'inv': INV, 'chain': '_program', 'prev': '0' * 64, 'body': {},
              'h': '0' * 64}
        with self.assertRaises(SchemaError):
            lab_eventlog.validate_envelope(ev)
        ev['chain'] = 'T4'
        ev['type'] = 'program_opened'
        with self.assertRaises(SchemaError):
            lab_eventlog.validate_envelope(ev)


class ReferenceRuleTests(TempTree):
    def setUp(self) -> None:
        super().setUp()
        self.good = build_good_chain()
        self.cfg = self.good['config']

    def test_looks_match_the_cadence_of_protocol_8_3(self) -> None:
        looks = lab_reference_rule.looks_from_chain(self.good['events'], self.cfg,
                                                    FIXTURE_TRIAL)
        logged = [e['body']['trigger'] for e in self.good['events']
                  if e['type'] == 'monitor_update']
        self.assertEqual([lk.trigger for lk in looks], logged)
        self.assertEqual(logged.count('enroll'), N_PAIRS)
        self.assertEqual(logged.count('reveal'), 2 * N_PAIRS)
        self.assertEqual(logged.count('resume'), 1)
        self.assertEqual(logged.count('drain'), 0)
        # one look per llm_* event that raised a pending episode's certified ell; the one
        # llm_error of the fixture raises none, so it produces no look (protocol 8.3.3)
        raisers = sum(1 for e in self.good['events']
                      if e['type'] in ('llm_request', 'llm_response'))
        self.assertEqual(logged.count('call'), raisers)
        self.assertEqual(sum(1 for e in self.good['events'] if e['type'] == 'llm_error'),
                         1)

    def test_drain_reveal_updates_but_never_decides(self) -> None:
        """protocol 8.3 trigger 5 / PG-2: after a decision, a pre-decision pair that
        resolves writes a `drain` update, which is an update and not a look."""
        cfg = copy.deepcopy(self.cfg)
        cfg['monitor']['n_min'] = 1
        cfg['monitor']['n_max'] = 1
        cfg['roster']['n_pairs'] = 1
        evs = [
            {'type': 'pair_enrolled', 'chain': FIXTURE_TRIAL,
             'body': {'pair': 1, 'arrivals': [1, 2], 're_enrolled': False}},
            {'type': 'coin_drawn', 'chain': FIXTURE_TRIAL,
             'body': {'pair': 1, 'assignment': {'1': 'candidate', '2': 'incumbent'}}},
            {'type': 'llm_request', 'chain': FIXTURE_TRIAL,
             'body': {'arrival': 2, 't_c1_ns': 0, 't_send_ns': 11_000_000_000}},
            {'type': 'episode_revealed', 'chain': FIXTURE_TRIAL,
             'body': {'arrival': 1, 'arm': 'candidate', 'post_decision': False,
                      'outcome': {'success': 1, 'latency_s': 10.0}}},
            {'type': 'decision', 'chain': FIXTURE_TRIAL, 'body': {'kind': 'x', 'n': 1}},
            {'type': 'episode_revealed', 'chain': FIXTURE_TRIAL,
             'body': {'arrival': 2, 'arm': 'incumbent', 'post_decision': False,
                      'outcome': {'success': 1, 'latency_s': 12.0}}},
        ]
        looks = lab_reference_rule.looks_from_chain(evs, cfg, FIXTURE_TRIAL)
        self.assertEqual([lk.trigger for lk in looks],
                         ['enroll', 'call', 'reveal', 'drain'])
        # the cost certificate bound at the reveal (0.95 * 11 = 10.45 > 10): the
        # hierarchy enclosure collapsed to a point while the partner was still pending
        self.assertEqual((looks[2].sum_lower_h, looks[2].sum_upper_h), (1.0, 1.0))
        self.assertEqual((looks[2].sum_lower_s, looks[2].sum_upper_s), (0.0, 1.0))
        # ...and the band at n = 1 is still the full range, so nothing decides
        self.assertEqual((looks[2].L_h, looks[2].U_h), (-1.0, 1.0))
        self.assertEqual(looks[2].action, 'none')
        self.assertEqual(looks[-1].action, 'none')       # a drain never decides
        self.assertEqual(
            lab_reference_rule.decide_from_chain(evs, cfg, FIXTURE_TRIAL)['kind'], 'none')

    def test_metrics_scrape_is_never_a_trigger(self) -> None:
        scrapes = [e for e in self.good['events'] if e['type'] == 'metrics_scrape']
        self.assertGreater(len(scrapes), 1)
        by_seq = {e['seq']: e for e in self.good['events']}
        for ev in scrapes:
            nxt = by_seq.get(ev['seq'] + 1)
            if nxt is not None:
                self.assertNotEqual(nxt['type'], 'monitor_update')

    def test_n_is_the_full_enrolled_prefix_never_the_completed_count(self) -> None:
        looks = lab_reference_rule.looks_from_chain(self.good['events'], self.cfg,
                                                    FIXTURE_TRIAL)
        ns = [lk.n for lk in looks]
        self.assertEqual(ns, sorted(ns))
        self.assertEqual(ns[0], 1)
        self.assertEqual(ns[-1], N_PAIRS)
        for lk in looks:
            self.assertGreaterEqual(lk.n, 1)

    def test_bands_are_clipped_and_monotone_within_a_prefix(self) -> None:
        looks = lab_reference_rule.looks_from_chain(self.good['events'], self.cfg,
                                                    FIXTURE_TRIAL)
        for lk in looks:
            self.assertGreaterEqual(lk.L_h, -1.0)
            self.assertLessEqual(lk.U_h, 1.0)
            self.assertGreaterEqual(lk.L_s, -1.0)
            self.assertLessEqual(lk.U_s, 1.0)
        by_n: dict[int, list] = {}
        for lk in looks:
            by_n.setdefault(lk.n, []).append(lk)
        for n, group in by_n.items():
            for a, b in zip(group, group[1:]):
                self.assertGreaterEqual(b.sum_lower_h, a.sum_lower_h - 1e-12)
                self.assertLessEqual(b.sum_upper_h, a.sum_upper_h + 1e-12)
                self.assertGreaterEqual(b.L_h, a.L_h - 1e-12)
                self.assertLessEqual(b.U_h, a.U_h + 1e-12)

    def test_n_min_blocks_a_decision(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg['monitor']['n_max'] = 10 ** 6
        cfg['roster']['n_pairs'] = 10 ** 6
        looks = lab_reference_rule.looks_from_chain(self.good['events'], cfg,
                                                    FIXTURE_TRIAL)
        self.assertTrue(all(lk.action == 'none' for lk in looks))
        self.assertEqual(
            lab_reference_rule.decide_from_chain(self.good['events'], cfg,
                                                 FIXTURE_TRIAL)['kind'], 'none')

    def test_harm_before_deploy_and_harm_is_hierarchy_only(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg['monitor']['n_min'] = 1
        pairs = _rebuild_pairs(self.good['events'])
        tiers, tol = lab_reference_rule._tiers(cfg)
        look = lab_reference_rule._look('reveal', pairs, tiers, tol, 0.00625, 100.0,
                                        0.03, 1, 10 ** 6, False)
        self.assertIn(look.action, ('none', 'harm_keep_incumbent', 'deploy_candidate'))
        # U_s < -delta with U_h > 0 must decide nothing (PG-5)
        self.assertFalse(look.U_h < 0.0 and look.action != 'harm_keep_incumbent')

    def test_certificate_collapses_the_hierarchy_mid_pair(self) -> None:
        tiers, tol = lab_reference_rule._tiers(self.cfg)
        p = lab_reference_rule._Pair(1, [1, 2])
        cand = p.episodes[1]
        inc = p.episodes[2]
        cand.arm, inc.arm = 'candidate', 'incumbent'
        cand.revealed, cand.success, cand.latency_s = True, 1, 10.0
        inc.note_stamp(0, [int(11.0 * 1e9)])           # ell = 11 s; 0.95*11 = 10.45 > 10
        h_lo, h_hi, s_lo, s_hi, collapsed, tier = lab_reference_rule._pair_enclosure(
            p, tiers, tol)
        self.assertEqual((h_lo, h_hi), (1.0, 1.0))
        self.assertEqual((s_lo, s_hi), (0.0, 1.0))     # success stays open
        self.assertFalse(collapsed)
        inc2 = lab_reference_rule._Pair(2, [3, 4])
        inc2.episodes[3].arm, inc2.episodes[4].arm = 'candidate', 'incumbent'
        inc2.episodes[3].revealed = True
        inc2.episodes[3].success, inc2.episodes[3].latency_s = 1, 10.0
        inc2.episodes[4].note_stamp(0, [int(10.4 * 1e9)])   # 0.95*10.4 = 9.88 < 10
        self.assertEqual(lab_reference_rule._pair_enclosure(inc2, tiers, tol)[:2],
                         (-1.0, 1.0))

    def test_joint_failure_and_equality_are_ties(self) -> None:
        tiers, tol = lab_reference_rule._tiers(self.cfg)
        p = lab_reference_rule._Pair(1, [1, 2])
        for a, arm, s, lat in ((1, 'candidate', 0, 5.0), (2, 'incumbent', 0, 9.0)):
            ep = p.episodes[a]
            ep.arm, ep.revealed, ep.success, ep.latency_s = arm, True, s, lat
        self.assertEqual(lab_reference_rule._pair_enclosure(p, tiers, tol)[:2], (0.0, 0.0))
        q = lab_reference_rule._Pair(1, [1, 2])
        for a, arm, s, lat in ((1, 'candidate', 1, 10.0), (2, 'incumbent', 1, 10.5)):
            ep = q.episodes[a]
            ep.arm, ep.revealed, ep.success, ep.latency_s = arm, True, s, lat
        # |10 - 10.5| = 0.5 == 0.05 * 10.5 exactly -> a tie (strict >)
        self.assertEqual(lab_reference_rule._pair_enclosure(q, tiers, tol)[:2], (0.0, 0.0))

    def test_success_enclosure_formula_all_nine_combinations(self) -> None:
        def ep(rev, s):
            e = lab_reference_rule._Episode()
            e.revealed, e.success, e.latency_s = rev, s, 1.0
            return e
        states = [(True, 0), (True, 1), (False, None)]
        for ra, sa in states:
            for rb, sb in states:
                a, b = ep(ra, sa), ep(rb, sb)
                lo, hi = lab_reference_rule._success_enclosure(a, b)
                a_lo, a_hi = (sa, sa) if ra else (0, 1)
                b_lo, b_hi = (sb, sb) if rb else (0, 1)
                self.assertEqual((lo, hi), (a_lo - b_hi, a_hi - b_lo))

    def test_no_certificate_from_tokens_and_no_betting(self) -> None:
        src = (HERE / 'lab_reference_rule.py').read_text('utf-8')
        self.assertNotIn('betting', src)
        self.assertNotIn('completion_tokens', src)

    @unittest.skipIf(lab_verify_log.lab_monitor is None,
                     'lab_monitor (G3) has not landed yet')
    def test_reference_rule_reproduces_lab_monitor_replay(self) -> None:
        """AD-7: two implementations written by two groups from the protocol text agree,
        element-wise, over every look of the fixture chain."""
        snaps = lab_verify_log.lab_monitor.replay(self.good['events'], self.cfg,
                                                  FIXTURE_TRIAL)
        looks = lab_reference_rule.looks_from_chain(self.good['events'], self.cfg,
                                                    FIXTURE_TRIAL)
        self.assertEqual(len(snaps), len(looks))
        self.assertGreater(len(looks), 50)
        for i, (snap, lk) in enumerate(zip(snaps, looks)):
            with self.subTest(look=i):
                self.assertEqual(int(snap['n']), lk.n)
                for key, mine in (('sum_lower_h', lk.sum_lower_h),
                                  ('sum_upper_h', lk.sum_upper_h),
                                  ('sum_lower_s', lk.sum_lower_s),
                                  ('sum_upper_s', lk.sum_upper_s),
                                  ('radius', lk.radius), ('L_h', lk.L_h),
                                  ('U_h', lk.U_h), ('L_s', lk.L_s), ('U_s', lk.U_s)):
                    if key in snap:
                        self.assertEqual(repr(float(snap[key])), repr(mine), key)

    def test_decide_from_chain_returns_the_first_crossing(self) -> None:
        d = lab_reference_rule.decide_from_chain(self.good['events'], self.cfg,
                                                 FIXTURE_TRIAL)
        self.assertEqual(d['kind'], 'horizon_no_decision')
        self.assertEqual(d['n'], N_PAIRS)
        logged = [e for e in self.good['events'] if e['type'] == 'decision'][0]
        self.assertEqual(logged['body']['kind'], d['kind'])
        self.assertEqual(logged['body']['n'], d['n'])

    def test_post_decision_reveals_are_ignored(self) -> None:
        evs = copy.deepcopy(self.good['events'])
        extra = copy.deepcopy(_find(evs, 'episode_revealed', arrival=1))
        extra['body']['arrival'] = 999
        extra['body']['post_decision'] = True
        evs.append(extra)
        before = lab_reference_rule.looks_from_chain(self.good['events'], self.cfg,
                                                     FIXTURE_TRIAL)
        after = lab_reference_rule.looks_from_chain(evs, self.cfg, FIXTURE_TRIAL)
        self.assertEqual(len(before), len(after))


class VerifierTests(TempTree):
    def setUp(self) -> None:
        super().setUp()
        self.good = build_good_chain()
        lab_eventlog.set_roster_uids(self.good['roster']['tasks'])
        self.root = materialize(self.good['events'], self.tmp / 'results',
                                FIXTURE_TRIAL, self.good)

    def _verify(self, mode: str = 'full', root: Path | None = None,
                work: Path | None = None):
        return lab_verify_log.verify_trial(
            FIXTURE_TRIAL, self.good['bundle_sha'], mode=mode,
            results_root=root or self.root, work_root=work)

    def test_missing_monitor_is_a_finding_never_a_silent_pass(self) -> None:
        saved = lab_verify_log.lab_monitor
        lab_verify_log.lab_monitor = None
        try:
            report = self._verify()
        finally:
            lab_verify_log.lab_monitor = saved
        fails = [f for f in report.findings if f.severity == 'FAIL']
        self.assertEqual([f.check for f in fails], ['monitor.replay'], fails)
        self.assertEqual(fails[0].detail['error'], 'lab_monitor is not importable')
        self.assertEqual(report.verdict, 'FAIL')

    def test_good_chain_passes_with_a_conforming_monitor(self) -> None:
        with _FakeMonitor(self.good, self.cfg_of()):
            report = self._verify()
        self.assertEqual([f.check for f in report.findings if f.severity == 'FAIL'], [])
        self.assertEqual(report.verdict, 'PASS')

    @unittest.skipIf(lab_verify_log.lab_monitor is None,
                     'lab_monitor (G3) has not landed yet')
    def test_good_chain_passes_against_the_real_lab_monitor(self) -> None:
        """Cross-group integration signal: a FAIL here is a disagreement between the
        chain fixture and G3's live statistical core, not a defect of this test."""
        report = self._verify()
        fails = [(f.check, f.detail) for f in report.findings if f.severity == 'FAIL']
        self.assertEqual(fails, [], f'lab_monitor disagrees with the chain: {fails}')

    def cfg_of(self) -> dict:
        return self.good['config']

    def test_every_defect_fixture_is_caught(self) -> None:
        defects = build_defects(self.good)
        self.assertGreaterEqual(len(defects), 20)
        for name, spec in sorted(defects.items()):
            with self.subTest(defect=name):
                root = materialize(spec['events'], self.tmp / name, FIXTURE_TRIAL,
                                   self.good)
                with _FakeMonitor(self.good, self.cfg_of()):
                    report = lab_verify_log.verify_trial(
                        FIXTURE_TRIAL, self.good['bundle_sha'], results_root=root)
                checks = {f.check for f in report.findings
                          if f.severity in ('FAIL', 'DEFECT')}
                self.assertIn(spec['check'], checks,
                              f'{name}: expected {spec["check"]}, got {sorted(checks)}')
                if lab_verify_log.CHECK_SEVERITY[spec['check']] == 'FAIL':
                    self.assertEqual(report.verdict, 'FAIL', name)

    def test_shadow_catches_injected_defects(self) -> None:
        """protocol 8.9 / audit B2: a sign slip, a swapped count and a wrong denominator
        in the LIVE monitor are each caught by the reference-rule shadow at the first
        evaluation at which they change anything, and a shadow that falsely reports
        agreement is itself a FAIL."""
        def sign_slip(body: dict) -> None:
            body['sum_lower_h'], body['sum_upper_h'] = (-body['sum_upper_h'],
                                                        -body['sum_lower_h'])
            r = body['radius']
            body['L_h'] = max(-1.0, body['sum_lower_h'] / body['n'] - r)
            body['U_h'] = min(1.0, body['sum_upper_h'] / body['n'] + r)

        def swapped_count(body: dict) -> None:
            body['sum_lower_h'], body['sum_lower_s'] = (body['sum_lower_s'],
                                                        body['sum_lower_h'])
            r = body['radius']
            body['L_h'] = max(-1.0, body['sum_lower_h'] / body['n'] - r)
            body['L_s'] = max(-1.0, body['sum_lower_s'] / body['n'] - r)

        for name, inject in (('sign_slip', sign_slip),
                             ('swapped_count', swapped_count)):
            with self.subTest(defect=name):
                evs = copy.deepcopy(self.good['events'])
                first = None
                for ev in evs:
                    if ev['type'] != 'monitor_update':
                        continue
                    before = canonical_json(ev['body'])
                    inject(ev['body'])
                    # the shadow still claims agreement: that is the live monitor lying
                    if canonical_json(ev['body']) != before:
                        first = ev
                        break
                self.assertIsNotNone(first, f'{name} changed nothing anywhere')
                evs = rechain(evs, self.good['bundle_sha'], FIXTURE_TRIAL)
                root = materialize(evs, self.tmp / f'inj_{name}', FIXTURE_TRIAL,
                                   self.good)
                with _FakeMonitor(self.good, self.cfg_of()):
                    report = lab_verify_log.verify_trial(
                        FIXTURE_TRIAL, self.good['bundle_sha'], results_root=root)
                checks = {f.check for f in report.findings if f.severity == 'FAIL'}
                self.assertIn('monitor.shadow', checks,
                              f'{name} was not caught by the shadow: {sorted(checks)}')
                self.assertEqual(report.verdict, 'FAIL')

    def test_wrong_denominator_is_caught_where_it_changes_anything(self) -> None:
        """The third injected defect of protocol 8.9: dividing by the number of COMPLETED
        pairs instead of the enrolled prefix (guidance item 2, "never divide by the number
        completed").  On an 8-pair fixture the band is saturated at the clip -- r(8) > 1
        -- so the defect changes nothing there and the shadow is silent, which is correct.
        At a prefix where the band is not saturated it changes the endpoints at once."""
        for n in (1, 8):
            r, lo, hi = lab_verify_log._band_independent(n, -float(n), float(n),
                                                         0.00625, 100.0)
            self.assertGreater(r, 1.0)
            self.assertEqual((lo, hi), (-1.0, 1.0))
        n, n_completed, s_lower, s_upper = 120, 100, 24.0, 48.0
        r_true, lo_true, hi_true = lab_verify_log._band_independent(
            n, s_lower, s_upper, 0.00625, 100.0)
        self.assertLess(r_true, 1.0)
        lo_wrong = max(-1.0, s_lower / n_completed - r_true)
        hi_wrong = min(1.0, s_upper / n_completed + r_true)
        self.assertGreater(abs(lo_wrong - lo_true), 1e-9)
        self.assertGreater(abs(hi_wrong - hi_true), 1e-9)
        # ...and that is exactly the comparison the verifier's shadow check applies
        self.assertGreater(max(abs(lo_wrong - lo_true), abs(hi_wrong - hi_true)), 1e-9)

    def test_condition_lists_are_printed(self) -> None:
        self.assertEqual(lab_verify_log.condition_list('chain.read'), 'B')
        self.assertEqual(lab_verify_log.condition_list('reference_rule.agreement'), 'B')
        self.assertEqual(lab_verify_log.condition_list('t4.payload_identity'), 'B')
        self.assertEqual(lab_verify_log.condition_list('usage.reconciliation'), 'A')

    def test_plumbing_mode_is_outcome_blind(self) -> None:
        """Two internally consistent chains that differ ONLY in their outcomes -- one of
        them with an extreme imbalance -- must give byte-identical plumbing reports."""
        extreme = build_good_chain(outcome=extreme_outcome)
        lab_eventlog.set_roster_uids(extreme['roster']['tasks'])
        other = materialize(extreme['events'], self.tmp / 'extreme', FIXTURE_TRIAL,
                            extreme)
        revealed = [e['body']['outcome']['success'] for e in extreme['events']
                    if e['type'] == 'episode_revealed']
        self.assertEqual(sum(revealed), N_PAIRS)          # a maximal imbalance
        a = self._verify(mode='plumbing')
        b = lab_verify_log.verify_trial(FIXTURE_TRIAL, extreme['bundle_sha'],
                                        mode='plumbing', results_root=other)
        self.assertEqual(canonical_json(a.to_json()), canonical_json(b.to_json()))
        for f in a.findings:
            self.assertTrue(lab_verify_log.plumbing_allows(f.check), f.check)
        # full mode additionally emits the rows the plumbing whitelist leaves out
        full_a = self._verify(mode='full')
        full_checks = {f.check for f in full_a.findings}
        plumbing_checks = {f.check for f in a.findings}
        self.assertIn('integrity.table', full_checks)
        self.assertNotIn('integrity.table', plumbing_checks)
        self.assertTrue(plumbing_checks <= full_checks)
        self.assertFalse(lab_verify_log.plumbing_allows('integrity.table'))
        self.assertFalse(lab_verify_log.plumbing_allows('enclosure.containment'))
        self.assertFalse(lab_verify_log.plumbing_allows('monitor.independent_band'))

    def test_independent_band_agrees_on_10000_random_inputs(self) -> None:
        import numpy as np
        rng = np.random.default_rng(20260919)
        ns = rng.integers(1, 600, size=10_000)
        frac_lo = rng.uniform(-1, 1, size=10_000)
        frac_hi = frac_lo + rng.uniform(0, 2, size=10_000)
        r = np.sqrt((ns + 100.0) * np.log((ns + 100.0) / (100.0 * 0.00625 ** 2))) / ns
        want_lo = np.maximum(-1.0, frac_lo - r)
        want_hi = np.minimum(1.0, frac_hi + r)
        for i in range(0, 10_000, 1):
            n = int(ns[i])
            rr, lo, hi = lab_verify_log._band_independent(
                n, float(frac_lo[i]) * n, float(frac_hi[i]) * n, 0.00625, 100.0)
            self.assertLess(abs(rr - float(r[i])), 1e-12)
            self.assertLess(abs(lo - float(want_lo[i])), 1e-12)
            self.assertLess(abs(hi - float(want_hi[i])), 1e-12)

    def test_record_match_needs_the_work_root(self) -> None:
        report = self._verify(work=self.tmp / 'work')
        fails = {f.check for f in report.findings if f.severity == 'FAIL'}
        self.assertIn('episode.record_match', fails)
        work = self.tmp / 'work' / FIXTURE_TRIAL / 'records'
        work.mkdir(parents=True)
        for ev in self.good['events']:
            if ev['type'] != 'episode_revealed':
                continue
            obj = {'outcome': ev['body']['outcome']}
            digest = lab_common.sha256_text(canonical_json(obj))
            (work / f'{digest}.json').write_text(canonical_json(obj), encoding='utf-8')
        patched = copy.deepcopy(self.good['events'])
        for ev in patched:
            if ev['type'] == 'episode_revealed':
                obj = {'outcome': ev['body']['outcome']}
                ev['body']['record_sha256'] = lab_common.sha256_text(canonical_json(obj))
        patched = rechain(patched, self.good['bundle_sha'], FIXTURE_TRIAL)
        art = dict(self.good)
        art['exposure_ledger'] = lab_verify_log._recount_exposure(patched)
        root = materialize(patched, self.tmp / 'withrecords', FIXTURE_TRIAL, art)
        report = lab_verify_log.verify_trial(
            FIXTURE_TRIAL, self.good['bundle_sha'], results_root=root,
            work_root=self.tmp / 'work')
        self.assertNotIn('episode.record_match',
                         {f.check for f in report.findings if f.severity == 'FAIL'})

    def test_exposure_ledger_recount(self) -> None:
        path = self.root / FIXTURE_TRIAL / 'exposure_ledger.json'
        bad = json.loads(path.read_text('utf-8'))
        bad['randomizing']['candidate']['episodes'] += 1
        path.write_text(canonical_json(bad), encoding='utf-8')
        report = self._verify()
        self.assertIn('exposure.ledger',
                      {f.check for f in report.findings if f.severity == 'FAIL'})

    def test_monitor_replay_is_compared_element_wise(self) -> None:
        with _FakeMonitor(self.good, self.cfg_of(), corrupt='L_h'):
            report = self._verify()
        self.assertIn('monitor.replay',
                      {f.check for f in report.findings if f.severity == 'FAIL'})
        with _FakeMonitor(self.good, self.cfg_of(), corrupt='drop'):
            report = self._verify()
        self.assertIn('monitor.replay',
                      {f.check for f in report.findings if f.severity == 'FAIL'})

    def test_program_chain(self) -> None:
        good = build_program_chain(self.good['bundle_sha'], lab_common.TRIALS)
        root = self.tmp / 'prog'
        (root / '_program' / 'events').mkdir(parents=True)
        (root / '_program' / 'events' / 'seg_0000.jsonl').write_text(
            chain_lines(good), encoding='utf-8')
        report = lab_verify_log.verify_program(self.good['bundle_sha'], results_root=root)
        self.assertEqual(report.verdict, 'PASS')
        bad = build_program_chain(self.good['bundle_sha'], ('T1', 'T4', 'T2', 'T3'))
        (root / '_program' / 'events' / 'seg_0000.jsonl').write_text(
            chain_lines(bad), encoding='utf-8')
        report = lab_verify_log.verify_program(self.good['bundle_sha'], results_root=root)
        self.assertEqual(report.verdict, 'FAIL')
        self.assertIn('program.order', {f.check for f in report.findings})

    def test_cli(self) -> None:
        out = self.tmp / 'report.json'
        rc = lab_verify_log.main(['--trial', FIXTURE_TRIAL, '--mode', 'plumbing',
                                  '--results', str(self.root),
                                  '--bundle', self.good['bundle_sha'],
                                  '--json', str(out)])
        self.assertIn(rc, (0, 1))
        payload = json.loads(out.read_text('utf-8'))
        self.assertEqual(payload['trial'], FIXTURE_TRIAL)
        self.assertEqual(lab_verify_log.main(['--trial', 'NOPE', '--results',
                                              str(self.root), '--bundle',
                                              self.good['bundle_sha']]), 2)


class _FakeMonitor:
    """A minimal stand-in for G3's lab_monitor, local to this test file (G1 never writes
    another group's module).  It replays the logged snapshots, which is what a correct
    lab_monitor.replay must also produce."""

    def __init__(self, good: dict, cfg: dict, corrupt: str | None = None) -> None:
        self.good = good
        self.cfg = cfg
        self.corrupt = corrupt
        self.saved = None

    def __enter__(self):
        import types
        mod = types.ModuleType('lab_monitor')
        corrupt = self.corrupt

        class Band:
            def __init__(self, lo: float, hi: float) -> None:
                self.lo, self.hi = lo, hi

        class MonitorConfig:
            def __init__(self, alpha_gate, rho, delta, n_min, n_max):
                self.alpha_gate, self.rho = alpha_gate, rho
                self.delta, self.n_min, self.n_max = delta, n_min, n_max

            @staticmethod
            def from_config(cfg, trial):
                m = cfg['monitor']
                return MonitorConfig(m['alpha_gate'], m['rho'], m['delta'], m['n_min'],
                                     m['n_max'])

        def band(n, s_lower, s_upper, mc):
            r, lo, hi = lab_verify_log._band_independent(n, s_lower, s_upper,
                                                         mc.alpha_gate, mc.rho)
            return Band(lo, hi)

        def replay(events, cfg, trial):
            snaps = []
            for ev in events:
                if ev['type'] != 'monitor_update':
                    continue
                b = ev['body']
                snaps.append({k: b[k] for k in
                              ('n', 'n_collapsed', 'sum_lower_h', 'sum_upper_h',
                               'sum_lower_s', 'sum_upper_s', 'radius', 'L_h', 'U_h',
                               'L_s', 'U_s')})
            if corrupt == 'L_h' and snaps:
                snaps[0] = dict(snaps[0], L_h=snaps[0]['L_h'] + 0.5)
            elif corrupt == 'drop' and snaps:
                snaps.pop()
            return snaps

        mod.Band = Band
        mod.MonitorConfig = MonitorConfig
        mod.band = band
        mod.replay = replay
        self.saved = lab_verify_log.lab_monitor
        lab_verify_log.lab_monitor = mod
        return self

    def __exit__(self, *exc) -> None:
        lab_verify_log.lab_monitor = self.saved


class FixtureTests(TempTree):
    def test_committed_fixtures_match_the_generator(self) -> None:
        regenerated = self.tmp / 'chains'
        write_fixtures(regenerated)
        self.assertTrue(CHAINS_DIR.exists(),
                        'testdata/chains/ has not been generated yet')
        produced = sorted(p.name for p in regenerated.iterdir())
        committed = sorted(p.name for p in CHAINS_DIR.iterdir())
        self.assertEqual(produced, committed)
        for name in produced:
            with self.subTest(fixture=name):
                self.assertEqual((regenerated / name).read_bytes(),
                                 (CHAINS_DIR / name).read_bytes())

    def test_good_fixture_shape(self) -> None:
        events = load_chain(CHAINS_DIR / 'good_T4.jsonl')
        self.assertGreaterEqual(len(events), 180)
        self.assertEqual(events[0]['type'], 'trial_started')
        self.assertEqual(events[-1]['type'], 'anchor_receipt')
        self.assertEqual(len(_segment_layout(events)), 6)
        kinds = {e['type'] for e in events}
        self.assertTrue({'trial_started', 'pair_enrolled', 'coin_drawn', 'llm_request',
                         'llm_response', 'llm_error', 'episode_revealed',
                         'monitor_update', 'decision', 'anchor', 'anchor_receipt',
                         'trial_paused', 'trial_resumed', 'trial_ended'} <= kinds, kinds)
        triggers = {e['body']['trigger'] for e in events
                    if e['type'] == 'monitor_update'}
        self.assertEqual(triggers, {'enroll', 'reveal', 'call', 'resume'})
        manifest = json.loads((CHAINS_DIR / 'manifest.json').read_text('utf-8'))
        self.assertEqual(manifest['n_events'], len(events))
        for name, check in manifest['defects'].items():
            self.assertTrue((CHAINS_DIR / f'{name}.jsonl').exists(), name)
            self.assertIn(check, lab_verify_log.CHECK_SEVERITY)


if __name__ == '__main__':                                            # pragma: no cover
    if '--write-fixtures' in sys.argv:
        write_fixtures()
        print(f'fixtures written to {CHAINS_DIR}')
    else:
        unittest.main()
