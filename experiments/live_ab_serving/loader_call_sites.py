"""Deposit the loader call sites, with their linkage into the candidate, as excerpts.

Root, 2026-09-23 16:30 (reviews/build_snapshot_review_20260923_1630.md): "The
sentence asserting every loader call site in `common/`, `src/` and
`tools/server/` uses argument-free `load_all()` is a literal in the snapshot
generator, without collected caller locations/source excerpts ... If the owner
relies on an all-default-call-sites proof, deposit the exact existing matching
source excerpts with paths, line locations and source-file hashes rather than
another summary assertion."

The contract does rely on it: the dynamic bound enumerates the DEFAULT search
locations, which is only the whole search if nothing linked into the candidate
passes a directory. So this collects, from the candidate's own source tree:

  * every match for the loader entry points and `dlopen`, anywhere in the tree
    (not only the three directories the old sentence named), with the exact
    line, its path, line number and the SHA-256 of the file it came from; and
  * for each matching file, whether it is actually LINKED into the launcher or
    one of its nine non-system members -- derived from the generated build
    rules (`build.ninja` link and archive statements, followed through static
    archives) and `compile_commands.json` (object -> source), not from where a
    file happens to sit. Unity-build translation units are followed through
    their generated `#include` lines to the real sources.

A header match is recorded and classified as a header: headers are compiled
into their includers, and the binary evidence for those (which members import
`dlopen`) is the owner's `nm -u` observation, reported separately.

READ-ONLY. Nothing is built, configured, executed or loaded; no native tool is
run. It reads text files of an existing tree and writes one receipt.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

#: What is searched for. Deliberately broader than the call the contract depends
#: on, so a different loader entry point cannot sit in the tree unnoticed.
PATTERNS = {
    'ggml_backend_load_all': r'\bggml_backend_load_all\s*\(',
    'ggml_backend_load_all_from_path': r'\bggml_backend_load_all_from_path\s*\(',
    'ggml_backend_load': r'\bggml_backend_load\s*\(',
    'ggml_backend_load_best': r'\bggml_backend_load_best\s*\(',
    'dl_load_library': r'\bdl_load_library\s*\(',
    'dlopen': r'\bdlopen\s*\(',
    'GGML_BACKEND_PATH': r'\bGGML_BACKEND_PATH\b',
}
SOURCE_SUFFIXES = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.m', '.mm')
HEADER_SUFFIXES = ('.h', '.hpp')


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- build-graph parsing (pure; tested on synthetic text) ----------------------
def ninja_statements(text: str) -> dict:
    """output -> {'rule', 'explicit', 'implicit', 'variables'}.

    Ninja continues long lines with a trailing `$`; those are joined first. The
    indented variable lines under a statement are kept: CMake names the static
    archives and shared libraries a target links in `LINK_LIBRARIES`, NOT in
    the explicit inputs -- the launcher's explicit inputs are one object file."""
    joined = re.sub(r'\$\n\s*', ' ', text)
    out = {}
    current = []
    for line in joined.splitlines():
        if line.startswith('build '):
            head, _, rest = line[len('build '):].partition(':')
            outputs = head.split('|')[0].split()
            toks = rest.split()
            current = []
            if not toks:
                continue
            rule, ins = toks[0], toks[1:]
            explicit, implicit, mode = [], [], 'e'
            for t in ins:
                if t == '|':
                    mode = 'i'
                elif t == '||':
                    mode = 'o'
                elif mode == 'e':
                    explicit.append(t)
                elif mode == 'i':
                    implicit.append(t)
            for o in outputs:
                out[o] = {'rule': rule, 'explicit': explicit, 'implicit': implicit,
                          'variables': {}}
                current.append(out[o])
        elif line.startswith('  ') and current:
            k, _, v = line.strip().partition(' = ')
            for st in current:
                st['variables'][k] = v
        else:
            current = []
    return out


def linked_objects(statements: dict, target: str, _seen=None) -> list:
    """Every object file linked into `target`, following static archives named
    either as explicit inputs or in `LINK_LIBRARIES`.

    Shared libraries are NOT followed: each is a separate member of the closure,
    examined as its own target."""
    seen = _seen if _seen is not None else set()
    if target in seen or target not in statements:
        return []
    seen.add(target)
    st = statements[target]
    objs = [i for i in st['explicit'] if i.endswith('.o')]
    archives = [i for i in st['explicit'] if i.endswith('.a')]
    archives += [t for t in (st.get('variables', {}).get('LINK_LIBRARIES') or '').split()
                 if t.endswith('.a') and t not in archives]
    for a in archives:
        if a not in statements:
            objs.append('UNRESOLVED-ARCHIVE:' + a)
            continue
        objs.extend(linked_objects(statements, a, seen))
    return objs


def unity_includes(text: str) -> list:
    """The real sources a generated unity translation unit includes."""
    return re.findall(r'^\s*#\s*include\s+"([^"]+)"', text, re.M)


def _in_string_or_comment(line: str, pos: int):
    """Is character `pos` inside a string literal or a comment? Returns
    'string', 'comment' or None."""
    quote, i = None, 0
    while i < pos:
        ch = line[i]
        if quote:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in '"\'':
            quote = ch
        elif line.startswith('//', i):
            return 'comment'
        i += 1
    if quote:
        return 'string'
    if line.lstrip().startswith(('*', '/*')):
        return 'comment'
    return None


def match_lines(text: str) -> list:
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        for name, rx in PATTERNS.items():
            m = re.search(rx, line)
            if m:
                rows.append({'line': n, 'pattern': name, 'text': line.strip()[:240],
                             'context': _in_string_or_comment(line, m.start()) or 'code'})
    return rows


def classify_call(row: dict) -> str:
    """What a `ggml_backend_load_all*` match does to the search set."""
    t = row['text']
    # A NAME IN A LOG STRING IS NOT A CALL. `src/llama.cpp:407` prints
    # "use ggml_backend_load() or ggml_backend_load_all()"; the first draft
    # counted it as a default-search call.
    if row.get('context') in ('string', 'comment'):
        return 'mention inside a %s, not a call' % row['context']
    # DEFINITIONS FIRST. `void ggml_backend_load_all() {` also matches the call
    # shape; checked the other way round it was counted as a default call --
    # the first control run caught exactly that.
    if row['pattern'] == 'ggml_backend_load_all':
        if re.search(r'\bvoid\s+ggml_backend_load_all\s*\(\s*(void)?\s*\)', t):
            return 'declaration or definition, not a call'
        if re.search(r'\bggml_backend_load_all\s*\(\s*\)', t):
            return 'default-search call, no directory argument'
        return 'UNCLASSIFIED: inspect'
    if row['pattern'] == 'ggml_backend_load_all_from_path':
        if re.search(r'\bvoid\s+ggml_backend_load_all_from_path\s*\(\s*const', t):
            return 'declaration or definition, not a call'
        if re.search(r'ggml_backend_load_all_from_path\s*\(\s*nullptr\s*\)', t):
            return 'the default search itself (load_all forwards nullptr)'
        return 'EXPLICIT-DIRECTORY CALL: changes the search set'
    return 'recorded'


def main() -> int:
    manifest_path = REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json'
    receipt = REPO / 'results/live_ab/LOADER_CALL_SITE_EXCERPTS.json'
    if receipt.exists():
        print('refusing: the receipt exists; this is write-once', file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    src = Path(manifest['source_and_patch']['source_tree'])
    build = src / 'build'
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    statements = ninja_statements((build / 'build.ninja').read_text())
    cc = json.loads((build / 'compile_commands.json').read_text())
    obj_to_src = {}
    for e in cc:
        o = e.get('output')
        if o:
            obj_to_src[os.path.normpath(os.path.join(e['directory'], o))] = e['file']

    targets = ['bin/llama-server', 'bin/libllama-server-impl.dylib',
               'bin/libggml.0.24.0.dylib', 'bin/libggml-base.0.24.0.dylib',
               'bin/libggml-cpu.0.24.0.dylib', 'bin/libggml-blas.0.24.0.dylib',
               'bin/libggml-metal.0.24.0.dylib', 'bin/libllama.0.4.1.dylib',
               'bin/libllama-common.0.4.1.dylib', 'bin/libmtmd.0.4.1.dylib']
    linked = {}                                    # real source -> [targets]
    unmapped = []
    for t in targets:
        if t not in statements:
            unmapped.append({'target': t, 'problem': 'no build statement'})
            continue
        for o in linked_objects(statements, t):
            if o.startswith('UNRESOLVED-ARCHIVE:'):
                unmapped.append({'target': t, 'archive': o.split(':', 1)[1],
                                 'problem': 'a linked archive has no build statement'})
                continue
            s = obj_to_src.get(os.path.normpath(str(build / o)))
            if s is None:
                unmapped.append({'target': t, 'object': o,
                                 'problem': 'no compile command for this object'})
                continue
            reals = [s]
            if '/Unity/' in s and s.endswith(('.cxx', '.cpp', '.c')):
                reals = [os.path.normpath(os.path.join(os.path.dirname(s), i))
                         for i in unity_includes(Path(s).read_text())]
            for r in reals:
                linked.setdefault(os.path.realpath(r), set()).add(t)

    sites = []
    for p in sorted(src.rglob('*')):
        if not p.is_file() or p.suffix not in SOURCE_SUFFIXES:
            continue
        rel = p.relative_to(src)
        if rel.parts and rel.parts[0] == 'build':
            continue
        try:
            text = p.read_text(errors='replace')
        except OSError:
            continue
        rows = match_lines(text)
        if not rows:
            continue
        real = os.path.realpath(p)
        kind = 'header' if p.suffix in HEADER_SUFFIXES else 'translation unit'
        for r in rows:
            sites.append(dict(r, path=str(rel), sha256=sha256_file(p), kind=kind,
                              linked_into=sorted(linked.get(real, ())),
                              classification=classify_call(r)))

    linked_calls = [s for s in sites if s['linked_into'] and s['kind'] != 'header'
                    and s['pattern'] in ('ggml_backend_load_all',
                                         'ggml_backend_load_all_from_path')
                    and not s['classification'].startswith(('mention', 'declaration'))]
    explicit_dir_linked = [s for s in linked_calls
                           if s['classification'].startswith('EXPLICIT')]
    unclassified_linked = [s for s in linked_calls
                           if s['classification'].startswith('UNCLASSIFIED')]
    doc = {
        'schema': 'live_ab/loader_call_site_excerpts-v1',
        'convention': 'deterministic-path',
        'generated_utc': t0,
        'authority': ('root, reviews/build_snapshot_review_20260923_1630.md, '
                      'call-site paragraph'),
        'nothing_executed_THIS_RECEIPT': ('text reads of an existing tree only; no '
                                          'build, configure, native tool, candidate '
                                          'execution or model load'),
        'source_tree': str(src),
        'source_head_declared': manifest['source_and_patch']['base_commit'],
        'build_rules': {n: {'path': str(build / n), 'sha256': sha256_file(build / n)}
                        for n in ('build.ninja', 'compile_commands.json')},
        'patterns': PATTERNS,
        'targets': targets,
        'linkage_problems': unmapped,
        'linked_translation_units': {k: sorted(v) for k, v in sorted(linked.items())},
        'sites': sites,
        'summary': {
            'sites_total': len(sites),
            'load_all_calls_linked_into_the_candidate': len(linked_calls),
            'by_classification_linked': {
                c: sum(1 for s in sites if s['linked_into'] and s['classification'] == c)
                for c in sorted({s['classification'] for s in sites if s['linked_into']})},
            'explicit_directory_calls_linked_into_the_candidate': len(explicit_dir_linked),
            'unclassified_calls_linked_into_the_candidate': len(unclassified_linked),
            'finding': (
                'every ggml_backend_load_all* call in a translation unit linked into '
                'the launcher or its nine members uses the default search '
                '(no directory argument)'
                if linked_calls and not explicit_dir_linked and not unclassified_linked
                and not unmapped else
                'NOT ESTABLISHED: see linkage_problems and the linked calls'),
        },
        'scope': ('source-level linkage of translation units, from the generated build '
                  'rules. Header-inline code is classified as header; which members '
                  'actually import dlopen is the separate owner-reported nm -u '
                  'observation. This is not a call-graph proof that any call runs.'),
    }
    receipt.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt, json.dumps(doc['summary']))
    return 0


# -- the build-rule deposit root asked for at 17:52 ---------------------------
TARGETS = ['bin/llama-server', 'bin/libllama-server-impl.dylib',
           'bin/libggml.0.24.0.dylib', 'bin/libggml-base.0.24.0.dylib',
           'bin/libggml-cpu.0.24.0.dylib', 'bin/libggml-blas.0.24.0.dylib',
           'bin/libggml-metal.0.24.0.dylib', 'bin/libllama.0.4.1.dylib',
           'bin/libllama-common.0.4.1.dylib', 'bin/libmtmd.0.4.1.dylib']


def statement_block(text: str, output: str):
    """The verbatim `build` statement for `output`, with its variable lines,
    exactly as the generated file has it (continuation lines included)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('build '):
            continue
        head = line[len('build '):].split(':', 1)[0]
        if output not in head.split('|')[0].split():
            continue
        block = [line]
        j = i + 1
        while block[-1].endswith('$') and j < len(lines):      # continuation
            block.append(lines[j])
            j += 1
        while j < len(lines) and lines[j].startswith('  '):
            block.append(lines[j])
            j += 1
        return '\n'.join(block)
    return None


def linkage_from_deposit(deposit: dict) -> dict:
    """Re-derive target -> linked real sources from the DEPOSIT ALONE.

    Pure: it reads only the deposited statements, object-to-source mappings and
    unity include lines, so a reviewer without the owner's tree can check that
    the call-site receipt's linkage follows from the deposited rules."""
    statements = ninja_statements('\n\n'.join(deposit['statements'].values()))
    obj_to_src = {m['object']: m['file'] for m in deposit['object_to_source']}
    unity = {u['path']: u['includes'] for u in deposit['unity_units']}
    build = deposit['build_directory']
    linked, problems = {}, []
    for t in deposit['targets']:
        if t not in statements:
            problems.append('no deposited statement for %s' % t)
            continue
        for o in linked_objects(statements, t):
            if o.startswith('UNRESOLVED-ARCHIVE:'):
                problems.append('%s links an undeposited archive %s' % (t, o[19:]))
                continue
            src = obj_to_src.get(o)
            if src is None:
                problems.append('%s links %s with no deposited mapping' % (t, o))
                continue
            reals = ([os.path.normpath(os.path.join(os.path.dirname(src), i))
                      for i in unity[src]] if src in unity else [src])
            for r in reals:
                linked.setdefault(r, set()).add(t)
    return {'linked': {k: sorted(v) for k, v in sorted(linked.items())},
            'problems': problems, 'build_directory': build}


def deposit_build_rules() -> int:
    manifest_path = REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json'
    sites_path = REPO / 'results/live_ab/LOADER_CALL_SITE_EXCERPTS.json'
    out_path = REPO / 'results/live_ab/LOADER_LINKAGE_BUILD_RULES.json'
    if out_path.exists():
        print('refusing: the deposit exists; this is write-once', file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    src = Path(manifest['source_and_patch']['source_tree'])
    build = src / 'build'
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    ninja_text = (build / 'build.ninja').read_text()
    statements = ninja_statements(ninja_text)
    cc = json.loads((build / 'compile_commands.json').read_text())
    by_output = {}
    for e in cc:
        if e.get('output'):
            by_output[os.path.normpath(os.path.join(e['directory'], e['output']))] = e

    # every statement the ten targets reach: themselves and every archive
    wanted, queue = [], list(TARGETS)
    while queue:
        t = queue.pop(0)
        if t in wanted:
            continue
        wanted.append(t)
        st = statements.get(t) or {}
        ins = list(st.get('explicit', [])) + (
            st.get('variables', {}).get('LINK_LIBRARIES') or '').split()
        queue.extend(i for i in ins if i.endswith('.a') and i not in wanted)
    blocks = {t: statement_block(ninja_text, t) for t in wanted}

    mappings, unity_units = [], []
    for t in TARGETS:
        for o in linked_objects(statements, t):
            if o.startswith('UNRESOLVED-ARCHIVE:') or o in {m['object'] for m in mappings}:
                continue
            e = by_output.get(os.path.normpath(str(build / o)))
            if e is None:
                continue
            mappings.append({'object': o, 'file': e['file'], 'directory': e['directory'],
                             'output': e.get('output'),
                             'entry_sha256': hashlib.sha256(json.dumps(
                                 e, sort_keys=True).encode()).hexdigest()})
            if '/Unity/' in e['file'] and e['file'] not in {u['path'] for u in unity_units}:
                up = Path(e['file'])
                unity_units.append({'path': e['file'], 'sha256': sha256_file(up),
                                    'includes': unity_includes(up.read_text())})
    deposit = {
        'schema': 'live_ab/loader_linkage_build_rules-v1',
        'convention': 'post-build-provenance',
        'generated_utc': t0,
        'authority': ('root, reviews/dependency_callsite_disposition_20260923_1752.md: '
                      '"deposit the existing relevant generated link/archive statements '
                      'and object-to-source compile mappings (with their original-file '
                      'hashes)"'),
        'nothing_executed_THIS_RECEIPT': 'text reads of existing generated files only',
        'build_directory': str(build),
        'originals': {n: {'path': str(build / n), 'bytes': (build / n).stat().st_size,
                          'sha256': sha256_file(build / n)}
                      for n in ('build.ninja', 'compile_commands.json')},
        'targets': TARGETS,
        'statements': blocks,
        'object_to_source': mappings,
        'unity_units': unity_units,
        'how_to_check': ('linkage_from_deposit(this) in '
                         'experiments/live_ab_serving/loader_call_sites.py re-derives '
                         'target -> linked sources from these statements, mappings and '
                         'unity includes ALONE; its result is compared below with the '
                         'call-site receipt. The whole-file digests above bind the '
                         'excerpts to the originals for anyone holding them.'),
    }
    rederived = linkage_from_deposit(deposit)
    receipt = json.loads(sites_path.read_text())
    want = {os.path.realpath(k): v for k, v in receipt['linked_translation_units'].items()}
    got = {os.path.realpath(k): v for k, v in rederived['linked'].items()}
    deposit['rederivation'] = {
        'problems': rederived['problems'],
        'linked_translation_units': len(got),
        'call_site_receipt': {'path': str(sites_path.relative_to(REPO)),
                              'sha256': sha256_file(sites_path)},
        'agrees_with_call_site_receipt': want == got,
        'differences': sorted(set(want) ^ set(got))[:20],
    }
    out_path.write_text(json.dumps(deposit, indent=1, sort_keys=True) + '\n')
    print(out_path, json.dumps(deposit['rederivation'])[:300])
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(deposit_build_rules() if '--deposit-build-rules' in sys.argv else main())
