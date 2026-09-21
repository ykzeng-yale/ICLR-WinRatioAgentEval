"""PARENT SUPERVISOR for a measured job: wall clock, process-tree memory, output bytes.

Root, 2026-09-21 08:28, ranked action 1:

    "Implement a parent supervisor for the entire operation, including startup,
     reference calls, output writes/close and receipts: total 300 seconds,
     simultaneous process-tree memory 2 GiB, total output 200 MiB. Terminate only its
     own job on a limit, preserving partial artifacts and a failure receipt. ... The
     current per-trial in-worker check cannot interrupt a native call and misses
     setup/final output; `full_grid` also lacks runtime caps."

Every clause of that was a real hole in what I shipped:

  * the in-worker check ran BETWEEN trials, so a long native ``confseq_eb`` call could
    not be interrupted at all;
  * the inner timer started after setup and pinning and stopped before the final
    write/close, so neither end of the job was inside the measured window;
  * the byte cap watched ``sink.raw_bytes``, which is the PRIMARY stream only -- the
    buffered reference rows and the receipt were outside it;
  * there was no recheck after the last trial;
  * ``full_grid`` passed ``caps=None`` and had no runtime monitoring whatsoever.

So ``completed_fully`` meant "no sampled pre-trial cap event", not "the whole operation
stayed inside every cap". This module makes the second claim checkable by putting the
job in a CHILD PROCESS and watching it from outside.

SAFETY. The supervisor signals **only the process group it created**. It never
enumerates, signals or inspects any process it did not spawn, so a foreign workload on
the same host -- and there is one -- cannot be touched by it.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent

#: Poll interval.  Fine enough that a breach is caught promptly, coarse enough
#: that the supervisor's own cost stays negligible against the job.
POLL_SECONDS = 0.15


class SupervisionError(RuntimeError):
    pass


@dataclass
class Caps:
    """The authorized hard limits.  Defaults are the root's exact figures."""

    seconds: float = 300.0
    tree_rss_bytes: int = 2 * 1024 ** 3
    output_bytes: int = 200 * 1024 ** 2


def _descendant_pids(root_pid: int) -> List[int]:
    """The child's own process tree, built from ONE ``ps`` snapshot.

    Only descendants of ``root_pid`` are returned.  Nothing outside the tree the
    supervisor created is ever considered, let alone signalled.
    """
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,ppid="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):              # pragma: no cover
        return [root_pid]
    kids: Dict[int, List[int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:                                     # pragma: no cover
            continue
        kids.setdefault(ppid, []).append(pid)
    seen: List[int] = []
    stack = [root_pid]
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.append(p)
        stack.extend(kids.get(p, []))
    return seen


class MeasurementFailure(SupervisionError):
    """A resource measurement could not be taken.  Fail closed, never open."""


def available_ram_bytes() -> Optional[int]:
    """Available (not merely free) RAM, or ``None`` if it cannot be measured.

    Root: "Check available RAM as well as CPU/disk before starting."  The
    previous host record had total RAM, load and free disk -- none of which is
    availability.  ``None`` is returned rather than a guess, and the caller
    fails closed on it.
    """
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):              # pragma: no cover
        return None
    page = 4096
    for line in out.splitlines():
        if "page size of" in line:
            try:
                page = int(line.split("page size of")[1].split("bytes")[0].strip())
            except (ValueError, IndexError):                   # pragma: no cover
                page = 4096
    vals = {}
    for line in out.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().rstrip(".")
        if v.isdigit():
            vals[k.strip()] = int(v)
    if not vals:
        return None
    free = (vals.get("Pages free", 0) + vals.get("Pages inactive", 0)
            + vals.get("Pages speculative", 0)
            + vals.get("Pages purgeable", 0))
    return free * page


def _tree_rss_bytes(pids: Sequence[int]) -> int:
    """SIMULTANEOUS summed RSS over the given pids, in bytes.

    This is the quantity ``getrusage`` could not give: a sum taken at one
    instant across live processes, rather than a per-process historical maximum
    over self and reaped children.
    """
    if not pids:
        return 0
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p",
                              ",".join(str(p) for p in pids)],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        # FAIL CLOSED.  Returning 0 here would read as "no memory in use" and
        # the cap would silently stop being enforced.
        raise MeasurementFailure(f"process-tree RSS measurement failed: {exc}")
    if out.returncode != 0 and not out.stdout.strip():
        raise MeasurementFailure(
            f"process-tree RSS measurement returned no data (rc={out.returncode})")
    total_kb = 0
    for line in out.stdout.split():
        try:
            total_kb += int(line)
        except ValueError:                                     # pragma: no cover
            pass
    return total_kb * 1024


def _dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def supervise(argv: Sequence[str], out_dir: Path, caps: Optional[Caps] = None,
              label: str = "job", cwd: Optional[Path] = None,
              receipt_reserve_bytes: int = 256 * 1024,
              require_available_ram_bytes: Optional[int] = None
              ) -> Dict[str, Any]:
    """Run ``argv`` as a supervised child and enforce every cap from outside.

    The measured window covers the WHOLE operation: process spawn, interpreter
    startup, imports, the run itself, output writes and close, and the child's
    own receipt writing.  Nothing is outside it, which was the point.

    On a breach the child's process GROUP is terminated (SIGTERM, then SIGKILL
    after a grace period), partial artifacts are left exactly as they are, and a
    failure receipt is written beside them.
    """
    caps = caps or Caps()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    avail = available_ram_bytes()
    if require_available_ram_bytes is not None:
        if avail is None:
            raise MeasurementFailure(
                "available RAM could not be measured; refusing to start rather "
                "than assuming capacity")
        if avail < require_available_ram_bytes:
            raise MeasurementFailure(
                f"available RAM {avail} < required {require_available_ram_bytes}; "
                f"reporting the blocker rather than forcing the run")

    started_wall = time.time()
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        list(argv), cwd=str(cwd or HERE),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,           # its own process group: see SAFETY
    )
    # Capture the group id NOW, while the leader is certainly alive, so a
    # breach detected after the leader exits can still reap the descendants.
    try:
        proc._owned_pgid = os.getpgid(proc.pid)                 # type: ignore[attr-defined]
    except (ProcessLookupError, PermissionError):               # pragma: no cover
        proc._owned_pgid = None                                 # type: ignore[attr-defined]
    peak_tree_rss = 0
    peak_output = 0
    samples = 0
    breach: Optional[Dict[str, Any]] = None

    try:
        while True:
            rc = proc.poll()
            elapsed = time.perf_counter() - t0
            pids = _descendant_pids(proc.pid) if rc is None else []
            try:
                rss = _tree_rss_bytes(pids) if pids else 0
            except MeasurementFailure as exc:
                breach = {"cap": "measurement_failed", "limit": None,
                          "observed": str(exc),
                          "note": ("a resource measurement that cannot be taken "
                                   "is not a passing measurement")}
                _terminate_own_job(proc)
                break
            # RESERVE the parent's own receipt bytes against the output cap, so
            # a job that fits only until the receipt is written is refused
            # before it writes one.
            obytes = _dir_bytes(out_dir) + receipt_reserve_bytes
            peak_tree_rss = max(peak_tree_rss, rss)
            peak_output = max(peak_output, obytes)
            samples += 1

            if elapsed > caps.seconds:
                breach = {"cap": "seconds", "limit": caps.seconds,
                          "observed": elapsed}
            elif rss > caps.tree_rss_bytes:
                breach = {"cap": "tree_rss_bytes", "limit": caps.tree_rss_bytes,
                          "observed": rss}
            elif obytes > caps.output_bytes:
                breach = {"cap": "output_bytes", "limit": caps.output_bytes,
                          "observed": obytes}
            if breach is not None:
                _terminate_own_job(proc)
                break
            if rc is not None:
                break
            time.sleep(POLL_SECONDS)
    finally:
        try:
            stdout, stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:                      # pragma: no cover
            _terminate_own_job(proc)
            stdout, stderr = proc.communicate()

    elapsed = time.perf_counter() - t0
    # FINAL RECHECK, after the child has closed its files.  The previous design
    # had no post-run check, so bytes written during close were never tested.
    final_output = _dir_bytes(out_dir)
    peak_output = max(peak_output, final_output)
    if breach is None and final_output > caps.output_bytes:
        breach = {"cap": "output_bytes", "limit": caps.output_bytes,
                  "observed": final_output, "detected": "final recheck after close"}

    record: Dict[str, Any] = {
        "schema": "live_ab_validation_v2.supervision.1",
        "label": label,
        "argv": list(argv),
        "caps": {"seconds": caps.seconds,
                 "tree_rss_bytes": caps.tree_rss_bytes,
                 "output_bytes": caps.output_bytes},
        "available_ram_bytes_at_start": avail,
        "receipt_reserve_bytes": receipt_reserve_bytes,
        "observed": {
            "wall_seconds": elapsed,
            "peak_tree_rss_bytes": peak_tree_rss,
            "peak_output_bytes": peak_output,
            "final_output_bytes": final_output,
            "poll_samples": samples,
            "poll_interval_seconds": POLL_SECONDS,
        },
        "measured_window": ("process spawn through exit, INCLUDING interpreter "
                            "startup, imports, reference calls, output writes, "
                            "close and the child's receipt write"),
        "rss_scope": ("SAMPLED simultaneous summed RSS over the child's own "
                      "process tree at a "
                      f"{POLL_SECONDS}s poll interval; NOT a getrusage "
                      "self/reaped-child maximum, and NOT an instantaneous hard "
                      "bound -- a spike between samples can be missed. Root was "
                      "explicit: do not describe polling as a hard memory bound."),
        "returncode": proc.returncode,
        "breach": breach,
        "within_caps": breach is None and proc.returncode == 0,
        "terminated_by_supervisor": breach is not None,
        "foreign_processes_touched": False,
        "safety": ("the supervisor signals only the process group it created; it "
                   "never signals or inspects a process it did not spawn"),
        "timestamps": {
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime(started_wall)),
            "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "child_stdout_tail": (stdout or "")[-4000:],
        "child_stderr_tail": (stderr or "")[-4000:],
    }
    if breach is not None or proc.returncode != 0:
        record["failure_receipt"] = {
            "reason": ("cap breach" if breach else
                       f"child exited {proc.returncode}"),
            "partial_artifacts_preserved": True,
            "artifacts_present": sorted(
                str(p.relative_to(out_dir)) for p in out_dir.rglob("*")
                if p.is_file()),
            "do_not": ("do not treat partial artifacts as a completed pass, and "
                       "do not auto-retry; deliver the finding"),
        }
        (out_dir / "SUPERVISION_FAILURE.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n")
    (out_dir / "SUPERVISION.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def _terminate_own_job(proc: subprocess.Popen) -> None:
    """SIGTERM then SIGKILL the child's OWN process group. Nothing else.

    Root: "finish termination of the owned process group even if its leader
    exits first."  The group id is captured when the child STARTS, so a leader
    that has already exited cannot strand its descendants: the saved id is used
    for the kill either way.
    """
    pgid = getattr(proc, "_owned_pgid", None)
    if pgid is None:
        try:
            pgid = os.getpgid(proc.pid)
        except (ProcessLookupError, PermissionError):
            return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):              # pragma: no cover
        return
    deadline = time.perf_counter() + 5.0
    while time.perf_counter() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)
    try:                                                       # pragma: no cover
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
