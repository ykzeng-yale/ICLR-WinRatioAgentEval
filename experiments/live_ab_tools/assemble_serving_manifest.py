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
design document, and it is not run against ``results/live_ab/freeze/`` in this delivery --
the real artifact and its configuration digest are written with the synchronized pre-outcome
amendment.  Run it from the checkout that will run the trial: paths are tokenized against
that checkout's roots (``<REPO>``, ``<HOME>``, ``<TMP>`` ...), and a manifest assembled in
another checkout names the build differently and is refused there.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import json
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
    args = ap.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    commit = str((config.get('llama_cpp') or {}).get('commit'))
    launcher = Path(args.launcher).absolute() if args.launcher \
        else Path(args.build_dir).absolute() / 'bin' / 'llama-server'
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
