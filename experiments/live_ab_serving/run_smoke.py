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

import hashlib
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
#: Bounds on the drained producer diagnostics. Root asked for them to be drained
#: and saved "within the already required absolute deadline", so the join is
#: bounded and what exceeds the caps is COUNTED rather than silently lost.
DIAGNOSTIC_LINE_CAP = 2000
DIAGNOSTIC_LINE_CHARS = 400
DRAIN_JOIN_S = 30.0
TOKEN_CAP = 2048


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


#: How much of a retained raw file is decoded into the receipt as a preview.
RAW_PREVIEW_CHARS = 4000


def _retain_bytes(p: Path) -> dict:
    """Retain a closed file by DIGEST, decoding only a labelled preview.

    Root, 2026-09-23 09:19: "retain raw bytes by digest/reference and decode
    only a labeled preview; a decoding failure must not erase the refusal
    record."

    The previous code did `log.read_text('utf-8').splitlines()`, which raises
    `UnicodeDecodeError` on non-UTF8 bytes -- and that exception escaped before
    the receipt was written, so the one artifact that would have recorded the
    problem was destroyed by it. Nothing here raises: an undecodable file is
    retained by digest and says so.
    """
    if not p.exists():
        return {'present': False}
    try:
        raw = p.read_bytes()
    except Exception as exc:                                   # noqa: BLE001
        return {'present': True, 'unreadable': '%s: %s' % (type(exc).__name__, exc)}
    out = {'present': True, 'bytes': len(raw),
           'sha256': hashlib.sha256(raw).hexdigest(),
           'path': lab_common.display_path(p),
           'preview_is_bounded': True, 'preview_chars_cap': RAW_PREVIEW_CHARS}
    try:
        text = raw.decode('utf-8')
        out['decodes_as_utf8'] = True
    except UnicodeDecodeError as exc:
        out['decodes_as_utf8'] = False
        out['decode_error'] = '%s at byte %d' % (exc.reason, exc.start)
        text = raw.decode('utf-8', 'replace')
    out['preview'] = text[:RAW_PREVIEW_CHARS]
    out['preview_truncated'] = len(text) > RAW_PREVIEW_CHARS
    return out


def drain_stream(stream, sink: list, dropped: dict, *,
                 line_cap: int = DIAGNOSTIC_LINE_CAP,
                 char_cap: int = DIAGNOSTIC_LINE_CHARS) -> None:
    """Read `stream` to EOF into `sink`, counting whatever exceeds the caps.

    Module level, and not the closure it started as, so it can be exercised with
    a mocked child. Root, 2026-09-23 08:00: "Mocked-child and saved-file
    regressions suffice for these Python repairs."

    The caps bound memory; `dropped` records exactly what they cost, because a
    silently truncated diagnostic reads as a quiet server. Nothing here raises:
    a failure to drain is appended to the sink as data, since this runs on a
    daemon thread whose exception would otherwise vanish.
    """
    dropped.setdefault('lines', 0)
    dropped.setdefault('chars', 0)
    dropped.setdefault('truncated_lines', 0)
    dropped['complete'] = False
    dropped['error'] = None
    try:
        for line in stream:
            if len(sink) < line_cap:
                kept = line.rstrip('\n')[:char_cap]
                # COUNT WHAT TRIMMING COSTS. Root, 2026-09-23 09:19:
                # "characters removed from retained lines are not counted (a
                # 900-character line trimmed to 400 reports zero dropped
                # characters)." A retained-but-truncated line looked identical
                # to a short one, so the receipt under-reported what was lost.
                lost = len(line.rstrip('\n')) - len(kept)
                if lost > 0:
                    dropped['truncated_lines'] += 1
                    dropped['chars'] += lost
                sink.append(kept)
            else:
                dropped['lines'] += 1
                dropped['chars'] += len(line)
        dropped['complete'] = True
    except Exception as exc:                                   # noqa: BLE001
        # Recorded as STRUCTURED state, not only as a line in the sink: root
        # observed that "an exception or unfinished drain can still accompany
        # supervisor success", because the caller only looked at the returned
        # lines.
        dropped['error'] = '%s: %s' % (type(exc).__name__, exc)
        sink.append('[drain failed: %s: %s]' % (type(exc).__name__, exc))


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

    # DRAIN THE PIPE. Root, 2026-09-23 08:00: "The terminal-failure path still
    # depends on an unchecked stderr stream that the supplied supervisor does
    # not drain or save ... Drain/save diagnostics within the already required
    # absolute deadline."
    #
    # Nothing read this pipe. Two consequences, and the first is worse than the
    # missing diagnostics: a child that writes more than the pipe buffer (~64 KB)
    # BLOCKS FOREVER on write, so the supervisor's own plumbing could hang the
    # producer it is measuring. And the process-level refusal's diagnostic line
    # went into a buffer nobody emptied.
    #
    # A daemon thread, so a stuck read can never outlive the absolute deadline
    # the caller already enforces, and a bounded buffer, so a chatty or looping
    # server cannot exhaust memory. What is dropped is COUNTED, never silently
    # truncated.
    diagnostics: list = []
    dropped = {'lines': 0, 'chars': 0}

    drain_thread = threading.Thread(
        target=drain_stream, args=(proc.stdout, diagnostics, dropped),
        daemon=True, name='live_ab_smoke_drain')
    drain_thread.start()

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
    # CONFIRM THE CHILD IS STOPPED BEFORE ANY FILE IS READ. Root, 2026-09-23
    # 08:40: the script "does not reap after its forced-kill fallback before
    # reading files ... Do not analyze output until the child is confirmed
    # stopped and the files closed."
    #
    # The forced-kill branch signalled and fell straight through to
    # proc.returncode, which is None until the child is reaped -- so a run that
    # needed SIGKILL read the lifecycle log while the producer might still have
    # had it open, and recorded a null exit code as if it were an outcome.
    stopped_cleanly = True
    try:
        proc.wait(timeout=60)
    except Exception:                                          # noqa: BLE001
        stopped_cleanly = False
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            out['forced_stop'] = True
        except Exception as exc:                               # noqa: BLE001
            out['forced_stop_error'] = '%s: %s' % (type(exc).__name__, exc)
        try:
            proc.wait(timeout=60)                              # REAP after SIGKILL
        except Exception as exc:                               # noqa: BLE001
            out['reap_error'] = '%s: %s' % (type(exc).__name__, exc)
    out['stopped_cleanly'] = stopped_cleanly
    out['child_confirmed_stopped'] = proc.returncode is not None
    out['server_exit_code'] = proc.returncode
    out['wall_seconds_total'] = round(time.monotonic() - t_wall0, 2)
    out['wall_cap_respected'] = out['wall_seconds_total'] <= WALL_CAP_S

    # Join the drain within the deadline, then RETAIN what it collected. A drain
    # that has not finished is reported as unfinished rather than waited on.
    drain_thread.join(timeout=DRAIN_JOIN_S)
    out['producer_diagnostics'] = {
        'lines': list(diagnostics),
        'lines_are_a_bounded_preview': True,
        'line_cap': DIAGNOSTIC_LINE_CAP,
        'chars_per_line_cap': DIAGNOSTIC_LINE_CHARS,
        'dropped_lines': dropped.get('lines', 0),
        'dropped_chars': dropped.get('chars', 0),
        'truncated_lines': dropped.get('truncated_lines', 0),
        'drain_reached_eof': bool(dropped.get('complete')),
        'drain_error': dropped.get('error'),
        'drain_thread_finished': not drain_thread.is_alive(),
        # The capture is COMPLETE only if the drain reached EOF, raised nothing,
        # and dropped nothing. Root: "Incomplete diagnostic capture must not be
        # reported as complete evidence." This flag is consumed by the
        # supervisor verdict below, not merely recorded.
        'capture_complete': (bool(dropped.get('complete'))
                             and not dropped.get('error')
                             and not dropped.get('lines', 0)
                             and not dropped.get('truncated_lines', 0)),
        'stream': 'the child stdout+stderr pipe, drained continuously from launch',
    }

    # --- THE GATE: nothing is parsed, read or hashed until the child is
    # --- CONFIRMED STOPPED -------------------------------------------------
    # Root, 2026-09-23 09:19: "both waits timing out still reaches `observe` and
    # three raw-log reads even though `child_confirmed_stopped=false`. A later
    # nonzero verdict cannot undo reading a file that may still be written.
    # Gate before every parse/read/hash."
    #
    # Exactly right, and the ordering was the whole point of the reap I added
    # last cycle: I recorded `child_confirmed_stopped` and then read the files
    # regardless, so the flag described the situation without governing it.
    # A refusal computed afterwards does not un-read a file a live producer was
    # still appending to.
    expected = {'host_id': m['host_id'], 'boot_id': m['boot_id'],
                'instance_id': token, 'binary_sha256': m['launcher']['sha256'],
                'patch_sha256': m['patch_sha256']}
    side = Path(str(log) + '.error')
    obs = None
    if not out['child_confirmed_stopped']:
        # The raw files are LEFT IN PLACE, unopened, for later closed-file
        # recovery. Root: "Preserve the raw files in place ... do not claim that
        # they are already closed or that their analysis completed."
        out['acquisition_not_analyzed'] = (
            'the child was never confirmed stopped, so the lifecycle log and its '
            'sidecar were NOT opened, parsed or hashed. They are preserved in '
            'place; they may still have been open for writing.')
        out['raw_artifacts_preserved_unread'] = [lab_common.display_path(log),
                                                 lab_common.display_path(side)]
        out['acquisition_invalidated_by_process_outcome'] = None
        out['observation'] = None
    else:
        # THE RETAINED EXIT OUTCOME REACHES THE READER. The declared stop signal
        # is passed as a DIAGNOSTIC only: root withdrew the signal-success
        # exception on 2026-09-23 09:19, and the retained smoke
        # (SMOKE_RECEIPT_smoke_4167e395ccfd.json) exited 0 under SIGTERM, so the
        # exception was never needed in the first place.
        obs = lab_lifecycle.observe(
            log, expected=expected, process_outcome=proc.returncode,
            expected_termination_signal=int(signal.SIGTERM))
        out['acquisition_invalidated_by_process_outcome'] = (
            obs.get('process_outcome_problem'))
        out['observation'] = obs
        out['raw_log_bytes'] = log.stat().st_size if log.exists() else 0
        out['sidecar_bytes'] = side.stat().st_size if side.exists() else 0
        # Retain by DIGEST, and decode only a labelled preview. Root: "retain raw
        # bytes by digest/reference and decode only a labeled preview; a decoding
        # failure must not erase the refusal record." The previous
        # `log.read_text('utf-8')` raised on non-UTF8 bytes and took the receipt
        # with it.
        out['raw_log'] = _retain_bytes(log)
        out['raw_sidecar'] = _retain_bytes(side)

    wins = (obs or {}).get('active_windows') or []
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
    # THE VERDICT IS COMPUTED BEFORE THE WRITE, because the sink is WRITE-ONCE
    # (`write_json_atomic` refuses a differing second write, which is what
    # caught the v2 drill's dry-run collision). One receipt, one write.
    problems = [p for p in (
        ('process outcome: %s' % out['acquisition_invalidated_by_process_outcome'])
        if out.get('acquisition_invalidated_by_process_outcome') else None,
        ('child never confirmed stopped'
         if not out.get('child_confirmed_stopped') else None),
        ('acquisition not analyzed: %s' % out['acquisition_not_analyzed']
         if out.get('acquisition_not_analyzed') else None),
        ('acquisition not complete: %s' % (obs or {}).get('reason')
         if obs is not None and not obs.get('lifecycle_complete') else None),
        ('diagnostic capture incomplete: %s'
         % {k: out['producer_diagnostics'][k] for k in
            ('drain_reached_eof', 'drain_error', 'dropped_lines', 'truncated_lines')}
         if not out['producer_diagnostics']['capture_complete'] else None),
    ) if p]
    out['supervisor_problems'] = problems
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

    # THE EXIT STATUS REPORTS THE ACQUISITION. Root, 2026-09-23 08:40: the
    # script "returns zero unconditionally". A supervisor whose own status is
    # always success cannot be used in any chain that checks it, and it reported
    # success for a run whose acquisition the reader had refused -- the same
    # shape as a receipt claiming a success its parser rejected.
    if problems:
        for p in problems:
            print('REFUSED:', p)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
