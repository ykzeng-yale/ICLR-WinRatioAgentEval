"""vendor.py -- fetch, verify, vendor and build the AUTHORS' empirical-Bernstein
reference, at the exact pins the root's literature document records.

WHY THIS FILE EXISTS.  The root overruled the default of implementing
Choe-Ramdas Theorem 2 from the theorem statement (COORDINATOR_DECISIONS
revision 16 item 74, issue 12 comment 5754619899):

    "use the PINNED AUTHORS' IMPLEMENTATION as the external reference, not a
    fresh theorem reimplementation as its sole check ... replacing the
    reference with unvalidated new math/code defeats this independent
    comparison.  Your independent implementation may be a separately labeled
    CROSS-CHECK, not the claimed author reference."

The value of an external reference is that someone else wrote it.  So this
file does not implement anything.  It downloads the authors' bytes at a fixed
commit, refuses them unless every SHA-256 matches a hash frozen in this file,
lays them out in an importable tree under ``upstream/``, compiles the authors'
own pybind11 wrapper, and writes ``MANIFEST.json``.

THE PINS ARE FROZEN IN SOURCE, NOT READ FROM THE NETWORK.  ``EXPECTED`` below
is the contract.  A file whose bytes do not hash to its frozen value is a
failure, never a silent update: ``vendor.py`` raises and vendors nothing.
Two of these hashes (``comparecast/confseq.py`` and ``src/confseq/betting.py``)
are quoted verbatim in ``evidence/literature_sequential_design_20260921.md``
under "Key source hashes", so the frozen table can be checked against the root's
own document without trusting this file.

WHAT IS DELIBERATELY NOT VENDORED, and why -- see ``VERIFIED_NOT_VENDORED``.
Vendoring the upstream ``comparecast/__init__.py`` would execute
``from comparecast.plotting import *`` and drag in pandas, matplotlib and
seaborn on import.  The literature document warns about exactly this: "Importing
the whole package can pull in additional dependencies, so an isolated reference
harness should record its actual imports rather than silently patching missing
packages."  So the package initialiser in ``upstream/comparecast/`` is OUR shim,
is marked as ours in the manifest, and is the only non-author Python byte in the
vendored tree.

NOTHING HERE IS IMPORTED BY THE PRIMARY.  ``vrun.py``, ``vgen.py``, ``vband.py``
and ``vcompare.py`` do not import this package and must not; the dependency runs
one way, reference -> primary, and ``tests_validation.py`` asserts it.

Usage:
    .venv/bin/python experiments/live_ab_validation/reference/vendor.py \
        --boost-include /path/to/boost_1_87_0 [--offline-from DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "upstream"
LICENSES = HERE / "licenses"
BUILD = HERE / "_build"
MANIFEST = HERE / "MANIFEST.json"

RAW = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"

# ===========================================================================
# THE PINS.  Repository, commit, upstream path, SHA-256, byte count.
# Commits are the ones the root's literature document inspected and recorded.
# ===========================================================================
COMPARECAST_REPO = "yjchoe/ComparingForecasters"
COMPARECAST_COMMIT = "52748c86e0429a9612dc79892c3be6156a524132"
CONFSEQ_REPO = "gostevehoward/confseq"
CONFSEQ_COMMIT = "5ffe733ca2447a2e28c2c91f3b00086173f2ab2c"

#: ``(repo, commit, upstream_path, local_path, sha256, size)``.  ``local_path``
#: is relative to this directory.  Every one of these is vendored verbatim.
EXPECTED: Tuple[Tuple[str, str, str, str, str, int], ...] = (
    (COMPARECAST_REPO, COMPARECAST_COMMIT, "comparecast/confseq.py",
     "upstream/comparecast/confseq.py",
     "8ea07278021cd06223fa1aa95c3a2aa46ab5be4d5a859d5ed49b5ef5218baef4", 12400),
    (COMPARECAST_REPO, COMPARECAST_COMMIT, "comparecast/utils.py",
     "upstream/comparecast/utils.py",
     "5bc239e18f13deb8b064df9a82b859f8556a11f1f91a39145c1cfba8ade37838", 4536),
    (COMPARECAST_REPO, COMPARECAST_COMMIT, "LICENSE.txt",
     "licenses/ComparingForecasters-LICENSE.txt",
     "11be31dffbbca949a64478dc821a900f6978ab37e7fca30066fc05ee5f088dc1", 1089),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "src/confseq/__init__.py",
     "upstream/confseq/__init__.py",
     "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "src/confseq/boundaries.cpp",
     "upstream/confseq/boundaries.cpp",
     "75818453e7b2ad9d5019aefcc3e52fd073244d2e9459a427661bbc688ef45d7b", 4895),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "src/confseq/uniform_boundaries.h",
     "upstream/confseq/uniform_boundaries.h",
     "2dd72cbfbee7110a49c67d142a58db83750fd653b189e310156d60d65685e21e", 28473),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "LICENSE", "licenses/confseq-LICENSE",
     "2462eb2880ba8e4e1c8c95567939c7d7a46a517370767aade4d7c877169fbbd5", 1075),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "CMakeLists.txt",
     "upstream/confseq/CMakeLists.txt",
     "d8cd3a9580b8c9ac6b2b670c511bac28b9fb2b1b0aaf9cf7cf89740184fa43db", 1109),
)

#: Files FETCHED AND HASH-VERIFIED for provenance but deliberately NOT placed in
#: the importable tree.  Each entry carries the reason, because "we did not
#: vendor it" is only evidence if the reason is on the record.
VERIFIED_NOT_VENDORED: Tuple[Tuple[str, str, str, str, str], ...] = (
    (COMPARECAST_REPO, COMPARECAST_COMMIT, "comparecast/__init__.py",
     "64380b8493e070722a55cc988b822f6e4a43e78a42d27caef6054a6ed4662e08",
     "Upstream package initialiser. Executing it runs `from comparecast.plotting "
     "import *` and 10 sibling star-imports, pulling in pandas, matplotlib and "
     "seaborn. The literature document warns against exactly this. Replaced in "
     "upstream/comparecast/ by OUR shim (marked `vendor_shim` in the manifest), "
     "which is the only non-author Python byte in the vendored tree."),
    (CONFSEQ_REPO, CONFSEQ_COMMIT, "src/confseq/betting.py",
     "c75ee344da46e7652cff40f42e2c879431efd629620d856cd2189ed926cae57b",
     "Hash-verified because the root's literature document quotes this exact "
     "SHA-256, so verifying it confirms the pin table against the root's own "
     "record. NOT vendored: it holds betting_cs/hedged_cs, which the literature "
     "document and the coordinator both forbid substituting for the running-mean "
     "reference ('Do not use confseq_pm_eb merely because its name also includes "
     "EB'). Keeping it out of the importable tree makes that substitution "
     "impossible rather than merely discouraged."),
)

#: The C++ toolchain input.  Boost is a BUILD-TIME dependency of the authors'
#: header (``uniform_boundaries.h`` includes boost/math), not something we
#: vendor: the authors' own wheel workflow does `brew install boost`.  Recorded
#: by URL and archive hash so the build is reproducible.
BOOST_URL = "https://archives.boost.io/release/1.87.0/source/boost_1_87_0.tar.gz"
BOOST_SHA256 = "f55c340aa49763b1925ccf02b2e83f35fdcf634c9d5164a2acb87540173c741d"
BOOST_VERSION = "1.87.0"

#: pybind11 supplies the headers the authors' ``boundaries.cpp`` includes.  It
#: is installed into an ISOLATED --target directory, never into the project
#: venv, so the primary's environment is not changed by this reference.
PYBIND11_VERSION = "2.13.6"

SHIM = '''"""NOT AUTHOR CODE -- a vendor shim written for this repository.

The upstream ``comparecast/__init__.py`` star-imports eleven sibling modules and
so requires pandas, matplotlib and seaborn at import time. The reference needs
exactly two upstream modules, ``comparecast.confseq`` and ``comparecast.utils``,
which between them import only numpy and typing.

This file is therefore intentionally empty of behaviour. It exists so that
``from comparecast.utils import check_bounds`` -- the import statement inside the
authors' unmodified ``confseq.py`` -- resolves. The upstream initialiser's own
SHA-256 is recorded in MANIFEST.json under ``verified_not_vendored``.
"""
'''


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class VendorFailure(RuntimeError):
    """Raised on any fetch, hash or build failure.

    The coordinator's instruction is explicit: "Report import or resource
    failure rather than silently substituting another construction."  Every
    failure path in this file raises; none falls back.
    """


def fetch(repo: str, commit: str, path: str, attempts: List[Dict[str, object]],
          offline_from: Optional[Path]) -> bytes:
    """Fetch one pinned file, recording the attempt whether it works or not."""
    url = RAW.format(repo=repo, commit=commit, path=path)
    started = time.time()
    if offline_from is not None:
        local = offline_from / repo.split("/")[-1] / path
        try:
            blob = local.read_bytes()
            attempts.append({"source": "offline", "path": str(local),
                             "url": url, "ok": True,
                             "bytes": len(blob),
                             "seconds": time.time() - started})
            return blob
        except OSError as exc:
            attempts.append({"source": "offline", "path": str(local),
                             "url": url, "ok": False, "error": repr(exc),
                             "seconds": time.time() - started})
            raise VendorFailure(f"offline source missing: {local}") from exc
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            blob = resp.read()
            code = resp.getcode()
    except (urllib.error.URLError, OSError) as exc:
        attempts.append({"source": "https", "url": url, "ok": False,
                         "error": repr(exc), "seconds": time.time() - started})
        raise VendorFailure(f"fetch failed: {url}: {exc!r}") from exc
    attempts.append({"source": "https", "url": url, "ok": True,
                     "http_status": code, "bytes": len(blob),
                     "seconds": time.time() - started})
    return blob


def verify(blob: bytes, want_sha: str, want_size: int, what: str) -> None:
    got = sha256_bytes(blob)
    if got != want_sha or len(blob) != want_size:
        raise VendorFailure(
            f"PIN MISMATCH for {what}: got sha256={got} size={len(blob)}, "
            f"frozen sha256={want_sha} size={want_size}. Nothing was vendored. "
            f"This is a provenance failure, not something to work around.")


# ---------------------------------------------------------------------------
# the build of the authors' pybind11 wrapper
# ---------------------------------------------------------------------------
def build_boundaries(boost_include: Path, pybind11_include: Path,
                     attempts: List[Dict[str, object]]) -> Path:
    """Compile the authors' UNMODIFIED ``boundaries.cpp`` into an extension.

    No source is patched.  The only inputs are include paths.  ``boundaries.cpp``
    is the authors' own pybind11 wrapper and ``uniform_boundaries.h`` their own
    header, so the compiled module is their implementation, not a bridge we
    wrote.  The authors' CMakeLists is vendored beside it so the flags below can
    be checked against their build (C++14, Boost >= 1.70, pybind11 module).
    """
    BUILD.mkdir(parents=True, exist_ok=True)
    ext = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    out = BUILD / f"boundaries{ext}"
    src = UPSTREAM / "confseq" / "boundaries.cpp"
    py_inc = sysconfig.get_paths()["include"]
    cxx = os.environ.get("CXX", "c++")
    cmd = [cxx, "-O3", "-std=c++14", "-shared", "-fPIC", "-fvisibility=hidden",
           "-I", str(pybind11_include), "-I", str(py_inc), "-I", str(boost_include),
           str(src), "-o", str(out)]
    if sys.platform == "darwin":
        cmd[3:3] = ["-undefined", "dynamic_lookup"]
    started = time.time()
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    attempts.append({
        "source": "build", "command": " ".join(cmd),
        "ok": done.returncode == 0, "returncode": done.returncode,
        "stderr_tail": done.stderr[-2000:], "seconds": time.time() - started})
    if done.returncode != 0:
        raise VendorFailure(
            f"build of the authors' boundaries.cpp FAILED (rc={done.returncode}).\n"
            f"{done.stderr[-4000:]}\n"
            f"Report this failure; do not substitute another construction.")
    return out


def find_pybind11_include(explicit: Optional[str],
                          attempts: List[Dict[str, object]]) -> Path:
    """Locate pybind11 headers, installing into an ISOLATED dir if needed."""
    if explicit:
        return Path(explicit)
    try:
        import pybind11                       # noqa: F401  (may not be present)
        return Path(pybind11.get_include())
    except ImportError:
        pass
    target = BUILD / "builddeps"
    target.mkdir(parents=True, exist_ok=True)
    for installer in (["uv", "pip", "install", "--python", sys.executable,
                       "--target", str(target), f"pybind11=={PYBIND11_VERSION}"],
                      [sys.executable, "-m", "pip", "install", "--target",
                       str(target), f"pybind11=={PYBIND11_VERSION}"]):
        if shutil.which(installer[0]) is None and installer[0] != sys.executable:
            continue
        started = time.time()
        done = subprocess.run(installer, capture_output=True, text=True,
                              timeout=900)
        attempts.append({"source": "install", "command": " ".join(installer),
                         "ok": done.returncode == 0,
                         "returncode": done.returncode,
                         "stderr_tail": done.stderr[-1000:],
                         "seconds": time.time() - started})
        if done.returncode == 0:
            inc = target / "pybind11" / "include"
            if inc.is_dir():
                return inc
    raise VendorFailure(
        "pybind11 headers are not available and could not be installed into an "
        "isolated directory. Report this resource failure.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--boost-include", required=True,
                    help="directory containing boost/ (e.g. .../boost_1_87_0)")
    ap.add_argument("--pybind11-include", default=None)
    ap.add_argument("--offline-from", default=None,
                    help="vendor from an already-downloaded tree instead of "
                         "the network; hashes are still enforced")
    ap.add_argument("--boost-archive", default=None,
                    help="path to the boost tarball, hashed into the manifest")
    args = ap.parse_args(argv)

    attempts: List[Dict[str, object]] = []
    offline = Path(args.offline_from).resolve() if args.offline_from else None

    boost_include = Path(args.boost_include).resolve()
    if not (boost_include / "boost" / "math").is_dir():
        raise VendorFailure(
            f"--boost-include {boost_include} does not contain boost/math. The "
            f"authors' uniform_boundaries.h includes boost/math headers and "
            f"cannot compile without them. Report this resource failure.")

    UPSTREAM.mkdir(parents=True, exist_ok=True)
    LICENSES.mkdir(parents=True, exist_ok=True)

    vendored: List[Dict[str, object]] = []
    for repo, commit, upath, lpath, want_sha, want_size in EXPECTED:
        blob = fetch(repo, commit, upath, attempts, offline)
        verify(blob, want_sha, want_size, f"{repo}@{commit[:12]}:{upath}")
        dest = HERE / lpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        vendored.append({
            "repository": f"https://github.com/{repo}",
            "commit": commit, "upstream_path": upath,
            "vendored_path": str(dest.relative_to(HERE)),
            "sha256": want_sha, "bytes": want_size, "verbatim": True,
            "license": "MIT"})

    not_vendored: List[Dict[str, object]] = []
    for repo, commit, upath, want_sha, reason in VERIFIED_NOT_VENDORED:
        blob = fetch(repo, commit, upath, attempts, offline)
        got = sha256_bytes(blob)
        if got != want_sha:
            raise VendorFailure(
                f"PIN MISMATCH for {repo}@{commit[:12]}:{upath}: got {got}, "
                f"frozen {want_sha}.")
        not_vendored.append({
            "repository": f"https://github.com/{repo}", "commit": commit,
            "upstream_path": upath, "sha256": got, "bytes": len(blob),
            "reason_not_vendored": reason})

    shim = UPSTREAM / "comparecast" / "__init__.py"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(SHIM)
    vendored.append({
        "repository": None, "commit": None, "upstream_path": None,
        "vendored_path": str(shim.relative_to(HERE)),
        "sha256": sha256_file(shim), "bytes": shim.stat().st_size,
        "verbatim": False, "vendor_shim": True,
        "note": "OUR shim, not author code. See VERIFIED_NOT_VENDORED for the "
                "upstream initialiser this replaces and why."})

    pybind11_include = find_pybind11_include(args.pybind11_include, attempts)
    so = build_boundaries(boost_include, pybind11_include, attempts)

    manifest = {
        "schema": "live_ab_validation_v2.reference.manifest.2",
        "role": "DECLARED EXTERNAL REFERENCE. Reported beside the primary, "
                "never instead of it. It can never override any decision, any "
                "gate, any margin or any stopping rule. It is not a "
                "construction in the primary panel and the primary does not "
                "import it.",
        "ruling": "COORDINATOR_DECISIONS revision 16 items 74 and 79; root "
                  "disposition 2026-09-21 02:26 decision 4; issue 12 comments "
                  "5754619899 and 5754667289.",
        "reference_callable": "comparecast.confseq.confseq_eb",
        "reference_paper": "Choe and Ramdas, Comparing Sequential Forecasters, "
                           "Theorem 2 (Operations Research; arXiv 2110.00115v6)",
        "bound_parameters": {
            "v_opt": 10.0, "lo": -1.0, "hi": 1.0,
            "boundary_type": "mixture",
            "alpha": "the existing two-sided per-gate allocation, passed in by "
                     "the caller; confseq_eb applies its own alpha/2 split",
            "v_opt_none_prohibited": True,
            "partial_endpoint_plug_in_prohibited": True,
            "one_sided_prohibited_without_explicit_c": True},
        "generated_unix": time.time(),
        "generated_by": str(Path(__file__).resolve()),
        "vendor_py_sha256": sha256_file(Path(__file__).resolve()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "compiler": os.environ.get("CXX", "c++"),
        "build_dependencies": {
            "boost": {"version": BOOST_VERSION, "url": BOOST_URL,
                      "archive_sha256": BOOST_SHA256,
                      "include_dir_used": str(boost_include),
                      "archive_sha256_recomputed": (
                          sha256_file(Path(args.boost_archive))
                          if args.boost_archive else None),
                      "role": "build-time only; header dependency of the "
                              "authors' uniform_boundaries.h. Not vendored, "
                              "not a runtime dependency of the built module."},
            "pybind11": {"version": PYBIND11_VERSION,
                         "include_dir_used": str(pybind11_include),
                         "role": "build-time only; installed into an isolated "
                                 "--target directory, never into the project "
                                 "venv."}},
        "build_product": {
            "path": str(so.relative_to(HERE)),
            "sha256": sha256_file(so),
            "bytes": so.stat().st_size,
            "built_from": "upstream/confseq/boundaries.cpp (verbatim) + "
                          "upstream/confseq/uniform_boundaries.h (verbatim)",
            "note": "Binary build product, not vendored source. Rebuild with "
                    "vendor.py; the sources it is built from are hashed above."},
        "vendored_files": vendored,
        "verified_not_vendored": not_vendored,
        "licenses": {
            "ComparingForecasters": "MIT, retained verbatim at "
                                    "licenses/ComparingForecasters-LICENSE.txt",
            "confseq": "MIT, retained verbatim at licenses/confseq-LICENSE",
            "pybind11": "BSD-3-Clause, build-time only, not redistributed here"},
        "attempts": attempts,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"vendored {len(vendored)} files, verified-not-vendored "
          f"{len(not_vendored)}, built {so.name}")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VendorFailure as exc:
        print(f"VENDOR FAILURE: {exc}", file=sys.stderr)
        raise SystemExit(2)
