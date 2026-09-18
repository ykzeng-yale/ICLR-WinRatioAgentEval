# Empirical feasibility and provenance audit

Audit date: 2026-09-18 UTC (2026-09-17 US Eastern). This is a source and design audit, not a claim that the proposed experiments have been completed. Comparative outcome summaries were inspected during this audit; the accompanying protocol is an analysis plan, not a registered prospective preregistration.

## Main recommendation

Use the original released τ²-bench trajectories for the primary conversational-agent case study and SWE-bench Lite trajectories for an independent coding-agent case study. These contain actual outputs of deployed language models executing agent workflows. They are historical **offline benchmark runs** with simulated users or software tasks. Reordering or sampling their outcomes supports a **sequential replay experiment**; it does not establish the performance of a live production A/B experiment.

Keep simulation experiments as the main evidence for continuous-monitoring validity, empirical benchmark reanalysis as evidence of useful metric disagreements, and a prospective online design as an explicitly unexecuted deployment protocol unless new genuinely randomized runs are collected.

## Source 1: original τ²-bench release trajectories

Repository: [Sierra Research τ-bench repository](https://github.com/sierra-research/tau2-bench). Download snapshot commit: `b7ea9074c1cba482b30687fecdb5c8425fd6f619`. Original source folder: [data/tau2/results/final](https://github.com/sierra-research/tau2-bench/tree/b7ea9074c1cba482b30687fecdb5c8425fd6f619/data/tau2/results/final). Reference: [Barres et al., 2025, τ²-Bench](https://arxiv.org/abs/2506.07982). Repository [MIT license](https://github.com/sierra-research/tau2-bench/blob/b7ea9074c1cba482b30687fecdb5c8425fd6f619/LICENSE) was downloaded and inspected; preserve the supplied notice with redistribution.

Local raw files are in `work/empirical_sources/`, with exact source URLs, download times, byte counts, and SHA256 hashes in `work/empirical_sources/manifest.json`. Filenames retain original model, domain, simulator, and trial metadata with an added `tau2_` prefix.

| Domain | Tasks per model | Runs per model | Main-run embedded code commit |
|---|---:|---:|---|
| Airline | 50 | 200 | `c30d59aaa71c65f9b9eb6a8f8636b48945028fcf` |
| Retail | 114 | 456 | `c30d59aaa71c65f9b9eb6a8f8636b48945028fcf` |
| Telecom | 114 | 456 | `f125e68a2cdc6161f11a4c611413ea4a0918edac` |

There are four trials per task. The strict-comparability main set is GPT-4.1 (`gpt-4.1-2025-04-14`), o4-mini (`o4-mini-2025-04-16`, high reasoning effort), and Claude 3.7 Sonnet (`claude-3-7-sonnet-20250219`): 3,336 runs across three domains. GPT-4.1-mini adds 1,112 runs, for 4,448 total downloaded. Its embedded harness commit is `ade39493be54aad326a4c65295f77fe09780329b`; use it as sensitivity evidence unless a code/configuration comparison establishes equivalence. Every model has exactly matching task definitions within each domain, matching task/trial seed assignments, and matching user-simulator configuration (`gpt-4.1-2025-04-14`, temperature 0). Equal seeds do not establish identical model stochasticity or a real-user counterfactual coupling.

Schema:

- `info.agent_info.llm`, `info.agent_info.llm_args`, `info.git_commit`: system identity and run provenance.
- `tasks`: the exact task definitions embedded in that historical evaluation.
- `simulations[]`: one trajectory; `task_id`, `trial`, `seed`, `id`, timestamps.
- `reward_info.reward`: recorded 0/1 task reward. Every inspected record has a binary value. Preserve original verifier labels as such; they are not fresh human judgments of correctness.
- `agent_cost`: historical recorded model-inference expenditure in USD; `user_cost` is simulator expenditure and should be reported separately.
- `messages`: complete visible interaction. Count assistant tool calls by summing the lengths of `tool_calls` arrays only for messages whose role is `assistant`. User tools in the dual-control environment are a distinct metric.
- `duration`: total simulation wall-clock duration, including the user simulator and environment; it is not isolated production-agent latency.
- `termination_reason`: preserve capped and unsuccessful runs; do not analyze successful runs only.

Integrity checks completed on all 4,448 records: complete/nonnegative agent cost and duration; complete trial/seed/reward; exactly four runs per task; identical embedded tasks and paired seeds within domain. Recorded agent cost agrees with the sum of assistant-message costs to floating-point tolerance (<5 × 10⁻¹⁶). Airline and retail all terminate with `user_stop`. Telecom has 1, 3, 32, and 0 `max_steps` terminations for Claude 3.7, GPT-4.1, GPT-4.1-mini, and o4-mini, respectively. These are outcomes, not exclusions.

**Material version limitation.** The current repository is branded τ³-bench and documents substantial task corrections after these runs. It is incorrect to label the downloaded historical case study a current leaderboard comparison. [Official task-fix account](https://taubench.com/blog/tau3-task-fixes.html) and [SABER](https://arxiv.org/abs/2512.07850) explain annotation and task-definition problems. New task instructions cannot generally be repaired by relabeling old trajectories alone: some changes would alter agent behavior. Analyze telecom separately, retain original labels, add label-contamination sensitivity, and describe version dependence prominently.

## Source 2: SWE-agent on SWE-bench Lite

Official metadata: [SWE-bench experiments](https://github.com/SWE-bench/experiments), snapshot `40f164d5b8f1d249bf95a6df8b74b577fd8e519d`. Primary run metadata/results were downloaded for [SWE-agent + GPT-4](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/lite/20240402_sweagent_gpt4) and [SWE-agent + Claude 3 Opus](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/lite/20240402_sweagent_claude3opus). System reference: [SWE-agent](https://arxiv.org/abs/2405.15793); benchmark reference: [SWE-bench](https://arxiv.org/abs/2310.06770).

Official metadata points to public S3 trajectories. Complete object listings verified exactly 300 `.traj` files for each run:

- `https://swe-bench-submissions.s3.amazonaws.com/lite/20240402_sweagent_gpt4/trajs/<instance_id>.traj`
- `https://swe-bench-submissions.s3.amazonaws.com/lite/20240402_sweagent_claude3opus/trajs/<instance_id>.traj`

Downloads are under `work/empirical_sources/swe_lite/<run>/`; hashes and original URLs are recorded in `work/empirical_sources/swe_lite_manifest.json` once retrieval completes. Success comes from each official `results/results.json` `resolved` membership. Every trajectory includes an `info` object and an ordered `trajectory` list. `info.model_stats.instance_cost` is the per-instance historical cost; **`total_cost` is cumulative across instances and must never be used as the task outcome**. `api_calls`, `tokens_sent`, `tokens_received`, and trajectory length support workload summaries. There is no verified per-instance latency field in the inspected schema.

These are 2024 runs of different language models under one agent family, with a single available attempt per task and budget-based terminations. A task-paired analysis is feasible; task identity does not create random treatment allocation. The 300 tasks come from multiple repositories: report repository dependence and a leave-one-repository-out sensitivity rather than treating repeated steps as independent samples. Repository licensing for the code does not automatically settle every embedded patch or transcript right. An explicit artifact-level license was not verified in the experiments tree. The portable research release should distribute numerical derivatives and source-fetch manifests, retain attribution, and avoid bundling raw third-party patches/transcripts until rights are resolved.

## Other sources inspected

[AgentBoard](https://github.com/hkust-nlp/AgentBoard) explicitly supplies baseline task-level logs in a downloadable archive, including success, progress, grounding, and trajectories across nine environments. Its [dataset card](https://huggingface.co/datasets/hkust-nlp/agentboard) states GPL-2.0 for the dataset; the repository states Apache-2.0 for code. This is a promising tertiary source, but the full archive and actual baseline record coverage were not downloaded/audited here. Do not equate the Hugging Face task table with agent-run logs.

The current τ-bench leaderboard supports raw trajectories, but its [submission guide](https://github.com/sierra-research/tau2-bench/blob/main/docs/leaderboard-submission.md) explains that new trajectory files are hosted separately from the metadata repository. Aggregate leaderboard records alone cannot support paired multimetric analysis. Latest-generation agent comparisons would require retrieving those actual run files and independently verifying benchmark version and user-simulator consistency.

## Reviewer-facing empirical boundaries

1. A success-first comparison defines a preference over a **pair of outcomes**; a positive mean win score can coexist with a worse marginal success rate. Show a population-level counterexample and require an independent success/safety noninferiority gate for deployment.
2. Same-task benchmark wins and cross-user A/B wins are different estimands. Ordinary single-exposure randomization does not identify the probability that the same user would prefer one potential outcome over the other.
3. More pairwise comparisons do not create more independent data. With four trials per task, uncertainty must retain task clusters; 16 within-task cross-comparisons are not 16 independent observations.
4. Priority order and practical-equivalence thresholds are normative inputs. Freeze a primary order before inspecting comparative wins and report a sensitivity grid; do not optimize a hierarchy for the desired winner.
5. Historical dollar costs reflect historical pricing/configuration. They should not be represented as current prices or as an intrinsic property of model quality.
6. Real-agent offline replay can demonstrate interpretability and decision instability. Finite-pool resampling does not prove performance on new live traffic, adaptive tools, changing users, or a new model release.
