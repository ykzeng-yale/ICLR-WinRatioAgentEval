"""The finite controls root named for the selected-dependency gate.

Root, 2026-09-23 14:03: "Use finite synthetic or retained-metadata controls:
complete matched graph; omitted implementation/backend/transitive member;
unrelated-only inventory; wrong resolved path/search environment;
source/patch/build mismatch. No candidate binary execution, rebuild, model load
or extra historical smoke is needed for this gate work."

Every graph here is a dictionary. Nothing is executed, nothing is loaded, and no
file on this host is read: `metadata`, `exists` and `read_bytes` are supplied by
the fixture, which is what makes the traversal testable at all.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        'dependency_closure_under_test', HERE / 'dependency_closure.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Graph:
    """A synthetic dependency graph: files, their load commands, their bytes."""

    def __init__(self, files):
        self.files = dict(files)

    def metadata(self, path):
        f = self.files.get(path)
        if f is None:
            return {'error': 'no such file: %s' % path}
        if f.get('metadata_error'):
            return {'error': f['metadata_error']}
        return {'path': path, 'load_references': list(f.get('refs', [])),
                'rpaths': list(f.get('rpaths', []))}

    def exists(self, path):
        return path in self.files

    def read_bytes(self, path):
        f = self.files.get(path)
        if f is None:
            raise FileNotFoundError(path)
        return f.get('bytes', b'')


def _complete():
    """Launcher -> impl -> ggml-base, plus a metal backend. One matched graph."""
    return _Graph({
        '/cand/bin/llama-server': {
            'refs': ['@rpath/libllama-server-impl.dylib',
                     '@rpath/libggml-metal.0.dylib',
                     '/usr/lib/libSystem.B.dylib'],
            'rpaths': ['@loader_path'], 'bytes': b'LAUNCHER'},
        '/cand/bin/libllama-server-impl.dylib': {
            'refs': ['@rpath/libggml-base.0.dylib'],
            'rpaths': ['@loader_path'], 'bytes': b'IMPL'},
        '/cand/bin/libggml-metal.0.dylib': {
            'refs': ['@rpath/libggml-base.0.dylib'],
            'rpaths': ['@loader_path'], 'bytes': b'METAL'},
        '/cand/bin/libggml-base.0.dylib': {'refs': [], 'bytes': b'BASE'},
    })


class DependencyClosureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dc = _load()

    def _derive(self, g, root='/cand/bin/llama-server'):
        return self.dc.derive_closure(root, metadata=g.metadata,
                                      exists=g.exists, read_bytes=g.read_bytes)

    # -- stage one: derivation ----------------------------------------------
    def test_a_complete_matched_graph_resolves_TRANSITIVELY(self):
        """THE CONTROL, and it must be transitive: `libggml-base` is reached
        only THROUGH the implementation library, never named by the launcher.
        A direct-only walk would miss it and call the closure complete."""
        c = self._derive(_complete())
        self.assertTrue(c['resolved'], c['unresolved'])
        self.assertEqual(sorted(c['members']),
                         ['@rpath/libggml-base.0.dylib',
                          '@rpath/libggml-metal.0.dylib',
                          '@rpath/libllama-server-impl.dylib'])
        self.assertEqual(c['system_references'], ['/usr/lib/libSystem.B.dylib'])
        # system members are recorded by name and NOT pinned
        self.assertNotIn('/usr/lib/libSystem.B.dylib', c['members'])

    def test_an_OMITTED_transitive_member_leaves_the_closure_unresolved(self):
        """Root's "omitted implementation/backend/transitive member" control.
        The edge is still declared; the file is gone."""
        g = _complete()
        del g.files['/cand/bin/libggml-base.0.dylib']
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertTrue(any('libggml-base' in u.get('reference', '')
                            for u in c['unresolved']))

    def test_unreadable_metadata_is_UNRESOLVED_not_an_absent_edge(self):
        """Silence about an edge is never evidence that it is absent."""
        g = _complete()
        g.files['/cand/bin/libllama-server-impl.dylib']['metadata_error'] = \
            'otool -l failed'
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertTrue(any('otool' in u['problem'] for u in c['unresolved']))

    def test_a_reference_that_resolves_two_ways_is_ambiguous(self):
        """If the same reference can resolve to two different files, the
        selection is not bounded and must not be frozen."""
        g = _complete()
        g.files['/other/libggml-base.0.dylib'] = {'refs': [], 'bytes': b'OTHER'}
        g.files['/cand/bin/libggml-metal.0.dylib']['rpaths'] = ['/other']
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertTrue(any('ambiguous' in u['problem'] for u in c['unresolved']))

    def test_a_dlopen_member_leaves_the_closure_UNBOUNDED_without_a_policy(self):
        """Root: "account for dynamically discovered backend/plugin paths under
        the selected configuration. If that selection cannot be bounded, mark
        the closure unresolved and refuse."

        This is not hypothetical for the candidate: `libggml.0.dylib` imports
        `dlopen` and carries GGML_BACKEND_PATH, so a backend can be chosen at
        run time from a search path that NO traversal of load commands can show.
        A static closure is then not a bound on what will load, and the
        nine-member answer is the comfortable one rather than the true one.
        """
        g = _complete()
        loader = lambda path: {'dlopen': path.endswith('libggml-metal.0.dylib')}
        c = self.dc.derive_closure('/cand/bin/llama-server', metadata=g.metadata,
                                   exists=g.exists, read_bytes=g.read_bytes,
                                   dynamic_loader=loader)
        self.assertFalse(c['resolved'])
        self.assertTrue(any('import dlopen' in u['problem']
                            for u in c['unresolved']))
        self.assertEqual([Path(x).name for x in
                          c['dynamic_loading']['members_importing_dlopen']],
                         ['libggml-metal.0.dylib'])

    def test_a_declared_bound_permits_the_closure(self):
        """The control: with the search environment declared bounded, the same
        graph resolves. Without it the refusal would be unconditional and would
        prove nothing about the check."""
        g = _complete()
        loader = lambda path: {'dlopen': path.endswith('libggml-metal.0.dylib')}
        c = self.dc.derive_closure('/cand/bin/llama-server', metadata=g.metadata,
                                   exists=g.exists, read_bytes=g.read_bytes,
                                   dynamic_loader=loader,
                                   dynamic_policy={'bounded': True,
                                                   'how': 'search path pinned '
                                                          'and enumerated'})
        self.assertTrue(c['resolved'], c['unresolved'])

    def test_no_dlopen_importer_needs_no_policy(self):
        g = _complete()
        c = self.dc.derive_closure('/cand/bin/llama-server', metadata=g.metadata,
                                   exists=g.exists, read_bytes=g.read_bytes,
                                   dynamic_loader=lambda path: {'dlopen': False})
        self.assertTrue(c['resolved'], c['unresolved'])
        self.assertTrue(c['dynamic_loading']['checked'])

    def test_an_unreadable_dynamic_check_is_unresolved(self):
        g = _complete()
        c = self.dc.derive_closure('/cand/bin/llama-server', metadata=g.metadata,
                                   exists=g.exists, read_bytes=g.read_bytes,
                                   dynamic_loader=lambda path: {'error': 'nm failed'})
        self.assertFalse(c['resolved'])

    # -- stage two: verification --------------------------------------------
    def _frozen(self):
        return self._derive(_complete())

    def test_an_unchanged_graph_verifies(self):
        """THE CONTROL for stage two."""
        v = self.dc.verify_closure(self._frozen(), metadata=_complete().metadata,
                                   exists=_complete().exists,
                                   read_bytes=_complete().read_bytes)
        self.assertTrue(v['verified'], v['problems'])
        self.assertEqual(v['members_agreeing'], 3)

    def test_a_HASH_CORRECT_file_at_the_WRONG_PATH_does_not_satisfy_an_edge(self):
        """Root: "A hash-correct unrelated file cannot satisfy a required
        implementation edge."

        The bytes are identical; only the path the loader would choose has
        moved. Membership is keyed by the EDGE, because what loads is chosen by
        path, not by digest.
        """
        frozen = self._frozen()
        g = _complete()
        g.files['/elsewhere/libggml-base.0.dylib'] = {'refs': [], 'bytes': b'BASE'}
        g.files['/cand/bin/libllama-server-impl.dylib']['rpaths'] = ['/elsewhere']
        del g.files['/cand/bin/libggml-base.0.dylib']
        g.files['/cand/bin/libggml-metal.0.dylib']['rpaths'] = ['/elsewhere']
        v = self.dc.verify_closure(frozen, metadata=g.metadata, exists=g.exists,
                                   read_bytes=g.read_bytes)
        self.assertFalse(v['verified'])
        self.assertTrue(any('was frozen at' in p for p in v['problems']),
                        v['problems'])

    def test_CHANGED_BYTES_at_the_same_path_refuse(self):
        frozen = self._frozen()
        g = _complete()
        g.files['/cand/bin/libllama-server-impl.dylib']['bytes'] = b'TAMPERED'
        v = self.dc.verify_closure(frozen, metadata=g.metadata, exists=g.exists,
                                   read_bytes=g.read_bytes)
        self.assertFalse(v['verified'])
        self.assertTrue(any('changed bytes' in p for p in v['problems']))

    def test_an_UNEXPECTED_non_system_member_refuses(self):
        """Root: "unexpected non-system resolution" must refuse. A member that
        appears now and was not frozen is as much a difference as one that
        disappears."""
        frozen = self._frozen()
        g = _complete()
        g.files['/cand/bin/libextra.dylib'] = {'refs': [], 'bytes': b'EXTRA'}
        g.files['/cand/bin/llama-server']['refs'].append('@rpath/libextra.dylib')
        v = self.dc.verify_closure(frozen, metadata=g.metadata, exists=g.exists,
                                   read_bytes=g.read_bytes)
        self.assertFalse(v['verified'])
        self.assertTrue(any('not in the frozen closure' in p
                            for p in v['problems']))

    def test_an_UNRELATED_ONLY_inventory_cannot_stand_in(self):
        """Root's "unrelated-only inventory" control, and the reason my own
        default was insufficient: a frozen set that names only unrelated files
        must not verify against the real graph, and its omissions must not read
        as compliance."""
        frozen = self._frozen()
        frozen = dict(frozen, members={
            '@rpath/libunrelated.dylib': {
                'reference': '@rpath/libunrelated.dylib',
                'resolved': '/cand/bin/libunrelated.dylib',
                'sha256': 'f' * 64, 'bytes': 4}})
        g = _complete()
        v = self.dc.verify_closure(frozen, metadata=g.metadata, exists=g.exists,
                                   read_bytes=g.read_bytes)
        self.assertFalse(v['verified'])
        self.assertTrue(any('no longer reached' in p for p in v['problems']))
        self.assertTrue(any('not in the frozen closure' in p
                            for p in v['problems']))

    def test_an_UNRESOLVED_frozen_closure_cannot_be_a_requirement(self):
        g = _complete()
        del g.files['/cand/bin/libggml-base.0.dylib']
        bad = self._derive(g)
        self.assertFalse(bad['resolved'])
        v = self.dc.verify_closure(bad, metadata=_complete().metadata,
                                   exists=_complete().exists,
                                   read_bytes=_complete().read_bytes)
        self.assertFalse(v['verified'])
        self.assertTrue(any('itself unresolved' in p for p in v['problems']))

    def test_no_frozen_closure_at_all_refuses(self):
        for junk in ({}, None, {'schema': 'something else'}):
            with self.subTest(frozen=junk):
                v = self.dc.verify_closure(junk, metadata=_complete().metadata,
                                           exists=_complete().exists,
                                           read_bytes=_complete().read_bytes)
                self.assertFalse(v['verified'])


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
