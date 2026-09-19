# tau2 open-model stream: protocol addendum, Round 10 (what the replay analysis can claim)

**Status.** Written 2026-09-19 by the experiment owner in answer to the root session's Round 10 audit of PR 8 (Finding 3, "Airline repeated seeds and conditioning require further narrowing", and section 5). It is POST HOC: the collection was finished and all 196 outcomes had been analysed when it was written. It **narrows** claims and adds no outcome, arm, task, stopping rule or model call; no frozen file, raw file or log is edited. Where this addendum disagrees with `protocol_addendum_round9.md` section (b), with `protocol.md` or with `results/tau2_open/report_final.md` on the scope of an inferential claim, this addendum governs. Numbers quoted here come from `results/tau2_open/round10_handoff_numbers.json` (key `orientation_randomization_reading`), written by `experiments/tau2_open/make_round10_handoff.py` from `design.json` and `episodes.csv` with the frozen scoring functions.

## 1. What Round 9 (b) got wrong

**1.1 The two tau2 trial seeds are reused across ALL tasks.** tau2 draws one seed per trial index from `--seed 300` (`runner/batch.py:742-743` at commit `b7ea907`): 626729 for trial 0 and 373753 for trial 1. Every one of the 49 tasks, in both arms, runs its trial-0 episode under 626729 and its trial-1 episode under 373753 (verified per unit in the raw JSONs: 49 + 49 in each arm). Round 9 (b), lines 58-65, said this dependence "is within task-by-trial cells, so it is absorbed by task-level clustering". **That sentence is withdrawn.** The same seed is a common source of randomness for 98 episodes of 49 different tasks, and each arm ran as one batch through one server process (shared prompt-cache and hardware state along the batch). Common-seed or batch-state dependence between *different tasks* is therefore possible, it is not confined to task-by-trial cells, and clustering on the task does not absorb it automatically. Whether the seed reaches the sampler at all cannot be verified from the saved requests (`report_final.md` 7.5), which leaves the size of this dependence unknown, not zero.

**1.2 The first 24 pairs also need the independent-episode model.** Round 9 (b) said the block-1 subset (pairs 1-24, each task at most once) is the part of the stream "for which the iid-roster argument ... applies verbatim". Distinct task labels are not enough. Under the superpopulation reading R2 the block-1 pair scores have a common conditional mean and the betting e-processes are valid only if, in addition to an exchangeable / iid task roster, **episodes of different tasks are independent given the tasks**. All 48 block-1 units share the single seed 626729 and one batch per arm, so that independence is a modelling assumption here, exactly as it is for the full stream. It is not a property of the design and it is not testable with two seed values.

**1.3 Consequences for what was already reported.**

- *E2, task-clustered t intervals (49 clusters).* They remain the prespecified fixed-horizon analysis, but their status is: **model-based and approximate**. They treat tasks as independent sampling units conditional on the two realized seed values and the two batch runs. They do not cover seed-to-seed or batch-to-batch variation (there are two seed values, shared by every task and both arms, and the seed is confounded with the trial block), and "conservative for the finite-roster average" is claimed only under between-task independence. The Round 9 phrase "absorbed by task-level clustering" must not be used.
- *E1 under R2, all 49 pairs and block 1.* Operational illustrations under (i) a common conditional mean of the pair scores, (ii) an exchangeable roster, (iii) independent episodes across tasks. None of the three is established. No population guarantee is asserted for either row; the block-1 row is not privileged beyond avoiding repeated task labels.
- *Monitor paths.* Descriptive.

## 2. The clean reading that needs no further execution: orientation randomization on the observed replay array

**Conditioning.** Condition on (a) **the complete collected outcome array itself**: the 196 realized outcome vectors, both arms on all 98 (task, trial) units, as fixed numbers (not on their law); and (b) **the matching**: the prespecified arrival order of `design.json` and the 49 disjoint pairs it forms, in their prespecified order. Nothing about tasks, seeds, models or servers is treated as random.

**What is random.** Only the 49 orientation coins R_k. They were generated with the matching from `numpy` seed 20260918 and frozen in `design.json` (sha256 `c8fa5728e8a9602813ffac10ea4ef88642ef3550aa9d5a5b7028c25586186597`, identical in both manifest invocations) before any design episode. Two facts make the reading legitimate:

1. **The collection did not use the coins.** tau2 ran every unit under both arms, arm A then arm B, trial-major in task order; `run_tau2_open.py` reads the design only to compare hashes in its pre-flight, and the tau2 command line is built from `config.json` alone. The one human intervention, Deviation 1, was decided from an operational failure and refers to no pairing or orientation.
2. **There was no outcome-driven selection of the order.** Arrival order, pairs and orientations are those frozen before collection; the analysis reads them from `design.json` and never reorders, drops or re-pairs.

The coins are pseudo-random numbers from a documented seed; as in any randomization analysis, the statement is about their nominal distribution, independent fair coins, independent of the array and the matching.

**The comparator.** Pair k consists of two fixed units, u_k1 (first arrival) and u_k2. Because both arms were collected on both units, **both orientation outcomes are fixed, known numbers**: a_k = hierarchical score of (B on u_k2) versus (A on u_k1), used when R_k = 1, and b_k = score of (B on u_k1) versus (A on u_k2), used when R_k = 0. The coin selects one of them: z_k = R_k a_k + (1 - R_k) b_k. Given the array and the matching, the z_k are independent, lie in [-1, 1], have mean m_k = (a_k + b_k) / 2, and z_k - m_k = +-(a_k - b_k) / 2 is a symmetric two-point variable, hence sub-Gaussian with variance proxy at most 1. The sum of the z_k - m_k is a martingale in the coin filtration, so the normal-mixture boundary with V_n = n applies without any sampling assumption.

**The statement.** With rho = 100, alpha = 0.05 and radius r_n = sqrt((n + rho) log((n + rho) / (rho alpha^2))) / n, conditional on the collected array and the matching,

> P( for some n in 1..49: | zbar_n - mbar_n | > r_n ) <= 0.05,

where zbar_n is the running mean of the observed pair scores and **mbar_n = (1/n) sum_{k<=n} (a_k + b_k) / 2 is the running orientation-averaged mean of the OBSERVED replay array**. The same holds for the success-difference score (B - A success of the pair, in {-1, 0, 1}).

**Numbers (49 prespecified pairs).**

| score | observed running mean at n = 49 | radius r_49 | 95% running-mean interval | target mbar_49 computed from the observed array | pairs whose two orientations give different scores |
|---|---|---|---|---|---|
| hierarchical net benefit | 0.0204 (10 wins / 30 ties / 9 losses) | **0.630** | **[-0.609, 0.650]** | 0.0102 | 24 of 49 |
| success difference | 0.0204 | **0.630** | **[-0.609, 0.650]** | 0.0000 | 24 of 49 |

r_49 = sqrt(149 x log(149 / 0.25)) / 49 = 0.6297. For the first 24 pairs r_24 = 1.156, so the interval is [-1, 1] after clipping (unclipped [-1.073, 1.239]); the radius first falls below 1 at n = 29 and would reach 0.03 only at n = 12,094. For both scores the known target lies inside the interval at every n from 1 to 49 (largest |zbar_n - mbar_n| = 0.375, at n = 4; at n = 49 it is 0.0102). For the success difference the target is exactly (15 - 15) / 98 = 0: the orientation-averaged success difference of the array is the difference of the two arms' overall success rates.

**The interval is wider than informative**: its width, 1.26, is 63% of the whole parameter range [-1, 1], and its target is a quantity that the complete array already gives exactly (0.0102 and 0.0000). Its value is only that it is a correct statement: it shows what a monitor that sees one exposure per arrival can guarantee about this array by design alone, and it says that at 49 pairs this is almost nothing.

**What the reading does not support.** It is a statement about the **observed replay array only**. It is not inference about a fresh run of the same tasks (agent temperature 0.3, unverified seeding and a non-bit-reproducible stack mean that a new collection would give a different array), not inference about new tasks or other domains, and not a statement about production performance of either agent. It does not upgrade the R2 outputs: the corrected betting CS [-0.366, 0.406] and the three e-processes keep the status given in 1.3.

**History-conditional alternative.** The audit also allows a history-conditional target (the mean of pair k's score given the previous pairs). For the full stream that target is not constant across pairs even under an iid roster, because block 2 reuses the tasks of block 1; using it would require the conditions of 1.3 to be stated as assumptions. It is not used, and no tau2 result is certified under it.

## 3. Labelling of temporal decisions

Every temporal quantity of this experiment (the three monitor paths, "from pair 20 on", first-crossing indices, the guarded anytime decision, the fixed-horizon decision at n = 49, the block-1 / block-2 split) is a **replay of batch collection (all A then all B)** over the prespecified ordering. None is a physically randomized arrival, a live stopping decision, a stopping saving, an operational latency or a production A/B result. In tables and captions the label "replay of batch collection (all A then all B)" is to be used for them; "descriptive replay" and "post hoc replay" in `report_final.md` mean the same thing.

## 4. Pre-amendment units and attempts (pointer)

`results/tau2_open/unit_policy_flags.csv` flags the five pre-amendment units and the 191 amended units; `results/tau2_open/all_attempt_accounting.{csv,md}` enumerates all 206 attempts and states tau2's canonical-outcome rule; `experiments/tau2_open/deviation_1_erratum.md` corrects the amendment's timestamp and its "would not have changed" / "outcome-blind" wording. The omit-five sensitivity reported in `report_final.md` is post hoc and does not replace the planned denominator of 196 units, 49 pairs and 49 task clusters.
