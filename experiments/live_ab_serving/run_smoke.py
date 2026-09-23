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
#: The FINITE byte budget for the retained diagnostic capture. Root, 10:03:
#: "Freeze that finite byte budget in the existing costed preparation plan; do
#: not use a new model run to tune it." Declared here and carried into the plan.
DIAGNOSTIC_BYTE_BUDGET = 8 * 1024 * 1024
#: Fixed-size reads: a line iterator would consume an entire line before any cap
#: applied, so one enormous line could exhaust memory whatever the cap said.
DIAGNOSTIC_CHUNK_BYTES = 65536
#: Display only. Preview length never decides whether an acquisition is valid.
DIAGNOSTIC_PREVIEW_CHARS = 4000
DRAIN_JOIN_S = 30.0
#: Time reserved at the end of the absolute budget for stop, reap and
#: finalisation, so cleanup is never the thing that runs out of clock.
CLEANUP_RESERVE_S = 90.0
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


def drain_to_artifact(stream, artifact_path: Path, state: dict, *,
                      byte_budget: int = DIAGNOSTIC_BYTE_BUDGET,
                      chunk: int = DIAGNOSTIC_CHUNK_BYTES,
                      deadline=None) -> None:
    """Copy `stream` to an IMMUTABLE per-attempt artifact, in bounded chunks.

    Root, 2026-09-23 10:03, deciding the question put to it:

        "A shortened display preview alone must not invalidate an otherwise
         complete acquisition. Missing required raw capture still must. The
         current stream helper keeps only truncated lines, so those lost
         characters are currently lost raw evidence, not merely hidden from the
         display. ... Retain the full bounded diagnostic byte stream as an
         immutable per-attempt artifact, with byte count and hash/reference;
         derive the bounded receipt preview from that capture. Read in bounded
         chunks, not an unbounded line iterator."

    THE DEFECT THAT MAKES THIS NECESSARY. The previous helper kept only trimmed
    lines. Its counts said how much was lost, but the bytes themselves were
    gone, so the receipt's digest covered the RETAINED TEXT rather than the
    stream. Root: "A digest of bytes that were discarded is not a retained raw
    artifact." Truncation was therefore never a display question -- it was
    destruction of evidence, which is exactly why the strict gate could not
    simply be dropped.

    Also: a line iterator consumes a whole line before any per-line cap applies,
    so one enormous line could exhaust memory however small the cap. Fixed-size
    reads bound that, which is the "bounded previews do not imply bounded
    memory" point root made.

    `raw_capture_complete` requires EOF, no error, and every byte read written
    to the artifact. Preview length plays no part in it.
    """
    state.setdefault('bytes_captured', 0)
    state.setdefault('bytes_dropped', 0)
    state['reached_eof'] = False
    state['error'] = None
    state['budget_exhausted'] = False
    state['deadline_exhausted'] = False
    state['artifact'] = lab_common.display_path(artifact_path)
    digest = hashlib.sha256()
    try:
        raw = getattr(stream, 'buffer', stream)      # bytes, not decoded text
        with open(artifact_path, 'wb') as fh:
            while True:
                if deadline is not None and time.monotonic() > deadline:
                    state['deadline_exhausted'] = True
                    break
                block = raw.read(chunk)
                if not block:
                    state['reached_eof'] = True
                    break
                if isinstance(block, str):
                    block = block.encode('utf-8', 'surrogateescape')
                room = byte_budget - state['bytes_captured']
                if room <= 0:
                    # The PREFIX is retained and the loss stated precisely. Root:
                    # "retain the available prefix and precise failure/loss state
                    # and refuse full capture."
                    state['budget_exhausted'] = True
                    state['bytes_dropped'] += len(block)
                    continue
                keep = block[:room]
                fh.write(keep)
                digest.update(keep)
                state['bytes_captured'] += len(keep)
                if len(keep) < len(block):
                    state['budget_exhausted'] = True
                    state['bytes_dropped'] += len(block) - len(keep)
    except Exception as exc:                                   # noqa: BLE001
        state['error'] = '%s: %s' % (type(exc).__name__, exc)
    state['sha256'] = digest.hexdigest()
    state['raw_capture_complete'] = bool(
        state['reached_eof'] and not state['error']
        and not state['budget_exhausted'] and not state['deadline_exhausted']
        and state['bytes_dropped'] == 0)


def preview_of_artifact(artifact_path: Path, state: dict, *,
                        chars: int = DIAGNOSTIC_PREVIEW_CHARS) -> dict:
    """The bounded display preview, DERIVED from the retained capture.

    Two distinct states, as root required: `preview_truncated` says the display
    was shortened; `raw_capture_complete` says whether evidence was lost. Only
    the second may refuse an acquisition.
    """
    out: dict = {'preview_chars_cap': chars, 'preview_truncated': False,
                 'preview': '', 'derived_from': state.get('artifact'),
                 'capture_sha256': state.get('sha256')}
    try:
        raw = artifact_path.read_bytes() if artifact_path.exists() else b''
    except Exception as exc:                                   # noqa: BLE001
        out['preview_unavailable'] = '%s: %s' % (type(exc).__name__, exc)
        return out
    text = raw.decode('utf-8', 'replace')
    out['preview'] = text[:chars]
    out['preview_truncated'] = len(text) > chars
    return out


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
    capture = {}
    capture_path = log.parent / ('%s.producer_stream' % token)
    drain_thread = threading.Thread(
        target=drain_to_artifact, args=(proc.stdout, capture_path, capture),
        kwargs={'deadline': t_wall0 + WALL_CAP_S - CLEANUP_RESERVE_S},
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
    out['producer_diagnostics'] = dict(
        preview_of_artifact(capture_path, capture),
        # TWO DISTINCT STATES, as root decided on 2026-09-23 10:03: a shortened
        # display preview must not invalidate an otherwise complete acquisition,
        # but missing raw capture still must. Only `raw_capture_complete` below
        # enters the verdict; `preview_truncated` never does.
        raw_capture_complete=bool(capture.get('raw_capture_complete')),
        bytes_captured=capture.get('bytes_captured', 0),
        bytes_dropped=capture.get('bytes_dropped', 0),
        reached_eof=bool(capture.get('reached_eof')),
        drain_error=capture.get('error'),
        budget_exhausted=bool(capture.get('budget_exhausted')),
        deadline_exhausted=bool(capture.get('deadline_exhausted')),
        byte_budget=DIAGNOSTIC_BYTE_BUDGET,
        drain_thread_finished=not drain_thread.is_alive(),
        artifact=capture.get('artifact'),
        artifact_sha256=capture.get('sha256'),
        stream='the owned child stdout+stderr pipe, captured to an immutable '
               'per-attempt artifact from launch',
        note='draining the owned child pipe is ACQUISITION, not analysis of an '
             'owner-written lifecycle file, so it runs before the closed-file '
             'gate (root, 10:03)')

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
        ('raw diagnostic capture incomplete: %s'
         % {k: out['producer_diagnostics'][k] for k in
            ('reached_eof', 'drain_error', 'bytes_dropped',
             'budget_exhausted', 'deadline_exhausted')}
         if not out['producer_diagnostics']['raw_capture_complete'] else None),
        ('the drain thread had not finished, so its state is not a final snapshot'
         if not out['producer_diagnostics']['drain_thread_finished'] else None),
    ) if p]
    out['supervisor_problems'] = problems
    dest = Path(lab_common.RESULTS_ROOT) / ('SMOKE_RECEIPT_%s.json' % token)
    lab_common.write_json_atomic(dest, out)
    # THE SUMMARY MUST NOT OUTLIVE THE RECEIPT. Root, 2026-09-23 10:03: "after
    # writing its valid refusal receipt, the console summary accesses the absent
    # `raw_log_bytes` key, then would call `obs.get` on `None`. Guard the summary
    # to return the intended nonzero status normally."
    #
    # Both are real on the route I added last cycle: when the child is not
    # confirmed stopped, `raw_log_bytes` is never set (KeyError) and `obs` stays
    # None (AttributeError). Both fire AFTER the refusal receipt is on disk and
    # BEFORE `return 1`, so the supervisor would die with a traceback instead of
    # the designed exit status -- a correct refusal reported as a crash. Printing
    # is cosmetic; the exit status is the contract, and nothing cosmetic may
    # stand between the two.
    print(json.dumps({k: out.get(k) for k in
                      ('server_ready', 'submitted_requests',
                       'generated_tokens_total', 'wall_seconds_total',
                       'distinct_slots', 'observed_overlap_s',
                       'two_slots_overlapped', 'raw_log_bytes',
                       'child_confirmed_stopped')}, indent=1))
    if obs is None:
        print('observation: NOT TAKEN -', out.get('acquisition_not_analyzed'))
    else:
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
