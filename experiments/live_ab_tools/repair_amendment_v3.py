"""Synchronized pre-outcome amendment v3 of the EB1+EB5 repair subset: the protocol and the
architecture say what the code on this branch now does.

Why a v3.  The committed amendment v2 (474f9d8; receipt
``results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json``, write-once, kept) described
the code of 474f9d8.  Three later commits changed what that code does (03fe0ca, 7ebffad and
9f0aff6; 988baf7, 591ebcd and 159e747 carry the harness pin successor), and protocol 5.3, 6.4,
12.2, 12.4, 13.1, 14.6 and 16 did not describe the new behaviour.  Root's rulings this amendment
writes down, each read on origin/main:

  * ``reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md`` item 1: "Once any terminal
    abort is owed before a decision, later reveal/monitor looks must remain in the immutable
    record and partial bounds, but must not create a decision"; item 2: "Define the earliest
    eligible decision prefix from durable event ordering, including the reason a later look is
    ineligible; apply that same classification in the orchestrator, verifier and results
    builder", "label a crossing inside an ineligible interval as **not acted on**, with a
    concrete operational reason", "a crossing before the exclusion point with no decision
    remains a defect"; "Do not alter margins, alpha allocation, raw observations or stop rules".
  * ``reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md``: an invalid post-boundary
    decision is never reportable; the summary's decision is the invalidity label, the logged
    decision is kept beside it.
  * ``reviews/decision_receipt_metadata_ruling_20260924_0324.md``: "verify the pushed
    commit/anchor-head evidence"; 12.4 "has **no timestamp authority**".
  * ``reviews/restart_cap_estimand_ruling_20260923_2114.md``: "Reconciliation must include
    smoke/restart counter windows and unknown usage", "killing/reaping does not turn unknown
    historical usage into zero".

WHAT IT DOES, AND ONLY THIS (every refusal goes through :func:`gate`, which names its checks)
  1. Preconditions on BYTES against the current pre-images, the documents amendment v2 wrote
     (474f9d8, unchanged since): config.json f158969e (16,136 bytes), ARCHITECTURE_FINAL.md
     e7ea9c0f, protocol_FINAL.md 6c0ebf2f (the v2 successor), cells.json 6b31bf20 whose six
     prior successors are each the entry as recorded (canonical digests), rule block cbfd1792,
     the three-way configuration contract; every anchor once, at a line start, inside its
     section.
  2. Amendment v2 named and verified: its receipt hashes to its pinned digest on disk and in
     474f9d8 (``git show``), 474f9d8 is an ancestor of HEAD, the digests the receipt says it
     wrote are the pre-images, and each of its 27 insertion texts is still whole, once, in its
     document.  It is not edited and not superseded: v3 adds to it.
  3. The prose against the code, at run time (:func:`code_checks`): every closed name the new
     prose uses is read back from the code (the ``abort_owed`` sources and fields, the
     no-decision reasons, the anchor-commit problem codes, the builder labels, the verifier
     rule names), and each behaviour the prose states is exercised on a synthetic chain by the
     code's own pure functions (the no-decision point reads ``abort_owed``, supervision replays
     it, a crossing after the point is ``not_acted_on`` and one before it ``missed``, an
     unresolved worker stays unresolved, a lost-counter window without a read counter is
     ``null``, the null fields are nullable in the schema).
  4. PURE INSERTIONS only, ten, into ARCHITECTURE (three) and the protocol (seven).  config.json is not
     written, and the configuration block of ARCHITECTURE 6.1 and Appendix B is byte-identical
     (no documented key was missing).  Sections 1, 3 and 11 byte-identical; no v2 text is split.
  5. Postconditions computed before anything is written; a negative control on scratch copies
     (each insertion moved out of its section; a configuration byte changed; the 12.2 text put
     inside amendment v2's own text; a vocabulary section touched) -- every variant refused.
  6. The successor of cells.json: 6c0ebf2f demoted whole with its changing commit 474f9d8
     (checked: ``git show 474f9d8:<protocol>`` hashes to it).
  7. Writes ARCHITECTURE, the protocol and cells.json, reads them back, and writes the
     write-once receipt ``results/live_ab/REPAIR_AMENDMENT_V3_RECEIPT_<UTC>.json``.

It is NOT a freeze, NOT trial, stage or launch approval; it starts no server, runs no model,
build or network request; it changes no statistical rule, margin, alpha, observation or stop
rule.  The witnesses are ``tests_repair_amendment_v3.py`` (drive main() on scratch copies of the
474f9d8 blobs) and the independent re-derivation ``verify_repair_amendment_v3.py``.

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
import lab_eventlog                                            # noqa: E402
import lab_orchestrator                                        # noqa: E402
import build_live_ab_results                                   # noqa: E402
# The reviewed section scanner: a section runs from its heading to the next heading of the
# same or a higher level, fenced lines skipped.
from engineering_cap_amendment import block_of, fence_span, section_span  # noqa: E402

REL_CONFIG = 'experiments/live_ab/config.json'
REL_ARCH = 'experiments/live_ab/design/ARCHITECTURE_FINAL.md'
REL_PROTO = 'experiments/live_ab/design/protocol_FINAL.md'
REL_CELLS = 'experiments/live_ab_validation/cells.json'
REL_VERIFY_LOG = 'experiments/live_ab/lab_verify_log.py'
CONFIG = REPO / REL_CONFIG
ARCH = REPO / REL_ARCH
PROTO = REPO / REL_PROTO
CELLS = REPO / REL_CELLS

#: The pre-images: the documents amendment v2 wrote in 474f9d8 (unchanged on this branch since).
PRE_REV = '474f9d82aae2b3979910d8a99d8305b5d7bc44c1'
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
PRIOR_SUCCESSOR = '6c0ebf2faa7515ff27f01188d9f1e487c928c63373f451dea51f06a8cdacaab9'
PRIOR_SUCCESSOR_COMMIT = PRE_REV
PRIOR_SUCCESSOR_RECORDED = '09:27'
PRIOR_CONFIG_SHA256 = 'f158969ecf02de47953cec8b6f9216a4a673e746e45851b882d30c5a221cefa7'
PRIOR_CONFIG_BYTES = 16136
PRIOR_ARCH_SHA256 = 'e7ea9c0fb7a28c6bdb47bb4085dcddba41144bd134d7b3a9b026ad7c9a30c86a'
PRIOR_CELLS_SHA256 = '6b31bf20a07cbc4b0c162fb0d309826d88ab5b95b36f9cd3e1d86500d7ff8df5'
PRIOR_RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
PRIOR_PRIOR_SUCCESSORS = 6
#: the six prior successors of the pre-image, in order: (sha256 field, canonical digest of
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
)
#: Amendment v2: its write-once receipt (kept, not edited, not superseded)
V2_RECEIPT_REL = 'results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
V2_RECEIPT = REPO / V2_RECEIPT_REL
V2_RECEIPT_SHA256 = '66efcb8b64b3e54d890ac70c77686e0678255fe6cba78347fa3a30878e12feff'
V2_INSERTIONS = 27

RECEIPT_PREFIX = 'REPAIR_AMENDMENT_V3_RECEIPT_'
ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'
#: the sections the vocabulary pin reads (cells.json sections_read [1, 3, 11])
VOCAB_MARKERS = {1: b'## 1. Purpose, scope', 3: b'## 3. Task roster',
                 11: b'## 11. The planning study'}
R0324 = '`reviews/decision_receipt_metadata_ruling_20260924_0324.md`'
R1605 = '`reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md`'
R1905 = '`reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md`'
R2114 = '`reviews/restart_cap_estimand_ruling_20260923_2114.md`'


def _lines(*lines: str) -> str:
    return ''.join(line + '\n' for line in lines)


# ---------------------------------------------------------------------------
# The prose.  Each is a pure insertion at one anchor, inside one section, and each anchor is
# the LAST line of amendment v2's text there (or an original row), so no v2 text is split.
# Each states what the code of this branch PERFORMS (the functions named in the receipt's
# ``code_the_prose_describes``; :func:`code_checks` reads the names back and runs the
# behaviours on synthetic chains).
# ---------------------------------------------------------------------------
P3_5_3 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s item 1, and' % R1605,
    '%s).* **Every owed abort is written before its drain.** Case (a)' % R2114,
    'above is one instance of the rule of 6.4 of this date: the moment supervision owes a terminal abort, a durable',
    '`abort_owed` (12.2 row 31, `source` `supervision`) is written, before any open attempt is drained, and no look',
    'after it carries a decision. Supervision owes one at the `server_down` that requires a fourth restart',
    '(`server_restart_cap`; the point of the cap is that `server_down` itself); at a supervised restart or a start at',
    'resume that fails at `gguf`, `serving_manifest`, `identity` or `smoke` (the abort of that stage, as above); at a',
    'restarted server whose `/props` differ from the previous start\'s (`server_identity`); at a restart or start call',
    'the harness refused, or an exception it did not convert (`harness_defect`); and when the frozen health threshold',
    'or cap is missing (`harness_defect`; preflight refuses that before seq 0). A restart, or a start at resume, that',
    'never becomes healthy (`launch`, `health`) owes the `server_unrecoverable` pause, not an abort, and writes no',
    '`abort_owed`. A resumed invocation rebuilds what the chain still owes, `abort_owed` included, so an abort owed',
    'before a crash inside its drain is still owed after it. The cap, the three cases, the margins, the alpha',
    'allocation, the observations and the stop rules are unchanged.',
)
P3_6_4 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s' % R1605,
    'items 1 and 2, and %s).*' % R1905,
    '**Decision eligibility: one durable classification.** "An abort can only remove decisions, never create one" is',
    'enforced from the chain alone. A look (a `monitor_update`) is **eligible** to carry the decision only when, in',
    'the chain before it, there is no `decision`, it is not a `drain` look, and the trial\'s **no-decision point**',
    'does not precede it. The point',
    '(`lab_eventlog.no_decision_point`) is the earliest of: the `server_down` that requires a fourth restart',
    '(`server_restart_cap`, 5.3); a `server_start_failed` that owes an abort - a first start (before any',
    '`invocation_started`) at any stage, any other start or restart at a stage other than `launch` and `health` -',
    '(`server_start_failed`); a `server_restarted` whose `/props` differ from the previous start\'s',
    '(`server_identity`); the trigger of an automatic abort - a response or a reveal with a receipt mismatch',
    '(`receipt_mismatch`), the reveal that completes ten consecutive reveals of one invocation classed',
    '`episode_timeout`, `worker_died` or `interrupted` (`infrastructure`); a `worker_resolved` that does not resolve',
    'its worker (`unresolved_worker`, 14.6); and an `abort_owed` (`abort_owed`, 12.2 row 31). **Every abort path',
    'writes `abort_owed` before its drain reveals anything**: supervision (`supervision`, 5.3); every `AbortTrial`',
    'that reaches the run loop - the automatic aborts, a failed first start, and any other code that raises it',
    '(`abort_raised`); the run loop\'s catch of a server exception outside supervision (`run_loop_backstop`); the',
    'close of an ended trial that finds an attempt still open and no decision, which closes as an abort, never as an',
    'ended trial whose drain could decide (`close_with_open_work`); and the resolution verdict of 14.6',
    '(`resolution_verdict`, written after the drain, before the terminal record). If a look ever finds an abort owed',
    'in memory that no path has written, the look writes it first (`look_guard`) and records a finding. The point is',
    'a function of the chain before it, so the orchestrator (before it writes each look), the verifier',
    '(`reference_rule.agreement`) and the results builder (`decision.json`) classify every look identically, with one',
    'function (`lab_eventlog.decision_eligibility`). Every look is still logged exactly as without the abort, with its',
    'band and the reference rule\'s shadow; only the `decision` event is withheld. The reference rule\'s first crossing',
    'is kept unfiltered, as a diagnostic beside every look and its classification, and is given one verdict. At a look',
    'that is not eligible, with no decision, it is **not acted on**: an INFO row of the verifier',
    '(`NOT_ACTED_ON_restart_cap_before_decision` or `NOT_ACTED_ON_abort_before_decision`) naming the concrete reason',
    '(what closed the prefix and at which seq, and for an `abort_owed` the abort and its source), never a',
    'disagreement. At an **eligible** look with no decision it is a **defect** (`LIVE_DECISION_INVALID`), however the',
    'trial ended: a later abort does not exempt a crossing missed before its point. A decision logged after the point',
    'is `LIVE_DECISION_INVALID` (`decision_after_no_decision_point`; the cap\'s own case is `server.lifecycle`',
    '`decision_after_cap`), and so is a logged decision the reference rule\'s first crossing does not agree with (kind',
    'and `n`, 8.9). A `trial_aborted` whose reason (or the reason an `unresolved_worker` abort superseded) no earlier',
    '`abort_owed` names FAILs (`abort_point_missing`). The classification reads no score and changes no margin, alpha',
    'allocation, observation, band, first crossing or stop rule: it only states which logged look may carry the',
    'decision. How each case is reported: 16 item 17.',
)
P3_12_2 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s item 2,' % R1605,
    '%s and' % R2114,
    '%s): row 31, and rows 24, 26 and 29.*' % R0324,
    '',
    '| # | type | body (main fields) | D |',
    '|---|---|---|---|',
    '| 31 | `abort_owed` | `reason` (the abort owed, a reason of `trial_aborted`); `source` (`supervision`, `abort_raised`, `run_loop_backstop`, `close_with_open_work`, `resolution_verdict`, `look_guard`); `decision_logged` (whether a decision precedes it: then the abort truncates the follow-up only); `open_arrivals` (the arrivals the drain still has to reveal). The durable no-decision point of every abort path (6.4), written once per reason, before the drain | yes |',
    '',
    'A value that was not observed is recorded `null`, never as 0 and never as the digest of an empty file.',
    '`usage_reconciliation` (#24): in a window whose counters were lost (a `server_down` cut it, or it has no exact',
    'scrape), the counter deltas are the last counters read in that window, or `null` for both when none was read',
    '(13.1). `worker_resolved` (#29): when the spool cannot be read at the moment of resolution, its bytes and SHA-256',
    'are `null`, and the resolution verdict of 14.6 fails (`spool_unreadable`). `deposit_sealed` (#26): a spool that',
    'cannot be read enters the deposit digest as `null`; so does a resolved worker\'s spool that was not read at its',
    'resolution or is now shorter than its resolution offset, which is also listed in `late_unread`, with `null` for',
    'a byte count that was not observed. `anchor_receipt` (#20) of a decision is chained only once its pushed commit',
    'is bound to its anchor (12.4). Row 31 is written on a trial chain only.',
)
P3_12_4 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s: "verify' % R0324,
    'the pushed commit/anchor-head evidence").* **The pushed commit is bound to its anchor.** Before an `ok` line',
    'bound to a decision anchor request is chained as that decision\'s receipt (outside a MOCK tree, and in a MOCK tree',
    'for any line that claims external evidence), the orchestrator reads the anchor repository locally, with read-only',
    '`git` and no network: the anchor file lies inside the repository (`anchor_outside_repo`); the commit the line',
    'names exists (`commit_absent`); it is an ancestor of `refs/remotes/origin/<branch>`, the repository\'s own record',
    'of its last push of the frozen anchor branch (`not_on_pushed_branch`); `git show <commit>:<anchor file>`',
    '(`anchors/anchor_<anchor_seq>.json`) exists (`anchor_file_absent`) and hashes to the digest of this anchor\'s own',
    'file object (`anchor_file_mismatch`); a `git` that cannot run is `repo_unreadable`. Any of these makes the line',
    '`conflict` (`anchor_receipt_rejected`, 12.2 row 30): it resolves nothing, the decision stays provisional, its',
    'anchor stays pending under the timeout of 6.4 row 26, and the problem is kept in the invocation\'s findings. Only',
    'a line that passes is chained with the SHA-256 of the anchor file, of the comment body and of `node_id`. The',
    'sentence above still holds: nothing reads the remote to show that the push or the comment exists; the evidence',
    'of the push is the anchor repository\'s own record of it, and no timestamp authority is added.',
)
P3_13_1 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s: "Reconciliation' % R2114,
    'must include smoke/restart counter windows and unknown usage").* A server count that was never observed is',
    'unknown, never 0: in a reconciliation window whose counters were lost (12.2 row 24), the counter deltas are the',
    'last counters read in that window, or `null` when none was read, and the residual is `null`; such a window is',
    'reported unreconciled (6.4 row 20), never reconciled against a guessed count.',
)
P3_14_6 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s' % R1605,
    'items 1 and 2, and %s).* **The close of an abort begins with its' % R2114,
    'point.** Before the bounded drain of an abort, `abort_owed` (12.2 row 31) is written unless the chain already',
    'carries it for that reason, so the looks of the drain are not eligible to carry a decision (6.4). The close of an',
    'ended trial that finds an attempt still open and no decision closes as an abort (`close_with_open_work`), never',
    'as an ended trial.',
    'When the resolution verdict does not pass, the `abort_owed` of `unresolved_worker` is written after the drain,',
    'before the terminal record, which names the reason it superseded. **An unresolved worker stays unresolved across',
    'resume.** A worker recorded `alive_unresolved` or `liveness_unknown` is a no-decision point from that record on',
    '(6.4), and the phase can no longer complete: for each attempt the verdict and the verifier read the first state',
    'that does not resolve its worker, if there is one, whatever is recorded later. A resumed invocation that finds an',
    'earlier worker it cannot resolve (its kill not confirmed, or its liveness unreadable) first records it durably as',
    'found, `worker_resolved` with `alive_unresolved` or `liveness_unknown` (not repeated when the attempt\'s last',
    'record already says so), and then refuses (`invocation_ended` with status `refused` and the counts), revealing,',
    'starting and dispatching nothing. A later resume must confirm that process gone before its attempt is revealed',
    'as interrupted (the attempt\'s last record must resolve it), but the earlier unresolved record is never undone:',
    'the close is `trial_aborted(unresolved_worker)`. **An unread spool is recorded unread.** A spool that could not be',
    'read when its worker was resolved is recorded with `null` bytes and a `null` SHA-256, never the size and digest',
    'of an empty file, and the verdict fails (`spool_unreadable`); the deposit seal records such a spool as `null`',
    '(12.2 rows 26 and 29).',
)
P3_16 = _lines(
    '17. *(Amendment 2026-09-24, v3, pre-outcome; root',
    '    %s and' % R1605,
    '    %s.)* the **decision eligibility** of 6.4: the' % R1905,
    '    no-decision point with its reason and seq, every look with its classification and concrete reason, and the',
    '    reference rule\'s unfiltered first crossing with its verdict (`decision.json` `eligibility`). The result',
    '    reported for the trial is, first match wins: `LIVE_DECISION_INVALID (harness defect)` - a decision logged',
    '    after the point, a logged decision the reference rule does not agree with, or a crossing at an eligible look',
    '    with no decision; `incomplete: restart cap before any decision (no decision; not a null result, not an',
    '    abstention)` - case (a) of 5.3 with no decision; `incomplete: aborted before any decision; a crossing',
    '    logged after the abort point was not acted on (no decision; not a null result, not an abstention)` - with',
    '    the crossing not acted on and its reason; `provisional: the logged decision has no chained external receipt',
    '    (no finalized claim)` - a valid decision without its chained external receipt; else the logged decision, or',
    '    `none` with no decision and no crossing. **Only the last is reportable**: an invalid decision is never',
    '    reportable. The program summary\'s decision is always this result, and whenever it is not reportable the',
    '    logged decision is kept beside it (`logged_decision`); the logged event stays in the chain and under',
    '    `decision` in `decision.json`.',
)
A3_4_4 = _lines(
    '',
    '*Amendment 2026-09-24, v3 (pre-outcome; root %s,' % R1605,
    '%s and' % R1905,
    '%s): row T35, and rows T23, T28, T29b and T33.*' % R0324,
    '',
    '| # | type | D | body fields |',
    '|---|---|---|---|',
    '| T35 | `abort_owed` | D | *(protocol 6.4 and 12.2 row 31)* `reason` enum (the reasons of T31 `trial_aborted`); `source` enum[`supervision`,`abort_raised`,`run_loop_backstop`,`close_with_open_work`,`resolution_verdict`,`look_guard`]; `decision_logged` bool; `open_arrivals` [int]. Trial chain only. Written by `lab_orchestrator.World.owe_abort` / `write_abort_owed`, once per reason, before the abort\'s drain; read by `lab_eventlog.no_decision_point` and replayed by `lab_orchestrator.supervision_state` |',
    '',
    'T28 `usage_reconciliation` `counter_delta` values are int? (null in a lost-counter window whose counters were never',
    'read); T33 `spool_bytes_at_resolution` int? and `spool_sha256_at_resolution` hex64? (null when the spool could not',
    'be read at resolution); T29b `late_unread` rows carry `bytes_at_resolution` int? and `bytes_found` int?. The pure',
    'function `lab_eventlog.decision_eligibility(...)`, over `lab_eventlog.no_decision_point(...)`, is THE',
    'classification of every look (protocol 6.4): `lab_orchestrator.World` calls it before it writes each T19 look and',
    'decides only at an eligible one; `lab_verify_log` calls it for the FAIL-level check `reference_rule.agreement`',
    '(rules `decision_after_no_decision_point`, `abort_point_missing` and the missed crossing; INFO rows',
    '`NOT_ACTED_ON_restart_cap_before_decision` and `NOT_ACTED_ON_abort_before_decision`); `build_live_ab_results`',
    'writes it to `decision.json` (`eligibility`). A T23 receipt of a decision is chained only after',
    '`lab_orchestrator.anchor_commit_problem` finds its pushed commit bound to its anchor in the anchor repository',
    '(protocol 12.4).',
)
A3_7_1_9C = _lines(
    '| 9c | any | *(Amendment 2026-09-24, v3; root %s; protocol 6.4)* before any `monitor_update` is written (rows 2a, 4a, 7, 8, 10, 12), `lab_eventlog.decision_eligibility` over the chain so far finds the look not eligible (a decision is logged, a `drain` look, or a no-decision point precedes it) | the `monitor_update` is written exactly as without the abort; `decide()` is not called and no `decision` is appended; a crossing there is not acted on | as the row that wrote the look | — |' % R1605,
)
A3_7_1_21C = _lines(
    '| 21c | any | *(Amendment 2026-09-24, v3; root %s items 1 and 2)* a terminal abort becomes owed: supervision owes one (rows 20, 20a, 21a), an `AbortTrial` reaches the run loop, the run loop catches a server exception outside supervision, or the close of an ended trial finds an attempt open and no decision (the resolution verdict of row 21b writes its own after the drain) | `abort_owed` (D) with its `reason`, `source` and open arrivals, once per reason, BEFORE the drain reveals anything (protocol 6.4); every later look is not eligible (row 9c); a resumed invocation replays it and still owes the abort | `ABORTED` / as before | — |' % R1605,
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


_S53 = (b'### 5.3 Server supervision', b'### 5.4 Sampling parameters')
_S64 = (b'### 6.4 Failure-to-outcome table: every mode, one outcome',
        b'## 7. Pairing, the filtration')
_S122 = (b'### 12.2 Event schema', b'### 12.3 The hash rule')
_S124 = (b'### 12.4 Anchoring: mechanics', b'### 12.5 What the anchors prove, and what they do not')
_S131 = (b'### 13.1 Usage accounting for every try',
         b'### 13.2 The sampler receipt and the golden objects')
_S146 = (b'### 14.6 Trial order, unconditional execution, inspection between trials, pauses and '
         b'aborts', b'### 14.7 The operator is an AI agent session')
_S16 = (b'## 16. What is reported whatever the outcome', b'## Appendix A.')
_A44 = (b'### 4.4 Trial chain', b'### 4.5 `what_was_known`')
_A71 = (b'### 7.1 States and transitions', b'### 7.2 What is fsynced, and when')

INSERTIONS = (
    Insertion('protocol.5_3', 'protocol',
              b'path whose tokenized form is not the golden `model_path` refuses the invocation '
              b'with the preflight code\n`golden_objects`.\n', 'after', P3_5_3, *_S53),
    Insertion('protocol.6_4', 'protocol',
              b'`unresolved_worker` abort names in its `resolution` record the reason it '
              b'superseded (14.6).\n', 'after', P3_6_4, *_S64),
    Insertion('protocol.12_2', 'protocol',
              b'are: a trial chain, and the program chain beside P8. These additions are made '
              b'before any freeze.\n', 'after', P3_12_2, *_S122),
    Insertion('protocol.12_4', 'protocol',
              b'external evidence at all is accepted; any line that claims some is checked in '
              b'full.\n', 'after', P3_12_4, *_S124),
    Insertion('protocol.13_1', 'protocol',
              b"trial totals are `null` with the reason `unknown_usage` whenever any call's usage "
              b"is unknown.\n", 'after', P3_13_1, *_S131),
    Insertion('protocol.14_6', 'protocol',
              b'is `operator_discretion` does not apply to them.\n', 'after', P3_14_6, *_S146),
    Insertion('protocol.16', 'protocol',
              b'    episode, whether its completion tokens are complete, a lower bound or unknown '
              b'(13.1).\n', 'after', P3_16, *_S16),
    Insertion('architecture.4_4', 'architecture',
              b'only by `lab_eventlog.decision_receipt` (protocol 12.4).\n', 'after', A3_4_4,
              *_A44),
    Insertion('architecture.7_1.row_9c', 'architecture', b'| 9b | `LOOK` | ', 'after-line',
              A3_7_1_9C, *_A71),
    Insertion('architecture.7_1.row_21c', 'architecture', b'| 21b | `CLOSING`, `ABORTED` | ',
              'after-line', A3_7_1_21C, *_A71),
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
# Anchors and insertion
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
    the checks named.  The witness module (tests_repair_amendment_v3.GateTests) wraps it to set
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


def v2_texts(v2_receipt: dict) -> list:
    """[(key, document, text bytes)] of amendment v2's insertions, from its receipt."""
    return [(str(i.get('key')), str(i.get('document')), str(i.get('text', '')).encode('utf-8'))
            for i in (v2_receipt.get('insertions') or [])]


def v2_intact(docs: dict, v2_receipt: dict) -> dict:
    """Each v2 insertion text occurs exactly once in its document (none split, none doubled)."""
    return {key: docs.get(doc, b'').count(text) == 1 for key, doc, text in v2_texts(v2_receipt)}


def postconditions(old: dict, new: dict, v2_receipt: dict) -> tuple:
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
    intact = v2_intact(new, v2_receipt)
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
        'v2_insertions_intact': intact,
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
        'v2_insertions_intact': len(intact) == V2_INSERTIONS and all(intact.values()),
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
    changed (config.json only); the 12.2 text placed inside amendment v2's own 12.2 text
    (after its row 30); the 6.4 text also copied into vocabulary section 1."""
    out = {}
    cfg = new['config']
    k = cfg.rindex(b'}')
    out['config_byte_changed'] = dict(new, config=cfg[:k] + b' ' + cfg[k:])
    ins = next(i for i in INSERTIONS if i.key == 'protocol.12_2')
    p = new['protocol'].replace(ins.text, b'', 1)
    row30 = p.index(b'| 30 | `anchor_receipt_rejected` | ')
    nl = p.index(b'\n', row30) + 1
    out['v2_text_split'] = dict(new, protocol=p[:nl] + ins.text + p[nl:])
    six = next(i for i in INSERTIONS if i.key == 'protocol.6_4')
    p = new['protocol']
    s0, _ = section_span(p, VOCAB_MARKERS[1])
    nl = p.index(b'\n', s0) + 1
    out['vocabulary_section_1_touched'] = dict(new, protocol=p[:nl] + six.text + p[nl:])
    return out


def negative_control(old: dict, new: dict, v2_receipt: dict) -> dict:
    """Scratch copies in a fresh temporary directory, never the real files: the pre-images and
    each variant are written there, read back, and the acceptance predicate is applied.  Each
    variant must be refused; the checks each one fails are recorded."""
    real = {p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    tmp = Path(tempfile.mkdtemp(prefix='repair_amendment_v3_negative_control_'))
    out = {'how': ('postconditions() -- the predicate main() applies before writing -- on '
                   'scratch copies in a temporary directory, removed afterwards; one variant per '
                   'insertion, moved just outside its section, and three more: a byte of '
                   'config.json changed, the 12.2 text put inside amendment v2\'s 12.2 text, '
                   'the 6.4 text also put into vocabulary section 1'),
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
            post, ok = postconditions(scratch, read, v2_receipt)
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
    out['v2_split_variant_refused'] = bool(ex.get('v2_text_split', {}).get('refused')) and \
        'v2_insertions_intact' in ex['v2_text_split']['failed_checks']
    out['vocabulary_variant_refused'] = bool(
        ex.get('vocabulary_section_1_touched', {}).get('refused')) and \
        'vocabulary_sections_1_3_11_byte_identical' in \
        ex['vocabulary_section_1_touched']['failed_checks']
    return out


def inserted_text_form() -> dict:
    """Every inserted text: ends with a newline, no CR, ASCII except the dash the ARCHITECTURE
    table already uses, no trailing whitespace, no ``` and no heading line (either would move
    a section or fence bound), prose lines at most 120 characters (table rows excepted); no
    anchor of any insertion."""
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
             and set(v['non_ascii']) <= {'—'} for v in out.values())
    return {'per_insertion': out, 'ok': ok}


# ---------------------------------------------------------------------------
# The prose against the code
# ---------------------------------------------------------------------------
#: the reasons ``lab_eventlog.no_decision_point`` returns (the INELIGIBLE_REASONS keys minus the
#: two that are not a point); 6.4 names each
POINT_REASONS = ('server_restart_cap', 'server_start_failed', 'server_identity',
                 'receipt_mismatch', 'infrastructure', 'unresolved_worker', 'abort_owed')
#: the verifier's rule names and INFO consequences the prose names (quoted in lab_verify_log.py)
VERIFIER_NAMES = ('decision_after_no_decision_point', 'abort_point_missing',
                  'NOT_ACTED_ON_restart_cap_before_decision', 'NOT_ACTED_ON_abort_before_decision',
                  'decision_after_cap')
BUILDER_LABELS = ('DECISION_INVALID_LABEL', 'RESTART_CAP_INCOMPLETE_LABEL',
                  'ABORT_INCOMPLETE_LABEL', 'PROVISIONAL_LABEL')


def _ticked(text: str) -> list:
    return re.findall(r'`([A-Za-z_]+)`', text)


def _row(text: str, cell_start: str) -> str:
    return next(ln for ln in text.split('\n') if ln.startswith(cell_start))


def _ev(seq: int, etype: str, body: dict) -> dict:
    return {'seq': seq, 'type': etype, 'body': body}


def _look(seq: int, trigger: str = 'reveal') -> dict:
    return _ev(seq, 'monitor_update', {'trigger': trigger, 'n': seq})


def code_checks() -> dict:
    """What the new prose states, read back from the code of this checkout and run on
    synthetic chains with the code's own pure functions.  Returns the facts and ``gate``."""
    ev, orch, bld = lab_eventlog, lab_orchestrator, build_live_ab_results
    f: dict = {}
    g: dict = {}
    row31 = _row(P3_12_2, '| 31 |')
    src = row31.split('`source` (', 1)[1].split(')', 1)[0]
    f['row_31_sources'] = _ticked(src)
    f['code_abort_sources'] = list(ev.ABORT_SOURCES)
    g['row_31_names_exactly_the_abort_sources'] = f['row_31_sources'] == list(ev.ABORT_SOURCES)
    f['code_abort_owed_fields'] = sorted(ev.ABORT_OWED_FIELDS)
    g['row_31_names_exactly_the_abort_owed_fields'] = (
        sorted(ev.ABORT_OWED_FIELDS) == sorted(ev.EVENT_SCHEMA.get('abort_owed', {}))
        and all('`%s`' % k in row31 for k in ev.ABORT_OWED_FIELDS)
        and sorted(ev.ABORT_OWED_FIELDS) == ['decision_logged', 'open_arrivals', 'reason',
                                             'source'])
    g['abort_owed_is_trial_only_and_durable_in_the_prose'] = (
        'abort_owed' in ev.TRIAL_ONLY_TYPES and row31.rstrip().endswith('| yes |')
        and 'Row 31 is written on a trial chain only.' in P3_12_2)
    f['code_point_reasons'] = sorted(set(ev.INELIGIBLE_REASONS) - {'decision_logged', 'drain_look'})
    g['point_reasons_are_the_code_and_6_4_names_each'] = (
        f['code_point_reasons'] == sorted(POINT_REASONS)
        and all('`%s`' % r in P3_6_4 for r in POINT_REASONS))
    f['code_anchor_commit_problems'] = list(orch.ANCHOR_COMMIT_PROBLEMS)
    named = [c for c in _ticked(P3_12_4) if c in orch.ANCHOR_COMMIT_PROBLEMS]
    g['anchor_commit_problems_named_in_12_4'] = (
        sorted(set(named)) == sorted(orch.ANCHOR_COMMIT_PROBLEMS)
        and len(orch.ANCHOR_COMMIT_PROBLEMS) == 6)
    flat16 = ' '.join(P3_16.split())
    f['builder_labels'] = {k: getattr(bld, k, None) for k in BUILDER_LABELS}
    g['builder_labels_quoted_verbatim_in_16'] = all(
        isinstance(v, str) and '`%s`' % v in flat16 for v in f['builder_labels'].values())
    verify_src = (SOURCE_REPO / REL_VERIFY_LOG).read_text('utf-8')
    f['verifier_names_in_code'] = {n: ("'%s'" % n) in verify_src for n in VERIFIER_NAMES}
    g['verifier_rule_names_are_the_code'] = (all(f['verifier_names_in_code'].values())
                                             and all('`%s`' % n in P3_6_4 for n in VERIFIER_NAMES))
    summary_src = inspect.getsource(bld.build)
    g['summary_decision_is_the_result_and_logged_decision_beside_it'] = (
        "'decision': dobj['primary_result']" in summary_src
        and "['logged_decision'] = logged_kind" in summary_src)
    # -- behaviours, on synthetic chains --------------------------------------------------
    owed = _ev(5, 'abort_owed', {'reason': 'harness_defect', 'source': 'run_loop_backstop',
                                 'decision_logged': False, 'open_arrivals': [3]})
    point = ev.no_decision_point([_look(4), owed, _look(6, 'reveal')], None)
    f['no_decision_point_of_an_abort_owed'] = point
    g['no_decision_point_reads_abort_owed'] = point == {
        'seq': 5, 'reason': 'abort_owed', 'abort_reason': 'harness_defect',
        'source': 'run_loop_backstop'}
    sup = orch.supervision_state([owed], 3)
    f['supervision_state_pending_abort'] = sup.pending_abort
    g['supervision_state_replays_abort_owed'] = sup.pending_abort == 'harness_defect'
    chain = [_look(4), owed, _look(6)]
    after = ev.decision_eligibility(chain, None, reference_actions=['none', 'deploy_candidate'])
    before = ev.decision_eligibility(chain, None, reference_actions=['deploy_candidate', 'none'])
    f['crossing_after_the_point'] = after['crossing']
    f['crossing_before_the_point'] = before['crossing']
    g['crossing_after_the_point_not_acted_on_with_its_reason'] = (
        after['crossing'] is not None and after['crossing']['verdict'] == 'not_acted_on'
        and after['crossing']['reason'] == 'abort_owed'
        and bool(after['crossing'].get('reason_text'))
        and [lk['eligible'] for lk in after['looks']] == [True, False])
    g['crossing_before_the_point_missed_is_a_defect'] = (
        before['crossing'] is not None and before['crossing']['verdict'] == 'missed')
    states = orch.effective_worker_states([
        _ev(1, 'worker_resolved', {'arrival': 1, 'attempt': 1, 'state': 'alive_unresolved'}),
        _ev(2, 'worker_resolved', {'arrival': 1, 'attempt': 1, 'state': 'killed_reaped'})])
    f['effective_state_after_a_later_resolution'] = states.get((1, 1))
    g['an_unresolved_worker_stays_unresolved'] = states.get((1, 1)) == 'alive_unresolved'
    unresolved = ev.no_decision_point([_ev(7, 'worker_resolved', {
        'arrival': 1, 'attempt': 1, 'state': 'liveness_unknown'})], None)
    g['an_unresolved_worker_is_a_no_decision_point'] = (
        (unresolved or {}).get('reason') == 'unresolved_worker')
    rec = orch.reconciliation_windows([
        _ev(1, 'server_started', {'server_id': 'coder', 'smoke': {
            'usage': {'prompt_tokens': 3, 'completion_tokens': 2}}}),
        _ev(2, 'server_down', {'server_id': 'coder'})], ['coder'])
    f['lost_window_without_a_read_counter'] = rec
    g['unread_counter_delta_is_null'] = (
        len(rec) == 1 and rec[0]['counter_delta'] == {'prompt': None, 'predicted': None}
        and rec[0]['counters_lost'] is True)
    sch = ev.EVENT_SCHEMA
    late = sch['deposit_sealed']['late_unread'].item.fields
    g['null_fields_are_nullable_in_the_schema'] = (
        sch['usage_reconciliation']['counter_delta'].item.kind == 'null_or'
        and sch['worker_resolved']['spool_bytes_at_resolution'].kind == 'null_or'
        and sch['worker_resolved']['spool_sha256_at_resolution'].kind == 'null_or'
        and late['bytes_at_resolution'].kind == 'null_or'
        and late['bytes_found'].kind == 'null_or'
        and 'spool_unreadable' in ev.RESOLUTION_PROBLEMS)
    g['decision_receipt_commit_check_is_wired'] = (
        'commit_check(str(commit), str(branch), request)'
        in inspect.getsource(orch.decision_evidence_verdict))
    return {'facts': f, 'gate': g}


def _refuse(msg: str, obj=None) -> int:
    print('refusing: %s; NOTHING was written%s'
          % (msg, (': ' + json.dumps(obj, default=str)) if obj is not None else ''),
          file=sys.stderr)
    return 2


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

    # -- 2. amendment v2, named and verified ------------------------------------------
    try:
        v2_raw = V2_RECEIPT.read_bytes()
        v2 = json.loads(v2_raw)
    except (OSError, ValueError) as e:
        return _refuse('the amendment v2 receipt could not be read (%s)' % e)
    try:
        v2_committed = git_blob(PRE_REV, V2_RECEIPT_REL)
    except (OSError, subprocess.CalledProcessError):
        v2_committed = None
    written = v2.get('written') or {}
    intact_before = v2_intact(old, v2)
    predecessor = {
        'receipt': V2_RECEIPT_REL, 'receipt_sha256': sha(v2_raw), 'commit': PRE_REV,
        'status': ('kept: write-once, not edited and not superseded; v3 adds insertions to the '
                   'documents v2 wrote'),
        'insertions_whole_before': intact_before,
        'written_by_v2': {k: written.get(k) for k in ('config_sha256', 'architecture_sha256',
                                                      'protocol_sha256', 'cells_sha256')},
    }
    predecessor['gate'] = {
        'v2_receipt_is_the_pinned_bytes': sha(v2_raw) == V2_RECEIPT_SHA256,
        'v2_receipt_is_committed_in_474f9d8': v2_committed == v2_raw,
        'v2_commit_is_an_ancestor_of_head': git_is_ancestor(PRE_REV, 'HEAD') is True,
        'v2_wrote_the_preimages': (
            written.get('config_sha256') == pre['config_sha256']
            and written.get('architecture_sha256') == pre['architecture_sha256']
            and written.get('protocol_sha256') == pre['protocol_sha256']
            and written.get('cells_sha256') == pre['cells_sha256']),
        'v2_insertions_whole_in_the_preimages': (len(intact_before) == V2_INSERTIONS
                                                 and all(intact_before.values())),
    }
    if not gate('amendment_v2', predecessor['gate']):
        return _refuse('amendment v2 is not as pinned', predecessor)

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
    post, ok = postconditions(old, new, v2)
    if not ok:
        return _refuse('a postcondition failed', post)
    control = negative_control(old, new, v2)
    control['gate'] = {
        'every_moved_variant_refused_on_placement':
            control['every_moved_variant_refused_on_placement'] is True,
        'config_variant_refused': control['config_variant_refused'] is True,
        'v2_split_variant_refused': control['v2_split_variant_refused'] is True,
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
        'Resolved AFTER the fact, when the repair amendment v3 landed on top of it: '
        '`git show %s:experiments/live_ab/design/protocol_FINAL.md` hashes to this '
        'successor.' % PRIOR_SUCCESSOR_COMMIT[:7])
    new_sb = {
        'sha256': post['protocol_sha256'],
        'supersedes': ORIGINAL_PIN,
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'reason': (
            'NOT an Appendix B change: the pre-outcome amendment v3 of the EB1+EB5 repair '
            'subset, which makes the protocol and ARCHITECTURE_FINAL.md say what the code of '
            'the subset now does. PURE INSERTIONS of dated prose, nothing else: deleting them '
            'reproduces the v2 successor 6c0ebf2f byte for byte. config.json is not written, and '
            'the configuration block of Appendix B and of ARCHITECTURE 6.1 is byte-identical; '
            'no key is added, removed or changed. Protocol 5.3 (every owed abort written '
            'before its drain), 6.4 (decision eligibility: the durable no-decision point, '
            'abort_owed written by every abort path before its drain, a crossing after the '
            'point not acted on with its concrete reason, a crossing missed at an eligible '
            'look and a decision after the point LIVE_DECISION_INVALID, abort_point_missing), '
            '12.2 (row 31 abort_owed; null counter deltas, null unread spool seals), 12.4 (the '
            'pushed commit of a decision receipt bound to its anchor in the anchor repository), '
            '13.1 (a counter never read is null, never 0), 14.6 (the close of an abort begins '
            'with its point; an unresolved worker stays unresolved across resume; an unread '
            'spool is recorded unread) and 16 (item 17: the reported result, first match wins, '
            'an invalid decision never reportable). It changes no execution rule the code of '
            'the subset does not already perform, and no CPU cell, parameter, seed, horizon, '
            'estimator, outcome definition, monitor or decision threshold, alpha, margin, stop '
            'rule or sampling parameter, and none of the vocabulary sections 1, 3 and 11 this '
            'pin reads (verified byte-identical). The rule-block keys are byte-unchanged '
            '(digest cbfd1792); that digest covers no protocol text, so it does not show the '
            'absence of the changes listed here. Amendment v2 (6c0ebf2f, commit 474f9d8, '
            'receipt REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json) is kept: none of its texts '
            'is split or changed.'),
        'ruling': (
            'Root 2026-09-24 16:05 (reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md) '
            'items 1 and 2; root 2026-09-24 19:05 '
            '(reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md); root 2026-09-24 03:24 '
            '(reviews/decision_receipt_metadata_ruling_20260924_0324.md), the pushed-commit / '
            'anchor-head evidence; root 2026-09-23 21:14 '
            '(reviews/restart_cap_estimand_ruling_20260923_2114.md), unknown usage in the '
            'reconciliation. The pin amendment follows the standing root ruling of 2026-09-22 '
            '04:27 (reviews/protocol_pin_disposition_20260922_0422.md): "preserve the original '
            'pin; record an explicit post-freeze provenance amendment ... Do not replace the '
            'original sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial, stage or launch approval, not a CPU rerun, and not the '
            'code it describes (03fe0ca, 7ebffad and 9f0aff6 are separate commits). It '
            'certifies no run: no server was started and no model was run. Its code checks '
            'read names from the code and run the code\'s pure functions on synthetic chains; '
            'they are not the controls of experiments/live_ab_controls.'),
        'correction_to_the_owner_report': sb['correction_to_the_owner_report'],
        'prior_successors': prior + [demoted],
        'changing_commit_note': (
            'The commit that introduces a successor cannot carry its own hash, so '
            '"changing_commit_of_this_successor" is resolved in a LATER commit. The last '
            'entry above records the one for the %s successor (the repair amendment v2), '
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
        'schema': 'live_ab.repair_amendment_receipt.v3',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root: reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md items '
                      '1 and 2; reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md; '
                      'reviews/decision_receipt_metadata_ruling_20260924_0324.md; '
                      'reviews/restart_cap_estimand_ruling_20260923_2114.md (quoted in this '
                      'tool\'s docstring)'),
        'prepared_by': ('prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off'),
        'predecessor_amendment_v2': dict(predecessor),
        'documents_amended': [REL_ARCH, REL_PROTO],
        'documents_not_written': [REL_CONFIG],
        'insertions': [ins.describe() for ins in INSERTIONS],
        'code_the_prose_describes': [
            'lab_eventlog: no_decision_point, decision_eligibility, INELIGIBLE_REASONS, '
            'CROSSING_VERDICTS, ABORT_SOURCES, ABORT_OWED_FIELDS, WORKER_RESOLVED_FIELDS, '
            'RESOLUTION_PROBLEMS, EVENT_SCHEMA (abort_owed, usage_reconciliation, '
            'deposit_sealed)',
            'lab_orchestrator: World.owe_abort, World.write_abort_owed, World._look_eligibility, '
            'World._write_one_look, supervise_down, supervised_restart, resume_servers, '
            'health_poll, the run loop (abort_raised, run_loop_backstop), close_trial '
            '(close_with_open_work, resolution_verdict), supervision_state, '
            'effective_worker_states, phase_resolution_verdict, resolve_previous_workers, '
            'assert_resolved_before_interrupt, resolve_worker / _resolution_body, seal_deposit, '
            'reconciliation_windows, anchor_commit_problem, decision_evidence_verdict, '
            'judge_receipt_line, World.anchor_commit_check',
            'lab_verify_log: reference_rule.agreement (_check_decision_eligibility: '
            'decision_after_no_decision_point, abort_point_missing, NOT_ACTED_ON_* INFO rows, '
            'the missed crossing), server.lifecycle decision_after_cap, workers.resolved',
            'build_live_ab_results: eligibility_object, decision_object (first match wins), '
            'DECISION_INVALID_LABEL, RESTART_CAP_INCOMPLETE_LABEL, ABORT_INCOMPLETE_LABEL, '
            'PROVISIONAL_LABEL, build (summary decision = primary_result, logged_decision)',
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
            'harness_file_sha256 of every file of the harness pin', 'rule_block_sha256',
            'llama_cpp.serving_manifest_sha256 and the serving-manifest artifact'],
        'runs_of_this_step_before_this_receipt': runs,
        'runs_after_this_receipt': ('the suites run after this receipt are recorded in the '
                                    'commit that adds it and in the owner report'),
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server, build or network request; text '
                             'edits, digests, git reads, and the pure functions of the harness '
                             'on synthetic in-memory chains'),
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
