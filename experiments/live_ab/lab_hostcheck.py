"""live_ab host quiescence gate: detect FOREIGN accelerator consumers on the serving host.

protocol_FINAL.md 5.7 requires "no other GPU job" for the duration of a trial.  The harness
enforced that with an exclusive lock file, which only excludes a second instance of THIS
harness; a model server belonging to a different project on the same machine was invisible
to it.  That gap is not cosmetic.  The frozen hierarchy is success > cost with
cost = latency_s, and when the two arms tie on success the whole composite effect rides on
the latency tier, so a foreign accelerator load silently corrupts the primary endpoint.

This module OBSERVES AND REPORTS ONLY.  It never sends a control instruction of any kind to
any process it finds: no termination, no suspension, no priority change.  The operator
decides what to do about an offender.  tests_lab_hostcheck.py asserts that property against
this file's own source, both at the syntax-tree level and at the token level, and also
asserts that the only external programs named anywhere in the file are `ps` and `lsof`.
(One precise caveat, PREREG_CHECK C.1: `subprocess.run(..., timeout=...)` kills the child
IT STARTED when the timeout expires, so the `ps`/`lsof` readers this module spawns can be
killed by the standard-library timeout path.  No process this module FINDS is ever
signalled, which is the property the tests enforce.)

WHAT A SCAN REPORTS, AND WHAT IT DOES NOT ESTABLISH (PREREG_CHECK C.3; COORDINATOR_DECISIONS
ruling 31(e); reviews/arxiv_baseline_daemon_policy_review.md clarification 3).  Read this
before writing any sentence claiming that "no other GPU job" is enforced.  A scan reports
what the detector saw at the instants it looked, and nothing beyond that.  The single
statement a scan supports is this one:

    At the recorded scans, the detector reported no non-baseline process satisfying the
    frozen detection criteria above the frozen resident-size floor, and every frozen
    baseline process it did find is recorded with its measured CPU delta.

That is a report about a detector at a few instants, not a description of the machine
between them.  In particular, the CPU-time deltas of the baseline activity test measure
CPU ACTIVITY; they do NOT establish accelerator activity, and they do not establish
accelerator inactivity.  A process can keep the GPU saturated while accumulating almost no
CPU time, and a process can burn CPU while touching no accelerator at all.  Nothing in this
module, in tests_lab_hostcheck.py or in protocol 5.7 may turn a scan into a statement that
the machine was doing no accelerator work, and no report may promote a scan into a claim of
continuous accelerator isolation over the trial window.

A scan reports a foreign accelerator consumer when, and only when, one of these holds:

  * the command names a known runner by exact token (RUNNER_TOKENS: llama-server,
    llama-cli, mlx_lm, ollama, vllm and spelling variants), or
  * the command is a python interpreter and the process holds ANY open Metal resource, or
  * the process is above PROBE_RSS_FLOOR_BYTES and holds a COMPUTE-class Metal resource
    (METAL_COMPUTE_RE: the ggml Metal backend, Metal Performance Shaders, MLX).

It therefore DOES detect a copy of `llama-server` renamed to anything at all, because a
rename does not change which Metal libraries the process opens.  It does NOT detect:

  * an accelerator job whose resident size is below PROBE_RSS_FLOOR_BYTES;
  * a job that drives the GPU through raw Metal only, linking neither ggml, MPS nor MLX
    (such a process is indistinguishable, by open files alone, from a window-drawing GUI
    application: measured on the serving host, two ordinary desktop applications map
    AGXMetal while performing no accelerator work, which is why a bare display-class
    marker on a non-python process is deliberately NOT a finding);
  * anything on a process the scan could not read.  That last case is never silence: it
    becomes a `degraded` marker and the preflight refuses.

FAILING CLOSED (PREREG_CHECK C.2).  When the Metal probe cannot run -- `lsof` absent, a
non-zero exit this module cannot attribute to a process that has simply exited, a timeout,
an OSError -- and there was at least one process it needed to interrogate, the scan records
a `degraded` marker naming the cause and `preflight_host_quiescent` RAISES.  An unprovable
host is not a clean host.  An empty `findings` list means "nothing found" only when
`degraded` is also empty.

THE FROZEN BASELINE ALLOWANCE (COORDINATOR_DECISIONS ruling 31, revision 8, which withdrew
and replaced BOTH the identity-only allowlist of ruling 28 and the refuse-on-possession
option of ARCHITECTURE_FINAL 3.17.1).  Two kinds of accelerator consumer are treated
differently, and the difference is measured rather than assumed:

  * 31(a) a NON-BASELINE consumer -- another experiment, another project, a user's model
    server -- REFUSES ON PRESENCE.  There is no activity test for it and no override.  A
    loaded model server exists in order to be used.
  * 31(b) a BASELINE process is one whose argv[0] is EXACTLY EQUAL to an entry of the
    frozen, closed list BASELINE_EXECUTABLES.  It refuses only when it is ACTIVE by a test
    fixed in advance: cumulative CPU time sampled at t and t + BASELINE_ACTIVITY_INTERVAL_S
    seconds, active iff the delta exceeds BASELINE_ACTIVITY_THRESHOLD_MS milliseconds of
    CPU time.  Idle-but-resident is recorded and does not refuse.
  * 31(d) every baseline process the scan finds is recorded at EVERY scan, active or not,
    with its elapsed time, resident size and CPU delta, so that `clean` is never a bare
    assertion a reader has to take on trust.

`match_baseline` is the whole identity rule and it is deliberately unforgiving: EXACT
string equality against a resolved absolute executable path, argv[0] only, never a
basename, never a substring, never a directory or framework prefix, and every entry must
additionally sit under BASELINE_PATH_PREFIX so that no user-writable path can ever be added
to the list.  `reviews/arxiv_baseline_daemon_policy_review.md` clarification 1 rejected the
blanket `/System/` prefix of ruling 28 for exactly this reason: a prefix exempts an entire
directory tree including binaries nobody has looked at.  A baseline daemon reached through
a wrapper, a symlink or a copy does NOT match, and therefore refuses like any other
non-baseline consumer.  That is the conservative direction of error, chosen on purpose.

An activity measurement that could not be taken is UNKNOWN, never zero (clarification 2).
`ACTIVITY_UNKNOWN` degrades the scan and the preflight refuses, so no baseline process is
ever admitted on the strength of a measurement that did not happen.  A baseline process
that exited between the two samples is `ACTIVITY_EXITED`: it is no longer contending, so
that case records itself and does not degrade the scan.

The policy is frozen BEFORE any trial and is bound by the freeze bundle, whose hash covers
every file under `experiments/live_ab/` (protocol 14.2), so these constants cannot move
without moving the bundle hash and invalidating the preflight.  `baseline_policy()` returns
the same facts as a JSON-able object for deposit in the freeze deliverable.  Per 31(f) the
thresholds are NOT tuned after a refusal: if this rule ever blocks a trial, the trial waits
and the rule stays where it is.

Identifier safety.  A finding is written into the public hash chain, so it must not carry an
account name, a home directory, a foreign project's directory names or a remote address.
Every finding therefore reduces the offending command to (a) a sha256 digest of the exact
argv text, which lets an operator confirm a match locally without the text ever being
published, and (b) a short summary whose every token is either a conservative label or a
placeholder drawn from a closed vocabulary.  `summary_is_identifier_safe` is the predicate,
it is applied by the builder itself, and anything that fails it becomes `<REDACTED>`.
That vocabulary is closed for paths and addresses but NOT for bare literals (C.6): a token
that is neither a path nor an address survives verbatim, so a foreign project's module name
or a model's relative filename can appear in a summary.  For that reason `chain_finding`
publishes the DIGEST of the summary into the event chain and keeps the token list itself
local to the operator's view.

Standard library only, plus lab_common for the shared digest and path vocabulary.
"""
from __future__ import annotations

import getpass
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import lab_common

# ---------------------------------------------------------------------------
# what counts as a foreign accelerator consumer
# ---------------------------------------------------------------------------
# Runner name -> detector label.  Matching is by EXACT token, never by substring: a
# substring rule reports `vim <dir>/ollama-notes/x.txt` as an accelerator job, and a gate
# that cries wolf on a text editor is a gate an operator learns to bypass.
RUNNER_TOKENS: dict[str, str] = {
    'llama-server': 'llama-server', 'llama_server': 'llama-server',
    'llama-cli': 'llama-cli', 'llama_cli': 'llama-cli',
    'mlx_lm': 'mlx-lm', 'mlx-lm': 'mlx-lm',
    'ollama': 'ollama',
    'vllm': 'vllm',
}

METAL_PYTHON_LABEL = 'metal-python'
METAL_PROCESS_LABEL = 'metal-process'
# A frozen baseline process that FAILED the activity test of ruling 31(b).  It is the only
# way a baseline identity becomes a refusal, and it is a finding like any other.
BASELINE_ACTIVE_LABEL = 'baseline-active'

# Every detector label this module can emit.  lab_eventlog transcribes this list into
# E_HOST_DETECTOR so a finding entering the chain carries a closed-vocabulary label, and
# tests_lab_hostcheck asserts the two lists agree.
DETECTOR_LABELS: tuple[str, ...] = tuple(sorted(
    set(RUNNER_TOKENS.values())
    | {METAL_PYTHON_LABEL, METAL_PROCESS_LABEL, BASELINE_ACTIVE_LABEL}))

# ---------------------------------------------------------------------------
# the frozen baseline allowance (COORDINATOR_DECISIONS ruling 31)
# ---------------------------------------------------------------------------
# THE CLOSED LIST.  Exact resolved absolute executable paths, one per entry, mapped to the
# closed-vocabulary label under which the entry is recorded in the chain.  Clarification 1
# of reviews/arxiv_baseline_daemon_policy_review.md rejects a blanket `/System/` or
# framework-directory prefix and a name-only match, so this is neither: it is an equality
# test against a path that was read off the serving host.
#
# The single entry was resolved on the serving host on 2026-09-20 with
# `ps -axo pid=,ppid=,etime=,time=,rss=,command=`:
#     pid 39197  elapsed 09:22:45  cumulative CPU 19:27.70  rss 372448 KiB
#     /System/Library/PrivateFrameworks/MediaAnalysis.framework/Versions/A/mediaanalysisd
# The same scan shows a DIFFERENT binary whose basename contains the same word,
#     /System/Library/PrivateFrameworks/MediaAnalysisAccess.framework/Versions/A/
#     XPCServices/mediaanalysisd-access.xpc/Contents/MacOS/mediaanalysisd-access
# which is NOT on this list, does NOT match, and therefore refuses on presence like any
# other consumer.  A name-only or prefix rule would have admitted it silently.
BASELINE_EXECUTABLES: dict[str, str] = {
    '/System/Library/PrivateFrameworks/MediaAnalysis.framework/Versions/A/mediaanalysisd':
        'mediaanalysisd',
}

# Every entry must live under this prefix.  This is a second lock on the LIST, not a
# matching rule for a process: it is what stops a user-writable path from ever being added.
# A test asserts it over every entry.
BASELINE_PATH_PREFIX = '/System/'

# The closed vocabulary of baseline labels, transcribed into lab_eventlog's E_HOST_BASELINE.
BASELINE_IDS: tuple[str, ...] = tuple(sorted(set(BASELINE_EXECUTABLES.values())))

# ---- the activity test, frozen per ruling 31(b) and (f) --------------------
# Cumulative CPU time sampled at t and t + BASELINE_ACTIVITY_INTERVAL_S; active iff the
# delta EXCEEDS BASELINE_ACTIVITY_THRESHOLD_MS (strict >, so exactly 0.5 CPU-seconds is
# idle).  NORMALIZATION: none.  The quantity is the raw difference of the cumulative CPU
# time `ps` reports for the process, summed over its threads, in milliseconds.  It is NOT
# divided by the sampling interval, NOT divided by the core count and NOT expressed as a
# percentage, so a multi-threaded process can legitimately show a delta larger than the
# interval.  The measurement that decided the rule (COORDINATOR_DECISIONS revision 8) was
# taken in exactly these units: mediaanalysisd held a compute-class Metal resource with a
# cumulative CPU time that did not move at all across three samples.
BASELINE_ACTIVITY_INTERVAL_S = 10
BASELINE_ACTIVITY_THRESHOLD_MS = 500

# A second sample taken too soon is not the frozen measurement, and a short interval could
# make a busy process look idle.  Below this measured wall interval the sample is discarded
# as UNKNOWN rather than believed.  80% of the frozen interval.
BASELINE_MIN_INTERVAL_MS = 8000

# ---- what the activity test can say ---------------------------------------
# A closed four-value vocabulary.  There is deliberately no boolean here: a boolean would
# have to render an unmeasured process as `false`, which is the one thing clarification 2
# forbids ("an unavailable measurement is unknown, not zero activity").
ACTIVITY_ACTIVE = 'active'      # delta > threshold over a valid interval: REFUSES
ACTIVITY_IDLE = 'idle'          # delta <= threshold over a valid interval: recorded only
ACTIVITY_EXITED = 'exited'      # gone by the second sample: not contending, not degraded
ACTIVITY_UNKNOWN = 'unknown'    # not measured: degrades the scan, so the preflight refuses
BASELINE_ACTIVITY_VALUES: tuple[str, ...] = (
    ACTIVITY_ACTIVE, ACTIVITY_EXITED, ACTIVITY_IDLE, ACTIVITY_UNKNOWN)

# ---- the frozen scan cadence (ruling 31(c)) --------------------------------
# The activity test runs at trial start AND at every quiescent scrape, which are exactly
# the points at which the orchestrator scans the host at all: the hard gate immediately
# before a trial chain is opened, then `World.host_scan` at these two scrape points.  A
# scan that finds no baseline accelerator consumer runs no activity test and costs nothing;
# a scan that finds one pays BASELINE_ACTIVITY_INTERVAL_S seconds, once, at that point.
SCAN_POINTS: tuple[str, ...] = ('trial_start', 'quiescent')

# THE TRIAL-OVERLAP FLAG, frozen here so that it is a reading rule and not a judgement call.
# A trial's window overlaps materially active baseline load if and only if that trial's own
# chain carries a `foreign_load_detected` record whose `baseline_active` is true.  The
# structure decides it: a trial chain exists only while its trial is running, so every
# record on it is inside the window, while the pre-trial gate's refusal lives on the PROGRAM
# chain as `host_quiescence_refused` and belongs to a trial that never opened.  Nothing has
# to be inferred from a timestamp.
TRIAL_OVERLAP_RULE = 'foreign_load_detected_on_trial_chain_with_baseline_active'

# ---- the two Metal marker families ----------------------------------------
# COMPUTE class: an open resource that a process doing accelerator WORK maps.  ggml is the
# llama.cpp backend (and survives any rename of the binary), MPS is Metal Performance
# Shaders, mlx is the MLX runtime.  Measured on the serving host: of six processes above
# the RSS floor holding some Metal resource, exactly the llama.cpp server and Apple's
# media-analysis daemon matched this family, and both are genuine GPU compute consumers.
METAL_COMPUTE_RE = re.compile(
    r'libggml-metal|ggml-metal|MetalPerformanceShaders|MPSCore|MPSNDArray'
    r'|libmlx|mlx\.metallib',
    re.IGNORECASE)

# DISPLAY class: mapped by any window-drawing application as well.  Measured on the same
# host: two ordinary desktop applications map AGXMetal while doing no accelerator work.
# Presence of a display marker ALONE is evidence only on a python interpreter, which has no
# business drawing a window on a serving host.
METAL_DISPLAY_RE = re.compile(
    r'AGXMetal|/com\.apple\.metal/|Metal\.framework|MTLCompiler|\.metallib',
    re.IGNORECASE)

# Any Metal resource at all.  Kept under the original name because it is the predicate the
# python arm of the scan uses, which is the arm whose behaviour is unchanged.
METAL_NAME_RE = re.compile(
    f'{METAL_COMPUTE_RE.pattern}|{METAL_DISPLAY_RE.pattern}', re.IGNORECASE)

_PYTHON_BASENAME_RE = re.compile(r'^python[0-9._]*$', re.IGNORECASE)

# A non-python, non-allowlisted process at or above this resident size is interrogated with
# lsof too, so that a RENAMED accelerator binary cannot walk past the name list (C.3).  The
# floor keeps the probe affordable: measured on the serving host, 956 processes were
# running and 16 stood at or above 128 MiB, well inside MAX_LSOF_PIDS.
PROBE_RSS_FLOOR_BYTES = 128 * 1024 * 1024

# Bound on how many processes we will interrogate with lsof in one scan.  A host with more
# candidates than this is reported as degraded rather than silently under-scanned: see
# ScanResult.degraded.
MAX_LSOF_PIDS = 96
PS_TIMEOUT_S = 20
LSOF_TIMEOUT_S = 30

# ---- degraded causes ------------------------------------------------------
# The closed vocabulary of reasons a scan could not establish quiescence.  A raw marker
# carries a count (`lsof-unlisted-3`); `degraded_causes` folds the markers into
# {cause, count} records, which is the only form that enters the event chain.
CAUSE_PS_UNAVAILABLE = 'ps_unavailable'
CAUSE_PS_LINE_UNPARSED = 'ps_line_unparsed'
CAUSE_LSOF_UNAVAILABLE = 'lsof_unavailable'
CAUSE_LSOF_TIMEOUT = 'lsof_timeout'
CAUSE_LSOF_FAILED = 'lsof_failed'
CAUSE_LSOF_INCOMPLETE = 'lsof_incomplete'
CAUSE_PROBE_BUDGET = 'probe_budget_exhausted'
CAUSE_SCAN_ERROR = 'scan_error'
# ruling 31(b) with clarification 2: the activity test of at least one baseline process
# could not be taken, so its activity is UNKNOWN.  Unknown is not idle, so this degrades
# the scan and the preflight refuses.
CAUSE_BASELINE_UNMEASURED = 'baseline_unmeasured'

DEGRADED_CAUSES: tuple[str, ...] = (
    CAUSE_PS_UNAVAILABLE, CAUSE_PS_LINE_UNPARSED, CAUSE_LSOF_UNAVAILABLE,
    CAUSE_LSOF_TIMEOUT, CAUSE_LSOF_FAILED, CAUSE_LSOF_INCOMPLETE,
    CAUSE_PROBE_BUDGET, CAUSE_BASELINE_UNMEASURED, CAUSE_SCAN_ERROR)

# marker prefix -> cause.  Longest prefix wins, and an unrecognised marker maps to
# CAUSE_SCAN_ERROR rather than being dropped: a marker we cannot classify is still a
# failure to establish quiescence.
_MARKER_CAUSES: tuple[tuple[str, str], ...] = (
    ('ps-unavailable', CAUSE_PS_UNAVAILABLE),
    ('short-line-fields', CAUSE_PS_LINE_UNPARSED),
    ('unparsed-fields', CAUSE_PS_LINE_UNPARSED),
    ('lsof-unavailable', CAUSE_LSOF_UNAVAILABLE),
    ('lsof-timeout', CAUSE_LSOF_TIMEOUT),
    ('lsof-unlisted', CAUSE_LSOF_INCOMPLETE),
    ('lsof-exit', CAUSE_LSOF_FAILED),
    ('lsof-failed', CAUSE_LSOF_FAILED),
    ('probe-budget', CAUSE_PROBE_BUDGET),
    ('baseline-unmeasured', CAUSE_BASELINE_UNMEASURED),
)


# ---------------------------------------------------------------------------
# exception
# ---------------------------------------------------------------------------
class HostNotQuiescent(lab_common.PreflightError):
    """The host is not in the state protocol_FINAL.md 5.7 requires, or the check could not
    prove that it is.  `findings` is the structured, identifier-safe evidence."""

    def __init__(self, message: str, findings: list[dict] | None = None,
                 degraded: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.findings = list(findings or [])
        self.degraded = tuple(degraded)


# ---------------------------------------------------------------------------
# the process table
# ---------------------------------------------------------------------------
PS_ARGV: tuple[str, ...] = ('ps', '-axo', 'pid=,ppid=,etime=,time=,rss=,command=')

# The SECOND sample of the baseline activity test (ruling 31(b)).  It asks for nothing but
# the pid and the cumulative CPU time, because that is all the test needs and because a
# second full command-line read would be a second copy of every foreign argv in memory.
PS_CPU_ARGV: tuple[str, ...] = ('ps', '-axo', 'pid=,time=')

# macOS ps renders elapsed time as [[DD-]HH:]MM:SS.  `etimes` (plain seconds) is a GNU
# extension and is NOT available here, which this module verified on the target host.
_ETIME_RE = re.compile(r'^(?:(\d+)-)?(?:(\d{1,3}):)?(\d{1,2}):(\d{2})$')

# The TIME column is CUMULATIVE CPU time and its minutes field does NOT roll over into
# hours on this platform: measured on the serving host, launchd showed `499:33.14` and
# another daemon `839:44.16`, both well past 60 minutes.  The optional day and hour groups
# are accepted anyway so that a platform which does roll over is read correctly, and the
# minutes bound of `_ETIME_RE` is deliberately NOT applied here.
_CPUTIME_RE = re.compile(r'^(?:(\d+)-)?(?:(\d+):)?(\d+):(\d{2})(?:\.(\d{1,2}))?$')


@dataclass(frozen=True)
class ProcRow:
    """One parsed line of the process table.  `command` is the raw, UNREDACTED text; it
    never leaves this process except as a digest or as a redacted summary.

    `cpu_ms` is the cumulative CPU time of the process in milliseconds, the FIRST sample of
    the baseline activity test, and it is None when the TIME field could not be read.  None
    is not zero: a baseline process whose first sample is None is reported UNKNOWN and the
    scan degrades."""
    pid: int
    ppid: int
    elapsed_s: int
    rss_bytes: int
    command: str
    cpu_ms: int | None = None


def parse_etime(text: str) -> int | None:
    """[pure] '02:03', '01:02:03' or '58-02:38:46' -> elapsed whole seconds; None if the
    field is not in a form this module recognises."""
    m = _ETIME_RE.match(text.strip())
    if m is None:
        return None
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3))
    seconds = int(m.group(4))
    if minutes > 59 or seconds > 59:
        return None
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_cputime(text: str) -> int | None:
    """[pure] A `ps` TIME field -> cumulative CPU MILLISECONDS; None if unreadable.

    '0:00.00' -> 0, '19:27.70' -> 1167700, '499:33.14' -> 29973140, '1-02:03:04' -> a day
    and change.  The fractional field is hundredths of a second, so '.7' is 700 ms and
    '.07' is 70 ms."""
    m = _CPUTIME_RE.match(text.strip())
    if m is None:
        return None
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3))
    seconds = int(m.group(4))
    if seconds > 59 or (m.group(2) is not None and minutes > 59):
        return None
    hundredths = int((m.group(5) or '0').ljust(2, '0'))
    whole = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return whole * 1000 + hundredths * 10


def parse_ps_table(text: str) -> tuple[list[ProcRow], list[str]]:
    """[pure] Parse the output of PS_ARGV.

    Returns (rows, malformed) where `malformed` holds a SHORT, redacted marker for every
    non-empty line that could not be parsed.  Callers must treat a non-empty `malformed`
    as a failure to establish quiescence rather than as an absence of offenders: a line we
    cannot read is exactly where an offender would hide."""
    rows: list[ProcRow] = []
    malformed: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            malformed.append(f'short-line-fields-{len(parts)}')
            continue
        pid_s, ppid_s, etime_s, cpu_s, rss_s, command = parts
        elapsed = parse_etime(etime_s)
        if not (pid_s.isdigit() and ppid_s.isdigit() and rss_s.isdigit()) or elapsed is None:
            # The marker names the shape of the failure, never the command text.
            malformed.append(f'unparsed-fields-pid-{pid_s if pid_s.isdigit() else "nan"}')
            continue
        # An unreadable TIME field does NOT discard the row: the row is still usable for
        # every detection rule, and the missing CPU sample only matters if this process
        # turns out to be a baseline identity, where it becomes ACTIVITY_UNKNOWN.
        rows.append(ProcRow(pid=int(pid_s), ppid=int(ppid_s), elapsed_s=elapsed,
                            rss_bytes=int(rss_s) * 1024, command=command,
                            cpu_ms=parse_cputime(cpu_s)))
    return rows, malformed


def parse_cpu_table(text: str) -> dict[int, int]:
    """[pure] Parse the output of PS_CPU_ARGV -> {pid: cumulative CPU milliseconds}.

    A line whose pid or TIME field cannot be read is dropped rather than guessed at, which
    leaves the pid absent from the map; the caller turns an absent pid into
    ACTIVITY_UNKNOWN or ACTIVITY_EXITED, never into zero activity."""
    out: dict[int, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        cpu_ms = parse_cputime(parts[1])
        if cpu_ms is not None:
            out[int(parts[0])] = cpu_ms
    return out


def read_process_table(*, timeout_s: int = PS_TIMEOUT_S) -> str:
    """Run `ps`.  Returns its stdout, or '' if it could not be run or failed."""
    try:
        done = subprocess.run(list(PS_ARGV), capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return ''
    if done.returncode != 0:
        return ''
    return done.stdout.decode('utf-8', 'replace')


# ---------------------------------------------------------------------------
# the baseline activity test (ruling 31(b))
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActivitySample:
    """The SECOND sample of the activity test, with its measured interval.

    `cpu_ms` maps pid -> cumulative CPU milliseconds at the second sample.  `interval_ms`
    is the wall time actually elapsed between the two samples, measured on the monotonic
    clock and recorded so that a reader can see the measurement really spanned the frozen
    interval.  `failure` is a marker when the second sample could not be taken at all; the
    caller then reports every baseline process as ACTIVITY_UNKNOWN and degrades the scan."""
    cpu_ms: Mapping[int, int] = field(default_factory=dict)
    interval_ms: int = 0
    failure: str | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None and self.interval_ms >= BASELINE_MIN_INTERVAL_MS


def probe_baseline_activity(*, interval_s: int = BASELINE_ACTIVITY_INTERVAL_S,
                            timeout_s: int = PS_TIMEOUT_S) -> ActivitySample:
    """Wait `interval_s` seconds and read the cumulative CPU times again.

    The wait is this scan's OWN wait: it is the measurement interval of ruling 31(b), and
    it is the only thing in this module that takes time on purpose.  Nothing is sent to any
    process while it passes -- this module observes, and a waiting observer is still an
    observer.  The cost is paid once per scan, and only on a scan that actually found a
    baseline accelerator consumer to measure."""
    started = time.monotonic()
    try:
        time.sleep(interval_s)
        done = subprocess.run(list(PS_CPU_ARGV), capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return ActivitySample(failure='baseline-unmeasured-ps')
    elapsed_ms = int((time.monotonic() - started) * 1000)
    if done.returncode != 0:
        return ActivitySample(interval_ms=elapsed_ms, failure='baseline-unmeasured-exit')
    table = parse_cpu_table(done.stdout.decode('utf-8', 'replace'))
    if not table:
        return ActivitySample(interval_ms=elapsed_ms, failure='baseline-unmeasured-empty')
    return ActivitySample(cpu_ms=table, interval_ms=elapsed_ms)


def classify_activity(row: ProcRow, sample: ActivitySample) -> tuple[str, int]:
    """[pure] One baseline process and the second sample -> (activity, cpu_delta_ms).

    The frozen rule of 31(b), and nothing else: active iff the delta EXCEEDS
    BASELINE_ACTIVITY_THRESHOLD_MS over an interval that really lasted at least
    BASELINE_MIN_INTERVAL_MS.  Every path that cannot produce that number returns
    ACTIVITY_UNKNOWN with a delta of 0, and the 0 is a filler for a field that must hold an
    int -- it is NOT a measurement, which is why the activity value beside it says so."""
    if sample.failure is not None or sample.interval_ms < BASELINE_MIN_INTERVAL_MS:
        return ACTIVITY_UNKNOWN, 0
    if row.cpu_ms is None:
        return ACTIVITY_UNKNOWN, 0
    later = sample.cpu_ms.get(row.pid)
    if later is None:
        # Absent from the second sample.  A process that is gone is not contending for the
        # accelerator, so this records itself and does not degrade the scan.
        return ACTIVITY_EXITED, 0
    delta = later - row.cpu_ms
    if delta < 0:
        # Cumulative CPU time cannot fall.  Something is wrong with the pairing (a reused
        # pid, a thread-accounting anomaly), so the measurement is not believed.
        return ACTIVITY_UNKNOWN, 0
    if delta > BASELINE_ACTIVITY_THRESHOLD_MS:
        return ACTIVITY_ACTIVE, delta
    return ACTIVITY_IDLE, delta


def baseline_record(row: ProcRow, baseline_id: str, sample: ActivitySample, *,
                    now: float | None = None) -> dict:
    """[pure given `now`] The chain-ready record of ONE frozen baseline process.

    Ruling 31(d): this is written at every scan whether the process is active or not, so
    that a reader sees what shared the host instead of taking a bare `clean` on trust.
    Every value is an int, a closed-vocabulary label or a digest; the executable path is
    NOT published, because `baseline_id` already names the frozen entry it matched and the
    argv digest lets an operator confirm the match locally."""
    stamp = time.time() if now is None else now
    activity, delta_ms = classify_activity(row, sample)
    return {
        'pid': row.pid,
        'ppid': row.ppid,
        'baseline_id': baseline_id,
        'start_utc': _iso_utc(stamp - row.elapsed_s),
        'elapsed_s': row.elapsed_s,
        'rss_bytes': row.rss_bytes,
        'cpu_delta_ms': delta_ms,
        'interval_ms': int(sample.interval_ms),
        'activity': activity,
        'argv_sha256': lab_common.sha256_text(row.command),
    }


def baseline_policy() -> dict:
    """[pure] The frozen baseline policy as a JSON-able object, for deposit in the freeze
    bundle (protocol 5.7.2, freeze deliverable 14.2).

    The bundle hash already covers every file under `experiments/live_ab/`, so these
    constants are bound by the freeze whether or not this object is deposited; the object
    exists so that a reader of the freeze does not have to read the source to see which
    identities were allowed and at what threshold."""
    return {
        'executables': [{'path': path, 'baseline_id': BASELINE_EXECUTABLES[path]}
                        for path in sorted(BASELINE_EXECUTABLES)],
        'match_rule': 'argv0_exact_absolute_path',
        'path_prefix_required': BASELINE_PATH_PREFIX,
        'activity_interval_s': BASELINE_ACTIVITY_INTERVAL_S,
        'activity_threshold_ms': BASELINE_ACTIVITY_THRESHOLD_MS,
        'activity_min_interval_ms': BASELINE_MIN_INTERVAL_MS,
        'activity_normalization': 'none_raw_cumulative_cpu_ms_delta',
        'activity_values': list(BASELINE_ACTIVITY_VALUES),
        'rss_floor_bytes': PROBE_RSS_FLOOR_BYTES,
        'scan_points': list(SCAN_POINTS),
        'trial_overlap_rule': TRIAL_OVERLAP_RULE,
        'non_baseline_rule': 'refuse_on_presence_no_activity_test_no_override',
        'unmeasured_rule': 'unknown_degrades_and_refuses',
        'newly_detected_load_rule': 'record_disclose_preserve_enrolment_never_adjust',
    }


# ---------------------------------------------------------------------------
# allowlist
# ---------------------------------------------------------------------------
def descendants_of(rows: list[ProcRow], seeds: set[int]) -> set[int]:
    """[pure] `seeds` plus every process reachable from a seed through ppid edges.

    The harness allowlists the pids it started.  A server it started through a shell has
    the shell's pid in the allowlist and its own pid nowhere, so without this closure the
    gate would report the harness's own server as a foreign one."""
    children: dict[int, list[int]] = {}
    for row in rows:
        children.setdefault(row.ppid, []).append(row.pid)
    seen = set(seeds)
    stack = list(seeds)
    while stack:
        pid = stack.pop()
        for child in children.get(pid, ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def own_pid_allowlist(caller_pids: set[int] | None, rows: list[ProcRow], *,
                      include_descendants: bool = True) -> set[int]:
    """[pure] The full set of pids this scan must ignore: the caller's declared pids, this
    interpreter, and (by default) everything descended from them."""
    seeds = set(caller_pids or set())
    seeds.add(os.getpid())
    if not include_descendants:
        return seeds
    return descendants_of(rows, seeds)


# ---------------------------------------------------------------------------
# identifier-safe command summary
# ---------------------------------------------------------------------------
PLACEHOLDER_REDACTED = '<REDACTED>'
PLACEHOLDER_PATH = '<PATH>'
PLACEHOLDER_SYS = '<SYS>'
PLACEHOLDER_REMOTE = '<REMOTE>'
PLACEHOLDER_TRUNCATED = '<TRUNCATED>'
PLACEHOLDER_USER = '<USER>'

# Placeholders this module may emit: lab_common's shared path vocabulary plus our own.
SUMMARY_PLACEHOLDERS: tuple[str, ...] = tuple(sorted(set(lab_common.PATH_TOKENS) | {
    PLACEHOLDER_REDACTED, PLACEHOLDER_PATH, PLACEHOLDER_SYS, PLACEHOLDER_REMOTE,
    PLACEHOLDER_TRUNCATED, PLACEHOLDER_USER}))

MAX_SUMMARY_TOKENS = 14

_SAFE_LABEL_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,47}$')
_SAFE_FLAG_RE = re.compile(r'^--?[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$')
_PLACEHOLDER_RE = re.compile(r'^<[A-Z][A-Z_]{2,11}>(/\*(\.[A-Za-z0-9]{1,12})?)?$')
# The event-log string discipline (PG-11 / protocol 12.2) rejects a bare hex run that could
# be a foreign commit id, so a summary must not carry one either.
_HEXISH_RE = re.compile(r'^[0-9a-f]+$', re.IGNORECASE)
_EXT_RE = re.compile(r'^[A-Za-z0-9]{1,12}$')
_IPV4_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}$')
_LOOPBACK_OK = frozenset({'127.0.0.1', '0.0.0.0', 'localhost', '::1'})

# Generic home-directory shapes, so that ANOTHER account's home is redacted too, not only
# the account this process happens to run as.
_GENERIC_HOME_RE = re.compile(r'^/(?:Users|home)/[^/]+')
_TMP_PREFIXES = ('/private/tmp', '/private/var/folders', '/var/folders', '/tmp', '/private/var/tmp')
_SYS_PREFIXES = ('/System', '/Library', '/usr', '/bin', '/sbin', '/opt', '/Applications',
                 '/private/var/db')


def account_names() -> tuple[str, ...]:
    """Every string that names this account and must never appear in a published finding."""
    out: set[str] = set()
    for value in (os.environ.get('USER'), os.environ.get('LOGNAME')):
        if value:
            out.add(value)
    try:
        out.add(getpass.getuser())
    except Exception:
        pass
    try:
        out.add(Path.home().name)
    except Exception:
        pass
    return tuple(sorted(n for n in out if len(n) >= 3))


def _scrub_accounts(text: str, accounts: tuple[str, ...]) -> str:
    """Replace every occurrence of an account name, anywhere in the string.

    A prefix rewrite alone is not enough.  A real path on this host is
    /private/tmp/claude-501/-Users-<account>-<project>/..., where the account name sits
    INSIDE a single path segment and no home-directory prefix matches it."""
    out = text
    for name in accounts:
        out = re.sub(re.escape(name), PLACEHOLDER_USER, out, flags=re.IGNORECASE)
    return out


def _path_root_token(path: str) -> str:
    """[pure] The placeholder standing for the root of an absolute path."""
    try:
        token = lab_common.tokenize_path(path)
    except lab_common.UntokenizablePath:
        token = ''
    if token:
        head = token.split('/', 1)[0]
        if head in lab_common.PATH_TOKENS:
            return head
    if _GENERIC_HOME_RE.match(path):
        return '<HOME>'
    for prefix in _TMP_PREFIXES:
        if path == prefix or path.startswith(prefix + '/'):
            return '<TMP>'
    for prefix in _SYS_PREFIXES:
        if path == prefix or path.startswith(prefix + '/'):
            return PLACEHOLDER_SYS
    return PLACEHOLDER_PATH


def summarize_path(path: str) -> str:
    """[pure] An absolute or relative path -> '<ROOT>/*.ext'.

    Only the root class and the file-extension class survive.  Every intermediate
    directory is dropped, because those names identify the account and the foreign
    project, and they add nothing an operator cannot recover from the argv digest."""
    root = _path_root_token(path) if path.startswith('/') else PLACEHOLDER_PATH
    base = path.rsplit('/', 1)[-1]
    ext = base.rsplit('.', 1)[-1] if '.' in base[1:] else ''
    if ext and _EXT_RE.match(ext):
        return f'{root}/*.{ext.lower()}'
    return f'{root}/*'


def _classify_value(tok: str) -> str:
    """[pure] One non-flag argv token -> a safe label or a placeholder."""
    if not tok:
        return PLACEHOLDER_REDACTED
    if '/' in tok:
        return summarize_path(tok)
    if _IPV4_RE.match(tok):
        return tok if tok in _LOOPBACK_OK else PLACEHOLDER_REMOTE
    if tok in _LOOPBACK_OK:
        return tok
    return tok


def _safe_token(tok: str, accounts: tuple[str, ...]) -> str:
    """[pure] Final gate.  Anything that is not demonstrably safe becomes <REDACTED>."""
    tok = _scrub_accounts(tok, accounts)
    if _PLACEHOLDER_RE.match(tok):
        return tok
    if PLACEHOLDER_USER in tok:
        return PLACEHOLDER_REDACTED
    if _HEXISH_RE.match(tok) and 7 <= len(tok) <= 40 and len(tok) not in (16, 32):
        return PLACEHOLDER_REDACTED
    if _SAFE_FLAG_RE.match(tok) or _SAFE_LABEL_RE.match(tok):
        return tok
    return PLACEHOLDER_REDACTED


def tokenize_command(command: str, *, accounts: tuple[str, ...] | None = None,
                     max_tokens: int = MAX_SUMMARY_TOKENS) -> tuple[str, ...]:
    """[pure] A raw command line -> a SHORT, identifier-safe summary.

    argv[0] contributes only its basename, since the directories leading to a binary name
    the account and the project.  Paths collapse to '<ROOT>/*.ext'.  Flags and small
    literals survive, because '-ngl 99' is the evidence that the offender is holding the
    accelerator.  Account names are scrubbed everywhere, not only at a path prefix."""
    names = account_names() if accounts is None else tuple(accounts)
    raw = command.split()
    if not raw:
        return ()
    out: list[str] = [_safe_token(raw[0].rsplit('/', 1)[-1], names)]
    for tok in raw[1:]:
        if len(out) >= max_tokens:
            out.append(PLACEHOLDER_TRUNCATED)
            break
        if tok.startswith('-') and '=' in tok:
            key, _, value = tok.partition('=')
            key_s = _safe_token(key, names)
            val_s = _safe_token(_classify_value(value), names)
            out.append(f'{key_s}={val_s}' if key_s != PLACEHOLDER_REDACTED
                       else PLACEHOLDER_REDACTED)
            continue
        if tok.startswith('-'):
            out.append(_safe_token(tok, names))
            continue
        out.append(_safe_token(_classify_value(tok), names))
    return tuple(out)


def summary_is_identifier_safe(summary: tuple[str, ...] | list[str],
                               accounts: tuple[str, ...] | None = None) -> bool:
    """[pure] True iff every token is a closed-vocabulary placeholder or a conservative
    label, and no token carries an account name or a home-directory shape."""
    names = account_names() if accounts is None else tuple(accounts)
    for tok in summary:
        for name in names:
            if name and name.lower() in tok.lower():
                return False
        if '/Users/' in tok or '/home/' in tok:
            return False
        head, _, tail = tok.partition('=')
        for part in ((head, tail) if tail else (head,)):
            if _PLACEHOLDER_RE.match(part):
                continue
            if _HEXISH_RE.match(part) and 7 <= len(part) <= 40 and len(part) not in (16, 32):
                return False
            if _SAFE_FLAG_RE.match(part) or _SAFE_LABEL_RE.match(part):
                continue
            return False
    return True


# ---------------------------------------------------------------------------
# findings
# ---------------------------------------------------------------------------
def _iso_utc(epoch: float) -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(epoch))


def finding_for(row: ProcRow, detector: str, *, now: float | None = None,
                accounts: tuple[str, ...] | None = None) -> dict:
    """[pure given `now`] The structured, identifier-safe record of one offender.

    Start time is derived as now - elapsed and reported in UTC.  The local wall-clock start
    that `ps` also offers is deliberately not used: a local timezone is itself a weak
    identifier, and the derived value is accurate to the second."""
    stamp = time.time() if now is None else now
    summary = tokenize_command(row.command, accounts=accounts)
    if not summary_is_identifier_safe(summary, accounts):      # pragma: no cover - belt
        summary = tuple(PLACEHOLDER_REDACTED for _ in summary)
    return {
        'pid': row.pid,
        'ppid': row.ppid,
        'detector': detector,
        'start_utc': _iso_utc(stamp - row.elapsed_s),
        'elapsed_s': row.elapsed_s,
        'rss_bytes': row.rss_bytes,
        'argv_sha256': lab_common.sha256_text(row.command),
        'summary_sha256': lab_common.sha256_text(' '.join(summary)),
        'command_summary': list(summary),
    }


def match_consumer(command: str) -> str | None:
    """[pure] The detector label for a command that invokes a known accelerator runner.

    Every token is reduced to its basename, so `/opt/bin/llama-server` matches and so does
    the wrapper form `sh -c /opt/bin/llama-server`, while a file that merely lives in a
    similarly named directory does not.  A dotted module token also matches on its head,
    which is how `python -m mlx_lm.server` and `python -m vllm.entrypoints...` are caught.

    A bare argument that happens to equal a runner name (`grep vllm README`) is still
    reported.  That direction of error costs an operator one look at a pid; the opposite
    direction costs the trial its primary endpoint.

    This predicate alone is defeated by a rename: `cp llama-server srv && ./srv -ngl 99`
    matches nothing here.  That is why it is not the only arm of the scan -- the Metal
    probe over processes above the resident-size floor is what closes the rename hole (see
    the module docstring for what that arm does and does not reach)."""
    for token in command.split():
        base = token.rsplit('/', 1)[-1]
        if base in RUNNER_TOKENS:
            return RUNNER_TOKENS[base]
        head = base.split('.', 1)[0]
        if head in RUNNER_TOKENS:
            return RUNNER_TOKENS[head]
    return None


def match_baseline(command: str) -> str | None:
    """[pure] The frozen baseline label for a command, or None.

    THE WHOLE IDENTITY RULE (ruling 31(b) as narrowed by clarification 1).  argv[0] -- the
    first whitespace-delimited token of the command line and nothing else -- must be
    EXACTLY EQUAL, character for character, to a key of BASELINE_EXECUTABLES, and that key
    must sit under BASELINE_PATH_PREFIX.

    What this deliberately does NOT do, each because it was the failure mode of a rejected
    proposal:

      * it does not match a basename, so a copy of any binary named `mediaanalysisd`
        anywhere on the host is not baseline;
      * it does not match a prefix or a framework directory, so nothing else under
        `/System/Library/PrivateFrameworks/MediaAnalysis.framework/` is baseline either,
        and `.../MediaAnalysisAccess.framework/.../mediaanalysisd-access` -- a real,
        different binary on this host -- is not baseline;
      * it does not resolve symlinks, follow a wrapper or look past argv[0], so a baseline
        daemon launched through a shell does not match.

    Every one of those cases falls through to the ordinary rules and REFUSES on presence.
    The list is closed: the only way onto it is to edit it before a freeze, which moves the
    freeze-bundle hash."""
    head = command.split(None, 1)[0] if command.split() else ''
    if not head.startswith(BASELINE_PATH_PREFIX):
        return None
    return BASELINE_EXECUTABLES.get(head)


def is_python_command(command: str) -> bool:
    """[pure] True if argv[0] looks like a python interpreter."""
    head = command.split(None, 1)[0] if command.split() else ''
    return bool(_PYTHON_BASENAME_RE.match(head.rsplit('/', 1)[-1]))


@dataclass(frozen=True)
class MetalProbe:
    """The outcome of one Metal probe, with failure reported DISTINGUISHABLY (C.2).

    `holders` are the probed pids found holding any Metal resource and `compute` the
    subset holding a compute-class one.  `covered` are the pids the probe could actually
    answer for, whether positively or negatively.  `failure` is None only when the probe
    ran and covered every pid it was asked about; otherwise it is a marker naming the
    cause, and the caller must treat the result as NOT PROVEN rather than as clean."""
    holders: frozenset[int] = frozenset()
    compute: frozenset[int] = frozenset()
    covered: frozenset[int] = frozenset()
    failure: str | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


# `lsof -V` names every search item it could not list.  A pid that no longer exists is the
# benign explanation of a non-zero exit, and it is the ONLY explanation this module accepts
# without degrading the scan: a process that has exited cannot be holding the accelerator.
_LSOF_NOT_LOCATED_RE = re.compile(r'not located:\s*([0-9]+)')


def metal_context_pids(pids: list[int], *, timeout_s: int = LSOF_TIMEOUT_S) -> MetalProbe:
    """Of `pids`, those holding an open Metal/GPU resource, via one `lsof` call.

    Field mode (`-F pn`) is used rather than the default columns because a COMMAND value
    containing a space makes the column form ambiguous, and an ambiguous line is exactly
    where an offender would hide.  `-V` makes lsof name the pids it could not locate, so a
    non-zero exit caused by a process that exited between `ps` and `lsof` can be told apart
    from a probe that genuinely failed.  Only pids are retained; no line of lsof output is
    ever stored, since those lines carry account names and full paths."""
    wanted = sorted(set(pids))
    if not wanted:
        return MetalProbe()
    argv = ['lsof', '-V', '-n', '-P', '-F', 'pn',
            '-p', ','.join(str(p) for p in wanted)]
    try:
        done = subprocess.run(argv, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return MetalProbe(failure='lsof-timeout')
    except OSError:
        return MetalProbe(failure='lsof-unavailable')
    except subprocess.SubprocessError:
        return MetalProbe(failure='lsof-failed')

    holders: set[int] = set()
    compute: set[int] = set()
    seen: set[int] = set()
    absent: set[int] = set()
    current: int | None = None
    for line in done.stdout.decode('utf-8', 'replace').splitlines():
        gone = _LSOF_NOT_LOCATED_RE.search(line)
        if gone is not None:
            absent.add(int(gone.group(1)))
            continue
        if line.startswith('p') and line[1:].isdigit():
            current = int(line[1:])
            seen.add(current)
            continue
        if not line.startswith('n') or current is None:
            continue
        if METAL_COMPUTE_RE.search(line):
            holders.add(current)
            compute.add(current)
        elif METAL_DISPLAY_RE.search(line):
            holders.add(current)

    covered = (seen | absent) & set(wanted)
    unlisted = set(wanted) - covered
    failure: str | None = None
    if unlisted:
        # lsof answered for neither "here it is" nor "it is gone".  Unprovable, so degrade.
        failure = f'lsof-unlisted-{len(unlisted)}'
    elif done.returncode != 0 and not absent:
        failure = f'lsof-exit-{done.returncode}'
    return MetalProbe(holders=frozenset(holders), compute=frozenset(compute),
                      covered=frozenset(covered), failure=failure)


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
@dataclass
class ScanResult:
    """The outcome of one host scan.

    `degraded` is non-empty when the scan could not establish quiescence -- ps failed, a
    line did not parse, the Metal probe could not run or could not answer for a process it
    was asked about, the activity test of a baseline process could not be taken, or there
    were more candidates than the probe budget.  An empty `findings` with a non-empty
    `degraded` means NOT PROVEN, never PROVEN CLEAN, and the preflight gate treats it
    accordingly.  `degraded_causes` folds these markers into the closed vocabulary the
    event chain accepts.

    `baseline` holds one record per frozen baseline accelerator consumer the scan found,
    active or not (ruling 31(d)).  An IDLE baseline record is not a finding and does not
    make the scan unclean; that is the whole content of the allowance.  An ACTIVE one also
    appears in `findings` under BASELINE_ACTIVE_LABEL and therefore refuses.

    `clean` remains exactly "no findings and no degraded cause".  It is a statement about
    what this detector saw at this instant, and it is not a claim that the machine was
    doing no accelerator work."""
    findings: list[dict] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    scanned: int = 0
    allowlisted: int = 0
    baseline: list[dict] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.findings and not self.degraded

    @property
    def baseline_active(self) -> bool:
        """True iff some frozen baseline process was measured ACTIVE at this scan."""
        return any(b['activity'] == ACTIVITY_ACTIVE for b in self.baseline)


def enumerate_foreign_consumers(own_pids: set[int] | None = None, *,
                                table_text: str | None = None,
                                metal_pids: set[int] | MetalProbe | None = None,
                                now: float | None = None,
                                accounts: tuple[str, ...] | None = None,
                                include_descendants: bool = True,
                                rss_floor_bytes: int = PROBE_RSS_FLOOR_BYTES,
                                max_probe_pids: int = MAX_LSOF_PIDS,
                                baseline_activity: ActivitySample | None = None
                                ) -> ScanResult:
    """Every foreign accelerator consumer visible on this host, as findings.

    `table_text` and `metal_pids` are injection points: pass them to evaluate a synthesized
    process table, which is how the tests stay independent of whatever happens to be
    running on the machine.  Left as None, they are read from `ps` and `lsof`.  A plain set
    of `metal_pids` stands for "these pids hold a compute-class Metal resource"; pass a
    MetalProbe to distinguish the two marker families or to simulate a probe failure.

    Two arms reach beyond the name list.  Every non-allowlisted PYTHON interpreter is
    probed whatever its size, and reported on ANY Metal resource.  Every other
    non-allowlisted process at or above `rss_floor_bytes` is probed too, and reported only
    on a COMPUTE-class resource: that is the arm a renamed binary cannot walk past, and the
    narrower predicate is what keeps a window-drawing application from being reported.  The
    docstring of this module states exactly what neither arm detects.

    A process whose argv[0] matches the frozen baseline list takes a THIRD path (ruling
    31).  It is probed exactly like any other heavy process, and if it holds a
    compute-class Metal resource it is recorded in `result.baseline` with the outcome of
    the activity test, active or not.  It becomes a finding, and therefore a refusal, only
    when that test says ACTIVE.  Every process that is NOT on the frozen list refuses on
    presence with no activity test and no override, which is ruling 31(a).

    `baseline_activity` is the injection point for the second sample of the activity test,
    in the same spirit as `metal_pids`: pass a prepared `ActivitySample` and no second `ps`
    runs and nothing waits, which is how the tests exercise the active, idle, exited and
    unmeasured paths deterministically."""
    text = read_process_table() if table_text is None else table_text
    result = ScanResult()
    if not text.strip():
        result.degraded.append('ps-unavailable')
        return result
    rows, malformed = parse_ps_table(text)
    result.scanned = len(rows)
    result.degraded.extend(malformed)
    allow = own_pid_allowlist(own_pids, rows, include_descendants=include_descendants)
    result.allowlisted = len(allow)

    candidates = [r for r in rows if r.pid not in allow]
    by_name: list[tuple[ProcRow, str]] = []
    python_rows: list[ProcRow] = []
    heavy_rows: list[ProcRow] = []
    baseline_rows: list[tuple[ProcRow, str]] = []
    for row in candidates:
        # The frozen identity is tested FIRST and it is decisive.  Nothing that fails it
        # reaches the baseline path, and everything that fails it is subject to the
        # refuse-on-presence rule of 31(a) exactly as before.
        baseline_id = match_baseline(row.command)
        if baseline_id is not None:
            if row.rss_bytes >= rss_floor_bytes:
                baseline_rows.append((row, baseline_id))
            continue
        label = match_consumer(row.command)
        if label is not None:
            by_name.append((row, label))
        elif is_python_command(row.command):
            python_rows.append(row)
        elif row.rss_bytes >= rss_floor_bytes:
            heavy_rows.append(row)

    probe_rows = python_rows + heavy_rows + [r for r, _ in baseline_rows]
    if metal_pids is None:
        if len(probe_rows) > max_probe_pids:
            # Never silently under-scan: the pids past the budget are unexamined, which is
            # a failure to establish quiescence, not an absence of offenders.
            result.degraded.append(f'probe-budget-{len(probe_rows)}')
            probe_rows = probe_rows[:max_probe_pids]
            probed = {r.pid for r in probe_rows}
            python_rows = [r for r in python_rows if r.pid in probed]
            heavy_rows = [r for r in heavy_rows if r.pid in probed]
            baseline_rows = [(r, b) for r, b in baseline_rows if r.pid in probed]
        probe = metal_context_pids([r.pid for r in probe_rows])
        # C.2: a probe that could not run degrades the scan, but only when there was
        # something it would have had to look at.  With nothing to probe there is nothing
        # left unproven.
        if probe.failure is not None and probe_rows:
            result.degraded.append(probe.failure)
    elif isinstance(metal_pids, MetalProbe):
        probe = metal_pids
        if probe.failure is not None and probe_rows:
            result.degraded.append(probe.failure)
    else:
        injected = frozenset(metal_pids)
        probe = MetalProbe(holders=injected, compute=injected,
                           covered=frozenset(r.pid for r in probe_rows))

    for row in python_rows:
        if row.pid in probe.holders:
            by_name.append((row, METAL_PYTHON_LABEL))
    for row in heavy_rows:
        if row.pid in probe.compute:
            by_name.append((row, METAL_PROCESS_LABEL))

    # ---- the baseline arm (ruling 31(b), (d)) -----------------------------
    # Only a baseline process that actually holds a compute-class Metal resource is a
    # baseline ACCELERATOR consumer, and only those are measured and recorded.  A frozen
    # identity that holds nothing is not competing for the accelerator and is no more
    # interesting than any other daemon on the host.
    holders = [(row, bid) for row, bid in baseline_rows if row.pid in probe.compute]
    if holders:
        sample = (probe_baseline_activity() if baseline_activity is None
                  else baseline_activity)
        records = [baseline_record(row, bid, sample, now=now) for row, bid in holders]
        records.sort(key=lambda rec: rec['pid'])
        result.baseline = records
        unmeasured = sum(1 for rec in records if rec['activity'] == ACTIVITY_UNKNOWN)
        if unmeasured:
            # Clarification 2: an unavailable measurement is unknown, not zero activity.
            result.degraded.append(f'baseline-unmeasured-{unmeasured}')
        active = {rec['pid'] for rec in records if rec['activity'] == ACTIVITY_ACTIVE}
        for row, _bid in holders:
            if row.pid in active:
                by_name.append((row, BASELINE_ACTIVE_LABEL))

    by_name.sort(key=lambda pair: pair[0].pid)
    result.findings = [finding_for(r, label, now=now, accounts=accounts)
                       for r, label in by_name]
    return result


def degraded_causes(degraded: Sequence[str]) -> list[dict]:
    """[pure] Fold raw degraded markers into `{cause, count}` records over the closed
    vocabulary DEGRADED_CAUSES, sorted by cause.

    The raw markers carry counts and pids (`lsof-unlisted-3`, `unparsed-fields-pid-91`),
    which is right for an operator reading JSON and wrong for the event chain, whose string
    discipline admits no free text.  A marker that matches no known prefix folds to
    `scan_error` rather than being dropped."""
    counts: dict[str, int] = {}
    prefixes = sorted(_MARKER_CAUSES, key=lambda pair: -len(pair[0]))
    for marker in degraded:
        cause = CAUSE_SCAN_ERROR
        for prefix, known in prefixes:
            if marker.startswith(prefix):
                cause = known
                break
        counts[cause] = counts.get(cause, 0) + 1
    return [{'cause': cause, 'count': counts[cause]} for cause in sorted(counts)]


def chain_finding(finding: Mapping) -> dict:
    """[pure] One finding reduced to the record that may enter the public event chain.

    `command_summary` is deliberately dropped and replaced by its digest: the summary's
    vocabulary is closed for paths and addresses but not for bare literals (C.6), so a
    foreign project's module name could ride into an immutable chain inside it.  The
    detector label, the pid, the age, the resident size and the argv digest are enough to
    name the offender, and the operator's local view still prints the tokens."""
    return {
        'pid': int(finding['pid']),
        'ppid': int(finding['ppid']),
        'detector': str(finding['detector']),
        'start_utc': str(finding['start_utc']),
        'elapsed_s': int(finding['elapsed_s']),
        'rss_bytes': int(finding['rss_bytes']),
        'argv_sha256': str(finding['argv_sha256']),
        'summary_sha256': str(finding['summary_sha256']),
    }


def chain_baseline(record: Mapping) -> dict:
    """[pure] One baseline record reduced to what may enter the public event chain.

    Nothing has to be dropped here the way `chain_finding` drops the token summary: a
    baseline record carries no derived free text at all.  `baseline_id` is a label from the
    closed frozen vocabulary, the executable path itself is never published, and every
    other value is an int, an enum or a digest."""
    return {
        'pid': int(record['pid']),
        'ppid': int(record['ppid']),
        'baseline_id': str(record['baseline_id']),
        'start_utc': str(record['start_utc']),
        'elapsed_s': int(record['elapsed_s']),
        'rss_bytes': int(record['rss_bytes']),
        'cpu_delta_ms': int(record['cpu_delta_ms']),
        'interval_ms': int(record['interval_ms']),
        'activity': str(record['activity']),
        'argv_sha256': str(record['argv_sha256']),
    }


def chain_body(scan: ScanResult) -> dict:
    """[pure] The identifier-safe body shared by `host_quiescence_refused` and
    `foreign_load_detected`.  Every value is an int, a bool or a closed-vocabulary token;
    no free text, no untokenized path and no URL can reach the chain through it.

    `baseline` and `baseline_active` implement ruling 31(d): every frozen baseline
    accelerator consumer the scan found is written at EVERY scan, active or not, so that
    `clean` is never a bare assertion.  `baseline_active` is the flag the trial-overlap
    rule reads (TRIAL_OVERLAP_RULE); it is redundant with the list by construction, and it
    is written out because it is the field a reader of a latency result actually needs."""
    return {
        'clean': bool(scan.clean),
        'scanned': int(scan.scanned),
        'allowlisted': int(scan.allowlisted),
        'findings': [chain_finding(f) for f in scan.findings],
        'degraded': degraded_causes(scan.degraded),
        'baseline': [chain_baseline(b) for b in scan.baseline],
        'baseline_active': bool(scan.baseline_active),
    }


def describe_findings(findings: list[dict]) -> str:
    """[pure] A one-line, identifier-safe roster of offenders for an exception message."""
    parts = [f"pid {f['pid']} {f['detector']} elapsed {f['elapsed_s']}s "
             f"rss {f['rss_bytes']}B argv {f['argv_sha256'][:12]}" for f in findings]
    return '; '.join(parts)


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------
def preflight_host_quiescent(own_pids: set[int] | None = None, **kwargs) -> ScanResult:
    """The hard gate.  Call before a trial episode may run.

    Raises HostNotQuiescent, naming the offenders, when any foreign consumer is present OR
    when the scan could not establish quiescence.  Failing closed is the point: protocol
    section 5.7 is a precondition for the latency tier to mean anything, and the harness
    must not proceed on an unproven host."""
    result = enumerate_foreign_consumers(own_pids, **kwargs)
    if result.findings:
        raise HostNotQuiescent(
            f'host is not quiescent: {len(result.findings)} foreign accelerator '
            f'consumer(s) present: {describe_findings(result.findings)}',
            findings=result.findings, degraded=tuple(result.degraded))
    if result.degraded:
        raise HostNotQuiescent(
            'host quiescence could not be established: '
            f'{", ".join(sorted(set(result.degraded)))}',
            findings=[], degraded=tuple(result.degraded))
    return result


def soft_host_check(own_pids: set[int] | None = None, **kwargs) -> ScanResult:
    """The observing check, for quiescent points inside a trial.

    Returns what it saw and NEVER raises, so that a mid-trial observation can be recorded
    in the event log without itself becoming a failure path."""
    try:
        return enumerate_foreign_consumers(own_pids, **kwargs)
    except Exception as exc:                                    # pragma: no cover - belt
        return ScanResult(degraded=[f'soft-check-error-{type(exc).__name__}'])


def _main(argv: list[str]) -> int:                              # pragma: no cover
    """Read-only operator view: `python lab_hostcheck.py`.  Prints the findings as JSON."""
    import json
    scan = soft_host_check(set())
    print(json.dumps({'findings': scan.findings, 'degraded': scan.degraded,
                      'scanned': scan.scanned, 'allowlisted': scan.allowlisted,
                      'baseline': scan.baseline,
                      'baseline_active': scan.baseline_active,
                      'baseline_policy': baseline_policy()},
                     indent=2, sort_keys=True))
    return 1 if scan.findings else 0


if __name__ == '__main__':                                      # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
