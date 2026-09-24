"""Assemble the frozen serving manifest of protocol 2.2 item 2 from a durable build.

Root, ``reviews/serving_manifest_binding_ruling_20260924_0153.md``: "Assemble it from the
pinned durable build before freeze; hash its canonical content and put that digest in the
config and bundle."  This tool is the command-line face of the PURE assembler
``lab_serving_manifest.assemble`` (harness pin); it performs nothing the harness does not.

    python assemble_serving_manifest.py --build-dir <LLAMA_BUILD>/build \\
        --build-receipt results/live_ab/DURABLE_REBUILD_20260923T192024Z.json \\
        --out <freeze tree>/serving_manifest.json

What it does, in order:

1. reads the commit from ``--config`` (``llama_cpp.commit``; default the live configuration);
2. ``lab_serving_manifest.assemble``: the launcher's recursively resolved non-system closure
   (``otool``/``nm`` metadata, nothing executed), the embedded Metal library, ``LC_RPATH``,
   and the build provenance files -- the receipt, the build and configure logs (default: the
   receipt's ``_build.log`` / ``_configure.log`` siblings), ``<build-dir>/CMakeCache.txt``,
   ``<build-dir>/common/build-info.cpp`` and the lifecycle patch -- each re-hashed; any
   problem refuses (exit 2) and nothing is written;
3. re-verifies the assembled object against the same build at once
   (``lab_serving_manifest.runtime_problems``; a non-empty answer refuses, exit 2);
4. with ``--out``: writes it ONCE (``lab_serving_manifest.write_artifact``: the path must be a
   ``.../freeze/serving_manifest.json``, an existing file is never replaced) and reads it
   back; without it, writes nothing;
5. prints ``{out, serving_manifest_sha256, bytes, libraries, metal_library}`` as JSON.  The
   digest is the value ``config.llama_cpp.serving_manifest_sha256`` must hold.

NOT done here, by design: the tool never edits ``config.json``, the freeze bundle or any
design document.  The real artifact ``results/live_ab/freeze/serving_manifest.json`` and its
configuration digest are written by the synchronized pre-outcome amendment
(``repair_amendment_v2.py``), which calls this file's :func:`provenance_paths`,
:func:`repo_root_problems` and :func:`repo_roots` and the same ``lab_serving_manifest``
functions in process.  Run it from the checkout that will run the trial: paths are tokenized against
that checkout's roots (``<REPO>``, ``<HOME>``, ``<TMP>`` ...), and a manifest assembled in
another checkout names the build differently and is refused there.

``--repo-root`` (added by the synchronized pre-outcome amendment, 2026-09-24, repair session
60): assemble and re-verify AS SEEN FROM another checkout -- the one that will run the trial --
without running from it.  ``lab_common`` fixes its three token roots from its own file location
(``REPO_ROOT = HERE.parents[1]``, ``RESULTS_ROOT = REPO_ROOT / 'results' / 'live_ab'``,
``WORK_ROOT = REPO_ROOT / 'work' / 'live_ab'``); :func:`repo_roots` rebinds exactly those three
for the duration of the call, so ``lab_common.tokenize_path`` and
``lab_serving_manifest.resolve_token`` answer as a process started from that checkout would.
What it performs first (:func:`repo_root_problems`): the root is absolute and canonical, holds
``experiments/live_ab/lab_common.py``, and that file defines the three roots by exactly the
lines :data:`ROOT_DEFINITIONS` (the lines this file's rebinding reproduces), as does this
checkout's ``lab_common``.  It reads the other checkout; it never writes there.  Without
``--repo-root`` nothing is rebound (the default is this checkout).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402
import lab_serving_manifest as sm                              # noqa: E402

DEFAULT_PATCH = HERE.parent / 'live_ab_serving' / 'live_ab_slot_lifecycle.patch'
DEFAULT_CONFIG = LAB / 'config.json'

#: The three lines of ``experiments/live_ab/lab_common.py`` that fix the token roots
#: (``lab_common._token_roots``) from the module's own location.  :func:`repo_roots` rebinds
#: exactly these three, as those lines would compute them in the checkout at ``repo_root``;
#: :func:`repo_root_problems` refuses a checkout (or this one) whose file says otherwise.
ROOT_DEFINITIONS: tuple[str, ...] = (
    'REPO_ROOT: Path = HERE.parents[1]',
    "RESULTS_ROOT: Path = REPO_ROOT / 'results' / 'live_ab'",
    "WORK_ROOT: Path = REPO_ROOT / 'work' / 'live_ab'",
)


def repo_root_problems(repo_root: str | Path) -> list[str]:
    """[reads files only] Why ``repo_root`` cannot stand for the checkout that runs the trial:
    ``repo_root_not_canonical`` (not absolute, or not its own ``os.path.realpath``: the token
    roots are compared on both spellings, and a non-canonical root would be a third one);
    ``repo_root_no_lab_common`` (no ``experiments/live_ab/lab_common.py`` there);
    ``repo_root_definitions`` / ``this_checkout_definitions`` (that file, or this checkout's
    ``lab_common.py``, does not carry each line of :data:`ROOT_DEFINITIONS` exactly once, so
    the rebinding would not be what the file computes).  ``[]`` when none applies."""
    root = str(repo_root)
    problems: list[str] = []
    if not os.path.isabs(root) or os.path.realpath(root) != root:
        problems.append('repo_root_not_canonical')
    source = Path(root) / 'experiments' / 'live_ab' / 'lab_common.py'
    try:
        lines = source.read_text(encoding='utf-8').splitlines()
    except OSError:
        return problems + ['repo_root_no_lab_common']
    if any(lines.count(d) != 1 for d in ROOT_DEFINITIONS):
        problems.append('repo_root_definitions')
    ours = (LAB / 'lab_common.py').read_text(encoding='utf-8').splitlines()
    if any(ours.count(d) != 1 for d in ROOT_DEFINITIONS):
        problems.append('this_checkout_definitions')
    return problems


@contextlib.contextmanager
def repo_roots(repo_root: str | Path | None):
    """Rebind ``lab_common.REPO_ROOT`` / ``RESULTS_ROOT`` / ``WORK_ROOT`` to the values
    :data:`ROOT_DEFINITIONS` give in the checkout at ``repo_root`` for the duration of the
    block, and restore them afterwards (also on an exception).  ``None`` rebinds nothing.
    Performs no check itself: callers run :func:`repo_root_problems` first."""
    if repo_root is None:
        yield
        return
    saved = (lab_common.REPO_ROOT, lab_common.RESULTS_ROOT, lab_common.WORK_ROOT)
    root = Path(str(repo_root))
    lab_common.REPO_ROOT = root
    lab_common.RESULTS_ROOT = root / 'results' / 'live_ab'
    lab_common.WORK_ROOT = root / 'work' / 'live_ab'
    try:
        yield
    finally:
        lab_common.REPO_ROOT, lab_common.RESULTS_ROOT, lab_common.WORK_ROOT = saved


def provenance_paths(args: argparse.Namespace) -> dict:
    """Role -> absolute path of every build-provenance file the manifest binds."""
    build_dir = Path(args.build_dir).absolute()
    receipt = Path(args.build_receipt).absolute()
    stem = receipt.with_suffix('')
    return {
        'build_receipt': str(receipt),
        'build_log': str(Path(args.build_log).absolute() if args.build_log
                         else Path(str(stem) + '_build.log')),
        'configure_log': str(Path(args.configure_log).absolute() if args.configure_log
                             else Path(str(stem) + '_configure.log')),
        'cmake_cache': str(build_dir / 'CMakeCache.txt'),
        'build_info_source': str(build_dir / 'common' / 'build-info.cpp'),
        'patch': str(Path(args.patch).absolute()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='assemble_serving_manifest')
    ap.add_argument('--build-dir', required=True, help='<LLAMA_BUILD>/build')
    ap.add_argument('--launcher', default=None,
                    help='default <build-dir>/bin/llama-server; must be canonical')
    ap.add_argument('--build-receipt', required=True)
    ap.add_argument('--build-log', default=None)
    ap.add_argument('--configure-log', default=None)
    ap.add_argument('--patch', default=str(DEFAULT_PATCH))
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--out', default=None,
                    help='<freeze tree>/serving_manifest.json, written once; omit to only '
                         'print the digest')
    ap.add_argument('--repo-root', default=None,
                    help='the canonical root of the checkout that will run the trial; paths '
                         'are tokenized and resolved as seen from it (default: this checkout)')
    args = ap.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    commit = str((config.get('llama_cpp') or {}).get('commit'))
    launcher = Path(args.launcher).absolute() if args.launcher \
        else Path(args.build_dir).absolute() / 'bin' / 'llama-server'
    if args.repo_root is not None:
        problems = repo_root_problems(args.repo_root)
        if problems:
            print(json.dumps({'refused': problems}, indent=1))
            return 2
    with repo_roots(args.repo_root):
        try:
            manifest = sm.assemble(launcher, provenance_paths(args), llama_commit=commit)
        except sm.ManifestError as exc:
            print(json.dumps({'refused': exc.problems}, indent=1))
            return 2
        again = sm.runtime_problems(manifest, launcher=launcher, llama_commit=commit)
        if again:
            print(json.dumps({'refused': ['does_not_reverify_at_once'] + again}, indent=1))
            return 2
        digest = lab_common.sha256_canonical(manifest)
        out = None
        if args.out:
            try:
                digest = sm.write_artifact(Path(args.out).absolute(), manifest)
            except (sm.ManifestError, lab_common.WriteOnceViolation) as exc:
                print(json.dumps({'refused': [type(exc).__name__, str(exc)]}, indent=1))
                return 2
            out = lab_common.display_path(Path(args.out).absolute())
    print(json.dumps({'out': out, 'serving_manifest_sha256': digest,
                      'bytes': len(lab_common.canonical_json(manifest)) + 1,
                      'libraries': len(manifest['libraries']),
                      'metal_library': manifest['metal_library'].get('kind')},
                     indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
