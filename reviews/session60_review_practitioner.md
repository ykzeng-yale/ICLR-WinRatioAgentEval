# Session 60 review: practitioner / head-of-experimentation perspective

Reviewer persona: head of experimentation at an online-evals company that runs continuous, guardrailed A/B tests of agent versions (Statsig/Eppo/Spotify-style tooling). Focus: would this protocol be adopted, is it demonstrably better than sequential testing plus guardrail practice, are delayed outcomes, cost, latency, rare safety events and multiple candidates handled, and is the guidance actionable.

This is a model-assisted internal review (ICLR 2027 form mirror in `reviews/rubric.md`), not external human peer review. Every number below was read from a file in this repository or produced by code I ran during this review; anything else is labelled as unverified. I did not modify any manuscript, source, or result file; the only file written is this review. LaTeX was compiled on a scratch copy of `paper/`.

Manuscript snapshot reviewed (SHA-256, 2026-09-17 21:26 local):

| File | SHA-256 |
|---|---|
| `paper/main.tex` | `8ad6c16e38086ce731ddd53032d398294212a5d4dadb347a20fbffc62a5f28a9` |
| `paper/theory.tex` | `053dd3790c382e7ee3c2380b30dd4bd620acdb76307dba0ce2f8d88957d53e16` |
| `paper/results_main.tex` | `d89028e4d61362af7f48b8fdb4d25bf23a5e7b36478977146977a44a122d08bc` |
| `paper/public_results.tex` | `baf02f30703f1ed3bce6b964f7fde6a78416a60f3060fc57e939ee9c592e0c69` |
| `paper/references.bib` | `7a89ce3f749cf451d5743673fbef54e2395035622a2030b06085f73fcab099b6` |
| `src/winstats.py` | `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9` |
| `experiments/run_simulations.py` | `b3d51d15f707855db19b52f206b7b3362fb8f9a3f4a42df138b4a18840f63c9c` |

Note: `paper/main.tex`, `paper/references.bib`, `reviews/RESPONSE_LEDGER.md` and the new `paper/async_results.tex`, `paper/asynchronous.tex`, `paper/async_appendix.tex`, `results/async_*` changed on disk while this review was in progress. The review covers the post-change versions listed above; `theory.tex`, `results_main.tex`, `public_results.tex` and the three core experiment scripts were unchanged by that update (hashes rechecked).

---

## Review block

```
reviewer: session60 practitioner reviewer (model-assisted; head-of-experimentation persona)
round: 3
manuscript_version: main.tex 8ad6c16e...28a9, theory.tex 053dd379...3e16 (2026-09-17 21:26)
summary: |
  The paper proposes a "guarded" deployment protocol for comparing two agent
  systems: a prespecified hierarchical (win/tie/loss) comparison kernel h in
  {-1,0,1} (compliance > success > cost with operational tie thresholds),
  monitored by a finite-sample betting e-process or normal-mixture confidence
  sequence, combined by an intersection-union rule with per-component
  non-inferiority gates (success, compliance). Main results: (i) a
  Horvitz-Thompson identification identity for disjoint AB/BA-randomized
  arrival pairs (Thm. pair_id); (ii) stationary IUT needs no alpha split
  (Thm. iut) while drifting targets need simultaneous CSs (Thm. drift_gate);
  (iii) a new "partial-trace envelope": worst-case completion bounds on
  unresolved pair scores give a lower wealth process that inherits the
  full-data threshold guarantee and never decides later than a
  completed-prefix rule (Thm. async_betting, Cor. async_envelope).
  Experiments: six stationary synthetic scenarios (2,000 reps, 10,000 pairs;
  guarded betting 0.45% false deployment vs 31.05% for repeatedly-inspected
  Wald; 96.85% deployment of an equally successful cheaper agent), boundary
  and adaptive-order stress tests, an informative-delay simulation (mean
  capped decision time 41.285 -> 22.363 ticks), and a descriptive reanalysis
  of 3,336 tau^2-bench and 600 SWE-agent runs showing hierarchical net benefit
  and success-rate difference can have opposite signs (retail o4-mini vs
  Claude-3.7: NB 0.528 vs success diff -0.072).
soundness: 3
presentation: 3
contribution: 2
strengths:
  - Sec. 2 / Prop. compensation / Eq. main_region - the population-priority
    obstruction (favorable NB with worse success) is exactly the failure
    mode we see when teams adopt pairwise "win rate" dashboards; stating it
    and coupling the pairwise primary to population guardrails answers
    "does this protect the primary metric" (key question 1) cleanly.
  - Thm. iut + Thm. drift_gate (theory.tex 426-476) - the stationary
    "no alpha split for a conjunction" vs drifting "split alpha" distinction
    is the first sequential statement of the guardrail IUT logic that Spotify
    (Schultzberg et al. 2024/2026) state only for fixed samples; this is a
    real, if small, clarification of practice (key question 3).
  - App. asynchronous.tex Thm. async_betting / Cor. async_envelope and the
    frozen delay study (async_results.csv) - a defensible, model-free way
    to use pending episodes; the pathwise-domination invariant is asserted
    in code and I reproduced all six result rows exactly (key question 2:
    delayed outcomes).
  - Reproducibility: seeds, manifests, analytic targets checked in code,
    all reported table cells match CSVs (verified below); the writing is
    unusually honest about what is and is not established.
weaknesses:
  - Sec. 6 (main.tex 342-363), references.bib (25 entries) - the paper is
    never positioned against experimentation practice: no Johari et al.
    (always-valid A/B), no Schultzberg et al. 2024/2026 (guardrail IUT in
    production), no Ham et al. (design-based CS whose framework contains
    Thm. pair_id), no Huang arXiv:2609.07785 (paired, cost-aware comparison
    on the same tau^2 data), no Kotawala arXiv:2605.30315 (anytime-valid
    paired LLM comparison), no Matsouaka 2022 (matched-pair win statistics).
    A practitioner cannot tell what changes relative to "Eppo CS on primary
    + guardrail cutoffs". Effect: contribution unassessable; N1/V2/V3 fail.
    Closest prior work: Schultzberg 2026 (IUT guardrails), Ham et al. 2024/26.
  - Table 1 / results_main.tex - the decision-level question a practitioner
    asks ("does the hierarchy pick different deployments than success-
    primary + cost non-inferiority, and are those decisions ones an owner
    endorses?") is not answered. The strongest argument is already in Table
    1 (efficiency-gain row: a success-primary rule can never deploy because
    the success difference is exactly 0) but it is never stated, and the
    obvious comparator columns (success-superiority + cost-NI; linear
    utility; Pareto) are absent. Raised in round 2 empirical; still open.
  - Table 1, results_main.tex 45-52 - the only valid anytime competitor is
    a range-only normal-mixture CS (V=n) that is structurally hopeless for a
    rare-event gate (score SD ~0.10, radius 0.033 at n=10,000). The
    variance-adaptive CSs that GrowthBook/Eppo actually run (asymptotic CS of
    Waudby-Smith et al. 2024; predictable-plug-in betting CS) would resolve a
    0.01 margin at ~10,000 pairs. "Directional betting ... materially more
    useful" is therefore only shown against a straw baseline. Round 1 M1;
    ledger says "comparison open"; still unresolved.
  - Prop. delay_bound / Prop. guardrail_lower_bound (theory.tex 647-728) -
    no numbers. A practitioner needs "how many pairs does the guardrail
    cost?" The answer is computable from the paper's own bound (e.g. >=
    1,232 pairs for delta=0.01 at 80% power; >= 12,416 for delta=0.001) and
    from Table 1 (4,310 mean pairs guarded vs 118 win-only), but is not given.
  - Sec. 3 (main.tex 165-171) - the protocol requires forming disjoint
    arrival pairs and randomizing AB/BA orientation before outcomes. Every
    production platform assigns per-arrival Bernoulli(q). The paper does not
    say how (or whether) its guarantees survive standard assignment.
    This is the single biggest adoption barrier.
  - Eq. main_region (main.tex 155-158) - components g_j in [0,1]; cost and
    latency (the guardrails every team actually sets) are unbounded and
    heavy-tailed, and tau^2 durations are explicitly excluded
    (public_results.tex 10-11). No cost or latency guardrail is shown.
  - Compliance gate at delta=0.01 with base violation rate 0.005
    (experiments_appendix.tex table) permits a 3x increase in violations;
    the paper says margins are illustrative but gives no rule for rare
    events (absolute gate mentioned at theory.tex 101-105, never
    implemented or simulated).
  - main.tex 262-265 - "further error allocation is necessary" for
    several candidates, with no rule. Teams test 3-10 variants at once.
  - public_results.tex 47-50 - swapping the cost/steps tier order flips
    the telecom o4-mini vs Claude-3.7 sign (0.259 -> -0.126); the paper
    offers no operational rule for hierarchy choice beyond "prespecify".
  - async_results.tex 18-19 - "completed-only" false deployment of 100% is
    presented as the naive baseline, but mature platforms define outcomes at
    a fixed post-exposure window, which coincides with the paper's own
    complete-prefix rule; the reveal mechanism (A failures 20x slower) fixes
    the size of the reported gain.
questions:
  - Q1: Add columns to Table 1 and a decision matrix on the 10 primary
    public contrasts for success-superiority + cost-NI, linear utility
    (lambda grid), and Pareto dominance. Where do the rules disagree, and
    which decision would an application owner endorse? - +2
  - Q2: Add a variance-adaptive valid competitor (asymptotic CS of
    Waudby-Smith et al. 2024 as used by GrowthBook; predictable-plug-in
    betting CS) to Table 1 and cs_width. Does guarded betting still win on
    sample use? - +1
  - Q3: Under per-arrival Bernoulli(1/2) assignment with iid arrivals, does
    pairing the k-th A-exposed with the k-th B-exposed arrival (outcome-blind)
    preserve Thm. pair_id / Thm. betting? Under drift? - +1
  - Q4: On the tau^2 / SWE traces with a realistic reveal schedule (success
    grade only at episode end; cost monotone), what fraction of pending pairs
    obtain a collapsed hierarchy enclosure before completion? - +0/+1
ethics_flag: no
rating: 5
confidence: 4
reproducibility_check: pass - all table cells match CSVs; async study replayed exactly in memory (1000/6/6, 1000/997/997, 41.285/22.363 ticks, gain 18.922 +- 0.033); analytic targets confirmed by 2M-pair Monte Carlo; scratch compile clean (25 pages, no undefined citations)
desk_reject_preflight: pass with one blocking edit - D1 body ends on p.8 (references p.8, appendix p.10); D2 AI-use statement present but currently states human verification is NOT complete (must be rewritten before submission); D3 anonymous; D4 references not re-opened by me (bib header claims verification); D5/D6 not checkable here
llm_use: |
  Entire review written by a model-assisted reviewer (Claude), including all
  verification code; no human reviewer contributed. Self-written core
  assessment above is verbatim.
```

---

## 1. What I verified (and how)

All commands were run with `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`; nothing was written outside this file and a scratch LaTeX build directory.

### 1.1 Reported numbers vs. result tables

| Claim (location) | Source of truth | Outcome |
|---|---|---|
| Abstract and Table 1: guarded betting 0.45% under identical agents; repeated Wald 31.05%; efficiency gain 96.85% | `results/simulation_results.csv` rows `null,guarded_betting` (9/2000), `null,guarded_repeated_wald` (621/2000), `efficiency_gain,guarded_betting` (1937/2000) | Match. All 30 cells of Table 1 match the CSV (`safety_regression` row = "Compliance regression"). |
| results_main.tex 34-41: Wilson 0.24-0.85%, 29.06-33.11%, upper 0.192% for 0/2000 | Recomputed with the script's `wilson()` | 0.237-0.853%, 29.06-33.11%, 0.192%. Match. |
| results_main.tex 46: normal-mixture width "about 0.033" at 10,000 pairs | `normal_mixture_radius(10000, .05, 100.)` | 0.03273. Match. |
| results_main.tex 54-67 stress numbers (0.75, 0.45, 32.40, 30.45, 95.25, 55.65, 93.0, 1.1, 0%) | `results/stress_results.csv` | All nine match (15/2000, 9/2000, 648, 609, 1905, 1113, 930/1000, 11/1000, 0/1000). |
| public_results.tex 26-35: retail o4-mini vs Claude-3.7 NB 0.528 [0.423,0.629], success -0.072 [-0.140,-0.004]; telecom 0.259 [0.161,0.354], -0.072 [-0.127,-0.018]; cost decides 60.0% / 33.1% | `results/public_comparisons.csv` primary rows | 0.5278 [0.4232,0.6294], -0.0724 [-0.1404,-0.0044]; 0.2588 [0.1608,0.3538], -0.0724 [-0.1272,-0.0175]; `cost_decisive` 0.6001 / 0.3311. Match. |
| public_results.tex 47-52: telecom steps-before-cost -0.126; SWE NB -0.113, success -0.063; 3,336 tau^2 runs; 12 off-diagonal comparisons per task | CSVs `public_comparisons.csv`, `public_run_metrics.csv`, `public_task_scores.csv` | -0.1257; -0.1133 / -0.0633; 3,336 tau^2 and 600 SWE rows; `comparisons` = 12 for every tau^2 task. Match. |
| async_results.tex 18-31 and async_appendix.tex table: 1000/1000 naive false deployments; 6/1000 (0.6%, Wilson 0.275-1.303%) for both valid methods; 997/1000; 41.285 -> 22.363 ticks; paired gain 18.922 (MCSE 0.033); executions 8130.8 -> 4459.6; no partial decision later, 997 strictly earlier | Re-ran `run_async_experiment.simulate_batch` in memory with the manifest seed (2026091803, child seeds 0/1, batch 25, 40 batches) | Exact replication of every reported figure, including MCSE 0.033 and the 997/0 earlier/later counts. The code's own invariants (partial <= latent wealth; interval containment; equal final decisions) passed in every batch. |
| experiments_appendix.tex analytic targets | `exact_targets()` vs 2,000,000-pair Monte Carlo from `generate()` | efficiency gain: 0.36258 (MC) vs 0.36249 (analytic), MCSE 0.0006; success regression: 0.31029 vs 0.31064. Consistent. |

### 1.2 Proof steps re-derived

- **Thm. normal_cs (theory.tex 288-329).** Conditional Hoeffding gives `E[exp(lambda D_i) | F_{i-1}] <= exp(lambda^2 c_i^2 / 8)`; with `V_n = sum c_i^2 / 4` the exponent is `lambda^2 V_n / 2`, so `M_n(lambda)` is a supermartingale. Mixing against `N(0, 1/rho)`: `int exp(lambda S - lambda^2 V/2) sqrt(rho/2pi) exp(-rho lambda^2/2) dlambda = sqrt(rho/(V+rho)) exp(S^2 / (2(V+rho)))`. Setting `M_n >= 1/alpha` and solving gives `S^2 >= (V+rho) log((V+rho)/(rho alpha^2))`, which is `B_alpha(V)^2`. Correct.
- **Thm. betting (theory.tex 363-393).** Factor positivity `1 + lambda(Z - c) >= 1 - lambda(1+c) > 0` for `lambda < 1/(1+c)`; the code's grid `np.geomspace(1e-4, .99/(1+threshold), 40)` (`src/winstats.py` line 76) respects this. I evaluated `E[1 + lambda(Z-c)]` numerically at `c = -0.01` for three boundary-null ternary laws (`(p_W,p_L) = (.005,.015), (0,.01), (.3,.31)`): maximum deviation from 1 was 2.2e-16 across all 40 stakes. Correct.
- **Thm. async_betting (asynchronous.tex 169-198).** With `lambda_k >= 0` and enclosures clipped to `[-B,B]`, `0 < 1 + lambda_k(l_i - c) <= 1 + lambda_k(X_i - c)` because `1 - lambda_k(B + c) > 0`; products and convex mixtures preserve the inequality; so any partial crossing implies a full-process crossing, bounded by Ville. Correct, and it is only a threshold guarantee, as the paper says. The corresponding runtime assertion (`run_async_experiment.py` lines 145-151) reported `max_partial_minus_latent_log_e = 0.0` in my replay.
- **Thm. iut (theory.tex 426-443).** The argument needs one fixed index `j*` whose conditional-mean null holds throughout; no dependence assumption is used. Correct. Note the theorem's premise is stationarity of every component mean, which the synthetic scenarios satisfy by construction.

### 1.3 Code vs. theory correspondence

- The reported betting deployment rule is the *same-look conjunction* (`np.logical_and.reduce(all_e)` then `.any(axis=1)` in `run_simulations.py` lines 82, 110), matching theory.tex 419-421. Round 2 finding R2.2 is resolved.
- Adaptive-order stress test: variance increment `1/(4 min(q,1-q)^2)` (`run_stress_tests.py` line 58) equals `r_i^2/4` for the predictable range `r_i = 1/min(q,1-q)` implied by `|Z_i| <= 1/(2 min(q,1-q))` (main.tex 190-191). Correct.
- Group Wald uses `norm.ppf(1 - alpha/10)` at the ten equally spaced looks only (`group_mask`), matching experiments_appendix.tex 25-26.
- The guarded normal-mixture rule in `run_simulations.py` line 74 uses level alpha = 0.05 per gate (stationary IUT), not alpha/(J+1); this is valid for the stationary scenarios but experiments_appendix.tex does not state the per-gate level (minor; see Optional).
- Compile check (scratch copy): 25 pages; body ends on page 8, references begin on page 8, appendix on page 10; no undefined citations or references.

### 1.4 What I did not verify

Reference metadata (D4) was not re-opened; the bib header claims verification. The public raw-source hashes were verified by the round-2 empirical reviewer, not by me. The other-session artifacts in `results/replay/`, `results/benchmarks/`, `results/online_methods_results.csv`, `results/cs_width.csv` and `experiments/decision_disagreement.py` were read but not re-executed; they are not cited by the manuscript.

---

## 2. Practitioner assessment: would we adopt this?

**What is genuinely useful.** (a) The compensation obstruction (Prop. compensation) is real and common: teams that switch to "pairwise win rate" dashboards regularly ship cheaper agents that fail more. Coupling a paired primary to population NI gates is the correct fix. (b) The stationary-vs-drift split of the guardrail IUT (Thms. iut / drift_gate) is a cleaner statement than anything in vendor docs; Spotify's practice of not adjusting alpha for guardrails is justified only under the stationary premise and the paper says so. (c) The partial-trace envelope is the first proposal I have seen that uses pending episodes without a delay model and without changing the estimand; the "cannot decide later than the completed-prefix rule" property is what an on-call engineer wants.

**Why we would not adopt it as written.**

1. *It does not map onto how traffic is assigned.* We assign per-arrival Bernoulli(q) and compute metrics per exposure. Section 3 asks us to form disjoint pairs before outcomes and randomize orientation within pairs. Nothing in the paper says whether outcome-blind post-hoc pairing (k-th A-exposed with k-th B-exposed arrival in a stratum) preserves Thm. pair_id and the betting guarantee. Under iid arrivals it should (the paired scores are then iid with mean theta_s); under drift the k-th A and k-th B arrivals occur at different times and the running-average target changes meaning. The paper must state this mapping and which theorems survive; otherwise adoption requires modifying the assignment service.

2. *It does not demonstrate better decisions than our current rule.* Our default is "primary metric superior AND every guardrail non-inferior" with per-metric sequential CSs. Replace "primary" by success rate and add a cost NI margin, and we have a rule that the paper never compares against. Table 1 already contains the decisive case (efficiency-gain row: success difference exactly zero, so a success-primary rule can never deploy while the guarded hierarchy deploys 96.85%), but the paper does not say it, and on the public data it shows the opposite direction (the hierarchy wanted to deploy the less successful agent; the guardrail stopped it). A practitioner reads Sec. 5 as "the hierarchy adds a risk that the guardrail then removes". The missing artifact is a decision matrix (see Must-fix 2).

3. *The strongest valid competitor is missing.* Our vendors run variance-adaptive asymptotic CSs (GrowthBook: Waudby-Smith et al. 2024 asymptotic CS; Eppo: tuned Howard et al. mixture with observed variance). The compliance score has SD sqrt(2 x .995 x .005) = 0.0997, so a variance-adaptive width at n = 10,000 is roughly 0.1 x 0.033 = 0.0033, comfortably inside the 0.01 margin. The paper's range-only normal mixture (V = n) at 0.033 is therefore not the method we would be replacing. (`results/cs_width.csv` in the repository compares a hedged betting CS and a Dirichlet-multinomial CS with the normal mixture, but on the net-benefit score only, and it is not in the manuscript.)

4. *No planning guidance.* We cannot size an experiment from the paper. The information it needs is already derivable: from Prop. guardrail_lower_bound with alpha = 0.05, beta = 0.2, `E[T] >= kl(0.8, 0.05)/kl(p1, delta)`:

   | Guardrail margin delta | Acceptable alternative p1 | Lower bound on expected pairs (beta = .2) | (beta = .05) |
   |---|---|---|---|
   | 0.03 | 0.015 | 404 | 562 |
   | 0.01 | 0.005 | 1,232 | 1,713 |
   | 0.005 | 0.0025 | 2,475 | 3,440 |
   | 0.001 | 0.0005 | 12,416 | 17,258 |

   and from Table 1 the observed cost of the guardrail is 4,310 mean pairs (8,620 executions) versus 118 pairs for the preference-only rule in the efficiency-gain scenario, a 36x increase. The best fixed stake's expected log growth per pair shows which gate binds there: success gate (margin 0.03 at 75% success) needs about 2,500 pairs to reach log(20); compliance gate about 790. None of this is in the paper.

5. *Cost and latency are not gates.* Every team sets "cost per task not more than +x%" and a P95 latency guardrail. The region D uses bounded components g_j in [0,1]; cost is unbounded and latency is explicitly excluded. The bounded transformation is easy (cost capped at the episode budget H, `g = 1 - min(c,H)/H`, or an exceedance indicator `1{c > budget}`), but a *relative* cost guardrail (+10%) is a ratio, not a bounded linear score, and needs a separate argument. The paper should say which of these it supports.

6. *Rare safety events.* With base violation rate 0.5%, a 1 pp NI margin lets the candidate triple its violation rate. The appendix (theory.tex 101-105) correctly says an absolute-rate gate is needed, but none is implemented or simulated, and the sample-size table above shows that a defensible rare-event margin (0.1 pp) needs tens of thousands of pairs. Say this plainly and point to a counting-process canary (Lindon and Kallus, AISTATS 2025) for severe events rather than a per-episode NI gate.

7. *Multiple candidates.* main.tex 262-265 defers the multi-candidate case. In practice we run 3-10 variants. With disjoint pairs, K candidates need K pair streams against control (control exposure share K/(K+1)), and the deployment IUT needs Bonferroni over candidates (alpha/K) or e-BH over candidate e-values if more than one may be deployed. One paragraph would suffice.

8. *Hierarchy choice.* The telecom sign flip under tier reordering (0.259 -> -0.126) is exactly what stops teams from prespecifying a hierarchy. The appendix hints at a finite-family simultaneous CS; make it a rule: deploy only if the *minimum* lower bound over a prespecified family of tier orders / tolerances clears zero (the anytime-valid analogue of Li, Fan and Yang 2026, arXiv:2608.29857). This costs one paragraph and one table row.

---

## 3. Checklist (rubric.md), with pointers

| Item | Answer | Pointer |
|---|---|---|
| N1 closest prior result named per theorem | No | Thm. pair_id: Ham et al. design-based CS not cited; Thm. iut: Schultzberg 2024/2026 not cited; Thm. offline: Fang et al. cited, Matsouaka 2022 (matched pairs) not; delay: Lindon-Kallus 2026 now cited (asynchronous.tex 391-394) |
| N2 no "first"/"novel" overreach | Yes | main.tex 86-88 |
| N3 contribution stands if CS proofs replaced by citations | Partly | identification + protocol + envelope stand; empirical claim of superiority over anytime baselines does not (Must-fix 3) |
| N4 contemporaneous work | No | Huang arXiv:2609.07785 (2026-09-07, same tau^2 data) absent; listed in `evidence/lit_winstats.md` A2 |
| T1-T3 pairing/randomization/bounds | Yes | theory.tex 179-267 |
| T4 error events named; alpha allocation identical text/code | Partly | per-gate alpha for guarded normal mixture not stated in experiments_appendix.tex |
| T5 finite-grid validity vs consistency | Yes | theory.tex 394-404 |
| T6 delay rules preserve coverage; timeouts are outcomes | Yes | prop:delay; asynchronous.tex |
| T7 independent unit consistent | Yes | thm:offline; reused-run stress test |
| T8 reviewer re-derived theorems | Yes | Sec. 1.2 above (normal_cs, betting, async_betting, iut) |
| E1 Type I / coverage with MC SEs incl. harmful-primary | Yes | Table 1, stress_results.csv |
| E2 power, stopping time, false deployment, abstention for all methods | Partly | abstention not reported; stopping times only as capped pair counts |
| E3 baselines | No | missing: variance-adaptive CS, GST alpha-spending (only Bonferroni group Wald), marginal-guardrail-only rule, scalarized composite, Pareto |
| E4 real data >= 2 families, pairing, clusters, versions, historical costs | Yes | public_results.tex, public_appendix.tex |
| E5 no "live A/B" wording for replay | Yes | throughout |
| E6 sensitivity to hierarchy order, thresholds, grading noise, workload shift | Partly | order and tolerance yes; grading noise and workload shift no |
| E7 figure uncertainty defined | Yes | captions |
| R1 code/seeds/manifests | Yes (no anonymous link in text yet) | Reproducibility statement |
| R2 numbers match implemented boundary/alpha | Yes | Sec. 1.1, 1.3 |
| R3 statements present | Yes, but AI-use statement text is not submission-ready | main.tex 395-401 |
| C1 one-sentence claim p.1; hierarchy example p.2; operational reading per theorem | Partly | claim yes; no worked deployment-rule example with numbers by p.2 |
| C2 notation table | No | none |
| C3 <= 9 pages | Yes | body ends p.8 |
| C4 abstract numbers match tables | Yes | Sec. 1.1 |
| V1 framed as agent decisions | Yes | |
| V2 "what does the reader learn beyond Buyse + Howard" stated explicitly | No | Sec. 6 says how to judge it, not what it is |
| V3 positioned vs ICLR evaluation work | Weak | tau-bench, SWE-agent, WildBench, LLMs-get-lost cited; no engagement with Huang/Kotawala/CELEUS-style sequential LLM evaluation |
| D1-D3 | Pass (D2 text must change) | |
| D4-D6 | Not checkable here | |

---

## 4. MUST-FIX (blocks submission)

1. **Position against experimentation practice and the nearest ML precedents** (main.tex Sec. 6, lines 342-363; references.bib). Add a paragraph "Sequential guardrailed A/B practice" citing Johari et al. 2017/2022, Ham et al. (design-based CS; state that Thm. pair_id is the paired instantiation of that framework), Schultzberg et al. 2024 and 2026 (fixed-sample guardrail IUT; Thm. iut is its sequential/stationary form and Thm. drift_gate the drifting correction), Lindon et al. KDD 2022 (canaries), Huang arXiv:2609.07785 and Kotawala arXiv:2605.30315 (nearest agent/LLM paired comparisons), Matsouaka 2022 (matched-pair win statistics; the online design is its sequential extension). End with one sentence per item stating the precise difference. All BibTeX entries already exist in `paper/refs_industry.bib`, `refs_sequential.bib`, `refs_winstats.bib`.

2. **Decision-level comparison against the practitioner's default rules** (Table 1 and Sec. 5 public results). Add columns/rows for (a) success-superiority + cost non-inferiority (the Spotify/Eppo rule with success as primary), (b) cost-superiority + success non-inferiority, (c) linear utility `success - lambda * cost` over a lambda grid (Huang's rule), (d) Pareto dominance on (success, cost). Report deployment rate and capped sample use in the six synthetic scenarios and the decision for each of the 10 primary public contrasts. State explicitly that the efficiency-gain scenario is the case the hierarchy is for (success-primary never deploys; guarded hierarchy deploys 96.85%), and that on the public data the guardrail, not the hierarchy, made the decision. Note: `experiments/decision_disagreement.py` and `results/benchmarks/decision_matrix.csv` (another session; not audited by me) appear to implement most of this and are not referenced by the manuscript.

3. **Add a variance-adaptive valid competitor** (Table 1, results_main.tex 45-52, and a width table). At minimum the asymptotic CS of Waudby-Smith et al. 2024 (as deployed by GrowthBook) and the predictable-plug-in betting CS of Waudby-Smith and Ramdas 2024, each applied per gate with the same IUT. Then either retain "directional betting is materially more useful" with the new evidence or drop it. Without this the paper's only valid comparator is one it has itself declared uninformative for rare-event gates. (EXPERIMENT_QUEUE.md lists a CPU-only "sequential U-statistic reference baseline" as unclaimed; that job plus the two CSs above closes this item.)

4. **Rewrite the AI-use statement** (main.tex 395-401). It currently states that human verification has not been completed; a submission cannot carry that sentence. Replace with the actual disclosure of what was verified by the human author(s).

## 5. SHOULD-FIX

5. **Bernoulli-assignment mapping** (Sec. 3, main.tex 165-171). State whether outcome-blind pairing of the k-th A-exposed and k-th B-exposed arrivals within a stratum satisfies the conditions of Thm. pair_id / Thm. betting under iid arrivals, and what breaks under drift; give the practitioner a recipe that does not require changing the assignment service.

6. **Planning guidance** (new paragraph in App. B or Sec. 4). Evaluate Prop. delay_bound and Prop. guardrail_lower_bound numerically (table in Sec. 2 above), report which gate binds in each Table 1 scenario, and state the delta^-2 scaling in words. Report abstention/non-decision rates and calendar-time-to-decision alongside capped pair counts.

7. **Cost and latency guardrails** (Eq. main_region, main.tex 155-158). Specify the bounded transformations that fit the theory (budget-capped cost; exceedance indicators; latency > SLO indicator) and say explicitly that a relative (+x%) cost guardrail is outside the bounded-score results unless transformed. Add one such gate to the synthetic study.

8. **Rare-event guidance** (theory.tex 101-105; experiments_appendix.tex table). Implement the absolute-rate gate as an e-process on the candidate's violation indicator, show it in Table 1, and state the sample requirement for sub-percent margins from Prop. guardrail_lower_bound. Recommend a counting-process canary for severe events.

9. **Multiple candidates** (main.tex 262-265). Give the rule: Bonferroni alpha/K over candidate deployment conjunctions (or e-BH when several may ship), K pair streams against control, control exposure share K/(K+1).

10. **Hierarchy-robust gate** (public_results.tex 47-50; theory.tex 749-757). Add the min-over-prespecified-family lower bound as an explicit deployment criterion and report it for the telecom contrast whose sign flips.

11. **Frame the async baseline correctly** (async_results.tex 18-19; async_appendix.tex 16-22). State that fixed-window outcome definition (standard practice) coincides with the complete-prefix rule, so the "completed-only" 100% false deployment is an outcome-dependent-reveal pathology, not current platform behaviour; report the gain as a relative reduction (46%) and label ticks as synthetic in the abstract. Add a reveal schedule where success is graded only at episode end for both arms and report how often the hierarchy enclosure collapses early.

12. **State the per-gate alpha for every method in experiments_appendix.tex** (line 23 area): guarded normal mixture and betting use alpha = 0.05 per gate under the stationary IUT; drift experiments would use alpha/(J+1).

## 6. OPTIONAL

13. A worked one-paragraph example by page 2 with concrete numbers (hierarchy, margins, when the rule deploys) and a notation table (C1/C2).
14. Report a power / minimum-detectable-effect curve for the guarded rule at 10,000 pairs (the weak-gain row, 4.9%, is currently the only hint).
15. Integrate, after audit, the replay study in `results/replay/replay_results.csv` (paired vs cross-arrival replay of tau^2 runs; deployment 96.2% vs 33.0% for o4-mini vs GPT-4.1 across domains), which directly illustrates the Sec. 2 estimand distinction on real traces; it is currently absent from the manuscript.
16. Grading-noise sensitivity (E6): re-run the public reanalysis with symmetric label flips at 5% and report the change in NB sign and tier contributions.

---

## 7. Score justification

Calibrated against ICLR 2025/2026 accepted work in evaluation methodology: the paper is technically correct (I re-derived the main CS, betting, IUT and envelope arguments and replayed the reported experiments exactly), unusually candid, and reproducible, which earns soundness 3 rather than 2. But its contribution is a careful assembly of known tools (GPC kernel + bounded-mean e-process + IUT + pathwise enclosure), and the one empirical claim of practical superiority ("directional betting ... materially more useful") is supported only against a baseline the paper itself calls uninformative; the practitioner's default rule and the vendor-deployed variance-adaptive CSs are absent, the nearest precedents (Ham et al., Schultzberg, Huang, Kotawala, Matsouaka) are uncited, and the actionable guidance a deployment team needs (assignment mapping, sample sizes, cost/latency and rare-event gates, multi-candidate rule) is missing. That combination is a 5 (marginally below threshold): sound, but the evidence and framing do not yet show a practitioner what changes relative to what they run today. Items 1-3 are each addressable within the deadline with existing repository code and bib entries; completing them with a favourable decision matrix would move this to a 6, and a demonstrated sample-use advantage over a variance-adaptive CS to a 6-8.

---

## 8. Notes for the root session (outside the review form)

- The user's standing instruction is to check whether any GitHub-listed experiment needs to be run. `EXPERIMENT_QUEUE.md` lists "Competitive sequential U-statistic reference baseline" (Issue #3, CPU-only, unclaimed). That job is precisely what Must-fix 3 needs. This reviewer's ownership rules (no git, no new directories) prevented claiming it; it should be assigned. The "Larger prospective randomized stream experiment" (Issue #1) and "local-model replication" (Issue #2) are queued and unfunded; nothing in this review depends on them.
- Repository artifacts that exist but are not in the manuscript and bear directly on the weaknesses above: `results/benchmarks/decision_matrix.csv` and `experiments/decision_disagreement.py` (Must-fix 2), `results/cs_width.csv` and `results/online_methods_results.csv` (Must-fix 3; the ledger records a numerical defect in the contributed multinomial module, so audit before use), `results/replay/replay_results.csv` (Optional 15). None were re-executed by me.
- Files changed on disk during this review; if `main.tex` changes again, the page-limit check (body ends p.8) should be repeated.
