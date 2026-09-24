"""Citations in the repair delta's modules resolve to tracked files.

Review of 2026-09-23 (finding: citation problems): ``lab_load`` cited session notes that are not in
the repository, so root could not check them.  These controls read the cited files themselves.  Each
has a negative control: the same reader refuses the text the module carried before the repair.

EB1+EB5 subset: this copy covers ``lab_load`` and ``lab_prepare`` only.  The ``lab_replay`` /
``lab_schedules`` parts of the original control (their modules in the citation scan, the stage-5 plan
quotation and the protocol 11.5 range) stay on session60/repair-replay with those modules, for the
next stage.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
PRODUCTION = ('lab_load.py', 'lab_prepare.py')
CITATION = re.compile(r'``((?:reviews|results|experiments|design)/[A-Za-z0-9_./-]+?\.(?:md|json|py|csv))'
                      r':(\d+)(?:-(\d+))?``')
UNTRACKED = re.compile(r'understand_[a-z0-9]+\.md|CONTRACT\.md|scratchpad')


def unresolved(text: str) -> list:
    """Every ``path:line[-line]`` citation in ``text`` whose file or line does not exist."""
    bad = []
    for m in CITATION.finditer(text):
        target = next((base / m.group(1) for base in (REPO, LIVE) if (base / m.group(1)).is_file()),
                      None)
        last = int(m.group(3) or m.group(2))
        if target is None or last > len(target.read_text('utf-8').splitlines()):
            bad.append(m.group(0))
    return bad


class CitationTests(unittest.TestCase):
    def test_every_path_line_citation_resolves(self) -> None:
        found = 0
        for name in PRODUCTION:
            with self.subTest(module=name):
                text = (LIVE / name).read_text('utf-8')
                found += len(CITATION.findall(text))
                self.assertEqual(unresolved(text), [])
        # lab_load carries 3 path:line citations, lab_prepare none; the original "> 5" also
        # counted lab_replay's 4 and lab_schedules' 3, which are not in this subset
        self.assertGreaterEqual(found, 3, 'the reader finds the citations it checks')

    def test_negative_an_unresolvable_citation_is_detected(self) -> None:
        self.assertEqual(unresolved('``reviews/NO_SUCH_REVIEW.md:1`` and '
                                    '``results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:'
                                    '999999``'),
                         ['``reviews/NO_SUCH_REVIEW.md:1``',
                          '``results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:999999``'])

    def test_no_production_module_cites_an_untracked_scratchpad_note(self) -> None:
        for name in PRODUCTION:
            with self.subTest(module=name):
                self.assertEqual(UNTRACKED.findall((LIVE / name).read_text('utf-8')), [])
        for path in sorted(HERE.glob('tests_*.py')):
            with self.subTest(control=path.name):
                doc = re.match(r'\s*"""(.*?)"""', path.read_text('utf-8'), re.S)
                self.assertEqual(UNTRACKED.findall(doc.group(1) if doc else ''), [])

    def test_negative_the_pre_repair_citations_are_detected(self) -> None:
        self.assertEqual(len(UNTRACKED.findall('(``understand_eb5.md`` Sec. 4) ``scratchpad '
                                               'understand_drivers.md`` Sec. 1')), 3)


if __name__ == '__main__':
    unittest.main()
