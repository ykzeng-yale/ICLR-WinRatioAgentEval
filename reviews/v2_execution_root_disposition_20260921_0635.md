# V2 executable integration review and scientific disposition

September 21, 2026, 06:35 UTC cycle. Reviewed exact owner head **63be271af3e01bf7743efd23e2bfddce47a2016c** (executable delivery `65e957e`, followed by live wording/snapshot edits), relative to `7f795e3`. **Full-project arXiv readiness 60%, change 0; separately bounded-v1 90%.** The deterministic adapter/specification milestone is not complete: the comparison tool has a matched operational policy, but the actual calibration runner does not yet execute it. No full calibration or live trial is cleared by this report.

## Accepted evidence and scientific diagnosis

The owner delivered 17,603 matched-policy comparison looks, including 1,592 nonfinal drain looks, with zero recorded disagreements, from 8/200 planned cell streams plus 726 comparable fixture scripts. This is bounded conformance evidence, not 200-stream completion, Monte Carlo calibration, or live execution. See the [independent policy review](v2_policy_delta_20260921_0635.md) for 96 independently matching partial states, the first-decision witness at tick 1010 rather than 1200, and saved-count reconciliation. The distinct ideal-oracle comparison retains 102 disagreeing looks and 103 narrower pair states; the operational comparison records 19,208,000 pair-state containment checks. Reclassification is appropriate because these are explicitly different observation policies, not evidence that the tighter oracle became the live rule.

Root independently reproduces all three newly exposed drain states, rather than returning their diagnosis to the collector:

| Cell / tick | Revealed arm and cost / pending lower cost | Ideal oracle | Operational/live |
|---|---|---|---|
| C2 / 2011 | incumbent 10 / 10.526315789473685 | [-1,-1] | [-1,0] |
| C3 / 2160 | candidate 40 / 38 | [0,1] | [-1,1] |
| C7 / 2090 | incumbent 40 / 38 | [-1,0] | [-1,1] |

All are already identified conservative boundary classes. In each, the wider interval contains the oracle interval and changes one aggregate endpoint by 1/2000 = 0.0005. These cases do not supply a mathematical counterexample to coverage. They demonstrate a policy difference that could affect decision timing elsewhere. **This adjudication is closed; do not rerun it merely to obtain another acknowledgement.** A separate decision-time comparison between oracle and operational policies is optional diagnostic work, not a new prerequisite for the agreed primary study. Use the operational policy for actual calibration and retain the narrower oracle as a labelled diagnostic. Do not tighten epsilon, alter margins, require a favorable result, or claim all stopping summaries invariant.

Root also reproduces 48 corrected prefix-centered sums of squares and predictable-clock values without calling the native reference. The descriptive variance and reversed alpha-history repairs are accepted within that scope. This does not independently reproduce native mixture widths or establish success-guard power. [Portable root checks](evidence/v2_root_checks_20260921_0635.py) and [receipt](evidence/v2_root_checks_20260921_0635.json) preserve the audit.

## Principal blocker: the full executable panel differs from the checked comparison

`vcompare` selects `vpolicy.OperationalMonitor` for v2. The actual `vrun` calibration path still obtains ideal-oracle states through `vgen.adapter_tick_sums` / `state_at_age`; it has no operational-policy selection. Also, the full grid still calls `run_block` without the declared H/D reference. The timing helper makes eight reference calls/program but discards the returned bands and writes primary rows only. Consequently, neither matched-policy conformance nor the helper's timings certify the intended full calibration executable.

**Owner's next implementation milestone:** one versioned end-to-end v2 entry point must execute the operational primary and persist the declared H and D complete-information diagnostics on the same latent draws. Keep one reference call per full score path, four trials/program, eight calls/program; index the returned bands at the declared prefixes. Keep the reference outside operational decisions and preserve v1 reproduction. Keep the primary implementation independent of the reference through an orchestration layer if needed. Log policy/workload IDs, seeds, source/config hashes, actual call counts and output identities in the immutable run receipt.

Before any full panel, demonstrate this actual entry point on the existing development coordinates with a small deterministic integration fixture: it must expose a known oracle-versus-operational boundary, the existing first-decision/drain witness, reference call counts, and retained H/D outputs. A fixture that only tests `vcompare` is insufficient. No new scientific cell, model call, or broad simulation is requested.

## Resource decision: retain the design and caps, finish the missing scope

The [resource review](v2_resource_delta_20260921_0635.md) independently reconciles the saved timing arithmetic and the eight-call harness. The receipt has 12 timing groups and 13 recorded attempts with zero recorded failures; repeated timing entails 9,600 reference calls plus 24 warm-ups, not 20 independent scientific experiments. The T1 projected total is approximately 2043.91 seconds against the existing 5400-second cap. This is encouraging conditional planning arithmetic, **not an observed over-cap run, a reliable upper bound, or complete execution clearance**. There is no current reason to reduce the scientific tier or remove the comparator.

The separate guard now rejects its three demonstrated cases, but still authorizes with NaN reference time, excessive total bytes/RSS, or a missing combined receipt backed by old scaled H-only arithmetic. It also prices the automatic tier before applying execution overrides. Fix these named failures: require finite nonnegative complete totals, matching code/config/policy/workload/receipt identities and planned group accounting, and check every existing cap against the actual proposed arguments. Retain old arithmetic as historical description rather than authority to execute an unresolved workload. Keep runtime resource checks as well.

Preserve all measurements. Reconcile the recorded `vrun` hash with the exact measured source; a whole-file hash difference alone does not prove the timed core changed. Add only the missing end-to-end orchestration, reference output/accumulation and memory scope on the already authorized balanced development design after that executable is bound. Record actual timestamps, raw timings, all attempts, binary/environment pins, actual output bytes and total usage. Do not repeat unchanged full timing grids. The existing cap and effect-independent primary tier remain fixed. The before/after timings are differences of medians from successive blocks, not interleaved paired causal overhead estimates.

## Close the live wording and snapshot precisely

The two live source edits are executable-AST identical after removing documentation. Snapshot `files` hashes match the delivered live bytes. However, `PINNED_V2.json` still has the old `lab_enclosure` hash, byte count and blob in `detail`, and an older source commit. Reconcile the complete manifest with the exact source used; preserve the already delivered comparison receipts and their original pins. A documentation-only snapshot change does not require repeating numerical comparisons.

The stopped-roster sentence is withdrawn, but its replacement still calls the target the mean of the observed scores of enrolled pairs and claims absence of stratum-weighting bias by construction. That does not match the authoritative protocol section 10.1. Replace both affected `lab_data` paragraphs with the following scientific statement, adapted only for their local context:

> Each stratum contributes floor(n_s/2) pairs, and the combined pair list is uniformly permuted. At any fixed, non-random prefix length, the expected stratum proportions equal the pair-roster proportions. This does not imply the same expectation at an outcome-selected stopping time. The monitored targets are the enrollment-running averages of the history-conditional means of the hierarchical score and success-difference score, under the paired serving regime defined in protocol sections 7.2 and 10.1. They are not the realized sample means or a fixed full-roster contrast. No unbiasedness or stopping-time invariance follows merely from proportional allocation.

This is a clarification of the existing target, not a new estimand or allocation redesign. The corrected live enclosure exactness disclaimer is acceptable; preserve it.

## Ranked handoff and completion state

1. **Session60:** connect the operational policy and retained two-score reference outputs to the actual v2 runner; deliver the small end-to-end fixture above. This is the next executable milestone.
2. **Session60:** close the named guard and provenance failures, then measure only the missing execution scope; apply the exact target/manifest corrections in the same delivery if practical. Root will review the immutable commit and explicitly decide full comparison/calibration and live-freeze clearance. No approval is implied by elapsed time.
3. **Root:** accept only reproduced evidence, then integrate accepted new findings into the expanded paper, supplement and release. **Yukang:** final scientific review and submission inputs remain pending.

Latest owner report **06:20:19 UTC** says zero live episodes, zero v2 calibration cells, no freeze, and host contention for 36.6 hours. Root has not inspected that host; the owner's 474/175/18 test counts are not represented as root reproduction. New evidence is received and bounded-checked as above, not fully accepted, integrated into the paper, or packaged. Frozen v1 paths and all five current arXiv artifact hashes remain unchanged; no PDF rebuild is needed for this review-only cycle. No PR was opened.

Remaining **40 checklist points**: prospective study and CPU validation 20 (session60 delivery/root acceptance), expanded integration and final QA 10 (root), final scientific/submission checks 10 (author). Half-hour coordination continues. The positive signal is closer agreement between independent implementations of the intended policy; the present blockers are executable integration, resource accounting and target wording, not a demonstrated failure of the win-statistics theory.
