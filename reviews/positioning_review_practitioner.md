# Practitioner review of `submission/positioning_memo.md`

Reviewer stance: head of experimentation at an AI-evaluation company that runs continuous, guardrailed online A/B tests of agents on Statsig/Eppo-style tooling. Date: 2026-09-17. This is an adversarial internal review, not human peer review. Everything below traces to a file in this repository or to a source I opened in this pass; items I could not open are marked UNVERIFIED.

Files read in full: `submission/positioning_memo.md`, `evidence/{venue_and_novelty,theory_design,empirical_feasibility,lit_winstats,lit_sequential,lit_agenteval,industry_practice,asynchronous_novelty,async_experiment_protocol}.md`, `paper/main.tex`, `paper/theory.tex` (lines 420-520), `paper/results_main.tex`, `paper/public_results.tex`, `experiments/protocol.md`, `experiments/run_replay.py`, `experiments/decision_disagreement.py` (grep), `results/{simulation_results,stress_results,online_methods_results,cs_width,async_results}.csv`, `results/replay/{replay_results.csv,manifest.json}`, `results/replay_run.log`, `results/benchmarks/{decision_matrix.csv,decision_matrix_summary.json,tau2_rankings.csv}`, `reviews/{RESPONSE_LEDGER,round2_empirical_independent,round2_theory_independent,round3_async_empirical_independent,rubric}.md`, `PROJECT_STATUS.md`, `EXPERIMENT_QUEUE.md`.

Sources opened in this pass (WebFetch; the web-search budget was already exhausted, so no new sweeps were run): arXiv abs 2402.11609 and HTML full text (Schultzberg et al., Spotify risk-aware decisions); arXiv abs 2604.09256 (Schultzberg, Bonferroni); arXiv abs 2609.07785 (Huang); arXiv abs 2605.30315 (Kotawala); arXiv abs 2501.03982 (Koning & van Meer); arXiv abs 2603.25971 (Lindon & Kallus, delayed outcomes); arXiv abs 2608.29857 (Li, Fan & Yang); arXiv abs 2402.09698 (Choe & Ramdas); arXiv abs 2011.03567 (Lindon & Malek, NeurIPS 2022); arXiv abs 2402.06122 (PEAK, ICML 2024); arXiv abs 2510.11977 (HAL); Eppo statistical-nitty-gritty and guardrail-cutoff docs; Statsig sequential-testing and AI Evals docs; GrowthBook sequential doc; LaunchDarkly regression-detection doc; Spotify engineering post "Better experiments with LLM evals: a funnel, not a fork" (May 2026). Could not open: Wiley page for Fu 2026 (403; I rely on the prior agent's Europe PMC record), the NeurIPS proceedings page for Lindon & Malek (404 at the guessed hash; the arXiv page states NeurIPS 2022).

---

## 1. Verification ledger for claims the memo leans on

| Memo claim | What I found | Status |
|---|---|---|
| Spotify: 42% of launches rolled back for secondary-metric regressions; 12% of A/B tests ship positive; "opinions, not evidence" | All three phrases appear verbatim in the May 2026 Spotify post. | Verified |
| Spotify: "with 5 guardrails powered at 80%, simultaneous power drops below 40%" | The arXiv paper (2402.11609 HTML) says "Already at 10 guardrail metrics, the simultaneous power is less than 11% without adjustment" and prescribes power 1-β/(G+1). The "5 guardrails / below 40%" sentence is not in the paper; the industry file attributes it to the 2024 blog post, which I did not open. Attribute to the blog only, or compute it yourself (0.8^5 = 0.33, 0.8^6 = 0.26) and say so. | Partly verified; fix attribution |
| Spotify decision rule is a fixed-sample conjunction | Paper's Decision Rule 2: ship iff at least one success metric significantly superior AND all guardrails significantly non-inferior AND no success/guardrail/deterioration metric significantly inferior AND no quality test rejects. Simulations use fixed-horizon z-tests for NI/superiority but **group-sequential tests for deterioration and quality metrics**. So "Spotify is fixed-sample" is only half true; their deterioration guardrails are already sequential. | Correct with caveat |
| Eppo: Howard et al. CS, N_tune = 10,000; guardrail cutoff compared to the CS lower bound, yellow/red states, no joint error statement | Verified on both Eppo pages. | Verified |
| Statsig: mSPRT (Zhao et al.); "an early significant result on some metrics doesn't guarantee enough power to detect regressions in other metrics" | Verified. Statsig also explicitly recommends limiting early decisions to cases where few metrics matter. | Verified |
| Statsig AI Evals shadow-runs candidates on live traffic | Verified: "shadow-run 'candidate' versions without exposing users to them." No statistics described. | Verified |
| LaunchDarkly checks guarded rollouts "multiple times per minute" with sequential testing; multi-metric logic unspecified | Verified verbatim. | Verified |
| GrowthBook: asymptotic CS (Waudby-Smith et al.), N* default 5,000, nothing on guardrails | Verified. | Verified |
| Lindon & Malek is NeurIPS 2022 main track | arXiv 2011.03567 lists "36th Conference on Neural Information Processing Systems (NeurIPS 2022)". Main-track status not independently confirmed by me (proceedings page not opened). | Verified venue; track UNVERIFIED by me |
| Koning & van Meer "Anytime validity is free" is a JRSS-B advance article | arXiv page shows no journal reference (latest v. Dec 2025). Cite as preprint unless the journal page is opened. | UNVERIFIED as journal |
| Huang arXiv:2609.07785 uses paired bootstrap, 2-pp margin, linear λ with switch at 0.0514 | Abstract confirms estimand-aware procedure, "stated uncertainty rule and practical margin", cost rule, and the same three benchmarks. The specific numbers (paired bootstrap, 0.0514) are from the prior agent's full-text read; not re-verified here. | Abstract verified; numbers UNVERIFIED by me |
| Kotawala: anytime-valid paired-Bernoulli e-process, clustering | Abstract mentions anytime-valid sequential testing and subject-level clustering; no ties, no hierarchy. | Verified |
| Lindon & Kallus 2026 does not treat paired designs | Abstract: design-based, calendar-time cumulative reward, arm-level CS combination; no mention of pairs/clusters. | Verified |
| Li-Fan-Yang 2026 is fixed-sample, IUT-inverted worst-case NB | Verified from abstract ("large-sample results"). | Verified |
| PEAK (Cho, Gan, Kallus) is ICML 2024, composite means of multiple streams, avoids union bounds by averaging | Verified from abstract. | Verified |
| HAL: 21,730 rollouts, ~$40k, higher reasoning effort reduces accuracy in the majority of runs | Verified from abstract. "Fewer than one-third of models on the frontier" is not in the abstract; only a search snippet supports it. | Partly UNVERIFIED |
| Replay: paired deploys 96.2% (median 805), cross-arrival 33.4% (median 1,172), final NB 0.111 vs 0.051; retail paired +0.067 vs cross-arrival -0.014; cross-arrival harm gate 3.4% | `results/replay/replay_results.csv` (written 21:26, same minute as the memo) says: paired 96.2% deploy, **median 846**, mean final NB **0.1035**; cross-arrival **33.0%**, median **1,157**, NB 0.0514; retail paired NB **+0.0573**, cross-arrival **-0.0124**, cross-arrival harm rate **2.6%**. Every number except 96.2% and 0.051 differs. Abstract C's "median of 805 paired runs" is therefore not reproducible from the shipped table. | **Mismatch: fix before any number leaves the repo** |
| Simulation headline numbers (0.45% = 9/2,000; 31.05%; 96.85%; 0/2,000; boundary 0.75%/0.45%; cluster coverage 95.25 vs 55.65; adaptive 93.0 vs 1.1) | All match `simulation_results.csv` and `stress_results.csv`. | Verified |
| Online-methods numbers (multinomial null 0.000, betting 0.006-0.008; efficiency-gain power 0.601 vs 0.966; widths 0.650/0.242/0.086 vs 0.562/0.179/0.055 vs 0.731/0.192/0.065) | All match `online_methods_results.csv` and `cs_width.csv`. Note `cs_width.csv` is for the **3-cell** stream only. | Verified, scope caveat |
| Async: 41.285 → 22.363 ticks; 99.7% deploy; 0.6% null | Matches `async_results.csv`. | Verified |
| Public reanalysis numbers (0.528 [0.423, 0.629], -0.072 [-0.140, -0.004], 0.259, -0.126 after swap, SWE -0.113) | Match `decision_matrix.csv` / `public_results.tex` to rounding. | Verified |
| HAL leaderboard cost double-counting (~2x) | Memo itself marks it UNVERIFIED. Do not put it in the main text without opening the Weave records again and checking the current website. | UNVERIFIED |

---

## 2. Fatal flaws (would drive a reject from an experimentation practitioner-reviewer)

### F1. On the paper's own real data, the guarded rule never makes a decision that success-only does not already make

I recomputed from `results/benchmarks/decision_matrix.csv` (25 contrasts: 9 tau2, 1 SWE, 15 HAL). The guarded rule (`dec_guarded`) decides in 10 contrasts. In **all 10**, `dec_success_only` reaches the **same** winner (telecom GPT-4.1 vs o4-mini; SWE; eight HAL scaffold/model contrasts where the success difference is 0.18-0.40). In the 15 remaining contrasts the guarded rule is undecided; the nine "priority inversions" and the three "hierarchy decides where success does not" cases (airline) all end in "undecided" once the success guardrail is applied. The `decision_matrix_summary.json` headline "pairs_where_rules_disagree: 19" counts disagreements between the *unguarded* hierarchy and other rules; the proposed *guarded* decision agrees with success-only in every decided case.

Why this is fatal for the current positioning: the thesis (memo Section 1) sells "the missing decision layer with guarantees". A practitioner reads the disagreement table and concludes the opposite: whenever the framework deploys, a plain success-superiority test on the same data would have deployed the same system; whenever the hierarchy disagrees with success, the guardrail blocks it. The hierarchical score therefore contributes no deployment on any of the 25 real contrasts. That is exactly the incumbent Spotify/Eppo behaviour (ship on a superior success metric, block on a failed guardrail), and it is what Fu 2026 / Verbeeck 2019 predict.

What would resolve it: produce at least one real (or prospectively collected) contrast, and one calibrated simulation family, where the guarded hierarchical rule ships something a per-metric "success NI + cost superiority" conjunction does not (or blocks something it ships), and argue under a declared objective that the guarded decision is the right one. The `efficiency_gain` simulation is the only place this happens today, and there the per-metric conjunction (cost CS superior AND success CS non-inferior) would also ship; it is not in the comparator set (R2-E4 already notes the "success-NI-plus-efficiency" rule was never run). Until that comparator exists, "the hierarchy adds nothing over per-metric guardrails" is the default reading.

### F2. The one "new" theorem (3(b), drifting gates) is mis-stated in the memo and, correctly stated, is Bonferroni

Memo Section 3, Theorem 3(b): "a sequence of distributions exists under which per-gate alpha deploys while some gate is currently false with probability → 1". This cannot be true for the error event as defined in `theory.tex` (Theorem `thm:drift_gate`: deploy at n while some running-average gate mean μ̄_jn ≤ c_j). If the rule deploys at n and μ̄_jn ≤ c_j, then L_jn > c_j ≥ μ̄_jn, i.e. gate j's confidence sequence has failed to cover. So the error event is contained in the union of the J+1 per-gate coverage failures and has probability at most (J+1)·α, uniformly over all drift sequences. The maximum inflation of per-gate α is a factor of J+1, not divergence to 1. The planned "alternating-block counterexample" can at most exhibit error between α and (J+1)α.

Consequence: Theorem 3(b) reduces to "under drift you need a union bound across gates" — Bonferroni across guardrails. GrowthBook already warns that "choosing too many guardrail metrics increases the chance of false positives", Optimizely applies FDR across metric tiers, and the industry file records (UNVERIFIED snippet) that Spotify Confidence Bonferroni-corrects across metrics. A reviewer from this community will not credit this as new, and the "→ 1" claim, if it appears in the paper, is a mathematical error that costs soundness points. The stationary result 3(a) is fine but, in production, traffic is never stationary (day-of-week, model-provider latency shifts), so the regime where "no alpha split is needed" is the regime practitioners are never in.

What would resolve it: state 3(b) as "per-gate α gives at most (J+1)α under drift; the bound is attainable up to constants" with an explicit construction showing error strictly above α, and drop the divergence language. Better: replace the union bound with a single e-process over the conjunction (PEAK-style averaging, which the memo already lists as optional) and show it beats Bonferroni in stopping time — that would be a genuinely new, useful result for guardrailed rollouts.

### F3. The online design asks platforms to change their randomization for no demonstrated benefit

The online estimand is τ_pop (Mao 2018): a functional of the two arm marginals. Under ordinary unit-level randomization (what Statsig/Eppo/LaunchDarkly do), τ_pop is identified and consistently estimated by the all-pairs two-sample U-statistic; the disjoint-pair AB/BA blocking is not needed for identification. The memo concedes the "disjoint-pair vs all-pairs efficiency ratio on real score distributions is still to be computed" (E8). So the paper currently asks a platform to (i) pair consecutive arrivals, (ii) randomize orientation within pairs, (iii) throw away the cross-pair comparisons, and (iv) accept an unmeasured variance inflation, in exchange for finite-sample validity that the asymptotic CSs already in production (Eppo, GrowthBook, Adobe) do not appear to need at production sample sizes. The stated benefit, "drift robustness", is semantic: the covered quantity under drift is a running average of conditional means, which is not what an operator wants to know (current effect), and which the incumbents' asymptotic CSs also cover under mild conditions.

What would resolve it: run E8 and either (a) show the disjoint-pair CS is within, say, 10-20% of the all-pairs width on tau2/SWE score distributions, or (b) provide a CS for the all-pairs U-statistic on standard unit-randomized logs (Cai-Hu-Li asymptotic, or a finite-sample version) and present the paired design only for the shadow-execution regime where it is natural. If the paper cannot show the paired design is at least as good as what platforms already log, drop it from the main claims.

---

## 3. Major concerns

### M1. Stale replay numbers in the memo and Abstract C
See the ledger: 805 vs 846, 33.4% vs 33.0%, 1,172 vs 1,157, 0.111 vs 0.1035, +0.067 vs +0.057, -0.014 vs -0.012, 3.4% vs 2.6%. Either the CSV was regenerated after the memo was drafted, or the memo copied a superseded run. Every number in the abstract must be regenerated from the shipped manifest; the reproducibility rubric item R2 fails as it stands.

### M2. The headline "paired and cross-arrival targets differ in sign in retail" is not statistically established
From `decision_matrix.csv`, retail GPT-4.1 vs o4-mini: τ_* = -0.058 [-0.171, +0.055], τ_pop = +0.015 [-0.050, +0.081]. Both intervals include zero; the sign difference is a point-estimate artefact of two noisy estimates. The replay sign flip (+0.057 vs -0.012, sd 0.021 across replays of 2,000 pairs) is the same noise viewed through a replay lens. The memo (C1, objection 3, all three abstracts) promotes this to a headline. A practitioner will ask for the paired difference τ_* - τ_pop with an interval; the summary JSON reports mean |τ_* - τ_pop| = 0.052 and "sign_differs_star_vs_pop: 2 of 25". Report it that way, or find a contrast where both intervals exclude zero on opposite sides.

### M3. "Three rules, three winners" in retail is mostly noise between GPT-4.1 and o4-mini
`tau2_rankings.csv`: success 0.741 (GPT-4.1) vs 0.715 (o4-mini), NB sum 0.525 vs 0.586. The pairwise NB between them is -0.058 [-0.171, +0.055] and the success difference is +0.026 [-0.047, +0.099]. The only well-separated fact is that Claude-3.7 is ~5-7 pp more successful and ~6x more expensive (0.335 vs 0.058 USD per task). That is a real trade-off, but a product owner already sees it from two columns; the NB of 0.53 adds a number, not a decision, because the guardrail then says "undecided".

### M4. No comparison with the incumbent decision rule
The comparator set (repeated Wald, group Wald, fixed Wald, normal mixture, multinomial) omits the rule practitioners actually run: per-metric sequential CS on success (non-inferiority at -3 pp) plus per-metric sequential CS on cost (superiority), conjunction, no pairing. That rule is implementable on today's Eppo/GrowthBook configuration. The paper must show, scenario by scenario, where its decision and stopping time differ from that rule and why the difference is desirable. Without it, the `efficiency_gain` result (guarded betting 96.85%, median ~3,750 pairs) is uninterpretable: a per-metric cost CS with a 5% tolerance would resolve a 0.55x cost ratio in far fewer pairs.

### M5. Stopping time and cost are governed by the guardrail margin, not by the win statistic
`online_methods_results.csv`, efficiency gain: win-only betting deploys at median 100 pairs; guarded betting at median 3,750 pairs (mean 4,362 pairs = ~8,700 agent executions) because the -3 pp success NI gate must resolve. The memo's own Proposition A10 says a narrow guardrail margin dominates sample size. So the practical cost of a decision is set by the NI margin and is identical to what Spotify already documents (power 1-β/(G+1)). Report decision cost in agent executions and dollars per scenario, alongside the per-metric conjunction, and say plainly that the hierarchy does not speed up decisions.

### M6. Delayed outcomes: the completed-prefix rule has head-of-line blocking; the partial-evidence envelope requires deterministic enclosures that production outcomes lack
Proposition A3 displays only fully matured enrollment prefixes: one slow pair (a 24-48 h resolution window, a CSAT survey that never returns) blocks the display of every later pair. The async envelope helps only when partial traces yield **guaranteed** bounds on the final score. For verifier success and metered cost that holds; for the delayed outcomes practitioners actually care about (resolution confirmed by no-reopen, CSAT at 2-8% response, escalation) there is no deterministic enclosure, and the async novelty file itself says "if agent success is only a prediction or a judge's fallible label ... retain all possible final labels", which makes the bound vacuous. The async simulation uses one synthetic telemetry mechanism with 100 pairs enrolled per tick and a 20-tick horizon; that is far from a production reveal process. Lindon & Kallus 2026 handle treatment-dependent delay for unit-level randomization without pairing; the paper must explain what a platform gains by waiting for pairs instead of using their arm-level construction.

### M7. Multinomial "one set for everything" is priced only at d = 3 and only under i.i.d.
`cs_width.csv` widths (0.650/0.242/0.086) are for a 3-cell stream. Theorem 1 is pitched on the 3^T-cell partition (27 cells for T = 3). A uniform Dirichlet prior over 27 cells, many empty, will widen the set substantially; no number exists. The i.i.d. requirement also means the "simultaneous reporting device" is inapplicable to the online regime the paper is about (drift, adaptive orientation). Run the width experiment on the actual 3^T design, with the informative prior, before claiming simultaneity "at one α".

### M8. The stationary/drift dichotomy is not operationally usable
An operator cannot verify stationarity. So the honest protocol is always the drifting one: α/(J+1) per gate and a running-average target. State that up front and compare against Bonferroni-corrected per-metric CSs (the actual incumbent) rather than presenting the no-split stationary theorem as a benefit.

### M9. Evidence base is historical, single-vintage and small
2024-2025 runs; four shared seeds per tau2 domain (R2-E1); tau2 tasks since corrected (tau3); 114 vs 115 retail-task discrepancy; SWE dominated by Django/SymPy (R2-E2); HAL single trial; 2,000 rather than the protocol's 10,000 null repetitions; the only prospective data is a 12-task Haiku telecom pilot under a USD 4 cap with no results in `results/` yet. None of this is "randomized A/B of agents". Label everything "replay" (the memo does) and do not use "online" in the title if E7 does not run.

### M10. Hierarchy, tolerances and margins are illustrative, and the paper says so
5% cost tolerance, zero-call step tolerance, 3-pp success margin. Practitioners need a way to elicit these (Statsig's "how bad is bad enough"), and a reviewer will ask why lexicographic rather than the linear utility Huang already uses on the same data. The sensitivity grid shows direction robustness only (R2-E6). Include a short elicitation protocol and show decisions across the elicited range.

### M11. Interpretability for decision makers
NB = 0.53 means "in a random pair of successful runs from the two systems, o4-mini is preferred 53 pp net", mostly because cost decided 60% of retail comparisons. Operators reason in "success -7 pp, cost -83%". The paper needs a one-line translation of NB to component effects (the tier decomposition identity does this) and must lead with it; otherwise the win statistic reads as a re-encoding of two numbers that were already on the dashboard.

### M12. Judge/verifier noise is deferred, not handled
The primary tiers are verifier success and metered cost, which sidesteps judge noise, but production hierarchies put a policy/safety tier first, and that tier is LLM-judged. The label-contamination sensitivity (0/1/5%) is listed in the protocol but not executed. Without it the safety-first hierarchy the introduction motivates is untested.

---

## 4. What is genuinely new versus restated (my assessment)

| Item | Verdict | Closest prior (opened) |
|---|---|---|
| Hierarchical kernel, NB/WR/WO relations, ties/thresholds | Restated | Buyse 2010; Pocock 2012; Dong 2020/2023; RADAR |
| Primary-outcome inversion (NB → 1 with success -ε) | Restated (mirror of Fu 2026; Verbeeck 2019) | Fu 2026; Verbeeck 2019 |
| Population vs individual vs same-covariate win estimands; cyclic non-identification | Restated | Mao 2018; Even & Josse 2026 |
| Exact-matching offline target τ_*(task); shared-seed lemma (1-1/R)θ_ind + (1/R)θ_coupled | Small, useful adaptation | Even & Josse; Benz et al. coupled generation |
| Design map (offline replicate / pair-randomized single exposure / shadow) | Clarification, not theory; useful for practitioners only if paired with the U-statistic-on-standard-logs alternative (F3) | Mao; Even & Josse; Ham et al. |
| Normal-mixture and betting CS on HT-weighted pair scores | Instance of Howard 2021 / Waudby-Smith & Ramdas 2024 / Ham et al. | as listed |
| Dirichlet-multinomial CS for all win functionals | Corollary of Lindon & Malek 2022 Thm 2.4; the functional/simultaneity remark is new but "immediate", and it is wider and i.i.d.-only | Lindon & Malek 2022 |
| Stationary IUT gate, no α split | Adaptation of Berger IUT; same logic as Spotify's Decision Rule 2 | Schultzberg et al. 2024/2026; Karampatziakis 2021 |
| Drifting gate needs summed budgets | Union bound; equals Bonferroni across guardrails (see F2) | GrowthBook/Optimizely practice; Spotify Confidence (UNVERIFIED) |
| Anytime worst-case NB over a hierarchy family | Small adaptation (union/IUT over CSs) | Li, Fan & Yang 2026 (fixed-sample) |
| Completed-prefix display; partial-evidence envelope | Adaptation; the pathwise transfer and positive-factor monotonicity are elementary; precedents credited | Henzi & Ziegel 2022 (+correction); Choe & Ramdas; Lindon & Kallus 2026 |
| Empirical: preference/success reversals on tau2; hierarchy-vs-success disagreements | New descriptive finding, but not decision-changing under the paper's own guarded rule (F1) | Huang 2026 (same data, linear utility); Kotawala 2026 |
| Simulation: invalid repeated-Wald vs valid betting | Known; not persuasive to practitioners who already use CSs | Johari et al. 2017/2022 |

Net: the paper is a careful protocol paper assembling known parts. Its only candidates for a contribution score above 2 are (i) a demonstrated case where the guarded hierarchical decision is both different from and better than the per-metric conjunction, and (ii) a single-e-process conjunction that beats Bonferroni under drift. Neither exists yet.

---

## 5. Concrete changes, in priority order

1. **Add the incumbent comparator** ("success NI CS AND cost-superiority CS, unit randomization, Bonferroni across gates") to every simulation, the replay and the decision matrix; report decisions, stopping time in pairs and in agent executions, and dollars. If it matches the guarded rule everywhere, reposition the paper as a reporting/estimand protocol, not a decision layer.
2. **Find or construct the decision-changing case.** A hierarchy with a safety tier first, where a cheaper system has a rare but real compliance regression that per-metric cost/success gates miss but the hierarchy plus compliance guardrail catches, or the reverse. Show it in simulation calibrated to tau2 cell frequencies and, if E7 runs, on the Haiku stream.
3. **Fix Theorem 3(b)**: replace "probability → 1" with the (J+1)α bound and an attainability construction; or supersede it with a PEAK-style single e-process for the conjunction and show a stopping-time gain over Bonferroni.
4. **Regenerate every number in the memo and abstracts from the shipped CSVs** (M1). Add a manifest line mapping each abstract number to a file/row.
5. **Run E8** (all-pairs vs disjoint-pair variance ratio on real score distributions) and add a CS for the all-pairs U-statistic on standard unit-randomized logs; present the paired design as the shadow-execution case only.
6. **Report τ_* - τ_pop with an interval**; demote the "sign flip" unless it is established.
7. **Price the 3^T multinomial set** with uniform and informative priors; state that it is offline/i.i.d. only.
8. **Delayed outcomes**: add one reveal model with judged/human outcomes (no deterministic enclosure) and show honestly that the envelope degrades to the completed-prefix rule; compare to Lindon & Kallus arm-level CSs.
9. **Execute the label-contamination sensitivity** with a judged safety tier at top priority.
10. **Elicitation box** for tolerances and margins; show the decision map across the elicited range instead of a single 5%/3-pp point.
11. **Reference hygiene**: attribute the "5 guardrails / below 40%" figure to the Spotify blog (not the arXiv paper, which says 10 guardrails / 11%); cite Koning & van Meer as a preprint; keep the HAL "one-third on frontier" and HAL cost double-counting out of the main text until verified; note that Spotify's deterioration guardrails are already group-sequential.
12. **Title/abstract**: do not use "continuous agent evaluation" or "online" as if live A/B data existed; "randomized stream replay" is the honest term the memo already uses.

---

## 6. Predicted outcome if the paper delivers exactly the memo's plan

Soundness 2-3 (the "→ 1" claim would be caught; otherwise correct), Presentation 3, Contribution 2. The empirical section shows disagreements between rules but no case where the proposed rule improves a decision; the theory is a union bound over known confidence sequences; the online design is unnecessary for the estimand it targets. Predicted ICLR rating: 4 (marginally below threshold; reject without the changes in Section 5). With items 1-5 executed and one convincing decision-changing case, 6 is reachable.
