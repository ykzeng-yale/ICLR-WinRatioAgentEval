# ROOT_REVIEW_RESPONSE.md — verifier's disposition of the five root reviews of `5776877`

Verifier pass, 2026-09-20 06:15 UTC. Written by the verification group, which changed **no**
code, **no** document and **no** test: this file is the only thing it wrote. Every row below
was produced by running something. Nothing is marked CLOSED that was not run and watched to
close.

**What was verified, exactly.** Working tree of branch `session60/live-ab-validation` at
`HEAD = 035a93458f8371a81eb06eae67048ca1f1580f76`, with uncommitted repair work in the tree.
The tree was stable throughout this pass (every file under `experiments/live_ab/` and
`experiments/live_ab_validation/` has an mtime at or before 01:52 UTC; the pass ran from
02:05 to 06:15). Fingerprint of the two directories, so this report can be tied to bytes:

```
$ find experiments/live_ab experiments/live_ab_validation -type f \
    \( -name '*.py' -o -name '*.md' -o -name '*.json' \) ! -path '*__pycache__*' \
    -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256
3395aa1ffcce86b82e4cee0204f6e7705c4307efa5b151967d03d821501a4a4f  -
```

Interpreter: `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython
3.12.13, macOS arm64. CPU only. No model call, no API call, no model server, no download, no
new dependency, no process signalled, no state-changing git command. Witness scripts live in
this session's scratchpad (`w1_clip.py`, `w2_preflight.py`, `w3_seeds.py`,
`w4_unknown_usage.py`, `w5_language.sh`); their full outputs are quoted below.

**The five reviews are not on local `main`.** They were committed to `origin/main` at
`c15d1c7` (four files) and `69ff058` (the fifth). Local `main` is at `1c3e9f3`, four commits
behind, and none of the five files exists in the local working tree. They were read with
`git show origin/main:reviews/<file>`. Anyone re-running this pass must do the same or fetch
first.

**Reading the verdicts.** CLOSED = the root's own witness was re-run and the defect is gone.
PARTLY = the defect is gone from the artifact the root named but survives somewhere the same
finding reaches. OPEN = not repaired. NOT-A-DEFECT = the root recorded a positive check, not a
finding; re-verified and kept for completeness.

---

## Headline

The five reviews carry **31** findings between them. **20 CLOSED, 6 PARTLY, 3 OPEN, 1 still
open but correctly so** (PROV-2, the 29 null freeze facts: a pre-freeze prerequisite, not a
defect — nothing is frozen and no trial has run), **1 NOT-A-DEFECT** (STAT-2, a positive
check the root recorded, re-verified here for completeness). One further row, **PROV-6, is
not a root finding**: it is a regression this pass found and it is open.

All four executed witnesses the root supplied now close:

| Root witness | Root's result at `5776877` | Result now |
|---|---|---|
| clip `[.2, 1]` at 100 zero-score pairs | accepted; `L_h = L_s = .2`; `deploy_candidate` | **refused**, `FrozenMismatch` |
| bundle fixed, `delta` .03 → .04, runtime hashes from current bytes | `preflight` returned `[]` (ACCEPTED) | **refused**, `config_sha`, drift names `config_sha256` + `rule_block_sha256` |
| duplicate-seed probe with forced entropy | `[42, 42]` | **refused**; survives crash and stale-registry resume |
| one started request + worker-death reveal | both recounts reported `unknown_usage_calls = 0` | **both report 1**, `tokens_are_lower_bound = true`, same request id |

**The two findings the coordinator confirmed as not in doubt are in different states.** The
`used_seeds.json` writer now exists and is enforced (CLOSED, row EXEC-E2). The withdrawn
abstention language is gone from `protocol_FINAL.md` — the lines the task cites as 178, 206
and the five "near-certain" sites no longer carry it — but it **survives as an active
assertion in `COORDINATOR_DECISIONS.md` itself**, which the task names binding. See row
STAT-1 and "Still open" §1. The withdrawal has moved from one document to the other; it has
not finished travelling.

The **#11 suite is green: 461 run, 461 passed, 0 failed, 0 errors, 0 skipped.** The **#12
suite is not: 3 of 88 tests fail and 1 of 18 fixtures fails**, all from one cause — the #11
protocol repair invalidated a #12 provenance pin. That is a real, unfixed breakage and it is
row PROV-6 / "Still open" §3.

---

## Findings table

### `arxiv_live_candidate_statistics_review.md`

| id | what it said | what changed | state | evidence command and its TRUE output |
|---|---|---|---|---|
| **STAT-1** (§1) | `protocol_FINAL.md:178` heading "guaranteed-abstention deploy route"; `:203–207` "the unreachability result below is untouched"; `:237–249` "PRE-SPECIFIED NEAR-CERTAIN ABSTENTION" from the same-task pilot s.e. 0.0151 ("about 8.5 standard errors"); `:301–302`, `:88`, `:293–298`. Remove "guaranteed", "unreachability", "near-certain" and the 8.5-SE rationale from all active claims/templates; keep `.03`, the horizon and the rule. | `protocol_FINAL.md` §1.3 is now "Declaration: this is a prospective feasibility study, and what its thresholds do and do not say". Line 88 is the corrected conditional statement (threshold `0.1279515`, `17,097` at zero difference, "do not calibrate the probability of deployment or abstention"). `:255` "No uncertainty scale is attached to these thresholds, deliberately"; `:264–265` and `:363–369` turn the four phrases and the pilot s.e. into explicit prohibitions. `ARCHITECTURE_FINAL.md:82–84` matches. `tests_lab_stats.TestActiveClaimLanguage` (5 tests) gates both documents against 19 assertive constructions. **But `COORDINATOR_DECISIONS.md` is not gated and still asserts the withdrawn wording at `:99`, `:190–191`.** | **PARTLY** | `zsh w5_language.sh`. In `protocol_FINAL.md` + `ARCHITECTURE_FINAL.md` there are 17 hits and **every one is a prohibition or a different sense of "unreachable"** (dead code at `ARCH:126,1064,1494,2457`; `test_deploy_threshold_at_scale` is labelled "conditional, never an impossibility" at `ARCH:2332`). In `COORDINATOR_DECISIONS.md`, 8 hits, of which `:99` "The protocol states this correctly as a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION, not an impossibility" sits **outside** the bracketed withdrawal that closes at `:98`, and revision 5's own "CORRECT STATEMENT" at `:190–191` reads "a paired standard error of 0.0151, so the threshold is about 8.5 standard errors away; the deploy route is therefore a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION". Revision 5 `:197` forbids three phrases and **omits** "near-certain abstention", which `protocol_FINAL.md:265` forbids — the two binding documents contradict each other. `cd experiments/live_ab && python -m unittest tests_lab_stats.TestActiveClaimLanguage -v` → `Ran 5 tests ... OK` (it scans only the two `ACTIVE_DOCS`). |
| **STAT-2** (§2) | Positive: formula, `.00625 × 4 × 2 = .05` allocation, randomized-prefix gates, strict comparisons, comparator/partial-outcome certificates, design/causal scope all agree with the declared target. Not a defect. | Nothing required. Re-verified incidentally: `r(100) = 0.4656929205179653` (so `1 − r(100) = 0.5343070794820347`, the coordinator's counterexample value), `r(568) − .03 = 0.1279515124940428`, first `n` with `r(n) < .03` is `17,097`, all recomputed from the pinned `src/winstats.py`. | **NOT-A-DEFECT** | `python w1_clip.py` → `"frozen_clip_default": {"L_h": -0.4656929205179653, "U_h": 0.4656929205179653, "decision": "horizon_no_decision", "alpha_gate": 0.00625, "rho": 100.0, "delta": 0.03, "n_min": 100}`. `tests_lab_stats.TestActiveClaimLanguage.test_the_declared_threshold_matches_the_frozen_radius` → ok. |
| **STAT-3** (§3) | `lab_monitor.py:133–134` accepted any `-1 <= clip_lo < clip_hi <= 1` although its error message says the clip is frozen at `[-1,1]`; `from_config` forwarded it. Witness: clip `[.2, 1]` at 100 complete zero-score pairs → both lower bounds `.2` → `decide` returns `deploy_candidate`, falsely excluding the true target 0. Enforce exact equality to `(-1., 1.)` and add a rejection fixture. | `MonitorConfig.__post_init__` now enforces `(self.clip_lo, self.clip_hi) != (-1.0, 1.0) → FrozenMismatch`, with the witness written into the comment. Enforced on the dataclass itself, so `from_config` and direct construction both refuse. | **CLOSED** | `python w1_clip.py` → `W1_VERDICT: CLOSED`. The root's exact config: `"altered_clip_0.2_1.0": {"refused": true, "exception": "FrozenMismatch", "message": "the clip is frozen at [-1.0, 1.0]; it is the known score range, not a tunable window (got [0.2, 1.0])"}`. It is an equality test, not an ordering test: `(-1.0, 0.9)`, `(-0.9, 1.0)`, `(0.0, 1.0)` and `(-1.0, 1.0000001)` all refuse; `(-1, 1)` (ints) is accepted and normalised. Direct `MonitorConfig(clip_lo=0.2, clip_hi=1.0)` also refuses. The frozen path is unchanged: 100 zero-score pairs still give `horizon_no_decision`. |
| **STAT-4a** (§4) | `lab_reference_rule.py:214–215` labels a partial cost certificate's decisive tier 1; the tier is not certain (the pending partner may fail, making tier 0 decisive). Return −1. Also correct the live comment at `lab_enclosure.py:492–493`. | `lab_reference_rule._hierarchy_enclosure` now returns `sgn, sgn, -1` under a binding cost certificate, with the reasoning written out and cross-referenced to the statistics review. `lab_enclosure.py:489–500` comment corrected the same way; `pair_enclosure`'s docstring states it. | **CLOSED** | `sed -n '215,226p' lab_reference_rule.py` → "the SCORE is certain … but the DECISIVE TIER is not … So the score collapses and the tier stays -1 … (statistics review section 4)", followed by `return sgn, sgn, -1`. `sed -n '493,499p' lab_enclosure.py` → "The TIER is not certain, and this certificate does not claim it is". |
| **STAT-4b** (§4) | `protocol_FINAL.md:1519–1520` says jointly valid marginal bands "are not a two-dimensional region"; their Cartesian product *is* a valid simultaneous rectangle. State it as a conservative rectangle or drop the denial. | `protocol_FINAL.md:1742–1743` now reads "their Cartesian product `[L_h, U_h] x [L_s, U_s]` **is** a valid simultaneous rectangular region for the pair of running targets at the stated joint level. What is not claimed is …". | **CLOSED** | `grep -n "two-dimensional\|rectangular\|Cartesian" design/protocol_FINAL.md` → only `:1742` and `:1743`, both the corrected wording. The denial is gone. |
| **STAT-4c** (§4) | `lab_reference_rule.py:23` module summary says every `pair_enrolled` triggers evaluation, while both paths and the protocol trigger at `coin_drawn`. | The summary now reads: "8.3 The prefix `n` grows at `coin_drawn`, NEVER at `pair_enrolled`: a pair whose coin has not been drawn and fsynced is not randomized, holds no position and produces no evaluation (COORDINATOR_DECISIONS revision 4 ruling 17)", and lists all five triggers. | **CLOSED** | `sed -n '18,30p' lab_reference_rule.py`, output quoted at left. |

### `arxiv_live_candidate_execution_review.md`

| id | what it said | what changed | state | evidence command and its TRUE output |
|---|---|---|---|---|
| **EXEC-E1** | `lab_orchestrator.py:269–303` incremented `unknown_usage_calls` only for `llm_error`. A durable `llm_request` with no terminal event is expressly permitted after `worker_died`/`episode_timeout`/`interrupted`, and the terminal reconstruction writes `episode_revealed` without minting an `llm_error` — so an interrupted request with unknown tokens produced **zero** unknown-usage calls. The verifier repeated the omission (`lab_verify_log.py:867–898`), so byte-equality could not detect it. Derive unknown usage by request id; add a fixture. | Two independently written functions now exist and are kept separate on purpose: `lab_orchestrator.unknown_usage_by_request` (a request is known only on `llm_response`, or on `llm_error` carrying `usage_known: true`) and `lab_verify_log._unknown_usage_requests` (three-state `receipted`/`unreceipted`/`outstanding`). Both key on request id, so a repeated or duplicated event cannot double count. `tokens_are_lower_bound` is set from the count, so the ledger states its own incompleteness. Six new tests in `tests_lab_serving.ExposureLedgerUnknownUsageTests` pin the expected numbers by hand **before** comparing the two implementations. | **CLOSED** | `python w4_unknown_usage.py` → `W4_VERDICT: CLOSED`. The root's fixture, rebuilt from scratch without the repo's test helpers: `"orchestrator_cell": {"unknown_usage_calls": 1, "tokens_are_lower_bound": true, "episodes": 1, "prompt_tokens": 0}`, `"verifier_cell"` identical, `"ledgers_byte_equal": true`. **They agree for the right reason**: both name the same id, `{"rrrrrrrr": 1}` — `"same_ids_not_merely_same_total": true`. The old rule re-implemented in the witness returns `"old_rule_count_on_same_fixture": 0`, so the repair is what changed the answer. Controls: a receipted request gives `unknown_usage_calls = 0, tokens_are_lower_bound = false`; an `llm_error` declaring `usage_known` gives `{}`. |
| **EXEC-E2** | Jobs point to `<trial work>/used_seeds.json` and each worker loads it, but the candidate contains **no writer**; a missing file silently yields an empty set, so uniqueness held only within one episode. `verify_program()` did not combine seeds across trials. Probe: initialise twice with forced entropy → seeds `[42, 42]`. | `lab_orchestrator` now has `seed_registry_path` / `seeds_from_spool_lines` / `seed_registry_reconstruct` / `write_seed_registry`, and `World.load_seed_registry` (called at start **and** resume), `note_seed` (called from the **spool** ingest, `:1857`, so a line already projected by an earlier invocation is still counted) and `persist_seed_registry` (called before every dispatch, `:1756`, `:2377`). The registry sits at the **program** work root. Reconstruction reads `<work root>/*/spools/*.jsonl`, i.e. the write-ahead record, so it survives an unclean exit. `lab_verify_log.program_seed_collisions` adds the cross-trial check. Severity stays `DEFECT`, per protocol 5.5. | **CLOSED** | `python w3_seeds.py` → `W3_VERDICT: CLOSED`. Control (registry bypassed, the root's original probe): `"A_control_no_registry": {"seeds": [42, 42], "duplicate": true}`. Enforced: first episode draws 42 and spools it; ingest writes `"registry_bytes": "[42]"`; the second episode with the **same forced entropy** is `"refused": true, "message": "seed space exhausted for worker_index 0"` — it will not return a duplicate — and with entropy that moves on it redraws `44`. **Crash:** registry file deleted, `"rebuilt_from_spools_alone": [42]`, still refused. **Stale registry** (crash between the spool write and the flush): `"stale_registry_contents": []`, `"rebuilt_on_resume": [42]`, still refused. **Program scope:** a seed from trial T2 and one from T4 reconstruct together, `[42, 43]`; the halves split correctly (`worker0_half [42]`, `worker1_half [43]`) and worker 1 on the same raw entropy word gets 43, is refused, and on fresh entropy gets the odd seed 51. |
| **EXEC-E3a** | The `plan_resume`/`_w_draw_coin` distinction is the right one, but the protocol/state-machine wording must specify the same moment; `IMPLEMENTATION_STATUS.md:194–228` records the conflict. Propagate the recorded coordinator ruling (rev 4 ruling 17) consistently and test the event ordering. | `lab_reference_rule` summary, `protocol_FINAL` 8.3 and the reference module all now say the prefix grows at `coin_drawn`. `defect_monitor_cadence.jsonl` and `defect_order_enrollment.jsonl` fixtures are present and exercised. | **CLOSED** | Suite run below: `tests_lab_chain.py` 58/58 and `tests_lab_e2e.py` 42/42 pass, including the cadence fixtures. `sed -n '24,30p' lab_reference_rule.py` quotes ruling 17 by number. |
| **EXEC-E3b** | The T4 canonical payload retained `inv`, so a pair split across invocations failed A/A byte identity although the scientific configuration was unchanged — and the candidate kept a **passing** test named `test_t4_payload_identity_breaks_when_a_pair_spans_two_invocations`, reproducing the defect rather than resolving it. | `inv` is now in `CANONICAL_JOB_DROP` alongside `worker_index`, with the reasoning written into `lab_orchestrator.py:255–270`. The test is renamed and inverted: `tests_lab_e2e.py:462 test_t4_payload_identity_survives_a_pair_spanning_two_invocations`. Every key that defines the configuration stays in the payload, so genuine drift still fails; `defect_t4_payload_identity.jsonl` and `lab_verify_log`'s `t4.payload_identity` FAIL are retained. | **CLOSED** | `grep -n payload_identity tests_lab_e2e.py lab_verify_log.py` → `tests_lab_e2e.py:462 …survives_a_pair_spanning_two_invocations`, `tests_lab_e2e.py:507 test_t4_payload_identity`, `lab_verify_log.py:70 't4.payload_identity': 'FAIL'`. Both pass in the suite run below. |
| **EXEC-E4** | Protocol §5.5 said the seed is written to both worker spool and `llm_request` before POST. The client durably writes `call_started` before the request; the orchestrator projects the spool into `llm_request` later. No pre-POST chain handshake exists. Distinguish the two guarantees or implement the handshake. | `protocol_FINAL.md` §5.5 now has a paragraph headed **"What is durable before the POST"** which names the spool line as the write-ahead evidence and calls `llm_request` "the orchestrator's **asynchronous projection** of that spool line". `ARCHITECTURE_FINAL.md` PG-8 says the same and adds why a handshake was not added ("adding one would put a round trip inside the measured `latency_s`"). | **CLOSED** | `sed -n '957,960p' design/protocol_FINAL.md`, output quoted at left. |
| **EXEC-R1** | "Do not label this review '304/304 independently passed' or 'protocol frozen'." Keep the owner's count, the audit's partial results, freeze approval and delivered evidence as separate states. | The suite is now 461, not 304, so the number itself is stale wherever it appears. `results/SESSION60_RESULTS_INDEX.md:56` still says "**304 tests pass**" and "harness complete and green"; `IMPLEMENTATION_STATUS.md` §3 still publishes the 304 table. | **OPEN** | See PROV-5a and "Still open" §2. |
| **EXEC-R2** | A cache prerequisite and an offline preparation/check command should accompany the handoff; supply a pinned runnable environment. The root's 4 failures were the inherited Seatbelt profile denying execution under `/opt` (probe return code 71). | Not addressed in this pass. The 16 legacy cases the root could not run **do** run here, because `work/local_stream/data/` exists on this host with `sanitized-mbpp.json`, `HumanEval.jsonl.gz`, `tasks.json`, `data_manifest.json`. That is a property of this machine, not of the handoff. No `PREPARE.md`, cache-check command or environment lock was added. | **OPEN** | `ls work/local_stream/data/` → the four files above. `grep -rn "cache" experiments/live_ab/README.md` finds no preparation command. The 4 root failures cannot be reproduced here (they pass) and cannot be re-run there (no pinned environment was supplied). See "Reproduction limits". |
| **EXEC-R3** | Ten dormant `skipTest` guards, two spelling-based PG-16 checks, three wall-clock loops without explicit `TimeoutError`, and one unidentified historical flake (= coordinator ruling 20's hardening list). | The flake test passes here (`ExecutionLockTests`, 3/3). The skip guards went from ten to **eight** and are still guards, not hard failures: `tests_lab_design.py:1258`, `tests_lab_e2e.py:231,1177`, `tests_lab_isolation.py:144,163,542,548`, `tests_lab_stats.py:1662`. No `TimeoutError` appears in any test file. The two PG-16 spelling checks are unchanged. | **PARTLY** | `grep -n skipTest tests_lab_*.py` → 8 hits, listed at left. `grep -c TimeoutError tests_lab_*.py` → `0` in all seven files. Suite reports `skipped = 0`, so all eight are dormant — which is exactly the hazard ruling 20 names: a removed module would make them go quiet, not red. |
| **EXEC-R4** | D1/D2/D4 use reduced mock screening prefixes and D3 uses the mock-only `delta = 0.9`; their success exercises paths, not power at `n_min = 100`, `delta = 0.03`. | Unchanged and still disclosed: `IMPLEMENTATION_STATUS.md` §3 prints the mock override block (`n_min=6`, `mock_overrides={"monitor.n_min": 6}`, D3 additionally `{"monitor.delta": 0.9}`) and states that the committed `config.json` is unmodified. | **CLOSED** (as a disclosure requirement) | Dry run below decides at `n = 39/40/44/40`, all far below `n_min = 100`, exactly as the disclosure says. The shipped `config.json` still reads `n_min=100, delta=0.03, alpha_gate=0.00625, rho=100.0`, confirmed by `w1_clip.py`'s `frozen_clip_default` block. |

### `arxiv_live_candidate_provenance_review.md`

| id | what it said | what changed | state | evidence command and its TRUE output |
|---|---|---|---|---|
| **PROV-1** | `git diff LIVE VALIDATION` was one file; zero tracked files under `experiments/live_ab_validation/`. Change "The frozen protocol is published before any simulation outcome exists" to "will be published and pinned before simulations run". | `experiments/live_ab_validation/` now exists with `PROTOCOL.md`, `vband.py`, `vfixtures.py`, `tests_validation.py`, `cells.json`, `pinned/`, `PREREG_CHECK.md`, `PREREG_CHECK_2.md` — a real package, not an index entry. **But the index sentence was not changed**: `results/SESSION60_RESULTS_INDEX.md:61` still reads "The frozen protocol is published before any simulation outcome exists." | **PARTLY** | `ls experiments/live_ab_validation/` → the eight entries above. `grep -n "published before any simulation outcome exists" results/SESSION60_RESULTS_INDEX.md` → `61:…The frozen protocol is published before any simulation outcome exists. No simulation outcome exists yet.` The ambiguous tense the review asked to fix is verbatim intact. |
| **PROV-2** | 29 null leaves in `config.json`; no real `results/live_ab/freeze/` bundle, roster, arrival orders, exposure ledger, prefreeze chain or external receipt. Legitimate placeholders, but not measured values. | Unchanged by design — nothing is frozen and no trial has run, which is the correct state. `MonitorConfig.from_config` still refuses a null runtime horizon (verified: the W1 witness had to inject a synthetic `n_max`, exactly as the root's fixtures did). | **OPEN, correctly** (a pre-freeze prerequisite, not a defect) | `python w1_clip.py` needed `mon["n_max"] = 100` injected to run at all; without it `from_config` raises. `ls results/live_ab/` → no such directory. |
| **PROV-3** | **The main executed witness.** `make_context` defaults runtime config/order/roster digests to the currently read file bytes; `preflight` compared config bytes with that runtime digest, checked roster/order **existence** only, and compared the bundle's canonical digest with `ctx.bundle_sha` — it did **not** compare each member with its hash inside the bundle. `build_freeze_bundle` existed but preflight never called it. Hardware was recorded at trial start, not compared with the allowlist. Witness: bundle fixed with the original config hash, `delta` .03 → .04, runtime hashes from current bytes → `preflight` returned `[]` for both. Also: CLI default `bundle_sha` hashed raw bytes while preflight hashed canonical JSON, so pretty-printing produced `freeze_bundle_drift`. Require a regression test over config, roster/order, reference/harness file, serving manifest and hardware identity. | `lab_common` now declares `BUNDLE_MEMBERS_RECOMPUTED` (18 members) and `BUNDLE_MEMBERS_NOT_RECOMPUTED` (8, "DECLARED rather than silently skipped"), plus `verify_bundle_members`. `lab_orchestrator.observed_bundle_members` recomputes every recomputable member from the deposited tree and the working copy; `preflight` compares them against the **fixed** bundle, maps each to a closed refusal code via `MEMBER_REFUSAL`, and now **compares** `lab_common.hardware_identity()` against the bundle allowlist. The roster is recomputed by `lab_data.roster_sha256` from the object, so rewriting a roster's own `roster_sha256` field does not help. `PreflightError` now carries `drift`, so a refusal names which artifact moved. The CLI default is now `lab_common.freeze_bundle_sha256_of_file`, which canonicalises. | **CLOSED** | `python w2_preflight.py` → `W2_VERDICT: CLOSED`. Baseline on the untampered tree accepts twice: `"S0_baseline_untampered": {"baseline": {"refused": false, "drift": []}, "after_alteration": {"refused": false, "drift": []}}`. Then, bundle held fixed, one artifact altered at a time — every scenario's own baseline accepts first, so the refusal is caused by the alteration and nothing else: **delta .03→.04** `reasons ["config_sha"]`, `drift ["config_sha256","rule_block_sha256"]`; **roster** (content *and* its self-declared digest rewritten) `["roster_sha"]`, `["roster_sha256","task_content_sha256"]`; **arrival order** `["order_sha"]`, `["arrival_order_sha256"]`; **reference rule** `["harness_file_sha"]`, `["harness_file_sha256.lab_reference_rule.py","reference_rule_sha256"]`; **harness file** (`lab_monitor.py`) `["harness_file_sha"]`, `["harness_file_sha256.lab_monitor.py"]`; **serving manifest** `["config_sha","serving_manifest"]`, `["config_sha256","serving_manifest_sha256"]`; **hardware identity** `["hardware_allowlist"]`, `["hardware_identity"]`. Canonical-digest convention: a pretty-printed bundle hashes to `6ba42e47…` raw but `10bb7db3…` canonically, and `freeze_bundle_sha256_of_file` returns `10bb7db3…` — `"of_file_matches_canonical": true`, so the CLI and preflight now agree. No repository file was modified: the harness was copied to a temp directory and `lab_common.HERE` pointed at the copy. |
| **PROV-4** | S1 591 / S2 at most 541 after the six smoke exclusions; the horizon is `floor(n_S1/2)+floor(n_S2/2)`, at most **565**, not 568; leftovers are `(n_S1 % 2) + (n_S2 % 2)`, not unconditionally "one per stratum"; four trials reuse one roster, so do not pool them as independent replications; the configured seed rule is not a deposited live seed receipt. | `protocol_FINAL.md:78` now says "at most 565 … `568` is … a **loose pre-exclusion bound, not the horizon**"; `:189–200` marks the 568 row "(pre-exclusion bound)" and the 569 row "reference row only"; `:630`, `:1690`, `:2045`, `:2066–2067`, `:2095` all carry the 565/568 distinction. | **CLOSED** | `grep -n "565\|568" design/protocol_FINAL.md` → 16 hits, every one qualified. Example `:78`: "**at most 565** once the six declared smoke tasks are excluded and smaller after the remaining exclusions of 3.2. `568` is the same rule applied to the candidate lists 591/547, i.e. a **loose pre-exclusion bound, not the horizon** (3.3)." |
| **PROV-5a** | The index's "harness complete and green" and "blocked on host quiescence, not on code" overstate the delivered state. Recommended status: "Substantial harness and mock tests delivered; independent validation package, required code hardening, real preflight/rehearsal, roster, and freeze artifacts pending…". | Not changed. | **OPEN** | `grep -n "harness complete and green" results/SESSION60_RESULTS_INDEX.md` → `56:- Status: **harness complete and green** (17 modules, 12,002 lines; 6 test files, 8,103 lines; **304 tests pass**; …)`. There are now **7** test files and **461** tests. The line is stale in three ways at once. See "Still open" §2. |
| **PROV-5b** | The host-contention plan asked to log an offending raw command line, which can expose local paths and account names and conflicts with the closed public schema. Log a process-kind label, counts, measurements and a digest instead. The coordinator note itself contains a literal user-specific path. | **The schema half is closed.** `lab_eventlog.HOST_SCAN_FIELDS` carries only `point, clean, scanned, allowlisted, findings, degraded, baseline, baseline_active`, all closed-vocabulary; `protocol_FINAL.md` 5.7.1 states that findings carry "the SHA-256 of the offending `argv`" and that "the command text and the token summary derived from it are **not** published", with the reason given. **The literal path is not removed:** `COORDINATOR_DECISIONS.md:216` still contains `/Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing`, which `protocol_FINAL.md:2742` names as a forbidden pattern (`/Users/`). | **PARTLY** | `grep -n HOST_SCAN_FIELDS -A5 lab_eventlog.py` → the eight closed fields, no command-line field. `grep -n "/Users/" design/COORDINATOR_DECISIONS.md` → `216: /Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing, running run.py --stage branch`. `grep -n "/Users/" design/protocol_FINAL.md` → `2742:` the redaction rule that forbids it. |
| **PROV-6** | *(not a root finding — a regression this pass found)* | — | **OPEN** | The #11 protocol repair invalidated the #12 provenance pin. See "Still open" §3 and the run numbers below. |

### `arxiv_live_candidate_disposition.md`

| id | what it said | what changed | state | evidence command and its TRUE output |
|---|---|---|---|---|
| **DISP-1** | Bind execution to the reviewed freeze; validate all required bundle members; bind the expected bundle identity independently; one canonical digest convention in CLI and verifier. | See PROV-3. | **CLOSED** | `python w2_preflight.py` → `W2_VERDICT: CLOSED`, seven alterations refused, CLI/preflight conventions agree. |
| **DISP-2** | Reconcile ledger edge cases: persistent cross-trial seed bookkeeping and interrupted-call unknown-usage accounting; distinguish a bookkeeping defect from an invalidation of the bounded-mean theorem. | See EXEC-E1, EXEC-E2. The severity discipline is preserved: `lab_verify_log.CHECK_SEVERITY['seeds.unique'] == 'DEFECT'`, and a test asserts it must never be escalated to FAIL. | **CLOSED** | `python w3_seeds.py`, `python w4_unknown_usage.py` → both `CLOSED`. `tests_lab_serving.py:1669` asserts the DEFECT severity; it passes in the suite run below. |
| **DISP-3** | Enforce the declared statistical contract and repair active text: reject other clip intervals; preserve the public withdrawal but remove remaining active guaranteed-outcome wording and the near-certain inference from a same-task pilot s.e. | Clip: CLOSED (STAT-3). Text: PARTLY (STAT-1) — repaired in the two documents the suite gates, still asserted in `COORDINATOR_DECISIONS.md`. | **PARTLY** | See STAT-1 and STAT-3. |
| **DISP-4** | Complete the recorded freeze prerequisites: 29 null facts, real roster/horizon/serving receipts/timeouts/hardware; use 565 not 568; propagate cadence/signature rulings; complete test hardening and serving checks. | 565/568 CLOSED (PROV-4); cadence ruling CLOSED (EXEC-E3a); 29 nulls correctly still open (PROV-2); test hardening PARTLY (EXEC-R3); **the signature ruling is not discharged** — the gate still prints three deviations from ARCHITECTURE §3, and ruling 19 requires it to print none at freeze time. | **PARTLY** | End of the suite log: `[signature gate] DEVIATION from section 3: lab_hostcheck.enumerate_foreign_consumers: extra keyword-only parameter(s) ['baseline_activity'] beyond section 3`; `… lab_server.restart: extra … ['golden', 'sampling']`; `… lab_server.start: extra … ['golden_props', 'golden', 'sampling', 'timeout_s', 'recompute_gguf_sha256']`. The two `lab_server` rows are the ones ruling 19 accepted and ordered documented; the `lab_hostcheck` row is **new**, introduced by the quiescence-gate work, and no ruling covers it. `tests_lab_isolation.test_other_group_signatures` runs non-strict, so it prints and passes. |
| **DISP-5 / DISP-6** | A documented host-load requirement is not an executable gate: at `5776877`, `lab_orchestrator.py:409–496` had no foreign-load detector and `lab_eventlog.py:183–187` had no refusal code and no `foreign_load_detected` event. Implement the detector, the before-run refusal and the mid-run event as chain events; report the detector's actual coverage and sampling times; do not terminate other owners' jobs. | `lab_hostcheck.py` exists (1,282 lines) with `preflight_host_quiescent`, `soft_host_check`, `enumerate_foreign_consumers`, three detection rules (exact runner token; any python holding any Metal resource; ≥128 MiB holding a **compute-class** Metal resource, which defeats a rename), a stated blind spot for sub-floor jobs, and `HostNotQuiescent` subclassing `PreflightError`. Wired in `lab_orchestrator.host_quiescence_gate` (hard gate before the chain opens) and `World.host_scan` (trial-start and quiescent scrapes). `lab_eventlog` carries `host_quiescence_refused` and `foreign_load_detected`, plus `preflight_refused(host_not_quiescent)`. Protocol 5.7.1 states it "**observes only**: it never terminates, suspends or reprioritises any process it finds". 117 tests in `tests_lab_hostcheck.py`. | **CLOSED** | `grep -n "host_quiescence_gate\|host_quiescence_refused\|soft_host_check" lab_orchestrator.py` → `:878`, `:889`, `:905`, `:1563`, `:1565`. `grep -n "foreign_load_detected\|host_quiescence_refused" lab_eventlog.py` → `:405`, `:458`, `:577`, `:583`. `tests_lab_hostcheck.py` loads **117** tests, all passing in the suite run below. |
| **DISP-7** | The public chain must not copy arbitrary foreign command lines; use an allowlist of process classes and sanitized identifiers/digests; test refusal, newly-appearing load and cleanup of this harness's own fixtures. | Closed in the schema (PROV-5b). Tests for refusal, newly-appearing load, degraded scans and fixture cleanup are in `tests_lab_hostcheck.py`. | **CLOSED** | Same as PROV-5b plus the 117 passing host-check tests. |

### `arxiv_baseline_daemon_policy_review.md`

Note first: this review reviewed **ruling 28** (revision 7), which the coordinator then
**withdrew and replaced** in revision 8. The rows below check the current implementation
against revision 8 *and* against each clarification, since revision 8 adopts most of them.

| id | what it said | what changed | state | evidence command and its TRUE output |
|---|---|---|---|---|
| **BASE-1** | Ruling 28 promised a closed list but used a `/System/...` **path prefix**. Deliver exact resolved executable-path entries and matching rules, not a blanket prefix or a name-only match; include the list in the freeze; test allowed, disallowed and ambiguous identities. | `lab_hostcheck.BASELINE_EXECUTABLES` is a dict of **exact resolved absolute paths** → closed-vocabulary label, with one entry. `BASELINE_PATH_PREFIX = '/System/'` is explicitly described as "a second lock on the LIST, not a matching rule for a process". The ambiguous case is written into the source: `…/MediaAnalysisAccess.framework/…/mediaanalysisd-access` is a different binary whose basename contains the same word, is **not** on the list, and refuses on presence — "A name-only or prefix rule would have admitted it silently." | **CLOSED** | `sed -n '163,190p' lab_hostcheck.py`, quoted at left. The allowed/disallowed/ambiguous triple is covered in `tests_lab_hostcheck.py` (117 tests, all pass). |
| **BASE-2** | "Materially active" was undefined. Freeze the CPU-time threshold, measurement interval/normalization, scan cadence, trial-overlap flag and missing/degraded-scan treatment. State the resident-size floor and units. **An unavailable measurement is unknown, not zero activity.** | `BASELINE_ACTIVITY_INTERVAL_S = 10`, `BASELINE_ACTIVITY_THRESHOLD_MS = 500` (strict `>`, so exactly 0.5 CPU-s is idle), `BASELINE_MIN_INTERVAL_MS = 8000` (a sample over a shorter measured interval is discarded as UNKNOWN). Normalization is stated as **none**, in raw milliseconds of cumulative CPU time summed over threads, explicitly not per-core and not a percentage. `SCAN_POINTS = ('trial_start', 'quiescent')`. `TRIAL_OVERLAP_RULE` is a structural reading rule, not a judgement. `PROBE_RSS_FLOOR_BYTES = 128 * 1024 * 1024`, published in the scan body as `rss_floor_bytes`. The activity vocabulary is four-valued with **no boolean**: `active` refuses, `idle` is recorded, `exited` is neither, `unknown` **degrades the scan so the preflight refuses** — the comment names clarification 2 as the reason a boolean was rejected. | **CLOSED** | `sed -n '192,240p' lab_hostcheck.py`, quoted at left. `grep -n PROBE_RSS_FLOOR_BYTES lab_hostcheck.py` → `:269 = 128 * 1024 * 1024`, `:579 'rss_floor_bytes'`. |
| **BASE-3** | Replace "what the gate proves" with a narrowed statement; a CPU-time delta does not establish accelerator activity or inactivity; drop the claim that refusal could never pass on a normal host. | `lab_hostcheck.py:26–31` states it in the review's own words: "At the recorded scans, the detector reported no non-baseline process satisfying the frozen detection criteria above the frozen resident-size floor, and every frozen baseline process it did find is recorded with its measured CPU delta", followed by the explicit note that CPU-time deltas do not measure the accelerator. `protocol_FINAL.md` §5.7.1 is titled "Host quiescence: **what a scan reports, and what it does not establish**" and states the blind spot for sub-floor jobs. | **CLOSED** | `sed -n '20,35p' lab_hostcheck.py` and `sed -n '1025,1050p' design/protocol_FINAL.md`, quoted at left. |
| **BASE-4** | Preserve the actual operating regime: report permitted baseline activity and detection limits beside latency; apply a frozen response to newly detected load while preserving enrolled pairs, failures and unknown usage; do not retrospectively adjust latency, drop pairs, redraw assignments or restart on outcomes; keep the sanitized schema. | Revision 31(c)–(d) is implemented: a baseline daemon that wakes mid-trial does **not** abort it, is recorded at every scan active or not with elapsed time, resident size and CPU delta, and names the affected window beside the latency tier. "No latency number is ever adjusted." The thresholds are frozen in the freeze bundle and 31(f) forbids tuning them after a refusal. Schema sanitized (PROV-5b). | **CLOSED** | `sed -n '286,296p' design/COORDINATOR_DECISIONS.md` (ruling 31(c)–(f)) and `lab_hostcheck.py:75–96`. The 117 host-check tests pass. |

---

## Run results — TRUE numbers

All four runs below were executed in this pass on the tree fingerprinted at the top.

### #11 suite

```
$ ./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py' -v
Ran 461 tests in 217.298s

OK
```

**461 run, 461 passed, 0 failed, 0 errors, 0 skipped.** Exit code 0.

Re-run after this file was written, to confirm that adding a document to `design/` does not
disturb the suite: `Ran 461 tests in 215.426s / OK`, exit code 0. Same for #12:
`ran=88 failures=3 errors=0 skipped=0` — unchanged, so the three failures are the stale pin
and nothing I did.

Per file, from `unittest.defaultTestLoader` (`countTestCases()`), which sums to the 461 above:

| test file | tests loaded |
|---|---:|
| `tests_lab_hostcheck.py` | 117 |
| `tests_lab_serving.py` | 89 |
| `tests_lab_design.py` | 78 |
| `tests_lab_stats.py` | 65 |
| `tests_lab_chain.py` | 58 |
| `tests_lab_e2e.py` | 42 |
| `tests_lab_isolation.py` | 12 |
| **total** | **461** |

Two things a reader should not gloss over. First, `tests_lab_serving.py` loads 89 but defines
only 73 `def test_` methods: the other **16 are the imported `tests_local_stream` classes**
(`AgentTests` 4, `SandboxTests` 7, `VerifyTests` 5) — precisely the "16 imported legacy cases
not run" in the root's accounting. They run and pass here only because this host has
`work/local_stream/data/`. Second, the suite emits three `[signature gate] DEVIATION from
section 3` lines and still passes, because that check is non-strict for other-group modules
(see DISP-4).

The count **grew from the stated 380 baseline to 461**. I did not measure a 380 baseline and
cannot confirm it: at `5776877` the seven test files define 288 `def test_` methods
(`tests_lab_hostcheck.py` did not exist), so 380 must have been measured part-way through
this round of repairs, not at the reviewed commit.

### Dry run

```
$ ./.venv/bin/python experiments/live_ab/dryrun_live_ab.py --scenario all
[MOCK] D1 status=ended verifier=PASS decision=harm_keep_incumbent@39
[MOCK] D2 status=ended verifier=PASS decision=horizon_no_decision@40
[MOCK] D3 status=ended verifier=PASS decision=deploy_candidate@44
[MOCK] D4 status=ended verifier=PASS decision=horizon_no_decision@40
```

Exit code 0. **4 scenarios, 4 verifier PASS, 0 fail.** Identical decisions and prefixes to the
root's own run, so nothing in the repairs moved a mock decision. These remain mock runs at a
reduced screening prefix, D3 additionally at the mock-only `delta = 0.9`; they exercise paths,
not power.

### #12 fixtures

```
$ ./.venv/bin/python experiments/live_ab_validation/vfixtures.py
...
FAIL F18_pinned_file_hashes
       provenance.vocabulary_alignment: experiments/live_ab/design/protocol_FINAL.md hashes to
       3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2, but cells.json pins
       dc681784504aaaf434b49ea8cd88fdc9a38efc438725600a773aef6ce641ce6f.
       The pin is stale: recompute it before the freeze commit

17/18 fixtures passed
```

Exit code 1. **18 run, 17 passed, 1 failed.**

### #12 tests

```
$ ./.venv/bin/python experiments/live_ab_validation/tests_validation.py
Ran 88 tests in 4.041s

FAILED (failures=3)
ran=88 failures=3 errors=0 skipped=0
```

Exit code 1. **88 run, 85 passed, 3 failed, 0 errors, 0 skipped.** The three are
`TestFixtures.test_every_fixture_passes(fixture='F18_pinned_file_hashes')`,
`TestPinnedFileHashes.test_every_pin_matches_the_file_it_names` and
`TestPinnedFileHashes.test_the_fixture_itself_passes` — one cause, three assertions.

**Combined: 567 tests run across #11 and #12, 563 passed, 4 failed** (plus 18 fixtures, 17
passed, 1 failed, and 4 dry-run scenarios, all pass).

---

## Still open

### 1. The withdrawal reached `protocol_FINAL.md` but not `COORDINATOR_DECISIONS.md` (STAT-1, DISP-3)

This is the same class of error the root caught the first time, one document further along.
The coordinator withdrew the unreachability claim; the repair propagated it into
`protocol_FINAL.md` and `ARCHITECTURE_FINAL.md`; the document the withdrawal was written in
still asserts the thing the statistics review said to remove:

- `COORDINATOR_DECISIONS.md:99` — "The protocol states this correctly as a PRE-SPECIFIED
  NEAR-CERTAIN ABSTENTION, not an impossibility." This sits **after** the bracketed
  `[WITHDRAWN …]` block that closes at `:98`, so it is not covered by that withdrawal, and it
  is now factually false: the protocol says the opposite.
- `COORDINATOR_DECISIONS.md:190–191` — revision 5's own "CORRECT STATEMENT" reads "a paired
  standard error of 0.0151, so the threshold is about 8.5 standard errors away; the deploy
  route is therefore a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION under pilot-like outcomes". This
  is verbatim the 8.5-SE rationale the statistics review §1 asked to remove and
  `protocol_FINAL.md:368–369` now explicitly forbids ("Also forbidden: attaching the pilot's
  same-task paired standard error (or any multiple of it, such as 'about 8.5 standard errors
  away') to a threshold of this trial").
- `COORDINATOR_DECISIONS.md:197` forbids three phrases and **omits** "near-certain
  abstention", which `protocol_FINAL.md:265` forbids. The two binding documents contradict
  each other on the contents of the ban list.

**Why the suite does not catch it.** `tests_lab_stats.ACTIVE_DOCS` is exactly
`("design/protocol_FINAL.md", "design/ARCHITECTURE_FINAL.md")`. The comment above it
classifies everything in `design/` as "the historical record of what was believed at the
time", which is the right treatment for `protocol_v3.md` and the audit files but is not
obviously right for a document the task calls binding and whose revisions 5 and 8 are cited as
live rulings.

**Why I did not fix it.** I am the verifier and may write only this file; and this is a
judgement for the coordinator, not a text edit. The document's own convention is
append-and-withdraw (`:95` and revision 8's withdrawal of ruling 28), not rewriting. The
smallest correct repair is a **revision 9** that withdraws the "near-certain abstention"
sentence and the 8.5-SE rationale from revision 5 the way revision 8 withdrew ruling 28, and
then adding `COORDINATOR_DECISIONS.md` to `ACTIVE_DOCS` if it is to be treated as binding —
or, if it is to be treated as a historical ledger, saying so in the file's own header so a
reader is not left to guess.

### 2. The results index still publishes the pre-repair state (EXEC-R1, PROV-1, PROV-5a)

`results/SESSION60_RESULTS_INDEX.md` was not touched by this round:

- `:56` — "Status: **harness complete and green** (17 modules, 12,002 lines; 6 test files,
  8,103 lines; **304 tests pass**; …)". There are now 7 test files and **461** tests, and
  "complete and green" is the phrasing the provenance review §5 asked to replace. The
  execution review's instruction was "Do not label this review '304/304 independently
  passed'"; the index still labels it 304.
- `:61` — "The frozen protocol is published before any simulation outcome exists." The
  provenance review §1 asked for "The protocol **will be published and pinned before
  simulations run**", keeping "No simulation outcome exists yet." The sentence is unchanged.

This file is outside `experiments/live_ab/` and is the coordinator's. I did not edit it.

### 3. The #11 protocol repair broke the #12 provenance pin (PROV-6)

`experiments/live_ab_validation/cells.json` pins `protocol_FINAL.md` at
`dc681784504aaaf434b49ea8cd88fdc9a38efc438725600a773aef6ce641ce6f`; the file on disk hashes
to `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2`. Three #12 tests and one
#12 fixture fail on it.

This has now happened **twice**. `cells.json:34` records the first occurrence in the #12
group's own words: the pin was stale at `03028374…` "was that file at commit `de31b6c`, and
the #11 quiescence-gate work had since added its section 5.7.1", so every pin was recomputed
and F18 was strengthened to open and hash each file rather than compare two documents'
strings. `cells.json` was last written at 00:35 UTC; `protocol_FINAL.md` was last written at
01:33 UTC. The #11 language repair invalidated it again, 58 minutes later.

**Why I did not fix it.** Recomputing the pin is a one-line change and I could have made it,
but it is the wrong move for three reasons, and the fixture's own message says so: (a) it is
not a syntax error or a stale import, it is a provenance pin, and the provenance review's own
instruction is "Do not replace frozen expected hashes with freshly observed values"; (b)
`protocol_FINAL.md` is still uncommitted and under active repair, so any value computed now
goes stale on the next edit — it already has, twice; (c) the correct moment is the freeze
commit, which is exactly what the failure message asks for.

**What should happen instead:** recompute all three pins in `cells.json`, `PROTOCOL.md` and
`pinned/PINNED.json` **as the last action before the freeze commit**, and add a cheap
ordering guard so a #11 document edit cannot silently invalidate a #12 pin again — the #12
suite failing is the guard, but it only fires if somebody runs it.

### 4. Ruling 19's signature gate is not discharged (DISP-4)

The suite prints three deviations from ARCHITECTURE §3 and passes anyway:

```
[signature gate] DEVIATION from section 3: lab_hostcheck.enumerate_foreign_consumers: extra keyword-only parameter(s) ['baseline_activity'] beyond section 3
[signature gate] DEVIATION from section 3: lab_server.restart: extra keyword-only parameter(s) ['golden', 'sampling'] beyond section 3
[signature gate] DEVIATION from section 3: lab_server.start: extra keyword-only parameter(s) ['golden_props', 'golden', 'sampling', 'timeout_s', 'recompute_gguf_sha256'] beyond section 3
```

Ruling 19 accepted the two `lab_server` signatures and ordered ARCHITECTURE §3 updated, with
"the signature gate must print no deviation at freeze time". §3 and the `SIGNATURES` table in
`tests_lab_isolation.py` were not updated. The `lab_hostcheck.enumerate_foreign_consumers`
row is **new** — introduced by the quiescence-gate work in this round — and no ruling covers
it. `test_other_group_signatures` runs with `strict=False`, so these print rather than fail.

### 5. Ruling 20's test hardening is two-thirds undone (EXEC-R3)

Eight dormant `skipTest` guards remain (`tests_lab_design.py:1258`,
`tests_lab_e2e.py:231,1177`, `tests_lab_isolation.py:144,163,542,548`,
`tests_lab_stats.py:1662`), down from ten. No test file contains `TimeoutError`, so the three
wall-clock loops still do not raise one. The two spelling-based PG-16 greps are unchanged.
All eight guards are dormant today (`skipped = 0`), which is exactly the hazard: a removed
module makes those tests go quiet instead of red.

### 6. A literal user path remains in an intended-public design document (PROV-5b)

`COORDINATOR_DECISIONS.md:216` contains
`/Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing`. `protocol_FINAL.md:2742`
lists `/Users/` among the patterns the redaction rule forbids in published artifacts. The
event schema is clean; this one line is not.

### 7. The superseded drafts still carry the withdrawn wording, unbannered (STAT-1, secondary)

Eleven files under `design/` still contain "guaranteed" / "unreachab" / "near-certain":
`audit_v3.md` (15 hits), `protocol_v3.md` (12), `R1_accepted_method.md` (5),
`protocol_draft_v2.md` (3), `protocol_draft_v1.md` (3), `audit_response_v3.md` (3),
`ARCHITECTURE.md` (3), `audit_v1_{claims,provenance,statistics}.md` (1 each),
`R4_power_analysis.md` (1). Treating them as a historical record is defensible and rewriting
them would falsify it — but only `protocol_v3.md` carries anything in its first eight lines
about supersession, and that line says v3 supersedes **v2**, not that v3 is itself
superseded. `ARCHITECTURE.md`, `protocol_draft_v1.md`, `protocol_draft_v2.md` and
`R1_accepted_method.md` carry no banner at all, so a reader who opens `protocol_v3.md:207`
finds "**A DEPLOY decision is therefore unreachable by construction at this scale, whatever
the outcomes**" with nothing on the page saying it was withdrawn. A one-line header on each
("superseded by `protocol_FINAL.md`; retained as a record; its unreachability claim was
withdrawn, see `COORDINATOR_DECISIONS.md` revision 5") costs nothing and falsifies nothing.

### Nothing breaks the scientific rule

No scientific rule moved in this round, and I checked rather than assumed: `alpha_gate
= 0.00625`, `rho = 100.0`, `delta = 0.03`, `n_min = 100`, clip `[-1.0, 1.0]`, the band formula
(`src/winstats.py` at `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`, the
value the config pins), the hierarchy `success > cost` with `cost = latency_s`,
`relative_tolerance = .05` and cost eligible only on joint success, the coin rule and the
enclosure rules are all as they were. `r(100) = 0.4656929205179653` and `r(568) − .03
= 0.1279515124940428` both recompute to the same bits.

---

## Reproduction limits

**Be blunt about this: the root could not reproduce the owner's suite, and neither of us has
shown the other is wrong.** The execution review's own accounting at `5776877` was
**264 passed, 4 failed, 20 blocked by missing benchmark caches, 16 imported legacy cases not
run**, on Homebrew Python **3.14.4** / macOS 26.6 arm64 / NumPy 2.4.1, against the owner's
**3.12** `.venv`, which was not available to them. Those numbers are the honest ones for that
host and are not superseded by the 461 I report here. My run is on the owner's own machine
with the owner's own interpreter and the owner's own caches, so it is the easiest environment
in which to get a green suite, not a reproduction.

Specifically:

1. **Interpreter.** The root ran 3.14.4; this pass ran 3.12.13 from
   `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`. No pinned environment
   file was delivered this round, so a third party still cannot construct either.
2. **Benchmark caches.** The root's 20 cache-blocked cases and the 16 legacy cases need
   `work/local_stream/data/` with `sanitized-mbpp.json`, `HumanEval.jsonl.gz`, `tasks.json`
   and `data_manifest.json`, and the pinned raw sources whose hashes are in `lab_data.py:68`.
   That directory exists on this host. It is **git-ignored**, it is not in either tracked
   tree, and nothing in the repository tells a reader how to obtain or verify it. At minimum
   the 16 imported `tests_local_stream` cases counted in my 461 cannot even load without it
   (that is the root's own diagnosis of its "serving-module import placeholder"), and the
   root additionally measured 20 cache-blocked cases; I did not re-measure the 20 by removing
   the directory, so treat "at least 16, plausibly 36" as the exposure, not a figure I
   verified. There is still no offline preparation command and no cache-check command; that
   was EXEC-R2 and it is untouched.
3. **Sandbox.** The root's four failures were traced to the inherited Seatbelt profile
   denying process execution under `/opt` (`sandbox_minimal_probe.json`, return code 71,
   `Operation not permitted`), consistent with `experiments/local_stream/sandbox.py:49,81`.
   Those four tests pass here. That does **not** prove the root's diagnosis wrong; it proves
   this host's profile permits what theirs denied. `test_reference_sweep_excludes`,
   `test_execution_lock_serialises_two_workers`, `test_agent_unchanged_and_runs_end_to_end`
   and `test_truncation_is_not_an_error` all pass here, and the lock test's 0.6 s sleep is
   observed, so the lock fixture is not an algorithmic defect — but the environment question
   is unresolved, not answered.
4. **The unreproduced flake.** `IMPLEMENTATION_STATUS.md` §6 records one historical flake.
   It did not appear in this run. One green run does not close a flake, and I am not claiming
   it does.
5. **The five reviews are not where the task says they are.** They are on `origin/main`
   (`c15d1c7`, `69ff058`), not on local `main` and not in the working tree. A reader who runs
   `ls reviews/` will not find them.
6. **What this pass did not do.** No trial episode, no freeze, no model call, no network, no
   real llama-server, no real preflight against a populated freeze bundle (the W2 witness
   builds a synthetic but real freeze tree in a temp directory — it demonstrates the binding
   logic, not a completed run), no external anchor, no host scan against live foreign load,
   no `git` mutation of any kind, and no edit to any file other than this one.

**What a reader needs to reproduce my numbers.** macOS arm64; CPython 3.12.13 at
`.venv/bin/python` with NumPy 2.4.1; a Seatbelt profile that permits execution of that
interpreter; `work/local_stream/data/` populated with the four pinned files; the working tree
fingerprinted at the top of this document. Measured wall times on this host: **217.3 s** for
the #11 suite, **53.5 s** for the dry run (`real 53.47`), **4.0 s** for the #12 tests and
**0.63 s** for the #12 fixtures. Take away the cache directory and at least 16 tests stop
being passes. Take away the sandbox permission and, on the root's evidence, four more do.

---

## Trivial breakage fixed by this pass

None. Nothing another group left required a repair to run the witnesses or the suites. The
one breakage found — the stale #12 pin — was deliberately **not** fixed, for the reasons in
"Still open" §3.
