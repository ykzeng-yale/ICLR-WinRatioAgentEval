"""Witnesses for the synchronized pre-outcome amendment v2 (repair_amendment_v2.py).

Started from the withdrawn predecessor's witnesses (branch session60/repair-amend,
tests_repair_amendment.py at ff152e9), copied and corrected; that branch is not edited.

HOW EVERY DRIVE RUNS
  The PRE-amendment blobs (`git show b049307:<path>`, read-only, once per class) are copied
  into a fresh temporary directory. A fresh instance of the tool is loaded, and its paths REPO,
  CONFIG, ARCH, PROTO and CELLS are re-pointed at the copies (the harness asserts each lies
  under the temporary directory), so the four documents, the serving-manifest artifact and the
  receipt are written there only. The tool's `subprocess` (git rev-parse / show / merge-base) is
  replaced in that instance only, `lab_common.harness_file_hashes` is stubbed, and the pinned
  roster sources are replaced by a small SYNTHETIC source set. The serving manifest is the REAL
  one: the tool assembles it from the durable build of the main checkout (read only: otool/nm
  metadata and file bytes; nothing is executed and no server is started). To keep the suite
  fast, `manifest_checks` -- whose real result is computed ONCE per class by the real function
  -- is served from that result (deep-copied) unless a test asks for the real call. Every drive
  compares the digests of this checkout's real documents and results/live_ab listing before and
  after.

WHAT A REFUSAL WITNESS SHOWS (the predecessor's review finding 5): two properties separately.
  * AGGREGATION (GateTests): every refusal of main() goes through gate(name, checks). The gates
    and their checks are pinned (GATES); for EVERY (gate, check), a drive on the pristine
    pre-images sets that one check False at gate() and main() must refuse.
  * LIVENESS (the LIVENESS table): which REAL input makes each check False; `test_isolated_*`
    make ONLY that check False. Checks that no real input can make alone False (implied by
    another check) or at all say so.

ProseTests: the prose says what the code of the EB1+EB5 subset performs -- every closed name the
prose uses (restart-cap cases, receipt reject reasons, worker states, start stages, abort
reasons, the preflight code, the artifact path, the chains each event may be on, the first-start
abort map, the builder labels) is read back from the code; and root's three cases are there, the
predecessor's withdrawn wording is not (negative control: the predecessor's own texts fail).
VerifierTests: the independent verifier. RealManifestTests: the committed artifact against the
real durable build, as seen from the main checkout -- a dry check, no server started -- and a
mutated copy refused. AssemblerRepoRootTests: the pinned repo-root parameter of
assemble_serving_manifest.py.

SCOPE: needs the git history (b049307, 48f4d70, the predecessor's commits) and, for the drives,
the durable build in the main checkout; without them the classes are skipped and the skip says
why. Nothing here runs a model, a server, a build or a network request.
"""

from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'repair_amendment_v2.py'
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json'}
PRE_REV = 'b049307ff62153a054f61b6179291ba987de2ba1'
REVIEWED = {'CONFIG': 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824',
            'ARCH': '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab',
            'PROTO': '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b',
            'CELLS': '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'}
#: the delivered documents, and the delivered cells.json with the new successor's recorded_utc
#: replaced by RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED = {'CONFIG': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
             'ARCH': 'e7ea9c0fb7a28c6bdb47bb4085dcddba41144bd134d7b3a9b026ad7c9a30c86a',
             'PROTO': '6c0ebf2faa7515ff27f01188d9f1e487c928c63373f451dea51f06a8cdacaab9'}
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    '8e6ab530f77116c522439f1312683bcc6569e30b70a8c47e0758f7690904706d')
#: the serving manifest assembled as seen from the main checkout (canonical digest)
SERVING_MANIFEST_SHA256 = '1edea9b072b9c87ed9d4a0b4d7ad69b8e768d0a10d09d99efc4e64324ad68b0c'
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
SMOKE = ('mbpp_full/39', 'mbpp_full/122', 'mbpp_full/522', 'mbpp_full/547',
         'mbpp_full/869', 'mbpp_full/966')
RECEIPT_GLOB = 'REPAIR_AMENDMENT_V2_RECEIPT_*.json'
MAIN = '/Users/yukangzengcmac/ICLR-WinRatioAgentEvals'
MAIN_LAUNCHER = Path(MAIN) / 'work/llama.cpp-build/build/bin/llama-server'
ARTIFACT = 'results/live_ab/freeze/serving_manifest.json'
PRED_RECEIPTS = {
    'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json':
        '134961944cec6e83f2b27586cda3d1f42ba40b72',
    'results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_20260923_2242.json':
        'ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc'}
PRED_HEAD = 'ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc'

#: every gate of main() and the checks in each (the aggregation witness)
GATES = {
    'pins': ['config_is_the_reviewed_preimage', 'architecture_is_the_reviewed_preimage',
             'protocol_is_the_reviewed_preimage', 'cells_is_the_reviewed_preimage',
             'no_cr_byte', 'three_way_contract_before', 'rule_block_before_is_the_pin',
             'cells_round_trips', 'cells_original_pin_untouched',
             'cells_current_successor_is_the_prior_successor',
             'cells_successor_supersedes_the_original', 'cells_prior_successor_count'],
    'anchors': ['every_anchor_once', 'no_anchor_error', 'every_anchor_inside_its_section',
                'every_replacement_site_once_inside_its_fence', 'inserted_text_form'],
    'prompt': ['build_user_prompt_takes_the_non_mbpp_branch', 'shape_ok',
               'normalized_equal_to_no_source', 'max_jaccard_below_threshold',
               'max_jaccard_smoke_tasks_below_threshold', 'entry_point_defined_in_no_source',
               'sources_compared'],
    'prompts': ['every_prompt_passes', 'ids_are_oodp_1_to_4', 'distinct_among_themselves',
                'no_smoke_task_missing', 'fields_are_exactly'],
    'withdrawn_predecessor': ['first_receipt_is_the_pinned_bytes',
                              'correction_receipt_is_the_pinned_bytes',
                              'predecessor_not_merged_into_this_branch'],
    'main_checkout': ['is_the_pinned_root', 'root_definitions_hold', 'durable_launcher_present',
                      'provenance_files_equal_this_checkout',
                      'declaration_is_the_pinned_bytes_in_both', 'no_loader_environment'],
    'manifest': ['assembled', 'reverifies_at_once_from_the_main_checkout',
                 'assembly_is_deterministic', 'launcher_is_the_declared_launcher',
                 'libraries_are_the_declared_closure', 'build_receipt_is_the_declared_receipt',
                 'commit_is_the_config_commit', 'refused_as_seen_from_another_checkout',
                 'mutated_copy_refused_by_digest', 'mutated_copy_refused_at_runtime',
                 'scratch_copy_verifies_before_launch'],
    'config': ['exactly_the_three_keys_added', 'no_key_removed',
               'only_the_serving_manifest_digest_changed', 'serving_manifest_digest_was_null',
               'serving_manifest_digest_is_the_artifact',
               'server_supervision_is_the_contract_value',
               'conformance_prompts_equal_the_tool_texts', 'pinned_subtrees_unchanged',
               'engineering_acquisition_equals_run_smoke_BOUND_LIMITS',
               'rule_block_before_is_the_pin', 'rule_block_after_is_the_pin',
               'reverting_the_changes_reproduces_the_prior_config'],
    'postconditions': ['reverting_the_changes_reproduces_each_preimage',
                       'every_insertion_inside_its_section_beside_its_anchor',
                       'every_replacement_once_inside_its_fence', 'no_cr_byte_after',
                       'three_way_contract_after', 'vocabulary_sections_1_3_11_byte_identical',
                       'config', 'every_document_changed'],
    'negative_control': ['every_variant_refused_on_placement', 'scratch_copies_unchanged',
                         'real_documents_unchanged'],
    'successor_commit': ['prior_successor_commit_carries_the_prior_successor'],
    'cells': ['cells_unchanged_outside_superseded_by'],
    'artifact': ['written_once_and_reads_back', 'verifies_before_launch_from_the_main_checkout'],
    'final': ['documents_read_back_equal_computed', 'dry_check_against_the_config_on_disk'],
}
#: gates evaluated AFTER something was written: flipping them refuses the receipt, not the write
AFTER_WRITE_GATES = ('artifact', 'final')

_I = 'test_isolated_'
#: (gate, check) -> the test whose real input makes that check False, or None with the reason
LIVENESS = {
    ('pins', 'config_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'architecture_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'protocol_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'cells_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'no_cr_byte'): 'test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed',
    ('pins', 'three_way_contract_before'):
        'test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed',
    ('pins', 'rule_block_before_is_the_pin'): 'test_each_cells_or_rule_block_precondition_refuses',
    ('pins', 'cells_round_trips'): 'test_each_cells_or_rule_block_precondition_refuses',
    ('pins', 'cells_original_pin_untouched'): 'test_each_cells_or_rule_block_precondition_refuses',
    ('pins', 'cells_current_successor_is_the_prior_successor'):
        'test_each_cells_or_rule_block_precondition_refuses',
    ('pins', 'cells_successor_supersedes_the_original'):
        'test_each_cells_or_rule_block_precondition_refuses',
    ('pins', 'cells_prior_successor_count'): 'test_each_cells_or_rule_block_precondition_refuses',
    ('anchors', 'every_anchor_once'): 'test_an_absent_anchor_is_refused',
    ('anchors', 'no_anchor_error'): 'test_an_absent_anchor_is_refused',
    ('anchors', 'every_anchor_inside_its_section'):
        _I + 'the_anchor_upper_bound_refuses_an_interloper_heading',
    ('anchors', 'every_replacement_site_once_inside_its_fence'):
        _I + 'a_preimage_whose_digest_is_not_null_is_refused',
    ('anchors', 'inserted_text_form'): 'test_an_inserted_text_of_the_wrong_form_is_refused',
    ('prompt', 'build_user_prompt_takes_the_non_mbpp_branch'):
        _I + 'a_prompt_the_builder_does_not_route_is_refused',
    ('prompt', 'shape_ok'): _I + 'a_prompt_that_is_not_a_bare_signature_is_refused',
    ('prompt', 'normalized_equal_to_no_source'):
        'test_a_source_prompt_equal_to_a_conformance_prompt_is_refused',
    ('prompt', 'max_jaccard_below_threshold'):
        'test_a_source_prompt_too_similar_to_a_conformance_prompt_is_refused',
    # IMPLIED by max_jaccard_below_threshold: the six smoke tasks are source records
    ('prompt', 'max_jaccard_smoke_tasks_below_threshold'):
        'test_a_smoke_task_too_similar_to_a_conformance_prompt_is_refused',
    ('prompt', 'entry_point_defined_in_no_source'):
        'test_a_source_that_defines_a_conformance_entry_point_is_refused',
    ('prompt', 'sources_compared'): 'test_each_prompt_set_rule_refuses',
    ('prompts', 'every_prompt_passes'):
        'test_a_source_prompt_equal_to_a_conformance_prompt_is_refused',
    ('prompts', 'ids_are_oodp_1_to_4'): 'test_each_prompt_set_rule_refuses',
    ('prompts', 'distinct_among_themselves'): 'test_each_prompt_set_rule_refuses',
    ('prompts', 'no_smoke_task_missing'): 'test_each_prompt_set_rule_refuses',
    ('prompts', 'fields_are_exactly'): 'test_each_prompt_set_rule_refuses',
    ('withdrawn_predecessor', 'first_receipt_is_the_pinned_bytes'):
        'test_each_withdrawn_predecessor_condition_refuses',
    ('withdrawn_predecessor', 'correction_receipt_is_the_pinned_bytes'):
        'test_each_withdrawn_predecessor_condition_refuses',
    ('withdrawn_predecessor', 'predecessor_not_merged_into_this_branch'):
        'test_each_withdrawn_predecessor_condition_refuses',
    ('main_checkout', 'is_the_pinned_root'):
        'test_a_repo_root_other_than_the_pinned_main_checkout_is_refused',
    ('main_checkout', 'root_definitions_hold'):
        'test_a_repo_root_whose_lab_common_defines_other_roots_is_refused',
    ('main_checkout', 'durable_launcher_present'):
        'test_a_repo_root_other_than_the_pinned_main_checkout_is_refused',
    ('main_checkout', 'provenance_files_equal_this_checkout'):
        _I + 'a_main_checkout_whose_tracked_files_differ_is_refused',
    ('main_checkout', 'declaration_is_the_pinned_bytes_in_both'):
        _I + 'a_main_checkout_whose_tracked_files_differ_is_refused',
    ('main_checkout', 'no_loader_environment'):
        _I + 'a_loader_variable_in_the_environment_is_refused',
    ('manifest', 'assembled'): 'test_manifest_checks_does_not_assemble_under_a_loader_variable',
    # IMPLIED: sm.assemble and sm.runtime_problems measure with one implementation; a fresh
    # assembly fails its own immediate re-verification only if the build changes between two
    # reads, which no input of this tool arranges
    ('manifest', 'reverifies_at_once_from_the_main_checkout'): None,
    # NO REAL INPUT: the same files read twice in one run
    ('manifest', 'assembly_is_deterministic'): None,
    ('manifest', 'launcher_is_the_declared_launcher'):
        'test_manifest_checks_refuses_a_declaration_naming_another_build',
    ('manifest', 'libraries_are_the_declared_closure'):
        'test_manifest_checks_refuses_a_declaration_naming_another_build',
    ('manifest', 'build_receipt_is_the_declared_receipt'):
        'test_manifest_checks_refuses_a_declaration_naming_another_build',
    # IMPLIED by assembled: sm.assemble refuses a receipt commit other than the config's
    # (build_commit) and structure_problems a manifest commit other than it (commit)
    ('manifest', 'commit_is_the_config_commit'): None,
    # NO REAL INPUT: the other root is a fresh, empty scratch directory, where no <REPO> or
    # <RESULTS> token of the manifest can resolve to a file
    ('manifest', 'refused_as_seen_from_another_checkout'): None,
    ('manifest', 'mutated_copy_refused_by_digest'):
        'test_a_manifest_mutation_that_changes_nothing_stops_the_run',
    ('manifest', 'mutated_copy_refused_at_runtime'):
        'test_a_manifest_mutation_that_changes_nothing_stops_the_run',
    # IMPLIED by reverifies_at_once: the same object, written canonically, through the same
    # measuring functions
    ('manifest', 'scratch_copy_verifies_before_launch'): None,
    ('config', 'exactly_the_three_keys_added'):
        'test_a_key_placed_inside_the_rule_block_is_refused',
    ('config', 'no_key_removed'): 'test_each_faulty_config_inserter_is_refused',
    ('config', 'only_the_serving_manifest_digest_changed'):
        'test_each_faulty_config_inserter_is_refused',
    # IMPLIED in main() by anchors.every_replacement_site_once_inside_its_fence, which refuses
    # a non-null pre-image first; the named unit test calls config_checks() directly
    ('config', 'serving_manifest_digest_was_null'):
        'test_config_checks_refuses_a_pre_image_whose_digest_is_not_null',
    ('config', 'serving_manifest_digest_is_the_artifact'):
        'test_an_amendment_carrying_another_digest_is_refused',
    ('config', 'server_supervision_is_the_contract_value'):
        'test_each_faulty_config_inserter_is_refused',
    ('config', 'conformance_prompts_equal_the_tool_texts'):
        'test_each_faulty_config_inserter_is_refused',
    ('config', 'pinned_subtrees_unchanged'): _I + 'a_pinned_subtree_key_is_refused',
    ('config', 'engineering_acquisition_equals_run_smoke_BOUND_LIMITS'):
        _I + 'engineering_acquisition_that_differs_from_BOUND_LIMITS_is_refused',
    # IMPLIED in main() by pins.rule_block_before_is_the_pin; the unit test calls config_checks
    ('config', 'rule_block_before_is_the_pin'):
        'test_config_checks_refuses_a_pre_image_rule_block_that_is_not_the_pin',
    ('config', 'rule_block_after_is_the_pin'): _I + 'a_rule_block_key_is_refused',
    ('config', 'reverting_the_changes_reproduces_the_prior_config'):
        'test_a_key_placed_inside_the_rule_block_is_refused',
    ('postconditions', 'reverting_the_changes_reproduces_each_preimage'):
        'test_an_inserter_that_also_edits_vocabulary_section_1_is_refused',
    ('postconditions', 'every_insertion_inside_its_section_beside_its_anchor'):
        _I + 'the_section_upper_bound_refuses_an_interloper_heading',
    ('postconditions', 'every_replacement_once_inside_its_fence'):
        'test_an_amendment_carrying_another_digest_is_refused',
    ('postconditions', 'no_cr_byte_after'): 'test_each_faulty_config_inserter_is_refused',
    ('postconditions', 'three_way_contract_after'):
        _I + 'a_missing_appendix_b_copy_breaks_only_the_contract',
    ('postconditions', 'vocabulary_sections_1_3_11_byte_identical'):
        _I + 'an_insertion_in_section_1_is_refused',
    ('postconditions', 'config'): 'test_a_key_placed_inside_the_rule_block_is_refused',
    ('postconditions', 'every_document_changed'): 'test_postconditions_refuse_unchanged_documents',
    ('negative_control', 'every_variant_refused_on_placement'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'scratch_copies_unchanged'):
        None,   # NO REAL INPUT: only a filesystem fault while the control runs
    ('negative_control', 'real_documents_unchanged'):
        None,   # NO REAL INPUT: only another writer changing the real files mid-run
    ('successor_commit', 'prior_successor_commit_carries_the_prior_successor'):
        'test_a_history_whose_48f4d70_is_not_the_prior_successor_is_refused',
    ('cells', 'cells_unchanged_outside_superseded_by'):
        None,   # NO REAL INPUT: the new cells.json is built by replacing that one key
    ('artifact', 'written_once_and_reads_back'): 'test_an_existing_artifact_is_never_replaced',
    # IMPLIED by manifest.scratch_copy_verifies_before_launch: the same bytes, the same check
    ('artifact', 'verifies_before_launch_from_the_main_checkout'): None,
    ('final', 'documents_read_back_equal_computed'):
        None,   # NO REAL INPUT: only a filesystem fault between the write and the read
    # IMPLIED by artifact.verifies_before_launch and config.serving_manifest_digest_is_the_artifact
    ('final', 'dry_check_against_the_config_on_disk'): None,
}

_loaded = [0]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git(*args, text=False):
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True,
                          check=True, text=text).stdout


def _blob(rev: str, rel: str) -> bytes:
    return _git('show', '%s:%s' % (rev, rel))


def _load(path: Path, stem: str):
    _loaded[0] += 1
    spec = importlib.util.spec_from_file_location('%s_under_test_%d' % (stem, _loaded[0]), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_tool():
    return _load(TOOL, 'repair_amendment_v2')


def _load_verifier():
    return _load(HERE / 'verify_repair_amendment_v2.py', 'verify_repair_amendment_v2')


def _real_digests() -> dict:
    out = {k: sha((REPO / rel).read_bytes()) for k, rel in REL.items()}
    out['results/live_ab'] = sorted(p.name for p in (REPO / 'results' / 'live_ab').iterdir())
    art = REPO / ARTIFACT
    out['artifact'] = sha(art.read_bytes()) if art.exists() else None
    return out


def _normalized_cells(raw: bytes) -> str:
    d = json.loads(raw)
    d['provenance']['vocabulary_alignment']['superseded_by']['recorded_utc'] = \
        RECORDED_PLACEHOLDER
    return sha((json.dumps(d, indent=1) + '\n').encode('utf-8'))


def _printed(err: str) -> dict:
    """The JSON a refusal prints after 'NOTHING was written: '."""
    return json.loads(err.split('NOTHING was written: ', 1)[1])


def synthetic_sources(extra_sanitized=(), smoke_text=None, drop_smoke=()):
    """A small stand-in for the three pinned sources: unrelated prompts, the six
    smoke-task uids present (unless dropped), plus ``extra_sanitized`` records."""
    san = [{'task_id': 1, 'prompt': 'Write a function to add two numbers.',
            'code': 'def add(a, b):\n    return a + b\n'}] + list(extra_sanitized)
    full = [{'task_id': int(u.split('/')[1]),
             'text': (smoke_text or {}).get(u, 'Write a function to find item %s.' % u),
             'code': 'def item_%s(x):\n    return x\n' % u.split('/')[1]}
            for u in SMOKE if u not in drop_smoke]
    he = [{'task_id': 'HumanEval/0', 'prompt': 'def ident(x):\n    """Return x."""\n',
           'entry_point': 'ident'}]
    return {'records': {'mbpp_sanitized': san, 'mbpp_full': full, 'humaneval': he},
            'facts': {'synthetic': True}}


class _Harness:
    """setUpClass, _drive and the refusal helpers shared by the witness classes (a mixin:
    it defines no test)."""

    MFACTS = None

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
            cls.PRED = {p: _blob(c, p) for p, c in PRED_RECEIPTS.items()}
            cls.SUCC = _blob('48f4d70fbd580df282b551506448457a09ab514d', REL['PROTO'])
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history (b049307, 48f4d70, the withdrawn '
                                    'predecessor) is not available here: %s' % e)
        if not MAIN_LAUNCHER.is_file():
            raise unittest.SkipTest('the durable build of the main checkout (%s) is not on '
                                    'this host; the serving manifest cannot be assembled'
                                    % MAIN_LAUNCHER)
        if _Harness.MFACTS is None:
            m = _load_tool()
            commit = json.loads(cls.PRE['CONFIG'])['llama_cpp']['commit']
            _Harness.MFACTS = m.manifest_checks(MAIN, commit)

    def _drive(self, docs, patch=None, wrap_insert_all=None, commit_protocol=None,
               sources=None, wraps=None, argv=(), env=None, real_manifest=False,
               pred=None, ancestry=1, source_repo=None, preexisting_artifact=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the four files after, tmp)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='repair_v2_witness_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, rel in REL.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(docs[k])
        (tmp / 'results' / 'live_ab').mkdir(parents=True)
        if preexisting_artifact is not None:
            (tmp / ARTIFACT).parent.mkdir(parents=True)
            (tmp / ARTIFACT).write_bytes(preexisting_artifact)
        m = _load_tool()
        m.REPO = tmp
        for k, rel in REL.items():
            setattr(m, k, tmp / rel)
        if source_repo is not None:
            m.SOURCE_REPO = Path(source_repo)
        src = synthetic_sources() if sources is None else sources
        m.load_sources = (src if callable(src) else (lambda d, pins, _s=src: _s))
        if not real_manifest:
            cached = _Harness.MFACTS
            m.manifest_checks = lambda root, commit, declaration_path=None, _c=cached: \
                copy.deepcopy(_c)
        for name, value in (patch or {}).items():
            setattr(m, name, value)
        if wrap_insert_all is not None:
            m.insert_all = wrap_insert_all(m.insert_all, m)
        for name, fn in (wraps or {}).items():
            setattr(m, name, fn(getattr(m, name), m))
        for name in ('REPO',) + tuple(REL):
            here = Path(getattr(m, name)).resolve()
            self.assertTrue(here == tmp.resolve() or tmp.resolve() in here.parents,
                            '%s escaped the scratch directory: %s' % (name, here))
        shown = self.PRE['PROTO'] if commit_protocol is None else commit_protocol
        receipts = dict(self.PRED, **(pred or {}))
        succ = self.SUCC if commit_protocol is None else commit_protocol

        def fake_run(argv_, *a, **kw):
            if argv_[:1] == ['git'] and 'rev-parse' in argv_:
                return types.SimpleNamespace(stdout='0' * 40 + '\n', returncode=0)
            if argv_[:1] == ['git'] and 'merge-base' in argv_:
                return types.SimpleNamespace(stdout=b'', returncode=ancestry)
            if argv_[:1] == ['git'] and 'show' in argv_:
                rev, path = argv_[-1].split(':', 1)
                if path == REL['PROTO']:
                    return types.SimpleNamespace(stdout=succ, returncode=0)
                if path in receipts:
                    return types.SimpleNamespace(stdout=receipts[path], returncode=0)
            raise AssertionError('unexpected subprocess call: %r' % (argv_,))
        m.subprocess = types.SimpleNamespace(run=fake_run, CalledProcessError=
                                             subprocess.CalledProcessError)
        err = io.StringIO()
        with mock.patch.object(m.lab_common, 'harness_file_hashes',
                               return_value={'config.json': 'stub'}), \
                mock.patch.dict(os.environ, env or {}), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = m.main(['--sources-dir', str(tmp / 'no_sources_needed')] + list(argv))
        found = sorted((tmp / 'results' / 'live_ab').glob(RECEIPT_GLOB))
        receipt = json.loads(found[0].read_bytes()) if found else None
        after = {k: (tmp / rel).read_bytes() for k, rel in REL.items()}
        self.assertEqual(_real_digests(), before_real,
                         'a real document, the real artifact or results/live_ab changed')
        self._tmp = tmp
        return rc, err.getvalue(), receipt, after

    def _assert_refused_unchanged(self, docs, rc, err, receipt, after, why):
        self.assertEqual(rc, 2, '%s: expected a refusal, got exit %r (%s)' % (why, rc, err[:800]))
        self.assertIsNone(receipt, '%s: a receipt was written' % why)
        for k in REL:
            self.assertEqual(after[k], docs[k], '%s: %s was changed' % (why, k))

    def _repoint(self, docs, **new):
        d = dict(docs)
        d.update(new)
        cells = json.loads(d['CELLS'])
        cells['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(d['PROTO'])
        d['CELLS'] = (json.dumps(cells, indent=1) + '\n').encode('utf-8')
        patch = {'PRIOR_SUCCESSOR': sha(d['PROTO']), 'PRIOR_CONFIG_SHA256': sha(d['CONFIG']),
                 'PRIOR_CONFIG_BYTES': len(d['CONFIG']), 'PRIOR_ARCH_SHA256': sha(d['ARCH']),
                 'PRIOR_CELLS_SHA256': sha(d['CELLS'])}
        return d, patch, d['PROTO']

    def _refused_alone(self, gate_json: dict, check: str, why: str):
        self.assertIs(gate_json[check], False, '%s: %s' % (why, gate_json))
        others = {k: v for k, v in gate_json.items() if k != check}
        self.assertTrue(all(v is True for v in others.values()), '%s: %s' % (why, others))

    @staticmethod
    def _extra(m, key, doc, anchor, side, text, section=None, section_end=None, fence=False):
        return m.Insertion(key, doc, anchor, side, text, section, section_end, fence)

    def _probe_config_key(self, m, anchor: bytes, line: bytes):
        a61 = (m.ARCH_MARKER, b'### 6.2 The rule block')
        appb = (b'## Appendix B.', b'## Appendix C.')
        return (self._extra(m, 'probe.config', 'config', anchor, 'before', line),
                self._extra(m, 'probe.arch', 'architecture', anchor, 'before', line, *a61,
                            fence=True),
                self._extra(m, 'probe.proto', 'protocol', anchor, 'before', line, *appb,
                            fence=True))


class RepairAmendmentV2WitnessTests(_Harness, unittest.TestCase):

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(len(self.PRE['CONFIG']), 13917)
        self.assertEqual(m.PRIOR_CONFIG_SHA256, REVIEWED['CONFIG'])
        self.assertEqual(m.PRIOR_ARCH_SHA256, REVIEWED['ARCH'])
        self.assertEqual(m.PRIOR_SUCCESSOR, REVIEWED['PROTO'])
        self.assertEqual(m.PRIOR_CELLS_SHA256, REVIEWED['CELLS'])
        self.assertEqual(m.PRIOR_RULE_BLOCK, RULE_BLOCK)
        self.assertEqual(m.PRIOR_SUCCESSOR_COMMIT, '48f4d70fbd580df282b551506448457a09ab514d')
        self.assertEqual(m.MAIN_CHECKOUT, MAIN)
        self.assertIsNone(json.loads(self.PRE['CONFIG'])['llama_cpp']['serving_manifest_sha256'])

    def test_the_predecessor_texts_and_rule_are_copied_verbatim(self):
        """The four prompts, their rule's mechanical part and the configuration insertions
        are the withdrawn predecessor's, byte for byte (read from its commit)."""
        m = _load_tool()
        pred_cfg = json.loads(_blob(PRED_HEAD, REL['CONFIG']))
        self.assertEqual(pred_cfg['prefreeze']['conformance_prompts'], [dict(p) for p in m.PROMPTS])
        self.assertEqual(pred_cfg['server_supervision'], m.SERVER_SUPERVISION)
        pred_tool = _blob(PRED_HEAD, 'experiments/live_ab_tools/repair_amendment.py').decode()
        for p in m.PROMPTS:
            self.assertIn("'entry_point': %r" % p['entry_point'], pred_tool)
            self.assertIn(repr(p['prompt'].split('\n')[1] + '\n'), pred_tool)
        self.assertIn(m.CFG_SUPERVISION_TEXT.encode(), _blob(PRED_HEAD, REL['CONFIG']))
        self.assertIn(m.CFG_PROMPTS_TEXT.encode(), _blob(PRED_HEAD, REL['CONFIG']))

    # -- control: the pristine pre-images pass and reproduce the delivery ----
    def test_control_the_pristine_pre_images_reproduce_the_delivered_bytes(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        for k, want in DELIVERED.items():
            self.assertEqual(sha(after[k]), want, k)
        m = _load_tool()
        digest = SERVING_MANIFEST_SHA256
        for k, doc in (('CONFIG', 'config'), ('ARCH', 'architecture'), ('PROTO', 'protocol')):
            self.assertEqual(m.remove_all(after[k], doc, digest), self.PRE[k], k)
        self.assertEqual(_normalized_cells(after['CELLS']), DELIVERED_CELLS_NORMALIZED_SHA256)
        post = receipt['postcondition_checked']
        self.assertEqual(len(post['every_insertion_inside_its_section_beside_its_anchor']), 27)
        self.assertTrue(all(post['every_insertion_inside_its_section_beside_its_anchor'].values()))
        self.assertEqual(post['reverting_the_changes_reproduces_each_preimage'],
                         {'config': True, 'architecture': True, 'protocol': True})
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertEqual(post['vocabulary_sections_1_3_11_byte_identical'],
                         {'1': True, '3': True, '11': True})
        self.assertEqual(post['config']['rule_block_sha256_after'], RULE_BLOCK)
        self.assertEqual(post['config']['added_keys'], m.ADDED_CONFIG_KEYS)
        self.assertEqual(post['config']['changed_keys'], ['llama_cpp.serving_manifest_sha256'])
        self.assertIsNone(post['config']['serving_manifest_sha256_before'])
        self.assertEqual(post['config']['serving_manifest_sha256_after'], digest)
        control = receipt['negative_control']
        self.assertIs(control['every_variant_refused_on_placement'], True)
        self.assertEqual(control['variants_run'], 25)
        cfg = json.loads(after['CONFIG'])
        self.assertEqual(cfg['server_supervision'],
                         {'max_supervised_restarts_per_server_per_trial': 3,
                          'on_exceeding': 'abort_trial_incomplete'})
        self.assertEqual([p['id'] for p in cfg['prefreeze']['conformance_prompts']],
                         ['oodp/1', 'oodp/2', 'oodp/3', 'oodp/4'])
        self.assertEqual(cfg['llama_cpp']['serving_manifest_sha256'], digest)
        # the artifact: written once in the scratch tree, canonical, the config's digest
        art = (self._tmp / ARTIFACT).read_bytes()
        obj = json.loads(art)
        self.assertEqual(art, (m.lab_common.canonical_json(obj) + '\n').encode())
        self.assertEqual(m.lab_common.sha256_canonical(obj), digest)
        committed = REPO / ARTIFACT
        if committed.exists():
            self.assertEqual(art, committed.read_bytes())
        sm_rec = receipt['serving_manifest']
        self.assertEqual(sm_rec['sha256_canonical'], digest)
        self.assertEqual(sm_rec['dry_check_after_writing']['labels'], [])
        self.assertTrue(all(sm_rec['evidence']['gate'].values()))
        self.assertEqual(receipt['replacement']['new_value'], digest)
        self.assertIsNone(receipt['replacement']['old_value'])
        # the withdrawn predecessor, named
        wp = receipt['withdrawn_predecessor']
        self.assertEqual(wp['status'], 'withdrawn, not applied')
        self.assertEqual(wp['branch'], 'session60/repair-amend')
        self.assertEqual([r['sha256'] for r in wp['receipts']],
                         [sha(self.PRED[p]) for p in PRED_RECEIPTS])
        self.assertTrue(all(wp['verified_from_git']['gate'].values()))
        # cells.json: 64ace6d3 demoted whole with 48f4d70, as the predecessor did
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(sb['sha256'], DELIVERED['PROTO'])
        self.assertEqual(sb['supersedes'], m.ORIGINAL_PIN)
        self.assertTrue(sb['reason'].startswith('NOT Appendix-B-only:'))
        self.assertEqual(len(sb['prior_successors']), 6)
        last = sb['prior_successors'][5]
        self.assertEqual(last['sha256'], REVIEWED['PROTO'])
        self.assertEqual(last['changing_commit_of_this_successor'], m.PRIOR_SUCCESSOR_COMMIT)
        self.assertIn('git show 48f4d70:', last['changing_commit_note'])
        old_sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment'][
            'superseded_by']
        self.assertEqual(sb['prior_successors'][:5], old_sb['prior_successors'])
        pred_sb = json.loads(_blob(PRED_HEAD, REL['CELLS']))['provenance'][
            'vocabulary_alignment']['superseded_by']
        self.assertEqual(sb['prior_successors'][5], pred_sb['prior_successors'][5],
                         'the demoted entry is the one the predecessor wrote')
        a, b = json.loads(self.PRE['CELLS']), json.loads(after['CELLS'])
        a['provenance']['vocabulary_alignment'].pop('superseded_by')
        b['provenance']['vocabulary_alignment'].pop('superseded_by')
        self.assertEqual(a, b)

    # -- CR --------------------------------------------------------------------
    def test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed(self):
        p = self.PRE['PROTO']
        i = p.index(b'\n')
        d, patch, shown = self._repoint(self.PRE, PROTO=p[:i] + b'\r' + p[i:])
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CR in protocol')
        g = _printed(err)['gate_pins']
        self.assertIs(g['no_cr_byte'], False)
        self.assertIs(g['three_way_contract_before'], False)

    def test_a_CRLF_config_is_refused(self):
        d = dict(self.PRE)
        d['CONFIG'] = d['CONFIG'].replace(b'\n', b'\r\n')
        rc, err, receipt, after = self._drive(
            d, patch={'PRIOR_CONFIG_SHA256': sha(d['CONFIG']),
                      'PRIOR_CONFIG_BYTES': len(d['CONFIG'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CRLF config')
        self.assertIn('precondition', err)

    def test_each_cells_or_rule_block_precondition_refuses(self):
        def cells_with(fn):
            c = json.loads(self.PRE['CELLS'])
            fn(c['provenance']['vocabulary_alignment'])
            return c

        def ser(c, indent=1):
            return (json.dumps(c, indent=indent) + '\n').encode('utf-8')
        anchor = b'"auto_abort": {"consecutive_infrastructure_failures": 10'
        rb = {k: self.PRE[k].replace(anchor, anchor[:-2] + b'11', 1)
              for k in ('CONFIG', 'ARCH', 'PROTO')}
        cases = {
            'rule_block_before_is_the_pin': dict(rb),
            'cells_round_trips': {'CELLS': ser(json.loads(self.PRE['CELLS']), indent=2)},
            'cells_original_pin_untouched': {'CELLS': ser(cells_with(
                lambda va: va.__setitem__('sha256', '0' * 64)))},
            'cells_current_successor_is_the_prior_successor': {'CELLS': ser(cells_with(
                lambda va: va['superseded_by'].__setitem__('sha256', '1' * 64)))},
            'cells_successor_supersedes_the_original': {'CELLS': ser(cells_with(
                lambda va: va['superseded_by'].__setitem__('supersedes', '2' * 64)))},
            'cells_prior_successor_count': {'CELLS': ser(cells_with(
                lambda va: va['superseded_by']['prior_successors'].pop()))},
        }
        for check, new in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                d.update(new)
                patch = {'PRIOR_SUCCESSOR': sha(d['PROTO']), 'PRIOR_CONFIG_SHA256': sha(d['CONFIG']),
                         'PRIOR_CONFIG_BYTES': len(d['CONFIG']), 'PRIOR_ARCH_SHA256': sha(d['ARCH']),
                         'PRIOR_CELLS_SHA256': sha(d['CELLS'])}
                if check == 'rule_block_before_is_the_pin':
                    c = json.loads(d['CELLS'])
                    c['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(d['PROTO'])
                    d['CELLS'] = ser(c)
                    patch['PRIOR_CELLS_SHA256'] = sha(d['CELLS'])
                if check == 'cells_current_successor_is_the_prior_successor':
                    patch['PRIOR_SUCCESSOR'] = REVIEWED['PROTO']
                rc, err, receipt, after = self._drive(d, patch=patch)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate_pins'], check, check)

    # -- moved outside its section -------------------------------------------
    def _moving(self, key):
        def wrap(real, m):
            ins = next(i for i in m.INSERTIONS if i.key == key)

            def moved(old):
                return m.move_out(real(old), ins)
            return moved
        return wrap

    def test_an_insertion_moved_out_of_its_section_is_refused(self):
        for key in ('protocol.5_3', 'protocol.12_4', 'protocol.14_6', 'protocol.2_2',
                    'architecture.2_2', 'architecture.3_16.row',
                    'architecture.7_1.rows_21a_21b', 'protocol.appendix_b.server_supervision'):
            with self.subTest(key=key):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=self._moving(key))
                self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved ' + key)
                self.assertIn('postcondition', err)
                self.assertIn('"%s": false' % key, err)

    def test_only_the_section_bound_refuses_an_anchor_that_lies_in_14_7(self):
        p = self.PRE['PROTO']
        heading = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        self.assertEqual(p.count(heading), 1)
        without = p.replace(heading, b'', 1)
        k = without.index(b'**Aborts.** The automatic aborts of 6.4')
        altered = without[:k] + heading + without[k:]
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.14_6')
        self.assertIs(m.anchor_facts(altered, ins)['inside_its_section'], False)
        real = m.anchor_facts
        patch['anchor_facts'] = lambda raw, i: dict(real(raw, i), inside_its_section=True)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor in 14.7')
        self.assertIn('postcondition', err)

    def _interloper(self):
        p = self.PRE['PROTO']
        h = b'### 5.4 Sampling parameters\n'
        self.assertEqual(p.count(h), 1)
        return p.replace(h, b'### 5.3a Interloper\n\nA heading nobody expected.\n\n' + h, 1)

    def test_isolated_the_anchor_upper_bound_refuses_an_interloper_heading(self):
        altered = self._interloper()
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'interloper, anchor')
        printed = _printed(err)
        self._refused_alone(printed['gate_anchors'], 'every_anchor_inside_its_section', 'anchor')
        bad = [k for k, a in printed['anchors'].items() if a.get('inside_its_section') is False]
        self.assertEqual(bad, ['protocol.5_3'])

    def test_isolated_the_section_upper_bound_refuses_an_interloper_heading(self):
        altered = self._interloper()
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        m = _load_tool()
        real = m.anchor_facts
        patch['anchor_facts'] = lambda raw, i: dict(real(raw, i), inside_its_section=True)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'interloper, placement')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'every_insertion_inside_its_section_beside_its_anchor',
                            'placement')
        self.assertEqual([k for k, v in printed['every_insertion_inside_its_section_beside_its_anchor']
                          .items() if not v], ['protocol.5_3'])

    # -- anchors and the replacement site ---------------------------------------
    def test_an_absent_anchor_is_refused(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.12_4')
        altered = self.PRE['PROTO'].replace(ins.anchor, ins.anchor.replace(b'names).', b'names.)'),
                                            1)
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor absent')
        g = _printed(err)['gate_anchors']
        self.assertIs(g['every_anchor_once'], False)
        self.assertIs(g['no_anchor_error'], False)

    def test_a_duplicated_anchor_is_refused(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'architecture.7_1.row_14c')
        a = self.PRE['ARCH']
        k = a.index(b'### 7.2 What is fsynced')
        altered = a[:k] + ins.anchor + b'x |\n\n' + a[k:]
        d, patch, shown = self._repoint(self.PRE, ARCH=altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor twice')
        self.assertIn('"anchor_occurrences": 2', err)

    def test_isolated_a_preimage_whose_digest_is_not_null_is_refused(self):
        """The three copies already carry a digest (pins re-pointed): only the replacement
        site check refuses."""
        old = b'"serving_manifest_sha256": null}'
        new = b'"serving_manifest_sha256": "%s"}' % (b'a' * 64)
        d, patch, shown = self._repoint(self.PRE, **{k: self.PRE[k].replace(old, new, 1)
                                                     for k in ('CONFIG', 'ARCH', 'PROTO')})
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'digest not null')
        printed = _printed(err)
        self._refused_alone(printed['gate_anchors'],
                            'every_replacement_site_once_inside_its_fence', 'site')
        self.assertTrue(all(v is True for v in printed['gate_pins'].values()))

    def test_an_inserted_text_of_the_wrong_form_is_refused(self):
        m = _load_tool()
        long_line = '*Probe.* ' + 'x' * 130
        swapped = tuple(m.Insertion(i.key, i.doc, i.anchor, i.side,
                                    (i.text + (long_line + '\n').encode()) if i.key == 'protocol.13_1'
                                    else i.text, i.section, i.section_end, i.fence)
                        for i in m.INSERTIONS)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': swapped})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'text form')
        self._refused_alone(_printed(err)['gate_anchors'], 'inserted_text_form', 'form')

    # -- the inserter edits more than it should ---------------------------------
    def test_an_inserter_that_also_edits_vocabulary_section_1_is_refused(self):
        def wrap(real, m):
            def faulty(old):
                out = real(old)
                p = out['protocol']
                i = p.index(b'## 1. Purpose, scope')
                j = p.index(b'\n', i) + 1
                return dict(out, protocol=p[:j] + b'\n' + p[j:])
            return faulty
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'section 1 edited')
        g = _printed(err)['gate']
        self.assertIs(g['reverting_the_changes_reproduces_each_preimage'], False)
        self.assertIs(g['vocabulary_sections_1_3_11_byte_identical'], False)

    def test_isolated_an_insertion_in_section_1_is_refused(self):
        m = _load_tool()
        heading = b'## 1. Purpose, scope, the feasibility declaration, and the claim lists\n'
        probe = self._extra(m, 'probe.section_1', 'protocol', heading, 'after',
                            '\n*Probe paragraph inside section 1.*\n',
                            b'## 1. Purpose, scope', b'## 2. Systems')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': m.INSERTIONS + (probe,)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'section 1 insertion')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'vocabulary_sections_1_3_11_byte_identical', 'vocab')

    def test_isolated_a_missing_appendix_b_copy_breaks_only_the_contract(self):
        m = _load_tool()
        fewer = tuple(i for i in m.INSERTIONS if i.key != 'protocol.appendix_b.server_supervision')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': fewer})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'no Appendix B copy')
        self._refused_alone(_printed(err)['gate'], 'three_way_contract_after', 'contract')

    def test_a_key_placed_inside_the_rule_block_is_refused(self):
        anchor = b'"auto_abort": {"consecutive_infrastructure_failures": 10,'

        def wrap(real, m):
            def faulty(old):
                out = real(old)
                return {k: v.replace(anchor, anchor + b' "restart_cap": 3,', 1)
                        for k, v in out.items()}
            return faulty
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'rule block')
        post = _printed(err)
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertNotEqual(post['config']['rule_block_sha256_after'], RULE_BLOCK)
        g = post['config']['gate']
        self.assertIs(g['exactly_the_three_keys_added'], False)
        self.assertIs(g['rule_block_after_is_the_pin'], False)
        self.assertIs(g['reverting_the_changes_reproduces_the_prior_config'], False)
        self.assertIs(post['gate']['config'], False)

    def test_isolated_a_rule_block_key_is_refused(self):
        m = _load_tool()
        probes = self._probe_config_key(m, b'    "clock_equivalence_tolerance_ms": 1\n',
                                        b'    "probe_key": 1,\n')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={
            'INSERTIONS': m.INSERTIONS + probes,
            'ADDED_CONFIG_KEYS': sorted(m.ADDED_CONFIG_KEYS + ['enclosure.probe_key'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'rule-block key')
        printed = _printed(err)
        self._refused_alone(printed['config']['gate'], 'rule_block_after_is_the_pin', 'rule block')
        self._refused_alone(printed['gate'], 'config', 'rule block')

    def test_isolated_a_pinned_subtree_key_is_refused(self):
        m = _load_tool()
        probes = self._probe_config_key(m, b'              "containment_probe_sha256": null},\n',
                                        b'              "probe_key": 1,\n')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={
            'INSERTIONS': m.INSERTIONS + probes,
            'ADDED_CONFIG_KEYS': sorted(m.ADDED_CONFIG_KEYS + ['sandbox.probe_key'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'pinned subtree key')
        printed = _printed(err)
        self._refused_alone(printed['config']['gate'], 'pinned_subtrees_unchanged', 'subtree')
        self.assertEqual([k for k, v in printed['config']['subtrees_unchanged'].items() if not v],
                         ['sandbox'])

    def test_each_faulty_config_inserter_is_refused(self):
        cases = {
            'no_key_removed': ('config', b'"pause_thresholds":', b'"pause_threshold":'),
            'only_the_serving_manifest_digest_changed':
                ('config', b'"battery_percent": 20', b'"battery_percent": 21'),
            'server_supervision_is_the_contract_value':
                ('config', b'"max_supervised_restarts_per_server_per_trial": 3',
                 b'"max_supervised_restarts_per_server_per_trial": 4'),
            'conformance_prompts_equal_the_tool_texts':
                ('config', b'Return one sentence that alternates', b'Return a sentence that alternates'),
            'no_cr_byte_after': ('postconditions', b'  "hardware_allowlist":', b'\r  "hardware_allowlist":'),
        }
        for check, (where, old, new) in cases.items():
            with self.subTest(check=check):
                def wrap(real, m, _o=old, _n=new):
                    def faulty(docs):
                        out = real(docs)
                        return {k: v.replace(_o, _n, 1) for k, v in out.items()}
                    return faulty
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                printed = _printed(err)
                g = printed['config']['gate'] if where == 'config' else printed['gate']
                self.assertIs(g[check], False, (check, g))

    def test_an_amendment_carrying_another_digest_is_refused(self):
        """amend() writes a digest other than the artifact's into all three copies."""
        def wrap(real, m):
            return lambda old, digest: real(old, 'b' * 64)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wraps={'amend': wrap})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'another digest')
        printed = _printed(err)
        self.assertIs(printed['config']['gate']['serving_manifest_digest_is_the_artifact'], False)
        self.assertIs(printed['gate']['every_replacement_once_inside_its_fence'], False)
        self.assertIs(printed['three_way_contract_after']['holds'], True)

    def test_isolated_engineering_acquisition_that_differs_from_BOUND_LIMITS_is_refused(self):
        m = _load_tool()
        limits = m.bound_limits()
        self.assertIsNotNone(limits)
        off = dict(limits, wall_seconds_total=601.0)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'bound_limits': lambda: dict(off)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'BOUND_LIMITS')
        self._refused_alone(_printed(err)['config']['gate'],
                            'engineering_acquisition_equals_run_smoke_BOUND_LIMITS', 'ea')

    def test_config_checks_refuses_a_pre_image_rule_block_that_is_not_the_pin(self):
        m = _load_tool()
        anchor = b'"consecutive_infrastructure_failures": 10'
        old = self.PRE['CONFIG'].replace(anchor, anchor[:-2] + b'11', 1)
        new = m.amend({'config': old, 'architecture': self.PRE['ARCH'],
                       'protocol': self.PRE['PROTO']}, SERVING_MANIFEST_SHA256)['config']
        out = m.config_checks(old, new, SERVING_MANIFEST_SHA256)
        self.assertIs(out['gate']['rule_block_before_is_the_pin'], False)
        self.assertIs(out['ok'], False)

    def test_config_checks_refuses_a_pre_image_whose_digest_is_not_null(self):
        m = _load_tool()
        old = self.PRE['CONFIG'].replace(b'"serving_manifest_sha256": null}',
                                         b'"serving_manifest_sha256": "%s"}' % (b'c' * 64), 1)
        new = m.amend({'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
                       'protocol': self.PRE['PROTO']}, SERVING_MANIFEST_SHA256)['config']
        out = m.config_checks(old, new, SERVING_MANIFEST_SHA256)
        self.assertIs(out['gate']['serving_manifest_digest_was_null'], False)
        self.assertIs(out['ok'], False)
        control = m.config_checks(self.PRE['CONFIG'], new, SERVING_MANIFEST_SHA256)
        self.assertIs(control['gate']['serving_manifest_digest_was_null'], True)

    def test_postconditions_refuse_unchanged_documents(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        post, ok = m.postconditions(old, dict(old), SERVING_MANIFEST_SHA256)
        self.assertIs(post['gate']['every_document_changed'], False)
        self.assertIs(ok, False)

    # -- the four prompts against the sources ------------------------------------
    def _prompt_refusal(self, sources, needle, patch=None, wraps=None):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, sources=sources, patch=patch, wraps=wraps)
        self._assert_refused_unchanged(d, rc, err, receipt, after, needle)
        self.assertIn('failed the stated rule', err)
        self.assertIn(needle, err)
        return err

    def test_a_source_prompt_equal_to_a_conformance_prompt_is_refused(self):
        m = _load_tool()
        clone = m.PROMPTS[1]['prompt'].upper().replace('\n', '  ')
        err = self._prompt_refusal(synthetic_sources([{'task_id': 900, 'prompt': clone,
                                                        'code': ''}]),
                                   '"normalized_equal_to": ["mbpp/900"]')
        printed = _printed(err)
        self.assertIs(printed['per_prompt'][1]['gate']['normalized_equal_to_no_source'], False)
        self._refused_alone(printed['gate'], 'every_prompt_passes', 'equal')

    def test_a_source_prompt_too_similar_to_a_conformance_prompt_is_refused(self):
        m = _load_tool()
        near = m.PROMPTS[2]['prompt'].replace('earliest', 'soonest')
        self.assertGreaterEqual(m.jaccard(near, m.PROMPTS[2]['prompt']), 0.5)
        err = self._prompt_refusal(synthetic_sources([{'task_id': 901, 'prompt': near,
                                                        'code': ''}]),
                                   '"closest_source_uid": "mbpp/901"')
        self._refused_alone(_printed(err)['per_prompt'][2]['gate'], 'max_jaccard_below_threshold',
                            'too similar')

    def test_a_smoke_task_too_similar_to_a_conformance_prompt_is_refused(self):
        m = _load_tool()
        near = m.PROMPTS[2]['prompt'].replace('earliest', 'soonest')
        err = self._prompt_refusal(synthetic_sources(smoke_text={'mbpp_full/39': near}),
                                   '"closest_smoke_task": "mbpp_full/39"')
        g = _printed(err)['per_prompt'][2]['gate']
        self.assertIs(g['max_jaccard_smoke_tasks_below_threshold'], False)
        self.assertIs(g['max_jaccard_below_threshold'], False)

    def test_a_source_that_defines_a_conformance_entry_point_is_refused(self):
        err = self._prompt_refusal(synthetic_sources([{'task_id': 902, 'prompt': 'Unrelated words.',
                                                       'code': 'def rotate_digits(s):\n  return s\n'}]),
                                   '"entry_point_defined_in_a_source": true')
        self._refused_alone(_printed(err)['per_prompt'][3]['gate'], 'entry_point_defined_in_no_source',
                            'entry point')

    def test_isolated_a_prompt_that_is_not_a_bare_signature_is_refused(self):
        m = _load_tool()
        bad = dict(m.PROMPTS[0], prompt=m.PROMPTS[0]['prompt'] + '    return left\n')
        err = self._prompt_refusal(None, '"shape_ok": false',
                                   patch={'PROMPTS': (bad,) + tuple(m.PROMPTS[1:])})
        printed = _printed(err)
        self._refused_alone(printed['per_prompt'][0]['gate'], 'shape_ok', 'shape')

    def test_isolated_a_prompt_the_builder_does_not_route_is_refused(self):
        err = self._prompt_refusal(
            None, '"build_user_prompt_takes_the_non_mbpp_branch": false',
            wraps={'build_user_prompt_fn': lambda real, m: (lambda: (lambda p: 'Solve: ' + p['prompt']))})
        for row in _printed(err)['per_prompt']:
            self._refused_alone(row['gate'], 'build_user_prompt_takes_the_non_mbpp_branch', 'route')

    def test_each_prompt_set_rule_refuses(self):
        m = _load_tool()
        p = [dict(x) for x in m.PROMPTS]
        cases = {
            'ids_are_oodp_1_to_4': ({'PROMPTS': tuple([dict(p[0], id='oodp/9')] + p[1:])}, None),
            'distinct_among_themselves': ({'PROMPTS': tuple(p[:3] + [dict(p[3], entry_point=p[0]['entry_point'])])},
                                          None),
            'fields_are_exactly': ({'PROMPTS': tuple([dict(p[0], note='x')] + p[1:])}, None),
            'no_smoke_task_missing': (None, synthetic_sources(drop_smoke=('mbpp_full/39',))),
            'sources_compared': (None, {'records': {'mbpp_sanitized': [], 'mbpp_full': [],
                                                    'humaneval': []}, 'facts': {}}),
        }
        for check, (patch, sources) in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, patch=patch, sources=sources)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                printed = _printed(err)
                if check == 'sources_compared':
                    self.assertIs(printed['per_prompt'][0]['gate']['sources_compared'], False)
                else:
                    self.assertIs(printed['gate'][check], False, printed['gate'])

    def test_a_pinned_source_whose_digest_is_not_the_pin_is_refused(self):
        tmp = Path(tempfile.mkdtemp(prefix='repair_v2_sources_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        m = _load_tool()
        for fname in m.SOURCE_FILES.values():
            (tmp / fname).write_bytes(b'not the pinned bytes\n')
        pins = json.loads(self.PRE['CONFIG'])['roster']['sources']
        with self.assertRaises(ValueError):
            m.load_sources(tmp, pins)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(
            d, sources=lambda _d, p, _t=tmp, _m=m: _m.load_sources(_t, p))
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'tampered sources')
        self.assertIn('could not be read', err)

    # -- the withdrawn predecessor ---------------------------------------------------
    def test_each_withdrawn_predecessor_condition_refuses(self):
        first, second = list(PRED_RECEIPTS)
        cases = {'first_receipt_is_the_pinned_bytes': ({first: b'{}\n'}, 1),
                 'correction_receipt_is_the_pinned_bytes': ({second: b'{}\n'}, 1),
                 'predecessor_not_merged_into_this_branch': (None, 0)}
        for check, (pred, ancestry) in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, pred=pred, ancestry=ancestry)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self.assertIn('withdrawn predecessor', err)
                self._refused_alone(_printed(err)['gate'], check, check)

    # -- the main checkout and the manifest -----------------------------------------
    def test_a_repo_root_other_than_the_pinned_main_checkout_is_refused(self):
        """This checkout as the repo root: its lab_common defines the roots as expected, but it
        is not the pinned root and holds no durable build."""
        root = os.path.realpath(str(REPO))
        if root == MAIN:
            self.skipTest('running inside the main checkout itself')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, argv=['--repo-root', root])
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'other root')
        g = _printed(err)['gate']
        self.assertIs(g['is_the_pinned_root'], False)
        self.assertIs(g['durable_launcher_present'], False)
        self.assertIs(g['root_definitions_hold'], True)

    def test_a_repo_root_whose_lab_common_defines_other_roots_is_refused(self):
        tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='repair_v2_root_')))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / 'experiments' / 'live_ab').mkdir(parents=True)
        src = (REPO / 'experiments' / 'live_ab' / 'lab_common.py').read_text('utf-8')
        (tmp / 'experiments' / 'live_ab' / 'lab_common.py').write_text(
            src.replace("RESULTS_ROOT: Path = REPO_ROOT / 'results' / 'live_ab'",
                        "RESULTS_ROOT: Path = REPO_ROOT / 'results'"), 'utf-8')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, argv=['--repo-root', str(tmp)])
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'root definitions')
        printed = _printed(err)
        self.assertIs(printed['gate']['root_definitions_hold'], False)
        self.assertIn('repo_root_definitions', printed['root_problems'])

    def test_isolated_a_main_checkout_whose_tracked_files_differ_is_refused(self):
        """This checkout's tracked copies replaced (in a scratch 'source repo') by one altered
        file: the build log, then the declaration.  Only the matching check refuses."""
        m = _load_tool()
        for rel, check in ((m.TRACKED_PROVENANCE[1], 'provenance_files_equal_this_checkout'),
                           (m.DECLARATION_REL, 'declaration_is_the_pinned_bytes_in_both')):
            with self.subTest(check=check):
                src = Path(tempfile.mkdtemp(prefix='repair_v2_source_'))
                self.addCleanup(shutil.rmtree, src, True)
                for r in m.TRACKED_PROVENANCE:
                    (src / r).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(REPO / r, src / r)
                (src / rel).write_bytes((src / rel).read_bytes() + b' ')
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, source_repo=src)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate'], check, check)

    def test_isolated_a_loader_variable_in_the_environment_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, env={'GGML_METAL_PATH_RESOURCES': '/tmp'})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'loader variable')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'no_loader_environment', 'environment')
        self.assertEqual(printed['loader_environment'], ['GGML_METAL_PATH_RESOURCES'])

    def test_manifest_checks_does_not_assemble_under_a_loader_variable(self):
        m = _load_tool()
        commit = json.loads(self.PRE['CONFIG'])['llama_cpp']['commit']
        with mock.patch.dict(os.environ, {'DYLD_LIBRARY_PATH': '/tmp'}):
            out = m.manifest_checks(MAIN, commit)
        self.assertIs(out['gate']['assembled'], False)
        self.assertTrue(any(p.startswith('assembly_environment') for p in out['assembly_problems']),
                        out['assembly_problems'])
        self.assertIs(m.gate('manifest', out['gate']), False)

    def test_manifest_checks_refuses_a_declaration_naming_another_build(self):
        m = _load_tool()
        commit = json.loads(self.PRE['CONFIG'])['llama_cpp']['commit']
        decl = json.loads((Path(MAIN) / m.DECLARATION_REL).read_text('utf-8'))

        def launcher(x):
            x['candidate_instrument']['launcher']['sha256'] = '0' * 64

        def library(x):
            lib = next(v for v in x['candidate_instrument']['library_closure'].values()
                       if not v.get('system_library'))
            lib['sha256'] = '0' * 64

        def receipt(x):
            x['rebuild_receipt']['sha256'] = '0' * 64
        for check, fn in (('launcher_is_the_declared_launcher', launcher),
                          ('libraries_are_the_declared_closure', library),
                          ('build_receipt_is_the_declared_receipt', receipt)):
            with self.subTest(check=check):
                variant = copy.deepcopy(decl)
                fn(variant)
                tmp = Path(tempfile.mkdtemp(prefix='repair_v2_decl_'))
                self.addCleanup(shutil.rmtree, tmp, True)
                (tmp / 'decl.json').write_text(json.dumps(variant), 'utf-8')
                out = m.manifest_checks(MAIN, commit, declaration_path=tmp / 'decl.json')
                self._refused_alone(out['gate'], check, check)

    def test_a_manifest_mutation_that_changes_nothing_stops_the_run(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, real_manifest=True,
                                              patch={'mutate': lambda man: copy.deepcopy(man)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'dead mutation')
        g = _printed(err)['gate']
        self.assertIs(g['mutated_copy_refused_by_digest'], False)
        self.assertIs(g['mutated_copy_refused_at_runtime'], False)

    def test_the_real_manifest_checks_pass_and_record_their_refusals(self):
        out = copy.deepcopy(_Harness.MFACTS)
        self.assertTrue(all(v is True for v in out['gate'].values()), out['gate'])
        self.assertEqual(out['sha256_canonical'], SERVING_MANIFEST_SHA256)
        self.assertEqual(out['reverify_as_seen_from_the_main_checkout'], [])
        self.assertIn('launcher_path', out['reverify_as_seen_from_another_checkout'])
        if os.path.realpath(str(REPO)) != MAIN:
            self.assertIn('launcher_path', out['reverify_as_seen_from_this_checkout'])
        mc = out['mutated_copy']
        self.assertEqual(mc['structure_problems'], [])
        self.assertEqual(mc['against_the_real_digest'], ['digest'])
        self.assertTrue(any(x.startswith('library_sha256:') for x in mc['against_its_own_digest']),
                        mc['against_its_own_digest'])
        self.assertEqual(out['scratch_copy_verify_before_launch'], [])
        self.assertEqual(out['libraries'], 9)
        self.assertEqual(out['metal_library_kind'], 'embedded')

    def test_an_existing_artifact_is_never_replaced(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, preexisting_artifact=b'{"older":true}\n')
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'existing artifact')
        self.assertIn('the four documents were NOT written', err)
        self.assertEqual((self._tmp / ARTIFACT).read_bytes(), b'{"older":true}\n')
        printed = json.loads(err.split('NOT written: ', 1)[1])
        self.assertIs(printed['gate']['written_once_and_reads_back'], False)

    # -- the successor commit and the one-shot guard -------------------------------
    def test_a_history_whose_48f4d70_is_not_the_prior_successor_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, commit_protocol=b'some other protocol\n')
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'wrong commit')
        self.assertIn('does not carry the prior successor', err)

    def test_a_negative_control_that_cannot_refuse_stops_the_run(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'move_out': lambda new, ins: new})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'dead control')
        self.assertIn('the negative control did not refuse', err)
        self._refused_alone(_printed(err)['gate'], 'every_variant_refused_on_placement', 'control')

    def test_the_amended_documents_are_refused(self):
        rc, err, receipt, amended = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        d = dict(amended)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, as pinned')
        g = _printed(err)['gate_pins']
        for check in ('config_is_the_reviewed_preimage', 'architecture_is_the_reviewed_preimage',
                      'protocol_is_the_reviewed_preimage', 'cells_is_the_reviewed_preimage'):
            self.assertIs(g[check], False, check)
        d2, patch, shown = self._repoint(d)
        patch['PRIOR_PRIOR_SUCCESSORS'] = 6
        rc, err, receipt, after = self._drive(d2, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d2, rc, err, receipt, after, 'amended, pins re-pointed')
        self.assertIn('the amendment is already present', err)

    def test_isolated_an_insertion_away_from_its_anchor_is_refused(self):
        def wrap(real, m):
            ins = next(i for i in m.INSERTIONS if i.key == 'protocol.5_3')

            def faulty(old):
                out = real(old)
                p = out['protocol'].replace(ins.text, b'', 1)
                k = p.index(ins.section)
                k = p.index(b'\n', k) + 1
                return dict(out, protocol=p[:k] + ins.text + p[k:])
            return faulty
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'away from anchor')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'every_insertion_inside_its_section_beside_its_anchor',
                            'beside')

    # -- units -------------------------------------------------------------------
    def test_placement_has_both_bounds_for_every_insertion(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        new = m.amend(old, SERVING_MANIFEST_SHA256)
        for ins in m.INSERTIONS:
            if ins.section is None:
                continue
            with self.subTest(key=ins.key):
                where = m.placement(new[ins.doc], ins)
                s0, s1 = where['section']
                self.assertTrue(new[ins.doc][s0:].startswith(ins.section))
                self.assertTrue(new[ins.doc][s1:].startswith(ins.section_end))
                self.assertTrue(s0 < where['insert_at'] < s1)
                self.assertIs(where['inside_its_section'], True)
                self.assertIs(m.placement(old[ins.doc], ins)['inside_its_section'], False)
        for rep in m.replacements(SERVING_MANIFEST_SHA256):
            with self.subTest(replacement=rep.key):
                self.assertIs(m.site_facts(new[rep.doc], rep, which='new')['ok'], True)
                self.assertIs(m.site_facts(old[rep.doc], rep, which='old')['ok'], True)
                self.assertIs(m.site_facts(old[rep.doc], rep, which='new')['ok'], False)

    def test_site_facts_refuses_a_replaced_value_outside_its_fence(self):
        m = _load_tool()
        rep = m.replacements(SERVING_MANIFEST_SHA256)[2]            # Appendix B
        new = m.amend({'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
                       'protocol': self.PRE['PROTO']}, SERVING_MANIFEST_SHA256)['protocol']
        moved = new.replace(rep.new, rep.old, 1)
        k = moved.index(b'## Appendix C.')
        moved = moved[:k] + rep.new + b'\n\n' + moved[k:]
        self.assertIs(m.site_facts(moved, rep, which='new')['inside_its_fence'], False)

    def test_prompt_shape_refuses_a_body_an_example_and_an_import(self):
        m = _load_tool()
        good = dict(m.PROMPTS[0])
        self.assertIs(m.prompt_shape(good)['ok'], True)
        for bad in (good['prompt'] + '    return left\n',
                    good['prompt'].replace('    """\n', '    >>> interleave_words("a", "b")\n'
                                                       '    """\n', 1),
                    'import re\n' + good['prompt']):
            with self.subTest(bad=bad[:30]):
                self.assertIs(m.prompt_shape(dict(good, prompt=bad))['ok'], False)

    def test_the_prompts_take_the_non_mbpp_branch_and_an_mbpp_route_would_not(self):
        m = _load_tool()
        build = m.build_user_prompt_fn()
        for p in m.PROMPTS:
            msg = build(dict(p))
            self.assertTrue(msg.startswith('Complete the following Python function.'))
            self.assertIn(p['prompt'], msg)
        with self.assertRaises(KeyError):
            build(dict(m.PROMPTS[0], benchmark='mbpp'))


class GateTests(_Harness, unittest.TestCase):
    """AGGREGATION: each named check of each gate refuses on its own."""

    def test_the_gates_and_their_checks_are_exactly_the_pinned_list(self):
        calls = {}

        def wrap(real, m):
            def recording(name, checks):
                calls.setdefault(name, list(checks))
                self.assertEqual(calls[name], list(checks), name)
                return real(name, checks)
            return recording
        rc, err, receipt, after = self._drive(dict(self.PRE), wraps={'gate': wrap})
        self.assertEqual(rc, 0, err)
        self.assertEqual(calls, GATES)

    def test_each_named_check_refuses_on_its_own(self):
        for name, checks in GATES.items():
            for check in checks:
                with self.subTest(gate=name, check=check):
                    state = {'flipped': False}

                    def wrap(real, m, _n=name, _c=check, _s=state):
                        def flipping(gname, gchecks):
                            if gname == _n and not _s['flipped']:
                                self.assertIn(_c, gchecks)
                                self.assertIs(gchecks[_c], True, 'not True on the pristine inputs')
                                gchecks[_c] = False
                                _s['flipped'] = True
                            return real(gname, gchecks)
                        return flipping
                    d = dict(self.PRE)
                    rc, err, receipt, after = self._drive(d, wraps={'gate': wrap})
                    self.assertTrue(state['flipped'])
                    if name in AFTER_WRITE_GATES:
                        self.assertEqual(rc, 2, err[:500])
                        self.assertIsNone(receipt)
                        if name == 'artifact':
                            for k in REL:
                                self.assertEqual(after[k], d[k], k)
                    else:
                        self._assert_refused_unchanged(d, rc, err, receipt, after,
                                                       '%s.%s flipped' % (name, check))
                        self.assertFalse((self._tmp / ARTIFACT).exists(),
                                         'the artifact was written before %s' % name)
                    self.assertIn('refusing', err)

    def test_the_gate_refuses_an_empty_or_non_boolean_check_set(self):
        m = _load_tool()
        self.assertIs(m.gate('x', {}), False)
        self.assertIs(m.gate('x', {'a': 1}), False)
        self.assertIs(m.gate('x', {'a': True, 'b': [1]}), False)
        self.assertIs(m.gate('x', {'a': True}), True)

    def test_every_named_check_has_a_liveness_entry_and_each_named_test_exists(self):
        pairs = {(g, c) for g, cs in GATES.items() for c in cs}
        self.assertEqual(set(LIVENESS), pairs)
        for (g, c), test in LIVENESS.items():
            if test is None:
                continue
            with self.subTest(gate=g, check=c):
                self.assertTrue(any(hasattr(cls, test) for cls in
                                    (RepairAmendmentV2WitnessTests, GateTests)), test)


class ProseTests(unittest.TestCase):
    """The prose says what the code performs: every closed name it uses is read back from
    the code, root's three cases are there, and the predecessor's withdrawn wording is not."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load_tool()
        import lab_eventlog
        import lab_orchestrator
        import lab_server
        import build_live_ab_results
        cls.ev, cls.orch, cls.srv, cls.bld = (lab_eventlog, lab_orchestrator, lab_server,
                                              build_live_ab_results)

    def all_text(self):
        return ''.join(i.text.decode() for i in self.m.INSERTIONS)

    def test_the_restart_cap_cases_are_the_codes(self):
        text = self.m.P_5_3
        named = re.findall(r'\*\* \(`(\w+)`\)', text)
        self.assertEqual(named, list(self.ev.RESTART_CAP_CASES[1:]))
        self.assertIn('`none`', self.m.P_16)
        for case in self.ev.RESTART_CAP_CASES:
            self.assertIn('`%s`' % case, self.m.P_16)

    def test_roots_three_cases_and_no_withdrawn_wording(self):
        t = self.m.P_5_3
        for phrase in ('**(a) Before a valid decision**',
                       '**(b) After a valid, logged and externally receipted decision**',
                       '**(c) While a logged decision awaits its blocking receipt**',
                       'stands at its original `tau`', 'no new deploy or harm decision is made',
                       'No band, score, `n`, decision time or claim of the earlier prefix is revised',
                       'not a valid abstention', '**Cap invariance.**',
                       '`trial_paused(anchor_unavailable)`, with the abort still owed'):
            self.assertIn(phrase, t)
        for withdrawn in ('not reportable: trial incomplete (restart cap)', "Provisional, pending",
                          'question (i)', 'no freeze may be made while'):
            self.assertNotIn(withdrawn, self.all_text())

    def test_control_the_predecessor_prose_fails_the_same_checks(self):
        try:
            pred = _blob(PRED_HEAD, 'experiments/live_ab_tools/repair_amendment.py').decode()
        except (OSError, subprocess.CalledProcessError) as e:
            self.skipTest('the predecessor commit is not available: %s' % e)
        self.assertNotIn('**(a) Before a valid decision**', pred)
        self.assertIn('not reportable: trial incomplete (restart cap)', pred)
        self.assertIn('on the `_prefreeze` chain', pred)

    def test_the_receipt_reject_reasons_and_worker_states_are_the_enums(self):
        reasons = re.findall(r'`(\w+)`', self.m.P_12_2.split('| 30 |', 1)[1].split('|')[1])
        self.assertEqual(sorted(set(reasons) & set(self.ev.E_RECEIPT_REJECT.enum)),
                         sorted(self.ev.E_RECEIPT_REJECT.enum))
        states = re.findall(r'`(\w+)`', self.m.P_12_2.split('| 29 |', 1)[1].split('|')[1])
        self.assertEqual([s for s in states if s in self.ev.WORKER_STATES],
                         list(self.ev.WORKER_STATES))
        for r in self.ev.E_RECEIPT_REJECT.enum:
            self.assertIn('`%s`' % r, self.m.P_12_4)

    def test_the_start_stages_and_the_first_start_map_are_the_code(self):
        self.assertEqual(tuple(self.srv.START_STAGES),
                         ('gguf', 'serving_manifest', 'launch', 'health', 'identity', 'smoke'))
        for stage in self.srv.START_STAGES:
            self.assertIn('`%s`' % stage, self.m.P_5_3)
        self.assertEqual(self.orch.START_FAILURE_REASON,
                         {'gguf': 'server_identity', 'serving_manifest': 'server_identity',
                          'identity': 'server_identity', 'smoke': 'receipt_mismatch',
                          'launch': 'infrastructure', 'health': 'infrastructure'})
        self.assertIn('a `gguf`, `serving_manifest` or `identity` failure is 6.4 row 6', self.m.P_5_3)
        self.assertIn('`launch` or `health` dispatches nothing and ends the trial as', self.m.P_5_3)

    def test_the_abort_reasons_the_preflight_code_and_the_chains_are_the_schema(self):
        text = self.all_text()
        for reason in set(re.findall(r'trial_aborted\((\w+)\)', text)):
            with self.subTest(reason=reason):
                self.assertIn(reason, self.ev.E_ABORT_REASON.enum)
        self.assertIn('golden_objects', self.ev.E_PREFLIGHT.enum)
        self.assertIn('server_start_failed', self.ev.TRIAL_ONLY_TYPES)
        self.assertIn('worker_resolved', self.ev.TRIAL_ONLY_TYPES)
        self.assertNotIn('anchor_receipt_rejected', self.ev.TRIAL_ONLY_TYPES)
        self.assertNotIn('anchor_receipt_rejected', self.ev.PROGRAM_ONLY_TYPES)
        self.assertIn('Rows 28 and 29 are written on a trial chain only.', self.m.P_12_2)
        self.assertIn('`worker_resolved` is a\ntrial-chain event', self.m.P_14_6)
        self.assertNotIn('_prefreeze` chain', self.m.P_14_6 + self.m.P_12_2 + self.m.A_4_4)
        for f in ('restart_cap_case', 'decision_status', 'arrivals_not_run', 'follow_up_not_run'):
            self.assertIn(f, self.ev.COMPLETION.fields)
        self.assertIn('usage_complete', self.ev.EVENT_SCHEMA['episode_revealed'])
        self.assertIn('unknown_usage_calls', self.ev.EVENT_SCHEMA['episode_revealed'])

    def test_the_artifact_path_and_the_builder_labels_are_the_code(self):
        import lab_serving_manifest as sm
        self.assertEqual(sm.TRACKED_RELPATH, 'results/live_ab/freeze/serving_manifest.json')
        self.assertIn('`%s`' % sm.TRACKED_RELPATH, self.m.P_2_2)
        self.assertIn(sm.ARTIFACT_NAME, self.m.A_2_2)
        self.assertIn('not a null result', self.bld.RESTART_CAP_INCOMPLETE_LABEL)
        self.assertTrue(self.bld.PROVISIONAL_LABEL.startswith('provisional'))

    def test_the_decision_receipt_evidence_is_the_codes(self):
        """Each piece of evidence 12.4 names is a problem code of
        lab_eventlog.decision_receipt_problems (its absence refuses)."""
        import inspect
        src = inspect.getsource(self.ev.decision_receipt_problems)
        for code in ('not_pushed', 'no_commit', 'no_anchor_file', 'no_comment_body',
                     'no_comment_id', 'no_node_id', 'no_created_at', 'no_updated_at',
                     'updated_before_created', 'request_unbound', 'request_mismatch'):
            self.assertIn("'%s'" % code, src)
        for phrase in ('`node_id`', '`created_at`', '`updated_at`', '`receipt_sha256`',
                       'No wall-clock equality and no latency window is imposed'):
            self.assertIn(phrase, self.m.P_12_4)

    def test_control_a_prose_naming_a_state_the_code_lacks_fails(self):
        mutated = self.m.P_12_2.replace('`alive_unresolved`', '`alive_forever`')
        states = re.findall(r'`(\w+)`', mutated.split('| 29 |', 1)[1].split('|')[1])
        self.assertNotEqual([s for s in states if s in self.ev.WORKER_STATES],
                            list(self.ev.WORKER_STATES))


class VerifierTests(_Harness, unittest.TestCase):
    """The independent verifier on the control drive's output: it must verify the amendment
    and must NOT verify its negative controls."""

    KEYS = {'CONFIG': 'config', 'ARCH': 'architecture', 'PROTO': 'protocol', 'CELLS': 'cells'}
    CHECKS = ['parent_is_the_reviewed_preimage', 'parent_config_bytes',
              'receipt_lists_exactly_the_expected_insertions',
              'receipt_sections_agree_with_the_verifier_headings',
              'receipt_lists_the_one_replacement', 'each_insertion_occurs_once',
              'value_replaced_once_per_document', 'reverting_the_changes_reproduces_the_parent',
              'each_insertion_under_the_verifier_heading', 'no_cr_byte',
              'three_blocks_byte_identical', 'config_parses', 'exactly_the_three_keys_added',
              'no_key_removed', 'only_the_serving_manifest_digest_changed_from_null',
              'server_supervision_is_the_contract_literal', 'prompts_are_the_receipt_texts',
              'engineering_acquisition_unchanged_and_root_table',
              'rule_block_before_and_after_is_cbfd1792', 'vocabulary_sections_identical', 'cells',
              'content_in_the_documents', 'artifact_is_canonical',
              'artifact_digest_is_the_config_digest', 'artifact_tokenized_as_the_main_checkout',
              'receipt_names_the_amended_protocol', 'receipt_written_digests_match',
              'receipt_names_the_withdrawn_predecessor',
              'withdrawn_receipts_are_the_pinned_bytes', 'withdrawn_commits_not_ancestors']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.HISTORY = {'receipts': dict(cls.PRED),
                       'ancestry': {c: False for c in set(PRED_RECEIPTS.values())}}
        cls.WITHDRAWN = {cls.KEYS[k]: _blob(PRED_HEAD, rel) for k, rel in REL.items()}

    def _amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        before = {self.KEYS[k]: v for k, v in self.PRE.items()}
        out = {self.KEYS[k]: v for k, v in after.items()}
        out['artifact'] = (self._tmp / ARTIFACT).read_bytes()
        return before, out, receipt

    def _reseal(self, after, receipt):
        receipt = json.loads(json.dumps(receipt))
        c = json.loads(after['cells'])
        c['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(after['protocol'])
        after = dict(after, cells=(json.dumps(c, indent=1) + '\n').encode('utf-8'))
        receipt['successor_provenance']['new_successor'] = sha(after['protocol'])
        receipt['written']['protocol_sha256'] = sha(after['protocol'])
        receipt['written']['config_sha256'] = sha(after['config'])
        receipt['written']['architecture_sha256'] = sha(after['architecture'])
        return after, receipt

    def test_the_verifier_re_derives_the_amendment(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, after, receipt, self.SUCC, self.HISTORY)
        self.assertIs(got['all_verified'], True, json.dumps(got['checks']))
        self.assertEqual(sum(got['insertions_listed'].values()), 27)
        self.assertEqual(list(got['checks']), self.CHECKS)
        ctl = v.negative_controls(before, after, receipt, self.SUCC, self.HISTORY, self.WITHDRAWN)
        self.assertIs(ctl['every_control_failed'], True, ctl)

    def test_each_verifier_check_is_load_bearing(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        real = v.verdict
        for name in self.CHECKS:
            with self.subTest(check=name):
                def flipping(checks, _n=name):
                    self.assertIs(checks[_n], True)
                    checks[_n] = False
                    return real(checks)
                with mock.patch.object(v, 'verdict', flipping):
                    got = v.verify(before, after, receipt, self.SUCC, self.HISTORY)
                self.assertIs(got['all_verified'], False)

    def test_each_verifier_check_can_fail_on_a_real_input(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        base = (before, after, receipt, self.SUCC, self.HISTORY)

        def rep(docs, old, new, which=('config', 'architecture', 'protocol')):
            return {d: (docs[d].replace(old, new, 1) if d in which else docs[d]) for d in docs}

        def with_receipt(fn):
            r = json.loads(json.dumps(receipt))
            fn(r)
            return (before, after, r, self.SUCC, self.HISTORY)

        def with_after(a):
            a, r = self._reseal(a, receipt)
            return (before, a, r, self.SUCC, self.HISTORY)
        row = next(i for i in receipt['insertions'] if i['key'] == 'protocol.13_1')
        k = after['protocol'].index(b'## 1. Purpose, scope')
        k = after['protocol'].index(b'\n\n', k) + 2
        t = next(i for i in receipt['insertions'] if i['key'] == 'protocol.14_6')['text'].encode()
        p = after['protocol'].replace(t, b'', 1)
        h = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        j = p.index(h) + len(h)
        fb, eb, _ = v.fence_block(before['architecture'], v.FENCE_MARKERS['architecture'])
        fa, ea, _ = v.fence_block(after['architecture'], v.FENCE_MARKERS['architecture'])
        dg = SERVING_MANIFEST_SHA256.encode()
        variants = {
            'parent_is_the_reviewed_preimage': (dict(before, cells=before['cells'] + b' '),) + base[1:],
            'parent_config_bytes': (dict(before, config=before['config'] + b' '),) + base[1:],
            'receipt_lists_exactly_the_expected_insertions': with_receipt(
                lambda r: r['insertions'].pop()),
            'receipt_sections_agree_with_the_verifier_headings': with_receipt(
                lambda r: r['insertions'][-1].__setitem__('section', '### 7.2 What is fsynced')),
            'receipt_lists_the_one_replacement': with_receipt(
                lambda r: r['replacement'].__setitem__('old_value', 'x')),
            'each_insertion_occurs_once': with_after(dict(after, protocol=after['protocol']
                                                          + row['text'].encode())),
            'value_replaced_once_per_document': with_after(dict(
                after, protocol=after['protocol'] + b'\n"serving_manifest_sha256": "' + dg + b'"}\n')),
            'reverting_the_changes_reproduces_the_parent': with_after(
                dict(after, protocol=after['protocol'] + b'\nextra\n')),
            'each_insertion_under_the_verifier_heading': with_after(dict(after, protocol=p[:j] + t + p[j:])),
            'no_cr_byte': with_after(dict(after, protocol=after['protocol'] + b'\r\n')),
            'three_blocks_byte_identical': with_after(dict(
                after, architecture=after['architecture'][:fa] + before['architecture'][fb:eb]
                + after['architecture'][ea:])),
            'config_parses': with_after(dict(after, config=b'{')),
            'exactly_the_three_keys_added': with_after(rep(after, b'"pause_thresholds":',
                                                           b'"pause_threshold":')),
            'no_key_removed': with_after(rep(after, b'"pause_thresholds":', b'"pause_threshold":')),
            'only_the_serving_manifest_digest_changed_from_null': with_after(
                rep(after, b'"battery_percent": 20', b'"battery_percent": 21')),
            'server_supervision_is_the_contract_literal': with_after(rep(
                after, b'"max_supervised_restarts_per_server_per_trial": 3',
                b'"max_supervised_restarts_per_server_per_trial": 4', ('config',))),
            'prompts_are_the_receipt_texts': with_receipt(
                lambda r: r['conformance_prompts']['2_texts'][0].__setitem__('prompt', 'x')),
            'engineering_acquisition_unchanged_and_root_table': with_after(rep(
                after, b'"wall_seconds_total": 600', b'"wall_seconds_total": 601', ('config',))),
            'rule_block_before_and_after_is_cbfd1792': with_after(rep(
                after, b'"consecutive_infrastructure_failures": 10',
                b'"consecutive_infrastructure_failures": 11')),
            'vocabulary_sections_identical': with_after(dict(
                after, protocol=after['protocol'][:k] + b'X' + after['protocol'][k:])),
            'cells': (before, after, receipt, b'not the 48f4d70 protocol', self.HISTORY),
            'content_in_the_documents': with_after(rep(
                after, b'**(a) Before a valid decision**', b'**(a) Before any decision**',
                ('protocol',))),
            'artifact_is_canonical': (before, dict(after, artifact=after['artifact'] + b'\n'),
                                      receipt, self.SUCC, self.HISTORY),
            'artifact_digest_is_the_config_digest': with_receipt(
                lambda r: r['serving_manifest'].__setitem__('sha256_canonical', '0' * 64)),
            'artifact_tokenized_as_the_main_checkout': (
                before, dict(after, artifact=after['artifact'].replace(b'<REPO>/work', b'<HOME>/work')),
                receipt, self.SUCC, self.HISTORY),
            'receipt_names_the_amended_protocol': with_receipt(
                lambda r: r['successor_provenance'].__setitem__('new_successor', '0' * 64)),
            'receipt_written_digests_match': with_receipt(
                lambda r: r['written'].__setitem__('protocol_sha256', '0' * 64)),
            'receipt_names_the_withdrawn_predecessor': with_receipt(
                lambda r: r['withdrawn_predecessor'].__setitem__('status', 'withdrawn')),
            'withdrawn_receipts_are_the_pinned_bytes': base[:4] + (
                dict(self.HISTORY, receipts={}),),
            'withdrawn_commits_not_ancestors': base[:4] + (
                dict(self.HISTORY, ancestry={c: True for c in self.HISTORY['ancestry']}),),
        }
        self.assertEqual(sorted(variants), sorted(self.CHECKS))
        for name, args in variants.items():
            with self.subTest(check=name):
                got = v.verify(*args)
                self.assertIs(got['checks'][name], False)
                self.assertIs(got['all_verified'], False)

    def test_the_predecessor_documents_do_not_verify(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, dict(self.WITHDRAWN, artifact=after['artifact']), receipt,
                       self.SUCC, self.HISTORY)
        self.assertIs(got['all_verified'], False)
        self.assertIs(got['checks']['content_in_the_documents'], False)

    def test_the_real_amendment_commit_verifies_if_present(self):
        """After the amendment is committed: the verifier's main() on the commit that ADDS a
        REPAIR_AMENDMENT_V2_RECEIPT, with the runtime re-check. Skipped before it exists."""
        log = subprocess.run(['git', '-C', str(REPO), 'log', '--diff-filter=A', '--format=%H',
                              '--name-only', '--', 'results/live_ab/'],
                             capture_output=True, text=True)
        commit, cur = None, None
        for line in log.stdout.splitlines() if log.returncode == 0 else ():
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                cur = line
            elif line.startswith('results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_'):
                commit = cur
                break
        if commit is None:
            self.skipTest('no commit in this history adds a v2 receipt')
        v = _load_verifier()
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = v.main([commit, '--runtime'])
        self.assertEqual(rc, 0, err.getvalue())


class RealManifestTests(unittest.TestCase):
    """The committed artifact against the real durable build, as seen from the main checkout
    (a dry check: lab_serving_manifest.verify_before_launch, the function preflight and every
    lab_server start and restart call; no server is started), and a mutated copy refused."""

    @classmethod
    def setUpClass(cls):
        cls.art = REPO / ARTIFACT
        if not cls.art.exists():
            raise unittest.SkipTest('the artifact %s is not in this checkout yet' % ARTIFACT)
        if not MAIN_LAUNCHER.is_file():
            raise unittest.SkipTest('the durable build of the main checkout is not on this host')
        import lab_serving_manifest as sm
        import assemble_serving_manifest as asm
        cls.sm, cls.asm = sm, asm
        cfg = json.loads((REPO / REL['CONFIG']).read_text('utf-8'))
        cls.digest = cfg['llama_cpp']['serving_manifest_sha256']
        cls.commit = cfg['llama_cpp']['commit']

    def _verify(self, path, expected, root=MAIN):
        with self.asm.repo_roots(root):
            _m, labels = self.sm.verify_before_launch(path, expected, launcher=MAIN_LAUNCHER,
                                                      llama_commit=self.commit)
        return labels

    def test_the_committed_artifact_is_the_config_digest_and_verifies_from_the_main_checkout(self):
        obj, digest, problems = self.sm.read_artifact(self.art.absolute())
        self.assertEqual(problems, [])
        self.assertEqual(digest, self.digest)
        self.assertEqual(digest, SERVING_MANIFEST_SHA256)
        self.assertEqual(self._verify(self.art.absolute(), self.digest), [])

    def test_a_mutated_copy_is_refused_by_digest_and_by_the_runtime(self):
        obj = json.loads(self.art.read_bytes())
        lib = obj['libraries'][0]
        new = ('0' if lib['sha256'][0] != '0' else '1') + lib['sha256'][1:]
        for rec in [lib] + [f for f in obj['closure']['files'] if f['path'] == lib['name']] \
                + [m for m in obj['build']['receipt_members'] if m['path'] == lib['name']]:
            rec['sha256'] = new
        self.assertEqual(self.sm.structure_problems(obj, self.commit), [])
        tmp = Path(tempfile.mkdtemp(prefix='repair_v2_mutated_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        path = self.sm.artifact_path(tmp / 'freeze')
        own = self.sm.write_artifact(path, obj)
        self.assertEqual(self._verify(path, self.digest), ['digest'])
        labels = self._verify(path, own)
        self.assertTrue(any(x.startswith('library_sha256:') for x in labels), labels)

    def test_the_committed_artifact_is_refused_as_seen_from_another_checkout(self):
        root = os.path.realpath(str(REPO))
        if root == MAIN:
            self.skipTest('running inside the main checkout itself')
        labels = self._verify(self.art.absolute(), self.digest, root=None)
        self.assertIn('launcher_path', labels)

    def test_the_assembler_cli_reproduces_the_digest_only_as_seen_from_the_main_checkout(self):
        argv = ['--build-dir', str(Path(MAIN) / 'work/llama.cpp-build/build'),
                '--build-receipt', str(Path(MAIN) / 'results/live_ab/DURABLE_REBUILD_20260923T192024Z.json'),
                '--patch', str(Path(MAIN) / 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch')]

        def run(extra):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = self.asm.main(argv + extra)
            return rc, json.loads(out.getvalue())
        rc, got = run(['--repo-root', MAIN])
        self.assertEqual(rc, 0, got)
        self.assertEqual(got['serving_manifest_sha256'], SERVING_MANIFEST_SHA256)
        self.assertIsNone(got['out'])
        rc_here, here = run([])
        self.assertEqual(rc_here, 0, here)
        same_checkout = os.path.realpath(str(REPO)) == MAIN
        self.assertEqual(here['serving_manifest_sha256'] == SERVING_MANIFEST_SHA256, same_checkout)


class AssemblerRepoRootTests(unittest.TestCase):
    """assemble_serving_manifest.repo_root_problems / repo_roots (the pinned repo-root
    parameter), each with its refusal."""

    @classmethod
    def setUpClass(cls):
        import assemble_serving_manifest as asm
        import lab_common
        cls.asm, cls.lc = asm, lab_common

    def test_this_checkout_is_a_valid_root_and_bad_roots_are_refused(self):
        root = os.path.realpath(str(REPO))
        self.assertEqual(self.asm.repo_root_problems(root), [])
        self.assertIn('repo_root_not_canonical', self.asm.repo_root_problems(root + '/'))
        self.assertIn('repo_root_not_canonical', self.asm.repo_root_problems('relative/path'))
        tmp = os.path.realpath(tempfile.mkdtemp(prefix='repair_v2_empty_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertEqual(self.asm.repo_root_problems(tmp), ['repo_root_no_lab_common'])

    def test_repo_roots_rebinds_exactly_three_roots_and_restores_them_on_an_exception(self):
        saved = (self.lc.REPO_ROOT, self.lc.RESULTS_ROOT, self.lc.WORK_ROOT, self.lc.FREEZE_DIR)
        with self.assertRaises(RuntimeError):
            with self.asm.repo_roots('/nonexistent/root'):
                self.assertEqual(self.lc.tokenize_path('/nonexistent/root/work/x'), '<REPO>/work/x')
                self.assertEqual(self.lc.tokenize_path('/nonexistent/root/results/live_ab/y'),
                                 '<RESULTS>/y')
                raise RuntimeError('boom')
        self.assertEqual((self.lc.REPO_ROOT, self.lc.RESULTS_ROOT, self.lc.WORK_ROOT,
                          self.lc.FREEZE_DIR), saved)
        with self.asm.repo_roots(None):
            self.assertEqual(self.lc.REPO_ROOT, saved[0])

    def test_the_rebinding_reproduces_the_definitions_it_checks(self):
        for d in self.asm.ROOT_DEFINITIONS:
            self.assertEqual((REPO / 'experiments/live_ab/lab_common.py').read_text('utf-8')
                             .splitlines().count(d), 1, d)

    def test_the_cli_refuses_a_root_that_is_not_canonical(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = self.asm.main(['--build-dir', '/nonexistent', '--build-receipt', '/nonexistent.json',
                                '--repo-root', 'not/absolute'])
        self.assertEqual(rc, 2)
        self.assertIn('repo_root_not_canonical', out.getvalue())


def _real_sources_dir():
    names = ('sanitized-mbpp.json', 'HumanEval.jsonl.gz', 'mbpp.jsonl')
    dirs = [os.environ.get('LIVE_AB_SOURCES_DIR'), REPO / 'work' / 'local_stream' / 'data',
            REPO / 'work' / 'live_ab' / 'sources']
    found = {}
    for n in names:
        for dd in dirs:
            if dd and (Path(dd) / n).is_file():
                found[n] = Path(dd) / n
                break
    return found if len(found) == len(names) else None


class RealSourcesTests(unittest.TestCase):
    """Optional: the mechanical prompt check on the REAL pinned sources reproduces the
    receipt's maxima (and the withdrawn predecessor's: the prompts did not change)."""

    def test_the_recorded_similarity_maxima_are_reproduced(self):
        found = _real_sources_dir()
        if found is None:
            self.skipTest('the three pinned roster sources are not on this host '
                          '(set LIVE_AB_SOURCES_DIR)')
        receipts = sorted((REPO / 'results' / 'live_ab').glob(RECEIPT_GLOB))
        if not receipts:
            self.skipTest('no v2 receipt in this checkout')
        tmp = Path(tempfile.mkdtemp(prefix='repair_v2_real_sources_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for n, p in found.items():
            shutil.copyfile(p, tmp / n)
        m = _load_tool()
        pins = json.loads(_blob(PRE_REV, REL['CONFIG']))['roster']['sources']
        got = m.check_prompts(m.load_sources(tmp, pins), list(SMOKE))
        self.assertIs(got['all_pass'], True)
        wants = [json.loads(p.read_bytes()) for p in receipts]
        try:
            wants.append(json.loads(_blob(PRED_HEAD, list(PRED_RECEIPTS)[1])))
        except (OSError, subprocess.CalledProcessError):
            pass
        for w in wants:
            want = w['conformance_prompts']['3_mechanical_check_results']
            for g, x in zip(got['per_prompt'], want['per_prompt']):
                for key in ('id', 'max_jaccard', 'closest_source_uid', 'max_jaccard_smoke_tasks',
                            'closest_smoke_task', 'normalized_equal_to', 'prompt_sha256'):
                    self.assertEqual(g[key], x[key], (g['id'], key))
        with gzip.open(tmp / 'HumanEval.jsonl.gz', 'rt') as fh:
            self.assertEqual(sum(1 for line in fh if line.strip()), 164)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
