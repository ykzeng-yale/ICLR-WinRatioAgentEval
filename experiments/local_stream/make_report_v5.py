"""Round 13 owner-document cleanup of the coding-stream report. REPORT-ONLY: no model call, no analysis rerun, no git
command, no number changed. Source results/local_stream/report_v4.md (reviewed by the root at 01f2381; byte-unchanged);
output report_v5.md and report_v5_manifest.json (sha256 digests of replaced passages; the text is in this generator).

Usage: .venv/bin/python experiments/local_stream/make_report_v5.py
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / 'results' / 'local_stream'
SRC, OUT, MAN = RD / 'report_v4.md', RD / 'report_v5.md', RD / 'report_v5_manifest.json'
REVIEWED_HEAD = '01f2381940fcf5bc57129f1498382cb40f3ea741'
ROOT_REVIEW = 'a2eee58526f0ce3cef913fa8156ae34601d1b597'

REPLACEMENTS = [
    ('Definitions pointer names the governing addendum first',
     'Definitions: `protocol_addendum_round10.md` (which supersedes the conflicting sentences of the Round 9 addendum).',
     'Definitions: `protocol_addendum_round12.md` first (it governs and withdraws several Round 10 sentences on the R1 filtration, the cluster t interval and the pass table), then `protocol_addendum_round10.md` (which supersedes the conflicting sentences of the Round 9 addendum).'),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    t = SRC.read_text(); applied = []
    for label, old, new in REPLACEMENTS:
        assert t.count(old) == 1, label
        t = t.replace(old, new); applied.append(dict(label=label, old_sha256=hashlib.sha256(old.encode()).hexdigest(), new_sha256=hashlib.sha256(new.encode()).hexdigest()))
    marker = '> **Round 12 report-only correction (2026-09-19).**'
    assert t.count(marker) == 1
    note = ("> **Round 13 owner-document cleanup (2026-09-19).** This file is `report_v4.md` (accepted for the named Round 12 corrections by the root session at `%s`; review on main at `%s`, `reviews/round13_integration_disposition.md`; kept byte-unchanged) with one pointer corrected so that the governing Round 12 addendum is named first. No number, table or figure changed. The root paper uses the raw observations with its own analysis; the model-dependent intervals of this report are excluded from it.\n>\n" % (REVIEWED_HEAD[:7], ROOT_REVIEW[:7]))
    t = t.replace(marker, note + marker)
    OUT.write_text(t)
    MAN.write_text(json.dumps(dict(kind='owner-document cleanup (Round 13); report-only', source='results/local_stream/report_v4.md', source_sha256=sha(SRC),
                                   output='results/local_stream/report_v5.md', output_sha256=sha(OUT), reviewed_owner_head=REVIEWED_HEAD, root_review_commit=ROOT_REVIEW,
                                   replacements=applied, note='digests only; passage text is in the generator'), indent=2) + '\n')
    print('wrote', OUT.relative_to(REPO), MAN.relative_to(REPO))


if __name__ == '__main__':
    build()
