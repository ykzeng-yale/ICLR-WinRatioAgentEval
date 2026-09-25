"""Controls of ``repro_inputs``: a missing reproduction input fails by NAME, not by digest drift.

Root 22:08 (``reviews/eb1_eb5_summary_repair_interim_20260924_2208.md``, main 76f5e71): in a
sparse worktree the seven summary controls never reached their assertions -- the mock tree's
program preflight refused with ``harness_file_sha`` / ``preflight_rule_failed``
(``reused_file_sha256``, ``sandbox_profile_sha256`` drift) and ``setUpClass`` died on a
``StopIteration``.  ``repro_inputs.problems`` names each input instead;
``tests_eb1_entry.setUpModule`` (shared by the summary module and seven others) now calls it.

* :class:`ThisCheckout` -- the positive control: this checkout has what the controls need.  In a
  sparse or shallow checkout, or without ``clang``, it FAILS with the named list.
* :class:`SparseRefusalTests` -- the two codes are exactly root's refusal: with the pilot
  directory emptied and the pilot ``sandbox`` unimportable, the production ``orch.preflight`` of a
  mock tree refuses ``{harness_file_sha, preflight_rule_failed}`` on those two drift rows, and
  the helper names ``reused_file_missing`` x5 and ``sandbox_profile_unobservable`` for a checkout
  without ``experiments/local_stream``; without the faults both are empty.
* One negative control per code (each refused), with its positive twin: no seatbelt; the three
  roster sources (synthetic pins; a byte flipped; ``mbpp.jsonl`` alone missing, which the suite
  would take as roster S1; found through a cache directory); the pilot task list; git history
  (an empty repository); the compiler (``PATH`` without ``clang``).
* :class:`SetUpModuleHook` -- the hook fails the module with the names and restores TMPDIR.
* :class:`HistoryListTests` -- every commit the controls ``git show`` / ``git diff`` is in
  ``repro_inputs.HISTORY`` (a reference outside it is reported).

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off (protocol
14.7).
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

import dryrun_live_ab as dry                                            # noqa: E402
import lab_common                                                       # noqa: E402
import lab_data                                                         # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import repro_inputs as ri                                               # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402

REPO = ri.REPO


def codes(found) -> list:
    return sorted(p['code'] for p in found)


class TmpCase(unittest.TestCase):
    def tmp(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix='repro_inputs_'))
        self.addCleanup(shutil.rmtree, path, True)
        return path


class ThisCheckout(unittest.TestCase):
    def test_this_checkout_has_every_input_the_controls_need(self):
        found = ri.problems(REPO, 'live_ab_controls')
        self.assertEqual(found, [], '\n' + ri.report(found))


class SparseRefusalTests(TmpCase):
    def _preflight(self, tree) -> tuple[set, set]:
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            try:
                return set(orch.preflight(tree.ctx())), set()
            except lab_common.PreflightError as exc:
                return (set(str(exc).split(',')),
                        {r['item'] for r in getattr(exc, 'drift', [])})

    def test_the_two_named_codes_are_the_two_drift_rows_of_the_sparse_refusal(self):
        empty = self.tmp()
        with mock.patch.object(lab_common, 'LS_DIR', empty), \
                mock.patch.object(lab_data, '_pilot_sandbox',
                                  side_effect=ModuleNotFoundError("No module named 'sandbox'")):
            tree = sup.Tree('T4', 4)
            self.addCleanup(tree.close)
            checks, items = self._preflight(tree)
        self.assertEqual(checks, {'harness_file_sha', 'preflight_rule_failed'})
        self.assertEqual(items, {'reused_file_sha256', 'sandbox_profile_sha256'})
        found = ri.problems(empty, 'mock_preflight')
        self.assertEqual(codes(found),
                         ['reused_file_missing'] * 5 + ['sandbox_profile_unobservable'])
        self.assertEqual({p['input'] for p in found if p['code'] == 'reused_file_missing'},
                         {'experiments/local_stream/' + n for n in lab_common.REUSED_FILES})
        self.assertTrue(all('FULL clone' in p['message'] or 'full checkout' in p['message']
                            for p in found))

    def test_positive_twin_without_the_faults_nothing_drifts_and_nothing_is_named(self):
        tree = sup.Tree('T4', 4)
        self.addCleanup(tree.close)
        self.assertEqual(self._preflight(tree), (set(), set()))
        self.assertEqual(ri.problems(REPO, 'mock_preflight'), [])


class ProfileTests(TmpCase):
    def _copy(self) -> Path:
        root = self.tmp()
        dest = root / 'experiments' / 'local_stream'
        dest.mkdir(parents=True)
        for name in lab_common.REUSED_FILES:
            shutil.copyfile(lab_common.LS_DIR / name, dest / name)
        return root

    def test_the_helper_observes_what_the_harness_observes(self):
        root = self._copy()
        got = ri.observe_profile(root)
        self.assertIsNotNone(got)
        self.assertEqual(got, lab_data.observed_sandbox_profile_sha256())
        self.assertEqual(ri.problems(root, 'mock_preflight'), [])

    def test_negative_no_seatbelt_is_named(self):
        root = self._copy()
        real = os.path.exists
        with mock.patch('os.path.exists',
                        side_effect=lambda p: False if p == '/usr/bin/sandbox-exec' else real(p)):
            self.assertIsNone(ri.observe_profile(root))
            self.assertEqual(codes(ri.problems(root, 'mock_preflight')),
                             ['sandbox_profile_unobservable'])


class SourceTests(TmpCase):
    """Synthetic pins, so the control needs none of the real (untracked) files."""

    def setUp(self) -> None:
        self.root = self.tmp()
        self.data = self.root / 'work' / 'local_stream' / 'data'
        self.data.mkdir(parents=True)
        self.content = {name: ('synthetic %s\n' % name).encode() for name in lab_data.SOURCES}
        pins = {name: dict(spec, bytes=len(self.content[name]),
                           sha256=hashlib.sha256(self.content[name]).hexdigest())
                for name, spec in lab_data.SOURCES.items()}
        patcher = mock.patch.object(lab_data, 'SOURCES', pins)
        patcher.start()
        self.addCleanup(patcher.stop)

    def put(self, name: str, directory: Path | None = None, data: bytes | None = None) -> None:
        spec = lab_data.SOURCES[name]
        (directory or self.data).joinpath(spec['filename']).write_bytes(
            self.content[name] if data is None else data)

    def found(self, cache_dirs=()) -> list:
        return [p for p in ri.problems(self.root, 'live_ab', cache_dirs=cache_dirs)
                if p['code'].startswith('pinned_source')]

    def test_negative_every_absent_source_is_named(self):
        found = self.found()
        self.assertEqual(codes(found), ['pinned_source_missing'] * 3)
        (mbpp,) = [p for p in found if p['input'].endswith('/mbpp.jsonl')]
        self.assertIn("'S1' != 'EXT'", mbpp['message'])

    def test_negative_mbpp_jsonl_alone_missing_is_the_one_named(self):
        self.put('mbpp_sanitized')
        self.put('humaneval')
        (only,) = self.found()
        self.assertEqual((only['code'], only['input']),
                         ('pinned_source_missing', 'work/local_stream/data/mbpp.jsonl'))

    def test_negative_a_flipped_byte_is_named(self):
        for name in lab_data.SOURCES:
            self.put(name)
        data = bytearray(self.content['mbpp_sanitized'])
        data[0] ^= 1
        self.put('mbpp_sanitized', data=bytes(data))
        self.assertEqual(codes(self.found()), ['pinned_source_digest'])

    def test_positive_present_here_or_in_a_cache_directory(self):
        for name in lab_data.SOURCES:
            self.put(name)
        self.assertEqual(self.found(), [])
        (self.data / 'mbpp.jsonl').unlink()
        cache = self.tmp()
        self.put('mbpp_full', directory=cache)
        self.assertEqual(self.found(cache_dirs=(cache,)), [])


class PilotTasksTests(TmpCase):
    def test_negative_absent_or_other_bytes_and_positive(self):
        root = self.tmp()
        data = root / 'work' / 'local_stream' / 'data'
        data.mkdir(parents=True)

        def pilot() -> list:
            return codes(p for p in ri.problems(root, 'live_ab', cache_dirs=())
                         if p['code'].startswith('pilot_tasks'))
        self.assertEqual(pilot(), ['pilot_tasks_missing'])
        (data / 'tasks.json').write_text('[]', encoding='utf-8')
        self.assertEqual(pilot(), ['pilot_tasks_digest'])
        with mock.patch.dict(ri.PILOT_TASKS, sha256=hashlib.sha256(b'[]').hexdigest()):
            self.assertEqual(pilot(), [])


class HistoryAndCompilerTests(TmpCase):
    def test_negative_an_empty_repository_names_every_commit(self):
        root = self.tmp()
        subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
        found = ri.problems(root, 'summary')
        history = [p for p in found if p['code'] == 'git_history_missing']
        self.assertEqual({p['input'] for p in history}, set(ri.HISTORY))
        self.assertEqual(ri.problems(REPO, 'summary'), [])

    def test_negative_no_compiler_on_path_is_named(self):
        bin_dir = self.tmp()
        os.symlink(shutil.which('git'), bin_dir / 'git')          # git stays; clang does not
        with mock.patch.dict(os.environ, {'PATH': str(bin_dir)}):
            self.assertEqual(codes(ri.problems(REPO, 'live_ab_controls')),
                             ['c_compiler_missing'])
        self.assertEqual(ri.problems(REPO, 'live_ab_controls'), [])


class SetUpModuleHook(TmpCase):
    def test_negative_the_module_fails_naming_the_files_and_restores_tmpdir(self):
        before = (os.environ.get('TMPDIR'), tempfile.tempdir)
        with mock.patch.object(ri, 'REPO', self.tmp()):
            with self.assertRaises(ri.MissingReproductionInputs) as caught:
                entry.setUpModule()
        self.assertIn('reused_file_missing  experiments/local_stream/sandbox.py',
                      str(caught.exception))
        self.assertIn('sandbox_profile_unobservable', str(caught.exception))
        self.assertEqual((os.environ.get('TMPDIR'), tempfile.tempdir), before)

    def test_positive_the_module_runs_under_the_prescribed_tmpdir(self):
        before = (os.environ.get('TMPDIR'), tempfile.tempdir)
        entry.setUpModule()
        try:
            self.assertEqual(os.environ.get('TMPDIR'), entry.LABSBX)
        finally:
            entry.tearDownModule()
        self.assertEqual((os.environ.get('TMPDIR'), tempfile.tempdir), before)


class HistoryListTests(unittest.TestCase):
    #: Where the controls name a commit they read: ``PRE_FIX`` / ``BASE`` constants and
    #: ``'<rev>:experiments/...`` arguments of ``git show``.
    REF = re.compile(r"^(?:PRE_FIX|BASE) = '([0-9a-f]{7,40})'|'([0-9a-f]{7,40}):experiments/",
                     re.M)

    @staticmethod
    def unlisted(refs) -> list:
        out = []
        for ref in sorted(refs):
            res = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--verify', '--quiet',
                                  ref + '^{commit}'], capture_output=True, text=True, check=False)
            if res.returncode != 0 or res.stdout.strip() not in ri.HISTORY:
                out.append(ref)
        return out

    def test_every_commit_the_controls_read_is_listed(self):
        refs = set()
        for path in HERE.glob('tests_*.py'):
            if path.name == Path(__file__).name:
                continue
            refs |= {a or b for a, b in self.REF.findall(path.read_text('utf-8'))}
        self.assertGreaterEqual(len(refs), 4, sorted(refs))
        self.assertEqual(self.unlisted(refs), [])

    def test_negative_a_reference_outside_the_list_is_reported(self):
        self.assertEqual(self.unlisted({'c001354', 'b049307'}), ['c001354'])


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
