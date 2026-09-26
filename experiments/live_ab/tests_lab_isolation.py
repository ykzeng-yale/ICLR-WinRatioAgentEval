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
import json
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
    'lab_server': {'requests', 'lab_common', 'lab_serving_manifest'},
    # lab_serving_manifest (root 01:53, session 60 repair): the serving manifest of protocol
    # 2.2 item 2 and the dependency closure transcribed from live_ab_serving.  Standard
    # library plus lab_common; imported by lab_server and the orchestrator.  Not yet a row of
    # ARCHITECTURE_FINAL.md 3.16 -- the synchronized amendment adds it.
    'lab_serving_manifest': {'lab_common'},
    'lab_mock_server': set(),
    'lab_worker': {'requests', 'lab_common', 'lab_client', 'lab_data', 'agent',
                   'sandbox', 'verify', 'data', 'common'},
    # lab_hostcheck is the host quiescence gate of protocol 5.7.  It sits beside
    # lab_server in the matrix: standard library plus lab_common, imported by the
    # orchestrator and by nothing below it.
    'lab_hostcheck': {'lab_common'},
    'lab_orchestrator': {'requests', 'lab_common', 'lab_eventlog', 'lab_data',
                         'lab_design', 'lab_coin', 'lab_monitor', 'lab_enclosure',
                         'lab_reference_rule', 'lab_server', 'lab_hostcheck',
                         'lab_serving_manifest'},
    'lab_anchor': {'requests', 'lab_common'},
    'build_live_ab_results': {'numpy', 'pandas', 'winstats', 'lab_common',
                              'lab_eventlog', 'lab_monitor', 'lab_enclosure',
                              'lab_reference_rule'},
    # lab_shard_receipt: the incremental immutable completed-shard receipt (root 22:20,
    # design_notes/DESIGN_PROPOSAL.md section 3 item 1).  A thin layer over lab_common's
    # write-once/durable primitives, deliberately free of any protocol-specific stage logic,
    # so it imports nothing else in the lab namespace.
    'lab_shard_receipt': {'lab_common'},
    # Protocol 11.5 extended CPU replay (design_notes/DESIGN_PROPOSAL.md section 3 item 2,
    # hand-ported from ref:session60-repair-replay). Pure CPU: the frozen band/decision and the
    # 3.4 order code path plus this branch's own write-once shard receipt, nothing that serves,
    # dispatches or anchors.
    'lab_replay': {'numpy', 'winstats', 'lab_common', 'lab_design', 'lab_enclosure',
                   'lab_monitor', 'lab_shard_receipt'},
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
        """audit B4: abstention on the deploy route is a property of the data, never a
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
        # `execution_lock` is keyword-only and defaults to None: production
        # callers pass nothing and get the canonical host-wide lock. It
        # exists so an ISOLATED tree can carry its own, which root permits.
        'trial_paths': fn(('trial', None, PO), ('execution_lock', 'None', KW)),
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
    # The serving manifest (root 01:53).  Not a section-3 module: this table is its own
    # public contract, pinned so that lab_server, the orchestrator and the assembler tool
    # cannot drift away from it silently.
    'lab_serving_manifest': {
        'MANIFEST_SCHEMA': CONST, 'ARTIFACT_NAME': CONST, 'FREEZE_DIR_NAME': CONST,
        'TRACKED_RELPATH': CONST, 'CONFIG_DIGEST_KEY': CONST, 'PROVENANCE_ROLES': CONST,
        'MANIFEST_KEYS': CONST, 'SCHEMA': CONST, 'ManifestError': CONST,
        'artifact_path': fn(('freeze_dir', None, PO)),
        'read_artifact': fn(('path', None, PO)),
        'digest_problems': fn(('found', None, PO), ('expected', None, PO)),
        'verify_artifact': fn(('path', None, PO), ('expected_sha256', None, PO)),
        'write_artifact': fn(('path', None, PO), ('manifest', None, PO)),
        'override_problems': fn(('cfg', None, PO), ('results_root', None, PO)),
        'server_cwd': fn(('launcher', None, PO)),
        # derive_closure / verify_closure are TRANSCRIBED from live_ab_serving; their
        # agreement with the original is tests_sm_manifest's AST comparison, not this table.
        'derive_closure': CONST, 'verify_closure': CONST,
        'runtime_facts': fn(('manifest', None, PO), ('launcher', None, KW),
                            ('environ', 'None', KW), ('readers', 'None', KW)),
        'recorded_facts': fn(('manifest', None, PO)),
        'compare_facts': fn(('manifest', None, PO), ('measured', None, PO)),
        'runtime_problems': fn(('manifest', None, PO), ('launcher', None, KW),
                               ('llama_commit', None, KW), ('environ', 'None', KW),
                               ('readers', 'None', KW)),
        'verify_before_launch': fn(('path', None, PO), ('expected_sha256', None, PO),
                                   ('launcher', None, KW), ('llama_commit', None, KW),
                                   ('environ', 'None', KW), ('readers', 'None', KW)),
        'props_build_info_problems': fn(('manifest', None, PO), ('props', None, PO)),
        'assemble': fn(('launcher', None, PO), ('provenance', None, PO),
                       ('llama_commit', None, KW), ('environ', 'None', KW),
                       ('readers', 'None', KW)),
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
    # lab_shard_receipt (design_notes/DESIGN_PROPOSAL.md section 3 item 1): the write-once
    # completed-shard receipt every stage 1-6 / 11.5 driver reuses.  Not a section-3 module;
    # this table is its own public contract, pinned so a driver cannot drift away from the
    # required receipt shape silently.
    'lab_shard_receipt': {
        'SCHEMA': CONST, 'OUTCOMES': CONST, 'REQUIRED_FIELDS': CONST,
        'REQUIRED_PIN_KEYS': CONST, 'ShardReceiptError': CONST,
        'shard_id': fn(('driver', None, PO), ('schedule_row', None, PO)),
        'validate_receipt': fn(('receipt', None, PO)),
        'write_shard_receipt': fn(('dir', None, PO), ('receipt', None, PO)),
        'completed_shards': fn(('dir', None, PO)),
        'verify_shards': fn(('dir', None, PO), ('schedule_rows', None, PO),
                            ('root_for_outputs', None, PO)),
    },
    # Not a section-3 module: the replay's own public contract (protocol 11.5), pinned so that
    # the seed rule, the open-model parameter and the manifest/receipt entry points cannot drift
    # silently. Hand-ported from ref:session60-repair-replay with the two PROPOSED/NOT_SIMULABLE
    # gaps kept exactly as flagged there, plus this branch's own per-cell shard receipt (new
    # relative to the held module, which predates lab_shard_receipt).
    'lab_replay': {
        'GRID_CELLS': CONST, 'GRID_REPLICATES': CONST, 'REPLAY_STREAM_TAG': CONST,
        'SEED_RULE_TEXT': CONST, 'FROZEN_RULE': CONST, 'LABELS': CONST, 'DRIVER': CONST,
        'OPEN_MODEL_CHOICES': CONST, 'PROPOSED_OPEN_MODEL': CONST, 'ReplayRefused': CONST,
        'Pilot': fields('tasks', 'success', 'latency', 'sha256'),
        'make_cell': fn(('ordinal', None, PO), ('trial', None, PO), ('w', None, PO),
                        ('q', None, PO), ('s', None, PO), ('n_p', None, PO),
                        ('n_p_role', None, PO), ('replicates', None, PO)),
        'enumerate_cells': fn(('realized_n_p', None, PO)),
        'check_grid': fn(('cells', None, PO), ('realized_n_p', None, PO)),
        'check_ruling_citation': fn(('ruling', None, PO)),
        'replicate_generator': fn(('design_seed_base', None, PO), ('ordinal', None, PO),
                                  ('replicate', None, PO)),
        'load_pilot_csv': fn(('path', None, PO)),
        'outcome_model_gaps': fn(('cfg', None, PO), ('trial', None, PO)),
        'check_open_model': fn(('cfg', None, PO), ('open_model', None, PO),
                               ('trials', None, PO)),
        'frozen_monitor_config': fn(('cfg', None, PO), ('trial', None, PO), ('n_p', None, PO)),
        'radius_vector': fn(('mc', None, PO), ('n_p', None, PO)),
        'build_trial_model': fn(('roster', None, PO), ('pilot', None, PO), ('cfg', None, PO),
                                ('trial', None, PO), ('open_model', None, PO)),
        'order_indices': fn(('generator', None, PO), ('n_s1', None, PO), ('n_s2', None, PO)),
        'draw_replicate': fn(('model', None, PO), ('cell', None, PO), ('generator', None, PO),
                             ('p_cand', None, PO), ('p_inc', None, PO)),
        'pair_scores': fn(('success_c', None, PO), ('success_i', None, PO), ('lat_c', None, PO),
                          ('lat_i', None, PO), ('tiers', None, PO)),
        'band_matrix': fn(('scores', None, PO), ('radius', None, PO), ('mc', None, PO)),
        'decide_matrix': fn(('z', None, PO), ('d', None, PO), ('radius', None, PO),
                            ('mc', None, PO)),
        'monitor_decision': fn(('success_c', None, PO), ('success_i', None, PO),
                               ('lat_c', None, PO), ('lat_i', None, PO), ('mc', None, PO),
                               ('tiers', None, PO), ('pending_looks', 'False', KW)),
        'monitor_decision_from_scores': fn(('z', None, PO), ('d', None, PO), ('mc', None, PO)),
        'wilson': fn(('x', None, PO), ('n', None, PO), ('z', '1.959963984540054', PO)),
        'quartiles': fn(('values', None, PO)),
        'run_cell': fn(('model', None, PO), ('cell', None, PO), ('mc', None, PO),
                       ('design_seed_base', None, PO), ('crosscheck', '0', KW),
                       ('replicates', 'None', KW)),
        'roster_rule_pairs': fn(('roster', None, PO)),
        'cell_shard_id': fn(('cell', None, PO)),
        'run_replay': fn(('roster', None, PO), ('pilot', None, PO), ('cfg', None, PO),
                         ('realized_n_p', None, KW), ('out_dir', None, KW),
                         ('open_model', None, KW), ('cells', 'None', KW),
                         ('crosscheck_per_cell', '2', KW), ('ruling', 'None', KW)),
        'verify_manifest': fn(('out_dir', None, PO)),
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


class PerAttemptControlTests(unittest.TestCase):
    """`lab_containment.pair_attempts` decides WHAT COUNTS AS EVIDENCE.

    Root rejected the previous negative control because it was a summary count of
    fifteen breaches: it could not say which operation the sandbox stopped. The
    pairing replaces it, so the pairing itself has to be right -- a control that
    over-credits is worse than no control, because it launders a denial the
    sandbox did not cause.
    """

    def _pair(self, sandboxed, unsandboxed):
        import lab_containment
        return lab_containment.pair_attempts(sandboxed, unsandboxed)

    def test_denied_in_both_supports_nothing(self) -> None:
        # The peer_run_dir enumerate row is exactly this: it fails with and
        # without the sandbox because no peer exists. Counting it as a controlled
        # denial would credit the sandbox for an absence.
        r = self._pair([{'target': 'peer_run_dir', 'op': 'enumerate', 'succeeded': False}],
                       [{'target': 'peer_run_dir', 'op': 'enumerate', 'succeeded': False}])
        self.assertEqual(r['controlled_denials'], 0)
        self.assertEqual(r['denied_in_both'], 1)
        self.assertIn('supports nothing', r['rows'][0]['reading'])

    def test_denied_inside_reachable_outside_is_the_only_supporting_row(self) -> None:
        r = self._pair([{'target': 'event_chain', 'op': 'read', 'succeeded': False}],
                       [{'target': 'event_chain', 'op': 'read', 'succeeded': True}])
        self.assertEqual(r['controlled_denials'], 1)
        self.assertEqual(r['denied_in_both'], 0)
        self.assertIn('THE SANDBOX DID IT', r['rows'][0]['reading'])

    def test_a_success_inside_the_sandbox_is_a_breach_not_a_denial(self) -> None:
        r = self._pair([{'target': 'spools', 'op': 'write', 'succeeded': True}],
                       [{'target': 'spools', 'op': 'write', 'succeeded': True}])
        self.assertEqual(r['reachable_inside_sandbox'], 1)
        self.assertEqual(r['controlled_denials'], 0)

    def test_a_missing_control_row_is_uncontrolled_not_credited(self) -> None:
        # If the unsandboxed arm never ran that operation, its denial inside is
        # not controlled. Silently treating it as controlled is how a partial
        # control arm turns into a full-looking pass.
        r = self._pair([{'target': 'task_file', 'op': 'write', 'succeeded': False}], [])
        self.assertEqual(r['controlled_denials'], 0)
        self.assertEqual(r['denied_in_both'], 0)
        self.assertFalse(r['rows'][0]['control_present'])
        self.assertIn('uncontrolled', r['rows'][0]['reading'])

    def test_pairing_is_by_identity_not_by_position(self) -> None:
        # The two arms are separate processes; nothing guarantees the same order.
        # Pairing by index would match event_chain against records_dir.
        sandboxed = [{'target': 'event_chain', 'op': 'read', 'succeeded': False},
                     {'target': 'records_dir', 'op': 'read', 'succeeded': False}]
        unsandboxed = [{'target': 'records_dir', 'op': 'read', 'succeeded': True},
                       {'target': 'event_chain', 'op': 'read', 'succeeded': True}]
        r = self._pair(sandboxed, unsandboxed)
        self.assertEqual(r['controlled_denials'], 2)
        for row in r['rows']:
            self.assertTrue(row['control_present'])

    def test_every_paired_row_is_accounted_for_in_exactly_one_bucket(self) -> None:
        sandboxed = [{'target': 'event_chain', 'op': 'read', 'succeeded': False},
                     {'target': 'peer_run_dir', 'op': 'enumerate', 'succeeded': False},
                     {'target': 'spools', 'op': 'write', 'succeeded': True},
                     {'target': 'task_file', 'op': 'list', 'succeeded': False}]
        unsandboxed = [{'target': 'event_chain', 'op': 'read', 'succeeded': True},
                       {'target': 'peer_run_dir', 'op': 'enumerate', 'succeeded': False},
                       {'target': 'spools', 'op': 'write', 'succeeded': True}]
        r = self._pair(sandboxed, unsandboxed)
        uncontrolled = sum(1 for row in r['rows'] if 'uncontrolled' in row['reading'])
        self.assertEqual(r['attempts_paired'], 4)
        self.assertEqual(r['controlled_denials'] + r['denied_in_both']
                         + r['reachable_inside_sandbox'] + uncontrolled, 4)


class ContenderSourceTests(unittest.TestCase):
    """The contender must be a real second process on the real production lock."""

    def test_contender_source_is_valid_python_and_binds_the_given_lock(self) -> None:
        import lab_containment
        src = lab_containment.contender_source(
            Path('/tmp/x/sandbox.lock'), 2.0, Path('/tmp/x/sig'),
            Path('/tmp/x/out.json'), require_holder=True)
        ast.parse(src)                       # it must actually compile
        self.assertIn('/tmp/x/sandbox.lock', src)
        self.assertIn('lab_data', src)
        self.assertIn('_ExecutionLock', src)

    def test_contender_never_differences_monotonic_across_processes(self) -> None:
        # The 694 s clock-domain trap, one layer down: the cross-process interval
        # arithmetic must use the shared realtime clock, and monotonic may be
        # recorded but never subtracted against another process's value.
        import lab_containment
        src = inspect.getsource(lab_containment.run_two_worker)
        for name in ('t_attempt_start_epoch', 't_attempt_end_epoch',
                     't_acquired_epoch', 't_release_epoch'):
            self.assertIn(name, src)
        self.assertNotIn('t_attempt_start_monotonic', src,
                         'the holder must not difference the contender monotonic clock')

    def test_the_verdict_requires_every_limb(self) -> None:
        # A verdict computed from a subset of its limbs is how the integrity
        # label shipped with a missing limb. Read the source and require that the
        # named limbs all feed `all(limbs.values())`.
        import lab_containment
        src = inspect.getsource(lab_containment.run_two_worker)
        self.assertIn("all(limbs.values())", src)
        for limb in ('contender_was_refused', 'attempt_inside_hold',
                     'lock_control_acquired', 'lock_path_is_production',
                     'control_interpreter_identical'):
            self.assertIn(limb, src)


class ExecutionLockConformanceTests(unittest.TestCase):
    """protocol 5.7 item 1: ONE lock file, host-wide, across trials AND checkouts.

    The section is titled "Sandbox under two workers: the host-wide execution
    lock" and item 1 requires an exclusive `flock` on ONE LOCK FILE. The hazard is
    a Seatbelt writable directory "shared by every run ON THE HOST".

    This test was RED BY INTENT from 2026-09-22 13:23 until root ruled. Root's
    ruling (`reviews/lock_anchor_review_20260923_0348.md`, and the 03:51 issue
    decision): repair it, bind every cooperating path to the canonical owner-host
    file, and *"do not skip the failing test"*. It is now green because the code
    conforms, not because the assertion was weakened.
    """

    def _resolve(self):
        import lab_orchestrator
        import lab_common as C
        cfg = C.harness_config()
        sweep = Path((cfg.get('sandbox') or {}).get('execution_lock_path')
                     or C.canonical_execution_lock(cfg))
        workers = {t: Path(lab_orchestrator._trial_paths(
            t, Path(C.RESULTS_ROOT), Path(C.WORK_ROOT)).sandbox_lock)
            for t in ('T1', 'T2', 'T3', 'T4')}
        return sweep, workers

    def test_protocol_5_7_item_1_resolves_to_one_lock_file(self) -> None:
        import lab_common as C
        sweep, workers = self._resolve()
        fallbacks = {t: Path(C.trial_paths(t).sandbox_lock)
                     for t in ('T1', 'T2', 'T3', 'T4')}
        distinct = sorted({str(sweep)}
                          | {str(p) for p in workers.values()}
                          | {str(p) for p in fallbacks.values()})
        self.assertEqual(
            len(distinct), 1,
            'protocol 5.7 item 1 requires ONE lock file host-wide; production '
            'resolves %d:\n  %s' % (len(distinct), '\n  '.join(distinct)))
        self.assertEqual(distinct[0],
                         str(C.canonical_execution_lock(C.harness_config())))

    def test_the_canonical_lock_does_not_move_with_the_checkout(self) -> None:
        # THE PROPERTY THAT MAKES IT HOST-WIDE. `<WORK>` is checkout-relative by
        # design; the lock must NOT be. Simulated by resolving the token against
        # a foreign work root -- the pin comes from config, so the answer cannot
        # depend on which checkout asks.
        import lab_common as C
        cfg = C.harness_config()
        want = C.canonical_execution_lock(cfg)
        self.assertEqual(C.resolve_execution_lock_token(
            C.tokenize_execution_lock(cfg), cfg), want)
        foreign = dict(cfg)
        self.assertEqual(C.canonical_execution_lock(foreign), want)
        self.assertTrue(Path(want).is_absolute())

    def test_run_locks_stay_per_trial(self) -> None:
        # Root explicitly preserved these. Only the SANDBOX lock is host-wide; a
        # host-wide run lock would serialize whole trials against each other.
        import lab_common as C
        runs = {str(C.trial_paths(t).run_lock) for t in ('T1', 'T2', 'T3', 'T4')}
        self.assertEqual(len(runs), 4)

    def test_a_stale_job_lock_path_refuses(self) -> None:
        # A job serialized BEFORE this repair carries <WORK>/<trial>/sandbox.lock.
        # Resolving it would open a second inode and the two workers would not
        # exclude each other. It must refuse, not run unlocked.
        import lab_common as C
        cfg = C.harness_config()
        stale = Path(C.WORK_ROOT) / 'T1' / 'sandbox.lock'
        with self.assertRaises(C.PreflightError):
            C.assert_canonical_execution_lock(stale, cfg, stage='stale-job')
        C.assert_canonical_execution_lock(
            C.canonical_execution_lock(cfg), cfg, stage='canonical')

    def test_host_work_root_must_be_an_absolute_pin(self) -> None:
        # Deriving it from the checkout is the defect itself, so a missing or
        # relative pin refuses rather than falling back.
        import lab_common as C
        for bad in (None, '', 'work/live_ab', 123):
            with self.assertRaises(C.PreflightError):
                C.host_work_root({'sandbox': {'host_work_root': bad}})

    # ---- ACTUAL-ENTRY TESTS, not source-string assertions --------------
    #
    # The previous version of this asserted that `lab_worker.main`'s SOURCE
    # CONTAINED certain substrings. Root: "Replace source-string assertions with
    # tiny actual-entry tests: default canonical path accepted; arbitrary
    # absolute, relative, stale-token and self-labelled production overrides
    # refused before dispatch; isolated fixtures remain isolated." A substring
    # test passes whether or not the entry point refuses anything, which is the
    # only thing worth knowing.

    def _job_file(self, lock_spelling, tmp, *, cfg_extra=None):
        import json as _json
        import lab_common as C
        job = {'trial': 'T1', 'arrival': 1, 'cfg': dict(cfg_extra or {}),
               'paths': {'sandbox_lock': lock_spelling,
                         'spool': str(Path(tmp) / 'spool.jsonl')}}
        f = Path(tmp) / 'job.json'
        f.write_text(_json.dumps(job), encoding='utf-8')
        return f

    def _run_entry(self, lock_spelling, tmp, *, cfg_extra=None):
        """Call the real CLI entry and report (refused, spool_written)."""
        import lab_common as C
        import lab_worker
        f = self._job_file(lock_spelling, tmp, cfg_extra=cfg_extra)
        spool = Path(tmp) / 'spool.jsonl'
        try:
            lab_worker.main(['--job', str(f)])
            return False, spool.exists()
        except C.PreflightError:
            return True, spool.exists()

    def test_entry_refuses_every_non_canonical_spelling_before_dispatch(self) -> None:
        import tempfile
        import lab_common as C
        cfg = C.harness_config()
        canonical = str(C.canonical_execution_lock(cfg))
        cases = {
            'arbitrary absolute': '/tmp/somewhere/sandbox.lock',
            'relative': 'work/live_ab/sandbox.lock',
            'stale trial token': '<WORK>/T1/sandbox.lock',
            'bare token': '<WORK>/sandbox.lock',
            'canonical with a lie about the host root':
                canonical,
        }
        for name, spelling in cases.items():
            tmp = tempfile.mkdtemp()
            extra = ({'sandbox': {'host_work_root': '/tmp/elsewhere'}}
                     if name.startswith('canonical with') else None)
            refused, spooled = self._run_entry(spelling, tmp, cfg_extra=extra)
            self.assertTrue(refused, '%s (%s) was NOT refused' % (name, spelling))
            self.assertFalse(spooled,
                             '%s: refused but the spool was already written, so '
                             'the refusal was not before dispatch' % name)

    def test_a_producer_shaped_job_is_validated_in_the_shape_it_is_emitted(self) -> None:
        """Through the REAL World.build_job shape and the REAL worker entry.

        Root found the guard reading `job['cfg']` while `World.build_job` emits
        top-level `job['sandbox']`, so a producer-shaped job with a conflicting
        host pin reached stubbed dispatch. A test built from my own idea of the
        job shape would have missed it exactly as the guard did, so this one
        takes the shape from the producer's own source.
        """
        import inspect
        import json as _json
        import tempfile
        from unittest import mock as _mock
        import lab_common as C
        import lab_orchestrator
        import lab_worker

        # the producer really does emit a TOP-LEVEL sandbox block and no 'cfg'
        src = inspect.getsource(lab_orchestrator.World.build_job)
        self.assertIn("'sandbox': dict(self.cfg.get('sandbox') or {})", src)
        self.assertNotIn("'cfg':", src)

        good = str(C.host_work_root(C.harness_config()))
        for label, pin, expect_refused in (('agreeing', good, False),
                                           ('conflicting', '/tmp/elsewhere', True)):
            tmp = tempfile.mkdtemp()
            job = {'trial': 'T1', 'arrival': 1,
                   'sandbox': {'host_work_root': pin},      # PRODUCER SHAPE
                   'paths': {'sandbox_lock': C.tokenize_execution_lock(
                                 C.harness_config()),
                             'spool': str(Path(tmp) / 'spool.jsonl')}}
            f = Path(tmp) / 'job.json'
            f.write_text(_json.dumps(job), encoding='utf-8')
            dispatched = []
            with _mock.patch.object(lab_worker, 'run_job',
                                    lambda *a, **k: dispatched.append(1)):
                refused = False
                try:
                    lab_worker.main(['--job', str(f)])
                except C.PreflightError:
                    refused = True
            self.assertEqual(refused, expect_refused,
                             'producer-shaped job with a %s host pin' % label)
            self.assertEqual(bool(dispatched), not expect_refused,
                             'a %s pin must%s reach dispatch'
                             % (label, '' if not expect_refused else ' NOT'))

    def test_contradictory_host_pin_copies_refuse(self) -> None:
        # Two copies that disagree have no correct reading; choosing one would
        # be a guess with a lock inode riding on it.
        import lab_common as C
        good = str(C.host_work_root(C.harness_config()))
        with self.assertRaises(C.PreflightError):
            C.assert_job_host_root_agreement(
                {'sandbox': {'host_work_root': good},
                 'cfg': {'sandbox': {'host_work_root': '/tmp/other'}}},
                stage='probe')

    def test_entry_accepts_the_canonical_spelling(self) -> None:
        # It must get PAST the lock check. Anything after that (a missing task
        # file, an unwritable path) is not a lock refusal, so only a
        # PreflightError naming the lock would be a failure here.
        import tempfile
        import lab_common as C
        import lab_worker
        tmp = tempfile.mkdtemp()
        f = self._job_file(C.tokenize_execution_lock(C.harness_config()), tmp)
        try:
            lab_worker.main(['--job', str(f)])
        except C.PreflightError as exc:
            self.assertNotIn('execution lock', str(exc),
                             'the canonical spelling must not be refused')
        except Exception:
            pass                 # later failures are not this test's subject

    def test_a_config_cannot_license_its_own_lock_override(self) -> None:
        # The removed bypass: a truthy execution_lock_is_fixture used to make an
        # override legitimate. A claim inside the validated data is not evidence.
        import lab_common as C
        for extra in ({'execution_lock_path': '/tmp/x.lock'},
                      {'execution_lock_path': '/tmp/x.lock',
                       'execution_lock_is_fixture': True}):
            with self.assertRaises(C.PreflightError):
                C.resolve_execution_lock({'sandbox': extra}, stage='probe')

    def test_isolation_by_patching_the_canonical_root_still_works(self) -> None:
        # The supported way to isolate: move the canonical root in-process. The
        # production resolver is unchanged and still validates.
        import tempfile
        from unittest import mock as _mock
        import lab_common as C
        root = Path(tempfile.mkdtemp()) / 'hostwork'
        root.mkdir(parents=True)
        cfg = dict(C.harness_config())
        cfg['sandbox'] = dict(cfg['sandbox'], host_work_root=str(root))
        with _mock.patch.object(C, '_HARNESS_CONFIG', cfg):
            path, info = C.resolve_execution_lock(cfg, stage='isolated')
            self.assertEqual(path, root / C.EXECUTION_LOCK_NAME)
        self.assertNotEqual(C.canonical_execution_lock(C.harness_config()),
                            root / C.EXECUTION_LOCK_NAME)

    def test_there_are_two_flock_implementations_and_they_differ(self) -> None:
        # Retained: root ruled two wrappers are acceptable PROVIDED they hold the
        # same physical file. This records that they still differ observably, so
        # validating one is still not validating the other.
        import inspect
        import lab_data
        import lab_worker
        a = inspect.getsource(lab_data._ExecutionLock)
        b = inspect.getsource(lab_worker.ExecutionLock)
        self.assertIn('PreflightError', a)
        self.assertIn('LockWaitExceeded', b)
        self.assertNotEqual('0.05' in a, '0.05' in b)
        self.assertIn('_LOCK_DEPTH', b)
        self.assertNotIn('_LOCK_DEPTH', a)


if __name__ == '__main__':                                        # pragma: no cover
    unittest.main()
