"""Tests for `lab_data`, `lab_design` and `lab_coin` (group G2).

Offline, deterministic (see the one declared exception below), no model, no network, no server.

**Local stand-ins.** G1 owns `lab_common` and `lab_eventlog`; G4 owns `lab_client` and `lab_worker`.
Those files are written in parallel with this one and may not exist yet, so this module installs a
faithful stand-in for `lab_common` **only when the real module is absent or incomplete**, and always
uses a local `FakeEventLog` / fake worker rather than assuming G1's or G4's classes. Nothing here
patches a real module that is present.

**Declared non-determinism, one test.** `test_coin_balance_10k` draws 10,000 real OS-entropy coins and
asserts the count of ones lies in [4850, 5150], which is the plumbing check protocol 4.3 prescribes.
That interval is +/- 3 standard deviations, so the test fails by chance about 0.3% of the time. It is
kept because both binding documents name it; every other test in this file is deterministic.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
for _p in (str(HERE), str(REPO_ROOT / 'experiments' / 'local_stream'), str(REPO_ROOT / 'src')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy


# ==================================================================================================
# Stand-in for lab_common (G1), used only when the real module is absent or incomplete
# ==================================================================================================

_LAB_COMMON_NAMES = ('REPO_ROOT', 'WORK_ROOT', 'RESULTS_ROOT', 'add_import_paths', 'canonical_json',
                     'sha256_bytes', 'sha256_text', 'sha256_canonical', 'fullsync',
                     'write_json_atomic', 'tokenize_path', 'LabError', 'FrozenMismatch',
                     'WriteOnceViolation', 'SchemaError', 'PreflightError', 'ChainError')

_EXCEPTIONS = ('FreezeIncomplete', 'FrozenMismatch', 'UntokenizablePath', 'WriteOnceViolation',
               'TornWrite', 'ChainError', 'SchemaError', 'SpoolError', 'EnclosureError',
               'MonitorError', 'ReceiptMismatch', 'ServerIdentityError', 'PreflightError',
               'VerifyFailure')


def _build_fake_lab_common() -> types.ModuleType:
    """A minimal, faithful `lab_common` (ARCHITECTURE 3.1) for use before G1 lands."""
    module = types.ModuleType('lab_common')
    module.__dict__['__FAKE__'] = True
    root = REPO_ROOT
    module.HERE = root / 'experiments' / 'live_ab'
    module.REPO_ROOT = root
    module.SRC_DIR = root / 'src'
    module.LS_DIR = root / 'experiments' / 'local_stream'
    module.RESULTS_ROOT = root / 'results' / 'live_ab'
    module.WORK_ROOT = root / 'work' / 'live_ab'
    module.FREEZE_DIR = module.RESULTS_ROOT / 'freeze'
    module.PROGRAM_CHAIN_ID = '_program'
    module.PREFREEZE_CHAIN_ID = '_prefreeze'
    module.TRIALS = ('T4', 'T2', 'T1', 'T3')
    module.ARMS = ('incumbent', 'candidate')

    class LabError(Exception):
        pass

    module.LabError = LabError
    for name in _EXCEPTIONS:
        module.__dict__[name] = type(name, (LabError,), {})

    def add_import_paths() -> None:
        for path in (module.LS_DIR, module.SRC_DIR):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))

    def canonical_json(obj) -> str:
        return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False)

    def sha256_bytes(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    def sha256_text(s: str) -> str:
        return sha256_bytes(s.encode('utf-8'))

    def sha256_file(p) -> str:
        digest = hashlib.sha256()
        with open(p, 'rb') as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def sha256_canonical(obj) -> str:
        return sha256_text(canonical_json(obj))

    def fullsync(fd: int) -> None:
        try:
            import fcntl
            if sys.platform == 'darwin' and hasattr(fcntl, 'F_FULLFSYNC'):
                fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
                return
        except Exception:
            pass
        os.fsync(fd)

    def tokenize_path(p) -> str:
        text = str(Path(p))
        for root_path, token in ((module.WORK_ROOT, '<WORK>'), (module.RESULTS_ROOT, '<RESULTS>'),
                                 (module.REPO_ROOT, '<REPO>'), (Path.home(), '<HOME>'),
                                 (Path(tempfile.gettempdir()), '<TMP>')):
            prefix = str(root_path)
            if text == prefix or text.startswith(prefix + os.sep):
                return token + text[len(prefix):]
        raise module.UntokenizablePath(text)

    def write_json_atomic(path, obj, *, durable: bool = True) -> str:
        path = Path(path)
        data = canonical_json(obj).encode('utf-8')
        digest = sha256_bytes(data)
        if path.exists():
            if path.read_bytes() == data:
                return digest
            raise module.WriteOnceViolation(str(path.name))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, data)
            if durable:
                fullsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)
        if durable:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                fullsync(dir_fd)
            finally:
                os.close(dir_fd)
        return digest

    def append_line_durable(fd: int, line: str, *, durable: bool) -> int:
        payload = (line + '\n').encode('utf-8')
        written = os.write(fd, payload)
        if written != len(payload):
            raise module.TornWrite('%d of %d bytes' % (written, len(payload)))
        if durable:
            fullsync(fd)
        return written

    module.add_import_paths = add_import_paths
    module.canonical_json = canonical_json
    module.sha256_bytes = sha256_bytes
    module.sha256_text = sha256_text
    module.sha256_file = sha256_file
    module.sha256_canonical = sha256_canonical
    module.fullsync = fullsync
    module.tokenize_path = tokenize_path
    module.write_json_atomic = write_json_atomic
    module.append_line_durable = append_line_durable
    return module


def install_fakes() -> bool:
    """Install the stand-in `lab_common` if the real one is missing. Returns True when faked."""
    if 'lab_common' in sys.modules and getattr(sys.modules['lab_common'], '__FAKE__', False):
        return True
    try:
        import lab_common as real
        missing = [name for name in _LAB_COMMON_NAMES if not hasattr(real, name)]
        if not missing:
            return False
    except Exception:
        pass
    sys.modules['lab_common'] = _build_fake_lab_common()
    return True


USING_FAKE_COMMON = install_fakes()

import lab_common                                        # noqa: E402
import lab_coin                                          # noqa: E402
import lab_data                                          # noqa: E402
import lab_prepare                                       # noqa: E402
import lab_design                                        # noqa: E402

DESIGN_SEED_BASE = 60260919


# ==================================================================================================
# Local fakes for the chain (G1) and for a worker try (G4)
# ==================================================================================================


class FakeEventLog:
    """A single-writer append-only JSON-lines log with the durability contract of `lab_eventlog`.

    Only what `lab_coin.draw_and_commit` uses is implemented: `append(etype, body, durable=)` writes
    exactly one line with one `os.write`, calls `lab_common.fullsync` when `durable` is true, and
    returns afterwards. `trace` records the interleaving of writes, fsyncs and anything the test adds,
    which is how the write-ahead order is asserted.
    """

    def __init__(self, path: Path, chain: str = 'T4', inv: str = '0' * 32,
                 trace: list | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.chain = chain
        self.inv = inv
        self.events: list[dict] = []
        self.durable_calls: list[tuple[str, bool]] = []
        self.trace = trace if trace is not None else []
        self._prev = hashlib.sha256(('live_ab/eventlog-v3|prefreeze|' + chain).encode()).hexdigest()
        self._fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)

    def append(self, etype: str, body: dict, *, durable: bool = False) -> dict:
        self.durable_calls.append((etype, bool(durable)))
        event = {'seq': len(self.events), 'type': etype, 't_wall_ns': time.time_ns(),
                 't_mono_ns': time.monotonic_ns(), 'inv': self.inv, 'chain': self.chain,
                 'prev': self._prev, 'body': body}
        event['h'] = hashlib.sha256(
            lab_common.canonical_json(event).encode('utf-8')).hexdigest()
        line = lab_common.canonical_json(event) + '\n'
        self.trace.append(('write', etype))
        os.write(self._fd, line.encode('utf-8'))
        if durable:
            self.trace.append(('fsync', etype))
            lab_common.fullsync(self._fd)
        self._prev = event['h']
        self.events.append(event)
        return event

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def read_lines(self) -> list[dict]:
        text = self.path.read_text(encoding='utf-8')
        return [json.loads(line) for line in text.splitlines() if line.strip()]


class ChainBuilder:
    """Builds the scripted trial chains the coin-ordering tests audit."""

    def __init__(self, log: FakeEventLog) -> None:
        self.log = log
        self.reveal_index = 0

    def start(self, *, receipt: bool = True) -> None:
        self.log.append('trial_started', {'n_pairs_max': 12}, durable=True)
        self.log.append('anchor', {'anchor_seq': 0, 'blocking': True}, durable=True)
        if receipt:
            self.log.append('anchor_receipt', {'anchor_seq': 0, 'pushed': True}, durable=True)

    def enroll(self, pair: int, stratum: str = 'S1', re_enrolled: bool = False,
               uids: tuple[str, str] = ('mbpp/2', 'mbpp/3')) -> None:
        self.log.append('pair_enrolled', {'pair': pair, 'stratum': stratum,
                                          'arrivals': [2 * pair - 1, 2 * pair],
                                          'task_uids': list(uids), 'phase': 'randomizing',
                                          're_enrolled': bool(re_enrolled)}, durable=True)

    def coin(self, pair: int, slot: dict | None = None) -> dict:
        slot = slot or {'pair': pair, 'stratum': 'S1',
                        'arrivals': (2 * pair - 1, 2 * pair), 'uids': ('mbpp/2', 'mbpp/3')}
        coin, assigned, event = lab_coin.draw_and_commit(self.log, slot)
        return {'coin': coin, 'assignment': assigned, 'event': event}

    def start_episodes(self, pair: int, assigned: dict) -> None:
        for position, arrival in enumerate(sorted(assigned), start=1):
            self.log.append('episode_started', {'arrival': arrival, 'pair': pair,
                                                'position': position, 'arm': assigned[arrival]})

    def reveal(self, pair: int, arrival: int, post_decision: bool = False) -> None:
        self.reveal_index += 1
        self.log.append('episode_revealed', {'arrival': arrival, 'pair': pair,
                                             'reveal_index': self.reveal_index,
                                             'post_decision': post_decision}, durable=True)

    def look(self, n: int, trigger: str = 'reveal') -> None:
        self.log.append('monitor_update', {'trigger': trigger, 'n': n, 'n_collapsed': n})

    def decision(self, kind: str = 'harm_keep_incumbent', n: int = 100) -> None:
        self.log.append('decision', {'kind': kind, 'n': n}, durable=True)

    def full_pair(self, pair: int, *, look: bool = True) -> dict:
        self.enroll(pair)
        drawn = self.coin(pair)
        self.start_episodes(pair, drawn['assignment'])
        self.log.append('monitor_update', {'trigger': 'enroll', 'n': pair, 'n_collapsed': pair - 1})
        for arrival in sorted(drawn['assignment']):
            self.reveal(pair, arrival)
        if look:
            self.look(pair)
        return drawn


class _PatchedUrandom:
    """Context manager replacing `os.urandom` with a scripted byte stream."""

    def __init__(self, chunks) -> None:
        self.chunks = list(chunks)
        self.calls: list[int] = []
        self._original = None

    def __enter__(self):
        self._original = os.urandom

        def fake(n: int) -> bytes:
            self.calls.append(n)
            if not self.chunks:
                raise AssertionError('os.urandom called more often than the script allows')
            chunk = self.chunks.pop(0)
            if len(chunk) != n:
                raise AssertionError('scripted chunk is %d bytes, %d requested' % (len(chunk), n))
            return chunk

        os.urandom = fake
        return self

    def __exit__(self, *exc) -> None:
        os.urandom = self._original


# ==================================================================================================
# Shared fixtures built from the pinned sources
# ==================================================================================================

_REAL: dict = {}


def real_raw() -> dict:
    """The three pinned sources, parsed once. Read from the caches only; never downloaded."""
    if 'raw' not in _REAL:
        _REAL['raw'] = lab_data.load_raw(lab_data.CACHE_SEARCH_DIRS[0])
    return _REAL['raw']


def real_tasks() -> list:
    if 'tasks' not in _REAL:
        _REAL['tasks'] = lab_data.build_candidate_tasks(real_raw())
    return _REAL['tasks']


def full_roster() -> dict:
    """The roster with no exclusion at all: 591 S1 + 547 S2, so `295 + 273 = 568` pairs.

    568 is the LOOSE PRE-EXCLUSION BOUND and is never a horizon; every roster that has had an
    exclusion applied gives at most 565. Use `blind_roster()` for a post-exclusion figure.
    """
    if 'full' not in _REAL:
        _REAL['full'] = lab_data.build_roster(real_tasks(), [], {})
    return _REAL['full']


def blind_roster() -> dict:
    """The roster after the blind exclusions of protocol 3.2 rules 1-3 (no sweep)."""
    if 'blind' not in _REAL:
        tasks = real_tasks()
        _REAL['blind'] = lab_data.build_roster(tasks, lab_data.prospective_exclusions(tasks, {}), {})
    return _REAL['blind']


def synthetic_roster(n_s1: int, n_s2: int) -> dict:
    return {'S1': ['mbpp/%d' % i for i in range(n_s1)],
            'S2': ['mbpp_full/%d' % i for i in range(n_s2)],
            'tasks': ['mbpp/%d' % i for i in range(n_s1)] + ['mbpp_full/%d' % i for i in range(n_s2)],
            'n_S1': n_s1, 'n_S2': n_s2, 'n_total': n_s1 + n_s2,
            'n_pairs': n_s1 // 2 + n_s2 // 2}


def protocol_3_4_reference(roster: dict, trial_no: int, base: int = DESIGN_SEED_BASE):
    """The literal code block of protocol_FINAL.md 3.4, transcribed, as an independent oracle."""
    rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([base, trial_no])))
    pairs, leftovers = [], []
    for stratum in ["S1", "S2"]:                 # S2 absent on roster S1
        if not roster.get(stratum):
            continue
        uids = sorted(roster[stratum])
        u = [uids[j] for j in rng.permutation(len(uids))]
        pairs += [(stratum, u[2 * m], u[2 * m + 1]) for m in range(len(u) // 2)]
        leftovers += u[2 * (len(u) // 2):]
    enrollment = [pairs[j] for j in rng.permutation(len(pairs))]
    return enrollment, leftovers


# ==================================================================================================
# lab_data
# ==================================================================================================


class SourceTests(unittest.TestCase):

    def test_source_hashes(self):
        """The pinned bytes and digests are exactly protocol 3.1 / config.roster.sources."""
        self.assertEqual(lab_data.SOURCES['mbpp_sanitized']['bytes'], 255053)
        self.assertEqual(lab_data.SOURCES['mbpp_sanitized']['sha256'],
                         'ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9')
        self.assertEqual(lab_data.SOURCES['humaneval']['bytes'], 44877)
        self.assertEqual(lab_data.SOURCES['humaneval']['sha256'],
                         'b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef')
        self.assertEqual(lab_data.SOURCES['mbpp_full']['bytes'], 563743)
        self.assertEqual(lab_data.SOURCES['mbpp_full']['sha256'],
                         'ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f')
        for spec in lab_data.SOURCES.values():
            self.assertNotIn('master', spec['url'], 'a mutable master URL is never used')
            self.assertIn(spec['revision'], spec['url'])

    def test_offline_fetch_uses_cache_and_records_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = lab_data.fetch_sources(Path(tmp), offline=True)
            self.assertEqual(manifest['roster_mode'], 'EXT')
            for name, spec in lab_data.SOURCES.items():
                entry = manifest['sources'][name]
                self.assertTrue(entry['present'], name)
                self.assertEqual(entry['sha256'], spec['sha256'])
                self.assertEqual(entry['bytes'], spec['bytes'])
                self.assertTrue((Path(tmp) / spec['filename']).is_file())
            written = json.loads((Path(tmp) / 'sources.json').read_text())
            self.assertEqual(written['sources']['mbpp_full']['sha256'],
                             lab_data.SOURCES['mbpp_full']['sha256'])
            self.assertNotIn(str(REPO_ROOT), json.dumps(written),
                             'the manifest must not carry an absolute path')

    def test_source_byte_change_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab_data.fetch_sources(Path(tmp), offline=True)
            target = Path(tmp) / lab_data.SOURCES['mbpp_sanitized']['filename']
            data = bytearray(target.read_bytes())
            data[10] = data[10] ^ 0x01
            target.write_bytes(bytes(data))
            with self.assertRaises(lab_common.FrozenMismatch):
                lab_data.load_raw(Path(tmp))
            with self.assertRaises(lab_common.FrozenMismatch):
                lab_data.fetch_sources(Path(tmp), offline=True)

    def test_offline_never_downloads(self):
        original = lab_data._download
        lab_data._download = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError('offline=True reached the network path'))
        original_dirs = lab_data.CACHE_SEARCH_DIRS
        try:
            lab_data.CACHE_SEARCH_DIRS = ()
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(lab_common.PreflightError):
                    lab_data.fetch_sources(Path(tmp), offline=True)
        finally:
            lab_data.CACHE_SEARCH_DIRS = original_dirs
            lab_data._download = original


class RosterTests(unittest.TestCase):

    def test_strata_sizes(self):
        tasks = real_tasks()
        s1 = [t for t in tasks if t['stratum'] == 'S1']
        s2 = [t for t in tasks if t['stratum'] == 'S2']
        self.assertEqual(len([t for t in s1 if t['benchmark'] == 'mbpp']), 427)
        self.assertEqual(len([t for t in s1 if t['benchmark'] == 'humaneval']), 164)
        self.assertEqual(len(s1), 591)
        self.assertEqual(len(s2), 547)
        self.assertEqual([t['benchmark'] for t in tasks][:1], ['mbpp'])
        order = [t['benchmark'] for t in tasks]
        self.assertEqual(order, sorted(order, key=['mbpp', 'mbpp_full', 'humaneval'].index),
                         'frozen order: mbpp, then mbpp_full, then humaneval')

    def test_n_pairs_rule(self):
        roster = full_roster()
        self.assertEqual(roster['n_excluded'], 0, 'the 568 below is the pre-exclusion bound')
        self.assertEqual((roster['n_S1'], roster['n_S2']), (591, 547))
        self.assertEqual(roster['n_pairs'], 591 // 2 + 547 // 2)
        self.assertEqual(roster['n_pairs'], 568)
        self.assertNotEqual(roster['n_pairs'], roster['n_total'] // 2)
        self.assertEqual(roster['n_total'] // 2, 569)      # the number that is NOT a horizon

    def test_roster_deterministic(self):
        first = lab_data.build_roster(real_tasks(), lab_data.prospective_exclusions(real_tasks(), {}), {})
        second = lab_data.build_roster(real_tasks(), lab_data.prospective_exclusions(real_tasks(), {}), {})
        self.assertEqual(first['roster_sha256'], second['roster_sha256'])
        self.assertEqual(first['task_content_sha256'], second['task_content_sha256'])
        self.assertEqual(first, second)

    def test_roster_hash_changes_with_content(self):
        tasks = [dict(t) for t in real_tasks()[:20]]
        base = lab_data.build_roster(tasks, [], {})
        tasks[3]['reference'] = tasks[3]['reference'] + '\n# changed\n'
        changed = lab_data.build_roster(tasks, [], {})
        self.assertNotEqual(base['task_content_sha256'], changed['task_content_sha256'])
        self.assertNotEqual(base['roster_sha256'], changed['roster_sha256'])

    def test_task_content_hash_per_task(self):
        roster = full_roster()
        by_uid = {t['uid']: t for t in real_tasks()}
        for uid in ('mbpp/2', 'humaneval/0', 'mbpp_full/1'):
            self.assertEqual(roster['task_content_sha256_by_uid'][uid],
                             lab_data.task_content_hash(by_uid[uid]))
            self.assertRegex(roster['task_content_sha256_by_uid'][uid], r'^[0-9a-f]{64}$')

    def test_smoke_tasks_excluded(self):
        roster = blind_roster()
        reasons = {e['uid']: e['reason'] for e in roster['exclusions']}
        for uid in lab_data.SMOKE_TASKS:
            self.assertEqual(reasons.get(uid), 'out_of_design_smoke_task', uid)
            self.assertNotIn(uid, roster['tasks'])

    def test_duplicate_prompts_excluded(self):
        raw = {'mbpp_sanitized': [{'task_id': 2, 'prompt': 'Write a function to add two numbers.',
                                   'code': 'def add(a,b):\n    return a+b\n',
                                   'test_imports': [], 'test_list': ['assert add(1,2)==3']}],
               'mbpp_full': [{'task_id': 2, 'text': 'x', 'code': 'def f():\n    pass\n',
                              'test_list': ['assert f() is None'], 'challenge_test_list': [],
                              'test_setup_code': ''},
                             {'task_id': 900, 'text': 'write a FUNCTION  to add   two numbers!!',
                              'code': 'def add(a,b):\n    return a+b\n',
                              'test_list': ['assert add(1,2)==3'], 'challenge_test_list': [],
                              'test_setup_code': ''}],
               'humaneval': [{'task_id': 'HumanEval/0', 'prompt': 'def z():\n', 'entry_point': 'z',
                              'canonical_solution': '    return 1\n', 'test': 'def check(f):\n    pass\n'}]}
        tasks = lab_data.build_candidate_tasks(raw)
        self.assertIn('mbpp_full/900', [t['uid'] for t in tasks])
        exclusions = lab_data.prospective_exclusions(tasks, {})
        reasons = {e['uid']: e['reason'] for e in exclusions}
        self.assertEqual(reasons.get('mbpp_full/900'), 'duplicate_prompt')
        roster = lab_data.build_roster(tasks, exclusions, {})
        self.assertNotIn('mbpp_full/900', roster['tasks'])
        self.assertIn('mbpp/2', roster['tasks'])

    def test_real_duplicates_are_the_known_two(self):
        reasons = {e['uid']: e['reason'] for e in blind_roster()['exclusions']}
        duplicates = sorted(uid for uid, reason in reasons.items() if reason == 'duplicate_prompt')
        self.assertEqual(duplicates, ['mbpp_full/217', 'mbpp_full/928'])

    def test_no_entry_point_and_unparsable(self):
        raw = {'mbpp_sanitized': [{'task_id': 2, 'prompt': 'p', 'code': 'def a():\n    pass\n',
                                   'test_imports': [], 'test_list': ['assert a() is None']}],
               'mbpp_full': [{'task_id': 800, 'text': 'no entry point here', 'code': 'x = 1\n',
                              'test_list': [], 'challenge_test_list': [], 'test_setup_code': ''},
                             {'task_id': 801, 'text': 'broken reference', 'code': 'def b(:\n',
                              'test_list': ['assert b() is None'], 'challenge_test_list': [],
                              'test_setup_code': ''}],
               'humaneval': [{'task_id': 'HumanEval/0', 'prompt': 'def z():\n', 'entry_point': 'z',
                              'canonical_solution': '    return 1\n', 'test': 'def check(f):\n    pass\n'}]}
        tasks = lab_data.build_candidate_tasks(raw)
        reasons = {e['uid']: e['reason'] for e in lab_data.prospective_exclusions(tasks, {})}
        self.assertEqual(reasons.get('mbpp_full/800'), 'no_entry_point')
        self.assertEqual(reasons.get('mbpp_full/801'), 'unparsable')

    def test_normalization_matches_pilot(self):
        """`normalize_prompt` agrees with timing_pilot.py:35-36, extracted from the pilot source."""
        source = (REPO_ROOT / 'experiments' / 'local_stream' / 'timing_pilot.py').read_text()
        tree = ast.parse(source)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_norm')
        namespace: dict = {'re': re}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<pilot>', 'exec'), namespace)
        pilot_norm = namespace['_norm']
        samples = ['Write a  FUNCTION, to add: two numbers!!', '  Mixed   Case\tTabs\n', 'a-b_c d',
                   real_tasks()[0]['prompt'], real_tasks()[600]['prompt']]
        for sample in samples:
            self.assertEqual(lab_data.normalize_prompt(sample), pilot_norm(sample))

    def test_write_roster_is_write_once(self):
        roster = lab_data.build_roster(real_tasks()[:40], [], {})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'roster.json'
            digest = lab_data.write_roster(roster, path)
            self.assertRegex(digest, r'^[0-9a-f]{64}$')
            self.assertEqual(lab_data.write_roster(roster, path), digest)   # identical bytes are fine
            other = dict(roster)
            other['tasks'] = roster['tasks'][:-1]
            other['n_S1'] = len([u for u in other['tasks'] if not u.startswith('mbpp_full')])
            other['n_S2'] = len(other['tasks']) - other['n_S1']
            other['S1'] = [u for u in other['tasks'] if not u.startswith('mbpp_full')]
            other['S2'] = [u for u in other['tasks'] if u.startswith('mbpp_full')]
            other['n_total'] = len(other['tasks'])
            other['n_pairs'] = other['n_S1'] // 2 + other['n_S2'] // 2
            other['task_content_sha256_by_uid'] = {
                k: v for k, v in roster['task_content_sha256_by_uid'].items() if k in other['tasks']}
            other['roster_sha256'] = lab_data.roster_sha256(other)
            with self.assertRaises(lab_common.WriteOnceViolation):
                lab_data.write_roster(other, path)

    def test_roster_roundtrip_and_check(self):
        roster = blind_roster()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'roster.json'
            lab_data.write_roster(roster, path)
            loaded = lab_data.load_roster(path)
            self.assertEqual(loaded['roster_sha256'], roster['roster_sha256'])
            tampered = dict(loaded)
            tampered['n_pairs'] = tampered['n_total'] // 2
            with self.assertRaises(lab_common.FrozenMismatch):
                lab_data.check_roster(tampered)

    def test_hidden_tests_never_in_prompt(self):
        """No hidden assert string reaches `agent.build_user_prompt` for ANY roster task."""
        lab_common.add_import_paths()
        import agent
        checked = 0
        for task in real_tasks():
            prompt = agent.build_user_prompt(lab_data.to_pilot_task(task))
            for assertion in list(task['test_list']) + list(task['challenge_test_list']):
                text = assertion.strip()
                if text:
                    self.assertNotIn(text, prompt, task['uid'])
            if task['benchmark'] == 'humaneval' and task['test']:
                self.assertNotIn(task['test'].strip(), prompt, task['uid'])
            checked += 1
        self.assertEqual(checked, 1138)


class SweepTests(unittest.TestCase):
    """protocol 3.2 rule 4, exercised on planted references only. No model, no server."""

    def _task(self, uid: str, reference: str, assertion: str) -> dict:
        return lab_data.Task(uid=uid, benchmark='mbpp_full', stratum='S2', prompt='planted',
                             entry_point='f', reference=reference, test_imports=[],
                             test_list=[assertion], challenge_test_list=[], test='')

    def test_reference_sweep_excludes(self):
        original = lab_data._download
        lab_data._download = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError('the sweep must never touch the network'))
        try:
            good = self._task('mbpp_full/9001', 'def f(a, b):\n    return a + b\n',
                              'assert f(1, 2) == 3')
            broken = self._task('mbpp_full/9002', 'def f(a, b):\n    return a - b\n',
                                'assert f(1, 2) == 3')
            slow = self._task('mbpp_full/9003',
                              'import time\ntime.sleep(2.7)\n\ndef f(a, b):\n    return a + b\n',
                              'assert f(1, 2) == 3')
            cfg = {'sandbox': {'timeout_s': 10.0, 'cpu_s': 10, 'output_cap_bytes': 65536},
                   'execution': {'max_lock_wait_s': 30}}
            seen: list = []
            exclusions = lab_data.sweep_references([good, broken, slow], cfg,
                                                   on_progress=lambda *a: seen.append(a))
            reasons = {e['uid']: e['reason'] for e in exclusions}
            self.assertNotIn('mbpp_full/9001', reasons)
            self.assertEqual(reasons.get('mbpp_full/9002'), 'reference_fails_verify')
            self.assertEqual(reasons.get('mbpp_full/9003'), 'reference_timeout')
            self.assertEqual(len(seen), 3)
            for exclusion in exclusions:
                self.assertRegex(exclusion['detail_sha256'], r'^[0-9a-f]{64}$')
            roster = lab_data.build_roster([good, broken, slow], exclusions, {})
            self.assertEqual(roster['tasks'], ['mbpp_full/9001'])
            self.assertEqual(roster['n_pairs'], 0)
        finally:
            lab_data._download = original


# ==================================================================================================
# lab_design
# ==================================================================================================


class OrderTests(unittest.TestCase):

    def test_order_matches_protocol_snippet(self):
        """`arrival_order` reproduces the literal code block of protocol 3.4, trial by trial."""
        roster = blind_roster()
        for trial, trial_no in sorted(lab_design.TRIAL_NO.items()):
            enrollment, leftovers = protocol_3_4_reference(roster, trial_no)
            order = lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
            self.assertEqual(len(order), len(enrollment), trial)
            for index, (stratum, u1, u2) in enumerate(enrollment):
                slot = order[index]
                self.assertEqual(slot['pair'], index + 1)
                self.assertEqual(slot['stratum'], stratum)
                self.assertEqual(slot['uids'], (u1, u2))
                self.assertEqual(slot['arrivals'], (2 * index + 1, 2 * index + 2))
            got = lab_design.leftover_slots(roster, trial, DESIGN_SEED_BASE)
            self.assertEqual([s['uid'] for s in got], list(leftovers), trial)
            self.assertEqual([s['arrival'] for s in got],
                             list(range(2 * len(order) + 1, 2 * len(order) + 1 + len(leftovers))))

    def test_order_is_permutation(self):
        roster = blind_roster()
        for trial in lab_design.TRIAL_NO:
            order = lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
            lab_design.check_order(order)
            uids = [u for slot in order for u in slot['uids']]
            self.assertEqual(len(uids), len(set(uids)))
            leftovers = [s['uid'] for s in lab_design.leftover_slots(roster, trial, DESIGN_SEED_BASE)]
            self.assertEqual(sorted(uids + leftovers), sorted(roster['tasks']))
            arrivals = [a for slot in order for a in slot['arrivals']]
            self.assertEqual(arrivals, list(range(1, 2 * len(order) + 1)))

    def test_order_stratified_never_crosses_a_stratum(self):
        roster = blind_roster()
        lookup = lab_design.strata_of(roster)
        for trial in lab_design.TRIAL_NO:
            order = lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
            lab_design.assert_no_mixed_slot(order, roster)
            for slot in order:
                self.assertIn(slot['stratum'], ('S1', 'S2'))
                self.assertEqual(lookup[slot['uids'][0]], lookup[slot['uids'][1]])
                self.assertEqual(lookup[slot['uids'][0]], slot['stratum'])
            counts = {'S1': 0, 'S2': 0}
            for slot in order:
                counts[slot['stratum']] += 1
            self.assertEqual(counts['S1'], roster['n_S1'] // 2)
            self.assertEqual(counts['S2'], roster['n_S2'] // 2)
            self.assertEqual(len(order), roster['n_pairs'])

    def test_mixed_slot_is_detected(self):
        roster = synthetic_roster(4, 4)
        order = lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE)
        bad = [dict(slot) for slot in order]
        bad[0]['uids'] = (roster['S1'][0], roster['S2'][0])
        with self.assertRaises(ValueError):
            lab_design.assert_no_mixed_slot(bad, roster)

    def test_leftover_per_stratum(self):
        roster = synthetic_roster(5, 7)
        order = lab_design.arrival_order(roster, 'T2', DESIGN_SEED_BASE)
        leftovers = lab_design.leftover_slots(roster, 'T2', DESIGN_SEED_BASE)
        self.assertEqual(len(order), 5 // 2 + 7 // 2)
        self.assertEqual(sorted(s['stratum'] for s in leftovers), ['S1', 'S2'])
        self.assertEqual([s['arrival'] for s in leftovers], [2 * len(order) + 1, 2 * len(order) + 2])
        enrolled = {u for slot in order for u in slot['uids']}
        for slot in leftovers:
            self.assertNotIn(slot['uid'], enrolled)

    def test_roster_s1_only(self):
        roster = {'S1': ['mbpp/%d' % i for i in range(591)], 'S2': [],
                  'tasks': ['mbpp/%d' % i for i in range(591)]}
        order = lab_design.arrival_order(roster, 'T3', DESIGN_SEED_BASE)
        self.assertEqual(len(order), 295)
        self.assertTrue(all(slot['stratum'] == 'S1' for slot in order))
        self.assertEqual(len(lab_design.leftover_slots(roster, 'T3', DESIGN_SEED_BASE)), 1)

    def test_order_document_matches_the_roster_it_was_built_from(self):
        """The document's `n_pairs` is whatever the rule gives on the roster it was handed.

        Renamed from `test_order_document_horizon`: this roster has had NOTHING excluded, so
        its 568 is the loose pre-exclusion bound and calling it a horizon is the mislabelling
        coordinator ruling 49 asks to stop. The post-exclusion document is checked too, and
        it is at most 565.
        """
        roster = full_roster()
        self.assertEqual(roster['n_excluded'], 0, 'this is the PRE-exclusion roster')
        document = lab_design.order_document(roster, 'T4', DESIGN_SEED_BASE)
        self.assertEqual(document['n_pairs'], 568)               # pre-exclusion bound
        self.assertEqual(len(document['pairs']), 568)
        self.assertEqual(document['trial_no'], 4)
        self.assertEqual(document['roster_sha256'], roster['roster_sha256'])
        self.assertEqual(len(document['leftovers']), 2)          # 591 and 547 are both odd
        blind = blind_roster()
        blind_document = lab_design.order_document(blind, 'T4', DESIGN_SEED_BASE)
        self.assertEqual(blind_document['n_pairs'], blind['n_pairs'])
        self.assertLessEqual(blind_document['n_pairs'], 565, 'the horizon is at most 565')
        self.assertEqual(len(blind_document['pairs']), blind_document['n_pairs'])

    def test_orders_differ_between_trials_and_repeat_within_one(self):
        roster = blind_roster()
        signatures = {trial: lab_design.order_sha256(
            lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)) for trial in lab_design.TRIAL_NO}
        self.assertEqual(len(set(signatures.values())), 4)
        again = lab_design.order_sha256(lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE))
        self.assertEqual(again, signatures['T1'])
        other_seed = lab_design.order_sha256(
            lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE + 1))
        self.assertNotEqual(other_seed, signatures['T1'])

    def test_order_write_once_and_roundtrip(self):
        roster = synthetic_roster(8, 6)
        order = lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'arrival_order_T1.json'
            digest = lab_design.write_order(order, path)
            self.assertRegex(digest, r'^[0-9a-f]{64}$')
            self.assertEqual(lab_design.load_order(path), order)
            self.assertEqual(lab_design.write_order(order, path), digest)
            other = lab_design.arrival_order(roster, 'T2', DESIGN_SEED_BASE)
            with self.assertRaises(lab_common.WriteOnceViolation):
                lab_design.write_order(other, path)
            document_path = Path(tmp) / 'arrival_order_T1_full.json'
            document = lab_design.order_document(roster, 'T1', DESIGN_SEED_BASE)
            lab_design.write_order_document(document, document_path)
            self.assertEqual(lab_design.load_order(document_path), order)

    def test_assert_disjoint(self):
        roster = blind_roster()
        orders = {trial: lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
                  for trial in lab_design.TRIAL_NO}
        lab_design.assert_disjoint(orders)
        broken = {t: [dict(s) for s in o] for t, o in orders.items()}
        broken['T1'][5]['uids'] = (broken['T1'][4]['uids'][0], broken['T1'][5]['uids'][1])
        with self.assertRaises(ValueError):
            lab_design.assert_disjoint(broken)

    def test_design_carries_no_orientation(self):
        source = (HERE / 'lab_design.py').read_text(encoding='utf-8')
        for token in ('urandom', 'coin', 'arm', 'incumbent', 'candidate'):
            self.assertNotIn(token, source, 'lab_design.py must not contain %r' % token)
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0])
        self.assertLessEqual(imported - {'__future__', 'json', 'pathlib', 'typing'},
                             {'numpy', 'lab_common'})


# ==================================================================================================
# lab_coin
# ==================================================================================================


class CoinTests(unittest.TestCase):

    def test_orientation_map(self):
        slot = {'pair': 1, 'stratum': 'S1', 'arrivals': (1, 2), 'uids': ('mbpp/2', 'mbpp/3')}
        one = lab_coin.assignment(slot, lab_coin.Coin(raw_hex='ff' * 8, bit=1))
        self.assertEqual(one, {1: 'candidate', 2: 'incumbent'})
        zero = lab_coin.assignment(slot, lab_coin.Coin(raw_hex='00' * 8, bit=0))
        self.assertEqual(zero, {1: 'incumbent', 2: 'candidate'})
        self.assertEqual(lab_coin.ORIENTATION[1], ('candidate', 'incumbent'))
        self.assertEqual(lab_coin.ORIENTATION[0], ('incumbent', 'candidate'))
        for pair_no in (1, 7, 284):
            slot = {'pair': pair_no, 'stratum': 'S1',
                    'arrivals': (2 * pair_no - 1, 2 * pair_no), 'uids': ('a', 'b')}
            assigned = lab_coin.assignment(slot, lab_coin.Coin(raw_hex='01' * 8, bit=1))
            self.assertEqual(sorted(assigned), [2 * pair_no - 1, 2 * pair_no])
            self.assertEqual(sorted(assigned.values()), ['candidate', 'incumbent'])

    def test_coin_uses_only_urandom(self):
        """With `os.urandom` patched, the arms follow the patched stream exactly (protocol 4.2 vi)."""
        stream = [bytes([0x01, 0, 0, 0, 0, 0, 0, 0]), bytes([0x02, 0, 0, 0, 0, 0, 0, 0]),
                  bytes([0xff, 0, 0, 0, 0, 0, 0, 0]), bytes([0xfe, 0, 0, 0, 0, 0, 0, 0])]
        expected_bits = [1, 0, 1, 0]
        with tempfile.TemporaryDirectory() as tmp:
            log = FakeEventLog(Path(tmp) / 'seg_0000.jsonl')
            with _PatchedUrandom(list(stream)) as patched:
                results = []
                for pair_no in range(1, 5):
                    slot = {'pair': pair_no, 'stratum': 'S1',
                            'arrivals': (2 * pair_no - 1, 2 * pair_no), 'uids': ('a', 'b')}
                    results.append(lab_coin.draw_and_commit(log, slot))
            log.close()
            self.assertEqual(patched.calls, [8, 8, 8, 8], 'exactly one os.urandom(8) per pair')
            for index, (coin, assigned, event) in enumerate(results):
                self.assertEqual(coin.bit, expected_bits[index])
                self.assertEqual(coin.raw_hex, stream[index].hex())
                first_arrival = 2 * (index + 1) - 1
                self.assertEqual(assigned[first_arrival],
                                 'candidate' if expected_bits[index] else 'incumbent')
                self.assertEqual(event['body']['raw_hex'], stream[index].hex())
                self.assertEqual(event['body']['bit'], expected_bits[index])
                self.assertEqual(event['body']['entropy_source'], 'os.urandom(8)')

    def test_coin_has_no_other_randomness(self):
        source = (HERE / 'lab_coin.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0])
        for forbidden in ('random', 'secrets', 'numpy', 'lab_design', 'lab_monitor'):
            self.assertNotIn(forbidden, imported)
        calls = {node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertIn('urandom', calls)
        self.assertLessEqual(calls & {'random', 'randbytes', 'token_bytes', 'getrandbits'}, set())

    def test_coin_write_ahead(self):
        """The fsync for `coin_drawn` happens before `draw_and_commit` returns and before any job."""
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp) / 'jobs'
            jobs.mkdir()
            trace: list = []
            log = FakeEventLog(Path(tmp) / 'seg_0000.jsonl', trace=trace)
            original = lab_common.fullsync
            jobs_at_fsync: list[int] = []

            def spy(fd: int) -> None:
                jobs_at_fsync.append(len(list(jobs.iterdir())))
                original(fd)

            lab_common.fullsync = spy
            try:
                slot = {'pair': 1, 'stratum': 'S1', 'arrivals': (1, 2), 'uids': ('a', 'b')}
                before = len(jobs_at_fsync)
                coin, assigned, event = lab_coin.draw_and_commit(log, slot)
                trace.append(('returned', 'coin_drawn'))
                after = len(jobs_at_fsync)
            finally:
                lab_common.fullsync = original
            # the write-ahead fsync happened during the call ...
            self.assertGreater(after, before)
            # ... with no job file in existence at that moment ...
            self.assertEqual(jobs_at_fsync, [0])
            # ... the durable flag was actually requested ...
            self.assertEqual(log.durable_calls, [('coin_drawn', True)])
            # ... and the ordering was write, fsync, return.
            self.assertEqual(trace, [('write', 'coin_drawn'), ('fsync', 'coin_drawn'),
                                     ('returned', 'coin_drawn')])
            # the line is readable on disk once the call returned, before any dispatch
            log.close()
            lines = [json.loads(line) for line in
                     (Path(tmp) / 'seg_0000.jsonl').read_text().splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]['type'], 'coin_drawn')
            self.assertEqual(lines[0]['body']['assignment'],
                             {'1': assigned[1], '2': assigned[2]})
            self.assertEqual(lines[0]['h'], event['h'])
            (jobs / 'job_1_1.json').write_text('{}')      # the dispatch may only happen now
            self.assertEqual(len(list(jobs.iterdir())), 1)

    def test_coin_balance_10k(self):
        """protocol 4.3 plumbing self-test on 10,000 NON-design coins. Stochastic by construction."""
        result = lab_coin.selftest_entropy()
        self.assertEqual(result['n'], 10_000)
        self.assertEqual(sorted(result), ['n', 'ok', 'ones'])
        self.assertTrue(4850 <= result['ones'] <= 5150,
                        'entropy self-test outside [4850, 5150]: ones=%d' % result['ones'])
        self.assertTrue(result['ok'])

    def test_selftest_reports_failure_without_repeating(self):
        with _PatchedUrandom([bytes([1, 0, 0, 0, 0, 0, 0, 0])] * 10):
            result = lab_coin.selftest_entropy(n=10, lo=4, hi=6)
        self.assertEqual(result, {'n': 10, 'ones': 10, 'ok': False})


class CoinOrderingTests(unittest.TestCase):
    """Protocol 4.2 invariants, audited by `lab_coin.coin_ordering_findings`."""

    def _log(self, tmp: str, name: str = 'seg_0000.jsonl') -> FakeEventLog:
        return FakeEventLog(Path(tmp) / name)

    def test_clean_chain_has_no_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            for pair_no in (1, 2, 3):
                builder.full_pair(pair_no)
            log.close()
            self.assertEqual(lab_coin.coin_ordering_findings(log.events), [])

    def test_one_coin_per_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            builder.coin(1)
            builder.coin(1)                       # a second coin for the same pair
            log.close()
            findings = lab_coin.coin_ordering_findings(log.events)
            self.assertIn('duplicate_coin:pair=1', [f.split(',')[0] for f in findings])

    def test_no_coin_before_the_start_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start(receipt=False)          # anchor requested but not yet receipted
            builder.enroll(1)
            builder.coin(1)
            log.close()
            findings = lab_coin.coin_ordering_findings(log.events)
            self.assertIn('coin_before_start_receipt:pair=1', [f.split(',')[0] for f in findings])

    def test_no_coin_after_a_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.full_pair(1)
            builder.decision(kind='harm_keep_incumbent', n=1)
            builder.enroll(2)
            builder.coin(2)
            log.close()
            findings = lab_coin.coin_ordering_findings(log.events)
            self.assertIn('coin_after_decision:pair=2', [f.split(',')[0] for f in findings])

    def test_next_coin_only_after_both_reveals_and_the_look(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            drawn = builder.coin(1)
            builder.start_episodes(1, drawn['assignment'])
            builder.reveal(1, 1)                  # only ONE of the two episodes revealed
            builder.enroll(2)
            builder.coin(2)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('coin_before_partner_reveals:pair=2', prefixes)
            self.assertIn('coin_before_evaluation:pair=2', prefixes)

        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            drawn = builder.coin(1)
            builder.start_episodes(1, drawn['assignment'])
            builder.reveal(1, 1)
            builder.reveal(1, 2)                  # both revealed, but no evaluation yet
            builder.enroll(2)
            builder.coin(2)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertNotIn('coin_before_partner_reveals:pair=2', prefixes)
            self.assertIn('coin_before_evaluation:pair=2', prefixes)

    def test_an_enroll_look_does_not_satisfy_the_evaluation_invariant(self):
        """Invariant (ii) needs the look taken AFTER both reveals, not the enroll-triggered one."""
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            drawn = builder.coin(1)
            builder.start_episodes(1, drawn['assignment'])
            builder.look(1, trigger='enroll')     # the only update at prefix 1, before the reveals
            builder.reveal(1, 1)
            builder.reveal(1, 2)
            builder.enroll(2)
            builder.coin(2)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertNotIn('coin_before_partner_reveals:pair=2', prefixes)
            self.assertIn('coin_before_evaluation:pair=2', prefixes)
            self.assertEqual(len(prefixes), 1)

    def test_re_enrollment_after_a_crash_between_enroll_and_coin(self):
        """A crash between `pair_enrolled` and `coin_drawn`: re-enroll, then exactly one coin."""
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            log.close()                           # crash here: enrolled, no coin
            resumed = FakeEventLog(Path(tmp) / 'seg_0000.jsonl')
            resumed.events = list(log.events)
            resumed_builder = ChainBuilder(resumed)
            resumed_builder.enroll(1, re_enrolled=True)
            resumed_builder.coin(1)
            resumed.close()
            self.assertEqual(lab_coin.coin_ordering_findings(resumed.events), [])
            coins = [e for e in resumed.events if e['type'] == 'coin_drawn']
            self.assertEqual(len(coins), 1, 'exactly one coin survives the crash')
            enrollments = [e for e in resumed.events if e['type'] == 'pair_enrolled']
            self.assertEqual([e['body']['re_enrolled'] for e in enrollments], [False, True])

    def test_re_enrollment_after_a_coin_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            builder.coin(1)
            builder.enroll(1, re_enrolled=True)   # a redraw path: forbidden
            builder.coin(1)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('re_enrollment_after_coin:pair=1', prefixes)
            self.assertIn('duplicate_coin:pair=1', prefixes)

    def test_unflagged_duplicate_enrollment_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            builder.enroll(1)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('duplicate_enrollment_not_flagged:pair=1', prefixes)

    def test_dispatch_before_the_coin_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            log.append('episode_started', {'arrival': 1, 'pair': 1, 'position': 1,
                                           'arm': 'candidate'})
            builder.coin(1)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('dispatch_before_coin:arrival=1', prefixes)

    def test_arm_must_come_from_the_coin(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            drawn = builder.coin(1)
            flipped = {1: 'incumbent' if drawn['assignment'][1] == 'candidate' else 'candidate',
                       2: drawn['assignment'][2]}
            builder.start_episodes(1, flipped)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('arm_not_from_coin:arrival=1', prefixes)

    def test_bit_must_come_from_the_logged_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            builder.enroll(1)
            log.append('coin_drawn', {'pair': 1, 'entropy_source': 'os.urandom(8)',
                                      'raw_hex': '02' * 8, 'bit': 1,
                                      'assignment': {'1': 'candidate', '2': 'incumbent'}},
                       durable=True)
            log.close()
            prefixes = [f.split(',')[0] for f in lab_coin.coin_ordering_findings(log.events)]
            self.assertIn('bit_not_from_raw:pair=1', prefixes)

    def test_assignments_from_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp)
            builder = ChainBuilder(log)
            builder.start()
            expected: dict[int, str] = {}
            for pair_no in (1, 2):
                drawn = builder.full_pair(pair_no)
                expected.update(drawn['assignment'])
            log.close()
            self.assertEqual(lab_coin.assignments_from_chain(log.events), expected)
            for pair_no in (1, 2):
                arms = sorted(expected[a] for a in (2 * pair_no - 1, 2 * pair_no))
                self.assertEqual(arms, ['candidate', 'incumbent'],
                                 'every pair holds exactly one episode per arm')


class SeedTests(unittest.TestCase):
    """protocol 5.5 / PROTOCOL-GAP PG-8. The worker itself is G4's; the rule is exercised here."""

    def test_seed_low_bit_is_the_worker_index(self):
        for worker_index in (0, 1):
            used: set[int] = set()
            for _ in range(2000):
                seed = lab_coin.draw_seed(worker_index, used)
                self.assertEqual(seed & 1, worker_index)
                self.assertEqual(lab_coin.seed_half(seed), worker_index)
                self.assertNotEqual(seed, lab_coin.SEED_FORBIDDEN)
                self.assertTrue(0 <= seed <= 0x7FFFFFFF)
            self.assertEqual(len(used), 2000, 'no duplicate inside one worker half')

    def test_no_cross_worker_collision_is_possible(self):
        zero = {lab_coin.draw_seed(0) for _ in range(5000)}
        one = {lab_coin.draw_seed(1) for _ in range(5000)}
        self.assertEqual(zero & one, set())
        self.assertTrue(all(s % 2 == 0 for s in zero))
        self.assertTrue(all(s % 2 == 1 for s in one))

    def test_seed_redraws_on_a_duplicate_within_the_half(self):
        repeated = (0x12345678).to_bytes(4, 'big')
        fresh = (0x7ABCDEF0).to_bytes(4, 'big')
        with _PatchedUrandom([repeated, repeated, fresh]):
            used: set[int] = set()
            first = lab_coin.draw_seed(0, used)
            second = lab_coin.draw_seed(0, used)
        self.assertNotEqual(first, second)
        self.assertEqual(first, (0x12345678 & lab_coin.SEED_MASK))
        self.assertEqual(second, (0x7ABCDEF0 & lab_coin.SEED_MASK))
        self.assertEqual(used, {first, second})

    def test_seed_never_reads_the_orientation(self):
        """The seed stream is identical whatever the patched coin stream says (protocol 5.5)."""
        seed_bytes = [(0x11111110 + i).to_bytes(4, 'big') for i in range(4)]
        coin_bytes_a = [bytes([0x01] + [0] * 7), bytes([0x01] + [0] * 7)]
        coin_bytes_b = [bytes([0x00] + [0] * 7), bytes([0x00] + [0] * 7)]
        results = []
        for coin_stream in (coin_bytes_a, coin_bytes_b):
            with tempfile.TemporaryDirectory() as tmp:
                log = FakeEventLog(Path(tmp) / 'seg_0000.jsonl')
                script = [coin_stream[0], seed_bytes[0], seed_bytes[1],
                          coin_stream[1], seed_bytes[2], seed_bytes[3]]
                with _PatchedUrandom(list(script)):
                    seeds = []
                    for pair_no in (1, 2):
                        slot = {'pair': pair_no, 'stratum': 'S1',
                                'arrivals': (2 * pair_no - 1, 2 * pair_no), 'uids': ('a', 'b')}
                        lab_coin.draw_and_commit(log, slot)
                        seeds.append(lab_coin.draw_seed(0))
                        seeds.append(lab_coin.draw_seed(1))
                log.close()
                results.append(seeds)
        self.assertEqual(results[0], results[1])

    def test_seed_is_spooled_before_the_post(self):
        """The seed reaches the fsynced spool before anything is sent (protocol 5.5, 13.1).

        `lab_client` is G4's; the ordering contract is exercised here with a local stand-in worker and
        a POST spy that reads the spool from disk at the moment it is called.
        """
        with tempfile.TemporaryDirectory() as tmp:
            spool = Path(tmp) / 'ep_1_1.jsonl'
            observed: list[dict] = []

            def post(payload: dict) -> dict:
                on_disk = [json.loads(line) for line in
                           spool.read_text().splitlines() if line.strip()]
                observed.append({'payload': payload, 'spool': on_disk})
                return {'seed': payload['seed']}

            def one_try(worker_index: int, used: set[int]) -> int:
                seed = lab_coin.draw_seed(worker_index, used)
                fd = os.open(spool, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
                try:
                    lab_common.append_line_durable(
                        fd, lab_common.canonical_json(
                            {'type': 'call_started', 'seed': seed,
                             'worker_index': worker_index}), durable=True)
                finally:
                    os.close(fd)
                receipt = post({'seed': seed})
                if receipt['seed'] != seed:
                    raise AssertionError('receipted seed differs from the sent seed')
                return seed

            used: set[int] = set()
            seeds = [one_try(0, used), one_try(0, used)]
            self.assertEqual(len(observed), 2)
            self.assertEqual([len(o['spool']) for o in observed], [1, 2],
                             'the spool line is on disk before the POST')
            for index, seed in enumerate(seeds):
                self.assertEqual(observed[index]['spool'][index]['seed'], seed)
                self.assertEqual(seed & 1, 0)


class DocumentedSignatureTests(unittest.TestCase):
    """The public names ARCHITECTURE 3.4-3.6 fixes, with the documented parameter names."""

    def test_signatures(self):
        import inspect
        expected = {
            (lab_data, 'fetch_sources'): ['dest', 'offline'],
            (lab_data, 'build_candidate_tasks'): ['raw'],
            # DEVIATION from ARCHITECTURE_FINAL.md section 3.4, recorded not hidden:
            # `on_attempt` is an EXTRA KEYWORD-ONLY parameter added by the D1
            # retention repair (root 2026-09-21 18:54, ranked item 2). Retention
            # requires the caller to RECEIVE each per-attempt verifier record; the
            # previous signature gave it no way to, so the preimage of every
            # detail digest was unavoidably discarded. The same deviation shape --
            # an added keyword-only parameter -- already exists and is tolerated
            # for lab_hostcheck.enumerate_foreign_consumers and lab_server.start /
            # .restart, which tests_lab_isolation reports as DEVIATION rather than
            # failing. Defaulting to None keeps every existing call site valid.
            (lab_data, 'sweep_references'): ['tasks', 'cfg', 'on_progress',
                                            'on_attempt'],
            (lab_data, 'build_roster'): ['tasks', 'exclusions', 'cfg'],
            (lab_data, 'write_roster'): ['roster', 'path'],
            (lab_data, 'load_roster'): ['path'],
            (lab_data, 'load_tasks_by_uid'): ['roster', 'sources_dir'],
            (lab_design, 'arrival_order'): ['roster', 'trial', 'design_seed_base'],
            (lab_design, 'write_order'): ['order', 'path'],
            (lab_design, 'load_order'): ['path'],
            (lab_design, 'order_sha256'): ['order'],
            (lab_design, 'assert_disjoint'): ['orders'],
            (lab_coin, 'draw'): [],
            (lab_coin, 'assignment'): ['pair', 'coin'],
            (lab_coin, 'draw_and_commit'): ['log', 'pair'],
            (lab_coin, 'selftest_entropy'): ['n', 'lo', 'hi'],
        }
        for (module, name), params in expected.items():
            function = getattr(module, name)
            self.assertEqual(list(inspect.signature(function).parameters), params,
                             '%s.%s' % (module.__name__, name))
        self.assertEqual(lab_coin.Coin('ab' * 8, 1).source, 'os.urandom(8)')
        self.assertEqual(sorted(lab_coin.ORIENTATION), [0, 1])
        self.assertEqual(set(lab_data.SOURCES), {'mbpp_sanitized', 'humaneval', 'mbpp_full'})


class TestDataTests(unittest.TestCase):
    """`testdata/roster_small.json`, the dry-run fixture G4 and G5 consume."""

    def setUp(self) -> None:
        self.path = HERE / 'testdata' / 'roster_small.json'
        if not self.path.is_file():
            self.skipTest('roster_small.json has not been generated yet')

    def test_shape_and_counts(self):
        roster = lab_data.load_roster(self.path)
        self.assertEqual(roster['n_S1'], 16)
        self.assertEqual(roster['n_S2'], 8)
        self.assertEqual(roster['n_total'], 24)
        self.assertEqual(roster['n_pairs'], 16 // 2 + 8 // 2)
        self.assertEqual(roster['n_pairs'], 12)
        self.assertEqual(len(roster['task_records']), 24)

    def test_records_carry_references_and_hidden_tests(self):
        roster = lab_data.load_roster(self.path)
        tasks = lab_data.load_tasks_by_uid(roster, HERE / 'testdata')
        self.assertEqual(len(tasks), 24)
        for uid, task in tasks.items():
            self.assertTrue(task['reference'].strip(), uid)
            self.assertTrue(task['entry_point'], uid)
            has_hidden = bool(task['test_list']) or bool(task['test'])
            self.assertTrue(has_hidden, uid)
            self.assertEqual(lab_data.task_content_hash(task),
                             roster['task_content_sha256_by_uid'][uid])

    def test_matches_the_pinned_sources(self):
        roster = lab_data.load_roster(self.path)
        by_uid = {t['uid']: t for t in real_tasks()}
        for record in roster['task_records']:
            self.assertIn(record['uid'], by_uid)
            self.assertEqual(lab_data.task_content_hash(lab_data.Task(**record)),
                             lab_data.task_content_hash(by_uid[record['uid']]),
                             'the fixture must be the pinned task, byte for byte')

    def test_dry_run_order_is_stratified(self):
        roster = lab_data.load_roster(self.path)
        for trial in lab_design.TRIAL_NO:
            order = lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
            self.assertEqual(len(order), 12)
            lab_design.check_order(order)
            lab_design.assert_no_mixed_slot(order, roster)
        lab_design.assert_disjoint({t: lab_design.arrival_order(roster, t, DESIGN_SEED_BASE)
                                    for t in lab_design.TRIAL_NO})


# ==================================================================================================
# Provenance review section 4: the horizon after exclusions, and the leftover parity rule
# ==================================================================================================
class HorizonAfterExclusionsTests(unittest.TestCase):
    """568 is a LOOSE PRE-EXCLUSION bound, never the post-exclusion horizon.

    `floor(591/2) + floor(547/2) = 568` counts the candidate task lists before protocol 3.2
    has excluded anything. The six declared smoke tasks are all `mbpp_full/*`, so they come
    out of S2 and lower its ceiling to 541, which lowers `N_P` to at most 565. Further
    exclusions (duplicate prompts, missing entry points, unparsable references, and the
    reference sweep, which can also touch S1) lower it again. The exact rule is
    `N_P = floor(n_S1 / 2) + floor(n_S2 / 2)` on the SURVIVING counts and nothing else.
    """

    def test_568_is_the_pre_exclusion_bound_only(self):
        full = full_roster()
        self.assertEqual((full['n_S1'], full['n_S2'], full['n_pairs']), (591, 547, 568))
        self.assertEqual(full['n_excluded'], 0, '568 is the count with NO exclusion applied')

    def test_the_six_smoke_tasks_put_the_ceiling_at_565(self):
        """With only the six declared smoke exclusions, N_P is exactly 565 and there are two
        leftovers, because 591 and 541 are both odd."""
        tasks = real_tasks()
        smoke = [e for e in lab_data.prospective_exclusions(tasks, {})
                 if e['reason'] == 'out_of_design_smoke_task']
        self.assertEqual(len(smoke), 6)
        self.assertEqual(sorted(e['uid'] for e in smoke), sorted(lab_data.SMOKE_TASKS))
        self.assertTrue(all(uid.startswith('mbpp_full/') for uid in lab_data.SMOKE_TASKS),
                        'all six smoke tasks are in S2, which is why only S2 shrinks here')
        roster = lab_data.build_roster(tasks, smoke, {})
        self.assertEqual(roster['n_S1'], 591)
        self.assertEqual(roster['n_S2'], 541)
        self.assertEqual(roster['n_pairs'], 591 // 2 + 541 // 2)
        self.assertEqual(roster['n_pairs'], 565)
        self.assertLess(roster['n_pairs'], 568)
        self.assertEqual(len(lab_design.leftover_slots(roster, 'T4', DESIGN_SEED_BASE)), 2)

    def test_the_remaining_blind_exclusions_lower_it_further(self):
        blind = blind_roster()
        self.assertLessEqual(blind['n_S2'], 541)
        self.assertLessEqual(blind['n_pairs'], 565)
        self.assertEqual(blind['n_pairs'], blind['n_S1'] // 2 + blind['n_S2'] // 2)
        self.assertGreater(blind['n_excluded'], 6, 'more than the six smoke tasks are blind-excluded')

    def test_leftovers_are_the_parity_sum_and_can_be_0_1_or_2(self):
        """The table's unconditional "one leftover per stratum" is wrong: the count is
        `(n_S1 % 2) + (n_S2 % 2)`, which is 0, 1 or 2 depending on the surviving counts."""
        for n_s1, n_s2, n_pairs, n_left in ((590, 540, 565, 0), (591, 540, 565, 1),
                                            (590, 541, 565, 1), (591, 541, 565, 2)):
            with self.subTest(n_S1=n_s1, n_S2=n_s2):
                roster = synthetic_roster(n_s1, n_s2)
                self.assertEqual(roster['n_pairs'], n_pairs)
                slots = lab_design.leftover_slots(roster, 'T1', DESIGN_SEED_BASE)
                self.assertEqual(len(slots), (n_s1 % 2) + (n_s2 % 2))
                self.assertEqual(len(slots), n_left)
                self.assertEqual(len(lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE)),
                                 n_pairs)

    def test_the_only_post_exclusion_figure_is_565_or_less(self):
        """Ruling 49's second free fix, as a test rather than as prose. Every roster that has
        had ANY exclusion applied must report `n_pairs <= 565`; 568 may appear only on the
        roster with `n_excluded == 0`, where it is the loose pre-exclusion bound."""
        tasks = real_tasks()
        smoke = [e for e in lab_data.prospective_exclusions(tasks, {})
                 if e['reason'] == 'out_of_design_smoke_task']
        for label, roster in (('smoke only', lab_data.build_roster(tasks, smoke, {})),
                              ('all blind', blind_roster())):
            with self.subTest(roster=label):
                self.assertGreater(roster['n_excluded'], 0)
                self.assertLessEqual(roster['n_pairs'], 565,
                                     '568 is never a post-exclusion figure')
        self.assertEqual(full_roster()['n_excluded'], 0,
                         'the only roster that gives 568 is the one with nothing excluded')

    def test_the_four_trials_reuse_one_roster_and_are_not_replications(self):
        """Root warning (provenance review section 4). The four trials differ ONLY in the
        order seed; they draw from the same task pool. Their results are therefore not
        independent replications and must never be pooled as such, and S1 -- the 591 tasks
        the pilot already observed -- is never "fresh tasks"."""
        roster = synthetic_roster(8, 6)                # even counts: no leftover to move
        pools = {trial: {uid
                         for slot in lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE)
                         for uid in slot['uids']}
                 for trial in lab_design.TRIAL_NO}
        self.assertEqual(len({frozenset(p) for p in pools.values()}), 1,
                         'every trial enrolls the same 14 tasks; only the order differs')
        signatures = {trial: lab_design.order_sha256(
            lab_design.arrival_order(roster, trial, DESIGN_SEED_BASE))
            for trial in lab_design.TRIAL_NO}
        self.assertEqual(len(set(signatures.values())), 4, 'the orders themselves do differ')


# ==================================================================================================
# Coordinator ruling 49: proportional allocation, and the MBPP/HumanEval stratum separation
# ==================================================================================================
class ProportionalAllocationTests(unittest.TestCase):
    """ALLOCATION ACROSS STRATA MUST STAY PROPORTIONAL, or the guardrail changes its target.

    Each stratum contributes `floor(n_s / 2)` pairs and protocol 3.4 permutes the COMBINED
    pair list, so the stratum mix of every enrolled prefix is the roster's own mix in
    expectation. That is what makes the guarded estimand invariant to the stopping time: the
    band is anytime-valid for the mean of the pairs it has seen, and proportionality is the
    separate property that keeps that mean equal to the contrast the protocol names. A
    blockwise or stratum-weighted order would leave the band valid and the ESTIMAND wrong,
    which is the failure mode this class exists to catch.

    Deterministic: the seeds below are fixed constants, so these tests either always pass or
    always fail.
    """

    #: 400 S1 + 200 S2 -> 200 + 100 = 300 pairs, so one third of every prefix should be S2.
    N_S1, N_S2, PREFIX, SEEDS = 400, 200, 30, 200

    def _orders(self):
        roster = synthetic_roster(self.N_S1, self.N_S2)
        return roster, [lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE + k)
                        for k in range(self.SEEDS)]

    def test_pair_counts_per_stratum_are_floor_half_the_surviving_counts(self):
        """The allocation rule itself: no stratum is weighted, on the real roster."""
        for label, roster in (('pre-exclusion', full_roster()), ('blind', blind_roster())):
            with self.subTest(roster=label):
                order = lab_design.arrival_order(roster, 'T4', DESIGN_SEED_BASE)
                counts = {s: 0 for s in lab_design.STRATA}
                for slot in order:
                    counts[slot['stratum']] += 1
                self.assertEqual(counts['S1'], roster['n_S1'] // 2)
                self.assertEqual(counts['S2'], roster['n_S2'] // 2)
                self.assertEqual(sum(counts.values()), roster['n_pairs'])

    def test_every_enrolled_prefix_is_proportional_in_expectation(self):
        """A stopping prefix is an exchangeable sample of the strata, not a block of one."""
        roster, orders = self._orders()
        share = (self.N_S2 // 2) / (self.N_S1 // 2 + self.N_S2 // 2)
        expected = self.PREFIX * share
        observed = [sum(1 for slot in order[:self.PREFIX] if slot['stratum'] == 'S2')
                    for order in orders]
        mean = sum(observed) / len(observed)
        self.assertAlmostEqual(mean, expected, delta=1.0,
                               msg='prefix stratum mix drifts from the roster mix')
        # and no single prefix is degenerate, which a blockwise order would make every one
        self.assertGreater(min(observed), 0)
        self.assertLess(max(observed), self.PREFIX)

    def test_a_blockwise_order_would_be_caught_by_the_same_check(self):
        """Negative control: the check above has teeth."""
        roster, orders = self._orders()
        blockwise = sorted(orders[0], key=lambda slot: slot['stratum'])
        observed = sum(1 for slot in blockwise[:self.PREFIX] if slot['stratum'] == 'S2')
        share = (self.N_S2 // 2) / (self.N_S1 // 2 + self.N_S2 // 2)
        self.assertEqual(observed, 0)
        self.assertGreater(abs(observed - self.PREFIX * share), 1.0)

    def test_a_weighted_allocation_would_change_the_guarded_estimand(self):
        """Why it matters, arithmetically, with no simulation.

        If the two strata carry different true guarded means, the mean over enrolled pairs is
        the stratum-size-weighted average. Re-weighting the allocation moves that average, so
        a band that is perfectly valid for what it saw certifies a different quantity.
        """
        roster = synthetic_roster(self.N_S1, self.N_S2)
        w1, w2 = roster['n_S1'] // 2, roster['n_S2'] // 2
        mu_s1, mu_s2 = 0.00, -0.12                       # illustrative stratum means
        proportional = (w1 * mu_s1 + w2 * mu_s2) / (w1 + w2)
        reweighted = (w2 * mu_s1 + w1 * mu_s2) / (w1 + w2)   # strata swapped in weight
        self.assertAlmostEqual(proportional, -0.04, places=12)
        self.assertGreater(abs(reweighted - proportional), 0.03,
                           'a re-weighted allocation moves the estimand by more than delta')


class StratumSeparationTests(unittest.TestCase):
    """Coordinator ruling 49's MBPP/HumanEval separation: its single change point, and the
    reason it is not applied in `lab_data` alone.

    The point of these assertions is that nobody can later believe the separation has been
    made when it has not, and that when it IS made there is exactly one table to edit.
    """

    def test_the_stratum_table_drives_every_task(self):
        """`BENCHMARK_STRATUM` is the single source of truth, not scattered literals."""
        for task in real_tasks():
            self.assertEqual(task['stratum'], lab_data.BENCHMARK_STRATUM[task['benchmark']])
        source = (HERE / 'lab_data.py').read_text(encoding='utf-8')
        body = source.split('def build_candidate_tasks', 1)[1].split('\ndef ', 1)[0]
        self.assertNotIn("stratum='S1'", body)
        self.assertNotIn("stratum='S2'", body)

    def test_mbpp_and_humaneval_still_share_one_stratum(self):
        """Recorded as the CURRENT state, deliberately, so the ruling stays visible."""
        self.assertEqual(lab_data.BENCHMARK_STRATUM['mbpp'],
                         lab_data.BENCHMARK_STRATUM['humaneval'])
        self.assertEqual(sorted(set(lab_data.BENCHMARK_STRATUM.values())), ['S1', 'S2'])
        self.assertEqual(lab_data.STRATA, lab_design.STRATA,
                         'the two modules must agree on the stratum vocabulary')
        s1 = [t for t in real_tasks() if t['stratum'] == 'S1']
        self.assertEqual(len([t for t in s1 if t['benchmark'] == 'mbpp']), 427)
        self.assertEqual(len([t for t in s1 if t['benchmark'] == 'humaneval']), 164)

    def test_the_separation_is_blocked_on_the_protocol_snippet(self):
        """The reason it is a coordinated amendment and not a local edit.

        Protocol 3.4's literal code block enumerates exactly two strata, and this test file
        transcribes it as an independent oracle. Splitting the strata in `lab_data` alone
        would drop HumanEval from every pairing; splitting them in `lab_design` alone would
        put the implementation ahead of the binding document and turn that oracle into a test
        written from the implementation, which is the anti-pattern the coordinator named.
        """
        snippet = inspect.getsource(protocol_3_4_reference)
        self.assertIn('["S1", "S2"]', snippet)
        # the oracle and the implementation must enumerate the SAME strata, always
        self.assertEqual(tuple(re.findall(r'"(S\d)"', snippet)), lab_design.STRATA)
        # ... and a roster carrying a stratum the implementation does not know would lose it
        roster = synthetic_roster(4, 4)
        roster['S3'] = ['humaneval/%d' % i for i in range(4)]
        roster['tasks'] = list(roster['tasks']) + roster['S3']
        order = lab_design.arrival_order(roster, 'T1', DESIGN_SEED_BASE)
        enrolled = {uid for slot in order for uid in slot['uids']}
        self.assertEqual(len(enrolled & set(roster['S3'])), 0,
                         'a third stratum is silently dropped until lab_design knows it')


# ==================================================================================================
# Provenance review section 3: preflight must bind execution to every MEMBER of the freeze
# ==================================================================================================
import shutil                                            # noqa: E402
from unittest import mock                                # noqa: E402

import dryrun_live_ab as dry                             # noqa: E402
import lab_eventlog                                      # noqa: E402
import lab_orchestrator as orch                          # noqa: E402

_LABEL_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}$')
_HEX64_RE = re.compile(r'^[0-9a-f]{64}$')


class FreezeBundleBindingTests(unittest.TestCase):
    """The regression test the root asked for: hold the APPROVED BUNDLE FIXED, alter each
    frozen artifact independently, and assert that every alteration is refused.

    The defect this closes (provenance review section 3, with an executed witness): preflight
    compared the bundle's own canonical digest with `ctx.bundle_sha` and checked that the
    roster and the arrival order EXISTED, but never compared a single bundle MEMBER with the
    artifact it names. The root kept an unchanged bundle carrying the original
    `config_sha256`, changed `monitor.delta` from .03 to .04, initialised the runtime hashes
    from the current bytes exactly as `make_context` does, and preflight returned `[]`.

    Nothing in this class changes a scientific rule. Every alteration is reverted with the
    temporary tree; `delta` is altered only in a throwaway mock freeze, never in the frozen
    configuration, and the assertion is that the alteration is REFUSED.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='live_ab_bundle_'))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.results = self.root / 'results'
        self.work = self.root / 'work'
        self.built = dry.build_mock_freeze(self.results, n_pairs=4, trial='T4')
        self.freeze = self.results / 'freeze'
        self.bundle_sha = self.built['bundle_sha']
        self.bundle = json.loads((self.freeze / 'freeze_bundle.json').read_text('utf-8'))

    # -- helpers -----------------------------------------------------------------------------
    def _ctx(self):
        """A context built the way a real invocation builds one: the configuration is read
        from the deposited file, and the runtime digests default to the CURRENT bytes."""
        cfg = json.loads((self.freeze / 'config.json').read_text('utf-8'))
        cfg['_runtime'] = {'results_root': str(self.results), 'work_root': str(self.work),
                           'bundle_sha': self.bundle_sha, 'sim': True, 'mock': True,
                           'free_disk_floor_gb': 0.0,
                           'tasks_path': str(self.freeze / 'tasks.json')}
        return orch.make_context('T4', cfg, results_root=self.results, work_root=self.work)

    def _passes(self) -> list:
        return orch.preflight(self._ctx())

    def _refusal(self) -> tuple[set, set]:
        """(closed reason codes, drift item labels) of the refusal, which must happen."""
        with self.assertRaises(lab_common.PreflightError) as caught:
            orch.preflight(self._ctx())
        drift = list(getattr(caught.exception, 'drift', []))
        for row in drift:
            self.assertRegex(str(row['item']), _LABEL_RE,
                             'a drift item must satisfy the event schema label rule')
            self.assertRegex(str(row['expected']), _HEX64_RE)
            self.assertRegex(str(row['found']), _HEX64_RE)
        return set(str(caught.exception).split(',')), {str(r['item']) for r in drift}

    def _rewrite_config(self, mutate) -> None:
        path = self.freeze / 'config.json'
        cfg = json.loads(path.read_text('utf-8'))
        mutate(cfg)
        path.write_text(lab_common.canonical_json(cfg) + '\n', encoding='utf-8')

    # -- the control -------------------------------------------------------------------------
    def test_the_untouched_freeze_passes_with_no_drift(self):
        """Without a control the refusals below would prove nothing."""
        self.assertEqual(self._passes(), [])

    # -- the seven independent alterations ---------------------------------------------------
    def test_an_altered_config_is_refused_the_roots_witness(self):
        """The root's exact witness: bundle unchanged, `monitor.delta` .03 -> .04."""
        self.assertEqual(self._passes(), [])
        self._rewrite_config(lambda c: c['monitor'].__setitem__('delta', 0.04))
        # The bundle on disk is untouched and still carries the ORIGINAL config hash.
        self.assertEqual(json.loads((self.freeze / 'freeze_bundle.json').read_text('utf-8')),
                         self.bundle)
        codes, items = self._refusal()
        self.assertIn('config_sha', codes)
        self.assertIn('config_sha256', items)
        self.assertIn('rule_block_sha256', items,
                      'delta is inside the rule block, so the decision-defining subset moved too')

    def test_a_roster_rewritten_with_its_own_hash_is_refused(self):
        """The hard case: the roster is edited AND its self-referential `roster_sha256` is
        recomputed, so `check_roster` still accepts it. Only the bundle catches this."""
        path = self.freeze / 'roster.json'
        roster = json.loads(path.read_text('utf-8'))
        roster['n_excluded'] = int(roster['n_excluded']) + 1
        roster['roster_sha256'] = lab_data.roster_sha256(roster)
        path.write_text(lab_common.canonical_json(roster) + '\n', encoding='utf-8')
        lab_data.check_roster(json.loads(path.read_text('utf-8')))   # internally consistent
        codes, items = self._refusal()
        self.assertIn('roster_sha', codes)
        self.assertIn('roster_sha256', items)

    def test_a_reordered_arrival_order_is_refused(self):
        """Swapping two enrollment slots after the freeze. `make_context` reads the order
        file without validating it, so preflight is the only thing that can catch this."""
        path = self.freeze / 'arrival_order_T4.json'
        rows = json.loads(path.read_text('utf-8'))
        rows[0]['uids'], rows[1]['uids'] = rows[1]['uids'], rows[0]['uids']
        path.write_text(lab_common.canonical_json(rows) + '\n', encoding='utf-8')
        codes, items = self._refusal()
        self.assertIn('order_sha', codes)
        self.assertIn('arrival_order_sha256.T4', items)

    def test_a_frozen_order_file_that_vanished_is_refused(self):
        """Fail closed: an artifact the freeze NAMES must be present to be checked, even for
        a trial this invocation is not running."""
        (self.freeze / 'arrival_order_T2.json').unlink()
        codes, items = self._refusal()
        self.assertIn('order_sha', codes)
        self.assertIn('arrival_order_sha256.T2', items)

    def test_an_edited_reference_rule_or_harness_file_is_refused(self):
        """The harness files live in the repository and are not editable from a test, so the
        FILE READ is stubbed and nothing else: `harness_file_hashes` returns what it would
        return if that one file had been edited. The byte-level read is exercised for real by
        `test_observed_members_read_the_files_they_name` below."""
        for name in ('lab_reference_rule.py', 'lab_monitor.py', 'lab_orchestrator.py'):
            with self.subTest(file=name):
                edited = dict(lab_common.harness_file_hashes())
                self.assertIn(name, edited)
                edited[name] = lab_common.sha256_text('one edited byte in ' + name)
                with mock.patch.object(lab_common, 'harness_file_hashes', lambda: edited):
                    codes, items = self._refusal()
                self.assertIn('harness_file_sha', codes)
                self.assertIn('harness_file_sha256.' + name, items)

    def test_an_altered_serving_manifest_is_refused_by_name(self):
        """The serving manifest digest is carried inside the frozen configuration, so this
        also moves `config_sha256`; what matters is that the refusal NAMES the manifest."""
        self._rewrite_config(lambda c: c['llama_cpp'].__setitem__(
            'serving_manifest_sha256', lab_common.sha256_text('a different serving build')))
        codes, items = self._refusal()
        self.assertIn('serving_manifest', codes)
        self.assertIn('serving_manifest_sha256', items)

    def test_a_host_outside_the_frozen_hardware_allowlist_is_refused(self):
        """Hardware was recorded at trial start and never compared. It is compared now."""
        self.assertIn(lab_common.hardware_identity(), self.bundle['hardware_allowlist'])
        with mock.patch.object(lab_common, 'hardware_identity', lambda: 'x86_64-linux'):
            codes, items = self._refusal()
        self.assertIn('hardware_allowlist', codes)
        self.assertIn('hardware_identity', items)

    # -- the recomputation really reads the artifacts ----------------------------------------
    def test_observed_members_read_the_files_they_name(self):
        """No stub at all: copy the harness into a temporary directory, append one comment
        line to `lab_reference_rule.py`, and point the recomputation at that copy. Exactly
        one member drifts, which also proves the other members are stable."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp)
            for name in lab_common.HARNESS_FILES:
                source = lab_common.HERE / name
                if source.exists():
                    shutil.copyfile(source, copy / name)
            target = copy / 'lab_reference_rule.py'
            target.write_text(target.read_text('utf-8') + '\n# edited after the freeze\n',
                              encoding='utf-8')
            observed = orch.observed_bundle_members(self.freeze, trial='T4',
                                                    bundle=self.bundle, harness_dir=copy)
            rows = lab_common.verify_bundle_members(self.bundle, observed)
        self.assertEqual({r['item'] for r in rows},
                         {'harness_file_sha256.lab_reference_rule.py'})

    def test_an_untouched_tree_recomputes_to_the_bundle(self):
        observed = orch.observed_bundle_members(self.freeze, trial='T4', bundle=self.bundle)
        self.assertEqual(lab_common.verify_bundle_members(self.bundle, observed), [])
        for member in lab_common.BUNDLE_MEMBERS_RECOMPUTED:
            self.assertIn(member, observed,
                          'every recomputable member must actually be observed in a real tree')

    def test_every_bundle_key_is_recomputed_or_declared_unrecomputable(self):
        """A future bundle key cannot be silently left unchecked: it must be put in one of
        the two lists, and the second list is the DECLARED limit of this gate."""
        recomputed = set(lab_common.BUNDLE_MEMBERS_RECOMPUTED)
        declared = set(lab_common.BUNDLE_MEMBERS_NOT_RECOMPUTED)
        self.assertEqual(recomputed & declared, set())
        self.assertEqual(recomputed | declared, set(lab_common.FREEZE_BUNDLE_KEYS))

    def test_build_freeze_bundle_is_the_only_shape_preflight_accepts(self):
        """`build_freeze_bundle` exists and preflight never called it. The mock freeze is
        built through it, and its key set is exactly what the member check iterates."""
        self.assertEqual(set(self.bundle), set(lab_common.FREEZE_BUNDLE_KEYS))
        with self.assertRaises(lab_common.FreezeIncomplete):
            lab_common.build_freeze_bundle({k: self.bundle[k]
                                            for k in list(self.bundle)[:-1]})

    # -- one canonical digest convention -----------------------------------------------------
    def test_one_canonical_digest_convention_for_the_bundle(self):
        """The CLI default hashed the bundle's RAW BYTES while preflight hashed its
        canonical JSON, so pretty-printing the very same bundle produced
        `freeze_bundle_drift`. Both sides now go through `freeze_bundle_sha256`."""
        path = self.freeze / 'freeze_bundle.json'
        raw_before = lab_common.sha256_file(path)
        canonical_before = lab_common.freeze_bundle_sha256_of_file(path)
        self.assertEqual(canonical_before, self.bundle_sha)
        self.assertNotEqual(raw_before, canonical_before,
                            'the file carries a trailing newline, so the two differ already')
        path.write_text(json.dumps(json.loads(path.read_text('utf-8')),
                                   indent=2, sort_keys=True) + '\n', encoding='utf-8')
        self.assertNotEqual(lab_common.sha256_file(path), raw_before,
                            'the bytes really did change')
        self.assertEqual(lab_common.freeze_bundle_sha256_of_file(path), canonical_before,
                         'the same bundle keeps the same identity when it is pretty-printed')
        self.assertEqual(self._passes(), [],
                         'a pretty-printed bundle must no longer be freeze_bundle_drift')

    def test_a_corrupt_bundle_fails_closed(self):
        (self.freeze / 'freeze_bundle.json').write_text('{not json', encoding='utf-8')
        codes, _ = self._refusal()
        self.assertIn('freeze_bundle_drift', codes)

    def test_a_refusal_carries_its_evidence_into_the_program_chain(self):
        """`preflight_refused` has always had a `drift` field and always wrote `[]`."""
        self._rewrite_config(lambda c: c['monitor'].__setitem__('delta', 0.04))
        ctx = self._ctx()
        self.assertEqual(orch.run_trial(ctx, resume=False), 'aborted')
        read = lab_eventlog.read_chain(self.results / '_program' / 'events', '_program',
                                       self.bundle_sha)
        refusals = [e for e in read.events if e['type'] == 'preflight_refused']
        self.assertEqual(len(refusals), 1)
        body = refusals[0]['body']
        self.assertIn('config_sha', body['checks_failed'])
        self.assertIn('config_sha256', {row['item'] for row in body['drift']})
        self.assertEqual(lab_eventlog.segment_paths(self.results / 'T4' / 'events'), [],
                         'the trial chain must not have been opened')


if __name__ == '__main__':
    unittest.main(verbosity=2)


class ReferenceAttemptRetentionTests(unittest.TestCase):
    """D1/D3 repairs (root 2026-09-21 18:54, ranked item 2 and item 3)."""

    def _rec(self, i=0, out='', err='', success=True, timed_out=False, secs=0.1):
        return {'schema': lab_data.ATTEMPT_RECORD_SCHEMA, 'uid': 'u', 'run_index': i,
                'stdout_tail': out, 'stderr': err, 'success': success,
                'timed_out': timed_out, 'returncode': 0 if success else 1,
                'sentinel_seen': success, 'verify_seconds': secs}

    # -- D1: the preimage is retained and the digest reconstructs from it ----
    def test_digest_reconstructs_from_retained_records(self):
        recs = [self._rec(0, '__LS_VERIFY_OK__deadbeef', ''),
                self._rec(1, 'boom', 'Traceback /tmp/p_9f/prog.py', success=False)]
        exc = lab_data._exclusion('u', 'reference_fails_verify',
                                  lab_data.detail_from_attempts(recs))
        self.assertEqual(lab_data.reconstruct_detail_sha256(recs), exc['detail_sha256'])

    def test_canonicalization_is_byte_compatible_with_pre_repair_digests(self):
        """The rule must reproduce the OLD inline construction exactly.

        Otherwise the repair would orphan every digest recorded before it, which
        would be a worse retention failure than the one being fixed.
        """
        recs = [self._rec(0, 'a', 'b'), self._rec(1, 'c', 'd')]
        legacy = '\n'.join('run%d:%s|%s' % (i, r['stdout_tail'], r['stderr'])
                           for i, r in enumerate(recs))
        self.assertEqual(lab_data.detail_from_attempts(recs), legacy)

    def test_record_retains_flags_and_duration_not_only_the_digest_inputs(self):
        r = self._rec(0, 'x', 'y', success=False, timed_out=True, secs=10.0)
        for key in ('timed_out', 'returncode', 'sentinel_seen', 'verify_seconds',
                    'success', 'stdout_tail', 'stderr'):
            self.assertIn(key, r)

    # -- D3: documented precedence, and no success-favoring change ----------
    def test_a_genuine_hang_is_a_timeout_not_a_verifier_failure(self):
        hang = self._rec(0, '', '', success=False, timed_out=True, secs=10.0)
        self.assertEqual(lab_data.classify_attempt(hang, 2.5), 'reference_timeout')

    def test_non_timeout_failure_is_still_a_verifier_failure(self):
        fail = self._rec(0, '', 'SyntaxError', success=False, timed_out=False, secs=0.2)
        self.assertEqual(lab_data.classify_attempt(fail, 2.5), 'reference_fails_verify')

    def test_slow_but_successful_is_a_timeout(self):
        slow = self._rec(0, 'ok', '', success=True, timed_out=False, secs=3.0)
        self.assertEqual(lab_data.classify_attempt(slow, 2.5), 'reference_timeout')

    def test_healthy_attempt_is_not_excluded(self):
        self.assertIsNone(lab_data.classify_attempt(self._rec(), 2.5))

    def test_exclusion_set_does_not_shrink(self):
        """Every attempt excluded BEFORE the repair is still excluded after it.

        Root: 'Preserve the same exclusion set implied by the protocol, not a
        success-favoring change.'  A hang and a non-timeout failure were both
        `reference_fails_verify` before; both must still be excluded now, only the
        hang's reason moves.
        """
        for rec in (self._rec(0, '', '', success=False, timed_out=True, secs=10.0),
                    self._rec(0, '', '', success=False, timed_out=False, secs=0.2),
                    self._rec(0, 'ok', '', success=True, timed_out=False, secs=3.0)):
            self.assertIsNotNone(lab_data.classify_attempt(rec, 2.5))


class DuplicateRuleScopeTests(unittest.TestCase):
    """D6 repair: the rule compares against ALL S1 tasks, including HumanEval."""

    def test_a_humaneval_twin_is_now_detected(self):
        def task(uid, bench, stratum, prompt):
            return {'uid': uid, 'benchmark': bench, 'stratum': stratum, 'prompt': prompt,
                    'entry_point': 'f', 'reference': 'def f():\n    return 1\n',
                    'test_imports': [], 'test_list': [], 'challenge_test_list': [], 'test': ''}
        tasks = [task('humaneval/1', 'humaneval', 'S1', 'Write a function that adds.'),
                 task('mbpp_full/999', 'mbpp_full', 'S2', 'Write a function that adds.')]
        exc = lab_data.prospective_exclusions(tasks, {'roster': {'smoke_tasks': []}})
        dups = [e for e in exc if e['reason'] == 'duplicate_prompt']
        self.assertEqual([e['uid'] for e in dups], ['mbpp_full/999'],
                         'an S2 prompt duplicating a HUMANEVAL S1 prompt must be excluded; '
                         'the pre-repair code only compared against benchmark=="mbpp"')


class Stage1RegressionFixtureTests(unittest.TestCase):
    """The stage-1 receipt as a regression fixture BOUND TO ITS SOURCE DIGESTS.

    Root: 'Keep the actual stage1 receipt as a regression fixture bound to its
    source digests, rather than a universal hardcoded benchmark size.'

    So the counts are asserted ONLY when the three pinned sources are present and
    hash to the values the receipt was produced from.  If the sources differ, the
    test SKIPS rather than failing -- a different corpus legitimately yields
    different counts, and pinning them universally would turn a provenance change
    into a spurious test failure.
    """

    EXPECTED = {'candidates': 1138, 'exclusions': 8, 'survivors': 1130,
                'n_S1': 591, 'n_S2': 539, 'n_pairs_ceiling': 564}

    def test_counts_match_the_stage1_receipt_for_these_exact_sources(self):
        import collections
        src = lab_common.WORK_ROOT / 'sources'
        if not (src / 'sources.json').is_file():
            self.skipTest('pinned sources not present on this host')
        manifest = json.loads((src / 'sources.json').read_text())
        for name, spec in lab_data.SOURCES.items():
            got = (manifest.get('sources') or {}).get(name) or {}
            if got.get('sha256') != spec['sha256']:
                self.skipTest('source %s is not the pinned revision this fixture binds'
                              % name)
        cfg = json.loads((lab_common.HERE / 'config.json').read_text())
        tasks = lab_data.build_candidate_tasks(lab_data.load_raw(src))
        exc = lab_data.prospective_exclusions(tasks, cfg)
        excl = {e['uid'] for e in exc}
        surv = [t for t in tasks if t['uid'] not in excl]
        sv = collections.Counter(t['stratum'] for t in surv)
        self.assertEqual(len(tasks), self.EXPECTED['candidates'])
        self.assertEqual(len(exc), self.EXPECTED['exclusions'])
        self.assertEqual(len(surv), self.EXPECTED['survivors'])
        self.assertEqual(sv['S1'], self.EXPECTED['n_S1'])
        self.assertEqual(sv['S2'], self.EXPECTED['n_S2'])
        self.assertEqual(sv['S1'] // 2 + sv['S2'] // 2,
                         self.EXPECTED['n_pairs_ceiling'])


class AttemptLedgerRetentionTests(unittest.TestCase):
    """D1 closure fixture (root 2026-09-21 19:29): save / reload / reconstruct.

    Root: "Save/reload/digest reconstruction with a stub closes that retention
    check without a model run."  No model, no server, no sandbox: a STUB verifier
    supplies the payloads, the sweep retains them through the production sink, the
    ledger is reloaded FROM DISK, and the exclusion digest is recomputed from the
    reloaded records alone.
    """

    def _stub_verify_module(self, payloads):
        class _Stub:
            def __init__(self, seq):
                self.seq = list(seq)
                self.calls = 0

            def verify(self, task, code, **kw):
                out = self.seq[min(self.calls, len(self.seq) - 1)]
                self.calls += 1
                return out
        return _Stub(payloads)

    def _payload(self, success, sentinel, timed_out, secs, out='', err=''):
        return {'success': success, 'sentinel_seen': sentinel, 'timed_out': timed_out,
                'entry_point_defined': True, 'sandbox_flag': False,
                'verify_seconds': secs,
                'run': {'passed': success, 'returncode': 0 if success else 1,
                        'stdout_tail': out, 'stderr': err, 'timed_out': timed_out}}

    def test_digest_reconstructs_from_the_reloaded_ledger(self):
        tmp = Path(tempfile.mkdtemp(prefix='ledger_'))
        try:
            ledger = lab_data.AttemptLedger(tmp / 'attempts.jsonl')
            failing = self._payload(False, False, False, 0.2,
                                    out='partial', err='AssertionError: boom')
            stub = self._stub_verify_module([failing])
            task = {'uid': 'mbpp_full/1', 'benchmark': 'mbpp_full', 'stratum': 'S2',
                    'prompt': 'p', 'entry_point': 'f',
                    'reference': 'def f():\n    return 1\n',
                    'test_imports': [], 'test_list': [], 'challenge_test_list': [],
                    'test': ''}
            cfg = {'sandbox': {'timeout_s': 10.0, 'cpu_s': 10,
                               'output_cap_bytes': 65536,
                               'execution_lock_path': str(tmp / 'lock')},
                   'execution': {'max_lock_wait_s': 5}}
            with mock.patch.object(lab_data, '_pilot_verify', lambda: stub):
                exclusions = lab_data.sweep_references([task], cfg,
                                                       on_attempt=ledger.append)
            self.assertEqual(len(exclusions), 1)
            self.assertEqual(exclusions[0]['reason'], 'reference_fails_verify')

            # RELOAD FROM DISK -- not from the in-memory objects.
            reloaded = lab_data.AttemptLedger(tmp / 'attempts.jsonl').attempts_for(
                'mbpp_full/1')
            self.assertTrue(reloaded, 'the ledger retained nothing')
            self.assertEqual(lab_data.reconstruct_detail_sha256(reloaded),
                             exclusions[0]['detail_sha256'],
                             'the digest did not reconstruct from the reloaded '
                             'records -- the preimage is still effectively lost')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_failing_sink_stops_preparation(self):
        """Root: 'loss/failure of the sink must stop preparation rather than
        silently continue.'"""
        tmp = Path(tempfile.mkdtemp(prefix='ledger_'))
        try:
            def broken_sink(_record):
                raise OSError('ledger device full')
            stub = self._stub_verify_module([self._payload(True, True, False, 0.1)])
            task = {'uid': 'x/1', 'benchmark': 'mbpp_full', 'stratum': 'S2',
                    'prompt': 'p', 'entry_point': 'f',
                    'reference': 'def f():\n    return 1\n',
                    'test_imports': [], 'test_list': [], 'challenge_test_list': [],
                    'test': ''}
            cfg = {'sandbox': {'execution_lock_path': str(tmp / 'lock')},
                   'execution': {'max_lock_wait_s': 5}}
            with mock.patch.object(lab_data, '_pilot_verify', lambda: stub):
                with self.assertRaises(OSError):
                    lab_data.sweep_references([task], cfg, on_attempt=broken_sink)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_clean_exit_without_the_sentinel_is_not_a_pass(self):
        """Root: 'A clean process exit is not a verification sentinel.'"""
        rec = lab_data.attempt_record('u', 0, self._payload(False, False, False, 0.2))
        rec['clean_exit'] = True
        self.assertFalse(rec['sentinel_seen'])
        self.assertEqual(lab_data.classify_attempt(rec, 2.5), 'reference_fails_verify')


class PreparationWiringTests(unittest.TestCase):
    """Root 2026-09-21 20:05: connect the ACTUAL preparation entry point.

    "A stubbed driver-level call can establish wiring without running task
    references."  These drive `lab_prepare.run_reference_sweep` with a stub sweep
    -- no model, no server, no sandbox, no task reference executed.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='prep_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _payload(self, success=False, sentinel=False, out='o', err='e'):
        return {'success': success, 'sentinel_seen': sentinel, 'timed_out': False,
                'entry_point_defined': True, 'sandbox_flag': False,
                'verify_seconds': 0.2,
                'run': {'passed': success, 'returncode': 0 if success else 1,
                        'stdout_tail': out, 'stderr': err, 'timed_out': False}}

    def _stub_sweep(self, uid='t/1'):
        """A sweep that emits one attempt through the sink and one exclusion."""
        def sweep(tasks, cfg, *, on_progress=None, on_attempt=None):
            rec = lab_data.attempt_record(uid, 0, self._payload())
            if on_attempt is not None:
                on_attempt(rec)
            return [lab_data._exclusion(uid, 'reference_fails_verify',
                                        lab_data.detail_from_attempts([rec]))]
        return sweep

    def test_refuses_without_a_load_observer(self):
        """An unloaded sweep must not be reachable through the entry point."""
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            lab_prepare.run_reference_sweep(
                [], {}, ledger_path=self.tmp / 'l.jsonl',
                sweep_fn=self._stub_sweep())
        self.assertIn('rule 4', str(ctx.exception))

    def test_wires_the_ledger_and_reconstructs_every_digest(self):
        res = lab_prepare.run_reference_sweep(
            [], {}, ledger_path=self.tmp / 'l.jsonl', require_load=False,
            sweep_fn=self._stub_sweep())
        self.assertTrue(res['receipt']['completed'])
        self.assertEqual(res['receipt']['records_retained'], 1)
        self.assertTrue(res['receipt']['all_digests_reconstruct_from_ledger'])
        # and the ledger really is on disk, independently readable
        self.assertEqual(len(lab_data.AttemptLedger(self.tmp / 'l.jsonl').load()), 1)

    def test_a_failed_durable_append_stops_the_entry_point(self):
        def boom(fd, data):
            raise OSError('device full')
        with mock.patch.object(os, 'write', boom):
            with self.assertRaises(lab_prepare.PreparationRefused):
                lab_prepare.run_reference_sweep(
                    [], {}, ledger_path=self.tmp / 'l.jsonl', require_load=False,
                    sweep_fn=self._stub_sweep())

    def test_refuses_to_continue_onto_an_unresolved_malformed_tail(self):
        p = self.tmp / 'l.jsonl'
        p.write_bytes(b'{"uid":"a"}\n{"uid":"trunc')       # failure evidence
        with self.assertRaises(lab_prepare.PreparationRefused):
            lab_prepare.run_reference_sweep(
                [], {}, ledger_path=p, require_load=False,
                sweep_fn=self._stub_sweep())

    def test_load_coverage_is_recorded_beside_each_attempt(self):
        def observer():
            return {'window_id': 'w1', 'active': True, 'resolution_ms': 50}
        res = lab_prepare.run_reference_sweep(
            [], {}, ledger_path=self.tmp / 'l.jsonl', load_observer=observer,
            sweep_fn=self._stub_sweep())
        self.assertEqual(len(res['coverage']), 1)
        self.assertEqual(res['coverage'][0]['observation']['window_id'], 'w1')
        stored = lab_data.AttemptLedger(self.tmp / 'l.jsonl').load()[0]
        self.assertIn('load_coverage', stored)


class LedgerShortWriteTests(unittest.TestCase):
    """Root 2026-09-21 20:05, reproduced defect: short writes silently succeeded."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='sw_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.rec = lab_data.attempt_record('u', 0, {
            'success': True, 'sentinel_seen': True, 'timed_out': False,
            'verify_seconds': 0.1,
            'run': {'passed': True, 'returncode': 0, 'stdout_tail': 'x',
                    'stderr': '', 'timed_out': False}})

    def test_a_positive_short_write_completes_through_the_loop(self):
        real, calls = os.write, {'n': 0}

        def half_once(fd, data):
            calls['n'] += 1
            return real(fd, data[:max(1, len(data) // 2)]) if calls['n'] == 1 \
                else real(fd, data)
        led = lab_data.AttemptLedger(self.tmp / 'a.jsonl')
        with mock.patch.object(os, 'write', half_once):
            led.append(self.rec)
        self.assertEqual(led.count, 1)
        self.assertTrue((self.tmp / 'a.jsonl').read_bytes().endswith(b'\n'))
        self.assertEqual(len(lab_data.AttemptLedger(self.tmp / 'a.jsonl').load()), 1)

    def test_a_non_progressing_write_fails_visibly_and_is_not_counted(self):
        led = lab_data.AttemptLedger(self.tmp / 'a.jsonl')
        with mock.patch.object(os, 'write', lambda fd, data: 0):
            with self.assertRaises(OSError):
                led.append(self.rec)
        self.assertEqual(led.count, 0, 'a failed append must not be counted')

    def test_load_refuses_a_truncated_tail_instead_of_skipping_it(self):
        p = self.tmp / 'a.jsonl'
        p.write_bytes(b'{"uid":"a"}\n{"uid":"trunc')
        with self.assertRaises(ValueError):
            lab_data.AttemptLedger(p).load()
        self.assertTrue(p.exists(), 'the incomplete tail must be retained as evidence')
