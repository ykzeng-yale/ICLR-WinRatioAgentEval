"""Reproduction preflight of the EB1+EB5 subset suites: every missing runtime input, by name.

Root 22:08 (``reviews/eb1_eb5_summary_repair_interim_20260924_2208.md``, main 76f5e71) ran the
seven summary controls in a sparse worktree; ``setUpClass`` died on a ``StopIteration`` because
the mock tree's program preflight refused before seq 0 with ``harness_file_sha`` /
``preflight_rule_failed`` (``reused_file_sha256`` and ``sandbox_profile_sha256`` drift).  The cause
(reproduced in a fresh sparse clone, see ``REPRODUCE_EB1_EB5_SUBSET.md``): the checkout lacked
``experiments/local_stream/`` -- five TRACKED files the mock bundle hashes
(``dryrun_live_ab._mock_bundle``) and whose ``sandbox.py`` preflight asks for the seatbelt profile
(``lab_data.observed_sandbox_profile_sha256``).  The mock bundle then pins ``{}`` and the literal
``sha256_text('mock-sandbox-profile')``, the observation carries neither member, and
``lab_common.verify_bundle_members`` reports both as drift.  Nothing named the missing files.

:func:`problems` names them, and the other inputs the suites need that git does not carry:

* ``reused_file_missing`` -- ``lab_common.REUSED_FILES`` under ``experiments/local_stream``;
* ``sandbox_profile_unobservable`` -- the checkout's own ``sandbox.sandbox_info()`` (loaded from
  its file, the function the harness asks) returns no profile digest: file absent, or no
  ``/usr/bin/sandbox-exec`` (not macOS);
* ``pinned_source_missing`` / ``pinned_source_digest`` -- the three roster sources of
  ``lab_data.SOURCES`` (bytes and sha256 pinned there), looked up the way ``lab_data._find_cached``
  looks (``work/local_stream/data`` of the checkout, then ``lab_data.CACHE_SEARCH_DIRS``).  The
  suites need ``mbpp.jsonl`` although production treats it as optional: without it the roster
  silently becomes S1 and ``tests_lab_design`` fails on ``'S1' != 'EXT'``;
* ``pilot_tasks_missing`` / ``pilot_tasks_digest`` -- ``work/local_stream/data/tasks.json``, which
  ``experiments/local_stream/tests_local_stream.py`` loads at import (so ``tests_lab_serving``,
  which imports it, fails to import);
* ``git_history_missing`` -- the commits the controls ``git show`` / ``git diff``
  (:data:`HISTORY`); without them three negative controls SKIP ("git history is not
  available"), so "OK (skipped=N)" is not the reproduction, and ``tests_delta_citations`` fails;
* ``c_compiler_missing`` -- ``clang --version`` does not run: ``sm_fixture.compiled()`` cannot
  build the C test double when no verified cache exists under the prescribed TMPDIR.

What it does NOT perform: it does not run a suite, does not start any process but ``git`` and
``clang --version``, does not check the host-quiescence gate (the gate names its own reason),
the interpreter or packages (reported by :func:`environment`, never refused), or the main
checkout's durable build that ``tests_repair_amendment_v2`` skips without.  It is stricter than
the controls in one place: it refuses a host without ``clang`` even when a verified cache exists.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement); the
``live_ab`` suite itself (harness files) cannot call it -- run ``python
experiments/live_ab_controls/repro_inputs.py --suite live_ab`` first.  Prepared and checked by
AI agent sessions; not human peer review or author sign-off (protocol 14.7).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                                       # noqa: E402
import lab_data                                                         # noqa: E402

#: The commits the controls read with ``git show`` / ``git diff``, and who reads them.
HISTORY: dict[str, str] = {
    '7ebffad66336b84bc0dae5ca53d8899f001112c9':
        'tests_invalid_decision_summary.PRE_FIX (its negative control skips without it)',
    '159e747815f76eacf6a4cd84efd860f0f3321207':
        'tests_decision_eligibility negative control (skips without it)',
    'b049307ff62153a054f61b6179291ba987de2ba1':
        'tests_decision_eligibility (skips) and tests_delta_citations.BASE (fails)',
    '988baf7ab3f65b9bf4318e5eb12001c49d6387d9': 'tests_delta_citations.PRE_FIX (fails)',
}
#: ``work/local_stream/data/tasks.json`` as ``experiments/local_stream/data.py`` builds it from the
#: two S1 sources (reproduced byte-exactly offline, REPRODUCE_EB1_EB5_SUBSET.md).
PILOT_TASKS = {'bytes': 602791,
               'sha256': '23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce'}
#: What each suite needs of the checks below.  ``summary`` is tests_invalid_decision_summary alone;
#: ``mock_preflight`` is what every mock-tree preflight reads (``tests_eb1_entry.setUpModule``).
SUITES: dict[str, tuple[str, ...]] = {
    'mock_preflight': ('reused', 'profile'),
    'summary': ('reused', 'profile', 'history'),
    'live_ab_controls': ('reused', 'profile', 'history', 'compiler'),
    'live_ab': ('reused', 'profile', 'sources', 'pilot_tasks'),
}
SUITES['all'] = tuple(dict.fromkeys(c for s in list(SUITES.values()) for c in s))


class MissingReproductionInputs(RuntimeError):
    """Raised by :func:`require`; its text names every missing input and its fix."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe_profile(repo: Path) -> str | None:
    """The profile digest ``sandbox.sandbox_info()`` of ``repo``'s own ``sandbox.py`` returns, or
    None (file absent, unloadable, or no seatbelt on this host).  Loaded from its file under a
    private module name, so the check reads the checkout named, not this one."""
    path = Path(repo) / 'experiments' / 'local_stream' / 'sandbox.py'
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location('_repro_inputs_sandbox', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)                          # type: ignore[union-attr]
        digest = module.sandbox_info().get('profile_sha256')
    except Exception:                                            # noqa: BLE001 - named below
        return None
    return str(digest) if isinstance(digest, str) and digest else None


def _find_source(name: str, data_dir: Path, cache_dirs) -> Path | None:
    for directory in (data_dir,) + tuple(cache_dirs):
        for alias in lab_data.SOURCES[name]['aliases']:
            if (Path(directory) / alias).is_file():
                return Path(directory) / alias
    return None


def _git_has(repo: Path, commit: str) -> bool:
    try:
        res = subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', commit + '^{commit}'],
                             capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


def problems(repo: Path = REPO, suite: str = 'all', *, cache_dirs=None) -> list[dict]:
    """``[{'code', 'input', 'message'}]`` for every input ``suite`` needs that ``repo`` lacks
    (empty when none).  ``cache_dirs`` defaults to ``lab_data.CACHE_SEARCH_DIRS``."""
    repo = Path(repo)
    cache_dirs = lab_data.CACHE_SEARCH_DIRS if cache_dirs is None else tuple(cache_dirs)
    want = SUITES[suite]
    out: list[dict] = []

    def add(code: str, what: str, message: str) -> None:
        out.append({'code': code, 'input': what, 'message': message})

    ls_dir = repo / 'experiments' / 'local_stream'
    if 'reused' in want:
        for name in lab_common.REUSED_FILES:
            if not (ls_dir / name).is_file():
                add('reused_file_missing', 'experiments/local_stream/' + name,
                    'tracked at the subset commit but absent here (sparse or partial checkout); '
                    'every mock-tree preflight then refuses harness_file_sha '
                    '(reused_file_sha256 drift). Fix: a FULL clone at the subset commit '
                    '(git sparse-checkout disable).')
    if 'profile' in want and observe_profile(repo) is None:
        add('sandbox_profile_unobservable', 'experiments/local_stream/sandbox.py',
            'sandbox_info() gives no profile digest (sandbox.py absent or unloadable, or no '
            '/usr/bin/sandbox-exec: not macOS); preflight then refuses preflight_rule_failed '
            '(sandbox_profile_sha256 drift). Fix: the full checkout, on macOS.')
    data_dir = repo / 'work' / 'local_stream' / 'data'
    if 'sources' in want:
        for name, spec in lab_data.SOURCES.items():
            found = _find_source(name, data_dir, cache_dirs)
            where = 'work/local_stream/data/%s' % spec['filename']
            pinned = '%d bytes, sha256 %s, %s' % (spec['bytes'], spec['sha256'], spec['url'])
            extra = (' Without it the roster silently becomes S1 and tests_lab_design fails '
                     "on 'S1' != 'EXT'." if not spec['required'] else '')
            if found is None:
                add('pinned_source_missing', where,
                    'untracked roster source not found in work/local_stream/data or %s. Fix: '
                    'put a byte-exact copy there (%s).%s'
                    % (', '.join(str(d) for d in cache_dirs) or 'any cache directory', pinned,
                       extra))
            elif (found.stat().st_size, _sha256(found)) != (spec['bytes'], spec['sha256']):
                add('pinned_source_digest', str(found),
                    'not the pinned bytes (%s); lab_data refuses it.%s' % (pinned, extra))
    if 'pilot_tasks' in want:
        tasks = data_dir / 'tasks.json'
        how = ('Fix: with sanitized-mbpp.json and HumanEval.jsonl.gz in place, run python '
               'experiments/local_stream/data.py (it reuses them; it downloads only a file '
               'that is absent) -> %d bytes, sha256 %s.' % (PILOT_TASKS['bytes'],
                                                           PILOT_TASKS['sha256']))
        if not tasks.is_file():
            add('pilot_tasks_missing', 'work/local_stream/data/tasks.json',
                'untracked pilot task list absent: tests_local_stream loads it at import, so '
                'tests_lab_serving fails to import. ' + how)
        elif _sha256(tasks) != PILOT_TASKS['sha256']:
            add('pilot_tasks_digest', 'work/local_stream/data/tasks.json',
                'not the pilot task list the suites were run with. ' + how)
    if 'history' in want:
        for commit, who in HISTORY.items():
            if not _git_has(repo, commit):
                add('git_history_missing', commit,
                    'not in this clone (shallow, partial or not a git checkout): %s; an '
                    '"OK (skipped=N)" is then not the reproduction. Fix: a full clone '
                    '(no --depth, no --filter).' % who)
    if 'compiler' in want:
        try:
            res = subprocess.run(['clang', '--version'], capture_output=True, text=True,
                                 timeout=60, check=False)
            ok = res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        if not ok:
            add('c_compiler_missing', 'clang',
                'clang --version does not run: sm_fixture.compiled() cannot build the C test '
                'double where no verified cache exists (its consumers then fail with '
                "'sm_fixture: clang failed' or FileNotFoundError). Fix: Xcode command line "
                'tools (the owner host used Apple clang 21.0.0).')
    return out


def environment() -> dict:
    """What this interpreter and host are (reported, never refused)."""
    versions = {}
    for name in ('numpy', 'pandas', 'scipy', 'requests'):
        try:
            versions[name] = __import__(name).__version__
        except Exception as exc:                                 # noqa: BLE001
            versions[name] = 'unavailable: %s' % type(exc).__name__
    return {'python': platform.python_version(), 'executable': sys.executable,
            'platform': sys.platform, 'machine': platform.machine(), 'packages': versions,
            'tmpdir': os.environ.get('TMPDIR')}


def report(found: list[dict]) -> str:
    return '\n'.join('%s  %s: %s' % (p['code'], p['input'], p['message']) for p in found)


def require(repo: Path, suite: str) -> None:
    """Raise :class:`MissingReproductionInputs` naming every input ``suite`` needs that ``repo``
    lacks; return None when there is none."""
    found = problems(repo, suite)
    if found:
        raise MissingReproductionInputs(
            'MISSING REPRODUCTION INPUTS (%d) for %s in %s -- the run would otherwise fail '
            'later, behind digest drift or a skip that names no file:\n%s'
            % (len(found), suite, repo, report(found)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repo', default=str(REPO))
    ap.add_argument('--suite', choices=sorted(SUITES), default='all')
    args = ap.parse_args(argv)
    print('environment: %s' % environment())
    found = problems(Path(args.repo), args.suite)
    if found:
        print('MISSING REPRODUCTION INPUTS (%d) for suite %s:\n%s'
              % (len(found), args.suite, report(found)))
        return 1
    print('reproduction inputs present for suite %s' % args.suite)
    return 0


if __name__ == '__main__':                                       # pragma: no cover
    sys.exit(main())
