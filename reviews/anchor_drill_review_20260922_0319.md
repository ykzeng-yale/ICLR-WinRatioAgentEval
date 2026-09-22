# Independent anchor-drill review — 2026-09-22 03:19 UTC

Exact delivery `5fa7154ee8b96c3afbe148b0828fae4b82bc033e`. Read committed 20-attempt JSONL, v2 receipt, superseded receipts, location amendment, drill script and production anchor/report code. Used read-only GitHub API to inspect issue13 and its20 comments and search issue11 links. No posts, drill reruns, model calls or production processes.

## Accepted external evidence and numerical reproduction

Issue13 contains exactly20 comments at this review. Every retained comment ID, created_at, updated_at, posting index, synthetic drill ID and four-event sequence endpoint matched the actual GitHub comment. All20 attempts report HTTP201 and success, with unique IDs; no missing index in1–20. First/last comments:

- https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/13#issuecomment-5770654019
- https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/13#issuecomment-5770657750

Independently recomputed all v2 summary numbers from raw fields, including monotonic ack-minus-send:

| Quantity | n | Median, seconds | Reported empirical p95 | Maximum |
|---|---:|---:|---:|---:|
| Monotonic POST round trip |20|0.598732043|0.824007084|3.320335542|
| GitHub created_at minus client send wall time, L |20|-0.279357433|0.247454882|1.622478008|
| Absolute consecutive L difference |19|0.475270987|1.541416168|2.324030161|

The script selects sorted index round(.95(n−1)); thus the first two reported p95s are19th of20 and the last18th of19. The latter is **not** nearest-rank p95, which for19 values selects the maximum; label its convention rather than interchange quantile definitions. RTT p95 coincides with nearest rank here.14 of20 L values are negative. First client send03:09:07.501548UTC; last acknowledgment03:09:40.933633UTC, spanning33.432085seconds. This is one short-period calibration sample, not a bound on future posting times.

The committed location amendment SHA-256 independently matches `2223dbdfc27be43579db8a5e9b08389b0b00e470bd0f2fa2dcbcaddf0a711110`. Its commit `1ec6ee7` is dated03:09:00UTC and precedes first client send and GitHub issue creation03:09:07UTC in retained chronology. Its recorded document time is03:05UTC; these are distinct timestamps. This supports the recorded pre-post amendment ordering; Git author/committer dates alone are not an independently trusted publication timestamp.

## Scope corrections and finite remaining work

1. **This is a real GitHub POST calibration with a bespoke script, not the full production anchor path.** `anchor_drill.py` imports `lab_anchor` only for its scanner. It builds custom mock segments and calls its own `session.post`; it does not call production `serve`, `_handle`, `commit_and_push`, or `post_comment`. No dedicated drill-branch push, anchor spool consumption, private production receipt, or chained receipt return is exercised. The v2 assertion that the production anchor path works end to end exceeds the delivered evidence. Preserve these20 valid posts; do not repeat them for timing. If not covered by another retained artifact, one bounded synthetic production-path anchor is the finite missing integration check, with branch/push/spool/receipt provenance. Root owns its authorization and exact scope.
2. **Identifier scan evidence is partly reconstructed.** The retained dry run has ID `drill_a5440e44f7b6`, whereas executed bodies have ID `drill_9dffbd171dfd`; the analysis-only helper's “same bodies” assertion is not byte-identical support. Source does scan before posting, but the retained dry-run receipt is not the executed-body scan receipt. Independently scanning all20 actual current GitHub bodies with the project scanner found **zero hits**. That is a current independent scan, not reconstruction of an unavailable original pre-post receipt. Retain the distinction; no repost is necessary.
3. **The promised link from issue11 was not present at review time.** Read-only exact-link search for `#13` or `issues/13` across its comments returned none. The drill issue itself mentions issue11, which is the reverse direction. Root can supply the missing forward link in its ordinary coordination update.
4. **Clock interpretation should stay narrower.** GitHub created_at is whole-second output; quantization plus offset/delay can produce negative L. The observed difference is not pure posting latency. The subtraction result L itself is not integer-second quantized because client send includes fractions. The retained sample does not establish a universal floor implementation or a maximum future effect. `p95(L)` and `p95(|ΔL|)` describe different quantities; their difference is not proof that a30-second-base audit is broken. Preserve the data and specify the operational tolerance before outcomes.

## Production reporting gap relevant to the drill

Confirmed `build_live_ab_results.integrity_object` at lines261–315 returns anchor counts but no consecutive-anchor time residuals or sandwich violations; its `integrity_qualified` expression includes coin adjacency and terminal-failure pairs only. The protocol §12.6 explicitly includes sandwich violations in the label. A successful POST drill does not close that report implementation gap. Root's proposed prefreeze definition—nearest-rank empirical p95 of local monotonic POST send-to-ack duration, retaining the30-second base—would yield **0.8240070836618543seconds** here. It is a transparent operational calibration heuristic, not guaranteed future error control. Trial sandwich residuals compare anchor-event wall times, so the report must use those actual event times rather than silently substituting drill send times; production queue/commit/push delay can differ from HTTP POST delay.

## Disposition

Accept20 independently matched external posts and exact reproduction of the saved timing summaries under their stated order-statistic convention. Preserve the dry-run collision and failed v1 ISO parser artifacts; rebuilding from retained attempts without repeating posts was appropriate. Accept neither full production anchoring coverage nor trial/report readiness from this receipt. Remaining finite work: ordinary issue11 forward link, scoped claim/provenance correction, actual production anchor-path integration evidence if otherwise absent, and the already-required sandwich reporting/label implementation under root's explicit prefreeze definition. No live-study results or readiness points are asserted by this independent review.

### Dated coordination delta — 2026-09-22 03:23:59 UTC

Read-only API verification confirms [owner comment5770756654](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5770756654) now explicitly links drill issue#13 from issue11. The earlier missing-forward-link observation is **resolved**; no repeat request is needed. Other bounded acceptance and production-path limitations above are unchanged.

### Bounded correction delta — 2026-09-22 03:27 UTC delivery

Read `90f26041db6216695b22c5906a22cbc024b5b118`, its `ANCHOR_CORRECTIONS_v1.json`, and index `59110a123aa575b8ad7e1e14c29ea90a4a12cab8`; no probes, tests or postings repeated. The owner now explicitly withdraws the inference that a frontend HTTP-Date offset establishes which mechanism dominates the sign of API `created_at − client send`. **That interpretation disclosure is resolved.** HTTP-Date and created_at have not been shown to share one clock; negative observed differences remain descriptive facts. The correction also distinguishes local receipt writes from remote GET-only behavior and states the constant-offset/common-clock assumptions of intersected bounds.

The quantile convention is now disclosed and the implementation uses nearest rank. The prior value1.541416168seconds is correctly retained as18th of19; nearest-rank p95 is19th of19, **2.324030161seconds**; the reported linear-interpolation value1.619677567seconds is consistent with interpolation between those two previously checked order statistics. Root's selected POST RTT nearest-rank p95 remains **0.8240070836618543seconds**. This is a convention clarification, not evidence that a percentile equalling the sample maximum is mathematically invalid: nearest-rank p95 legitimately equals the maximum for small samples, including n=19. Do not retain the tool comment asserting that a percentile equal to the maximum “is not a percentile.”

Likewise, an intersection narrower than one second does not itself discard quantization uncertainty: if every per-probe interval validly contains one common offset, their intersection also contains it. The substantive cautions are validity of each bound, constant/common-clock assumptions, and inability to transfer a frontend-clock bound to created_at; width alone is not a counterexample. This clarification does not demand additional probe execution.

The new GET probe receipts are **received, not independently accepted calibration** in this bounded delta. Original20 POST observations and their acceptance remain unchanged; no repeat20-post request, new tolerance, production-path closure or readiness credit follows. The03:23:59 forward-link repair remains closed, and root has separately answered the clock-domain implementation question.
