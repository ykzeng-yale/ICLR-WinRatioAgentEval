"""Witnesses for the hardened engineering-cap amendment tool (review findings config 0 and 1).

The two findings, as confirmed at 5a81c34:

    config 0: "Amendment tool rewrites ARCHITECTURE_FINAL.md in text mode with no
    digest pin and no check that the change stays inside section 6.1, and still
    reports success." Expected instead: "Read and write the three documents as
    bytes. Require the architecture file's pre-image to be the reviewed digest
    6b36c4a4..., as the protocol is pinned to f75de323. Assert
    new_arch_bytes.replace(INSERTED,b'',1) == old_arch_bytes before writing, and
    refuse otherwise."

    config 1: "The 'protocol_change_is_inside_appendix_b_only' check only confirms
    the insertion comes after the Appendix B heading, not before Appendix C."

HOW EVERY CASE RUNS
  The PRE-amendment blobs (`git show 0e05d96~1:<path>`, read-only, once per class)
  are copied into a fresh temporary directory. A fresh instance of the tool is
  loaded, and its module paths (REPO, CONFIG, ARCH, PROTO, CELLS) are re-pointed at
  the copies. The harness asserts that each re-pointed path lies under the
  temporary directory. The tool's `subprocess` (git rev-parse and git show) is
  replaced in that instance only, and `lab_common.harness_file_hashes` is stubbed
  for the duration of the call. Then main() runs. The real documents are never
  opened for writing, and every drive compares their digests before and after.

The reviewer's witnesses, which the unhardened tool ACCEPTED with exit 0, and
which must now refuse with nothing written:
  W1  line 1 of ARCHITECTURE_FINAL.md ends in CRLF, outside section 6.1;
  W1b a lone CR outside section 6.1;
  W1c an unreviewed extra line outside section 6.1;
  W2  the configuration fence moved under '## Appendix C.' (Appendix B keeps no
      fence), with the protocol pin re-pointed at that protocol, so that ONLY the
      placement check stands between it and success;
  and a fault-injected inserter that also edits one byte of ARCHITECTURE outside
  the fence.
Controls that must still pass: the pristine pre-images reproduce the delivered
0e05d96 bytes exactly. Against the amended documents the tool refuses, which is
the one-shot guard.

SCOPE: this needs the repository's git history (0e05d96 and its parent). Without
it the class is skipped, and the skip names the reason. Nothing here runs a model,
server, build or network request.
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
TOOL = HERE / 'engineering_cap_amendment.py'
REL = {'CONFIG': 'experiments/live_ab/config.json',
       'ARCH': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
       'PROTO': 'experiments/live_ab/design/protocol_FINAL.md',
       'CELLS': 'experiments/live_ab_validation/cells.json'}
AMENDMENT = '0e05d96'
#: the reviewed pre-images, as the review states them
REVIEWED = {'CONFIG': '05255df3b0d12bb6f5571616378a1366c67c6eb8b913def907c6a5d901e1731c',
            'ARCH': '6b36c4a41a23612bc2b8035ac2538977f81f341ed1527fee9c5535578254241c',
            'PROTO': 'f75de3235ae0431b727cf7c24b09927204a1da8c5424e14ea428dbfea256f48b'}
ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'

_loaded = [0]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _blob(rev: str, rel: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, rel)],
                          capture_output=True, check=True).stdout


def _load_tool():
    _loaded[0] += 1
    spec = importlib.util.spec_from_file_location(
        'engineering_cap_amendment_under_test_%d' % _loaded[0], TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _real_digests() -> dict:
    out = {k: sha((REPO / rel).read_bytes()) for k, rel in REL.items()}
    out['results/live_ab'] = sorted(p.name for p in (REPO / 'results' / 'live_ab').iterdir())
    return out


def _move_fence_under_appendix_c(proto: bytes) -> bytes:
    """The config-1 witness: Appendix B keeps its prose and loses its fence, and the
    same fence appears right after the '## Appendix C.' heading."""
    b0 = proto.index(PROTO_MARKER)
    f0 = proto.index(b'```json', b0)
    f1 = proto.index(b'```', f0 + len(b'```json')) + 3
    fence = proto[f0:f1]
    without = proto[:f0] + proto[f1:]
    c0 = without.index(b'## Appendix C.')
    c_eol = without.index(b'\n', c0) + 1
    moved = without[:c_eol] + b'\n' + fence + b'\n' + without[c_eol:]
    assert b'```json' not in moved[moved.index(PROTO_MARKER):moved.index(b'## Appendix C.')]
    return moved


class EngineeringCapAmendmentWitnessTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.PRE = {k: _blob(AMENDMENT + '~1', rel) for k, rel in REL.items()}
            cls.AMENDED = {k: _blob(AMENDMENT, rel) for k, rel in REL.items()}
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest('the git history holding %s and its parent is not '
                                    'available here: %s' % (AMENDMENT, e))

    # -- harness -------------------------------------------------------------
    def _drive(self, docs, patch=None, wrap_insert_once=None, commit_protocol=None):
        """Run the REAL main() of a fresh tool instance on scratch copies of ``docs``.
        Returns (exit code, stderr, receipt or None, bytes of the four documents after)."""
        before_real = _real_digests()
        tmp = Path(tempfile.mkdtemp(prefix='eca_witness_'))
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
        receipts = sorted((tmp / 'results' / 'live_ab').glob('CONFIG_AMENDMENT_RECEIPT_*.json'))
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

    # -- the pre-images ------------------------------------------------------
    def test_the_blobs_are_the_reviewed_pre_images_and_the_tool_pins_them(self):
        m = _load_tool()
        for k, want in REVIEWED.items():
            self.assertEqual(sha(self.PRE[k]), want, k)
        self.assertEqual(m.PRIOR_BLOCK_SHA256, REVIEWED['CONFIG'])
        self.assertEqual(m.PRIOR_ARCH_SHA256, REVIEWED['ARCH'])
        self.assertEqual(m.PRIOR_SUCCESSOR, REVIEWED['PROTO'])
        self.assertTrue(all(v.count(b'\r') == 0 for v in self.PRE.values()))

    # -- control: the pristine pre-images still pass -------------------------
    def test_control_the_pristine_pre_images_reproduce_the_delivered_bytes(self):
        rc, err, receipt, after = self._drive(dict(self.PRE))
        self.assertEqual(rc, 0, err)
        for k in ('CONFIG', 'ARCH', 'PROTO'):
            self.assertEqual(after[k], self.AMENDED[k], '%s differs from %s' % (k, AMENDMENT))
        # cells.json: identical to the delivered file except the newest successor's
        # recorded_utc, which is the time of the run.
        got, want = json.loads(after['CELLS']), json.loads(self.AMENDED['CELLS'])
        for d in (got, want):
            d['provenance']['vocabulary_alignment']['superseded_by'].pop('recorded_utc')
        self.assertEqual(got, want)
        post = receipt['postcondition_checked']
        self.assertIs(post['architecture_change_is_inside_6_1_only'], True)
        self.assertIs(post['protocol_change_is_inside_appendix_b_only'], True)
        self.assertEqual(post['deleting_the_inserted_text_reproduces_each_preimage'],
                         {'config': True, 'architecture': True, 'protocol': True})
        self.assertIs(receipt['precondition_checked']['architecture_is_the_reviewed_preimage'],
                      True)
        self.assertIs(receipt['written']['read_back_equals_computed'], True)

    # -- config 0: the architecture witnesses ------------------------------------
    def _w1(self):
        d = dict(self.PRE)
        i = d['ARCH'].index(b'\n')
        d['ARCH'] = d['ARCH'][:i] + b'\r' + d['ARCH'][i:]
        self.assertLess(d['ARCH'].index(b'\r'), d['ARCH'].index(ARCH_MARKER))
        return d

    def test_W1_crlf_on_line_1_outside_6_1_is_refused(self):
        """The reviewer's witness verbatim: the unhardened tool exited 0 on it."""
        d = self._w1()
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'W1')
        self.assertIn('precondition', err)

    def test_W1_is_refused_even_with_the_architecture_pin_repointed_at_it(self):
        """Two independent guards: with the pin moved to W1's own digest, the
        no-CR-byte rule still refuses it."""
        d = self._w1()
        rc, err, receipt, after = self._drive(d, patch={'PRIOR_ARCH_SHA256': sha(d['ARCH'])})
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'W1, pin re-pointed')

    def test_W1b_a_lone_cr_outside_6_1_is_refused(self):
        d = dict(self.PRE)
        j = d['ARCH'].index(b'\n', d['ARCH'].index(b'\n') + 1)
        k = d['ARCH'].rindex(b' ', 0, j)
        d['ARCH'] = d['ARCH'][:k] + b'\r' + d['ARCH'][k + 1:]
        self.assertLess(d['ARCH'].index(b'\r'), d['ARCH'].index(ARCH_MARKER))
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'W1b')

    def test_W1c_an_unreviewed_line_outside_6_1_is_refused(self):
        d = dict(self.PRE)
        d['ARCH'] = d['ARCH'].replace(b'\n', b'\nUNREVIEWED EDIT OUTSIDE 6.1\n', 1)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'W1c')
        self.assertIn('architecture_is_the_reviewed_preimage": false', err)

    def test_an_inserter_that_also_edits_architecture_outside_the_fence_is_refused(self):
        """Fault injection: the byte-additivity check can fail. The inserter also
        changes one byte of ARCHITECTURE's first line. The three blocks stay
        identical, so only the bytes-in-equals-bytes-out check can catch it."""
        def wrap(real):
            def faulty(raw):
                out = real(raw)
                marker = ARCH_MARKER if isinstance(out, bytes) else ARCH_MARKER.decode()
                if marker in out:
                    nl = out.index(b'\n' if isinstance(out, bytes) else '\n')
                    out = out[:nl] + out[nl:nl + 1] * 2 + out[nl + 1:]
                return out
            return faulty
        d = dict(self.PRE)
        rc, err, receipt, after = self._drive(d, wrap_insert_once=wrap)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'faulty inserter')
        self.assertIn('postcondition', err)

    # -- config 1: the Appendix C witness ------------------------------------
    def test_W2_a_fence_under_appendix_c_is_refused(self):
        """The reviewer's witness. The protocol pin and the cells.json successor are
        re-pointed at the altered protocol, so every other check passes, and only
        the placement bound can refuse it. The unhardened tool exited 0 on it, with
        'protocol_change_is_inside_appendix_b_only' true."""
        d = dict(self.PRE)
        d['PROTO'] = _move_fence_under_appendix_c(self.PRE['PROTO'])
        cells = json.loads(d['CELLS'])
        cells['provenance']['vocabulary_alignment']['superseded_by']['sha256'] = sha(d['PROTO'])
        d['CELLS'] = (json.dumps(cells, indent=1) + '\n').encode('utf-8')
        rc, err, receipt, after = self._drive(d, patch={'PRIOR_SUCCESSOR': sha(d['PROTO'])},
                                              commit_protocol=d['PROTO'])
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'W2')
        self.assertIn('postcondition', err)
        m = _load_tool()
        where = m.confinement(m.insert_once(d['PROTO']), PROTO_MARKER)
        self.assertIs(where['insertion_inside_fence'], True)     # inside A fence ...
        self.assertIs(where['fence_inside_section'], False)      # ... not Appendix B's

    def test_section_span_has_an_upper_bound_and_skips_fenced_hashes(self):
        m = _load_tool()
        doc = (b'# T\n\n### 6.1 Full key list\n\n```bash\n# not a heading\n```\n\n'
               b'#### 6.1.1 a subsection stays inside\n\n```json\n{}\n```\n\n'
               b'### 6.2 next\n\nrest\n')
        s0, s1 = m.section_span(doc, ARCH_MARKER)
        self.assertEqual(doc[s0:s1].count(b'### 6.2'), 0)
        self.assertTrue(doc[s1:].startswith(b'### 6.2 next'))
        self.assertIn(b'# not a heading', doc[s0:s1])
        self.assertIn(b'#### 6.1.1', doc[s0:s1])
        higher = doc.replace(b'### 6.2 next', b'## 7. next')
        s0, s1 = m.section_span(higher, ARCH_MARKER)
        self.assertTrue(higher[s1:].startswith(b'## 7. next'))
        with self.assertRaises(ValueError):
            m.section_span(b'prose ### 6.1 Full key list\n', ARCH_MARKER)

    # -- the one-shot guard --------------------------------------------------
    def test_the_amended_documents_are_refused(self):
        """Against the 0e05d96 documents the tool refuses. The preconditions pin the
        pre-amendment bytes, so they refuse first. With every pin re-pointed at the
        amended bytes, the kept 'section already exists' refusal still stops it."""
        d = dict(self.AMENDED)
        rc, err, receipt, after = self._drive(d)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, as pinned')
        self.assertIn('precondition', err)
        repointed = {'PRIOR_BLOCK_SHA256': sha(d['CONFIG']), 'PRIOR_BLOCK_BYTES': len(d['CONFIG']),
                     'PRIOR_ARCH_SHA256': sha(d['ARCH']), 'PRIOR_SUCCESSOR': sha(d['PROTO'])}
        rc, err, receipt, after = self._drive(d, patch=repointed)
        self._assert_refused_unchanged(d, rc, err, receipt, after, 'amended, pins re-pointed')
        self.assertIn('the section already exists', err)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
