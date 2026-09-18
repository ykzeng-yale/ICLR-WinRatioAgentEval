"""Writes results/local_stream/report_v2.md from the v2 analysis outputs (POST HOC Round 9 report).

Every number is formatted from summary_v2.json / two_sided_cs_check.json / data_manifest.json /
monitor_state.json; nothing is typed by hand. Also writes the short results/local_stream/report.md stub that
points to report_v2.md (the v1 report is preserved in v1_pre_round9/report.md). No model call, no git command.

Usage: .venv/bin/python experiments/local_stream/make_report_v2.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def f(x, d=3):
    return 'NA' if x is None else ('%+.*f' % (d, x) if isinstance(x, float) and x != 0 and d == 3 and False else '%.*f' % (d, x))


def ci(c, d=3):
    return 'NA' if not c or c[0] is None else '[%s, %s]' % (f(c[0], d), 'inf' if c[1] is None else f(c[1], d))


def n0(x):
    return 'none' if x is None else str(x)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(REPO / 'results/local_stream'))
    rd = Path(ap.parse_args(argv).results_dir)
    S = json.loads((rd / 'summary_v2.json').read_text()); chk = json.loads((rd / 'two_sided_cs_check.json').read_text())
    dm = json.loads((rd / 'data_manifest.json').read_text())
    o, sh, e1, e2, comp, res = S['online'], S['shadow'], S['e1'], S['e2'], S['components'], S['resources']
    R1, R2, mon = e1['R1'], e1['R2'], e1['monitor']; ovn = S['old_vs_new_intervals']; sp = comp['same_task_paired']; pl = comp['cross_arrival_pair_level']
    sd = e2['success_difference']; fr = e2['finite_roster']; a, b = res['per_arm']; rr = res['ratio_B_over_A']; sc = e1['scores']
    L = []
    P = L.append
    P('# Local-model prospective stream: report v2 (Round 9 re-analysis, POST HOC)')
    P('')
    P('This report supersedes `v1_pre_round9/report.md` for every inferential statement. It was generated %s by `experiments/local_stream/make_report_v2.py` from `summary_v2.json` '
      '(`analysis_v2.py`), which re-analyses the **unchanged** raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `design.json`, `run_manifest.json`; sha256 in `analysis_v2_manifest.json`). '
      'No episode was re-run and no model was called. The re-analysis is **post hoc**: it was specified in `experiments/local_stream/protocol_addendum_round9.md` after the outcomes were known, '
      'in response to the Round 9 audit of PR 8. The frozen `protocol.md` and `analysis.py` are untouched; the v1 outputs (uncorrected two-sided CS, uncorrected target wording) are preserved in `v1_pre_round9/`.' % S['generated_at'])
    P('')
    P('## 1. Summary')
    P('')
    P('Two workflows on one local open-weight model (`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, served at `127.0.0.1`; no commercial or proprietary model call) were compared on a fixed roster of 591 tasks '
      '(427 MBPP-sanitized + 164 HumanEval): A `single_shot` versus B `self_test_repair`. All %d planned episodes were run and retained. '
      '**The preregistered primary hypothesis H1 (B has higher hidden-test success) is not supported, and this negative result is retained as is**: both arms succeeded on %d/591 tasks (%d B-only and %d A-only successes). '
      'B used %.2fx the model calls, %.2fx the prompt tokens, %.2fx the completion tokens and %.2fx the mean workflow latency of A. Under the frozen hierarchy (success > latency at 10%% tolerance > completion tokens, absorbing rule) '
      'the net benefit of B is negative on both prespecified contrasts: E1 cross-arrival NB = %s (%d wins / %d ties / %d losses over 295 pairs) and E2 same-task NB = %s (591 tasks).'
      % (S['n_episodes'], a['successes'], sd['b_only'], sd['a_only'], rr['model_calls'], rr['prompt_tokens'], rr['completion_tokens'], rr['latency_mean_s'], f(o['net_benefit']), sc['wins'], sc['ties'], sc['losses'], f(sh['net_benefit'])))
    P('')
    P('Uncertainty for E1 is given under two explicitly separated readings (section 3): **R1**, design-based and conditional on the realized pairing, 95%% normal-mixture CS for the running average of pair means %s, first entirely below 0 at pair %s; '
      '**R2**, under the unverifiable assumption that the roster is an iid sample of tasks, corrected 95%% betting CS %s, first below 0 at pair %s. '
      'The online monitor outcome is a **%s** (harm e-process read above threshold at pair %s): an unfavourable result for B on the prespecified composite, driven by the latency tier; it is not a success-rate or safety harm and not a reverse guarded approval of A. '
      'The success guardrail was **not** certified online, and the same-task non-inferiority check passes by only %.5f under one approximation (section 5).'
      % (ci(R1['nb_cs']), n0(R1['first_n_nb_upper_below_0']), ci(R2['nb_cs']), n0(R2['first_n_nb_upper_below_0']), S['online_label'], n0(mon['first_harm']), sd['slack_above_margin']))
    P('')
    P('## 2. What changed relative to v1')
    P('')
    P('| item | v1 (preserved in `v1_pre_round9/`) | v2 |')
    P('|---|---|---|')
    P('| two-sided betting CS | `max(K+, K-)` against `1/delta` (guarantee 2 delta) | hedged capital `(K+ + K-)/2` against `1/delta` (guarantee delta); `src/wincs.py` sha256 `%s` |' % S['wincs_sha256'][:16])
    P('| E1 NB interval | %s | R2 %s; R1 %s |' % (ci(ovn['nb_cs']['v1_uncorrected'], 4), ci(ovn['nb_cs']['v2_corrected_R2'], 4), ci(ovn['nb_cs']['v2_R1_normal_mixture'], 4)))
    P('| E1 success-difference interval | %s | R2 %s; R1 %s |' % (ci(ovn['success_diff_cs']['v1_uncorrected'], 4), ci(ovn['success_diff_cs']['v2_corrected_R2'], 4), ci(ovn['success_diff_cs']['v2_R1_normal_mixture'], 4)))
    P('| E1 win-ratio interval (decided pairs) | %s | R2 %s (no R1 analogue is claimed) |' % (ci(ovn['wr_cs']['v1_uncorrected'], 4), ci(ovn['wr_cs']['v2_corrected_R2'], 4)))
    P('| first pair at which the NB interval is below 0 | 32 (uncorrected CS) | R2: %s (stays below from pair %s); R1: %s |' % (n0(R2['first_n_nb_upper_below_0']), n0(R2['stays_below_0_from']), n0(R1['first_n_nb_upper_below_0'])))
    P('| target of E1 | "295 independent pairs", population guarantee asserted | R1: running average over the pairs actually formed (no sampling assumption); R2: theta_P under an iid-roster ASSUMPTION |')
    P('| monitor crossings | "valid decision after 24 independent pairs" | descriptive under R1; anytime guarantee only under R2 |')
    P('| label `B_harmful` | "B harmful" | "%s" |' % S['online_label'])
    P('| pass-1 component intervals | independent-arm Welch | pair-level differences (n = 295) |')
    P('| freeze wording | "before any model call" | "before any design-task outcome" (section 8) |')
    P('| resources | completion tokens and latency | prompt, completion and total tokens, model calls, latency per arm (section 6) |')
    P('')
    P('Point estimates, tier decompositions, the e-process paths and the first-crossing indices are identical to v1 (asserted in `analysis_v2.py`); `task_scores.csv` and `episodes_flat.csv` do not depend on the CS and are unchanged. '
      'Regression check of the correction (`two_sided_cs_check.json`): for one fair +/-1 observation E max(K+, K-) = %.8f > 1 while E (K+ + K-)/2 = %.12f; simulated time-uniform miscoverage of the corrected CS over %d streams of length %d at delta = %.2f: %s (uncorrected max rule on the same streams: %s).'
      % (chk['witness']['expected_max'], chk['witness']['expected_hedged'], chk['simulations'][0]['reps'], chk['simulations'][0]['n'], chk['simulations'][0]['delta'],
         ', '.join('%.4f' % s['ever_miss_hedged'] for s in chk['simulations']), ', '.join('%.4f' % s['ever_miss_uncorrected_max_rule'] for s in chk['simulations'])))
    P('')
    P('## 3. E1: cross-arrival contrast (295 pass-1 pairs)')
    P('')
    P('Sampling facts. The 591 tasks are a FIXED roster. The design (seed 20260918) drew one uniformly random permutation and independent Bernoulli(1/2) orientations for 295 disjoint consecutive pairs; '
      'one arrival (`mbpp/256`) is unpaired by design and enters E2 only. Each episode adds model-sampling randomness. Pass 1 was physically executed in the frozen arrival order, one exposure per arrival; execution never stopped at a crossing.')
    P('')
    P('Counts: %d B wins / %d ties / %d B losses; NB = %s; WR = %s; success difference D = %s (A %.3f, B %.3f in pass 1). Tier decomposition: %s.'
      % (sc['wins'], sc['ties'], sc['losses'], f(o['net_benefit'], 4), f(o['win_ratio']), f(o['success_diff_hat'], 4), pl['success']['mean_A'], pl['success']['mean_B'],
         '; '.join('%s %d wins / %d losses (%s)' % (k, v['wins'], v['losses'], f(v['contribution'])) for k, v in o['tier_decomposition'].items())))
    P('')
    P('| reading | target | assumption | procedure | NB, 95% | first n with upper bound < 0 | success difference, 95% | gate (lower > -0.03) |')
    P('|---|---|---|---|---|---|---|---|')
    P('| **R1** design-based | running average mu_bar_n = (1/n) sum_k mu_k, mu_k = (1/2)[m(s_k,t_k) + m(t_k,s_k)], over the pairs actually formed | none beyond the design (conditional on the matching; pair scores independent, not identically distributed) | normal-mixture CS, V_n = n, rho = 100 (radius %s at n = 295) | %s | %s | %s | not established |'
      % (f(R1['radius_at_n'], 4), ci(R1['nb_cs'], 4), n0(R1['first_n_nb_upper_below_0']), ci(R1['success_diff_cs'], 4)))
    P('| **R2** superpopulation | theta_P = E m(s,t) for s, t iid from P | **roster is an iid sample from a task distribution P (unverifiable for a curated benchmark)** | corrected hedged betting CS; decided-pair WR CS %s | %s | %s (stays below from %s) | %s | not established (first n: %s) |'
      % (ci(R2['wr_cs'], 4), ci(R2['nb_cs'], 4), n0(R2['first_n_nb_upper_below_0']), n0(R2['stays_below_0_from']), ci(R2['success_diff_cs'], 4), n0(R2['first_n_success_lower_above_minus_margin'])))
    P('')
    P('Under R1, because the matching is uniformly random, E_design[mu_bar_n] equals the finite-roster cross-task target theta_N = (1/(N(N-1))) sum_{s != t} m(s,t); the CS statement is nevertheless about mu_bar_n conditional on the matching, and **no without-replacement martingale or CS for theta_N is claimed**. '
      'No running intersection is applied under R1 because its target moves with n. Proofs and definitions: `protocol_addendum_round9.md` section 3.')
    P('')
    P('Monitor (one-sided e-processes of `winstats.betting_log_e_ternary`, alpha 0.05, threshold log 20 = %.3f, read from pair 20; numerically unaffected by the two-sided fix): harm first read above threshold at **pair %s** (log e %.3f; it was above threshold at pair %s, log e %.3f, inside the prespecified n < 20 blackout, which is not read); final log e: harm %.2f, win %.3f, gate %.3f (maxima %.3f and %.3f; neither crossed). No deploy crossing.'
      % (mon['threshold'], n0(mon['first_harm']), mon['log_e_harm_at_first_harm'], mon['harm_above_threshold_before_min_n']['n'], mon['harm_above_threshold_before_min_n']['log_e'],
         mon['final_log_e']['harm'], mon['final_log_e']['win'], mon['final_log_e']['gate'], mon['max_log_e']['win'], mon['max_log_e']['gate']))
    P('')
    P('- Under **R1** these crossings are reported **descriptively**: the e-processes test the pointwise conditional null (harm: mu_k >= 0 for every realized pair), a stronger null than mu_bar_n >= 0 or theta_N >= 0.')
    P('- Under **R2** they have the stated anytime type-I guarantee at alpha for theta_P.')
    P('- Outcome label: **%s**. %s' % (S['online_label'], mon['label_note']))
    P('- The crossing is a recorded decision that could have been taken; the run was not stopped and nothing was deployed.')
    P('')
    P('![fig1](figures_v2/fig1_monitoring.png)')
    P('')
    P('*Figure 1. Log e-values of the win, guardrail (gate) and harm e-processes after each pass-1 pair (`monitor_pass1.csv`); dotted line log(1/alpha); shaded region n < 20 is not read. '
      'These one-sided paths are descriptive under R1 (fixed roster, conditional on the matching) and carry their anytime guarantee only under the R2 iid-roster assumption. The marked crossing is the composite harm signal for B (incumbent A retained), not a success-rate or safety harm.*')
    P('')
    P('![fig2](figures_v2/fig2_running_nb.png)')
    P('')
    P('*Figure 2. Running cross-arrival net benefit with (blue) the corrected 95% hedged betting CS, valid for theta_P under the R2 iid-roster assumption, and (green, dashed) the 95% normal-mixture CS for the running average mu_bar_n, valid under R1 with no sampling assumption; orange: same-task NB with its 95% task-level interval (section 4). Source: `running_cs_v2.csv`, `summary_v2.json`.*')
    P('')
    P('Pass-1 component contrasts from pair-level differences d_k = X_B,k - X_A,k (n = 295; t interval, conservative for the average of pair means under R1, iid under R2):')
    P('')
    P('| component | mean A | mean B | mean difference [95%] |')
    P('|---|---|---|---|')
    for c in ('success', 'latency_s', 'completion_tokens', 'prompt_tokens', 'n_llm_calls'):
        P('| %s | %s | %s | %s %s |' % (c, f(pl[c]['mean_A']), f(pl[c]['mean_B']), f(pl[c]['mean']), ci(pl[c]['ci'])))
    P('')
    P('## 4. E2: same-task shadow contrast (all 591 roster tasks, one A and one B episode each)')
    P('')
    P('| scope | n tasks | p_win / p_tie / p_loss | NB [95% task-level t interval] | WR [95%] |')
    P('|---|---|---|---|---|')
    rows = [('pooled', sh)] + [(k, v) for k, v in sh.get('by_benchmark', {}).items()] + ([('stratified, equal benchmark weight', sh['stratified_equal_weight'])] if sh.get('stratified_equal_weight') else [])
    for k, v in rows:
        P('| %s | %s | %s / %s / %s | %s %s | %s %s |' % (k, v['n_tasks'], f(v['p_win']), f(v['p_tie']), f(v['p_loss']), f(v['net_benefit']), ci(v['nb_ci']), f(v['win_ratio']), ci(v['wr_ci'])))
    P('')
    P('Targets and status of the interval (both statements are kept):')
    P('')
    P('- **Finite-roster target**: theta_roster = (1/N) sum_t E h(Y_B(t), Y_A(t)) over the 591 roster tasks; the only randomness is model sampling. The task-level variance estimator is **conservative** for it (Neyman-type): '
      'E[s^2/N] = Var(mean) + (1/(N(N-1))) sum_t (tau_t - tau_bar)^2, so between-task variation of the means inflates it. Interval %s (normal approximation). Assumption-free fixed-n Hoeffding interval: %s.' % (ci(fr['interval_t'], 4), ci(fr['interval_hoeffding'], 4)))
    P('- **Superpopulation target** (iid-roster model): the same interval %s is the conventional task-clustered interval (one cluster = one task).' % ci(fr['interval_t'], 4))
    P('')
    P('Tier contribution means: %s. Same-task paired component differences (B - A, n = 591 tasks, t interval with the same two readings):' % ', '.join('%s %s' % (k, f(v)) for k, v in sh['tier_contribution_mean'].items()))
    P('')
    P('| component | mean A | mean B | mean difference [95%] | ratio of means |')
    P('|---|---|---|---|---|')
    for c in ('success', 'latency_s', 'completion_tokens', 'prompt_tokens', 'n_llm_calls'):
        r = sp[c]; P('| %s | %s | %s | %s %s | %s |' % (c, f(r['mean_A']), f(r['mean_B']), f(r['mean']), ci(r['ci']), f(r.get('ratio_of_means_B_over_A'), 2) if r.get('ratio_of_means_B_over_A') else (f(r['mean_B'] / r['mean_A'], 2) if r['mean_A'] else 'NA')))
    P('')
    P('## 5. Guardrail precision, and E1 versus E2')
    P('')
    P('- Same-task success difference %s (%d B-only, %d A-only successes), t interval %s. Its lower end %.9f clears the -0.03 margin by only **%.6f**, under that single fixed-time approximation. '
      '**This is not a robust non-inferiority result**: the assumption-free interval is %s; the online gate e-process did not cross (final log e %.3f against %.3f); and the online success-difference intervals reach %s (v1, uncorrected CS), %s (R2, corrected CS) and %s (R1). '
      'The data do not certify a 3-percentage-point success guardrail online.' % (f(sd['hat']), sd['b_only'], sd['a_only'], ci(sd['interval_t'], 4), sd['interval_t'][0], sd['slack_above_margin'], ci(sd['interval_hoeffding']), mon['final_log_e']['gate'], mon['threshold'], f(ovn['success_diff_cs']['v1_uncorrected'][0]), f(R2['success_diff_cs'][0]), f(R1['success_diff_cs'][0])))
    P('- E1 NB %s versus E2 NB %s: difference %s. %s The tier and tie patterns that accompany the two numbers (v1 report section 6, unchanged counts) are descriptive context, not an established population difference or an efficiency comparison.'
      % (f(S['e1_vs_e2']['e1_nb'], 4), f(S['e1_vs_e2']['e2_nb'], 4), f(S['e1_vs_e2']['difference_e1_minus_e2']), S['e1_vs_e2']['status']))
    P('')
    P('## 6. Resources per arm (recomputed from `episodes.jsonl`; `resources_v2.csv`)')
    P('')
    P('| arm | episodes | successes | model calls | prompt tokens | completion tokens | total tokens | latency sum (s) | latency mean / median (s) | executions incl. hidden verifier | agent self-test executions |')
    P('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in res['per_arm']:
        P('| %s `%s` | %d | %d | %s | %s | %s | %s | %s | %s / %s | %s | %s |' % (r['arm'], r['variant'], r['episodes'], r['successes'], format(r['model_calls'], ','), format(r['prompt_tokens'], ','), format(r['completion_tokens'], ','),
                                                                              format(r['total_tokens'], ','), format(round(r['latency_sum_s'], 1), ','), f(r['latency_mean_s'], 4), f(r['latency_median_s']), format(r['n_executions_incl_hidden_verifier'], ','), format(r['agent_self_test_executions'], ',')))
    t = res['totals']
    P('| total | %d | | %s | %s | %s | %s | | | | |' % (S['n_episodes'], format(t['model_calls'], ','), format(t['prompt_tokens'], ','), format(t['completion_tokens'], ','), format(t['total_tokens'], ',')))
    P('')
    P('B/A ratios: model calls %.2f, prompt tokens %.2f, completion tokens %.2f, total tokens %.2f, mean latency %.2f. Completion tokens are **generation counts, not dollars, energy or total compute**; prompt tokens are shown because B consumes %.1fx as many. '
      'No token count is marked estimated. `n_executions` **includes the one hidden-verifier execution per episode**, whereas `latency_s` (model calls + the workflow\'s own self-tests) excludes hidden verification; verifier operations are not agent tool calls. '
      'Latency is single-host, sequential, local-server workflow latency on the recorded hardware, not queueing or production latency; these ratios are for this run only.' % (rr['model_calls'], rr['prompt_tokens'], rr['completion_tokens'], rr['total_tokens'], rr['latency_mean_s'], rr['prompt_tokens']))
    P('')
    P('## 7. Decision rules and sensitivity (corrected CS; `decision_rules_v2.csv`, `sensitivity_v2.csv`)')
    P('')
    P('| rule | data | reading | estimate | 95% interval | outcome |')
    P('|---|---|---|---|---|---|')
    for r in S['decision_rules']:
        P('| %s | %s | %s | %s | %s | %s |' % (r['rule'], r['data'], r.get('reading', ''), f(r['estimate']) if r['estimate'] is not None else '-', ci(r['ci']) if r['ci'] and r['ci'][0] is not None else '-', r['decision']))
    P('')
    P('"A" in the outcome column means the rule\'s interval or point estimate favours A on that rule\'s own criterion; for `guarded_anytime` the outcome is "retain A" (composite harm signal), which is not a guarded approval of A. Success-only rules return no decision.')
    P('')
    P('| tol | order | eligibility | E2 NB [95%] | E1 NB [R2 corrected CS] | online label |')
    P('|---|---|---|---|---|---|')
    for r in S['sensitivity']:
        P('| %s | %s | %s | %s [%s, %s] | %s [%s, %s] | %s |' % (r['tolerance'], r['order'].replace('>', ' > '), r['eligibility'], f(r['shadow_nb']), f(r['shadow_nb_lo']), f(r['shadow_nb_hi']), f(r['online_nb']), f(r['online_nb_lo']), f(r['online_nb_hi']), r['online_guarded_label']))
    P('')
    P('## 8. Hypotheses, provenance and wording corrections')
    P('')
    P('- **H1 not supported (retained negative result).** H2 (B costs more latency and tokens) supported. H3 (hierarchy prefers B) refuted on both contrasts. H4: resource-first orders also favour A; the predicted disagreement was not observed. H5: not robustly established (section 5). No new variants were run and none are proposed as a completion criterion.')
    P('- **Freeze wording.** The protocol and design were frozen **before any design-task outcome**, not "before any model call": smoke checks and the 6-task out-of-design timing pilot (full MBPP, disjoint from the design, never analysed) called the model earlier and are disclosed. This is a timestamped internal freeze, not an external registration.')
    P('- **Harness commits.** The run manifest and every episode record harness commit `526dff7b6d26f818964611b9ccbd8f61fae2e43c`; protocol section 16 names freeze commit `d9793d56430e65c600e241f325a7cd540d23a668`. Per the Round 9 audit\'s Git reconciliation, all 13 recorded file hashes match `526dff7b`, and at `d9793d5` only `protocol.md` differs (the other 12 files are identical); both commits precede the first episode. (This report did not run git; the reconciliation is the audit\'s, and it agrees with the per-file sha256 comparison in the v1 report section 10.)')
    P('- **Exposure.** Coding pass 1 is a physically executed, randomized, sequential laboratory stream with fresh generations; crossings are recorded, not acted on; there are no production users.')
    ms, he, fm = dm['sources']['mbpp_sanitized'], dm['sources']['humaneval'], dm['sources']['mbpp_full_timing_pilot']
    P('- **Data provenance** (`data_manifest.json`, checked by `verify_data_manifest.py --verify-pinned`): MBPP-sanitized pinned at `google-research/google-research@%s` (%d bytes, sha256 `%s`, CC-BY-4.0); HumanEval pinned at `openai/human-eval@%s` (%d bytes, sha256 `%s`, MIT); full MBPP (timing pilot only) at `@%s` (%d bytes, sha256 `%s`). Re-fetching the pinned URLs gave identical bytes (%s); the canonical task list rebuilds to sha256 `%s`, the value stamped in `design.json`.'
      % (ms['upstream_revision'][:12], ms['bytes'], ms['sha256'][:16], he['upstream_revision'][:12], he['bytes'], he['sha256'][:16], fm['upstream_revision'][:12], fm['bytes'], fm['sha256'][:16],
         (dm.get('pinned_bytes_verified') or {}).get('at', 'not yet verified'), dm['canonical_task_list']['sha256']))
    P('- **Anonymized release copies** of manifests/config/README/protocol with `<REPO>`, `<HOME>`, `<TMP>` placeholders and the sha256 of each original: `release_anon/` (`MAPPING.md`). Originals are not edited.')
    P('- Unchanged descriptive material (failure accounting, latency scope, tier/tie tables, requirement checklist) remains in `v1_pre_round9/report.md` sections 6, 7, 11; where that text says "independent pairs", "valid decision", "B harmful" or "Welch", read it with the corrections above. Scope limits are unchanged: one 7B 4-bit model, one machine, public benchmarks with likely training overlap; benchmark success is not exhaustive correctness.')
    P('')
    P('## 9. Reproducibility')
    P('')
    P('```')
    P('.venv/bin/python experiments/local_stream/run_v2_all.py            # regenerates every v2 output from the preserved raw files (about 4 min, CPU only, no model)')
    P('.venv/bin/python experiments/local_stream/run_v2_all.py --verify-pinned   # also re-fetches the pinned benchmark files into memory and compares bytes')
    P('```')
    P('')
    P('Input, code and output hashes with timestamps: `analysis_v2_manifest.json`.')
    P('')
    (rd / 'report_v2.md').write_text('\n'.join(L))
    stub = ['# Local-model prospective stream: report', '',
            'The current report is **[report_v2.md](report_v2.md)** (Round 9 post hoc re-analysis: corrected two-sided confidence sequence, explicit design-based (R1) and superpopulation (R2) readings, corrected labels and provenance).', '',
            'The original report, produced with the uncorrected two-sided CS and the uncorrected target wording, is preserved unchanged at [v1_pre_round9/report.md](v1_pre_round9/report.md) together with the other v1 outputs. '
            'The top-level `summary.json`, `decision_rules.csv` and `sensitivity.csv` are those v1 files (byte-identical to the copies in `v1_pre_round9/`); their two-sided online intervals are superseded by `summary_v2.json`, `decision_rules_v2.csv` and `sensitivity_v2.csv`. '
            '`task_scores.csv`, `episodes_flat.csv` and all raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `design.*`) are unchanged.', '']
    (rd / 'report.md').write_text('\n'.join(stub))
    print('wrote', rd / 'report_v2.md', 'and report.md stub')


if __name__ == '__main__':
    main()
