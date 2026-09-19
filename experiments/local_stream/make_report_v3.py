"""Writes results/local_stream/report_v3.md (POST HOC Round 10 report) and the report.md stub pointing to it.

report_v3.md = the content of report_v2.md (regenerated in memory by the unchanged make_report_v2.py from the current
summary_v2.json) with: a "Round 10 changes" list at the top; the R1/R2 tables, captions and paragraphs reworded
(running-conditional-mean target under a stated filtration; R2 = unconditional model-based inference); the E2 section
rewritten (task-level intervals MODEL-BASED, orientation-pair cluster analysis, counterexample, pass/period table);
the guardrail paragraph updated (margin not certified by any interval). Every number is formatted from
summary_v2.json / summary_v3.json; nothing is typed by hand. No model call, no git command.

Usage: .venv/bin/python experiments/local_stream/make_report_v3.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, contextlib, io, json, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import make_report_v2 as mr2  # noqa: E402

f, ci = mr2.f, mr2.ci
BANNED = ('assumption-free', 'assumption free', 'automatically conservative', 'no sampling assumption', 'none beyond the design')


def v2_text(rd: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        for n in ('summary_v2.json', 'two_sided_cs_check.json', 'data_manifest.json'):
            shutil.copy(rd / n, Path(td) / n)
        with contextlib.redirect_stdout(io.StringIO()):
            mr2.main(['--results-dir', td])
        return (Path(td) / 'report_v2.md').read_text()


def rep(text, old, new, count=None):
    k = text.count(old)
    assert k >= 1 and (count is None or k == count), ('expected text not found / wrong count', k, old[:90])
    return text.replace(old, new)


def replace_line(lines, prefix, new):
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix, idx)
    lines[idx[0]:idx[0] + 1] = new if isinstance(new, list) else [new]


def section_bounds(lines, heading_prefix):
    i = [k for k, l in enumerate(lines) if l.startswith(heading_prefix)]
    assert len(i) == 1, heading_prefix
    j = next((k for k in range(i[0] + 1, len(lines)) if lines[k].startswith('## ')), len(lines))
    return i[0], j


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(REPO / 'results/local_stream'))
    rd = Path(ap.parse_args(argv).results_dir)
    S2 = json.loads((rd / 'summary_v2.json').read_text()); S3 = json.loads((rd / 'summary_v3.json').read_text())
    cmp_path = rd / 'v2_vs_v3_numeric_check.json'; CMP = json.loads(cmp_path.read_text()) if cmp_path.exists() else None
    R1, R2, mon = S3['e1']['R1'], S3['e1']['R2'], S3['e1']['monitor']; e2 = S3['e2']; nb = e2['net_benefit']; sd = e2['success_difference']
    nbc, sdc = nb['orientation_pair_cluster'], sd['orientation_pair_cluster']; sp = S2['components']['same_task_paired']; sh = S2['shadow']; pe = S3['pass_effects']['rows']
    t = v2_text(rd)

    # ---- global wording
    t = rep(t, 'before any design-task outcome', 'before design-task outcomes')
    t = rep(t, '# Local-model prospective stream: report v2 (Round 9 re-analysis, POST HOC)', '# Local-model prospective stream: report v3 (Round 9 + Round 10 re-analysis, POST HOC)', 1)
    lines = t.split('\n')
    # ---- header paragraph + Round 10 changes
    i0 = next(k for k, l in enumerate(lines) if l.startswith('This report supersedes'))
    changed = 'not recorded (run `run_v3_all.py`)' if CMP is None else (
        'no v2 number changed (largest absolute difference over %d numeric leaves and %d CSV cells: %.3g)' % (CMP['summary_v2_json']['n_numeric_leaves'], CMP['n_csv_numeric_cells'], CMP['max_abs_diff_overall'])
        if CMP['max_abs_diff_overall'] <= 1e-8 else 'largest absolute change of a v2 number: %.3g (details in `v2_vs_v3_numeric_check.json`)' % CMP['max_abs_diff_overall'])
    head = [
        'This report supersedes `report_v2.md` (preserved in `v2_pre_round10/`) and `v1_pre_round9/report.md` for every inferential statement. It was generated %s by `experiments/local_stream/make_report_v3.py` from `summary_v2.json` (`analysis_v2.py`, E1 numbers) and `summary_v3.json` (`analysis_v3.py`, E2 cluster analysis, pass table, Round 10 labels), which re-analyse the **unchanged** raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `design.json`, `run_manifest.json`; sha256 in `analysis_v3_manifest.json`). No episode was re-run, no model was called and no generated program was executed. Everything here is **post hoc**: specified in `experiments/local_stream/protocol_addendum_round9.md` and `protocol_addendum_round10.md` after the outcomes were known, in response to the Round 9 and Round 10 audits of PR 8. The frozen `protocol.md` and `analysis.py` are untouched.' % S3['generated_at'],
        '',
        '**Round 10 changes** (response to the Round 10 audit; raw data and every point estimate unchanged):',
        '',
        '1. **E2 uncertainty relabelled.** The task-level t interval and the task-level Hoeffding interval are **model-based**: they need independent task scores with stable task-specific episode laws and no relevant pass/period effects (the t interval also a Lindeberg / variance-growth condition). They are not consequences of the two-pass AB/BA design, in which the two tasks of a design pair share one orientation coin. The v2 claims that these intervals were free of assumptions, or conservative by construction, are withdrawn (section 4, with the audit\'s two-task counterexample).',
        '2. **Orientation-pair cluster analysis added** (G = 296 clusters: 295 design pairs + the unpaired task): cluster-robust SE %s versus task-level SE %s for the same-task NB (ratio %s); exact final-time cluster Hoeffding radius %s (task-level, model-based: %s). Independence across clusters is still an assumption.' % (f(nbc['cluster_robust_se'], 5), f(nb['task_level_se'], 5), f(nb['se_ratio_cluster_over_task'], 4), f(nbc['hoeffding_cluster_radius'], 5), f(nb['task_level']['hoeffding_radius'], 5)),
        '3. **The -0.03 same-task success margin is not certified by any reported interval** (section 5).',
        '4. **Descriptive pass/period table added** (section 4; no inference).',
        '5. **R1 wording**: the target is the running conditional mean of the pair scores given a stated filtration; the pair-mean formula and the link to a roster-level target hold only under an additional stable episode-law model. Separate 95% intervals for NB and the success difference are not a joint 95% region; rho was fixed after outcomes were seen. **R2 wording**: unconditional model-based inference over hypothetical iid rosters, with a filtration that does not contain the whole realized roster; not a guarantee conditional on the curated benchmark. Fixed-stake e-process crossings stay descriptive under R1.',
        '6. **Endpoint arithmetic of `src/wincs.py` repaired** (`0 * log 0 = 0`: a stake whose factor is 0 kills the capital only when its count is positive; new test `test_endpoint_normalization_round10`). Effect on the v2 numbers: %s.' % changed,
        '7. **Anonymized data manifest** now committed at a non-ignored path (`release_anon/local_data_manifest.anon.json`); anonymized-copy regeneration is location-dependent (section 8).',
    ]
    lines[i0:i0 + 1] = head
    t = '\n'.join(lines)

    # ---- section 1
    t = rep(t, 'design-based and conditional on the realized pairing, 95% normal-mixture CS for the running average of pair means', '95% normal-mixture CS for the **running conditional mean** of the pair scores given the stated filtration (section 3)', 1)
    t = rep(t, 'under the unverifiable assumption that the roster is an iid sample of tasks,', 'model-based (unconditional inference over hypothetical iid rosters with independent stable episode laws; unverifiable for a curated benchmark and not conditional on it),', 1)
    t = rep(t, 'under one approximation (section 5)', 'under one model-based approximation and is **not certified by any reported interval** (section 5)', 1)
    t = rep(t, 'and E2 same-task NB = %s (591 tasks).' % f(sh['net_benefit']),
            'and E2 same-task NB = %s (591 tasks; model-based task-level t interval %s, orientation-pair cluster-robust interval %s, exact cluster Hoeffding interval %s; section 4).' % (
                f(sh['net_benefit']), ci(nb['task_level']['interval_t']), ci(nbc['interval_cluster_t']), ci(nbc['interval_cluster_hoeffding'])), 1)
    # ---- section 2 table
    t = rep(t, '| item | v1 (preserved in `v1_pre_round9/`) | v2 |', '| item | v1 (preserved in `v1_pre_round9/`) | v2 numbers (Round 9), Round 10 wording |', 1)
    t = rep(t, 'R1: running average over the pairs actually formed (no sampling assumption); R2: theta_P under an iid-roster ASSUMPTION', 'R1: running conditional mean of the pair scores (stated filtration); R2: theta_P under the iid-roster MODEL (unconditional)', 1)
    # ---- section 3
    lines = t.split('\n')
    replace_line(lines, '| reading | target | assumption |', '| reading | target | conditions | procedure | NB, 95% | first n with upper bound < 0 | success difference, 95% | gate (lower > -0.03) |')
    replace_line(lines, '| **R1** design-based', '| **R1** running conditional mean | (1/n) sum_{k<=n} mu_k with mu_k = E[Z_k \\| F_(k-1)], F_k = sigma(design information independent of future outcomes, revealed pair data up to k) | bounded scores and the stated filtration; the target may move with n and with history (thermal state, order, caching). The reading mu_k = [m(s_k,t_k)+m(t_k,s_k)]/2 needs an ADDITIONAL orientation-independent, history-independent stable episode-law model and is not assumed | normal-mixture CS, V_n = n, rho = 100 fixed post hoc (radius %s at n = %d); no running intersection | %s | %s | %s | not established |' % (
        f(R1['radius_at_n'], 4), R1['n'], ci(R1['nb_cs'], 4), mr2.n0(R1['first_n_nb_upper_below_0']), ci(R1['success_diff_cs'], 4)))
    replace_line(lines, '| **R2** superpopulation', '| **R2** iid-roster model | theta_P = E m(s,t) for s, t iid from P | **MODEL: roster = iid sample from a task distribution P, independent stable episode laws, F = past revealed pair data + design information independent of future task values (not the whole realized roster). Unconditional inference over hypothetical rosters; NOT a guarantee conditional on the curated benchmark** | corrected hedged betting CS; decided-pair WR CS %s | %s | %s (stays below from %s) | %s | not established (first n: %s) |' % (
        ci(R2['wr_cs'], 4), ci(R2['nb_cs'], 4), mr2.n0(R2['first_n_nb_upper_below_0']), mr2.n0(R2['stays_below_0_from']), ci(R2['success_diff_cs'], 4), mr2.n0(R2['first_n_success_lower_above_minus_margin'])))
    replace_line(lines, 'Under R1, because the matching is uniformly random,',
                 'Caption for the table. The R1 interval is a statement about the **running conditional mean** n^-1 sum mu_k, mu_k = E[Z_k | F_(k-1)], for the filtration F_k = sigma(design information independent of future outcomes, revealed pair data up to k); Z_k - mu_k is a martingale difference with conditional range 2, which is all the normal-mixture boundary uses. No running intersection is applied because this target can move with n. The interpretation mu_k = [m(s_k,t_k) + m(t_k,s_k)]/2, and with it E_design[mu_bar] = theta_N, holds **only under an additional orientation-independent, history-independent stable episode-law model**; thermal state, execution order and caching can affect latency, so that model is not assumed and **no statement about theta_N (and no without-replacement martingale or CS for it) is claimed**. The two separate 95% intervals (NB, success difference) are **not a joint 95% region**. rho = 100 is the library default but was fixed after the outcomes of this experiment had been seen (post hoc); these are post hoc analyses of a prespecified observed stream, not a prospectively chosen decision rule. The R2 row is unconditional model-based inference over hypothetical iid rosters, not a guarantee conditional on the curated benchmark. Definitions: `protocol_addendum_round10.md` (which supersedes the conflicting sentences of the Round 9 addendum).')
    replace_line(lines, '- Under **R1** these crossings are reported', '- Under **R1** these crossings are reported **descriptively**: the fixed-stake e-processes test the pointwise conditional null (harm: mu_k >= 0 for every k), a stronger null than a non-negative running conditional mean or theta_N >= 0. No guarantee about the running conditional mean is claimed from a crossing (no new theorem is imported).')
    replace_line(lines, '- Under **R2** they have', '- Under the **R2 model** (with the coarse filtration stated above) they have the anytime type-I guarantee at alpha for theta_P; this is model-based, not conditional on the curated roster.')
    replace_line(lines, '*Figure 1.', '*Figure 1. Log e-values of the win, guardrail (gate) and harm e-processes after each pass-1 pair (`monitor_pass1.csv`); dotted line log(1/alpha); shaded region n < 20 is not read. These one-sided paths are descriptive under R1 and carry their anytime guarantee only under the R2 iid-roster model. The marked crossing is the composite harm signal for B (incumbent A retained), not a success-rate or safety harm. (Figure files are those of Round 9; the raw paths are unchanged.)*')
    replace_line(lines, '*Figure 2.', '*Figure 2. Running cross-arrival net benefit with (blue) the corrected 95% hedged betting CS, valid for theta_P under the R2 iid-roster model, and (green, dashed) the 95% normal-mixture CS for the **running conditional mean** of the pair scores (R1; the legend text "design-based" in the Round 9 figure file is to be read with this wording); orange: same-task NB with its 95% task-level t interval, which is MODEL-BASED (section 4). Source: `running_cs_v2.csv`, `summary_v2.json`.*')
    replace_line(lines, 'Pass-1 component contrasts from pair-level differences', 'Pass-1 component contrasts from pair-level differences d_k = X_B,k - X_A,k (n = 295). The t intervals are **approximate and model-based**: they need (conditionally) independent pair differences, finite moments and a CLT regularity condition; latency and token differences are not bounded scores, and history dependence (thermal state, caching) is not excluded by the design.')
    t = '\n'.join(lines)
    t = rep(t, 'Sampling facts. The 591 tasks are a FIXED roster.', 'Sampling facts. The 591 tasks are a FIXED roster (R2 replaces this by a model).', 1)

    # ---- section 4 rewritten (the benchmark table of v2 is kept, relabelled)
    lines = t.split('\n'); a, b = section_bounds(lines, '## 4. E2')
    sec = lines[a:b]
    tab = [l for l in sec if l.startswith('|')]; k_comp = next(i for i, l in enumerate(tab) if l.startswith('| component'))
    bench_tab, comp_tab = tab[:k_comp], tab[k_comp:]
    bench_tab[0] = bench_tab[0].replace('NB [95% task-level t interval]', 'NB [95% task-level t interval, MODEL-BASED]').replace('WR [95%]', 'WR [95%, model-based]')
    tier_line = next(l for l in sec if l.startswith('Tier contribution means'))
    tier_line = tier_line.split(' Same-task paired component differences')[0]
    pr = {r['arm']: r for r in pe}
    new = ['## 4. E2: same-task shadow contrast (all 591 roster tasks, one A and one B episode each)', '']
    new += bench_tab + ['']
    new += [
        '**Status of the task-level intervals (Round 10).** The task-level t interval and the task-level Hoeffding interval are **MODEL-BASED**. They are valid under *independent task scores with stable task-specific episode laws and no relevant pass/period effects*; the t interval additionally needs a Lindeberg / variance-growth regularity condition (boundedness alone does not give a CLT: for independent S_t ~ Bernoulli(1/N) all 591 scores are 0 with probability %s and the zero-width t interval then misses the mean) and is approximate. Under that model the identity E[s^2/N] = Var(mean) + (1/(N(N-1))) sum_t (tau_t - tau_bar)^2 holds and the Hoeffding radius sqrt(2 log(2/alpha)/N) = %s is exact at the final time. **Neither is a property of the actual two-pass design**: the pass in which each workflow sees a task is assigned by an orientation coin that is SHARED by the two tasks of a design pair, and all episodes share one machine. With dependent scores E[s^2/N] acquires the extra term -2 sum_{i<j} Cov(S_i, S_j) / (N(N-1)).' % (f((1 - 1 / 591) ** 591, 6), f(nb['task_level']['hoeffding_radius'], 5)),
        '',
        '**Counterexample (Round 10 audit, finding 1).** ' + e2['counterexample'],
        '',
        '**Orientation-pair cluster analysis.** Clusters: the 295 design pairs of `design.json` (two tasks that shared one AB/BA coin and complementary pass positions) plus the singleton unpaired task `mbpp/256`; G = 296. Target: the **assignment-averaged same-task preference over the roster**, (1/591) sum_t E[S_t], the expectation taken over the orientation coins and episode randomness. Estimator: total same-task score / 591. (a) Cluster-robust variance by linearization with cluster totals, e_g = T_g - n_g NB_hat, var = G/(G-1) sum e_g^2 / 591^2, t reference on G - 1 = %d df, **approximate**. (b) Exact range-based final-time Hoeffding bound under independent clusters, radius sqrt(2 (4*295 + 1) log(2/alpha)) / 591 = %s. **Independent clusters is still an assumption**: arbitrary dependence inside a design pair is allowed, but dependence across clusters through shared machine state (thermal, cache, server history) is not excluded by the design. Per-cluster data: `e2_cluster_v3.csv`.' % (nbc['t_df'], f(nbc['hoeffding_cluster_radius'], 5)),
        '',
        '| quantity | estimate | task-level SE | task-level t 95% (model-based, approximate) | task-level Hoeffding 95% (model-based) | cluster-robust SE (G = 296) | cluster t 95% (approximate; independent clusters) | cluster Hoeffding 95% (exact; independent clusters) |',
        '|---|---|---|---|---|---|---|---|']
    for label, q, qc in (('same-task NB', nb, nbc), ('same-task success difference (B - A)', sd, sdc)):
        new.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (label, f(q['estimate'], 4), f(q['task_level_se'], 5), ci(q['task_level']['interval_t'], 4), ci(q['task_level']['interval_hoeffding'], 4),
                                                              f(qc['cluster_robust_se'], 5), ci(qc['interval_cluster_t'], 4), ci(qc['interval_cluster_hoeffding'], 4)))
    wp = nb['within_pair_descriptive']; bo = e2['by_exposure_order_descriptive']
    new += ['',
            'The cluster-robust SE is %s times the task-level SE for NB and %s times for the success difference; the observed within-pair correlation of the two task scores is %s (descriptive). In this sample the known orientation-pair dependence is therefore numerically immaterial for the t-type intervals, but that is an empirical observation, not a guarantee; the exact bound that does not rely on it is the cluster Hoeffding interval, which is wider (%s versus %s). Mean same-task score by exposure order (descriptive): A first then B %s (%d tasks), B first then A %s (%d tasks).' % (
                f(nb['se_ratio_cluster_over_task'], 4), f(sd['se_ratio_cluster_over_task'], 4), f(wp['pearson_corr_of_the_two_task_scores'], 4), f(nbc['hoeffding_cluster_radius'], 5), f(nb['task_level']['hoeffding_radius'], 5),
                f(bo['A_then_B']['mean_score']), bo['A_then_B']['n_tasks'], f(bo['B_then_A']['mean_score']), bo['B_then_A']['n_tasks']),
            '',
            'Under the iid-roster model the task-level t interval is also the conventional task-clustered interval for theta_task,P = E_{t~P} tau_t; that reading is model-based in the same sense as R2.',
            '',
            '**Pass/period table (DESCRIPTIVE; no inference claimed; `pass_effects_v3.csv`).** For a given variant the pass-1 and pass-2 episodes are on different tasks (a random split of the roster), so a difference mixes task composition with any period effect.',
            '',
            '| variant | episodes pass 1 / pass 2 | success rate pass 1 | pass 2 | diff (2 - 1) | mean latency (s) pass 1 | pass 2 | diff | mean completion tokens pass 1 | pass 2 | diff |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in pe:
        new.append('| %s `%s` | %d / %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (r['arm'], r['variant'], r['n_pass1'], r['n_pass2'], f(r['success_rate_pass1'], 4), f(r['success_rate_pass2'], 4), f(r['success_rate_diff_pass2_minus_pass1'], 4),
                                                                                  f(r['mean_latency_s_pass1']), f(r['mean_latency_s_pass2']), f(r['mean_latency_s_diff_pass2_minus_pass1']),
                                                                                  f(r['mean_completion_tokens_pass1'], 1), f(r['mean_completion_tokens_pass2'], 1), f(r['mean_completion_tokens_diff_pass2_minus_pass1'], 1)))
    new += ['',
            'Reading aid (descriptive): the task set seen by A in pass 1 is the set seen by B in pass 2 (success %s for A, %s for B), and the set seen by B in pass 1 is the set seen by A in pass 2 (success %s for B, %s for A); the success-rate differences between passes within a variant therefore largely track which half of the roster was exposed, and period effects on latency are not separately identified.' % (
                f(pr['A']['success_rate_pass1']), f(pr['B']['success_rate_pass2']), f(pr['B']['success_rate_pass1']), f(pr['A']['success_rate_pass2'])),
            '',
            tier_line + ' Same-task paired component differences (B - A, n = 591 tasks; task-level t intervals, **model-based and approximate** as above; latency and token differences additionally need finite-moment CLT conditions):',
            ''] + comp_tab + ['']
    lines[a:b] = new
    # ---- section 5 rewritten
    a, b = section_bounds(lines, '## 5. Guardrail')
    ev = S2['e1_vs_e2']; le = sd['lower_ends']
    lines[a:b] = ['## 5. Guardrail precision, and E1 versus E2', '',
                  '- Same-task success difference %s (%d B-only, %d A-only successes). Lower ends of the four reported 95%% intervals: task-level t %s (model-based, approximate; clears the -0.03 margin by only **%s**), orientation-pair cluster-robust t %s (approximate, independent clusters; slack %s), task-level Hoeffding %s (model-based), cluster Hoeffding %s (exact under independent clusters). **The -0.03 margin is NOT certified by any of these intervals**: the two t-type intervals clear it by less than 0.001 and only under assumptions that the design does not guarantee plus a normal approximation; both exact bounds reach far below it. The online gate e-process did not cross (final log e %s against %s), and the online success-difference intervals reach %s (R2 model) and %s (R1). **This is not a non-inferiority result**; the data do not certify a 3-percentage-point success guardrail, online or same-task.' % (
                      f(sd['estimate']), sd['b_only'], sd['a_only'], f(le['task_t'], 6), f(sd['lower_end_minus_margin']['task_t'], 6), f(le['cluster_t'], 6), f(sd['lower_end_minus_margin']['cluster_t'], 6),
                      f(le['task_hoeffding'], 4), f(le['cluster_hoeffding'], 4), f(mon['final_log_e']['gate']), f(mon['threshold']), f(R2['success_diff_cs'][0]), f(R1['success_diff_cs'][0])),
                  '- E1 NB %s versus E2 NB %s: difference %s. %s The tier and tie patterns that accompany the two numbers (v1 report section 6, unchanged counts) are descriptive context, not an established population difference, a causal mechanism or an efficiency comparison.' % (
                      f(ev['e1_nb'], 4), f(ev['e2_nb'], 4), f(ev['difference_e1_minus_e2']), ev['status']),
                  '']
    # ---- section 7: decision table from decision_rules v3
    a, b = section_bounds(lines, '## 7. Decision rules')
    sec = lines[a:b]; k0 = next(i for i, l in enumerate(sec) if l.startswith('| rule | data | reading')); k1 = next(i for i in range(k0, len(sec)) if not sec[i].startswith('|'))
    rows = ['| rule | data | reading / status | estimate | 95% interval | outcome |', '|---|---|---|---|---|---|']
    for r in S3['decision_rules']:
        rows.append('| %s | %s | %s | %s | %s | %s |' % (r['rule'], r['data'], r['reading'], '-' if r.get('estimate') is None else f(r['estimate']), ci(r['ci']) if r.get('ci') and r['ci'][0] is not None else '-', r['decision']))
    sec[k0:k1] = rows
    sec[0] = '## 7. Decision rules and sensitivity (corrected CS; `decision_rules_v3.csv`, `sensitivity_v2.csv`)'
    lines[a:b] = sec
    t = '\n'.join(lines)
    t = rep(t, '| tol | order | eligibility | E2 NB [95%] |', '| tol | order | eligibility | E2 NB [95% task-level t, model-based] |', 1)
    t = rep(t, 'Success-only rules return no decision.', 'Success-only rules return no decision. All shadow-data rows are model-based (section 4); the four `*_cluster_*` rows are the Round 10 orientation-pair cluster intervals. An "A" outcome of a fixed-horizon rule is not a validated reverse deployment approval of A.', 1)
    # ---- section 8 / 9
    lines = t.split('\n')
    replace_line(lines, '- **Anonymized release copies**', '- **Anonymized release copies** of manifests/config/README/protocol with `<REPO>`, `<HOME>`, `<TMP>` placeholders and the sha256 of each original: `release_anon/` (`MAPPING.md`). Originals are not edited. Round 10: the sanitized copy of the git-ignored local data manifest is now at the non-ignored path `release_anon/local_data_manifest.anon.json` (the Round 9 copy sat under an ignored `work/` directory and was never committed). Regeneration of the anonymized copies depends on the executing account and repository location (the strings to replace are derived at run time), so **no byte-for-byte portability of the anonymized copies is claimed**; `original_sha256` in `MAPPING.json` ties each copy to its original. The copies are a scoped allowlist, not approval to publish the whole branch anonymously.')
    a, b = section_bounds(lines, '## 9. Reproducibility')
    lines[a:b] = ['## 9. Reproducibility', '', '```',
                  '.venv/bin/python experiments/local_stream/run_v3_all.py                  # endpoint tests + v2 numerics + v3 analysis/report from the preserved raw files (CPU only, no model)',
                  '.venv/bin/python experiments/local_stream/run_v3_all.py --with-cs-check  # also re-runs the Round 9 Monte Carlo CS check (about 3 more minutes)',
                  '```', '',
                  'Input, code and output hashes with timestamps: `analysis_v3_manifest.json`; comparison of the regenerated v2 numbers with the Round 9 files: `v2_vs_v3_numeric_check.json`. Round 9 outputs as committed before this repair: `v2_pre_round10/`; v1 outputs: `v1_pre_round9/`.', '']
    t = '\n'.join(lines)
    low = t.lower()
    for bad in BANNED:
        assert bad not in low, 'banned wording survived: ' + bad
    assert 'before design-task outcomes' in t and 'composite harm signal for B; incumbent A retained' in t and 'DESCRIPTIVE ONLY' in t
    (rd / 'report_v3.md').write_text(t)
    stub = ['# Local-model prospective stream: report', '',
            'The current report is **[report_v3.md](report_v3.md)** (Round 10 post hoc repair on top of the Round 9 re-analysis: E2 task-level intervals labelled model-based, orientation-pair cluster analysis, descriptive pass/period table, '
            'R1 = running conditional mean under a stated filtration, R2 = unconditional iid-roster model, endpoint-exact betting capital).', '',
            'Superseded: [report_v2.md](report_v2.md) (Round 9; original bytes in `v2_pre_round10/`; its statements that the E2 intervals need no assumptions or are conservative by construction are withdrawn) and '
            '[v1_pre_round9/report.md](v1_pre_round9/report.md) (uncorrected two-sided CS and target wording). The top-level `summary.json`, `decision_rules.csv` and `sensitivity.csv` are the v1 files; '
            'use `summary_v2.json` / `running_cs_v2.csv` / `sensitivity_v2.csv` / `resources_v2.csv` for E1 and resources and `summary_v3.json` / `decision_rules_v3.csv` / `e2_cluster_v3.csv` / `pass_effects_v3.csv` for E2 and labels. '
            '`task_scores.csv`, `episodes_flat.csv` and all raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `design.*`) are unchanged.', '']
    (rd / 'report.md').write_text('\n'.join(stub))
    print('wrote', rd / 'report_v3.md', 'and report.md stub')


if __name__ == '__main__':
    main()
