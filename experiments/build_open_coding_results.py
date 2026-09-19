"""Recompute audited coding summaries from a row-preserving metrics projection.

No model requests, candidate-program execution, or contributed inference imports.
The optional projection operation requires the frozen source directory explicitly.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare, normal_mixture_radius

OUT = ROOT / 'results/open_coding'
RAW_SHA = '95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0'
FIELDS = ('task_id benchmark variant variant_letter trial arrival_index pair_index '
          'orientation pass start_ts end_ts n_llm_calls prompt_tokens completion_tokens '
          'tokens_estimated n_executions repair_rounds self_test_passed success '
          'sandbox_flag timed_out model connection_retries llm_call_seconds '
          'execution_seconds finish_reasons response_models verify_seconds sentinel_seen '
          'hack_flags static_flags sandbox_kind latency_scope latency_s '
          'entry_point_defined verify_returncode sandbox_limits_applied').split()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_csv(path, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def project(source):
    raw = source / 'results/local_stream/episodes.jsonl'
    if sha(raw) != RAW_SHA:
        raise ValueError('Unreviewed raw source: SHA-256 differs')
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    projected = [{**{key: row[key] for key in FIELDS},
                  'error_present': bool(row.get('error'))} for row in rows]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'episode_metrics.jsonl').write_text(''.join(
        json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n' for row in projected))
    design = json.loads((source / 'results/local_stream/design.json').read_text())
    write_json(OUT / 'assignment.json', {key: design[key] for key in
               ['arrivals', 'seed', 'n_pairs', 'n_tasks', 'n_unpaired', 'trial',
                'variants', 'strata', 'task_list_sha256', 'config_hash']})
    config = json.loads((source / 'experiments/local_stream/config.json').read_text())
    config.pop('base_url')
    write_json(OUT / 'collection_config.json', config)
    invocation = json.loads((source / 'results/local_stream/run_manifest.json').read_text())['invocations'][0]
    data = json.loads((source / 'results/local_stream/data_manifest.json').read_text())
    sources = {key: {k: v for k, v in value.items() if k not in ['local_path', 'recorded_in']}
               for key, value in data['sources'].items()}
    snapshot = invocation['model_snapshot']
    provenance = {
        'schema': 'row-preserving-coding-metrics-v1', 'original_episode_sha256': RAW_SHA,
        'original_design_sha256': sha(source / 'results/local_stream/design.json'),
        'original_config_file_sha256': sha(source / 'experiments/local_stream/config.json'),
        'original_run_manifest_sha256': sha(source / 'results/local_stream/run_manifest.json'),
        'original_benchmark_manifest_sha256': sha(source / 'results/local_stream/data_manifest.json'),
        'config_projection': 'Original configuration values retained except local base_url omitted; exact original configuration is also retained as historical text.',
        'retained_episode_fields': FIELDS, 'derived_field': 'error_present = bool(error)',
        'projection': 'All rows in original order; no outcome-based filtering. Candidate code, self-tests, verifier stderr, retry details, endpoints and identifying paths/hashes are omitted.',
        'n_original_rows': len(rows), 'n_projected_rows': len(projected),
        'nonempty_original_errors': sum(bool(row.get('error')) for row in rows),
        'nonempty_original_retry_logs': sum(bool(row.get('retry_log')) for row in rows),
        'collection': {k: invocation[k] for k in ['at', 'finished_at', 'status', 'trial', 'dry_run', 'hardware', 'packages']},
        'model_snapshot': {k: snapshot[k] for k in ['model', 'revision', 'expected_revision', 'files', 'total_bytes', 'ok']},
        'model_license': 'Apache-2.0; see upstream model card',
        'source_datasets': sources,
        'analysis_scope': 'Root normal-mixture reanalysis only, chosen post hoc; E2 is descriptive. No contributed E2/R2 uncertainty or betting-capital endpoint routines.',
        'projection_output_sha256': {name: sha(OUT / name) for name in
                                    ['episode_metrics.jsonl', 'assignment.json', 'collection_config.json']}}
    write_json(OUT / 'provenance.json', provenance)


def score(a, b, config):
    tiers = tuple(Tier(**tier) for tier in config['hierarchy'])
    values = lambda r: [int(r['success']), r['latency_s'], r['completion_tokens']]
    both = bool(a['success'] and b['success'])
    z, tier = compare(values(b), values(a), tiers, [True, both, both])
    return int(z), int(tier), int(b['success']) - int(a['success'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-source-dir', type=Path)
    args = parser.parse_args()
    if args.project_source_dir:
        project(args.project_source_dir)
    provenance = json.loads((OUT / 'provenance.json').read_text())
    for name, digest in provenance['projection_output_sha256'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Projection integrity mismatch: ' + name)
    records = [json.loads(line) for line in (OUT / 'episode_metrics.jsonl').read_text().splitlines()]
    design = json.loads((OUT / 'assignment.json').read_text())
    config = json.loads((OUT / 'collection_config.json').read_text())
    assert len(records) == 1182 and len(design['arrivals']) == 591
    assert {r['trial'] for r in records} == {1}
    assert [(r['pass'], r['arrival_index']) for r in records] == [(p, i) for p in (1, 2) for i in range(1, 592)]
    by_task_variant = {(r['task_id'], r['variant_letter']): r for r in records}
    assert len(by_task_variant) == 1182
    for arrival in design['arrivals']:
        for p in (1, 2):
            row = records[(p - 1) * 591 + arrival['arrival_index'] - 1]
            assert row['task_id'] == arrival['task_id']
            assert row['variant'] == arrival[f'pass{p}_variant']
    pairs = []
    for k in range(1, 296):
        pair = records[2 * k - 2:2 * k]
        assert {r['pair_index'] for r in pair} == {k}
        arms = {r['variant_letter']: r for r in pair}
        z, tier, sd = score(arms['A'], arms['B'], config)
        pairs.append({'pair': k, 'task_a': arms['A']['task_id'], 'task_b': arms['B']['task_id'],
                      'score': z, 'decisive_tier_zero_based': tier, 'success_difference': sd})
    shadow = []
    for arrival in design['arrivals']:
        task = arrival['task_id']
        z, tier, sd = score(by_task_variant[task, 'A'], by_task_variant[task, 'B'], config)
        shadow.append({'task_id': task, 'benchmark': arrival['benchmark'], 'score': z,
                       'decisive_tier_zero_based': tier, 'success_difference': sd})
    counts = lambda rs: {'n': len(rs), 'wins': sum(r['score'] == 1 for r in rs),
                         'ties': sum(r['score'] == 0 for r in rs), 'losses': sum(r['score'] == -1 for r in rs),
                         'net_benefit': sum(r['score'] for r in rs) / len(rs),
                         'success_difference': sum(r['success_difference'] for r in rs) / len(rs)}
    e1, e2 = counts(pairs), counts(shadow)
    assert (e1['wins'], e1['ties'], e1['losses']) == (69, 18, 208)
    assert (e2['wins'], e2['ties'], e2['losses']) == (41, 121, 429)
    n = np.arange(1, 296)
    radius = normal_mixture_radius(n, alpha=.05, rho=100.)
    nb = np.cumsum([r['score'] for r in pairs]) / n
    sd = np.cumsum([r['success_difference'] for r in pairs]) / n
    running = [{'n': int(i), 'net_benefit': float(z), 'success_difference': float(d),
                'radius': float(rad), 'nb_lo': float(max(-1., z - rad)),
                'nb_hi': float(min(1., z + rad)), 'success_lo': float(max(-1., d - rad)),
                'success_hi': float(min(1., d + rad))} for i, z, d, rad in zip(n, nb, sd, radius)]
    resources = []
    for arm in ('A', 'B'):
        rows = [r for r in records if r['variant_letter'] == arm]
        resources.append({'arm': arm, 'episodes': len(rows), 'successes': sum(r['success'] for r in rows),
                          'model_calls': sum(r['n_llm_calls'] for r in rows),
                          'prompt_tokens': sum(r['prompt_tokens'] for r in rows),
                          'completion_tokens': sum(r['completion_tokens'] for r in rows),
                          'total_tokens': sum(r['prompt_tokens'] + r['completion_tokens'] for r in rows),
                          'latency_sum_s': sum(r['latency_s'] for r in rows),
                          'latency_mean_s': statistics.mean(r['latency_s'] for r in rows),
                          'latency_median_s': statistics.median(r['latency_s'] for r in rows),
                          'n_executions_including_verifier': sum(r['n_executions'] for r in rows),
                          'selftest_executions': sum(r['n_executions'] - 1 for r in rows),
                          'verify_seconds_sum': sum(r['verify_seconds'] for r in rows),
                          'estimated_token_episodes': sum(bool(r['tokens_estimated']) for r in rows),
                          'timed_out': sum(bool(r['timed_out']) for r in rows),
                          'error_episodes': sum(r['error_present'] for r in rows)})
    assert all(r['episodes'] == 591 and r['successes'] == 433 for r in resources)
    summary = {'first_pass': e1, 'same_task_descriptive': e2, 'final_marginal_r1': running[-1],
               'first_negative_nb_upper_endpoint': next((r['n'] for r in running if r['nb_hi'] < 0), None),
               'any_success_lower_above_minus_003': any(r['success_lo'] > -.03 for r in running),
               'analysis_status': 'Post-hoc fixed construction, no adjustment for analysis selection; conditional-mean target, not full-roster inference; two marginal 95% bands, not joint 95%.',
               'resources': resources}
    write_csv(OUT / 'first_pass_pairs.csv', pairs)
    write_csv(OUT / 'same_task_scores.csv', shadow)
    write_csv(OUT / 'running_mean_bands.csv', running)
    write_csv(OUT / 'resources.csv', resources)
    write_json(OUT / 'summary.json', summary)
    a, b = resources
    table = '\n'.join(label + ' & ' + fmt.format(a[key]) + ' & ' + fmt.format(b[key]) + r' \\'
                      for label, key, fmt in [('Successful tasks', 'successes', '{:,}'),
                       ('Model calls', 'model_calls', '{:,}'), ('Prompt tokens', 'prompt_tokens', '{:,}'),
                       ('Completion tokens', 'completion_tokens', '{:,}'), ('Total tokens', 'total_tokens', '{:,}'),
                       ('Mean workflow latency (s)', 'latency_mean_s', '{:.3f}'),
                       ('Median workflow latency (s)', 'latency_median_s', '{:.3f}'),
                       ('Self-test executions', 'selftest_executions', '{:,}')])
    (ROOT / 'paper/open_coding_resource_rows.tex').write_text(
        r'\begin{tabular}{lrr}\toprule' + '\n' + r' & A & B\\\midrule' + '\n'
        + table + '\n' + r'\bottomrule\end{tabular}' + '\n')
    outputs = [str(p.relative_to(ROOT)) for p in sorted(OUT.glob('*')) if p.is_file()]
    outputs += ['paper/open_coding_resource_rows.tex']
    write_json(ROOT / 'results/open_coding_integrity.json', {
        'outputs': [{'path': path, 'sha256': sha(ROOT / path)} for path in outputs],
        'analysis_script_sha256': sha(Path(__file__)), 'core_sha256': sha(ROOT / 'src/winstats.py'),
        'commercial_calls': 0, 'model_calls_for_reanalysis': 0})
    print(json.dumps({'episodes': len(records), 'first_pass': e1, 'same_task_descriptive': e2,
                      'final_band': running[-1], 'latency_ratio': b['latency_mean_s'] / a['latency_mean_s']}, indent=2))


if __name__ == '__main__':
    main()
