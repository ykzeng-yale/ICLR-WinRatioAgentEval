"""Independent re-derivation of the repair amendment (root 20:40 items 2 and 4), from git.

    verify_repair_amendment.py <amendment-commit> [--sources-dir DIR] [--write-receipt]

<amendment-commit> is the commit that ADDS the correction receipt
results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_<UTC>.json (the correction run of
the amendment tool; its first run, commit 1349619, was withdrawn after review and its
receipt is kept unedited).

It does NOT import the amendment tool (experiments/live_ab_tools/repair_amendment.py).
Every expectation is its own literal: the pre-image revision and digests, the key of
every insertion and the heading it must lie under (EXPECTED, not the receipt's
"section" field: review finding 6 of the first run showed that a paragraph moved into
the wrong section verified once the receipt was edited to match), the added config
keys, the contract value, root's 16:30 engineering caps, the rule-block digest, the
withdrawn first run. From `git show` blobs of the reviewed pre-image revision
(PRE_REV, b049307 -- NOT <commit>~1, which is the withdrawn first run) and of the
commit it re-derives:

  1. the pre-image documents are the reviewed ones (config e4d42f5d, 13,917 bytes;
     ARCHITECTURE 727003c1; protocol 64ace6d3; cells.json 5c4a28f7);
  2. the receipt lists exactly the insertion keys of EXPECTED, each once, and its
     "section" fields agree with EXPECTED;
  3. every change is a pure insertion: each listed text occurs once, and deleting
     them reproduces each pre-image document byte for byte;
  4. each prose insertion lies under the heading EXPECTED names (its own line
     scanner), each configuration insertion inside the ```json fence of its section;
  5. the three-way verbatim contract on BYTES (its own fence extraction), no CR;
  6. the flattened config key diff is exactly the three added keys, nothing removed
     or changed; `server_supervision` is the contract literal; the prompts in the
     config are the receipt's texts; `engineering_acquisition` is unchanged and equals
     root's 16:30 table;
  7. the statistical rule-block digest before and after is cbfd1792
     (lab_common.rule_block_sha256, the canonical definition);
  8. protocol sections 1, 3 and 11 are byte-identical (its own section scanner);
  9. cells.json: the original pin untouched; the new successor is the commit's
     protocol digest and supersedes the original; the five earlier entries are
     unchanged; the sixth is the pre-image's successor minus the moved keys plus its
     changing commit 48f4d70 (and `git show 48f4d70:` of the protocol hashes to
     64ace6d3); the reason names the new automatic aborts and the provisional
     reportability change and no longer claims "no decision rule, stopping rule";
     nothing outside superseded_by changed;
 10. the corrections of the review are present in the protocol text (6.4 lists the
     new automatic aborts; 5.3 marks the reportability sentence provisional; 12.2
     puts row 29 on the _prefreeze chain; 14.6 takes the new aborts out of
     operator_discretion);
 11. the correction receipt names the withdrawn first run by its literals; `git show
     1349619:` of the protocol hashes to the withdrawn digest; the first receipt is
     present in the commit byte-unchanged (write-once);
 12. optionally (--sources-dir), the prompt similarity maxima recorded in the
     receipt, recomputed with its own normalisation (checked equal to
     lab_data.normalize_prompt on the prompts).

Every check is NAMED, and all_verified is verdict(checks): True only if every named
check is True. The witnesses (tests_repair_amendment.VerifierTests) pin the list of
names and set each one False in turn at verdict(), so a check deleted from the list or
from the aggregation is caught; they also give real-input negative controls for the
pins, the config diff, the rule block, the vocabulary sections and the placement map.

NEGATIVE CONTROLS run by main() (each must FAIL the same predicate): the pre-image
documents presented as the amendment; the amendment with one byte of the protocol
changed outside every insertion; the amended config with the pre-image ARCHITECTURE
block; the withdrawn first run's documents presented as the amendment.

READ-ONLY: git show and file reads. By default it prints its result; with
--write-receipt it also writes results/live_ab/REPAIR_AMENDMENT_VERIFICATION_<UTC>.json
(write-once). Exit 0 only if everything verified and every negative control failed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

DOCS = {'config': 'experiments/live_ab/config.json',
        'architecture': 'experiments/live_ab/design/ARCHITECTURE_FINAL.md',
        'protocol': 'experiments/live_ab/design/protocol_FINAL.md',
        'cells': 'experiments/live_ab_validation/cells.json'}
#: the reviewed pre-image revision (main before the amendment)
PRE_REV = 'b049307ff62153a054f61b6179291ba987de2ba1'
PARENT_PINS = {'config': 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824',
               'architecture': '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab',
               'protocol': '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b',
               'cells': '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'}
PARENT_CONFIG_BYTES = 13917
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
DEMOTED_COMMIT = '48f4d70fbd580df282b551506448457a09ab514d'
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
ADDED_KEYS = ['prefreeze.conformance_prompts',
              'server_supervision.max_supervised_restarts_per_server_per_trial',
              'server_supervision.on_exceeding']
SERVER_SUPERVISION = {'max_supervised_restarts_per_server_per_trial': 3,
                      'on_exceeding': 'abort_trial_incomplete'}
#: root 16:30 decision 3, the six literal engineering caps
ROOT_1630_TABLE = {'wall_seconds_total': 600, 'cleanup_reserve_seconds': 90,
                   'dispatch_cutoff_seconds': 510, 'diagnostic_byte_budget': 8388608,
                   'seconds_per_request': 120, 'total_generated_tokens': 2048}
FENCE_MARKERS = {'architecture': '### 6.1 Full key list', 'protocol': '## Appendix B.'}
VOCAB = {'1': '## 1. Purpose, scope', '3': '## 3. Task roster', '11': '## 11. The planning study'}
MOVED = ('prior_successors', 'changing_commit_note', 'correction_to_the_owner_report')
DOC_KEYS = ('config', 'architecture', 'protocol')
#: the withdrawn first run (commit 1349619) and its kept receipt
WITHDRAWN_COMMIT = '134961944cec6e83f2b27586cda3d1f42ba40b72'
WITHDRAWN_PROTOCOL = '25014221bbba4a4d67e8bde845d401318d7db6fc04375ec3f7d875532b754a0c'
WITHDRAWN_RECEIPT = 'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json'
WITHDRAWN_RECEIPT_SHA256 = '6729de69f66ed7cea7b6f8c8eb8370d9612ab4be7f094288ee5c2cc445715a19'
RECEIPT_RE = r'results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_\d{8}_\d{4}\.json'
#: key -> (document, the heading it must lie under (None: config.json), inside the
#: ```json fence of that heading's section)
EXPECTED = {
    'config.prompts': ('config', None, False),
    'config.server_supervision': ('config', None, False),
    'architecture.6_1.prompts': ('architecture', '### 6.1 Full key list', True),
    'architecture.6_1.server_supervision': ('architecture', '### 6.1 Full key list', True),
    'protocol.appendix_b.prompts': ('protocol', '## Appendix B.', True),
    'protocol.appendix_b.server_supervision': ('protocol', '## Appendix B.', True),
    'protocol.2_4_item_6': ('protocol', '### 2.4 T3 candidate', False),
    'protocol.5_3': ('protocol', '### 5.3 Server supervision', False),
    'protocol.5_8': ('protocol', '### 5.8 Pre-freeze out-of-design phase', False),
    'protocol.6_4': ('protocol', '### 6.4 Failure-to-outcome table', False),
    'protocol.12_2': ('protocol', '### 12.2 Event schema', False),
    'protocol.13_1': ('protocol', '### 13.1 Usage accounting for every try', False),
    'protocol.14_3': ('protocol', '### 14.3 Immutability, and the two classes of code', False),
    'protocol.14_6': ('protocol', '### 14.6 Trial order, unconditional execution', False),
    'architecture.4_4': ('architecture', '### 4.4 Trial chain', False),
    'architecture.6_3': ('architecture', '### 6.3 Keys that may never be amended', False),
    'architecture.7_1.row_1b': ('architecture', '### 7.1 States and transitions', False),
    'architecture.7_1.row_20a': ('architecture', '### 7.1 States and transitions', False),
    'architecture.7_1.rows_21a_21b': ('architecture', '### 7.1 States and transitions', False),
}
#: the review's corrections, as text the amended protocol must carry in each section
CORRECTIONS = {
    '6_4_lists_the_new_automatic_aborts': (
        '### 6.4 Failure-to-outcome table', ('**New automatic, deterministic aborts.**',
                                             '`trial_aborted(server_restart_cap)`',
                                             '`trial_aborted(unresolved_worker)`',
                                             '`smoke_transport`', '`smoke_no_usage`'), ()),
    '5_3_reportability_is_provisional': (
        '### 5.3 Server supervision', ('**Provisional, pending root\'s',
                                       'no freeze may be made while it is'),
        ('that label replaces the rule of 6.4', 'the rule already fixed for the stage')),
    '12_2_row_29_also_on_the_prefreeze_chain': (
        '### 12.2 Event schema', ('Row 28 is written on a trial chain only.',
                                  'on the `_prefreeze` chain'),
        ('Rows 28 and 29 are trial-chain events.',)),
    '14_6_new_aborts_are_not_operator_discretion': (
        '### 14.6 Trial order, unconditional execution',
        ('does not apply', '`operator_discretion`', '`trial_aborted(server_restart_cap)`'), ()),
    '5_8_neither_served_model': (
        '### 5.8 Pre-freeze out-of-design phase', ('neither served model',),
        ('no model was run', 'under a rule fixed before their texts')),
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


def verdict(checks: dict) -> bool:
    """THE aggregation point: True only if ``checks`` is non-empty and every named check
    is exactly True. The witnesses wrap this function to set one check False at a time."""
    return bool(checks) and all(v is True for v in checks.values())


# -- its own text machinery ------------------------------------------------------
def fence_block(raw: bytes, marker: str) -> tuple:
    """(start, end, block): the first ```json fence after ``marker``, the extraction
    tests_lab_e2e.ConfigTests performs, on bytes."""
    s = raw.index(marker.encode())
    f = raw.index(b'```json', s) + len(b'```json')
    e = raw.index(b'```', f)
    return f, e, raw[f:e].lstrip(b'\n')


def heading_lines(raw: bytes) -> list:
    """[(offset, level, text)] of every markdown heading line outside ``` fences."""
    out, pos, fenced = [], 0, False
    for line in raw.split(b'\n'):
        if line.startswith(b'```'):
            fenced = not fenced
        elif not fenced and line.startswith(b'#'):
            level = len(line) - len(line.lstrip(b'#'))
            if line[level:level + 1] == b' ':
                out.append((pos, level, line.decode('utf-8')))
        pos += len(line) + 1
    return out


def governing_heading(raw: bytes, offset: int, max_level: int = 3) -> str:
    """The text of the nearest heading of level <= max_level before ``offset``."""
    best = None
    for pos, level, text in heading_lines(raw):
        if pos > offset:
            break
        if level <= max_level:
            best = text
    return best


def section_text(raw: bytes, heading: str) -> bytes:
    hs = heading_lines(raw)
    for n, (pos, level, text) in enumerate(hs):
        if text.startswith(heading):
            end = next((p for p, lv, _ in hs[n + 1:] if lv <= level), len(raw))
            return raw[pos:end]
    raise ValueError('heading %r not found' % heading)


def flat(d, prefix=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, prefix + k + '.'))
    else:
        out[prefix[:-1]] = d
    return out


def normalize(text: str) -> str:
    return re.sub(r'\W+', ' ', (text or '').lower()).strip()


def jaccard(a: str, b: str) -> float:
    x, y = set(normalize(a).split()), set(normalize(b).split())
    return len(x & y) / len(x | y) if (x | y) else 1.0


# -- the predicate -----------------------------------------------------------------
def verify(before: dict, after: dict, receipt: dict, demoted_commit_protocol: bytes,
           history: dict) -> dict:
    """Every re-derivation for one (pre-image, amendment, receipt) triple. Pure.
    ``history``: {'withdrawn_protocol': `git show 1349619:` of the protocol,
    'withdrawn_receipt_then': the first receipt at 1349619, 'withdrawn_receipt_now':
    the first receipt in the amendment commit (b'' if absent)}."""
    r = {}
    c = {}                                                     # the named checks
    r['parent_is_the_reviewed_preimage'] = {k: sha(before[k]) == v for k, v in PARENT_PINS.items()}
    r['parent_config_bytes'] = len(before['config'])
    c['parent_is_the_reviewed_preimage'] = all(r['parent_is_the_reviewed_preimage'].values())
    c['parent_config_bytes'] = r['parent_config_bytes'] == PARENT_CONFIG_BYTES
    ins = receipt.get('insertions', [])
    keys = [i.get('key') for i in ins]
    r['insertion_keys'] = keys
    c['receipt_lists_exactly_the_expected_insertions'] = (
        sorted(keys) == sorted(EXPECTED) and len(set(keys)) == len(keys)
        and all(i.get('document') == EXPECTED[i['key']][0] for i in ins if i.get('key') in EXPECTED))
    c['receipt_sections_agree_with_the_verifier_headings'] = all(
        (EXPECTED[i['key']][1] is None and i.get('section') is None)
        or (EXPECTED[i['key']][1] is not None
            and str(i.get('section') or '').startswith(EXPECTED[i['key']][1]))
        for i in ins if i.get('key') in EXPECTED)
    by_doc = {d: [i for i in ins if i.get('document') == d] for d in DOC_KEYS}
    r['insertions_listed'] = {d: len(v) for d, v in by_doc.items()}
    additive, once = {}, {}
    for d in DOC_KEYS:
        raw = after[d]
        once[d] = all(raw.count(i['text'].encode('utf-8')) == 1 for i in by_doc[d])
        for i in by_doc[d]:
            raw = raw.replace(i['text'].encode('utf-8'), b'', 1)
        additive[d] = raw == before[d] and after[d] != before[d]
    r['each_insertion_occurs_once'] = once
    r['deleting_the_insertions_reproduces_the_parent'] = additive
    c['each_insertion_occurs_once'] = bool(ins) and all(once.values())
    c['deleting_the_insertions_reproduces_the_parent'] = all(additive.values())
    placed = {}
    for key, (d, heading, fenced) in EXPECTED.items():
        if heading is None:
            continue
        row = next((i for i in ins if i.get('key') == key), None)
        if row is None:
            placed[key] = False
            continue
        raw = after[d]
        text = row['text'].encode('utf-8')
        off = raw.find(text)
        level = len(heading) - len(heading.lstrip('#'))
        head = governing_heading(raw, off, level) if off >= 0 else None
        ok = head is not None and head.startswith(heading)
        if fenced:
            try:
                f, e, _ = fence_block(raw, FENCE_MARKERS[d])
                ok = ok and f <= off and off + len(text) <= e
            except ValueError:
                ok = False
        placed[key] = ok
    r['each_insertion_under_its_heading'] = placed
    c['each_insertion_under_the_verifier_heading'] = bool(placed) and all(placed.values())
    r['cr_bytes'] = {d: after[d].count(b'\r') for d in DOC_KEYS}
    c['no_cr_byte'] = not any(r['cr_bytes'].values())
    try:
        blocks = {'config': after['config'],
                  'architecture': fence_block(after['architecture'], FENCE_MARKERS['architecture'])[2],
                  'protocol': fence_block(after['protocol'], FENCE_MARKERS['protocol'])[2]}
        r['three_blocks_byte_identical'] = len(set(blocks.values())) == 1
    except ValueError:
        r['three_blocks_byte_identical'] = False
    c['three_blocks_byte_identical'] = r['three_blocks_byte_identical']
    try:
        old_cfg, new_cfg = json.loads(before['config']), json.loads(after['config'])
        fo, fn = flat(old_cfg), flat(new_cfg)
        r['added_keys'] = sorted(set(fn) - set(fo))
        r['removed_keys'] = sorted(set(fo) - set(fn))
        r['changed_keys'] = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
        r['server_supervision_is_the_contract_literal'] = (
            new_cfg.get('server_supervision') == SERVER_SUPERVISION)
        r['prompts_are_the_receipt_texts'] = (
            new_cfg.get('prefreeze', {}).get('conformance_prompts')
            == receipt.get('conformance_prompts', {}).get('2_texts'))
        r['engineering_acquisition_unchanged_and_root_table'] = (
            old_cfg.get('engineering_acquisition') == new_cfg.get('engineering_acquisition')
            == ROOT_1630_TABLE)
        r['rule_block_before'] = lab_common.rule_block_sha256(old_cfg)
        r['rule_block_after'] = lab_common.rule_block_sha256(new_cfg)
    except (ValueError, KeyError, AttributeError) as e:
        r['config_error'] = str(e)
    c['config_parses'] = 'config_error' not in r
    c['exactly_the_three_keys_added'] = r.get('added_keys') == ADDED_KEYS
    c['no_key_removed'] = r.get('removed_keys') == []
    c['no_key_changed'] = r.get('changed_keys') == []
    c['server_supervision_is_the_contract_literal'] = (
        r.get('server_supervision_is_the_contract_literal') is True)
    c['prompts_are_the_receipt_texts'] = r.get('prompts_are_the_receipt_texts') is True
    c['engineering_acquisition_unchanged_and_root_table'] = (
        r.get('engineering_acquisition_unchanged_and_root_table') is True)
    c['rule_block_before_and_after_is_cbfd1792'] = (
        r.get('rule_block_before') == RULE_BLOCK == r.get('rule_block_after'))
    try:
        r['vocabulary_sections_identical'] = {
            n: section_text(before['protocol'], h) == section_text(after['protocol'], h)
            for n, h in VOCAB.items()}
    except ValueError as e:
        r['vocabulary_sections_identical'] = {'error': str(e)}
    c['vocabulary_sections_identical'] = all(
        v is True for v in r['vocabulary_sections_identical'].values())
    # cells.json
    try:
        cb, ca = json.loads(before['cells']), json.loads(after['cells'])
        vb, vaa = cb['provenance']['vocabulary_alignment'], ca['provenance']['vocabulary_alignment']
        sbb, sba = vb['superseded_by'], vaa['superseded_by']
        prior = sba.get('prior_successors', [])
        demoted = prior[5] if len(prior) > 5 else {}
        expect = {k: v for k, v in sbb.items() if k not in MOVED}
        got = {k: v for k, v in demoted.items()
               if k not in ('changing_commit_of_this_successor', 'changing_commit_note')}
        note = str(demoted.get('changing_commit_note'))
        reason = str(sba.get('reason', ''))
        xb, xa = json.loads(before['cells']), json.loads(after['cells'])
        xb['provenance']['vocabulary_alignment'].pop('superseded_by')
        xa['provenance']['vocabulary_alignment'].pop('superseded_by')
        r['cells'] = {
            'original_pin_untouched': vaa.get('sha256') == ORIGINAL_PIN == vb.get('sha256'),
            'new_successor_is_the_amended_protocol': sba.get('sha256') == sha(after['protocol']),
            'supersedes_the_original': sba.get('supersedes') == ORIGINAL_PIN,
            'six_prior_successors': len(prior) == 6,
            'first_five_unchanged': prior[:5] == sbb.get('prior_successors'),
            'sixth_is_the_parent_successor_whole': got == expect,
            'sixth_names_its_commit': demoted.get('changing_commit_of_this_successor')
            == DEMOTED_COMMIT,
            'sixth_says_how_resolved': ('git show %s:' % DEMOTED_COMMIT[:7] in note
                                        and '/design/protocol_FINAL.md' in note),
            'correction_moved_whole': sba.get('correction_to_the_owner_report')
            == sbb.get('correction_to_the_owner_report'),
            'reason_says_not_appendix_b_only': reason.startswith('NOT Appendix-B-only'),
            'reason_names_the_new_automatic_aborts': all(
                t in reason for t in ('server_restart_cap', 'unresolved_worker',
                                      'trial_aborted(infrastructure)', 'receipt_mismatch')),
            'reason_says_the_reportability_change_is_provisional': 'PROVISIONALLY' in reason,
            'reason_does_not_claim_no_decision_or_stopping_rule_change':
                'decision rule, stopping rule' not in reason,
            'ruling_cites_the_2040_review': 'reviews/prerun_bundle_go_nogo_20260923_2040.md'
            in str(sba.get('ruling', '')),
            'nothing_outside_superseded_by_changed': xb == xa,
            'demoted_commit_carries_the_parent_successor':
                sha(demoted_commit_protocol) == PARENT_PINS['protocol'] == sbb.get('sha256'),
        }
    except (ValueError, KeyError, TypeError, IndexError) as e:
        r['cells'] = {'error': str(e)}
    c['cells'] = 'error' not in r['cells'] and all(v is True for v in r['cells'].values())
    # the review's corrections, in the amended protocol
    corr = {}
    for name, (heading, must, must_not) in CORRECTIONS.items():
        try:
            sec = section_text(after['protocol'], heading).decode('utf-8')
            corr[name] = all(t in sec for t in must) and not any(t in sec for t in must_not)
        except ValueError:
            corr[name] = False
    r['corrections_in_the_protocol'] = corr
    c['corrections_in_the_protocol'] = all(corr.values())
    c['receipt_names_the_amended_protocol'] = (
        receipt.get('successor_provenance', {}).get('new_successor') == sha(after['protocol']))
    c['receipt_written_digests_match'] = (
        receipt.get('written', {}).get('config_sha256') == sha(after['config'])
        and receipt.get('written', {}).get('protocol_sha256') == sha(after['protocol'])
        and receipt.get('written', {}).get('architecture_sha256') == sha(after['architecture']))
    corrects = receipt.get('corrects') or {}
    c['receipt_corrects_the_withdrawn_first_run'] = (
        corrects.get('commit') == WITHDRAWN_COMMIT
        and corrects.get('protocol_sha256') == WITHDRAWN_PROTOCOL
        and corrects.get('receipt') == WITHDRAWN_RECEIPT
        and corrects.get('receipt_sha256') == WITHDRAWN_RECEIPT_SHA256)
    c['withdrawn_commit_carries_the_withdrawn_protocol'] = (
        sha(history.get('withdrawn_protocol', b'')) == WITHDRAWN_PROTOCOL
        and sha(after['protocol']) != WITHDRAWN_PROTOCOL)
    c['withdrawn_receipt_kept_byte_unchanged'] = (
        sha(history.get('withdrawn_receipt_then', b'')) == WITHDRAWN_RECEIPT_SHA256
        == sha(history.get('withdrawn_receipt_now', b'')))
    r['checks'] = c
    r['all_verified'] = verdict(c)
    return r


def negative_controls(before: dict, after: dict, receipt: dict, demoted: bytes,
                      history: dict, withdrawn_docs: dict) -> dict:
    """The same predicate on four document sets that must NOT verify."""
    out = {}
    out['parent_presented_as_the_amendment'] = verify(before, dict(before), receipt,
                                                      demoted, history)['all_verified']
    p = after['protocol']
    k = p.index(b'## 1. Purpose, scope') - 2               # a byte outside every insertion
    tampered = dict(after, protocol=p[:k] + (b'X' if p[k:k + 1] != b'X' else b'Y') + p[k + 1:])
    out['one_protocol_byte_changed_outside_the_insertions'] = verify(
        before, tampered, receipt, demoted, history)['all_verified']
    f, e, _ = fence_block(after['architecture'], FENCE_MARKERS['architecture'])
    fb, eb, _ = fence_block(before['architecture'], FENCE_MARKERS['architecture'])
    old_block_arch = after['architecture'][:f] + before['architecture'][fb:eb] + \
        after['architecture'][e:]
    out['amended_config_with_the_parent_architecture_block'] = verify(
        before, dict(after, architecture=old_block_arch), receipt, demoted, history)['all_verified']
    out['withdrawn_first_run_presented_as_the_amendment'] = verify(
        before, dict(withdrawn_docs), receipt, demoted, history)['all_verified']
    out['every_control_failed'] = not any(v for v in out.values())
    return out


def prompt_recheck(receipt: dict, sources_dir: Path) -> dict:
    """The similarity maxima, recomputed with this file's normalisation on the three
    sources (their digests checked against the config pins recorded in the receipt)."""
    sys.path.insert(0, str(LAB))
    import lab_data                                            # noqa: E402
    facts = receipt['conformance_prompts']['3_mechanical_check_results']['source_facts']
    recs = {}
    for name, fact in facts.items():
        data = (Path(sources_dir) / fact['file']).read_bytes()
        if sha(data) != fact['sha256']:
            return {'error': '%s digest differs from the receipt' % name, 'ok': False}
        if name == 'humaneval':
            recs[name] = [json.loads(l) for l in gzip.decompress(data).decode().splitlines()
                          if l.strip()]
        elif fact['file'].endswith('.jsonl'):
            recs[name] = [json.loads(l) for l in data.decode().splitlines() if l.strip()]
        else:
            recs[name] = json.loads(data.decode())
    texts = ([('mbpp/%d' % int(r['task_id']), r['prompt']) for r in recs['mbpp_sanitized']]
             + [('mbpp_full/%d' % int(r['task_id']), r['text']) for r in recs['mbpp_full']]
             + [('humaneval/%s' % str(r['task_id']).split('/')[-1], r['prompt'])
                for r in recs['humaneval']])
    out = []
    for p, row in zip(receipt['conformance_prompts']['2_texts'],
                      receipt['conformance_prompts']['3_mechanical_check_results']['per_prompt']):
        best = max((jaccard(p['prompt'], t), u) for u, t in texts)
        out.append({'id': p['id'], 'max_jaccard': round(best[0], 6), 'closest': best[1],
                    'matches_receipt': (round(best[0], 6) == row['max_jaccard']
                                        and best[1] == row['closest_source_uid']),
                    'below_0_5': best[0] < 0.5,
                    'normalisation_agrees_with_lab_data':
                        normalize(p['prompt']) == lab_data.normalize_prompt(p['prompt'])})
    return {'per_prompt': out, 'sources_compared': len(texts),
            'ok': all(o['matches_receipt'] and o['below_0_5']
                      and o['normalisation_agrees_with_lab_data'] for o in out)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('commit', help='the commit that adds the correction receipt')
    ap.add_argument('--sources-dir', default=None)
    ap.add_argument('--write-receipt', action='store_true')
    args = ap.parse_args(argv)
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', args.commit + '^{commit}'],
                            capture_output=True, text=True, check=True).stdout.strip()
    names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', commit],
                           capture_output=True, text=True, check=True).stdout.split()
    receipts = [n for n in names if re.fullmatch(RECEIPT_RE, n)]
    if len(receipts) != 1:
        print('refusing: %s adds %d repair amendment correction receipts'
              % (commit[:7], len(receipts)), file=sys.stderr)
        return 2
    receipt = json.loads(blob(commit, receipts[0]))
    before = {k: blob(PRE_REV, p) for k, p in DOCS.items()}
    after = {k: blob(commit, p) for k, p in DOCS.items()}
    demoted = blob(DEMOTED_COMMIT, DOCS['protocol'])
    try:
        now = blob(commit, WITHDRAWN_RECEIPT)
    except subprocess.CalledProcessError:
        now = b''
    history = {'withdrawn_protocol': blob(WITHDRAWN_COMMIT, DOCS['protocol']),
               'withdrawn_receipt_then': blob(WITHDRAWN_COMMIT, WITHDRAWN_RECEIPT),
               'withdrawn_receipt_now': now}
    withdrawn_docs = {k: blob(WITHDRAWN_COMMIT, p) for k, p in DOCS.items()}
    result = verify(before, after, receipt, demoted, history)
    controls = negative_controls(before, after, receipt, demoted, history, withdrawn_docs)
    doc = {'schema': 'live_ab/repair_amendment_verification-v2',
           'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'amendment_commit': commit, 'receipt': receipts[0], 'pre_image_revision': PRE_REV,
           'working_tree_equals_amendment_commit': all(
               (REPO / p).read_bytes() == after[k] for k, p in DOCS.items()),
           're_derivation': result, 'negative_controls': controls,
           'nothing_executed': 'git show and file reads only'}
    if args.sources_dir:
        doc['prompt_recheck'] = prompt_recheck(receipt, Path(args.sources_dir))
    ok = (result['all_verified'] and controls['every_control_failed']
          and doc.get('prompt_recheck', {'ok': True})['ok'])
    doc['all_verified'] = ok
    text = json.dumps(doc, indent=1, sort_keys=True) + '\n'
    if args.write_receipt:
        out = REPO / 'results' / 'live_ab' / ('REPAIR_AMENDMENT_VERIFICATION_%s.json'
                                              % time.strftime('%Y%m%d_%H%M', time.gmtime()))
        if out.exists():
            print('refusing: %s exists (write-once)' % out, file=sys.stderr)
            return 2
        out.write_text(text)
        print(out)
    print(text if not args.write_receipt else 'all_verified=%s' % ok)
    return 0 if ok else 1


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
