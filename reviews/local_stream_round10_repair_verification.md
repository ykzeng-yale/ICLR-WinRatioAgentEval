# Local stream: independent verification of the Round 10 repair

Date: 2026-09-19. Verifier: independent agent (did not write the repair). Binding requirements: the root's Round 10 audit of PR 8 (findings 1, 2, 4, 5, 6 and section 3). No model or API was called, no generated benchmark program was executed, no git command was run, nothing under `experiments/tau2_open/` or `results/tau2_open/` was written (one read-only grep of `results/tau2_open/report_final.md`). Files written by this verification: this file and `reviews/local_stream_round10_verify.py`. **No wording fix was applied to any repair file** (none was needed).

**Verdict: PASS on all six items**, with the notes in section 7 for the coordinator.

## 1. Endpoint normalization (finding 4): PASS

- `src/wincs.py` adds `_count_log1p` (term exactly 0 when count is 0); used by `betting_log_capital_ternary` and `betting_log_capital_bernoulli`.
- Independently evaluated with the default stakes: `exp(betting_log_capital_ternary(0,0,0,1))`, `(5,0,0,1)`, `(0,0,5,-1)`, `(0,0,0,-1)` all `== 1.0` exactly; Bernoulli `(k,n,q)` = `(0,0,0)`, `(0,0,1)`, `(5,5,1)`, `(0,5,0)` all `== 1.0` exactly. Wrong-endpoint cases grow as they should (`(5,0,0,-1)` -> 1.921).
- The Round 9 file preserved in `v2_pre_round10/wincs_v2_pre_endpoint_fix.py.txt` returns 0.9875 for the same calls, so the new test discriminates.
- Full `src/test_wincs.py`: all stages pass, including `round 10 endpoint tests passed` (about 40 s).
- Interior CS unchanged: recomputed from the last row of `monitor_pass1.csv` (69 wins / 18 ties / 208 losses; success +67 / -52): NB CS [-0.6281037, -0.2879839], success-difference CS [-0.0786118, 0.1793977], decided-pair WR CS [0.2010018, 0.5299129]; R1 radius 0.1828387 -> [-0.65403, -0.28835]. These equal `summary_v2.json` / `summary_v3.json`. Old versus new `wincs` over the whole 295-step running path: maximum endpoint difference 0.0. `v2_vs_v3_numeric_check.json`: 482 numeric leaves, max abs diff 0, four CSVs byte-identical.

## 2. E2 dependence and CLT (findings 1, 2): PASS

Own code (`reviews/local_stream_round10_verify.py`; scores rebuilt from `episodes.jsonl` with an independent implementation of the frozen hierarchy: success, then latency and completion tokens at 10% relative tolerance, lower tiers only when both succeeded; clusters from `design.json` `pair_index`):

| quantity | mine | repair (`summary_v3.json`) |
|---|---|---|
| clusters | 296 (295 of size 2 + singleton `mbpp/256`), 591 tasks | 296 |
| NB: sum of cluster totals / estimate | -388 / -0.6565143824 | -0.6565143824 |
| NB cluster totals distribution | -2: 153, -1: 96, 0: 34, 1: 12, 2: 1 | same multiset as `e2_cluster_v3.csv` |
| NB task-level SE | 0.0248470280 | 0.0248470280 |
| NB linearized cluster-robust SE (G/(G-1)) | 0.0248769589 | 0.0248769589 |
| NB cluster t (295 df) | [-0.7054732, -0.6075556] | same |
| cluster Hoeffding radius sqrt(2(4*295+1) log 40)/591 | 0.1579427508 | 0.15794 (audit value) |
| NB cluster Hoeffding | [-0.8144571, -0.4985716] | same |
| success diff: estimate / totals | 0.0 / -2: 1, -1: 35, 0: 224, 1: 35, 2: 1 | same |
| success cluster-robust SE / t | 0.0149690648 / [-0.0294597, 0.0294597] | same |
| success cluster Hoeffding | [-0.1579428, 0.1579428] | same |
| task-level Hoeffding radius | 0.1117297 | same |

Wording: `report_v3.md` section 4 and `protocol_addendum_round10.md` section 4 label the task-level t and Hoeffding intervals MODEL-BASED with the assumptions stated (independent task scores, stable task-specific episode laws, no relevant pass/period effects; Lindeberg / variance-growth condition and "approximate" for the t interval); both contain the audit's two-task counterexample, the extra covariance term, and the Bernoulli(1/N) example with probability 0.367568; "independent clusters is still an assumption" is stated; the -0.03 margin is reported as not certified by any interval; the decision-rule table rows carry the model-based label. Grep of `report_v3.md`, the addendum, `PR8_BODY_round10.md`, `report.md`, `summary_v3.json`, `decision_rules_v3.csv` for "assumption-free", "automatically conservative", "therefore independent", "no assumption", "by construction", "design-based": every hit is inside a withdrawal statement (or the Figure 2 legend disclaimer); no live claim.

## 3. R1/R2 wording (section 3 of the audit): PASS

R1: filtration defined (`F_k` = design information independent of future outcomes + revealed pair data up to k; `F_0` contains no outcome), target = running conditional mean, no running intersection, pair-mean formula and `theta_N` link only under an added orientation- and history-independent stable episode-law model, "therefore independent" sentence withdrawn, rho fixed after outcomes (post hoc), and "not a joint 95% region" present in the addendum, report (Round 10 item 5 and table caption), summary JSON and PR body. R2: unconditional model-based inference over hypothetical iid rosters with independent stable episode laws, filtration explicitly excludes the entire realized roster, not conditional on the curated benchmark. E-process crossings descriptive under R1; root theorem not imported. Superseded Round 9 sentences tabulated (addendum section 6). The report also discloses that the harm process was above threshold at pair 14 inside the n < 20 blackout.

## 4. Anonymized copies (finding 5): PASS

All 14 originals and 14 anonymized copies listed in `release_anon/MAPPING.json` exist in the working tree; every recorded original and anonymized sha256 matches. The sanitized data manifest is at `results/local_stream/release_anon/local_data_manifest.anon.json` (sha256 `5f28f427...e54c0`, the audit's value), not under the `work/` ignore rule (checked by reading `.gitignore`); its git-ignored original is marked as such. Portability disclaimer present in JSON and MD. Own scan of the 17 files under `release_anon/` (including the stale ignored `work/` copy) for `/Users/`, account name, host name, `/home/<x>`, e-mail patterns, name fragments, institution: no hit except the indicator string `/Users/` inside `MAPPING.json -> identifier_scan` itself. Generic `/private/tmp` literals of the sandbox profile remain and are not identifiers.

## 5. PR body (finding 6): PASS

`PR8_BODY_round10.md`: the uncorrected CS [-0.618, -0.301], "before any outcome", "every fixed-horizon rule agrees" and the causal E1/E2 explanation occur only in the one sentence that withdraws them. It points to `report_v3.md`, says "before design-task outcomes", quotes R1/R2/E2 intervals with assumption labels, states E1 versus E2 is descriptive with no causal mechanism, and the numbers match `summary_v3.json` and `resources_v2.csv` (2.96x calls, 7.42x prompt tokens, 4.46x completion tokens, 4.46x mean latency). tau2 section: 196 units, 15/98 per arm, abstention, Deviation 1 cross-checked read-only against `results/tau2_open/report_final.md`; batch-plus-replay wording present.

## 6. Evidence integrity and preservation: PASS

- The six raw evidence files have the sha256 recorded in the Round 9 `analysis_v2_manifest.json` (`raw_evidence_sha256`): episodes `95179f93...`, monitor CSV `67504351...`, monitor state `daeca326...`, run manifest `f2efc949...`, design `6175b815...`, design.sha256 `f50b77f3...`.
- Frozen files: the 8 hashes in the Round 9 manifest and the 11 in `analysis_v3_manifest.json` (adds `agent.py`, `sandbox.py`, `verify.py`; modification times 2026-09-18 10:41-10:53, before the run) all match. The 8 Round 9 script hashes are unchanged.
- `v2_pre_round10/`: all 14 `outputs_sha256` entries of the Round 9 manifest match the backup copies; all 22 hashes in its README match; the manifest copy is identical. `report_v2.md` at top level = 321-byte SUPERSEDED banner + the original bytes. `v1_pre_round9/`: all 10 recorded hashes match.
- `analysis_v3_manifest.json`: all 81 recorded hashes match the files on disk; six steps with return code 0.

## 7. Notes for the coordinator (not failures)

1. Git status could not be checked here (no git commands). Confirm on commit that `release_anon/local_data_manifest.anon.json` is tracked, and whether the dry-run originals `results/local_stream/dryrun/{run_manifest.json,episodes.jsonl}` (present on disk, absent from the audited Git snapshot) are tracked; if not, MAPPING should mark them as unavailable originals.
2. `src/wincs.py` is shared with tau2. The change only affects capitals at zero counts with endpoint candidate means and was conservative before; tau2 outputs were not regenerated here. `results/tau2_open/report_final.md` line 330 calls Deviation 1 "outcome-blind", which the audit (section 5) qualifies; that file belongs to the other agent.
3. `figures_v2` legends still say "design-based" / "task-level CI"; `report_v3.md` re-captions them. Acceptable, cosmetic.
4. `experiments/local_stream/README.md` still contains two absolute-path lines (originals are identifiable by design; the anonymized copy is clean).
5. `tests_local_stream.py` was not run by the repair or by me (it may exercise the sandbox).

## Reproducers

```text
.venv/bin/python src/test_wincs.py
.venv/bin/python reviews/local_stream_round10_verify.py
.venv/bin/python -c "import sys,math;sys.path.insert(0,'src');import wincs as w;print([math.exp(w.betting_log_capital_ternary(*a)) for a in [(0,0,0,1),(5,0,0,1),(0,0,5,-1)]],[math.exp(w.betting_log_capital_bernoulli(*a)) for a in [(0,0,0),(0,0,1),(5,5,1),(0,5,0)]])"
grep -n -i "assumption-free\|automatically conservative\|therefore independent" results/local_stream/report_v3.md experiments/local_stream/protocol_addendum_round10.md
shasum -a 256 results/local_stream/{episodes.jsonl,monitor_pass1.csv,monitor_state.json,run_manifest.json,design.json,design.sha256}
```
