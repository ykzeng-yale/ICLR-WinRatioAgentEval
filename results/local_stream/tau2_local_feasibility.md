# Feasibility note: tau2-bench with a local open-weight model (not executed at scale)

Date: 2026-09-18. Purpose: check whether the queued "larger prospective stream" (issue #1) could be run on tau2-bench itself with a zero-cost local model.

Setup: tau2-bench cloned at commit b7ea9074c1cba482b30687fecdb5c8425fd6f619 (uv sync; the optional `websockets` package had to be added for the import to succeed); local OpenAI-compatible server `mlx_lm.server` (mlx-lm 0.31.3) serving mlx-community/Qwen2.5-Coder-7B-Instruct-4bit on an Apple M5 (32 GB); agent and user simulator both pointed at the local server via `OPENAI_API_BASE`; one airline task, one trial, max 40 steps, temperature 0.

Outcome: the pipeline runs end to end (reward computed, litellm cost = $0 for the unregistered local model), but the simulation terminated at max_steps with reward 0 and **zero assistant tool calls in 41 messages**: the local serving stack does not return OpenAI-style structured tool calls, so the agent never queries the environment. Wall-clock 57 s for the 41-message episode with two local model roles. Stop-token artifacts (`<|im_end|>`) also leaked into simulated-user text.

Conclusion: a tau2-bench stream with this local stack would measure a non-functional agent (no tool use) and is therefore not run. The prospective local stream uses verifiable code-generation benchmarks (MBPP-sanitized, HumanEval) with an explicit sandboxed-execution tool instead (experiments/local_stream/). A tool-call-capable local serving stack (e.g. vLLM with a tool parser on Linux) or a paid model would be required for tau2-bench; no paid allocation exists.
