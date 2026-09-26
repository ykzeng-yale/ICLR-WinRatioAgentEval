"""Stage-1 golden/conformance driver (design_notes/DESIGN_PROPOSAL.md section 3 item 4;
authorized against `lab_mock_server` only by root's 2026-09-26 07:18 bounded review,
`reviews/drivers_successor_pin_bounded_review_20260926_0718.md`, item 1: "Session60 may now
proceed with step 4's model-free stage-1 golden/conformance driver against `lab_mock_server`
only, in its exclusive branch").

design_notes/map_stage1.md section 3 names exactly what was still missing at `c62b59b`, and this
module supplies it:

* **The golden-request driver.**  `LlamaClient.__init__` (`lab_client.py:399-410`) takes a
  *mandatory* `golden: GoldenReceipt` -- a real chicken-and-egg gap, since the very first
  reference request is what PRODUCES the golden object.  design_notes/DESIGN_PROPOSAL.md section
  3 item 4 / section 8's own open question resolves this: "a new file issues the reference HTTP
  request directly and hands the result to a GoldenReceipt; `lab_client.py:399-410`'s mandatory-
  golden constructor is left byte-identical."  :func:`capture_reference` is that new file's
  function: it speaks to the server's `/props` and `/v1/chat/completions` surface with plain
  `requests` calls, never through `LlamaClient`, and `lab_client.py` is not edited by this
  commit (`tests_stage1.LabClientByteIdentityTests` pins its blob sha256).
* **The writer.**  :func:`write_golden_objects` deposits `golden_props_<server>.json` /
  `golden_generation_settings_<server>.json` at exactly the path and canonical-JSON shape
  `lab_orchestrator.load_golden_objects` / `lab_orchestrator.observed_bundle_members` read back
  (`ARCHITECTURE_FINAL.md:190-191`; `lab_orchestrator.py:1541-1610,1670-1699`), write-once via
  `lab_common.write_json_atomic` (reused verbatim, never reimplemented).
* **The format-conformance counter.**  :func:`run_conformance_probe` sends the configured fixed
  prompts (`config.json:209-218`, `prefreeze.conformance_prompts`) and applies protocol_FINAL.md
  585-587's own rule verbatim: "**Format-conformance rule (outcome-blind).** On the ten
  out-of-design prompts of 5.8, at least 9 of 10 responses of **each** model contain a code block
  that `extract_code` turns into a non-empty program. Correctness of the program is neither
  computed nor looked at."  :data:`_CODE_BLOCK_RE` is a byte-for-byte replication of
  `experiments/local_stream/agent.py:43`'s own compiled pattern (never imported -- the same
  "replicate rather than import the pilot" discipline `lab_data.normalize_prompt` already uses,
  `lab_data.py:394-395`, because importing `agent` pulls its own run-loop and sandbox modules into
  a module this driver's MATRIX row keeps free of them); `tests_stage1.py` asserts the two
  patterns' source text agree, the same way `tests_lab_design.test_normalization_matches_pilot`
  already pins `normalize_prompt` against the pilot file it was copied from.

**Why no interior `_prefreeze` event.**  Every `_prefreeze` write goes through `lab_prefreeze`
(design_notes/DESIGN_PROPOSAL.md section 3 item 3), whose `PrefreezeChain.append` only accepts an
`etype` already in `lab_eventlog.EVENT_SCHEMA`, matched *exactly* (every required key, no unknown
key, `lab_eventlog.validate_event`).  No existing etype fits a plain HTTP capture against an
already-running mock without fabricating a field this driver never observed: `server_started` /
`server_restarted` need a real launch's `pid`/`port`/`argv_sha256`/`gguf.bytes`/`load_seconds` --
and `lab_server.start`'s own docstring says its `mode='capture'` body deliberately returns
`props_matches_golden: None` / `smoke: None`, "values the `server_started` schema rejects, so a
capture body can never be appended" (`lab_server.py:464-467`); `server_health` needs an
`rss_bytes` this driver has no way to observe over plain HTTP; `llm_request`/`llm_response` need
`CALL_ID_FIELDS`' `arrival`/`attempt`/`call_index` (`lab_eventlog.py:564-567`), which name a real
trial enrollment this pre-freeze capture is not part of and must never impersonate.  Rather than
force one of these and fabricate the fields it does not have, this driver follows section 8's own
"safe direction to fail" default for exactly this shape of gap (an `E_PHASE`/event-schema value
root has not yet named): it opens and closes a segregated `_prefreeze` subtree
(`_prefreeze/stage1_golden/` and `_prefreeze/stage1_conformance/`, `lab_prefreeze.open_prefreeze`'s
own `subtree` mechanism) around every capture/probe attempt with **zero fabricated interior
events**, so the one event it DOES write -- `PrefreezeChain.close`'s own `prefreeze_closed`,
honestly reporting `n_events: 0` -- is never a placeholder standing in for an observation this
driver did not make.  The real per-unit evidence is the `lab_shard_receipt` this module records
through `lab_prefreeze.resume_shard` / `lab_prefreeze.record_shard` (never a presence-only
`lab_shard_receipt.completed_shards` check), which does have a field for every fact this driver
actually observes.  Should root define a fitting event type later, wiring an interior event in is
a pure addition, not a change to what has already landed.

**Refusal of anything but the loopback `lab_mock_server`.**  This commit's authorization (above)
is scoped to `lab_mock_server` only; the real-server path is a later, separately reviewed step.
:func:`assert_mock_target` is the one gate every public entry point of this module calls before
any network I/O: it requires the caller to say `target_kind='mock'` explicitly (never inferred),
*and* independently asserts the URL's host is loopback (`lab_client.py:82`'s own
`_LOOPBACK_HOSTS` set, replicated here rather than imported since `lab_client` is not a MATRIX
dependency of this module and stays untouched) -- the same defense-in-depth `lab_load.py:651-655`
already uses for its own load generator. Either check failing raises
:class:`RealServerNotApproved`, naming exactly why.

**2026-09-26 10:19 repair (root's independent interim review,
`reviews/stage1_pin_and_conformance_interim_20260926_1019.md`).**  Three HIGH findings against
the pinned `b229060` tree, all repaired in this commit and none by weakening an assertion:

1. **Prompt binding.**  :func:`_effective_pins` folds `prompts` (the exact ordered
   `(id, prompt)` pairs `conformance_shard` was called with) into the digested
   `stage1_request` pin alongside `sampling`/`seed`/`threshold`, so a changed prompt text, a
   changed id, or a changed order at an otherwise-unchanged `pins` now raises
   `lab_shard_receipt.ResumeMismatch` on resume instead of silently returning the stale
   receipt.  `golden_shard` has no prompt-shaped input (`capture_reference` always sends the
   fixed `lab_server.SMOKE_PROMPT`), so nothing there needed folding in.
2. **Conformance predicate.**  :func:`conforms` is the frozen rule root's ruling names: an
   actual fenced code block (:func:`contains_code_block`, unchanged) AND the REAL first-block
   extractor -- `experiments/local_stream/agent.extract_code`, loaded by :func:`_real_extract_code`
   from its own pinned AST node (never `import agent`: `agent`/`sandbox`/`verify`/`data`/`common`
   are not in this module's MATRIX row) -- returning non-whitespace output.  Neither half alone
   is the rule: an empty first fence (`` ```python\n\n``` ``) has a code block but the real
   extractor returns only `'\n'` for it (non-conforming); unfenced prose has non-empty real-
   extractor output via its fallback branch but no fence (also non-conforming).
   `_count_conforming`/`probe_prompt` now gate on `conforms`, never on fence-presence alone.
   `run_conformance_probe` also now REFUSES (`PromptSetRefused`) any `prompts` whose length is
   not exactly ten, or whose set of ids is not exactly config.json's predeclared ten -- the six
   `config.json:87` `roster.smoke_tasks` ids plus the four `config.json:209-218`
   `prefreeze.conformance_prompts` ids (:func:`_predeclared_prompt_ids`) -- and, for any id
   among the four inline `conformance_prompts`, whose submitted text disagrees with
   `config.json`'s own text for that id (:func:`_predeclared_conformance_text`).  **As of the
   2026-09-26 13:20 repair below, this text check covers all ten predeclared ids, not only the
   four**; the sentence that used to stand here (the six smoke tasks' text "comes from the MBPP
   roster, which this module cannot read... any drift there is instead caught by the
   prompt-binding fix above, on resume") was root's next finding, not a closed gap -- see below.
3. **Guard before resume.**  `assert_mock_target` is now the first statement of both
   `golden_shard` and `conformance_shard`, before either function's own `lab_prefreeze.
   resume_shard` call -- so a `target_kind='real'` (or a `target_kind='mock'` with a
   non-loopback `base_url`) call is refused even when a matching mock receipt already exists on
   disk with otherwise-unchanged pins, rather than being handed that receipt.

**2026-09-26 13:20 repair (root's independent interim review,
`reviews/stage1_repair_frozen_gate_interim_20260926_1320.md`).**  Two more HIGH findings against
the pinned `e6a8d7d` tree (the commit above), both repaired here and neither by weakening an
assertion or excluding what a check names:

1. **Six smoke-task prompt texts.** `_predeclared_conformance_text` used to cover only the four
   inline `prefreeze.conformance_prompts` and said the six `roster.smoke_tasks` texts could not
   be reached from this module.  Root's witness: with all ten predeclared ids kept, replacing
   `mbpp_full/39`'s submitted text with `'def unrelated(x): return 99'` still returned PASS.  The
   fix DERIVES each smoke id's exact prompt text from its pinned MBPP source
   (:data:`_MBPP_FULL_SOURCE`, replicated from `lab_data.SOURCES['mbpp_full']`) through the SAME
   frozen path a real episode's prompt goes through: `lab_data._mbpp_task`'s prompt/entry-point
   extraction (replicated, `lab_data` is out of this module's MATRIX row), the REAL
   `data.mbpp_entry_point` (:func:`_load_pilot_mbpp_entry_point`, its own pinned AST node) and the
   REAL `agent.build_user_prompt`/`signature_line` (:func:`_load_agent_ast_functions`, extended
   from the 10:19 repair's `extract_code` loader to load these two names from the SAME pinned
   `agent.py` into the SAME namespace, so `build_user_prompt` can call `signature_line` exactly as
   it does in the real module) -- never a reimplementation, and never `import data`/`import
   agent` (both PILOT, out of this module's MATRIX row).  `_predeclared_conformance_text` now
   merges these six derived texts with the four config texts, so `run_conformance_probe`'s
   existing per-prompt check (unchanged code) covers all ten.  The mbpp_full source's bytes and
   sha256 are checked against their pin (:func:`_load_mbpp_full_records`) before any record is
   read, and `data.py`'s sha256 is checked (:func:`_load_pilot_mbpp_entry_point`) before its
   AST is executed; either mismatch refuses (:class:`Stage1Error`) before any request or resume.
   `conformance_shard`'s resume pins additionally carry the two new sources' pinned sha256
   alongside the existing `extract_code_source_sha256`, as provenance on top of those runtime
   checks (see :func:`conformance_shard`'s own docstring).
2. **Non-amendable threshold.** `run_conformance_probe` used to accept an arbitrary `threshold`
   and never compared it to config.json.  Root's witness: `threshold=0` with all ten mock
   responses forced to HTTP 500 (zero conforming) still returned PASS.  :func:`_assert_frozen_
   threshold` now refuses (:class:`ThresholdRefused`) any `threshold` that disagrees with
   config.json's own `prefreeze.format_conformance_min` (frozen at 9, protocol 2.4 item 6),
   called before any request in `run_conformance_probe` and before any resume in
   `conformance_shard`.  The signature of both functions is unchanged (`threshold` stays a
   caller-supplied keyword argument, per `tests_lab_isolation.SIGNATURES`); it is now checked
   against the frozen value rather than accepted as-is.

**Independent adversarial review of the 13:20 repair (same day).**  One more HIGH finding, in the
same defect class as both findings above, plus two MEDIUM test-coverage gaps and one LOW gap,
all closed here:

1. **Sampling was entirely caller-controlled.** `protocol_FINAL.md:3018`'s execution row names
   "every sampling parameter" non-amendable -- the same freeze class as the prompts and the
   threshold -- yet no entry point compared a caller's `sampling` to config.json's own frozen
   `sampling` block. Live witness: `run_conformance_probe` with `sampling={'temperature': 1.9,
   'max_tokens': 3}` (missing every other frozen key) returned a PASS verdict with no refusal,
   and `capture_reference` wrote that same rogue sampling straight into the golden
   `generation_settings` object every later trial receipt is compared against
   (`protocol 13.2`).  :func:`_assert_frozen_sampling` now refuses (:class:`SamplingRefused`)
   any `sampling` that is not byte-for-byte equal to `config.json`'s own top-level `sampling`
   object, called immediately after `assert_mock_target` (and, where present, after
   `_assert_frozen_threshold`) in every one of the five public entry points that accept a
   `sampling` argument: :func:`capture_reference`, :func:`probe_prompt`,
   :func:`run_conformance_probe`, :func:`golden_shard` and :func:`conformance_shard` -- in the
   latter two, before either function's own `lab_prefreeze.resume_shard` call, exactly mirroring
   where :func:`_assert_frozen_threshold` already sits in :func:`conformance_shard`. No
   function's signature changes (`sampling` stays a caller-supplied keyword argument).
2. **Two mutation-testing coverage gaps (MEDIUM), no production change.** A mutant that deletes
   the byte/sha256 digest comparison in :func:`_load_mbpp_full_records` survived the whole suite,
   because the suite's only "changed source" negative control used a 1-record fixture that the
   downstream record-count check already catches on its own, never exercising the digest
   comparison in isolation; `tests_stage1.SmokePromptDerivationTests` now also carries a
   same-byte-length, same-974-record-count tamper (one ASCII letter of one record's `text`
   substituted for a different letter) that only the digest check can catch.  A mutant that
   truncated `run_conformance_probe`'s predeclared-text comparison to the first 30 characters
   also survived, because every existing tamper differs from the real text within its first 30
   characters; `tests_stage1.SmokePromptDerivationTests` now also carries a tamper that is
   byte-identical to a predeclared text for its entire length except its last character.
3. **One ordering coverage gap (LOW), no production change.** No test isolated "`threshold` is
   checked strictly before `conformance_shard`'s own `resume_shard` call" the way
   `tests_stage1.GuardBeforeResumeTests` already isolates the `target_kind` guard's ordering (by
   monkeypatching `lab_prefreeze.resume_shard` to raise if reached at all); one test failing
   only incidentally, via an unrelated sampling-triggered `ResumeMismatch`, was standing in for
   it.  `tests_stage1.GuardBeforeResumeTests` now carries a dedicated test doing exactly that for
   both the threshold check and the new sampling check.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import ast
import json
import re
import tempfile
import warnings
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

import lab_common
import lab_prefreeze
import lab_server

#: Replicated from `lab_client.py:82` (`_LOOPBACK_HOSTS`), not imported: `lab_client` is not a
#: MATRIX dependency of this module (it stays untouched, per this module's docstring), and a
#: second implementation of "what counts as loopback" is the same discipline `lab_server.smoke`
#: already uses for the frozen receipt rule rather than importing `lab_client` (`lab_server.py:
#: 645-648`). `tests_stage1.py` pins the two sets equal.
_LOOPBACK_HOSTS: frozenset[str] = frozenset({'127.0.0.1', 'localhost', '::1', '[::1]'})

#: `ARCHITECTURE_FINAL.md:190-191` names these two file patterns; `lab_orchestrator.py:1541-1543`
#: (`GOLDEN_FILES`) is the one production reader/writer-contract for them. Replicated here rather
#: than imported -- `lab_orchestrator` is a large module (it alone pulls `lab_design`, `lab_coin`,
#: `lab_monitor`, `lab_enclosure`, `lab_reference_rule`, `lab_hostcheck`, `lab_serving_manifest`
#: into this driver's dependency closure for two string literals) -- and pinned equal to it by
#: `tests_stage1.py`, the same "replicate, then test for parity" discipline this module's own
#: docstring already uses for `_CODE_BLOCK_RE`.
GOLDEN_FILE_PATTERNS: dict[str, str] = {
    'golden_props_sha256': 'golden_props_%s.json',
    'golden_generation_settings_sha256': 'golden_generation_settings_%s.json',
}

#: Byte-for-byte replication of `experiments/local_stream/agent.py:43`'s own compiled pattern
#: (see the module docstring's "The format-conformance counter" paragraph for why this is
#: replicated rather than imported). `tests_stage1.py` asserts the two patterns' source text
#: agree.
_CODE_BLOCK_RE = re.compile(r'```(?:python|py|python3)?[ \t]*\n(.*?)```', re.S)


class Stage1Error(lab_common.LabError):
    """Root of every refusal this module raises."""


class RealServerNotApproved(Stage1Error):
    """`target_kind` was not `'mock'`, or `base_url`'s host is not loopback.  This commit's
    authorization (root's 2026-09-26 07:18 review item 1) is scoped to `lab_mock_server` only;
    the real-server path is a separately reviewed, not-yet-approved step."""


class PromptSetRefused(Stage1Error):
    """`run_conformance_probe`'s `prompts` was not exactly ten items, was not exactly
    config.json's predeclared ten ids (:func:`_predeclared_prompt_ids`), or supplied text for a
    predeclared id -- any of the four inline `prefreeze.conformance_prompts` OR any of the six
    `roster.smoke_tasks` (root's 2026-09-26 13:20 review, finding 1, closing the gap left by
    root's 2026-09-26 10:19 review, finding 2: the six smoke ids used to be entirely
    unchecked here) -- that disagrees with its predeclared text (:func:`_predeclared_conformance_text`)."""


class ThresholdRefused(Stage1Error):
    """`threshold` disagreed with the frozen, non-amendable `config.json`
    `prefreeze.format_conformance_min` (protocol 2.4 item 6 / `protocol_FINAL.md:3018,3773`;
    root's 2026-09-26 13:20 review, finding 2).  `run_conformance_probe` and `conformance_shard`
    both refuse any other value, before any request or resume."""


class SamplingRefused(Stage1Error):
    """`sampling` disagreed with the frozen, non-amendable `config.json` top-level `sampling`
    object (protocol_FINAL.md:3018, "every sampling parameter"; independent adversarial review
    of the 2026-09-26 13:20 repair).  Every public entry point that accepts a `sampling` keyword
    argument -- :func:`capture_reference`, :func:`probe_prompt`, :func:`run_conformance_probe`,
    :func:`golden_shard`, :func:`conformance_shard` -- refuses any other value, before any
    request or resume, the same discipline :class:`ThresholdRefused` already applies."""


#: Path to the ONE real first-block extractor this driver's conformance predicate defers to,
#: never a reimplementation (root's 2026-09-26 10:19 ruling, finding 2).  `lab_common.LS_DIR` is
#: already `REPO_ROOT / 'experiments' / 'local_stream'`.
_AGENT_PY_PATH: Path = lab_common.LS_DIR / 'agent.py'

#: `lab_common.sha256_file(_AGENT_PY_PATH)` at the moment this repair was written.  Loading
#: `extract_code` from a file that no longer hashes to this must refuse rather than silently run
#: an unpinned extractor -- the same "pin, then verify before trusting" discipline this module
#: already applies to `lab_client.py` (module docstring) and to a golden `/props` (`lab_orchestrator
#: .load_golden_objects`'s own rejection, mirrored by :func:`capture_reference`).
_AGENT_PY_SHA256: str = '3cf2056330c72ebd5d2884f48d6ec2daa706fcc685ad67e3c2609d809ff75b64'

_agent_ast_cache: dict | None = None  # cache for :func:`_load_agent_ast_functions`


def _load_agent_ast_functions() -> dict:
    """[pure-ish] Load the REAL `experiments/local_stream/agent` names this driver depends on --
    `extract_code` (the first-block extractor, root's 2026-09-26 10:19 ruling, finding 2) AND
    `build_user_prompt`/`signature_line` (the exact template path a real episode's MBPP/smoke-
    task user message goes through, root's 2026-09-26 13:20 ruling, finding 1) -- plus the two
    module-level patterns `extract_code` closes over, all from `_AGENT_PY_PATH`'s own AST nodes,
    executed into ONE shared namespace so `build_user_prompt` can call `signature_line` exactly
    as it does inside the real module.  Never `import agent` (out of this module's MATRIX row:
    `agent`/`sandbox`/`verify`/`data`/`common` are the PILOT group, and `lab_data.py:394-395`'s
    "replicate rather than import" discipline this module's own docstring already follows for
    `_CODE_BLOCK_RE` is extended here from a pattern to three callables sharing one namespace).

    Of the three ways root's reviews offered to call an exact pilot function -- subprocess a
    small driver script, monkeypatch `sys.modules` with a stub `common`/`sandbox`/`verify` so
    `import agent` succeeds, or parse and exec only the wanted AST nodes -- this picks the third,
    the same choice `_load_real_extract_code` (this function's predecessor) already made: it adds
    no subprocess boundary and no stand-in modules whose behavior could itself silently diverge
    from a real `agent` import; it costs re-parsing one small file once per process, cached in
    :data:`_agent_ast_cache` after the first call.  Refuses (:class:`Stage1Error`) before
    executing anything if the file's sha256 no longer matches the pinned :data:`_AGENT_PY_SHA256`,
    or if any of the five wanted top-level names is missing."""
    actual = lab_common.sha256_file(_AGENT_PY_PATH)
    if actual != _AGENT_PY_SHA256:
        raise Stage1Error(
            f'{_AGENT_PY_PATH} sha256 {actual!r} does not match the pinned '
            f'{_AGENT_PY_SHA256!r}; refusing to load real agent.py names from a drifted '
            'pilot file (update _AGENT_PY_SHA256 only after confirming the change deliberately, '
            'and only alongside a fresh review of every predicate/derivation that depends on it)')
    source = _AGENT_PY_PATH.read_text('utf-8')
    tree = ast.parse(source, filename=str(_AGENT_PY_PATH))
    wanted_assigns = {'_CODE_BLOCK', '_SPECIAL_TOKENS'}
    nodes = [n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in wanted_assigns for t in n.targets)]
    wanted_fns = {'extract_code', 'build_user_prompt', 'signature_line'}
    fn_nodes = [n for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name in wanted_fns]
    if len(nodes) != len(wanted_assigns) or len(fn_nodes) != len(wanted_fns):
        raise Stage1Error(
            f'{_AGENT_PY_PATH} no longer defines the expected extract_code/build_user_prompt/'
            'signature_line/_CODE_BLOCK/_SPECIAL_TOKENS shape this loader depends on')
    nodes.extend(fn_nodes)
    namespace: dict = {'re': re, 'ast': ast, 'warnings': warnings}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<agent.py (pinned AST nodes)>',
                'exec'), namespace)
    return namespace


def _real_extract_code(text) -> str:
    """[pure-ish, cached] The REAL `experiments/local_stream/agent.extract_code(text)`; see
    :func:`_load_agent_ast_functions` for how it is loaded and pinned."""
    global _agent_ast_cache
    if _agent_ast_cache is None:
        _agent_ast_cache = _load_agent_ast_functions()
    return _agent_ast_cache['extract_code'](text)


def _real_build_user_prompt(pilot_task: Mapping) -> str:
    """[pure-ish, cached] The REAL `experiments/local_stream/agent.build_user_prompt(task)` --
    the exact template path a real episode's user message goes through (protocol 5.8/2.4; root's
    2026-09-26 13:20 ruling, finding 1) -- see :func:`_load_agent_ast_functions`."""
    global _agent_ast_cache
    if _agent_ast_cache is None:
        _agent_ast_cache = _load_agent_ast_functions()
    return _agent_ast_cache['build_user_prompt'](dict(pilot_task))


#: `experiments/local_stream/data.py`'s own AST-pinned `mbpp_entry_point` (root's 2026-09-26
#: 13:20 ruling, finding 1): the ONE real rule for which def in an MBPP reference becomes a
#: smoke task's entry point, never a reimplementation.  `data` is PILOT (out of this module's
#: MATRIX row), loaded the same "pin, then verify before trusting" way as `_AGENT_PY_PATH`.
_DATA_PY_PATH: Path = lab_common.LS_DIR / 'data.py'

#: `lab_common.sha256_file(_DATA_PY_PATH)` at the moment this repair was written.
_DATA_PY_SHA256: str = 'ae630675f43786bcf7483ff90d4c641ab9a6c7c16202de456d96b03f19321405'


def _load_pilot_mbpp_entry_point():
    """[pure-ish] Load the REAL `experiments/local_stream/data.mbpp_entry_point` (plus the two
    regex patterns it closes over) from its own pinned AST node, never `import data` -- the same
    discipline :func:`_load_agent_ast_functions` uses for `agent.py`.  Deliberately NOT cached
    across calls, unlike :func:`_load_agent_ast_functions`: this loader backs the mbpp-source-
    drift negative control (`tests_stage1.py`'s changed-source-file test), and a persistent cache
    would let an earlier, unrelated call's successful load silently paper over a later drifted-
    file scenario within the same process.  The file is a few KB; one read plus one sha256 costs
    nothing that matters at the rate this driver derives smoke-task prompts."""
    actual = lab_common.sha256_file(_DATA_PY_PATH)
    if actual != _DATA_PY_SHA256:
        raise Stage1Error(
            f'{_DATA_PY_PATH} sha256 {actual!r} does not match the pinned {_DATA_PY_SHA256!r}; '
            'refusing to derive smoke-task prompt texts through a drifted pilot file')
    source = _DATA_PY_PATH.read_text('utf-8')
    tree = ast.parse(source, filename=str(_DATA_PY_PATH))
    wanted_assigns = {'_ASSERT_NAME', '_DEF_NAME'}
    nodes = [n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in wanted_assigns for t in n.targets)]
    fn_node = next((n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == 'mbpp_entry_point'), None)
    if fn_node is None or len(nodes) != len(wanted_assigns):
        raise Stage1Error(
            f'{_DATA_PY_PATH} no longer defines the expected mbpp_entry_point/_ASSERT_NAME/'
            '_DEF_NAME shape this loader depends on')
    nodes.append(fn_node)
    namespace: dict = {'re': re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<data.py (pinned AST nodes)>',
                'exec'), namespace)
    return namespace['mbpp_entry_point']


def _pilot_mbpp_entry_point(rec: Mapping) -> str:
    """[pure-ish] The REAL `experiments/local_stream/data.mbpp_entry_point(rec)`; see
    :func:`_load_pilot_mbpp_entry_point` for how it is loaded and pinned (never cached)."""
    return _load_pilot_mbpp_entry_point()(rec)


#: Replicated from `lab_data.py:130-143` (`SOURCES['mbpp_full']`), never imported: `lab_data` is
#: not in this module's MATRIX row.  `tests_stage1.py` pins this dict equal to
#: `lab_data.SOURCES['mbpp_full']`.
_MBPP_FULL_SOURCE: dict = {
    'filename': 'mbpp.jsonl',
    'bytes': 563743,
    'sha256': 'ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f',
    'records': 974,
    'aliases': ('mbpp.jsonl', 'mbpp_full.jsonl'),
}

#: Replicated from `lab_data.py:146-150` (`CACHE_SEARCH_DIRS`), same reason as above.  A plain
#: module-level tuple (not derived only from `lab_common.REPO_ROOT`), so a test can monkeypatch
#: it to an isolated temp directory for the source-drift negative control without ever touching
#: the real cache under `work/local_stream/data`.
_MBPP_FULL_CACHE_SEARCH_DIRS: tuple[Path, ...] = (
    lab_common.REPO_ROOT / 'work' / 'local_stream' / 'data',
    Path('/tmp/claude-501'),
    Path(tempfile.gettempdir()),
)


def _find_mbpp_full_source() -> "Path | None":
    """[pure-ish] The same search order as `lab_data._find_cached` restricted to `mbpp_full`
    (replicated, not imported -- see this module's docstring)."""
    for directory in _MBPP_FULL_CACHE_SEARCH_DIRS:
        for alias in _MBPP_FULL_SOURCE['aliases']:
            candidate = Path(directory) / alias
            try:
                if candidate.is_file():
                    return candidate
            except OSError:
                continue
    return None


def _load_mbpp_full_records() -> list:
    """The full pinned mbpp_full record list, bytes-and-sha256 verified BEFORE anything is
    parsed (root's 2026-09-26 13:20 ruling, finding 1: "check the source file's sha256 against
    its pin ... REFUSE on any mismatch, before any request or resume").  Deliberately NOT cached
    across calls -- see :func:`_load_pilot_mbpp_entry_point`'s docstring for why."""
    path = _find_mbpp_full_source()
    if path is None:
        raise Stage1Error(
            'no cached copy of the pinned mbpp_full source (%s) was found under any of %s; '
            'refusing to derive the six smoke-task prompt texts without it'
            % (_MBPP_FULL_SOURCE['filename'],
              [str(d) for d in _MBPP_FULL_CACHE_SEARCH_DIRS]))
    raw = path.read_bytes()
    got_bytes, got_sha256 = len(raw), lab_common.sha256_bytes(raw)
    if got_bytes != _MBPP_FULL_SOURCE['bytes'] or got_sha256 != _MBPP_FULL_SOURCE['sha256']:
        raise Stage1Error(
            'mbpp_full source at %s: expected %d bytes sha256 %s, found %d bytes sha256 %s; '
            'refusing to derive smoke-task prompt texts from a drifted source'
            % (path, _MBPP_FULL_SOURCE['bytes'], _MBPP_FULL_SOURCE['sha256'], got_bytes,
              got_sha256))
    records = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    if len(records) != _MBPP_FULL_SOURCE['records']:
        raise Stage1Error(
            'mbpp_full source at %s: expected %d records, found %d'
            % (path, _MBPP_FULL_SOURCE['records'], len(records)))
    return records


def _derive_smoke_prompt_text(uid: str, records: list) -> str:
    """[pure] The exact prompt text a real episode would send for smoke-task `uid` (an
    `mbpp_full/<n>` id), through the FROZEN normalization/template path: the same prompt/entry-
    point/reference extraction `lab_data._mbpp_task` applies to a raw `mbpp_full` record
    (`lab_data.py:404-419`, replicated here rather than imported -- `lab_data` is out of this
    module's MATRIX row), the REAL `data.mbpp_entry_point` (:func:`_pilot_mbpp_entry_point`), and
    the REAL `agent.build_user_prompt`/`signature_line` (:func:`_real_build_user_prompt`) -- the
    same three steps `lab_data.to_pilot_task` + `agent.build_user_prompt` apply to a real
    `mbpp_full` task in a real episode (`lab_data.py:460-475`; `agent.py:69-74`).  Refuses
    (:class:`Stage1Error`) if `uid` is not an `mbpp_full/<n>` id, or names a `task_id` absent
    from `records`."""
    m = re.match(r'^mbpp_full/([0-9]+)$', str(uid))
    if not m:
        raise Stage1Error(f'{uid!r} is not an mbpp_full/<n> smoke-task id')
    task_id = int(m.group(1))
    rec = next((r for r in records if int(r['task_id']) == task_id), None)
    if rec is None:
        raise Stage1Error(
            f'mbpp_full task_id {task_id} (smoke id {uid!r}) is not present in the pinned '
            'mbpp_full source; refusing to derive its prompt text')
    raw_prompt = rec['prompt'] if 'prompt' in rec else rec['text']
    prompt = (raw_prompt or '').strip()
    reference = rec.get('code') or ''
    entry_point = _pilot_mbpp_entry_point(
        {'test_list': list(rec.get('test_list') or []), 'code': reference})
    pilot_task = {'benchmark': 'mbpp', 'prompt': prompt, 'entry_point': entry_point,
                 'reference': reference}
    return _real_build_user_prompt(pilot_task)


def _predeclared_smoke_prompt_texts() -> dict[str, str]:
    """[pure-ish] `{id: prompt text}` for the six `config.json:87` `roster.smoke_tasks` ids,
    DERIVED from their pinned MBPP source through the frozen normalization/template path
    (:func:`_derive_smoke_prompt_text`) -- root's 2026-09-26 13:20 ruling, finding 1.  Before
    this repair `_predeclared_conformance_text` covered only the four inline
    `prefreeze.conformance_prompts` and intentionally left these six unchecked; this closes that
    gap.  Refuses (:class:`Stage1Error`) on a missing/drifted mbpp_full source, a drifted
    `data.py`/`agent.py` pilot file, or a smoke id absent from the source -- before any request
    or resume, the same way :func:`_predeclared_prompt_ids` already refuses on a config drift."""
    cfg = lab_common.harness_config()
    smoke_ids = tuple((cfg.get('roster') or {}).get('smoke_tasks') or ())
    records = _load_mbpp_full_records()
    return {uid: _derive_smoke_prompt_text(uid, records) for uid in smoke_ids}


def _predeclared_prompt_ids() -> frozenset[str]:
    """[pure-ish] The exactly-ten predeclared conformance-probe ids of protocol 5.8: the six
    `config.json:87` `roster.smoke_tasks` ids plus the four `config.json:209-218`
    `prefreeze.conformance_prompts` ids -- read through `lab_common.harness_config()` (already
    in this module's MATRIX row; no new dependency), never re-parsed from a second copy of
    config.json.  Refuses (:class:`Stage1Error`) if config.json itself no longer declares
    exactly ten distinct ids across the two lists, so a config drift is caught here rather than
    silently shrinking or padding the set this driver refuses against."""
    cfg = lab_common.harness_config()
    smoke = tuple((cfg.get('roster') or {}).get('smoke_tasks') or ())
    conformance = (cfg.get('prefreeze') or {}).get('conformance_prompts') or []
    ood_ids = tuple(p['id'] for p in conformance if isinstance(p, Mapping) and 'id' in p)
    ids = frozenset(smoke) | frozenset(ood_ids)
    if len(ids) != 10 or len(smoke) + len(ood_ids) != 10:
        raise Stage1Error(
            f'config.json roster.smoke_tasks ({len(smoke)}) + prefreeze.conformance_prompts '
            f'({len(ood_ids)}) must declare exactly ten DISTINCT ids; got {sorted(ids)}')
    return ids


def _predeclared_conformance_text() -> dict[str, str]:
    """[pure-ish] `{id: prompt text}` for all TEN predeclared conformance-probe ids of protocol
    5.8: the four `config.json:209-218` `prefreeze.conformance_prompts` (read straight from
    config.json) PLUS the six `config.json:87` `roster.smoke_tasks`
    (:func:`_predeclared_smoke_prompt_texts`, DERIVED from their pinned MBPP source through the
    frozen normalization/template path).

    Before root's 2026-09-26 13:20 review this function covered only the four inline prompts and
    said the six smoke texts "come from the MBPP roster, which this module does not import" --
    true of a plain `import lab_data`, but not of the source-hash-pinned AST-node approach
    :func:`_derive_smoke_prompt_text` uses (the same approach already used for `extract_code`).
    Root's witness: with all ten predeclared ids kept but `mbpp_full/39`'s submitted text
    replaced with `'def unrelated(x): return 99'`, `run_conformance_probe` returned PASS, because
    the six smoke ids were never checked here.  They are now."""
    cfg = lab_common.harness_config()
    conformance = (cfg.get('prefreeze') or {}).get('conformance_prompts') or []
    out = {p['id']: p['prompt'] for p in conformance if isinstance(p, Mapping) and 'id' in p}
    out.update(_predeclared_smoke_prompt_texts())
    return out


def assert_mock_target(base_url: str, target_kind: str) -> None:
    """The one gate every public entry point of this module calls before any network I/O.
    Refuses (:class:`RealServerNotApproved`) unless `target_kind == 'mock'` *and* `base_url`'s
    host is one of :data:`_LOOPBACK_HOSTS` -- two independent checks, since a caller could pass
    `target_kind='mock'` by rote without the URL actually being loopback, or vice versa."""
    if target_kind != 'mock':
        raise RealServerNotApproved(
            f"lab_stage1 is authorized (root's 2026-09-26 07:18 bounded review, "
            f"reviews/drivers_successor_pin_bounded_review_20260926_0718.md, item 1) only "
            f"against the loopback lab_mock_server; target_kind={target_kind!r} names a "
            "real-server path, which is not approved in this commit. Pass target_kind='mock'.")
    host = urlsplit(str(base_url)).hostname
    if host not in _LOOPBACK_HOSTS:
        raise RealServerNotApproved(
            f'base_url {base_url!r} is not loopback (host={host!r}); lab_stage1 may only '
            'address a loopback lab_mock_server in this commit -- the real-server path is not '
            'approved.')


def capture_reference(base_url, server_id, *, sampling, target_kind, seed=1, session=None,
                      timeout_s=120.0) -> dict:
    """Issue the reference `GET /props` and `POST /v1/chat/completions` directly against
    `base_url`'s HTTP surface -- never through `LlamaClient`, whose constructor requires an
    already-existing golden (`lab_client.py:399-410`) -- and return the pieces
    `lab_orchestrator.load_golden_objects` / `observed_bundle_members` need:
    `{'props': <tokenized /props object>, 'generation_settings': <the reference response's
    __verbose.generation_settings>, 'raw_props_sha256': ..., 'request_sha256': ...}`.

    `props` is tokenized by `lab_server.tokenized_props` (`lab_server.py:209-224`), the ONE
    tokenization rule the golden object and every later observation both go through; a
    `model_path` under no known root -- including one that is already a token, which a real
    server never reports -- raises `lab_common.UntokenizablePath`, and one whose tokenized form
    still does not start with `'<'` raises :class:`Stage1Error`, mirroring
    `lab_orchestrator.load_golden_objects`'s own rejection (`lab_orchestrator.py:1599-1602`) as
    early as possible rather than only when the file is later read back.

    The reference request reuses `lab_server.SMOKE_PROMPT` (`lab_server.py:122`, `'Reply with the
    single word: pong'`) -- the same non-task completion `lab_server.smoke` sends at every real
    start/restart -- so the mock classifies it `kind='smoke'` and returns a deterministic
    response, and so this bootstrap's reference request is not itself a fresh, unreviewed prompt.
    `sampling` is applied exactly as `lab_server._smoke_attempt` applies it (`lab_server.py:
    667-673`); `seed` is a plain request field, never `design_seed_base`-derived (that seed rule
    is for the live trial's arrival order and the section 11.5 replicate seed only,
    design_notes/DESIGN_PROPOSAL.md section 4 -- confusing the two is exactly the mistake that
    section warns against)."""
    assert_mock_target(base_url, target_kind)
    _assert_frozen_sampling(sampling)
    sess = session if session is not None else requests
    root = str(base_url).rstrip('/')
    try:
        r = sess.get(root + '/props', timeout=timeout_s)
    except requests.RequestException as exc:
        raise Stage1Error(f'GET /props failed: {exc}') from exc
    if r.status_code != 200:
        raise Stage1Error(f'GET /props returned HTTP {r.status_code}, expected 200')
    try:
        raw_props = r.json()
    except ValueError as exc:
        raise Stage1Error(f'GET /props did not return valid JSON: {exc}') from exc
    if not isinstance(raw_props, Mapping):
        raise Stage1Error('GET /props did not return a JSON object')
    tokenized = lab_server.tokenized_props(raw_props)
    if not str(tokenized.get('model_path') or '').startswith('<'):
        raise Stage1Error(
            "golden /props model_path must tokenize to a value starting with '<' -- "
            f'{tokenized.get("model_path")!r} does not, mirroring '
            "lab_orchestrator.load_golden_objects's own rejection of an untokenized golden "
            '/props (lab_orchestrator.py:1599-1602)')
    body: dict = {'model': str(raw_props.get('model_alias') or server_id),
                 'messages': [{'role': 'user', 'content': lab_server.SMOKE_PROMPT}]}
    body.update(dict(sampling))
    body['seed'] = int(seed)
    body.setdefault('stream', False)
    body.setdefault('verbose', True)
    try:
        r2 = sess.post(root + '/v1/chat/completions', json=body, timeout=timeout_s)
    except requests.RequestException as exc:
        raise Stage1Error(f'reference POST /v1/chat/completions failed: {exc}') from exc
    if r2.status_code != 200:
        raise Stage1Error(
            f'reference POST /v1/chat/completions returned HTTP {r2.status_code}, expected 200')
    try:
        chat = r2.json()
    except ValueError as exc:
        raise Stage1Error(
            f'reference POST /v1/chat/completions did not return valid JSON: {exc}') from exc
    if not isinstance(chat, Mapping):
        raise Stage1Error('reference chat completion did not return a JSON object')
    verbose = chat.get('__verbose')
    if not isinstance(verbose, Mapping) or 'generation_settings' not in verbose:
        raise Stage1Error(
            'reference chat completion carried no __verbose.generation_settings')
    gen = verbose['generation_settings']
    if not isinstance(gen, Mapping) or not gen:
        raise Stage1Error('__verbose.generation_settings was not a non-empty JSON object')
    return {
        'props': tokenized,
        'generation_settings': dict(gen),
        'raw_props_sha256': lab_common.sha256_canonical(dict(raw_props)),
        'request_sha256': lab_common.sha256_canonical(body),
    }


def write_golden_objects(freeze_dir, server_id, captured) -> dict:
    """Write-once golden files at exactly the path/format `lab_orchestrator.load_golden_objects`
    / `observed_bundle_members` expect (`ARCHITECTURE_FINAL.md:190-191`; `lab_orchestrator.py:
    1541-1610,1670-1699`): `<freeze_dir>/golden_props_<server_id>.json` and
    `<freeze_dir>/golden_generation_settings_<server_id>.json`, each the canonical JSON of a
    plain object, through `lab_common.write_json_atomic(..., durable=True)` alone (reused
    verbatim: a byte-identical rewrite is a no-op, different bytes raise
    `lab_common.WriteOnceViolation`).

    Refuses (:class:`Stage1Error`) BEFORE writing anything, given a `captured['props']` whose
    `model_path` is not already tokenized (does not start with `'<'`) or a `captured
    ['generation_settings']` that is not a non-empty JSON object -- mirroring
    `lab_orchestrator.load_golden_objects`'s own rejection of an untokenized golden `/props`
    (`lab_orchestrator.py:1599-1602`) at the point this driver writes the file, not only when a
    later reader opens it.  Returns `{'golden_props_sha256': <digest>,
    'golden_generation_settings_sha256': <digest>}`, the same member names
    `lab_orchestrator.GOLDEN_FILES` uses."""
    props = captured['props']
    gen = captured['generation_settings']
    if not isinstance(props, Mapping) or not str(props.get('model_path') or '').startswith('<'):
        raise Stage1Error(
            "golden props model_path must already be tokenized (start with '<'), mirroring "
            "lab_orchestrator.load_golden_objects's own rejection of an untokenized golden "
            f'/props (lab_orchestrator.py:1599-1602); got '
            f'{(props.get("model_path") if isinstance(props, Mapping) else props)!r}')
    if not isinstance(gen, Mapping) or not gen:
        raise Stage1Error('golden generation_settings must be a non-empty JSON object')
    out_dir = Path(freeze_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    props_path = out_dir / (GOLDEN_FILE_PATTERNS['golden_props_sha256'] % server_id)
    gen_path = out_dir / (GOLDEN_FILE_PATTERNS['golden_generation_settings_sha256'] % server_id)
    return {
        'golden_props_sha256': lab_common.write_json_atomic(props_path, dict(props),
                                                            durable=True),
        'golden_generation_settings_sha256': lab_common.write_json_atomic(
            gen_path, dict(gen), durable=True),
    }


def _utcnow() -> str:
    """[pure-ish] The current instant in the ISO-8601 `...Z` form `lab_shard_receipt`'s
    `_ISO_UTC_RE` requires."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def _effective_pins(pins: Mapping, **request_fields) -> dict:
    """[pure] The pins block ACTUALLY passed to `lab_prefreeze.resume_shard`/`record_shard`: the
    caller's `pins` (design_notes' code/config/seed/data block) plus one extra key,
    `stage1_request`, a digest of every keyword field this call's OUTPUT also depends on
    (`golden_shard` passes `sampling`/`seed`; `conformance_shard` passes `sampling`/`seed`/
    `threshold`/`prompts` -- the exact ORDERED `(id, prompt)` pairs, root's 2026-09-26 10:19
    review finding 1: without this, a changed prompt text/id/order at an unchanged caller `pins`
    would resume the stale receipt with no error at all, the same class of gap this function's
    `sampling`/`seed` folding already closed for the mutable-request-field case).

    Without this extra key, two calls with an IDENTICAL caller-supplied `pins` but a DIFFERENT
    `sampling` would resume the first call's stale receipt with no error at all -- exactly the
    gap an independent adversarial review of this commit reproduced empirically (two
    `golden_shard` calls, same `pins`, `sampling.temperature` 0.1 vs 0.9, same stale receipt
    returned, the second call's `base_url` -- deliberately pointed at a closed local port -- was
    never even dialed).  `lab_prefreeze.resume_shard`/`lab_shard_receipt.verify_resume` only ever
    compare the `expected_pins` mapping THEY are given -- by design, since `lab_prefreeze` itself
    has no notion of what a driver's own request parameters are -- so it is this module's job,
    not theirs, to fold every request field its two shard functions accept into that mapping.

    `base_url` and `target_kind` are deliberately NOT folded in here: resuming must never touch
    the network (`ShardResumeTests.test_unchanged_resume_is_reused_and_changed_pin_resume_is_
    refused` resumes against a `base_url` pointed at a closed local port, to prove exactly that),
    and this module's own `assert_mock_target` already polices `target_kind` on every FRESH
    capture/probe attempt -- a resumed, already-recorded receipt has no fresh attempt for it to
    police."""
    merged = dict(pins)
    merged['stage1_request'] = {'sha256': lab_common.sha256_canonical(dict(request_fields))}
    return merged


def golden_shard(*, base_url, server_id, freeze_dir, receipts_dir, inv, target_kind, sampling,
                 pins, prefreeze_root=None, seed=1, session=None, subtree='stage1_golden',
                 create=True) -> dict:
    """One golden-capture completed-shard unit for one server (design_notes/DESIGN_PROPOSAL.md
    section 3 item 4 / section 5's shard shape).  Resumes ONLY through
    `lab_prefreeze.resume_shard` (never a presence-only `lab_shard_receipt.completed_shards`
    check): a shard already on disk whose recorded pins/schedule row/output hashes still agree
    with :func:`_effective_pins` of the caller's current `pins`/`sampling`/`seed` is returned
    as-is; any disagreement raises `lab_shard_receipt.ResumeMismatch`, naming every field that
    differs, and repairs nothing.  See :func:`_effective_pins` for exactly which request fields
    are folded in and why (an independent adversarial review of this commit reproduced a
    resume-silently-ignores-`sampling` gap; this is the fix).

    Otherwise: opens one segregated `_prefreeze/<subtree>/` chain segment for the attempt (see
    this module's docstring for why it carries no interior event beyond `PrefreezeChain.close`'s
    own honest `prefreeze_closed`), calls :func:`capture_reference` then
    :func:`write_golden_objects`, closes the chain, and records exactly one
    `lab_shard_receipt` via `lab_prefreeze.record_shard`.  A capture/write failure propagates
    (the chain is still closed first, in a `finally`) and writes NO receipt -- mirroring
    `lab_server.start`'s own contract of raising without recording, and leaving the decision of
    whether/how to persist a failed attempt to this function's caller, exactly as
    `lab_server.start`'s caller (the orchestrator) is the one that appends
    `server_start_failed`.

    `assert_mock_target` is called FIRST, before any resume check (root's 2026-09-26 10:19
    review, finding 3): a `target_kind='real'` (or non-loopback `base_url`) call is refused even
    when a matching mock receipt already exists on disk with otherwise-unchanged pins, rather
    than being handed that receipt."""
    assert_mock_target(base_url, target_kind)
    _assert_frozen_sampling(sampling)
    schedule_row = {'unit': 'golden_capture', 'server_id': str(server_id)}
    freeze_path = Path(freeze_dir)
    output_rel = {
        member: pattern % server_id for member, pattern in GOLDEN_FILE_PATTERNS.items()
    }
    resume_pins = _effective_pins(pins, sampling=dict(sampling), seed=int(seed))
    resumed = lab_prefreeze.resume_shard(
        receipts_dir, 'stage1_golden', schedule_row, expected_pins=resume_pins,
        expected_output_paths=list(output_rel.values()), root_for_outputs=freeze_path)
    if resumed is not None:
        return resumed
    start_utc = _utcnow()
    chain = lab_prefreeze.open_prefreeze('server_smoke', inv=inv, root=prefreeze_root,
                                         subtree=subtree, create=create)
    try:
        captured = capture_reference(base_url, server_id, sampling=sampling,
                                     target_kind=target_kind, seed=seed, session=session)
        digests = write_golden_objects(freeze_path, server_id, captured)
    finally:
        chain.close()
    end_utc = _utcnow()
    outputs = {output_rel[member]: digests[member] for member in GOLDEN_FILE_PATTERNS}
    inputs = {
        'base_url': str(base_url), 'server_id': str(server_id),
        'raw_props_sha256': captured['raw_props_sha256'],
        'request_sha256': captured['request_sha256'],
        'prefreeze_head': chain.head,
    }
    lab_prefreeze.record_shard(
        receipts_dir, 'stage1_golden', schedule_row, pins=resume_pins, inputs=inputs,
        outputs=outputs, start_utc=start_utc, end_utc=end_utc, outcome='success')
    written = lab_prefreeze.resume_shard(
        receipts_dir, 'stage1_golden', schedule_row, expected_pins=resume_pins,
        expected_output_paths=list(output_rel.values()), root_for_outputs=freeze_path)
    assert written is not None, 'the receipt just written must itself resume successfully'
    return written


def contains_code_block(text) -> bool:
    """[pure] Whether `text` contains a fenced code block `_CODE_BLOCK_RE` matches -- a STRICTER
    reading of protocol_FINAL.md:585-587's format-conformance rule ("at least 9 of 10 responses
    ... contain a code block that `extract_code` turns into a non-empty program") than the rule's
    own text taken fully literally.

    Taken fully literally, the rule is nearly vacuous: `agent.extract_code`'s own fallback branch
    (`_SPECIAL_TOKENS.sub('', text).strip() + '\\n'`, `experiments/local_stream/agent.py:83`)
    returns a NON-EMPTY string for almost any non-blank response, fenced or not (its trailing
    `'\\n'` alone makes `bool(...)` true) -- so a fully literal "extract_code(text) is non-empty"
    reading would count nearly every response as conforming, which is not a meaningful format
    gate.  `tests_stage1.ProtocolInterpretationTests` executes the REAL `agent.extract_code`
    (from its own AST node, never imported wholesale) against a prose-only, unfenced response and
    shows it returns non-empty precisely to make this divergence an executable, quantified fact
    rather than only this docstring's prose.

    This was an UNREVIEWED INTERPRETIVE SCOPE DECISION when this module first landed: root's
    2026-09-26 07:18 bounded review authorized item 1's driver but had not yet adjudicated which
    of these two readings the format-conformance gate should use.  Root's 2026-09-26 10:19 review
    (finding 2) has since settled it: the frozen predicate is neither reading alone but their
    CONJUNCTION -- see :func:`conforms`, which every counting path now uses instead of this
    function alone.  `contains_code_block` itself is UNCHANGED (fence presence only; it is sound
    in one direction only, per `tests_stage1.ProtocolInterpretationTests` -- whenever it reports
    `True`, the real `extract_code` never reports an effectively empty result), and remains a
    building block of :func:`conforms`, never the conformance gate by itself any more."""
    if not text:
        return False
    return _CODE_BLOCK_RE.search(str(text)) is not None


def conforms(text) -> bool:
    """[pure-ish] The frozen format-conformance predicate per root's 2026-09-26 10:19 ruling
    (finding 2): `text` conforms iff it contains an actual fenced code block
    (:func:`contains_code_block`) AND the REAL first-block extractor -- `experiments/
    local_stream/agent.extract_code`, loaded from its own pinned AST node by
    :func:`_real_extract_code`, never a reimplementation -- returns non-whitespace output.

    Neither half is the rule by itself: an empty first fence (`` ```python\\n\\n``` ``) has a
    code block `_CODE_BLOCK_RE` matches, but the real extractor returns only `'\\n'` for it
    (`.strip()` empties it, so this reports `False`); unfenced prose has non-empty real-extractor
    output through its non-fence fallback branch, but no fence at all (also `False`).  Only a
    response with an actual fence whose first block extracts to something other than whitespace
    reports `True`."""
    if not contains_code_block(text):
        return False
    return _real_extract_code(str(text)).strip() != ''


def probe_prompt(base_url, prompt_id, prompt_text, *, target_kind, sampling, seed=1,
                 session=None, timeout_s=120.0) -> dict:
    """One format-conformance probe request: `POST /v1/chat/completions` with `prompt_text` as
    the sole user message, exactly as `lab_data.normalize_prompt`'s callers already format a
    task's prompt for the pilot -- no template wrapping is added here, since the ten
    out-of-design/smoke prompts of `config.json:209-218` are already complete function-signature
    prompts, not raw task text.

    Any transport failure (connection error, timeout, non-200, unparseable JSON, no `choices[0]
    .message.content`) reports `ok_transport=False, has_code_block=False, conforms=False` -- a
    response that was never received cannot contain an extractable code block, matching 5.8's own
    framing of stage 1's quantities as "durations, memory, receipt equality, ... and the yes/no
    extractability of a code block" (`protocol_FINAL.md:1335`) -- rather than raising and losing
    the other nine prompts' results.

    `has_code_block` (fence presence, :func:`contains_code_block`) is kept alongside the frozen
    `conforms` (:func:`conforms`, root's 2026-09-26 10:19 conjunction) for the same reason
    `_count_conforming`'s own docstring warns against conflating `has_code_block` with
    `ok_transport`: keeping both raw signals lets a later reviewer tell a missing fence apart
    from a fenced-but-empty first block, rather than collapsing both into one bit.  `usage` (the
    response's own token-usage object, or `None` when the mock/server omitted it) and
    `content_sha256` are kept on every ok_transport response so a later real stage-1 run
    preserves the original per-prompt response and usage, not merely the pass/fail verdict.

    `prompt_id`/`prompt_text` are NOT checked here against the predeclared ten (root's 2026-09-26
    13:20 review, finding 3's enumeration): this function makes no PASS/FAIL verdict and has
    exactly one caller in this repository, :func:`run_conformance_probe`, which performs the full
    frozen-set/text check (:func:`_predeclared_prompt_ids`/:func:`_predeclared_conformance_text`)
    on every prompt before calling this per-request primitive.  Classified PROVABLY IRRELEVANT to
    the frozen-gate concern rather than duplicated here."""
    assert_mock_target(base_url, target_kind)
    _assert_frozen_sampling(sampling)
    sess = session if session is not None else requests
    root = str(base_url).rstrip('/')
    body: dict = {'model': 'lab_stage1_conformance_probe',
                 'messages': [{'role': 'user', 'content': str(prompt_text)}]}
    body.update(dict(sampling))
    body['seed'] = int(seed)
    body.setdefault('stream', False)
    out: dict = {'id': str(prompt_id), 'request_sha256': lab_common.sha256_canonical(body)}
    try:
        r = sess.post(root + '/v1/chat/completions', json=body, timeout=timeout_s)
    except requests.RequestException as exc:
        out.update(ok_transport=False, has_code_block=False, conforms=False, status_code=None,
                   error=str(exc))
        return out
    if r.status_code != 200:
        out.update(ok_transport=False, has_code_block=False, conforms=False,
                   status_code=r.status_code, error=f'HTTP {r.status_code}')
        return out
    try:
        data = r.json()
    except ValueError as exc:
        out.update(ok_transport=False, has_code_block=False, conforms=False,
                   status_code=r.status_code, error=f'invalid JSON: {exc}')
        return out
    content = None
    if isinstance(data, Mapping):
        choices = data.get('choices')
        if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
            message = choices[0].get('message')
            if isinstance(message, Mapping):
                content = message.get('content')
    if content is None:
        out.update(ok_transport=False, has_code_block=False, conforms=False,
                   status_code=r.status_code, error='no choices[0].message.content in response')
        return out
    usage = data.get('usage') if isinstance(data, Mapping) else None
    out.update(ok_transport=True, has_code_block=contains_code_block(content),
               conforms=conforms(content), status_code=r.status_code, error=None,
               content_sha256=lab_common.sha256_text(str(content)),
               usage=dict(usage) if isinstance(usage, Mapping) else None)
    return out


def _count_conforming(rows) -> int:
    """[pure] The number of `rows` (each a :func:`probe_prompt` result) whose `conforms` is true
    -- root's 2026-09-26 10:19 frozen predicate (:func:`conforms`: a fence AND the real
    extractor's non-whitespace output), NEVER `ok_transport` (a materially weaker quantity:
    `lab_mock_server` happens to wrap every successful response body in a real fenced program,
    `_build_response`, even the `kind='smoke'` `'pong'` reply, so on scripted fixtures alone
    `ok_transport` and `conforms` agree and a field-swap bug would pass unnoticed) and NEVER bare
    `has_code_block` (fence presence alone is the reading root's 10:19 ruling rejected: it also
    counts an empty first fence as conforming, which `conforms` does not).  Extracted to its own
    function precisely so `tests_stage1.ConformanceCounterTests.test_negative_counts_code_block_
    presence_not_transport_success` can pin this exact counting rule down against synthetic rows
    where the fields disagree, independent of the mock server's fixture choices."""
    return sum(1 for row in rows if row['conforms'])


def _verdict(n_with_code_block, threshold) -> str:
    """[pure] `n_with_code_block >= threshold` -- an integer comparison, so "PASS at 9 of 10" is
    never reached by rounding a smaller count up.  Extracted to its own function so a test can
    call the REAL comparison directly: the mutation control this module shipped with originally
    hardcoded `'PASS' if 9 >= 9 else 'FAIL'` as a literal Python expression and never imported or
    called anything in this module, so it proved nothing about the real boundary check (an
    independent adversarial review's finding 3); `tests_stage1.MutationControlTests` now calls
    this function itself."""
    return 'PASS' if int(n_with_code_block) >= int(threshold) else 'FAIL'


def _frozen_conformance_threshold() -> int:
    """[pure-ish] `config.json`'s own `prefreeze.format_conformance_min` -- protocol 2.4 item 6's
    "non-amendable success margin" (`protocol_FINAL.md:3018,3773`), read through
    `lab_common.harness_config()` (already in this module's MATRIX row), never hardcoded here so
    this module cannot itself drift from root's frozen value.  Refuses (:class:`Stage1Error`) if
    config.json no longer declares it as an int, so a config drift is caught here rather than
    silently comparing against `None` or a wrong type."""
    cfg = lab_common.harness_config()
    raw = (cfg.get('prefreeze') or {}).get('format_conformance_min')
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise Stage1Error(
            f'config.json prefreeze.format_conformance_min must be an int; got {raw!r}')
    return raw


def _assert_frozen_threshold(threshold) -> int:
    """[pure-ish] Refuse (:class:`ThresholdRefused`) unless `threshold` equals
    :func:`_frozen_conformance_threshold`'s value exactly -- root's 2026-09-26 13:20 ruling,
    finding 2: "the non-amendable success margin is caller-controlled".  Root's witness: with all
    ten HTTP responses forced to 500 (zero conforming), `run_conformance_probe` returned PASS
    when called with `threshold=0`, because the caller-supplied threshold was never checked
    against config.json's own frozen value.  Called before any request or resume in both
    :func:`run_conformance_probe` and :func:`conformance_shard`.  Returns the frozen value so a
    caller of either function need not read config.json a second time."""
    frozen = _frozen_conformance_threshold()
    if int(threshold) != frozen:
        raise ThresholdRefused(
            f'threshold={threshold!r} disagrees with the frozen, non-amendable config.json '
            f'prefreeze.format_conformance_min={frozen!r} (protocol 2.4 item 6); lab_stage1 '
            'never accepts a different conformance margin, before any request or resume.')
    return frozen


def _frozen_sampling() -> dict:
    """[pure-ish] `config.json`'s own top-level `sampling` object -- protocol_FINAL.md:3018's
    "every sampling parameter" (non-amendable), read through `lab_common.harness_config()`
    (already in this module's MATRIX row), never hardcoded here so this module cannot itself
    drift from root's frozen value.  Refuses (:class:`Stage1Error`) if config.json no longer
    declares it as a non-empty JSON object, so a config drift is caught here rather than silently
    comparing against `None` or an empty mapping (which would make every `sampling` refuse, or
    -- worse -- every `sampling` agree)."""
    cfg = lab_common.harness_config()
    raw = cfg.get('sampling')
    if not isinstance(raw, Mapping) or not raw:
        raise Stage1Error(f'config.json sampling must be a non-empty JSON object; got {raw!r}')
    return dict(raw)


def _assert_frozen_sampling(sampling) -> dict:
    """[pure-ish] Refuse (:class:`SamplingRefused`) unless `sampling` equals
    :func:`_frozen_sampling`'s value exactly -- independent adversarial review of the 2026-09-26
    13:20 repair: "sampling (including max_tokens) is entirely caller-controlled and
    unvalidated, in every public entry point."  Live witness: `run_conformance_probe` with
    `sampling={'temperature': 1.9, 'max_tokens': 3}` (missing every other frozen key) returned a
    PASS verdict with no refusal, and `capture_reference` wrote that same rogue sampling straight
    into the golden `generation_settings` object every later trial receipt is compared against
    (protocol 13.2).  Called before any request in :func:`capture_reference`,
    :func:`probe_prompt`, :func:`run_conformance_probe`, and before any resume in
    :func:`golden_shard`/:func:`conformance_shard` -- the same placement
    :func:`_assert_frozen_threshold` already uses.  Returns the frozen value so a caller need not
    read config.json a second time."""
    frozen = _frozen_sampling()
    got = dict(sampling)
    if got != frozen:
        raise SamplingRefused(
            f'sampling={got!r} disagrees with the frozen, non-amendable config.json '
            f'sampling={frozen!r} (protocol_FINAL.md:3018, "every sampling parameter" is '
            'non-amendable, the same freeze class as the prompts and the threshold); lab_stage1 '
            'never accepts a different sampling block, before any request or resume.')
    return frozen


def run_conformance_probe(base_url, prompts, *, target_kind, sampling, threshold, seed=1,
                          session=None) -> dict:
    """The format-conformance counter of protocol_FINAL.md:585-587: "**Format-conformance rule
    (outcome-blind).** On the ten out-of-design prompts of 5.8, at least 9 of 10 responses of
    **each** model contain a code block that `extract_code` turns into a non-empty program.
    Correctness of the program is neither computed nor looked at." (See :func:`contains_code_block`
    for why this driver implements a stricter-than-fully-literal reading of that rule, flagged
    there for root, not adjudicated by the 07:18 bounded review.)

    `prompts` is an iterable of `{'id': ..., 'prompt': ...}` mappings; the caller assembles the
    full ten-prompt set (the six smoke tasks plus the four `config.json:209-218`
    `prefreeze.conformance_prompts`), but this function no longer trusts that blindly (root's
    2026-09-26 10:19 review, finding 2, extended by the 13:20 review, finding 1): before any
    request is sent, `assert_mock_target` runs first, then it REFUSES (:class:`PromptSetRefused`)
    unless `prompts` is exactly ten items, its ids are exactly config.json's predeclared ten
    (:func:`_predeclared_prompt_ids`), and EVERY one of the ten -- the four inline
    `conformance_prompts` AND the six `roster.smoke_tasks`, DERIVED from their pinned MBPP source
    through the frozen normalization/template path -- carries exactly its predeclared text
    (:func:`_predeclared_conformance_text`) -- never a rerouted/duplicated/truncated probe list,
    and never a silently-substituted out-of-design OR smoke prompt.  `threshold` must equal
    `config.json`'s own `prefreeze.format_conformance_min` (named non-amendable,
    `protocol_FINAL.md:3018,3773`) exactly, checked by :func:`_assert_frozen_threshold`
    (:class:`ThresholdRefused` otherwise, root's 2026-09-26 13:20 review, finding 2) before any
    request -- this module never silently adopts or accepts a different conformance margin.
    Counting is :func:`_count_conforming` (root's 10:19 `conforms` predicate, never transport
    success or fence-presence alone) and the verdict is :func:`_verdict` (never rounded up); both
    are separate, directly-testable pure functions rather than inlined here.

    Returns `{'n_prompts', 'n_with_code_block', 'threshold', 'verdict' ('PASS'/'FAIL'),
    'per_prompt': [<probe_prompt result>, ...]}` (the `n_with_code_block` member name is
    unchanged for compatibility with existing callers/receipts; its value is now the count of
    `conforms`, per :func:`_count_conforming`)."""
    assert_mock_target(base_url, target_kind)
    _assert_frozen_threshold(threshold)
    _assert_frozen_sampling(sampling)
    prompts = list(prompts)
    if len(prompts) != 10:
        raise PromptSetRefused(
            f'run_conformance_probe requires exactly ten prompts (protocol 5.8); got '
            f'{len(prompts)}')
    ids = [str(p['id']) for p in prompts]
    if len(set(ids)) != len(ids):
        raise PromptSetRefused(f'run_conformance_probe prompt ids must be distinct; got {ids}')
    predeclared = _predeclared_prompt_ids()
    if frozenset(ids) != predeclared:
        extra = sorted(frozenset(ids) - predeclared)
        missing = sorted(predeclared - frozenset(ids))
        raise PromptSetRefused(
            'run_conformance_probe prompts must be exactly config.json\'s predeclared ten ids '
            f'(roster.smoke_tasks + prefreeze.conformance_prompts); extra={extra} missing='
            f'{missing}')
    declared_text = _predeclared_conformance_text()
    for p in prompts:
        want = declared_text.get(str(p['id']))
        if want is not None and str(p['prompt']) != want:
            raise PromptSetRefused(
                f"run_conformance_probe prompt {p['id']!r} text disagrees with its predeclared "
                'text (config.json prefreeze.conformance_prompts, or the derived mbpp_full '
                'smoke-task text)')
    rows = [probe_prompt(base_url, p['id'], p['prompt'], target_kind=target_kind,
                        sampling=sampling, seed=seed, session=session)
           for p in prompts]
    n_with_code_block = _count_conforming(rows)
    return {
        'n_prompts': len(rows),
        'n_with_code_block': n_with_code_block,
        'threshold': int(threshold),
        'verdict': _verdict(n_with_code_block, threshold),
        'per_prompt': rows,
    }


def conformance_shard(*, base_url, prompts, server_id, receipts_dir, inv, target_kind, sampling,
                      threshold, pins, out_dir=None, prefreeze_root=None, seed=1, session=None,
                      subtree='stage1_conformance', create=True) -> dict:
    """One format-conformance completed-shard unit for one server, the counter half of
    design_notes/DESIGN_PROPOSAL.md section 3 item 4 (see :func:`golden_shard` for the parallel
    golden-capture half; the two share the same resume/`_prefreeze`/shard-receipt discipline, and
    this docstring only names what differs).  Resumes through :func:`_effective_pins` of
    `pins`/`sampling`/`seed`/`threshold`, the same fix :func:`golden_shard`/:func:`_effective_pins`
    document for the resume-silently-ignores-request-fields gap an independent adversarial review
    reproduced.

    When `out_dir` is given, the full `run_conformance_probe` report is deposited write-once at
    `<out_dir>/conformance_<server_id>.json` and its digest enters `outputs`; when `out_dir` is
    `None` the shard's `outputs` is empty (nothing is persisted to disk beyond the receipt
    itself) -- `lab_shard_receipt.validate_receipt` accepts an empty `outputs` mapping, and a
    probe run purely to exercise this driver need not always write a results file.  Returns the
    full validated receipt dict in both cases (resumed or freshly recorded), for the same reason
    :func:`golden_shard` re-reads its own write through `lab_prefreeze.resume_shard`.

    `assert_mock_target` is called FIRST, before any resume check (root's 2026-09-26 10:19
    review, finding 3), the same fix :func:`golden_shard` documents.  `threshold` is then checked
    against the frozen, non-amendable config.json margin (:func:`_assert_frozen_threshold`,
    :class:`ThresholdRefused` otherwise, root's 2026-09-26 13:20 review, finding 2) -- also before
    any resume, so a caller cannot obtain a stale receipt under a changed threshold merely by
    finding one already on disk.  The resume pins also fold in the exact ORDERED `(id, prompt)`
    pairs of `prompts` (root's 2026-09-26 10:19 review, finding 1): a changed prompt text, a
    changed id, or a changed order at an otherwise-unchanged caller `pins` now raises
    `lab_shard_receipt.ResumeMismatch` on resume rather than silently reusing the stale receipt --
    `run_conformance_probe` itself is called only after the resume check (or not at all, if
    resumed), so its own :class:`PromptSetRefused` guard runs on every FRESH attempt but is never
    reached, and never needs to be, on a legitimate resume.  The resume pins also fold in three
    static source-identity pins (root's 2026-09-26 13:20 review, finding 1):
    :data:`_AGENT_PY_SHA256` (`extract_code_source_sha256`, the pinned identity of the REAL
    first-block extractor :func:`conforms` defers to, finding 2 of the 10:19 review),
    :data:`_DATA_PY_SHA256` (`mbpp_entry_point_source_sha256`) and :data:`_MBPP_FULL_SOURCE`'s
    `sha256` (`smoke_prompt_source_sha256`) -- the pinned identities of the two pilot/roster
    sources :func:`_predeclared_smoke_prompt_texts` derives the six smoke prompts from.  A
    receipt recorded under one pinned source and later resumed after a REVIEWED change to any of
    these three constants is refused rather than silently reused under the new source's
    semantics; this is provenance on top of, not instead of, the hard runtime hash checks
    :func:`_load_agent_ast_functions`/:func:`_load_pilot_mbpp_entry_point`/
    :func:`_load_mbpp_full_records` already perform against the files on disk."""
    assert_mock_target(base_url, target_kind)
    _assert_frozen_threshold(threshold)
    _assert_frozen_sampling(sampling)
    schedule_row = {'unit': 'conformance_probe', 'server_id': str(server_id)}
    prompts = list(prompts)
    output_rel = {}
    if out_dir is not None:
        output_rel['report'] = 'conformance_%s.json' % server_id
    ordered_prompts = [(str(p['id']), str(p['prompt'])) for p in prompts]
    resume_pins = _effective_pins(pins, sampling=dict(sampling), seed=int(seed),
                                  threshold=int(threshold), prompts=ordered_prompts,
                                  extract_code_source_sha256=_AGENT_PY_SHA256,
                                  mbpp_entry_point_source_sha256=_DATA_PY_SHA256,
                                  smoke_prompt_source_sha256=_MBPP_FULL_SOURCE['sha256'])
    resumed = lab_prefreeze.resume_shard(
        receipts_dir, 'stage1_conformance', schedule_row, expected_pins=resume_pins,
        expected_output_paths=list(output_rel.values()),
        root_for_outputs=(out_dir if out_dir is not None else receipts_dir))
    if resumed is not None:
        return resumed
    start_utc = _utcnow()
    chain = lab_prefreeze.open_prefreeze('smoke', inv=inv, root=prefreeze_root, subtree=subtree,
                                         create=create)
    try:
        report = run_conformance_probe(base_url, prompts, target_kind=target_kind,
                                       sampling=sampling, threshold=threshold, seed=seed,
                                       session=session)
        outputs = {}
        if out_dir is not None:
            report_path = Path(out_dir) / output_rel['report']
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            outputs[output_rel['report']] = lab_common.write_json_atomic(
                report_path, report, durable=True)
    finally:
        chain.close()
    end_utc = _utcnow()
    inputs = {
        'base_url': str(base_url), 'server_id': str(server_id),
        'n_prompts': report['n_prompts'], 'threshold': report['threshold'],
        'verdict': report['verdict'], 'prefreeze_head': chain.head,
    }
    lab_prefreeze.record_shard(
        receipts_dir, 'stage1_conformance', schedule_row, pins=resume_pins, inputs=inputs,
        outputs=outputs, start_utc=start_utc, end_utc=end_utc, outcome='success')
    written = lab_prefreeze.resume_shard(
        receipts_dir, 'stage1_conformance', schedule_row, expected_pins=resume_pins,
        expected_output_paths=list(output_rel.values()),
        root_for_outputs=(out_dir if out_dir is not None else receipts_dir))
    assert written is not None, 'the receipt just written must itself resume successfully'
    return written
