"""Tests for durable_linkage_delta.py: root normalization, the file walk, and
that the linkage walk is the v2 walk (a unity unit's includes count as linked).

Run: python3 -m unittest experiments/live_ab_serving/tests_durable_linkage_delta.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import durable_linkage_delta as dld                            # noqa: E402


class RootNormalization(unittest.TestCase):
    def test_nested_build_root_is_replaced_before_its_source_root(self):
        roots = [('/private/tmp/x/src/build', '<BUILD>'), ('/private/tmp/x/src', '<SRC>')]
        got = dld._root_normalized(b'/private/tmp/x/src/build/a.s /private/tmp/x/src/b.c', roots)
        self.assertEqual(got, b'<BUILD>/a.s <SRC>/b.c')

    def test_the_tmp_spelling_of_a_private_root_is_replaced_too(self):
        roots = [('/private/tmp/x/src', '<SRC>')]
        self.assertEqual(dld._root_normalized(b'/tmp/x/src/b.c', roots), b'<SRC>/b.c')

    def test_a_content_difference_survives_normalization(self):
        a = dld._root_normalized(b'#include "/A/src/f.cpp"\nint x;', [('/A/src', '<SRC>')])
        b = dld._root_normalized(b'#include "/B/src/f.cpp"\nint y;', [('/B/src', '<SRC>')])
        self.assertNotEqual(a, b)

    def test_normalize_prefers_the_longest_root_and_needs_a_separator(self):
        roots = [('/t/src', '<SRC>'), ('/t/src/build', '<BUILD>')]
        self.assertEqual(dld.normalize('/t/src/build/x.o', roots), '<BUILD>/x.o')
        self.assertEqual(dld.normalize('/t/srcx/y.c', roots), '/t/srcx/y.c')


class FileWalk(unittest.TestCase):
    def test_skips_git_and_the_named_top_level_directories(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ('a.c', 'k.metal', 'e.s', 'x.txt', '.git/h.c', 'build/b.c', 'sub/c.h'):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text('x')
            self.assertEqual(sorted(dld._c_family(root, ('build',))),
                             ['a.c', 'e.s', 'k.metal', 'sub/c.h'])


class LinkageWalk(unittest.TestCase):
    def test_unity_unit_and_its_includes_are_linked_and_problems_kept(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(os.path.realpath(d)) / 'build'
            (b / 'U/Unity').mkdir(parents=True)
            src = Path(os.path.realpath(d)) / 'real.cpp'
            src.write_text('int f();')
            unity = b / 'U/Unity/unity_0_cxx.cxx'
            unity.write_text('#include "%s"\n' % src)
            targets = dld.lcs.TARGETS
            lines = ['rule cc', '  command = x', '']
            lines += ['build U/Unity/u.o: cc %s' % unity, '']
            lines += ['build %s: cc U/Unity/u.o' % targets[0], '']
            (b / 'build.ninja').write_text('\n'.join(lines))
            (b / 'compile_commands.json').write_text(json.dumps([
                {'directory': str(b), 'file': str(unity), 'output': 'U/Unity/u.o'}]))
            got = dld.durable_linkage(b)
            self.assertEqual(got['linked'][str(src)], [targets[0]])
            self.assertEqual(got['linked'][str(unity)], [targets[0]])
            # every other target has no statement in this fixture: kept as problems
            self.assertEqual(len(got['problems']), len(targets) - 1)


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
