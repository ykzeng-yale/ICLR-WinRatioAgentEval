"""Witnesses for the repair amendment tool (root 20:40 items 2 and 4).

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

Refusals, each with nothing written:
  * a CR in the protocol, with every pin re-pointed at it; a CRLF config.json;
  * an insertion MOVED OUT of its section by a fault-injected inserter: the 5.3
    paragraph into 5.4, the 14.6 paragraph into 14.7, the 7.1 rows into 7.2, the
    Appendix B `server_supervision` line out of its fence (the other two copies
    left in place);
  * a pre-image whose '### 14.7' heading sits above the 14.6 anchor, pins
    re-pointed and the anchor precondition disabled, so that only the upper
    section bound of the postcondition refuses it;
  * an anchor absent, and an anchor duplicated;
  * an inserter that also edits one byte of vocabulary section 1;
  * an inserter that also puts a key under `execution.auto_abort` in all three
    copies (the contract still holds; the rule-block digest moves);
  * `engineering_acquisition` no longer equal to run_smoke.BOUND_LIMITS;
  * a source prompt equal (normalized) to a conformance prompt; a source prompt
    with token-set Jaccard >= 0.5 but not equal; a source defining the same
    entry point; a pinned source file whose digest is not the pin;
  * a git history whose 48f4d70 does not carry the prior successor;
  * a negative control that cannot refuse (the run must stop);
  * the amended documents (the one-shot guard), as pinned and with every pin
    re-pointed at them.
Control that must pass: the pristine pre-images reproduce the delivered bytes
(config.json, ARCHITECTURE and the protocol exactly; cells.json exactly except the
new successor's recorded_utc, which is the time of the run).

VerifierTests: the independent verifier (verify_repair_amendment.py) re-derives
the control drive's amendment, and does NOT verify its own three negative
controls, a receipt that omits an insertion, a wrong 48f4d70 blob or a wrong
section heading; once the amendment commit exists, its main() is run on it.
RealSourcesTests (optional): the prompt check on the real pinned sources
reproduces the receipt's similarity maxima.

SCOPE: this needs the repository's git history (b049307). Without it the class is
skipped, and the skip names the reason. Nothing here runs a model, server, build
or network request.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
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
REVIEWED = {'CONFIG': 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824',
            'ARCH': '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab',
            'PROTO': '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b',
            'CELLS': '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'}
#: the delivered documents, and the delivered cells.json with the new successor's
#: recorded_utc replaced by RECORDED_PLACEHOLDER, serialized as the tool does
DELIVERED = {'CONFIG': 'c323e0f26e7cba68355083a104e6397097f446f5e4532eb23edea57952ebd850',
             'ARCH': '4e8546f236cf0211b9d8bb9375e42cc410f8d084fbd7c72dcee3e9ec9955d156',
             'PROTO': '25014221bbba4a4d67e8bde845d401318d7db6fc04375ec3f7d875532b754a0c'}
DELIVERED_CELLS_NORMALIZED_SHA256 = (
    'f73286fa6b2ea1fbe28476853897bcddbd072049c70c09112a986b0eeef8e97e')
RECORDED_PLACEHOLDER = 'RECORDED_UTC'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
SMOKE = ('mbpp_full/39', 'mbpp_full/122', 'mbpp_full/522', 'mbpp_full/547',
         'mbpp_full/869', 'mbpp_full/966')

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


def synthetic_sources(extra_sanitized=()):
    """A small stand-in for the three pinned sources: unrelated prompts, the six
    smoke-task uids present, plus ``extra_sanitized`` records."""
    san = [{'task_id': 1, 'prompt': 'Write a function to add two numbers.',
            'code': 'def add(a, b):\n    return a + b\n'}] + list(extra_sanitized)
    full = [{'task_id': int(u.split('/')[1]), 'text': 'Write a function to find item %s.' % u,
             'code': 'def item_%s(x):\n    return x\n' % u.split('/')[1]} for u in SMOKE]
    he = [{'task_id': 'HumanEval/0', 'prompt': 'def ident(x):\n    """Return x."""\n',
           'entry_point': 'ident'}]
    return {'records': {'mbpp_sanitized': san, 'mbpp_full': full, 'humaneval': he},
            'facts': {'synthetic': True}}


class _DriveHarness:
    """setUpClass, _drive, _assert_refused_unchanged and _repoint, shared by the
    witness class and the verifier class (a mixin: it defines no test)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(PRE_REV, rel) for k, rel in REL.items()}
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history holding %s is not available here: %s'
                                    % (PRE_REV[:7], e))

    # -- harness -------------------------------------------------------------
    def _drive(self, docs, patch=None, wrap_insert_all=None, commit_protocol=None,
               sources=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the four files after)."""
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
        receipts = sorted((tmp / 'results' / 'live_ab').glob('REPAIR_AMENDMENT_RECEIPT_*.json'))
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
        self.assertEqual(len(post['every_insertion_inside_its_section_beside_its_anchor']), 18)
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
        self.assertEqual(control['variants_run'], 16)
        cfg = json.loads(after['CONFIG'])
        self.assertEqual(cfg['server_supervision'],
                         {'max_supervised_restarts_per_server_per_trial': 3,
                          'on_exceeding': 'abort_trial_incomplete'})
        self.assertEqual([p['id'] for p in cfg['prefreeze']['conformance_prompts']],
                         ['oodp/1', 'oodp/2', 'oodp/3', 'oodp/4'])
        cp = receipt['conformance_prompts']
        self.assertEqual(sorted(cp), ['1_selection_rule_stated_before_the_texts', '2_texts',
                                      '3_mechanical_check_results'])
        sb = json.loads(after['CELLS'])['provenance']['vocabulary_alignment']['superseded_by']
        self.assertEqual(sb['sha256'], DELIVERED['PROTO'])
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

    def test_a_CRLF_config_is_refused(self):
        d = dict(self.PRE)
        d['CONFIG'] = d['CONFIG'].replace(b'\n', b'\r\n')
        rc, err, receipt, after = self._drive(
            d, patch={'PRIOR_CONFIG_SHA256': sha(d['CONFIG']),
                      'PRIOR_CONFIG_BYTES': len(d['CONFIG'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'CRLF config')
        self.assertIn('precondition', err)

    # -- moved outside its section -------------------------------------------
    def _moving(self, key):
        def wrap(real, m):
            ins = next(i for i in m.INSERTIONS if i.key == key)

            def moved(old):
                return m.move_out(real(old), ins)
            return moved
        return wrap

    def test_an_insertion_moved_out_of_its_section_is_refused(self):
        for key in ('protocol.5_3', 'protocol.14_6', 'architecture.7_1.rows_21a_21b',
                    'architecture.6_3', 'protocol.appendix_b.server_supervision'):
            with self.subTest(key=key):
                d = dict(self.PRE)
                rc, err, receipt, after = self._drive(d, wrap_insert_all=self._moving(key))
                self._assert_refused_unchanged(d, rc, err, receipt, after, 'moved ' + key)
                self.assertIn('postcondition', err)
                self.assertIn('"%s": false' % key, err)

    def test_only_the_section_bound_refuses_an_anchor_that_lies_in_14_7(self):
        """The '### 14.7' heading is moved above the 14.6 anchor paragraph, so the anchor,
        and the paragraph after it, lie in 14.7 while staying directly after the anchor.
        Pins re-pointed, anchor precondition disabled: only the upper bound stands."""
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
        post = json.loads(err.split('NOTHING was written: ', 1)[1])
        self.assertIs(post['three_way_contract_after']['holds'], True)
        self.assertNotEqual(post['config']['rule_block_sha256_after'], RULE_BLOCK)
        self.assertIn('execution.auto_abort.restart_cap', post['config']['added_keys'])

    def test_engineering_acquisition_that_differs_from_BOUND_LIMITS_is_refused(self):
        m = _load_tool()
        limits = m.bound_limits()
        self.assertIsNotNone(limits)
        off = dict(limits, wall_seconds_total=601.0)
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, patch={'bound_limits': lambda: dict(off)})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'BOUND_LIMITS')
        self.assertIn('"engineering_acquisition_equals_run_smoke_BOUND_LIMITS": false', err)

    # -- the four prompts against the sources ------------------------------------
    def _prompt_refusal(self, sources, needle):
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, sources=sources)
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

    def test_a_source_that_defines_a_conformance_entry_point_is_refused(self):
        self._prompt_refusal(synthetic_sources([{'task_id': 902, 'prompt': 'Unrelated words.',
                                                 'code': 'def rotate_digits(s):\n  return s\n'}]),
                             '"entry_point_defined_in_a_source": true')

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

    # -- the one-shot guard ------------------------------------------------------
    def test_the_amended_documents_are_refused(self):
        rc, err, receipt, amended = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        d = dict(amended)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, as pinned')
        self.assertIn('precondition', err)
        d2, patch, shown = self._repoint(d)
        patch['PRIOR_PRIOR_SUCCESSORS'] = 6
        rc, err, receipt, after = self._drive(d2, patch=patch, commit_protocol=shown)
        self._assert_refused_unchanged(d2, rc, err, receipt, after, 'amended, pins re-pointed')
        self.assertIn('the amendment is already present', err)

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

    def _amended(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        before = {self.KEYS[k]: v for k, v in self.PRE.items()}
        return before, {self.KEYS[k]: v for k, v in after.items()}, receipt

    def test_the_verifier_re_derives_the_amendment(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, after, receipt, self.PRE['PROTO'])
        self.assertIs(got['all_verified'], True, json.dumps(got)[:3000])
        self.assertEqual(sum(got['insertions_listed'].values()), 18)
        self.assertEqual(len(got['each_insertion_under_its_heading']), 16)
        self.assertIs(v.negative_controls(before, after, receipt, self.PRE['PROTO'])
                      ['every_control_failed'], True)

    def test_the_verifier_refuses_a_receipt_that_omits_an_insertion(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        receipt = dict(receipt, insertions=[i for i in receipt['insertions']
                                            if i['key'] != 'protocol.13_1'])
        got = v.verify(before, after, receipt, self.PRE['PROTO'])
        self.assertIs(got['all_verified'], False)
        self.assertIs(got['deleting_the_insertions_reproduces_the_parent']['protocol'], False)

    def test_the_verifier_refuses_a_wrong_demoted_commit_and_a_moved_heading(self):
        v = _load_verifier()
        before, after, receipt = self._amended()
        got = v.verify(before, after, receipt, b'not the 48f4d70 protocol')
        self.assertIs(got['cells']['demoted_commit_carries_the_parent_successor'], False)
        self.assertIs(got['all_verified'], False)
        rows = [i for i in receipt['insertions'] if i['key'] == 'protocol.5_8']
        moved = dict(receipt, insertions=[dict(i, section='### 5.7 Sandbox under two workers')
                                          if i['key'] == 'protocol.5_8' else i
                                          for i in receipt['insertions']])
        self.assertEqual(len(rows), 1)
        got = v.verify(before, after, moved, self.PRE['PROTO'])
        self.assertIs(got['each_insertion_under_its_heading']['protocol.5_8'], False)
        self.assertIs(got['all_verified'], False)

    def test_the_real_amendment_commit_verifies_if_present(self):
        """After the amendment is committed: the verifier's main() on that commit (the
        one that ADDS a REPAIR_AMENDMENT_RECEIPT). Skipped before it exists."""
        log = subprocess.run(['git', '-C', str(REPO), 'log', '--diff-filter=A', '--format=%H',
                              '--name-only', '--', 'results/live_ab/'],
                             capture_output=True, text=True)
        commit, cur = None, None
        for line in log.stdout.splitlines() if log.returncode == 0 else ():
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                cur = line
            elif line.startswith('results/live_ab/REPAIR_AMENDMENT_RECEIPT_'):
                commit = cur
                break
        if commit is None:
            self.skipTest('no commit in this history adds a repair amendment receipt')
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
    compare with the delivered receipt. Skipped where the gitignored sources are
    absent; the tool itself refuses without them."""

    def test_the_recorded_similarity_maxima_are_reproduced(self):
        found = _real_sources_dir()
        if found is None:
            self.skipTest('the three pinned roster sources are not on this host '
                          '(set LIVE_AB_SOURCES_DIR)')
        receipts = sorted((REPO / 'results' / 'live_ab').glob('REPAIR_AMENDMENT_RECEIPT_*.json'))
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
        want = json.loads(receipts[0].read_bytes())['conformance_prompts'][
            '3_mechanical_check_results']
        for g, w in zip(got['per_prompt'], want['per_prompt']):
            for key in ('id', 'max_jaccard', 'closest_source_uid', 'max_jaccard_smoke_tasks',
                        'closest_smoke_task', 'normalized_equal_to', 'prompt_sha256'):
                self.assertEqual(g[key], w[key], (g['id'], key))
        with gzip.open(tmp / 'HumanEval.jsonl.gz', 'rt') as fh:
            self.assertEqual(sum(1 for line in fh if line.strip()), 164)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
