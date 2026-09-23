"""The ONE synchronized pre-outcome repair amendment (root 20:40, items 2 and 4).

Root, 2026-09-23 20:40 (reviews/prerun_bundle_go_nogo_20260923_2040.md):

    item 2 (line 17): "The four absent conformance prompts must be fixed in a
     synchronized pre-outcome config/protocol/architecture amendment before
     stage 1; use out-of-design prompts and no observed success outcome to
     choose them."
    item 4 (line 19): "choose a pre-outcome infrastructure cap of three
     supervised restarts per server per trial: if a fourth would be required,
     abort and report that trial incomplete, preserve every enrolled
     pair/attempt and its missingness, and make no deployment/harm decision
     from it. ... Record the cap as a pre-outcome protocol/config/harness
     amendment before any trial; no replacement trial, extra pair, alpha
     transfer or margin change."

The same amendment states, as prose, the fixed names of the session-60 repair
contract for items 1 and 3 (EB1 real server lifecycle: `server_start_failed`,
`trial_aborted(server_restart_cap)`, preflight code `golden_objects`; EB5
worker resolution: `worker_resolved`, `trial_aborted(unresolved_worker)`,
`episode_revealed.usage_complete` / `unknown_usage_calls`), so that one protocol
successor carries all of it. It changes no code: the schema and orchestrator
changes are other lanes' commits and move the harness pin there.

WHAT THIS DOES, AND ONLY THIS
  1. Preconditions, on BYTES, against the reviewed pre-images of main at
     b049307: config.json e4d42f5d (13,917 bytes), ARCHITECTURE_FINAL.md
     727003c1, protocol_FINAL.md 64ace6d3 (the patch-state successor, changing
     commit 48f4d70), cells.json 5c4a28f7 with five prior successors, rule block
     cbfd1792. No CR byte anywhere; the three-way verbatim contract holds;
     cells.json round-trips byte-exactly; every anchor occurs exactly once,
     begins a line and lies inside its section; no inserted text is present yet.
  2. The four conformance prompts: the selection rule (PROMPT_RULE, written
     before the texts, below) is checked MECHANICALLY against the three pinned
     roster sources, read from a local directory and verified against the
     config's byte counts and SHA-256 pins: distinct under
     lab_data.normalize_prompt from every source prompt and the six smoke
     tasks, token-set Jaccard below JACCARD_BELOW with each, entry point used by
     no source, the prompt parses to exactly one bare signature-plus-docstring
     function, and experiments/local_stream/agent.build_user_prompt accepts the
     record and takes its non-MBPP branch. Any failure refuses.
  3. Nineteen PURE insertions: two config line blocks, byte-identical in
     config.json, ARCHITECTURE 6.1 and protocol Appendix B (the prompts inside
     `prefreeze`; `server_supervision` at top level, outside the rule block);
     eight dated protocol paragraphs (2.4 item 6, 5.3, 5.8, 6.4, 12.2, 13.1,
     14.3, 14.6); five ARCHITECTURE insertions (4.4, 6.3, three in 7.1). No
     existing byte changes.
  4. Postconditions, computed BEFORE anything is written: each inserted text
     occurs exactly once; deleting them reproduces each pre-image byte for byte;
     each lies inside its section (lower AND upper bound, the section scanner of
     the hardened engineering-cap tool) directly beside its anchor, and each
     configuration insertion lies inside its ```json fence; the three-way
     contract holds; no CR; protocol sections 1, 3 and 11 byte-identical; the
     flattened config key diff is exactly three added keys; the rule-block
     digest is still cbfd1792; `engineering_acquisition` and every other
     pinned subtree are unchanged and `engineering_acquisition` still equals
     run_smoke.BOUND_LIMITS.
  5. A NEGATIVE CONTROL on scratch copies in a temporary directory: each of the
     seventeen document insertions moved out of its section (prose into the next
     section, configuration lines out of their fence) must be refused by the
     predicate of step 4. If the check cannot refuse, nothing is written.
  6. The protocol successor, ADDITIVELY in cells.json: the original pin
     untouched; the patch-state successor 64ace6d3 moves WHOLE into
     prior_successors with its changing commit 48f4d70 (verified with git show);
     the new successor names the amended protocol.
  7. One write-once receipt,
     results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_<UTC>.json.

EVERY REFUSAL GOES THROUGH gate(name, checks): one named predicate, True only if
each named check in it is True. That single aggregation point is what lets the
witnesses show that each named check refuses ON ITS OWN (review finding 5 of the
first run: many guards could be deleted with every test still green, because each
test was refused by an earlier or broader guard as well).

CORRECTION RUN (review of commit 1349619, 2026-09-23). The first run of this
tool, committed in 1349619 with the receipt
results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json, made protocol
25014221 and ARCHITECTURE 4e8546f2; review found that its prose stated a pending
reportability default as settled, called new automatic aborts "the rule already
fixed", confined `worker_resolved` to trial chains while requiring it for
pre-freeze stages, and over-claimed provenance (WITHDRAWN_FIRST_RUN below lists
each point). That receipt is committed and write-once: it is KEPT, unedited. This
version of the tool is re-run from the same b049307 pre-images (the four documents
checked out from b049307 on a clean tree) and writes a CORRECTION receipt that
names the first run and what it corrects. config.json comes out byte-identical to
the first run; the prose, the ARCHITECTURE and cells.json differ.

It refuses, changing nothing, if any precondition fails. It is NOT a freeze, NOT
trial, stage or launch approval; it runs no simulation, model, server, build or
network request. The prompts were AUTHORED by the implementing AI agent session,
itself a language model; neither served model (incumbent or candidate) was run and
no output of a served model was consulted.

MODELLED ON experiments/live_ab_tools/patch_state_amendment.py (itself modelled
on the hardened engineering_cap_amendment.py). The witness is
experiments/live_ab_tools/tests_repair_amendment.py (drives main() on scratch
copies of the b049307 blobs); the independent re-derivation is
experiments/live_ab_tools/verify_repair_amendment.py.

SCOPE: the pins are the values for THIS amendment. A reuse must re-point every
pin at its own reviewed pre-images. What carries over is the set of checks.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import importlib.util
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
LOCAL_STREAM = REPO / 'experiments' / 'local_stream'
SERVING = REPO / 'experiments' / 'live_ab_serving'
for _p in (str(LAB), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
import lab_data                                                # noqa: E402
# The reviewed section scanner (review finding config 1): a section runs from its
# heading to the next heading of the same or a higher level, fenced lines skipped.
from engineering_cap_amendment import block_of, fence_span, flatten, section_span  # noqa: E402

CONFIG = LAB / 'config.json'
ARCH = LAB / 'design' / 'ARCHITECTURE_FINAL.md'
PROTO = LAB / 'design' / 'protocol_FINAL.md'
CELLS = REPO / 'experiments' / 'live_ab_validation' / 'cells.json'
DEFAULT_SOURCES_DIR = REPO / 'work' / 'local_stream' / 'data'

#: the revision holding the reviewed pre-images (main before this amendment)
PRE_REV = 'b049307ff62153a054f61b6179291ba987de2ba1'
ORIGINAL_PIN = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
#: the protocol pre-image: the patch-state successor, as delivered in 48f4d70
PRIOR_SUCCESSOR = '64ace6d3e37732b372fd316055208e9deaab4d4e0722708563c8ebcc1579e82b'
PRIOR_SUCCESSOR_COMMIT = '48f4d70fbd580df282b551506448457a09ab514d'
PRIOR_SUCCESSOR_RECORDED = '19:33'
PRIOR_CONFIG_SHA256 = 'e4d42f5d442dde7e709222e0a4ad4985de0f20604061fec01f2e3ea95f75d824'
PRIOR_CONFIG_BYTES = 13917
PRIOR_ARCH_SHA256 = '727003c1efe2b210fff0cf7d0a60ca30f53948516171b863548849676b1242ab'
PRIOR_CELLS_SHA256 = '5c4a28f76a066d110205335b66c7df12a0c5d70045ad24fecace0ebec75e7784'
PRIOR_RULE_BLOCK = 'cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607'
PRIOR_PRIOR_SUCCESSORS = 5

#: the write-once receipt of THIS run (the first run's name,
#: REPAIR_AMENDMENT_RECEIPT_<UTC>.json, is taken by its committed receipt)
RECEIPT_PREFIX = 'REPAIR_AMENDMENT_CORRECTION_RECEIPT_'
#: The first run of this tool, withdrawn after review, and what this run corrects.
#: Its receipt was committed in 1349619 and is write-once, so it is kept unedited;
#: these values are recorded in the correction receipt ("corrects").
WITHDRAWN_FIRST_RUN = {
    'commit': '134961944cec6e83f2b27586cda3d1f42ba40b72',
    'branch': 'session60/repair-amend (not merged to main when withdrawn)',
    'receipt': 'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json',
    'receipt_sha256': '6729de69f66ed7cea7b6f8c8eb8370d9612ab4be7f094288ee5c2cc445715a19',
    'receipt_kept': ('committed, write-once: kept byte-unchanged; where it differs from this '
                     'receipt, this receipt supersedes it'),
    'config_sha256': 'c323e0f26e7cba68355083a104e6397097f446f5e4532eb23edea57952ebd850',
    'architecture_sha256': '4e8546f236cf0211b9d8bb9375e42cc410f8d084fbd7c72dcee3e9ec9955d156',
    'protocol_sha256': '25014221bbba4a4d67e8bde845d401318d7db6fc04375ec3f7d875532b754a0c',
    'cells_sha256': 'af4ed3b9620d29a058528cd6b8ec544c127af135972a7143a05748b566b3cf59',
    'how_this_run_was_made': ('the fixed tool re-run from the b049307 pre-images: config.json, '
                              'ARCHITECTURE_FINAL.md, protocol_FINAL.md and cells.json checked out '
                              'from b049307 on a clean tree, the first receipt left in place'),
    'corrections': [
        {'finding': 1, 'first_run': ('protocol 5.3 stated the reportability default of question '
                                     '(i) as settled ("that label replaces the rule of 6.4 ... and '
                                     'of 14.6") and 14.3 froze it as non-amendable'),
         'this_run': ('5.3 marks it provisional pending root\'s ruling, names it a change to a '
                      'rule for reporting decisions, and says no freeze may be made while it is '
                      'pending; 14.3 and ARCHITECTURE 6.3 admit it only in the form root\'s '
                      'ruling fixes; ARCHITECTURE row 21a says "provisionally"')},
        {'finding': 2, 'first_run': ('cells.json said the amendment "changes NO ... decision '
                                     'rule, stopping rule ... or other execution rule"; the '
                                     'receipt said the unchanged rule-block digest "shows '
                                     'mechanically" that no statistical-rule change happened'),
         'this_run': ('cells.json names the four new automatic aborts and the provisional '
                      'reportability change; the receipt and cells.json limit the rule-block '
                      'claim to "the rule-block keys are byte-unchanged" and say the digest '
                      'covers neither server_supervision nor any protocol text')},
        {'finding': 3, 'first_run': ('5.3 called the start consequences "the rule already fixed '
                                     'for the stage"; the new aborts were not in 6.4\'s automatic '
                                     'list, so 14.6 made them operator_discretion; the protocol '
                                     'did not say what smoke_transport / smoke_no_usage lead to'),
         'this_run': ('5.3 separates existing rules from new automatic aborts; a new 6.4 '
                      'paragraph lists the four new automatic aborts and their post-decision '
                      'treatment; 14.6 says they are not operator_discretion; 5.3 and '
                      'ARCHITECTURE 20a say a SERVER_SMOKE without a receipt is '
                      'receipt_mismatch')},
        {'finding': 4, 'first_run': ('12.2 made rows 28 and 29 trial-chain events while 14.6 '
                                     'required row 29 for pre-freeze stages, which write the '
                                     '_prefreeze chain'),
         'this_run': ('row 28 trial chain only; row 29 on a trial chain and, for a stage, on the '
                      '_prefreeze chain; never the program chain (12.2, 14.6, ARCHITECTURE T33); '
                      'a stage-3 load thread resolves through the lab_load ledger')},
        {'finding': 5, 'first_run': ('many acceptance guards could be deleted with every '
                                     'witness still passing'),
         'this_run': ('every refusal goes through gate(); the witnesses flip each named check '
                      'alone and pin the check names, and a LIVENESS table names a real-input '
                      'witness for each check or says why none exists')},
        {'finding': 6, 'first_run': ('the verifier took each insertion\'s expected section from '
                                     'the receipt; several of its checks had no negative control'),
         'this_run': ('verify_repair_amendment.py has its own key-to-heading map, a pinned check '
                      'list, a flip witness per check and negative controls for the pins, the '
                      'config diff, the rule block and the vocabulary sections')},
        {'finding': 7, 'first_run': ('"no model was run"; "a rule recorded before their texts" '
                                     '(evidenced only by a hard-coded constant); the commit '
                                     'message said plan v2r3 "refuses"'),
         'this_run': ('"neither served model was run"; the rule is stated ahead of the texts and '
                      'its prior timing is attested, not recorded; only the two launch records '
                      'refuse, plan v2r3\'s pin is stale and unenforced')},
    ],
}

ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'
#: the sections the vocabulary pin reads (cells.json sections_read [1, 3, 11])
VOCAB_MARKERS = {1: b'## 1. Purpose, scope', 3: b'## 3. Task roster',
                 11: b'## 11. The planning study'}
REVIEW = '`reviews/prerun_bundle_go_nogo_20260923_2040.md`'

# ---------------------------------------------------------------------------
# The configuration content (contract, "Fixed names (EB1)")
# ---------------------------------------------------------------------------
SERVER_SUPERVISION = {'max_supervised_restarts_per_server_per_trial': 3,
                      'on_exceeding': 'abort_trial_incomplete'}

# ---------------------------------------------------------------------------
# The four conformance prompts. THE RULE IS STATED FIRST, here and in the
# receipt. That it was fixed before the texts below were written is the
# implementing session's attestation, not a recorded fact: the rule and the texts
# entered the repository in the same file and the same commit (1349619). Nothing in
# the rule refers to any model output.
# ---------------------------------------------------------------------------
JACCARD_BELOW = 0.5
MAX_PROMPT_CHARS = 600
PROMPT_RULE = {
    'order': ('the rule is stated ahead of the texts in this tool and in its receipts; that it '
              'was fixed before the texts were written is the implementing session\'s '
              'attestation, NOT a recorded fact: the rule and the texts entered the repository '
              'in the same file and the same commit (1349619)'),
    'authorship': ('written by the implementing AI agent session (session 60 repair lane), '
                   'itself a language model, not by hand; neither served model (incumbent or '
                   'candidate) nor any other served model was run, and no output of any served '
                   'model was consulted'),
    'outcome_blindness': ('no success, conformance, latency, token or other observation of '
                          'any model on any prompt was used to write, choose or order them '
                          '(root 20:40 item 2; protocol 5.8 "Success outcomes of these runs '
                          'are never used for any design choice")'),
    'task_shape': ('a short, self-contained Python function task that needs only the '
                   'standard library (no import is required); one function; no tests, no '
                   'examples, no doctest, no reference solution (correctness is never '
                   'computed, protocol_FINAL.md 2.4 item 6)'),
    'fields': ('id (oodp/1..oodp/4), benchmark (out_of_design: any value other than "mbpp" '
               'selects the signature-and-docstring branch of '
               'experiments/local_stream/agent.py build_user_prompt, which reads only '
               'benchmark and prompt and needs no reference solution), entry_point, prompt '
               '(the signature line plus a docstring, nothing else). extract_code reads '
               'only the response text; the format-conformance rule of 2.4 item 6 needs a '
               'code block, not only the fallback of extract_code'),
    'length': ('prompt at most %d characters; the task is chosen so that a correct answer '
               'is one short function, far below max_tokens 1024. That bound is a design '
               'judgement: no answer was written or generated to measure it' % MAX_PROMPT_CHARS),
    'mechanical_distinctness': ('for every prompt of the three pinned roster sources '
                                '(mbpp_sanitized "prompt", mbpp_full "text", humaneval '
                                '"prompt", all records) and the six smoke tasks: '
                                'lab_data.normalize_prompt(candidate) != '
                                'normalize_prompt(source); and token-set Jaccard similarity '
                                'of the two normalized forms (split on spaces) strictly '
                                'below %.2f. The entry point is the name of no function '
                                'defined in any source record (mbpp code, humaneval prompt '
                                'and entry_point). Checked by this tool at run time; a '
                                'failure refuses the amendment' % JACCARD_BELOW),
    'threshold_fixed_before_checking': JACCARD_BELOW,
}

_P1 = ('def interleave_words(left: str, right: str) -> str:\n'
       '    """Return one sentence that alternates the words of two sentences.\n'
       '\n'
       '    Words are separated by single spaces, and an empty sentence has no words.\n'
       '    Take the first word of left, then the first word of right, then the second\n'
       '    word of left, and so on. When one sentence has no words left, append the\n'
       '    remaining words of the other in their original order. Join the result with\n'
       '    single spaces.\n'
       '    """\n')
_P2 = ('def covered_length(stretches: list) -> int:\n'
       '    """Return the total length of a ruler covered by the given stretches.\n'
       '\n'
       '    Each item of stretches is a pair (start, end) of integers with start <= end.\n'
       '    It covers the part of the ruler from start to end, a length of end - start.\n'
       '    Parts covered by more than one stretch are counted once. An empty list\n'
       '    covers a length of 0.\n'
       '    """\n')
_P3 = ('def most_named(ballots: list) -> str:\n'
       '    """Return the option named on the most ballots.\n'
       '\n'
       '    Each ballot is a non-empty string naming one option. When several options\n'
       '    share the highest count, return the one whose first ballot comes earliest\n'
       '    in the list. Return an empty string when there are no ballots.\n'
       '    """\n')
_P4 = ('def rotate_digits(text: str, k: int) -> str:\n'
       '    """Return text with every character from 0 to 9 replaced by a digit.\n'
       '\n'
       '    A digit d becomes the digit (d + k) % 10. All other characters are\n'
       '    unchanged. k is a non-negative integer.\n'
       '    """\n')
PROMPTS = (
    {'id': 'oodp/1', 'benchmark': 'out_of_design', 'entry_point': 'interleave_words',
     'prompt': _P1},
    {'id': 'oodp/2', 'benchmark': 'out_of_design', 'entry_point': 'covered_length',
     'prompt': _P2},
    {'id': 'oodp/3', 'benchmark': 'out_of_design', 'entry_point': 'most_named',
     'prompt': _P3},
    {'id': 'oodp/4', 'benchmark': 'out_of_design', 'entry_point': 'rotate_digits',
     'prompt': _P4},
)
PROMPT_KEYS = ('id', 'benchmark', 'entry_point', 'prompt')


def _prompts_block() -> str:
    """The `conformance_prompts` lines, inside `prefreeze` (keys indented 16)."""
    lines = ['                "conformance_prompts": [']
    for n, p in enumerate(PROMPTS):
        lines.append('                  {"id": %s, "benchmark": %s, "entry_point": %s,'
                     % (json.dumps(p['id']), json.dumps(p['benchmark']),
                        json.dumps(p['entry_point'])))
        lines.append('                   "prompt": %s}%s'
                     % (json.dumps(p['prompt']), '],' if n == len(PROMPTS) - 1 else ','))
    return ''.join(line + '\n' for line in lines)


CFG_PROMPTS_TEXT = _prompts_block()
CFG_SUPERVISION_TEXT = ('  "server_supervision": {"max_supervised_restarts_per_server_per_trial": 3, '
                        '"on_exceeding": "abort_trial_incomplete"},\n')
CFG_PROMPTS_ANCHOR = b'  "prefreeze": {"format_conformance_min": 9,\n'
CFG_SUPERVISION_ANCHOR = b'  "hardware_allowlist": ["arm64-darwin"],'
ADDED_CONFIG_KEYS = sorted(['prefreeze.conformance_prompts',
                            'server_supervision.max_supervised_restarts_per_server_per_trial',
                            'server_supervision.on_exceeding'])
#: subtrees that must be byte-for-byte (as parsed) unchanged
UNCHANGED_CONFIG_PATHS = ('engineering_acquisition', 'sampling', 'execution', 'servers',
                          'llama_args', 'llama_cpp', 'receipt', 'hardware_allowlist',
                          'environment_lock_sha256', 'pause_thresholds', 'monitor',
                          'plumbing_fail_conditions', 'integrity_label_rule', 'roster',
                          'sandbox', 'anchor', 'refreeze')


def _lines(*lines: str) -> str:
    return ''.join(line + '\n' for line in lines)


# ---------------------------------------------------------------------------
# The prose. Each is a pure insertion at one anchor, inside one section.
# ---------------------------------------------------------------------------
P_2_4 = _lines(
    '',
    '   *Amendment 2026-09-23 (pre-outcome; root %s item 2):* in the' % REVIEW,
    '   sentence above, "the prompts ... were developed on the incumbent\'s model family" applies to the **six smoke tasks',
    '   only**. The four out-of-design prompts of 5.8 (`prefreeze.conformance_prompts`) were written for this amendment by',
    '   the implementing AI agent session, without running either served model (incumbent or candidate) and without',
    '   consulting any output of a served model; they were developed on neither model family. Their selection rule is',
    '   stated ahead of the texts in the amendment tool and its receipts (5.8); that the rule was fixed before the texts',
    '   were written is the session\'s attestation, not a recorded fact. The extractor is unchanged.',
)
P_5_3 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1 and 4).*' % REVIEW,
    '**Restart cap.** At most **three** supervised restarts per server per trial: `server_supervision` =',
    '`{"max_supervised_restarts_per_server_per_trial": 3, "on_exceeding": "abort_trial_incomplete"}`, a top-level config',
    'key outside the rule block, non-amendable after the first outcome (14.3). Every supervised restart attempt counts,',
    'whether it succeeds (`server_restarted`) or fails (`server_start_failed` with `kind = restart`); the count is rebuilt',
    'from the chain on resume. If a fourth restart would be required, dispatch of new arrivals stops, every open attempt is',
    'drained (bounded; the `episode_hard_cap_s` kill still applies) and revealed, and the trial ends with',
    '`trial_aborted(server_restart_cap)`, a **new automatic abort** added by this amendment (6.4). Every enrolled pair,',
    'attempt and missingness record is retained. There is **no replacement trial, no extra pair, no alpha transfer and no',
    'margin change**. A crash may be arm-related, so a cap-aborted trial is **not a valid null**: it is reported as',
    'incomplete, and no deployment or harm decision is made from it after the abort. **Provisional, pending root\'s',
    'ruling** (question (i) of the session-60 repair contract): a `decision` logged before the abort stays in the chain,',
    'is labelled "not reportable: trial incomplete (restart cap)" and is not reported. For this abort reason only, that',
    'would replace the rule of 6.4 ("Aborts in the post-decision phase") and of 14.6 under which a logged decision stands;',
    'it is a change to a rule for reporting decisions, not a restatement of one. It is not final until root\'s ruling is',
    'recorded by a further pre-outcome amendment that confirms or replaces it, and no freeze may be made while it is',
    'pending. The cap was fixed without looking at any success or cost outcome.',
    '',
    '**Real start, and refusal instead of a placeholder.** Every first start and every supervised restart goes through',
    '`lab_server`: the GGUF bytes and hash and the serving manifest are re-verified, the frozen argv is launched, `/health`',
    'is awaited, the full `/props` object (with `model_path` tokenized) is compared with the tokenized golden object of the',
    'freeze bundle, and the `SERVER_SMOKE` response is compared with the golden `generation_settings` object under the',
    'mask of 13.2. A failure at any of these stages is recorded durably as `server_start_failed` (12.2 row 28) and is never',
    'replaced by a success-valued `server_started` or `server_restarted`: no comparison flag is written true unless the',
    'comparison was made, and no placeholder digest is written. Its consequence, by stage, under rules that existed before',
    'this amendment: a GGUF, serving-manifest or identity difference is 6.4 row 6 (`trial_aborted(server_identity)`); a',
    '`SERVER_SMOKE` receipt that differs from the golden object is a mismatch of 13.2 and ends the trial as',
    '`trial_aborted(receipt_mismatch)` before any further dispatch (6.4 row 12); a restart that does not come up within',
    '`server_recovery_s` is the `server_unrecoverable` pause of 14.6. Under **new automatic aborts** added by this',
    'amendment (6.4): a `SERVER_SMOKE` that yields no receipt at all - no HTTP 200 JSON object (`smoke_transport`), or a',
    'usage or timings key missing (`smoke_no_usage`) - also ends the trial as `trial_aborted(receipt_mismatch)` before any',
    'further dispatch; a first start that fails at launch or health dispatches nothing and ends the trial as',
    '`trial_aborted(infrastructure)`. Before seq 0, on every non-simulated path, the golden files are read, their digests',
    'are recomputed and compared with the config tables, and a null, missing, unreadable or mismatched golden file, or a',
    'runtime `golden` override, refuses the invocation with the preflight code `golden_objects`.',
)
P_5_8 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s item 2).* The four' % REVIEW,
    'out-of-design prompts are stored at `prefreeze.conformance_prompts` (ids `oodp/1` to `oodp/4`), byte-identically in',
    '`config.json`, ARCHITECTURE 6.1 and Appendix B. They are not hand-written: the implementing AI agent session wrote',
    'them. Their selection rule is stated ahead of the texts in the amendment tool',
    '(`experiments/live_ab_tools/repair_amendment.py`), in its first receipt',
    '(`results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json`) and in the correction receipt beside it; that the rule',
    'was fixed before the texts were written is the session\'s attestation, not a recorded fact, since the rule and the',
    'texts entered the repository in one commit. The rule: short, self-contained Python function tasks that need only the',
    'standard library, in the signature-and-docstring form that `build_user_prompt` sends on its non-MBPP branch, with no',
    'tests, no examples and no reference solution (correctness is never computed, 2.4 item 6); each mechanically distinct',
    'under `normalize_prompt` from every prompt of the three pinned sources and from the six smoke tasks, with token-set',
    'Jaccard similarity below 0.5 to each of them. **No observed outcome was used to choose them**: neither served model',
    '(incumbent or candidate) was run, and no success, conformance, latency or other output of any served model was',
    'consulted. They are not roster tasks and carry no task uid. With the six smoke tasks they are the ten prompts of the',
    'format-conformance rule of 2.4 item 6.',
)
P_6_4 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4).*' % REVIEW,
    '**New automatic, deterministic aborts.** This amendment adds four triggers that did not exist before it:',
    '`trial_aborted(server_restart_cap)` when a fourth supervised restart of a server would be required (5.3);',
    '`trial_aborted(unresolved_worker)` when a worker is not confirmed exited where `trial_ended` would otherwise be',
    'written (14.6); `trial_aborted(infrastructure)` when the first start of a server fails at launch or health (5.3), a',
    'second trigger of that reason beside the ten-failure rule; and `trial_aborted(receipt_mismatch)` when a',
    '`SERVER_SMOKE` yields no receipt at all (`smoke_transport`, `smoke_no_usage`; 5.3). Each is automatic, is reported',
    'under its own reason and is never `operator_discretion` (14.6). In the post-decision phase an `unresolved_worker` or',
    '`receipt_mismatch` abort is treated as the aborts listed under "Aborts in the post-decision phase" above (the',
    'follow-up cohort is truncated and the logged decision stands); a first-start abort cannot occur there, because it',
    'precedes every dispatch; for `server_restart_cap` the provisional rule of 5.3 applies, pending root\'s ruling.',
)
P_12_2 = _lines(
    '| 28 | `server_start_failed` | *(Amendment 2026-09-23, pre-outcome; root %s item 1)* server id; `kind` (`start`, `restart`); `stage` (`gguf`, `serving_manifest`, `launch`, `health`, `identity`, `smoke`); `findings` (closed codes); pid; return code or null; argv hash; `/props` hash or null; load seconds; `restart_index` (0 for the first start). Written instead of, never beside, a success-valued #3 or #6 for the same attempt | yes |' % REVIEW,
    '| 29 | `worker_resolved` | *(Amendment 2026-09-23, pre-outcome; same review, item 3)* arrival, attempt, pid, `state` (`exited`, `killed_reaped`, `liveness_unknown`, `alive_unresolved`), return code or null, spool bytes and spool SHA-256 at resolution | yes |',
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4), to rows' % REVIEW,
    '2, 14 and 27 and to P6.* `episode_revealed` (#14) also carries `usage_complete` and `unknown_usage_calls` (13.1); the',
    'reason of `trial_aborted` (#27) may also be `server_restart_cap` (5.3) or `unresolved_worker` (14.6), both automatic',
    'aborts of 6.4; the closed list of preflight check codes shared by `invocation_refused` (#2) and `preflight_refused`',
    '(P6) gains `golden_objects` (5.3). Row 28 is written on a trial chain only. Row 29 is written on a trial chain and,',
    'for a stage of 5.8, on the `_prefreeze` chain (14.6). Neither is written on the program chain. These additions are',
    'made before any freeze.',
)
P_13_1 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s item 3).* Every' % REVIEW,
    '`episode_revealed` also carries `usage_complete` (true only when every call of the attempt has a terminal response with',
    'known usage and the attempt\'s worker is resolved, 14.6) and `unknown_usage_calls` (the number of its calls without',
    'known usage). A call left without a terminal record when its worker is resolved or killed is **unfinished**: its',
    'delivery is unknown, its usage is `null`, never 0, and it is never counted as unsent. A total over attempts that',
    'include such a call is a lower bound and is labelled as one.',
)
P_14_3 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 2 and 4).* The config' % REVIEW,
    'key `server_supervision` (the restart cap of 5.3 and its consequence) and the four prompts at',
    '`prefreeze.conformance_prompts` (5.8) join this list: neither may be amended after the first outcome. The',
    'reportability sentence of 5.3 joins it only in the form in which root\'s ruling fixes it before the freeze (5.3).',
    '`server_supervision` lies outside the rule block, so it is bound by `config_sha256` and by the harness pin of',
    '`config.json`, not by `rule_block_sha256`: the rule-block digest does not cover it, and that digest being unchanged',
    'shows nothing about this key or about any protocol text.',
)
P_14_6 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4).*' % REVIEW,
    '**Every worker is resolved before a terminal acceptance.** Before `trial_ended` is written, and before any stage of 5.8',
    'marks itself completed, every worker process of the trial or stage is resolved - confirmed exited - and recorded by a',
    'durable `worker_resolved` event (12.2 row 29, on the trial chain or, for a stage, on the `_prefreeze` chain) with',
    '`state` `exited` or `killed_reaped`. A load thread of stage 3 is not a worker process: it is resolved when it has',
    'stopped and the durable ledger of `lab_load` holds a terminal line for every load intent it made. A worker whose exit',
    'cannot be confirmed (`liveness_unknown`, `alive_unresolved`) is unresolved: the trial ends as',
    '`trial_aborted(unresolved_worker)` instead of `trial_ended`, and a stage of 5.8 is recorded as incomplete. An abort or a',
    'pause for any other reason first drains (bounded; the `episode_hard_cap_s` kill still applies) and keeps its own reason;',
    'a worker still unresolved then is recorded with its state. The calls of an unresolved or killed worker that have no',
    'terminal record are unfinished, with `null` usage (13.1); none is counted as unsent or as 0, and no artifact such a call',
    'leaves is read as a completed response. This is truthful failure accounting: it does not prove that no request is sent',
    'after the terminal snapshot, and a phase accepted as successful must show every permitted worker resolved. The four',
    'automatic aborts that the amendment of 6.4 of this date adds - `trial_aborted(unresolved_worker)`,',
    '`trial_aborted(server_restart_cap)`, and the first-start `trial_aborted(infrastructure)` and the no-receipt',
    '`trial_aborted(receipt_mismatch)` of 5.3 - are automatic aborts of 6.4, so the rule above that',
    'every other abort is `operator_discretion` does not apply to them.',
)
A_4_4 = _lines(
    '| T32 | `server_start_failed` | D | *(Amendment 2026-09-23, pre-outcome; root %s item 1; protocol 5.3 and 12.2 row 28)* `server_id` enum; `kind` enum[`start`,`restart`]; `stage` enum[`gguf`,`serving_manifest`,`launch`,`health`,`identity`,`smoke`]; `findings` [enum] (closed codes: `IDENTITY_FINDINGS`, the receipt finding codes, `process_exited`, `health_timeout`, `smoke_transport`, `smoke_no_usage`, `serving_manifest`); `pid` int; `returncode` int?; `argv_sha256` hex64; `props_sha256` hex64?; `load_seconds` float; `restart_index` int (0 for the first start). Trial chain only. The record is carried by `lab_common.ServerStartFailed(LabError).record`; it is written instead of, never beside, a success-valued T4 or T8 |' % REVIEW,
    '| T33 | `worker_resolved` | D | *(Amendment 2026-09-23, pre-outcome; same review, item 3; protocol 14.6 and 12.2 row 29)* `arrival` int; `attempt` int; `pid` int; `state` enum[`exited`,`killed_reaped`,`liveness_unknown`,`alive_unresolved`]; `returncode` int?; `spool_bytes_at_resolution` int; `spool_sha256_at_resolution` hex64. Trial chain, and the `_prefreeze` chain for a stage of protocol 5.8; never the program chain |',
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4), to rows' % REVIEW,
    'T3, T17 and T31 and to P6.* T17 `episode_revealed` gains `usage_complete` bool and `unknown_usage_calls` int; the',
    '`reason` of T31 `trial_aborted` gains `server_restart_cap` and `unresolved_worker` (automatic aborts, protocol 6.4);',
    'the preflight check enum shared by T3 `invocation_refused` and P6 `preflight_refused` gains `golden_objects`. The pure',
    'function `phase_resolution_verdict(...)` is evaluated before `trial_ended` and before any pre-freeze stage marks',
    'itself completed; `lab_verify_log` mirrors it as the FAIL-level check `workers.resolved`, and checks T4, T7, T8 and',
    'T32 against protocol 5.3 as the FAIL-level check `server.lifecycle`.',
)
A_6_3 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 2 and 4; protocol' % REVIEW,
    '14.3):* this list gains `server_supervision` (top level, outside the rule block: bound by `config_sha256` and',
    '`harness_file_sha256[config.json]`, not by `rule_block_sha256`) and `prefreeze.conformance_prompts`; the',
    'reportability sentence of protocol 5.3 joins it only in the form in which root\'s ruling fixes it before the freeze.',
    '',
)
A_7_1_1B = _lines(
    '| 1b | `PREFLIGHT` | *(Amendment 2026-09-23, pre-outcome; root %s item 1)* on a non-simulated path: a golden file is null, missing, unreadable or does not match its config digest, or a runtime `golden` override is present | append `preflight_refused` with the check `golden_objects` to the **program** chain (D); no server is started and nothing success-valued is written | `ABORTED` | — |' % REVIEW,
)
A_7_1_20A = _lines(
    '| 20a | any | *(Amendment 2026-09-23; same review, item 1)* `lab_server.start` or `lab_server.restart` raises `ServerStartFailed` | `server_start_failed` (D) with the exception\'s record, never a success-valued T4 or T8; then the rule for its stage (protocol 5.3): `gguf`, `serving_manifest` or `identity` → `trial_aborted(server_identity)` (D); `smoke` → `trial_aborted(receipt_mismatch)` (D), both when the smoke receipt differs from the golden object and when none was obtained (`smoke_transport`, `smoke_no_usage`; the latter is a new automatic abort, protocol 6.4); `launch` or `health` on a restart → `trial_paused(server_unrecoverable)` (D), on the first start → `trial_aborted(infrastructure)` (D; a new automatic abort, protocol 6.4) | `ABORTED` / `PAUSED` | — |',
)
A_7_1_21AB = _lines(
    '| 21a | any | *(Amendment 2026-09-23; same review, item 4)* `server_down` on a server that already had `server_supervision.max_supervised_restarts_per_server_per_trial` (3) supervised restart attempts in this trial, counted from the chain | stop dispatching new arrivals; drain every open attempt (bounded; the `episode_hard_cap_s` kill still applies) and reveal each (D); `worker_resolved` per worker (D); `trial_aborted(server_restart_cap)` (D) + blocking anchor. No replacement trial, no extra pair; a logged `decision` is kept in the chain and, provisionally pending root\'s ruling, labelled not reportable (protocol 5.3) | `ABORTED` | **yes** |',
    '| 21b | `CLOSING`, or a pre-freeze stage about to complete | *(Amendment 2026-09-23; same review, item 3)* `phase_resolution_verdict` finds a worker that is not confirmed exited (`worker_resolved.state` in {`liveness_unknown`,`alive_unresolved`}) | no `trial_ended` and no stage completion: `trial_aborted(unresolved_worker)` (D) + blocking anchor, or the stage recorded incomplete; that worker\'s calls without a terminal record are unfinished, usage `null` | `ABORTED` | **yes** |',
)


class Insertion:
    """One pure insertion: ``text`` goes directly ``side`` ('after' / 'before') the
    unique ``anchor`` of document ``doc``, inside the section headed ``section``
    (whose upper bound must be the heading ``section_end``); ``fence`` means it must
    also lie inside that section's ```json fence."""

    def __init__(self, key, doc, anchor, side, text, section=None, section_end=None,
                 fence=False):
        self.key, self.doc, self.anchor, self.side = key, doc, anchor, side
        self.text = text.encode('utf-8') if isinstance(text, str) else text
        self.section, self.section_end, self.fence = section, section_end, fence

    def describe(self) -> dict:
        return {'key': self.key, 'document': self.doc, 'side': self.side,
                'anchor': self.anchor.decode('utf-8'),
                'section': self.section.decode('utf-8') if self.section else None,
                'section_upper_bound': (self.section_end.decode('utf-8')
                                        if self.section_end else None),
                'inside_json_fence': self.fence, 'bytes': len(self.text),
                'sha256': sha(self.text), 'text': self.text.decode('utf-8')}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_APPB = (b'## Appendix B.', b'## Appendix C.')
_A61 = (ARCH_MARKER, b'### 6.2 The rule block')

INSERTIONS = (
    # the configuration block, byte-identical in the three documents
    Insertion('config.prompts', 'config', CFG_PROMPTS_ANCHOR, 'after', CFG_PROMPTS_TEXT),
    Insertion('config.server_supervision', 'config', CFG_SUPERVISION_ANCHOR, 'before',
              CFG_SUPERVISION_TEXT),
    Insertion('architecture.6_1.prompts', 'architecture', CFG_PROMPTS_ANCHOR, 'after',
              CFG_PROMPTS_TEXT, *_A61, fence=True),
    Insertion('architecture.6_1.server_supervision', 'architecture', CFG_SUPERVISION_ANCHOR,
              'before', CFG_SUPERVISION_TEXT, *_A61, fence=True),
    Insertion('protocol.appendix_b.prompts', 'protocol', CFG_PROMPTS_ANCHOR, 'after',
              CFG_PROMPTS_TEXT, *_APPB, fence=True),
    Insertion('protocol.appendix_b.server_supervision', 'protocol', CFG_SUPERVISION_ANCHOR,
              'before', CFG_SUPERVISION_TEXT, *_APPB, fence=True),
    # protocol prose
    Insertion('protocol.2_4_item_6', 'protocol',
              b"   neither computed nor looked at. The prompts and the extractor were developed on "
              b"the incumbent's model family and are\n   not changed.\n", 'after', P_2_4,
              b'### 2.4 T3 candidate: selection criteria and preflight rules', b'### 2.5 Arms'),
    Insertion('protocol.5_3', 'protocol',
              b'enters the reconciliation identity of 13.1. `/metrics` scrape points: 13.1.\n',
              'after', P_5_3, b'### 5.3 Server supervision', b'### 5.4 Sampling parameters'),
    Insertion('protocol.5_8', 'protocol',
              b'quantities used are durations, memory, receipt equality, template facts and the '
              b'yes/no extractability of a code block.\n', 'after', P_5_8,
              b'### 5.8 Pre-freeze out-of-design phase', b'## 6. Outcomes, the hierarchy'),
    Insertion('protocol.6_4', 'protocol',
              b'one**; every abort is reported with the band endpoints at the abort (14.6).\n',
              'after', P_6_4, b'### 6.4 Failure-to-outcome table: every mode, one outcome',
              b'## 7. Pairing, the filtration'),
    Insertion('protocol.12_2', 'protocol',
              b'| 27 | `invocation_ended`, `trial_ended` / `trial_aborted` | status and reason; '
              b'exposure ledger by phase and arm; reconciliation totals; terminal failures by arm; '
              b'longest span without a receipt; `what_was_known`; final head | yes + blocking '
              b'anchor |\n', 'after', P_12_2, b'### 12.2 Event schema', b'### 12.3 The hash rule'),
    Insertion('protocol.13_1', 'protocol',
              b'uses**. **Tokens are never converted into money, energy or "compute"**; prompt '
              b'tokens stay visible.\n', 'after', P_13_1,
              b'### 13.1 Usage accounting for every try',
              b'### 13.2 The sampler receipt and the golden objects'),
    Insertion('protocol.14_3', 'protocol',
              b'| **reporting thresholds (N16)** | ', 'after-line', P_14_3,
              b'### 14.3 Immutability, and the two classes of code',
              b'### 14.4 The harness-only re-freeze'),
    Insertion('protocol.14_6', 'protocol',
              b'abort. **An aborted trial is reported, never restarted**; no decision other than '
              b'one already logged is claimed.\n', 'after', P_14_6,
              b'### 14.6 Trial order, unconditional execution, inspection between trials, pauses '
              b'and aborts', b'### 14.7 The operator is an AI agent session'),
    # ARCHITECTURE prose
    Insertion('architecture.4_4', 'architecture', b'| T31 | `trial_ended` / `trial_aborted` | ',
              'after-line', A_4_4, b'### 4.4 Trial chain', b'### 4.5 `what_was_known`'),
    Insertion('architecture.6_3', 'architecture',
              b'code** (`refreeze.scope == ["reporting_code"]`), never a config key.\n', 'after',
              A_6_3, b'### 6.3 Keys that may never be amended after the first design outcome',
              b'## 7. Orchestrator state machine'),
    Insertion('architecture.7_1.row_1b', 'architecture', b'| 1a | `PREFLIGHT` | ', 'after-line',
              A_7_1_1B, b'### 7.1 States and transitions', b'### 7.2 What is fsynced, and when'),
    Insertion('architecture.7_1.row_20a', 'architecture', b'| 20 | any | ', 'after-line',
              A_7_1_20A, b'### 7.1 States and transitions', b'### 7.2 What is fsynced, and when'),
    Insertion('architecture.7_1.rows_21a_21b', 'architecture', b'| 21 | any | ', 'after-line',
              A_7_1_21AB, b'### 7.1 States and transitions', b'### 7.2 What is fsynced, and when'),
)
DOC_NAMES = ('config', 'architecture', 'protocol')


def git(*args) -> str:
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


# ---------------------------------------------------------------------------
# Anchors and insertion
# ---------------------------------------------------------------------------
def anchor_offset(raw: bytes, ins: Insertion) -> int:
    """Where ``ins.text`` goes in ``raw``. The anchor must occur exactly once and begin
    a line. 'after' = directly after the anchor (which ends with a newline);
    'after-line' = directly after the whole line the anchor begins; 'before' =
    directly before the anchor. ValueError otherwise."""
    n = raw.count(ins.anchor)
    if n != 1:
        raise ValueError('%s: the anchor occurs %d times' % (ins.key, n))
    i = raw.index(ins.anchor)
    if i and raw[i - 1:i] != b'\n':
        raise ValueError('%s: the anchor does not begin a line' % ins.key)
    if ins.side == 'before':
        return i
    if ins.side == 'after':
        if not ins.anchor.endswith(b'\n'):
            raise ValueError('%s: an "after" anchor must be a whole line' % ins.key)
        return i + len(ins.anchor)
    if ins.side == 'after-line':
        nl = raw.find(b'\n', i)
        if nl < 0:
            raise ValueError('%s: the anchor line does not end' % ins.key)
        return nl + 1
    raise ValueError(ins.side)


def anchor_facts(raw: bytes, ins: Insertion) -> dict:
    """The precondition on one anchor in the PRE-image ``raw``: exactly once, at a
    line start, inside its section (and, for configuration lines, inside the
    section's ```json fence); and the text is not there yet."""
    try:
        off = anchor_offset(raw, ins)
        row = {'anchor_occurrences': 1, 'offset': off}
        if ins.section is not None:
            s0, s1 = section_span(raw, ins.section)
            row['inside_its_section'] = (raw.count(ins.section) == 1 and s0 < off <= s1
                                         and raw[s1:s1 + len(ins.section_end)]
                                         == ins.section_end)
            if ins.fence:
                f0, f1 = fence_span(raw, ins.section)
                row['inside_the_json_fence'] = s0 < f0 <= off <= f1 <= s1
                row['inside_its_section'] = (row['inside_its_section']
                                             and row['inside_the_json_fence'])
    except ValueError as e:
        row = {'anchor_occurrences': raw.count(ins.anchor), 'error': str(e),
               'inside_its_section': False}
    row['text_already_present'] = raw.count(ins.text)
    return row


def insert_all(old: dict) -> dict:
    """Every insertion, as bytes, at offsets computed in the PRE-image. Raises
    ValueError if an anchor is absent, duplicated or not at a line start."""
    out = {}
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
    for ins in INSERTIONS:
        if ins.doc == doc:
            new_raw = new_raw.replace(ins.text, b'', 1)
    return new_raw


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def gate(name: str, checks: dict) -> bool:
    """THE aggregation point of every acceptance predicate: ``name`` passes only if
    ``checks`` is non-empty and each named check in it is exactly True.

    Every refusal of main() on a computed condition goes through a call of this
    function, with the checks named, and each ``checks`` dict is recorded where the
    refusal prints it. That is what makes each check independently witnessable: the
    witness module (tests_repair_amendment.GateTests) wraps this function to set ONE
    named check False on the pristine pre-images, on which every other check is True,
    and requires main() to refuse and write nothing. Which REAL input makes each check
    False is a separate property, witnessed test by test and listed, check by check,
    in the witness module's LIVENESS table (some checks are implied by others and have
    no input that makes them alone False; the table says so)."""
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
    """Where ``ins.text`` landed in ``new_raw``: once; inside its section with a
    lower AND an upper bound; directly beside its anchor; for a configuration
    insertion, inside the section's ```json fence."""
    i = new_raw.find(ins.text)
    j = i + len(ins.text)
    out = {'occurrences': new_raw.count(ins.text), 'insert_at': i}
    if ins.side == 'before':
        out['directly_beside_the_anchor'] = i >= 0 and new_raw[j:j + len(ins.anchor)] == ins.anchor
    elif ins.side == 'after':
        out['directly_beside_the_anchor'] = i >= 0 and new_raw[i - len(ins.anchor):i] == ins.anchor
    else:                                                      # after-line
        k = new_raw.rfind(b'\n', 0, max(i - 1, 0)) + 1
        out['directly_beside_the_anchor'] = (i > 0 and new_raw[i - 1:i] == b'\n'
                                             and new_raw[k:k + len(ins.anchor)] == ins.anchor)
    if ins.section is None:
        out['inside_its_section'] = i >= 0
        return out
    try:
        s0, s1 = section_span(new_raw, ins.section)
    except ValueError as e:
        out.update(error=str(e), inside_its_section=False)
        return out
    ends = new_raw[s1:s1 + len(ins.section_end)] == ins.section_end
    inside = (i >= 0 and new_raw.count(ins.section) == 1 and ends and s0 < i and j <= s1)
    out.update({'section': [s0, s1], 'section_ends_at_its_upper_bound': ends})
    if ins.fence:
        try:
            f0, f1 = fence_span(new_raw, ins.section)
        except ValueError:
            f0, f1 = -1, -1
        out['fence'] = [f0, f1]
        out['inside_the_json_fence'] = (i >= 0 and s0 < f0 and f1 <= s1 and f0 <= i and j <= f1)
        inside = inside and out['inside_the_json_fence']
    out['inside_its_section'] = inside
    return out


def config_checks(old_cfg_raw: bytes, new_cfg_raw: bytes) -> dict:
    try:
        old_cfg, new_cfg = json.loads(old_cfg_raw), json.loads(new_cfg_raw)
    except ValueError as e:
        return {'error': str(e), 'ok': False}
    fo, fn = flatten(old_cfg), flatten(new_cfg)
    added = sorted(set(fn) - set(fo))
    removed = sorted(set(fo) - set(fn))
    changed = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
    unchanged = {p: old_cfg.get(p) == new_cfg.get(p) for p in UNCHANGED_CONFIG_PATHS}
    prompts = new_cfg.get('prefreeze', {}).get('conformance_prompts')
    bound = bound_limits()
    ea = new_cfg.get('engineering_acquisition')
    ea_equals = (isinstance(ea, dict) and bound is not None and set(ea) == set(bound)
                 and all(not isinstance(ea[k], bool) and float(ea[k]) == float(bound[k])
                         for k in bound))
    out = {
        'added_keys': added, 'removed_keys': removed, 'changed_keys': changed,
        'exactly_the_three_keys_added': added == ADDED_CONFIG_KEYS,
        'server_supervision_is_the_contract_value': new_cfg.get('server_supervision')
        == SERVER_SUPERVISION,
        'server_supervision_is_top_level': 'server_supervision' in new_cfg,
        'conformance_prompts_equal_the_tool_texts': prompts == [dict(p) for p in PROMPTS],
        'subtrees_unchanged': unchanged,
        'engineering_acquisition_equals_run_smoke_BOUND_LIMITS': ea_equals,
        'rule_block_sha256_before': lab_common.rule_block_sha256(old_cfg),
        'rule_block_sha256_after': lab_common.rule_block_sha256(new_cfg),
        'deleting_the_insertions_reproduces_the_prior_config': (
            sha(remove_all(new_cfg_raw, 'config')) == PRIOR_CONFIG_SHA256),
    }
    out['gate'] = {
        'exactly_the_three_keys_added': bool(out['exactly_the_three_keys_added']),
        'no_key_removed': not removed,
        'no_key_changed': not changed,
        'server_supervision_is_the_contract_value':
            bool(out['server_supervision_is_the_contract_value']),
        'conformance_prompts_equal_the_tool_texts':
            bool(out['conformance_prompts_equal_the_tool_texts']),
        'pinned_subtrees_unchanged': all(unchanged.values()),
        'engineering_acquisition_equals_run_smoke_BOUND_LIMITS': bool(ea_equals),
        'rule_block_before_is_the_pin': out['rule_block_sha256_before'] == PRIOR_RULE_BLOCK,
        'rule_block_after_is_the_pin': out['rule_block_sha256_after'] == PRIOR_RULE_BLOCK,
        'deleting_the_insertions_reproduces_the_prior_config':
            bool(out['deleting_the_insertions_reproduces_the_prior_config']),
    }
    out['ok'] = gate('config', out['gate'])
    return out


_BOUND = []


def bound_limits():
    """run_smoke.BOUND_LIMITS, the limits the acquisition supervisor enforces (loaded
    once from the real file; it defines constants only at import). None if it cannot
    be loaded, which fails the check."""
    if not _BOUND:
        try:
            spec = importlib.util.spec_from_file_location('run_smoke_for_repair_amendment',
                                                          SERVING / 'run_smoke.py')
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _BOUND.append(dict(mod.BOUND_LIMITS))
        except Exception:                                      # noqa: BLE001
            return None
    return dict(_BOUND[0])


def postconditions(old: dict, new: dict) -> tuple:
    """(post, ok) for candidate documents ``new`` against the pre-images ``old``
    ({'config', 'architecture', 'protocol'} -> bytes). The acceptance predicate
    main() applies before writing, and the one the negative control must fail."""
    where = {ins.key: placement(new[ins.doc], ins) for ins in INSERTIONS}
    additive = {d: (all(new[d].count(ins.text) == 1 for ins in INSERTIONS if ins.doc == d)
                    and remove_all(new[d], d) == old[d]) for d in DOC_NAMES}
    try:
        vo, vn = vocab_sections(old['protocol']), vocab_sections(new['protocol'])
        vocab = {str(n): vo[n] == vn[n] for n in VOCAB_MARKERS}
    except ValueError as e:
        vocab = {'error': str(e)}
    after = contract(new['config'], new['architecture'], new['protocol'])
    cfg = config_checks(old['config'], new['config'])
    post = {
        'config_sha256': sha(new['config']), 'config_bytes': len(new['config']),
        'architecture_sha256': sha(new['architecture']),
        'protocol_sha256': sha(new['protocol']), 'protocol_bytes': len(new['protocol']),
        'deleting_the_inserted_text_reproduces_each_preimage': additive,
        'insertion_placement': where,
        'every_insertion_inside_its_section_beside_its_anchor': {
            k: bool(v.get('occurrences') == 1 and v.get('inside_its_section')
                    and v.get('directly_beside_the_anchor')) for k, v in where.items()},
        'cr_bytes_after': {d: new[d].count(b'\r') for d in DOC_NAMES},
        'three_way_contract_after': after,
        'vocabulary_sections_1_3_11_byte_identical': vocab,
        'config': cfg,
    }
    post['gate'] = {
        'deleting_the_inserted_text_reproduces_each_preimage': all(additive.values()),
        'every_insertion_inside_its_section_beside_its_anchor':
            all(post['every_insertion_inside_its_section_beside_its_anchor'].values()),
        'no_cr_byte_after': not any(post['cr_bytes_after'].values()),
        'three_way_contract_after': after['holds'] is True,
        'vocabulary_sections_1_3_11_byte_identical':
            'error' not in vocab and all(v is True for v in vocab.values()),
        'config': cfg['ok'] is True,
        'every_document_changed': all(new[d] != old[d] for d in DOC_NAMES),
    }
    ok = gate('postconditions', post['gate'])
    return post, ok


def move_out(new: dict, ins: Insertion) -> dict:
    """The negative control: ``ins.text`` taken out of its place and put just outside
    its bound -- prose at the start of the next section's body, configuration lines
    just after their fence's closing line (still in the section, not in the fence)."""
    raw = new[ins.doc]
    base = raw.replace(ins.text, b'', 1)
    if ins.fence:
        _, f1 = fence_span(base, ins.section)
        k = base.index(b'\n', f1) + 1
    else:
        h = base.index(ins.section_end)
        k = base.index(b'\n', h) + 1
    out = dict(new)
    out[ins.doc] = base[:k] + ins.text + base[k:]
    return out


def negative_control(old: dict, new: dict) -> dict:
    """Scratch copies in a fresh temporary directory, never the real files: the
    pre-images and one moved variant per document insertion are written there, read
    back, and the acceptance predicate is applied. Each variant must be refused."""
    real = {p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    tmp = Path(tempfile.mkdtemp(prefix='repair_amendment_negative_control_'))
    out = {'how': ('postconditions() -- the predicate main() applies before writing -- on '
                   'scratch copies in a temporary directory, removed afterwards; one variant '
                   'per insertion into ARCHITECTURE or the protocol, moved just outside its '
                   'bound (config.json has no section to leave)'),
           'variants': {}}
    names = {'config': 'config.json', 'architecture': 'ARCHITECTURE_FINAL.md',
             'protocol': 'protocol_FINAL.md'}
    try:
        for k, name in names.items():
            (tmp / name).write_bytes(old[k])
        scratch = {k: (tmp / name).read_bytes() for k, name in names.items()}
        for ins in INSERTIONS:
            if ins.section is None:
                continue
            p = tmp / ('%s.moved.%s' % (names[ins.doc], ins.key))
            p.write_bytes(move_out(new, ins)[ins.doc])
            variant = dict(new)
            variant[ins.doc] = p.read_bytes()
            post, ok = postconditions(scratch, variant)
            pl = post['insertion_placement'][ins.key]
            out['variants'][ins.key] = {
                'sha256': sha(variant[ins.doc]),
                'deleting_the_inserted_text_reproduces_the_preimage':
                    post['deleting_the_inserted_text_reproduces_each_preimage'][ins.doc],
                'inside_its_section': pl.get('inside_its_section'),
                'accepted': ok, 'refused': not ok}
        out['scratch_copies_unchanged'] = all(
            (tmp / name).read_bytes() == old[k] for k, name in names.items())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out['real_documents_unchanged'] = real == {
        p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    out['variants_run'] = len(out['variants'])
    out['every_variant_refused_on_placement'] = bool(out['variants']) and all(
        v['refused'] and not v['inside_its_section'] for v in out['variants'].values())
    return out


def inserted_text_form() -> dict:
    """Every inserted text: ends with a newline, no CR, ASCII except the arrows and
    dashes the ARCHITECTURE table already uses, no trailing whitespace, no ``` (a
    fence would break the contract extraction); prose lines at most 120 characters
    (table rows and configuration lines excepted)."""
    out = {}
    for ins in INSERTIONS:
        t = ins.text.decode('utf-8')
        lines = t.split('\n')[:-1]
        prose = [l for l in lines if not l.startswith('|') and not ins.doc == 'config'
                 and not ins.fence]
        out[ins.key] = {
            'ends_with_a_newline': t.endswith('\n'),
            'cr_bytes': ins.text.count(b'\r'),
            'non_ascii': sorted(set(c for c in t if ord(c) > 127)),
            'no_trailing_whitespace': all(l == l.rstrip() for l in lines),
            'no_backtick_fence': '```' not in t,
            'max_prose_line_chars': max([len(l) for l in prose] or [0]),
            'contains_no_anchor': not any(o.anchor in ins.text for o in INSERTIONS),
        }
    ok = all(v['ends_with_a_newline'] and v['cr_bytes'] == 0 and v['no_trailing_whitespace']
             and v['no_backtick_fence'] and v['max_prose_line_chars'] <= 120
             and v['contains_no_anchor'] and set(v['non_ascii']) <= {'→', '—'}
             for v in out.values())
    return {'per_insertion': out, 'ok': ok}


# ---------------------------------------------------------------------------
# The conformance prompts, checked against the pinned sources
# ---------------------------------------------------------------------------
SOURCE_FILES = {'mbpp_sanitized': 'sanitized-mbpp.json', 'humaneval': 'HumanEval.jsonl.gz',
                'mbpp_full': 'mbpp.jsonl'}
SOURCE_RECORDS = {'mbpp_sanitized': 427, 'humaneval': 164, 'mbpp_full': 974}


def load_sources(sources_dir: Path, pins: dict) -> dict:
    """{name: records} from ``sources_dir``; each file must match the config's pin
    (roster.sources.<name>.bytes / .sha256) and its record count. Raises
    ValueError otherwise. Reads files only."""
    out, facts = {}, {}
    for name, fname in SOURCE_FILES.items():
        path = Path(sources_dir) / fname
        if not path.is_file():
            raise ValueError('pinned source %r (%s) not found' % (name, fname))
        data = path.read_bytes()
        pin = pins[name]
        if len(data) != pin['bytes'] or sha(data) != pin['sha256']:
            raise ValueError('pinned source %r: %d bytes sha256 %s, pinned %d bytes sha256 %s'
                             % (name, len(data), sha(data), pin['bytes'], pin['sha256']))
        if name == 'humaneval':
            recs = [json.loads(l) for l in gzip.decompress(data).decode('utf-8').splitlines()
                    if l.strip()]
        elif fname.endswith('.jsonl'):
            recs = [json.loads(l) for l in data.decode('utf-8').splitlines() if l.strip()]
        else:
            recs = json.loads(data.decode('utf-8'))
        if len(recs) != SOURCE_RECORDS[name]:
            raise ValueError('pinned source %r: %d records, expected %d'
                             % (name, len(recs), SOURCE_RECORDS[name]))
        out[name] = recs
        facts[name] = {'file': fname, 'bytes': len(data), 'sha256': sha(data),
                       'records': len(recs), 'matches_config_pin': True}
    return {'records': out, 'facts': facts}


_DEF = re.compile(r'^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(', re.M)


def source_prompts(records: dict) -> list:
    """[(uid, text, defined function names)] for every record of the three sources."""
    out = []
    for r in records['mbpp_sanitized']:
        out.append(('mbpp/%d' % int(r['task_id']), r['prompt'],
                    set(_DEF.findall(r.get('code') or ''))))
    for r in records['mbpp_full']:
        out.append(('mbpp_full/%d' % int(r['task_id']), r['text'],
                    set(_DEF.findall(r.get('code') or ''))))
    for r in records['humaneval']:
        idx = int(str(r['task_id']).split('/')[-1])
        out.append(('humaneval/%d' % idx, r['prompt'],
                    set(_DEF.findall(r['prompt'])) | {r['entry_point']}))
    return out


def jaccard(a: str, b: str) -> float:
    ta = set(lab_data.normalize_prompt(a).split())
    tb = set(lab_data.normalize_prompt(b).split())
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / len(ta | tb)


def build_user_prompt_fn():
    """experiments/local_stream/agent.py build_user_prompt, loaded from the file (its
    imports -- common, sandbox, verify, requests -- define functions only)."""
    if str(LOCAL_STREAM) not in sys.path:
        sys.path.insert(0, str(LOCAL_STREAM))
    spec = importlib.util.spec_from_file_location('agent_for_repair_amendment',
                                                  LOCAL_STREAM / 'agent.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_user_prompt


def prompt_shape(p: dict) -> dict:
    """Parses to exactly one function, named entry_point, whose body is its
    docstring only; no import, no decorator, no example, no assert."""
    try:
        tree = ast.parse(p['prompt'])
    except SyntaxError as e:
        return {'parses': False, 'error': str(e), 'ok': False}
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    body_is_docstring = (len(tree.body) == 1 and len(fns) == 1 and len(fns[0].body) == 1
                         and isinstance(fns[0].body[0], ast.Expr)
                         and isinstance(fns[0].body[0].value, ast.Constant)
                         and isinstance(fns[0].body[0].value.value, str))
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    out = {'parses': True,
           'one_function_named_entry_point': (len(fns) == 1
                                              and fns[0].name == p['entry_point']),
           'body_is_the_docstring_only': body_is_docstring,
           'no_import': not imports,
           'no_decorator': bool(fns) and not fns[0].decorator_list,
           'no_example_or_assert': ('>>>' not in p['prompt']
                                    and 'assert' not in p['prompt'].lower()),
           'chars': len(p['prompt']),
           'ascii_only': all(ord(c) < 128 for c in p['prompt'])}
    out['ok'] = (out['one_function_named_entry_point'] and body_is_docstring
                 and out['no_import'] and out['no_decorator'] and out['no_example_or_assert']
                 and out['chars'] <= MAX_PROMPT_CHARS and out['ascii_only'])
    return out


def check_prompts(sources: dict, smoke_uids: list, build=None) -> dict:
    """The mechanical half of PROMPT_RULE, for every prompt against every source."""
    build = build or build_user_prompt_fn()
    srcs = source_prompts(sources['records'])
    by_uid = {uid: text for uid, text, _ in srcs}
    defined = set().union(*(names for _, _, names in srcs)) if srcs else set()
    missing_smoke = [u for u in smoke_uids if u not in by_uid]
    per = []
    for p in PROMPTS:
        norm = lab_data.normalize_prompt(p['prompt'])
        sims = [(jaccard(p['prompt'], text), uid) for uid, text, _ in srcs]
        best, best_uid = max(sims) if sims else (0.0, None)
        smoke = [(jaccard(p['prompt'], by_uid[u]), u) for u in smoke_uids if u in by_uid]
        sbest, sbest_uid = max(smoke) if smoke else (0.0, None)
        equal = [uid for uid, text, _ in srcs if lab_data.normalize_prompt(text) == norm]
        try:
            msg = build(dict(p))
            route_ok = (p['benchmark'] != 'mbpp' and msg == (
                'Complete the following Python function.\n\n```python\n%s\n```' % p['prompt']))
        except Exception as e:                                 # noqa: BLE001
            msg, route_ok = 'ERROR %r' % e, False
        shape = prompt_shape(p)
        row = {'id': p['id'], 'entry_point': p['entry_point'],
               'prompt_sha256': sha(p['prompt'].encode('utf-8')),
               'user_message_sha256': sha(msg.encode('utf-8')),
               'build_user_prompt_takes_the_non_mbpp_branch': route_ok,
               'shape': shape,
               'normalized_equal_to': equal,
               'max_jaccard': round(best, 6), 'closest_source_uid': best_uid,
               'max_jaccard_smoke_tasks': round(sbest, 6), 'closest_smoke_task': sbest_uid,
               'sources_compared': len(srcs),
               'entry_point_defined_in_a_source': p['entry_point'] in defined}
        # The smoke-task bound is IMPLIED by the all-sources bound: the six smoke tasks
        # are source records (a missing one refuses via no_smoke_task_missing), so
        # sbest <= best. It is kept as a named check, witnessed at the gate only.
        row['gate'] = {
            'build_user_prompt_takes_the_non_mbpp_branch': route_ok is True,
            'shape_ok': shape['ok'] is True,
            'normalized_equal_to_no_source': not equal,
            'max_jaccard_below_threshold': best < JACCARD_BELOW,
            'max_jaccard_smoke_tasks_below_threshold': sbest < JACCARD_BELOW,
            'entry_point_defined_in_no_source': not row['entry_point_defined_in_a_source'],
            'sources_compared': len(srcs) > 0,
        }
        row['passes'] = gate('prompt', row['gate'])
        per.append(row)
    ids = [p['id'] for p in PROMPTS]
    distinct_among_themselves = (
        len({lab_data.normalize_prompt(p['prompt']) for p in PROMPTS}) == len(PROMPTS)
        and len({p['entry_point'] for p in PROMPTS}) == len(PROMPTS))
    out = {'per_prompt': per,
           'ids_are_oodp_1_to_4': ids == ['oodp/%d' % i for i in range(1, 5)],
           'fields_are_exactly': all(tuple(p) == PROMPT_KEYS for p in PROMPTS),
           'distinct_among_themselves': distinct_among_themselves,
           'smoke_tasks': list(smoke_uids), 'smoke_tasks_missing_from_sources': missing_smoke,
           'source_counts': {k: len(v) for k, v in sources['records'].items()},
           'source_facts': sources['facts']}
    out['gate'] = {'every_prompt_passes': all(r['passes'] for r in per),
                   'ids_are_oodp_1_to_4': out['ids_are_oodp_1_to_4'],
                   'distinct_among_themselves': distinct_among_themselves,
                   'no_smoke_task_missing': not missing_smoke,
                   'fields_are_exactly': out['fields_are_exactly']}
    out['all_pass'] = gate('prompts', out['gate'])
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sources-dir', default=str(DEFAULT_SOURCES_DIR),
                    help='directory holding sanitized-mbpp.json, HumanEval.jsonl.gz and '
                         'mbpp.jsonl, byte copies of the pinned roster sources')
    args = ap.parse_args(argv)
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / (RECEIPT_PREFIX + '%s.json' % stamp)
    if receipt_path.exists():
        print('refusing: %s exists (write-once)' % receipt_path, file=sys.stderr)
        return 2

    # -- 1. preconditions, on BYTES --------------------------------------------
    old = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
           'protocol': PROTO.read_bytes()}
    cells_raw = CELLS.read_bytes()
    try:
        cells = json.loads(cells_raw)
        va = cells['provenance']['vocabulary_alignment']
        sb = va.get('superseded_by', {})
    except (ValueError, KeyError, TypeError) as e:
        print('refusing: cells.json unreadable (%s); NOTHING was written' % e, file=sys.stderr)
        return 2
    before = contract(old['config'], old['architecture'], old['protocol'])
    anchors = {ins.key: anchor_facts(old[ins.doc], ins) for ins in INSERTIONS}
    form = inserted_text_form()
    pre = {
        'config_sha256': sha(old['config']), 'config_bytes': len(old['config']),
        'config_is_the_reviewed_preimage': (sha(old['config']) == PRIOR_CONFIG_SHA256
                                            and len(old['config']) == PRIOR_CONFIG_BYTES),
        'architecture_sha256': sha(old['architecture']),
        'architecture_is_the_reviewed_preimage': sha(old['architecture']) == PRIOR_ARCH_SHA256,
        'protocol_sha256': sha(old['protocol']),
        'protocol_is_the_reviewed_preimage': sha(old['protocol']) == PRIOR_SUCCESSOR,
        'cells_sha256': sha(cells_raw),
        'cells_is_the_reviewed_preimage': sha(cells_raw) == PRIOR_CELLS_SHA256,
        'cr_bytes': dict({k: v.count(b'\r') for k, v in old.items()},
                         cells=cells_raw.count(b'\r')),
        'three_way_contract_before': before,
        'rule_block_sha256_before': (lab_common.rule_block_sha256(json.loads(old['config']))
                                     if before.get('holds') else None),
        'cells_round_trips': ((json.dumps(cells, indent=1) + '\n').encode('utf-8')
                              == cells_raw),
        'cells_original_pin': va.get('sha256'),
        'cells_current_successor': sb.get('sha256'),
        'cells_prior_successors': len(sb.get('prior_successors', [])),
        'anchors': anchors,
        'inserted_text_form': form,
        'head': git('rev-parse', 'HEAD'),
    }
    # The pins first. Behind them, the one-shot guard: against documents that
    # already carry the insertions the pins refuse, and with every pin re-pointed
    # at such documents the "already present" refusal still stops the run.
    pre['gate_pins'] = {
        'config_is_the_reviewed_preimage': pre['config_is_the_reviewed_preimage'],
        'architecture_is_the_reviewed_preimage': pre['architecture_is_the_reviewed_preimage'],
        'protocol_is_the_reviewed_preimage': pre['protocol_is_the_reviewed_preimage'],
        'cells_is_the_reviewed_preimage': pre['cells_is_the_reviewed_preimage'],
        'no_cr_byte': not any(pre['cr_bytes'].values()),
        'three_way_contract_before': before['holds'] is True,
        'rule_block_before_is_the_pin': pre['rule_block_sha256_before'] == PRIOR_RULE_BLOCK,
        'cells_round_trips': pre['cells_round_trips'],
        'cells_original_pin_untouched': pre['cells_original_pin'] == ORIGINAL_PIN,
        'cells_current_successor_is_the_prior_successor':
            pre['cells_current_successor'] == PRIOR_SUCCESSOR,
        'cells_successor_supersedes_the_original': sb.get('supersedes') == ORIGINAL_PIN,
        'cells_prior_successor_count': pre['cells_prior_successors'] == PRIOR_PRIOR_SUCCESSORS,
    }
    if not gate('pins', pre['gate_pins']):
        print('refusing: a precondition failed; NOTHING was written: %s' % json.dumps(pre),
              file=sys.stderr)
        return 2
    if any(a['text_already_present'] for a in anchors.values()):
        print('refusing: the amendment is already present; NOTHING was written',
              file=sys.stderr)
        return 2
    pre['gate_anchors'] = {
        'every_anchor_once': all(a.get('anchor_occurrences') == 1 for a in anchors.values()),
        'no_anchor_error': all('error' not in a for a in anchors.values()),
        'every_anchor_inside_its_section': all(a.get('inside_its_section', True) is True
                                               for a in anchors.values()),
        'inserted_text_form': form['ok'] is True,
    }
    if not gate('anchors', pre['gate_anchors']):
        print('refusing: a precondition failed; NOTHING was written: %s' % json.dumps(pre),
              file=sys.stderr)
        return 2

    # -- 2. the four prompts, against the pinned sources -------------------------
    old_cfg = json.loads(old['config'])
    try:
        sources = load_sources(Path(args.sources_dir), old_cfg['roster']['sources'])
    except (ValueError, OSError, KeyError) as e:
        print('refusing: the pinned roster sources could not be read (%s); NOTHING was '
              'written' % e, file=sys.stderr)
        return 2
    prompt_check = check_prompts(sources, list(old_cfg['roster']['smoke_tasks']))
    if not prompt_check['all_pass']:
        print('refusing: a conformance prompt failed the stated rule; NOTHING was written: %s'
              % json.dumps(prompt_check), file=sys.stderr)
        return 2

    # -- 3. insert, as bytes -----------------------------------------------------
    try:
        new = insert_all(old)
    except ValueError as e:
        print('refusing: %s; NOTHING was written' % e, file=sys.stderr)
        return 2

    # -- 4. postconditions, computed BEFORE anything is written ------------------
    post, ok = postconditions(old, new)
    if not ok:
        print('refusing: a postcondition failed; NOTHING was written: %s'
              % json.dumps(post), file=sys.stderr)
        return 2

    # -- 5. the negative control: the check must be able to refuse ---------------
    control = negative_control(old, new)
    control['gate'] = {
        'every_variant_refused_on_placement': control['every_variant_refused_on_placement'],
        'scratch_copies_unchanged': control['scratch_copies_unchanged'] is True,
        'real_documents_unchanged': control['real_documents_unchanged'] is True,
    }
    if not gate('negative_control', control['gate']):
        print('refusing: the negative control did not refuse; NOTHING was written: %s'
              % json.dumps(control), file=sys.stderr)
        return 2

    # -- 6. the successor, additively --------------------------------------------
    verified_commit_hash = sha(subprocess.run(
        ['git', '-C', str(REPO), 'show',
         '%s:experiments/live_ab/design/protocol_FINAL.md' % PRIOR_SUCCESSOR_COMMIT],
        capture_output=True, check=True).stdout)
    commit_gate = {'prior_successor_commit_carries_the_prior_successor':
                   verified_commit_hash == PRIOR_SUCCESSOR}
    if not gate('successor_commit', commit_gate):
        print('refusing: %s does not carry the prior successor' % PRIOR_SUCCESSOR_COMMIT,
              file=sys.stderr)
        return 2
    old_sb = sb
    demoted = {k: v for k, v in old_sb.items()
               if k not in ('prior_successors', 'changing_commit_note',
                            'correction_to_the_owner_report')}
    demoted['changing_commit_of_this_successor'] = PRIOR_SUCCESSOR_COMMIT
    demoted['changing_commit_note'] = (
        'Resolved AFTER the fact, when the repair amendment landed on top of it: '
        '`git show %s:experiments/live_ab/design/protocol_FINAL.md` hashes to this '
        'successor.' % PRIOR_SUCCESSOR_COMMIT[:7])
    new_sb = {
        'sha256': post['protocol_sha256'],
        'supersedes': ORIGINAL_PIN,
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'reason': (
            'NOT Appendix-B-only: one synchronized pre-outcome amendment of config.json, '
            'ARCHITECTURE_FINAL.md and protocol_FINAL.md, every change a pure insertion '
            '(deleting the inserted text reproduces the prior successor 64ace6d3 byte for '
            'byte). Appendix B (byte-identical with config.json and ARCHITECTURE 6.1 under the '
            'three-way verbatim contract) gains two configuration insertions: the four '
            'out-of-design format-conformance prompts at prefreeze.conformance_prompts (ids '
            'oodp/1..oodp/4), and the top-level key server_supervision '
            '{"max_supervised_restarts_per_server_per_trial": 3, "on_exceeding": '
            '"abort_trial_incomplete"}, outside the rule block. Eight dated prose paragraphs '
            'are inserted: 2.4 item 6 (the "developed on the incumbent\'s model family" '
            'sentence applies to the six smoke tasks only), 5.3 (the restart cap and its '
            'consequence; the real server start and the refusal instead of a success-valued '
            'placeholder; server_start_failed; the golden_objects preflight refusal), 5.8 (where '
            'the four prompts are stored and the rule that chose them without any observed '
            'outcome), 6.4 (the new automatic aborts), 12.2 (event rows server_start_failed and '
            'worker_resolved and the chains they are written on; the new abort reasons '
            'server_restart_cap and unresolved_worker; the preflight code golden_objects; '
            'episode_revealed usage_complete and unknown_usage_calls), 13.1 (usage of unfinished '
            'calls is null, never 0 or unsent), 14.3 (server_supervision and the prompts are '
            'non-amendable after the first outcome) and 14.6 (every worker is resolved before '
            'trial_ended or any stage completion; the new aborts are not operator_discretion). '
            'It ADDS execution and failure-to-outcome rules: four new automatic aborts, '
            'trial_aborted(server_restart_cap), trial_aborted(unresolved_worker), '
            'trial_aborted(infrastructure) for a first start that fails at launch or health, and '
            'trial_aborted(receipt_mismatch) for a SERVER_SMOKE that yields no receipt. '
            'PROVISIONALLY, pending root\'s ruling on question (i) of the session-60 repair '
            'contract, it also changes a rule for reporting decisions: a decision logged before a '
            'server_restart_cap abort is labelled not reportable, where 6.4 and 14.6 keep a logged '
            'decision after other aborts; protocol 5.3 says no freeze may be made while that '
            'ruling is pending. It changes no CPU cell, parameter, seed, horizon, estimator, '
            'outcome definition, monitor or decision threshold, alpha, margin or sampling '
            'parameter, and none of the vocabulary sections 1, 3 and 11 this pin reads (verified '
            'byte-identical). The rule-block keys are byte-unchanged (digest cbfd1792); that '
            'digest covers neither server_supervision nor any protocol text, so it does not show '
            'the absence of the changes listed here. This successor replaces the protocol digest '
            'beginning 25014221, the first run of the same amendment (commit 1349619), withdrawn '
            'after review before merge; its receipt is kept and the correction is recorded in the '
            'REPAIR_AMENDMENT_CORRECTION_RECEIPT written with this successor.'),
        'ruling': (
            'Root decision 2026-09-23 20:40 (reviews/prerun_bundle_go_nogo_20260923_2040.md). '
            'Item 2 (line 17): "The four absent conformance prompts must be fixed in a '
            'synchronized pre-outcome config/protocol/architecture amendment before stage 1; '
            'use out-of-design prompts and no observed success outcome to choose them." Item 4 '
            '(line 19): "choose a pre-outcome infrastructure cap of three supervised restarts '
            'per server per trial ... Record the cap as a pre-outcome protocol/config/harness '
            'amendment before any trial; no replacement trial, extra pair, alpha transfer or '
            'margin change." Items 1 and 3 (lines 16 and 18) fix route (a) for the server '
            'lifecycle and the worker-resolution requirement, whose names the prose states. '
            'The pin amendment follows the standing root ruling of 2026-09-22 04:27 '
            '(reviews/protocol_pin_disposition_20260922_0422.md): "preserve the original pin; '
            'record an explicit post-freeze provenance amendment ... Do not replace the '
            'original sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial, stage or launch approval, not a CPU rerun, and not the '
            'code changes of items 1 and 3 (the orchestrator, server, event-schema and '
            'verifier changes are separate commits that move the harness pin). It certifies '
            'no server start, no worker resolution and no prompt outcome: neither served model '
            'was run. Not root\'s ruling on question (i): the reportability sentence of 5.3 is '
            'provisional. The four prompts were written by the implementing AI agent session '
            'under a selection rule stated ahead of the texts (that it preceded them in time is '
            'attested, not recorded); the mechanical checks are distinctness and similarity '
            'checks, not a proof that the tasks are unseen by any model.'),
        'correction_to_the_owner_report': old_sb['correction_to_the_owner_report'],
        'prior_successors': list(old_sb['prior_successors']) + [demoted],
        'changing_commit_note': (
            'The commit that introduces a successor cannot carry its own hash, so '
            '"changing_commit_of_this_successor" is resolved in a LATER commit. The last '
            'entry above records the one for the %s successor (the patch state), resolved '
            'when this amendment landed; this newest successor\'s own commit is recorded the '
            'same way when the next one lands.' % PRIOR_SUCCESSOR_RECORDED),
    }
    new_cells = json.loads(cells_raw)
    new_cells['provenance']['vocabulary_alignment']['superseded_by'] = new_sb
    a, b = json.loads(cells_raw), json.loads(json.dumps(new_cells))
    a['provenance']['vocabulary_alignment'].pop('superseded_by')
    b['provenance']['vocabulary_alignment'].pop('superseded_by')
    cells_gate = {'cells_unchanged_outside_superseded_by': a == b}
    if not gate('cells', cells_gate):
        print('refusing: cells.json would change outside superseded_by', file=sys.stderr)
        return 2
    new_cells_raw = (json.dumps(new_cells, indent=1) + '\n').encode('utf-8')

    # -- 7. write, as bytes, then the receipt ------------------------------------
    harness_before = lab_common.harness_file_hashes()
    intended = {CONFIG: new['config'], ARCH: new['architecture'], PROTO: new['protocol'],
                CELLS: new_cells_raw}
    for path, raw in intended.items():
        path.write_bytes(raw)
    harness_after = lab_common.harness_file_hashes()
    on_disk = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
               'protocol': PROTO.read_bytes()}
    written = {
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
        'harness_file_sha256_config_before': harness_before.get('config.json'),
        'harness_file_sha256_config_after': harness_after.get('config.json'),
        'config_equals_the_withdrawn_first_run': (
            sha(on_disk['config']) == WITHDRAWN_FIRST_RUN['config_sha256']),
    }
    doc = {
        'schema': 'live_ab.repair_amendment_receipt.2',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root, reviews/prerun_bundle_go_nogo_20260923_2040.md items 2 and 4 '
                      '(lines 17 and 19; quoted in this tool\'s docstring), with the fixed '
                      'names of items 1 and 3 from the session-60 repair contract'),
        'prepared_by': ('prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off'),
        'corrects': WITHDRAWN_FIRST_RUN,
        'documents_amended_in_lockstep': [str(p.relative_to(REPO)) for p in (CONFIG, ARCH, PROTO)],
        'insertions': [ins.describe() for ins in INSERTIONS],
        'conformance_prompts': {
            '1_selection_rule': PROMPT_RULE,
            '2_texts': [dict(p) for p in PROMPTS],
            '3_mechanical_check_results': prompt_check,
        },
        'server_supervision': {
            'value': SERVER_SUPERVISION,
            'placement': ('a NEW top-level key, outside the rule block (not under '
                          'execution.auto_abort or plumbing_fail_conditions, which '
                          'rule_block_sha256 hashes). The existing automatic abort '
                          'execution.auto_abort IS in the rule block; this cap is therefore '
                          'bound by config_sha256 and harness_file_sha256[config.json], not by '
                          'rule_block_sha256. Reason: root 20:40 item 4 forbids any alpha, '
                          'margin or statistical-rule change; the rule-block keys are '
                          'byte-unchanged (digest cbfd1792), the precedent being '
                          'engineering_acquisition (CONFIG_AMENDMENT_RECEIPT_20260923_1804.json). '
                          'That digest covers neither this key nor any protocol text, so it '
                          'shows nothing about the cap, the new automatic aborts or the '
                          'reportability sentence of protocol 5.3'),
            'what_counts': ('each supervised restart ATTEMPT per server per trial: a '
                            'server_restarted, or a server_start_failed with kind "restart"; '
                            'rebuilt from the chain on resume. The fourth required restart '
                            'aborts. This reading is stated in protocol 5.3 and ARCHITECTURE '
                            '7.1 row 21a; the orchestrator lane must count the same way'),
            'reportability': ('PROVISIONAL, pending root\'s answer to question (i) of the repair '
                              'contract: no deployment/harm decision is made from a cap-aborted '
                              'trial after the abort (root 20:40 item 4); a decision logged '
                              'BEFORE the abort stays in the chain labelled "not reportable: '
                              'trial incomplete (restart cap)" (the contract default). Protocol '
                              '5.3 states it as provisional, says it would change for this abort '
                              'reason the 6.4/14.6 rule under which a logged decision stands, and '
                              'says no freeze may be made while the ruling is pending'),
            'open_point_for_root': ('the default can withdraw a logged decision because of '
                                    'post-decision crashes, which may be arm-related: after a '
                                    'switch to deploy_candidate the follow-up cohort is '
                                    'single-arm on the candidate (protocol 1, "Traffic switch"), '
                                    'so candidate-server crashes alone can reach the cap; which '
                                    'decisions are reported can then depend on the arm'),
            'fixed_without_outcomes': 'no success or cost outcome exists; none was looked at',
        },
        'choices_stated_in_the_prose_for_the_code_lanes_to_match': [
            'NEW automatic aborts (protocol 6.4 amendment, 5.3, 14.6): '
            'trial_aborted(server_restart_cap); trial_aborted(unresolved_worker); a first start '
            'failing at stage launch or health ends the trial as trial_aborted(infrastructure); '
            'a SERVER_SMOKE that yields no receipt (smoke_transport, smoke_no_usage) ends it as '
            'trial_aborted(receipt_mismatch). None is operator_discretion (14.6 amendment)',
            'EXISTING rules applied at a start or restart: gguf/serving_manifest/identity -> '
            'server_identity (6.4 row 6); a SERVER_SMOKE receipt that differs from the golden '
            'object -> receipt_mismatch (13.2, 6.4 row 12); a restart that does not come up -> '
            'server_unrecoverable pause (14.6)',
            'in the post-decision phase an unresolved_worker or receipt_mismatch abort truncates '
            'the follow-up cohort only and the logged decision stands, as for the aborts of the '
            '6.4 post-decision paragraph; server_restart_cap follows the provisional rule of 5.3',
            'a failed supervised restart counts toward the cap (protocol 5.3)',
            'an abort or pause for another reason drains first and keeps its reason; '
            'unresolved_worker is used only where trial_ended or a stage completion would '
            'otherwise be written (protocol 14.6; ARCHITECTURE 7.1 row 21b)',
            'server_start_failed is written on a trial chain only; worker_resolved on a trial '
            'chain and, for a pre-freeze stage, on the _prefreeze chain; neither on the program '
            'chain (protocol 12.2, 14.6; ARCHITECTURE T32, T33); a stage-3 load thread is '
            'resolved through the lab_load ledger (protocol 14.6)',
            'usage_complete is true only when every call has known usage and the worker is '
            'resolved (protocol 13.1)',
        ],
        'event_list_placement': ('the task named "section 13 event list"; protocol section 13 '
                                 'has no event list, so the events are added to the event '
                                 'table of 12.2 (rows 28, 29 and a paragraph for rows 2, 14, 27 '
                                 'and P6), and 13.1 states the usage fields'),
        'precondition_checked': pre,
        'postcondition_checked': post,
        'negative_control': control,
        'written': written,
        'successor_provenance': {
            'original_pin_untouched': ORIGINAL_PIN,
            'new_successor': post['protocol_sha256'],
            'demoted_successor': PRIOR_SUCCESSOR,
            'demoted_successor_commit_verified': PRIOR_SUCCESSOR_COMMIT,
            'gate_successor_commit': commit_gate,
            'gate_cells': cells_gate,
            'prior_successors_now': len(new_sb['prior_successors']),
            'withdrawn_first_run_not_in_the_history': (
                'the first run\'s successor (%s) was never demoted into prior_successors: this '
                'run starts again from the b049307 cells.json, so the history reads 64ace6d3 -> '
                'this successor; the first run is recorded under "corrects"'
                % WITHDRAWN_FIRST_RUN['protocol_sha256'][:8])},
        'prior_versions_retained': {
            'config_sha256': PRIOR_CONFIG_SHA256, 'config_bytes': PRIOR_CONFIG_BYTES,
            'architecture_sha256': PRIOR_ARCH_SHA256, 'protocol_sha256': PRIOR_SUCCESSOR,
            'cells_sha256': PRIOR_CELLS_SHA256, 'revision_at_run': pre['head'],
            'reviewed_revision': PRE_REV,
            'note': ('the four documents were checked out from the reviewed revision before '
                     'this run; each is recoverable byte-exactly by `git show '
                     '<reviewed_revision>:<path>`, and by deleting every inserted text')},
        'dependent_hashes_that_move': {
            'config_sha256 / harness_file_sha256[config.json]': (
                'moves against b049307, as any config byte change must; no freeze exists, so '
                'nothing frozen is invalidated. Both prospective launch records '
                '(PROSPECTIVE_LAUNCH_RECORD_20260923_1922.json and _2030.json) pin the old '
                'config.json digest, and run_smoke.verify_acquisition_code refuses a launch with '
                'either of them, by design. FINITE_COSTED_PLAN_DRAFT_v2r3 also pins the old '
                'digest, but nothing consumes that pin with a refusal '
                '(assemble_prerun_bundle.py reads the sheet without a config-pin check): its '
                'pin is stale, not enforced. New dependent records are needed (not written '
                'here; the old ones are write-once and kept). Against the withdrawn first run '
                'the config does not move (written.config_equals_the_withdrawn_first_run)'),
            'protocol_sha256': 'moves; recorded as the new successor above',
            'architecture_sha256': 'moves (ARCHITECTURE is under design/, outside the harness pin)',
        },
        'dependent_hashes_that_do_not_move': ['rule_block_sha256', 'receipt_mask_sha256',
                                             'monitor.winstats_sha256',
                                             'environment_lock_sha256',
                                             'engineering_acquisition (== run_smoke.BOUND_LIMITS)',
                                             'harness_file_sha256 of every .py file'],
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server, build or network request; text '
                             'edits, digests, and local reads of the three pinned roster '
                             'sources'),
    }
    receipt_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt_path)
    print(json.dumps({'post_ok': ok, 'rule_block': post['config']['rule_block_sha256_after'][:12],
                      'new_protocol': post['protocol_sha256'],
                      'new_config': post['config_sha256'],
                      'negative_control_refused': control['every_variant_refused_on_placement'],
                      'variants': control['variants_run'],
                      'prompts_max_jaccard': [r['max_jaccard'] for r in
                                              prompt_check['per_prompt']]}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
