"""Narrow pre-outcome amendment v4 of the EB1+EB5 repair subset: an abort before any decision is
incomplete, a reportable ``none`` needs a normal end at the frozen full horizon, and the effective
restart cap and its binding are reported.

Why a v4.  Root's ruling ``reviews/predecision_abort_reporting_ruling_20260925_0710.md`` (origin/main
9790043), read on origin/main, chose (b) on finding 9 of the final verification of 8f0b4ae:

  * "a trial aborted before any decision by a non-cap cause, with no crossing, is incomplete and not
    reportable as a scientific no-decision/abstention result."  "Amendment-v3 protocol §16 item 17
    expressly permits that; the code follows the currently written text. The problem is therefore a
    **pre-outcome reporting-rule defect**";
  * "Session60 owns a narrow **v4 additive pre-outcome amendment** and corresponding code/controls.
    Preserve v2/v3 and all prior chains. In the result precedence, invalid decisions remain first.
    For no logged decision, a non-cap ``trial_aborted`` is an incomplete, nonreportable result
    **whether or not a crossing was logged after the abort point**, with the concrete abort reason
    and any not-acted-on crossing retained separately. Keep the existing cap-specific label. A
    genuinely reportable ``none`` requires a verifier-valid normal terminal at the frozen full
    horizon with no eligible crossing; an open or incomplete chain must not masquerade as that
    outcome. A decision validly logged before a later abort retains its existing
    receipt/provisional and truncated-follow-up rules.";
  * "Include the effective cap value and its config binding in the immutable result/provenance
    output in this same narrow amendment ... This is reporting provenance, not a change to the cap
    of three or its operational behavior."; "This ruling does not change the score, decision
    threshold, margin, alpha allocation, enrollment, or stop rule".

The code is the commit before this one (``build_live_ab_results``: ``PREDECISION_ABORT_LABEL``,
``INCOMPLETE_CHAIN_LABEL``, ``normal_end_reading``, ``restart_cap_binding``, the precedence of
``decision_object``, the rows of ``build``); this amendment makes protocol 16 and ARCHITECTURE 3.15
say what it does.

WHAT IT DOES, AND ONLY THIS (the v3 pattern; every refusal goes through :func:`gate`)
  1. Preconditions on BYTES against the current pre-images, the documents amendment v3 wrote
     (56df17f, unchanged on this branch since): config.json f158969e (16,136 bytes, not written by
     v3 either), ARCHITECTURE_FINAL.md 2ec71980, protocol_FINAL.md 73dd0573 (the v3 successor),
     cells.json 192804a4 whose seven prior successors are each the entry as recorded (canonical
     digests), rule block cbfd1792, the three-way configuration contract; every anchor once, at a
     line start, inside its section.
  2. Amendment v3 named and verified: its receipt hashes to its pinned digest on disk and in
     56df17f (``git show``), 56df17f is an ancestor of HEAD, the digests the receipt says it wrote
     are the pre-images, each of its 10 texts is whole, once, in its document; and amendment v2's 27
     texts are whole too (its receipt at its pinned digest).  Neither is edited or superseded: v4
     adds to them.
  3. The prose against the code, at run time (:func:`code_checks`): the labels, the closed reasons
     of a normal end, the precedence, the row keys and the dotted names the new prose uses are read
     back from the code, and the behaviours it states are run on synthetic chains with the code's
     own functions (a non-cap abort with no decision is the abort label, not reportable, with its
     reason beside it; an open chain and an ended chain short of the horizon are the incomplete
     label; a normal end at the horizon holds and each condition refuses it; the cap and its
     binding are read from the configuration, and a missing block gives no value).
  4. PURE INSERTIONS only, two: protocol 16 item 18 directly after item 17 (the last line of the
     v3 text), and a paragraph of ARCHITECTURE 3.15 after its last paragraph.  config.json is not
     written; the configuration blocks of ARCHITECTURE 6.1 and Appendix B are byte-identical;
     sections 1, 3 and 11 byte-identical; no v2 or v3 text is split.
  5. Postconditions computed before anything is written; a negative control on scratch copies
     (each insertion moved out of its section; a configuration byte changed; the 16 text put inside
     amendment v3's item 17; a vocabulary section touched) -- every variant refused.
  6. The successor of cells.json: 73dd0573 demoted whole with its changing commit 56df17f
     (checked: ``git show 56df17f:<protocol>`` hashes to it).
  7. Writes ARCHITECTURE, the protocol and cells.json, reads them back, and writes the write-once
     receipt ``results/live_ab/REPAIR_AMENDMENT_V4_RECEIPT_<UTC>.json``.

It is NOT a freeze, NOT trial, stage or launch approval; it starts no server, runs no model, build
or network request; it changes no statistical rule, score, threshold, margin, alpha, enrollment,
observation or stop rule, and not the cap of three or what it does.  The witnesses are
``tests_repair_amendment_v4.py`` (drive main() on scratch copies of the 56df17f blobs) and the
independent re-derivation ``verify_repair_amendment_v4.py``.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
#: where the three documents and the receipt are written (re-pointed by the witnesses)
REPO = HERE.parent.parent
#: THIS checkout, read only (git and the code the prose describes)
SOURCE_REPO = HERE.parent.parent
LAB = SOURCE_REPO / 'experiments' / 'live_ab'
for _p in (str(LAB), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
import build_live_ab_results                                   # noqa: E402
# The reviewed section scanner: a section runs from its heading to the next heading of the
# same or a higher level, fenced lines skipped.
from engineering_cap_amendment import block_of, section_span   # noqa: E402

REL_CONFIG = 'experiments/live_ab/config.json'
REL_ARCH = 'experiments/live_ab/design/ARCHITECTURE_FINAL.md'
REL_PROTO = 'experiments/live_ab/design/protocol_FINAL.md'
REL_CELLS = 'experiments/live_ab_validation/cells.json'
CONFIG = REPO / REL_CONFIG
ARCH = REPO / REL_ARCH
PROTO = REPO / REL_PROTO
CELLS = REPO / REL_CELLS

#: The pre-images: the documents amendment v3 wrote in 56df17f (unchanged on this branch since).
PRE_REV = '56df17f72b17744d89564d0bf05f3fa84f4b8e1d'
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
PRIOR_SUCCESSOR = '73dd0573955b2ef586e120f2b44558eb0227c70bbca9cbf9225ec4fb5583500c'
PRIOR_SUCCESSOR_COMMIT = PRE_REV
PRIOR_SUCCESSOR_RECORDED = '2026-09-24 22:18'
PRIOR_CONFIG_SHA256 = 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7'
PRIOR_CONFIG_BYTES = 16136
PRIOR_ARCH_SHA256 = '2ec71980de5b6a74df586c5790e6eac7c54dbd79342ae69dab1a01a0bb458190'
PRIOR_CELLS_SHA256 = '192804a4c1538df64a9902430d158e5174269fe2a6c77d8a0be2345304622e58'
PRIOR_RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
PRIOR_PRIOR_SUCCESSORS = 7
#: the seven prior successors of the pre-image, in order: (sha256 field, canonical digest of
#: the whole entry, sha256(json.dumps(entry, sort_keys=True)) -- the values
#: experiments/live_ab_validation/tests_validation.py PinSuccessorAmendmentTests records)
PRIOR_ENTRIES = (
    ('b1ff97cc163ce7ea121ebd578a4c37de09d5ed7223f2029e5d56118cdc790822',
     '06d606dc055340ec2c2607a16c98a4af866e2b27956929a27009084997c3942c'),
    ('d63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d',
     'd2857b0d6e292f944f07ac4a5da360dff18df0ecaf617cecff07dd760749d312'),
    ('0e1bcb710ce2c13a06a243a7c3034d6bec55389d4de45dce569a7dee15af0284',
     '33fa39c17e4b63e40e2ebb8241c56ab04866267ec3878ab11037699d0bebabe2'),
    ('f75de3235ae0431b727cf7c24b09927204a1da8c5424e14ea428dbfea256f48b',
     'ca1be58e4119a7a2bf95354899c9c4120b4b293d1b6cd84427677aa4405941db'),
    ('7f6664770b0d88ac5904967d9b8e2225d20932942824cd689278a03a2ee45e53',
     'c29dd214f9e160639b13c9638da020b0453ef760002312b23c91e85fe224dd86'),
    ('64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b',
     '41719e17ce181ed5a014a02c317ae51356fdf87088a953a0a08e4550dace3495'),
    ('6c0ebf2faa7515ff27f01188d9f1e487c928c63373f451dea51f06a8cdacaab9',
     '121790d25e83616b3ec6fda47b7b83398f8ad8f7f2cb917e61dc5aab6b513958'),
)
#: Amendment v3: its write-once receipt (kept, not edited, not superseded)
V3_RECEIPT_REL = 'results/live_ab/REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218.json'
V3_RECEIPT = REPO / V3_RECEIPT_REL
V3_RECEIPT_SHA256 = 'cd71949e8c460c159e5bde5b4a3d9a843acb3cd116845b6fc91b6042dae6527a'
V3_INSERTIONS = 10
#: Amendment v2 (474f9d8): its texts must stay whole too ("Preserve v2/v3")
V2_RECEIPT_REL = 'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
V2_RECEIPT = REPO / V2_RECEIPT_REL
V2_RECEIPT_SHA256 = '66efcb8b64b3e54d890ac70c77686e0678255fe6cba78347fa3a30878e12feff'
V2_INSERTIONS = 27

RECEIPT_PREFIX = 'REPAIR_AMENDMENT_V4_RECEIPT_'
ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'
#: the sections the vocabulary pin reads (cells.json sections_read [1, 3, 11])
VOCAB_MARKERS = {1: b'## 1. Purpose, scope', 3: b'## 3. Task roster',
                 11: b'## 11. The planning study'}
R0710 = '`reviews/predecision_abort_reporting_ruling_20260925_0710.md`'


def _lines(*lines: str) -> str:
    return ''.join(line + '\n' for line in lines)


# ---------------------------------------------------------------------------
# The prose.  Each is a pure insertion at one anchor, inside one section; the protocol text is
# anchored on the LAST line of amendment v3's item 17, so no v3 text is split.  Each states what
# the code of this branch PERFORMS (:func:`code_checks` reads the names back and runs the
# behaviours on synthetic chains).
# ---------------------------------------------------------------------------
P4_16 = _lines(
    '18. *(Amendment 2026-09-25, v4, pre-outcome; root',
    '    %s, choice (b).)* **An abort before any decision is' % R0710,
    '    incomplete.** Item 17 is amended as follows, and nothing else in it changes. With no logged decision, a trial',
    '    whose terminal record is `trial_aborted` is incomplete and not reportable, whatever its cause and whether or',
    '    not a crossing was logged after its no-decision point: it is not a null result and not an abstention. Its',
    '    result is `incomplete: aborted before any decision (no decision; not a null result, not an abstention)`;',
    '    the cap keeps its own label of item 17 (case (a) of 5.3), and a crossing logged after the point and not',
    '    acted on keeps its label of item 17. The concrete abort reason is kept beside the result, never inside the',
    '    label (`decision.json` `normal_end`, the program summary\'s `abort_reason`), and so is any crossing that was',
    '    not acted on (`crossing_not_acted_on`). With no logged decision and no terminal abort, a chain that is not a',
    '    normal end at the frozen full horizon - no terminal record, a `trial_ended` short of `N_P`, a resolution of',
    '    14.6 that did not pass, a no-decision point in the chain - is `incomplete: no decision and no normal end at',
    '    the frozen full horizon (no decision; not a null result, not an abstention)`, not reportable. With no logged',
    '    decision, `none` is reportable only for a `trial_ended` whose resolution passed, at the frozen full horizon',
    '    (`N_P` pairs enrolled, `N_P` the chain\'s `n_pairs_max`, and the last look at `N_P` with every pair',
    '    collapsed), with no no-decision point and no crossing. The results builder reads that from the chain; it',
    '    does not run the verifier, whose FAIL is reported as before. At that look the frozen rule of 8.4 logs',
    '    `horizon_no_decision`, so a normal full-horizon trial with no crossing reports that logged result. The order',
    '    of item 17 is now, first match wins: `LIVE_DECISION_INVALID (harness defect)`; the cap\'s label; the label of',
    '    a crossing not acted on; the two labels of this item, the abort first; the provisional label; the logged',
    '    decision, or `none` as just stated. A decision logged before a later abort keeps every rule of items 16',
    '    and 17: its receipt, its provisional state and its truncated follow-up. The effective restart cap and its',
    '    binding are reported for every trial (`decision.json` `restart_cap.cap_value` and `restart_cap.binding`;',
    '    the program summary\'s `restart_cap`, and `restart_cap_value` per trial): the value the one reader of 5.3',
    '    reads from `server_supervision` of the frozen `config.json`, the block and its canonical SHA-256, the file',
    '    and the SHA-256 of its bytes, and whether that is the `config_sha256` the chain\'s `trial_started`',
    '    recorded. This is reporting provenance only: the cap of three and its behaviour are unchanged. No score,',
    '    decision threshold, margin, alpha allocation, enrollment or stop rule changes.',
)
A4_3_15 = _lines(
    '',
    '*Amendment 2026-09-25, v4 (pre-outcome; root %s;' % R0710,
    'protocol 16 item 18).* `decision.json` also carries `normal_end` (`build_live_ab_results.normal_end_reading`): the',
    'terminal record, its seq and abort reason, its resolution verdict, the frozen horizon and the chain\'s `n_pairs_max`,',
    'the pairs enrolled, the last look, the no-decision point, and the closed reasons the chain is not a normal end at the',
    'frozen full horizon (`trial_not_started`, `no_terminal_record`, `trial_aborted`, `events_after_terminal_record`,',
    '`resolution_absent`, `resolution_not_pass`, `no_decision_point_in_chain`, `horizon_unknown`,',
    '`horizon_not_the_chain_horizon`, `enrolment_short_of_horizon`, `no_look`, `last_look_short_of_horizon`,',
    '`last_look_not_all_collapsed`); and `restart_cap.cap_value` with `restart_cap.binding`',
    '(`build_live_ab_results.restart_cap_binding`: the value `lab_common.server_supervision_cap` reads, the',
    '`server_supervision` block and its canonical SHA-256, `freeze/config.json` and the SHA-256 of its bytes, the chain\'s',
    '`trial_started.config_sha256` and whether they agree). `program_summary.json` carries `restart_cap` (the same',
    'binding) and, per trial, `restart_cap_value`, `restart_cap_config_matches_chain`, `abort_reason`,',
    '`crossing_not_acted_on` when a crossing was not acted on, and `incomplete_reasons` with either label of protocol 16',
    'item 18. The builder reads the chain-borne terminal evidence only; it may not import the verifier (3.16).',
)


class Insertion:
    """One pure insertion: ``text`` goes directly ``side`` ('after' / 'after-line') the unique
    ``anchor`` of document ``doc``, inside the section headed ``section`` (whose upper bound
    must be the heading ``section_end``)."""

    def __init__(self, key, doc, anchor, side, text, section, section_end):
        self.key, self.doc, self.anchor, self.side = key, doc, anchor, side
        self.text = text.encode('utf-8') if isinstance(text, str) else text
        self.section, self.section_end = section, section_end

    def describe(self) -> dict:
        return {'key': self.key, 'document': self.doc, 'side': self.side,
                'anchor': self.anchor.decode('utf-8'),
                'section': self.section.decode('utf-8'),
                'section_upper_bound': self.section_end.decode('utf-8'),
                'bytes': len(self.text), 'sha256': sha(self.text),
                'text': self.text.decode('utf-8')}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_S16 = (b'## 16. What is reported whatever the outcome', b'## Appendix A.')
_A315 = (b'### 3.15 `build_live_ab_results.py`', b'### 3.16 Import isolation matrix')

INSERTIONS = (
    Insertion('protocol.16', 'protocol', b'    `decision` in `decision.json`.\n', 'after', P4_16,
              *_S16),
    Insertion('architecture.3_15', 'architecture',
              b'`decision_code_defect` (P11) and drops claims 2-5 and 7 of the affected trials '
              b'(protocol 6.4 row 24).\n', 'after', A4_3_15, *_A315),
)
DOC_NAMES = ('architecture', 'protocol')
ALL_DOCS = ('config', 'architecture', 'protocol')


def git(*args) -> str:
    return subprocess.run(['git', '-C', str(SOURCE_REPO)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


def git_blob(rev: str, path: str) -> bytes:
    return subprocess.run(['git', '-C', str(SOURCE_REPO), 'show', '%s:%s' % (rev, path)],
                          capture_output=True, check=True).stdout


def git_is_ancestor(rev: str, of: str) -> bool | None:
    """True / False from ``git merge-base --is-ancestor``; None when git cannot answer."""
    res = subprocess.run(['git', '-C', str(SOURCE_REPO), 'merge-base', '--is-ancestor', rev, of],
                         capture_output=True)
    return {0: True, 1: False}.get(res.returncode)


# ---------------------------------------------------------------------------
# Anchors and insertion (the v3 machinery, unchanged)
# ---------------------------------------------------------------------------
def anchor_offset(raw: bytes, ins: Insertion) -> int:
    """Where ``ins.text`` goes in ``raw``: the anchor must occur exactly once and begin a line;
    'after' = directly after the anchor (which ends with a newline); 'after-line' = directly
    after the whole line the anchor begins.  ValueError otherwise."""
    n = raw.count(ins.anchor)
    if n != 1:
        raise ValueError('%s: the anchor occurs %d times' % (ins.key, n))
    i = raw.index(ins.anchor)
    if i and raw[i - 1:i] != b'\n':
        raise ValueError('%s: the anchor does not begin a line' % ins.key)
    if ins.side == 'after':
        if not ins.anchor.endswith(b'\n'):
            raise ValueError('%s: an "after" anchor must be whole lines' % ins.key)
        return i + len(ins.anchor)
    if ins.side == 'after-line':
        nl = raw.find(b'\n', i)
        if nl < 0:
            raise ValueError('%s: the anchor line does not end' % ins.key)
        return nl + 1
    raise ValueError(ins.side)


def anchor_facts(raw: bytes, ins: Insertion) -> dict:
    """The precondition on one anchor in the PRE-image: exactly once, at a line start, inside
    its section; and the text is not there yet."""
    try:
        off = anchor_offset(raw, ins)
        s0, s1 = section_span(raw, ins.section)
        row = {'anchor_occurrences': 1, 'offset': off,
               'inside_its_section': (raw.count(ins.section) == 1 and s0 < off <= s1
                                      and raw[s1:s1 + len(ins.section_end)] == ins.section_end)}
    except ValueError as e:
        row = {'anchor_occurrences': raw.count(ins.anchor), 'error': str(e),
               'inside_its_section': False}
    row['text_already_present'] = raw.count(ins.text)
    return row


def insert_all(old: dict) -> dict:
    """Every insertion, as bytes, at offsets computed in the PRE-image; config.json is returned
    as it was.  Raises ValueError if an anchor is absent, duplicated or not at a line start."""
    out = {'config': old['config']}
    for doc in DOC_NAMES:
        raw = old[doc]
        spots = sorted(((anchor_offset(raw, ins), n, ins) for n, ins in enumerate(INSERTIONS)
                        if ins.doc == doc), key=lambda t: (t[0], t[1]))
        pieces, last = [], 0
        for off, _, ins in spots:
            pieces += [raw[last:off], ins.text]
            last = off
        pieces.append(raw[last:])
        out[doc] = b''.join(pieces)
    return out


def remove_all(new_raw: bytes, doc: str) -> bytes:
    """Undo: every insertion of ``doc`` deleted (once)."""
    for ins in INSERTIONS:
        if ins.doc == doc:
            new_raw = new_raw.replace(ins.text, b'', 1)
    return new_raw


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def gate(name: str, checks: dict) -> bool:
    """THE aggregation point of every acceptance predicate: ``name`` passes only if ``checks``
    is non-empty and each named check in it is exactly True.

    Every refusal of main() on a computed condition goes through a call of this function, with
    the checks named.  The witness module (tests_repair_amendment_v4.GateTests) wraps it to set
    ONE named check False on the pristine inputs, on which every other check is True, and
    requires main() to refuse; which REAL input makes each check False is listed, check by
    check, in the witness module's LIVENESS table."""
    return bool(checks) and all(v is True for v in checks.values())


def contract(config: bytes, arch: bytes, proto: bytes) -> dict:
    """The three-way verbatim configuration contract, on bytes (the extraction of
    tests_lab_e2e.ConfigTests and live_ab_serving/tests_config_contract.py)."""
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
    out = {}
    for n, marker in VOCAB_MARKERS.items():
        if raw.count(marker) != 1:
            raise ValueError('vocabulary heading %r occurs %d times' % (marker, raw.count(marker)))
        s0, s1 = section_span(raw, marker)
        out[n] = raw[s0:s1]
    return out


def placement(new_raw: bytes, ins: Insertion) -> dict:
    """Where ``ins.text`` landed in ``new_raw``: once; inside its section with a lower AND an
    upper bound; directly beside its anchor."""
    i = new_raw.find(ins.text)
    j = i + len(ins.text)
    out = {'occurrences': new_raw.count(ins.text), 'insert_at': i}
    if ins.side == 'after':
        out['directly_beside_the_anchor'] = i >= 0 and new_raw[i - len(ins.anchor):i] == ins.anchor
    else:                                                      # after-line
        k = new_raw.rfind(b'\n', 0, max(i - 1, 0)) + 1
        out['directly_beside_the_anchor'] = (i > 0 and new_raw[i - 1:i] == b'\n'
                                             and new_raw[k:k + len(ins.anchor)] == ins.anchor)
    try:
        s0, s1 = section_span(new_raw, ins.section)
    except ValueError as e:
        out.update(error=str(e), inside_its_section=False)
        return out
    ends = new_raw[s1:s1 + len(ins.section_end)] == ins.section_end
    out.update({'section': [s0, s1], 'section_ends_at_its_upper_bound': ends,
                'inside_its_section': (i >= 0 and new_raw.count(ins.section) == 1 and ends
                                       and s0 < i and j <= s1)})
    return out


def texts_of(receipt: dict) -> list:
    """[(key, document, text bytes)] of an earlier amendment's insertions, from its receipt."""
    return [(str(i.get('key')), str(i.get('document')), str(i.get('text', '')).encode('utf-8'))
            for i in (receipt.get('insertions') or [])]


def texts_intact(docs: dict, receipt: dict) -> dict:
    """Each insertion text of an earlier amendment occurs exactly once in its document (none
    split, none doubled)."""
    return {key: docs.get(doc, b'').count(text) == 1 for key, doc, text in texts_of(receipt)}


def postconditions(old: dict, new: dict, v3_receipt: dict, v2_receipt: dict) -> tuple:
    """(post, ok) for candidate documents ``new`` against the pre-images ``old``
    ({'config', 'architecture', 'protocol'} -> bytes).  The acceptance predicate main()
    applies before writing, and the one the negative control must fail."""
    where = {ins.key: placement(new[ins.doc], ins) for ins in INSERTIONS}
    additive = {d: (all(new[d].count(ins.text) == 1 for ins in INSERTIONS if ins.doc == d)
                    and remove_all(new[d], d) == old[d]) for d in DOC_NAMES}
    try:
        vo, vn = vocab_sections(old['protocol']), vocab_sections(new['protocol'])
        vocab = {str(n): vo[n] == vn[n] for n in VOCAB_MARKERS}
    except ValueError as e:
        vocab = {'error': str(e)}
    after = contract(new['config'], new['architecture'], new['protocol'])
    try:
        blocks_same = (block_of(old['architecture'], ARCH_MARKER)
                       == block_of(new['architecture'], ARCH_MARKER)
                       and block_of(old['protocol'], PROTO_MARKER)
                       == block_of(new['protocol'], PROTO_MARKER))
    except ValueError:
        blocks_same = False
    try:
        rb_after = lab_common.rule_block_sha256(json.loads(new['config']))
    except (ValueError, TypeError, KeyError, lab_common.LabError):
        rb_after = None
    v3_whole = texts_intact(new, v3_receipt)
    v2_whole = texts_intact(new, v2_receipt)
    post = {
        'config_sha256': sha(new['config']), 'config_bytes': len(new['config']),
        'architecture_sha256': sha(new['architecture']),
        'protocol_sha256': sha(new['protocol']), 'protocol_bytes': len(new['protocol']),
        'reverting_the_insertions_reproduces_each_preimage': additive,
        'insertion_placement': where,
        'every_insertion_inside_its_section_beside_its_anchor': {
            k: bool(v.get('occurrences') == 1 and v.get('inside_its_section')
                    and v.get('directly_beside_the_anchor')) for k, v in where.items()},
        'cr_bytes_after': {d: new[d].count(b'\r') for d in ALL_DOCS},
        'three_way_contract_after': after,
        'configuration_blocks_byte_identical': blocks_same,
        'vocabulary_sections_1_3_11_byte_identical': vocab,
        'rule_block_sha256_after': rb_after,
        'v3_insertions_intact': v3_whole,
        'v2_insertions_intact': v2_whole,
    }
    post['gate'] = {
        'reverting_the_insertions_reproduces_each_preimage': all(additive.values()),
        'every_insertion_inside_its_section_beside_its_anchor':
            all(post['every_insertion_inside_its_section_beside_its_anchor'].values()),
        'no_cr_byte_after': not any(post['cr_bytes_after'].values()),
        'three_way_contract_after': after['holds'] is True,
        'config_json_byte_identical': new['config'] == old['config'],
        'configuration_blocks_byte_identical': blocks_same is True,
        'vocabulary_sections_1_3_11_byte_identical':
            'error' not in vocab and all(v is True for v in vocab.values()),
        'rule_block_after_is_the_pin': rb_after == PRIOR_RULE_BLOCK,
        'v3_insertions_intact': len(v3_whole) == V3_INSERTIONS and all(v3_whole.values()),
        'v2_insertions_intact': len(v2_whole) == V2_INSERTIONS and all(v2_whole.values()),
        'architecture_and_protocol_changed': all(new[d] != old[d] for d in DOC_NAMES),
    }
    ok = gate('postconditions', post['gate'])
    return post, ok


def move_out(new: dict, ins: Insertion) -> dict:
    """A negative-control variant: ``ins.text`` taken out of its place and put at the start of
    the next section's body, just outside its bound."""
    raw = new[ins.doc]
    base = raw.replace(ins.text, b'', 1)
    h = base.index(ins.section_end)
    k = base.index(b'\n', h) + 1
    out = dict(new)
    out[ins.doc] = base[:k] + ins.text + base[k:]
    return out


def extra_variants(new: dict) -> dict:
    """The negative-control variants that are not a moved insertion: a configuration byte
    changed (config.json only); the 16 text placed inside amendment v3's own item 17 (after
    its first line); the 16 text also copied into vocabulary section 1."""
    out = {}
    cfg = new['config']
    k = cfg.rindex(b'}')
    out['config_byte_changed'] = dict(new, config=cfg[:k] + b' ' + cfg[k:])
    ins = next(i for i in INSERTIONS if i.key == 'protocol.16')
    p = new['protocol'].replace(ins.text, b'', 1)
    item17 = p.index(b'17. *(Amendment 2026-09-24, v3, pre-outcome; root\n')
    nl = p.index(b'\n', item17) + 1
    out['v3_text_split'] = dict(new, protocol=p[:nl] + ins.text + p[nl:])
    p = new['protocol']
    s0, _ = section_span(p, VOCAB_MARKERS[1])
    nl = p.index(b'\n', s0) + 1
    out['vocabulary_section_1_touched'] = dict(new, protocol=p[:nl] + ins.text + p[nl:])
    return out


def negative_control(old: dict, new: dict, v3_receipt: dict, v2_receipt: dict) -> dict:
    """Scratch copies in a fresh temporary directory, never the real files: the pre-images and
    each variant are written there, read back, and the acceptance predicate is applied.  Each
    variant must be refused; the checks each one fails are recorded."""
    real = {p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    tmp = Path(tempfile.mkdtemp(prefix='repair_amendment_v4_negative_control_'))
    out = {'how': ('postconditions() -- the predicate main() applies before writing -- on '
                   'scratch copies in a temporary directory, removed afterwards; one variant per '
                   'insertion, moved just outside its section, and three more: a byte of '
                   'config.json changed, the 16 text put inside amendment v3\'s item 17, the 16 '
                   'text also put into vocabulary section 1'),
           'variants': {}}
    names = {'config': 'config.json', 'architecture': 'ARCHITECTURE_FINAL.md',
             'protocol': 'protocol_FINAL.md'}
    try:
        for k, name in names.items():
            (tmp / name).write_bytes(old[k])
        scratch = {k: (tmp / name).read_bytes() for k, name in names.items()}
        variants = {'moved.' + ins.key: move_out(new, ins) for ins in INSERTIONS}
        variants.update(extra_variants(new))
        for vname, docs in variants.items():
            read = {}
            for k, name in names.items():
                p = tmp / ('%s.%s' % (name, vname))
                p.write_bytes(docs[k])
                read[k] = p.read_bytes()
            post, ok = postconditions(scratch, read, v3_receipt, v2_receipt)
            out['variants'][vname] = {
                'sha256': {k: sha(v) for k, v in read.items()},
                'failed_checks': sorted(k for k, v in post['gate'].items() if v is not True),
                'accepted': ok, 'refused': not ok}
        out['scratch_copies_unchanged'] = all(
            (tmp / name).read_bytes() == old[k] for k, name in names.items())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out['real_documents_unchanged'] = real == {
        p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    out['variants_run'] = len(out['variants'])
    moved = {k: v for k, v in out['variants'].items() if k.startswith('moved.')}
    out['every_moved_variant_refused_on_placement'] = len(moved) == len(INSERTIONS) and all(
        v['refused'] and 'every_insertion_inside_its_section_beside_its_anchor'
        in v['failed_checks'] for v in moved.values())
    ex = out['variants']
    out['config_variant_refused'] = bool(ex.get('config_byte_changed', {}).get('refused')) and \
        'config_json_byte_identical' in ex['config_byte_changed']['failed_checks']
    out['v3_split_variant_refused'] = bool(ex.get('v3_text_split', {}).get('refused')) and \
        'v3_insertions_intact' in ex['v3_text_split']['failed_checks']
    out['vocabulary_variant_refused'] = bool(
        ex.get('vocabulary_section_1_touched', {}).get('refused')) and \
        'vocabulary_sections_1_3_11_byte_identical' in \
        ex['vocabulary_section_1_touched']['failed_checks']
    return out


def inserted_text_form() -> dict:
    """Every inserted text: ends with a newline, no CR, ASCII only, no trailing whitespace, no
    ``` and no heading line (either would move a section or fence bound), prose lines at most
    120 characters; no anchor of any insertion."""
    out = {}
    for ins in INSERTIONS:
        t = ins.text.decode('utf-8')
        lines = t.split('\n')[:-1]
        prose = [ln for ln in lines if not ln.startswith('|')]
        out[ins.key] = {
            'ends_with_a_newline': t.endswith('\n'),
            'cr_bytes': ins.text.count(b'\r'),
            'non_ascii': sorted(set(c for c in t if ord(c) > 127)),
            'no_trailing_whitespace': all(ln == ln.rstrip() for ln in lines),
            'no_backtick_fence': '```' not in t,
            'no_heading_line': not any(ln.startswith('#') for ln in lines),
            'max_prose_line_chars': max([len(ln) for ln in prose] or [0]),
            'contains_no_anchor': not any(o.anchor in ins.text for o in INSERTIONS),
        }
    ok = all(v['ends_with_a_newline'] and v['cr_bytes'] == 0 and v['no_trailing_whitespace']
             and v['no_backtick_fence'] and v['no_heading_line']
             and v['max_prose_line_chars'] <= 120 and v['contains_no_anchor']
             and not v['non_ascii'] for v in out.values())
    return {'per_insertion': out, 'ok': ok}


# ---------------------------------------------------------------------------
# The prose against the code
# ---------------------------------------------------------------------------
#: the builder's result labels in the order of item 17 as item 18 amends it (first match wins)
ORDER = ('DECISION_INVALID_LABEL', 'RESTART_CAP_INCOMPLETE_LABEL', 'ABORT_INCOMPLETE_LABEL',
         'PREDECISION_ABORT_LABEL', 'INCOMPLETE_CHAIN_LABEL', 'PROVISIONAL_LABEL')
#: the two labels this amendment adds, quoted verbatim in item 18
NEW_LABELS = ('PREDECISION_ABORT_LABEL', 'INCOMPLETE_CHAIN_LABEL')
#: the summary-row keys and decision.json keys the prose names, as build / decision_object write
ROW_KEYS = ('restart_cap_value', 'restart_cap_config_matches_chain', 'abort_reason',
            'crossing_not_acted_on', 'incomplete_reasons')
#: the dotted code names the prose uses
DOTTED = ('build_live_ab_results.normal_end_reading', 'build_live_ab_results.restart_cap_binding',
          'lab_common.server_supervision_cap')


def _ticked(text: str) -> list:
    return re.findall(r'`([A-Za-z_]+)`', text)


def reasons_listed(text: str) -> list:
    """The closed reasons the ARCHITECTURE text lists, in its order: every backticked name in the
    parenthesis that opens with `trial_not_started` (the whole list, so a reason the code has and
    the prose lacks, or the reverse, shows).  [] when the list is not there."""
    start = text.find('(`trial_not_started`')
    end = text.find(');', start)
    if start < 0 or end < 0:
        return []
    return re.findall(r'`([a-z_]+)`', text[start:end])


def _ev(seq: int, etype: str, **body) -> dict:
    return {'seq': seq, 'type': etype, 'body': body}


def _cfg_with_horizon(n: int) -> dict:
    """The frozen configuration of this checkout with the horizon a run-time value would carry
    (``monitor.n_max`` is null in the frozen file and filled from the roster at run time)."""
    cfg = json.loads((SOURCE_REPO / REL_CONFIG).read_text('utf-8'))
    return dict(cfg, monitor=dict(cfg['monitor'], n_max=n),
                roster=dict(cfg.get('roster') or {}, n_pairs=n))


def code_checks() -> dict:
    """What the new prose states, read back from the code of this checkout and run on
    synthetic chains with the code's own functions.  Returns the facts and ``gate``."""
    bld = build_live_ab_results
    f: dict = {}
    g: dict = {}
    flat16 = ' '.join(P4_16.split())
    flat315 = ' '.join(A4_3_15.split())
    f['labels'] = {k: getattr(bld, k, None) for k in ORDER}
    g['new_labels_quoted_verbatim_in_16'] = all(
        isinstance(f['labels'][k], str) and '`%s`' % f['labels'][k] in flat16 for k in NEW_LABELS)
    src = inspect.getsource(bld.decision_object)
    marks = [src.find('primary, reportable, label = %s' % n) if n == 'DECISION_INVALID_LABEL'
             else src.find('primary, reportable = %s' % n) for n in ORDER]
    f['precedence_offsets'] = marks
    g['precedence_in_the_code_is_the_order_of_16'] = (all(m >= 0 for m in marks)
                                                     and marks == sorted(marks))
    g['new_branches_require_no_logged_decision'] = all(
        ("elif logged is None and %s" % cond) in src
        for cond in ("end['terminal'] == 'trial_aborted':",
                     "not end['normal_end_at_full_horizon']:"))
    f['not_normal_end_reasons'] = list(getattr(bld, 'NOT_NORMAL_END_REASONS', ()))
    f['reasons_listed_in_3_15'] = reasons_listed(A4_3_15)
    g['closed_reasons_named_in_3_15_in_the_code_order'] = (
        bool(f['not_normal_end_reasons'])
        and f['reasons_listed_in_3_15'] == f['not_normal_end_reasons'])
    bsrc = inspect.getsource(bld.build)
    g['row_keys_are_written_by_build'] = (
        all("'%s'" % k in bsrc for k in ROW_KEYS)
        and "summary['restart_cap'] = restart_cap_binding(" in bsrc
        and all('`%s`' % k in flat315 for k in ROW_KEYS))
    found = []
    for dotted in DOTTED:
        mod, name = dotted.split('.', 1)
        obj = {'build_live_ab_results': bld, 'lab_common': lab_common}[mod]
        found.append(callable(getattr(obj, name, None)))
    g['dotted_names_exist'] = all(found) and all('`%s`' % d in flat315 for d in DOTTED)
    # -- behaviours, on synthetic chains ----------------------------------------------
    cfg2 = _cfg_with_horizon(2)
    start = _ev(0, 'trial_started', config_sha256='a' * 64, n_pairs_max=2)
    owed = _ev(1, 'abort_owed', reason='harness_defect', source='run_loop_backstop',
               decision_logged=False, open_arrivals=[])
    aborted = _ev(2, 'trial_aborted', status='aborted', reason='harness_defect',
                  resolution={'verdict': 'PASS'})
    ended = _ev(1, 'trial_ended', status='ended', reason=None, resolution={'verdict': 'PASS'})
    a = bld.decision_object([start, owed, aborted], cfg2, 'T4')
    f['non_cap_abort_no_decision'] = {k: a[k] for k in ('primary_result', 'reportable',
                                                        'decision_label')}
    g['a_non_cap_abort_without_a_decision_is_the_abort_label'] = (
        a['primary_result'] == bld.PREDECISION_ABORT_LABEL and a['reportable'] is False
        and a['normal_end']['abort_reason'] == 'harness_defect'
        and 'harness_defect' not in a['primary_result'])
    o = bld.decision_object([start], cfg2, 'T4')
    e = bld.decision_object([start, ended], cfg2, 'T4')
    f['open_chain'] = [o['primary_result'], o['reportable'], o['normal_end']['reasons']]
    f['ended_short'] = [e['primary_result'], e['reportable'], e['normal_end']['reasons']]
    g['an_open_or_short_chain_is_the_incomplete_label'] = (
        o['primary_result'] == e['primary_result'] == bld.INCOMPLETE_CHAIN_LABEL
        and o['reportable'] is False and e['reportable'] is False
        and 'no_terminal_record' in o['normal_end']['reasons']
        and 'enrolment_short_of_horizon' in e['normal_end']['reasons'])
    full = [start, _ev(1, 'pair_enrolled', pair=1), _ev(2, 'pair_enrolled', pair=2),
            _ev(3, 'monitor_update', n=2, n_collapsed=2),
            _ev(4, 'trial_ended', status='ended', reason=None, resolution={'verdict': 'PASS'})]
    ok_end = bld.normal_end_reading(full, cfg2, None)
    broken = [bld.normal_end_reading(full[:-1] + [dict(full[-1], type='trial_aborted')], cfg2,
                                     None),
              bld.normal_end_reading(full[:-1] + [_ev(4, 'trial_ended', status='ended',
                                                      reason=None,
                                                      resolution={'verdict': 'FAIL'})], cfg2,
                                     None),
              bld.normal_end_reading(full, cfg2, {'seq': 1, 'reason': 'abort_owed'}),
              bld.normal_end_reading(full, _cfg_with_horizon(3), None)]
    f['normal_end'] = [ok_end['reasons']] + [b['reasons'] for b in broken]
    g['a_normal_end_holds_and_each_condition_refuses_it'] = (
        ok_end['normal_end_at_full_horizon'] is True
        and [b['normal_end_at_full_horizon'] for b in broken] == [False] * 4
        and [b['reasons'][0] for b in broken] == ['trial_aborted', 'resolution_not_pass',
                                                   'no_decision_point_in_chain',
                                                   'horizon_not_the_chain_horizon'])
    frozen = json.loads((SOURCE_REPO / REL_CONFIG).read_text('utf-8'))
    bind = bld.restart_cap_binding([start], frozen, config_path='freeze/config.json',
                                   config_sha256='a' * 64)
    gone = bld.restart_cap_binding([start], {k: v for k, v in frozen.items()
                                             if k != 'server_supervision'})
    f['binding'] = {k: bind[k] for k in ('value', 'server_supervision',
                                         'config_sha256_matches_chain')}
    g['the_cap_and_its_binding_are_read_from_the_configuration'] = (
        bind['value'] == lab_common.server_supervision_cap(frozen) == 3
        and bind['server_supervision'] == frozen['server_supervision']
        and bind['server_supervision_sha256']
        == lab_common.sha256_canonical(frozen['server_supervision'])
        and bind['config_sha256_matches_chain'] is True
        and gone['value'] is None and bool(gone['error'])
        and a['restart_cap']['cap_value'] == 3)
    return {'facts': f, 'gate': g}


def _refuse(msg: str, obj=None) -> int:
    print('refusing: %s; NOTHING was written%s'
          % (msg, (': ' + json.dumps(obj, default=str)) if obj is not None else ''),
          file=sys.stderr)
    return 2


def _earlier(path: Path, pinned: str, n: int, commit: str | None, rel: str, old: dict,
             name: str) -> tuple:
    """(receipt, facts, gate checks) of an earlier amendment kept whole."""
    raw = path.read_bytes()
    doc = json.loads(raw)
    committed = None
    if commit is not None:
        try:
            committed = git_blob(commit, rel)
        except (OSError, subprocess.CalledProcessError):
            committed = None
    whole = texts_intact(old, doc)
    facts = {'receipt': rel, 'receipt_sha256': sha(raw), 'insertions_whole_before': whole}
    checks = {'%s_receipt_is_the_pinned_bytes' % name: sha(raw) == pinned,
              '%s_insertions_whole_in_the_preimages' % name: (len(whole) == n
                                                              and all(whole.values()))}
    if commit is not None:
        checks['%s_receipt_is_committed_in_its_commit' % name] = committed == raw
    return doc, facts, checks


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runs-json', default=None,
                    help='a JSON list of every run of this step before this one (pass or '
                         'fail), recorded in the receipt verbatim')
    args = ap.parse_args(argv)
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / (RECEIPT_PREFIX + '%s.json' % stamp)
    if receipt_path.exists():
        print('refusing: %s exists (write-once)' % receipt_path, file=sys.stderr)
        return 2
    runs = None
    if args.runs_json:
        try:
            runs = json.loads(Path(args.runs_json).read_text('utf-8'))
        except (OSError, ValueError) as e:
            return _refuse('the runs file could not be read (%s)' % e)

    # -- 1. preconditions, on BYTES --------------------------------------------
    old = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
           'protocol': PROTO.read_bytes()}
    cells_raw = CELLS.read_bytes()
    try:
        cells = json.loads(cells_raw)
        va = cells['provenance']['vocabulary_alignment']
        sb = va.get('superseded_by', {})
        prior = list(sb.get('prior_successors', []))
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        return _refuse('cells.json unreadable (%s)' % e)
    before = contract(old['config'], old['architecture'], old['protocol'])
    anchors = {ins.key: anchor_facts(old[ins.doc], ins) for ins in INSERTIONS}
    form = inserted_text_form()
    try:
        rb_before = lab_common.rule_block_sha256(json.loads(old['config']))
    except (ValueError, TypeError, KeyError, lab_common.LabError):
        rb_before = None
    entries = [(e.get('sha256'), sha(json.dumps(e, sort_keys=True).encode('utf-8')))
               if isinstance(e, dict) else (None, None) for e in prior]
    pre = {
        'config_sha256': sha(old['config']), 'config_bytes': len(old['config']),
        'architecture_sha256': sha(old['architecture']),
        'protocol_sha256': sha(old['protocol']),
        'cells_sha256': sha(cells_raw),
        'cr_bytes': dict({k: v.count(b'\r') for k, v in old.items()},
                         cells=cells_raw.count(b'\r')),
        'three_way_contract_before': before,
        'rule_block_sha256_before': rb_before,
        'cells_round_trips': ((json.dumps(cells, indent=1) + '\n').encode('utf-8')
                              == cells_raw),
        'cells_original_pin': va.get('sha256'),
        'cells_current_successor': sb.get('sha256'),
        'cells_prior_successors': [{'sha256': a, 'entry_canonical_sha256': b}
                                   for a, b in entries],
        'anchors': anchors,
        'inserted_text_form': form,
        'head': git('rev-parse', 'HEAD'),
    }
    pre['gate_pins'] = {
        'config_is_the_reviewed_preimage': (pre['config_sha256'] == PRIOR_CONFIG_SHA256
                                            and pre['config_bytes'] == PRIOR_CONFIG_BYTES),
        'architecture_is_the_reviewed_preimage': pre['architecture_sha256'] == PRIOR_ARCH_SHA256,
        'protocol_is_the_reviewed_preimage': pre['protocol_sha256'] == PRIOR_SUCCESSOR,
        'cells_is_the_reviewed_preimage': pre['cells_sha256'] == PRIOR_CELLS_SHA256,
        'no_cr_byte': not any(pre['cr_bytes'].values()),
        'three_way_contract_before': before['holds'] is True,
        'rule_block_before_is_the_pin': rb_before == PRIOR_RULE_BLOCK,
        'cells_round_trips': pre['cells_round_trips'],
        'cells_original_pin_untouched': pre['cells_original_pin'] == ORIGINAL_PIN,
        'cells_current_successor_is_the_prior_successor':
            pre['cells_current_successor'] == PRIOR_SUCCESSOR,
        'cells_successor_supersedes_the_original': sb.get('supersedes') == ORIGINAL_PIN,
        'cells_prior_successor_count': len(prior) == PRIOR_PRIOR_SUCCESSORS,
        'cells_prior_successors_are_the_recorded_entries':
            tuple(entries) == PRIOR_ENTRIES,
    }
    if not gate('pins', pre['gate_pins']):
        return _refuse('a precondition failed', pre)
    if any(a['text_already_present'] for a in anchors.values()):
        return _refuse('the amendment is already present')
    pre['gate_anchors'] = {
        'every_anchor_once': all(a.get('anchor_occurrences') == 1 for a in anchors.values()),
        'no_anchor_error': all('error' not in a for a in anchors.values()),
        'every_anchor_inside_its_section': all(a.get('inside_its_section') is True
                                               for a in anchors.values()),
        'inserted_text_form': form['ok'] is True,
    }
    if not gate('anchors', pre['gate_anchors']):
        return _refuse('a precondition failed', pre)

    # -- 2. amendments v3 and v2, named and verified ----------------------------------
    try:
        v3, v3_facts, v3_checks = _earlier(V3_RECEIPT, V3_RECEIPT_SHA256, V3_INSERTIONS, PRE_REV,
                                           V3_RECEIPT_REL, old, 'v3')
        v2, v2_facts, v2_checks = _earlier(V2_RECEIPT, V2_RECEIPT_SHA256, V2_INSERTIONS, None,
                                           V2_RECEIPT_REL, old, 'v2')
    except (OSError, ValueError) as e:
        return _refuse('an earlier amendment receipt could not be read (%s)' % e)
    written = v3.get('written') or {}
    predecessor = dict(v3_facts, commit=PRE_REV,
                       status=('kept: write-once, not edited and not superseded; v4 adds two '
                               'insertions to the documents v3 wrote'),
                       written_by_v3={k: written.get(k) for k in (
                           'config_sha256', 'architecture_sha256', 'protocol_sha256',
                           'cells_sha256')},
                       amendment_v2_kept=v2_facts)
    predecessor['gate'] = dict(
        v3_checks, **v2_checks,
        v3_commit_is_an_ancestor_of_head=git_is_ancestor(PRE_REV, 'HEAD') is True,
        v3_wrote_the_preimages=(
            written.get('config_sha256') == pre['config_sha256']
            and written.get('architecture_sha256') == pre['architecture_sha256']
            and written.get('protocol_sha256') == pre['protocol_sha256']
            and written.get('cells_sha256') == pre['cells_sha256']))
    if not gate('amendments_v3_v2', predecessor['gate']):
        return _refuse('amendment v3 or v2 is not as pinned', predecessor)

    # -- 3. the prose against the code ---------------------------------------------------
    try:
        code = code_checks()
    except Exception as e:                                     # noqa: BLE001
        return _refuse('the code the prose describes could not be checked (%r)' % e)
    if not gate('code', code['gate']):
        return _refuse('the prose does not describe the code', code)

    # -- 4. insert, as bytes -----------------------------------------------------------
    try:
        new = insert_all(old)
    except ValueError as e:
        return _refuse(str(e))

    # -- 5. postconditions, computed BEFORE anything is written; the negative control ------
    post, ok = postconditions(old, new, v3, v2)
    if not ok:
        return _refuse('a postcondition failed', post)
    control = negative_control(old, new, v3, v2)
    control['gate'] = {
        'every_moved_variant_refused_on_placement':
            control['every_moved_variant_refused_on_placement'] is True,
        'config_variant_refused': control['config_variant_refused'] is True,
        'v3_split_variant_refused': control['v3_split_variant_refused'] is True,
        'vocabulary_variant_refused': control['vocabulary_variant_refused'] is True,
        'scratch_copies_unchanged': control['scratch_copies_unchanged'] is True,
        'real_documents_unchanged': control['real_documents_unchanged'] is True,
    }
    if not gate('negative_control', control['gate']):
        return _refuse('the negative control did not refuse', control)

    # -- 6. the successor, additively --------------------------------------------------
    try:
        verified_commit_hash = sha(git_blob(PRIOR_SUCCESSOR_COMMIT, REL_PROTO))
    except (OSError, subprocess.CalledProcessError):
        verified_commit_hash = None
    commit_gate = {'prior_successor_commit_carries_the_prior_successor':
                   verified_commit_hash == PRIOR_SUCCESSOR}
    if not gate('successor_commit', commit_gate):
        return _refuse('%s does not carry the prior successor' % PRIOR_SUCCESSOR_COMMIT)
    demoted = {k: v for k, v in sb.items()
               if k not in ('prior_successors', 'changing_commit_note',
                            'correction_to_the_owner_report')}
    demoted['changing_commit_of_this_successor'] = PRIOR_SUCCESSOR_COMMIT
    demoted['changing_commit_note'] = (
        'Resolved AFTER the fact, when the repair amendment v4 landed on top of it: '
        '`git show %s:experiments/live_ab/design/protocol_FINAL.md` hashes to this '
        'successor.' % PRIOR_SUCCESSOR_COMMIT[:7])
    new_sb = {
        'sha256': post['protocol_sha256'],
        'supersedes': ORIGINAL_PIN,
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'reason': (
            'NOT an Appendix B change: the narrow pre-outcome amendment v4 of the EB1+EB5 repair '
            'subset (root 2026-09-25 07:10, choice (b)). PURE INSERTIONS of dated prose, nothing '
            'else: deleting them reproduces the v3 successor 73dd0573 byte for byte. config.json '
            'is not written, and the configuration block of Appendix B and of ARCHITECTURE 6.1 is '
            'byte-identical; no key is added, removed or changed. Protocol 16 item 18: with no '
            'logged decision a trial_aborted is incomplete and not reportable whatever its cause '
            'and whether or not a crossing was logged after its point, its concrete reason and '
            'any crossing not acted on kept beside the result; a chain that is not a normal end at '
            'the frozen full horizon is incomplete; none is reportable only for a trial_ended '
            'whose resolution passed at the frozen full horizon with no crossing (the frozen rule '
            'logs horizon_no_decision there); a decision logged before a later abort keeps its '
            'rules; the effective restart cap and its configuration binding are reported. '
            'ARCHITECTURE 3.15: the decision.json and program_summary.json fields that carry it. '
            'It changes no execution rule, and no CPU cell, parameter, seed, horizon, estimator, '
            'outcome definition, monitor or decision threshold, alpha, margin, enrollment, stop '
            'rule, restart cap or sampling parameter, and none of the vocabulary sections 1, 3 and '
            '11 this pin reads (verified byte-identical). The rule-block keys are byte-unchanged '
            '(digest cbfd1792); that digest covers no protocol text, so it does not show the '
            'absence of the changes listed here. Amendments v3 (73dd0573, commit 56df17f, receipt '
            'REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218.json) and v2 (receipt '
            'REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json) are kept: none of their texts is '
            'split or changed.'),
        'ruling': (
            'Root 2026-09-25 07:10 (reviews/predecision_abort_reporting_ruling_20260925_0710.md), '
            'choice (b), and the cap provenance it asks for. The pin amendment follows the '
            'standing root ruling of 2026-09-22 04:27 '
            '(reviews/protocol_pin_disposition_20260922_0422.md): "preserve the original pin; '
            'record an explicit post-freeze provenance amendment ... Do not replace the original '
            'sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial, stage or launch approval, not a CPU rerun, and not the code '
            'it describes (the builder change is a separate, earlier commit). It certifies no '
            'run: no server was started and no model was run. Its code checks read names from '
            'the code and run the code\'s functions on synthetic chains; they are not the '
            'controls of experiments/live_ab_controls.'),
        'correction_to_the_owner_report': sb['correction_to_the_owner_report'],
        'prior_successors': prior + [demoted],
        'changing_commit_note': (
            'The commit that introduces a successor cannot carry its own hash, so '
            '"changing_commit_of_this_successor" is resolved in a LATER commit. The last '
            'entry above records the one for the %s successor (the repair amendment v3), '
            'resolved when this amendment landed; this newest successor\'s own commit is '
            'recorded the same way when the next one lands.' % PRIOR_SUCCESSOR_RECORDED),
    }
    new_cells = json.loads(cells_raw)
    new_cells['provenance']['vocabulary_alignment']['superseded_by'] = new_sb
    a, b = json.loads(cells_raw), json.loads(json.dumps(new_cells))
    a['provenance']['vocabulary_alignment'].pop('superseded_by')
    b['provenance']['vocabulary_alignment'].pop('superseded_by')
    cells_gate = {'cells_unchanged_outside_superseded_by': a == b}
    if not gate('cells', cells_gate):
        return _refuse('cells.json would change outside superseded_by')
    new_cells_raw = (json.dumps(new_cells, indent=1) + '\n').encode('utf-8')

    # -- 7. write: the two documents and cells.json (config.json is NOT written) ----------
    harness_before = lab_common.harness_file_hashes()
    intended = {ARCH: new['architecture'], PROTO: new['protocol'], CELLS: new_cells_raw}
    for path, raw in intended.items():
        path.write_bytes(raw)
    harness_after = lab_common.harness_file_hashes()
    on_disk = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
               'protocol': PROTO.read_bytes()}
    written_facts = {
        'read_back_equals_computed': all(p.read_bytes() == raw for p, raw in intended.items()),
        'config_sha256': sha(on_disk['config']), 'config_bytes': len(on_disk['config']),
        'architecture_sha256': sha(on_disk['architecture']),
        'protocol_sha256': sha(on_disk['protocol']),
        'cells_sha256': sha(CELLS.read_bytes()),
        'three_way_contract_on_disk': contract(on_disk['config'], on_disk['architecture'],
                                               on_disk['protocol']),
        'rule_block_sha256_on_disk': lab_common.rule_block_sha256(json.loads(on_disk['config'])),
        'harness_files_before': len(harness_before), 'harness_files_after': len(harness_after),
        'harness_entries_changed': sorted(k for k in set(harness_before) | set(harness_after)
                                          if harness_before.get(k) != harness_after.get(k)),
    }
    written_facts['gate'] = {
        'documents_read_back_equal_computed': written_facts['read_back_equals_computed'] is True,
        'config_on_disk_unchanged': on_disk['config'] == old['config'],
        'no_harness_file_changed': written_facts['harness_entries_changed'] == [],
    }
    if not gate('final', written_facts['gate']):
        print('refusing to write the receipt: the written documents did not verify (the '
              'documents ARE written; restore them from git): %s' % json.dumps(written_facts),
              file=sys.stderr)
        return 2
    doc = {
        'schema': 'live_ab.repair_amendment_receipt.v4',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root: reviews/predecision_abort_reporting_ruling_20260925_0710.md, choice '
                      '(b), and its cap provenance (quoted in this tool\'s docstring)'),
        'prepared_by': ('prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off'),
        'predecessor_amendment_v3': dict(predecessor),
        'documents_amended': [REL_ARCH, REL_PROTO],
        'documents_not_written': [REL_CONFIG],
        'insertions': [ins.describe() for ins in INSERTIONS],
        'code_the_prose_describes': [
            'build_live_ab_results: PREDECISION_ABORT_LABEL, INCOMPLETE_CHAIN_LABEL, '
            'NOT_NORMAL_END_REASONS, AFTER_TERMINAL_TYPES, CONFIG_REL, frozen_horizon, '
            'restart_cap_binding, normal_end_reading, restart_cap_reading (cap_value, binding), '
            'decision_object (first match wins: invalid, the cap, a crossing not acted on, the '
            'abort, the incomplete chain, provisional, the logged decision or none; normal_end), '
            'build (the summary rows: restart_cap_value, restart_cap_config_matches_chain, '
            'abort_reason, crossing_not_acted_on, incomplete_reasons; the program restart_cap)',
            'lab_common: server_supervision_cap, SERVER_SUPERVISION_KEY, sha256_canonical',
            'the verifier (lab_verify_log) is unchanged: it classifies no reportability',
        ],
        'code_checked_at_run_time': code,
        'precondition_checked': pre,
        'postcondition_checked': post,
        'negative_control': control,
        'written': written_facts,
        'successor_provenance': {
            'original_pin_untouched': ORIGINAL_PIN,
            'new_successor': post['protocol_sha256'],
            'demoted_successor': PRIOR_SUCCESSOR,
            'demoted_successor_commit_verified': PRIOR_SUCCESSOR_COMMIT,
            'gate_successor_commit': commit_gate,
            'gate_cells': cells_gate,
            'prior_successors_now': len(new_sb['prior_successors'])},
        'prior_versions_retained': {
            'config_sha256': PRIOR_CONFIG_SHA256, 'config_bytes': PRIOR_CONFIG_BYTES,
            'architecture_sha256': PRIOR_ARCH_SHA256, 'protocol_sha256': PRIOR_SUCCESSOR,
            'cells_sha256': PRIOR_CELLS_SHA256, 'revision_at_run': pre['head'],
            'reviewed_revision': PRE_REV,
            'note': ('each is recoverable byte-exactly by `git show <reviewed_revision>:<path>` '
                     'and by deleting every inserted text')},
        'dependent_hashes_that_move': {
            'protocol_sha256': 'moves; recorded as the new successor above (a bundle member '
                               'not recomputed at run time, lab_common.'
                               'BUNDLE_MEMBERS_NOT_RECOMPUTED)',
            'architecture_sha256': 'moves (ARCHITECTURE is under design/, outside the harness pin)',
            'cells.json': 'moves (the successor history)',
        },
        'dependent_hashes_that_do_not_move': [
            'config_sha256 and harness_file_sha256[config.json] (config.json not written)',
            'harness_file_sha256 of every file of the harness pin (the builder moved in the '
            'commit BEFORE this one; this tool writes no harness file)', 'rule_block_sha256',
            'llama_cpp.serving_manifest_sha256 and the serving-manifest artifact'],
        'runs_of_this_step_before_this_receipt': runs,
        'runs_after_this_receipt': ('the suites run after this receipt are recorded in the '
                                    'commit that adds it and in the owner report'),
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server, build or network request; text '
                             'edits, digests, git reads, and the functions of the results '
                             'builder on synthetic in-memory chains'),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(receipt_path, 'x', encoding='utf-8') as fh:     # write-once
        fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + '\n')
    print(receipt_path)
    print(json.dumps({'post_ok': ok, 'new_protocol': post['protocol_sha256'],
                      'new_architecture': post['architecture_sha256'],
                      'config_unchanged': post['config_sha256'] == PRIOR_CONFIG_SHA256,
                      'rule_block': (post['rule_block_sha256_after'] or '')[:12],
                      'negative_control_variants': control['variants_run']}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
