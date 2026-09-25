"""Independent re-derivation of the pre-outcome amendment v4, from git.

    verify_repair_amendment_v4.py <amendment-commit> [--write-receipt]

<amendment-commit> is the commit that ADDS results/live_ab/REPAIR_AMENDMENT_V4_RECEIPT_<UTC>.json.

It does NOT import the amendment tool (experiments/live_ab_tools/repair_amendment_v4.py).  Every
expectation is its own literal: the pre-image revision and digests, the key of each insertion and
the heading it must lie under (EXPECTED, never the receipt's "section" field), the phrases each
amended section must carry (CONTENT), the rule-block digest, the receipts of amendments v3 and v2,
the seven recorded prior successors.  From `git show` blobs of the pre-image revision (PRE_REV,
56df17f, the commit of amendment v3) and of the commit it re-derives:

  1. the pre-image documents are the reviewed ones (config f158969e, 16,136 bytes; ARCHITECTURE
     2ec71980; protocol 73dd0573; cells.json 192804a4);
  2. the receipt lists exactly the insertion keys of EXPECTED, each once, with EXPECTED's
     document, and its "section" fields agree with EXPECTED;
  3. every change is a pure insertion: each listed text occurs once, and deleting the texts
     reproduces the pre-image ARCHITECTURE and protocol byte for byte; config.json is the
     pre-image byte for byte;
  4. each insertion lies under the heading EXPECTED names (its own heading scanner);
  5. the three configuration blocks are byte-identical to each other and to the pre-image's; no
     CR; the rule-block digest is cbfd1792 (lab_common.rule_block_sha256, the definition);
  6. protocol sections 1, 3 and 11 are byte-identical (its own section scanner);
  7. amendments v3 and v2 kept: each receipt at the commit hashes to its pinned digest, and each
     of their 10 and 27 insertion texts occurs exactly once in its document (none split);
  8. cells.json: the original pin untouched; the new successor is the commit's protocol digest
     and supersedes the original; the seven earlier entries are the recorded ones (canonical
     digests); the eighth is the pre-image's successor minus the moved keys plus its changing
     commit 56df17f (and `git show 56df17f:` of the protocol hashes to 73dd0573); nothing outside
     superseded_by changed;
  9. the amended sections carry what the code does (CONTENT);
 10. the closed names of the prose are the committed code's, read with `ast` from the commit's
     builder blob (no import): the two new labels quoted verbatim in 16, the four labels of v3
     still quoted there, and NOT_NORMAL_END_REASONS named in 3.15 in the code's order;
 11. the receipt names the amended protocol and the written digests.

Every check is NAMED, and all_verified is verdict(checks): True only if every named check is True.
The witnesses (tests_repair_amendment_v4.VerifierTests) pin the list of names, set each one False
in turn at verdict(), and give a real-input variant that makes each check False.

NEGATIVE CONTROLS run by main() (each must FAIL the same predicate): the pre-image presented as the
amendment; one protocol byte changed outside every insertion; one config.json byte changed; the
16 text moved into Appendix A; the 3.15 text removed; the 16 text put inside amendment v3's item 17.

READ-ONLY: git show and file reads.  With --write-receipt it writes
results/live_ab/REPAIR_AMENDMENT_V4_VERIFICATION_<UTC>.json (write-once).  Exit 0 only if everything
verified and every negative control failed.

Prepared and checked by AI agent sessions; not human peer review or author sign-off.
"""

from __future__ import annotations

import argparse
import ast
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
CODE = {'build_live_ab_results': 'experiments/live_ab/build_live_ab_results.py'}
PRE_REV = '56df17f72b17744d89564d0bf05f3fa84f4b8e1d'
PARENT_PINS = {'config': 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7',
               'architecture': '2ec71980de5b6a74df586c5790e6eac7c54dbd79342ae69dab1a01a0bb458190',
               'protocol': '73dd0573955b2ef586e120f2b44558eb0227c70bbca9cbf9225ec4fb5583500c',
               'cells': '192804a4c1538df64a9902430d158e5174269fe2a6c77d8a0be2345304622e58'}
PARENT_CONFIG_BYTES = 16136
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
DEMOTED_COMMIT = PRE_REV
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
V3_RECEIPT = 'results/live_ab/REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218.json'
V3_RECEIPT_SHA256 = 'cd71949e8c460c159e5bde5b4a3d9a843acb3cd116845b6fc91b6042dae6527a'
V2_RECEIPT = 'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
V2_RECEIPT_SHA256 = '66efcb8b64b3e54d890ac70c77686e0678255fe6cba78347fa3a30878e12feff'
#: canonical digests (sha256 of json.dumps(entry, sort_keys=True)) of the seven prior successors
PRIOR_ENTRY_DIGESTS = (
    '06d606dc055340ec2c2607a16c98a4af866e2b27956929a27009084997c3942c',
    'd2857b0d6e292f944f07ac4a5da360dff18df0ecaf617cecff07dd760749d312',
    '33fa39c17e4b63e40e2ebb8241c56ab04866267ec3878ab11037699d0bebabe2',
    'ca1be58e4119a7a2bf95354899c9c4120b4b293d1b6cd84427677aa4405941db',
    'c29dd214f9e160639b13c9638da020b0453ef760002312b23c91e85fe224dd86',
    '41719e17ce181ed5a014a02c317ae51356fdf87088a953a0a08e4550dace3495',
    '121790d25e83616b3ec6fda47b7b83398f8ad8f7f2cb917e61dc5aab6b513958')
FENCE_MARKERS = {'architecture': '### 6.1 Full key list', 'protocol': '## Appendix B.'}
VOCAB = {'1': '## 1. Purpose, scope', '3': '## 3. Task roster', '11': '## 11. The planning study'}
MOVED = ('prior_successors', 'changing_commit_note', 'correction_to_the_owner_report')
RECEIPT_RE = r'results/live_ab/REPAIR_AMENDMENT_V4_RECEIPT_\d{8}_\d{4}\.json'
_S16 = '## 16. What is reported whatever the outcome'
_S315 = '### 3.15 `build_live_ab_results.py`'
#: key -> (document, the heading it must lie under)
EXPECTED = {
    'protocol.16': ('protocol', _S16),
    'architecture.3_15': ('architecture', _S315),
}
#: what each amended section must carry (the behaviour of the code, in the prose's words)
CONTENT = {
    '16_item_18': ('protocol', _S16, (
        '18. *(Amendment 2026-09-25, v4, pre-outcome; root',
        '`reviews/predecision_abort_reporting_ruling_20260925_0710.md`, choice (b).)*',
        '**An abort before any decision is incomplete.**',
        'whatever its cause and whether or not a crossing was logged after its no-decision point',
        'The concrete abort reason is kept beside the result, never inside the label',
        '`none` is reportable only for a `trial_ended` whose resolution passed, at the frozen full horizon',
        'it does not run the verifier', '`horizon_no_decision`',
        'the two labels of this item, the abort first',
        'A decision logged before a later abort keeps every rule of items 16 and 17',
        '`restart_cap.cap_value` and `restart_cap.binding`',
        'the cap of three and its behaviour are unchanged',
        '17. *(Amendment 2026-09-24, v3, pre-outcome; root')),
    'architecture_3_15': ('architecture', _S315, (
        '*Amendment 2026-09-25, v4 (pre-outcome; root', '`normal_end`',
        '`build_live_ab_results.normal_end_reading`', '`restart_cap.cap_value` with `restart_cap.binding`',
        '`build_live_ab_results.restart_cap_binding`', '`restart_cap_config_matches_chain`',
        '`incomplete_reasons`', 'it may not import the verifier')),
}
V3_LABELS = ('DECISION_INVALID_LABEL', 'RESTART_CAP_INCOMPLETE_LABEL', 'ABORT_INCOMPLETE_LABEL',
             'PROVISIONAL_LABEL')
V4_LABELS = ('PREDECISION_ABORT_LABEL', 'INCOMPLETE_CHAIN_LABEL')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


def verdict(checks: dict) -> bool:
    """THE aggregation point: True only if ``checks`` is non-empty and every named check is
    exactly True.  The witnesses wrap this function to set one check False at a time."""
    return bool(checks) and all(v is True for v in checks.values())


# -- its own text machinery ------------------------------------------------------
def fence_block(raw: bytes, marker: str) -> bytes:
    """The first ```json fence after ``marker`` (bytes), without its leading newline."""
    s = raw.index(marker.encode())
    f = raw.index(b'```json', s) + len(b'```json')
    e = raw.index(b'```', f)
    return raw[f:e].lstrip(b'\n')


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


def governing_heading(raw: bytes, offset: int, max_level: int) -> str | None:
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


def module_literal(source: bytes, name: str):
    """The literal value of the module-level assignment ``name`` in ``source`` (ast only)."""
    tree = ast.parse(source.decode('utf-8'))
    for node in tree.body:
        targets = ([node.target] if isinstance(node, ast.AnnAssign)
                   else node.targets if isinstance(node, ast.Assign) else [])
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def _kept_whole(receipt_raw: bytes, pinned: str, n: int, after: dict) -> tuple:
    try:
        doc = json.loads(receipt_raw)
        texts = [(i['document'], i['text'].encode('utf-8')) for i in doc['insertions']]
        whole = [after.get(d, b'').count(t) == 1 for d, t in texts]
    except (ValueError, KeyError, TypeError):
        whole = []
    return whole, (sha(receipt_raw) == pinned and len(whole) == n and all(whole))


# -- the predicate -----------------------------------------------------------------
def verify(before: dict, after: dict, receipt: dict, demoted_commit_protocol: bytes,
           v3_receipt: bytes, v2_receipt: bytes, code: dict) -> dict:
    """Every re-derivation for one (pre-image, amendment, receipt) triple.  Pure.
    ``code``: module name -> the committed source bytes (CODE)."""
    r, c = {}, {}
    r['parent_is_the_reviewed_preimage'] = {k: sha(before[k]) == v for k, v in PARENT_PINS.items()}
    c['parent_is_the_reviewed_preimage'] = (all(r['parent_is_the_reviewed_preimage'].values())
                                            and len(before['config']) == PARENT_CONFIG_BYTES)
    ins = receipt.get('insertions', [])
    keys = [i.get('key') for i in ins]
    r['insertion_keys'] = keys
    c['receipt_lists_exactly_the_expected_insertions'] = (
        sorted(keys) == sorted(EXPECTED) and len(set(keys)) == len(keys)
        and all(i.get('document') == EXPECTED[i['key']][0] for i in ins if i.get('key') in EXPECTED))
    c['receipt_sections_agree_with_the_verifier_headings'] = all(
        str(i.get('section') or '').startswith(EXPECTED[i['key']][1])
        for i in ins if i.get('key') in EXPECTED)
    once, additive = {}, {}
    for d in ('architecture', 'protocol'):
        raw = after[d]
        mine = [i['text'].encode('utf-8') for i in ins if i.get('document') == d]
        once[d] = bool(mine) and all(raw.count(t) == 1 for t in mine)
        for t in mine:
            raw = raw.replace(t, b'', 1)
        additive[d] = raw == before[d] and after[d] != before[d]
    r['each_insertion_occurs_once'] = once
    r['reverting_the_insertions_reproduces_the_parent'] = additive
    c['each_insertion_occurs_once'] = all(once.values())
    c['reverting_the_insertions_reproduces_the_parent'] = all(additive.values())
    c['config_json_is_the_parent'] = after['config'] == before['config']
    placed = {}
    for key, (d, heading) in EXPECTED.items():
        row = next((i for i in ins if i.get('key') == key), None)
        if row is None:
            placed[key] = False
            continue
        off = after[d].find(row['text'].encode('utf-8'))
        level = len(heading) - len(heading.lstrip('#'))
        head = governing_heading(after[d], off, level) if off >= 0 else None
        placed[key] = head is not None and head.startswith(heading)
    r['each_insertion_under_its_heading'] = placed
    c['each_insertion_under_the_verifier_heading'] = bool(placed) and all(placed.values())
    r['cr_bytes'] = {d: after[d].count(b'\r') for d in ('config', 'architecture', 'protocol')}
    c['no_cr_byte'] = not any(r['cr_bytes'].values())
    try:
        blocks = {after['config'], fence_block(after['architecture'], FENCE_MARKERS['architecture']),
                  fence_block(after['protocol'], FENCE_MARKERS['protocol']),
                  fence_block(before['protocol'], FENCE_MARKERS['protocol'])}
        c['three_blocks_byte_identical_and_unchanged'] = len(blocks) == 1
    except ValueError:
        c['three_blocks_byte_identical_and_unchanged'] = False
    try:
        r['rule_block'] = lab_common.rule_block_sha256(json.loads(after['config']))
    except (ValueError, KeyError, TypeError, lab_common.LabError) as e:
        r['rule_block'] = 'error: %s' % e
    c['rule_block_is_cbfd1792'] = r['rule_block'] == RULE_BLOCK
    try:
        r['vocabulary_sections_identical'] = {
            n: section_text(before['protocol'], h) == section_text(after['protocol'], h)
            for n, h in VOCAB.items()}
    except ValueError as e:
        r['vocabulary_sections_identical'] = {'error': str(e)}
    c['vocabulary_sections_identical'] = all(
        v is True for v in r['vocabulary_sections_identical'].values())
    # amendments v3 and v2 kept whole
    r['v3_texts_whole'], c['amendment_v3_kept_whole'] = _kept_whole(v3_receipt, V3_RECEIPT_SHA256,
                                                                    10, after)
    r['v2_texts_whole'], c['amendment_v2_kept_whole'] = _kept_whole(v2_receipt, V2_RECEIPT_SHA256,
                                                                    27, after)
    # cells.json
    try:
        cb, ca = json.loads(before['cells']), json.loads(after['cells'])
        vb, vaa = cb['provenance']['vocabulary_alignment'], ca['provenance']['vocabulary_alignment']
        sbb, sba = vb['superseded_by'], vaa['superseded_by']
        prior = sba.get('prior_successors', [])
        demoted = prior[7] if len(prior) > 7 else {}
        expect = {k: v for k, v in sbb.items() if k not in MOVED}
        got = {k: v for k, v in demoted.items()
               if k not in ('changing_commit_of_this_successor', 'changing_commit_note')}
        note = str(demoted.get('changing_commit_note'))
        xb, xa = json.loads(before['cells']), json.loads(after['cells'])
        xb['provenance']['vocabulary_alignment'].pop('superseded_by')
        xa['provenance']['vocabulary_alignment'].pop('superseded_by')
        r['cells'] = {
            'original_pin_untouched': vaa.get('sha256') == ORIGINAL_PIN == vb.get('sha256'),
            'new_successor_is_the_amended_protocol': sba.get('sha256') == sha(after['protocol']),
            'supersedes_the_original': sba.get('supersedes') == ORIGINAL_PIN,
            'eight_prior_successors': len(prior) == 8,
            'first_seven_are_the_recorded_entries': tuple(
                sha(json.dumps(e, sort_keys=True).encode('utf-8')) for e in prior[:7])
            == PRIOR_ENTRY_DIGESTS,
            'first_seven_unchanged': prior[:7] == sbb.get('prior_successors'),
            'eighth_is_the_parent_successor_whole': got == expect,
            'eighth_names_its_commit':
                demoted.get('changing_commit_of_this_successor') == DEMOTED_COMMIT,
            'eighth_says_how_resolved': ('git show %s:' % DEMOTED_COMMIT[:7] in note
                                         and '/design/protocol_FINAL.md' in note),
            'correction_moved_whole': sba.get('correction_to_the_owner_report')
            == sbb.get('correction_to_the_owner_report'),
            'reason_says_not_an_appendix_b_change':
                str(sba.get('reason', '')).startswith('NOT an Appendix B change'),
            'nothing_outside_superseded_by_changed': xb == xa,
            'demoted_commit_carries_the_parent_successor':
                sha(demoted_commit_protocol) == PARENT_PINS['protocol'] == sbb.get('sha256'),
        }
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as e:
        r['cells'] = {'error': str(e)}
    c['cells'] = 'error' not in r['cells'] and all(v is True for v in r['cells'].values())
    content = {}
    for name, (d, heading, must) in CONTENT.items():
        try:
            sec = ' '.join(section_text(after[d], heading).decode('utf-8').split())
            content[name] = all(' '.join(t.split()) in sec for t in must)
        except ValueError:
            content[name] = False
    r['content'] = content
    c['content_in_the_documents'] = bool(content) and all(content.values())
    # the closed names of the prose, against the committed code
    try:
        src = code['build_live_ab_results']
        s16 = ' '.join(section_text(after['protocol'], _S16).decode('utf-8').split())
        s315 = section_text(after['architecture'], _S315).decode('utf-8')
        reasons = list(module_literal(src, 'NOT_NORMAL_END_REASONS'))
        start = s315.index('(`trial_not_started`')
        named = re.findall(r'`([a-z_]+)`', s315[start:s315.index(');', start)])
        r['code_names'] = {
            'new_labels_quoted_in_16': all('`%s`' % module_literal(src, n) in s16
                                           for n in V4_LABELS),
            'v3_labels_still_quoted_in_16': all('`%s`' % module_literal(src, n) in s16
                                                for n in V3_LABELS),
            'normal_end_reasons_named_in_3_15_in_order': bool(reasons) and named == reasons}
    except (KeyError, ValueError, IndexError, StopIteration, SyntaxError) as e:
        r['code_names'] = {'error': str(e)}
    c['code_names_are_the_committed_code'] = (
        'error' not in r['code_names'] and all(v is True for v in r['code_names'].values()))
    c['receipt_names_the_amended_protocol'] = (
        receipt.get('successor_provenance', {}).get('new_successor') == sha(after['protocol']))
    w = receipt.get('written', {})
    c['receipt_written_digests_match'] = (
        w.get('config_sha256') == sha(after['config'])
        and w.get('protocol_sha256') == sha(after['protocol'])
        and w.get('architecture_sha256') == sha(after['architecture'])
        and w.get('cells_sha256') == sha(after['cells']))
    r['checks'] = c
    r['all_verified'] = verdict(c)
    return r


def negative_controls(before: dict, after: dict, receipt: dict, demoted: bytes,
                      v3_receipt: bytes, v2_receipt: bytes, code: dict) -> dict:
    """The same predicate on six document sets that must NOT verify."""
    out = {}

    def run(docs):
        return verify(before, docs, receipt, demoted, v3_receipt, v2_receipt,
                      code)['all_verified']
    out['parent_presented_as_the_amendment'] = run(dict(before))
    p = after['protocol']
    k = p.index(b'## 1. Purpose, scope') - 2
    out['one_protocol_byte_changed_outside_the_insertions'] = run(
        dict(after, protocol=p[:k] + (b'X' if p[k:k + 1] != b'X' else b'Y') + p[k + 1:]))
    cfg = after['config']
    j = cfg.rindex(b'}')
    out['one_config_byte_changed'] = run(dict(after, config=cfg[:j] + b' ' + cfg[j:]))
    text = {i['key']: i['text'].encode('utf-8') for i in receipt.get('insertions', [])}
    t = text.get('protocol.16', b'\x00')
    q = p.replace(t, b'', 1)
    h = b'## Appendix A. Pre-freeze appendix: values determined by a rule, pinned before the freeze\n'
    m = q.index(h) + len(h)
    out['16_text_moved_into_appendix_a'] = run(dict(after, protocol=q[:m] + t + q[m:]))
    out['3_15_text_removed'] = run(dict(after, architecture=after['architecture'].replace(
        text.get('architecture.3_15', b'\x00'), b'', 1)))
    q = p.replace(t, b'', 1)
    item17 = q.index(b'17. *(Amendment 2026-09-24, v3, pre-outcome; root\n')
    m = q.index(b'\n', item17) + 1
    out['16_text_inside_amendment_v3_text'] = run(dict(after, protocol=q[:m] + t + q[m:]))
    out['every_control_failed'] = not any(v for v in out.values())
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('commit', help='the commit that adds the v4 receipt')
    ap.add_argument('--write-receipt', action='store_true')
    args = ap.parse_args(argv)
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', args.commit + '^{commit}'],
                            capture_output=True, text=True, check=True).stdout.strip()
    names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', commit],
                           capture_output=True, text=True, check=True).stdout.split()
    receipts = [n for n in names if re.fullmatch(RECEIPT_RE, n)]
    if len(receipts) != 1:
        print('refusing: %s adds %d v4 receipts' % (commit[:7], len(receipts)), file=sys.stderr)
        return 2
    receipt = json.loads(blob(commit, receipts[0]))
    before = {k: blob(PRE_REV, p) for k, p in DOCS.items()}
    after = {k: blob(commit, p) for k, p in DOCS.items()}
    demoted = blob(DEMOTED_COMMIT, DOCS['protocol'])
    v3_receipt = blob(commit, V3_RECEIPT)
    v2_receipt = blob(commit, V2_RECEIPT)
    code = {k: blob(commit, p) for k, p in CODE.items()}
    result = verify(before, after, receipt, demoted, v3_receipt, v2_receipt, code)
    controls = negative_controls(before, after, receipt, demoted, v3_receipt, v2_receipt, code)
    doc = {'schema': 'live_ab/repair_amendment_v4_verification-v1',
           'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'amendment_commit': commit, 'receipt': receipts[0], 'pre_image_revision': PRE_REV,
           'working_tree_equals_amendment_commit': all(
               (REPO / p).read_bytes() == after[k] for k, p in DOCS.items()),
           're_derivation': result, 'negative_controls': controls,
           'nothing_executed': 'git show and file reads only'}
    ok = result['all_verified'] and controls['every_control_failed']
    doc['all_verified'] = ok
    text = json.dumps(doc, indent=1, sort_keys=True) + '\n'
    if args.write_receipt:
        out = REPO / 'results' / 'live_ab' / ('REPAIR_AMENDMENT_V4_VERIFICATION_%s.json'
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
