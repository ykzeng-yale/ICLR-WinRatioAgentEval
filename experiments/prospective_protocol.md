# Frozen prospective telecom laboratory pilot

The machine-readable protocol in `prospective_protocol.json` was saved before any paid evaluation request. The data are collected prospectively from commercial models, but this is a laboratory shadow-execution experiment with a language-model user simulator. There are no live production users and no production A/B randomization.

## Sampling and execution

The pinned τ-bench source commit is `b7ea9074c1cba482b30687fecdb5c8425fd6f619`. Eligibility was evaluated before outcomes: use the telecom base split, require deterministic environment/action criteria, and exclude any task with natural-language assertions or an NL reward component. All 114 base tasks met these conditions. Rank eligible IDs by SHA256(`20260918|task_id`) and select the first 12. Exact IDs and full embedded task definitions appear in the frozen JSON.

Each task receives one GPT-5.6-Luna execution and one Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) execution. A fixed Python random seed randomizes system order within every selected task. The user simulator is GPT-5.6-Luna for both systems. System-specific harness seeds are fixed in the plan. The direct provider requests do not send provider random seeds, so the harness seeds do not promise deterministic commercial-model generations.

Each run has a 40-step cap, a four-error cap, and no task, provider, or malformed-output retry. Agent completions are capped at 384 tokens and user-simulator completions at 192. Luna runs with reasoning effort `none`; Haiku runs at temperature zero. The language-model identity and these provider-specific inference settings jointly define each evaluated system. The same tools, policy, task state, user model and terminal verifier apply across systems.

## Endpoints

The primary descriptive preference compares recorded deterministic task success first. If both systems fail, the pair ties. For two successes, historical/current-run recorded agent cost decides when its difference exceeds 5% of the larger cost; any strict assistant tool-call difference breaks remaining ties. Simulator expenditure is recorded separately and included in total experimental spending. Capped runs are completed experimental outcomes with the upstream terminal verifier; infrastructure and budget interruptions are not converted into task failures.

The task-paired realized preference, wins/losses/ties, marginal success counts, agent cost and tool-call summaries are descriptive. With one run per system/task, this pilot cannot estimate task-specific run variability. The 12-task size is a feasibility pilot and provides no deployment recommendation or proof of real-user effectiveness. No decision is based on an unvalidated noninferiority margin.

## Strict spending controls

The delegated maximum is **US$4.00** across agent and user-simulator requests; the coordinating author separately reserved another US$1.00 outside this adapter. The only allowed model prices are the verified list prices fixed before execution: Luna US$0.20 per million input and US$1.20 per million output tokens; Haiku US$1.00 per million input and US$5.00 per million output tokens.

Before every HTTP request, the adapter reserves the input upper bound plus the requested maximum output cost. The input upper bound is the UTF-8 byte length of the complete serialized provider payload plus 8,192 tokens and 512 tokens per tool for provider framing overhead. This deliberately overestimates ordinary text tokenization and tool wrappers. A request cannot begin if the remaining unreserved budget is insufficient. Calls are serialized; ledger mutation is lock-protected and persisted atomically before transport. Successful response usage reconciles the reservation. Prompt-cache discounts are ignored, making usage-priced amounts conservative list-price accounting rather than an assertion of final invoiced charges.

Transport uses one direct HTTP POST, zero retries, no redirects, no SDK fallback, and a fixed provider/model whitelist. Uncertain or unsuccessful responses retain their reservation. An unexpected model, unsupported output cap, usage above the reserved bound, infrastructure exception, or insufficient budget halts further requests. Planned but unrun rows remain in the output. An interrupted pilot reports the partial prespecified sample transparently and does not replace tasks based on observed outcomes.

The cap and uncertain-reservation behavior were checked without network calls. A second smoke check instantiated the actual pinned telecom environment and reached the replaced completion function with transport disabled. Safe hashed filenames and fail-closed exception handling were added after the plan was frozen but before any paid request; neither changed selected tasks, model order, endpoints, token limits or budget. The final executed adapter hash and plan hash are recorded separately.

## Artifacts and privacy

Credentials are read only from a CLI-supplied private JSON path and never appear in protocol, headers in logs, public traces or results. The public ledger records model, task index, conservative token bound, reservation, response usage, cost and request hash. Public trace summaries retain tool names, timing, usage, termination and verifier breakdowns; raw model text is hashed. The original native run JSON is saved in a private CLI-supplied directory for authorized audit, with restricted filesystem permissions. Regenerating outputs requires the exact source snapshot, frozen protocol, the adapter, compatible runtime and valid provider credentials; exact generations may change.

The source runtime is Python 3.13 with core τ dependencies plus `websockets` and `audioop-lts` required by current text-path imports. Source, environment and adapter versions are recorded in the run manifest. No package source code, model policy or deterministic scoring rule was modified.
