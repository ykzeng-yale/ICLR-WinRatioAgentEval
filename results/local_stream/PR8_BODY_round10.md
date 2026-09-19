<!-- Corrected PR 8 description (Round 10 audit, finding 6). For the coordinator to post; this file does not post anything. -->
# Session 60: open-model prospective evidence (local coding stream + tau2 airline)

**Read first:** `results/local_stream/report_v3.md` (current report; supersedes `report_v2.md` and `v1_pre_round9/report.md`). Protocol: `experiments/local_stream/protocol.md` (frozen), with the POST HOC addenda `protocol_addendum_round9.md` and `protocol_addendum_round10.md`. Every interval below is quoted **with its assumption label**; the earlier PR text (uncorrected CS [-0.618, -0.301], "before any outcome", "every fixed-horizon rule agrees", a causal explanation of the E1/E2 gap) is withdrawn.

## Local coding stream (one local open-weight model, no commercial model call)

- **Design.** A `single_shot` versus B `self_test_repair` on a fixed roster of 591 tasks (427 MBPP-sanitized + 164 HumanEval), `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` on one machine. Pass 1: randomized sequential laboratory stream of 295 disjoint pairs with AB/BA orientation coins (one task unpaired); pass 2: the complementary workflow on every task. **Design frozen before design-task outcomes** (smoke checks and a 6-task out-of-design timing pilot called the model earlier and are disclosed). Internal timestamped freeze, not an external registration. All 1,182 planned episodes were run and retained.
- **Primary hypothesis H1 (B has higher hidden-test success): not supported; negative result retained.** Both workflows succeed on 433/591 tasks (40 B-only, 40 A-only). B uses 2.96x the model calls, 7.42x the prompt tokens, 4.46x the completion tokens and 4.46x the mean latency of A.
- **E1, cross-arrival contrast (295 pass-1 pairs):** 69 wins / 18 ties / 208 losses for B, NB = -0.4712.
  - **R1 (running conditional mean of the pair scores given the stated filtration; bounded scores only; POST HOC, rho fixed after outcomes were seen):** 95% normal-mixture CS **[-0.6540, -0.2883]**, upper bound first below 0 at pair 60. The pair-mean formula and any link to a roster-level target need an additional stable episode-law model and are not claimed. Success-difference CS [-0.1320, 0.2337]; the two intervals are not a joint 95% region.
  - **R2 (iid-roster MODEL: unconditional inference over hypothetical iid rosters with independent stable episode laws; not a guarantee conditional on the curated benchmark):** corrected hedged betting CS **[-0.6281, -0.2880]**, below 0 from pair 42 (stays below from pair 50); success-difference CS [-0.0786, 0.1794]; decided-pair win-ratio CS [0.2010, 0.5299].
  - **Monitor / decision wording: "composite harm signal for B; incumbent retained".** The harm e-process was first read above log 20 at pair 24; win and success-gate processes never crossed; nothing was stopped or deployed. The crossing is descriptive under R1 and carries its anytime guarantee only under the R2 model. It is an unfavourable result for B on the prespecified composite (driven by the latency tier), not a success-rate or safety harm and not a reverse guarded approval of A.
- **E2, same-task contrast (591 tasks): NB = -0.657** (-0.6565).
  - Model-based task-level intervals (valid under independent task scores with stable task-specific episode laws and no relevant pass/period effects; the t interval also needs a Lindeberg / variance-growth condition and is approximate): t [-0.7053, -0.6077] (SE 0.02485); Hoeffding [-0.7682, -0.5448].
  - Orientation-pair cluster intervals (G = 296: the 295 design pairs that shared an AB/BA coin + the unpaired task; target = assignment-averaged same-task preference over the roster; **independent clusters is still an assumption**, shared machine state is not excluded): cluster-robust t [-0.7055, -0.6076] (SE 0.02488, approximate); exact final-time cluster Hoeffding [-0.8145, -0.4986] (radius 0.15794).
  - The Round 9 description of the E2 intervals as free of assumptions / conservative by construction is withdrawn (two-task counterexample in `report_v3.md` section 4).
- **Success guardrail: not certified.** Same-task success difference 0.000; the -0.03 margin is not certified by any reported interval (t-type lower ends -0.0297 / -0.0295 only under their models and a normal approximation; Hoeffding lower ends -0.112 / -0.158). The online gate did not cross.
- **E1 versus E2 (-0.471 versus -0.657): descriptive only.** Different targets, shared episodes, different unit counts and exposure passes; no joint uncertainty and no causal mechanism is claimed for the difference.
- **Round 10 code repair.** `src/wincs.py` endpoint arithmetic (`0 * log 0 = 0`; capital exactly 1 at n = 0 and at degenerate endpoints) with new tests; the regenerated v2 numbers are compared with the Round 9 files in `results/local_stream/v2_vs_v3_numeric_check.json`.
- **Reproduce (CPU only, no model call):** `.venv/bin/python experiments/local_stream/run_v3_all.py`; hashes in `results/local_stream/analysis_v3_manifest.json`. Raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `design.*`) is byte-identical to the original run; v1 outputs in `v1_pre_round9/`, Round 9 outputs in `v2_pre_round10/`.
- **Anonymous release copies:** `results/local_stream/release_anon/` (explicit allowlist; regeneration is location-dependent, no byte-for-byte portability claim).
- **Scope.** One 7B 4-bit model, one machine, public benchmarks with likely training overlap; laboratory stream, not a production experiment.

## tau2 airline (open model)

- **Collection COMPLETE: 196/196 planned units recorded** (49 airline tasks x 2 trials x 2 arms).
- **Both arms: 15/98 successes.**
- **Guarded decision = abstention (inconclusive).**
- **Batch collection with prespecified replay analysis** (all of arm A, then all of arm B; the temporal decisions are a replay of batch-collected outcomes, not physically randomized arrivals, live stopping savings or a production A/B test).
- **Deviation 1 disclosed** (post-freeze operational amendment; see the tau2 report and addendum).
- Final report and verification: under `results/tau2_open/`.

tau2 report: results/tau2_open/report_final.md
