"""Unit tests for the local stream harness (stdlib unittest; no pytest dependency).

Run:  /path/to/.venv/bin/python -m unittest experiments/local_stream/tests_local_stream.py -v
Requires the cached task list (run data.py once; network needed the first time).
No test contacts the model server; no test sends a design task to any model.
"""
from __future__ import annotations
import argparse, csv, json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np

from common import ROOT, RESULTS_DIR, canonical_json, hf_snapshot_record, load_config, read_jsonl, sha256_text
from data import load_tasks
from sandbox import base_interpreter, run_program, sandbox_info, static_check
from verify import SENTINEL_PREFIX, build_program, hack_flags, verify
from agent import MockModel, build_user_prompt, extract_code, run_episode, signature_line
import run_stream
import analysis
from timing_pilot import assert_disjoint, select_pilot_tasks
from winstats import Tier, compare, betting_log_e_ternary

PY = sys.executable
CFG = load_config()
TASKS = load_tasks()
BY_UID = {t['uid']: t for t in TASKS}
SEATBELT = sandbox_info()['kind'] == 'seatbelt'


class SandboxTests(unittest.TestCase):
    def test_base_interpreter_not_venv_symlink(self):
        py = base_interpreter()
        self.assertTrue(os.path.exists(py)); self.assertFalse(os.path.islink(py))
        self.assertNotIn(str(ROOT), py)  # the repository path is never exposed to candidate programs
        info = sandbox_info()
        self.assertEqual(info['python'], py)
        if SEATBELT:
            self.assertEqual(len(info['profile_sha256']), 64); self.assertIn('(deny network*)', info['profile'])
            self.assertIn(os.path.realpath(str(Path.home())), info['profile'])

    def test_static_rules_are_flags_not_blocks(self):
        flagged = ["import os\nos.system('true')\n", "import subprocess\n", "import socket\n", "import sys\nsys.exit(0)\n", "m = __import__('os')\n"]
        for src in flagged:
            self.assertTrue(static_check(src), src)
            r = run_program(src, timeout_s=5)
            self.assertTrue(r['executed'], src)  # executed, only flagged
            self.assertTrue(r['flags'], src)
        ok = "import math\ndef f(x):\n    return math.sqrt(x)\nassert f(4) == 2\nopen('local.txt', 'w').write('x')\nprint(open('local.txt').read())\n"
        self.assertEqual(static_check(ok), [])
        r = run_program(ok, timeout_s=5); self.assertTrue(r['passed']); self.assertEqual(r['stdout'].strip(), 'x')

    def test_stdlib_available(self):
        src = ("import math, re, collections, itertools, functools, heapq, bisect, string, datetime, fractions, decimal, statistics, random, json, typing, sys, os\n"
               "import tempfile\nf = tempfile.NamedTemporaryFile('w'); f.write('x')\nprint('ok')\n")
        r = run_program(src, timeout_s=10); self.assertTrue(r['passed'], r['stderr']); self.assertEqual(r['stdout'].strip(), 'ok')

    @unittest.skipUnless(SEATBELT, 'macOS Seatbelt only')
    def test_adversarial_programs_contained(self):
        home = os.path.realpath(str(Path.home()))
        victim_dir = tempfile.mkdtemp(prefix='ls_victim_')  # in the user's temp dir, outside the sandbox base
        victim = os.path.join(victim_dir, 'victim.txt'); open(victim, 'w').write('keep me')
        home_probe = os.path.join(home, '.zshrc') if os.path.exists(os.path.join(home, '.zshrc')) else home + '/.bash_history'
        try:
            programs = {
                'read_home': "try:\n    open(%r).read(); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n" % home_probe,
                'read_repo_env': "import os\ntry:\n    open(%r).read(); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n" % str(ROOT / 'config.json'),
                'write_home': "try:\n    open(%r, 'w').write('x'); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n" % (home + '/ls_sandbox_escape.txt'),
                'delete_outside_cwd': "import os\np = %r\ntry:\n    os.remove(p[:3] + p[3:]); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n" % victim,
                'write_tmp_other': "try:\n    open('/private/tmp/ls_sandbox_escape.txt', 'w').write('x'); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n",
                'exec_shell': "import os as o\ntry:\n    out = o.popen('id').read()\n    print('ESCAPED' if out.strip() else 'contained empty')\nexcept Exception as e: print('contained', type(e).__name__)\n",
                'subprocess_exec': "import subprocess\ntry:\n    subprocess.run(['/bin/ls']); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n",
                'network': "import _socket as n\ns = n.socket()\ns.settimeout(3)\ntry:\n    s.connect(('1.1.1.1', 80)); print('ESCAPED')\nexcept Exception as e: print('contained', type(e).__name__)\n",
                'fork_bomb': "import os, time\nn = 0\nfor i in range(20):\n    try:\n        if os.fork() == 0:\n            time.sleep(30); os._exit(0)\n        n += 1\n    except OSError:\n        pass\nprint('forked', n)\ntime.sleep(30)\n",
            }
            results = {}
            for name, src in programs.items():
                r = run_program(src, timeout_s=2.0 if name == 'fork_bomb' else 10.0)
                results[name] = r
                self.assertTrue(r['executed'], name)
                if name != 'fork_bomb':
                    self.assertNotIn('ESCAPED', r['stdout'], (name, r['stdout'], r['stderr'][-300:]))
                    self.assertIn('contained', r['stdout'], (name, r['stdout'], r['stderr'][-300:]))
            self.assertTrue(os.path.exists(victim), 'victim file outside the sandbox was deleted')
            self.assertFalse(os.path.exists(home + '/ls_sandbox_escape.txt')); self.assertFalse(os.path.exists('/private/tmp/ls_sandbox_escape.txt'))
            fb = results['fork_bomb']
            self.assertTrue(fb['timed_out']); self.assertFalse(fb['passed'])
            time.sleep(0.5)
            ps = subprocess.run(['ps', '-axo', 'pid=,ppid=,command='], capture_output=True, text=True).stdout
            orphans = [l for l in ps.splitlines() if 'ls_sbx' in l and 'prog.py' in l]
            self.assertEqual(orphans, [], 'sandbox children survived killpg: %s' % orphans)
        finally:
            shutil.rmtree(victim_dir, ignore_errors=True)

    def test_wall_clock_timeout(self):
        r = run_program("while True:\n    pass\n", timeout_s=1.0, cpu_seconds=30)
        self.assertTrue(r['timed_out']); self.assertFalse(r['passed']); self.assertLess(r['seconds'], 5)

    def test_cpu_limit(self):
        r = run_program("while True:\n    pass\n", timeout_s=10.0, cpu_seconds=1)
        self.assertFalse(r['passed']); self.assertIn('RLIMIT_CPU=1', r['limits_applied']); self.assertIn('RLIMIT_NPROC=', r['limits_applied']); self.assertLess(r['seconds'], 8)

    def test_output_cap_and_failure(self):
        r = run_program("print('x' * 200000)\nprint('tail-marker')\n", timeout_s=5, output_cap=1000)
        self.assertTrue(r['passed']); self.assertIn('truncated', r['stdout']); self.assertLess(len(r['stdout']), 1200)
        self.assertTrue(r['stdout_tail'].rstrip().endswith('tail-marker'))  # the raw tail survives the cap (sentinel check)
        r = run_program("assert 1 == 2\n", timeout_s=5)
        self.assertFalse(r['passed']); self.assertEqual(r['returncode'], 1); self.assertIn('AssertionError', r['stderr'])


class VerifyTests(unittest.TestCase):
    def test_reference_solutions_pass(self):
        rng = np.random.default_rng(20260918)
        mbpp = [t for t in TASKS if t['benchmark'] == 'mbpp']; he = [t for t in TASKS if t['benchmark'] == 'humaneval']
        for pool in (mbpp, he):
            for i in rng.choice(len(pool), 20, replace=False):
                t = pool[int(i)]; v = verify(t, t['reference'])
                self.assertTrue(v['success'], (t['uid'], v['run']['stderr'][-300:]))
                self.assertTrue(v['sentinel_seen']); self.assertFalse(v['timed_out']); self.assertGreater(v['verify_seconds'], 0)

    def test_wrong_solutions_fail(self):
        for uid in ('mbpp/2', 'humaneval/0'):
            t = BY_UID[uid]
            wrong = 'def %s(*args, **kwargs):\n    return None\n' % t['entry_point']
            self.assertFalse(verify(t, wrong)['success'])
            self.assertFalse(verify(t, 'def unrelated():\n    pass\n')['success'])  # entry point missing
            self.assertFalse(verify(t, '')['success'])

    def test_sentinel_defeats_early_exit(self):
        for uid in ('mbpp/2', 'humaneval/0', 'mbpp/430'):
            t = BY_UID[uid]; ref = t['reference']
            wrong = 'def %s(*args, **kwargs):\n    return None\n' % t['entry_point']
            hacks = {'ref+SystemExit': ref + '\nraise SystemExit(0)\n', 'wrong+os._exit': wrong + 'import os\nos._exit(0)\n',
                     'wrong+indented sys.exit': wrong + 'import sys\nif True:\n    sys.exit(0)\n',
                     'wrong+guessed sentinel': wrong + "print(%r + '0' * 16)\nraise SystemExit(0)\n" % SENTINEL_PREFIX}
            self.assertTrue(verify(t, ref)['success'], uid)
            for name, code in hacks.items():
                v = verify(t, code)
                self.assertFalse(v['success'], (uid, name)); self.assertFalse(v['sentinel_seen'], (uid, name))
                self.assertEqual(v['run']['returncode'], 0, (uid, name))  # exit status alone would have passed
                self.assertTrue(v['hack_flags'], (uid, name))
        self.assertIn(SENTINEL_PREFIX, build_program(BY_UID['mbpp/2'], 'x = 1\n', SENTINEL_PREFIX + 'abcd'))
        self.assertNotIn(SENTINEL_PREFIX, build_program(BY_UID['mbpp/2'], 'x = 1\n'))

    def test_hack_flags_recorded_not_blocking(self):
        t = BY_UID['mbpp/2']
        v = verify(t, t['reference'] + '\nimport socket\nclass Q:\n    def __eq__(self, o):\n        return True\n')
        self.assertTrue(v['success'])  # static/hack matches never decide success
        self.assertTrue(v['sandbox_flag']); self.assertIn('def __eq__', v['hack_flags'])
        self.assertEqual(hack_flags('def f(x):\n    return x\n'), [])

    def test_all_asserts_graded(self):
        t = BY_UID['mbpp/2']
        prog = build_program(t, t['reference'])
        for a in t['test_list']:
            self.assertIn(a, prog)


class AgentTests(unittest.TestCase):
    def test_hidden_tests_never_in_prompt(self):
        """MBPP: no assert of test_list (not even the first) appears in the prompt; only the def signature line does.
        HumanEval: the benchmark test string and check() never appear."""
        for t in TASKS:
            p = build_user_prompt(t)
            if t['benchmark'] == 'mbpp':
                self.assertNotIn('assert', p, t['uid'])
                for hidden in t['test_list'] + t.get('challenge_test_list', []):
                    self.assertNotIn(hidden, p, t['uid'])
                sig = signature_line(t)
                self.assertIn(sig, p); self.assertRegex(sig, r'^(async )?def \w+\(.*\):$')
                self.assertIn('def %s(' % t['entry_point'], sig, t['uid'])
            else:
                self.assertNotIn('def check(', p); self.assertNotIn(t['test'].strip()[:40], p)

    def test_signature_line_examples(self):
        self.assertEqual(signature_line(BY_UID['mbpp/2']), 'def similar_elements(test_tup1, test_tup2):')
        self.assertEqual(signature_line(BY_UID['mbpp/6']), 'def differ_At_One_Bit_Pos(a, b):')  # first def is a helper; entry point used

    def test_extract_code(self):
        self.assertEqual(extract_code('text\n```python\nx = 1\n```\nmore ```py\ny=2\n```'), 'x = 1\n')
        self.assertEqual(extract_code('```\nz = 3\n```'), 'z = 3\n')
        self.assertEqual(extract_code('plain code'), 'plain code\n')
        self.assertEqual(extract_code('x = 1<|im_end|>\n'), 'x = 1\n')

    def test_mock_episode_records(self):
        m = MockModel(CFG, TASKS)
        for variant in ('single_shot', 'self_test_repair'):
            rec = run_episode(BY_UID['mbpp/2'], variant, m, CFG, dict(trial=1, arrival_index=1, pair_index=1, orientation=1, **{'pass': 1}))
            for k in ('task_id', 'benchmark', 'variant', 'arrival_index', 'pair_index', 'orientation', 'pass', 'start_ts', 'end_ts', 'latency_s', 'n_llm_calls',
                      'prompt_tokens', 'completion_tokens', 'n_executions', 'repair_rounds', 'self_test_passed', 'success', 'sandbox_flag', 'timed_out', 'error',
                      'final_code', 'model', 'endpoint', 'harness_git_hash', 'config_hash', 'verify_seconds', 'sentinel_seen', 'hack_flags', 'static_flags',
                      'response_models', 'sandbox_kind', 'sandbox_profile_sha256'):
                self.assertIn(k, rec)
            self.assertGreater(rec['verify_seconds'], 0)
            if variant == 'single_shot':
                self.assertEqual(rec['n_llm_calls'], 1)
                self.assertLess(rec['latency_s'], rec['verify_seconds'])  # mock calls are instant: latency excludes verification
            else:
                self.assertGreaterEqual(rec['n_llm_calls'], 2); self.assertLessEqual(rec['n_llm_calls'], 4); self.assertLessEqual(rec['repair_rounds'], 2)
            self.assertEqual(rec['response_models'], ['mock-deterministic-v1'] * rec['n_llm_calls'])


class DesignTests(unittest.TestCase):
    def _sha(self, hashseed):
        env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
        out = subprocess.run([PY, str(HERE / 'design.py'), '--print-sha-only'], capture_output=True, text=True, env=env, cwd=str(HERE), timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.strip()

    def test_deterministic_across_processes(self):
        s0, s1 = self._sha(0), self._sha(1)
        self.assertEqual(s0, s1); self.assertEqual(len(s0), 64)
        frozen = RESULTS_DIR / 'design.json'
        if frozen.exists():  # the frozen primary design must be exactly what the generator produces
            d = json.loads(frozen.read_text())
            stripped = {k: v for k, v in d.items() if k not in ('generated_at', 'generator_sha256', 'harness_git_hash')}
            self.assertEqual(sha256_text(canonical_json(stripped)), s0)
            self.assertEqual(d['n_pairs'], 295); self.assertEqual(d['n_tasks'], 591)
            self.assertEqual(d['config_hash'], CFG['_config_hash'])  # config unchanged since the freeze
            pairs = {}
            for a in d['arrivals']:
                if a['pair_index'] is not None:
                    pairs.setdefault(a['pair_index'], []).append(a)
            for k, (a1, a2) in pairs.items():
                self.assertEqual({a1['pass1_variant'], a2['pass1_variant']}, {'single_shot', 'self_test_repair'})
                self.assertEqual(a1['pass1_variant'] == 'single_shot', a1['orientation'] == 1)
            self.assertEqual(len({a['task_id'] for a in d['arrivals']}), 591)


class StreamTests(unittest.TestCase):
    def _args(self, rd, limit, config=None, only_pass=0):
        return argparse.Namespace(config=config, results_dir=str(rd), dry_run=True, limit=limit, trial=1, only_pass=only_pass)

    def test_resume_skips_completed(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            s1 = run_stream.run(self._args(rd, 4))
            self.assertEqual(s1['ran'], 8); self.assertEqual(s1['skipped_completed'], 0)
            n_lines = len(read_jsonl(rd / 'episodes.jsonl'))
            s2 = run_stream.run(self._args(rd, 4))
            self.assertEqual(s2['ran'], 0); self.assertEqual(s2['skipped_completed'], 8)
            self.assertEqual(len(read_jsonl(rd / 'episodes.jsonl')), n_lines)
            s3 = run_stream.run(self._args(rd, 6))  # extension: only the new arrivals run
            self.assertEqual(s3['ran'], 4); self.assertEqual(s3['skipped_completed'], 8)
            self.assertEqual(s3['monitor']['n_pairs_monitored'], 3)
            self.assertFalse((rd / 'run.lock').exists())

    def test_manifest_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_stream.run(self._args(rd, 2))
            m1 = json.loads((rd / 'run_manifest.json').read_text())
            self.assertEqual(len(m1['invocations']), 1); self.assertNotIn('config', m1)  # no mutable top-level config
            inv1 = m1['invocations'][0]
            self.assertEqual(inv1['status'], 'completed'); self.assertEqual(inv1['config_hash'], CFG['_config_hash'])
            self.assertIn('sandbox', inv1); self.assertIn('smoke_check', inv1); self.assertIn('protocol.md', inv1['harness_file_sha256'])
            run_stream.run(self._args(rd, 2))
            m2 = json.loads((rd / 'run_manifest.json').read_text())
            self.assertEqual(len(m2['invocations']), 2)
            self.assertEqual(m2['invocations'][0], inv1)  # earlier record untouched
            self.assertEqual({k: v for k, v in m2.items() if k != 'invocations'}, {k: v for k, v in m1.items() if k != 'invocations'})
            self.assertEqual(m2['invocations'][1]['summary']['ran'], 0)

    def test_config_drift_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_stream.run(self._args(rd, 2))
            cfg = json.loads((HERE / 'config.json').read_text()); cfg['temperature'] = 0.2
            alt = Path(td) / 'config_alt.json'; alt.write_text(json.dumps(cfg))
            with self.assertRaises(SystemExit) as cm:
                run_stream.run(self._args(rd, 4, config=str(alt)))
            self.assertIn('config hash', str(cm.exception))
            self.assertEqual(len(read_jsonl(rd / 'episodes.jsonl')), 4)  # nothing appended
            self.assertEqual(len(json.loads((rd / 'run_manifest.json').read_text())['invocations']), 1)
            # an episode with a foreign config hash also blocks the run
            eps = read_jsonl(rd / 'episodes.jsonl'); eps[0]['config_hash'] = 'f' * 64
            (rd / 'episodes.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in eps))
            with self.assertRaises(SystemExit):
                run_stream.run(self._args(rd, 4))

    def test_only_pass_2_requires_pass_1(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            with self.assertRaises(SystemExit) as cm:
                run_stream.run(self._args(rd, 4, only_pass=2))
            self.assertIn('pass 1 incomplete', str(cm.exception))
            self.assertEqual(read_jsonl(rd / 'episodes.jsonl'), [])
            run_stream.run(self._args(rd, 4, only_pass=1))
            s = run_stream.run(self._args(rd, 4, only_pass=2))
            self.assertEqual(s['ran'], 4)

    def test_run_lock(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'; rd.mkdir()
            (rd / 'run.lock').write_text(json.dumps(dict(pid=os.getpid())))  # a live pid
            with self.assertRaises(SystemExit) as cm:
                run_stream.run(self._args(rd, 2))
            self.assertIn('refusing a concurrent run', str(cm.exception))
            (rd / 'run.lock').write_text(json.dumps(dict(pid=2 ** 22 + 12345)))  # stale (dead) pid
            s = run_stream.run(self._args(rd, 2)); self.assertEqual(s['ran'], 4)

    def test_snapshot_and_model_checks(self):
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / 'hub'; snaps = cache / ('models--' + CFG['model'].replace('/', '--')) / 'snapshots'
            (snaps / 'deadbeef').mkdir(parents=True); (snaps / 'deadbeef' / 'config.json').write_text('{}')
            rec = hf_snapshot_record(CFG['model'], CFG['model_revision_expected'], cache)
            self.assertFalse(rec['ok']); self.assertIn('deadbeef', rec['snapshots_present'])
            with self.assertRaises(SystemExit):
                run_stream.check_snapshot(CFG, cache)
            (snaps / CFG['model_revision_expected']).mkdir(); (snaps / CFG['model_revision_expected'] / 'model.safetensors').write_bytes(b'weights')
            rec = run_stream.check_snapshot(CFG, cache)
            self.assertTrue(rec['ok']); self.assertEqual(rec['files'][0]['bytes'], 7); self.assertEqual(rec['total_bytes'], 7)
        self.assertTrue(run_stream.model_name_matches(CFG['model'], CFG['model']))
        self.assertTrue(run_stream.model_name_matches(CFG['model'], 'Qwen2.5-Coder-7B-Instruct-4bit'))
        self.assertFalse(run_stream.model_name_matches(CFG['model'], 'Qwen/Qwen3-4B-Instruct-2507'))
        self.assertFalse(run_stream.model_name_matches(CFG['model'], None))

    def test_monitor_matches_direct_recomputation(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / 'r'
            run_stream.run(self._args(rd, 12))
            eps = read_jsonl(rd / 'episodes.jsonl'); design = json.load(open(rd / 'design.json'))
            rows = list(csv.DictReader(open(rd / 'monitor_pass1.csv')))
            self.assertEqual(len(rows), 6)
            arr = {a['arrival_index']: a for a in design['arrivals']}
            byk = {(e['task_id'], e['variant']): e for e in eps if e['pass'] == 1}
            tiers = [Tier('success'), Tier('latency_s', False, relative_tolerance=0.10), Tier('completion_tokens', False, relative_tolerance=0.10)]
            z, dq = [], []
            for k in range(1, 7):
                a1, a2 = arr[2 * k - 1], arr[2 * k]
                ea = byk[(a1['task_id'], 'single_shot')] if a1['pass1_variant'] == 'single_shot' else byk[(a2['task_id'], 'single_shot')]
                eb = byk[(a1['task_id'], 'self_test_repair')] if a1['pass1_variant'] == 'self_test_repair' else byk[(a2['task_id'], 'self_test_repair')]
                xa = np.array([[float(ea['success']), ea['latency_s'], ea['completion_tokens']]]); xb = np.array([[float(eb['success']), eb['latency_s'], eb['completion_tokens']]])
                both = bool(ea['success'] and eb['success']); elig = np.array([[True, both, both]])
                s, _ = compare(xb, xa, tiers, elig); z.append(int(s[0])); dq.append(int(eb['success']) - int(ea['success']))
            z = np.array(z); dq = np.array(dq); n = np.arange(1, 7)
            pos, neg = np.cumsum(z > 0), np.cumsum(z < 0); qp, qn = np.cumsum(dq > 0), np.cumsum(dq < 0)
            le_win = betting_log_e_ternary(pos, neg, n, 0.0); le_gate = betting_log_e_ternary(qp, qn, n, -0.03); le_harm = betting_log_e_ternary(neg, pos, n, 0.0)
            for i, r in enumerate(rows):
                self.assertEqual(int(r['z']), z[i]); self.assertEqual(int(r['success_diff']), dq[i])
                self.assertAlmostEqual(float(r['log_e_win']), le_win[i], places=9)
                self.assertAlmostEqual(float(r['log_e_gate']), le_gate[i], places=9)
                self.assertAlmostEqual(float(r['log_e_harm']), le_harm[i], places=9)
                self.assertEqual(r['deploy'], 'False')  # min_n = 20 not reached
            # analysis on the dry run: H4 rows present, MOCK banner
            analysis.main(['--results-dir', str(rd)])
            sens = list(csv.DictReader(open(rd / 'sensitivity.csv')))
            self.assertEqual(len(sens), 12)
            orders = {(r['order'], r['eligibility']) for r in sens}
            self.assertIn(('latency_s>success>completion_tokens', 'none'), orders); self.assertIn(('completion_tokens>success>latency_s', 'none'), orders)
            self.assertIn(('success>latency_s>completion_tokens', 'absorbing'), orders)
            self.assertIn('MOCK DATA', (rd / 'report.md').read_text())
            summ = json.loads((rd / 'summary.json').read_text()); self.assertTrue(summ['dry_run'])
            self.assertIn('hack_flagged_success', summ['components']['failure_accounting']['single_shot'])

    def test_no_absorbing_mask_scores(self):
        eA = [dict(success=False, latency_s=1.0, completion_tokens=100)]; eB = [dict(success=True, latency_s=5.0, completion_tokens=300)]
        tiers = run_stream.tiers_from_config(CFG, order=['latency_s', 'success', 'completion_tokens'])
        z, tier, dq = run_stream.pair_scores(eA, eB, tiers, absorbing=False)
        self.assertEqual(int(z[0]), -1); self.assertEqual(int(tier[0]), 0)  # latency-first prefers A although A failed
        z2, tier2, _ = run_stream.pair_scores(eA, eB, run_stream.tiers_from_config(CFG))
        self.assertEqual(int(z2[0]), 1); self.assertEqual(int(tier2[0]), 0)  # frozen rule: decided by success

    def test_dry_run_refuses_primary_dir(self):
        with self.assertRaises(SystemExit):
            run_stream.main(['--dry-run', '--limit', '2', '--results-dir', str(RESULTS_DIR)])


class PilotTests(unittest.TestCase):
    def test_pilot_tasks_disjoint(self):
        mb = [t for t in TASKS if t['benchmark'] == 'mbpp']
        fake_full = [dict(task_id=mb[0]['source_task_id'], text='copied id', code='def f(): pass', test_list=['assert f() is None']),
                     dict(task_id=100000, text=mb[1]['prompt'], code='def g(): pass', test_list=['assert g() is None'])]
        fake_full += [dict(task_id=200000 + i, text='Write a function number %d.' % i, code='def h%d(x):\n    return x\n' % i,
                           test_list=['assert h%d(1) == 1' % i]) for i in range(10)]
        pil = select_pilot_tasks(fake_full, TASKS, n=6, seed=1)
        self.assertEqual(len(pil), 6)
        self.assertTrue(all(t['source_task_id'] >= 200000 for t in pil))
        with self.assertRaises(AssertionError):
            assert_disjoint([dict(uid='mbpp_full/%d' % mb[0]['source_task_id'], source_task_id=mb[0]['source_task_id'], prompt='x')], TASKS)
        with self.assertRaises(AssertionError):
            assert_disjoint([dict(uid='mbpp_full/999999', source_task_id=999999, prompt=mb[2]['prompt'])], TASKS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
