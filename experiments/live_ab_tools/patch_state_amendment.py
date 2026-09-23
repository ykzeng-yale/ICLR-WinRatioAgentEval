"""The narrow patch-state amendment of protocol_FINAL.md section 2.2 item 1.

Root, 2026-09-23 18:29 (reviews/preparation_wiring_disposition_20260923_1829.md,
freeze blocker 2):

    "The current source-binding rule expects precisely the two patch-modified
     files, while §2.2 still literally says `git status --porcelain` must be
     empty. Before a freeze, make a narrow pre-outcome protocol amendment that
     states the declared source-patch state and exact status/reverse-apply
     checks, or produce a clean derived source revision with equivalent
     provenance. Keep statistical trial rules fixed and record the successor
     pin; do not silently treat a dirty patched checkout as compliant."

Root, issue #11 comment 5800875382 (18:48), as relayed to the implementing
session: "...use the already authorized narrow patch-state amendment route
instead". This tool did not fetch the comment; it runs no network request.

WHAT THIS DOES, AND ONLY THIS
  1. Checks the preconditions, on BYTES: protocol_FINAL.md is the reviewed
     pre-image (the engineering-cap successor 7f666477), config.json and
     ARCHITECTURE_FINAL.md are their reviewed pre-images, no document carries a
     CR byte, the three-way verbatim configuration contract holds, cells.json
     round-trips byte-exactly and records the expected successor, the anchor
     (the last line of item 1) occurs exactly once, begins a line, lies inside
     section 2.2 and is followed directly by item 2, and the facts the inserted
     paragraph states are true of the repository: the lifecycle patch it names
     has the digest it states and modifies exactly two files, and the commit it
     names is the one section 2.2 already pins.
  2. Inserts the paragraph root authorized, INSERTED below, immediately after
     the anchor line and before item 2. A pure insertion: no existing byte
     changes. Only protocol_FINAL.md is written among the three documents.
  3. Verifies the postconditions BEFORE anything is written: the inserted text
     occurs exactly once and deleting it reproduces the pre-image byte for byte;
     it lies inside section 2.2, between the '### 2.2' heading and the '### 2.3'
     heading (lower AND upper bound, with the section scanner of the hardened
     engineering-cap tool); it sits directly after the anchor and directly
     before item 2; no CR byte; the Appendix B block is byte-unchanged and the
     three-way contract still holds; vocabulary sections 1, 3 and 11 (the
     sections the vocabulary pin reads) are byte-identical; the statistical
     rule-block digest is unchanged.
  4. Runs a NEGATIVE CONTROL on scratch copies in a temporary directory: the
     same paragraph moved outside section 2.2 (into 2.3, and into 2.1) must be
     refused by the acceptance predicate of step 3. If the check cannot refuse
     it, nothing is written. The real documents are never used for this.
  5. Records the protocol successor ADDITIVELY in cells.json: the original pin
     is untouched, the current successor (7f666477) moves WHOLE into
     prior_successors with its verified changing commit (0e05d96), and the new
     successor names the new protocol digest.
  6. Writes one write-once receipt.

It refuses, changing nothing, if any precondition fails. It is NOT a freeze, NOT
trial or launch approval, runs no simulation, model, server, build or network
request, and does not examine any llama.cpp checkout: it changes what the
protocol says will be recorded, not whether a checkout satisfies it.

WHAT THE INSERTED TEXT SAYS, AND ONE DIFFERENCE FROM THE 18:29 WORDING
  Root 18:29 named "exact status/reverse-apply checks". The paragraph as
  supplied states a tree comparison instead of a reverse-apply: the working
  tree equals HEAD with the patch applied, compared as git trees built in
  temporary indexes with a temporary object directory. The receipt records
  this; the tool does not rewrite the authorized text.

MODELLED ON experiments/live_ab_tools/engineering_cap_amendment.py AS HARDENED
  bytes only; pinned pre-images; no CR before or after; deletion reproduces the
  pre-image; placement bounded above and below. The witness is
  experiments/live_ab_tools/tests_patch_state_amendment.py, which drives main()
  on scratch copies of the pre-image blobs and never touches the real
  documents.

  SCOPE: the pins are the values for THIS amendment. A reuse must re-point every
  pin at its own reviewed pre-images. What carries over is the set of checks.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
for _p in (str(LAB), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
# The reviewed section scanner (review finding config 1): a section runs from its
# heading to the next heading of the same or a higher level, fenced lines skipped.
from engineering_cap_amendment import block_of, section_span  # noqa: E402

CONFIG = LAB / 'config.json'
ARCH = LAB / 'design' / 'ARCHITECTURE_FINAL.md'
PROTO = LAB / 'design' / 'protocol_FINAL.md'
CELLS = REPO / 'experiments' / 'live_ab_validation' / 'cells.json'
PATCH = REPO / 'experiments' / 'live_ab_serving' / 'live_ab_slot_lifecycle.patch'

ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
#: the protocol pre-image: the engineering-cap successor, as delivered in 0e05d96
PRIOR_SUCCESSOR = '7f6664770b0d88ac5904967d9b8e2225d20932942824cd689278a03a2ee45e53'
PRIOR_SUCCESSOR_COMMIT = '0e05d9658b15c6248a41b094db99e31231943d55'
PRIOR_SUCCESSOR_RECORDED = '18:04'
#: the documents that must NOT change, pinned at their reviewed pre-images
PRIOR_CONFIG_SHA256 = 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824'
PRIOR_ARCH_SHA256 = '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab'
PRIOR_RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
PRIOR_PRIOR_SUCCESSORS = 4
#: what the inserted paragraph states, checked against the repository
PATCH_SHA256 = '88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184'
PATCH_FILES = ('tools/server/server-common.h', 'tools/server/server-context.cpp')
PINNED_LLAMA_COMMIT = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'

SECTION_MARKER = b'### 2.2 Serving software and the manifest fields that are pinned'
NEXT_HEADING = b'### 2.3 Models'
PREV_SECTION_MARKER = b'### 2.1 Hardware, host, working locations'
ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'
#: the sections the vocabulary pin reads (cells.json sections_read [1, 3, 11])
VOCAB_MARKERS = {1: b'## 1. Purpose, scope', 3: b'## 3. Task roster',
                 11: b'## 11. The planning study'}

#: item 1 of section 2.2 ends with this line; item 2 begins right after it
ANCHOR_PREV = (b'   empty and is recorded; cmake options, compiler version, SDK version and '
               b'the SHA-256 of the configure and build logs\n')
ANCHOR = b'   are recorded;\n'
ITEM2_START = b'2. the **serving manifest** is assembled'

#: root's authorized text, verbatim. It begins with an empty line.
INSERTED_LINES = (
    '',
    '   *Amendment 2026-09-23 (pre-outcome; root, `reviews/preparation_wiring_disposition_'
    '20260923_1829.md` and issue #11',
    '   comment 5800875382 -- the narrow patch-state route):* the checkout is the pinned '
    'commit with the lifecycle patch',
    '   `experiments/live_ab_serving/live_ab_slot_lifecycle.patch` (SHA-256',
    '   `88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184`) applied as its '
    '**declared working-tree',
    '   state**, uncommitted, so that `/props.build_info` reports the pinned commit prefix. '
    'For this checkout the',
    '   empty-status requirement above is replaced by three recorded checks: `HEAD` is',
    '   `4fea119de30f6a923992780f6fd5ccb0bee5d47d`; `git status --porcelain` lists exactly '
    'the two files the patch',
    '   modifies; and the working tree equals `HEAD` with the patch applied, compared as git '
    'trees built in temporary',
    '   indexes with a temporary object directory. No statistical rule, estimator, stopping '
    'rule or margin changes.',
)
INSERTED = ''.join(line + '\n' for line in INSERTED_LINES)
INSERTED_BYTES = INSERTED.encode('utf-8')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args) -> str:
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


def insert_once(raw: bytes) -> bytes:
    """The paragraph, immediately after the anchor line. Refuses unless the anchor
    occurs exactly once."""
    n = raw.count(ANCHOR)
    if n != 1:
        raise ValueError('the anchor line occurs %d times' % n)
    i = raw.index(ANCHOR) + len(ANCHOR)
    return raw[:i] + INSERTED_BYTES + raw[i:]


def contract(config: bytes, arch: bytes, proto: bytes) -> dict:
    """The three-way verbatim configuration contract, on bytes: config.json, the
    ARCHITECTURE 6.1 block and the protocol Appendix B block are one block, and
    none of the three files carries a CR byte. The extraction is the one
    tests_lab_e2e.ConfigTests and live_ab_serving/tests_config_contract.py perform."""
    try:
        a, p = block_of(arch, ARCH_MARKER), block_of(proto, PROTO_MARKER)
    except ValueError as e:
        return {'error': str(e), 'holds': False}
    cr = {'config': config.count(b'\r'), 'architecture': arch.count(b'\r'),
          'protocol': proto.count(b'\r')}
    return {'config_equals_architecture_block': config == a,
            'architecture_block_equals_protocol_block': a == p,
            'cr_bytes': cr, 'block_sha256': sha(p), 'block_bytes': len(p),
            'holds': config == a == p and not any(cr.values())}


def vocab_sections(raw: bytes) -> dict:
    """The bytes of protocol sections 1, 3 and 11, by heading (ValueError if a
    heading is missing or not a heading)."""
    out = {}
    for n, marker in VOCAB_MARKERS.items():
        if raw.count(marker) != 1:
            raise ValueError('vocabulary heading %r occurs %d times'
                             % (marker, raw.count(marker)))
        s0, s1 = section_span(raw, marker)
        out[n] = raw[s0:s1]
    return out


def anchor_facts(raw: bytes) -> dict:
    """Where the anchor is in ``raw``: exactly once, begins a line, is item 1's last
    line (after ANCHOR_PREV, before item 2), and lies inside section 2.2."""
    n = raw.count(ANCHOR)
    out = {'anchor_occurrences': n}
    if n != 1:
        return dict(out, anchor_is_item_1_last_line=False, anchor_inside_section_2_2=False)
    i = raw.index(ANCHOR)
    j = i + len(ANCHOR)
    try:
        s0, s1 = section_span(raw, SECTION_MARKER)
    except ValueError as e:
        return dict(out, error=str(e), anchor_is_item_1_last_line=False,
                    anchor_inside_section_2_2=False)
    out.update({
        'anchor_at': i,
        'section_2_2': [s0, s1],
        'anchor_is_item_1_last_line': (raw[i - len(ANCHOR_PREV):i] == ANCHOR_PREV
                                       and raw[j:j + len(ITEM2_START)] == ITEM2_START),
        'anchor_inside_section_2_2': (raw.count(SECTION_MARKER) == 1 and s0 < i
                                      and j <= s1
                                      and raw[s1:s1 + len(NEXT_HEADING)] == NEXT_HEADING),
    })
    return out


def placement(new_raw: bytes) -> dict:
    """Where the inserted text landed in ``new_raw``: inside section 2.2 with a lower
    AND an upper bound (the '### 2.2' heading, the '### 2.3' heading), directly
    after the anchor line, directly before item 2. Byte offsets."""
    i = new_raw.find(INSERTED_BYTES)
    j = i + len(INSERTED_BYTES)
    if i < 0:
        return {'insert_at': -1, 'insertion_inside_section_2_2': False,
                'section_ends_at_2_3_heading': False,
                'directly_after_the_anchor': False, 'directly_before_item_2': False}
    try:
        s0, s1 = section_span(new_raw, SECTION_MARKER)
    except ValueError as e:
        return {'insert_at': i, 'error': str(e), 'insertion_inside_section_2_2': False,
                'section_ends_at_2_3_heading': False,
                'directly_after_the_anchor': False, 'directly_before_item_2': False}
    ends = new_raw[s1:s1 + len(NEXT_HEADING)] == NEXT_HEADING
    return {'insert_at': i, 'insert_end': j, 'section_2_2': [s0, s1],
            'section_heading_occurs_once': new_raw.count(SECTION_MARKER) == 1,
            'section_ends_at_2_3_heading': ends,
            'insertion_inside_section_2_2': (new_raw.count(SECTION_MARKER) == 1 and ends
                                             and s0 < i and j <= s1),
            'directly_after_the_anchor': new_raw[i - len(ANCHOR):i] == ANCHOR,
            'directly_before_item_2': new_raw[j:j + len(ITEM2_START)] == ITEM2_START}


def postconditions(old: dict, new_proto: bytes) -> tuple:
    """(post, ok) for a candidate protocol ``new_proto`` against the pre-image
    documents ``old`` ({'config', 'architecture', 'protocol'} -> bytes). This is
    the acceptance predicate main() applies before writing, and the one the
    negative control must fail."""
    where = placement(new_proto)
    additive = (new_proto.count(INSERTED_BYTES) == 1
                and new_proto.replace(INSERTED_BYTES, b'', 1) == old['protocol'])
    try:
        vocab_old, vocab_new = vocab_sections(old['protocol']), vocab_sections(new_proto)
        vocab = {str(n): vocab_old[n] == vocab_new[n] for n in VOCAB_MARKERS}
    except ValueError as e:
        vocab = {'error': str(e)}
    after = contract(old['config'], old['architecture'], new_proto)
    try:
        appendix_b_same = (block_of(new_proto, PROTO_MARKER)
                           == block_of(old['protocol'], PROTO_MARKER))
    except ValueError:
        appendix_b_same = False
    cfg = json.loads(old['config'])
    post = {
        'protocol_sha256': sha(new_proto),
        'protocol_bytes': len(new_proto),
        'inserted_occurrences': new_proto.count(INSERTED_BYTES),
        'deleting_the_inserted_text_reproduces_the_preimage': additive,
        'insertion_placement': where,
        'protocol_change_is_inside_section_2_2_item_1_only': (
            additive and where['insertion_inside_section_2_2']
            and where['directly_after_the_anchor'] and where['directly_before_item_2']),
        'cr_bytes_after': new_proto.count(b'\r'),
        'appendix_b_block_unchanged': appendix_b_same,
        'three_way_contract_after': after,
        'vocabulary_sections_1_3_11_byte_identical': vocab,
        'rule_block_sha256': lab_common.rule_block_sha256(cfg),
    }
    ok = (post['protocol_change_is_inside_section_2_2_item_1_only']
          and post['inserted_occurrences'] == 1
          and post['cr_bytes_after'] == 0
          and appendix_b_same and after['holds']
          and 'error' not in vocab and all(vocab.values())
          and post['rule_block_sha256'] == PRIOR_RULE_BLOCK
          and post['protocol_sha256'] != sha(old['protocol']))
    return post, ok


def move_outside_2_2(new_proto: bytes, where: str) -> bytes:
    """The negative control: the paragraph taken out of item 1 and put at the start
    of section 2.3's body ('2.3') or at the end of section 2.1 ('2.1')."""
    base = new_proto.replace(INSERTED_BYTES, b'', 1)
    if where == '2.3':
        h = base.index(NEXT_HEADING)
        k = base.index(b'\n', h) + 1
    elif where == '2.1':
        k = base.index(SECTION_MARKER)
    else:
        raise ValueError(where)
    return base[:k] + INSERTED_BYTES + base[k:]


def negative_control(old: dict, new_proto: bytes) -> dict:
    """Scratch copies in a fresh temporary directory, never the real files: the
    pre-image documents and the two moved variants are written there, read back,
    and the acceptance predicate is applied. Each variant must be refused."""
    real = {p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    tmp = Path(tempfile.mkdtemp(prefix='patch_state_negative_control_'))
    out = {'how': ('postconditions() -- the predicate main() applies before writing -- '
                   'on scratch copies in a temporary directory, removed afterwards'),
           'variants': {}}
    try:
        names = {'config': 'config.json', 'architecture': 'ARCHITECTURE_FINAL.md',
                 'protocol': 'protocol_FINAL.md'}
        for k, name in names.items():
            (tmp / name).write_bytes(old[k])
        scratch = {k: (tmp / name).read_bytes() for k, name in names.items()}
        for where in ('2.3', '2.1'):
            p = tmp / ('protocol_FINAL.moved_into_%s.md' % where.replace('.', '_'))
            p.write_bytes(move_outside_2_2(new_proto, where))
            moved = p.read_bytes()
            post, ok = postconditions(scratch, moved)
            pl = post['insertion_placement']
            out['variants']['moved_into_section_' + where] = {
                'sha256': sha(moved),
                'deleting_the_inserted_text_reproduces_the_preimage':
                    post['deleting_the_inserted_text_reproduces_the_preimage'],
                'insertion_inside_section_2_2': pl['insertion_inside_section_2_2'],
                'directly_after_the_anchor': pl['directly_after_the_anchor'],
                'directly_before_item_2': pl['directly_before_item_2'],
                'accepted': ok,
                'refused': not ok,
            }
        out['scratch_copies_unchanged'] = all(
            (tmp / name).read_bytes() == old[k] for k, name in names.items())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out['real_documents_unchanged'] = real == {
        p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    out['every_variant_refused_on_placement'] = all(
        v['refused'] and not v['insertion_inside_section_2_2']
        for v in out['variants'].values())
    return out


def patch_files(patch_raw: bytes) -> list:
    return sorted(set(m.group(1).decode('utf-8') for m in
                      re.finditer(rb'^diff --git a/(\S+) b/\S+$', patch_raw, re.M)))


def inserted_text_is_well_formed() -> dict:
    lines = INSERTED.split('\n')[:-1]
    return {'starts_with_an_empty_line': INSERTED.startswith('\n'),
            'ends_with_a_newline': INSERTED.endswith('\n'),
            'cr_bytes': INSERTED_BYTES.count(b'\r'),
            'lines': len(lines),
            'every_line_empty_or_item_indented': all(l == '' or (l.startswith('   ')
                                                                 and not l.startswith('    '))
                                                     for l in lines),
            'no_trailing_whitespace': all(l == l.rstrip() for l in lines),
            'max_line_chars': max(len(l) for l in lines)}


def main() -> int:
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / ('PATCH_STATE_AMENDMENT_RECEIPT_%s.json'
                                                   % stamp)
    if receipt_path.exists():
        print('refusing: %s exists (write-once)' % receipt_path, file=sys.stderr)
        return 2

    # -- 1. preconditions, on BYTES --------------------------------------------
    old = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
           'protocol': PROTO.read_bytes()}
    cells_raw = CELLS.read_bytes()
    patch_raw = PATCH.read_bytes()
    cells = json.loads(cells_raw)
    va = cells['provenance']['vocabulary_alignment']
    sb = va.get('superseded_by', {})
    before = contract(old['config'], old['architecture'], old['protocol'])
    try:
        s0, s1 = section_span(old['protocol'], SECTION_MARKER)
        pinned_commit_in_2_2 = PINNED_LLAMA_COMMIT.encode() in old['protocol'][s0:s1]
    except ValueError:
        pinned_commit_in_2_2 = False
    form = inserted_text_is_well_formed()
    pre = {
        'protocol_sha256': sha(old['protocol']),
        'protocol_is_the_reviewed_preimage': sha(old['protocol']) == PRIOR_SUCCESSOR,
        'config_sha256': sha(old['config']),
        'config_is_the_reviewed_preimage': sha(old['config']) == PRIOR_CONFIG_SHA256,
        'architecture_sha256': sha(old['architecture']),
        'architecture_is_the_reviewed_preimage': sha(old['architecture']) == PRIOR_ARCH_SHA256,
        'cr_bytes': dict({k: v.count(b'\r') for k, v in old.items()},
                         cells=cells_raw.count(b'\r')),
        'three_way_contract_before': before,
        'anchor': anchor_facts(old['protocol']),
        'inserted_text_already_present': old['protocol'].count(INSERTED_BYTES),
        'inserted_text_form': form,
        'patch_sha256': sha(patch_raw),
        'patch_digest_matches_the_stated_digest': (sha(patch_raw) == PATCH_SHA256
                                                   and PATCH_SHA256 in INSERTED),
        'patch_modifies': patch_files(patch_raw),
        'patch_modifies_exactly_the_two_files': patch_files(patch_raw) == sorted(PATCH_FILES),
        'stated_commit_is_the_one_section_2_2_pins': (pinned_commit_in_2_2
                                                      and PINNED_LLAMA_COMMIT in INSERTED),
        'cells_sha256': sha(cells_raw),
        'cells_round_trips': ((json.dumps(cells, indent=1) + '\n').encode('utf-8')
                              == cells_raw),
        'cells_original_pin': va.get('sha256'),
        'cells_current_successor': sb.get('sha256'),
        'cells_prior_successors': len(sb.get('prior_successors', [])),
        'head': git('rev-parse', 'HEAD'),
    }
    # The pins first. Behind them, the one-shot guard: against documents that
    # already carry the paragraph the pins refuse, and with every pin re-pointed at
    # such documents the "already present" refusal still stops the run.
    pins_ok = (pre['protocol_is_the_reviewed_preimage']
               and pre['config_is_the_reviewed_preimage']
               and pre['architecture_is_the_reviewed_preimage']
               and not any(pre['cr_bytes'].values()) and before['holds']
               and pre['cells_round_trips'] and pre['cells_original_pin'] == ORIGINAL_PIN
               and pre['cells_current_successor'] == PRIOR_SUCCESSOR
               and sb.get('supersedes') == ORIGINAL_PIN
               and pre['cells_prior_successors'] == PRIOR_PRIOR_SUCCESSORS)
    if not pins_ok:
        print('refusing: a precondition failed; NOTHING was written: %s' % json.dumps(pre),
              file=sys.stderr)
        return 2
    if pre['inserted_text_already_present']:
        print('refusing: the amendment is already present; NOTHING was written',
              file=sys.stderr)
        return 2
    rest_ok = (pre['anchor']['anchor_occurrences'] == 1
               and pre['anchor']['anchor_is_item_1_last_line']
               and pre['anchor']['anchor_inside_section_2_2']
               and pre['patch_digest_matches_the_stated_digest']
               and pre['patch_modifies_exactly_the_two_files']
               and pre['stated_commit_is_the_one_section_2_2_pins']
               and form['starts_with_an_empty_line'] and form['ends_with_a_newline']
               and form['cr_bytes'] == 0 and form['every_line_empty_or_item_indented']
               and form['no_trailing_whitespace'])
    if not rest_ok:
        print('refusing: a precondition failed; NOTHING was written: %s' % json.dumps(pre),
              file=sys.stderr)
        return 2

    # -- 2. insert, as bytes -----------------------------------------------------
    try:
        new_proto = insert_once(old['protocol'])
    except ValueError as e:
        print('refusing: %s; NOTHING was written' % e, file=sys.stderr)
        return 2

    # -- 3. postconditions, computed BEFORE anything is written ------------------
    post, ok = postconditions(old, new_proto)
    if not ok:
        print('refusing: a postcondition failed; NOTHING was written: %s'
              % json.dumps(post), file=sys.stderr)
        return 2

    # -- 4. the negative control: the check must be able to refuse ---------------
    control = negative_control(old, new_proto)
    if not (control['every_variant_refused_on_placement']
            and control['scratch_copies_unchanged'] and control['real_documents_unchanged']):
        print('refusing: the negative control did not refuse; NOTHING was written: %s'
              % json.dumps(control), file=sys.stderr)
        return 2

    # -- 5. the successor, additively --------------------------------------------
    verified_commit_hash = sha(subprocess.run(
        ['git', '-C', str(REPO), 'show',
         '%s:experiments/live_ab/design/protocol_FINAL.md' % PRIOR_SUCCESSOR_COMMIT],
        capture_output=True, check=True).stdout)
    if verified_commit_hash != PRIOR_SUCCESSOR:
        print('refusing: %s does not carry the prior successor' % PRIOR_SUCCESSOR_COMMIT,
              file=sys.stderr)
        return 2
    old_sb = sb
    demoted = {k: v for k, v in old_sb.items()
               if k not in ('prior_successors', 'changing_commit_note',
                            'correction_to_the_owner_report')}
    demoted['changing_commit_of_this_successor'] = PRIOR_SUCCESSOR_COMMIT
    demoted['changing_commit_note'] = (
        'Resolved AFTER the fact, when the patch-state amendment landed on top of it: '
        '`git show %s:experiments/live_ab/design/protocol_FINAL.md` hashes to this '
        'successor.' % PRIOR_SUCCESSOR_COMMIT[:7])
    new_sb = {
        'sha256': post['protocol_sha256'],
        'supersedes': ORIGINAL_PIN,
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'reason': (
            'Section 2.2 item 1 ONLY: one dated pre-outcome amendment paragraph (a blank '
            'line and nine text lines) was inserted after the last line of item 1 of '
            'section 2.2 ("Serving software and the manifest fields that are pinned") and '
            'before item 2. It declares the llama.cpp checkout to be the pinned commit '
            '4fea119de30f6a923992780f6fd5ccb0bee5d47d with the lifecycle patch '
            'experiments/live_ab_serving/live_ab_slot_lifecycle.patch (SHA-256 '
            '88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184) applied as '
            'its declared, uncommitted working-tree state, and, for that checkout only, '
            'replaces item 1\'s requirement that `git status --porcelain` be empty by three '
            'recorded checks: HEAD is the pinned commit; the porcelain status lists exactly '
            'the two files the patch modifies; the working tree equals HEAD with the patch '
            'applied, compared as git trees built in temporary indexes with a temporary '
            'object directory. A pure insertion: no existing byte changes, and deleting it '
            'reproduces the prior successor 7f666477 byte for byte. It changes NO CPU cell, '
            'parameter, seed, horizon, estimator, outcome, decision rule, stopping rule, '
            'margin, trial sampling or execution rule, NOT the Appendix B configuration '
            'block (config.json and ARCHITECTURE_FINAL.md are byte-unchanged and the '
            'three-way verbatim contract still holds), and none of the vocabulary sections '
            '1, 3 and 11 this pin reads (verified byte-identical). The statistical '
            'rule-block digest is unchanged.'),
        'ruling': (
            'Root disposition 2026-09-23 18:29 (reviews/preparation_wiring_disposition_'
            '20260923_1829.md, freeze blocker 2): "Before a freeze, make a narrow '
            'pre-outcome protocol amendment that states the declared source-patch state and '
            'exact status/reverse-apply checks, or produce a clean derived source revision '
            'with equivalent provenance. Keep statistical trial rules fixed and record the '
            'successor pin; do not silently treat a dirty patched checkout as compliant." '
            'Root, issue #11 comment 5800875382 (18:48): "...use the already authorized '
            'narrow patch-state amendment route instead" (the fragment as relayed to the '
            'implementing session; the comment itself was not re-fetched, no network). '
            'The pin amendment follows the standing root ruling of 2026-09-22 04:27: '
            '"preserve the original pin; record an explicit post-freeze provenance '
            'amendment ... Do not replace the original sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial or launch approval, not a CPU rerun, and not the other '
            'route root 18:29 allowed (a clean derived source revision). It does not certify '
            'that any checkout or build satisfies the three checks: it fixes what is '
            'recorded, and the checks are performed and receipted by the build and '
            'preflight tooling. It relaxes nothing else in section 2.2: the durable build, '
            'the recorded build facts and every manifest field stand. The third check is a '
            'tree comparison, not the reverse-apply root 18:29 named; the authorized text '
            'says so and is inserted verbatim.'),
        'correction_to_the_owner_report': old_sb['correction_to_the_owner_report'],
        'prior_successors': list(old_sb['prior_successors']) + [demoted],
        'changing_commit_note': (
            'The commit that introduces a successor cannot carry its own hash, so '
            '"changing_commit_of_this_successor" is resolved in a LATER commit. The last '
            'entry above records the one for the %s successor (the engineering caps), '
            'resolved when this amendment landed; this newest successor\'s own commit is '
            'recorded the same way when the next one lands.' % PRIOR_SUCCESSOR_RECORDED),
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

    # -- 6. write, as bytes, then the receipt ------------------------------------
    harness_before = lab_common.harness_file_hashes()
    intended = {PROTO: new_proto, CELLS: new_cells_raw}
    for path, raw in intended.items():
        path.write_bytes(raw)
    reread_config = CONFIG.read_bytes()
    written = {
        'read_back_equals_computed': all(p.read_bytes() == raw for p, raw in intended.items()),
        'protocol_sha256': sha(PROTO.read_bytes()),
        'cells_sha256': sha(CELLS.read_bytes()),
        'config_sha256_after': sha(reread_config),
        'architecture_sha256_after': sha(ARCH.read_bytes()),
        'config_byte_unchanged': reread_config == old['config'],
        'architecture_byte_unchanged': ARCH.read_bytes() == old['architecture'],
        'three_way_contract_on_disk': contract(reread_config, ARCH.read_bytes(),
                                               PROTO.read_bytes()),
        'rule_block_sha256_on_disk': lab_common.rule_block_sha256(json.loads(reread_config)),
        'harness_file_hashes_unchanged': lab_common.harness_file_hashes() == harness_before,
    }
    doc = {
        'schema': 'live_ab.patch_state_amendment_receipt.1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root, reviews/preparation_wiring_disposition_20260923_1829.md freeze '
                      'blocker 2, and issue #11 comment 5800875382 (18:48), the narrow '
                      'patch-state route (quoted in this tool\'s docstring; the comment was '
                      'not fetched by the tool)'),
        'document_amended': str(PROTO.relative_to(REPO)),
        'documents_checked_byte_unchanged': [str(p.relative_to(REPO)) for p in (CONFIG, ARCH)],
        'inserted_text': INSERTED,
        'anchor_line': ANCHOR.decode('utf-8'),
        'difference_from_the_1829_wording': (
            'root 18:29 named "exact status/reverse-apply checks"; the authorized paragraph '
            'states a tree comparison (HEAD plus the patch, built in a temporary index with a '
            'temporary object directory, against the working tree). Inserted verbatim.'),
        'precondition_checked': pre,
        'postcondition_checked': post,
        'negative_control': control,
        'written': written,
        'successor_provenance': {
            'original_pin_untouched': ORIGINAL_PIN,
            'new_successor': post['protocol_sha256'],
            'demoted_successor': PRIOR_SUCCESSOR,
            'demoted_successor_commit_verified': PRIOR_SUCCESSOR_COMMIT,
            'prior_successors_now': len(new_sb['prior_successors'])},
        'prior_versions_retained': {
            'protocol_sha256': PRIOR_SUCCESSOR, 'revision': pre['head'],
            'note': 'recoverable byte-exactly by `git show <revision>:<path>`, and by '
                    'deleting inserted_text from the protocol'},
        'dependent_hashes_that_move': {
            'protocol_sha256': 'moves; recorded as the new successor above. No freeze '
                               'exists, so nothing frozen is invalidated'},
        'dependent_hashes_that_do_not_move': ['config_sha256', 'architecture_sha256',
                                             'rule_block_sha256',
                                             'harness_file_sha256 (every entry)'],
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server, build or network request; no '
                             'llama.cpp checkout examined; text edits and digests only'),
    }
    receipt_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt_path)
    print(json.dumps({'post_ok': ok, 'rule_block': post['rule_block_sha256'][:12],
                      'new_protocol': post['protocol_sha256'],
                      'negative_control_refused': control['every_variant_refused_on_placement']}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
