# Closest sequential-inference papers and reusable simulation code

Accessed September 21, 2026 UTC. Bounded source review using the `fan-paper-review` approach: six closely related papers/items and three inspected author repositories. Selected full-text sections and source functions were read; this is not a claim to have audited every proof or run the authors' experiments. No package installation, simulations, model calls, or changes to the paper, owner experiment directories, or Git state were made.

**Main recommendation:** add a properly specified empirical-Bernstein **running-mean** full-score reference from `comparecast`, using the same latent scores, prefix, error allocation, and legal looks. Do not substitute the similarly named predictable-mixture or hedged-capital intervals for a changing unweighted running mean. Keep any new pending-outcome EB adaptation outside the present primary until separately reviewed.

## Relationship to the existing review

Reopened `evidence/asynchronous_novelty.md`, `evidence/async_experiment_protocol.md`, and relevant entries in `paper/references.bib`. Lindon–Kallus, Henzi–Ziegel plus correction, and Choe–Ramdas filtration lifting were already explicitly reviewed in the September 18 asynchronous ledger. Waudby-Smith–Ramdas betting is already cited. These are **renewed/deeper checks, not newly discovered prior art**. The closest additional comparator identified here is Choe–Ramdas **Comparing Sequential Forecasters**, absent from the inspected bibliography. The new practical contribution of this audit is its exact running-mean implementation and reuse boundary, rather than a new broad novelty claim.

## Six primary-source checks

### 1. Waudby-Smith and Ramdas: Estimating means of bounded random variables by betting

Sources: [arXiv v7, August 25, 2022](https://arxiv.org/html/2010.09686v7); [published JRSS B article](https://doi.org/10.1093/jrsssb/qkad009), cited in the local bibliography as 2024, 86(1):1–27. Read selected full text: Proposition 2, betting constructions, Appendix D simulation details, and E.5; publisher metadata was not independently re-audited here.

**Literature facts:** the common-mean construction assumes bounded observations with the same conditional mean; independence is unnecessary. Its non-i.i.d. variance-shift example changes Beta(10,10) observations to Bernoulli(1/2), retaining mean 1/2. It also develops a distinct without-replacement construction. Width plots average five draws; those plots are not high-precision coverage estimates. Its strong empirical performance is not a guarantee for an arbitrary drifting unweighted mean.

**Design implication:** use the actual author implementation as a strong comparator in a separately labeled constant-conditional-mean panel, including a variance shift. Do not count failure under an unsupported changing target as a failure of its stated theorem. The finite-population option requires the specified sampling design, not merely a finite task roster.

### 2. Choe and Ramdas: Comparing Sequential Forecasters

Sources: [arXiv v6, November 9, 2023](https://arxiv.org/html/2110.00115v6); [Operations Research article](https://doi.org/10.1287/opre.2021.0792). Read selected full text: Sections 4.2–4.3, Theorem 2, Section 5.1, and Appendix I.4. An older v4 was initially opened; the relevant theorem and experimental specifications were then checked in v6.

**Literature facts:** Theorem 2 covers the time-varying average conditional score difference using bounded scores, predictable centers, and a sub-exponential boundary applied to cumulative squared prediction residuals. The score bound is not replaced by a plug-in Gaussian variance assumption. Simulations include 10,000-round non-i.i.d. Bernoulli streams with sharp changes, comparing finite-sample Hoeffding/EB sequences, asymptotic sequences, and fixed-time intervals. The authors freeze a default intrinsic-time tuning value of 10 after preliminary comparisons.

**Design implication:** this is the closest strong full-score baseline for our unweighted running conditional mean. Its confidence-sequence guarantee is the relevant object; a weak-null e-process or fixed-time interval should not be silently substituted for it. Preserve prefix-specific truth under drift and report cumulative miscoverage, rather than only terminal coverage.

### 3. Choe and Ramdas: Combining Evidence Across Filtrations

Source: [arXiv v5, March 15, 2026](https://arxiv.org/html/2402.09698v5); abstract record says accepted by JRSS B. Read selected full text: Section 3.1 lifting lemma/Theorem 1, Section 5.2, Appendix H.2, and the rejection-power versus e-power discussion.

**Literature facts:** time-uniform event/p-process validity can transfer to a finer filtration; expectation validity of an e-process does not transfer automatically. The paper gives adjust-then-combine constructions. Its delayed forecast comparison separates a valid sequential test from a genuine evidence process and compares lagged, p-merging, and adjusted approaches. It distinguishes rejection probability from expected log evidence.

**Design implication:** our calendar-time enclosure argument must retain its threshold/event interpretation. Do not average coarse-filtration wealths and label the result a calendar-time e-process. No adjustment is required merely to repeat an already established simultaneous pathwise confidence bound; adjustment and its power cost arise for the different e-process claim. Fixed-lag forecasting code is an instructive optional test, not automatically an informative, variable-delay agent baseline.

### 4. Henzi and Ziegel: Valid sequential inference on probability forecast performance

Sources: [arXiv v3, July 1, 2022](https://arxiv.org/html/2103.08402v3); [Biometrika article](https://doi.org/10.1093/biomet/asab047). Read full-text selections: Section 3.2, lagged stopping rule, Appendix A.2, and Sections 4.1–4.2.

**Literature facts:** for delayed binary forecasts the stopping rule accounts for every possible pending outcome before declaring significance. Simulations compare mixtures of prechosen alternatives, stopped and unstopped evidence, and lags 1–3; the stationary ideal-forecast example supplies a setting where a classical competitor's assumptions hold. The forecasting null concerns conditional score dominance, not our generic hierarchy-score running mean.

**Design implication:** worst-case pending completion is direct prior art. A useful falsification case is evidence that appears favorable before an unfavorable pending outcome arrives. Copying its fixed-lag forecast test directly into the hierarchy experiment would change the statistical question. The author-linked `eprob` repository was located, but its source was not included among this audit's three pinned code reviews.

### 5. Henzi and Ziegel: Correction to the preceding article

Source: [Biometrika 109(4):1181–1182, DOI asac043](https://academic.oup.com/biomet/article/109/4/1181/6696629). Direct opening failed once; the publisher's indexed full correction text, including revised Proposition 2 and the stopping-rule conclusion, was accessible and read. This is **not abstract-only evidence**.

**Literature fact:** the original general supermartingale statement is false for lag greater than one. The correction retains the specially protected stopping rule's type-I bound and supplies lag-adjusted expectation validity. It does not revoke all empirical findings.

**Design implication:** cite the correction with the original article. Test an adversarial reveal pattern against naive thresholding, and identify which guarantee is checked: current-prefix coverage, ever-crossing probability, or stopped expected evidence. Passing one does not establish the others.

### 6. Lindon and Kallus: Design-Based Anytime-Valid Inference for Randomized Experiments with Delayed Outcomes and Staggered Entry

Source: [arXiv v2, May 29, 2026](https://arxiv.org/html/2603.25971v2). Read selected full text: Theorems 4.4, 4.6 and 4.9, Section 5, and Appendix A.2.

**Literature facts:** the target is calendar-time cumulative counterfactual reward. The directly observable IPW analysis combines arm-specific processes; Theorems 4.6/4.9 are **asymptotic** confidence sequences. The simulation uses 500 staggered entrants, balanced randomization, arm-dependent never-event probabilities, earlier treatment arrivals but smaller rewards, and calendar-time changes. The supported event-time martingale argument does not automatically justify entry-frozen AIPW augmentation.

**Design implication:** reuse the *stress mechanism* of treatment-dependent timing and eventual reversal, with our own explicitly defined bounded complete-horizon scores. Do not rank its cumulative-reward interval against ours as though both targeted the same quantity, or describe its asymptotic result as finite-sample exact. No separate implementation of this paper was audited in this bounded pass.

## Actual open-source code inspected and pinned

All three repositories' official GitHub metadata and license files identify **MIT**. Preserve their copyright/license notices if code is copied. Accessed current default-branch commits, not floating package-version claims. Paper text licenses were not audited; no paper text was vendored.

| Repository and pin | What was actually inspected | Reuse judgment |
|---|---|---|
| [gostevehoward/confseq](https://github.com/gostevehoward/confseq/tree/5ffe733ca2447a2e28c2c91f3b00086173f2ab2c), `5ffe733ca2447a2e28c2c91f3b00086173f2ab2c`, Jan 7, 2026 | License, Python-interface README, selected `betting.py` signatures/defaults and predictable-mixture implementation structure; boundary dependency interface through comparecast | `betting_cs`/`hedged_cs` are useful common-mean references; `N` selects a distinct without-replacement design. Do not confuse a running intersection for one fixed mean with intervals for changing means. Compiled boundary code was **not** audited or executed here. |
| [yjchoe/ComparingForecasters](https://github.com/yjchoe/ComparingForecasters/tree/52748c86e0429a9612dc79892c3be6156a524132), `52748c86e0429a9612dc79892c3be6156a524132`, Oct 24, 2023 | License, README, full `confseq_eb` function and imports, related `confseq_h`/predictable-mixture signatures, diagnostic truth and cumulative-event functions, utility import/bounds interface | Best immediate full-score reference. Its `diagnostics.py` distinguishes cumulative miscoverage from sign-error summaries. Its forecast-specific DGP/score functions are not needed for our ternary-score input. |
| [yjchoe/CombiningEvidenceAcrossFiltrations](https://github.com/yjchoe/CombiningEvidenceAcrossFiltrations/tree/279128f222e09f04484a1ccb14537431752a16ea), `279128f222e09f04484a1ccb14537431752a16ea`, Mar 15, 2026 | License, README structure, `ecombine/calibrators.py` calibrator/adjuster functions, process entry points | `adjuster` explicitly uses a running maximum by default. Reuse only after specifying the base process, common null and filtrations. It is not needed to make our existing threshold-only proof valid. Not a drop-in hierarchy evaluator. |

Twenty selected small source/license files totaling 128,615 bytes were downloaded to ignored scratch; no repository clone, dependency install, data download, notebook execution or source-code execution occurred. [Repository receipt](../reviews/evidence/literature_sequential_repos_20260921.json) records repository metadata and accessed UTC times; [source receipt](../reviews/evidence/literature_sequential_sources_20260921.json) records each URL, commit, byte count and SHA-256. Downloaded ancillary files are not all claimed as fully read. Key source hashes:

- `comparecast/confseq.py`: `8ea07278021cd06223fa1aa95c3a2aa46ab5be4d5a859d5ed49b5ef5218baef4`
- `confseq/src/confseq/betting.py`: `c75ee344da46e7652cff40f42e2c879431efd629620d856cd2189ed926cae57b`
- `ecombine/calibrators.py`: `c390fdb0ceafaa09a00a5feefde2b67d8f4550ee4795cb47a57727c43d9aa7a0`

## Minimal executable comparison recommendation — proposed, not executed

Start with deterministic external-reference checks, then append the accepted reference to the **already agreed corrected CPU design** after review. No extra model study, horizon extension, or broad new grid is recommended here.

The exact [callable function](https://github.com/yjchoe/ComparingForecasters/blob/52748c86e0429a9612dc79892c3be6156a524132/comparecast/confseq.py#L108) is:

```python
from comparecast.confseq import confseq_eb

reference = confseq_eb(
    z,                         # complete latent scores in enrollment order
    alpha=alpha_gate,           # same two-sided per-gate allocation
    lo=-1.0, hi=1.0,
    boundary_type="mixture",
    v_opt=10.0,                 # chosen before validation, never None
)
lower, upper = reference.lcbs, reference.ucbs
```

This function imports `numpy`, `typing.NamedTuple`, `confseq.boundaries`, and `comparecast.utils` (`check_bounds`, `scale`, `unscale`; the latter two are not used by this function). The utility module uses NumPy and typing. Importing the whole package can pull in additional dependencies, so an isolated reference harness should record its actual imports rather than silently patching missing packages. This pass has **not** verified installation compatibility.

The inspected implementation uses a lagged empirical mean as predictable center, starting at zero; accumulated squared residuals with a floor of one; scale `hi-lo=2`; and an internal alpha/2 split for the two-sided call. Supplying `v_opt=None` selects the observed final variance clock: prohibit that in a confirmatory comparison. Do not use `confseq_pm_eb` merely because its name also includes EB: its weighted center is a different target under drift. For a one-sided alternative comparison, explicitly review allocation and set the required `c`; do not gain an apparent advantage by changing direction/error budgets unnoticed.

Recommended minimal rows and interpretation:

| Row | Target and availability | Role |
|---|---|---|
| Existing range-only and directional fixed-stake rules | Existing reviewed targets and enclosures | Preserve original comparators and separate method choice from information availability. |
| comparecast EB on full latent prefix `n` | Same unweighted running conditional mean at `n`; full outcomes available only to simulator | Strong finite-sample full-information reference; not a deployable asynchronous oracle. |
| Same EB on the complete enrollment prefix `k` | Valid for its own `mu_bar_k`; `k` may be less than enrolled `n` | Practical availability baseline. Under drift, do not score it against `mu_bar_n` or call a difference in targets a coverage failure. |
| confseq hedged/PrPl common-mean reference | Only constant-conditional-mean cells with correct scaling | Optional supplementary comparison; label out-of-domain changing-mean applications explicitly. |

Keep every legal event look, including completion-only changes; report current-prefix truth, ever-miscoverage, guarded false decisions, terminal abstention, calendar-time decision and prefix at decision. Report Monte Carlo uncertainty, not only zero/nonzero flags. Fix methods and tuning before the amended run, use shared random paths for paired comparisons, and distinguish development replay from independent calibration. Include already planned drift and informative-delay stress mechanisms; do not select new effect sizes because they make one method win.

**Separate adaptation candidate, not a primary recommendation this cycle:** a delayed EB procedure would need a reviewed bound on the latent squared-residual clock as well as on the score sum. Plugging lower endpoints into the complete-data EB function is not justified by coordinatewise monotonicity of directional betting. A fixed ex-ante center and worst-case residual bounds are a possible route, but no implementation, formal adaptation approval, or empirical validation is delivered here. Root retains review of any such extension.

The reference distinguishes running-mean confidence coverage, pointwise conditional nulls, fixed common means, and calendar cumulative effects. Its purpose is a fair stronger comparison, not to manufacture a deployment or reopen accepted baseline evidence. Readiness and execution permissions remain with the coordinator.
