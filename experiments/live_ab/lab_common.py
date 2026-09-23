"""live_ab foundation: paths, canonical JSON, hashing, durable writes, freeze bundle.

Group G1.  Standard library only (ARCHITECTURE_FINAL.md 3.1 / 3.16): this module must be
importable by the monitor, the verifier and the builder without dragging the pilot's path
shim into them, so it deliberately does not import experiments/local_stream/common.py.

Every public name below is specified in ARCHITECTURE_FINAL.md section 3.1.
"""
from __future__ import annotations

from collections.abc import Mapping

import fcntl
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# ---- paths (module constants, all absolute, computed once) -----------------
HERE: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = HERE.parents[1]
SRC_DIR: Path = REPO_ROOT / 'src'
LS_DIR: Path = REPO_ROOT / 'experiments' / 'local_stream'
RESULTS_ROOT: Path = REPO_ROOT / 'results' / 'live_ab'
WORK_ROOT: Path = REPO_ROOT / 'work' / 'live_ab'
FREEZE_DIR: Path = RESULTS_ROOT / 'freeze'
PROGRAM_CHAIN_ID: str = '_program'
PREFREEZE_CHAIN_ID: str = '_prefreeze'
TRIALS: tuple[str, ...] = ('T4', 'T2', 'T1', 'T3')     # execution order, frozen
ARMS: tuple[str, str] = ('incumbent', 'candidate')


def add_import_paths() -> None:
    """Insert LS_DIR and SRC_DIR at the front of sys.path (idempotent).
    Side effect: mutates sys.path. ONLY lab_data, lab_worker and lab_client may call it."""
    for d in (str(SRC_DIR), str(LS_DIR)):
        if d in sys.path:
            sys.path.remove(d)
        sys.path.insert(0, d)


@dataclass(frozen=True)
class TrialPaths:
    trial: str
    results: Path
    events: Path
    anchors: Path
    work: Path
    jobs: Path
    spools: Path
    records: Path
    requests: Path
    anchor_spool: Path
    anchors_private: Path
    logs: Path
    run_lock: Path
    sandbox_lock: Path

    def mkdirs(self) -> None:
        """Side effect: creates every directory of this trial, mode 0o755."""
        for d in (self.results, self.events, self.anchors, self.work, self.jobs,
                  self.spools, self.records, self.requests, self.anchor_spool,
                  self.anchors_private, self.logs):
            d.mkdir(parents=True, exist_ok=True, mode=0o755)


def trial_paths(trial: str, *, execution_lock: Path | str | None = None) -> TrialPaths:
    """The directory layout of one chain id (a trial, '_program' or '_prefreeze').

    ``execution_lock`` exists for ISOLATED TREES ONLY. Production passes nothing
    and gets the canonical host-wide file. An isolated fixture tree passes its
    own, because a unit test must not contend for the production inode -- and
    because hard-wiring the canonical lock into every constructed layout made two
    concurrently running suites serialize on one real file, which is how I first
    noticed. The CONTRACT is not enforced here: it is enforced at production
    entry by `resolve_execution_lock` and `assert_canonical_execution_lock`,
    which is where root asked for it.
    """
    if not isinstance(trial, str) or not trial:
        raise ValueError('trial must be a non-empty string')
    results = RESULTS_ROOT / trial
    work = WORK_ROOT / trial
    return TrialPaths(
        trial=trial,
        results=results,
        events=results / 'events',
        anchors=results / 'anchors',
        work=work,
        jobs=work / 'jobs',
        spools=work / 'spools',
        records=work / 'records',
        requests=work / 'requests',
        anchor_spool=work / 'anchor_spool',
        anchors_private=work / 'anchors_private',
        logs=work / 'logs',
        run_lock=work / 'run.lock',
        # PER-TRIAL run.lock, HOST-WIDE sandbox.lock. The sandbox lock used to be
        # `work / 'sandbox.lock'`, which gave every trial its own inode and every
        # checkout its own again -- five files where protocol 5.7 item 1 requires
        # one. run.lock stays per trial: root explicitly preserved it.
        sandbox_lock=(Path(execution_lock) if execution_lock is not None
                      else canonical_execution_lock(harness_config())),
    )


#: THE CANONICAL HOST-WIDE EXECUTION LOCK, token and resolver.
#:
#: Protocol 5.7 is titled "the host-wide execution lock" and item 1 requires an
#: exclusive `flock` on ONE LOCK FILE, because the Seatbelt writable directory is
#: shared by EVERY run on the host. Production resolved FIVE files
#: (`results/live_ab/LOCK_TOPOLOGY_v2.json`): `<WORK>/sandbox.lock` for the
#: reference sweep and `<WORK>/<trial>/sandbox.lock` per trial.
#:
#: Root's ruling, `reviews/lock_anchor_review_20260923_0348.md`:
#:
#:     "All cooperating execution paths on that host must bind to this same
#:      resolved file ... A relative `work/live_ab/sandbox.lock` in each clone
#:      would still create one lock per clone and would not satisfy the contract
#:      ... Use one frozen host-root resolver/token (for example `<HOST_WORK>`)
#:      consistently in serialization and resolution."
#:
#: WHY A SEPARATE TOKEN AND NOT `<WORK>`. `<WORK>` resolves against whatever
#: checkout is reading the job, so a job serialized in one clone and resolved in
#: another names a DIFFERENT physical file and the exclusion domain splits
#: silently. `flock` protects an inode; two inodes exclude nothing. `<HOST_WORK>`
#: resolves from a FROZEN pin in config, identically in every checkout.
#:
#: `run.lock` stays per trial -- root: "Preserve per-trial run locks." Only the
#: sandbox execution lock is host-wide.
_HARNESS_CONFIG: dict | None = None


def harness_config() -> dict:
    """`config.json` beside this module, read once.

    `trial_paths` has no cfg argument and is called from the worker fallback, so
    the canonical lock has to be reachable without threading config through every
    caller. Cached because it is read on every path construction.
    """
    global _HARNESS_CONFIG
    if _HARNESS_CONFIG is None:
        _HARNESS_CONFIG = json.loads((HERE / 'config.json').read_text('utf-8'))
    return _HARNESS_CONFIG


HOST_WORK_TOKEN: str = '<HOST_WORK>'
EXECUTION_LOCK_NAME: str = 'sandbox.lock'


def host_work_root(cfg: Mapping | None) -> Path:
    """The frozen host work root the execution lock lives under.

    Read from `config.sandbox.host_work_root`, which is a PIN, not a derivation:
    deriving it from this checkout is exactly the bug -- every clone would derive
    its own. Absent or relative means the contract cannot be honoured, and that
    refuses rather than silently falling back to a checkout-local path.
    """
    declared = (((cfg or {}).get('sandbox') or {}) or {}).get('host_work_root')
    if not declared or not isinstance(declared, str):
        raise PreflightError(
            'config.sandbox.host_work_root is %r; protocol 5.7 item 1 needs a '
            'frozen host path so every checkout binds the same lock inode'
            % (declared,))
    if not os.path.isabs(declared):
        raise PreflightError(
            'config.sandbox.host_work_root must be ABSOLUTE; %r would resolve '
            'per checkout and split the lock' % (declared,))
    return Path(declared)


def canonical_execution_lock(cfg: Mapping | None) -> Path:
    """The ONE file every cooperating execution path must flock."""
    return host_work_root(cfg) / EXECUTION_LOCK_NAME


def tokenize_execution_lock(cfg: Mapping | None) -> str:
    """`<HOST_WORK>/sandbox.lock` -- serialized into job payloads."""
    return '%s/%s' % (HOST_WORK_TOKEN, EXECUTION_LOCK_NAME)


def resolve_execution_lock_token(tok: str, cfg: Mapping | None) -> Path:
    """Resolve `<HOST_WORK>/...` against the FROZEN pin, never the local checkout."""
    s = str(tok)
    if s == HOST_WORK_TOKEN:
        return host_work_root(cfg)
    if s.startswith(HOST_WORK_TOKEN + '/'):
        return host_work_root(cfg) / s[len(HOST_WORK_TOKEN) + 1:]
    raise PreflightError('%r is not a %s path' % (s, HOST_WORK_TOKEN))


def resolve_execution_lock(cfg: Mapping | None, *, stage: str) -> tuple:
    """THE ONE resolver every cooperating execution path uses. Returns (path, info).

    IT TAKES NO OVERRIDE AND HONOURS NO FLAG. Root, reviewing the first version
    (`reviews/lock_delta_disposition_20260923_0502.md`):

        "a path or flag cannot designate itself an isolated fixture ...
         `resolve_execution_lock` accepts an override when a truthy serialized
         `execution_lock_is_fixture` field is supplied ... do not teach the
         production job reader to bypass validation merely to keep those tests
         passing."

    That is right, and the reason I built the bypass is the reason it was wrong: I
    wanted four worker tests to pass. Validation must never consult a claim made
    by the thing being validated -- a job or config that says "trust me, I am a
    fixture" is exactly what an arbitrary job would say.

    ISOLATION NOW LIVES IN THE TEST PROCESS: a test patches the canonical root
    (`lab_common._HARNESS_CONFIG`) so the canonical file IS its temporary file.
    The production path is unchanged and still validates; only the configuration
    it validates against is isolated. An offline runner that needs different
    configuration gets its own non-production entry, not a hole in this one.

    A supplied `execution_lock_path` now REFUSES rather than being honoured,
    because there is no longer any way to declare it legitimate.
    """
    sandbox_cfg = ((cfg or {}).get('sandbox') or {})
    override = sandbox_cfg.get('execution_lock_path')
    if override:
        raise PreflightError(
            'sandbox.execution_lock_path=%r at %s: the execution lock is not '
            'configurable. Protocol 5.7 item 1 admits one host-wide file, and a '
            'configuration cannot license its own exception. Isolate by patching '
            'the canonical root inside the test process instead.'
            % (override, stage))
    assert_host_root_agreement(cfg, stage=stage)
    path = canonical_execution_lock(harness_config())
    return path, assert_canonical_execution_lock(path, harness_config(), stage=stage)


def assert_job_host_root_agreement(job: Mapping | None, *, stage: str) -> dict:
    """Validate the host pin in EVERY place a job can carry one, and reject copies
    that contradict each other.

    Root, `reviews/lock_anchor_disposition_20260923_0618.md`:

        "`World.build_job` emits top-level `job['sandbox']`, with no
         `job['cfg']`. The worker's new host-root agreement guard instead checks
         only `job.get('cfg') or {}`. An actual producer-shaped job with a
         conflicting top-level host pin reaches stubbed dispatch ... apply
         agreement validation to the actual top-level sandbox block used by the
         worker and validate any supported nested configuration as well; reject
         contradictory copies."

    My guard checked the shape I ASSUMED the producer emits rather than the shape
    it does emit -- the same defect as a fixture written by the same mind as the
    reader. `run_job` already reads both spellings (`job['sandbox']` at one site,
    `job['cfg']['sandbox']` at another), so both are live and both must be
    validated. Two copies that disagree are refused outright: there is no rule
    for choosing between them that is not a guess.
    """
    job = job or {}
    blocks = {
        'job.sandbox': (job.get('sandbox') or {}),
        'job.cfg.sandbox': (((job.get('cfg') or {}).get('sandbox')) or {}),
    }
    declared = {where: b.get('host_work_root')
                for where, b in blocks.items() if b.get('host_work_root')}
    values = {os.path.realpath(str(v)) for v in declared.values()}
    if len(values) > 1:
        raise PreflightError(
            'contradictory host_work_root copies at %s: %r. A job carrying two '
            'different host pins has no correct reading; it refuses.'
            % (stage, declared))
    out = {'stage': stage, 'declared_in': sorted(declared),
           'checked_both_shapes': sorted(blocks)}
    for where, value in declared.items():
        assert_host_root_agreement({'sandbox': {'host_work_root': value}},
                                   stage='%s (%s)' % (stage, where))
        out['agrees_with_audited_pin'] = True
    return out


def assert_host_root_agreement(cfg: Mapping | None, *, stage: str) -> dict:
    """A job-carried host root must AGREE with the audited module pin.

    Root: "Verify the effective configuration/job host root agrees with the
    audited canonical pin rather than silently mixing it with cached module
    configuration." A job may carry its own `sandbox` block; if it names a
    different host root than the module config the two are silently mixed and the
    lock the worker checks is not the lock the job meant.
    """
    declared = (((cfg or {}).get('sandbox') or {}) or {}).get('host_work_root')
    if declared is None:
        return {'stage': stage, 'job_declared_host_root': None,
                'note': 'job carries no host root; the audited module pin governs'}
    audited = str(host_work_root(harness_config()))
    if os.path.realpath(str(declared)) != os.path.realpath(audited):
        raise PreflightError(
            'host_work_root at %s is %r but the audited pin is %r; a job may not '
            'relocate the host-wide lock' % (stage, declared, audited))
    return {'stage': stage, 'job_declared_host_root': str(declared),
            'agrees_with_audited_pin': True}


def assert_canonical_lock_spelling(raw, cfg: Mapping | None, *, stage: str) -> dict:
    """The SERIALIZED SPELLING must be canonical too, not merely resolve there.

    `<WORK>/sandbox.lock` resolves to the canonical file IN THE OWNER CHECKOUT,
    because `<WORK>` and `<HOST_WORK>` coincide there -- and to a different file
    in any clone. Accepting it would accept a spelling that is only accidentally
    correct on one host, which is the cross-checkout splitting root's ruling is
    about. So exactly two spellings are admissible: the canonical token, or the
    canonical absolute path.

    This is an ADDITIONAL requirement, not an exemption. Nothing here lets a
    spelling through that the resolved-path check would refuse.
    """
    s = str(raw)
    ok_token = tokenize_execution_lock(cfg)
    ok_abs = str(canonical_execution_lock(cfg))
    if s == ok_token or s == ok_abs:
        return {'stage': stage, 'spelling': s,
                'kind': 'token' if s == ok_token else 'absolute'}
    raise PreflightError(
        'execution lock spelling at %s is %r; only %r or %r are admissible. A '
        'spelling that merely resolves correctly in THIS checkout resolves '
        'elsewhere in a clone, which is the splitting protocol 5.7 item 1 '
        'forbids.' % (stage, s, ok_token, ok_abs))


def assert_canonical_execution_lock(path, cfg: Mapping | None, *, stage: str) -> dict:
    """Refuse any execution lock that is not the canonical file.

    Root: "Bind and check the canonical execution-lock identity at production
    entry; do not permit an arbitrary job path to split it." A stale serialized
    job from before this repair carries `<WORK>/<trial>/sandbox.lock`; resolving
    it would open a second inode and the two workers would not exclude each
    other. That must REFUSE, not proceed.

    Compared on the REALPATH, because /tmp and /var reach the same inode through
    /private on macOS and a string comparison would refuse a correct path.
    """
    want = canonical_execution_lock(cfg)
    got = Path(path)
    # ABSOLUTE FIRST. `os.path.realpath` resolves a relative path against the
    # CURRENT WORKING DIRECTORY, so `work/live_ab/sandbox.lock` compares EQUAL to
    # the canonical file when cwd happens to be the repo root and unequal
    # otherwise. A lock whose identity depends on where the process was started
    # is not a host-wide lock. Found by an actual-entry test; the source-string
    # assertion it replaced could never have found it.
    if not got.is_absolute():
        raise PreflightError(
            'execution lock at %s is the RELATIVE path %s; it would resolve '
            'against the current working directory, so the inode it names '
            'depends on where the process started. Protocol 5.7 item 1 requires '
            'one host-wide file.' % (stage, got))
    same = os.path.realpath(str(got)) == os.path.realpath(str(want))
    if not same:
        raise PreflightError(
            'execution lock at %s is %s; protocol 5.7 item 1 requires the '
            'canonical host-wide file %s. A different path is a different inode '
            'and excludes nothing.' % (stage, got, want))
    return {'stage': stage, 'canonical': str(want), 'bound': str(got),
            'compared_on': 'realpath'}


def _token_roots() -> list[tuple[str, str]]:
    """(prefix string, token) pairs, longest prefix first.  Both the nominal and the
    realpath form of each root is offered, because macOS resolves /tmp and /var through
    /private."""
    raw: list[tuple[Path, str]] = [
        (WORK_ROOT, '<WORK>'),
        (RESULTS_ROOT, '<RESULTS>'),
        (REPO_ROOT, '<REPO>'),
        (Path.home(), '<HOME>'),
        (Path(tempfile.gettempdir()), '<TMP>'),
    ]
    out: list[tuple[str, str]] = []
    for p, tok in raw:
        for s in {str(p), os.path.realpath(str(p))}:
            out.append((s.rstrip('/'), tok))
    out.sort(key=lambda kv: len(kv[0]), reverse=True)
    return out


def tokenize_path(p: str | Path) -> str:
    """'<repo>/work/live_ab/T1/records/ab.json' -> '<WORK>/T1/records/ab.json'.

    Replaces, longest prefix first: WORK_ROOT -> '<WORK>', RESULTS_ROOT -> '<RESULTS>',
    REPO_ROOT -> '<REPO>', Path.home() -> '<HOME>', tempfile.gettempdir() -> '<TMP>'.
    A path that matches none of these raises UntokenizablePath."""
    s = str(p)
    for prefix, tok in _token_roots():
        if s == prefix:
            return tok
        if s.startswith(prefix + '/'):
            rest = s[len(prefix) + 1:]
            return tok + '/' + rest if rest else tok
    raise UntokenizablePath(str(p))



def display_path(p) -> str:
    """A path for a RECEIPT FIELD. Never raises.

    `tokenize_path` raises `UntokenizablePath` and `Path.relative_to` raises
    `ValueError`, both for a path outside the expected roots. Every use of either
    in a display field is a line that can abort the thing it is reporting on --
    and it has now done so three times: the write-once refusal message, the
    environment checker's `config_pin_read_from` under a drift test, and the tool
    auditor's `file` field on a synthetic module in a temp dir.

    Naming a file must never be able to fail. Tokenized when possible,
    repo-relative when possible, absolute otherwise.
    """
    q = Path(p)
    try:
        return tokenize_path(q)
    except UntokenizablePath:
        pass
    try:
        return str(q.relative_to(REPO_ROOT))
    except ValueError:
        return str(q)

# ---- canonical JSON and hashing -------------------------------------------
def canonical_json(obj: object) -> str:
    """json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    allow_nan=False).  Raises ValueError (from json) on NaN/Inf.  Floats serialize
    through repr() as CPython does."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def sha256_file(p: str | Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_canonical(obj: object) -> str:
    return sha256_text(canonical_json(obj))


# ---- durable writes --------------------------------------------------------
def fullsync(fd: int) -> None:
    """fcntl.fcntl(fd, fcntl.F_FULLFSYNC) on darwin when available, else os.fsync(fd).
    macOS os.fsync() does NOT flush the drive cache; F_FULLFSYNC does."""
    f_fullfsync = getattr(fcntl, 'F_FULLFSYNC', None)
    if sys.platform == 'darwin' and f_fullfsync is not None:
        try:
            fcntl.fcntl(fd, f_fullfsync)
            return
        except OSError:
            pass
    os.fsync(fd)


def _fullsync_dir(d: Path) -> None:
    fd = os.open(str(d), os.O_RDONLY)
    try:
        fullsync(fd)
    finally:
        os.close(fd)


def write_json_atomic(path: Path, obj: object, *, durable: bool = True) -> str:
    """Write canonical_json(obj) to <path>.tmp, fullsync, os.replace, fullsync the
    directory.  Returns the sha256 of the bytes written.  Raises WriteOnceViolation if
    path exists and its bytes differ."""
    # RESOLVE FIRST. `tokenize_path` matches absolute prefixes and raises
    # UntokenizablePath otherwise, so a caller passing a RELATIVE path made the
    # write-once refusal below raise UntokenizablePath instead of
    # WriteOnceViolation. The write was still refused -- it fails safe -- but the
    # reported reason was the wrong one, precisely when a caller most needs to be
    # told that a receipt already exists.
    path = Path(path).resolve()
    data = canonical_json(obj).encode('utf-8')
    digest = sha256_bytes(data)
    if path.exists():
        existing = path.read_bytes()
        if existing == data:
            return digest
        try:
            where = tokenize_path(path)
        except UntokenizablePath:
            # Naming the file must never be able to mask the refusal.
            where = '<UNTOKENIZABLE>/' + path.name
        raise WriteOnceViolation(
            f'{where} exists with sha256 {sha256_bytes(existing)}, '
            f'refusing to overwrite with {digest}')
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        written = os.write(fd, data)
        if written != len(data):
            raise TornWrite(f'{written} of {len(data)} bytes written to {tokenize_path(tmp)}')
        if durable:
            fullsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(path))
    if durable:
        _fullsync_dir(path.parent)
    return digest


def append_line_durable(fd: int, line: str, *, durable: bool) -> int:
    """One os.write of (line + '\\n').encode('utf-8') on an O_APPEND descriptor; fullsync
    when durable.  Returns bytes written.  Partial writes raise TornWrite."""
    if '\n' in line:
        raise TornWrite('a chain line may not contain a newline')
    data = (line + '\n').encode('utf-8')
    n = os.write(fd, data)
    if n != len(data):
        raise TornWrite(f'partial write: {n} of {len(data)} bytes')
    if durable:
        fullsync(fd)
    return n


# ---- environment provenance ------------------------------------------------
def _sysctl(name: str) -> str:
    try:
        out = subprocess.run(['sysctl', '-n', name], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    if out.returncode != 0:
        return ''
    return out.stdout.decode('utf-8', 'replace').strip()


def hardware_identity() -> str:
    """The single string ``hardware_allowlist`` lists, e.g. ``'arm64-darwin'``.

    ``hardware_info()`` is the full provenance record written at trial start; this is the
    coarse identity the frozen allowlist is expressed in, so that preflight can *compare*
    the running host with the allowlist instead of merely recording it afterwards
    (provenance review section 3: "Hardware is recorded at trial start rather than compared
    with the allowlist in the inspected preflight")."""
    return '%s-%s' % (platform.machine(), sys.platform)


def hardware_info() -> dict:
    """Host provenance in a form the event-schema string discipline accepts: the CPU brand
    string is carried as a digest, never as free text."""
    brand = _sysctl('machdep.cpu.brand_string')
    memsize = _sysctl('hw.memsize')
    ncpu = _sysctl('hw.ncpu')
    return {
        'platform': sys.platform,
        'machine': platform.machine(),
        'os_version': platform.release(),
        'cpu_brand_sha256': sha256_text(brand),
        'memsize_bytes': int(memsize) if memsize.isdigit() else 0,
        'ncpu': int(ncpu) if ncpu.isdigit() else (os.cpu_count() or 0),
    }


def package_versions() -> dict:
    """Version strings of the four permitted third-party packages plus python."""
    import importlib.metadata as md
    out: dict = {'python': platform.python_version()}
    for name in ('numpy', 'scipy', 'pandas', 'requests'):
        try:
            out[name] = md.version(name)
        except Exception:
            out[name] = '0'
    return out


def boottime_hash() -> str:
    """sha256 of `sysctl -n kern.boottime` output; '' off darwin."""
    if sys.platform != 'darwin':
        return ''
    raw = _sysctl('kern.boottime')
    return sha256_text(raw) if raw else ''


def process_rss_bytes(pattern: str) -> list[dict]:
    """[{'pid': int, 'rss_bytes': int}] for every process whose command matches `pattern`.
    The command text itself is never returned (string discipline)."""
    try:
        out = subprocess.run(['ps', '-axo', 'pid=,rss=,command='],
                             capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    rows: list[dict] = []
    for line in out.stdout.decode('utf-8', 'replace').splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        if pattern in parts[2]:
            rows.append({'pid': int(parts[0]), 'rss_bytes': int(parts[1]) * 1024})
    rows.sort(key=lambda r: r['pid'])
    return rows


# ---- freeze bundle ---------------------------------------------------------
FREEZE_BUNDLE_KEYS: tuple[str, ...] = (
    'protocol_version', 'config_sha256', 'rule_block_sha256', 'roster_sha256',
    'task_content_sha256', 'arrival_order_sha256', 'protocol_sha256', 'run_book_sha256',
    'harness_file_sha256', 'reused_file_sha256', 'winstats_sha256', 'gguf_sha256',
    'license_evidence_sha256', 'serving_manifest_sha256', 'golden_props_sha256',
    'golden_generation_settings_sha256', 'receipt_mask_sha256', 'sandbox_profile_sha256',
    'containment_probe_sha256', 'prefreeze_head', 'prefreeze_bytes', 'prefreeze_file_sha256',
    'derivation_sha256', 'planning_sha256', 'environment_lock_sha256', 'hardware_allowlist')


def _harness_files() -> tuple[str, ...]:
    names = sorted(p.name for p in HERE.glob('*.py'))
    if (HERE / 'config.json').exists():
        names.append('config.json')
    return tuple(sorted(names))


HARNESS_FILES: tuple[str, ...] = _harness_files()
REUSED_FILES: tuple[str, ...] = ('agent.py', 'sandbox.py', 'verify.py', 'data.py', 'common.py')


def _walk_for_holes(obj: object, path: str, out: list[str]) -> None:
    if obj is None:
        out.append(path or '<root>')
    elif isinstance(obj, str):
        if obj == 'unknown':
            out.append(path or '<root>')
    elif isinstance(obj, dict):
        for k in sorted(obj):
            _walk_for_holes(obj[k], f'{path}.{k}' if path else str(k), out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _walk_for_holes(v, f'{path}[{i}]', out)


def build_freeze_bundle(parts: dict) -> dict:
    """[pure] Validate that parts.keys() == set(FREEZE_BUNDLE_KEYS) exactly (no extras, no
    missing, no None, no 'unknown' anywhere in the tree) and return the canonicalised
    object.  Raises FreezeIncomplete naming every offending key."""
    if not isinstance(parts, dict):
        raise FreezeIncomplete('freeze bundle parts must be a dict')
    want = set(FREEZE_BUNDLE_KEYS)
    have = set(parts)
    missing = sorted(want - have)
    extra = sorted(have - want)
    holes: list[str] = []
    _walk_for_holes({k: parts[k] for k in sorted(have & want)}, '', holes)
    if missing or extra or holes:
        raise FreezeIncomplete(canonical_json(
            {'missing': missing, 'extra': extra, 'null_or_unknown': sorted(holes)}))
    return json.loads(canonical_json(parts))


def freeze_bundle_sha256(bundle: dict) -> str:
    """[pure] The genesis anchor value of the program chain and of the four trial chains.

    THE ONE CANONICAL DIGEST CONVENTION.  A freeze bundle's identity is the sha256 of the
    canonical JSON of its **object**, never of the bytes of the file that happens to carry
    it.  Hashing raw file bytes gives a different digest for a pretty-printed copy of the
    same bundle (provenance review section 3, ``freeze_bundle_drift`` in the root's
    witness), so every producer and consumer of a bundle digest -- the orchestrator CLI,
    preflight, the verifier, the anchor and the report builder -- goes through this
    function or through ``freeze_bundle_sha256_of_file`` below, and none of them calls
    ``sha256_file`` on ``freeze_bundle.json``."""
    return sha256_canonical(bundle)


def load_freeze_bundle(path: str | Path) -> dict:
    """Read a freeze bundle from disk.  Raises ``FreezeIncomplete`` on unreadable bytes or
    on anything that is not a JSON object, so a corrupt bundle fails closed rather than
    escaping preflight as a bare ``ValueError``."""
    try:
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise FreezeIncomplete('freeze bundle at %s is unreadable: %s'
                               % (tokenize_path(path), type(exc).__name__)) from None
    if not isinstance(obj, dict):
        raise FreezeIncomplete('freeze bundle at %s is not a JSON object'
                               % (tokenize_path(path),))
    return obj


def freeze_bundle_sha256_of_file(path: str | Path) -> str:
    """The canonical digest of the bundle stored at ``path`` (see ``freeze_bundle_sha256``).

    This is what a caller that has a *path* must use.  ``sha256_file(path)`` is the raw-byte
    digest of the same file and is NOT the bundle's identity."""
    return freeze_bundle_sha256(load_freeze_bundle(path))


def harness_file_hashes() -> dict[str, str]:
    """sha256 of every HARNESS_FILES entry, keyed by bare file name."""
    return {name: sha256_file(HERE / name) for name in HARNESS_FILES}


# ---- freeze-bundle MEMBER verification -------------------------------------
# A bundle whose canonical digest still matches the approved one proves exactly one thing:
# that nobody edited the bundle.  It proves nothing whatever about the artifacts the bundle
# NAMES.  The root's executed witness (provenance review section 3) kept an unchanged bundle
# carrying the original `config_sha256`, changed `monitor.delta` from .03 to .04, and
# preflight returned `[]`.  The two tuples below partition FREEZE_BUNDLE_KEYS into the
# members a run-time artifact determines -- which preflight recomputes and compares, one by
# one -- and the members nothing at run time determines, which are bound by the bundle digest
# alone.  The second list is DECLARED rather than silently skipped.

#: Recomputed from the deposited freeze tree and the working copy at every invocation.
BUNDLE_MEMBERS_RECOMPUTED: tuple[str, ...] = (
    'protocol_version', 'config_sha256', 'rule_block_sha256', 'roster_sha256',
    'task_content_sha256', 'arrival_order_sha256', 'harness_file_sha256',
    'reused_file_sha256', 'winstats_sha256', 'gguf_sha256', 'serving_manifest_sha256',
    'golden_props_sha256', 'golden_generation_settings_sha256', 'receipt_mask_sha256',
    'sandbox_profile_sha256', 'containment_probe_sha256', 'environment_lock_sha256',
    'hardware_allowlist')

#: Named by the bundle but not determined by any artifact a run can read: the protocol
#: document, the run book, the licence evidence, the derivation and planning records and the
#: three pre-freeze chain facts.  Covered by the bundle digest only.
BUNDLE_MEMBERS_NOT_RECOMPUTED: tuple[str, ...] = (
    'protocol_sha256', 'run_book_sha256', 'license_evidence_sha256', 'derivation_sha256',
    'planning_sha256', 'prefreeze_head', 'prefreeze_bytes', 'prefreeze_file_sha256')

#: The ``found`` value of a drift row for a member the bundle records and nothing observed.
MEMBER_ABSENT: str = '0' * 64

_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


def _member_digest(value: object) -> str:
    """The 64-hex form every drift row must carry (event schema ``DRIFT_LIST``, PG-11): a
    recorded sha256 stands for itself, anything else travels as the sha256 of its canonical
    JSON, so no free text and no path ever reaches the chain."""
    if isinstance(value, str) and _SHA256_RE.match(value):
        return value
    return sha256_canonical(value)


def _member_item(member: str, key: str | None = None) -> str:
    """A drift ``item`` label (``_LABEL_RE``: 1-64 chars of ``[A-Za-z0-9_.+-]``)."""
    label = member if key is None else '%s.%s' % (member, re.sub(r'[^A-Za-z0-9_.+-]', '-',
                                                                 str(key)))
    return label[:64]


def verify_bundle_members(bundle: dict, observed: dict) -> list[dict]:
    """[pure] Drift rows for every recomputable bundle member that does not match.

    ``bundle`` is the approved freeze bundle, held FIXED; ``observed`` is what
    ``lab_orchestrator.observed_bundle_members`` recomputed from the deposited freeze tree
    and the working copy.  Returns ``[{'item', 'expected', 'found'}]``, empty when every
    recomputable member agrees.

    * A member the bundle records and ``observed`` does not carry is drift, with
      ``found = MEMBER_ABSENT``: an artifact the freeze names must be there to be checked.
    * A dict-valued member (``harness_file_sha256``, ``gguf_sha256``, the per-trial
      ``arrival_order_sha256``, the two golden tables) is compared key by key over the UNION
      of the recorded and observed keys, so an edited file, a removed file and a newly added
      file each produce their own row.
    * ``BUNDLE_MEMBERS_NOT_RECOMPUTED`` is not examined here; those members are bound by the
      bundle digest alone and that limit is stated, not hidden.
    """
    if not isinstance(bundle, dict) or not isinstance(observed, dict):
        raise FrozenMismatch('verify_bundle_members takes two dicts')
    rows: list[dict] = []
    for member in BUNDLE_MEMBERS_RECOMPUTED:
        if member not in bundle:
            continue
        want = bundle[member]
        if member not in observed:
            rows.append({'item': _member_item(member), 'expected': _member_digest(want),
                         'found': MEMBER_ABSENT})
            continue
        got = observed[member]
        if isinstance(want, dict) or isinstance(got, dict):
            if not (isinstance(want, dict) and isinstance(got, dict)):
                rows.append({'item': _member_item(member),
                             'expected': _member_digest(want),
                             'found': _member_digest(got)})
                continue
            for key in sorted(set(want) | set(got)):
                if key in want and key in got and want[key] == got[key]:
                    continue
                rows.append({
                    'item': _member_item(member, key),
                    'expected': _member_digest(want[key]) if key in want else MEMBER_ABSENT,
                    'found': _member_digest(got[key]) if key in got else MEMBER_ABSENT})
            continue
        if want != got:
            rows.append({'item': _member_item(member), 'expected': _member_digest(want),
                         'found': _member_digest(got)})
    return rows


RULE_BLOCK_KEYS: tuple[str, ...] = (
    'rule_id', 'trials', 'execution_order', 'monitor', 'hierarchy', 'eligibility_rule',
    'tie_rule', 'enclosure', 'coin', 'seed_rule', 'roster.strata', 'roster.exclusion_rules',
    'roster.pairing', 'roster.n_pairs_rule', 'design_seed_base', 'execution.max_attempts',
    'execution.auto_abort', 'plumbing_fail_conditions', 'integrity_label_rule')


def _dotted(cfg: dict, dotted: str) -> object:
    node: object = cfg
    for part in dotted.split('.'):
        if not isinstance(node, dict) or part not in node:
            raise FrozenMismatch(f'config is missing the rule-block key {dotted!r}')
        node = node[part]
    return node


def rule_block_sha256(config: dict) -> str:
    """[pure] sha256 over the canonical JSON of the decision-defining subset of the config
    (ARCHITECTURE_FINAL.md 6.2 'rule block' == protocol Appendix B).  Everything outside
    this key list may be pinned in the pre-freeze phase without changing the hash."""
    if not isinstance(config, dict):
        raise FrozenMismatch('config must be a dict')
    block = {k: _dotted(config, k) for k in RULE_BLOCK_KEYS}
    return sha256_canonical(block)


# ---- exception taxonomy (every module raises only from this tree) ----------
class LabError(Exception):
    """Root of the live_ab exception taxonomy.  No module raises a bare Exception."""


class FreezeIncomplete(LabError): ...


class FrozenMismatch(LabError):
    """A hash, a tier table or a frozen constant differs from the bundle."""


class UntokenizablePath(LabError): ...


class WriteOnceViolation(LabError): ...


class TornWrite(LabError): ...


class ChainError(LabError):
    """Any hash-chain or ordering violation."""


class SchemaError(LabError):
    """An event body violates the schema or the string discipline."""


class SpoolError(LabError): ...


class EnclosureError(LabError):
    """An enclosure widened, or is empty, or is outside [-1, 1]."""


class MonitorError(LabError): ...


class ReceiptMismatch(LabError): ...


class ServerIdentityError(LabError): ...


class PreflightError(LabError): ...


class ServerStartFailed(LabError):
    """A server start or supervised restart failed AFTER its inputs were accepted (repair
    contract EB1, root 20:40 item 1, route (a)).

    ``record`` is the complete ``server_start_failed`` event body -- ``server_id``, ``kind``,
    ``stage``, ``findings``, ``pid``, ``returncode``, ``argv_sha256``, ``props_sha256``,
    ``load_seconds``, ``restart_index`` -- so the orchestrator appends it as raised and
    writes nothing it did not observe.  By the time this is raised the child (if one was
    launched) has already been stopped by ``lab_server.stop``; ``returncode`` is what that
    stop observed."""

    def __init__(self, record: Mapping) -> None:
        rec = dict(record)
        super().__init__('%s:%s' % (rec.get('stage'), ','.join(rec.get('findings') or [])))
        self.record = rec


class VerifyFailure(LabError):
    """The verifier's own FAIL; carries the list of findings."""

    def __init__(self, message: str, findings: list | None = None) -> None:
        super().__init__(message)
        self.findings = list(findings or [])


class AbortTrial(LabError):
    reason: str

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PauseTrial(LabError):
    reason: str

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# Helpers shared with lab_eventlog's string discipline (PG-11 / protocol 12.2 form (c)).
PATH_TOKENS: tuple[str, ...] = ('<WORK>', '<HF_CACHE>', '<LLAMA_BUILD>', '<RESULTS>',
                                '<REPO>', '<HOME>', '<TMP>', '<REMOTE>')
UID_RE = re.compile(r'^(mbpp|mbpp_full|humaneval)/[0-9]+$')


# ---------------------------------------------------------------------------
# The shared startup policy (root 2026-09-22 01:44 / 03:19)
# ---------------------------------------------------------------------------
# Root: "Move the shared stdlib directory checks to lab_common. This exact
# placement was explicitly prescribed ... Do not clone the policy into two
# implementations or ask again."  And 03:19: "The lab_common instruction was a
# design handoff, not a claim that that commit already implemented the helper.
# The owner must implement/move the one shared stdlib policy and wire the actual
# production caller."
#
# IT LIVES HERE BECAUSE OF THE IMPORT MATRIX, NOT FOR TIDINESS.
# ARCHITECTURE_FINAL.md 3.16 gives lab_common an EMPTY permitted-import set, and
# gives lab_worker and lab_orchestrator lab_common but not lab_prepare and not
# lab_injected_decision.  An earlier attempt to import lab_prepare from
# lab_worker broke the isolation gate and was reverted (commit babfa13).  A
# stdlib-only policy here is reachable from every production path without
# relaxing anything.
#
# THE POLICY IS DEFINED ONCE.  lab_prepare and lab_injected_decision delegate to
# these functions rather than carrying their own copies: two implementations of
# one refusal is how a path quietly stops being guarded.

#: The key whose PRESENCE requests the injected-decision test fixture.  Kept
#: equal to lab_injected_decision.ACTIVATION_KEY by a test, not by a comment.
FIXTURE_ACTIVATION_KEY: str = 'injected_decision_fixture'


def fixture_requested(cfg: Mapping | None) -> bool:
    """Whether a configuration asks for the injected-decision fixture.

    PRESENCE at the top level counts, whatever the value: a configuration that
    mentions the fixture at all has left the production path.  A truthy value
    under ``testing`` counts too.
    """
    cfg = cfg or {}
    if FIXTURE_ACTIVATION_KEY in cfg:
        return True
    testing = cfg.get('testing')
    return bool(isinstance(testing, Mapping) and testing.get(FIXTURE_ACTIVATION_KEY))


def assert_no_fixture(cfg: Mapping | None, *, stage: str) -> dict:
    """Refuse a fixture-requesting configuration BEFORE any dispatch or model call.

    Raises ``PreflightError``; every production entry point calls this, and the
    call sites are asserted by a test rather than promised by a docstring.
    """
    if fixture_requested(cfg):
        raise PreflightError(
            '%s: configuration requests %r. The injected-decision fixture is a '
            'TEST-ONLY control-path device and is refused on the production path, '
            'before any dispatch or model request. A trial that ran with an '
            'injected decision would not be a trial.' % (stage, FIXTURE_ACTIVATION_KEY))
    return {'stage': stage, 'injection_requested': False,
            'checked_before_dispatch': True}


#: Protocol 5.7 item 2: "TMPDIR is set to the neutral path carried in config.json
#: as the token ``<TMP>/labsbx``".
PRESCRIBED_TMPDIR_TOKEN: str = '<TMP>/labsbx'


def prescribed_tmpdir(cfg: Mapping | None, *, tmp_root: str = '/private/tmp') -> str:
    """The absolute directory ``config.sandbox.tmpdir`` prescribes.

    Raises ``PreflightError`` if the configuration does not carry the prescribed
    token at all -- a configuration that prescribes something else is not a
    configuration this harness may run under.
    """
    declared = (((cfg or {}).get('sandbox') or {}) or {}).get('tmpdir')
    if declared != PRESCRIBED_TMPDIR_TOKEN:
        raise PreflightError(
            'config.sandbox.tmpdir is %r; protocol 5.7 item 2 prescribes %r'
            % (declared, PRESCRIBED_TMPDIR_TOKEN))
    return os.path.join(tmp_root, declared.split('/', 1)[1])


def assert_tmpdir(cfg: Mapping | None, *, stage: str,
                  tmp_root: str = '/private/tmp') -> dict:
    """The ONE shared TMPDIR check, reachable from every production module.

    Root, 2026-09-22 01:44 and 03:19: "Move the shared stdlib directory checks to
    lab_common ... The owner must implement/move the one shared stdlib policy and
    wire the actual production caller."

    WHY IT IS ENFORCED AND NOT ASSUMED. Protocol 5.7 item 2 is in the passive
    voice and nothing checked it. A run that forgets to export TMPDIR silently
    gets the ambient one and therefore a DIFFERENT Seatbelt profile digest, with
    no error. That is not hypothetical: an ambient-TMPDIR digest was computed and
    promoted into config.json, ARCHITECTURE 6.1 and protocol Appendix B before
    anyone noticed. The digest depending on TMPDIR is the DESIGN; silently
    getting the wrong one is the defect.
    """
    want = prescribed_tmpdir(cfg, tmp_root=tmp_root)
    effective = os.path.realpath(tempfile.gettempdir())
    if effective != os.path.realpath(want):
        raise PreflightError(
            '%s: TMPDIR is %s but protocol 5.7 item 2 prescribes %s. The Seatbelt '
            'profile digest is a function of TMPDIR, so running under the wrong '
            'one silently produces a profile hash no production run can '
            'reproduce. Export TMPDIR=%s and retry.'
            % (stage, effective, want, want))
    return {'stage': stage, 'tmpdir': want, 'checked': True}
