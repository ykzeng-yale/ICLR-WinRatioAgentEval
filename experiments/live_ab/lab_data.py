"""Roster build, prospective exclusions, reference sweep and task-content hashing (G2).

Implements ARCHITECTURE_FINAL.md section 3.4 against protocol_FINAL.md sections 3.1-3.3.

Scope, stated once:

* The two strata are **S1** (the 427 MBPP-sanitized problems plus the 164 HumanEval problems, all of
  which the timing pilot observed) and **S2** (the 547 MBPP-full problems absent from the sanitized
  subset, none of which was ever observed).
* Every exclusion rule here is **blind to every model output**: it reads the benchmark files and, for
  rule 4, the behaviour of the task's own *reference* solution inside the sandbox. No model is called
  from this module, ever, and nothing in it depends on an arm.
* `n_pairs = n_S1 // 2 + n_S2 // 2` (protocol 3.3). It is never `n_total // 2`: pairs are formed inside
  a stratum and each stratum keeps its own leftover.
* **Allocation across strata must stay PROPORTIONAL.** **CORRECTED 2026-09-21 (root disposition
  06:35). This paragraph is the root's dictated statement; my two earlier attempts are withdrawn.**
  The first claimed proportionality made the stopped estimand invariant to the stopping time. The
  second withdrew that but still called the target the mean of the OBSERVED SCORES of enrolled pairs
  and still claimed absence of stratum-weighting bias "by construction", neither of which matches
  authoritative protocol section 10.1. The governing statement:

      Each stratum contributes `floor(n_s / 2)` pairs, and the combined pair list is uniformly
      permuted. At any fixed, non-random prefix length, the expected stratum proportions equal the
      pair-roster proportions. This does not imply the same expectation at an outcome-selected
      stopping time. The monitored targets are the enrollment-running averages of the
      history-conditional means of the hierarchical score and the success-difference score, under
      the paired serving regime defined in protocol sections 7.2 and 10.1. They are NOT the realized
      sample means and NOT a fixed full-roster contrast. No unbiasedness or stopping-time invariance
      follows merely from proportional allocation.

  Nothing in this module may weight a stratum, enroll the strata in blocks, or otherwise make a
  prefix's stratum mix depend on the arm or the outcome.
  (`ProportionalAllocationTests` in `tests_lab_design.py`.)

**Known, deliberately NOT applied here: the MBPP/HumanEval stratum separation.** Coordinator ruling 49
lists "separate MBPP from HumanEval in the strata" as a free fix, because S1 currently pairs a
sanitized-MBPP task with a HumanEval task and that cross-benchmark heterogeneity inflates the paired
score variance. The investigation sizes the gain at about **3.8% of the pairing gap** -- the gap
between the cross-arrival discordance .392 and the same-task .135 -- which is roughly 2.5% off the
betting-gate sample size and **nothing at all at the horizon this roster provides**. It is not applied
in this module because it is not a `lab_data` change: it adds a third stratum, and the stratum
vocabulary and the draw order are fixed by the literal code block of `protocol_FINAL.md` section 3.4
(`for stratum in ["S1", "S2"]`), transcribed as an independent oracle in
`tests_lab_design.protocol_3_4_reference`. Applying it here alone would silently drop the 164
HumanEval tasks from every pairing; applying it in `lab_design` alone would put the implementation
ahead of the binding document and turn that oracle into a test written from the implementation.
The separation therefore needs one coordinated amendment: protocol 3.4's code block, `lab_design.STRATA`
and its `order_document` count, `lab_eventlog.E_STRATUM`, the `Literal` annotations in `lab_coin` and
`lab_design`, the roster concatenation in `lab_orchestrator`, `dryrun_live_ab`'s mock roster, and this
module's stratum table. It also changes every `order_sha256`, which costs nothing today because no
trial episode has ever run. See the report accompanying coordinator ruling 49.

Network use is confined to `_download()`, reached only from `fetch_sources(..., offline=False)`. Every
other entry point works from cached bytes and refuses anything whose size or SHA-256 differs from the
pinned value.
"""
from __future__ import annotations

import ast
import gzip
import json
import os
import re
import tempfile
import platform
import subprocess
import time
from pathlib import Path
from typing import Callable, Literal, Sequence, TypedDict

import lab_common

# --------------------------------------------------------------------------------------------------
# Task and exclusion records (ARCHITECTURE_FINAL.md 3.4)
# --------------------------------------------------------------------------------------------------


class Task(TypedDict):
    uid: str                 # 'mbpp/2', 'mbpp_full/39', 'humaneval/0'
    benchmark: Literal['mbpp', 'mbpp_full', 'humaneval']
    stratum: Literal['S1', 'S2']       # S1 = sanitized MBPP + HumanEval, S2 = unsanitized MBPP
    prompt: str
    entry_point: str
    reference: str
    test_imports: list[str]
    test_list: list[str]
    challenge_test_list: list[str]
    test: str                # humaneval only, '' otherwise


class Exclusion(TypedDict):
    uid: str
    reason: Literal['duplicate_prompt', 'no_entry_point', 'reference_fails_verify',
                    'reference_timeout', 'out_of_design_smoke_task', 'unparsable']
    detail_sha256: str       # sha256 of the captured stderr/stdout, never the text itself


# --------------------------------------------------------------------------------------------------
# Pinned sources (protocol 3.1; the same bytes/sha256 as config.roster.sources)
# --------------------------------------------------------------------------------------------------

_GR = 'https://raw.githubusercontent.com/google-research/google-research'
_HE = 'https://raw.githubusercontent.com/openai/human-eval'
_MBPP_REV = 'f82046ba5aabbbb427dbfd38a254d26bff08b533'
_HE_REV = '463c980b59e818ace59f6f9803cd92c749ceae61'

SOURCES: dict[str, dict] = {
    'mbpp_sanitized': {
        'filename': 'sanitized-mbpp.json',
        'url': '%s/%s/mbpp/sanitized-mbpp.json' % (_GR, _MBPP_REV),
        'revision': _MBPP_REV,
        'bytes': 255053,
        'sha256': 'ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9',
        'records': 427,
        'stratum': 'S1',
        'required': True,
        'aliases': ('sanitized-mbpp.json', 'mbpp_sanitized.json'),
    },
    'humaneval': {
        'filename': 'HumanEval.jsonl.gz',
        'url': '%s/%s/data/HumanEval.jsonl.gz' % (_HE, _HE_REV),
        'revision': _HE_REV,
        'bytes': 44877,
        'sha256': 'b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef',
        'records': 164,
        'stratum': 'S1',
        'required': True,
        'aliases': ('HumanEval.jsonl.gz',),
    },
    'mbpp_full': {
        'filename': 'mbpp.jsonl',
        'url': '%s/%s/mbpp/mbpp.jsonl' % (_GR, _MBPP_REV),
        'revision': _MBPP_REV,
        'bytes': 563743,
        'sha256': 'ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f',
        'records': 974,
        'stratum': 'S2',
        # protocol 3.1: "a mismatch means roster S1" - S2 is the only optional source, and its absence
        # downgrades the roster instead of stopping the program.
        'required': False,
        'aliases': ('mbpp.jsonl', 'mbpp_full.jsonl'),
    },
}

#: Directories searched for an already-present copy of a pinned source, in order. `dest` always wins.
CACHE_SEARCH_DIRS: tuple[Path, ...] = (
    lab_common.REPO_ROOT / 'work' / 'local_stream' / 'data',
    Path('/tmp/claude-501'),
    Path(tempfile.gettempdir()),
)

#: The six out-of-design timing-pilot tasks (protocol 3.2 rule 1, config roster.smoke_tasks).
SMOKE_TASKS: tuple[str, ...] = ('mbpp_full/39', 'mbpp_full/122', 'mbpp_full/522',
                                'mbpp_full/547', 'mbpp_full/869', 'mbpp_full/966')

UID_PATTERN: str = r'^(mbpp|mbpp_full|humaneval)/[0-9]+$'
_UID_RE = re.compile(UID_PATTERN)

#: The stratum of each benchmark (protocol 3.1/3.3), as ONE table rather than string literals spread
#: through the module. `mbpp` (sanitized) and `humaneval` SHARE S1 today; giving HumanEval its own
#: stratum -- coordinator ruling 49's free fix -- is a one-line change here plus the coordinated
#: amendment the module docstring lists, and it must not be made in this file alone.
BENCHMARK_STRATUM: dict[str, str] = {'mbpp': 'S1', 'humaneval': 'S1', 'mbpp_full': 'S2'}

#: The stratum labels, in the order protocol 3.4 draws them. Pairs never cross a stratum.
STRATA: tuple[str, ...] = ('S1', 'S2')

#: protocol 3.2 rule 4: "more than half of the 5 s verifier wall limit".  The frozen config pins the
#: sandbox wall limit at 10.0 s (`sandbox.timeout_s`); the exclusion threshold below is the protocol's
#: and is *not* derived from that key.  See the disagreement note in the module docstring of the tests.
REFERENCE_VERIFIER_WALL_LIMIT_S: float = 5.0
REFERENCE_TIME_FRACTION: float = 0.5
#: Each reference is verified this many times; a single failure in any run excludes the task.
REFERENCE_SWEEP_RUNS: int = 2

ROSTER_SCHEMA: str = 'live_ab/roster-v1'

_pilot_cache: dict[str, object] = {}


def _pilot():
    """Import the pilot's `data` module through `lab_common.add_import_paths()` (matrix row `(s)`).

    Imported lazily so that `lab_data` can be imported (and its pure functions used) on a host where
    `experiments/local_stream/` is not importable.
    """
    mod = _pilot_cache.get('data')
    if mod is None:
        lab_common.add_import_paths()
        import data as _ls_data          # noqa: E402  (deliberately late)
        _pilot_cache['data'] = mod = _ls_data
    return mod


def _pilot_verify():
    """Import the pilot's `verify` module (used only by `sweep_references`)."""
    mod = _pilot_cache.get('verify')
    if mod is None:
        lab_common.add_import_paths()
        import verify as _ls_verify      # noqa: E402
        _pilot_cache['verify'] = mod = _ls_verify
    return mod


# --------------------------------------------------------------------------------------------------
# Source acquisition
# --------------------------------------------------------------------------------------------------


def _safe_token(p: Path) -> str:
    """`lab_common.tokenize_path` when the path is under a known root, else '<EXTERNAL>/<name>'.

    `fetch_sources` may legitimately read a cached copy from a directory that is under none of the
    tokenizable roots; the manifest still must not carry an absolute path.
    """
    try:
        return lab_common.tokenize_path(p)
    except Exception:
        return '<EXTERNAL>/' + Path(p).name


def _check_bytes(name: str, data: bytes, origin: str) -> None:
    spec = SOURCES[name]
    got_bytes, got_sha = len(data), lab_common.sha256_bytes(data)
    if got_bytes != spec['bytes'] or got_sha != spec['sha256']:
        raise lab_common.FrozenMismatch(
            'pinned source %r from %s: expected %d bytes sha256 %s, found %d bytes sha256 %s'
            % (name, origin, spec['bytes'], spec['sha256'], got_bytes, got_sha))


def _find_cached(name: str, dest: Path) -> Path | None:
    spec = SOURCES[name]
    for directory in (dest,) + CACHE_SEARCH_DIRS:
        for alias in spec['aliases']:
            candidate = Path(directory) / alias
            try:
                if candidate.is_file():
                    return candidate
            except OSError:
                continue
    return None


def _download(url: str, timeout: float = 120.0) -> bytes:
    """The ONLY network access in this module. Never called with `offline=True`."""
    import requests      # imported here so that the offline path never needs it
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def fetch_sources(dest: Path, *, offline: bool = False) -> dict:
    """Download (or reuse the cached copy of) every pinned source; verify bytes and sha256.

    Raises `FrozenMismatch` on any difference from `SOURCES`. `offline=True` refuses to use the network
    and requires every file to be present in `dest` or in `CACHE_SEARCH_DIRS`; a missing **required**
    source then raises `PreflightError`. A missing or mismatching `mbpp_full` is reported as
    `roster_mode == 'S1'` instead of stopping the caller (protocol 3.1: "a mismatch means roster S1").

    Side effects: writes `dest/<filename>` for every source it resolved, and `dest/sources.json`.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    manifest: dict = {'dest': _safe_token(dest), 'offline': bool(offline), 'sources': {}}
    for name, spec in SOURCES.items():
        target = dest / spec['filename']
        cached = _find_cached(name, dest)
        origin: str
        if cached is not None:
            data = cached.read_bytes()
            origin = _safe_token(cached)
            from_cache = True
        elif offline:
            if spec['required']:
                raise lab_common.PreflightError(
                    'offline=True and no cached copy of pinned source %r (looked for %s)'
                    % (name, ', '.join(spec['aliases'])))
            manifest['sources'][name] = {'present': False, 'reason': 'absent_offline'}
            continue
        else:
            data = _download(spec['url'])
            origin = 'network'
            from_cache = False
        try:
            _check_bytes(name, data, origin)
        except lab_common.FrozenMismatch:
            if spec['required']:
                raise
            manifest['sources'][name] = {'present': False, 'reason': 'hash_mismatch'}
            continue
        if not target.exists():
            tmp = target.with_suffix(target.suffix + '.tmp')
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            try:
                os.write(fd, data)
                lab_common.fullsync(fd)
            finally:
                os.close(fd)
            os.replace(tmp, target)
        manifest['sources'][name] = {
            'present': True, 'filename': spec['filename'], 'bytes': len(data),
            'sha256': lab_common.sha256_bytes(data), 'revision': spec['revision'],
            'records': spec['records'], 'stratum': spec['stratum'],
            'from_cache': from_cache, 'origin': origin, 'path': _safe_token(target)}
    manifest['roster_mode'] = 'EXT' if manifest['sources'].get('mbpp_full', {}).get('present') else 'S1'
    lab_common.write_json_atomic(dest / 'sources.json', manifest, durable=True)
    return manifest


def load_raw(sources_dir: Path) -> dict:
    """Parse the pinned files in `sources_dir` into `{'mbpp_sanitized': [...], ...}`.

    Every file present is hash-checked again; an absent `mbpp_full` yields roster S1 (the key is simply
    missing from the result). Side effect: reads files.
    """
    sources_dir = Path(sources_dir)
    raw: dict = {}
    for name, spec in SOURCES.items():
        path = sources_dir / spec['filename']
        if not path.is_file():
            alt = _find_cached(name, sources_dir)
            if alt is None:
                if spec['required']:
                    raise lab_common.PreflightError('pinned source %r not found under %s'
                                                    % (name, _safe_token(sources_dir)))
                continue
            path = alt
        data = path.read_bytes()
        try:
            _check_bytes(name, data, _safe_token(path))
        except lab_common.FrozenMismatch:
            if spec['required']:
                raise
            continue
        if name == 'humaneval':
            with gzip.open(path, 'rt') as handle:
                records = [json.loads(line) for line in handle if line.strip()]
        elif spec['filename'].endswith('.jsonl'):
            records = [json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip()]
        else:
            records = json.loads(data.decode('utf-8'))
        if len(records) != spec['records']:
            raise lab_common.FrozenMismatch('pinned source %r: expected %d records, found %d'
                                            % (name, spec['records'], len(records)))
        raw[name] = records
    return raw


# --------------------------------------------------------------------------------------------------
# Canonicalisation
# --------------------------------------------------------------------------------------------------


def normalize_prompt(text: str) -> str:
    """Prompt normalisation of `experiments/local_stream/timing_pilot.py:35-36` (protocol 3.2 rule 2).

    Two lines, replicated rather than imported because importing `timing_pilot` pulls in the pilot's
    agent and run-loop modules. `tests_lab_design.test_normalization_matches_pilot` extracts those two
    lines from the pilot file and asserts this function agrees with them.
    """
    return re.sub(r'\W+', ' ', (text or '').lower()).strip()


def _mbpp_task(rec: dict, *, benchmark: str, stratum: str) -> Task:
    entry = _pilot().mbpp_entry_point({'test_list': list(rec.get('test_list') or []),
                                       'code': rec.get('code') or ''})
    # The sanitized file carries `prompt`/`test_imports`; the full release carries `text`/
    # `test_setup_code`. Both are canonicalised into the same Task shape.
    prompt = rec['prompt'] if 'prompt' in rec else rec['text']
    if 'test_imports' in rec:
        imports = [s for s in (rec.get('test_imports') or []) if str(s).strip()]
    else:
        setup = (rec.get('test_setup_code') or '').strip()
        imports = [setup] if setup else []
    return Task(uid='%s/%d' % (benchmark, int(rec['task_id'])), benchmark=benchmark, stratum=stratum,
                prompt=(prompt or '').strip(), entry_point=entry, reference=rec.get('code') or '',
                test_imports=imports, test_list=list(rec.get('test_list') or []),
                challenge_test_list=list(rec.get('challenge_test_list') or []), test='')


def build_candidate_tasks(raw: dict) -> list[Task]:
    """[pure, apart from the lazy import of the pilot's `data`] Canonicalise the sources into Tasks.

    Ordering is frozen: mbpp (sanitized) by numeric id, then mbpp_full by numeric id, then humaneval by
    numeric index.

    **Deviation from ARCHITECTURE_FINAL.md 3.4, reported rather than hidden.** That section says a
    duplicate-prompt `mbpp_full` task "is dropped here with reason 'duplicate_prompt'", but the declared
    return type carries no channel for a reason, and protocol 3.2 requires every exclusion *with its
    reason* to be frozen in `roster.json`. This function therefore returns the full candidate list and
    `prospective_exclusions()` records the duplicates; `build_roster()` drops them. The surviving roster
    is identical either way.
    """
    if 'mbpp_sanitized' not in raw or 'humaneval' not in raw:
        raise lab_common.PreflightError('build_candidate_tasks needs mbpp_sanitized and humaneval')
    tasks: list[Task] = []
    for rec in sorted(raw['mbpp_sanitized'], key=lambda r: int(r['task_id'])):
        tasks.append(_mbpp_task(rec, benchmark='mbpp', stratum=BENCHMARK_STRATUM['mbpp']))
    sanitized_ids = {int(r['task_id']) for r in raw['mbpp_sanitized']}
    for rec in sorted(raw.get('mbpp_full') or [], key=lambda r: int(r['task_id'])):
        if int(rec['task_id']) in sanitized_ids:
            continue                       # the sanitized version is the S1 task; S2 is the complement
        tasks.append(_mbpp_task(rec, benchmark='mbpp_full', stratum=BENCHMARK_STRATUM['mbpp_full']))
    for rec in sorted(raw['humaneval'], key=lambda r: int(str(r['task_id']).split('/')[-1])):
        idx = int(str(rec['task_id']).split('/')[-1])
        tasks.append(Task(uid='humaneval/%d' % idx, benchmark='humaneval',
                          stratum=BENCHMARK_STRATUM['humaneval'],
                          prompt=rec['prompt'], entry_point=rec['entry_point'],
                          reference=rec['prompt'] + rec['canonical_solution'],
                          test_imports=[], test_list=[], challenge_test_list=[], test=rec['test']))
    uids = [t['uid'] for t in tasks]
    if len(set(uids)) != len(uids):
        raise lab_common.FrozenMismatch('duplicate uid in the canonicalised task list')
    for uid in uids:
        if not _UID_RE.match(uid):
            raise lab_common.SchemaError('uid %r violates %s' % (uid, UID_PATTERN))
    return tasks


def to_pilot_task(task: Task) -> dict:
    """The dict shape `experiments/local_stream/{agent,verify}.py` expect.

    Needed because those modules switch on `benchmark == 'mbpp'` and read `signature_example`, neither
    of which the `Task` record of ARCHITECTURE 3.4 provides for stratum S2. Reported as a gap; the
    mapping itself is mechanical and changes no task content.
    """
    benchmark = 'mbpp' if task['benchmark'] in ('mbpp', 'mbpp_full') else task['benchmark']
    out = dict(uid=task['uid'], benchmark=benchmark, entry_point=task['entry_point'],
               prompt=task['prompt'], reference=task['reference'],
               test_imports=list(task['test_imports']), test_list=list(task['test_list']),
               challenge_test_list=list(task['challenge_test_list']),
               signature_example=task['test_list'][0] if task['test_list'] else '')
    if task['benchmark'] == 'humaneval':
        out['test'] = task['test']
    return out


def task_content_hash(task: Task) -> str:
    """[pure] sha256 over the canonical JSON of one full task object (the per-task content hash)."""
    return lab_common.sha256_canonical(_content_view(task))


def _content_view(task: Task) -> dict:
    return {'uid': task['uid'], 'benchmark': task['benchmark'], 'stratum': task['stratum'],
            'prompt': task['prompt'], 'entry_point': task['entry_point'],
            'reference': task['reference'], 'test_imports': list(task['test_imports']),
            'test_list': list(task['test_list']),
            'challenge_test_list': list(task['challenge_test_list']), 'test': task['test']}


# --------------------------------------------------------------------------------------------------
# Exclusions
# --------------------------------------------------------------------------------------------------


def _exclusion(uid: str, reason: str, detail: str) -> Exclusion:
    return Exclusion(uid=uid, reason=reason, detail_sha256=lab_common.sha256_text(detail))


# ---------------------------------------------------------------------------
# D1 REPAIR: the detail PREIMAGE is retained, and its canonicalization is a rule
# ---------------------------------------------------------------------------
# Root, 2026-09-21 18:54: "Persist the complete per-attempt verifier record used to
# construct each detail digest, with an explicit canonicalization rule; reconstruct
# the roster/hash from those saved records ... If current code hashes details then
# discards the preimage, repair retention now."
#
# It did.  `sweep_references` built a detail string inline, hashed it into
# `detail_sha256`, and dropped the string on the floor.  Nothing could afterwards
# reconstruct what had been hashed, so the roster identity was unverifiable against
# its own evidence -- not because the hash was wrong, but because its preimage was
# gone.  (Root also corrected my overstatement that this made the roster
# "unfreezable": a hash of recorded bytes stays recomputable FROM THOSE BYTES.  The
# defect is retention, and this is the retention repair.)
#
# THE CANONICALIZATION RULE, stated once and used by both the producer and the
# reconstructor, so they cannot drift:
#   detail = "\n".join("run{i}:{stdout_tail}|{stderr}" for each attempt, in order)
# That is byte-for-byte what the previous inline construction produced, so retained
# records reconstruct digests recorded BEFORE this repair as well as after it.
ATTEMPT_RECORD_SCHEMA: str = 'live_ab/reference_attempt-v1'

#: THE NAMED CLOCK DOMAINS, root 2026-09-22 03:19 (clock_domain_root_decision):
#: "Record both clocks, with explicit domains; use one named domain for lifecycle
#:  comparisons. The existing requirement meant the same clock source and epoch,
#:  not merely the same machine."
#:
#: Measured on this host: the two differ by 694.15 s
#: (results/live_ab/CLOCK_DOMAIN_FINDING.json). The legacy readings keep their
#: operational timeout/duration semantics; the POSIX readings exist ONLY to be
#: compared with server lifecycle events, which read the same POSIX clock.
CLOCK_DOMAIN_LEGACY = 'time.monotonic'
CLOCK_DOMAIN_POSIX = 'clock_gettime(CLOCK_MONOTONIC)'
INTERVAL_SCHEMA_V3 = 'live_ab/attempt_interval-v3'


def _posix_monotonic_ns() -> "int | None":
    """``clock_gettime_ns(CLOCK_MONOTONIC)``, integer nanoseconds, or None.

    Root: "Record integer nanoseconds and explicit conversion from any server
    microseconds; the representation does not imply nanosecond accuracy." The
    integer is the representation, not a claim about resolution.

    None on a platform without the clock: root requires an unsupported clock to
    REFUSE COVERAGE and retain the attempt, never to exclude a task.
    """
    clk = getattr(time, 'CLOCK_MONOTONIC', None)
    if clk is None:                                            # pragma: no cover
        return None
    try:
        return int(time.clock_gettime_ns(clk))
    except (AttributeError, OSError):                          # pragma: no cover
        return None


class ProvenanceUnavailable(lab_common.PreflightError):
    """Required clock provenance could not be read. There is no fallback."""


#: The declared sources. Recorded so a consumer knows WHAT was read, not only
#: that something was.
BOOT_SOURCE = 'sysctl kern.bootsessionuuid'
HOST_SOURCE = 'platform.node'

#: Values that must never be accepted as an identity. Root's counterexamples:
#: two records with boot_id None, or both 'unknown', CERTIFIED -- because the
#: check was metadata EQUALITY, and two equally absent identities are equal.
PLACEHOLDER_IDENTITIES = frozenset({'', 'unknown', 'none', 'null', 'n/a', '-'})


def _digest_identity(raw: str, kind: str) -> str:
    """``<kind>:<sha256[:32]>`` -- never the raw machine identifier.

    Root: "retain its cryptographic digest plus a declared source, not its raw
    value in shared artifacts."
    """
    return '%s:%s' % (kind, lab_common.sha256_text(raw)[:32])


def boot_identity() -> str:
    """The KERNEL boot-session identity, digested. Refuses if unavailable.

    REPLACED 2026-09-22 after root's review. The previous version returned
    ``'boot:%d' % int(time.time() - posix_ns/1e9)`` -- second-truncated
    wall-minus-clock arithmetic, which is **not a boot session identity**. Root's
    witness: a deterministic same-POSIX-time/different-wall pair returns
    ``boot:900`` then ``boot:901``, so it discriminates nothing reliably, and the
    test named "changes when the clock restarts" merely called the helper twice.
    The earlier review had already rejected reading a difference between clock
    families as an immutable offset; this was the same mistake wearing an
    identity's name.

    There is NO fallback. Root: "Unsupported sources refuse; do not fall back to
    wall-minus-clock or 'unknown'."
    """
    try:
        out = subprocess.run(['sysctl', '-n', 'kern.bootsessionuuid'],
                             capture_output=True, text=True, timeout=30)
    except Exception as exc:                                   # noqa: BLE001
        raise ProvenanceUnavailable(
            'the kernel boot-session identity could not be read (%s: %s). There is '
            'no fallback: wall-minus-clock arithmetic is not a boot identity and '
            "'unknown' is not an identity." % (type(exc).__name__, exc)) from None
    raw = (out.stdout or '').strip()
    if out.returncode != 0 or not raw or raw.lower() in PLACEHOLDER_IDENTITIES:
        raise ProvenanceUnavailable(
            'the kernel boot-session identity is unavailable on this host '
            '(%s returned %r). Preparation refuses rather than recording a '
            'placeholder.' % (BOOT_SOURCE, raw[:40]))
    return _digest_identity(raw, 'boot')


def host_identity() -> str:
    """The host identity, digested. Refuses on a placeholder.

    Root: "Require nonempty, non-placeholder host and kernel boot-session
    identities on BOTH producer and observer, matching the declared owner host
    and current boot. Metadata equality alone is insufficient."
    """
    raw = (platform.node() or '').strip()
    if not raw or raw.lower() in PLACEHOLDER_IDENTITIES:
        raise ProvenanceUnavailable(
            'the host identity is unavailable or a placeholder (%r)' % (raw[:40],))
    return _digest_identity(raw, 'host')


def clock_provenance() -> dict:
    """Everything a consumer needs to decide whether two readings share a
    timeline: which clock, which host, which boot, and where each came from."""
    return {
        'clock_domain_posix': CLOCK_DOMAIN_POSIX,
        'boot_id': boot_identity(),
        'boot_source': BOOT_SOURCE,
        'host_id': host_identity(),
        'host_source': HOST_SOURCE,
        'units': 'integer nanoseconds',
    }


def attempt_record(uid: str, run_index: int, result: dict,
                   started_monotonic: "float | None" = None,
                   ended_monotonic: "float | None" = None,
                   lock_requested_monotonic: "float | None" = None,
                   lock_acquired_monotonic: "float | None" = None,
                   verification_started_monotonic: "float | None" = None,
                   verification_ended_monotonic: "float | None" = None,
                   lock_released_monotonic: "float | None" = None,
                   verification_started_posix_ns: "int | None" = None,
                   verification_ended_posix_ns: "int | None" = None,
                   boot_id: "str | None" = None,
                   host_id: "str | None" = None,
                   boot_source: "str | None" = None,
                   host_source: "str | None" = None) -> dict:
    """The COMPLETE per-attempt verifier record, retained rather than discarded.

    Carries the two fields the digest is built from (`stdout_tail`, `stderr`), the
    flags and measured duration root required kept explicitly, and the RAW
    verifier payload, so nothing that went into a classification is lost.

    CORRECTED 2026-09-21 19:29, root: "D1 must read the actual top-level sentinel
    flag ... A clean process exit is not a verification sentinel."  My first
    version set ``sentinel_seen`` from ``run['passed']``, which is
    ``rc == 0 and not timed_out`` -- a CLEAN EXIT.  The sentinel exists precisely
    to catch a candidate that exits 0 without running the tests (verify.py's own
    docstring: "a candidate that exits early with status 0 (sys.exit,
    SystemExit...)"), so reading `passed` as the sentinel defeated the check it
    was named after.  ``verify()`` returns ``sentinel_seen`` and ``timed_out`` at
    the TOP LEVEL; both are read from there now, with the nested run dict used
    only as a fallback for the sandbox-level fields it alone carries.
    """
    result = result or {}
    run = result.get('run') or {}
    return {
        'schema': ATTEMPT_RECORD_SCHEMA,
        'uid': uid,
        'run_index': int(run_index),
        # --- the digest preimage, verbatim -------------------------------
        'stdout_tail': run.get('stdout_tail', ''),
        'stderr': run.get('stderr', ''),
        # --- the flags and duration (D3), from the TOP LEVEL --------------
        'success': bool(result.get('success')),
        'timed_out': bool(result.get('timed_out', run.get('timed_out'))),
        'sentinel_seen': bool(result.get('sentinel_seen')),
        'entry_point_defined': bool(result.get('entry_point_defined')),
        'sandbox_flag': bool(result.get('sandbox_flag')),
        'clean_exit': bool(run.get('passed')),   # NOT the sentinel; kept distinctly
        'returncode': run.get('returncode'),
        'verify_seconds': float(result.get('verify_seconds') or 0.0),
        # --- the attempt's own interval, on ONE monotonic clock -----------
        # Root 21:17 requires comparing verifier start/end times against active
        # load windows. Without endpoints on a single clock there is nothing to
        # compare, and coverage degenerates to metadata presence.
        # Root 22:56: "The new constructor always marks interval_schema v2 even
        # when invoked with only legacy positional endpoints." It no longer does:
        # the label follows what was actually supplied.
        # v3 adds the NAMED POSIX clock readings beside the legacy ones; the
        # label still follows what was actually supplied, never what the
        # constructor hopes was supplied.
        'interval_schema': (
            INTERVAL_SCHEMA_V3
            # v3 means: both clocks AND the provenance that makes them
            # comparable. Root: "Do not cure it by relabelling incomplete records
            # as v3 without declaring the missing data."
            if (verification_started_monotonic is not None
                and verification_ended_monotonic is not None
                and isinstance(verification_started_posix_ns, int)
                and isinstance(verification_ended_posix_ns, int)
                and bool(boot_id) and bool(host_id))
            else 'live_ab/attempt_interval-v2'
            if (verification_started_monotonic is not None
                and verification_ended_monotonic is not None)
            else 'live_ab/attempt_interval-v1'),
        # the CERTIFIED interval: the verifier call itself, inside the lock
        'verification_started_monotonic': verification_started_monotonic,
        'verification_ended_monotonic': verification_ended_monotonic,
        # --- THE NAMED POSIX DOMAIN, root 2026-09-22 03:19 -----------------
        # Kept SEPARATE from the legacy readings, which keep their operational
        # timeout/duration semantics. These exist only to be compared with server
        # lifecycle events, which read the same POSIX clock. Integer nanoseconds;
        # the representation does not imply nanosecond accuracy.
        'clock_domain_legacy': CLOCK_DOMAIN_LEGACY,
        'clock_domain_posix': CLOCK_DOMAIN_POSIX,
        'verification_started_posix_ns': verification_started_posix_ns,
        'verification_ended_posix_ns': verification_ended_posix_ns,
        'posix_units': 'integer nanoseconds',
        'boot_id': boot_id,
        'host_id': host_id,
        'boot_source': boot_source,
        'host_source': host_source,
        # retained beside it, never certified, never overwritten
        'lock_requested_monotonic': lock_requested_monotonic,
        'lock_acquired_monotonic': lock_acquired_monotonic,
        'lock_released_monotonic': lock_released_monotonic,
        'lock_wait_s': (None if (lock_acquired_monotonic is None
                                 or lock_requested_monotonic is None)
                        else lock_acquired_monotonic - lock_requested_monotonic),
        # v1 spelling, kept so pre-v2 records still parse
        'started_monotonic': started_monotonic,
        'ended_monotonic': ended_monotonic,
        # --- the RAW payload, preserved whole ----------------------------
        # Root: "preserve the raw verifier payload".  A record that keeps only the
        # fields I thought mattered is the same defect as hashing a detail and
        # discarding it: it decides in advance what a later question may ask.
        'raw_verifier_payload': result,
    }


class AttemptLedger:
    """A durable append-only sink for retained attempt records.

    Root: "wire the callback to a durable production preparation ledger ... loss
    or failure of the sink must stop preparation rather than silently continue."

    So ``append`` fsyncs and does NOT swallow errors: a sink that cannot record is
    a preparation that must stop, because continuing would produce exclusions
    whose preimage is again unavailable -- the very defect D1 repairs.
    """

    def __init__(self, path: "str | Path") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.count = 0

    def append(self, record: dict) -> None:
        """Append one record durably, or raise. Never report a partial write as success.

        SHORT-WRITE REPAIR, root 2026-09-21 20:05. The first version issued ONE
        ``os.write`` and ignored its return value. ``os.write`` may legally accept
        only part of the buffer and return a positive count WITHOUT raising, so a
        truncated record was recorded as a successful append: root's injected
        witness produced ``count == 1``, a 219-byte tail with no newline, and a
        ``JSONDecodeError`` on reload. That is precisely the fail-closed contract
        this class exists to provide, broken by the class itself.

        Now: encode once, write until every byte is accepted, fail on a zero or
        non-progressing write, sync, and only THEN count the record. An incomplete
        tail from a failed append is deliberately LEFT ON DISK as failure evidence,
        and ``load`` refuses to read past it rather than silently skipping it.
        """
        payload = (lab_common.canonical_json(record) + '\n').encode('utf-8')
        created = not self.path.exists()
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            written = 0
            while written < len(payload):
                n = os.write(fd, payload[written:])
                if n <= 0:
                    # No progress. Raising here leaves whatever was accepted on
                    # disk as evidence; it must never be reported as an append.
                    raise OSError(
                        'ledger append made no progress after %d of %d bytes; '
                        'the retained record is incomplete and this preparation '
                        'must stop' % (written, len(payload)))
                written += n
            lab_common.fullsync(fd)
        finally:
            os.close(fd)
        if created:
            # fsync of the file does not make a NEW directory entry durable.
            lab_common._fullsync_dir(self.path.parent)
        self.count += 1

    def load(self) -> list[dict]:
        """Every retained record, or raise on a malformed tail.

        Root: "refuse a continuation that would append onto malformed JSON without
        an explicit preserved-tail recovery rule." A truncated final line is the
        signature of a failed append, and silently dropping it would hide exactly
        the loss this ledger exists to make impossible. The rule is: the tail is
        PRESERVED on disk and reported, never skipped and never overwritten.
        """
        if not self.path.is_file():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b'\n'):
            raise ValueError(
                'ledger %s ends with an incomplete record (%d bytes, no trailing '
                'newline). This is retained failure evidence from a short or failed '
                'append. Resolve it explicitly -- preserve the tail and decide '
                'whether a new preparation run is needed -- before appending again.'
                % (lab_common.tokenize_path(self.path), len(raw)))
        out: list[dict] = []
        for i, line in enumerate(raw.decode('utf-8').splitlines()):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(
                    'ledger %s line %d is not valid JSON (%s); the tail is retained '
                    'as failure evidence and is not skipped'
                    % (lab_common.tokenize_path(self.path), i + 1, exc)) from None
        return out

    def attempts_for(self, uid: str) -> list[dict]:
        return [r for r in self.load() if r.get('uid') == uid]


def detail_from_attempts(attempts: Sequence[dict]) -> str:
    """THE canonicalization rule. Both the producer and any reconstructor use this.

    Reconstruction check, for any retained attempt list:
        lab_common.sha256_text(detail_from_attempts(attempts)) == exclusion['detail_sha256']
    """
    return '\n'.join('run%d:%s|%s' % (int(a['run_index']), a['stdout_tail'], a['stderr'])
                     for a in attempts)


def reconstruct_detail_sha256(attempts: Sequence[dict]) -> str:
    """The exclusion's `detail_sha256`, recomputed from retained records alone."""
    return lab_common.sha256_text(detail_from_attempts(attempts))


#: D3 REPAIR: the documented precedence when more than one condition holds.
#: Root: "classify genuine timeout distinctly from non-timeout verifier failure,
#: with documented precedence if multiple conditions hold. Preserve the same
#: exclusion set implied by the protocol, not a success-favoring change."
#:
#: Before the repair the order was (not success) -> (slow), so a wall-clock TIMEOUT
#: -- which sets passed False in sandbox.py:196 and hence success False -- was filed
#: `reference_fails_verify`, and `reference_timeout` could fire only for a run that
#: SUCCEEDED but took over the threshold.  The two reasons did not mean what their
#: names say, and protocol 3.5 item 7's timeout count was systematically understated.
#:
#: The exclusion SET is unchanged by this repair: every attempt excluded before is
#: still excluded, because a timed-out attempt was already failing. Only its REASON
#: moves, from `reference_fails_verify` to `reference_timeout`.
EXCLUSION_PRECEDENCE: tuple[tuple[str, str], ...] = (
    ('timed_out', 'reference_timeout'),
    ('not_success', 'reference_fails_verify'),
    ('over_threshold', 'reference_timeout'),
)


def classify_attempt(record: dict, threshold_s: float) -> "str | None":
    """The exclusion reason for one attempt, or None. Precedence as documented above."""
    if record['timed_out']:
        return 'reference_timeout'          # a GENUINE hang, not a verifier failure
    if not record['success']:
        return 'reference_fails_verify'     # exited non-zero or no sentinel
    if record['verify_seconds'] > threshold_s:
        return 'reference_timeout'          # succeeded but over the wall threshold
    return None


def prospective_exclusions(tasks: list[Task], cfg: dict) -> list[Exclusion]:
    """[pure] The exclusions of protocol 3.2 that need no execution: rules 1, 2, 3 and `unparsable`.

    Blind to every model output. Order is frozen: by the position of the task in `tasks`, then by the
    fixed reason order, so the list is a deterministic function of the sources.
    """
    roster_cfg = (cfg or {}).get('roster') or {}
    smoke = tuple(roster_cfg.get('smoke_tasks') or SMOKE_TASKS)
    s1_prompts: dict[str, str] = {}
    for task in tasks:
        # D6 REPAIR, root 2026-09-21 18:54: "Apply the declared normalized-prompt
        # duplicate rule against ALL S1 tasks, including HumanEval; record if counts
        # stay unchanged."  The rule (protocol 3.2 item 2) says "S2 problems whose
        # normalized prompt duplicates an S1 task" -- an S1 TASK, with no benchmark
        # qualifier.  The `and task['benchmark'] == 'mbpp'` clause made the code
        # narrower than the rule it implements, silently skipping the 164 HumanEval
        # prompts.  On the delivered sources this changes NO count (verified: zero
        # additional duplicates), which is exactly why it had gone unnoticed.
        if task['stratum'] == 'S1':
            s1_prompts.setdefault(normalize_prompt(task['prompt']), task['uid'])
    out: list[Exclusion] = []
    for task in tasks:
        uid = task['uid']
        if uid in smoke:
            out.append(_exclusion(uid, 'out_of_design_smoke_task', 'protocol_3.2_rule_1'))
            continue
        if task['stratum'] != 'S2':
            continue                       # rules 2-3 are S2-only (protocol 3.2 items 2 and 3)
        twin = s1_prompts.get(normalize_prompt(task['prompt']))
        if twin is not None:
            out.append(_exclusion(uid, 'duplicate_prompt', 'duplicate_of:' + twin))
            continue
        if not task['entry_point']:
            out.append(_exclusion(uid, 'no_entry_point', 'mbpp_entry_point_returned_empty'))
            continue
        try:
            ast.parse(task['reference'])
        except SyntaxError as exc:
            out.append(_exclusion(uid, 'unparsable', 'SyntaxError:%s' % (exc.msg,)))
    return out


class _ExecutionLock:
    """The host-wide execution lock of protocol 5.7, as a context manager (flock, exclusive)."""

    def __init__(self, path: Path, max_wait_s: float) -> None:
        self.path = Path(path)
        self.max_wait_s = float(max_wait_s)
        self._fd: int | None = None

    def __enter__(self) -> '_ExecutionLock':
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + self.max_wait_s
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    raise lab_common.PreflightError('execution lock not acquired within %.1f s'
                                                    % self.max_wait_s)
                time.sleep(0.05)

    def __exit__(self, *exc) -> None:
        import fcntl
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None


def sweep_references(tasks: list[Task], cfg: dict, *, on_progress: Callable | None = None,
                     on_attempt: Callable | None = None) -> list[Exclusion]:
    """Protocol 3.2 rule 4: verify every task's own reference solution, twice, under the sandbox.

    A task is excluded `reference_fails_verify` if either run fails, and `reference_timeout` if either
    run's verifier wall time exceeds `REFERENCE_TIME_FRACTION * REFERENCE_VERIFIER_WALL_LIMIT_S`.

    Side effects: sandbox subprocesses, temporary directories, and the host-wide execution lock held
    for each execution. **No model call.** The caller is responsible for the load regime protocol 3.2
    rule 4 prescribes (a 1,024-token generation running on the coder server during the sweep); this
    function neither starts nor contacts a server. `tasks` is never mutated.
    """
    verify_mod = _pilot_verify()
    sandbox_cfg = (cfg or {}).get('sandbox') or {}
    timeout_s = float(sandbox_cfg.get('timeout_s', 10.0))
    cpu_s = int(sandbox_cfg.get('cpu_s', 10))
    output_cap = int(sandbox_cfg.get('output_cap_bytes', 65536))
    mem_bytes = int(sandbox_cfg.get('mem_bytes_requested_not_enforced_on_macos', 2 << 30))
    lock_path = Path(sandbox_cfg.get('execution_lock_path')
                     or (lab_common.WORK_ROOT / 'sandbox.lock'))
    max_lock_wait_s = float(((cfg or {}).get('execution') or {}).get('max_lock_wait_s', 120))
    threshold = REFERENCE_TIME_FRACTION * REFERENCE_VERIFIER_WALL_LIMIT_S
    # REFUSE BEFORE DISPATCH, root 2026-09-22 04:02: "With actual
    # sweep_references, injected readers only, _posix_monotonic_ns=None
    # produces a fresh v2 record. Feeding it a legacy-domain lifecycle
    # observation yields VALID COVERAGE. Thus current source can silently
    # turn unavailable new instrumentation into accepted legacy
    # production." Exactly so: the fallback was invisible and it graded.
    # "Prefer to reject unavailable required readers/provenance BEFORE
    # verifier dispatch."
    if _posix_monotonic_ns() is None:
        raise ProvenanceUnavailable(
            'clock_gettime(CLOCK_MONOTONIC) is unavailable on this host, so '
            'a new production attempt cannot carry the named POSIX domain. '
            'Refusing BEFORE the verifier is dispatched rather than emitting '
            'a v2 record that a legacy observation would then certify.')
    _prov = clock_provenance()          # raises if provenance is unavailable
    _boot_id, _host_id = _prov['boot_id'], _prov['host_id']

    out: list[Exclusion] = []
    for index, task in enumerate(tasks):
        pilot_task = to_pilot_task(task)
        reason: str | None = None
        attempts: list[dict] = []
        for run_index in range(REFERENCE_SWEEP_RUNS):
            # INTERVAL SCHEMA v2 (root 2026-09-21 22:23). Five named boundaries,
            # of which only verification_started..verification_ended is the
            # interval load coverage must certify. The lock wait is retained but
            # is NOT part of the certified interval: 3.2(4) asks for verification
            # under load, not for waiting under load.
            # READ ORDER IS PRESCRIBED, root 2026-09-22 03:19: "Read its start
            # before the legacy start read and its end after the legacy end read,
            # so cross-call measurement order WIDENS the interval rather than
            # silently shortening it." The POSIX interval therefore encloses the
            # legacy one, and the coverage requirement it carries is strictly
            # harder to satisfy, never easier.
            _boot_id, _host_id = _prov['boot_id'], _prov['host_id']
            _lock_requested = time.monotonic()
            with _ExecutionLock(lock_path, max_lock_wait_s):
                _lock_acquired = time.monotonic()
                _verify_started_posix_ns = _posix_monotonic_ns()   # FIRST
                _verify_started = time.monotonic()
                result = verify_mod.verify(pilot_task, task['reference'], timeout_s=timeout_s,
                                           mem_bytes=mem_bytes, cpu_seconds=cpu_s,
                                           output_cap=output_cap)
                _verify_ended = time.monotonic()
                _verify_ended_posix_ns = _posix_monotonic_ns()     # LAST
            _lock_released = time.monotonic()
            # D1: the COMPLETE record is retained, not a string that is hashed and
            # thrown away.  `on_attempt` lets the caller persist it durably; the
            # digest below is built from these same records through the one
            # canonicalization rule, so it reconstructs from what was saved.
            record = attempt_record(
                task['uid'], run_index, result,
                lock_requested_monotonic=_lock_requested,
                lock_acquired_monotonic=_lock_acquired,
                verification_started_monotonic=_verify_started,
                verification_ended_monotonic=_verify_ended,
                lock_released_monotonic=_lock_released,
                verification_started_posix_ns=_verify_started_posix_ns,
                verification_ended_posix_ns=_verify_ended_posix_ns,
                boot_id=_boot_id, host_id=_host_id,
                boot_source=_prov['boot_source'], host_source=_prov['host_source'])
            attempts.append(record)
            if on_attempt is not None:
                # DELIBERATELY UNGUARDED.  Root: "loss/failure of the sink must
                # stop preparation rather than silently continue."  A try/except
                # here would let the sweep carry on producing exclusions whose
                # preimage was never recorded -- exactly the defect D1 repairs.
                on_attempt(record)
            # D3: documented precedence; a genuine hang is a timeout, not a
            # verifier failure.  The excluded SET is unchanged -- a timed-out
            # attempt was already failing -- only its reason moves.
            reason = classify_attempt(record, threshold)
            if reason is not None:
                break
        if reason is not None:
            out.append(_exclusion(task['uid'], reason, detail_from_attempts(attempts)))
        if on_progress is not None:
            on_progress(index + 1, len(tasks), task['uid'], reason)
    return out


# --------------------------------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------------------------------

_REASON_ORDER = ('out_of_design_smoke_task', 'duplicate_prompt', 'no_entry_point', 'unparsable',
                 'reference_fails_verify', 'reference_timeout')


def build_roster(tasks: list[Task], exclusions: list[Exclusion], cfg: dict) -> dict:
    """[pure] The frozen roster object.

    Returns the surviving uids in the frozen order, the two strata, the exclusion list with reasons,
    the counts and `n_pairs = n_S1 // 2 + n_S2 // 2` (protocol 3.3; **never** `n_total // 2`), plus
    `roster_sha256` and `task_content_sha256`.

    `n_pairs` is computed on the SURVIVING counts, so it is the horizon `N_P` of whatever roster this
    call produces. The number 568 is the same rule applied to the candidate lists 591/547, i.e.
    before any exclusion: a loose pre-exclusion bound and not a horizon. Wherever a POST-exclusion
    figure is wanted the number is **at most 565**: the six smoke tasks of `SMOKE_TASKS` are all in
    S2, so they alone put the ceiling at `295 + floor(541/2) = 565`, and the duplicate-prompt,
    entry-point, unparsable and reference-sweep exclusions lower it further, S1 included. 568 may be
    quoted only where it is explicitly labelled the loose pre-exclusion bound. The leftover count is
    `(n_S1 % 2) + (n_S2 % 2)`, which is 0, 1 or 2.

    The per-stratum pair counts `floor(n_s / 2)` are what makes the allocation PROPORTIONAL (module
    docstring). **CORRECTED 2026-09-21 (root disposition 06:35); this is the root's dictated
    statement and supersedes both of my earlier wordings here.** Each stratum contributes
    `floor(n_s / 2)` pairs, and the combined pair list is uniformly permuted. At any fixed,
    non-random prefix length, the expected stratum proportions equal the pair-roster proportions.
    This does not imply the same expectation at an outcome-selected stopping time. The monitored
    targets are the enrollment-running averages of the history-conditional means of the hierarchical
    score and the success-difference score, under the paired serving regime defined in protocol
    sections 7.2 and 10.1. They are NOT the realized sample means and NOT a fixed full-roster
    contrast. No unbiasedness or stopping-time invariance follows merely from proportional
    allocation. Nothing in this function may weight a stratum.

    The top-level `'S1'` and `'S2'` keys are the lists protocol 3.4's code path indexes as
    `roster[stratum]`; `'tasks'` is the flat frozen order ARCHITECTURE 3.4 names.
    """
    roster_cfg = (cfg or {}).get('roster') or {}
    by_uid = {t['uid']: t for t in tasks}
    if len(by_uid) != len(tasks):
        raise lab_common.FrozenMismatch('duplicate uid in tasks')
    seen: dict[str, str] = {}
    ordered_exclusions: list[Exclusion] = []
    position = {t['uid']: i for i, t in enumerate(tasks)}
    for exc in sorted(exclusions, key=lambda e: (position.get(e['uid'], 1 << 30),
                                                 _REASON_ORDER.index(e['reason'])
                                                 if e['reason'] in _REASON_ORDER else len(_REASON_ORDER))):
        if exc['uid'] not in by_uid:
            raise lab_common.FrozenMismatch('exclusion names an unknown uid: %r' % (exc['uid'],))
        if exc['uid'] in seen:
            continue                       # first reason in the frozen order wins; the rest are noise
        seen[exc['uid']] = exc['reason']
        ordered_exclusions.append(Exclusion(uid=exc['uid'], reason=exc['reason'],
                                            detail_sha256=exc['detail_sha256']))
    surviving = [t for t in tasks if t['uid'] not in seen]
    s1 = [t['uid'] for t in surviving if t['stratum'] == 'S1']
    s2 = [t['uid'] for t in surviving if t['stratum'] == 'S2']
    n_s1, n_s2 = len(s1), len(s2)
    roster = {
        'schema': ROSTER_SCHEMA,
        'strata': ['S1', 'S2'],
        'pairing': 'stratified_no_mixed_pair',
        'n_pairs_rule': 'floor(n_S1 / 2) + floor(n_S2 / 2)',
        'uid_pattern': roster_cfg.get('uid_pattern', UID_PATTERN),
        'roster_mode': 'EXT' if n_s2 else 'S1',
        'tasks': [t['uid'] for t in surviving],
        'S1': s1,
        'S2': s2,
        'exclusions': [dict(e) for e in ordered_exclusions],
        'n_S1': n_s1,
        'n_S2': n_s2,
        'n_total': n_s1 + n_s2,
        'n_pairs': n_s1 // 2 + n_s2 // 2,
        'n_excluded': len(ordered_exclusions),
        'task_content_sha256_by_uid': {t['uid']: task_content_hash(t) for t in surviving},
        'sources': {name: {'bytes': spec['bytes'], 'sha256': spec['sha256'],
                           'revision': spec['revision'], 'records': spec['records']}
                    for name, spec in SOURCES.items()
                    if spec['required'] or n_s2 or spec['stratum'] != 'S2'},
        'task_content_sha256': lab_common.sha256_canonical([_content_view(t) for t in surviving]),
    }
    roster['roster_sha256'] = roster_sha256(roster)
    return roster


def roster_sha256(roster: dict) -> str:
    """[pure] sha256 of the canonical roster object with the self-referential hash field removed."""
    return lab_common.sha256_canonical({k: v for k, v in roster.items() if k != 'roster_sha256'})


def check_roster(roster: dict) -> None:
    """[pure] Raise `FrozenMismatch` unless the roster is internally consistent (protocol 3.3)."""
    findings: list[str] = []
    if roster.get('roster_sha256') != roster_sha256(roster):
        findings.append('roster_sha256 does not match the object')
    s1, s2 = list(roster.get('S1') or []), list(roster.get('S2') or [])
    if roster.get('n_S1') != len(s1) or roster.get('n_S2') != len(s2):
        findings.append('n_S1/n_S2 do not match the stratum lists')
    if roster.get('n_total') != len(s1) + len(s2):
        findings.append('n_total is not n_S1 + n_S2')
    if roster.get('n_pairs') != len(s1) // 2 + len(s2) // 2:
        findings.append('n_pairs is not floor(n_S1/2) + floor(n_S2/2)')
    if set(roster.get('tasks') or []) != set(s1) | set(s2):
        findings.append('tasks is not the union of the strata')
    pattern = re.compile(roster.get('uid_pattern') or UID_PATTERN)
    for uid in roster.get('tasks') or []:
        if not pattern.match(uid):
            findings.append('uid %r violates the uid pattern' % (uid,))
            break
    if findings:
        raise lab_common.FrozenMismatch('; '.join(findings))


def write_roster(roster: dict, path: Path) -> str:
    """Write-once, durable. Returns the sha256 of the bytes written; raises `WriteOnceViolation`."""
    check_roster(roster)
    return lab_common.write_json_atomic(Path(path), roster, durable=True)


def load_roster(path: Path) -> dict:
    """Read a roster written by `write_roster` and re-check it. Side effect: reads one file."""
    roster = json.loads(Path(path).read_text(encoding='utf-8'))
    check_roster(roster)
    return roster


def load_tasks_by_uid(roster: dict, sources_dir: Path) -> dict[str, Task]:
    """Full Task records for every uid of the roster, keyed by uid.

    A roster that embeds `task_records` (the small dry-run roster of `testdata/roster_small.json`) is
    served from those records and `sources_dir` is not read; otherwise the pinned sources under
    `sources_dir` are re-parsed and hash-checked.
    """
    embedded = roster.get('task_records')
    if embedded:
        by_uid = {rec['uid']: Task(**rec) for rec in embedded}
    else:
        by_uid = {t['uid']: t for t in build_candidate_tasks(load_raw(Path(sources_dir)))}
    out: dict[str, Task] = {}
    missing: list[str] = []
    for uid in roster.get('tasks') or []:
        task = by_uid.get(uid)
        if task is None:
            missing.append(uid)
            continue
        recorded = (roster.get('task_content_sha256_by_uid') or {}).get(uid)
        if recorded is not None and task_content_hash(task) != recorded:
            raise lab_common.FrozenMismatch('task content of %s differs from the frozen hash' % uid)
        out[uid] = task
    if missing:
        raise lab_common.FrozenMismatch('roster uids absent from the sources: %s'
                                        % ', '.join(missing[:5]))
    return out
