# Round 11: coding target and inferential scope

**Verdict: the proposed narrow integration is sound.** Use the validated observed coding records and the root's explicit normal-mixture construction for a running conditional-mean target, label its application post hoc, retain E2 point estimates descriptively, and import no contributed `wincs` or E2 uncertainty. This does not certify inference for the full fixed task roster, a task superpopulation, or production performance.

Reviewed 2026-09-19, frozen PR8 **`c89b525cd8e51564ca8c23399201d9cfdf0431a3`**. Scope: `round10_open_model_repair_audit.md`, design and execution source, the original protocol and post-hoc addendum, raw coding records, recorded monitor, and R1 calculation. The reviewer contributed project theory previously; this is an independent formula/raw-data scope check, not an independent model experiment. No model calls, generated benchmark-program executions, heavy Monte Carlo, contribution-source changes, or Git mutations occurred.

## Minimal valid target and probability statement

Let Z_k ∈ {−1,0,1} be the frozen hierarchical sign **B minus A** for the two actual pass-1 episodes in pair k, in collection order. Let D_k ∈ {−1,0,1} be that pair's success difference. Here the hierarchy is success, then latency with relative tolerance 0.10, then completion tokens with relative tolerance 0.10; resource tiers are eligible only after joint success. Joint failure ties.

Specify a filtration (ℱ_k) to which these complete pair records are adapted. A useful choice includes the fixed task roster and realized pairing/order at ℱ_0, and then the revealed assignments, outcomes, and relevant execution history through pair k. It excludes future outcomes and later shadow-pass records. Write

\[
\mu_k=E(Z_k\mid\mathcal F_{k-1}),\qquad
\nu_k=E(D_k\mid\mathcal F_{k-1}),\qquad
\bar\mu_n=n^{-1}\sum_{k\le n}\mu_k,\quad
\bar\nu_n=n^{-1}\sum_{k\le n}\nu_k.
\]

These are **running averages of history-conditional means for this first-pass pair process**. They may change with task composition, machine state, previous outcomes, and exposure history. Arbitrary serial dependence is allowed for this target; independent model calls, identical distributions, stationarity, and an iid task roster are not needed. The assertion still requires a probabilistic model for the experiment and the specified filtration. It is not uncertainty about an already conditioned-on full outcome array.

For a procedure with fixed α ∈ (0,1), ρ > 0, fixed score definition, and the declared observation order, define

\[
r_n=\frac{\sqrt{(n+\rho)\log\{(n+\rho)/(\rho\alpha^2)\}}}{n},\qquad
C_n^Z=[\bar Z_n-r_n,\bar Z_n+r_n]\cap[-1,1].
\]

Then P(μ̄_n ∈ C_n^Z for every n ≤ 295) ≥ 1−α. The same marginal statement holds separately for C_n^D and ν̄_n. One can extend to an indefinitely defined process; this experiment only needs 1 ≤ n ≤ 295. No intersection with intervals from previous times is appropriate because the target moves.

**Proof.** Given ℱ_{k−1}, the centered increment Z_k−μ_k has range length 2. Conditional Hoeffding gives E[exp{λ(Z_k−μ_k)} | ℱ_{k−1}] ≤ exp(λ²/2). Thus, writing S_n = Σ_{k≤n}(Z_k−μ_k), the process exp{λ S_n−nλ²/2} is a nonnegative supermartingale. Mixing over λ ∼ N(0,1/ρ) yields

\[
M_n=\sqrt{\rho/(n+\rho)}\exp\{S_n^2/[2(n+\rho)]\}.
\]

The event |S_n| ≥ n r_n implies M_n ≥ 1/α; Ville's inequality proves the all-prefix bound. The proof for D_k is identical. This is the established Hoeffding/normal-mixture argument already proved in the root's Theorem `thm:normal_cs`, not a new inequality or an application of the contributed betting-capital inversion.

### Additional conditions only for a randomization/causal interpretation

The concentration result above does **not** itself need a fair allocation coin. To interpret μ_k as the average of the two possible AB/BA assignment responses, additionally assume that, before the pair's assignment is revealed, its orientation is fair and nonanticipating conditional on the chosen history and pairing. Under that model,

\[
\mu_k=\tfrac12 E(Z_k\mid\mathcal F_{k-1},R_k=0)
       +\tfrac12 E(Z_k\mid\mathcal F_{k-1},R_k=1).
\]

The two terms may include position effects and within-pair execution history. This history-dependent expression is safer than the addendum's time-invariant {m(s_k,t_k)+m(t_k,s_k)}/2. That simpler task-only formula needs stable, assignment/position-compatible episode laws and sufficient independence/no relevant interference to justify the product-episode construction. Different task labels and separate calls do not establish those conditions, especially for measured latency.

The design precomputed all orientations from a fixed recorded pseudorandom seed. If using allocation randomness in the probability model, treat the intended independent fair draws as unrevealed until their pairs and assume execution does not anticipate future orientations; do not condition ℱ_0 on the complete orientation sequence or a seed that determines it and simultaneously assert conditional fair-coin assignment. Alternatively condition on the full realized schedule and keep only the general conditional-mean target; the concentration formula remains available for the remaining outcome randomness, but its mean no longer automatically averages over orientations. No claim of cryptographic or literal physical randomness is needed.

## Physical collection versus post-hoc chronological reanalysis

The source and raw records support **prospectively assigned laboratory exposures**: a fixed permutation of 591 tasks, 295 disjoint AB/BA pairs, and one unpaired task; pass 1 was physically executed in arrival order, followed by the complementary workflow on every task in pass 2. The code updated the original betting monitor after completed pass-1 pairs and expressly continued through all arrivals. The raw file contains exactly this pass/arrival order with nonoverlapping, increasing timestamps.

The **R1 normal-mixture analysis was added after all 1,182 episodes and the original analysis were seen**, as the addendum states. Therefore its upper-bound crossing at pair 60 is a post-hoc chronological replay/reanalysis of that prospective stream, not a stopping rule that was prospectively chosen or acted upon. It is not replay assignment of an already collected complete outcome array, and it is not a production A/B deployment.

The mathematical guarantee is for the specified fixed procedure. The addendum acknowledges post-outcome choice of this analysis and ρ=100, although 100 was already the project library default. The paper should say **“post-hoc application of the fixed 95% normal-mixture construction”** and disclose that analysis selection is not adjusted for. Do not upgrade it to a selection-adjusted, preregistered confirmatory claim. No realized episode, latency, token, or wall-clock saving follows from the replay crossing; all planned executions were completed.

## Independent numeric check using only root core and raw records

I independently rebuilt the hierarchy with direct scalar comparisons from the frozen design and 1,182 episode records, without importing any contributed analysis or `wincs` function. Scores, success differences, and decisive tiers agree exactly with all 295 recorded monitor rows. I extracted only the root `normal_mixture_radius` function by AST and independently evaluated the displayed formula. Every archived R1 endpoint/radius agrees exactly, including all prefixes, with zero numerical discrepancy.

| Quantity | Independently confirmed value |
|---|---:|
| First-pass complete pairs | 295 (590 episodes) |
| B wins / ties / losses | 69 / 18 / 208 |
| Observed net benefit | −0.4711864407 |
| R1 radius, α=.05, ρ=100, n=295 | 0.1828387393 |
| R1 net-benefit band | [−0.6540251800, −0.2883477014] |
| First upper endpoint below zero | Pair 60; remains below through pair 295 |
| First-pass success difference | 0.0508474576 |
| Separate R1 success-difference band | [−0.1319912817, 0.2336861969] |
| Any prefix with success lower endpoint above −0.03 | None |
| Descriptive E2 wins / ties / losses | 41 / 121 / 429 over 591 tasks |
| Descriptive E2 net benefit | −0.6565143824 |

The unpaired task is absent only from E1 and is included in E2 by design; it is not an outcome-driven exclusion. Its identity need not appear in the main text.

The root core SHA-256 used here is `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`. The R1 formula uses an explicit square root and logarithm, never ternary-capital endpoint inversion. The outstanding contributed `0*log(0)` endpoint issue therefore has no role in these numbers or their proof.

## Multiplicity, target boundaries, and labels

- **Separate bands:** two separate 95% CSs provide marginal time-uniform coverage; their joint rectangle has only the generic 90% lower guarantee by the union bound. Do not call the displayed pair a joint 95% region. For joint 95% coverage, allocate a total error budget across the two processes and recompute. Merely displaying both does not require silently changing the original estimates.
- **No guardrail certification:** the success lower endpoint never exceeds −0.03. The negative composite signal does not establish success-rate harm, safety harm, or noninferiority. It does not constitute guarded approval of A in the reverse direction. “Incumbent A retained” is an action label consistent with the observed negative composite signal; no real deployment occurred.
- **No fixed-roster inference:** the CS covers μ̄_n, conditional on the specified history model, not θ_N, the all-distinct-pairs fixed-roster functional. Random matching can induce additional variation between those quantities. Equality in expectation under stable-law idealizations does not transfer coverage. A history-dependent latency target also need not admit that equality.
- **No automatic R2:** an iid task-superpopulation interpretation needs hypothetical iid rosters, independent/stable episode laws, and a filtration not conditioning on all future realized task values. Neither a curated benchmark nor random permutation proves those assumptions. No R2 interval or decided-pair win-ratio CS is needed for the proposed integration.
- **E2 descriptive only:** same-task outcomes come from complementary passes sharing orientation decisions and possible period/machine effects. One record per task does not prove independent task scores. Retain the E2 mean and observed success totals, without the contributed “assumption-free,” “Neyman-conservative,” t/CLT, or Hoeffding interval claims. Do not give uncertainty for the E1–E2 difference from these separate calculations.
- **Observed resource scope:** latency is local wall-clock workflow time including self-tests and excluding hidden-test verification and model loading. Completion tokens are generation counts, not measured monetary cost or total compute. The hierarchy is conditioned on that declared endpoint definition and recorded hardware; no hardware-invariant ordering is implied.
- **Timing and initial information:** keep frozen score definitions, complete enrollment/pair order, and post-hoc analysis status explicit. Do not retrospectively select a more favorable prefix, hierarchy, tolerance, model variant, or ρ and invoke the fixed-procedure theorem without accounting for that selection. Time-uniform coverage permits inspecting all prefixes for the fixed rule; it does not automatically cover arbitrary analysis selection.

## Suggested manuscript wording

> We collected a laboratory coding stream under a frozen randomized AB/BA schedule, followed by complementary same-task shadow runs. A post-hoc application of the fixed 95% normal-mixture construction to the 295 first-pass pair scores gave net benefit −0.471 and band [−0.654, −0.288] for the running average of history-conditional pair means; its upper endpoint first fell below zero at pair 60. All planned episodes were completed. The separately reported success-difference band [−0.132, 0.234] did not certify the −0.03 noninferiority margin. These are marginal bands for the observed collection process, not a joint region or a confidence statement about the entire fixed task roster; the post-hoc choice of analysis is not selection-adjusted. The same-task net benefit of −0.657 is descriptive.

Suggested short table headings: **“First-pass cross-task pairs: observed NB”**, **“Post-hoc R1 normal-mixture band”**, **“Separate success-difference band”**, and **“Same-task shadow NB (descriptive)”**. Suggested crossing label: **“First negative upper endpoint in chronological reanalysis”**. Avoid “prospective CS stopping,” “live savings,” “population win rate,” “assumption-free confidence,” “joint 95% certification,” and “A approved by the success guardrail.”

## Evidence and remaining work

Outer-workspace scratch: `work/round11_coding_theory/independent_r1_check.json` contains all numeric checks; `source_hashes.json` pins the exact source/data snapshot. Key original hashes: design JSON `6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457`; episodes `95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0`; recorded monitor `67504351725acbf51de936ae0ee9b9361de7fd7d73c58ca529987547ac4621a6`.

**No new experiment is required for this narrow use.** Root should compute/package only the validated observation subset and its own R1 formula, preserve the post-hoc and target limitations, and omit unsupported E2/R2 inference and contributed endpoint routines. Final integrated manuscript and anonymous payload still require their ordinary scoped review after integration; this report does not audit the pending airline evidence or the completed release package.
