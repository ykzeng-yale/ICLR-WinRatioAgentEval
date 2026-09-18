# Round 2: independent empirical implementation and manuscript review

Date: September 18, 2026 UTC. Reviewer: a separate model-assisted reviewer who did not write the public reanalysis script. The reviewer previously drafted the theoretical appendix; this is independent empirical implementation review, not an independent human referee report or a blind review of the entire theory. Only this review file was edited during the audit.

## Assessment

The historical reanalysis is internally reproducible at the level checked, and I found no arithmetic error in its primary hierarchy comparison. The manuscript is unusually careful about distinguishing preference from guardrails and historical analysis from production evaluation. However, the current evidence does not establish a strong new ML methodology beyond a useful assembly of existing statistical methods. The major submission issue remains contribution strength and decision evidence, not a hidden error in the reported win counts. My present simulated-review recommendation is **weak reject as a new ICLR methodology paper**, with a credible path to improvement through stronger decision-focused agent experiments and a sharply justified contribution. This recommendation is not an acceptance forecast.

The public-data prose was still being integrated when inspected. `results_main.tex` conditionally includes `public_results.tex`, and the latter was not present at the initial audit. This review therefore covers the completed public numerical artifacts and the available manuscript, not a final frozen submission PDF.

## Evidence checked independently

- Recomputed SHA256 for all **611 raw source files** in `results/public_manifest.json`: every source matched. These comprise nine selected τ² result files, two SWE resolved-result files, and 600 SWE trajectories.
- Recomputed every output CSV hash in that manifest: all matched.
- Confirmed **3,336 τ² trajectories**, with four trials on each of 50 airline, 114 retail, and 114 telecom tasks for each of the three selected models; **600 SWE trajectories**, one per model on all 300 tasks.
- Recomputed historical τ² `agent_cost` as the sum of assistant-message costs across every selected trajectory. Maximum discrepancy was below **5.6×10⁻¹⁶**. User-simulator cost is not silently included.
- Wrote a separate branch-by-branch comparison calculation, without importing the shared comparator, and recovered all **1,134 primary task net-benefit scores exactly**. It implements binary success first, joint failures tied, lower historical cost decisive only above the relative 5% threshold, then lower step count.
- Checked all **68** contrast/configuration rows: wins + losses + ties equals one, and net benefit equals wins minus losses.
- Verified all nine τ² contrasts satisfy the exact realized identity `V = 0.75 U_offdiag + 0.25 D_same_seed` to floating-point accuracy. No contrast changed its net-benefit sign between the off-diagonal and same-seed specifications.
- Inspected original model/harness settings. Within each domain the selected models use matching task definitions, user-simulator settings, paired seeds, and historical verifier commits. Airline/retail and telecom have different embedded commits and are correctly analyzed separately. GPT-4.1-mini is excluded from this strict-comparability set.
- Verified SWE uses `instance_cost`, not cumulative `total_cost`, and official resolved membership defines success. The two model labels denote systems under historical configurations, not a randomized model-only causal comparison.
- Visually inspected the complete primary forest plot and cost-tolerance sensitivity figure. Labels, directions, and the illustrative −3 percentage-point line agree with the numerical tables. These are pointwise descriptive displays.
- Searched current text, code, JSON, CSV, and bibliography outputs for author-identifying paths/names and common credential markers. No matches were found in this bounded scan. This is not a final archive, PDF metadata, or secret-scanner certification.

Snapshot hashes:

| File | SHA256 |
|---|---|
| `experiments/reanalyze_public.py` | `63887e085b149c58e42c40a36e4e340d4bb658db74cd54ad0d6e8b1d94c16f92` |
| `paper/main.tex` | `1a1884614541c611087ec90d09f69912ecb6332891897bb4b7df4302f983fa58` |
| `paper/results_main.tex` | `d89028e4d61362af7f48b8fdb4d25bf23a5e7b36478977146977a44a122d08bc` |
| `results/public_manifest.json` | `97d82816fe642c9b9aa0e2f84d8a90ee89a1b45eacaf71ea9c65cfd8385b0759` |

## Findings requiring integration or explicit resolution

### R2-E1 — Shared seeds across tasks limit the uncertainty interpretation

**Priority: high for inferential claims; not an arithmetic defect.** Every τ² domain contains only **four seed values**, each reused on every task: seed reuse is 50 or 114 times per model. Removing same-seed diagonal comparisons correctly removes those within-task paired comparisons. It does not establish that distinct seeds are independent random samples, or remove possible shared seed effects across tasks. The task bootstrap in `reanalyze_public.py:194–195` resamples rows while retaining the same four historical seeds. If seeds induce common cross-task random effects, this bootstrap does not capture uncertainty from sampling new seeds.

Required resolution: make the public interval interpretation conditional/descriptive for the archived task/seed design, and state the separate assumptions needed for population task-and-run generalization. Do not describe these intervals as validated coverage over new evaluation seeds. Fresh experiments should use independently generated, task-specific seed assignments and preserve them in the manifest. A sensitivity analysis over the four existing seeds is useful but cannot turn four seed clusters into a well-powered variance study.

### R2-E2 — SWE repository dependence is acknowledged but not corrected by deletion sensitivity

**Priority: high if SWE intervals support significance claims.** The task bootstrap treats all 300 SWE task records as independent. The 12 repository groups include 114 Django and 77 SymPy tasks, so dependence within these large groups can materially alter uncertainty. Leave-one-repository-out results retain a negative point estimate (approximately −0.130 to −0.065), but this is a robustness-of-estimate check, not a cluster-valid confidence interval.

Required resolution: explicitly keep the SWE intervals descriptive/conditional and avoid repository-population significance claims, or add a clearly labeled repository-cluster inference sensitivity with its small-cluster limitations. Report repository task counts. The parser currently records the GitHub owner (`split('__')[0]`) as repository; it coincides with the 12 groups in this dataset, but the data dictionary should say so or retain the full owner/repository string for portability.

### R2-E3 — Main text promises signed tier contributions that the public outputs do not supply

**Priority: medium; direct reporting mismatch.** `paper/main.tex:109–110` says tier-level wins and losses accompany the summary. `reanalyze_public.py` stores only the decisive mass of each tier: `success_decisive`, `cost_decisive`, `steps_decisive`. These tell how often a tier decides, but not which system it favors. The signed decomposition is central to explaining a preference–success conflict.

Required resolution: either generate per-tier win, loss, and signed net-benefit columns, or narrow the statement to “decisive-tier frequencies.” Adding the signed decomposition is preferable for the paper's interpretability claim. A positive composite cannot be attributed quantitatively to cost from decisive masses alone.

### R2-E4 — Prespecified versus unexecuted protocol elements need a deviation ledger

**Priority: medium.** The off-diagonal amendment is transparently documented and scientifically justified. The record should continue to call this an internal analysis specification written after source/schema and summary inspection, not public preregistration. The protocol also lists several elements that are absent from the executed public script: ordinary lexicographic comparison among joint failures, duration sensitivity, sequential replays, normalized weighted utility, a success–cost Pareto view, and the success-NI-plus-efficiency decision alternative. Simulation recommendations specify 10,000 core-null and 5,000 power repetitions, whereas the executed initial run has 2,000.

Required resolution: mark each as executed, deliberately omitted, pending, or superseded, with timing and rationale. Do not silently rewrite the plan to imply it was followed fully. A 2,000-repetition simulation can be informative when its Monte Carlo interval is shown; the issue is consistency with the saved protocol and its “development evidence” wording, not a universal rule that 2,000 is insufficient.

### R2-E5 — Preference/success reversals are fair observed findings, but not simultaneous discovery claims

**Priority: medium.** The retail and telecom comparisons of o4-mini versus Claude 3.7 have positive estimated net benefit and negative success differences; the arithmetic independently checks. This is a legitimate historical illustration even with joint failures tied. However, these are additional contrasts rather than the designated o4-mini versus GPT-4.1 main contrast, and the reported intervals are unadjusted pointwise intervals across models, domains, thresholds, and outcomes. The `pointwise_NI_lower_above_margin` Boolean is an illustrative fixed-time interval diagnostic, not an anytime-valid deployment gate.

Required resolution: label all extra contrasts exploratory/descriptive and show the full comparison family. Do not promote selected interval exclusions into familywise-confirmed findings or recommend deployment from them. Distinguish “the archived sample exhibits a reversal” from “the population reversal has been established under simultaneous inference.” The current CSV/manifest labeling is good; retain it in captions and prose.

### R2-E6 — Tolerance sensitivity preserves point-estimate signs but not interval exclusion

**Priority: medium.** For o4-mini versus GPT-4.1, all displayed net-benefit point estimates remain positive over cost tolerances 0%, 5%, 10%, and 20%. But airline's 0% interval includes zero (approximately −0.0017 to 0.2817), while its 5% interval excludes zero; telecom's 20% interval includes zero (approximately −0.0190 to 0.1608), while its 5% interval excludes zero. Retail intervals include zero at every displayed tolerance.

Required resolution: describe robustness of the observed direction, not robustness of a statistically confirmed recommendation. The tolerance plot has no uncertainty bands; explain its descriptive purpose or accompany it with the existing complete sensitivity table. The 5% margin is an illustrative preference choice, not elicited stakeholder utility.

### R2-E7 — Final third-party notices and anonymous packaging are not yet verified

**Priority: medium before release.** The raw τ repository MIT notice exists in the private raw-source directory. At the audit snapshot I did not find an output-package `THIRD_PARTY_NOTICES`/license file retaining that notice, although the public manifest says the notice is retained. Avoid distributing raw SWE transcripts/patches without verified artifact-level terms; the current numerical-derivative/source-fetch design is a sensible boundary. A public development repository and an anonymous submission archive are different artifacts.

Required resolution: include applicable notices/attribution in the final package; preserve source-fetch URLs and hashes; inspect the exact final archive and PDF metadata for identity leakage. Re-run these checks after the new paid-pilot integration. The bounded no-match text scan in this review does not cover a future ZIP or PDF.

## Contribution and experimental-strength critique

The manuscript correctly acknowledges [sequential win-statistic designs](https://arxiv.org/abs/2410.06281), [anytime U-statistic inference](https://arxiv.org/abs/2605.14692), [off-policy confidence sequences with deployment gates](https://proceedings.mlr.press/v139/karampatziakis21a.html), and [causal win estimand distinctions](https://arxiv.org/html/2501.16933v4). These precedents make it difficult to defend a broad methodological novelty claim. A bounded hierarchy score plus a standard betting process and an intersection–union guardrail is mathematically sound, but is largely a specialization of known machinery.

The clearest empirical value is that the archived tasks expose disagreement between an ordered pairwise preference and marginal success. This helps motivate a reporting protocol. It does not yet demonstrate that this protocol chooses better deployable agents than a success-NI-plus-cost criterion, a Pareto display, or an elicited weighted utility. Those methods answer different questions; the experiment should compare their resulting decisions against a declared preference/constraint objective rather than label them worse solely for disagreeing with the proposed hierarchy.

The abstract foregrounds the invalid repeatedly inspected Wald baseline. That result is useful as a failure illustration but is not persuasive evidence of an advance over modern sequential evaluation. The paper already includes group-adjusted and fixed baselines and candidly reports normal-mixture conservatism. Strengthen the front-facing comparison by emphasizing the guardrail decision question, finite-sample assumptions, sample cost, and a strong calibrated existing betting or empirical-Bernstein procedure, not merely the contrast with an intentionally invalid baseline.

A small fresh τ pilot can establish implementation feasibility and real-run data provenance. It cannot by itself establish the production-A/B claim or the gain of the statistical decision protocol. Its value will be higher if it has frozen independent task-specific seeds, randomized run scheduling, exact budget accounting, uncertainty and failed runs retained, and a prespecified comparison of alternative decision rules. Treat task/seed count, not trajectories or tool calls alone, as the information scale.

## Resolution criteria

I would consider the empirical audit technically resolved when E1–E7 receive concrete manuscript/data/release changes or explicit scoped limitations in a response ledger, source hashes are regenerated only where warranted, and the final public tables/figures are checked against the frozen manuscript. Scientific novelty remains a separate open assessment even after those corrections. Further independent review should include a reviewer uninvolved in both the empirical code and theoretical drafting.
