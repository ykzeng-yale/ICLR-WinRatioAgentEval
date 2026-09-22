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


#: The contender program. It is a SEPARATE PROCESS on purpose: `flock` associates
#: a lock with an open file description, and "another worker" in protocol 5.7
#: means another process, not another descriptor in mine. It imports the real
#: `lab_data._ExecutionLock` and opens the real production lock path -- root's
#: exact objection to `lab_lockfixture` was that it used a fixture lock path and
#: never met the sandbox route.
CONTENDER_SOURCE = '''\
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, %(lab)r)
import lab_data

LOCK = %(lock)r
MAX_WAIT = %(max_wait)r
HOLD_SIGNAL = %(signal)r
OUT = %(out)r
REQUIRE_HOLDER = %(require_holder)r

rec = {"pid": os.getpid(), "lock_path": LOCK, "max_wait_s": MAX_WAIT,
       "require_holder": REQUIRE_HOLDER}

if REQUIRE_HOLDER:
    deadline = time.time() + 30.0
    while not os.path.exists(HOLD_SIGNAL):
        if time.time() > deadline:
            rec["error"] = "the holder never signalled within 30 s"
            Path(OUT).write_text(json.dumps(rec))
            raise SystemExit(3)
        time.sleep(0.01)
    rec["holder_signal_seen_epoch"] = time.time()

# CLOCK: time.time() is CLOCK_REALTIME and is shared across processes on this
# host, so the holder's interval and this attempt CAN be compared. monotonic is
# recorded per process as a diagnostic and is NEVER differenced across processes
# -- that is the 694 s trap, one layer down.
rec["t_attempt_start_epoch"] = time.time()
rec["t_attempt_start_monotonic"] = time.monotonic()
try:
    with lab_data._ExecutionLock(Path(LOCK), MAX_WAIT):
        rec["acquired"] = True
        rec["t_acquired_epoch"] = time.time()
except BaseException as exc:
    rec["acquired"] = False
    rec["refusal_type"] = type(exc).__name__
    rec["refusal_message"] = str(exc)[:300]
rec["t_attempt_end_epoch"] = time.time()
rec["t_attempt_end_monotonic"] = time.monotonic()
rec["elapsed_s"] = rec["t_attempt_end_epoch"] - rec["t_attempt_start_epoch"]
Path(OUT).write_text(json.dumps(rec))
'''


def contender_source(lock_path: Path, max_wait_s: float, signal_path: Path,
                     out_path: Path, *, require_holder: bool) -> str:
    """The contender child program, with every path bound explicitly."""
    return CONTENDER_SOURCE % {
        'lab': str(HERE), 'lock': str(lock_path), 'max_wait': float(max_wait_s),
        'signal': str(signal_path), 'out': str(out_path),
        'require_holder': bool(require_holder),
    }


def pair_attempts(sandboxed: List[dict], unsandboxed: List[dict]) -> Dict[str, Any]:
    """PER-ATTEMPT negative control, paired by (target, op).

    Root, on the receipt this replaces: "the negative control is a SUMMARY of
    fifteen detected breaches; it carries no per-operation raw execution receipt,
    so it supports the summary only."

    A count cannot say WHICH operation the sandbox stopped. Pairing can: for each
    (target, op) the table carries both outcomes, and the row that makes the probe
    evidence rather than decoration is *denied inside, reachable outside*. Rows
    where BOTH denied are reported as `denied_in_both` and explicitly do NOT
    support containment -- if an operation fails unsandboxed too, its denial
    inside tells us nothing about the sandbox.
    """
    def key(r: dict) -> tuple:
        return (r.get('target'), r.get('op'))

    out_map = {key(r): r for r in unsandboxed}
    rows, controlled, denied_both, breached = [], [], [], []
    for r in sandboxed:
        k = key(r)
        ctrl = out_map.get(k)
        row = {
            'target': k[0], 'op': k[1],
            'sandboxed_succeeded': bool(r.get('succeeded')),
            'sandboxed_error': r.get('error'),
            'control_present': ctrl is not None,
            'unsandboxed_succeeded': bool(ctrl.get('succeeded')) if ctrl else None,
            'unsandboxed_error': (ctrl or {}).get('error'),
        }
        if row['sandboxed_succeeded']:
            row['reading'] = 'REACHABLE INSIDE THE SANDBOX'
            breached.append(row)
        elif ctrl is None:
            row['reading'] = 'no control row; this denial is uncontrolled'
        elif row['unsandboxed_succeeded']:
            row['reading'] = 'denied inside, reachable outside -- THE SANDBOX DID IT'
            controlled.append(row)
        else:
            row['reading'] = ('denied in BOTH; the sandbox is not shown to be the '
                              'cause and this row supports nothing')
            denied_both.append(row)
        rows.append(row)
    return {
        'rows': rows,
        'attempts_paired': len(rows),
        'controlled_denials': len(controlled),
        'denied_in_both': len(denied_both),
        'reachable_inside_sandbox': len(breached),
        # MEASURED. This was a hard-coded True describing the function's own
        # design -- true by construction, but a result field that never
        # checked anything. It now says what it can fail on: every sandboxed
        # attempt got its own row, so no attempt was silently dropped from
        # the table. A count that quietly lost rows would read as a clean
        # per-attempt control.
        'control_is_per_attempt': len(rows) == len(sandboxed) and bool(rows),
        'what_a_count_could_not_say': (
            'which operations the sandbox actually stopped. Only rows marked '
            '"denied inside, reachable outside" support containment; '
            'denied_in_both rows are excluded from that support rather than '
            'folded into a total.'),
    }


def lock_is_free(lock_path: Path) -> Dict[str, Any]:
    """Is the host execution lock unheld right now?

    A FAST FAIL, not a guarantee. Between this probe releasing and the holder
    acquiring, anything on the host may take the lock; the LOCK CONTROL at the end
    of the run is what actually establishes that the run was clean. This only
    stops the fixture from spending two seconds and then reporting a verdict about
    containment when the real answer is "the host was busy".

    Why it exists: I launched the test suite in the background and ran the fixture
    beside it. Four suites take <WORK>/sandbox.lock. The control caught it and the
    run came out `verdict: FAIL, lock_control_acquired: False` -- correct, but it
    labelled a BUSY HOST as a failed containment check. Those are different
    findings and a receipt must not conflate them.

    Uses the audited `lab_data._ExecutionLock` with a zero wait rather than a raw
    `fcntl.flock`: one attempt, then refuse.
    """
    import lab_data                                            # noqa: PLC0415
    try:
        with lab_data._ExecutionLock(Path(lock_path), 0.0):
            pass
        return {'free': True, 'probe': 'acquired and released immediately'}
    except lab_common.PreflightError as exc:
        return {'free': False, 'refusal': str(exc)[:200],
                'probe': 'one non-blocking attempt, refused'}
    except OSError as exc:                                     # noqa: BLE001
        # Cannot open the lock file at all: report it rather than reading an
        # unopenable lock as a free one.
        return {'free': False, 'error': '%s: %s' % (type(exc).__name__, exc)}


def _run_contender(py: str, work: Path, lock_path: Path, max_wait_s: float,
                   signal: Path, tag: str, *, require_holder: bool,
                   background: bool):
    """Write and launch the contender. Returns (popen_or_completed, out_path)."""
    import subprocess                                           # noqa: PLC0415
    out = work / ('contender_%s.json' % tag)
    prog = work / ('contender_%s.py' % tag)
    prog.write_text(contender_source(lock_path, max_wait_s, signal, out,
                                     require_holder=require_holder),
                    encoding='utf-8')
    args = [py, str(prog)]
    if background:
        return subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True), out
    return subprocess.run(args, capture_output=True, text=True, timeout=120), out


def run_two_worker(fixture_root: Optional[Path] = None,
                   contender_wait_s: float = 2.0,
                   hold_timeout_s: float = 60.0) -> Dict[str, Any]:
    """The two-worker exclusion fixture root named as still owed.

    Root, on the receipt this completes:

        "still_owed: the two-worker fixture with an ACTUAL contender blocked
         while the first holds the production lock, retaining timing and refusal
         evidence, plus per-attempt negative-control evidence rather than a
         summary count."

    THREE THINGS ARE EXERCISED TOGETHER, which is the part that was missing:
    the PRODUCTION lock path, the PRODUCTION sandbox route, and a REAL second
    process contending for that same lock. The previous evidence was an empty
    directory glob -- no peer being found is not a demonstration that a peer
    would be blocked, and root said so.

    TWO CONTROLS, because a refusal on its own is not evidence:

      * the LOCK control -- the same contender, same path, run when NOBODY
        holds the lock, MUST ACQUIRE. Without it, a refusal caused by a stale
        lock, a permission fault or a bug in my own fixture would read exactly
        like exclusion.
      * the CONTAINMENT control -- the identical probe program run through the
        identical interpreter WITHOUT the sandbox, recorded PER ATTEMPT.

    CONTAINMENT OF THE ATTEMPT IS MEASURED, NOT ASSUMED. The signal files order
    the two processes, but ordering by construction is what the code intends; the
    receipt checks that the contender's attempt interval lies strictly inside the
    holder's hold interval on the shared realtime clock. If it does not, the
    fixture proves nothing and says so.
    """
    import subprocess                                           # noqa: PLC0415
    import lab_prepare                                          # noqa: PLC0415
    import sandbox as SB                                        # noqa: PLC0415
    import lab_data                                             # noqa: PLC0415

    cfg = json.loads((HERE / 'config.json').read_text('utf-8'))
    tmp = lab_prepare.assert_prescribed_tmpdir(cfg)

    work = Path(lab_common.WORK_ROOT) / '_two_worker' / ('tw_%d' % int(time.time()))
    work.mkdir(parents=True, exist_ok=True)
    signal = work / 'holder_has_the_lock'

    fixture_root = Path(fixture_root or (lab_common.WORK_ROOT / '_containment_fixtures'))
    fixtures = build_fixtures(fixture_root)
    targets = {k: str(v) for k, v in fixtures.items()}
    base = SB.sandbox_base_dir()
    src = probe_source(targets, os.path.join(base, 'p_*'))

    sandbox_cfg = cfg.get('sandbox') or {}
    lock_path = Path(sandbox_cfg.get('execution_lock_path')
                     or (lab_common.WORK_ROOT / 'sandbox.lock'))
    max_lock_wait = float((cfg.get('execution') or {}).get('max_lock_wait_s', 120))
    py = sys.executable

    # PRECONDITION. Checked BEFORE anything is spawned, so a busy host costs
    # nothing and is never reported as a containment verdict.
    pre = lock_is_free(lock_path)
    if not pre.get('free'):
        return {
            'schema': 'live_ab/two_worker_containment-v1',
            'verdict': 'REFUSED_PRECONDITION',
            'precondition': pre,
            'lock_path': lab_common.tokenize_path(lock_path),
            'why': ('the host execution lock was already held when this run '
                    'started. The fixture needs it free: its LOCK CONTROL runs a '
                    'contender when nobody should be holding, and a pre-existing '
                    'holder makes that control fail for a reason that has nothing '
                    'to do with containment.'),
            'this_is_not_a_containment_failure': True,
            'what_to_do': ('wait for the other holder. Four test suites take this '
                           'lock, so do not run this fixture beside the suite.'),
        }

    out: Dict[str, Any] = {
        'schema': 'live_ab/two_worker_containment-v1',
        'protocol': '5.7 item 3, and the exclusion clause of 5.7',
        'tmpdir': tmp,
        'lock_path': lab_common.tokenize_path(lock_path),
        'lock_path_is_production': (sandbox_cfg.get('execution_lock_path') is None
                                    and lock_path.name == 'sandbox.lock'),
        'clock': ('time.time() / CLOCK_REALTIME -- shared across processes on this '
                  'host. monotonic values are recorded per process and NEVER '
                  'differenced across processes.'),
        'contender_max_wait_s': contender_wait_s,
        'holder_max_lock_wait_s': max_lock_wait,
        'precondition': pre,
        'precondition_is_not_a_guarantee': (
            'the lock was free at the probe. Anything on the host could take it '
            'between the probe and the hold; the lock control at the end is what '
            'establishes the run was clean.'),
    }

    # --- worker B starts first, and waits for the signal ---------------------
    proc, b_out = _run_contender(py, work, lock_path, contender_wait_s, signal,
                                 'blocked', require_holder=True, background=True)

    holder: Dict[str, Any] = {'pid': os.getpid()}
    try:
        with lab_data._ExecutionLock(lock_path, max_lock_wait):
            holder['t_acquired_epoch'] = time.time()
            signal.write_text(json.dumps(holder), encoding='utf-8')
            # the PRODUCTION sandbox route, inside the hold
            run = SB.run_program(
                src, timeout_s=float(sandbox_cfg.get('timeout_s', 10.0)),
                mem_bytes=int(sandbox_cfg.get(
                    'mem_bytes_requested_not_enforced_on_macos', 2 << 30)),
                cpu_seconds=int(sandbox_cfg.get('cpu_s', 10)),
                output_cap=int(sandbox_cfg.get('output_cap_bytes', 65536)))
            holder['sandbox_kind'] = run.get('sandbox_kind')
            holder['profile_sha256'] = run.get('profile_sha256')
            # hold until the contender has finished attempting -- BOUNDED
            deadline = time.time() + hold_timeout_s
            while not b_out.exists() and time.time() < deadline:
                time.sleep(0.02)
            holder['waited_for_contender'] = b_out.exists()
            holder['t_release_epoch'] = time.time()
    finally:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:                        # pragma: no cover
            proc.kill()
    holder['held_s'] = holder.get('t_release_epoch', 0) - holder.get('t_acquired_epoch', 0)
    out['holder'] = holder

    contender = (json.loads(b_out.read_text('utf-8')) if b_out.exists()
                 else {'error': 'the contender wrote no record'})
    contender['child_returncode'] = proc.returncode
    out['contender_blocked'] = contender

    # --- did the attempt actually happen INSIDE the hold? --------------------
    a0, a1 = holder.get('t_acquired_epoch'), holder.get('t_release_epoch')
    b0, b1 = contender.get('t_attempt_start_epoch'), contender.get('t_attempt_end_epoch')
    inside = all(v is not None for v in (a0, a1, b0, b1)) and a0 < b0 and b1 < a1
    out['attempt_inside_hold'] = inside
    out['attempt_containment'] = {
        'holder_acquired_epoch': a0, 'holder_released_epoch': a1,
        'contender_attempt_start_epoch': b0, 'contender_attempt_end_epoch': b1,
        'margin_before_s': (b0 - a0) if (a0 and b0) else None,
        'margin_after_s': (a1 - b1) if (a1 and b1) else None,
        'why_it_matters': ('a refusal outside the hold interval is a refusal by '
                           'something else. Signal files ORDER the processes; this '
                           'arithmetic CHECKS the order actually held.'),
    }
    out['contender_was_refused'] = (contender.get('acquired') is False)
    out['refusal_type'] = contender.get('refusal_type')

    # --- LOCK CONTROL: the same contender, nobody holding, MUST acquire ------
    done, c_out = _run_contender(py, work, lock_path, contender_wait_s, signal,
                                 'control', require_holder=False, background=False)
    control = (json.loads(c_out.read_text('utf-8')) if c_out.exists()
               else {'error': 'the lock control wrote no record'})
    control['child_returncode'] = done.returncode
    out['lock_control_free'] = control
    out['lock_control_acquired'] = (control.get('acquired') is True)

    # --- CONTAINMENT CONTROL: the identical program, no sandbox, per attempt -
    sandboxed_rows: List[dict] = []
    stdout = run.get('stdout') or ''
    if '<<<PROBE>>>' in stdout:
        sandboxed_rows = json.loads(
            stdout.split('<<<PROBE>>>', 1)[1].strip().splitlines()[0])
    out['sandboxed_attempts'] = sandboxed_rows

    # The SAME interpreter the sandbox uses, so the sandbox is the ONLY
    # difference between the two arms. That equality is COMPARED, not asserted:
    # `run_program` does not report its interpreter, so the first version of this
    # receipt carried `negative_control_interpreter_matches_sandbox: True` as a
    # literal -- a field naming a check it never performed. Both values are read
    # from the same resolver the sandbox uses and differenced here.
    control_python = SB.base_interpreter()
    sandbox_python = SB.sandbox_info()['python']
    ctrl_prog = work / 'unsandboxed_probe.py'
    ctrl_prog.write_text(src, encoding='utf-8')
    bare = subprocess.run([control_python, str(ctrl_prog)],
                          capture_output=True, text=True, timeout=120)
    unsandboxed_rows: List[dict] = []
    if '<<<PROBE>>>' in (bare.stdout or ''):
        unsandboxed_rows = json.loads(
            bare.stdout.split('<<<PROBE>>>', 1)[1].strip().splitlines()[0])
    out['unsandboxed_attempts'] = unsandboxed_rows
    out['control_interpreter'] = {
        'control_arm': lab_common.tokenize_path(control_python),
        'sandbox_arm': lab_common.tokenize_path(sandbox_python),
        'identical': control_python == sandbox_python,
        'why_it_must_match': ('if the two arms ran different interpreters, a '
                              'difference in outcome could be the interpreter '
                              'rather than the sandbox, and the control would '
                              'not be a control'),
    }
    out['per_attempt_control'] = pair_attempts(sandboxed_rows, unsandboxed_rows)

    if sandboxed_rows:
        out.update({k: v for k, v in classify(sandboxed_rows).items()
                    if k in ('isolation_breaches', 'isolation_ok',
                             'allowed_by_audited_profile')})

    # --- the verdict, with every limb required ------------------------------
    limbs = {
        'contender_was_refused': out['contender_was_refused'],
        'attempt_inside_hold': out['attempt_inside_hold'],
        'lock_control_acquired': out['lock_control_acquired'],
        'isolation_ok': out.get('isolation_ok', False),
        'per_attempt_control_has_controlled_denials':
            out['per_attempt_control']['controlled_denials'] > 0,
        'no_reachable_target_inside_sandbox':
            out['per_attempt_control']['reachable_inside_sandbox'] == 0,
        'lock_path_is_production': out['lock_path_is_production'],
        'control_interpreter_identical': out['control_interpreter']['identical'],
    }
    out['limbs'] = limbs
    out['verdict'] = 'PASS' if all(limbs.values()) else 'FAIL'
    out['failed_limbs'] = sorted(k for k, v in limbs.items() if not v)
    out['peer_glob_exclusion_deliberately_not_used'] = (
        'classify() also returns concurrent_peer_run_dir_found / exclusion_ok '
        'from an empty directory glob. Root rejected that as evidence -- "no peer '
        'being found is not a demonstration that a concurrent worker is blocked" '
        '-- so those keys are NOT copied into this verdict. The refused contender '
        'replaces them.')
    out['what_this_does_NOT_establish'] = [
        'that a LIVE WORKER running a real episode is contained: the program '
        'inside the sandbox is a probe, not an agent episode',
        'exclusion for arbitrary interleavings: it shows ONE contender refused '
        'during ONE hold, which is the property flock provides, not a proof '
        'about every schedule',
        'that a second SANDBOXED worker is excluded: the contender contends for '
        'the LOCK and never reaches the sandbox route. That is what the lock is '
        'for -- it stops the second worker before it runs anything -- but the '
        'fixture shows the lock refusing, not a sandbox refusing',
        'anything about the loaded reference sweep, which remains uncleared',
    ]
    out['work_dir'] = lab_common.tokenize_path(work)
    return out


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
