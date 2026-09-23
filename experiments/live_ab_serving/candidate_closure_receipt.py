"""Run the repaired dependency contract on the REAL candidate, read-only.

Derives the closure under a PROPOSED launch context, verifies it straight back,
and runs the refusals that matter on the same real metadata. The context is a
proposal for root's item 4 (wiring), not a frozen launch requirement: nothing
is written into a launch manifest here, and nothing is launched.

Nothing is executed or loaded. `otool` and `nm` read metadata; the search
locations are listed, not opened.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import dependency_closure as dc                                # noqa: E402


def _readers(ctx):
    return dict(metadata=dc.macho_dependency_metadata, exists=os.path.exists,
                read_bytes=lambda p: Path(p).read_bytes(),
                dynamic_loader=dc.imports_dynamic_loader,
                enumerate_dir=dc.discovery_candidates, launch_context=ctx,
                realpath=os.path.realpath)


def main() -> int:
    manifest_path = REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json'
    snapshot_path = REPO / 'results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json'
    receipt = REPO / 'results/live_ab/DEPENDENCY_CONTRACT_REPAIR.json'
    if receipt.exists():
        print('refusing: the receipt exists; this is write-once', file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    snapshot = json.loads(snapshot_path.read_text())
    launcher = manifest['candidate_instrument']['launcher']['path']
    exe_dir = str(Path(launcher).parent)
    compiled_dir = snapshot['compile_definitions']['any_source_defines_GGML_BACKEND_DIR']
    assert compiled_dir is False, 'the snapshot says GGML_BACKEND_DIR is compiled in'

    ctx = {
        'executable_invoked_path': launcher,
        # PROPOSED: the child runs IN the executable directory, so the pinned
        # loader's two default locations are one location, already enumerated.
        'cwd': exe_dir,
        'compiled_backend_dir': None,
        # PROPOSED: the child environment with every GGML_* and DYLD_* removed.
        'environment': {},
        'provenance': {
            'candidate_declaration': str(manifest_path.relative_to(REPO)),
            'build_config_snapshot': str(snapshot_path.relative_to(REPO)),
            'compiled_backend_dir': ('absent: no compile command defines '
                                     'GGML_BACKEND_DIR (build snapshot)'),
            'status': 'PROPOSED for item 4, not frozen into any launch manifest'},
    }
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    derived = dc.derive_closure(launcher, **_readers(ctx))
    verified = dc.verify_closure(derived, **_readers(ctx))

    # The same REAL metadata under contexts that must refuse. Each is a control:
    # if it passed, the pass above would mean nothing.
    controls = {}
    for label, change in (
            ('GGML_BACKEND_PATH set', {'environment': {'GGML_BACKEND_PATH': exe_dir}}),
            ('DYLD_LIBRARY_PATH set', {'environment': {'DYLD_LIBRARY_PATH': exe_dir}}),
            ('operator cwd inherited', {'cwd': str(REPO)}),
            ('no dynamic reader', None)):
        if change is None:
            r = _readers(ctx)
            r['dynamic_loader'] = None
            v = dc.verify_closure(derived, **r)
        else:
            v = dc.verify_closure(derived, **_readers(dict(ctx, **change)))
        controls[label] = {'verified': v['verified'], 'first_problems': v['problems'][:3]}

    manifest_members = sorted(
        d['resolved'] for d in manifest['candidate_instrument']['library_closure'].values()
        if not d.get('system_library'))
    derived_members = sorted(f for f in derived['files'] if f != launcher)
    doc = {
        'schema': 'live_ab/session60_receipt-v1',
        'convention': 'deterministic-path',
        'generated_utc': t0,
        'authority': ('root, reviews/completion_and_backend_disposition_20260923_1441.md, '
                      'helper items 1-3 on 6b83860'),
        'nothing_executed_THIS_RECEIPT': ('otool -h/-l and nm -u read metadata; the '
                                          'search locations were listed, not opened; '
                                          'no candidate execution, model load or build'),
        'what_this_is_not': ('not a frozen launch requirement and not wired: run_smoke '
                             'still uses its inventory-only check (item 4 is next)'),
        'proposed_launch_context': derived.get('launch_context'),
        'derived': {
            'resolved': derived['resolved'],
            'unresolved': derived['unresolved'],
            'edge_count': len(derived['edges']),
            'member_count': derived['member_count'],
            'members': derived_members,
            'members_equal_the_declared_nine': derived_members == manifest_members,
            'system_references': derived['system_references'],
            'duplicate_install_names': derived['duplicate_install_names'],
            'dynamic_loading': derived['dynamic_loading'],
            'shadowed_edges': {k: e['shadowed'] for k, e in derived['edges'].items()
                               if e['shadowed']},
        },
        'verified_straight_back': {k: verified[k] for k in
                                   ('verified', 'problems', 'edges_checked',
                                    'edges_agreeing', 'files_checked')},
        'real_metadata_refusal_controls': controls,
        'closure': derived,
    }
    receipt.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt, 'resolved=%s verified=%s controls_refused=%s' % (
        derived['resolved'], verified['verified'],
        all(not c['verified'] for c in controls.values())))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
