"""Witnesses for harness_pin_successor.py (the harness pin successor of the EB1+EB5 subset).

HOW THE CASES RUN
  Everything is read from git objects of this repository at fixed, immutable revisions:
  PREDECESSOR (b049307, the reviewed head), AMENDMENT_COMMIT (474f9d8), E2E_REV (a289fa5,
  the last commit before the tool), AMENDMENT_V3_COMMIT (56df17f, amendment v3) and
  AMENDMENT_V4_COMMIT (90219f2, amendment v4).  The end-to-end cases run the tool on a sparse,
  shared clone of the repository checked out at E2E_REV, 56df17f or 90219f2 under a temporary
  directory, so the working tree of this checkout is
  never written and the cases stay valid after later commits.  A "mutated predecessor" (and
  every other mutant commit) is a real commit made in that clone with git plumbing (one blob
  changed or added); nothing is pushed or committed here.

NEGATIVE CONTROLS (each must refuse or report the defect):
  * one mutated blob changes the canonical digest and the tool refuses (predecessor_digest),
    in memory (a reader that flips one byte) and end to end (a committed mutation);
  * a predecessor git cannot resolve refuses (predecessor_missing), and main() exits 2
    writing nothing;
  * an altered diff, or the diff applied to altered old bytes, does not reproduce the new file;
  * a binary file added to the subset (outside the harness) reproduces end to end from its
    diff (DIFF_ARGV carries --binary; e7470c7's sm8_diagnosis tar.gz archives are the real
    fixture), and a corrupted binary patch does not reproduce
    (``subset_diff_does_not_reproduce``);
  * an injected GIT_DIFF_OPTS changes even the tool's own argv output, and injected git
    configuration a plain ``git diff``; neither changes the tool's digest;
  * a rule-block edit moves the rule-block digest, an edit outside the block does not;
  * a record whose pins all belong to unchanged artifacts is not called stale;
  * a missing fixture cache with no compiler, a partial cache, a skipped or partial control
    run, or a control that passes without a compiler is never judged ``ok``;
  * a suite output without its ``Ran`` line, with fewer tests than planned, with a FAILED
    verdict, with a nonzero exit, or whose verdict appears only on stdout is never a pass;
  * a watched process outside a suite's tree that is not an orphan it started is
    ``foreign`` and makes the run not solo (a live sampler flags a real one);
  * a dirty working tree refuses; a second write to the same receipt path refuses;
    ``--no-suites`` into results/live_ab refuses;
  * amendment v3 (56df17f): one byte of the protocol changed after it, a v3 receipt whose
    written protocol digest is not the blob at its commit, a v3 receipt copied onto a289fa5
    without its commit, and a v3 receipt naming another v2 receipt digest each refuse
    (``amendment_receipt_disagrees`` / ``amendment_chain:v3`` / ``amendment_chain_link:v3``);
  * amendment v4 (90219f2): a v4 receipt naming another v3 receipt digest, and a v4 receipt
    copied onto 56df17f without its commit, each refuse (``amendment_chain_link:v4`` /
    ``amendment_chain:v4``, ``amendment_receipt_disagrees``);
  * the mutation partition of the final verification of 8f0b4ae: the owner's 05:18 headline
    counts, one entry in two classes, a specified entry in no class, an equivalent dropped, a
    guard without its 2113dbd control, and a rerun-counted entry outside the right-control
    kills each refuse (``mutation_partition:...``); with MUTATION_LOGS_8F0B4AE naming the
    verifier's log directory the constant is recomputed from the logs, and a copy of the logs
    with one verdict flipped does not reproduce it;
  * a superseded receipt whose recorded successor map is not the git blobs at the head it
    recorded refuses (``superseded_map_does_not_reproduce``);
  * a committed ``HARNESS_PIN_SUCCESSOR_*.json`` at HEAD that names no SUPERSEDES entry refuses
    (``superseded_receipts_incomplete``), and ``since_the_superseded_receipt`` picks the ..._2009
    receipt (head 98ce004) once it is listed;
  * a missing, unparsable, empty or row-incomplete ``--runs-of-this-step`` file refuses and
    main() writes nothing.

Nothing here runs a model, a llama-server, a llama.cpp build or a network request.  The
fixture cases compile the C test double under temporary roots (root 07:03 item 1).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LIVE = REPO / 'experiments' / 'live_ab'
CONTROLS = REPO / 'experiments' / 'live_ab_controls'
for _p in (HERE, LIVE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import harness_pin_successor as hps                                     # noqa: E402
import lab_common                                                       # noqa: E402

#: The last commit before the tool (two comments fixed); the end-to-end clone checks it out.
E2E_REV = 'a289fa5e52cf8a1e3e758e750f681f0c299d07c9'
#: Its successor harness map (34 entries), computed once from git blobs when the tool landed.
E2E_CANONICAL = '6f96e81596708627d5633e929dbc4eceae46414c31933db1f0db08f72d31944c'
SPARSE = ('experiments/live_ab', 'experiments/live_ab_controls', 'experiments/local_stream',
          'experiments/live_ab_serving', 'experiments/live_ab_tools',
          'experiments/live_ab_validation', 'results/live_ab', 'src')


def git(*args: str, cwd: Path = REPO, stdin: bytes | None = None,
        env: dict | None = None) -> bytes:
    return subprocess.run(['git', '-C', str(cwd), *args], input=stdin, capture_output=True,
                          check=True, env=env or hps.git_env(), timeout=300).stdout


def make_clone(dest: Path, rev: str = E2E_REV) -> Path:
    git('clone', '-q', '--shared', '--no-checkout', str(REPO), str(dest))
    git('sparse-checkout', 'set', *SPARSE, cwd=dest)
    git('checkout', '-q', '--detach', rev, cwd=dest)
    return dest


def commit_with(clone: Path, parent: str, blobs: dict) -> str:
    """A commit in ``clone``: ``parent`` with each ``rel -> bytes`` of ``blobs`` written
    (git plumbing only; nothing is checked out or pushed)."""
    env = dict(hps.git_env(), GIT_INDEX_FILE=str(clone / '.git' / 'mutant_index'),
               GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@t')
    git('read-tree', parent, cwd=clone, env=env)
    for rel, data in blobs.items():
        oid = git('hash-object', '-w', '--stdin', cwd=clone, stdin=data).decode().strip()
        git('update-index', '--add', '--cacheinfo', '100644,%s,%s' % (oid, rel), cwd=clone,
            env=env)
    tree = git('write-tree', cwd=clone, env=env).decode().strip()
    return git('commit-tree', tree, '-p', parent, '-m', 'mutant', cwd=clone,
               env=env).decode().strip()


def mutated_predecessor(clone: Path, rel: str) -> str:
    """A commit in ``clone``: PREDECESSOR with one byte of ``rel`` flipped (plumbing only)."""
    blob = bytearray(git('cat-file', 'blob', '%s:%s' % (hps.PREDECESSOR, rel), cwd=clone))
    blob[10] ^= 0x01
    env = dict(hps.git_env(), GIT_INDEX_FILE=str(clone / '.git' / 'mutant_index'),
               GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@t')
    oid = git('hash-object', '-w', '--stdin', cwd=clone, stdin=bytes(blob)).decode().strip()
    git('read-tree', hps.PREDECESSOR, cwd=clone, env=env)
    git('update-index', '--cacheinfo', '100644,%s,%s' % (oid, rel), cwd=clone, env=env)
    tree = git('write-tree', cwd=clone, env=env).decode().strip()
    return git('commit-tree', tree, '-p', hps.PREDECESSOR, '-m', 'mutant', cwd=clone,
               env=env).decode().strip()


class _Clone(unittest.TestCase):
    """One sparse clone at E2E_REV per class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_test_')))
        cls.clone = make_clone(cls.tmp / 'clone')

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(str(cls.tmp), ignore_errors=True)


# --------------------------------------------------------------------------- #
class PredecessorTests(unittest.TestCase):

    def test_the_b049307_map_is_the_reviewed_33_entry_pin(self):
        pmap = hps.harness_map(hps.GitTree(REPO, hps.PREDECESSOR))
        self.assertEqual(len(pmap), 33)
        self.assertEqual(hps.sha256_canonical(pmap), hps.PREDECESSOR_CANONICAL)
        self.assertEqual(hps.predecessor_problems(pmap), [])
        self.assertTrue(pmap['config.json'].startswith('e4d42f5d'))

    def test_negative_one_mutated_blob_changes_the_digest_and_refuses(self):
        class Mutated(hps.GitTree):
            def read(self, path):
                data = super().read(path)
                if path.endswith('/lab_monitor.py'):
                    data = data[:5] + bytes([data[5] ^ 1]) + data[6:]
                return data
        good = hps.harness_map(hps.GitTree(REPO, hps.PREDECESSOR))
        bad = hps.harness_map(Mutated(REPO, hps.PREDECESSOR))
        self.assertEqual([n for n in good if good[n] != bad[n]], ['lab_monitor.py'])
        self.assertNotEqual(hps.sha256_canonical(bad), hps.PREDECESSOR_CANONICAL)
        self.assertEqual(hps.predecessor_problems(bad), ['predecessor_digest'])
        self.assertEqual(hps.predecessor_problems(dict(list(good.items())[:32])),
                         ['predecessor_count:32', 'predecessor_digest'])

    def test_negative_a_missing_predecessor_refuses(self):
        with self.assertRaises(hps.Refused) as cm:
            hps.build_receipt(REPO, '0' * 40, run_suites=False)
        self.assertEqual(cm.exception.problems, ['predecessor_missing'])
        with self.assertRaises(hps.Refused):
            hps.GitTree(REPO, 'no-such-revision')
        with tempfile.TemporaryDirectory() as empty:
            git('init', '-q', empty, cwd=Path(empty))
            with self.assertRaises(hps.Refused) as cm:
                hps.build_receipt(Path(empty), hps.PREDECESSOR, run_suites=False)
            self.assertEqual(cm.exception.problems, ['predecessor_missing'])

    def test_negative_main_exits_2_and_writes_nothing_without_the_predecessor(self):
        with tempfile.TemporaryDirectory() as out:
            err = io.StringIO()
            with redirect_stderr(err):
                rc = hps.main(['--repo', str(REPO), '--predecessor', 'no-such-revision',
                               '--no-suites', '--out-dir', out])
            self.assertEqual(rc, 2)
            self.assertIn('predecessor_missing', err.getvalue())
            self.assertEqual(os.listdir(out), [])


class SemanticsTests(unittest.TestCase):
    """The tool's map is lab_common's map, on a directory and on git blobs."""

    def test_dir_mode_is_lab_common_harness_file_hashes(self):
        self.assertEqual(hps.harness_map_from_dir(LIVE), lab_common.harness_file_hashes())
        sample = {'b': [1.5, 'é'], 'a': None}
        self.assertEqual(hps.canonical_json(sample), lab_common.canonical_json(sample))
        self.assertEqual(hps.sha256_canonical(sample), lab_common.sha256_canonical(sample))

    def test_git_mode_equals_dir_mode_on_the_exported_b049307_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = git('archive', '--format=tar', hps.PREDECESSOR, 'experiments/live_ab')
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                tar.extractall(tmp, filter="data")
            exported = Path(tmp) / 'experiments' / 'live_ab'
            from_git = hps.harness_map(hps.GitTree(REPO, hps.PREDECESSOR))
            self.assertEqual(hps.harness_map_from_dir(exported), from_git)
            # negative controls: a new top-level module counts, nested and non-.py do not
            (exported / 'testdata' / 'nested.py').write_text('x = 1\n')
            (exported / 'notes.md').write_text('n\n')
            self.assertEqual(hps.harness_map_from_dir(exported), from_git)
            (exported / 'lab_new.py').write_text('x = 1\n')
            grown = hps.harness_map_from_dir(exported)
            self.assertEqual(len(grown), 34)
            self.assertNotEqual(hps.sha256_canonical(grown), hps.PREDECESSOR_CANONICAL)


class DiffTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.old = hps.GitTree(REPO, hps.PREDECESSOR)
        cls.new = hps.GitTree(REPO, hps.AMENDMENT_COMMIT)

    def test_a_modified_and_an_added_entry_reproduce_from_their_diffs(self):
        for name, status in (('lab_prepare.py', 'modified'),
                             ('lab_serving_manifest.py', 'added')):
            with self.subTest(name=name):
                row = hps.diff_entry(REPO, self.old, self.new, 'experiments/live_ab/' + name)
                self.assertEqual(row['status'], status)
                self.assertTrue(row['diff_applied_to_old_gives_new'])
                self.assertEqual(row['diff_sha256'], hps.sha256(hps.unified_diff(
                    REPO, self.old.rev, self.new.rev, 'experiments/live_ab/' + name)))
                self.assertGreater(row['lines_added'], 0)

    def test_every_hunk_carries_three_lines_of_context_and_full_blob_ids(self):
        path = 'experiments/live_ab/lab_orchestrator.py'
        diff = hps.unified_diff(REPO, self.old.rev, self.new.rev, path).decode()
        old_len = len(self.old.read(path).decode().splitlines())
        self.assertRegex(diff.splitlines()[1], r'^index [0-9a-f]{40}\.\.[0-9a-f]{40} ')
        self.assertEqual(diff.splitlines()[2:4], ['--- a/' + path, '+++ b/' + path])
        hunks = [h.splitlines() for h in diff.split('\n@@ ')[1:]]
        self.assertGreater(len(hunks), 10)
        for lines in hunks:
            first, _, count = lines[0].split(' ')[0][1:].partition(',')
            start, count = int(first), int(count or 1)
            body = lines[1:]
            lead = next(i for i, ln in enumerate(body) if ln[:1] in '+-')
            trail = next(i for i, ln in enumerate(reversed(body)) if ln[:1] in '+-')
            with self.subTest(hunk=start):
                self.assertEqual(lead, min(3, start - 1))       # 3 unless the file starts
                if start + count - 1 < old_len:                   # 3 unless the file ends
                    self.assertEqual(trail, 3)

    def test_negative_an_altered_diff_or_altered_old_bytes_do_not_reproduce(self):
        path = 'experiments/live_ab/lab_prepare.py'
        old, new = self.old.read(path), self.new.read(path)
        diff = hps.unified_diff(REPO, self.old.rev, self.new.rev, path)
        self.assertTrue(hps.diff_reproduces(old, new, diff, path))
        at = diff.index(b'\n+', diff.index(b'@@')) + 3
        altered = diff[:at] + bytes([diff[at] ^ 1]) + diff[at + 1:]
        self.assertFalse(hps.diff_reproduces(old, new, altered, path))
        self.assertFalse(hps.diff_reproduces(old + b'# changed\n', new, diff, path))
        self.assertFalse(hps.diff_reproduces(old, new + b'\n', diff, path))

    def test_a_binary_file_reproduces_from_its_diff(self):
        """DIFF_ARGV must carry --binary: without it, git diff emits only "Binary files ...
        differ" for an added binary file and diff_reproduces can never recreate the bytes.
        Real fixture: the sm8_diagnosis tar.gz archives added at e7470c7, whose subset diff
        the tool refused (subset_diff_does_not_reproduce) before this fix."""
        path = 'results/live_ab/sm8_diagnosis/20260925_1732/earlier_runs_logs.tar.gz'
        old_tree = hps.GitTree(REPO, 'e7470c7~1')
        new_tree = hps.GitTree(REPO, 'e7470c7')
        diff = hps.unified_diff(REPO, old_tree.rev, new_tree.rev, path)
        self.assertIn(b'GIT binary patch', diff)
        row = hps.diff_entry(REPO, old_tree, new_tree, path)
        self.assertEqual(row['status'], 'added')
        self.assertTrue(row['diff_applied_to_old_gives_new'])

    def test_negative_a_corrupted_binary_patch_does_not_reproduce(self):
        path = 'results/live_ab/sm8_diagnosis/20260925_1732/earlier_runs_logs.tar.gz'
        old_tree = hps.GitTree(REPO, 'e7470c7~1')
        new_tree = hps.GitTree(REPO, 'e7470c7')
        old, new = old_tree.read(path), new_tree.read(path)
        diff = hps.unified_diff(REPO, old_tree.rev, new_tree.rev, path)
        self.assertTrue(hps.diff_reproduces(old, new, diff, path))
        at = diff.index(b'\nliteral ')
        body_start = diff.index(b'\n', at + 1) + 1
        corrupt_at = body_start + 5
        corrupted = diff[:corrupt_at] + bytes([diff[corrupt_at] ^ 1]) + diff[corrupt_at + 1:]
        self.assertNotEqual(corrupted, diff)
        self.assertFalse(hps.diff_reproduces(old, new, corrupted, path))

    def test_the_digest_ignores_injected_git_environment(self):
        """GIT_DIFF_OPTS overrides --unified even on the tool's own command line, and
        injected configuration changes a plain git diff; neither reaches the digest."""
        path = 'experiments/live_ab/lab_prepare.py'
        ours = hps.unified_diff(REPO, self.old.rev, self.new.rev, path)
        inject = {'GIT_DIFF_OPTS': '--unified=7', 'GIT_CONFIG_COUNT': '1',
                  'GIT_CONFIG_KEY_0': 'diff.noprefix', 'GIT_CONFIG_VALUE_0': 'true'}
        raw_env = dict(os.environ, **inject)
        same_argv = subprocess.run(['git', '-C', str(REPO), *hps.DIFF_ARGV, self.old.rev,
                                    self.new.rev, '--', path], capture_output=True,
                                   env=raw_env, check=True).stdout
        plain = subprocess.run(['git', '-C', str(REPO), 'diff', self.old.rev, self.new.rev,
                                '--', path], capture_output=True, env=raw_env,
                               check=True).stdout
        self.assertNotEqual(same_argv, ours, 'GIT_DIFF_OPTS changes the fixed argv output')
        self.assertNotEqual(plain, ours)
        with mock.patch.dict(os.environ, inject):
            self.assertEqual(hps.unified_diff(REPO, self.old.rev, self.new.rev, path), ours)
            self.assertNotIn('GIT_DIFF_OPTS', hps.git_env())


class BinaryDiffFixtureTests(unittest.TestCase):
    """A fresh, throwaway git repository (not REPO): a real base commit and a real commit
    adding a binary file, exercising GitTree, unified_diff and diff_reproduces end to end on
    genuinely-committed bytes -- the path that needed --binary in DIFF_ARGV.  (The real
    fixture is DiffTests: the sm8_diagnosis tar.gz archives added at e7470c7, refused
    subset_diff_does_not_reproduce before this fix; this class isolates the same defect from
    that history so it stays provable independent of it.)"""

    def test_a_freshly_committed_binary_file_reproduces_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = dict(hps.git_env(), GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t',
                      GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
            git('init', '-q', str(repo), cwd=repo)
            (repo / 'README.md').write_text('base\n')
            git('add', 'README.md', cwd=repo, env=env)
            git('commit', '-q', '-m', 'base', cwd=repo, env=env)
            base = git('rev-parse', 'HEAD', cwd=repo, env=env).decode().strip()

            path = 'results/fixture/added.bin'
            blob = (bytes(range(256)) * 40) + b'\x00binary\x00' * 5
            (repo / 'results' / 'fixture').mkdir(parents=True)
            (repo / path).write_bytes(blob)
            git('add', path, cwd=repo, env=env)
            git('commit', '-q', '-m', 'add a binary file', cwd=repo, env=env)
            head = git('rev-parse', 'HEAD', cwd=repo, env=env).decode().strip()

            old_tree, new_tree = hps.GitTree(repo, base), hps.GitTree(repo, head)
            diff = hps.unified_diff(repo, old_tree.rev, new_tree.rev, path)
            self.assertIn(b'GIT binary patch', diff)
            row = hps.diff_entry(repo, old_tree, new_tree, path)
            self.assertEqual(row['status'], 'added')
            self.assertEqual(row['new_sha256'], hps.sha256(blob))
            self.assertTrue(row['diff_applied_to_old_gives_new'])

    def test_negative_a_corrupted_committed_binary_patch_does_not_reproduce(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = dict(hps.git_env(), GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t',
                      GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
            git('init', '-q', str(repo), cwd=repo)
            (repo / 'README.md').write_text('base\n')
            git('add', 'README.md', cwd=repo, env=env)
            git('commit', '-q', '-m', 'base', cwd=repo, env=env)
            base = git('rev-parse', 'HEAD', cwd=repo, env=env).decode().strip()

            path = 'results/fixture/added.bin'
            blob = (bytes(range(256)) * 40) + b'\x00binary\x00' * 5
            (repo / 'results' / 'fixture').mkdir(parents=True)
            (repo / path).write_bytes(blob)
            git('add', path, cwd=repo, env=env)
            git('commit', '-q', '-m', 'add a binary file', cwd=repo, env=env)
            head = git('rev-parse', 'HEAD', cwd=repo, env=env).decode().strip()

            old_tree, new_tree = hps.GitTree(repo, base), hps.GitTree(repo, head)
            diff = hps.unified_diff(repo, old_tree.rev, new_tree.rev, path)
            self.assertTrue(hps.diff_reproduces(None, blob, diff, path))
            at = diff.index(b'\nliteral ')
            body_start = diff.index(b'\n', at + 1) + 1
            corrupt_at = body_start + 5
            corrupted = diff[:corrupt_at] + bytes([diff[corrupt_at] ^ 1]) + diff[corrupt_at + 1:]
            self.assertNotEqual(corrupted, diff)
            self.assertFalse(hps.diff_reproduces(None, blob, corrupted, path))


class RuleBlockTests(unittest.TestCase):

    def test_the_rule_block_is_cbfd1792_at_b049307_and_at_the_amendment(self):
        for rev in (hps.PREDECESSOR, hps.AMENDMENT_COMMIT):
            with self.subTest(rev=rev[:7]):
                tree = hps.GitTree(REPO, rev)
                cfg = json.loads(tree.read(hps.CONFIG_REL))
                keys = hps.module_constant(tree.read('experiments/live_ab/lab_common.py'),
                                           'RULE_BLOCK_KEYS')
                self.assertEqual(tuple(keys), lab_common.RULE_BLOCK_KEYS)
                self.assertEqual(hps.rule_block_digest(cfg, keys), hps.RULE_BLOCK)
                self.assertEqual(lab_common.rule_block_sha256(cfg), hps.RULE_BLOCK)

    def test_negative_a_rule_block_edit_moves_it_an_edit_outside_does_not(self):
        cfg = json.loads(hps.GitTree(REPO, hps.AMENDMENT_COMMIT).read(hps.CONFIG_REL))
        keys = lab_common.RULE_BLOCK_KEYS
        outside = json.loads(json.dumps(cfg))
        outside['server_supervision']['max_supervised_restarts_per_server_per_trial'] = 2
        self.assertEqual(hps.rule_block_digest(outside, keys), hps.RULE_BLOCK)
        inside = json.loads(json.dumps(cfg))
        inside['monitor']['delta'] = 0.04
        self.assertNotEqual(hps.rule_block_digest(inside, keys), hps.RULE_BLOCK)
        del inside['monitor']
        with self.assertRaises(hps.Refused):
            hps.rule_block_digest(inside, keys)

    def test_module_constant_reads_source_not_imports(self):
        src = hps.GitTree(REPO, hps.PREDECESSOR).read('experiments/live_ab/lab_common.py')
        self.assertEqual(tuple(hps.module_constant(src, 'REUSED_FILES')),
                         lab_common.REUSED_FILES)
        with self.assertRaises(hps.Refused):
            hps.module_constant(src, 'NO_SUCH_CONSTANT')


class ClassificationTests(unittest.TestCase):
    H = {i: ('%x' % i) * 64 for i in range(1, 10)}

    def table(self) -> dict:
        h = self.H
        return {'experiments/live_ab/a.py': {'b049307': h[1], 'head': h[2]},
                'experiments/live_ab/b.py': {'b049307': h[3], 'head': h[3]},
                'experiments/live_ab/c.py': {'b049307': None, 'head': h[4]}}

    def test_moved_unchanged_historical_and_other_pins(self):
        h = self.H
        # the JSON PATH names an artifact (a.py; b.py under 'older'), never the value text
        record = {'pins': {'experiments/live_ab/a.py': h[1], 'by_value': h[3],
                           'older': {'experiments/live_ab/b.py': 'was %s' % h[9]},
                           'y': [h[8]], 'z': h[4],
                           'text': 'experiments/live_ab/b.py is not a key here'}}
        c = hps.classify_pins(record, self.table(), frozenset([h[8]]))
        self.assertEqual(c['pins_found'], 5)
        self.assertEqual(c['moved_artifacts'], ['experiments/live_ab/a.py'])
        self.assertEqual(c['unchanged_artifacts'], ['experiments/live_ab/b.py'])
        self.assertEqual([x['value'] for x in c['already_historical']], [h[9]])
        self.assertEqual([x['artifacts'] for x in c['successor_only']],
                         [['experiments/live_ab/c.py']])
        self.assertEqual(c['not_a_digest_at_either_revision'],
                         [{'json_path': '$.pins.y[0]', 'value': h[8],
                           'in_real_serving_manifest': True, 'in_successor_config': False}])
        self.assertTrue(hps.record_verdict(c).startswith('STALE'))

    def test_negative_a_record_of_unchanged_pins_is_not_called_stale(self):
        c = hps.classify_pins({'p': self.H[3], 'q': {'experiments/live_ab/b.py': self.H[3]}},
                              self.table())
        self.assertEqual(c['moved_artifacts'], [])
        self.assertFalse(hps.record_verdict(c).startswith('STALE'))

    def test_the_real_launch_record_moves_with_config_and_lab_common(self):
        old, new = hps.PREDECESSOR, hps.AMENDMENT_COMMIT
        d_old = hps.blob_digests(REPO, old, hps.TRACKED_PREFIXES)
        d_new = hps.blob_digests(REPO, new, hps.TRACKED_PREFIXES)
        table = {p: {'b049307': d_old.get(p), 'head': d_new.get(p)}
                 for p in set(d_old) | set(d_new)}
        tree = hps.GitTree(REPO, new)
        launch = json.loads(tree.read(
            'results/live_ab/PROSPECTIVE_LAUNCH_RECORD_20260923_2030.json'))
        c = hps.classify_pins(launch, table)
        self.assertEqual(c['moved_artifacts'], ['experiments/live_ab/config.json',
                                                'experiments/live_ab/lab_common.py'])
        smoke = json.loads(tree.read('results/live_ab/SMOKE_RECEIPT_smoke_4167e395ccfd.json'))
        self.assertEqual(hps.classify_pins(smoke, table)['moved_artifacts'], [])
        self.assertEqual(hps.sha256(tree.read('experiments/live_ab/config.json')),
                         'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7')


class FixtureTests(unittest.TestCase):

    def test_the_c_sources_are_read_from_the_committed_module(self):
        src = hps.GitTree(REPO, E2E_REV).read(hps.FIXTURE_REL)
        got = hps.fixture_sources(src)
        self.assertEqual(sorted(got['files']), ['base.c', 'core.c', 'launcher.c'])
        self.assertEqual([a[0] for a in got['compile_argv']], ['clang', 'ln', 'clang', 'clang'])
        if str(CONTROLS) not in sys.path:
            sys.path.insert(0, str(CONTROLS))
        import sm_fixture
        self.assertEqual(got['sources_key'], sm_fixture._sources_key())
        self.assertEqual(got['files']['base.c']['sha256'],
                         hps.sha256(sm_fixture.BASE_C.encode('utf-8')))
        # negative control: one changed C byte changes its digest and the cache key
        mutated = hps.fixture_sources(src.replace(b'eb1c-base-marker-0123456789";',
                                                  b'eb1c-base-marker-0123456780";'))
        self.assertNotEqual(mutated['files']['base.c']['sha256'],
                            got['files']['base.c']['sha256'])
        self.assertNotEqual(mutated['sources_key'], got['sources_key'])

    def test_a_missing_cache_rebuilds_or_fails_visibly(self):
        key = hps.fixture_sources(hps.GitTree(REPO, E2E_REV).read(hps.FIXTURE_REL))
        out = hps.fixture_missing_cache_controls(REPO, key['cache_dir_name'])
        self.assertEqual({t: out[t]['ok'] for t in hps.FIXTURE_CONTROL_TAGS},
                         {t: True for t in hps.FIXTURE_CONTROL_TAGS})
        self.assertEqual(out['B_no_compiler']['raised'], 'RuntimeError')
        self.assertEqual(out['E_real_control_no_compiler']['error_types'], ['RuntimeError'])

    def test_negative_the_judge_never_accepts_a_silent_pass(self):
        n = len(hps.FIXTURE_CONTROL_TESTS)
        good = {
            'A_rebuild': {'raised': None, 'cache_existed_before': False,
                          'cache_launcher_exists_after': True, 'otool_L_links_core': True},
            'B_no_compiler': {'raised': 'RuntimeError', 'cache_existed_before': False,
                              'cache_launcher_exists_after': False},
            'C_partial_cache': {'raised': 'FileNotFoundError'},
            'D_real_control_rebuilds': {'ran': n, 'successful': True, 'skipped': 0,
                                        'cache_launcher_exists_after': True},
            'E_real_control_no_compiler': {'ran': n, 'successful': False, 'skipped': 0,
                                           'errors': n, 'failures': 0,
                                           'cache_launcher_exists_after': False}}
        judged = hps.judge_fixture_controls(json.loads(json.dumps(good)))
        self.assertTrue(all(judged[t]['ok'] for t in hps.FIXTURE_CONTROL_TAGS))
        defects = {
            'A_rebuild': {'cache_existed_before': True},                # not a missing cache
            'B_no_compiler': {'raised': None},                          # silent without clang
            'C_partial_cache': {'raised': None},                        # partial cache accepted
            'D_real_control_rebuilds': {'skipped': n, 'successful': True},
            'E_real_control_no_compiler': {'successful': True, 'errors': 0},   # a pass
        }
        for tag, edit in defects.items():
            with self.subTest(tag=tag):
                case = json.loads(json.dumps(good))
                case[tag].update(edit)
                self.assertFalse(hps.judge_fixture_controls(case)[tag]['ok'])
        skipped = json.loads(json.dumps(good))
        skipped['E_real_control_no_compiler'].update(skipped=n, errors=0)
        self.assertFalse(hps.judge_fixture_controls(skipped)['E_real_control_no_compiler']['ok'])
        inconsistent = json.loads(json.dumps(good))       # 'successful' is read, not inferred
        inconsistent['E_real_control_no_compiler']['successful'] = True
        self.assertFalse(
            hps.judge_fixture_controls(inconsistent)['E_real_control_no_compiler']['ok'])
        partial = json.loads(json.dumps(good))
        partial['D_real_control_rebuilds']['ran'] = n - 1
        self.assertFalse(hps.judge_fixture_controls(partial)['D_real_control_rebuilds']['ok'])
        # since the subset fix a partial cache may instead be moved aside and REBUILT: ok only
        # when the rebuilt cache verifies and the partial one was really moved aside
        rebuilt = json.loads(json.dumps(good))
        rebuilt['C_partial_cache'] = {'raised': None, 'cache_verified_after': True,
                                      'moved_aside': 1}
        self.assertTrue(hps.judge_fixture_controls(rebuilt)['C_partial_cache']['ok'])
        for edit in ({'moved_aside': 0}, {'cache_verified_after': False},
                     {'cache_verified_after': None}):
            with self.subTest(rebuilt_but=edit):
                case = json.loads(json.dumps(rebuilt))
                case['C_partial_cache'].update(edit)
                self.assertFalse(hps.judge_fixture_controls(case)['C_partial_cache']['ok'])

    def test_the_uses_log_is_read_inside_the_suite_window_only(self):
        """Reviewer 2 finding 6 (review of 988baf7): the digests of the test double a suite
        executed are recorded from the lines sm_fixture logged during that suite."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / hps.FIXTURE_USES_LOG
            rows = [{'utc': '2026-09-24T10:00:00Z', 'event': 'compiled',
                     'outputs': {'llama-server': 'a' * 64}, 'clang_version': 'c1',
                     'ld_version': 'l1'},
                    {'utc': '2026-09-24T11:00:00Z', 'event': 'cache_verified',
                     'outputs': {'llama-server': 'b' * 64}, 'clang_version': 'c1',
                     'ld_version': 'l1'},
                    {'utc': '2026-09-24T13:00:00Z', 'event': 'compiled',
                     'outputs': {'llama-server': 'c' * 64}}]
            log.write_text(''.join(json.dumps(r) + '\n' for r in rows) + 'not json\n')
            got = hps.fixture_uses(log, '2026-09-24T10:30:00Z', '2026-09-24T12:00:00Z')
            self.assertEqual((got['uses'], got['events']), (1, {'cache_verified': 1}))
            self.assertEqual(got['distinct_output_sets'], [{'llama-server': 'b' * 64}])
            # negative control: a window that holds none, and a missing log
            self.assertEqual(hps.fixture_uses(log, '2026-09-25T00:00:00Z',
                                              '2026-09-25T01:00:00Z')['uses'], 0)
            self.assertEqual(hps.fixture_uses(Path(tmp) / 'absent.jsonl', '0', '9')['uses'], 0)


class SupersedesTests(unittest.TestCase):

    def test_the_superseded_receipt_is_the_committed_bytes_and_a_change_refuses(self):
        self.assertEqual([e['path'].rsplit('/', 1)[1] for e in hps.SUPERSEDES],
                         ['HARNESS_PIN_SUCCESSOR_20260924_1217.json',
                          'HARNESS_PIN_SUCCESSOR_20260924_1635.json',
                          'HARNESS_PIN_SUCCESSOR_20260924_1732.json',
                          'HARNESS_PIN_SUCCESSOR_20260925_0027.json',
                          'HARNESS_PIN_SUCCESSOR_20260925_2009.json',
                          'HARNESS_PIN_SUCCESSOR_20260926_0600.json',
                          'HARNESS_PIN_SUCCESSOR_20260926_0958.json'])
        for entry in hps.SUPERSEDES:
            with self.subTest(receipt=entry['path']):
                data = (REPO / entry['path']).read_bytes()
                rec, problems = hps.supersedes_record(entry, data)
                self.assertEqual((rec['byte_identical'], problems), (True, []))
                self.assertEqual(rec['sha256_at_head'], entry['sha256'])
                rec, problems = hps.supersedes_record(entry, data + b' ')
                self.assertEqual((rec['byte_identical'], problems),
                                 (False, ['superseded_receipt_changed:%s' % entry['path']]))
                rec, problems = hps.supersedes_record(entry, None)
                self.assertEqual((rec['present_at_head'], problems), (False, []))

    def test_the_disclosed_red_runs_name_their_result_and_disposition(self):
        self.assertGreaterEqual(len(hps.DISCLOSED_RED_RUNS), 1)
        for row in hps.DISCLOSED_RED_RUNS:
            for key in ('when', 'suite', 'result', 'disposition'):
                self.assertTrue(row.get(key), key)
        self.assertIn('FAILED (failures=2)', hps.DISCLOSED_RED_RUNS[0]['result'])
        self.assertEqual({r['kind'] for r in hps.DISCLOSED_RED_RUNS},
                         {'red_run', 'review_finding'})
        # the history root named: 79bb1ab, the 03fe0ca pre-commit C6 pair, the 1635 coin
        # failure and host, root 19:05 with its fix commit, and the v3 step
        text = json.dumps(hps.DISCLOSED_RED_RUNS)
        for fragment in ('79bb1ab', 'test_c6_mutation_the_kill_fails', 'test_coin_balance_10k',
                         '28762', 'probe1 FAILED', 'V4', 'SM8AtTheRestart'):
            self.assertIn(fragment, text)
        (finding,) = [r for r in hps.DISCLOSED_RED_RUNS if '1905' in r['when']]
        self.assertEqual((finding['kind'], finding['fix_commits']), ('review_finding',
                                                                     ['9f0aff6']))

    def test_the_history_carries_what_the_0027_receipt_omitted(self):
        """The final adversarial verification of 8f0b4ae (its finding 8): the 0027 receipt called
        its list the whole failure history but omitted root 02:54 (a blocking finding against
        8df2558), the discarded 11:41 pin run of 988baf7 (receipt f1a136fe...), that commit's
        witness-sweep survivor, and root's 22:08 reproduction attempt that failed at setUpClass.
        They are rows now, and so are that verification and the red runs of the step answering
        it, so the next receipt carries them."""
        rows = hps.DISCLOSED_RED_RUNS
        text = json.dumps(rows)
        for fragment in ('f1a136fe', '20 mutants, 19 killed', 'setUpClass', 'sparse worktree',
                         '109 mutant entries specified', 'W6, W6s, E3r, E17, E6, E12, E18, R6f, '
                         'C8', 'kill matrix 1', 'errors=28'):
            self.assertIn(fragment, text)
        (root0254,) = [r for r in rows if '0254' in r['when']]
        self.assertEqual((root0254['kind'], root0254['fix_commits']),
                         ('review_finding', ['e9bfb18']))
        (attempt,) = [r for r in rows if '2208' in r['when']]
        self.assertEqual(attempt['kind'], 'red_run')
        for row in rows:
            for key in ('when', 'suite', 'result', 'disposition'):
                self.assertTrue(row.get(key), key)

    def test_the_history_carries_the_steps_after_2113dbd(self):
        """Root 07:10: the new receipt "must include the externally recorded 22:08 root
        preflight refusal and other failed attempts"; root 10:10: "Preserve all failed runs".
        The rows of root 07:10 (finding 9 ruled (b), the 05:18 headline), the reproduction
        step (f54d215), the root 07:10 code step (bdee21b) and the amendment-v4 step (90219f2),
        each red run by its result line, and the 05:18 headline named as double-counted."""
        rows = hps.DISCLOSED_RED_RUNS
        text = json.dumps(rows)
        ruling = [r for r in rows if 'predecision_abort_reporting_ruling_20260925_0710' in
                  r['when'] or 'the same ruling' in r['when']]
        self.assertEqual([(r['kind'], r['fix_commits']) for r in ruling],
                         [('review_finding', ['bdee21b', '90219f2']), ('review_finding', [])])
        for step, fragments in (
                ('f54d215', ('R01', 'StopIteration', 'Ran 678 in 207.034s, FAILED (errors=28',
                             'failures=14, errors=2', 'Ran 442 in 3146.396s, FAILED '
                             '(failures=5', 'R17', 'R23a')),
                ('bdee21b', ('Ran 15 in 73.227s, FAILED (failures=13, errors=23)',
                             'Ran 474 in 3369.621s, FAILED (failures=2)', 'ModuleNotFoundError',
                             'Ran 2 in 52.142s, FAILED')),
                ('90219f2', ('Ran 38, FAILED (failures=3, skipped=1)', 'T9', 'V6',
                             'Ran 474 in 3382.069s, FAILED (failures=1)'))):
            with self.subTest(step=step):
                found = [r for r in rows if r['kind'] == 'red_run' and step in r['when']]
                self.assertEqual(len(found), 1, 'one red_run row of the %s step' % step)
                row = found[0]
                for fragment in fragments:
                    self.assertIn(fragment, row['result'])
        self.assertIn('OPEN, UNDIAGNOSED', text)
        (verification,) = [r for r in rows if 'final adversarial verification of 8f0b4ae, in '
                           in r['when']]
        self.assertIn('DOUBLE-COUNTED', verification['headline_as_first_reported'])
        self.assertIn('98 + 7 + 2 = 107, not 105', verification['headline_as_first_reported'])
        for row in rows:
            for key in ('when', 'suite', 'result', 'disposition'):
                self.assertTrue(row.get(key), key)

    def test_the_delta_since_the_superseded_receipt_reproduces_and_a_forged_map_refuses(self):
        head = hps.GitTree(REPO, 'HEAD')
        smap = hps.harness_map(head)
        sup = [hps.supersedes_record(e, head.read(e['path']))[0] for e in hps.SUPERSEDES]
        since, problems = hps.since_superseded(REPO, head, smap, sup)
        self.assertEqual(problems, [])
        self.assertEqual(since['receipt'], hps.SUPERSEDES[-1]['path'])
        self.assertTrue(since['superseded_map_reproduces_from_git'])
        self.assertTrue(all(r['diff_applied_to_old_gives_new']
                            for r in since['harness_entries_moved'].values()))
        target = hps.SUPERSEDES[-1]['path']

        class Forged(hps.GitTree):
            def read(self, path):
                data = super().read(path)
                if path == target:
                    obj = json.loads(data)
                    m = obj['harness_pin']['successor']['map']
                    m['lab_monitor.py'] = '0' * 64
                    data = json.dumps(obj).encode()
                return data
        forged = Forged(REPO, 'HEAD')
        since, problems = hps.since_superseded(REPO, forged, smap, sup)
        # the forged map also claims lab_monitor.py moved, which no git diff reproduces
        self.assertEqual(problems, ['superseded_map_does_not_reproduce',
                                    'since_superseded_diff_does_not_reproduce'])
        self.assertFalse(since['superseded_map_reproduces_from_git'])
        self.assertFalse(since['harness_entries_moved']['lab_monitor.py'][
            'diff_applied_to_old_gives_new'])
        none, problems = hps.since_superseded(REPO, head, smap, [])
        self.assertEqual((none['receipt'], problems), (None, []))


class SupersededReceiptsGuardTests(unittest.TestCase):
    """The ``superseded_receipts_incomplete`` guard (root 01:17 replay-resume interim repair
    item: a run at c5817f9 wrote a receipt whose hard-coded SUPERSEDES ended at ..._0027, so it
    never named the already-accepted ..._2009 receipt of the 98ce004 harness and measured
    ``since_the_superseded_receipt`` against 0027 instead of 2009)."""

    def test_positive_the_guard_passes_at_head_with_every_committed_receipt_named(self):
        head = hps.GitTree(REPO, 'HEAD')
        self.assertEqual(hps.superseded_receipts_incomplete(head, hps.SUPERSEDES), [])
        # the 0600 receipt (drivers steps 1-3, ced7a13) is the reason this step named it: with
        # it missing the guard is not vacuously green, it actually refuses (root 07:18)
        self.assertEqual(len(hps.SUPERSEDES), 7)
        self.assertEqual(hps.SUPERSEDES[-2]['path'],
                         'results/live_ab/HARNESS_PIN_SUCCESSOR_20260926_0600.json')
        # the 0958 receipt (step 4, b229060; root 10:19) is the reason the next step named it
        self.assertEqual(hps.SUPERSEDES[-1]['path'],
                         'results/live_ab/HARNESS_PIN_SUCCESSOR_20260926_0958.json')

    def test_negative_removing_the_2009_entry_by_monkeypatch_refuses_and_names_it(self):
        without_2009 = tuple(e for e in hps.SUPERSEDES
                             if not e['path'].endswith('HARNESS_PIN_SUCCESSOR_20260925_2009.'
                                                       'json'))
        self.assertEqual(len(without_2009), len(hps.SUPERSEDES) - 1)
        with mock.patch.object(hps, 'SUPERSEDES', without_2009):
            head = hps.GitTree(REPO, 'HEAD')
            problems = hps.superseded_receipts_incomplete(head, hps.SUPERSEDES)
        self.assertEqual(problems,
                         ['superseded_receipts_incomplete:results/live_ab/'
                          'HARNESS_PIN_SUCCESSOR_20260925_2009.json'])

    def test_negative_removing_the_0600_entry_by_monkeypatch_refuses_and_names_it(self):
        """The entry this step adds: without it, the guard refuses exactly as root 07:18
        found (a run at c4c1db9's successor without this entry refuses on the next receipt)."""
        without_0600 = tuple(e for e in hps.SUPERSEDES
                             if not e['path'].endswith('HARNESS_PIN_SUCCESSOR_20260926_0600.'
                                                       'json'))
        self.assertEqual(len(without_0600), len(hps.SUPERSEDES) - 1)
        with mock.patch.object(hps, 'SUPERSEDES', without_0600):
            head = hps.GitTree(REPO, 'HEAD')
            problems = hps.superseded_receipts_incomplete(head, hps.SUPERSEDES)
        self.assertEqual(problems,
                         ['superseded_receipts_incomplete:results/live_ab/'
                          'HARNESS_PIN_SUCCESSOR_20260926_0600.json'])

    def test_negative_removing_the_0958_entry_by_monkeypatch_refuses_and_names_it(self):
        """The entry the stage-1 repair step adds: without it, the guard refuses the next
        receipt, exactly as observed before this entry was added (root 10:19)."""
        without_0958 = tuple(e for e in hps.SUPERSEDES
                             if not e['path'].endswith('HARNESS_PIN_SUCCESSOR_20260926_0958.'
                                                       'json'))
        self.assertEqual(len(without_0958), len(hps.SUPERSEDES) - 1)
        with mock.patch.object(hps, 'SUPERSEDES', without_0958):
            head = hps.GitTree(REPO, 'HEAD')
            problems = hps.superseded_receipts_incomplete(head, hps.SUPERSEDES)
        self.assertEqual(problems,
                         ['superseded_receipts_incomplete:results/live_ab/'
                          'HARNESS_PIN_SUCCESSOR_20260926_0958.json'])

    def test_since_the_superseded_receipt_selects_2009_at_98ce004_when_0600_is_not_yet_listed(
            self):
        """Coverage kept from before this step (without weakening it): restricted to the
        entries this repository named before 0600 was pinned, selection still lands on 2009 at
        98ce004."""
        through_2009 = tuple(e for e in hps.SUPERSEDES
                             if not e['path'].endswith(('HARNESS_PIN_SUCCESSOR_20260926_0600.'
                                                        'json',
                                                        'HARNESS_PIN_SUCCESSOR_20260926_0958.'
                                                        'json')))
        self.assertEqual(len(through_2009), len(hps.SUPERSEDES) - 2)
        head = hps.GitTree(REPO, 'HEAD')
        smap = hps.harness_map(head)
        sup = [hps.supersedes_record(e, head.read(e['path']))[0] for e in through_2009]
        since, problems = hps.since_superseded(REPO, head, smap, sup)
        self.assertEqual(problems, [])
        self.assertEqual(since['receipt'],
                         'results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json')
        self.assertEqual(since['recorded_head'][:7], '98ce004')

    def test_since_the_superseded_receipt_selects_0600_at_ced7a13(self):
        """Coverage kept (not weakened): restricted to the entries named before 0958, the latest
        superseded receipt is 0600 and its recorded head is ced7a13 (root 07:18's accepted pin)."""
        head = hps.GitTree(REPO, 'HEAD')
        smap = hps.harness_map(head)
        through_0600 = tuple(e for e in hps.SUPERSEDES
                             if not e['path'].endswith('HARNESS_PIN_SUCCESSOR_20260926_0958.'
                                                       'json'))
        self.assertEqual(len(through_0600), len(hps.SUPERSEDES) - 1)
        sup = [hps.supersedes_record(e, head.read(e['path']))[0] for e in through_0600]
        since, problems = hps.since_superseded(REPO, head, smap, sup)
        self.assertEqual(problems, [])
        self.assertEqual(since['receipt'],
                         'results/live_ab/HARNESS_PIN_SUCCESSOR_20260926_0600.json')
        self.assertEqual(since['recorded_head'][:7], 'ced7a13')

    def test_since_the_superseded_receipt_selects_0958_at_b229060(self):
        """With 0958 named, it (not 0600) is the latest superseded receipt HEAD carries, and its
        recorded head is b229060 (the receipt root 10:19 accepted as a run receipt only)."""
        head = hps.GitTree(REPO, 'HEAD')
        smap = hps.harness_map(head)
        sup = [hps.supersedes_record(e, head.read(e['path']))[0] for e in hps.SUPERSEDES]
        since, problems = hps.since_superseded(REPO, head, smap, sup)
        self.assertEqual(problems, [])
        self.assertEqual(since['receipt'],
                         'results/live_ab/HARNESS_PIN_SUCCESSOR_20260926_0958.json')
        self.assertEqual(since['recorded_head'][:7], 'b229060')


def partition_from_logs(logs: Path) -> dict:
    """The partition recomputed from the verifier's own files under ``logs`` (spec3.json, the
    three result streams, the per-mutant logs under logs/logs): each entry's recorded verdict;
    a kill whose own log shows the real host gate refusing the run is host-gate only unless the
    solo rerun of the same edit (``<id>r``) was killed; equivalence and guards are the
    constant's judgement (the logs record verdicts, not equivalence)."""
    streams = {'mut_run1.out': 'mut_%s.log', 'mut_results2.jsonl': 'mut2_%s.log',
               'mut_run3.out': 'mut_%s.log'}
    spec = [s['id'] for s in json.loads((logs / 'spec3.json').read_text('utf-8'))]
    rows = {}
    for name, pattern in streams.items():
        for line in (logs / name).read_text('utf-8').splitlines():
            if line.startswith('{'):
                row = json.loads(line)
                row['_log'] = pattern % row['id']
                rows[row['id']] = row
    host, right, survived = {}, [], []
    for i in spec:
        row = rows.get(i)
        if row is None:
            continue
        if row['verdict'] == 'SURVIVED':
            survived.append(i)
            continue
        log = logs / 'logs' / row['_log']
        text = log.read_text('utf-8') if log.is_file() else ''
        rerun = rows.get(i + 'r')
        if ('host gate' in text or 'host_not_quiescent' in text) and not (
                rerun and rerun['verdict'] == 'KILLED'):
            host[i] = hps.sha256(log.read_bytes())
        else:
            right.append(i)
    eq = hps.MUTATION_PARTITION_8F0B4AE['equivalent']
    return {'logs': {n: hps.sha256((logs / n).read_bytes())
                     for n in ('spec3.json',) + tuple(streams)},
            'specified': spec, 'not_run': sorted(i for i in spec if i not in rows),
            'killed_by_the_right_control': right,
            'killed_only_by_the_host_gate': host,
            'survived_equivalent': [i for i in survived if i in eq],
            'survived_non_equivalent': sorted(i for i in survived if i not in eq)}


class PartitionTests(unittest.TestCase):
    """Root 07:10: the 05:18 mutation headline "double-counts two"; the receipt carries a
    mutually exclusive partition reconciled from the verifier's logs."""
    P = hps.MUTATION_PARTITION_8F0B4AE

    def edited(self, **changes) -> dict:
        p = json.loads(json.dumps(self.P))
        p.update(changes)
        return p

    def test_the_constant_is_an_exclusive_exhaustive_partition(self):
        self.assertEqual(hps.partition_problems(self.P), [])
        c = self.P['counts']
        self.assertEqual((c['specified'], c['run'], c['killed'], c['survived']),
                         (109, 108, 98, 10))
        self.assertEqual(c['killed_by_the_right_control'] + c['killed_only_by_the_host_gate'],
                         c['killed'])
        self.assertEqual(c['survived_equivalent'] + c['survived_non_equivalent'], c['survived'])
        self.assertEqual((sorted(self.P['killed_only_by_the_host_gate']),
                          sorted(self.P['equivalent']), list(self.P['not_run'])),
                         (['E3', 'R8g'], ['R8g', 'S10'], ['E6c']))
        self.assertEqual(len(set(self.P['survived_non_equivalent'].values())), 7)
        # the seven guards are the seven classes 2113dbd added
        src = (REPO / 'experiments/live_ab_controls/tests_guard_controls.py').read_text('utf-8')
        for cls in self.P['guards_controlled_by_2113dbd'].values():
            self.assertIn('class %s(' % cls, src)

    def test_negative_the_0518_headline_and_each_broken_partition_refuse(self):
        h = self.P['headline_0518']
        self.assertFalse(hps.headline_is_a_partition(h['total'], h['killed'],
                                                     h['non_equivalent'], h['equivalent']))
        self.assertTrue(hps.headline_is_a_partition(108, 96, 2, 1, 9))
        headline_counts = dict(self.P['counts'], specified=105, killed=98,
                               survived_non_equivalent=7)
        right = list(self.P['killed_by_the_right_control'])
        cases = {
            'the 05:18 counts': (self.edited(counts=headline_counts),
                                 ['mutation_partition:count:specified',
                                  'mutation_partition:count:survived_non_equivalent']),
            'E3 also a right-control kill': (
                self.edited(killed_by_the_right_control=right + ['E3']),
                ['mutation_partition:classes_overlap',
                 'mutation_partition:count:killed',
                 'mutation_partition:count:killed_by_the_right_control']),
            'E6c run but in no class': (
                self.edited(not_run={}),
                ['mutation_partition:classes_not_the_run', 'mutation_partition:count:not_run',
                 'mutation_partition:count:run']),
            'R8g not equivalent': (
                self.edited(equivalent={'S10': 'x'}),
                ['mutation_partition:count:equivalent']),
            'an equivalent among the right-control kills': (
                self.edited(equivalent=dict(self.P['equivalent'], S1='x')),
                ['mutation_partition:equivalents', 'mutation_partition:count:equivalent']),
            'a guard without its control': (
                self.edited(guards_controlled_by_2113dbd={
                    k: v for k, v in self.P['guards_controlled_by_2113dbd'].items()
                    if k != 'look_guard'}),
                ['mutation_partition:guards']),
            'S6 rerun-counted but not a right-control kill': (
                self.edited(killed_by_the_right_control=[i for i in right if i != 'S6'],
                            not_run=dict(self.P['not_run'], S6='x'),
                            counts=dict(self.P['counts'], killed=97, run=107, not_run=2,
                                        killed_by_the_right_control=95)),
                ['mutation_partition:rerun_counted_outside_the_right_control'])}
        for label, (p, expected) in cases.items():
            with self.subTest(case=label):
                self.assertEqual(hps.partition_problems(p), expected)

    @unittest.skipUnless(os.environ.get('MUTATION_LOGS_8F0B4AE'),
                         'MUTATION_LOGS_8F0B4AE (the verifier\'s log directory, kept by the '
                         'owner session, not tracked) is not set')
    def test_the_constant_is_the_partition_of_the_verifier_logs(self):
        logs = Path(os.environ['MUTATION_LOGS_8F0B4AE'])
        got = partition_from_logs(logs)
        self.assertEqual(got['logs'], self.P['logs'])
        self.assertEqual(got['specified'], self.P['specified'])
        self.assertEqual(got['not_run'], sorted(self.P['not_run']))
        self.assertEqual(got['killed_by_the_right_control'],
                         self.P['killed_by_the_right_control'])
        self.assertEqual(got['killed_only_by_the_host_gate'],
                         {i: r['log_sha256'] for i, r in
                          self.P['killed_only_by_the_host_gate'].items()})
        self.assertEqual(got['survived_equivalent'], self.P['survived_equivalent'])
        self.assertEqual(got['survived_non_equivalent'],
                         sorted(self.P['survived_non_equivalent']))
        # negative control: the same reading of a copy whose E3r row says KILLED does not
        # reproduce the constant (E3 then counts as a right-control kill, E3r leaves the
        # survivors)
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'logs'
            shutil.copytree(str(logs), str(copy), ignore=shutil.ignore_patterns(
                'clone', 'clone2', 'ro', 'r6f'))
            run3 = copy / 'mut_run3.out'
            run3.write_text(run3.read_text('utf-8').replace(
                '{"id": "E3r", "verdict": "SURVIVED"', '{"id": "E3r", "verdict": "KILLED"'),
                'utf-8')
            flipped = partition_from_logs(copy)
            self.assertNotEqual(flipped['logs'], self.P['logs'])
            self.assertIn('E3', flipped['killed_by_the_right_control'])
            self.assertNotIn('E3r', flipped['survived_non_equivalent'])


class RunsOfThisStepTests(unittest.TestCase):

    def test_rows_are_kept_and_every_malformed_file_refuses(self):
        tok = hps.make_tokenizer(REPO)
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / 'good.json'
            rows = [{'id': 'r1', 'utc': '2026-09-24T23:00:00Z', 'command': 'python -m x',
                     'result': 'Ran 1 test, FAILED (failures=1)', 'note': str(REPO)}]
            good.write_text(json.dumps(rows))
            sec, problems = hps.load_runs_of_this_step(good, tok)
            self.assertEqual(problems, [])
            self.assertEqual(sec['rows'][0]['result'], 'Ran 1 test, FAILED (failures=1)')
            self.assertEqual(sec['rows'][0]['note'], '<REPO>')
            self.assertEqual(sec['source_sha256'], hps.sha256(good.read_bytes()))
            self.assertEqual(hps.load_runs_of_this_step(None, tok),
                             ('not given in this invocation', []))
            bad = {'missing': None, 'unparsable': b'[{', 'empty': b'[]',
                   'not_a_list': json.dumps(rows[0]).encode(),
                   'no_result': json.dumps([dict(rows[0], result='')]).encode(),
                   'no_utc': json.dumps([{k: v for k, v in rows[0].items()
                                          if k != 'utc'}]).encode()}
            for name, data in bad.items():
                with self.subTest(case=name):
                    path = Path(tmp) / (name + '.json')
                    if data is not None:
                        path.write_bytes(data)
                    self.assertEqual(hps.load_runs_of_this_step(path, tok),
                                     (None, ['runs_of_this_step_malformed']))


class SuiteParseTests(unittest.TestCase):
    OK = 'test_a (m.C.test_a) ... ok\n\n' + '-' * 70 + '\nRan 5 tests in 0.100s\n\nOK (skipped=1)\n'

    def test_a_complete_ok_run_passes(self):
        r = hps.parse_suite_output(self.OK, 0, 5)
        self.assertTrue(r['passed'])
        self.assertEqual((r['ran'], r['verdict_line'], r['verdict_counts']),
                         (5, 'OK (skipped=1)', {'skipped': 1}))

    def test_negative_every_incomplete_or_failed_run_is_not_a_pass(self):
        cases = {
            'no Ran line': ('OK\n', 0, 5, ''),
            'fewer than planned': (self.OK, 0, 6, ''),
            'planned unknown': (self.OK, 0, None, ''),
            'FAILED verdict': (self.OK.replace('OK (skipped=1)', 'FAILED (failures=1)'), 1, 5,
                               ''),
            'nonzero exit': (self.OK, 1, 5, ''),
            'verdict only on stdout': ('', 0, 5, self.OK),
        }
        for label, (err, rc, planned, out) in cases.items():
            with self.subTest(label=label):
                self.assertFalse(hps.parse_suite_output(err, rc, planned, out)['passed'])

    def test_failure_headers_skip_reasons_and_the_script_line_are_read(self):
        err = ("test_x (mod.K.test_x)\nA docstring line ... skipped 'no lsof'\n"
               + "test_y (mod.K.test_y) ... skipped 'other'\n" + '=' * 70
               + '\nFAIL: test_z (mod.K.test_z)\n' + '-' * 70
               + '\nRan 3 tests in 0.1s\n\nFAILED (failures=1, skipped=2)\n')
        r = hps.parse_suite_output(err, 1, 3, 'ran=3 failures=1 errors=0 skipped=2\n')
        self.assertEqual(r['failure_headers'], ['FAIL: test_z (mod.K.test_z)'])
        self.assertEqual(r['skips'], [{'test': 'mod.K.test_x', 'reason': "'no lsof'"},
                                      {'test': 'mod.K.test_y', 'reason': "'other'"}])
        self.assertEqual(r['script_summary_line'], 'ran=3 failures=1 errors=0 skipped=2')
        self.assertEqual(r['verdict_counts'], {'failures': 1, 'skipped': 2})


class ProcessAttributionTests(unittest.TestCase):
    """The solo evidence: a watched process outside the suite's tree is ``foreign`` unless it
    is an orphan (parent launchd) that started during the suite."""

    def test_rows_are_attributed(self):
        now = 1_000_000.0
        rows = [(10, 1, now - 100, 'python -m unittest discover'),       # before the suite
                (11, 1, now + 5, '/t/eb1c_C10/host/bin/llama-server.py -m x'),   # orphan
                (12, 50, now + 5, 'llama-server --port 1'),              # live foreign parent
                (13, 99, now, 'python -m unittest x'),                   # in the suite tree
                (14, 1, now + 5, 'bash -c true'),                        # not watched
                (15, 1, now + 5, 'ps -axo pid=,ppid=,lstart=,command= unittest')]
        got = hps.watched_outside(rows, {13, 99}, str, since=now)
        self.assertEqual([(r['pid'], r['attribution']) for r in got],
                         [(10, 'foreign'), (11, 'orphan_started_during_the_suite'),
                          (12, 'foreign')])
        self.assertEqual([r['attribution'] for r in hps.watched_outside(rows[1:2], set(), str)],
                         ['foreign'], 'without a suite start nothing is an orphan of it')
        self.assertEqual(hps.tree_of([(2, 1, 0, 'a'), (3, 2, 0, 'b'), (4, 9, 0, 'c')], [2]),
                         {2, 3})
        self.assertEqual(hps.ancestors_of([(2, 1, 0, 'a'), (3, 2, 0, 'b')], 3), {3, 2, 1})

    def test_negative_one_foreign_row_makes_the_run_not_solo(self):
        def run(before=(), during=(), after=()):
            return {'host_before': {'watched_processes_outside_the_suite': list(before)},
                    'sampler': {'watched_outside_the_tree': list(during)},
                    'host_after': {'watched_processes_outside_the_suite': list(after)}}
        orphan = {'attribution': 'orphan_started_during_the_suite', 'command_head': 'x'}
        foreign = {'attribution': 'foreign', 'command_head': 'y'}
        self.assertEqual(hps.solo_verdict([run(), run(during=[orphan])])['solo'], True)
        self.assertEqual(hps.solo_verdict([run(), run(during=[orphan])])['solo_strict'], False)
        for where in ('before', 'during', 'after'):
            with self.subTest(where=where):
                self.assertFalse(hps.solo_verdict([run(**{where: [foreign]})])['solo'])

    def test_a_live_sampler_keeps_its_own_orphan_and_flags_a_foreign_process(self):
        # the child lives 1 s after starting its grandchild (so a sample sees the grandchild
        # in the tree, and ``known`` must keep it after the child exits and it is orphaned)
        orphan_maker = ("import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', "
                        "'import time; time.sleep(3.5)  # tests_pinsucc_orphan'], "
                        "start_new_session=True); time.sleep(1.0)")
        foreign = subprocess.Popen([sys.executable, '-c',
                                    'import time; time.sleep(4)  # tests_pinsucc_foreign'])
        try:
            with mock.patch.object(hps, 'SAMPLE_EVERY_S', 0.2):
                child = subprocess.Popen([sys.executable, '-c', orphan_maker])
                sampler = hps.Sampler(child.pid, str, hps.time.time() - 1)
                sampler.start()
                child.wait(timeout=30)
                hps.time.sleep(1.5)
                sampler.stop_event.set()
                sampler.join()
            rows = list(sampler.seen.values())
            marks = {('tests_pinsucc_orphan' in r['command_head'],
                      'tests_pinsucc_foreign' in r['command_head']): r['attribution']
                     for r in rows}
            self.assertEqual(marks.get((False, True)), 'foreign')
            self.assertNotIn((True, False), marks, 'seen in the tree, so never outside it')
            self.assertGreater(sampler.samples, 3)
        finally:
            foreign.kill()
            foreign.wait()


class WriteOnceTests(unittest.TestCase):

    def test_a_second_write_refuses_and_the_first_bytes_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'r.json'
            digest = hps.write_once(path, {'a': 1})
            self.assertEqual(hps.sha256(path.read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                hps.write_once(path, {'a': 2})
            self.assertEqual(json.loads(path.read_text()), {'a': 1})


class PinLogTests(unittest.TestCase):
    """``write_pin_log`` / ``verify_pin_log``: the write-once retention of a suite's full
    stdout or stderr next to the receipt (root: RED_PIN_RUN_20260926_1227.json could not be
    diagnosed because only the tail and a digest were kept and the traceback was discarded)."""

    def test_the_gzip_member_is_deterministic(self):
        raw = b'the same content, twice' * 5
        with tempfile.TemporaryDirectory() as tmp:
            a = hps.write_pin_log(Path(tmp) / 'a.gz', raw)
            b = hps.write_pin_log(Path(tmp) / 'b.gz', raw)
            self.assertEqual(a, b, 'mtime 0 makes the compressed bytes identical run to run')
            self.assertEqual((Path(tmp) / 'a.gz').read_bytes(), (Path(tmp) / 'b.gz').read_bytes())
            self.assertEqual(gzip.decompress((Path(tmp) / 'a.gz').read_bytes()), raw)

    def test_an_identical_rewrite_is_a_no_op_and_different_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.stderr.gz'
            first = hps.write_pin_log(path, b'the original bytes')
            on_disk = path.read_bytes()
            again = hps.write_pin_log(path, b'the original bytes')
            self.assertEqual((first, again), (hps.sha256(on_disk), hps.sha256(on_disk)))
            self.assertEqual(path.read_bytes(), on_disk, 'a matching rewrite changes nothing')
            with self.assertRaises(hps.Refused) as cm:
                hps.write_pin_log(path, b'different bytes entirely')
            self.assertEqual(cm.exception.problems, ['pin_log_mismatch:x.stderr.gz'])
            self.assertEqual(path.read_bytes(), on_disk, 'a refused rewrite leaves the file')

    def test_negative_a_missing_log_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(hps.Refused) as cm:
                hps.verify_pin_log(Path(tmp) / 'never_written.stdout.gz', 'a' * 64)
            self.assertEqual(cm.exception.problems, ['pin_log_missing:never_written.stdout.gz'])

    def test_negative_a_digest_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.stdout.gz'
            hps.write_pin_log(path, b'the real recorded bytes')
            with self.assertRaises(hps.Refused) as cm:
                hps.verify_pin_log(path, 'f' * 64)
            self.assertEqual(cm.exception.problems, ['pin_log_digest_mismatch:x.stdout.gz'])
            # a file that is not even gzip is the same refusal, not a bare exception
            path.write_bytes(b'not gzip at all')
            with self.assertRaises(hps.Refused) as cm2:
                hps.verify_pin_log(path, hps.sha256(b'not gzip at all'))
            self.assertEqual(cm2.exception.problems, ['pin_log_digest_mismatch:x.stdout.gz'])

    def test_retain_pin_log_matches_the_already_computed_digest_and_tokenizes_its_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'live_ab.stderr.gz'
            raw = b'traceback goes here\nAssertionError: boom\n'
            record = hps.retain_pin_log(path, raw, hps.sha256(raw), str)
            self.assertEqual(record['uncompressed_sha256'], hps.sha256(raw))
            self.assertEqual(record['uncompressed_bytes'], len(raw))
            self.assertEqual(record['compressed_sha256'], hps.sha256(path.read_bytes()))
            self.assertEqual(record['compressed_bytes'], len(path.read_bytes()))
            self.assertEqual(record['path'], str(path), 'tokenize() is applied to the path')

    def test_negative_retain_pin_log_refuses_on_a_wrong_expected_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'live_ab.stdout.gz'
            with self.assertRaises(hps.Refused) as cm:
                hps.retain_pin_log(path, b'abc', '0' * 64, str)
            self.assertEqual(cm.exception.problems, ['pin_log_digest_mismatch:live_ab.stdout.gz'])

    def test_negative_a_fresh_writes_readback_divergence_refuses_on_its_own(self):
        """``write_pin_log`` re-reads the file it just wrote and compares it to the bytes it
        meant to write, BEFORE ``verify_pin_log`` ever runs (a fail-before/pass-after control
        for that specific check, independent of ``retain_pin_log``'s later re-verification: this
        intercepts only ``write_pin_log``'s own post-write read, so a real, separate read of the
        file afterwards -- unmocked -- shows the bytes on disk were correct all along)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a_suite.stdout.gz'
            raw = b'the bytes actually meant for disk'
            compressed = hps.gzip.compress(raw, compresslevel=9, mtime=0)
            real_read_bytes = hps.Path.read_bytes

            def lying_read_bytes(self_path, *a, **kw):
                data = real_read_bytes(self_path, *a, **kw)
                return data + b'\x00' if self_path == path else data

            with mock.patch.object(hps.Path, 'read_bytes', new=lying_read_bytes):
                with self.assertRaises(hps.Refused) as cm:
                    hps.write_pin_log(path, raw)
            self.assertEqual(cm.exception.problems, ['pin_log_mismatch:a_suite.stdout.gz'])
            # the write itself succeeded; only the post-write readback check (not yet reached
            # by verify_pin_log, which is a separate function) is what must have refused here
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), compressed, "the on-disk bytes were fine -- "
                             "only this test's patched read lied to write_pin_log's own check")


class EndToEndTests(_Clone):
    """The tool on a sparse clone at E2E_REV (a clean tree whose HEAD is fixed)."""

    def test_the_receipt_of_the_fixed_revision(self):
        r = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        hp = r['harness_pin']
        self.assertEqual((hp['counts']['before'], hp['counts']['after']), (33, 34))
        self.assertEqual(hp['predecessor']['canonical_sha256'], hps.PREDECESSOR_CANONICAL)
        self.assertEqual(hp['successor']['canonical_sha256'], E2E_CANONICAL)
        self.assertEqual(hp['counts']['added'], ['lab_serving_manifest.py'])
        self.assertEqual(hp['counts']['modified'], 16)
        self.assertTrue(all(c['diff_applied_to_old_gives_new'] for c in hp['changed'].values()))
        self.assertTrue(r['rule_block']['unchanged'])
        self.assertTrue(r['reused_files']['unchanged'])
        self.assertEqual({k: v['head'][:8] for k, v in r['documents'].items()},
                         {'config.json': 'f158969e', 'ARCHITECTURE_FINAL.md': 'e7ea9c0f',
                          'protocol_FINAL.md': '6c0ebf2f', 'cells.json': '6b31bf20'})
        self.assertEqual(r['serving_manifest']['head']['canonical_sha256'][:8], '1edea9b0')
        am = r['amendments']
        self.assertTrue(am['head_equals_the_latest_written_values'])
        self.assertTrue(all(am['head_equals_the_latest_written_values'].values()))
        self.assertEqual(set(am['latest_writer'].values()), {'v2'})
        self.assertEqual([(c['name'], c['present_at_head']) for c in am['chain']],
                         [('v2', True), ('v3', False), ('v4', False)])
        self.assertEqual(r['since_the_superseded_receipt']['receipt'], None)
        self.assertEqual(r['runs_of_this_step_before_this_receipt'],
                         'not given in this invocation')
        self.assertEqual(r['server_supervision']['landed_in_commits'], [hps.AMENDMENT_COMMIT])
        self.assertEqual(len(r['prior_observations_not_reissued']['records']), 7)
        self.assertEqual(r['solo_run_suites'], 'not run in this invocation (--no-suites)')
        self.assertEqual(r['status'], hps.STATUS)
        self.assertEqual(r['convention'], 'deterministic-path')

    def test_main_writes_one_receipt_outside_results(self):
        with tempfile.TemporaryDirectory() as out:
            with redirect_stdout(io.StringIO()):
                rc = hps.main(['--repo', str(self.clone), '--no-suites', '--out-dir', out])
            self.assertEqual(rc, 0)
            (name,) = os.listdir(out)
            self.assertRegex(name, r'^HARNESS_PIN_SUCCESSOR_\d{8}_\d{4}\.json$')

    def test_negative_a_malformed_runs_file_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / 'runs.json'
            runs.write_text('[{"id": "r1"}]')
            with redirect_stderr(io.StringIO()) as err:
                rc = hps.main(['--repo', str(self.clone), '--no-suites', '--out-dir', out,
                               '--runs-of-this-step', str(runs)])
            self.assertEqual(rc, 2)
            self.assertIn('runs_of_this_step_malformed', err.getvalue())
            self.assertEqual(os.listdir(out), [])

    def test_negative_no_suites_into_results_refuses(self):
        results = self.clone / 'results' / 'live_ab'
        before = sorted(os.listdir(results))
        with redirect_stderr(io.StringIO()) as err:
            self.assertEqual(hps.main(['--repo', str(self.clone), '--no-suites']), 2)
        self.assertIn('no_suites_into_results', err.getvalue())
        self.assertEqual(sorted(os.listdir(results)), before)

    def test_negative_a_dirty_tree_refuses_own_files_do_not(self):
        self.assertEqual(hps.worktree_state(self.clone), ([], []))
        own = self.clone / hps.OWN_FILES[1]
        stray = self.clone / 'experiments' / 'live_ab' / 'stray.py'
        try:
            own.write_text('# untracked copy\n')
            entries, problems = hps.worktree_state(self.clone)
            self.assertEqual((len(entries), problems), (1, []))
            stray.write_text('x = 1\n')
            with self.assertRaises(hps.Refused) as cm:
                hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
            self.assertIn('working_tree_dirty:experiments/live_ab/stray.py',
                          cm.exception.problems)
        finally:
            own.unlink(missing_ok=True)
            stray.unlink(missing_ok=True)

    def test_negative_a_committed_mutated_predecessor_refuses(self):
        mutant = mutated_predecessor(self.clone, 'experiments/live_ab/lab_monitor.py')
        with self.assertRaises(hps.Refused) as cm:
            hps.build_receipt(self.clone, mutant, run_suites=False)
        self.assertIn('predecessor_digest', cm.exception.problems)
        self.assertIn('decision_module_changed', cm.exception.problems)


class EndToEndV3Tests(_Clone):
    """The tool on a sparse clone at AMENDMENT_V3_COMMIT (56df17f), and mutant commits on it."""
    REV = hps.AMENDMENT_V3_COMMIT
    PROTOCOL = 'experiments/live_ab/design/protocol_FINAL.md'

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_test_')))
        cls.clone = make_clone(cls.tmp / 'clone', cls.REV)

    def at(self, rev: str) -> None:
        git('checkout', '-q', '--detach', rev, cwd=self.clone)
        self.addCleanup(git, 'checkout', '-q', '--detach', self.REV, cwd=self.clone)

    def refused(self, rev: str) -> list:
        self.at(rev)
        with self.assertRaises(hps.Refused) as cm:
            hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        return cm.exception.problems

    def v3_receipt(self) -> dict:
        return json.loads(git('show', '%s:%s' % (self.REV, hps.AMENDMENT_V3_RECEIPT_REL),
                              cwd=self.clone))

    def test_the_receipt_at_amendment_v3(self):
        r = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        self.assertEqual({k: v['head'][:8] for k, v in r['documents'].items()},
                         {'config.json': 'f158969e', 'ARCHITECTURE_FINAL.md': '2ec71980',
                          'protocol_FINAL.md': '73dd0573', 'cells.json': '192804a4'})
        am = r['amendments']
        self.assertEqual([(c['name'], c['present_at_head'], c.get('added_in_commits'))
                          for c in am['chain']],
                         [('v2', True, [hps.AMENDMENT_COMMIT]),
                          ('v3', True, [hps.AMENDMENT_V3_COMMIT]), ('v4', False, None)])
        self.assertTrue(all(am['head_equals_the_latest_written_values'].values()))
        self.assertEqual(am['latest_writer']['protocol_FINAL.md'], 'v3')
        self.assertEqual(am['latest_writer']['serving_manifest_canonical'], 'v2')
        self.assertTrue(all(am['chain'][1]['names_its_predecessor'][k] for k in (
            'equals_the_predecessor_receipt_at_head', 'equals_the_predecessor_commit',
            'equal_the_predecessor_written_values')))
        hist = am['document_pin_history']['protocol_FINAL.md']['pins']
        self.assertEqual([(p['at'][:2], p['sha256'][:8]) for p in hist],
                         [('b0', '64ace6d3'), ('v2', '6c0ebf2f'), ('v3', '73dd0573'),
                          ('he', '73dd0573')])
        self.assertFalse(am['document_pin_history']['config.json']['pins'][2][
            'moved_from_the_previous_step'])
        since = r['since_the_superseded_receipt']
        # the 0027 receipt is not in 56df17f: the latest superseded receipt there is 1732
        self.assertEqual(since['receipt'], hps.SUPERSEDES[2]['path'])
        self.assertTrue(since['superseded_map_reproduces_from_git'])
        self.assertEqual(sorted(since['documents_moved']),
                         ['ARCHITECTURE_FINAL.md', 'cells.json', 'protocol_FINAL.md'])
        self.assertIn('lab_eventlog.py', since['harness_entries_moved'])
        self.assertTrue(r['cells_vocabulary_successor']['holds'])

    def test_negative_a_document_changed_after_v3_refuses(self):
        data = bytearray(git('show', '%s:%s' % (self.REV, self.PROTOCOL), cwd=self.clone))
        data[100] ^= 0x01
        problems = self.refused(commit_with(self.clone, self.REV, {self.PROTOCOL: bytes(data)}))
        self.assertIn('amendment_receipt_disagrees', problems)

    def test_negative_a_v3_receipt_that_is_not_the_blob_at_its_commit_refuses(self):
        rec = self.v3_receipt()
        rec['written']['protocol_sha256'] = '0' * 64
        problems = self.refused(commit_with(self.clone, self.REV, {
            hps.AMENDMENT_V3_RECEIPT_REL: json.dumps(rec).encode()}))
        self.assertIn('amendment_chain:v3', problems)
        self.assertIn('amendment_receipt_disagrees', problems)

    def test_negative_a_v3_receipt_copied_in_without_its_commit_refuses(self):
        data = git('show', '%s:%s' % (self.REV, hps.AMENDMENT_V3_RECEIPT_REL), cwd=self.clone)
        problems = self.refused(commit_with(self.clone, E2E_REV,
                                            {hps.AMENDMENT_V3_RECEIPT_REL: data}))
        self.assertIn('amendment_chain:v3', problems)
        self.assertIn('amendment_receipt_disagrees', problems)

    def test_negative_a_v3_receipt_naming_another_v2_receipt_refuses(self):
        rec = self.v3_receipt()
        rec['predecessor_amendment_v2']['receipt_sha256'] = 'f' * 64
        problems = self.refused(commit_with(self.clone, self.REV, {
            hps.AMENDMENT_V3_RECEIPT_REL: json.dumps(rec).encode()}))
        self.assertEqual(problems, ['amendment_chain_link:v3'])


class EndToEndV4Tests(_Clone):
    """The tool on a sparse clone at AMENDMENT_V4_COMMIT (90219f2), and mutant commits on it."""
    REV = hps.AMENDMENT_V4_COMMIT

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_test_')))
        cls.clone = make_clone(cls.tmp / 'clone', cls.REV)

    def refused(self, rev: str) -> list:
        git('checkout', '-q', '--detach', rev, cwd=self.clone)
        self.addCleanup(git, 'checkout', '-q', '--detach', self.REV, cwd=self.clone)
        with self.assertRaises(hps.Refused) as cm:
            hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        return cm.exception.problems

    def v4_receipt(self) -> bytes:
        return git('show', '%s:%s' % (self.REV, hps.AMENDMENT_V4_RECEIPT_REL), cwd=self.clone)

    def test_the_receipt_at_amendment_v4(self):
        r = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        self.assertEqual({k: v['head'][:8] for k, v in r['documents'].items()},
                         {'config.json': 'f158969e', 'ARCHITECTURE_FINAL.md': '4c762f21',
                          'protocol_FINAL.md': 'c46718fa', 'cells.json': '47961619'})
        am = r['amendments']
        self.assertEqual([(c['name'], c['present_at_head'], c.get('added_in_commits'))
                          for c in am['chain']],
                         [('v2', True, [hps.AMENDMENT_COMMIT]),
                          ('v3', True, [hps.AMENDMENT_V3_COMMIT]),
                          ('v4', True, [hps.AMENDMENT_V4_COMMIT])])
        self.assertTrue(all(am['head_equals_the_latest_written_values'].values()))
        self.assertEqual(am['latest_writer']['protocol_FINAL.md'], 'v4')
        self.assertEqual(am['latest_writer']['serving_manifest_canonical'], 'v2')
        link = am['chain'][2]['names_its_predecessor']
        self.assertEqual((link['predecessor'], link['commit_named']),
                         ('v3', hps.AMENDMENT_V3_COMMIT))
        self.assertTrue(all(link[k] for k in (
            'equals_the_predecessor_receipt_at_head', 'equals_the_predecessor_commit',
            'equal_the_predecessor_written_values')))
        hist = am['document_pin_history']['protocol_FINAL.md']['pins']
        self.assertEqual([(p['at'][:2], p['sha256'][:8]) for p in hist],
                         [('b0', '64ace6d3'), ('v2', '6c0ebf2f'), ('v3', '73dd0573'),
                          ('v4', 'c46718fa'), ('he', 'c46718fa')])
        since = r['since_the_superseded_receipt']
        # the 2009 receipt is not committed yet at 90219f2: the latest superseded receipt
        # present there is still 0027 (SUPERSEDES[3], not the current SUPERSEDES[-1])
        self.assertEqual(since['receipt'], hps.SUPERSEDES[3]['path'])
        self.assertEqual(since['recorded_head'][:7], '79e60d4')
        self.assertTrue(since['superseded_map_reproduces_from_git'])
        self.assertEqual(sorted(since['harness_entries_moved']), ['build_live_ab_results.py'])
        self.assertEqual(sorted(since['documents_moved']),
                         ['ARCHITECTURE_FINAL.md', 'cells.json', 'protocol_FINAL.md'])
        self.assertTrue(r['cells_vocabulary_successor']['holds'])
        self.assertTrue(r['mutation_partition_of_the_final_verification_of_8f0b4ae'][
            'checked']['exclusive_and_exhaustive'])

    def test_negative_a_v4_receipt_naming_another_v3_receipt_refuses(self):
        rec = json.loads(self.v4_receipt())
        rec['predecessor_amendment_v3']['receipt_sha256'] = 'f' * 64
        problems = self.refused(commit_with(self.clone, self.REV, {
            hps.AMENDMENT_V4_RECEIPT_REL: json.dumps(rec).encode()}))
        self.assertEqual(problems, ['amendment_chain_link:v4'])

    def test_negative_a_double_counting_partition_refuses_the_receipt(self):
        broken = json.loads(json.dumps(hps.MUTATION_PARTITION_8F0B4AE))
        broken['killed_by_the_right_control'].append('E3')
        with mock.patch.object(hps, 'MUTATION_PARTITION_8F0B4AE', broken):
            with self.assertRaises(hps.Refused) as cm:
                hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
        self.assertEqual(cm.exception.problems,
                         ['mutation_partition:classes_overlap', 'mutation_partition:count:killed',
                          'mutation_partition:count:killed_by_the_right_control'])

    def test_negative_a_v4_receipt_copied_in_without_its_commit_refuses(self):
        problems = self.refused(commit_with(self.clone, hps.AMENDMENT_V3_COMMIT,
                                            {hps.AMENDMENT_V4_RECEIPT_REL: self.v4_receipt()}))
        self.assertIn('amendment_chain:v4', problems)
        self.assertIn('amendment_receipt_disagrees', problems)


#: Two tiny fixture suites (never the real five-suite discovery): one fails on purpose, with a
#: distinctive assertion message the retained stderr log must keep; one passes.
FAILING_FIXTURE_SUITE = '''\
import unittest


class FixtureFailTests(unittest.TestCase):
    def test_it_fails_on_purpose(self):
        assert False, "PINSUCC_FIXTURE_MARKER_9f2b"


if __name__ == '__main__':
    unittest.main()
'''
PASSING_FIXTURE_SUITE = '''\
import unittest


class FixturePassTests(unittest.TestCase):
    def test_it_passes(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''


class SoloRunSuitesPinLogTests(_Clone):
    """``build_receipt(..., run_suites=True)`` against two small fixture suites living OUTSIDE
    the clone (so the clone's tracked tree stays clean): the retained log of a failing suite
    keeps its traceback, the receipt's digests equal the decompressed log bytes, and
    ``--no-suites`` stays as it was."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.fixtures_dir = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_fixtures_')))
        cls.out_dir = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_pinlogs_out_')))
        (cls.fixtures_dir / 'fail_suite.py').write_text(FAILING_FIXTURE_SUITE)
        (cls.fixtures_dir / 'pass_suite.py').write_text(PASSING_FIXTURE_SUITE)
        cls.suites = (('fail_suite', [str(cls.fixtures_dir / 'fail_suite.py')]),
                      ('pass_suite', [str(cls.fixtures_dir / 'pass_suite.py')]))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(str(cls.fixtures_dir), ignore_errors=True)
        shutil.rmtree(str(cls.out_dir), ignore_errors=True)
        super().tearDownClass()

    #: A fixed stamp for every build() in this class, so two calls always land in the same
    #: pin_logs directory (never flaky at a real minute boundary around a sub-second run).
    STAMP = '20260101_0000'

    def build(self, suites: tuple | None = None) -> dict:
        real_strftime = time.strftime

        def frozen(fmt: str, *a, **kw) -> str:
            return self.STAMP if fmt == '%Y%m%d_%H%M' else real_strftime(fmt, *a, **kw)

        with mock.patch.object(hps, 'SUITES', suites or self.suites), \
                mock.patch.object(hps.time, 'strftime', side_effect=frozen):
            return hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=True,
                                     out_dir=self.out_dir)

    def pin_logs_dir(self, receipt: dict) -> Path:
        self.assertEqual(receipt['receipt_stamp'], self.STAMP)
        return self.out_dir / hps.PIN_LOGS_DIRNAME / receipt['receipt_stamp']

    def test_a_failing_fixtures_traceback_is_kept_in_the_retained_stderr_log(self):
        r = self.build()
        runs = {row['suite']: row for row in r['solo_run_suites']['runs']}
        self.assertFalse(runs['fail_suite']['result']['passed'])
        self.assertTrue(runs['pass_suite']['result']['passed'])
        stderr_path = self.pin_logs_dir(r) / 'fail_suite.stderr.gz'
        kept = gzip.decompress(stderr_path.read_bytes()).decode('utf-8')
        self.assertIn('PINSUCC_FIXTURE_MARKER_9f2b', kept)
        self.assertIn('AssertionError', kept)
        self.assertIn('Traceback (most recent call last)', kept)

    def test_the_receipts_digests_equal_the_decompressed_log_bytes(self):
        r = self.build()
        pin_logs_dir = self.pin_logs_dir(r)
        for row in r['solo_run_suites']['runs']:
            for stream in ('stdout', 'stderr'):
                path = pin_logs_dir / ('%s.%s.gz' % (row['suite'], stream))
                decompressed = gzip.decompress(path.read_bytes())
                self.assertEqual(hps.sha256(decompressed), row['%s_sha256' % stream])
                log = row['%s_log' % stream]
                self.assertEqual(log['uncompressed_sha256'], row['%s_sha256' % stream])
                self.assertEqual(log['uncompressed_bytes'], row['%s_bytes' % stream])
                self.assertEqual(log['compressed_sha256'], hps.sha256(path.read_bytes()))
                self.assertEqual(log['compressed_bytes'], len(path.read_bytes()))

    def test_a_second_identical_build_is_a_no_op_and_a_changed_suite_refuses(self):
        r1 = self.build()
        r2 = self.build()
        self.assertEqual(self.pin_logs_dir(r1), self.pin_logs_dir(r2))
        for row in r2['solo_run_suites']['runs']:
            self.assertIn('stderr_log', row)
        # the suite named 'fail_suite' now runs the passing script: same name, same stamp,
        # different bytes -- the write-once retention must refuse, not silently overwrite
        changed_suites = (('fail_suite', [str(self.fixtures_dir / 'pass_suite.py')]),
                          ('pass_suite', [str(self.fixtures_dir / 'pass_suite.py')]))
        with self.assertRaises(hps.Refused) as cm:
            self.build(suites=changed_suites)
        self.assertTrue(any(p.startswith('pin_log_mismatch:fail_suite.')
                            for p in cm.exception.problems), cm.exception.problems)

    def test_negative_no_out_dir_refuses_before_any_suite_runs(self):
        with mock.patch.object(hps, 'SUITES', self.suites):
            with self.assertRaises(hps.Refused) as cm:
                hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=True)
        self.assertEqual(cm.exception.problems, ['pin_logs_out_dir_required'])

    def test_the_receipt_stamp_and_its_pin_logs_dir_share_one_clock_read(self):
        """``build_receipt`` must read the ``%Y%m%d_%H%M`` clock exactly once and use that same
        ``stamp`` for both the receipt filename (``receipt_stamp``) and the pin_logs directory a
        run's suites are retained under: a second, independent clock read for the directory
        could disagree with the stamp at a minute boundary (the bug the shared ``stamp`` fixes).
        A fail-before/pass-after control: reverting ``pin_logs_dir`` to a fresh
        ``time.strftime(...)`` call reintroduces exactly this, and this test then fails, both on
        the call count and on the directory actually written to."""
        real_strftime = time.strftime
        stamps = ['20270101_0000', '20270101_9999']
        calls = {'n': 0}

        def side_effect(fmt: str, *a, **kw) -> str:
            if fmt == '%Y%m%d_%H%M':
                i = min(calls['n'], len(stamps) - 1)
                calls['n'] += 1
                return stamps[i]
            return real_strftime(fmt, *a, **kw)

        with mock.patch.object(hps, 'SUITES', self.suites), \
                mock.patch.object(hps.time, 'strftime', side_effect=side_effect):
            r = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=True,
                                  out_dir=self.out_dir)
        self.assertEqual(calls['n'], 1,
                         'build_receipt must read the %Y%m%d_%H%M clock exactly once, not once '
                         'per use (receipt filename vs. pin_logs directory)')
        self.assertEqual(r['receipt_stamp'], stamps[0])
        first_dir = self.out_dir / hps.PIN_LOGS_DIRNAME / stamps[0]
        second_dir = self.out_dir / hps.PIN_LOGS_DIRNAME / stamps[1]
        self.assertTrue((first_dir / 'fail_suite.stderr.gz').exists(),
                        'the suites must have been retained under the SAME stamp as receipt_stamp')
        self.assertFalse(second_dir.exists(),
                         'a second, independent clock read for the directory would land here '
                         'and disagree with receipt_stamp')

    def test_no_suites_behaviour_is_unchanged(self):
        with tempfile.TemporaryDirectory() as fresh_out:
            r = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False,
                                  out_dir=fresh_out)
            self.assertEqual(r['solo_run_suites'], 'not run in this invocation (--no-suites)')
            self.assertIn('receipt_stamp', r)
            self.assertFalse((Path(fresh_out) / hps.PIN_LOGS_DIRNAME).exists(),
                             'no suites ran, so no pin_logs directory is made')
            # out_dir need not even be given when --no-suites (main() still passes one, but
            # build_receipt() itself must not require it outside the run_suites branch)
            r2 = hps.build_receipt(self.clone, hps.PREDECESSOR, run_suites=False)
            self.assertEqual(r2['solo_run_suites'], 'not run in this invocation (--no-suites)')


if __name__ == '__main__':
    unittest.main()
