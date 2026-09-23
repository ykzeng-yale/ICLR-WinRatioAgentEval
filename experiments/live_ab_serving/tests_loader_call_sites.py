"""Controls for the loader call-site deposit: build-graph linkage and classification.

Synthetic inputs only: text, and small throwaway trees under a temporary
directory (never the repo, never the candidate). The linkage walk matters
most: a walk that read only the explicit inputs would find ONE object in the
real launcher and call every call site in its static archives unlinked -- a
clean result for the wrong reason. Each agreeing case has a disagreeing twin.

The F0-F5 tests are the witnesses for review findings deposit/0-5 against the
v1 receipt. Each one fails on the v1 scanner and passes on v2. Every
classification control goes through match_lines, not through a hand-built row
(finding 2).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

EVIL = '    ggml_backend_load_all_from_path("/opt/evil");\n'
DEFAULT_CALL = 'void setup() {\n    ggml_backend_load_all();\n}\n'


class LoaderCallSiteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load()
        cls.tmp = Path(tempfile.mkdtemp(prefix='loader_call_sites_tests_'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- helpers ----------------------------------------------------------------
    def rows(self, text, suffix='.cpp'):
        """(pattern, context, classification) of every row match_lines gives.
        The suffix is passed only when it is not the default, so these controls
        also run, and fail by assertion, against v1's one-argument matcher."""
        got = (self.m.match_lines(text) if suffix == '.cpp'
               else self.m.match_lines(text, suffix))
        return [(r['pattern'], r['context'], self.m.classify_call(r)) for r in got]

    def classes(self, text, suffix='.cpp', pattern_prefix='ggml_backend_load_all'):
        return [c for p, _, c in self.rows(text, suffix) if p.startswith(pattern_prefix)]

    def world(self, files, link, missing=()):
        """A synthetic candidate tree plus a fake repo holding its manifest.

        `files` maps a path under the source tree to its text. `link` maps a
        target to the source paths linked into it: each source is compiled to
        an object and linked through a static archive named ONLY in
        LINK_LIBRARIES (the CMake shape). All ten TARGETS have a statement, so
        a 'no build statement' problem cannot mask the result. A path in
        `missing` is named by the compile commands but never written."""
        root = Path(tempfile.mkdtemp(dir=self.tmp))
        src, fake = root / 'tree', root / 'repo'
        build = src / 'build'
        build.mkdir(parents=True)
        (fake / 'results/live_ab').mkdir(parents=True)
        for rel, text in files.items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text.replace('@SRC@', str(src)))
        ninja, cc = [], []
        for i, t in enumerate(self.m.TARGETS):
            objs = []
            for j, rel in enumerate(link.get(t, ())):
                objs.append('obj/%d_%d.o' % (i, j))
                cc.append({'directory': str(build), 'file': str(src / rel),
                           'output': objs[-1], 'command': 'c++ -c'})
            if objs:
                ninja += ['build lib/a%d.a: CXX_STATIC_LIBRARY_LINKER %s' % (i, ' '.join(objs)),
                          '', 'build %s: CXX_SHARED_LIBRARY_LINKER' % t,
                          '  LINK_LIBRARIES = lib/a%d.a' % i, '']
            else:
                ninja += ['build %s: CXX_SHARED_LIBRARY_LINKER' % t, '']
        (build / 'build.ninja').write_text('\n'.join(ninja) + '\n')
        (build / 'compile_commands.json').write_text(json.dumps(cc))
        (fake / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json').write_text(json.dumps(
            {'source_and_patch': {'source_tree': str(src), 'base_commit': 'deadbeef'}}))
        return fake, src

    def run_main(self, fake):
        """The real main(), with REPO pointed at the fake repo. Returns the
        receipt it wrote, whatever that receipt is named."""
        with mock.patch.object(self.m, 'REPO', fake), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = self.m.main()
        self.assertEqual(rc, 0)
        written = sorted((fake / 'results/live_ab').glob('LOADER_CALL_SITE_EXCERPTS*.json'))
        self.assertEqual(len(written), 1)
        return json.loads(written[0].read_text())

    def established(self, doc):
        return not doc['summary']['finding'].startswith('NOT ESTABLISHED')

    # -- the linkage walk -------------------------------------------------------
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

    # -- classification, always through match_lines ----------------------------
    def test_a_default_call_and_an_EXPLICIT_directory_call_are_told_apart(self):
        self.assertEqual(self.classes('ggml_backend_load_all();'),
                         ['default-search call, no directory argument'])
        self.assertTrue(self.classes('ggml_backend_load_all_from_path(path_to_backend);')[0]
                        .startswith('EXPLICIT'))
        self.assertEqual(self.classes('ggml_backend_load_all_from_path(nullptr);'),
                         ['the default search itself (load_all forwards nullptr)'])
        self.assertEqual(self.classes('void ggml_backend_load_all() {\n}\n'),
                         ['declaration or definition, not a call'])
        self.assertEqual(self.classes(
            'GGML_API void ggml_backend_load_all_from_path(const char * dir_path);'),
            ['declaration or definition, not a call'])

    def test_an_UNFAMILIAR_call_shape_is_unclassified_not_assumed_default(self):
        """Through the real matcher now (finding 2: the v1 control built this
        row by hand, and match_lines never produced it)."""
        got = self.classes('auto f = &ggml_backend_load_all; f (')
        self.assertTrue(got)
        self.assertTrue(all(c.startswith('UNCLASSIFIED') for c in got), got)

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

    def test_a_call_right_after_a_directive_is_a_call(self):
        """tools/llama-bench/llama-bench.cpp:2232 follows an #endif."""
        self.assertEqual(self.classes('#endif\n    ggml_backend_load_all();\n'),
                         ['default-search call, no directory argument'])

    # -- F0: every linked unit is read, by the path the linkage names ----------
    def test_F0_a_linked_unit_under_build_is_scanned(self):
        """Finding 0: "22 are never scanned, including build/common/build-info.cpp
        ... a linked build/common/build-info.cpp containing
        ggml_backend_load_all_from_path("/opt/evil") still produces rc 0,
        explicit linked 0, and the same finding sentence"."""
        for body, blocked in ((EVIL, True), ('int LLAMA_BUILD_NUMBER = 1;\n', False)):
            with self.subTest(blocked=blocked):
                fake, _ = self.world(
                    {'common/arg.cpp': DEFAULT_CALL, 'build/common/build-info.cpp': body},
                    {'bin/llama-server': ['common/arg.cpp', 'build/common/build-info.cpp']})
                doc = self.run_main(fake)
                rows = [s for s in doc['sites'] if s['path'] == 'build/common/build-info.cpp']
                self.assertEqual(self.established(doc), not blocked, doc['summary'])
                self.assertEqual(
                    doc['summary']['explicit_directory_calls_linked_into_the_candidate'],
                    1 if blocked else 0)
                if blocked:
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]['linked_into'], ['bin/llama-server'])

    def test_F0_a_linked_ASSEMBLER_unit_is_read_as_text(self):
        """Finding 0: the 20 build/ggml/src/ggml-metal/autogenerated/*.s units.
        A suffix the lexer does not read is searched as text, and a load_all*
        name there (Mach-O spelling) is UNCLASSIFIED, so it blocks."""
        s_rel = 'build/ggml/src/ggml-metal/autogenerated/embed.s'
        for body, blocked in (('    bl _ggml_backend_load_all_from_path\n', True),
                              ('.section __DATA,__x\n.incbin "x.metal"\n', False)):
            with self.subTest(blocked=blocked):
                fake, _ = self.world(
                    {'common/arg.cpp': DEFAULT_CALL, s_rel: body},
                    {'bin/llama-server': ['common/arg.cpp'],
                     'bin/libggml-metal.0.24.0.dylib': [s_rel]})
                doc = self.run_main(fake)
                self.assertEqual(self.established(doc), not blocked, doc['summary'])
                rows = [s for s in doc['sites'] if s['path'] == s_rel]
                self.assertEqual([s['classification'][:12] for s in rows],
                                 ['UNCLASSIFIED'] if blocked else [])

    def test_F0_an_assembler_INCLUDE_in_a_linked_unit_is_a_problem(self):
        """The text search reads one file; an .include would pull in another."""
        s_rel = 'build/embed.s'
        for body, blocked in (('.include "more.s"\n', True), ('.incbin "x.metal"\n', False)):
            with self.subTest(blocked=blocked):
                fake, _ = self.world({'common/arg.cpp': DEFAULT_CALL, s_rel: body},
                                     {'bin/llama-server': ['common/arg.cpp', s_rel]})
                self.assertEqual(self.established(self.run_main(fake)), not blocked)

    def test_F0_an_UNREADABLE_linked_unit_is_a_linkage_problem(self):
        """Finding 0 as specified: "an unreadable linked unit is a linkage
        problem making the finding NOT ESTABLISHED"."""
        fake, _ = self.world({'common/arg.cpp': DEFAULT_CALL},
                             {'bin/llama-server': ['common/arg.cpp', 'build/gone.cpp']})
        doc = self.run_main(fake)
        self.assertFalse(self.established(doc))
        self.assertTrue(any('gone.cpp' in json.dumps(p) for p in doc['linkage_problems']),
                        doc['linkage_problems'])

    def test_F0_the_UNITY_unit_itself_is_linked_and_read(self):
        """Finding 0: the linkage names the unity unit, not only what it
        includes. Code in the unity unit itself is compiled into the object."""
        unity = 'build/src/CMakeFiles/l.dir/Unity/unity_0_cxx.cxx'
        for extra, blocked in ((EVIL, True), ('', False)):
            with self.subTest(blocked=blocked):
                fake, src = self.world(
                    {'src/a.cpp': DEFAULT_CALL,
                     unity: '/* generated */\n#include "@SRC@/src/a.cpp"\n' + extra},
                    {'bin/libllama.0.4.1.dylib': [unity]})
                doc = self.run_main(fake)
                self.assertEqual(self.established(doc), not blocked, doc['summary'])
                linked = doc['linked_translation_units']
                self.assertTrue(any(k.endswith('/src/a.cpp') for k in linked))

    # -- F1: a header row blocks unless shown not included ----------------------
    def test_F1_an_EXPLICIT_call_in_a_HEADER_blocks_the_finding(self):
        """Finding 1: "common/loader.h contains `inline void load_custom() {
        ggml_backend_load_all_from_path("/opt/evil"); }` ... yet the summary
        gives explicit_directory_calls_linked_into_the_candidate 0 and the
        finding 'every ... uses the default search'"."""
        for header, blocked in (
                ('#pragma once\ninline void load_custom() '
                 '{ ggml_backend_load_all_from_path("/opt/evil"); }\n', True),
                ('#pragma once\ninline void load_custom() { }\n', False)):
            with self.subTest(blocked=blocked):
                fake, _ = self.world(
                    {'common/loader.h': header,
                     'common/arg.cpp': '#include "loader.h"\n' + DEFAULT_CALL},
                    {'bin/libllama-common.0.4.1.dylib': ['common/arg.cpp']})
                doc = self.run_main(fake)
                self.assertEqual(self.established(doc), not blocked, doc['summary'])

    def test_F1_an_UNCLASSIFIED_occurrence_in_a_header_blocks_too(self):
        fake, _ = self.world(
            {'common/loader.h': 'static auto p = &ggml_backend_load_all_from_path;\n',
             'common/arg.cpp': DEFAULT_CALL},
            {'bin/libllama-common.0.4.1.dylib': ['common/arg.cpp']})
        self.assertFalse(self.established(self.run_main(fake)))

    def test_F1_an_INCLUDED_source_file_counts_as_a_header(self):
        """A .cpp that is not linked but is #included is compiled into its
        includer. Its twin is the tree's real case,
        examples/llama.android/.../ai_chat.cpp: an explicit call in a unit that
        is neither linked nor included does not block."""
        for includer, blocked in (('#include "impl/evil_impl.cpp"\n', True), ('', False)):
            with self.subTest(blocked=blocked):
                fake, _ = self.world(
                    {'common/impl/evil_impl.cpp': 'void f() {\n' + EVIL + '}\n',
                     'common/arg.cpp': includer + DEFAULT_CALL},
                    {'bin/libllama-common.0.4.1.dylib': ['common/arg.cpp']})
                doc = self.run_main(fake)
                self.assertEqual(self.established(doc), not blocked, doc['summary'])

    def test_F1_the_scope_no_longer_leans_on_the_dlopen_import_observation(self):
        """Finding 1: "That observation records which members import _dlopen.
        A header-inline call to ggml_backend_load_all_from_path would show up as
        an import of _ggml_backend_load_all_from_path, not _dlopen"."""
        fake, _ = self.world({'common/arg.cpp': DEFAULT_CALL},
                             {'bin/llama-server': ['common/arg.cpp']})
        doc = self.run_main(fake)
        self.assertTrue(self.established(doc))
        self.assertNotIn('Header-inline code is classified as header', doc['scope'])
        self.assertIn('not relied on here', doc['scope'])
        self.assertIn('ANY scanned header', doc['scope'])

    # -- F2: bare identifiers ----------------------------------------------------
    def test_F2_references_WITHOUT_call_parentheses_are_UNCLASSIFIED(self):
        """Finding 2: "S2 `static void (*const loader)(const char *) =
        ggml_backend_load_all_from_path; ...` and S2b `#define LOAD_FROM
        ggml_backend_load_all_from_path ...`. Both produce no row"."""
        for text in (
                'static void (*const loader)(const char *) = ggml_backend_load_all_from_path;\n'
                'void init() { loader("/opt/evil"); }\n',
                '#define LOAD_FROM ggml_backend_load_all_from_path\n'
                'void init() { LOAD_FROM("/opt/evil"); }\n',
                'void init() { auto f = &ggml_backend_load_all_from_path; f("/opt/evil"); }\n',
                'void init() { std::call_once(flag, ggml_backend_load_all); }\n',
                '#define LOAD ggml_backend_load_all_from_path(dir)\n'):
            with self.subTest(text=text):
                got = self.classes(text)
                self.assertEqual(len(got), 1, got)
                self.assertTrue(got[0].startswith('UNCLASSIFIED'), got)

    def test_F2_the_OTHER_entry_points_are_matched_bare_too(self):
        self.assertEqual([p for p, _, _ in self.rows(
            'static void *(*open_fn)(const char *, int) = dlopen;\n')], ['dlopen'])

    def test_F2_a_HAND_BUILT_row_is_not_trusted(self):
        """v1 classified the row's text; a row without the lexer's tokens is
        UNCLASSIFIED now, so a control cannot pass on a row match_lines would
        never give."""
        self.assertTrue(self.m.classify_call(
            {'pattern': 'ggml_backend_load_all', 'context': 'code',
             'text': 'ggml_backend_load_all();'}).startswith('UNCLASSIFIED'))

    def test_F2_a_function_pointer_in_a_LINKED_unit_blocks_the_finding(self):
        fake, _ = self.world(
            {'common/arg.cpp': DEFAULT_CALL,
             'src/evil.cpp': 'static void (*const loader)(const char *) = '
                             'ggml_backend_load_all_from_path;\n'
                             'void init() { loader("/opt/evil"); }\n'},
            {'bin/llama-server': ['common/arg.cpp', 'src/evil.cpp']})
        doc = self.run_main(fake)
        self.assertFalse(self.established(doc))
        self.assertEqual(doc['summary']['unclassified_calls_linked_into_the_candidate'], 1)

    # -- F3: a lexer over the whole file, every occurrence ---------------------
    def test_F3_each_WITNESS_line_yields_its_EXPLICIT_call(self):
        """Finding 3's witnesses S3, S3b, S4, S5, S6 (and S5 reversed): each
        was read as a mention or a default call in v1."""
        for name, line in (
                ('S3', 'void g() { /* see https://example.org */ '
                       'ggml_backend_load_all_from_path("/opt/evil"); }'),
                ('S3b', '    /* plugins */ ggml_backend_load_all_from_path("/opt/evil");'),
                ('S4', "    int n = 1'000; ggml_backend_load_all_from_path(\"/opt/evil\");"),
                ('S4x', "    int n = 0x1'FF; ggml_backend_load_all_from_path(\"/opt/evil\");"),
                ('S5', '    if (b) ggml_backend_load_all_from_path(nullptr); '
                       'else ggml_backend_load_all_from_path("/opt/evil");'),
                ('S5r', '    if (b) ggml_backend_load_all_from_path("/opt/evil"); '
                        'else ggml_backend_load_all_from_path(nullptr);'),
                ('S6', '    LOG("calling ggml_backend_load_all_from_path()"); '
                       'ggml_backend_load_all_from_path("/opt/evil");')):
            with self.subTest(name=name):
                got = self.classes(line)
                self.assertEqual(sum(c.startswith('EXPLICIT') for c in got), 1, got)
        both = self.classes('if (b) ggml_backend_load_all_from_path(nullptr); '
                            'else ggml_backend_load_all_from_path("/opt/evil");')
        self.assertEqual(both, ['the default search itself (load_all forwards nullptr)',
                                'EXPLICIT-DIRECTORY CALL: changes the search set'])

    def test_F3_an_UNCLEAR_lexical_state_is_UNCLASSIFIED_not_a_mention(self):
        """Finding 3: "When the lexical state is unclear, fall back to
        UNCLASSIFIED rather than 'mention'"."""
        got = self.rows('LOG("unterminated ggml_backend_load_all_from_path(dir);\n')
        self.assertEqual(got[0][1], 'unclear')
        self.assertTrue(got[0][2].startswith('UNCLASSIFIED'))

    def test_F3_raw_strings_splices_and_character_literals(self):
        # a raw string holding a call, across lines, then a real call
        self.assertEqual([c[:8] for c in self.classes(
            'auto s = R"x(\nggml_backend_load_all_from_path("/opt");\n)x";\n' + EVIL)],
            ['mention ', 'EXPLICIT'])
        # a // comment continued by a backslash-newline swallows the next line
        self.assertEqual([ctx for _, ctx, _ in self.rows(
            '// note \\\nggml_backend_load_all_from_path("/opt");\n')], ['comment'])
        # a quote inside a character literal does not open a string
        self.assertEqual([c[:8] for c in self.classes(
            "char c = '\"'; ggml_backend_load_all_from_path(\"/opt/evil\");")], ['EXPLICIT'])
        # an escaped quote does not close the string
        self.assertEqual([ctx for _, ctx, _ in self.rows(
            'puts("a \\" ggml_backend_load_all_from_path(x) \\"");')], ['string'])
        # line and column are those of the unspliced file
        rows = self.m.match_lines('int a = 1; \\\n  int b; ggml_backend_load_all();\n')
        self.assertEqual((rows[0]['line'], rows[0]['column']), (2, 10))

    def test_F3_a_raw_string_in_a_C_unit_is_UNCLEAR(self):
        """R"(...)" is C++ (a GNU C extension): its reading in a .c file
        depends on the dialect, so the state there is unclear."""
        text = 'const char *s = R"(ggml_backend_load_all_from_path(x))";\n'
        self.assertTrue(self.classes(text, '.cpp')[0].startswith('mention'))
        self.assertTrue(self.classes(text, '.c')[0].startswith('UNCLASSIFIED'))

    # -- F4: block comments across lines -----------------------------------------
    def test_F4_a_BLOCK_COMMENT_continuation_line_is_a_comment(self):
        """Finding 4: "match_lines('/*\\n  Usage: ggml_backend_load_all() once at
        startup.\\n*/') gives context 'code'", and miniaudio.h:523 and :690
        are documentation inside a block comment."""
        rows = self.m.match_lines('/*\n  Usage: ggml_backend_load_all() once at startup.\n'
                                  '*/\nint x;\n')
        self.assertEqual([(r['line'], r['context']) for r in rows], [(2, 'comment')])
        self.assertTrue(self.m.classify_call(rows[0]).startswith('mention'))
        rows = self.m.match_lines('/*\nPlatform notes\n'
                                  'devices due to `dlopen()` failing to open "libOpenSLES.so".\n'
                                  '*/\nvoid *h = dlopen(p, 0);\n')
        self.assertEqual([(r['line'], r['context']) for r in rows],
                         [(3, 'comment'), (5, 'code')])

    def test_F4_a_comment_mention_in_a_LINKED_unit_is_not_counted_as_a_call(self):
        fake, _ = self.world(
            {'common/arg.cpp': '/*\n  Usage: ggml_backend_load_all() once.\n*/\n' + DEFAULT_CALL},
            {'bin/llama-server': ['common/arg.cpp']})
        doc = self.run_main(fake)
        self.assertEqual(doc['summary']['load_all_calls_linked_into_the_candidate'], 1)

    # -- F5: the ninja parser ----------------------------------------------------
    def test_F5_ANY_indent_after_a_build_line_is_a_binding(self):
        """Finding 5: "one-space indent: linkage_from_deposit returns linked
        ['/src/main.cpp'] with problems []"."""
        for indent in (' ', '  ', '   '):
            with self.subTest(indent=repr(indent)):
                st = self.m.ninja_statements(
                    'build bin/srv: LINK main.o\n%sLINK_LIBRARIES = lib/libctx.a\n\n'
                    'build lib/libctx.a: AR ctx.o\n' % indent)
                self.assertEqual(sorted(self.m.linked_objects(st, 'bin/srv')),
                                 ['ctx.o', 'main.o'])
        block = self.m.statement_block('build bin/srv: LINK main.o\n LINK_LIBRARIES = x.a\n',
                                       'bin/srv')
        self.assertIn('LINK_LIBRARIES', block)

    def test_F5_FILE_SCOPE_variables_are_expanded(self):
        """Finding 5: "'libs = lib/libctx.a' plus 'LINK_LIBRARIES = $libs' gives
        linked_objects ['main.o'] with no UNRESOLVED marker"."""
        for ref in ('$libs', '${libs}'):
            with self.subTest(ref=ref):
                st = self.m.ninja_statements(
                    'libs = lib/libctx.a\n\nbuild bin/srv: LINK main.o\n'
                    '  LINK_LIBRARIES = %s\n\nbuild lib/libctx.a: AR ctx.o\n' % ref)
                self.assertEqual(sorted(self.m.linked_objects(st, 'bin/srv')),
                                 ['ctx.o', 'main.o'])
        st = self.m.ninja_statements('o = main.o\nbuild bin/srv: LINK $o\n')
        self.assertEqual(self.m.linked_objects(st, 'bin/srv'), ['main.o'])

    def test_F5_an_UNEXPANDED_dollar_is_a_problem_not_an_empty_list(self):
        text = 'build bin/srv: LINK main.o\n  LINK_LIBRARIES = $nope\n'
        got = self.m.linked_objects(self.m.ninja_statements(text), 'bin/srv')
        self.assertTrue(any(o.startswith('NINJA-PROBLEM:') and '$nope' in o for o in got), got)
        parsed = self.m.parse_ninja('x = $undefined\nbuild a: r b\n')
        self.assertTrue(any('$undefined' in p for p in parsed['problems']))

    def test_F5_ninja_BLOCK_rules_comments_blanks_and_double_dollars(self):
        # a comment line does not end a block; a blank line does
        st = self.m.ninja_statements('build a: r x.o\n# note\n  LINK_LIBRARIES = l.a\n\n'
                                     '  STRAY = 1\nbuild l.a: AR y.o\n')
        self.assertEqual(st['a']['variables'], {'LINK_LIBRARIES': 'l.a'})
        # `$$` at the end of a line is an escaped dollar, not a continuation
        st = self.m.ninja_statements('build a: r b $$\nbuild c: r d\n')
        self.assertEqual(sorted(st), ['a', 'c'])
        self.assertEqual(st['a']['explicit'], ['b', '$'])
        # an indented line outside any statement is reported
        self.assertTrue(self.m.parse_ninja('  STRAY = 1\n')['problems'])

    def test_F5_an_INCLUDE_is_followed_or_reported(self):
        inc = 'libs = lib/libctx.a\nbuild lib/libctx.a: AR ctx.o\n'
        text = 'include rules.ninja\nbuild bin/srv: LINK main.o\n  LINK_LIBRARIES = $libs\n'
        followed = self.m.parse_ninja(text, read_include={'rules.ninja': inc}.get)
        self.assertEqual(followed['problems'], [])
        self.assertEqual(sorted(self.m.linked_objects(followed['statements'], 'bin/srv')),
                         ['ctx.o', 'main.o'])
        self.assertTrue(any('not followed' in p for p in self.m.parse_ninja(text)['problems']))

    def test_F5_the_DEPOSIT_carries_file_scope_bindings_in_their_order(self):
        d = {'build_directory': '/b', 'targets': ['bin/srv'],
             'statements': {'bin/srv': 'build bin/srv: LINK main.o\n LINK_LIBRARIES = $libs',
                            'lib/libctx.a': 'build lib/libctx.a: AR ctx.o'},
             'statement_order': {'bin/srv': 2, 'lib/libctx.a': 3},
             'file_scope_bindings': [{'seq': 1, 'text': 'libs = lib/libctx.a'}],
             'object_to_source': [{'object': 'main.o', 'file': '/s/main.cpp'},
                                  {'object': 'ctx.o', 'file': '/s/ctx.cpp'}],
             'unity_units': []}
        r = self.m.linkage_from_deposit(d)
        self.assertEqual((sorted(r['linked']), r['problems']),
                         (['/s/ctx.cpp', '/s/main.cpp'], []))
        d['file_scope_bindings'] = []            # the disagreeing twin
        r = self.m.linkage_from_deposit(d)
        self.assertTrue(r['problems'])

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
        includes are enough -- no generated original is read. The unity unit
        is linked together with what it includes (finding 0)."""
        r = self.m.linkage_from_deposit(self._deposit())
        self.assertEqual(r['problems'], [])
        self.assertEqual(sorted(r['linked']),
                         ['/b/Unity/unity_0_cxx.cxx', '/src/a.cpp', '/src/b.cpp',
                          '/src/base.cpp', '/src/chat.cpp', '/src/main.cpp'])

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

    # -- v2 receipts: new files, v1 kept -------------------------------------------
    def test_V2_receipts_are_NEW_files_and_both_refuse_to_overwrite(self):
        m = self.m
        self.assertEqual(m.CALL_SITE_RECEIPT_V1, 'results/live_ab/LOADER_CALL_SITE_EXCERPTS.json')
        self.assertEqual(m.BUILD_RULES_V1, 'results/live_ab/LOADER_LINKAGE_BUILD_RULES.json')
        self.assertTrue(m.CALL_SITE_RECEIPT.endswith('_v2.json'))
        self.assertTrue(m.BUILD_RULES.endswith('_v2.json'))
        fake, _ = self.world({'common/arg.cpp': DEFAULT_CALL},
                             {'bin/llama-server': ['common/arg.cpp']})
        v1 = fake / m.CALL_SITE_RECEIPT_V1
        v1.write_text('{"v1": "untouched"}\n')
        with mock.patch.object(m, 'REPO', fake), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(), 0)
            self.assertEqual(m.deposit_build_rules(), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(), 2)
                self.assertEqual(m.deposit_build_rules(), 2)
        self.assertEqual(v1.read_text(), '{"v1": "untouched"}\n')
        dep = json.loads((fake / m.BUILD_RULES).read_text())
        self.assertEqual(dep['rederivation']['call_site_receipt']['path'], m.CALL_SITE_RECEIPT)
        self.assertTrue(dep['rederivation']['agrees_with_call_site_receipt'])


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
