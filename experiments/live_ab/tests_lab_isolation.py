"""G1 tests: the import-isolation matrix and the public-signature contract.

ARCHITECTURE_FINAL.md 3.16 ("import isolation is a test, not a convention") and section 10
("a signature test in tests_lab_isolation.py uses inspect.signature on every public name in
this document").

The AST checks run against any module that exists on disk, so they are a live gate while
G2-G5 are still writing theirs.  The signature checks are asserted hard for the modules G1
owns and for every other module that imports; a module that is absent or not yet importable
is reported as a skip rather than as a failure of this group.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

G1_MODULES = ('lab_common', 'lab_eventlog', 'lab_verify_log', 'lab_reference_rule')

THIRD_PARTY = frozenset({'numpy', 'pandas', 'requests', 'scipy'})
PILOT = frozenset({'agent', 'sandbox', 'verify', 'data', 'common'})
WINSTATS = frozenset({'winstats'})

# ---------------------------------------------------------------------------
# the matrix of ARCHITECTURE_FINAL.md 3.16, transcribed row by row
# ---------------------------------------------------------------------------
MATRIX: dict[str, set[str]] = {
    'lab_common': set(),
    'lab_eventlog': {'lab_common'},
    'lab_verify_log': {'numpy', 'winstats', 'lab_common', 'lab_eventlog', 'lab_design',
                       'lab_monitor', 'lab_enclosure', 'lab_reference_rule'},
    'lab_reference_rule': {'numpy', 'winstats'},
    'lab_data': {'requests', 'lab_common', 'agent', 'sandbox', 'verify', 'data',
                 'common'},
    'lab_design': {'numpy', 'lab_common'},
    'lab_coin': {'lab_common', 'lab_eventlog'},
    'lab_monitor': {'numpy', 'winstats', 'lab_common', 'lab_enclosure'},
    'lab_enclosure': {'numpy', 'winstats', 'lab_common'},
    'lab_client': {'requests', 'lab_common'},
    'lab_server': {'requests', 'lab_common'},
    'lab_mock_server': set(),
    'lab_worker': {'requests', 'lab_common', 'lab_client', 'lab_data', 'agent',
                   'sandbox', 'verify', 'data', 'common'},
    # lab_hostcheck is the host quiescence gate of protocol 5.7.  It sits beside
    # lab_server in the matrix: standard library plus lab_common, imported by the
    # orchestrator and by nothing below it.
    'lab_hostcheck': {'lab_common'},
    'lab_orchestrator': {'requests', 'lab_common', 'lab_eventlog', 'lab_data',
                         'lab_design', 'lab_coin', 'lab_monitor', 'lab_enclosure',
                         'lab_reference_rule', 'lab_server', 'lab_hostcheck'},
    'lab_anchor': {'requests', 'lab_common'},
    'build_live_ab_results': {'numpy', 'pandas', 'winstats', 'lab_common',
                              'lab_eventlog', 'lab_monitor', 'lab_enclosure',
                              'lab_reference_rule'},
}
LAB_NAMES = frozenset(set(MATRIX) | {'dryrun_live_ab'})


def module_path(name: str) -> Path:
    return HERE / f'{name}.py'


def imported_names(path: Path) -> set[str]:
    """Every top-level package name imported anywhere in the file, including inside a
    function body or a try block."""
    tree = ast.parse(path.read_text('utf-8'), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError(f'{path.name}: relative import')
            if node.module:
                out.add(node.module.split('.')[0])
    return out


def interesting(names: set[str]) -> set[str]:
    """Drop the standard library; what is left is what the matrix governs."""
    return {n for n in names if n not in sys.stdlib_module_names}


def calls_os_urandom(path: Path) -> bool:
    tree = ast.parse(path.read_text('utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == 'urandom':
            return True
        if isinstance(node, ast.ImportFrom) and node.module == 'os' \
                and any(a.name == 'urandom' for a in node.names):
            return True
    return False


class ImportIsolationTests(unittest.TestCase):
    def test_import_isolation_matrix(self) -> None:
        checked = 0
        for name, permitted in sorted(MATRIX.items()):
            path = module_path(name)
            if not path.exists():
                continue
            checked += 1
            with self.subTest(module=name):
                got = interesting(imported_names(path))
                forbidden = sorted(got - permitted)
                self.assertEqual(forbidden, [],
                                 f'{name} imports {forbidden}, which its row of '
                                 f'ARCHITECTURE_FINAL.md 3.16 forbids')
        self.assertGreaterEqual(checked, len(G1_MODULES))

    def test_reference_rule_imports_nothing_from_the_lab_namespace(self) -> None:
        """AD-7 / protocol 8.9: the strictest row in the matrix, and that is the point.
        A defect in the live statistical core must not be able to reach the shadow."""
        got = imported_names(module_path('lab_reference_rule'))
        self.assertEqual(sorted(got & LAB_NAMES), [])
        self.assertNotIn('lab_common', got)
        self.assertNotIn('lab_monitor', got)
        self.assertNotIn('lab_enclosure', got)
        self.assertEqual(sorted(interesting(got)), ['numpy', 'winstats'])

    def test_monitor_verifier_and_builder_avoid_the_orchestrator_and_the_worker(self) -> None:
        for name in ('lab_monitor', 'lab_verify_log', 'build_live_ab_results'):
            path = module_path(name)
            if not path.exists():
                continue
            with self.subTest(module=name):
                got = imported_names(path)
                for banned in ('lab_orchestrator', 'lab_worker', 'lab_client',
                               'lab_server', 'lab_anchor', 'lab_mock_server'):
                    self.assertNotIn(banned, got, f'{name} must not import {banned}')

    def test_orchestrator_does_not_import_the_worker(self) -> None:
        path = module_path('lab_orchestrator')
        if not path.exists():
            self.skipTest('lab_orchestrator (G5) has not landed yet')
        self.assertNotIn('lab_worker', imported_names(path))
        self.assertNotIn('lab_client', imported_names(path))

    def test_only_lab_coin_and_lab_client_call_os_urandom(self) -> None:
        for name in sorted(MATRIX):
            path = module_path(name)
            if not path.exists():
                continue
            with self.subTest(module=name):
                if name in ('lab_coin', 'lab_client'):
                    continue
                self.assertFalse(calls_os_urandom(path),
                                 f'{name} calls os.urandom; only lab_coin (the coin) and '
                                 'lab_client (the per-request seed) may')

    def test_design_has_no_assignment(self) -> None:
        path = module_path('lab_design')
        if not path.exists():
            self.skipTest('lab_design (G2) has not landed yet')
        src = path.read_text('utf-8')
        hit = re.search(r'\b(urandom|coin|arm|incumbent|candidate)\b', src)
        self.assertIsNone(
            hit, '' if hit is None else
            f'lab_design contains {hit.group(0)!r} at offset {hit.start()}: this file '
            'carries no coin, no arm and no assignment (ARCHITECTURE_FINAL.md 3.5)')

    def test_no_betting_in_the_decision_path(self) -> None:
        for name in ('lab_monitor', 'lab_reference_rule', 'lab_orchestrator'):
            path = module_path(name)
            if not path.exists():
                continue
            with self.subTest(module=name):
                self.assertNotIn('betting', path.read_text('utf-8'),
                                 f'{name} must not mention betting (PG-16)')

    def test_superseded_drafts_are_never_cited(self) -> None:
        """audit M16.  The needles are assembled at run time so that this file does not
        itself contain the forbidden strings."""
        needles = ('protocol' + '_draft_v2', 'protocol' + '_v3')
        for path in sorted(HERE.glob('*.py')):
            with self.subTest(module=path.name):
                src = path.read_text('utf-8')
                for needle in needles:
                    self.assertNotIn(needle, src,
                                     f'{path.name} cites a superseded draft')

    def test_no_module_or_test_name_denies_the_deploy_path(self) -> None:
        """audit B4: the near-certain abstention is a property of the data, never a
        property of the rule, and no output may say otherwise.  The needle is assembled
        at run time so that this file does not itself contain it."""
        needle = 'unreach' + 'able'
        for path in sorted(HERE.glob('*.py')):
            with self.subTest(module=path.name):
                self.assertNotIn(needle, path.read_text('utf-8').lower(),
                                 f'{path.name} describes the deploy path as impossible')


# ---------------------------------------------------------------------------
# the public signatures of ARCHITECTURE_FINAL.md section 3
# ---------------------------------------------------------------------------
# name -> (list of (param, default-repr-or-None, keyword_only)) for a callable,
#         or ('#fields', [names...]) for a dataclass / TypedDict,
#         or ('#const',) for a module constant.
KW = True
PO = False


def fn(*params) -> tuple:
    return ('#call', list(params))


def fields(*names: str) -> tuple:
    return ('#fields', list(names))


CONST = ('#const',)

SIGNATURES: dict[str, dict[str, tuple]] = {
    'lab_common': {
        'HERE': CONST, 'REPO_ROOT': CONST, 'SRC_DIR': CONST, 'LS_DIR': CONST,
        'RESULTS_ROOT': CONST, 'WORK_ROOT': CONST, 'FREEZE_DIR': CONST,
        'PROGRAM_CHAIN_ID': CONST, 'PREFREEZE_CHAIN_ID': CONST, 'TRIALS': CONST,
        'ARMS': CONST, 'FREEZE_BUNDLE_KEYS': CONST, 'HARNESS_FILES': CONST,
        'REUSED_FILES': CONST,
        'add_import_paths': fn(),
        'TrialPaths': fields('trial', 'results', 'events', 'anchors', 'work', 'jobs',
                             'spools', 'records', 'requests', 'anchor_spool',
                             'anchors_private', 'logs', 'run_lock', 'sandbox_lock'),
        'TrialPaths.mkdirs': fn(('self', None, PO)),
        'trial_paths': fn(('trial', None, PO)),
        'tokenize_path': fn(('p', None, PO)),
        'canonical_json': fn(('obj', None, PO)),
        'sha256_bytes': fn(('b', None, PO)),
        'sha256_text': fn(('s', None, PO)),
        'sha256_file': fn(('p', None, PO)),
        'sha256_canonical': fn(('obj', None, PO)),
        'fullsync': fn(('fd', None, PO)),
        'write_json_atomic': fn(('path', None, PO), ('obj', None, PO),
                                ('durable', 'True', KW)),
        'append_line_durable': fn(('fd', None, PO), ('line', None, PO),
                                  ('durable', None, KW)),
        'hardware_info': fn(), 'package_versions': fn(), 'boottime_hash': fn(),
        'process_rss_bytes': fn(('pattern', None, PO)),
        'build_freeze_bundle': fn(('parts', None, PO)),
        'freeze_bundle_sha256': fn(('bundle', None, PO)),
        'harness_file_hashes': fn(),
        'rule_block_sha256': fn(('config', None, PO)),
        'LabError': CONST, 'FreezeIncomplete': CONST, 'FrozenMismatch': CONST,
        'UntokenizablePath': CONST, 'WriteOnceViolation': CONST, 'TornWrite': CONST,
        'ChainError': CONST, 'SchemaError': CONST, 'SpoolError': CONST,
        'EnclosureError': CONST, 'MonitorError': CONST, 'ReceiptMismatch': CONST,
        'ServerIdentityError': CONST, 'PreflightError': CONST, 'VerifyFailure': CONST,
        'AbortTrial': CONST, 'PauseTrial': CONST,
    },
    'lab_eventlog': {
        'CHAIN_DOMAIN': CONST, 'SEGMENT_FMT': CONST, 'EVENT_SCHEMA': CONST,
        'Event': fields('seq', 'type', 't_wall_ns', 't_mono_ns', 'inv', 'chain', 'prev',
                        'body', 'h'),
        'genesis_prev': fn(('anchor_value', None, PO), ('chain_id', None, PO)),
        'event_hash': fn(('ev', None, PO)),
        'EventLog.__init__': fn(('self', None, PO), ('events_dir', None, PO),
                                ('chain_id', None, PO),
                                ('freeze_bundle_sha256', None, PO), ('inv', None, PO),
                                ('create', 'False', KW)),
        'EventLog.append': fn(('self', None, PO), ('etype', None, PO), ('body', None, PO),
                              ('durable', 'False', KW)),
        'EventLog.close_segment': fn(('self', None, PO), ('anchor_body', None, KW)),
        'EventLog.close': fn(('self', None, PO)),
        'TornRegion': fields('segment', 'offset', 'length', 'sha256', 'is_event_prefix'),
        'ChainRead': fields('events', 'torn', 'segments', 'segment_bytes',
                            'segment_sha256'),
        'read_chain': fn(('events_dir', None, PO), ('chain_id', None, PO),
                         ('freeze_bundle_sha256', None, PO)),
        'validate_event': fn(('etype', None, PO), ('body', None, PO)),
        'FieldSpec': fields('kind', 'required', 'enum', 'item', 'fields', 'inner'),
    },
    'lab_verify_log': {
        'Finding': fields('check', 'severity', 'trial', 'seq', 'detail'),
        'VerifyReport': fields('trial', 'mode', 'verdict', 'findings', 'counts'),
        'VerifyReport.to_json': fn(('self', None, PO)),
        'verify_trial': fn(('trial', None, PO), ('freeze_bundle_sha256', None, PO),
                           ('mode', "'full'", KW), ('results_root', 'None', KW),
                           ('work_root', 'None', KW)),
        'verify_program': fn(('freeze_bundle_sha256', None, PO),
                             ('results_root', 'None', KW)),
        'main': fn(('argv', 'None', PO)),
    },
    'lab_reference_rule': {
        'RefLook': fields('trigger', 'n', 'sum_lower_h', 'sum_upper_h', 'sum_lower_s',
                          'sum_upper_s', 'radius', 'L_h', 'U_h', 'L_s', 'U_s', 'action'),
        'looks_from_chain': fn(('events', None, PO), ('cfg', None, PO),
                               ('trial', None, PO)),
        'shadow_step': fn(('events', None, PO), ('cfg', None, PO), ('trial', None, PO)),
        'decide_from_chain': fn(('events', None, PO), ('cfg', None, PO),
                                ('trial', None, PO)),
    },
    'lab_data': {
        'SOURCES': CONST,
        'Task': fields('uid', 'benchmark', 'stratum', 'prompt', 'entry_point',
                       'reference', 'test_imports', 'test_list', 'challenge_test_list',
                       'test'),
        'Exclusion': fields('uid', 'reason', 'detail_sha256'),
        'fetch_sources': fn(('dest', None, PO), ('offline', 'False', KW)),
        'build_candidate_tasks': fn(('raw', None, PO)),
        'sweep_references': fn(('tasks', None, PO), ('cfg', None, PO),
                               ('on_progress', 'None', KW)),
        'build_roster': fn(('tasks', None, PO), ('exclusions', None, PO),
                           ('cfg', None, PO)),
        'write_roster': fn(('roster', None, PO), ('path', None, PO)),
        'load_roster': fn(('path', None, PO)),
        'load_tasks_by_uid': fn(('roster', None, PO), ('sources_dir', None, PO)),
    },
    'lab_design': {
        'PairSlot': fields('pair', 'stratum', 'arrivals', 'uids'),
        'arrival_order': fn(('roster', None, PO), ('trial', None, PO),
                            ('design_seed_base', None, PO)),
        'write_order': fn(('order', None, PO), ('path', None, PO)),
        'load_order': fn(('path', None, PO)),
        'order_sha256': fn(('order', None, PO)),
        'assert_disjoint': fn(('orders', None, PO)),
    },
    'lab_coin': {
        'ORIENTATION': CONST,
        'Coin': fields('raw_hex', 'bit', 'source'),
        'draw': fn(),
        'assignment': fn(('pair', None, PO), ('coin', None, PO)),
        'draw_and_commit': fn(('log', None, PO), ('pair', None, PO)),
        'selftest_entropy': fn(('n', '10000', PO), ('lo', '4850', PO), ('hi', '5150', PO)),
    },
    'lab_enclosure': {
        'TIER_NAMES': CONST,
        'Enclosure': fields('lo', 'hi'),
        'Enclosure.narrows_to': fn(('self', None, PO), ('other', None, PO),
                                   ('tol', '1e-12', KW)),
        'Enclosure.contains': fn(('self', None, PO), ('x', None, PO),
                                 ('tol', '1e-12', KW)),
        'Enclosure.full': fn(),
        'EpisodeView': fields('arm', 'revealed', 'success', 'latency_s',
                              'completion_tokens', 'ell', 'tokens_known'),
        'PairEnclosure': fields('h', 's', 'collapsed', 'decisive_tier'),
        'tiers_from_config': fn(('cfg', None, PO)),
        'outcome_vector': fn(('view', None, PO), ('names', None, PO)),
        'final_scores': fn(('candidate', None, PO), ('incumbent', None, PO),
                           ('tiers', None, PO)),
        'certified_elapsed': fn(('call_stamps', None, PO)),
        'success_enclosure': fn(('candidate', None, PO), ('incumbent', None, PO)),
        'hierarchy_enclosure': fn(('candidate', None, PO), ('incumbent', None, PO),
                                  ('tiers', None, PO)),
        'pair_enclosure': fn(('candidate', None, PO), ('incumbent', None, PO),
                             ('tiers', None, PO)),
        'assert_monotone': fn(('old', None, PO), ('new', None, PO)),
    },
    'lab_monitor': {
        'MonitorConfig': fields('alpha_gate', 'rho', 'delta', 'n_min', 'n_max',
                                'clip_lo', 'clip_hi'),
        'MonitorConfig.from_config': fn(('cfg', None, PO), ('trial', None, PO)),
        'Band': fields('n', 'radius', 's_lower', 's_upper', 'lo', 'hi'),
        'band': fn(('n', None, PO), ('s_lower', None, PO), ('s_upper', None, PO),
                   ('mc', None, PO)),
        'MonitorState.__init__': fn(('self', None, PO), ('mc', None, PO)),
        'MonitorState.enroll': fn(('self', None, PO), ('pair', None, PO)),
        'MonitorState.update': fn(('self', None, PO), ('pair', None, PO),
                                  ('enc', None, PO)),
        'MonitorState.sums': fn(('self', None, PO)),
        'MonitorState.bands': fn(('self', None, PO)),
        'MonitorState.snapshot': fn(('self', None, PO)),
        'Decision': fields('kind', 'n', 'band_h', 'band_s', 'rule_id'),
        'decide': fn(('state', None, PO), ('mc', None, PO)),
        'replay': fn(('events', None, PO), ('cfg', None, PO), ('trial', None, PO)),
        'radius_table': fn(('ns', None, PO), ('mc', None, PO)),
    },
    'lab_client': {
        'Spool.__init__': fn(('self', None, PO), ('path', None, PO)),
        'Spool.write': fn(('self', None, PO), ('kind', None, PO), ('body', None, PO),
                          ('durable', 'True', KW)),
        'Spool.close': fn(('self', None, PO)),
        'GoldenReceipt': fields('props', 'generation_settings', 'mask',
                                'float_tolerance'),
        'LlamaClient.__init__': fn(
            ('self', None, PO), ('base_url', None, KW), ('alias', None, KW),
            ('sampling', None, KW), ('spool', None, KW), ('golden', None, KW),
            ('request_timeout_s', None, KW), ('max_connection_retries', None, KW),
            ('server_recovery_s', None, KW), ('arrival', None, KW), ('attempt', None, KW),
            ('trial', None, KW), ('worker_index', None, KW), ('session', 'None', KW)),
        'LlamaClient.chat': fn(('self', None, PO), ('messages', None, PO),
                               ('ctx', None, PO)),
        'ConnectionFailure': CONST, 'HttpError': CONST, 'MalformedResponse': CONST,
    },
    'lab_server': {
        'ServerSpec': fields('server_id', 'port', 'alias', 'gguf_path', 'gguf_bytes',
                             'gguf_sha256', 'llama_bin', 'llama_commit', 'args',
                             'log_path', 'n_slots', 'n_ctx'),
        'server_argv': fn(('spec', None, PO)),
        'start': fn(('spec', None, PO)),
        'probe': fn(('base_url', None, PO), ('timeout', '5.0', KW)),
        'health': fn(('base_url', None, PO), ('timeout', '5.0', KW)),
        'metrics': fn(('base_url', None, PO), ('timeout', '5.0', KW), ('tries', '3', KW)),
        'smoke': fn(('base_url', None, PO), ('spec', None, PO), ('golden', None, PO),
                    ('sampling', None, PO)),
        'stop': fn(('pid', None, PO), ('grace_s', '10.0', KW)),
        'restart': fn(('spec', None, PO), ('golden_props', None, PO)),
    },
    'lab_mock_server': {
        'make_server': fn(('scenario', None, PO), ('port', '0', KW)),
        'main': fn(('argv', 'None', PO)),
    },
    'lab_worker': {
        'Job': fields('trial', 'inv', 'arrival', 'attempt', 'pair', 'position', 'arm',
                      'workflow', 'task_uid', 'server', 'worker_index', 'sampling',
                      'limits', 'paths', 'assignment_seq', 'payload_sha256'),
        'canonical_job_payload': fn(('job', None, PO)),
        'run_job': fn(('job', None, PO), ('sandbox_lock_path', None, KW)),
        'main': fn(('argv', 'None', PO)),
    },
    # The host quiescence gate of protocol 5.7.  Not a section-3 module: this table is the
    # gate's own public contract, pinned here so that the orchestrator's two call sites and
    # the event-schema vocabularies cannot drift away from it silently.
    'lab_hostcheck': {
        'RUNNER_TOKENS': CONST, 'DETECTOR_LABELS': CONST, 'DEGRADED_CAUSES': CONST,
        'PROBE_RSS_FLOOR_BYTES': CONST, 'MAX_LSOF_PIDS': CONST,
        'METAL_COMPUTE_RE': CONST, 'METAL_DISPLAY_RE': CONST, 'METAL_NAME_RE': CONST,
        'HostNotQuiescent': CONST,
        'ProcRow': fields('pid', 'ppid', 'elapsed_s', 'rss_bytes', 'command'),
        'MetalProbe': fields('holders', 'compute', 'covered', 'failure'),
        'ScanResult': fields('findings', 'degraded', 'scanned', 'allowlisted'),
        'metal_context_pids': fn(('pids', None, PO), ('timeout_s', '30', KW)),
        'enumerate_foreign_consumers': fn(
            ('own_pids', 'None', PO), ('table_text', 'None', KW),
            ('metal_pids', 'None', KW), ('now', 'None', KW), ('accounts', 'None', KW),
            ('include_descendants', 'True', KW), ('rss_floor_bytes', '134217728', KW),
            ('max_probe_pids', '96', KW)),
        'preflight_host_quiescent': fn(('own_pids', 'None', PO), ('**kwargs', None, PO)),
        'soft_host_check': fn(('own_pids', 'None', PO), ('**kwargs', None, PO)),
        'degraded_causes': fn(('degraded', None, PO)),
        'chain_finding': fn(('finding', None, PO)),
        'chain_body': fn(('scan', None, PO)),
    },
    'lab_orchestrator': {
        'RunContext': fields('trial', 'inv', 'cfg', 'bundle_sha', 'paths', 'order',
                             'tasks', 'mc', 'servers', 'golden'),
        'preflight': fn(('ctx', None, PO)),
        'host_scan_is_required': fn(('cfg', None, PO)),
        'own_harness_pids': fn(('world', 'None', PO)),
        'host_quiescence_gate': fn(('ctx', None, PO)),
        'write_host_quiescence_refused': fn(('ctx', None, PO), ('exc', None, PO)),
        'run_trial': fn(('ctx', None, PO), ('resume', 'True', KW)),
        'step': fn(('state', None, PO), ('ctx', None, PO), ('world', None, PO)),
        'ResumePlan': fields('phase', 'next_pair', 'reenroll_pair', 'bound_assignments',
                             'orphan_reveals', 'orphan_rejections', 'interrupted',
                             'dispatch_after_resume', 'decision_seq',
                             'pending_decision_steps', 'monitor_prefix', 'findings'),
        'plan_resume': fn(('events', None, PO), ('spools', None, PO), ('order', None, PO),
                          ('cfg', None, PO)),
        'worktree_check': fn(('ctx', None, PO), ('world', None, PO)),
        'status_snapshot': fn(('ctx', None, PO), ('world', None, PO)),
        'main': fn(('argv', 'None', PO)),
    },
    'lab_anchor': {
        'AnchorRequest': fields('request_id', 'trial', 'anchor_seq', 'upto_seq', 'upto_h',
                                'segment_index', 'segment_bytes', 'segment_sha256',
                                'trigger', 'blocking', 'publish_segments'),
        'AnchorReceipt': fields('request_id', 'ok', 'commit', 'branch', 'pushed',
                                'comment_id', 'created_at', 'updated_at',
                                'receipt_sha256', 'error_class'),
        'write_anchor_file': fn(('paths', None, PO), ('req', None, PO)),
        'scan_for_identifiers': fn(('paths', None, PO), ('patterns', None, PO)),
        'commit_and_push': fn(('repo', None, PO), ('files', None, PO),
                              ('message_id', None, PO), ('expect_branch', None, KW),
                              ('expect_parent', None, KW), ('push', None, KW)),
        'post_comment': fn(('api', None, PO), ('issue', None, PO), ('body', None, PO),
                           ('token_env', None, PO)),
        'serve': fn(('paths', None, PO), ('cfg', None, PO), ('once', 'False', KW)),
        'main': fn(('argv', 'None', PO)),
    },
    'build_live_ab_results': {
        'build': fn(('trials', None, PO), ('bundle_sha', None, PO),
                    ('results_root', None, KW), ('work_root', None, KW),
                    ('out_dir', None, KW), ('mock', 'False', KW)),
        'main': fn(('argv', 'None', PO)),
    },
}


def _resolve(mod, dotted: str):
    obj = mod
    for part in dotted.split('.'):
        obj = getattr(obj, part)
    return obj


class SignatureTests(unittest.TestCase):
    """Every public name of ARCHITECTURE_FINAL.md section 3 exists with exactly the
    documented signature: the parameter names, their order, whether each is keyword-only,
    and the defaults."""

    deviations: list[str] = []

    def _check_callable(self, obj, spec, where: str, *, strict: bool) -> None:
        """The documented parameters must be present, in order, with the documented
        defaults and keyword-only-ness.  An EXTRA keyword-only parameter that carries a
        default still lets every documented call site work unchanged, so it is recorded
        as a deviation from section 3 rather than as a broken contract; anything else --
        a missing, renamed, reordered or re-defaulted parameter, or an extra required one
        -- is a failure."""
        sig = inspect.signature(obj)
        got = []
        for p in sig.parameters.values():
            if p.kind in (inspect.Parameter.VAR_POSITIONAL,
                          inspect.Parameter.VAR_KEYWORD):
                got.append((('*' if p.kind == inspect.Parameter.VAR_POSITIONAL else '**')
                            + p.name, None, False))
                continue
            default = None if p.default is inspect.Parameter.empty else repr(p.default)
            got.append((p.name, default, p.kind == inspect.Parameter.KEYWORD_ONLY))
        want = [tuple(x) for x in spec[1]]
        want_names = {n for n, _, _ in want}
        extra = [g for g in got if g[0] not in want_names]
        core = [g for g in got if g[0] in want_names]
        self.assertEqual(core, want, f'{where}: signature differs from '
                                     'ARCHITECTURE_FINAL.md section 3')
        bad_extra = [g for g in extra if not (g[2] and g[1] is not None)]
        self.assertEqual(bad_extra, [],
                         f'{where}: undocumented parameter(s) {bad_extra} that are not '
                         'keyword-only with a default')
        if extra:
            note = (f'{where}: extra keyword-only parameter(s) '
                    f'{[g[0] for g in extra]} beyond section 3')
            if strict:
                self.fail(note)
            if note not in SignatureTests.deviations:
                SignatureTests.deviations.append(note)

    def _check_module(self, name: str, table: dict, strict: bool) -> None:
        path = module_path(name)
        if not path.exists():
            if strict:
                self.fail(f'{name}.py is missing')
            self.skipTest(f'{name}.py has not landed yet')
        try:
            mod = importlib.import_module(name)
        except Exception as exc:                                  # pragma: no cover
            if strict:
                raise
            self.skipTest(f'{name} is not importable yet: {type(exc).__name__}: {exc}')
        for dotted, spec in sorted(table.items()):
            with self.subTest(name=f'{name}.{dotted}'):
                try:
                    obj = _resolve(mod, dotted)
                except AttributeError:
                    self.fail(f'{name}.{dotted} does not exist')
                if spec[0] == '#const':
                    self.assertIsNotNone(obj)
                elif spec[0] == '#fields':
                    if hasattr(obj, '__annotations__') and not inspect.isfunction(obj):
                        got = list(obj.__annotations__)
                        if hasattr(obj, '__dataclass_fields__'):
                            got = list(obj.__dataclass_fields__)
                    else:                                         # pragma: no cover
                        got = []
                    missing = [f for f in spec[1] if f not in got]
                    self.assertEqual(missing, [],
                                     f'{name}.{dotted} is missing fields {missing}')
                else:
                    self._check_callable(obj, spec, f'{name}.{dotted}', strict=strict)

    def test_g1_signatures(self) -> None:
        for name in G1_MODULES:
            with self.subTest(module=name):
                self._check_module(name, SIGNATURES[name], strict=True)

    def test_other_group_signatures(self) -> None:
        landed = []
        for name, table in sorted(SIGNATURES.items()):
            if name in G1_MODULES:
                continue
            path = module_path(name)
            if not path.exists():
                continue
            landed.append(name)
            with self.subTest(module=name):
                self._check_module(name, table, strict=False)
        print(f'\n[signature gate] other-group modules present: '
              f'{landed if landed else "none yet"}')
        for note in SignatureTests.deviations:
            print(f'[signature gate] DEVIATION from section 3: {note}')

    def test_every_module_of_the_matrix_is_covered_by_the_signature_table(self) -> None:
        self.assertEqual(sorted(SIGNATURES), sorted(MATRIX))


if __name__ == '__main__':                                        # pragma: no cover
    unittest.main()
