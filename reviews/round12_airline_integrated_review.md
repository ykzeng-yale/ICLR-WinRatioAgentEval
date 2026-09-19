# Round 12 airline root-integration review

**Verdict: PASS for the explicitly descriptive airline integration and the conditional observed-array replay illustration.** Independent reconstruction agrees with every retained metric, attempt/policy projection, comparison and band. No numerical or inferential integration blocker was found. This verdict does not certify production A/B evidence, model superiority, an operational resource advantage, the complete submission package, or acceptance by a venue.

This is an AI review, not human peer review. The reviewer did not collect the airline data or write the root airline builder. The scope is the new root builder and outputs, three airline TeX files, shortened coding paragraph, and their frozen source at `55fb1e51234ad712c56799455bd704b829ed1d26`. The separate source/log and inference reviews are `reviews/round12_airline_evidence_review.md` and `reviews/round12_airline_inference_review.md`. Only this report and outer `work/round12_airline_integrated/` were written; no models, benchmark programs, contributed inference, heavy simulation, or Git mutations were executed.

## Independent reconstruction

The standard-library checker in outer `work/round12_airline_integrated/independent_check.py` reads the two frozen compressed raw arrays directly. It does not import the root builder, the project core, or the contributed analysis. It separately implements the hierarchy, uses exact integer arithmetic for the 5% larger-value token tolerance, and calculates the normal-mixture radius using scalar logarithms. `independent_check.json` records the passing results.

| Check | Independently verified result |
|---|---|
| Canonical metrics | All 196 complete projected rows equal the raw-derived fields, in the declared sorted arm/task/trial order; all expected keys appear exactly once. |
| Raw outcome provenance | 124 user-stop records have reward bases; 70 saved max-step/error trajectories have zero reward without a basis; two infrastructure placeholders have missing reward and count as unsuccessful. |
| Response usage | Every saved assistant/user prompt and completion count and assistant tool-call count agrees; no other role has ignored recorded usage. Combined recorded model responses are 4,205 A and 4,075 B. |
| Attempt projection | All 206 rows and all declared fields agree with the frozen ledger, preserving its order. There are 194 retained trajectory-producing attempts plus 12 discarded attempts. |
| Regime projection | All 196 rows and declared fields agree with the frozen flags. Five A units precede the amendment; 191 canonical records belong to the amended invocation, including two placeholders. |
| Retention/retries | All 30 retained successes come from single-attempt units. The retained A/15/0 retry has reward zero. The two empty placeholders remain in the denominator. |
| Replay | All 49 rows, both alternative orientation scores, realized signs, decisive tiers, success differences, and orientation means agree. The realized assignment agrees with the design's pass-one arm labels. |
| Same-task comparisons | All 196 four-trial-combination rows agree, including signs, decisive tiers and success differences. |
| Running bands | All 49 scalar radii, observed means, known array means and clipped endpoints agree to floating-point precision. All known array targets lie within the displayed bands on this path; this is not a repeated-sampling calibration estimate. |

The principal output values are:

| Quantity | A | B |
|---|---:|---:|
| Canonical units / successes | 98 / 15 | 98 / 15 |
| Saved trajectories / logged attempts | 96 / 108 | 98 / 98 |
| Discarded attempts | 12 | 0 |
| Agent prompt tokens in saved messages | 20,412,368 | 19,138,768 |
| Agent completion tokens in saved messages | 248,996 | 223,345 |
| User prompt tokens in saved messages | 4,373,819 | 5,915,658 |
| User completion tokens in saved messages | 85,101 | 82,565 |
| Assistant tool calls | 979 | 520 |

The 49 replay pairs give **10 B wins, 30 ties and 9 losses**, NB `1/49 = 0.0204081633`; every realized non-tie resolves at success. The 196 dependent same-task comparisons give **28 wins, 141 ties and 27 losses**, NB `1/196 = 0.0051020408`. The same-trial subset gives `13/73/12`, NB `1/98`; the different-trial subset gives `15/68/15`, NB zero. The generated table and summary reproduce these counts and the resource totals without changing denominators.

At 49 pairs, the observed mean is `0.0204081633`, the exact array orientation-average target is `0.0102040816`, and the radius is `0.6297318534`. The band is `[-0.6093236901, 0.6501400166]`. The scalar reconstruction differs from the stored vectorized radius/endpoints only at the last floating-point digit.

## Resource accounting and provenance

The omitted-usage arithmetic is correct:

```
16,444 - 2 - 15,014 = 1,428
448,226 - 2 - 401,648 = 46,576
1,428 + 46,576 = 48,004
48,004 + 198,280 = 246,284
```

The canonical subtractions were independently rebuilt from raw role-specific completions: the first five A units contribute 15,014; the second A/user-server session contributes 401,648 after including remaining A agent/user messages and B user-simulator messages. These agree exactly with the source counters. The separate evidence review independently parses original server logs and supports both the A-collection attribution and cancellation/completion accounting; this integration review does not claim to have independently repeated that log parser. The 246,284 quantity remains a **partial lower bound on omitted generated tokens**, with unknown agent/user partition and incomplete prompt/resource accounting. It is not the total failed-attempt cost or a basis for an operational efficiency claim.

The sanitized configuration preserves the original values and model identities/hashes, apart from declared path removal and explicit role/amendment summaries. Both retained runner snapshots match their corresponding invocation-manifest hashes exactly. The five pre-amendment raw trajectories have maximum single-response completion lengths of 85, 514, 179, 120 and 308 tokens, and durations below 433 seconds. Thus their realized paths did not reach the later limits; this does not establish counterfactual invariance under amended settings. No weight files were downloaded or independently hashed here.

## Manuscript scope and remaining limits

`paper/open_airline_results.tex` and `paper/open_airline_appendix.tex` faithfully distinguish all-A-then-all-B collection from the prescribed replay. They disclose repeated trial seeds, the mixed amendment history, missing rewards, termination-based zero rewards, canonical versus discarded work, and the different serving arrangements. Equal 15/98 observed successes is expressly not equivalence or noninferiority. All 196 units remain, including infrastructure failures and pre-amendment records; no favorable subset or independent-comparison denominator is substituted.

The optional illustration in `paper/open_airline_appendix.tex` conditions on the complete array and fixed matching, models independent fair orientation coins, excludes future coins from the pre-pair filtration, and requires collection/amendment/retention independent of those coins. It displays the already-known target next to the band and states the post-hoc, unadjusted scope. This is consistent with the separate inference audit. It imports no task-t, independent-arm Welch, fixed-mean betting, win-ratio or other model/population interval, and makes no live-stopping or deployment claim. Different tasks/trials and an already observed full array do not become new independent sampling units through replay.

The shortened `paper/open_coding_results.tex` preserves the accepted coding numbers and scope: 591 tasks per arm, 433 successes per arm, resource ratios rounded to 4.46 and 6.33, 295 first-pass pairs with 69/18/208 signs, NB −0.471 and the post-hoc running-history-conditional-mean band [−0.654, −0.288]. It retains the uncertified success guardrail and points to the detailed appendix. It does not convert that band to full-roster or fresh-model inference.

Two minor precision corrections were sent to root and are resolved in the final files: success is described as derived from raw reward fields, with missing reward mapped to unsuccessful, while message usage/tool counts come from messages; role-specific token counts are explicitly limited to saved messages. Neither affects numerical results. Final source/hash status is recorded below.

This bounded integration adds fresh open-weight interactive benchmark observations. It does not resolve the broader empirical gap between batch/replay studies and prospectively randomized continuous deployment, nor does it prove a general benefit of the hierarchy when only five same-task comparisons resolve at resource tiers. Those are honest scope limits, not reasons to run more models for the present descriptive claims. No additional experiment is required to repair the retained integration.

## Audit identifiers and final verification

- Independent checker SHA-256: `71a0679658386704220414c6c78e7e6da3c934a996a6e299ba2299e5d80d5520`.
- Raw uncompressed A: `887c66a23c2c1c2188279ce658efb15436648a9e26251b62f569521df4845fd8`.
- Raw uncompressed B: `39a49567936fb14f5444ae6e406c43abd1cfbb21198540c8b8df585d8fa1c8f6`.
- Pre-amendment runner: `215e943a371a778900033586a28cd00b7e0f49f77966354ff3d2b6913c1c06ee`.
- Amended runner: `27797f68e2aff6e088d0300f4be9baac903ef34b71ec84116125c2fa664ff75c`.

Use from the outer workspace (with no model execution):

```
python3 work/round12_airline_integrated/independent_check.py \
  --repo outputs/agent_win_eval \
  --source outputs/agent_win_eval/work/round12_airline_source \
  --output work/round12_airline_integrated/independent_check.json
```

The final checkpoint verified all 13 integrity-listed output hashes, the builder/core hashes, all seven historical-source hashes, both invocation runner identities, all six projection hashes and all ten frozen source-file hashes. Ten checked numerical files remain byte-identical after the wording changes. `work/round12_airline_integrated/final_hash_checkpoint.json` records the exact current files. I also reread the shortened final appendix paragraphs: the coin model, known target, post-hoc limitation, and no-stopping/no-production scope remain intact.

| Final root object | SHA-256 |
|---|---|
| `experiments/build_open_airline_results.py` | `7a39748fe14c42aa3d7e614bfb6f67cac1ed6453d5774452467897018a9057fd` |
| `src/winstats.py` | `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` |
| `results/open_airline_integrity.json` | `6cb519e16af338dddd60ad8e4676615104fc01d0d337df2dff91cc46782fb220` |
| `results/open_airline/provenance.json` | `45be7c0d5332d6bba38572adb74e0bf55b78fccc08fc357cfa8774ad800df7c1` |
| `paper/open_airline_results.tex` | `8e2bd718cc6b51093bae5ef070a456f5e974d886d1dcc9dde4f63a5c13c437c7` |
| `paper/open_airline_appendix.tex` | `91a07b8e0dfe741a144eaeb637b63a1072afda8ed7e5a000ca459bef54516f40` |
| `paper/open_airline_table.tex` | `4917b2d80cf678f1f847f6119d573c18fd9d7d507230318c6d72b922c3c628cb` |
| `paper/open_coding_results.tex` | `9d1da75347b5bffb4c570260a61e65120cd983ddaab6c7030daafa10cc87aa62` |

**Final PASS: no outstanding correction for the retained numerical or scientific integration.** This is a scientific/numerical integration audit; full-package archival anonymity, PDF page/layout QA and author-only submission inputs remain root's separate release responsibilities.
