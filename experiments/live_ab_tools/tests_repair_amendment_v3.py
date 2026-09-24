"""Witnesses for the pre-outcome amendment v3 (repair_amendment_v3.py).

HOW EVERY DRIVE RUNS
  The PRE-amendment blobs (`git show 474f9d8:<path>`, read-only, once per class: the documents
  amendment v2 wrote, unchanged on this branch since, and the v2 receipt) are copied into a fresh
  temporary directory.  A fresh instance of the tool is loaded, and its paths REPO, CONFIG, ARCH,
  PROTO, CELLS and V2_RECEIPT are re-pointed at the copies (the harness asserts each lies under the
  temporary directory), so the documents and the receipt are written there only.  The tool's
  `subprocess` (git rev-parse / show / merge-base) is replaced in that instance only, and
  `lab_common.harness_file_hashes` is stubbed.  The code the prose describes is the REAL code of
  this checkout (its pure functions run on synthetic chains; a witness that needs the code to say
  something else patches one name for the length of one drive).  Every drive compares the digests
  of this checkout's real documents and the results/live_ab listing before and after.

WHAT A REFUSAL WITNESS SHOWS: two properties separately.
  * AGGREGATION (GateTests): every refusal of main() goes through gate(name, checks).  The gates
    and their checks are pinned (GATES); for EVERY (gate, check), a drive on the pristine
    pre-images sets that one check False at gate() and main() must refuse.
  * LIVENESS (the LIVENESS table): which REAL input makes each check False; `test_isolated_*`
    make ONLY that check False.  Checks that no real input can make alone False (implied by
    another check) or at all say so.

ProseTests: every closed name and dotted code name of the new prose is read back from the code,
and the order of the reported results is the builder's.  VerifierTests: the independent verifier
on the control drive's output, and on the real amendment commit once it exists.

SCOPE: needs the git history (474f9d8); without it the classes are skipped and the skip says why.
Nothing here runs a model, a server, a build or a network request.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
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
TOOL = HERE / 'repair_amendment_v3.py'
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json'}
V2_REL = 'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
PRE_REV = '474f9d82aae2b3979910d8a99d8305b5d7bc44c1'
REVIEWED = {'CONFIG': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
            'ARCH': 'e7ea9c0fb7a28c6bdb47bb4085dcddba41144bd134d7b3a9b026ad7c9a30c86a',
            'PROTO': '6c0ebf2faa7515ff27f01188d9f1e487c928c63373f451dea51f06a8cdacaab9',
            'CELLS': '6b31bf20a07cbc4b0c162fb0d309826d88ab5b95b36f9cd3e1d86500d7ff8df5'}
V2_SHA256 = '66efcb8b64b3e54d890ac70c77686e0678255fe6cba78347fa3a30878e12feff'
#: the delivered documents (the one real run, receipt REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218),
#: and the delivered cells.json with the new successor's recorded_utc replaced by
#: RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED = {'CONFIG': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
             'ARCH': '2ec71980de5b6a74df586c5790e6eac7c54dbd79342ae69dab1a01a0bb458190',
             'PROTO': '73dd0573955b2ef586e120f2b44558eb0227c70bbca9cbf9225ec4fb5583500c'}
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    '93afb31ccabfdc0ecba83040173b0d277a8302e71d3fc38b7e3579683ec461e6')
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
RECEIPT_GLOB = 'REPAIR_AMENDMENT_V3_RECEIPT_*.json'

#: every gate of main() and the checks in each (the aggregation witness)
GATES = {
    'pins': ['config_is_the_reviewed_preimage', 'architecture_is_the_reviewed_preimage',
             'protocol_is_the_reviewed_preimage', 'cells_is_the_reviewed_preimage',
             'no_cr_byte', 'three_way_contract_before', 'rule_block_before_is_the_pin',
             'cells_round_trips', 'cells_original_pin_untouched',
             'cells_current_successor_is_the_prior_successor',
             'cells_successor_supersedes_the_original', 'cells_prior_successor_count',
             'cells_prior_successors_are_the_recorded_entries'],
    'anchors': ['every_anchor_once', 'no_anchor_error', 'every_anchor_inside_its_section',
                'inserted_text_form'],
    'amendment_v2': ['v2_receipt_is_the_pinned_bytes', 'v2_receipt_is_committed_in_474f9d8',
                     'v2_commit_is_an_ancestor_of_head', 'v2_wrote_the_preimages',
                     'v2_insertions_whole_in_the_preimages'],
    'code': ['row_31_names_exactly_the_abort_sources', 'row_31_names_exactly_the_abort_owed_fields',
             'abort_owed_is_trial_only_and_durable_in_the_prose',
             'point_reasons_are_the_code_and_6_4_names_each',
             'anchor_commit_problems_named_in_12_4', 'builder_labels_quoted_verbatim_in_16',
             'verifier_rule_names_are_the_code',
             'summary_decision_is_the_result_and_logged_decision_beside_it',
             'no_decision_point_reads_abort_owed', 'supervision_state_replays_abort_owed',
             'crossing_after_the_point_not_acted_on_with_its_reason',
             'crossing_before_the_point_missed_is_a_defect',
             'an_unresolved_worker_stays_unresolved',
             'an_unresolved_worker_is_a_no_decision_point', 'unread_counter_delta_is_null',
             'null_fields_are_nullable_in_the_schema', 'decision_receipt_commit_check_is_wired'],
    'postconditions': ['reverting_the_insertions_reproduces_each_preimage',
                       'every_insertion_inside_its_section_beside_its_anchor', 'no_cr_byte_after',
                       'three_way_contract_after', 'config_json_byte_identical',
                       'configuration_blocks_byte_identical',
                       'vocabulary_sections_1_3_11_byte_identical', 'rule_block_after_is_the_pin',
                       'v2_insertions_intact', 'architecture_and_protocol_changed'],
    'negative_control': ['every_moved_variant_refused_on_placement', 'config_variant_refused',
                         'v2_split_variant_refused', 'vocabulary_variant_refused',
                         'scratch_copies_unchanged', 'real_documents_unchanged'],
    'successor_commit': ['prior_successor_commit_carries_the_prior_successor'],
    'cells': ['cells_unchanged_outside_superseded_by'],
    'final': ['documents_read_back_equal_computed', 'config_on_disk_unchanged',
              'no_harness_file_changed'],
}
#: gates evaluated AFTER something was written: flipping them refuses the receipt, not the write
AFTER_WRITE_GATES = ('final',)

_I = 'test_isolated_'
_C = 'test_code_'
#: (gate, check) -> the test whose real input makes that check False, or None with the reason
LIVENESS = {
    ('pins', 'config_is_the_reviewed_preimage'): _I + 'a_config_that_is_not_the_preimage_is_refused',
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
    # IMPLIED by cells_prior_successors_are_the_recorded_entries (a tuple of six); the named
    # test drops an entry, which makes both False
    ('pins', 'cells_prior_successor_count'): 'test_a_dropped_prior_successor_is_refused',
    ('pins', 'cells_prior_successors_are_the_recorded_entries'):
        'test_each_cells_or_rule_block_precondition_refuses',
    ('anchors', 'every_anchor_once'): 'test_an_absent_or_duplicated_anchor_is_refused',
    ('anchors', 'no_anchor_error'): 'test_an_absent_or_duplicated_anchor_is_refused',
    ('anchors', 'every_anchor_inside_its_section'):
        _I + 'an_interloper_heading_puts_an_anchor_outside_its_section',
    ('anchors', 'inserted_text_form'): _I + 'an_inserted_text_of_the_wrong_form_is_refused',
    ('amendment_v2', 'v2_receipt_is_the_pinned_bytes'): 'test_each_amendment_v2_condition_refuses',
    ('amendment_v2', 'v2_receipt_is_committed_in_474f9d8'):
        'test_each_amendment_v2_condition_refuses',
    ('amendment_v2', 'v2_commit_is_an_ancestor_of_head'):
        'test_each_amendment_v2_condition_refuses',
    ('amendment_v2', 'v2_wrote_the_preimages'): 'test_each_amendment_v2_condition_refuses',
    ('amendment_v2', 'v2_insertions_whole_in_the_preimages'):
        'test_each_amendment_v2_condition_refuses',
    ('code', 'row_31_names_exactly_the_abort_sources'): _C + 'names_refuse_one_by_one',
    ('code', 'row_31_names_exactly_the_abort_owed_fields'): _C + 'names_refuse_one_by_one',
    ('code', 'abort_owed_is_trial_only_and_durable_in_the_prose'): _C + 'names_refuse_one_by_one',
    ('code', 'point_reasons_are_the_code_and_6_4_names_each'): _C + 'names_refuse_one_by_one',
    ('code', 'anchor_commit_problems_named_in_12_4'): _C + 'names_refuse_one_by_one',
    ('code', 'builder_labels_quoted_verbatim_in_16'): _C + 'names_refuse_one_by_one',
    ('code', 'verifier_rule_names_are_the_code'): _C + 'names_refuse_one_by_one',
    ('code', 'summary_decision_is_the_result_and_logged_decision_beside_it'):
        _C + 'names_refuse_one_by_one',
    ('code', 'no_decision_point_reads_abort_owed'): _C + 'a_point_that_ignores_abort_owed_is_refused',
    ('code', 'supervision_state_replays_abort_owed'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'crossing_after_the_point_not_acted_on_with_its_reason'):
        _C + 'a_point_that_ignores_abort_owed_is_refused',
    ('code', 'crossing_before_the_point_missed_is_a_defect'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'an_unresolved_worker_stays_unresolved'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'an_unresolved_worker_is_a_no_decision_point'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'unread_counter_delta_is_null'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'null_fields_are_nullable_in_the_schema'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'decision_receipt_commit_check_is_wired'): _C + 'behaviours_refuse_one_by_one',
    ('postconditions', 'reverting_the_insertions_reproduces_each_preimage'):
        _I + 'an_inserter_that_also_edits_another_byte_is_refused',
    ('postconditions', 'every_insertion_inside_its_section_beside_its_anchor'):
        'test_an_insertion_moved_out_of_its_section_is_refused',
    ('postconditions', 'no_cr_byte_after'): 'test_each_faulty_inserter_is_refused',
    # IMPLIED by config_json_byte_identical, configuration_blocks_byte_identical and the
    # precondition three_way_contract_before; the named test makes it False with them
    ('postconditions', 'three_way_contract_after'): 'test_each_faulty_inserter_is_refused',
    ('postconditions', 'config_json_byte_identical'): 'test_each_faulty_inserter_is_refused',
    ('postconditions', 'configuration_blocks_byte_identical'):
        'test_each_faulty_inserter_is_refused',
    ('postconditions', 'vocabulary_sections_1_3_11_byte_identical'):
        _I + 'an_insertion_in_section_1_is_refused',
    # IMPLIED by config_json_byte_identical and pins.rule_block_before_is_the_pin
    ('postconditions', 'rule_block_after_is_the_pin'): 'test_each_faulty_inserter_is_refused',
    ('postconditions', 'v2_insertions_intact'): _I + 'an_insertion_inside_a_v2_text_is_refused',
    ('postconditions', 'architecture_and_protocol_changed'):
        'test_postconditions_refuse_unchanged_documents',
    ('negative_control', 'every_moved_variant_refused_on_placement'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'config_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'v2_split_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'vocabulary_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'scratch_copies_unchanged'):
        None,   # NO REAL INPUT: only a filesystem fault while the control runs
    ('negative_control', 'real_documents_unchanged'):
        None,   # NO REAL INPUT: only another writer changing the real files mid-run
    ('successor_commit', 'prior_successor_commit_carries_the_prior_successor'):
        'test_a_history_whose_474f9d8_is_not_the_prior_successor_is_refused',
    ('cells', 'cells_unchanged_outside_superseded_by'):
        None,   # NO REAL INPUT: the new cells.json is built by replacing that one key
    ('final', 'documents_read_back_equal_computed'):
        None,   # NO REAL INPUT: only a filesystem fault between the write and the read
    # NO REAL INPUT: config.json is never written by the tool
    ('final', 'config_on_disk_unchanged'): None,
    ('final', 'no_harness_file_changed'): 'test_a_harness_file_that_moves_withholds_the_receipt',
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
    return _load(TOOL, 'repair_amendment_v3')


def _load_verifier():
    return _load(HERE / 'verify_repair_amendment_v3.py', 'verify_repair_amendment_v3')


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


def _cells_with(raw: bytes, fn) -> bytes:
    c = json.loads(raw)
    fn(c['provenance']['vocabulary_alignment'])
    return (json.dumps(c, indent=1) + '\n').encode('utf-8')


class _Harness:
    """setUpClass, _drive and the refusal helpers shared by the witness classes (a mixin: it
    defines no test)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
            cls.V2 = _blob(PRE_REV, V2_REL)
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history (474f9d8) is not available here: %s' % e)

    def _drive(self, docs, patch=None, wrap_insert_all=None, commit_protocol=None, v2=None,
               v2_committed=None, ancestry=0, wraps=None, code_patches=(), harness=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the four files after)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='repair_v3_witness_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, rel in REL.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(docs[k])
        (tmp / V2_REL).parent.mkdir(parents=True, exist_ok=True)
        v2_bytes = self.V2 if v2 is None else v2
        (tmp / V2_REL).write_bytes(v2_bytes)
        m = _load_tool()
        m.REPO = tmp
        for k, rel in REL.items():
            setattr(m, k, tmp / rel)
        m.V2_RECEIPT = tmp / V2_REL
        for name, value in (patch or {}).items():
            setattr(m, name, value)
        if wrap_insert_all is not None:
            m.insert_all = wrap_insert_all(m.insert_all, m)
        for name, fn in (wraps or {}).items():
            setattr(m, name, fn(getattr(m, name), m))
        for name in ('REPO', 'V2_RECEIPT') + tuple(REL):
            here = Path(getattr(m, name)).resolve()
            self.assertTrue(here == tmp.resolve() or tmp.resolve() in here.parents,
                            '%s escaped the scratch directory: %s' % (name, here))
        succ = self.PRE['PROTO'] if commit_protocol is None else commit_protocol
        committed = v2_bytes if v2_committed is None else v2_committed

        def fake_run(argv_, *a, **kw):
            if argv_[:1] == ['git'] and 'rev-parse' in argv_:
                return types.SimpleNamespace(stdout='0' * 40 + '\n', returncode=0)
            if argv_[:1] == ['git'] and 'merge-base' in argv_:
                return types.SimpleNamespace(stdout=b'', returncode=ancestry)
            if argv_[:1] == ['git'] and 'show' in argv_:
                rev, path = argv_[-1].split(':', 1)
                if rev == PRE_REV and path == REL['PROTO']:
                    return types.SimpleNamespace(stdout=succ, returncode=0)
                if rev == PRE_REV and path == V2_REL:
                    return types.SimpleNamespace(stdout=committed, returncode=0)
            raise AssertionError('unexpected subprocess call: %r' % (argv_,))
        m.subprocess = types.SimpleNamespace(run=fake_run, CalledProcessError=
                                             subprocess.CalledProcessError)
        err = io.StringIO()
        hashes = harness or (lambda: {'config.json': 'stub'})
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(m.lab_common, 'harness_file_hashes',
                                                  side_effect=hashes))
            for obj, attr, value in code_patches:
                stack.enter_context(mock.patch.object(obj, attr, value))
            stack.enter_context(contextlib.redirect_stderr(err))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            rc = m.main([])
        found = sorted((tmp / 'results' / 'live_ab').glob(RECEIPT_GLOB))
        receipt = json.loads(found[0].read_bytes()) if found else None
        after = {k: (tmp / rel).read_bytes() for k, rel in REL.items()}
        self.assertEqual(_real_digests(), before_real,
                         'a real document or results/live_ab changed')
        self._tmp = tmp
        return rc, err.getvalue(), receipt, after

    def _assert_refused_unchanged(self, docs, rc, err, receipt, after, why):
        self.assertEqual(rc, 2, '%s: expected a refusal, got exit %r (%s)' % (why, rc, err[:800]))
        self.assertIsNone(receipt, '%s: a receipt was written' % why)
        for k in REL:
            self.assertEqual(after[k], docs[k], '%s: %s was changed' % (why, k))

    def _repin(self, d):
        """Point the cells successor and every pre-image pin at the documents ``d``."""
        d = dict(d)
        d['CELLS'] = _cells_with(d['CELLS'], lambda va: va['superseded_by'].__setitem__(
            'sha256', sha(d['PROTO'])))
        patch = {'PRIOR_SUCCESSOR': sha(d['PROTO']), 'PRIOR_CONFIG_SHA256': sha(d['CONFIG']),
                 'PRIOR_CONFIG_BYTES': len(d['CONFIG']), 'PRIOR_ARCH_SHA256': sha(d['ARCH']),
                 'PRIOR_CELLS_SHA256': sha(d['CELLS'])}
        return d, patch

    def _v2_for(self, d, fn=None):
        """The v2 receipt with ``written`` pointing at the documents ``d`` (and ``fn`` applied),
        and the pin patch that accepts it."""
        r = json.loads(self.V2)
        r['written'].update(config_sha256=sha(d['CONFIG']), architecture_sha256=sha(d['ARCH']),
                            protocol_sha256=sha(d['PROTO']), cells_sha256=sha(d['CELLS']))
        if fn is not None:
            fn(r)
        raw = (json.dumps(r, indent=1, sort_keys=True) + '\n').encode('utf-8')
        return raw, {'V2_RECEIPT_SHA256': sha(raw)}

    def _refused_alone(self, gate_json: dict, check: str, why: str):
        self.assertIs(gate_json[check], False, '%s: %s' % (why, gate_json))
        others = {k: v for k, v in gate_json.items() if k != check}
        self.assertTrue(all(v is True for v in others.values()), '%s: %s' % (why, others))

    def _code_refusal(self, code_patches, check, alone=True, **kw):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, code_patches=code_patches, **kw)
        self._assert_refused_unchanged(d, rc, err, receipt, after, check)
        g = _printed(err)['gate']
        if alone:
            self._refused_alone(g, check, check)
        else:
            self.assertIs(g[check], False, g)
        return g


class RepairAmendmentV3WitnessTests(_Harness, unittest.TestCase):

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(len(self.PRE['CONFIG']), 16136)
        self.assertEqual(sha(self.V2), V2_SHA256)
        self.assertEqual((m.PRIOR_CONFIG_SHA256, m.PRIOR_ARCH_SHA256, m.PRIOR_SUCCESSOR,
                          m.PRIOR_CELLS_SHA256),
                         (REVIEWED['CONFIG'], REVIEWED['ARCH'], REVIEWED['PROTO'],
                          REVIEWED['CELLS']))
        self.assertEqual(m.PRIOR_RULE_BLOCK, RULE_BLOCK)
        self.assertEqual(m.PRIOR_SUCCESSOR_COMMIT, PRE_REV)
        self.assertEqual(m.V2_RECEIPT_SHA256, V2_SHA256)
        # the six recorded entries are the ones the validation pin test records
        sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(tuple((e['sha256'], sha(json.dumps(e, sort_keys=True).encode()))
                               for e in sb['prior_successors']), m.PRIOR_ENTRIES)
        # the documents of this checkout are still these pre-images, or the delivery
        now = {k: sha((REPO / rel).read_bytes()) for k, rel in REL.items()}
        self.assertEqual(now['CONFIG'], REVIEWED['CONFIG'])

    # -- control: the pristine pre-images are amended ------------------------------------
    def test_control_the_pristine_pre_images_are_amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        m = _load_tool()
        self.assertEqual(after['CONFIG'], self.PRE['CONFIG'], 'config.json was written')
        for k, doc in (('ARCH', 'architecture'), ('PROTO', 'protocol')):
            self.assertNotEqual(after[k], self.PRE[k])
            self.assertEqual(m.remove_all(after[k], doc), self.PRE[k], k)
        if DELIVERED is not None:
            for k, want in DELIVERED.items():
                self.assertEqual(sha(after[k]), want, k)
            self.assertEqual(_normalized_cells(after['CELLS']), DELIVERED_CELLS_NORMALIZED_SHA256)
        real = {k: (REPO / rel).read_bytes() for k, rel in REL.items()}
        if sha(real['PROTO']) != REVIEWED['PROTO']:
            # the real run has been made: the drive reproduces the delivered documents
            for k in ('CONFIG', 'ARCH', 'PROTO'):
                self.assertEqual(after[k], real[k], k)
            self.assertEqual(_normalized_cells(after['CELLS']), _normalized_cells(real['CELLS']))
        post = receipt['postcondition_checked']
        self.assertEqual(len(post['every_insertion_inside_its_section_beside_its_anchor']), 10)
        self.assertTrue(all(post['gate'].values()), post['gate'])
        self.assertEqual(post['vocabulary_sections_1_3_11_byte_identical'],
                         {'1': True, '3': True, '11': True})
        self.assertEqual(post['rule_block_sha256_after'], RULE_BLOCK)
        self.assertEqual(len(post['v2_insertions_intact']), 27)
        control = receipt['negative_control']
        self.assertEqual(control['variants_run'], 13)
        self.assertTrue(all(v['refused'] for v in control['variants'].values()))
        self.assertTrue(all(control['gate'].values()), control['gate'])
        self.assertTrue(all(receipt['code_checked_at_run_time']['gate'].values()))
        self.assertEqual(receipt['predecessor_amendment_v2']['receipt_sha256'], V2_SHA256)
        self.assertEqual(receipt['written']['harness_entries_changed'], [])
        # cells.json: 6c0ebf2f demoted whole with 474f9d8
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        old_sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment'][
            'superseded_by']
        self.assertEqual(sb['sha256'], sha(after['PROTO']))
        self.assertEqual(sb['supersedes'], m.ORIGINAL_PIN)
        self.assertTrue(sb['reason'].startswith('NOT an Appendix B change:'))
        self.assertEqual(len(sb['prior_successors']), 7)
        self.assertEqual(sb['prior_successors'][:6], old_sb['prior_successors'])
        last = sb['prior_successors'][6]
        self.assertEqual({k: v for k, v in last.items() if k not in (
            'changing_commit_of_this_successor', 'changing_commit_note')},
            {k: v for k, v in old_sb.items() if k not in (
                'prior_successors', 'changing_commit_note', 'correction_to_the_owner_report')})
        self.assertEqual(last['changing_commit_of_this_successor'], PRE_REV)
        self.assertIn('git show 474f9d8:', last['changing_commit_note'])
        self.assertEqual(sb['correction_to_the_owner_report'],
                         old_sb['correction_to_the_owner_report'])
        a, b = json.loads(self.PRE['CELLS']), json.loads(after['CELLS'])
        a['provenance']['vocabulary_alignment'].pop('superseded_by')
        b['provenance']['vocabulary_alignment'].pop('superseded_by')
        self.assertEqual(a, b)

    def test_the_amended_documents_are_refused(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        rc, err, receipt, again = self._drive(dict(after))
        self._assert_refused_unchanged(after, rc, err, receipt, again, 'second run')
        g = _printed(err)['gate_pins']
        self.assertIs(g['config_is_the_reviewed_preimage'], True)
        for check in ('architecture_is_the_reviewed_preimage', 'protocol_is_the_reviewed_preimage',
                      'cells_is_the_reviewed_preimage'):
            self.assertIs(g[check], False, check)

    def test_isolated_a_config_that_is_not_the_preimage_is_refused(self):
        old, new = b'"battery_percent": 20', b'"battery_percent": 21'
        d = {k: (v.replace(old, new, 1) if k in ('CONFIG', 'ARCH', 'PROTO') else v)
             for k, v in self.PRE.items()}
        self.assertNotEqual(d['CONFIG'], self.PRE['CONFIG'])
        d, patch = self._repin(d)
        patch.pop('PRIOR_CONFIG_SHA256')
        rc, err, receipt, after = self._drive(d, patch=patch)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'other config')
        self._refused_alone(_printed(err)['gate_pins'], 'config_is_the_reviewed_preimage',
                            'other config')

    def test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed(self):
        p = self.PRE['PROTO']
        i = p.index(b'\n')
        d, patch = self._repin(dict(self.PRE, PROTO=p[:i] + b'\r' + p[i:]))
        rc, err, receipt, after = self._drive(d, patch=patch)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CR in protocol')
        g = _printed(err)['gate_pins']
        self.assertIs(g['no_cr_byte'], False)
        self.assertIs(g['three_way_contract_before'], False)

    def test_each_cells_or_rule_block_precondition_refuses(self):
        def ser(c, indent=1):
            return (json.dumps(c, indent=indent) + '\n').encode('utf-8')

        def edit_entry(va):
            va['superseded_by']['prior_successors'][2]['reason'] += ' '
        anchor = b'"auto_abort": {"consecutive_infrastructure_failures": 10'
        rb = {k: self.PRE[k].replace(anchor, anchor[:-2] + b'11', 1)
              for k in ('CONFIG', 'ARCH', 'PROTO')}
        cases = {
            'rule_block_before_is_the_pin': dict(rb),
            'cells_round_trips': {'CELLS': ser(json.loads(self.PRE['CELLS']), indent=2)},
            'cells_original_pin_untouched': {'CELLS': _cells_with(
                self.PRE['CELLS'], lambda va: va.__setitem__('sha256', '0' * 64))},
            'cells_current_successor_is_the_prior_successor': {'CELLS': _cells_with(
                self.PRE['CELLS'], lambda va: va['superseded_by'].__setitem__('sha256', '1' * 64))},
            'cells_successor_supersedes_the_original': {'CELLS': _cells_with(
                self.PRE['CELLS'],
                lambda va: va['superseded_by'].__setitem__('supersedes', '2' * 64))},
            'cells_prior_successors_are_the_recorded_entries': {'CELLS': _cells_with(
                self.PRE['CELLS'], edit_entry)},
        }
        for check, new in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                d.update(new)
                if check == 'rule_block_before_is_the_pin':
                    d, patch = self._repin(d)
                else:
                    patch = {'PRIOR_CELLS_SHA256': sha(d['CELLS'])}
                rc, err, receipt, after = self._drive(d, patch=patch)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate_pins'], check, check)

    def test_a_dropped_prior_successor_is_refused(self):
        d = dict(self.PRE, CELLS=_cells_with(
            self.PRE['CELLS'], lambda va: va['superseded_by']['prior_successors'].pop(0)))
        rc, err, receipt, after = self._drive(d, patch={'PRIOR_CELLS_SHA256': sha(d['CELLS'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'dropped entry')
        g = _printed(err)['gate_pins']
        self.assertIs(g['cells_prior_successor_count'], False)
        self.assertIs(g['cells_prior_successors_are_the_recorded_entries'], False)

    # -- anchors ---------------------------------------------------------------
    def test_an_absent_or_duplicated_anchor_is_refused(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.12_4')
        for what, proto in (('absent', self.PRE['PROTO'].replace(ins.anchor, b'', 1)),
                            ('duplicated', self.PRE['PROTO'].replace(
                                ins.anchor, ins.anchor + ins.anchor, 1))):
            with self.subTest(what=what):
                d, patch = self._repin(dict(self.PRE, PROTO=proto))
                v2, vpatch = self._v2_for(d)
                patch.update(vpatch)
                rc, err, receipt, after = self._drive(d, patch=patch, v2=v2)
                self._assert_refused_unchanged(d, rc, err, receipt, after, what)
                g = _printed(err)['gate_anchors']
                self.assertIs(g['every_anchor_once'], False)
                self.assertIs(g['no_anchor_error'], False)

    def test_isolated_an_interloper_heading_puts_an_anchor_outside_its_section(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'protocol.5_3')
        p = self.PRE['PROTO']
        i = p.index(ins.anchor)
        d, patch = self._repin(dict(self.PRE, PROTO=p[:i] + b'### 5.3b Interloper\n\n' + p[i:]))
        rc, err, receipt, after = self._drive(d, patch=patch)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'interloper')
        self._refused_alone(_printed(err)['gate_anchors'], 'every_anchor_inside_its_section',
                            'interloper')

    def test_isolated_an_inserted_text_of_the_wrong_form_is_refused(self):
        m = _load_tool()
        bad = tuple(m.Insertion(i.key, i.doc, i.anchor, i.side,
                                i.text + b'a trailing space \n' if i.key == 'protocol.13_1'
                                else i.text, i.section, i.section_end) for i in m.INSERTIONS)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': bad})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'form')
        self._refused_alone(_printed(err)['gate_anchors'], 'inserted_text_form', 'form')

    # -- amendment v2 --------------------------------------------------------------
    def test_each_amendment_v2_condition_refuses(self):
        other = json.loads(self.V2)
        other['generated_utc'] = '2026-09-24T09:27:09Z'
        other_raw = (json.dumps(other, indent=1, sort_keys=True) + '\n').encode('utf-8')
        split, split_patch = self._v2_for(self.PRE, lambda r: r['insertions'][10].__setitem__(
            'text', r['insertions'][10]['text'] + 'X'))
        wrote, wrote_patch = self._v2_for(self.PRE, lambda r: r['written'].__setitem__(
            'protocol_sha256', '0' * 64))
        cases = {
            'v2_receipt_is_the_pinned_bytes': {'v2': other_raw},
            'v2_receipt_is_committed_in_474f9d8': {'v2_committed': b'{}'},
            'v2_commit_is_an_ancestor_of_head': {'ancestry': 1},
            'v2_wrote_the_preimages': {'v2': wrote, 'patch': wrote_patch},
            'v2_insertions_whole_in_the_preimages': {'v2': split, 'patch': split_patch},
        }
        for check, kw in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, **kw)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate'], check, check)

    # -- the code the prose describes ------------------------------------------------
    def test_code_names_refuse_one_by_one(self):
        import lab_eventlog as ev
        import lab_orchestrator as orch
        import build_live_ab_results as bld
        schema = dict(ev.EVENT_SCHEMA)
        schema['abort_owed'] = dict(schema['abort_owed'], hook=ev.EVENT_SCHEMA['abort_owed']['reason'])
        verify_copy = Path(tempfile.mkdtemp(prefix='repair_v3_verify_log_')) / 'lab_verify_log.py'
        self.addCleanup(shutil.rmtree, verify_copy.parent, True)
        verify_copy.write_text((REPO / 'experiments/live_ab/lab_verify_log.py').read_text('utf-8')
                               .replace("'abort_point_missing'", "'abort_point_absent'"))

        def old_build(*a, **kw):                                  # the pre-19:05 summary shape
            return {'decision': 'logged kind'}
        cases = {
            'row_31_names_exactly_the_abort_sources': ([(ev, 'ABORT_SOURCES',
                                                         ev.ABORT_SOURCES + ('hook',))], {}),
            'row_31_names_exactly_the_abort_owed_fields': ([(ev, 'EVENT_SCHEMA', schema)], {}),
            'abort_owed_is_trial_only_and_durable_in_the_prose': (
                [(ev, 'TRIAL_ONLY_TYPES', ev.TRIAL_ONLY_TYPES - {'abort_owed'})], {}),
            'point_reasons_are_the_code_and_6_4_names_each': (
                [(ev, 'INELIGIBLE_REASONS', dict(ev.INELIGIBLE_REASONS, hook_abort='a hook'))], {}),
            'anchor_commit_problems_named_in_12_4': (
                [(orch, 'ANCHOR_COMMIT_PROBLEMS', orch.ANCHOR_COMMIT_PROBLEMS + ('no_remote',))],
                {}),
            'builder_labels_quoted_verbatim_in_16': (
                [(bld, 'ABORT_INCOMPLETE_LABEL', 'incomplete: aborted')], {}),
            'verifier_rule_names_are_the_code': ([], {'patch': {'REL_VERIFY_LOG': str(verify_copy)}}),
            'summary_decision_is_the_result_and_logged_decision_beside_it': (
                [(bld, 'build', old_build)], {}),
        }
        for check, (patches, kw) in cases.items():
            with self.subTest(check=check):
                self._code_refusal(patches, check, **kw)

    def test_code_a_point_that_ignores_abort_owed_is_refused(self):
        """The no-decision point as it stood before 7ebffad (no ``abort_owed``): the point is
        not read and the drain's crossing is no longer not acted on."""
        import lab_eventlog as ev
        real = ev.no_decision_point

        def before_7ebffad(events, cap, **kw):
            return real([e for e in events if e['type'] != 'abort_owed'], cap, **kw)
        g = self._code_refusal([(ev, 'no_decision_point', before_7ebffad)],
                               'no_decision_point_reads_abort_owed', alone=False)
        self.assertIs(g['crossing_after_the_point_not_acted_on_with_its_reason'], False)
        others = {k: v for k, v in g.items() if k not in (
            'no_decision_point_reads_abort_owed',
            'crossing_after_the_point_not_acted_on_with_its_reason')}
        self.assertTrue(all(v is True for v in others.values()), others)

    def test_code_behaviours_refuse_one_by_one(self):
        import lab_eventlog as ev
        import lab_orchestrator as orch
        real_sup, real_elig = orch.supervision_state, ev.decision_eligibility
        real_point, real_rec = ev.no_decision_point, orch.reconciliation_windows

        def sup_forgets(events, cap):
            return real_sup([e for e in events if e['type'] != 'abort_owed'], cap)

        def blanket_exemption(*a, **kw):
            out = real_elig(*a, **kw)
            if out.get('crossing') and out['crossing']['verdict'] == 'missed':
                out['crossing'] = dict(out['crossing'], verdict='not_acted_on')
            return out

        def last_state_wins(events):
            out = {}
            for e in events:
                if e['type'] == 'worker_resolved':
                    out[(int(e['body']['arrival']), int(e['body']['attempt']))] = e['body']['state']
            return out

        def point_without_workers(events, cap, **kw):
            return real_point([e for e in events if e['type'] != 'worker_resolved'], cap, **kw)

        def zero_counters(*a, **kw):
            rows = real_rec(*a, **kw)
            for r in rows:
                r['counter_delta'] = {k: (0 if v is None else v)
                                      for k, v in r['counter_delta'].items()}
            return rows
        schema = dict(ev.EVENT_SCHEMA)
        schema['worker_resolved'] = dict(schema['worker_resolved'],
                                         spool_bytes_at_resolution=ev.FieldSpec('int'))

        def unwired(*a, **kw):
            return None, {}
        cases = {
            'supervision_state_replays_abort_owed': [(orch, 'supervision_state', sup_forgets)],
            'crossing_before_the_point_missed_is_a_defect': [
                (ev, 'decision_eligibility', blanket_exemption)],
            'an_unresolved_worker_stays_unresolved': [
                (orch, 'effective_worker_states', last_state_wins)],
            'an_unresolved_worker_is_a_no_decision_point': [
                (ev, 'no_decision_point', point_without_workers)],
            'unread_counter_delta_is_null': [(orch, 'reconciliation_windows', zero_counters)],
            'null_fields_are_nullable_in_the_schema': [(ev, 'EVENT_SCHEMA', schema)],
            'decision_receipt_commit_check_is_wired': [
                (orch, 'decision_evidence_verdict', unwired)],
        }
        for check, patches in cases.items():
            with self.subTest(check=check):
                self._code_refusal(patches, check)

    # -- postconditions -------------------------------------------------------------
    def _moving(self, key):
        def wrap(real, m):
            ins = next(i for i in m.INSERTIONS if i.key == key)

            def moved(old):
                return m.move_out(real(old), ins)
            return moved
        return wrap

    def test_an_insertion_moved_out_of_its_section_is_refused(self):
        for key in ('protocol.5_3', 'protocol.6_4', 'protocol.12_4', 'protocol.14_6',
                    'protocol.16', 'architecture.4_4', 'architecture.7_1.row_21c'):
            with self.subTest(key=key):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=self._moving(key))
                self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved ' + key)
                self._refused_alone(_printed(err)['gate'],
                                    'every_insertion_inside_its_section_beside_its_anchor', key)

    def test_isolated_an_inserter_that_also_edits_another_byte_is_refused(self):
        def wrap(real, m):
            def edits(old):
                out = real(old)
                return dict(out, architecture=out['architecture'] + b'x\n')
            return edits
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'extra edit')
        self._refused_alone(_printed(err)['gate'],
                            'reverting_the_insertions_reproduces_each_preimage', 'extra edit')

    def test_each_faulty_inserter_is_refused(self):
        anchor = b'"consecutive_infrastructure_failures": 10'

        def wrap_with(fn):
            def wrap(real, m):
                return lambda old: fn(real(old))
            return wrap
        cases = {
            'no_cr_byte_after': (lambda out: dict(out, protocol=out['protocol'] + b'\r\n'),
                                 ('no_cr_byte_after', 'three_way_contract_after')),
            'config_json_byte_identical': (
                lambda out: dict(out, config=out['config'].replace(b'\n}', b'\n }', 1)),
                ('config_json_byte_identical', 'three_way_contract_after')),
            'configuration_blocks_byte_identical': (
                lambda out: dict(out, protocol=out['protocol'].replace(
                    b'"battery_percent": 20', b'"battery_percent": 21', 1)),
                ('configuration_blocks_byte_identical', 'three_way_contract_after')),
            'rule_block_after_is_the_pin': (
                lambda out: {k: (v.replace(anchor, anchor[:-2] + b'11', 1)) for k, v in out.items()},
                ('rule_block_after_is_the_pin', 'config_json_byte_identical',
                 'configuration_blocks_byte_identical')),
        }
        for name, (fn, must_fail) in cases.items():
            with self.subTest(case=name):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=wrap_with(fn))
                self._assert_refused_unchanged(d, rc, err, receipt, after, name)
                g = _printed(err)['gate']
                for check in must_fail:
                    self.assertIs(g[check], False, (name, check, g))

    def _extra(self, m, key, doc, anchor, side, text, section, section_end):
        return m.Insertion(key, doc, anchor, side, text, section, section_end)

    def test_isolated_an_insertion_in_section_1_is_refused(self):
        m = _load_tool()
        p = self.PRE['PROTO']
        s0 = p.index(b'## 1. Purpose, scope')
        line = p[s0:p.index(b'\n', s0) + 1]
        extra = self._extra(m, 'probe.section_1', 'protocol', line, 'after', b'\nA probe.\n',
                            b'## 1. Purpose, scope', b'## 2. ')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': m.INSERTIONS + (extra,)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'section 1')
        self._refused_alone(_printed(err)['gate'], 'vocabulary_sections_1_3_11_byte_identical',
                            'section 1')

    def test_isolated_an_insertion_inside_a_v2_text_is_refused(self):
        m = _load_tool()
        extra = self._extra(m, 'probe.inside_v2', 'protocol', b'| 30 | `anchor_receipt_rejected` | ',
                            'after-line', b'| 30b | `probe` | a probe | no |\n',
                            b'### 12.2 Event schema', b'### 12.3 The hash rule')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': m.INSERTIONS + (extra,)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'inside v2')
        self._refused_alone(_printed(err)['gate'], 'v2_insertions_intact', 'inside v2')

    def test_postconditions_refuse_unchanged_documents(self):
        m = _load_tool()
        old = {'config': self.PRE['CONFIG'], 'architecture': self.PRE['ARCH'],
               'protocol': self.PRE['PROTO']}
        post, ok = m.postconditions(old, dict(old), json.loads(self.V2))
        self.assertIs(ok, False)
        self.assertIs(post['gate']['architecture_and_protocol_changed'], False)

    # -- negative control, successor, final ----------------------------------------------
    def test_a_negative_control_that_cannot_refuse_stops_the_run(self):
        def identity_moves(real, m):
            return lambda new, ins: dict(new)

        def no_extras(which):
            def wrap(real, m):
                def extras(new):
                    out = real(new)
                    out[which] = dict(new)
                    return out
                return extras
            return wrap
        cases = {'every_moved_variant_refused_on_placement': {'move_out': identity_moves},
                 'config_variant_refused': {'extra_variants': no_extras('config_byte_changed')},
                 'v2_split_variant_refused': {'extra_variants': no_extras('v2_text_split')},
                 'vocabulary_variant_refused': {
                     'extra_variants': no_extras('vocabulary_section_1_touched')}}
        for check, wraps in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wraps=wraps)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate'], check, check)

    def test_a_history_whose_474f9d8_is_not_the_prior_successor_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, commit_protocol=b'not the v2 protocol')
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'successor commit')
        self.assertIn('does not carry the prior successor', err)

    def test_a_harness_file_that_moves_withholds_the_receipt(self):
        calls = iter([{'config.json': 'a'}, {'config.json': 'b'}])
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, harness=lambda: next(calls))
        self.assertEqual(rc, 2, err)
        self.assertIsNone(receipt)
        self.assertIn('"no_harness_file_changed": false', err)

    def test_an_existing_receipt_is_never_replaced(self):
        m = _load_tool()
        self.assertIn("open(receipt_path, 'x'", inspect.getsource(m.main))


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
                    else:
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
                self.assertTrue(hasattr(RepairAmendmentV3WitnessTests, test), test)


class ProseTests(unittest.TestCase):
    """The prose says what the code performs: every closed name and every dotted code name it
    uses is read back from the code, and the order of the reported results is the builder's."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load_tool()
        import lab_eventlog
        import lab_orchestrator
        import build_live_ab_results
        import lab_verify_log
        cls.ev, cls.orch, cls.bld, cls.vl = (lab_eventlog, lab_orchestrator,
                                             build_live_ab_results, lab_verify_log)

    def all_text(self):
        return ''.join(i.text.decode() for i in self.m.INSERTIONS)

    def test_row_31_and_t35_name_the_sources_and_fields_of_the_schema(self):
        for text, start in ((self.m.P3_12_2, '| 31 |'), (self.m.A3_4_4, '| T35 |')):
            row = next(ln for ln in text.split('\n') if ln.startswith(start))
            for f in self.ev.ABORT_OWED_FIELDS:
                self.assertIn('`%s`' % f, row)
            for s in self.ev.ABORT_SOURCES:
                self.assertIn('`%s`' % s, row)
        self.assertEqual(sorted(self.ev.EVENT_SCHEMA['abort_owed']),
                         sorted(self.ev.ABORT_OWED_FIELDS))

    def test_every_abort_source_is_written_by_the_orchestrator(self):
        src = inspect.getsource(self.orch)
        for s in self.ev.ABORT_SOURCES:
            with self.subTest(source=s):
                self.assertIn("'%s'" % s, src)

    def test_the_no_decision_reasons_are_the_code(self):
        self.assertEqual(sorted(set(self.ev.INELIGIBLE_REASONS) - {'decision_logged', 'drain_look'}),
                         sorted(self.m.POINT_REASONS))
        src = inspect.getsource(self.ev.no_decision_point)
        for r in self.m.POINT_REASONS:
            self.assertIn("'%s'" % r, src)

    def test_the_anchor_commit_checks_are_named_in_their_order(self):
        """12.4 names the problem codes in the order anchor_commit_problem checks them."""
        src = inspect.getsource(self.orch.anchor_commit_problem)
        order_code = sorted(self.orch.ANCHOR_COMMIT_PROBLEMS, key=lambda c: src.index("'%s'" % c))
        order_prose = sorted(self.orch.ANCHOR_COMMIT_PROBLEMS,
                             key=lambda c: self.m.P3_12_4.index('`%s`' % c))
        self.assertEqual(order_prose[:-1], [c for c in order_code if c != 'repo_unreadable'])
        self.assertEqual(order_prose[-1], 'repo_unreadable')

    def test_the_results_are_in_the_builders_order_first_match_wins(self):
        flat = ' '.join(self.m.P3_16.split())
        names = ('DECISION_INVALID_LABEL', 'RESTART_CAP_INCOMPLETE_LABEL', 'ABORT_INCOMPLETE_LABEL',
                 'PROVISIONAL_LABEL')
        prose = [flat.index('`%s`' % getattr(self.bld, n)) for n in names]
        self.assertEqual(prose, sorted(prose))
        src = inspect.getsource(self.bld.decision_object)
        code = [src.index('primary, reportable = %s' % n) if n != 'DECISION_INVALID_LABEL'
                else src.index('primary, reportable, label = %s' % n) for n in names]
        self.assertEqual(code, sorted(code))

    def test_every_dotted_code_name_of_the_prose_exists(self):
        mods = {'lab_eventlog': self.ev, 'lab_orchestrator': self.orch,
                'build_live_ab_results': self.bld, 'lab_verify_log': self.vl}
        found = set(re.findall(r'`((?:lab_\w+|build_live_ab_results)\.[\w.]+?)(?:\(\.\.\.\))?`',
                               self.all_text()))
        self.assertTrue(found)
        for dotted in sorted(found):
            with self.subTest(name=dotted):
                mod, *path = dotted.split('.')
                obj = mods[mod]
                for p in path:
                    obj = getattr(obj, p)

    def test_the_verifier_consequences_are_the_code(self):
        src = inspect.getsource(self.vl._check_decision_eligibility)
        for name in ('decision_after_no_decision_point', 'abort_point_missing',
                     'NOT_ACTED_ON_restart_cap_before_decision',
                     'NOT_ACTED_ON_abort_before_decision'):
            self.assertIn("'%s'" % name, src)
            self.assertIn('`%s`' % name, self.m.P3_6_4)

    def test_control_a_prose_naming_a_source_the_code_lacks_fails(self):
        row = next(ln for ln in self.m.P3_12_2.split('\n') if ln.startswith('| 31 |'))
        mutated = row.replace('`look_guard`', '`look_guard`, `hook`')
        src = mutated.split('`source` (', 1)[1].split(')', 1)[0]
        self.assertNotEqual(re.findall(r'`([A-Za-z_]+)`', src), list(self.ev.ABORT_SOURCES))


class VerifierTests(_Harness, unittest.TestCase):
    """The independent verifier on the control drive's output: it must verify the amendment
    and must NOT verify its negative controls."""

    KEYS = {'CONFIG': 'config', 'ARCH': 'architecture', 'PROTO': 'protocol', 'CELLS': 'cells'}
    CHECKS = ['parent_is_the_reviewed_preimage', 'receipt_lists_exactly_the_expected_insertions',
              'receipt_sections_agree_with_the_verifier_headings', 'each_insertion_occurs_once',
              'reverting_the_insertions_reproduces_the_parent', 'config_json_is_the_parent',
              'each_insertion_under_the_verifier_heading', 'no_cr_byte',
              'three_blocks_byte_identical_and_unchanged', 'rule_block_is_cbfd1792',
              'vocabulary_sections_identical', 'amendment_v2_kept_whole', 'cells',
              'content_in_the_documents', 'code_names_are_the_committed_code',
              'receipt_names_the_amended_protocol', 'receipt_written_digests_match']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CODE = {k: (REPO / ('experiments/live_ab/%s.py' % k)).read_bytes()
                    for k in ('lab_eventlog', 'lab_orchestrator', 'build_live_ab_results')}

    def _amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        before = {self.KEYS[k]: v for k, v in self.PRE.items()}
        out = {self.KEYS[k]: v for k, v in after.items()}
        return before, out, receipt

    def _reseal(self, after, receipt):
        receipt = json.loads(json.dumps(receipt))
        c = json.loads(after['cells'])
        c['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(after['protocol'])
        after = dict(after, cells=(json.dumps(c, indent=1) + '\n').encode('utf-8'))
        receipt['successor_provenance']['new_successor'] = sha(after['protocol'])
        for k in ('config', 'architecture', 'protocol', 'cells'):
            receipt['written']['%s_sha256' % k] = sha(after[k])
        return after, receipt

    def _args(self, before, after, receipt, **kw):
        base = {'before': before, 'after': after, 'receipt': receipt,
                'demoted_commit_protocol': self.PRE['PROTO'], 'v2_receipt': self.V2,
                'code': self.CODE}
        base.update(kw)
        return base

    def test_the_verifier_re_derives_the_amendment(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(**self._args(before, after, receipt))
        self.assertIs(got['all_verified'], True, json.dumps(got['checks']))
        self.assertEqual(list(got['checks']), self.CHECKS)
        ctl = v.negative_controls(before, after, receipt, self.PRE['PROTO'], self.V2, self.CODE)
        self.assertIs(ctl['every_control_failed'], True, ctl)
        self.assertEqual(len(ctl), 7)

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
                    got = v.verify(**self._args(before, after, receipt))
                self.assertIs(got['all_verified'], False)

    def test_each_verifier_check_can_fail_on_a_real_input(self):
        v = _load_verifier()
        before, after, receipt = self._amended()

        def with_receipt(fn):
            r = json.loads(json.dumps(receipt))
            fn(r)
            return self._args(before, after, r)

        def with_after(a):
            a, r = self._reseal(a, receipt)
            return self._args(before, a, r)
        text = {i['key']: i['text'].encode() for i in receipt['insertions']}
        p = after['protocol'].replace(text['protocol.14_6'], b'', 1)
        h = b'### 14.7 The operator is an AI agent session; blinding is procedural\n\n'
        j = p.index(h) + len(h)
        k = after['protocol'].index(b'## 1. Purpose, scope')
        k = after['protocol'].index(b'\n\n', k) + 2
        rb = b'"consecutive_infrastructure_failures": 10'
        code = dict(self.CODE, lab_eventlog=self.CODE['lab_eventlog'].replace(
            b"'look_guard')", b"'look_guard', 'hook')", 1))
        variants = {
            'parent_is_the_reviewed_preimage': self._args(
                dict(before, cells=before['cells'] + b' '), after, receipt),
            'receipt_lists_exactly_the_expected_insertions': with_receipt(
                lambda r: r['insertions'].pop()),
            'receipt_sections_agree_with_the_verifier_headings': with_receipt(
                lambda r: r['insertions'][-1].__setitem__('section', '### 7.2 What is fsynced')),
            'each_insertion_occurs_once': with_after(dict(
                after, protocol=after['protocol'] + text['protocol.13_1'])),
            'reverting_the_insertions_reproduces_the_parent': with_after(
                dict(after, protocol=after['protocol'] + b'\nextra\n')),
            'config_json_is_the_parent': with_after(dict(after, config=after['config'] + b' ')),
            'each_insertion_under_the_verifier_heading': with_after(
                dict(after, protocol=p[:j] + text['protocol.14_6'] + p[j:])),
            'no_cr_byte': with_after(dict(after, protocol=after['protocol'] + b'\r\n')),
            'three_blocks_byte_identical_and_unchanged': with_after(dict(
                after, architecture=after['architecture'].replace(
                    b'"battery_percent": 20', b'"battery_percent": 21', 1))),
            'rule_block_is_cbfd1792': with_after({d: (b.replace(rb, rb[:-2] + b'11', 1)
                                                      if d != 'cells' else b)
                                                  for d, b in after.items()}),
            'vocabulary_sections_identical': with_after(dict(
                after, protocol=after['protocol'][:k] + b'X' + after['protocol'][k:])),
            'amendment_v2_kept_whole': self._args(before, after, receipt,
                                                  v2_receipt=self.V2 + b' '),
            'cells': self._args(before, after, receipt,
                                demoted_commit_protocol=b'not the 474f9d8 protocol'),
            'content_in_the_documents': with_after(dict(after, protocol=after['protocol'].replace(
                b'**Only the last is reportable**', b'**Only the last is reported**', 1))),
            'code_names_are_the_committed_code': self._args(before, after, receipt, code=code),
            'receipt_names_the_amended_protocol': with_receipt(
                lambda r: r['successor_provenance'].__setitem__('new_successor', '0' * 64)),
            'receipt_written_digests_match': with_receipt(
                lambda r: r['written'].__setitem__('protocol_sha256', '0' * 64)),
        }
        self.assertEqual(sorted(variants), sorted(self.CHECKS))
        for name, args in variants.items():
            with self.subTest(check=name):
                got = v.verify(**args)
                self.assertIs(got['checks'][name], False)
                self.assertIs(got['all_verified'], False)

    def test_each_cells_sub_check_of_the_verifier_can_fail(self):
        """The ``cells`` check is a conjunction: each of its parts refuses a real defect of
        the successor history on its own (the mutation sweep found the changing commit
        unwitnessed)."""
        v = _load_verifier()
        before, after, receipt = self._amended()

        def edit(fn):
            c = json.loads(after['cells'])
            fn(c['provenance']['vocabulary_alignment'])
            a = dict(after, cells=(json.dumps(c, indent=1) + '\n').encode('utf-8'))
            r = json.loads(json.dumps(receipt))
            r['written']['cells_sha256'] = sha(a['cells'])
            return a, r

        def sb(va):
            return va['superseded_by']

        def other(c):
            c['provenance']['vocabulary_alignment']['note_added'] = 'x'
        cases = {
            'original_pin_untouched': lambda va: va.__setitem__('sha256', '0' * 64),
            'new_successor_is_the_amended_protocol':
                lambda va: sb(va).__setitem__('sha256', '1' * 64),
            'supersedes_the_original': lambda va: sb(va).__setitem__('supersedes', '2' * 64),
            'seven_prior_successors': lambda va: sb(va)['prior_successors'].append({}),
            'first_six_are_the_recorded_entries':
                lambda va: sb(va)['prior_successors'][1].__setitem__('reason', 'edited'),
            # the same input: the six entries of the pre-image ARE the recorded ones
            'first_six_unchanged':
                lambda va: sb(va)['prior_successors'][1].__setitem__('reason', 'edited'),
            'seventh_is_the_parent_successor_whole':
                lambda va: sb(va)['prior_successors'][6].__setitem__('reason', 'edited'),
            'seventh_names_its_commit': lambda va: sb(va)['prior_successors'][6].__setitem__(
                'changing_commit_of_this_successor', '48f4d70fbd580df282b551506448457a09ab514d'),
            'seventh_says_how_resolved': lambda va: sb(va)['prior_successors'][6].__setitem__(
                'changing_commit_note', 'resolved later'),
            'correction_moved_whole':
                lambda va: sb(va).__setitem__('correction_to_the_owner_report', 'x'),
            'reason_says_not_an_appendix_b_change':
                lambda va: sb(va).__setitem__('reason', 'Appendix B only'),
        }
        for name, fn in cases.items():
            with self.subTest(sub_check=name):
                a, r = edit(fn)
                got = v.verify(**self._args(before, a, r))
                self.assertIs(got['cells'][name], False, got['cells'])
                self.assertIs(got['all_verified'], False)
        c = json.loads(after['cells'])
        other(c)
        a = dict(after, cells=(json.dumps(c, indent=1) + '\n').encode('utf-8'))
        got = v.verify(**self._args(before, a, receipt))
        self.assertIs(got['cells']['nothing_outside_superseded_by_changed'], False)
        got = v.verify(**self._args(before, after, receipt, demoted_commit_protocol=b'x'))
        self.assertIs(got['cells']['demoted_commit_carries_the_parent_successor'], False)
        self.assertEqual(len(got['cells']), len(cases) + 2)

    def test_the_real_amendment_commit_verifies_if_present(self):
        """After the amendment is committed: the verifier's main() on the commit that ADDS a
        REPAIR_AMENDMENT_V3_RECEIPT.  Skipped before it exists."""
        log = subprocess.run(['git', '-C', str(REPO), 'log', '--diff-filter=A', '--format=%H',
                              '--name-only', '--', 'results/live_ab/'],
                             capture_output=True, text=True)
        commit, cur = None, None
        for line in log.stdout.splitlines() if log.returncode == 0 else ():
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                cur = line
            elif line.startswith('results/live_ab/REPAIR_AMENDMENT_V3_RECEIPT_'):
                commit = cur
                break
        if commit is None:
            self.skipTest('no commit in this history adds a v3 receipt')
        v = _load_verifier()
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = v.main([commit])
        self.assertEqual(rc, 0, err.getvalue())


if __name__ == '__main__':
    unittest.main()
