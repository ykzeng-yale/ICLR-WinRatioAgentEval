"""Recompute every unified-diff hunk header from the hunk BODY, and report.

Root, `reviews/pin_failure_disposition_20260923_0800.md`, ranked item 1:

    "Regenerate the patch against the pinned base, verify ordinary application,
     and refresh its digest/version record additively."

and `reviews/evidence/lifecycle_producer_review_20260923_0800.json`:

    git apply --numstat  -> "error: corrupt patch at line 283", rc 128
    git apply --check    -> "error: corrupt patch at line 283", rc 128
    git apply --recount --check -> rc 0

WHAT THAT PAIR OF RESULTS MEANS. `--recount` tells git to ignore the declared
line counts and recount from the body. It succeeded, so the hunk BODIES match
the pinned preimages exactly; what is wrong is only the arithmetic in the `@@`
headers. I edited a hunk body and did not update its header, and I said in the
same delivery that I had not verified application -- root verified it and found
this. A patch that needs `--recount` is not a patch: every ordinary consumer
(`git apply`, `patch`, a review tool, a build script) refuses it.

TWO THINGS ARE WRONG AFTER AN EDIT, not one:

  * the hunk's own counts -- old = lines marked ' ' or '-', new = ' ' or '+';
  * every LATER hunk's new-side START offset in the same file, which shifts by
    the cumulative (new - old) delta of the hunks before it.

Fixing only the first leaves a patch that parses and applies to the wrong place.

WHAT THIS TOOL DOES NOT DO. It does not check that the patch applies to the real
base tree; that needs a checkout of llama.cpp at the pinned revision, which this
host does not have. It verifies the PACKAGING is self-consistent and that the
recounted numbers are unchanged -- i.e. that this rewrite changed headers only
and no body byte. Application against the pinned base remains root's check until
a base tree exists here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AUDIT_ROLE = 'reporter'

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]

HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$')


def _counts(body: List[str]) -> Tuple[int, int]:
    """(old, new) line counts of a hunk body, by the unified-diff rules.

    A line beginning ' ' is in both sides, '-' only in old, '+' only in new. A
    '\\' line ("\\ No newline at end of file") belongs to neither count.
    """
    old = new = 0
    for line in body:
        if line.startswith('\\'):
            continue
        if line.startswith(' ') or line == '':
            old += 1
            new += 1
        elif line.startswith('-'):
            old += 1
        elif line.startswith('+'):
            new += 1
    return old, new


def recount(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (rewritten patch, per-hunk report). Bodies are never touched."""
    lines = text.split('\n')
    out: List[str] = []
    report: List[Dict[str, Any]] = []
    i = 0
    delta = 0          # cumulative (new - old) within the CURRENT file
    while i < len(lines):
        line = lines[i]
        if line.startswith('diff --git ') or line.startswith('--- '):
            if line.startswith('diff --git '):
                delta = 0          # a new file restarts the offset arithmetic
            out.append(line)
            i += 1
            continue
        m = HUNK_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue
        old_start = int(m.group(1))
        declared_old = int(m.group(2)) if m.group(2) is not None else 1
        declared_new_start = int(m.group(3))
        declared_new = int(m.group(4)) if m.group(4) is not None else 1
        tail = m.group(5)

        body: List[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if HUNK_RE.match(nxt) or nxt.startswith('diff --git ') \
                    or nxt.startswith('--- ') or nxt.startswith('index '):
                break
            # a trailing empty string from the final split is not a body line
            if nxt == '' and j == len(lines) - 1:
                break
            body.append(nxt)
            j += 1
        actual_old, actual_new = _counts(body)
        new_start = old_start + delta
        header = '@@ -%d,%d +%d,%d @@%s' % (old_start, actual_old, new_start,
                                            actual_new, tail)
        report.append({
            'line': i + 1,
            'header_before': line,
            'header_after': header,
            'declared_old': declared_old, 'actual_old': actual_old,
            'declared_new': declared_new, 'actual_new': actual_new,
            'declared_new_start': declared_new_start, 'new_start': new_start,
            'counts_agreed': declared_old == actual_old
                             and declared_new == actual_new,
            'start_agreed': declared_new_start == new_start,
        })
        out.append(header)
        out.extend(body)
        delta += actual_new - actual_old
        i = j
    return '\n'.join(out), report


def _git(args: List[str], patch: Path) -> Dict[str, Any]:
    proc = subprocess.run(['git'] + args + [str(patch)], cwd=str(REPO),
                          capture_output=True, text=True)
    return {'command': ['git'] + args + [patch.name],
            'returncode': proc.returncode,
            'stdout': proc.stdout.strip()[:800],
            'stderr': proc.stderr.strip()[:400]}


def check(patch: Path) -> Dict[str, Any]:
    """Parse checks that need no base tree.

    `git apply --numstat` PARSES the patch and prints per-file line counts
    without reading the working tree, so it is exactly the check that failed for
    root at line 283 and exactly the one this host can run. `--check` needs the
    real files and is reported for completeness, not as evidence.
    """
    plain = _git(['apply', '--numstat'], patch)
    recounted = _git(['apply', '--recount', '--numstat'], patch)
    return {
        'numstat_parses_without_recount': plain['returncode'] == 0,
        'numstat_plain': plain,
        'numstat_recounted': recounted,
        'plain_equals_recounted': (plain['returncode'] == 0
                                   and plain['stdout'] == recounted['stdout']),
        'what_this_does_not_establish': (
            'that the patch applies to the pinned base tree: that needs a '
            'checkout of llama.cpp at 4fea119de30f6a923992780f6fd5ccb0bee5d47d, '
            'which this host does not have. Root\'s --recount --check rc 0 is '
            'the evidence that the BODIES match the preimages.'),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('patch', type=Path, nargs='?',
                    default=REPO / 'experiments/live_ab_serving'
                                   '/live_ab_slot_lifecycle.patch')
    ap.add_argument('--write', action='store_true',
                    help='rewrite the headers in place')
    ap.add_argument('--out', type=Path, default=None)
    a = ap.parse_args(argv)

    before = a.patch.read_text('utf-8')
    fixed, report = recount(before)
    bad = [r for r in report if not r['counts_agreed'] or not r['start_agreed']]

    print('hunks: %d | disagreeing: %d' % (len(report), len(bad)))
    for r in report:
        flag = '' if (r['counts_agreed'] and r['start_agreed']) else '   <<< REWRITTEN'
        print('  line %-5s old %s/%s new %s/%s start %s/%s%s'
              % (r['line'], r['declared_old'], r['actual_old'],
                 r['declared_new'], r['actual_new'],
                 r['declared_new_start'], r['new_start'], flag))

    result: Dict[str, Any] = {
        'schema': 'live_ab/patch_recount-v1',
        'convention': 'deterministic-path',
        'patch': str(a.patch.relative_to(REPO)),
        'sha256_before': hashlib.sha256(before.encode()).hexdigest(),
        'hunks': report,
        'disagreeing_hunks': len(bad),
        'check_before': check(a.patch),
    }
    if a.write and fixed != before:
        a.patch.write_text(fixed, encoding='utf-8')
        result['sha256_after'] = hashlib.sha256(fixed.encode()).hexdigest()
        result['check_after'] = check(a.patch)
        # A rewrite that changed a BODY byte would be a silent corruption of the
        # thing being repaired, so it is checked rather than trusted.
        result['bodies_unchanged'] = (
            [l for l in before.split('\n') if not l.startswith('@@')]
            == [l for l in fixed.split('\n') if not l.startswith('@@')])
        print('\nrewritten: %s -> %s' % (result['sha256_before'][:12],
                                         result['sha256_after'][:12]))
        print('bodies unchanged:', result['bodies_unchanged'])
        print('parses without --recount:',
              result['check_after']['numstat_parses_without_recount'])
    if a.out:
        lab_common.write_json_atomic(a.out, result)
        print('written:', a.out)
    return 0 if (a.write or not bad) else 1


if __name__ == '__main__':
    raise SystemExit(main())
