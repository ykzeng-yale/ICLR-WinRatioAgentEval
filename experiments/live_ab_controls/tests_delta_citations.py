"""Citations in the repair delta's modules resolve to tracked files, and quotations are verbatim.

Review of 2026-09-23 (finding: citation problems): ``lab_schedules`` put in quotation marks a plan text
that is not the plan's; ``lab_load`` and ``lab_replay`` cited session notes that are not in the
repository, so root could not check them; ``lab_replay`` cited protocol 11.5's specification from
line 2242, leaving out item 1.  These controls read the cited files themselves.  Each has a negative
control: the same reader refuses the text the modules carried before the repair.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
PRODUCTION = ('lab_replay.py', 'lab_schedules.py', 'lab_load.py', 'lab_prepare.py')
PLAN = REPO / 'results' / 'live_ab' / 'FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json'
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
        self.assertGreater(found, 5, 'the reader finds the citations it checks')

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

    def test_the_stage_5_plan_quotation_is_verbatim(self) -> None:
        plan = json.loads(PLAN.read_text('utf-8'))

        def values(obj, key):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == key:
                        yield v
                    yield from values(v, key)
            elif isinstance(obj, list):
                for v in obj:
                    yield from values(v, key)
        (orientation,) = list(values(plan, 'stage_5_orientation'))
        doc = ' '.join((LIVE / 'lab_schedules.py').read_text('utf-8').split('"""')[1].split())
        quoted = re.search(r'``stage_5_orientation`` is "([^"]+)"', doc).group(1)
        self.assertEqual(quoted, orientation)
        lines = PLAN.read_text('utf-8').splitlines()
        self.assertIn('"stage_5_orientation": "%s"' % quoted, lines[214 - 1])
        self.assertIn('is not identified at HEAD', lines[357 - 1])
        # negative control: the text the module quoted before the repair is not the field's value
        self.assertNotEqual('orientation: deterministic prospective 15/15 schedule, NOT YET WRITTEN',
                            orientation)

    def test_the_protocol_11_5_specification_range_starts_at_its_heading(self) -> None:
        doc = (LIVE / 'lab_replay.py').read_text('utf-8')
        start, end = map(int, re.search(r'protocol_FINAL\.md:(\d+)-(\d+)``\):', doc).groups())
        lines = (LIVE / 'design' / 'protocol_FINAL.md').read_text('utf-8').splitlines()
        self.assertTrue(lines[start - 1].startswith('**Specification**'))
        self.assertTrue(lines[start + 1].startswith('1. **Tasks and strata**'))
        self.assertTrue(lines[end - 2].startswith('7. **Provenance:**'))
        self.assertEqual(lines[end], '')
        # negative control: the range cited before the repair began inside item 2, after item 1
        self.assertFalse(lines[2242 - 1].startswith(('**Specification**', '1. ')))


if __name__ == '__main__':
    unittest.main()
