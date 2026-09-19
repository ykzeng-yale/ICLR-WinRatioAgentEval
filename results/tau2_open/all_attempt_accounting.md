# tau2 open-model stream: all-attempt accounting (Round 10 owner handoff)

Written 2026-09-19, POST HOC, in answer to the root session's Round 10 audit, section 5, requirement 2. It is **operational accounting, failure-inclusive, and separate from the canonical analysis**: nothing here changes `episodes.csv`, `summary.json`, the 196-unit denominator or any result of `report_final.md`. No model, API or git command was used; no raw, log or frozen file was edited.

Generator: `experiments/tau2_open/make_round10_handoff.py` (reads the three tau2 logs, the two llama-server logs, the two raw tau2 JSONs, `run_manifest.json`, `design.json`, `episodes.csv`). Machine-readable outputs: `all_attempt_accounting.csv` (206 rows, one per tau2-level attempt), `unit_policy_flags.csv` (196 rows, one per canonical unit), `round10_handoff_numbers.json` (every number quoted here; key `reconciliation` and `operational_accounting_failure_inclusive`). Times are UTC; tau2 and its logger print naive local time (UTC-4), converted by adding 4 h (checked: in each of the three log segments the first tau2 line is within 1 s of the segment's UTC marker after the conversion, and the first logged model response follows 4.5-4.8 s after the marker).

Sources and their limits. The tau2 retry lines name the task but not the trial; with `--max-concurrency 1` the log is strictly sequential, so the trial is the one of the preceding `Running task <id>, trial <k>` line. `logs/tau2_armA.invocation1_preamendment.log` is a byte-for-byte prefix of `logs/tau2_armA.log` (checked), so invocation 1 is counted once. Invocation 1 has no per-invocation raw copy (the harness writes that copy when an arm subprocess returns, and invocation 1 was stopped); its five completed units survive in tau2's results file, which invocation 2 resumed, and its interrupted state is documented by the pre-amendment log snapshot and by the first server session in `logs/llama_server_8081.log` (lines 1-4727).

## 1. The rule that selects the canonical outcome (tau2-bench at commit `b7ea907`, read, not executed)

1. **One work unit = one (task, trial, trial seed).** `runner/batch.py:743` draws the two trial seeds from `--seed 300`; `batch.py:818` skips every unit whose key `(trial, task_id, seed)` is already in the resumed results ("Skipping task ..., because it has already been run").
2. **Retry on any exception, up to 4 attempts.** `runner/progress.py:19-133` (`run_with_retry`): `max_attempts = max_retries + 1` (line 52) with tau2's default `--max-retries 3` (the recorded commands do not override it). Each attempt calls the whole simulation again from the start, with the same seed (line 75). The **first attempt that returns without an exception is returned** (line 90) and no further attempt is made. A failed attempt raises out of the orchestrator ("Simulation loop exited with an exception - running emergency cleanup"); its partial trajectory is **not written anywhere**: a failed attempt leaves no simulation record. Only the log lines `Task <id> failed (attempt k/4): <message>` (line 97) and `Task <id> failed after 4 attempts` (line 101) remain.
3. **After the last allowed attempt** tau2 builds a placeholder record with `termination_reason = infrastructure_error`, `messages = []`, `duration = 0.0`, `reward_info = null` and `info = {error, error_type, error_traceback, failed_after_attempts: 4}` (lines 112-133).
4. **Exactly one record per unit is saved**, after `run_with_retry` returns: `batch.py:670` calls the checkpoint saver once with the returned record; `runner/checkpoint.py:351-377` appends it to `results.json` and refuses a second record with the same key ("Skipping duplicate save"). So the canonical record of a unit is **the record of its last attempt: the first attempt that completed, or the placeholder if all four failed**. Outcomes play no part in the rule; a completed attempt is never re-run, whatever its reward.
5. **Resume.** With `--auto-resume`, `checkpoint.py:34-224` (`try_resume`) loads the existing results, treats every record whose termination reason is not `infrastructure_error` as done (lines 169-175), **deletes the `infrastructure_error` records from the checkpoint so that those units are run again** (lines 164-168, 178-182), continues despite a changed run configuration after logging the difference (line 110), and returns the **previous** results object, so the file keeps the first invocation's `info` block (line 224).
6. **What happened here.** Invocation 2 resumed arm A from 5 records, none of them an infrastructure record (`n_infrastructure_error_rerun_on_resume = 0` for both arms in the manifest; "Resuming run from 5 runs. 93 runs remaining."). The two `infrastructure_error` records were both created during invocation 2 (task 6 trial 0 at 20:37:59Z, task 32 trial 1 at 00:44:39Z). **No tau2 process was started after invocation 2 finished, so neither was dropped or re-run**; they are the canonical records. A later `tau2 run --auto-resume` on that results file would delete and re-run both; the harness refuses to do so because it skips an arm whose raw copy already holds all 98 units (`run_tau2_open.py`, "raw copy already complete").

## 2. Reconciliation of the planned 196 units

| quantity | value |
|---|---|
| planned units (49 tasks x 2 trials x 2 arms) | **196** |
| unique canonical units in the raw JSONs (each key once; key set equals the plan) | **196** (98 + 98) |
| missing outcomes / duplicate units | **0 / 0** |
| tau2-level attempts started, all invocations | **206** (arm A 108, arm B 98; invocation 1: 8, invocation 2: 198) |
| attempts that produced the saved trajectory record | 194 |
| attempts discarded (no simulation record) | **12**, all arm A: 11 with a tau2 failure line + 1 interrupted when the owner stopped invocation 1 |
| extra attempts beyond one per unit | 10 = **9 tau2 within-invocation retries + 1 re-run on resume** of a unit that had no record (task 6 trial 0) |
| retries by the failure that triggered them | request timeout 2 (invocation 1; the second of these retries is the interrupted attempt); JSON decode error after truncation 3; context-window overflow 4 (task 15: 1, task 32: 3) |
| discarded attempts by cause | `litellm.Timeout: APITimeoutError` 2; interrupted by the owner's stop 1 (it had itself accumulated 2 request timeouts); `JSONDecodeError` "Unterminated string starting at: line 1 column 185 (char 184)" after a response cut at 1,024 tokens 4; `litellm.BadRequestError` context overflow 5 (33,050 > 32,768 once; 32,836 > 32,768 four times) |
| units with more than one attempt | 3, all arm A: task 6 trial 0 (7 attempts), task 15 trial 0 (2), task 32 trial 1 (4); the other 193 units have exactly one attempt |
| tau2 `timeout` terminations (1,800 s per simulation, invocation 2 only) | **0**; longest canonical simulation 899.1 s (A), 492.2 s (B); longest attempt of invocation 2 including discarded ones about 944 s (task 15 trial 0, attempt 1) |
| request-level timeouts (client disconnects seen by llama-server after 600 s of generation) | **16**, all invocation 1, all task 6 trial 0 (7 + 7 + 2), plus 1 request aborted after 10 s when the process was stopped; 0 in invocation 2; 0 on port 8082 |
| requests rejected by llama-server for context overflow | 20 = 5 failed attempts x 4 requests (tau2 passes `num_retries = 3` to litellm, `utils/llm_utils.py:379-380`) |
| truncated responses (`finish_reason = length`, exactly 1,024 completion tokens) in canonical records | **4**, all arm-A agent: task 22 trial 0, task 24 trials 0 and 1, task 31 trial 1 (the last still succeeded) |
| truncation warnings in discarded attempts (log only) | **5**: task 6 trial 0, invocation 2, attempts 1-4 (one each); task 15 trial 0, attempt 1 (one, before the overflow) |
| truncation warnings in all logs | 9 = 4 + 5 (arm A); arm B 0. In the canonical records the user simulator has 0 truncated responses in either arm. The log warning does not name the role: for task 6 the cut response was the agent's tool call (the parse error is in its arguments); for the discarded attempt of task 15 the role cannot be determined from the saved artifacts. Per unit, the number of warnings in the record-producing attempt equals the number of `finish_reason = length` responses in the raw record (196 of 196 units) |
| `infrastructure_error` records | **2**, arm A: task 6 trial 0 (`JSONDecodeError`), task 32 trial 1 (`BadRequestError`); both with `failed_after_attempts = 4`, no messages, reward missing |
| units with a missing reward | 2 (the same two); scored as failures and retained (`report_final.md` 7.2) |
| infrastructure records dropped and re-run | 0 |

## 3. Every unit with more than one attempt

All 98 arm-B units and 95 arm-A units: one attempt, which produced the record (rows in `all_attempt_accounting.csv`). The three exceptions:

**Arm A, task 6, trial 0 (seed 626729): 7 attempts, canonical record `infrastructure_error`, reward missing.**

| # | invocation / settings | attempt | window (UTC, approximate) | outcome of the attempt | truncation warnings | server-side evidence |
|---|---|---|---|---|---|---|
| 1 | 1 / no `max_tokens`, no `--timeout` | 1 of 4 | 17:51:05 - 19:01:32 (4,227 s) | failed: `litellm.Timeout: APITimeoutError - Request timed out.` | 0 | 7 requests cancelled after 600 s each; up to 12,817 tokens generated in one request when cancelled |
| 2 | 1 | 2 of 4 | 19:01:32 - 20:12:01 (4,229 s) | failed: same message | 0 | 7 requests cancelled after 600 s each |
| 3 | 1 | 3 of 4 | 20:12:01 - 20:32:38 (1,237 s) | **interrupted**: the owner stopped invocation 1; tau2 printed no failure line | 0 | 2 requests cancelled after 600 s, 1 aborted after 10 s at the stop |
| 4 | 2 / `max_tokens = 1024`, `--timeout 1800` | 1 of 4 | 20:33:13 - 20:34:29 (76 s) | failed: `Unterminated string starting at: line 1 column 185 (char 184)` | 1 | none |
| 5 | 2 | 2 of 4 | 20:34:29 - 20:35:40 (71 s) | failed: identical message | 1 | none |
| 6 | 2 | 3 of 4 | 20:35:40 - 20:36:49 (69 s) | failed: identical message | 1 | none |
| 7 | 2 | 4 of 4 | 20:36:49 - 20:37:59 (70 s) | failed: identical message; attempts exhausted, tau2 wrote the placeholder | 1 | none |

**Arm A, task 15, trial 0 (seed 626729): 2 attempts, canonical record `user_stop`, reward 0.** Attempt 1 (invocation 2, 20:56:12 - 21:11:55, 944 s): one truncation warning, then `litellm.BadRequestError: OpenAIException - request (33050 tokens) exceeds the available context size (32768 tokens)`; 4 requests rejected by the server. Attempt 2 (21:11:55 - 21:15:40) completed and **is the recorded episode** ("Task 15 succeeded on retry 1" means the retry completed without an exception, not that the task was solved).

**Arm A, task 32, trial 1 (seed 373753): 4 attempts, canonical record `infrastructure_error`, reward missing.** Attempts 1-4 (invocation 2; ending 00:22:28, 00:29:54, 00:37:15, 00:44:39; 381, 445, 442 and 444 s): each failed with `request (32836 tokens) exceeds the available context size (32768 tokens)`, each with 4 rejected requests, no truncation warning.

**Did a retry ever turn a failure into a success?** No. The rule is blind to rewards, but exceptions are not independent of how a trajectory is going (runaway generation and context overflow are failure modes), so the question matters. The only unit whose canonical record comes from a retry, task 15 trial 0, is a failure (reward 0); the other two multi-attempt units are `infrastructure_error` failures. All 30 canonical successes (15 per arm) come from first and only attempts. A canonical record obtained after a retry does not erase the earlier attempts: they stay listed here and in the CSV.

## 4. Failure-inclusive operational accounting (not used by any analysis)

| | invocation 1 (pre-amendment) | invocation 2 (amendment 1) |
|---|---|---|
| tau2 attempts started / discarded | 8 / 3 | 198 / 9 |
| wall-clock | 10,452 s (2.90 h), invocation start to the last server event | arm A 18,082 s, arm B 12,127 s (manifest) |
| of which retained simulations | 740 s (5 units) | A 15,111 s, B 12,096 s |
| of which discarded attempts (approximate log windows) | 9,693 s | 2,941 s (A), 0 (B) |
| generated tokens in completed requests, port 8081 (llama-server log) | 16,444 | 448,226 |
| of which retained in canonical records | 15,014 | 401,648 (arm-A agent and user after the amendment, plus the arm-B user simulator) |
| of which smoke check | 2 | 2 |
| of which in discarded attempts | 1,428 | **46,576** |
| generated tokens in cancelled requests (lower bound, last progress line) | **198,280** in 17 requests | 0 |
| port 8082 (arm-B agent): completed requests / generated tokens | not started | 2,264 / 223,347 = 2,263 retained responses with 223,345 tokens + the 2-token smoke check (exact match; nothing discarded) |

Arm A's cost of obtaining its 98 canonical records therefore includes about 3.5 h of discarded wall-clock (2.69 h in invocation 1, 0.82 h in invocation 2) and at least 246,000 generated tokens that appear in no record, against 248,996 agent completion tokens in the records. Arm B had no discarded work. None of this enters the token tier, the component table or any interval of `report_final.md`, which use the canonical records only; it is reported here so that the canonical resource comparison is not read as the full operational cost of arm A.

## 5. What this adds to, or corrects in, `report_final.md`

1. `report_final.md` 6 and 7.2 count "2 pre-amendment timeouts" on task 6. The log has two failed attempts **and a third attempt that was running when invocation 1 was stopped** (it had been running for 20.6 min and had two request timeouts of its own). Total for the unit: 7 attempts, not 6. The third attempt has no tau2 failure line; the evidence is the `Retry 2/3` line, the status lines up to "1216s R2", and the server log.
2. Each tau2-level attempt contains request-level retries that tau2 does not log: 7 requests of 600 s per timed-out attempt (the mechanism that produces 7 is inside litellm / the OpenAI client and is not determined from the artifacts), and 4 requests per context-overflow attempt.
3. The amendment file and the deviation note say one request "produced 18,084 tokens". In the server log 18,084 is the slot's token count (prompt + generated) when that request was cancelled; the same request had generated about 12,019 tokens in 600 s (20 tokens/s). See `experiments/tau2_open/deviation_1_erratum.md`.
4. The longest simulation figures (899 s, 492 s) are for canonical records; the longest attempt under the amended settings was a discarded one (about 944 s). No attempt of invocation 2 came near 1,800 s.
