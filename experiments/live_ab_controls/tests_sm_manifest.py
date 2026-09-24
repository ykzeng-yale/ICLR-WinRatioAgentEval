"""The serving-manifest binding, focused controls (root 01:53, session 60 repair).

Root, ``reviews/serving_manifest_binding_ruling_20260924_0153.md``: one tracked write-once
artifact ``results/live_ab/freeze/serving_manifest.json``, assembled from the durable build,
its canonical digest in the configuration; preflight and every invocation/start/restart read
that exact artifact and re-check the digest and the launcher, the recursively resolved
non-system libraries, the Metal library, the build provenance and ``/props.build_info``
against the actual runtime; "a missing file, null digest, self-comparison, path substitution
or runtime mismatch refuses".

Every check here has a NEGATIVE CONTROL beside it (the same call on an input it must refuse,
asserted refused, or the unmodified input, asserted accepted), so none can pass by being
unable to fail.  What runs: ``lab_serving_manifest`` in process; ``otool``/``nm``/``codesign``
on the compiled ``sm_fixture`` double (metadata reads; nothing of the durable build, no model,
no server); the assembler TOOL as a subprocess.  The main() subprocess controls are
``tests_sm_entry``.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
SERVING = HERE.parent / 'live_ab_serving'
for _p in (LIVE, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import lab_common                                                       # noqa: E402
import lab_serving_manifest as sm                                       # noqa: E402
import sm_fixture                                                       # noqa: E402

LIVE_CFG: dict = json.loads((LIVE / 'config.json').read_text(encoding='utf-8'))
LABSBX: str = lab_common.prescribed_tmpdir(LIVE_CFG)
COMMIT = sm_fixture.COMMIT
_saved: dict = {}


def setUpModule() -> None:
    """Every ``<TMP>`` token must resolve identically here and in the tool's subprocess:
    the module runs under the prescribed TMPDIR (as ``tests_eb1_entry`` does)."""
    os.makedirs(LABSBX, exist_ok=True)
    _saved['TMPDIR'] = os.environ.get('TMPDIR')
    _saved['tempdir'] = tempfile.tempdir
    os.environ['TMPDIR'] = LABSBX
    tempfile.tempdir = LABSBX


def tearDownModule() -> None:
    tempfile.tempdir = _saved.get('tempdir')
    if _saved.get('TMPDIR') is None:
        os.environ.pop('TMPDIR', None)
    else:
        os.environ['TMPDIR'] = _saved['TMPDIR']


def _load_module(name: str, path: Path, source: str | None = None) -> types.ModuleType:
    """A module object from ``path`` (or from ``source``, a mutated copy of it)."""
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    code = compile(source if source is not None else path.read_text('utf-8'), str(path),
                   'exec')
    exec(code, mod.__dict__)                                   # noqa: S102
    return mod


# --------------------------------------------------------------------------- #
# 1. the transcription agrees with live_ab_serving/dependency_closure.py
# --------------------------------------------------------------------------- #
def top_level_named(tree: ast.Module) -> dict:
    """name -> list of AST dumps of every top-level assignment / function of that name."""
    out: dict = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            continue
        for name in names:
            out.setdefault(name, []).append(ast.dump(node, include_attributes=False))
    return out


def transcription_disagreements(original_source: str, transcribed_source: str) -> list:
    """The names, from ``SCHEMA`` through ``verify_closure`` of the original, whose top-level
    statement is absent from the transcription, defined there more than once, or not
    AST-identical.  ``[]`` when the transcription is verbatim."""
    original = top_level_named(ast.parse(original_source))
    ours = top_level_named(ast.parse(transcribed_source))
    order = [n for n in original if n not in ('HERE', 'LAB')]
    wanted = order[order.index('SCHEMA'):]
    out = []
    for name in wanted:
        if len(ours.get(name, [])) != 1 or ours[name] != original[name]:
            out.append(name)
    return out


class TranscriptionAgreementTests(unittest.TestCase):
    """How the harness copy and ``live_ab_serving/dependency_closure.py`` are KEPT in
    agreement: statement-level AST identity, and the original's own root-reviewed test class
    rerun against the copy (``TranscribedDependencyClosureTests`` below)."""

    ORIGINAL = SERVING / 'dependency_closure.py'

    def test_every_transcribed_statement_is_ast_identical_to_the_original(self):
        original = self.ORIGINAL.read_text('utf-8')
        ours = (LIVE / 'lab_serving_manifest.py').read_text('utf-8')
        self.assertEqual(transcription_disagreements(original, ours), [])
        names = top_level_named(ast.parse(original))
        for name in ('SCHEMA', 'SYSTEM_PREFIXES', 'NON_DEPENDENCY_COMMANDS',
                     'MODELLED_DLOPEN_INSTALL_NAMES', 'parse_load_commands', 'derive_closure',
                     'verify_closure'):
            self.assertIn(name, names, 'the comparison covers %s' % name)

    def test_control_a_one_token_edit_on_either_side_is_detected(self):
        original = self.ORIGINAL.read_text('utf-8')
        ours = (LIVE / 'lab_serving_manifest.py').read_text('utf-8')
        edited = ours.replace("SYSTEM_PREFIXES = ('/usr/lib/', '/System/')",
                              "SYSTEM_PREFIXES = ('/usr/lib/', '/System/', '/opt/')")
        self.assertNotEqual(edited, ours)
        self.assertEqual(transcription_disagreements(original, edited), ['SYSTEM_PREFIXES'])
        edited = original.replace("if len(files) > max_members:",
                                  "if len(files) >= max_members:")
        self.assertNotEqual(edited, original)
        self.assertEqual(transcription_disagreements(edited, ours), ['derive_closure'])
        redefined = ours + '\n\ndef resolve_reference(ref, **kw):\n    return {}\n'
        self.assertEqual(transcription_disagreements(original, redefined),
                         ['resolve_reference'])

    def test_control_the_rerun_class_fails_on_a_mutated_transcription(self):
        """The rerun below is a control only if it can fail: a transcription that stops
        walking at the launcher's direct dependencies must fail the original's transitive
        test."""
        ours = (LIVE / 'lab_serving_manifest.py').read_text('utf-8')
        walk = "            queue.append(canon['canonical'])\n    if truncated:"
        self.assertEqual(ours.count(walk), 1)
        src = ours.replace(walk, "            pass\n    if truncated:")
        mutant = _load_module('lsm_mutant', LIVE / 'lab_serving_manifest.py', src)
        good = unittest.TestResult()
        unittest.TestSuite([TranscribedDependencyClosureTests(
            'test_a_complete_matched_graph_resolves_TRANSITIVELY')]).run(good)
        self.assertTrue(good.wasSuccessful(), good.failures + good.errors)
        self.assertEqual(good.testsRun, 1)

        class _Mutant(TranscribedDependencyClosureTests):
            @classmethod
            def setUpClass(cls):
                cls.dc = mutant
        bad = unittest.TestResult()
        suite = unittest.TestSuite([_Mutant('test_a_complete_matched_graph_resolves_'
                                            'TRANSITIVELY')])
        suite.run(bad)
        self.assertEqual(bad.testsRun, 1)
        self.assertFalse(bad.wasSuccessful(), 'the rerun could not tell the mutant apart')
        self.assertEqual(len(bad.failures), 1, bad.errors)


_TDC = _load_module('tests_dependency_closure_original',
                    SERVING / 'tests_dependency_closure.py')


class TranscribedDependencyClosureTests(_TDC.DependencyClosureTests):
    """The ORIGINAL's whole root-reviewed test class (root 14:03, 14:41, 16:30), unchanged,
    with ``lab_serving_manifest`` -- the harness transcription -- in place of
    ``dependency_closure``."""

    @classmethod
    def setUpClass(cls):
        cls.dc = sm


# --------------------------------------------------------------------------- #
# 2. the artifact: one fixed path, canonical bytes, the configuration digest
# --------------------------------------------------------------------------- #
class TmpCase(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='sm_')))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def fixture(self, name: str = 'build') -> sm_fixture.Build:
        state = self.tmp / (name + '_state')
        state.mkdir()
        return sm_fixture.Build(self.tmp / name, state=state)


class ArtifactTests(TmpCase):

    def test_the_artifact_is_the_tracked_path_of_the_freeze_tree(self):
        self.assertEqual(sm.artifact_path(lab_common.FREEZE_DIR),
                         lab_common.REPO_ROOT / sm.TRACKED_RELPATH)
        self.assertEqual(sm.TRACKED_RELPATH, 'results/live_ab/freeze/serving_manifest.json')
        self.assertEqual(sm.artifact_path_problems(sm.artifact_path(self.tmp / 'freeze')), [])

    def test_control_any_other_name_directory_or_a_relative_path_is_refused(self):
        for path in (self.tmp / 'freeze' / 'manifest.json', self.tmp / 'other' /
                     sm.ARTIFACT_NAME, Path('freeze') / sm.ARTIFACT_NAME,
                     self.tmp / 'freeze' / 'x' / sm.ARTIFACT_NAME, ''):
            with self.subTest(path=str(path)):
                self.assertEqual(sm.artifact_path_problems(path), ['artifact_path'])
                self.assertEqual(sm.read_artifact(path)[2], ['artifact_path'])

    def test_missing_symlinked_non_canonical_or_non_object_files_are_refused(self):
        path = sm.artifact_path(self.tmp / 'freeze')
        obj = {'schema': sm.MANIFEST_SCHEMA, 'mock': True}
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_missing'])
        digest = sm.write_artifact(path, obj)
        got, found, problems = sm.read_artifact(path)
        self.assertEqual((got, found, problems), (obj, lab_common.sha256_canonical(obj), []),
                         'control: the canonical regular file reads')
        self.assertEqual(found, digest)
        # a symlink at the fixed path, to a byte-identical copy kept elsewhere
        elsewhere = self.tmp / 'elsewhere' / 'freeze' / sm.ARTIFACT_NAME
        elsewhere.parent.mkdir(parents=True)
        shutil.copy2(str(path), str(elsewhere))
        path.unlink()
        os.symlink(str(elsewhere), str(path))
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_not_regular_file'])
        self.assertEqual(sm.read_artifact(elsewhere)[2], [], 'the copy itself is valid')
        path.unlink()
        path.write_text(json.dumps(obj, indent=1) + '\n', encoding='utf-8')
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_not_canonical'])
        path.write_text(lab_common.canonical_json(obj), encoding='utf-8')   # no newline
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_not_canonical'])
        path.write_text('[1]\n', encoding='utf-8')
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_not_object'])
        path.write_text('{not json\n', encoding='utf-8')
        self.assertEqual(sm.read_artifact(path)[2], ['artifact_unreadable'])

    def test_a_null_or_different_configuration_digest_refuses(self):
        path = sm.artifact_path(self.tmp / 'freeze')
        digest = sm.write_artifact(path, {'schema': sm.MANIFEST_SCHEMA, 'mock': True})
        self.assertEqual(sm.verify_artifact(path, digest)[2], [], 'control: the digest')
        for expected, label in ((None, 'config_digest_null'), ('', 'config_digest_null'),
                                ('X' * 64, 'config_digest_null'), ('0' * 64, 'digest')):
            with self.subTest(expected=expected):
                obj, found, problems = sm.verify_artifact(path, expected)
                self.assertEqual((obj, problems), (None, [label]))
                self.assertEqual(found, digest, 'the artifact digest is reported, never used '
                                                'as the expectation')
        path.unlink()
        self.assertEqual(sm.verify_artifact(path, None)[2],
                         ['artifact_missing', 'config_digest_null'])

    def test_the_artifact_is_written_once(self):
        path = sm.artifact_path(self.tmp / 'freeze')
        sm.write_artifact(path, {'a': 1})
        with self.assertRaises(lab_common.WriteOnceViolation):
            sm.write_artifact(path, {'a': 2})
        self.assertEqual(json.loads(path.read_text('utf-8')), {'a': 1}, 'never replaced')
        with self.assertRaises(sm.ManifestError):
            sm.write_artifact(self.tmp / 'freeze' / 'other.json', {'a': 1})
        self.assertFalse((self.tmp / 'freeze' / 'other.json').exists())

    def test_runtime_or_configuration_overrides_of_the_location_are_refused(self):
        root = self.tmp / 'results'
        base = {'llama_cpp': {'commit': COMMIT, 'serving_manifest_sha256': '0' * 64},
                '_runtime': {'results_root': str(root), 'freeze_dir': str(root / 'freeze')}}
        self.assertEqual(sm.override_problems(base, root), [], 'control: the fixed layout')
        cases = {
            'override:_runtime.freeze_dir': ('_runtime', 'freeze_dir', str(self.tmp / 'f')),
            'override:_runtime.serving_manifest_path': (
                '_runtime', 'serving_manifest_path', str(self.tmp / 'x.json')),
            'override:serving_manifest': (None, 'serving_manifest', {'x': 1}),
            'override:llama_cpp.serving_manifest_path': (
                'llama_cpp', 'serving_manifest_path', str(self.tmp / 'x.json')),
        }
        for label, (block, key, value) in cases.items():
            with self.subTest(label=label):
                cfg = copy.deepcopy(base)
                (cfg if block is None else cfg[block])[key] = value
                self.assertEqual(sm.override_problems(cfg, root), [label])


# --------------------------------------------------------------------------- #
# 3. the assembler: the pure function and the tool
# --------------------------------------------------------------------------- #
class AssemblerTests(TmpCase):

    def test_the_assembled_manifest_carries_every_protocol_2_2_field(self):
        b = self.fixture()
        m = b.manifest()
        for key in ('llama_cpp_commit', 'launcher_sha256', 'libraries', 'metal_library',
                    'resolved_rpath', 'cmake_options', 'compiler_version', 'sdk_version',
                    'build_log_sha256', 'configure_log_sha256', 'props_build_info'):
            self.assertIn(key, m, 'protocol 2.2 field %s' % key)
        self.assertEqual(m['llama_cpp_commit'], COMMIT)
        self.assertEqual(m['launcher_sha256'], lab_common.sha256_file(b.launcher))
        self.assertEqual(m['launcher']['path'], lab_common.tokenize_path(str(b.launcher)))
        # RECURSIVE: libeb1c-base is reached only THROUGH libeb1c-core, never named by the
        # launcher, and it is bound by its canonical (versioned) target, not the alias
        self.assertEqual([lib['name'].rsplit('/', 1)[-1] for lib in m['libraries']],
                         ['libeb1c-base.0.1.0.dylib', 'libeb1c-core.0.dylib'])
        for lib in m['libraries']:
            path = sm.resolve_token(lib['name'])
            self.assertEqual(lib['sha256'], lab_common.sha256_file(path))
        edges = {(e['parent'].rsplit('/', 1)[-1], e['reference']): e for e in
                 m['closure']['edges']}
        self.assertEqual(sorted(edges), [('libeb1c-core.0.dylib', '@rpath/libeb1c-base.0.dylib'),
                                         ('llama-server', '@rpath/libeb1c-core.0.dylib')])
        alias = edges[('libeb1c-core.0.dylib', '@rpath/libeb1c-base.0.dylib')]
        self.assertTrue(alias['resolved'].endswith('/libeb1c-base.0.dylib'))
        self.assertTrue(alias['canonical'].endswith('/libeb1c-base.0.1.0.dylib'))
        self.assertEqual(m['resolved_rpath'], [lab_common.tokenize_path(str(b.bin))])
        self.assertEqual(m['closure']['system_references'], ['/usr/lib/libSystem.B.dylib'])
        # the embedded Metal library: its container and the section's own bytes
        metal = m['metal_library']
        self.assertEqual((metal['kind'], metal['section']),
                         ('embedded', '__DATA,__ggml_metallib'))
        self.assertEqual(metal['container'], lab_common.tokenize_path(str(b.base)))
        data = b.base.read_bytes()
        self.assertIn(sm_fixture.METAL_MARKER, data)
        section, problem = sm.section_bytes(str(b.base), '__DATA', '__ggml_metallib')
        self.assertIsNone(problem)
        self.assertIn(sm_fixture.METAL_MARKER, section)
        self.assertEqual(metal['section_sha256'], lab_common.sha256_bytes(section))
        self.assertEqual(metal['container_sha256'], lab_common.sha256_file(b.base))
        # the build provenance and the expected build string
        self.assertEqual(m['props_build_info'], sm_fixture.BUILD_INFO)
        self.assertEqual(m['build']['commit'], COMMIT)
        self.assertEqual(sorted(m['build']['files']), sorted(sm.PROVENANCE_ROLES))
        self.assertEqual(m['build']['files']['patch']['sha256'],
                         lab_common.sha256_file(b.patch))
        self.assertEqual(m['build_log_sha256'], lab_common.sha256_file(b.build_log))
        self.assertEqual(m['build']['config'], {'GGML_METAL': True,
                                                'GGML_METAL_EMBED_LIBRARY': True,
                                                'GGML_BACKEND_DL': False,
                                                'GGML_BACKEND_DIR': False})
        self.assertEqual(sm.structure_problems(m, COMMIT), [])
        self.assertEqual(sm.runtime_problems(m, launcher=b.launcher, llama_commit=COMMIT), [],
                         'the negative control of every runtime refusal below')

    def test_the_assembler_refuses_what_it_cannot_bind(self):
        def base_removed(b):
            b.base.unlink()

        def receipt_stale(b):
            sm_fixture.flip(b.core, sm_fixture.CORE_MARKER)

        def patch_edited(b):
            b.patch.write_text('another patch\n', encoding='utf-8')

        def not_embedded(b):
            p = b.build / 'CMakeCache.txt'
            p.write_text(p.read_text('utf-8').replace('GGML_METAL_EMBED_LIBRARY:BOOL=ON',
                                                      'GGML_METAL_EMBED_LIBRARY:BOOL=OFF'),
                         encoding='utf-8')

        def two_build_numbers(b):
            p = b.build / 'common' / 'build-info.cpp'
            p.write_text(p.read_text('utf-8') + 'int LLAMA_BUILD_NUMBER = 7;\n',
                         encoding='utf-8')
        cases = [
            ('closure_unresolved', base_removed, {}),
            ('receipt_members_closure', receipt_stale, {}),
            ('patch_sha256', patch_edited, {}),
            ('metal_library_not_embedded', not_embedded, {}),
            ('build_info_source', two_build_numbers, {}),
            ('build_commit', None, {'llama_commit': '0' * 40}),
            ('assembly_environment:GGML_BACKEND_PATH', None,
             {'environ': {'GGML_BACKEND_PATH': '/x'}}),
        ]
        for i, (label, damage, kw) in enumerate(cases):
            with self.subTest(label=label):
                b = self.fixture('b%d' % i)
                sm.assemble(b.launcher, b.provenance(), llama_commit=COMMIT)   # control
                if damage:
                    damage(b)
                args = dict(llama_commit=COMMIT)
                args.update(kw)
                with self.assertRaises(sm.ManifestError) as caught:
                    sm.assemble(b.launcher, b.provenance(), **args)
                self.assertTrue(any(p.startswith(label) for p in caught.exception.problems),
                                caught.exception.problems)
        # a launcher named through a symlinked directory is not canonical
        b = self.fixture('blink')
        link = self.tmp / 'linked_bin'
        os.symlink(str(b.bin), str(link))
        with self.assertRaises(sm.ManifestError) as caught:
            sm.assemble(link / 'llama-server', b.provenance(), llama_commit=COMMIT)
        self.assertIn('launcher_not_canonical', caught.exception.problems)

    def run_tool(self, argv: list) -> tuple[int, dict]:
        res = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False,
                             env=dict(os.environ))
        try:
            out = json.loads(res.stdout)
        except ValueError:
            out = {'stdout': res.stdout, 'stderr': res.stderr}
        return res.returncode, out

    def test_the_tool_writes_the_artifact_once_and_prints_its_digest(self):
        b = self.fixture()
        out = self.tmp / 'results' / 'freeze' / sm.ARTIFACT_NAME
        code, printed = self.run_tool(b.tool_argv(out))
        self.assertEqual(code, 0, printed)
        manifest, digest, problems = sm.read_artifact(out)
        self.assertEqual(problems, [])
        self.assertEqual(printed['serving_manifest_sha256'], digest)
        self.assertEqual(manifest, b.manifest(), 'the tool writes the pure function\'s object')
        self.assertEqual((printed['libraries'], printed['metal_library']), (2, 'embedded'))
        before = out.read_bytes()
        code, printed = self.run_tool(b.tool_argv(out))
        self.assertEqual(code, 2, 'write-once: a second write is refused')
        self.assertIn('WriteOnceViolation', printed['refused'])
        self.assertEqual(out.read_bytes(), before)
        code, printed = self.run_tool(b.tool_argv(self.tmp / 'results' / 'other.json'))
        self.assertEqual(code, 2)
        self.assertFalse((self.tmp / 'results' / 'other.json').exists())
        # a build it cannot bind: refused, nothing written
        b2 = self.fixture('broken')
        b2.base.unlink()
        out2 = self.tmp / 'results2' / 'freeze' / sm.ARTIFACT_NAME
        code, printed = self.run_tool(b2.tool_argv(out2))
        self.assertEqual(code, 2)
        self.assertTrue(any(p.startswith('closure_unresolved') for p in printed['refused']))
        self.assertFalse(out2.exists())


# --------------------------------------------------------------------------- #
# 4. the runtime re-verification: every fact measured now
# --------------------------------------------------------------------------- #
class RuntimeTests(TmpCase):

    def setUp(self) -> None:
        super().setUp()
        self.b = self.fixture()
        self.freeze = self.tmp / 'results' / 'freeze'
        self.digest = self.b.write_manifest(self.freeze)
        self.path = sm.artifact_path(self.freeze)

    def labels(self, launcher: Path | None = None, environ: dict | None = None,
               expected: str | None = None) -> list:
        return sm.verify_before_launch(
            self.path, self.digest if expected is None else expected,
            launcher=launcher or self.b.launcher, llama_commit=COMMIT,
            environ={} if environ is None else environ)[1]

    def test_control_the_unchanged_build_reverifies(self):
        self.assertEqual(self.labels(), [])

    def test_one_library_byte_changed_after_assembly_refuses(self):
        sm_fixture.flip(self.b.core, sm_fixture.CORE_MARKER)
        self.assertEqual(self.labels(), ['closure', 'library_sha256:libeb1c-core.0.dylib'])

    def test_the_alias_target_and_the_embedded_metal_library_are_bound(self):
        sm_fixture.flip(self.b.base, sm_fixture.BASE_MARKER)
        self.assertEqual(self.labels(), ['closure', 'library_sha256:libeb1c-base.0.1.0.dylib',
                                         'metal_library'])

    def test_a_metal_section_byte_changed_refuses(self):
        before = sm.section_bytes(str(self.b.base), '__DATA', '__ggml_metallib')[0]
        sm_fixture.flip(self.b.base, sm_fixture.METAL_MARKER)
        after = sm.section_bytes(str(self.b.base), '__DATA', '__ggml_metallib')[0]
        self.assertNotEqual(before, after, 'the byte is inside the section')
        self.assertIn('metal_library', self.labels())

    def test_a_library_added_to_the_closure_at_runtime_refuses(self):
        self.b.add_discoverable_library('libggml-eb1c.so')
        labels = self.labels()
        self.assertIn('library_added:libggml-eb1c.so', labels)
        self.assertIn('edge_added:libggml-eb1c.so', labels, 'ggml\'s backend search edge')
        # (a copy of libeb1c-core also repeats its install name, which the transcribed
        # closure refuses as well: 'closure_unresolved')

    def test_control_a_file_the_backend_search_does_not_load_is_not_a_member(self):
        shutil.copy2(str(self.b.core), str(self.b.bin / 'libother-eb1c.dylib'))
        self.assertEqual(self.labels(), [], 'not libggml-*.so and named by no load command')

    def test_an_alias_retargeted_to_identical_bytes_refuses(self):
        """Root 16:30's probe on the runtime path: same bytes, another canonical file."""
        twin = self.b.bin / 'libeb1c-base.0.1.1.dylib'
        shutil.copy2(str(self.b.base), str(twin))
        alias = self.b.bin / 'libeb1c-base.0.dylib'
        alias.unlink()
        os.symlink(twin.name, str(alias))
        labels = self.labels()
        self.assertIn('edge_moved:@rpath/libeb1c-base.0.dylib', labels)
        self.assertIn('library_added:libeb1c-base.0.1.1.dylib', labels)
        self.assertIn('library_missing:libeb1c-base.0.1.0.dylib', labels)

    def test_a_substituted_launcher_path_refuses_even_with_identical_bytes(self):
        other = self.tmp / 'copy'
        shutil.copytree(str(self.b.root), str(other), symlinks=True)
        launcher = Path(os.path.realpath(str(other))) / 'build' / 'bin' / 'llama-server'
        self.assertEqual(lab_common.sha256_file(launcher), self.b.manifest()['launcher_sha256'])
        labels = self.labels(launcher=launcher)
        self.assertIn('launcher_path', labels)
        self.assertIn('launch_context', labels)
        self.assertNotIn('launcher_sha256', labels, 'the bytes are the same; the path is not')

    def test_a_launcher_byte_changed_refuses(self):
        sm_fixture.flip(self.b.launcher, sm_fixture.LAUNCHER_MARKER)
        self.assertEqual(self.labels(), ['closure', 'launcher_sha256'])

    def test_a_relative_launcher_is_refused(self):
        self.assertEqual(self.labels(launcher=Path('llama-server')),
                         ['launcher_not_explicit'])

    def test_every_build_provenance_file_is_rehashed(self):
        def append(path: Path, text: str) -> None:
            path.write_bytes(path.read_bytes() + text.encode('utf-8'))
        cases = {
            'cmake_cache': lambda: append(self.b.build / 'CMakeCache.txt', '#x\n'),
            'build_info_source': lambda: (self.b.build / 'common' / 'build-info.cpp').write_text(
                sm_fixture.build_info_cpp(COMMIT, 6001), encoding='utf-8'),
            'patch': lambda: self.b.patch.write_text('edited\n', encoding='utf-8'),
            'build_log': lambda: self.b.build_log.write_text('edited\n', encoding='utf-8'),
            'build_receipt': lambda: append(self.b.receipt, ' '),
        }
        saved = {role: Path(p).read_bytes() for role, p in self.b.provenance().items()}
        for role, damage in cases.items():
            with self.subTest(role=role):
                damage()
                labels = self.labels()
                self.assertIn('build', labels, 'the re-hashed file differs')
                if role == 'build_info_source':
                    self.assertIn('props_build_info', labels)
                if role in ('patch', 'build_log'):
                    self.assertIn('provenance:%s_sha256' % role, labels)
                Path(self.b.provenance()[role]).write_bytes(saved[role])
                self.assertEqual(self.labels(), [], 'control: restored, it re-verifies')

    def test_a_loader_variable_in_the_server_environment_refuses(self):
        for var in ('DYLD_LIBRARY_PATH', 'GGML_BACKEND_PATH'):
            with self.subTest(var=var):
                labels = self.labels(environ={var: str(self.tmp)})
                self.assertIn('launch_context', labels)
                self.assertIn('closure_unresolved', labels)
        self.assertEqual(self.labels(environ={'PATH': '/usr/bin'}), [],
                         'control: other variables are not the loader\'s')

    def test_another_commit_refuses(self):
        labels = sm.verify_before_launch(self.path, self.digest, launcher=self.b.launcher,
                                         llama_commit='0' * 40, environ={})[1]
        self.assertEqual(labels, ['build_commit', 'commit', 'props_build_info_commit'])

    def test_a_mock_manifest_never_passes_the_runtime_check(self):
        mock_manifest = {'schema': sm.MANIFEST_SCHEMA, 'mock': True}
        self.assertEqual(sm.runtime_problems(mock_manifest, launcher=self.b.launcher,
                                             llama_commit=COMMIT), ['mock_manifest'])

    def test_the_servers_actual_build_info_is_compared(self):
        m = self.b.manifest()
        self.assertEqual(sm.props_build_info_problems(m, {'build_info': sm_fixture.BUILD_INFO}),
                         [])
        for props in ({'build_info': 'b6001-4fea119d'}, {}, None, {'build_info': None}):
            with self.subTest(props=props):
                self.assertEqual(sm.props_build_info_problems(m, props),
                                 ['props_build_info_observed'])
        self.assertEqual(sm.props_build_info_problems(None, {'build_info': 'x'}),
                         ['props_build_info_observed'])

    def test_self_comparison_mutants_are_told_apart_by_these_controls(self):
        """In process, the two mutants of ``sm_mutant_entry`` (the main() mutation controls
        are ``tests_sm_entry``): each makes a refusal above disappear."""
        original = sm.digest_problems
        self.assertEqual(self.labels(expected=''), ['config_digest_null'])
        with mock.patch.object(sm, 'digest_problems',
                               lambda found, expected: original(found, found)):
            self.assertEqual(self.labels(expected=''), [],
                             'the digest mutant hashes the artifact against itself')
        sm_fixture.flip(self.b.core, sm_fixture.CORE_MARKER)
        self.assertIn('library_sha256:libeb1c-core.0.dylib', self.labels())
        with mock.patch.object(sm, 'runtime_facts',
                               lambda manifest, **kw: sm.recorded_facts(manifest)):
            self.assertEqual(self.labels(), [],
                             'the facts mutant compares the manifest with itself')


if __name__ == '__main__':
    unittest.main()
