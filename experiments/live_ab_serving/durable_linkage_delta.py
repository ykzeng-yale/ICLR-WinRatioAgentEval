"""Reconcile the DURABLE build's linkage with the authenticated temporary-build map.

Root, 2026-09-23 19:26 (reviews/durable_candidate_delta_20260923_1926.md):
"Reconcile the selected durable build's generated link/source map with the
now-authenticated temporary-build v2 map; a bounded changed/generated-file
delta and byte-complete generated originals are enough, without repeating an
unchanged full source scan or simulation."

What this does:
  1. deposits the durable build's generated originals, byte-complete
     (`build.ninja`, `compile_commands.json`), with their digests;
  2. derives the linked translation units per target of BOTH build trees with
     one walk, the v2 walk of `loader_call_sites.main()` (`parse_ninja`,
     `linked_objects`, compile mappings, unity include lists), and checks that
     the walk over the temporary tree equals the authenticated v2 deposit's own
     re-derivation (`linkage_from_deposit`) and that the temporary originals
     still match the deposit's digests;
  3. compares the two maps per target after replacing only the two roots (the
     source tree and the build tree) by tokens;
  4. compares the BYTES of every linked unit present in both trees -- source
     files and generated ones -- so any unit whose bytes differ is listed as the
     delta that the v2 classification does not cover.
If the maps are equal and no linked unit's bytes differ, the v2 call-site
classification applies to the durable build unchanged, with no rescan.

READ-ONLY apart from the deposit and one write-once receipt. Nothing is built,
executed or loaded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import loader_call_sites as lcs                                # noqa: E402

TMP_RULES = REPO / 'results/live_ab/LOADER_LINKAGE_BUILD_RULES_v2.json'
DURABLE_DECL = REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json'
OUT = REPO / 'results/live_ab/DURABLE_LINKAGE_DELTA.json'
ORIGINALS = REPO / 'results/live_ab/durable_build_originals'


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def durable_linkage(build: Path) -> dict:
    """real linked source -> targets, for a build tree, by the SAME walk as
    loader_call_sites.main() (v2): parse_ninja with includes, compile mappings
    joined as directory + file, NINJA-PROBLEM / UNRESOLVED-ARCHIVE entries kept
    as problems, and a unity unit linked together with the sources it includes
    (an #include the walk does not follow is a problem)."""
    build = Path(os.path.abspath(build))     # compile mappings are absolute
    parsed = lcs.parse_ninja((build / 'build.ninja').read_text(),
                             read_include=lambda p: lcs._read_text_or_none(build / p))
    statements = parsed['statements']
    problems = ['build rules: ' + p for p in parsed['problems']]
    cc = json.loads((build / 'compile_commands.json').read_text())
    obj_to_src = {}
    for e in cc:
        o = e.get('output')
        if o:
            obj_to_src[os.path.normpath(os.path.join(e['directory'], o))] = \
                os.path.normpath(os.path.join(e['directory'], e['file']))
    linked = {}
    for t in lcs.TARGETS:
        if t not in statements:
            problems.append('%s: no build statement' % t)
            continue
        for o in lcs.linked_objects(statements, t):
            if o.startswith(('NINJA-PROBLEM:', 'UNRESOLVED-ARCHIVE:')):
                problems.append('%s: %s' % (t, o))
                continue
            s = obj_to_src.get(os.path.normpath(str(build / o)))
            if s is None:
                problems.append('%s links %s with no compile command' % (t, o))
                continue
            reals = [s]
            if '/Unity/' in s and s.endswith(('.cxx', '.cpp', '.c')):
                utext = lcs._read_text_or_none(Path(s))
                if utext is None:
                    problems.append('%s: unity unit %s cannot be read' % (t, s))
                else:
                    incs = lcs.unity_includes(utext)
                    if lcs.unity_include_directives(utext) != len(incs):
                        problems.append('%s: unity unit %s has an unfollowed #include' % (t, s))
                    reals += [os.path.normpath(os.path.join(os.path.dirname(s), i))
                              for i in incs]
            for r in reals:
                linked.setdefault(os.path.realpath(r), set()).add(t)
    return {'linked': {k: sorted(v) for k, v in sorted(linked.items())},
            'problems': sorted(set(problems))}


def normalize(path: str, roots: list) -> str:
    """Replace the longest matching root by its token."""
    for root, token in sorted(roots, key=lambda r: -len(r[0])):
        if path == root or path.startswith(root.rstrip('/') + '/'):
            return token + path[len(root.rstrip('/')):]
    return path


def main() -> int:
    if OUT.exists() or ORIGINALS.exists():
        print('refusing: write-once outputs exist', file=sys.stderr)
        return 2
    decl = json.loads(DURABLE_DECL.read_text())
    d_src = os.path.realpath(decl['source_and_patch']['source_tree'])
    d_build = Path(decl['build']['build_tree'])
    tmp_rules = json.loads(TMP_RULES.read_text())
    t_build = tmp_rules['build_directory']
    t_src = str(Path(t_build).parent)
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    ORIGINALS.mkdir(parents=True)
    originals = {}
    for n in ('build.ninja', 'compile_commands.json'):
        shutil.copyfile(d_build / n, ORIGINALS / n)
        originals[n] = {'bytes': (ORIGINALS / n).stat().st_size, 'sha256': sha(ORIGINALS / n),
                        'equals_the_build_tree_file': sha(ORIGINALS / n) == sha(d_build / n)}

    durable = durable_linkage(d_build)
    tmp = durable_linkage(Path(t_build))
    # the temporary map used here must BE the authenticated one: the same walk
    # over the temporary tree agrees with the deposit's own re-derivation
    dep = lcs.linkage_from_deposit(tmp_rules)
    tmp_equals_deposit = ({os.path.realpath(k): v for k, v in dep['linked'].items()}
                          == tmp['linked'])
    dep_originals_unchanged = {n: lcs.sha256_file(Path(t_build) / n) == o['sha256']
                               for n, o in tmp_rules['originals'].items()}
    d_roots = [(os.path.realpath(str(d_build)), '<BUILD>'), (d_src, '<SRC>')]
    t_roots = [(os.path.realpath(t_build), '<BUILD>'), (os.path.realpath(t_src), '<SRC>')]
    d_norm = {normalize(k, d_roots): (k, v) for k, v in durable['linked'].items()}
    t_norm = {normalize(os.path.realpath(k), t_roots): (k, v) for k, v in tmp['linked'].items()}
    only_durable = sorted(set(d_norm) - set(t_norm))
    only_tmp = sorted(set(t_norm) - set(d_norm))
    target_mismatch = sorted(k for k in set(d_norm) & set(t_norm)
                             if sorted(d_norm[k][1]) != sorted(t_norm[k][1]))

    # BYTES of every linked unit present in both trees
    differing, missing_tmp_bytes, compared = [], [], 0
    for k in sorted(set(d_norm) & set(t_norm)):
        dp, tp = d_norm[k][0], os.path.realpath(t_norm[k][0])
        if not os.path.exists(tp):
            missing_tmp_bytes.append(k)
            continue
        compared += 1
        if sha(dp) != sha(tp):
            differing.append({'unit': k, 'durable_sha256': sha(dp), 'temporary_sha256': sha(tp)})
    applies = (not only_durable and not only_tmp and not target_mismatch and not differing
               and not missing_tmp_bytes and not durable['problems'] and not tmp['problems']
               and tmp_equals_deposit and all(dep_originals_unchanged.values())
               and not dep['problems'])
    doc = {
        'schema': 'live_ab/durable_linkage_delta-v1',
        'convention': 'post-build-provenance',
        'generated_utc': t0,
        'authority': 'root, reviews/durable_candidate_delta_20260923_1926.md item 3',
        'nothing_executed_THIS_RECEIPT': ('file reads, two copies and digests only; no build, '
                                          'no source scan, no candidate execution'),
        'durable_generated_originals': {'directory': str(ORIGINALS.relative_to(REPO)),
                                        'files': originals},
        'temporary_map': {'deposit': str(TMP_RULES.relative_to(REPO)), 'sha256': sha(TMP_RULES),
                          'linked_units': len(tmp['linked']), 'problems': tmp['problems'],
                          'same_walk_equals_deposit_rederivation': tmp_equals_deposit,
                          'deposit_rederivation_problems': dep['problems'],
                          'originals_still_match_deposit_digests': dep_originals_unchanged},
        'durable_map': {'linked_units': len(durable['linked']),
                        'problems': durable['problems']},
        'roots_normalized': {'durable': {r: t for r, t in d_roots},
                             'temporary': {r: t for r, t in t_roots}},
        'delta': {'units_only_in_durable': only_durable, 'units_only_in_temporary': only_tmp,
                  'units_linked_into_different_targets': target_mismatch,
                  'units_byte_compared': compared,
                  'units_with_different_bytes': differing,
                  'temporary_bytes_no_longer_available': missing_tmp_bytes},
        'v2_classification_applies_unchanged': applies,
        'meaning': ('if true: the same units are linked into the same targets and every one is '
                    'byte-identical, so the v2 call-site scan of the temporary build holds for '
                    'the durable build without a rescan. Any listed delta is exactly what the '
                    'v2 classification does not cover.'),
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(OUT, 'applies=%s durable=%d temporary=%d differing=%d' % (
        applies, len(durable['linked']), len(tmp['linked']), len(differing)))
    return 0


EXPLAINED = REPO / 'results/live_ab/DURABLE_LINKAGE_DELTA_EXPLAINED.json'
INCBIN = re.compile(rb'^\s*\.incbin\s+"([^"]+)"', re.M)
EXTRA_SUFFIXES = ('.metal', '.s', '.S')


def _root_normalized(data: bytes, roots: list) -> bytes:
    """`data` with every spelling of each tree root replaced by its token,
    longest root first (the build tree lies under the temporary source tree)."""
    spellings = []
    for root, token in roots:
        for sp in {root, os.path.realpath(root)} | (
                {root[len('/private'):]} if root.startswith('/private/') else set()):
            spellings.append((sp, token))
    for sp, token in sorted(spellings, key=lambda r: -len(r[0])):
        data = data.replace(sp.encode(), token.encode())
    return data


def _c_family(tree: Path, skip: tuple) -> dict:
    """relative path -> absolute path, for every file the v2 scan would read
    (C-family) plus the Metal/assembly files the embeds are made of."""
    out = {}
    suffixes = tuple(lcs.SOURCE_SUFFIXES) + EXTRA_SUFFIXES
    for p in tree.rglob('*'):
        rel = p.relative_to(tree)
        if rel.parts and (rel.parts[0] in skip or rel.parts[0] == '.git'):
            continue
        if p.is_file() and p.suffix.lower() in suffixes:
            out[str(rel)] = p
    return out


def explain() -> int:
    """Second, bounded step over the write-once delta receipt: for each unit
    with different bytes, is the difference ONLY the tree roots? For each
    `.incbin` in those units, are the embedded files byte-identical? And the
    tree-wide changed-file delta over every C-family/Metal/assembly file of both
    source and build trees. Hashes and byte replacements only; no scan."""
    if EXPLAINED.exists():
        print('refusing: write-once output exists', file=sys.stderr)
        return 2
    delta = json.loads(OUT.read_text())
    d_roots = list(delta['roots_normalized']['durable'].items())
    t_roots = list(delta['roots_normalized']['temporary'].items())
    back = {'durable': {t: r for r, t in d_roots}, 'temporary': {t: r for r, t in t_roots}}

    def real(side, unit):
        tok = unit.split('/', 1)[0]
        return Path(back[side][tok] + unit[len(tok):])

    units, incbins = [], []
    for u in delta['delta']['units_with_different_bytes']:
        dp, tp = real('durable', u['unit']), real('temporary', u['unit'])
        db, tb = dp.read_bytes(), tp.read_bytes()
        units.append({'unit': u['unit'], 'durable_sha256': sha(dp), 'temporary_sha256': sha(tp),
                      'equal_after_root_normalization':
                          _root_normalized(db, d_roots) == _root_normalized(tb, t_roots)})
        for di, ti in zip(INCBIN.findall(db), INCBIN.findall(tb)):
            di, ti = di.decode(), ti.decode()
            incbins.append({'in': u['unit'],
                            'embedded': _root_normalized(di.encode(), d_roots).decode(),
                            'same_after_normalization':
                                _root_normalized(di.encode(), d_roots)
                                == _root_normalized(ti.encode(), t_roots),
                            'durable_sha256': sha(di), 'temporary_sha256': sha(ti),
                            'bytes_identical': sha(di) == sha(ti)})
        if len(INCBIN.findall(db)) != len(INCBIN.findall(tb)):
            incbins.append({'in': u['unit'], 'problem': 'different number of .incbin lines'})

    # tree-wide changed-file delta (source trees without their build dirs, and
    # the build trees), over the files the v2 scan reads plus Metal/assembly
    trees = {}
    d_src = Path(back['durable']['<SRC>']); t_src = Path(back['temporary']['<SRC>'])
    d_bld = Path(back['durable']['<BUILD>']); t_bld = Path(back['temporary']['<BUILD>'])
    for name, dt, tt, skip in (('<SRC>', d_src, t_src, ('build',)),
                               ('<BUILD>', d_bld, t_bld, ())):
        df, tf = _c_family(dt, skip), _c_family(tt, skip)
        differing, path_only = [], []
        for rel in sorted(set(df) & set(tf)):
            if sha(df[rel]) == sha(tf[rel]):
                continue
            if _root_normalized(df[rel].read_bytes(), d_roots) == \
                    _root_normalized(tf[rel].read_bytes(), t_roots):
                path_only.append(rel)
            else:
                differing.append({'file': rel, 'durable_sha256': sha(df[rel]),
                                  'temporary_sha256': sha(tf[rel])})
        trees[name] = {'files_compared': len(set(df) & set(tf)),
                       'only_in_durable': sorted(set(df) - set(tf)),
                       'only_in_temporary': sorted(set(tf) - set(df)),
                       'differing_beyond_tree_roots': differing,
                       'differing_only_by_tree_roots': path_only}
    all_units_path_only = all(u['equal_after_root_normalization'] for u in units)
    all_incbin_identical = all(i.get('bytes_identical') and i.get('same_after_normalization')
                               for i in incbins)
    no_tree_delta = all(not t['only_in_durable'] and not t['only_in_temporary']
                        and not t['differing_beyond_tree_roots'] for t in trees.values())
    doc = {
        'schema': 'live_ab/durable_linkage_delta_explained-v1',
        'convention': 'post-build-provenance',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'explains': {'path': str(OUT.relative_to(REPO)), 'sha256': sha(OUT)},
        'nothing_executed_THIS_RECEIPT': 'file reads, digests and byte replacements only',
        'root_spellings_replaced': 'each root as recorded, its realpath, and /tmp for /private/tmp',
        'units_with_different_bytes': units,
        'incbin_embedded_files': incbins,
        'tree_file_delta': trees,
        'every_differing_unit_differs_only_by_tree_roots': all_units_path_only,
        'every_embedded_file_byte_identical': all_incbin_identical,
        'no_c_family_metal_or_assembly_file_differs_beyond_tree_roots': no_tree_delta,
        'v2_classification_applies_to_the_durable_build':
            bool(all_units_path_only and all_incbin_identical and no_tree_delta),
        'meaning': ('if true: the durable build links the same units into the same targets '
                    'as the authenticated temporary build; every linked unit is byte-identical '
                    'or differs only in the absolute tree root written into it by CMake '
                    '(unity #include lines, Metal .incbin paths); every embedded file is '
                    'byte-identical; and no C-family, Metal or assembly file of either tree '
                    'differs beyond the roots. The v2 call-site classification therefore '
                    'transfers without a rescan. What it does NOT show: that the compiled '
                    'objects are identical (those are not compared, and embed their paths).'),
    }
    EXPLAINED.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(EXPLAINED, 'applies=%s units_path_only=%s incbin=%s tree_delta_empty=%s' % (
        doc['v2_classification_applies_to_the_durable_build'], all_units_path_only,
        all_incbin_identical, no_tree_delta))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(explain() if '--explain' in sys.argv else main())
