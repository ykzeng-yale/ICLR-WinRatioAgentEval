# local_stream: Round 12 addendum (report-only corrections, 2026-09-19)

Status: POST HOC wording corrections requested by the root session's Round 12 review of owner head
`c1da1c3fc4e8c90644388e8b47e2e15574fe5215` (`reviews/round12_coding_correction_and_baseline_delta.md` on main; root
integration commit `45e8ee2715f148c81db7f6510d66677f57e03f0a`). No model was run and no analysis was rerun. No raw
observation, frozen file, earlier addendum, earlier report or earlier output was edited:
`protocol_addendum_round10.md`, `results/local_stream/report_v3.md` and all v1 / v2 / v3 outputs stay byte-unchanged.
The corrected report is the new file `results/local_stream/report_v4.md` (script `make_report_v4.py`, hashes in
`report_v4_manifest.json`). No estimate, interval or decision label changes.

Where this addendum conflicts with `protocol_addendum_round10.md` or `report_v3.md`, this addendum governs.

Scope note. The root integration uses the raw coding observations with the root's own running-conditional-mean
analysis and a descriptive same-task comparison. The owner intervals discussed here are **not** part of that
integration. These corrections matter only if the owner reports are reused.

## 1. R1: two filtrations that must not be mixed (supersedes section 1 of the Round 10 addendum where they conflict)

**The guarantee (unchanged in substance).** Let

    F_k = sigma( the full frozen schedule: arrival order, pairing and ALL orientation coins ; revealed pair data of pairs 1..k ).

`Z_k` in [-1, 1] is adapted to `F_k`, so `Z_k - E[Z_k | F_(k-1)]` is a bounded martingale difference and the
normal-mixture boundary (`V_n = n`, `rho = 100`, two-sided `alpha = 0.05`) covers the running conditional mean
`(1/n) sum_{k<=n} E[Z_k | F_(k-1)]` uniformly in n. Nothing else is used.

Withdrawn: the phrase "design information that is independent of future outcomes". It is not needed for the
guarantee, and it was not justified: information fixed before the outcomes existed is not thereby independent of
them.

**What this filtration does not give.** Under `F_(k-1)` the orientation of pair k is already known. `E[Z_k | F_(k-1)]`
is therefore the conditional mean of the score **in the realized orientation**. A filtration that contains every
realized coin cannot also give the coin of pair k conditional probability 1/2, and no stability assumption restores
that randomness. The Round 10 sentence "conditional on the pairing and the past, the coin is fair" is withdrawn for
this filtration.

**Where the symmetric formula does hold.** Take the coarser filtration

    G_k = sigma( arrival order, pairing ; orientations and revealed pair data of pairs 1..k ),

which leaves the orientation of pair k unrevealed at time k - 1. Assume, in addition,

1. the coin of pair k is fair and independent of `G_(k-1)` (the nominal model of the seeded design), and
2. a stable assignment / episode-law model: given `G_(k-1)` and the orientation, the two episodes of pair k have a
   joint law that depends only on their tasks and workflows, not on the orientation, the pass position or the history
   (thermal state, execution order, caching).

Then `E[Z_k | G_(k-1)] = [ m(s_k, t_k) + m(t_k, s_k) ] / 2`. The score is adapted to `G_k` as well, so the same
boundary also covers the running mean of `E[Z_k | G_(k-1)]` (this coverage needs neither assumption 1 nor 2; only
the symmetric formula does). These are two different targets for one realized
interval; each statement is valid separately and neither implies the other. Assumption 2 is not established by the
design (latency is tier 2 of the hierarchy), so the symmetric reading is **not assumed** in any report.

**Unconditional identity.** `E_design[ mu_bar ] = theta_N` is an average over the random assignment (matching and
coins). It can hold under assumptions 1-2 with a random matching, and it is not the conditional identity above. No
statement about `theta_N` is made.

Numbers (unchanged): NB -0.4712, band [-0.6540, -0.2883], upper bound first below 0 at pair 60; success-difference
band [-0.1320, 0.2337]; the gate is not established; the two bands are marginal, not a joint 95% region; `rho` was
fixed post hoc.

## 2. E2: the approximate cluster t interval needs cluster-level CLT conditions

The Round 10 addendum and `report_v3.md` described the orientation-pair cluster t interval as "approximate" and
"valid under independent orientation-pair clusters". That is incomplete. Independent clusters with bounded totals do
not by themselves justify the t approximation. It additionally needs

- variance growth / nondegeneracy of the cluster totals,
- a Lindeberg or no-dominant-cluster condition, and
- a consistent cluster variance estimator.

Counterexample to a blanket coverage claim (from the root review): `G = 296` independent clusters, `B_g ~
Bernoulli(1/G)`, sizes `n_g = 2` except one singleton, totals `T_g = n_g B_g`. The target is `1/G > 0`. With
probability `(1 - 1/296)^296 = 0.367257147` every total is 0, the cluster variance and the t width are 0, and the
interval misses the target. This limits the claim; it is not evidence that the observed sample has that law.

Unchanged and separate: the **exact** final-time cluster Hoeffding interval [-0.8145, -0.4986] (radius 0.15794)
needs independent clusters and bounded totals only, and no CLT. Independence across clusters remains an assumption
(shared machine state). The -0.03 success margin is not certified by any reported interval.

## 3. Pass / period table: no attribution

Withdrawn: "the success-rate differences between passes within a variant therefore largely track which half of the
roster was exposed". Correct statement: these descriptive differences mix task composition with possible period
effects, including workflow-specific period effects; the table does not separate them. No number changes and no
inference is drawn from the table.

## 4. Scope of issues #1 and #2

The coding experiment followed its prespecified collection schedule; its retained monitoring analyses (R1, R2, the
cluster analysis) are post hoc. It is not a live randomized A/B deployment and not an independent replication by a
second party. Whether the broader confirmatory ambitions of issues #1 and #2 are pursued is the repository owner's
decision; no further run is requested or started.
