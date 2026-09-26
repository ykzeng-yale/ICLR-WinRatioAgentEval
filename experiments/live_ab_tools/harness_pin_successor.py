"""The harness pin successor of the EB1+EB5 subset: exact old/new pins, prior observations kept.

    harness_pin_successor.py [--repo DIR] [--predecessor REV] [--out-dir DIR] [--no-suites]
                             [--runs-of-this-step FILE]

Root 20:40 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:16``, EB1 route (a)): "The
orchestrator is in the harness pin: record the pre-outcome pin successor and preserve the old
pin and all prior observations."  Root 21:14 (reviews/restart_cap_estimand_ruling_20260923_2114.md
on main, item 2): send the EB1 lifecycle and EB5 resolution code and controls "with old/new
hashes and no loaded run".  Root 07:03 (reviews/eb1_fixture_and_wip_delta_20260924_0703.md on
main, items 1 and 3): for the compiled C test double "retain the C source, compiler/version,
source digest and exact control result"; "A missing temp cache must rebuild or make the control
fail visibly"; "run controls alone, and submit one immutable exact-pinned subset with
completed/planned counts, failures, resource use and timestamps".

WHAT IT COMPUTES, WITHOUT EDITING ANY EXISTING FILE (every value from git objects unless named):

1. The predecessor harness map at PREDECESSOR (b049307) with ``lab_common.harness_file_hashes``
   semantics -- the top-level ``experiments/live_ab/*.py`` files plus ``config.json``, sha256 of
   each file's bytes -- read from ``git`` blobs; its canonical digest (``lab_common.
   sha256_canonical`` of the name -> sha256 map) must be PREDECESSOR_CANONICAL (5675cc5e, 33
   entries) or the tool REFUSES.  A revision git cannot resolve REFUSES (``predecessor_missing``).
2. The successor map at HEAD, checked equal to ``lab_common.harness_file_hashes()`` imported
   from the working tree of ``--repo`` (a clean tree is required, so the two must agree).
3. Per changed or added harness entry: old sha256, new sha256, the sha256 of its unified diff
   (DIFF_ARGV, fixed options, user git configuration ignored), line counts, the commits of
   ``PREDECESSOR..HEAD`` that touch it, and a check that ``git apply`` of that diff to the old
   bytes reproduces the new bytes.  The same for every other file the subset changes.
4. REUSED_FILES (``experiments/local_stream``) digests at both revisions (must be unchanged);
   the five decision-defining modules byte-unchanged; the rule block (must be RULE_BLOCK at both
   revisions); config.json, ARCHITECTURE_FINAL.md, protocol_FINAL.md, cells.json and the real
   serving manifest old/new, cross-checked against the pre-outcome amendments (AMENDMENTS: v2
   474f9d8, v3 56df17f, v4 90219f2) whose receipts HEAD carries: each receipt added by its own
   commit, an ancestor of HEAD; each digest it says it wrote equal to the blob at that commit;
   v3 naming the v2 receipt and v2's written digests, v4 naming v3's; and each HEAD value equal
   to the value written by the LATEST amendment that records it (``amendments``; the pin
   history of every document b049307 -> v2 -> v3 -> v4 -> HEAD from git blobs).
5. The prior observations that are NOT reissued (PRIOR_OBSERVATIONS): each file's sha256, and
   every 64-hex value it carries classified against the b049307/HEAD digests of the tracked
   files (which of its pins moved, which did not, which were already historical at b049307).
6. The compiled C test double (``experiments/live_ab_controls/sm_fixture.py``): its C sources
   (string constants of that committed file) with their sha256, the compile argv, the compiler
   path and ``clang --version``; checks that its outputs appear nowhere in the freeze tree; and
   five missing-cache controls under isolated temporary roots (never the shared cache).
7. Unless ``--no-suites``: the five suites, run one after another (never two at once), each
   with its exact argv, planned (loader) and completed (``Ran``) counts, verdict line, skip
   reasons, failure headers, wall time, start/end UTC, child rusage, host snapshots before and
   after, and a ``ps`` sampler that lists any watched process outside the suite's own tree
   (the evidence that it ran alone; sampled, not continuous; a process the suite itself
   orphans is told apart from a foreign one, see ``watched_outside``) -- and, per suite, the
   compiled test double it actually executed (``fixture_uses``: the lines ``sm_fixture``
   logged during the suite, with every output SHA-256 and the compiler and linker that built
   it), which the exclusion check of 6 then searches the freeze tree for as well (review of
   988baf7, reviewer 2 finding 6: those digests were recorded nowhere) -- and each suite's FULL
   stdout and stderr, retained write-once as a deterministic gzip (mtime 0), whether or not the
   suite passed, with the compressed and uncompressed SHA-256/bytes of each recorded in its run
   (the uncompressed digest equal to the ``stderr_sha256``/``stdout_sha256`` already kept).
   WHERE THE LOGS LIVE: DURING the run every log is written write-once under a fresh temporary
   staging directory created outside ``--repo`` (never under it, checked), so a real five-suite
   run against ``--out-dir`` inside the repository never makes ``git status`` see a new file
   mid-run (the defect this fixes: the tool's own end-of-run tree check, comparing
   ``worktree_state()`` before and after, used to see the untracked logs it had just written
   into the tree and refuse the whole run as ``tree_changed_during_the_run``, even on an
   otherwise clean pass).  Only AFTER that end-of-run tree check has passed, and every other
   problem list is empty, are the logs promoted write-once into the tree at
   ``<out-dir>/pin_logs/<receipt stamp>/<suite>.std{out,err}.gz``, next to the receipt this
   same call is about to let main() write -- a receipt is never written without its logs there,
   nor are the logs promoted without a receipt following.  On a REFUSED or otherwise
   problem-carrying run the logs are never promoted into the tree at all: they stay retained,
   at the staging location, beside the refused draft main() writes under its own temporary
   directory, and main() prints where.  Promotion re-verifies the write-once digest at the
   final path (identical bytes already there is a no-op; different bytes REFUSES,
   ``pin_log_mismatch``), so retention is write-once end to end regardless of where a log
   currently sits; a red run of RED_PIN_RUN_20260926_1227.json could not be diagnosed from the
   tail and digest alone, and a write, read-back or digest failure REFUSES the whole receipt
   (``pin_log_*``), never silently drops the log.  UNDECIDED, flagged for root rather than
   decided here: nothing ages these logs out, and they are committed the same as the receipts
   (no ``.gitignore`` exclusion); from the two most recent real receipts' recorded
   ``stdout_bytes``/``stderr_bytes`` a full five-suite
   run is on the order of several hundred KB of retained gzip per run, permanently, at the
   observed cadence of this branch -- this keeps every red diagnosable (the point of this fix)
   but root should decide a retention or archival policy before it is routine.
8. The receipts this one SUPERSEDES (SUPERSEDES: path, SHA-256, why; each stays byte-identical),
   with a guard (``superseded_receipts_incomplete``) that REFUSES when a committed
   ``results/live_ab/HARNESS_PIN_SUCCESSOR_*.json`` at HEAD names no SUPERSEDES entry (root
   01:17 repair: a run at c5817f9 omitted the already-accepted ..._2009 receipt this way), and
   every red run of the subset so far, with the root findings answered since the review
   of 988baf7 and their fix commits (DISCLOSED_RED_RUNS; review of 988baf7, reviewer 2 finding
   5; root 16:05 "the revised pin must include the failure history and exact changed bytes"),
   and the mutually exclusive mutation partition of the final adversarial verification of
   8f0b4ae reconciled from its logs (MUTATION_PARTITION_8F0B4AE; root 07:10: the 05:18
   headline "double-counts two"), refused unless it is exclusive and exhaustive
   (``partition_problems``).
9. The exact changed bytes since the LATEST superseded receipt HEAD carries (``since_the_
   superseded_receipt``): its successor map re-derived from the git blobs at the head it
   recorded (it must reproduce), and per harness entry or document moved since then the same
   diff record as 3 (commits, diff digest, ``git apply`` reproduction).
10. With ``--runs-of-this-step FILE``: the runs of the step that made this receipt, made before
   the tool ran (a JSON list; each row ``id``, ``utc``, ``command``, ``result``, any other
   keys kept), copied in with the file's SHA-256 -- every run, pass or fail; a malformed file
   REFUSES.

It writes ONE write-once receipt ``<out-dir>/HARNESS_PIN_SUCCESSOR_<UTC>.json``.  The default
out-dir is ``results/live_ab``; ``--no-suites`` is refused there, so a receipt in results always
carries the solo-run suites.  Every refusal names its problems and writes nothing.

Nothing here starts a model, a llama-server, a llama.cpp build or a network request.  It
compiles the C test double (root 07:03 item 1 authorizes that fixture) under temporary roots,
and the suites it runs start their own loopback mocks.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Mapping

HERE = Path(__file__).resolve().parent
DEFAULT_REPO = HERE.parent.parent
RESULTS_REL = 'results/live_ab'
SCHEMA = 'live_ab/harness_pin_successor-v1'
STATUS = 'PROPOSED pre-outcome pin successor for root review; not a freeze'
PY = sys.executable

#: The reviewed predecessor revision (root 20:40 reviewed this head) and its harness map.
PREDECESSOR = 'b049307ff62153a054f61b6179291ba987de2ba1'
PREDECESSOR_COUNT = 33
PREDECESSOR_CANONICAL = '5675cc5ef970328834314480ec33d0edf237f38c1a3d977d3d22e93dc71f3fee'
#: The rule block (lab_common.RULE_BLOCK_KEYS) of the b049307 config.json; must not move.
RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
LIVE_REL = 'experiments/live_ab'
REUSED_REL = 'experiments/local_stream'
CONFIG_REL = LIVE_REL + '/config.json'
DOCUMENTS = {
    'config.json': (CONFIG_REL,
                    'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824'),
    'ARCHITECTURE_FINAL.md': (LIVE_REL + '/design/ARCHITECTURE_FINAL.md',
                              '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab'),
    'protocol_FINAL.md': (LIVE_REL + '/design/protocol_FINAL.md',
                          '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b'),
    'cells.json': ('experiments/live_ab_validation/cells.json',
                   '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'),
}
VOCABULARY_ORIGINAL = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
SERVING_MANIFEST_REL = RESULTS_REL + '/freeze/serving_manifest.json'
AMENDMENT_COMMIT = '474f9d82aae2b3979910d8a99d8305b5d7bc44c1'
AMENDMENT_RECEIPT_REL = RESULTS_REL + '/REPAIR_AMENDMENT_V2_RECEIPT_20260924_0927.json'
AMENDMENT_V3_COMMIT = '56df17f72b17744d89564d0bf05f3fa84f4b8e1d'
AMENDMENT_V3_RECEIPT_REL = RESULTS_REL + '/REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218.json'
AMENDMENT_V4_COMMIT = '90219f2437c7b4d6ef9e4c3869a242365412c0a7'
AMENDMENT_V4_RECEIPT_REL = RESULTS_REL + '/REPAIR_AMENDMENT_V4_RECEIPT_20260925_1120.json'
#: The pre-outcome amendments of the subset, oldest first: the commit that wrote each, its
#: write-once receipt, and which key of the receipt's ``written`` carries which pin.  v3
#: (reviews/eb1_eb5_summary_repair_interim_20260924_2208.md: "finish and commit amendment v3
#: ... and issue a fresh pin receipt") inserts text into ARCHITECTURE and the protocol, moves
#: cells.json, writes no config.json and no serving manifest; v2 stays as written.  v4
#: (reviews/predecision_abort_reporting_ruling_20260925_0710.md: "a narrow v4 additive
#: pre-outcome amendment ... Preserve v2/v3") inserts protocol 16 item 18 and ARCHITECTURE
#: 3.15, moves cells.json, writes no config.json and no serving manifest; v2 and v3 stay.
AMENDMENTS = (
    {'name': 'v2', 'commit': AMENDMENT_COMMIT, 'receipt': AMENDMENT_RECEIPT_REL,
     'keys': {'config.json': 'config_sha256', 'ARCHITECTURE_FINAL.md': 'architecture_sha256',
              'protocol_FINAL.md': 'protocol_sha256', 'cells.json': 'cells_sha256',
              'rule_block': 'rule_block_sha256_on_disk',
              'serving_manifest_canonical': 'artifact_sha256_canonical',
              'serving_manifest_file': 'artifact_file_sha256'},
     'names_predecessor': None},
    {'name': 'v3', 'commit': AMENDMENT_V3_COMMIT, 'receipt': AMENDMENT_V3_RECEIPT_REL,
     'keys': {'config.json': 'config_sha256', 'ARCHITECTURE_FINAL.md': 'architecture_sha256',
              'protocol_FINAL.md': 'protocol_sha256', 'cells.json': 'cells_sha256',
              'rule_block': 'rule_block_sha256_on_disk'},
     'names_predecessor': {'name': 'v2', 'field': 'predecessor_amendment_v2',
                           'written_field': 'written_by_v2'}},
    {'name': 'v4', 'commit': AMENDMENT_V4_COMMIT, 'receipt': AMENDMENT_V4_RECEIPT_REL,
     'keys': {'config.json': 'config_sha256', 'ARCHITECTURE_FINAL.md': 'architecture_sha256',
              'protocol_FINAL.md': 'protocol_sha256', 'cells.json': 'cells_sha256',
              'rule_block': 'rule_block_sha256_on_disk'},
     'names_predecessor': {'name': 'v3', 'field': 'predecessor_amendment_v3',
                           'written_field': 'written_by_v3'}},
)
#: Decision-defining modules the restart cap must not touch (root 21:14, cap invariance).
DECISION_MODULES = ('lab_coin.py', 'lab_design.py', 'lab_enclosure.py', 'lab_monitor.py',
                    'lab_reference_rule.py')
#: Prior observations kept, NOT reissued by this successor.
PRIOR_OBSERVATIONS = (
    RESULTS_REL + '/SMOKE_RECEIPT_smoke_4167e395ccfd.json',
    RESULTS_REL + '/PROSPECTIVE_LAUNCH_RECORD_20260923_1922.json',
    RESULTS_REL + '/PROSPECTIVE_LAUNCH_RECORD_20260923_2030.json',
    RESULTS_REL + '/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json',
    RESULTS_REL + '/PRE_RUN_BUNDLE_20260923_2035.json',
    RESULTS_REL + '/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json',
    RESULTS_REL + '/PATCH_STATE_AMENDMENT_RECEIPT_20260923_1933.json',
)
#: Committed statements of the harness count/state at b049307 (path, line, fragment it carries).
COUNT_STATEMENTS = (
    (RESULTS_REL + '/ABSENT_DRAIN_AND_REQUEST_RECONCILIATION.json', 33, '33 (32'),
    (RESULTS_REL + '/LAUNCH_WIRING.json', 41, '"33, unchanged"'),
    (RESULTS_REL + '/CONFIG_AMENDMENT_RECEIPT_20260923_1804.json', 123, '"harness_files": 33'),
    (RESULTS_REL + '/PATCH_STATE_AMENDMENT_RECEIPT_20260923_1933.json', 169,
     '"harness_file_hashes_unchanged": true'),
)
#: Where pins are looked up (tracked files at both revisions, recursive).
TRACKED_PREFIXES = ('experiments/live_ab', 'experiments/live_ab_serving',
                    'experiments/live_ab_validation', 'experiments/live_ab_tools',
                    'experiments/live_ab_controls', 'experiments/local_stream',
                    'results/live_ab', 'src/winstats.py')
OWN_FILES = ('experiments/live_ab_tools/harness_pin_successor.py',
             'experiments/live_ab_tools/tests_harness_pin_successor.py')
FIXTURE_REL = 'experiments/live_ab_controls/sm_fixture.py'
FIXTURE_CONTROL_TESTS = (
    'tests_sm_manifest.RuntimeTests.test_control_the_unchanged_build_reverifies',
    'tests_sm_manifest.RuntimeTests.test_one_library_byte_changed_after_assembly_refuses')
PRESCRIBED_LABSBX = '/private/tmp/labsbx'
FIXTURE_CONTROL_TAGS = ('A_rebuild', 'B_no_compiler', 'C_partial_cache',
                        'D_real_control_rebuilds', 'E_real_control_no_compiler')
#: The log every ``sm_fixture.compiled()`` appends to under its temporary directory (review of
#: 988baf7, reviewer 2 finding 6): which binaries each suite actually executed.
FIXTURE_USES_LOG = 'eb1c_sm_fixture_uses.jsonl'

#: The receipts this one supersedes (write-once: each stays, byte-identical), and why.
SUPERSEDES = (
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260924_1217.json',
     'sha256': '25010726114a05415c519a5c4ab297d75f8bdeeca9a0f8d91930dc6c170f2462',
     'head_when_written': '988baf7',
     'why': ('the subset fix answering the two reviews of 988baf7 changes harness files '
             '(lab_orchestrator, lab_eventlog, lab_verify_log, build_live_ab_results); that '
             'receipt pins the 988baf7 harness and stays as written')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260924_1635.json',
     'sha256': '7e5cb1c3f333562d1b91cbdb31d8cb7e68a0e17126c69237fc5dc538023d6db5',
     'head_when_written': '03fe0ca',
     'why': ('the same harness pins (03fe0ca), but its suites were neither all green nor solo: '
             'live_ab failed the stochastic tests_lab_design.CoinTests.test_coin_balance_10k '
             '(10,000 coins outside [4850, 5150], about a 0.3% false failure rate; lab_coin '
             'unchanged since b049307), and a foreign real llama-server of another project '
             'ran on the host during it; this receipt re-runs the suites on a quiet host')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260924_1732.json',
     'sha256': '198eae6a3ddb912e555073306b38abfaebc22b1e1db305435e66a1b24dc0cf16',
     'head_when_written': '591ebcd',
     'why': ('it pins the 591ebcd harness (canonical 0f20e087) and the amendment-v2 documents; '
             'since then 7ebffad (root 16:05) and 9f0aff6 (root 19:05) changed harness files '
             '(lab_eventlog, lab_orchestrator, lab_verify_log, build_live_ab_results, '
             'tests_lab_chain) and amendment v3 (56df17f) moved ARCHITECTURE_FINAL.md, '
             'protocol_FINAL.md and cells.json; root 22:08: it "does not pin 9f0aff6"; its '
             'suites (all passed, solo) stay the observation of the 591ebcd tree only')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260925_0027.json',
     'sha256': '889c36c6f7b419f39d20f292bef2186f30b5f745a1202ffd9fcced05151c9300',
     'head_when_written': '79e60d4',
     'why': ('it pins the 79e60d4 harness (canonical b0a45e31) and the amendment-v3 documents; '
             'since then bdee21b (root 07:10, choice (b)) changed build_live_ab_results.py (a '
             'harness entry), amendment v4 (90219f2) moved ARCHITECTURE_FINAL.md, '
             'protocol_FINAL.md and cells.json, and 2113dbd, c001354, f54d215, bdee21b and '
             '90219f2 added controls and tools; its failure history lacked rows (the final '
             'verification of 8f0b4ae, finding 8: root 02:54, the discarded 11:41 pin run, the '
             '988baf7 witness survivor, root\'s 22:08 attempt); root 01:10 accepted it as '
             'disclosed engineering-test evidence with solo=false, which it keeps: its suites '
             '(1,782 of 1,782 passed, not solo) stay the observation of the 79e60d4 tree only')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260925_2009.json',
     'sha256': '3745631750c3913f40069185971be8b3c2bd44e4538ab2fdc07cbdc7773da101',
     'head_when_written': '98ce004',
     'why': ('it pins the 98ce004 harness (canonical f9a7703f) of the accepted EB1+EB5 tagged '
             'subset (root 22:20 on main, the bounded disposition of tag '
             'session60-eb1-eb5-subset-v1); its preservation companion results/live_ab/'
             'DELIVERY_STEP_RUNS_20260925_2014.json travels with it and is not itself '
             'reissued; since 98ce004 this branch changed the harness again (the EB2-EB4 '
             'driver work); its suites (1,889 of 1,889 passed, solo=false) stay the '
             'observation of the 98ce004 tree only')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260926_0600.json',
     'sha256': 'e35c4e5e745b6e52e73c7651e2385dc9832e41a4b715bea02f43b9c1bc1f1724',
     'head_when_written': 'ced7a13',
     'why': ('it pins the ced7a13 harness (canonical 7881023e) accepted by root 07:18 as a '
             'bounded non-solo engineering pin (drivers steps 1-3, the replay-resume repair '
             'and the section 11.5 core-control port); its runs-of-this-step input is '
             'deposited at results/live_ab/pin_inputs/HARNESS_PIN_SUCCESSOR_20260926_0600.'
             'runs_of_this_step.json; since ced7a13 the drivers step 4 work changed the '
             'harness again (the model-free stage-1 golden/conformance driver); its suites '
             'stay the observation of the ced7a13 tree only')},
    {'path': RESULTS_REL + '/HARNESS_PIN_SUCCESSOR_20260926_0958.json',
     'sha256': '052f141659b27533cc77f0582ce991169afc75595559226de87fa4b770bf6675',
     'head_when_written': 'b229060',
     'why': ('it pins the b229060 harness (canonical 5ec14626) that root 10:19 accepted only as '
             'a bounded engineering run receipt, NOT the stage-1 conformance logic it pinned; '
             'its runs-of-this-step input is deposited at results/live_ab/pin_inputs/'
             'HARNESS_PIN_SUCCESSOR_20260926_0920.runs_of_this_step.json and its red first '
             'attempt at results/live_ab/RED_PIN_RUN_20260926_0909.json; since b229060 the '
             'stage-1 repair (e6a8d7d: ordered-prompt binding, the frozen conformance '
             'predicate, the mock guard before resume) changed the harness again; its suites '
             'stay the observation of the b229060 tree only')},
)

#: Every red run of the subset so far (review of 988baf7, reviewer 2 finding 5; root 16:05:
#: "the revised pin must include the failure history"), and the root findings answered since
#: that review with their fix commits (``kind`` review_finding).  Each row is an observation of
#: an earlier run or review, named with the log it left where one is kept (the session's
#: scratch logs are not tracked; their SHA-256 identifies the bytes read).  A red run that a
#: commit message already reported is listed again here, so this list is the whole history.
#: A run meant to fail (a pre-fix negative control) is a red run too and says so.  Scope: the
#: runs of the owner and of the reviews known to the session, and every root finding against
#: the subset's own code (from 8df2558 on).  The 0027 receipt called this list the whole
#: history but lacked four of them (the final verification of 8f0b4ae, finding 8); they are the
#: rows after the v3 step, with that verification and the step answering it.  The rows after
#: 2113dbd: root 07:10 (finding 9 ruled (b); the 05:18 headline arithmetic), the reproduction
#: step (f54d215), the root 07:10 code step (bdee21b) and the amendment-v4 step (90219f2).
DISCLOSED_RED_RUNS = (
    {'kind': 'red_run',
     'when': '2026-09-24 03:06-03:43 local, integration solo run at 79bb1ab',
     'suite': 'live_ab_controls', 'result': 'Ran 357 tests, FAILED (failures=2)',
     'failures': ['tests_eb5_resolution.C3GarbageSpoolLine.test_c3_mutation_no_kill_keeps_'
                  'sending_and_is_refused (AssertionError: pid_alive after obs.close(); a '
                  'timing race in the control: the worker exits 43-64 ms after the POST the '
                  'observer answered)',
                  'tests_sm_entry.SM10SelfComparisonMutants.test_mutant_digest_self_accepts_'
                  'the_null_digest_of_sm3 (the real host gate refused on a DEGRADED scan; '
                  'the helper printed "offending detectors []")'],
     'log_sha256': 'e3f2b645cba6c95a84099c5234f32d109e21838a66ba6bd9a98b1bc09ce4c37f',
     'disposition': 'both controls repaired by the subset fix (K1, K2); the second '
                    'run of the same suite at 79bb1ab was OK'},
    {'kind': 'red_run',
     'when': 'review of 988baf7 (reviewer 2), solo runs in a clone of 988baf7',
     'suite': 'live_ab_controls (single controls)',
     'result': ('C3 mutation control failed 8 of 20, C6 mutation control failed 5 of 6 '
                '(ProcessLookupError at its killpg), C2 mutation control failed 1 of 6 '
                '("2 != 1"), the whole tests_eb5_resolution module failed 2 of 3'),
     'log_sha256': None,
     'disposition': 'the three controls made deterministic by the subset fix (K1)'},
    {'kind': 'red_run',
     'when': 'review of 988baf7 (reviewer 1), an independent clone of 988baf7',
     'suite': 'live_ab_controls',
     'result': ('C6 mutation control ERROR 3 of 3 (ProcessLookupError); other non-passes of '
                'a contended run were host_not_quiescent refusals caused by a concurrent '
                'suite and passed on quiet solo reruns'),
     'log_sha256': None,
     'disposition': 'repaired by the subset fix (K1)'},
    {'kind': 'red_run',
     'when': '2026-09-24 14:0x UTC, this session, the pre-fix clone of 988baf7',
     'suite': 'live_ab_controls (single controls, solo)',
     'result': ('C3 mutation control failed 2 of 6, C6 mutation control failed 2 of 4, C2 '
                'mutation control failed 0 of 4'),
     'log_sha256': {
         'c3': ['365073e4f3363ef5ddf8ed14c367b7b107eea746d4cabb0899c19a255177c181',
                'e2118de0987b2e87e8ddd9a3b834da801e589b6b4594f2f0ba6a8e61cd6f038b'],
         'c6': ['a10d3174f90e42e6d11a03ebf58c2ff70ea79dfbf7d09e3e819abfb8f240fa90',
                'ed81c61b4cdb36bc50232344fe4bc5b68df70dea5377ba79b6f7ed12fcf5bb92']},
     'disposition': 'the reproduction the K1 repair started from'},
    {'kind': 'red_run',
     'when': '2026-09-24 14:52-15:25 UTC (10:52-11:25 local), the subset fix before its '
             'commit 03fe0ca (run r1)',
     'suite': 'live_ab_controls',
     'result': ('Ran 393 tests in 1942.083s, FAILED (failures=2): tests_eb5_resolution.'
                'C6DispatcherExitsMidEpisode test_c6_mutation_no_resolution_reveals_a_live_'
                'orphan (the orphan was answered by the resumed server) and test_c6_mutation_'
                'the_kill_fails_so_the_resume_refuses (the interrupted reveal refused after '
                'the new alive_unresolved record); live_ab 766 OK (skipped=1), live_ab_tools '
                '137 OK (skipped=1), live_ab_serving 193 OK, validation 207 OK'),
     'log_sha256': {'controls': '1d59865ed879412ec30123ed30fb5af3d766901b1e34a061a2b5de108793b125',
                    'summary': 'acad0c909656fba311e427845ee5b462cb17d77e8b365abd62ca5eefa585799b'},
     'disposition': ('both controls repaired inside 03fe0ca (commit message: "both repaired '
                     'here, tests_eb5_resolution + the new module then 67 OK")')},
    {'kind': 'red_run',
     'when': '2026-09-24 15:44-16:35 UTC, the suites of receipt HARNESS_PIN_SUCCESSOR_20260924_'
             '1635 at 03fe0ca (commit 591ebcd)',
     'suite': 'live_ab (and the solo evidence of all five suites)',
     'result': ('live_ab Ran 766, FAILED (failures=1): tests_lab_design.CoinTests.test_coin_'
                'balance_10k (10,000 coins outside [4850, 5150]); solo=False: a foreign real '
                'llama-server of another project (pids 28762, 31001, started 15:38:48 and '
                '15:45:00 UTC) and a foreign shell of this session were sampled; the other '
                'four suites OK'),
     'log_sha256': {'tool_stdout': 'c0a30e4676f2e7daf383636b61d612ae73cbb7aa572596a79ccce6b5'
                                   'abce31f9'},
     'disposition': ('not repaired: a stochastic self-test of the unchanged lab_coin (about a '
                     '0.3% false failure rate per run; lab_coin and the test are the b049307 '
                     'blobs); the receipt stays as written and was superseded by the 1732 '
                     're-run (all passed, solo); any later failure of it is recorded again')},
    {'kind': 'review_finding',
     'when': 'root 16:05 ruling (reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md, '
             'main 78df9e5) on 988baf7',
     'suite': 'source review (not a test run)',
     'result': ('two high findings supported: (1) a non-cap predecision owed abort could still '
                'reach take_decision during its drain; (2) the orchestrator, the verifier and '
                'the results builder used different decision-eligibility rules'),
     'log_sha256': None,
     'fix_commits': ['03fe0ca', '7ebffad'],
     'disposition': ('03fe0ca: no_decision_point for the cap, supervision-owed and triggered '
                     'aborts; 7ebffad: every abort path writes a durable abort_owed before its '
                     'drain, one lab_eventlog.decision_eligibility used by all three paths, '
                     'controls tests_decision_eligibility (26) with before/after ordering, '
                     'unresolved worker across resume and the normal eligible crossing')},
    {'kind': 'red_run',
     'when': '2026-09-24 13:49-14:03 local (17:49-18:03 UTC), the root 16:05 step before 7ebffad '
             '(wip1, wip3)',
     'suite': 'live_ab tests_lab_chain+tests_lab_isolation; live_ab_controls '
              'tests_decision_eligibility (first version)',
     'result': ('wip1 Ran 103, FAILED (failures=1): SchemaTests count 53 != 52 (the schema '
                'grew by abort_owed; the test was updated); wip3 Ran 25, FAILED (failures=2): '
                'two helper errors in the new test (fixed); wip2 60 OK and wip4 9 OK'),
     'log_sha256': {'wip1': '12bc05af75ebd48bddb66f06105835c083b9a10b73b0e4ea24041a8f4f0927ea',
                    'wip3': 'f459aab7e9e639f859773e0c6fde48272e85933fc2403c066d0e26a8511ac014'},
     'disposition': 'test updates inside 7ebffad; production bytes not involved'},
    {'kind': 'red_run',
     'when': '2026-09-24 14:03 local (18:03 UTC), before1: the new tests_decision_eligibility '
             'on a git archive of 159e747 (a pre-fix negative control, meant to fail)',
     'suite': 'live_ab_controls tests_decision_eligibility',
     'result': 'Ran 25 in 174.0s, FAILED (failures=13, errors=22, skipped=3)',
     'log_sha256': {'before1': '7e80d90fafed596480a7abff827359f1eacdd74ee255550725b54d3ccbbb519d'},
     'disposition': ('expected: the backstop, refused-restart and hook drain crossings read '
                     'reference_rule.agreement LIVE_DECISION_INVALID at 159e747 with no '
                     'abort_owed; the unresolved-worker resume controls already passed there')},
    {'kind': 'red_run',
     'when': '2026-09-24 18:03-19:01 UTC, full1 of the root 16:05 step (before 7ebffad)',
     'suite': 'live_ab_controls',
     'result': ('Ran 418 in 3173.1s, FAILED (failures=1): tests_eb1_supervision.HealthPollTests.'
                'test_the_restart_count_reaches_the_cap_and_the_next_down_restarts_nothing '
                '(the event tail now ends with the cap\'s abort_owed); live_ab 766 OK '
                '(skipped=1), tools 137 OK (skipped=1), serving 193 OK, validation 207 OK'),
     'log_sha256': {'controls': 'e6108f45b0012ab4c3deb839249fdca04de55c8ef75ffc44609e43ed26dcc048'},
     'disposition': 'deterministic; the test updated inside 7ebffad (fix1: 90 OK)'},
    {'kind': 'red_run',
     'when': '2026-09-24 19:06-19:57 UTC, full2 of the root 16:05 step on the bytes committed as '
             '7ebffad',
     'suite': 'live_ab_controls',
     'result': ('Ran 419 in 3068.4s, FAILED (failures=2): tests_eb1_receipt_attribution.'
                'ProdCaseBExternalReceipt.test_e2_the_same_across_a_pause_and_resume_with_the_'
                'anchor_carried_over (the real host gate refused three resumes: detector '
                'baseline-active, mediaanalysisd active) and tests_sm_entry.SM8AtTheRestart.'
                'test_sm8_a_library_changed_before_the_restart_refuses_it (entry exit 0 != 1, '
                'empty stdout); both passed in full1 on the same production bytes'),
     'log_sha256': {
         'controls': 'd02aa09b6be69294658828e869260c7538b016f4d9a9bd2144c7bd468947d7a7',
         'rerun_sm8': ['07e93dd58cc2e4fceb3cc2b18684627d217639bfe0a61ad6dfab433c457eeced',
                       '4fc307e0bc491d1a2f082e7e3006218436fd7cbac2d2ccc911afc680d3f2796d',
                       '69bb881a30d25b1eb2a4a3a985c8255e7eae2fd87019a44f14a672b2ae0ebaa0'],
         'rerun_e2': ['ce1e77d09630d5877cc944c91d797fab6483df542eec2da1d47e69d8697f0247',
                      '7e97b3515a6998571b96f1221032fb0ce6984bc085a2d6ce12da7fc3b724e710'],
         'runs_txt': '7d6dca38e13066ddc5cb85ab6dbb3a7ac0e33dbbc96e89cf88a8c28c71840748'},
     'disposition': ('NOT repaired and NOT diagnosed: solo reruns SM8AtTheRestart 3 of 3 OK and '
                     'ProdCaseBExternalReceipt 2 of 2 OK; e2 is the real host gate refusing on '
                     'a busy host (a named detector); the SM8 exit 0 is unexplained and stays '
                     'an open intermittent failure of that control')},
    {'kind': 'review_finding',
     'when': 'root 19:05 (reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md, main '
             '75c10af) on 03fe0ca at 159e747',
     'suite': 'source review (not a test run)',
     'result': ('blocking: build_live_ab_results.decision_object set primary_result '
                'LIVE_DECISION_INVALID but reportable=True for a decision after a non-cap '
                'no-decision point, and program_summary.json published the logged '
                'deploy_candidate with reportable true'),
     'log_sha256': None,
     'fix_commits': ['9f0aff6'],
     'disposition': ('fixed in 9f0aff6: one precedence, invalid first; reportable only for a '
                     'valid logged decision; the summary decision is always primary_result; '
                     'controls tests_invalid_decision_summary (7) over the complete results '
                     'path; root 22:08 (main 76f5e71): "the 19:05 leak is repaired in the '
                     'committed source path"')},
    {'kind': 'red_run',
     'when': '2026-09-24 16:22-16:27 local (20:22-20:27 UTC), the root 19:05 step before '
             '9f0aff6 (the probe and before1, pre-fix reproductions meant to fail)',
     'suite': 'scratch probe; live_ab_controls tests_invalid_decision_summary on the unfixed '
              'builder',
     'result': ('probe: refused_988baf7 and identity_988baf7 summaries decision deploy_'
                'candidate, reportable True (root\'s finding reproduced); before1 Ran 7, FAILED '
                '(failures=6)'),
     'log_sha256': {
         'probe_script': 'ede64b8ad33e856b91e29cb1acbba8bbfd8e07c3685826a3447149c0c89f2b77',
         'before1': '03f69bdd6d762085dbafa85ede1d7134416dc29343c9f1d4613819c115cecac4'},
     'disposition': 'expected; fix1 7 OK, run2 live_ab_controls 426 OK'},
    {'kind': 'red_run',
     'when': '2026-09-24 21:30-22:16 UTC, the amendment-v3 step before 56df17f',
     'suite': 'repair_amendment_v3 probes; live_ab_tools tests_repair_amendment_v3; the '
              'mutation sweeps',
     'result': ('probe1 FAILED inserted_text_form (four prose lines over 120 characters); '
                'probe2 FAILED (one line 135 characters); dev1 Ran 36, FAILED (errors=1: a '
                'path bug in VerifierTests.setUpClass); mutation1 14 of 15 killed, V4 (the '
                'verifier ignoring the demoted entry\'s commit) SURVIVED, M7 killed only by a '
                'crash; mutation2 NOT VALID EVIDENCE (the new witness failed on the original, '
                '41 ran, failures=1); dev3 Ran 1, FAILED (13 != 12 sub-checks)'),
     'log_sha256': {'probe1': '0edd595acebac201d0a1bf8093067c9677ed2dd05e5d888fb3294435672387c8',
                    'probe2': '0c353b7676d06dae67b55b7fc7e802c4b6815c551d373ec52fa969a3b5d9b982',
                    'dev1': '7168ac2ea48ecc1460f8fb62223db3b3999a24bd342d723f0eaa812e0e3ea53b',
                    'mutation1': '102f8d5fc161e9becee850aa313fff228205b9f9c0e43836ba64da3ee33738cd',
                    'mutation2': '438b5ed7a604fe8cb21dae08cfcd64a2a744866f5632cb9db9364688fc43e49f',
                    'dev3': '2a46ccea288cc0c0c213b8f2714ee0e2a166a66c6e1c0e698268131dc373791a',
                    'summary': '07185b7ee72056a9a907fbb5a3505d2e011ef666164190591402aa0f611aa52e'},
     'disposition': ('repaired inside 56df17f: prose rewrapped (probe3 ok), path fixed (dev2 '
                     '40 OK), witness added for V4 and M7 rewritten, sub-check listed; '
                     'mutation3 15 of 15 killed, original 41 ran 0 failures; the receipt '
                     'REPAIR_AMENDMENT_V3_RECEIPT_20260924_2218 lists every one of these runs')},
    # -- omitted from the 0027 receipt (final verification of 8f0b4ae, finding 8) -------------
    {'kind': 'review_finding',
     'when': 'root 02:54 (reviews/eb1_receipt_attribution_review_20260924_0254.md, main f855e45) '
             'on 8df2558',
     'suite': 'source review (not a test run)',
     'result': ('blocking: World.ingest_receipts attributed a receipt row whose request_id it '
                'did not know to the newest anchor, so an unmatched success-valued row could '
                'clear the decision gate (traffic_switch, post-decision dispatch)'),
     'log_sha256': None,
     'fix_commits': ['e9bfb18'],
     'disposition': ('fixed in e9bfb18: judge_receipt_line on every raw spool line, '
                     'anchor_receipt_rejected for an unknown, stale, malformed, duplicate or '
                     'conflicting row, no newest-anchor fallback, a decision receipt bound to '
                     'its exact request with its external evidence (tests_eb1_receipt_'
                     'attribution); root 07:03 (main ccdda96): it "closes the particular source '
                     'path"')},
    {'kind': 'red_run',
     'when': '2026-09-24 11:41 (as the 988baf7 commit message gives it), the first complete '
             'pin run of 988baf7',
     'suite': 'the five suites and the host sampler of harness_pin_successor',
     'result': ('the same green counts as the committed 1217 run, but its receipt (sha256 '
                'f1a136fe...) was discarded, never committed: its sampler counted the orphan '
                'the C10 control makes on purpose (its llama-server.py) as a foreign process'),
     'log_sha256': None,
     'disposition': ('the sampler attribution of that orphan was added and tested inside '
                     '988baf7; the 1217 receipt is the re-run (solo True, solo_strict False)')},
    {'kind': 'red_run',
     'when': '2026-09-24, the witness mutation sweep of 988baf7 (scratch clone, restored)',
     'suite': 'live_ab_tools tests_harness_pin_successor',
     'result': ('20 mutants, 19 killed, 1 SURVIVED: the diff argv without its explicit a/ b/ '
                'prefixes'),
     'log_sha256': None,
     'disposition': ('judged equivalent in 988baf7 (git already uses a/ b/ under the forced '
                     'configuration of DIFF_ARGV); no witness added')},
    {'kind': 'red_run',
     'when': 'root 22:08 (reviews/eb1_eb5_summary_repair_interim_20260924_2208.md, main '
             "76f5e71), root's reproduction attempt at 9f0aff6",
     'suite': ('live_ab_controls tests_invalid_decision_summary (the seven controls) in a 31 MiB '
               'sparse worktree, local Python 3.14'),
     'result': ('did not reach its assertions: setUpClass expected a crossing, but the mock tree '
                'aborted before its first trial event (program preflight harness_file_sha / '
                'preflight_rule_failed, reused_file_sha256 and sandbox_profile_sha256 drift: '
                'the sparse checkout omitted runtime material)'),
     'log_sha256': None,
     'disposition': ('root\'s own attempt, not a run of the full checkout; the 0027 receipt '
                     'quoted 22:08 only for its source finding.  Explained and reproduced by '
                     'f54d215 (runs R01, R02 below: a fresh sparse clone of 9f0aff6 without the '
                     'five tracked files of experiments/local_stream/, so the mock bundle '
                     'pinned {} and the literal sandbox profile; the same seven controls 7 OK '
                     'once that directory is present, and in full clones); root 10:10 (main '
                     '161966e): "source-consistent and independently checked at the '
                     'committed-byte level", without reproducing R01-R25')},
    # -- the final adversarial verification of 8f0b4ae and the step answering it ---------------
    {'kind': 'red_run',
     'when': '2026-09-25 (UTC, finished before 05:18), the final adversarial verification of '
             '8f0b4ae, in clones of 8f0b4ae (the worktree unmodified)',
     'suite': 'mutation runs over live_ab_controls, then live_ab, live_ab_tools, live_ab_serving',
     'result': ('reconciled from its logs (MUTATION_PARTITION_8F0B4AE; root 07:10), mutually '
                'exclusive: 109 mutant entries specified over the rulings 2114, 0153, 0254, '
                '0324, 0703, 1605, 1905, 108 run (E6c never run); 98 recorded KILLED = 96 by '
                'the right control (S6 counted after its solo rerun S6r, which '
                'SM8AtTheRestart killed with "2 != 1") + 2 recorded only because the real '
                'host gate refused the run (E3, whose solo rerun E3r SURVIVED; R8g, an '
                'equivalent mutant); 10 SURVIVED = 1 equivalent (S10) + 9 non-equivalent '
                'entries (W6, W6s, E3r, E17, E6, E12, E18, R6f, C8) over 7 distinct guards '
                '(W6/W6s and E3r/E17 share guards); equivalent mutants in total 2 (S10, R8g).  '
                'With the seven guards mutated at once: controls 426 OK, live_ab 766 OK '
                '(skipped=1), tools 186 OK (skipped=1), serving 193 OK.  Its first combined '
                'live_ab run FAILED (Ran 678, errors=28: tests_lab_design and the import of '
                'tests_lab_serving) in a clone without the untracked work/local_stream data; '
                '766 OK once that data was copied in'),
     'headline_as_first_reported': (
         'the owner\'s 05:18 UTC issue-11 comment: "105 mutants, 98 killed ... 98 were killed '
         'by the right control ... 2 survivors are equivalent ... 7 survivors are not '
         'equivalent" (105 total, 98 killed, 7 non-equivalent, 2 equivalent), and this row as '
         'first written at c001354 ("105 '
         'mutants ... 98 killed by the right control; 3 killed only by the real host gate ... '
         '7 non-equivalent SURVIVED"): DOUBLE-COUNTED.  98 + 7 + 2 = 107, not 105; E3 and R8g '
         'are inside the 98 killed and again inside the 7 guards and the 2 equivalents; 105 '
         'was the specification before the reruns E3r, S6r, W6s, E6c; the 98 included the '
         'rerun S6r and counted E3 and R8g, which only the host gate killed; "7" counted '
         'guards, not the 9 surviving non-equivalent entries.  Corrected by the owner at 07:27 '
         'UTC; no mutant was re-run for this accounting'),
     'log_sha256': {
         'mut_run1': 'd924b5db5ae7d8f2d3d8b91e7600df0a667fa90268c82074488ac6707ac1f4b0',
         'mut_run2': '43657be94d729c38a0479ced4f3ae733eedee400b75b15c642e32019df418a49',
         'mut_run3': '41f870cbb519af5144e5debd990724d0bca9de132431781732a3510575b623ad',
         'mutant_specs': '05e86a155dfc68609137ed9537be2fd708e86ca5da3cdf4e61cca88168b9b09a',
         'combined_summary': '4ba7c7694796915b38a2543ddd650f5473136296fddcf4990b06f73c81e727d8',
         'combined_live_ab_failed': ('e53476ef08f19dc4888fbebd7d675ad6e736119e748c965525c48247'
                                     '692c7940'),
         'combined_live_ab_ok': '9e918cce730f603f09bc6075af6a457f38941ab1990e61625692e13cd9bd79fb',
         'flaky_reruns': '3fb0dfa7f2856233ecbc0ff2cf8ef80e94a620c7cb687b051b1b703bae926522'},
     'disposition': ('the seven guards were correct and uncontrolled: tests_guard_controls '
                     '(2113dbd) gives each a control and its mutation; no production byte '
                     'changed.  Its finding 9 (a predecision non-cap abort with no crossing is '
                     'published none, reportable true, as protocol 16 item 17 prescribes; the '
                     'cap value is in no built output) went to root, who ruled (b) at 07:10 '
                     '(the review_finding row below, fixed by bdee21b and amendment v4 '
                     '90219f2); its finding 8 is the rows above')},
    {'kind': 'red_run',
     'when': '2026-09-25 05:29-05:52 UTC, the step answering that verification (2113dbd)',
     'suite': ('live_ab_controls tests_guard_controls against the verifier\'s source mutants in a '
               'clone (pre-fix negative controls, meant to fail)'),
     'result': ('kill matrix 1: 8 of 8 classes failed, 6 of them only at setUpClass (the in-test '
                'mutation refused before the unmutated control ran; restructured); kill matrix '
                '2: 8 of 8 killed, E3/E17 case B by a ValueError (made an assertion); kill 3 '
                '(E3, E17) by assertion; kill matrix 4 on the committed bytes: 8 of 8 killed, '
                'each positive control by its own assertion; then the witness of these rows '
                'before they were written: Ran 1, FAILED (failures=1, f1a136fe not found)'),
     'log_sha256': {
         'killmatrix1': '7a608b180d8b8623b60bf9086e87ecfcc9b7821be9f3cde199721aeb1b4f1e43',
         'killmatrix2': 'e055d90d0a1d5dfdc60d25f1276439be94869860f4079553849ff270a358ea0e',
         'kill3_E3': '5c4e7ddf85c98f43cd13adb79cc9f2a7d92fffa6a53faa20bfa76c36401efa16',
         'kill3_E17': 'edd9bb1caf602a341b78f3d346b5984b3378b213c2fe72d43a866cdea6e9bbcb',
         'killmatrix4': '03453bb6b7374174528ca368e817441ee9427b6fba6bdeaf0a983512cd45b015',
         'full_controls': '4339180030c460a68e24669a67b291ba5a8918333497a37d0587d980739d6bf7',
         'history_witness_before': ('a50d8c324b819c45ae6c977f0d54f8f4e55dced60f337f5a7dc0a3fb'
                                    '3f23709d')},
     'disposition': ('expected; on 8f0b4ae plus the module: dev1-dev3 16 OK, dev4 (with '
                     'tests_delta_citations) 23 OK; full live_ab_controls at 2113dbd '
                     '05:53-06:46 UTC: Ran 442 tests in 3184.690s, OK')},
    # -- after 2113dbd: root 07:10, the reproduction step, the v4 code and amendment steps ------
    {'kind': 'review_finding',
     'when': 'root 07:10 UTC (reviews/predecision_abort_reporting_ruling_20260925_0710.md, main '
             '9790043) on 2113dbd and c001354: finding 9 of the final verification of 8f0b4ae',
     'suite': 'source review (not a test run)',
     'result': ('choice (b): build_live_ab_results.decision_object published primary_result '
                "'none', reportable=True for a trial aborted before any decision by a non-cap "
                'cause with no crossing (amendment-v3 protocol 16 item 17 permitted it): a '
                'pre-outcome reporting-rule defect; such a trial is incomplete and not '
                'reportable, and the effective restart cap and its config binding were in no '
                'result/provenance output'),
     'log_sha256': None,
     'fix_commits': ['bdee21b', '90219f2'],
     'disposition': ('bdee21b: decision_object precedence (invalid first; the cap label; a '
                     'crossing not acted on; NEW the predecision-abort label and the '
                     'incomplete-chain label; reportable none only at a normal end at the '
                     'frozen full horizon), normal_end with 13 closed reasons, restart_cap '
                     'cap_value and binding in decision.json and program_summary.json; controls '
                     'tests_predecision_abort_reporting (16).  90219f2: amendment v4 (protocol '
                     '16 item 18, ARCHITECTURE 3.15), receipt REPAIR_AMENDMENT_V4_RECEIPT_'
                     '20260925_1120.json (0b4e4108...)')},
    {'kind': 'review_finding',
     'when': 'root 07:10 UTC (the same ruling): the owner\'s 05:18 mutation headline',
     'suite': 'arithmetic of a reported summary (not a test run)',
     'result': ('"it says 105 mutants, 98 killed, seven non-equivalent survivors and two '
                'equivalent survivors, which as written double-counts two unless they belong '
                'within another category.  Reconcile from existing logs; no repeat merely for '
                'this accounting"'),
     'log_sha256': None,
     'fix_commits': [],
     'disposition': ('reconciled from the verifier\'s logs by this receipt\'s step '
                     '(MUTATION_PARTITION_8F0B4AE, checked exclusive and exhaustive by '
                     'partition_problems; the reconciliation run is in the runs of this step): '
                     '109 specified, 108 run, 98 killed = 96 + 2 host-gate-only, 10 survived = '
                     '1 + 9 over 7 guards, 2 equivalent; the headline double-counted E3 and '
                     'R8g; the owner corrected it at 07:27 UTC; no mutant re-run')},
    {'kind': 'red_run',
     'when': '2026-09-25 07:02-08:27 UTC, the reproduction step (f54d215), fresh clones of '
             '9f0aff6 and c001354 outside the owner checkout',
     'suite': ('the summary controls, live_ab, tests_lab_design, live_ab_controls, the host gate, '
               'the pin recompute, the C test double, repro_inputs'),
     'result': ('R01 sparse clone 9f0aff6, summary module: setUpClass StopIteration, Ran 0, '
                'FAILED (errors=1); R02 its program chain: preflight_refused [harness_file_sha, '
                'preflight_rule_failed], drift reused_file_sha256 + sandbox_profile_sha256; '
                'R08b host gate probe during R15: refused on R15\'s own mock llama-server; R09 '
                'live_ab with no work/: Ran 678 in 207.034s, FAILED (errors=28, skipped=1); '
                'R12 tests_lab_design with mbpp.jsonl unreachable: Ran 345, FAILED '
                '(failures=14, errors=2, skipped=1); R15 live_ab_controls in the clone: Ran 442 '
                'in 3146.396s, FAILED (failures=5: C10, C1, C2b, C4, C4b of tests_eb1_entry, '
                'each host_not_quiescent, offending detector baseline-active, mediaanalysisd '
                'busy).  Meant to fail: R17 the pin recompute against the 1732 receipt, '
                'SOMETHING DIFFERS, exit 1; R20 sm_fixture.compiled() without clang, '
                'FileNotFoundError; R22 kill matrix of repro_inputs, 11 of 11 killed; R23a '
                'sparse clone + the three new control files: ERROR setUpModule '
                '(MissingReproductionInputs, 6 inputs named), Ran 0; R23b the CLI on a sparse '
                'and a shallow clone: exit 1 (9 named, 4 commits)'),
     'log_sha256': {
         'R01': '797506ef4d74b60c8ce9830707d48d39a6615b8552d0c53b0477643cfb452762',
         'R02': '26c5e1e481e37cfc9135dd18832aed4a7b1eb8d43dad71c86c45334599d81d92',
         'R08b': 'f9c67c9a5fbc5f5280bcef717cecda0abe81cac8f6678a49a08ec62a4f7beebf',
         'R09': '3a0f80724895aa8b11bf8ec7f7761f19d794d571848375cea5ae91ddc94482f7',
         'R12': '87e514c3a4b5dc1920cfbd06c22818a66f8577ffe7b63f5b18b42e3240838a53',
         'R15': 'b9eef8cda325f30535ba9dadeb1f1d5819709bf782f9f7f41fdcb0ee13189c5d',
         'R17': '1704a76e345f57665b78282f462a859f8eef823b3d5f2fc3c7176cb6884cff6c',
         'R20': '1bda59ad0504ce991ee0a03c214d832d3fdbd3275f4c49495a28fc784d1e9c86',
         'R22': 'e8cdc7bdb7032ce32ea4d147756f8d1daf9e6b303e074f507f8771c4b7b472b5',
         'R23a': '652b855012d0f05d4eea9f5ff514a1828bc9ee8da28dcb87ab684e5a91287da3',
         'R23b': '9c1f72aaf668756ec72df848bb2b7a1e7b4bcf9dd001510d6598baea4086bc8c'},
     'disposition': ('environment-only, none a defect of the subset\'s code: R01/R02 reproduce '
                     'root\'s 22:08 refusal (experiments/local_stream/ absent); R09/R12 lack '
                     'the untracked inputs; R15 is the real host gate refusing on a busy host '
                     '(R18 re-ran tests_eb1_entry alone: Ran 32 in 386.373s, OK).  R01-R23b, '
                     'green and red, are listed with their logs in experiments/live_ab_controls/'
                     'REPRODUCE_EB1_EB5_SUBSET.md section 11, R24/R25 (all OK, live_ab_controls '
                     '458) in the f54d215 commit message; repro_inputs.py names each missing '
                     'input')},
    {'kind': 'red_run',
     'when': '2026-09-25 ~09:46-11:18 UTC, the root 07:10 code step before bdee21b',
     'suite': ('live_ab_controls tests_predecision_abort_reporting, its kill matrix, the full '
               'suites (full1) and SM8AtTheRestart alone'),
     'result': ('before1, the new module on the unfixed builder (a pre-fix negative control, '
                'meant to fail): Ran 15 in 73.227s, FAILED (failures=13, errors=23); fix2 Ran '
                '16 in 76.058s, FAILED (failures=1: the horizon_unknown case kept '
                'monitor.n_max); kill matrix, 28 builder mutants in 4 clones (meant to fail): '
                '28 of 28 killed; full1 live_ab_controls Ran 474 in 3369.621s, FAILED '
                '(failures=2): tests_invalid_decision_summary SummaryPathControls.test_control_'
                'a_valid_eligible_decision_stays_reportable (its whole-row comparison met the '
                'three provenance keys 07:10 added) and tests_sm_entry.SM8AtTheRestart.'
                'test_sm8_a_library_changed_before_the_restart_refuses_it (entry exit 0 != '
                '1); three SM8 invocations from the worktree root were mistaken '
                '(ModuleNotFoundError tests_sm_entry, Ran 1, errors=1 each, no test ran; logs '
                'not kept); sm8_1 from experiments/live_ab_controls: Ran 2 in 52.142s, FAILED '
                '(failures=1, the same exit 0 != 1)'),
     'log_sha256': {
         'before1': '4c645afd260dbdb715f0d7bca0c5f97e46068f60cbfcc34c6c079aacb0758f2c',
         'fix2': 'abf5f7ef7c7660431e6740bb484cad15b54724473be13f0db540db10f7feccac',
         'killmatrix_c1': '83e89c3a588d8ecc4c06a3b228ba5c92654c45a8d1ee019baa70502e27d3dc1a',
         'killmatrix_c2': 'd6399e2e9a3ff77e629ba3406fd571d76aac40a76bb415a81cbdee10f3e6306b',
         'killmatrix_c3': '3de1859effe5bf7a446d9ba3e687de3997518468675aee351449ca7183f1ba15',
         'killmatrix_c4': 'bb4398a478dadeaf5e417a344cea5964e86741c5504465d7fb92f778d56e88ef',
         'full1_controls': 'f129eb1e533244059b2d2996ca69499b647c2cf9d2c2b59047536c40a0e60cf7',
         'sm8_1': '2e831cd488eaf752cffe7e5620a1ac3a67b2a354609b326b2013037aa361ebe8'},
     'disposition': ('fix3 16 OK; the summary control edited in place inside bdee21b (summ1 7 '
                     'OK); full1 live_ab 766 OK (skipped=1), serving 193 OK, tools 187 OK '
                     '(skipped=1), validation 211 OK; sm8_2 and sm8_3 Ran 2 OK: SM8 NOT '
                     'repaired, NOT diagnosed (the next row)')},
    {'kind': 'red_run',
     'when': '2026-09-25 ~10:04-12:24 UTC, the amendment-v4 step before 90219f2',
     'suite': ('live_ab_tools tests_repair_amendment_v4 and its mutation sweeps, the unedited '
               'v3 witness, the full suites (full2)'),
     'result': ('v4dev1 Ran 38, FAILED (failures=3, skipped=1): a recompiled mutant\'s '
                'getsource read the wrong lines, and the reason-list check filtered by '
                'membership; '
                'mutation1, 11 tool + 6 verifier mutants: 15 of 17 killed, T9 (the ASCII clause '
                'of the text form) and V6 (a verifier negative control replaced by False) '
                'SURVIVED; the UNEDITED v3 witness on the v4 documents: test_control_the_'
                'pristine_pre_images_are_amended FAILED (ARCH differs; why it was edited); the '
                'independent verifier\'s 6 negative controls failed as meant; full2 '
                'live_ab_controls Ran 474 in 3382.069s, FAILED (failures=1): tests_sm_entry.'
                'SM8AtTheRestart.test_sm8_a_library_changed_before_the_restart_refuses_it, '
                'entry exit 0 != 1 again'),
     'log_sha256': {
         'v4dev1': '90013193eb42ccc354ef7debb61b71f4288b5059598ddd2608f6efe219455049',
         'mutation1': '31687cb67db10356394f6de6ba14f076f789b1e55093850b8bd202faec9b10b0',
         'v3_witness_unedited': '28d7ed75a02951a83349fc0dc66cd565be2ce6a0ce4e209d3fbeeaac9e9f5562',
         'verifier_pre_commit': '0cd08ca65db089b3a44fb9d56768fdd82873f92e3d2328a3b8fd80e567250319',
         'full2_controls': 'a6886edeab1db6eb497388c215cc19130508a1b7490b4d7c3bcaa79af7215dd7'},
     'disposition': ('witnesses added (v4dev2/v4dev3 OK; mutation2 killed T9 and V6, '
                     '730ab966...); the v3 witness edited in place inside 90219f2; full2 '
                     'live_ab 766 OK (skipped=1), serving 193 OK, tools 227 OK (skipped=2), '
                     'validation 215 OK.  SM8AtTheRestart exit 0 != 1 stays an OPEN, '
                     'UNDIAGNOSED intermittent failure of that control: red in 7ebffad full2, '
                     'bdee21b full1, sm8_1 and 90219f2 full2; green in 3 of 3 solo reruns at '
                     '7ebffad and in sm8_2, sm8_3; the orchestrator subprocess it drives never '
                     'reaches the results builder')},
)

#: The mutation partition of the final adversarial verification of 8f0b4ae, reconciled from its
#: own logs (root 07:10: "a clarified mutually exclusive partition ... Reconcile from existing
#: logs; no repeat merely for this accounting").  Read from the verifier's mutant specification
#: (spec3.json) and its three result streams (one JSON row per mutant run: mut_run1.out,
#: mut_results2.jsonl, mut_run3.out), each named by the SHA-256 of the bytes read; a kill is
#: "host gate only" when the mutant's own log shows the REAL host gate refusing the run (the
#: control's host-gate assertion or host_not_quiescent) and no solo rerun of the same edit was
#: killed.  Every entry is listed by id so partition_problems can check that the classes are
#: mutually exclusive and exhaustive and that each stated count is the size of its class.
MUTATION_PARTITION_8F0B4AE = {
    'verification': ('the final adversarial verification of 8f0b4ae, clones of 8f0b4ae, finished '
                     'before 05:18 UTC 2026-09-25 (the red_run row of DISCLOSED_RED_RUNS)'),
    'logs': {'spec3.json': '05e86a155dfc68609137ed9537be2fd708e86ca5da3cdf4e61cca88168b9b09a',
             'mut_run1.out': 'd924b5db5ae7d8f2d3d8b91e7600df0a667fa90268c82074488ac6707ac1f4b0',
             'mut_results2.jsonl': ('43657be94d729c38a0479ced4f3ae733eedee400b75b15c642e32019'
                                    'df418a49'),
             'mut_run3.out': '41f870cbb519af5144e5debd990724d0bca9de132431781732a3510575b623ad'},
    'specified': (
        'E1 E2 E3 E4 E5 E5b E6 E7a E7b E7c E7d E7e E7f E7g E7h E7i E7j E7k E8 E9 E10 E11 E12 E13 '
        'E15 E16 E17 E18 B1 B2 B3 B4 B5 B6 B7 B9 B10 B11 B12 R1 R2 R3 R4 R5 R6a R6b R6c R6d R6e '
        'R6f R6g R6h R6i R6j R6k R6l R7a R7b R7c R8a R8b R8c R8d R8e R8f R8g R8h R8i R10 R11 C1 '
        'C2 C3 C4 C5 C6 C7 C8 C9 S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 W1 W2 W4 W5 W6 W7 M1 M2 '
        'M4 M5 M6 M7 M8 F1 E3r S6r W6s E6c').split(),
    'not_run': {'E6c': 'a rerun of E6 (close_with_open_work removed) that was specified and never '
                       'run'},
    'killed_by_the_right_control': (
        'E1 E2 E4 E5 E5b E7a E7b E7c E7d E7e E7f E7g E7h E7i E7j E7k E8 E9 E10 E11 E13 E15 E16 '
        'B1 B2 B3 B4 B5 B6 B7 B9 B10 B11 B12 R1 R2 R3 R4 R5 R6a R6b R6c R6d R6e R6g R6h R6i R6j '
        'R6k R6l R7a R7b R7c R8a R8b R8c R8d R8e R8f R8h R8i R10 R11 C1 C2 C3 C4 C5 C6 C7 C9 S1 '
        'S2 S3 S4 S5 S6 S7 S8 S9 S11 S12 W1 W2 W4 W5 W7 M1 M2 M4 M5 M6 M7 M8 F1 S6r').split(),
    'counted_after_a_solo_rerun': {
        'S6': ('its run was refused by the real host gate (mut2_S6.log: host_not_quiescent, '
               'baseline-active); the same edit rerun alone, S6r, was killed by tests_sm_entry.'
               'SM8AtTheRestart with "2 != 1" (not the intermittent "0 != 1")')},
    'killed_only_by_the_host_gate': {
        'E3': {'log': 'mut_E3.log',
               'log_sha256': '5bc17ecbdec807db596294ca547ac30f9a9f25edb5f76eebc3929d35cdd67f77',
               'line': "AssertionError: True is not false : host gate",
               'solo_rerun': 'E3r', 'solo_rerun_verdict': 'SURVIVED'},
        'R8g': {'log': 'mut2_R8g.log',
                'log_sha256': '529db8cae575331bb2ed48affb8ae1af132e28ba958483976d1e171693888c5b',
                'line': "AssertionError: True is not false : host gate",
                'solo_rerun': None, 'solo_rerun_verdict': None}},
    'survived_equivalent': ['S10'],
    'survived_non_equivalent': {
        'W6': 'unresolved_seen stops follow-up dispatch',
        'W6s': 'unresolved_seen stops follow-up dispatch',
        'E3r': 'look_guard', 'E17': 'look_guard',
        'E6': 'close_with_open_work', 'E12': 'abort_point_missing ordering',
        'E18': 'abort_owed once per reason', 'R6f': 'decision receipt on the frozen branch',
        'C8': 'nothing restarts during an owed-abort drain'},
    'equivalent': {
        'S10': 'launcher digest ignored: redundant with the closure check (survived)',
        'R8g': ('anchor_mismatch removed: can never differ at its only caller (recorded killed '
                'only by the host gate)')},
    'guards_controlled_by_2113dbd': {
        'unresolved_seen stops follow-up dispatch': 'UnresolvedFollowUpInProcess',
        'look_guard': 'LookGuardInProcess',
        'close_with_open_work': 'CloseWithOpenWorkInProcess',
        'abort_point_missing ordering': 'LateAbortPointTests',
        'abort_owed once per reason': 'TwoOwedReasonsInProcess',
        'decision receipt on the frozen branch': 'FrozenBranchTests',
        'nothing restarts during an owed-abort drain': 'NoRestartDuringOwedAbortInProcess'},
    'counts': {'specified': 109, 'run': 108, 'not_run': 1, 'killed': 98,
               'killed_by_the_right_control': 96, 'killed_only_by_the_host_gate': 2,
               'survived': 10, 'survived_equivalent': 1, 'survived_non_equivalent': 9,
               'distinct_non_equivalent_guards': 7, 'equivalent': 2},
    'headline_0518': {'total': 105, 'killed': 98, 'non_equivalent': 7, 'equivalent': 2,
                      'reading': ('the owner\'s 05:18 headline double-counted: 98 + 7 + 2 = '
                                  '107 != 105 (see the verification row)')},
}


#: The unified-diff form whose bytes are hashed (every option fixed; see git_env()).
DIFF_ARGV = ('-c', 'core.quotePath=true', '-c', 'diff.noprefix=false',
             '-c', 'diff.mnemonicPrefix=false', '-c', 'diff.suppressBlankEmpty=false',
             'diff', '--no-color', '--no-ext-diff', '--no-textconv', '--full-index',
             '--no-renames', '--no-relative', '--diff-algorithm=myers', '--indent-heuristic',
             '--inter-hunk-context=0', '--src-prefix=a/', '--dst-prefix=b/', '--unified=3',
             '--binary')

SUITES = (
    ('live_ab', ['-m', 'unittest', 'discover', '-v', '-s', 'experiments/live_ab',
                 '-p', 'tests_*.py']),
    ('live_ab_controls', ['-m', 'unittest', 'discover', '-v', '-s',
                          'experiments/live_ab_controls', '-p', 'tests_*.py']),
    ('live_ab_serving', ['-m', 'unittest', 'discover', '-v', '-s',
                         'experiments/live_ab_serving', '-p', 'tests_*.py']),
    ('live_ab_tools', ['-m', 'unittest', 'discover', '-v', '-s', 'experiments/live_ab_tools',
                       '-p', 'tests_*.py']),
    ('live_ab_validation', ['experiments/live_ab_validation/tests_validation.py']),
)
SUITE_TIMEOUT_S = 3 * 3600
SAMPLE_EVERY_S = 2.0
#: Where each suite's full stdout/stderr ends up retained, write-once, next to the receipt: one
#: directory per receipt (``<out-dir>/pin_logs/<receipt stamp>/<suite>.std{out,err}.gz``), only
#: once the run has turned out clean (``pin_log_staging_root``/``promote_pin_log``: during the
#: run itself the logs sit under a temporary staging root outside ``--repo``, never in the
#: tree).  A red run must be diagnosable from what is kept here, never from a rerun for a
#: favourable count.
PIN_LOGS_DIRNAME = 'pin_logs'
WATCH = ('unittest', 'tests_', 'llama-server', 'llama_server', 'lab_orchestrator',
         'lab_mock_server', 'run_smoke', 'run_live_ab', 'ninja', 'cmake', 'mlx_lm', 'ollama',
         'vllm')

HEX64 = re.compile(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])')


class Refused(Exception):
    """The tool refuses; ``problems`` names every reason.  No receipt is written; a receipt
    already assembled (``draft``) is saved by main() under the temporary directory only, for
    diagnosis, never under results/."""

    def __init__(self, problems: Iterable[str], draft: dict | None = None) -> None:
        self.problems = sorted(set(problems))
        self.draft = draft
        super().__init__('refused: ' + ', '.join(self.problems))


# --------------------------------------------------------------------------- #
# hashing, canonical JSON, git
# --------------------------------------------------------------------------- #
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: object) -> str:
    """``lab_common.canonical_json`` (checked equal in LabCommonAgreementTests)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def sha256_canonical(obj: object) -> str:
    return sha256(canonical_json(obj).encode('utf-8'))


def git_env() -> dict:
    """The environment of every git call: no GIT_* variable of the caller (no injected
    ``GIT_CONFIG_*``, and no ``GIT_DIFF_OPTS``, which OVERRIDES ``--unified`` on the command
    line), no global or system configuration or attributes, C locale."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               LC_ALL='C', GIT_PAGER='cat')
    return env


def git(repo: Path, *args: str, check: bool = True, stdin: bytes | None = None) -> bytes:
    res = subprocess.run(['git', '-C', str(repo), *args], input=stdin, capture_output=True,
                         env=git_env(), timeout=600, check=False)
    if check and res.returncode != 0:
        raise Refused(['git_failed:%s' % ' '.join(args[:3])])
    return res.stdout


def resolve(repo: Path, rev: str) -> str | None:
    res = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet',
                          rev + '^{commit}'], capture_output=True, env=git_env(), timeout=60,
                         check=False)
    out = res.stdout.decode().strip()
    return out if res.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', out) else None


class GitTree:
    """Read-only view of one commit: top-level listing of a directory and blob bytes."""

    def __init__(self, repo: Path, rev: str) -> None:
        self.repo = Path(repo)
        sha = resolve(self.repo, rev)
        if sha is None:
            raise Refused(['revision_missing:%s' % rev])
        self.rev = sha

    def entries(self, directory: str) -> list:
        """``(mode, type, name)`` of the direct children of ``directory``."""
        out = git(self.repo, 'ls-tree', '-z', '--full-tree', self.rev, '--',
                  directory.rstrip('/') + '/')
        rows = []
        for rec in out.split(b'\0'):
            if not rec:
                continue
            meta, path = rec.split(b'\t', 1)
            mode, typ, _oid = meta.decode().split(' ')
            rows.append((mode, typ, path.decode('utf-8').rsplit('/', 1)[-1]))
        return rows

    def read(self, path: str) -> bytes | None:
        res = subprocess.run(['git', '-C', str(self.repo), 'cat-file', 'blob',
                              '%s:%s' % (self.rev, path)], capture_output=True, env=git_env(),
                             timeout=120, check=False)
        return res.stdout if res.returncode == 0 else None


def harness_names_from_git(tree: GitTree) -> tuple[list, list]:
    """(names, problems): ``lab_common._harness_files`` on a commit -- the top-level ``*.py``
    blobs of experiments/live_ab plus ``config.json`` when present, sorted."""
    names, problems = [], []
    for mode, typ, name in tree.entries(LIVE_REL):
        if typ == 'blob' and (name.endswith('.py') or name == 'config.json'):
            if mode == '120000':
                problems.append('symlink_in_harness:%s' % name)
            names.append(name)
    return sorted(names), problems


def harness_map(tree: GitTree) -> dict:
    names, problems = harness_names_from_git(tree)
    if problems:
        raise Refused(problems)
    out = {}
    for name in names:
        data = tree.read('%s/%s' % (LIVE_REL, name))
        if data is None:
            raise Refused(['unreadable_blob:%s' % name])
        out[name] = sha256(data)
    return out


def harness_map_from_dir(directory: Path) -> dict:
    """Exactly ``lab_common._harness_files`` + ``harness_file_hashes`` on a directory."""
    names = sorted(p.name for p in Path(directory).glob('*.py'))
    if (Path(directory) / 'config.json').exists():
        names.append('config.json')
    return {n: sha256((Path(directory) / n).read_bytes()) for n in sorted(names)}


def predecessor_problems(pmap: Mapping) -> list:
    """Why a map is not the reviewed b049307 harness pin ([] when it is)."""
    problems = []
    if len(pmap) != PREDECESSOR_COUNT:
        problems.append('predecessor_count:%d' % len(pmap))
    if sha256_canonical(dict(pmap)) != PREDECESSOR_CANONICAL:
        problems.append('predecessor_digest')
    return problems


def unified_diff(repo: Path, old: str, new: str, path: str) -> bytes:
    return git(repo, *DIFF_ARGV, old, new, '--', path)


def diff_reproduces(old: bytes | None, new: bytes | None, diff: bytes, path: str) -> bool:
    """``git apply`` of ``diff`` (outside any repository) to ``old`` at ``path`` gives
    exactly ``new`` (for a deleted file: nothing)."""
    tmp = Path(tempfile.mkdtemp(prefix='pinsucc_apply_'))
    try:
        work = tmp / 'w'
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if old is not None:
            target.write_bytes(old)
        (tmp / 'd.patch').write_bytes(diff)
        env = git_env()
        env['GIT_CEILING_DIRECTORIES'] = str(tmp)
        res = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-p1',
                              str(tmp / 'd.patch')], cwd=str(work), capture_output=True,
                             env=env, timeout=120, check=False)
        if res.returncode != 0:
            return False
        if new is None:
            return not target.exists()
        return target.is_file() and target.read_bytes() == new
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def diff_entry(repo: Path, old_tree: GitTree, new_tree: GitTree, path: str) -> dict:
    old, new = old_tree.read(path), new_tree.read(path)
    diff = unified_diff(repo, old_tree.rev, new_tree.rev, path)
    text = diff.decode('utf-8', 'replace').splitlines()
    commits = git(repo, 'log', '--format=%H', '%s..%s' % (old_tree.rev, new_tree.rev), '--',
                  path).decode().split()
    return {
        'status': 'added' if old is None else ('deleted' if new is None else 'modified'),
        'old_sha256': None if old is None else sha256(old),
        'new_sha256': None if new is None else sha256(new),
        'old_bytes': None if old is None else len(old),
        'new_bytes': None if new is None else len(new),
        'diff_sha256': sha256(diff),
        'diff_bytes': len(diff),
        'lines_added': sum(1 for ln in text if ln.startswith('+') and not ln.startswith('+++')),
        'lines_removed': sum(1 for ln in text if ln.startswith('-')
                             and not ln.startswith('---')),
        'diff_applied_to_old_gives_new': diff_reproduces(old, new, diff, path),
        'changing_commits': list(reversed(commits)),
    }


def blob_digests(repo: Path, rev: str, prefixes: Iterable[str]) -> dict:
    """path -> sha256 of every blob under ``prefixes`` at ``rev`` (one cat-file batch)."""
    out = git(repo, 'ls-tree', '-r', '-z', '--full-tree', rev, '--', *prefixes)
    rows = []
    for rec in out.split(b'\0'):
        if rec:
            meta, path = rec.split(b'\t', 1)
            _mode, typ, oid = meta.decode().split(' ')
            if typ == 'blob':
                rows.append((path.decode('utf-8'), oid))
    oids = sorted({oid for _p, oid in rows})
    raw = git(repo, 'cat-file', '--batch', stdin=('\n'.join(oids) + '\n').encode())
    by_oid, i = {}, 0
    while i < len(raw):
        nl = raw.index(b'\n', i)
        oid, _typ, size = raw[i:nl].decode().split(' ')
        start = nl + 1
        by_oid[oid] = sha256(raw[start:start + int(size)])
        i = start + int(size) + 1
    return {p: by_oid[oid] for p, oid in rows}


# --------------------------------------------------------------------------- #
# configuration: rule block, tuples read from lab_common source
# --------------------------------------------------------------------------- #
def module_constant(source: bytes, name: str) -> object:
    """The literal value assigned to top-level ``name`` in ``source`` (ast, not import)."""
    for node in ast.parse(source).body:
        targets = ([node.target] if isinstance(node, ast.AnnAssign)
                   else node.targets if isinstance(node, ast.Assign) else [])
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise Refused(['constant_absent:%s' % name])


def rule_block_digest(config: Mapping, keys: Iterable[str]) -> str:
    """``lab_common.rule_block_sha256`` with the given RULE_BLOCK_KEYS."""
    block = {}
    for dotted in keys:
        node: object = config
        for part in dotted.split('.'):
            if not isinstance(node, Mapping) or part not in node:
                raise Refused(['rule_block_key_missing:%s' % dotted])
            node = node[part]
        block[dotted] = node
    return sha256_canonical(block)


LAB_COMMON_PROBE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import lab_common
cfg = json.loads(open(sys.argv[2], encoding='utf-8').read())
print(json.dumps({'harness': lab_common.harness_file_hashes(),
                  'harness_files': list(lab_common.HARNESS_FILES),
                  'reused_files': list(lab_common.REUSED_FILES),
                  'rule_block_keys': list(lab_common.RULE_BLOCK_KEYS),
                  'rule_block': lab_common.rule_block_sha256(cfg),
                  'canonical_of_map': lab_common.sha256_canonical(
                      lab_common.harness_file_hashes()),
                  'server_supervision_cap': lab_common.server_supervision_cap(cfg)}))
'''


def lab_common_view(repo: Path) -> dict:
    """What the working tree's own lab_common computes (a subprocess; nothing imported here)."""
    res = subprocess.run([PY, '-c', LAB_COMMON_PROBE, str(repo / LIVE_REL),
                          str(repo / CONFIG_REL)], capture_output=True, text=True, timeout=300,
                         cwd=str(repo), check=False)
    if res.returncode != 0:
        raise Refused(['lab_common_probe_failed'])
    return json.loads(res.stdout)


# --------------------------------------------------------------------------- #
# prior observations: which pins moved
# --------------------------------------------------------------------------- #
def pins_in(obj: object, path: str = '$') -> list:
    """``(json_path, hex)`` of every 64-hex value inside a string of ``obj``."""
    out = []
    if isinstance(obj, Mapping):
        for k in obj:
            out.extend(pins_in(obj[k], '%s.%s' % (path, k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(pins_in(v, '%s[%d]' % (path, i)))
    elif isinstance(obj, str):
        out.extend((path, h) for h in HEX64.findall(obj))
    return out


def classify_pins(obj: object, table: Mapping, manifest_hexes: frozenset = frozenset(),
                  tokenize: Callable[[str], str] = str,
                  config_hexes: frozenset = frozenset()) -> dict:
    """Classify every pin of a record against ``table`` (artifact -> {'b049307', 'head'}).

    A pin is attributed to the artifact whose repository path its JSON path names (longest
    match), else to every artifact whose b049307 digest it equals.  Attributed and equal to
    that artifact's b049307 digest: ``moved`` if the HEAD digest differs, else ``unchanged``.
    Named but not the b049307 digest: ``already_historical`` (stale before this successor).
    Otherwise ``successor_only`` (equals a HEAD digest only) or
    ``not_a_digest_at_either_revision`` (with whether the real serving manifest, or the HEAD
    config.json, carries it)."""
    pred: dict = {}
    succ: dict = {}
    for art, row in table.items():
        if row.get('b049307'):
            pred.setdefault(row['b049307'], []).append(art)
        if row.get('head'):
            succ.setdefault(row['head'], []).append(art)
    by_artifact: dict = {}
    historical, successor_only, untracked = [], [], []
    pins = pins_in(obj)
    for raw_jp, hx in pins:
        named = max((a for a in table if '/' in a and a in raw_jp), key=len, default=None)
        jp = tokenize(raw_jp)
        if named is not None and table[named].get('b049307') != hx:
            historical.append({'json_path': jp, 'value': hx, 'artifact': named,
                               'b049307': table[named].get('b049307'),
                               'head': table[named].get('head')})
            continue
        arts = [named] if named is not None else pred.get(hx, [])
        if arts:
            for art in arts:
                row = by_artifact.setdefault(art, {
                    'b049307': table[art].get('b049307'), 'head': table[art].get('head'),
                    'moved': table[art].get('b049307') != table[art].get('head'),
                    'json_paths': []})
                row['json_paths'].append(jp)
        elif hx in succ:
            successor_only.append({'json_path': jp, 'value': hx, 'artifacts': succ[hx]})
        else:
            untracked.append({'json_path': jp, 'value': hx,
                              'in_real_serving_manifest': hx in manifest_hexes,
                              'in_successor_config': hx in config_hexes})
    moved = sorted(a for a, r in by_artifact.items() if r['moved'])
    return {'pins_found': len(pins), 'by_artifact': by_artifact, 'moved_artifacts': moved,
            'unchanged_artifacts': sorted(a for a, r in by_artifact.items() if not r['moved']),
            'already_historical': historical, 'successor_only': successor_only,
            'not_a_digest_at_either_revision': untracked}


def record_verdict(c: Mapping) -> str:
    """One sentence from the classification (nothing else is consulted)."""
    parts = []
    if c['moved_artifacts']:
        parts.append('STALE: pins of %d artifact(s) moved between b049307 and HEAD (%s)'
                     % (len(c['moved_artifacts']), ', '.join(c['moved_artifacts'])))
    else:
        parts.append('no pin it carries is a b049307 digest that moved')
    if c['unchanged_artifacts']:
        parts.append('%d pinned artifact(s) unchanged' % len(c['unchanged_artifacts']))
    if c['already_historical']:
        parts.append('%d pin(s) already historical at b049307 (%s)' % (
            len(c['already_historical']),
            ', '.join(sorted({h['artifact'] for h in c['already_historical']}))))
    other = c['not_a_digest_at_either_revision']
    if other:
        bound = sum(1 for u in other if u['in_real_serving_manifest'])
        conf = sum(1 for u in other if u.get('in_successor_config'))
        parts.append('%d pin(s) are digests of no tracked file at either revision: %d carried '
                     'by the real serving manifest (the durable build), %d by the HEAD '
                     'config.json, %d by neither' % (len(other), bound, conf, sum(
                         1 for u in other if not u['in_real_serving_manifest']
                         and not u.get('in_successor_config'))))
    return '; '.join(parts) + '. Kept as written; not reissued by this successor.'


# --------------------------------------------------------------------------- #
# the compiled C test double (root 07:03 item 1)
# --------------------------------------------------------------------------- #
def fixture_sources(source: bytes) -> dict:
    """From sm_fixture.py (ast only): the C string constants, the file each is written to by
    ``compiled()``, their digests, the compile argv and the cache key formula's value."""
    tree = ast.parse(source)
    consts = {n: module_constant(source, n) for n in ('BASE_C', 'CORE_C', 'LAUNCHER_C')}
    written, argvs = {}, []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == 'compiled':
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'write_text' and node.args
                        and isinstance(node.args[0], ast.Name)
                        and isinstance(node.func.value, ast.BinOp)
                        and isinstance(node.func.value.right, ast.Constant)):
                    written[node.args[0].id] = node.func.value.right.value
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple) and \
                        node.iter.elts and all(isinstance(e, ast.List) for e in node.iter.elts):
                    argvs = [ast.literal_eval(e) for e in node.iter.elts]
    key = hashlib.sha256()
    for name in ('BASE_C', 'CORE_C', 'LAUNCHER_C'):
        key.update(consts[name].encode('utf-8'))
    return {
        'where': ('string constants BASE_C, CORE_C, LAUNCHER_C of the committed %s (no separate '
                  '.c file is tracked); compiled() writes each to the named file in its '
                  'compile directory, UTF-8, then deletes it' % FIXTURE_REL),
        'files': {written.get(n, '?'): {'constant': n, 'bytes': len(v.encode('utf-8')),
                                        'sha256': sha256(v.encode('utf-8'))}
                  for n, v in consts.items()},
        'compile_argv': argvs,
        'sources_key': key.hexdigest()[:16],
        'cache_dir_name': 'eb1c_sm_fixture_%s' % key.hexdigest()[:16],
    }


def run_text(argv: list, timeout: int = 60) -> tuple[int, str]:
    try:
        res = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                             check=False)
        return res.returncode, res.stdout + res.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, 'ERROR %s' % type(exc).__name__


def compiler_record() -> dict:
    rc, version = run_text(['clang', '--version'])
    _rc, xcrun = run_text(['xcrun', '--find', 'clang'])
    _rc, dev = run_text(['xcode-select', '-p'])
    which = shutil.which('clang')
    return {'invoked_as': 'clang (resolved through PATH by subprocess)',
            'which_clang': which, 'which_clang_realpath': which and os.path.realpath(which),
            'xcrun_find_clang': xcrun.strip(), 'xcode_select_p': dev.strip(),
            'clang_version_exit': rc, 'clang_version': version.rstrip('\n').splitlines()}


FIXTURE_PROBE = r'''
import hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import sm_fixture
mode = sys.argv[3]
out = {'tempdir': os.path.realpath(tempfile.gettempdir()), 'key': sm_fixture._sources_key()}
cache = Path(out['tempdir']) / ('eb1c_sm_fixture_' + out['key'])
out['cache_existed_before'] = cache.exists()
try:
    path = sm_fixture.compiled()
    if mode == 'partial':
        (path / 'libeb1c-core.0.dylib').unlink()
        root = Path(tempfile.mkdtemp(prefix='b_'))
        (root / 'state').mkdir()
        sm_fixture.Build(root / 'build', state=root / 'state')
    out['raised'] = None
except BaseException as exc:
    out['raised'] = type(exc).__name__
    out['message'] = str(exc)[:300]
out['cache_launcher_exists_after'] = (cache / 'llama-server').is_file()
out['moved_aside'] = sum(1 for p in Path(out['tempdir']).iterdir() if '.untrusted.' in p.name)
check = getattr(sm_fixture, 'cache_problems', None)
out['cache_verified_after'] = (None if check is None or not cache.is_dir()
                               else check(cache) == [])
out['files'] = {}
if cache.is_dir():
    for p in sorted(cache.iterdir()):
        out['files'][p.name] = ('symlink -> ' + os.readlink(p) if p.is_symlink()
                                else hashlib.sha256(p.read_bytes()).hexdigest())
print(json.dumps(out))
'''

CONTROL_PROBE = r'''
import io, json, os, sys, unittest
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import tests_sm_manifest
tests_sm_manifest.LABSBX = sys.argv[3]
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[5:])
stream = io.StringIO()
res = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
print(json.dumps({'ran': res.testsRun, 'failures': len(res.failures),
                  'errors': len(res.errors), 'skipped': len(res.skipped),
                  'successful': res.wasSuccessful(),
                  'error_types': sorted({e[1].strip().splitlines()[-1].split(':')[0]
                                         for e in res.errors}),
                  'cache_launcher_exists_after': os.path.isfile(os.path.join(
                      sys.argv[3], sys.argv[4], "llama-server"))}))
'''


def _probe(argv: list, env: dict, root: Path) -> dict:
    res = subprocess.run(argv, capture_output=True, text=True, timeout=600, env=env,
                         check=False)
    try:
        out = json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        out = {'unparsed_output': (res.stdout + res.stderr)[-400:]}
    out['exit'] = res.returncode
    for key in ('message', 'unparsed_output'):
        if key in out:
            out[key] = out[key].replace(str(root), '<CONTROL_ROOT>')
    return out


def judge_fixture_controls(out: dict) -> dict:
    """[pure] Set ``ok`` on each of the five probe results (FIXTURE_CONTROL_TAGS).  A
    missing cache must REBUILD (A, D) or FAIL VISIBLY (B, C, E): an exception, or every
    control test run and erroring/failing.  A skip, a partial run or a pass without a
    compiler is never ``ok``."""
    n = len(FIXTURE_CONTROL_TESTS)
    a, b, c = (out.setdefault(t, {}) for t in FIXTURE_CONTROL_TAGS[:3])
    d, e = (out.setdefault(t, {}) for t in FIXTURE_CONTROL_TAGS[3:])
    a['ok'] = (a.get('raised') is None and a.get('cache_existed_before') is False
               and a.get('cache_launcher_exists_after') is True
               and a.get('otool_L_links_core') is True)
    b['ok'] = (b.get('raised') is not None and b.get('cache_existed_before') is False
               and b.get('cache_launcher_exists_after') is False)
    # a partial cache fails visibly (an exception), or -- since the subset fix, whose
    # compiled() trusts a cache only when its compile-time manifest verifies -- is moved
    # aside and rebuilt, the rebuilt cache verifying; never accepted as it is
    c['ok'] = (c.get('raised') is not None
               or (c.get('raised') is None and c.get('cache_verified_after') is True
                   and int(c.get('moved_aside') or 0) >= 1))
    d['ok'] = (d.get('ran') == n and d.get('successful') is True and d.get('skipped') == 0
               and d.get('cache_launcher_exists_after') is True)
    e['ok'] = (e.get('ran') == n and e.get('successful') is False and e.get('skipped') == 0
               and e.get('errors', 0) + e.get('failures', 0) == n
               and e.get('cache_launcher_exists_after') is False)
    return out


def fixture_missing_cache_controls(repo: Path, cache_dir_name: str) -> dict:
    """Five controls, each under its own fresh temporary root (never the shared cache):

    A. no cache -> ``compiled()`` rebuilds it (launcher present after, links libeb1c-core);
    B. no cache and a ``clang`` that fails (a stub first on PATH) -> an exception, no cache;
    C. a partial cache (launcher present, core library missing) -> ``Build()`` raises, or
       (since the subset fix) the cache is moved aside as untrusted and rebuilt, and verifies;
    D. the real control tests FIXTURE_CONTROL_TESTS with their LABSBX pointed at an empty
       root -> both run and pass, and the cache exists afterwards (rebuilt by the control);
    E. D with the failing ``clang`` -> both run and ERROR (visible; none skipped, none pass)."""
    controls, live = str(repo / 'experiments/live_ab_controls'), str(repo / LIVE_REL)
    roots = []

    def fresh(tag: str) -> Path:
        r = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_%s_' % tag)))
        roots.append(r)
        return r

    stub = fresh('stub')
    (stub / 'clang').write_text('#!/bin/sh\necho "clang disabled by the missing-cache '
                                'control" >&2\nexit 1\n', encoding='utf-8')
    (stub / 'clang').chmod(0o755)
    base_env = {k: v for k, v in os.environ.items() if k != 'TMPDIR'}
    no_cc = dict(base_env, PATH=str(stub) + os.pathsep + base_env.get('PATH', ''))
    try:
        out = {}
        for tag, mode, env in (('A_rebuild', 'fresh', base_env),
                               ('B_no_compiler', 'fresh', no_cc),
                               ('C_partial_cache', 'partial', base_env)):
            root = fresh(tag)
            out[tag] = _probe([PY, '-c', FIXTURE_PROBE, controls, live, mode],
                              dict(env, TMPDIR=str(root)), root)
        a = out['A_rebuild']
        otool_rc, otool = (run_text(['otool', '-L', os.path.join(
            a.get('tempdir', ''), cache_dir_name, 'llama-server')])
            if a.get('cache_launcher_exists_after') else (-1, ''))
        a['otool_L_links_core'] = otool_rc == 0 and '@rpath/libeb1c-core.0.dylib' in otool
        for tag, env in (('D_real_control_rebuilds', base_env),
                         ('E_real_control_no_compiler', no_cc)):
            labsbx = fresh(tag) / 'labsbx'
            out[tag] = _probe([PY, '-c', CONTROL_PROBE, controls, live, str(labsbx),
                               cache_dir_name] + list(FIXTURE_CONTROL_TESTS), env,
                              labsbx.parent)
            out[tag]['tests'] = list(FIXTURE_CONTROL_TESTS)
        judge_fixture_controls(out)
        for row in out.values():
            row.pop('tempdir', None)
        c = out['C_partial_cache']
        common = sorted(set(a.get('files', {})) & set(c.get('files', {})))
        out['observation_outputs_reproducible'] = {
            'files_compared': common,
            'byte_identical_between_A_and_C': [f for f in common
                                               if a['files'][f] == c['files'][f]],
            'reading': ('two compiles of the same sources in this run (A and C, different '
                        'temporary roots); where they differ, the committed C source digest, '
                        'not an output digest, is the fixture\'s identity')}
        return out
    finally:
        for r in roots:
            shutil.rmtree(str(r), ignore_errors=True)


def supersedes_record(entry: Mapping, data: bytes | None) -> tuple[dict, list]:
    """[pure] One SUPERSEDES ``entry`` of the receipt from the superseded receipt's bytes at
    HEAD (``None``: not in this revision), and ``['superseded_receipt_changed:<path>']`` when
    they are present and are not the bytes it was written with (write-once)."""
    rec = dict(entry, present_at_head=data is not None,
               sha256_at_head=None if data is None else sha256(data))
    rec['byte_identical'] = data is not None and rec['sha256_at_head'] == entry['sha256']
    return rec, (['superseded_receipt_changed:%s' % entry['path']] if data is not None
                 and not rec['byte_identical'] else [])


def superseded_receipts_incomplete(head: GitTree, supersedes: Iterable[Mapping]) -> list:
    """[read-only] ``['superseded_receipts_incomplete:<path>', ...]`` for every committed
    ``results/live_ab/HARNESS_PIN_SUCCESSOR_*.json`` blob at HEAD whose path names no entry of
    ``supersedes`` (root 01:17 repair: a run at c5817f9 wrote a receipt whose hard-coded
    SUPERSEDES ended at the ..._0027 entry, so it never named the already-accepted ..._2009
    receipt of the 98ce004 harness and measured ``since_the_superseded_receipt`` against 0027
    instead).  This reads the committed tree directly, independent of what SUPERSEDES claims,
    so a future omission is caught the same way.  The receipt this call is itself about to
    write is never a committed blob at HEAD yet (write_once has not run), so it can never
    trigger this guard against itself."""
    known = {e['path'] for e in supersedes}
    problems = []
    for _mode, typ, name in head.entries(RESULTS_REL):
        if typ == 'blob' and re.fullmatch(r'HARNESS_PIN_SUCCESSOR_\d{8}_\d{4}\.json', name):
            path = '%s/%s' % (RESULTS_REL, name)
            if path not in known:
                problems.append('superseded_receipts_incomplete:%s' % path)
    return sorted(problems)


def partition_problems(p: Mapping) -> list:
    """[pure] ``[]`` when ``p`` (MUTATION_PARTITION_8F0B4AE's form) is a mutually exclusive,
    exhaustive partition: the specified ids unique; run = specified minus not_run; the four
    classes killed_by_the_right_control, killed_only_by_the_host_gate, survived_equivalent and
    survived_non_equivalent pairwise disjoint with union = run; every rerun-counted id among the
    right-control kills; the equivalents exactly survived_equivalent plus the equivalent
    host-gate-only kills; the guards of the non-equivalent survivors exactly the guards
    2113dbd controls; and each stated count the size of its class.  Else the names of what
    fails, each ``mutation_partition:<what>``."""
    bad = []
    spec = list(p.get('specified') or [])
    run = [i for i in spec if i not in (p.get('not_run') or {})]
    classes = {'killed_by_the_right_control': list(p.get('killed_by_the_right_control') or []),
               'killed_only_by_the_host_gate': list(p.get('killed_only_by_the_host_gate') or {}),
               'survived_equivalent': list(p.get('survived_equivalent') or []),
               'survived_non_equivalent': list(p.get('survived_non_equivalent') or {})}
    members = [i for ids in classes.values() for i in ids]
    if len(set(spec)) != len(spec):
        bad.append('specified_not_unique')
    if not set(p.get('not_run') or {}) <= set(spec):
        bad.append('not_run_not_specified')
    if len(set(members)) != len(members):
        bad.append('classes_overlap')
    if sorted(set(members)) != sorted(run):
        bad.append('classes_not_the_run')
    if not set(p.get('counted_after_a_solo_rerun') or {}) <= set(
            classes['killed_by_the_right_control']):
        bad.append('rerun_counted_outside_the_right_control')
    eq = set(p.get('equivalent') or {})
    if not eq <= set(classes['survived_equivalent']) | set(
            classes['killed_only_by_the_host_gate']) or \
            not set(classes['survived_equivalent']) <= eq:
        bad.append('equivalents')
    guards = set((p.get('survived_non_equivalent') or {}).values())
    if guards != set(p.get('guards_controlled_by_2113dbd') or {}):
        bad.append('guards')
    killed = classes['killed_by_the_right_control'] + classes['killed_only_by_the_host_gate']
    survived = classes['survived_equivalent'] + classes['survived_non_equivalent']
    sizes = {'specified': len(spec), 'run': len(run), 'not_run': len(p.get('not_run') or {}),
             'killed': len(killed), 'survived': len(survived), 'equivalent': len(eq),
             'distinct_non_equivalent_guards': len(guards)}
    sizes.update({k: len(v) for k, v in classes.items()})
    for key, size in sorted(sizes.items()):
        if (p.get('counts') or {}).get(key) != size:
            bad.append('count:%s' % key)
    return ['mutation_partition:%s' % b for b in bad]


def headline_is_a_partition(total: int, *parts: int) -> bool:
    """[pure] Whether mutually exclusive parts can make up ``total`` (a headline that says
    total T with parts a, b, c... double-counts when they add to more than T)."""
    return sum(parts) == total


def is_ancestor(repo: Path, rev: str, of: str) -> bool:
    res = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', rev, of],
                         capture_output=True, env=git_env(), timeout=120, check=False)
    return res.returncode == 0


def amendment_chain(repo: Path, head: GitTree, current: Mapping) -> tuple[dict, list]:
    """[read-only] The pre-outcome amendments (AMENDMENTS, oldest first) whose receipt HEAD
    carries, checked against git; ``current`` maps each pin label of AMENDMENTS[*]['keys'] to
    its HEAD value.  Per amendment present: the receipt's SHA-256; the commits that ADDED it
    (must be exactly its own commit, an ancestor of HEAD); every value its ``written`` records
    (none may be absent); each document digest it records equal to the blob at its own commit;
    for v3, the v2 receipt digest, commit and written digests it names equal to v2's.  Then
    ``head_equals_the_latest_written_values``: per label, the HEAD value equals the value of
    the LATEST present amendment recording that label (a document v3 did not write is compared
    with v2).  Problems: ``amendment_chain:<name>``, ``amendment_chain_link:<name>``,
    ``amendment_receipt_disagrees`` (also when no amendment receipt is present at all)."""
    problems, rows, latest = [], [], {}
    for am in AMENDMENTS:
        data = head.read(am['receipt'])
        row = {'name': am['name'], 'commit': am['commit'], 'receipt': am['receipt'],
               'present_at_head': data is not None}
        if data is None:
            rows.append(row)
            continue
        written = json.loads(data).get('written') or {}
        added = git(repo, 'log', '--diff-filter=A', '--format=%H', head.rev, '--',
                    am['receipt']).decode().split()
        known = resolve(repo, am['commit']) == am['commit']
        at = GitTree(repo, am['commit']) if known else None
        values = {label: written.get(key) for label, key in am['keys'].items()}
        blobs = {}
        for label in am['keys']:
            if label in DOCUMENTS and at is not None:
                blob = at.read(DOCUMENTS[label][0])
                blobs[label] = blob and sha256(blob)
        row.update({
            'receipt_sha256': sha256(data), 'receipt_bytes': len(data),
            'added_in_commits': added,
            'commit_is_an_ancestor_of_head': known and is_ancestor(repo, am['commit'], head.rev),
            'written': values,
            'document_blobs_at_its_commit': blobs,
            'written_equals_the_blob_at_its_commit': {
                label: blobs.get(label) is not None and blobs[label] == values[label]
                for label in am['keys'] if label in DOCUMENTS}})
        if added != [am['commit']] or not row['commit_is_an_ancestor_of_head'] or \
                any(v is None for v in values.values()) or \
                not all(row['written_equals_the_blob_at_its_commit'].values()):
            problems.append('amendment_chain:%s' % am['name'])
        link = am.get('names_predecessor')
        if link:
            prev = next((r for r in rows if r['name'] == link['name']), {})
            named = json.loads(data).get(link['field']) or {}
            named_written = named.get(link['written_field']) or {}
            prev_keys = next(a['keys'] for a in AMENDMENTS if a['name'] == link['name'])
            prev_written = {prev_keys[lb]: v for lb, v in (prev.get('written') or {}).items()}
            row['names_its_predecessor'] = {
                'predecessor': link['name'],
                'predecessor_present_at_head': bool(prev.get('present_at_head')),
                'receipt_sha256_named': named.get('receipt_sha256'),
                'equals_the_predecessor_receipt_at_head':
                    named.get('receipt_sha256') is not None
                    and named.get('receipt_sha256') == prev.get('receipt_sha256'),
                'commit_named': named.get('commit'),
                'equals_the_predecessor_commit':
                    named.get('commit') is not None and named.get('commit') == prev.get('commit'),
                'written_digests_named': named_written,
                'equal_the_predecessor_written_values': bool(named_written) and all(
                    prev_written.get(k) == v for k, v in named_written.items())}
            if not all(row['names_its_predecessor'][k] for k in (
                    'predecessor_present_at_head', 'equals_the_predecessor_receipt_at_head',
                    'equals_the_predecessor_commit', 'equal_the_predecessor_written_values')):
                problems.append('amendment_chain_link:%s' % am['name'])
        for label, value in values.items():
            latest[label] = (am['name'], value)
        rows.append(row)
    agreement = {label: current.get(label) is not None and current.get(label) == value
                 for label, (_n, value) in latest.items()}
    if not agreement or not all(agreement.values()):
        problems.append('amendment_receipt_disagrees')
    return {'chain': rows,
            'latest_writer': {label: name for label, (name, _v) in sorted(latest.items())},
            'head_equals_the_latest_written_values': agreement}, problems


def document_pin_history(repo: Path, old: GitTree, head: GitTree) -> dict:
    """[read-only] Per DOCUMENTS entry: its SHA-256 and byte length at b049307, at the commit of
    every amendment of AMENDMENTS that is an ancestor of HEAD, and at HEAD -- from git blobs,
    never from a receipt -- and at which of those steps it moved."""
    steps = [('b049307', old)]
    for am in AMENDMENTS:
        if resolve(repo, am['commit']) == am['commit'] and is_ancestor(repo, am['commit'],
                                                                         head.rev):
            steps.append((am['name'] + ' ' + am['commit'][:7], GitTree(repo, am['commit'])))
    steps.append(('head', head))
    out = {}
    for label, (rel, _expected) in DOCUMENTS.items():
        pins = []
        for name, tree in steps:
            blob = tree.read(rel)
            pins.append({'at': name, 'rev': tree.rev, 'sha256': blob and sha256(blob),
                         'bytes': blob and len(blob)})
        for prev, row in zip(pins, pins[1:]):
            row['moved_from_the_previous_step'] = row['sha256'] != prev['sha256']
        out[label] = {'path': rel, 'pins': pins}
    return out


def since_superseded(repo: Path, head: GitTree, smap: Mapping,
                     supersedes: list) -> tuple[dict, list]:
    """[read-only] The exact changed bytes since the LATEST superseded receipt (last entry of
    ``supersedes`` present and byte-identical at HEAD): its successor harness map re-derived
    from the git blobs of the head it recorded (``superseded_map_reproduces_from_git``; else
    ``superseded_map_does_not_reproduce``), and a diff record (diff_entry) per harness entry
    that moved since, and per DOCUMENTS entry whose digest differs from the one it recorded."""
    last = next((e for e in reversed(supersedes) if e.get('byte_identical')), None)
    if last is None:
        return {'receipt': None, 'reading': 'no superseded receipt is present at HEAD'}, []
    data = json.loads(head.read(last['path']) or b'{}')
    hp = data.get('harness_pin', {}).get('successor', {})
    rev = hp.get('rev') or (data.get('repository') or {}).get('head')
    prior_map = hp.get('map') or {}
    problems = []
    if not rev or resolve(repo, rev) != rev:
        return {'receipt': last['path'], 'recorded_head': rev,
                'reading': 'the head it recorded is not in this repository'}, \
            ['superseded_head_missing']
    then = GitTree(repo, rev)
    reproduces = harness_map(then) == prior_map
    if not reproduces:
        problems.append('superseded_map_does_not_reproduce')
    moved = sorted(n for n in set(prior_map) | set(smap) if prior_map.get(n) != smap.get(n))
    harness = {n: diff_entry(repo, then, head, '%s/%s' % (LIVE_REL, n)) for n in moved}
    docs = {}
    for label, (rel, _e) in DOCUMENTS.items():
        recorded = ((data.get('documents') or {}).get(label) or {}).get('head')
        now = head.read(rel)
        if recorded != (now and sha256(now)):
            docs[label] = dict(diff_entry(repo, then, head, rel), recorded_in_it=recorded)
    if not all(r['diff_applied_to_old_gives_new'] for r in list(harness.values())
               + list(docs.values())):
        problems.append('since_superseded_diff_does_not_reproduce')
    return {'receipt': last['path'], 'receipt_sha256': last['sha256_at_head'],
            'recorded_head': rev,
            'recorded_canonical_sha256': hp.get('canonical_sha256'),
            'superseded_map_reproduces_from_git': reproduces,
            'head_canonical_sha256': sha256_canonical(dict(smap)),
            'harness_entries_moved': harness,
            'harness_entries_unchanged': len([n for n in smap if prior_map.get(n) == smap[n]]),
            'documents_moved': docs}, problems


RUN_ROW_KEYS = ('id', 'utc', 'command', 'result')


def load_runs_of_this_step(path: Path | None, tokenize: Callable[[str], str]) -> tuple[object,
                                                                                       list]:
    """[read-only] ``--runs-of-this-step``: a JSON list of objects, each with non-empty string
    RUN_ROW_KEYS (other keys kept), strings tokenized.  ``(section, problems)``; a missing,
    unreadable or malformed file is ``runs_of_this_step_malformed``."""
    if path is None:
        return 'not given in this invocation', []
    try:
        raw = Path(path).read_bytes()
        rows = json.loads(raw)
    except (OSError, ValueError):
        return None, ['runs_of_this_step_malformed']
    if not isinstance(rows, list) or not rows or not all(
            isinstance(r, dict) and all(isinstance(r.get(k), str) and r[k].strip()
                                        for k in RUN_ROW_KEYS) for r in rows):
        return None, ['runs_of_this_step_malformed']

    def tok(v: object) -> object:
        if isinstance(v, str):
            return tokenize(v)
        if isinstance(v, list):
            return [tok(x) for x in v]
        if isinstance(v, dict):
            return {k: tok(x) for k, x in v.items()}
        return v
    return {'source_sha256': sha256(raw), 'rows': [tok(r) for r in rows],
            'reading': ('every run of the step that made this receipt, pass or fail, made '
                        'before the tool ran; the tool run itself is solo_run_suites')}, []


def fixture_uses(log: Path, start_utc: str, end_utc: str) -> dict:
    """[read-only] The lines of the fixture's uses log (``sm_fixture._log_use``) written in
    ``[start_utc, end_utc]``: how often a suite used the compiled test double, how (a verified
    cache or a fresh compile), and the SHA-256 of every binary it executed with the compiler
    and linker that built them.  A missing log is zero uses."""
    rows = []
    try:
        lines = Path(log).read_text('utf-8').splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and start_utc <= str(row.get('utc', '')) <= end_utc:
            rows.append(row)
    outputs = sorted({json.dumps(r.get('outputs'), sort_keys=True) for r in rows})
    return {'log': FIXTURE_USES_LOG, 'uses': len(rows),
            'events': {e: sum(1 for r in rows if r.get('event') == e)
                       for e in sorted({str(r.get('event')) for r in rows})},
            'distinct_output_sets': [json.loads(o) for o in outputs],
            'compilers': sorted({str(r.get('clang_version')) for r in rows}),
            'linkers': sorted({str(r.get('ld_version')) for r in rows})}


def fixture_section(repo: Path, head: GitTree) -> tuple[dict, list]:
    problems = []
    src = head.read(FIXTURE_REL)
    if src is None:
        raise Refused(['fixture_absent'])
    sources = fixture_sources(src)
    controls = fixture_missing_cache_controls(repo, sources['cache_dir_name'])
    for tag in FIXTURE_CONTROL_TAGS:
        if not controls.get(tag, {}).get('ok'):
            problems.append('fixture_control:%s' % tag)
    # the outputs of this run (A) never appear in the freeze tree or the real manifest
    outputs = {v for v in controls['A_rebuild'].get('files', {}).values()
               if HEX64.fullmatch(v)}
    freeze_blobs = {p: head.read(p) or b'' for p in blob_digests(repo, head.rev,
                                                                 [RESULTS_REL + '/freeze'])}
    in_freeze = sorted(p for p, data in freeze_blobs.items()
                       if any(h.encode() in data for h in outputs))
    tracked = git(repo, 'ls-tree', '-r', '--name-only', '--full-tree', head.rev).decode()
    named_in_tree = [p for p in tracked.splitlines() if 'eb1c_sm_fixture' in p]
    manifest = json.loads(head.read(SERVING_MANIFEST_REL) or b'{}')
    lau = manifest.get('launcher')
    launcher = str(lau.get('path', '')) if isinstance(lau, dict) else str(lau or '')
    exclusion = {
        'fixture_output_digests_of_this_run': sorted(outputs),
        'freeze_tree_files_containing_any_of_them': in_freeze,
        'tracked_paths_naming_the_cache': named_in_tree,
        'real_manifest_launcher_is_a_repo_path_not_a_temp_path': launcher.startswith('<REPO>/'),
    }
    if in_freeze or named_in_tree or not exclusion[
            'real_manifest_launcher_is_a_repo_path_not_a_temp_path']:
        problems.append('fixture_outputs_not_excluded')
    imports = re.compile(r'^\s*(?:import|from)\s+(\w+)', re.M)
    ctl = {p.stem: set(imports.findall(p.read_text('utf-8')))
           for p in (repo / 'experiments/live_ab_controls').glob('*.py')}
    direct = sorted(m for m, deps in ctl.items() if 'sm_fixture' in deps)
    consumers = {'import_sm_fixture': direct,
                 'through_one_of_those': sorted(m for m, deps in ctl.items()
                                                if m not in direct and deps & set(direct))}
    own_names = {Path(rel).name for rel in OWN_FILES}
    cache_refs = sorted(p.name for p in (repo / 'experiments').rglob('*.py')
                        if p.name not in own_names
                        and 'eb1c_sm_fixture_' in p.read_text('utf-8', 'replace'))
    shared = Path(PRESCRIBED_LABSBX) / sources['cache_dir_name']
    return {
        'ruling': ('reviews/eb1_fixture_and_wip_delta_20260924_0703.md (main ccdda96) item 1: '
                   'acceptable as a model-free control fixture within its disclosed scope'),
        'fixture_module': {'path': FIXTURE_REL, 'sha256': sha256(src), 'bytes': len(src)},
        'c_sources': sources,
        'compiler': compiler_record(),
        'consumers': consumers,
        'files_naming_the_cache_directory': cache_refs,
        'shared_cache_the_suites_use': {
            'path': str(shared), 'exists_at_this_run': (shared / 'llama-server').is_file(),
            'note': ('the suites run under TMPDIR=<prescribed>/labsbx and reuse this cache; '
                     'the controls below never touch it')},
        'statement': ('the fixture outputs (the compiled launcher and two libraries, the '
                      'synthetic CMakeCache/build-info/receipt/logs of sm_fixture.Build) are TEST '
                      'ARTIFACTS under temporary directories: excluded from the freeze manifest '
                      'and from any evidence about the real durable build; no control result '
                      'is a real-host receipt'),
        'exclusion_checks': exclusion,
        'missing_cache_controls': controls,
        'missing_cache_controls_counts': {
            'planned': len(FIXTURE_CONTROL_TAGS),
            'completed': sum(1 for t in FIXTURE_CONTROL_TAGS
                             if t in controls and 'unparsed_output' not in controls[t]),
            'as_expected': sum(1 for t in FIXTURE_CONTROL_TAGS
                               if controls.get(t, {}).get('ok'))},
    }, problems


# --------------------------------------------------------------------------- #
# the solo-run suites
# --------------------------------------------------------------------------- #
RAN_RE = re.compile(r'^Ran (\d+) tests? in ([0-9.]+)s$', re.M)
VERDICT_RE = re.compile(r'^(OK|FAILED)(?: \((.*)\))?$', re.M)
VAL_RE = re.compile(r'^ran=(\d+) failures=(\d+) errors=(\d+) skipped=(\d+)$', re.M)
HEADER_RE = re.compile(r'^(FAIL|ERROR|UNEXPECTED SUCCESS): (.+)$', re.M)
SKIP_RE = re.compile(r"\.\.\. skipped (.*)$")
TEST_ID_RE = re.compile(r'^(\w+) \(([\w.]+)\)')


def parse_suite_output(text: str, returncode: int, planned: int | None,
                       stdout: str = '') -> dict:
    """The runner's own summary, never inferred: the LAST ``Ran`` line and the LAST verdict
    line of ``text`` (the runner's stream, stderr; test output on stdout is kept apart so it
    cannot supply either line).  ``passed`` only when both exist, the verdict is OK, the exit
    code is 0 and the number run equals the number planned.  ``stdout`` supplies only the
    validation script's own ``ran=... failures=...`` line."""
    ran = RAN_RE.findall(text)
    verdict = VERDICT_RE.findall(text)
    val = VAL_RE.findall(stdout)
    counts = {}
    if verdict and verdict[-1][1]:
        for part in verdict[-1][1].split(', '):
            k, _, v = part.partition('=')
            if v.isdigit():
                counts[k.strip()] = int(v)
    skips, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        m = SKIP_RE.search(line)
        if m:
            ident = TEST_ID_RE.match(line) or (i and TEST_ID_RE.match(lines[i - 1]))
            skips.append({'test': ident.group(2) if ident else None,
                          'reason': m.group(1)[:300]})
    out = {
        'exit': returncode,
        'ran_line': ('Ran %s tests in %ss' % ran[-1]) if ran else None,
        'ran': int(ran[-1][0]) if ran else None,
        'runner_seconds': float(ran[-1][1]) if ran else None,
        'verdict_line': (verdict[-1][0] + (' (%s)' % verdict[-1][1] if verdict[-1][1] else ''))
        if verdict else None,
        'verdict_counts': counts,
        'script_summary_line': ('ran=%s failures=%s errors=%s skipped=%s' % val[-1])
        if val else None,
        'failure_headers': [h[0] + ': ' + h[1] for h in HEADER_RE.findall(text)],
        'skips': skips,
        'planned': planned,
    }
    out['completed_equals_planned'] = (out['ran'] is not None and planned is not None
                                       and out['ran'] == planned)
    out['passed'] = (returncode == 0 and out['ran'] is not None and bool(verdict)
                     and verdict[-1][0] == 'OK' and out['completed_equals_planned'])
    return out


PLAN_PROBE = r'''
import json, sys, unittest
from collections import Counter
loader = unittest.TestLoader()
if sys.argv[1] == 'discover':
    suite = loader.discover(sys.argv[2], pattern='tests_*.py')
else:
    sys.path.insert(0, sys.argv[2])
    import importlib
    suite = loader.loadTestsFromModule(importlib.import_module(sys.argv[3]))
per, failed = Counter(), []
def walk(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            walk(t)
        else:
            per[t.id().split('.')[0]] += 1
            if type(t).__name__ == '_FailedTest':
                failed.append(t.id())
walk(suite)
print(json.dumps({'planned': suite.countTestCases(), 'per_module': dict(sorted(per.items())),
                  'import_failures': failed}))
'''


def planned_counts(repo: Path, argv: list) -> dict:
    if '-s' in argv:
        probe = ['discover', argv[argv.index('-s') + 1]]
    else:
        script = Path(argv[0])
        probe = ['module', str(script.parent), script.stem]
    res = subprocess.run([PY, '-c', PLAN_PROBE] + probe, cwd=str(repo), capture_output=True,
                         text=True, timeout=900, check=False)
    try:
        return json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'planned': None, 'probe_error': (res.stdout + res.stderr)[-400:]}


def utc() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def ps_rows() -> list:
    """``(pid, ppid, started_epoch | None, command)`` of every process (``ps``, C locale)."""
    try:
        res = subprocess.run(['ps', '-axo', 'pid=,ppid=,lstart=,command='], capture_output=True,
                             text=True, timeout=30, check=False,
                             env=dict(os.environ, LC_ALL='C', LANG='C'))
        text = res.stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = []
    for line in text.splitlines():
        parts = line.split(None, 7)
        if len(parts) == 8 and parts[0].isdigit() and parts[1].isdigit():
            try:
                started = time.mktime(time.strptime(' '.join(parts[2:7]),
                                                    '%a %b %d %H:%M:%S %Y'))
            except ValueError:
                started = None
            rows.append((int(parts[0]), int(parts[1]), started, parts[7]))
    return rows


def tree_of(rows: list, roots: Iterable[int]) -> set:
    """The pids of ``roots`` and of all their descendants in ``rows``."""
    kids: dict = {}
    for pid, ppid, _s, _c in rows:
        kids.setdefault(ppid, []).append(pid)
    seen, todo = set(), [r for r in roots if r]
    while todo:
        q = todo.pop()
        if q not in seen:
            seen.add(q)
            todo.extend(kids.get(q, []))
    return seen


def ancestors_of(rows: list, pid: int) -> set:
    parent = {q: pp for q, pp, _s, _c in rows}
    out = set()
    while pid and pid not in out:
        out.add(pid)
        pid = parent.get(pid, 0)
    return out


def watched_outside(rows: list, known: set, tokenize: Callable[[str], str],
                    since: float | None = None) -> list:
    """[pure] Watched processes (WATCH) whose pid is not in ``known`` (the suite's tree as
    observed so far, this tool and its ancestors).  ``attribution``:
    ``orphan_started_during_the_suite`` when its parent is launchd (pid 1) and it started at
    or after ``since`` (a descendant reparented before a sample caught it in the tree -- the
    controls orphan servers on purpose, e.g. tests_eb1_entry C10); otherwise ``foreign``."""
    out = []
    for pid, ppid, started, cmd in rows:
        if pid in known or cmd.startswith('ps -axo') or not any(w in cmd for w in WATCH):
            continue
        orphan = (since is not None and ppid == 1 and started is not None
                  and started >= since - 1)
        out.append({'pid': pid, 'ppid': ppid,
                    'started_utc': None if started is None else time.strftime(
                        '%Y-%m-%dT%H:%M:%SZ', time.gmtime(started)),
                    'command_head': tokenize(cmd)[:140],
                    'attribution': 'orphan_started_during_the_suite' if orphan else 'foreign'})
    return out


def host_snapshot(repo: Path, known: set, tokenize: Callable[[str], str],
                  since: float | None = None) -> dict:
    st = os.statvfs(str(repo))
    _rc, vm = run_text(['vm_stat'])
    page = re.search(r'page size of (\d+) bytes', vm)
    pages = {k.strip(): int(v.strip().rstrip('.')) for k, v in
             re.findall(r'^(Pages [a-z ]+):\s+(\d+)\.?$', vm, re.M)}
    avail = None
    if page:
        avail = int(page.group(1)) * sum(pages.get(k, 0) for k in (
            'Pages free', 'Pages inactive', 'Pages speculative'))
    _rc, batt = run_text(['pmset', '-g', 'batt'])
    rows = ps_rows()
    return {
        'utc': utc(),
        'load_average': run_text(['sysctl', '-n', 'vm.loadavg'])[1].strip(),
        'ncpu': os.cpu_count(),
        'memory_bytes': int((run_text(['sysctl', '-n', 'hw.memsize'])[1].strip() or '0')),
        'vm_free_inactive_speculative_bytes': avail,
        'disk_free_bytes_repo_volume': st.f_bavail * st.f_frsize,
        'battery': [ln.strip() for ln in batt.splitlines()[1:2]],
        'processes': len(rows),
        'watched_processes_outside_the_suite': watched_outside(
            rows, known | ancestors_of(rows, os.getpid()), tokenize, since),
        'reading': 'an observation at utc; not a capacity reservation',
    }


class Sampler(threading.Thread):
    """``ps`` every SAMPLE_EVERY_S while a suite runs.  ``known`` accumulates every pid ever
    seen in the suite's tree (so a descendant reparented later stays attributed); ``seen``
    keeps each watched process outside it, with its attribution."""

    def __init__(self, child: int, tokenize: Callable[[str], str], since: float) -> None:
        super().__init__(daemon=True)
        self.child, self.tokenize, self.since = child, tokenize, since
        self.stop_event = threading.Event()
        self.samples = 0
        self.known: set = set()
        self.seen: dict = {}

    def sample(self) -> None:
        rows = ps_rows()
        self.samples += 1
        self.known |= tree_of(rows, [self.child]) | ancestors_of(rows, os.getpid())
        for row in watched_outside(rows, self.known, self.tokenize, self.since):
            self.seen.setdefault(row['pid'], row)
        for pid in list(self.seen):                 # seen outside first, in the tree later
            if pid in self.known:
                self.seen.pop(pid)

    def run(self) -> None:
        self.sample()
        while not self.stop_event.wait(SAMPLE_EVERY_S):
            self.sample()


def solo_verdict(runs: list) -> dict:
    """[pure] ``solo``: no watched process attributed ``foreign`` before, during (sampled) or
    after any suite.  ``solo_strict``: no watched process outside a suite's tree at all."""
    rows = [row for r in runs for row in (r['host_before']['watched_processes_outside_the_suite']
                                          + r['sampler']['watched_outside_the_tree']
                                          + r['host_after']['watched_processes_outside_the_suite'])]
    return {'solo': not any(row['attribution'] == 'foreign' for row in rows),
            'solo_strict': not rows,
            'foreign': [row for row in rows if row['attribution'] == 'foreign'],
            'orphans_started_during_a_suite': sorted({row['command_head'] for row in rows
                                                      if row['attribution'] != 'foreign'})}


def run_suite(repo: Path, name: str, argv: list, tokenize: Callable[[str], str],
             pin_logs_dir: Path) -> dict:
    plan = planned_counts(repo, argv)
    before = host_snapshot(repo, set(), tokenize)
    since = time.time()
    err_fd, err_path = tempfile.mkstemp(prefix='pinsucc_%s_' % name, suffix='.err')
    out_fd, out_path = tempfile.mkstemp(prefix='pinsucc_%s_' % name, suffix='.out')
    start_utc, m0 = utc(), time.monotonic()
    with os.fdopen(err_fd, 'wb') as err, os.fdopen(out_fd, 'wb') as out:
        proc = subprocess.Popen([PY] + argv, cwd=str(repo), stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL)
        sampler = Sampler(proc.pid, tokenize, since)
        sampler.start()
        timed_out = False
        while True:
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - m0 > SUITE_TIMEOUT_S and not timed_out:
                timed_out = True
                proc.kill()
            time.sleep(0.5)
        proc.returncode = os.waitstatus_to_exitcode(status)
        sampler.stop_event.set()
        sampler.join()
    wall = time.monotonic() - m0
    end_utc = utc()
    text = Path(err_path).read_text('utf-8', 'replace')
    stdout = Path(out_path).read_text('utf-8', 'replace')
    os.unlink(err_path)
    os.unlink(out_path)
    parsed = parse_suite_output(text, proc.returncode, plan.get('planned'), stdout)
    for row in parsed['skips']:
        row['reason'] = tokenize(row['reason'])
    parsed['failure_headers'] = [tokenize(h) for h in parsed['failure_headers']]
    after = host_snapshot(repo, sampler.known, tokenize, since)
    stderr_bytes, stdout_bytes = text.encode('utf-8'), stdout.encode('utf-8')
    stderr_sha256, stdout_sha256 = sha256(stderr_bytes), sha256(stdout_bytes)
    # retained whether or not the suite passed, so a red run is diagnosed from what is kept
    stderr_log = retain_pin_log(pin_logs_dir / ('%s.stderr.gz' % name), stderr_bytes,
                                stderr_sha256, tokenize)
    stdout_log = retain_pin_log(pin_logs_dir / ('%s.stdout.gz' % name), stdout_bytes,
                                stdout_sha256, tokenize)
    return {
        'suite': name,
        'argv': [tokenize(PY)] + argv,
        'cwd': '<REPO>',
        'start_utc': start_utc, 'end_utc': end_utc, 'wall_seconds': round(wall, 3),
        'timed_out': timed_out,
        'plan': plan,
        'result': parsed,
        'stderr_sha256': stderr_sha256,
        'stderr_bytes': len(stderr_bytes),
        'stdout_sha256': stdout_sha256,
        'stdout_bytes': len(stdout_bytes),
        'stderr_tail': [tokenize(ln) for ln in text.rstrip('\n').splitlines()[-4:]],
        'stdout_tail': [tokenize(ln) for ln in stdout.rstrip('\n').splitlines()[-2:]],
        'stderr_log': stderr_log,
        'stdout_log': stdout_log,
        'child_rusage': {'user_s': round(ru.ru_utime, 3), 'system_s': round(ru.ru_stime, 3),
                         'max_rss_bytes_darwin': ru.ru_maxrss},
        'host_before': before, 'host_after': after,
        'sampler': {'every_s': SAMPLE_EVERY_S, 'samples': sampler.samples,
                    'watched_patterns': list(WATCH),
                    'pids_attributed_to_the_suite_tree': len(sampler.known),
                    'watched_outside_the_tree': [row for _p, row in sorted(sampler.seen.items())],
                    'reading': ('watched processes never seen in the suite\'s own process tree '
                                'at any sample (every %gs); sampled, not continuous'
                                % SAMPLE_EVERY_S)},
    }


# --------------------------------------------------------------------------- #
# the receipt
# --------------------------------------------------------------------------- #
def make_tokenizer(repo: Path) -> Callable[[str], str]:
    pairs = sorted({(str(Path(repo).resolve()), '<REPO>'), (str(repo), '<REPO>'),
                    (os.path.realpath(tempfile.gettempdir()), '<TMP>'),
                    (tempfile.gettempdir(), '<TMP>'), (str(Path.home()), '<HOME>')},
                   key=lambda p: -len(p[0]))

    def tokenize(s: str) -> str:
        for raw, token in pairs:
            s = s.replace(raw, token)
        return s
    return tokenize


def worktree_state(repo: Path) -> tuple[list, list]:
    """(entries, problems): ``git status --porcelain`` (untracked included, ignored not);
    anything but OWN_FILES is a problem."""
    out = git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    entries = [e.decode('utf-8') for e in out.split(b'\0') if e]
    problems = ['working_tree_dirty:%s' % e[3:] for e in entries if e[3:] not in OWN_FILES]
    return entries, problems


def pin_log_staging_root(repo: Path) -> Path:
    """A fresh temporary directory for THIS run's suite logs, checked to sit outside ``repo`` --
    ``git status`` on ``repo`` can never see it, however deep ``--out-dir`` sits inside the
    repository.  This is the fix for the defect where a real run with ``--out-dir`` inside the
    repository (``results/live_ab``) wrote each suite's retained log straight into the tree
    mid-run; the tool's own end-of-run check (``worktree_state`` before vs. after) then saw
    those new untracked files and refused the whole run as ``tree_changed_during_the_run``, on
    an otherwise clean pass.  Logs written here are promoted into the tree, write-once, only
    once that check has passed with no other problem either (``promote_pin_log``); a refused or
    otherwise problem-carrying run leaves them here, never in the tree."""
    root = Path(os.path.realpath(tempfile.mkdtemp(prefix='pinsucc_pinlogs_staging_')))
    repo_r = Path(os.path.realpath(str(repo)))
    if root == repo_r or repo_r in root.parents:
        raise Refused(['pin_logs_staging_inside_repo'])
    return root


def build_receipt(repo: Path, predecessor: str, *, run_suites: bool,
                  runs_of_this_step: Path | None = None, out_dir: Path | None = None) -> dict:
    repo = Path(repo).resolve()
    tokenize = make_tokenizer(repo)
    problems: list = []
    started = utc()
    #: Fixed once, at the start, so the receipt's own filename (main() uses this value, not a
    #: fresh clock read) and its pin_logs directory always agree.
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    if resolve(repo, predecessor) is None:
        raise Refused(['predecessor_missing'])
    old = GitTree(repo, predecessor)
    head = GitTree(repo, 'HEAD')
    entries, dirty = worktree_state(repo)
    problems += dirty

    # 1-2. harness maps
    pmap = harness_map(old)
    problems += predecessor_problems(pmap)
    smap = harness_map(head)
    view = lab_common_view(repo)
    if view['harness'] != smap:
        problems.append('successor_differs_from_lab_common_on_the_working_tree')
    if view['canonical_of_map'] != sha256_canonical(smap):
        problems.append('canonical_digest_differs_from_lab_common')

    # 3. per changed / added entry, and every other file of the subset
    changed = sorted(n for n in set(pmap) | set(smap) if pmap.get(n) != smap.get(n))
    harness_changes = {n: diff_entry(repo, old, head, '%s/%s' % (LIVE_REL, n)) for n in changed}
    if not all(r['diff_applied_to_old_gives_new'] for r in harness_changes.values()):
        problems.append('diff_does_not_reproduce')
    names = git(repo, 'diff', '--name-status', '--no-renames', '-z', old.rev, head.rev
                ).decode('utf-8').split('\0')
    subset = {}
    for i in range(0, len(names) - 1, 2):
        path = names[i + 1]
        if path.startswith(LIVE_REL + '/') and path.count('/') == 2 and \
                path.rsplit('/', 1)[1] in set(pmap) | set(smap):
            continue
        subset[path] = diff_entry(repo, old, head, path)
    if not all(r['diff_applied_to_old_gives_new'] for r in subset.values()):
        problems.append('subset_diff_does_not_reproduce')
    old_lc, new_lc = old.read(LIVE_REL + '/lab_common.py'), head.read(LIVE_REL + '/lab_common.py')

    # 4. reused files, decision modules, documents, rule block, serving manifest
    reused_old = module_constant(old_lc, 'REUSED_FILES')
    reused_new = module_constant(new_lc, 'REUSED_FILES')
    rmap = {rev: {n: sha256(t.read('%s/%s' % (REUSED_REL, n)) or b'') for n in reused_new}
            for rev, t in (('b049307', old), ('head', head))}
    reused_ok = reused_old == reused_new and rmap['b049307'] == rmap['head'] and \
        list(reused_new) == view['reused_files']
    if not reused_ok:
        problems.append('reused_files_changed')
    decision = {n: {'b049307': pmap.get(n), 'head': smap.get(n)} for n in DECISION_MODULES}
    if any(r['b049307'] is None or r['b049307'] != r['head'] for r in decision.values()):
        problems.append('decision_module_changed')
    docs = {}
    for label, (rel, expected_old) in DOCUMENTS.items():
        o, n = old.read(rel), head.read(rel)
        docs[label] = {'path': rel, 'b049307': o and sha256(o), 'head': n and sha256(n),
                       'b049307_bytes': o and len(o), 'head_bytes': n and len(n),
                       'b049307_is_the_reviewed_pre_image': bool(o) and sha256(o) == expected_old}
        if not docs[label]['b049307_is_the_reviewed_pre_image']:
            problems.append('pre_image:%s' % label)
    cfg_old, cfg_new = json.loads(old.read(CONFIG_REL)), json.loads(head.read(CONFIG_REL))
    keys_old = module_constant(old_lc, 'RULE_BLOCK_KEYS')
    keys_new = module_constant(new_lc, 'RULE_BLOCK_KEYS')
    rb = {'b049307': rule_block_digest(cfg_old, keys_old),
          'head': rule_block_digest(cfg_new, keys_new),
          'keys_unchanged': keys_old == keys_new}
    rb['head_equals_lab_common_rule_block_sha256'] = view['rule_block'] == rb['head']
    rb['unchanged'] = rb['b049307'] == rb['head'] == RULE_BLOCK and rb['keys_unchanged']
    if not (rb['unchanged'] and rb['head_equals_lab_common_rule_block_sha256']):
        problems.append('rule_block_moved')
    mbytes = head.read(SERVING_MANIFEST_REL)
    manifest = json.loads(mbytes) if mbytes else {}
    mcanon = sha256_canonical(manifest) if mbytes else None
    cfg_value = (cfg_new.get('llama_cpp') or {}).get('serving_manifest_sha256')
    sm = {'path': SERVING_MANIFEST_REL,
          'b049307': {'artifact': 'absent' if old.read(SERVING_MANIFEST_REL) is None
                      else 'present',
                      'config_llama_cpp_serving_manifest_sha256':
                          (cfg_old.get('llama_cpp') or {}).get('serving_manifest_sha256')},
          'head': {'file_sha256': mbytes and sha256(mbytes), 'bytes': mbytes and len(mbytes),
                   'canonical_sha256': mcanon,
                   'file_is_canonical_json_plus_newline':
                       bool(mbytes) and mbytes == (canonical_json(manifest) + '\n').encode(),
                   'config_llama_cpp_serving_manifest_sha256': cfg_value,
                   'config_value_equals_canonical_digest': cfg_value == mcanon,
                   'carries_no_home_token': bool(mbytes) and b'<HOME>' not in mbytes,
                   'launcher_sha256': manifest.get('launcher_sha256'),
                   'libraries': len(manifest.get('libraries') or {}),
                   'code': '%s/lab_serving_manifest.py (added; harness entry)' % LIVE_REL}}
    if not (sm['head']['config_value_equals_canonical_digest']
            and sm['head']['file_is_canonical_json_plus_newline']
            and sm['head']['carries_no_home_token']):
        problems.append('serving_manifest_binding')
    cells = json.loads(head.read(DOCUMENTS['cells.json'][0]))
    sup = cells['provenance']['vocabulary_alignment']
    vocab = {'original_pin': sup['sha256'],
             'superseded_by': sup['superseded_by']['sha256'],
             'supersedes': sup['superseded_by']['supersedes'],
             'prior_successors': len(sup['superseded_by']['prior_successors'])}
    vocab['holds'] = (vocab['original_pin'] == VOCABULARY_ORIGINAL
                      and vocab['supersedes'] == VOCABULARY_ORIGINAL
                      and vocab['superseded_by'] == docs['protocol_FINAL.md']['head'])
    if not vocab['holds']:
        problems.append('cells_successor')
    current = {label: docs[label]['head'] for label in DOCUMENTS}
    current.update({'rule_block': rb['head'], 'serving_manifest_canonical': mcanon,
                    'serving_manifest_file': sm['head']['file_sha256']})
    amendments, aproblems = amendment_chain(repo, head, current)
    problems += aproblems
    amendments['document_pin_history'] = document_pin_history(repo, old, head)
    sup_block = cfg_new.get('server_supervision')
    landed = git(repo, 'log', '--format=%H', '-S"server_supervision"',
                 '%s..%s' % (old.rev, head.rev), '--', CONFIG_REL).decode().split()
    cfg_lines = [ln for ln in (head.read(CONFIG_REL) or b'').decode().splitlines()
                 if ln.lstrip().startswith('"server_supervision"')]
    fences = {label: (head.read(DOCUMENTS[label][0]) or b'').decode().count(cfg_lines[0])
              if len(cfg_lines) == 1 else 0
              for label in ('ARCHITECTURE_FINAL.md', 'protocol_FINAL.md')}
    naming = sorted(p.name for p in (repo / 'experiments/live_ab_controls').glob('tests_*.py')
                    if re.search(r'server_supervision|SERVER_SUPERVISION_KEY',
                                 p.read_text('utf-8')))
    supervision = {
        'b049307': cfg_old.get('server_supervision'),
        'head': sup_block,
        'config_line': cfg_lines,
        'same_line_occurrences_in_the_two_fences': fences,
        'lab_common_server_supervision_cap_at_head': view['server_supervision_cap'],
        'landed_in_commits': landed,
        'outside_rule_block': 'server_supervision' not in keys_new,
        'control_modules_naming_the_block': naming,
        'statement': (
            'The restart-cap binding is already IN this subset, not deferred to a later '
            'amendment: config.json carries server_supervision since commit %s (the '
            'synchronized amendment v2, receipt %s), and the ARCHITECTURE 6.1 and Appendix B '
            'fences carry the same line once each (same_line_occurrences_in_the_two_fences). '
            'Within the subset the cap is exercised only by model-free controls with temporary '
            'freeze trees and configurations (dryrun_live_ab.build_mock_freeze reads this '
            'config.json at experiments/live_ab/dryrun_live_ab.py:184; the modules in '
            'control_modules_naming_the_block construct, edit or remove the block); no trial, '
            'loaded phase or run against a real frozen configuration has exercised it.'
            % (','.join(c[:7] for c in landed) or 'NONE', AMENDMENT_RECEIPT_REL)),
    }
    if landed != [AMENDMENT_COMMIT] or not supervision['outside_rule_block'] or \
            fences != {'ARCHITECTURE_FINAL.md': 1, 'protocol_FINAL.md': 1} or not naming:
        problems.append('server_supervision_binding')

    # 5. prior observations not reissued
    table: dict = {}
    d_old = blob_digests(repo, old.rev, TRACKED_PREFIXES)
    d_new = blob_digests(repo, head.rev, TRACKED_PREFIXES)
    for p in set(d_old) | set(d_new):
        table[p] = {'b049307': d_old.get(p), 'head': d_new.get(p)}
    table['<rule block of config.json>'] = {'b049307': rb['b049307'], 'head': rb['head']}
    table['<harness map canonical digest>'] = {'b049307': sha256_canonical(pmap),
                                               'head': sha256_canonical(smap)}
    table['<serving manifest canonical digest>'] = {'b049307': None, 'head': mcanon}
    mhex = frozenset(HEX64.findall((mbytes or b'').decode('utf-8')))
    chex = frozenset(HEX64.findall((head.read(CONFIG_REL) or b'').decode('utf-8')))
    prior = []
    for rel in PRIOR_OBSERVATIONS:
        data = head.read(rel)
        if data is None or old.read(rel) != data:
            problems.append('prior_observation_missing_or_changed:%s' % rel)
            continue
        added = git(repo, 'log', '--diff-filter=A', '--format=%H', head.rev, '--', rel
                    ).decode().split()
        c = classify_pins(json.loads(data), table, mhex, tokenize, chex)
        prior.append(dict({'path': rel, 'sha256': sha256(data), 'bytes': len(data),
                           'added_in_commit': added[-1] if added else None,
                           'byte_identical_at_b049307_and_head': True,
                           'reissued_by_this_successor': False,
                           'verdict': record_verdict(c)}, **c))
    statements = []
    for rel, line_no, fragment in COUNT_STATEMENTS:
        data = head.read(rel) or b''
        lines = data.decode('utf-8', 'replace').splitlines()
        text = lines[line_no - 1] if len(lines) >= line_no else ''
        ok = fragment in text
        statements.append({'path': rel, 'line': line_no, 'text': text.strip(),
                           'sha256': sha256(data), 'cited_line_carries_it': ok,
                           'now': 'historical: the successor map has %d entries and %d changed'
                                  % (len(smap), len(changed))})
        if not ok:
            problems.append('count_statement:%s' % rel)

    # 6. the compiled C test double
    fixture, fproblems = fixture_section(repo, head)
    problems += fproblems
    # the receipt this one supersedes stays byte-identical where the head carries it
    supersedes = []
    for entry in SUPERSEDES:
        rec, sproblems = supersedes_record(entry, head.read(entry['path']))
        supersedes.append(rec)
        problems += sproblems
    problems += superseded_receipts_incomplete(head, SUPERSEDES)
    since, sproblems = since_superseded(repo, head, smap, supersedes)
    problems += sproblems
    step_runs, rproblems = load_runs_of_this_step(runs_of_this_step, tokenize)
    problems += rproblems
    partition = dict(MUTATION_PARTITION_8F0B4AE)
    problems += partition_problems(partition)
    headline = partition['headline_0518']
    partition['checked'] = {
        'exclusive_and_exhaustive': not partition_problems(partition),
        'headline_0518_is_a_partition': headline_is_a_partition(
            headline['total'], headline['killed'], headline['non_equivalent'],
            headline['equivalent']),
        'reading': ('partition_problems ran on this constant (a failure refuses the receipt); '
                    'the headline check sums the 05:18 parts against its total')}

    commits = [ln.split('\t', 1) for ln in git(
        repo, 'log', '--reverse', '--topo-order', '--format=%H%x09%s',
        '%s..%s' % (old.rev, head.rev)).decode().splitlines()]
    own = {}
    for rel in OWN_FILES:
        p = repo / rel
        status = next((e[:2] for e in entries if e[3:] == rel), None)
        own[rel] = {'sha256': sha256(p.read_bytes()) if p.is_file() else None,
                    'git_status': status if status else
                    ('committed' if head.read(rel) is not None else 'absent')}
    this_file = Path(__file__).resolve()

    receipt = {
        'schema': SCHEMA,
        'convention': 'deterministic-path',
        'convention_note': ('pins, maps and diff digests are deterministic functions of git '
                            'objects; wall times, host snapshots and timestamps are '
                            'observations of this run'),
        'status': STATUS,
        'this_is_not_a_freeze': ('no freeze bundle exists; nothing here approves a freeze, a '
                                 'loaded stage or a trial'),
        'authority': [
            'reviews/prerun_bundle_go_nogo_20260923_2040.md:16 (record the pre-outcome pin '
            'successor; preserve the old pin and all prior observations)',
            'reviews/restart_cap_estimand_ruling_20260923_2114.md (main ebcd637) item 2 (exact '
            'EB1/EB5 code and controls with old/new hashes, no loaded run)',
            'reviews/eb1_fixture_and_wip_delta_20260924_0703.md (main ccdda96) items 1 and 3',
            'reviews/eb1_eb5_pin_interim_audit_20260924_1304.md (main f0cb14c)',
            'reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md (main 78df9e5; "the '
            'revised pin must include the failure history and exact changed bytes")',
            'reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md (main 75c10af; "Re-pin '
            'after changing the builder and rerun only affected controls plus the already '
            'planned final solo receipt")',
            'reviews/eb1_eb5_summary_repair_interim_20260924_2208.md (main 76f5e71; "finish and '
            'commit amendment v3 ... and issue a fresh pin receipt")',
            'reviews/eb1_eb5_v3_pin_interim_20260925_0110.md (main bb093d7; the 0027 receipt '
            'keeps its non-solo label; "deliver one immutable completed subset with the exact '
            'final code/config/seed pins, all attempts/failures/missingness")',
            'reviews/predecision_abort_reporting_ruling_20260925_0710.md (main 9790043; "issue '
            'one new write-once superseding receipt after v4/code/control changes, retaining '
            'the ..._0027 receipt"; the 22:08 refusal and other failed attempts; the mutually '
            'exclusive mutation partition)',
            'reviews/eb1_eb5_reproduction_path_interim_20260925_1010.md (main 161966e; '
            '"Preserve all failed runs, missingness and original observations in the new '
            'write-once superseding receipt")',
        ],
        'run_started_utc': started,
        'receipt_stamp': stamp,
        'repository': {
            'predecessor': old.rev, 'head': head.rev,
            'commits_predecessor_to_head': [{'commit': c[0], 'subject': c[1]} for c in commits],
            'working_tree_porcelain': entries,
            'tool_files': own,
            'tool_run_from': tokenize(str(this_file)),
            'git_version': run_text(['git', '--version'])[1].strip(),
        },
        'harness_pin': {
            'semantics': ('lab_common.harness_file_hashes: the top-level experiments/live_ab/'
                          '*.py files plus config.json, sha256 of each file; canonical digest '
                          '= lab_common.sha256_canonical of the name -> sha256 map'),
            'predecessor': {'rev': old.rev, 'count': len(pmap),
                            'canonical_sha256': sha256_canonical(pmap),
                            'expected_canonical_sha256': PREDECESSOR_CANONICAL,
                            'equals_expected': not predecessor_problems(pmap), 'map': pmap},
            'successor': {'rev': head.rev, 'count': len(smap),
                          'canonical_sha256': sha256_canonical(smap),
                          'equals_lab_common_harness_file_hashes_on_the_working_tree':
                              view['harness'] == smap, 'map': smap},
            'counts': {'before': len(pmap), 'after': len(smap),
                       'modified': sum(1 for r in harness_changes.values()
                                       if r['status'] == 'modified'),
                       'added': sorted(n for n, r in harness_changes.items()
                                       if r['status'] == 'added'),
                       'removed': sorted(n for n, r in harness_changes.items()
                                         if r['status'] == 'deleted'),
                       'unchanged': len(set(pmap) & set(smap)) - sum(
                           1 for n in changed if n in pmap and n in smap)},
            'changed': harness_changes,
            'unchanged_entries': sorted(n for n in smap if pmap.get(n) == smap[n]),
            'diff_command': 'git ' + ' '.join(DIFF_ARGV) + ' <predecessor> <head> -- <path> '
                            '(every GIT_* variable unset, then GIT_CONFIG_NOSYSTEM=1, '
                            'GIT_CONFIG_GLOBAL=%s, GIT_ATTR_NOSYSTEM=1, LC_ALL=C)'
                            % os.devnull,
            'diff_check': ('each diff is applied with git apply -p1 to the predecessor bytes '
                           'in a directory outside any repository; the result must be the '
                           'HEAD bytes'),
        },
        'reused_files': {'dir': REUSED_REL, 'names_b049307': list(reused_old),
                         'names_head': list(reused_new), 'b049307': rmap['b049307'],
                         'head': rmap['head'], 'unchanged': reused_ok,
                         'reused_file_sha256_canonical': sha256_canonical(rmap['head'])},
        'decision_modules_byte_unchanged': decision,
        'documents': docs,
        'rule_block': rb,
        'serving_manifest': sm,
        'cells_vocabulary_successor': vocab,
        'amendments': amendments,
        'server_supervision': supervision,
        'other_files_changed_by_the_subset': subset,
        'prior_observations_not_reissued': {
            'classification': classify_pins.__doc__.split('\n\n', 1)[1].strip(),
            'records': prior,
            'harness_count_statements': statements,
        },
        'compiled_c_test_double': fixture,
        'supersedes': supersedes,
        'since_the_superseded_receipt': since,
        'disclosed_red_runs_before_this_successor': list(DISCLOSED_RED_RUNS),
        'disclosed_red_runs_counts': {
            'red_runs': sum(1 for r in DISCLOSED_RED_RUNS if r.get('kind') == 'red_run'),
            'review_findings': sum(1 for r in DISCLOSED_RED_RUNS
                                   if r.get('kind') == 'review_finding')},
        'mutation_partition_of_the_final_verification_of_8f0b4ae': partition,
        'runs_of_this_step_before_this_receipt': step_runs,
        'nothing_executed': ('no model, llama-server, llama.cpp build or network request; the '
                             'C test double compiled under temporary roots; the suites start '
                             'their own loopback mocks'),
        'prepared_by': ('Prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off (protocol 14.7).'),
    }
    pin_logs_staging = None
    if run_suites:
        if out_dir is None:
            raise Refused(['pin_logs_out_dir_required'])
        out_dir = Path(out_dir)
        final_pin_logs_dir = out_dir / PIN_LOGS_DIRNAME / stamp
        staging_root = pin_log_staging_root(repo)
        pin_logs_dir = staging_root / PIN_LOGS_DIRNAME / stamp
        pin_logs_staging = pin_logs_dir
        runs = [run_suite(repo, name, argv, tokenize, pin_logs_dir) for name, argv in SUITES]
        uses_log = Path(PRESCRIBED_LABSBX) / FIXTURE_USES_LOG
        used: set = set()
        for r in runs:
            r['fixture_uses'] = fixture_uses(uses_log, r['start_utc'], r['end_utc'])
            used |= {h for outs in r['fixture_uses']['distinct_output_sets']
                     for h in (outs or {}).values() if isinstance(h, str)
                     and HEX64.fullmatch(h)}
        freeze_blobs = {p: head.read(p) or b'' for p in blob_digests(
            repo, head.rev, [RESULTS_REL + '/freeze'])}
        in_freeze = sorted(p for p, data in freeze_blobs.items()
                           if any(h.encode() in data for h in used))
        receipt['compiled_c_test_double']['exclusion_checks'][
            'fixture_output_digests_the_suites_executed'] = sorted(used)
        receipt['compiled_c_test_double']['exclusion_checks'][
            'freeze_tree_files_containing_any_the_suites_executed'] = in_freeze
        if in_freeze:
            problems.append('fixture_outputs_used_by_the_suites_not_excluded')
        receipt['solo_run_suites'] = {
            'python': tokenize(PY),
            'order': [s[0] for s in SUITES],
            'runs': runs,
            'all_passed': all(r['result']['passed'] for r in runs),
            'solo_evidence': solo_verdict(runs),
            'planned_total': sum(r['plan'].get('planned') or 0 for r in runs),
            'completed_total': sum(r['result']['ran'] or 0 for r in runs),
            'deviation_from_the_contract_command': ('-v added to each discover command (for '
                                                    'skip reasons); nothing else'),
            'pin_logs_dir': tokenize(str(pin_logs_dir)),
            'pin_logs_reading': ('every suite\'s FULL stdout and stderr, gzip mtime 0, '
                                 'write-once at <this dir>/<suite>.std{out,err}.gz; '
                                 'stderr_tail/stdout_tail and the digests above are unchanged; '
                                 'retained whether or not the suite passed; staged outside the '
                                 'repository during the run and promoted here write-once only '
                                 'once the run turns out clean; a write, read-back or promotion '
                                 'failure refuses the whole receipt (pin_log_*)'),
        }
        entries_after, _ = worktree_state(repo)
        if resolve(repo, 'HEAD') != head.rev or entries_after != entries:
            problems.append('tree_changed_during_the_run')
        if not problems:
            # The run is otherwise clean: promote the write-once logs from staging into the
            # tree, together with the receipt main() is about to write.  Never done on a
            # refused or problem-carrying run (checked above) -- the tree check just re-read
            # stays valid, since nothing has touched the repository between it and here.  A
            # promotion refusal (``promote_pin_log``'s own write-once mismatch at the FINAL
            # path -- e.g. a same-stamp/out_dir retry whose suite output is not byte-stable)
            # must be caught here and folded into ``problems`` like any other refusal, NOT
            # left to propagate out of this function on its own: unlike every other Refused
            # this module raises, ``promote_pin_log``'s carries no draft, and left alone it
            # would bypass the ``if problems:`` draft-attachment below entirely -- silently
            # discarding the already fully-verified staged logs and skipping main()'s
            # "refused pin logs kept at" reporting (root review finding (d) on this fix's own
            # first draft).  ``pin_logs_staging`` is already set to ``pin_logs_dir`` above, so
            # once folded in here it is preserved and named exactly like a refusal from the
            # tree check would be.
            try:
                for row in runs:
                    for stream in ('stdout', 'stderr'):
                        staged = pin_logs_dir / ('%s.%s.gz' % (row['suite'], stream))
                        final = final_pin_logs_dir / ('%s.%s.gz' % (row['suite'], stream))
                        row['%s_log' % stream] = promote_pin_log(
                            staged, final, row['%s_sha256' % stream], tokenize)
            except Refused as exc:
                problems += exc.problems
            else:
                receipt['solo_run_suites']['pin_logs_dir'] = tokenize(str(final_pin_logs_dir))
                shutil.rmtree(str(staging_root), ignore_errors=True)
                pin_logs_staging = None
    else:
        receipt['solo_run_suites'] = 'not run in this invocation (--no-suites)'
    receipt['generated_utc'] = utc()
    if problems:
        draft = (receipt if pin_logs_staging is None
                 else dict(receipt, pin_logs_staging_dir=str(pin_logs_staging)))
        raise Refused(problems, draft)
    return receipt


def write_pin_log(path: Path, raw: bytes) -> str:
    """Write ``raw`` at ``path`` as a deterministic gzip member (mtime 0, no filename embedded;
    the same bytes in give the same bytes out, run to run and host to host, at a fixed
    compresslevel -- checked directly by ``PinLogTests.test_the_gzip_member_is_deterministic``,
    not assumed from a specific header byte).  Write-once, the same convention as ``write_once``
    (``O_CREAT|O_EXCL``, flushed, fsynced, read back): a rewrite with the SAME bytes already
    there is a no-op, a rewrite with DIFFERENT bytes REFUSES (``pin_log_mismatch``) and leaves
    the file untouched.  Any other write failure (a missing directory that cannot be made, a
    permission or disk error) also refuses, named (``pin_log_write_failed``), never raised as a
    bare OSError.  Returns the sha256 of the compressed bytes."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            existing = path.read_bytes()
            if existing != compressed:
                raise Refused(['pin_log_mismatch:%s' % path.name]) from None
            return sha256(existing)
        with os.fdopen(fd, 'wb') as fh:
            fh.write(compressed)
            fh.flush()
            os.fsync(fh.fileno())
        on_disk = path.read_bytes()
    except OSError as exc:
        raise Refused(['pin_log_write_failed:%s' % path.name]) from exc
    if on_disk != compressed:
        raise Refused(['pin_log_mismatch:%s' % path.name])
    return sha256(compressed)


def verify_pin_log(path: Path, expected_sha256: str) -> dict:
    """Read ``path`` back from disk -- never the bytes just written in memory -- and decompress
    it; check its sha256 against ``expected_sha256`` (the ``stdout_sha256`` / ``stderr_sha256``
    the tool already computed from the live run).  REFUSES when the file is missing
    (``pin_log_missing``) or the decompressed digest does not match
    (``pin_log_digest_mismatch``, also raised for bytes that do not even gunzip)."""
    if not path.exists():
        raise Refused(['pin_log_missing:%s' % path.name])
    try:
        on_disk = path.read_bytes()
        decompressed = gzip.decompress(on_disk)
    except OSError:
        raise Refused(['pin_log_digest_mismatch:%s' % path.name]) from None
    digest = sha256(decompressed)
    if digest != expected_sha256:
        raise Refused(['pin_log_digest_mismatch:%s' % path.name])
    return {'compressed_sha256': sha256(on_disk), 'compressed_bytes': len(on_disk),
            'uncompressed_sha256': digest, 'uncompressed_bytes': len(decompressed)}


def retain_pin_log(path: Path, raw: bytes, expected_sha256: str,
                   tokenize: Callable[[str], str]) -> dict:
    """Retain one suite's FULL stdout or stderr write-once at ``path``, next to the receipt
    (root: a red pin run could not be diagnosed because the tool kept only the stderr tail and
    a digest, and the traceback was discarded).  Retained whether or not the suite passed.
    Returns the run record's log entry: ``path`` (tokenized), the compressed sha256/bytes and
    the uncompressed sha256/bytes -- equal to ``expected_sha256``, the digest the tool already
    computed from the live run."""
    write_pin_log(path, raw)
    record = verify_pin_log(path, expected_sha256)
    record['path'] = tokenize(str(path))
    return record


def promote_pin_log(staged: Path, final: Path, expected_sha256: str,
                    tokenize: Callable[[str], str]) -> dict:
    """Move one suite's already-verified, staged log into its FINAL write-once location inside
    the tree, together with the receipt main() is about to write (``build_receipt``: only once
    the end-of-run tree check has passed and every other problem list is empty).  Re-derives
    the raw bytes from the staged gzip member -- never trusts its compressed bytes directly --
    and checks them against ``expected_sha256`` again before promoting.  Write-once at ``final``
    with the exact same convention as a fresh ``retain_pin_log``: identical bytes already there
    is a no-op, different bytes REFUSES (``pin_log_mismatch``) and leaves ``final`` untouched;
    the staged copy is left alone either way (the caller removes the whole staging root once
    every suite's logs have been promoted)."""
    raw = gzip.decompress(staged.read_bytes())
    if sha256(raw) != expected_sha256:
        raise Refused(['pin_log_digest_mismatch:%s' % staged.name])
    return retain_pin_log(final, raw, expected_sha256, tokenize)


def write_once(path: Path, obj: Mapping) -> str:
    data = (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'wb') as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    if Path(path).read_bytes() != data:
        raise Refused(['read_back'])
    return sha256(data)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    ap.add_argument('--repo', default=str(DEFAULT_REPO))
    ap.add_argument('--predecessor', default=PREDECESSOR)
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--no-suites', action='store_true')
    ap.add_argument('--runs-of-this-step', default=None)
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else repo / RESULTS_REL
    try:
        if args.no_suites and out_dir == (repo / RESULTS_REL).resolve():
            raise Refused(['no_suites_into_results'])
        if out_dir == (repo / RESULTS_REL).resolve() and \
                repo not in Path(__file__).resolve().parents:
            raise Refused(['tool_not_in_repo'])
        receipt = build_receipt(repo, args.predecessor, run_suites=not args.no_suites,
                                runs_of_this_step=(Path(args.runs_of_this_step)
                                                   if args.runs_of_this_step else None),
                                out_dir=out_dir)
        out = out_dir / ('HARNESS_PIN_SUCCESSOR_%s.json' % receipt['receipt_stamp'])
        if out.exists():
            raise Refused(['write_once:%s' % out.name])
        digest = write_once(out, receipt)
    except Refused as exc:
        print('REFUSED: %s' % ', '.join(exc.problems), file=sys.stderr)
        if exc.draft is not None:
            fd, path = tempfile.mkstemp(prefix='pinsucc_refused_', suffix='.json')
            draft = dict(exc.draft)
            draft.pop('REFUSED', None)
            staging = draft.pop('pin_logs_staging_dir', None)
            if staging and Path(staging).is_dir():
                # Never promoted into the tree (the run was refused) -- kept instead beside
                # this same refused draft, so a red run stays diagnosable from what main()
                # names here, not from a rerun for a favourable count.
                logs_dest = Path(path).with_name(Path(path).stem + '_pin_logs')
                shutil.move(staging, str(logs_dest))
                if isinstance(draft.get('solo_run_suites'), dict):
                    draft['solo_run_suites'] = dict(draft['solo_run_suites'],
                                                    pin_logs_dir=str(logs_dest))
                print('refused pin logs kept at: %s' % logs_dest, file=sys.stderr)
            with os.fdopen(fd, 'w') as fh:
                json.dump(dict(draft, REFUSED=exc.problems), fh, indent=1, sort_keys=True)
            print('refused draft (not a receipt): %s' % path, file=sys.stderr)
        return 2
    suites = receipt['solo_run_suites']
    print('%s sha256=%s harness %d->%d canonical %s->%s suites=%s' % (
        out, digest, receipt['harness_pin']['counts']['before'],
        receipt['harness_pin']['counts']['after'],
        receipt['harness_pin']['predecessor']['canonical_sha256'][:8],
        receipt['harness_pin']['successor']['canonical_sha256'][:8],
        suites if isinstance(suites, str) else 'all_passed=%s solo=%s solo_strict=%s' % (
            suites['all_passed'], suites['solo_evidence']['solo'],
            suites['solo_evidence']['solo_strict'])))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
