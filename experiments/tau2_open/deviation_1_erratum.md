# Erratum to Deviation 1 (`config_amendment_1.json`, `deviation_1_runaway_generation.md`)

Written 2026-09-19 by the experiment owner in answer to the root session's Round 10 audit (section 5, "Airline amendment and all-attempt boundary"). POST HOC. **Neither of the two files it corrects is edited**: `config_amendment_1.json` stays byte-identical because its sha256 `696aede45eb45360a1a7e3e78626ec5d86ef745af5f2a02c5d0248adc272ce8f` and its full content are embedded in the invocation-2 record of `results/tau2_open/run_manifest.json`, and `deviation_1_runaway_generation.md` (sha256 `1160458fca2ddfc50908edc89405ff757b3cf05f6fda8120753e8ac2e6116e88`) is kept as the record of what was written at the time. This erratum takes precedence over both wherever they differ. Facts quoted here are in `results/tau2_open/round10_handoff_numbers.json` (key `erratum_facts`), produced by `experiments/tau2_open/make_round10_handoff.py` from the saved artifacts. No model, API or git command was used.

## (a) `decided_utc` is wrong

`config_amendment_1.json` records `"decided_utc": "2026-09-18T20:45Z"` and the note says "Recorded 2026-09-18 about 20:45 UTC". That value was a **clock estimate typed by the owner, not a measured time, and it is wrong**: it is later than the start of the invocation that embeds the amendment. What the artifacts show:

| event | time (UTC) | source |
|---|---|---|
| invocation 1 starts | 2026-09-18T17:38:26Z | manifest |
| last tau2 failure line of invocation 1 (task 6, attempt 2 of 4) | 20:12:01Z | `logs/tau2_armA.invocation1_preamendment.log` line 897 |
| last llama-server event of invocation 1 (request aborted: the owner's stop) | 20:32:38Z | `logs/llama_server_8081.log` line 4725, server clock anchored to the invocation start (agreement with tau2 timestamps within 1.1 s) |
| modification time of `config_amendment_1.json`, of the deviation note, of the edited `run_tau2_open.py` and of the pre-amendment log snapshot (all four identical) | **20:32:43Z** | file system |
| invocation 2 starts; its manifest record embeds the amendment | **20:33:06Z** | manifest |
| first model response logged by tau2 under the amended settings | 20:33:13Z | `logs/tau2_armA.log` line 1026 |
| first arm-B episode starts | 2026-09-19T01:34:36Z | raw arm-B JSON |

So the decision and the amendment files **preceded invocation 2** (files in place at about 20:32:43Z, 23 s before it started) and preceded every arm-B episode by five hours. The correct reading of `decided_utc` is "shortly before 20:33Z". Two limits are stated plainly: a modification time is file-system metadata, not tamper-proof evidence; and the artifacts do not show when, during the 2.9 h of invocation 1, the owner formed the intention to amend. The content-level ordering does not depend on the clock: the manifest record of invocation 2 contains the amendment and the amended command line, and invocation 1's record contains neither.

## (b) Wording correction required by the root session

The amendment file ("so the amendment would not have changed these records"), the note ("so the cap and the limit would not have altered them"; "all but the five retained units (for which it is immaterial)") and both under the heading "outcome blindness" claim more than was verified. The corrected statement, which replaces those sentences:

> The five retained pre-amendment units (arm A, tasks 1-5, trial 0; rewards 0, 0, 1, 1, 0) **did not reach the later caps**: their largest single completion is 514 tokens (agent) and 205 tokens (user simulator) against the later 1,024-token cap, and their durations are 46.9 to 432.3 s against the later 1,800 s limit. This is an observation about the realized trajectories. **It is not a verified counterfactual invariance under the changed serving regime**: the five units were never re-run with `max_tokens = 1024` and `--timeout 1800` in the request and command line, and a request that carries a `max_tokens` field is a different request to the server even when the cap does not bind. They are retained because the protocol retains every enrolled episode and because tau2's resume keeps completed records, not because equality of the two regimes was shown.

> **The amendment was not blind to arm-A performance information.** When it was decided the owner had seen: the five arm-A outcomes (tau2's status line printed "Avg reward: 0.40 (N=5)" every 30 s), their durations, the token lengths of their responses, and one operational failure (the runaway generation and repeated request timeouts on task 6). It was blind to **all arm-B outcomes**, none of which existed, and to the outcomes of the other 93 arm-A units. It was motivated by the operational failure and chosen as a standard serving safeguard, symmetric in arms and roles; "outcome-blind" without this qualification is withdrawn.

Both policies stay in the provenance: `results/tau2_open/unit_policy_flags.csv` marks each of the 196 canonical units with its invocation, `pre_amendment` true/false and the settings in force (5 units pre-amendment, 191 under amendment 1). The planned denominator is unchanged; the omit-five sensitivity in `report_final.md` (Round 10 addendum) is labelled post hoc and replaces nothing.

## (c) Post-freeze edit of the runner

`run_tau2_open.py` is listed among the frozen harness files, and it **was edited after the freeze** so that it loads `config_amendment_1.json` and appends the extra request arguments and flags: sha256 `215e943a371a778900033586a28cd00b7e0f49f77966354ff3d2b6913c1c06ee` in invocation 1, `27797f68e2aff6e088d0300f4be9baac903ef34b71ec84116125c2fa664ff75c` in invocation 2 and on disk. Every other harness hash recorded by the manifest is identical in the two invocations (`common.py`, `design.py`, `build_episodes.py`, `analysis.py`, `tests_tau2_open.py`, `config.json`, `protocol.md`, `README.md`); the harness git hash moves from `35a8d5a1c8b9155a39ad211252b928c244553893` to `4f01206a7d579f0ea02b6445c852d60d0ca23009`. The invocation-1 version of the runner is identified by its hash only; this erratum does not claim that its bytes can be recovered from the working tree.

## (d) Two further corrections of fact found while compiling the all-attempt accounting

1. **"One request produced 18,084 tokens".** In `llama_server_8081.log`, 18,084 is the slot's token count (prompt plus generated) at the moment that request was cancelled (`stop processing: n_tokens = 18084`); the last progress line of the same request shows 12,019 generated tokens after 600 s (about 20 tokens/s). The sixteen requests that ran into the 600 s client timeout had generated between 11,625 and 12,817 tokens each when cancelled. "Runaway generation of about 12,000 tokens per request until the client timed out" is the accurate description.
2. **"Two failed attempts" on task 6.** Invocation 1 contains two attempts that tau2 logged as failed (19:01:32Z and 20:12:01Z) **and a third attempt that was running when the owner stopped the process** (from 20:12:01Z to 20:32:38Z; two more request timeouts, no tau2 failure line). Together with the four attempts of invocation 2 the unit has 7 attempts and no trajectory record; its canonical record is tau2's `infrastructure_error` placeholder. Details: `results/tau2_open/all_attempt_accounting.md`.

## (e) What does not change

The amendment content (`max_tokens = 1024` for both roles and both arms, `--timeout 1800`), the units it applies to, the 196-unit denominator, every outcome, and every number of the frozen analysis. The note's forecast that the cap would show up as `finish_reason = length` responses and failed units is what happened (4 canonical truncated responses, all arm A; task 6 failed under both regimes); no unit reached the 1,800 s limit.
