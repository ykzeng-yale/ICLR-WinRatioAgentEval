# tau2_open: Round 13 note (owner-document precision items, 2026-09-19)

Status: report-only. The root session accepted the named Round 12 corrections at owner head
`01f2381940fcf5bc57129f1498382cb40f3ea741` (review on main at `a2eee58526f0ce3cef913fa8156ae34601d1b597`,
`reviews/round13_integration_disposition.md`) and listed optional precision items for future reuse of the owner
documents. They are applied in the new file `results/tau2_open/report_final_v3.md` (generator
`make_report_final_v3.py`; `report_final_v2.md` and every earlier file stay byte-unchanged). No model was run, no
analysis was rerun and no number changed. Precedence: `protocol_addendum_round12.md` with this note, then the Round 10
addendum and the erratum, then the Round 9 addendum, then the frozen protocol.

1. **Omitted generated tokens.** Wherever the Round 12 addendum or report says "generated arm-A tokens", read:
   a lower bound of 246,284 additional **A-collection generated tokens; the split between agent and user-simulator
   roles is unavailable**. The quantity is the root's log reconstruction and includes user-simulator work.
2. **Placeholder sensitivity (section 7.2).** The planned retained-record analysis remains the primary analysis. Its
   E1 and E2 net benefit are unchanged when the two infrastructure placeholders are omitted; resource summaries and
   some denominators change. The sentence that no descriptive observation depends on the treatment is withdrawn.
3. **Abstention scope (section 8).** The primary-rule interval-based comparisons abstain. Some alternative hierarchy /
   tolerance rows of the section 4 sensitivity table select B. Those rows are separate, model-dependent sensitivity
   outputs and remain excluded from the root integration.
4. **n = 12,094.** This is arithmetic for the normal-mixture boundary with rho = 100 under the nominal coin model. It
   is not a lower bound for other methods and not a general cost of inference without a task-sampling model. The
   coin model is itself an assumption.
5. **Verification chronology.** `reviews/session60_round12_report_corrections_verification.md` describes the files
   before the five late fixes; its hashes and diff counts are historical. The committed v2 / v4 files were verified by
   the root's Round 13 reviews. The v3 / v5 files of this round were checked by their generator assertions only.
   Manifests hold sha256 digests of replaced passages; the passage text is in the generators.
