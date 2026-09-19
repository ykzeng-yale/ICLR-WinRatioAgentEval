# Round 11: incoming airline deposit — design and inference scope

**Verdict: canonical observation deposit verified in a bounded check; current inferential/report package needs repair before integration.** The new deposit provides all 196 planned task–trial–arm records, with 15 successes among 98 canonical records in each arm. It does not yet provide complete attempt/resource accounting or a defensible unqualified interpretation of its reported confidence intervals. Keep this delivery separate from the already accepted coding subset.

Frozen incoming head: **`3c70c3e5ec8c8d6f9c5e06b369237319799c864d`**, reviewed 2026-09-19 by reading Git blobs into isolated outer scratch. This reviewer previously contributed project theory and reviewed the coding target; no airline model collection was performed by this reviewer. No model, benchmark program, full analysis runner, or Monte Carlo was executed; no contribution source or Git state was changed. Only this report and outer `work/round11_airline_scope/` scratch were written. The owner's completed interpretation/report and independent full evidence verification were still pending at this head.

## 1. Safe observed quantities independently checked

Both gzip files decompress to the exact uncompressed byte sizes and SHA-256 values recorded in `results/tau2_open/raw_deposit_manifest.json`. The same bytes also match the manifest's claimed canonical/per-invocation copies. The deposit does not contain a separate raw snapshot from interrupted invocation 1.

| Canonical accounting | Arm A | Arm B |
|---|---:|---:|
| Distinct planned task–trial records | 98 | 98 |
| Reward exactly 1 | 15 | 15 |
| Reward 0 | 81 | 83 |
| Missing reward, retained infrastructure failure | 2 | 0 |
| `user_stop` | 55 | 69 |
| `too_many_errors` | 14 | 0 |
| `max_steps` | 27 | 29 |
| `infrastructure_error` | 2 | 0 |

The two A infrastructure failures are **zero-duration, zero-message placeholder records**, not complete saved trajectories: task 6/trial 0 and task 32/trial 1. Thus “196 canonical records covering all planned units, including two infrastructure-failure placeholders” is more precise than “196 complete trajectories.” Success counts retain both failures in the denominator.

I independently checked every row's success label, agent prompt/completion token count, and assistant tool-call count against raw messages; all checked fields match `episodes.csv`. I rebuilt the primary hierarchy directly, without contributed inference modules: success first, agent completion tokens second with 5% relative-max tolerance, tool calls third without tolerance, resource tiers eligible only after joint success.

| Descriptive comparison | Wins / ties / losses for B versus A | Net benefit |
|---|---:|---:|
| Prespecified 49 replay pairs | 10 / 30 / 9 | 0.02040816 |
| First-block 24 replay pairs | 5 / 16 / 3 | 0.08333333 |
| Same-task all four trial combinations, 196 comparisons | 28 / 141 / 27 | 0.00510204 |
| Same-task matched trial, 98 comparisons | 13 / 73 / 12 | 0.01020408 |
| Same-task different trial, 98 comparisons | 15 / 68 / 15 | 0 |

All 49 replay signs and decisive tiers match the deposited monitor. All 19 non-ties in that replay are decided by success; none are decided by the resource tiers. The deposited monitor records no win, success-gate, harm, or deployment crossing. These are **observed replay outputs**, not validation of the attached inference.

Raw simulation seeds are 626729 for all 49 trial-0 tasks and 373753 for all 49 trial-1 tasks in each arm. Available response model fields identify A's agent and both arms' user simulator as `qwen2.5-7b-instruct`, and B's agent as `qwen3-4b-instruct-2507`. These checks establish recorded seed/model fields, not complete per-request seed forwarding or bit reproducibility.

## 2. Prioritized integration blockers and repairs

### P1 — The reported CSs do not implement the promised qualified airline R1 analysis

**Sources:** `experiments/tau2_open/analysis.py:238–270`, `protocol_addendum_round9.md` section (b), `results/tau2_open/report.md` section (a), `summary.json` fields `online` and `online_block1`.

The current full-stream NB and success CSs, [−0.3660, 0.4063], are contributed fixed-mean betting inversions, not root normal-mixture bands for running conditional means. The full stream revisits every task in trial block 2. A fixed roster randomly permuted twice is not an iid task stream; shared seeds and execution/batch state require additional modeling even for the 24-pair first block. Uniqueness of first-block task labels does not establish independent episode laws.

The addendum promises a separate R1 script but none is delivered. Its R1 sentence that independent orientation coins make scores independent after conditioning only on matching and the trajectories' **law** is insufficient: shared latent outcome dependence can remain. The current report does not display this caveat or distinguish inferential readings. Its full-stream fixed-mean CI must not be relabeled as a running-mean CS. The win-ratio CS additionally assumes the decided subsequence has the required common conditional win probability; that is not established here.

**Minimal repair:** either retain these replay summaries descriptively without uncertainty, or implement a separately labeled root-core conditional-running-mean analysis under a precise filtration. A clean limited option is to condition on the entire retained outcome array and matching, provided collection/amendment/retention did not depend on the replay orientation coins. Independent fair orientation coins then select between two fixed scores per pair. With μ_k equal to the average of those two fixed scores, the core normal-mixture construction covers the running average of these μ_k. It is uncertainty over replay orientations for this retained array, not fresh-model, new-task, fixed-roster-population, or production inference. Do not condition on the realized orientations as well and still call them random.

For the displayed α=.05 and ρ=100, the 49-pair normal-mixture radius is **0.62973185**, giving [−0.60932369, 0.65014002] around the observed 0.02040816. This is an independently calculated repair illustration, **not an analysis delivered or integrated by this audit**. Because both arm records exist for every unit, the corresponding full-array orientation-average target is itself directly computable (0.01020408 for this matching); a replay band primarily demonstrates the masked-stream procedure rather than creating uncertainty about that already observed array.

### P1 — Task clustering and cross-arm Welch do not establish the current fixed-horizon CIs

**Sources:** `analysis.py:299–318`, `analysis.py:328–354`, `src/wincs.py:405–438`, addendum section (b), report sections (b)–(e).

Same-task CIs use a t/delta-method calculation over 49 task averages. This handles within-task replication **if task clusters meet an appropriate independence/weak-dependence and nondegenerate asymptotic model**. It does not automatically absorb globally reused seeds, shared execution state, or common batch effects. The addendum's claim that common-seed dependence is only within task-by-trial cells is not established: the same two seeds are used across all tasks. Conversely, a repeated numeric seed alone does not prove a particular covariance; the issue is the unsupported independence guarantee. A justified model could condition on seed/batch variables, but it must be stated and its target limited accordingly.

The blanket assertion that these CIs are conservative for a fixed curated roster is unsupported without the independent-task-score and regularity conditions already identified in Round 10. The current cross-arrival component code still computes `welch_ci` on arm arrays and labels the output `cross_arrival_independent`, directly contrary to the addendum's promised pair-level replacement. Repeated tasks/pairing dependence and resource missingness require attention rather than a simple label change.

**Minimal repair:** retain means and counts as descriptive; omit unqualified E2 and component CIs. If retaining model-based intervals, state the exact task/seed/period model and approximate status. Do not advertise finite-sample or assumption-free coverage. No sensitivity row whose unsupported CI happens to exclude zero should become a confirmatory claim; the twenty sensitivity rows are also multiple correlated analyses. The current primary outcomes are inconclusive in the supplied analysis, and observed equal success is not evidence of equivalence or noninferiority.

### P1 — Planned-unit completeness is not all-attempt completeness, and current resource totals omit failed attempts

**Sources:** `raw_gz/tau2_open_armA.json.gz`, `logs_gz/tau2_armA.invocation1_preamendment.log.gz`, `logs_gz/tau2_armA.log.gz`, `run_manifest.json`, `build_episodes.py:43–82`, `raw_deposit_manifest.json`.

The raw placeholder records say `failed_after_attempts=4` for A task 6/trial 0 and task 32/trial 1, with zero messages/duration. The amended A log shows four failures for each. It also shows a failed whole-simulation attempt for task 15 before a retained outcome. The pre-amendment log shows task 6 attempts 1 and 2 failing, followed by a running R2 retry at interruption. The first invocation has no completed status, end-time reconciliation, raw snapshot, or attempt ledger in the deposit. Log evidence is present, but the records have not been reconciled into all-attempt accounting.

`build_episodes.py` sums only the messages saved in canonical records. The discarded/failed attempts' generation, tokens, calls, and duration are therefore absent from those totals. In particular a zero-duration placeholder is not evidence that a failed unit consumed no time or compute. Whole-run timing also differs from sums of retained simulation durations. Upstream summary logs exclude the two infrastructure failures, whereas the deposited custom CSV correctly keeps them as unsuccessful planned units; do not substitute the upstream 96-record denominator.

**Required repair:** deliver a unit-to-attempt ledger identifying invocation, attempt, configuration regime, interruption/failure, retained canonical record, and whether raw usage is known or unavailable. Reconcile the retry counters and the interrupted third pre-amendment attempt rather than merely repeating “two failed attempts.” State the canonical selection rule. Keep canonical-outcome summaries distinct from failure-inclusive operational accounting; if failed-attempt tokens cannot be recovered, report them as unavailable, not zero. No rerun should replace or erase these failures.

### P1 — Amendment chronology and regime labels require correction

**Sources:** `config_amendment_1.json`, `deviation_1_runaway_generation.md`, `run_manifest.json` invocations 1–2, canonical A raw `info`.

The amendment records `decided_utc=2026-09-18T20:45Z`, but the amended invocation starts **20:33:06Z**, and its task-6 failure placeholder is timestamped about **20:37:59Z** after converting the raw local timestamps using the recorded run offset. The amended command is already in the log at 16:33 local. The owner must reconcile whether 20:45 is a later documentation time or an inaccurate decision time; do not present it as a verified prospective timestamp.

The first five A records were collected without the later explicit max-token and simulation caps; remaining canonical records use the amended invocation. Their observed lengths/durations did not reach the subsequent caps, but that does not experimentally verify that the entire serving-regime amendment would leave their outcomes unchanged. Label them pre-amendment, preserve them in the planned denominator, and describe their observed limits. The combined A raw file retains its initial top-level `llm_args` without the new cap, while the invocation-2 commands and B metadata include the cap; a naive reader cannot infer a single uniform A policy from the top-level metadata.

The raw canonical messages contain four A assistant completions with `finish_reason=length` and completion count 1,024; no B assistant completion reaches that cap in the retained records. This supports observed truncation accounting but does not prove caps for every failed request or an all-attempt total. Add per-unit regime/invocation labels and state request/timeout verification separately from intended configuration.

### P2 — Report, reproducibility, and anonymous release are incomplete

**Sources:** `results/tau2_open/report.md`, `analysis.py:454–495`, `raw_deposit_manifest.json`, `config.json`, `run_manifest.json`, raw error tracebacks.

The report literally labels itself a skeleton, leaves interpretation pending, and says “none recorded yet” under deviations despite the amendment. It does not fulfill the promised R1 analysis, qualified CIs, all-role token/resource accounting, or attempt reconciliation. The committed session index also still describes airline collection as running. These are completion-state and interpretation defects, not reasons to alter observations.

The raw gzip deposits make the canonical result arrays inspectable, which is useful progress. A clean reproduction handoff still needs a small hash-checked decompression/parser command and pinned result/source manifest; the current parser defaults to uncompressed `raw/` paths that are absent from the Git tree. The existing source must remain frozen; corrections can be a clearly labeled second analysis.

The incoming branch is not an anonymous supplement: personal absolute paths are present in config, manifest, CSV source paths, logs, and raw infrastructure-error tracebacks. Do not put these objects directly in the current anonymous release. Build a sanitized allowlist with original/release hashes and verify numerical leaves. Realistic passenger/customer strings in tau2 benchmark content should be distinguished from author identifiers rather than blindly deleting benchmark data. No complete credential/license/publication audit was performed here.

## 3. Design interpretation that can safely accompany the descriptive results

This was **prospectively specified batch collection of fresh local open-model outcomes, all A then all B, with a prespecified replay order**. The replay design uses two permutations, one for each trial block, and 49 orientation coins; pair 25 straddles trial blocks. The physical exposures were not randomized into that order. No actual early stopping or deployment occurred. Replay prefixes and potential crossing indices do not measure live stopping savings.

A uses Qwen2.5-7B as both agent and user model on one server; B uses Qwen3-4B as agent and Qwen2.5-7B as user on separate processes. Agent model, serving arrangement, batch period, and recorded amendment history jointly define the measured systems. Resource differences cannot be attributed solely to agent model size or architecture. Duration includes user simulation and tool work, unlike the coding experiment's agent-workflow latency; do not merge their latency labels.

The resource hierarchy uses **agent completion tokens**, not dollars or common-unit compute. Both user and agent usage can be summarized from retained canonical messages, but those sums exclude unsuccessful discarded attempts. For audit reference, canonical agent prompt/completion totals are A 20,412,368 / 248,996 and B 19,138,768 / 223,345; canonical user prompt/completion totals are A 4,373,819 / 85,101 and B 5,915,658 / 82,565. These are verified recorded-message totals only. Different agent tokenizers and model sizes further limit compute interpretations.

Same-task “all” averages four comparisons per task, half sharing a trial index and half crossing the two trial indices. With two seeds, its descriptive score is exactly the average of the diagonal and off-diagonal scores. It should not silently replace an independent-draw target. Off-diagonal seed indices are not alone proof of independent episode laws. Report all three as the stated recorded-array summaries unless a stronger sampling model is justified.

## 4. Minimum owner handoff before a new integration decision

1. Finish the report and source-backed attempt/configuration ledger, including both invocation histories, interruption, retries, two zero-trajectory placeholders, exact canonical selection, cap/truncation/timeout accounting, and chronology correction.
2. Replace current unqualified inference with descriptive reporting or a separately implemented, explicitly targeted analysis. Do not reuse the full-stream fixed-mean betting CS as a running-mean result; do not call the existing E2/independent-Welch intervals assumption-free.
3. Audit the pinned tau2 request path for agent/user seed forwarding and cap/timeout behavior. Raw per-simulation seed fields and response model IDs already pass the bounded checks above; the request path itself was not fetched or certified here.
4. Provide a reproducible hash-checked raw-to-summary workflow and anonymous copies/mappings. Preserve original snapshots, summaries and amendment history.
5. Obtain the promised independent owner-side analysis/report verification; then conduct a scoped integration/release audit. No new model experiment is required merely to fix the current wording, accounting and inference scope.

These requirements do not block finishing the separately validated coding-only package. They block treating this incoming airline analysis as a completed, inference-validated extension at this head.

## Evidence

The isolated snapshot and file hashes are under outer `work/round11_airline_scope/`. `independent_airline_checks.json` records raw-to-CSV and direct hierarchy checks; `extra_checks.json` records model/seed/resource and gzip/deposit checks. The two uncompressed canonical SHA-256 values are A `887c66a23c2c1c2188279ce658efb15436648a9e26251b62f569521df4845fd8` and B `39a49567936fb14f5444ae6e406c43abd1cfbb21198540c8b8df585d8fa1c8f6`.

The frozen contributed `src/wincs.py` SHA-256 remains `6a6a0b51bf46d64079614af3aefc364800c1862fd7635728c2949be7f2907a3b`. Its ternary/Bernoulli capital code still maps a NaN from zero-count endpoint arithmetic to negative infinity, the conservative endpoint defect identified in Round 10. This is separate from the more consequential design/target issue: repairing that arithmetic alone does not validate the current airline CIs. No such endpoint routine was used in this audit's direct score or normal-mixture arithmetic.
