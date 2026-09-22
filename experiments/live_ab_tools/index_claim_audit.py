"""Check what the results index CLAIMS against the receipts it cites.

Two cycles ago I had to withdraw a line from `results/SESSION60_RESULTS_INDEX.md`:
it said "both trees clean on all four detectors ... 0 unbucketed literal checks"
when the cited receipt said 27. The receipt was right the whole time; I had
grepped one summary line and described the whole run from it.

That is a document root reads, and I now have a demonstrated error rate in it. I
proposed this check on issue #11 rather than running it unilaterally, because
"this is really the follow-up to a defect, not new work" is the rationalisation I
asked to be watched for. Root did not object, so the default is in force.

WHAT IS CHECKED, AND HOW COMPLETE EACH CHECK IS
-----------------------------------------------
``cited_paths``    COMPLETE over the index. Every `results/live_ab/*.json` path
                   the index names must exist. A citation to a file that is not
                   there is a defect regardless of what was claimed about it.

``digests``        COMPLETE over the index. Every 64-hex string, and every 16-hex
                   prefix, must appear in some committed receipt or in config.
                   This catches a fabricated, mistyped or stale hash -- the exact
                   failure mode of the timestamp I once supplied from inference.

``numeric_claims`` NOT COMPLETE, and this is the honest part. The index is prose;
                   there is no general parse of "the sentence asserts X about
                   receipt Y". So the headline claims are enumerated BY HAND in
                   ``CLAIMS`` below and the script does the comparison. The
                   enumeration is mine, so a claim I failed to list is a claim
                   this does not check -- the same limitation as the audit
                   self-test, stated rather than glossed.

NOTHING IS EXECUTED and nothing is rewritten. It reads the index and the receipts
and reports disagreements.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_ROLE = 'reporter'

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]
INDEX = REPO / 'results' / 'SESSION60_RESULTS_INDEX.md'
RESULTS = Path(lab_common.RESULTS_ROOT)

#: (claim, receipt, dotted json path or callable, expected)
#:
#: Enumerated by hand from the index's headline numbers. `path` may be a dotted
#: key chain, or a callable taking the loaded receipt.
CLAIMS: tuple = (
    ('freeze: 14 of 26 keys resolved', 'FREEZE_REACHABILITY_v3.json',
     'resolved_offline_count', 14),
    ('freeze: 12 still required', 'FREEZE_REACHABILITY_v3.json',
     'still_required_count', 12),
    ('freeze split: 2 resolvable_now', 'FREEZE_REACHABILITY_v3.json',
     lambda d: len(d['answer']['resolvable_now']), 2),
    ('freeze split: 1 offline_work_owed', 'FREEZE_REACHABILITY_v3.json',
     lambda d: len(d['answer']['offline_work_owed']), 1),
    ('freeze split: 9 execution_blocked', 'FREEZE_REACHABILITY_v3.json',
     lambda d: len(d['answer']['execution_blocked']), 9),
    ('lock: 5 distinct lock files', 'LOCK_TOPOLOGY_v2.json',
     lambda d: d['paths']['distinct_lock_file_count'], 5),
    ('lock: does not conform to one lock file', 'LOCK_TOPOLOGY_v2.json',
     'conforms_to_one_lock_file', False),
    ('lock: 2 implementations', 'LOCK_TOPOLOGY_v2.json',
     'implementation_count', 2),
    ('two-worker: 16 attempts paired', 'TWO_WORKER_CONTAINMENT_20260922T141527Z.json',
     lambda d: d['per_attempt_control']['attempts_paired'], 16),
    ('two-worker: 15 controlled denials', 'TWO_WORKER_CONTAINMENT_20260922T141527Z.json',
     lambda d: d['per_attempt_control']['controlled_denials'], 15),
    ('two-worker: 1 denied in both', 'TWO_WORKER_CONTAINMENT_20260922T141527Z.json',
     lambda d: d['per_attempt_control']['denied_in_both'], 1),
    ('two-worker: 0 reachable inside sandbox',
     'TWO_WORKER_CONTAINMENT_20260922T141527Z.json',
     lambda d: d['per_attempt_control']['reachable_inside_sandbox'], 0),
    ('two-worker: verdict PASS', 'TWO_WORKER_CONTAINMENT_20260922T141527Z.json',
     'verdict', 'PASS'),
    ('two-worker FAIL run: lock control did not acquire',
     'TWO_WORKER_CONTAINMENT_20260922T134847Z.json', 'lock_control_acquired', False),
    ('two-worker FAIL run: verdict FAIL',
     'TWO_WORKER_CONTAINMENT_20260922T134847Z.json', 'verdict', 'FAIL'),
    ('self-test: 6 positive detected', 'AUDIT_SELFTEST.json',
     'positive_detected', 6),
    ('self-test: 6 negative silent', 'AUDIT_SELFTEST.json',
     'negative_correctly_silent', 6),
    ('self-test: all correct', 'AUDIT_SELFTEST.json', 'all_correct', True),
    ('production audit: 32 files', 'PRODUCTION_AUDIT_v7.json', 'files_audited', 32),
    ('production audit: 0 claims without read', 'PRODUCTION_AUDIT_v7.json',
     'claims_without_read_count', 0),
    ('production audit: 27 literal checks (the CORRECTED figure)',
     'PRODUCTION_AUDIT_v7.json', 'literal_check_count', 27),
    ('production audit: 4 reimplementation candidates (the CORRECTED figure)',
     'PRODUCTION_AUDIT_v7.json', 'reimplementation_candidate_count', 4),
    ('tools audit: 0 literal checks', 'TOOL_AUDIT_v12.json',
     'literal_check_count', 0),
    ('tools audit: 0 claims without read', 'TOOL_AUDIT_v12.json',
     'claims_without_read_count', 0),
    ('licence: coder blob 11343 bytes', 'LICENSE_EVIDENCE_v2.json',
     lambda d: d['servers']['coder']['retained']['bytes'], 11343),
    ('licence: t3 served a model-card declaration, not a licence blob',
     'LICENSE_EVIDENCE_v2.json',
     lambda d: d['servers']['t3']['retained']['evidence_kind'],
     'model_card_declaration'),
    ('containment probe: 15 denied filesystem operations',
     'CONTAINMENT_PROBE_RECEIPT.json',
     lambda d: d['denied_attempts_corrected']['denied_filesystem_operations'], 15),
)


def _resolve(receipt: Dict[str, Any], path) -> Any:
    if callable(path):
        return path(receipt)
    cur: Any = receipt
    for part in str(path).split('.'):
        cur = cur[part]
    return cur


def check_cited_paths(text: str) -> Dict[str, Any]:
    cited = sorted(set(re.findall(r'results/live_ab/[A-Za-z0-9_.\-]+\.json', text)))
    missing = [c for c in cited if not (REPO / c).is_file()]
    return {'cited': len(cited), 'missing': missing,
            'complete_over_the_index': True,
            'all_present': not missing}


def check_digests(text: str) -> Dict[str, Any]:
    """Every hex string in the index must occur in a committed receipt or config."""
    # CORPUS WIDTH IS THE CHECK'S REACH. The first version read only
    # results/live_ab/*.json plus config, and reported two digests unbacked that
    # were in fact recorded in evidence/ and results/live_ab_validation_v2/. A
    # digest check whose corpus omits where digests live manufactures false
    # alarms -- the same defect as the capability table that named one of several
    # valid providers. Every committed JSON under results/ and evidence/ now, plus
    # config; reviews/ is root-owned and read only, never written.
    corpus = []
    for root in (REPO / 'results', REPO / 'evidence'):
        if root.is_dir():
            for f in sorted(root.rglob('*.json')):
                corpus.append(f.read_text('utf-8', errors='replace'))
    corpus.append((LAB / 'config.json').read_text('utf-8'))
    blob = '\n'.join(corpus)

    full = sorted(set(re.findall(r'\b[0-9a-f]{64}\b', text)))
    short = sorted(set(re.findall(r'\b[0-9a-f]{16}\b', text)))
    unbacked_full = [h for h in full if h not in blob]
    # a 16-hex prefix is backed if any 64-hex digest in the corpus starts with it
    corpus_digests = set(re.findall(r'\b[0-9a-f]{64}\b', blob))
    unbacked_short = [h for h in short
                      if not any(d.startswith(h) for d in corpus_digests)]
    return {
        'full_digests': len(full), 'unbacked_full': unbacked_full,
        'short_prefixes': len(short), 'unbacked_short': unbacked_short,
        'complete_over_the_index': True,
        'all_backed': not unbacked_full and not unbacked_short,
        'why': ('a hash in a report that appears in no receipt is fabricated, '
                'mistyped or stale. I once supplied a timestamp from inference '
                'and had to retract it to a peer; this is the mechanical version '
                'of that check.'),
    }


def check_numeric_claims() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for claim, receipt_name, path, expected in CLAIMS:
        f = RESULTS / receipt_name
        row: Dict[str, Any] = {'claim': claim, 'receipt': receipt_name,
                               'expected': expected}
        if not f.is_file():
            row.update(ok=False, problem='receipt absent')
            rows.append(row)
            continue
        try:
            got = _resolve(json.loads(f.read_text('utf-8')), path)
        except Exception as exc:                               # noqa: BLE001
            row.update(ok=False, problem='%s: %s' % (type(exc).__name__, exc))
            rows.append(row)
            continue
        row.update(actual=got, ok=(got == expected))
        rows.append(row)
    bad = [r for r in rows if not r['ok']]
    return {'checked': len(rows), 'disagreements': bad,
            'all_agree': not bad,
            'complete_over_the_index': False,
            'completeness_caveat': (
                'the claims are enumerated BY HAND from the index prose. A claim '
                'I failed to list is a claim this does not check. Same limitation '
                'as the audit self-test: the cases are mine.'),
            'rows': rows}


def report() -> Dict[str, Any]:
    text = INDEX.read_text('utf-8')
    paths = check_cited_paths(text)
    digests = check_digests(text)
    numeric = check_numeric_claims()
    clean = paths['all_present'] and digests['all_backed'] and numeric['all_agree']
    return {
        'schema': 'live_ab/index_claim_audit-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'index': lab_common.display_path(INDEX),
        'index_lines': text.count('\n'),
        'why': ('two cycles ago a line in this index claimed "both trees clean ... '
                '0 unbucketed literal checks" while the cited receipt said 27. '
                'Proposed on issue #11 and not objected to.'),
        'cited_paths': paths,
        'digests': digests,
        'numeric_claims': numeric,
        'all_checks_agree': clean,
        'what_this_does_not_establish': [
            'that every claim in the index is true -- only the enumerated ones '
            'and the two complete mechanical checks',
            'that the receipts themselves are right; this compares the report to '
            'the receipt, not the receipt to the world',
            'anything about the prose claims that carry no number',
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=RESULTS / 'INDEX_CLAIM_AUDIT.json')
    a = ap.parse_args(argv)
    r = report()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, r)
    p, d, n = r['cited_paths'], r['digests'], r['numeric_claims']
    print('cited receipt paths : %d, missing %d' % (p['cited'], len(p['missing'])))
    for m in p['missing']:
        print('   MISSING:', m)
    print('digests             : %d full + %d prefixes, unbacked %d'
          % (d['full_digests'], d['short_prefixes'],
             len(d['unbacked_full']) + len(d['unbacked_short'])))
    for h in d['unbacked_full'] + d['unbacked_short']:
        print('   UNBACKED:', h)
    print('numeric claims      : %d checked, %d disagree'
          % (n['checked'], len(n['disagreements'])))
    for row in n['disagreements']:
        print('   DISAGREE: %s\n             expected %r, receipt says %r %s'
              % (row['claim'], row['expected'], row.get('actual'),
                 row.get('problem', '')))
    print('\nall_checks_agree:', r['all_checks_agree'])
    print('written:', a.out)
    return 0 if r['all_checks_agree'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
