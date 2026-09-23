"""The selected-dependency contract: derive and freeze, then verify resolution.

Root, 2026-09-23 14:03, answering the question put to it about where the
required implementation members come from:

    "Derive the required set during preparation from the selected launcher,
     backend configuration and dependency metadata; freeze that resolved set; at
     launch verify the selected files and resolution against the frozen set. The
     supervisor checks agreement and refuses differences. It must not silently
     replace the agreed set or treat any caller-provided nonempty list as
     sufficient."

WHY MY OWN DEFAULT WAS INSUFFICIENT. I proposed verifying the members a manifest
names. Root: that "is insufficient if omissions can redefine what is required" --
a manifest that simply fails to mention `libllama-server-impl.dylib` would then
have nothing to verify, and its absence would look like compliance. The required
set has to be DERIVED from the artifact, not accepted from the document, and
frozen before any outcome is known.

TWO STAGES, AND BOTH ARE NECESSARY

  1. ``derive_closure`` walks the dependency metadata of the selected launcher
     and every non-system library it reaches, transitively, under the selected
     backend configuration. What it produces is frozen into the launch manifest.
  2. ``verify_closure`` re-resolves the actual load references at preflight and
     compares membership, canonical resolved paths and measured bytes with the
     frozen set.

The first justifies the requirement; the second checks that what will load is
what was required. Neither alone is enough: stage 1 without stage 2 trusts that
the frozen set still describes the disk, and stage 2 without stage 1 trusts
whoever wrote the list.

A HASH-CORRECT UNRELATED FILE CANNOT SATISFY A REQUIRED EDGE. Root said so
explicitly. Membership is keyed by the dependency EDGE -- the load reference as
the binary states it -- and an entry must match on reference, resolved path and
bytes. A file with the right digest sitting at the wrong path is a mismatch, not
a pass, because what loads is chosen by path.

UNRESOLVABLE MEANS REFUSE. Root: "If that selection cannot be bounded, mark the
closure unresolved and refuse instead of certifying the nine-entry inventory as
complete." An edge whose metadata cannot be read, or a search environment that
cannot place it, leaves the closure `resolved: False`, and a caller must treat
that as a refusal. Silence about an edge is never evidence that it is absent.

NOTHING HERE EXECUTES THE CANDIDATE. Dependency metadata is supplied by a reader
callable, so the traversal is exercised with finite synthetic graphs in tests and
with the real Mach-O load commands in production. Root: "No candidate binary
execution, rebuild, model load or extra historical smoke is needed for this gate
work."
REPAIRED 2026-09-23, root's 14:41 ranked response to `6b83860`:

  1. "Carry the dynamic contract through verification." `verify_closure`
     re-derived WITHOUT a dynamic reader, so it could report verified=True
     having made zero dynamic checks, and `dynamic_policy={'bounded': True}` was
     only the caller's assertion. Now a MEASURED launch context -- invoked
     executable path, child cwd, compiled backend directory, the child's
     GGML_*/DYLD_* environment -- is required by derive AND verify, every search
     location the pinned loader source consults is enumerated, and a missing
     reader or context refuses. `bounded` is computed, never supplied.
  2. "Fail closed on unsupported dependency metadata." The parser read three
     command types and silently skipped the rest, so an `LC_REEXPORT_DYLIB`
     member vanished and the closure resolved with zero members. Every load
     command is now classified against a CLOSED list; an unknown command, a
     dependency record without a name, or a command count that disagrees with
     the Mach header makes the file unreadable, which is unresolved.
  3. "Represent an edge with its parent/resolution context." Two
     `@loader_path/helper` references from different directories were collapsed
     under the reference text and refused as ambiguous. An edge is now keyed by
     (parent, command, reference); resolved files are a separate table.
     Rejection is preserved where one context truly cannot select: a relative
     path, a bare leaf name or a relative rpath, each resolved by dyld against
     the working directory or fallback paths.

"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

SCHEMA = 'live_ab/dependency_closure-v2'

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
    ``@executable_path`` are substituted. Two things are deliberately
    conservative. A miss on the image's own rpaths refuses rather than walking
    the run-path stack of the images that loaded it, which dyld would also
    search: that can only refuse more, never pass more. And a reference or rpath
    that is RELATIVE, or a bare leaf name, is resolved by dyld against the
    working directory or fallback paths -- the same context does not select one
    file -- so it refuses.
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
                key = edge_key('search:' + loc, 'ggml_backend_load_best', c['name'])
                edges[key] = {'parent': 'search:' + loc,
                              'command': 'ggml_backend_load_best',
                              'reference': c['name'], 'resolved': c['resolved'],
                              'searched': [loc], 'shadowed': []}
                dynamic['discovered'].append(c['resolved'])
                if _add_file(c['resolved'], key):
                    queue.append(c['resolved'])

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
            edges[key] = {'parent': current, 'command': command, 'reference': ref,
                          'resolved': r['resolved'], 'searched': r['searched'],
                          'shadowed': r['shadowed']}
            if not _add_file(r['resolved'], key):
                continue
            if len(files) > max_members:
                truncated = True
                queue = []
                break
            queue.append(r['resolved'])
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

    ids: Dict[str, List[str]] = {}
    for f, n in install_names.items():
        if n:
            ids.setdefault(n, []).append(f)
    return {
        'schema': SCHEMA,
        'root': root_path,
        'executable_dir': exe_dir,
        'launch_context': None if ctx.get('error') else ctx,
        'edges': edges,
        'files': files,
        'member_count': len(files) - 1,
        'install_names': install_names,
        # Recorded, not refused: two different files answering to one install
        # name are both bound and both verified. Root's item 3 treats distinct
        # parent contexts as distinct edges.
        'duplicate_install_names': {n: fs for n, fs in ids.items() if len(fs) > 1},
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
        'note': ('an edge is (parent, command, reference). A hash-correct file at '
                 'another path cannot satisfy it, because what loads is chosen by '
                 'path.'),
    }
