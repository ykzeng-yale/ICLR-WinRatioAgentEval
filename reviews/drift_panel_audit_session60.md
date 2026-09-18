# Drift / unequal-law-null panel: independent audit (session 60)

Date 2026-09-18. Auditor did not write the panel. Scope: `experiments/drift_panel/{protocol.md,run_drift_panel.py,README.md,make_figures.py}`, `results/drift_panel/*`, `evidence/drift_panel_report.md`. No git commands, no model/API calls, tau2_open files and processes untouched. At most 4 worker processes used. Every number below comes from a file read or a computation run in this audit (audit scripts kept in the session scratchpad, not in the tree).

Overall: **PASS** (13 of 13 items), one wording fix applied to the report; no cell needed re-running for correction.

| # | item | verdict |
|---|---|---|
| 1 | Protocol hash recorded before results; manifest hashes/timestamps consistent | PASS |
| 2 | Unequal-law nulls C1/C2 have net benefit exactly 0 (analytic + 1e6 MC) | PASS |
| 3 | Boundary nulls A1-A3 sit exactly at thresholds at every step | PASS |
| 4 | B3a/B3b: different components below margin at different times; every look violated; no gate violated at all looks | PASS |
| 5 | Running-average targets in the error event come from true conditional means, not data | PASS |
| 6 | Reuse of `src/winstats.py`; conventions match `experiments/run_simulations.py` | PASS |
| 7 | Error events match `paper/theory.tex` (thm iut, thm drift_gate) | PASS |
| 8 | Wilson intervals | PASS |
| 9 | Deterministic seeds (exact re-run) | PASS |
| 10 | Report numbers match result files | PASS |
| 11 | Guarantees separated from observations | PASS |
| 12 | No "holds level" claim from an interval containing 0.05 | PASS |
| 13 | Deviations disclosed | PASS (one wording fix, see below) |

## 1. Protocol hash and timeline: PASS
- `shasum -a 256 protocol.md` = `bb497cbb7c58fd1578530748c9d5ef834dc079e8b14973bc0bee348ca5c276cc` = `manifest.protocol_sha256` = first line of `run.log` = README. Runner sha256 `1bc0a113...3a41` and `src/winstats.py` sha256 `3053f8a1...7fd9` equal `manifest.source_sha256` / `core_sha256`.
- File times (macOS birth/modify): protocol.md modified 16:16:40; `results/drift_panel/` and `run.log` born 16:17:01; `results.csv` born 16:17:47, `manifest.json` born 16:17:54; runner last modified 16:18:25; `run.log` content starts 16:18:26 and ends 16:19:19 (53.3 s, equals manifest `seconds`). So there was a first full run 16:17:01-16:17:54 after the protocol freeze, a runner edit, and a rerun. This is exactly what the report's Deviation 1 discloses (E_current_first bug for win-only rules; rerun with identical seeds). The protocol predates both runs. The first run's outputs are not retained, so the builder's "only E_current_first columns changed" statement cannot be re-verified; it is immaterial because the current runner reproduces the current results exactly (item 9).
- `--design-check` path (`build_scenarios`, `design_summary`) contains no RNG call; confirmed by reading.
- The runner exits on hash mismatch for non-smoke runs (lines 310-313); smoke runs use seed 20260920 and cannot write into `results/`.

## 2. Unequal-law nulls, exact theta = 0: PASS
Independent recomputation (own code): resource preference by `scipy.integrate.quad` over the lognormal cost law instead of the runner's closed form, and net benefit by enumerating the hierarchy as P(win)-P(loss).
- C1: pA = 0.8232694453707727; resource pref quad -0.11866717670554977 vs code -0.11866717670554999; net benefit 1.1e-16 (runner's step target -2.8e-17, constant over all 10,000 steps).
- C2: pA = 0.10291732834706396; resource pref quad -0.2834704380658979 vs code -0.28347043806589795; net benefit -1.3e-17 (runner 0.0).
Independent 1e6-draw Monte Carlo (own seeds, own scoring with explicit lognormal costs, r applied multiplicatively): C1 nb = -0.000818, SE 0.000958, z = -0.85, tie prob 0.0824; C2 nb = -0.000583, SE 0.000441, z = -1.32, tie prob 0.8059. `winstats.compare` with the eligibility mask gave element-wise identical scores to the own scoring on all 1e6 draws in both cells. Builder's manifest values (C1 MC 5.6e-05, SE 0.00096, p_tie 0.0825) are consistent. Laws are genuinely unequal (success difference +0.0733 in C1; cost ratio 1.10 / 1.50).

## 3. Boundary nulls at every step: PASS
Step-target min/max over all 10,000 steps: A1 all three gates (0, 0). A2 success gate (-0.030000000000000027, same), max |step - threshold| = 2.8e-17; net benefit 0.177 to 0.618, compliance 0. A3 compliance gate (-0.010000000000000009, same), max deviation 8.7e-18; net benefit 0.206 to 0.654, success 0. All 199 looks flagged violated in A1, A2, A3, C1, C2; `fixed_gate_conditional_null_every_step` True exactly for those five cells. The 1e-9 tolerance only absorbs these 1e-17-scale errors.

## 4. Alternating / cycling violators: PASS
Recomputed running targets and violation sets from the scenario parameters:
- B3a: net benefit violated at looks 100-2000 (39 looks), success 100-4000 (79), compliance 4000-10000 (121); every look violated: True; any gate violated at all looks: False. Current (per-step) violators by block: steps 1-2000 {net benefit, success}, 2001-4000 {success, compliance}, 4001-10000 {compliance}.
- B3b: net benefit 100-500 and 8000-10000 (50 looks), success 100-1000 (19), compliance 1000-8000 (141); every look violated: True; no gate at all looks. Current violators: 1-500 {nb, success}, 501-1000 {success, compliance}, 1001-5000 {compliance}, 5001-8000 {nb, compliance}, 8001-10000 {nb}.
- B1: nb violated iff n >= 6000 (81 looks); B2: iff n <= 6000 (119 looks); other gates never.
Boundary tightness: at violated looks the running target exceeds its threshold by at most 1.4e-14 (floating point); at non-violated looks the smallest margin is 5.6e-4 (B3b compliance). The 1e-9 tolerance therefore classifies every look unambiguously. Bisection-solved cost ratios stay in [0.418, 2.123]; requested net-benefit paths reproduced to 0.0 difference against hierarchy enumeration.

## 5. Targets from true conditional means: PASS
`sc['step'] = exact_targets(parameters)`, `sc['running'] = cumsum(step)/t`, `viol_gate = running[:, LOOKS-1] <= c + 1e-9` are computed once in `build_scenarios` from the deterministic parameter paths; `run_chunk` only indexes these fixed boolean arrays with the data-dependent deployment masks. No sample quantity enters the error event. Pairs are independent with deterministic parameters, so conditional mean = per-step mean. Win-only rules are scored against the net-benefit gate only, as the protocol states.

## 6. winstats reuse and run_simulations conventions: PASS
- `betting_log_e_ternary(pos, neg, LOOKS, c)` with default 40 bets against log(1/alpha) (log(3/alpha) for split); `normal_mixture_radius(LOOKS, alpha)` with default rho = 100, V = n; lower bound `m - radius > c`. Radius at n = 10,000: 0.032730 (alpha), 0.035961 (alpha/3), matching the protocol's 0.0327 / 0.0360.
- Thresholds (0, -0.03, -0.01), alpha 0.05, looks `unique(r_[arange(100, N+1, 50), N, arange(1,11)*N/10])` = 199 looks, same-look conjunction via `logical_and.reduce`, Wald variance `(pos+neg-n m^2)/(n-1)`, group mask and alpha/10, fixed-horizon rule at the last look only: all identical to `run_simulations.py`.
- Score construction identical (compliance, then success on compliance ties incl. both noncompliant, cost only if both compliant and both successful and beyond relative tolerance). The log-scale cost comparison `|la-lb| > -log(1-tol)` is algebraically the same as `|cA-cB| > tol*max(cA,cB)`; the closed-form resource preference equals the one in `run_simulations.exact_targets`.
- Target verification uses `winstats.compare` with `Tier(..., higher_better=False, relative_tolerance=tol)` and an eligibility mask; max |z| = 2.34 over 132 comparisons in the manifest.

## 7. Error events vs theory.tex: PASS
- thm drift_gate event: "exists n: rule deploys at n and some running mean_jn <= c_j". Code `e_any = (d & v[None,:]).any(axis=1)` is this event over the 199 looks (monitoring without stopping); `e_first` is its restriction to tau and is a subset (checked: first <= any <= deploy in all 108 rows).
- thm iut / fixed-index clause: in A1-A3, C1, C2 every look is violated, so false deployment = ever-deploy; checked in the CSV that ever_deploy = E_running_any = E_running_first for all guarded rules in those cells (and for win-only rules in A1, C1, C2).
- The report correctly notes that thm iut is stated for constant means of all scores while A2/A3 have drifting net benefit, and cites the proof argument (thm betting on gate j*, thm drift_gate fixed-index clause) rather than the statement. Guarantee table entries (0.05, 0.0167, union bound 0.15 for per-gate CS in B3, none for betting in B, none for Wald) are consistent with the theorems. The betting-under-running-average remark is labelled as not a paper claim.

## 8. Wilson intervals: PASS
Independent closed-form Wilson for all 108 rows x 4 events plus 9 permutation rows: max absolute discrepancy in rate/lo/hi = 2.2e-16.

## 9. Determinism: PASS
Re-ran complete cells by calling `run_chunk` with 3 workers (builder used 5): A6_strong_all_gates (2,000 reps), B3b_cycling_violator (10,000), C2_unequal_law_null_tie_heavy (10,000). All 9 rules x {ever_deploy, E_running_first, E_running_any, E_current_first counts, mean_pairs_used} match `results.csv` exactly. Permutation cell C1 re-run with 4 workers: (2000, 1886, 1538, 1795), identical to `permutation_results.csv`. Seeds are per (scenario, chunk), so worker count cannot matter; seed namespaces [k], [8000+k], [9000+k] do not collide (12 scenarios, 3 perm cells, 44 verification sets; at most 20 of 40 spawned children used).

## 10. Report vs files: PASS
All 79 "rate [lo, hi]" triples in the report match a row of `results.csv` or `permutation_results.csv` at 4 decimals. Power-table means/MCSEs, B1/B2 mean pairs (283-1484; 7395-7586; repeated Wald 6685, 462/10,000 first deployments at a violated look) and C-cell constants match.

## 11-12. Guarantee vs observation; level language: PASS
Separate "guaranteed" column in every table; text states which rows are guaranteed and that the rest is observed. The seven intervals containing 0.05 (fixed Wald A1 0.0486, A2 0.0508, A3 0.0510, B3a 0.0495, C1 0.0520, C2 0.0508; repeated Wald B1 0.0470, B2 0.0462) are each described as "not resolved" / "no level claim". "Below 0.05" is used only where the upper limit is below 0.05. The report explicitly states the panel does not demonstrate the alpha split is necessary (CS rules made zero deployments in B3).

## 13. Deviations and fix applied
Deviations 1-4 in the report are consistent with the file timeline (item 1). One mechanical wording fix applied to `evidence/drift_panel_report.md`: the B1 bullet said "every sequential rule deploys ... at mean 283 to 1484 pairs", but that range covers only the betting and normal-mixture rules; repeated Wald deploys at mean 145 and group Bonferroni Wald at 1000 (`results.csv`). The sentence now says so. No code, protocol, result or manifest file was changed, so no hash is affected and no cell was re-run for correction.

## Residual notes (not failures)
- The first full run's outputs were overwritten; only the rerun is auditable. E_current_first is descriptive, so this has no bearing on any guarantee-related number.
- The panel cannot discriminate per-gate vs split CS rules on error (zero deployments in B3) and says so.
- The permutation contrast permutes arm labels over 1,000 unpaired executions; C0 calibration 0.0429 [0.0391, 0.0471].
