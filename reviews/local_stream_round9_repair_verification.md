# Local stream, Round 9 repair: independent verification

Verifier: independent statistical check (did not write the repair). Date 2026-09-18. No model call, no git command,
no raw-evidence file, frozen tau2 file, results/tau2_open file or llama-server touched. Every number below comes from
a file read or a computation run in this session. Requirements source: `round9_open_model_evidence_audit.md`.

**Overall: PASS on all seven items. No file of the repair was edited.** One file was added:
`experiments/local_stream/verify_round9_independent.py` (read-only reproducer). Three non-blocking remarks at the end.

| # | item | verdict |
|---|---|---|
| 1 | R1 design-based argument, interval and first exclusion time | PASS |
| 2 | R2 superpopulation proof, labelled as assumption | PASS |
| 3 | corrected two-sided CS (martingale proof, regression check, E1 intervals) | PASS |
| 4 | E2 conservativeness argument | PASS |
| 5 | wording requirements in `report_v2.md` | PASS |
| 6 | raw evidence unmodified | PASS (with the limitation stated below) |
| 7 | data manifest and anonymized copies | PASS |

## 1. R1 (design-based) -- PASS

- Independence. Conditional on the realized permutation the unordered pairs are fixed; the orientation coins are
  independent Bernoulli(1/2); different pairs use disjoint tasks and separate model calls. So Z_k are independent
  given the pairing with mu_k = (1/2)[m(s_k,t_k) + m(t_k,s_k)], not identically distributed. The addendum also gives
  the fallback that, if episode noise is serially dependent, mu_k is read as E[Z_k | past]; the CS only needs
  Z_k - mu_k to be a martingale difference in [-1-mu_k, 1-mu_k] (range 2, sub-Gaussian variance proxy 1), so the
  fallback is correct.
- CS. Normal mixture martingale M_n = sqrt(rho/(n+rho)) exp(S_n^2 / (2(n+rho))), S_n = sum (Z_k - mu_k), is a
  nonnegative supermartingale with M_0 = 1 for conditionally 1-sub-Gaussian increments; M_n >= 1/alpha iff
  |S_n| >= sqrt((n+rho) log((n+rho)/(rho alpha^2))). Dividing by n gives exactly the radius in
  `winstats.normal_mixture_radius` (two-sided at alpha, not alpha/2 per side). It covers the moving target mu_bar_n
  for all n simultaneously; correctly, no running intersection is taken.
- Nothing stronger is claimed: E_design[mu_bar_n] = theta_N is correct (under a uniform permutation each ordered pair
  of distinct tasks is equally likely in positions (2k-1, 2k), and the coin symmetrizes), and both the addendum and the
  report say the CS is about mu_bar_n conditional on the matching and that no without-replacement martingale / CS
  for theta_N is claimed. It is not used as a coverage claim anywhere in `report_v2.md`. Monitor crossings are
  labelled descriptive under R1 with the correct reason (pointwise null is stronger than a null on mu_bar_n).
- Recomputation from `monitor_pass1.csv` (own code): n = 295, 69/18/208, NB = -0.4711864; radius at 295 =
  0.1828387393; NB CS [-0.6540252, -0.2883477]; success-difference CS [-0.1319913, 0.2336862]; first n with upper
  bound < 0 is 60 and it stays below from 60; the R1 success lower bound never exceeds -0.03. All equal
  `summary_v2.json` (radius column of `running_cs_v2.csv` agrees to 1.8e-15).
- rho = 100 was chosen after outcomes; this is disclosed as part of the post hoc status. Acceptable.

## 2. R2 (superpopulation) -- PASS

Proof is correct: a permutation drawn independently of an iid vector leaves it iid (exchangeability of the product
law, then mix over permutations); disjoint consecutive pairs are iid; independent coins and episode noise keep (Z_k)
iid, so E[Z_k | F_{k-1}] = theta_P = E m(s,t) (the symmetrization is immaterial for iid s,t). It is headed
"an ASSUMPTION", states it cannot be verified for a curated roster, and every R2 number in the report carries the
assumption (summary paragraph, section 3 table in bold, decision-rule `reading` column, figure captions). The
decided-pair WR CS is claimed only under R2 ("no R1 analogue is claimed"), which is right because conditioning on
"decided" preserves a common Bernoulli parameter only for iid pairs.

## 3. Corrected two-sided CS -- PASS

- Derivation. For candidate m and fixed stake lambda in (0, 0.5], each factor 1 + lambda (z - m) >= 0 because
  |z - m| <= 2; if E[Z_k | F_{k-1}] = m the product is a nonnegative martingale with initial value 1. K+ (grid average
  over +lambda) and K- (over -lambda) are therefore test martingales, and so is any fixed convex combination, in
  particular (K+ + K-)/2. Ville gives P(exists n: K_n(m_true) >= 1/delta) <= delta. max(K+, K-) is not a
  supermartingale (E max = 1 + mean stake = 1.0637 for one fair +/-1 draw). The set {m: K_n(m) < 1/delta} is an
  interval because each product is a product of nonnegative, monotone, affine functions of m, hence convex, so K+
  and K- and their average are convex in m; the sample mean is inside (AM-GM gives K <= 1 there), so bisection from
  the sample mean with the outside iterate returned is conservative. `src/wincs.py` sha256 6a6a0b51...2907a3b
  implements exactly this for both the ternary and the Bernoulli (WR) capital; `src/test_wincs.py` passes.
- `check_two_sided_cs.py` re-run (output to scratchpad, 148 s, exit 0): witness E max = 1.06370423, E hedged =
  1.000000000000; ever-miss 0.0100 / 0.0105 / 0.0100 (max rule 0.0285 / 0.0230 / 0.0245); 0 interval-vs-capital
  disagreements. Identical to the stored `two_sided_cs_check.json`.
- Independent E1 intervals (own capital + brentq, no wincs import):

| interval | hedged, mine | `summary_v2.json` R2 | audit directional 0.025 (my recomputation) | v1 max rule (mine) |
|---|---|---|---|---|
| NB | [-0.6281037, -0.2879839] | [-0.6281037, -0.2879839] | [-0.6282930, -0.2877391] | [-0.6183726, -0.3008304] |
| success diff | [-0.0786118, 0.1793977] | [-0.0786118, 0.1793977] | [-0.0787917, 0.1795753] | - |
| WR | [0.2010018, 0.5299129] | [0.2010018, 0.5299129] | [0.2008608, 0.5302186] | - |

  The directional-0.025 column reproduces the audit's diagnostic values to 6 decimals, and the hedged intervals sit
  inside them by 2e-4 to 3e-4, as expected (
  hedged >= 1/delta requires max(K+, K-) >= 1/delta and is implied by max >= 2/delta, so the hedged set lies inside the alpha/2-per-tail set and
  contains the max-rule set). Stored endpoints differ from brentq by at most 2.3e-8, always outward. First n with
  upper bound < 0: 42, stays below from 50 -- equals the report.

## 4. E2 -- PASS

For independent task scores S_t with means tau_t and variances v_t: E sum (S_t - S_bar)^2 =
(1 - 1/N) sum v_t + sum (tau_t - tau_bar)^2, hence E[s^2/N] = (1/N^2) sum v_t + (1/(N(N-1))) sum (tau_t - tau_bar)^2
= Var(S_bar) + nonnegative term. The formula in the addendum and report is exact; the t interval is asymptotically
conservative for theta_roster and is labelled "normal approximation". Hoeffding radius sqrt(2 log(2/alpha)/N) is
correct for range 2 (2 exp(-N t^2 / 2)); 0.1117 at N = 591, giving [-0.7682, -0.5448] for NB and [-0.112, 0.112] for
the success difference. The superpopulation reading is stated separately. Pair-level component intervals replace
the Welch intervals.

## 5. Wording -- PASS

Grep of `report_v2.md`: "B_harmful" 0 hits; "B harmful", "independent pairs", "valid decision", "Welch" appear only
once, inside the sentence telling the reader to re-read the v1 text with the corrections; "robust non-inferiority"
appears only as "**This is not a robust non-inferiority result**" (slack 0.000251 stated, Hoeffding and online
intervals next to it); "guarded approval" appears only as "not a reverse guarded approval of A"; "before any model
call" appears only as the quoted phrase being corrected to "before any design-task outcome"; E1-E2 difference is
"DESCRIPTIVE ONLY ... no joint uncertainty"; prompt, completion and total tokens, calls and latency are tabulated per
arm with the generation-count and `n_executions` caveats; H1 negative result retained. The report also discloses
that the harm e-process was above threshold at pair 14 inside the unread n < 20 window (I confirmed: first
log_e_harm >= log 20 is at n = 14; first read crossing at 24).

## 6. Raw evidence -- PASS, with a limitation

Current sha256: episodes.jsonl 95179f93...0effa0; monitor_pass1.csv 67504351...4621a6; monitor_state.json
daeca326...ef1773; run_manifest.json f2efc949...15aa4f; design.json 6175b815...645457. These equal
`analysis_v2_manifest.json -> raw_evidence_sha256` and the `original_sha256` entries of `release_anon/MAPPING.json`.
Limitation: the only hash recorded BEFORE the repair is design.json's (in `design.sha256`, `run_manifest.json`, and
v1 `summary.json`/`report.md`); it matches. For the other four files no pre-repair hash exists in
`v1_pre_round9/` or the run manifest, so byte-identity with the pre-repair state is supported indirectly:
(a) file mtimes are 17:37:01Z = the `end_ts` of the last episode, three hours before the v2 work (20:18Z+);
(b) the v1 `episodes_flat.csv` (mtime 17:38Z, hash equal to the preserved copy) matches the current episodes.jsonl on
all 1,182 rows x 5 fields (0 mismatches); (c) the audit's independent aggregates reproduce exactly: 1,182 unique
keys, 433/433 successes, 591/1,748 calls, 41,491/185,088 completion and 71,218/528,191 prompt tokens, mean latency
2.7997/12.4761 s, 69/18/208; (d) `analysis_v2.py` asserts monitor z, success_diff and log_e_harm equal the
reconstruction. All 14 original/anonymized hashes in MAPPING.json and every hash in `analysis_v2_manifest.json`
(outputs, scripts, src, frozen files, v1 copies) verify against the files on disk.

## 7. Data manifest and anonymization -- PASS

`verify_data_manifest.py` (without `--verify-pinned`, which would rewrite the manifest timestamp and invalidate its
recorded hash): local files OK, task list rebuilds to 23727895...01c2ce (591 = 427 + 164) = design.json stamp. Pinned
URLs fetched independently into memory (curl | sha256, nothing saved): mbpp_sanitized 255,053 bytes, humaneval
44,877, mbpp full 563,743; bytes and sha256 identical to the manifest for all three; every pinned URL contains the
40-hex upstream revision and none contains `master`. `release_anon/` (16 files incl. MAPPING): 0 hits for `/Users/`,
the account name, "yukang", "zeng", "yale", the host name (full and short), e-mail patterns or the repo owner;
residual `/private/tmp` hits are generic sandbox-profile text in protocol.md; `.local` hits are `<HOME>/.local/share/uv`.
v2 outputs (`report_v2.md`, `summary_v2.json`, csvs, manifests) contain no personal path.

## Non-blocking remarks (no edit applied)

1. tau2 addendum (b), R1: "conditional on the realized matching and on the collected trajectories' law" is vague.
   Because the tau2 orientations are drawn independently of batch-collected trajectories, the cleanest valid
   statement conditions on the collected trajectories themselves: then the only randomness is the coins, pair
   scores are independent regardless of shared seeds, repeated tasks or batch effects, and
   mu_k = (1/2)[h(y_B(u_k), y_A(v_k)) + h(y_B(v_k), y_A(u_k))]. With m defined as a model-sampling expectation the
   independence across pairs additionally needs independent episodes, which the shared trial seeds make
   questionable. Recommend adding that sentence when the tau2 analysis_v2-style script is written. Not edited here
   because it is a wording judgement and the file hash is recorded in `analysis_v2_manifest.json`. The rest of the
   tau2 addendum (batch label, block-1 restriction, seed-note supersession, token scope, radius 0.63 =
   sqrt(149 log 596)/49 = 0.6297, "cannot be narrower" claim) is correct.
2. E2 finite-roster independence across tasks shares the same caveat as R1 (serially dependent latency noise); the
   addendum mentions period effects but not this. Immaterial at the observed effect size (Hoeffding interval is
   also far from 0), but the Hoeffding interval is "assumption-free" only given independent task scores.
3. `report_v2.md` section 9 says "about 4 min"; the builder reports about 2.5 min. Cosmetic.

## Reproducers

```
.venv/bin/python experiments/local_stream/verify_round9_independent.py      # items 1 and 3 (independent code)
.venv/bin/python experiments/local_stream/check_two_sided_cs.py --out <scratch>/check.json
.venv/bin/python src/test_wincs.py
.venv/bin/python experiments/local_stream/verify_data_manifest.py            # item 7, local + rebuild
shasum -a 256 results/local_stream/{episodes.jsonl,monitor_pass1.csv,monitor_state.json,run_manifest.json,design.json}
grep -rIl "/Users/" results/local_stream/release_anon                         # expect no output
```
