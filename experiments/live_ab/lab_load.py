"""The continuous-load observer of protocol 3.2 rule 4.

Protocol 3.2 rule 4 requires the reference sweep to run UNDER THE TRIAL'S LOAD
REGIME -- a 1,024-token generation on the coder server.  ``lab_prepare`` already
refuses a sweep that is handed no ``load_observer``, and ``_coverage_verdict``
already decides whether an observation's ``active_windows`` contain an attempt.
Neither of them produced an observation: until this module, the observer was a
parameter with no implementation, so the enforcement was a hole with a gate in
front of it.

WHAT A WINDOW MUST MEAN, AND WHY SAMPLING CANNOT PRODUCE ONE
------------------------------------------------------------
Root, 2026-09-21 21:50: "A series of active samples cannot become proof of
continuous activity merely by shrinking the ends ... A sampler's cadence is not
an endpoint-error bound and says nothing about unobserved interior gaps."

That rules out the easy implementation.  Polling ``/slots`` or ``/metrics`` every
200 ms yields a series of instants at which the server was busy and says nothing
whatever about the 199 ms between them.  No arithmetic applied afterwards repairs
that, and a window built from such samples would be a fabricated interval wearing
a measurement's clothes.

This module therefore observes load through EVIDENCE OF PRODUCTION, not through
samples of state: the load generator issues STREAMED generations, and every token
that arrives is evidence that the server produced output at that moment.  Between
two consecutive arrivals the server's state is unobserved, so the honest claim is
bounded, not absolute:

    "the server was never idle for longer than the largest gap between two
     consecutive token arrivals inside this window"

A window is therefore emitted only while consecutive arrivals stay within
``max_interior_gap_s``; a larger gap SPLITS the window in two rather than being
averaged away.  An attempt that straddles the gap is then not covered, which is
the correct outcome -- during that gap we do not know what the server was doing.

THE ENDPOINT BOUND IS MEASURED, AND ITS LIMIT IS STATED
-------------------------------------------------------
``_coverage_verdict`` contracts every window inward by ``endpoint_error_s``, so
that number must bound how far the true activity interval could lie INSIDE the
reported one.  The reported endpoints are arrival timestamps, and an arrival is
stamped later than the production it evidences -- by the socket delivery and by
this process's own scheduling.

This observer measures the second part: a probe thread wakes on a fixed schedule
throughout the same run and records its worst lateness.  The bound reported is
``max(declared floor, worst observed lateness)``.

BE CLEAR ABOUT WHAT THAT IS.  It is an EMPIRICAL MAXIMUM taken under the same
concurrent load, plus a floor -- not a proof.  It does not bound a kernel stall
longer than any the probe happened to sample, and it does not bound socket
buffering at all.  It is offered as the justification the contract asks for, and
whether it is accepted as one, replaced by a declared constant, or pre-registered
in ``config.json`` is the root session's ruling, not this module's claim.

WHAT IS NOT DECIDED HERE
------------------------
* ``StreamingHttpLoad`` streams its load requests so that arrivals exist to be
  stamped, while the trial's own client (``lab_client``) sends ``stream: false``.
  The WORK offered to the server is the same 1,024-token generation; the
  transport of the reply is not.  That difference is declared, not hidden, and is
  for root to rule on.
* No tolerance here is pre-registered.  ``config.json`` is under the three-way
  verbatim contract and this module does not touch it.
"""

from __future__ import annotations

import math
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

OBSERVATION_SCHEMA = 'live_ab/load_observation-v1'
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
        if prev_t is not None and t < prev_t:
            # The series is produced by one monotonic clock read per arrival, in
            # arrival order.  Out-of-order stamps mean the series is not what it
            # claims to be, and re-sorting it would hide that.
            raise LoadRefused('arrivals are out of order at index %d (%.6f after '
                              '%.6f); this series was not produced by one '
                              'monotonic clock in arrival order' % (i, t, prev_t))
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
            late = self._clock() - target
            with self._lock:
                self._samples += 1
                if late > self._max_lateness:
                    self._max_lateness = late
            k += 1

    def start(self) -> None:
        if self._thread is not None:
            raise LoadRefused('the jitter probe is already running')
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='lab_load_jitter',
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
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
        return {
            'available': True,
            'endpoint_error_s': max(f, worst),
            'samples': n,
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
        self._lock = threading.Lock()

    @property
    def errors(self) -> List[str]:
        with self._lock:
            return list(self._errors)

    @property
    def generations(self) -> int:
        with self._lock:
            return self._generations

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
            sink(gid, t)

    def _loop(self, sink: Callable[[str, float], None]) -> None:
        session = self._session()
        index = 0
        while not self._stop.is_set():
            gid = 'gen_%06d' % index
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
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.source = source
        self.max_interior_gap_s = float(max_interior_gap_s)
        self.endpoint_error_floor_s = float(endpoint_error_floor_s)
        self.jitter = jitter if jitter is not None else JitterProbe()
        self.ring_capacity = int(ring_capacity)
        self.window_prefix = str(window_prefix)
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
        # The probe runs for the whole observation period, not for a calibration
        # burst: the bound must come from the same interval it is applied to.
        if getattr(self.jitter, '_thread', None) is None and \
                self.jitter.samples < MIN_JITTER_SAMPLES:
            try:
                self.jitter.start()
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
