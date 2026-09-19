# Round 10 accepted-result integration and remaining findings

Date: September 18, 2026. This is an intermediate release checkpoint, not author signoff or completed submission.

## Accepted exact sources

- PR 7 `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb`: selectively copied `experiments/ustat_reference/`, `results/ustat_reference/` and `evidence/ustat_reference_report.md`. Other branch code, generic projections, replay changes and draft text were not approved or imported. All 26 selected source/result/evidence files match the source commit exactly. Round 9's table/interval/provenance/convention checks and Round 10's exact rare-event diagnostic reproduction support the bounded comparison; the root audit does not claim an independent rerun of all 56,000 original comparison repetitions.
- PR 10 `ae3f0a5d4936855fc0b81f4a327254e932ea729b`: copied `experiments/drift_panel/`, `results/drift_panel/` and `evidence/drift_panel_report.md`. All 12 selected files match the source commit exactly. The independent reviewer reran all 96,000 sequential and 14,000 permutation repetitions, reproduced both numerical CSVs, independently checked target calculations and audited generated paper tables.
- New root theory: fixed-stake normalization proves a fixed-threshold crossing guarantee for the running average of conditional means. A separate reviewer checked the exact proof and conjunction extension. Fixed stakes, fixed weights/thresholds and the bounded-score assumptions remain essential. Old gate crossings cannot certify a new drifting conjunction; the result is not a random-threshold confidence sequence or a guarantee for arbitrary adaptive stakes. The paper credits established martingale machinery and does not claim a new generic concentration inequality. This is a post-study mathematical clarification, not a preregistered new empirical hypothesis.

The root's generated sections distinguish finite-sample and asymptotic methods, same-look and retained decisions, component and guarded errors, separate random seeds, and actual versus planned replication counts. Diagnostic summaries conditioned on rejection do not establish a causal mechanism. Zero deployment of a wide interval does not prove a particular reason for conservatism. Distributional permutation nulls and mean-win nulls are separate claims.

## Preserved provenance and anonymous release

The original numerical core is executable-AST identical to `f806aba`; only a docstring changes to state the new scoped guarantee. The prior reproducibility manifest is preserved under `results/source_baselines/`, with its exact hash recorded in the updated manifest. Original contributed files remain byte-identical on disk.

Only archive copies of five identifying absolute output paths are sanitized. `results/anonymous_provenance_map.json` records the original/release hashes, and the release integrity manifest points to the transformed copies. The first release check caught a diagnostic manifest's temporary-directory path that was not covered by the original sanitizer. The builder now handles any absolute output path and scans identifying username/repository variants. Independent final archive checks and exact artifact hashes are in `round10_release_delta_audit.md`; PDF visual evidence is in `round10_visual_and_archive_qa.json`.

## PR 8 remains outside this release

At `c89b525cd8e51564ca8c23399201d9cfdf0431a3`, version-2 aggregate outputs, raw preservation and immutable benchmark sources were independently reproduced. The corrected two-sided hedge fixes the prior maximum-of-two-capitals defect. Remaining findings are concrete:

1. Same-task uncertainty does not automatically survive complementary pass assignments driven by one orientation coin. The two tasks may be dependent under period effects. Supply appropriate uncertainty or state and defend a stable independent-outcome model; include CLT nondegeneracy/variance-growth assumptions.
2. Zero-count endpoint arithmetic still drops a term through `0*log(0)`; exact capital-1 endpoint checks and versioned regeneration are needed. The demonstrated discrepancy is conservative.
3. One anonymous provenance-map target is absent, and the PR-body interval summary is stale. Correct release mapping and labels without modifying raw observations.
4. Airline final real outcomes are absent. The last owner's posted count is 27/196 at 21:44 UTC, under an amended second invocation. That is not proof of current process state. Preserve every original/amended invocation, failed/truncated unit and protocol deviation for later review; do not launch a duplicate job.

These findings were sent to the existing owner. The core release does not import the affected code or empirical claims. Deferred model-size/hardware/Pareto-cost/tie/grader expansions do not become mandatory just to increase experiment counts. A concurrent timestamped prefix study is required only if the paper later claims measured operational latency savings.

## Readiness disposition

Readiness stays **70/100** under the fixed rubric. The accepted PR 7/10 studies close parts of S6/E4/M4/Q4, but final incoming-result disposition and human inputs remain unresolved. An independently checked intermediate archive is useful progress without being the final package. No model inference, paid calls, author declaration or submission occurred during this review.
