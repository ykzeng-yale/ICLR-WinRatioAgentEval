"""Controls for the loader call-site deposit: build-graph linkage and classification.

Synthetic text only. The linkage walk matters most: a walk that read only the
explicit inputs would find ONE object in the real launcher and call every
call site in its static archives unlinked -- a clean result for the wrong
reason. Each agreeing case has a disagreeing twin.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        'loader_call_sites_under_test', HERE / 'loader_call_sites.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NINJA = """build bin/llama-server: CXX_EXECUTABLE_LINKER main.o | bin/libimpl.dylib $
    lib/libctx.a || bin/libimpl.dylib
  LINK_LIBRARIES = -Wl,-rpath,/b/bin  lib/libctx.a  bin/libimpl.dylib  lib/libbase.a

build lib/libctx.a: CXX_STATIC_LIBRARY_LINKER ctx.o chat.o

build lib/libbase.a: CXX_STATIC_LIBRARY_LINKER base.o

build bin/libimpl.dylib: CXX_SHARED_LIBRARY_LINKER impl.o
  LINK_LIBRARIES = lib/libgone.a
"""


class LoaderCallSiteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def test_archives_named_ONLY_in_LINK_LIBRARIES_are_followed(self):
        """THE CONTROL: the launcher's explicit input is one object; its
        archives are in LINK_LIBRARIES, and their objects are linked."""
        st = self.m.ninja_statements(NINJA)
        self.assertEqual(sorted(self.m.linked_objects(st, 'bin/llama-server')),
                         ['base.o', 'chat.o', 'ctx.o', 'main.o'])

    def test_a_walk_of_EXPLICIT_inputs_alone_would_miss_them(self):
        """The disagreeing twin: without the variables, only main.o."""
        st = self.m.ninja_statements(NINJA)
        for v in st.values():
            v['variables'] = {}
        self.assertEqual(self.m.linked_objects(st, 'bin/llama-server'), ['main.o'])

    def test_shared_libraries_are_separate_members_not_followed(self):
        st = self.m.ninja_statements(NINJA)
        self.assertNotIn('impl.o', self.m.linked_objects(st, 'bin/llama-server'))

    def test_an_archive_with_NO_build_statement_is_reported_not_skipped(self):
        st = self.m.ninja_statements(NINJA)
        self.assertEqual(self.m.linked_objects(st, 'bin/libimpl.dylib'),
                         ['impl.o', 'UNRESOLVED-ARCHIVE:lib/libgone.a'])

    def test_unity_translation_units_are_followed_to_real_sources(self):
        text = ('/* generated */\n#include "/src/llama.cpp"\n'
                '  #  include "/src/llama-model.cpp"\n#include <vector>\n')
        self.assertEqual(self.m.unity_includes(text),
                         ['/src/llama.cpp', '/src/llama-model.cpp'])

    def test_a_default_call_and_an_EXPLICIT_directory_call_are_told_apart(self):
        c = self.m.classify_call
        self.assertEqual(c({'pattern': 'ggml_backend_load_all',
                            'text': 'ggml_backend_load_all();'}),
                         'default-search call, no directory argument')
        self.assertTrue(c({'pattern': 'ggml_backend_load_all_from_path',
                           'text': 'ggml_backend_load_all_from_path(path_to_backend);'})
                        .startswith('EXPLICIT'))
        self.assertEqual(c({'pattern': 'ggml_backend_load_all_from_path',
                            'text': 'ggml_backend_load_all_from_path(nullptr);'}),
                         'the default search itself (load_all forwards nullptr)')
        self.assertEqual(c({'pattern': 'ggml_backend_load_all',
                            'text': 'void ggml_backend_load_all() {'}),
                         'declaration or definition, not a call')

    def test_an_UNFAMILIAR_call_shape_is_unclassified_not_assumed_default(self):
        self.assertTrue(self.m.classify_call(
            {'pattern': 'ggml_backend_load_all',
             'text': 'auto f = &ggml_backend_load_all; f ('})
            .startswith('UNCLASSIFIED'))

    def test_every_pattern_is_matched_by_line(self):
        rows = self.m.match_lines('a\n  handle = dlopen(x, RTLD_NOW);\n'
                                  'getenv("GGML_BACKEND_PATH")\n')
        self.assertEqual([(r['line'], r['pattern']) for r in rows],
                         [(2, 'dlopen'), (3, 'GGML_BACKEND_PATH')])

    def test_a_name_in_a_LOG_STRING_is_a_mention_not_a_call(self):
        """src/llama.cpp:407 names both entry points inside a log message; the
        first draft counted it as a default-search call."""
        line = ('        LLAMA_LOG_ERROR("%s: no backends are loaded. hint: use '
                'ggml_backend_load() or ggml_backend_load_all() to load", __func__);')
        rows = self.m.match_lines(line)
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r['context'], 'string')
            self.assertTrue(self.m.classify_call(r).startswith('mention'))

    def test_a_comment_mention_and_the_real_call_on_a_later_line(self):
        rows = self.m.match_lines('    // ggml_backend_load_all() is called below\n'
                                  '    ggml_backend_load_all();\n')
        self.assertEqual([r['context'] for r in rows], ['comment', 'code'])
        self.assertEqual(self.m.classify_call(rows[1]),
                         'default-search call, no directory argument')

    # -- root 17:52: the build-rule deposit, checkable on its own -------------
    def _deposit(self):
        m = self.m
        return {'build_directory': '/b', 'targets': ['bin/llama-server'],
                'statements': {t: m.statement_block(NINJA, t)
                               for t in ('bin/llama-server', 'lib/libctx.a',
                                         'lib/libbase.a')},
                'object_to_source': [
                    {'object': 'main.o', 'file': '/src/main.cpp'},
                    {'object': 'ctx.o', 'file': '/b/Unity/unity_0_cxx.cxx'},
                    {'object': 'chat.o', 'file': '/src/chat.cpp'},
                    {'object': 'base.o', 'file': '/src/base.cpp'}],
                'unity_units': [{'path': '/b/Unity/unity_0_cxx.cxx',
                                 'includes': ['/src/a.cpp', '/src/b.cpp']}]}

    def test_the_DEPOSIT_ALONE_rederives_the_linkage(self):
        """THE CONTROL: statements (continuation lines kept), mappings and unity
        includes are enough -- no generated original is read."""
        r = self.m.linkage_from_deposit(self._deposit())
        self.assertEqual(r['problems'], [])
        self.assertEqual(sorted(r['linked']),
                         ['/src/a.cpp', '/src/b.cpp', '/src/base.cpp',
                          '/src/chat.cpp', '/src/main.cpp'])

    def test_a_deposit_MISSING_an_archive_statement_says_so(self):
        d = self._deposit()
        del d['statements']['lib/libbase.a']
        r = self.m.linkage_from_deposit(d)
        self.assertTrue(any('undeposited archive lib/libbase.a' in p
                            for p in r['problems']))

    def test_a_deposit_MISSING_a_mapping_says_so(self):
        d = self._deposit()
        d['object_to_source'] = [x for x in d['object_to_source'] if x['object'] != 'chat.o']
        r = self.m.linkage_from_deposit(d)
        self.assertTrue(any('chat.o with no deposited mapping' in p
                            for p in r['problems']))
        self.assertNotIn('/src/chat.cpp', r['linked'])

    def test_statement_blocks_keep_CONTINUATION_lines_verbatim(self):
        b = self.m.statement_block(NINJA, 'bin/llama-server')
        self.assertIn('lib/libctx.a || bin/libimpl.dylib', b)
        self.assertIn('LINK_LIBRARIES', b)
        self.assertIsNone(self.m.statement_block(NINJA, 'bin/nothing'))


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
