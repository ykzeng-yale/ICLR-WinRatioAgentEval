"""Tests for source_tree_three_checks.py's pure helpers.

Run: python3 -m unittest experiments/live_ab_serving/tests_source_tree_three_checks.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_tree_three_checks as s3                          # noqa: E402


class Helpers(unittest.TestCase):
    def test_patch_files_come_from_the_plus_lines(self):
        diff = ('--- a/x/one.h\n+++ b/x/one.h\n@@ -1 +1 @@\n-a\n+b\n'
                '--- a/two.cpp\n+++ b/two.cpp\n@@ -1 +1 @@\n-c\n+d\n')
        self.assertEqual(s3.patch_files(diff), ['two.cpp', 'x/one.h'])

    def test_the_real_patch_modifies_exactly_two_files(self):
        text = (s3.REPO / s3.PATCH_REL).read_text()
        self.assertEqual(s3.patch_files(text), ['tools/server/server-common.h',
                                                'tools/server/server-context.cpp'])

    def test_porcelain_must_be_exactly_the_patched_files_unstaged(self):
        files = ['a', 'b']
        self.assertTrue(s3.porcelain_matches([' M b', ' M a'], files))
        self.assertFalse(s3.porcelain_matches([' M a', ' M b', '?? c'], files))   # extra
        self.assertFalse(s3.porcelain_matches([' M a'], files))                    # missing
        self.assertFalse(s3.porcelain_matches(['M  a', ' M b'], files))            # staged


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
