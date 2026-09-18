"""Fixed-archive ordinal trace replay; no latency, deployment or safety claim.

Read evidence/trace_certificate_protocol.md before interpreting the outputs.
Bounds depend only on revealed states and a common conservative numerical
allowance. Full archived outcomes are used separately for validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare

D = Decimal
ZERO = D('0')
Q = D('0.95')
ATOL = D('1e-10')
RTOL = D('1e-10')
MODELS = {'gpt-4.1-2025-04-14': 'GPT-4.1', 'o4-mini-2025-04-16': 'o4-mini',
          'claude-3-7-sonnet-20250219': 'Claude-3.7'}
CONTRASTS = [('o4-mini', 'GPT-4.1'), ('Claude-3.7', 'GPT-4.1'), ('o4-mini', 'Claude-3.7')]
DOMAINS = ('airline', 'retail', 'telecom')
TIERS = [Tier('success'), Tier('cost', False, relative_tolerance=.05), Tier('tools', False)]
TIER_ORDER = {'success': 0, 'cost': 1, 'tools': 2, 'tie': 3}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def anonymous(domain, task):
    return hashlib.sha256(f'{domain}:{task}'.encode()).hexdigest()[:12]


def task_sort(task):
    return (0, int(task)) if task.isdigit() else (1, task)


@dataclass(frozen=True)
class Episode:
    domain: str
    model: str
    task: str
    trial: int
    seed: int
    success: int
    final_cost: Decimal
    cumulative_cost: tuple
    cumulative_calls: tuple

    @property
    def terminal(self):
        return len(self.cumulative_cost)  # L actual messages + one terminal tick.

    @property
    def final_calls(self):
        return self.cumulative_calls[-1]


@dataclass(frozen=True)
class RevealedState:
    complete: bool
    success: int | None
    cost_lo: Decimal
    cost_hi: Decimal | None  # None represents unbounded future additions.
    calls_lo: int
    calls_hi: int | None
    assistant_messages_exposed: int
    observed_cost: Decimal


def reveal(episode, tick, allowance):
    """Scheduling layer. Hidden fields do not enter a pending state's bounds."""
    exposed = min(tick, episode.terminal - 1)
    observed_cost = episode.cumulative_cost[exposed]
    observed_calls = episode.cumulative_calls[exposed]
    if tick >= episode.terminal:
        return RevealedState(True, episode.success, episode.final_cost, episode.final_cost,
                             episode.final_calls, episode.final_calls, exposed, observed_cost)
    return RevealedState(False, None, max(ZERO, observed_cost - allowance), None,
                         observed_calls, None, exposed, observed_cost)


def possible_resource_scores(a, b):
    """Outer feasible set over rectangular nonnegative cost/count intervals."""
    outcomes = set()
    if b.cost_hi is None or a.cost_lo < Q * b.cost_hi:
        outcomes.add((1, 'cost'))
    if a.cost_hi is None or b.cost_lo < Q * a.cost_hi:
        outcomes.add((-1, 'cost'))
    cost_tie = ((b.cost_hi is None or Q * a.cost_lo <= b.cost_hi)
                and (a.cost_hi is None or Q * b.cost_lo <= a.cost_hi))
    if cost_tie:
        if b.calls_hi is None or a.calls_lo < b.calls_hi:
            outcomes.add((1, 'tools'))
        if a.calls_hi is None or b.calls_lo < a.calls_hi:
            outcomes.add((-1, 'tools'))
        if ((b.calls_hi is None or a.calls_lo <= b.calls_hi)
                and (a.calls_hi is None or b.calls_lo <= a.calls_hi)):
            outcomes.add((0, 'tie'))
    assert outcomes
    return outcomes


def possible_hierarchy_scores(a, b):
    """Certificate engine: receives only already revealed state objects."""
    outcomes = set()
    sa = [a.success] if a.complete else [0, 1]
    sb = [b.success] if b.complete else [0, 1]
    for av in sa:
        for bv in sb:
            if av != bv:
                outcomes.add((av - bv, 'success'))
            elif av == 0:
                outcomes.add((0, 'tie'))
            else:
                outcomes.update(possible_resource_scores(a, b))
    assert outcomes
    return outcomes


def final_score(a, b):
    if a.success != b.success:
        return a.success - b.success, 'success'
    if not a.success:
        return 0, 'tie'
    if a.final_cost < Q * b.final_cost:
        return 1, 'cost'
    if b.final_cost < Q * a.final_cost:
        return -1, 'cost'
    if a.final_calls != b.final_calls:
        return (1 if a.final_calls < b.final_calls else -1), 'tools'
    return 0, 'tie'


def load_and_audit(raw, public_manifest):
    manifest = json.loads(public_manifest.read_text())
    sources = [r for r in manifest['raw_sources'] if r['file'].startswith('tau2_') and r['file'].endswith('4trials.json')]
    assert len(sources) == 9
    episodes = {}
    audits = []
    common_allowance = ZERO
    for source in sorted(sources, key=lambda r: r['file']):
        path = raw / source['file']
        assert sha(path) == source['sha256'], f'Source hash mismatch: {path.name}'
        data = json.loads(path.read_text(), parse_float=D)
        model = MODELS[data['info']['agent_info']['llm']]
        domain = next(d for d in DOMAINS if f'_{d}_' in path.name)
        max_error = ZERO
        message_count = zero_messages = 0
        tasks = set()
        for run in data['simulations']:
            cost = D(str(run['agent_cost']))
            success = D(str(run['reward_info']['reward']))
            assert cost.is_finite() and cost >= 0 and success in (0, 1)
            increments = []
            calls = []
            for message in run['messages']:
                if message['role'] != 'assistant':
                    continue
                assert message.get('cost') is not None, 'Missing assistant message cost'
                amount = D(str(message['cost']))
                assert amount.is_finite() and amount >= 0, 'Invalid message cost'
                tool_calls = message.get('tool_calls') or []
                assert isinstance(tool_calls, list)
                increments.append(amount); calls.append(len(tool_calls))
                message_count += 1; zero_messages += amount == 0
            assert increments, 'No assistant events in archived episode'
            cumulative_cost = [ZERO]
            cumulative_calls = [0]
            for amount, n_calls in zip(increments, calls):
                cumulative_cost.append(cumulative_cost[-1] + amount)
                cumulative_calls.append(cumulative_calls[-1] + n_calls)
            error = abs(cumulative_cost[-1] - cost)
            assert error <= ATOL + RTOL * abs(cost), 'Agent cost does not reconcile'
            max_error = max(max_error, error)
            common_allowance = max(common_allowance, ATOL + RTOL * max(D(1), cost))
            task = str(run['task_id']); trial = int(run['trial']); seed = int(run['seed'])
            key = domain, model, task, trial
            assert key not in episodes
            episodes[key] = Episode(domain, model, task, trial, seed, int(success), cost,
                                    tuple(cumulative_cost), tuple(cumulative_calls))
            tasks.add(task)
        audits.append(dict(domain=domain, model=model, source_file=path.name,
                           source_sha256=source['sha256'], source_url=source['url'],
                           tasks=len(tasks), episodes=len(data['simulations']),
                           assistant_messages=message_count, zero_cost_assistant_messages=zero_messages,
                           maximum_absolute_cost_discrepancy=str(max_error),
                           nonnegative_cost_checks_passed=True, sum_cost_checks_passed=True))
    total_tasks = 0
    for domain in DOMAINS:
        model_tasks = {m: {k[2] for k in episodes if k[:2] == (domain, m)} for m in MODELS.values()}
        assert len({frozenset(t) for t in model_tasks.values()}) == 1
        total_tasks += len(model_tasks['o4-mini'])
        for task in model_tasks['o4-mini']:
            trial_maps = []
            for model in MODELS.values():
                found = {k[3]: e.seed for k, e in episodes.items() if k[:3] == (domain, model, task)}
                assert len(found) == 4 and len(set(found.values())) == 4
                trial_maps.append(found)
            assert all(m == trial_maps[0] for m in trial_maps)
    assert total_tasks == 278 and len(episodes) == 3336
    return episodes, audits, sources, common_allowance


def replay_pair(a, b, allowance):
    truth, tier = final_score(a, b)
    arr_a = [a.success, float(a.final_cost), a.final_calls]
    arr_b = [b.success, float(b.final_cost), b.final_calls]
    eligible = [True, bool(a.success and b.success), bool(a.success and b.success)]
    original_z, original_tier = compare(arr_a, arr_b, TIERS, eligible)
    original_name = 'tie' if int(original_tier) == -1 else TIERS[int(original_tier)].name
    assert int(original_z) == truth and original_name == tier, 'Decimal final rule differs from existing comparator'
    last = max(a.terminal, b.terminal)
    first = None
    first_states = None
    first_tiers = None
    first_sign = None
    previous = (-1, 1)
    prefix_checks = 0
    for tick in range(last + 1):
        av = reveal(a, tick, allowance); bv = reveal(b, tick, allowance)
        for state, episode in ((av, a), (bv, b)):
            assert state.cost_lo <= episode.final_cost and state.calls_lo <= episode.final_calls
            if not state.complete:
                assert state.success is None and state.cost_hi is None and state.calls_hi is None
        outcomes = possible_hierarchy_scores(av, bv)
        lo = min(sign for sign, _ in outcomes); hi = max(sign for sign, _ in outcomes)
        assert lo <= truth <= hi, 'Completion interval excludes archived final score'
        assert lo >= previous[0] and hi <= previous[1], 'Intervals are not nested'
        previous = lo, hi
        prefix_checks += 1
        if lo == hi and first is None:
            first = tick; first_states = (av, bv)
            first_sign = lo
            first_tiers = '|'.join(sorted({t for _, t in outcomes}, key=TIER_ORDER.get))
    assert first is not None and previous == (truth, truth) and first <= last
    early = first < last
    if early:
        assert truth != 0
        winner = first_states[0] if truth == 1 else first_states[1]
        loser = first_states[1] if truth == 1 else first_states[0]
        assert winner.complete and winner.success == 1 and not loser.complete
    row = dict(domain=a.domain, model_a=a.model, model_b=b.model,
               task_hash=anonymous(a.domain, a.task), trial_a=a.trial, trial_b=b.trial,
               seed_a=a.seed, seed_b=b.seed, final_sign=truth, final_decisive_tier=tier,
               terminal_tick_a=a.terminal, terminal_tick_b=b.terminal,
               completion_only_tick=last, certificate_tick=first,
               resolved_early=early, certificate_direction='A_win' if first_sign > 0 else 'B_win' if first_sign < 0 else 'tie',
               certificate_possible_decisive_tiers=first_tiers,
               ordinal_resolution_lead=last - first, prefixes_checked=prefix_checks)
    # Diagnostic inputs exclude unrevealed final tier and future terminal/lead metadata.
    example = {key: row[key] for key in ('domain', 'model_a', 'model_b', 'task_hash',
               'trial_a', 'trial_b', 'seed_a', 'seed_b', 'certificate_tick',
               'certificate_direction', 'certificate_possible_decisive_tiers')}
    example['certified_sign'] = first_sign
    for label, state in zip(('a', 'b'), first_states):
        example.update({f'{label}_complete_at_certificate': state.complete,
                        f'{label}_revealed_success': state.success if state.complete else 'unknown',
                        f'{label}_assistant_messages_exposed': state.assistant_messages_exposed,
                        f'{label}_observed_cumulative_cost': str(state.observed_cost),
                        f'{label}_certified_cost_lower_bound': str(state.cost_lo),
                        f'{label}_final_cost_if_revealed': str(state.cost_hi) if state.complete else 'unknown',
                        f'{label}_issued_tool_calls_observed': state.calls_lo})
    return row, example


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['domain'], row['model_a'], row['model_b'])].append(row)
    summaries = []
    for (domain, a, b), values in groups.items():
        early = [r for r in values if r['resolved_early']]
        leads = [r['ordinal_resolution_lead'] for r in early]
        directions = Counter(r['certificate_direction'] for r in early)
        tiers = Counter(r['final_decisive_tier'] for r in early)
        summaries.append(dict(domain=domain, model_a=a, model_b=b,
                              motivating_case=a == 'o4-mini' and b == 'Claude-3.7' and domain in ('retail', 'telecom'),
                              tasks=len({r['task_hash'] for r in values}), comparisons=len(values),
                              early_certificates=len(early), early_fraction=len(early) / len(values),
                              early_a_wins=directions['A_win'], early_b_wins=directions['B_win'], early_ties=directions['tie'],
                              early_final_success_tier=tiers['success'], early_final_cost_tier=tiers['cost'], early_final_tools_tier=tiers['tools'],
                              mean_ordinal_lead_all=float(np.mean([r['ordinal_resolution_lead'] for r in values])),
                              mean_ordinal_lead_early=float(np.mean(leads)) if leads else '',
                              median_ordinal_lead_early=float(np.median(leads)) if leads else '',
                              maximum_ordinal_lead=max(leads) if leads else 0,
                              prefix_containment_checks=sum(r['prefixes_checked'] for r in values)))
    return summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-dir', type=Path, default=ROOT.parents[1] / 'work/empirical_sources')
    args = parser.parse_args()
    public_manifest = ROOT / 'results/public_manifest.json'
    protocol = ROOT / 'evidence/trace_certificate_protocol.md'
    protocol_hash = sha(protocol)
    episodes, audits, sources, allowance = load_and_audit(args.raw_dir, public_manifest)
    rows, examples = [], []
    example_counts = Counter()
    for domain in DOMAINS:
        tasks = sorted({e.task for e in episodes.values() if e.domain == domain}, key=task_sort)
        for a, b in CONTRASTS:
            for task in tasks:
                aruns = sorted([e for e in episodes.values() if (e.domain, e.model, e.task) == (domain, a, task)], key=lambda e: e.trial)
                bruns = sorted([e for e in episodes.values() if (e.domain, e.model, e.task) == (domain, b, task)], key=lambda e: e.trial)
                for ea in aruns:
                    for eb in bruns:
                        if ea.trial == eb.trial:
                            assert ea.seed == eb.seed
                            continue
                        assert ea.seed != eb.seed
                        row, example = replay_pair(ea, eb, allowance)
                        rows.append(row)
                        key = domain, a, b
                        if row['resolved_early'] and example_counts[key] < 3:
                            examples.append(example); example_counts[key] += 1
    assert len(rows) == 10008
    summaries = summarize(rows)
    assert len(summaries) == 9 and sha(protocol) == protocol_hash
    output = ROOT / 'results'
    files = []
    for suffix, table in [('cost_audit', audits), ('pairs', rows), ('summary', summaries), ('examples', examples)]:
        path = output / f'trace_certificate_{suffix}.csv'
        write_csv(path, table); files.append(path)
    manifest = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
                    protocol_sha256=protocol_hash, source_code_sha256=sha(Path(__file__)),
                    comparator_sha256=sha(ROOT / 'src/winstats.py'), public_manifest_sha256=sha(public_manifest),
                    python=platform.python_version(), numpy=np.__version__,
                    source_files=sources, cost_allowance=str(allowance), cost_arithmetic='Decimal on archived numeric strings',
                    cost_absolute_tolerance=str(ATOL), cost_relative_tolerance=str(RTOL),
                    tasks=278, models=3, trials_per_task_model=4, episodes=len(episodes), comparisons=len(rows),
                    assistant_messages=sum(r['assistant_messages'] for r in audits),
                    every_prefix_containment_checks=sum(r['prefixes_checked'] for r in rows),
                    early_certificates=sum(r['resolved_early'] for r in rows),
                    checks=dict(source_hashes=True, nonnegative_message_costs=True, final_cost_reconciliation=True,
                                verified_seed_grid=True, no_hidden_labels_in_pending_states=True,
                                pending_lower_bounds_below_final=True, every_prefix_containment=True,
                                interval_nesting=True, final_collapse=True, final_rule_matches_existing_comparator=True),
                    output_sha256={p.name: sha(p) for p in files},
                    inference='Descriptive fixed archive; dependent task/seed comparisons; no population confidence intervals or sequential deployment decisions.',
                    replay='Ordinal assistant-message ticks with a terminal marker; not observed concurrent latency, operational savings, or a safety evaluation.')
    (output / 'trace_certificate_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'comparisons': len(rows), 'early_certificates': manifest['early_certificates'],
                      'prefix_checks': manifest['every_prefix_containment_checks'], 'cost_allowance': str(allowance),
                      'summaries': summaries}, indent=2))


if __name__ == '__main__':
    main()
