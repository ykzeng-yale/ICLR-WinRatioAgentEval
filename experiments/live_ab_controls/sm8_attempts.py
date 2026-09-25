"""The bounded SM8 attempt loop, with every attempt's temporary tree PRESERVED (test-only).

Root, ``reviews/eb1_eb5_v4_interim_20260925_1315.md``: the v4 receipt recorded red runs of
``tests_sm_entry.SM8AtTheRestart.test_sm8_a_library_changed_before_the_restart_refuses_it``
(the entry exited 0, not 1) without "the per-run stdout, event chain, library hashes or launch
record needed to diagnose" them -- ``tests_eb1_entry.EntryTree.cleanup`` removes the tree.
This module runs ONLY that class (SM8 and its unchanged no-flip control) and keeps what each
run leaves.  It changes no test, no fixture, no shim and no production file:

* ``child --out DIR`` runs ``tests_sm_entry.SM8AtTheRestart`` in this process (verbosity 2,
  the module fixtures of ``tests_eb1_entry`` included) with two OBSERVING wrappers on
  ``tests_eb1_entry.EntryTree``: ``_run_once`` records, immediately before and after the
  entry-point subprocess, the UTC time and the SHA-256 / size / inode / ``mtime_ns`` of every
  entry of the fixture build's ``bin`` (the launcher, both libraries, the alias symlink's
  target, the launcher ``.conf``) and of THE serving manifest; ``cleanup`` copies the whole
  temporary tree (results/ with the trial and program chains, work/ with the shim's llama
  log, host/ with the launch record ``launches.jsonl`` and the scenarios) to
  ``DIR/trees/<tree name>/`` and writes ``DIR/trees/<tree name>.json`` (the digests above,
  the entry's return code and stdout, its pid) BEFORE calling the unmodified cleanup.  Both
  wrappers call the original method; neither changes an argument or a result.
* ``loop --out DIR`` runs ``child`` as a subprocess, one attempt at a time, and records per
  attempt: start/end UTC, the host-gate state just before it (``lab_hostcheck.
  soft_host_check`` -- the read-only observing form of the gate every control then runs for
  real; the loop first waits, ``--gate-wait-s`` at most, for a clean observation and keeps
  every unclean one), the foreign harness/model processes then on the host (``ps``; this
  process tree excluded; nothing is signalled), the load average, the child's stdout, exit
  code, per-test verdicts and the SM8 failure mode (:func:`sm8_mode`: ``exit_0_not_1`` is
  the red under diagnosis, ``host_not_quiescent`` a host-gate refusal).  It stops once
  ``--stop-after-red`` reds of the diagnosed kind are captured or after ``--max-attempts``.
  ``--busy N`` starts N pure-Python busy loops of its OWN before the first attempt and stops
  exactly those pids after the last (the timing probe).  ``--test`` runs another class
  (``tests_sm_entry.SM8ForcedInterleaving``).
* ``timeline TREE`` prints one preserved tree event by event (:func:`timeline`, read only).

What it does NOT perform: it does not decide a cause; the comparison of a red and a green
attempt is made on the preserved files.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (LIVE, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

TEST_NAME = 'tests_sm_entry.SM8AtTheRestart'
SM8_TEST = 'test_sm8_a_library_changed_before_the_restart_refuses_it'
CONTROL_TEST = 'test_control_the_same_crash_without_the_change_restarts'
#: command-line words of processes this loop records as foreign when present (never signals)
FOREIGN_WORDS = ('llama', 'lab_orchestrator', 'eb1c', 'lab_mock_server', 'unittest',
                 'DTR-AgentEvals', 'lab_worker', 'ollama', 'mlx')


def utc() -> str:
    t = time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t)) + ('.%03dZ' % int((t % 1) * 1000))


def file_state(path: Path) -> dict:
    """SHA-256, size, inode and ``mtime_ns`` of ``path`` (a symlink: its target text too)."""
    path = Path(path)
    out: dict = {'path': str(path)}
    try:
        if path.is_symlink():
            out['symlink_to'] = os.readlink(str(path))
        st = path.stat()
        out.update({'bytes': st.st_size, 'inode': st.st_ino, 'mtime_ns': st.st_mtime_ns,
                    'ctime_ns': st.st_ctime_ns,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    except OSError as exc:
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
    return out


def closure_state(tree) -> dict:
    """Every entry of the fixture build's ``bin`` and THE serving manifest of the tree."""
    import lab_serving_manifest as sm
    rows = {p.name: file_state(p) for p in sorted(Path(tree.fixture.bin).iterdir())}
    manifest = sm.artifact_path(tree.freeze)
    return {'utc': utc(), 'bin': rows, 'serving_manifest': file_state(manifest)}


# --------------------------------------------------------------------------- #
# child: one run of the class, trees preserved
# --------------------------------------------------------------------------- #
def child(out: Path, test_name: str = TEST_NAME) -> int:
    import unittest
    import tests_eb1_entry as entry

    trees = out / 'trees'
    trees.mkdir(parents=True, exist_ok=True)
    original_run_once = entry.EntryTree._run_once
    original_cleanup = entry.EntryTree.cleanup

    def _run_once(self, **kw):
        runs = self.__dict__.setdefault('_sm8_runs', [])
        rec = {'before': closure_state(self), 'start_utc': utc()}
        try:
            return original_run_once(self, **kw)
        finally:
            rec['end_utc'] = utc()
            rec['after'] = closure_state(self)
            rec['returncode'] = self.returncode
            rec['stdout'] = self.stdout
            rec['entry_pid'] = getattr(self.proc, 'pid', None)
            runs.append(rec)

    def cleanup(self):
        try:
            dest = trees / self.name
            shutil.copytree(str(self.root), str(dest), symlinks=True)
            record = {'tree': self.name, 'root': str(self.root), 'port': self.port,
                      'flip_target': str(self.fixture.core), 'runs': self.__dict__.get(
                          '_sm8_runs', []), 'preserved_utc': utc()}
            (trees / (self.name + '.json')).write_text(
                json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        except Exception as exc:                       # preservation never hides the test
            sys.stdout.write('sm8_attempts: preserving %s failed: %r\n' % (self.name, exc))
        return original_cleanup(self)

    entry.EntryTree._run_once = _run_once
    entry.EntryTree.cleanup = cleanup
    suite = unittest.defaultTestLoader.loadTestsFromName(test_name)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    sys.stdout.flush()
    return 0 if result.wasSuccessful() else 1


# --------------------------------------------------------------------------- #
# loop: bounded attempts, host state recorded before each
# --------------------------------------------------------------------------- #
def own_tree_pids() -> set:
    """This process, its ancestors' chain up to launchd excluded, and its descendants."""
    res = subprocess.run(['ps', '-Ao', 'pid=,ppid='], capture_output=True, text=True,
                         timeout=30, check=False)
    parent = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            parent[int(parts[0])] = int(parts[1])
    mine = {os.getpid()}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parent.items():
            if ppid in mine and pid not in mine:
                mine.add(pid)
                changed = True
    pid = os.getppid()
    while pid > 1 and pid not in mine:
        mine.add(pid)
        pid = parent.get(pid, 1)
    return mine


def foreign_processes(exclude: set) -> list:
    res = subprocess.run(['ps', '-Ao', 'pid=,ppid=,pgid=,etime=,pcpu=,command='],
                         capture_output=True, text=True, timeout=30, check=False)
    rows = []
    for line in res.stdout.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6 or int(parts[0]) in exclude:
            continue
        if any(w in parts[5] for w in FOREIGN_WORDS):
            rows.append({'pid': int(parts[0]), 'ppid': int(parts[1]), 'pgid': int(parts[2]),
                         'etime': parts[3], 'pcpu': parts[4], 'command': parts[5][:300]})
    return rows


def host_gate_state() -> dict:
    """The read-only observing form of the host gate (``soft_host_check``), this process as
    the only own pid (each control's orchestrator then runs the hard gate itself)."""
    import lab_hostcheck
    scan = lab_hostcheck.soft_host_check({os.getpid()})
    return {'clean': scan.clean, 'findings': [
        {'detector': f.get('detector'), 'summary': f.get('summary') or f.get('command_summary')}
        for f in scan.findings], 'degraded': list(scan.degraded),
        'baseline_active': bool(scan.baseline_active), 'scanned': scan.scanned}


def verdicts(stdout: str) -> dict:
    """Every test's verdict in a verbosity-2 unittest stdout (``name (id) ... ok``)."""
    out = {}
    for ln in stdout.splitlines():
        if not ln.startswith('test') or ' ... ' not in ln:
            continue
        name = ln.split(' ', 1)[0]
        tail = ln.rsplit(' ... ', 1)[1].strip()
        out[name] = tail if tail in ('ok', 'FAIL', 'ERROR') else 'unknown'
    for name in (SM8_TEST, CONTROL_TEST):
        out.setdefault(name, 'not_run')
    return out


def sm8_mode(stdout: str) -> str:
    """[pure] Which failure the SM8 test showed: ``ok``; ``exit_0_not_1`` (the red under
    diagnosis: its traceback ends in ``AssertionError: 0 != 1``); ``host_not_quiescent``
    (the real host gate refused the control before seq 0 -- ``tests_eb1_entry.host_refusal``);
    ``other``.  Read from the SM8 test's own FAIL/ERROR block only."""
    if verdicts(stdout)[SM8_TEST] in ('ok', 'not_run'):
        return verdicts(stdout)[SM8_TEST]
    blocks = stdout.split('=' * 70)
    block = next((b for b in blocks if ('FAIL: %s ' % SM8_TEST) in b
                  or ('ERROR: %s ' % SM8_TEST) in b), '')
    if 'host_not_quiescent' in block:
        return 'host_not_quiescent'
    if 'AssertionError: 0 != 1' in block:
        return 'exit_0_not_1'
    return 'other'


def wait_for_clean_gate(timeout_s: float) -> list:
    """Observe the host gate (read only) until it is clean or ``timeout_s`` passed; every
    observation is returned (the last one is the state the attempt starts in)."""
    seen = []
    deadline = time.monotonic() + float(timeout_s)
    while True:
        state = host_gate_state()
        state['utc'] = utc()
        seen.append(state)
        if state['clean'] or time.monotonic() >= deadline:
            return seen
        time.sleep(5.0)


def start_busy(n: int) -> list:
    procs = []
    for _ in range(int(n)):
        procs.append(subprocess.Popen([sys.executable, '-c', 'while True:\n    pass\n'],
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL))
    return procs


def stop_busy(procs: list) -> list:
    """Stop exactly the busy loops this loop started (by their Popen objects)."""
    out = []
    for p in procs:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
        out.append({'pid': p.pid, 'returncode': p.returncode})
    return out


def loop(out: Path, *, max_attempts: int, stop_after_red: int, busy: int, first: int,
         label: str, gate_wait_s: float = 600.0, test_name: str = TEST_NAME) -> int:
    out.mkdir(parents=True, exist_ok=True)
    busy_procs = start_busy(busy) if busy else []
    ledger = out / 'attempts.jsonl'
    reds = 0
    try:
        if busy_procs:
            time.sleep(2.0)
        for k in range(first, first + int(max_attempts)):
            adir = out / ('attempt_%02d' % k)
            adir.mkdir(parents=True, exist_ok=False)
            exclude = own_tree_pids() | {p.pid for p in busy_procs}
            gate = wait_for_clean_gate(gate_wait_s) if gate_wait_s > 0 else [host_gate_state()]
            rec = {'index': k, 'label': label, 'test': test_name,
                   'busy_loops': [p.pid for p in busy_procs],
                   'host_gate_before': gate[-1], 'host_gate_observations_before': len(gate),
                   'host_gate_unclean_observations_before': [g for g in gate if not g['clean']],
                   'foreign_processes_before': foreign_processes(exclude),
                   'loadavg_before': list(os.getloadavg()), 'start_utc': utc()}
            res = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'child',
                                  '--out', str(adir), '--test', test_name],
                                 cwd=str(HERE), capture_output=True,
                                 text=True, timeout=1800, check=False)
            rec['end_utc'] = utc()
            rec['loadavg_after'] = list(os.getloadavg())
            rec['exit_code'] = res.returncode
            (adir / 'stdout.log').write_text(res.stdout + res.stderr, encoding='utf-8')
            rec['stdout_sha256'] = hashlib.sha256(
                (res.stdout + res.stderr).encode('utf-8')).hexdigest()
            rec['verdicts'] = verdicts(res.stdout + res.stderr)
            rec['sm8_red'] = rec['verdicts'][SM8_TEST] not in ('ok', 'not_run')
            rec['all_green'] = res.returncode == 0 and all(
                v in ('ok', 'not_run') for v in rec['verdicts'].values())
            rec['sm8_mode'] = sm8_mode(res.stdout + res.stderr)
            (adir / 'attempt.json').write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n',
                                               encoding='utf-8')
            with open(ledger, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({k2: rec[k2] for k2 in (
                    'index', 'label', 'test', 'start_utc', 'end_utc', 'exit_code', 'verdicts',
                    'sm8_red', 'sm8_mode', 'all_green')}, sort_keys=True) + '\n')
            print('attempt %d %s exit=%d %s %s' % (k, label, res.returncode, rec['verdicts'],
                                                   rec['sm8_mode']), flush=True)
            # only the red under diagnosis counts towards the stop; a host-gate refusal is
            # recorded like every attempt but is not that red
            reds += int(rec['sm8_mode'] == 'exit_0_not_1')
            if reds >= int(stop_after_red):
                break
    finally:
        if busy_procs:
            (out / ('busy_stopped_%s.json' % label)).write_text(
                json.dumps(stop_busy(busy_procs)) + '\n', encoding='utf-8')
    return 0


# --------------------------------------------------------------------------- #
# timeline: one preserved tree, event by event (read only)
# --------------------------------------------------------------------------- #
_SERVER_FIELDS = ('pid', 'detected_by', 'returncode', 'kind', 'stage', 'findings',
                  'restart_index', 'inflight', 'reason')
_CALL_FIELDS = ('arrival', 'call_index', 'try_index', 'http_status', 'error_class',
                'will_retry', 't_recv_ns', 'client_seconds')


def _jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text('utf-8').splitlines() if line.strip()]


def timeline(tree_dir: Path) -> dict:
    """[read only] The preserved tree ``tree_dir`` (``DIR/trees/<name>``) as one record: the
    trial chain event by event (seq, type, orchestrator ``t_mono_ns`` relative to seq 0, the
    lifecycle / call fields), the workers' spool rows (``t_send_ns`` / ``t_recv_ns`` on the
    same monotonic clock), the shim's launch record and log, the flip target's digest and
    ``mtime_ns`` before and after the entry ran, and three derived facts: how many task
    completions the FIRST launched pid answered (``llm_response`` before the first
    ``server_down``), whether the flip target's bytes differ after the run, and whether it
    was written (``mtime_ns`` changed)."""
    tree_dir = Path(tree_dir)
    record = json.loads((tree_dir.parent / (tree_dir.name + '.json')).read_text('utf-8'))
    events = []
    for seg in sorted((tree_dir / 'results' / 'T4' / 'events').glob('seg_*.jsonl')):
        events.extend(_jsonl(seg))
    t0 = events[0]['t_mono_ns'] if events else 0
    rows = []
    for e in events:
        b = e['body']
        keep = (_SERVER_FIELDS if e['type'].startswith(('server_', 'trial_')) else
                _CALL_FIELDS if e['type'].startswith('llm_') else ())
        rows.append({'seq': e['seq'], 'type': e['type'],
                     'dt_ms': round((e['t_mono_ns'] - t0) / 1e6, 3),
                     **{k: b[k] for k in keep if k in b}})
    spool = []
    for path in sorted((tree_dir / 'work' / 'T4' / 'spools').glob('*.jsonl')):
        for r in _jsonl(path):
            b = r.get('body') or {}
            spool.append({'arrival': r.get('arrival'), 'kind': r.get('kind'),
                          'pid': r.get('pid'), 'dt_ms': round((r['t_mono_ns'] - t0) / 1e6, 3),
                          **{k: (round((b[k] - t0) / 1e6, 3) if k.endswith('_ns') else b[k])
                             for k in ('call_index', 'try_index', 't_send_ns', 't_recv_ns',
                                       'error_class', 'http_status') if k in b}})
    spool.sort(key=lambda r: r['dt_ms'])
    state = tree_dir / 'host' / 'shim_state'
    launches = _jsonl(state / 'launches.jsonl') if (state / 'launches.jsonl').exists() else []
    logs = {p.name: p.read_text('utf-8', 'replace')
            for p in sorted((tree_dir / 'work' / 'T4' / 'logs').glob('llama_*.log'))}
    first_down = next((r['seq'] for r in rows if r['type'] == 'server_down'), None)
    answered = [r for r in rows if r['type'] == 'llm_response'
                and (first_down is None or r['seq'] < first_down)]
    target = Path(record['flip_target']).name
    run = record['runs'][-1] if record['runs'] else {}
    before = (run.get('before') or {}).get('bin', {}).get(target, {})
    after = (run.get('after') or {}).get('bin', {}).get(target, {})
    return {
        'tree': record['tree'], 'returncode': run.get('returncode'),
        'start_utc': run.get('start_utc'), 'end_utc': run.get('end_utc'),
        'events': rows, 'spool': spool, 'launches': [
            {k: r[k] for k in ('start', 'pid', 'scenario_index', 'scenario_sha256', 't_wall')
             if k in r} for r in launches], 'llama_logs': logs,
        'flip_target': target,
        'flip_target_before': {k: before.get(k) for k in ('sha256', 'mtime_ns', 'inode')},
        'flip_target_after': {k: after.get(k) for k in ('sha256', 'mtime_ns', 'inode')},
        'serving_manifest_before': ((run.get('before') or {}).get('serving_manifest')
                                    or {}).get('sha256'),
        'serving_manifest_after': ((run.get('after') or {}).get('serving_manifest')
                                   or {}).get('sha256'),
        'derived': {
            'task_completions_answered_by_first_pid': len(answered),
            'flip_target_bytes_changed': before.get('sha256') != after.get('sha256'),
            'flip_target_written': before.get('mtime_ns') != after.get('mtime_ns'),
            'lifecycle': [r['type'] for r in rows if r['type'].startswith(
                ('server_', 'trial_ended', 'trial_aborted', 'trial_paused'))
                and r['type'] != 'server_health'],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='sm8_attempts')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('child')
    c.add_argument('--out', required=True)
    c.add_argument('--test', default=TEST_NAME)
    tl = sub.add_parser('timeline')
    tl.add_argument('tree')
    lp = sub.add_parser('loop')
    lp.add_argument('--out', required=True)
    lp.add_argument('--max-attempts', type=int, default=20)
    lp.add_argument('--stop-after-red', type=int, default=2)
    lp.add_argument('--busy', type=int, default=0)
    lp.add_argument('--first', type=int, default=1)
    lp.add_argument('--label', default='quiescent')
    lp.add_argument('--gate-wait-s', type=float, default=600.0)
    lp.add_argument('--test', default=TEST_NAME)
    args = ap.parse_args(argv)
    if args.cmd == 'child':
        return child(Path(args.out), args.test)
    if args.cmd == 'timeline':
        print(json.dumps(timeline(Path(args.tree)), indent=1, sort_keys=True))
        return 0
    return loop(Path(args.out), max_attempts=args.max_attempts,
                stop_after_red=args.stop_after_red, busy=args.busy, first=args.first,
                label=args.label, gate_wait_s=args.gate_wait_s, test_name=args.test)


if __name__ == '__main__':
    sys.exit(main())
