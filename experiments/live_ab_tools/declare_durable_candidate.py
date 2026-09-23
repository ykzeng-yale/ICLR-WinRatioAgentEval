"""Declare the durably rebuilt candidate, from its rebuild receipt.

Root, 2026-09-23 18:29: after the one model-free durable rebuild, "retain
original logs/receipts, then measure and pin the new source/build/launcher/
library closure". This writes the new candidate DECLARATION in the same shape as
results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json (the /tmp candidate's, which
stays as retrospective evidence), so the existing snapshot and launch-record
tools read it unchanged. Every value comes from the rebuild receipt or is
re-measured here; nothing is typed by hand.

Read-only apart from the one write-once declaration. Nothing is executed.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json'


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print('usage: declare_durable_candidate.py <DURABLE_REBUILD_*.json>', file=sys.stderr)
        return 2
    if OUT.exists():
        print('refusing: %s exists (write-once)' % OUT, file=sys.stderr)
        return 2
    rpath = REPO / argv[0]
    rb = json.loads(rpath.read_text())
    if not rb.get('build_succeeded'):
        print('refusing: the rebuild receipt does not record a successful build',
              file=sys.stderr)
        return 2
    members = rb['members']
    launcher = members['llama-server']
    # re-measured, not copied: the declaration states what is on disk NOW
    problems = []
    for name, m in members.items():
        if sha(m['path']) != m['sha256']:
            problems.append('%s changed since the rebuild receipt' % name)
    if problems:
        print('refusing: %s' % '; '.join(problems), file=sys.stderr)
        return 2
    closure = {
        '/usr/lib/libSystem.B.dylib': {'reference': '/usr/lib/libSystem.B.dylib',
                                       'system_library': True,
                                       'note': 'OS-provided; not pinned by this manifest'},
        '/usr/lib/libc++.1.dylib': {'reference': '/usr/lib/libc++.1.dylib',
                                    'system_library': True,
                                    'note': 'OS-provided; not pinned by this manifest'},
    }
    for name, m in sorted(members.items()):
        if name == 'llama-server':
            continue
        closure[name] = {'reference': '@rpath/%s' % name, 'resolved': m['path'],
                         'canonical': m['canonical'], 'sha256': m['sha256'],
                         'bytes': m['bytes'], 'present': True}
    p22 = rb['protocol_2_2_item_1']
    doc = {
        'schema': 'live_ab/candidate_instrument_manifest-durable-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': 'root, reviews/preparation_wiring_disposition_20260923_1829.md',
        'supersedes_for_prospective_use': {
            'path': 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json',
            'sha256': sha(REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json'),
            'status': 'retained as retrospective engineering evidence; not frozen or '
                      'trialled (root 18:29)'},
        'rebuild_receipt': {'path': argv[0], 'sha256': sha(rpath)},
        'candidate_instrument': {
            'launcher': {'path': launcher['path'], 'sha256': launcher['sha256'],
                         'bytes': launcher['bytes'], 'present': True},
            'library_closure': closure,
            'closure_note': ('the members llama-server links, as the rebuild measured '
                             'them; the transitive v3 closure is derived separately'),
        },
        'source_and_patch': {
            'base_commit': rb['source_state']['pinned_commit'],
            'base_declared': rb['source_state']['head'],
            'source_tree': rb['source_checkout'],
            'declared_state': rb['source_state']['declared_working_tree_state'],
            'git_status_porcelain': rb['source_state']['git_status_porcelain'],
            'patch': {'path': 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch',
                      'sha256': rb['source_state']['patch_sha256'], 'version': 7,
                      'present': True},
        },
        'build': {
            'build_tree': str(Path(rb['llama_build']) / 'build'),
            'llama_build': rb['llama_build'],
            'cmake_options': p22['cmake_options'], 'toolchain': p22['toolchain'],
            'configure_log_sha256': p22['configure_log_sha256'],
            'build_log_sha256': p22['build_log_sha256'],
            'ui': rb['ui'],
        },
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(OUT)
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
