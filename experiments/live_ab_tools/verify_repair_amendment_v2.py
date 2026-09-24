"""Independent re-derivation of the synchronized pre-outcome amendment v2, from git.

    verify_repair_amendment_v2.py <amendment-commit> [--sources-dir DIR] [--runtime]
                                  [--write-receipt]

<amendment-commit> is the commit that ADDS results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_<UTC>.json.

It does NOT import the amendment tool (experiments/live_ab_tools/repair_amendment_v2.py).
Every expectation is its own literal: the pre-image revision and digests, the key of every
insertion and the heading it must lie under (EXPECTED, never the receipt's "section" field), the
one replaced value, the added configuration keys, the contract value, root's 16:30 engineering
caps, the rule-block digest, the withdrawn predecessor.  From `git show` blobs of the reviewed
pre-image revision (PRE_REV, b049307) and of the commit it re-derives:

  1. the pre-image documents are the reviewed ones (config e4d42f5d, 13,917 bytes;
     ARCHITECTURE 727003c1; protocol 64ace6d3; cells.json 5c4a28f7);
  2. the receipt lists exactly the insertion keys of EXPECTED, each once, and its "section"
     fields agree with EXPECTED; it lists the one replacement;
  3. every change is a pure insertion except the one replacement: each listed text occurs once;
     reverting ``"serving_manifest_sha256": "<digest>"}`` to ``... null}`` (once per document)
     and deleting the texts reproduces each pre-image byte for byte;
  4. each prose insertion lies under the heading EXPECTED names (its own line scanner), each
     configuration insertion and the replaced value inside the ```json fence of its section;
  5. the three-way verbatim contract on BYTES (its own fence extraction), no CR;
  6. the flattened config key diff is exactly the three added keys, nothing removed, and the one
     changed key llama_cpp.serving_manifest_sha256 (null before); `server_supervision` is the
     contract literal; the prompts in the config are the receipt's texts;
     `engineering_acquisition` is unchanged and equals root's 16:30 table;
  7. the rule-block digest before and after is cbfd1792 (lab_common.rule_block_sha256);
  8. protocol sections 1, 3 and 11 are byte-identical (its own section scanner);
  9. cells.json: the original pin untouched; the new successor is the commit's protocol digest
     and supersedes the original; the five earlier entries unchanged; the sixth is the
     pre-image's successor minus the moved keys plus its changing commit 48f4d70 (and `git show
     48f4d70:` of the protocol hashes to 64ace6d3); nothing outside superseded_by changed;
 10. the protocol carries root's three restart-cap cases and the corrections the withdrawn
     predecessor lacked, and none of its withdrawn wording (CONTENT);
 11. the serving manifest: the commit adds results/live_ab/freeze/serving_manifest.json, whose
     bytes are its canonical JSON plus one newline (its own canonical form, checked equal to
     lab_common.canonical_json) and whose canonical SHA-256 is the digest in all three
     configuration copies and in the receipt; its paths are <REPO>/<RESULTS> tokens, never
     <HOME> (assembled as seen from the main checkout);
 12. the withdrawn predecessor: the receipt names branch session60/repair-amend, both commits and
     both receipts with their digests, status "withdrawn, not applied"; `git show` of each
     receipt at its commit hashes to that digest; neither commit is an ancestor of the
     amendment commit;
 13. optionally (--runtime): the committed artifact re-verified against the durable build of
     the main checkout with lab_serving_manifest.verify_before_launch (harness code, as seen
     from the main checkout through assemble_serving_manifest.repo_roots) -- no server started
     -- and a copy with one library digest changed refused;
 14. optionally (--sources-dir), the prompt similarity maxima recomputed.

Every check is NAMED, and all_verified is verdict(checks): True only if every named check is
True.  The witnesses (tests_repair_amendment_v2.VerifierTests) pin the list of names, set each
one False in turn at verdict(), and give a real-input variant that makes each check False.

NEGATIVE CONTROLS run by main() (each must FAIL the same predicate): the pre-image presented as
the amendment; one protocol byte changed outside every insertion; the amended config with the
pre-image ARCHITECTURE block; the withdrawn predecessor's documents presented as the amendment;
the amendment with the replaced value reverted to null.

READ-ONLY: git show and file reads (and, with --runtime, otool/nm metadata reads of the durable
build).  With --write-receipt it writes results/live_ab/REPAIR_AMENDMENT_V2_VERIFICATION_<UTC>.json
(write-once).  Exit 0 only if everything verified and every negative control failed.

Prepared and checked by AI agent sessions; not human peer review or author sign-off.
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
CHANGED_KEY = 'llama_cpp.serving_manifest_sha256'
OLD_VALUE = b'"serving_manifest_sha256": null}'
SERVER_SUPERVISION = {'max_supervised_restarts_per_server_per_trial': 3,
                      'on_exceeding': 'abort_trial_incomplete'}
ROOT_1630_TABLE = {'wall_seconds_total': 600, 'cleanup_reserve_seconds': 90,
                   'dispatch_cutoff_seconds': 510, 'diagnostic_byte_budget': 8388608,
                   'seconds_per_request': 120, 'total_generated_tokens': 2048}
FENCE_MARKERS = {'architecture': '### 6.1 Full key list', 'protocol': '## Appendix B.'}
VOCAB = {'1': '## 1. Purpose, scope', '3': '## 3. Task roster', '11': '## 11. The planning study'}
MOVED = ('prior_successors', 'changing_commit_note', 'correction_to_the_owner_report')
DOC_KEYS = ('config', 'architecture', 'protocol')
ARTIFACT = 'results/live_ab/freeze/serving_manifest.json'
RECEIPT_RE = r'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_\d{8}_\d{4}\.json'
MAIN_CHECKOUT = '/Users/yukangzengcmac/ICLR-WinRatioAgentEvals'
#: the withdrawn, never-applied predecessor
WITHDRAWN_BRANCH = 'session60/repair-amend'
WITHDRAWN_COMMITS = ('134961944cec6e83f2b27586cda3d1f42ba40b72',
                     'ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc')
WITHDRAWN_RECEIPTS = {
    'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json':
        ('134961944cec6e83f2b27586cda3d1f42ba40b72',
         '6729de69f66ed7cea7b6f8c8eb8370d9612ab4be7f094288ee5c2cc445715a19'),
    'results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_20260923_2242.json':
        ('ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc',
         '9feea2ac87b086810f38062bd039186a93d352aae1dbcc1d5e0a73ad9451a291')}
WITHDRAWN_PROTOCOLS = ('25014221bbba4a4d67e8bde845d401318d7db6fc04375ec3f7d875532b754a0c',
                       '5d108b4a1a8d076fdd79b973834b8f3b3e4604526a9d90e943329c9cbf2fc2b8')
_S71 = '### 7.1 States and transitions'
#: key -> (document, the heading it must lie under (None: config.json), inside the ```json
#: fence of that heading's section)
EXPECTED = {
    'config.prompts': ('config', None, False),
    'config.server_supervision': ('config', None, False),
    'architecture.6_1.prompts': ('architecture', '### 6.1 Full key list', True),
    'architecture.6_1.server_supervision': ('architecture', '### 6.1 Full key list', True),
    'protocol.appendix_b.prompts': ('protocol', '## Appendix B.', True),
    'protocol.appendix_b.server_supervision': ('protocol', '## Appendix B.', True),
    'protocol.2_2': ('protocol', '### 2.2 Serving software', False),
    'protocol.2_4_item_6': ('protocol', '### 2.4 T3 candidate', False),
    'protocol.5_3': ('protocol', '### 5.3 Server supervision', False),
    'protocol.5_8': ('protocol', '### 5.8 Pre-freeze out-of-design phase', False),
    'protocol.6_4': ('protocol', '### 6.4 Failure-to-outcome table', False),
    'protocol.12_2': ('protocol', '### 12.2 Event schema', False),
    'protocol.12_4': ('protocol', '### 12.4 Anchoring: mechanics', False),
    'protocol.13_1': ('protocol', '### 13.1 Usage accounting for every try', False),
    'protocol.14_3': ('protocol', '### 14.3 Immutability, and the two classes of code', False),
    'protocol.14_6': ('protocol', '### 14.6 Trial order, unconditional execution', False),
    'protocol.16': ('protocol', '## 16. What is reported whatever the outcome', False),
    'architecture.2_1': ('architecture', '### 2.1 `experiments/live_ab/`', False),
    'architecture.2_2': ('architecture', '### 2.2 `results/live_ab/`', False),
    'architecture.3_16.row': ('architecture', '### 3.16 Import isolation matrix', False),
    'architecture.3_16.note': ('architecture', '### 3.16 Import isolation matrix', False),
    'architecture.4_4': ('architecture', '### 4.4 Trial chain', False),
    'architecture.6_3': ('architecture', '### 6.3 Keys that may never be amended', False),
    'architecture.7_1.row_1b': ('architecture', _S71, False),
    'architecture.7_1.row_14c': ('architecture', _S71, False),
    'architecture.7_1.row_20a': ('architecture', _S71, False),
    'architecture.7_1.rows_21a_21b': ('architecture', _S71, False),
}
#: what the amended protocol must carry in each section, and must NOT (the withdrawn wording)
CONTENT = {
    '5_3_three_cases_in_roots_words': (
        '### 5.3 Server supervision',
        ('**(a) Before a valid decision**', '**(b) After a valid, logged and externally receipted '
         'decision**', '**(c) While a logged decision awaits its blocking receipt**',
         'stands at its original `tau`', 'no new deploy or harm decision is made',
         '**Cap invariance.**', 'never reclassified as favourable, unfavourable or',
         '`trial_aborted(server_restart_cap)`', '`golden_objects`'),
        ('not reportable: trial incomplete (restart cap)', "**Provisional, pending root's",
         'question (i)', 'no freeze may be made while it is')),
    '6_4_lists_the_new_automatic_aborts': (
        '### 6.4 Failure-to-outcome table',
        ('**New automatic, deterministic aborts.**', '`trial_aborted(server_restart_cap)`',
         '`trial_aborted(unresolved_worker)`', '`smoke_transport`', '`smoke_no_usage`',
         'follows the three cases of 5.3'),
        ('the provisional rule of 5.3',)),
    '12_2_rows_28_29_30': (
        '### 12.2 Event schema',
        ('| 28 | `server_start_failed` |', '| 29 | `worker_resolved` |',
         '| 30 | `anchor_receipt_rejected` |', 'Rows 28 and 29 are written on a trial chain only.',
         '`completion`', '`resolution`'),
        ('on the `_prefreeze` chain',)),
    '12_4_receipt_attribution_without_timestamp_authority': (
        '### 12.4 Anchoring: mechanics',
        ('**No unknown or stale row becomes a receipt.**', '`node_id`',
         'No wall-clock equality and no latency window is imposed', '`anchor_receipt_rejected`',
         '12.4 has **no timestamp authority**'), ()),
    '14_6_resolution_as_the_code_does_it': (
        '### 14.6 Trial order, unconditional execution',
        ('`trial_aborted(unresolved_worker)`', '`worker_resolved` is a', 'does not apply',
         'it does not take the resolution verdict above'),
        ('for a stage, on the `_prefreeze` chain', 'marks itself completed')),
    '2_2_names_the_artifact': (
        '### 2.2 Serving software',
        ('`results/live_ab/freeze/serving_manifest.json`', '**Re-verification',
         '`llama_cpp.serving_manifest_sha256`'), ()),
    '5_8_neither_served_model': (
        '### 5.8 Pre-freeze out-of-design phase', ('neither served model',),
        ('no model was run', 'under a rule fixed before their texts')),
}
ARCH_CONTENT = {
    '2_2_freeze_layout_names_the_artifact': ('### 2.2 `results/live_ab/`',
                                             ('    serving_manifest.json ',)),
    '6_3_lists_the_keys': ('### 6.3 Keys that may never be amended',
                           ('`server_supervision`', '`prefreeze.conformance_prompts`',
                            '`llama_cpp.serving_manifest_sha256`')),
    '7_1_rows': (_S71, ('| 1b | `PREFLIGHT` |', '| 14c | `ANCHOR_BLOCK` |', '| 20a | any |',
                        '| 21a | any |', '| 21b | ')),
    '4_4_events': ('### 4.4 Trial chain', ('| T32 | `server_start_failed` |',
                                            '| T33 | `worker_resolved` |',
                                            '| T34 | `anchor_receipt_rejected` |')),
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


def is_ancestor(rev: str, of: str) -> bool | None:
    res = subprocess.run(['git', '-C', str(REPO), 'merge-base', '--is-ancestor', rev, of],
                         capture_output=True)
    return {0: True, 1: False}.get(res.returncode)


def verdict(checks: dict) -> bool:
    """THE aggregation point: True only if ``checks`` is non-empty and every named check
    is exactly True. The witnesses wrap this function to set one check False at a time."""
    return bool(checks) and all(v is True for v in checks.values())


# -- its own text machinery ------------------------------------------------------
def fence_block(raw: bytes, marker: str) -> tuple:
    """(start, end, block): the first ```json fence after ``marker`` (bytes)."""
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


def canonical(obj) -> str:
    """Its own canonical JSON (sorted keys, no spaces, UTF-8, no NaN)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def normalize(text: str) -> str:
    return re.sub(r'\W+', ' ', (text or '').lower()).strip()


def jaccard(a: str, b: str) -> float:
    x, y = set(normalize(a).split()), set(normalize(b).split())
    return len(x & y) / len(x | y) if (x | y) else 1.0


def _tokens(obj) -> set:
    out = set()
    if isinstance(obj, dict):
        for v in obj.values():
            out |= _tokens(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _tokens(v)
    elif isinstance(obj, str) and obj.startswith('<') and '>' in obj:
        out.add(obj[:obj.index('>') + 1])
    return out


# -- the predicate -----------------------------------------------------------------
def verify(before: dict, after: dict, receipt: dict, demoted_commit_protocol: bytes,
           history: dict) -> dict:
    """Every re-derivation for one (pre-image, amendment, receipt) triple.  Pure.
    ``after`` also carries 'artifact' (the committed manifest bytes, b'' if absent).
    ``history``: {'receipts': {path: bytes at its commit}, 'ancestry': {commit: bool|None}}."""
    r = {}
    c = {}
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
    # the one replaced value, from the amended config itself
    try:
        digest = json.loads(after['config'])['llama_cpp']['serving_manifest_sha256']
    except (ValueError, KeyError, TypeError):
        digest = None
    r['serving_manifest_sha256'] = digest
    new_value = ('"serving_manifest_sha256": "%s"}' % digest).encode() if isinstance(digest, str) \
        else b'\x00never'
    rep = receipt.get('replacement') or {}
    c['receipt_lists_the_one_replacement'] = (
        rep.get('key') == CHANGED_KEY and rep.get('old_value') is None
        and rep.get('new_value') == digest
        and sorted(s.get('document') for s in rep.get('sites') or []) == sorted(DOC_KEYS))
    by_doc = {d: [i for i in ins if i.get('document') == d] for d in DOC_KEYS}
    r['insertions_listed'] = {d: len(v) for d, v in by_doc.items()}
    additive, once, replaced = {}, {}, {}
    for d in DOC_KEYS:
        raw = after[d]
        once[d] = all(raw.count(i['text'].encode('utf-8')) == 1 for i in by_doc[d])
        replaced[d] = raw.count(new_value) == 1 and raw.count(OLD_VALUE) == 0
        raw = raw.replace(new_value, OLD_VALUE, 1)
        for i in by_doc[d]:
            raw = raw.replace(i['text'].encode('utf-8'), b'', 1)
        additive[d] = raw == before[d] and after[d] != before[d]
    r['each_insertion_occurs_once'] = once
    r['value_replaced_once'] = replaced
    r['reverting_the_changes_reproduces_the_parent'] = additive
    c['each_insertion_occurs_once'] = bool(ins) and all(once.values())
    c['value_replaced_once_per_document'] = all(replaced.values())
    c['reverting_the_changes_reproduces_the_parent'] = all(additive.values())
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
    for d in ('architecture', 'protocol'):
        try:
            f, e, _ = fence_block(after[d], FENCE_MARKERS[d])
            off = after[d].find(new_value)
            placed['replacement.%s' % d] = off >= 0 and f <= off and off + len(new_value) <= e
        except ValueError:
            placed['replacement.%s' % d] = False
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
        r['value_before'] = fo.get(CHANGED_KEY, 'ABSENT')
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
    c['only_the_serving_manifest_digest_changed_from_null'] = (
        r.get('changed_keys') == [CHANGED_KEY] and r.get('value_before') is None)
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
            'reason_names_the_replaced_value': 'llama_cpp.serving_manifest_sha256' in reason,
            'reason_names_the_new_automatic_aborts': all(
                t in reason for t in ('server_restart_cap', 'unresolved_worker',
                                      'trial_aborted(infrastructure)', 'receipt_mismatch')),
            'reason_names_the_withdrawn_predecessor': (WITHDRAWN_BRANCH in reason
                                                       and 'never applied' in reason),
            'withdrawn_digests_not_in_the_history': not any(
                e.get('sha256') in WITHDRAWN_PROTOCOLS for e in prior)
            and sba.get('sha256') not in WITHDRAWN_PROTOCOLS,
            'nothing_outside_superseded_by_changed': xb == xa,
            'demoted_commit_carries_the_parent_successor':
                sha(demoted_commit_protocol) == PARENT_PINS['protocol'] == sbb.get('sha256'),
        }
    except (ValueError, KeyError, TypeError, IndexError) as e:
        r['cells'] = {'error': str(e)}
    c['cells'] = 'error' not in r['cells'] and all(v is True for v in r['cells'].values())
    # the content of the protocol and of ARCHITECTURE
    content = {}
    for name, (heading, must, must_not) in CONTENT.items():
        try:
            sec = section_text(after['protocol'], heading).decode('utf-8')
            content[name] = all(t in sec for t in must) and not any(t in sec for t in must_not)
        except ValueError:
            content[name] = False
    for name, (heading, must) in ARCH_CONTENT.items():
        try:
            # (the 2.2 layout lines sit inside a ``` fence: section_text skips fenced lines
            # when it looks for headings, and keeps them as text)
            sec = section_text(after['architecture'], heading).decode('utf-8')
            content['architecture.' + name] = all(t in sec for t in must)
        except ValueError:
            content['architecture.' + name] = False
    r['content'] = content
    c['content_in_the_documents'] = bool(content) and all(content.values())
    # the serving manifest artifact
    art = after.get('artifact') or b''
    try:
        obj = json.loads(art.decode('utf-8'))
        canon_ok = art == (canonical(obj) + '\n').encode('utf-8') \
            and canonical(obj) == lab_common.canonical_json(obj)
        art_digest = sha(canonical(obj).encode('utf-8'))
        toks = _tokens(obj)
    except (ValueError, UnicodeDecodeError, TypeError):
        obj, canon_ok, art_digest, toks = None, False, None, set()
    r['artifact'] = {'present': bool(art), 'canonical': canon_ok, 'sha256_canonical': art_digest,
                     'tokens': sorted(toks)}
    c['artifact_is_canonical'] = canon_ok is True
    c['artifact_digest_is_the_config_digest'] = (
        art_digest is not None and art_digest == digest
        and (receipt.get('serving_manifest') or {}).get('sha256_canonical') == digest)
    c['artifact_tokenized_as_the_main_checkout'] = (
        bool(toks) and toks <= {'<REPO>', '<RESULTS>'} and '<REPO>' in toks)
    # receipt / history
    c['receipt_names_the_amended_protocol'] = (
        receipt.get('successor_provenance', {}).get('new_successor') == sha(after['protocol']))
    c['receipt_written_digests_match'] = (
        receipt.get('written', {}).get('config_sha256') == sha(after['config'])
        and receipt.get('written', {}).get('protocol_sha256') == sha(after['protocol'])
        and receipt.get('written', {}).get('architecture_sha256') == sha(after['architecture'])
        and receipt.get('written', {}).get('artifact_file_sha256') == sha(art))
    wp = receipt.get('withdrawn_predecessor') or {}
    c['receipt_names_the_withdrawn_predecessor'] = (
        wp.get('status') == 'withdrawn, not applied' and wp.get('branch') == WITHDRAWN_BRANCH
        and tuple(wp.get('commits') or ()) == WITHDRAWN_COMMITS
        and {x.get('path'): (x.get('commit'), x.get('sha256'))
             for x in wp.get('receipts') or []} == WITHDRAWN_RECEIPTS)
    got_receipts = history.get('receipts') or {}
    c['withdrawn_receipts_are_the_pinned_bytes'] = all(
        sha(got_receipts.get(p, b'')) == d for p, (_, d) in WITHDRAWN_RECEIPTS.items())
    anc = history.get('ancestry') or {}
    c['withdrawn_commits_not_ancestors'] = all(anc.get(x) is False for x in WITHDRAWN_COMMITS)
    r['checks'] = c
    r['all_verified'] = verdict(c)
    return r


def negative_controls(before: dict, after: dict, receipt: dict, demoted: bytes,
                      history: dict, withdrawn_docs: dict) -> dict:
    """The same predicate on five document sets that must NOT verify."""
    out = {}
    out['parent_presented_as_the_amendment'] = verify(
        before, dict(before, artifact=after.get('artifact', b'')), receipt, demoted,
        history)['all_verified']
    p = after['protocol']
    k = p.index(b'## 1. Purpose, scope') - 2
    tampered = dict(after, protocol=p[:k] + (b'X' if p[k:k + 1] != b'X' else b'Y') + p[k + 1:])
    out['one_protocol_byte_changed_outside_the_insertions'] = verify(
        before, tampered, receipt, demoted, history)['all_verified']
    f, e, _ = fence_block(after['architecture'], FENCE_MARKERS['architecture'])
    fb, eb, _ = fence_block(before['architecture'], FENCE_MARKERS['architecture'])
    old_block_arch = after['architecture'][:f] + before['architecture'][fb:eb] + \
        after['architecture'][e:]
    out['amended_config_with_the_parent_architecture_block'] = verify(
        before, dict(after, architecture=old_block_arch), receipt, demoted, history)['all_verified']
    out['withdrawn_predecessor_presented_as_the_amendment'] = verify(
        before, dict(withdrawn_docs, artifact=after.get('artifact', b'')), receipt, demoted,
        history)['all_verified']
    digest = json.loads(after['config'])['llama_cpp']['serving_manifest_sha256']
    new_value = ('"serving_manifest_sha256": "%s"}' % digest).encode()
    reverted = {d: (after[d].replace(new_value, OLD_VALUE, 1) if d in DOC_KEYS else after[d])
                for d in after}
    out['replaced_value_reverted_to_null'] = verify(before, reverted, receipt, demoted,
                                                    history)['all_verified']
    out['every_control_failed'] = not any(v for v in out.values())
    return out


def runtime_recheck(artifact_bytes: bytes, digest: str, commit_id: str) -> dict:
    """--runtime: the committed artifact re-verified against the durable build of the main
    checkout with the harness's own lab_serving_manifest.verify_before_launch, as seen from
    that checkout (assemble_serving_manifest.repo_roots), from a scratch copy; and a copy with
    one library digest changed consistently, which must be refused.  Starts no server."""
    import os
    import tempfile
    import shutil
    sys.path.insert(0, str(HERE))
    import lab_serving_manifest as sm                          # noqa: E402
    import assemble_serving_manifest as asm                    # noqa: E402
    launcher = Path(MAIN_CHECKOUT) / 'work/llama.cpp-build/build/bin/llama-server'
    tmp = Path(tempfile.mkdtemp(prefix='verify_repair_v2_'))
    try:
        good = tmp / 'good' / 'freeze' / 'serving_manifest.json'
        good.parent.mkdir(parents=True)
        good.write_bytes(artifact_bytes)
        obj = json.loads(artifact_bytes)
        lib = obj['libraries'][0]
        new = ('0' if lib['sha256'][0] != '0' else '1') + lib['sha256'][1:]
        for rec in [lib] + [f for f in obj['closure']['files'] if f['path'] == lib['name']] \
                + [m for m in obj['build']['receipt_members'] if m['path'] == lib['name']]:
            rec['sha256'] = new
        bad = tmp / 'bad' / 'freeze' / 'serving_manifest.json'
        bad.parent.mkdir(parents=True)
        bad.write_bytes((canonical(obj) + '\n').encode('utf-8'))
        with asm.repo_roots(MAIN_CHECKOUT):
            _, ok_labels = sm.verify_before_launch(good, digest, launcher=launcher,
                                                   llama_commit=commit_id)
            _, bad_labels = sm.verify_before_launch(bad, sha(canonical(obj).encode()),
                                                    launcher=launcher, llama_commit=commit_id)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {'as_seen_from': MAIN_CHECKOUT, 'labels': ok_labels,
            'mutated_copy_labels': bad_labels, 'ok': ok_labels == [] and bool(bad_labels),
            'loader_environment': sorted(k for k in os.environ
                                         if k.startswith(('GGML_', 'DYLD_')))}


def prompt_recheck(receipt: dict, sources_dir: Path) -> dict:
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
    ap.add_argument('commit', help='the commit that adds the v2 receipt')
    ap.add_argument('--sources-dir', default=None)
    ap.add_argument('--runtime', action='store_true')
    ap.add_argument('--write-receipt', action='store_true')
    args = ap.parse_args(argv)
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', args.commit + '^{commit}'],
                            capture_output=True, text=True, check=True).stdout.strip()
    names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', commit],
                           capture_output=True, text=True, check=True).stdout.split()
    receipts = [n for n in names if re.fullmatch(RECEIPT_RE, n)]
    if len(receipts) != 1 or ARTIFACT not in names:
        print('refusing: %s adds %d v2 receipts and %s the artifact'
              % (commit[:7], len(receipts), 'adds' if ARTIFACT in names else 'does not add'),
              file=sys.stderr)
        return 2
    receipt = json.loads(blob(commit, receipts[0]))
    before = {k: blob(PRE_REV, p) for k, p in DOCS.items()}
    after = {k: blob(commit, p) for k, p in DOCS.items()}
    after['artifact'] = blob(commit, ARTIFACT)
    demoted = blob(DEMOTED_COMMIT, DOCS['protocol'])
    history = {'receipts': {p: blob(c, p) for p, (c, _) in WITHDRAWN_RECEIPTS.items()},
               'ancestry': {c: is_ancestor(c, commit) for c in WITHDRAWN_COMMITS}}
    withdrawn_docs = {k: blob(WITHDRAWN_COMMITS[1], p) for k, p in DOCS.items()}
    result = verify(before, after, receipt, demoted, history)
    controls = negative_controls(before, after, receipt, demoted, history, withdrawn_docs)
    doc = {'schema': 'live_ab/repair_amendment_v2_verification-v1',
           'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'amendment_commit': commit, 'receipt': receipts[0], 'pre_image_revision': PRE_REV,
           'working_tree_equals_amendment_commit': all(
               (REPO / p).read_bytes() == after[k] for k, p in DOCS.items()),
           're_derivation': result, 'negative_controls': controls,
           'nothing_executed': 'git show and file reads only (and --runtime metadata reads)'}
    if args.sources_dir:
        doc['prompt_recheck'] = prompt_recheck(receipt, Path(args.sources_dir))
    if args.runtime:
        cfg = json.loads(after['config'])
        doc['runtime_recheck'] = runtime_recheck(after['artifact'],
                                                 cfg['llama_cpp']['serving_manifest_sha256'],
                                                 cfg['llama_cpp']['commit'])
    ok = (result['all_verified'] and controls['every_control_failed']
          and doc.get('prompt_recheck', {'ok': True})['ok']
          and doc.get('runtime_recheck', {'ok': True})['ok'])
    doc['all_verified'] = ok
    text = json.dumps(doc, indent=1, sort_keys=True) + '\n'
    if args.write_receipt:
        out = REPO / 'results' / 'live_ab' / ('REPAIR_AMENDMENT_V2_VERIFICATION_%s.json'
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
