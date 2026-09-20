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
import json
import os
import re
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
    """The roster with no exclusion at all: 591 S1 + 547 S2, so N_P = 295 + 273 = 568."""
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

    def test_order_document_horizon(self):
        roster = full_roster()
        document = lab_design.order_document(roster, 'T4', DESIGN_SEED_BASE)
        self.assertEqual(document['n_pairs'], 568)
        self.assertEqual(len(document['pairs']), 568)
        self.assertEqual(document['trial_no'], 4)
        self.assertEqual(document['roster_sha256'], roster['roster_sha256'])
        self.assertEqual(len(document['leftovers']), 2)          # 591 and 547 are both odd

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
            (lab_data, 'sweep_references'): ['tasks', 'cfg', 'on_progress'],
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
