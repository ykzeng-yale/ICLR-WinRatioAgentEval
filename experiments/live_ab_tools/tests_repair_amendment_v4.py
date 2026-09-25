"""Witnesses for the pre-outcome amendment v4 (repair_amendment_v4.py), the v3 pattern.

HOW EVERY DRIVE RUNS
  The PRE-amendment blobs (`git show 56df17f:<path>`, read-only, once per class: the documents
  amendment v3 wrote, unchanged on this branch since, and the v3 and v2 receipts) are copied into a
  fresh temporary directory.  A fresh instance of the tool is loaded, and its paths REPO, CONFIG,
  ARCH, PROTO, CELLS, V3_RECEIPT and V2_RECEIPT are re-pointed at the copies (the harness asserts
  each lies under the temporary directory), so the documents and the receipt are written there
  only.  The tool's `subprocess` (git rev-parse / show / merge-base) is replaced in that instance
  only, and `lab_common.harness_file_hashes` is stubbed.  The code the prose describes is the REAL
  code of this checkout (its functions run on synthetic chains; a witness that needs the code to
  say something else patches one name for the length of one drive).  Every drive compares the
  digests of this checkout's real documents and the results/live_ab listing before and after.

WHAT A REFUSAL WITNESS SHOWS: two properties separately.
  * AGGREGATION (GateTests): every refusal of main() goes through gate(name, checks).  The gates
    and their checks are pinned (GATES); for EVERY (gate, check), a drive on the pristine
    pre-images sets that one check False at gate() and main() must refuse.
  * LIVENESS (the LIVENESS table): which REAL input makes each check False; `test_isolated_*`
    make ONLY that check False.  Checks that no real input can make alone False (implied by
    another check) or at all say so.

ProseTests: every closed name and dotted code name of the new prose is read back from the code.
VerifierTests: the independent verifier on the control drive's output, and on the real amendment
commit once it exists.

SCOPE: needs the git history (56df17f); without it the classes are skipped and the skip says why.
Nothing here runs a model, a server, a build or a network request.
"""

from __future__ import annotations

import __future__
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'repair_amendment_v4.py'
LAB = REPO / 'experiments' / 'live_ab'
for _p in (str(LAB), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json'}
V3_REL = 'results/live_ab/REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218.json'
V2_REL = 'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
PRE_REV = '56df17f72b17744d89564d0bf05f3fa84f4b8e1d'
REVIEWED = {'CONFIG': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
            'ARCH': '2ec71980de5b6a74df586c5790e6eac7c54dbd79342ae69dab1a01a0bb458190',
            'PROTO': '73dd0573955b2ef586e120f2b44558eb0227c70bbca9cbf9225ec4fb5583500c',
            'CELLS': '192804a4c1538df64a9902430d158e5174269fe2a6c77d8a0be2345304622e58'}
V3_SHA256 = 'cd71949e8c460c159e5bde5b4a3d9a843acb3cd116845b6fc91b6042dae6527a'
V2_SHA256 = '66efcb8b64b3e54d890ac70c77686e0678255fe6cba78347fa3a30878e12feff'
#: the delivered documents (the one real run, receipt REPAIR_AMENDMENT_V4_RECEIPT_20260925_1120),
#: and the delivered cells.json with the new successor's recorded_utc replaced by
#: RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED = {'CONFIG': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
             'ARCH': '4c762f2122c39c2a9698e09eaca1f1a10805c868c9163a3ca12323788506e4c8',
             'PROTO': 'c46718faedc19280eb5ccd7d2eb55daaa43632b9d17b6ec3fb9441e8ce3f365f'}
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    '7b2b03c24138b3ace5295c1b0f9872f934d847f8ca29b1541fc768837ba916d9')
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
RECEIPT_GLOB = 'REPAIR_AMENDMENT_V4_RECEIPT_*.json'

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
    'amendments_v3_v2': ['v3_receipt_is_the_pinned_bytes', 'v3_insertions_whole_in_the_preimages',
                         'v3_receipt_is_committed_in_its_commit', 'v2_receipt_is_the_pinned_bytes',
                         'v2_insertions_whole_in_the_preimages',
                         'v3_commit_is_an_ancestor_of_head', 'v3_wrote_the_preimages'],
    'code': ['new_labels_quoted_verbatim_in_16', 'precedence_in_the_code_is_the_order_of_16',
             'new_branches_require_no_logged_decision',
             'closed_reasons_named_in_3_15_in_the_code_order', 'row_keys_are_written_by_build',
             'dotted_names_exist', 'a_non_cap_abort_without_a_decision_is_the_abort_label',
             'an_open_or_short_chain_is_the_incomplete_label',
             'a_normal_end_holds_and_each_condition_refuses_it',
             'the_cap_and_its_binding_are_read_from_the_configuration'],
    'postconditions': ['reverting_the_insertions_reproduces_each_preimage',
                       'every_insertion_inside_its_section_beside_its_anchor', 'no_cr_byte_after',
                       'three_way_contract_after', 'config_json_byte_identical',
                       'configuration_blocks_byte_identical',
                       'vocabulary_sections_1_3_11_byte_identical', 'rule_block_after_is_the_pin',
                       'v3_insertions_intact', 'v2_insertions_intact',
                       'architecture_and_protocol_changed'],
    'negative_control': ['every_moved_variant_refused_on_placement', 'config_variant_refused',
                         'v3_split_variant_refused', 'vocabulary_variant_refused',
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
_P = 'test_each_cells_or_rule_block_precondition_refuses'
_A = 'test_each_earlier_amendment_condition_refuses'
#: (gate, check) -> the test whose real input makes that check False, or None with the reason
LIVENESS = {
    ('pins', 'config_is_the_reviewed_preimage'): _I + 'a_config_that_is_not_the_preimage_is_refused',
    ('pins', 'architecture_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'protocol_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'cells_is_the_reviewed_preimage'): 'test_the_amended_documents_are_refused',
    ('pins', 'no_cr_byte'): 'test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed',
    ('pins', 'three_way_contract_before'):
        'test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed',
    ('pins', 'rule_block_before_is_the_pin'): _P,
    ('pins', 'cells_round_trips'): _P,
    ('pins', 'cells_original_pin_untouched'): _P,
    ('pins', 'cells_current_successor_is_the_prior_successor'): _P,
    ('pins', 'cells_successor_supersedes_the_original'): _P,
    # IMPLIED by cells_prior_successors_are_the_recorded_entries (a tuple of seven); the named
    # test drops an entry, which makes both False
    ('pins', 'cells_prior_successor_count'): 'test_a_dropped_prior_successor_is_refused',
    ('pins', 'cells_prior_successors_are_the_recorded_entries'): _P,
    ('anchors', 'every_anchor_once'): 'test_an_absent_or_duplicated_anchor_is_refused',
    ('anchors', 'no_anchor_error'): 'test_an_absent_or_duplicated_anchor_is_refused',
    ('anchors', 'every_anchor_inside_its_section'):
        _I + 'an_interloper_heading_puts_an_anchor_outside_its_section',
    ('anchors', 'inserted_text_form'): _I + 'an_inserted_text_of_the_wrong_form_is_refused',
    ('amendments_v3_v2', 'v3_receipt_is_the_pinned_bytes'): _A,
    ('amendments_v3_v2', 'v3_insertions_whole_in_the_preimages'): _A,
    ('amendments_v3_v2', 'v3_receipt_is_committed_in_its_commit'): _A,
    ('amendments_v3_v2', 'v2_receipt_is_the_pinned_bytes'): _A,
    ('amendments_v3_v2', 'v2_insertions_whole_in_the_preimages'): _A,
    ('amendments_v3_v2', 'v3_commit_is_an_ancestor_of_head'): _A,
    ('amendments_v3_v2', 'v3_wrote_the_preimages'): _A,
    ('code', 'new_labels_quoted_verbatim_in_16'): _C + 'names_refuse_one_by_one',
    ('code', 'precedence_in_the_code_is_the_order_of_16'): _C + 'names_refuse_one_by_one',
    ('code', 'new_branches_require_no_logged_decision'): _C + 'names_refuse_one_by_one',
    ('code', 'closed_reasons_named_in_3_15_in_the_code_order'): _C + 'names_refuse_one_by_one',
    ('code', 'row_keys_are_written_by_build'): _C + 'names_refuse_one_by_one',
    ('code', 'dotted_names_exist'): _C + 'names_refuse_one_by_one',
    ('code', 'a_non_cap_abort_without_a_decision_is_the_abort_label'):
        _C + 'behaviours_refuse_one_by_one',
    ('code', 'an_open_or_short_chain_is_the_incomplete_label'): _C + 'behaviours_refuse_one_by_one',
    ('code', 'a_normal_end_holds_and_each_condition_refuses_it'):
        _C + 'behaviours_refuse_one_by_one',
    ('code', 'the_cap_and_its_binding_are_read_from_the_configuration'):
        _C + 'behaviours_refuse_one_by_one',
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
    ('postconditions', 'v3_insertions_intact'): _I + 'an_insertion_inside_a_v3_text_is_refused',
    ('postconditions', 'v2_insertions_intact'): _I + 'an_insertion_inside_a_v2_text_is_refused',
    ('postconditions', 'architecture_and_protocol_changed'):
        'test_postconditions_refuse_unchanged_documents',
    ('negative_control', 'every_moved_variant_refused_on_placement'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'config_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'v3_split_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'vocabulary_variant_refused'):
        'test_a_negative_control_that_cannot_refuse_stops_the_run',
    ('negative_control', 'scratch_copies_unchanged'):
        None,   # NO REAL INPUT: only a filesystem fault while the control runs
    ('negative_control', 'real_documents_unchanged'):
        None,   # NO REAL INPUT: only another writer changing the real files mid-run
    ('successor_commit', 'prior_successor_commit_carries_the_prior_successor'):
        'test_a_history_whose_56df17f_is_not_the_prior_successor_is_refused',
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
    return _load(TOOL, 'repair_amendment_v4')


def _load_verifier():
    return _load(HERE / 'verify_repair_amendment_v4.py', 'verify_repair_amendment_v4')


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


def _receipt_with(raw: bytes, fn) -> bytes:
    r = json.loads(raw)
    fn(r)
    return (json.dumps(r, indent=1, sort_keys=True) + '\n').encode('utf-8')


class _Harness:
    """setUpClass, _drive and the refusal helpers shared by the witness classes (a mixin: it
    defines no test)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
            cls.V3 = _blob(PRE_REV, V3_REL)
            cls.V2 = _blob(PRE_REV, V2_REL)
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history (56df17f) is not available here: %s' % e)

    def _drive(self, docs, patch=None, wrap_insert_all=None, commit_protocol=None, v3=None,
               v3_committed=None, v2=None, ancestry=0, wraps=None, code_patches=(),
               harness=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the four files after)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='repair_v4_witness_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, rel in REL.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(docs[k])
        (tmp / V3_REL).parent.mkdir(parents=True, exist_ok=True)
        v3_bytes = self.V3 if v3 is None else v3
        (tmp / V3_REL).write_bytes(v3_bytes)
        (tmp / V2_REL).write_bytes(self.V2 if v2 is None else v2)
        m = _load_tool()
        m.REPO = tmp
        for k, rel in REL.items():
            setattr(m, k, tmp / rel)
        m.V3_RECEIPT = tmp / V3_REL
        m.V2_RECEIPT = tmp / V2_REL
        for name, value in (patch or {}).items():
            setattr(m, name, value)
        if wrap_insert_all is not None:
            m.insert_all = wrap_insert_all(m.insert_all, m)
        for name, fn in (wraps or {}).items():
            setattr(m, name, fn(getattr(m, name), m))
        for name in ('REPO', 'V3_RECEIPT', 'V2_RECEIPT') + tuple(REL):
            here = Path(getattr(m, name)).resolve()
            self.assertTrue(here == tmp.resolve() or tmp.resolve() in here.parents,
                            '%s escaped the scratch directory: %s' % (name, here))
        succ = self.PRE['PROTO'] if commit_protocol is None else commit_protocol
        committed = v3_bytes if v3_committed is None else v3_committed

        def fake_run(argv_, *a, **kw):
            if argv_[:1] == ['git'] and 'rev-parse' in argv_:
                return types.SimpleNamespace(stdout='0' * 40 + '\n', returncode=0)
            if argv_[:1] == ['git'] and 'merge-base' in argv_:
                return types.SimpleNamespace(stdout=b'', returncode=ancestry)
            if argv_[:1] == ['git'] and 'show' in argv_:
                rev, path = argv_[-1].split(':', 1)
                if rev == PRE_REV and path == REL['PROTO']:
                    return types.SimpleNamespace(stdout=succ, returncode=0)
                if rev == PRE_REV and path == V3_REL:
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

    def _v3_for(self, d, fn=None):
        """The v3 receipt with ``written`` pointing at the documents ``d`` (and ``fn`` applied),
        and the pin patch that accepts it."""
        def edit(r):
            r['written'].update(config_sha256=sha(d['CONFIG']),
                                architecture_sha256=sha(d['ARCH']),
                                protocol_sha256=sha(d['PROTO']), cells_sha256=sha(d['CELLS']))
            if fn is not None:
                fn(r)
        raw = _receipt_with(self.V3, edit)
        return raw, {'V3_RECEIPT_SHA256': sha(raw)}

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


def _decision_object_without(branch: str):
    """The builder's ``decision_object`` recompiled from its own source with ``branch`` made
    unreachable (``elif False:``); refuses unless the text occurs exactly once."""
    import build_live_ab_results as bld
    fn = bld.decision_object
    src = inspect.getsource(fn)
    if src.count(branch) != 1:
        raise AssertionError('mutation text found %d times' % src.count(branch))
    # the same first line number, so ``inspect.getsource`` of the mutant still reads the
    # function's own lines of the file (the code checks read the source of the live name)
    pad = '\n' * (fn.__code__.co_firstlineno - 1)
    code = compile(pad + textwrap.dedent(src.replace(branch, '    elif False:\n')),
                   inspect.getsourcefile(fn), 'exec',
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    scratch: dict = {}
    exec(code, dict(fn.__globals__), scratch)                          # noqa: S102
    made = scratch[fn.__name__]
    out = types.FunctionType(made.__code__, fn.__globals__, fn.__name__, made.__defaults__,
                             made.__closure__)
    out.__kwdefaults__ = made.__kwdefaults__
    return out


class RepairAmendmentV4WitnessTests(_Harness, unittest.TestCase):

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(len(self.PRE['CONFIG']), 16136)
        self.assertEqual((sha(self.V3), sha(self.V2)), (V3_SHA256, V2_SHA256))
        self.assertEqual((m.PRIOR_CONFIG_SHA256, m.PRIOR_ARCH_SHA256, m.PRIOR_SUCCESSOR,
                          m.PRIOR_CELLS_SHA256),
                         (REVIEWED['CONFIG'], REVIEWED['ARCH'], REVIEWED['PROTO'],
                          REVIEWED['CELLS']))
        self.assertEqual(m.PRIOR_RULE_BLOCK, RULE_BLOCK)
        self.assertEqual(m.PRIOR_SUCCESSOR_COMMIT, PRE_REV)
        self.assertEqual((m.V3_RECEIPT_SHA256, m.V2_RECEIPT_SHA256), (V3_SHA256, V2_SHA256))
        # the seven recorded entries are the ones the validation pin test records
        sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(tuple((e['sha256'], sha(json.dumps(e, sort_keys=True).encode()))
                               for e in sb['prior_successors']), m.PRIOR_ENTRIES)
        # config.json of this checkout is still the pre-image (the tool never writes it)
        self.assertEqual(sha((REPO / REL['CONFIG']).read_bytes()), REVIEWED['CONFIG'])

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
            if sha(real['PROTO']) == DELIVERED['PROTO']:
                # the real run is the checkout's documents: the drive reproduces them
                for k in ('CONFIG', 'ARCH', 'PROTO'):
                    self.assertEqual(after[k], real[k], k)
                self.assertEqual(_normalized_cells(after['CELLS']),
                                 _normalized_cells(real['CELLS']))
        post = receipt['postcondition_checked']
        self.assertEqual(len(post['every_insertion_inside_its_section_beside_its_anchor']), 2)
        self.assertTrue(all(post['gate'].values()), post['gate'])
        self.assertEqual(post['vocabulary_sections_1_3_11_byte_identical'],
                         {'1': True, '3': True, '11': True})
        self.assertEqual(post['rule_block_sha256_after'], RULE_BLOCK)
        self.assertEqual((len(post['v3_insertions_intact']), len(post['v2_insertions_intact'])),
                         (10, 27))
        control = receipt['negative_control']
        self.assertEqual(control['variants_run'], 5)
        self.assertTrue(all(v['refused'] for v in control['variants'].values()))
        self.assertTrue(all(control['gate'].values()), control['gate'])
        self.assertTrue(all(receipt['code_checked_at_run_time']['gate'].values()))
        self.assertEqual(receipt['predecessor_amendment_v3']['receipt_sha256'], V3_SHA256)
        self.assertEqual(receipt['predecessor_amendment_v3']['amendment_v2_kept'][
            'receipt_sha256'], V2_SHA256)
        self.assertEqual(receipt['written']['harness_entries_changed'], [])
        # cells.json: 73dd0573 demoted whole with 56df17f
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        old_sb = json.loads(self.PRE['CELLS'])['provenance']['vocabulary_alignment'][
            'superseded_by']
        self.assertEqual(sb['sha256'], sha(after['PROTO']))
        self.assertEqual(sb['supersedes'], m.ORIGINAL_PIN)
        self.assertTrue(sb['reason'].startswith('NOT an Appendix B change:'))
        self.assertEqual(len(sb['prior_successors']), 8)
        self.assertEqual(sb['prior_successors'][:7], old_sb['prior_successors'])
        last = sb['prior_successors'][7]
        self.assertEqual({k: v for k, v in last.items() if k not in (
            'changing_commit_of_this_successor', 'changing_commit_note')},
            {k: v for k, v in old_sb.items() if k not in (
                'prior_successors', 'changing_commit_note', 'correction_to_the_owner_report')})
        self.assertEqual(last['changing_commit_of_this_successor'], PRE_REV)
        self.assertIn('git show 56df17f:', last['changing_commit_note'])
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
        v3, vpatch = self._v3_for(d)
        patch.update(vpatch)
        rc, err, receipt, after = self._drive(d, patch=patch, v3=v3)
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
            va['superseded_by']['prior_successors'][6]['reason'] += ' '
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
                kw = {}
                if check == 'rule_block_before_is_the_pin':
                    d, patch = self._repin(d)
                    kw['v3'], vpatch = self._v3_for(d)
                    patch.update(vpatch)
                else:
                    patch = {'PRIOR_CELLS_SHA256': sha(d['CELLS'])}
                rc, err, receipt, after = self._drive(d, patch=patch, **kw)
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
        ins = next(i for i in m.INSERTIONS if i.key == 'architecture.3_15')
        for what, arch in (('absent', self.PRE['ARCH'].replace(ins.anchor, b'', 1)),
                           ('duplicated', self.PRE['ARCH'].replace(
                               ins.anchor, ins.anchor + ins.anchor, 1))):
            with self.subTest(what=what):
                d, patch = self._repin(dict(self.PRE, ARCH=arch))
                v3, vpatch = self._v3_for(d)
                patch.update(vpatch)
                rc, err, receipt, after = self._drive(d, patch=patch, v3=v3)
                self._assert_refused_unchanged(d, rc, err, receipt, after, what)
                g = _printed(err)['gate_anchors']
                self.assertIs(g['every_anchor_once'], False)
                self.assertIs(g['no_anchor_error'], False)

    def test_isolated_an_interloper_heading_puts_an_anchor_outside_its_section(self):
        m = _load_tool()
        ins = next(i for i in m.INSERTIONS if i.key == 'architecture.3_15')
        a = self.PRE['ARCH']
        i = a.index(ins.anchor)
        j = a.rindex(b'\nThe builder never recomputes a decision', 0, i) + 1
        d, patch = self._repin(dict(self.PRE, ARCH=a[:j] + b'### 3.15b Interloper\n\n' + a[j:]))
        v3, vpatch = self._v3_for(d)
        patch.update(vpatch)
        rc, err, receipt, after = self._drive(d, patch=patch, v3=v3)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'interloper')
        self._refused_alone(_printed(err)['gate_anchors'], 'every_anchor_inside_its_section',
                            'interloper')

    def test_isolated_an_inserted_text_of_the_wrong_form_is_refused(self):
        m = _load_tool()
        bad = tuple(m.Insertion(i.key, i.doc, i.anchor, i.side,
                                i.text + b'a trailing space \n' if i.key == 'architecture.3_15'
                                else i.text, i.section, i.section_end) for i in m.INSERTIONS)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': bad})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'form')
        self._refused_alone(_printed(err)['gate_anchors'], 'inserted_text_form', 'form')

    def test_a_non_ascii_inserted_text_is_refused(self):
        """The form rule is ASCII only (the v3 rule allowed the ARCHITECTURE table's dash; v4's
        two texts have none): an em dash in one text is refused on its own.  Added after the
        first mutation sweep found the ASCII clause unobserved."""
        m = _load_tool()
        bad = tuple(m.Insertion(i.key, i.doc, i.anchor, i.side,
                                i.text.replace(b' - no terminal record', b' \xe2\x80\x94 no terminal '
                                               b'record', 1) if i.key == 'protocol.16'
                                else i.text, i.section, i.section_end) for i in m.INSERTIONS)
        self.assertNotEqual(bad[0].text, m.INSERTIONS[0].text)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': bad})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'non-ascii')
        g = _printed(err)
        self._refused_alone(g['gate_anchors'], 'inserted_text_form', 'non-ascii')
        self.assertEqual(g['inserted_text_form']['per_insertion']['protocol.16']['non_ascii'],
                         ['\u2014'])

    # -- amendments v3 and v2 ----------------------------------------------------------
    def test_each_earlier_amendment_condition_refuses(self):
        other = _receipt_with(self.V3, lambda r: r.__setitem__('generated_utc',
                                                               '2026-09-24T22:18:09Z'))
        split, split_patch = self._v3_for(self.PRE, lambda r: r['insertions'][6].__setitem__(
            'text', r['insertions'][6]['text'] + 'X'))
        wrote, wrote_patch = self._v3_for(self.PRE, lambda r: r['written'].__setitem__(
            'protocol_sha256', '0' * 64))
        v2_other = _receipt_with(self.V2, lambda r: r.__setitem__('generated_utc', 'x'))
        v2_split = _receipt_with(self.V2, lambda r: r['insertions'][10].__setitem__(
            'text', r['insertions'][10]['text'] + 'X'))
        cases = {
            'v3_receipt_is_the_pinned_bytes': {'v3': other, 'v3_committed': other},
            'v3_insertions_whole_in_the_preimages': {'v3': split, 'patch': split_patch},
            'v3_receipt_is_committed_in_its_commit': {'v3_committed': b'{}'},
            'v2_receipt_is_the_pinned_bytes': {'v2': v2_other},
            'v2_insertions_whole_in_the_preimages': {
                'v2': v2_split, 'patch': {'V2_RECEIPT_SHA256': sha(v2_split)}},
            'v3_commit_is_an_ancestor_of_head': {'ancestry': 1},
            'v3_wrote_the_preimages': {'v3': wrote, 'patch': wrote_patch},
        }
        for check, kw in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, **kw)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate'], check, check)

    # -- the code the prose describes ------------------------------------------------
    def test_code_names_refuse_one_by_one(self):
        import build_live_ab_results as bld
        real_do, real_build = bld.decision_object, bld.build

        def order_swapped(*a, **kw):
            # primary, reportable = PROVISIONAL_LABEL
            # primary, reportable, label = DECISION_INVALID_LABEL
            # primary, reportable = RESTART_CAP_INCOMPLETE_LABEL
            # primary, reportable = ABORT_INCOMPLETE_LABEL
            # primary, reportable = PREDECISION_ABORT_LABEL
            # primary, reportable = INCOMPLETE_CHAIN_LABEL
            # elif logged is None and end['terminal'] == 'trial_aborted':
            # elif logged is None and not end['normal_end_at_full_horizon']:
            return real_do(*a, **kw)

        def logged_not_required(*a, **kw):
            # primary, reportable, label = DECISION_INVALID_LABEL
            # primary, reportable = RESTART_CAP_INCOMPLETE_LABEL
            # primary, reportable = ABORT_INCOMPLETE_LABEL
            # elif end['terminal'] == 'trial_aborted':
            # primary, reportable = PREDECISION_ABORT_LABEL
            # elif logged is None and not end['normal_end_at_full_horizon']:
            # primary, reportable = INCOMPLETE_CHAIN_LABEL
            # primary, reportable = PROVISIONAL_LABEL
            return real_do(*a, **kw)

        def build_without_reasons(*a, **kw):
            # 'restart_cap_value' 'restart_cap_config_matches_chain' 'abort_reason'
            # 'crossing_not_acted_on'  summary['restart_cap'] = restart_cap_binding(
            return real_build(*a, **kw)
        reasons = tuple(r for r in bld.NOT_NORMAL_END_REASONS if r != 'no_look')
        cases = {
            'new_labels_quoted_verbatim_in_16': (
                [(bld, 'INCOMPLETE_CHAIN_LABEL', 'incomplete: no decision (no decision)')], {}),
            'precedence_in_the_code_is_the_order_of_16': (
                [(bld, 'decision_object', order_swapped)], {}),
            'new_branches_require_no_logged_decision': (
                [(bld, 'decision_object', logged_not_required)], {}),
            'closed_reasons_named_in_3_15_in_the_code_order': (
                [(bld, 'NOT_NORMAL_END_REASONS', reasons)], {}),
            'row_keys_are_written_by_build': ([(bld, 'build', build_without_reasons)], {}),
            'dotted_names_exist': ([], {'patch': {'DOTTED': (
                'build_live_ab_results.normal_end_reading',
                'build_live_ab_results.restart_cap_binding',
                'lab_common.server_supervision_cap', 'build_live_ab_results.no_such_name')}}),
        }
        for check, (patches, kw) in cases.items():
            with self.subTest(check=check):
                self._code_refusal(patches, check, **kw)

    def test_code_behaviours_refuse_one_by_one(self):
        import build_live_ab_results as bld
        real_end, real_bind = bld.normal_end_reading, bld.restart_cap_binding

        def pass_ignored(events, cfg, point):
            out = real_end(events, cfg, point)
            if out['reasons'] == ['resolution_not_pass']:
                out = dict(out, reasons=[], normal_end_at_full_horizon=True)
            return out

        def constant_cap(*a, **kw):
            return dict(real_bind(*a, **kw), value=3, error=None)
        cases = {
            'a_non_cap_abort_without_a_decision_is_the_abort_label': [
                (bld, 'decision_object', _decision_object_without(
                    "    elif logged is None and end['terminal'] == 'trial_aborted':\n"))],
            'an_open_or_short_chain_is_the_incomplete_label': [
                (bld, 'decision_object', _decision_object_without(
                    "    elif logged is None and not end['normal_end_at_full_horizon']:\n"))],
            'a_normal_end_holds_and_each_condition_refuses_it': [
                (bld, 'normal_end_reading', pass_ignored)],
            'the_cap_and_its_binding_are_read_from_the_configuration': [
                (bld, 'restart_cap_binding', constant_cap)],
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
        for key in ('protocol.16', 'architecture.3_15'):
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

    def test_isolated_an_insertion_inside_a_v3_text_is_refused(self):
        m = _load_tool()
        extra = self._extra(m, 'probe.inside_v3', 'protocol',
                            b'    reference rule\'s unfiltered first crossing with its verdict ',
                            'after-line', b'    a probe inside item 17.\n',
                            b'## 16. What is reported whatever the outcome', b'## Appendix A.')
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'INSERTIONS': m.INSERTIONS + (extra,)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'inside v3')
        self._refused_alone(_printed(err)['gate'], 'v3_insertions_intact', 'inside v3')

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
        post, ok = m.postconditions(old, dict(old), json.loads(self.V3), json.loads(self.V2))
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
                 'v3_split_variant_refused': {'extra_variants': no_extras('v3_text_split')},
                 'vocabulary_variant_refused': {
                     'extra_variants': no_extras('vocabulary_section_1_touched')}}
        for check, wraps in cases.items():
            with self.subTest(check=check):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wraps=wraps)
                self._assert_refused_unchanged(d, rc, err, receipt, after, check)
                self._refused_alone(_printed(err)['gate'], check, check)

    def test_a_history_whose_56df17f_is_not_the_prior_successor_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, commit_protocol=b'not the v3 protocol')
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
                self.assertTrue(hasattr(RepairAmendmentV4WitnessTests, test), test)


class ProseTests(unittest.TestCase):
    """The prose says what the code performs: every closed name and every dotted code name it
    uses is read back from the code."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load_tool()
        import build_live_ab_results
        import lab_common
        cls.bld, cls.lc = build_live_ab_results, lab_common

    def all_text(self):
        return ''.join(i.text.decode() for i in self.m.INSERTIONS)

    def test_every_dotted_code_name_of_the_prose_exists(self):
        mods = {'build_live_ab_results': self.bld, 'lab_common': self.lc}
        found = set(re.findall(r'`((?:lab_\w+|build_live_ab_results)\.[\w.]+?)`', self.all_text()))
        self.assertEqual(found, set(self.m.DOTTED))
        for dotted in sorted(found):
            with self.subTest(name=dotted):
                mod, *path = dotted.split('.')
                obj = mods[mod]
                for p in path:
                    obj = getattr(obj, p)
                self.assertTrue(callable(obj))

    def test_every_backticked_reason_of_3_15_is_a_closed_reason_of_the_code(self):
        text = self.m.A4_3_15
        start = text.index('(`trial_not_started`')
        listed = re.findall(r'`([a-z_]+)`', text[start:text.index(');', start)])
        self.assertEqual(listed, list(self.bld.NOT_NORMAL_END_REASONS))

    def test_item_18_follows_item_17_and_names_every_label_of_the_order(self):
        flat = ' '.join(self.m.P4_16.split())
        self.assertTrue(self.m.P4_16.startswith('18. *(Amendment 2026-09-25, v4'))
        for name in self.m.NEW_LABELS:
            self.assertIn('`%s`' % getattr(self.bld, name), flat)
        self.assertIn('`LIVE_DECISION_INVALID (harness defect)`', flat)
        self.assertIn('first match wins', flat)

    def test_the_row_keys_are_the_summary_rows_of_a_build(self):
        src = inspect.getsource(self.bld.build)
        for key in self.m.ROW_KEYS:
            self.assertIn("'%s'" % key, src)

    def test_control_a_prose_naming_a_reason_the_code_lacks_fails(self):
        mutated = self.m.A4_3_15.replace('`no_look`, ', '`no_look`, `no_pairs`, ')
        start = mutated.index('(`trial_not_started`')
        listed = re.findall(r'`([a-z_]+)`', mutated[start:mutated.index(');', start)])
        self.assertNotEqual(listed, list(self.bld.NOT_NORMAL_END_REASONS))


class VerifierTests(_Harness, unittest.TestCase):
    """The independent verifier on the control drive's output: it must verify the amendment
    and must NOT verify its negative controls."""

    KEYS = {'CONFIG': 'config', 'ARCH': 'architecture', 'PROTO': 'protocol', 'CELLS': 'cells'}
    CHECKS = ['parent_is_the_reviewed_preimage', 'receipt_lists_exactly_the_expected_insertions',
              'receipt_sections_agree_with_the_verifier_headings', 'each_insertion_occurs_once',
              'reverting_the_insertions_reproduces_the_parent', 'config_json_is_the_parent',
              'each_insertion_under_the_verifier_heading', 'no_cr_byte',
              'three_blocks_byte_identical_and_unchanged', 'rule_block_is_cbfd1792',
              'vocabulary_sections_identical', 'amendment_v3_kept_whole',
              'amendment_v2_kept_whole', 'cells', 'content_in_the_documents',
              'code_names_are_the_committed_code', 'receipt_names_the_amended_protocol',
              'receipt_written_digests_match']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CODE = {'build_live_ab_results':
                    (REPO / 'experiments/live_ab/build_live_ab_results.py').read_bytes()}

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
                'demoted_commit_protocol': self.PRE['PROTO'], 'v3_receipt': self.V3,
                'v2_receipt': self.V2, 'code': self.CODE}
        base.update(kw)
        return base

    def test_the_verifier_re_derives_the_amendment(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(**self._args(before, after, receipt))
        self.assertIs(got['all_verified'], True, json.dumps(got['checks']))
        self.assertEqual(list(got['checks']), self.CHECKS)
        ctl = v.negative_controls(before, after, receipt, self.PRE['PROTO'], self.V3, self.V2,
                                  self.CODE)
        self.assertIs(ctl['every_control_failed'], True, ctl)
        self.assertEqual(len(ctl), 7)

    def test_each_negative_control_runs_the_predicate(self):
        """Each control is the predicate run on its variant, never a constant: with verify()
        made to accept everything, every control reads True and the set is not failed.  Added
        after the first mutation sweep: a control replaced by ``False`` survived it."""
        v = _load_verifier()
        before, after, receipt = self._amended()
        with mock.patch.object(v, 'verify', lambda *a, **kw: {'all_verified': True}):
            ctl = v.negative_controls(before, after, receipt, self.PRE['PROTO'], self.V3,
                                      self.V2, self.CODE)
        self.assertEqual({k: val for k, val in ctl.items() if k != 'every_control_failed'},
                         {k: True for k in ctl if k != 'every_control_failed'})
        self.assertIs(ctl['every_control_failed'], False)
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
        a315 = after['architecture'].replace(text['architecture.3_15'], b'', 1)
        h = b'### 3.16 Import isolation matrix (enforced by `tests_lab_isolation.py`)\n\n'
        j = a315.index(h) + len(h)
        k = after['protocol'].index(b'## 1. Purpose, scope')
        k = after['protocol'].index(b'\n\n', k) + 2
        rb = b'"consecutive_infrastructure_failures": 10'
        code = {'build_live_ab_results': self.CODE['build_live_ab_results'].replace(
            b"'no_look',", b"'no_look', 'no_pairs',", 1)}
        dropped = {'build_live_ab_results': self.CODE['build_live_ab_results'].replace(
            b" 'no_look',", b"", 1)}
        got = v.verify(**self._args(before, after, receipt, code=dropped))
        self.assertIs(got['checks']['code_names_are_the_committed_code'], False,
                      'a reason dropped from the code must show too')
        variants = {
            'parent_is_the_reviewed_preimage': self._args(
                dict(before, cells=before['cells'] + b' '), after, receipt),
            'receipt_lists_exactly_the_expected_insertions': with_receipt(
                lambda r: r['insertions'].pop()),
            'receipt_sections_agree_with_the_verifier_headings': with_receipt(
                lambda r: r['insertions'][-1].__setitem__('section', '### 3.16 Import')),
            'each_insertion_occurs_once': with_after(dict(
                after, architecture=after['architecture'] + text['architecture.3_15'])),
            'reverting_the_insertions_reproduces_the_parent': with_after(
                dict(after, protocol=after['protocol'] + b'\nextra\n')),
            'config_json_is_the_parent': with_after(dict(after, config=after['config'] + b' ')),
            'each_insertion_under_the_verifier_heading': with_after(
                dict(after, architecture=a315[:j] + text['architecture.3_15'] + a315[j:])),
            'no_cr_byte': with_after(dict(after, protocol=after['protocol'] + b'\r\n')),
            'three_blocks_byte_identical_and_unchanged': with_after(dict(
                after, architecture=after['architecture'].replace(
                    b'"battery_percent": 20', b'"battery_percent": 21', 1))),
            'rule_block_is_cbfd1792': with_after({d: (b.replace(rb, rb[:-2] + b'11', 1)
                                                      if d != 'cells' else b)
                                                  for d, b in after.items()}),
            'vocabulary_sections_identical': with_after(dict(
                after, protocol=after['protocol'][:k] + b'X' + after['protocol'][k:])),
            'amendment_v3_kept_whole': self._args(before, after, receipt,
                                                  v3_receipt=self.V3 + b' '),
            'amendment_v2_kept_whole': self._args(before, after, receipt,
                                                  v2_receipt=self.V2 + b' '),
            'cells': self._args(before, after, receipt,
                                demoted_commit_protocol=b'not the 56df17f protocol'),
            'content_in_the_documents': with_after(dict(after, protocol=after['protocol'].replace(
                b'the cap of three and its behaviour are unchanged',
                b'the cap of three and its behaviour are changed', 1))),
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
            'eight_prior_successors': lambda va: sb(va)['prior_successors'].append({}),
            'first_seven_are_the_recorded_entries':
                lambda va: sb(va)['prior_successors'][1].__setitem__('reason', 'edited'),
            # the same input: the seven entries of the pre-image ARE the recorded ones
            'first_seven_unchanged':
                lambda va: sb(va)['prior_successors'][1].__setitem__('reason', 'edited'),
            'eighth_is_the_parent_successor_whole':
                lambda va: sb(va)['prior_successors'][7].__setitem__('reason', 'edited'),
            'eighth_names_its_commit': lambda va: sb(va)['prior_successors'][7].__setitem__(
                'changing_commit_of_this_successor', '474f9d82aae2b3979910d8a99d8305b5d7bc44c1'),
            'eighth_says_how_resolved': lambda va: sb(va)['prior_successors'][7].__setitem__(
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
        REPAIR_AMENDMENT_V4_RECEIPT.  Skipped before it exists."""
        log = subprocess.run(['git', '-C', str(REPO), 'log', '--diff-filter=A', '--format=%H',
                              '--name-only', '--', 'results/live_ab/'],
                             capture_output=True, text=True)
        commit, cur = None, None
        for line in log.stdout.splitlines() if log.returncode == 0 else ():
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                cur = line
            elif line.startswith('results/live_ab/REPAIR_AMENDMENT_V4_RECEIPT_'):
                commit = cur
                break
        if commit is None:
            self.skipTest('no commit in this history adds a v4 receipt')
        v = _load_verifier()
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = v.main([commit])
        self.assertEqual(rc, 0, err.getvalue())


if __name__ == '__main__':
    unittest.main()
