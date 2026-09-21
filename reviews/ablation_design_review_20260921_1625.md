# Bounded review of the matched certificate-ablation operator

Reviewed `vablation.py` and `ablation_20260921/PREREGISTRATION.json` at `60f9e21`, with the unchanged `vgen.state_at_age` and adapter call path as context. Source-only review; no simulated draw, invariant execution, native/reference call, or model run was performed. This is a check of the delivered transformation, not a new approval requirement.

## Per-state argument: accepted

Let T be exactly the pairs with `f <= age < d` and revealed success 1. The original hierarchy bounds on T are `[q,1]` if the candidate revealed first, or `[-1,-q]` otherwise, with q in {-1,0,1}. The proposed replacement is `[-1,1]` on T. Therefore it contains the original hierarchy interval for **every age and every admissible original state**, not only for the deposited snapshots. Outside T, both hierarchy endpoints are copied from the original state.

This establishes the intended branch-level properties, conditional on the pinned original implementation:

- Both-pending and revealed-failure hierarchy states are unchanged.
- Resolved pairs (`age >= d`) are outside T and retain their identical final score.
- `s_lo` and `s_hi`, along with resolved/unrevealed indicators, are untouched by `dataclasses.replace`; success enclosures are identical everywhere.
- At a common enrolled prefix/look, summing the new hierarchy endpoints and applying the same denominator and radius yields a lower bound no greater and an upper bound no smaller than the original. The success band remains identical. No altered primitive boundary is introduced.

“Final scores unchanged” must mean resolved individual scores, not identical hierarchy bands at the fixed finalization tick: some pairs remain pending there by design, and their disabled hierarchy bounds can still be wider.

## Diagnostic counter semantics: accepted

The original `cost_narrowed` is `partial & succeeded & (q != -1)` and `cost_collapsed` is `partial & succeeded & (q == 1)`. Both flags are already false outside T. Setting their entire arrays to zero therefore exactly removes the certificate-based diagnostic counts, without erasing an unrelated failure-based or fully resolved category. Keep the original resolved/certified counts and recompute any “point-resolved” diagnostic from the variant's bounds/counters; do not relabel a merely widened pending pair as a changed final outcome. Work/update counts can legitimately change because certificate transitions now have zero increments; they are not evidence that the reveal or enrollment schedule changed.

## What the deposited snapshots establish

The receipt claims 384 age snapshots and 768,000 pair-state comparisons: these counts agree with four cells × six programs × four trials × four snapshots × 2,000 pairs. The function checks containment, resolved-score equality, and success equality at ticks 1,1000,2000,2100. It does not exhaust all ticks or all threshold branches, and it does not include finalization tick 2200. Early snapshots also include array positions not yet enrolled, assigned age zero; their count is array-state comparisons, not 768,000 distinct active-trial observations.

These limitations do not undermine the simple all-age source argument above and do not warrant a massive tick rerun. State the evidence layers accurately: sampled regression checks plus a branch-level containment argument. The returned `schedule_untouched` field is an explanation, not an executed schedule equality assertion. `negative_controls` in the JSON is a delivered claim not independently executed in this review. The “before outcomes” phrase must refer to new ablation evaluation only: original coarse outcomes were already known, and the specification correctly labels this a post-hoc exploratory analysis.

## Runtime integration: not delivered in this snapshot

A repository-wide source search at this commit finds `state_at_age_nocert` called only by `assert_invariants`; no actual ablation evaluation runner or installation path is committed. The existing `vgen.adapter_tick_sums` calls the module's `state_at_age`, so an explicit scoped injection can use this operator. Do not count the present code as evidence that disabled-arm trial records have been evaluated.

The wrapper itself invokes `vgen.state_at_age`. Consequently a future direct global assignment of that name to this wrapper would recurse unless the implementation retains an unmodified original callable. This is integration guidance for the authorized runner, not a claim that an uncommitted runner already has the defect. Root owns that wiring review. Existing breakpoint ages may remain in the timeline as redundant zero-change breakpoints; removing them is unnecessary to the ablation.

## Interpretation of paired endpoints

On a common trace/look, widening can only remove a deploy opportunity or a retain opportunity, never create one relative to that same look. This per-look nesting does not by itself prove that the **first-decision label** is monotone across variants when deploy and retain are competing stopping labels: an original early retain can precede a later deploy opportunity that a wider variant reaches. Preserve and compare both first-decision labels, times, and discordant pairs rather than assuming a one-direction change in deployment for every possible trace. If the delivered original subset has no retains, that empirical fact can simplify its observed comparison; it is not needed for the general containment proof.

With identical traces/configuration and the operator correctly connected, paired differences isolate removal of these two certificate branches **within this fixed synthetic replay design**. They do not establish that cost narrowing explains every A-versus-N difference or generalize to all informative-delay systems. A result with little/no change remains valid evidence. The existing post-hoc label and fixed four-cell coordinates are appropriate.

## Disposition

Accept the branch-level containment, unchanged success/resolved-score argument, and reset-counter semantics. Treat the sampled checks as bounded regression evidence and the runtime evaluator as still to be delivered. No new scientific gate, draw expansion, reference call, or large invariant sweep is requested by this review.
