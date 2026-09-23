"""Independent verification of the 2026-09-23 engineering-cap amendment.

The amendment tool checked its postconditions in text mode. Two gaps were named
by an independent critic of the plan, and this closes them:

  1. BYTES, NOT TEXT. `tests_lab_e2e.ConfigTests.test_config_is_appendix_b_verbatim`
     reads the three files with `Path.read_text`, which normalizes newlines, so it
     compares text, not bytes -- while root asked for "byte-for-byte". This
     compares the three blocks as raw bytes and counts CR bytes.
  2. A NEGATIVE CONTROL. Root's own practice (reviews/config_sync_review_
     20260923_0541.md): run the verbatim comparison with the PRE-amendment
     documents substituted and expect it to fail. A check that also passes on
     the unsynchronized documents would prove nothing.

It also re-derives, from git, that deleting the added lines reproduces the prior
block and that the statistical rule-block digest is unchanged.

READ-ONLY on the repository: it reads the working tree and `git show` blobs and
writes one receipt. Nothing is executed beyond that.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

AMENDMENT_COMMIT = '0e05d96'
DOCS = {'config': 'experiments/live_ab/config.json',
        'architecture': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
        'protocol': 'experiments/live_ab/design/protocol_FINAL.md'}
MARKERS = {'architecture': b'### 6.1 Full key list', 'protocol': b'## Appendix B.'}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


def block_bytes(raw: bytes, marker: bytes) -> bytes:
    """tests_lab_e2e.py:243-247's extraction, on BYTES."""
    s = raw.index(marker)
    f = raw.index(b'```json', s) + len(b'```json')
    e = raw.index(b'```', f)
    return raw[f:e].lstrip(b'\n')


def e2e_text_check(cfg: bytes, arch: bytes, proto: bytes) -> bool:
    """The e2e test's comparison as it is written: text mode, newline-normalized."""
    def text_block(raw: bytes, marker: str) -> str:
        t = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
        s = t.index(marker)
        f = t.index('```json', s) + len('```json')
        e = t.index('```', f)
        return t[f:e].lstrip('\n')
    a = text_block(arch, '### 6.1 Full key list')
    p = text_block(proto, '## Appendix B.')
    c = cfg.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    return a == p == c


def main() -> int:
    out_path = REPO / 'results' / 'live_ab' / ('CONFIG_AMENDMENT_VERIFICATION_%s.json'
                                               % time.strftime('%Y%m%d_%H%M', time.gmtime()))
    if out_path.exists():
        print('refusing: %s exists (write-once)' % out_path, file=sys.stderr)
        return 2
    now = {k: (REPO / p).read_bytes() for k, p in DOCS.items()}
    after = {k: blob(AMENDMENT_COMMIT, p) for k, p in DOCS.items()}
    before = {k: blob(AMENDMENT_COMMIT + '~1', p) for k, p in DOCS.items()}

    raw_blocks = {'config': now['config'],
                  'architecture': block_bytes(now['architecture'], MARKERS['architecture']),
                  'protocol': block_bytes(now['protocol'], MARKERS['protocol'])}
    receipt = json.loads((REPO / 'results/live_ab/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json')
                         .read_text())
    inserted = receipt['inserted_text'].encode('utf-8')
    doc = {
        'schema': 'live_ab/config_amendment_verification-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'amendment_commit': AMENDMENT_COMMIT,
        'working_tree_equals_amendment_commit': now == after,
        'raw_bytes': {
            'cr_bytes': {k: v.count(b'\r') for k, v in now.items()},
            'three_blocks_byte_identical': len(set(raw_blocks.values())) == 1,
            'block_sha256': sha(raw_blocks['config']),
            'block_bytes': len(raw_blocks['config']),
        },
        'additivity_from_git': {
            'prior_block_sha256': sha(before['config']),
            'deleting_the_inserted_text_reproduces_the_prior_bytes': {
                k: now[k].replace(inserted, b'', 1) == before[k] for k in DOCS},
            'inserted_text_occurs_once_per_document': {k: now[k].count(inserted) for k in DOCS},
        },
        'rule_block_sha256': {
            'before': lab_common.rule_block_sha256(json.loads(before['config'])),
            'after': lab_common.rule_block_sha256(json.loads(now['config'])),
        },
        'negative_control': {
            'what': ('the e2e verbatim comparison, exactly as written (text mode), run '
                     'three ways: all three amended documents (must pass); the amended '
                     'config with the PRE-amendment ARCHITECTURE and protocol (must '
                     'fail); the amended config and ARCHITECTURE with the PRE-amendment '
                     'protocol (must fail)'),
            'amended_all_three_passes': e2e_text_check(now['config'], now['architecture'],
                                                       now['protocol']),
            'old_documents_fail': not e2e_text_check(now['config'], before['architecture'],
                                                     before['protocol']),
            'old_protocol_only_fails': not e2e_text_check(now['config'], now['architecture'],
                                                          before['protocol']),
        },
        'nothing_executed': 'git show and file reads only',
    }
    ok = (doc['working_tree_equals_amendment_commit']
          and doc['raw_bytes']['three_blocks_byte_identical']
          and not any(doc['raw_bytes']['cr_bytes'].values())
          and all(doc['additivity_from_git']['deleting_the_inserted_text_reproduces_the_prior_bytes'].values())
          and doc['rule_block_sha256']['before'] == doc['rule_block_sha256']['after']
          and all(v for k, v in doc['negative_control'].items() if k != 'what'))
    doc['all_verified'] = ok
    out_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(out_path, 'all_verified=%s' % ok)
    return 0 if ok else 1


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
