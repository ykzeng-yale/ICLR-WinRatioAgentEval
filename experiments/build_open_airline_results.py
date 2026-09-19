"""Reproduce bounded airline descriptions and an observed-array replay illustration.

No model requests, benchmark execution, contributed inference imports, or log replay.
Projection requires an explicitly supplied frozen source directory and raw hashes.
"""
from pathlib import Path
import argparse
import collections
import csv
import gzip
import hashlib
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare, normal_mixture_radius

OUT = ROOT / 'results/open_airline'
RAW_HASHES = {'A': '887c66a23c2c1c2188279ce658efb15436648a9e26251b62f569521df4845fd8',
              'B': '39a49567936fb14f5444ae6e406c43abd1cfbb21198540c8b8df585d8fa1c8f6'}
ATTEMPT_FIELDS = ('arm task trial tau2_seed invocation_index attempt_in_invocation '
                  'attempt_overall n_attempts_overall attempt_status failure_class '
                  'is_canonical_record_source canonical_record_basis '
                  'truncation_warnings_in_attempt attempt_start_utc_approx attempt_end_utc '
                  'attempt_wall_clock_s_approx attempt_end_basis').split()
POLICY_FIELDS = ('arm task trial invocation_index pre_amendment agent_max_tokens '
                 'user_max_tokens tau2_simulation_timeout_s n_attempts_all_invocations '
                 'n_discarded_attempts canonical_termination_reason '
                 'n_agent_responses_finish_length n_user_responses_finish_length').split()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def project(source):
    inputs = source / 'results/tau2_open'
    recorded = read_csv(inputs / 'episodes.csv')
    indexed = {(r['arm'], r['task_id'], int(r['trial'])): r for r in recorded}
    metrics = []
    source_hashes = {}
    for arm in ('A', 'B'):
        path = inputs / f'raw_gz/tau2_open_arm{arm}.json.gz'
        raw = gzip.decompress(path.read_bytes())
        if hashlib.sha256(raw).hexdigest() != RAW_HASHES[arm]:
            raise ValueError('Unreviewed raw airline array for arm ' + arm)
        source_hashes[str(path.relative_to(source))] = sha(path)
        for unit in json.loads(raw)['simulations']:
            key = (arm, str(unit['task_id']), int(unit['trial']))
            row = indexed[key]
            reward = (unit.get('reward_info') or {}).get('reward')
            result = {'arm': arm, 'task_id': key[1], 'trial': key[2],
                      'tau2_seed': unit['seed'], 'success': int(reward == 1),
                      'reward_missing': reward is None,
                      'reward_basis_present': bool((unit.get('reward_info') or {}).get('reward_basis')),
                      'termination_reason': unit['termination_reason'],
                      'has_saved_trajectory': bool(unit['messages']),
                      'agent_tokens_prompt': 0, 'agent_tokens_completion': 0,
                      'user_tokens_prompt': 0, 'user_tokens_completion': 0,
                      'n_assistant_tool_calls': 0, 'n_recorded_model_responses': 0}
            for message in unit['messages']:
                role = message['role']
                if role == 'assistant':
                    result['n_assistant_tool_calls'] += len(message.get('tool_calls') or [])
                usage = message.get('usage')
                if usage is not None and role in ('assistant', 'user'):
                    prefix = 'agent' if role == 'assistant' else 'user'
                    result[prefix + '_tokens_prompt'] += usage['prompt_tokens']
                    result[prefix + '_tokens_completion'] += usage['completion_tokens']
                    result['n_recorded_model_responses'] += 1
            assert result['success'] == int(row['success'] == 'True')
            for field in ('agent_tokens_prompt', 'agent_tokens_completion', 'n_assistant_tool_calls'):
                assert result[field] == int(row[field]), (key, field)
            metrics.append(result)
    OUT.mkdir(parents=True, exist_ok=True)
    metrics.sort(key=lambda r: (r['arm'], int(r['task_id']), r['trial']))
    dump(OUT / 'episode_metrics.json', metrics)
    design = json.loads((inputs / 'design.json').read_text())
    dump(OUT / 'assignment.json', {k: design[k] for k in
          ['arrivals', 'seed', 'n_pairs', 'n_tasks', 'n_trials', 'n_units',
           'n_unpaired', 'task_list_sha256', 'orientation_rule']})
    attempts = [{k: row[k] for k in ATTEMPT_FIELDS}
                for row in read_csv(inputs / 'all_attempt_accounting.csv')]
    policies = [{k: row[k] for k in POLICY_FIELDS}
                for row in read_csv(inputs / 'unit_policy_flags.csv')]
    write_csv(OUT / 'attempt_ledger.csv', attempts)
    write_csv(OUT / 'unit_policy_flags.csv', policies)
    handoff = json.loads((inputs / 'round10_handoff_numbers.json').read_text())
    counters = handoff['operational_accounting_failure_inclusive']
    dump(OUT / 'omitted_usage_counters.json', {
        k: counters[k] for k in ['invocation1_port8081', 'invocation2_port8081']})
    cfgpath = source / 'experiments/tau2_open/config.json'
    config = json.loads(cfgpath.read_text())
    safe_config = {k: config[k] for k in ['domain', 'task_ids', 'excluded_task_ids',
                   'airline_data_sha256', 'num_trials', 'tau2_seed', 'tau2_trial_seeds_expected',
                   'max_steps', 'max_errors', 'max_concurrency', 'hallucination_retries',
                   'agent_temperature', 'user_temperature', 'tau2_commit_expected',
                   'llama_cpp_commit_expected', 'llama_ctx_size', 'llama_parallel',
                   'hierarchy', 'absorbing_rule', 'alpha', 'success_margin']}
    safe_config['models'] = {alias: {**{k: m[k] for k in ['hf_repo', 'hf_revision', 'base_model', 'license']},
                           'files': [{'name': Path(f['path']).name, 'bytes': f['bytes'], 'sha256': f['sha256']}
                                     for f in m['gguf_files']]} for alias, m in config['models'].items()}
    safe_config['roles'] = {'A_agent': 'qwen2.5-7b-instruct', 'B_agent': 'qwen3-4b-instruct-2507',
                            'both_user_simulators': 'qwen2.5-7b-instruct'}
    safe_config['amended_settings'] = {'max_tokens_each_role_each_arm': 1024, 'simulation_timeout_s': 1800}
    dump(OUT / 'collection_config.json', safe_config)
    invocations = json.loads((inputs / 'run_manifest.json').read_text())['invocations']
    for name in ['episodes.csv', 'design.json', 'all_attempt_accounting.csv', 'unit_policy_flags.csv', 'run_manifest.json', 'raw_deposit_manifest.json', 'round10_handoff_numbers.json']:
        source_hashes['results/tau2_open/' + name] = sha(inputs / name)
    source_hashes['experiments/tau2_open/config.json'] = sha(cfgpath)
    dump(OUT / 'provenance.json', {
        'schema': 'airline-metric-projection-v1', 'source_file_sha256': source_hashes,
        'uncompressed_raw_sha256': RAW_HASHES,
        'projection': 'All 196 canonical units retained, including two empty-trajectory infrastructure failures. Success comes from archived reward_info.reward, with missing reward mapped to unsuccessful; retained usage and tool-call counts come from raw messages. No dialogue, tool arguments, customer strings, tracebacks, local paths or simulation UUIDs retained.',
        'attempt_projection_fields': ATTEMPT_FIELDS, 'policy_projection_fields': POLICY_FIELDS,
        'attempt_ledger_scope': '206 logged tau2-level attempts; complete discarded-attempt token usage unavailable. Independently checked server counters give a partial generated-token lower bound without role partition. Canonical metrics count only saved messages; empty placeholders do not establish zero operational cost.',
        'runtime': [{'invocation_index': i + 1, 'started_at': v['started_at'],
                     'hardware': v['hardware'], 'packages': v['packages'],
                     'finished_at': v.get('finished_at'), 'runner_sha256': v['harness_file_sha256'].get('run_tau2_open.py')}
                    for i, v in enumerate(invocations)],
        'analysis_scope': 'Descriptive canonical-array contrasts; post-hoc independent-orientation masked-replay illustration only. No task-population, fresh-run, operational saving or selection-adjusted inference.',
        'projection_output_sha256': {name: sha(OUT / name) for name in
                    ['episode_metrics.json', 'assignment.json', 'attempt_ledger.csv', 'unit_policy_flags.csv', 'collection_config.json', 'omitted_usage_counters.json']}})


def sign(a, b, tiers):
    columns = ['success', 'agent_tokens_completion', 'n_assistant_tool_calls']
    both = bool(a['success'] and b['success'])
    z, tier = compare([b[k] for k in columns], [a[k] for k in columns], tiers, [True, both, both])
    return int(z), int(tier), b['success'] - a['success']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project-source-dir', type=Path)
    args = ap.parse_args()
    if args.project_source_dir:
        project(args.project_source_dir)
    provenance = json.loads((OUT / 'provenance.json').read_text())
    for name, digest in provenance['projection_output_sha256'].items():
        assert sha(OUT / name) == digest, name
    units = json.loads((OUT / 'episode_metrics.json').read_text())
    design = json.loads((OUT / 'assignment.json').read_text())
    config = json.loads((OUT / 'collection_config.json').read_text())
    attempts, policies = read_csv(OUT / 'attempt_ledger.csv'), read_csv(OUT / 'unit_policy_flags.csv')
    omitted = json.loads((OUT / 'omitted_usage_counters.json').read_text())
    c1, c2 = omitted['invocation1_port8081'], omitted['invocation2_port8081']
    omitted_completed = (c1['generated_tokens_completed_requests'] - c1['smoke_tokens_first_request']
                         - c1['retained_in_canonical_records'] + c2['generated_tokens_completed_requests']
                         - c2['smoke_tokens'] - c2['retained_in_canonical_records'])
    omitted_lower = omitted_completed + c1['generated_tokens_in_cancelled_requests_lower_bound']
    assert omitted_completed == 48004 and omitted_lower == 246284
    index = {(r['arm'], r['task_id'], r['trial']): r for r in units}
    expected = {(arm, str(t), j) for arm in ('A', 'B') for t in range(1, 50) for j in (0, 1)}
    assert len(units) == len(index) == 196 and set(index) == expected
    assert len(attempts) == 206 and len(policies) == 196
    assert sum(not r['has_saved_trajectory'] for r in units) == 2
    assert sum(r['is_canonical_record_source'] == 'True' for r in attempts) == 194
    tiers = tuple(Tier(**t) for t in config['hierarchy'])
    get = lambda arm, arrival: index[arm, arrival['task_id'], arrival['trial']]
    replay = []
    for k in range(49):
        first, second = design['arrivals'][2*k:2*k+2]
        assert first['pair_index'] == second['pair_index'] == k + 1
        assert first['orientation'] == second['orientation']
        score1 = sign(get('A', first), get('B', second), tiers)
        score0 = sign(get('A', second), get('B', first), tiers)
        score = score1 if first['orientation'] == 1 else score0
        replay.append({'pair': k + 1, 'orientation': first['orientation'],
                       'observed_score': score[0], 'decisive_tier_zero_based': score[1],
                       'observed_success_difference': score[2], 'score_if_r0': score0[0], 'score_if_r1': score1[0],
                       'array_orientation_mean': (score0[0] + score1[0]) / 2,
                       'array_success_orientation_mean': (score0[2] + score1[2]) / 2})
    same_task = []
    for t in range(1, 50):
        for trial_a in (0, 1):
            for trial_b in (0, 1):
                z, tier, sd = sign(index['A', str(t), trial_a], index['B', str(t), trial_b], tiers)
                same_task.append({'task_id': str(t), 'trial_a': trial_a, 'trial_b': trial_b,
                                  'score': z, 'decisive_tier_zero_based': tier, 'success_difference': sd})
    n = np.arange(1, 50)
    radius = normal_mixture_radius(n, .05, 100.)
    mean = np.cumsum([r['observed_score'] for r in replay]) / n
    truth = np.cumsum([r['array_orientation_mean'] for r in replay]) / n
    running = [{'n': int(i), 'observed_mean': float(m), 'array_mean': float(t),
                'radius': float(rad), 'lower': float(max(-1, m-rad)), 'upper': float(min(1, m+rad))}
               for i, m, t, rad in zip(n, mean, truth, radius)]
    summaries = []
    for arm in ('A', 'B'):
        rows = [r for r in units if r['arm'] == arm]
        a = [r for r in attempts if r['arm'] == arm]
        summary = {'arm': arm, 'canonical_units': len(rows), 'successes': sum(r['success'] for r in rows),
                   'saved_trajectories': sum(r['has_saved_trajectory'] for r in rows), 'logged_attempts': len(a),
                   'discarded_attempts': sum(r['is_canonical_record_source'] != 'True' for r in a),
                   'pre_amendment_units': sum(r['arm'] == arm and r['pre_amendment'] == 'true' for r in policies)}
        for key in ['agent_tokens_prompt', 'agent_tokens_completion', 'user_tokens_prompt', 'user_tokens_completion',
                    'n_assistant_tool_calls', 'n_recorded_model_responses']:
            summary['canonical_' + key] = sum(r[key] for r in rows)
        summaries.append(summary)
    counts = lambda vals: {'wins': sum(v == 1 for v in vals), 'ties': sum(v == 0 for v in vals),
                           'losses': sum(v == -1 for v in vals), 'n': len(vals), 'net_benefit': sum(vals)/len(vals)}
    report = {'arms': summaries, 'replay': counts([r['observed_score'] for r in replay]),
              'same_task_all': counts([r['score'] for r in same_task]),
              'same_trial': counts([r['score'] for r in same_task if r['trial_a'] == r['trial_b']]),
              'different_trial': counts([r['score'] for r in same_task if r['trial_a'] != r['trial_b']]),
              'final_masked_replay_illustration': running[-1],
              'discarded_failure_classes': dict(collections.Counter(r['failure_class'] for r in attempts if r['failure_class'])),
              'inference_scope': provenance['analysis_scope'], 'complete_failed_attempt_token_totals': None,
              'omitted_a_generated_tokens_lower_bound': omitted_lower,
              'omitted_generated_tokens_role_partition': None}
    assert report['replay']['wins'] == 10 and report['replay']['ties'] == 30 and report['replay']['losses'] == 9
    assert report['same_task_all']['wins'] == 28 and report['same_task_all']['ties'] == 141 and report['same_task_all']['losses'] == 27
    assert [r['successes'] for r in summaries] == [15, 15]
    write_csv(OUT / 'replay_scores.csv', replay)
    write_csv(OUT / 'same_task_scores.csv', same_task)
    write_csv(OUT / 'masked_replay_bands.csv', running)
    write_csv(OUT / 'canonical_accounting.csv', summaries)
    dump(OUT / 'summary.json', report)
    fields = [('Planned canonical units', 'canonical_units'), ('Successful units', 'successes'),
              ('Saved trajectories', 'saved_trajectories'), ('Logged attempts', 'logged_attempts'),
              ('Discarded attempts', 'discarded_attempts'), ('Pre-amendment canonical units', 'pre_amendment_units'),
              ('Agent completion tokens, saved messages', 'canonical_agent_tokens_completion'),
              ('User completion tokens, saved messages', 'canonical_user_tokens_completion')]
    table = r'\begin{tabular}{lrr}\toprule' + '\n' + r' & A & B\\\midrule' + '\n'
    table += '\n'.join(label + f" & {summaries[0][key]:,} & {summaries[1][key]:,} " + r'\\' for label, key in fields)
    table += '\n' + r'\bottomrule\end{tabular}' + '\n'
    (ROOT / 'paper/open_airline_table.tex').write_text(table)
    files = [str(p.relative_to(ROOT)) for p in sorted(OUT.glob('*')) if p.is_file()] + ['paper/open_airline_table.tex']
    dump(ROOT / 'results/open_airline_integrity.json', {'outputs': [{'path': name, 'sha256': sha(ROOT / name)} for name in files],
         'analysis_script_sha256': sha(Path(__file__)), 'core_sha256': sha(ROOT / 'src/winstats.py'), 'new_model_calls': 0})
    print(json.dumps({'canonical_units': len(units), 'attempts': len(attempts), 'replay': report['replay'],
                      'same_task': report['same_task_all'], 'last_masked_replay': running[-1]}, indent=2))


if __name__ == '__main__':
    main()
