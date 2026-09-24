"""Citations in the repair delta resolve to tracked files.

Review of 2026-09-23 (finding: citation problems): ``lab_load`` cited session notes that are not in
the repository, so root could not check them.  These controls read the cited files themselves.  Each
has a negative control: the same reader refuses the text the delta carried before its repair.

EB1+EB5 subset.  The first copy of this control scanned ``lab_load`` and ``lab_prepare`` only, and its
pattern required the ``.md`` suffix; the subset's orchestrator, event log, EB5 mutation and worker
entries and ``tests_eb5_resolution`` then cited the session's untracked EB5 map by its name
without the suffix, and the scan did not see it (review of 988baf7, K3).  The scan
now covers EVERY line the subset adds to the repository since the reviewed revision
:data:`BASE` (``git diff`` of the working tree, plus files not yet added), except this file, whose
patterns and negative controls must name what they refuse.  What it refuses: a citation of a session
note (:data:`UNTRACKED`: the session's maps, the lane contract file, a scratch path), and a
``path:line`` citation whose file or line does not exist.  "Repair contract <item>" is the NAME of
the owner's EB1/EB5 design posted to issue #11 (comment 5802890982), not a file citation, and is
not refused.  The negative
control runs the same scan over the subset as it stood at :data:`PRE_FIX` (``BASE..PRE_FIX``) and
finds the untracked citations this repair removed.

The ``lab_replay`` / ``lab_schedules`` parts of the original control (their modules in the citation
scan, the stage-5 plan quotation and the protocol 11.5 range) stay on session60/repair-replay with
those modules, for the next stage.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
PRODUCTION = ('lab_load.py', 'lab_prepare.py')
#: The reviewed revision the subset is a delta of (root 20:40 reviewed b049307).
BASE = 'b049307'
#: The subset's head before this citation repair (the review of 988baf7, K3).
PRE_FIX = '988baf7'
CITATION = re.compile(r'``((?:reviews|results|experiments|design)/[A-Za-z0-9_./-]+?\.(?:md|json|py|csv))'
                      r':(\d+)(?:-(\d+))?``')
UNTRACKED = re.compile(r'understand_[a-z0-9]+(?:\.md)?|CONTRACT\.md|scratchpad')
SELF = 'experiments/live_ab_controls/tests_delta_citations.py'


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


def _git(*args: str) -> str:
    res = subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True, text=True,
                         timeout=120, check=False)
    if res.returncode != 0:
        raise AssertionError('git %s failed: %s' % (' '.join(args), res.stderr.strip()))
    return res.stdout


def added_lines(base: str, head: str | None = None) -> dict:
    """``{repo-relative path: [added line, ...]}`` of ``git diff base [head]`` (``head`` None:
    the working tree, plus every file under ``experiments/`` not yet added).  Binary files
    and this file are skipped."""
    out: dict = {}
    current = None
    for line in _git('diff', '-U0', '--no-color', '--no-ext-diff', base,
                     *([head] if head else [])).splitlines():
        if line.startswith('+++ '):
            path = line[4:]
            current = path[2:] if path.startswith('b/') else None
            if current == SELF:
                current = None
        elif current is not None and line.startswith('+'):
            out.setdefault(current, []).append(line[1:])
    if head is None:
        for rel in _git('ls-files', '--others', '--exclude-standard', '--',
                        'experiments').splitlines():
            if rel == SELF:
                continue
            try:
                out[rel] = (REPO / rel).read_text('utf-8').splitlines()
            except (UnicodeDecodeError, OSError):
                continue
    return out


def untracked_citations(lines_by_file: dict) -> list:
    """``(path, text)`` of every added line citing a session note."""
    return [(path, line.strip()) for path, lines in sorted(lines_by_file.items())
            for line in lines if UNTRACKED.search(line)]


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

    def test_every_path_line_citation_the_subset_adds_resolves(self) -> None:
        added = added_lines(BASE)
        self.assertGreater(len(added), 20, 'the scan reads the subset\'s files')
        for path, lines in sorted(added.items()):
            with self.subTest(file=path):
                self.assertEqual(unresolved('\n'.join(lines)), [])

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

    def test_no_line_the_subset_adds_cites_an_untracked_note(self) -> None:
        """K3 (review of 988baf7): every file the subset changed, every line it added."""
        self.assertEqual(untracked_citations(added_lines(BASE)), [])

    def test_negative_the_pre_repair_citations_are_detected(self) -> None:
        self.assertEqual(len(UNTRACKED.findall('(``understand_eb5.md`` Sec. 4) ``scratchpad '
                                               'understand_drivers.md`` Sec. 1')), 3)
        # the suffix-less form the subset used, which the first pattern did not see
        self.assertEqual(UNTRACKED.findall('(understand_eb5 section 2, O:1930-1934)'),
                         ['understand_eb5'])

    def test_negative_the_subset_before_this_repair_is_refused(self) -> None:
        """The same scan over ``BASE..PRE_FIX`` finds the untracked citations K3 named: the
        orchestrator (8 lines), the event log, both EB5 entries and tests_eb5_resolution."""
        hits = untracked_citations(added_lines(BASE, PRE_FIX))
        files = {path for path, _ in hits}
        for want in ('experiments/live_ab/lab_orchestrator.py',
                     'experiments/live_ab/lab_eventlog.py',
                     'experiments/live_ab_controls/eb5_mutant_entry.py',
                     'experiments/live_ab_controls/eb5_worker_entry.py',
                     'experiments/live_ab_controls/tests_eb5_resolution.py'):
            self.assertIn(want, files)
        self.assertEqual(sum(1 for path, _ in hits
                             if path == 'experiments/live_ab/lab_orchestrator.py'), 8)


if __name__ == '__main__':
    unittest.main()
