"""The narrow engineering-cap configuration amendment root authorized, 2026-09-23 16:30.

Root (reviews/acquisition_preparation_disposition_20260923_1630.md, decision 3):

    "Authorize a narrow pre-outcome engineering-cap configuration amendment. Add a
     scoped engineering-acquisition section with the six declared fields below,
     keeping the trial execution/sampling rules separate. Preserve the prior
     config, plan and receipts by exact revision and an additive amendment record.
     Synchronize `config.json`, `ARCHITECTURE_FINAL.md` section 6.1 and
     `protocol_FINAL.md` Appendix B byte-for-byte; refresh dependent hashes and
     add protocol-successor provenance where required without overwriting
     original CPU pins/results. Verify the statistical rule-block digest remains
     unchanged. No CPU simulation rerun is required by a configuration-only
     amendment."

WHAT THIS DOES, AND ONLY THIS
  1. Checks the preconditions: the three verbatim blocks are identical and are
     the reviewed 13,641-byte block; `cells.json` round-trips byte-exactly.
  2. Inserts the SAME three lines -- a new top-level `engineering_acquisition`
     section with the six literal values -- immediately before the
     `hardware_allowlist` line of each block. Pure line additions: no existing
     line changes. The file is never round-tripped through `json.dumps` (that
     broke the contract twice: 19e93cc, a95ba08).
  3. Verifies the postconditions: the three blocks are identical again; the
     flattened key diff is exactly the six added keys; deleting the added lines
     reproduces the prior block byte for byte; the statistical rule-block digest,
     the receipt mask, the winstats pin and the environment lock are unchanged.
  4. Records the protocol successor ADDITIVELY in `cells.json`: the original pin
     is untouched, the current successor moves WHOLE into `prior_successors`
     with its verified changing commit, and the new successor names the new
     protocol digest.
  5. Writes one write-once amendment receipt.

It refuses, changing nothing, if any precondition fails. It is NOT a freeze, NOT
trial or launch approval, and runs no simulation, model or server.
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

CONFIG = LAB / 'config.json'
ARCH = LAB / 'design' / 'ARCHITECTURE_FINAL.md'
PROTO = LAB / 'design' / 'protocol_FINAL.md'
CELLS = REPO / 'experiments' / 'live_ab_validation' / 'cells.json'

PRIOR_BLOCK_SHA256 = '05255df3b0d12bb6f5571616378a1366c67c6eb8b913def907c6a5d901e1731c'
PRIOR_BLOCK_BYTES = 13641
PRIOR_RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
PRIOR_SUCCESSOR = 'f75de3235ae0431b727cf7c24b09927204a1da8c5424e14ea428dbfea256f48b'
PRIOR_SUCCESSOR_COMMIT = '855a40636d4a84d64edee91052652eac6999a1a1'

#: The six fields, as literals -- root's table, not the supervisor's constants,
#: so that agreement between config and code is between two statements.
SECTION = {'wall_seconds_total': 600, 'cleanup_reserve_seconds': 90,
           'dispatch_cutoff_seconds': 510, 'diagnostic_byte_budget': 8388608,
           'seconds_per_request': 120, 'total_generated_tokens': 2048}
INSERTED = (
    '  "engineering_acquisition": {"wall_seconds_total": 600, '
    '"cleanup_reserve_seconds": 90,\n'
    '                              "dispatch_cutoff_seconds": 510, '
    '"diagnostic_byte_budget": 8388608,\n'
    '                              "seconds_per_request": 120, '
    '"total_generated_tokens": 2048},\n')
ANCHOR = '  "hardware_allowlist": ["arm64-darwin"],'


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def block_of(text: str, marker: str) -> str:
    """The extraction tests_lab_e2e.py:243-247 performs, reproduced exactly."""
    start = text.index(marker)
    fence = text.index('```json', start) + len('```json')
    end = text.index('```', fence)
    return text[fence:end].lstrip('\n')


def flatten(d, prefix=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, prefix + k + '.'))
    else:
        out[prefix[:-1]] = d
    return out


def insert_once(text: str) -> str:
    if text.count(ANCHOR) != 1:
        raise SystemExit('refusing: the anchor line occurs %d times' % text.count(ANCHOR))
    return text.replace(ANCHOR, INSERTED + ANCHOR, 1)


def git(*args) -> str:
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> int:
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / ('CONFIG_AMENDMENT_RECEIPT_%s.json' % stamp)
    if receipt_path.exists():
        print('refusing: %s exists (write-once)' % receipt_path, file=sys.stderr)
        return 2

    # -- 1. preconditions -----------------------------------------------------
    cfg_text = CONFIG.read_text(encoding='utf-8')
    arch_text = ARCH.read_text(encoding='utf-8')
    proto_text = PROTO.read_text(encoding='utf-8')
    blocks = [cfg_text, block_of(arch_text, '### 6.1 Full key list'),
              block_of(proto_text, '## Appendix B.')]
    pre = {
        'three_blocks_identical': len(set(blocks)) == 1,
        'block_sha256': sha(cfg_text.encode()),
        'block_bytes': len(cfg_text.encode()),
        'is_the_reviewed_block': (sha(cfg_text.encode()) == PRIOR_BLOCK_SHA256
                                  and len(cfg_text.encode()) == PRIOR_BLOCK_BYTES),
        'protocol_sha256': sha(PROTO.read_bytes()),
        'architecture_sha256': sha(ARCH.read_bytes()),
        'cells_sha256': sha(CELLS.read_bytes()),
        'cells_round_trips': (json.dumps(json.loads(CELLS.read_text()), indent=1) + '\n'
                              == CELLS.read_text()),
        'head': git('rev-parse', 'HEAD'),
    }
    if not (pre['three_blocks_identical'] and pre['is_the_reviewed_block']
            and pre['cells_round_trips'] and pre['protocol_sha256'] == PRIOR_SUCCESSOR):
        print('refusing: a precondition failed: %s' % json.dumps(pre), file=sys.stderr)
        return 2
    old_cfg = json.loads(cfg_text)
    if 'engineering_acquisition' in old_cfg:
        print('refusing: the section already exists', file=sys.stderr)
        return 2

    # -- 2. insert, identically, three times ---------------------------------
    new_cfg_text = insert_once(cfg_text)
    new_arch = insert_once(arch_text)
    new_proto = insert_once(proto_text)

    # -- 3. postconditions, computed BEFORE anything is written ---------------
    new_blocks = [new_cfg_text, block_of(new_arch, '### 6.1 Full key list'),
                  block_of(new_proto, '## Appendix B.')]
    new_cfg = json.loads(new_cfg_text)
    fo, fn = flatten(old_cfg), flatten(new_cfg)
    added = sorted(set(fn) - set(fo))
    removed = sorted(set(fo) - set(fn))
    changed = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
    post = {
        'three_blocks_identical': len(set(new_blocks)) == 1,
        'block_sha256': sha(new_cfg_text.encode()),
        'block_bytes': len(new_cfg_text.encode()),
        'added_keys': added, 'removed_keys': removed, 'changed_keys': changed,
        'exactly_the_six_fields_added': added == sorted('engineering_acquisition.' + k
                                                        for k in SECTION),
        'section_equals_root_table': new_cfg['engineering_acquisition'] == SECTION,
        'dispatch_cutoff_is_wall_minus_reserve': (
            SECTION['dispatch_cutoff_seconds']
            == SECTION['wall_seconds_total'] - SECTION['cleanup_reserve_seconds']),
        'deleting_the_added_lines_reproduces_the_prior_block': (
            sha(new_cfg_text.replace(INSERTED, '', 1).encode()) == PRIOR_BLOCK_SHA256),
        'rule_block_sha256_before': lab_common.rule_block_sha256(old_cfg),
        'rule_block_sha256_after': lab_common.rule_block_sha256(new_cfg),
        'receipt_mask_sha256_unchanged': (
            lab_common.sha256_canonical(old_cfg['receipt']['mask'])
            == lab_common.sha256_canonical(new_cfg['receipt']['mask'])),
        'winstats_pin_unchanged': (old_cfg['monitor']['winstats_sha256']
                                   == new_cfg['monitor']['winstats_sha256']),
        'environment_lock_unchanged': (old_cfg['environment_lock_sha256']
                                       == new_cfg['environment_lock_sha256']),
        'sampling_unchanged': old_cfg['sampling'] == new_cfg['sampling'],
        'execution_unchanged': old_cfg['execution'] == new_cfg['execution'],
        'protocol_sha256': sha(new_proto.encode()),
        'architecture_sha256': sha(new_arch.encode()),
        'protocol_change_is_inside_appendix_b_only': (
            new_proto.replace(INSERTED, '', 1) == proto_text
            and new_proto.index(INSERTED) > new_proto.index('## Appendix B.')),
    }
    ok = (post['three_blocks_identical'] and post['exactly_the_six_fields_added']
          and not removed and not changed and post['section_equals_root_table']
          and post['dispatch_cutoff_is_wall_minus_reserve']
          and post['deleting_the_added_lines_reproduces_the_prior_block']
          and post['rule_block_sha256_before'] == PRIOR_RULE_BLOCK
          and post['rule_block_sha256_after'] == PRIOR_RULE_BLOCK
          and post['receipt_mask_sha256_unchanged'] and post['winstats_pin_unchanged']
          and post['environment_lock_unchanged'] and post['sampling_unchanged']
          and post['execution_unchanged']
          and post['protocol_change_is_inside_appendix_b_only'])
    if not ok:
        print('refusing: a postcondition failed; NOTHING was written: %s'
              % json.dumps(post), file=sys.stderr)
        return 2

    # -- 4. the successor, additively ----------------------------------------
    verified_commit_hash = sha(subprocess.run(
        ['git', '-C', str(REPO), 'show',
         '%s:experiments/live_ab/design/protocol_FINAL.md' % PRIOR_SUCCESSOR_COMMIT],
        capture_output=True, check=True).stdout)
    if verified_commit_hash != PRIOR_SUCCESSOR:
        print('refusing: %s does not carry the prior successor' % PRIOR_SUCCESSOR_COMMIT,
              file=sys.stderr)
        return 2
    cells = json.loads(CELLS.read_text())
    va = cells['provenance']['vocabulary_alignment']
    old_sb = va['superseded_by']
    assert va['sha256'] == ORIGINAL_PIN and old_sb['sha256'] == PRIOR_SUCCESSOR
    demoted = {k: v for k, v in old_sb.items()
               if k not in ('prior_successors', 'changing_commit_note',
                            'correction_to_the_owner_report')}
    demoted['changing_commit_of_this_successor'] = PRIOR_SUCCESSOR_COMMIT
    demoted['changing_commit_note'] = (
        'Resolved AFTER the fact, when the engineering-cap amendment landed on top of '
        'it: `git show %s:experiments/live_ab/design/protocol_FINAL.md` hashes to this '
        'successor.' % PRIOR_SUCCESSOR_COMMIT[:7])
    new_sb = {
        'sha256': post['protocol_sha256'],
        'supersedes': ORIGINAL_PIN,
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'reason': (
            'Appendix B ONLY: the configuration block gained the scoped '
            '"engineering_acquisition" section root authorized in '
            'reviews/acquisition_preparation_disposition_20260923_1630.md decision 3 '
            '-- six engineering-acquisition caps (wall_seconds_total 600, '
            'cleanup_reserve_seconds 90, dispatch_cutoff_seconds 510, '
            'diagnostic_byte_budget 8388608, seconds_per_request 120, '
            'total_generated_tokens 2048) -- synchronising Appendix B with config.json '
            'under the three-way verbatim contract. It changes NO CPU cell, parameter, '
            'seed, horizon, estimator, outcome, decision rule, trial sampling or '
            'execution rule, or any of the vocabulary sections 1, 3 and 11 this pin '
            'reads. Verified: the flattened key diff against the prior config is six '
            'added keys, none changed or removed, and the statistical rule-block digest '
            'is unchanged.'),
        'ruling': (
            'Root ruling 2026-09-23 16:30 (reviews/acquisition_preparation_disposition_'
            '20260923_1630.md, decision 3): "Authorize a narrow pre-outcome '
            'engineering-cap configuration amendment ... Synchronize config.json, '
            'ARCHITECTURE_FINAL.md section 6.1 and protocol_FINAL.md Appendix B '
            'byte-for-byte; refresh dependent hashes and add protocol-successor '
            'provenance where required without overwriting original CPU pins/results." '
            'The pin amendment follows the standing root ruling of 2026-09-22 04:27: '
            '"preserve the original pin; record an explicit post-freeze provenance '
            'amendment ... Do not replace the original sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial or launch approval, and not a CPU rerun. The caps '
            'bound one engineering acquisition; they are not trial sampling rules '
            '(sampling.max_tokens 1024 and every execution rule are unchanged). The 600 s '
            'is a measurement at a declared point, not an end-to-end hard wall-clock '
            'guarantee.'),
        'correction_to_the_owner_report': old_sb['correction_to_the_owner_report'],
        'prior_successors': list(old_sb['prior_successors']) + [demoted],
        'changing_commit_note': (
            'The commit that introduces a successor cannot carry its own hash, so '
            '"changing_commit_of_this_successor" is resolved in a LATER commit. The last '
            'entry above records the one for the 06:40 successor, resolved when this '
            'amendment landed; this newest successor\'s own commit is recorded the same '
            'way when the next one lands.'),
    }
    new_cells = json.loads(CELLS.read_text())
    new_cells['provenance']['vocabulary_alignment']['superseded_by'] = new_sb
    a, b = json.loads(CELLS.read_text()), json.loads(json.dumps(new_cells))
    a['provenance']['vocabulary_alignment'].pop('superseded_by')
    b['provenance']['vocabulary_alignment'].pop('superseded_by')
    if a != b:
        print('refusing: cells.json would change outside superseded_by', file=sys.stderr)
        return 2
    new_cells_text = json.dumps(new_cells, indent=1) + '\n'

    # -- 5. write, then the receipt ------------------------------------------
    CONFIG.write_text(new_cfg_text, encoding='utf-8')
    ARCH.write_text(new_arch, encoding='utf-8')
    PROTO.write_text(new_proto, encoding='utf-8')
    CELLS.write_text(new_cells_text, encoding='utf-8')
    written = {
        'config_sha256': sha(CONFIG.read_bytes()), 'config_bytes': CONFIG.stat().st_size,
        'architecture_sha256': sha(ARCH.read_bytes()), 'protocol_sha256': sha(PROTO.read_bytes()),
        'cells_sha256': sha(CELLS.read_bytes()),
        'harness_file_sha256_config': lab_common.harness_file_hashes().get('config.json'),
        'harness_files': len(lab_common.harness_file_hashes()),
    }
    doc = {
        'schema': 'live_ab.config_amendment_receipt.1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root, reviews/acquisition_preparation_disposition_20260923_1630.md '
                      'decision 3 (quoted in this tool\'s docstring)'),
        'documents_amended_in_lockstep': [str(p.relative_to(REPO)) for p in (CONFIG, ARCH, PROTO)],
        'inserted_text': INSERTED,
        'field_by_field': {k: {'was': 'absent', 'now': v,
                               'source': 'root 16:30 disposition table',
                               'derivation': ('600 - 90' if k == 'dispatch_cutoff_seconds'
                                              else 'literal')} for k, v in SECTION.items()},
        'placement': ('a NEW top-level key, not under sampling (sent on the wire by '
                      'lab_client) nor execution (execution.auto_abort is in the rule '
                      'block)'),
        'precondition_checked': pre,
        'postcondition_checked': post,
        'written': written,
        'successor_provenance': {
            'original_pin_untouched': ORIGINAL_PIN,
            'new_successor': post['protocol_sha256'],
            'demoted_successor': PRIOR_SUCCESSOR,
            'demoted_successor_commit_verified': PRIOR_SUCCESSOR_COMMIT,
            'prior_successors_now': len(new_sb['prior_successors'])},
        'prior_versions_retained': {
            'config_block_sha256': PRIOR_BLOCK_SHA256, 'config_block_bytes': PRIOR_BLOCK_BYTES,
            'revision': pre['head'],
            'note': 'recoverable byte-exactly by `git show <revision>:<path>`, and by '
                    'deleting inserted_text from each document'},
        'dependent_hashes_that_move': {
            'config_sha256 / harness_file_sha256[config.json]': 'moves, as any config byte '
                'change must; no freeze exists yet, so nothing frozen is invalidated',
            'protocol_sha256': 'moves; recorded as the new successor above'},
        'dependent_hashes_that_do_not_move': ['rule_block_sha256', 'receipt_mask_sha256',
                                             'monitor.winstats_sha256',
                                             'environment_lock_sha256'],
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server or build; text edits and '
                             'digests only'),
        'scope': ('the section is declarative configuration. Its agreement with the '
                  'supervisor\'s enforced constants is a separate code check, delivered '
                  'with the launch wiring.'),
    }
    receipt_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt_path)
    print(json.dumps({'post_ok': ok, 'new_block_bytes': post['block_bytes'],
                      'rule_block': post['rule_block_sha256_after'][:12],
                      'new_protocol': post['protocol_sha256'][:12]}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
