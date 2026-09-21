# Bounded review of optional piecewise conformance diagnostic

September21 09:46 UTC cycle. Exact candidate **1c1304118a84827c46d29deeb9543683e1411863**, compared with3341f2107b9ff9a5d67c9a09c3c27e9a4fe74d7d. Export `/Users/yukang/Documents/Codex/2026-09-17/i-x20/work/v2_review_0946`. Scope only `vconformance` completeness/coverage claims. Root handles pinning, runtime-hook and handoff decisions. No stochastic/native/timing grid, model or experiment output review was performed.

## Bounded execution result

A single independent invocation of `vconformance.run()` passes its **1857 cost-combination/positive-delay checks and36734 pair-state comparisons**. The three cost combinations cover620 declared delay values, with d=0 appropriately excluded from partial-life threshold checks and addressed by resolved-branch fixtures. This reproduces the owner's diagnostic counts; it does not establish36734 independent observations or simulated error calibration.

The check actually executes `vgen.state_at_age(policy='operational')`, rather than a separate toy enclosure implementation. It covers both revealed-arm orientations and both revealed-success values in its partial-state loop. The threshold test independently recomputes the first certificate ages across all reachable combo/delay pairs. This is useful additional deterministic evidence and should be preserved as a standalone diagnostic.

## Scope of the piecewise argument

The literal global statement that a pair has breakpoints “only at the two certificate thresholds” is incomplete. The full age partition also changes at **first reveal f and full resolution d**. Its pieces are:

1. age<f: both arms unrevealed, full intervals;
2. f<=age<d: exactly one revealed, with success/failure branch and two potential epsilon-certificate transitions;
3. age>=d: resolved final H/D scores.

Within the **partial** branch for the current pinned source, age enters only through the nondecreasing certified elapsed cost. The two monotone certificate inequalities and their checked first-crossing tables determine that branch's remaining interval pieces. Thus a representative boundary/interior comparison can be extended to all ages **conditional on the inspected source having no other age/state dependence**, the declared finite cost/delay support, valid f<=d and correct supplied outcome arrays. That is a defensible source-structure argument; it is not an unconditional completeness guarantee of the test routine against arbitrary future code changes.

The actual test reductions need to be stated accurately:

- `_vgen_single` fixes f=0 in all partial comparisons; it does not enumerate first-reveal boundaries for every possible f. Current `state_at_age` depends on f only through the branch mask, so that reduction can be justified by source inspection.
- Resolved tests use all atoms but only five delays, three ages per delay and candidate-first orientation. Current resolved outputs read `draw.z` and `draw.dsc` regardless of those omitted dimensions, which supplies the structural justification.
- Unrevealed tests use one helper atom/state, age0, f=d and four positive delays. Current unrevealed branch is constant; the diagnostic does not literally exercise every unrevealed state.
- `_vgen_resolved` constructs its supplied z/d from the independent `vband` final-scoring calls. It consequently checks resolved propagation, not whether the generator's own ATOM_Z/ATOM_D lookup arrays were correct. Generator/scoring consistency belongs to the separately accepted source/fixture evidence.
- The new checker does not by itself prove vectorized breakpoint accumulation, prefix denominators, legal monitoring looks or first-decision timing. Those were already independently checked in the accepted specification and should be linked, not relabeled as consequences of this new module.

Recommended wording: **“Threshold-table exhaustion and36734 representative state checks, with a conditional piecewise coverage argument for the inspected source and declared finite design.”** Replace unqualified “equals everywhere,” “complete by construction,” and “only two breakpoints.” No counterexample to the current operational policy or primary theorem was found in this review.

## Keep this optional and do not reopen the accepted gate

The authoritative09:09 root disposition already retained one runtime draw plus linked accepted deterministic witness/configuration receipts on unchanged scientific digests. This optional diagnostic is **not a missing prerequisite** and is not a reason to delay the study, withdraw the completed deterministic five-point milestone, launch a5.7million-state fallback or repeat broad timing/calibration runs.

Root's current concrete decision is to preserve the new diagnostic source/result, remove its new mandatory runtime hook to restore the accepted3341 workload, and narrow its claims as above. Its source/receipt pinning must be handled if the optional artifact is later reused; this reviewer makes no new execution authorization. Follow the current launcher/freeze handoff rather than the stale interpretation that exhaustive conformance replaced the accepted gate.

## Evidence

The [portable script](evidence/v2_conformance_probe_20260921_0946.py) and [captured receipt](evidence/v2_conformance_probe_20260921_0946.json) record the bounded successful checker result. The script removed only elapsed-time reporting from the review receipt; this review reports no performance estimate. It wrote no owner file or study result and did not rerun accepted scientific witnesses.
