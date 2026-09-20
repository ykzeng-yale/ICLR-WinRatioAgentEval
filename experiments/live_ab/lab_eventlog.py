"""live_ab append-only, segmented, hash-chained event log and its schema validator.

Group G1.  Permitted imports: stdlib + lab_common.  Never numpy, never any other lab_*
module (ARCHITECTURE_FINAL.md 3.16).

The chain rule is ARCHITECTURE_FINAL.md 4.2 == protocol_FINAL.md 12.3:

    canon(x) = json.dumps(x, sort_keys=True, separators=(',',':'), ensure_ascii=False,
                          allow_nan=False)
    h_i      = sha256(canon(event_i without 'h'))
    prev_0   = sha256('live_ab/eventlog-v3|' + anchor_value + '|' + chain_id)
    line_i   = canon(event_i including 'h') + '\\n'      # ONE os.write

The event schema is ARCHITECTURE_FINAL.md sections 4.3 and 4.4, transcribed verbatim
below, with the string discipline of PG-11 / protocol 12.2 enforced field by field.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence, TypedDict

from lab_common import (ARMS, TRIALS, ChainError, SchemaError, UID_RE, PATH_TOKENS,
                        append_line_durable, canonical_json, sha256_bytes, sha256_text)

CHAIN_DOMAIN: str = 'live_ab/eventlog-v3'
SEGMENT_FMT: str = 'seg_%04d.jsonl'

CHAIN_IDS: tuple[str, ...] = ('_program', '_prefreeze', 'T1', 'T2', 'T3', 'T4')
ENVELOPE_KEYS: tuple[str, ...] = ('seq', 'type', 't_wall_ns', 't_mono_ns', 'inv', 'chain',
                                  'prev', 'body', 'h')


class Event(TypedDict):
    seq: int
    type: str
    t_wall_ns: int
    t_mono_ns: int
    inv: str
    chain: str
    prev: str
    body: dict
    h: str


def genesis_prev(anchor_value: str, chain_id: str) -> str:
    """[pure] sha256(CHAIN_DOMAIN + '|' + anchor_value + '|' + chain_id), the ONE genesis
    rule for all three kinds of chain (protocol 12.1).  `anchor_value` is the freeze-bundle
    sha256 for the program chain ('_program') and the four trial chains, and the literal
    token 'prefreeze' for the pre-freeze chain, which is written before the bundle exists.
    There is no second domain string."""
    return sha256_text(CHAIN_DOMAIN + '|' + anchor_value + '|' + chain_id)


def event_hash(ev: Mapping) -> str:
    """[pure] sha256 of canonical_json({k: v for k, v in ev.items() if k != 'h'})."""
    return sha256_text(canonical_json({k: v for k, v in ev.items() if k != 'h'}))


# =============================================================================
# string discipline (PG-11, protocol 12.2)
# =============================================================================
_HEX_RE = re.compile(r'^[0-9a-f]+$')
_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$')
_NUM_RE = re.compile(r'^-?[0-9]+$')
_LABEL_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}$')
_TOKEN_RE = re.compile(r'^<(WORK|HF_CACHE|LLAMA_BUILD|RESULTS|REPO|HOME|TMP|REMOTE)>'
                       r'(/[A-Za-z0-9_.+/=-]*)?$')
_KEY_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}$')

# A bare hex run of a length that is not one of the declared digest lengths is exactly what
# a foreign commit id looks like (protocol 12.2: no commit ids, no URLs, no prose).
_DIGEST_LENGTHS = (16, 32, 40, 64)


def _looks_like_commit_id(s: str) -> bool:
    return bool(_HEX_RE.match(s)) and 7 <= len(s) <= 40 and len(s) not in (16, 32)


def is_label(s: str) -> bool:
    """Form used for map keys and for the values of free-form provenance objects: no
    whitespace, no '/', no ':', no '@', at most 64 characters, and never a bare hex run
    that could be a commit id."""
    return bool(_LABEL_RE.match(s)) and not _looks_like_commit_id(s)


def is_token_path(s: str) -> bool:
    return bool(_TOKEN_RE.match(s))


# The roster registry backing string form (e): a task uid must be PRESENT in roster.json,
# not merely match the pattern (protocol 12.2 form (e), audit M13).
_ROSTER_UIDS: set[str] | None = None


def set_roster_uids(uids: Iterable[str] | None) -> None:
    """Install (or clear, with None) the roster membership set used by the 'uid' field
    kind.  The orchestrator installs it from roster.json before opening any chain."""
    global _ROSTER_UIDS
    _ROSTER_UIDS = None if uids is None else set(uids)


def load_roster_uids(path: Path) -> set[str]:
    """Read roster.json and install its uids.  Returns the installed set."""
    obj = json.loads(Path(path).read_text('utf-8'))
    tasks = obj.get('tasks', [])
    uids = {t if isinstance(t, str) else t['uid'] for t in tasks}
    set_roster_uids(uids)
    return uids


def roster_uids() -> set[str] | None:
    """The installed roster membership set, or None when no roster is installed (the
    pre-freeze chain is written before roster.json exists)."""
    return None if _ROSTER_UIDS is None else set(_ROSTER_UIDS)


# =============================================================================
# field specs
# =============================================================================
@dataclass(frozen=True)
class FieldSpec:
    kind: Literal['int', 'float', 'bool', 'hex64', 'hex40', 'hex32', 'hex16', 'enum',
                  'token_path', 'iso8601', 'list', 'obj', 'null_or', 'uid', 'label']
    required: bool = True
    enum: tuple[str, ...] = ()
    item: 'FieldSpec | None' = None      # for 'list'; for 'obj' it types every map value
    fields: 'dict[str, FieldSpec] | None' = None    # for 'obj'
    inner: 'FieldSpec | None' = None     # for 'null_or'


def _I() -> FieldSpec: return FieldSpec('int')
def _F() -> FieldSpec: return FieldSpec('float')
def _B() -> FieldSpec: return FieldSpec('bool')
def _H64() -> FieldSpec: return FieldSpec('hex64')
def _H32() -> FieldSpec: return FieldSpec('hex32')
def _H16() -> FieldSpec: return FieldSpec('hex16')
def _TOK() -> FieldSpec: return FieldSpec('token_path')
def _ISO() -> FieldSpec: return FieldSpec('iso8601')
def _UID() -> FieldSpec: return FieldSpec('uid')
def _LAB() -> FieldSpec: return FieldSpec('label')
def _E(*vals: str) -> FieldSpec: return FieldSpec('enum', enum=tuple(vals))
def _L(item: FieldSpec) -> FieldSpec: return FieldSpec('list', item=item)


def _O(fields: dict[str, FieldSpec] | None = None,
       item: FieldSpec | None = None) -> FieldSpec:
    return FieldSpec('obj', fields=fields, item=item)


def _N(inner: FieldSpec) -> FieldSpec: return FieldSpec('null_or', inner=inner)
def _opt(spec: FieldSpec) -> FieldSpec: return replace(spec, required=False)


# ---- closed vocabularies ----------------------------------------------------
E_TRIAL = _E(*sorted(TRIALS))
E_ARM = _E(*ARMS)
E_WORKFLOW = _E('single_shot', 'self_test_repair')
E_SERVER = _E('coder', 't3')
E_STRATUM = _E('S1', 'S2')                      # no 'mixed' stratum (audit B5)
E_PHASE = _E('prefreeze', 'smoke', 'server_smoke', 'randomizing', 'draining',
             'post_decision', 'paused', 'ended', 'aborted')
E_DECISION_KIND = _E('deploy_candidate', 'harm_keep_incumbent', 'horizon_no_decision')
E_ACTION = _E('none', 'deploy_candidate', 'harm_keep_incumbent', 'horizon_no_decision')
E_TRIGGER = _E('enroll', 'reveal', 'call', 'resume', 'drain')
E_RULE_ID = _E('nm_guarded_v3')
E_ERROR_CLASS = _E('timeout', 'connection', 'http_4xx', 'http_5xx', 'malformed')
E_OUTCOME_ERROR_CLASS = _E('timeout', 'connection', 'http_4xx', 'http_5xx', 'malformed',
                           'worker_died', 'episode_timeout', 'interrupted',
                           'verifier_timeout', 'receipt_mismatch', 'no_code')
E_FINISH = _E('stop', 'length', 'tool_calls', 'content_filter', 'abort')
E_TRIAL_PAUSE = _E('power', 'disk', 'server_unrecoverable', 'anchor_unavailable',
                   'monitor_exception', 'monitor_mismatch', 'worktree_drift',
                   'plumbing_fail', 'planned', 'operator_discretion')
E_PROGRAM_PAUSE = _E('plumbing_fail', 'power', 'disk', 'anchor_unavailable',
                     'worktree_drift', 'operator_discretion')
E_ABORT_REASON = _E('server_identity', 'receipt_mismatch', 'infrastructure',
                    'chain_unreadable', 'harness_defect', 'disk', 'operator_discretion',
                    'worktree_drift')
E_PREFLIGHT = _E('weights_hash', 'serving_manifest', 'port_busy', 'api_key_env', 'disk_low',
                 'freeze_bundle_drift', 'worktree_identity', 'clock_equivalence',
                 'run_lock', 'hardware_allowlist', 'package_lock', 'config_sha',
                 'roster_sha', 'order_sha', 'winstats_sha', 'harness_file_sha',
                 'gguf_sha256', 'llama_commit', 'preflight_rule_failed',
                 'host_not_quiescent')
# The host quiescence gate of protocol 5.7 (lab_hostcheck).  Both vocabularies are
# transcribed from that module rather than imported, so the schema stays a G1 artifact that
# depends on nothing below it; tests_lab_hostcheck asserts the two lists agree exactly.
E_HOST_DETECTOR = _E('llama-cli', 'llama-server', 'metal-process', 'metal-python',
                     'mlx-lm', 'ollama', 'vllm')
E_HOST_DEGRADED = _E('lsof_failed', 'lsof_incomplete', 'lsof_timeout', 'lsof_unavailable',
                     'probe_budget_exhausted', 'ps_line_unparsed', 'ps_unavailable',
                     'scan_error')
E_ANCHOR_TRIGGER = _E('trial_started', 'every_25_completed_pairs', 'decision',
                      'trial_paused', 'trial_resumed', 'refreeze_authorization',
                      'trial_ended', 'trial_aborted', 'operator_action', 'program_paused',
                      'program_resumed', 'preflight_refused', 'plumbing_verdict_fail',
                      'erratum', 'chain_unreadable')
E_ANCHOR_ERROR = _E('tree_state', 'push', 'api', 'scanner', 'timeout', 'dry_run')
E_TRIAL_STATUS = _E('ended', 'aborted', 'not_started', 'chain_unreadable')
E_INVOCATION_STATUS = _E('ended', 'aborted', 'paused', 'refused', 'interrupted')
E_SCOPE = _E('reporting_code')
E_CHECK_VERDICT = _E('PASS', 'FAIL', 'DEFECT', 'INFO')
E_COMPONENT = _E('lab_coin', 'lab_monitor', 'lab_enclosure', 'lab_reference_rule',
                 'failure_rules', 'seed_rule', 'config')
E_ORPHAN_CHECK = _E('record_missing', 'record_hash', 'pid_mismatch', 'inv_mismatch',
                    'outcome_mismatch', 'spool_gap', 'no_terminal_line', 'request_mismatch')
E_SCRAPE_POINT = _E('trial_start', 'pair_boundary', 'before_failed_try', 'after_failed_try',
                    'restart', 'quiescent', 'trial_end')
E_WINDOW = _E('trial', 'pair', 'restart', 'quiescent', 'call')
E_CALL_KIND = _E('code', 'tests', 'repair', 'smoke')
E_OPERATOR_ACTION = _E('stop', 'start', 'pause', 'resume', 'inspect', 'acknowledge')
E_DETECTED_BY = _E('exit', 'health')
E_PARTNER_STATE = _E('running', 'revealed', 'not_started')
E_PATTERN_CLASS = _E('url', 'account', 'commit_id', 'absolute_path', 'token')
E_REFREEZE_REASON = _E('reporting_code_defect', 'plumbing_fail', 'erratum')

# ---- shared sub-objects -----------------------------------------------------
HARDWARE = _O({'platform': _LAB(), 'machine': _LAB(), 'os_version': _LAB(),
               'cpu_brand_sha256': _H64(), 'memsize_bytes': _I(), 'ncpu': _I()})
PACKAGES = _O(item=_LAB())
HASH_MAP = _O(item=_H64())
INT_MAP = _O(item=_I())
NUM_OBJ = _O()          # free-form provenance object: scalars under the string discipline

WHAT_WAS_KNOWN = _O({
    'pairs_enrolled': _I(), 'pairs_completed': _I(),
    'revealed_by_arm': _O({'incumbent': _I(), 'candidate': _I()}),
    'L_h': _F(), 'U_h': _F(), 'L_s': _F(), 'U_s': _F(),
    'distance_to_harm': _F(), 'distance_to_deploy_h': _F(), 'distance_to_deploy_s': _F(),
    'earlier_trials': _L(_O({'trial': E_TRIAL, 'status': E_TRIAL_STATUS,
                             'decision_kind': _E('deploy_candidate', 'harm_keep_incumbent',
                                                 'horizon_no_decision', 'none'),
                             'final_head': _H64()})),
})

FILE_DIFFS = _L(_O({'file': _TOK(), 'old_sha256': _H64(), 'new_sha256': _H64(),
                    'diff_sha256': _H64()}))
DRIFT_LIST = _L(_O({'item': _LAB(), 'expected': _H64(), 'found': _H64()}))

SEED_RULE = _O({'source': _E('os.urandom(4)'), 'mask': _E('0x7FFFFFFE'),
                'low_bit': _E('worker_index'), 'forbidden': _L(_E('0xFFFFFFFF')),
                'unique_within_worker_half': _B(), 'unique_across_program': _B(),
                'logged_before_post': _B(),
                'duplicate_is': _E('logged_defect_no_outcome_effect')})

MONITOR_BLOCK = _O({
    'rule_id': E_RULE_ID, 'construction': _E('winstats.normal_mixture_radius'),
    'alpha_gate': _F(), 'rho': _F(), 'delta': _F(), 'n_min': _I(),
    'variance_process': _E('n'), 'clip': _L(_F()),
    'prefix': _E('current_full_enrolled'), 'retention': _B(),
    'running_intersection': _B(), 'harm_tail': _E('hierarchy_upper_only'),
    'tiers': _L(_O({'name': _E('success', 'cost'), 'higher_better': _B(),
                    'relative_tolerance': _F()})),
    'eligibility': _E('lower_tiers_require_both_success'),
})

COIN_BLOCK = _O({'source': _E('os.urandom(8)'), 'bit': _E('byte0&1'),
                 'map': _E('1->candidate_at_position_1'),
                 'unit': _E('pair', 'pre_enrolled_pair')})

ARM_SPEC = _O({'workflow': E_WORKFLOW, 'server_id': E_SERVER, 'alias': _LAB(),
               'gguf_sha256': _H64()})

USAGE = _O({'prompt_tokens': _I(), 'completion_tokens': _I(), 'total_tokens': _I(),
            'cached_tokens': _I()})
TIMINGS = _O({'cache_n': _I(), 'prompt_n': _I(), 'prompt_ms': _F(), 'predicted_n': _I(),
              'predicted_ms': _F(), 'predicted_per_second': _F()})
COUNTERS = _O({'prompt_tokens_total': _N(_I()), 'tokens_predicted_total': _N(_I()),
               'n_decode_total': _N(_I()), 'requests_processing': _N(_I()),
               'requests_deferred': _N(_I())})

SERVER_STARTED_FIELDS: dict[str, FieldSpec] = {
    'server_id': E_SERVER, 'pid': _I(), 'port': _I(), 'argv_sha256': _H64(),
    'gguf': _O({'bytes': _I(), 'sha256': _H64()}), 'props_sha256': _H64(),
    'props_matches_golden': _B(), 'total_slots': _I(), 'n_ctx': _I(),
    'load_seconds': _F(),
    'smoke': _O({'request_sha256': _H64(), 'receipt_matches_golden': _B(),
                 'usage': USAGE, 'timings': TIMINGS, 'ok': _B()}),
}

ANCHOR_FIELDS: dict[str, FieldSpec] = {
    'anchor_seq': _I(), 'upto_seq': _I(), 'upto_h': _H64(), 'segment_index': _I(),
    'segment_bytes': _I(), 'segment_sha256': _H64(), 'cumulative_bytes': _I(),
    'pairs_enrolled': _I(), 'pairs_completed': _I(), 'records_manifest_sha256': _H64(),
    'server_log_sha256': HASH_MAP, 'server_log_bytes': INT_MAP,
    'trigger': E_ANCHOR_TRIGGER, 'blocking': _B(),
}
ANCHOR_RECEIPT_FIELDS: dict[str, FieldSpec] = {
    'anchor_seq': _I(), 'pushed': _B(), 'comment_id': _N(_I()), 'created_at': _N(_ISO()),
    'updated_at': _N(_ISO()), 'receipt_sha256': _H64(), 'commit_sha256': _H64(),
}
ANCHOR_FAILED_FIELDS: dict[str, FieldSpec] = {
    'anchor_seq': _I(), 'error_class': E_ANCHOR_ERROR, 'blocking': _B(),
}
LOG_RECOVERY_FIELDS: dict[str, FieldSpec] = {
    'torn_offset': _I(), 'torn_len': _I(), 'torn_sha256': _H64(), 'segment_index': _I(),
    'is_event_prefix': _B(), 'boottime_changed': _B(),
}

# One foreign accelerator consumer, as it may enter the public chain (protocol 5.7).  The
# offender is named by its closed-vocabulary detector label and identified by the digest of
# its exact argv, which an operator can reproduce locally; the command text itself and the
# token summary derived from it are never published, because that summary's vocabulary is
# closed for paths but not for bare literals.
HOST_FINDING = _O({
    'pid': _I(), 'ppid': _I(), 'detector': E_HOST_DETECTOR, 'start_utc': _ISO(),
    'elapsed_s': _I(), 'rss_bytes': _I(), 'argv_sha256': _H64(),
    'summary_sha256': _H64(),
})
# Why the scan could not establish quiescence, as counts over a closed vocabulary.  A raw
# marker carries a pid or a count and is therefore kept out of the chain.
HOST_DEGRADED = _L(_O({'cause': E_HOST_DEGRADED, 'count': _I()}))
# `clean` is the recorded verdict and is redundant with the two lists by construction; the
# verifier asserts the agreement, so a chain that claims a clean host while carrying
# findings is a FAIL rather than a reader's problem.
HOST_SCAN_FIELDS: dict[str, FieldSpec] = {
    'point': E_SCRAPE_POINT, 'clean': _B(), 'scanned': _I(), 'allowlisted': _I(),
    'findings': _L(HOST_FINDING), 'degraded': HOST_DEGRADED,
}

# T14 identifying + timing keys, repeated by T15 and T16.
CALL_ID_FIELDS: dict[str, FieldSpec] = {
    'arrival': _I(), 'attempt': _I(), 'call_index': _I(), 'request_id': _H32(),
    'server_id': E_SERVER, 't_c1_ns': _I(), 't_send_ns': _I(),
}

OUTCOME = _O({
    'success': _I(), 'latency_s': _F(), 'completion_tokens': _I(), 'prompt_tokens': _I(),
    'n_llm_calls': _I(), 'n_failed_calls': _I(), 'connection_retries': _I(),
    'n_self_test_executions': _I(), 'n_verifier_executions': _I(), 'repair_rounds': _I(),
    'self_test_passed': _N(_B()), 'request_timeout_any': _B(), 'episode_timeout': _B(),
    'verifier_timeout': _B(), 'truncated_any': _B(), 'sentinel_seen': _B(),
    'entry_point_defined': _B(), 'error_class': _N(E_OUTCOME_ERROR_CLASS),
    'infra_flag': _B(),
})


# =============================================================================
# EVENT_SCHEMA (ARCHITECTURE_FINAL.md 4.3 and 4.4, transcribed)
# =============================================================================
EVENT_SCHEMA: dict[str, dict[str, FieldSpec]] = {
    # ---- 4.3 program chain -------------------------------------------------
    'program_opened': {
        'freeze_bundle_sha256': _H64(), 'config_sha256': _H64(),
        'rule_block_sha256': _H64(), 'protocol_sha256': _H64(),
        'prefreeze_head': _H64(), 'prefreeze_bytes': _I(),
        'prefreeze_file_sha256': _H64(), 'trial_order': _L(E_TRIAL),
        'n_pairs_max': _I(),
        'alpha': _O({'program': _F(), 'trial': _F(), 'gate': _F()}),
        'rho': _F(), 'delta': _F(), 'n_min': _I(), 'rule_id': E_RULE_ID,
        'harness_file_sha256': HASH_MAP, 'reused_file_sha256': HASH_MAP,
        'winstats_sha256': _H64(), 'hardware': HARDWARE, 'packages': PACKAGES,
        'freeze_receipt': _O({'comment_id': _N(_I()), 'created_at': _N(_ISO()),
                              'receipt_sha256': _N(_H64())}),
    },
    'trial_opened': {
        'trial': E_TRIAL, 'genesis_prev': _H64(), 'order_sha256': _H64(),
        'roster_sha256': _H64(), 'refreezes_in_force': _L(_H64()),
    },
    'trial_closed': {
        'trial': E_TRIAL, 'status': E_TRIAL_STATUS, 'final_head': _N(_H64()),
        'final_seq': _N(_I()), 'end_receipt_id': _N(_I()),
        'reason': _N(_E(*sorted(set(E_ABORT_REASON.enum) | set(E_PREFLIGHT.enum)))),
    },
    'plumbing_verdict': {
        'trial': E_TRIAL, 'verdict': _E('PASS', 'FAIL'),
        'checks': _O(item=E_CHECK_VERDICT), 'report_sha256': _H64(),
    },
    'refreeze_authorization': {
        'reason_code': E_REFREEZE_REASON, 'files': FILE_DIFFS,
        'what_was_known': WHAT_WAS_KNOWN, 'scope': E_SCOPE,
    },
    'preflight_refused': {
        'trial': E_TRIAL, 'checks_failed': _L(E_PREFLIGHT), 'drift': DRIFT_LIST,
    },
    # protocol 5.7: the trial-start quiescence gate refused to open a trial.  Written to
    # the PROGRAM chain, beside the preflight_refused that carries the reason code, because
    # it happens before the trial chain's seq 0.
    'host_quiescence_refused': dict(HOST_SCAN_FIELDS, trial=E_TRIAL),
    'program_paused': {'reason_code': E_PROGRAM_PAUSE, 'what_was_known': WHAT_WAS_KNOWN},
    'program_resumed': {'reason_code': E_PROGRAM_PAUSE, 'what_was_known': WHAT_WAS_KNOWN},
    'erratum': {
        'scope': E_SCOPE, 'files': FILE_DIFFS, 'output_sha256_before': _H64(),
        'output_sha256_after': _H64(), 'what_was_known': WHAT_WAS_KNOWN,
    },
    'decision_code_defect': {
        'component': E_COMPONENT, 'trials_affected': _L(E_TRIAL),
        'claims_dropped': _L(_I()), 'what_was_known': WHAT_WAS_KNOWN,
    },
    'program_closed': {
        'trials': _L(_O({'trial': E_TRIAL, 'status': E_TRIAL_STATUS,
                         'final_head': _H64()})),
        'final_head': _H64(),
    },
    # ---- pre-freeze chain --------------------------------------------------
    'prefreeze_closed': {
        'head': _H64(), 'bytes': _I(), 'file_sha256': _H64(), 'phase': E_PHASE,
        'n_events': _I(),
    },
    # ---- 4.4 trial chain ---------------------------------------------------
    'trial_started': {
        'freeze_bundle_sha256': _H64(), 'program_head': _H64(), 'config_sha256': _H64(),
        'rule_block_sha256': _H64(), 'order_sha256': _H64(), 'roster_sha256': _H64(),
        'task_content_sha256': _H64(), 'n_pairs_max': _I(),
        'arms': _O({'incumbent': ARM_SPEC, 'candidate': ARM_SPEC}),
        'monitor': MONITOR_BLOCK, 'coin': COIN_BLOCK, 'seed_rule': SEED_RULE,
        'failure_rules_sha256': _H64(), 'harness_file_sha256': HASH_MAP,
        'reused_file_sha256': HASH_MAP, 'winstats_sha256': _H64(),
        'sandbox_profile_sha256': _H64(), 'golden_props_sha256': HASH_MAP,
        'golden_generation_settings_sha256': HASH_MAP, 'hardware': HARDWARE,
        'packages': PACKAGES, 'llama_cpp_commit_sha256': _H64(),
        'refreezes_in_force': _L(_H64()),
    },
    'invocation_started': {
        'pid': _I(), 'argv_sha256': _H64(), 'argv_tokens': _L(_TOK()), 'resumed': _B(),
        'head_at_start': _H64(),
        'state': _O({'pairs_enrolled': _I(), 'pairs_completed': _I(),
                     'open_attempts': _I(), 'phase': E_PHASE}),
        'boottime_hash': _H64(), 'drift': DRIFT_LIST,
    },
    'invocation_refused': {'checks_failed': _L(E_PREFLIGHT), 'drift': DRIFT_LIST},
    'server_started': dict(SERVER_STARTED_FIELDS),
    'server_restarted': dict(SERVER_STARTED_FIELDS, props_equal_previous=_B()),
    'server_health': {'server_id': E_SERVER, 'ok': _B(), 'slots_busy': _I(),
                      'rss_bytes': _I(), 'clock_anomaly': _B()},
    'metrics_scrape': {'server_id': E_SERVER, 'point': E_SCRAPE_POINT, 'ok': _B(),
                       'counters': COUNTERS, 'tries': _I(), 'unreconciled': _B()},
    # protocol 5.7: the host scan taken at the trial-start scrape and at every quiescent
    # scrape.  It is written whether or not anything was found, so that a reader can see
    # positively that the host was scanned and was clean, rather than inferring it from the
    # absence of an event.
    'foreign_load_detected': dict(HOST_SCAN_FIELDS),
    'server_down': {'server_id': E_SERVER, 'detected_by': E_DETECTED_BY,
                    'returncode': _N(_I()),
                    'inflight': _L(_O({'arrival': _I(), 'arm': E_ARM})),
                    'last_counters': COUNTERS, 'counters_lost': _B()},
    'server_stopped': {'server_id': E_SERVER, 'pid': _I(), 'returncode': _N(_I()),
                       'seconds': _F()},
    'pair_enrolled': {'pair': _I(), 'stratum': E_STRATUM, 'arrivals': _L(_I()),
                      'task_uids': _L(_UID()), 'phase': _E('randomizing'),
                      're_enrolled': _B()},
    'coin_drawn': {'pair': _I(), 'entropy_source': _E('os.urandom(8)'),
                   'raw_hex': _H16(), 'bit': _I(), 'assignment': _O(item=E_ARM)},
    'arm_assigned_by_decision': {'arrival': _I(), 'arm': E_ARM, 'decision_seq': _I()},
    'episode_started': {
        'arrival': _I(), 'pair': _I(), 'position': _I(), 'arm': E_ARM,
        'workflow': E_WORKFLOW, 'server_id': E_SERVER, 'worker_pid': _I(),
        'task_uid': _UID(), 'assignment_seq': _I(), 'payload_sha256': _H64(),
        'job_sha256': _H64(), 'enqueued_ns': _I(), 'dispatched_ns': _I(),
        'started_after_resume': _B(), 'partner_concurrent': _B(),
    },
    'job_accepted': {'arrival': _I(), 'attempt': _I(), 'worker_pid': _I(),
                     'spool_offset': _I(), 'worker_t_wall_ns': _I(),
                     'worker_t_mono_ns': _I()},
    'llm_request': dict(
        CALL_ID_FIELDS, kind=E_CALL_KIND, try_index=_I(), body_sha256=_H64(),
        messages_sha256=_H64(), n_messages=_I(), prompt_chars=_I(), seed=_I(),
        sampling_sent=NUM_OBJ, spool_offset=_I(), spool_fsync_ms=_F(),
        partner_inflight=_B(), recovered=_B()),
    'llm_response': dict(
        CALL_ID_FIELDS, http_status=_I(), model_matches_alias=_B(),
        finish_reason=E_FINISH, usage=USAGE, timings=TIMINGS,
        generation_settings_sha256=_H64(), receipt_mismatch=_L(_LAB()), id_slot=_I(),
        truncated=_B(), tokens_cached=_I(), tokens_evaluated=_I(), tokens_predicted=_I(),
        rendered_prompt_sha256=_H64(), content_sha256=_H64(), client_seconds=_F(),
        t_recv_ns=_I()),
    'llm_error': dict(
        CALL_ID_FIELDS, error_class=E_ERROR_CLASS, http_status=_N(_I()),
        error_sha256=_H64(), client_seconds=_F(), will_retry=_B(), usage_known=_B(),
        bracketing_scrapes=_L(_I()), bound_is_joint=_B()),
    'episode_revealed': {
        'arrival': _I(), 'pair': _I(), 'position': _I(), 'arm': E_ARM,
        'reveal_index': _I(), 'outcome': OUTCOME, 'record_sha256': _H64(),
        'final_code_sha256': _H64(), 'verify_program_sha256': _H64(),
        'static_flags': _L(_LAB()), 'hack_flags': _L(_LAB()),
        'worker_t_start_ns': _I(), 'worker_t_end_ns': _I(), 'verify_seconds': _F(),
        'sandbox_lock_wait_s': _F(),
        'overlap': _O({'seconds_with_partner': _F(), 'partner_arm': _N(E_ARM),
                       'partner_state_at_verify': _N(E_PARTNER_STATE)}),
        'certified_ell': _F(), 'tokens_known': _I(), 'recovered_orphan': _B(),
        'post_decision': _B(),
    },
    'orphan_rejected': {'arrival': _I(), 'attempt': _I(), 'check_failed': E_ORPHAN_CHECK,
                        'record_sha256': _N(_H64()), 'spool_sha256': _H64()},
    'monitor_update': {
        'trigger': E_TRIGGER, 'n': _I(), 'n_collapsed': _I(),
        'sum_lower_h': _F(), 'sum_upper_h': _F(), 'sum_lower_s': _F(),
        'sum_upper_s': _F(), 'radius': _F(), 'L_h': _F(), 'U_h': _F(), 'L_s': _F(),
        'U_s': _F(), 'pair_updated': _N(_I()),
        'pair_enclosure': _O({'h': _L(_F()), 's': _L(_F()), 'collapsed': _B(),
                              'decisive_tier': _I()}),
        'flags': _O({'n_min_ok': _B(), 'harm': _B(), 'deploy': _B(),
                     'success_guard_ok': _B()}),
        'shadow': _O({'n': _I(), 'L_h': _F(), 'U_h': _F(), 'L_s': _F(), 'U_s': _F(),
                      'action': E_ACTION, 'mismatch': _B()}),
        'readouts': _O({'L_s_vs_010': _F(), 'L_s_vs_015': _F(), 's1_restricted': _N(_F()),
                        'completed_prefix': _O({'n': _I(), 'L_h': _F(), 'U_h': _F(),
                                                'L_s': _F(), 'U_s': _F()})}),
        'sums_fsum': _B(), 'monitor_code_sha256': _H64(),
    },
    'decision': {
        'kind': E_DECISION_KIND, 'rule_id': E_RULE_ID, 'n': _I(), 'monitor_seq': _I(),
        'radius': _F(), 'L_h': _F(), 'U_h': _F(), 'L_s': _F(), 'U_s': _F(),
        'delta': _F(), 'alpha_gate': _F(),
        'inflight': _L(_O({'arrival': _I(), 'arm': E_ARM})),
        'next_unassigned_arrival': _N(_I()), 'decided_on_resume': _B(),
    },
    'traffic_switch': {'decision_seq': _I(), 'arm': E_ARM,
                       'effective_from_arrival': _I(), 'anchor_wait_ms': _I(),
                       'switch_latency_ms': _I()},
    'anchor': dict(ANCHOR_FIELDS),
    'anchor_receipt': dict(ANCHOR_RECEIPT_FIELDS),
    'anchor_failed': dict(ANCHOR_FAILED_FIELDS),
    'log_recovery': dict(LOG_RECOVERY_FIELDS),
    'trial_paused': {'reason_code': E_TRIAL_PAUSE, 'what_was_known': WHAT_WAS_KNOWN,
                     'digests': _opt(_L(_O({'file': _TOK(), 'expected': _H64(),
                                            'observed': _H64()})))},
    'trial_resumed': {'reason_code': E_TRIAL_PAUSE, 'what_was_known': WHAT_WAS_KNOWN,
                      'digests': _opt(_L(_O({'file': _TOK(), 'expected': _H64(),
                                             'observed': _H64()})))},
    'operator_action': {'action': E_OPERATOR_ACTION, 'reason_code': E_TRIAL_PAUSE,
                        'what_was_known': WHAT_WAS_KNOWN},
    'usage_reconciliation': {
        'server_id': E_SERVER, 'window': E_WINDOW, 'window_from_seq': _I(),
        'window_to_seq': _I(), 'counter_delta': INT_MAP, 'client_usage_sum': INT_MAP,
        'residual': _O({'prompt': _N(_I()), 'predicted': _N(_I())}),
        'reconciliation_defect': _B(), 'counters_lost': _B(),
    },
    'deposit_sealed': {'deposit_sha256': _H64(), 'deposit_bytes': _I(),
                       'n_records': _I(), 'n_spools': _I()},
    'publication_withheld': {'segment_index': _I(), 'pattern_class': E_PATTERN_CLASS},
    'invocation_ended': {'status': E_INVOCATION_STATUS, 'counts': INT_MAP},
    'trial_ended': {
        'status': _E('ended'), 'reason': _N(E_ABORT_REASON), 'phase': E_PHASE,
        'exposure_ledger': _O(), 'reconciliation_totals': _O(),
        'terminal_failures_by_arm': INT_MAP, 'n_torn_recoveries': _I(),
        'longest_unreceipted_span_s': _F(), 'what_was_known': WHAT_WAS_KNOWN,
        'final_head': _H64(),
    },
    'trial_aborted': {
        'status': _E('aborted'), 'reason': _N(E_ABORT_REASON), 'phase': E_PHASE,
        'exposure_ledger': _O(), 'reconciliation_totals': _O(),
        'terminal_failures_by_arm': INT_MAP, 'n_torn_recoveries': _I(),
        'longest_unreceipted_span_s': _F(), 'what_was_known': WHAT_WAS_KNOWN,
        'final_head': _H64(),
    },
}

PROGRAM_ONLY_TYPES: frozenset[str] = frozenset({
    'program_opened', 'trial_opened', 'trial_closed', 'plumbing_verdict',
    'refreeze_authorization', 'preflight_refused', 'host_quiescence_refused',
    'program_paused', 'program_resumed',
    'erratum', 'decision_code_defect', 'program_closed'})

TRIAL_ONLY_TYPES: frozenset[str] = frozenset({
    'trial_started', 'invocation_started', 'invocation_refused', 'server_started',
    'server_restarted', 'server_health', 'metrics_scrape', 'foreign_load_detected',
    'server_down', 'server_stopped',
    'pair_enrolled', 'coin_drawn', 'arm_assigned_by_decision', 'episode_started',
    'job_accepted', 'llm_request', 'llm_response', 'llm_error', 'episode_revealed',
    'orphan_rejected', 'monitor_update', 'decision', 'traffic_switch', 'trial_paused',
    'trial_resumed', 'operator_action', 'usage_reconciliation', 'deposit_sealed',
    'publication_withheld', 'invocation_ended', 'trial_ended', 'trial_aborted'})


# =============================================================================
# validation
# =============================================================================
def _fail(path: str, why: str) -> None:
    raise SchemaError(f'{path}: {why}')


def _check_generic_scalar(v: object, path: str) -> None:
    if isinstance(v, bool) or isinstance(v, int) or isinstance(v, float) or v is None:
        if isinstance(v, float) and (v != v or v in (float('inf'), float('-inf'))):
            _fail(path, 'non-finite float')
        return
    if isinstance(v, str):
        if (len(v) in (16, 32, 64) and _HEX_RE.match(v)) or is_token_path(v) \
                or _ISO_RE.match(v) or _NUM_RE.match(v) or UID_RE.match(v) or is_label(v):
            return
        _fail(path, 'string violates the field discipline of protocol 12.2 '
                    '(no URL, no commit id, no absolute path, no free text)')
    _fail(path, f'value of type {type(v).__name__} is not permitted')


def _check_generic(v: object, path: str) -> None:
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str) or not _KEY_RE.match(k):
                _fail(f'{path}.{k!r}', 'object key violates the field discipline')
            _check_generic(v[k], f'{path}.{k}')
        return
    if isinstance(v, list):
        for i, item in enumerate(v):
            _check_generic(item, f'{path}[{i}]')
        return
    _check_generic_scalar(v, path)


def _check_field(spec: FieldSpec, v: object, path: str) -> None:
    k = spec.kind
    if k == 'null_or':
        if v is None:
            return
        assert spec.inner is not None
        _check_field(spec.inner, v, path)
        return
    if k == 'int':
        if isinstance(v, bool) or not isinstance(v, int):
            _fail(path, 'expected int (bool is not an int here)')
        return
    if k == 'float':
        if isinstance(v, bool) or not isinstance(v, float):
            _fail(path, 'expected float (an int is not a float here)')
        if v != v or v in (float('inf'), float('-inf')):
            _fail(path, 'non-finite float')
        return
    if k == 'bool':
        if not isinstance(v, bool):
            _fail(path, 'expected bool')
        return
    if k in ('hex64', 'hex40', 'hex32', 'hex16'):
        want = int(k[3:])
        if not isinstance(v, str) or len(v) != want or not _HEX_RE.match(v):
            _fail(path, f'expected {want} lowercase hex characters')
        return
    if k == 'enum':
        if not isinstance(v, str) or v not in spec.enum:
            _fail(path, f'expected one of {list(spec.enum)!r}')
        return
    if k == 'token_path':
        if not isinstance(v, str) or not is_token_path(v):
            _fail(path, f'expected a tokenized path {list(PATH_TOKENS)!r}')
        return
    if k == 'iso8601':
        if not isinstance(v, str) or not _ISO_RE.match(v):
            _fail(path, 'expected an ISO-8601 UTC instant')
        return
    if k == 'uid':
        if not isinstance(v, str) or not UID_RE.match(v):
            _fail(path, 'expected a task uid matching ^(mbpp|mbpp_full|humaneval)/[0-9]+$')
        known = roster_uids()
        if known is not None and v not in known:
            _fail(path, 'task uid is not present in roster.json')
        return
    if k == 'label':
        if not isinstance(v, str) or not is_label(v):
            _fail(path, 'expected a bare label (no space, no /, no :, no commit id)')
        return
    if k == 'list':
        if not isinstance(v, list):
            _fail(path, 'expected a list')
        assert spec.item is not None
        for i, item in enumerate(v):
            _check_field(spec.item, item, f'{path}[{i}]')
        return
    if k == 'obj':
        if not isinstance(v, dict):
            _fail(path, 'expected an object')
        if spec.fields is not None:
            _check_fields(spec.fields, v, path)
            return
        if spec.item is not None:
            for key in v:
                if not isinstance(key, str) or not _KEY_RE.match(key):
                    _fail(f'{path}.{key!r}', 'object key violates the field discipline')
                _check_field(spec.item, v[key], f'{path}.{key}')
            return
        _check_generic(v, path)
        return
    _fail(path, f'unknown field kind {k!r}')


def _check_fields(fields: Mapping[str, FieldSpec], body: Mapping, path: str) -> None:
    for key, spec in fields.items():
        if key not in body:
            if spec.required:
                _fail(f'{path}.{key}' if path else key, 'required key is missing')
            continue
        _check_field(spec, body[key], f'{path}.{key}' if path else key)
    for key in body:
        if key not in fields:
            _fail(f'{path}.{key}' if path else key, 'unknown key')


def validate_event(etype: str, body: Mapping) -> None:
    """[pure] Raise SchemaError unless body matches EVENT_SCHEMA[etype] exactly: every
    required key present, no unknown key, every value of the declared type, every string
    satisfying the string discipline of PG-11, every int a real int (bool is not an int
    here), every float finite."""
    if etype not in EVENT_SCHEMA:
        raise SchemaError(f'unknown event type {etype!r}')
    if not isinstance(body, Mapping):
        raise SchemaError(f'{etype}: body must be an object')
    _check_fields(EVENT_SCHEMA[etype], body, '')


def validate_envelope(ev: Mapping) -> None:
    """Raise SchemaError unless the nine envelope keys of 4.1 are present with the right
    types.  The chain rules themselves (prev, seq, h) are checked by read_chain."""
    if set(ev) != set(ENVELOPE_KEYS):
        raise SchemaError(f'envelope keys {sorted(ev)} != {sorted(ENVELOPE_KEYS)}')
    if isinstance(ev['seq'], bool) or not isinstance(ev['seq'], int) or ev['seq'] < 0:
        raise SchemaError('seq must be a non-negative int')
    for key in ('t_wall_ns', 't_mono_ns'):
        if isinstance(ev[key], bool) or not isinstance(ev[key], int):
            raise SchemaError(f'{key} must be an int')
    if not isinstance(ev['type'], str) or ev['type'] not in EVENT_SCHEMA:
        raise SchemaError(f'unknown event type {ev["type"]!r}')
    if not isinstance(ev['inv'], str) or len(ev['inv']) != 32 or not _HEX_RE.match(ev['inv']):
        raise SchemaError('inv must be 32 lowercase hex characters')
    if ev['chain'] not in CHAIN_IDS:
        raise SchemaError(f'chain must be one of {list(CHAIN_IDS)}')
    if not isinstance(ev['prev'], str) or len(ev['prev']) != 64 \
            or not _HEX_RE.match(ev['prev']):
        raise SchemaError('prev must be 64 lowercase hex characters')
    if not isinstance(ev['h'], str) or len(ev['h']) != 64 or not _HEX_RE.match(ev['h']):
        raise SchemaError('h must be 64 lowercase hex characters')
    if not isinstance(ev['body'], dict):
        raise SchemaError('body must be an object')
    chain = ev['chain']
    etype = ev['type']
    if chain == '_program' and etype in TRIAL_ONLY_TYPES:
        raise SchemaError(f'{etype} may not appear on the program chain')
    if chain in TRIALS and etype in PROGRAM_ONLY_TYPES:
        raise SchemaError(f'{etype} may only appear on the program chain')


# =============================================================================
# reading a chain
# =============================================================================
@dataclass(frozen=True)
class TornRegion:
    segment: int
    offset: int
    length: int
    sha256: str
    is_event_prefix: bool


@dataclass(frozen=True)
class ChainRead:
    events: list[Event]
    torn: TornRegion | None
    segments: list[Path]
    segment_bytes: list[int]
    segment_sha256: list[str]


def segment_paths(events_dir: Path) -> list[Path]:
    """Every seg_NNNN.jsonl in `events_dir`, in numeric order.  Raises ChainError on a gap
    or on a name that is not a segment."""
    events_dir = Path(events_dir)
    found: dict[int, Path] = {}
    if events_dir.exists():
        for p in sorted(events_dir.iterdir()):
            if p.name.endswith('.tmp') or p.is_dir():
                continue
            m = re.fullmatch(r'seg_(\d{4})\.jsonl', p.name)
            if not m:
                raise ChainError(f'{p.name} is not a chain segment')
            found[int(m.group(1))] = p
    if not found:
        return []
    want = list(range(max(found) + 1))
    missing = [i for i in want if i not in found]
    if missing:
        raise ChainError(f'segment numbering has gaps: missing {missing}')
    return [found[i] for i in want]


def _is_event_prefix(raw: bytes) -> bool:
    """True when the torn bytes are a prefix of a plausible canonical event line.  A
    canonical event line always begins with '{"body":' because the keys are sorted."""
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return text.startswith('{"body":') and '\n' not in text


def _parse_line(line: bytes) -> dict | None:
    """A fully chain-shaped event, or None when the bytes are not one."""
    try:
        ev = json.loads(line.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(ev, dict):
        return None
    try:
        validate_envelope(ev)
    except SchemaError:
        return None
    return ev


def read_chain(events_dir: Path, chain_id: str, freeze_bundle_sha256: str) -> ChainRead:
    """Verify and return the whole chain (ARCHITECTURE_FINAL.md 3.2).

    Rules, all fatal (ChainError) unless stated:
      * segments are seg_0000..seg_NNNN with no gaps; every segment but the last ends with
        an `anchor` event; a closed segment is never reopened.
      * per line: json.loads succeeds; event_hash(ev) == ev['h']; ev['prev'] == previous h
        (across segment boundaries); ev['seq'] == len(events); ev['chain'] == chain_id;
        canonical_json(ev).encode('utf-8') == the raw line bytes (byte-identity round trip).
      * torn region: ALL bytes from the first invalid byte to the end of the LAST segment
        form one opaque region regardless of newlines inside it.  It is legal only as the
        unterminated tail, or when the next valid event is `log_recovery` committing to
        exactly (offset, length, sha256).  Two committed regions in a row, or a region not
        at the end, is a ChainError.
      * `t_wall_ns` decreasing by more than 1e9 ns inside one `inv` is recorded as a
        `clock_anomaly` finding, NOT a ChainError.
    """
    events_dir = Path(events_dir)
    segs = segment_paths(events_dir)
    events: list[Event] = []
    torn: TornRegion | None = None
    seg_bytes: list[int] = []
    seg_sha: list[str] = []
    prev = genesis_prev(freeze_bundle_sha256, chain_id)

    def _consume(ev: dict, path: Path, offset: int, line: bytes) -> None:
        nonlocal prev
        try:
            validate_event(ev['type'], ev['body'])
        except SchemaError as exc:
            raise ChainError(f'{path.name}@{offset}: schema violation: {exc}') from exc
        if canonical_json(ev).encode('utf-8') != line:
            raise ChainError(f'{path.name}@{offset}: byte identity violated '
                             '(re-canonicalisation differs from the raw line)')
        if event_hash(ev) != ev['h']:
            raise ChainError(f'{path.name}@{offset}: h does not match the event body')
        if ev['chain'] != chain_id:
            raise ChainError(f'{path.name}@{offset}: chain {ev["chain"]!r} != {chain_id!r}')
        if ev['seq'] != len(events):
            raise ChainError(f'{path.name}@{offset}: seq {ev["seq"]} != {len(events)}')
        if ev['prev'] != prev:
            raise ChainError(f'{path.name}@{offset}: prev does not link to the previous h')
        prev = ev['h']
        events.append(ev)                       # type: ignore[arg-type]

    for idx, path in enumerate(segs):
        raw = path.read_bytes()
        seg_bytes.append(len(raw))
        seg_sha.append(sha256_bytes(raw))
        is_last = (idx == len(segs) - 1)
        offset = 0
        seg_event_count = 0
        last_type_in_segment: str | None = None
        while offset < len(raw):
            nl = raw.find(b'\n', offset)
            line = raw[offset:nl] if nl >= 0 else raw[offset:]
            ev = _parse_line(line) if nl >= 0 else None
            if ev is None:
                # ---- an invalid byte: a torn region starts here ------------
                if not is_last:
                    raise ChainError(
                        f'{path.name}@{offset}: invalid bytes in a closed segment')
                if torn is not None:
                    raise ChainError('two torn regions in one chain')
                committed_at: int | None = None
                q = raw.find(b'\n', offset)
                while q >= 0:
                    nxt = _parse_line(raw[q + 1:raw.find(b'\n', q + 1)]
                                      if raw.find(b'\n', q + 1) >= 0 else raw[q + 1:])
                    if nxt is not None and nxt['type'] == 'log_recovery':
                        region = raw[offset:q]
                        b = nxt['body']
                        if (b['torn_offset'] == offset and b['torn_len'] == len(region)
                                and b['torn_sha256'] == sha256_bytes(region)
                                and b['segment_index'] == idx):
                            committed_at = q + 1
                            break
                    elif nxt is not None:
                        raise ChainError(
                            f'{path.name}@{offset}: invalid bytes followed by a valid event '
                            'that is not a committing log_recovery')
                    q = raw.find(b'\n', q + 1)
                if committed_at is None:
                    region = raw[offset:]
                    torn = TornRegion(segment=idx, offset=offset, length=len(region),
                                      sha256=sha256_bytes(region),
                                      is_event_prefix=_is_event_prefix(region))
                    offset = len(raw)
                    break
                region = raw[offset:committed_at - 1]
                torn = TornRegion(segment=idx, offset=offset, length=len(region),
                                  sha256=sha256_bytes(region),
                                  is_event_prefix=_is_event_prefix(region))
                offset = committed_at
                continue
            _consume(ev, path, offset, line)
            seg_event_count += 1
            last_type_in_segment = ev['type']
            offset = nl + 1
        if not is_last:
            if seg_event_count == 0:
                raise ChainError(f'{path.name}: a closed segment holds no event')
            if last_type_in_segment != 'anchor':
                raise ChainError(f'{path.name}: a closed segment must end with an anchor event')
    if segs and not events and any(seg_bytes):
        # protocol 6.4 row 25: a chain that cannot be opened at all.
        raise ChainError('the chain has segment bytes but no readable event')
    return ChainRead(events=events, torn=torn, segments=segs, segment_bytes=seg_bytes,
                     segment_sha256=seg_sha)


def clock_anomalies(events: Sequence[Mapping]) -> list[dict]:
    """t_wall_ns decreasing by more than 1e9 ns inside one `inv` is a finding, never a
    ChainError (ARCHITECTURE_FINAL.md 3.2)."""
    last: dict[str, int] = {}
    out: list[dict] = []
    for ev in events:
        inv = ev['inv']
        t = ev['t_wall_ns']
        if inv in last and t < last[inv] - 1_000_000_000:
            out.append({'seq': ev['seq'], 'delta_ns': t - last[inv]})
        last[inv] = max(last.get(inv, t), t)
    return out


# =============================================================================
# the writer
# =============================================================================
class EventLog:
    """Single-writer, append-only, segmented hash chain.  One instance per chain per
    process (AD-2: the orchestrator is the only writer of a chain).

    Opening an existing chain re-verifies it in full (read_chain) and refuses to append on
    any violation except a single torn region at the end of the last segment, which is
    committed by a log_recovery event (the file is NEVER truncated).
    """

    def __init__(self, events_dir: Path, chain_id: str, freeze_bundle_sha256: str,
                 inv: str, *, create: bool = False) -> None:
        self.events_dir = Path(events_dir)
        self.chain_id = chain_id
        self.bundle_sha = freeze_bundle_sha256
        self.inv = inv
        self._closed = False
        self.events_dir.mkdir(parents=True, exist_ok=True)
        existing = segment_paths(self.events_dir)
        if create and existing:
            raise ChainError(f'create=True but {len(existing)} segment(s) already exist')
        read = read_chain(self.events_dir, chain_id, freeze_bundle_sha256)
        self._events: list[Event] = list(read.events)
        self._segment_index = max(0, len(read.segments) - 1)
        self._genesis = genesis_prev(freeze_bundle_sha256, chain_id)
        seg_path = self.events_dir / (SEGMENT_FMT % self._segment_index)
        self._fd = os.open(str(seg_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        self._torn = read.torn
        if read.torn is not None:
            already = any(e['type'] == 'log_recovery'
                          and e['body']['torn_sha256'] == read.torn.sha256
                          for e in self._events)
            if not already:
                # Terminate the torn bytes with one newline so that the committed region
                # is exactly (offset, length, sha256); the file is never truncated.
                os.write(self._fd, b'\n')
                from lab_common import fullsync as _fullsync
                _fullsync(self._fd)
                self.append('log_recovery', {
                    'torn_offset': read.torn.offset, 'torn_len': read.torn.length,
                    'torn_sha256': read.torn.sha256, 'segment_index': read.torn.segment,
                    'is_event_prefix': read.torn.is_event_prefix,
                    'boottime_changed': False}, durable=True)

    # -- state ---------------------------------------------------------------
    @property
    def head(self) -> str:
        return self._events[-1]['h'] if self._events else self._genesis

    @property
    def seq(self) -> int:
        return len(self._events)

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    @property
    def segment_index(self) -> int:
        return self._segment_index

    # -- writing -------------------------------------------------------------
    def append(self, etype: str, body: dict, *, durable: bool = False) -> Event:
        """Validate the body, build the envelope, one os.write, fullsync when durable,
        append to self.events, return the event.  Raises SchemaError before any byte is
        written.  A durable append returns only after fullsync() has returned."""
        if self._closed:
            raise ChainError('the log is closed')
        import time as _time
        validate_event(etype, body)
        ev: dict = {
            'seq': len(self._events),
            'type': etype,
            't_wall_ns': _time.time_ns(),
            't_mono_ns': _time.monotonic_ns(),
            'inv': self.inv,
            'chain': self.chain_id,
            'prev': self.head,
            'body': body,
        }
        validate_envelope(dict(ev, h='0' * 64))
        ev['h'] = event_hash(ev)
        line = canonical_json(ev)
        append_line_durable(self._fd, line, durable=durable)
        self._events.append(ev)                 # type: ignore[arg-type]
        return ev                               # type: ignore[return-value]

    def close_segment(self, *, anchor_body: dict) -> Event:
        """Append the `anchor` event (durable), close the descriptor, open segment k+1.
        The anchor event is by definition the last line of its segment."""
        ev = self.append('anchor', anchor_body, durable=True)
        os.close(self._fd)
        self._segment_index += 1
        seg_path = self.events_dir / (SEGMENT_FMT % self._segment_index)
        if seg_path.exists():
            raise ChainError(f'{seg_path.name} already exists')
        self._fd = os.open(str(seg_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        return ev

    def close(self) -> None:
        if not self._closed:
            os.close(self._fd)
            self._closed = True

    def __enter__(self) -> 'EventLog':
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
