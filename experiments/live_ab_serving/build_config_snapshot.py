"""A read-only snapshot of the candidate's EXISTING build configuration.

Root, 2026-09-23 14:41 (reviews/backend_selection_source_review_20260923_1441.md):
"Copy and hash the existing closed cache plus relevant compiler/link rules as
post-execution reconciliation, retaining the current candidate rather than
rebuilding it. Required settings are BUILD_SHARED_LIBS, GGML_BACKEND_DL,
GGML_BACKEND_DIR, enabled backend options/available-backend list,
GGML_CPU_ALL_VARIANTS and GGML_METAL_EMBED_LIBRARY; relevant compile definitions
and link dependencies must agree with those values and the measured candidate
bytes."

POST-BUILD PROVENANCE. Everything here was produced by a build that already
happened; this file reads it afterwards. It is a reconciliation, not a
pre-execution record, and it does not turn a retrospective inventory into one.

Nothing is configured, built, executed or loaded. `nm` reads symbol tables and
`git` reads the source tree's index; neither runs the candidate.

A CONFIGURED value is not a COMPILED one. The cache says what CMake was asked
for; the compile database and the ninja link rules say what the compiler and
linker were actually given; the measured bytes say what came out. Each setting
root named is checked across those layers, and a disagreement is reported as a
disagreement, never resolved in favour of the layer that reads better.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# The settings root named, plus every backend switch the pinned revision knows,
# so an enabled backend cannot hide by being left off the list. Root, 16:30: the
# list omitted `GGML_ET` although ggml/src/CMakeLists.txt at 4fea119 declares
# `ggml_add_backend(ET)`. It is now the source's whole `ggml_add_backend` list,
# and the cache's own GGML_AVAILABLE_BACKENDS is checked against it, so an
# enabled backend outside this list disagrees instead of passing unseen.
REQUIRED_CACHE = ('BUILD_SHARED_LIBS', 'GGML_BACKEND_DL', 'GGML_BACKEND_DIR',
                  'GGML_CPU_ALL_VARIANTS', 'GGML_METAL_EMBED_LIBRARY',
                  'GGML_NATIVE', 'CMAKE_BUILD_TYPE', 'CMAKE_SKIP_RPATH')
BACKEND_OPTIONS = ('GGML_CPU', 'GGML_BLAS', 'GGML_CANN', 'GGML_CUDA', 'GGML_ET',
                   'GGML_HIP', 'GGML_METAL', 'GGML_MUSA', 'GGML_RPC',
                   'GGML_VIRTGPU', 'GGML_SYCL', 'GGML_VULKAN', 'GGML_WEBGPU',
                   'GGML_ZDNN', 'GGML_OPENCL', 'GGML_HEXAGON', 'GGML_ZENDNN',
                   'GGML_OPENVINO')
# The registry translation unit: its -D flags decide which backends are
# registered at compile time and whether the dynamic-loading branch exists.
REGISTRY_SOURCES = ('ggml/src/ggml-backend-reg.cpp', 'ggml/src/ggml-backend-dl.cpp')
METAL_SOURCES = ('ggml/src/ggml-metal/ggml-metal-device.m',
                 'ggml/src/ggml-metal/ggml-metal.cpp')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# -- parsers (pure; tested on synthetic text) ---------------------------------
def parse_cmake_cache(text: str) -> dict:
    """`NAME:TYPE=VALUE` lines. Comments and blank lines are skipped; a line
    that looks like neither is kept as unparsed rather than dropped."""
    entries, unparsed = {}, []
    for line in text.splitlines():
        if not line.strip() or line.startswith('#') or line.startswith('//'):
            continue
        m = re.match(r'^([^:=]+):([A-Z_]+)=(.*)$', line)
        if m is None:
            unparsed.append(line)
            continue
        entries[m.group(1)] = {'type': m.group(2), 'value': m.group(3)}
    return {'entries': entries, 'unparsed_lines': unparsed}


def compile_definitions(entries: list, suffix: str) -> dict:
    """The -D flags the compiler was given for the ONE source ending in
    `suffix`. Zero or several matches are reported, not guessed between."""
    hits = [e for e in entries if str(e.get('file', '')).endswith(suffix)]
    if len(hits) != 1:
        return {'source': suffix, 'error': '%d compile entries match' % len(hits)}
    e = hits[0]
    argv = e.get('arguments') or shlex.split(e.get('command', ''))
    defs = []
    for i, a in enumerate(argv):
        if a == '-D' and i + 1 < len(argv):
            defs.append(argv[i + 1])
        elif a.startswith('-D') and len(a) > 2:
            defs.append(a[2:])
    return {'source': suffix, 'file': e.get('file'), 'output': e.get('output'),
            'definitions': sorted(set(defs)),
            'entry_sha256': sha256_bytes(json.dumps(e, sort_keys=True).encode())}


def ninja_build_block(text: str, output: str) -> dict:
    """The `build <output>: RULE ...` statement and its indented variables."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('build '):
            continue
        head = line[len('build '):]
        outs = head.split(':', 1)[0].split()
        if output not in outs:
            continue
        block = [line]
        for nxt in lines[i + 1:]:
            if nxt.startswith('  '):
                block.append(nxt)
            else:
                break
        rule_and_inputs = head.split(':', 1)[1].split()
        variables = {}
        for v in block[1:]:
            k, _, val = v.strip().partition(' = ')
            variables[k] = val
        return {'output': output, 'rule': rule_and_inputs[0] if rule_and_inputs else None,
                'statement': block[0], 'variables': variables,
                'block_text': '\n'.join(block)}
    return {'output': output, 'error': 'no build statement for this output'}


def link_libraries(block: dict) -> list:
    return [t for t in (block.get('variables', {}).get('LINK_LIBRARIES') or '').split()
            if not t.startswith('-')]


def ninja_log_outputs(text: str) -> list:
    """`.ninja_log` v5+: start, end, mtime, output, hash -- tab separated."""
    rows = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 5:
            rows.append({'start_ms': int(parts[0]), 'end_ms': int(parts[1]),
                         'mtime': int(parts[2]), 'output': parts[3]})
    return rows


# -- agreement checks (pure) -------------------------------------------------
def _on(v) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ('ON', 'YES', 'TRUE', '1', 'Y'):
        return True
    if s in ('OFF', 'NO', 'FALSE', '0', 'N', ''):
        return False
    return None


def agreement_checks(cache: dict, registry_defs: list, metal_defs: list,
                     libggml_links: list, any_backend_dir_define: bool,
                     metal_embed_symbols: int | None, cpu_variant_files: list) -> list:
    """Each check names every layer it compared. `agrees` is None when a layer
    is missing: an unreadable layer is not agreement."""
    c = cache['entries']
    val = lambda k: (c.get(k) or {}).get('value')
    reg = set()
    for d in registry_defs or []:
        reg.update([d])
    checks = []

    dl = _on(val('GGML_BACKEND_DL'))
    dl_define = any(d.split('=')[0] == 'GGML_BACKEND_DL' for d in registry_defs or [])
    checks.append({
        'check': 'GGML_BACKEND_DL',
        'cache': val('GGML_BACKEND_DL'), 'registry_compiled_with_GGML_BACKEND_DL': dl_define,
        'agrees': None if dl is None or registry_defs is None else (dl == dl_define)})

    bdir = val('GGML_BACKEND_DIR')
    checks.append({
        'check': 'GGML_BACKEND_DIR',
        'cache': bdir, 'any_compile_defines_GGML_BACKEND_DIR': any_backend_dir_define,
        'agrees': None if bdir is None else ((bdir == '') == (not any_backend_dir_define))})

    enabled = sorted(k[len('GGML_'):] for k in BACKEND_OPTIONS if _on(val(k)))
    registered = sorted(d.split('=')[0][len('GGML_USE_'):] for d in (registry_defs or [])
                        if d.startswith('GGML_USE_'))
    checks.append({
        'check': 'enabled backends == GGML_USE_* on the registry',
        'cache_enabled': enabled, 'registry_GGML_USE': registered,
        'agrees': None if registry_defs is None else (enabled == registered)})

    # THE CACHE'S OWN LIST, against the options this module knows. An available
    # backend with no option here is UNSUPPORTED and disagrees -- the list is
    # only exhaustive if nothing enabled can fall outside it.
    avail_raw = val('GGML_AVAILABLE_BACKENDS')
    available = sorted(a.strip()[len('ggml-'):].upper() for a in (avail_raw or '').split(';')
                       if a.strip())
    known = {k[len('GGML_'):] for k in BACKEND_OPTIONS}
    unsupported = sorted(a for a in available if a not in known)
    checks.append({
        'check': 'GGML_AVAILABLE_BACKENDS == enabled options, all supported',
        'cache_available': available, 'cache_enabled': enabled,
        'unsupported_available': unsupported,
        'agrees': None if avail_raw is None else (available == enabled
                                                   and not unsupported)})

    # With DL OFF the enabled backends are LINKED into libggml, not discovered.
    linked = sorted(set(re.sub(r'^.*libggml-([a-z]+)\..*$', r'\1', t).upper()
                        for t in libggml_links if re.search(r'libggml-[a-z]+\.', t))
                    - {'BASE'})
    checks.append({
        'check': 'libggml links exactly the enabled backends',
        'cache_enabled': enabled, 'libggml_link_backends': linked,
        'agrees': None if not libggml_links else (linked == enabled)})

    emb = _on(val('GGML_METAL_EMBED_LIBRARY'))
    emb_define = any(d.split('=')[0] == 'GGML_METAL_EMBED_LIBRARY' for d in metal_defs or [])
    checks.append({
        'check': 'GGML_METAL_EMBED_LIBRARY',
        'cache': val('GGML_METAL_EMBED_LIBRARY'),
        'metal_compiled_with_define': emb_define,
        'embedded_source_symbols_in_measured_libggml_metal': metal_embed_symbols,
        'agrees': (None if emb is None or metal_defs is None or metal_embed_symbols is None
                   else (emb == emb_define == (metal_embed_symbols > 0)))})

    cv = _on(val('GGML_CPU_ALL_VARIANTS'))
    checks.append({
        'check': 'GGML_CPU_ALL_VARIANTS',
        'cache': val('GGML_CPU_ALL_VARIANTS'), 'cpu_variant_files_present': cpu_variant_files,
        'agrees': None if cv is None else (cv == bool(cpu_variant_files))})

    sh = _on(val('BUILD_SHARED_LIBS'))
    checks.append({
        'check': 'BUILD_SHARED_LIBS',
        'cache': val('BUILD_SHARED_LIBS'),
        'libggml_links_dylibs': any(t.endswith('.dylib') for t in libggml_links),
        'agrees': None if sh is None or not libggml_links
        else (sh == any(t.endswith('.dylib') for t in libggml_links))})
    return checks


# -- the loader's search, as the pinned source defines it --------------------
def discovery_candidates(directory: Path) -> dict:
    """Everything `ggml_backend_load_best` could open in one search location.

    The source opens `libggml-<name>-*.so` (scored) and `libggml-<name>.so`
    (base) for fifteen names, via `is_regular_file`, which FOLLOWS symlinks.
    This enumerates the SUPERSET `libggml-*.so`, symlinks included, so a name
    added to the list later is still covered. Absence is recorded as absence.
    """
    row = {'directory': str(directory), 'exists': directory.is_dir()}
    if not row['exists']:
        row['candidates'] = []
        return row
    cands = []
    for p in sorted(directory.iterdir()):
        if p.name.startswith('libggml-') and p.suffix == '.so':
            c = {'name': p.name, 'is_symlink': p.is_symlink()}
            try:
                c['resolved'] = str(p.resolve())
                c['sha256'] = sha256_file(p) if p.is_file() else None
            except OSError as exc:
                c['error'] = '%s: %s' % (type(exc).__name__, exc)
            cands.append(c)
    row['candidates'] = cands
    return row


def _run(argv):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout, r.stderr
    except Exception as exc:                                   # noqa: BLE001
        return None, '', '%s: %s' % (type(exc).__name__, exc)


def main(argv=None) -> int:
    # PARAMETERIZED for the durable rebuild (root 18:29): the declaration, the
    # receipt and the copies directory are arguments; the defaults reproduce
    # the original /tmp candidate's snapshot exactly.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--declaration', default='results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json')
    ap.add_argument('--receipt', default='results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json')
    ap.add_argument('--copies', default='results/live_ab/candidate_build_snapshot')
    a = ap.parse_args(argv)
    manifest_path = REPO / a.declaration
    manifest = json.loads(manifest_path.read_text())
    src = Path(manifest['source_and_patch']['source_tree'])
    # the declaration may name its build tree; the original candidate's was
    # inside its source tree
    build = Path(manifest.get('build', {}).get('build_tree') or (src / 'build'))
    launcher_decl = manifest['candidate_instrument']['launcher']
    closure_decl = manifest['candidate_instrument']['library_closure']
    out_dir = REPO / a.copies
    receipt = REPO / a.receipt
    if receipt.exists() or out_dir.exists():
        print('refusing: a snapshot already exists; this is write-once', file=sys.stderr)
        return 2

    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    files = {}
    for name in ('CMakeCache.txt', 'compile_commands.json', 'build.ninja', '.ninja_log'):
        p = build / name
        st = p.stat()
        files[name] = {'path': str(p), 'bytes': st.st_size, 'sha256': sha256_file(p),
                       'mtime_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                  time.gmtime(st.st_mtime))}

    cache_text = (build / 'CMakeCache.txt').read_text()
    cache = parse_cmake_cache(cache_text)
    cc = json.loads((build / 'compile_commands.json').read_text())
    ninja = (build / 'build.ninja').read_text()
    nlog = ninja_log_outputs((build / '.ninja_log').read_text())

    registry = [compile_definitions(cc, s) for s in REGISTRY_SOURCES]
    metal = [compile_definitions(cc, s) for s in METAL_SOURCES]
    reg_defs = registry[0].get('definitions')
    metal_defs = metal[0].get('definitions')
    backend_dir_defined = any(
        any(d.split('=')[0] == 'GGML_BACKEND_DIR'
            for d in compile_definitions([e], str(e.get('file', ''))).get('definitions', []))
        for e in cc)

    outputs = ['bin/llama-server', 'bin/libllama-server-impl.dylib',
               'bin/libggml.0.24.0.dylib', 'bin/libggml-base.0.24.0.dylib',
               'bin/libggml-cpu.0.24.0.dylib', 'bin/libggml-blas.0.24.0.dylib',
               'bin/libggml-metal.0.24.0.dylib', 'bin/libllama.0.4.1.dylib',
               'bin/libllama-common.0.4.1.dylib', 'bin/libmtmd.0.4.1.dylib']
    blocks = {o: ninja_build_block(ninja, o) for o in outputs}
    libggml_links = link_libraries(blocks['bin/libggml.0.24.0.dylib'])

    # Embedded Metal source: symbols in the MEASURED library bytes, via `nm`.
    rc, so, se = _run(['nm', str(build / 'bin' / 'libggml-metal.0.dylib')])
    embed_syms = (len(re.findall(r'\b_ggml_metallib_\w+_start\b', so))
                  if rc == 0 else None)
    cpu_variants = sorted(p.name for p in (build / 'bin').iterdir()
                          if re.match(r'libggml-cpu-.+', p.name))
    checks = agreement_checks(cache, reg_defs, metal_defs, libggml_links,
                              backend_dir_defined, embed_syms, cpu_variants)

    # The measured candidate bytes against the declaration.
    measured = []
    lp = Path(launcher_decl['path'])
    measured.append({'member': 'launcher', 'path': str(lp),
                     'declared_sha256': launcher_decl['sha256'],
                     'measured_sha256': sha256_file(lp)})
    for name, d in closure_decl.items():
        if d.get('system_library'):
            continue
        p = Path(d['resolved'])
        measured.append({'member': name, 'path': str(p), 'declared_sha256': d['sha256'],
                         'measured_sha256': sha256_file(p) if p.exists() else None})
    for m in measured:
        m['agrees'] = m['measured_sha256'] == m['declared_sha256']

    # dlopen importers, by symbol table, over the declared members.
    importers = []
    for m in measured:
        rc, so, se = _run(['nm', '-u', m['path']])
        importers.append({'member': m['member'],
                          'imports_dlopen': (bool(re.search(r'^_dlopen$', so, re.M))
                                             if rc == 0 else None),
                          'error': se.strip()[:200] if rc != 0 else None})

    # Source identity.
    rc_h, head, _ = _run(['git', '-C', str(src), 'rev-parse', 'HEAD'])
    rc_s, status, _ = _run(['git', '-C', str(src), 'status', '--porcelain'])
    patch = REPO / manifest['source_and_patch']['patch']['path']
    rc_p, _, perr = _run(['git', '-C', str(src), 'apply', '--reverse', '--check', str(patch)])
    patch_files = sorted(set(re.findall(r'^\+\+\+ b/(\S+)', patch.read_text(), re.M)))
    modified = sorted(l[3:] for l in status.splitlines() if l.strip())

    # Root's pinned upstream sources, compared with this tree's bytes.
    ev = json.loads((REPO / 'reviews/evidence/'
                     'backend_selection_source_review_20260923_1441.json').read_text())
    pinned = []
    for s in ev.get('sources', []):
        p = src / s['path']
        h = sha256_file(p) if p.exists() else None
        pinned.append({'path': s['path'], 'root_sha256': s['sha256'], 'tree_sha256': h,
                       'agrees': h == s['sha256']})

    # The launch context the dynamic contract needs, as the source defines it.
    exe_dir_invoked = str(lp.parent)
    exe_dir_real = str(lp.resolve().parent)
    search = {
        'derivation': ('ggml_backend_load_best(name, silent, NULL): compiled '
                       'GGML_BACKEND_DIR if defined, then the executable directory '
                       '(_NSGetExecutablePath, the INVOKED path), then cwd; '
                       'ggml_backend_load_all() then loads GGML_BACKEND_PATH if set. '
                       'Every call site in common/, src/ and tools/server/ is '
                       'ggml_backend_load_all() with no directory argument.'),
        'compiled_backend_dir': ('absent: no compile command defines GGML_BACKEND_DIR'
                                 if not backend_dir_defined else 'DEFINED'),
        'executable_dir_as_invoked': discovery_candidates(Path(exe_dir_invoked)),
        'executable_dir_realpath': (discovery_candidates(Path(exe_dir_real))
                                    if exe_dir_real != exe_dir_invoked else 'same path'),
        'cwd': ('NOT FIXED by the current supervisor: run_smoke.py calls Popen with no '
                'cwd=, so the child inherits the operator\'s working directory, which '
                'is a search location. Unbounded until the launch fixes it.'),
        'GGML_BACKEND_PATH': ('NOT CONTROLLED by the current supervisor: the child env '
                              'is dict(os.environ, ...), so any value in the operator\'s '
                              'environment is inherited. Root chose explicitly unset.'),
        'this_process_environment_at_collection': {
            'GGML_or_DYLD_names_set': sorted(k for k in os.environ
                                             if k.startswith(('GGML_', 'DYLD_')))},
    }

    out_dir.mkdir(parents=True)
    shutil.copyfile(build / 'CMakeCache.txt', out_dir / 'CMakeCache.txt')
    shutil.copyfile(build / '.ninja_log', out_dir / 'ninja_log.txt')
    excerpt_cc = [e for e in cc if '/ggml/src/' in str(e.get('file', ''))]
    (out_dir / 'compile_commands.ggml_excerpt.json').write_text(
        json.dumps(excerpt_cc, indent=1) + '\n')
    (out_dir / 'build.ninja.link_excerpt.txt').write_text(
        '\n\n'.join(b.get('block_text', '# ' + b.get('error', '')) for b in blocks.values())
        + '\n')
    copies = {p.name: {'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
              for p in sorted(out_dir.iterdir())}
    copies_agree = (copies['CMakeCache.txt']['sha256'] == files['CMakeCache.txt']['sha256']
                    and copies['ninja_log.txt']['sha256'] == files['.ninja_log']['sha256'])

    rebuilt_after_config = [r['output'] for r in nlog if 'build.ninja' in r['output']]
    doc = {
        'schema': 'live_ab/candidate_build_config_snapshot-v1',
        'convention': 'post-build-provenance',
        'generated_utc': t0,
        'collection_completed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'authority': ('root, reviews/completion_and_backend_disposition_20260923_1441.md '
                      'and reviews/backend_selection_source_review_20260923_1441.md, '
                      '"Concrete next owner delivery"'),
        'what_this_is_not': [
            'not a pre-execution record: every file read here was produced by a build '
            'that had already happened',
            'not evidence of native loading behaviour: nothing was executed or loaded',
            'not a launch authorization and not a configuration change'],
        'nothing_executed_THIS_RECEIPT': ('no build, configure, candidate execution or '
                                          'model load; nm reads symbol tables and git '
                                          'reads the source index'),
        'candidate_declaration': {'path': str(manifest_path.relative_to(REPO)),
                                  'sha256': sha256_file(manifest_path)},
        'source_tree': str(src), 'build_tree': str(build),
        'originals': files,
        'copies_in_repo': {'directory': str(out_dir.relative_to(REPO)), 'files': copies,
                           'whole_file_copies_match_originals': copies_agree,
                           'excerpts': 'compile_commands entries under ggml/src; build.ninja '
                                       'statements for the launcher and nine members. The '
                                       'whole originals are pinned by sha256 above.'},
        'cache_settings': {k: cache['entries'].get(k) for k in REQUIRED_CACHE},
        'cache_backend_options': {k: cache['entries'].get(k) for k in BACKEND_OPTIONS},
        'cache_unparsed_lines': cache['unparsed_lines'],
        'compile_definitions': {'registry': registry, 'metal': metal,
                                'any_source_defines_GGML_BACKEND_DIR': backend_dir_defined},
        'link_rules': {o: {k: b.get(k) for k in ('rule', 'variables', 'error')}
                       for o, b in blocks.items()},
        'agreement': checks,
        'all_layers_agree': all(c['agrees'] is True for c in checks),
        'build_ninja_regenerated_after_configuration': rebuilt_after_config,
        'measured_candidate_bytes': measured,
        'measured_bytes_match_declaration': all(m['agrees'] for m in measured),
        'dlopen_importers': importers,
        'source_identity': {
            'head': head.strip() if rc_h == 0 else None,
            'declared_base': manifest['source_and_patch']['base_commit'],
            'modified_files': modified, 'patch_touches': patch_files,
            'patch_reverse_applies_cleanly': rc_p == 0,
            'patch_reverse_check_stderr': perr.strip()[:300],
            'root_pinned_upstream_sources': pinned},
        'loader_search_context': search,
    }
    receipt.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt, 'all_layers_agree=%s bytes_match=%s' % (
        doc['all_layers_agree'], doc['measured_bytes_match_declaration']))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
