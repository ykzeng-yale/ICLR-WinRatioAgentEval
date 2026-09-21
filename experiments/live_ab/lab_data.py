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
* **Allocation across strata must stay PROPORTIONAL.** Each stratum contributes `floor(n_s / 2)` pairs
  and protocol 3.4 then permutes the whole pair list as ONE sequence, so every enrolled prefix is an
  exchangeable sample of the strata in proportion to their pair counts. The guardrail's target is the
  mean guarded score over the pairs actually enrolled. If allocation drifted away from proportional --
  by weighting a stratum, by enrolling the strata in blocks, or by any rule that makes the stratum mix
  of a stopping prefix differ from the roster's -- then the quantity the band brackets at the stopping
  time would drift further from the roster contrast the design is named for. **CORRECTED 2026-09-21
  (root disposition 04:53, "correct its exactness and stopped-roster wording"):** proportionality does
  NOT make the stopped estimand equal to the roster's. The target is, and remains, the mean guarded
  score over the pairs ACTUALLY ENROLLED at the look in question; proportional allocation makes that
  prefix's stratum mix match the roster's IN EXPECTATION ONLY, and the REALISED mix at a stopping time
  can differ from it. What proportionality buys is that the target does not acquire a stratum-weighting
  bias BY CONSTRUCTION; it does not make the estimand invariant to when you stop, which
  is a separate requirement from the anytime validity of the band itself.
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
import time
from pathlib import Path
from typing import Callable, Literal, TypedDict

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


def prospective_exclusions(tasks: list[Task], cfg: dict) -> list[Exclusion]:
    """[pure] The exclusions of protocol 3.2 that need no execution: rules 1, 2, 3 and `unparsable`.

    Blind to every model output. Order is frozen: by the position of the task in `tasks`, then by the
    fixed reason order, so the list is a deterministic function of the sources.
    """
    roster_cfg = (cfg or {}).get('roster') or {}
    smoke = tuple(roster_cfg.get('smoke_tasks') or SMOKE_TASKS)
    s1_prompts: dict[str, str] = {}
    for task in tasks:
        if task['stratum'] == 'S1' and task['benchmark'] == 'mbpp':
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


def sweep_references(tasks: list[Task], cfg: dict, *, on_progress: Callable | None = None) -> list[Exclusion]:
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
    out: list[Exclusion] = []
    for index, task in enumerate(tasks):
        pilot_task = to_pilot_task(task)
        reason: str | None = None
        detail_parts: list[str] = []
        for run_index in range(REFERENCE_SWEEP_RUNS):
            with _ExecutionLock(lock_path, max_lock_wait_s):
                result = verify_mod.verify(pilot_task, task['reference'], timeout_s=timeout_s,
                                           mem_bytes=mem_bytes, cpu_seconds=cpu_s,
                                           output_cap=output_cap)
            run = result.get('run') or {}
            detail_parts.append('run%d:%s|%s' % (run_index, run.get('stdout_tail', ''),
                                                 run.get('stderr', '')))
            seconds = float(result.get('verify_seconds') or 0.0)
            if not result.get('success'):
                reason = 'reference_fails_verify'
                break
            if seconds > threshold:
                reason = 'reference_timeout'
                break
        if reason is not None:
            out.append(_exclusion(task['uid'], reason, '\n'.join(detail_parts)))
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
    docstring): protocol 3.4 permutes the combined pair list, so the stratum mix of every enrolled
    prefix is the roster's own mix IN EXPECTATION. **CORRECTED 2026-09-21: the previous sentence here
    claimed "the guarded estimand does not move with the stopping time". That is withdrawn.** The
    estimand IS the mean over the pairs actually enrolled, so it moves with the stopping time by
    definition; what proportional allocation prevents is a stratum-weighting bias by construction, not
    stopping-time dependence. Nothing in this function may weight a stratum.

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
