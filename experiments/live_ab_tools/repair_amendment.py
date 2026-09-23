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
  3. Eighteen PURE insertions: two config line blocks, byte-identical in
     config.json, ARCHITECTURE 6.1 and protocol Appendix B (the prompts inside
     `prefreeze`; `server_supervision` at top level, outside the rule block);
     seven dated protocol paragraphs (2.4 item 6, 5.3, 5.8, 12.2, 13.1, 14.3,
     14.6); five ARCHITECTURE insertions (4.4, 6.3, three in 7.1). No existing
     byte changes.
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
     sixteen document insertions moved out of its section (prose into the next
     section, configuration lines out of their fence) must be refused by the
     predicate of step 4. If the check cannot refuse, nothing is written.
  6. The protocol successor, ADDITIVELY in cells.json: the original pin
     untouched; the patch-state successor 64ace6d3 moves WHOLE into
     prior_successors with its changing commit 48f4d70 (verified with git show);
     the new successor names the amended protocol.
  7. One write-once receipt, results/live_ab/REPAIR_AMENDMENT_RECEIPT_<UTC>.json.

It refuses, changing nothing, if any precondition fails. It is NOT a freeze, NOT
trial, stage or launch approval; it runs no simulation, model, server, build or
network request. The prompts were AUTHORED by the implementing AI agent session
(this is not a model's served output being consulted; no model was run).

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
# The four conformance prompts. THE RULE COMES FIRST, and is fixed before the
# texts below were written. Nothing in it refers to any model output.
# ---------------------------------------------------------------------------
JACCARD_BELOW = 0.5
MAX_PROMPT_CHARS = 600
PROMPT_RULE = {
    'stated_before_the_texts': True,
    'authorship': ('written by the implementing AI agent session (session 60 repair lane), '
                   'not by hand; no model was run and no output of any served model '
                   '(incumbent, candidate or other) was consulted'),
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
    '   the implementing AI agent session under a rule recorded before their texts, without running either model and',
    '   without consulting any model\'s output; they were developed on neither model family. The extractor is unchanged.',
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
    '`trial_aborted(server_restart_cap)`. Every enrolled pair, attempt and missingness record is retained. There is **no',
    'replacement trial, no extra pair, no alpha transfer and no margin change**. A crash may be arm-related, so a',
    'cap-aborted trial is **not a valid null** and is reported as incomplete: it reports **no deployment or harm decision**,',
    'and a `decision` logged before the abort stays in the chain and is labelled "not reportable: trial incomplete (restart',
    'cap)". For this abort reason only, that label replaces the rule of 6.4 ("Aborts in the post-decision phase") and of',
    '14.6 under which a logged decision stands. The cap was fixed without looking at any success or cost outcome.',
    '',
    '**Real start, and refusal instead of a placeholder.** Every first start and every supervised restart goes through',
    '`lab_server`: the GGUF bytes and hash and the serving manifest are re-verified, the frozen argv is launched, `/health`',
    'is awaited, the full `/props` object (with `model_path` tokenized) is compared with the tokenized golden object of the',
    'freeze bundle, and the `SERVER_SMOKE` response is compared with the golden `generation_settings` object under the',
    'mask of 13.2. A failure at any of these stages is recorded durably as `server_start_failed` (12.2 row 28) and is never',
    'replaced by a success-valued `server_started` or `server_restarted`: no comparison flag is written true unless the',
    'comparison was made, and no placeholder digest is written. Its consequence is the rule already fixed for the stage: a',
    'GGUF, serving-manifest or identity difference is 6.4 row 6 (`trial_aborted(server_identity)`); a `SERVER_SMOKE`',
    'receipt difference is `trial_aborted(receipt_mismatch)` before any further dispatch; a restart that does not come up',
    'is the `server_unrecoverable` pause of 14.6; a first start that fails at launch or health dispatches nothing and ends',
    'the trial as `trial_aborted(infrastructure)`. Before seq 0, on every non-simulated path, the golden files are read,',
    'their digests are recomputed and compared with the config tables, and a null, missing, unreadable or mismatched golden',
    'file, or a runtime `golden` override, refuses the invocation with the preflight code `golden_objects`.',
)
P_5_8 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s item 2).* The four' % REVIEW,
    'out-of-design prompts are stored at `prefreeze.conformance_prompts` (ids `oodp/1` to `oodp/4`), byte-identically in',
    '`config.json`, ARCHITECTURE 6.1 and Appendix B. They are not hand-written: the implementing AI agent session wrote them',
    'under a rule fixed before their texts and recorded with them in the amendment receipt',
    '(`results/live_ab/REPAIR_AMENDMENT_RECEIPT_*.json`): short, self-contained Python function tasks that need only the',
    'standard library, in the signature-and-docstring form that `build_user_prompt` sends on its non-MBPP branch, with no',
    'tests, no examples and no reference solution (correctness is never computed, 2.4 item 6); each mechanically distinct',
    'under `normalize_prompt` from every prompt of the three pinned sources and from the six smoke tasks, with token-set',
    'Jaccard similarity below 0.5 to each of them. **No observed outcome was used to choose them**: no model was run, and no',
    'success, conformance, latency or other output of any model was consulted. They are not roster tasks and carry no task',
    'uid. With the six smoke tasks they are the ten prompts of the format-conformance rule of 2.4 item 6.',
)
P_12_2 = _lines(
    '| 28 | `server_start_failed` | *(Amendment 2026-09-23, pre-outcome; root %s item 1)* server id; `kind` (`start`, `restart`); `stage` (`gguf`, `serving_manifest`, `launch`, `health`, `identity`, `smoke`); `findings` (closed codes); pid; return code or null; argv hash; `/props` hash or null; load seconds; `restart_index` (0 for the first start). Written instead of, never beside, a success-valued #3 or #6 for the same attempt | yes |' % REVIEW,
    '| 29 | `worker_resolved` | *(Amendment 2026-09-23, pre-outcome; same review, item 3)* arrival, attempt, pid, `state` (`exited`, `killed_reaped`, `liveness_unknown`, `alive_unresolved`), return code or null, spool bytes and spool SHA-256 at resolution | yes |',
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4), to rows' % REVIEW,
    '2, 14 and 27 and to P6.* `episode_revealed` (#14) also carries `usage_complete` and `unknown_usage_calls` (13.1); the',
    'reason of `trial_aborted` (#27) may also be `server_restart_cap` (5.3) or `unresolved_worker` (14.6); the closed list of',
    'preflight check codes shared by `invocation_refused` (#2) and `preflight_refused` (P6) gains `golden_objects` (5.3).',
    'Rows 28 and 29 are trial-chain events. These additions are made before any freeze.',
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
    '`prefreeze.conformance_prompts` (5.8) join this list: neither may be amended after the first outcome.',
    '`server_supervision` lies outside the rule block, so it is bound by `config_sha256` and by the harness pin of',
    '`config.json`, not by `rule_block_sha256`; placing it there leaves the rule-block digest unchanged and relaxes nothing.',
)
P_14_6 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s item 3).* **Every worker is' % REVIEW,
    'resolved before a terminal acceptance.** Before `trial_ended` is written, and before any stage of 5.8 marks itself',
    'completed, every worker process of the trial or stage is resolved - confirmed exited - and recorded by a durable',
    '`worker_resolved` event (12.2 row 29) with `state` `exited` or `killed_reaped`. A worker whose exit cannot be confirmed',
    '(`liveness_unknown`, `alive_unresolved`) is unresolved: the trial ends as `trial_aborted(unresolved_worker)` instead of',
    '`trial_ended`, and a stage of 5.8 is recorded as incomplete. An abort or a pause for any other reason first drains',
    '(bounded; the `episode_hard_cap_s` kill still applies) and keeps its own reason; a worker still unresolved then is',
    'recorded with its state. The calls of an unresolved or killed worker that have no terminal record are unfinished, with',
    '`null` usage (13.1); none is counted as unsent or as 0, and no artifact such a call leaves is read as a completed',
    'response. This is truthful failure accounting: it does not prove that no request is sent after the terminal snapshot,',
    'and a phase accepted as successful must show every permitted worker resolved.',
)
A_4_4 = _lines(
    '| T32 | `server_start_failed` | D | *(Amendment 2026-09-23, pre-outcome; root %s item 1; protocol 5.3 and 12.2 row 28)* `server_id` enum; `kind` enum[`start`,`restart`]; `stage` enum[`gguf`,`serving_manifest`,`launch`,`health`,`identity`,`smoke`]; `findings` [enum] (closed codes: `IDENTITY_FINDINGS`, the receipt finding codes, `process_exited`, `health_timeout`, `smoke_transport`, `smoke_no_usage`, `serving_manifest`); `pid` int; `returncode` int?; `argv_sha256` hex64; `props_sha256` hex64?; `load_seconds` float; `restart_index` int (0 for the first start). Trial chain only. The record is carried by `lab_common.ServerStartFailed(LabError).record`; it is written instead of, never beside, a success-valued T4 or T8 |' % REVIEW,
    '| T33 | `worker_resolved` | D | *(Amendment 2026-09-23, pre-outcome; same review, item 3; protocol 14.6 and 12.2 row 29)* `arrival` int; `attempt` int; `pid` int; `state` enum[`exited`,`killed_reaped`,`liveness_unknown`,`alive_unresolved`]; `returncode` int?; `spool_bytes_at_resolution` int; `spool_sha256_at_resolution` hex64 |',
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 1, 3 and 4), to rows' % REVIEW,
    'T3, T17 and T31 and to P6.* T17 `episode_revealed` gains `usage_complete` bool and `unknown_usage_calls` int; the',
    '`reason` of T31 `trial_aborted` gains `server_restart_cap` and `unresolved_worker`; the preflight check enum shared',
    'by T3 `invocation_refused` and P6 `preflight_refused` gains `golden_objects`. The pure function',
    '`phase_resolution_verdict(...)` is evaluated before `trial_ended` and before any pre-freeze stage marks itself',
    'completed; `lab_verify_log` mirrors it as the FAIL-level check `workers.resolved`, and checks T4, T7, T8 and T32',
    'against protocol 5.3 as the FAIL-level check `server.lifecycle`.',
)
A_6_3 = _lines(
    '',
    '*Amendment 2026-09-23 (pre-outcome; root %s items 2 and 4; protocol' % REVIEW,
    '14.3):* this list gains `server_supervision` (top level, outside the rule block: bound by `config_sha256` and',
    '`harness_file_sha256[config.json]`, not by `rule_block_sha256`) and `prefreeze.conformance_prompts`.',
    '',
)
A_7_1_1B = _lines(
    '| 1b | `PREFLIGHT` | *(Amendment 2026-09-23, pre-outcome; root %s item 1)* on a non-simulated path: a golden file is null, missing, unreadable or does not match its config digest, or a runtime `golden` override is present | append `preflight_refused` with the check `golden_objects` to the **program** chain (D); no server is started and nothing success-valued is written | `ABORTED` | — |' % REVIEW,
)
A_7_1_20A = _lines(
    '| 20a | any | *(Amendment 2026-09-23; same review, item 1)* `lab_server.start` or `lab_server.restart` raises `ServerStartFailed` | `server_start_failed` (D) with the exception\'s record, never a success-valued T4 or T8; then the rule for its stage (protocol 5.3): `gguf`, `serving_manifest` or `identity` → `trial_aborted(server_identity)` (D); `smoke` → `trial_aborted(receipt_mismatch)` (D); `launch` or `health` on a restart → `trial_paused(server_unrecoverable)` (D), on the first start → `trial_aborted(infrastructure)` (D) | `ABORTED` / `PAUSED` | — |',
)
A_7_1_21AB = _lines(
    '| 21a | any | *(Amendment 2026-09-23; same review, item 4)* `server_down` on a server that already had `server_supervision.max_supervised_restarts_per_server_per_trial` (3) supervised restart attempts in this trial, counted from the chain | stop dispatching new arrivals; drain every open attempt (bounded; the `episode_hard_cap_s` kill still applies) and reveal each (D); `worker_resolved` per worker (D); `trial_aborted(server_restart_cap)` (D) + blocking anchor. No replacement trial, no extra pair; a logged `decision` is kept and labelled not reportable (protocol 5.3) | `ABORTED` | **yes** |',
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
    out['ok'] = (out['exactly_the_three_keys_added'] and not removed and not changed
                 and out['server_supervision_is_the_contract_value']
                 and out['conformance_prompts_equal_the_tool_texts']
                 and all(unchanged.values()) and ea_equals
                 and out['rule_block_sha256_before'] == PRIOR_RULE_BLOCK
                 and out['rule_block_sha256_after'] == PRIOR_RULE_BLOCK
                 and out['deleting_the_insertions_reproduces_the_prior_config'])
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
    ok = (all(additive.values())
          and all(post['every_insertion_inside_its_section_beside_its_anchor'].values())
          and not any(post['cr_bytes_after'].values()) and after['holds']
          and 'error' not in vocab and all(vocab.values()) and cfg['ok']
          and all(new[d] != old[d] for d in DOC_NAMES))
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
        row['passes'] = (route_ok and shape['ok'] and not equal and best < JACCARD_BELOW
                         and sbest < JACCARD_BELOW and not row['entry_point_defined_in_a_source']
                         and len(srcs) > 0)
        per.append(row)
    ids = [p['id'] for p in PROMPTS]
    distinct_among_themselves = (
        len({lab_data.normalize_prompt(p['prompt']) for p in PROMPTS}) == len(PROMPTS)
        and len({p['entry_point'] for p in PROMPTS}) == len(PROMPTS))
    return {'per_prompt': per,
            'ids_are_oodp_1_to_4': ids == ['oodp/%d' % i for i in range(1, 5)],
            'fields_are_exactly': all(tuple(p) == PROMPT_KEYS for p in PROMPTS),
            'distinct_among_themselves': distinct_among_themselves,
            'smoke_tasks': list(smoke_uids), 'smoke_tasks_missing_from_sources': missing_smoke,
            'source_counts': {k: len(v) for k, v in sources['records'].items()},
            'source_facts': sources['facts'],
            'all_pass': (all(r['passes'] for r in per) and ids == ['oodp/%d' % i for i in range(1, 5)]
                         and distinct_among_themselves and not missing_smoke
                         and all(tuple(p) == PROMPT_KEYS for p in PROMPTS))}


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
    receipt_path = REPO / 'results' / 'live_ab' / ('REPAIR_AMENDMENT_RECEIPT_%s.json' % stamp)
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
    pins_ok = (pre['config_is_the_reviewed_preimage']
               and pre['architecture_is_the_reviewed_preimage']
               and pre['protocol_is_the_reviewed_preimage']
               and pre['cells_is_the_reviewed_preimage']
               and not any(pre['cr_bytes'].values()) and before['holds']
               and pre['rule_block_sha256_before'] == PRIOR_RULE_BLOCK
               and pre['cells_round_trips'] and pre['cells_original_pin'] == ORIGINAL_PIN
               and pre['cells_current_successor'] == PRIOR_SUCCESSOR
               and sb.get('supersedes') == ORIGINAL_PIN
               and pre['cells_prior_successors'] == PRIOR_PRIOR_SUCCESSORS)
    if not pins_ok:
        print('refusing: a precondition failed; NOTHING was written: %s' % json.dumps(pre),
              file=sys.stderr)
        return 2
    if any(a['text_already_present'] for a in anchors.values()):
        print('refusing: the amendment is already present; NOTHING was written',
              file=sys.stderr)
        return 2
    rest_ok = (all(a.get('anchor_occurrences') == 1 and 'error' not in a
                   and (a.get('inside_its_section', True)) for a in anchors.values())
               and form['ok'])
    if not rest_ok:
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
    if not (control['every_variant_refused_on_placement']
            and control['scratch_copies_unchanged'] and control['real_documents_unchanged']):
        print('refusing: the negative control did not refuse; NOTHING was written: %s'
              % json.dumps(control), file=sys.stderr)
        return 2

    # -- 6. the successor, additively --------------------------------------------
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
            '"abort_trial_incomplete"}, outside the rule block. Seven dated prose paragraphs '
            'are inserted: 2.4 item 6 (the "developed on the incumbent\'s model family" '
            'sentence applies to the six smoke tasks only), 5.3 (the restart cap and its '
            'consequence; the real server start and the refusal instead of a success-valued '
            'placeholder; server_start_failed; the golden_objects preflight refusal), 5.8 (where '
            'the four prompts are stored and the rule that chose them without any observed '
            'outcome), 12.2 (event rows server_start_failed and worker_resolved; the new abort '
            'reasons server_restart_cap and unresolved_worker; the preflight code '
            'golden_objects; episode_revealed usage_complete and unknown_usage_calls), 13.1 '
            '(usage of unfinished calls is null, never 0 or unsent), 14.3 (server_supervision '
            'and the prompts are non-amendable after the first outcome) and 14.6 (every worker '
            'is resolved before trial_ended or any stage completion). It changes NO CPU cell, '
            'parameter, seed, horizon, estimator, outcome, decision rule, stopping rule, alpha, '
            'margin, sampling or other execution rule, and none of the vocabulary sections 1, '
            '3 and 11 this pin reads (verified byte-identical). The statistical rule-block '
            'digest is unchanged (cbfd1792).'),
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
            'no server start, no worker resolution and no prompt outcome: no model was run. '
            'The four prompts were written by the implementing AI agent session under a rule '
            'recorded before their texts; the mechanical checks are distinctness and '
            'similarity checks, not a proof that the tasks are unseen by any model.'),
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
    if a != b:
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
    }
    doc = {
        'schema': 'live_ab.repair_amendment_receipt.1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root, reviews/prerun_bundle_go_nogo_20260923_2040.md items 2 and 4 '
                      '(lines 17 and 19; quoted in this tool\'s docstring), with the fixed '
                      'names of items 1 and 3 from the session-60 repair contract'),
        'prepared_by': ('prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off'),
        'documents_amended_in_lockstep': [str(p.relative_to(REPO)) for p in (CONFIG, ARCH, PROTO)],
        'insertions': [ins.describe() for ins in INSERTIONS],
        'conformance_prompts': {
            '1_selection_rule_stated_before_the_texts': PROMPT_RULE,
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
                          'margin or statistical-rule change, and keeping the rule-block digest '
                          'cbfd1792 shows mechanically that none happened (the precedent is '
                          'engineering_acquisition, CONFIG_AMENDMENT_RECEIPT_20260923_1804.json)'),
            'what_counts': ('each supervised restart ATTEMPT per server per trial: a '
                            'server_restarted, or a server_start_failed with kind "restart"; '
                            'rebuilt from the chain on resume. The fourth required restart '
                            'aborts. This reading is stated in protocol 5.3 and ARCHITECTURE '
                            '7.1 row 21a; the orchestrator lane must count the same way'),
            'reportability': ('the contract default pending root\'s answer to question (i): '
                              'no deployment/harm decision; a decision logged before the abort '
                              'stays in the chain labelled "not reportable: trial incomplete '
                              '(restart cap)". Protocol 5.3 states it as the rule for this '
                              'abort reason, stricter than 6.4/14.6 for other aborts'),
            'fixed_without_outcomes': 'no success or cost outcome exists; none was looked at',
        },
        'choices_stated_in_the_prose_for_the_code_lanes_to_match': [
            'a first start failing at stage launch or health ends the trial as '
            'trial_aborted(infrastructure) (protocol 5.3; ARCHITECTURE 7.1 row 20a); '
            'gguf/serving_manifest/identity -> server_identity (existing 6.4 row 6), smoke -> '
            'receipt_mismatch, a restart that does not come up -> server_unrecoverable pause '
            '(existing 14.6)',
            'a failed supervised restart counts toward the cap (protocol 5.3)',
            'an abort or pause for another reason drains first and keeps its reason; '
            'unresolved_worker is used only where trial_ended or a stage completion would '
            'otherwise be written (protocol 14.6; ARCHITECTURE 7.1 row 21b)',
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
            'prior_successors_now': len(new_sb['prior_successors'])},
        'prior_versions_retained': {
            'config_sha256': PRIOR_CONFIG_SHA256, 'config_bytes': PRIOR_CONFIG_BYTES,
            'architecture_sha256': PRIOR_ARCH_SHA256, 'protocol_sha256': PRIOR_SUCCESSOR,
            'cells_sha256': PRIOR_CELLS_SHA256, 'revision': pre['head'],
            'reviewed_revision': PRE_REV,
            'note': 'recoverable byte-exactly by `git show <revision>:<path>`, and by deleting '
                    'every inserted text from each document'},
        'dependent_hashes_that_move': {
            'config_sha256 / harness_file_sha256[config.json]': (
                'moves, as any config byte change must; no freeze exists, so nothing frozen is '
                'invalidated. Both prospective launch records (PROSPECTIVE_LAUNCH_RECORD_'
                '20260923_1922.json and _2030.json) and FINITE_COSTED_PLAN_DRAFT_v2r3 pin the '
                'old config.json digest: by design a launch with either record now refuses, '
                'and new dependent records are needed (not written here; the old ones are '
                'write-once and kept)'),
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
