"""The frozen serving manifest of protocol 2.2 item 2: ONE tracked, write-once artifact, its
assembly from the pinned durable build, and its re-verification against the actual runtime.

Root, ``reviews/serving_manifest_binding_ruling_20260924_0153.md`` (origin/main 6a8e644):
"use ``results/live_ab/freeze/serving_manifest.json`` as the single tracked, write-once frozen
copy.  Assemble it from the pinned durable build before freeze; hash its canonical content and
put that digest in the config and bundle. ... Preflight and every invocation/start/restart
must read that exact artifact and re-check its digest and the launcher, recursively resolved
non-system libraries, Metal library, build provenance and ``/props.build_info`` against the
actual runtime as protocol §2.2 requires.  A missing file, null digest, self-comparison, path
substitution or runtime mismatch refuses."  This module replaces EB1a's invented handling
(``lab_orchestrator.SERVING_MANIFEST_FILE`` / ``load_serving_manifest`` and
``lab_server.serving_manifest_problems``, which checked listed libraries by base name beside
the launcher); nothing of it is kept.

What the module PERFORMS, and where:

* **The artifact** (:func:`artifact_path`, :func:`read_artifact`, :func:`verify_artifact`):
  exactly ``<freeze tree>/serving_manifest.json`` -- the freeze tree being
  ``<results root>/freeze``, so in the repository ``results/live_ab/freeze/
  serving_manifest.json`` (:data:`TRACKED_RELPATH`).  The file must be a regular file (a
  symlink is a substituted path), its bytes must be its canonical JSON plus one newline (the
  form :func:`write_artifact` writes, once), and ``sha256_canonical`` of its object must equal
  the configuration's ``llama_cpp.serving_manifest_sha256``, which must be a 64-hex digest (a
  null digest refuses: nothing is inferred from it).  :func:`override_problems` refuses any
  runtime or configuration key that would name another location.
* **The runtime facts** (:func:`runtime_facts`), each MEASURED now, never read from the
  manifest: the launcher's path and SHA-256; the recursively resolved non-system dependency
  closure, re-derived from the Mach-O load commands under the launch context the server will
  actually get (:func:`verify_closure` below re-resolves every edge and re-hashes every member;
  a member added, removed, moved or changed refuses); the launcher's resolved ``LC_RPATH``;
  the Metal library binding (:func:`metal_binding`); the build provenance, re-read and
  re-hashed from the provenance files (:func:`read_provenance`); and the ``/props.build_info``
  the build's own ``build-info.cpp`` produces.  :func:`compare_facts` compares them with
  :func:`recorded_facts` of the manifest, field by field.  The server's ACTUAL
  ``/props.build_info`` is compared by :func:`props_build_info_problems` once the server
  answers (``lab_server.start``).
* **The assembler** (:func:`assemble`) builds the manifest content from a given durable build
  with the SAME measuring functions, so the frozen object and every later observation are
  produced by one implementation.  The tool is ``experiments/live_ab_tools/
  assemble_serving_manifest.py``; it writes a file only where it is told to.

The dependency closure: THE DERIVATION IS TRANSCRIBED, NOT IMPORTED.  Execution code must be
inside the harness pin (repair contract, fixed placement), and ``experiments/live_ab_serving/
dependency_closure.py`` (sha256 ``f581ff93...``, root-reviewed at 14:03, 14:41 and 16:30) is
outside it and is itself pinned by ``run_smoke.ACQUISITION_CODE``, so it is neither imported
nor edited.  Its constants and functions from ``SCHEMA`` through ``verify_closure`` are copied
below VERBATIM.  Agreement is kept by two controls in ``experiments/live_ab_controls/
tests_sm_manifest.py``: every transcribed top-level statement's AST must equal the original's
(any edit to either side fails it), and the original's whole root-reviewed test class
``tests_dependency_closure.DependencyClosureTests`` is run again with this module in its place.

Not modelled, and therefore REFUSED rather than assumed: a Metal library that is not embedded
(the non-embedded search -- bundle resources, ``GGML_METAL_PATH_RESOURCES``, the working
directory -- is not bounded here; the durable build embeds it: ``GGML_METAL_EMBED_LIBRARY:
BOOL=ON`` in its ``CMakeCache.txt``, the ``.incbin`` of ``ggml-metal-embed-*.s`` into
``__DATA,__ggml_metallib`` of ``libggml-metal``, and the external branch of
``ggml-metal-device.m`` compiled out); a fat Mach-O; anything outside the supported profile of
the transcribed closure.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import lab_common

#: The manifest object's own schema (the closure inside it keeps :data:`SCHEMA`).
MANIFEST_SCHEMA: str = 'live_ab/serving_manifest-v1'
#: The artifact's file name and the directory that holds it, both FIXED.
ARTIFACT_NAME: str = 'serving_manifest.json'
FREEZE_DIR_NAME: str = 'freeze'
#: The tracked location in the repository (root 01:53).
TRACKED_RELPATH: str = 'results/live_ab/freeze/serving_manifest.json'
#: ``config.llama_cpp.<CONFIG_DIGEST_KEY>`` holds the artifact's canonical digest.
CONFIG_DIGEST_KEY: str = 'serving_manifest_sha256'
#: Where the embedded Metal library lives (``ggml/src/ggml-metal/CMakeLists.txt`` at the
#: pinned commit: ``.section __DATA,__ggml_metallib`` + ``.incbin``).
METAL_SEGMENT: str = '__DATA'
METAL_SECTION: str = '__ggml_metallib'
#: The durable-build receipt schema (``experiments/live_ab_tools/durable_rebuild.py``).
RECEIPT_SCHEMA: str = 'live_ab/durable_rebuild-v1'
#: The build-provenance files, by role.  Each is recorded as ``{path (tokenized), bytes,
#: sha256}`` and RE-HASHED at runtime.
PROVENANCE_ROLES: tuple[str, ...] = ('build_receipt', 'build_log', 'configure_log',
                                     'cmake_cache', 'build_info_source', 'patch')
#: The members of a manifest.  The first twelve are protocol 2.2's field names.
MANIFEST_KEYS: tuple[str, ...] = (
    'llama_cpp_commit', 'launcher_sha256', 'libraries', 'metal_library', 'resolved_rpath',
    'cmake_options', 'compiler_version', 'sdk_version', 'build_log_sha256',
    'configure_log_sha256', 'props_build_info',
    'schema', 'launcher', 'closure', 'build')
#: The facts :func:`runtime_facts` measures and :func:`recorded_facts` reads back.
FACT_KEYS: tuple[str, ...] = (
    'launcher', 'closure', 'resolved_rpath', 'metal_library', 'build', 'cmake_options',
    'compiler_version', 'sdk_version', 'build_log_sha256', 'configure_log_sha256',
    'props_build_info')


class ManifestError(lab_common.LabError):
    """The assembler refused: ``problems`` names every reason (never a partial manifest)."""

    def __init__(self, problems: List[str]) -> None:
        super().__init__('; '.join(problems))
        self.problems = list(problems)


# =========================================================================== #
# TRANSCRIBED VERBATIM from experiments/live_ab_serving/dependency_closure.py
# (sha256 f581ff9378d1c8e004dc3c0e50ef29b85ea5c7eacbf00d6b9cfa73e2384e02ce), from SCHEMA
# through verify_closure.  Do not edit here without editing there: tests_sm_manifest compares
# the two ASTs statement by statement and reruns the original's test class on this module.
# =========================================================================== #
SCHEMA = 'live_ab/dependency_closure-v3'

#: Prefixes whose members are OS-provided. Root, 12:42: "System library names
#: are sufficient here when linked to the already required OS build/architecture
#: /runtime provenance; separately hashing `libSystem` and `libc++` is not an
#: added requirement." They are RECORDED, never pinned, and never traversed.
SYSTEM_PREFIXES = ('/usr/lib/', '/System/')

#: Load-reference prefixes that a search environment must resolve.
_AT_RPATH = '@rpath/'
_AT_LOADER = '@loader_path/'
_AT_EXEC = '@executable_path/'

#: Commands that ADD A FILE to what loads. Each becomes an edge. A weak edge is
#: still required to resolve: if its file exists it loads, so it must be bound.
DEPENDENCY_COMMANDS = ('LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
                       'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB')
#: Commands that change WHERE an edge resolves.
CONTEXT_COMMANDS = ('LC_RPATH',)
#: Commands known to carry no load or search effect. A CLOSED list: anything
#: outside it and the two tuples above refuses, so a command type this module
#: has not been taught -- `LC_DYLD_ENVIRONMENT`, which sets loader variables
#: from inside the binary, is the example that matters -- cannot pass silently.
NON_DEPENDENCY_COMMANDS = frozenset((
    'LC_SEGMENT', 'LC_SEGMENT_64', 'LC_SYMTAB', 'LC_DYSYMTAB', 'LC_ID_DYLIB',
    'LC_LOAD_DYLINKER', 'LC_UUID', 'LC_BUILD_VERSION', 'LC_VERSION_MIN_MACOSX',
    'LC_SOURCE_VERSION', 'LC_MAIN', 'LC_FUNCTION_STARTS', 'LC_DATA_IN_CODE',
    'LC_CODE_SIGNATURE', 'LC_DYLD_INFO', 'LC_DYLD_INFO_ONLY',
    'LC_DYLD_CHAINED_FIXUPS', 'LC_DYLD_EXPORTS_TRIE',
    'LC_LINKER_OPTIMIZATION_HINT', 'LC_SEGMENT_SPLIT_INFO', 'LC_NOTE',
    'LC_DYLIB_CODE_SIGN_DRS', 'LC_ATOM_INFO', 'LC_ENCRYPTION_INFO_64',
    'LC_LINKER_OPTION'))

#: What the pinned loader source can open in a search location
#: (ggml/src/ggml-backend-reg.cpp at 4fea119: `libggml-<name>-*.so` scored and
#: `libggml-<name>.so` base, via `is_regular_file`, which follows symlinks).
#: Enumerated as the SUPERSET `libggml-*.so`, so a backend name added to the
#: source's list is still covered.
DISCOVERY_PREFIX = 'libggml-'
DISCOVERY_SUFFIX = '.so'

#: The ONLY `dlopen` importer whose search is modelled here: ggml's registry,
#: whose search locations and patterns are read from the pinned source above
#: and whose build (GGML_BACKEND_DL OFF, no compiled GGML_BACKEND_DIR) is
#: established in results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json. Any
#: other importer -- including a discovered backend -- opens paths this module
#: does not model, and refuses.
MODELLED_DLOPEN_INSTALL_NAMES = ('@rpath/libggml.0.dylib',)

#: Environment names that change what the loader resolves or opens.
LOADER_ENV_PREFIX = 'DYLD_'
BACKEND_PATH_ENV = 'GGML_BACKEND_PATH'

LAUNCH_CONTEXT_FIELDS = ('executable_invoked_path', 'cwd', 'compiled_backend_dir',
                         'environment')


def is_system_reference(ref: str) -> bool:
    return any(ref.startswith(p) for p in SYSTEM_PREFIXES)


# -- stage zero: reading metadata, failing closed -----------------------------
def parse_mach_header(text: str) -> Dict[str, Any]:
    """`otool -h`. One header only: a fat file's architecture selection is not
    something this contract bounds."""
    headers = text.count('Mach header')
    if headers != 1:
        return {'error': 'expected one Mach header, found %d' % headers}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'ncmds' in line.split() and i + 1 < len(lines):
            cols, vals = line.split(), lines[i + 1].split()
            if len(cols) == len(vals):
                try:
                    return {'ncmds': int(dict(zip(cols, vals))['ncmds'])}
                except ValueError:
                    break
    return {'error': 'the Mach header has no readable ncmds'}


def parse_load_commands(text: str, *, ncmds: Optional[int] = None) -> Dict[str, Any]:
    """`otool -l`, classified command by command against the closed lists.

    Pure, so the fail-closed rules are testable on text. Returns
    ``{'error': ...}`` for anything it cannot account for; the traversal turns
    that into an unresolved closure, never into an absent edge.
    """
    out: Dict[str, Any] = {'load_references': [], 'rpaths': [], 'commands': [],
                           'install_name': None}
    blocks = re.split(r'^Load command \d+\s*$', text, flags=re.M)[1:]
    if ncmds is not None and len(blocks) != ncmds:
        out['error'] = ('otool listed %d load commands but the Mach header declares '
                        '%d' % (len(blocks), ncmds))
        return out
    problems = []
    for i, block in enumerate(blocks):
        m = re.search(r'^\s*cmd (\S+)\s*$', block, re.M)
        if m is None:
            problems.append('load command %d has no readable cmd' % i)
            continue
        cmd = m.group(1)
        out['commands'].append(cmd)
        if cmd in DEPENDENCY_COMMANDS or cmd == 'LC_ID_DYLIB':
            nm = re.search(r'^\s*name (.+) \(offset \d+\)\s*$', block, re.M)
            if nm is None:
                problems.append('%s (load command %d) has no readable name' % (cmd, i))
                continue
            if cmd == 'LC_ID_DYLIB':
                out['install_name'] = nm.group(1)
            else:
                out['load_references'].append({'command': cmd,
                                               'reference': nm.group(1)})
        elif cmd in CONTEXT_COMMANDS:
            pm = re.search(r'^\s*path (.+) \(offset \d+\)\s*$', block, re.M)
            if pm is None:
                problems.append('%s (load command %d) has no readable path' % (cmd, i))
                continue
            out['rpaths'].append(pm.group(1))
        elif cmd not in NON_DEPENDENCY_COMMANDS:
            problems.append('unsupported load command %s (load command %d): its '
                            'effect on what loads is not modelled' % (cmd, i))
    if problems:
        out['error'] = '; '.join(problems)
    return out


def macho_dependency_metadata(path: Path) -> Dict[str, Any]:
    """Load references and rpaths of a Mach-O file, via `otool -h` and `-l`.

    Reads METADATA of the candidate; it does not execute it. Raises nothing.
    """
    out: Dict[str, Any] = {'path': str(path)}
    try:
        h = subprocess.run(['otool', '-h', str(path)], capture_output=True,
                           text=True, timeout=60)
        lc = subprocess.run(['otool', '-l', str(path)], capture_output=True,
                            text=True, timeout=60)
    except Exception as exc:                                   # noqa: BLE001
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
        return out
    if h.returncode != 0 or lc.returncode != 0:
        out['error'] = 'otool failed: %s' % (h.stderr + lc.stderr).strip()[:200]
        return out
    header = parse_mach_header(h.stdout)
    if header.get('error'):
        out['error'] = header['error']
        return out
    out.update(parse_load_commands(lc.stdout, ncmds=header['ncmds']))
    out['path'] = str(path)
    return out


def imports_dynamic_loader(path: Path) -> Dict[str, Any]:
    """Does this member import `dlopen`? Metadata only; nothing is executed.

    Root, 2026-09-23 14:03: "account for dynamically discovered backend/plugin
    paths under the selected configuration. If that selection cannot be bounded,
    mark the closure unresolved and refuse."
    """
    out: Dict[str, Any] = {'path': str(path)}
    try:
        proc = subprocess.run(['nm', '-u', str(path)], capture_output=True,
                              text=True, timeout=60)
        if proc.returncode != 0:
            out['error'] = 'nm -u failed: %s' % proc.stderr.strip()[:200]
            return out
        out['dlopen'] = bool(re.search(r'^_dlopen$', proc.stdout, re.M))
    except Exception as exc:                                   # noqa: BLE001
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
    return out


def discovery_candidates(directory: str) -> Dict[str, Any]:
    """Everything the pinned loader could open in ONE search location.

    Symlinks are included, because `is_regular_file` follows them. A location
    that does not exist is recorded as not existing -- the loader skips it --
    and is re-enumerated at preflight, since it could be created in between.
    """
    d = Path(directory)
    row: Dict[str, Any] = {'directory': directory, 'exists': d.is_dir(),
                           'candidates': []}
    if not row['exists']:
        return row
    try:
        entries = sorted(d.iterdir())
    except OSError as exc:
        row['error'] = '%s: %s' % (type(exc).__name__, exc)
        return row
    for p in entries:
        if p.name.startswith(DISCOVERY_PREFIX) and p.name.endswith(DISCOVERY_SUFFIX):
            c: Dict[str, Any] = {'name': p.name, 'path': str(p),
                                 'is_symlink': p.is_symlink()}
            try:
                c['resolved'] = str(p.resolve(strict=True))
            except OSError as exc:
                c['error'] = '%s: %s' % (type(exc).__name__, exc)
            row['candidates'].append(c)
    return row


# -- resolution ---------------------------------------------------------------
def resolve_reference(ref: str, *, rpaths: List[str], loader_dir: str,
                      executable_dir: str, exists: Callable[[str], bool]
                      ) -> Dict[str, Any]:
    """Where a load reference actually resolves, or why it cannot be placed.

    The loader's rules: ``@rpath`` is tried against each of the LOADING image's
    rpaths in order and the first hit wins; ``@loader_path`` and
    ``@executable_path`` are substituted. A miss on the image's own rpaths
    refuses rather than walking the run-path stack of the images that loaded
    it: that case lies outside the supported profile (see the module notes),
    and the tested inherited-only miss refuses. This is a scope, not a proof
    that the resolver never passes what dyld would load differently. A
    reference or rpath that is RELATIVE, or a bare leaf name, is resolved by
    dyld against the working directory or fallback paths -- the same context
    does not select one file -- so it refuses.
    """
    if is_system_reference(ref):
        return {'reference': ref, 'system': True, 'resolved': ref}

    def _unplaceable(why, searched=()):
        return {'reference': ref, 'system': False, 'resolved': None,
                'searched': list(searched), 'problem': why}

    candidates: List[str] = []
    if ref.startswith(_AT_RPATH):
        tail = ref[len(_AT_RPATH):]
        for rp in rpaths:
            base = (rp.replace('@loader_path', loader_dir)
                      .replace('@executable_path', executable_dir))
            if not base.startswith('/'):
                return _unplaceable('the rpath %r is relative, so %r resolves '
                                    'against the working directory' % (rp, ref))
            candidates.append(str(Path(base) / tail))
    elif ref.startswith(_AT_LOADER):
        candidates.append(str(Path(loader_dir) / ref[len(_AT_LOADER):]))
    elif ref.startswith(_AT_EXEC):
        candidates.append(str(Path(executable_dir) / ref[len(_AT_EXEC):]))
    elif ref.startswith('/'):
        candidates.append(ref)
    else:
        return _unplaceable('the load reference %r is relative or a bare leaf name, '
                            'which dyld resolves against the working directory or '
                            'fallback paths; one context does not select one file'
                            % ref)
    hits = [c for c in candidates if exists(c)]
    if not hits:
        return _unplaceable('the load reference %r could not be placed under the '
                            'declared search environment' % ref, candidates)
    return {'reference': ref, 'system': False, 'resolved': hits[0],
            'searched': candidates,
            # Recorded, not refused: a later hit is shadowed and never loads. If
            # the first one goes away, the selection moves, and verification
            # sees a different resolved path.
            'shadowed': hits[1:]}


def _digest(path: str, read_bytes: Callable[[str], bytes]) -> Dict[str, Any]:
    try:
        blob = read_bytes(path)
    except Exception as exc:                                   # noqa: BLE001
        return {'unreadable': '%s: %s' % (type(exc).__name__, exc)}
    return {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def edge_key(parent: str, command: str, reference: str) -> str:
    return '%s -[%s]-> %s' % (parent, command, reference)


def _normalize_context(ctx: Any) -> Dict[str, Any]:
    if not isinstance(ctx, dict):
        return {'error': 'no launch context was supplied'}
    missing = [f for f in LAUNCH_CONTEXT_FIELDS if f not in ctx]
    if missing:
        return {'error': 'the launch context lacks %s' % ', '.join(missing)}
    env = ctx['environment']
    if not isinstance(env, dict):
        return {'error': 'the launch context environment is not a mapping'}
    return {'executable_invoked_path': ctx['executable_invoked_path'],
            'cwd': ctx['cwd'],
            'compiled_backend_dir': ctx['compiled_backend_dir'],
            'environment': {k: env[k] for k in sorted(env)
                            if k.startswith(('GGML_', LOADER_ENV_PREFIX))},
            'provenance': ctx.get('provenance')}


# -- stage one: derive ---------------------------------------------------------
def derive_closure(root_path: str, *, metadata: Callable[[str], Dict[str, Any]],
                   exists: Callable[[str], bool],
                   read_bytes: Callable[[str], bytes],
                   dynamic_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
                   enumerate_dir: Optional[Callable[[str], Dict[str, Any]]] = None,
                   launch_context: Optional[Dict[str, Any]] = None,
                   realpath: Callable[[str], str] = os.path.realpath,
                   max_members: int = 512) -> Dict[str, Any]:
    """STAGE ONE. Walk the selected launcher's dependency graph, transitively,
    under a measured launch context, and bound what the dynamic loader could
    add to it.

    Every reader is REQUIRED. A reader left out is a check not made, and a
    check not made cannot contribute to `resolved: True`.
    """
    unresolved: List[Dict[str, Any]] = []
    # Problems with the DYNAMIC half are kept apart as well, so `bounded` is
    # computed from them directly rather than read back out of message text.
    dyn_problems: List[Dict[str, Any]] = []
    ctx = _normalize_context(launch_context)
    if ctx.get('error'):
        dyn_problems.append({'problem': ctx['error']})
    for name, reader in (('dynamic-loading reader', dynamic_loader),
                         ('search-location reader', enumerate_dir)):
        if reader is None:
            dyn_problems.append({'problem': 'no %s was supplied, so that check was '
                                            'not made' % name})

    exe_dir = str(Path(root_path).parent)
    if not ctx.get('error'):
        # One canonical executable path. The loader's executable-directory
        # search uses the INVOKED path (`_NSGetExecutablePath`); if it is not
        # canonical, that directory and `@executable_path` can disagree.
        if ctx['executable_invoked_path'] != root_path:
            dyn_problems.append({'problem': 'the launch context invokes %s, not the '
                                            'closure root %s'
                                            % (ctx['executable_invoked_path'],
                                               root_path)})
        if realpath(root_path) != root_path:
            dyn_problems.append({'problem': 'the executable path %s is not canonical '
                                            '(it resolves to %s)'
                                            % (root_path, realpath(root_path))})
        if not str(ctx['cwd']).startswith('/'):
            dyn_problems.append({'problem': 'the child working directory %r is not '
                                            'an absolute path' % (ctx['cwd'],)})
        loader_env = [k for k in ctx['environment'] if k.startswith(LOADER_ENV_PREFIX)]
        if loader_env:
            dyn_problems.append({'problem': 'the child environment sets loader '
                                            'variables %s, which change where every '
                                            'edge resolves' % ', '.join(loader_env)})
        if BACKEND_PATH_ENV in ctx['environment']:
            dyn_problems.append({'problem': 'the child environment sets %s; root '
                                            'chose it explicitly unset'
                                            % BACKEND_PATH_ENV})

    edges: Dict[str, Dict[str, Any]] = {}
    files: Dict[str, Dict[str, Any]] = {}
    install_names: Dict[str, Optional[str]] = {}
    system_refs: List[str] = []
    seen: set = set()
    queue: List[str] = [root_path]
    truncated = False

    def _add_file(path: str, via: Optional[str]) -> bool:
        if path not in files:
            d = _digest(path, read_bytes)
            if d.get('unreadable'):
                unresolved.append({'file': path, 'problem': 'resolved but unreadable: '
                                                            '%s' % d['unreadable']})
                return False
            files[path] = dict(d, reached_by=[])
        if via:
            files[path]['reached_by'].append(via)
        return True

    def _canonical(spelling: str) -> Dict[str, Any]:
        """The canonical target a selected spelling will map, or why the
        alias is outside the supported profile."""
        try:
            target = realpath(spelling)
        except Exception as exc:                               # noqa: BLE001
            return {'problem': 'the canonical target of %s could not be read: %s'
                               % (spelling, exc)}
        # LEXICAL '..' IS NOT AN ALIAS. `@loader_path/../lib` spells
        # /cand/bin/../lib/x, whose directory is /cand/lib; only a SYMLINK can
        # make the loaded file live somewhere the spelling does not name. The
        # spelling is normalized first, so an ordinary relative rpath is not
        # refused as a different-directory alias (review finding, 18:50).
        if str(Path(target).parent) != str(Path(os.path.normpath(spelling)).parent):
            return {'canonical': target,
                    'problem': ('the selected path %s is an alias of %s in a '
                                'different directory; the loader-relative context '
                                'of the spelling and of the target differ, so this '
                                'alias is outside the supported profile'
                                % (spelling, target))}
        return {'canonical': target}

    _add_file(root_path, None)

    # THE DYNAMIC SEARCH, ENUMERATED BEFORE THE WALK. Root: a "complete finite
    # set of possible non-system loads under the frozen configuration ... must
    # cover every permitted choice", "including scoring candidates and the
    # ordinary recursively resolved implementation-library dependencies." So a
    # discoverable backend is not refused for existing: it becomes an edge, and
    # it is QUEUED, so its own dependencies are walked and bound like any other
    # member's. The locations are the pinned source's, in its order.
    dynamic: Dict[str, Any] = {'checked': dynamic_loader is not None,
                               'members_importing_dlopen': [],
                               'search_locations': [], 'discovered': []}
    if enumerate_dir is not None and not ctx.get('error'):
        locations = ([ctx['compiled_backend_dir']] if ctx['compiled_backend_dir']
                     else []) + [exe_dir, ctx['cwd']]
        for loc in dict.fromkeys(locations):
            row = enumerate_dir(loc)
            dynamic['search_locations'].append(row)
            if row.get('error'):
                dyn_problems.append({'problem': 'the search location %s could not '
                                                'be enumerated: %s'
                                                % (loc, row['error'])})
                continue
            for c in row.get('candidates') or []:
                if c.get('error') or not c.get('resolved'):
                    dyn_problems.append({'problem': 'discoverable candidate %s cannot '
                                                    'be pinned: %s'
                                                    % (c.get('path'), c.get('error'))})
                    continue
                spelling = c.get('path') or str(Path(loc) / c['name'])
                canon = _canonical(spelling)
                if canon.get('problem'):
                    dyn_problems.append({'problem': 'discoverable candidate: %s'
                                                    % canon['problem']})
                    continue
                key = edge_key('search:' + loc, 'ggml_backend_load_best', c['name'])
                edges[key] = {'parent': 'search:' + loc,
                              'command': 'ggml_backend_load_best',
                              'reference': c['name'], 'resolved': spelling,
                              'canonical': canon['canonical'],
                              'searched': [loc], 'shadowed': []}
                dynamic['discovered'].append(canon['canonical'])
                if _add_file(canon['canonical'], key):
                    queue.append(canon['canonical'])

    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        meta = metadata(current)
        if meta.get('error'):
            unresolved.append({'file': current, 'problem': meta['error']})
            continue
        install_names[current] = meta.get('install_name')
        loader_dir = str(Path(current).parent)
        for rec in meta.get('load_references') or []:
            ref, command = rec['reference'], rec['command']
            if is_system_reference(ref):
                if ref not in system_refs:
                    system_refs.append(ref)
                continue
            r = resolve_reference(ref, rpaths=meta.get('rpaths') or [],
                                  loader_dir=loader_dir, executable_dir=exe_dir,
                                  exists=exists)
            key = edge_key(current, command, ref)
            if not r.get('resolved'):
                unresolved.append({'file': current, 'command': command,
                                   'reference': ref, 'problem': r['problem'],
                                   'searched': r.get('searched')})
                continue
            # KEYED BY EDGE: parent, command and reference. A hash-correct file
            # at the wrong path cannot satisfy it, because what loads is chosen
            # by path; and two parents naming the same text are two edges.
            # AND BOUND BY ITS CANONICAL TARGET. Root, 16:30: a dependency
            # symlink retargeted to a different file with identical bytes still
            # verified, because only the spelling was kept. The spelling stays
            # as context; the file that will be mapped is the canonical target.
            canon = _canonical(r['resolved'])
            if canon.get('problem'):
                unresolved.append({'file': current, 'command': command,
                                   'reference': ref, 'problem': canon['problem']})
                continue
            edges[key] = {'parent': current, 'command': command, 'reference': ref,
                          'resolved': r['resolved'], 'canonical': canon['canonical'],
                          'searched': r['searched'], 'shadowed': r['shadowed']}
            if not _add_file(canon['canonical'], key):
                continue
            if len(files) > max_members:
                truncated = True
                queue = []
                break
            queue.append(canon['canonical'])
    if truncated:
        unresolved.append({'problem': 'the closure exceeded %d members and was '
                                      'not bounded' % max_members})

    # Every file that will be mapped, including discovered backends, is asked
    # whether it can `dlopen`. The answer is recorded; what it could open is
    # already bounded above, because the loader's only search is enumerated.
    if dynamic_loader is not None:
        for target in list(files):
            info = dynamic_loader(target)
            if info.get('error') or 'dlopen' not in info:
                dyn_problems.append({'file': target,
                                     'problem': 'could not determine dynamic loading: '
                                                '%s' % info.get('error', 'no answer')})
            elif info['dlopen']:
                dynamic['members_importing_dlopen'].append(target)
                if install_names.get(target) not in MODELLED_DLOPEN_INSTALL_NAMES:
                    dyn_problems.append({
                        'file': target,
                        'problem': ('%s imports dlopen and its search is not '
                                    'modelled (install name %r); only %s is'
                                    % (Path(target).name, install_names.get(target),
                                       ', '.join(MODELLED_DLOPEN_INSTALL_NAMES)))})
    dynamic['problems'] = [d['problem'] for d in dyn_problems]
    dynamic['bounded'] = not dyn_problems
    unresolved.extend(dyn_problems)

    # ONE CANONICAL FILE PER INSTALL NAME. Root, 16:30: "root chooses refusal
    # for distinct canonical files sharing an install name" until the loader's
    # selection among them is specified. `install_names` is keyed by canonical
    # path, so a same-directory alias and its target are one file, not two.
    ids: Dict[str, List[str]] = {}
    for f, n in install_names.items():
        if n:
            ids.setdefault(n, []).append(f)
    duplicates = {n: sorted(fs) for n, fs in ids.items() if len(fs) > 1}
    for n, fs in sorted(duplicates.items()):
        unresolved.append({'problem': ('%d distinct canonical files answer to the '
                                       'install name %s (%s); which one the loader '
                                       'reuses for each edge is outside the '
                                       'supported profile'
                                       % (len(fs), n, ', '.join(fs)))})
    return {
        'schema': SCHEMA,
        'root': root_path,
        'executable_dir': exe_dir,
        'launch_context': None if ctx.get('error') else ctx,
        'edges': edges,
        'files': files,
        'member_count': len(files) - 1,
        'install_names': install_names,
        'duplicate_install_names': duplicates,
        'system_references': sorted(system_refs),
        'dynamic_loading': dynamic,
        'unresolved': unresolved,
        'resolved': not unresolved,
        'note': ('transitive over non-system members. System references are '
                 'recorded by name and never pinned or traversed, per root '
                 '2026-09-23 12:42.'),
    }


# -- stage two: verify ---------------------------------------------------------
def verify_closure(frozen: Dict[str, Any], *,
                   metadata: Callable[[str], Dict[str, Any]],
                   exists: Callable[[str], bool],
                   read_bytes: Callable[[str], bytes],
                   dynamic_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
                   enumerate_dir: Optional[Callable[[str], Dict[str, Any]]] = None,
                   launch_context: Optional[Dict[str, Any]] = None,
                   realpath: Callable[[str], str] = os.path.realpath
                   ) -> Dict[str, Any]:
    """STAGE TWO. Re-derive now, under the context the launch will actually
    use, and compare with the frozen closure.

    Root: "at preflight, independently resolve the actual selected load
    references under that frozen environment and compare the required
    membership, canonical resolved paths and measured bytes to the reviewed
    manifest. Missing required members, unexpected non-system resolution,
    changed paths or source/patch/build mismatches refuse BEFORE Popen."
    """
    problems: List[str] = []
    if not isinstance(frozen, dict) or frozen.get('schema') != SCHEMA:
        return {'verified': False, 'problems': ['no frozen %s closure was supplied '
                                                'to verify against' % SCHEMA]}
    if not frozen.get('resolved'):
        problems.append('the frozen closure was itself unresolved and cannot be '
                        'used as a requirement')
    now_ctx = _normalize_context(launch_context)
    want_ctx = frozen.get('launch_context') or {}
    if now_ctx.get('error'):
        problems.append('preflight: %s' % now_ctx['error'])
    else:
        for f in LAUNCH_CONTEXT_FIELDS:
            if now_ctx.get(f) != want_ctx.get(f):
                problems.append('the launch context field %s is %r now but was '
                                'frozen as %r' % (f, now_ctx.get(f), want_ctx.get(f)))
    now = derive_closure(frozen['root'], metadata=metadata, exists=exists,
                         read_bytes=read_bytes, dynamic_loader=dynamic_loader,
                         enumerate_dir=enumerate_dir, launch_context=launch_context,
                         realpath=realpath)
    if not now['resolved']:
        problems.append('the closure cannot be resolved now: %s'
                        % '; '.join(u['problem'] for u in now['unresolved'][:4]))
    rows = []
    want_e, got_e = frozen.get('edges') or {}, now['edges']
    for key in sorted(set(want_e) | set(got_e)):
        w, g = want_e.get(key), got_e.get(key)
        row: Dict[str, Any] = {'edge': key}
        if w and not g:
            row['problem'] = ('required edge %r is no longer reached by the '
                              'dependency graph' % key)
        elif g and not w:
            row['problem'] = ('%r is loaded now but is not in the frozen closure: '
                              'an unexpected non-system resolution' % key)
        elif w['resolved'] != g['resolved']:
            row['problem'] = ('%r resolves to %s but was frozen at %s'
                              % (key, g['resolved'], w['resolved']))
        elif w.get('canonical') != g.get('canonical'):
            row['problem'] = ('%r still resolves to %s, but its canonical target is '
                              '%s now and was frozen as %s'
                              % (key, g['resolved'], g.get('canonical'),
                                 w.get('canonical')))
        else:
            row['agrees'] = True
        rows.append(row)
    want_f, got_f = frozen.get('files') or {}, now['files']
    for path in sorted(set(want_f) & set(got_f)):
        if want_f[path].get('sha256') != got_f[path].get('sha256'):
            rows.append({'file': path,
                         'problem': '%s changed bytes at the same path' % path})
    for path in sorted(set(want_f) ^ set(got_f)):
        rows.append({'file': path,
                     'problem': ('required file %s is no longer reached' % path
                                 if path in want_f else
                                 '%s is loaded now but is not in the frozen closure'
                                 % path)})
    problems.extend(r['problem'] for r in rows if r.get('problem'))
    return {
        'verified': not problems,
        'problems': problems,
        'edges_checked': len(want_e.keys() | got_e.keys()),
        'edges_agreeing': sum(1 for r in rows if r.get('agrees')),
        'files_checked': len(want_f.keys() | got_f.keys()),
        'dynamic_loading_now': now['dynamic_loading'],
        'rows': rows,
        'note': ('an edge is (parent, command, reference), bound by its spelling '
                 'AND its canonical target; files are keyed by canonical path. A '
                 'hash-correct file at another path or behind a retargeted alias '
                 'cannot satisfy it.'),
    }


# =========================================================================== #
# END OF THE TRANSCRIPTION.  Everything below is this module's own.
# =========================================================================== #
def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 \
        and all(c in '0123456789abcdef' for c in value)


def _tok(path: object) -> str:
    """The ONE tokenization rule (``lab_common.tokenize_path``, protocol 15.2): the manifest
    is a tracked file and carries no host path.  Raises ``UntokenizablePath``."""
    return lab_common.tokenize_path(str(path))


def resolve_token(token: object) -> str:
    """The inverse of :func:`_tok` for the five roots of ``lab_common.tokenize_path``
    (``lab_worker.resolve_token_path`` without the host-work pin, which no build file uses;
    the orchestrator's matrix row may not import ``lab_worker``).  Each root is taken in its
    CANONICAL form (``os.path.realpath``): ``tokenize_path`` maps both the nominal and the
    canonical spelling of a root to one token, and every path the closure compares is
    canonical, so the canonical spelling is the one that round-trips (a nominal
    ``/var/folders/...`` temporary root would otherwise name ``/private/var/...`` files by
    another spelling and fail the comparison).  A string that is not a token raises
    ``UntokenizablePath``: the manifest never names an absolute path."""
    s = str(token)
    roots = (('<WORK>', lab_common.WORK_ROOT), ('<RESULTS>', lab_common.RESULTS_ROOT),
             ('<REPO>', lab_common.REPO_ROOT), ('<HOME>', Path.home()),
             ('<TMP>', Path(tempfile.gettempdir())))
    for tok, root in roots:
        base = os.path.realpath(str(root))
        if s == tok:
            return base
        if s.startswith(tok + '/'):
            return str(Path(base) / s[len(tok) + 1:])
    raise lab_common.UntokenizablePath(s)


def _read_bytes(path: str) -> bytes:
    return Path(str(path)).read_bytes()


def host_readers() -> Dict[str, Callable]:
    """The readers of the transcribed closure on THIS host: ``otool``/``nm`` metadata, the
    filesystem, and the canonical path.  Nothing is executed; metadata is read."""
    return {'metadata': macho_dependency_metadata, 'exists': os.path.exists,
            'read_bytes': _read_bytes, 'dynamic_loader': imports_dynamic_loader,
            'enumerate_dir': discovery_candidates, 'realpath': os.path.realpath}


# --------------------------------------------------------------------------- #
# the artifact: one fixed path, canonical bytes, the config digest
# --------------------------------------------------------------------------- #
def artifact_path(freeze_dir: str | Path) -> Path:
    """[pure] THE artifact of a freeze tree: ``<freeze_dir>/serving_manifest.json``."""
    return Path(str(freeze_dir)) / ARTIFACT_NAME


def artifact_path_problems(path: str | Path) -> List[str]:
    """[pure] ``['artifact_path']`` unless ``path`` is an ABSOLUTE ``.../freeze/
    serving_manifest.json`` -- the only form :func:`artifact_path` produces.  Any other name
    or directory is a substituted path and is refused, whatever its content."""
    p = Path(str(path))
    if not p.is_absolute() or p.name != ARTIFACT_NAME or p.parent.name != FREEZE_DIR_NAME:
        return ['artifact_path']
    return []


def read_artifact(path: str | Path) -> tuple[dict | None, str | None, List[str]]:
    """``(object, canonical digest, problems)`` of the artifact at ``path``.

    Performs: the fixed-path check (:func:`artifact_path_problems`); ``lstat`` -- the file
    must exist (``artifact_missing``) and be a REGULAR file, never a symlink to content kept
    elsewhere (``artifact_not_regular_file``); a UTF-8 JSON object (``artifact_unreadable``,
    ``artifact_not_object``); and its bytes must be exactly ``canonical_json(object) + '\\n'``,
    the form :func:`write_artifact` writes (``artifact_not_canonical``).  The digest is
    ``sha256_canonical(object)``, the one digest convention of the freeze bundle.  Compares
    nothing with the configuration: that is :func:`digest_problems`."""
    problems = artifact_path_problems(path)
    if problems:
        return None, None, problems
    p = Path(str(path))
    try:
        st = os.lstat(str(p))
    except FileNotFoundError:
        return None, None, ['artifact_missing']
    except OSError:
        return None, None, ['artifact_unreadable']
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        return None, None, ['artifact_not_regular_file']
    try:
        raw = p.read_bytes()
        obj = json.loads(raw.decode('utf-8'))
    except (OSError, UnicodeDecodeError, ValueError):
        return None, None, ['artifact_unreadable']
    if not isinstance(obj, dict):
        return None, None, ['artifact_not_object']
    try:
        canon = lab_common.canonical_json(obj)
    except (TypeError, ValueError):
        return None, None, ['artifact_not_canonical']
    if raw != (canon + '\n').encode('utf-8'):
        return None, None, ['artifact_not_canonical']
    return obj, lab_common.sha256_text(canon), []


def digest_problems(found: str | None, expected: object) -> List[str]:
    """[pure] The artifact's canonical digest (``found``, computed by :func:`read_artifact`
    from the file) against the configuration's ``llama_cpp.serving_manifest_sha256``
    (``expected``).  A null or malformed configuration digest is ``config_digest_null`` --
    never replaced by the artifact's own digest, which would compare the file with itself."""
    if not _hex64(expected):
        return ['config_digest_null']
    if found is not None and found != expected:
        return ['digest']
    return []


def verify_artifact(path: str | Path,
                    expected_sha256: object) -> tuple[dict | None, str | None, List[str]]:
    """:func:`read_artifact` and :func:`digest_problems` (both always run, so a missing file
    under a null digest reports both).  The object is returned only when neither found a
    problem; the digest (``None`` when unreadable) is returned for the drift row."""
    obj, digest, problems = read_artifact(path)
    problems = problems + digest_problems(digest, expected_sha256)
    return (None if problems else obj), digest, problems


def write_artifact(path: str | Path, manifest: Mapping) -> str:
    """Write ``manifest`` ONCE at ``path`` as its canonical JSON plus one newline and return
    its canonical digest (the value of ``llama_cpp.serving_manifest_sha256``).

    Refuses a path :func:`artifact_path_problems` rejects (``ManifestError``) and an existing
    file (``lab_common.WriteOnceViolation``: ``O_CREAT|O_EXCL``).  The file is fsynced, then
    read back through :func:`read_artifact`, whose digest must be the one returned."""
    problems = artifact_path_problems(path)
    if problems:
        raise ManifestError(problems)
    p = Path(str(path))
    data = (lab_common.canonical_json(dict(manifest)) + '\n').encode('utf-8')
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise lab_common.WriteOnceViolation(str(p)) from None
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    _obj, digest, problems = read_artifact(p)
    if problems or digest != lab_common.sha256_canonical(dict(manifest)):
        raise ManifestError(['written_artifact_does_not_read_back'] + problems)
    return str(digest)


def override_problems(cfg: Mapping, results_root: str | Path) -> List[str]:
    """[pure] Every runtime or configuration key that would put the artifact somewhere other
    than ``<results_root>/freeze/serving_manifest.json``.

    Performs: a runtime ``freeze_dir`` other than ``<results_root>/freeze``
    (``override:_runtime.freeze_dir``); any runtime key, top-level configuration key or
    ``llama_cpp`` key whose name contains ``serving_manifest``, except
    ``llama_cpp.serving_manifest_sha256`` itself (``override:<key>``).  No such key is read
    anywhere; it is refused so that none can be introduced silently."""
    out: List[str] = []
    rt = cfg.get('_runtime') if isinstance(cfg.get('_runtime'), Mapping) else {}
    fixed = Path(str(results_root)) / FREEZE_DIR_NAME
    if rt.get('freeze_dir') is not None and Path(str(rt['freeze_dir'])) != fixed:
        out.append('override:_runtime.freeze_dir')
    for key in rt:
        if 'serving_manifest' in str(key):
            out.append('override:_runtime.%s' % key)
    for key in cfg:
        if key != '_runtime' and 'serving_manifest' in str(key):
            out.append('override:%s' % key)
    llama = cfg.get('llama_cpp') if isinstance(cfg.get('llama_cpp'), Mapping) else {}
    for key in llama:
        if 'serving_manifest' in str(key) and key != CONFIG_DIGEST_KEY:
            out.append('override:llama_cpp.%s' % key)
    return sorted(out)


# --------------------------------------------------------------------------- #
# the launch context and the closure, tokenized
# --------------------------------------------------------------------------- #
def server_cwd(launcher: str | Path) -> str:
    """[pure] The working directory ``lab_server.start`` gives the server: its launcher's
    directory.  ggml's backend registry searches the working directory (the transcribed
    closure's launch context), so the directory is part of what the manifest binds; fixing it
    to the launcher's makes that search location the executable directory the closure already
    enumerates, whatever directory the orchestrator was started from."""
    return str(Path(str(launcher)).parent)


def launch_context(launcher: str | Path, *, compiled_backend_dir: str | None = None,
                   environ: Mapping[str, str] | None = None) -> Dict[str, Any]:
    """The launch context the server WILL get: the invoked launcher path (as given, never
    resolved), :func:`server_cwd`, the build's compiled backend directory, and the
    ``GGML_*``/``DYLD_*`` variables of ``environ`` (the orchestrator's environment, which the
    child inherits: ``lab_server.start`` passes no ``env``)."""
    env = os.environ if environ is None else environ
    return {'executable_invoked_path': str(launcher), 'cwd': server_cwd(launcher),
            'compiled_backend_dir': compiled_backend_dir,
            'environment': {str(k): str(env[k]) for k in sorted(env)
                            if str(k).startswith(('GGML_', LOADER_ENV_PREFIX))}}


def _tok_ref(ref: str) -> str:
    return _tok(ref) if str(ref).startswith('/') else str(ref)


def _res_ref(ref: str) -> str:
    return resolve_token(ref) if str(ref).startswith('<') else str(ref)


def _tok_parent(parent: str) -> str:
    if parent.startswith('search:'):
        return 'search:' + _tok(parent[len('search:'):])
    return _tok(parent)


def _res_parent(parent: str) -> str:
    if parent.startswith('search:'):
        return 'search:' + resolve_token(parent[len('search:'):])
    return resolve_token(parent)


def tokenize_closure(closure: Mapping) -> Dict[str, Any]:
    """[pure] The frozen form of a RESOLVED closure of :func:`derive_closure`: every path
    tokenized, edges and files as sorted lists.  Kept: what :func:`verify_closure` compares
    (launch context, each edge's spelling and canonical target, each file's bytes and digest)
    and, recorded only, the system references and the dynamic-loading summary.  Raises
    ``UntokenizablePath`` for a member outside the token roots."""
    ctx = closure['launch_context']
    edges = [{'parent': _tok_parent(e['parent']), 'command': e['command'],
              'reference': _tok_ref(e['reference']), 'resolved': _tok(e['resolved']),
              'canonical': _tok(e['canonical'])} for e in closure['edges'].values()]
    edges.sort(key=lambda e: (e['parent'], e['command'], e['reference']))
    files = sorted(({'path': _tok(p), 'bytes': int(f['bytes']), 'sha256': str(f['sha256'])}
                    for p, f in closure['files'].items()), key=lambda f: f['path'])
    dyn = closure.get('dynamic_loading') or {}
    return {
        'schema': closure['schema'], 'resolved': bool(closure['resolved']),
        'root': _tok(closure['root']),
        'launch_context': {
            'executable_invoked_path': _tok(ctx['executable_invoked_path']),
            'cwd': _tok(ctx['cwd']),
            'compiled_backend_dir': (None if not ctx['compiled_backend_dir']
                                     else _tok(ctx['compiled_backend_dir'])),
            'environment': dict(ctx['environment'])},
        'edges': edges, 'files': files,
        'system_references': sorted(closure.get('system_references') or []),
        'discovered': sorted(_tok(p) for p in dyn.get('discovered') or []),
        'members_importing_dlopen': sorted(_tok(p)
                                           for p in dyn.get('members_importing_dlopen') or []),
    }


def detokenize_closure(frozen: Mapping) -> Dict[str, Any]:
    """[pure but for the token roots] :func:`tokenize_closure` inverted into the shape
    :func:`verify_closure` reads (``schema``, ``resolved``, ``root``, ``launch_context``,
    ``edges`` keyed by :func:`edge_key`, ``files`` keyed by path).  Raises
    ``UntokenizablePath``/``KeyError``/``TypeError`` on a malformed record."""
    ctx = frozen['launch_context']
    edges: Dict[str, Dict[str, Any]] = {}
    for e in frozen['edges']:
        parent, ref = _res_parent(e['parent']), _res_ref(e['reference'])
        edges[edge_key(parent, e['command'], ref)] = {
            'parent': parent, 'command': e['command'], 'reference': ref,
            'resolved': resolve_token(e['resolved']),
            'canonical': resolve_token(e['canonical'])}
    return {
        'schema': frozen['schema'], 'resolved': frozen['resolved'],
        'root': resolve_token(frozen['root']),
        'launch_context': {
            'executable_invoked_path': resolve_token(ctx['executable_invoked_path']),
            'cwd': resolve_token(ctx['cwd']),
            'compiled_backend_dir': (None if ctx['compiled_backend_dir'] is None
                                     else resolve_token(ctx['compiled_backend_dir'])),
            'environment': dict(ctx['environment'])},
        'edges': edges,
        'files': {resolve_token(f['path']): {'bytes': f['bytes'], 'sha256': f['sha256']}
                  for f in frozen['files']},
    }


def libraries_of(frozen: Mapping) -> List[Dict[str, Any]]:
    """[pure] Protocol 2.2's ``libraries[]``: every non-system closure member but the
    launcher, as ``{name (tokenized canonical path), bytes, sha256}``."""
    return [{'name': f['path'], 'bytes': f['bytes'], 'sha256': f['sha256']}
            for f in frozen['files'] if f['path'] != frozen['root']]


def closure_labels(frozen: Mapping, result: Mapping) -> List[str]:
    """[pure] Labels for a :func:`verify_closure` result, read from its ROWS (their text is
    part of the transcription): ``library_sha256:<name>`` (changed bytes at the same path),
    ``library_missing:<name>``, ``library_added:<name>`` (a file loaded now that the frozen
    closure does not hold), ``edge_missing|edge_added|edge_moved:<reference>``,
    ``launcher_sha256``, ``launch_context``, ``closure_unresolved``; ``[]`` when verified."""
    if result.get('verified'):
        return []
    labels = ['closure']
    want_files = frozen.get('files') or {}
    want_edges = frozen.get('edges') or {}
    root = frozen.get('root')
    row_problems = set()
    for row in result.get('rows') or []:
        problem = row.get('problem')
        if not problem:
            continue
        row_problems.add(problem)
        if 'file' in row:
            path, name = row['file'], Path(str(row['file'])).name
            if path in want_files:
                changed = 'changed bytes' in problem
                if changed and path == root:
                    labels.append('launcher_sha256')
                else:
                    labels.append('library_%s:%s' % ('sha256' if changed else 'missing',
                                                     name))
            else:
                labels.append('library_added:%s' % name)
        else:
            key = str(row.get('edge', ''))
            ref = key.rsplit('-> ', 1)[-1]
            if key not in want_edges:
                labels.append('edge_added:%s' % ref)
            elif 'no longer reached' in problem:
                labels.append('edge_missing:%s' % ref)
            else:
                labels.append('edge_moved:%s' % ref)
    for problem in result.get('problems') or []:
        if problem in row_problems:
            continue
        if problem.startswith(('the launch context field', 'preflight:')):
            labels.append('launch_context')
        elif problem.startswith('the closure cannot be resolved now'):
            labels.append('closure_unresolved')
        else:
            labels.append('closure_record')
    return sorted(set(labels))


def resolved_rpath(launcher: str | Path,
                   metadata: Callable[[str], Dict[str, Any]] = macho_dependency_metadata
                   ) -> Any:
    """Protocol 2.2's ``resolved_rpath``: the launcher's ``LC_RPATH`` entries in order, with
    ``@loader_path``/``@executable_path`` substituted and tokenized; a relative entry is kept
    as written (the closure refuses it).  ``{'problem': ...}`` when unreadable."""
    meta = metadata(str(launcher))
    if meta.get('error'):
        return {'problem': 'launcher_metadata'}
    d = str(Path(str(launcher)).parent)
    out: List[str] = []
    for rp in meta.get('rpaths') or []:
        base = str(rp).replace('@loader_path', d).replace('@executable_path', d)
        if not base.startswith('/'):
            out.append(str(rp))
            continue
        try:
            out.append(_tok(os.path.normpath(base)))
        except lab_common.UntokenizablePath:
            return {'problem': 'rpath_untokenizable'}
    return out


# --------------------------------------------------------------------------- #
# the Metal library
# --------------------------------------------------------------------------- #
def parse_sections(text: str) -> List[Dict[str, Any]]:
    """[pure] Every ``Section`` block of ``otool -l``: ``{segname, sectname, size, offset}``,
    or ``{'error'}`` for a block whose fields are not all readable."""
    out: List[Dict[str, Any]] = []
    for block in re.split(r'^Section\s*$', text, flags=re.M)[1:]:
        block = re.split(r'^Load command \d+\s*$', block, flags=re.M)[0]
        fields: Dict[str, str] = {}
        for key in ('sectname', 'segname', 'size', 'offset'):
            m = re.search(r'^\s*%s (\S+)\s*$' % key, block, re.M)
            if m:
                fields[key] = m.group(1)
        try:
            out.append({'segname': fields['segname'], 'sectname': fields['sectname'],
                        'size': int(fields['size'], 0), 'offset': int(fields['offset'], 0)})
        except (KeyError, ValueError):
            out.append({'error': 'a Section block without readable fields'})
    return out


def macho_sections(path: str) -> Dict[str, Any]:
    """The section table of a Mach-O file (``otool -l``).  Reads metadata; never raises."""
    try:
        lc = subprocess.run(['otool', '-l', str(path)], capture_output=True, text=True,
                            timeout=60)
    except Exception as exc:                                   # noqa: BLE001
        return {'error': '%s: %s' % (type(exc).__name__, exc)}
    if lc.returncode != 0:
        return {'error': 'otool failed'}
    return {'sections': parse_sections(lc.stdout)}


def section_bytes(path: str, segname: str, sectname: str, *,
                  sections: Callable[[str], Dict[str, Any]] = macho_sections,
                  read_bytes: Callable[[str], bytes] = _read_bytes
                  ) -> tuple[bytes | None, str | None]:
    """``(bytes, None)`` of one named section, ``(None, None)`` when the file has no such
    section, ``(None, problem)`` when that cannot be told (an unreadable table, the section
    named twice, or a range outside the file).  The bytes are the file's own, at the
    section's file offset: what the loader maps."""
    info = sections(str(path))
    if info.get('error'):
        return None, 'section table unreadable'
    table = info.get('sections') or []
    if any('error' in s for s in table):
        return None, 'section table unreadable'
    hits = [s for s in table if s['segname'] == segname and s['sectname'] == sectname]
    if not hits:
        return None, None
    if len(hits) > 1:
        return None, 'section named twice'
    try:
        data = read_bytes(str(path))
    except Exception:                                          # noqa: BLE001
        return None, 'file unreadable'
    s = hits[0]
    if s['offset'] <= 0 or s['size'] <= 0 or s['offset'] + s['size'] > len(data):
        return None, 'section outside the file'
    return data[s['offset']:s['offset'] + s['size']], None


def metal_binding(build_config: Mapping, members: List[str], *,
                  sections: Callable[[str], Dict[str, Any]] = macho_sections,
                  read_bytes: Callable[[str], bytes] = _read_bytes
                  ) -> tuple[Dict[str, Any], List[str]]:
    """Protocol 2.2's ``metal_library``: the SHA-256 of the Metal library, which of embedded
    or external it is, and what binds it.

    Determined from the build configuration (the re-hashed ``CMakeCache.txt``) and the closure
    members' own bytes: ``GGML_METAL`` OFF is ``{'kind': 'none'}``; ``GGML_METAL_EMBED_LIBRARY``
    ON must find EXACTLY ONE member carrying ``__DATA,__ggml_metallib`` (the ``.incbin`` of the
    kernel sources) and records its container (tokenized), the container's digest -- itself a
    closure member digest -- and the section's size and digest.  Metal ON without the embedded
    library is ``metal_library_not_embedded``: the external search is not modelled and is
    refused, never assumed."""
    if build_config.get('GGML_METAL') is False:
        return {'kind': 'none', 'bound_by': 'GGML_METAL is OFF in the build CMakeCache.txt'}, []
    if build_config.get('GGML_METAL') is not True:
        return {}, ['metal_build_config']
    if build_config.get('GGML_METAL_EMBED_LIBRARY') is not True:
        return {}, ['metal_library_not_embedded']
    found: List[tuple[str, bytes]] = []
    problems: List[str] = []
    for path in sorted(members):
        data, problem = section_bytes(path, METAL_SEGMENT, METAL_SECTION,
                                      sections=sections, read_bytes=read_bytes)
        if problem:
            problems.append('metal_section_unreadable:%s' % Path(path).name)
        elif data is not None:
            found.append((path, data))
    if problems:
        return {}, problems
    if len(found) != 1:
        return {}, ['metal_library_containers:%d' % len(found)]
    path, data = found[0]
    try:
        container = _tok(path)
        container_sha = hashlib.sha256(read_bytes(path)).hexdigest()
    except (lab_common.UntokenizablePath, OSError):
        return {}, ['metal_library_container']
    return {'kind': 'embedded', 'container': container, 'container_sha256': container_sha,
            'section': '%s,%s' % (METAL_SEGMENT, METAL_SECTION), 'section_bytes': len(data),
            'section_sha256': hashlib.sha256(data).hexdigest(),
            'bound_by': ('the one closure member carrying the section: the container digest '
                         'is a closure member digest and the section digest is recomputed '
                         'from the container at every invocation, start and restart')}, []


# --------------------------------------------------------------------------- #
# build provenance
# --------------------------------------------------------------------------- #
_CMAKE_LINE = re.compile(r'^([A-Za-z_][A-Za-z0-9_.+\-]*):([A-Z_]+)=(.*)$')
_BUILD_NUMBER = re.compile(r'^int LLAMA_BUILD_NUMBER = (\d+);\s*$', re.M)
_BUILD_COMMIT = re.compile(r'^char const \* LLAMA_COMMIT = "([^"\\]*)";\s*$', re.M)


def parse_cmake_cache(text: str) -> Dict[str, str]:
    """[pure] ``NAME:TYPE=VALUE`` lines of a ``CMakeCache.txt``; comments skipped."""
    out: Dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith(('//', '#')):
            continue
        m = _CMAKE_LINE.match(line)
        if m:
            out[m.group(1)] = m.group(3)
    return out


def _cmake_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    v = value.strip().upper()
    if v in ('ON', 'TRUE', 'YES', 'Y', '1'):
        return True
    if v in ('OFF', 'FALSE', 'NO', 'N', '0', '') or v.endswith('-NOTFOUND'):
        return False
    return None


def build_config(cache: Mapping[str, str]) -> tuple[Dict[str, Any], List[str]]:
    """[pure] The build options that change what the server loads: ``GGML_METAL``,
    ``GGML_METAL_EMBED_LIBRARY`` (required when Metal is on), ``GGML_BACKEND_DL`` and the
    compiled ``GGML_BACKEND_DIR``.  A required option that is absent or not a boolean is
    ``cmake_cache:<name>``."""
    out: Dict[str, Any] = {}
    problems: List[str] = []
    for key in ('GGML_METAL', 'GGML_BACKEND_DL'):
        out[key] = _cmake_bool(cache.get(key))
        if out[key] is None:
            problems.append('cmake_cache:%s' % key)
    out['GGML_METAL_EMBED_LIBRARY'] = _cmake_bool(cache.get('GGML_METAL_EMBED_LIBRARY'))
    if out['GGML_METAL'] and out['GGML_METAL_EMBED_LIBRARY'] is None:
        problems.append('cmake_cache:GGML_METAL_EMBED_LIBRARY')
    out['GGML_BACKEND_DIR'] = cache.get('GGML_BACKEND_DIR') or None
    return out, problems


def compiled_backend_dir(config: Mapping) -> Optional[str]:
    """[pure] The backend directory compiled into ggml: only with ``GGML_BACKEND_DL``."""
    return config.get('GGML_BACKEND_DIR') if config.get('GGML_BACKEND_DL') else None


def expected_build_info(text: str) -> tuple[Optional[str], List[str]]:
    """[pure] The ``/props.build_info`` a build reports, from its generated
    ``common/build-info.cpp``: ``"b" + std::to_string(LLAMA_BUILD_NUMBER) + "-" +
    LLAMA_COMMIT`` (``common/build-info.cpp.in:28`` at the pinned commit).  Exactly one of
    each definition, else ``build_info_source``."""
    numbers = _BUILD_NUMBER.findall(text)
    commits = _BUILD_COMMIT.findall(text)
    if len(numbers) != 1 or len(commits) != 1:
        return None, ['build_info_source']
    return 'b%d-%s' % (int(numbers[0]), commits[0]), []


def read_provenance(paths: Mapping[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any],
                                                       List[str]]:
    """``(record, facts, problems)`` of the build-provenance files named by ``paths`` (role ->
    absolute path, the roles of :data:`PROVENANCE_ROLES`).

    READS AND HASHES EVERY FILE NOW.  ``record`` is the manifest's ``build`` member: the
    commit and patch digest the durable-build receipt states, every file as ``{path
    (tokenized), bytes, sha256}``, the build options of :func:`build_config`, and the
    receipt's member digests (tokenized canonical path -> sha256).  ``facts`` adds the
    protocol-2.2 literals the receipt states (``cmake_options``, ``compiler_version``,
    ``sdk_version``, ``build_log_sha256``, ``configure_log_sha256``) and the ``/props.
    build_info`` the build's ``build-info.cpp`` yields.  ``problems``: a role absent,
    unreadable or not a regular file; a receipt that is not a successful
    ``live_ab/durable_rebuild-v1`` build of one commit; a patch or log whose digest is not
    the one the receipt states; an unreadable build option or build-info source."""
    problems: List[str] = []
    files: Dict[str, Dict[str, Any]] = {}
    blobs: Dict[str, bytes] = {}
    for role in PROVENANCE_ROLES:
        raw_path = paths.get(role)
        if not raw_path:
            problems.append('provenance_missing:%s' % role)
            continue
        path = str(raw_path)
        try:
            st = os.lstat(path)
            if not stat.S_ISREG(st.st_mode):
                problems.append('provenance_not_regular_file:%s' % role)
                continue
            data = Path(path).read_bytes()
            token = _tok(path)
        except lab_common.UntokenizablePath:
            problems.append('provenance_untokenizable:%s' % role)
            continue
        except OSError:
            problems.append('provenance_unreadable:%s' % role)
            continue
        files[role] = {'path': token, 'bytes': len(data),
                       'sha256': hashlib.sha256(data).hexdigest()}
        blobs[role] = data
    facts: Dict[str, Any] = {k: None for k in (
        'cmake_options', 'compiler_version', 'sdk_version', 'build_log_sha256',
        'configure_log_sha256', 'props_build_info')}
    record: Dict[str, Any] = {'commit': None, 'patch_sha256': None, 'files': files,
                              'config': None, 'receipt_members': None}
    # -- the durable-build receipt ------------------------------------------------
    receipt: Any = None
    if 'build_receipt' in blobs:
        try:
            receipt = json.loads(blobs['build_receipt'].decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            receipt = None
        if not isinstance(receipt, dict) or receipt.get('schema') != RECEIPT_SCHEMA:
            problems.append('receipt_schema')
            receipt = None
    if receipt is not None:
        state = receipt.get('source_state') if isinstance(receipt.get('source_state'),
                                                          Mapping) else {}
        item = receipt.get('protocol_2_2_item_1') if isinstance(
            receipt.get('protocol_2_2_item_1'), Mapping) else {}
        tool = item.get('toolchain') if isinstance(item.get('toolchain'), Mapping) else {}
        commit = state.get('head')
        if not (isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit)) \
                or state.get('pinned_commit') != commit:
            problems.append('receipt_commit')
        if receipt.get('build_succeeded') is not True or item.get('build_exit') != 0 \
                or item.get('configure_exit') != 0:
            problems.append('receipt_build_status')
        record['commit'] = commit if isinstance(commit, str) else None
        record['patch_sha256'] = state.get('patch_sha256') if _hex64(
            state.get('patch_sha256')) else None
        for role, key in (('patch', None), ('build_log', 'build_log_sha256'),
                          ('configure_log', 'configure_log_sha256')):
            stated = record['patch_sha256'] if key is None else item.get(key)
            if role in files and files[role]['sha256'] != stated:
                problems.append('%s_sha256' % role)
            if key is not None:
                facts[key] = stated if _hex64(stated) else None
        options = item.get('cmake_options')
        if isinstance(options, list) and all(isinstance(o, str) for o in options):
            facts['cmake_options'] = list(options)
        else:
            problems.append('receipt_cmake_options')
        for key, src in (('compiler_version', 'compiler'), ('sdk_version', 'sdk')):
            if isinstance(tool.get(src), str) and tool.get(src):
                facts[key] = tool[src]
            else:
                problems.append('receipt_%s' % key)
        members = receipt.get('members')
        rows: Dict[str, str] = {}
        if isinstance(members, Mapping) and members:
            for m in members.values():
                try:
                    rows[_tok(m['canonical'])] = str(m['sha256'])
                except (lab_common.UntokenizablePath, KeyError, TypeError):
                    problems.append('receipt_members')
                    break
        else:
            problems.append('receipt_members')
        record['receipt_members'] = [{'path': k, 'sha256': rows[k]} for k in sorted(rows)]
    # -- the build options and the build string ------------------------------------
    if 'cmake_cache' in blobs:
        config, p = build_config(parse_cmake_cache(
            blobs['cmake_cache'].decode('utf-8', 'replace')))
        problems.extend(p)
        record['config'] = config
    if 'build_info_source' in blobs:
        info, p = expected_build_info(blobs['build_info_source'].decode('utf-8', 'replace'))
        problems.extend(p)
        facts['props_build_info'] = info
    return record, facts, sorted(set(problems))


def _public_build(record: Mapping) -> Dict[str, Any]:
    """[pure] The manifest's ``build`` member: the record, with the compiled backend
    directory reduced to whether one is set (the directory itself is in the closure's launch
    context, tokenized)."""
    out = dict(record)
    config = dict(record.get('config') or {})
    if 'GGML_BACKEND_DIR' in config:
        config['GGML_BACKEND_DIR'] = config['GGML_BACKEND_DIR'] is not None
    out['config'] = config
    return out


# --------------------------------------------------------------------------- #
# the facts, measured now and recorded in the manifest
# --------------------------------------------------------------------------- #
def _launcher_fact(launcher: str, read_bytes: Callable[[str], bytes]) -> Dict[str, Any]:
    try:
        token: Optional[str] = _tok(launcher)
    except lab_common.UntokenizablePath:
        token = None
    try:
        data = read_bytes(launcher)
    except Exception:                                          # noqa: BLE001
        return {'path': token, 'bytes': None, 'sha256': None}
    return {'path': token, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def runtime_facts(manifest: Mapping, *, launcher: str | Path,
                  environ: Mapping[str, str] | None = None,
                  readers: Mapping[str, Callable] | None = None) -> Dict[str, Any]:
    """MEASURE, now, every fact :func:`recorded_facts` reads from the manifest.

    From the manifest only two things are taken: WHICH provenance files to re-read (their
    tokenized paths) and the frozen closure :func:`verify_closure` compares with -- whose
    verification re-derives every edge from the Mach-O load commands under the launch context
    the server will get (:func:`launch_context` of ``launcher`` and ``environ``) and re-hashes
    every member.  Everything else is measured: the launcher's tokenized path and digest, the
    provenance of :func:`read_provenance` (and its problems), the launcher's ``LC_RPATH``, the
    Metal binding of :func:`metal_binding` over the frozen members' CURRENT bytes (the closure
    verification has compared the member set itself), and the build string of the build's own
    ``build-info.cpp``."""
    readers = dict(host_readers() if readers is None else readers)
    launcher = str(launcher)
    facts: Dict[str, Any] = {'launcher': _launcher_fact(launcher, readers['read_bytes'])}
    paths: Dict[str, Optional[str]] = {}
    build = manifest.get('build') if isinstance(manifest.get('build'), Mapping) else {}
    for role, rec in dict(build.get('files') or {}).items():
        try:
            paths[str(role)] = resolve_token(rec['path'])
        except (lab_common.UntokenizablePath, KeyError, TypeError):
            paths[str(role)] = None
    record, pfacts, pproblems = read_provenance(paths)
    facts['build'] = _public_build(record)
    facts['provenance_problems'] = pproblems
    for key in ('cmake_options', 'compiler_version', 'sdk_version', 'build_log_sha256',
                'configure_log_sha256', 'props_build_info'):
        facts[key] = pfacts.get(key)
    config = dict(record.get('config') or {})
    ctx = launch_context(launcher, compiled_backend_dir=compiled_backend_dir(config),
                         environ=environ)
    try:
        frozen = detokenize_closure(manifest['closure'])
    except (lab_common.UntokenizablePath, KeyError, TypeError, AttributeError):
        frozen = None
    if frozen is None:
        facts['closure'] = {'verified': False, 'labels': ['closure_record']}
        members: List[str] = []
    else:
        result = verify_closure(frozen, launch_context=ctx, **{
            k: readers[k] for k in ('metadata', 'exists', 'read_bytes', 'dynamic_loader',
                                    'enumerate_dir', 'realpath')})
        facts['closure'] = {'verified': bool(result['verified']),
                            'labels': closure_labels(frozen, result)}
        members = sorted(frozen['files'])
    facts['resolved_rpath'] = resolved_rpath(launcher, readers['metadata'])
    metal, problems = metal_binding(config, members,
                                    sections=readers.get('sections', macho_sections),
                                    read_bytes=readers['read_bytes'])
    facts['metal_library'] = metal if not problems else {'problems': problems}
    return facts


def recorded_facts(manifest: Mapping) -> Dict[str, Any]:
    """[pure] The facts the manifest RECORDS, in the shape :func:`runtime_facts` measures
    them: the closure as verified with no label, the provenance with no problem."""
    return {'launcher': manifest.get('launcher'),
            'closure': {'verified': True, 'labels': []},
            'resolved_rpath': manifest.get('resolved_rpath'),
            'metal_library': manifest.get('metal_library'),
            'build': manifest.get('build'),
            'provenance_problems': [],
            'cmake_options': manifest.get('cmake_options'),
            'compiler_version': manifest.get('compiler_version'),
            'sdk_version': manifest.get('sdk_version'),
            'build_log_sha256': manifest.get('build_log_sha256'),
            'configure_log_sha256': manifest.get('configure_log_sha256'),
            'props_build_info': manifest.get('props_build_info')}


def compare_facts(manifest: Mapping, measured: Mapping) -> List[str]:
    """[pure] :func:`recorded_facts` of ``manifest`` against ``measured`` (from
    :func:`runtime_facts`), key by key.  Labels: the differing key (``launcher`` split into
    ``launcher_path`` / ``launcher_sha256``), every closure label, every provenance
    problem as ``provenance:<problem>``."""
    recorded = recorded_facts(manifest)
    labels: List[str] = []
    for key in sorted(recorded):
        want, got = recorded[key], measured.get(key)
        if key == 'launcher':
            want, got = dict(want or {}), dict(got or {})
            if want.get('path') != got.get('path'):
                labels.append('launcher_path')
            if want.get('sha256') != got.get('sha256') or want.get('bytes') != got.get('bytes'):
                labels.append('launcher_sha256')
        elif key == 'closure':
            if want != got:
                labels.extend(list((got or {}).get('labels') or ['closure']))
        elif key == 'provenance_problems':
            labels.extend('provenance:%s' % p for p in (got or []))
        elif want != got:
            labels.append(key)
    return sorted(set(labels))


def structure_problems(manifest: object, llama_commit: str) -> List[str]:
    """[pure] Whether ``manifest`` is a well-formed, internally consistent manifest of
    ``llama_commit``.  Performs: the schema and exactly :data:`MANIFEST_KEYS` (a ``mock``
    manifest is ``mock_manifest``); the closure record's shape; ``launcher_sha256`` equals
    ``launcher.sha256``; the closure's root and its file are the launcher; ``libraries`` is
    :func:`libraries_of` the closure; the receipt's members are the closure's files (path and
    digest); the commit is ``llama_commit`` in ``llama_cpp_commit`` and ``build.commit``, and
    its 7-character prefix is in ``props_build_info``.  Measures nothing."""
    if not isinstance(manifest, Mapping):
        return ['structure']
    if manifest.get('mock'):
        return ['mock_manifest']
    labels: List[str] = []
    if manifest.get('schema') != MANIFEST_SCHEMA:
        labels.append('schema')
    for key in MANIFEST_KEYS:
        if key not in manifest:
            labels.append('missing:%s' % key)
    for key in manifest:
        if key not in MANIFEST_KEYS:
            labels.append('unknown:%s' % key)
    if labels:
        return sorted(labels)
    closure = manifest['closure']
    launcher = manifest['launcher']
    build = manifest['build']
    try:
        if closure['schema'] != SCHEMA or closure['resolved'] is not True:
            labels.append('closure_record')
        files = {f['path']: (f['bytes'], f['sha256']) for f in closure['files']}
        if manifest['launcher_sha256'] != launcher['sha256']:
            labels.append('inconsistent:launcher_sha256')
        if closure['root'] != launcher['path'] \
                or files.get(launcher['path']) != (launcher['bytes'], launcher['sha256']):
            labels.append('inconsistent:launcher')
        if manifest['libraries'] != libraries_of(closure):
            labels.append('inconsistent:libraries')
        members = {m['path']: m['sha256'] for m in build['receipt_members']}
        if members != {p: v[1] for p, v in files.items()}:
            labels.append('inconsistent:receipt_members')
    except (KeyError, TypeError, AttributeError):
        labels.append('closure_record')
    if manifest.get('llama_cpp_commit') != llama_commit:
        labels.append('commit')
    if not isinstance(build, Mapping) or build.get('commit') != llama_commit:
        labels.append('build_commit')
    if not isinstance(manifest.get('props_build_info'), str) \
            or str(llama_commit)[:7] not in manifest['props_build_info']:
        labels.append('props_build_info_commit')
    return sorted(set(labels))


def runtime_problems(manifest: Mapping, *, launcher: str | Path, llama_commit: str,
                     environ: Mapping[str, str] | None = None,
                     readers: Mapping[str, Callable] | None = None) -> List[str]:
    """The manifest against the actual runtime: :func:`structure_problems` first (a
    malformed manifest is not measured against), an explicit absolute launcher
    (``launcher_not_explicit``), then :func:`compare_facts` of :func:`runtime_facts`.
    ``[]`` means every fact re-verified."""
    labels = structure_problems(manifest, llama_commit)
    if not os.path.isabs(str(launcher)):
        labels = sorted(set(labels + ['launcher_not_explicit']))
    if labels:
        return labels
    return compare_facts(manifest, runtime_facts(manifest, launcher=launcher,
                                                 environ=environ, readers=readers))


def verify_before_launch(path: str | Path, expected_sha256: object, *,
                         launcher: str | Path, llama_commit: str,
                         environ: Mapping[str, str] | None = None,
                         readers: Mapping[str, Callable] | None = None
                         ) -> tuple[dict | None, List[str]]:
    """The whole pre-launch re-verification of protocol 2.2 item 2 / 5.3 (P:452, P:918):
    :func:`verify_artifact` of THE artifact at ``path`` against the configuration digest,
    then :func:`runtime_problems`.  Returns ``(manifest, labels)``; the manifest is ``None``
    when the artifact itself did not verify.  Called by ``lab_orchestrator.preflight`` at
    every invocation and by ``lab_server.start`` at every start and restart."""
    manifest, _digest, labels = verify_artifact(path, expected_sha256)
    if labels:
        return None, labels
    return manifest, runtime_problems(manifest, launcher=launcher, llama_commit=llama_commit,
                                      environ=environ, readers=readers)


def props_build_info_problems(manifest: Mapping | None, props: object) -> List[str]:
    """[pure] The server's ACTUAL ``/props.build_info`` against the manifest's
    ``props_build_info``: ``['props_build_info_observed']`` unless they are equal strings."""
    want = manifest.get('props_build_info') if isinstance(manifest, Mapping) else None
    got = props.get('build_info') if isinstance(props, Mapping) else None
    if not isinstance(want, str) or got != want:
        return ['props_build_info_observed']
    return []


# --------------------------------------------------------------------------- #
# the assembler
# --------------------------------------------------------------------------- #
def assemble(launcher: str | Path, provenance: Mapping[str, Any], *, llama_commit: str,
             environ: Mapping[str, str] | None = None,
             readers: Mapping[str, Callable] | None = None) -> Dict[str, Any]:
    """[pure but for the files it reads] The manifest content of the durable build whose
    launcher is ``launcher`` and whose provenance files are ``provenance`` (role -> path).

    Refuses with :class:`ManifestError` naming every problem, never returning a partial
    manifest: a launcher path that is not absolute and canonical; a ``GGML_*``/``DYLD_*``
    variable in the assembling environment (the frozen launch environment is empty, and the
    runtime environment must equal it); any :func:`read_provenance` problem; a receipt commit
    other than ``llama_commit``; an unresolved closure (the transcribed
    :func:`derive_closure`, under :func:`launch_context`); a member outside the token roots;
    a receipt whose members are not the derived closure's files (path and digest); a Metal
    binding problem; an unreadable ``LC_RPATH``; and a result that fails its own
    :func:`structure_problems`.  The measuring functions are the ones :func:`runtime_facts`
    uses, so what is frozen and what is later observed come from one implementation."""
    readers = dict(host_readers() if readers is None else readers)
    env = os.environ if environ is None else environ
    launcher = str(launcher)
    problems: List[str] = []
    if not os.path.isabs(launcher) or readers['realpath'](launcher) != launcher:
        problems.append('launcher_not_canonical')
    loader_env = sorted(str(k) for k in env if str(k).startswith(('GGML_', LOADER_ENV_PREFIX)))
    if loader_env:
        problems.append('assembly_environment:%s' % ','.join(loader_env))
    record, pfacts, p = read_provenance(provenance)
    problems.extend(p)
    if record.get('commit') != llama_commit:
        problems.append('build_commit')
    config = dict(record.get('config') or {})
    ctx = launch_context(launcher, compiled_backend_dir=compiled_backend_dir(config),
                         environ=env)
    closure = derive_closure(launcher, launch_context=ctx, **{
        k: readers[k] for k in ('metadata', 'exists', 'read_bytes', 'dynamic_loader',
                                'enumerate_dir', 'realpath')})
    frozen: Optional[Dict[str, Any]] = None
    if not closure['resolved']:
        problems.append('closure_unresolved: %s' % ' | '.join(
            str(u.get('problem')) for u in closure['unresolved'][:6]))
    else:
        try:
            frozen = tokenize_closure(closure)
        except lab_common.UntokenizablePath as exc:
            problems.append('closure_untokenizable: %s' % exc)
    if frozen is not None:
        members = {m['path']: m['sha256'] for m in record.get('receipt_members') or []}
        if members != {f['path']: f['sha256'] for f in frozen['files']}:
            problems.append('receipt_members_closure')
    metal, p = metal_binding(config, sorted(closure['files']),
                             sections=readers.get('sections', macho_sections),
                             read_bytes=readers['read_bytes'])
    problems.extend(p)
    rpath = resolved_rpath(launcher, readers['metadata'])
    if isinstance(rpath, Mapping):
        problems.append(str(rpath.get('problem')))
    if problems or frozen is None:
        raise ManifestError(sorted(set(problems)) or ['closure_unresolved'])
    launcher_file = next(f for f in frozen['files'] if f['path'] == frozen['root'])
    manifest = {
        'schema': MANIFEST_SCHEMA,
        'llama_cpp_commit': str(llama_commit),
        'launcher_sha256': launcher_file['sha256'],
        'launcher': dict(launcher_file),
        'libraries': libraries_of(frozen),
        'closure': frozen,
        'resolved_rpath': rpath,
        'metal_library': metal,
        'build': _public_build(record),
        'cmake_options': pfacts['cmake_options'],
        'compiler_version': pfacts['compiler_version'],
        'sdk_version': pfacts['sdk_version'],
        'build_log_sha256': pfacts['build_log_sha256'],
        'configure_log_sha256': pfacts['configure_log_sha256'],
        'props_build_info': pfacts['props_build_info'],
    }
    problems = structure_problems(manifest, str(llama_commit))
    if problems:
        raise ManifestError(problems)
    return manifest
