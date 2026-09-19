# Round 13 report-correction provenance audit

**PASS on preservation, declared hashes, exact report regeneration, the five applied fixes, and the newly computed numbers.** No correction found here requires changing the retained main-paper numbers or numerical archive contents. The residual notes below concern the excluded owner reports and their documentation. This is an AI review, not human peer review; inferential interpretation is assessed separately by the theory reviewer.

Frozen head: `01f2381940fcf5bc57129f1498382cb40f3ea741` (`origin/review-pr8` as fetched by root). Baseline: `04989e88efd548e4f40a12366b6534a5aad18ed8`. Read-only Git inspection and all generator execution were confined to extraction/reproduction in outer `work/round13_report_provenance/`; only that scratch and this report were written. No model calls, full analyses, benchmark programs, simulations, source edits or Git mutations were performed.

## Preservation and exact reproduction

The intervening merge `60f0a5ec10e36590fc601f24530d10cf3beaa1c0` has parents `04989e8` and root release `45e8ee2715f148c81db7f6510d66677f57e03f0a`. After separating that merge, the correction commit adds nine files and modifies only `results/SESSION60_RESULTS_INDEX.md`. All **221 pre-existing files** under `experiments/{local_stream,tau2_open}/` and `results/{local_stream,tau2_open}/` retain identical Git blob identities against `04989e8`. That includes **107 raw/log/CSV/JSON-class files**, as well as the original reports, earlier addenda, figures and analysis code. No raw outcome or computed table was silently replaced.

Both generators were read before execution. They use only standard-library local text/JSON/hash operations and small scalar arithmetic, resolve paths under their own extracted repository, and write only their new report and manifest. Running them in scratch reproduces **both reports and both manifests byte-for-byte**. Every extracted input and referenced figure remains byte-identical afterward.

Independent static evaluation of the declared replacement expressions verifies every old/new passage digest and match count: the coding generator has **12 replacement entries, covering 13 occurrences**; the airline generator has **15 entries, covering 15 occurrences**, followed by six separately implemented section-status insertions and a banner/status section. All manifest source/output hashes, the airline numeric-input hash, and the two coding figure hashes match actual frozen bytes. Figure 2 now embeds the pre-existing `figures_v3` file, with a caption describing both orange bands; neither figure file was regenerated.

## The five required fixes are present

These checks apply to the final committed reports, after the owner disposition appended to `reviews/session60_round12_report_corrections_verification.md:157`.

| Required fix | Verified final location and result |
|---|---|
| Resource-significance residuals | Airline `report_final_v2.md:261` says descriptive canonical observations and no significance claim. The two component interval cells are no longer emphasized; component/sensitivity wording points to model-dependent status. |
| Method-independent impossibility | Airline `:42` restricts the conclusion to the specified rule, intervals and data. Both additional prohibited phrases are absent from the report and present in the generator's banned-phrase checks. |
| Local status and checklist | Status pointers appear at airline `:79,101,144,204,255,315`, covering all six required sections. The section-0 locations include infrastructure exclusion in §7.2; checklist rows `:329,350` do not count excluded uncertainty as established. The run-manifest row separates manifest preservation from unverified decision chronology. |
| Unsupported conservative-t statement | Airline `:75` explicitly withdraws it and adds variance/nondegeneracy, Lindeberg/no-dominant-task and consistent-variance-estimator conditions. Airline Round 12 addendum `:61` records the withdrawal. |
| Coding sentence boundary | Coding `report_v4.md:52` correctly ends the conditional/unconditional distinction before “Thermal state…”. |

The corrections do not retroactively validate the excluded model-dependent intervals. The final reports and addenda explicitly retain that exclusion. Whether the remaining inferential formulations are sufficient is the separate theory review's scope.

## Independent numerical checks

Exact rational accumulation of the 49 frozen orientation rows, without importing either generator or contributed inference, gives:

| Quantity | Net benefit | Success difference |
|---|---:|---:|
| Observed mean | 1/49 | 1/49 |
| Complete-array orientation target | 1/98 | 0 |
| Final absolute error | 1/98 = 0.0102040816 | 1/49 = 0.0204081633 |
| Largest path error | 3/8, uniquely at n=4 | 3/8, uniquely at n=4 |

The recorded orientation selects the observed score in all 49 rows. Both target paths lie inside their respective displayed bands at every prefix. The independently calculated final radius is `0.6297318533794021`, agreeing with the stored value to the last floating-point digit. These checks establish the recorded arithmetic, not empirical calibration or joint 95% coverage.

Using 60-digit decimal arithmetic, the cluster counterexample probability is

```
(295/296)^296 = 0.367257146972302209855640143448493949082933468096655195758833
```

It rounds to the reports' `0.367257147`; the stored binary-float constant differs only by about `2.3e-15`. The reported target is `1/296`, since 295 clusters of size two and one singleton sum to 591 observations. The all-zero event makes the estimated mean and t width zero and misses that positive target. This is a counterexample, not a fitted explanation of the observed coding data.

The new same-task counts `28/141/27` agree with the frozen airline summary's proportions times 196. The reward-provenance counts `124/70/2` agree with the already independently audited unchanged raw array: 55+69 user stops, 27+14+29 termination-based zero records, and two missing rewards. The token lower bound independently recomputes as

```
198,280 + (16,444 - 2 - 15,014) + (448,226 - 2 - 401,648)
= 198,280 + 48,004
= 246,284.
```

The original log reconstruction and A-collection attribution are documented in the Round 12 evidence/integration reviews; those logs were not re-parsed here. The number is still an incomplete generated-token lower bound without an agent/user partition.

## Residual owner-document provenance notes

1. **P3 — stale replacement summary.** Airline `report_final_v2.md:9` and its generator banner still say “three passages replaced.” There are now 15 declared replacements plus six local status pointers. The same banner says the manifest contains “the replaced passages,” but it contains their hashes; the generator contains their text. A future owner-report version should say “the listed wording replacements and status pointers” and “passage hashes; exact text in the generator.” Output reproducibility is unaffected.
2. **P3 — supersession pointers.** Airline `report_final_v2.md:3` still lists Round 10 first “in order of precedence”; coding `report_v4.md:52` ends with a Round-10-only Definitions pointer. Both new banners/addenda explicitly state Round 12 governs, but these local pointers should name the current addendum to avoid directing readers to withdrawn wording.
3. **Historical verification is not a current checksum certificate.** The prior verification report's `:71,73` output hashes and its initial diff counts describe the pre-disposition versions. Its final paragraph `:179` expressly says the later edits were not independently re-verified. Preserve that chronology; cite this Round 13 audit for validation of the committed hashes and applied fixes rather than treating the older table as current. The final manifests themselves are correct.
4. **P3 — token-role precision.** The owner report/addendum's “generated arm-A tokens” is less clear than root's “A-collection generated tokens; role partition unavailable.” The arithmetic includes agent and user-simulator work. Retain the root wording when communicating this quantity.

These are owner-only corrections or provenance clarifications. They do not justify importing the excluded intervals, replacing the root analysis, or rerunning models. The accepted root paper already uses the direct observations, properly scoped conditional-mean/observed-array constructions, and explicit resource/chronology limitations. No numerical paper or scientific-archive rebuild is indicated by this audit; root separately decides whether to add the new audit/disposition to its release records.

## Exact audited identities

| Object | SHA-256 |
|---|---|
| Coding generator `make_report_v4.py` | `fc02697dc3a36eb250196279851be3bc1738ce6438567d6a1ec01c9b6215a49e` |
| Airline generator `make_report_final_v2.py` | `4d40c81ec15cda9aacb0ff34f859d96c6995519c53bda9beb9f038af061cbbfc` |
| Coding source `report_v3.md` | `0a534fd6bacf10e1e28e01e0aa06f57966cb0f6aa5b0d1fdcc2fa07e11a8e378` |
| Coding output `report_v4.md` | `806d82ce35d55d9c573b806575d3d4176ffbb4e89cbe9d8d2281d92d80ae59bd` |
| Coding manifest | `dbbe51f6acbf1b58d38fb6007cdba4356413707049a6d8ce59c2749a3a3272fe` |
| Airline source `report_final.md` | `1ae93f5bff68d57eb879c37fb5069b3fc6595c41e18fdce209ec7e1eb86505d0` |
| Airline output `report_final_v2.md` | `11f5691e54ac2603e229a10524685b69d91035620d20fe8748e500efc257b3cc` |
| Airline manifest | `1d58fb59e1c68c59431a4d29b2896bf1850c2d1011c2792bd42e687c9517a53c` |
| Airline numeric input `round10_handoff_numbers.json` | `a6937828fbf82aabbacda3863f18dd3c0111aa786a9b3448f3282d8739754124` |

Scratch records: `snapshot_hashes.json`, `reproduction_and_preservation.json`, `verify_corrections.py`, and `independent_correction_checks.json` under outer `work/round13_report_provenance/`. The exact generator reproduction used the selected frozen snapshot under that scratch; no source or output in the working repository was modified.
