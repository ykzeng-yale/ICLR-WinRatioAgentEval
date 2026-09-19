"""Round 13 owner-document cleanup of the tau2_open report (precision items of the root's Round 13 review). REPORT-ONLY:
no model call, no analysis rerun, no git command, no number changed.

Source: results/tau2_open/report_final_v2.md (reviewed by the root at 01f2381; kept byte-unchanged).
Output: results/tau2_open/report_final_v3.md and report_final_v3_manifest.json. The manifest holds sha256 DIGESTS of each
replaced passage; the passage TEXT is in this generator.

Usage: .venv/bin/python experiments/tau2_open/make_report_final_v3.py
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / 'results' / 'tau2_open'
SRC, OUT, MAN = RD / 'report_final_v2.md', RD / 'report_final_v3.md', RD / 'report_final_v3_manifest.json'
REVIEWED_HEAD = '01f2381940fcf5bc57129f1498382cb40f3ea741'
ROOT_REVIEW = 'a2eee58526f0ce3cef913fa8156ae34601d1b597'

REPLACEMENTS = [
    ('item 1: precedence of governing documents (header)',
     'Binding documents, in order of precedence: `experiments/tau2_open/protocol_addendum_round10.md` and `experiments/tau2_open/deviation_1_erratum.md` (',
     'Binding documents, in order of precedence: `experiments/tau2_open/protocol_addendum_round12.md` (Round 12/13: governs wherever it conflicts with anything below, including withdrawn Round 10 wording), then `experiments/tau2_open/protocol_addendum_round10.md` and `experiments/tau2_open/deviation_1_erratum.md` ('),
    ('item 1: governing text of section 12',
     'Governing text: `experiments/tau2_open/protocol_addendum_round10.md`.',
     'Governing text: `experiments/tau2_open/protocol_addendum_round12.md` first (it withdraws and corrects several Round 10 sentences), then `experiments/tau2_open/protocol_addendum_round10.md`.'),
    ('item 5: banner describes the replacements and the manifest accurately',
     'with three passages replaced and this status section added, in response to',
     'with the wording replacements and status pointers listed below and this status section added (Round 12: 15 declared replacements and six local status pointers; Round 13: the further replacements of `make_report_final_v3.py`), in response to'),
    ('item 5: manifest holds digests, generator holds text',
     'hashes and the replaced passages: `report_final_v2_manifest.json`;',
     'source / output hashes and sha256 digests of each replaced passage: `report_final_v2_manifest.json` and `report_final_v3_manifest.json` (the passage text itself is in the generators `make_report_final_v2.py` and `make_report_final_v3.py`);'),
    ('item 5 / token-role precision: summary sentence',
     "(the root's independent log reconstruction gives at least 246,284 additional generated arm-A tokens, `reviews/round12_integration_ledger.md` on main)",
     "(the root's independent log reconstruction gives a lower bound of 246,284 additional A-collection generated tokens; the split between agent and user-simulator roles is unavailable; `reviews/round12_integration_ledger.md` on main)"),
    ('item 2: placeholder sensitivity sentence',
     'No descriptive observation of this report depends on the treatment.',
     '(Round 13 correction.) The planned retained-record analysis remains the primary analysis; its E1 and E2 net benefit are unchanged in this sensitivity, whereas resource summaries and some denominators change (success 15/96 instead of 15/98 for arm A, and the component means above).'),
    ('item 3: abstention scoped to the primary rules (a)',
     'returns "no decision" on all interval-based rules, and says so rather than forcing a ranking.',
     'returns "no decision" on the primary-rule interval-based comparisons, and says so rather than forcing a ranking. (Round 13 correction: some alternative hierarchy / tolerance rows of the section 4 sensitivity table select B; those are separate, model-dependent sensitivity outputs and are excluded from the root integration, section 0.)'),
    ('item 3: abstention scoped to the primary rules (b)',
     '(Pareto on means and utility weights pick B) and **uncertainty-aware rules** (all abstain) on the same data.',
     '(Pareto on means and utility weights pick B) and the **primary-rule uncertainty-aware comparisons** (which abstain) on the same data; alternative-hierarchy sensitivity rows are kept separate (section 4).'),
    ('item 4: radius extrapolation is specific to this boundary and rho',
     'With this rho the R1 radius reaches 0.03 only at n = 12,094 pairs (N). That is the honest price of the assumption-free reading here.',
     'For this normal-mixture boundary and this rho the radius reaches 0.03 at n = 12,094 pairs (N). (Round 13 correction.) This is arithmetic for one boundary and one rho under the nominal coin model of section 12.1; it is not a lower bound for other methods and not a general cost of inference without a task-sampling model. The coin model is itself an assumption, even though no task-sampling model is used.'),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    t = SRC.read_text(); applied = []
    for label, old, new in REPLACEMENTS:
        assert t.count(old) == 1, 'expected exactly one match: ' + label
        t = t.replace(old, new)
        applied.append(dict(label=label, old_sha256=hashlib.sha256(old.encode()).hexdigest(), new_sha256=hashlib.sha256(new.encode()).hexdigest()))
    note = ("> **Round 13 owner-document cleanup (2026-09-19).** This file is `report_final_v2.md` (reviewed and accepted for the named Round 12 corrections by the root session at `%s`, review on main at `%s`: `reviews/round13_integration_disposition.md`; kept byte-unchanged) with the %d precision replacements of `experiments/tau2_open/make_report_final_v3.py`. No model was run, no analysis was rerun and no number, table or figure changed. Verification chronology: `reviews/session60_round12_report_corrections_verification.md` describes the files BEFORE the five late fixes (its hashes and diff counts are historical); the committed v2 files were verified by the root's Round 13 reviews (`reviews/round13_owner_report_inference_review.md`, `reviews/round13_report_provenance_review.md`). This v3 file has been checked by its generator assertions only.\n\n"
            % (REVIEWED_HEAD[:7], ROOT_REVIEW[:7], len(REPLACEMENTS)))
    marker = '> **Round 12 report-only correction (2026-09-19).**'
    assert t.count(marker) == 1
    t = t.replace(marker, note + marker)
    for banned in ('honest price', 'No descriptive observation of this report depends', '(all abstain)', 'with three passages replaced', 'generated arm-A tokens'):
        assert banned not in t, banned
    OUT.write_text(t)
    MAN.write_text(json.dumps(dict(kind='owner-document cleanup (Round 13); report-only; no model call; no analysis rerun', source='results/tau2_open/report_final_v2.md',
                                   source_sha256=sha(SRC), output='results/tau2_open/report_final_v3.md', output_sha256=sha(OUT), reviewed_owner_head=REVIEWED_HEAD,
                                   root_review_commit=ROOT_REVIEW, replacements=applied, note='replacements hold sha256 digests of the passages; the passage text is in the generator'), indent=2) + '\n')
    print('wrote', OUT.relative_to(REPO), MAN.relative_to(REPO), len(REPLACEMENTS), 'replacements')


if __name__ == '__main__':
    build()
