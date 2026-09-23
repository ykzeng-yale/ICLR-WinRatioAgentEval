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
    # REFUSE A COLLISION BEFORE TOUCHING THE ORIGINAL. Root, 10:39: "Create the
    # per-attempt artifact without truncating an existing path; refuse collision
    # before changing the original." `open(..., 'wb')` truncates, so a repeated
    # token would have destroyed the earlier attempt's evidence in the act of
    # recording the new one.
    if artifact_path.exists():
        state['error'] = ('refusing to overwrite an existing capture artifact at '
                          '%s' % lab_common.display_path(artifact_path))
        state['sha256'] = None
        state['raw_capture_complete'] = False
        return
    try:
        raw = getattr(stream, 'buffer', stream)      # bytes, not decoded text
        with open(artifact_path, 'xb') as fh:
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
    # ATTEMPTED-WRITE counters, named as such. Root, 10:39: "On write failure,
    # the current incremental counters can also misdescribe the saved prefix: a
    # mocked sink persists two bytes before raising, while the receipt reports
    # zero bytes and the empty digest ... do not label an attempted-write digest
    # as a measured persisted digest."
    state['attempted_write_sha256'] = digest.hexdigest()
    state['attempted_write_bytes'] = state['bytes_captured']
    # MEASURED from the closed file. The `with` block has exited, so the writer
    # is done with it either way.
    try:
        persisted = artifact_path.read_bytes()
        state['measured_bytes'] = len(persisted)
        state['measured_sha256'] = hashlib.sha256(persisted).hexdigest()
        state['measured_unavailable'] = None
    except Exception as exc:                                   # noqa: BLE001
        state['measured_bytes'] = None
        state['measured_sha256'] = None
        state['measured_unavailable'] = '%s: %s' % (type(exc).__name__, exc)
    state['sha256'] = state['measured_sha256']
    state['attempted_equals_measured'] = (
        state['measured_sha256'] is not None
        and state['measured_sha256'] == state['attempted_write_sha256'])
    state['raw_capture_complete'] = bool(
        state['reached_eof'] and not state['error']
        and not state['budget_exhausted'] and not state['deadline_exhausted']
        and state['bytes_dropped'] == 0
        and state['attempted_equals_measured'])


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


class Deadline:
    """ONE absolute monotonic deadline for the whole attempt, with a reserve.

    Root, 2026-09-23 09:19: "Startup can consume nearly the entire 600-second
    budget, after which request joins, two independent 60-second waits and the
    30-second drain join still receive fresh time allowances ... Use one absolute
    monotonic deadline, reserve cleanup time, bound every remaining wait by time
    left, prevent new dispatch after budget exhaustion, and record final elapsed
    time after cleanup/finalization. Do not describe a daemon thread as
    enforcement of that deadline."

    Every fresh `timeout=60` was a new budget grant. Four of them in sequence
    meant the declared 600 s cap bounded no path through the script; it bounded
    only the first wait. `bounded()` is the repair: a wait may have at most the
    time actually left.

    `CLEANUP_RESERVE_S` is held back from the dispatch budget so stopping,
    reaping and writing the receipt are never the operations that run out of
    clock -- an attempt that cannot finalise leaves no evidence at all.
    """

    def __init__(self, budget_s: float, *, reserve_s: float = CLEANUP_RESERVE_S,
                 now=time.monotonic) -> None:
        self._now = now
        self.started = now()
        self.budget_s = float(budget_s)
        self.reserve_s = float(reserve_s)
        self.hard = self.started + self.budget_s
        self.dispatch_until = self.hard - self.reserve_s

    def elapsed(self) -> float:
        return self._now() - self.started

    def remaining(self) -> float:
        return max(0.0, self.hard - self._now())

    def dispatch_remaining(self) -> float:
        """Time left before the cleanup reserve begins."""
        return max(0.0, self.dispatch_until - self._now())

    def may_dispatch(self) -> bool:
        """False once the reserve is reached: no NEW work after exhaustion."""
        return self.dispatch_remaining() > 0.0

    def expired(self) -> bool:
        return self.remaining() <= 0.0

    def bounded(self, want_s: float, *, use_reserve: bool = False) -> float:
        """The largest wait permitted now: never more than the time left."""
        left = self.remaining() if use_reserve else self.dispatch_remaining()
        return max(0.0, min(float(want_s), left))

    def state(self) -> dict:
        return {'budget_s': self.budget_s, 'reserve_s': self.reserve_s,
                'elapsed_s': round(self.elapsed(), 3),
                'remaining_s': round(self.remaining(), 3),
                'dispatch_remaining_s': round(self.dispatch_remaining(), 3),
                'may_dispatch': self.may_dispatch(), 'expired': self.expired(),
                'enforcement': ('every wait is bounded by remaining(); this is '
                                'arithmetic on one monotonic origin, NOT a '
                                'daemon thread')}


def verify_launch_artifacts(manifest: dict, *, binary: Path, model: Path) -> dict:
    """MEASURE the artifacts about to be launched and compare with the manifest.

    Root, 2026-09-23 09:19: "The selected binary is a hardcoded path and the
    model is the first matching glob result; their measured byte hashes are not
    checked against the immutable launch manifest before `Popen`. Verify the
    selected source/patch, launcher/library closure and model artifact against
    their declared pins at the trusted launch boundary; never treat copying
    manifest hashes into `expected` as that verification."

    That last clause is the point. The supervisor took `m['launcher']['sha256']`
    and put it into the `expected` dict handed to the reader -- so the reader
    compared the manifest with itself and the bytes on disk were never read.
    An agreement between a dict and a copy of that dict is not evidence about a
    file, the same shape as the foreign-records-plus-foreign-manifest witness
    root produced in September.

    Returns a verdict; raises nothing. The caller refuses before `Popen`.
    """
    checks = []
    for name, path, declared in (
            ('launcher', binary, (manifest.get('launcher') or {}).get('sha256')),
            ('model', model, (manifest.get('model') or {}).get('sha256'))):
        row: dict = {'artifact': name, 'path': lab_common.display_path(path),
                     'declared_sha256': declared}
        if not isinstance(declared, str) or not lab_lifecycle.is_digest(declared):
            row['problem'] = ('the manifest declares no usable %s digest, so '
                              'there is nothing to verify against' % name)
        elif not path.exists():
            row['problem'] = 'the selected %s does not exist at that path' % name
        else:
            h = hashlib.sha256()
            try:
                with path.open('rb') as fh:
                    for block in iter(lambda: fh.read(1 << 20), b''):
                        h.update(block)
                row['measured_sha256'] = h.hexdigest()
                row['bytes'] = path.stat().st_size
                row['agrees'] = (row['measured_sha256'] == declared)
                if not row['agrees']:
                    row['problem'] = ('the selected %s does not match its '
                                      'declared pin' % name)
            except Exception as exc:                           # noqa: BLE001
                row['problem'] = 'could not read the %s: %s' % (name, exc)
        checks.append(row)
    # THE LAUNCHER IS NOT THE IMPLEMENTATION. Root, 2026-09-23 11:16: "the
    # actual `non_system_library_closure` declaration can name a sibling
    # implementation library whose bytes have changed and still receive
    # verified=true ... Resolve and check the actual selected implementation
    # libraries and backend artifacts against the declared inventory ... The
    # small launcher is not the implementation. Do not present a successful
    # two-file hash comparison as acceptance of the entire candidate instrument."
    #
    # The built launcher is 33,472 bytes; every line of instrumented server code
    # lives in libllama-server-impl.dylib and the ggml backends beside it. A
    # two-file check could pass while the code that actually runs had changed.
    declared_libs = manifest.get('non_system_library_closure')
    lib_rows = []
    if not isinstance(declared_libs, dict) or not declared_libs:
        lib_rows.append({'problem': (
            'the manifest declares no non-system library closure, so the '
            'implementation libraries this launcher loads are unverified. A '
            'missing required input refuses before Popen.')})
    else:
        for name in sorted(declared_libs):
            entry = declared_libs[name] or {}
            want = entry.get('sha256') if isinstance(entry, dict) else entry
            lib = binary.parent / name
            row = {'library': name, 'declared_sha256': want,
                   'path': lab_common.display_path(lib)}
            if not isinstance(want, str) or not lab_lifecycle.is_digest(want):
                row['problem'] = ('%s declares no usable digest' % name)
            elif not lib.exists():
                row['problem'] = ('%s is declared but absent beside the launcher'
                                  % name)
            else:
                h = hashlib.sha256()
                try:
                    with lib.open('rb') as fh:
                        for block in iter(lambda: fh.read(1 << 20), b''):
                            h.update(block)
                    row['measured_sha256'] = h.hexdigest()
                    row['agrees'] = (row['measured_sha256'] == want)
                    if not row['agrees']:
                        row['problem'] = ('%s does not match its declared pin'
                                          % name)
                except Exception as exc:                       # noqa: BLE001
                    row['problem'] = 'could not read %s: %s' % (name, exc)
            lib_rows.append(row)
    checks.extend(lib_rows)
    problems = [c['problem'] for c in checks if c.get('problem')]
    return {'checks': checks, 'problems': problems, 'verified': not problems,
            'measured_from_disk': True,
            'libraries_declared': (len(declared_libs)
                                   if isinstance(declared_libs, dict) else 0),
            'libraries_verified': sum(1 for r in lib_rows if r.get('agrees')),
            'note': ('measured byte digests of the launcher, the model AND the '
                     'declared non-system library closure, compared with the '
                     'immutable launch manifest BEFORE Popen. This is an '
                     'inventory check of the declared members, not a proven '
                     'transitive closure.')}


def finalize(out: dict, dest: Path, problems: list) -> int:
    """Write EXACTLY ONE receipt and return the supervisor status.

    Root, 2026-09-23 09:19: "Startup `Popen` failure and non-UTF8 lifecycle
    bytes both currently raise before the receipt is written. Persist the launch
    intent before attempting the child, preserve actual attempted-versus-started
    state, and route failures through one guaranteed receipt/finalization path."

    Every early exit used to be a bare `return 2` or an escaping exception, so
    the runs that failed WORST left the least evidence: a missing weight, a
    failed `Popen` and an undecodable log each produced no receipt at all. The
    attempt that cannot be described is the one most worth describing.
    """
    out['supervisor_problems'] = list(problems)
    out['ended_utc'] = _now()
    try:
        lab_common.write_json_atomic(dest, out)
        out['receipt_written'] = True
    except Exception as exc:                                   # noqa: BLE001
        # Last resort: say so on stderr. There is nowhere else left.
        print('FATAL: could not write the receipt: %s: %s'
              % (type(exc).__name__, exc), file=sys.stderr)
        return 3
    for p in problems:
        print('REFUSED:', p)
    print('written:', dest)
    return 1 if problems else 0


def usable_token_count(value: object) -> bool:
    """A usable completion-token count: a NON-NEGATIVE, non-boolean integer.

    Root, 2026-09-23 11:16: "Keep integer usage strict and nonnegative. Boolean
    and float token counts are unusable; do not silently truncate or coerce
    them. Also reject negative integers ... current code accepts `-1` as a known
    token total/cap success."
    """
    return (isinstance(value, int) and not isinstance(value, bool) and value >= 0)


def _persist_response_bytes(directory: Path, request_id: str, raw: bytes) -> dict:
    """Write the response bytes ONCE under the request identity, then describe them.

    Root, 2026-09-23 11:16: "Persist the response bytes once under unique
    request identity before parsing, with a reference and measured byte
    count/hash; preserve unparsable responses and fail retention explicitly.
    Preview truncation alone is harmless only when the complete raw artifact
    exists."

    The previous version kept length, hash and a 4,000-character preview. For a
    response longer than that, the tail existed in no persisted file anywhere --
    a digest describing bytes that no longer exist, which is the same finding as
    the diagnostic capture.

    The size and hash reported are MEASURED back from the written file, not
    counted on the way in, and a retention failure is stated rather than
    swallowed.
    """
    path = directory / ('%s.response' % request_id)
    out: dict = {'request_id': request_id,
                 'path': lab_common.display_path(path),
                 'retained': False,
                 'preview_chars_cap': DIAGNOSTIC_PREVIEW_CHARS,
                 'preview': raw.decode('utf-8', 'replace')[:DIAGNOSTIC_PREVIEW_CHARS],
                 'preview_truncated': len(raw) > DIAGNOSTIC_PREVIEW_CHARS,
                 'bytes_received': len(raw)}
    try:
        # 'xb': never overwrite another request's evidence.
        with open(path, 'xb') as fh:
            fh.write(raw)
        persisted = path.read_bytes()
        out['retained'] = True
        out['bytes'] = len(persisted)
        out['sha256'] = hashlib.sha256(persisted).hexdigest()
        out['complete'] = (len(persisted) == len(raw))
    except Exception as exc:                                   # noqa: BLE001
        out['retention_error'] = '%s: %s' % (type(exc).__name__, exc)
        out['complete'] = False
    return out


def summarize_usage(results: list, *, token_cap: int, expected: int) -> dict:
    """Totals that refuse to invent a zero, over an EXPECTED denominator.

    Root, 09:19: "A timeout with missing usage stays unknown rather than
    becoming a measured zero." Root, 11:16: "`summarize_usage([])` returns
    measured zero/cap true ... Unfinished/absent request records must not
    disappear from the denominator."

    The second is the first defect one level up, and I had missed it. I stopped
    an absent USAGE from becoming zero, while an absent REQUEST RECORD still
    did: a worker that never appended its row simply shrank the population, and
    an empty list summed to a confident 0 with the cap "respected". The
    denominator is now what was PLANNED, not what happened to be reported.
    """
    # THE DENOMINATOR IS REQUIRED AND VALIDATED. Root, 2026-09-23 12:04,
    # answering the API question I put to it: "Make the expected denominator
    # required ... remove the silent fallback to reported rows ... Validate this
    # smoke helper's expected count as a positive non-boolean integer rather
    # than coercing floats/bools with int()."
    #
    # The fallback was the defect in miniature: omitting the argument gave a
    # measured total of 100 for a single record, while expected=2 correctly left
    # it unknown. A caller that forgot would silently get the old behaviour.
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise ValueError('expected must be a positive non-boolean integer, got %r'
                         % (expected,))
    # THE SAME RULE, APPLIED IN BOTH PLACES -- not the aggregate trusting the
    # row's flag. Root asked that row and total "derive ... from the same
    # nonnegative, non-boolean integer rule"; a total that merely believes
    # `usage_known` would be bypassed by any row that set it wrongly, which is
    # exactly the disagreement being repaired.
    known = [r for r in results
             if r.get('usage_known')
             and usable_token_count((r.get('usage') or {}).get('completion_tokens'))]
    reported = len(results)
    denom = expected
    # records that were planned but never appended a row at all
    unaccounted = max(0, denom - reported)
    unknown = (reported - len(known)) + unaccounted
    known_sum = sum(int(r['usage']['completion_tokens']) for r in known)
    complete = (denom > 0 and unknown == 0)
    return {
        'generated_tokens_known_sum': known_sum,
        'requests_expected': denom,
        'requests_with_records': reported,
        'requests_unaccounted_for': unaccounted,
        'requests_with_known_usage': len(known),
        'requests_with_unknown_usage': unknown,
        'generated_tokens_total': known_sum if complete else None,
        'generated_tokens_total_note': (
            'every expected request reported a usable non-negative integer '
            'usage' if complete else
            'None: %d of %d expected request(s) reported no usable usage (%d '
            'left no record at all). The known-only sum is a LOWER BOUND, never '
            'the total.' % (unknown, denom, unaccounted)),
        'token_cap_respected': (known_sum <= token_cap) if complete else None,
        'token_cap': token_cap,
    }


def main() -> int:
    # LAUNCH INTENT IS PERSISTED BEFORE ANYTHING IS ATTEMPTED, so a failure
    # during selection or startup still leaves a receipt describing what was
    # about to happen and how far it got.
    out: dict = {
        'schema': 'live_ab/smoke_receipt-v1',
        'convention': 'model-dependent',
        'started_utc': _now(),
        'attempted': True,
        'child_started': False,
        'planned_requests': 2,
        'submitted_requests': 0,
        'is_a_trial_episode': False,
    }
    dest = Path(lab_common.RESULTS_ROOT) / ('SMOKE_RECEIPT_unstarted_%s.json'
                                            % time.strftime('%Y%m%dT%H%M%SZ',
                                                            time.gmtime()))
    try:
        manifest_path, log_path, token = (
            Path(l) if i < 2 else l
            for i, l in enumerate(Path('/tmp/lab_smoke_manifest.txt')
                                  .read_text().strip().splitlines()))
        m = json.loads(Path(manifest_path).read_text('utf-8'))
    except Exception as exc:                                   # noqa: BLE001
        return finalize(out, dest,
                        ['the launch manifest could not be read: %s: %s'
                         % (type(exc).__name__, exc)])
    out['manifest'] = manifest_path.name
    out['run_token'] = token
    out['caps'] = m.get('caps')
    dest = Path(lab_common.RESULTS_ROOT) / ('SMOKE_RECEIPT_%s.json' % token)
    log = Path(log_path)
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:                                   # noqa: BLE001
        return finalize(out, dest, ['the log directory could not be created: %s'
                                    % exc])

    deadline = Deadline(WALL_CAP_S)
    out['deadline'] = deadline.state()

    model = None
    import glob
    for cand in glob.glob(str(Path.home() / '.cache/huggingface/**'
                              / m['model']['file']), recursive=True):
        model = Path(cand)
        break
    if model is None:
        return finalize(out, dest, ['the pinned weight was not found locally'])

    # THE TRUSTED LAUNCH BOUNDARY. Measured bytes, compared with the immutable
    # manifest, BEFORE Popen -- not manifest hashes copied into `expected`.
    out['launch_verification'] = verify_launch_artifacts(m, binary=BIN, model=model)
    if not out['launch_verification']['verified']:
        return finalize(out, dest, ['launch artifacts do not match their pins: %s'
                                    % '; '.join(out['launch_verification']['problems'])])

    out.update({
        'schema': 'live_ab/smoke_receipt-v1',
        'convention': 'model-dependent',
        # UNKNOWN until the child exists and loads. Root, 11:16: the Popen
        # failure receipt "combines child_started=false with loaded_a_model=true;
        # retain actual attempted/started/loaded states and leave unobserved
        # loading unknown. Do not infer a loaded model before the child exists."
        'loaded_a_model': None,
    })
    env = dict(os.environ, LIVE_AB_LIFECYCLE_LOG=str(log), LIVE_AB_RUN_TOKEN=token)
    args = [str(BIN), '-m', str(model)] + m['server_args']
    t_wall0 = deadline.started

    try:
        proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
    except Exception as exc:                                   # noqa: BLE001
        # ATTEMPTED but never STARTED, and that distinction is retained.
        out['child_started'] = False
        out['popen_error'] = '%s: %s' % (type(exc).__name__, exc)
        return finalize(out, dest, ['the child could not be started: %s' % exc])
    out['child_started'] = True
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
        # THE DRAIN RUNS TO THE HARD END, NOT THE WORK CUTOFF. Root, 10:39:
        # "Use the reserve for cleanup, not to stop collecting its diagnostics
        # early ... Keep the drain collecting shutdown diagnostics through EOF
        # within the hard deadline. The newly supplied `drain deadline =
        # start+510` can end capture before shutdown diagnostics arrive; it is
        # not the correct use of the reserve." Exactly right: the diagnostics
        # that matter most are the ones the server emits WHILE SHUTTING DOWN,
        # which is precisely the window the reserve exists for.
        kwargs={'deadline': deadline.hard},
        daemon=True, name='live_ab_smoke_drain')
    drain_thread.start()

    import requests
    base = 'http://127.0.0.1:%d' % m['port']
    ready = False
    while deadline.may_dispatch():
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
    # DURABLE REQUEST INTENT, DEPOSITED BEFORE THE BARRIER. Root, 2026-09-23
    # 09:19: "Planned request IDs/payloads are not durably deposited before the
    # barrier; `submitted_requests=2` is assigned before either thread submits."
    #
    # The payload was built inside the worker, after the thread had started, so
    # an attempt that died at the barrier left no record of what it had been
    # about to send. Intent is now written down first, with the exact payload
    # and its digest, so a failed dispatch is still a described dispatch.
    planned = []
    for idx in range(2):
        body = {'model': 'coder',
                'messages': [{'role': 'user', 'content': m['request']['prompt']}],
                'max_tokens': m['request']['max_tokens'],
                'temperature': m['request']['temperature'],
                'seed': m['request']['seed'], 'stream': False, 'n': 1}
        payload = json.dumps(body, sort_keys=True, separators=(',', ':'))
        planned.append({'index': idx,
                        'request_id': '%s_req%d' % (token, idx),
                        'payload': body,
                        'payload_sha256': hashlib.sha256(payload.encode()).hexdigest(),
                        'endpoint': base + '/v1/chat/completions'})
    out['planned_request_intent'] = planned

    # DURABLE, ON DISK, BEFORE ANY TRANSPORT. Root, 2026-09-23 11:16: "Persist
    # intent, rather than assigning a dictionary. `out['planned_request_intent']
    # = planned` is only memory until terminal finalization. In the actual-main
    # witness, both barriers and both POST calls observe zero durable writes ...
    # Failure to persist must refuse dispatch; terminal completion must not
    # overwrite intent."
    #
    # The comment above it used to say intent was "persisted before anything is
    # attempted". It was a dict in memory. If the supervisor died mid-dispatch,
    # nothing on disk said what it had been about to send -- which is the one
    # thing an interrupted attempt most needs to leave behind.
    #
    # A SEPARATE file, so the terminal receipt's write-once semantics cannot
    # erase it.
    intent_path = log.parent / ('%s.intent.json' % token)
    intent_doc = {
        'schema': 'live_ab/request_intent-v1',
        'attempt_id': '%s_%s' % (token, time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())),
        'run_token': token,
        'written_utc': _now(),
        'canonicalization': 'json.dumps(body, sort_keys=True, separators=(",",":"))',
        'planned_requests': planned,
        'note': ('written BEFORE the barrier and before any transport call, so an '
                 'interrupted attempt still says what it was about to send'),
    }
    try:
        lab_common.write_json_atomic(intent_path, intent_doc)
        out['request_intent_artifact'] = {
            'path': lab_common.display_path(intent_path),
            'attempt_id': intent_doc['attempt_id'],
            'persisted': True,
            'sha256': hashlib.sha256(intent_path.read_bytes()).hexdigest(),
            'bytes': intent_path.stat().st_size,
        }
    except Exception as exc:                                   # noqa: BLE001
        out['request_intent_artifact'] = {
            'path': lab_common.display_path(intent_path), 'persisted': False,
            'error': '%s: %s' % (type(exc).__name__, exc)}
        return finalize(out, dest,
                        ['the request intent could not be persisted, so no '
                         'request was dispatched: %s' % exc])

    submitted = threading.Lock()
    submitted_count = [0]
    attempted_count = [0]

    if ready:
        barrier = threading.Barrier(2)

        def one(idx: int) -> None:
            plan = planned[idx]
            rec: dict = {'index': idx, 'request_id': plan['request_id'],
                         'payload_sha256': plan['payload_sha256'],
                         'submitted': False}
            try:
                barrier.wait(timeout=deadline.bounded(30))
            except Exception as exc:                           # noqa: BLE001
                # A FAILED BARRIER IS NOT PERMISSION TO SEND. Root, 11:16: "the
                # actual-main early-broken-barrier case still makes both POST
                # calls and returns success while budget remains; the
                # post-barrier cutoff repair does not close it." The barrier is
                # the coordination this smoke exists to observe -- two requests
                # overlapping. If it broke, the pair was never coordinated, and
                # sending anyway produces traffic that answers no question.
                rec['barrier_error'] = '%s: %s' % (type(exc).__name__, exc)
                rec['not_dispatched'] = ('the barrier failed, so this request '
                                         'was never coordinated with its pair '
                                         'and was not sent')
                rec['t_ack_monotonic'] = rec['t_send_monotonic'] = time.monotonic()
                rec['elapsed_s'] = 0.0
                results.append(rec)
                return
            if not deadline.may_dispatch():
                # NO NEW DISPATCH AFTER EXHAUSTION.
                rec['not_dispatched'] = 'the work cutoff was reached before this '\
                                        'request was sent'
                rec['t_ack_monotonic'] = rec['t_send_monotonic'] = time.monotonic()
                rec['elapsed_s'] = 0.0
                results.append(rec)
                return
            # THE TRANSPORT INVOCATION IS RECORDED BEFORE THE CALL. Root,
            # 11:16: "the new submission counter increments only after
            # `requests.post` returns, so a request that was attempted and then
            # timed out still counts as unsubmitted ... records
            # submitted_requests=0 and incorrectly calls both 'never submitted'.
            # Record transport invocation before the call and response receipt
            # afterward; preserve timeout and unknown server receipt/usage
            # without claiming no request was sent."
            #
            # Three distinct states, and conflating them is how a timed-out
            # request became a request that was never made: ATTEMPTED (we called
            # the transport), RESPONSE RECEIVED (it returned), and DELIVERY
            # UNKNOWN (it raised, so whether the server got it is not knowable
            # from here).
            rec['transport_attempted'] = True
            rec['t_send_monotonic'] = time.monotonic()
            rec['t_send_utc'] = _now()
            with submitted:
                attempted_count[0] += 1
            try:
                r = requests.post(plan['endpoint'], json=plan['payload'],
                                  timeout=deadline.bounded(REQUEST_CAP_S))
                rec['response_received'] = True
                rec['delivery'] = 'response_received'
                rec['submitted'] = True
                with submitted:
                    submitted_count[0] += 1
                rec['t_ack_monotonic'] = time.monotonic()
                rec['status'] = r.status_code
                # RAW RESPONSE BYTES RETAINED. Root: "raw HTTP responses are
                # reduced to a few fields." The three summary fields below are
                # derived; these bytes are the evidence they were derived from.
                # THE BYTES ARE PERSISTED ONCE, BEFORE PARSING. Root, 11:16:
                # "Length, hash and a 4,000-character preview cannot recover the
                # omitted bytes. Valid responses longer than 9 KB return
                # supervisor success while their tail bytes are absent from
                # every persisted file ... Persist the response bytes once under
                # unique request identity before parsing."
                #
                # A digest plus a preview describes bytes that no longer exist,
                # which is the same finding as the diagnostic capture: a digest
                # of discarded bytes is not a retained artifact.
                raw = r.content
                rec['raw_response'] = _persist_response_bytes(
                    log.parent, plan['request_id'], raw)
                try:
                    d = r.json()
                except Exception as exc:                       # noqa: BLE001
                    rec['body_unparsable'] = '%s: %s' % (type(exc).__name__, exc)
                    d = {}
                # USAGE IS UNKNOWN WHEN ABSENT, NEVER ZERO.
                # ONE PREDICATE FOR THE ROW AND THE TOTAL. Root, 12:04: "the
                # negative-token actual-main witness now refuses correctly, but
                # its request rows still label completion_tokens=-1 as
                # usage_known=true. Preserve the original value, mark it
                # unusable with a reason, and derive both row and total
                # usability from the same nonnegative, non-boolean integer
                # rule." The aggregate was strict while the row it summarised
                # was not, so the receipt disagreed with itself.
                usage = d.get('usage')
                rec['usage'] = usage                      # original, preserved
                tokens = usage.get('completion_tokens') if isinstance(usage, dict) else None
                rec['usage_known'] = usable_token_count(tokens)
                if not rec['usage_known']:
                    rec['usage_unusable_reason'] = (
                        'no usage object in the response' if not isinstance(usage, dict)
                        else 'completion_tokens %r is not a non-negative, '
                             'non-boolean integer' % (tokens,))
                rec['finish_reason'] = (d.get('choices') or [{}])[0].get('finish_reason')
                rec['content_chars'] = len(
                    ((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '')
            except Exception as exc:                           # noqa: BLE001
                rec['t_ack_monotonic'] = time.monotonic()
                rec['error'] = '%s: %s' % (type(exc).__name__, exc)
                rec['response_received'] = False
                # NOT 'never submitted'. The transport was invoked; whether the
                # server received it cannot be known from this side.
                rec['delivery'] = 'unknown_server_receipt'
                rec['usage_known'] = False
                rec['usage_unusable_reason'] = (
                    'the transport raised (%s), so no usage was returned and '
                    'delivery is unknown' % type(exc).__name__)
            rec['elapsed_s'] = rec['t_ack_monotonic'] - rec['t_send_monotonic']
            results.append(rec)

        threads = [threading.Thread(target=one, args=(i,)) for i in range(2)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=deadline.bounded(REQUEST_CAP_S + 30, use_reserve=True))
    out['submitted_requests'] = submitted_count[0]
    out['transport_attempted_requests'] = attempted_count[0]
    out['requests_with_unknown_delivery'] = sum(
        1 for r in results if r.get('delivery') == 'unknown_server_receipt')
    out['requests'] = sorted(results, key=lambda r: r['index'])
    out.update(summarize_usage(results, token_cap=TOKEN_CAP,
                               expected=len(planned)))

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
        proc.wait(timeout=deadline.bounded(60, use_reserve=True))
    except Exception:                                          # noqa: BLE001
        stopped_cleanly = False
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            out['forced_stop'] = True
        except Exception as exc:                               # noqa: BLE001
            out['forced_stop_error'] = '%s: %s' % (type(exc).__name__, exc)
        try:
            proc.wait(timeout=deadline.bounded(60, use_reserve=True))  # REAP
        except Exception as exc:                               # noqa: BLE001
            out['reap_error'] = '%s: %s' % (type(exc).__name__, exc)
    out['stopped_cleanly'] = stopped_cleanly
    out['child_confirmed_stopped'] = proc.returncode is not None
    out['server_exit_code'] = proc.returncode
    out['wall_seconds_total'] = round(time.monotonic() - t_wall0, 2)
    out['wall_cap_respected'] = out['wall_seconds_total'] <= WALL_CAP_S

    # Join the drain within the deadline, then RETAIN what it collected. A drain
    # that has not finished is reported as unfinished rather than waited on.
    drain_thread.join(timeout=deadline.bounded(DRAIN_JOIN_S, use_reserve=True))
    # DO NOT READ THE CAPTURE WHILE ITS WRITER MAY STILL BE ACTIVE. Root,
    # 10:39: "Do not call `preview_of_artifact`, hash or parse the capture while
    # its drain writer is still active. Check completion first; unresolved
    # capture stays unread with paths/state retained, just as unresolved
    # lifecycle files do." The same rule I applied to the lifecycle log, which I
    # had not applied to my own capture artifact.
    drain_finished = not drain_thread.is_alive()
    out['producer_diagnostics'] = dict(
        (preview_of_artifact(capture_path, capture) if drain_finished else
         {'preview_unavailable': 'the drain writer had not finished, so the '
                                 'capture was not read, hashed or parsed',
          'derived_from': capture.get('artifact')}),
        # TWO DISTINCT STATES, as root decided on 2026-09-23 10:03: a shortened
        # display preview must not invalidate an otherwise complete acquisition,
        # but missing raw capture still must. Only `raw_capture_complete` below
        # enters the verdict; `preview_truncated` never does.
        raw_capture_complete=bool(capture.get('raw_capture_complete')),
        # MEASURED size and hash are forwarded TOGETHER. Root, 11:16: "the
        # actual receipt-construction expression still forwards
        # `bytes_captured` from the old incremental counter while forwarding
        # the newly measured hash. The two-byte witness therefore becomes ZERO
        # BYTES PAIRED WITH THE HASH OF THOSE TWO BYTES."
        measured_bytes=capture.get('measured_bytes'),
        measured_sha256=capture.get('measured_sha256'),
        measured_unavailable=capture.get('measured_unavailable'),
        # read/credited counters, named for what they actually count
        bytes_credited_after_write_return=capture.get('bytes_captured', 0),
        attempted_write_sha256=capture.get('attempted_write_sha256'),
        attempted_equals_measured=capture.get('attempted_equals_measured'),
        bytes_dropped=capture.get('bytes_dropped', 0),
        reached_eof=bool(capture.get('reached_eof')),
        drain_error=capture.get('error'),
        budget_exhausted=bool(capture.get('budget_exhausted')),
        deadline_exhausted=bool(capture.get('deadline_exhausted')),
        byte_budget=DIAGNOSTIC_BYTE_BUDGET,
        drain_thread_finished=not drain_thread.is_alive(),
        artifact=capture.get('artifact'),
        artifact_sha256=capture.get('measured_sha256'),
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
        ('the absolute deadline expired' if deadline.expired() else None),
        ('%d response(s) were not fully retained' % sum(
            1 for r in results if r.get('raw_response')
            and not r['raw_response'].get('complete'))
         if any(r.get('raw_response') and not r['raw_response'].get('complete')
                for r in results) else None),
        ('%d request(s) have unknown server delivery'
         % out.get('requests_with_unknown_delivery', 0)
         if out.get('requests_with_unknown_delivery') else None),
        ('token usage was not measurable for %d request(s), so the token cap '
         'could not be judged' % out.get('requests_with_unknown_usage', 0)
         if out.get('token_cap_respected') is None else None),
        ('the token cap was exceeded' if out.get('token_cap_respected') is False
         else None),
        ('%d request(s) were planned but never submitted'
         % (len(out.get('planned_request_intent') or []) - out.get('submitted_requests', 0))
         if out.get('submitted_requests', 0)
            < len(out.get('planned_request_intent') or []) else None),
    ) if p]
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
    # ELAPSED IS RECORDED AFTER CLEANUP AND BEFORE FINALISATION, as root asked:
    # "record final elapsed time after cleanup/finalization".
    out['deadline'] = deadline.state()
    out['wall_seconds_total'] = round(deadline.elapsed(), 2)
    out['wall_cap_respected'] = not deadline.expired()
    return finalize(out, dest, problems)


if __name__ == '__main__':
    raise SystemExit(main())
