"""Witnesses for the patch-state amendment tool (protocol_FINAL.md section 2.2 item 1).

HOW EVERY CASE RUNS
  The PRE-amendment blobs (`git show 0194a59:<path>`, read-only, once per class;
  at that revision protocol_FINAL.md is the engineering-cap successor 7f666477)
  are copied into a fresh temporary directory. A fresh instance of the tool is
  loaded, and its module paths (REPO, CONFIG, ARCH, PROTO, CELLS, PATCH) are
  re-pointed at the copies. The harness asserts that each re-pointed path lies
  under the temporary directory. The tool's `subprocess` (git rev-parse and git
  show) is replaced in that instance only, and `lab_common.harness_file_hashes`
  is stubbed for the duration of the call. Then main() runs. The real documents
  are never opened for writing, and every drive compares their digests before
  and after.

Refusals, each with nothing written:
  * a CR byte in the protocol, with every pin re-pointed at it, so that only the
    no-CR rule stands between it and success; a CRLF in config.json;
  * the paragraph MOVED OUTSIDE section 2.2 by a fault-injected inserter, into
    2.3 and into 2.1;
  * a pre-image whose '### 2.3' heading sits above item 1, pins re-pointed and the
    anchor precondition disabled, so that only the section bound of the
    postcondition refuses it (the analogue of the engineering tool's W2);
  * the anchor absent, and the anchor duplicated;
  * an inserter that also edits one byte of vocabulary section 1;
  * a lifecycle patch whose digest is not the one the paragraph states;
  * a negative control that cannot refuse (the run must stop);
  * the amended documents (the one-shot guard), as pinned and with every pin
    re-pointed at them.
Control that must pass: the pristine pre-images reproduce the delivered bytes
(the protocol exactly; cells.json exactly except the new successor's
recorded_utc, which is the time of the run).

SCOPE: this needs the repository's git history (0194a59). Without it the class
is skipped, and the skip names the reason. Nothing here runs a model, server,
build or network request.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'patch_state_amendment.py'
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json',
       'PATCH': 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'}
#: the revision holding the reviewed pre-images (main before this amendment)
PRE_REV = '0194a594dd0079696ba9e107e24caf9bf7875360'
REVIEWED = {'CONFIG': 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824',
            'ARCH': '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab',
            'PROTO': '7f6664770b0d88ac5904967d9b8e2225d20932942824cd689278a03a2ee45e53',
            'PATCH': '88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184'}
#: the delivered protocol, and the delivered cells.json with the new successor's
#: recorded_utc replaced by RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED_PROTOCOL_SHA256 = (
    '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b')
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    '90ca1cb07f9a395ede29dcaf5aa3e2476a3413cc6a3fd75b81179a6e4d298caa')
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
SECTION_MARKER = b'### 2.2 Serving software and the manifest fields that are pinned'
NEXT_HEADING = b'### 2.3 Models'
ANCHOR = b'   are recorded;\n'

_loaded = [0]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _blob(rev: str, rel: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, rel)],
                          capture_output=True, check=True).stdout


def _load_tool():
    _loaded[0] += 1
    spec = importlib.util.spec_from_file_location(
        'patch_state_amendment_under_test_%d' % _loaded[0], TOOL)
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


class PatchStateAmendmentWitnessTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history holding %s is not available here: %s'
                                    % (PRE_REV[:7], e))

    # -- harness -------------------------------------------------------------
    def _drive(self, docs, patch=None, wrap_insert_once=None, commit_protocol=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the five files after)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='psa_witness_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, rel in REL.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(docs[k])
        (tmp / 'results' / 'live_ab').mkdir(parents=True)
        m = _load_tool()
        m.REPO = tmp
        for k, rel in REL.items():
            setattr(m, k, tmp / rel)
        for name, value in (patch or {}).items():
            setattr(m, name, value)
        if wrap_insert_once is not None:
            m.insert_once = wrap_insert_once(m.insert_once)
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
            rc = m.main()
        receipts = sorted((tmp / 'results' / 'live_ab').glob(
            'PATCH_STATE_AMENDMENT_RECEIPT_*.json'))
        receipt = json.loads(receipts[0].read_bytes()) if receipts else None
        after = {k: (tmp / rel).read_bytes() for k, rel in REL.items()}
        self.assertEqual(_real_digests(), before_real,
                         'a real document or results/live_ab changed during the drive')
        return rc, err.getvalue(), receipt, after

    def _assert_refused_unchanged(self, docs, rc, err, receipt, after, why):
        self.assertEqual(rc, 2, '%s: expected a refusal, got exit %r (%s)' % (why, rc, err))
        self.assertIsNone(receipt, '%s: a receipt was written' % why)
        for k in REL:
            self.assertEqual(after[k], docs[k], '%s: %s was changed' % (why, k))

    def _repoint_protocol(self, docs, proto):
        """``docs`` with ``proto`` as the protocol, and cells.json's current successor
        and the tool's protocol pin re-pointed at it, so that the pin does not refuse
        it. Returns (docs, patch, commit_protocol) for _drive."""
        d = dict(docs)
        d['PROTO'] = proto
        cells = json.loads(d['CELLS'])
        cells['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(proto)
        d['CELLS'] = (json.dumps(cells, indent=1) + '\n').encode('utf-8')
        return d, {'PRIOR_SUCCESSOR': sha(proto)}, proto

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(m.PRIOR_CONFIG_SHA256, REVIEWED['CONFIG'])
        self.assertEqual(m.PRIOR_ARCH_SHA256, REVIEWED['ARCH'])
        self.assertEqual(m.PRIOR_SUCCESSOR, REVIEWED['PROTO'])
        self.assertEqual(m.PATCH_SHA256, REVIEWED['PATCH'])
        self.assertTrue(all(v.count(b'\r') == 0 for v in self.PRE.values()))
        self.assertEqual(self.PRE['PROTO'].count(ANCHOR), 1)

    # -- control: the pristine pre-images pass and reproduce the delivery ----
    def test_control_the_pristine_pre_images_reproduce_the_delivered_bytes(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        self.assertEqual(sha(after['PROTO']), DELIVERED_PROTOCOL_SHA256)
        m = _load_tool()
        self.assertEqual(after['PROTO'].replace(m.INSERTED_BYTES, b'', 1), self.PRE['PROTO'])
        for k in ('CONFIG', 'ARCH', 'PATCH'):
            self.assertEqual(after[k], self.PRE[k], '%s changed' % k)
        self.assertEqual(_normalized_cells(after['CELLS']), DELIVERED_CELLS_NORMALIZED_SHA256)
        post = receipt['postcondition_checked']
        self.assertIs(post['protocol_change_is_inside_section_2_2_item_1_only'], True)
        self.assertIs(post['deleting_the_inserted_text_reproduces_the_preimage'], True)
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertEqual(post['vocabulary_sections_1_3_11_byte_identical'],
                         {'1': True, '3': True, '11': True})
        self.assertEqual(post['rule_block_sha256'], m.PRIOR_RULE_BLOCK)
        control = receipt['negative_control']
        self.assertIs(control['every_variant_refused_on_placement'], True)
        self.assertEqual(sorted(control['variants']),
                         ['moved_into_section_2.1', 'moved_into_section_2.3'])
        self.assertIs(control['real_documents_unchanged'], True)
        w = receipt['written']
        self.assertIs(w['read_back_equals_computed'], True)
        self.assertIs(w['config_byte_unchanged'], True)
        self.assertIs(w['architecture_byte_unchanged'], True)
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(sb['sha256'], DELIVERED_PROTOCOL_SHA256)
        self.assertTrue(sb['reason'].startswith('Section 2.2 item 1 ONLY:'))
        self.assertEqual(len(sb['prior_successors']), 5)
        self.assertEqual(sb['prior_successors'][4]['sha256'], REVIEWED['PROTO'])

    # -- CR --------------------------------------------------------------------
    def test_a_CR_in_the_protocol_is_refused_even_with_every_pin_repointed(self):
        p = self.PRE['PROTO']
        i = p.index(b'\n')
        d, patch, shown = self._repoint_protocol(self.PRE, p[:i] + b'\r' + p[i:])
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CR in protocol')
        self.assertIn('"protocol": 1', err)

    def test_a_CRLF_config_is_refused(self):
        d = dict(self.PRE)
        d['CONFIG'] = d['CONFIG'].replace(b'\n', b'\r\n')
        rc, err, receipt, after = self._drive(
            d, patch={'PRIOR_CONFIG_SHA256': sha(d['CONFIG'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CRLF config')
        self.assertIn('precondition', err)

    # -- moved outside section 2.2 ---------------------------------------------
    def _moving_inserter(self, where):
        def wrap(real):
            m = _load_tool()

            def moved(raw):
                return m.move_outside_2_2(real(raw), where)
            return moved
        return wrap

    def test_the_paragraph_moved_into_2_3_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_once=self._moving_inserter('2.3'))
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved into 2.3')
        self.assertIn('postcondition', err)
        self.assertIn('"insertion_inside_section_2_2": false', err)

    def test_the_paragraph_moved_into_2_1_is_refused(self):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_once=self._moving_inserter('2.1'))
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved into 2.1')
        self.assertIn('"insertion_inside_section_2_2": false', err)

    def test_only_the_section_bound_refuses_an_anchor_that_lies_in_2_3(self):
        """The '### 2.3 Models' heading is moved above item 1, so the anchor, and
        the paragraph after it, lie in section 2.3 while staying directly after the
        anchor and before item 2. Pins re-pointed, anchor precondition disabled:
        only the upper bound of the postcondition's placement check stands."""
        p = self.PRE['PROTO']
        heading = NEXT_HEADING + b'\n\n'
        self.assertEqual(p.count(heading), 1)
        without = p.replace(heading, b'', 1)
        k = without.index(b'1. the checkout is built into')
        altered = without[:k] + heading + without[k:]
        d, patch, shown = self._repoint_protocol(self.PRE, altered)
        m = _load_tool()
        facts = m.anchor_facts(altered)
        self.assertIs(facts['anchor_inside_section_2_2'], False)     # the pre-check sees it
        patch['anchor_facts'] = lambda raw: dict(facts, anchor_is_item_1_last_line=True,
                                                 anchor_inside_section_2_2=True)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor in 2.3')
        self.assertIn('postcondition', err)
        where = m.placement(m.insert_once(altered))
        self.assertIs(where['directly_after_the_anchor'], True)
        self.assertIs(where['directly_before_item_2'], True)
        self.assertIs(where['insertion_inside_section_2_2'], False)

    # -- the anchor ------------------------------------------------------------
    def test_an_absent_anchor_is_refused(self):
        altered = self.PRE['PROTO'].replace(ANCHOR, b'   are recorded (edited);\n', 1)
        d, patch, shown = self._repoint_protocol(self.PRE, altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor absent')
        self.assertIn('"anchor_occurrences": 0', err)
        with self.assertRaises(ValueError):
            _load_tool().insert_once(altered)

    def test_a_duplicated_anchor_is_refused(self):
        p = self.PRE['PROTO']
        k = p.index(NEXT_HEADING)
        altered = p[:k] + ANCHOR + b'\n' + p[k:]
        d, patch, shown = self._repoint_protocol(self.PRE, altered)
        rc, err, receipt, after = self._drive(d, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'anchor twice')
        self.assertIn('"anchor_occurrences": 2', err)

    # -- the inserter edits more than it should ---------------------------------
    def test_an_inserter_that_also_edits_vocabulary_section_1_is_refused(self):
        def wrap(real):
            def faulty(raw):
                out = real(raw)
                i = out.index(b'## 1. Purpose, scope')
                j = out.index(b'\n', i) + 1
                return out[:j] + b'\n' + out[j:]
            return faulty
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_once=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'section 1 edited')
        self.assertIn('"deleting_the_inserted_text_reproduces_the_preimage": false', err)
        self.assertIn('"1": false', err)

    # -- the facts the paragraph states ------------------------------------------
    def test_a_patch_that_is_not_the_stated_one_is_refused(self):
        d = dict(self.PRE)
        d['PATCH'] = d['PATCH'].replace(b'\n', b'\n ', 1)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'other patch')
        self.assertIn('"patch_digest_matches_the_stated_digest": false', err)

    # -- the negative control is live ------------------------------------------
    def test_a_negative_control_that_cannot_refuse_stops_the_run(self):
        """If moving the paragraph no longer moves it, the control 'variant' is the
        correct protocol and is accepted; the run must stop, nothing written."""
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(
            d, patch={'move_outside_2_2': lambda new_proto, where: new_proto})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'dead control')
        self.assertIn('the negative control did not refuse', err)

    # -- the one-shot guard ------------------------------------------------------
    def test_the_amended_documents_are_refused(self):
        rc, err, receipt, amended = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        d = dict(amended)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, as pinned')
        self.assertIn('precondition', err)
        repointed = {'PRIOR_SUCCESSOR': sha(d['PROTO']), 'PRIOR_PRIOR_SUCCESSORS': 5}
        rc, err, receipt, after = self._drive(d, patch=repointed)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, pins re-pointed')
        self.assertIn('the amendment is already present', err)

    # -- units -------------------------------------------------------------------
    def test_placement_has_both_bounds(self):
        m = _load_tool()
        new = m.insert_once(self.PRE['PROTO'])
        where = m.placement(new)
        s0, s1 = where['section_2_2']
        self.assertTrue(new[s0:].startswith(SECTION_MARKER))
        self.assertTrue(new[s1:].startswith(NEXT_HEADING))
        self.assertTrue(s0 < where['insert_at'] < where['insert_end'] <= s1)
        self.assertIs(m.placement(self.PRE['PROTO'])['insertion_inside_section_2_2'], False)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
