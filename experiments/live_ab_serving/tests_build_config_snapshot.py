"""Controls for the build-configuration snapshot's parsers and agreement checks.

Every input is synthetic text. The point of the agreement check is that a
disagreement between layers is REPORTED; a check that could only ever agree
would prove nothing, so each agreeing case has a disagreeing twin.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        'build_config_snapshot_under_test', HERE / 'build_config_snapshot.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CACHE = """# This is the CMakeCache file.
//Build shared
BUILD_SHARED_LIBS:BOOL=ON
GGML_BACKEND_DL:BOOL=OFF
GGML_BACKEND_DIR:PATH=
GGML_CPU:BOOL=ON
GGML_BLAS:BOOL=ON
GGML_METAL:BOOL=ON
GGML_CUDA:BOOL=OFF
GGML_CPU_ALL_VARIANTS:BOOL=OFF
GGML_METAL_EMBED_LIBRARY:BOOL=ON
"""

NINJA = """build bin/libggml.0.24.0.dylib: CXX_SHARED_LIBRARY_LINKER__ggml_Release a.o | x
  LINK_FLAGS = -dynamiclib
  LINK_LIBRARIES = -Wl,-rpath,/b/bin  bin/libggml-cpu.0.24.0.dylib  bin/libggml-blas.0.24.0.dylib  bin/libggml-metal.0.24.0.dylib  bin/libggml-base.0.24.0.dylib

build bin/other: PHONY
"""

REG = ['GGML_BACKEND_SHARED', 'GGML_BUILD', 'GGML_USE_BLAS', 'GGML_USE_CPU',
       'GGML_USE_METAL']
METAL = ['GGML_BACKEND_BUILD', 'GGML_METAL_EMBED_LIBRARY']


class BuildConfigSnapshotTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def _checks(self, cache=CACHE, reg=REG, metal=METAL, ninja=NINJA,
                bdir_defined=False, embed=12, variants=()):
        links = self.m.link_libraries(
            self.m.ninja_build_block(ninja, 'bin/libggml.0.24.0.dylib'))
        return {c['check']: c for c in self.m.agreement_checks(
            self.m.parse_cmake_cache(cache), reg, metal, links, bdir_defined,
            embed, list(variants))}

    def test_the_CONSISTENT_configuration_agrees_on_every_layer(self):
        """THE CONTROL: without it, the refusals below prove nothing."""
        c = self._checks()
        self.assertTrue(all(v['agrees'] is True for v in c.values()),
                        {k: v for k, v in c.items() if v['agrees'] is not True})

    def test_a_cache_saying_OFF_with_a_DL_compile_define_DISAGREES(self):
        """A configured OFF is not a compiled OFF."""
        c = self._checks(reg=REG + ['GGML_BACKEND_DL'])
        self.assertIs(c['GGML_BACKEND_DL']['agrees'], False)

    def test_a_compiled_BACKEND_DIR_with_an_empty_cache_value_DISAGREES(self):
        c = self._checks(bdir_defined=True)
        self.assertIs(c['GGML_BACKEND_DIR']['agrees'], False)

    def test_an_enabled_backend_that_is_NOT_REGISTERED_disagrees(self):
        c = self._checks(reg=[d for d in REG if d != 'GGML_USE_METAL'])
        self.assertIs(c['enabled backends == GGML_USE_* on the registry']['agrees'],
                      False)

    def test_a_backend_missing_from_the_LINK_rule_disagrees(self):
        c = self._checks(ninja=NINJA.replace('  bin/libggml-metal.0.24.0.dylib', ''))
        self.assertIs(c['libggml links exactly the enabled backends']['agrees'], False)

    def test_EMBED_on_in_the_cache_but_NO_symbols_in_the_bytes_disagrees(self):
        """The cache and the compile flags can both say embedded while the
        measured library carries nothing; the bytes are the last word."""
        c = self._checks(embed=0)
        self.assertIs(c['GGML_METAL_EMBED_LIBRARY']['agrees'], False)

    def test_an_UNREADABLE_symbol_table_is_not_agreement(self):
        c = self._checks(embed=None)
        self.assertIsNone(c['GGML_METAL_EMBED_LIBRARY']['agrees'])

    def test_CPU_variant_files_present_with_variants_OFF_disagrees(self):
        c = self._checks(variants=['libggml-cpu-apple_m1.so'])
        self.assertIs(c['GGML_CPU_ALL_VARIANTS']['agrees'], False)

    def test_a_setting_ABSENT_from_the_cache_is_not_agreement(self):
        c = self._checks(cache=CACHE.replace('GGML_BACKEND_DL:BOOL=OFF\n', ''))
        self.assertIsNone(c['GGML_BACKEND_DL']['agrees'])

    def test_compile_definitions_refuse_an_ambiguous_source(self):
        entries = [{'file': '/a/ggml/src/ggml-backend-reg.cpp', 'command': 'cc -DX'},
                   {'file': '/b/ggml/src/ggml-backend-reg.cpp', 'command': 'cc -DY'}]
        r = self.m.compile_definitions(entries, 'ggml/src/ggml-backend-reg.cpp')
        self.assertIn('error', r)

    def test_compile_definitions_read_both_flag_spellings(self):
        entries = [{'file': '/a/ggml/src/ggml-backend-reg.cpp',
                    'arguments': ['cc', '-DGGML_USE_CPU', '-D', 'GGML_USE_METAL', '-c']}]
        r = self.m.compile_definitions(entries, 'ggml/src/ggml-backend-reg.cpp')
        self.assertEqual(r['definitions'], ['GGML_USE_CPU', 'GGML_USE_METAL'])

    def test_discovery_enumerates_the_superset_including_symlinks(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'libggml-metal-x.so').write_bytes(b'A')
            (d / 'libggml-cpu.so').write_bytes(b'B')
            (d / 'libggml-metal.0.dylib').write_bytes(b'C')     # not a candidate
            os.symlink(d / 'libggml-cpu.so', d / 'libggml-rpc.so')
            r = self.m.discovery_candidates(d)
            names = [c['name'] for c in r['candidates']]
            self.assertEqual(names, ['libggml-cpu.so', 'libggml-metal-x.so',
                                     'libggml-rpc.so'])
            self.assertTrue([c for c in r['candidates']
                             if c['name'] == 'libggml-rpc.so'][0]['is_symlink'])

    def test_an_EMPTY_location_records_absence_not_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.m.discovery_candidates(Path(d))
            self.assertTrue(r['exists'])
            self.assertEqual(r['candidates'], [])


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
