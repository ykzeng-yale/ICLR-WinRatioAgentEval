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

HARDENED FOR REUSE AS A TEMPLATE (2026-09-23, after the independent review)
  The run that produced 0e05d96 is done and is not repeated. Against the amended
  documents this tool refuses: its preconditions pin the PRE-amendment bytes, and
  behind them the "section already exists" refusal is kept. What changed is what a
  copy of it checks. Two findings were confirmed against the run as delivered:

    config 0: "Amendment tool rewrites ARCHITECTURE_FINAL.md in text mode with no
    digest pin and no check that the change stays inside section 6.1, and still
    reports success." Witness: with line 1 of ARCHITECTURE_FINAL.md ending in CRLF,
    main() exited 0 with every postcondition true, but the written file was NOT the
    input plus the three lines (CR bytes went from 1 to 0).

    config 1: "The 'protocol_change_is_inside_appendix_b_only' check only confirms
    the insertion comes after the Appendix B heading, not before Appendix C."
    Witness: with the configuration fence moved under Appendix C, the check
    passed and reported true.

  Now:
    * the three documents are read and written as BYTES, so no newline
      translation can happen in either direction. cells.json is written as bytes
      too;
    * the ARCHITECTURE pre-image is pinned by digest (PRIOR_ARCH_SHA256), as the
      protocol's already was (PRIOR_SUCCESSOR), and no document may carry a CR
      byte, before or after;
    * before anything is written, and for ALL THREE documents, the inserted text
      must occur exactly once, and deleting it must reproduce the pre-image byte
      for byte;
    * the insertion must lie INSIDE the extracted ```json fence, and that fence
      must lie INSIDE its section, for ARCHITECTURE section 6.1 and for protocol
      Appendix B. The section runs from its heading to the next heading of the
      same or a higher level; for Appendix B that is '## Appendix C.'. Both the
      lower and the upper bound are checked. The receipt key
      'protocol_change_is_inside_appendix_b_only' now computes exactly that, and
      'architecture_change_is_inside_6_1_only' is new. The same key in the
      delivered receipt (results/live_ab/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json,
      write-once, not rewritten) was computed by the old check, which had only a
      lower bound. The reviewer confirmed separately that the real insertion lies
      inside Appendix B, and the control case in the witness file reproduces the
      delivered bytes under the new check.
  The witness is experiments/live_ab_tools/tests_engineering_cap_amendment.py.
  It drives main() on scratch copies of the 0e05d96~1 blobs and never touches the
  real documents.

  SCOPE: the pins are the values for THIS amendment. A reuse must re-point every
  pin (block, architecture, protocol, successor commit) at its own reviewed
  pre-images. What carries over is the set of checks, not the constants.
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
#: The reviewed ARCHITECTURE_FINAL.md pre-image (0e05d96~1), pinned like the
#: protocol's. Review finding config 0: it was recorded before, but never compared.
PRIOR_ARCH_SHA256 = '6b36c4a41a23612bc2b8035ac2538977f81f341ed1527fee9c5535578254241c'
ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'

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
INSERTED_BYTES = INSERTED.encode('utf-8')
ANCHOR_BYTES = ANCHOR.encode('utf-8')
DOC_NAMES = ('config', 'architecture', 'protocol')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fence_span(raw: bytes, marker: bytes) -> tuple:
    """[first byte after the opening ```json, the closing ```) of the first fence
    after ``marker``. The extraction tests_lab_e2e.py:243-247 performs, on BYTES."""
    start = raw.index(marker)
    lo = raw.index(b'```json', start) + len(b'```json')
    hi = raw.index(b'```', lo)
    return lo, hi


def block_of(raw: bytes, marker: bytes) -> bytes:
    """The block tests_lab_e2e.py:243-247 compares, extracted from BYTES (that test
    reads text; experiments/live_ab_serving/tests_config_contract.py reads bytes)."""
    lo, hi = fence_span(raw, marker)
    return raw[lo:hi].lstrip(b'\n')


def section_span(raw: bytes, marker: bytes) -> tuple:
    """[the heading ``marker``, the next heading of the same or a higher level).

    Review finding config 1: the old check had a lower bound (after '## Appendix
    B.') and no upper bound, so a fence under Appendix C passed. Lines inside ```
    fences are skipped, so a '#' comment in a code block is not taken for a
    heading. The marker must begin a line and must be a heading.
    """
    start = raw.index(marker)
    if start and raw[start - 1:start] != b'\n':
        raise ValueError('marker %r does not begin a line' % marker)
    level = len(marker) - len(marker.lstrip(b'#'))
    if not level:
        raise ValueError('marker %r is not a heading' % marker)
    nl = raw.find(b'\n', start)
    pos = len(raw) if nl == -1 else nl + 1
    in_fence = False
    while pos < len(raw):
        nl = raw.find(b'\n', pos)
        line = raw[pos:len(raw) if nl == -1 else nl]
        if line.startswith(b'```'):
            in_fence = not in_fence
        elif not in_fence and line.startswith(b'#'):
            k = len(line) - len(line.lstrip(b'#'))
            if k <= level and line[k:k + 1] == b' ':
                return start, pos
        if nl == -1:
            break
        pos = nl + 1
    return start, len(raw)


def confinement(new_raw: bytes, marker: bytes) -> dict:
    """Where the inserted text landed: inside the fence, and the fence inside the
    section (lower AND upper bound)? Offsets are byte offsets."""
    i = new_raw.find(INSERTED_BYTES)
    try:
        s0, s1 = section_span(new_raw, marker)
        f0, f1 = fence_span(new_raw, marker)
    except ValueError as e:
        return {'error': str(e), 'fence_inside_section': False,
                'insertion_inside_fence': False}
    j = i + len(INSERTED_BYTES)
    return {'insert_at': i, 'insert_end': j, 'section': [s0, s1], 'fence': [f0, f1],
            'fence_inside_section': s0 < f0 and f1 <= s1,
            'insertion_inside_fence': i >= 0 and f0 <= i and j <= f1}


def flatten(d, prefix=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, prefix + k + '.'))
    else:
        out[prefix[:-1]] = d
    return out


def insert_once(raw: bytes) -> bytes:
    if raw.count(ANCHOR_BYTES) != 1:
        raise ValueError('the anchor line occurs %d times' % raw.count(ANCHOR_BYTES))
    return raw.replace(ANCHOR_BYTES, INSERTED_BYTES + ANCHOR_BYTES, 1)


def git(*args) -> str:
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> int:
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / ('CONFIG_AMENDMENT_RECEIPT_%s.json' % stamp)
    if receipt_path.exists():
        print('refusing: %s exists (write-once)' % receipt_path, file=sys.stderr)
        return 2

    # -- 1. preconditions, on BYTES (review finding config 0) ------------------
    old_raw = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
               'protocol': PROTO.read_bytes()}
    cells_raw = CELLS.read_bytes()
    cfg_raw = old_raw['config']
    try:
        blocks = [cfg_raw, block_of(old_raw['architecture'], ARCH_MARKER),
                  block_of(old_raw['protocol'], PROTO_MARKER)]
    except ValueError as e:
        print('refusing: a configuration block could not be extracted: %s' % e,
              file=sys.stderr)
        return 2
    pre = {
        'three_blocks_identical': len(set(blocks)) == 1,
        'block_sha256': sha(cfg_raw),
        'block_bytes': len(cfg_raw),
        'is_the_reviewed_block': (sha(cfg_raw) == PRIOR_BLOCK_SHA256
                                  and len(cfg_raw) == PRIOR_BLOCK_BYTES),
        'protocol_sha256': sha(old_raw['protocol']),
        'architecture_sha256': sha(old_raw['architecture']),
        'protocol_is_the_reviewed_preimage': sha(old_raw['protocol']) == PRIOR_SUCCESSOR,
        'architecture_is_the_reviewed_preimage': (sha(old_raw['architecture'])
                                                  == PRIOR_ARCH_SHA256),
        'cr_bytes': dict({k: v.count(b'\r') for k, v in old_raw.items()},
                         cells=cells_raw.count(b'\r')),
        'cells_sha256': sha(cells_raw),
        'cells_round_trips': ((json.dumps(json.loads(cells_raw), indent=1) + '\n')
                              .encode('utf-8') == cells_raw),
        'head': git('rev-parse', 'HEAD'),
    }
    if not (pre['three_blocks_identical'] and pre['is_the_reviewed_block']
            and pre['cells_round_trips'] and pre['protocol_is_the_reviewed_preimage']
            and pre['architecture_is_the_reviewed_preimage']
            and not any(pre['cr_bytes'].values())):
        print('refusing: a precondition failed: %s' % json.dumps(pre), file=sys.stderr)
        return 2
    old_cfg = json.loads(cfg_raw)
    if 'engineering_acquisition' in old_cfg:
        print('refusing: the section already exists', file=sys.stderr)
        return 2

    # -- 2. insert, identically, three times, as bytes -----------------------
    try:
        new_raw = {k: insert_once(v) for k, v in old_raw.items()}
    except ValueError as e:
        print('refusing: %s; NOTHING was written' % e, file=sys.stderr)
        return 2
    new_cfg_raw = new_raw['config']

    # -- 3. postconditions, computed BEFORE anything is written ---------------
    new_blocks = [new_cfg_raw, block_of(new_raw['architecture'], ARCH_MARKER),
                  block_of(new_raw['protocol'], PROTO_MARKER)]
    new_cfg = json.loads(new_cfg_raw)
    fo, fn = flatten(old_cfg), flatten(new_cfg)
    added = sorted(set(fn) - set(fo))
    removed = sorted(set(fo) - set(fn))
    changed = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
    # Review finding config 0: "Assert new_arch_bytes.replace(INSERTED,b'',1) ==
    # old_arch_bytes before writing". This checks it for all three documents, and
    # requires the inserted text to occur exactly once, so the deletion is
    # unambiguous.
    additive = {k: (new_raw[k].count(INSERTED_BYTES) == 1
                    and new_raw[k].replace(INSERTED_BYTES, b'', 1) == old_raw[k])
                for k in DOC_NAMES}
    # Review finding config 1: the insertion must be inside the fence, and the
    # fence inside the section, with an upper bound.
    where = {'architecture': confinement(new_raw['architecture'], ARCH_MARKER),
             'protocol': confinement(new_raw['protocol'], PROTO_MARKER)}
    inside = {k: (additive[k] and v['fence_inside_section'] and v['insertion_inside_fence'])
              for k, v in where.items()}
    post = {
        'three_blocks_identical': len(set(new_blocks)) == 1,
        'block_sha256': sha(new_cfg_raw),
        'block_bytes': len(new_cfg_raw),
        'added_keys': added, 'removed_keys': removed, 'changed_keys': changed,
        'exactly_the_six_fields_added': added == sorted('engineering_acquisition.' + k
                                                        for k in SECTION),
        'section_equals_root_table': new_cfg.get('engineering_acquisition') == SECTION,
        'dispatch_cutoff_is_wall_minus_reserve': (
            SECTION['dispatch_cutoff_seconds']
            == SECTION['wall_seconds_total'] - SECTION['cleanup_reserve_seconds']),
        'deleting_the_added_lines_reproduces_the_prior_block': (
            sha(new_cfg_raw.replace(INSERTED_BYTES, b'', 1)) == PRIOR_BLOCK_SHA256),
        'deleting_the_inserted_text_reproduces_each_preimage': additive,
        'cr_bytes_after': {k: v.count(b'\r') for k, v in new_raw.items()},
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
        'protocol_sha256': sha(new_raw['protocol']),
        'architecture_sha256': sha(new_raw['architecture']),
        'insertion_placement': where,
        'architecture_change_is_inside_6_1_only': inside['architecture'],
        'protocol_change_is_inside_appendix_b_only': inside['protocol'],
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
          and all(additive.values()) and not any(post['cr_bytes_after'].values())
          and post['architecture_change_is_inside_6_1_only']
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
    cells = json.loads(cells_raw)
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
    new_cells = json.loads(cells_raw)
    new_cells['provenance']['vocabulary_alignment']['superseded_by'] = new_sb
    a, b = json.loads(cells_raw), json.loads(json.dumps(new_cells))
    a['provenance']['vocabulary_alignment'].pop('superseded_by')
    b['provenance']['vocabulary_alignment'].pop('superseded_by')
    if a != b:
        print('refusing: cells.json would change outside superseded_by', file=sys.stderr)
        return 2
    new_cells_raw = (json.dumps(new_cells, indent=1) + '\n').encode('utf-8')

    # -- 5. write, as bytes, then the receipt --------------------------------
    intended = {CONFIG: new_cfg_raw, ARCH: new_raw['architecture'],
                PROTO: new_raw['protocol'], CELLS: new_cells_raw}
    for path, raw in intended.items():
        path.write_bytes(raw)
    written = {
        'read_back_equals_computed': all(p.read_bytes() == raw for p, raw in intended.items()),
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
            'architecture_sha256': PRIOR_ARCH_SHA256, 'protocol_sha256': PRIOR_SUCCESSOR,
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
