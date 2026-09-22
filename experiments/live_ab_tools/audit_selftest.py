"""Can the audit detectors FAIL? The positive control I owed them.

Last cycle I wrote, in the uncertainty section of the issue #11 comment:

    "I do not know whether the detectors would catch a defect I had not already
     made. Every hit so far has been a shape I previously shipped. That is weak
     evidence they generalise."

That is an untested claim about my own instrument, and root's standard for the
containment probe applies to it unchanged: *a probe that passes proves nothing
unless it can fail.* Four detectors reporting a clean tree is decoration until
something shows they fire on the thing they are for.

WHAT THIS MEASURES, EXACTLY
---------------------------
Each case below is a SYNTHETIC module carrying exactly one shape. Positive cases
carry a defect and must be detected; negative cases carry the look-alike that must
NOT be reported -- the fail-safe default, the branch-determined literal, the
declaration, the provider implementing its own capability.

A miss is a false negative: the detector is blind to that shape.
A hit on a negative case is a false positive: the detector cries wolf, which is
how a checker gets switched off.

WHAT A PERFECT SCORE WOULD AND WOULD NOT SHOW
---------------------------------------------
It would show the detectors catch THE SHAPES I CAN THINK OF. It would NOT show
they catch shapes I cannot -- these cases are my own constructions, written by the
same mind that wrote the detectors, which is the exact criticism I made of my own
lifecycle fixtures: *"a fixture written by the same mind as the reader tests the
author's model of the format, not the format."* The limitation is not repaired by
this file; it is measured by it, and the number below is a floor, not a coverage
estimate.

NOTHING IS EXECUTED. The synthetic modules are parsed, never imported or run.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_ROLE = 'reporter'

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402
import tool_audit                                              # noqa: E402

REPO = HERE.parents[1]

#: (name, source, detector, expect_detected, why)
#:
#: `detector` names the list in the per-file audit that should (or should not)
#: contain the case's key.
CASES: tuple = (
    # ---- POSITIVE: each must be detected --------------------------------
    ('literal_check_unconditional',
     "def f():\n    return {'thing_matches_golden': True}\n",
     'literal_checks', True,
     'a check-shaped key with a constant value, nothing conditional around it'),

    ('literal_check_in_nested_dict',
     "def f():\n    return {'outer': {'inner_is_verified': True}}\n",
     'literal_checks', True,
     'the same shape one level down; ast.walk must reach it'),

    ('subscript_literal_check',
     "def f():\n    r = {}\n    r['signature_matches'] = True\n    return r\n",
     'subscript_literal_checks', True,
     'a final claim assigned by subscript after construction'),

    ('claim_without_read',
     "def f():\n    return {'digest_matches_config': compute()}\n",
     'claims_without_read', True,
     'a key naming config in a module that never opens config.json'),

    ('reimplementation_hashlib',
     "import hashlib\n\ndef f(b):\n    return hashlib.sha256(b).hexdigest()\n",
     'reimplementation_candidates', True,
     'a digest re-derived without importing the module that provides it'),

    ('reimplementation_ps',
     "import subprocess\n\ndef f():\n    return subprocess.run(['ps', '-Ao', 'pid'])\n",
     'reimplementation_candidates', True,
     'the quiescence question answered with its own ps scan'),

    # ---- NEGATIVE: each must NOT be detected ----------------------------
    ('negative_failsafe_initialiser',
     "def f():\n    out = {'ok': False}\n    out['ok'] = True\n    return out\n",
     'literal_checks', False,
     'the RIGHT pattern: default to failure, set on success'),

    ('negative_default_over_two_statements',
     "def f():\n    out = {}\n    out['ok'] = False\n    if g():\n        out['ok'] = True\n"
     "    return out\n",
     'subscript_literal_checks', False,
     'a default spelled over two statements, written more than once'),

    ('negative_branch_determined',
     "def f(p):\n    if not p.exists():\n        return {'receipt_is_present': False}\n"
     "    return {'x': 1}\n",
     'literal_checks', False,
     'the `if` performed the measurement'),

    ('negative_declaration',
     "def f():\n    return {'is_a_trial_episode': False, 'loaded_a_model': False}\n",
     'literal_checks', False,
     'a deliberate statement about what the run did not do'),

    ('negative_computed_value',
     "def f(a, b):\n    return {'digests_match': a == b}\n",
     'literal_checks', False,
     'the value is computed; nothing to report'),

    ('negative_claim_with_read',
     "def f():\n    cfg = open('config.json').read()\n"
     "    return {'digest_matches_config': cfg == want()}\n",
     'claims_without_read', False,
     'the module does read the source its key names'),
)


def _case_result(name: str, source: str, detector: str) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / ('%s.py' % name)
        path.write_text(source, encoding='utf-8')
        audit = tool_audit.audit_file(path)
    hits = audit.get(detector) or []
    return {'hit_count': len(hits),
            'hit_keys': sorted({h.get('key') or h.get('capability') or '?'
                                for h in hits}),
            'buckets': {k: len(v) for k, v in audit.items()
                        if isinstance(v, list) and v and k != detector}}


def run() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for name, source, detector, expect, why in CASES:
        r = _case_result(name, source, detector)
        detected = r['hit_count'] > 0
        rows.append({
            'case': name, 'detector': detector, 'polarity':
                'positive' if expect else 'negative',
            'expected_detected': expect, 'detected': detected,
            'correct': detected == expect,
            'hit_keys': r['hit_keys'],
            'other_buckets': r['buckets'],
            'why': why,
        })

    pos = [r for r in rows if r['polarity'] == 'positive']
    neg = [r for r in rows if r['polarity'] == 'negative']
    misses = [r['case'] for r in pos if not r['correct']]
    false_pos = [r['case'] for r in neg if not r['correct']]

    return {
        'schema': 'live_ab/audit_selftest-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'why': ('four detectors reporting a clean tree is decoration until '
                'something shows they fire on the thing they are for. This is the '
                'positive control I owed them, and it answers the uncertainty I '
                'posted last cycle rather than repeating it.'),
        'cases': rows,
        'positive_cases': len(pos),
        'positive_detected': sum(1 for r in pos if r['correct']),
        'false_negatives': misses,
        'negative_cases': len(neg),
        'negative_correctly_silent': sum(1 for r in neg if r['correct']),
        'false_positives': false_pos,
        'all_correct': not misses and not false_pos,
        'what_a_perfect_score_shows': (
            'that the detectors catch THE SHAPES I CAN THINK OF'),
        'what_it_does_not_show': [
            'that they catch shapes I cannot think of -- these cases are my own '
            'constructions, written by the same mind as the detectors. That is '
            'the criticism I made of my own lifecycle fixtures: a fixture written '
            'by the same mind as the reader tests the author model of the format, '
            'not the format.',
            'any coverage fraction of the real defect space. The count below is a '
            'FLOOR, not an estimate.',
            'anything about the 224 unclassified literal booleans in the '
            'production tree, which remain unread.',
        ],
        'nothing_executed': ['synthetic modules are parsed, never imported or run',
                             'no model, no server, no episode, no lock taken'],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=Path(lab_common.RESULTS_ROOT) / 'AUDIT_SELFTEST.json')
    a = ap.parse_args(argv)
    r = run()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, r)
    for row in r['cases']:
        mark = 'ok ' if row['correct'] else 'BAD'
        print('%s %-9s %-36s detected=%-5s expected=%-5s %s'
              % (mark, row['polarity'], row['case'], row['detected'],
                 row['expected_detected'],
                 ','.join(row['hit_keys'])[:34]))
    print('\npositive %d/%d detected | negative %d/%d silent | all_correct=%s'
          % (r['positive_detected'], r['positive_cases'],
             r['negative_correctly_silent'], r['negative_cases'], r['all_correct']))
    if r['false_negatives']:
        print('FALSE NEGATIVES:', ', '.join(r['false_negatives']))
    if r['false_positives']:
        print('FALSE POSITIVES:', ', '.join(r['false_positives']))
    print('written:', a.out)
    return 0 if r['all_correct'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
