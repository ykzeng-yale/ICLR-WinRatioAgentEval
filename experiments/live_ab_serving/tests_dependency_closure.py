"""The finite controls root named for the selected-dependency gate.

Root, 2026-09-23 14:03: "Use finite synthetic or retained-metadata controls:
complete matched graph; omitted implementation/backend/transitive member;
unrelated-only inventory; wrong resolved path/search environment;
source/patch/build mismatch. No candidate binary execution, rebuild, model load
or extra historical smoke is needed for this gate work."

Root, 14:41, on `6b83860`: carry the dynamic contract through verification;
fail closed on unsupported dependency metadata (the `LC_REEXPORT_DYLIB` probe);
key an edge by its parent/resolution context (the two-parent
`@loader_path/helper` probe), preserving rejection where one context truly
cannot select.

Every graph here is a dictionary and every `otool` output a string. Nothing is
executed, nothing is loaded, and no file on this host is read: every reader is
supplied by the fixture, which is what makes the traversal testable at all.
"""

from __future__ import annotations

import importlib.util
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
    """A synthetic dependency graph: files, load commands, bytes, `dlopen`
    imports, and what each search location holds."""

    def __init__(self, files, dirs=None, links=None):
        self.files = dict(files)
        self.dirs = dict(dirs or {})
        # spelling -> target: a symlink. `realpath` follows it; `exists` and the
        # readers see through it, exactly as the filesystem would.
        self.links = dict(links or {})

    def realpath(self, path):
        seen = set()
        while path in self.links:
            if path in seen:
                raise OSError('symlink loop at %s' % path)
            seen.add(path)
            path = self.links[path]
        return path

    def metadata(self, path):
        f = self.files.get(self.realpath(path))
        if f is None:
            return {'error': 'no such file: %s' % path}
        if f.get('metadata_error'):
            return {'error': f['metadata_error']}
        refs = [r if isinstance(r, tuple) else ('LC_LOAD_DYLIB', r)
                for r in f.get('refs', [])]
        return {'path': path, 'install_name': f.get('id'),
                'load_references': [{'command': c, 'reference': r} for c, r in refs],
                'rpaths': list(f.get('rpaths', []))}

    def exists(self, path):
        try:                               # as os.path.exists: False, not raise
            return self.realpath(path) in self.files
        except OSError:
            return False

    def read_bytes(self, path):
        f = self.files.get(self.realpath(path))
        if f is None:
            raise FileNotFoundError(path)
        return f.get('bytes', b'')

    def dynamic_loader(self, path):
        f = self.files.get(path) or {}
        if f.get('nm_error'):
            return {'error': f['nm_error']}
        return {'dlopen': bool(f.get('dlopen'))}

    def enumerate_dir(self, d):
        if d in self.dirs:
            return {'directory': d, 'exists': True, 'candidates': list(self.dirs[d])}
        return {'directory': d, 'exists': False, 'candidates': []}


LAUNCHER = '/cand/bin/llama-server'


def _ctx(**kw):
    c = {'executable_invoked_path': LAUNCHER, 'cwd': '/run',
         'compiled_backend_dir': None, 'environment': {}}
    c.update(kw)
    return c


def _complete():
    """Launcher -> impl -> ggml-base, plus a metal backend, plus libggml, which
    imports dlopen -- the candidate's real shape, in miniature."""
    return _Graph({
        LAUNCHER: {
            'refs': ['@rpath/libllama-server-impl.dylib', '@rpath/libggml.0.dylib',
                     '@rpath/libggml-metal.0.dylib', '/usr/lib/libSystem.B.dylib'],
            'rpaths': ['@loader_path'], 'bytes': b'LAUNCHER'},
        '/cand/bin/libllama-server-impl.dylib': {
            'refs': ['@rpath/libggml-base.0.dylib'], 'rpaths': ['@loader_path'],
            'id': '@rpath/libllama-server-impl.dylib', 'bytes': b'IMPL'},
        '/cand/bin/libggml.0.dylib': {
            'refs': ['@rpath/libggml-base.0.dylib'], 'rpaths': ['@loader_path'],
            'id': '@rpath/libggml.0.dylib', 'dlopen': True, 'bytes': b'GGML'},
        '/cand/bin/libggml-metal.0.dylib': {
            'refs': ['@rpath/libggml-base.0.dylib'], 'rpaths': ['@loader_path'],
            'id': '@rpath/libggml-metal.0.dylib', 'bytes': b'METAL'},
        '/cand/bin/libggml-base.0.dylib': {
            'refs': [], 'id': '@rpath/libggml-base.0.dylib', 'bytes': b'BASE'},
    }, dirs={'/cand/bin': [], '/run': []})


def _readers(g, **kw):
    r = {'metadata': g.metadata, 'exists': g.exists, 'read_bytes': g.read_bytes,
         'dynamic_loader': g.dynamic_loader, 'enumerate_dir': g.enumerate_dir,
         'launch_context': _ctx(), 'realpath': g.realpath}
    r.update(kw)
    return r


def _alias_graph():
    """The candidate's real shape for ggml-base: the load command names
    `libggml-base.0.dylib`, a same-directory symlink to the versioned file."""
    g = _complete()
    g.files['/cand/bin/libggml-base.0.24.0.dylib'] = g.files.pop(
        '/cand/bin/libggml-base.0.dylib')
    g.links['/cand/bin/libggml-base.0.dylib'] = '/cand/bin/libggml-base.0.24.0.dylib'
    return g


OTOOL_DYLIB = """/x/libggml.0.dylib:
Load command 0
      cmd LC_SEGMENT_64
  cmdsize 72
  segname __TEXT
Load command 1
          cmd LC_ID_DYLIB
      cmdsize 48
         name @rpath/libggml.0.dylib (offset 24)
   time stamp 1 Wed Dec 31 19:00:01 1969
Load command 2
          cmd LC_RPATH
      cmdsize 32
         path /cand/bin (offset 12)
Load command 3
          cmd LC_LOAD_DYLIB
      cmdsize 56
         name @rpath/libggml-base.0.dylib (offset 24)
Load command 4
          cmd LC_LOAD_DYLIB
      cmdsize 56
         name /usr/lib/libSystem.B.dylib (offset 24)
Load command 5
      cmd LC_CODE_SIGNATURE
  cmdsize 16
"""


class DependencyClosureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dc = _load()

    def _derive(self, g, root=LAUNCHER, **kw):
        return self.dc.derive_closure(root, **_readers(g, **kw))

    def _problems(self, c):
        return ' | '.join(u['problem'] for u in c['unresolved'])

    # -- stage one: derivation ----------------------------------------------
    def test_a_complete_matched_graph_resolves_TRANSITIVELY(self):
        """THE CONTROL, and it must be transitive: `libggml-base` is reached
        only THROUGH other libraries, never named by the launcher. A
        direct-only walk would miss it and call the closure complete."""
        c = self._derive(_complete())
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertEqual(sorted(Path(f).name for f in c['files']),
                         ['libggml-base.0.dylib', 'libggml-metal.0.dylib',
                          'libggml.0.dylib', 'libllama-server-impl.dylib',
                          'llama-server'])
        self.assertEqual(c['member_count'], 4)
        self.assertEqual(len(c['files']['/cand/bin/libggml-base.0.dylib']['reached_by']),
                         3)
        self.assertEqual(c['system_references'], ['/usr/lib/libSystem.B.dylib'])
        self.assertNotIn('/usr/lib/libSystem.B.dylib', c['files'])
        self.assertTrue(c['dynamic_loading']['bounded'])

    def test_an_OMITTED_transitive_member_leaves_the_closure_unresolved(self):
        g = _complete()
        del g.files['/cand/bin/libggml-base.0.dylib']
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertTrue(any('libggml-base' in u.get('reference', '')
                            for u in c['unresolved']))

    def test_unreadable_metadata_is_UNRESOLVED_not_an_absent_edge(self):
        g = _complete()
        g.files['/cand/bin/libllama-server-impl.dylib']['metadata_error'] = \
            'otool -l failed'
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('otool', self._problems(c))

    # -- root item 3: an edge is (parent, command, reference) ----------------
    def test_ROOTS_PROBE_two_loader_path_helpers_from_different_parents_resolve(self):
        """Root, 14:41: "Two legitimate `@loader_path/helper` references from
        different parent directories are collapsed under the reference text and
        rejected as ambiguous. This is a conservative false refusal." Two
        parents, two edges, two files -- no ambiguity."""
        g = _Graph({
            LAUNCHER: {'refs': ['/a/liba.dylib', '/b/libb.dylib'], 'bytes': b'L'},
            '/a/liba.dylib': {'refs': ['@loader_path/helper'], 'bytes': b'A'},
            '/b/libb.dylib': {'refs': ['@loader_path/helper'], 'bytes': b'B'},
            '/a/helper': {'bytes': b'HA'}, '/b/helper': {'bytes': b'HB'},
        })
        c = self._derive(g)
        self.assertTrue(c['resolved'], self._problems(c))
        helpers = sorted(e['resolved'] for e in c['edges'].values()
                         if e['reference'] == '@loader_path/helper')
        self.assertEqual(helpers, ['/a/helper', '/b/helper'])

    def test_the_same_rpath_reference_from_TWO_PARENTS_is_two_edges(self):
        """Two parents, two edges, two distinct files -- not an ambiguity."""
        g = _complete()
        g.files['/other/libggml-base.0.dylib'] = {
            'refs': [], 'id': '@rpath/libggml-base-other.0.dylib', 'bytes': b'OTHER'}
        g.files['/cand/bin/libggml-metal.0.dylib']['rpaths'] = ['/other']
        c = self._derive(g)
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertIn('/other/libggml-base.0.dylib', c['files'])

    def test_ROOTS_CHOICE_two_canonical_files_sharing_an_INSTALL_NAME_refuse(self):
        """Root, 16:30: "root chooses refusal for distinct canonical files
        sharing an install name" until the loader's selection among them is
        specified. Was recorded and passed at `ab38e61`."""
        g = _complete()
        g.files['/other/libggml-base.0.dylib'] = {
            'refs': [], 'id': '@rpath/libggml-base.0.dylib', 'bytes': b'OTHER'}
        g.files['/cand/bin/libggml-metal.0.dylib']['rpaths'] = ['/other']
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('install name @rpath/libggml-base.0.dylib', self._problems(c))

    def test_an_ALIAS_and_its_target_are_ONE_file_not_a_duplicate(self):
        """The control for the refusal above: a same-directory symlink and its
        target are one canonical file, so one install name, one file."""
        g = _alias_graph()
        g.files['/cand/bin/libggml-metal.0.dylib']['refs'] = [
            '@rpath/libggml-base.0.24.0.dylib']                # names the target
        c = self._derive(g)
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertEqual(c['duplicate_install_names'], {})

    def test_rejection_is_PRESERVED_where_one_context_cannot_select(self):
        """Root: "Preserve rejection where the same supported context truly has
        unresolved selection." A relative rpath, a relative reference and a bare
        leaf name are each resolved by dyld against the working directory or
        fallback paths, so the same parent context does not pick one file."""
        for label, mutate in (
                ('relative rpath', lambda g: g.files[LAUNCHER].update(
                    rpaths=['lib'])),
                ('relative reference', lambda g: g.files[LAUNCHER]['refs'].append(
                    'lib/libx.dylib')),
                ('bare leaf name', lambda g: g.files[LAUNCHER]['refs'].append(
                    'libx.dylib'))):
            with self.subTest(label):
                g = _complete()
                mutate(g)
                c = self._derive(g)
                self.assertFalse(c['resolved'])
                self.assertTrue(any(('relative' in u['problem'])
                                    for u in c['unresolved']), self._problems(c))

    def test_a_shadowed_later_hit_is_recorded_not_loaded(self):
        g = _complete()
        g.files['/cand/lib2/libggml-base.0.dylib'] = {'bytes': b'SHADOW'}
        g.files['/cand/bin/libllama-server-impl.dylib']['rpaths'] = [
            '@loader_path', '/cand/lib2']
        c = self._derive(g)
        self.assertTrue(c['resolved'], self._problems(c))
        e = c['edges'][self.dc.edge_key('/cand/bin/libllama-server-impl.dylib',
                                        'LC_LOAD_DYLIB', '@rpath/libggml-base.0.dylib')]
        self.assertEqual(e['resolved'], '/cand/bin/libggml-base.0.dylib')
        self.assertEqual(e['shadowed'], ['/cand/lib2/libggml-base.0.dylib'])

    # -- root item 2: fail closed on metadata --------------------------------
    def test_the_REAL_FORMAT_parses_completely(self):
        """THE CONTROL for the parser: an ordinary dylib's commands, every one
        of them classified, nothing refused."""
        m = self.dc.parse_load_commands(OTOOL_DYLIB, ncmds=6)
        self.assertNotIn('error', m)
        self.assertEqual(m['install_name'], '@rpath/libggml.0.dylib')
        self.assertEqual(m['rpaths'], ['/cand/bin'])
        self.assertEqual([r['reference'] for r in m['load_references']],
                         ['@rpath/libggml-base.0.dylib', '/usr/lib/libSystem.B.dylib'])

    def test_ROOTS_PROBE_a_REEXPORTED_dependency_is_an_edge(self):
        """Root's parser probe: an `LC_REEXPORT_DYLIB` dependency was silently
        omitted, so a missing member became `resolved=True` with zero
        members."""
        text = OTOOL_DYLIB.replace('cmd LC_LOAD_DYLIB\n      cmdsize 56\n         '
                                   'name @rpath/libggml-base',
                                   'cmd LC_REEXPORT_DYLIB\n      cmdsize 56\n'
                                   '         name @rpath/libggml-base')
        m = self.dc.parse_load_commands(text, ncmds=6)
        self.assertNotIn('error', m)
        self.assertIn({'command': 'LC_REEXPORT_DYLIB',
                       'reference': '@rpath/libggml-base.0.dylib'},
                      m['load_references'])
        # ... and a MISSING re-exported member now leaves the closure unresolved
        g = _complete()
        g.files[LAUNCHER]['refs'].append(('LC_REEXPORT_DYLIB', '@rpath/libgone.dylib'))
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertTrue(any(u.get('command') == 'LC_REEXPORT_DYLIB'
                            for u in c['unresolved']))

    def test_every_dependency_command_is_an_edge(self):
        for cmd in self.dc.DEPENDENCY_COMMANDS:
            with self.subTest(cmd):
                g = _complete()
                g.files[LAUNCHER]['refs'].append((cmd, '@rpath/libgone.dylib'))
                c = self._derive(g)
                self.assertFalse(c['resolved'])

    def test_an_UNSUPPORTED_command_refuses(self):
        """`LC_DYLD_ENVIRONMENT` sets loader variables from inside the binary.
        A deny-list would let it pass; the closed list refuses it."""
        text = OTOOL_DYLIB.replace('cmd LC_CODE_SIGNATURE', 'cmd LC_DYLD_ENVIRONMENT')
        m = self.dc.parse_load_commands(text, ncmds=6)
        self.assertIn('unsupported load command LC_DYLD_ENVIRONMENT', m['error'])
        text = OTOOL_DYLIB.replace('cmd LC_CODE_SIGNATURE', 'cmd ?(0x80000099)')
        self.assertIn('unsupported', self.dc.parse_load_commands(text, ncmds=6)['error'])

    def test_a_MALFORMED_dependency_record_refuses(self):
        text = OTOOL_DYLIB.replace('name @rpath/libggml-base.0.dylib (offset 24)',
                                   'nmae garbled')
        self.assertIn('no readable name',
                      self.dc.parse_load_commands(text, ncmds=6)['error'])
        text = OTOOL_DYLIB.replace('path /cand/bin (offset 12)', 'path')
        self.assertIn('no readable path',
                      self.dc.parse_load_commands(text, ncmds=6)['error'])

    def test_a_COMMAND_COUNT_mismatch_refuses(self):
        """Truncated output lists fewer commands than the header declares; the
        missing ones cannot be assumed harmless."""
        self.assertIn('declares 7',
                      self.dc.parse_load_commands(OTOOL_DYLIB, ncmds=7)['error'])

    def test_the_mach_header_must_be_ONE_readable_header(self):
        one = ('/x:\nMach header\n      magic  cputype cpusubtype  caps    filetype '
               'ncmds sizeofcmds      flags\n 0xfeedfacf 16777228          0  0x00  '
               '         6    22       1648 0x00110085\n')
        self.assertEqual(self.dc.parse_mach_header(one), {'ncmds': 22})
        self.assertIn('error', self.dc.parse_mach_header(one + one))
        self.assertIn('error', self.dc.parse_mach_header('/x:\nMach header\n'))

    # -- root item 1: the dynamic contract, measured -------------------------
    def test_a_MODELLED_dlopen_importer_under_an_enumerated_search_resolves(self):
        """THE CONTROL for the dynamic half: libggml imports dlopen, every
        location the pinned source searches is enumerated and empty, and the
        environment sets no loader variable. `bounded` is computed, not
        supplied."""
        c = self._derive(_complete())
        self.assertTrue(c['resolved'], self._problems(c))
        d = c['dynamic_loading']
        self.assertEqual([Path(x).name for x in d['members_importing_dlopen']],
                         ['libggml.0.dylib'])
        self.assertEqual([r['directory'] for r in d['search_locations']],
                         ['/cand/bin', '/run'])
        self.assertTrue(d['bounded'])

    def test_an_UNMODELLED_dlopen_importer_refuses(self):
        g = _complete()
        g.files['/cand/bin/libggml-metal.0.dylib']['dlopen'] = True
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('search is not modelled', self._problems(c))
        self.assertFalse(c['dynamic_loading']['bounded'])

    def test_a_MISSING_reader_or_context_is_a_check_NOT_MADE(self):
        """Root: `verify_closure` "re-derives without a dynamic reader or
        policy, allowing verified=True while making zero dynamic checks."
        Leaving a reader out is now a refusal, never a pass."""
        for missing in ('dynamic_loader', 'enumerate_dir', 'launch_context'):
            with self.subTest(missing):
                c = self._derive(_complete(), **{missing: None})
                self.assertFalse(c['resolved'])
                self.assertFalse(c['dynamic_loading']['bounded'])

    def test_an_unreadable_dynamic_check_is_unresolved(self):
        g = _complete()
        g.files['/cand/bin/libggml.0.dylib']['nm_error'] = 'nm failed'
        self.assertFalse(self._derive(g)['resolved'])

    def test_a_DISCOVERABLE_backend_is_bound_and_its_dependencies_walked(self):
        """Root: enumerate "the complete possible candidate set, including
        scoring candidates and the ordinary recursively resolved
        implementation-library dependencies." A candidate in cwd is not refused
        for existing -- it becomes an edge, and what IT loads is walked."""
        g = _complete()
        g.files['/run/libggml-vulkan-x.so'] = {
            'refs': ['/opt/vk/libvk.dylib'], 'bytes': b'VK'}
        g.files['/opt/vk/libvk.dylib'] = {'bytes': b'VKDEP'}
        g.dirs['/run'] = [{'name': 'libggml-vulkan-x.so', 'path': '/run/libggml-vulkan-x.so',
                           'resolved': '/run/libggml-vulkan-x.so', 'is_symlink': False}]
        c = self._derive(g)
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertIn('/run/libggml-vulkan-x.so', c['files'])
        self.assertIn('/opt/vk/libvk.dylib', c['files'])

    def test_a_discoverable_candidate_that_CANNOT_be_pinned_refuses(self):
        g = _complete()
        g.dirs['/run'] = [{'name': 'libggml-x.so', 'path': '/run/libggml-x.so',
                           'error': 'FileNotFoundError: dangling symlink'}]
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('cannot be pinned', self._problems(c))

    def test_an_UNENUMERABLE_search_location_refuses(self):
        g = _complete()
        g.enumerate_dir = lambda d: {'directory': d, 'error': 'PermissionError'}
        self.assertFalse(self._derive(g)['resolved'])

    def test_LOADER_and_BACKEND_PATH_environment_refuse_other_GGML_is_recorded(self):
        for env, ok in (({'DYLD_LIBRARY_PATH': '/x'}, False),
                        ({'DYLD_INSERT_LIBRARIES': '/x.dylib'}, False),
                        ({'GGML_BACKEND_PATH': '/cand/bin'}, False),
                        ({'GGML_METAL_NO_RESIDENCY': '1'}, True),
                        ({'HOME': '/Users/x'}, True)):
            with self.subTest(env=env):
                c = self._derive(_complete(), launch_context=_ctx(environment=env))
                self.assertIs(c['resolved'], ok, self._problems(c))
        c = self._derive(_complete(), launch_context=_ctx(
            environment={'HOME': '/Users/x', 'GGML_METAL_NO_RESIDENCY': '1'}))
        self.assertEqual(c['launch_context']['environment'],
                         {'GGML_METAL_NO_RESIDENCY': '1'})

    def test_the_EXECUTABLE_PATH_must_be_the_root_and_canonical(self):
        c = self._derive(_complete(), launch_context=_ctx(
            executable_invoked_path='/elsewhere/llama-server'))
        self.assertFalse(c['resolved'])
        c = self._derive(_complete(), realpath=lambda p: '/private' + p)
        self.assertFalse(c['resolved'])
        self.assertIn('not canonical', self._problems(c))
        c = self._derive(_complete(), launch_context=_ctx(cwd='relative/dir'))
        self.assertFalse(c['resolved'])

    def test_a_COMPILED_backend_dir_is_searched_first(self):
        g = _complete()
        g.dirs['/opt/backends'] = []
        c = self._derive(g, launch_context=_ctx(compiled_backend_dir='/opt/backends'))
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertEqual([r['directory'] for r in c['dynamic_loading']['search_locations']],
                         ['/opt/backends', '/cand/bin', '/run'])

    # -- stage two: verification --------------------------------------------
    def _frozen(self):
        c = self._derive(_complete())
        self.assertTrue(c['resolved'], self._problems(c))
        return c

    def _verify(self, frozen, g=None, **kw):
        g = g or _complete()
        r = _readers(g, **kw)
        return self.dc.verify_closure(frozen, **r)

    def test_an_unchanged_graph_verifies(self):
        """THE CONTROL for stage two."""
        v = self._verify(self._frozen())
        self.assertTrue(v['verified'], v['problems'])
        self.assertEqual(v['edges_agreeing'], v['edges_checked'])
        self.assertTrue(v['dynamic_loading_now']['bounded'])

    def test_ROOTS_PROBE_verification_without_a_dynamic_reader_REFUSES(self):
        """Root, 14:41: verification "re-derives without a dynamic reader or
        policy, allowing verified=True while making zero dynamic checks." Under
        the old code this call verified."""
        for missing in ('dynamic_loader', 'enumerate_dir', 'launch_context'):
            with self.subTest(missing):
                v = self._verify(self._frozen(), **{missing: None})
                self.assertFalse(v['verified'])

    def test_a_CHANGED_launch_context_refuses(self):
        v = self._verify(self._frozen(), launch_context=_ctx(cwd='/elsewhere'))
        self.assertFalse(v['verified'])
        self.assertTrue(any('launch context field cwd' in p for p in v['problems']))

    def test_GGML_BACKEND_PATH_set_at_preflight_refuses(self):
        v = self._verify(self._frozen(), launch_context=_ctx(
            environment={'GGML_BACKEND_PATH': '/tmp/libggml-evil.so'}))
        self.assertFalse(v['verified'])

    def test_a_backend_that_APPEARS_in_a_search_location_after_freezing_refuses(self):
        """Root: "do not infer that a directory remained unchanged from an old
        inventory." The search is re-enumerated at preflight."""
        g = _complete()
        g.files['/cand/bin/libggml-cuda.so'] = {'bytes': b'NEW'}
        g.dirs['/cand/bin'] = [{'name': 'libggml-cuda.so',
                                'path': '/cand/bin/libggml-cuda.so',
                                'resolved': '/cand/bin/libggml-cuda.so'}]
        v = self._verify(self._frozen(), g)
        self.assertFalse(v['verified'])
        self.assertTrue(any('not in the frozen closure' in p for p in v['problems']))

    def test_a_HASH_CORRECT_file_at_the_WRONG_PATH_does_not_satisfy_an_edge(self):
        """Root: "A hash-correct unrelated file cannot satisfy a required
        implementation edge." Same bytes; only the path the loader would choose
        has moved."""
        frozen = self._frozen()
        g = _complete()
        g.files['/elsewhere/libggml-base.0.dylib'] = dict(
            g.files.pop('/cand/bin/libggml-base.0.dylib'))
        for f in ('/cand/bin/libllama-server-impl.dylib', '/cand/bin/libggml.0.dylib',
                  '/cand/bin/libggml-metal.0.dylib'):
            g.files[f]['rpaths'] = ['/elsewhere']
        v = self._verify(frozen, g)
        self.assertFalse(v['verified'])
        self.assertTrue(any('was frozen at' in p for p in v['problems']), v['problems'])

    def test_CHANGED_BYTES_at_the_same_path_refuse(self):
        frozen = self._frozen()
        g = _complete()
        g.files['/cand/bin/libllama-server-impl.dylib']['bytes'] = b'TAMPERED'
        v = self._verify(frozen, g)
        self.assertFalse(v['verified'])
        self.assertTrue(any('changed bytes' in p for p in v['problems']))

    def test_an_UNEXPECTED_non_system_member_refuses(self):
        frozen = self._frozen()
        g = _complete()
        g.files['/cand/bin/libextra.dylib'] = {'refs': [], 'bytes': b'EXTRA'}
        g.files[LAUNCHER]['refs'].append('@rpath/libextra.dylib')
        v = self._verify(frozen, g)
        self.assertFalse(v['verified'])
        self.assertTrue(any('not in the frozen closure' in p for p in v['problems']))

    def test_an_UNRELATED_ONLY_inventory_cannot_stand_in(self):
        """A frozen set naming only unrelated files must not verify against the
        real graph, and its omissions must not read as compliance."""
        frozen = dict(self._frozen())
        key = self.dc.edge_key(LAUNCHER, 'LC_LOAD_DYLIB', '@rpath/libunrelated.dylib')
        frozen['edges'] = {key: {'parent': LAUNCHER, 'command': 'LC_LOAD_DYLIB',
                                 'reference': '@rpath/libunrelated.dylib',
                                 'resolved': '/cand/bin/libunrelated.dylib'}}
        frozen['files'] = {'/cand/bin/libunrelated.dylib': {'sha256': 'f' * 64}}
        v = self._verify(frozen)
        self.assertFalse(v['verified'])
        self.assertTrue(any('no longer reached' in p for p in v['problems']))
        self.assertTrue(any('not in the frozen closure' in p for p in v['problems']))

    def test_an_UNRESOLVED_frozen_closure_cannot_be_a_requirement(self):
        g = _complete()
        del g.files['/cand/bin/libggml-base.0.dylib']
        bad = self._derive(g)
        self.assertFalse(bad['resolved'])
        v = self._verify(bad)
        self.assertFalse(v['verified'])
        self.assertTrue(any('itself unresolved' in p for p in v['problems']))

    def test_no_frozen_closure_or_an_OLD_SCHEMA_one_refuses(self):
        """A v1 closure carries no dynamic contract and a v2 closure no
        canonical targets, so neither can be verified under this one."""
        for junk in ({}, None, {'schema': 'something else'},
                     {'schema': 'live_ab/dependency_closure-v1', 'resolved': True},
                     {'schema': 'live_ab/dependency_closure-v2', 'resolved': True}):
            with self.subTest(frozen=junk):
                self.assertFalse(self._verify(junk)['verified'])

    # -- root 16:30: canonical targets ----------------------------------------
    def test_a_SAME_DIRECTORY_alias_binds_its_CANONICAL_target(self):
        """THE CONTROL, and the candidate's real shape: the file that will be
        mapped is the versioned target, and it is what the closure pins."""
        c = self._derive(_alias_graph())
        self.assertTrue(c['resolved'], self._problems(c))
        self.assertIn('/cand/bin/libggml-base.0.24.0.dylib', c['files'])
        self.assertNotIn('/cand/bin/libggml-base.0.dylib', c['files'])
        e = c['edges'][self.dc.edge_key('/cand/bin/libllama-server-impl.dylib',
                                        'LC_LOAD_DYLIB', '@rpath/libggml-base.0.dylib')]
        self.assertEqual(e['resolved'], '/cand/bin/libggml-base.0.dylib')
        self.assertEqual(e['canonical'], '/cand/bin/libggml-base.0.24.0.dylib')
        v = self.dc.verify_closure(c, **_readers(_alias_graph()))
        self.assertTrue(v['verified'], v['problems'])

    def test_ROOTS_PROBE_a_RETARGETED_alias_with_IDENTICAL_BYTES_refuses(self):
        """Root's witness at `ab38e61`: the canonical target of a selected
        dependency changed while its spelling, bytes and metadata did not, and
        verification returned verified=true. A changed target cannot be
        certified merely because its bytes match."""
        frozen = self._derive(_alias_graph())
        self.assertTrue(frozen['resolved'], self._problems(frozen))
        g = _alias_graph()
        g.files['/cand/bin/libggml-base.0.25.0.dylib'] = dict(
            g.files['/cand/bin/libggml-base.0.24.0.dylib'])      # same bytes
        del g.files['/cand/bin/libggml-base.0.24.0.dylib']
        g.links['/cand/bin/libggml-base.0.dylib'] = '/cand/bin/libggml-base.0.25.0.dylib'
        v = self.dc.verify_closure(frozen, **_readers(g))
        self.assertFalse(v['verified'])
        self.assertTrue(any('canonical target' in p for p in v['problems']),
                        v['problems'])

    def test_ROOTS_PROBE_an_alias_into_ANOTHER_DIRECTORY_refuses(self):
        """Root's exact spelling: `/cand/bin/helper.dylib` -> `/payload/A/...`.
        The loader context of the spelling (/cand/bin) and of the target
        (/payload/A) differ, so the alias is outside the supported profile --
        and a later retarget to /payload/B can never have been frozen."""
        g = _complete()
        g.files['/payload/A/helper.dylib'] = {'refs': [], 'bytes': b'HELPER'}
        g.links['/cand/bin/helper.dylib'] = '/payload/A/helper.dylib'
        g.files[LAUNCHER]['refs'].append('@rpath/helper.dylib')
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('different directory', self._problems(c))

    def test_a_DISCOVERED_backend_alias_into_another_directory_refuses(self):
        g = _complete()
        g.files['/opt/x/libggml-vk.so'] = {'bytes': b'VK'}
        g.links['/run/libggml-vk.so'] = '/opt/x/libggml-vk.so'
        g.dirs['/run'] = [{'name': 'libggml-vk.so', 'path': '/run/libggml-vk.so',
                           'resolved': '/opt/x/libggml-vk.so'}]
        c = self._derive(g)
        self.assertFalse(c['resolved'])
        self.assertIn('different directory', self._problems(c))

    def test_an_UNREADABLE_canonical_target_refuses(self):
        """The spelling exists, but its canonical target cannot be read."""
        g = _alias_graph()

        def realpath(p):
            if p == '/cand/bin/libggml-base.0.dylib':
                raise OSError('permission denied reading the link')
            return g.realpath(p)
        c = self._derive(g, realpath=realpath)
        self.assertFalse(c['resolved'])
        self.assertIn('could not be read', self._problems(c))


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
