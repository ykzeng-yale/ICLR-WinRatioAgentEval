# R1 — The root's accepted online method (reference for the live A/B trial design)

Reader R1, 2026-09-19. Read-only on the repository; CPU-only toy computations; no model calls.
Sources read at working tree `session60/local-stream` (HEAD `ce8b506`, which merged root `410b158`). `origin/main`
has since advanced to `955579d` (Round 15, an index-only disposition: it again separates the root's **retained pair-60
normal-mixture crossing** from the **descriptive pair-24 e-process reading**; `git show origin/main:reviews/round15_integration_disposition.md`).
`git diff origin/main -- paper src/winstats.py experiments/build_open_coding_results.py experiments/run_simulations.py
experiments/run_async_experiment.py results/open_coding` is empty, so every paper/code line number below is valid for
the root's current main as well (only `EXPERIMENT_QUEUE.md:35` here is `:37` on `origin/main`). `src/winstats.py` SHA-256 =
`56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` (the same hash the root reviewers pinned in
`reviews/round11_coding_target_scope.md:80` and `reviews/round12_airline_inference_review.md:92`).

Paths are relative to `<REPO>/`. Scratch files produced by this reader:
`R1_toy_api_check.py`, `R1_toy_api_check.out`, `R1_radius_table.out` (same directory as this report).

---

## 0. Executive summary (what the coordinator must take from this)

1. **The only analysis the root retains for the open coding stream is a two-sided normal-mixture band for the running
   average of history-conditional means**: `normal_mixture_radius(n, alpha=.05, rho=100.)`, `V_n = n`, clipped to
   `[-1,1]`, no running intersection, applied separately (marginally) to the net-benefit pair score and to the
   success-difference pair score (`paper/open_coding_appendix.tex:77-106`, `experiments/build_open_coding_results.py:142-149`).
   It rests on Theorem `thm:normal_cs` (`paper/theory.tex:288-329`), which needs only: scores adapted to a filtration,
   predictable known bounds, and `rho`, `alpha` fixed before looking. No iid, no stationarity, no independence.
2. **The paper's guarded deployment rule** is a conjunction of gates `c_0 = 0` (net benefit) and `c_j = -delta_j`
   (component noninferiority). Under *stationary* conditional means each gate may use the full `alpha` (IUT,
   `thm:iut`, `theory.tex:465-482`). Under *drifting / history-conditional* targets — which is what a fixed finite
   roster in a fixed order gives (Round 9 P1, `reviews/round9_open_model_evidence_audit.md:75-81`) — the paper requires
   **alpha split across the J+1 gates, all gates passing at the same current prefix, and no retention of old
   crossings** (`paper/main.tex:270-277`, `thm:drift_gate`, `theory.tex:494-531`). The same holds for the 40-stake
   fixed-grid betting gates through `prop:bet_running` (`theory.tex:408-436`).
3. **There is no harm / futility test in the paper's rule.** The only harm-like reading the root retains is "upper
   endpoint of the two-sided normal-mixture band below zero" (pair 60 on the pilot). The owner's one-sided harm
   e-process (pair 24) is labelled *descriptive* (`reviews/round14_integration_disposition.md:20`). A prespecified
   harm gate is derivable from the paper's own results but is not something the root has explicitly endorsed —
   see 2.6 and the open questions.
4. **Two conflicts between the coordinator's design text and the root's accepted construction** must be resolved
   before freezing:
   - *Coin unit.* The paper randomizes the **orientation of a disjoint pair of arrivals** (one coin per pair, one
     exposure per arm per pair; `main.tex:171-177`, `theory.tex:181-195`). An independent coin **per arrival** is
     not the paper's design and `thm:pair_id` does not cover it.
   - *Reveal order.* The paper never feeds scores to the monitor in completion order. Statistics are always over
     **enrollment-order prefixes**; out-of-order information enters through guaranteed enclosures `[l_i(t), u_i(t)]`
     of pending pair scores (`paper/asynchronous.tex:33-48, 85-97`; `main.tex:203-213`; `theory.tex:555-563`).
     "Consume outcomes in reveal order" must mean "re-evaluate enrollment prefixes at every reveal event".
5. **The current pair's assignment coin is NOT in the conditioning filtration** `F_{i-1}`; earlier coins are; future
   coins must not exist yet (no seed-determined orientation sequence in `F_0`). Exact statement in section 5.3.
6. **Feasibility warning (numbers from `src/winstats.py`, section 4.3):** with cross-task pairs at ~73% success the
   success-difference score is discordant in ~39% of pairs. Certifying `delta = 0.03` needs roughly 6,000 pairs with
   the betting gate and >12,000 with the normal-mixture band (the root computed 12,094,
   `round12_airline_inference_review.md:70`; reproduced here). A 591-task single pass gives 295 pairs. A live
   *deploy* crossing therefore cannot occur in T1 unless the margin, the pairing (strata), or the number of
   arrivals changes. The net-benefit gate and a harm gate are well powered (crossings at n ~ 40-90 on the pilot).

---

## (a) Pair score, hierarchy and tolerance conventions

### a.1 The kernel
- Episode record `Y` = whole episode through a **fixed evaluation horizon** (outcomes + resources); a tool call is
  not a unit (`paper/main.tex:95-97`; `paper/theory.tex:19-21`).
- Tier comparators `d_k(y,y') in {-1,0,1}`, antisymmetric, 0 = prespecified operational tie. Hierarchical kernel
  `h(y,y') = sum_k d_k(y,y') * prod_{l<k} 1{d_l(y,y')=0}` — only the first decisive tier contributes; `h in {-1,0,1}`
  and antisymmetric (`main.tex:98-105`, eq. `eq:main_kernel`; `theory.tex:22-42`, eq. `eq:hierarchy_kernel`).
- Resource tiers "can be disabled unless both episodes satisfy a symmetric eligibility rule, such as both achieving
  verified completion" (`main.tex:105-107`; `theory.tex:31-34`). The rule is part of the estimand and "must not be
  chosen after inspecting the systems' comparative results" (`theory.tex:33-34`).
- Tolerance in the paper's synthetic work: `|c_A - c_B| > 0.05 * max(c_A, c_B)`; **equality is a tie**; "This
  threshold is an operational preference, not a significance test" (`main.tex:107-109`).
- Code (`src/winstats.py:25-48`): for tier `k`,
  `tol = absolute_tolerance + relative_tolerance * max(|a_k|, |b_k|)`; `delta = (a_k - b_k) * (+1 if higher_better else -1)`;
  the tier is decisive iff it is the first with `|delta| > tol` (strict) and `eligible[..., k]` is true.
  Returns `(sign, zero_based_decisive_tier)` with tier `-1` for a tie. Missing / non-finite outcomes raise
  `ValueError` (`winstats.py:36-37`) — a failed or timed-out episode must therefore be given finite endpoint values.

### a.2 The coding hierarchy the root accepted (use it unchanged to stay comparable with the pilot)
`results/open_coding/collection_config.json` ("hierarchy") and `paper/open_coding_appendix.tex:42-56`:

| tier | field | direction | tolerance | eligibility |
|---|---|---|---|---|
| 0 | `success` (hidden checks exit 0 AND verifier sentinel seen; timeouts/failed checks = 0) | higher better | 0 | always |
| 1 | `latency_s` (model calls + agent self-tests; excludes hidden verification and model loading) | lower better | relative 0.10 of the larger value | only if both episodes succeeded |
| 2 | `completion_tokens` (all calls in the workflow) | lower better | relative 0.10 of the larger value | only if both succeeded |

Joint failure ties. Root builder call (`experiments/build_open_coding_results.py:90-95`):
```python
tiers = tuple(Tier(**tier) for tier in config['hierarchy'])
values = lambda r: [int(r['success']), r['latency_s'], r['completion_tokens']]
both = bool(a['success'] and b['success'])
z, tier = compare(values(b), values(a), tiers, [True, both, both])     # positive favours B
return int(z), int(tier), int(b['success']) - int(a['success'])       # success difference D in {-1,0,1}
```
**Orientation trap.** In `main.tex`/`theory.tex` the candidate is called `A` (`Delta_S = P(S^A=1) - P(S^B=1)`,
`main.tex:154-157`; "arguments are always oriented as A then B", `theory.tex:205`). In the coding appendix the
candidate is `B` and "Positive scores favor B" (`open_coding_appendix.tex:49`). For the new trial (incumbent A,
candidate B) keep the builder's convention: `compare(candidate, incumbent)`.

### a.3 Summaries and the component score
- `theta = p_W - p_L = E h` is the monitored bounded target; `WR = p_W/p_L` if `p_L>0`; `WO = (1+theta)/(1-theta)`;
  no pseudocount for zero losses (`main.tex:111-117`; `theory.tex:44-64`; `winstats.summary`, `winstats.py:88-93`).
- Component gate score: `phi_j(y,y') = g_j(y) - g_j(y')`, `g_j in [0,1]`; for success it is `D in {-1,0,1}`. Its pair
  target is the average same-episode component effect of the pair (`theory.tex:247-258`, eq. `eq:component_pair_effect`).
- Deployment region `D = {theta > 0, Delta_j > -delta_j for all j}` (`main.tex:159-167`, eq. `eq:main_region`);
  margins "require application-specific justification" (`main.tex:165-166`). Value used everywhere so far:
  `delta_success = 0.03` (`paper/results_main.tex:6-9`; `collection_config.json` `success_margin`;
  `paper/async_results.tex:13-14`), `delta_compliance = 0.01` in the synthetic studies only.

### a.4 The online pair score (what `Z_i` is in a single-exposure stream)
`main.tex:169-201` and `theory.tex:179-236`:
- "Before observing outcomes, form **disjoint pairs of arrivals** within a prespecified stratum. Let `R_i=1` assign
  system A to the first arrival and B to the second; `R_i=0` reverses the order ... Each arrival receives only one
  system. This design fixes **one exposure per arm per pair**; it is not an arbitrary traffic-allocation bandit"
  (`main.tex:171-177`).
- `Z_i = R_i U_i/(2 q_i) + (1-R_i) V_i/(2(1-q_i))` with `U_i = h(Y^A_{i1}, Y^B_{i2})`, `V_i = h(Y^A_{i2}, Y^B_{i1})`
  (`main.tex:179-186`). With `q_i = 1/2`, `Z_i` is just the observed oriented kernel, `Z_i in {-1,0,1}` and `V_n = n`
  (`main.tex:195`, `theory.tex:223-224, 304`).
- `E(Z_i | H_i, potential outcomes) = m_i = {phi(Y^A_{i1},Y^B_{i2}) + phi(Y^A_{i2},Y^B_{i1})}/2` (`thm:pair_id`,
  `theory.tex:213-236`). Exchangeability of the two positions is **not** needed for this symmetrized target
  (`theory.tex:238-245`); pairing within a baseline stratum is allowed and "reduces cross-context comparisons".

---

## (b) The guarded monitoring rule the paper endorses

### b.1 Building blocks
| Block | Definition | Where |
|---|---|---|
| Normal-mixture CS | `Zbar_n +/- (1/n) sqrt((V_n+rho) log((V_n+rho)/(rho alpha^2)))`, `V_n = sum r_i^2/4` (`= n` for balanced ternary scores); covers the running mean of conditional means `mubar_n` for all `n` simultaneously w.p. `>= 1-alpha` | `main.tex:217-234`; `thm:normal_cs`, `theory.tex:288-329`; `winstats.py:51-61` |
| `rho` | `rho = 100`, fixed; library default; "Tuning rho after examining this stream invalidates this particular guarantee" | `paper/experiments_appendix.tex:23`; `theory.tex:342-344`; `winstats.py:51,55` |
| Betting gate | `E_n(c) = sum_k w_k prod_i {1 + lambda_k (X_i - c)}`; **40 equal-weight geometric stakes from 1e-4 to 0.99/(1+c)**; ternary count sufficient statistics; reject gate null when `E_n(c) >= 1/alpha` | `main.tex:236-251`; `theory.tex:346-406`; `experiments_appendix.tex:21-23`; `winstats.py:64-85` |
| Betting under drift | For the same fixed nonnegative grid: `P{exists n: mubar_n <= c and E_n(c) >= 1/alpha} <= alpha` with no stationarity. Does **not** make the wealth a supermartingale and does **not** justify retaining old crossings. Predictably time-varying stakes are **not** covered. | `prop:bet_running`, `theory.tex:408-443`; `main.tex:253-256`; docstring `winstats.py:67-74` |

### b.2 The deployment rule and its alpha convention
- Gates: `c_0 = 0` for preference, `c_j = -delta_j` for each component (`main.tex:259`; `theory.tex:447-457`).
  Rule `tau = inf{n: L_jn(alpha_j) > c_j for all j}` (eq. `eq:deploy_rule`, `theory.tex:454-457`); the betting
  implementation replaces each condition by `E_jn(c_j) >= 1/alpha_j`, "all criteria must pass at the **same monitored
  look**" (`theory.tex:458-460`).
- **Stationary conditional means** (`E(Z_ij | F_{i-1}) = mu_j` constant): every gate at the full `alpha`, no split
  (IUT; `thm:iut`, `theory.tex:465-482`; `main.tex:258-268`). "An optional retained-evidence variant ...
  `sup_{t<=n} E_jt >= 1/alpha_j`. Retention is justified only for the fixed stationary claims" (`theory.tex:460-463`).
  This is one deployment claim, **not** simultaneous `1-alpha` coverage of the reported effects (`main.tex:266-268`).
- **Drifting / running-average targets** (no fixed violating component): "Use simultaneous component confidence
  sequences, for example at levels `alpha/(J+1)`, and deploy only when every lower bound for its running target
  exceeds its threshold (`thm:drift_gate`). For fixed-stake betting gates the same allocation controls the
  conjunction when every gate crosses at the same current prefix; retaining old crossings does not certify current
  running targets" (`main.tex:270-277`; `theory.tex:494-531`). `experiments/drift_panel/protocol.md:43` names
  `L_jn(alpha/3) > c_j for all j` "the paper's drift rule, J+1 = 3"; the split betting rule is analysed in
  `paper/drift_extension_appendix.tex:43-51`.
- **Multiplicity beyond one experiment**: "For several candidates or repeated model revisions, further error
  allocation is necessary" (`main.tex:277-280`); `sum_e alpha_e <= alpha_program` by the union bound
  (`theory.tex:484-492`). Relevant to T1-T4.

### b.3 Numerical conventions actually used by the root
| Item | Value | Where |
|---|---|---|
| `alpha` | 0.05 | `results_main.tex:9`; `experiments/run_simulations.py:101`; `collection_config.json` |
| crossing threshold | `log E >= log(1/alpha)` i.e. `E >= 20` | `run_simulations.py:73`; `paper/async_appendix.tex:27-28` |
| margins | success `-0.03`, compliance `-0.01` | `run_simulations.py:65`; `results_main.tex:6-9` |
| first look / schedule (synthetic) | begins at 100 pairs, every 50 pairs, plus ten group looks | `results_main.tex:9-11`; `run_simulations.py:100` |
| first look (async study) | `minimum_pairs = 100`, prefix grid `100,150,...,6000`, both gates cross 20 at one common prefix | `experiments/run_async_experiment.py:26-30`; `async_appendix.tex:26-33` |
| first look (pilot coding monitor, owner's config, not a root choice) | `min_n_pairs = 20` | `collection_config.json`; `experiments/local_stream/run_stream.py:84-95` |
| root's post hoc coding band | **all prefixes n = 1..295**, no minimum | `build_open_coding_results.py:142-149` |

A minimum sample size is therefore *not* part of the validity argument (the guarantees are uniform over all `n >= 1`);
it is a design choice that must be frozen ex ante. With clipping to `[-1,1]` the band is vacuous until `r_n < 1`:
n = 29 (alpha_j = .05), 32 (.025), 34 (.05/3), 35 (.0125) — `R1_radius_table.out`.

### b.4 Simultaneous vs retained crossing
- Reported/primary everywhere: **same look / same current prefix** (`theory.tex:458-463`; `async_appendix.tex:27-28`;
  `paper/ustat_extension_appendix.tex:45-49`: "retention is not used to certify a current drifting conjunction").
- Retained crossings: allowed only under fixed stationary parameters (`theory.tex:460-463`;
  `asynchronous.tex:371-379`: "Gates may cross at different times or prefix lengths because they concern fixed
  stationary parameters"). Excluded from the drifting guarantee (`theory.tex:529-531`; `main.tex:276-277`;
  `asynchronous.tex:385-387`).
- Why this matters live: on the pilot stream the one-sided harm wealth was `>= 20` at n = 14 and n = 24, fell below,
  and stayed above only from n = 48 (section 4.2). Acting at the first same-prefix crossing is valid (time-uniform),
  but the decision and its prefix must be logged at that instant; a later "it was above at some point" reading is a
  retained crossing.

### b.5 Which variant is "accepted without re-analysis" for a fixed-roster stream
The root rejected a pointwise conditional-mean null for a randomly permuted fixed roster ("a random permutation of a
fixed roster does not establish the monitor's conditional null", `round9_open_model_evidence_audit.md:75-81`) and
retained the running-conditional-mean target instead (`round11_coding_target_scope.md:9-29`). For a prospective
trial on the same kind of roster this selects, in order of safety:
1. **Primary:** split normal-mixture CS, `rho = 100`, `V_n = n`, `alpha_j` with `sum_j alpha_j <= alpha`, all lower
   bounds above their thresholds on the **same enrolled prefix**, targets `mubar_n` and `nubar_n`
   (`thm:normal_cs` + `thm:drift_gate`). This is literally the root's coding analysis made prospective and joint.
   (`round11_coding_target_scope.md:84`: "For joint 95% coverage, allocate a total error budget across the two
   processes and recompute".)
2. **Secondary (more power, same theorems):** split fixed-grid betting gates `betting_log_e_ternary(..., threshold=c_j)`
   at `1/alpha_j`, same current prefix, no retention (`prop:bet_running` + `thm:drift_gate`, `theory.tex:503-505, 518-521`).
3. Full-alpha-per-gate IUT with optional retention is available **only** if stationarity of every gate's conditional
   mean is guaranteed by design (e.g. arrivals drawn iid with replacement by physical randomization, independent
   per-episode seeds, no machine-state drift). With a prespecified permutation of a finite roster it is not.

### b.6 Harm test — status
- Not in `main.tex`/`theory.tex`. `grep -i harm paper/*.tex` finds only `prop:compensation` and the grader-ablation text.
- Root-retained harm-like statement: "The first negative net-benefit upper endpoint occurs at pair 60"
  (`open_coding_appendix.tex:99-100`), with the explicit limits "does not establish success-rate harm ... does not
  constitute guarded approval of A in the reverse direction. 'Incumbent A retained' is an action label"
  (`round11_coding_target_scope.md:85`).
- Owner's one-sided harm e-process: `betting_log_e_ternary` with win/loss counts swapped. Root: "descriptive
  reading under R1; its fixed-mean guarantee requires the additional R2 model and is excluded"
  (`round14_integration_disposition.md:20`).
- Derivable, *if prespecified*: (i) two-sided normal-mixture band at `alpha_NB` already covers both directions, so
  "upper endpoint < 0 at the current prefix" costs no extra alpha beyond the two-sided `alpha_NB`; (ii) a betting harm
  gate on `-Z` at `alpha_H` is covered by `prop:bet_running` for the claim "running conditional mean of NB `< 0` at
  the crossing prefix", with `alpha_NB + alpha_S + alpha_H <= alpha` by the union bound. Neither (i) as a stopping
  rule nor (ii) has been explicitly endorsed by the root — open question 1.

---

## (c) The running-conditional-mean normal-mixture band used for the coding stream

**Text** (`paper/open_coding_appendix.tex:77-106`; main-text summary `paper/open_coding_results.tex:1-10`):
- `Z_k` = observed first-pass hierarchical sign (B minus A) of pair `k`; `D_k` = its success difference.
- Filtration: "`F_k` containing the fixed roster/schedule and revealed records through pair `k`, but no future
  outcomes"; `mu_k = E[Z_k | F_{k-1}]`, `nu_k = E[D_k | F_{k-1}]`; targets `n^{-1} sum_{k<=n} mu_k` and
  `n^{-1} sum_{k<=n} nu_k`. "These history-conditional means allow task composition, machine state and serial
  dependence" (`:78-84`).
- Coin caveat: "Conditioning on the full assignment schedule does not simultaneously give a conditional fair-coin
  causal interpretation. Such an interpretation instead requires orientations to be unrevealed and nonanticipating
  at their pairs, and appropriate history-dependent assignment-response laws" (`:84-88`).
- Construction: "Theorem `thm:normal_cs` gives the fixed normal-mixture construction with `V_n = n`, `rho = 100`
  and `alpha = 0.05`: `r_n = sqrt((n+100) log{(n+100)/(100 * 0.05^2)}) / n`. Apply
  `[Zbar_n - r_n, Zbar_n + r_n] ∩ [-1,1]` and its success-difference analogue, **without intersections across times
  because the targets can move**" (`:90-97`).
- Results: `r_295 = 0.18284`; NB band `[-0.65403, -0.28835]`; success-difference band `[-0.13199, 0.23369]`; first
  negative NB upper endpoint at pair 60; success lower endpoint never exceeds `-0.03`; "These two separate 95%
  constructions do not form a joint 95% region"; "the post-hoc choice of this analysis is not adjusted for
  selection"; "implies no realized savings" (`:97-106`).

**Code** (`experiments/build_open_coding_results.py:142-149`):
```python
n = np.arange(1, 296)
radius = normal_mixture_radius(n, alpha=.05, rho=100.)
nb = np.cumsum([r['score'] for r in pairs]) / n
sd = np.cumsum([r['success_difference'] for r in pairs]) / n
... 'nb_lo': max(-1., z - rad), 'nb_hi': min(1., z + rad), 'success_lo': max(-1., d - rad), 'success_hi': min(1., d + rad)
```
Outputs: `results/open_coding/running_mean_bands.csv` (295 rows), `summary.json`
(`final_marginal_r1`, `first_negative_nb_upper_endpoint = 60`, `any_success_lower_above_minus_003 = false`,
`analysis_status` = "Post-hoc fixed construction, no adjustment for analysis selection; conditional-mean target, not
full-roster inference; two marginal 95% bands, not joint 95%."). Reproduced exactly in section 4.2.

**Theorem and assumptions cited** — `thm:normal_cs` (`theory.tex:288-329`), set-up at `theory.tex:271-286`:
1. `(F_i)` a filtration to which the scores are adapted;
2. known `F_{i-1}`-measurable bounds `a_i <= Z_i <= b_i` ("The predictable bounds must hold before observing `Z_i`"),
   `V_n = (1/4) sum (b_i-a_i)^2`; balanced ternary scores give `V_n = n`;
3. "Fix `rho > 0` and `alpha in (0,1)` **before examining this score stream**";
4. conclusion `P{mubar_n in C_n for every n >= 1} >= 1 - alpha`; intersecting with a known parameter range is allowed;
5. proof = conditional Hoeffding + `N(0, 1/rho)` mixture + Ville; "No identical-distribution assumption appears ...
   the target is the running average conditional effect, not the effect at the latest arrival or a future workload"
   (`theory.tex:331-338`).
The Round 11 scope review restates the proof for this stream and what it does *not* give
(`round11_coding_target_scope.md:20-37, 84-90`): not the all-pairs fixed-roster functional `theta_N`, not an iid
task-superpopulation (R2) statement, not a joint region, not selection-adjusted. The same construction was the only
inference retained for the airline replay (`paper/open_airline_appendix.tex:118-137`;
`round12_airline_inference_review.md:20-39`), there with filtration `G_0 = sigma(Y,P)`, `G_n = G_0 ∨ sigma(R_1..R_n)`.

---

## (d) Python API (verified by import and execution)

### d.1 Signatures (`src/winstats.py`)
```python
@dataclass(frozen=True)
class Tier: name: str; higher_better: bool = True; absolute_tolerance: float = 0.0; relative_tolerance: float = 0.0   # :11-22
compare(a, b, tiers, eligible=None) -> (sign int8 array, decisive_tier int16 array)      # :25-48  a,b shape (..., n_tiers)
normal_mixture_radius(n, alpha=.05, rho=100., variance_process=None) -> radius array      # :51-61  two-sided; V=n default
betting_log_e_ternary(positive, negative, n, threshold=0., bets=40) -> log E array        # :64-85  cumulative COUNTS, not scores
summary(scores) -> dict(p_win, p_loss, p_tie, net_benefit, win_ratio, win_odds)            # :88-93
```
Notes: `betting_log_e_ternary` is valid only for scores in `{-1,0,1}` (balanced `q = 1/2`), `threshold in (-1,1)`,
grid `np.geomspace(1e-4, .99/(1+threshold), bets)` (`:80`), returns `logsumexp(...) - log(bets)`; compare with
`np.log(1/alpha_j)`. Harm direction = swap the counts (`positive=#losses, negative=#wins`, `threshold=0`).
Partial-score lower wealth = pass counts of the lower enclosures `l_i(t)` (ternary) — exactly what the root does in
`experiments/run_async_experiment.py:81-84, 146-155`. For non-ternary/IPW scores use `variance_process` in the radius
and do not use the ternary betting function.

### d.2 Toy code (full file: `R1_toy_api_check.py`; core part reproduced)
```python
import sys, csv, numpy as np
sys.path.insert(0, '<REPO>/src')
from winstats import Tier, compare, normal_mixture_radius, betting_log_e_ternary, summary

TIERS = (Tier('success', True, relative_tolerance=0.0),
         Tier('latency_s', False, relative_tolerance=0.1),
         Tier('completion_tokens', False, relative_tolerance=0.1))

def pair_score(cand, inc):                      # positive = candidate wins (root builder convention)
    vals = lambda r: [int(r['success']), r['latency_s'], r['completion_tokens']]
    both = bool(cand['success'] and inc['success'])
    z, tier = compare(vals(cand), vals(inc), TIERS, [True, both, both])
    return int(z), int(tier), int(cand['success']) - int(inc['success'])

rng = np.random.default_rng(7); n_max = 120
z = rng.choice([1, 0, -1], size=n_max, p=[.70, .06, .24])       # net-benefit pair scores (enrollment order)
d = rng.choice([1, 0, -1], size=n_max, p=[.20, .60, .20])       # success-difference pair scores
ALPHA, RHO, DELTA = .05, 100., .03
A_NB = A_S = ALPHA / 2                                           # thm:drift_gate split over J+1 = 2 gates
n = np.arange(1, n_max + 1)
pos, neg = np.cumsum(z > 0), np.cumsum(z < 0); dpos, dneg = np.cumsum(d > 0), np.cumsum(d < 0)
nb, sd = (pos - neg) / n, (dpos - dneg) / n
r_nb = normal_mixture_radius(n, alpha=A_NB, rho=RHO); r_sd = normal_mixture_radius(n, alpha=A_S, rho=RHO)
nb_lo, nb_hi = np.maximum(-1, nb - r_nb), np.minimum(1, nb + r_nb); sd_lo = np.maximum(-1, sd - r_sd)
loge_nb   = betting_log_e_ternary(pos,  neg,  n, threshold=0.)       # H0: running mean NB <= 0
loge_sd   = betting_log_e_ternary(dpos, dneg, n, threshold=-DELTA)   # H0: running mean SD <= -delta
loge_harm = betting_log_e_ternary(neg,  pos,  n, threshold=0.)       # H0: running mean of -Z <= 0
deploy_cs  = (nb_lo > 0) & (sd_lo > -DELTA)                          # same prefix, no retention
deploy_bet = (loge_nb >= np.log(1/A_NB)) & (loge_sd >= np.log(1/A_S))
# partial scores: replace pending pair scores by their guaranteed lower enclosure (-1 if nothing certified)
ell = z.copy(); ell[[3, 17, 40]] = -1
loge_partial = betting_log_e_ternary(np.cumsum(ell > 0), np.cumsum(ell < 0), n, threshold=0.)
assert np.all(loge_partial <= loge_nb + 1e-12)                       # pathwise domination (thm:async_betting)
```

### d.3 Output (`R1_toy_api_check.out`, run with `.venv/bin/python`, < 2 s)
```
== 1. compare() on hand cases (z, decisive_tier, success_diff) ==
cand ok 2.0s vs inc ok 9.0s      -> (1, 1, 0)
cand fail vs inc ok              -> (-1, 0, -1)
both fail (resource tiers off)   -> (0, -1, 0)
lat within 10% of larger, tokens -> (1, 2, 0)
exact threshold equality is a tie-> (0, -1, 0)

== 2. toy stream, n_max=120, alpha split 0.025/0.025, rho=100, delta=0.03 ==
n= 20 NB=+0.200 CS=[-1.000,+1.000] SDlo=-1.000 logE_nb=0.01 logE_sd=-0.15 logE_harm=-0.29
n= 60 NB=+0.483 CS=[-0.107,+1.000] SDlo=-0.657 logE_nb=4.76 logE_sd=-0.26 logE_harm=-0.57
n=120 NB=+0.475 CS=[+0.122,+0.828] SDlo=-0.387 logE_nb=11.41 logE_sd=-0.26 logE_harm=-0.70
log(1/alpha_j)=3.689
first n with CS lower NB > 0            : 68
first n with betting NB gate crossed    : 49
first n with BOTH betting gates same n  : None
first n with BOTH CS lower bounds same n: None
summary(z): {'p_win': 0.725, 'p_loss': 0.25, 'p_tie': 0.025, 'net_benefit': 0.475, 'win_ratio': 2.9, 'win_odds': 2.8095238095238093}

== 3. partial lower wealth <= full wealth at every prefix: OK; envelope max_n logE_partial = 11.05 vs full 13.25 ==

== 4. root coding stream (B=self_test_repair minus A=single_shot), n=295 ==
W/T/L = 69 18 208  NB=-0.4711864407
radius(295)=0.1828387393 band=[-0.6540251800, -0.2883477014]
first n with upper endpoint < 0: 60
alpha_j=0.0500: CS upper<0 first at n=60; betting harm gate (log E >= 3.00) first at n=14; radius(295)=0.1828
alpha_j=0.0250: CS upper<0 first at n=63; betting harm gate (log E >= 3.69) first at n=41; radius(295)=0.1993
alpha_j=0.0167: CS upper<0 first at n=65; betting harm gate (log E >= 4.09) first at n=42; radius(295)=0.2083
success gate B-A: max log E over prefixes = 0.812 (needs 2.996); max CS lower = -0.1320 (needs > -0.03)
success gate A-B: max log E over prefixes = 0.800 (needs 2.996); max CS lower = -0.1906 (needs > -0.03)
```
Block 4 reproduces the root's numbers to all printed digits (`results/open_coding/summary.json`,
`open_coding_appendix.tex:97-100`). Extra check: on the pilot stream the alpha = .05 harm wealth is `>= 20` at
prefixes {14, 24} among n < 30, first at n >= 20 is 24 (the owner's "pair 24"), and it stays above only from n = 48.
Read by symmetry, block 4 is also the T1 pilot (candidate = single_shot): NB gate would cross around n = 41-65.

### d.4 Feasibility sketch for the success guardrail (crude expected-growth calculation, block 5 of the script)
`pairs ~ (log(1/alpha_j) + log 40) / max_lambda E log(1 + lambda (D - c))`, true success difference 0, discordance `q = P(D != 0)`:

| discordance q | delta = 0.03 | delta = 0.05 | delta = 0.10 |
|---|---:|---:|---:|
| 0.39 (cross-task pairs at 73% success; pilot first pass had 119/295 = 0.40) | ~5,800-6,400 | ~2,100-2,300 | ~530-580 |
| 0.20 | ~3,000-3,300 | ~1,100-1,200 | ~285-315 |
| 0.10 (e.g. pairing within a pilot-difficulty stratum) | ~1,550-1,720 | ~580-640 | ~170-185 |

(ranges = alpha_j .05 to .025). Normal-mixture radius (`R1_radius_table.out`): `r_n <= 0.10` first at n = 922
(alpha_j = .05) / 1,076 (.025); `r_n <= 0.03` at n = 12,094 / 13,778; `r_295` = 0.183 / 0.199 / 0.208 / 0.215 for
alpha_j = .05 / .025 / .0167 / .0125. The exact Monte Carlo power analysis belongs to the power reader; the point
here is that with 295 cross-task pairs **no accepted construction can certify a 0.03 (or even 0.10) success margin**,
so a live *deploy* stop is unreachable in T1 as currently sized, while NB and harm crossings are easy.

---

## (e) Delayed / out-of-order reveals, pairing, informative delay, and what a physically randomized stream must satisfy

### e.1 What the paper says
- **Completed-prefix baseline** (`main.tex:203-213`; `prop:delay`, `theory.tex:535-563`): analyse the completely
  matured prefix of enrolled pairs; `N(t)` may be any data-dependent integer such that the first `N(t)` pairs are
  complete; coverage transfers pathwise, no stopping-time property needed. "Selecting whichever runs finish first can
  preferentially include fast successes and change the comparison law ... this is not a license to delete missing or
  slow episodes." "Naively sorting by completion time or selecting only completed successes can change the comparison
  population." Failure to reach the outcome by the horizon "is an endpoint, not an observation to discard".
  The root's async simulation shows completed-only selection falsely deploying in 1000/1000 null runs
  (`paper/async_results.tex:18-21`).
- **Partial-score enclosures** (`asynchronous.tex:15-56`): enrollment filtration `(F_i)` "need not be the
  calendar-time filtration actually observed by the evaluator". Required: `X_i` is `F_i`-measurable,
  `a_i <= X_i <= b_i` predictable, `mu_i = E(X_i | F_{i-1})`. At calendar time `t`, `N(t)` = number of *fully enrolled
  and randomized* pairs; evaluator information `G_t` supplies `a_i <= l_i(t) <= X_i <= u_i(t) <= b_i` **simultaneously
  for every enrolled i and every t** (eq. `eq:async_enclosures`). "Outcome-dependent delay, out-of-order updates, and
  partial information are allowed. The observation process does not need to make `X_i` independent of its reveal
  time." A prediction or pointwise interval is not an enclosure; if enclosures hold only w.p. `1-eta`, add `eta`.
- **CS from all enrolled pairs** (`asynchronous.tex:85-143`, `thm:async_cs`):
  `L_{n,t} = (sum_{i<=n} l_i(t) - B_alpha(V_n))/n`, `U_{n,t}` analogous, valid for every `t` and every
  `1 <= n <= N(t)`; "The bounds use `n`, not the number of completed episodes, in both the sum and the boundary";
  no need for `N(t)` or a display time to be an `F`-stopping time. Width = complete-data width +
  `n^{-1} sum (u_i - l_i)` (eq. `eq:async_width`).
- **Partial-score betting** (`asynchronous.tex:145-245`): lower wealth with the *committed* stakes; "Past factors are
  recomputed or updated when an enclosure improves; they are not counted as fresh independent observations";
  `thm:async_betting` controls the threshold crossing over all `(n,t)` **under the pointwise conditional null**; it
  "does not assert that [the partial wealth] is a martingale or an e-process in `(G_t)`". Prefix envelope
  `max_{n<=N(t)}` needs no alpha division over prefixes and never crosses later than the completed-prefix test
  (`cor:async_envelope`). Widening a previously stated enclosure means the enclosure guarantee was invalid (`:235-238`).
  Under drift "maximizing lower bounds across prefixes does not produce a lower bound for `mubar_{N(t)}`. The drifting
  analysis should retain the selected prefix and its corresponding target explicitly" (`:240-245`).
- **Enclosures from traces** (`asynchronous.tex:247-300`): `l^h_i(t) = inf`, `u^h_i(t) = sup` of `h(a,b)` over all
  feasible completions; component enclosure `[g_A^- - g_B^+, g_A^+ - g_B^-]`. Worked certificate: A finished with
  success at cost 1, B pending with accrued cost 2, 5% tolerance, nondecreasing cost -> `l = u = 1` before B
  completes, while the success-difference enclosure is still `[0,1]` (`:283-292`; also `main.tex:289-293`).
  "Absence of a violation so far is not a certificate"; accumulated cost is a lower bound only if it cannot decrease;
  "Evaluation cannot improve evidence by deleting that pair" (`:294-300`). Live use "must validate its own terminal
  semantics, irrevocable costs, grader errors, enrollment assumptions, and information available at each decision"
  (`paper/trace_certificate_appendix.tex:96-99`).
- **Conjunctions with partial scores** (`asynchronous.tex:369-400`): stationary -> each gate at `alpha`, gates may
  cross at different times/prefixes; drifting -> "use the bounds `eq:async_cs` **for the same stated enrolled
  prefix**, allocate the confidence-sequence error across all required criteria, and require every lower bound to
  exceed its threshold ... A historical partial-bound crossing cannot be retained". "Stopping enrollment does not
  authorize changing the endpoint definition for pending episodes. If deployment terminates pending runs, either the
  prespecified intervention includes that termination or the estimand remains the stated hypothetical continuation
  through the frozen horizon."
- **Sufficient experimental model** (`asynchronous.tex:57-83`): independent full potential records and reveal paths
  per pair, fixed systems and outcome protocol, **no cross-pair interference**; "Pair orientation is then drawn with a
  fresh recorded randomization coin; its probability can depend on information from previously enrolled pairs";
  design-based version: condition on all potential records and reveal paths, "with independent assignment coins
  supplying the randomness". Warning: "revealing all earlier final records in a mathematical filtration can change a
  conditional-mean restriction. Shared infrastructure effects, interference, or adaptive candidate updates require
  their own justification. The hierarchy must not be refitted after a pending episode's partial outcome is seen."
- The root's own wish-list for this experiment: "actual reveal timestamps, nonanticipating certificates, fixed
  endpoint horizons and the matched completed-prefix comparator ... Specify the target and shared-resource
  assumptions first" (`reviews/round9_experiment_gap_assessment.md:35`); "reliable reveal timestamps and
  enrolled-outcome retention" (`reviews/round12_completion_scope_review.md:54`); `EXPERIMENT_QUEUE.md:35`.

### e.2 Pairing rule implied for a single-exposure stream
Pairs are **consecutive arrivals in the prespecified arrival order** (positions fixed before the orientation is
randomized, `theory.tex:181-187`), optionally within a prespecified outcome-blind stratum (`main.tex:171-172`).
One fair coin per pair: `R_i = 1` -> candidate on arrival `2i-1`, incumbent on arrival `2i`; `R_i = 0` reversed. Each
arrival is executed under exactly one arm; each pair contains exactly one episode per arm. An odd last arrival is
unpaired and is outside the monitored stream (the pilot had one: `open_coding_appendix.tex:33-35`). Pairing the
k-th candidate completion with the k-th incumbent completion, or pairing by reveal time, is outcome-dependent
matching and is not covered.

### e.3 The filtration, stated precisely
Let `i = 1..N` index enrolled pairs in arrival order. Let `W_i` = complete fixed-horizon records of both episodes of
pair `i` (success, latency, tokens, all attempts, timestamps).

- `F_0 = sigma(roster, arrival permutation, pairing/strata, frozen protocol: hierarchy, tolerances, horizon, caps,
  systems/model hashes, alpha_j, rho, stake grid, n_min, N_max)`. In the design-based reading `F_0` additionally
  contains all potential records `{Y^a_{ir}}` and reveal paths of all pairs (`asynchronous.tex:68-70`).
  **`F_0` contains no coin and no seed that determines a coin.**
- `H_i = F_{i-1} ∨ sigma(information used to form pair i)`; `P(R_i = 1 | H_i, {Y^a_{ir}}) = 1/2`
  (`theory.tex:188-195`: "satisfied by a fresh randomization coin with its recorded probability. It excludes
  assignments driven by unrecorded current outcomes").
- `F_i = F_{i-1} ∨ sigma(R_i, W_i)`, and `F_{i-1} ⊆ H_i` (`theory.tex:218-221`).
- Therefore: **`R_i` (the current pair's coin) is not in `F_{i-1}`; it enters at `F_i`. `R_1..R_{i-1}` are in `F_{i-1}`.
  `R_{i+1}, ...` are in no `F_j, j <= i`, and must be physically non-existent when pair `i` is executed.**
  `mu_i = E(Z_i | F_{i-1}) = E(m_i | F_{i-1})` = fair average of the two orientations of pair `i`; target = `mubar_n`.
- What goes wrong otherwise is the root's exact counterexample (`round12_coding_correction_and_baseline_delta.md:41-49`):
  with the orientation sequence in `F_0`, task `s` always succeeding and `t` always failing, `E(Z_k | F_{k-1})` is the
  realized `+/-1`, not the symmetric average 0. Also `round11_coding_target_scope.md:50`: "do not condition `F_0` on
  the complete orientation sequence or a seed that determines it and simultaneously assert conditional fair-coin
  assignment"; airline analogue: "The pre-pair filtration contains the array, matching and earlier revealed coins,
  but not future coins" (`open_airline_appendix.tex:124-125`).
- The monitor's real information `G_t` (reveal order, timestamps, partial traces) is a different filtration. It is
  never used for a martingale argument; every live decision at `(n,t)` implies a statement about the latent
  enrollment-order process, which is where the error bound lives (`asynchronous.tex:111-127, 181-198`). Consequently
  the live stopping time needs no stopping-time property with respect to `F`.

### e.4 Conditions that make the guarantees hold by design
Coverage / crossing control (need only `thm:normal_cs` or `prop:bet_running`):
1. Score definition, hierarchy, tolerances, horizon, caps, `alpha_j`, `rho = 100`, stake grid, `n_min`, maximum `N`,
   prefix rule and enclosure rule frozen (committed, hashed) before the first trial episode.
2. `Z_i, D_i in {-1,0,1}` by construction (`q = 1/2`, balanced) -> predictable range 2, `V_n = n`.
3. Every enrolled pair stays in its enrollment position forever; pending pairs contribute `[l_i(t), u_i(t)]`; `n` in the
   radius counts all pairs in the prefix. Failure, timeout, crash, infrastructure error = endpoint values defined ex
   ante (success 0, resource fields recorded), never missing, never re-run for a better outcome.
4. Enclosures are logically guaranteed: pending success in `{0,1}`; latency lower bound = elapsed workflow time so
   far (monotone), upper bound = per-episode cap; tokens lower bound = tokens already generated. Never a prediction.
5. Same-prefix conjunction with split alpha; no retained crossings; no running intersection of bands.
These five give `P(any false deploy or false harm statement about the running target at its prefix) <= alpha` under
arbitrary dependence, machine drift and informative delay.

Causal / fair-coin reading of `mu_i` (needs `thm:pair_id`), additionally:
6. Coin per pair from OS entropy, drawn at enrollment of the pair, written to the hash-chained log **before** either
   episode starts, never precomputed, probability exactly 1/2, independent of everything else.
7. Execution is nonanticipating: nothing about pair `i` (prompt, server state, scheduling, retries, operator action)
   may depend on `R_j, j > i`; nothing about the coin may depend on outcomes.
8. **No cross-pair interference.** `F_{i-1}` contains the *final* records of pair `i-1`, which with concurrent workers
   may still be running when `R_i` is drawn and pair `i` starts. If pair `i`'s orientation changes pair `i-1`'s record
   (shared GPU -> wall-clock `latency_s`; load-induced timeouts -> `success`), then conditioning on `F_{i-1}` is
   informative about `R_i` and `E(Z_i | F_{i-1}) != E(m_i | F_{i-1})`. This is exactly the
   `asynchronous.tex:72-76` warning. Options, to be chosen and stated ex ante ("Specify the target and
   shared-resource assumptions first"):
   (a) pair-synchronous concurrency: the two workers run the two arrivals of the *same* pair; the next pair is
       enrolled only when both finish. Within-pair interference is absorbed into the pair-level potential scores
       `(U_i, V_i)` (the proof of `thm:pair_id` uses only those), there is no cross-pair overlap, and within-pair
       out-of-order reveals still give real timestamps and early certificates;
   (b) sliding-window concurrency with load-invariant tiers (success, model calls, tokens) in the hierarchy and
       wall-clock latency reported but not scored;
   (c) sliding-window concurrency with wall-clock latency scored, claiming only the running history-conditional-mean
       guarantee (items 1-5) and stating that the fair-coin reading assumes negligible cross-pair load effects.
   For the A/A control the coin only relabels identical systems, so the null `mu_i = 0` is exact under any of these.
9. Fixed systems for the whole trial (model files, server build, sampling settings, prompts); a changed version
   "should ordinarily start a separately specified experiment" (`theory.tex:335-338`). Independent per-episode
   sampling seeds (not shared across units — airline criticism, `open_airline_appendix.tex:111-115`).
10. After a live decision: in-flight pairs run to their frozen horizon and are recorded (or early termination is
    declared part of the intervention ex ante); the decision is about `mubar_n` at the logged prefix `n`, not about
    future arrivals (`theory.tex:524-531`). Post-decision single-arm traffic is outside the monitored process; its
    realized exposure counts are measurements, not inference.

---

## (f) Pitfalls for the live implementation (short list)

1. **Per-arrival coin vs per-pair orientation coin.** Use one coin per disjoint consecutive pair; otherwise the run is
   outside `thm:pair_id` and cannot "enter the paper without re-analysis".
2. **Completion-order scoring.** Never accumulate scores in reveal order and never drop pending pairs; evaluate
   enrollment prefixes with enclosures; `n` = enrolled pairs in the prefix.
3. **Coin or seed in `F_0`.** No precomputed orientation list, no design seed for orientations; log raw entropy bytes
   and the coin before execution; anchor the log head in git before the first episode and periodically.
4. **Post hoc parameters.** `rho`, `alpha_j`, `delta`, stake grid (40, `geomspace(1e-4, .99/(1+c))`), `n_min`, look
   rule, hierarchy, tolerances, horizon, `N_max`, harm rule — all frozen in a committed protocol whose hash is the
   first log entry. `rho = 100` is the library default; changing it after data invalidates the guarantee.
5. **Alpha accounting.** Split across gates (and the harm gate if betting is used); state whether T1-T4 are each at
   0.05 or share a program-level 0.05; say "joint" only if the split was made. Two bands at .05 each are marginal
   (generic joint guarantee only 90%).
6. **Retention and dips.** Wealth is not monotone (pilot: above 20 at n = 14 and 24, below until 48). Log the decision
   with its prefix `n`, calendar time, all gate values and the log-chain hash at the instant of crossing.
7. **No running intersection** of bands across `n`; clip to `[-1,1]` only.
8. **`betting_log_e_ternary` takes cumulative counts** `(positive, negative, n)`, ternary balanced scores only; harm =
   swapped counts; compare `log E` with `log(1/alpha_j)`. `normal_mixture_radius` is two-sided.
9. **Success guardrail power.** With ~295 cross-task pairs no accepted construction certifies `delta <= 0.10`;
   decide ex ante between a larger justified margin, stratified pairing (pilot-difficulty strata are outcome-blind
   for the new trial), more arrivals (several passes with fresh coins and independent seeds), or declaring that the
   expected live event in T1 is "NB gate passes, guardrail abstains" (which is not a deployment).
10. **Shared-resource interference** with 2+ workers on one GPU (latency tier, load-induced timeouts). Choose 8(a),
    (b) or (c) explicitly; record concurrent load per episode.
11. **Enclosures must be certain and never widen.** Elapsed latency is a valid lower bound only if the endpoint clock
    cannot restart; define what a retry/reconnect does to `latency_s` and tokens. If an enclosure can fail with
    probability `eta`, the bound is `alpha + eta`.
12. **Failures are outcomes.** Server errors, sandbox crashes, timeouts and retries produce endpoint values and full
    usage rows for every attempt (airline criticism: 12 discarded attempts without complete usage). No "first
    attempt that completes" retention rule unless frozen ex ante and coin-independent.
13. **Sampler receipt.** Record, per request, the sampling parameters as received/applied by the server (server-side
    log or echo), not just what the client sent (`round12_integration_ledger.md:24`: "Actual sampler receipt ...
    remain unverified").
14. **Amendments.** Any change after the freeze needs an immutable timestamped record (pushed commit / chain anchor)
    before the next episode, plus who had seen which outcomes (airline amendment criticism,
    `open_airline_appendix.tex:75-97`). A changed system version starts a new trial.
15. **Stopping with pending pairs.** Let in-flight episodes reach the frozen horizon; report the final all-enrolled
    band as well as the decision-time band; do not redefine endpoints for pending episodes.
16. **Orientation and labels.** `compare(candidate, incumbent)`; positive favours the candidate; do not mix the
    paper's "A = candidate" convention with the coding convention "B = candidate".
17. **Claims.** A crossing is a statement about the running history-conditional mean of this laboratory stream at the
    logged prefix: not the all-pairs roster functional, not a task superpopulation, not future workload, not
    production. One A/A stream is not an empirical type-I-error estimate
    (`round9_experiment_gap_assessment.md:15`). "NB upper < 0" is not success harm and not reverse approval of the
    incumbent. Realized exposure savings may be reported as measured counts for this stream only.
18. **Pilot reuse.** The 1,182 pilot episodes may inform power and strata only; any tuning of `rho`, stakes, tolerances
    or margin on them must be declared as ex ante design based on external data, and the trial tasks' new outcomes
    must play no role.

---

## Open questions for the root (GitHub issue before freezing)

1. Will the root accept a **prespecified harm gate**, and in which form: (i) "two-sided normal-mixture NB upper endpoint
   `< 0` at the current prefix" (no extra alpha), or (ii) betting on `-Z` with threshold 0 at `alpha_H` under
   `prop:bet_running`? It is not in the paper today and the pilot's harm e-process was labelled descriptive.
2. Is the **partial-score betting crossing under the running-average null** acceptable? `thm:async_betting` is stated
   for the pointwise conditional null and `asynchronous.tex:381-388` names only the CS for drifting targets; the
   extension (partial wealth `<=` full wealth at the same prefix, then `prop:bet_running`) is a one-line corollary but
   is not written in the paper.
3. Which construction is **primary**: split normal-mixture (the literal accepted analysis, low power for the
   guardrail) or split fixed-grid betting (same theorems, more power)? And the alpha allocation: `.025/.025`,
   `alpha/3` with a harm gate, per-trial 0.05 or a program-level split over T1-T4?
4. **Success margin and pairing.** Is a margin larger than 0.03, or pairing within pilot-difficulty strata, or several
   passes over the roster acceptable, given that 295 cross-task pairs cannot certify 0.03 by any accepted method?
5. **Concurrency model** for the fair-coin reading: pair-synchronous workers (8a), load-invariant tiers (8b), or
   wall-clock latency with the weaker history-conditional claim only (8c)?
6. Is a **permutation of the finite roster** (running-average target, split alpha) preferred, or iid-with-replacement
   arrivals by physical randomization (which could justify the stationary IUT rule without a split)?
