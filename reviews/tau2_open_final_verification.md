# tau2 open-model stream: independent verification of `results/tau2_open/report_final.md`

Date: 2026-09-19. Verifier: independent session (did not write the report). No git command, no model or API call,
no edit to any raw or frozen file. Recomputation code: `reviews/tau2_open_final_verify.py` (own code; reads only
`raw/tau2_open_arm{A,B}.json`, `design.json`, and, for comparison, `episodes.csv`, `summary.json`,
`monitor_pass1.csv`; imports only `src/winstats.py`; does not import `build_episodes.py` or `analysis.py`).

Reproducer: `.venv/bin/python reviews/tau2_open_final_verify.py` (prints 23 `CHK ... OK` lines, 0 `FAIL`).

**Verdict: PASS with two corrections applied and one provenance item for the owner.** Every headline number,
count, interval and decision in the report reproduces from the raw JSONs. No forbidden claim is present.

## Item-by-item

| # | item | result | evidence |
|---|---|---|---|
| 1 | 98 units per arm, 49 tasks x 2 trials, each (task, trial) exactly once | PASS | both arms: key set equals {1..49} x {0,1}, max multiplicity 1 |
| 2 | successes (reward >= 1) | PASS | A 15 (trial 0: 6, trial 1: 9), B 15 (8, 7); tasks both/one/never A 2/11/36, B 3/9/37; 20 tasks solved by either arm; unit table both 5, A only 10, B only 10, neither 73 |
| 3 | termination reasons | PASS | A user_stop 55, max_steps 27, too_many_errors 14, infrastructure_error 2; B user_stop 69, max_steps 29; no timeout |
| 4 | infrastructure units and their treatment | PASS | A task 6 trial 0 and A task 32 trial 1: no messages, reward_info null, duration 0.0; retained as failures with 0 tokens / 0 calls; neither is a pass-1 unit, so neither enters the 49 E1 pairs; `episodes.csv` agrees with my per-unit recomputation on success, completion tokens, prompt tokens, tool calls and duration for all 196 rows (0 mismatches) |
| 5 | truncated responses | PASS | 4 agent responses with finish_reason = length, all arm A, all exactly 1,024 tokens: tasks 22/0, 24/0, 24/1, 31/1 (31/1 succeeded); 0 for B and for the user simulator; max completion B agent 935, user 460 (A) / 169 (B); `tau2_armA.log` has 9 token-limit warnings (4 retained + 5 discarded: 4 on task 6, 1 before the task-15 overflow), `tau2_armB.log` 0 |
| 6 | tokens, calls, time per arm | PASS | agent completion 248,996 / 223,345; agent prompt 20,412,368 / 19,138,768; user completion 85,101 / 82,565; user prompt 4,373,819 / 5,915,658; agent LLM calls 2,485 / 2,263; user calls 1,720 / 1,812; duration sums 15,851.16 / 12,096.15 s; max 899.07 / 492.15 s; generation sums 11,972 / 8,258 s; served model ids as reported; seeds 626729 x 49 and 373753 x 49 in both arms |
| 7 | 49 prespecified pairs from `design.json` | PASS | pairs 1-49 each with one pass-1 A unit and one pass-1 B unit; only pair 25 straddles blocks; pass-1 success A 9/49, B 10/49 |
| 8 | hierarchical pair scores, W/T/L, NB | PASS | all pairs 10/30/9, NB 0.0204081633; block 1 (pairs 1-24) 5/16/3, NB 0.0833333333; all 19 decided pairs decided at the success tier; success-difference score equals z in every pair; all equal `summary.json` within 1e-9 |
| 9 | three e-process paths (`winstats.betting_log_e_ternary`; win thr 0, guardrail thr -0.03 on the success difference, harm mirrored) | PASS | max abs difference from `monitor_pass1.csv` over 49 rows x 3 paths = 0.0; finals -0.140724, -0.074950, -0.212449 (block 1: 0.001593, 0.065088, -0.213446); maxima win 0.738 (pair 11), guardrail 0.905 (pair 12), harm 0.000 (pair 1); from pair 20: 0.130, 0.225, -0.132; threshold 2.9957; no crossing |
| 10 | R1 normal-mixture CS | PASS | radius 0.629732 (n = 49) -> [-0.6093, 0.6501]; 1.155914 (n = 24) -> unclipped [-1.0726, 1.2392]; radius <= 0.03 first at n = 12,094 |
| 11 | corrected betting CS | PASS (values) | current `src/wincs.py` gives [-0.36603528, 0.40631790], block 1 [-0.64513449, 0.81152998], WR lower 0.0070957: identical to `summary.json`. See item 19 for the hash |
| 12 | same-task shadow NB, task clusters (t, 48 df) | PASS | all: 0.0051020408, se 0.0576289758, [-0.1107687809, 0.1209728625]; offdiagonal 0.0 [-0.1135390, 0.1135390]; diagonal 0.0102041 [-0.1123963, 0.1328045]; equal to `summary.json` within 1e-9 |
| 13 | component contrasts | PASS | same-task: success 0.000 [-0.1135, 0.1135]; completion tokens -261.74 [-881.95, 358.46]; prompt -12,995.9 [-69,131.6, 43,139.8]; tool calls -4.684 [-6.869, -2.499]; LLM calls -2.265 [-7.953, 3.422]; duration -38.32 [-77.10, 0.46]; generation time -44.10 [-75.30, -12.91]. Pair-level (49 / 24 pairs): tokens -906.3 [-1658.4, -154.3] / -1231.2 [-2017.4, -444.9]; prompt -68,683 [-140,697, 3,331] / -123,743 [-219,150, -28,337]; calls -5.92 [-8.98, -2.86] / -6.46 [-10.73, -2.18]; duration -78.9 [-129.6, -28.1] / -96.8 [-150.9, -42.7]; generation -62.7 [-97.1, -28.4] / -75.2 [-110.5, -39.9] |
| 14 | infrastructure-exclusion sensitivity | PASS | NB 0.0051 [-0.1108, 0.1210]; success 0.000 [-0.1135, 0.1135]; tokens -386.8 [-1081.6, 308.0] (A mean of task means 2,665.9); prompt -20,755 [-79,117, 37,606]; calls -4.745 [-6.915, -2.575]; duration -47.94 [-94.79, -1.08] (A 171.4) |
| 15 | decision rules and sensitivity tables | PASS | all 14 rows of `decision_rules.csv` and all 20 rows of `sensitivity.csv` match the report's tables |
| 16 | medians and means in section 3.3 | **FIXED** | the report called `mean_A`/`mean_B` "per-episode means" and gave "Medians" without saying they are medians of the 49 per-task means. Per-episode medians are lower (tokens 1,912 / 1,362.5; calls 7 / 5; duration 120.0 / 66.5 s, which is what section 7.3 prints; generation 95.0 / 51.1 s), and arm A's per-episode mean generation time is 124.7 s over 96 units, not 128.4 s (mean of task means). Sentence rewritten to say exactly this; no number in a table changed |
| 17 | forbidden wording (addendum) | PASS | `grep -n -i "inferior\|equivalent\|approved\|latency\|saving\|randomized" report_final.md`: "non-inferior", "equivalent", "approved" absent; "randomized" occurs only negated (lines 15, 247, 298) or in the issue title (290); "latency" / "savings" only as "no ... claim" (15, 243, 320). Batch-collection wording, R1/R2, block-1 pairs 1-24, task = cluster, shared seeds, token scope and the corrected-CS deviation all match addendum (a)-(e). Section 8 says explicitly that the result is not evidence that B performs as well as A |
| 18 | Deviation 1 | PASS | `run_manifest.json` has two invocations: 48c09d0c... (started 17:38:26Z; no status / finished_at; no `config_amendment` key; runner sha 215e943a...) and 0bf28fc9... (20:33:06Z to 04:56:43Z, completed, elapsed 30,216 s; `config_amendment` embedded with id 1; runner sha 27797f68... = on disk; all other harness hashes identical). Amendment sha256 696aede4... and note sha256 1160458f... match the files. Five pre-amendment units = arm A tasks 1-5 trial 0 (ended 13:39-13:51 local; rewards 0, 0, 1, 1, 0; durations 46.9-432.3 s; max per-message completion 514 agent / 205 user); the sixth arm-A record ends 16:37:59 local. Log lines 710 and 897 are the two task-6 timeouts; four post-amendment task-6 attempts fail with the identical JSON error; task 32: 32,836 tokens x 4; task 15 first attempt 33,050 tokens. `max_tokens`/`--timeout 1800` are in both recorded tau2 commands; arm-A `info.llm_args` lacks `max_tokens`, arm B has it; `n_infrastructure_error_rerun_on_resume` 0 and `info_mismatches` [] in both arm runs; arm wall-clock 18,082 / 12,127 s. The `decided_utc` 20:45Z versus 20:33:06Z start inconsistency is real (file mtimes 16:32:43 local) and is disclosed |
| 19 | hashes in section 9 | PASS except one | raw A/B (and per-invocation copies), `episodes.csv`, `summary.json`, `design.json`, `config.json`, `analysis.py`, `run_tau2_open.py`, amendment: all match disk. **`src/wincs.py` does not**: on disk 601865d9adf0a9f1a0f20c44ef78cb18dffe33fdc3beb5d98a47d6c5199b8754, mtime 01:15:34 local, i.e. 46 s after the report (01:14:48) and 14 min after `summary.json` (01:01:30); `src/test_wincs.py` changed at 01:15:55. The reported 6a6a0b51... is the addendum-registered hash; the wincs hash is recorded neither in the manifest nor in `summary.json`. A verifier note stating this was added under the hash table (**FIXED as disclosure; root cause is for the owner**) |
| 20 | figures | PASS | f1, f2, f3 PNG opened and legible (titles, axes, legends, printed counts; f1 labelled descriptive / no live stopping; f3 shows 55/27/14/2 and 69/29, "4 + 5"); PDFs present |

## Edits made to `report_final.md` (mechanical, unambiguous)

1. Section 3.3, the sentence after the component table: means/medians described correctly (item 16).
2. Section 9, after the hash table: verifier note on the `src/wincs.py` hash (item 19).

A copy of the file before these edits is not kept in the repository; the two edits are the only changes.

## Open problems (not fixable mechanically)

- `src/wincs.py` was changed by another session after the tau2 analysis ran. The numbers are unaffected (the on-disk
  version reproduces them exactly), but the report's statement that the analysis used sha256 6a6a0b51... cannot be
  confirmed from saved artifacts. Suggested: record the wincs hash in a small post hoc provenance file, or re-run
  `analysis.py` (deterministic, no model) and confirm `summary.json` is byte-identical apart from `generated_at`.
- `run_tau2_open.py`, listed as frozen, was edited post-freeze to apply the amendment (disclosed in section 6; hashes
  in the manifest).
- Section 1 quotes "84 s versus 128 s" for generation time; 128 s is the mean of task means (per-episode 124.7 s over
  96 units). Now explained in 3.3; left unchanged in section 1 because it is the `summary.json` value.
- H5: quoting archived commercial rates "for context only" is in tension with protocol H5 ("never compared");
  disclosed in section 11 item 7; owner's call.
- Absolute local paths in manifest/config/README need sanitizing before an anonymous release (disclosed).
- Seed forwarding is unverifiable at request level (disclosed; consistent with what I found: no "seed" in either
  llama-server log, no request bodies saved).
