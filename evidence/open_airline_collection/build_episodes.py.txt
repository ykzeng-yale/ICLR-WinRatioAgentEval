"""Parse tau2 results.json files into results/tau2_open/episodes.csv (one row per episode, every episode retained).

Outcome fields per episode (protocol.md section 6):
  success                 reward_info.reward == 1 (tau2 evaluates the task's reward_basis, [DB, COMMUNICATE] for every airline task
                          at the pinned commit; NL assertions are not evaluated under the default EvaluationType.ALL, so no LLM judge
                          enters the reward; 1.0 = all evaluated checks passed; missing reward = failure)
  agent_tokens_completion sum of usage.completion_tokens over ASSISTANT messages that carry `usage`
                          (each such message is one agent LLM call; the scripted greeting turn 0 has no usage)
  agent_tokens_prompt     sum of usage.prompt_tokens over the same messages (cumulative context re-sent per call)
  n_agent_llm_calls       number of assistant messages with usage (fallback: assistant messages after turn 0)
  n_assistant_tool_calls  total number of tool calls emitted by the agent (len(tool_calls) summed)
  duration                tau2 `duration`: wall-clock seconds of the whole simulation incl. user simulator and tool execution
  agent_generation_seconds sum of generation_time_seconds over assistant messages (agent inference time only)
  termination_reason, max_steps_hit (termination_reason == 'max_steps'), error (non-normal termination reasons)
  tokens_source           'usage' when every agent call had usage; otherwise 'usage+estimate' with
                          tokens_estimated_calls > 0: missing calls are estimated with the llama-server /tokenize
                          endpoint when --tokenize-url is given, else len(text)/4 (documented, flagged, counted)
Arm, task, trial and the design fields (arrival_index, pair_index, orientation, pass, block) are joined from design.json.
"""
from __future__ import annotations
import argparse, csv, json, urllib.request
from pathlib import Path

from common import EPISODE_COLUMNS, RESULTS_DIR, load_config
from design import A, B, load_design

NORMAL_TERMINATIONS = {'user_stop', 'agent_stop', 'max_steps'}


def _estimate_tokens(text: str, tokenize_url: str | None) -> int:
    if not text:
        return 0
    if tokenize_url:
        try:
            req = urllib.request.Request(tokenize_url.rstrip('/') + '/tokenize', data=json.dumps(dict(content=text)).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return len(json.loads(r.read())['tokens'])
        except Exception:
            pass
    return max(1, len(text) // 4)


def _assistant_text(m: dict) -> str:
    parts = [m.get('content') or '']
    for tc in m.get('tool_calls') or []:
        parts.append(json.dumps(tc.get('arguments', {})) if isinstance(tc, dict) else str(tc))
    return '\n'.join(parts)


def parse_simulation(sim: dict, tokenize_url: str | None = None) -> dict:
    msgs = sim.get('messages') or []
    asst = [m for m in msgs if m.get('role') == 'assistant']
    with_usage = [m for m in asst if m.get('usage')]
    # agent LLM calls: assistant messages after the scripted greeting (turn 0 has no LLM call)
    llm_calls = [m for m in asst if m.get('usage') or (m.get('turn_idx') not in (0, None))]
    comp = sum(int(m['usage'].get('completion_tokens') or 0) for m in with_usage)
    prompt = sum(int(m['usage'].get('prompt_tokens') or 0) for m in with_usage)
    missing = [m for m in llm_calls if not m.get('usage')]
    est_calls = 0
    for m in missing:
        comp += _estimate_tokens(_assistant_text(m), tokenize_url); est_calls += 1
    n_tc = sum(len(m.get('tool_calls') or []) for m in asst)
    reward = (sim.get('reward_info') or {}).get('reward')
    reward = float(reward) if reward is not None else None
    term = sim.get('termination_reason')
    served = sorted({(m.get('raw_data') or {}).get('model') for m in asst if (m.get('raw_data') or {}).get('model')})
    gen = [m.get('generation_time_seconds') for m in asst if m.get('generation_time_seconds') is not None]
    return dict(task_id=str(sim['task_id']), trial=int(sim.get('trial', 0)), tau2_seed=sim.get('seed'),
                success=bool(reward is not None and abs(reward - 1.0) < 1e-9), reward=reward,
                agent_tokens_completion=int(comp), agent_tokens_prompt=int(prompt), n_agent_llm_calls=len(llm_calls),
                n_assistant_tool_calls=int(n_tc), n_assistant_messages=len(asst), n_user_messages=sum(m.get('role') == 'user' for m in msgs),
                n_tool_messages=sum(m.get('role') == 'tool' for m in msgs), n_messages=len(msgs),
                duration=float(sim.get('duration')) if sim.get('duration') is not None else None,
                agent_generation_seconds=float(sum(gen)) if gen else None, termination_reason=term,
                max_steps_hit=bool(term == 'max_steps'), error=None if term in NORMAL_TERMINATIONS else term,
                tokens_source='usage' if est_calls == 0 else 'usage+estimate', tokens_estimated_calls=est_calls,
                served_models='|'.join(served), simulation_id=sim.get('id'), start_time=sim.get('start_time'), end_time=sim.get('end_time'))


def parse_results_file(path: Path, arm: str, tokenize_url: str | None = None) -> list:
    d = json.loads(Path(path).read_text())
    info = d.get('info') or {}
    agent_model = (info.get('agent_info') or {}).get('llm'); user_model = (info.get('user_info') or {}).get('llm')
    rows = []
    for sim in d.get('simulations') or []:
        r = parse_simulation(sim, tokenize_url)
        r.update(arm=arm, agent_model=agent_model, user_model=user_model, source_file=str(path))
        rows.append(r)
    return rows


def attach_design(rows: list, design: dict) -> list:
    by_unit = {(a['task_id'], a['trial']): a for a in design['arrivals']}
    for r in rows:
        a = by_unit.get((r['task_id'], r['trial']))
        if a is None:
            r.update(arrival_index=None, pair_index=None, position_in_pair=None, orientation=None, block=None, **{'pass': None})
            continue
        r.update(arrival_index=a['arrival_index'], pair_index=a['pair_index'], position_in_pair=a['position_in_pair'], orientation=a['orientation'],
                 block=a['block'], **{'pass': 1 if a['pass1_arm'] == r['arm'] else 2})
    return rows


def write_episodes(rows: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=EPISODE_COLUMNS, extrasaction='ignore'); w.writeheader()
        for r in sorted(rows, key=lambda r: (r['arm'], r['trial'], (len(r['task_id']), r['task_id']))):
            w.writerow({c: ('' if r.get(c) is None else r.get(c)) for c in EPISODE_COLUMNS})


def build(results_dir: Path, cfg: dict, raw_files: dict | None = None, tokenize_url: str | None = None) -> list:
    design = load_design(results_dir)
    raw_files = raw_files or {arm: results_dir / 'raw' / ('tau2_open_arm%s.json' % arm) for arm in (A, B)}
    rows = []
    for arm, p in raw_files.items():
        if Path(p).exists():
            rows += parse_results_file(Path(p), arm, tokenize_url)
    for r in rows:
        r['config_hash'] = cfg['_config_hash']
    attach_design(rows, design)
    dup = {}
    for r in rows:
        dup[(r['arm'], r['task_id'], r['trial'])] = dup.get((r['arm'], r['task_id'], r['trial']), 0) + 1
    dups = [k for k, v in dup.items() if v > 1]
    if dups:
        raise SystemExit('duplicate episodes for %s' % dups[:5])
    write_episodes(rows, results_dir / 'episodes.csv')
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--config', default=None)
    ap.add_argument('--tokenize-url', default=None, help='llama-server base URL (e.g. http://127.0.0.1:8081) used only for calls without usage')
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    rows = build(Path(args.results_dir), cfg, tokenize_url=args.tokenize_url)
    by_arm = {}
    for r in rows:
        by_arm.setdefault(r['arm'], []).append(r)
    print(json.dumps({arm: dict(n=len(v), success=sum(r['success'] for r in v), tokens_estimated_calls=sum(r['tokens_estimated_calls'] for r in v),
                                max_steps=sum(r['max_steps_hit'] for r in v), errors=sum(r['error'] is not None for r in v)) for arm, v in by_arm.items()}, indent=2))


if __name__ == '__main__':
    main()
