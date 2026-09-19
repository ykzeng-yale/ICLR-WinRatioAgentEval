# Airline collection provenance and retained analytical scope

The root-owned analytical pipeline is `experiments/build_open_airline_results.py`, invoked by `python reproduce.py --airline`. It reads the supplied metric projection, assignment array, policy flags, attempt ledger and server-counter summaries. No model request, benchmark program, dialogue playback or contributed inference module is executed. The optional `--project-source-dir` operation rebuilds the projection from the frozen source and rejects different uncompressed raw hashes.

## Observation and resource accounting

All 196 planned task–trial–arm units are retained. There are 194 saved trajectories and two infrastructure-failure placeholders; both placeholders have missing reward and count as unsuccessful units. The projection explicitly retains `reward_missing`, `reward_basis_present`, `has_saved_trajectory` and termination reason. Termination-based zero rewards are not represented as successful completion of every benchmark reward check.

The independently audited 206-row ledger accounts for 194 retained trajectory-producing attempts plus 12 discarded attempts. It does not turn empty placeholders into zero-cost execution or recover complete unrecorded trajectories. Canonical role-specific prompt/completion tokens come only from saved messages. Two independently parsed server-counter groups yield an omitted A-collection generated-token lower bound: 198,280 cancelled-request progress tokens + (16,444 − 2 smoke − 15,014 retained) + (448,226 − 2 smoke − 401,648 retained) = 246,284. Agent/user partition and complete failed-attempt usage remain unavailable. The counter summaries and arithmetic are retained; original server-log hashes are recorded in the source handoff/audit. No failure-inclusive efficiency advantage is claimed.

The projection omits dialogue, tool arguments, synthetic customer strings, benchmark task copies, tracebacks, identifying paths and simulation UUIDs. Canonical success comes from archived `reward_info.reward`, with missing reward mapped to unsuccessful; token and tool-call fields are rebuilt from raw messages. The attempt ledger is a declared field projection of the independently checked owner ledger. Original raw/CSV hashes and derived projection hashes are recorded separately. Reproduction verifies archived labels and arithmetic, not fresh generation or independent benchmark adjudication.

## Scientific scope

This is fresh local-model **batch collection, all A then all B**, with a prespecified replay schedule. Both trial seeds are reused across tasks and arms. The retained estimates are descriptive contrasts of that array. Neither independent task sampling, a constant history-conditional mean, equivalence, noninferiority, nor production performance is inferred from equal success counts or task-level clustering.

The post-hoc normal-mixture illustration conditions on the full array and matching and assumes independent fair replay orientation coins, with collection/amendment/retention independent of those coins. The filtration reveals past coins only. Its target is the running orientation-average of two explicitly computable scores per pair. The final target is already known from the full array; the band illustrates masking rather than uncertainty about an observed array. It is not selection-adjusted or a fresh-task/model-run confidence interval. No execution was stopped and no live stopping saving is claimed. Contributed task-t, independent-arm Welch, fixed-mean betting and win-ratio intervals are excluded, not silently relabeled.

## Amendment, source versions and reproducibility limits

Five A units preceded the cap amendment; all remain in the planned denominator. Their observed trajectories did not reach the later caps. That does not prove invariance to the changed policy. The amendment followed observed A outcomes and failure information, before B outcomes; it was not fully outcome-blind. The incorrect original estimated decision timestamp is retained alongside the explicit owner erratum. Manifest commands establish which settings were invoked, but owner filesystem timestamps do not independently establish exact prospective decision time.

The `.txt` snapshots are historical collection definitions, not executable entrypoints or instructions for the current analysis. The original amendment and owner erratum retain historical claims; this README and the paper govern retained scope. Both runner versions were recovered later from source history and exactly match invocation hashes: pre-amendment `215e943a371a778900033586a28cd00b7e0f49f77966354ff3d2b6913c1c06ee`, amended `27797f68e2aff6e088d0300f4be9baac903ef34b71ec84116125c2fa664ff75c`. This later recovery supersedes the erratum's statement that the original runner was identified only by hash. Neither version is executed by reproduction.

The pinned tau2 source forwards trial seeds in model arguments; no complete request bodies were saved, so actual sampler receipt and bit-identical replay are unverified. Recorded identities and response counts establish use of local Qwen systems, not independent random replications. Cap/timeout command settings, observed truncations and source-code request forwarding are distinct evidence layers.

## Source identities and terms

- Benchmark: τ²-bench, commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619`, https://github.com/sierra-research/tau2-bench. The paper cites the original benchmark; its upstream license notice is retained in `third_party/tau2_LICENSE.txt`. Benchmark dialogues/tasks are not redistributed in this projection.
- A agent and both user simulators: Qwen2.5-7B-Instruct, Q4_K_M files from https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF at `bb5d59e06d9551d752d08b292a50eb208b07ab1f`.
- B agent: Qwen3-4B-Instruct-2507, Q4_K_M file from https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF at `a06e946bb6b655725eafa393f4a9745d460374c9`.
- The model repositories/base models declare Apache-2.0. Weights and tokenizer data are not redistributed; filenames, sizes, hashes and model identities are retained in `collection_config.json`. Upstream licenses do not automatically license the research harness.
- Serving: llama.cpp `4fea119de30f6a923992780f6fd5ccb0bee5d47d`, https://github.com/ggml-org/llama.cpp. Hardware, Python and available dependency versions are recorded in `provenance.json`; missing versions are not invented.

The source manifest and scientific audit identify exactly what was preserved, transformed and independently checked. No human authorship verification, venue submission or production deployment is asserted by a successful rebuild.
