"""Independent re-derivation of the repair amendment (root 20:40 items 2 and 4), from git.

    verify_repair_amendment.py <amendment-commit> [--sources-dir DIR] [--write-receipt]

It does NOT import the amendment tool (experiments/live_ab_tools/repair_amendment.py)
and restates its expectations as its own literals. From `git show` blobs of the
amendment commit and of its parent (<commit>~1) it re-derives:

  1. the parent documents are the reviewed pre-images (config e4d42f5d, 13,917
     bytes; ARCHITECTURE 727003c1; protocol 64ace6d3; cells.json 5c4a28f7);
  2. every change is a pure insertion: the texts the commit's receipt lists occur
     exactly once each, and deleting them reproduces each parent document byte
     for byte;
  3. each insertion lies under the heading the receipt names (its own line
     scanner, not the tool's section_span), and each configuration insertion lies
     inside a ```json fence;
  4. the three-way verbatim contract on BYTES (its own fence extraction), no CR;
  5. the flattened config key diff is exactly the three added keys; the
     `server_supervision` value is the contract literal; the prompts in the config
     are the receipt's texts; `engineering_acquisition` is unchanged and equals
     root's 16:30 table (literals, not run_smoke's constants);
  6. the statistical rule-block digest before and after is cbfd1792
     (lab_common.rule_block_sha256, the canonical definition);
  7. protocol sections 1, 3 and 11 are byte-identical (its own section scanner);
  8. cells.json: the original pin untouched; the new successor is the commit's
     protocol digest and supersedes the original; the five earlier entries are
     unchanged; the sixth is the parent's successor minus the moved keys plus its
     changing commit 48f4d70 (and `git show 48f4d70:` of the protocol hashes to
     64ace6d3); nothing outside superseded_by changed;
  9. optionally (--sources-dir), the prompt similarity maxima recorded in the
     receipt, recomputed with its own normalisation (checked equal to
     lab_data.normalize_prompt on the prompts).

NEGATIVE CONTROLS (each must FAIL the same predicate): the parent documents
presented as the amendment; the amendment with one byte of the protocol changed
outside every insertion; the amended config with the parent ARCHITECTURE block.

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


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


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
def verify(before: dict, after: dict, receipt: dict, demoted_commit_protocol: bytes) -> dict:
    """Every re-derivation for one (parent, amendment, receipt) triple. Pure."""
    r = {}
    r['parent_is_the_reviewed_preimage'] = {k: sha(before[k]) == v for k, v in PARENT_PINS.items()}
    r['parent_config_bytes'] = len(before['config'])
    ins = receipt.get('insertions', [])
    by_doc = {d: [i for i in ins if i['document'] == d] for d in DOC_KEYS}
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
    placed = {}
    for i in ins:
        if i['document'] == 'config' or i.get('section') is None:
            continue
        raw = after[i['document']]
        off = raw.find(i['text'].encode('utf-8'))
        level = len(i['section']) - len(i['section'].lstrip('#'))
        head = governing_heading(raw, off, level) if off >= 0 else None
        ok = head is not None and head.startswith(i['section'])
        if i.get('inside_json_fence'):
            f, e, _ = fence_block(raw, FENCE_MARKERS[i['document']])
            ok = ok and f <= off and off + len(i['text'].encode('utf-8')) <= e
        placed[i['key']] = ok
    r['each_insertion_under_its_heading'] = placed
    r['cr_bytes'] = {d: after[d].count(b'\r') for d in DOC_KEYS}
    try:
        blocks = {'config': after['config'],
                  'architecture': fence_block(after['architecture'], FENCE_MARKERS['architecture'])[2],
                  'protocol': fence_block(after['protocol'], FENCE_MARKERS['protocol'])[2]}
        r['three_blocks_byte_identical'] = len(set(blocks.values())) == 1
    except ValueError:
        r['three_blocks_byte_identical'] = False
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
    try:
        r['vocabulary_sections_identical'] = {
            n: section_text(before['protocol'], h) == section_text(after['protocol'], h)
            for n, h in VOCAB.items()}
    except ValueError as e:
        r['vocabulary_sections_identical'] = {'error': str(e)}
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
            'reason_says_not_appendix_b_only': str(sba.get('reason', '')).startswith(
                'NOT Appendix-B-only'),
            'ruling_cites_the_2040_review': 'reviews/prerun_bundle_go_nogo_20260923_2040.md'
            in str(sba.get('ruling', '')),
            'nothing_outside_superseded_by_changed': xb == xa,
            'demoted_commit_carries_the_parent_successor':
                sha(demoted_commit_protocol) == PARENT_PINS['protocol'] == sbb.get('sha256'),
        }
    except (ValueError, KeyError, TypeError, IndexError) as e:
        r['cells'] = {'error': str(e)}
    r['receipt_names_the_amended_protocol'] = (
        receipt.get('successor_provenance', {}).get('new_successor') == sha(after['protocol']))
    r['receipt_written_digests_match'] = (
        receipt.get('written', {}).get('config_sha256') == sha(after['config'])
        and receipt.get('written', {}).get('protocol_sha256') == sha(after['protocol'])
        and receipt.get('written', {}).get('architecture_sha256') == sha(after['architecture']))
    r['all_verified'] = bool(
        all(r['parent_is_the_reviewed_preimage'].values())
        and r['parent_config_bytes'] == PARENT_CONFIG_BYTES
        and all(r['insertions_listed'].values())
        and all(once.values()) and all(additive.values())
        and placed and all(placed.values())
        and not any(r['cr_bytes'].values()) and r['three_blocks_byte_identical']
        and 'config_error' not in r and r.get('added_keys') == ADDED_KEYS
        and not r.get('removed_keys') and not r.get('changed_keys')
        and r.get('server_supervision_is_the_contract_literal')
        and r.get('prompts_are_the_receipt_texts')
        and r.get('engineering_acquisition_unchanged_and_root_table')
        and r.get('rule_block_before') == RULE_BLOCK == r.get('rule_block_after')
        and 'error' not in r['vocabulary_sections_identical']
        and all(r['vocabulary_sections_identical'].values())
        and 'error' not in r['cells'] and all(r['cells'].values())
        and r['receipt_names_the_amended_protocol'] and r['receipt_written_digests_match'])
    return r


def negative_controls(before: dict, after: dict, receipt: dict, demoted: bytes) -> dict:
    """The same predicate on three documents sets that must NOT verify."""
    out = {}
    out['parent_presented_as_the_amendment'] = verify(before, dict(before), receipt,
                                                      demoted)['all_verified']
    p = after['protocol']
    k = p.index(b'## 1. Purpose, scope') - 2               # a byte outside every insertion
    tampered = dict(after, protocol=p[:k] + (b'X' if p[k:k + 1] != b'X' else b'Y') + p[k + 1:])
    out['one_protocol_byte_changed_outside_the_insertions'] = verify(
        before, tampered, receipt, demoted)['all_verified']
    f, e, _ = fence_block(after['architecture'], FENCE_MARKERS['architecture'])
    fb, eb, _ = fence_block(before['architecture'], FENCE_MARKERS['architecture'])
    old_block_arch = after['architecture'][:f] + before['architecture'][fb:eb] + \
        after['architecture'][e:]
    out['amended_config_with_the_parent_architecture_block'] = verify(
        before, dict(after, architecture=old_block_arch), receipt, demoted)['all_verified']
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
            return {'error': '%s digest differs from the receipt' % name}
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
    ap.add_argument('commit', help='the amendment commit')
    ap.add_argument('--sources-dir', default=None)
    ap.add_argument('--write-receipt', action='store_true')
    args = ap.parse_args(argv)
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', args.commit + '^{commit}'],
                            capture_output=True, text=True, check=True).stdout.strip()
    names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', commit],
                           capture_output=True, text=True, check=True).stdout.split()
    receipts = [n for n in names if re.fullmatch(
        r'results/live_ab/REPAIR_AMENDMENT_RECEIPT_\d{8}_\d{4}\.json', n)]
    if len(receipts) != 1:
        print('refusing: %s adds %d repair amendment receipts' % (commit[:7], len(receipts)),
              file=sys.stderr)
        return 2
    receipt = json.loads(blob(commit, receipts[0]))
    before = {k: blob(commit + '~1', p) for k, p in DOCS.items()}
    after = {k: blob(commit, p) for k, p in DOCS.items()}
    demoted = blob(DEMOTED_COMMIT, DOCS['protocol'])
    result = verify(before, after, receipt, demoted)
    controls = negative_controls(before, after, receipt, demoted)
    doc = {'schema': 'live_ab/repair_amendment_verification-v1',
           'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'amendment_commit': commit, 'receipt': receipts[0],
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
