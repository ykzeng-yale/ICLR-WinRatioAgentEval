# Session 60 results index (aggregated; updated by the 30-minute coordination loop)

Last updated: 2026-09-21T01:00Z. Owner: session `iclr-winratioagentevals-60`. All work is on `session60/*` branches and returned by pull request; the root session owns the manuscript, the release archives and integration. No commercial or proprietary model was called by this session; all fresh executions use open-weight models only (EXPERIMENT_POLICY.md on main).

**How to read this index.** "Integrated" means the root session copied or re-derived the material into its own files and reviewed it; it never means a pull request was merged wholesale. Numbers marked *descriptive* are counts and means of retained records. Numbers marked *model-dependent* are owner intervals whose assumptions the designs do not establish; the root paper **excludes** them. Current root state: main `6c6f6a1` (Round 14: owner-report cleanup accepted and closed), validated technical release `45e8ee2`, root-reported readiness 90%, remaining items author-only.

## Deliverables and their disposition

| # | Deliverable | Where | Last delivery head | Root disposition |
|---|---|---|---|---|
| 1 | Library fix for issue #4 in `src/wincs.py` (exact boundary laws, shift-invariant certified bounds, hedged betting CS, robust inversion, zero-count endpoint normalization) | PR #5, `session60/wincs-fix` | 5e91fcd | Root verification is limited to the zero-count betting endpoint arithmetic (Round 12: 3,465 ternary and 1,911 Bernoulli endpoint cases). The generic projection and width methods of the library remain separately unapproved and excluded from the paper, and the root does not import this interval implementation. PR open, not merged. |
| 2 | Sequential all-pairs U-statistic reference baseline (issue #3) | PR #7, `session60/contrib` | 88d6434 (accepted subset from ac17f59) | **Integrated (subset) in Round 10; issue #3 closed.** The other material on the branch (decision evidence on archived trajectories, replay, positioning notes, issue #6 fixes) is delivered but not integrated. |
| 3 | Open-model coding stream (issues #1/#2) | PR #8, `session60/local-stream` | c1da1c3 (Round 10 repair); report corrections 01f2381 | **Observations integrated in Rounds 11-12 with the root's own running-conditional-mean analysis and a descriptive same-task comparison.** Owner intervals excluded. Round 12 report corrections accepted in Round 13. |
| 4 | Open-model tau2-bench airline collection (issues #1/#2) | PR #8, same branch | 55fb1e5 (owner handoff); report corrections 01f2381 | **Integrated in Round 12 as descriptive batch-collection results plus an optional observed-array replay illustration.** Owner intervals and sensitivity-derived decisions excluded. Round 12 report corrections accepted in Round 13. |
| 5 | Drift / treatment-by-time / unequal-law null panel (issue #9) | PR #10, `session60/drift-panel` | e0f7dab (accepted files from ae3f0a5) | **Integrated in Round 10 (byte-for-byte reproduction); issue #9 closed.** |
| 6 | Round 13 owner-document cleanup (optional precision items) | PR #8 | be4b8e4 | **Accepted and closed by the root in Round 14** (both generators and manifests reproduced exactly); no effect on the paper. |

Issues #1 and #2 were **closed by the root on 2026-09-19 with an explicitly narrowed acceptance**: delivered collections and reviewed root analyses; broader confirmatory, live randomized-exposure and second-party / other-hardware replication ambitions are deferred optional extensions. The branch `session60/local-stream` follows main by merge commits (never rebased), so every recorded freeze and delivery commit stays reachable.

## Open-model coding stream

Design frozen at d9793d5; Qwen2.5-Coder-7B-Instruct 4-bit served locally; 591 MBPP-sanitized + HumanEval tasks; A single-shot versus B self-test-and-repair; 1,182 episodes, all retained.

Current owner report: `results/local_stream/report_v5.md` (= `report_v4.md` with one pointer corrected; v4 is the version the root reviewed). Governing wording: `experiments/local_stream/protocol_addendum_round12.md`. Superseded and preserved: `report_v3.md`, `v2_pre_round10/`, `v1_pre_round9/`. Data: `episodes.jsonl`, `monitor_pass1.csv`, `summary_v3.json`, `e2_cluster_v3.csv`, `pass_effects_v3.csv`, `data_manifest.json`, `release_anon/`. Figure: `figures_v3/fig2_running_nb.png`.

- *Descriptive.* Pre-registered H1 (B has higher success) is **not supported**: 433/591 successes in both arms (40 B-only, 40 A-only). B used 4.46x the latency (12.48 s versus 2.80 s), 4.46x the completion tokens, 7.4x the prompt tokens and 1,748 versus 591 model calls. Cross-arrival replay over 295 prespecified pairs: 69 wins / 18 ties / 208 losses, net benefit -0.471. Same-task net benefit -0.657.
- *Post hoc, conditional-mean reading (the kind of analysis the root retains, in its own implementation).* 95% normal-mixture band for the running conditional mean given the full frozen schedule: [-0.654, -0.288], below 0 from pair 60. This normal-mixture running-mean analysis and its pair-60 crossing are what the root retains. The harm e-process reading above threshold at pair 24 is **descriptive** under this reading; its anytime guarantee holds only under the iid-roster model (R2), which is excluded from the paper. Label of that reading: composite harm signal for B, incumbent A retained. The success guardrail of 0.03 is **not certified** by any interval or e-process.
- *Model-dependent owner intervals, excluded from the paper.* Betting CS under an iid-roster model [-0.628, -0.288]; task-level t [-0.705, -0.608]; cluster-robust t over 296 orientation-pair clusters [-0.7055, -0.6076] (needs cluster-level CLT conditions); exact cluster Hoeffding [-0.8145, -0.4986] (needs independent clusters).

## Open-model tau2-bench airline collection

A = Qwen2.5-7B-Instruct, B = Qwen3-4B-Instruct-2507, user simulator Qwen2.5-7B in both arms; llama.cpp; tasks 1-49 x 2 trials x 2 arms = 196 units; design frozen at 696fe57. Evidence type: **prospectively specified batch collection (all A, then all B) with a prespecified replay analysis**; shared trial seeds; one documented post-freeze operational amendment (deviation 1 with erratum). Not a live randomized exposure.

Current owner report: `results/tau2_open/report_final_v3.md` (= `report_final_v2.md`, the version the root reviewed, with nine precision replacements). Governing wording: `experiments/tau2_open/protocol_addendum_round12.md` and `protocol_addendum_round13.md`. Superseded and preserved: `report_final.md`, `report.md`. Data and accounting: `raw_gz/`, `episodes.csv`, `run_manifest.json`, `all_attempt_accounting.{md,csv}`, `unit_policy_flags.csv`, `round10_handoff_numbers.json`, `analysis_consistency_check*.json`, `release_anon/` (the deposited arm-A `logs_gz` and `raw_gz` archives contain account paths; an anonymous package must use `release_anon/`).

- *Descriptive.* 196 canonical units: 194 saved trajectories and 2 infrastructure placeholders scored as failures. 15/98 successes in each arm. Replay over 49 prespecified pairs: 10 wins / 30 ties / 9 losses, net benefit 0.020. Same-task: 28 / 141 / 27 over 196 comparisons, net benefit 0.005. Mean assistant tool calls 5.3 (B) versus 10.0 (A); mean agent generation time 84 s versus 128 s. No significance claim. 206 attempts, 12 discarded (all in the A collection); canonical totals omit at least 246,284 A-collection generated tokens (root reconstruction; role split unavailable). Equal observed success is not equivalence and not non-inferiority.
- *Optional observed-array replay illustration.* Conditional on the full retained array and the matching, under nominal independent fair replay coins: marginal 95% band [-0.609, 0.650] beside the known target 0.0102; final errors 0.010204 (net benefit) and 0.020408 (success difference). Marginal, not joint. No new-task, fresh-run or production inference.
- *Replay of the prespecified monitoring rule.* No e-process moved; abstention on the primary-rule comparisons.
- *Model-dependent owner intervals and sensitivity decisions, excluded from the paper.* Betting CS [-0.366, 0.406]; task-clustered t intervals; win-ratio CS; Welch intervals; hierarchy / tolerance, infrastructure-exclusion and omit-five sensitivities.
- *Unverified.* The actual sampler receipt inside the servers, an immutable decision chronology for deviation 1, complete failed-attempt usage.

## CPU-only studies

**U-statistic reference baseline (integrated subset).** `evidence/ustat_reference_report.md`, `results/ustat_reference/`. 8 scenarios x 2,000 replicates; 4 boundary nulls x 10,000. Asymptotic relative efficiency of all-pairs over disjoint pairs 1.13-1.41 for net benefit and 1.0 for the component gates. Monte Carlo false-rejection rates at the compliance-gate boundary: projection-Gaussian component rule 7.25% [6.76, 7.77]; simultaneous guarded deployment 1.83%; retained-crossing convention 7.11% (three distinct events); exact betting rule 0.76%.

**Drift / unequal-law null panel (integrated).** `evidence/drift_panel_report.md`, `results/drift_panel/`; protocol sha256 bb497cbb... 12 scenarios x 9 rules. Guarded betting ever-false-deployment under common drift 0.55% [0.42, 0.72] at the identical null and 0.38% at each guardrail boundary; repeated Wald 27-31%. Limitation: the normal-mixture rules never deploy in the alternating-component cells, so the alpha split is not demonstrated empirically there.

**Decision evidence on archived public trajectories (delivered on PR #7, not integrated).** `results/benchmarks/decision_matrix.csv`, `tau2_contrasts.csv`, `label_noise_sensitivity.csv`, `results/replay/`. 25 ordered contrasts; the compared rules disagree on 19; 9 priority inversions. These use archived third-party model outputs, not fresh executions, and their intervals carry the same model-dependence caveats as above.

## ArXiv phase: live randomized trial (#11) and its validation (#12)

Both are NEW work for the arXiv version, started 2026-09-19 after the ICLR abstract deadline passed. Neither has produced a scientific result yet, and nothing below is evidence.

**#11 live_ab — prospective randomized live-stopped A/B trial.** Branch `session60/live-ab`, head `5776877`. Directories `experiments/live_ab/` and `results/live_ab/`.
- Built to the root's design guidance (`reviews/arxiv_live_design_guidance.md`), adopted literally: the normal-mixture band is the decision rule, alpha .05 program / .0125 per trial / .00625 per band with one band serving both tails, delta = 0.03, current-full-enrolled-prefix only, no envelope, no retained crossing, enclosures starting at [-1,1].
- Status: **harness complete and green** (17 modules, 12,002 lines; 6 test files, 8,103 lines; **304 tests pass**; end-to-end mock dry run passes on four scenarios, no model and no network). Full pre-registration record in `experiments/live_ab/design/`.
- **No trial episode has been run and nothing is frozen.**
- **Blocked on host quiescence, not on code.** Another project (`DTR-AgentEvals`, a different session, launched with `--allow-contention`) has been holding this host's GPU with two `llama-server` processes since 2026-09-19 13:41. The frozen hierarchy is success > cost with cost = latency_s and the pilot ties on success, so nearly the whole composite effect rides on the latency tier; latency measured under foreign load is not a measurement of the two workflows. A preflight quiescence gate is required before the freeze. Those processes will not be killed.
- Two errors of mine, corrected publicly rather than silently: the claim that a deploy was "unreachable whatever the outcomes" (false: it is a condition on the observed data, and a verified counterexample deploys at n = 100), and a merge statement of "0 root-owned files modified" produced by a filter that did not cover `results/`.

**#12 live_ab_validation — independent CPU validation of that monitor.** Branch `session60/live-ab-validation`, head `3db00ba`. Independence is **procedural, not organizational**: the band and fixtures were written from the guidance formula alone by agents that never read the #11 monitor, which is loaded by hash only at the comparison step.
- **The v1 grid RAN** (`results/live_ab_validation/`): T1, 28,000 programs, 112,000 trials, 224,000,000 enrolled pairs, 86.4 s, 89.8 MiB peak, determinism re-run byte-identical. The root independently reconciled 336,000 saved construction records, ten source hashes and 480 aggregates.
- **Positive control PASSED and survives re-examination**: the deliberately invalid rule is flagged in all three precommitted cells, Wilson lower limits 0.81 to 0.9996 against a nominal 0.00625. *Descriptive of the synthetic cells.*
- **The adapter shows no exceedance flag** in any cell, on any gate, at any horizon. Worded as no exceedance detected at this resolution, never as the bound holding. *Model-dependent on the frozen cells.*
- **Known defects, both conceded to the root.** The last-look reduction is NOT exact for the two completed-data baselines; the root's witness reproduces exactly; 12 deposited rows move under the batched reading and 77 under the finest, every one understated; the adapter is untouched and the positive control survives. And the root's further witness of a missed drain-tick crossing at lower bound +0.0133027164 is **not yet fixed** and is v2 work.
- **The comparison against #11 is a CONTRACT MISMATCH, not 122,786 findings**: it compared two differently-declared enclosure policies, so every disagreement was guaranteed. It becomes meaningful only after the pins are matched and the grid re-run, which is v2.

**Numbers I have withdrawn, listed so they are not quoted from older comments.** "A deploy is unreachable whatever the outcomes" — false; it is a condition on the observed data. "The published method misleads practitioners by 11x" — the paper makes no sample-size claim at all, and the like-for-like estimator gap is **2.55x**. The percentage apportionment of the shortfall (27.5 / 22.6 / 49.8) — withdrawn, because it divided a deterministic path calculation by a powered floor. What stands: **17,097 against 6,697 pairs, both path calculations under one convention.**

## v2 executable milestone (#12), 2026-09-21 — DELIVERED, not cleared to run

Branch `session60/live-ab-validation`, head `98bbbbc`. Root's ranked actions 1 and 2. **None of this is
calibration, a coverage rate, or a power statement.** Convention: *deterministic-path* throughout.

**The runner now executes the deployed policy.** `vrun`'s calibration path took ideal-ORACLE states via
`vgen.adapter_tick_sums`/`state_at_age` with no operational selection, while `vcompare` selected
`vpolicy.OperationalMonitor` — so the matched-policy conformance I had reported rested on a runner that
never ran the policy. `RunConfig.policy` + an `operational` reading in the threshold tables + per-policy
`breakpoint_ages` fix it.
- **5,772,240** reachable pair-states compared against `vpolicy` via **3,570,720** distinct evaluations:
  **0 mismatches**. Every atom x both arm orders x every delay in the frozen blocks x every age x both
  reveal cases.
- Difference array == brute-force per-tick evaluation, 16 (draw, policy) pairs, full drain axis.
- The seam is live, not decorative: **127** differing ticks over 8 cells x 6 programs, operational
  containing oracle at every one. *(At one cell, n=60, it differed at zero ticks — scanning all eight is
  what showed it live.)*
- v1 default stays `oracle` and **refuses** an operational config rather than returning oracle numbers
  under an operational label.

**`vpanel.py` — the versioned end-to-end entry point** (`experiments/live_ab_validation/results/panel_fixture/`).
Operational primary **plus** both complete-information reference bands on the **same latent draws**;
one call per score per trial; bands indexed at declared prefixes; separate artifact; immutable receipt.
Deposited fixture: 12 trials, **24 reference calls = 8/program**, **48** retained band rows
(12 x 2 scores x prefixes [100, 300]), **12,612** pair-states verified against `vpolicy` during the run.
The previous timing helper computed the bands and **assigned them to nothing**.
- One-way dependency is structural and source-checked: the primary modules may not name the reference.
- 27-test fixture drives the real entry point, never `vcompare`. Boundary coordinate pinned by value:
  **C1, program 1, trial 3, tick 6, pair 1** — revealed cost 10.0 vs pending elapsed 10.526315789473685,
  oracle `[-1,-1]` vs operational `[-1,0]`, forward margin **exactly 0.0**. Same class as the root's
  C2/2011, C3/2160, C7/2090.
- **Negative result recorded, not implied:** no drain-window *decision* at fixture scale — 192 trials at
  n_max 400 and 1,000 gave zero `tau > N_max` and zero schedule disagreements. The root's tick
  1200 -> 1010 witness is a *constructed* one and measures the **look schedule**, not the policy.

**Total-workload guard v2.0.0** (`results/live_ab_validation_v2/total_workload_guard_demonstration_v2.json`).
v1 compared `total > cap`, and `nan > cap` is **False**, so a NaN reference time **authorized**; so did a
negative total. v1 also checked only `seconds` while the config caps three quantities, authorized on
scaled H-only arithmetic with no combined receipt, and priced the automatic tier before overrides.
**12 tripped cases now all refuse and all raise; 9 new unit tests; the positive control still authorizes.**
- **Consequence:** under guard v2 the **current committed projection does NOT authorize execution**
  (`identity_unverifiable`) — the committed combined receipt carries no identity fingerprints and no
  planned-group accounting. Correct fail-closed answer, not a regression. **Nothing in the repository
  today authorizes a full grid, a calibration panel or a live trial.**

**Manifest reconciled.** `PINNED_V2.json` `detail` held a stale `lab_enclosure` sha256/bytes/blob while
`files` held the current one — the manifest disagreed with itself. The **verifier** was the reason it
survived: it checked only the `files` map. It now cross-checks `files` vs `detail`, every
sha256/bytes/git_blob against live source, and source-commit reachability. Regeneration history is now
carried forward by the builder instead of being silently dropped on rebuild.

**Deviation receipt filed** (`results/live_ab_validation_v2/DEVIATION_RECEIPT_rerun_20260921.{md,json}`).
The **39,800 drain looks / 51 disagreements** I reported from a broader rerun have **NO surviving
artifact** — withdrawn from circulation, not reconstructed, not re-run. Absence verified (no stash; the
one dangling blob is a 163,886-byte PNG; no logs). Surviving committed receipts tabulated with digests:
22,523 / 24,115 / 24,115 look rows, 1,592 drain-look rows in each all-look receipt, no tracked file
modified.

**Tests:** 184 validation + 27 panel + 86 design pass.

**Still true:** zero live episodes, zero v2 calibration cells, no freeze. Host contention ~38 h.

**Identity reconciliation, 2026-09-21** (`results/live_ab_validation_v2/IDENTITY_RECONCILIATION_20260921.json`,
tool `experiments/live_ab_validation/videntity.py`). *Convention: deterministic-path; no timing measured.*
- The combined receipt's pinned **`vrun.py` source exists in NO object in the repository** (all 1,341 blobs,
  reachable and unreachable, hashed). It was timed against an uncommitted file. `vgen.py`, `vband.py`,
  `vresource_check.py` pins **are** recoverable. The root's requested reconciliation is permanently
  impossible for `vrun`.
- **The timed core DID change** across the operational-policy work: 5 members changed
  (`vgen.adapter_tick_sums`, `vgen.state_at_age`, `vrun.RunConfig`, `vrun.build_series`,
  `vrun.build_series_v2`), 2 added. So "a whole-file difference alone does not prove the timed core
  changed" does **not** rescue the old projection — the executable structure of the timed scope moved.
- **Consequence:** guard v2's `identity_unverifiable` refusal is correct **on the merits**, not on a
  technicality. 33 panel tests pass (6 new identity tests, both directions).

**Root's identity ruling acted on, and the AUTHORIZED BOUNDED MEASUREMENT delivered, 2026-09-21.**
Head `93cc628`. Root disposition `reviews/v2_panel_root_disposition_20260921_0750.md`.

*My timed-core identity was refuted and is withdrawn from any authorizing role.* I reproduced all
three of the root's counterexamples against this tree first: changing `vgen.OPERATIONAL_EPS` from
`1e-9` to `1.0` leaves the fingerprint **identical** while flipping the forward certificate at
revealed cost 10 vs pending 11; a partly-missing entry point still returned a digest; `vpanel` and
`eb_reference` were outside its own scope. `videntity.identities()` is **removed**; the three
counterexamples are kept as regression tests asserted in the refuting direction. Binding is now
`vpins.py`: **whole-file pins** over orchestrator, primary, reference bridge, vendored manifest,
compiled `.so`, output/accumulator and guard, with a before/after drift check.

*The entry point now calls the guard* — the root's sharpest point was that a correct helper protects
nothing if nothing calls it. Three modes: fixture (bounded, enforced), measurement (allowlist +
caps), full_grid (refused through the real guard). Non-frozen `alpha_gate` and `trials_per_program`
are **refused**: alpha was used by the reference and *ignored* by the primary, so a run at 0.5 would
have paired a 0.5 reference with a 0.00625 primary and called them one experiment.

**THE MEASUREMENT** — `results/live_ab_validation_v2/measurement_20260921/MEASUREMENT_RECEIPT.json`.
*Convention: **descriptive**. One observed pass under recorded concurrent load. NOT calibration, NOT
a coverage rate, NOT an uncontended benchmark, NOT a guaranteed upper bound.*

| quantity | observed | cap | authorized |
|---|---|---|---|
| wall clock | **7.901 s** | 300 s | — |
| peak process-tree RSS | **69 MiB** | 2 GiB | — |
| output bytes | **63.9 KiB** | 200 MiB | — |
| trial evaluations | **80** | — | 80 |
| reference calls | **160** | — | 160 |
| units / seed-program identities | 20 / 10 | — | 20 / 10 |

Per horizon: 65 ms/trial at n=1000, 133 ms/trial at n=2000 — the ratio of **two measured points**,
not a fitted exponent and not a full-grid projection. Both passes complete, zero cap events, 2
attempts / 0 failures, no retry, no alternative seed selection. Source pins identical before and
after each pass. Host load 2.49 on 10 cores; the two foreign `llama-server` processes (DTR-AgentEvals
— its `code_routing/config.json` declares ports 8193/8191, exactly those held) sat at 0.0% CPU and
~11.7 MiB RSS and were not touched.

Effect summaries withheld and never accumulated. **Disclosed rather than left to inference:** the raw
primary output does carry per-trial decision labels, because writing it is part of the measured
workload; I did not aggregate or inspect them. A first pass that wrote decision *counts* into the
receipt was discarded uncommitted (`41c5991`).

Tests: 184 validation + 48 panel + 86 design.

**Preflight-only amendment returns T1 under the cap, 2026-09-21.** Head `4f62df1`. Root disposition
`reviews/v2_measurement_root_disposition_20260921_0828.md` (milestone accepted, +5 → **65%**).

*Convention: **descriptive** measurement, then **deterministic same-horizon extrapolation** by program
count (root's own method, no fitted exponent), conditional on recorded load. NOT a measured grid, NOT
calibration, NOT clearance.*

`results/live_ab_validation_v2/measurement_preflight_20260921/FINDING.json`

| | verified mode (delivered) | preflight-only (new) |
|---|---:|---:|
| h2000 s/program | 0.530730 | **0.095585** |
| **T1 @ 28,000 programs** | 14,860 s — **ABOVE** 5,400 s cap | **2,676 s — BELOW** |
| pair-state checks | 420,080 | **10,502** |
| persisted primary + reference digests | baseline | **all four IDENTICAL** |

**The amendment changed no persisted scientific byte** — that is the proof the root required, done over
whole-file digests with no effect value displayed. *Caution kept with the number:* the 5.55× ratio is a
difference of **two single passes at different times under possibly different load**, not an interleaved
paired causal estimate.

Parent-supervised whole operation (`vsupervise.py`): **1.747 s** / 300 s cap, **69.2 MiB simultaneous
process-tree RSS** / 2 GiB, 103,713 B / 200 MiB. No breach; no foreign process touched. Supervisor
signals only the process group it creates. Four synthetic fixtures prove the caps trip — including a
tight loop an in-worker check could never interrupt — and a clean run passes, so they are not
always-fail. Counts exactly as authorized: 20 units / 80 trials / 160 reference calls.

**Pins now cover what actually ran:** nine `sys.modules` entries (comparecast, submodules, `confseq`,
the real compiled `.so`, and `__pycache__` bytecode), replacing a manifest hash and a `.so` glob.
Verification and reference modes are bound into the pin identity. Reference rows are **streamed**, so
reference memory is O(1) in grid size.

**Accounting corrected without rerunning** (`measurement_20260921/ACCOUNTING_CORRECTION.json`): the
`uncompressed_total` of 3,291 was the *compressed* sum; true decompressed primary **48,262 B**, all
uncompressed data **110,374 B**, data artifacts **65,403 B**, all seven files **99,631 B** — all
independently recomputed and matching the root's figures. RSS relabelled as getrusage self/reaped-child
scope. **Attempts restated: 6 cumulative measurement-mode executions, not 2** (a cap control, two
contaminated passes, a leak check, two delivered). Discarded artifacts confirmed **irrecoverable**
after searching Trash, scratchpad, system temp and all git objects.

Tests: 184 validation + 58 panel + 86 design.

**Conformance diagnostic — CLAIM NARROWED by root, and removed from the runtime path. 2026-09-21,
head `5d744b4`.** `experiments/live_ab_validation/vconformance.py`, receipt `CONFORMANCE_RECEIPT.json`.

*Root's exact wording, which is the only claim this makes:* **"Threshold tables and representative
per-pair states agree on the checked finite design; extension across ages relies on the reviewed branch
structure of the pinned implementation."** Explicitly **not** universally complete conformance, and not
a new theoretical result.

**My earlier "complete by construction" framing here was over-claimed and is withdrawn.** I argued the
enclosure has breakpoints only at the two certificate thresholds. The full pair process also has the
first-reveal boundary `f` and the resolution boundary `d` — and the refutation was in the module I was
reasoning about: `vgen.BREAKPOINTS_PER_PAIR = 5`, difference array stacking `{0, f, a_narrow,
a_collapse, d}`. **Five, not two.** The three-piece argument holds only *within the partial-observation
branch* (`age ∈ [f, d)`, positive delay); resolved and unrevealed are separate transitions checked as
their own cases.

**Removed from `run_panel`.** The unconditional call I added is gone; the previously accepted
preflight-only workload and its **one-draw smoke test** stand unchanged, because that workload's
resource planning was already accepted at that exact shape. Runtime use is **NONE**. The checker now
pins **itself** (it previously pinned only its subjects) and records its version.

Does not establish: aggregation, the event schedule, the full generation-to-state mapping, stopping
inference, empirical calibration, or absence of untested transitions after future code changes.

**T1 LAUNCHER AND MANIFEST DELIVERED FOR REVIEW — execution uncleared. 2026-09-21, head `dedab44`.**
Root disposition `reviews/v2_precalibration_root_disposition_20260921_0909.md`: **resource ledger
accepted, timing objection CLOSED.**

*Accepted planning ledger (root's own figure): T1 = **2,676.3868 s (44.61 min)** at horizon 2000.
Convention: descriptive measurement + deterministic same-horizon extrapolation, conditional on the
C1/C2 mixture and recorded load. **Does not guarantee all eight cells finish within 5,400 s** — C3–C6
are unmeasured at this scale.*

`results/live_ab_validation_v2/T1_MANIFEST.json`, `T1_DRY_RUN.json`, code `experiments/live_ab_validation/vlaunch.py`

| frozen T1 request | |
|---|---|
| cells | C1/C2/C7/C8 @ 2000 · C3–C6 @ 5000 |
| programs / trials / reference calls | **28,000 / 112,000 / 224,000** |
| horizon · trials/program · namespace | 2000 · 4 · **0 (replay seeds)** |
| policy · schedule · verification | operational · tick-batched · **preflight-only** |
| caps, **cumulative over the whole job** | 5,400 s / 2 GiB tree RSS / 200 MiB — **not reset per shard** |
| exposure | **`fresh_holdout = False`**, prior development exposure, no switch |
| clearance | **NOT CLEARED**; dry run evaluates **0 trials** |

**13 malformed/unsupported requests refused by name** (changed allocation, partial grid, unknown cell,
non-integral / negative / boolean counts, NaN and infinite horizons, wrong namespace, oracle policy,
per-trial verification, non-frozen alpha, reference disabled) — and the frozen request still validates,
so they are not always-fail.

**Four named defects repaired.** `verify_policy=False` refused in measurement/full-grid (unpinned, so
disabling verification would be invisible); an **absent baseline file now raises instead of counting as
a match**, and a hash mismatch returns nonzero; supervisor/driver/conformance/launcher added to
whole-file pins; `uncompressed_bytes` repaired at source (it repeated the *compressed* size) and
additively for deposited receipts without rerunning.

**Supervisor hardened:** available RAM measured (not inferred from total/free) and a shortfall or
unmeasurable value refuses to start; a failed `ps` call is now a **breach, not a zero** — it previously
read as "no memory in use" and silently stopped enforcing the cap; process-group id captured while the
leader is alive; receipt bytes reserved; sampled RSS explicitly **not** an instantaneous hard bound.

**Attempts kept separate:** 2 preflight executions recorded apart from the old 6 (different
executable), cumulative 8 — not summed.

Tests: 184 validation + 79 panel + 86 design.

**T1 SHARD EXECUTOR + RECEIPT CONTRACT IMPLEMENTED — execution still uncleared. 2026-09-21, head
`44d05ee`.** Root spec `reviews/v2_launcher_root_disposition_20260921_1022.md`; plan
`evidence/t1_shard_plan_20260921_1022.json`. *Convention: **design-based** (plan verification and
orchestration checks). No scientific grid run, no native reference called, no effect value read.*

**Root's shard plan verified independently before building on it:** 56 shards × 500 programs, **28,000
unique coordinates, zero duplicates, zero gaps**, order = ascending block then C1→C8, sequences 1–56
exactly once; totals 112,000 trials / 224,000 reference calls / 336,000 primary rows / 672,000
reference rows.

`experiments/live_ab_validation/vshard.py` + `tests_shard.py` (**16 tests, synthetic stubs only**):
attempt-specific partial directory → counts, coordinate coverage and hashes reconciled **before**
publication → **atomic rename**. A completed receipt is never overwritten; an incomplete attempt is
never deleted or reused. **Per-shard peak memory is recorded `unknown`**, not derived from a whole-job
maximum. Cumulative counters; caps never reset per shard. Final completion requires all 56 ids once,
disjoint+complete coverage, reconciled counts/hashes/pins, successful supervision and no cap event —
**`within_caps` or exit 0 alone is explicitly insufficient**, and a test asserts it.

**Both supervisor repairs I had left incomplete are now done**, and saving the group id was *not* the
fix: escalation returned as soon as the **leader** exited, so a descendant ignoring SIGTERM survived and
SIGKILL was never sent. Completion is now decided by whether the saved group still has members (probed
with signal 0). Tree enumeration no longer degrades to leader-only on a `ps` exception — that let RSS
sampling of a subset *succeed while undercounting*. Both calls now sit in the same handler and route to
the failure receipt.

**Manifest regenerated from a clean tree** (`T1_MANIFEST.json`, identity
`0730f77ac66954bd…`). The root found the prior one was built from a **dirty pre-commit tree** — its own
pins said `validation_tree_dirty: true` and two digests were stale; both confirmed, and it is retained
as a marked historical draft. The manifest now binds the **canonical execution spec** (allocation, shard
plan digest, full 56-shard order, cumulative caps, accepted resource-ledger digest) instead of an empty
program list, and launch compares that identity — a reusable clearance string can say *a* decision was
made but never *what* was reviewed.

Tests: 16 shard + 83 panel + 184 validation + 86 design.

**T1 EXECUTOR COMPLETE AND UNRUN — production runner wired, completion accounting repaired.
2026-09-21, head `6a0c2bd`.** Root spec `reviews/v2_executor_root_disposition_20260921_1058.md`.
*Convention: **design-based** (orchestration checks with injected stub scientific functions). No grid
run, no native reference called, no effect value read.*

**Four defects the root found, all real, all verified before fixing:**

| defect | consequence |
|---|---|
| `published_dir` assigned **after** serialization + rename | on-disk receipt lacked it → **successful publication could never finalize** |
| `counts_ok` omitted `reference_rows` | a shard emitting **zero** reference rows reconciled |
| coordinates checked by **cardinality** | a uniformly **shifted** range of the right size passed |
| attempt accounting never reconciled | **`completed=0, failed=4` published as complete** when row totals matched |

Also: the identity hashed the execution spec only, so **changing a source pin left it unchanged**;
`allow_missing=True` was set **unconditionally** in the production caller, reopening by default the gap
the flag narrows; and `launch()` reported completion from `within_caps` alone — the root's mocked
launcher returned **complete with zero shards**.

**Now:** identity folds in source/config/loaded-reference/environment bindings (volatile timestamps
excluded) and is **mandatory** + CLI-exposed — verified both ways, a one-comment change to `vgen.py`
moves it and restoring the file restores it exactly. Zero shards with `within_caps=True` now yields
`scientific_completion: False` with six named failing conditions. `vshard.py`/`vprod.py` pinned; ledger
digest may not be null.

`vprod.py` is the production runner over the **accepted** scientific routines with explicit indices,
closing both files before reconciliation. `vlaunch.run_child` iterates the fixed 56-shard plan serially
under one parent window and writes a terminal job receipt; a shard error stops the attempt and returns
an incomplete study — no retry, no resume.

**24 shard tests** (incl. a positive roundtrip and refusals through the **real** orchestration with stub
science) + 83 panel + 184 validation + 86 design.

Manifest regenerated at clean `a137d39`; identity `c3d4bce5021d3a3f…`. **Clearance: NOT CLEARED.**

**T1 PARENT-CHILD INTEGRATION CLOSED — executor complete and unrun. 2026-09-21, head `8582e58`.**
Root spec `reviews/v2_prerun_root_disposition_20260921_1136.md`. *Convention: **design-based**
(orchestration checks, stub scientific functions). No grid run, no native reference, no effect read.*

**The blocker: a successful child could not exit successfully.** `run_child` passed `supervision=None`
into `finalize_job`, which then required successful supervision and no cap event — two conditions the
child cannot observe — so it returned 6, and the nonzero exit failed the parent too. Finalization is now
two-stage: the child's **data** stage reconciles data/pins/accounting only; the parent's **final** stage
adds actual terminal supervision. Both receipts are preserved separately (`T1_CHILD_DATA_RECEIPT.json`
and `T1_JOB_RECEIPT.json`) — **they previously wrote the same filename, so the parent overwrote the
child's.**

| other defect | what it did |
|---|---|
| parent finalized with `job_id="T1"` and **fresh zero counters** | observed totals real, cumulative counters zero, elapsed = monotonic clock − 0 |
| bindings checked against **each other**, not the context | a fixture with a different manifest, source pin and job passed finalization |
| `run_child` without identity | **published a shard against unreviewed source** |
| terminal elapsed **recomputed but never compared** | a 2 s run under a 1 s cap reported `within_caps: true` |
| runner caught a trial exception and **continued** | an injected first-trial failure still ran the three later trials |

All repaired: deterministic `job_identity()` carried through both stages with the child's real counters
restored; bindings must equal the frozen context and an unbound finalization fails outright; identity
mandatory in the child; terminal elapsed checked with earlier breaches preserved, plus a parent-side
check covering its **own** hashing and metadata writes and the final all-artifact byte total with no
reset; the runner stops at the first failure, still closing both handles.

**31 shard tests**, including a positive roundtrip through `launch` → **actual** `run_child` with an
intercepted supervisor reaching **child exit 0 and final completion true**, and shard-error / cap /
missing-identity cases all remaining incomplete. Plus 83 panel + 184 validation + 86 design.

**Environment stays in the identity binding**, per the root's ruling — it describes the execution host,
not the reviewer's. New identity `18ad539884566215ff…` at clean `f63553a`. **Clearance: NOT CLEARED.**

**Per-shard count derivation — read-only, identity undisturbed. 2026-09-21, head at post time.**
`results/live_ab_validation_v2/T1_COUNT_DERIVATION.json`. *Convention: **design-based** derivation from
frozen constants; not a measurement.*

Closes an uncertainty I had flagged twice: the plan **asserts** 6,000 primary / 12,000 reference rows
per shard and the runner **independently produces** them, with nothing cross-checking the two. A
disagreement would fail every shard at reconciliation *after* burning budget. They agree exactly —
500 × 4 × 3 = 6,000; × 2 scores × 3 prefixes = 12,000; job totals derive to the declared
112,000 / 224,000 / 336,000 / 672,000.

Residual assumption also closed: the runner's `n > arr.size` prefix-skip branch would silently emit
fewer reference rows. Draw arrays are exactly `n_max` long and the largest prefix equals the horizon, so
**the branch is unreachable at horizon 2000** — checked in the **fixture** namespace, deliberately not
the T1 replay namespace.

Establishes nothing about runtime, coverage, power or effects, and nothing about C3–C6 cost. Manifest
identity verified unchanged at `18ad539884566215ff…` before and after.

## Open requests

None from the root. Root-side open items: disposition of PR #5 and of the non-integrated parts of PR #7 and PR #8 (no whole-PR approval is implied by any integration). Author-only items, which no agent can do: abstract submission on OpenReview (deadline 2026-09-18 23:59 AoE = 2026-09-19 11:59 UTC = 07:59 EDT), OpenReview profile and reciprocal-review eligibility, human scientific review, AI-use disclosure, originality and concurrent-submission declarations.
