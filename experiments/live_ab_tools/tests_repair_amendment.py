"""Witnesses for the repair amendment tool (root 20:40 items 2 and 4), correction run.

HOW EVERY CASE RUNS
  The PRE-amendment blobs (`git show b049307:<path>`, read-only, once per class)
  are copied into a fresh temporary directory. A fresh instance of the tool is
  loaded, and its module paths (REPO, CONFIG, ARCH, PROTO, CELLS) are re-pointed
  at the copies. The harness asserts that each re-pointed path lies under the
  temporary directory. The tool's `subprocess` (git rev-parse and git show) is
  replaced in that instance only, `lab_common.harness_file_hashes` is stubbed for
  the duration of the call, and the pinned roster sources are replaced by a small
  SYNTHETIC source set (so these witnesses need no gitignored data; the real
  sources are exercised by the one real run, recorded in its receipt, and by the
  optional class at the end). Then main() runs. The real documents are never
  opened for writing, and every drive compares their digests before and after.

WHAT A REFUSAL WITNESS SHOWS, AND WHAT IT DOES NOT (review finding 5 of commit
1349619: a test refused by an earlier or broader guard is no witness for a later
one, and many guards could be deleted with every test still green). Two
properties are witnessed separately:
  * AGGREGATION (GateTests): every refusal of main() goes through
    repair_amendment.gate(name, checks). The list of gates and of the checks in
    each is pinned here (GATES); for EVERY (gate, check) a drive on the pristine
    pre-images, on which every check is True, sets that one check False at gate()
    and main() must refuse and write nothing. A check deleted from a gate, or a
    gate whose aggregation ignores a check, fails here.
  * LIVENESS (the LIVENESS table): which REAL input makes each check False. Each
    entry names the test that shows it, and that test asserts the check's own value
    False in the refusal it prints. Tests named `test_isolated_*` make ONLY that
    check False (the other checks of main() pass), which is what the review asked
    for the guards it named; the rest may make other checks False too. Checks that
    no real input can make alone False (implied by another check) or at all (a
    filesystem fault) say so in the table instead of naming a test.

Control that must pass: the pristine pre-images reproduce the delivered bytes
(config.json, ARCHITECTURE and the protocol exactly; cells.json exactly except the
new successor's recorded_utc, which is the time of the run); config.json equals the
withdrawn first run's (the correction changes prose only).

ProseCorrectionTests: the review's findings 1-4 and 7 on the delivered prose (each
fails on the withdrawn first run's texts and passes on these).
VerifierTests: the independent verifier (verify_repair_amendment.py): its own
heading map refuses the moved-paragraph exploit of finding 6; its check list is
pinned and each check is flipped at verdict(); real-input negative controls for the
pins, config diff, rule block and vocabulary; once the correction commit exists, its
main() is run on it.
RealSourcesTests (optional): the prompt check on the real pinned sources
reproduces the receipt's similarity maxima.

SCOPE: this needs the repository's git history (b049307 and 1349619). Without it the
classes are skipped, and the skip names the reason. Nothing here runs a model,
server, build or network request.
"""

from __future__ import annotations

import contextlib
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
TOOL = HERE / 'repair_amendment.py'
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json'}
#: the revision holding the reviewed pre-images (main before this amendment)
PRE_REV = 'b049307ff62153a054f61b6179291ba987de2ba1'
#: the withdrawn first run of the tool, and its kept receipt
WITHDRAWN_REV = '134961944cec6e83f2b27586cda3d1f42ba40b72'
WITHDRAWN_RECEIPT = 'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json'
REVIEWED = {'CONFIG': 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824',
            'ARCH': '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab',
            'PROTO': '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b',
            'CELLS': '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'}
#: the delivered documents, and the delivered cells.json with the new successor's
#: recorded_utc replaced by RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED = {'CONFIG': 'c323e0f26e7cba68355083a104e6397097f446f5e4532eb23edea57952ebd850',
             'ARCH': '78a4a1c72f00c594ef091227f8dbf99e300f856b82e50eed76c73e740bae6846',
             'PROTO': '5d108b4a1a8d076fdd79b973834b8f3b3e4604526a9d90e943329c9cbf2fc2b8'}
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    '1ad19ecd2973470da56265475c3daa2972129434b2053198f3840f102d82a90c')
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
SMOKE = ('mbpp_full/39', 'mbpp_full/122', 'mbpp_full/522', 'mbpp_full/547',
         'mbpp_full/869', 'mbpp_full/966')
RECEIPT_GLOB = 'REPAIR_AMENDMENT_CORRECTION_RECEIPT_*.json'

#: every gate of main() and the checks in each, in order (the aggregation witness)
GATES = {
    'pins': ['config_is_the_reviewed_preimage', 'architecture_is_the_reviewed_preimage',
             'protocol_is_the_reviewed_preimage', 'cells_is_the_reviewed_preimage',
             'no_cr_byte', 'three_way_contract_before', 'rule_block_before_is_the_pin',
             'cells_round_trips', 'cells_original_pin_untouched',
             'cells_current_successor_is_the_prior_successor',
             'cells_successor_supersedes_the_original', 'cells_prior_successor_count'],
    'anchors': ['every_anchor_once', 'no_anchor_error', 'every_anchor_inside_its_section',
                'inserted_text_form'],
    'prompt': ['build_user_prompt_takes_the_non_mbpp_branch', 'shape_ok',
               'normalized_equal_to_no_source', 'max_jaccard_below_threshold',
               'max_jaccard_smoke_tasks_below_threshold', 'entry_point_defined_in_no_source',
               'sources_compared'],
    'prompts': ['every_prompt_passes', 'ids_are_oodp_1_to_4', 'distinct_among_themselves',
                'no_smoke_task_missing', 'fields_are_exactly'],
    'config': ['exactly_the_three_keys_added', 'no_key_removed', 'no_key_changed',
               'server_supervision_is_the_contract_value',
               'conformance_prompts_equal_the_tool_texts', 'pinned_subtrees_unchanged',
               'engineering_acquisition_equals_run_smoke_BOUND_LIMITS',
               'rule_block_before_is_the_pin', 'rule_block_after_is_the_pin',
               'deleting_the_insertions_reproduces_the_prior_config'],
    'postconditions': ['deleting_the_inserted_text_reproduces_each_preimage',
                       'every_insertion_inside_its_section_beside_its_anchor',
                       'no_cr_byte_after', 'three_way_contract_after',
                       'vocabulary_sections_1_3_11_byte_identical', 'config',
                       'every_document_changed'],
    'negative_control': ['every_variant_refused_on_placement', 'scratch_copies_unchanged',
                         'real_documents_unchanged'],
    'successor_commit': ['prior_successor_commit_carries_the_prior_successor'],
    'cells': ['cells_unchanged_outside_superseded_by'],
}

#: (gate, check) -> the test whose real input makes that check False, or None with the
#: reason no real input does. 'test_isolated_*' tests make that check ALONE False.
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
        'test_isolated_the_anchor_upper_bound_refuses_an_interloper_heading',
    ('anchors', 'inserted_text_form'): 'test_an_inserted_text_of_the_wrong_form_is_refused',
    ('prompt', 'build_user_prompt_takes_the_non_mbpp_branch'):
        'test_isolated_a_prompt_the_builder_does_not_route_is_refused',
    ('prompt', 'shape_ok'): 'test_isolated_a_prompt_that_is_not_a_bare_signature_is_refused',
    ('prompt', 'normalized_equal_to_no_source'):
        'test_a_source_prompt_equal_to_a_conformance_prompt_is_refused',
    ('prompt', 'max_jaccard_below_threshold'):
        'test_a_source_prompt_too_similar_to_a_conformance_prompt_is_refused',
    # IMPLIED by max_jaccard_below_threshold: the six smoke tasks are source records
    # (a missing one refuses via no_smoke_task_missing), so the smoke maximum never
    # exceeds the all-sources maximum; the named test makes both False.
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
    ('config', 'exactly_the_three_keys_added'): 'test_a_key_placed_inside_the_rule_block_is_refused',
    ('config', 'no_key_removed'): 'test_each_faulty_config_inserter_is_refused',
    ('config', 'no_key_changed'): 'test_each_faulty_config_inserter_is_refused',
    ('config', 'server_supervision_is_the_contract_value'):
        'test_each_faulty_config_inserter_is_refused',
    ('config', 'conformance_prompts_equal_the_tool_texts'):
        'test_each_faulty_config_inserter_is_refused',
    ('config', 'pinned_subtrees_unchanged'): 'test_isolated_a_pinned_subtree_key_is_refused',
    ('config', 'engineering_acquisition_equals_run_smoke_BOUND_LIMITS'):
        'test_isolated_engineering_acquisition_that_differs_from_BOUND_LIMITS_is_refused',
    # IMPLIED in main() by pins.rule_block_before_is_the_pin, which refuses first;
    # the named unit test calls config_checks() on such a pre-image directly.
    ('config', 'rule_block_before_is_the_pin'):
        'test_config_checks_refuses_a_pre_image_rule_block_that_is_not_the_pin',
    ('config', 'rule_block_after_is_the_pin'): 'test_isolated_a_rule_block_key_is_refused',
    ('config', 'deleting_the_insertions_reproduces_the_prior_config'):
        'test_a_key_placed_inside_the_rule_block_is_refused',
    ('postconditions', 'deleting_the_inserted_text_reproduces_each_preimage'):
        'test_an_inserter_that_also_edits_vocabulary_section_1_is_refused',
    ('postconditions', 'every_insertion_inside_its_section_beside_its_anchor'):
        'test_isolated_the_section_upper_bound_refuses_an_interloper_heading',
    ('postconditions', 'no_cr_byte_after'): 'test_each_faulty_config_inserter_is_refused',
    ('postconditions', 'three_way_contract_after'):
        'test_isolated_a_missing_appendix_b_copy_breaks_only_the_contract',
    ('postconditions', 'vocabulary_sections_1_3_11_byte_identical'):
        'test_isolated_an_insertion_in_section_1_is_refused',
    ('postconditions', 'config'): 'test_a_key_placed_inside_the_rule_block_is_refused',
    # IMPLIED in main(): an unchanged document carries none of its insertions, which
    # the additivity and contract checks refuse; the unit test calls postconditions().
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
}

_loaded = [0]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _blob(rev: str, rel: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, rel)],
                          capture_output=True, check=True).stdout


def _load_tool():
    _loaded[0] += 1
    spec = importlib.util.spec_from_file_location(
        'repair_amendment_under_test_%d' % _loaded[0], TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _real_digests() -> dict:
    out = {k: sha((REPO / rel).read_bytes()) for k, rel in REL.items()}
    out['results/live_ab'] = sorted(p.name for p in (REPO / 'results' / 'live_ab').iterdir())
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


class _DriveHarness:
    """setUpClass, _drive, _assert_refused_unchanged and _repoint, shared by the
    witness classes and the verifier class (a mixin: it defines no test)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history holding %s is not available here: %s'
                                    % (PRE_REV[:7], e))

    # -- harness -------------------------------------------------------------
    def _drive(self, docs, patch=None, wrap_insert_all=None, commit_protocol=None,
               sources=None, wraps=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        ``wraps``: {attribute: fn(real, module) -> replacement}. Returns (exit code,
        stderr, receipt or None, bytes of the four files after)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='repair_witness_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, rel in REL.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(docs[k])
        (tmp / 'results' / 'live_ab').mkdir(parents=True)
        m = _load_tool()
        m.REPO = tmp
        for k, rel in REL.items():
            setattr(m, k, tmp / rel)
        src = synthetic_sources() if sources is None else sources
        m.load_sources = (src if callable(src) else (lambda d, pins, _s=src: _s))
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
        shown = docs['PROTO'] if commit_protocol is None else commit_protocol

        def fake_run(argv, *a, **kw):
            if argv[:1] == ['git'] and 'rev-parse' in argv:
                return types.SimpleNamespace(stdout='0' * 40 + '\n', returncode=0)
            if argv[:1] == ['git'] and 'show' in argv:
                return types.SimpleNamespace(stdout=shown, returncode=0)
            raise AssertionError('unexpected subprocess call: %r' % (argv,))
        m.subprocess = types.SimpleNamespace(run=fake_run)
        err = io.StringIO()
        with mock.patch.object(m.lab_common, 'harness_file_hashes',
                               return_value={'config.json': 'stub'}), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = m.main(['--sources-dir', str(tmp / 'no_sources_needed')])
        receipts = sorted((tmp / 'results' / 'live_ab').glob(RECEIPT_GLOB))
        receipt = json.loads(receipts[0].read_bytes()) if receipts else None
        after = {k: (tmp / rel).read_bytes() for k, rel in REL.items()}
        self.assertEqual(_real_digests(), before_real,
                         'a real document or results/live_ab changed during the drive')
        return rc, err.getvalue(), receipt, after

    def _assert_refused_unchanged(self, docs, rc, err, receipt, after, why):
        self.assertEqual(rc, 2, '%s: expected a refusal, got exit %r (%s)' % (why, rc, err[:500]))
        self.assertIsNone(receipt, '%s: a receipt was written' % why)
        for k in REL:
            self.assertEqual(after[k], docs[k], '%s: %s was changed' % (why, k))

    def _repoint(self, docs, **new):
        """``docs`` with the given documents replaced, and every pin (and cells.json's
        current successor) re-pointed at them, so that no pin refuses them. Returns
        (docs, patch, commit_protocol) for _drive."""
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
        """``check`` is False in ``gate_json`` and every other check there is True."""
        self.assertIs(gate_json[check], False, '%s: %s' % (why, gate_json))
        others = {k: v for k, v in gate_json.items() if k != check}
        self.assertTrue(all(v is True for v in others.values()), '%s: %s' % (why, others))

    @staticmethod
    def _extra(m, key, doc, anchor, side, text, section=None, section_end=None, fence=False):
        return m.Insertion(key, doc, anchor, side, text, section, section_end, fence)

    def _probe_config_key(self, m, anchor: bytes, line: bytes):
        """Three extra insertions of one configuration line, byte-identical in config.json,
        ARCHITECTURE 6.1 and Appendix B (so additivity, placement and the contract hold)."""
        a61 = (m.ARCH_MARKER, b'### 6.2 The rule block')
        appb = (b'## Appendix B.', b'## Appendix C.')
        return (self._extra(m, 'probe.config', 'config', anchor, 'before', line),
                self._extra(m, 'probe.arch', 'architecture', anchor, 'before', line, *a61,
                            fence=True),
                self._extra(m, 'probe.proto', 'protocol', anchor, 'before', line, *appb,
                            fence=True))


class RepairAmendmentWitnessTests(_DriveHarness, unittest.TestCase):

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(len(self.PRE['CONFIG']), 13917)
        self.assertEqual(m.PRIOR_CONFIG_SHA256, REVIEWED['CONFIG'])
        self.assertEqual(m.PRIOR_CONFIG_BYTES, 13917)
        self.assertEqual(m.PRIOR_ARCH_SHA256, REVIEWED['ARCH'])
        self.assertEqual(m.PRIOR_SUCCESSOR, REVIEWED['PROTO'])
        self.assertEqual(m.PRIOR_CELLS_SHA256, REVIEWED['CELLS'])
        self.assertEqual(m.PRIOR_RULE_BLOCK, RULE_BLOCK)
        self.assertEqual(m.PRIOR_SUCCESSOR_COMMIT, '48f4d70fbd580df282b551506448457a09ab514d')
        self.assertTrue(all(v.count(b'\r') == 0 for v in self.PRE.values()))
        cells = json.loads(self.PRE['CELLS'])
        self.assertEqual(len(cells['provenance']['vocabulary_alignment']['superseded_by']
                             ['prior_successors']), 5)

    # -- control: the pristine pre-images pass and reproduce the delivery ----
    def test_control_the_pristine_pre_images_reproduce_the_delivered_bytes(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        for k, want in DELIVERED.items():
            self.assertEqual(sha(after[k]), want, k)
        m = _load_tool()
        for k, doc in (('CONFIG', 'config'), ('ARCH', 'architecture'), ('PROTO', 'protocol')):
            self.assertEqual(m.remove_all(after[k], doc), self.PRE[k], k)
        self.assertEqual(_normalized_cells(after['CELLS']), DELIVERED_CELLS_NORMALIZED_SHA256)
        post = receipt['postcondition_checked']
        self.assertTrue(all(post['every_insertion_inside_its_section_beside_its_anchor']
                            .values()))
        self.assertEqual(len(post['every_insertion_inside_its_section_beside_its_anchor']), 19)
        self.assertEqual(post['deleting_the_inserted_text_reproduces_each_preimage'],
                         {'config': True, 'architecture': True, 'protocol': True})
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertEqual(post['vocabulary_sections_1_3_11_byte_identical'],
                         {'1': True, '3': True, '11': True})
        self.assertEqual(post['config']['rule_block_sha256_after'], RULE_BLOCK)
        self.assertIs(post['config']['engineering_acquisition_equals_run_smoke_BOUND_LIMITS'],
                      True)
        self.assertEqual(post['config']['added_keys'], m.ADDED_CONFIG_KEYS)
        control = receipt['negative_control']
        self.assertIs(control['every_variant_refused_on_placement'], True)
        self.assertEqual(control['variants_run'], 17)
        cfg = json.loads(after['CONFIG'])
        self.assertEqual(cfg['server_supervision'],
                         {'max_supervised_restarts_per_server_per_trial': 3,
                          'on_exceeding': 'abort_trial_incomplete'})
        self.assertEqual([p['id'] for p in cfg['prefreeze']['conformance_prompts']],
                         ['oodp/1', 'oodp/2', 'oodp/3', 'oodp/4'])
        cp = receipt['conformance_prompts']
        self.assertEqual(sorted(cp), ['1_selection_rule', '2_texts',
                                      '3_mechanical_check_results'])
        # the correction: config.json as in the withdrawn first run, which is named
        self.assertEqual(sha(after['CONFIG']), receipt['corrects']['config_sha256'])
        self.assertIs(receipt['written']['config_equals_the_withdrawn_first_run'], True)
        self.assertEqual(receipt['corrects'], m.WITHDRAWN_FIRST_RUN)
        self.assertEqual([c['finding'] for c in receipt['corrects']['corrections']],
                         [1, 2, 3, 4, 5, 6, 7])
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(sb['sha256'], DELIVERED['PROTO'])
        self.assertNotEqual(sb['sha256'], m.WITHDRAWN_FIRST_RUN['protocol_sha256'])
        self.assertEqual(sb['supersedes'], m.ORIGINAL_PIN)
        self.assertTrue(sb['reason'].startswith('NOT Appendix-B-only:'))
        self.assertIn('reviews/prerun_bundle_go_nogo_20260923_2040.md', sb['ruling'])
        self.assertEqual(len(sb['prior_successors']), 6)
        last = sb['prior_successors'][5]
        self.assertEqual(last['sha256'], REVIEWED['PROTO'])
        self.assertEqual(last['changing_commit_of_this_successor'], m.PRIOR_SUCCESSOR_COMMIT)
        self.assertIn('git show 48f4d70:', last['changing_commit_note'])
        self.assertIn('/design/protocol_FINAL.md', last['changing_commit_note'])
        old_sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment'][
            'superseded_by']
        self.assertEqual(sb['prior_successors'][:5], old_sb['prior_successors'])
        self.assertEqual(sb['correction_to_the_owner_report'],
                         old_sb['correction_to_the_owner_report'])
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
        self.assertIn('"protocol": 1', err)
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

    # -- the pins of cells.json and the rule block ---------------------------------
    def test_each_cells_or_rule_block_precondition_refuses(self):
        """Each with every digest pin re-pointed, so the named check is what refuses."""
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
                    for k in ('CONFIG', 'ARCH', 'PROTO'):
                        self.assertEqual(self.PRE[k].count(anchor), 1, k)
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
        for key in ('protocol.5_3', 'protocol.6_4', 'protocol.14_6',
                    'architecture.7_1.rows_21a_21b', 'architecture.6_3',
                    'protocol.appendix_b.server_supervision'):
            with self.subTest(key=key):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=self._moving(key))
                self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved ' + key)
                self.assertIn('postcondition', err)
                self.assertIn('"%s": false' % key, err)
                self.assertIs(_printed(err)['gate'][
                    'every_insertion_inside_its_section_beside_its_anchor'], False)

    def test_only_the_section_bound_refuses_an_anchor_that_lies_in_14_7(self):
        """The '### 14.7' heading is moved above the 14.6 anchor paragraph, so the anchor,
        and the paragraph after it, lie in 14.7 while staying directly after the anchor.
        Pins re-pointed, anchor precondition disabled: of placement's bounds only j <= s1
        refuses it (the 14.7 heading ends 14.6 before the paragraph)."""
        p = self.PRE['PROTO']
        heading = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        self.assertEqual(p.count(heading), 1)
        without = p.replace(heading, b'', 1)
        k = without.index(b'**Aborts.** The automatic aborts of 6.4')
        altered = without[:k] + heading + without[k:]
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.14_6')
        facts = m.anchor_facts(altered, ins)
        self.assertIs(facts['inside_its_section'], False)          # the pre-check sees it
        real = m.anchor_facts
        patch['anchor_facts'] = lambda raw, i: dict(real(raw, i), inside_its_section=True)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor in 14.7')
        self.assertIn('postcondition', err)
        where = m.placement(m.insert_all({'config': d['CONFIG'], 'architecture': d['ARCH'],
                                          'protocol': altered})['protocol'], ins)
        self.assertIs(where['directly_beside_the_anchor'], True)
        self.assertIs(where['inside_its_section'], False)

    def _interloper(self):
        """The pre-image with a '### 5.3a' heading between the 5.3 anchor paragraph and
        '### 5.4': the 5.3 section now ends at 5.3a, not at its expected upper bound."""
        p = self.PRE['PROTO']
        h = b'### 5.4 Sampling parameters\n'
        self.assertEqual(p.count(h), 1)
        return p.replace(h, b'### 5.3a Interloper\n\nA heading nobody expected.\n\n' + h, 1)

    def test_isolated_the_anchor_upper_bound_refuses_an_interloper_heading(self):
        """anchor_facts' upper-bound check ALONE refuses: the 5.3 anchor lies inside
        [5.3, 5.3a), but that section does not end at '### 5.4'."""
        altered = self._interloper()
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.5_3')
        s0, s1 = m.section_span(altered, ins.section)
        self.assertTrue(s0 < m.anchor_offset(altered, ins) <= s1)    # inside, lower and upper
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'interloper, anchor')
        printed = _printed(err)
        self._refused_alone(printed['gate_anchors'], 'every_anchor_inside_its_section', 'anchor')
        self.assertTrue(all(v is True for v in printed['gate_pins'].values()))
        bad = [k for k, a in printed['anchors'].items() if a.get('inside_its_section') is False]
        self.assertEqual(bad, ['protocol.5_3'])

    def test_isolated_the_section_upper_bound_refuses_an_interloper_heading(self):
        """placement()'s upper-bound check ALONE refuses: the 5.3 paragraph lands inside
        [5.3, 5.3a) directly beside its anchor, but 5.3 no longer ends at '### 5.4'.
        The anchor precondition is disabled so that the postcondition is reached."""
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
        pl = printed['insertion_placement']['protocol.5_3']
        self.assertIs(pl['section_ends_at_its_upper_bound'], False)
        self.assertIs(pl['directly_beside_the_anchor'], True)
        s0, s1 = pl['section']
        self.assertTrue(s0 < pl['insert_at'] < s1)
        self.assertEqual([k for k, v in printed['every_insertion_inside_its_section_beside_its_anchor']
                          .items() if not v], ['protocol.5_3'])

    # -- anchors -----------------------------------------------------------------
    def test_an_absent_anchor_is_refused(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.5_3')
        altered = self.PRE['PROTO'].replace(ins.anchor, ins.anchor.replace(b'13.1.', b'13.1 '),
                                            1)
        d, patch, shown = self._repoint(self.PRE, PROTO=altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor absent')
        self.assertIn('"anchor_occurrences": 0', err)
        g = _printed(err)['gate_anchors']
        self.assertIs(g['every_anchor_once'], False)
        self.assertIs(g['no_anchor_error'], False)
        with self.assertRaises(ValueError):
            m.insert_all({'config': d['CONFIG'], 'architecture': d['ARCH'], 'protocol': altered})

    def test_a_duplicated_anchor_is_refused(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'architecture.7_1.row_20a')
        a = self.PRE['ARCH']
        k = a.index(b'### 7.2 What is fsynced')
        altered = a[:k] + ins.anchor + b'x |\n\n' + a[k:]
        d, patch, shown = self._repoint(self.PRE, ARCH=altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor twice')
        self.assertIn('"anchor_occurrences": 2', err)

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
        self.assertIn('"protocol": false', err)
        self.assertIn('"1": false', err)
        g = _printed(err)['gate']
        self.assertIs(g['deleting_the_inserted_text_reproduces_each_preimage'], False)
        self.assertIs(g['vocabulary_sections_1_3_11_byte_identical'], False)

    def test_isolated_an_insertion_in_section_1_is_refused(self):
        """A variant insertion list with one more PURE insertion, placed properly inside
        section 1: additivity, placement, contract and config all hold; only the
        vocabulary check refuses."""
        m = _load_tool()
        heading = b'## 1. Purpose, scope, the feasibility declaration, and the claim lists\n'
        self.assertEqual(self.PRE['PROTO'].count(heading), 1)
        probe = self._extra(m, 'probe.section_1', 'protocol', heading, 'after',
                            '\n*Probe paragraph inside section 1.*\n',
                            b'## 1. Purpose, scope', b'## 2. Systems')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': m.INSERTIONS + (probe,)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'section 1 insertion')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'vocabulary_sections_1_3_11_byte_identical', 'vocab')
        self.assertIs(printed['vocabulary_sections_1_3_11_byte_identical']['1'], False)

    def test_isolated_a_missing_appendix_b_copy_breaks_only_the_contract(self):
        """A variant insertion list without the Appendix B copy of server_supervision:
        every listed insertion is pure and placed, the config is right; only the
        three-way contract refuses."""
        m = _load_tool()
        fewer = tuple(i for i in m.INSERTIONS if i.key != 'protocol.appendix_b.server_supervision')
        self.assertEqual(len(fewer), len(m.INSERTIONS) - 1)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': fewer})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'no Appendix B copy')
        printed = _printed(err)
        self._refused_alone(printed['gate'], 'three_way_contract_after', 'contract')
        self.assertIs(printed['three_way_contract_after']['architecture_block_equals_protocol_block'],
                      False)

    def test_a_key_placed_inside_the_rule_block_is_refused(self):
        """All three copies get the same extra key under execution.auto_abort, so the
        three-way contract still holds; the rule-block digest and the key diff refuse."""
        anchor = b'"auto_abort": {"consecutive_infrastructure_failures": 10,'

        def wrap(real, m):
            def faulty(old):
                out = real(old)
                return {k: v.replace(anchor, anchor + b' "restart_cap": 3,', 1)
                        for k, v in out.items()}
            return faulty
        d = dict(self.PRE)
        for k in ('CONFIG', 'ARCH', 'PROTO'):
            self.assertEqual(d[k].count(anchor), 1, k)
        rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'rule block')
        post = _printed(err)
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertNotEqual(post['config']['rule_block_sha256_after'], RULE_BLOCK)
        self.assertIn('execution.auto_abort.restart_cap', post['config']['added_keys'])
        g = post['config']['gate']
        self.assertIs(g['exactly_the_three_keys_added'], False)
        self.assertIs(g['rule_block_after_is_the_pin'], False)
        self.assertIs(g['deleting_the_insertions_reproduces_the_prior_config'], False)
        self.assertIs(post['gate']['config'], False)

    def test_isolated_a_rule_block_key_is_refused(self):
        """A PURE insertion of one key under `enclosure` (a rule-block key that no
        pinned-subtree check covers), byte-identical in the three copies, with the tool's
        own added-key list extended to name it: only the rule-block digest refuses."""
        m = _load_tool()
        anchor = b'    "clock_equivalence_tolerance_ms": 1\n'
        probes = self._probe_config_key(m, anchor, b'    "probe_key": 1,\n')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={
            'INSERTIONS': m.INSERTIONS + probes,
            'ADDED_CONFIG_KEYS': sorted(m.ADDED_CONFIG_KEYS + ['enclosure.probe_key'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'rule-block key')
        printed = _printed(err)
        self._refused_alone(printed['config']['gate'], 'rule_block_after_is_the_pin', 'rule block')
        self._refused_alone(printed['gate'], 'config', 'rule block')

    def test_isolated_a_pinned_subtree_key_is_refused(self):
        """A PURE insertion of one key under `sandbox` (a pinned subtree outside the rule
        block), byte-identical in the three copies, with the added-key list extended:
        only the pinned-subtree check refuses."""
        m = _load_tool()
        anchor = b'              "containment_probe_sha256": null},\n'
        probes = self._probe_config_key(m, anchor, b'              "probe_key": 1,\n')
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
        """An inserter that also renames a key, changes a value, changes the cap value,
        changes a prompt byte, or adds a CR -- the same way in all three copies."""
        cases = {
            'no_key_removed': ('config', b'"pause_thresholds":', b'"pause_threshold":'),
            'no_key_changed': ('config', b'"battery_percent": 20', b'"battery_percent": 21'),
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

    def test_isolated_engineering_acquisition_that_differs_from_BOUND_LIMITS_is_refused(self):
        m = _load_tool()
        limits = m.bound_limits()
        self.assertIsNotNone(limits)
        off = dict(limits, wall_seconds_total=601.0)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'bound_limits': lambda: dict(off)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'BOUND_LIMITS')
        self.assertIn('"engineering_acquisition_equals_run_smoke_BOUND_LIMITS": false', err)
        self._refused_alone(_printed(err)['config']['gate'],
                            'engineering_acquisition_equals_run_smoke_BOUND_LIMITS', 'ea')

    def test_config_checks_refuses_a_pre_image_rule_block_that_is_not_the_pin(self):
        m = _load_tool()
        anchor = b'"consecutive_infrastructure_failures": 10'
        old = self.PRE['CONFIG'].replace(anchor, anchor[:-2] + b'11', 1)
        new = m.insert_all({'config': old, 'architecture': self.PRE['ARCH'],
                            'protocol': self.PRE['PROTO']})['config']
        out = m.config_checks(old, new)
        self.assertIs(out['gate']['rule_block_before_is_the_pin'], False)
        self.assertIs(out['ok'], False)

    def test_postconditions_refuse_unchanged_documents(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        post, ok = m.postconditions(old, dict(old))
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
        clone = m.PROMPTS[1]['prompt'].upper().replace('\n', '  ')   # equal once normalized
        err = self._prompt_refusal(synthetic_sources([{'task_id': 900, 'prompt': clone,
                                                        'code': ''}]),
                                   '"normalized_equal_to": ["mbpp/900"]')
        self.assertIn('"passes": false', err)
        printed = _printed(err)
        self.assertIs(printed['per_prompt'][1]['gate']['normalized_equal_to_no_source'], False)
        self._refused_alone(printed['gate'], 'every_prompt_passes', 'equal')

    def test_a_source_prompt_too_similar_to_a_conformance_prompt_is_refused(self):
        m = _load_tool()
        near = m.PROMPTS[2]['prompt'].replace('earliest', 'soonest')   # Jaccard >= 0.5
        self.assertGreaterEqual(m.jaccard(near, m.PROMPTS[2]['prompt']), 0.5)
        self.assertNotEqual(m.lab_data.normalize_prompt(near),
                            m.lab_data.normalize_prompt(m.PROMPTS[2]['prompt']))
        err = self._prompt_refusal(synthetic_sources([{'task_id': 901, 'prompt': near,
                                                        'code': ''}]),
                                   '"closest_source_uid": "mbpp/901"')
        self.assertIn('"passes": false', err)
        self._refused_alone(_printed(err)['per_prompt'][2]['gate'], 'max_jaccard_below_threshold',
                            'too similar')

    def test_a_smoke_task_too_similar_to_a_conformance_prompt_is_refused(self):
        """Not isolable: a smoke task is a source record, so both maxima exceed 0.5."""
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
        """oodp/1 with a body line: still distinct, dissimilar, routed and unique; only
        its shape check refuses."""
        m = _load_tool()
        bad = dict(m.PROMPTS[0], prompt=m.PROMPTS[0]['prompt'] + '    return left\n')
        self.assertIs(m.prompt_shape(bad)['ok'], False)
        err = self._prompt_refusal(None, '"shape_ok": false',
                                   patch={'PROMPTS': (bad,) + tuple(m.PROMPTS[1:])})
        printed = _printed(err)
        self._refused_alone(printed['per_prompt'][0]['gate'], 'shape_ok', 'shape')
        self.assertTrue(all(r['passes'] for r in printed['per_prompt'][1:]))

    def test_isolated_a_prompt_the_builder_does_not_route_is_refused(self):
        """A user-prompt builder that does not produce the non-MBPP wrapper: only the
        route check refuses (every other check of every prompt holds)."""
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
        """The REAL load_sources on a directory of tampered files."""
        tmp = Path(tempfile.mkdtemp(prefix='repair_sources_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        m = _load_tool()
        for fname in m.SOURCE_FILES.values():
            (tmp / fname).write_bytes(b'not the pinned bytes\n')
        pins = json.loads(self.PRE['CONFIG'])['roster']['sources']
        with self.assertRaises(ValueError) as cm:
            m.load_sources(tmp, pins)
        self.assertIn('pinned', str(cm.exception))
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(
            d, sources=lambda _d, p, _t=tmp, _m=m: _m.load_sources(_t, p))
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'tampered sources')
        self.assertIn('could not be read', err)

    # -- the successor commit ------------------------------------------------------
    def test_a_history_whose_48f4d70_is_not_the_prior_successor_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, commit_protocol=b'some other protocol\n')
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'wrong commit')
        self.assertIn('does not carry the prior successor', err)

    # -- the negative control is live ------------------------------------------
    def test_a_negative_control_that_cannot_refuse_stops_the_run(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'move_out': lambda new, ins: new})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'dead control')
        self.assertIn('the negative control did not refuse', err)
        self._refused_alone(_printed(err)['gate'], 'every_variant_refused_on_placement', 'control')

    # -- the one-shot guard ------------------------------------------------------
    def test_the_amended_documents_are_refused(self):
        rc, err, receipt, amended = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        d = dict(amended)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, as pinned')
        self.assertIn('precondition', err)
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
        """A faulty inserter that puts the 5.3 paragraph at the START of section 5.3
        instead of after its anchor: still a pure insertion, still inside 5.3 with both
        bounds; only 'directly beside the anchor' refuses."""
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
        pl = printed['insertion_placement']['protocol.5_3']
        self.assertIs(pl['inside_its_section'], True)
        self.assertIs(pl['directly_beside_the_anchor'], False)

    def test_placement_refuses_text_before_its_section_and_a_duplicated_heading(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.5_3')
        new = m.insert_all(old)['protocol']
        self.assertIs(m.placement(new, ins)['inside_its_section'], True)
        # the text just before the section heading: the lower bound refuses
        p = new.replace(ins.text, b'', 1)
        k = p.index(ins.section)
        before_heading = p[:k] + ins.text + p[k:]
        self.assertIs(m.placement(before_heading, ins)['section_ends_at_its_upper_bound'], True)
        self.assertIs(m.placement(before_heading, ins)['inside_its_section'], False)
        # the section heading twice: which section is meant is ambiguous, refused
        twice = new + b'\n' + ins.section + b' (copy)\n\ntext\n'
        self.assertEqual(twice.count(ins.section), 2)
        self.assertIs(m.placement(twice, ins)['inside_its_section'], False)

    def test_anchor_facts_requires_a_fenced_anchor_inside_the_fence(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'architecture.6_1.prompts')
        a = self.PRE['ARCH']
        self.assertIs(m.anchor_facts(a, ins)['inside_its_section'], True)
        k = a.index(ins.anchor)
        # the first fence now closes above the anchor, and a second one holds it: the
        # section still ends at 6.2, only the fence bound refuses
        closed_early = a[:k] + b'```\n\n```json\n' + a[k:]
        s0, s1 = m.section_span(closed_early, ins.section)
        self.assertTrue(closed_early[s1:].startswith(ins.section_end))
        facts = m.anchor_facts(closed_early, ins)
        self.assertIs(facts['inside_the_json_fence'], False)
        self.assertIs(facts['inside_its_section'], False)

    # -- units -------------------------------------------------------------------
    def test_placement_has_both_bounds_for_every_insertion(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        new = m.insert_all(old)
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
        with self.assertRaises(KeyError):                   # the MBPP branch needs a reference
            build(dict(m.PROMPTS[0], benchmark='mbpp'))


class GateTests(_DriveHarness, unittest.TestCase):
    """AGGREGATION: each named check of each gate refuses on its own (finding 5)."""

    def _recorded_gates(self):
        calls = {}

        def wrap(real, m):
            def recording(name, checks):
                calls.setdefault(name, list(checks))
                self.assertEqual(calls[name], list(checks), name)
                return real(name, checks)
            return recording
        rc, err, receipt, after = self._drive(dict(self.PRE), wraps={'gate': wrap})
        self.assertEqual(rc, 0, err)
        return calls

    def test_the_gates_and_their_checks_are_exactly_the_pinned_list(self):
        self.assertEqual(self._recorded_gates(), GATES)

    def test_each_named_check_refuses_on_its_own(self):
        for name, checks in GATES.items():
            for check in checks:
                with self.subTest(gate=name, check=check):
                    def wrap(real, m, _n=name, _c=check):
                        def flipping(gname, gchecks):
                            if gname == _n:
                                self.assertIn(_c, gchecks)
                                self.assertIs(gchecks[_c], True, 'not True on the pristine inputs')
                                gchecks[_c] = False
                            return real(gname, gchecks)
                        return flipping
                    d = dict(self.PRE)
                    rc, err, receipt, after = self._drive(d, wraps={'gate': wrap})
                    self._assert_refused_unchanged(d, rc, err, receipt, after,
                                                   '%s.%s flipped' % (name, check))
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
                                    (RepairAmendmentWitnessTests, GateTests)), test)
        none = sorted(k for k, v in LIVENESS.items() if v is None)
        self.assertEqual(none, [('cells', 'cells_unchanged_outside_superseded_by'),
                                ('negative_control', 'real_documents_unchanged'),
                                ('negative_control', 'scratch_copies_unchanged')])


class ProseCorrectionTests(_DriveHarness, unittest.TestCase):
    """The review's findings 1-4 and 7 (commit 1349619), on the delivered texts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = _load_tool()

    def _amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        return receipt, after

    def _section(self, raw: bytes, heading: bytes) -> str:
        s0, s1 = self.m.section_span(raw, heading)
        return raw[s0:s1].decode('utf-8')

    def test_finding_1_the_restart_cap_reportability_is_provisional(self):
        m = self.m
        text = m.P_5_3
        self.assertIn("**Provisional, pending root's", text)
        self.assertIn('question (i)', text)
        self.assertIn('no freeze may be made while it is', text)
        self.assertIn('it is a change to a rule for reporting decisions', text)
        self.assertNotIn('that label replaces the rule of 6.4', text)
        self.assertIn("only in the form in which root's ruling fixes it", m.P_14_3)
        self.assertIn("root's ruling fixes it before the freeze", m.A_6_3)
        self.assertIn("provisionally pending root's ruling", m.A_7_1_21AB)
        receipt, after = self._amended()
        self.assertTrue(receipt['server_supervision']['reportability'].startswith('PROVISIONAL'))
        self.assertIn('open_point_for_root', receipt['server_supervision'])

    def test_finding_2_the_provenance_claims_say_only_what_was_checked(self):
        receipt, after = self._amended()
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertNotIn('decision rule, stopping rule', sb['reason'])
        self.assertNotIn('It changes NO', sb['reason'])
        for t in ('trial_aborted(server_restart_cap)', 'trial_aborted(unresolved_worker)',
                  'trial_aborted(infrastructure)', 'trial_aborted(receipt_mismatch)',
                  'PROVISIONALLY'):
            self.assertIn(t, sb['reason'])
        self.assertIn('covers neither server_supervision nor any protocol text', sb['reason'])
        placement = receipt['server_supervision']['placement']
        self.assertNotIn('shows mechanically', placement)
        self.assertIn('covers neither this key nor any protocol text', placement)

    def test_finding_3_every_abort_reason_the_amendment_names_is_an_automatic_abort_of_6_4(self):
        receipt, after = self._amended()
        p = after['PROTO']
        s64 = self._section(p, b'### 6.4 Failure-to-outcome table')
        named = set()
        for ins in self.m.INSERTIONS:
            named |= set(re.findall(r'trial_aborted\((\w+)\)', ins.text.decode('utf-8')))
        self.assertEqual(named, {'server_restart_cap', 'unresolved_worker', 'infrastructure',
                                 'receipt_mismatch', 'server_identity'})
        for reason in sorted(named):
            with self.subTest(reason=reason):
                self.assertIn('trial_aborted(%s)' % reason, s64)
        new_part = self.m.P_6_4
        for t in ('`trial_aborted(server_restart_cap)`', '`trial_aborted(unresolved_worker)`',
                  '`trial_aborted(infrastructure)` when the first start', '`smoke_transport`',
                  '`smoke_no_usage`', 'never `operator_discretion`'):
            self.assertIn(t, new_part)
        s146 = self._section(p, b'### 14.6 Trial order, unconditional execution')
        self.assertIn('every other abort is `operator_discretion` does not apply', s146)
        self.assertNotIn('the rule already fixed for the stage', self.m.P_5_3)
        self.assertIn('under rules that existed before', self.m.P_5_3)
        self.assertIn('`smoke_transport`', self.m.P_5_3)
        self.assertIn('smoke_no_usage', self.m.A_7_1_20A)
        self.assertIn('new automatic abort, protocol 6.4', self.m.A_7_1_20A)

    def test_finding_4_row_28_is_trial_only_and_row_29_also_prefreeze(self):
        receipt, after = self._amended()
        s122 = self._section(after['PROTO'], b'### 12.2 Event schema')
        self.assertIn('Row 28 is written on a trial chain only.', s122)
        self.assertIn('for a stage of 5.8, on the `_prefreeze` chain', s122)
        self.assertNotIn('Rows 28 and 29 are trial-chain events.', s122)
        self.assertIn('for a stage, on the `_prefreeze` chain', self.m.P_14_6)
        self.assertIn('ledger of `lab_load`', self.m.P_14_6)
        self.assertIn('the `_prefreeze` chain for a stage of protocol 5.8', self.m.A_4_4)

    def test_finding_7_wording(self):
        m = self.m
        self.assertNotIn('no model was run', m.P_5_8)
        self.assertIn('neither served model', m.P_5_8)
        self.assertIn('neither served model', m.P_2_4 + m.P_5_8)
        for t in (m.P_2_4, m.P_5_8):
            self.assertNotIn('under a rule recorded before their texts', t)
            self.assertNotIn('under a rule fixed before their texts', t)
            self.assertIn('not a recorded fact', t)
        self.assertNotIn('stated_before_the_texts', m.PROMPT_RULE)
        self.assertIn('NOT a recorded fact', m.PROMPT_RULE['order'])
        receipt, after = self._amended()
        moved = receipt['dependent_hashes_that_move'][
            'config_sha256 / harness_file_sha256[config.json]']
        self.assertIn('nothing consumes that pin with a refusal', moved)
        self.assertNotIn('with either record now refuses', moved)
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertNotIn('no model was run', sb['what_this_is_not'])


def _load_verifier():
    _loaded[0] += 1
    spec = importlib.util.spec_from_file_location(
        'verify_repair_amendment_under_test_%d' % _loaded[0], HERE / 'verify_repair_amendment.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class VerifierTests(_DriveHarness, unittest.TestCase):
    """The independent verifier (verify_repair_amendment.py) on the control drive's
    output: it must verify the amendment and must NOT verify its negative controls."""

    KEYS = {'CONFIG': 'config', 'ARCH': 'architecture', 'PROTO': 'protocol', 'CELLS': 'cells'}
    CHECKS = ['parent_is_the_reviewed_preimage', 'parent_config_bytes',
              'receipt_lists_exactly_the_expected_insertions',
              'receipt_sections_agree_with_the_verifier_headings', 'each_insertion_occurs_once',
              'deleting_the_insertions_reproduces_the_parent',
              'each_insertion_under_the_verifier_heading', 'no_cr_byte',
              'three_blocks_byte_identical', 'config_parses', 'exactly_the_three_keys_added',
              'no_key_removed', 'no_key_changed', 'server_supervision_is_the_contract_literal',
              'prompts_are_the_receipt_texts', 'engineering_acquisition_unchanged_and_root_table',
              'rule_block_before_and_after_is_cbfd1792', 'vocabulary_sections_identical', 'cells',
              'corrections_in_the_protocol', 'receipt_names_the_amended_protocol',
              'receipt_written_digests_match', 'receipt_corrects_the_withdrawn_first_run',
              'withdrawn_commit_carries_the_withdrawn_protocol',
              'withdrawn_receipt_kept_byte_unchanged']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            then = _blob(WITHDRAWN_REV, WITHDRAWN_RECEIPT)
            cls.HISTORY = {'withdrawn_protocol': _blob(WITHDRAWN_REV, REL['PROTO']),
                           'withdrawn_receipt_then': then, 'withdrawn_receipt_now': then}
            cls.WITHDRAWN = {cls.KEYS[k]: _blob(WITHDRAWN_REV, rel) for k, rel in REL.items()}
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history holding %s is not available here: %s'
                                    % (WITHDRAWN_REV[:7], e))

    def _amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        before = {self.KEYS[k]: v for k, v in self.PRE.items()}
        return before, {self.KEYS[k]: v for k, v in after.items()}, receipt

    def _reseal(self, after, receipt):
        """``after`` and ``receipt`` with the digests that follow the protocol, config and
        ARCHITECTURE bytes (cells successor, receipt new_successor, written digests)
        recomputed, so only the check under test sees the change."""
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
        got = v.verify(before, after, receipt, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['all_verified'], True, json.dumps(got)[:3000])
        self.assertEqual(sum(got['insertions_listed'].values()), 19)
        self.assertEqual(len(got['each_insertion_under_its_heading']), 17)
        self.assertEqual(list(got['checks']), self.CHECKS)
        self.assertIs(v.negative_controls(before, after, receipt, self.PRE['PROTO'], self.HISTORY,
                                          self.WITHDRAWN)['every_control_failed'], True)

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
                    got = v.verify(before, after, receipt, self.PRE['PROTO'], self.HISTORY)
                self.assertIs(got['all_verified'], False)

    def test_the_withdrawn_first_run_does_not_verify(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, self.WITHDRAWN, receipt, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['all_verified'], False)
        self.assertIs(got['checks']['corrections_in_the_protocol'], False)

    def test_the_verifier_refuses_a_receipt_that_omits_an_insertion(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        receipt = dict(receipt, insertions=[i for i in receipt['insertions']
                                            if i['key'] != 'protocol.13_1'])
        got = v.verify(before, after, receipt, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['all_verified'], False)
        self.assertIs(got['deleting_the_insertions_reproduces_the_parent']['protocol'], False)
        self.assertIs(got['checks']['receipt_lists_exactly_the_expected_insertions'], False)

    def test_the_verifier_refuses_a_wrong_demoted_commit_and_a_wrong_receipt_section(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, after, receipt, b'not the 48f4d70 protocol', self.HISTORY)
        self.assertIs(got['cells']['demoted_commit_carries_the_parent_successor'], False)
        self.assertIs(got['all_verified'], False)
        moved = dict(receipt, insertions=[dict(i, section='### 5.7 Sandbox under two workers')
                                          if i['key'] == 'protocol.5_8' else i
                                          for i in receipt['insertions']])
        got = v.verify(before, after, moved, self.PRE['PROTO'], self.HISTORY)
        # the heading comes from the verifier's own map, so the paragraph still lies
        # under it; the receipt's wrong section is refused as a disagreement
        self.assertIs(got['each_insertion_under_its_heading']['protocol.5_8'], True)
        self.assertIs(got['checks']['receipt_sections_agree_with_the_verifier_headings'], False)
        self.assertIs(got['all_verified'], False)

    def test_a_paragraph_moved_into_another_section_does_not_verify_even_with_a_matching_receipt(self):
        """Finding 6: the 14.6 paragraph moved into 14.7, and the receipt's section, the
        cells successor and the written digests edited to match."""
        v = _load_verifier()
        before, after, receipt = self._amended()
        row = next(i for i in receipt['insertions'] if i['key'] == 'protocol.14_6')
        t = row['text'].encode('utf-8')
        p = after['protocol'].replace(t, b'', 1)
        h = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        k = p.index(h) + len(h)
        moved_after = dict(after, protocol=p[:k] + t + p[k:])
        receipt = dict(receipt, insertions=[dict(i, section='### 14.7 The operator is an AI agent session')
                                            if i['key'] == 'protocol.14_6' else i
                                            for i in receipt['insertions']])
        moved_after, receipt = self._reseal(moved_after, receipt)
        got = v.verify(before, moved_after, receipt, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['each_insertion_under_its_heading']['protocol.14_6'], False)
        self.assertIs(got['checks']['each_insertion_under_the_verifier_heading'], False)
        self.assertIs(got['all_verified'], False)

    def test_negative_controls_for_the_pins_config_diff_rule_block_and_vocabulary(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        # pins, ALONE: the same ARCHITECTURE byte changed in pre-image and amendment
        k = before['architecture'].index(b'## 1.') + 3
        b2 = dict(before, architecture=before['architecture'][:k] + b'X' + before['architecture'][k + 1:])
        ka = after['architecture'].index(b'## 1.') + 3
        a2 = dict(after, architecture=after['architecture'][:ka] + b'X' + after['architecture'][ka + 1:])
        a2, r2 = self._reseal(a2, receipt)
        got = v.verify(b2, a2, r2, self.PRE['PROTO'], self.HISTORY)
        self.assertEqual([n for n, ok in got['checks'].items() if not ok],
                         ['parent_is_the_reviewed_preimage'])
        # the config diff and the rule block: a rule-block value changed in all three copies
        old = b'"consecutive_infrastructure_failures": 10'
        a3 = {d: (after[d].replace(old, old[:-2] + b'11', 1) if d in ('config', 'architecture',
                                                                         'protocol') else after[d])
              for d in after}
        a3, r3 = self._reseal(a3, receipt)
        got = v.verify(before, a3, r3, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['checks']['no_key_changed'], False)
        self.assertIs(got['checks']['rule_block_before_and_after_is_cbfd1792'], False)
        self.assertIs(got['all_verified'], False)
        # the config diff: a key renamed in all three copies
        old = b'"pause_thresholds":'
        a4 = {d: (after[d].replace(old, b'"pause_threshold":', 1) if d != 'cells' else after[d])
              for d in after}
        a4, r4 = self._reseal(a4, receipt)
        got = v.verify(before, a4, r4, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['checks']['no_key_removed'], False)
        self.assertIs(got['checks']['exactly_the_three_keys_added'], False)
        # the vocabulary sections: one byte of section 1
        p = after['protocol']
        k = p.index(b'## 1. Purpose, scope')
        k = p.index(b'\n\n', k) + 2
        a5 = dict(after, protocol=p[:k] + b'X' + p[k:])
        a5, r5 = self._reseal(a5, receipt)
        got = v.verify(before, a5, r5, self.PRE['PROTO'], self.HISTORY)
        self.assertIs(got['checks']['vocabulary_sections_identical'], False)
        self.assertIs(got['all_verified'], False)
        # the kept receipt: changed after the fact
        got = v.verify(before, after, receipt, self.PRE['PROTO'],
                       dict(self.HISTORY, withdrawn_receipt_now=b'{}\n'))
        self.assertEqual([n for n, ok in got['checks'].items() if not ok],
                         ['withdrawn_receipt_kept_byte_unchanged'])

    def test_each_verifier_check_can_fail_on_a_real_input(self):
        """LIVENESS for the verifier: for every named check, a real variant of the
        amendment, receipt or history on which that check's own value is False (others
        may be False too; the flip test above covers the aggregation)."""
        v = _load_verifier()
        before, after, receipt = self._amended()
        base = (before, after, receipt, self.PRE['PROTO'], self.HISTORY)

        def rep(docs, old, new, which=('config', 'architecture', 'protocol')):
            return {d: (docs[d].replace(old, new, 1) if d in which else docs[d]) for d in docs}

        def with_receipt(fn):
            r = json.loads(json.dumps(receipt))
            fn(r)
            return (before, after, r, self.PRE['PROTO'], self.HISTORY)

        def with_after(a):
            a, r = self._reseal(a, receipt)
            return (before, a, r, self.PRE['PROTO'], self.HISTORY)
        row = next(i for i in receipt['insertions'] if i['key'] == 'protocol.13_1')
        k = after['protocol'].index(b'## 1. Purpose, scope')
        k = after['protocol'].index(b'\n\n', k) + 2
        t = next(i for i in receipt['insertions'] if i['key'] == 'protocol.14_6')['text'].encode()
        p = after['protocol'].replace(t, b'', 1)
        h = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        j = p.index(h) + len(h)
        fb, eb, _ = v.fence_block(before['architecture'], v.FENCE_MARKERS['architecture'])
        fa, ea, _ = v.fence_block(after['architecture'], v.FENCE_MARKERS['architecture'])
        variants = {
            'parent_is_the_reviewed_preimage': (dict(before, cells=before['cells'] + b' '),) + base[1:],
            'parent_config_bytes': (dict(before, config=before['config'] + b' '),) + base[1:],
            'receipt_lists_exactly_the_expected_insertions': with_receipt(
                lambda r: r['insertions'].pop()),
            'receipt_sections_agree_with_the_verifier_headings': with_receipt(
                lambda r: r['insertions'][-1].__setitem__('section', '### 7.2 What is fsynced')),
            'each_insertion_occurs_once': with_after(dict(after, protocol=after['protocol']
                                                          + row['text'].encode())),
            'deleting_the_insertions_reproduces_the_parent': with_after(
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
            'no_key_changed': with_after(rep(after, b'"battery_percent": 20', b'"battery_percent": 21')),
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
            'corrections_in_the_protocol': (before, dict(self.WITHDRAWN), receipt, self.PRE['PROTO'],
                                            self.HISTORY),
            'receipt_names_the_amended_protocol': with_receipt(
                lambda r: r['successor_provenance'].__setitem__('new_successor', '0' * 64)),
            'receipt_written_digests_match': with_receipt(
                lambda r: r['written'].__setitem__('protocol_sha256', '0' * 64)),
            'receipt_corrects_the_withdrawn_first_run': with_receipt(
                lambda r: r['corrects'].__setitem__('commit', '0' * 40)),
            'withdrawn_commit_carries_the_withdrawn_protocol': base[:4] + (
                dict(self.HISTORY, withdrawn_protocol=b'x'),),
            'withdrawn_receipt_kept_byte_unchanged': base[:4] + (
                dict(self.HISTORY, withdrawn_receipt_now=b'{}\n'),),
        }
        self.assertEqual(sorted(variants), sorted(self.CHECKS))
        for name, args in variants.items():
            with self.subTest(check=name):
                got = v.verify(*args)
                self.assertIs(got['checks'][name], False)
                self.assertIs(got['all_verified'], False)

    def test_the_real_amendment_commit_verifies_if_present(self):
        """After the correction is committed: the verifier's main() on that commit (the
        one that ADDS a REPAIR_AMENDMENT_CORRECTION_RECEIPT). Skipped before it exists."""
        log = subprocess.run(['git', '-C', str(REPO), 'log', '--diff-filter=A', '--format=%H',
                              '--name-only', '--', 'results/live_ab/'],
                             capture_output=True, text=True)
        commit, cur = None, None
        for line in log.stdout.splitlines() if log.returncode == 0 else ():
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                cur = line
            elif line.startswith('results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_'):
                commit = cur
                break
        if commit is None:
            self.skipTest('no commit in this history adds a repair amendment correction receipt')
        v = _load_verifier()
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = v.main([commit])
        self.assertEqual(rc, 0, err.getvalue())


def _real_sources_dir():
    """A directory holding byte copies of the three pinned sources, if this host has
    them (LIVE_AB_SOURCES_DIR, or the default cache locations); else None."""
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
    """Optional: re-run the mechanical prompt check on the REAL pinned sources and
    compare with the delivered receipts (the first run's and the correction's; the
    prompts did not change). Skipped where the gitignored sources are absent; the tool
    itself refuses without them."""

    def test_the_recorded_similarity_maxima_are_reproduced(self):
        found = _real_sources_dir()
        if found is None:
            self.skipTest('the three pinned roster sources are not on this host '
                          '(set LIVE_AB_SOURCES_DIR)')
        receipts = sorted((REPO / 'results' / 'live_ab').glob('REPAIR_AMENDMENT_*RECEIPT_*.json'))
        if not receipts:
            self.skipTest('no repair amendment receipt in this checkout')
        tmp = Path(tempfile.mkdtemp(prefix='repair_real_sources_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for n, p in found.items():
            shutil.copyfile(p, tmp / n)
        m = _load_tool()
        pins = json.loads(_blob(PRE_REV, REL['CONFIG']))['roster']['sources']
        got = m.check_prompts(m.load_sources(tmp, pins), list(SMOKE))
        self.assertIs(got['all_pass'], True)
        for path in receipts:
            want = json.loads(path.read_bytes())['conformance_prompts'][
                '3_mechanical_check_results']
            for g, w in zip(got['per_prompt'], want['per_prompt']):
                for key in ('id', 'max_jaccard', 'closest_source_uid', 'max_jaccard_smoke_tasks',
                            'closest_smoke_task', 'normalized_equal_to', 'prompt_sha256'):
                    self.assertEqual(g[key], w[key], (path.name, g['id'], key))
        with gzip.open(tmp / 'HumanEval.jsonl.gz', 'rt') as fh:
            self.assertEqual(sum(1 for line in fh if line.strip()), 164)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
