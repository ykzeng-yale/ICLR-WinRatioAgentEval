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
import lab_injected_decision                             # noqa: E402
import lab_lifecycle                                     # noqa: E402
import lab_load                                          # noqa: E402
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
                           # protocol 7.5 item 4 measures over 10 s; an offline
                           # suite sets a short window EXPLICITLY and preflight
                           # records it as below_protocol_window
                           'clock_window_s': 0.01,
                           # and DECLARE that this is not a production preflight
                           'preflight_mode': 'offline_fixture',
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
            # Root 2026-09-21 22:56: "Update intended test fixtures/callers ...
            # do not retain silent fallback merely to preserve a misleading
            # fixture label." The production sweep supplies the NAMED v2
            # endpoints, so the fixture does too.
            rec = lab_data.attempt_record(
                uid, 0, self._payload(),
                verification_started_monotonic=100.0,
                verification_ended_monotonic=100.5,
                verification_started_posix_ns=100_000_000_000,
                verification_ended_posix_ns=100_500_000_000,
                boot_id='boot:aa', host_id='host:bb',
                boot_source='sysctl kern.bootsessionuuid',
                host_source='platform.node')
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
            enforce_tmpdir=False, sweep_fn=self._stub_sweep())
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
            # A VALID observation must COVER THE ATTEMPT'S INTERVAL, not merely
            # carry three fields. Root 2026-09-21 21:17: "Required load coverage
            # is still metadata presence, not interval validation ... A
            # post-attempt result containing those three fields passes." It no
            # longer does; active_windows must span the attempt on one clock,
            # with the stated resolution charged against the claim.
            return {'window_id': 'w1', 'active': True, 'resolution_ms': 50,
                    'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
                    'clock': 'clock_gettime(CLOCK_MONOTONIC)',
                    'boot_id': 'boot:aa', 'host_id': 'host:bb',
                    'concurrency_required': 2,
                    'active_windows': [
                        {'start': 99.0, 'end': 101.0, 'identity': 'slot0/req_a'},
                        {'start': 99.0, 'end': 101.0, 'identity': 'slot1/req_b'}]}
        res = lab_prepare.run_reference_sweep(
            [], {}, ledger_path=self.tmp / 'l.jsonl', load_observer=observer,
            enforce_tmpdir=False, sweep_fn=self._stub_sweep())
        self.assertEqual(len(res['coverage']), 1)
        self.assertEqual(res['coverage'][0]['observation']['window_id'], 'w1')
        # The RAW attempt is stored first and UNMODIFIED; coverage is a separate
        # ledger entry. Embedding coverage in the attempt record was the earlier
        # shape, and it is exactly what let an observer failure lose the raw
        # attempt (root 2026-09-21 20:43).
        entries = lab_data.AttemptLedger(self.tmp / 'l.jsonl').load()
        attempts = [e for e in entries
                    if e.get('schema') == lab_data.ATTEMPT_RECORD_SCHEMA]
        covers = [e for e in entries
                  if e.get('schema') == 'live_ab/load_coverage-v1']
        self.assertEqual(len(attempts), 1)
        self.assertNotIn('load_coverage', attempts[0],
                         'the raw attempt must be stored unmodified')
        self.assertEqual(len(covers), 1)
        self.assertEqual(covers[0]['observation']['window_id'], 'w1')


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


class SourceAcquisitionTests(unittest.TestCase):
    """D4/D5 guards, exercised on the DEFAULT integrity-enabled path.

    Root 2026-09-22 00:34: "Do NOT deposit 860 KB of actual benchmark bytes merely
    to test refusal. Use tiny synthetic files in a temporary test directory and
    patch the source specification/expected SHA256 values within the test to those
    fixture bytes. Call acquisition with verification enabled (the production
    default)."  My earlier fixtures passed verify_required_bytes=False, which did
    not exercise the integrity half at all; that keyword is now gone from the API.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='acq_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # two tiny REQUIRED sources and one absent OPTIONAL source
        self.specs = {}
        for name, filename, required, stratum in (
                ('tiny_a', 'tiny_a.txt', True, 'S1'),
                ('tiny_b', 'tiny_b.txt', True, 'S1'),
                ('tiny_opt', 'tiny_opt.txt', False, 'S2')):
            data = ('%s-fixture-bytes' % name).encode()
            spec = {'filename': filename, 'url': 'file:///dev/null',
                    'revision': 'rev', 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'records': 1, 'stratum': stratum, 'required': required,
                    'aliases': (filename,)}
            self.specs[name] = spec
            if required:                      # optional one deliberately absent
                (self.tmp / filename).write_bytes(data)
        self._patch = mock.patch.object(lab_data, 'SOURCES', self.specs)
        self._patch.start(); self.addCleanup(self._patch.stop)

    def _manifest(self, mode):
        srcs = {}
        for name, spec in self.specs.items():
            present = (self.tmp / spec['filename']).is_file()
            srcs[name] = ({'present': True, 'filename': spec['filename'],
                           'bytes': spec['bytes'], 'sha256': spec['sha256'],
                           'revision': spec['revision'], 'records': spec['records'],
                           'stratum': spec['stratum'], 'from_cache': True,
                           'origin': '<SOMEWHERE>/' + spec['filename']}
                          if present else
                          {'present': False, 'reason': 'absent_offline'})
        return {'dest': '<W>', 'offline': True, 'sources': srcs, 'roster_mode': mode}

    # -- accepted controls, on the DEFAULT path ------------------------------
    def test_fresh_S1_with_intact_required_bytes_is_accepted(self):
        res = lab_prepare.acquire_sources(
            self.tmp, fetch_fn=lambda d, **k: self._manifest('S1'))
        self.assertEqual(res['roster_mode'], 'S1')

    def test_repeat_acquisition_preserves_the_original_manifest(self):
        (self.tmp / 'sources.json').write_text(json.dumps(self._manifest('S1')), 'utf-8')
        before = (self.tmp / 'sources.json').read_bytes()
        res = lab_prepare.acquire_sources(
            self.tmp, fetch_fn=lambda d, **k: self._manifest('S1'))
        self.assertTrue(res['reused_existing_manifest'])
        self.assertEqual((self.tmp / 'sources.json').read_bytes(), before)

    # -- the two counterexamples root named, integrity ENABLED ---------------
    def test_explicit_EXT_refuses_a_prior_S1_manifest(self):
        (self.tmp / 'sources.json').write_text(json.dumps(self._manifest('S1')), 'utf-8')
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            lab_prepare.acquire_sources(self.tmp, expect_mode='EXT',
                                        fetch_fn=lambda d, **k: self._manifest('S1'))
        self.assertIn('EXT', str(ctx.exception))

    def test_corrupted_required_source_refuses_under_S1(self):
        (self.tmp / 'tiny_a.txt').write_bytes(b'corrupted')
        with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
            lab_prepare.acquire_sources(self.tmp,
                                        fetch_fn=lambda d, **k: self._manifest('S1'))
        self.assertIn('pinned sha256', str(ctx.exception))

    def test_missing_required_source_refuses_under_S1(self):
        (self.tmp / 'tiny_b.txt').unlink()
        with self.assertRaises(lab_prepare.PreparationRefused):
            lab_prepare.acquire_sources(self.tmp,
                                        fetch_fn=lambda d, **k: self._manifest('S1'))

    def test_production_api_exposes_no_integrity_bypass(self):
        """Root: do not allow a production entry point to clear required-byte
        validation."""
        import inspect
        params = inspect.signature(lab_prepare.acquire_sources).parameters
        self.assertNotIn('verify_required_bytes', params)

    def test_content_identity_excludes_the_origin_field(self):
        a = self._manifest('S1')
        b = json.loads(json.dumps(a))
        b['sources']['tiny_a']['origin'] = '<ELSEWHERE>/tiny_a.txt'
        b['sources']['tiny_a']['from_cache'] = False
        self.assertEqual(lab_prepare._content_key(a), lab_prepare._content_key(b))

    def test_accesses_are_recorded_separately_from_acquisition(self):
        lab_prepare.acquire_sources(self.tmp,
                                    fetch_fn=lambda d, **k: self._manifest('S1'))
        log = self.tmp / lab_prepare.ACCESS_LOG_NAME
        self.assertTrue(log.is_file())
        self.assertEqual(lab_data.AttemptLedger(log).load()[0]['kind'], 'acquire')


class TmpdirEnforcementTests(unittest.TestCase):
    """Root 2026-09-21 20:43: "The new assertion currently has no callers ...
    Wire it and show valid/mismatched startup fixtures through the real entry
    points."  These drive the REAL entry point, not the helper."""

    def setUp(self):
        self.cfg = json.loads((lab_common.HERE / 'config.json').read_text('utf-8'))

    def test_mismatched_startup_is_refused_at_the_real_entry_point(self):
        tmp = Path(tempfile.mkdtemp(prefix='tmpd_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with mock.patch.object(tempfile, 'gettempdir', lambda: '/private/tmp/WRONG'):
            with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
                lab_prepare.run_reference_sweep(
                    [], self.cfg, ledger_path=tmp / 'l.jsonl', require_load=False,
                    sweep_fn=lambda *a, **k: [])
        self.assertIn('labsbx', str(ctx.exception))

    def test_valid_startup_passes_the_check(self):
        with mock.patch.object(tempfile, 'gettempdir', lambda: '/private/tmp/labsbx'):
            got = lab_prepare.assert_prescribed_tmpdir(self.cfg)
        self.assertEqual(got['sandbox_base_dir'], '/private/tmp/labsbx/ls_sbx')

    def test_the_check_compares_the_RESOLVED_directory_not_the_env_string(self):
        """Root: "Compare the resolved effective temp directory, including
        tempfile caching, not only the environment string." """
        import os as _os
        with mock.patch.dict(_os.environ, {'TMPDIR': '/private/tmp/labsbx'}):
            with mock.patch.object(tempfile, 'gettempdir', lambda: '/private/tmp/OTHER'):
                with self.assertRaises(lab_prepare.PreparationRefused):
                    lab_prepare.assert_prescribed_tmpdir(self.cfg)


class CoverageSchemaDomainMatrixTests(unittest.TestCase):
    """The presence/version/domain matrix root suggested (2026-09-21 22:56).

    Closes together: explicit-null uncertainty, schema-directed parsing, refusal
    of alias rescue for a malformed v2 record, and the explicit legacy audit route.
    """

    # Root's binding decision of 2026-09-22 02:49 replaced the evidence this
    # function may certify from: two DISTINCT server-acknowledged decoding
    # lifetimes occupied throughout the interval, not union coverage of one.
    # These version/domain tests are about the ATTEMPT record's schema, so the
    # observation is now the minimal valid lifecycle observation.
    OBS = {'active': True, 'window_id': 'w', 'endpoint_error_s': 0.0,
           'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
           'clock': 'time.monotonic', 'concurrency_required': 2,
           'boot_id': 'boot:aa', 'host_id': 'host:bb',
           'active_windows': [{'start': 99.0, 'end': 101.0, 'identity': 'slot0/req_a'},
                              {'start': 99.0, 'end': 101.0, 'identity': 'slot1/req_b'}]}

    def _v(self, record, **kw):
        # v2/v1 are readable only through the explicit historical audit route
        # since root's 2026-09-22 04:02 decision; this class is about the
        # SCHEMA/DOMAIN matrix, so it takes that route by default.
        kw.setdefault('allow_legacy_audit', True)
        return lab_prepare._coverage_verdict(self.OBS, record, **kw)

    # -- version branch ------------------------------------------------------
    def test_v2_with_valid_named_endpoints_is_certified_as_v2(self):
        v = self._v({'interval_schema': lab_prepare.INTERVAL_SCHEMA_V2,
                     'verification_started_monotonic': 100.0,
                     'verification_ended_monotonic': 100.5})
        self.assertTrue(v['valid'])
        self.assertEqual(v['interval_version'], lab_prepare.INTERVAL_SCHEMA_V2)
        self.assertIn('verifier call', v['certified_interval'])

    def test_malformed_v2_is_NOT_rescued_by_valid_legacy_aliases(self):
        """The exact defect: a NaN named start plus good aliases returned valid."""
        for bad in (float('nan'), None, 'invalid'):
            with self.subTest(bad=bad):
                v = self._v({'interval_schema': lab_prepare.INTERVAL_SCHEMA_V2,
                             'verification_started_monotonic': bad,
                             'verification_ended_monotonic': 100.5,
                             'started_monotonic': 100.0, 'ended_monotonic': 100.5})
                self.assertFalse(v['valid'])
                self.assertIn('may not rescue', v['reason'])

    def test_v2_missing_named_endpoints_refuses_despite_aliases(self):
        v = self._v({'interval_schema': lab_prepare.INTERVAL_SCHEMA_V2,
                     'started_monotonic': 100.0, 'ended_monotonic': 100.5})
        self.assertFalse(v['valid'])

    def test_legacy_refuses_in_production_and_is_readable_only_by_audit(self):
        # v1 in production: still refused, and since 2026-09-22 so is v2.
        rec = {'interval_schema': lab_prepare.INTERVAL_SCHEMA_V1,
               'started_monotonic': 100.0, 'ended_monotonic': 100.5}
        self.assertFalse(self._v(rec, allow_legacy_audit=False)['valid'])
        audit = self._v(rec, allow_legacy_audit=True)
        self.assertTrue(audit['valid'])
        self.assertEqual(audit['interval_version'], lab_prepare.INTERVAL_SCHEMA_V1)
        self.assertIn('wider span', audit['certified_interval'],
                      'the audit route must NAME the interval it certified')

    def test_unknown_schema_is_a_schema_error_not_a_guess(self):
        v = self._v({'interval_schema': 'live_ab/attempt_interval-v9',
                     'started_monotonic': 100.0, 'ended_monotonic': 100.5})
        self.assertFalse(v['valid'])
        self.assertIn('unsupported interval schema', v['reason'])

    # -- uncertainty presence/domain ----------------------------------------
    def _v2(self, **extra):
        return {'interval_schema': lab_prepare.INTERVAL_SCHEMA_V2,
                'verification_started_monotonic': 100.0,
                'verification_ended_monotonic': 100.5, **extra}

    def test_absent_uncertainty_defaults_to_zero(self):
        self.assertTrue(self._v(self._v2())['valid'])

    def test_explicit_null_uncertainty_REFUSES(self):
        """Root: 'explicit null is unknown and must refuse, not be treated as absent.'"""
        v = self._v(self._v2(endpoint_error_s=None))
        self.assertFalse(v['valid'])
        self.assertIn('not a finite number', v['reason'])

    def test_explicit_malformed_uncertainty_refuses(self):
        for bad in (float('nan'), float('inf'), 'invalid'):
            with self.subTest(bad=bad):
                self.assertFalse(self._v(self._v2(endpoint_error_s=bad))['valid'])

    def test_zero_and_positive_finite_uncertainty_remain_valid(self):
        self.assertTrue(self._v(self._v2(endpoint_error_s=0.0))['valid'])
        # a large positive bound EXPANDS the verifier interval, so it stops fitting
        self.assertFalse(self._v(self._v2(endpoint_error_s=2.0))['valid'])

    # -- the constructor must label honestly ---------------------------------
    def test_constructor_labels_v1_when_only_legacy_endpoints_supplied(self):
        payload = {'success': True, 'sentinel_seen': True, 'timed_out': False,
                   'verify_seconds': 0.1,
                   'run': {'passed': True, 'returncode': 0, 'stdout_tail': '',
                           'stderr': '', 'timed_out': False}}
        legacy = lab_data.attempt_record('u', 0, payload,
                                         started_monotonic=1.0, ended_monotonic=2.0)
        self.assertEqual(legacy['interval_schema'], lab_prepare.INTERVAL_SCHEMA_V1,
                         'a record built from legacy endpoints must not claim v2')
        modern = lab_data.attempt_record('u', 0, payload,
                                         verification_started_monotonic=1.0,
                                         verification_ended_monotonic=2.0)
        self.assertEqual(modern['interval_schema'], lab_prepare.INTERVAL_SCHEMA_V2)


class WorkerStartupEnforcementTests(unittest.TestCase):
    """Root 2026-09-22 01:07: BOTH supervisor-launch and worker-startup checks.

    "Offline stubs should show invalid launch refusal and invalid
    direct/restarted worker refusal before dispatch; valid prescribed setup
    passes."
    """

    def setUp(self):
        self.cfg = json.loads((lab_common.HERE / 'config.json').read_text('utf-8'))

    # -- supervisor side: refuse BEFORE any worker exists --------------------
    def test_invalid_launch_is_refused_before_any_worker(self):
        bad = json.loads(json.dumps(self.cfg))
        bad['sandbox']['tmpdir'] = '<TMP>/wrong'
        with self.assertRaises(lab_prepare.PreparationRefused):
            lab_prepare.launch_environment(bad)

    def test_valid_launch_environment_carries_the_prescribed_tmpdir(self):
        # SELF-CONTAINED (root 2026-09-22 01:44): the first version silently
        # depended on /private/tmp/labsbx existing on the running host. It does
        # not on an independent reviewer's machine, where the helper correctly
        # refused -- a test setup dependency, not a production defect. The
        # prescribed-directory condition is now stubbed explicitly.
        with mock.patch.object(Path, 'is_dir', lambda self: True):
            env = lab_prepare.launch_environment(self.cfg, base_env={})
        self.assertEqual(env['TMPDIR'], '/private/tmp/labsbx')

    # -- worker side: startup AND restart, before dispatch -------------------
    def test_invalid_worker_is_refused_at_startup_and_after_restart(self):
        with mock.patch.object(tempfile, 'gettempdir',
                               lambda: '/private/tmp/WRONG'):
            for phase in ('startup', 'restart'):
                with self.subTest(phase=phase):
                    with self.assertRaises(lab_prepare.PreparationRefused):
                        lab_prepare.assert_worker_startup(self.cfg, phase=phase)

    def test_valid_prescribed_worker_setup_passes(self):
        import os as _os
        # BOTH must agree: the env string and Python's resolved directory. The
        # first version of this test patched only gettempdir and the check
        # correctly refused, because the ambient TMPDIR still disagreed.
        with mock.patch.object(tempfile, 'gettempdir',
                               lambda: '/private/tmp/labsbx'):
            with mock.patch.dict(_os.environ, {'TMPDIR': '/private/tmp/labsbx'}):
                got = lab_prepare.assert_worker_startup(self.cfg)
        self.assertEqual(got['sandbox_base_dir'], '/private/tmp/labsbx/ls_sbx')
        self.assertTrue(got['checked_before_dispatch'])

    def test_resolved_directory_is_authoritative_over_the_env_string(self):
        """Root: 'an environment string alone does not establish Python's
        resolved/cached temporary directory. Do not change a running process's
        cache to force a pass.'"""
        import os as _os
        with mock.patch.object(tempfile, 'gettempdir',
                               lambda: '/private/tmp/labsbx'):
            with mock.patch.dict(_os.environ, {'TMPDIR': '/private/tmp/OTHER'}):
                with self.assertRaises(lab_prepare.PreparationRefused) as ctx:
                    lab_prepare.assert_worker_startup(self.cfg)
        self.assertIn('resolved', str(ctx.exception).lower())

    def test_a_refusal_diagnostic_cannot_itself_raise(self):
        """An untokenizable path must be redacted, not turned into a traceback."""
        self.assertEqual(lab_prepare._safe_token('/nowhere/at/all'),
                         '<UNTOKENIZABLE-PATH-REDACTED>')


class CombinedFixtureControlFlowTests(unittest.TestCase):
    """Root's two narrow fixture corrections (2026-09-22 01:07)."""

    def test_preexisting_scan_happens_before_the_holder_is_launched(self):
        """A fast valid holder must not be misclassified as pre-existing."""
        import inspect
        import lab_combined_fixture
        src = inspect.getsource(lab_combined_fixture.run_fixture)
        self.assertLess(src.index('preexisting = list('),
                        src.index('holder = subprocess.Popen'),
                        'the nonce scan must precede holder launch')

    def test_contender_is_not_launched_when_readiness_is_false(self):
        import inspect
        import lab_combined_fixture
        src = inspect.getsource(lab_combined_fixture.run_fixture)
        self.assertLess(src.index('if not sandbox_active_observed'),
                        src.index('c = subprocess.run'),
                        'readiness must gate the contender launch')


class InjectedDecisionRefusalTests(unittest.TestCase):
    """Root's STRONG-FORM requirement (2026-09-21 20:43 and 23:29).

    "Exercise the real production configuration/startup path with the injection
    flag/hook requested, assert explicit refusal before any dispatch or model
    request, and include a valid production configuration control."

    The weak form would assert the fixture "is not wired in today", proving only
    that nobody wired it. These drive the production path with activation
    requested.
    """

    def setUp(self):
        self.cfg = json.loads((lab_common.HERE / 'config.json').read_text('utf-8'))

    # -- the strong form ----------------------------------------------------
    def test_production_refuses_a_configuration_requesting_injection(self):
        bad = dict(self.cfg)
        bad[lab_injected_decision.ACTIVATION_KEY] = True
        with self.assertRaises(lab_injected_decision.FixtureActivationRefused):
            lab_injected_decision.assert_no_test_fixture_active(bad)

    def test_the_real_sweep_entry_point_refuses_before_any_dispatch(self):
        """Not the helper -- the actual production entry point."""
        tmp = Path(tempfile.mkdtemp(prefix='inj_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        bad = json.loads(json.dumps(self.cfg))
        bad[lab_injected_decision.ACTIVATION_KEY] = True
        dispatched = []
        with mock.patch.object(tempfile, 'gettempdir', lambda: '/private/tmp/labsbx'):
            with self.assertRaises(Exception) as ctx:
                lab_prepare.run_reference_sweep(
                    [], bad, ledger_path=tmp / 'l.jsonl', require_load=False,
                    sweep_fn=lambda *a, **k: dispatched.append(1) or [])
        self.assertIn('injected_decision_fixture', str(ctx.exception))
        self.assertEqual(dispatched, [], 'refusal must precede any dispatch')

    # -- the valid production control root required -------------------------
    def test_valid_production_configuration_passes(self):
        got = lab_injected_decision.assert_no_test_fixture_active(self.cfg)
        self.assertFalse(got['injection_requested'])
        self.assertTrue(got['checked_before_dispatch'])

    # -- reachable ONLY through the explicit test route ---------------------
    def test_fixture_cannot_be_armed_without_the_test_token(self):
        with self.assertRaises(lab_injected_decision.FixtureActivationRefused):
            lab_injected_decision.arm(self.cfg)

    def test_the_token_alone_cannot_arm_against_a_trial_configuration(self):
        """A valid token must not turn a real trial into an injected one."""
        with self.assertRaises(lab_injected_decision.FixtureActivationRefused):
            lab_injected_decision.arm(self.cfg,
                                      lab_injected_decision.TEST_ROUTE_TOKEN)

    def test_the_test_route_works_for_a_rehearsal_only_configuration(self):
        got = lab_injected_decision.arm({'rehearsal_only': True},
                                        lab_injected_decision.TEST_ROUTE_TOKEN)
        self.assertTrue(got['armed'])
        self.assertFalse(got['produces_observations'])
        self.assertFalse(got['touches_monitor_outputs'])

    # -- pinning ------------------------------------------------------------
    def test_the_fixture_is_pinned_in_the_harness_set(self):
        """Root: it 'may live inside the owned harness directory and MUST be pinned'."""
        self.assertIn('lab_injected_decision.py', lab_common.HARNESS_FILES)

    def test_an_injected_decision_is_labelled_as_not_an_observation(self):
        ev = lab_injected_decision.inject_decision('DEPLOY')
        self.assertTrue(ev['synthetic'])
        self.assertFalse(ev['is_observation'])


class ContinuousLoadObserverTests(unittest.TestCase):
    """The observer of protocol 3.2 rule 4, and the negative controls that matter.

    Until `lab_load`, `load_observer` was a parameter with no implementation: the
    sweep refused when it was absent and validated whatever it returned when it
    was present, and nothing produced one. These tests fix what an observation
    means, and -- more importantly -- what it must REFUSE to mean.
    """

    GAP = 0.5

    def _probe(self, lateness=0.002, n=lab_load.MIN_JITTER_SAMPLES):
        """A probe with real samples and no thread: the tests never sleep."""
        p = lab_load.JitterProbe()
        for _ in range(n):
            p.observe_sample(lateness)
        return p

    def _observer(self, script, **kw):
        kw.setdefault('max_interior_gap_s', self.GAP)
        kw.setdefault('jitter', self._probe())
        # The scripted arrivals live on their own timeline, so 'now' must too --
        # otherwise the staleness rule (correctly) reports that traffic stopped
        # five million seconds ago.
        newest = max((t for _, t in script), default=0.0)
        kw.setdefault('clock', lambda: newest)
        return lab_load.ContinuousLoadObserver(lab_load.ScriptedLoad(script), **kw)

    @staticmethod
    def _dense(gid, t0, t1, step=0.05):
        t, out = t0, []
        while t <= t1 + 1e-9:
            out.append((gid, round(t, 6)))
            t += step
        return out

    def _attempt(self, start, end):
        return {'interval_schema': lab_prepare.INTERVAL_SCHEMA_V3,
                'verification_started_monotonic': start,
                'verification_ended_monotonic': end,
                'verification_started_posix_ns': int(start * 1e9),
                'verification_ended_posix_ns': int(end * 1e9),
                'clock_domain_posix': 'clock_gettime(CLOCK_MONOTONIC)',
                'boot_id': 'boot:aa', 'host_id': 'host:bb',
                'boot_source': 'sysctl kern.bootsessionuuid',
                'host_source': 'platform.node'}

    # -- the pure core -----------------------------------------------------
    def test_a_dense_series_is_one_window(self):
        w = lab_load.windows_from_arrivals(self._dense('g0', 100.0, 101.0),
                                           max_interior_gap_s=self.GAP)
        self.assertEqual(len(w), 1)
        self.assertAlmostEqual(w[0]['start'], 100.0)
        self.assertAlmostEqual(w[0]['end'], 101.0)
        self.assertAlmostEqual(w[0]['max_interior_gap_s'], 0.05, places=6)

    def test_an_interior_gap_splits_the_window_rather_than_being_averaged(self):
        """The whole point. A gap is unobserved time, not a small imperfection."""
        series = self._dense('g0', 100.0, 100.3) + self._dense('g0', 101.5, 102.0)
        w = lab_load.windows_from_arrivals(series, max_interior_gap_s=self.GAP)
        self.assertEqual(len(w), 2)
        self.assertAlmostEqual(w[0]['end'], 100.3)
        self.assertAlmostEqual(w[1]['start'], 101.5)
        for win in w:
            self.assertLessEqual(win['max_interior_gap_s'], self.GAP)

    def test_two_concurrent_generations_interleave_without_destroying_the_windows(self):
        """The trial runs two workers, so the load regime is two generations at
        once and their arrivals interleave. An earlier rule here split at every
        change of generation id -- which ended every window after ONE arrival and
        reported NO ACTIVE LOAD at the moment the server was busiest, silently
        and in the safe-looking direction. Partitioning by generation first is
        what makes the observer usable under the regime it exists to observe."""
        series = sorted(self._dense('g0', 100.0, 101.0, step=0.1)
                        + self._dense('g1', 100.05, 101.05, step=0.1),
                        key=lambda x: x[1])
        self.assertNotEqual([g for g, _ in series[:4]], ['g0'] * 4)   # interleaved
        w = lab_load.windows_from_arrivals(series, max_interior_gap_s=self.GAP)
        self.assertEqual(len(w), 2)
        self.assertEqual({x['generation_id'] for x in w}, {'g0', 'g1'})
        for win in w:
            self.assertGreaterEqual(win['arrivals'], 10)

    def test_a_gap_inside_one_generation_splits_it_while_the_other_is_untouched(self):
        series = sorted(self._dense('g0', 100.0, 100.2, step=0.05)
                        + self._dense('g0', 101.0, 101.2, step=0.05)
                        + self._dense('g1', 100.0, 101.2, step=0.05),
                        key=lambda x: x[1])
        w = lab_load.windows_from_arrivals(series, max_interior_gap_s=self.GAP)
        self.assertEqual(len([x for x in w if x['generation_id'] == 'g0']), 2)
        self.assertEqual(len([x for x in w if x['generation_id'] == 'g1']), 1)

    def test_a_lone_arrival_is_not_an_interval(self):
        self.assertEqual(
            lab_load.windows_from_arrivals([('g0', 100.0)], max_interior_gap_s=self.GAP),
            [])

    def test_out_of_order_or_nonfinite_stamps_refuse(self):
        for bad in ([('g0', 100.0), ('g0', 99.0)],
                    [('g0', 100.0), ('g0', float('nan'))],
                    [('g0', 100.0), ('g0', float('inf'))]):
            with self.subTest(bad=bad), self.assertRaises(lab_load.LoadRefused):
                lab_load.windows_from_arrivals(bad, max_interior_gap_s=self.GAP)

    def test_a_nonpositive_tolerance_refuses(self):
        for g in (0.0, -1.0, float('nan')):
            with self.subTest(g=g), self.assertRaises(lab_load.LoadRefused):
                lab_load.windows_from_arrivals(self._dense('g0', 100.0, 100.5),
                                               max_interior_gap_s=g)

    # -- the endpoint bound ------------------------------------------------
    def test_an_unmeasured_endpoint_bound_is_not_a_small_one(self):
        obs = self._observer(self._dense('g0', 100.0, 101.0),
                             jitter=self._probe(n=lab_load.MIN_JITTER_SAMPLES - 1))
        with obs:
            got = obs.observe()
        self.assertFalse(got['active'])
        self.assertIn('UNMEASURED', got['reason'])
        self.assertNotIn('endpoint_error_s', got)

    def test_the_bound_is_the_worst_observation_floored(self):
        p = self._probe(lateness=0.001)
        self.assertAlmostEqual(p.bound(floor_s=0.01)['endpoint_error_s'], 0.01)
        p.observe_sample(0.25)
        self.assertAlmostEqual(p.bound(floor_s=0.01)['endpoint_error_s'], 0.25)

    # -- the observation ---------------------------------------------------
    def test_a_dense_arrival_series_is_NOT_certifying_evidence(self):
        """Root's binding decision, 2026-09-22 02:49: client stream arrivals do
        not identify server decoding lifetime, and no tolerance converts them
        into it. The instrument stays; its certification does not."""
        obs = self._observer(self._dense('g0', 99.0, 102.0))
        with obs:
            o = obs.observe()
        self.assertTrue(o['active'])                       # traffic WAS flowing
        self.assertEqual(o['evidence_kind'], 'client_stream_arrivals')
        self.assertFalse(o['certifies_coverage'])
        v = lab_prepare._coverage_verdict(o, self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('server_lifecycle', v['reason'])

    def test_an_interior_gap_still_splits_the_diagnostic_windows(self):
        """The splitting rule remains correct as a DIAGNOSTIC of traffic gaps."""
        obs = self._observer(self._dense('g0', 99.0, 100.1)
                             + self._dense('g0', 100.8, 102.0))
        with obs:
            o = obs.observe()
        self.assertEqual(len(o['active_windows']), 2)
        self.assertLess(o['active_windows'][0]['end'], 100.8)

    # -- the three defects root's independent review named ------------------
    def test_an_unhealthy_source_yields_no_windows(self):
        """Review finding 2: observe() recorded source_healthy and then IGNORED
        it. The reviewer's own witness -- five arrivals 100.0..100.4, 20 jitter
        samples, healthy=False, attempt [100.12, 100.18] -- returned active=True
        and coverage valid. The docstring claimed an enforcement that did not
        exist."""
        class _Sick(lab_load.ScriptedLoad):
            kind = 'scripted_unhealthy'

            def healthy(self):
                return False

        obs = lab_load.ContinuousLoadObserver(
            _Sick([('g0', 100.0), ('g0', 100.1), ('g0', 100.2),
                   ('g0', 100.3), ('g0', 100.4)]),
            max_interior_gap_s=self.GAP, jitter=self._probe(),
            clock=lambda: 100.4)
        with obs:
            o = obs.observe()
        self.assertFalse(o['active'])
        self.assertEqual(o['active_windows'], [])
        self.assertIn('UNHEALTHY', o['reason'])
        self.assertEqual(o['arrivals_seen'], 5)            # evidence RETAINED
        v = lab_prepare._coverage_verdict(o, self._attempt(100.12, 100.18))
        self.assertFalse(v['valid'])

    def test_role_and_usage_chunks_are_not_token_production(self):
        """Review finding 3: every non-DONE data: line counted as an arrival, so
        a two-line response of role metadata plus a usage event produced two
        'arrivals' -- lengthening a window at exactly the two ends where the
        continuity claim is weakest."""
        cases = [
            ('data: {"choices":[{"delta":{"role":"assistant"}}]}', 'role_or_empty_delta', False),
            ('data: {"choices":[{"delta":{"content":"hi"}}]}', 'content', True),
            ('data: {"choices":[],"usage":{"total_tokens":5}}', 'usage_or_metadata', False),
            ('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}', 'finish', False),
            ('data: not json', 'unparsable', False),
            ('data:', 'empty', False),
        ]
        for text, kind, is_token in cases:
            with self.subTest(text=text[:40]):
                self.assertEqual(lab_load.classify_stream_chunk(text), (kind, is_token))

    def test_the_reviewers_two_line_mock_produces_no_arrival(self):
        class _Resp:
            status_code = 200

            def iter_lines(self):
                return [b'data: {"choices":[{"delta":{"role":"assistant"}}]}',
                        b'data: {"choices":[],"usage":{"total_tokens":5}}',
                        b'data: [DONE]']

        class _Session:
            def post(self, *a, **kw):
                return _Resp()

        src = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193',
                                         model='m', prompt='p',
                                         session_factory=_Session)
        got = []
        src._one_generation(_Session(), 'g0', lambda gid, t: got.append((gid, t)))
        self.assertEqual(got, [])
        self.assertEqual(src.event_counts['content_events'], 0)
        self.assertEqual(sum(src.event_counts['nontoken_events'].values()), 2)

    def test_two_sources_do_not_collide_in_generation_identity(self):
        """Review finding 1: generations were named gen_000000 with no per-source
        prefix, so two sources routed into one observer would COLLIDE -- merging
        two concurrent lifetimes into one identity, which is exactly what
        concurrency must count separately."""
        a = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193', model='m',
                                       prompt='p', source_id='srcA')
        b = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193', model='m',
                                       prompt='p', source_id='srcB')
        self.assertNotEqual(a.source_id, b.source_id)
        ids_a, ids_b = [], []
        a._stop.set(); b._stop.set()        # the loop exits before any request
        for src, out in ((a, ids_a), (b, ids_b)):
            out.append('%s/gen_%06d' % (src.source_id, 0))
        self.assertNotEqual(ids_a[0], ids_b[0])
        # and an auto-assigned id is still unique
        c = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193', model='m',
                                       prompt='p')
        d = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193', model='m',
                                       prompt='p')
        self.assertNotEqual(c.source_id, d.source_id)

    # -- the concurrency rule that replaced union coverage ------------------
    def _lifecycle(self, windows, **kw):
        obs = {'active': True, 'window_id': 'lc', 'endpoint_error_s': 0.0,
               'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
               'clock': 'clock_gettime(CLOCK_MONOTONIC)',
               'boot_id': 'boot:aa', 'host_id': 'host:bb',
               'concurrency_required': 2, 'active_windows': windows}
        obs.update(kw)
        return obs

    def test_two_distinct_lifetimes_throughout_the_attempt_certify(self):
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 101.0, 'identity': 'slot0/req_a'},
            {'start': 99.5, 'end': 101.5, 'identity': 'slot1/req_b'}]),
            self._attempt(100.0, 100.5))
        self.assertTrue(v['valid'], v.get('reason'))
        self.assertEqual(v['concurrency_observed_min'], 2)

    def test_union_coverage_by_ONE_lifetime_no_longer_certifies(self):
        """The reviewer's finding 1, and the saved single-generation case that
        expressly passed under the old union walk."""
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 100.4, 'identity': 'slot0/req_a'},
            {'start': 100.3, 'end': 101.5, 'identity': 'slot0/req_a'}]),
            self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('distinct lifetime', v['reason'])

    def test_a_second_lifetime_that_starts_late_does_not_certify(self):
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 101.0, 'identity': 'a'},
            {'start': 100.3, 'end': 101.0, 'identity': 'b'}]),
            self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertEqual(v['concurrency_observed_min'], 1)

    def test_an_anonymous_window_cannot_be_counted(self):
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 101.0},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}]),
            self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('no string identity', v['reason'])

    def test_an_incomplete_lifecycle_refuses_and_does_not_exclude(self):
        """Root: "Unknown/missing endpoint or lifecycle discontinuity refuses
        coverage and retains the attempt; it does not become a task exclusion."
        """
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 101.0, 'identity': 'a'},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}],
            lifecycle_complete=False), self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('lifecycle_complete', v['reason'])

    def test_declaring_concurrency_one_is_refused(self):
        v = lab_prepare._coverage_verdict(self._lifecycle([
            {'start': 99.0, 'end': 101.0, 'identity': 'a'},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}],
            concurrency_required=1), self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('at least', v['reason'])

    def test_no_arrivals_yields_no_observation_of_activity(self):
        obs = self._observer([])
        with obs:
            o = obs.observe()
        self.assertFalse(o['active'])
        self.assertEqual(o['active_windows'], [])

    def test_the_observer_stops_the_sweep_on_the_first_uncovered_attempt(self):
        """Through the REAL entry point: raw attempt retained, then immediate stop."""
        tmp = Path(tempfile.mkdtemp(prefix='loadobs_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        obs = self._observer([])                  # load absent
        obs.start()
        self.addCleanup(obs.stop)
        wiring = PreparationWiringTests('test_refuses_without_a_load_observer')
        with self.assertRaises(lab_prepare.PreparationRefused):
            lab_prepare.run_reference_sweep(
                [], {}, ledger_path=tmp / 'l.jsonl', load_observer=obs.observe,
                enforce_tmpdir=False, sweep_fn=wiring._stub_sweep())
        rows = [json.loads(x) for x in
                (tmp / 'l.jsonl').read_text('utf-8').splitlines() if x.strip()]
        kinds = [r.get('schema') for r in rows]
        self.assertIn(lab_data.ATTEMPT_RECORD_SCHEMA, kinds)   # raw attempt retained
        self.assertIn('live_ab/load_coverage-v1', kinds)       # and the refusal reason

    # -- the interior-gap declaration is SUPERSEDED -------------------------
    # It was added when the arrival instrument was still meant to certify: an
    # observation had to declare the largest unobserved gap inside its windows.
    # Root's 2026-09-22 decision removed the premise -- arrivals cannot certify at
    # all, and inside a server-acknowledged lifetime "server scheduling pauses
    # ... are part of the operational regime", so an interior-gap tolerance would
    # reject exactly the evidence that is now required. The check is gone from
    # _coverage_verdict and its two tests are gone with it, rather than left
    # asserting a rule the function no longer applies.

    # -- the real source ---------------------------------------------------
    def test_the_load_generator_may_only_address_loopback(self):
        with self.assertRaises(lab_load.LoadRefused):
            lab_load.StreamingHttpLoad(base_url='http://example.com:8080',
                                       model='m', prompt='p')

    def test_streamed_chunks_are_stamped_and_no_generated_text_is_kept(self):
        clock = iter([10.0, 10.1, 10.2, 10.3])

        class _Resp:
            status_code = 200

            def iter_lines(self):
                return [b'data: {"choices":[{"delta":{"content":"a"}}]}',
                        b'', b'data: {"choices":[{"delta":{"content":"b"}}]}',
                        b'data: [DONE]']

        class _Session:
            def post(self, *a, **kw):
                return _Resp()

        src = lab_load.StreamingHttpLoad(
            base_url='http://127.0.0.1:8193', model='m', prompt='p',
            clock=lambda: next(clock), session_factory=_Session)
        got = []
        src._one_generation(_Session(), 'g0', lambda gid, t: got.append((gid, t)))
        self.assertEqual(got, [('g0', 10.0), ('g0', 10.1)])

    def test_a_failing_load_source_is_unhealthy_rather_than_quiet(self):
        class _Session:
            def post(self, *a, **kw):
                raise OSError('connection refused')

        src = lab_load.StreamingHttpLoad(base_url='http://127.0.0.1:8193',
                                         model='m', prompt='p',
                                         session_factory=_Session)
        src._loop(lambda gid, t: None)
        self.assertFalse(src.healthy())
        self.assertTrue(src.errors)

    # -- pinning -----------------------------------------------------------
    def test_the_observer_is_pinned_in_the_harness_set(self):
        self.assertIn('lab_load.py', lab_common.HARNESS_FILES)


class LoadObserverSecondReviewTests(unittest.TestCase):
    """Defects found by an adversarial review of the repaired observer.

    Every one of these was a real input that produced a wrong answer. They are
    kept as the regression set for the classes of mistake, not only the instances.
    """

    GAP = 0.5

    def _probe(self, n=lab_load.MIN_JITTER_SAMPLES):
        p = lab_load.JitterProbe()
        for _ in range(n):
            p.observe_sample(0.002)
        return p

    def _lc(self, windows, **kw):
        obs = {'active': True, 'window_id': 'lc', 'endpoint_error_s': 0.0,
               'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
               'clock': 'clock_gettime(CLOCK_MONOTONIC)',
               'boot_id': 'boot:aa', 'host_id': 'host:bb',
               'concurrency_required': 2, 'active_windows': windows}
        obs.update(kw)
        return obs

    ATTEMPT = {'interval_schema': 'live_ab/attempt_interval-v3',
               'verification_started_monotonic': 100.0,
               'verification_ended_monotonic': 100.5,
               'verification_started_posix_ns': 100_000_000_000,
               'verification_ended_posix_ns': 100_500_000_000,
               'clock_domain_posix': 'clock_gettime(CLOCK_MONOTONIC)',
               'boot_id': 'boot:aa', 'host_id': 'host:bb',
               'boot_source': 'sysctl kern.bootsessionuuid',
               'host_source': 'platform.node'}

    # -- identity must be a value, not a repr -------------------------------
    def test_one_slot_written_two_ways_is_not_two_lifetimes(self):
        """`str(ident)` made distinctness a property of the Python repr: a slot
        written once as 0 and once as '0' became TWO lifetimes -- fabricating
        exactly the concurrency the rule exists to require."""
        v = lab_prepare._coverage_verdict(self._lc([
            {'start': 99.0, 'end': 101.0, 'identity': 0},
            {'start': 99.0, 'end': 101.0, 'identity': '0'}]), self.ATTEMPT)
        self.assertFalse(v['valid'])
        self.assertIn('no string identity', v['reason'])

    def test_a_zero_duration_window_is_not_an_occupied_lifetime(self):
        v = lab_prepare._coverage_verdict(self._lc([
            {'start': 100.2, 'end': 100.2, 'identity': 'a'},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}]), self.ATTEMPT)
        self.assertFalse(v['valid'])
        self.assertIn('zero duration', v['reason'])

    def test_concurrency_required_must_be_an_integer(self):
        for bad in (2.9, '2', True, None):
            with self.subTest(bad=bad):
                v = lab_prepare._coverage_verdict(
                    self._lc([{'start': 99.0, 'end': 101.0, 'identity': 'a'},
                              {'start': 99.0, 'end': 101.0, 'identity': 'b'}],
                             concurrency_required=bad), self.ATTEMPT)
                self.assertFalse(v['valid'])

    # -- the clock is named and checked, not assumed ------------------------
    def test_a_legacy_observation_against_a_v3_record_is_refused(self):
        """The 694 s finding, turned into a gate: a POSIX-clock lifecycle may not
        be compared with a Python-monotonic verifier interval, even on one host.
        Root 2026-09-22 03:19: "Do not compare a Python-monotonic interval to a
        POSIX-clock lifecycle, even if both are on the same host." """
        v = lab_prepare._coverage_verdict(self._lc([
            {'start': 99.0, 'end': 101.0, 'identity': 'a'},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}],
            clock='time.monotonic'), self.ATTEMPT)
        self.assertFalse(v['valid'])
        self.assertIn('exact named POSIX domain', v['reason'])

    def test_an_unsupported_clock_domain_is_refused(self):
        v = lab_prepare._coverage_verdict(self._lc([
            {'start': 99.0, 'end': 101.0, 'identity': 'a'},
            {'start': 99.0, 'end': 101.0, 'identity': 'b'}],
            clock='time.perf_counter'), self.ATTEMPT)
        self.assertFalse(v['valid'])
        self.assertIn('unsupported clock domain', v['reason'])

    def test_an_observation_that_names_no_clock_is_refused(self):
        obs = self._lc([{'start': 99.0, 'end': 101.0, 'identity': 'a'},
                        {'start': 99.0, 'end': 101.0, 'identity': 'b'}])
        obs.pop('clock')
        self.assertFalse(lab_prepare._coverage_verdict(obs, self.ATTEMPT)['valid'])

    # -- liveness is a property of the arrivals, not of a thread ------------
    def test_a_hung_generator_does_not_keep_reporting_load(self):
        """healthy() was 'no errors AND thread alive'. A worker blocked inside
        iter_lines() on a server that stopped decoding is both -- for up to the
        300 s request timeout -- so observe() returned active windows minutes
        after the last token."""
        script = [('g0', 100.0), ('g0', 100.05), ('g0', 100.10),
                  ('g0', 100.15), ('g0', 100.20)]
        fresh = lab_load.ContinuousLoadObserver(
            lab_load.ScriptedLoad(script), max_interior_gap_s=self.GAP,
            jitter=self._probe(), clock=lambda: 100.25)
        with fresh:
            self.assertTrue(fresh.observe()['active'])
        hung = lab_load.ContinuousLoadObserver(
            lab_load.ScriptedLoad(script), max_interior_gap_s=self.GAP,
            jitter=self._probe(), clock=lambda: 250.0)
        with hung:
            o = hung.observe()
        self.assertFalse(o['active'])
        self.assertIn('STOPPED', o['reason'])
        self.assertGreater(o['newest_arrival_age_s'], 100.0)

    # -- two sources must not look like a broken clock ----------------------
    def test_interleaved_sources_out_of_global_order_do_not_abort_the_sweep(self):
        """Stamping and appending are not atomic, so source B can stamp 100.001,
        source A stamp 100.000, and A append second. The global order check then
        raised 'not one monotonic clock' and aborted the whole sweep, although
        each generation's own stamps were perfectly ordered."""
        series = [('srcB/g0', 100.001), ('srcA/g0', 100.000),
                  ('srcB/g0', 100.101), ('srcA/g0', 100.100)]
        w = lab_load.windows_from_arrivals(series, max_interior_gap_s=self.GAP)
        self.assertEqual(len(w), 2)
        self.assertEqual({x['generation_id'] for x in w}, {'srcA/g0', 'srcB/g0'})

    def test_one_generation_out_of_its_own_order_still_refuses(self):
        with self.assertRaises(lab_load.LoadRefused):
            lab_load.windows_from_arrivals(
                [('g0', 100.0), ('g0', 100.2), ('g0', 100.1)],
                max_interior_gap_s=self.GAP)

    # -- the jitter probe --------------------------------------------------
    def test_a_stall_does_not_manufacture_samples(self):
        """Without a catch-up skip, one stall replays every missed tick with no
        sleep: a 5 s stall made 200,000 'samples' in 50 ms, and
        MIN_JITTER_SAMPLES -- which exists to stop an unmeasured bound -- was
        satisfied by the stall itself."""
        ticks = iter([0.0] + [5.0] * 4000)
        p = lab_load.JitterProbe(interval_s=0.010, clock=lambda: next(ticks),
                                 sleep=lambda s: None)
        p._stop.set()                      # one pass only
        p._loop()
        self.assertLessEqual(p.samples, 2)

    def test_a_probe_that_will_not_stop_is_not_reported_as_stopped(self):
        p = lab_load.JitterProbe()
        for _ in range(lab_load.MIN_JITTER_SAMPLES):
            p.observe_sample(0.001)
        p._thread = types.SimpleNamespace(is_alive=lambda: True,
                                          join=lambda timeout=None: None)
        p.stop()
        self.assertIsNotNone(p._thread)     # NOT cleared
        self.assertFalse(p.bound()['available'])
        with self.assertRaises(lab_load.LoadRefused):
            p.start()

    def test_a_nonpositive_ring_capacity_refuses_instead_of_raising_later(self):
        with self.assertRaises(lab_load.LoadRefused):
            lab_load.ContinuousLoadObserver(lab_load.ScriptedLoad([]),
                                            ring_capacity=0)

    # -- the sink retains the observation before the fallible verdict -------
    def test_a_verdict_that_raises_does_not_lose_the_observation(self):
        tmp = Path(tempfile.mkdtemp(prefix='cov_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        wiring = PreparationWiringTests('test_refuses_without_a_load_observer')

        def observer():
            return {'active': True, 'window_id': 'w',
                    'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
                    'clock': 'clock_gettime(CLOCK_MONOTONIC)',
                    'boot_id': 'boot:aa', 'host_id': 'host:bb',
                    'concurrency_required': 2, 'endpoint_error_s': 0.0,
                    'active_windows': 'not-a-list-at-all'}

        with mock.patch.object(lab_prepare, '_coverage_verdict',
                               side_effect=RuntimeError('boom')):
            with self.assertRaises(lab_prepare.PreparationRefused):
                lab_prepare.run_reference_sweep(
                    [], {}, ledger_path=tmp / 'l.jsonl', load_observer=observer,
                    enforce_tmpdir=False, sweep_fn=wiring._stub_sweep())
        rows = [json.loads(x) for x in
                (tmp / 'l.jsonl').read_text('utf-8').splitlines() if x.strip()]
        kinds = [r.get('schema') for r in rows]
        self.assertIn(lab_data.ATTEMPT_RECORD_SCHEMA, kinds)
        self.assertIn('live_ab/load_observation_raw-v1', kinds)   # RETAINED
        self.assertIn('live_ab/load_coverage_failure-v1', kinds)


class NamedClockDomainTests(unittest.TestCase):
    """Root's authorized clock repair, driven through the ACTUAL producer and
    consumer (root 2026-09-22 03:19 item 4: "Use deterministic reader/observer
    stubs to test a large domain offset, changing offset, wrong/missing domain,
    reboot mismatch and the normal matched-clock case, through the actual
    producer and consumer")."""

    def _record(self, **kw):
        base = dict(
            uid='t/1', run_index=0,
            result={'success': False, 'sentinel_seen': False, 'timed_out': False,
                    'entry_point_defined': True, 'sandbox_flag': False,
                    'verify_seconds': 0.2,
                    'run': {'passed': False, 'returncode': 1, 'stdout_tail': 'o',
                            'stderr': 'e', 'timed_out': False}})
        base.update(kw)
        return lab_data.attempt_record(**base)

    def _obs(self, clock, boot_id, windows=None, host_id='host:bb'):
        return {'active': True, 'window_id': 'lc', 'endpoint_error_s': 0.0,
                'evidence_kind': 'server_lifecycle', 'lifecycle_complete': True,
                'clock': clock, 'boot_id': boot_id, 'host_id': host_id,
                'concurrency_required': 2,
                'active_windows': windows or [
                    {'start': 99.0, 'end': 102.0, 'identity': 'slot0/req_a'},
                    {'start': 99.0, 'end': 102.0, 'identity': 'slot1/req_b'}]}

    # -- the producer -------------------------------------------------------
    def test_the_producer_labels_v3_only_when_it_really_has_both_clocks(self):
        v3 = self._record(verification_started_monotonic=100.0,
                          verification_ended_monotonic=100.5,
                          verification_started_posix_ns=100_000_000_000,
                          verification_ended_posix_ns=100_500_000_000,
                          boot_id='boot:1', host_id='host:bb')
        self.assertEqual(v3['interval_schema'], lab_data.INTERVAL_SCHEMA_V3)
        v2 = self._record(verification_started_monotonic=100.0,
                          verification_ended_monotonic=100.5)
        self.assertEqual(v2['interval_schema'], 'live_ab/attempt_interval-v2')
        self.assertIsNone(v2['verification_started_posix_ns'])

    def test_the_legacy_fields_keep_their_own_semantics_beside_the_new_ones(self):
        r = self._record(verification_started_monotonic=100.0,
                         verification_ended_monotonic=100.5,
                         verification_started_posix_ns=794_000_000_000,
                         verification_ended_posix_ns=794_600_000_000,
                         boot_id='boot:1', host_id='host:bb')
        self.assertEqual(r['verification_started_monotonic'], 100.0)
        self.assertEqual(r['verification_started_posix_ns'], 794_000_000_000)
        self.assertEqual(r['clock_domain_legacy'], lab_data.CLOCK_DOMAIN_LEGACY)
        self.assertEqual(r['clock_domain_posix'], lab_data.CLOCK_DOMAIN_POSIX)

    def test_the_posix_reads_are_ordered_to_WIDEN_the_interval(self):
        """Root: read the POSIX start BEFORE the legacy start and the POSIX end
        AFTER the legacy end, so cross-call order widens rather than shortens."""
        src = inspect.getsource(lab_data.sweep_references)
        i_ps = src.index('_verify_started_posix_ns = ')
        i_ls = src.index('_verify_started = time.monotonic()')
        i_le = src.index('_verify_ended = time.monotonic()')
        i_pe = src.index('_verify_ended_posix_ns = ')
        self.assertLess(i_ps, i_ls)
        self.assertLess(i_le, i_pe)

    def test_boot_identity_is_the_KERNEL_session_digested_and_refuses_otherwise(self):
        """Root, 2026-09-22 04:02: the previous helper returned second-truncated
        wall-minus-clock arithmetic, which "establishes neither reboot
        discrimination nor host identity" -- a same-POSIX-time/different-wall pair
        returns boot:900 then boot:901. It is now the kernel boot session,
        digested, with NO fallback."""
        a = lab_data.boot_identity()
        self.assertTrue(a.startswith('boot:'))
        self.assertEqual(len(a.split(':', 1)[1]), 32)     # a digest, not a count
        self.assertEqual(a, lab_data.boot_identity())     # stable within a boot
        with mock.patch.object(lab_data.subprocess, 'run') as run:
            run.return_value = types.SimpleNamespace(returncode=0, stdout='  ')
            with self.assertRaises(lab_data.ProvenanceUnavailable):
                lab_data.boot_identity()                  # NO 'unknown' fallback

    def test_the_raw_machine_identifiers_never_appear(self):
        import platform as _pl
        raw_host = _pl.node()
        self.assertNotIn(raw_host, lab_data.host_identity())
        self.assertNotIn(raw_host, json.dumps(lab_data.clock_provenance()))

    # -- the consumer: the five cases root named ---------------------------
    def _v3(self, boot_id='boot:1', host_id='host:bb'):
        return self._record(verification_started_monotonic=100.0,
                            verification_ended_monotonic=100.5,
                            verification_started_posix_ns=100_000_000_000,
                            verification_ended_posix_ns=100_500_000_000,
                            boot_id=boot_id, host_id=host_id,
                            boot_source='sysctl kern.bootsessionuuid',
                            host_source='platform.node')

    def test_matched_clock_case_certifies(self):
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1'), self._v3())
        self.assertTrue(v['valid'], v.get('reason'))
        self.assertEqual(v['interval_version'], lab_data.INTERVAL_SCHEMA_V3)

    def test_a_large_domain_offset_does_not_make_coverage_easier(self):
        """694 s of offset applied to the WINDOWS, with the record unchanged: the
        windows no longer contain the attempt and coverage is refused. Nothing
        subtracts the offset -- root forbade that explicitly."""
        off = 694.1511
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1', windows=[
                {'start': 99.0 + off, 'end': 102.0 + off, 'identity': 'a'},
                {'start': 99.0 + off, 'end': 102.0 + off, 'identity': 'b'}]),
            self._v3())
        self.assertFalse(v['valid'])

    def test_a_wrong_domain_is_refused(self):
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_LEGACY, 'boot:1'), self._v3())
        self.assertFalse(v['valid'])
        self.assertIn('exact named POSIX domain', v['reason'])

    def test_a_missing_domain_is_refused(self):
        obs = self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1')
        obs.pop('clock')
        v = lab_prepare._coverage_verdict(obs, self._v3())
        self.assertFalse(v['valid'])
        self.assertIn('names no clock domain', v['reason'])

    def test_a_reboot_mismatch_is_refused_and_says_why(self):
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:2'), self._v3(boot_id='boot:1'))
        self.assertFalse(v['valid'])
        self.assertIn('kernel boot session identity differs', v['reason'])

    def test_a_host_mismatch_is_refused(self):
        """Root counterexample (b): host_id 'hostA' versus 'hostB' with the same
        boot string CERTIFIED, because the host fields were ignored entirely."""
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1', host_id='host:OTHER'),
            self._v3(host_id='host:bb'))
        self.assertFalse(v['valid'])
        self.assertIn('host identity differs', v['reason'])

    def test_two_equally_absent_or_unknown_identities_are_not_a_match(self):
        """Root counterexamples (a): both boot_id None CERTIFIED, and both
        'unknown' CERTIFIED, because the check was metadata EQUALITY."""
        for bad in ('unknown', 'n/a'):
            with self.subTest(bad=bad, route='labelled v3'):
                v = lab_prepare._coverage_verdict(
                    self._obs(lab_data.CLOCK_DOMAIN_POSIX, bad),
                    self._v3(boot_id=bad))
                self.assertFalse(v['valid'])
                self.assertIn('not an identity', v['reason'])
        for bad in (None, ''):
            with self.subTest(bad=bad, route='cannot even be v3'):
                # A record with no identity is not v3 at all: the producer will
                # not label it so. It is then refused as non-production legacy,
                # which is a refusal by a different door and is also correct.
                rec = self._v3(boot_id=bad)
                self.assertNotEqual(rec['interval_schema'],
                                    lab_data.INTERVAL_SCHEMA_V3)
                v = lab_prepare._coverage_verdict(
                    self._obs(lab_data.CLOCK_DOMAIN_POSIX, bad), rec)
                self.assertFalse(v['valid'])

    def test_malformed_nanosecond_endpoints_refuse_and_retain(self):
        for bad in (100.5, None, '100'):
            with self.subTest(bad=bad):
                rec = self._v3()
                rec['verification_started_posix_ns'] = bad
                v = lab_prepare._coverage_verdict(
                    self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1'), rec)
                self.assertFalse(v['valid'])

    def test_a_v2_record_is_not_compared_with_a_posix_lifecycle(self):
        v2 = self._record(verification_started_monotonic=100.0,
                          verification_ended_monotonic=100.5)
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_POSIX, 'boot:1'), v2)
        self.assertFalse(v['valid'])
        self.assertIn('New production requires', v['reason'])

    def test_a_v2_record_cannot_be_certified_in_production_at_all(self):
        """Root counterexample (d): an unsupported POSIX reader silently emitted
        v2 and a legacy-domain observation then certified it -- "current source
        can silently turn unavailable new instrumentation into accepted legacy
        production."""
        v2 = self._record(verification_started_monotonic=100.0,
                          verification_ended_monotonic=100.5)
        self.assertEqual(v2['interval_schema'], 'live_ab/attempt_interval-v2')
        v = lab_prepare._coverage_verdict(
            self._obs(lab_data.CLOCK_DOMAIN_LEGACY, 'boot:1'), v2)
        self.assertFalse(v['valid'])
        self.assertIn('historical audit route', v['reason'])

    def test_an_unavailable_posix_reader_refuses_BEFORE_dispatch(self):
        """And the production sweep must not reach the verifier at all."""
        seen = []
        with mock.patch.object(lab_data, '_posix_monotonic_ns', lambda: None):
            with self.assertRaises(lab_data.ProvenanceUnavailable) as c:
                # An EMPTY task list: the refusal must not depend on there
                # being work to do. It is hoisted above the task loop, so no
                # task is even read before it fires.
                lab_data.sweep_references(
                    [], {}, on_attempt=lambda rec: seen.append(rec))
        self.assertIn('BEFORE the verifier is dispatched', str(c.exception))
        self.assertEqual(seen, [])          # no attempt was ever produced


class ProductionStartupGuardTests(unittest.TestCase):
    """The fixture refusal at the ACTUAL production entry points.

    Root's reviewer, 2026-09-22 02:37: "A repository-wide Python search at exact
    ce106af finds the production guard call only in lab_prepare.
    run_reference_sweep; it does not show a call in lab_orchestrator.run_trial /
    trial preflight. Thus a general trial-startup refusal claim is not yet
    demonstrated."

    And the caveat that decides how these are written: every existing e2e world
    OVERRIDES World.spawn, so a check inside the production body is exercised by
    none of them. Each test below drives the REAL production body with its
    process/filesystem dependencies stubbed, and each has a CONTROL that shows
    the same path proceeds on a clean configuration -- a guard that refuses
    everything would otherwise pass every refusal test.
    """

    FIXTURE_CFG = {'injected_decision_fixture': {'decision': 'DEPLOY'}}

    def test_the_shared_key_is_the_fixture_key(self):
        """Kept equal by a test, not by a comment."""
        import lab_injected_decision as lid
        self.assertEqual(lab_common.FIXTURE_ACTIVATION_KEY, lid.ACTIVATION_KEY)

    def test_presence_counts_whatever_the_value(self):
        for cfg in ({'injected_decision_fixture': None},
                    {'injected_decision_fixture': False},
                    {'injected_decision_fixture': {}},
                    {'testing': {'injected_decision_fixture': True}}):
            with self.subTest(cfg=cfg):
                self.assertTrue(lab_common.fixture_requested(cfg))
        for cfg in ({}, {'trials': {}}, {'testing': {}},
                    {'testing': {'injected_decision_fixture': False}}, None):
            with self.subTest(cfg=cfg):
                self.assertFalse(lab_common.fixture_requested(cfg))

    # -- World.spawn: the real body, zero Popen on refusal -------------------
    def _fake_world(self, cfg, logs):
        import lab_orchestrator as orch
        return types.SimpleNamespace(
            rt={'worker_cmd': [sys.executable, '-c', 'pass']},
            ctx=types.SimpleNamespace(cfg=cfg,
                                      paths=types.SimpleNamespace(logs=logs)),
        ), orch

    def test_the_production_spawn_body_refuses_and_starts_NO_process(self):
        import lab_orchestrator as orch
        tmp = Path(tempfile.mkdtemp(prefix='spawn_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        me, _ = self._fake_world(self.FIXTURE_CFG, tmp / 'logs')
        att = types.SimpleNamespace(arrival=1, attempt=0, proc=None)
        with mock.patch.object(orch.subprocess, 'Popen') as popen:
            with self.assertRaises(lab_common.PreflightError):
                orch.World.spawn(me, att, tmp / 'job.json')
        popen.assert_not_called()
        self.assertIsNone(att.proc)

    def test_the_production_spawn_body_PROCEEDS_on_a_clean_config(self):
        """The control. Without it, a guard that refused everything would pass."""
        import lab_orchestrator as orch
        tmp = Path(tempfile.mkdtemp(prefix='spawn_ok_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        me, _ = self._fake_world({'trials': {}}, tmp / 'logs')
        att = types.SimpleNamespace(arrival=1, attempt=0, proc=None)
        with mock.patch.object(orch.subprocess, 'Popen') as popen:
            popen.return_value = types.SimpleNamespace(pid=4242)
            pid = orch.World.spawn(me, att, tmp / 'job.json')
        popen.assert_called_once()
        self.assertEqual(pid, 4242)

    # -- lab_worker.run_job: the real body ----------------------------------
    def test_the_real_run_job_refuses_before_it_opens_the_spool(self):
        import lab_worker
        job = dict(self.FIXTURE_CFG, paths={'spool': '<WORK>/nope.jsonl'})
        with mock.patch.object(lab_worker, 'Spool') as spool:
            with self.assertRaises(lab_common.PreflightError):
                lab_worker.run_job(job, sandbox_lock_path=Path('/dev/null'))
        spool.assert_not_called()

    def test_the_real_run_job_also_inspects_the_jobs_cfg(self):
        import lab_worker
        job = {'cfg': self.FIXTURE_CFG, 'paths': {'spool': '<WORK>/nope.jsonl'}}
        with mock.patch.object(lab_worker, 'Spool') as spool:
            with self.assertRaises(lab_common.PreflightError):
                lab_worker.run_job(job, sandbox_lock_path=Path('/dev/null'))
        spool.assert_not_called()

    def test_the_real_run_job_PROCEEDS_past_the_guard_on_a_clean_job(self):
        """The control: a clean job reaches the spool, so the guard is not a
        blanket refusal. It then fails further in for its own reasons, which is
        not what this test is about."""
        import lab_worker
        job = {'cfg': {'trials': {}}, 'paths': {'spool': '<WORK>/x.jsonl'}}
        with mock.patch.object(lab_worker, 'Spool') as spool:
            spool.side_effect = RuntimeError('reached the spool')
            with self.assertRaises(Exception) as ctx:
                lab_worker.run_job(job, sandbox_lock_path=Path('/dev/null'))
        self.assertNotIsInstance(ctx.exception, lab_common.PreflightError)
        spool.assert_called()

    # -- orchestrator preflight ---------------------------------------------
    def test_trial_preflight_refuses_a_fixture_configuration(self):
        import lab_orchestrator as orch
        ctx = types.SimpleNamespace(cfg=dict(self.FIXTURE_CFG, _runtime={}))
        with self.assertRaises(lab_common.PreflightError) as c:
            orch.preflight(ctx)
        self.assertIn('trial preflight', str(c.exception))

    def test_preflight_refuses_before_any_drift_accounting(self):
        """It must raise before it reads the freeze directory: a fixture
        configuration should never get as far as being compared with the frozen
        files."""
        import lab_orchestrator as orch
        ctx = types.SimpleNamespace(cfg=dict(self.FIXTURE_CFG, _runtime={}))
        with mock.patch.object(orch, 'sha256_file') as digest:
            with self.assertRaises(lab_common.PreflightError):
                orch.preflight(ctx)
        digest.assert_not_called()

    # -- the call sites exist, and a later edit that drops one is caught -----
    def test_every_named_production_path_calls_the_shared_guard(self):
        import lab_orchestrator as orch
        import lab_worker
        for fn, label in ((orch.preflight, 'preflight'),
                          (orch.World.spawn, 'World.spawn'),
                          (lab_worker.run_job, 'run_job')):
            with self.subTest(path=label):
                self.assertIn('assert_no_fixture', inspect.getsource(fn),
                              '%s no longer calls the shared startup guard' % label)

    def test_the_policy_is_not_cloned_into_a_second_implementation(self):
        """Root: "Do not clone the policy into two implementations." The
        delegating module must not carry its own membership test."""
        import lab_injected_decision as lid
        src = inspect.getsource(lid.assert_no_test_fixture_active)
        self.assertIn('lab_common.fixture_requested', src)
        self.assertNotIn("ACTIVATION_KEY in cfg", src)


class ServerLifecycleProducerConsumerTests(unittest.TestCase):
    """The MODEL-FREE producer/consumer fixture root required (2026-09-22 04:02):
    "Deliver ... durable start/end lifecycle records, complete/failed lifecycle
    handling and a model-free fixture through the ACTUAL producer format and
    consumer."

    The records here are written in exactly the bytes the patched server emits
    (`experiments/live_ab_serving/live_ab_slot_lifecycle.patch`), and are driven
    through the real `lab_lifecycle.observe` and the real
    `lab_prepare._coverage_verdict`. No server, no model, no network.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='lifecycle_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / 'lifecycle.jsonl'
        self._seq = 0
        self.prov = {'boot_id': 'boot:aa', 'host_id': 'host:bb',
                     'boot_source': 'sysctl kern.bootsessionuuid',
                     'host_source': 'platform.node'}
        # The run manifest the supervisor persists BEFORE dispatch. Root
        # 2026-09-22 04:59: the reader compares records against this instead of
        # stamping its own process's provenance onto whatever file it is handed.
        self.expected = {'host_id': 'host:bb', 'boot_id': 'boot:aa',
                         'instance_id': 'srv_1_2',
                         'binary_sha256': 'b' * 64, 'patch_sha256': 'p' * 64}

    def _emit(self, *, slot, task, t_assigned, t_prompt, t_gen, t_rel,
              complete=True, instance='srv_1_2', clock=None, units='microseconds'):
        """One line in the emitter's exact format."""
        rec = {'schema': 'live_ab/slot_lifecycle-v1', 'instance_id': instance,
               'slot_id': slot, 'task_id': task,
               'clock': clock or lab_lifecycle.CLOCK, 'units': units,
               'run_token': instance,
               't_assigned_us': t_assigned, 't_prompt_start_us': t_prompt,
               't_gen_last_us': t_gen, 't_released_us': t_rel,
               'n_prompt_processed': 10, 'n_gen': 1024, 'complete': complete,
               'means': 'occupied decoding slot, not uninterrupted hardware utilization'}
        rec['seq'] = self._seq
        self._seq += 1
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def _seal(self, records=None, write_failures=0, token='srv_1_2'):
        """The closing seal, in the bytes the built binary actually writes."""
        seal = {'schema': 'live_ab/acquisition_seal-v1', 'run_token': token,
                'records': self._seq if records is None else records,
                'write_failures': write_failures, 't_us': 103_000_000,
                'clock': lab_lifecycle.CLOCK}
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(seal, separators=(',', ':')) + '\n')

    def _attempt(self, start_s, end_s):
        return lab_data.attempt_record(
            't/1', 0, {'success': False, 'sentinel_seen': False, 'timed_out': False,
                       'entry_point_defined': True, 'sandbox_flag': False,
                       'verify_seconds': 0.2,
                       'run': {'passed': False, 'returncode': 1, 'stdout_tail': 'o',
                               'stderr': 'e', 'timed_out': False}},
            verification_started_monotonic=start_s,
            verification_ended_monotonic=end_s,
            verification_started_posix_ns=int(start_s * 1e9),
            verification_ended_posix_ns=int(end_s * 1e9),
            boot_id='boot:aa', host_id='host:bb',
            boot_source='sysctl kern.bootsessionuuid', host_source='platform.node')

    # -- the regime root prescribed: TWO concurrent occupancies ---------------
    def test_two_concurrent_occupancies_covering_the_attempt_certify(self):
        self._emit(slot=0, task=11, t_assigned=99_000_000, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000)
        self._emit(slot=1, task=12, t_assigned=99_050_000, t_prompt=99_150_000,
                   t_gen=102_050_000, t_rel=102_150_000)
        self._seal()
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        self.assertTrue(obs['active'])
        self.assertTrue(obs['lifecycle_complete'])
        self.assertEqual(len(obs['active_windows']), 2)
        v = lab_prepare._coverage_verdict(obs, self._attempt(100.0, 100.5))
        self.assertTrue(v['valid'], v.get('reason'))
        self.assertEqual(v['concurrency_observed_min'], 2)

    def test_ONE_occupancy_does_not_certify_however_long_it_is(self):
        self._emit(slot=0, task=11, t_assigned=1, t_prompt=90_000_000,
                   t_gen=110_000_000, t_rel=110_100_000)
        self._seal()
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        v = lab_prepare._coverage_verdict(obs, self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('distinct lifetime', v['reason'])

    def test_the_INNER_bracket_is_used_so_coverage_is_never_made_easier(self):
        """The outer bracket would cover the attempt; the inner one does not."""
        self._emit(slot=0, task=11, t_assigned=99_000_000, t_prompt=100_200_000,
                   t_gen=102_000_000, t_rel=102_500_000)
        self._emit(slot=1, task=12, t_assigned=99_000_000, t_prompt=100_200_000,
                   t_gen=102_000_000, t_rel=102_500_000)
        # start is charged the 1 us quantization inward
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        w = obs['active_windows'][0]
        # inner, not the outer 99.0 -- and charged the 1 us quantization INWARD
        self.assertAlmostEqual(w['start'], 100.200001, places=6)
        self.assertEqual(w['raw_inner_start_us'], 100_200_000)
        self.assertEqual(w['quantization_allowance_us'],
                         lab_lifecycle.QUANTIZATION_US)
        self.assertAlmostEqual(w['end'], 102.0)             # inner, not 102.5
        v = lab_prepare._coverage_verdict(obs, self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])                        # outer would have passed

    # -- failed / partial lifecycles ----------------------------------------
    def test_an_incomplete_lifecycle_is_refused_and_named(self):
        self._emit(slot=0, task=11, t_assigned=99_000_000, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000)
        self._emit(slot=1, task=12, t_assigned=99_000_000, t_prompt=99_100_000,
                   t_gen=0, t_rel=102_100_000, complete=False)
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        self.assertFalse(obs['lifecycle_complete'])
        self.assertEqual(len(obs['records_refused']), 1)
        self.assertIn('incomplete lifecycle', obs['records_refused'][0]['reason'])
        v = lab_prepare._coverage_verdict(obs, self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])
        self.assertIn('lifecycle_complete', v['reason'])

    def test_a_record_on_another_clock_is_refused(self):
        self._emit(slot=0, task=11, t_assigned=1, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000, clock='time.monotonic')
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        self.assertFalse(obs['active'])
        self.assertIn('not', obs['records_refused'][0]['reason'])

    def test_a_truncated_tail_is_refused_rather_than_trimmed(self):
        self._emit(slot=0, task=11, t_assigned=1, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000)
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write('{"schema":"live_ab/slot_lifecycle-v1","instance_id":"srv')
        obs = lab_lifecycle.observe(self.log, provenance=self.prov,
                                    expected=self.expected)
        self.assertFalse(obs['active'])
        self.assertIn('still writing', obs['reason'])

    def test_an_absent_log_is_an_absence_not_an_empty_success(self):
        obs = lab_lifecycle.observe(self.tmp / 'nothing.jsonl', provenance=self.prov,
                                    expected=self.expected)
        self.assertFalse(obs['active'])
        self.assertFalse(obs['lifecycle_complete'])

    # -- provenance ----------------------------------------------------------
    def test_an_observer_on_another_host_does_not_certify(self):
        """The observer measures a host the launch manifest does not name, so the
        manifest is not bound to this observer and nothing it vouches for
        certifies. Before root's 05:42 witness this reached the verifier check
        and failed there; it now fails one link earlier, which is the point."""
        self._emit(slot=0, task=11, t_assigned=1, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000)
        self._emit(slot=1, task=12, t_assigned=1, t_prompt=99_100_000,
                   t_gen=102_000_000, t_rel=102_100_000)
        obs = lab_lifecycle.observe(
            self.log, provenance=dict(self.prov, host_id='host:ELSEWHERE'),
            expected=self.expected)
        self.assertFalse(obs['manifest_bound_to_observer'])
        v = lab_prepare._coverage_verdict(obs, self._attempt(100.0, 100.5))
        self.assertFalse(v['valid'])

    # -- the patch this reader is the counterpart of -------------------------
    def test_the_patch_exists_and_names_its_base_revision(self):
        patch = Path(lab_common.REPO_ROOT) / lab_lifecycle.PATCH_PATH
        self.assertTrue(patch.is_file(), 'the lifecycle patch is missing')
        text = patch.read_text('utf-8')
        self.assertIn('live_ab_emit_lifecycle', text)
        self.assertIn('slot_lifecycle-v1', text)
        self.assertIn('clock_gettime(CLOCK_MONOTONIC)', text)
        self.assertEqual(len(lab_lifecycle.PATCHED_BASE_REV), 40)


class LifecycleReaderWitnessTests(unittest.TestCase):
    """Root's six independent witnesses, 2026-09-22 04:59. Every one of them
    CERTIFIED before this repair. They are kept as the regression set."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='lcw_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / 'lifecycle.jsonl'
        self._seq = 0
        self.expected = {'host_id': 'host:bb', 'boot_id': 'boot:aa',
                         'instance_id': 'srv_1_2'}
        self.prov = {'boot_id': 'boot:aa', 'host_id': 'host:bb',
                     'boot_source': 's', 'host_source': 'p'}

    def _emit(self, **kw):
        rec = {'schema': 'live_ab/slot_lifecycle-v1', 'instance_id': 'srv_1_2',
               'run_token': 'srv_1_2',
               'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
               'slot_id': 0, 'task_id': 11,
               't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
               't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
               'n_prompt_processed': 10, 'n_gen': 1024, 'complete': True}
        rec.update(kw)
        rec.setdefault('seq', self._seq)
        self._seq += 1
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def _seal(self, records=None, write_failures=0, token='srv_1_2'):
        seal = {'schema': 'live_ab/acquisition_seal-v1', 'run_token': token,
                'records': self._seq if records is None else records,
                'write_failures': write_failures, 't_us': 103_000_000,
                'clock': lab_lifecycle.CLOCK}
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(seal, separators=(',', ':')) + '\n')

    def _obs(self, **kw):
        kw.setdefault('expected', self.expected)
        return lab_lifecycle.observe(self.log, provenance=self.prov, **kw)

    def test_witness_positive_control_still_certifies(self):
        self._emit(slot_id=0, task_id=11)
        self._emit(slot_id=1, task_id=12)
        self._seal()
        o = self._obs()
        self.assertTrue(o['active'])
        self.assertTrue(o['lifecycle_complete'])
        self.assertTrue(o['producer_bound'])

    def test_witness_a_foreign_log_is_caught_by_its_RUN_TOKEN(self):
        """Root's copied-log finding, closed the way the real emitter allows.

        The C++ emitter sends run_token/instance_id, NOT host/boot digests, so a
        reader that demanded per-record host/boot was demanding fields the
        instrument never writes -- my Python fixtures carried them and the real
        bytes never would. The record is bound by its TOKEN; the MANIFEST is
        bound to the measured host and boot (see ManifestObserverBindingTests).
        """
        self._emit(slot_id=0, task_id=11, run_token='some_other_run')
        self._emit(slot_id=1, task_id=12, run_token='some_other_run')
        o = self._obs()
        self.assertFalse(o['active'])
        self.assertEqual(len(o['records_refused']), 2)
        self.assertIn('run_token', o['records_refused'][0]['reason'])

    def test_a_record_carrying_NO_host_or_boot_field_is_fine(self):
        """The emitted shape. A positive fixture must pass on bytes the
        instrument can actually produce."""
        for slot, task in ((0, 11), (1, 12)):
            rec = {'schema': 'live_ab/slot_lifecycle-v1', 'seq': slot,
                   'run_token': 'srv_1_2', 'instance_id': 'srv_1_2',
                   'slot_id': slot, 'task_id': task,
                   'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
                   't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
                   't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
                   'n_prompt_processed': 10, 'n_gen': 1024, 'complete': True}
            with open(self.log, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, separators=(',', ':')) + '\n')
            self._seq += 1
        self._seal()
        o = self._obs()
        self.assertTrue(o['active'], o.get('reason'))
        self.assertTrue(o['lifecycle_complete'])
        for w in o['active_windows']:
            self.assertTrue(w['identity'].startswith('srv_1_2/slot'))

    def test_witness_absent_identifiers_are_not_spelled_into_identities(self):
        """Built "None/slot0/taskNone" and counted it as a lifetime."""
        self._emit(slot_id=0, task_id=None, instance_id=None)
        self._emit(slot_id=1, task_id=None, instance_id=None)
        o = self._obs()
        self.assertFalse(o['active'])
        self.assertIn('not an identity', o['records_refused'][0]['reason'])

    def test_witness_unordered_transitions_are_refused_despite_complete_true(self):
        """"complete=true, but assignment is after release" still certified.
        A boolean does not validate the record."""
        self._emit(slot_id=0, task_id=11, t_assigned_us=103_000_000, complete=True)
        self._emit(slot_id=1, task_id=12)
        o = self._obs()
        self.assertEqual(len(o['records_refused']), 1)
        self.assertIn('not ordered', o['records_refused'][0]['reason'])
        self.assertFalse(o['lifecycle_complete'])

    def test_witness_one_slot_cannot_be_occupied_twice_at_once(self):
        """"Same instance and same slot, two overlapping task IDs" counted as two
        concurrent lifetimes. Request labels inflating slot concurrency."""
        self._emit(slot_id=0, task_id=11)
        self._emit(slot_id=0, task_id=12)          # SAME slot, overlapping
        o = self._obs()
        self.assertFalse(o['active'])
        self.assertIn('cannot be occupied twice', o['reason'])

    def test_witness_quantization_is_charged_inward_not_assumed_zero(self):
        """"The POSIX producer truncates nanoseconds ... the asserted zero-error
        bound can include time before actual prompt processing." """
        self._emit(slot_id=0, task_id=11, t_prompt_start_us=100_000_000)
        self._emit(slot_id=1, task_id=12, t_prompt_start_us=100_000_000)
        o = self._obs()
        w = o['active_windows'][0]
        self.assertGreater(w['start'] * 1e6, w['raw_inner_start_us'])
        self.assertIn('does NOT mean', o['endpoint_error_basis'])

    def test_an_unbound_read_is_readable_but_never_certifying(self):
        self._emit(slot_id=0, task_id=11)
        self._emit(slot_id=1, task_id=12)
        o = lab_lifecycle.observe(self.log, provenance=self.prov)   # no manifest
        self.assertFalse(o['producer_bound'])
        self.assertFalse(o['lifecycle_complete'])
        v = lab_prepare._coverage_verdict(o, {
            'interval_schema': lab_prepare.INTERVAL_SCHEMA_V3,
            'verification_started_monotonic': 100.0,
            'verification_ended_monotonic': 100.5,
            'verification_started_posix_ns': 100_000_000_000,
            'verification_ended_posix_ns': 100_500_000_000,
            'clock_domain_posix': lab_lifecycle.CLOCK,
            'boot_id': 'boot:aa', 'host_id': 'host:bb',
            'boot_source': 's', 'host_source': 'p'})
        self.assertFalse(v['valid'])


class ManifestObserverBindingTests(unittest.TestCase):
    """Root's 05:42 witness: foreign records PLUS a matching foreign manifest,
    with local observer/verifier provenance, still obtained producer_bound=true,
    lifecycle_complete=true, coverage_valid=true.

    The error shape: I checked that two things AGREE WITH EACH OTHER without
    checking that either is what it claims to be. A foreign log and a foreign
    manifest agree perfectly.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='mob_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / 'lifecycle.jsonl'
        self.local = {'boot_id': 'boot:LOCAL', 'host_id': 'host:LOCAL',
                      'boot_source': 's', 'host_source': 'p'}

    def _emit(self, slot, task, host, boot):
        rec = {'schema': 'live_ab/slot_lifecycle-v1', 'instance_id': 'srv_X',
               'run_token': 'srv_X', 'host_id': host, 'boot_id': boot,
               'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
               'slot_id': slot, 'task_id': task,
               't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
               't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
               'n_prompt_processed': 10, 'n_gen': 1024, 'complete': True}
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def test_a_foreign_log_with_its_OWN_matching_manifest_does_not_certify(self):
        """The witness, exactly."""
        self._emit(0, 11, 'host:FOREIGN', 'boot:FOREIGN')
        self._emit(1, 12, 'host:FOREIGN', 'boot:FOREIGN')
        foreign_manifest = {'host_id': 'host:FOREIGN', 'boot_id': 'boot:FOREIGN',
                            'instance_id': 'srv_X'}
        o = lab_lifecycle.observe(self.log, provenance=self.local,
                                  expected=foreign_manifest)
        self.assertFalse(o['active'])
        self.assertFalse(o['producer_bound'])
        self.assertFalse(o['manifest_bound_to_observer'])
        self.assertIn('written HERE on THIS boot', o['reason'])

    def test_a_local_log_with_a_local_manifest_still_certifies(self):
        """The control: the new link must not refuse the legitimate case."""
        self._emit(0, 11, 'host:LOCAL', 'boot:LOCAL')
        self._emit(1, 12, 'host:LOCAL', 'boot:LOCAL')
        o = lab_lifecycle.observe(
            self.log, provenance=self.local,
            expected={'host_id': 'host:LOCAL', 'boot_id': 'boot:LOCAL',
                      'instance_id': 'srv_X'})
        self.assertTrue(o['active'])
        self.assertTrue(o['manifest_bound_to_observer'])

    def test_a_manifest_with_a_placeholder_identity_does_not_certify(self):
        self._emit(0, 11, 'host:LOCAL', 'boot:LOCAL')
        self._emit(1, 12, 'host:LOCAL', 'boot:LOCAL')
        for bad in (None, '', 'unknown'):
            with self.subTest(bad=bad):
                o = lab_lifecycle.observe(
                    self.log, provenance=self.local,
                    expected={'host_id': bad, 'boot_id': 'boot:LOCAL',
                              'instance_id': 'srv_X'})
                self.assertFalse(o['producer_bound'])

    def test_the_pending_items_are_LABELLED_not_implied_to_be_checked(self):
        """Root: "label these pending until the planned producer/consumer
        completion." An unlabelled echoed field reads as a verified one."""
        self._emit(0, 11, 'host:LOCAL', 'boot:LOCAL')
        self._emit(1, 12, 'host:LOCAL', 'boot:LOCAL')
        o = lab_lifecycle.observe(
            self.log, provenance=self.local,
            expected={'host_id': 'host:LOCAL', 'boot_id': 'boot:LOCAL',
                      'instance_id': 'srv_X'})
        pending = ' '.join(o['pending_not_yet_validated'])
        self.assertIn('ECHOED METADATA', pending)
        self.assertIn('seal', pending)


class AcquisitionSealTests(unittest.TestCase):
    """The seal and sequence contract -- and the defect the NATIVE fixture found.

    Root asked for a native model-free fixture precisely to "test real
    serialization/reader interoperability, not only Python dictionaries shaped to
    resemble it". The first thing it found: the built binary wrote its closing
    seal and THIS READER REJECTED IT as "not a slot_lifecycle-v1 record", so a
    correctly sealed acquisition read as containing garbage. The seal is the one
    line that proves the log is finished.
    """

    #: The EXACT bytes the built binary emitted, 2026-09-22 05:57, from
    #: results/live_ab/BUILD_RECEIPT_20260922T055747Z.json.
    NATIVE_SEAL = ('{"schema":"live_ab/acquisition_seal-v1","run_token":'
                   '"run_native_fixture_1790056650","records":0,'
                   '"write_failures":0,"t_us":5204918383254,'
                   '"clock":"clock_gettime(CLOCK_MONOTONIC)"}')

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='seal_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / 'l.jsonl'
        self._seq = 0
        self.prov = {'boot_id': 'boot:aa', 'host_id': 'host:bb',
                     'boot_source': 's', 'host_source': 'p'}
        self.expected = {'host_id': 'host:bb', 'boot_id': 'boot:aa',
                         'instance_id': 'srv_1_2'}

    def _emit(self, slot, task, **kw):
        rec = {'schema': 'live_ab/slot_lifecycle-v1', 'instance_id': 'srv_1_2',
               'run_token': 'srv_1_2', 'seq': self._seq,
               'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
               'slot_id': slot, 'task_id': task,
               't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
               't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
               'n_prompt_processed': 10, 'n_gen': 1024, 'complete': True}
        rec.update(kw)
        self._seq += 1
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def _seal(self, **kw):
        seal = {'schema': 'live_ab/acquisition_seal-v1', 'run_token': 'srv_1_2',
                'records': self._seq, 'write_failures': 0, 't_us': 103_000_000,
                'clock': lab_lifecycle.CLOCK}
        seal.update(kw)
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(seal, separators=(',', ':')) + '\n')

    def _obs(self):
        return lab_lifecycle.observe(self.log, provenance=self.prov,
                                     expected=self.expected)

    # -- the native bytes, through the real reader --------------------------
    def test_the_seal_the_BUILT_BINARY_wrote_is_recognised(self):
        self.log.write_text(self.NATIVE_SEAL + '\n', encoding='utf-8')
        parsed = lab_lifecycle.read_records(self.log)
        self.assertEqual(parsed['rejected'], [],
                         'the reader rejected bytes its own producer wrote')
        self.assertEqual(len(parsed['seals']), 1)
        self.assertEqual(parsed['seals'][0]['clock'], lab_lifecycle.CLOCK)
        self.assertEqual(parsed['seals'][0]['records'], 0)

    # -- the contract -------------------------------------------------------
    def test_an_UNSEALED_log_does_not_certify(self):
        """A crashed producer leaves exactly this: records, no seal."""
        self._emit(0, 11)
        self._emit(1, 12)
        o = self._obs()
        self.assertFalse(o['lifecycle_complete'])
        self.assertIn('NO CLOSING SEAL', o['seal_problem'])

    def test_a_SEQUENCE_GAP_against_the_seal_is_caught(self):
        """The seal says three records; the file carries two."""
        self._emit(0, 11)
        self._emit(1, 12)
        self._seq += 1                      # a record that never reached the file
        self._seal()
        o = self._obs()
        self.assertFalse(o['lifecycle_complete'])
        self.assertIn('sequence multiset', o['seal_problem'])

    def test_a_WRITER_FAILURE_reported_in_the_seal_refuses(self):
        self._emit(0, 11)
        self._emit(1, 12)
        self._seal(write_failures=1)
        o = self._obs()
        self.assertFalse(o['lifecycle_complete'])
        self.assertIn('write failure', o['seal_problem'])

    def test_a_seal_from_ANOTHER_RUN_refuses(self):
        self._emit(0, 11)
        self._emit(1, 12)
        self._seal(run_token='some_other_run')
        o = self._obs()
        self.assertFalse(o['lifecycle_complete'])
        self.assertIn('run token', o['seal_problem'])

    def test_TWO_seals_refuse(self):
        self._emit(0, 11)
        self._emit(1, 12)
        self._seal()
        self._seal()
        o = self._obs()
        self.assertIn('sealed once', o['seal_problem'])

    def test_a_writer_error_side_channel_record_refuses(self):
        """The producer appends acquisition errors to a SEPARATE file, but if one
        ever lands in the main log it must not be read as noise."""
        self._emit(0, 11)
        self._emit(1, 12)
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write('{"schema":"live_ab/acquisition_error-v1","stage":"write",'
                     '"t_us":1,"failures":1}\n')
        self._seal()
        o = self._obs()
        self.assertFalse(o['lifecycle_complete'])
        self.assertTrue(o['writer_errors'])

    def test_a_correctly_sealed_log_still_certifies(self):
        """The control: the contract must not refuse the legitimate case."""
        self._emit(0, 11)
        self._emit(1, 12)
        self._seal()
        o = self._obs()
        self.assertTrue(o['active'])
        self.assertTrue(o['lifecycle_complete'])
        self.assertIsNone(o['seal_problem'])


class ClockEquivalenceWindowTests(unittest.TestCase):
    """Protocol 7.5 item 4 measures the perf_counter/monotonic deltas over TEN
    SECONDS against a 1 ms tolerance. The orchestrator defaulted to 0.05 s.

    Root, 2026-09-22 04:02: "Make the actual frozen invocation use the protocol's
    10-second window and record that effective value; the new POSIX-clock
    diagnostic does not satisfy that check."

    The sensitivity arithmetic is the point. The check compares two clocks'
    ELAPSED deltas, so what it detects is a RELATIVE RATE difference. A rate
    difference that accumulates to just over the 1 ms tolerance in the protocol's
    10 s accumulates to 0.005 ms in 50 ms -- about 200x below the same tolerance.
    The short window did not merely measure less; it passed clocks the protocol
    refuses, and passed them silently.
    """

    def test_the_default_window_is_the_protocol_window(self):
        self.assertEqual(orch.CLOCK_WINDOW_PROTOCOL_S, 10.0)
        src = inspect.getsource(orch.preflight)
        self.assertIn("rt.get('clock_window_s', CLOCK_WINDOW_PROTOCOL_S)", src)
        self.assertNotIn("rt.get('clock_window_s', 0.05)", src)

    def test_a_short_window_is_RECORDED_as_below_protocol(self):
        """An offline run may shorten it; it may not hide that it did."""
        rt = {}
        with mock.patch.object(orch.time, 'sleep'):
            rec = self._run_clock_check(rt, window=0.01)
        self.assertTrue(rec['below_protocol_window'])
        self.assertEqual(rec['window_s_effective'], 0.01)
        self.assertEqual(rec['window_s_protocol'], 10.0)

    def test_the_protocol_window_is_not_flagged(self):
        rt = {}
        with mock.patch.object(orch.time, 'sleep'):
            rec = self._run_clock_check(rt, window=None)
        self.assertFalse(rec['below_protocol_window'])
        self.assertEqual(rec['window_s_effective'], 10.0)

    @staticmethod
    def _run_clock_check(rt, window):
        """Drive the real arithmetic without sleeping or building a freeze tree."""
        import time as _t
        tol_ms = 1.0
        window_s = float(window if window is not None
                         else orch.CLOCK_WINDOW_PROTOCOL_S)
        p0, m0 = _t.perf_counter(), _t.monotonic()
        dp, dm = _t.perf_counter() - p0, _t.monotonic() - m0
        return {
            'window_s_effective': window_s,
            'window_s_protocol': orch.CLOCK_WINDOW_PROTOCOL_S,
            'below_protocol_window': window_s < orch.CLOCK_WINDOW_PROTOCOL_S,
            'tolerance_ms': tol_ms,
            'difference_ms': abs(dp - dm) * 1000.0,
        }

    def test_the_sensitivity_claim_is_arithmetic_not_rhetoric(self):
        """A rate difference of 150 ppm accumulates past the 1 ms tolerance in the
        protocol's 10 s and stays far under it in 50 ms. This is why the default
        mattered.

        (100 ppm lands on EXACTLY 1.000 ms over 10 s -- the boundary, not past
        it. I asserted strictly-greater there first and the test caught me.)"""
        rate_error = 1.5e-4                    # 150 parts per million
        self.assertGreater(rate_error * 10.0 * 1000.0, 1.0)     # 1.5 ms over 10 s
        self.assertLess(rate_error * 0.05 * 1000.0, 1.0)        # 0.0075 ms over 50 ms
        # the window ratio, which is what the sensitivity loss actually is
        self.assertEqual((rate_error * 10.0) / (rate_error * 0.05), 200.0)
        # and the exact boundary case, stated rather than glossed
        self.assertEqual(1e-4 * 10.0 * 1000.0, 1.0)


class SequenceMultisetAndSidecarTests(unittest.TestCase):
    """Root, 2026-09-22 06:16: "require EXACTLY ONE non-boolean integer for each
    value in 0..count-1; reject missing, DUPLICATE, EXTRA and out-of-range
    values" and "Read and retain the actual <log>.error output".

    My first version took a SET DIFFERENCE, which is blind to duplicates and
    extras: two records both numbered 3 with 4 missing gave an empty gap and
    passed. And the producer writes failures to a separate file precisely so a
    failing log cannot hide its own failure -- useless if the reader never opens
    it.
    """

    def test_the_multiset_rejects_what_a_set_difference_missed(self):
        f = lab_lifecycle.sequence_problem
        self.assertIsNone(f([0, 1, 2], 3))                 # exact
        self.assertIsNone(f([2, 0, 1], 3))                 # order need not be numeric
        self.assertIsNotNone(f([0, 1], 3))                 # missing
        self.assertIsNotNone(f([0, 3, 3], 4))              # DUPLICATE + missing
        self.assertIsNotNone(f([0, 1, 2, 3], 3))           # extra
        self.assertIsNotNone(f([0, 1, 7], 3))              # out of range
        self.assertIsNotNone(f([0, 1, True], 3))           # bool is not an integer
        self.assertIsNotNone(f([0, 1, 2], True))           # nor is a bool a count
        self.assertIsNotNone(f([0, 1, 2], -1))             # nor a negative count
        self.assertIsNone(f([], 0))                        # an empty sealed log

    def test_the_duplicate_case_the_old_check_passed(self):
        """Exactly the input a set difference could not see."""
        seqs, declared = [0, 3, 3], 4
        self.assertEqual(sorted(set(range(declared)) - set(seqs)), [1, 2])
        problem = lab_lifecycle.sequence_problem(seqs, declared)
        self.assertIn('duplicated', problem)

    def test_the_sidecar_is_read_and_refuses_the_acquisition(self):
        tmp = Path(tempfile.mkdtemp(prefix='side_'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        log = tmp / 'l.jsonl'
        prov = {'boot_id': 'b', 'host_id': 'h', 'boot_source': 's', 'host_source': 'p'}
        exp = {'host_id': 'h', 'boot_id': 'b', 'instance_id': 'tok'}
        for i, (slot, task) in enumerate(((0, 11), (1, 12))):
            rec = {'schema': 'live_ab/slot_lifecycle-v1', 'seq': i,
                   'run_token': 'tok', 'instance_id': 'tok',
                   'slot_id': slot, 'task_id': task,
                   'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
                   't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
                   't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
                   'n_prompt_processed': 1, 'n_gen': 2, 'complete': True}
            log.open('a').write(json.dumps(rec, separators=(',', ':')) + '\n')
        log.open('a').write(json.dumps(
            {'schema': 'live_ab/acquisition_seal-v1', 'run_token': 'tok',
             'records': 2, 'write_failures': 0, 't_us': 1,
             'clock': lab_lifecycle.CLOCK}, separators=(',', ':')) + '\n')
        clean = lab_lifecycle.observe(log, provenance=prov, expected=exp)
        self.assertTrue(clean['lifecycle_complete'])       # control

        # a seal-close error is invisible ANYWHERE ELSE than the sidecar
        (tmp / 'l.jsonl.error').write_text(
            '{"schema":"live_ab/acquisition_error-v1","stage":"seal_close",'
            '"t_us":2,"failures":1}\n', encoding='utf-8')
        o = lab_lifecycle.observe(log, provenance=prov, expected=exp)
        self.assertFalse(o['lifecycle_complete'])
        self.assertIn('sidecar', o['seal_problem'])
        self.assertEqual(len(o['sidecar_records']), 1)
        self.assertEqual(o['sidecar_records'][0]['stage'], 'seal_close')


class TokenInstanceBindingTests(unittest.TestCase):
    """Root's two 06:57 witnesses. Both certified before this repair.

    The `or inst` fallback was mine, written to keep an old hand-authored fixture
    passing. That is the worst reason to weaken a production check, and root
    found both holes it opened.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='tok_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / 'l.jsonl'
        self._seq = 0
        self.prov = {'boot_id': 'b', 'host_id': 'h', 'boot_source': 's',
                     'host_source': 'p'}
        self.expected = {'host_id': 'h', 'boot_id': 'b', 'instance_id': 'launched'}

    def _emit(self, **kw):
        rec = {'schema': 'live_ab/slot_lifecycle-v1', 'seq': self._seq,
               'run_token': 'launched', 'instance_id': 'launched',
               'slot_id': 0, 'task_id': 11,
               'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
               't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
               't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
               'n_prompt_processed': 1, 'n_gen': 2, 'complete': True}
        rec.update(kw)
        self._seq += 1
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def _seal(self):
        with open(self.log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'schema': 'live_ab/acquisition_seal-v1',
                                 'run_token': 'launched', 'records': self._seq,
                                 'write_failures': 0, 't_us': 1,
                                 'clock': lab_lifecycle.CLOCK},
                                separators=(',', ':')) + '\n')

    def _obs(self):
        return lab_lifecycle.observe(self.log, provenance=self.prov,
                                     expected=self.expected)

    def test_control_two_slots_with_both_ids_certify(self):
        self._emit(slot_id=0, task_id=11)
        self._emit(slot_id=1, task_id=12)
        self._seal()
        o = self._obs()
        self.assertTrue(o['active'], o.get('reason'))
        self.assertTrue(o['lifecycle_complete'])

    def test_witness_1_a_record_with_NO_run_token_no_longer_falls_back(self):
        """"Delete run_token from otherwise valid current-format records. Both
        records still certify by falling back to instance_id. No explicit
        production schema authorizes this legacy substitution." """
        for slot, task in ((0, 11), (1, 12)):
            rec = {'schema': 'live_ab/slot_lifecycle-v1', 'seq': self._seq,
                   'instance_id': 'launched', 'slot_id': slot, 'task_id': task,
                   'clock': lab_lifecycle.CLOCK, 'units': 'microseconds',
                   't_assigned_us': 99_000_000, 't_prompt_start_us': 99_100_000,
                   't_gen_last_us': 102_000_000, 't_released_us': 102_100_000,
                   'n_prompt_processed': 1, 'n_gen': 2, 'complete': True}
            self._seq += 1
            with open(self.log, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, separators=(',', ':')) + '\n')
        self._seal()
        o = self._obs()
        self.assertFalse(o['active'])
        self.assertIn('NOT accepted as a substitute',
                      o['records_refused'][0]['reason'])

    def test_witness_2_a_valid_token_cannot_carry_foreign_instances(self):
        """"Keep the valid expected token on both records, but set both slot IDs
        to 0 and instance IDs to other_instance_0 and other_instance_1 ... Actual
        result: complete=true, coverage valid=true, observed concurrency=2."

        Two instances the single launched instance does not identify, supplying
        the concurrency the rule exists to require.
        """
        self._emit(slot_id=0, task_id=11, instance_id='other_instance_0')
        self._emit(slot_id=0, task_id=12, instance_id='other_instance_1')
        self._seal()
        o = self._obs()
        self.assertFalse(o['active'])
        self.assertEqual(len(o['records_refused']), 2)
        self.assertIn('must BOTH match', o['records_refused'][0]['reason'])

    def test_a_placeholder_token_is_not_a_token(self):
        """One record poisoned, one clean. The clean one still yields a window,
        so `active` stays true -- but the acquisition is NOT complete and the
        poisoned record is refused by name. Asserting on `active` here would have
        been asserting the wrong field: a single surviving window is not a
        certification, and the concurrency rule is what refuses it downstream."""
        for bad in (None, '', 'unknown', 'none'):
            with self.subTest(bad=bad):
                self.log.unlink(missing_ok=True)
                self._seq = 0
                self._emit(slot_id=0, task_id=11, run_token=bad)
                self._emit(slot_id=1, task_id=12)
                self._seal()
                o = self._obs()
                self.assertEqual(len(o['records_refused']), 1)
                self.assertFalse(o['lifecycle_complete'])
                self.assertEqual(len(o['active_windows']), 1)
                v = lab_prepare._coverage_verdict(o, {
                    'interval_schema': lab_prepare.INTERVAL_SCHEMA_V3,
                    'verification_started_monotonic': 100.0,
                    'verification_ended_monotonic': 100.5,
                    'verification_started_posix_ns': 100_000_000_000,
                    'verification_ended_posix_ns': 100_500_000_000,
                    'clock_domain_posix': lab_lifecycle.CLOCK,
                    'boot_id': 'b', 'host_id': 'h',
                    'boot_source': 's', 'host_source': 'p'})
                self.assertFalse(v['valid'])


class ProductionClockWindowRefusalTests(FreezeBundleBindingTests):
    """Root, 2026-09-22 06:16: "require a finite window of at least ten seconds
    ... at every actual production preflight. The runtime short-window override
    currently remains allowed and flagged; LOGGING A WEAKENED CHECK DOES NOT
    ENFORCE THE PROTOCOL ... ensure [offline fixtures] cannot supply a production
    preflight receipt. Verify the refusal THROUGH THE ACTUAL PREFLIGHT PATH with
    stubbed clocks."

    Inherits the real freeze-tree harness, so these drive `orch.preflight`
    exactly as the other binding tests do -- with only `time.sleep` stubbed, so
    no test sleeps ten seconds to prove a ten-second rule.
    """

    def _pf(self, **rt_extra):
        ctx = self._ctx()
        ctx.cfg['_runtime'].update(rt_extra)
        with mock.patch.object(orch.time, 'sleep'):
            try:
                return orch.preflight(ctx), None, ctx
            except Exception as exc:                       # noqa: BLE001
                return None, exc, ctx

    def test_production_with_a_SHORT_window_is_refused(self):
        _, exc, _ = self._pf(clock_window_s=0.01, preflight_mode='production')
        self.assertIsNotNone(exc, 'a short production window was not refused')
        self.assertIn('clock_equivalence', str(exc))

    def test_production_is_the_DEFAULT_so_a_forgetful_runtime_is_strict(self):
        """A runtime that does not say what it is must not be read as offline."""
        ctx = self._ctx()
        ctx.cfg['_runtime'].pop('preflight_mode', None)
        ctx.cfg['_runtime']['clock_window_s'] = 0.01
        with mock.patch.object(orch.time, 'sleep'):
            with self.assertRaises(Exception) as caught:
                orch.preflight(ctx)
        self.assertIn('clock_equivalence', str(caught.exception))

    def test_an_offline_fixture_may_shorten_it_and_is_MARKED(self):
        _, exc, ctx = self._pf(clock_window_s=0.01,
                               preflight_mode='offline_fixture')
        rec = ctx.cfg['_runtime']['clock_equivalence']
        self.assertTrue(rec['below_protocol_window'])
        self.assertEqual(rec['preflight_mode'], 'offline_fixture')
        self.assertFalse(rec['production_receipt'],
                         'a shortened window must not yield a production receipt')
        if exc is not None:
            self.assertNotIn('clock_equivalence', str(exc))

    def test_the_protocol_window_yields_a_production_receipt(self):
        _, _, ctx = self._pf(clock_window_s=orch.CLOCK_WINDOW_PROTOCOL_S,
                             preflight_mode='production')
        rec = ctx.cfg['_runtime']['clock_equivalence']
        self.assertEqual(rec['window_s_effective'], 10.0)
        self.assertFalse(rec['below_protocol_window'])
        self.assertTrue(rec['production_receipt'])

    def test_the_effective_metadata_survives_the_call(self):
        """`runtime(cfg)` returns a COPY. The previous cycle wrote the clock
        record into that copy, so the value I reported as "recorded" vanished the
        moment preflight returned."""
        _, _, ctx = self._pf(clock_window_s=orch.CLOCK_WINDOW_PROTOCOL_S,
                             preflight_mode='production')
        self.assertIn('clock_equivalence', ctx.cfg['_runtime'])

    def test_the_refusal_names_the_window_not_just_a_reason_code(self):
        _, exc, _ = self._pf(clock_window_s=0.01, preflight_mode='production')
        self.assertIsNotNone(exc)
        rows = [d for d in (getattr(exc, 'drift', None) or [])
                if d.get('item') == 'clock_window_s']
        self.assertTrue(rows or 'clock_window_s' in str(exc),
                        'the refusal names only a reason code, not which clock '
                        'rule failed')

    def test_the_closed_reason_vocabulary_is_not_widened(self):
        """The refusal reuses `clock_equivalence` rather than adding a code to
        E_PREFLIGHT, which is a G1 CLOSED vocabulary."""
        import lab_eventlog
        codes = set(lab_eventlog.E_PREFLIGHT.enum or ())
        self.assertIn('clock_equivalence', codes)
        self.assertNotIn('clock_window_below_protocol', codes)


class RuntimeCopySweepTests(unittest.TestCase):
    """`lab_orchestrator.runtime(cfg)` returns a COPY, so any `rt[...] = ...`
    write into it vanishes when the function returns.

    I proposed this sweep to root after the clock record was lost that way. It
    found one sibling: `rt['drift']` in `run_trial`, which no code anywhere
    reads -- the loss was invisible precisely because nothing consumed it.
    """

    def test_runtime_really_does_return_a_copy(self):
        """The premise, asserted rather than assumed."""
        cfg = {'_runtime': {'a': 1}}
        rt = orch.runtime(cfg)
        rt['b'] = 2
        self.assertNotIn('b', cfg['_runtime'],
                         'runtime() no longer returns a copy; this whole class of '
                         'defect changes shape and the sweep must be redone')

    def test_no_write_into_a_runtime_copy_survives_unnoticed(self):
        """Every `rt[...] = ` site in the package is either bound to the REAL
        block or accompanied by a persisting write. A new one added without
        either will fail here."""
        import re
        src = Path(orch.__file__).read_text('utf-8')
        # sites where rt came from runtime(...) -- those need a sibling persist
        for m in re.finditer(r"rt\['(\w+)'\] = ", src):
            name = m.group(1)
            if name in ('results_root', 'work_root', 'mock', 'ports', 'max_pairs'):
                continue                      # bound to cfg.setdefault, verified
            with self.subTest(field=name):
                self.assertIn("setdefault('_runtime', {})['%s']" % name, src,
                              'rt[%r] is written into a runtime() COPY with no '
                              'persisting write; it will vanish silently' % name)

    def test_the_drift_copy_now_persists(self):
        cfg = {'_runtime': {}}
        ctx = types.SimpleNamespace(cfg=cfg)
        ctx.cfg.setdefault('_runtime', {})['drift'] = [{'item': 'x'}]
        self.assertEqual(cfg['_runtime']['drift'], [{'item': 'x'}])

    def test_nothing_reads_the_drift_copy_and_that_is_recorded(self):
        """The repair does not claim a consequence it does not have."""
        src = Path(orch.__file__).read_text('utf-8')
        self.assertIn('NOTHING READS IT TODAY', src)


class TmpdirPolicyTests(unittest.TestCase):
    """The shared TMPDIR policy, in lab_common and wired to the worker.

    Root, 2026-09-22: "Move the shared stdlib directory checks to lab_common ...
    The owner must implement/move the one shared stdlib policy and wire the
    actual production caller." Protocol 5.7 item 2 is in the passive voice and
    nothing checked it: a run that forgets to export TMPDIR silently gets the
    ambient one and a DIFFERENT Seatbelt profile digest, with no error. That is
    not hypothetical -- an ambient-TMPDIR digest was once promoted into
    config.json, ARCHITECTURE 6.1 and protocol Appendix B before anyone noticed.
    """

    GOOD = {'sandbox': {'tmpdir': '<TMP>/labsbx'}}

    def test_a_configuration_that_prescribes_something_else_is_refused(self):
        for bad in ({}, {'sandbox': {}}, {'sandbox': {'tmpdir': '/tmp/other'}}):
            with self.subTest(bad=bad):
                with self.assertRaises(lab_common.PreflightError):
                    lab_common.prescribed_tmpdir(bad)

    def test_the_prescribed_directory_is_derived_not_guessed(self):
        self.assertEqual(lab_common.prescribed_tmpdir(self.GOOD),
                         '/private/tmp/labsbx')

    def test_a_wrong_ambient_tmpdir_is_refused_and_says_how_to_fix_it(self):
        with mock.patch.object(lab_common.tempfile, 'gettempdir',
                               return_value='/var/folders/whatever'):
            with self.assertRaises(lab_common.PreflightError) as c:
                lab_common.assert_tmpdir(self.GOOD, stage='unit')
        msg = str(c.exception)
        self.assertIn('Seatbelt profile digest is a function of TMPDIR', msg)
        self.assertIn('/private/tmp/labsbx', msg)

    def test_the_right_tmpdir_passes(self):
        with mock.patch.object(lab_common.tempfile, 'gettempdir',
                               return_value='/private/tmp/labsbx'):
            got = lab_common.assert_tmpdir(self.GOOD, stage='unit')
        self.assertTrue(got['checked'])

    def test_lab_prepare_delegates_and_keeps_no_second_implementation(self):
        src = inspect.getsource(lab_prepare.assert_prescribed_tmpdir)
        self.assertIn('lab_common.assert_tmpdir', src)
        self.assertNotIn("declared != PRESCRIBED_TMPDIR_TOKEN", src)

    # -- the real worker body ------------------------------------------------
    def _job(self, with_tmpdir=True):
        cfg = {'sandbox': {'timeout_s': 10.0}}
        if with_tmpdir:
            cfg['sandbox']['tmpdir'] = lab_common.PRESCRIBED_TMPDIR_TOKEN
        return {'cfg': cfg, 'paths': {'spool': '<WORK>/x.jsonl'}}

    def test_the_real_run_job_refuses_a_wrong_TMPDIR_before_the_spool(self):
        import lab_worker
        with mock.patch.object(lab_common.tempfile, 'gettempdir',
                               return_value='/var/folders/whatever'):
            with mock.patch.object(lab_worker, 'Spool') as spool:
                with self.assertRaises(lab_common.PreflightError):
                    lab_worker.run_job(self._job(), sandbox_lock_path=Path('/dev/null'))
        spool.assert_not_called()

    def test_the_real_run_job_PROCEEDS_on_the_right_TMPDIR(self):
        """The control: the check must not be a blanket refusal."""
        import lab_worker
        with mock.patch.object(lab_common.tempfile, 'gettempdir',
                               return_value='/private/tmp/labsbx'):
            with mock.patch.object(lab_worker, 'Spool') as spool:
                spool.side_effect = RuntimeError('reached the spool')
                with self.assertRaises(Exception) as c:
                    lab_worker.run_job(self._job(), sandbox_lock_path=Path('/dev/null'))
        self.assertNotIsInstance(c.exception, lab_common.PreflightError)
        spool.assert_called()

    def test_a_job_without_the_sandbox_key_is_not_a_TMPDIR_failure(self):
        """A job shape with no tmpdir declaration is a configuration error
        surfaced elsewhere, not silently reported as a TMPDIR refusal."""
        import lab_worker
        with mock.patch.object(lab_common.tempfile, 'gettempdir',
                               return_value='/var/folders/whatever'):
            with mock.patch.object(lab_worker, 'Spool') as spool:
                spool.side_effect = RuntimeError('reached the spool')
                with self.assertRaises(Exception) as c:
                    lab_worker.run_job(self._job(with_tmpdir=False),
                                       sandbox_lock_path=Path('/dev/null'))
        self.assertNotIsInstance(c.exception, lab_common.PreflightError)

    def test_the_worker_fixture_now_matches_production(self):
        """tests_lab_serving.WorkerTests.make_job built a sandbox block with no
        tmpdir key while production jobs carry one -- which is exactly why this
        check could not be wired without updating the fixture in the same
        change."""
        src = Path(lab_common.HERE / 'tests_lab_serving.py').read_text('utf-8')
        self.assertIn("'tmpdir': lab_common.PRESCRIBED_TMPDIR_TOKEN", src)


class SandwichAuditAndLabelTests(unittest.TestCase):
    """Protocol 12.6 item 4, and the label limb this repository declared and
    never evaluated.

    `config.integrity_label_rule` carries THREE limbs -- coin_adjacent_events,
    sandwich_violations, pairs_with_terminal_failure -- and
    `build_live_ab_results` computed the label from the first and the third
    only. A trial whose ONLY integrity signal was a sandwich violation would
    have been reported as NOT integrity-qualified.
    """

    def setUp(self):
        import build_live_ab_results as B
        self.B = B

    def _receipt(self, seq, created_at, t_wall_ns):
        return {'type': 'anchor_receipt', 'seq': seq, 't_wall_ns': t_wall_ns,
                'body': {'anchor_seq': seq, 'created_at': created_at}}

    # -- the refusal when the second term is not pinned ---------------------
    def test_an_unpinned_p95_makes_the_audit_REFUSE_not_assume_zero(self):
        a = self.B.sandwich_audit([], 30, None)
        self.assertFalse(a['computable'])
        self.assertIsNone(a['violations'])
        self.assertIn('UNKNOWN, not zero', a['reason'])

    def test_an_uncomputable_limb_does_not_make_the_label_False(self):
        """"Not integrity-qualified" is not a conclusion an unevaluated limb
        supports."""
        src = inspect.getsource(self.B)
        self.assertIn('label_determined = sandwich[\'computable\'] or label', src)
        self.assertIn('integrity_label_caveat', src)

    # -- the arithmetic ------------------------------------------------------
    def test_a_constant_offset_cancels_in_the_difference_of_differences(self):
        """The audit is stated on consecutive pairs precisely so a fixed clock
        offset disappears. Shift every server stamp by +600 s and the verdict
        must not move."""
        base = [self._receipt(1, '2026-09-22T00:00:00Z', 0),
                self._receipt(2, '2026-09-22T00:00:10Z', 10_000_000_000)]
        shifted = [self._receipt(1, '2026-09-22T00:10:00Z', 0),
                   self._receipt(2, '2026-09-22T00:10:10Z', 10_000_000_000)]
        a = self.B.sandwich_audit(base, 30, 1.0)
        b = self.B.sandwich_audit(shifted, 30, 1.0)
        self.assertEqual(a['violation_count'], b['violation_count'])
        self.assertEqual(a['rows'][0]['difference_s'], b['rows'][0]['difference_s'])

    def test_a_violation_is_detected_past_the_tolerance(self):
        ev = [self._receipt(1, '2026-09-22T00:00:00Z', 0),
              self._receipt(2, '2026-09-22T00:01:00Z', 0)]   # 60 s server, 0 s wall
        a = self.B.sandwich_audit(ev, 30, 1.0)
        self.assertEqual(a['violation_count'], 1)
        self.assertGreater(a['rows'][0]['difference_s'], a['tolerance_s'])

    def test_within_tolerance_is_not_a_violation(self):
        ev = [self._receipt(1, '2026-09-22T00:00:00Z', 0),
              self._receipt(2, '2026-09-22T00:00:10Z', 8_000_000_000)]
        a = self.B.sandwich_audit(ev, 30, 1.0)
        self.assertEqual(a['violation_count'], 0)

    def test_a_missing_or_unparsable_stamp_is_SKIPPED_not_counted_as_clean(self):
        ev = [self._receipt(1, None, 0),
              self._receipt(2, '2026-09-22T00:00:10Z', 10_000_000_000)]
        a = self.B.sandwich_audit(ev, 30, 1.0)
        self.assertIn('skipped', a['rows'][0])
        self.assertEqual(a['violation_count'], 0)
        self.assertEqual(a['pairs_compared'], 1)   # the pair is COUNTED as examined

    # -- the gap report ------------------------------------------------------
    def test_a_gap_covered_by_an_open_llm_request_is_not_reported(self):
        """Finding N3's false-FAIL case, on an event pair the chain ACTUALLY has.
        The first version of this test used sandbox_started/sandbox_ended, which
        are not in the vocabulary at all -- so it asserted the behaviour of a
        string that could never match."""
        ev = [{'type': 'llm_request', 'seq': 1, 't_wall_ns': 0,
               'body': {'request_id': 'A'}},
              {'type': 'llm_response', 'seq': 2, 't_wall_ns': 10_000_000_000,
               'body': {'request_id': 'A'}}]
        g = self.B.gap_report(ev, 5.0)
        self.assertTrue(g['computable'])
        self.assertEqual(g['gaps_above_threshold'], 1)
        self.assertEqual(g['covered_gaps'], 1)
        self.assertEqual(g['reported_gaps'], [])

    def test_an_uncovered_gap_IS_reported(self):
        ev = [{'type': 'pair_enrolled', 'seq': 1, 't_wall_ns': 0},
              {'type': 'pair_enrolled', 'seq': 2, 't_wall_ns': 10_000_000_000}]
        g = self.B.gap_report(ev, 5.0)
        self.assertEqual(len(g['reported_gaps']), 1)
        self.assertAlmostEqual(g['reported_gaps'][0]['seconds'], 10.0)

    def test_a_gap_below_the_threshold_is_not_a_gap(self):
        ev = [{'type': 'pair_enrolled', 'seq': 1, 't_wall_ns': 0},
              {'type': 'pair_enrolled', 'seq': 2, 't_wall_ns': 3_000_000_000}]
        self.assertEqual(self.B.gap_report(ev, 5.0)['gaps_above_threshold'], 0)

    # -- the limb is actually wired -----------------------------------------
    def test_the_sandwich_limb_is_read_from_the_config_rule(self):
        src = inspect.getsource(self.B)
        self.assertIn("rule.get('sandwich_violations'", src)
        self.assertIn('or sandwich_limb', src)


class GapReportVocabularyTests(unittest.TestCase):
    """I invented the opener/closer names from the protocol's prose and three of
    six did not exist in the chain vocabulary. Checking them against the schema
    was my own stated next step, and it found two bugs in OPPOSITE directions.
    """

    def setUp(self):
        import build_live_ab_results as B
        import lab_eventlog as E
        self.B = B
        self.vocab = set(E.TRIAL_ONLY_TYPES) | set(E.PROGRAM_ONLY_TYPES)

    def test_every_name_in_the_coverage_map_exists_in_the_chain(self):
        """The guard that would have caught the invention immediately."""
        self.assertEqual(self.B._validate_coverage_map(self.vocab), [])

    def test_the_names_I_invented_are_NOT_in_the_vocabulary(self):
        """Recorded so the finding is not lost: these were in the shipped code."""
        for invented in ('sandbox_started', 'sandbox_ended',
                         'metrics_scrape_started', 'metrics_scrape_ended'):
            with self.subTest(invented=invented):
                self.assertNotIn(invented, self.vocab)

    def test_an_invented_name_makes_the_report_REFUSE_not_silently_miss(self):
        real = dict(self.B.COVERAGE_MAP)
        try:
            self.B.COVERAGE_MAP.clear()
            self.B.COVERAGE_MAP['sandbox_started'] = (('sandbox_ended',), 'arrival')
            g = self.B.gap_report([], 5.0, vocabulary=self.vocab)
            self.assertFalse(g['computable'])
            self.assertIn('the chain does not have', g['reason'])
        finally:
            self.B.COVERAGE_MAP.clear()
            self.B.COVERAGE_MAP.update(real)

    def test_llm_error_closes_a_request_so_later_gaps_are_not_falsely_covered(self):
        """THE DANGEROUS DIRECTION. A missing closer leaves the opener open for
        ever, so every subsequent gap reads as COVERED and the report
        under-reports. llm_error is a real closer I had omitted."""
        ev = [{'type': 'llm_request', 'seq': 1, 't_wall_ns': 0,
               'body': {'request_id': 'A'}},
              {'type': 'llm_error', 'seq': 2, 't_wall_ns': 1_000_000_000,
               'body': {'request_id': 'A'}},
              {'type': 'pair_enrolled', 'seq': 3, 't_wall_ns': 30_000_000_000,
               'body': {}}]
        g = self.B.gap_report(ev, 5.0, vocabulary=self.vocab)
        self.assertEqual(g['still_open_at_end'], {})
        self.assertEqual(len(g['reported_gaps']), 1,
                         'the gap after an ERRORED request must be reported')

    def test_the_unrepresentable_coverers_are_named_not_dropped(self):
        """Protocol 12.6 item 4 names a sandbox execution and a /metrics scrape as
        coverers; the vocabulary has no interval for either. That is stated in the
        report rather than letting their gaps read as plain unexplained ones."""
        g = self.B.gap_report([], 5.0, vocabulary=self.vocab)
        self.assertIn('sandbox execution', g['unrepresented_coverers'])
        self.assertIn('/metrics scrape', g['unrepresented_coverers'])
        self.assertIn('UNEXPLAINED-BY-THIS-CHECK', g['limits'])

    def test_metrics_scrape_is_a_point_event_not_a_pair(self):
        self.assertIn('metrics_scrape', self.vocab)
        self.assertNotIn('metrics_scrape', self.B.COVERAGE_MAP)


class GapCoverageIdentityTests(unittest.TestCase):
    """Coverage is paired by IDENTITY, not counted by type.

    The type-counting version let one interval close another: an
    `orphan_rejected` for arrival 2 decremented the `episode_started` counter
    opened by arrival 1. With two workers these interleave constantly.

    The authoritative pairing already existed in `lab_verify_log`:
    `calls.one_terminal` keys llm_request against llm_response/llm_error by
    `request_id`, and the episode checks key by `arrival`. This mirrors it rather
    than inventing a second convention that could disagree with the verifier.
    """

    def setUp(self):
        import build_live_ab_results as B
        import lab_eventlog as E
        self.B = B
        self.vocab = set(E.TRIAL_ONLY_TYPES) | set(E.PROGRAM_ONLY_TYPES)

    def _ev(self, typ, seq, secs, **body):
        return {'type': typ, 'seq': seq, 't_wall_ns': int(secs * 1e9), 'body': body}

    def test_a_terminal_for_ANOTHER_identity_does_not_close_this_one(self):
        """The exact defect. Arrival 1's episode must stay open."""
        ev = [self._ev('episode_started', 1, 0, arrival=1),
              self._ev('orphan_rejected', 2, 1, arrival=2),
              self._ev('pair_enrolled', 3, 30)]
        g = self.B.gap_report(ev, 5.0, vocabulary=self.vocab)
        self.assertEqual(g['still_open_at_end'], {'episode_started': ['1']})
        self.assertEqual(len(g['reported_gaps']), 0,
                         "arrival 1's episode is genuinely open, so the gap IS "
                         'covered')
        self.assertEqual(len(g['unmatched_terminals']), 1)
        self.assertIn('no matching open', g['unmatched_terminals'][0]['problem'])

    def test_interleaved_concurrent_requests_pair_correctly(self):
        """Two workers, two requests in flight, terminals out of order."""
        ev = [self._ev('llm_request', 1, 0, request_id='A'),
              self._ev('llm_request', 2, 1, request_id='B'),
              self._ev('llm_response', 3, 2, request_id='B'),
              self._ev('llm_response', 4, 3, request_id='A'),
              self._ev('pair_enrolled', 5, 40)]
        g = self.B.gap_report(ev, 5.0, vocabulary=self.vocab)
        self.assertEqual(g['still_open_at_end'], {})
        self.assertEqual(g['unmatched_terminals'], [])
        self.assertEqual(len(g['reported_gaps']), 1,
                         'both requests closed, so the later gap is uncovered')

    def test_one_open_request_covers_the_gap_while_its_partner_is_closed(self):
        ev = [self._ev('llm_request', 1, 0, request_id='A'),
              self._ev('llm_request', 2, 1, request_id='B'),
              self._ev('llm_error', 3, 2, request_id='B'),
              self._ev('pair_enrolled', 4, 40)]
        g = self.B.gap_report(ev, 5.0, vocabulary=self.vocab)
        self.assertEqual(g['still_open_at_end'], {'llm_request': ['A']})
        self.assertEqual(len(g['reported_gaps']), 0)

    def test_an_opener_without_its_identity_field_is_flagged(self):
        ev = [self._ev('llm_request', 1, 0),          # no request_id
              self._ev('pair_enrolled', 2, 40)]
        g = self.B.gap_report(ev, 5.0, vocabulary=self.vocab)
        self.assertTrue(any('opener carries no' in u['problem']
                            for u in g['unmatched_terminals']))
        self.assertEqual(len(g['reported_gaps']), 1,
                         'an opener we cannot identify must not cover anything')

    def test_the_identity_fields_match_the_verifier_s_own_keys(self):
        """lab_verify_log keys llm_request by request_id and episodes by arrival.
        A second pairing convention that disagreed with the verifier would be the
        same class of error in a different place."""
        self.assertEqual(self.B.COVERAGE_MAP['llm_request'][1], 'request_id')
        self.assertEqual(self.B.COVERAGE_MAP['episode_started'][1], 'arrival')
        src = Path(lab_common.HERE / 'lab_verify_log.py').read_text('utf-8')
        self.assertIn("rid = ev['body']['request_id']", src)
        self.assertIn("('llm_response', 'llm_error')", src)
