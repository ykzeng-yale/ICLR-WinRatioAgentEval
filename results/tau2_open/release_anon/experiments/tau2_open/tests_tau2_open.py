"""Unit tests for the tau2 open-model stream harness (stdlib unittest; no pytest dependency).

Run:  <REPO>/.venv/bin/python -m unittest experiments/tau2_open/tests_tau2_open.py -v
No test contacts a model server or runs tau2; dry runs use the deterministic mock generator in temp dirs.
"""
from __future__ import annotations
import argparse, csv, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np

from common import RESULTS_DIR, canonical_json, load_config, sha256_text
import design as design_mod
from design import A, B, check_pairing_invariants, content_sha256, generate, load_design, task_list_sha256, write_design
from build_episodes import attach_design, parse_results_file, parse_simulation
import run_tau2_open
import analysis
from winstats import Tier, betting_log_e_ternary, compare

PY = sys.executable
CFG = load_config()
TAU2_SIMS = Path(CFG['tau2_dir']) / 'data' / 'simulations'


class DesignTests(unittest.TestCase):
    def _sha(self, hashseed):
        env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
        out = subprocess.run([PY, str(HERE / 'design.py'), '--print-sha-only'], capture_output=True, text=True, env=env, cwd=str(HERE), timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.strip()

    def test_deterministic_across_processes_and_hashseeds(self):
        s0, s1 = self._sha(0), self._sha(12345)
        self.assertEqual(s0, s1); self.assertEqual(len(s0), 64)
        self.assertEqual(content_sha256(generate(CFG, CFG['design_seed'])), s0)
        frozen = RESULTS_DIR / 'design.json'
        if frozen.exists():  # the frozen primary design must be exactly what the generator produces from the current config
            d = load_design(RESULTS_DIR)
            self.assertEqual(content_sha256(d), s0)
            self.assertEqual(d['config_hash'], CFG['_config_hash'])
            self.assertEqual(d['n_pairs'], 49); self.assertEqual(d['n_units'], 98); self.assertEqual(d['seed'], 20260918)
            self.assertEqual(d['n_tasks'], 49); self.assertNotIn('0', {a['task_id'] for a in d['arrivals']})  # task 0 (smoke task) excluded
            self.assertEqual(d['arms']['B'], 'agent qwen3-4b-instruct-2507')
            check_pairing_invariants(d, CFG)

    def test_pairing_invariants(self):
        d = generate(CFG, CFG['design_seed'])
        check_pairing_invariants(d, CFG)
        arr = d['arrivals']
        self.assertEqual(len(arr), 98); self.assertEqual(d['n_unpaired'], 0); self.assertEqual(d['n_pairs'], 49)
        self.assertEqual(CFG['task_ids'], [str(i) for i in range(1, 50)])  # task 0 excluded (coordinator's smoke task)
        # each block visits every task once; pass-1 arms in a pair are {A, B}; both arms cover every unit across the two passes
        self.assertEqual(sorted(a['task_id'] for a in arr[:49]), sorted(CFG['task_ids'])); self.assertTrue(all(a['trial'] == 0 for a in arr[:49]))
        self.assertTrue(all(a['trial'] == 1 for a in arr[49:]))
        for k in range(1, 50):
            a1, a2 = arr[2 * k - 2], arr[2 * k - 1]
            self.assertEqual((a1['pair_index'], a2['pair_index']), (k, k)); self.assertEqual({a1['pass1_arm'], a2['pass1_arm']}, {A, B})
            self.assertEqual(a1['pass1_arm'] == A, a1['orientation'] == 1)
        p1 = sum(a['pass1_arm'] == A for a in arr); self.assertEqual(p1, 49)  # exactly one A per pair
        orient = np.array([arr[2 * k]['orientation'] for k in range(49)]); self.assertTrue(0 < orient.mean() < 1)
        # odd block size: exactly pair 25 straddles the blocks (arrivals 49 and 50); block-1 subset = pairs 1-24 (48 distinct tasks)
        pb = analysis.pair_blocks(d)
        self.assertEqual([k for k, v in pb.items() if len(v) > 1], [25]); self.assertEqual([k for k, v in pb.items() if v == {1}], list(range(1, 25)))
        self.assertEqual(len({a['task_id'] for a in arr[:48]}), 48); self.assertGreaterEqual(24, CFG['min_n_pairs'])
        # a different seed changes the design; the same seed reproduces it
        self.assertNotEqual(content_sha256(generate(CFG, 1)), content_sha256(d)); self.assertEqual(content_sha256(generate(CFG, CFG['design_seed'])), content_sha256(d))
        # a broken design is caught
        bad = json.loads(json.dumps(d)); bad['arrivals'][0]['pass1_arm'] = bad['arrivals'][1]['pass1_arm']
        with self.assertRaises(AssertionError):
            check_pairing_invariants(bad, CFG)

    def test_write_refuses_overwrite_and_verifies_hash(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td)
            info = write_design(rd, CFG); self.assertEqual(info['n_pairs'], 49); self.assertEqual(info['n_units'], 98)
            d = load_design(rd); self.assertEqual(d['task_list_sha256'], task_list_sha256(CFG))
            with self.assertRaises(FileExistsError):
                write_design(rd, CFG)
            (rd / 'design.json').write_text(canonical_json(dict(d, seed=1)))
            with self.assertRaises(RuntimeError):
                load_design(rd)
            (rd / 'episodes.csv').write_text('x')
            with self.assertRaises(RuntimeError):
                write_design(rd, CFG, force=True)


class ParserTests(unittest.TestCase):
    @unittest.skipUnless((TAU2_SIMS / 'llama_smoke' / 'results.json').exists(), 'llama_smoke JSON not present')
    def test_llama_smoke_json(self):
        rows = parse_results_file(TAU2_SIMS / 'llama_smoke' / 'results.json', 'A')
        self.assertEqual(len(rows), 1); r = rows[0]
        # independent hand count over the 14 messages: 6 assistant messages carry usage (turn 0 greeting has none)
        self.assertEqual(r['task_id'], '0'); self.assertEqual(r['trial'], 0); self.assertEqual(r['tau2_seed'], 626729)
        self.assertTrue(r['success']); self.assertEqual(r['reward'], 1.0)
        self.assertEqual(r['agent_tokens_completion'], 25 + 25 + 66 + 86 + 105 + 90)
        self.assertEqual(r['agent_tokens_prompt'], 4889 + 4953 + 5296 + 5427 + 5563 + 5714)
        self.assertEqual(r['n_agent_llm_calls'], 6); self.assertEqual(r['n_assistant_tool_calls'], 1); self.assertEqual(r['n_tool_messages'], 1)
        self.assertEqual(r['termination_reason'], 'user_stop'); self.assertFalse(r['max_steps_hit']); self.assertIsNone(r['error'])
        self.assertEqual(r['tokens_source'], 'usage'); self.assertEqual(r['tokens_estimated_calls'], 0)
        self.assertEqual(r['served_models'], 'qwen2.5-7b-instruct'); self.assertAlmostEqual(r['duration'], 60.255, places=2)
        self.assertEqual(r['agent_model'], 'openai/qwen2.5-7b-instruct')

    @unittest.skipUnless((TAU2_SIMS / 'local_smoke' / 'results.json').exists(), 'local_smoke JSON not present')
    def test_local_smoke_json(self):
        r = parse_results_file(TAU2_SIMS / 'local_smoke' / 'results.json', 'B')[0]
        self.assertFalse(r['success']); self.assertTrue(r['max_steps_hit']); self.assertEqual(r['termination_reason'], 'max_steps')
        self.assertEqual(r['n_assistant_tool_calls'], 0); self.assertEqual(r['n_agent_llm_calls'], 20); self.assertEqual(r['n_messages'], 41)
        self.assertEqual(r['arm'], 'B'); self.assertIsNone(r['error'])  # max_steps is an outcome, not an error

    @unittest.skipUnless((TAU2_SIMS / 'smoke_retail_4b' / 'results.json').exists(), 'smoke_retail_4b JSON not present')
    def test_retail_smoke_4b_json(self):
        """Coordinator's Qwen3-4B tool-call verification on one RETAIL task (not an airline design unit): structured tool calls parse."""
        r = parse_results_file(TAU2_SIMS / 'smoke_retail_4b' / 'results.json', 'B')[0]
        self.assertEqual(r['served_models'], 'qwen3-4b-instruct-2507'); self.assertEqual(r['agent_model'], 'openai/qwen3-4b-instruct-2507')
        self.assertEqual(r['user_model'], 'openai/qwen2.5-7b-instruct'); self.assertTrue(r['success']); self.assertEqual(r['n_assistant_tool_calls'], 5)
        self.assertEqual(r['agent_tokens_completion'], 1283); self.assertEqual(r['n_agent_llm_calls'], 17); self.assertEqual(r['tokens_source'], 'usage')

    def test_missing_usage_is_estimated_and_flagged(self):
        sim = dict(task_id='3', trial=1, seed=5, duration=10.0, termination_reason='agent_error', reward_info=dict(reward=0.0),
                   messages=[dict(role='assistant', content='Hi!', turn_idx=0, usage=None), dict(role='user', content='u', turn_idx=1, usage=dict(completion_tokens=3, prompt_tokens=10)),
                             dict(role='assistant', content='x' * 80, turn_idx=2, usage=None, tool_calls=[dict(id='1', name='f', arguments={'a': 1})]),
                             dict(role='assistant', content='ok', turn_idx=3, usage=dict(completion_tokens=7, prompt_tokens=100))])
        r = parse_simulation(sim, tokenize_url=None)
        self.assertEqual(r['tokens_source'], 'usage+estimate'); self.assertEqual(r['tokens_estimated_calls'], 1)
        self.assertEqual(r['agent_tokens_completion'], 7 + (80 + len('\n' + json.dumps({'a': 1}))) // 4); self.assertEqual(r['agent_tokens_prompt'], 100)
        self.assertEqual(r['n_agent_llm_calls'], 2); self.assertEqual(r['n_assistant_tool_calls'], 1); self.assertEqual(r['error'], 'agent_error')
        self.assertFalse(r['success'])
        self.assertEqual(parse_simulation(dict(sim, reward_info=dict(reward=None)))['success'], False)

    def test_attach_design_and_pass(self):
        d = generate(CFG, CFG['design_seed'])
        a1 = d['arrivals'][0]
        rows = [dict(arm=a1['pass1_arm'], task_id=a1['task_id'], trial=a1['trial']), dict(arm=a1['pass2_arm'], task_id=a1['task_id'], trial=a1['trial']), dict(arm='A', task_id='zzz', trial=0)]
        attach_design(rows, d)
        self.assertEqual(rows[0]['pass'], 1); self.assertEqual(rows[1]['pass'], 2); self.assertEqual(rows[0]['arrival_index'], 1); self.assertIsNone(rows[2]['arrival_index'])


class OrchestratorTests(unittest.TestCase):
    def _args(self, rd, arm='both', limit=None):
        return argparse.Namespace(config=None, results_dir=str(rd), arm=arm, dry_run=True, limit_tasks=limit, skip_gguf_hash=True, accept_running_server=False, keep_servers=False)

    def test_dry_run_builds_episodes_and_manifest_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            s = run_tau2_open.run(self._args(rd))
            self.assertEqual(s['status'], 'completed'); self.assertEqual(s['episodes']['n_episodes'], 196)
            rows = analysis.load_episodes(rd / 'episodes.csv')
            self.assertEqual({(r['arm'], r['task_id'], r['trial']) for r in rows}, {(a, t, tr) for a in (A, B) for t in CFG['task_ids'] for tr in range(2)})
            self.assertTrue(all(r['pass'] in (1, 2) and r['arrival_index'] is not None for r in rows))
            self.assertEqual(sum(r['pass'] == 1 for r in rows), 98)
            m1 = json.loads((rd / 'run_manifest.json').read_text())
            self.assertEqual(len(m1['invocations']), 1); inv = m1['invocations'][0]
            self.assertTrue(inv['dry_run']); self.assertIn('tau2_commands', inv); self.assertIn('server_commands', inv); self.assertIn('protocol.md', inv['harness_file_sha256'])
            self.assertEqual(inv['status'], 'completed'); self.assertEqual(inv['preflight']['config_hash'], CFG['_config_hash'])
            self.assertEqual([r['info_mismatches'] for r in inv['arm_runs']], [[], []])  # mock JSON passes the served-model / temperature checks
            # per-invocation raw copies exist next to the canonical copy and are never overwritten
            for arm in (A, B):
                inv_copy = rd / 'raw' / ('tau2_open_arm%s.%s.json' % (arm, inv['invocation_id']))
                self.assertTrue(inv_copy.exists()); self.assertEqual(inv_copy.read_bytes(), (rd / 'raw' / ('tau2_open_arm%s.json' % arm)).read_bytes())
            run_tau2_open.run(self._args(rd))
            m2 = json.loads((rd / 'run_manifest.json').read_text())
            self.assertEqual(len(m2['invocations']), 2); self.assertEqual(m2['invocations'][0], inv)
            self.assertEqual(len(list((rd / 'raw').glob('tau2_open_arm*.*.json'))), 4)  # two invocations x two arms
            self.assertFalse((rd / 'run.lock').exists())
            with self.assertRaises(SystemExit):  # a per-invocation copy is never overwritten
                run_tau2_open.store_raw(rd, A, rd / 'raw' / ('tau2_open_armA.%s.json' % inv['invocation_id']), inv['invocation_id'])

    def test_tau2_command_routes_roles_to_their_servers(self):
        for arm in (A, B):
            cmd = run_tau2_open.tau2_command(CFG, arm)
            aa = json.loads(cmd[cmd.index('--agent-llm-args') + 1]); ua = json.loads(cmd[cmd.index('--user-llm-args') + 1])
            self.assertEqual(aa['api_base'], 'http://127.0.0.1:%d/v1' % CFG['arms'][arm]['port']); self.assertEqual(ua['api_base'], 'http://127.0.0.1:8081/v1')
            self.assertEqual(aa['temperature'], 0.3); self.assertEqual(ua['temperature'], 0.0)  # agent 0.3 in BOTH arms, user simulator 0.0
            self.assertEqual(cmd[cmd.index('--agent-llm') + 1], 'openai/' + CFG['arms'][arm]['alias']); self.assertEqual(cmd[cmd.index('--user-llm') + 1], 'openai/qwen2.5-7b-instruct')
            self.assertEqual(cmd[cmd.index('--max-steps') + 1], '100'); self.assertEqual(cmd[cmd.index('--num-trials') + 1], '2'); self.assertEqual(cmd[cmd.index('--max-concurrency') + 1], '1')
            self.assertEqual(cmd[cmd.index('--hallucination-retries') + 1], '0')
            self.assertEqual(cmd[cmd.index('--task-ids') + 1:cmd.index('--task-ids') + 50], CFG['task_ids']); self.assertEqual(cmd[cmd.index('--task-ids') + 50], '--max-steps')
            self.assertNotIn('0', cmd[cmd.index('--task-ids') + 1:cmd.index('--task-ids') + 50]); self.assertIn('--auto-resume', cmd)
        self.assertEqual(CFG['arms']['B']['alias'], 'qwen3-4b-instruct-2507'); self.assertEqual(CFG['arms']['B']['port'], 8082)
        sc = run_tau2_open.server_command(CFG, 'qwen3-4b-instruct-2507', 8082)
        self.assertIn('--jinja', sc); self.assertEqual(sc[sc.index('-c') + 1], '32768'); self.assertEqual(sc[sc.index('-np') + 1], '1'); self.assertEqual(sc[sc.index('--alias') + 1], 'qwen3-4b-instruct-2507')
        self.assertTrue(sc[sc.index('-m') + 1].endswith('Qwen3-4B-Instruct-2507-Q4_K_M.gguf')); self.assertNotIn('--temp', sc)  # temperature is per request

    def test_config_drift_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_tau2_open.run(self._args(rd, limit=None))
            cfg = json.loads((HERE / 'config.json').read_text()); cfg['max_steps'] = 50
            alt = Path(td) / 'alt.json'; alt.write_text(json.dumps(cfg))
            args = self._args(rd); args.config = str(alt)
            with self.assertRaises(SystemExit) as cm:
                run_tau2_open.run(args)
            self.assertIn('config hash', str(cm.exception))
            self.assertEqual(len(json.loads((rd / 'run_manifest.json').read_text())['invocations']), 1)

    def test_dry_run_refuses_primary_dir_and_lock(self):
        with self.assertRaises(SystemExit):
            run_tau2_open.main(['--dry-run', '--results-dir', str(RESULTS_DIR)])
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'; rd.mkdir()
            (rd / 'run.lock').write_text(json.dumps(dict(pid=os.getpid())))
            with self.assertRaises(SystemExit) as cm:
                run_tau2_open.run(self._args(rd))
            self.assertIn('refusing a concurrent run', str(cm.exception))

    def test_check_results_info(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'r.json'
            mock = run_tau2_open.mock_results(CFG, A, CFG['task_ids'][:2])
            p.write_text(json.dumps(mock))
            self.assertEqual(run_tau2_open.check_results_info(p, CFG, A), [])
            self.assertTrue(run_tau2_open.check_results_info(p, CFG, B))  # arm B expects the Qwen3-4B agent
            # a user-simulator message served by another model is caught (should-fix 1 of the audit)
            bad = json.loads(json.dumps(mock)); um = [m for m in bad['simulations'][0]['messages'] if m['role'] == 'user'][0]; um['raw_data']['model'] = 'qwen3-4b-instruct-2507'
            p.write_text(json.dumps(bad)); mism = run_tau2_open.check_results_info(p, CFG, A)
            self.assertEqual(len(mism), 1); self.assertIn('served user-simulator models', mism[0])
            # a wrong agent temperature in the info block is caught
            bad = json.loads(json.dumps(mock)); bad['info']['agent_info']['llm_args']['temperature'] = 0.0
            p.write_text(json.dumps(bad)); self.assertIn('agent temperature 0.0 != 0.3', run_tau2_open.check_results_info(p, CFG, A))
            # an infrastructure-error record is counted (tau2 re-runs such units on resume)
            bad = json.loads(json.dumps(mock)); bad['simulations'][0]['termination_reason'] = 'infrastructure_error'
            p.write_text(json.dumps(bad)); self.assertEqual(run_tau2_open.count_infra_errors(p), 1)


class AnalysisTests(unittest.TestCase):
    def test_pair_scores_rules(self):
        tiers = analysis.tiers_from_config(CFG)
        self.assertEqual([t.name for t in tiers], ['success', 'agent_tokens_completion', 'n_assistant_tool_calls'])
        self.assertEqual(tiers[1].relative_tolerance, 0.05); self.assertEqual(tiers[2].relative_tolerance, 0.0)
        eA = [dict(success=True, agent_tokens_completion=1000, n_assistant_tool_calls=5, duration=10.0), dict(success=False, agent_tokens_completion=100, n_assistant_tool_calls=1, duration=1.0),
              dict(success=True, agent_tokens_completion=1000, n_assistant_tool_calls=5, duration=1.0)]
        eB = [dict(success=True, agent_tokens_completion=960, n_assistant_tool_calls=4, duration=9.0), dict(success=False, agent_tokens_completion=50, n_assistant_tool_calls=0, duration=1.0),
              dict(success=True, agent_tokens_completion=900, n_assistant_tool_calls=5, duration=1.0)]
        z, tier, dq = analysis.pair_scores(eA, eB, tiers)
        self.assertEqual(z.tolist(), [1, 0, 1]); self.assertEqual(tier.tolist(), [2, -1, 1])  # 4 % token gap is a tie at 5 %, decided by calls; both failed -> tie; 10 % -> tokens
        self.assertEqual(dq.tolist(), [0, 0, 0])
        z2, tier2, _ = analysis.pair_scores(eA, eB, tiers, absorbing=False)
        self.assertEqual(int(z2[1]), 1); self.assertEqual(int(tier2[1]), 1)  # lexicographic: the cheaper failure wins
        z3, tier3, _ = analysis.pair_scores(eA, eB, analysis.tiers_from_config(CFG, order=['agent_tokens_completion', 'success', 'n_assistant_tool_calls']), absorbing=False)
        self.assertEqual(z3.tolist(), [1, 1, 1]); self.assertEqual(tier3.tolist(), [2, 0, 0])  # token-first: pair 1 (a failure) is won by the cheaper B; pair 0 falls through to calls
        t0 = analysis.tiers_from_config(CFG, tolerance=0.0); self.assertEqual(analysis.pair_scores(eA, eB, t0)[1].tolist(), [1, -1, 1])
        td = analysis.tiers_from_config(CFG, tolerance=0.2, order=['success', 'duration', 'agent_tokens_completion'])
        self.assertEqual(td[1].name, 'duration'); self.assertEqual(td[1].relative_tolerance, 0.2); self.assertFalse(td[1].higher_better)

    def test_monitor_matches_direct_recomputation_on_mock(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_tau2_open.run(argparse.Namespace(config=None, results_dir=str(rd), arm='both', dry_run=True, limit_tasks=None, skip_gguf_hash=True, accept_running_server=False, keep_servers=False))
            analysis.main(['--results-dir', str(rd)])
            eps = analysis.load_episodes(rd / 'episodes.csv'); d = load_design(rd)
            with open(rd / 'monitor_pass1.csv', newline='') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 49)
            byk = {(e['arm'], e['task_id'], e['trial']): e for e in eps}
            arr = {a['arrival_index']: a for a in d['arrivals']}
            tiers = [Tier('success'), Tier('agent_tokens_completion', False, relative_tolerance=0.05), Tier('n_assistant_tool_calls', False)]
            z, dq = [], []
            for k in range(1, 50):
                a1, a2 = arr[2 * k - 1], arr[2 * k]
                ea = byk[(A, a1['task_id'], a1['trial'])] if a1['pass1_arm'] == A else byk[(A, a2['task_id'], a2['trial'])]
                eb = byk[(B, a1['task_id'], a1['trial'])] if a1['pass1_arm'] == B else byk[(B, a2['task_id'], a2['trial'])]
                xa = np.array([[float(ea['success']), ea['agent_tokens_completion'], ea['n_assistant_tool_calls']]]); xb = np.array([[float(eb['success']), eb['agent_tokens_completion'], eb['n_assistant_tool_calls']]])
                both = bool(ea['success'] and eb['success']); s, _ = compare(xb, xa, tiers, np.array([[True, both, both]]))
                z.append(int(s[0])); dq.append(int(eb['success']) - int(ea['success']))
            z = np.array(z); dq = np.array(dq); n = np.arange(1, 50)
            le_win = betting_log_e_ternary(np.cumsum(z > 0), np.cumsum(z < 0), n, 0.0); le_gate = betting_log_e_ternary(np.cumsum(dq > 0), np.cumsum(dq < 0), n, -0.03)
            le_harm = betting_log_e_ternary(np.cumsum(z < 0), np.cumsum(z > 0), n, 0.0)
            for i, r in enumerate(rows):
                self.assertEqual(int(r['pair_index']), i + 1); self.assertEqual(int(r['z']), z[i]); self.assertEqual(int(r['success_diff']), dq[i])
                self.assertAlmostEqual(float(r['log_e_win']), le_win[i], places=9); self.assertAlmostEqual(float(r['log_e_gate']), le_gate[i], places=9)
                self.assertAlmostEqual(float(r['log_e_harm']), le_harm[i], places=9)
                if i < 19:
                    self.assertEqual(r['deploy'], 'False')  # min_n = 20 not reached
                self.assertEqual(int(r['block']), 1 if i < 24 else 2)  # pair 25 straddles the blocks and is assigned to block 2
            summ = json.loads((rd / 'summary.json').read_text())
            self.assertTrue(summ['dry_run']); self.assertIn('MOCK DATA', (rd / 'report.md').read_text())
            self.assertEqual(summ['online']['n_pairs'], 49); self.assertEqual(summ['online_block1']['n_pairs'], 24); self.assertEqual(summ['shadow']['n_tasks'], 49)
            self.assertEqual(summ['online']['n_pairs_straddling_blocks'], 1); self.assertEqual(summ['online_block1']['n_pairs_straddling_blocks'], 0)
            self.assertEqual(summ['n_per_arm'], {'A': 98, 'B': 98}); self.assertEqual(summ['arms']['B'], 'agent qwen3-4b-instruct-2507')
            self.assertIn('success_tier_determines_sign', summ['online']); self.assertIn('success_tier_determines_sign', summ['shadow'])
            # H3 flag semantics on hand-made decompositions
            self.assertTrue(analysis.success_determines_sign({'success': -0.2, 'agent_tokens_completion': 0.1, 'n_assistant_tool_calls': 0.05}, -0.05))
            self.assertFalse(analysis.success_determines_sign({'success': 0.05, 'agent_tokens_completion': -0.2, 'n_assistant_tool_calls': 0.0}, -0.15))
            self.assertIsNone(analysis.success_determines_sign({'success': 0.0, 'agent_tokens_completion': 0.0}, 0.0))
            # diagonal pairing = same tau2 trial regardless of episode file order
            names = ['success', 'agent_tokens_completion', 'n_assistant_tool_calls']
            R1 = analysis.runs_by_task(eps, A, names); R2 = analysis.runs_by_task(list(reversed(eps)), A, names)
            self.assertTrue(all(np.array_equal(R1[t], R2[t]) for t in R1))
            with open(rd / 'sensitivity.csv', newline='') as f:
                sens = list(csv.DictReader(f))
            self.assertEqual(len(sens), 20)
            orders = {(r['order'], r['eligibility']) for r in sens}
            for o in (('agent_tokens_completion>success>n_assistant_tool_calls', 'none'), ('success>agent_tokens_completion>n_assistant_tool_calls', 'absorbing'),
                      ('success>agent_tokens_completion>n_assistant_tool_calls', 'none'), ('success>n_assistant_tool_calls>agent_tokens_completion', 'absorbing'), ('success>duration>agent_tokens_completion', 'absorbing')):
                self.assertIn(o, orders)
            self.assertEqual(set(summ['shadow_pairing']), {'all', 'offdiagonal', 'diagonal'})
            rules = {r['rule'] for r in summ['decision_rules']}
            for r in ('success_only', 'pareto_means', 'hierarchical_nb', 'guarded_hierarchical', 'conjunction_all_components', 'hierarchical_nb_betting_cs', 'guarded_anytime', 'success_only_betting_cs'):
                self.assertIn(r, rules)
            self.assertIn('A', summ['components']['failure_accounting']); self.assertIn('max_steps', summ['components']['failure_accounting']['A'])
            # the primary sensitivity row equals the primary analysis
            prim = [r for r in sens if r['order'] == 'success>agent_tokens_completion>n_assistant_tool_calls' and r['eligibility'] == 'absorbing' and float(r['tolerance']) == 0.05][0]
            self.assertAlmostEqual(float(prim['online_nb']), summ['online']['net_benefit'], places=9); self.assertAlmostEqual(float(prim['shadow_nb']), summ['shadow']['net_benefit'], places=9)

    def test_analysis_on_partial_episodes(self):
        """Only arm A present: shadow/online are empty but the analysis still runs (resumable pipeline)."""
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_tau2_open.run(argparse.Namespace(config=None, results_dir=str(rd), arm='A', dry_run=True, limit_tasks=None, skip_gguf_hash=True, accept_running_server=False, keep_servers=False))
            self.assertFalse((rd / 'episodes.csv').exists())
            import build_episodes
            rows = build_episodes.build(rd, CFG); self.assertEqual(len(rows), 98)
            analysis.main(['--results-dir', str(rd)])
            summ = json.loads((rd / 'summary.json').read_text()); self.assertEqual(summ['online']['n_pairs'], 0); self.assertEqual(summ['shadow']['n_tasks'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
