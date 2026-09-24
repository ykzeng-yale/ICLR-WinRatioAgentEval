"""The harness pin successor of the EB1+EB5 subset: exact old/new pins, prior observations kept.

    harness_pin_successor.py [--repo DIR] [--predecessor REV] [--out-dir DIR] [--no-suites]

Root 20:40 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:16``, EB1 route (a)): "The
orchestrator is in the harness pin: record the pre-outcome pin successor and preserve the old
pin and all prior observations."  Root 21:14 (reviews/restart_cap_estimand_ruling_20260923_2114.md
on main, item 2): send the EB1 lifecycle and EB5 resolution code and controls "with old/new
hashes and no loaded run".  Root 07:03 (reviews/eb1_fixture_and_wip_delta_20260924_0703.md on
main, items 1 and 3): for the compiled C test double "retain the C source, compiler/version,
source digest and exact control result"; "A missing temp cache must rebuild or make the control
fail visibly"; "run controls alone, and submit one immutable exact-pinned subset with
completed/planned counts, failures, resource use and timestamps".

WHAT IT COMPUTES, WITHOUT EDITING ANY EXISTING FILE (every value from git objects unless named):

1. The predecessor harness map at PREDECESSOR (b049307) with ``lab_common.harness_file_hashes``
   semantics -- the top-level ``experiments/live_ab/*.py`` files plus ``config.json``, sha256 of
   each file's bytes -- read from ``git`` blobs; its canonical digest (``lab_common.
   sha256_canonical`` of the name -> sha256 map) must be PREDECESSOR_CANONICAL (5675cc5e, 33
   entries) or the tool REFUSES.  A revision git cannot resolve REFUSES (``predecessor_missing``).
2. The successor map at HEAD, checked equal to ``lab_common.harness_file_hashes()`` imported
   from the working tree of ``--repo`` (a clean tree is required, so the two must agree).
3. Per changed or added harness entry: old sha256, new sha256, the sha256 of its unified diff
   (DIFF_ARGV, fixed options, user git configuration ignored), line counts, the commits of
   ``PREDECESSOR..HEAD`` that touch it, and a check that ``git apply`` of that diff to the old
   bytes reproduces the new bytes.  The same for every other file the subset changes.
4. REUSED_FILES (``experiments/local_stream``) digests at both revisions (must be unchanged);
   the five decision-defining modules byte-unchanged; the rule block (must be RULE_BLOCK at both
   revisions); config.json, ARCHITECTURE_FINAL.md, protocol_FINAL.md, cells.json and the real
   serving manifest old/new, cross-checked against the synchronized amendment's receipt.
5. The prior observations that are NOT reissued (PRIOR_OBSERVATIONS): each file's sha256, and
   every 64-hex value it carries classified against the b049307/HEAD digests of the tracked
   files (which of its pins moved, which did not, which were already historical at b049307).
6. The compiled C test double (``experiments/live_ab_controls/sm_fixture.py``): its C sources
   (string constants of that committed file) with their sha256, the compile argv, the compiler
   path and ``clang --version``; checks that its outputs appear nowhere in the freeze tree; and
   five missing-cache controls under isolated temporary roots (never the shared cache).
7. Unless ``--no-suites``: the five suites, run one after another (never two at once), each
   with its exact argv, planned (loader) and completed (``Ran``) counts, verdict line, skip
   reasons, failure headers, wall time, start/end UTC, child rusage, host snapshots before and
   after, and a ``ps`` sampler that lists any watched process outside the suite's own tree
   (the evidence that it ran alone; sampled, not continuous; a process the suite itself
   orphans is told apart from a foreign one, see ``watched_outside``).

It writes ONE write-once receipt ``<out-dir>/HARNESS_PIN_SUCCESSOR_<UTC>.json``.  The default
out-dir is ``results/live_ab``; ``--no-suites`` is refused there, so a receipt in results always
carries the solo-run suites.  Every refusal names its problems and writes nothing.

Nothing here starts a model, a llama-server, a llama.cpp build or a network request.  It
compiles the C test double (root 07:03 item 1 authorizes that fixture) under temporary roots,
and the suites it runs start their own loopback mocks.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Mapping

HERE = Path(__file__).resolve().parent
DEFAULT_REPO = HERE.parent.parent
RESULTS_REL = 'results/live_ab'
SCHEMA = 'live_ab/harness_pin_successor-v1'
STATUS = 'PROPOSED pre-outcome pin successor for root review; not a freeze'
PY = sys.executable

#: The reviewed predecessor revision (root 20:40 reviewed this head) and its harness map.
PREDECESSOR = 'b049307ff62153a054f61b6179291ba987de2ba1'
PREDECESSOR_COUNT = 33
PREDECESSOR_CANONICAL = '5675cc5ef970328834314480ec33d0edf237f38c1a3d977d3d22e93dc71f3fee'
#: The rule block (lab_common.RULE_BLOCK_KEYS) of the b049307 config.json; must not move.
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
LIVE_REL = 'experiments/live_ab'
REUSED_REL = 'experiments/local_stream'
CONFIG_REL = LIVE_REL + '/config.json'
DOCUMENTS = {
    'config.json': (CONFIG_REL,
                    'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824'),
    'ARCHITECTURE_FINAL.md': (LIVE_REL + '/design/ARCHITECTURE_FINAL.md',
                              '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab'),
    'protocol_FINAL.md': (LIVE_REL + '/design/protocol_FINAL.md',
                          '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b'),
    'cells.json': ('experiments/live_ab_validation/cells.json',
                   '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'),
}
VOCABULARY_ORIGINAL = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
SERVING_MANIFEST_REL = RESULTS_REL + '/freeze/serving_manifest.json'
AMENDMENT_COMMIT = '474f9d82aae2b3979910d8a99d8305b5d7bc44c1'
AMENDMENT_RECEIPT_REL = RESULTS_REL + '/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
#: Decision-defining modules the restart cap must not touch (root 21:14, cap invariance).
DECISION_MODULES = ('lab_coin.py', 'lab_design.py', 'lab_enclosure.py', 'lab_monitor.py',
                    'lab_reference_rule.py')
#: Prior observations kept, NOT reissued by this successor.
PRIOR_OBSERVATIONS = (
    RESULTS_REL + '/SMOKE_RECEIPT_smoke_4167e395ccfd.json',
    RESULTS_REL + '/PROSPECTIVE_LAUNCH_RECORD_20260923_1922.json',
    RESULTS_REL + '/PROSPECTIVE_LAUNCH_RECORD_20260923_2030.json',
    RESULTS_REL + '/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json',
    RESULTS_REL + '/PRE_RUN_BUNDLE_20260923_2035.json',
    RESULTS_REL + '/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json',
    RESULTS_REL + '/PATCH_STATE_AMENDMENT_RECEIPT_20260923_1933.json',
)
#: Committed statements of the harness count/state at b049307 (path, line, fragment it carries).
COUNT_STATEMENTS = (
    (RESULTS_REL + '/ABSENT_DRAIN_AND_REQUEST_RECONCILIATION.json', 33, '33 (32'),
    (RESULTS_REL + '/LAUNCH_WIRING.json', 41, '"33, unchanged"'),
    (RESULTS_REL + '/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json', 123, '"harness_files": 33'),
    (RESULTS_REL + '/PATCH_STATE_AMENDMENT_RECEIPT_20260923_1933.json', 169,
     '"harness_file_hashes_unchanged": true'),
)
#: Where pins are looked up (tracked files at both revisions, recursive).
TRACKED_PREFIXES = ('experiments/live_ab', 'experiments/live_ab_serving',
                    'experiments/live_ab_validation', 'experiments/live_ab_tools',
                    'experiments/live_ab_controls', 'experiments/local_stream',
                    'results/live_ab', 'src/winstats.py')
OWN_FILES = ('experiments/live_ab_tools/harness_pin_successor.py',
             'experiments/live_ab_tools/tests_harness_pin_successor.py')
FIXTURE_REL = 'experiments/live_ab_controls/sm_fixture.py'
FIXTURE_CONTROL_TESTS = (
    'tests_sm_manifest.RuntimeTests.test_control_the_unchanged_build_reverifies',
    'tests_sm_manifest.RuntimeTests.test_one_library_byte_changed_after_assembly_refuses')
PRESCRIBED_LABSBX = '/private/tmp/labsbx'
FIXTURE_CONTROL_TAGS = ('A_rebuild', 'B_no_compiler', 'C_partial_cache',
                        'D_real_control_rebuilds', 'E_real_control_no_compiler')

#: The unified-diff form whose bytes are hashed (every option fixed; see git_env()).
DIFF_ARGV = ('-c', 'core.quotePath=true', '-c', 'diff.noprefix=false',
             '-c', 'diff.mnemonicPrefix=false', '-c', 'diff.suppressBlankEmpty=false',
             'diff', '--no-color', '--no-ext-diff', '--no-textconv', '--full-index',
             '--no-renames', '--no-relative', '--diff-algorithm=myers', '--indent-heuristic',
             '--inter-hunk-context=0', '--src-prefix=a/', '--dst-prefix=b/', '--unified=3')

SUITES = (
    ('live_ab', ['-m', 'unittest', 'discover', '-v', '-s', 'experiments/live_ab',
                 '-p', 'tests_*.py']),
    ('live_ab_controls', ['-m', 'unittest', 'discover', '-v', '-s',
                          'experiments/live_ab_controls', '-p', 'tests_*.py']),
    ('live_ab_serving', ['-m', 'unittest', 'discover', '-v', '-s',
                         'experiments/live_ab_serving', '-p', 'tests_*.py']),
    ('live_ab_tools', ['-m', 'unittest', 'discover', '-v', '-s', 'experiments/live_ab_tools',
                       '-p', 'tests_*.py']),
    ('live_ab_validation', ['experiments/live_ab_validation/tests_validation.py']),
)
SUITE_TIMEOUT_S = 3 * 3600
SAMPLE_EVERY_S = 2.0
WATCH = ('unittest', 'tests_', 'llama-server', 'llama_server', 'lab_orchestrator',
         'lab_mock_server', 'run_smoke', 'run_live_ab', 'ninja', 'cmake', 'mlx_lm', 'ollama',
         'vllm')

HEX64 = re.compile(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])')


class Refused(Exception):
    """The tool refuses; ``problems`` names every reason.  No receipt is written; a receipt
    already assembled (``draft``) is saved by main() under the temporary directory only, for
    diagnosis, never under results/."""

    def __init__(self, problems: Iterable[str], draft: dict | None = None) -> None:
        self.problems = sorted(set(problems))
        self.draft = draft
        super().__init__('refused: ' + ', '.join(self.problems))


# --------------------------------------------------------------------------- #
# hashing, canonical JSON, git
# --------------------------------------------------------------------------- #
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: object) -> str:
    """``lab_common.canonical_json`` (checked equal in LabCommonAgreementTests)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def sha256_canonical(obj: object) -> str:
    return sha256(canonical_json(obj).encode('utf-8'))


def git_env() -> dict:
    """The environment of every git call: no GIT_* variable of the caller (no injected
    ``GIT_CONFIG_*``, and no ``GIT_DIFF_OPTS``, which OVERRIDES ``--unified`` on the command
    line), no global or system configuration or attributes, C locale."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               LC_ALL='C', GIT_PAGER='cat')
    return env


def git(repo: Path, *args: str, check: bool = True, stdin: bytes | None = None) -> bytes:
    res = subprocess.run(['git', '-C', str(repo), *args], input=stdin, capture_output=True,
                         env=git_env(), timeout=600, check=False)
    if check and res.returncode != 0:
        raise Refused(['git_failed:%s' % ' '.join(args[:3])])
    return res.stdout


def resolve(repo: Path, rev: str) -> str | None:
    res = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet',
                          rev + '^{commit}'], capture_output=True, env=git_env(), timeout=60,
                         check=False)
    out = res.stdout.decode().strip()
    return out if res.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', out) else None


class GitTree:
    """Read-only view of one commit: top-level listing of a directory and blob bytes."""

    def __init__(self, repo: Path, rev: str) -> None:
        self.repo = Path(repo)
        sha = resolve(self.repo, rev)
        if sha is None:
            raise Refused(['revision_missing:%s' % rev])
        self.rev = sha

    def entries(self, directory: str) -> list:
        """``(mode, type, name)`` of the direct children of ``directory``."""
        out = git(self.repo, 'ls-tree', '-z', '--full-tree', self.rev, '--',
                  directory.rstrip('/') + '/')
        rows = []
        for rec in out.split(b'\0'):
            if not rec:
                continue
            meta, path = rec.split(b'\t', 1)
            mode, typ, _oid = meta.decode().split(' ')
            rows.append((mode, typ, path.decode('utf-8').rsplit('/', 1)[-1]))
        return rows

    def read(self, path: str) -> bytes | None:
        res = subprocess.run(['git', '-C', str(self.repo), 'cat-file', 'blob',
                              '%s:%s' % (self.rev, path)], capture_output=True, env=git_env(),
                             timeout=120, check=False)
        return res.stdout if res.returncode == 0 else None


def harness_names_from_git(tree: GitTree) -> tuple[list, list]:
    """(names, problems): ``lab_common._harness_files`` on a commit -- the top-level ``*.py``
    blobs of experiments/live_ab plus ``config.json`` when present, sorted."""
    names, problems = [], []
    for mode, typ, name in tree.entries(LIVE_REL):
        if typ == 'blob' and (name.endswith('.py') or name == 'config.json'):
            if mode == '120000':
                problems.append('symlink_in_harness:%s' % name)
            names.append(name)
    return sorted(names), problems


def harness_map(tree: GitTree) -> dict:
    names, problems = harness_names_from_git(tree)
    if problems:
        raise Refused(problems)
    out = {}
    for name in names:
        data = tree.read('%s/%s' % (LIVE_REL, name))
        if data is None:
            raise Refused(['unreadable_blob:%s' % name])
        out[name] = sha256(data)
    return out


def harness_map_from_dir(directory: Path) -> dict:
    """Exactly ``lab_common._harness_files`` + ``harness_file_hashes`` on a directory."""
    names = sorted(p.name for p in Path(directory).glob('*.py'))
    if (Path(directory) / 'config.json').exists():
        names.append('config.json')
    return {n: sha256((Path(directory) / n).read_bytes()) for n in sorted(names)}


def predecessor_problems(pmap: Mapping) -> list:
    """Why a map is not the reviewed b049307 harness pin ([] when it is)."""
    problems = []
    if len(pmap) != PREDECESSOR_COUNT:
        problems.append('predecessor_count:%d' % len(pmap))
    if sha256_canonical(dict(pmap)) != PREDECESSOR_CANONICAL:
        problems.append('predecessor_digest')
    return problems


def unified_diff(repo: Path, old: str, new: str, path: str) -> bytes:
    return git(repo, *DIFF_ARGV, old, new, '--', path)


def diff_reproduces(old: bytes | None, new: bytes | None, diff: bytes, path: str) -> bool:
    """``git apply`` of ``diff`` (outside any repository) to ``old`` at ``path`` gives
    exactly ``new`` (for a deleted file: nothing)."""
    tmp = Path(tempfile.mkdtemp(prefix='pinsucc_apply_'))
    try:
        work = tmp / 'w'
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if old is not None:
            target.write_bytes(old)
        (tmp / 'd.patch').write_bytes(diff)
        env = git_env()
        env['GIT_CEILING_DIRECTORIES'] = str(tmp)
        res = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-p1',
                              str(tmp / 'd.patch')], cwd=str(work), capture_output=True,
                             env=env, timeout=120, check=False)
        if res.returncode != 0:
            return False
        if new is None:
            return not target.exists()
        return target.is_file() and target.read_bytes() == new
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def diff_entry(repo: Path, old_tree: GitTree, new_tree: GitTree, path: str) -> dict:
    old, new = old_tree.read(path), new_tree.read(path)
    diff = unified_diff(repo, old_tree.rev, new_tree.rev, path)
    text = diff.decode('utf-8', 'replace').splitlines()
    commits = git(repo, 'log', '--format=%H', '%s..%s' % (old_tree.rev, new_tree.rev), '--',
                  path).decode().split()
    return {
        'status': 'added' if old is None else ('deleted' if new is None else 'modified'),
        'old_sha256': None if old is None else sha256(old),
        'new_sha256': None if new is None else sha256(new),
        'old_bytes': None if old is None else len(old),
        'new_bytes': None if new is None else len(new),
        'diff_sha256': sha256(diff),
        'diff_bytes': len(diff),
        'lines_added': sum(1 for ln in text if ln.startswith('+') and not ln.startswith('+++')),
        'lines_removed': sum(1 for ln in text if ln.startswith('-')
                             and not ln.startswith('---')),
        'diff_applied_to_old_gives_new': diff_reproduces(old, new, diff, path),
        'changing_commits': list(reversed(commits)),
    }


def blob_digests(repo: Path, rev: str, prefixes: Iterable[str]) -> dict:
    """path -> sha256 of every blob under ``prefixes`` at ``rev`` (one cat-file batch)."""
    out = git(repo, 'ls-tree', '-r', '-z', '--full-tree', rev, '--', *prefixes)
    rows = []
    for rec in out.split(b'\0'):
        if rec:
            meta, path = rec.split(b'\t', 1)
            _mode, typ, oid = meta.decode().split(' ')
            if typ == 'blob':
                rows.append((path.decode('utf-8'), oid))
    oids = sorted({oid for _p, oid in rows})
    raw = git(repo, 'cat-file', '--batch', stdin=('\n'.join(oids) + '\n').encode())
    by_oid, i = {}, 0
    while i < len(raw):
        nl = raw.index(b'\n', i)
        oid, _typ, size = raw[i:nl].decode().split(' ')
        start = nl + 1
        by_oid[oid] = sha256(raw[start:start + int(size)])
        i = start + int(size) + 1
    return {p: by_oid[oid] for p, oid in rows}


# --------------------------------------------------------------------------- #
# configuration: rule block, tuples read from lab_common source
# --------------------------------------------------------------------------- #
def module_constant(source: bytes, name: str) -> object:
    """The literal value assigned to top-level ``name`` in ``source`` (ast, not import)."""
    for node in ast.parse(source).body:
        targets = ([node.target] if isinstance(node, ast.AnnAssign)
                   else node.targets if isinstance(node, ast.Assign) else [])
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise Refused(['constant_absent:%s' % name])


def rule_block_digest(config: Mapping, keys: Iterable[str]) -> str:
    """``lab_common.rule_block_sha256`` with the given RULE_BLOCK_KEYS."""
    block = {}
    for dotted in keys:
        node: object = config
        for part in dotted.split('.'):
            if not isinstance(node, Mapping) or part not in node:
                raise Refused(['rule_block_key_missing:%s' % dotted])
            node = node[part]
        block[dotted] = node
    return sha256_canonical(block)


LAB_COMMON_PROBE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import lab_common
cfg = json.loads(open(sys.argv[2], encoding='utf-8').read())
print(json.dumps({'harness': lab_common.harness_file_hashes(),
                  'harness_files': list(lab_common.HARNESS_FILES),
                  'reused_files': list(lab_common.REUSED_FILES),
                  'rule_block_keys': list(lab_common.RULE_BLOCK_KEYS),
                  'rule_block': lab_common.rule_block_sha256(cfg),
                  'canonical_of_map': lab_common.sha256_canonical(
                      lab_common.harness_file_hashes()),
                  'server_supervision_cap': lab_common.server_supervision_cap(cfg)}))
'''


def lab_common_view(repo: Path) -> dict:
    """What the working tree's own lab_common computes (a subprocess; nothing imported here)."""
    res = subprocess.run([PY, '-c', LAB_COMMON_PROBE, str(repo / LIVE_REL),
                          str(repo / CONFIG_REL)], capture_output=True, text=True, timeout=300,
                         cwd=str(repo), check=False)
    if res.returncode != 0:
        raise Refused(['lab_common_probe_failed'])
    return json.loads(res.stdout)


# --------------------------------------------------------------------------- #
# prior observations: which pins moved
# --------------------------------------------------------------------------- #
def pins_in(obj: object, path: str = '$') -> list:
    """``(json_path, hex)`` of every 64-hex value inside a string of ``obj``."""
    out = []
    if isinstance(obj, Mapping):
        for k in obj:
            out.extend(pins_in(obj[k], '%s.%s' % (path, k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(pins_in(v, '%s[%d]' % (path, i)))
    elif isinstance(obj, str):
        out.extend((path, h) for h in HEX64.findall(obj))
    return out


def classify_pins(obj: object, table: Mapping, manifest_hexes: frozenset = frozenset(),
                  tokenize: Callable[[str], str] = str,
                  config_hexes: frozenset = frozenset()) -> dict:
    """Classify every pin of a record against ``table`` (artifact -> {'b049307', 'head'}).

    A pin is attributed to the artifact whose repository path its JSON path names (longest
    match), else to every artifact whose b049307 digest it equals.  Attributed and equal to
    that artifact's b049307 digest: ``moved`` if the HEAD digest differs, else ``unchanged``.
    Named but not the b049307 digest: ``already_historical`` (stale before this successor).
    Otherwise ``successor_only`` (equals a HEAD digest only) or
    ``not_a_digest_at_either_revision`` (with whether the real serving manifest, or the HEAD
    config.json, carries it)."""
    pred: dict = {}
    succ: dict = {}
    for art, row in table.items():
        if row.get('b049307'):
            pred.setdefault(row['b049307'], []).append(art)
        if row.get('head'):
            succ.setdefault(row['head'], []).append(art)
    by_artifact: dict = {}
    historical, successor_only, untracked = [], [], []
    pins = pins_in(obj)
    for raw_jp, hx in pins:
        named = max((a for a in table if '/' in a and a in raw_jp), key=len, default=None)
        jp = tokenize(raw_jp)
        if named is not None and table[named].get('b049307') != hx:
            historical.append({'json_path': jp, 'value': hx, 'artifact': named,
                               'b049307': table[named].get('b049307'),
                               'head': table[named].get('head')})
            continue
        arts = [named] if named is not None else pred.get(hx, [])
        if arts:
            for art in arts:
                row = by_artifact.setdefault(art, {
                    'b049307': table[art].get('b049307'), 'head': table[art].get('head'),
                    'moved': table[art].get('b049307') != table[art].get('head'),
                    'json_paths': []})
                row['json_paths'].append(jp)
        elif hx in succ:
            successor_only.append({'json_path': jp, 'value': hx, 'artifacts': succ[hx]})
        else:
            untracked.append({'json_path': jp, 'value': hx,
                              'in_real_serving_manifest': hx in manifest_hexes,
                              'in_successor_config': hx in config_hexes})
    moved = sorted(a for a, r in by_artifact.items() if r['moved'])
    return {'pins_found': len(pins), 'by_artifact': by_artifact, 'moved_artifacts': moved,
            'unchanged_artifacts': sorted(a for a, r in by_artifact.items() if not r['moved']),
            'already_historical': historical, 'successor_only': successor_only,
            'not_a_digest_at_either_revision': untracked}


def record_verdict(c: Mapping) -> str:
    """One sentence from the classification (nothing else is consulted)."""
    parts = []
    if c['moved_artifacts']:
        parts.append('STALE: pins of %d artifact(s) moved between b049307 and HEAD (%s)'
                     % (len(c['moved_artifacts']), ', '.join(c['moved_artifacts'])))
    else:
        parts.append('no pin it carries is a b049307 digest that moved')
    if c['unchanged_artifacts']:
        parts.append('%d pinned artifact(s) unchanged' % len(c['unchanged_artifacts']))
    if c['already_historical']:
        parts.append('%d pin(s) already historical at b049307 (%s)' % (
            len(c['already_historical']),
            ', '.join(sorted({h['artifact'] for h in c['already_historical']}))))
    other = c['not_a_digest_at_either_revision']
    if other:
        bound = sum(1 for u in other if u['in_real_serving_manifest'])
        conf = sum(1 for u in other if u.get('in_successor_config'))
        parts.append('%d pin(s) are digests of no tracked file at either revision: %d carried '
                     'by the real serving manifest (the durable build), %d by the HEAD '
                     'config.json, %d by neither' % (len(other), bound, conf, sum(
                         1 for u in other if not u['in_real_serving_manifest']
                         and not u.get('in_successor_config'))))
    return '; '.join(parts) + '. Kept as written; not reissued by this successor.'


# --------------------------------------------------------------------------- #
# the compiled C test double (root 07:03 item 1)
# --------------------------------------------------------------------------- #
def fixture_sources(source: bytes) -> dict:
    """From sm_fixture.py (ast only): the C string constants, the file each is written to by
    ``compiled()``, their digests, the compile argv and the cache key formula's value."""
    tree = ast.parse(source)
    consts = {n: module_constant(source, n) for n in ('BASE_C', 'CORE_C', 'LAUNCHER_C')}
    written, argvs = {}, []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == 'compiled':
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'write_text' and node.args
                        and isinstance(node.args[0], ast.Name)
                        and isinstance(node.func.value, ast.BinOp)
                        and isinstance(node.func.value.right, ast.Constant)):
                    written[node.args[0].id] = node.func.value.right.value
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple) and \
                        node.iter.elts and all(isinstance(e, ast.List) for e in node.iter.elts):
                    argvs = [ast.literal_eval(e) for e in node.iter.elts]
    key = hashlib.sha256()
    for name in ('BASE_C', 'CORE_C', 'LAUNCHER_C'):
        key.update(consts[name].encode('utf-8'))
    return {
        'where': ('string constants BASE_C, CORE_C, LAUNCHER_C of the committed %s (no separate '
                  '.c file is tracked); compiled() writes each to the named file in its '
                  'compile directory, UTF-8, then deletes it' % FIXTURE_REL),
        'files': {written.get(n, '?'): {'constant': n, 'bytes': len(v.encode('utf-8')),
                                        'sha256': sha256(v.encode('utf-8'))}
                  for n, v in consts.items()},
        'compile_argv': argvs,
        'sources_key': key.hexdigest()[:16],
        'cache_dir_name': 'eb1c_sm_fixture_%s' % key.hexdigest()[:16],
    }


def run_text(argv: list, timeout: int = 60) -> tuple[int, str]:
    try:
        res = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                             check=False)
        return res.returncode, res.stdout + res.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, 'ERROR %s' % type(exc).__name__


def compiler_record() -> dict:
    rc, version = run_text(['clang', '--version'])
    _rc, xcrun = run_text(['xcrun', '--find', 'clang'])
    _rc, dev = run_text(['xcode-select', '-p'])
    which = shutil.which('clang')
    return {'invoked_as': 'clang (resolved through PATH by subprocess)',
            'which_clang': which, 'which_clang_realpath': which and os.path.realpath(which),
            'xcrun_find_clang': xcrun.strip(), 'xcode_select_p': dev.strip(),
            'clang_version_exit': rc, 'clang_version': version.rstrip('\n').splitlines()}


FIXTURE_PROBE = r'''
import hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import sm_fixture
mode = sys.argv[3]
out = {'tempdir': os.path.realpath(tempfile.gettempdir()), 'key': sm_fixture._sources_key()}
cache = Path(out['tempdir']) / ('eb1c_sm_fixture_' + out['key'])
out['cache_existed_before'] = cache.exists()
try:
    path = sm_fixture.compiled()
    if mode == 'partial':
        (path / 'libeb1c-core.0.dylib').unlink()
        root = Path(tempfile.mkdtemp(prefix='b_'))
        (root / 'state').mkdir()
        sm_fixture.Build(root / 'build', state=root / 'state')
    out['raised'] = None
except BaseException as exc:
    out['raised'] = type(exc).__name__
    out['message'] = str(exc)[:300]
out['cache_launcher_exists_after'] = (cache / 'llama-server').is_file()
out['files'] = {}
if cache.is_dir():
    for p in sorted(cache.iterdir()):
        out['files'][p.name] = ('symlink -> ' + os.readlink(p) if p.is_symlink()
                                else hashlib.sha256(p.read_bytes()).hexdigest())
print(json.dumps(out))
'''

CONTROL_PROBE = r'''
import io, json, os, sys, unittest
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import tests_sm_manifest
tests_sm_manifest.LABSBX = sys.argv[3]
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[5:])
stream = io.StringIO()
res = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
print(json.dumps({'ran': res.testsRun, 'failures': len(res.failures),
                  'errors': len(res.errors), 'skipped': len(res.skipped),
                  'successful': res.wasSuccessful(),
                  'error_types': sorted({e[1].strip().splitlines()[-1].split(':')[0]
                                         for e in res.errors}),
                  'cache_launcher_exists_after': os.path.isfile(os.path.join(
                      sys.argv[3], sys.argv[4], "llama-server"))}))
'''


def _probe(argv: list, env: dict, root: Path) -> dict:
    res = subprocess.run(argv, capture_output=True, text=True, timeout=600, env=env,
                         check=False)
    try:
        out = json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        out = {'unparsed_output': (res.stdout + res.stderr)[-400:]}
    out['exit'] = res.returncode
    for key in ('message', 'unparsed_output'):
        if key in out:
            out[key] = out[key].replace(str(root), '<CONTROL_ROOT>')
    return out


def judge_fixture_controls(out: dict) -> dict:
    """[pure] Set ``ok`` on each of the five probe results (FIXTURE_CONTROL_TAGS).  A
    missing cache must REBUILD (A, D) or FAIL VISIBLY (B, C, E): an exception, or every
    control test run and erroring/failing.  A skip, a partial run or a pass without a
    compiler is never ``ok``."""
    n = len(FIXTURE_CONTROL_TESTS)
    a, b, c = (out.setdefault(t, {}) for t in FIXTURE_CONTROL_TAGS[:3])
    d, e = (out.setdefault(t, {}) for t in FIXTURE_CONTROL_TAGS[3:])
    a['ok'] = (a.get('raised') is None and a.get('cache_existed_before') is False
               and a.get('cache_launcher_exists_after') is True
               and a.get('otool_L_links_core') is True)
    b['ok'] = (b.get('raised') is not None and b.get('cache_existed_before') is False
               and b.get('cache_launcher_exists_after') is False)
    c['ok'] = c.get('raised') is not None
    d['ok'] = (d.get('ran') == n and d.get('successful') is True and d.get('skipped') == 0
               and d.get('cache_launcher_exists_after') is True)
    e['ok'] = (e.get('ran') == n and e.get('successful') is False and e.get('skipped') == 0
               and e.get('errors', 0) + e.get('failures', 0) == n
               and e.get('cache_launcher_exists_after') is False)
    return out


def fixture_missing_cache_controls(repo: Path, cache_dir_name: str) -> dict:
    """Five controls, each under its own fresh temporary root (never the shared cache):

    A. no cache -> ``compiled()`` rebuilds it (launcher present after, links libeb1c-core);
    B. no cache and a ``clang`` that fails (a stub first on PATH) -> an exception, no cache;
    C. a partial cache (launcher present, core library missing) -> ``Build()`` raises;
    D. the real control tests FIXTURE_CONTROL_TESTS with their LABSBX pointed at an empty
       root -> both run and pass, and the cache exists afterwards (rebuilt by the control);
    E. D with the failing ``clang`` -> both run and ERROR (visible; none skipped, none pass)."""
    controls, live = str(repo / 'experiments/live_ab_controls'), str(repo / LIVE_REL)
    roots = []

    def fresh(tag: str) -> Path:
        r = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_%s_' % tag)))
        roots.append(r)
        return r

    stub = fresh('stub')
    (stub / 'clang').write_text('#!/bin/sh\necho "clang disabled by the missing-cache '
                                'control" >&2\nexit 1\n', encoding='utf-8')
    (stub / 'clang').chmod(0o755)
    base_env = {k: v for k, v in os.environ.items() if k != 'TMPDIR'}
    no_cc = dict(base_env, PATH=str(stub) + os.pathsep + base_env.get('PATH', ''))
    try:
        out = {}
        for tag, mode, env in (('A_rebuild', 'fresh', base_env),
                               ('B_no_compiler', 'fresh', no_cc),
                               ('C_partial_cache', 'partial', base_env)):
            root = fresh(tag)
            out[tag] = _probe([PY, '-c', FIXTURE_PROBE, controls, live, mode],
                              dict(env, TMPDIR=str(root)), root)
        a = out['A_rebuild']
        otool_rc, otool = (run_text(['otool', '-L', os.path.join(
            a.get('tempdir', ''), cache_dir_name, 'llama-server')])
            if a.get('cache_launcher_exists_after') else (-1, ''))
        a['otool_L_links_core'] = otool_rc == 0 and '@rpath/libeb1c-core.0.dylib' in otool
        for tag, env in (('D_real_control_rebuilds', base_env),
                         ('E_real_control_no_compiler', no_cc)):
            labsbx = fresh(tag) / 'labsbx'
            out[tag] = _probe([PY, '-c', CONTROL_PROBE, controls, live, str(labsbx),
                               cache_dir_name] + list(FIXTURE_CONTROL_TESTS), env,
                              labsbx.parent)
            out[tag]['tests'] = list(FIXTURE_CONTROL_TESTS)
        judge_fixture_controls(out)
        for row in out.values():
            row.pop('tempdir', None)
        c = out['C_partial_cache']
        common = sorted(set(a.get('files', {})) & set(c.get('files', {})))
        out['observation_outputs_reproducible'] = {
            'files_compared': common,
            'byte_identical_between_A_and_C': [f for f in common
                                               if a['files'][f] == c['files'][f]],
            'reading': ('two compiles of the same sources in this run (A and C, different '
                        'temporary roots); where they differ, the committed C source digest, '
                        'not an output digest, is the fixture\'s identity')}
        return out
    finally:
        for r in roots:
            shutil.rmtree(str(r), ignore_errors=True)


def fixture_section(repo: Path, head: GitTree) -> tuple[dict, list]:
    problems = []
    src = head.read(FIXTURE_REL)
    if src is None:
        raise Refused(['fixture_absent'])
    sources = fixture_sources(src)
    controls = fixture_missing_cache_controls(repo, sources['cache_dir_name'])
    for tag in FIXTURE_CONTROL_TAGS:
        if not controls.get(tag, {}).get('ok'):
            problems.append('fixture_control:%s' % tag)
    # the outputs of this run (A) never appear in the freeze tree or the real manifest
    outputs = {v for v in controls['A_rebuild'].get('files', {}).values()
               if HEX64.fullmatch(v)}
    freeze_blobs = {p: head.read(p) or b'' for p in blob_digests(repo, head.rev,
                                                                 [RESULTS_REL + '/freeze'])}
    in_freeze = sorted(p for p, data in freeze_blobs.items()
                       if any(h.encode() in data for h in outputs))
    tracked = git(repo, 'ls-tree', '-r', '--name-only', '--full-tree', head.rev).decode()
    named_in_tree = [p for p in tracked.splitlines() if 'eb1c_sm_fixture' in p]
    manifest = json.loads(head.read(SERVING_MANIFEST_REL) or b'{}')
    lau = manifest.get('launcher')
    launcher = str(lau.get('path', '')) if isinstance(lau, dict) else str(lau or '')
    exclusion = {
        'fixture_output_digests_of_this_run': sorted(outputs),
        'freeze_tree_files_containing_any_of_them': in_freeze,
        'tracked_paths_naming_the_cache': named_in_tree,
        'real_manifest_launcher_is_a_repo_path_not_a_temp_path': launcher.startswith('<REPO>/'),
    }
    if in_freeze or named_in_tree or not exclusion[
            'real_manifest_launcher_is_a_repo_path_not_a_temp_path']:
        problems.append('fixture_outputs_not_excluded')
    imports = re.compile(r'^\s*(?:import|from)\s+(\w+)', re.M)
    ctl = {p.stem: set(imports.findall(p.read_text('utf-8')))
           for p in (repo / 'experiments/live_ab_controls').glob('*.py')}
    direct = sorted(m for m, deps in ctl.items() if 'sm_fixture' in deps)
    consumers = {'import_sm_fixture': direct,
                 'through_one_of_those': sorted(m for m, deps in ctl.items()
                                                if m not in direct and deps & set(direct))}
    own_names = {Path(rel).name for rel in OWN_FILES}
    cache_refs = sorted(p.name for p in (repo / 'experiments').rglob('*.py')
                        if p.name not in own_names
                        and 'eb1c_sm_fixture_' in p.read_text('utf-8', 'replace'))
    shared = Path(PRESCRIBED_LABSBX) / sources['cache_dir_name']
    return {
        'ruling': ('reviews/eb1_fixture_and_wip_delta_20260924_0703.md (main ccdda96) item 1: '
                   'acceptable as a model-free control fixture within its disclosed scope'),
        'fixture_module': {'path': FIXTURE_REL, 'sha256': sha256(src), 'bytes': len(src)},
        'c_sources': sources,
        'compiler': compiler_record(),
        'consumers': consumers,
        'files_naming_the_cache_directory': cache_refs,
        'shared_cache_the_suites_use': {
            'path': str(shared), 'exists_at_this_run': (shared / 'llama-server').is_file(),
            'note': ('the suites run under TMPDIR=<prescribed>/labsbx and reuse this cache; '
                     'the controls below never touch it')},
        'statement': ('the fixture outputs (the compiled launcher and two libraries, the '
                      'synthetic CMakeCache/build-info/receipt/logs of sm_fixture.Build) are TEST '
                      'ARTIFACTS under temporary directories: excluded from the freeze manifest '
                      'and from any evidence about the real durable build; no control result '
                      'is a real-host receipt'),
        'exclusion_checks': exclusion,
        'missing_cache_controls': controls,
        'missing_cache_controls_counts': {
            'planned': len(FIXTURE_CONTROL_TAGS),
            'completed': sum(1 for t in FIXTURE_CONTROL_TAGS
                             if t in controls and 'unparsed_output' not in controls[t]),
            'as_expected': sum(1 for t in FIXTURE_CONTROL_TAGS
                               if controls.get(t, {}).get('ok'))},
    }, problems


# --------------------------------------------------------------------------- #
# the solo-run suites
# --------------------------------------------------------------------------- #
RAN_RE = re.compile(r'^Ran (\d+) tests? in ([0-9.]+)s$', re.M)
VERDICT_RE = re.compile(r'^(OK|FAILED)(?: \((.*)\))?$', re.M)
VAL_RE = re.compile(r'^ran=(\d+) failures=(\d+) errors=(\d+) skipped=(\d+)$', re.M)
HEADER_RE = re.compile(r'^(FAIL|ERROR|UNEXPECTED SUCCESS): (.+)$', re.M)
SKIP_RE = re.compile(r"\.\.\. skipped (.*)$")
TEST_ID_RE = re.compile(r'^(\w+) \(([\w.]+)\)')


def parse_suite_output(text: str, returncode: int, planned: int | None,
                       stdout: str = '') -> dict:
    """The runner's own summary, never inferred: the LAST ``Ran`` line and the LAST verdict
    line of ``text`` (the runner's stream, stderr; test output on stdout is kept apart so it
    cannot supply either line).  ``passed`` only when both exist, the verdict is OK, the exit
    code is 0 and the number run equals the number planned.  ``stdout`` supplies only the
    validation script's own ``ran=... failures=...`` line."""
    ran = RAN_RE.findall(text)
    verdict = VERDICT_RE.findall(text)
    val = VAL_RE.findall(stdout)
    counts = {}
    if verdict and verdict[-1][1]:
        for part in verdict[-1][1].split(', '):
            k, _, v = part.partition('=')
            if v.isdigit():
                counts[k.strip()] = int(v)
    skips, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        m = SKIP_RE.search(line)
        if m:
            ident = TEST_ID_RE.match(line) or (i and TEST_ID_RE.match(lines[i - 1]))
            skips.append({'test': ident.group(2) if ident else None,
                          'reason': m.group(1)[:300]})
    out = {
        'exit': returncode,
        'ran_line': ('Ran %s tests in %ss' % ran[-1]) if ran else None,
        'ran': int(ran[-1][0]) if ran else None,
        'runner_seconds': float(ran[-1][1]) if ran else None,
        'verdict_line': (verdict[-1][0] + (' (%s)' % verdict[-1][1] if verdict[-1][1] else ''))
        if verdict else None,
        'verdict_counts': counts,
        'script_summary_line': ('ran=%s failures=%s errors=%s skipped=%s' % val[-1])
        if val else None,
        'failure_headers': [h[0] + ': ' + h[1] for h in HEADER_RE.findall(text)],
        'skips': skips,
        'planned': planned,
    }
    out['completed_equals_planned'] = (out['ran'] is not None and planned is not None
                                       and out['ran'] == planned)
    out['passed'] = (returncode == 0 and out['ran'] is not None and bool(verdict)
                     and verdict[-1][0] == 'OK' and out['completed_equals_planned'])
    return out


PLAN_PROBE = r'''
import json, sys, unittest
from collections import Counter
loader = unittest.TestLoader()
if sys.argv[1] == 'discover':
    suite = loader.discover(sys.argv[2], pattern='tests_*.py')
else:
    sys.path.insert(0, sys.argv[2])
    import importlib
    suite = loader.loadTestsFromModule(importlib.import_module(sys.argv[3]))
per, failed = Counter(), []
def walk(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            walk(t)
        else:
            per[t.id().split('.')[0]] += 1
            if type(t).__name__ == '_FailedTest':
                failed.append(t.id())
walk(suite)
print(json.dumps({'planned': suite.countTestCases(), 'per_module': dict(sorted(per.items())),
                  'import_failures': failed}))
'''


def planned_counts(repo: Path, argv: list) -> dict:
    if '-s' in argv:
        probe = ['discover', argv[argv.index('-s') + 1]]
    else:
        script = Path(argv[0])
        probe = ['module', str(script.parent), script.stem]
    res = subprocess.run([PY, '-c', PLAN_PROBE] + probe, cwd=str(repo), capture_output=True,
                         text=True, timeout=900, check=False)
    try:
        return json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'planned': None, 'probe_error': (res.stdout + res.stderr)[-400:]}


def utc() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def ps_rows() -> list:
    """``(pid, ppid, started_epoch | None, command)`` of every process (``ps``, C locale)."""
    try:
        res = subprocess.run(['ps', '-axo', 'pid=,ppid=,lstart=,command='], capture_output=True,
                             text=True, timeout=30, check=False,
                             env=dict(os.environ, LC_ALL='C', LANG='C'))
        text = res.stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = []
    for line in text.splitlines():
        parts = line.split(None, 7)
        if len(parts) == 8 and parts[0].isdigit() and parts[1].isdigit():
            try:
                started = time.mktime(time.strptime(' '.join(parts[2:7]),
                                                    '%a %b %d %H:%M:%S %Y'))
            except ValueError:
                started = None
            rows.append((int(parts[0]), int(parts[1]), started, parts[7]))
    return rows


def tree_of(rows: list, roots: Iterable[int]) -> set:
    """The pids of ``roots`` and of all their descendants in ``rows``."""
    kids: dict = {}
    for pid, ppid, _s, _c in rows:
        kids.setdefault(ppid, []).append(pid)
    seen, todo = set(), [r for r in roots if r]
    while todo:
        q = todo.pop()
        if q not in seen:
            seen.add(q)
            todo.extend(kids.get(q, []))
    return seen


def ancestors_of(rows: list, pid: int) -> set:
    parent = {q: pp for q, pp, _s, _c in rows}
    out = set()
    while pid and pid not in out:
        out.add(pid)
        pid = parent.get(pid, 0)
    return out


def watched_outside(rows: list, known: set, tokenize: Callable[[str], str],
                    since: float | None = None) -> list:
    """[pure] Watched processes (WATCH) whose pid is not in ``known`` (the suite's tree as
    observed so far, this tool and its ancestors).  ``attribution``:
    ``orphan_started_during_the_suite`` when its parent is launchd (pid 1) and it started at
    or after ``since`` (a descendant reparented before a sample caught it in the tree -- the
    controls orphan servers on purpose, e.g. tests_eb1_entry C10); otherwise ``foreign``."""
    out = []
    for pid, ppid, started, cmd in rows:
        if pid in known or cmd.startswith('ps -axo') or not any(w in cmd for w in WATCH):
            continue
        orphan = (since is not None and ppid == 1 and started is not None
                  and started >= since - 1)
        out.append({'pid': pid, 'ppid': ppid,
                    'started_utc': None if started is None else time.strftime(
                        '%Y-%m-%dT%H:%M:%SZ', time.gmtime(started)),
                    'command_head': tokenize(cmd)[:140],
                    'attribution': 'orphan_started_during_the_suite' if orphan else 'foreign'})
    return out


def host_snapshot(repo: Path, known: set, tokenize: Callable[[str], str],
                  since: float | None = None) -> dict:
    st = os.statvfs(str(repo))
    _rc, vm = run_text(['vm_stat'])
    page = re.search(r'page size of (\d+) bytes', vm)
    pages = {k.strip(): int(v.strip().rstrip('.')) for k, v in
             re.findall(r'^(Pages [a-z ]+):\s+(\d+)\.?$', vm, re.M)}
    avail = None
    if page:
        avail = int(page.group(1)) * sum(pages.get(k, 0) for k in (
            'Pages free', 'Pages inactive', 'Pages speculative'))
    _rc, batt = run_text(['pmset', '-g', 'batt'])
    rows = ps_rows()
    return {
        'utc': utc(),
        'load_average': run_text(['sysctl', '-n', 'vm.loadavg'])[1].strip(),
        'ncpu': os.cpu_count(),
        'memory_bytes': int((run_text(['sysctl', '-n', 'hw.memsize'])[1].strip() or '0')),
        'vm_free_inactive_speculative_bytes': avail,
        'disk_free_bytes_repo_volume': st.f_bavail * st.f_frsize,
        'battery': [ln.strip() for ln in batt.splitlines()[1:2]],
        'processes': len(rows),
        'watched_processes_outside_the_suite': watched_outside(
            rows, known | ancestors_of(rows, os.getpid()), tokenize, since),
        'reading': 'an observation at utc; not a capacity reservation',
    }


class Sampler(threading.Thread):
    """``ps`` every SAMPLE_EVERY_S while a suite runs.  ``known`` accumulates every pid ever
    seen in the suite's tree (so a descendant reparented later stays attributed); ``seen``
    keeps each watched process outside it, with its attribution."""

    def __init__(self, child: int, tokenize: Callable[[str], str], since: float) -> None:
        super().__init__(daemon=True)
        self.child, self.tokenize, self.since = child, tokenize, since
        self.stop_event = threading.Event()
        self.samples = 0
        self.known: set = set()
        self.seen: dict = {}

    def sample(self) -> None:
        rows = ps_rows()
        self.samples += 1
        self.known |= tree_of(rows, [self.child]) | ancestors_of(rows, os.getpid())
        for row in watched_outside(rows, self.known, self.tokenize, self.since):
            self.seen.setdefault(row['pid'], row)
        for pid in list(self.seen):                 # seen outside first, in the tree later
            if pid in self.known:
                self.seen.pop(pid)

    def run(self) -> None:
        self.sample()
        while not self.stop_event.wait(SAMPLE_EVERY_S):
            self.sample()


def solo_verdict(runs: list) -> dict:
    """[pure] ``solo``: no watched process attributed ``foreign`` before, during (sampled) or
    after any suite.  ``solo_strict``: no watched process outside a suite's tree at all."""
    rows = [row for r in runs for row in (r['host_before']['watched_processes_outside_the_suite']
                                          + r['sampler']['watched_outside_the_tree']
                                          + r['host_after']['watched_processes_outside_the_suite'])]
    return {'solo': not any(row['attribution'] == 'foreign' for row in rows),
            'solo_strict': not rows,
            'foreign': [row for row in rows if row['attribution'] == 'foreign'],
            'orphans_started_during_a_suite': sorted({row['command_head'] for row in rows
                                                      if row['attribution'] != 'foreign'})}


def run_suite(repo: Path, name: str, argv: list, tokenize: Callable[[str], str]) -> dict:
    plan = planned_counts(repo, argv)
    before = host_snapshot(repo, set(), tokenize)
    since = time.time()
    err_fd, err_path = tempfile.mkstemp(prefix='pinsucc_%s_' % name, suffix='.err')
    out_fd, out_path = tempfile.mkstemp(prefix='pinsucc_%s_' % name, suffix='.out')
    start_utc, m0 = utc(), time.monotonic()
    with os.fdopen(err_fd, 'wb') as err, os.fdopen(out_fd, 'wb') as out:
        proc = subprocess.Popen([PY] + argv, cwd=str(repo), stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL)
        sampler = Sampler(proc.pid, tokenize, since)
        sampler.start()
        timed_out = False
        while True:
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - m0 > SUITE_TIMEOUT_S and not timed_out:
                timed_out = True
                proc.kill()
            time.sleep(0.5)
        proc.returncode = os.waitstatus_to_exitcode(status)
        sampler.stop_event.set()
        sampler.join()
    wall = time.monotonic() - m0
    end_utc = utc()
    text = Path(err_path).read_text('utf-8', 'replace')
    stdout = Path(out_path).read_text('utf-8', 'replace')
    os.unlink(err_path)
    os.unlink(out_path)
    parsed = parse_suite_output(text, proc.returncode, plan.get('planned'), stdout)
    for row in parsed['skips']:
        row['reason'] = tokenize(row['reason'])
    parsed['failure_headers'] = [tokenize(h) for h in parsed['failure_headers']]
    after = host_snapshot(repo, sampler.known, tokenize, since)
    return {
        'suite': name,
        'argv': [tokenize(PY)] + argv,
        'cwd': '<REPO>',
        'start_utc': start_utc, 'end_utc': end_utc, 'wall_seconds': round(wall, 3),
        'timed_out': timed_out,
        'plan': plan,
        'result': parsed,
        'stderr_sha256': sha256(text.encode('utf-8')),
        'stderr_bytes': len(text.encode('utf-8')),
        'stdout_sha256': sha256(stdout.encode('utf-8')),
        'stdout_bytes': len(stdout.encode('utf-8')),
        'stderr_tail': [tokenize(ln) for ln in text.rstrip('\n').splitlines()[-4:]],
        'stdout_tail': [tokenize(ln) for ln in stdout.rstrip('\n').splitlines()[-2:]],
        'child_rusage': {'user_s': round(ru.ru_utime, 3), 'system_s': round(ru.ru_stime, 3),
                         'max_rss_bytes_darwin': ru.ru_maxrss},
        'host_before': before, 'host_after': after,
        'sampler': {'every_s': SAMPLE_EVERY_S, 'samples': sampler.samples,
                    'watched_patterns': list(WATCH),
                    'pids_attributed_to_the_suite_tree': len(sampler.known),
                    'watched_outside_the_tree': [row for _p, row in sorted(sampler.seen.items())],
                    'reading': ('watched processes never seen in the suite\'s own process tree '
                                'at any sample (every %gs); sampled, not continuous'
                                % SAMPLE_EVERY_S)},
    }


# --------------------------------------------------------------------------- #
# the receipt
# --------------------------------------------------------------------------- #
def make_tokenizer(repo: Path) -> Callable[[str], str]:
    pairs = sorted({(str(Path(repo).resolve()), '<REPO>'), (str(repo), '<REPO>'),
                    (os.path.realpath(tempfile.gettempdir()), '<TMP>'),
                    (tempfile.gettempdir(), '<TMP>'), (str(Path.home()), '<HOME>')},
                   key=lambda p: -len(p[0]))

    def tokenize(s: str) -> str:
        for raw, token in pairs:
            s = s.replace(raw, token)
        return s
    return tokenize


def worktree_state(repo: Path) -> tuple[list, list]:
    """(entries, problems): ``git status --porcelain`` (untracked included, ignored not);
    anything but OWN_FILES is a problem."""
    out = git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    entries = [e.decode('utf-8') for e in out.split(b'\0') if e]
    problems = ['working_tree_dirty:%s' % e[3:] for e in entries if e[3:] not in OWN_FILES]
    return entries, problems


def build_receipt(repo: Path, predecessor: str, *, run_suites: bool) -> dict:
    repo = Path(repo).resolve()
    tokenize = make_tokenizer(repo)
    problems: list = []
    started = utc()
    if resolve(repo, predecessor) is None:
        raise Refused(['predecessor_missing'])
    old = GitTree(repo, predecessor)
    head = GitTree(repo, 'HEAD')
    entries, dirty = worktree_state(repo)
    problems += dirty

    # 1-2. harness maps
    pmap = harness_map(old)
    problems += predecessor_problems(pmap)
    smap = harness_map(head)
    view = lab_common_view(repo)
    if view['harness'] != smap:
        problems.append('successor_differs_from_lab_common_on_the_working_tree')
    if view['canonical_of_map'] != sha256_canonical(smap):
        problems.append('canonical_digest_differs_from_lab_common')

    # 3. per changed / added entry, and every other file of the subset
    changed = sorted(n for n in set(pmap) | set(smap) if pmap.get(n) != smap.get(n))
    harness_changes = {n: diff_entry(repo, old, head, '%s/%s' % (LIVE_REL, n)) for n in changed}
    if not all(r['diff_applied_to_old_gives_new'] for r in harness_changes.values()):
        problems.append('diff_does_not_reproduce')
    names = git(repo, 'diff', '--name-status', '--no-renames', '-z', old.rev, head.rev
                ).decode('utf-8').split('\0')
    subset = {}
    for i in range(0, len(names) - 1, 2):
        path = names[i + 1]
        if path.startswith(LIVE_REL + '/') and path.count('/') == 2 and \
                path.rsplit('/', 1)[1] in set(pmap) | set(smap):
            continue
        subset[path] = diff_entry(repo, old, head, path)
    if not all(r['diff_applied_to_old_gives_new'] for r in subset.values()):
        problems.append('subset_diff_does_not_reproduce')
    old_lc, new_lc = old.read(LIVE_REL + '/lab_common.py'), head.read(LIVE_REL + '/lab_common.py')

    # 4. reused files, decision modules, documents, rule block, serving manifest
    reused_old = module_constant(old_lc, 'REUSED_FILES')
    reused_new = module_constant(new_lc, 'REUSED_FILES')
    rmap = {rev: {n: sha256(t.read('%s/%s' % (REUSED_REL, n)) or b'') for n in reused_new}
            for rev, t in (('b049307', old), ('head', head))}
    reused_ok = reused_old == reused_new and rmap['b049307'] == rmap['head'] and \
        list(reused_new) == view['reused_files']
    if not reused_ok:
        problems.append('reused_files_changed')
    decision = {n: {'b049307': pmap.get(n), 'head': smap.get(n)} for n in DECISION_MODULES}
    if any(r['b049307'] is None or r['b049307'] != r['head'] for r in decision.values()):
        problems.append('decision_module_changed')
    docs = {}
    for label, (rel, expected_old) in DOCUMENTS.items():
        o, n = old.read(rel), head.read(rel)
        docs[label] = {'path': rel, 'b049307': o and sha256(o), 'head': n and sha256(n),
                       'b049307_bytes': o and len(o), 'head_bytes': n and len(n),
                       'b049307_is_the_reviewed_pre_image': bool(o) and sha256(o) == expected_old}
        if not docs[label]['b049307_is_the_reviewed_pre_image']:
            problems.append('pre_image:%s' % label)
    cfg_old, cfg_new = json.loads(old.read(CONFIG_REL)), json.loads(head.read(CONFIG_REL))
    keys_old = module_constant(old_lc, 'RULE_BLOCK_KEYS')
    keys_new = module_constant(new_lc, 'RULE_BLOCK_KEYS')
    rb = {'b049307': rule_block_digest(cfg_old, keys_old),
          'head': rule_block_digest(cfg_new, keys_new),
          'keys_unchanged': keys_old == keys_new}
    rb['head_equals_lab_common_rule_block_sha256'] = view['rule_block'] == rb['head']
    rb['unchanged'] = rb['b049307'] == rb['head'] == RULE_BLOCK and rb['keys_unchanged']
    if not (rb['unchanged'] and rb['head_equals_lab_common_rule_block_sha256']):
        problems.append('rule_block_moved')
    mbytes = head.read(SERVING_MANIFEST_REL)
    manifest = json.loads(mbytes) if mbytes else {}
    mcanon = sha256_canonical(manifest) if mbytes else None
    cfg_value = (cfg_new.get('llama_cpp') or {}).get('serving_manifest_sha256')
    sm = {'path': SERVING_MANIFEST_REL,
          'b049307': {'artifact': 'absent' if old.read(SERVING_MANIFEST_REL) is None
                      else 'present',
                      'config_llama_cpp_serving_manifest_sha256':
                          (cfg_old.get('llama_cpp') or {}).get('serving_manifest_sha256')},
          'head': {'file_sha256': mbytes and sha256(mbytes), 'bytes': mbytes and len(mbytes),
                   'canonical_sha256': mcanon,
                   'file_is_canonical_json_plus_newline':
                       bool(mbytes) and mbytes == (canonical_json(manifest) + '\n').encode(),
                   'config_llama_cpp_serving_manifest_sha256': cfg_value,
                   'config_value_equals_canonical_digest': cfg_value == mcanon,
                   'carries_no_home_token': bool(mbytes) and b'<HOME>' not in mbytes,
                   'launcher_sha256': manifest.get('launcher_sha256'),
                   'libraries': len(manifest.get('libraries') or {}),
                   'code': '%s/lab_serving_manifest.py (added; harness entry)' % LIVE_REL}}
    if not (sm['head']['config_value_equals_canonical_digest']
            and sm['head']['file_is_canonical_json_plus_newline']
            and sm['head']['carries_no_home_token']):
        problems.append('serving_manifest_binding')
    cells = json.loads(head.read(DOCUMENTS['cells.json'][0]))
    sup = cells['provenance']['vocabulary_alignment']
    vocab = {'original_pin': sup['sha256'],
             'superseded_by': sup['superseded_by']['sha256'],
             'supersedes': sup['superseded_by']['supersedes'],
             'prior_successors': len(sup['superseded_by']['prior_successors'])}
    vocab['holds'] = (vocab['original_pin'] == VOCABULARY_ORIGINAL
                      and vocab['supersedes'] == VOCABULARY_ORIGINAL
                      and vocab['superseded_by'] == docs['protocol_FINAL.md']['head'])
    if not vocab['holds']:
        problems.append('cells_successor')
    amend = json.loads(head.read(AMENDMENT_RECEIPT_REL) or b'{}').get('written', {})
    agreement = {
        'config.json': amend.get('config_sha256') == docs['config.json']['head'],
        'ARCHITECTURE_FINAL.md':
            amend.get('architecture_sha256') == docs['ARCHITECTURE_FINAL.md']['head'],
        'protocol_FINAL.md': amend.get('protocol_sha256') == docs['protocol_FINAL.md']['head'],
        'cells.json': amend.get('cells_sha256') == docs['cells.json']['head'],
        'rule_block': amend.get('rule_block_sha256_on_disk') == rb['head'],
        'serving_manifest_canonical': amend.get('artifact_sha256_canonical') == mcanon,
        'serving_manifest_file': amend.get('artifact_file_sha256') == sm['head']['file_sha256'],
    }
    if not all(agreement.values()):
        problems.append('amendment_receipt_disagrees')
    sup_block = cfg_new.get('server_supervision')
    landed = git(repo, 'log', '--format=%H', '-S"server_supervision"',
                 '%s..%s' % (old.rev, head.rev), '--', CONFIG_REL).decode().split()
    cfg_lines = [ln for ln in (head.read(CONFIG_REL) or b'').decode().splitlines()
                 if ln.lstrip().startswith('"server_supervision"')]
    fences = {label: (head.read(DOCUMENTS[label][0]) or b'').decode().count(cfg_lines[0])
              if len(cfg_lines) == 1 else 0
              for label in ('ARCHITECTURE_FINAL.md', 'protocol_FINAL.md')}
    naming = sorted(p.name for p in (repo / 'experiments/live_ab_controls').glob('tests_*.py')
                    if re.search(r'server_supervision|SERVER_SUPERVISION_KEY',
                                 p.read_text('utf-8')))
    supervision = {
        'b049307': cfg_old.get('server_supervision'),
        'head': sup_block,
        'config_line': cfg_lines,
        'same_line_occurrences_in_the_two_fences': fences,
        'lab_common_server_supervision_cap_at_head': view['server_supervision_cap'],
        'landed_in_commits': landed,
        'outside_rule_block': 'server_supervision' not in keys_new,
        'control_modules_naming_the_block': naming,
        'statement': (
            'The restart-cap binding is already IN this subset, not deferred to a later '
            'amendment: config.json carries server_supervision since commit %s (the '
            'synchronized amendment v2, receipt %s), and the ARCHITECTURE 6.1 and Appendix B '
            'fences carry the same line once each (same_line_occurrences_in_the_two_fences). '
            'Within the subset the cap is exercised only by model-free controls with temporary '
            'freeze trees and configurations (dryrun_live_ab.build_mock_freeze reads this '
            'config.json at experiments/live_ab/dryrun_live_ab.py:184; the modules in '
            'control_modules_naming_the_block construct, edit or remove the block); no trial, '
            'loaded phase or run against a real frozen configuration has exercised it.'
            % (','.join(c[:7] for c in landed) or 'NONE', AMENDMENT_RECEIPT_REL)),
    }
    if landed != [AMENDMENT_COMMIT] or not supervision['outside_rule_block'] or \
            fences != {'ARCHITECTURE_FINAL.md': 1, 'protocol_FINAL.md': 1} or not naming:
        problems.append('server_supervision_binding')

    # 5. prior observations not reissued
    table: dict = {}
    d_old = blob_digests(repo, old.rev, TRACKED_PREFIXES)
    d_new = blob_digests(repo, head.rev, TRACKED_PREFIXES)
    for p in set(d_old) | set(d_new):
        table[p] = {'b049307': d_old.get(p), 'head': d_new.get(p)}
    table['<rule block of config.json>'] = {'b049307': rb['b049307'], 'head': rb['head']}
    table['<harness map canonical digest>'] = {'b049307': sha256_canonical(pmap),
                                               'head': sha256_canonical(smap)}
    table['<serving manifest canonical digest>'] = {'b049307': None, 'head': mcanon}
    mhex = frozenset(HEX64.findall((mbytes or b'').decode('utf-8')))
    chex = frozenset(HEX64.findall((head.read(CONFIG_REL) or b'').decode('utf-8')))
    prior = []
    for rel in PRIOR_OBSERVATIONS:
        data = head.read(rel)
        if data is None or old.read(rel) != data:
            problems.append('prior_observation_missing_or_changed:%s' % rel)
            continue
        added = git(repo, 'log', '--diff-filter=A', '--format=%H', head.rev, '--', rel
                    ).decode().split()
        c = classify_pins(json.loads(data), table, mhex, tokenize, chex)
        prior.append(dict({'path': rel, 'sha256': sha256(data), 'bytes': len(data),
                           'added_in_commit': added[-1] if added else None,
                           'byte_identical_at_b049307_and_head': True,
                           'reissued_by_this_successor': False,
                           'verdict': record_verdict(c)}, **c))
    statements = []
    for rel, line_no, fragment in COUNT_STATEMENTS:
        data = head.read(rel) or b''
        lines = data.decode('utf-8', 'replace').splitlines()
        text = lines[line_no - 1] if len(lines) >= line_no else ''
        ok = fragment in text
        statements.append({'path': rel, 'line': line_no, 'text': text.strip(),
                           'sha256': sha256(data), 'cited_line_carries_it': ok,
                           'now': 'historical: the successor map has %d entries and %d changed'
                                  % (len(smap), len(changed))})
        if not ok:
            problems.append('count_statement:%s' % rel)

    # 6. the compiled C test double
    fixture, fproblems = fixture_section(repo, head)
    problems += fproblems

    commits = [ln.split('\t', 1) for ln in git(
        repo, 'log', '--reverse', '--topo-order', '--format=%H%x09%s',
        '%s..%s' % (old.rev, head.rev)).decode().splitlines()]
    own = {}
    for rel in OWN_FILES:
        p = repo / rel
        status = next((e[:2] for e in entries if e[3:] == rel), None)
        own[rel] = {'sha256': sha256(p.read_bytes()) if p.is_file() else None,
                    'git_status': status if status else
                    ('committed' if head.read(rel) is not None else 'absent')}
    this_file = Path(__file__).resolve()

    receipt = {
        'schema': SCHEMA,
        'convention': 'deterministic-path',
        'convention_note': ('pins, maps and diff digests are deterministic functions of git '
                            'objects; wall times, host snapshots and timestamps are '
                            'observations of this run'),
        'status': STATUS,
        'this_is_not_a_freeze': ('no freeze bundle exists; nothing here approves a freeze, a '
                                 'loaded stage or a trial'),
        'authority': [
            'reviews/prerun_bundle_go_nogo_20260923_2040.md:16 (record the pre-outcome pin '
            'successor; preserve the old pin and all prior observations)',
            'reviews/restart_cap_estimand_ruling_20260923_2114.md (main ebcd637) item 2 (exact '
            'EB1/EB5 code and controls with old/new hashes, no loaded run)',
            'reviews/eb1_fixture_and_wip_delta_20260924_0703.md (main ccdda96) items 1 and 3',
        ],
        'run_started_utc': started,
        'repository': {
            'predecessor': old.rev, 'head': head.rev,
            'commits_predecessor_to_head': [{'commit': c[0], 'subject': c[1]} for c in commits],
            'working_tree_porcelain': entries,
            'tool_files': own,
            'tool_run_from': tokenize(str(this_file)),
            'git_version': run_text(['git', '--version'])[1].strip(),
        },
        'harness_pin': {
            'semantics': ('lab_common.harness_file_hashes: the top-level experiments/live_ab/'
                          '*.py files plus config.json, sha256 of each file; canonical digest '
                          '= lab_common.sha256_canonical of the name -> sha256 map'),
            'predecessor': {'rev': old.rev, 'count': len(pmap),
                            'canonical_sha256': sha256_canonical(pmap),
                            'expected_canonical_sha256': PREDECESSOR_CANONICAL,
                            'equals_expected': not predecessor_problems(pmap), 'map': pmap},
            'successor': {'rev': head.rev, 'count': len(smap),
                          'canonical_sha256': sha256_canonical(smap),
                          'equals_lab_common_harness_file_hashes_on_the_working_tree':
                              view['harness'] == smap, 'map': smap},
            'counts': {'before': len(pmap), 'after': len(smap),
                       'modified': sum(1 for r in harness_changes.values()
                                       if r['status'] == 'modified'),
                       'added': sorted(n for n, r in harness_changes.items()
                                       if r['status'] == 'added'),
                       'removed': sorted(n for n, r in harness_changes.items()
                                         if r['status'] == 'deleted'),
                       'unchanged': len(set(pmap) & set(smap)) - sum(
                           1 for n in changed if n in pmap and n in smap)},
            'changed': harness_changes,
            'unchanged_entries': sorted(n for n in smap if pmap.get(n) == smap[n]),
            'diff_command': 'git ' + ' '.join(DIFF_ARGV) + ' <predecessor> <head> -- <path> '
                            '(every GIT_* variable unset, then GIT_CONFIG_NOSYSTEM=1, '
                            'GIT_CONFIG_GLOBAL=%s, GIT_ATTR_NOSYSTEM=1, LC_ALL=C)'
                            % os.devnull,
            'diff_check': ('each diff is applied with git apply -p1 to the predecessor bytes '
                           'in a directory outside any repository; the result must be the '
                           'HEAD bytes'),
        },
        'reused_files': {'dir': REUSED_REL, 'names_b049307': list(reused_old),
                         'names_head': list(reused_new), 'b049307': rmap['b049307'],
                         'head': rmap['head'], 'unchanged': reused_ok,
                         'reused_file_sha256_canonical': sha256_canonical(rmap['head'])},
        'decision_modules_byte_unchanged': decision,
        'documents': docs,
        'rule_block': rb,
        'serving_manifest': sm,
        'cells_vocabulary_successor': vocab,
        'synchronized_amendment': {'commit': AMENDMENT_COMMIT, 'receipt': AMENDMENT_RECEIPT_REL,
                                   'receipt_sha256': sha256(head.read(AMENDMENT_RECEIPT_REL)
                                                            or b''),
                                   'head_equals_its_written_values': agreement},
        'server_supervision': supervision,
        'other_files_changed_by_the_subset': subset,
        'prior_observations_not_reissued': {
            'classification': classify_pins.__doc__.split('\n\n', 1)[1].strip(),
            'records': prior,
            'harness_count_statements': statements,
        },
        'compiled_c_test_double': fixture,
        'nothing_executed': ('no model, llama-server, llama.cpp build or network request; the '
                             'C test double compiled under temporary roots; the suites start '
                             'their own loopback mocks'),
        'prepared_by': ('Prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off (protocol 14.7).'),
    }
    if run_suites:
        runs = [run_suite(repo, name, argv, tokenize) for name, argv in SUITES]
        receipt['solo_run_suites'] = {
            'python': tokenize(PY),
            'order': [s[0] for s in SUITES],
            'runs': runs,
            'all_passed': all(r['result']['passed'] for r in runs),
            'solo_evidence': solo_verdict(runs),
            'planned_total': sum(r['plan'].get('planned') or 0 for r in runs),
            'completed_total': sum(r['result']['ran'] or 0 for r in runs),
            'deviation_from_the_contract_command': ('-v added to each discover command (for '
                                                    'skip reasons); nothing else'),
        }
        entries_after, _ = worktree_state(repo)
        if resolve(repo, 'HEAD') != head.rev or entries_after != entries:
            problems.append('tree_changed_during_the_run')
    else:
        receipt['solo_run_suites'] = 'not run in this invocation (--no-suites)'
    receipt['generated_utc'] = utc()
    if problems:
        raise Refused(problems, receipt)
    return receipt


def write_once(path: Path, obj: Mapping) -> str:
    data = (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'wb') as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    if Path(path).read_bytes() != data:
        raise Refused(['read_back'])
    return sha256(data)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    ap.add_argument('--repo', default=str(DEFAULT_REPO))
    ap.add_argument('--predecessor', default=PREDECESSOR)
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--no-suites', action='store_true')
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else repo / RESULTS_REL
    try:
        if args.no_suites and out_dir == (repo / RESULTS_REL).resolve():
            raise Refused(['no_suites_into_results'])
        if out_dir == (repo / RESULTS_REL).resolve() and \
                repo not in Path(__file__).resolve().parents:
            raise Refused(['tool_not_in_repo'])
        receipt = build_receipt(repo, args.predecessor, run_suites=not args.no_suites)
        out = out_dir / ('HARNESS_PIN_SUCCESSOR_%s.json'
                         % time.strftime('%Y%m%d_%H%M', time.gmtime()))
        if out.exists():
            raise Refused(['write_once:%s' % out.name])
        digest = write_once(out, receipt)
    except Refused as exc:
        print('REFUSED: %s' % ', '.join(exc.problems), file=sys.stderr)
        if exc.draft is not None:
            fd, path = tempfile.mkstemp(prefix='pinsucc_refused_', suffix='.json')
            with os.fdopen(fd, 'w') as fh:
                json.dump(dict(exc.draft, REFUSED=exc.problems), fh, indent=1, sort_keys=True)
            print('refused draft (not a receipt): %s' % path, file=sys.stderr)
        return 2
    suites = receipt['solo_run_suites']
    print('%s sha256=%s harness %d->%d canonical %s->%s suites=%s' % (
        out, digest, receipt['harness_pin']['counts']['before'],
        receipt['harness_pin']['counts']['after'],
        receipt['harness_pin']['predecessor']['canonical_sha256'][:8],
        receipt['harness_pin']['successor']['canonical_sha256'][:8],
        suites if isinstance(suites, str) else 'all_passed=%s solo=%s solo_strict=%s' % (
            suites['all_passed'], suites['solo_evidence']['solo'],
            suites['solo_evidence']['solo_strict'])))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
