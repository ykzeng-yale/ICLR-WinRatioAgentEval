"""The ONE synchronized pre-outcome amendment of the EB1+EB5 repair subset, corrected (v2).

Root's rulings this amendment carries out, each read on origin/main:

  * ``reviews/prerun_bundle_go_nogo_20260923_2040.md`` item 2 (line 17): "The four absent
    conformance prompts must be fixed in a synchronized pre-outcome config/protocol/
    architecture amendment before stage 1; use out-of-design prompts and no observed success
    outcome to choose them."  Item 4 (line 19): the cap of three supervised restarts per server
    per trial, "a pre-outcome protocol/config/harness amendment before any trial; no
    replacement trial, extra pair, alpha transfer or margin change."  Items 1 and 3 fix the real
    server lifecycle (route (a)) and the worker-resolution requirement.
  * ``reviews/restart_cap_estimand_ruling_20260923_2114.md``: the cap is phase-aware (three
    cases, stated below in root's words); "The amendment should state these cases"; the cap
    "may be a top-level infrastructure setting outside the statistical rule block only if it
    cannot change the reference monitor, alpha allocation, success margin, score,
    enrollment-indexed band or first crossing ... disclose it in the protocol, config,
    architecture, report and immutable successor pins."
  * ``reviews/serving_manifest_binding_ruling_20260924_0153.md``: "use
    ``results/live_ab/freeze/serving_manifest.json`` as the single tracked, write-once frozen
    copy.  Assemble it from the pinned durable build before freeze; hash its canonical content
    and put that digest in the config and bundle.  Add the path to the architecture's freeze
    layout in the synchronized pre-outcome amendment."
  * ``reviews/eb1_receipt_attribution_review_20260924_0254.md`` and
    ``reviews/decision_receipt_metadata_ruling_20260924_0324.md``: receipt attribution by exact
    request binding; the decision receipt's external evidence; "12.4 has no timestamp
    authority"; and the delivery rule this tool obeys: the amendment and the real manifest may
    be in the immutable EB1+EB5 subset "if the manifest is derived from the pinned durable
    build, bound to the final config digest and available for exact root review".

WHAT IT DOES, AND ONLY THIS (every refusal goes through :func:`gate`, which names its checks)
  1. Preconditions on BYTES against the reviewed pre-images of b049307 (config.json e4d42f5d,
     13,917 bytes; ARCHITECTURE_FINAL.md 727003c1; protocol_FINAL.md 64ace6d3, the patch-state
     successor of commit 48f4d70; cells.json 5c4a28f7 with five prior successors; rule block
     cbfd1792), exactly as the withdrawn predecessor did; every anchor once, at a line start,
     inside its section; the one replacement site once, inside its fence.
  2. The four conformance prompts of the withdrawn predecessor, re-checked by its mechanical
     rule against the three pinned roster sources (read from ``--sources-dir``, verified against
     the config pins).
  3. The withdrawn predecessor (branch ``session60/repair-amend``, commits 1349619 and ff152e9)
     is named and verified from git: its two receipts hash to their pinned digests and neither
     commit is an ancestor of HEAD ("withdrawn, not applied").  Its history is not touched.
  4. THE REAL SERVING MANIFEST, as seen from the main checkout (``MAIN_CHECKOUT``, pinned, read
     only): ``assemble_serving_manifest.repo_root_problems`` / ``repo_roots`` rebind the three
     token roots of ``lab_common`` to that checkout and ``lab_serving_manifest.assemble`` reads
     the durable build ``work/llama.cpp-build/build`` there (``otool``/``nm`` metadata and file
     bytes; nothing executed, nothing built) with its provenance files.  Checked: the durable
     declaration ``results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json`` names the same
     launcher, the same nine libraries and the same rebuild receipt; the provenance files of the
     main checkout equal this checkout's tracked copies; a second assembly gives the same
     digest; the object re-verifies at once as seen from the main checkout and does NOT verify
     as seen from another checkout (an empty scratch root; the labels as seen from this checkout
     are recorded too); a mutated copy is refused by digest and, carrying its own
     digest, by the runtime comparison; a scratch copy passes
     ``lab_serving_manifest.verify_before_launch`` -- the exact function preflight and every
     ``lab_server`` start and restart call -- with no server started.
  5. Pure insertions (twenty-seven) plus ONE in-place replacement: in config.json, ARCHITECTURE
     6.1 and Appendix B (byte-identical copies) ``"serving_manifest_sha256": null`` becomes the
     manifest's canonical digest.  That is the only existing byte that changes; it is not an
     insertion, and it is bound exactly (old and new bytes, once per document, inside the
     fence, the only changed configuration key, null before).
  6. Postconditions computed before anything is written; a negative control on scratch copies
     (each prose insertion moved out of its section must be refused); the successor of
     cells.json (64ace6d3 demoted whole with its changing commit 48f4d70, as the predecessor
     did).
  7. Writes: the artifact ``results/live_ab/freeze/serving_manifest.json`` (write-once), then
     the four documents; then the dry check again on the written artifact against the digest of
     the written config.json; then the write-once receipt
     ``results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_<UTC>.json``.

It is NOT a freeze, NOT trial, stage or launch approval; it starts no server, runs no model,
build or network request.  The prompts were AUTHORED by an implementing AI agent session, itself
a language model; neither served model was run and no output of a served model was consulted.

The witnesses are ``tests_repair_amendment_v2.py`` (drives main() on scratch copies of the
b049307 blobs, with the real main checkout read for the manifest) and the independent
re-derivation ``verify_repair_amendment_v2.py``.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""

from __future__ import annotations

import argparse
import ast
import copy
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
#: where the four documents, the artifact and the receipt are written (re-pointed by the
#: witnesses at a scratch directory)
REPO = HERE.parent.parent
#: THIS checkout, read only: the tracked copies the main checkout's provenance files must equal
SOURCE_REPO = HERE.parent.parent
LAB = SOURCE_REPO / 'experiments' / 'live_ab'
LOCAL_STREAM = SOURCE_REPO / 'experiments' / 'local_stream'
SERVING = SOURCE_REPO / 'experiments' / 'live_ab_serving'
for _p in (str(LAB), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
import lab_data                                                # noqa: E402
import lab_serving_manifest as sm                              # noqa: E402
import assemble_serving_manifest as asm                        # noqa: E402
# The reviewed section scanner: a section runs from its heading to the next heading of the
# same or a higher level, fenced lines skipped.
from engineering_cap_amendment import block_of, fence_span, flatten, section_span  # noqa: E402

REL_CONFIG = 'experiments/live_ab/config.json'
REL_ARCH = 'experiments/live_ab/design/ARCHITECTURE_FINAL.md'
REL_PROTO = 'experiments/live_ab/design/protocol_FINAL.md'
REL_CELLS = 'experiments/live_ab_validation/cells.json'
CONFIG = REPO / REL_CONFIG
ARCH = REPO / REL_ARCH
PROTO = REPO / REL_PROTO
CELLS = REPO / REL_CELLS
DEFAULT_SOURCES_DIR = SOURCE_REPO / 'work' / 'local_stream' / 'data'

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

RECEIPT_PREFIX = 'REPAIR_AMENDMENT_V2_RECEIPT_'

#: The withdrawn, never-applied predecessor (root 21:14 withdrew its reporting wording; its
#: history is preserved: the branch is neither merged nor edited).  Verified from git at run
#: time (:func:`predecessor_checks`) and recorded in the receipt as ``withdrawn_predecessor``.
WITHDRAWN_PREDECESSOR = {
    'status': 'withdrawn, not applied',
    'branch': 'session60/repair-amend',
    'commits': ['134961944cec6e83f2b27586cda3d1f42ba40b72',
                'ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc'],
    'receipts': [
        {'commit': '134961944cec6e83f2b27586cda3d1f42ba40b72',
         'path': 'results/live_ab/REPAIR_AMENDMENT_RECEIPT_20260923_2151.json',
         'sha256': '6729de69f66ed7cea7b6f8c8eb8370d9612ab4be7f094288ee5c2cc445715a19'},
        {'commit': 'ff152e9ee8975b4a6cc47e6f1a54a416da07b9bc',
         'path': 'results/live_ab/REPAIR_AMENDMENT_CORRECTION_RECEIPT_20260923_2242.json',
         'sha256': '9feea2ac87b086810f38062bd039186a93d352aae1dbcc1d5e0a73ad9451a291'}],
    'documents_it_produced': {
        'first_run': {'config_sha256': 'c323e0f26e7cba68355083a104e6397097f446f5e4532eb23edea57952ebd850',
                      'architecture_sha256': '4e8546f236cf0211b9d8bb9375e42cc410f8d084fbd7c72dcee3e9ec9955d156',
                      'protocol_sha256': '25014221bbba4a4d67e8bde845d401318d7db6fc04375ec3f7d875532b754a0c',
                      'cells_sha256': 'af4ed3b9620d29a058528cd6b8ec544c127af135972a7143a05748b566b3cf59'},
        'correction_run': {'config_sha256': 'c323e0f26e7cba68355083a104e6397097f446f5e4532eb23edea57952ebd850',
                           'architecture_sha256': '78a4a1c72f00c594ef091227f8dbf99e300f856b82e50eed76c73e740bae6846',
                           'protocol_sha256': '5d108b4a1a8d076fdd79b973834b8f3b3e4604526a9d90e943329c9cbf2fc2b8',
                           'cells_sha256': 'c9504a22e63238e9b76e60bf61f6ae58300e5f87407d7f90b66dd61392d90cee'}},
    'why_withdrawn': ('its protocol 5.3 made a decision logged before a restart-cap abort "not '
                      'reportable" (the repair contract\'s provisional default); root\'s ruling '
                      'reviews/restart_cap_estimand_ruling_20260923_2114.md withdrew that wording '
                      'and fixed three phase-aware cases instead; its prose also described code '
                      'that had not been delivered (worker_resolved on the _prefreeze chain, a '
                      'stage-completion resolution verdict) and it carried no serving manifest'),
    'what_is_reused': ('its tool, witnesses and verifier as the starting point of this v2, its four '
                       'conformance prompts and their selection rule verbatim (re-checked here), '
                       'its configuration insertions byte for byte, and its successor demotion of '
                       '64ace6d3 with commit 48f4d70'),
    'history': ('preserved: branch session60/repair-amend is not merged and not edited; its two '
                'receipts stay on it byte-unchanged; neither of its protocol digests (25014221, '
                '5d108b4a) enters the successor history of cells.json'),
}

# ---------------------------------------------------------------------------
# The real serving manifest: where it is assembled from (read only)
# ---------------------------------------------------------------------------
#: The checkout that runs the trials (protocol 12.4 item 1: the main clone).  Pinned: the
#: manifest's paths are tokenized as seen from exactly this root.
MAIN_CHECKOUT = '/Users/yukangzengcmac/ICLR-WinRatioAgentEvals'
DURABLE_BUILD_REL = 'work/llama.cpp-build/build'
LAUNCHER_REL = DURABLE_BUILD_REL + '/bin/llama-server'
BUILD_RECEIPT_REL = 'results/live_ab/DURABLE_REBUILD_20260923T192024Z.json'
DECLARATION_REL = 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json'
PATCH_REL = 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
#: the tracked files the main checkout's copies must equal byte for byte (a manifest names them
#: by ``<RESULTS>`` / ``<REPO>`` tokens, so after the merge the trial resolves them there)
TRACKED_PROVENANCE = (BUILD_RECEIPT_REL,
                      BUILD_RECEIPT_REL[:-len('.json')] + '_build.log',
                      BUILD_RECEIPT_REL[:-len('.json')] + '_configure.log',
                      PATCH_REL, DECLARATION_REL)
DECLARATION_SHA256 = 'bc180e4e85b3563564dffb8e4ad6ef3c8818c549c4f7cfc1c17b3869c13c2096'
ARTIFACT_REL = sm.TRACKED_RELPATH
#: The mutation the refusal controls apply to a copy of the manifest: one library digest.
MUTATED_LIBRARY_INDEX = 0

ARCH_MARKER = b'### 6.1 Full key list'
PROTO_MARKER = b'## Appendix B.'
#: the sections the vocabulary pin reads (cells.json sections_read [1, 3, 11])
VOCAB_MARKERS = {1: b'## 1. Purpose, scope', 3: b'## 3. Task roster',
                 11: b'## 11. The planning study'}
R2040 = '`reviews/prerun_bundle_go_nogo_20260923_2040.md`'
R2114 = '`reviews/restart_cap_estimand_ruling_20260923_2114.md`'
R0153 = '`reviews/serving_manifest_binding_ruling_20260924_0153.md`'
R0254 = '`reviews/eb1_receipt_attribution_review_20260924_0254.md`'
R0324 = '`reviews/decision_receipt_metadata_ruling_20260924_0324.md`'

# ---------------------------------------------------------------------------
# The configuration content (repair contract, "Fixed names (EB1)")
# ---------------------------------------------------------------------------
SERVER_SUPERVISION = {'max_supervised_restarts_per_server_per_trial': 3,
                      'on_exceeding': 'abort_trial_incomplete'}

# ---------------------------------------------------------------------------
# The four conformance prompts, the withdrawn predecessor's texts and rule, VERBATIM.  The rule
# is stated first.  That it was fixed before the texts were written is the implementing
# session's attestation, not a recorded fact: the rule and the texts entered the repository in
# the same file and the same commit (1349619, on the withdrawn branch).
# ---------------------------------------------------------------------------
JACCARD_BELOW = 0.5
MAX_PROMPT_CHARS = 600
PROMPT_RULE = {
    'order': ('the rule is stated ahead of the texts in this tool and in its receipts; that it '
              'was fixed before the texts were written is the implementing session\'s '
              'attestation, NOT a recorded fact: the rule and the texts entered the repository '
              'in the same file and the same commit (1349619, withdrawn branch '
              'session60/repair-amend); this v2 copies both verbatim'),
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
#: the ONE existing configuration value this amendment changes (null -> the manifest digest)
CHANGED_CONFIG_KEY = 'llama_cpp.serving_manifest_sha256'
CHANGED_CONFIG_KEYS = [CHANGED_CONFIG_KEY]
REPLACE_OLD = b'"serving_manifest_sha256": null}'
REPLACE_NEW_FMT = '"serving_manifest_sha256": "%s"}'
#: subtrees that must be unchanged (as parsed); llama_cpp is compared without the one key
UNCHANGED_CONFIG_PATHS = ('engineering_acquisition', 'sampling', 'execution', 'servers',
                          'llama_args', 'receipt', 'hardware_allowlist',
                          'environment_lock_sha256', 'pause_thresholds', 'monitor',
                          'plumbing_fail_conditions', 'integrity_label_rule', 'roster',
                          'sandbox', 'anchor', 'refreeze')


def _lines(*lines: str) -> str:
    return ''.join(line + '\n' for line in lines)


# ---------------------------------------------------------------------------
# The prose.  Each is a pure insertion at one anchor, inside one section.  Each states what the
# code of the EB1+EB5 subset PERFORMS (the functions named in the receipt's
# ``code_the_prose_describes``); nothing is promised that the code does not do.
# ---------------------------------------------------------------------------
P_2_2 = _lines(
    '',
    '   *Amendment 2026-09-24 (pre-outcome; root %s and' % R0153,
    '   %s):*' % R0324,
    '   the serving manifest is **one tracked, write-once artifact**,',
    '   `results/live_ab/freeze/serving_manifest.json`, the file `serving_manifest.json` of the freeze tree',
    '   `<results root>/freeze`; no other location is read, and a runtime or configuration key that names another one',
    '   refuses. Its bytes are its canonical JSON plus one newline; it must be a regular file (a symlink refuses); the',
    '   SHA-256 of its canonical JSON is `llama_cpp.serving_manifest_sha256` of Appendix B, and a null or malformed',
    '   digest refuses: the artifact\'s own digest is never taken as the expectation. It was assembled for this',
    '   amendment from the durable build of item 1 (`work/llama.cpp-build/build` of the checkout that runs the',
    '   trials, declared in `results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json`) by reading metadata only',
    '   (`otool`, `nm` and file bytes; nothing was executed or built), with every path tokenized as that checkout',
    '   sees it (`<REPO>/...`, `<RESULTS>/...`); a manifest assembled from another checkout names the build',
    '   differently and refuses there. Besides the fields of the table it records the launcher\'s tokenized path and',
    '   digest, the whole dependency closure (each edge of the recursive resolution under the launch context the',
    '   server gets, each member\'s bytes and SHA-256), the build options of the build\'s `CMakeCache.txt`, and the',
    '   path, bytes and SHA-256 of each provenance file (the durable-build receipt, the build and configure logs,',
    '   `CMakeCache.txt`, `common/build-info.cpp`, the lifecycle patch). **Re-verification, at preflight of every',
    '   invocation (resume included) and at every server start and supervised restart (5.3):** the artifact is read',
    '   again and its digest compared with the configuration; then the launcher\'s path and SHA-256, the closure',
    '   (re-derived from the Mach-O load commands, every member re-hashed: a member added, removed, moved or changed',
    '   refuses), `LC_RPATH`, the embedded Metal library (the one member carrying `__DATA,__ggml_metallib`, its',
    '   container and section digests), the provenance files (re-read and re-hashed) and the build string of',
    '   `build-info.cpp` are **measured** and compared field by field; once the started server answers, its actual',
    '   `/props.build_info` is compared with `props_build_info`. The launch context is part of the closure: the',
    '   server runs in its launcher\'s directory, and the frozen launch environment has no `GGML_*` or `DYLD_*`',
    '   variable, so such a variable in the orchestrator\'s environment refuses. A Metal library that is not',
    '   embedded is not modelled and refuses. A refusal is the preflight code `serving_manifest` (6.4 row 21) or, at',
    '   a start or restart, `server_start_failed` at stage `serving_manifest` (5.3). What this does not establish:',
    '   which bytes the GPU executes; every check is on files and on the server\'s own answer.',
)
P_2_4 = _lines(
    '',
    '   *Amendment 2026-09-24 (pre-outcome; root %s item 2):* in the' % R2040,
    '   sentence above, "the prompts ... were developed on the incumbent\'s model family" applies to the **six smoke tasks',
    '   only**. The four out-of-design prompts of 5.8 (`prefreeze.conformance_prompts`) were written by the',
    '   implementing AI agent session, without running either served model (incumbent or candidate) and without',
    '   consulting any output of a served model; they were developed on neither model family. Their selection rule is',
    '   stated ahead of the texts in the amendment tool and its receipts (5.8); that the rule was fixed before the texts',
    '   were written is the session\'s attestation, not a recorded fact. The extractor is unchanged.',
)
P_5_3 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 1 and 4, and' % R2040,
    '%s).*' % R2114,
    '**Restart cap.** At most **three** supervised restarts per server per',
    'trial: `server_supervision` = `{"max_supervised_restarts_per_server_per_trial": 3, "on_exceeding":',
    '"abort_trial_incomplete"}`, a top-level config key outside the rule block. Every non-simulated invocation reads',
    'it, and `execution.health_failures_to_down`, before seq 0; either one absent or malformed refuses the invocation',
    '(`preflight_rule_failed`): there is no default cap. At every health poll a server whose process has exited is',
    '`server_down` (detected by exit); otherwise `/health` is polled, and `health_failures_to_down` consecutive',
    'failures are `server_down`. Before `server_down` is written every open spool is ingested; then the old process',
    'is stopped (`server_stopped`). Every supervised restart **attempt** counts towards the cap, whether it succeeds',
    '(`server_restarted`) or fails (`server_start_failed` with `kind = restart`); the count is rebuilt from the chain',
    'on resume. When a `server_down` finds the server\'s attempts already at three, a fourth restart would be',
    'required: nothing is restarted, no new arrival is dispatched, the open attempts drain through the ordinary loop',
    '(the `episode_hard_cap_s` kill still applies) and are revealed, every worker is resolved (14.6), and the trial',
    'ends `trial_aborted(server_restart_cap)`, a **new automatic abort** (6.4). Every enrolled pair, attempt, band',
    'endpoint, failure, unknown usage and missingness record is kept. **No replacement trial, no extra pair, no alpha',
    'transfer, no margin change.** The cap was fixed without looking at any success or cost outcome.',
    '',
    '**What a cap abort means depends on where the chain stands** when the `server_down` that required the fourth',
    'restart is written (root\'s ruling of 21:14; `lab_eventlog.restart_cap_case` fixes the case from the chain alone):',
    '',
    '- **(a) Before a valid decision** (`before_decision`): no new deploy or harm decision is made. A look logged',
    '  during the abort\'s drain is logged exactly as it would be without the cap, and if it crosses, no `decision` is',
    '  appended; the report names that crossing as not acted on. The trial is reported **incomplete**, with its',
    '  enrolled prefix, band endpoints, attempts, failures, unknown usage and missingness. It is not a null result and',
    '  not a valid abstention: a crash may be arm-related, so it is never reclassified as favourable, unfavourable or',
    '  null.',
    '- **(b) After a valid, logged and externally receipted decision** (`after_receipted_decision`): the decision',
    '  stands at its original `tau` and is reported. The follow-up cohort is truncated, and every arrival that did not',
    '  run is counted and reported. No band, score, `n`, decision time or claim of the earlier prefix is revised.',
    '- **(c) While a logged decision awaits its blocking receipt** (`decision_provisional`): the decision is',
    '  provisional, not a finalized external decision. The owed abort is not taken while the receipt is pending: the',
    '  trial stays in the anchor wait, the servers stay supervised, and nothing post-switch is dispatched. When the',
    '  existing receipt rule of 12.4 succeeds, the abort is taken before any `traffic_switch`, and the decision is',
    '  reported as in (b), at its original `tau`, labelled as receipted after the cap bound. When the receipt cannot',
    '  be obtained (the decision anchor comes back failed, or the wait of 6.4 row 26 runs out), the existing rule',
    '  applies: `trial_paused(anchor_unavailable)`, with the abort still owed after the pause. A decision that is',
    '  never receipted is reported as provisional, never as a finalized claim.',
    '',
    '"Externally receipted" means the decision\'s blocking anchor with its chained external receipt of 12.4 (the',
    'amendment of 12.4 of this date), including the server time of claim 3 of 1.4. A logged decision without such a',
    'receipt is reported as provisional in every trial, capped or not.',
    '',
    '**Cap invariance.** The cap reads no outcome, score, band or coin. It changes nothing in the reference monitor,',
    'the alpha allocation, the success margin, the scoring, the enrollment-indexed band or the first crossing: every',
    '`monitor_update` is written exactly as it would be without the cap, `lab_monitor`, `lab_reference_rule`,',
    '`lab_coin`, `lab_design` and `lab_enclosure` are not changed by the repair, and case (a) only withholds a',
    'decision. It does change **operational completion and observed exposure**, and both are reported: every',
    'terminal record carries `completion` (12.2), with the case, the decision\'s receipt state and seq, the receipt\'s',
    'server time, the arrivals of the frozen order that ran and did not run, and the follow-up arrivals that ran and',
    'did not run. The verifier recounts it (`server.lifecycle`).',
    '',
    '**Real start, and refusal instead of a placeholder.** Every first start, start at resume and supervised restart',
    'goes through `lab_server.start`, in stages: `gguf` (the GGUF file named explicitly for the server is read, and',
    'its bytes and SHA-256 are measured against `servers.<id>.bytes` and `sha256_expected`, never copied from the',
    'configuration; preflight also refuses a frozen entry whose `sha256_recomputed` differs from `sha256_expected`),',
    '`serving_manifest` (the artifact of 2.2,',
    're-verified against the runtime before the launch), `launch`, `health` (healthy only when `/health` answers 200',
    'and the child is the port\'s only listener), `identity` (first the server\'s actual `/props.build_info` against',
    'the manifest, a difference being recorded at stage `serving_manifest`; then the full `/props`, `model_path`',
    'tokenized, against the tokenized golden object of the freeze bundle) and `smoke` (`SERVER_SMOKE`, compared with',
    'the golden `generation_settings` under the mask of 13.2; its `usage` and `timings` keys must be present). A',
    'failure at any stage is recorded durably as `server_start_failed` (12.2 row 28), the child is stopped, and no',
    'success-valued `server_started` or `server_restarted` is written: no comparison flag is written true unless the',
    'comparison was made, and no placeholder digest is written. What follows, by stage, **under rules that existed',
    'before this amendment**: a `gguf`, `serving_manifest` or `identity` failure is 6.4 row 6',
    '(`trial_aborted(server_identity)`); a smoke receipt that differs from the golden object is',
    '`trial_aborted(receipt_mismatch)` (6.4 row 12); a supervised restart that never becomes healthy is the',
    '`server_unrecoverable` pause of 14.6. **New automatic aborts** added by this amendment (6.4): a `SERVER_SMOKE`',
    'that yields no receipt (no HTTP 200 JSON object, `smoke_transport`; a `usage` or `timings` key missing,',
    '`smoke_no_usage`) also ends the trial as `trial_aborted(receipt_mismatch)`; a **first** start that fails at',
    '`launch` or `health` dispatches nothing and ends the trial as `trial_aborted(infrastructure)`, and a crash between',
    'the failure record and the abort is resumed into that abort. A start at resume follows the restart rules. A',
    'start call the harness refused, or an exception it did not anticipate, ends the trial as',
    '`trial_aborted(harness_defect)`.',
    '',
    '**Golden objects, before seq 0.** On every non-simulated path the golden files are read from the freeze tree,',
    'their canonical digests recomputed and compared with the config tables; a null, missing, unreadable or',
    'mismatched golden file, a golden `model_path` that is not tokenized, a runtime `golden` override, or a `--gguf`',
    'path whose tokenized form is not the golden `model_path` refuses the invocation with the preflight code',
    '`golden_objects`.',
)
P_5_8 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s item 2).* The four' % R2040,
    'out-of-design prompts are stored at `prefreeze.conformance_prompts` (ids `oodp/1` to `oodp/4`), byte-identically in',
    '`config.json`, ARCHITECTURE 6.1 and Appendix B. They are not hand-written: an implementing AI agent session wrote',
    'them. Their selection rule is stated ahead of the texts in the amendment tool',
    '(`experiments/live_ab_tools/repair_amendment_v2.py`) and in its receipt',
    '(`results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_<UTC>.json`); the same rule and texts were first recorded by a',
    'predecessor amendment that was withdrawn and never applied (branch `session60/repair-amend`, named in that',
    'receipt). That the rule was fixed before the texts were written is the session\'s attestation, not a recorded',
    'fact, since the rule and the texts entered the repository in one commit. The rule: short, self-contained Python',
    'function tasks that need only the standard library, in the signature-and-docstring form that',
    '`build_user_prompt` sends on its non-MBPP branch, with no tests, no examples and no reference solution',
    '(correctness is never computed, 2.4 item 6); each mechanically distinct under `normalize_prompt` from every',
    'prompt of the three pinned sources and from the six smoke tasks, with token-set Jaccard similarity below 0.5 to',
    'each of them. **No observed outcome was used to choose them**: neither served model (incumbent or candidate)',
    'was run, and no success, conformance, latency or other output of any served model was consulted. They are not',
    'roster tasks and carry no task uid. With the six smoke tasks they are the ten prompts of the format-conformance',
    'rule of 2.4 item 6.',
)
P_6_4 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 1, 3 and 4, and' % R2040,
    '%s).*' % R2114,
    '**New automatic, deterministic aborts.** This amendment adds four',
    'triggers that did not exist before it: `trial_aborted(server_restart_cap)` when a fourth supervised restart of a',
    'server would be required (5.3); `trial_aborted(unresolved_worker)` when the resolution verdict of 14.6 does not',
    'pass where a terminal record would otherwise be written; `trial_aborted(infrastructure)` when the first start of a',
    'server fails at `launch` or `health` (5.3), a second trigger of that reason beside the ten-failure rule; and',
    '`trial_aborted(receipt_mismatch)` when a `SERVER_SMOKE` yields no receipt at all (`smoke_transport`,',
    '`smoke_no_usage`; 5.3). Each is automatic, is reported under its own reason and is never',
    '`operator_discretion` (14.6). In the post-decision phase an `unresolved_worker` or `receipt_mismatch` abort is',
    'treated as the aborts listed under "Aborts in the post-decision phase" above: the follow-up cohort is truncated',
    'and the logged, receipted decision stands. A first-start abort cannot occur there, because it precedes every',
    'dispatch. A `server_restart_cap` abort follows the three cases of 5.3: before a valid decision it prevents one;',
    'after a logged and externally receipted decision, that decision stands at its original `tau` and the follow-up',
    'is truncated and counted; while the decision awaits its blocking receipt, it is provisional and the existing',
    'receipt and pause rules of 12.4 and row 26 apply. An abort still only removes decisions, never creates one. An',
    '`unresolved_worker` abort names in its `resolution` record the reason it superseded (14.6).',
)
P_12_2 = _lines(
    '| 28 | `server_start_failed` | *(Amendment 2026-09-24, pre-outcome; root %s item 1)* server id; `kind` (`start`, `restart`); `stage` (`gguf`, `serving_manifest`, `launch`, `health`, `identity`, `smoke`); `findings` (closed codes); pid (0 when no process existed); return code or null; argv hash; `/props` hash or null; load seconds; `restart_index` (0 for a start). Written instead of, never beside, a success-valued #3 or #6 for the same attempt (5.3) | yes |' % R2040,
    '| 29 | `worker_resolved` | *(Amendment 2026-09-24, pre-outcome; same review, item 3)* arrival, attempt, pid, `state` (`exited`, `killed_reaped`, `liveness_unknown`, `alive_unresolved`), return code or null, spool bytes and spool SHA-256 at resolution (the offset the deposit is sealed to, 14.6) | yes |',
    '| 30 | `anchor_receipt_rejected` | *(Amendment 2026-09-24, pre-outcome; root %s and %s)* the receipt line\'s `request_id` when it is one (32 lowercase hex), else null; `reason` (`unknown_request`, `stale`, `malformed`, `duplicate`, `conflict`); SHA-256 and byte length of the line as it stays in the receipt spool. The line is attributed to no anchor (12.4) | yes |' % (R0254, R0324),
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 1, 3 and 4,' % R2040,
    'and the rulings of 21:14, 02:54 and 03:24), to rows 2, 14, 19, 20, 26 and 27 and to P6 and P8.*',
    '`episode_revealed` (#14) also carries',
    '`usage_complete` and `unknown_usage_calls` (13.1). `anchor` (#19) also carries the `request_id` of the durable',
    'anchor request it was sent as; `anchor_receipt` (#20) also carries the `request_id` it answered and, on a verified',
    'decision receipt only, the SHA-256 of the committed anchor file, of the echoed comment body and of the response\'s',
    '`node_id` (12.4). `deposit_sealed` (#26) lists as `late_unread` every spool found past its resolution offset. The',
    'reason of `trial_aborted` (#27) may also be `server_restart_cap` (5.3) or `unresolved_worker` (14.6), both',
    'automatic aborts of 6.4. Every terminal record (#27) also carries `completion` (the restart-cap case of 5.3, the',
    'decision\'s receipt state, the arrivals that ran and did not run, the follow-up that ran and did not run) and',
    '`resolution` (the verdict of 14.6, every unresolved attempt, every unfinished call with usage `null`, every spool',
    'found past its offset, the servers observed idle, and the reason an `unresolved_worker` abort superseded). The',
    'closed list of preflight check codes shared by `invocation_refused` (#2) and `preflight_refused` (P6) gains',
    '`golden_objects` (5.3). Rows 28 and 29 are written on a trial chain only. Row 30 is written wherever anchor events',
    'are: a trial chain, and the program chain beside P8. These additions are made before any freeze.',
)
P_12_4 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s and' % R0254,
    '%s): receipt attribution.*' % R0324,
    '12.4 has **no timestamp authority**, and this',
    'amendment adds none. Every line of the receipt spool (`anchor_spool/receipts.jsonl`) becomes **exactly one**',
    'chain event: `anchor_receipt`, `anchor_failed` or `anchor_receipt_rejected` (12.2 row 30). A line is attributed',
    'to an anchor **only** when its `request_id` (32 lowercase hex) names a durable anchor request',
    '(`anchor_spool/requests.jsonl`, written with the chained `anchor`, which carries the same id) and that request',
    'agrees with the chained `anchor` of its `anchor_seq`. Otherwise the line is rejected and never credited to the',
    'newest anchor: `malformed` (not a JSON object, no such id, a field the chain cannot hold, or a decision receipt',
    'missing evidence), `unknown_request`, `duplicate` (the exact bytes that already resolved that anchor), `stale`',
    '(another line for an earlier, resolved anchor), `conflict` (another line for the newest resolved anchor, a',
    'request that disagrees with its anchor, or decision evidence that disagrees with itself or with its request).',
    '**No unknown or stale row becomes a receipt.** A rejected line resolves nothing: its anchor stays pending and',
    'the existing timeout of 6.4 row 26 applies. The line stays in the spool unaltered, and the chain carries its',
    'SHA-256 and length. A resumed invocation re-reads the spool and does not chain again a line the chain holds.',
    '**The decision receipt.** An `ok` line bound to a `decision` anchor request is the decision\'s external receipt',
    'only if it carries: the push (`pushed`, a 40-hex commit, the frozen anchor branch); the SHA-256 of the anchor',
    'file of that request (the anchor head: `upto_seq`, `upto_h`, the segment SHA-256); the comment\'s `id` and',
    '`node_id`; parsable `created_at` and `updated_at`; the SHA-256 of the exact comment body of item 3 (trial id,',
    '`upto_seq`, `upto_h`, segment SHA-256); and the raw API response, whose SHA-256 is `receipt_sha256` and whose',
    'own `id`, `node_id`, `created_at`, `updated_at` and `body` equal the row\'s. Evidence missing is `malformed`;',
    'evidence inconsistent is `conflict`, including `updated_at` earlier than `created_at`, the only ordering read.',
    'No wall-clock equality and no latency window is imposed. The chained `anchor_receipt` then carries',
    '`created_at`, the server time of claim 3 of 1.4. The decision is **externally receipted** (claim 3 of 1.4, the',
    'gate of item 5, the cases of 5.3) only by such a receipt of one of its own blocking decision anchors; until',
    'then it is provisional, and neither `traffic_switch` nor any post-decision assignment is written. A receipt',
    'chained for the pending decision anchor that still does not qualify marks that anchor failed, which is the',
    'pause of 6.4 row 26, instead of requesting it again without end. What this does **not** perform: any read of',
    'the remote that the push or the comment exists. In a MOCK tree only (a dry run), a receipt that claims no',
    'external evidence at all is accepted; any line that claims some is checked in full.',
)
P_13_1 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s item 3).* Every' % R2040,
    '`episode_revealed` also carries `usage_complete` and `unknown_usage_calls`: `usage_complete` is true only when',
    'every call the attempt started before its reveal has a response with a usage receipt, and `unknown_usage_calls`',
    'counts the calls that have none (a failed try, whose usage the client never knows, or a call without any terminal',
    'line). `completion_tokens` stays the known tokens; it is reported as a lower bound whenever `usage_complete` is',
    'false and as unknown for a reveal that carries no flag, never as a complete count. A call left without a terminal',
    'record when its worker is resolved or killed is **unfinished**: its delivery is unknown, its usage is `null`,',
    'never 0, and it is never counted as unsent. The exposure ledger keeps the calls of an arrival that was never',
    'revealed in their own `unrevealed` cell; a cell with unknown usage marks its tokens as a lower bound, and the',
    'trial totals are `null` with the reason `unknown_usage` whenever any call\'s usage is unknown.',
)
P_14_3 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 2 and 4, and' % R2040,
    '%s).*' % R2114,
    'The config key `server_supervision` (the restart cap of 5.3), the',
    'four prompts at `prefreeze.conformance_prompts` (5.8), the three restart-cap cases of 5.3 and the rule of 14.6',
    'that every worker is resolved before a terminal record join this list: none may be amended after the first',
    'outcome. `server_supervision` lies outside the rule block, so it is bound by `config_sha256` and by the harness',
    'pin of `config.json`, not by `rule_block_sha256`: the rule-block digest does not cover it, and that digest being',
    'unchanged shows nothing about this key or about any protocol text. The serving manifest\'s digest,',
    '`llama_cpp.serving_manifest_sha256`, is a value of `config.json`, which is already immutable (decision-defining',
    'code, below); the artifact it names is write-once (2.2).',
)
P_14_6 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 1, 3 and 4, and' % R2040,
    '%s).*' % R2114,
    '**Every worker is resolved before a terminal record.** A worker',
    'process is a used send permit until its exit is confirmed: the orchestrator has no gate that can revoke a live',
    'worker\'s request. Each worker is therefore polled after its reveal until its exit is confirmed, and recorded by a',
    'durable `worker_resolved` (12.2 row 29) with `state` `exited` or `killed_reaped`; a worker whose kill cannot be',
    'confirmed within the bound is recorded `alive_unresolved`, one whose liveness cannot be read `liveness_unknown`,',
    'and an unresolved record is never undone later. The pair boundary waits for both workers to be resolved, not only',
    'revealed. An abort or a pause first runs a bounded drain (the `episode_hard_cap_s` kill still applies) and keeps',
    'its own reason. Before `trial_ended` or `trial_aborted` is written, every open attempt is revealed, every worker is',
    'resolved or recorded unresolved, every server still held is observed idle, the deposit seals each spool at its',
    'recorded resolution offset (bytes found later are listed and never read), and a pure resolution verdict is taken',
    'over the chain, the spools and the server observation. If it does not pass, the terminal record is',
    '`trial_aborted(unresolved_worker)`; its `resolution` lists every unresolved attempt and every unfinished call',
    '(usage `null`, 13.1) and names the abort reason it superseded. On resume an earlier worker is identified by its',
    'pid and its process identity; a live orphan\'s process group is killed and confirmed gone before its attempt is',
    'revealed as interrupted, or else the invocation is refused. The verifier checks the same rules',
    '(`workers.resolved`, FAIL level). This is truthful failure accounting: it does not prove that no request is sent',
    'after the terminal snapshot, and unresolved work makes the phase incomplete, never zero. `worker_resolved` is a',
    'trial-chain event. For the pre-freeze stages of 5.8, the loaded reference sweep resolves its background load',
    'streams through the durable ledger of `lab_load` (an intent before every request, one terminal line after it)',
    'and is recorded incomplete unless every load source is resolved; it does not take the resolution verdict above.',
    'The resolution rule of any stage driver that starts worker processes is fixed with that driver, before its stage',
    'runs. The four automatic aborts that the amendment of 6.4 of this date adds - `trial_aborted(unresolved_worker)`,',
    '`trial_aborted(server_restart_cap)`, and the first-start `trial_aborted(infrastructure)` and the no-receipt',
    '`trial_aborted(receipt_mismatch)` of 5.3 - are automatic aborts of 6.4, so the rule above that every other abort',
    'is `operator_discretion` does not apply to them.',
)
P_16 = _lines(
    '16. *(Amendment 2026-09-24, pre-outcome; root',
    '    %s.)* the **restart-cap' % R2114,
    '    case** of 5.3 (`none`, `before_decision`, `after_receipted_decision`, `decision_provisional`) with the',
    '    decision\'s receipt state; whether the decision is reportable (not in case (a), and not when it lacks its chained',
    '    external receipt, which is labelled provisional); in case (a) the crossing that was not acted on; the cap\'s',
    '    effect on completion and exposure (arrivals of the frozen order not run, follow-up arrivals not run); and, per',
    '    episode, whether its completion tokens are complete, a lower bound or unknown (13.1).',
)
A_2_1 = _lines(
    '| `lab_serving_manifest.py` | G4 | *(Amendment 2026-09-24, pre-outcome; root %s)* the serving manifest of protocol 2.2 item 2: the one write-once artifact `results/live_ab/freeze/serving_manifest.json`, its assembly from the durable build and its re-verification against the runtime at every invocation, start and restart; the dependency closure of `experiments/live_ab_serving/dependency_closure.py` transcribed verbatim (3.16) |' % R0153,
)
A_2_2 = _lines(
    '    serving_manifest.json        # protocol 2.2 item 2: written once (amendment 2026-09-24, root 01:53)',
)
A_3_16_ROW = _lines(
    '| lab_serving_manifest | x | . | . | . | . | . | x | . | . | . | . | . | . | . | . | . | . | . | . | . |',
)
A_3_16_NOTE = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s):' % R0153,
    'the row `lab_serving_manifest`.*',
    'The module holds the serving manifest of protocol 2.2 item 2 (2.1). It may import the standard library and',
    '`lab_common` only. `lab_server` and `lab_orchestrator` may import it (the matrix has no column for it;',
    '`tests_lab_isolation.py` names both edges), and `dryrun_live_ab` imports it to deposit a mock manifest. The',
    'dependency closure it carries is transcribed verbatim from `experiments/live_ab_serving/dependency_closure.py`,',
    'which it does not import; `experiments/live_ab_controls/tests_sm_manifest.py` keeps the two equal statement by',
    'statement.',
)
A_4_4 = _lines(
    '| T32 | `server_start_failed` | D | *(Amendment 2026-09-24, pre-outcome; root %s item 1; protocol 5.3 and 12.2 row 28)* `server_id` enum; `kind` enum[`start`,`restart`]; `stage` enum[`gguf`,`serving_manifest`,`launch`,`health`,`identity`,`smoke`]; `findings` [enum] (closed codes: `lab_server.IDENTITY_FINDINGS`, `lab_client.RECEIPT_FINDINGS`, `lab_server.START_FINDINGS`); `pid` int; `returncode` int?; `argv_sha256` hex64; `props_sha256` hex64?; `load_seconds` float; `restart_index` int (0 for a start). Trial chain only. The record is carried by `lab_common.ServerStartFailed(LabError).record`; it is written instead of, never beside, a success-valued T4 or T8 |' % R2040,
    '| T33 | `worker_resolved` | D | *(Amendment 2026-09-24, pre-outcome; same review, item 3; protocol 14.6 and 12.2 row 29)* `arrival` int; `attempt` int; `pid` int; `state` enum[`exited`,`killed_reaped`,`liveness_unknown`,`alive_unresolved`]; `returncode` int?; `spool_bytes_at_resolution` int; `spool_sha256_at_resolution` hex64. Trial chain only |',
    '| T34 | `anchor_receipt_rejected` | D | *(Amendment 2026-09-24, pre-outcome; root %s and %s; protocol 12.4 and 12.2 row 30)* `request_id` hex32?; `reason` enum[`unknown_request`,`stale`,`malformed`,`duplicate`,`conflict`]; `raw_sha256` hex64; `raw_bytes` int. Neither trial-only nor program-only: written wherever anchor events are (also beside P8) |' % (R0254, R0324),
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 1, 3 and 4,' % R2040,
    'and the rulings of 21:14, 02:54 and 03:24), to rows T3, T17, T22, T23, T29b and T31 and to P6.*',
    'T17 `episode_revealed` gains',
    '`usage_complete` bool and `unknown_usage_calls` int; T22 `anchor` gains `request_id` hex32 (optional in the',
    'schema); T23 `anchor_receipt` gains `request_id` hex32, `anchor_file_sha256` hex64?, `comment_body_sha256` hex64?',
    'and `node_id_sha256` hex64? (all optional; the last three non-null only on a verified decision receipt); T29b',
    '`deposit_sealed` gains `late_unread` [obj] (optional); T31 `trial_ended` / `trial_aborted` gains `completion` obj',
    'and `resolution` obj (optional in the schema, written on every terminal record), and its `reason` gains',
    '`server_restart_cap` and `unresolved_worker` (automatic aborts, protocol 6.4). The preflight check enum shared by',
    'T3 `invocation_refused` and P6 `preflight_refused` gains `golden_objects`. The pure function',
    '`phase_resolution_verdict(...)` is evaluated before every terminal record of a trial; `lab_verify_log` mirrors',
    'it as the FAIL-level check `workers.resolved`, checks T4, T7, T8, T32 and `completion` against protocol 5.3 as',
    'the FAIL-level check `server.lifecycle`, and its FAIL-level check `switch.phase` counts a decision as receipted',
    'only by `lab_eventlog.decision_receipt` (protocol 12.4).',
)
A_6_3 = _lines(
    '',
    '*Amendment 2026-09-24 (pre-outcome; root %s items 2 and 4, and' % R2040,
    '%s;' % R0153,
    'protocol 14.3):* this list gains `server_supervision` (top level, outside the rule block: bound by',
    '`config_sha256` and `harness_file_sha256[config.json]`, not by `rule_block_sha256`),',
    '`prefreeze.conformance_prompts` and `llama_cpp.serving_manifest_sha256`, the canonical digest of the write-once',
    'artifact `results/live_ab/freeze/serving_manifest.json` (2.2).',
    '',
)
A_7_1_1B = _lines(
    '| 1b | `PREFLIGHT` | *(Amendment 2026-09-24, pre-outcome; root %s item 1, and %s)* on a non-simulated path: a golden file is null, missing, unreadable or does not match its config digest, a golden `model_path` is not tokenized, a `--gguf` path does not tokenize to the golden `model_path`, or a runtime `golden` override is present (check `golden_objects`); the artifact `results/live_ab/freeze/serving_manifest.json` is missing, not a regular canonical file, not the file of `llama_cpp.serving_manifest_sha256` (null refuses) or does not re-verify against the runtime (check `serving_manifest`); `server_supervision` or `execution.health_failures_to_down` is absent or malformed (`preflight_rule_failed`) | before seq 0 append `preflight_refused` with the check to the **program** chain (D), at a later invocation `invocation_refused` (protocol 6.4 row 21); no server is started and nothing success-valued is written | `ABORTED` | — |' % (R2040, R0153),
)
A_7_1_14C = _lines(
    '| 14c | `ANCHOR_BLOCK` | *(Amendment 2026-09-24, pre-outcome; root %s and %s; protocol 12.4)* a receipt spool line arrives, or a supervision outcome is owed | exactly one chain event per line (D): `anchor_receipt` only when the line\'s `request_id` is bound to that anchor\'s durable request and, for the decision anchor, it carries the full external evidence of protocol 12.4; otherwise `anchor_failed` or `anchor_receipt_rejected`, and the anchor stays pending. The servers stay supervised. Row 14 is taken only once `lab_eventlog.decision_receipt` finds the decision receipted; a supervision outcome owed while the decision was provisional is taken then, before any switch (protocol 5.3 case (c)); a decision anchor that came back failed, or no receipt within `blocking_wait_minutes`, is row 14a with the outcome still owed | `ANCHOR_BLOCK` / `POST_DECISION` / `PAUSED` / `ABORTED` | **yes** |' % (R0254, R0324),
)
A_7_1_20A = _lines(
    '| 20a | any | *(Amendment 2026-09-24; root %s item 1)* `lab_server.start` or `lab_server.restart` raises `ServerStartFailed` | `server_start_failed` (D) with the exception\'s record, never a success-valued T4 or T8; then the rule for its stage (protocol 5.3): `gguf`, `serving_manifest` or `identity` → `trial_aborted(server_identity)` (D); `smoke` → `trial_aborted(receipt_mismatch)` (D), both when the smoke receipt differs from the golden object and when none was obtained (`smoke_transport`, `smoke_no_usage`; the latter is a new automatic abort, protocol 6.4); `launch` or `health` on a supervised restart or a start at resume → `trial_paused(server_unrecoverable)` (D), on the first start → `trial_aborted(infrastructure)` (D; a new automatic abort, protocol 6.4). A refused start call or an exception the start did not convert → `trial_aborted(harness_defect)` (D). A failed restart counts towards the cap (row 21a) | `ABORTED` / `PAUSED` | — |' % R2040,
)
A_7_1_21AB = _lines(
    '| 21a | any | *(Amendment 2026-09-24; root %s item 4, and %s)* `server_down` on a server whose supervised restart attempts in this trial (`server_restarted` plus `server_start_failed` with `kind` `restart`, counted from the chain) already equal `server_supervision.max_supervised_restarts_per_server_per_trial` (3) | nothing is restarted and nothing new is dispatched; the open attempts drain (the `episode_hard_cap_s` kill still applies) and are revealed (D); every worker is resolved (row 21b); then `trial_aborted(server_restart_cap)` (D) with `completion` + blocking anchor. The case is fixed by the chain at that `server_down` (protocol 5.3): (a) no decision yet → none is taken afterwards, a crossing look is logged unchanged and not acted on; (b) a decision with its chained external receipt → it stands at its `tau`, the follow-up is truncated and counted; (c) a decision awaiting its receipt → the abort waits in `ANCHOR_BLOCK` (row 14c) and is taken only after the receipt, else row 14a pauses with the abort still owed. No replacement trial, no extra pair | `ABORTED` / `PAUSED` | **yes** |' % (R2040, R2114),
    '| 21b | `CLOSING`, `ABORTED` | *(Amendment 2026-09-24; root %s item 3)* before the terminal record, after the bounded drain, the idle observation of every held server and the deposit seal: `phase_resolution_verdict` does not pass (a worker not confirmed exited, a started call with no terminal event under an unresolved worker, a spool grown or changed past its resolution offset, a held server busy or unobserved) | no `trial_ended`: `trial_aborted(unresolved_worker)` (D) + blocking anchor, whose `resolution` lists every unresolved attempt and unfinished call (usage `null`) and names the reason it superseded | `ABORTED` | **yes** |' % R2040,
)


class Insertion:
    """One pure insertion: ``text`` goes directly ``side`` ('after' / 'after-line' / 'before')
    the unique ``anchor`` of document ``doc``, inside the section headed ``section`` (whose
    upper bound must be the heading ``section_end``); ``fence`` means it must also lie inside
    that section's ```json fence."""

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


class Replacement:
    """The ONE in-place change: in document ``doc`` the bytes ``old`` (which must occur
    exactly once, inside the ```json fence of ``section`` when one is named) become ``new``."""

    def __init__(self, key, doc, old, new, section=None, section_end=None, fence=False):
        self.key, self.doc, self.old, self.new = key, doc, old, new
        self.section, self.section_end, self.fence = section, section_end, fence

    def describe(self) -> dict:
        return {'key': self.key, 'document': self.doc, 'old': self.old.decode('utf-8'),
                'new': self.new.decode('utf-8'),
                'section': self.section.decode('utf-8') if self.section else None,
                'inside_json_fence': self.fence,
                'old_sha256': sha(self.old), 'new_sha256': sha(self.new)}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_APPB = (b'## Appendix B.', b'## Appendix C.')
_A61 = (ARCH_MARKER, b'### 6.2 The rule block')
_S71 = (b'### 7.1 States and transitions', b'### 7.2 What is fsynced, and when')

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
    Insertion('protocol.2_2', 'protocol',
              b'   | `props_build_info` | `/props.build_info`, which must contain the commit '
              b'prefix |\n', 'after', P_2_2,
              b'### 2.2 Serving software and the manifest fields that are pinned',
              b'### 2.3 Models'),
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
    Insertion('protocol.12_4', 'protocol',
              b'    because its URLs lack the real account and repository names).\n', 'after',
              P_12_4, b'### 12.4 Anchoring: mechanics',
              b'### 12.5 What the anchors prove, and what they do not'),
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
    Insertion('protocol.16', 'protocol',
              b'    **nothing is rerun to obtain a different answer**; deferred items listed as '
              b'deferred.\n', 'after', P_16,
              b'## 16. What is reported whatever the outcome', b'## Appendix A.'),
    # ARCHITECTURE prose
    Insertion('architecture.2_1', 'architecture', b'| `lab_server.py` | G4 | ', 'after-line',
              A_2_1, b'### 2.1 `experiments/live_ab/`', b'### 2.2 `results/live_ab/`'),
    Insertion('architecture.2_2', 'architecture',
              b'    golden_generation_settings_coder.json, golden_generation_settings_t3.json\n',
              'after', A_2_2, b'### 2.2 `results/live_ab/`', b'### 2.3 `work/live_ab/`'),
    Insertion('architecture.3_16.row', 'architecture', b'| lab_server | x | ', 'after-line',
              A_3_16_ROW, b'### 3.16 Import isolation matrix', b'### 3.17 `lab_hostcheck.py`'),
    Insertion('architecture.3_16.note', 'architecture', b'| build_live_ab_results | x | ',
              'after-line', A_3_16_NOTE, b'### 3.16 Import isolation matrix',
              b'### 3.17 `lab_hostcheck.py`'),
    Insertion('architecture.4_4', 'architecture', b'| T31 | `trial_ended` / `trial_aborted` | ',
              'after-line', A_4_4, b'### 4.4 Trial chain', b'### 4.5 `what_was_known`'),
    Insertion('architecture.6_3', 'architecture',
              b'code** (`refreeze.scope == ["reporting_code"]`), never a config key.\n', 'after',
              A_6_3, b'### 6.3 Keys that may never be amended after the first design outcome',
              b'## 7. Orchestrator state machine'),
    Insertion('architecture.7_1.row_1b', 'architecture', b'| 1a | `PREFLIGHT` | ', 'after-line',
              A_7_1_1B, *_S71),
    Insertion('architecture.7_1.row_14c', 'architecture', b'| 14b | `ANCHOR_BLOCK` | ',
              'after-line', A_7_1_14C, *_S71),
    Insertion('architecture.7_1.row_20a', 'architecture', b'| 20 | any | ', 'after-line',
              A_7_1_20A, *_S71),
    Insertion('architecture.7_1.rows_21a_21b', 'architecture', b'| 21 | any | ', 'after-line',
              A_7_1_21AB, *_S71),
)
DOC_NAMES = ('config', 'architecture', 'protocol')


def replacements(digest: str) -> tuple:
    """The one in-place change, in each of its three byte-identical copies."""
    new = (REPLACE_NEW_FMT % digest).encode('utf-8')
    return (Replacement('config.serving_manifest_sha256', 'config', REPLACE_OLD, new),
            Replacement('architecture.6_1.serving_manifest_sha256', 'architecture', REPLACE_OLD,
                        new, *_A61, fence=True),
            Replacement('protocol.appendix_b.serving_manifest_sha256', 'protocol', REPLACE_OLD,
                        new, *_APPB, fence=True))


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
# Anchors, insertion and the replacement
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


def site_facts(raw: bytes, rep: Replacement, *, which: str) -> dict:
    """Where ``rep.old`` (``which='old'``, the pre-image) or ``rep.new`` (``which='new'``, the
    amended document) lies in ``raw``: its count, and whether the one occurrence is inside
    the ```json fence of its section (config.json: the whole file)."""
    needle = rep.old if which == 'old' else rep.new
    out = {'occurrences': raw.count(needle),
           'other_occurrences': raw.count(rep.new if which == 'old' else rep.old)}
    i = raw.find(needle)
    if rep.section is None:
        out['inside_its_fence'] = i >= 0
    else:
        try:
            s0, s1 = section_span(raw, rep.section)
            f0, f1 = fence_span(raw, rep.section)
            out['inside_its_fence'] = (i >= 0 and raw.count(rep.section) == 1
                                       and raw[s1:s1 + len(rep.section_end)] == rep.section_end
                                       and s0 < f0 <= i and i + len(needle) <= f1 <= s1)
        except ValueError as e:
            out.update(error=str(e), inside_its_fence=False)
    out['ok'] = (out['occurrences'] == 1 and out['other_occurrences'] == 0
                 and out['inside_its_fence'] is True)
    return out


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


def replace_all(docs: dict, digest: str) -> dict:
    """The one in-place change in each document; ValueError unless ``old`` occurs once."""
    out = dict(docs)
    for rep in replacements(digest):
        if out[rep.doc].count(rep.old) != 1:
            raise ValueError('%s: the replaced bytes occur %d times'
                             % (rep.key, out[rep.doc].count(rep.old)))
        out[rep.doc] = out[rep.doc].replace(rep.old, rep.new, 1)
    return out


def amend(old: dict, digest: str) -> dict:
    return replace_all(insert_all(old), digest)


def remove_all(new_raw: bytes, doc: str, digest: str) -> bytes:
    """Undo: the replacement reverted (new -> old, once), every insertion deleted (once)."""
    for rep in replacements(digest):
        if rep.doc == doc:
            new_raw = new_raw.replace(rep.new, rep.old, 1)
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

    Every refusal of main() on a computed condition goes through a call of this function,
    with the checks named.  The witness module (tests_repair_amendment_v2.GateTests) wraps it
    to set ONE named check False on the pristine inputs, on which every other check is True,
    and requires main() to refuse; which REAL input makes each check False is listed, check by
    check, in the witness module's LIVENESS table (some checks are implied by others and have
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


def config_checks(old_cfg_raw: bytes, new_cfg_raw: bytes, digest: str) -> dict:
    try:
        old_cfg, new_cfg = json.loads(old_cfg_raw), json.loads(new_cfg_raw)
    except ValueError as e:
        return {'error': str(e), 'ok': False}
    fo, fn = flatten(old_cfg), flatten(new_cfg)
    added = sorted(set(fn) - set(fo))
    removed = sorted(set(fo) - set(fn))
    changed = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
    unchanged = {p: old_cfg.get(p) == new_cfg.get(p) for p in UNCHANGED_CONFIG_PATHS}
    lo = {k: v for k, v in (old_cfg.get('llama_cpp') or {}).items() if k != 'serving_manifest_sha256'}
    ln = {k: v for k, v in (new_cfg.get('llama_cpp') or {}).items() if k != 'serving_manifest_sha256'}
    unchanged['llama_cpp (without serving_manifest_sha256)'] = lo == ln
    prompts = new_cfg.get('prefreeze', {}).get('conformance_prompts')
    bound = bound_limits()
    ea = new_cfg.get('engineering_acquisition')
    ea_equals = (isinstance(ea, dict) and bound is not None and set(ea) == set(bound)
                 and all(not isinstance(ea[k], bool) and float(ea[k]) == float(bound[k])
                         for k in bound))
    out = {
        'added_keys': added, 'removed_keys': removed, 'changed_keys': changed,
        'serving_manifest_sha256_before': (old_cfg.get('llama_cpp') or {}).get(
            'serving_manifest_sha256', 'ABSENT'),
        'serving_manifest_sha256_after': (new_cfg.get('llama_cpp') or {}).get(
            'serving_manifest_sha256', 'ABSENT'),
        'server_supervision_is_the_contract_value': new_cfg.get('server_supervision')
        == SERVER_SUPERVISION,
        'conformance_prompts_equal_the_tool_texts': prompts == [dict(p) for p in PROMPTS],
        'subtrees_unchanged': unchanged,
        'engineering_acquisition_equals_run_smoke_BOUND_LIMITS': ea_equals,
        'rule_block_sha256_before': lab_common.rule_block_sha256(old_cfg),
        'rule_block_sha256_after': lab_common.rule_block_sha256(new_cfg),
        'reverting_the_changes_reproduces_the_prior_config': (
            sha(remove_all(new_cfg_raw, 'config', digest)) == PRIOR_CONFIG_SHA256),
    }
    out['gate'] = {
        'exactly_the_three_keys_added': added == ADDED_CONFIG_KEYS,
        'no_key_removed': not removed,
        'only_the_serving_manifest_digest_changed': changed == CHANGED_CONFIG_KEYS,
        'serving_manifest_digest_was_null': out['serving_manifest_sha256_before'] is None,
        'serving_manifest_digest_is_the_artifact': out['serving_manifest_sha256_after'] == digest,
        'server_supervision_is_the_contract_value':
            bool(out['server_supervision_is_the_contract_value']),
        'conformance_prompts_equal_the_tool_texts':
            bool(out['conformance_prompts_equal_the_tool_texts']),
        'pinned_subtrees_unchanged': all(unchanged.values()),
        'engineering_acquisition_equals_run_smoke_BOUND_LIMITS': bool(ea_equals),
        'rule_block_before_is_the_pin': out['rule_block_sha256_before'] == PRIOR_RULE_BLOCK,
        'rule_block_after_is_the_pin': out['rule_block_sha256_after'] == PRIOR_RULE_BLOCK,
        'reverting_the_changes_reproduces_the_prior_config':
            bool(out['reverting_the_changes_reproduces_the_prior_config']),
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
            spec = importlib.util.spec_from_file_location('run_smoke_for_repair_amendment_v2',
                                                          SERVING / 'run_smoke.py')
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _BOUND.append(dict(mod.BOUND_LIMITS))
        except Exception:                                      # noqa: BLE001
            return None
    return dict(_BOUND[0])


def postconditions(old: dict, new: dict, digest: str) -> tuple:
    """(post, ok) for candidate documents ``new`` against the pre-images ``old``
    ({'config', 'architecture', 'protocol'} -> bytes). The acceptance predicate
    main() applies before writing, and the one the negative control must fail."""
    where = {ins.key: placement(new[ins.doc], ins) for ins in INSERTIONS}
    sites = {rep.key: site_facts(new[rep.doc], rep, which='new') for rep in replacements(digest)}
    additive = {d: (all(new[d].count(ins.text) == 1 for ins in INSERTIONS if ins.doc == d)
                    and remove_all(new[d], d, digest) == old[d]) for d in DOC_NAMES}
    try:
        vo, vn = vocab_sections(old['protocol']), vocab_sections(new['protocol'])
        vocab = {str(n): vo[n] == vn[n] for n in VOCAB_MARKERS}
    except ValueError as e:
        vocab = {'error': str(e)}
    after = contract(new['config'], new['architecture'], new['protocol'])
    cfg = config_checks(old['config'], new['config'], digest)
    post = {
        'config_sha256': sha(new['config']), 'config_bytes': len(new['config']),
        'architecture_sha256': sha(new['architecture']),
        'protocol_sha256': sha(new['protocol']), 'protocol_bytes': len(new['protocol']),
        'reverting_the_changes_reproduces_each_preimage': additive,
        'insertion_placement': where,
        'every_insertion_inside_its_section_beside_its_anchor': {
            k: bool(v.get('occurrences') == 1 and v.get('inside_its_section')
                    and v.get('directly_beside_the_anchor')) for k, v in where.items()},
        'replacement_sites': sites,
        'cr_bytes_after': {d: new[d].count(b'\r') for d in DOC_NAMES},
        'three_way_contract_after': after,
        'vocabulary_sections_1_3_11_byte_identical': vocab,
        'config': cfg,
    }
    post['gate'] = {
        'reverting_the_changes_reproduces_each_preimage': all(additive.values()),
        'every_insertion_inside_its_section_beside_its_anchor':
            all(post['every_insertion_inside_its_section_beside_its_anchor'].values()),
        'every_replacement_once_inside_its_fence': all(s['ok'] for s in sites.values()),
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


def negative_control(old: dict, new: dict, digest: str) -> dict:
    """Scratch copies in a fresh temporary directory, never the real files: the
    pre-images and one moved variant per document insertion are written there, read
    back, and the acceptance predicate is applied. Each variant must be refused."""
    real = {p.name: sha(p.read_bytes()) for p in (CONFIG, ARCH, PROTO, CELLS)}
    tmp = Path(tempfile.mkdtemp(prefix='repair_amendment_v2_negative_control_'))
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
            post, ok = postconditions(scratch, variant, digest)
            pl = post['insertion_placement'][ins.key]
            out['variants'][ins.key] = {
                'sha256': sha(variant[ins.doc]),
                'reverting_the_changes_reproduces_the_preimage':
                    post['reverting_the_changes_reproduces_each_preimage'][ins.doc],
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
    (table rows and configuration lines excepted); no anchor and no replaced bytes."""
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
            'contains_no_replaced_bytes': REPLACE_OLD not in ins.text
            and b'"serving_manifest_sha256": "' not in ins.text,
        }
    ok = all(v['ends_with_a_newline'] and v['cr_bytes'] == 0 and v['no_trailing_whitespace']
             and v['no_backtick_fence'] and v['max_prose_line_chars'] <= 120
             and v['contains_no_anchor'] and v['contains_no_replaced_bytes']
             and set(v['non_ascii']) <= {'→', '—'}
             for v in out.values())
    return {'per_insertion': out, 'ok': ok}


# ---------------------------------------------------------------------------
# The conformance prompts, checked against the pinned sources (the predecessor's rule)
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
    spec = importlib.util.spec_from_file_location('agent_for_repair_amendment_v2',
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
# The withdrawn predecessor, from git
# ---------------------------------------------------------------------------
def predecessor_checks() -> dict:
    """Each receipt of the withdrawn predecessor, as committed, hashes to its pinned digest,
    and neither of its commits is an ancestor of HEAD: it was never applied here."""
    out = {'receipts': [], 'ancestry': {}}
    for rec in WITHDRAWN_PREDECESSOR['receipts']:
        try:
            got = sha(git_blob(rec['commit'], rec['path']))
        except (OSError, subprocess.CalledProcessError):
            got = None
        out['receipts'].append({'path': rec['path'], 'sha256_found': got,
                                'is_the_pinned_bytes': got == rec['sha256']})
    for c in WITHDRAWN_PREDECESSOR['commits']:
        out['ancestry'][c] = git_is_ancestor(c, 'HEAD')
    out['gate'] = {
        'first_receipt_is_the_pinned_bytes': out['receipts'][0]['is_the_pinned_bytes'],
        'correction_receipt_is_the_pinned_bytes': out['receipts'][1]['is_the_pinned_bytes'],
        'predecessor_not_merged_into_this_branch': all(
            v is False for v in out['ancestry'].values()),
    }
    return out


# ---------------------------------------------------------------------------
# The real serving manifest, as seen from the main checkout (read only there)
# ---------------------------------------------------------------------------
def main_paths(main_root: str) -> dict:
    root = Path(main_root)
    return {'root': root, 'build_dir': root / DURABLE_BUILD_REL, 'launcher': root / LAUNCHER_REL,
            'build_receipt': root / BUILD_RECEIPT_REL, 'patch': root / PATCH_REL,
            'declaration': root / DECLARATION_REL}


def provenance_of(main_root: str) -> dict:
    """Role -> path of the provenance files, by the assembler tool's own rule
    (``assemble_serving_manifest.provenance_paths``: logs beside the receipt)."""
    mp = main_paths(main_root)
    return asm.provenance_paths(argparse.Namespace(
        build_dir=str(mp['build_dir']), build_receipt=str(mp['build_receipt']),
        build_log=None, configure_log=None, patch=str(mp['patch'])))


def assemble_as_seen_from(main_root: str, commit: str) -> tuple:
    """``(manifest or None, problems)``: ``lab_serving_manifest.assemble`` of the durable
    build of ``main_root`` with the token roots of that checkout (``asm.repo_roots``)."""
    launcher = main_paths(main_root)['launcher']
    with asm.repo_roots(main_root):
        try:
            return sm.assemble(launcher, provenance_of(main_root), llama_commit=commit), []
        except sm.ManifestError as exc:
            return None, list(exc.problems)


def runtime_as_seen_from(root: str | None, manifest: dict, main_root: str,
                         commit: str) -> list:
    """``lab_serving_manifest.runtime_problems`` of ``manifest`` against the durable launcher,
    with the token roots of ``root`` (``None``: this checkout's own roots)."""
    launcher = main_paths(main_root)['launcher']
    with asm.repo_roots(root):
        return sm.runtime_problems(manifest, launcher=launcher, llama_commit=commit)


def verify_before_launch_as_seen_from(root: str, path: Path, expected: object,
                                      main_root: str, commit: str) -> list:
    """``lab_serving_manifest.verify_before_launch`` -- what preflight and every
    ``lab_server`` start and restart call -- of the artifact at ``path`` against
    ``expected``, as seen from ``root``.  Reads files; starts nothing."""
    launcher = main_paths(main_root)['launcher']
    with asm.repo_roots(root):
        _manifest, labels = sm.verify_before_launch(path, expected, launcher=launcher,
                                                    llama_commit=commit)
    return list(labels)


def mutate(manifest: dict) -> dict:
    """A copy in which ONE library's digest is changed in one hex digit CONSISTENTLY, wherever
    the manifest records it (``libraries``, the closure's ``files``, the build's
    ``receipt_members``), so that the copy is internally consistent
    (``lab_serving_manifest.structure_problems`` finds nothing) and only the runtime
    measurement -- the member re-hashed, the receipt re-read -- can refuse it."""
    out = copy.deepcopy(manifest)
    lib = out['libraries'][MUTATED_LIBRARY_INDEX]
    old = lib['sha256']
    new = ('0' if old[0] != '0' else '1') + old[1:]
    lib['sha256'] = new
    for rec in out['closure']['files']:
        if rec['path'] == lib['name']:
            rec['sha256'] = new
    for rec in out['build']['receipt_members']:
        if rec['path'] == lib['name']:
            rec['sha256'] = new
    return out


def declared_facts(declaration: dict, main_root: str) -> dict:
    """What the durable declaration names, tokenized as seen from ``main_root``: the launcher
    ``{path, bytes, sha256}``, the non-system libraries ``{canonical path: sha256}`` and the
    rebuild receipt digest."""
    inst = declaration.get('candidate_instrument') or {}
    with asm.repo_roots(main_root):
        launcher = inst.get('launcher') or {}
        try:
            lpath = lab_common.tokenize_path(str(launcher.get('path')))
        except lab_common.UntokenizablePath:
            lpath = None
        libs = {}
        for rec in (inst.get('library_closure') or {}).values():
            if rec.get('system_library'):
                continue
            try:
                libs[lab_common.tokenize_path(str(rec.get('canonical')))] = rec.get('sha256')
            except lab_common.UntokenizablePath:
                libs['<untokenizable>'] = rec.get('sha256')
    return {'launcher': {'path': lpath, 'bytes': launcher.get('bytes'),
                         'sha256': launcher.get('sha256')},
            'libraries': libs,
            'rebuild_receipt_sha256': (declaration.get('rebuild_receipt') or {}).get('sha256')}


def main_checkout_checks(main_root: str) -> dict:
    """The pinned root and what the manifest will be assembled from; reads only."""
    mp = main_paths(main_root)
    out = {'root': lab_common.display_path(mp['root']),
           'root_problems': asm.repo_root_problems(main_root) if os.path.isdir(main_root)
           else ['repo_root_missing'],
           'loader_environment': sorted(k for k in os.environ
                                        if k.startswith(('GGML_', 'DYLD_'))),
           'tracked_provenance': {}}
    for rel in TRACKED_PROVENANCE:
        a, b = mp['root'] / rel, SOURCE_REPO / rel
        try:
            ra, rb = a.read_bytes(), b.read_bytes()
            out['tracked_provenance'][rel] = {'sha256_main': sha(ra), 'sha256_this_checkout': sha(rb),
                                              'equal': ra == rb}
        except OSError as e:
            out['tracked_provenance'][rel] = {'error': type(e).__name__, 'equal': False}
    decl = out['tracked_provenance'].get(DECLARATION_REL, {})
    out['gate'] = {
        'is_the_pinned_root': main_root == MAIN_CHECKOUT,
        'root_definitions_hold': out['root_problems'] == [],
        'durable_launcher_present': mp['launcher'].is_file(),
        'provenance_files_equal_this_checkout': all(
            v.get('equal') is True for k, v in out['tracked_provenance'].items()
            if k != DECLARATION_REL),
        'declaration_is_the_pinned_bytes_in_both': (
            decl.get('equal') is True and decl.get('sha256_main') == DECLARATION_SHA256),
        'no_loader_environment': not out['loader_environment'],
    }
    return out


def manifest_checks(main_root: str, commit: str, declaration_path=None) -> dict:
    """Assemble THE manifest as seen from ``main_root`` and establish, before anything is
    written, what the receipt claims about it.  Starts no server; writes only scratch files.
    ``declaration_path``: the durable declaration to compare with (default: the one in the
    main checkout, which :func:`main_checkout_checks` requires to be the pinned bytes)."""
    out: dict = {'gate': {}}
    manifest, problems = assemble_as_seen_from(main_root, commit)
    out['assembly_problems'] = problems
    if manifest is None:
        out['gate'] = {k: False for k in MANIFEST_CHECKS}
        return out
    digest = lab_common.sha256_canonical(manifest)
    again, again_problems = assemble_as_seen_from(main_root, commit)
    try:
        declaration = json.loads(Path(declaration_path or main_paths(main_root)['declaration'])
                                 .read_text('utf-8'))
    except (OSError, ValueError):
        declaration = {}
    declared = declared_facts(declaration, main_root)
    closure_libs = {f['path']: f['sha256'] for f in manifest['closure']['files']
                    if f['path'] != manifest['closure']['root']}
    reverify = runtime_as_seen_from(main_root, manifest, main_root, commit)
    from_here = runtime_as_seen_from(None, manifest, main_root, commit)
    tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='repair_amendment_v2_manifest_')))
    try:
        # another checkout: a fresh, empty directory standing for any root but the main
        # checkout; the manifest's <REPO>/<RESULTS> tokens resolve there to nothing
        other_root = tmp / 'another_checkout'
        other_root.mkdir()
        from_other = runtime_as_seen_from(str(other_root), manifest, main_root, commit)
        good = sm.artifact_path(tmp / 'good' / sm.FREEZE_DIR_NAME)
        bad = sm.artifact_path(tmp / 'mutated' / sm.FREEZE_DIR_NAME)
        mutated = mutate(manifest)
        mutated_structure = sm.structure_problems(mutated, commit)
        good_digest = sm.write_artifact(good, manifest)
        bad_digest = sm.write_artifact(bad, mutated)
        scratch = verify_before_launch_as_seen_from(main_root, good, digest, main_root, commit)
        by_digest = verify_before_launch_as_seen_from(main_root, bad, digest, main_root, commit)
        at_runtime = verify_before_launch_as_seen_from(main_root, bad, bad_digest, main_root,
                                                       commit)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out.update({
        'manifest': manifest, 'sha256_canonical': digest,
        'bytes': len(lab_common.canonical_json(manifest)) + 1,
        'libraries': len(manifest['libraries']),
        'metal_library_kind': (manifest.get('metal_library') or {}).get('kind'),
        'second_assembly_sha256': (lab_common.sha256_canonical(again) if again is not None
                                   else None),
        'second_assembly_problems': again_problems,
        'declared': declared,
        'reverify_as_seen_from_the_main_checkout': reverify,
        'reverify_as_seen_from_this_checkout': from_here,
        'reverify_as_seen_from_another_checkout': from_other,
        'scratch_copy_verify_before_launch': scratch,
        'mutated_copy': {'mutation': ('the digest of libraries[%d] changed in one hex digit, '
                                      'consistently in libraries, closure.files and '
                                      'build.receipt_members' % MUTATED_LIBRARY_INDEX),
                         'structure_problems': mutated_structure,
                         'sha256_canonical': bad_digest,
                         'against_the_real_digest': by_digest,
                         'against_its_own_digest': at_runtime},
        'scratch_copy_sha256_canonical': good_digest,
    })
    out['gate'] = {
        'assembled': True,
        'reverifies_at_once_from_the_main_checkout': reverify == [],
        'assembly_is_deterministic': out['second_assembly_sha256'] == digest,
        'launcher_is_the_declared_launcher': (
            dict(manifest['launcher']) == declared['launcher']),
        'libraries_are_the_declared_closure': (
            bool(declared['libraries']) and closure_libs == declared['libraries']),
        'build_receipt_is_the_declared_receipt': (
            ((manifest['build'].get('files') or {}).get('build_receipt') or {}).get('sha256')
            == declared['rebuild_receipt_sha256'] is not None),
        'commit_is_the_config_commit': manifest.get('llama_cpp_commit') == commit,
        'refused_as_seen_from_another_checkout': bool(from_other),
        'mutated_copy_refused_by_digest': 'digest' in by_digest,
        'mutated_copy_refused_at_runtime': (bool(at_runtime) and mutated_structure == []
                                            and bad_digest != digest),
        'scratch_copy_verifies_before_launch': scratch == [] and good_digest == digest,
    }
    return out


MANIFEST_CHECKS = ('assembled', 'reverifies_at_once_from_the_main_checkout',
                   'assembly_is_deterministic', 'launcher_is_the_declared_launcher',
                   'libraries_are_the_declared_closure', 'build_receipt_is_the_declared_receipt',
                   'commit_is_the_config_commit', 'refused_as_seen_from_another_checkout',
                   'mutated_copy_refused_by_digest', 'mutated_copy_refused_at_runtime',
                   'scratch_copy_verifies_before_launch')


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
    ap.add_argument('--sources-dir', default=str(DEFAULT_SOURCES_DIR),
                    help='directory holding sanitized-mbpp.json, HumanEval.jsonl.gz and '
                         'mbpp.jsonl, byte copies of the pinned roster sources')
    ap.add_argument('--repo-root', default=MAIN_CHECKOUT,
                    help='the checkout that runs the trials (pinned: %s); read only' % MAIN_CHECKOUT)
    args = ap.parse_args(argv)
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / (RECEIPT_PREFIX + '%s.json' % stamp)
    artifact = REPO / ARTIFACT_REL
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
        return _refuse('cells.json unreadable (%s)' % e)
    before = contract(old['config'], old['architecture'], old['protocol'])
    anchors = {ins.key: anchor_facts(old[ins.doc], ins) for ins in INSERTIONS}
    sites_before = {rep.key: site_facts(old[rep.doc], rep, which='old')
                    for rep in replacements('0' * 64)}
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
        'replacement_sites_before': sites_before,
        'inserted_text_form': form,
        'head': git('rev-parse', 'HEAD'),
    }
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
        return _refuse('a precondition failed', pre)
    if any(a['text_already_present'] for a in anchors.values()):
        return _refuse('the amendment is already present')
    pre['gate_anchors'] = {
        'every_anchor_once': all(a.get('anchor_occurrences') == 1 for a in anchors.values()),
        'no_anchor_error': all('error' not in a for a in anchors.values()),
        'every_anchor_inside_its_section': all(a.get('inside_its_section', True) is True
                                               for a in anchors.values()),
        'every_replacement_site_once_inside_its_fence': all(
            s['ok'] for s in sites_before.values()),
        'inserted_text_form': form['ok'] is True,
    }
    if not gate('anchors', pre['gate_anchors']):
        return _refuse('a precondition failed', pre)

    # -- 2. the four prompts, against the pinned sources -------------------------
    old_cfg = json.loads(old['config'])
    try:
        sources = load_sources(Path(args.sources_dir), old_cfg['roster']['sources'])
    except (ValueError, OSError, KeyError) as e:
        return _refuse('the pinned roster sources could not be read (%s)' % e)
    prompt_check = check_prompts(sources, list(old_cfg['roster']['smoke_tasks']))
    if not prompt_check['all_pass']:
        return _refuse('a conformance prompt failed the stated rule', prompt_check)

    # -- 3. the withdrawn predecessor, from git ------------------------------------
    predecessor = predecessor_checks()
    if not gate('withdrawn_predecessor', predecessor['gate']):
        return _refuse('the withdrawn predecessor is not as pinned', predecessor)

    # -- 4. the real serving manifest, as seen from the main checkout ---------------
    commit = str((old_cfg.get('llama_cpp') or {}).get('commit'))
    main_root = str(args.repo_root)
    main_facts = main_checkout_checks(main_root)
    if not gate('main_checkout', main_facts['gate']):
        return _refuse('the main checkout cannot stand for the trial checkout', main_facts)
    mfacts = manifest_checks(main_root, commit)
    if not gate('manifest', mfacts['gate']):
        return _refuse('the serving manifest did not verify as seen from the main checkout',
                       {k: v for k, v in mfacts.items() if k != 'manifest'})
    manifest, digest = mfacts['manifest'], mfacts['sha256_canonical']

    # -- 5. insert and replace, as bytes ------------------------------------------
    try:
        new = amend(old, digest)
    except ValueError as e:
        return _refuse(str(e))

    # -- 6. postconditions, computed BEFORE anything is written ------------------
    post, ok = postconditions(old, new, digest)
    if not ok:
        return _refuse('a postcondition failed', post)
    control = negative_control(old, new, digest)
    control['gate'] = {
        'every_variant_refused_on_placement': control['every_variant_refused_on_placement'],
        'scratch_copies_unchanged': control['scratch_copies_unchanged'] is True,
        'real_documents_unchanged': control['real_documents_unchanged'] is True,
    }
    if not gate('negative_control', control['gate']):
        return _refuse('the negative control did not refuse', control)

    # -- 7. the successor, additively --------------------------------------------
    verified_commit_hash = sha(git_blob(PRIOR_SUCCESSOR_COMMIT, REL_PROTO))
    commit_gate = {'prior_successor_commit_carries_the_prior_successor':
                   verified_commit_hash == PRIOR_SUCCESSOR}
    if not gate('successor_commit', commit_gate):
        print('refusing: %s does not carry the prior successor; NOTHING was written'
              % PRIOR_SUCCESSOR_COMMIT, file=sys.stderr)
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
            'NOT Appendix-B-only: the one synchronized pre-outcome amendment of the EB1+EB5 '
            'repair subset (v2), applied to config.json, ARCHITECTURE_FINAL.md and '
            'protocol_FINAL.md. Every change is a pure insertion except ONE in-place value: '
            'llama_cpp.serving_manifest_sha256, null before, now the canonical digest of the '
            'write-once artifact results/live_ab/freeze/serving_manifest.json, in the three '
            'byte-identical configuration copies. Reverting that value and deleting the '
            'inserted text reproduces the prior successor 64ace6d3 byte for byte. Appendix B '
            'gains the four out-of-design format-conformance prompts at '
            'prefreeze.conformance_prompts (ids oodp/1..oodp/4) and the top-level key '
            'server_supervision {"max_supervised_restarts_per_server_per_trial": 3, '
            '"on_exceeding": "abort_trial_incomplete"}, outside the rule block. Dated prose is '
            'inserted into 2.2 (the serving-manifest artifact and its re-verification), 2.4 '
            'item 6, 5.3 (the restart cap and root\'s three restart-cap cases, cap invariance '
            'and completion reporting, the real server start and its refusals, the '
            'golden_objects refusal), 5.8, 6.4 (new automatic aborts), 12.2 (rows '
            'server_start_failed, worker_resolved, anchor_receipt_rejected and the new fields), '
            '12.4 (receipt attribution and the decision receipt, with no timestamp authority), '
            '13.1 (usage_complete, unknown_usage_calls), 14.3, 14.6 (every worker resolved '
            'before a terminal record) and 16. It ADDS execution and failure-to-outcome rules: '
            'four new automatic aborts, trial_aborted(server_restart_cap), '
            'trial_aborted(unresolved_worker), trial_aborted(infrastructure) for a first start '
            'that fails at launch or health, and trial_aborted(receipt_mismatch) for a '
            'SERVER_SMOKE that yields no receipt; and it states the reporting rule of root\'s '
            '21:14 ruling for a restart-cap abort (before a valid decision: no decision; after '
            'a logged and externally receipted decision: that decision stands at its original '
            'tau and the follow-up is truncated; while the decision awaits its blocking '
            'receipt: provisional). It changes no CPU cell, parameter, seed, horizon, estimator, '
            'outcome definition, monitor or decision threshold, alpha, margin or sampling '
            'parameter, and none of the vocabulary sections 1, 3 and 11 this pin reads '
            '(verified byte-identical). The rule-block keys are byte-unchanged (digest '
            'cbfd1792); that digest covers neither server_supervision nor '
            'llama_cpp.serving_manifest_sha256 nor any protocol text, so it does not show the '
            'absence of the changes listed here. A predecessor of this amendment (branch '
            'session60/repair-amend, commits 1349619 and ff152e9, protocol digests 25014221 and '
            '5d108b4a) was withdrawn and never applied; neither of its digests entered this '
            'history, and its receipts are named in REPAIR_AMENDMENT_V2_RECEIPT.'),
        'ruling': (
            'Root 2026-09-23 20:40 (reviews/prerun_bundle_go_nogo_20260923_2040.md) items 2 and '
            '4 (lines 17 and 19; items 1 and 3 fix the server lifecycle and worker resolution); '
            'root 2026-09-23 21:14 (reviews/restart_cap_estimand_ruling_20260923_2114.md), the '
            'three restart-cap cases; root 2026-09-24 01:53 '
            '(reviews/serving_manifest_binding_ruling_20260924_0153.md), the one write-once '
            'serving-manifest artifact bound by its config digest; root 2026-09-24 02:54 and '
            '03:24 (reviews/eb1_receipt_attribution_review_20260924_0254.md, '
            'reviews/decision_receipt_metadata_ruling_20260924_0324.md), receipt attribution and '
            'the decision receipt, and the delivery of this amendment with the real manifest in '
            'the EB1+EB5 subset. The pin amendment follows the standing root ruling of '
            '2026-09-22 04:27 (reviews/protocol_pin_disposition_20260922_0422.md): "preserve the '
            'original pin; record an explicit post-freeze provenance amendment ... Do not '
            'replace the original sha256."'),
        'what_this_is_not': (
            'Not a freeze, not trial, stage or launch approval, not a CPU rerun, and not the '
            'code of the EB1+EB5 subset (the orchestrator, server, event-schema, verifier, '
            'builder and load-ledger changes are separate commits that move the harness pin). '
            'It certifies no server start, no worker resolution and no prompt outcome: no '
            'server was started, and neither served model was run. The serving manifest was '
            'assembled from files (otool/nm metadata and bytes) and checked against files; it '
            'does not show which bytes the GPU executes. The four prompts were written by an '
            'implementing AI agent session under a selection rule stated ahead of the texts '
            '(that it preceded them in time is attested, not recorded); the mechanical checks '
            'are distinctness and similarity checks, not a proof that the tasks are unseen by '
            'any model.'),
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
        return _refuse('cells.json would change outside superseded_by')
    new_cells_raw = (json.dumps(new_cells, indent=1) + '\n').encode('utf-8')

    # -- 8. write: the artifact (write-once), then the documents, then the receipt --
    artifact_facts = {'path': ARTIFACT_REL}
    try:
        written_digest = sm.write_artifact(artifact, manifest)
        artifact_facts['write'] = 'written once (O_CREAT|O_EXCL), read back'
    except (sm.ManifestError, lab_common.WriteOnceViolation) as exc:
        written_digest = None
        artifact_facts['write'] = 'refused: %s' % type(exc).__name__
    artifact_facts['verify_before_launch_from_the_main_checkout'] = (
        verify_before_launch_as_seen_from(main_root, artifact, digest, main_root, commit)
        if written_digest is not None else ['not_written'])
    artifact_facts['gate'] = {
        'written_once_and_reads_back': written_digest == digest,
        'verifies_before_launch_from_the_main_checkout':
            artifact_facts['verify_before_launch_from_the_main_checkout'] == [],
    }
    if not gate('artifact', artifact_facts['gate']):
        print('refusing: the serving-manifest artifact was not written and verified; the four '
              'documents were NOT written: %s' % json.dumps(artifact_facts), file=sys.stderr)
        return 2
    harness_before = lab_common.harness_file_hashes()
    intended = {CONFIG: new['config'], ARCH: new['architecture'], PROTO: new['protocol'],
                CELLS: new_cells_raw}
    for path, raw in intended.items():
        path.write_bytes(raw)
    harness_after = lab_common.harness_file_hashes()
    on_disk = {'config': CONFIG.read_bytes(), 'architecture': ARCH.read_bytes(),
               'protocol': PROTO.read_bytes()}
    try:
        disk_digest = (json.loads(on_disk['config']).get('llama_cpp') or {}).get(
            'serving_manifest_sha256')
    except ValueError:
        disk_digest = None
    final_dry = verify_before_launch_as_seen_from(main_root, artifact, disk_digest, main_root,
                                                  commit)
    written = {
        'read_back_equals_computed': all(p.read_bytes() == raw for p, raw in intended.items()),
        'config_sha256': sha(on_disk['config']), 'config_bytes': len(on_disk['config']),
        'architecture_sha256': sha(on_disk['architecture']),
        'protocol_sha256': sha(on_disk['protocol']),
        'cells_sha256': sha(CELLS.read_bytes()),
        'artifact_file_sha256': sha(artifact.read_bytes()),
        'artifact_sha256_canonical': digest,
        'three_way_contract_on_disk': contract(on_disk['config'], on_disk['architecture'],
                                               on_disk['protocol']),
        'rule_block_sha256_on_disk': lab_common.rule_block_sha256(json.loads(on_disk['config'])),
        'harness_files_before': len(harness_before), 'harness_files_after': len(harness_after),
        'harness_entries_changed': sorted(k for k in set(harness_before) | set(harness_after)
                                          if harness_before.get(k) != harness_after.get(k)),
        'harness_file_sha256_config_before': harness_before.get('config.json'),
        'harness_file_sha256_config_after': harness_after.get('config.json'),
        'config_digest_on_disk': disk_digest,
        'dry_check_on_disk': final_dry,
    }
    written['gate'] = {
        'documents_read_back_equal_computed': written['read_back_equals_computed'] is True,
        'dry_check_against_the_config_on_disk': final_dry == [] and disk_digest == digest,
    }
    if not gate('final', written['gate']):
        print('refusing to write the receipt: the written documents or the artifact did not '
              'verify (the artifact and the documents ARE written; restore them from git): %s'
              % json.dumps(written), file=sys.stderr)
        return 2
    manifest_record = {k: v for k, v in mfacts.items() if k not in ('manifest',)}
    doc = {
        'schema': 'live_ab.repair_amendment_receipt.v2',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root: reviews/prerun_bundle_go_nogo_20260923_2040.md items 2 and 4; '
                      'reviews/restart_cap_estimand_ruling_20260923_2114.md; '
                      'reviews/serving_manifest_binding_ruling_20260924_0153.md; '
                      'reviews/eb1_receipt_attribution_review_20260924_0254.md; '
                      'reviews/decision_receipt_metadata_ruling_20260924_0324.md (quoted in '
                      'this tool\'s docstring)'),
        'prepared_by': ('prepared and checked by AI agent sessions; not human peer review or '
                        'author sign-off'),
        'withdrawn_predecessor': dict(WITHDRAWN_PREDECESSOR, verified_from_git=predecessor),
        'documents_amended_in_lockstep': [REL_CONFIG, REL_ARCH, REL_PROTO],
        'insertions': [ins.describe() for ins in INSERTIONS],
        'replacement': {
            'key': CHANGED_CONFIG_KEY, 'old_value': None, 'new_value': digest,
            'sites': [rep.describe() for rep in replacements(digest)],
            'why_not_an_insertion': (
                'the key llama_cpp.serving_manifest_sha256 exists in the pre-image with the '
                'value null ("null = pinned in the pre-freeze phase", Appendix B heading and '
                'Appendix A); root 01:53 requires the digest IN the config, so the value is '
                'replaced, not a key added. Deleting a key to insert it again would be a '
                'removal plus an insertion of the same key'),
            'bound_exactly': (
                'in each of config.json, the ARCHITECTURE 6.1 fence and the Appendix B fence '
                'the bytes %s occur exactly once, inside the fence, and become %s; the '
                'flattened key diff has exactly this one changed key (null before); reverting it '
                'and deleting the insertions reproduces each b049307 pre-image byte for byte'
                % (REPLACE_OLD.decode(), (REPLACE_NEW_FMT % digest))),
        },
        'serving_manifest': {
            'artifact': ARTIFACT_REL,
            'sha256_canonical': digest,
            'assembled_as_seen_from': {
                'repo_root': lab_common.display_path(Path(main_root)),
                'why': ('the trials run from the main checkout; lab_common tokenizes paths from '
                        'its own location, so the same files are <REPO>/work/llama.cpp-build/... '
                        'there but <HOME>/ICLR-WinRatioAgentEvals/work/... from any other '
                        'checkout. assemble_serving_manifest.repo_roots rebinds the three '
                        'token roots to the main checkout for the assembly and every check'),
                'main_checkout_checks': main_facts,
            },
            'durable_build': {'launcher': LAUNCHER_REL, 'build_receipt': BUILD_RECEIPT_REL,
                              'declaration': DECLARATION_REL,
                              'declaration_sha256': DECLARATION_SHA256},
            'evidence': manifest_record,
            'written': artifact_facts,
            'dry_check_after_writing': {
                'function': 'lab_serving_manifest.verify_before_launch (preflight at every '
                            'invocation, lab_server.start at every start and restart)',
                'as_seen_from': lab_common.display_path(Path(main_root)),
                'expected': 'llama_cpp.serving_manifest_sha256 of the written config.json',
                'labels': final_dry},
            'what_this_is_not': ('no server was started and nothing was executed or built: '
                                 'otool/nm metadata reads and file hashing only; the check does '
                                 'not show which bytes the GPU executes'),
        },
        'conformance_prompts': {
            '1_selection_rule': PROMPT_RULE,
            '2_texts': [dict(p) for p in PROMPTS],
            '3_mechanical_check_results': prompt_check,
        },
        'server_supervision': {
            'value': SERVER_SUPERVISION,
            'placement': ('a NEW top-level key, outside the rule block (not under '
                          'execution.auto_abort or plumbing_fail_conditions, which '
                          'rule_block_sha256 hashes); bound by config_sha256 and '
                          'harness_file_sha256[config.json]. The rule-block keys are '
                          'byte-unchanged (digest cbfd1792); that digest covers neither this key '
                          'nor any protocol text'),
            'what_counts': ('each supervised restart ATTEMPT per server per trial: a '
                            'server_restarted, or a server_start_failed with kind "restart"; '
                            'rebuilt from the chain on resume (lab_eventlog.'
                            'restart_cap_required_seq, lab_orchestrator.supervision_state)'),
            'reportability': ('root 21:14, three cases (protocol 5.3): before a valid decision, '
                              'none is made and the trial is incomplete; after a logged and '
                              'externally receipted decision, it stands at its original tau and '
                              'the follow-up is truncated and counted; while the decision awaits '
                              'its blocking receipt, it is provisional and the existing receipt / '
                              'pause rules apply'),
            'fixed_without_outcomes': 'no success or cost outcome exists; none was looked at',
        },
        'code_the_prose_describes': [
            'lab_eventlog: restart_cap_required_seq, restart_cap_case, decision_receipt, '
            'decision_receipt_problems, completion_record, COMPLETION, RESOLUTION, '
            'WORKER_RESOLVED_FIELDS, ANCHOR_RECEIPT_REJECTED_FIELDS, E_ABORT_REASON, E_PREFLIGHT',
            'lab_orchestrator: supervise_down, supervised_restart, raise_pending, _write_one_look, '
            'the ANCHOR_BLOCK transition, start_servers, resume_servers, START_FAILURE_REASON, '
            'judge_receipt_line, decision_evidence_verdict, ingest_receipts, '
            'phase_resolution_verdict, close_trial, usage_of_lines, exposure_recount, preflight '
            '(golden_objects, serving_manifest, supervision)',
            'lab_server.start / restart (stages); lab_serving_manifest (artifact, runtime_facts, '
            'verify_before_launch, props_build_info_problems)',
            'lab_verify_log: server.lifecycle, workers.resolved, switch.phase',
            'build_live_ab_results: decision_object, RESTART_CAP_INCOMPLETE_LABEL, '
            'PROVISIONAL_LABEL, completion_tokens_status',
            'lab_prepare.run_reference_sweep and lab_load (the load ledger)',
        ],
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
            'withdrawn_predecessor_not_in_the_history': (
                'neither 25014221 nor 5d108b4a (the withdrawn predecessor\'s protocol digests) '
                'was demoted into prior_successors: this run starts from the b049307 '
                'cells.json, so the history reads 64ace6d3 -> this successor')},
        'prior_versions_retained': {
            'config_sha256': PRIOR_CONFIG_SHA256, 'config_bytes': PRIOR_CONFIG_BYTES,
            'architecture_sha256': PRIOR_ARCH_SHA256, 'protocol_sha256': PRIOR_SUCCESSOR,
            'cells_sha256': PRIOR_CELLS_SHA256, 'revision_at_run': pre['head'],
            'reviewed_revision': PRE_REV,
            'note': ('the four documents are unchanged on this branch since the reviewed '
                     'revision; each is recoverable byte-exactly by `git show '
                     '<reviewed_revision>:<path>`, and by reverting the replacement and '
                     'deleting every inserted text')},
        'dependent_hashes_that_move': {
            'config_sha256 / harness_file_sha256[config.json]': (
                'moves against b049307, as any config byte change must; no freeze exists, so '
                'nothing frozen is invalidated. Both prospective launch records '
                '(PROSPECTIVE_LAUNCH_RECORD_20260923_1922.json and _2030.json) pin the old '
                'config.json digest, and run_smoke.verify_acquisition_code refuses a launch '
                'with either of them, by design. FINITE_COSTED_PLAN_DRAFT_v2r3 also pins the '
                'old digest, but nothing consumes that pin with a refusal: its pin is stale, '
                'not enforced. New dependent records are needed (not written here; the old '
                'ones are write-once and kept)'),
            'protocol_sha256': 'moves; recorded as the new successor above',
            'architecture_sha256': 'moves (ARCHITECTURE is under design/, outside the harness pin)',
            'serving_manifest_sha256': 'null -> the artifact digest (this amendment)',
        },
        'dependent_hashes_that_do_not_move': ['rule_block_sha256', 'receipt_mask_sha256',
                                             'monitor.winstats_sha256',
                                             'environment_lock_sha256',
                                             'engineering_acquisition (== run_smoke.BOUND_LIMITS)',
                                             'harness_file_sha256 of every .py file'],
        'this_is_not_a_freeze': True,
        'nothing_executed': ('no CPU simulation, model, server, build or network request; text '
                             'edits, digests, local reads of the three pinned roster sources, '
                             'git reads, and read-only otool/nm/file reads of the durable build '
                             'in the main checkout'),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + '\n')
    print(receipt_path)
    print(json.dumps({'post_ok': ok, 'rule_block': post['config']['rule_block_sha256_after'][:12],
                      'new_protocol': post['protocol_sha256'],
                      'new_config': post['config_sha256'],
                      'serving_manifest_sha256': digest,
                      'negative_control_refused': control['every_variant_refused_on_placement'],
                      'variants': control['variants_run'],
                      'prompts_max_jaccard': [r['max_jaccard'] for r in
                                              prompt_check['per_prompt']]}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
