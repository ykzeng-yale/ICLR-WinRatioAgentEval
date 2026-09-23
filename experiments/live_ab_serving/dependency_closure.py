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
"""

from __future__ import annotations

import hashlib
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

#: Prefixes whose members are OS-provided. Root, 12:42: "System library names
#: are sufficient here when linked to the already required OS build/architecture
#: /runtime provenance; separately hashing `libSystem` and `libc++` is not an
#: added requirement." They are RECORDED, never pinned, and never traversed.
SYSTEM_PREFIXES = ('/usr/lib/', '/System/')

#: Load-reference prefixes that a search environment must resolve.
_AT_RPATH = '@rpath/'
_AT_LOADER = '@loader_path/'
_AT_EXEC = '@executable_path/'


def is_system_reference(ref: str) -> bool:
    return any(ref.startswith(p) for p in SYSTEM_PREFIXES)


def macho_dependency_metadata(path: Path) -> Dict[str, Any]:
    """Load references and rpaths of a Mach-O file, via `otool`.

    Reads METADATA of the candidate; it does not execute it. Raises nothing:
    an unreadable file yields ``{'error': ...}``, which the traversal turns
    into an unresolved closure rather than an omission.
    """
    out: Dict[str, Any] = {'path': str(path), 'load_references': [], 'rpaths': []}
    try:
        lc = subprocess.run(['otool', '-l', str(path)], capture_output=True,
                            text=True, timeout=60)
        if lc.returncode != 0:
            out['error'] = 'otool -l failed: %s' % lc.stderr.strip()[:200]
            return out
        text = lc.stdout
    except Exception as exc:                                   # noqa: BLE001
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
        return out
    refs, rpaths = [], []
    for block in text.split('Load command')[1:]:
        m = re.search(r'cmd (LC_LOAD_DYLIB|LC_LOAD_WEAK_DYLIB|LC_RPATH)', block)
        if not m:
            continue
        nm = re.search(r'(?:name|path) (\S+) \(offset', block)
        if not nm:
            continue
        (rpaths if m.group(1) == 'LC_RPATH' else refs).append(nm.group(1))
    out['load_references'] = refs
    out['rpaths'] = rpaths
    return out


def resolve_reference(ref: str, *, rpaths: List[str], loader_dir: str,
                      executable_dir: str, exists: Callable[[str], bool]
                      ) -> Dict[str, Any]:
    """Where a load reference actually resolves, or why it cannot be placed.

    The resolution rules are the loader's, not a convenience: ``@rpath`` is tried
    against each declared rpath in order, and ``@loader_path``/``@executable_path``
    are substituted directly. The FIRST hit wins, because that is what loads.
    """
    if is_system_reference(ref):
        return {'reference': ref, 'system': True, 'resolved': ref}
    candidates: List[str] = []
    if ref.startswith(_AT_RPATH):
        tail = ref[len(_AT_RPATH):]
        for rp in rpaths:
            base = (rp.replace('@loader_path', loader_dir)
                      .replace('@executable_path', executable_dir))
            candidates.append(str(Path(base) / tail))
    elif ref.startswith(_AT_LOADER):
        candidates.append(str(Path(loader_dir) / ref[len(_AT_LOADER):]))
    elif ref.startswith(_AT_EXEC):
        candidates.append(str(Path(executable_dir) / ref[len(_AT_EXEC):]))
    else:
        candidates.append(ref)
    for c in candidates:
        if exists(c):
            return {'reference': ref, 'system': False, 'resolved': c,
                    'searched': candidates}
    return {'reference': ref, 'system': False, 'resolved': None,
            'searched': candidates,
            'problem': ('the load reference %r could not be placed under the '
                        'declared search environment' % ref)}


def _digest(path: str, read_bytes: Callable[[str], bytes]) -> Dict[str, Any]:
    try:
        blob = read_bytes(path)
    except Exception as exc:                                   # noqa: BLE001
        return {'unreadable': '%s: %s' % (type(exc).__name__, exc)}
    return {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def imports_dynamic_loader(path: Path) -> Dict[str, Any]:
    """Does this member import `dlopen`? Metadata only; nothing is executed.

    Root, 2026-09-23 14:03: "account for dynamically discovered backend/plugin
    paths under the selected configuration. If that selection cannot be bounded,
    mark the closure unresolved and refuse."

    This is not hypothetical for the candidate: `libggml` imports `dlopen` and
    carries `GGML_BACKEND_PATH` and `ggml_backend_load_best`, so ggml can select
    a backend at run time from a search path. Such a member can load a file that
    NO amount of `LC_LOAD_DYLIB` traversal will ever show, which means a static
    closure over load commands is not a bound on what will load.
    """
    out: Dict[str, Any] = {'path': str(path)}
    try:
        proc = subprocess.run(['nm', '-u', str(path)], capture_output=True,
                              text=True, timeout=60)
        out['dlopen'] = ('_dlopen' in proc.stdout)
        if proc.returncode != 0 and not proc.stdout:
            out['error'] = 'nm -u failed: %s' % proc.stderr.strip()[:200]
    except Exception as exc:                                   # noqa: BLE001
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
    return out


def derive_closure(root_path: str, *, metadata: Callable[[str], Dict[str, Any]],
                   exists: Callable[[str], bool],
                   read_bytes: Callable[[str], bytes],
                   executable_dir: Optional[str] = None,
                   dynamic_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
                   dynamic_policy: Optional[Dict[str, Any]] = None,
                   max_members: int = 512) -> Dict[str, Any]:
    """STAGE ONE. Walk the selected launcher's dependency graph, transitively.

    Returns the resolved closure, or ``resolved: False`` with the edges that
    could not be bounded. A caller must refuse on the latter: root's
    instruction is to "mark the closure unresolved and refuse instead of
    certifying the nine-entry inventory as complete".
    """
    exe_dir = executable_dir or str(Path(root_path).parent)
    members: Dict[str, Dict[str, Any]] = {}
    system_refs: List[str] = []
    unresolved: List[Dict[str, Any]] = []
    seen: set = set()
    queue: List[str] = [root_path]
    truncated = False
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        meta = metadata(current)
        if meta.get('error'):
            unresolved.append({'file': current, 'problem': meta['error']})
            continue
        loader_dir = str(Path(current).parent)
        for ref in meta.get('load_references') or []:
            if is_system_reference(ref):
                if ref not in system_refs:
                    system_refs.append(ref)
                continue
            r = resolve_reference(ref, rpaths=meta.get('rpaths') or [],
                                  loader_dir=loader_dir,
                                  executable_dir=exe_dir, exists=exists)
            if not r.get('resolved'):
                unresolved.append({'file': current, 'reference': ref,
                                   'problem': r['problem'],
                                   'searched': r.get('searched')})
                continue
            # KEYED BY EDGE, not by digest: a hash-correct file at the wrong
            # path cannot satisfy a required edge, because what loads is chosen
            # by path.
            key = ref
            entry = dict(r, required_by=current,
                         **_digest(r['resolved'], read_bytes))
            if entry.get('unreadable'):
                unresolved.append({'file': current, 'reference': ref,
                                   'problem': 'resolved but unreadable: %s'
                                              % entry['unreadable']})
                continue
            prior = members.get(key)
            if prior and prior['resolved'] != entry['resolved']:
                unresolved.append({
                    'reference': ref,
                    'problem': ('the same reference resolves to two different '
                                'paths (%s and %s); the selection is ambiguous'
                                % (prior['resolved'], entry['resolved']))})
                continue
            members.setdefault(key, entry)
            if len(members) > max_members:
                truncated = True
                queue = []
                break
            queue.append(r['resolved'])
    if truncated:
        unresolved.append({'problem': 'the closure exceeded %d members and was '
                                      'not bounded' % max_members})

    # THE DYNAMIC-LOADING BOUND. A member that can `dlopen` may load a file no
    # traversal of load commands will ever show, so the static closure is not a
    # bound on what will load unless the caller states how that search is
    # confined. Root: "If that selection cannot be bounded, mark the closure
    # unresolved and refuse instead of certifying the nine-entry inventory as
    # complete."
    dynamic: Dict[str, Any] = {'checked': dynamic_loader is not None,
                               'members_importing_dlopen': []}
    if dynamic_loader is not None:
        for target in [root_path] + [e['resolved'] for e in members.values()]:
            info = dynamic_loader(target)
            if info.get('error'):
                unresolved.append({'file': target,
                                   'problem': 'could not determine dynamic '
                                              'loading: %s' % info['error']})
            elif info.get('dlopen'):
                dynamic['members_importing_dlopen'].append(target)
        if dynamic['members_importing_dlopen']:
            dynamic['policy'] = dynamic_policy
            if not dynamic_policy or not dynamic_policy.get('bounded'):
                unresolved.append({
                    'problem': ('%d member(s) import dlopen and the launch '
                                'environment does not bound their search, so '
                                'what will load is not determined by the load '
                                'commands: %s'
                                % (len(dynamic['members_importing_dlopen']),
                                   ', '.join(Path(x).name for x in
                                             dynamic['members_importing_dlopen']))),
                    'remedy': ('pin the backend search environment and enumerate '
                               'it into the closure, or establish that the '
                               'selected configuration performs no dynamic '
                               'backend load')})
    return {
        'schema': 'live_ab/dependency_closure-v1',
        'root': root_path,
        'executable_dir': exe_dir,
        'members': members,
        'member_count': len(members),
        'system_references': sorted(system_refs),
        'dynamic_loading': dynamic,
        'unresolved': unresolved,
        'resolved': not unresolved,
        'note': ('transitive over non-system members. System references are '
                 'recorded by name and never pinned or traversed, per root '
                 '2026-09-23 12:42.'),
    }


def verify_closure(frozen: Dict[str, Any], *,
                   metadata: Callable[[str], Dict[str, Any]],
                   exists: Callable[[str], bool],
                   read_bytes: Callable[[str], bytes]) -> Dict[str, Any]:
    """STAGE TWO. Re-derive now and compare with the frozen set.

    Root: "at preflight, independently resolve the actual selected load
    references under that frozen environment and compare the required
    membership, canonical resolved paths and measured bytes to the reviewed
    manifest. Missing required members, unexpected non-system resolution,
    changed paths or source/patch/build mismatches refuse BEFORE Popen."
    """
    problems: List[str] = []
    if not isinstance(frozen, dict) or frozen.get('schema') != 'live_ab/dependency_closure-v1':
        return {'verified': False, 'problems': ['no frozen dependency closure was '
                                                'supplied to verify against']}
    if not frozen.get('resolved'):
        problems.append('the frozen closure was itself unresolved and cannot be '
                        'used as a requirement')
    now = derive_closure(frozen['root'], metadata=metadata, exists=exists,
                         read_bytes=read_bytes,
                         executable_dir=frozen.get('executable_dir'))
    if not now['resolved']:
        problems.append('the closure cannot be resolved now: %s'
                        % '; '.join(u['problem'] for u in now['unresolved'][:4]))
    want, got = frozen.get('members') or {}, now['members']
    rows = []
    for ref in sorted(set(want) | set(got)):
        w, g = want.get(ref), got.get(ref)
        row: Dict[str, Any] = {'reference': ref}
        if w and not g:
            row['problem'] = ('required member %r is no longer reached by the '
                              'dependency graph' % ref)
        elif g and not w:
            row['problem'] = ('%r is loaded now but is not in the frozen '
                              'closure: an unexpected non-system resolution' % ref)
        else:
            row.update({'frozen_path': w['resolved'], 'resolved_path': g['resolved'],
                        'frozen_sha256': w.get('sha256'),
                        'measured_sha256': g.get('sha256')})
            if w['resolved'] != g['resolved']:
                row['problem'] = ('%r resolves to %s but was frozen at %s'
                                  % (ref, g['resolved'], w['resolved']))
            elif w.get('sha256') != g.get('sha256'):
                row['problem'] = ('%r changed bytes at the same path' % ref)
            else:
                row['agrees'] = True
        rows.append(row)
        if row.get('problem'):
            problems.append(row['problem'])
    return {
        'verified': not problems,
        'problems': problems,
        'members_checked': len(rows),
        'members_agreeing': sum(1 for r in rows if r.get('agrees')),
        'rows': rows,
        'note': ('membership is keyed by the dependency EDGE. A hash-correct '
                 'unrelated file at another path cannot satisfy a required '
                 'edge, because what loads is chosen by path.'),
    }
