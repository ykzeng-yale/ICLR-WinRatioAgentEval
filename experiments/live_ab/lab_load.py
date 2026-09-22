"""The client-side load DIAGNOSTIC of protocol 3.2 rule 4 -- not its certification.

READ THIS FIRST.  Root's binding design choice of 2026-09-22 02:49
(``reviews/live_load_root_decision_20260922_0237.md``) ruled that what this module
observes is **not** what the coverage contract requires:

    "Dense streamed arrivals do not establish continuous computation between
     arrivals, and socket buffering separates receipt time from production time.
     ... Define the load criterion operationally before collection: TWO DISTINCT
     SERVER-ACKNOWLEDGED DECODING REQUESTS/OCCUPIED DECODING SLOTS THROUGHOUT THE
     VERIFIER INTERVAL, recorded by pinned server-side lifecycle start/end events
     on the same host monotonic clock. ... Client POST-to-response outstanding
     intervals alone do not identify server decoding lifetime. ... Stream
     events/timer lateness can remain diagnostics."

So this module now declares ``evidence_kind = 'client_stream_arrivals'`` and
``certifies_coverage = False``.  ``lab_prepare._coverage_verdict`` refuses to
certify from it.  The instrument is kept because the diagnostic is worth having --
it shows whether traffic was flowing and when it stopped -- **not** because it was
rescued by a tolerance.  The certifying observer reads server-side lifecycle
events; that is a separate instrument.

WHY NO TOLERANCE COULD HAVE SAVED IT
-------------------------------------
The arrival series identifies gaps in **observed arrival traffic**, not gaps in
compute activity.  A server may finish producing before buffered events reach the
client; even with no buffering, output at two instants does not establish activity
throughout the interval between them.  Declaring the maximum gap makes the
assumption explicit but cannot establish it, and replacing the jitter maximum with
a larger constant would not repair the identification problem -- it would only
move it.  This is an instrumentation/design mismatch, not a statistical failure.

WHAT IS STILL TRUE AND USEFUL HERE
-----------------------------------
* ``windows_from_arrivals`` partitions by generation before splitting, so two
  concurrent generations do not destroy each other's windows.  (The first version
  split at every change of generation id, which reported NO ACTIVE LOAD at peak
  load -- silently, in the safe-looking direction.)
* ``classify_stream_chunk`` separates content deltas from the role-only opening
  chunk and the usage/finish closing chunk.  Counting those two as production
  lengthened every window at exactly the two ends where the claim is weakest.
* An UNHEALTHY source now yields no windows.  The flag used to be recorded and
  then ignored, while the docstring claimed an enforcement that did not exist.
* Each ``StreamingHttpLoad`` owns a ``source_id`` and prefixes its generation
  identities with it, so two sources routed into one observer cannot collide.
* ``max_tokens`` is a CAP, not a count: a request may finish earlier, and a
  content chunk may carry more than one token.  ``event_counts`` reports events.

THE ENDPOINT BOUND, AND WHY IT IS NOT OFFERED AS ONE ANY MORE
--------------------------------------------------------------
``JitterProbe`` measures the worst observed lateness of a fixed-schedule wake-up.
Root ruled that neither this empirical maximum nor an arbitrary pre-registered
constant is an accepted endpoint-error guarantee.  It is retained as a diagnostic
of this process's own scheduling, and it is not put forward as a bound on
delivery or observation error.
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

OBSERVATION_SCHEMA = 'live_ab/load_observation-v2'
#: What this instrument produces. NOT the kind that may certify coverage; see
#: lab_prepare.EVIDENCE_SERVER_LIFECYCLE.
EVIDENCE_KIND = 'client_stream_arrivals'
WINDOW_SCHEMA = 'live_ab/load_window-v1'

#: Largest gap between consecutive token arrivals that may sit INSIDE one window.
#: A 1,024-token generation on the coder server produces tokens far faster than
#: this; a gap this large means the server stopped producing, so the window ends.
DEFAULT_MAX_INTERIOR_GAP_S = 0.5

#: Floor under the endpoint error bound.  A measured maximum smaller than this is
#: not believed: a bound of zero would assert that an arrival is stamped at the
#: instant of production.
DEFAULT_ENDPOINT_ERROR_FLOOR_S = 0.010

#: The probe's nominal wake interval, and the fewest samples that may stand
#: behind a bound.  Below this the bound is unmeasured, and an unmeasured bound
#: is not a small one.
JITTER_PROBE_INTERVAL_S = 0.010
MIN_JITTER_SAMPLES = 20

#: Arrivals retained.  At ~40 tokens/s this is over an hour of load; an overflow
#: drops the OLDEST, is counted, and moves ``retained_since`` forward so no window
#: can claim evidence that was discarded.
DEFAULT_RING_CAPACITY = 200_000

#: How old the newest arrival may be before traffic counts as STOPPED.
#: A worker blocked inside ``iter_lines()`` on a server that stopped decoding has
#: neither exited nor recorded an error, so ``healthy()`` read true for up to the
#: request timeout -- 300 s -- while ``observe()`` kept returning windows minutes
#: after the last token. Liveness is a property of the arrivals, not of a thread.
DEFAULT_MAX_ARRIVAL_STALENESS_S = 5.0


class LoadRefused(Exception):
    """The observer cannot stand behind an observation, so it produces none."""


def _finite(x: object) -> Optional[float]:
    try:
        v = float(x)                                    # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ---------------------------------------------------------------------------
# the pure core: arrivals -> windows.  No threads, no clock, no server.
# ---------------------------------------------------------------------------

def windows_from_arrivals(arrivals: Sequence[Tuple[str, float]], *,
                          max_interior_gap_s: float) -> List[Dict[str, Any]]:
    """Split an arrival series into windows of evidenced continuous production.

    ``arrivals`` is ``(generation_id, monotonic_time)`` in arrival order.  The
    series is PARTITIONED BY GENERATION first, and each generation's own arrivals
    are then split wherever they gap by more than ``max_interior_gap_s``.

    Partitioning first is load-bearing, not tidiness.  The trial runs
    ``execution.workers = 2`` episodes, so the load regime is two concurrent
    generations and their arrivals INTERLEAVE: ``g0, g1, g0, g1, ...``.  A rule
    that split at every change of generation id would end every window after one
    arrival and report NO ACTIVE LOAD at the moment the server is busiest --
    silently, and in the safe-looking direction.  Windows from different
    generations may overlap; the consumer unions them, which is what
    ``_coverage_verdict`` already does.

    Two splits that are deliberately conservative:

    * WITHIN a generation, a gap larger than the tolerance splits.  Between two
      distant arrivals the server's state is unobserved, and unobserved is not
      idle-free.
    * A SINGLE arrival produces NO window.  One instant is not an interval, and
      the one place a lone sample could be stretched into one is exactly the
      fabrication this module exists to avoid.
    """
    gap = _finite(max_interior_gap_s)
    if gap is None or gap <= 0:
        raise LoadRefused('max_interior_gap_s must be a finite positive number, '
                          'got %r; a nonpositive tolerance would either split '
                          'every arrival apart or accept any gap at all'
                          % (max_interior_gap_s,))
    by_gid: Dict[str, List[float]] = {}
    order: List[str] = []
    interleave_inversions: List[int] = []
    prev_t: Optional[float] = None
    for i, item in enumerate(arrivals):
        try:
            gid, raw_t = item
        except (TypeError, ValueError):
            raise LoadRefused('arrival %d is not a (generation_id, time) pair: %r'
                              % (i, item)) from None
        t = _finite(raw_t)
        if t is None:
            raise LoadRefused('arrival %d carries a nonfinite timestamp (%r); an '
                              'unusable stamp is not a late one' % (i, raw_t))
        # ORDER IS CHECKED PER GENERATION, NOT GLOBALLY.
        # The global check was wrong for the regime this module exists to serve.
        # Two sources stamp the clock and then append; the two operations are not
        # atomic, so source B can stamp 100.001, source A stamp 100.000, and A
        # append second. The global series then LOOKS inverted although each
        # generation's own stamps are perfectly ordered -- and the whole sweep
        # aborted with a false "not one monotonic clock" diagnosis. Within one
        # generation the stamps come from one thread in order, and that is the
        # claim actually being made.
        if by_gid.get(gid) and t < by_gid[gid][-1]:
            raise LoadRefused('arrivals of generation %r are out of order at index '
                              '%d (%.6f after %.6f); one generation is stamped by '
                              'one thread in order, so this series is not what it '
                              'claims to be' % (gid, i, t, by_gid[gid][-1]))
        if prev_t is not None and t < prev_t:
            interleave_inversions.append(i)
        if gid not in by_gid:
            by_gid[gid] = []
            order.append(gid)
        by_gid[gid].append(t)
        prev_t = t

    runs: List[List[Tuple[str, float]]] = []
    for gid in order:
        times = by_gid[gid]
        run: List[Tuple[str, float]] = [(gid, times[0])]
        for a, b in zip(times, times[1:]):
            if (b - a) > gap:
                runs.append(run)
                run = []
            run.append((gid, b))
        runs.append(run)

    windows: List[Dict[str, Any]] = []
    for run in runs:
        if len(run) < 2:
            continue
        times = [t for _, t in run]
        # A COUNT OF ARRIVALS IS NOT A DURATION. Two arrivals stamped at the same
        # instant satisfied len(run) >= 2 and produced a window with start == end,
        # reported as active load with a 'means' sentence about an interval.
        if times[-1] <= times[0]:
            continue
        interior = max(b - a for a, b in zip(times, times[1:]))
        windows.append({
            'schema': WINDOW_SCHEMA,
            'start': times[0],
            'end': times[-1],
            'generation_id': run[0][0],
            'arrivals': len(run),
            'max_interior_gap_s': interior,
            'evidence': 'consecutive streamed token arrivals on the observer clock',
        })
    return windows


# ---------------------------------------------------------------------------
# what counts as a token, and what does not
# ---------------------------------------------------------------------------

def classify_stream_chunk(text: str) -> tuple:
    """``(kind, is_token_production)`` for one ``data:`` line of an SSE stream.

    Root's reviewer, 2026-09-22: *"Events are not necessarily tokens ... a
    two-line mock response containing only role metadata and an empty
    choices/usage event produced two arrivals."*

    An OpenAI-compatible stream emits, in order:

      * a **role-only** first delta (``{"delta": {"role": "assistant"}}``) when
        the slot is assigned -- before any token has been decoded;
      * ``content`` deltas, one per decoded token or token group;
      * a **finish/usage** chunk after the last token.

    Only the middle kind is evidence of production.  Counting the other two
    lengthens a window at exactly the two ends where the continuity claim is
    weakest, which is why they are excluded here rather than trimmed later.

    Malformed JSON is ``('unparsable', False)``: an event we cannot read is not
    an event we may count.
    """
    payload = text[len('data:'):].strip() if text.startswith('data:') else text.strip()
    if not payload:
        return ('empty', False)
    try:
        obj = json.loads(payload)
    except ValueError:
        return ('unparsable', False)
    if not isinstance(obj, dict):
        return ('unparsable', False)
    choices = obj.get('choices')
    if not isinstance(choices, list) or not choices:
        # usage-only or keep-alive chunks carry no choices at all
        return ('usage_or_metadata', False)
    produced = False
    finished = False
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        if ch.get('finish_reason') not in (None, ''):
            finished = True
        delta = ch.get('delta')
        if isinstance(delta, dict):
            content = delta.get('content')
            if isinstance(content, str) and content != '':
                produced = True
            # A delta carrying ONLY a role is the slot-assignment event.
        text_field = ch.get('text')
        if isinstance(text_field, str) and text_field != '':
            produced = True          # the legacy completions shape
    if produced:
        return ('content', True)
    if finished:
        return ('finish', False)
    return ('role_or_empty_delta', False)


# ---------------------------------------------------------------------------
# the endpoint bound
# ---------------------------------------------------------------------------

class JitterProbe:
    """Worst observed lateness of a fixed-schedule wake-up during the run.

    This is the measured part of the endpoint error bound.  Read the module
    docstring for what it is and is not: an empirical maximum under concurrent
    load, not a proof about the worst case.
    """

    def __init__(self, *, interval_s: float = JITTER_PROBE_INTERVAL_S,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.interval_s = float(interval_s)
        self._clock = clock
        self._sleep = sleep
        self._max_lateness = 0.0
        self._samples = 0
        self._skipped_ticks = 0
        self._degraded: Optional[str] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def samples(self) -> int:
        with self._lock:
            return self._samples

    @property
    def max_lateness_s(self) -> float:
        with self._lock:
            return self._max_lateness

    def _loop(self) -> None:
        started = self._clock()
        k = 1
        while not self._stop.is_set():
            target = started + k * self.interval_s
            delay = target - self._clock()
            if delay > 0:
                self._sleep(delay)
            now = self._clock()
            late = now - target
            with self._lock:
                self._samples += 1
                if late > self._max_lateness:
                    self._max_lateness = late
            # CATCH-UP SKIP. Without it, one stall replays every missed tick with
            # delay <= 0 and no sleep, so a 5 s stall manufactured 200,000
            # 'samples' in 50 ms -- and MIN_JITTER_SAMPLES, which exists to stop
            # an unmeasured bound, was satisfied by the stall itself.
            k += 1
            missed = int((now - target) // self.interval_s)
            if missed > 0:
                k += missed
                with self._lock:
                    self._skipped_ticks += missed

    def start(self, *, reset: bool = False) -> None:
        if self._degraded:
            raise LoadRefused(self._degraded)
        if self._thread is not None:
            raise LoadRefused('the jitter probe is already running')
        if reset:
            # A bound must come from the period it is applied to. Samples carried
            # over from an earlier observation period describe that period.
            with self._lock:
                self._samples = 0
                self._max_lateness = 0.0
                self._skipped_ticks = 0
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='lab_load_jitter',
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop, and REFUSE to pretend the thread is gone when it is not.

        The first version set ``_thread = None`` whether or not the join
        succeeded, so an abandoned thread kept writing the counters while
        ``start()`` happily launched a SECOND probe into the same state.
        """
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                self._degraded = ('the probe thread did not stop within 5 s; its '
                                  'counters are still being written and this probe '
                                  'may not be restarted')
                return
            self._thread = None

    def observe_sample(self, lateness_s: float) -> None:
        """Record a sample directly.  Used by fixtures that drive a fake clock."""
        v = _finite(lateness_s)
        if v is None or v < 0:
            raise LoadRefused('lateness sample must be finite and nonnegative, '
                              'got %r' % (lateness_s,))
        with self._lock:
            self._samples += 1
            if v > self._max_lateness:
                self._max_lateness = v

    def bound(self, *, floor_s: float = DEFAULT_ENDPOINT_ERROR_FLOOR_S) -> Dict[str, Any]:
        """The bound, or a refusal reason -- never a silent default."""
        f = _finite(floor_s)
        if f is None or f < 0:
            raise LoadRefused('endpoint error floor must be finite and '
                              'nonnegative, got %r' % (floor_s,))
        with self._lock:
            n, worst = self._samples, self._max_lateness
        if n < MIN_JITTER_SAMPLES:
            return {'available': False, 'samples': n,
                    'reason': 'the endpoint error bound rests on %d probe sample(s), '
                              'fewer than the %d required; an UNMEASURED bound is '
                              'not a small one and this observation carries no '
                              'certifiable endpoints' % (n, MIN_JITTER_SAMPLES)}
        with self._lock:
            skipped, degraded = self._skipped_ticks, self._degraded
        if degraded:
            return {'available': False, 'samples': n, 'reason': degraded}
        return {
            'available': True,
            'endpoint_error_s': max(f, worst),
            'samples': n,
            'skipped_ticks': skipped,
            'max_observed_lateness_s': worst,
            'floor_s': f,
            'basis': 'empirical maximum lateness of a %.3f s fixed-schedule wake-up '
                     'during this run, floored at %.3f s; an empirical maximum under '
                     'concurrent load, NOT a proven worst case, and it does not bound '
                     'socket buffering' % (self.interval_s, f),
        }


# ---------------------------------------------------------------------------
# arrival sources
# ---------------------------------------------------------------------------

class ScriptedLoad:
    """A fixture source that replays a prescribed arrival series.

    It touches no server and no network, so the observer's decision logic and its
    negative controls are testable on any host, including one whose accelerator
    is occupied.  It is NOT a stand-in for load: an observation built from it
    describes the script, and the receipt that records it says so.
    """

    kind = 'scripted_fixture'

    def __init__(self, script: Sequence[Tuple[str, float]]) -> None:
        self.script = list(script)
        self._sink: Optional[Callable[[str, float], None]] = None

    def start(self, sink: Callable[[str, float], None]) -> None:
        self._sink = sink
        for gid, t in self.script:
            sink(gid, t)

    def stop(self) -> None:
        self._sink = None

    def healthy(self) -> bool:
        return True


class StreamingHttpLoad:
    """The real source: back-to-back streamed generations on the coder server.

    One worker thread issues generations of ``max_tokens`` tokens and stamps the
    monotonic clock as each streamed chunk arrives.  Only the arrival TIME is
    kept; no generated text is retained, because this is a load instrument and
    nothing it produces is scientific data.

    Declared deviation: these load requests set ``stream: true`` while the trial's
    own client sends ``stream: false``.  The offered work is identical; the reply
    transport is not.  See the module docstring.
    """

    kind = 'streaming_http'

    def __init__(self, *, base_url: str, model: str, prompt: str,
                 max_tokens: int = 1024, request_timeout_s: float = 300.0,
                 source_id: Optional[str] = None,
                 clock: Callable[[], float] = time.monotonic,
                 session_factory: Optional[Callable[[], Any]] = None) -> None:
        if not str(base_url).startswith('http://127.0.0.1') and \
                not str(base_url).startswith('http://localhost'):
            # The same loopback restriction lab_client enforces: a load generator
            # that can reach off-host is a policy hole, not a convenience.
            raise LoadRefused('the load generator may only address a loopback '
                              'server, got %r' % (base_url,))
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.prompt = prompt
        self.max_tokens = int(max_tokens)
        self.request_timeout_s = float(request_timeout_s)
        self._clock = clock
        self._session_factory = session_factory
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._errors: List[str] = []
        self._generations = 0
        self._token_events = 0
        self._nontoken_events: Dict[str, int] = {}
        self._lock = threading.Lock()
        # DEFECT 1 OF ROOT'S REVIEW: "StreamingHttpLoad._loop also names its
        # generations gen_000000, etc., with NO PER-SOURCE PREFIX. Two
        # independently instantiated sources routed into one observer would
        # COLLIDE in generation identity unless the composition layer adds a
        # source ID." Correct, and the collision would have been silent: two
        # concurrent lifetimes would have merged into one identity, which is
        # exactly the thing concurrency must count separately. The source owns
        # its identity rather than leaving it to a composition layer that may
        # not exist.
        self.source_id = str(source_id) if source_id else ('src_' + uuid4().hex[:8])

    @property
    def errors(self) -> List[str]:
        with self._lock:
            return list(self._errors)

    @property
    def generations(self) -> int:
        with self._lock:
            return self._generations

    @property
    def event_counts(self) -> Dict[str, Any]:
        """Token-bearing versus non-token stream events, kept apart.

        ``max_tokens`` is a CAP, not a count: a request may finish earlier, and
        the number of content chunks is not the number of tokens either, because
        a chunk may carry more than one. These counters describe events.
        """
        with self._lock:
            return {'content_events': self._token_events,
                    'nontoken_events': dict(self._nontoken_events),
                    'max_tokens_is_a_cap_not_a_count': True}

    def healthy(self) -> bool:
        """False once the worker has stopped or recorded an error.

        An unhealthy source does not silently degrade into a quiet one: the
        observer reports no windows, and no coverage is certified.
        """
        with self._lock:
            if self._errors:
                return False
        return self._thread is not None and self._thread.is_alive()

    def _session(self) -> Any:
        if self._session_factory is not None:
            return self._session_factory()
        import requests                                        # pragma: no cover
        return requests.Session()                              # pragma: no cover

    def _one_generation(self, session: Any, gid: str,
                        sink: Callable[[str, float], None]) -> None:
        body = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': self.prompt}],
            'max_tokens': self.max_tokens,
            'stream': True,
            'temperature': 0.0,
            'seed': 0,
        }
        resp = session.post(self.base_url + '/v1/chat/completions', json=body,
                            stream=True, timeout=self.request_timeout_s)
        status = getattr(resp, 'status_code', None)
        if status is not None and int(status) >= 400:
            raise LoadRefused('load generation %s returned HTTP %s' % (gid, status))
        for line in resp.iter_lines():
            if self._stop.is_set():
                break
            if not line:
                continue
            # Stamp the clock FIRST, before any parsing: the stamp is the
            # measurement and parsing is not part of it.
            t = self._clock()
            text = line.decode('utf-8', 'replace') if isinstance(line, bytes) else str(line)
            if not text.startswith('data:'):
                continue
            if text.strip() == 'data: [DONE]':
                break
            # DEFECT 3 OF ROOT'S REVIEW, 2026-09-22
            # (reviews/live_load_review_20260922_0237.md finding 3): "_one_generation
            # accepts every non-DONE data: line without parsing its contents. A
            # two-line mock response containing only role metadata and an empty
            # choices/usage event produced two 'arrivals'."
            #
            # Correct. An OpenAI-compatible stream opens with a role-only delta
            # (emitted when the slot is assigned, before any token is decoded) and
            # closes with a usage/finish chunk (emitted after the last token). Both
            # were counted as production, which lengthens every window at exactly
            # the two ends where the claim is weakest. Non-token events are now
            # counted SEPARATELY and never reach the sink.
            kind, ok = classify_stream_chunk(text)
            if not ok:
                with self._lock:
                    self._nontoken_events[kind] = self._nontoken_events.get(kind, 0) + 1
                continue
            with self._lock:
                self._token_events += 1
            sink(gid, t)

    def _loop(self, sink: Callable[[str, float], None]) -> None:
        session = self._session()
        index = 0
        while not self._stop.is_set():
            gid = '%s/gen_%06d' % (self.source_id, index)
            try:
                self._one_generation(session, gid, sink)
            except Exception as exc:
                with self._lock:
                    self._errors.append('%s: %s' % (type(exc).__name__, exc))
                return
            with self._lock:
                self._generations += 1
            index += 1

    def start(self, sink: Callable[[str, float], None]) -> None:
        if self._thread is not None:
            raise LoadRefused('the load source is already running')
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(sink,),
                                        name='lab_load_http', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None


# ---------------------------------------------------------------------------
# the observer
# ---------------------------------------------------------------------------

class ContinuousLoadObserver:
    """Produces the observation ``lab_prepare.run_reference_sweep`` requires.

    ``observer.observe`` is the zero-argument callable to pass as
    ``load_observer``.  Every refusal path returns ``active: False`` with a
    reason rather than raising, so the sweep's own immediate-stop rule -- persist
    the raw attempt, then refuse -- keeps its shape; the one exception is a
    malformed arrival series, which means the instrument is broken rather than
    the load absent, and that raises.
    """

    def __init__(self, source: Any, *,
                 max_interior_gap_s: float = DEFAULT_MAX_INTERIOR_GAP_S,
                 endpoint_error_floor_s: float = DEFAULT_ENDPOINT_ERROR_FLOOR_S,
                 jitter: Optional[JitterProbe] = None,
                 ring_capacity: int = DEFAULT_RING_CAPACITY,
                 window_prefix: str = 'load',
                 max_arrival_staleness_s: float = DEFAULT_MAX_ARRIVAL_STALENESS_S,
                 reset_jitter_on_start: bool = False,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.source = source
        self.max_interior_gap_s = float(max_interior_gap_s)
        self.endpoint_error_floor_s = float(endpoint_error_floor_s)
        self.jitter = jitter if jitter is not None else JitterProbe()
        self.ring_capacity = int(ring_capacity)
        if self.ring_capacity < 1:
            raise LoadRefused('ring_capacity must be at least 1, got %r; a '
                              'nonpositive capacity raised IndexError inside the '
                              'arrival sink, corrupting the source instead of '
                              'refusing the configuration' % (ring_capacity,))
        self.window_prefix = str(window_prefix)
        self.max_arrival_staleness_s = float(max_arrival_staleness_s)
        self._reset_jitter_on_start = bool(reset_jitter_on_start)
        self._probe_was_started = False
        self._clock = clock
        self._arrivals: List[Tuple[str, float]] = []
        self._dropped = 0
        self._retained_since: Optional[float] = None
        self._lock = threading.Lock()
        self._started = False

    # -- lifecycle ---------------------------------------------------------
    def _sink(self, gid: str, t: float) -> None:
        with self._lock:
            self._arrivals.append((gid, t))
            if len(self._arrivals) > self.ring_capacity:
                drop = len(self._arrivals) - self.ring_capacity
                self._arrivals = self._arrivals[drop:]
                self._dropped += drop
                self._retained_since = self._arrivals[0][1]

    def start(self) -> None:
        if self._started:
            raise LoadRefused('the observer is already started')
        self._started = True
        # The probe runs for the WHOLE observation period, and for THIS one.
        # The first version started it only when it held fewer than
        # MIN_JITTER_SAMPLES, so a probe carrying samples from an earlier period
        # -- or pre-seeded by a test -- was never started at all and its bound
        # described a different interval entirely.
        self._probe_was_started = False
        if getattr(self.jitter, '_thread', None) is None:
            try:
                self.jitter.start(reset=self._reset_jitter_on_start)
                self._probe_was_started = True
            except LoadRefused:
                pass
        self.source.start(self._sink)

    def stop(self) -> None:
        try:
            self.source.stop()
        finally:
            self.jitter.stop()
            self._started = False

    def __enter__(self) -> 'ContinuousLoadObserver':
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- observation -------------------------------------------------------
    def arrivals(self) -> List[Tuple[str, float]]:
        with self._lock:
            return list(self._arrivals)

    def observe(self) -> Dict[str, Any]:
        """The observation.  ``active`` is True only when a window exists."""
        arrivals = self.arrivals()
        with self._lock:
            dropped, retained_since = self._dropped, self._retained_since
        base: Dict[str, Any] = {
            'schema': OBSERVATION_SCHEMA,
            # ROOT'S BINDING DECISION, 2026-09-22 02:49: client stream arrivals do
            # not identify server decoding lifetime, and no tolerance converts
            # them into it. This observer therefore declares itself a DIAGNOSTIC,
            # and lab_prepare._coverage_verdict refuses to certify coverage from
            # it. The instrument is kept because the diagnostic is worth having,
            # not because it was rescued.
            'evidence_kind': EVIDENCE_KIND,
            'certifies_coverage': False,
            'source_kind': getattr(self.source, 'kind', type(self.source).__name__),
            'max_interior_gap_s_allowed': self.max_interior_gap_s,
            'observed_at_monotonic': self._clock(),
            'arrivals_seen': len(arrivals),
            'arrivals_dropped': dropped,
            'retained_since_monotonic': retained_since,
        }
        healthy = True
        try:
            healthy = bool(self.source.healthy())
        except Exception as exc:                               # pragma: no cover
            healthy = False
            base['source_health_error'] = '%s: %s' % (type(exc).__name__, exc)
        base['source_healthy'] = healthy

        # DEFECT 2 OF ROOT'S REVIEW, 2026-09-22
        # (reviews/live_load_review_20260922_0237.md finding 2): "observe records
        # source_healthy but does not refuse when it is false. A pure offline
        # witness with one scripted generation, five arrivals from 100.0 to 100.4,
        # 20 injected jitter samples, healthy=False, and attempt [100.12, 100.18]
        # yielded active=True and coverage.valid=True. This contradicts the
        # module's claim that unhealthy sources yield no certifiable windows."
        #
        # Exactly right: the flag was recorded and then ignored, and the docstring
        # claimed an enforcement that did not exist -- a check that names what it
        # does not perform. Historical evidence is preserved (the arrivals stay in
        # the ring and the observation still reports them), but an attempt is not
        # described as loaded on the word of a source that has failed.
        if not healthy:
            return dict(base, active=False, active_windows=[],
                        reason='the load source is UNHEALTHY; an interval crossing a '
                               'failed or unresolved source is not described as '
                               'loaded. The arrivals already recorded are retained '
                               'as diagnostics.')

        # A malformed series is a broken instrument, and that is not a quiet
        # server.  It raises, and the sweep's sink turns it into a retained
        # failure record and an immediate stop.
        windows = windows_from_arrivals(
            arrivals, max_interior_gap_s=self.max_interior_gap_s)

        bound = self.jitter.bound(floor_s=self.endpoint_error_floor_s)
        base['endpoint_error_basis'] = bound

        if not bound.get('available'):
            return dict(base, active=False, active_windows=[],
                        reason=bound.get('reason'))
        newest = max((t for _, t in arrivals), default=None)
        now = base['observed_at_monotonic']
        staleness = None if newest is None else (now - newest)
        base['newest_arrival_age_s'] = staleness
        base['max_arrival_staleness_s'] = self.max_arrival_staleness_s
        if staleness is not None and staleness > self.max_arrival_staleness_s:
            return dict(base, active=False, active_windows=[],
                        endpoint_error_s=bound.get('endpoint_error_s'),
                        reason='traffic has STOPPED: the newest arrival is %.3f s '
                               'old, beyond the %.3f s staleness limit. A live '
                               'thread blocked in a read is not a live server.'
                               % (staleness, self.max_arrival_staleness_s))
        if not windows:
            return dict(base, active=False, active_windows=[],
                        endpoint_error_s=bound['endpoint_error_s'],
                        reason='no window of evidenced continuous production exists '
                               '(%d arrival(s), source %s)'
                               % (len(arrivals),
                                  'healthy' if healthy else 'UNHEALTHY'))
        measured = max(w['max_interior_gap_s'] for w in windows)
        if measured > self.max_interior_gap_s:                 # pragma: no cover
            # windows_from_arrivals splits at the tolerance, so this cannot hold.
            # It is asserted rather than assumed because the whole certification
            # rests on it.
            raise LoadRefused('a window exceeds the interior gap tolerance '
                              '(%.6f > %.6f); the splitting rule did not hold'
                              % (measured, self.max_interior_gap_s))
        return dict(
            base,
            active=True,
            active_windows=windows,
            endpoint_error_s=bound['endpoint_error_s'],
            max_interior_gap_s_measured=measured,
            window_id='%s:%s..%s:%d' % (self.window_prefix,
                                        windows[0]['generation_id'],
                                        windows[-1]['generation_id'], len(windows)),
            means='each window is an interval throughout which the server is '
                  'evidenced to have produced output, never idle for longer than '
                  'max_interior_gap_s_measured',
        )


def observation_digest(obs: Dict[str, Any]) -> str:
    """Content digest of an observation, for the freeze bundle."""
    return lab_common.sha256_text(lab_common.canonical_json(obs))
