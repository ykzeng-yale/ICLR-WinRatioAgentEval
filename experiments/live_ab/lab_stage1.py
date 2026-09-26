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

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import re
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
    `threshold`).

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
    `server_start_failed`."""
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

    This is therefore an UNREVIEWED INTERPRETIVE SCOPE DECISION this commit makes and flags for
    the record: root's 2026-09-26 07:18 bounded review authorized item 1's driver but did not
    adjudicate which of these two readings the format-conformance gate should use.  This function
    implements the stricter, fence-presence reading -- deliberately, since it is the one that can
    actually fail a model that never emits fenced code -- and never the looser one; it is sound
    in one direction only (`tests_stage1.ProtocolInterpretationTests` also checks that whenever
    this function reports `True`, the real `extract_code` never reports an effectively empty
    result), and root should confirm or override this choice before its PASS/FAIL verdict is
    treated as a scientific outcome."""
    if not text:
        return False
    return _CODE_BLOCK_RE.search(str(text)) is not None


def probe_prompt(base_url, prompt_id, prompt_text, *, target_kind, sampling, seed=1,
                 session=None, timeout_s=120.0) -> dict:
    """One format-conformance probe request: `POST /v1/chat/completions` with `prompt_text` as
    the sole user message, exactly as `lab_data.normalize_prompt`'s callers already format a
    task's prompt for the pilot -- no template wrapping is added here, since the ten
    out-of-design/smoke prompts of `config.json:209-218` are already complete function-signature
    prompts, not raw task text.

    Any transport failure (connection error, timeout, non-200, unparseable JSON, no `choices[0]
    .message.content`) reports `ok_transport=False, has_code_block=False` -- a response that was
    never received cannot contain an extractable code block, matching 5.8's own framing of
    stage 1's quantities as "durations, memory, receipt equality, ... and the yes/no
    extractability of a code block" (`protocol_FINAL.md:1335`) -- rather than raising and losing
    the other nine prompts' results."""
    assert_mock_target(base_url, target_kind)
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
        out.update(ok_transport=False, has_code_block=False, status_code=None, error=str(exc))
        return out
    if r.status_code != 200:
        out.update(ok_transport=False, has_code_block=False, status_code=r.status_code,
                   error=f'HTTP {r.status_code}')
        return out
    try:
        data = r.json()
    except ValueError as exc:
        out.update(ok_transport=False, has_code_block=False, status_code=r.status_code,
                   error=f'invalid JSON: {exc}')
        return out
    content = None
    if isinstance(data, Mapping):
        choices = data.get('choices')
        if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
            message = choices[0].get('message')
            if isinstance(message, Mapping):
                content = message.get('content')
    if content is None:
        out.update(ok_transport=False, has_code_block=False, status_code=r.status_code,
                   error='no choices[0].message.content in response')
        return out
    out.update(ok_transport=True, has_code_block=contains_code_block(content),
               status_code=r.status_code, error=None,
               content_sha256=lab_common.sha256_text(str(content)))
    return out


def _count_conforming(rows) -> int:
    """[pure] The number of `rows` (each a :func:`probe_prompt` result) whose `has_code_block` is
    true -- NEVER `ok_transport`, a materially weaker quantity: `lab_mock_server` happens to wrap
    every successful response body in a fence (`_build_response`, even the `kind='smoke'` `'pong'`
    reply), so on scripted fixtures alone the two fields agree and a `has_code_block` -> `
    ok_transport` field-swap bug would pass unnoticed.  Extracted to its own function precisely so
    `tests_stage1.ConformanceCounterTests.test_negative_counts_code_block_presence_not_transport_
    success` can pin this exact counting rule down against synthetic rows where the two fields
    disagree, independent of the mock server's fixture choices."""
    return sum(1 for row in rows if row['has_code_block'])


def _verdict(n_with_code_block, threshold) -> str:
    """[pure] `n_with_code_block >= threshold` -- an integer comparison, so "PASS at 9 of 10" is
    never reached by rounding a smaller count up.  Extracted to its own function so a test can
    call the REAL comparison directly: the mutation control this module shipped with originally
    hardcoded `'PASS' if 9 >= 9 else 'FAIL'` as a literal Python expression and never imported or
    called anything in this module, so it proved nothing about the real boundary check (an
    independent adversarial review's finding 3); `tests_stage1.MutationControlTests` now calls
    this function itself."""
    return 'PASS' if int(n_with_code_block) >= int(threshold) else 'FAIL'


def run_conformance_probe(base_url, prompts, *, target_kind, sampling, threshold, seed=1,
                          session=None) -> dict:
    """The format-conformance counter of protocol_FINAL.md:585-587: "**Format-conformance rule
    (outcome-blind).** On the ten out-of-design prompts of 5.8, at least 9 of 10 responses of
    **each** model contain a code block that `extract_code` turns into a non-empty program.
    Correctness of the program is neither computed nor looked at." (See :func:`contains_code_block`
    for why this driver implements a stricter-than-fully-literal reading of that rule, flagged
    there for root, not adjudicated by the 07:18 bounded review.)

    `prompts` is an iterable of `{'id': ..., 'prompt': ...}` mappings (the caller assembles the
    full ten-prompt set -- the six smoke tasks plus the four `config.json:209-218`
    `prefreeze.conformance_prompts` -- this function is agnostic to how many prompts it is given
    or where they came from).  `threshold` is `config.json`'s own `prefreeze.
    format_conformance_min` (named non-amendable, `protocol_FINAL.md:3018,3773`), passed by the
    caller rather than hardcoded here, so this module never silently adopts or drifts from root's
    frozen value.  Counting is :func:`_count_conforming` (never transport success) and the
    verdict is :func:`_verdict` (never rounded up); both are separate, directly-testable pure
    functions rather than inlined here.

    Returns `{'n_prompts', 'n_with_code_block', 'threshold', 'verdict' ('PASS'/'FAIL'),
    'per_prompt': [<probe_prompt result>, ...]}`."""
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
    :func:`golden_shard` re-reads its own write through `lab_prefreeze.resume_shard`."""
    schedule_row = {'unit': 'conformance_probe', 'server_id': str(server_id)}
    prompts = list(prompts)
    output_rel = {}
    if out_dir is not None:
        output_rel['report'] = 'conformance_%s.json' % server_id
    resume_pins = _effective_pins(pins, sampling=dict(sampling), seed=int(seed),
                                  threshold=int(threshold))
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
