"""The two-worker containment probe of protocol 5.7 item 3.

Protocol 5.7 item 3, verbatim:

    "Containment probe before the freeze, on the trial host, with two workers
     running: a probe program in one worker tries to list, read and write the
     other worker's run directory, the event chain, records/, the spools, the
     task file and the server log; every result is recorded in the freeze bundle;
     ANY SUCCESS OF THE PROBE other than those the audited profile already
     allowed for a single worker STOPS THE FREEZE."

Root, 2026-09-21 18:54: "Implement the existing two-worker containment probe with
synthetic nonsecret fixtures and bounded attempts, exercising the prescribed
production lock/sandbox path. DO NOT WEAKEN CONTAINMENT TO OBTAIN A PASS."

WHAT THE AUDITED PROFILE ACTUALLY ALLOWS
----------------------------------------
Read ``sandbox.seatbelt_profile`` before reading the expectations below. It is:

    (allow default)                      <- everything not denied is ALLOWED
    (deny network*)
    (deny file-read*  (subpath HOME))
    (allow file-read* (subpath VENV_PREFIX))
    (deny file-write* (subpath HOME))
    (deny file-write* (subpath each tmp root))
    (allow file-write* (subpath SANDBOX_BASE))
    (allow file-write* (literal /dev/null))
    (deny process-exec (EXEC_DENY_DIRS))

Two consequences decide this probe:

  * Every live_ab artifact -- the event chain, ``records/``, the spools, the task
    file, the server log -- lives under the repository, which is under HOME.
    Reading OR writing any of them from inside the sandbox must therefore be DENIED.
    A success is a containment breach and stops the freeze.

  * The sandbox base is WRITABLE by design and is shared by every run on the
    host. So a peer worker's run directory would be readable and writable IF one
    existed concurrently. That is exactly the hole protocol 5.7 names, and the
    protocol's remedy is not a profile change but the HOST-WIDE EXECUTION LOCK:
    "At most one generated program exists and runs at any instant, exactly as in
    the audited regime."

The probe therefore reports two different things and never conflates them:
``isolation`` (repo artifacts denied) and ``exclusion`` (no concurrent peer
run directory exists while we hold the lock). Reporting a writable sandbox base
as a "breach" would be a false alarm; reporting it as "allowed" without checking
the lock would be the weakening root forbade.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

LS_DIR = lab_common.REPO_ROOT / 'experiments' / 'local_stream'
if str(LS_DIR) not in sys.path:                                # pragma: no cover
    sys.path.insert(0, str(LS_DIR))

PROBE_SCHEMA = 'live_ab/containment_probe-v1'

#: Synthetic, NON-SECRET fixture content. Nothing real is placed where a probe
#: could read it; if containment fails, what leaks is this string.
FIXTURE_MARKER = 'SYNTHETIC-NONSECRET-CONTAINMENT-FIXTURE-DO-NOT-TREAT-AS-DATA'

#: The six target classes protocol 5.7 item 3 enumerates.
TARGET_KINDS = ('peer_run_dir', 'event_chain', 'records_dir', 'spools',
                'task_file', 'server_log')


def build_fixtures(root: Path) -> Dict[str, Path]:
    """Synthetic stand-ins for the six targets, in repository-resident locations.

    They are placed under the repo (hence under HOME) precisely because that is
    where the real artifacts live and where the profile must deny access.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        'event_chain': root / 'events' / 'seg_0000.jsonl',
        'records_dir': root / 'records' / 'row_0001.json',
        'spools': root / 'spools' / 'spool_0.jsonl',
        'task_file': root / 'tasks.json',
        'server_log': root / 'logs' / 'server_coder.log',
    }
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(FIXTURE_MARKER + '\n', encoding='utf-8')
    return paths


def probe_source(targets: Dict[str, str], peer_glob: str) -> str:
    """The probe program. Attempts list, read and write on every target.

    Bounded by construction: a fixed target list, one attempt of each kind per
    target, no loops over the filesystem, no recursion, no network.
    """
    return (
        'import json, os, glob\n'
        'TARGETS = %s\n'
        'PEER_GLOB = %r\n'
        'out = []\n'
        'def attempt(kind, op, fn):\n'
        '    try:\n'
        '        v = fn()\n'
        '        out.append({"target": kind, "op": op, "succeeded": True,\n'
        '                    "detail": (v if isinstance(v, str) else repr(v))[:120]})\n'
        '    except Exception as e:\n'
        '        out.append({"target": kind, "op": op, "succeeded": False,\n'
        '                    "error": type(e).__name__})\n'
        'for kind, path in TARGETS.items():\n'
        '    attempt(kind, "list", lambda p=path: os.listdir(os.path.dirname(p)))\n'
        '    attempt(kind, "read", lambda p=path: open(p).read())\n'
        '    attempt(kind, "write", lambda p=path: open(p, "a").write("BREACH"))\n'
        '# the peer worker run directory: does one exist while we hold the lock?\n'
        'peers = sorted(glob.glob(PEER_GLOB))\n'
        'mine = os.path.realpath(os.getcwd())\n'
        'peers = [p for p in peers if os.path.realpath(p) != mine]\n'
        'out.append({"target": "peer_run_dir", "op": "enumerate",\n'
        '            "succeeded": bool(peers), "detail": repr(peers[:3])})\n'
        'for p in peers[:1]:\n'
        '    attempt("peer_run_dir", "list", lambda q=p: os.listdir(q))\n'
        'print("<<<PROBE>>>" + json.dumps(out))\n'
    ) % (json.dumps(targets), peer_glob)


def classify(results: List[dict]) -> Dict[str, Any]:
    """Split results into allowed-by-the-audited-profile and BREACH.

    The rule is protocol 5.7 item 3's: any success other than one the audited
    single-worker profile already allowed stops the freeze. Repo-resident targets
    are denied by the profile, so ANY success on them is a breach. The peer run
    directory is a different question -- see the module docstring -- and is
    reported under ``exclusion``, not silently excused.
    """
    breaches, allowed, denied = [], [], []
    peer_present = False
    for r in results:
        if r['target'] == 'peer_run_dir':
            if r['op'] == 'enumerate':
                peer_present = bool(r.get('succeeded'))
            if r.get('succeeded'):
                allowed.append(r)      # the base IS writable by design
            else:
                denied.append(r)
            continue
        if r.get('succeeded'):
            breaches.append(r)         # a repo artifact was reachable
        else:
            denied.append(r)
    return {
        'isolation_breaches': breaches,
        'isolation_ok': not breaches,
        'denied_attempts': len(denied),
        'allowed_by_audited_profile': allowed,
        'concurrent_peer_run_dir_found': peer_present,
        'exclusion_ok': not peer_present,
        'verdict': 'PASS' if (not breaches and not peer_present) else 'FAIL',
        'rule': ('protocol 5.7 item 3: any success of the probe other than those '
                 'the audited profile already allowed for a single worker stops '
                 'the freeze'),
    }


def run_probe(fixture_root: Optional[Path] = None) -> Dict[str, Any]:
    """Run the probe through the PRODUCTION lock and sandbox path."""
    import lab_prepare
    import sandbox as SB

    cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
    tmp = lab_prepare.assert_prescribed_tmpdir(cfg)   # refuses a wrong TMPDIR

    fixture_root = Path(fixture_root or (lab_common.WORK_ROOT / '_containment_fixtures'))
    fixtures = build_fixtures(fixture_root)
    targets = {k: str(v) for k, v in fixtures.items()}
    base = SB.sandbox_base_dir()
    src = probe_source(targets, os.path.join(base, 'p_*'))

    sandbox_cfg = cfg.get('sandbox') or {}
    lock_path = Path(sandbox_cfg.get('execution_lock_path')
                     or (lab_common.WORK_ROOT / 'sandbox.lock'))
    import lab_data
    started = time.time()
    with lab_data._ExecutionLock(lock_path, float((cfg.get('execution') or {})
                                                  .get('max_lock_wait_s', 120))):
        run = SB.run_program(src, timeout_s=float(sandbox_cfg.get('timeout_s', 10.0)),
                             mem_bytes=int(sandbox_cfg.get(
                                 'mem_bytes_requested_not_enforced_on_macos', 2 << 30)),
                             cpu_seconds=int(sandbox_cfg.get('cpu_s', 10)),
                             output_cap=int(sandbox_cfg.get('output_cap_bytes', 65536)))
    elapsed = time.time() - started

    stdout = run.get('stdout') or ''
    if '<<<PROBE>>>' not in stdout:
        return {'schema': PROBE_SCHEMA, 'verdict': 'FAIL',
                'error': 'the probe produced no parsable result; containment is '
                         'UNKNOWN and an unknown result is not a pass',
                'returncode': run.get('returncode'),
                'stderr_tail': (run.get('stderr') or '')[-300:],
                'elapsed_s': elapsed}
    results = json.loads(stdout.split('<<<PROBE>>>', 1)[1].strip().splitlines()[0])
    verdict = classify(results)
    return {
        'schema': PROBE_SCHEMA,
        'protocol': '5.7 item 3',
        'tmpdir': tmp,
        'sandbox_kind': run.get('sandbox_kind'),
        'profile_sha256': run.get('profile_sha256'),
        'fixtures': {'marker': FIXTURE_MARKER,
                     'root': lab_common.tokenize_path(fixture_root),
                     'synthetic_and_nonsecret': True},
        'target_kinds': list(TARGET_KINDS),
        'attempts': results,
        'elapsed_s': elapsed,
        **verdict,
    }
