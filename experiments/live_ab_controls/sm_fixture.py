"""A compiled, model-free stand-in for the durable llama.cpp build: the serving-manifest fixture.

Root's serving-manifest ruling (``reviews/serving_manifest_binding_ruling_20260924_0153.md``)
makes every start re-verify "the launcher, recursively resolved non-system libraries, Metal
library, build provenance and ``/props.build_info`` against the actual runtime".  The runtime
closure is re-derived from Mach-O load commands (``lab_serving_manifest``, transcribed from
``live_ab_serving/dependency_closure.py``), so the launcher every control starts must be a
thin Mach-O whose dependency graph ``otool`` can read and whose members do not import
``dlopen`` (the closure contract refuses an unmodelled importer).  Nothing on this host
provides one without compiling: copies of system binaries are killed at exec by the OS launch
constraints (probed: ``cp /bin/sh x; x -c true`` exits 137), and the only other executable,
the uv Python, imports ``dlopen``.

WHAT IS COMPILED, AND WHAT IS NOT.  Three tiny C files, with the host's ``clang``, into a
cache directory under the temporary directory -- never the llama.cpp source, never anything
of the durable build, never a model:

* ``llama-server`` -- a launcher that calls one function of ``libeb1c-core`` (so the dynamic
  loader really loads the closure), reads ``<its own path>.conf`` (interpreter, shim script,
  shim state directory) and ``exec``s ``eb1c_llama_shim.py`` with its argv unchanged: after
  the ``exec`` the recorded pid is the shim's, exactly as with EB1c's ``/bin/sh`` launcher;
* ``libeb1c-core.0.dylib`` (``@rpath``, ``LC_RPATH @loader_path``) -> ``libeb1c-base.0.dylib``,
  a same-directory alias of ``libeb1c-base.0.1.0.dylib`` -- the shape of ``libggml-base`` in
  the real build, so the recursion, the alias binding and the canonical target all run;
* ``libeb1c-base`` carries a ``__DATA,__ggml_metallib`` section, as ``libggml-metal`` carries
  the ``.incbin`` of the Metal kernel sources in the durable build (``GGML_METAL_EMBED_LIBRARY``
  ON), so the embedded-Metal binding runs on the same code path as production.

The build "provenance" beside it is SYNTHETIC and says so: a ``CMakeCache.txt`` with the
durable build's Metal / backend options, a ``common/build-info.cpp`` in the generated form
(build number 6000, commit prefix 8), a durable-rebuild receipt of schema
``live_ab/durable_rebuild-v1`` naming these three files, two log files and a patch file.  A
TEST DOUBLE: nothing it states is an observation of the durable build.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                                       # noqa: E402
import lab_serving_manifest as sm                                       # noqa: E402

COMMIT = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'
BUILD_NUMBER = 6000
#: What the fixture's ``build-info.cpp`` yields (``"b" + number + "-" + LLAMA_COMMIT``).
BUILD_INFO = 'b%d-%s' % (BUILD_NUMBER, COMMIT[:8])

#: Byte strings inside each binary that a control may flip without touching its load
#: commands (``flip``): the file stays a readable Mach-O with a different digest.
LAUNCHER_MARKER = b'eb1c-launcher-marker-0123456789'
CORE_MARKER = b'eb1c-core-marker-0123456789'
BASE_MARKER = b'eb1c-base-marker-0123456789'
METAL_MARKER = b'eb1c-metal-kernel-source'

BASE_C = r'''
__attribute__((used, section("__DATA,__ggml_metallib")))
static const char eb1c_metal_source[] =
    "// eb1c-metal-kernel-source: a test double of the embedded Metal library\n"
    "kernel void eb1c_kernel(device float * x [[buffer(0)]]) { x[0] = 1.0f; }\n";
__attribute__((used)) static const char eb1c_base_marker[] = "eb1c-base-marker-0123456789";
const char *eb1c_base_tag(void) { return eb1c_base_marker; }
'''

CORE_C = r'''
extern const char *eb1c_base_tag(void);
__attribute__((used)) static const char eb1c_core_marker[] = "eb1c-core-marker-0123456789";
const char *eb1c_core_tag(void) { return eb1c_base_tag()[0] == 'e' ? eb1c_core_marker : 0; }
'''

LAUNCHER_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern const char *eb1c_core_tag(void);
__attribute__((used)) static const char eb1c_launcher_marker[] =
    "eb1c-launcher-marker-0123456789";

static int read_line(FILE *f, char *buf, size_t n) {
    if (!fgets(buf, (int)n, f)) return 0;
    buf[strcspn(buf, "\n")] = 0;
    return buf[0] != 0;
}

/* argv[0] is the absolute launcher path (lab_server.server_argv); "<argv[0]>.conf" names the
   interpreter, the shim script and the shim's state directory, one per line. */
int main(int argc, char **argv) {
    char conf[4096], py[2048], shim[2048], state[2048];
    FILE *f;
    char **nv;
    int i;
    if (!eb1c_core_tag()) return 98;
    snprintf(conf, sizeof conf, "%s.conf", argv[0]);
    f = fopen(conf, "r");
    if (!f) return 97;
    if (!read_line(f, py, sizeof py) || !read_line(f, shim, sizeof shim)
            || !read_line(f, state, sizeof state)) { fclose(f); return 96; }
    fclose(f);
    setenv("EB1C_SHIM_STATE", state, 1);
    nv = calloc((size_t)argc + 2, sizeof(char *));
    if (!nv) return 95;
    nv[0] = py;
    nv[1] = shim;
    for (i = 1; i < argc; i++) nv[i + 1] = argv[i];
    execv(py, nv);
    perror("eb1c launcher: execv");
    return 127;
}
'''

CMAKE_CACHE = '''# This is the CMakeCache file of an EB1C TEST DOUBLE (sm_fixture), not of a llama.cpp build.
CMAKE_BUILD_TYPE:STRING=Release
BUILD_SHARED_LIBS:BOOL=ON
//ggml: use Metal
GGML_METAL:BOOL=ON
//ggml: embed Metal library
GGML_METAL_EMBED_LIBRARY:BOOL=ON
//ggml: build backends as dynamic libraries (requires BUILD_SHARED_LIBS)
GGML_BACKEND_DL:BOOL=OFF
//ggml: directory to load dynamic backends from (requires GGML_BACKEND_DL
GGML_BACKEND_DIR:PATH=
'''


def build_info_cpp(commit: str = COMMIT, number: int = BUILD_NUMBER) -> str:
    """The generated ``common/build-info.cpp`` form (from ``build-info.cpp.in``)."""
    return ('#include "build-info.h"\n\n#include <cstdio>\n#include <string>\n\n'
            'int LLAMA_BUILD_NUMBER = %d;\nchar const * LLAMA_COMMIT = "%s";\n'
            'char const * LLAMA_COMPILER = "eb1c test double";\n'
            'char const * LLAMA_BUILD_TARGET = "Darwin arm64";\n' % (number, commit[:8]))


def _sources_key() -> str:
    h = hashlib.sha256()
    for text in (BASE_C, CORE_C, LAUNCHER_C):
        h.update(text.encode('utf-8'))
    return h.hexdigest()[:16]


#: The compiled outputs, with the source MARKERS each must carry (string constants of the
#: C sources above, so they are the same in every compile of THIS module's sources).
OUTPUT_MARKERS = {'llama-server': (LAUNCHER_MARKER,),
                  'libeb1c-core.0.dylib': (CORE_MARKER,),
                  'libeb1c-base.0.1.0.dylib': (BASE_MARKER, METAL_MARKER)}
#: The record ``compiled()`` writes beside its outputs, and the log of every use.
CACHE_MANIFEST = 'sm_fixture_manifest.json'
USES_LOG = 'eb1c_sm_fixture_uses.jsonl'


def _tool_version(argv: list) -> str:
    try:
        res = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return 'unavailable'
    return ((res.stdout or res.stderr).splitlines() or ['unavailable'])[0].strip()


def cache_problems(cache: Path) -> list:
    """[read-only] Why the cache directory ``cache`` is NOT the output of ``compiled()`` for
    this module's sources (``[]`` when it is): its :data:`CACHE_MANIFEST` is missing or
    unreadable, names another sources key, or its outputs' SHA-256 are not the ones it
    recorded at compile time, or an output lacks its source markers (:data:`OUTPUT_MARKERS`).
    Review of 988baf7 (reviewer 2): the cache used to be trusted by its NAME alone -- binaries
    compiled from other C source, planted under the key, were served to every control.
    Does NOT perform: an independent rebuild (the outputs are not byte-reproducible), so a
    cache planted WITH a forged manifest and the committed markers is not detected."""
    out = []
    try:
        man = json.loads((cache / CACHE_MANIFEST).read_text('utf-8'))
    except (OSError, ValueError):
        return ['manifest_unreadable']
    if not isinstance(man, dict) or man.get('sources_key') != _sources_key():
        out.append('sources_key')
    recorded = (man.get('outputs') or {}) if isinstance(man, dict) else {}
    for name, markers in OUTPUT_MARKERS.items():
        try:
            data = (cache / name).read_bytes()
        except OSError:
            out.append('missing:%s' % name)
            continue
        if hashlib.sha256(data).hexdigest() != recorded.get(name):
            out.append('digest:%s' % name)
        if not all(m in data for m in markers):
            out.append('markers:%s' % name)
    return out


def _log_use(cache: Path, event: str) -> dict:
    """Append one line to ``<tempdir>/`` :data:`USES_LOG`: which binaries this process is
    about to execute (their SHA-256 and the compiler that built them) -- the record a suite
    run leaves of the test double it actually used."""
    try:
        man = json.loads((cache / CACHE_MANIFEST).read_text('utf-8'))
    except (OSError, ValueError):
        man = {}
    row = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'pid': os.getpid(),
           'event': event, 'cache': str(cache), 'sources_key': man.get('sources_key'),
           'outputs': man.get('outputs'), 'clang_version': man.get('clang_version'),
           'ld_version': man.get('ld_version')}
    try:
        with open(cache.parent / USES_LOG, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, sort_keys=True) + '\n')
    except OSError:
        pass
    return row


def compiled() -> Path:
    """The directory holding the three compiled binaries, compiled at most once per source
    digest (a cache under the temporary directory; concurrent callers race to an atomic
    rename, and the loser's copy is discarded).  A cache is used only when
    :func:`cache_problems` finds nothing: its manifest (written here at compile time: sources
    key, output SHA-256, ``clang --version``, ``ld -v``) must match the files and each output
    must carry its source markers.  An untrusted cache is moved aside
    (``<name>.untrusted.<ns>``) and the sources are compiled again.  Every return is logged
    (:func:`_log_use`)."""
    cache = Path(os.path.realpath(tempfile.gettempdir())) / ('eb1c_sm_fixture_%s'
                                                              % _sources_key())
    if cache.exists():
        if not cache_problems(cache):
            _log_use(cache, 'cache_verified')
            return cache
        try:
            os.rename(str(cache), '%s.untrusted.%d' % (cache, time.monotonic_ns()))
        except OSError:
            pass
    work = Path(tempfile.mkdtemp(prefix='eb1c_sm_compile_', dir=str(cache.parent)))
    try:
        (work / 'base.c').write_text(BASE_C, encoding='utf-8')
        (work / 'core.c').write_text(CORE_C, encoding='utf-8')
        (work / 'launcher.c').write_text(LAUNCHER_C, encoding='utf-8')
        for argv in (
                ['clang', '-dynamiclib', '-O0', '-o', 'libeb1c-base.0.1.0.dylib',
                 '-install_name', '@rpath/libeb1c-base.0.dylib', 'base.c'],
                ['ln', '-s', 'libeb1c-base.0.1.0.dylib', 'libeb1c-base.0.dylib'],
                ['clang', '-dynamiclib', '-O0', '-o', 'libeb1c-core.0.dylib',
                 '-install_name', '@rpath/libeb1c-core.0.dylib', 'core.c', '-L.',
                 '-leb1c-base.0', '-Wl,-rpath,@loader_path'],
                ['clang', '-O0', '-o', 'llama-server', 'launcher.c', '-L.', '-leb1c-core.0',
                 '-Wl,-rpath,@executable_path']):
            res = subprocess.run(argv, cwd=str(work), capture_output=True, text=True,
                                 timeout=120, check=False)
            if res.returncode != 0:
                raise RuntimeError('sm_fixture: %s failed: %s' % (argv[0], res.stderr[-400:]))
        for name in ('base.c', 'core.c', 'launcher.c'):
            (work / name).unlink()
        (work / CACHE_MANIFEST).write_text(json.dumps({
            'sources_key': _sources_key(),
            'outputs': {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                        for name in OUTPUT_MARKERS},
            'clang_version': _tool_version(['clang', '--version']),
            'ld_version': _tool_version(['ld', '-v'])}, indent=1, sort_keys=True) + '\n',
            encoding='utf-8')
        try:
            os.rename(str(work), str(cache))
        except OSError:
            shutil.rmtree(str(work), ignore_errors=True)
    except BaseException:
        shutil.rmtree(str(work), ignore_errors=True)
        raise
    problems = cache_problems(cache)
    if problems:
        raise RuntimeError('sm_fixture: the compiled cache does not verify: %s' % problems)
    _log_use(cache, 'compiled')
    return cache


def clang_version() -> str:
    res = subprocess.run(['clang', '--version'], capture_output=True, text=True, timeout=60,
                         check=False)
    return (res.stdout.splitlines() or ['clang'])[0]


def flip(path: Path, marker: bytes, *, resign: bool = False) -> None:
    """XOR ONE byte inside ``marker`` in the file at ``path`` (in place).  The load commands
    are untouched, so the file is still read as the same Mach-O; only its bytes differ.

    The flipped file's code signature no longer matches, so the loader would kill a process
    that maps it (probed: exit -9).  ``resign=True`` then re-signs it ad hoc (``codesign -f
    -s -``, as the linker signed it), so the changed file is still LOADABLE -- what a
    different build of the same library would be; a self-comparison mutant of the checker
    then visibly serves it instead of dying at exec."""
    data = bytearray(Path(path).read_bytes())
    at = data.find(marker)
    if at < 0:
        raise AssertionError('marker %r not in %s' % (marker, path))
    data[at + 5] ^= 0x01
    Path(path).write_bytes(bytes(data))
    if resign:
        res = subprocess.run(['codesign', '-f', '-s', '-', str(path)], capture_output=True,
                             text=True, timeout=60, check=False)
        if res.returncode != 0:
            raise RuntimeError('sm_fixture: codesign failed: %s' % res.stderr[-300:])


class Build:
    """One control's "durable build": the compiled launcher and libraries in ``build/bin``,
    the synthetic ``CMakeCache.txt`` and ``build-info.cpp``, and the provenance files.

    ``root`` is canonicalized (the closure contract requires the canonical launcher path).
    ``shim`` is the script the launcher ``exec``s (EB1c's shim by default; C10 passes a
    symlink whose name the host gate reads as a llama-server)."""

    def __init__(self, root: Path, *, state: Path, shim: Path | None = None,
                 commit: str = COMMIT, build_number: int = BUILD_NUMBER) -> None:
        self.root = Path(os.path.realpath(str(root)))
        self.commit = commit
        self.build = self.root / 'build'
        self.bin = self.build / 'bin'
        self.bin.mkdir(parents=True, exist_ok=True)
        src = compiled()
        for name in ('llama-server', 'libeb1c-core.0.dylib', 'libeb1c-base.0.1.0.dylib'):
            shutil.copy2(str(src / name), str(self.bin / name))
        os.symlink('libeb1c-base.0.1.0.dylib', str(self.bin / 'libeb1c-base.0.dylib'))
        self.launcher = self.bin / 'llama-server'
        self.core = self.bin / 'libeb1c-core.0.dylib'
        self.base = self.bin / 'libeb1c-base.0.1.0.dylib'
        self.state = Path(state)
        self.set_shim(shim or (HERE / 'eb1c_llama_shim.py'))
        (self.build / 'CMakeCache.txt').write_text(CMAKE_CACHE, encoding='utf-8')
        (self.build / 'common').mkdir()
        (self.build / 'common' / 'build-info.cpp').write_text(
            build_info_cpp(commit, build_number), encoding='utf-8')
        prov = self.root / 'provenance'
        prov.mkdir()
        self.patch = prov / 'live_ab_slot_lifecycle.patch'
        self.patch.write_text('eb1c test double: not the lifecycle patch\n', encoding='utf-8')
        self.build_log = prov / 'DURABLE_REBUILD_eb1c_build.log'
        self.build_log.write_text('eb1c test double: no build ran\n', encoding='utf-8')
        self.configure_log = prov / 'DURABLE_REBUILD_eb1c_configure.log'
        self.configure_log.write_text('eb1c test double: no configure ran\n',
                                      encoding='utf-8')
        self.receipt = prov / 'DURABLE_REBUILD_eb1c.json'
        self.write_receipt()

    def set_shim(self, shim: Path) -> None:
        """(Re)write ``llama-server.conf``: interpreter, shim script, shim state directory.
        The conf is not a closure member (the launcher reads it at run time, as the real
        launcher reads its argv); the manifest does not bind it."""
        (self.bin / 'llama-server.conf').write_text(
            '%s\n%s\n%s\n' % (sys.executable, shim, self.state), encoding='utf-8')

    def write_receipt(self) -> None:
        """The durable-rebuild receipt of THIS double: its members are the three files'
        canonical paths and current digests (rewrite it after changing a file on purpose)."""
        members = {}
        for path in (self.launcher, self.core, self.base):
            members[path.name] = {'path': str(path), 'canonical': os.path.realpath(str(path)),
                                  'bytes': path.stat().st_size,
                                  'sha256': lab_common.sha256_file(path)}
        receipt = {
            'schema': sm.RECEIPT_SCHEMA,
            'what_this_is': 'EB1C TEST DOUBLE (sm_fixture): a compiled stand-in, not a '
                            'llama.cpp build; nothing here is an observation of one',
            'build_succeeded': True,
            'source_state': {'head': self.commit, 'pinned_commit': self.commit,
                             'patch_sha256': lab_common.sha256_file(self.patch)},
            'protocol_2_2_item_1': {
                'build_exit': 0, 'configure_exit': 0,
                'build_log_sha256': lab_common.sha256_file(self.build_log),
                'configure_log_sha256': lab_common.sha256_file(self.configure_log),
                'cmake_options': ['-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
                                  '-DGGML_METAL=ON'],
                'toolchain': {'compiler': clang_version(), 'sdk': 'eb1c-test-double'}},
            'members': members,
        }
        self.receipt.write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n',
                                encoding='utf-8')

    def provenance(self) -> dict:
        return {'build_receipt': str(self.receipt), 'build_log': str(self.build_log),
                'configure_log': str(self.configure_log),
                'cmake_cache': str(self.build / 'CMakeCache.txt'),
                'build_info_source': str(self.build / 'common' / 'build-info.cpp'),
                'patch': str(self.patch)}

    def manifest(self) -> dict:
        """``lab_serving_manifest.assemble`` of this double (the pure function)."""
        return sm.assemble(self.launcher, self.provenance(), llama_commit=self.commit)

    def write_manifest(self, freeze_dir: Path) -> str:
        """Assemble and write THE artifact of ``freeze_dir`` (write-once); returns the digest
        the configuration's ``llama_cpp.serving_manifest_sha256`` must hold."""
        return sm.write_artifact(sm.artifact_path(Path(os.path.realpath(str(freeze_dir)))),
                                 self.manifest())

    def tool_argv(self, out: Path) -> list:
        """The assembler TOOL's command line for this double."""
        return [sys.executable, str(HERE.parent / 'live_ab_tools' /
                                    'assemble_serving_manifest.py'),
                '--launcher', str(self.launcher), '--build-dir', str(self.build),
                '--build-receipt', str(self.receipt), '--build-log', str(self.build_log),
                '--configure-log', str(self.configure_log), '--patch', str(self.patch),
                '--out', str(out)]

    def add_discoverable_library(self, name: str = 'libggml-eb1c.so') -> Path:
        """A library ggml's backend registry would load from the executable directory
        (``libggml-*.so``, the search the closure enumerates), added AFTER assembly: a copy
        of the core library, a real Mach-O."""
        target = self.bin / name
        shutil.copy2(str(self.core), str(target))
        return target
