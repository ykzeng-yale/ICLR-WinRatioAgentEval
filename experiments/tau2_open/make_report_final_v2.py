"""Round 12 REPORT-ONLY corrections of the tau2_open owner report. No model call, no analysis rerun, no git command.

Reads results/tau2_open/report_final.md (never modified) and results/tau2_open/round10_handoff_numbers.json, applies the
exact-text replacements listed in REPLACEMENTS (each must match exactly once, otherwise the script aborts), prepends a
Round 12 status section, and writes

    results/tau2_open/report_final_v2.md
    results/tau2_open/report_final_v2_manifest.json   (sha256 of source and output, the replacements, recomputed numbers)

The only numbers that are new are the final observed-minus-target errors and the success-difference path check of the
observed-array replay illustration; both are recomputed here from the per-pair rows of round10_handoff_numbers.json.
Numbers quoted in the new text that do not appear verbatim in report_final.md: the same-task comparison counts
28 / 141 / 27 (= 196 x the p_win / p_tie / p_loss of summary.json), the reward-basis counts 124 / 70 / 2 (= the termination
counts of section 7.1: user_stop; max_steps + too_many_errors; infrastructure_error) and the root session's lower bound of
246,284 omitted generated arm-A tokens (reviews/round12_integration_ledger.md on main). Every other number is copied
from report_final.md unchanged.

Usage: .venv/bin/python experiments/tau2_open/make_report_final_v2.py
"""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / 'results' / 'tau2_open'
SRC, OUT, MAN = RD / 'report_final.md', RD / 'report_final_v2.md', RD / 'report_final_v2_manifest.json'
REVIEWED_HEAD = '55fb1e51234ad712c56799455bd704b829ed1d26'
ROOT_INTEGRATION = '45e8ee2715f148c81db7f6510d66677f57e03f0a'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def replay_numbers() -> dict:
    """Final errors and path checks of the observed-array replay illustration, from the per-pair rows."""
    h = json.load(open(RD / 'round10_handoff_numbers.json'))['orientation_randomization_reading']
    pairs = h['pairs']; n = len(pairs); assert n == 49
    out = {}
    for name, obs, r1, r0 in (('net_benefit', 'z_obs', 'z_R1', 'z_R0'), ('success_difference', 'dq_obs', 'dq_R1', 'dq_R0')):
        so = st = 0.0; worst = (0.0, 0); inside = True
        for k, p in enumerate(pairs, 1):
            so += p[obs]; st += 0.5 * (p[r1] + p[r0])
            rad = math.sqrt((k + 100) * math.log((k + 100) / (100 * 0.05 ** 2))) / k   # normal mixture, V = k, rho = 100, alpha = 0.05
            err = abs(so / k - st / k)
            if err > worst[0] + 1e-15: worst = (err, k)
            inside &= err <= rad
        rec = h['all_pairs_49'][name]
        assert abs(so / n - rec['observed_running_mean']) < 1e-12
        assert abs(st / n - rec['orientation_averaged_target_computed_from_observed_array']) < 1e-12
        assert abs(rad - rec['radius']) < 1e-9, (rad, rec['radius'])
        out[name] = dict(observed=so / n, target=st / n, final_abs_error=abs(so / n - st / n), max_abs_path_error=worst[0],
                         max_abs_path_error_at_n=worst[1], target_inside_at_every_n=bool(inside), final_radius=rad)
    assert abs(out['net_benefit']['max_abs_path_error'] - h['path_check_net_benefit']['max_abs_running_mean_minus_running_target']) < 1e-12
    return out


def build():
    t = SRC.read_text()
    r = replay_numbers()
    nb, sd = r['net_benefit'], r['success_difference']
    assert round(nb['final_abs_error'], 6) == 0.010204 and round(sd['final_abs_error'], 6) == 0.020408

    REPLACEMENTS = [
        # -- correction 2 and 4: summary paragraph (section 1)
        ("summary: separate descriptive observations from model-dependent intervals; drop 'significantly'",
         "Both arms succeeded on 15 of 98 units (15.3%) (N, S). The same-task success difference is 0.000 with 95% task-clustered interval [-0.114, 0.114] (S). Under the frozen hierarchy (success > agent completion tokens at 5% relative tolerance > assistant tool calls, absorbing rule) the net benefit of B is indistinguishable from 0 on both prespecified contrasts: cross-arrival (E1, 49 prespecified pairs) NB = 0.020, 10 wins / 30 ties / 9 losses, corrected 95% betting CS [-0.366, 0.406]; same-task shadow (E2, 49 task clusters) NB = 0.005, 95% interval [-0.111, 0.121] (S). The guarded decision is **abstention (`inconclusive`)**: neither a deploy signal nor a harm signal; the three e-processes never moved (largest log e-value anywhere 0.91, at pair 12 inside the unread n < 20 window; largest value read from pair 20 on 0.22; threshold 3.00) (P, S). On resources, B used significantly fewer assistant tool calls (same-task -4.68 per episode, [-6.87, -2.50]; 5.3 versus 10.0) and less agent generation time (-44.1 s, [-75.3, -12.9]; 84 s versus 128 s), while the difference in agent completion tokens is **not resolved** in the same-task pairing (-262, [-882, 358]) (S). This is an abstention example at small n, not a finding that the two agents perform the same.",
         "**Descriptive observations (canonical retained records).** Both arms succeeded on 15 of 98 units (15.3%) (N, S); the same-task success difference is 0.000. Under the frozen hierarchy (success > agent completion tokens at 5% relative tolerance > assistant tool calls, absorbing rule): cross-arrival replay (E1, 49 prespecified pairs) 10 wins / 30 ties / 9 losses, NB = 0.020; same-task contrast (E2, 196 comparisons in 49 task clusters) 28 wins / 141 ties / 27 losses, NB = 0.005 (S). The comparisons within a task are not independent sample counts. On canonical records B made fewer assistant tool calls per episode (5.3 versus 10.0; same-task mean difference -4.68) and had less agent generation time (84 s versus 128 s; -44.1 s); the mean difference in agent completion tokens was -262 (S). The replay of the prespecified monitoring rule gives **abstention (`inconclusive`)**: neither a deploy signal nor a harm signal; the three e-processes never moved (largest log e-value anywhere 0.91, at pair 12 inside the unread n < 20 window; largest value read from pair 20 on 0.22; threshold 3.00) (P, S). "
         "**Observed-array replay illustration (section 12.1; optional, post hoc).** Conditional on the complete retained array and the matching, and under the nominal model of independent fair replay coins, the final marginal 95% band for the orientation-averaged net-benefit target is [-0.609, 0.650]; that target is already computable from the array (0.0102). "
         "**Model-dependent intervals (kept in sections 3-4 for the record; not adopted by the root integration; Round 12 status section above).** The corrected betting CS for E1, [-0.366, 0.406], needs a common conditional mean of the pair scores or an iid-roster model with independent episodes; the task-clustered t intervals for E2 (NB [-0.111, 0.121]; success difference [-0.114, 0.114]) and for the components (tool calls [-6.87, -2.50]; generation time [-75.3, -12.9] s; completion tokens [-882, 358]) need independent tasks and a normal approximation. None of these assumptions is established by the design: two trial seeds are shared by all tasks, each arm ran as one batch, and the component variables are unbounded counts. No multiplicity adjustment was made. **No statistical-significance claim is made for any resource difference**, and canonical totals omit discarded attempts (the root's independent log reconstruction gives at least 246,284 additional generated arm-A tokens, `reviews/round12_integration_ledger.md` on main), so no operational-efficiency, total-cost or elapsed-saving claim is made either. Equal observed success is not equivalence and not non-inferiority. This is an abstention example at small n, not a finding that the two agents perform the same."),
        # -- correction 2: method-independent impossibility sentence (section 8)
        ("section 8: remove the method-independent impossibility assertion",
         "with 15% success and 49 tasks the success-difference half-width is 0.114 against a margin of 0.03, the design-based R1 radius is 0.63, and roughly 670 tasks would be needed at this spread. A guardrail of this size is not certifiable on a benchmark domain of 50 tasks at these success levels, whatever the method.",
         "with 15% success and 49 tasks the model-dependent task-clustered half-width for the success difference is 0.114 against a margin of 0.03, and the radius of the observed-array replay band (section 12.1) is 0.63; a variance-based sample-size heuristic for the task-clustered t interval gives roughly 670 tasks at this spread. (Round 12 correction.) The specified replay rule and the reported intervals did not certify the 0.03 margin on these data. That is a statement about these rules and these data. The retained records and a sample-size heuristic do not prove that no method could certify the margin on these tasks, and no such method-independent claim is made."),
        # -- correction 3: history-conditional alternative, final errors, joint coverage (section 12.1)
        ("section 12.1: history-conditional construction; final errors; marginal (not joint) bands",
         "No tau2 result is certified under the history-conditional alternative, which would need the assumptions of the previous paragraph.",
         "(Round 12 correction.) The history-conditional running-mean construction is not used in this report, and no tau2 result is reported under it. The earlier statement that it would need the assumptions of the previous paragraph is withdrawn: for any adapted score bounded in [-1, 1] the normal-mixture boundary covers the running mean of E[Z_k | F_(k-1)] without a common mean and without independent episodes. Reuse of tasks across the two blocks means that a constant conditional mean is not guaranteed; it does not mean that the conditional mean must vary in every model. "
         "Final observed-minus-target errors of the observed-array illustration at n = 49: net benefit |0.020408 - 0.010204| = **%.6f**; success difference |0.020408 - 0.000000| = **%.6f**. Largest error along the path: net benefit %.3f at n = %d; success difference %.3f at n = %d; for both scores the known target lies inside the band at every n from 1 to 49. "
         "The target and its guarantee are as stated above: the orientation average of the observed array, under nominal independent fair coins, with collection, amendment and retention independent of those coins. The net-benefit band and the success-difference band are **marginal** 95%% time-uniform bands. They do not form a joint 95%% statement: the union bound gives at least 90%% simultaneous coverage, and a joint 95%% statement would need the error budget to be split between them. No success non-inferiority and no guarded deployment is certified by either band."
         % (nb['final_abs_error'], sd['final_abs_error'], nb['max_abs_path_error'], nb['max_abs_path_error_at_n'], sd['max_abs_path_error'], sd['max_abs_path_error_at_n'])),

        # -- independent verification (reviews/session60_round12_report_corrections_verification.md), required fixes 1-4
        ("section 3.1 power paragraph: no unqualified impossibility wording (a)",
         "the interval's lower end, -0.114, cannot clear -0.03 whatever the truth.",
         "the lower end of this model-dependent task-clustered interval, -0.114, is far below -0.03, so this interval did not certify the margin (Round 12 correction: a statement about this interval and these data, not about every method)."),
        ("section 3.1 power paragraph: no unqualified impossibility wording (b)",
         "Forty-nine pairs cannot resolve a 0.03 guardrail; the protocol anticipated this",
         "With the prespecified rule and these intervals, 49 pairs did not resolve a 0.03 guardrail (Round 12 correction: not a method-independent statement); the protocol anticipated a short stream"),
        ("section 3.2: withdraw 'conservative for the finite-roster average'",
         "The intervals are conservative for the finite-roster average and conventional task-clustered intervals under a task-superpopulation model.",
         "(Round 12 correction.) The earlier sentence that these intervals are conservative for the finite-roster average is withdrawn. They are conventional task-clustered t intervals: model-dependent and approximate. Independence between tasks is not sufficient for them; they also need variance growth / nondegeneracy of the task scores, a Lindeberg or no-dominant-task condition and a consistent variance estimator. They are excluded from the root integration (section 0)."),
        ("section 3.3 table: no emphasis on interval cells (tool calls)",
         "| **-4.68 [-6.87, -2.50]** |", "| -4.68 [-6.87, -2.50] |"),
        ("section 3.3 table: no emphasis on interval cells (generation time)",
         "| **-44.1 [-75.3, -12.9]** |", "| -44.1 [-75.3, -12.9] |"),
        ("section 3.3 text: neutral wording instead of 'resolved'",
         "the two pairings disagree on whether the completion-token difference is resolved, and the same-task pairing is the prespecified test for H2.",
         "the model-dependent intervals of the two pairings differ on whether they contain 0 for the completion-token difference (section 0: no significance claim is made from either), and the same-task pairing is the prespecified contrast for H2."),
        ("section 7.2 sensitivity: neutral wording",
         "The duration interval then excludes 0 where the frozen one ([-77.1, 0.5]) just includes it; H2 remains unresolved either way. No conclusion of this report depends on the treatment.",
         "The model-dependent duration interval then lies below 0 where the frozen one ([-77.1, 0.5]) contains it; neither supports a significance claim (section 0), and the prespecified H2 criterion is not met either way. No descriptive observation of this report depends on the treatment."),
        ("section 8: descriptive instead of 'Resolved secondary facts'",
         "- Resolved secondary facts: B makes about half as many tool calls and spends about two thirds of the agent generation time;",
         "- Descriptive secondary observations on canonical records (Round 12 correction; no significance claim; canonical totals omit discarded attempts): B's mean tool calls were about half, and its mean agent generation time about two thirds, of A's;"),
        ("section 10: run manifest versus decision chronology",
         "| immutable run manifest | met | append-only, two invocations; invocation 1 has no completion record because it was stopped |",
         "| immutable run manifest | met for the run manifest only | append-only, two invocations; invocation 1 has no completion record because it was stopped. (Round 12 correction.) This does not extend to the decision chronology of deviation 1: there is no immutable record of when the amendment was decided (erratum; section 0), and that chronology remains unverified |"),
        ("section 10: independent-unit uncertainty rating",
         "| correct independent-unit uncertainty | met with stated limits |",
         "| correct independent-unit uncertainty | not established for the model-dependent intervals; met only for the observed-array replay statement (Round 12 correction) |"),
        ("section 10: repeated-task uncertainty rating",
         "| uncertainty appropriate for repeated tasks | met with stated limits (Round 10 wording correction) |",
         "| uncertainty appropriate for repeated tasks | not established: the intervals are model-dependent and excluded from the root integration (Round 12 correction; Round 10 wording correction retained) |"),
        ("section 12.1: name the coin model instead of 'by design alone'",
         "can guarantee for this array by design alone.",
         "can guarantee for this array under the nominal model of independent fair replay coins (Round 12 wording: the guarantee rests on that coin model, with collection, amendment and retention independent of the coins)."),
    ]
    applied = []
    for label, old, new in REPLACEMENTS:
        assert t.count(old) == 1, 'replacement target not found exactly once: ' + label
        t = t.replace(old, new); applied.append(dict(label=label, old_sha256=hashlib.sha256(old.encode()).hexdigest(), new_sha256=hashlib.sha256(new.encode()).hexdigest()))

    POINTER = ("\n> *Round 12 status pointer: the intervals, verdicts and decisions in this section are model-dependent and are excluded from the root integration; "
               "only the counts and means are descriptive observations (section 0).*\n")
    for heading in ('### 3.3 Components, B - A', '## 4. Decision rules and sensitivity', '## 5. Hypotheses H1-H5',
                    '### 7.2 Infrastructure errors: which units, and exactly how they are scored', '## 8. What this adds to the paper, and what it does not',
                    '## 10. Requirement checklist'):
        assert t.count('\n' + heading + '\n') == 1, heading
        t = t.replace('\n' + heading + '\n', '\n' + heading + '\n' + POINTER, 1)

    banner = f"""> **Round 12 report-only correction (2026-09-19).** This file is `report_final.md` (reviewed by the root session at `{REVIEWED_HEAD[:7]}`; kept byte-unchanged) with three passages replaced and this status section added, in response to the root session's Round 12 review (integration commit `{ROOT_INTEGRATION[:7]}` on main; `reviews/round12_integration_ledger.md`, `reviews/round12_airline_inference_review.md`). No model was run, no analysis was rerun, no observation, table or figure changed. Script: `experiments/tau2_open/make_report_final_v2.py`; hashes and the replaced passages: `report_final_v2_manifest.json`; binding wording: `experiments/tau2_open/protocol_addendum_round12.md`.

## 0. Round 12 status of every kind of statement in this report

| kind of statement | where | status |
|---|---|---|
| Canonical counts and means: 196 units, 194 saved trajectories, 2 infrastructure placeholders scored as failures, 15/98 successes per arm, replay 10 / 30 / 9, same-task 28 / 141 / 27, per-arm token, tool-call and time means, terminations, all-attempt accounting (206 attempts, 12 discarded) | sections 1, 3, 7, 12.3 | **Descriptive observations.** Accepted by the root as descriptive collection results. Reward labels are the archived tau2 labels (124 user-stop trajectories with a reward basis, 70 termination-based zeros, 2 missing), not independent re-adjudications. |
| Observed-array replay band for the orientation-averaged target | section 12.1 | **Optional post hoc illustration**, conditional on the full retained array and the matching, under nominal independent fair replay coins with collection, amendment and retention independent of the coins. The target is already computable from the array. Marginal bands, not joint. No new-task, fresh-run, production or stopping-gain inference. |
| Corrected betting CS for E1 (fixed mean), decided-pair win-ratio CS, task-clustered t intervals for E2 and for components, the independent-arm Welch intervals printed by the frozen `report.md`, H1-H5 verdicts that rest on those intervals | sections 3, 4, 5, 7.2, 8, 10 | **Model-dependent; assumptions not established by the design; excluded from the root integration.** Kept here for the record of the prespecified analysis. They are not to be read as supporting any conclusion beyond the descriptive rows above. |
| Decisions derived from intervals or sensitivity variants (decision-rule table and hierarchy / tolerance sensitivity in section 4, infrastructure-exclusion sensitivity in section 7.2, omit-five sensitivity in section 12.4), and the interval-based ratings of sections 8 and 10 | sections 4, 7.2, 8, 10, 12.4 | **Model-dependent and post hoc where marked; excluded from the root integration.** They are outputs of the stated rules on these data, separate from the descriptive observations. |
| Resource comparison | sections 1, 3.3, 7.3 | Descriptive means of canonical records only. No significance claim; canonical totals omit discarded attempts, and complete failed-attempt usage is unavailable. No operational-saving conclusion. |
| Provenance | sections 6, 7.5, 9, 12.5 | The actual sampler receipt, an immutable decision chronology for deviation 1 and complete failed-attempt usage remain **unverified**. No fresh-run, production, equivalence or operational-saving conclusion follows from this report. |

"""
    head, sep, rest = t.partition('\n## 1. Summary\n')
    assert sep, 'summary heading not found'
    t = head + '\n' + banner + '## 1. Summary\n' + rest
    for banned in ('significantly fewer', 'whatever the method', 'whatever the truth', 'cannot resolve a 0.03 guardrail', 'Resolved secondary facts',
                   'conservative for the finite-roster average and conventional', 'which would need the assumptions of the previous paragraph'):
        assert banned not in t, banned
    OUT.write_text(t)
    MAN.write_text(json.dumps(dict(
        kind='report-only correction (Round 12); no model call; no analysis rerun', source='results/tau2_open/report_final.md',
        source_sha256=sha(SRC), output='results/tau2_open/report_final_v2.md', output_sha256=sha(OUT),
        reviewed_owner_head=REVIEWED_HEAD, root_integration_commit=ROOT_INTEGRATION, replacements=applied,
        observed_array_replay_numbers=r, numbers_source='results/tau2_open/round10_handoff_numbers.json',
        numbers_source_sha256=sha(RD / 'round10_handoff_numbers.json')), indent=2) + '\n')
    print('wrote', OUT.relative_to(REPO), 'and', MAN.relative_to(REPO)); print(json.dumps(r, indent=1))


if __name__ == '__main__':
    build()
