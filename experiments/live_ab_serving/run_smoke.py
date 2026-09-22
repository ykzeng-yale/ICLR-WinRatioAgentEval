"""The bounded instrument smoke root authorized on 2026-09-22 06:16.

INSTRUMENT ONLY. Not a trial episode, roster or reference sweep, calibration,
rehearsal grid or deployment decision. No task data, no verifier, no generated
program is executed, no success is graded, no alpha is spent.

Every cap is enforced here rather than intended:

  * ONE server start. No retry, no restart.
  * TWO generation requests, dispatched from one supervisor on two threads with
    separate connections and a single barrier. Root, 07:00: "actual server
    overlap must be OBSERVED, not guaranteed by dispatch." The barrier makes
    overlap likely; only the lifecycle records can show whether it happened.
  * 2,048 generated tokens TOTAL, 600 s wall, 120 s per request.
  * Early EOS, failure, timeout and absence of overlap are RESULTS. They are
    preserved and reported. Nothing is retried to obtain a nicer answer.

The acquisition is finished and closed before anything analyses it: the server is
stopped, its seal is written by the static destructor, and only then is the log
read. Root: "Do not analyze a file still being written."
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402
import lab_lifecycle                                           # noqa: E402

SC = Path('/private/tmp/claude-501/-Users-yukangzengcmac-ICLR-WinRatioAgentEvals'
          '/35a3ef1c-e430-45ac-b78e-94ba942c34a1/scratchpad')
BIN = SC / 'llama_lifecycle_iso' / 'build' / 'bin' / 'llama-server'

WALL_CAP_S = 600.0
REQUEST_CAP_S = 120.0
TOKEN_CAP = 2048


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def main() -> int:
    manifest_path, log_path, token = (
        Path(l) if i < 2 else l
        for i, l in enumerate(Path('/tmp/lab_smoke_manifest.txt')
                              .read_text().strip().splitlines()))
    m = json.loads(Path(manifest_path).read_text('utf-8'))
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)

    model = None
    import glob
    for p in glob.glob(str(Path.home() / '.cache/huggingface/**' / m['model']['file']),
                       recursive=True):
        model = Path(p)
        break
    if model is None:
        print('REFUSE: pinned weight not found locally', file=sys.stderr)
        return 2

    out: dict = {
        'schema': 'live_ab/smoke_receipt-v1',
        'convention': 'model-dependent',
        'manifest': manifest_path.name,
        'run_token': token,
        'started_utc': _now(),
        'caps': m['caps'],
        'planned_requests': 2,
        'submitted_requests': 0,
        'loaded_a_model': True,
        'is_a_trial_episode': False,
    }
    env = dict(os.environ, LIVE_AB_LIFECYCLE_LOG=str(log), LIVE_AB_RUN_TOKEN=token)
    args = [str(BIN), '-m', str(model)] + m['server_args']
    t_wall0 = time.monotonic()

    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    out['server_pid'] = proc.pid
    out['server_started_utc'] = _now()

    import requests
    base = 'http://127.0.0.1:%d' % m['port']
    ready = False
    while time.monotonic() - t_wall0 < WALL_CAP_S:
        if proc.poll() is not None:
            break
        try:
            if requests.get(base + '/health', timeout=2).status_code == 200:
                ready = True
                break
        except Exception:                                      # noqa: BLE001
            time.sleep(1.0)
    out['server_ready'] = ready
    out['seconds_to_ready'] = round(time.monotonic() - t_wall0, 2)

    results: list = []
    if ready:
        barrier = threading.Barrier(2)

        def one(idx: int) -> None:
            body = {'model': 'coder', 'messages': [
                {'role': 'user', 'content': m['request']['prompt']}],
                'max_tokens': m['request']['max_tokens'],
                'temperature': m['request']['temperature'],
                'seed': m['request']['seed'], 'stream': False, 'n': 1}
            rec: dict = {'index': idx}
            try:
                barrier.wait(timeout=30)
            except Exception as exc:                           # noqa: BLE001
                rec['barrier_error'] = str(exc)
            rec['t_send_monotonic'] = time.monotonic()
            rec['t_send_utc'] = _now()
            try:
                r = requests.post(base + '/v1/chat/completions', json=body,
                                  timeout=REQUEST_CAP_S)
                rec['t_ack_monotonic'] = time.monotonic()
                rec['status'] = r.status_code
                d = r.json()
                rec['usage'] = d.get('usage')
                rec['finish_reason'] = (d.get('choices') or [{}])[0].get('finish_reason')
                rec['content_chars'] = len(
                    ((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '')
            except Exception as exc:                           # noqa: BLE001
                rec['t_ack_monotonic'] = time.monotonic()
                rec['error'] = '%s: %s' % (type(exc).__name__, exc)
            rec['elapsed_s'] = rec['t_ack_monotonic'] - rec['t_send_monotonic']
            results.append(rec)

        threads = [threading.Thread(target=one, args=(i,)) for i in range(2)]
        out['submitted_requests'] = 2
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=REQUEST_CAP_S + 30)
    out['requests'] = sorted(results, key=lambda r: r['index'])
    out['generated_tokens_total'] = sum(
        (r.get('usage') or {}).get('completion_tokens', 0) for r in results)
    out['token_cap_respected'] = out['generated_tokens_total'] <= TOKEN_CAP

    # --- stop OUR OWN server, then let the seal be written -------------------
    out['server_stop_utc'] = _now()
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception as exc:                                   # noqa: BLE001
        out['stop_error'] = '%s: %s' % (type(exc).__name__, exc)
    try:
        proc.wait(timeout=60)
    except Exception:                                          # noqa: BLE001
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            out['forced_stop'] = True
        except Exception:                                      # noqa: BLE001
            pass
    out['server_exit_code'] = proc.returncode
    out['wall_seconds_total'] = round(time.monotonic() - t_wall0, 2)
    out['wall_cap_respected'] = out['wall_seconds_total'] <= WALL_CAP_S

    # --- ONLY NOW read the closed acquisition -------------------------------
    expected = {'host_id': m['host_id'], 'boot_id': m['boot_id'],
                'instance_id': token, 'binary_sha256': m['launcher']['sha256'],
                'patch_sha256': m['patch_sha256']}
    obs = lab_lifecycle.observe(log, expected=expected)
    out['observation'] = obs
    out['raw_log_bytes'] = log.stat().st_size if log.exists() else 0
    side = Path(str(log) + '.error')
    out['sidecar_bytes'] = side.stat().st_size if side.exists() else 0
    out['raw_log_lines'] = (log.read_text('utf-8').splitlines() if log.exists() else [])

    wins = obs.get('active_windows') or []
    overlap = None
    if len(wins) >= 2:
        a, b = sorted(wins, key=lambda w: w['start'])[:2]
        overlap = round(min(a['end'], b['end']) - max(a['start'], b['start']), 6)
    out['distinct_slots'] = sorted({w['identity'] for w in wins})
    out['observed_overlap_s'] = overlap
    out['two_slots_overlapped'] = bool(overlap is not None and overlap > 0)
    out['ended_utc'] = _now()
    out['what_this_does_not_establish'] = [
        'coverage of any future verifier interval',
        'uninterrupted GPU utilization -- these are OCCUPIED DECODING SLOTS',
        'any readiness point, roster validity or trial clearance',
    ]
    dest = Path(lab_common.RESULTS_ROOT) / ('SMOKE_RECEIPT_%s.json' % token)
    lab_common.write_json_atomic(dest, out)
    print(json.dumps({k: out[k] for k in
                      ('server_ready', 'submitted_requests',
                       'generated_tokens_total', 'wall_seconds_total',
                       'distinct_slots', 'observed_overlap_s',
                       'two_slots_overlapped', 'raw_log_bytes')}, indent=1))
    print('observation active:', obs.get('active'),
          '| lifecycle_complete:', obs.get('lifecycle_complete'),
          '| reason:', obs.get('reason'))
    print('written:', dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
