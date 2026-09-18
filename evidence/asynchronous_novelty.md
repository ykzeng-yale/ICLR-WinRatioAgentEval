# Asynchronous partial-score evaluation: theory and novelty assessment

Date: September 18, 2026 UTC. Ownership for this task: only this file and `paper/asynchronous.tex`; existing sources and manuscript are read-only to this agent.

## Mathematical conclusion

The proposed construction is valid under explicit assumptions and materially improves the protocol's handling of incomplete episodes. It retains all enrolled pairs with guaranteed bounds on their eventual frozen-horizon scores. No independence between outcome and reveal time is required for the pathwise transfer argument. The key qualification is that the complete latent score sequence must already satisfy its enrollment-order confidence-sequence or betting assumptions in a specified filtration. Informative reveal alone does not invalidate those assumptions, but arbitrary production adaptation/interference can.

There are two different mathematical claims:

1. A full-score all-prefix confidence sequence transfers to calendar-time lower/upper bounds by replacing each unobserved score with a guaranteed interval. Width equals the ordinary full-score width plus the average unresolved-score width.
2. A positive-stake product evaluated at lower score bounds is bounded above by the corresponding full-score product. A partial-wealth threshold crossing therefore implies a crossing somewhere in the full enrollment-order process. This proves anytime threshold error control. It does **not** by itself make the calendar-time partial wealth an e-process or give expectation at most one at every calendar stopping time.

The distinction is central: the two time filtrations need not be interchangeable, and a general expectation-valid e-process claim would require additional conditions.

## Results included in paper/asynchronous.tex

- Full definition of latent enrollment filtration versus actual calendar observations.
- Simultaneous guaranteed completion intervals, with an alpha-plus-eta extension if all enclosures hold only on a common probability-1-minus-eta event.
- Full pathwise proof of a CS using all enrolled scores; it covers the corresponding running conditional target.
- Exact uncertainty-width decomposition and a bound of 2 B M/n when M of n bounded scores remain wholly unresolved.
- Full positive-mixture lower-wealth threshold proof. It explicitly avoids claiming the partial process is a calendar-time e-process.
- Optional prefix envelope `max_{n<=N(t)} lower_wealth(n,t)` with the same alpha guarantee, because every prefix is dominated by the same latent full-score process. This envelope includes a completed-prefix test and therefore cannot detect later than that baseline, holding its score/bet/monitoring choices fixed. Merely using all enrolled N(t) does not have this speed guarantee.
- Feasible-completion construction of hierarchical score bounds and component difference bounds. HT weighting is a positive known multiplier.
- Agent-specific early-resolution example: A has completed successfully at cost1; B has already spent2 but remains unresolved. For success-first then lower-cost preference at 5% tolerance, A is guaranteed to win whether B later succeeds or fails, provided no higher unresolved tier can reverse the comparison.
- Almost-sure eventual confidence-bound decision when stationary gate gaps are positive and the average unresolved width vanishes. A single permanently unresolved early pair need not block inference.
- Log-wealth penalty bounded by `lambda/[1-lambda(B+c)] * sum(X_i-lower_i)`, supplying a corresponding consistency condition for a preselected stake with positive full-score log growth.
- Stationary conjunction alpha control versus drifting simultaneous gate budgets, plus explicit fixed-horizon versus calendar-time estimand distinction.

## Prior art discovered and verified

### Direct delayed-outcome prior

Michael Lindon and Nathan Kallus, **Design-Based Anytime-Valid Inference for Randomized Experiments with Delayed Outcomes and Staggered Entry**, arXiv:2603.25971v2, May29,2026. [Latest full text](https://arxiv.org/html/2603.25971v2), [abstract](https://arxiv.org/abs/2603.25971).

Their target is sample cumulative reward as a function of calendar time under fixed potential outcome times/values and randomized assignment. They study arm-specific filtrations, show a direct treatment-effect martingale obstruction, and combine arm-level confidence sequences. Section4 describes asymptotic CS construction; do not characterize every guarantee in that paper as exact finite-sample. Our target is a complete fixed-horizon enrollment-prefix score, conservatively bounded while pending. These are different estimands and mechanisms. Their work rules out any broad claim that anytime inference with treatment-dependent delays is new here.

### Very close worst-case pending-outcome precedent

Alexander Henzi and Johanna F. Ziegel, **Valid sequential inference on probability forecast performance**, *Biometrika*109(3):647–663,2022. [Publisher](https://academic.oup.com/biomet/article/109/3/647/6375942), [DOI10.1093/biomet/asab047](https://doi.org/10.1093/biomet/asab047), [arXiv2103.08402](https://arxiv.org/abs/2103.08402).

Section3 gives a delayed forecast stopping rule that remains above threshold for every possible value of the pending outcomes. This is a close conceptual predecessor to lower-bounding wealth across feasible completions. Our protocol uses bounded hierarchy/component scores, informative reveal schedules under the latent-score assumptions, and partially resolved tiers. This is a specialization of worst-case completion principles. It is not established as a strict generalization of the forecasting result, whose forecasting-time conditional null need not match our latent enrollment filtration.

### Correction must accompany the forecast citation

Henzi and Ziegel, **Correction to: 'Valid sequential inference on probability forecast performance'**, *Biometrika*109(4):1181–1182,2022. [Publisher](https://academic.oup.com/biomet/article/109/4/1181/6696629), [DOI10.1093/biomet/asac043](https://doi.org/10.1093/biomet/asac043).

The correction rejects the original general supermartingale/optional-stopping claim for forecast lags greater than one. It retains the specific worst-case pending-outcome stopping rule's type-I control. This reinforces why our proof establishes an event inclusion and threshold guarantee and does not assert a calendar-time martingale or e-process expectation guarantee. The correction's substance was inspected directly in indexed publisher content.

### Filtration transfer is an established separate issue

Yo Joong Choe and Aaditya Ramdas, **Combining Evidence Across Filtrations**, arXiv:2402.09698. [Primary abstract](https://arxiv.org/abs/2402.09698).

They study combining e-processes built in different filtrations and adjustment for lifting evidence into a finer filtration. Their abstract establishes that validity in a coarser filtration does not automatically transfer to a finer one. Version 5 Section 3.1 (Lemma 1 and Theorem 1) directly establishes free p-process and confidence-sequence lifting through time-uniform/random-time event equivalence; Section 5.2 discusses delayed forecasting. This is a structural precedent for our pathwise threshold transfer, beyond a warning about exchanging filtrations. We do not establish a new general lifting theorem.

## Suggested citation keys and metadata for root integration

```bibtex
@misc{lindon2026delayed,
  title={Design-Based Anytime-Valid Inference for Randomized Experiments with Delayed Outcomes and Staggered Entry},
  author={Lindon, Michael and Kallus, Nathan},
  year={2026}, eprint={2603.25971}, archivePrefix={arXiv},
  url={https://arxiv.org/abs/2603.25971}, note={Version 2, May 29, 2026}
}
@article{henzi2022forecast,
  title={Valid sequential inference on probability forecast performance},
  author={Henzi, Alexander and Ziegel, Johanna F.},
  journal={Biometrika}, year={2022}, volume={109}, number={3}, pages={647--663},
  doi={10.1093/biomet/asab047}
}
@article{henzi2022correction,
  title={Correction to: `Valid sequential inference on probability forecast performance'},
  author={Henzi, Alexander and Ziegel, Johanna F.},
  journal={Biometrika}, year={2022}, volume={109}, number={4}, pages={1181--1182},
  doi={10.1093/biomet/asac043}
}
@misc{choe2024filtrations,
  title={Combining Evidence Across Filtrations},
  author={Choe, Yo Joong and Ramdas, Aaditya},
  year={2024}, eprint={2402.09698}, archivePrefix={arXiv},
  url={https://arxiv.org/abs/2402.09698}
}
```

The Lindon/Kallus work appears under an ICML2026 title in search indexing, but official proceedings metadata was not verified in this bounded task. The arXiv citation is verified; do not invent an ICML volume/page record.

## Novelty assessment and empirical burden

This is a more operationally compelling online contribution than a protocol that waits for the entire completed enrollment prefix. It explicitly uses agent trace structure to certify pair outcomes early and quantifies the penalty of unresolved information. However, the transfer proof and coordinatewise product monotonicity are elementary, and worst-case pending-outcome stopping already exists. The construction alone does not establish a strong new general probability theorem or guarantee ICLR-level novelty.

A convincing experiment should show the incremental value of **partial hierarchy resolution**, not only compare against an invalid completion-only analysis. At equal false-deployment control and frozen targets, compare (i) fully observed oracle, (ii) complete enrollment prefix, (iii) all-enrolled partial bounds, (iv) partial prefix envelope if implemented, and (v) completion-only analysis explicitly labeled selection-biased. Distinguish partial outcome certificates from full completion. Report calendar time, enrolled pairs, agent executions, unresolved counts/width, and failure/nondeployment rates. Include a null with outcome-dependent delays, a valid positive alternative, an adversarial unfavorable-late scenario, and a reveal pattern where early tier resolution helps despite an unresolved first episode. A basic all-enrolled implementation must not claim the envelope's pathwise speed dominance.

Deterministic or protocol-guaranteed enclosures are essential. If agent success is only a prediction or a judge's fallible label, construct a separate simultaneous measurement guarantee or retain all possible final labels in the bounds. Neither early apparent success nor absence of observed safety violations is automatically final. New stochastic simulations validate the assumed mathematical model; they cannot establish that a live deployment harness produces valid enclosures without a trace-level audit.
