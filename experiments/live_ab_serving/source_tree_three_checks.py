"""The three recorded checks of protocol §2.2 item 1 (patch-state amendment),
on the durable candidate's source checkout.

Root, 2026-09-23 20:03 (reviews/patch_state_and_durable_linkage_delta_20260923_2003.md):
the amendment "does not establish the owner-host checkout actually satisfies
the new three checks"; the bundle is to carry the "source-tree three-check
receipt". The amendment text (experiments/live_ab/design/protocol_FINAL.md,
§2.2 item 1) names them:
  1. `HEAD` is 4fea119de30f6a923992780f6fd5ccb0bee5d47d;
  2. `git status --porcelain` lists exactly the two files the patch modifies;
  3. the working tree equals `HEAD` with the patch applied, compared as git
     trees built in temporary indexes with a temporary object directory.
Check 3 is the supervisor's own `run_smoke.verify_source_binding`, the one a
launch runs before `Popen`. The files the patch modifies are read from the
patch itself, not typed here.

Read-only on the checkout: `rev-parse`, `status` with --no-optional-locks (no
index refresh is written), and check 3's temporary indexes and object
directory. One write-once receipt. Nothing is built or executed.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import run_smoke as rs                                         # noqa: E402

PINNED_HEAD = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'
PATCH_REL = 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
PATCH_SHA256 = '88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184'
DECLARATION = 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json'
SNAPSHOT = 'results/live_ab/DURABLE_BUILD_CONFIG_SNAPSHOT.json'


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def patch_files(text: str) -> list:
    """The files a unified diff modifies, from its `+++ b/<path>` lines."""
    return sorted(set(re.findall(r'^\+\+\+ b/(\S+)', text, re.M)))


def porcelain_matches(lines: list, files: list) -> bool:
    """Exactly the patched files, each modified in the working tree only."""
    return sorted(lines) == sorted(' M %s' % f for f in files)


def git(tree: str, *args: str):
    p = subprocess.run(['git', '--no-optional-locks', '-C', tree] + list(args),
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    out = REPO / 'results' / 'live_ab' / ('SOURCE_TREE_THREE_CHECKS_%s.json' % stamp)
    if out.exists():
        print('refusing: %s exists (write-once)' % out, file=sys.stderr)
        return 2
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    decl = json.loads((REPO / DECLARATION).read_text())
    tree = decl['source_and_patch']['source_tree']
    patch_path = REPO / PATCH_REL
    patch_sha = sha(patch_path)
    files = patch_files(patch_path.read_text())

    rc1, head, err1 = git(tree, 'rev-parse', 'HEAD')
    head = head.strip()
    c1 = {'command': 'git rev-parse HEAD', 'returncode': rc1, 'output': head,
          'stderr': err1.strip(), 'expected': PINNED_HEAD,
          'passes': rc1 == 0 and head == PINNED_HEAD}

    rc2, status, err2 = git(tree, 'status', '--porcelain')
    lines = [l for l in status.splitlines() if l]
    c2 = {'command': 'git --no-optional-locks status --porcelain', 'returncode': rc2,
          'output_lines': lines, 'stderr': err2.strip(),
          'expected': ['files the patch modifies, each " M"', files],
          'passes': rc2 == 0 and porcelain_matches(lines, files)}

    binding = {'source_tree': tree, 'head': head, 'patch_path': PATCH_REL,
               'patch_sha256': patch_sha,
               'build_snapshot': {'path': SNAPSHOT, 'sha256': sha(REPO / SNAPSHOT)}}
    sb = rs.verify_source_binding(binding, patch_sha256=patch_sha)
    c3 = {'function': 'experiments/live_ab_serving/run_smoke.py verify_source_binding '
                      '(the check a launch runs before Popen)',
          'tree_equality': sb.get('tree_equality'), 'problems': sb.get('problems'),
          'passes': bool(sb.get('verified'))}

    doc = {
        'schema': 'live_ab/source_tree_three_checks-v1',
        'convention': 'deterministic-path',
        'generated_utc': t0,
        'authority': ('experiments/live_ab/design/protocol_FINAL.md §2.2 item 1 amendment '
                      '(successor 64ace6d3...); root 20:03, reviews/'
                      'patch_state_and_durable_linkage_delta_20260923_2003.md'),
        'nothing_executed_THIS_RECEIPT': ('git rev-parse and status (--no-optional-locks), '
                                          'and check 3\'s temporary indexes; no build'),
        'source_tree': tree,
        'patch': {'path': PATCH_REL, 'sha256': patch_sha,
                  'sha256_is_the_amended_one': patch_sha == PATCH_SHA256,
                  'files_modified': files},
        'check_1_head': c1,
        'check_2_status_porcelain': c2,
        'check_3_tree_equality': c3,
        'all_three_pass': bool(c1['passes'] and c2['passes'] and c3['passes']
                               and patch_sha == PATCH_SHA256),
        'scope': ('the checkout as it is at generated_utc; a launch re-runs check 3 before '
                  'Popen, and any later edit to the checkout makes that refuse'),
    }
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(out, 'all_three_pass=%s' % doc['all_three_pass'])
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
