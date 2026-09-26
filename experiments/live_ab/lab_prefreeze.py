"""The `_prefreeze` chain runner scaffold (design_notes/DESIGN_PROPOSAL.md section 3 item 3,
section 8's OD on the `_prefreeze` subtree default and the new `E_PHASE` values, and section 9).
Third of the drivers-plan commits: a shared, driver-facing module every stage 1-6 driver opens
its pre-freeze logging through, so no driver hand-rolls chain hashing or a receipt shape of its
own.

What this module PERFORMS, and nothing else:

* :func:`open_prefreeze` -- opens a `_prefreeze` chain (or a segregated subtree of it,
  section 8's default for a phase root has not yet named) through `lab_eventlog.EventLog`
  alone: no hashing, chaining, segment rollover or torn-write recovery is reimplemented here.
  The chain id written into every event is always `lab_common.PREFREEZE_CHAIN_ID` and the
  genesis anchor is always the literal token `'prefreeze'` (`lab_eventlog.genesis_prev`'s own
  rule for the pre-freeze chain, written before any freeze bundle exists) -- neither is ever a
  parameter, so nothing this module opens can become, or be silently redirected into, a trial
  chain.
* Every open and every write is gated on `phase`, checked ONLY against `VALID_PHASES` --
  the pre-freeze-relevant SUBSET of `lab_eventlog.E_PHASE` (`prefreeze`/`smoke`/`server_smoke`;
  bare `lab_eventlog.py` line numbers cited only in prose, never as a resolvable citation of a
  checked-in path), never the whole enum: `E_PHASE` is shared with the trial/program invocation
  state machine, and its `randomizing`/`draining`/`post_decision`/`paused`/`ended`/`aborted`
  members name a LIVE TRIAL's own lifecycle, not anything a `_prefreeze` chain may carry, so
  this module refuses those the same as any undefined string. `timing_pilot`/`rehearsal`
  (section 8's own examples of a value protocol_FINAL.md section 5.8 names but `E_PHASE` does
  not yet carry) are refused with a named error, `UndefinedPhaseError`, until root adds that
  value -- never guessed, never normalized (a case, whitespace or alias variant of an existing
  value is refused exactly like a wholly unknown one, since silently accepting one would be
  the same guess in different clothes).
* :func:`prefreeze_root` / :func:`prefreeze_events_dir` -- the path safety this module owns:
  the resolved (every symlink followed) pre-freeze directory's own name must be exactly
  `lab_common.PREFREEZE_CHAIN_ID`, a segregated subtree's resolved parent must be exactly that
  directory, and the final `events` leaf's resolved parent must be exactly that (sub)tree -- so
  a trial chain, the program chain, a `..` traversal, or a symlink planted at ANY of the three
  levels is refused (`PrefreezePathError`) before `lab_eventlog.EventLog` ever opens a file
  descriptor.
* :class:`PrefreezeChain` -- the open handle: `append` (one event, through
  `lab_eventlog.EventLog.append` alone) and `close` (writes the closing `prefreeze_closed`
  event -- `head`/`bytes`/`file_sha256` of the chain as of just before that event, this
  chain's own `phase`, and `n_events` -- then closes the underlying log).  Every event this
  writes carries the SAME already-validated `phase` this handle opened with; a caller naming a
  different one in `body` is refused before anything is written, so one open handle can never
  silently mix phases.
* :func:`resume_shard` / :func:`record_shard` -- the write-once completed-shard receipt per
  finished unit, both thin calls into `lab_shard_receipt` and nothing else: `record_shard`
  builds the receipt shape section 4/5 requires and writes it through
  `lab_shard_receipt.write_shard_receipt`; `resume_shard` is the ONLY legal resume check --
  `None` when the shard is not yet present, otherwise the receipt `lab_shard_receipt.verify_resume`
  itself validated against the caller's CURRENT pins, schedule row and output hashes.  A driver
  that only tests `shard_id in lab_shard_receipt.completed_shards(...)` and then reuses the
  shard's outputs without going through `resume_shard` is doing exactly the presence-only
  resume root's replay-resume-provenance finding refused
  (`reviews/driver_replay_resume_interim_20260926_0117.md`, cited by single backtick and no
  line: that file lives on `origin/main`, not on this branch's history, and root's 22:20 review
  of the accepted EB1+EB5 subset -- `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`,
  same citation form -- is what names the incremental immutable completed-shard receipt this
  module reuses rather than reinvents).

Deliberately NOT here: no stage 1-6 semantics, no server, no model, no schedule generation, no
new `E_PHASE`/event-schema value (root's schema decision, section 8's OD, is never pre-empted),
and no decision about whether a given driver's data belongs in `results/live_ab/_prefreeze/`
itself or a named subtree -- that placement call is the caller's, this module only refuses an
unsafe one. This keeps `lab_prefreeze` importable by every future driver without dragging in any
of their stage logic, and keeps it out of `lab_design`'s own import row: nothing this module
writes is ever read back as a design input (protocol_FINAL.md 5.8, "Success outcomes of these
runs are never used for any design choice" -- the same discipline extended here to every
`_prefreeze` write this scaffold makes, not only the outcome fields 5.8 already names).

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import lab_common
import lab_eventlog
import lab_shard_receipt

#: The closed vocabulary this module will ever write a `phase` as -- NOT all of
#: `lab_eventlog.E_PHASE` (that enum is shared with the trial/program invocation state machine:
#: `randomizing`/`draining`/`post_decision`/`paused`/`ended`/`aborted` name a LIVE trial's own
#: lifecycle and can never legitimately land on a `_prefreeze` chain this module opens). This is
#: the pre-freeze-relevant subset protocol_FINAL.md 5.8/12.1 name for the `_prefreeze` chain
#: (`SMOKE`/`TIMING_PILOT`/`SERVER_SMOKE`/`REHEARSAL`, case folded to `E_PHASE`'s own spelling)
#: intersected with what `E_PHASE` already defines -- `timing_pilot`/`rehearsal` are not yet
#: members and stay refused by :func:`open_prefreeze` exactly like any other undefined value.
#: The assertion below is a load-time trip-wire: if root ever renamed or dropped one of these
#: three from `E_PHASE`, importing this module fails loudly instead of this constant silently
#: keeping a stale, now-undefined string.
_PREFREEZE_PHASE_NAMES = frozenset({'prefreeze', 'smoke', 'server_smoke'})
assert _PREFREEZE_PHASE_NAMES <= set(lab_eventlog.E_PHASE.enum), (
    'lab_eventlog.E_PHASE no longer defines one of lab_prefreeze._PREFREEZE_PHASE_NAMES -- '
    'update this module rather than silently keeping a stale phase name')
VALID_PHASES: frozenset[str] = _PREFREEZE_PHASE_NAMES

#: A segregated subtree name (section 8: e.g. `rehearsal`): no path separator, no `.`, so it
#: can never itself carry a traversal component.
_SUBTREE_RE = re.compile(r'^[A-Za-z0-9_-]+$')


class PrefreezeError(lab_common.LabError):
    """Root of every refusal this module raises."""


class UndefinedPhaseError(PrefreezeError):
    """`phase` is not one of :data:`VALID_PHASES` -- either a string `lab_eventlog.E_PHASE`
    does not define at all (root must add it, an `E_PHASE` schema amendment, before this runner
    may write it), or a real `E_PHASE` member that names a trial/program invocation-lifecycle
    state (`randomizing`/`draining`/`post_decision`/`paused`/`ended`/`aborted`) rather than
    anything the `_prefreeze` chain may carry. This module never guesses an enum string and
    never normalizes a near-miss into an accepted one."""


class PrefreezePathError(PrefreezeError):
    """The resolved directory is not a legitimate `_prefreeze` (sub)tree: a trial chain, the
    program chain, a path outside the pre-freeze root, a `..` traversal, or a symlink escape."""


def prefreeze_root(root: 'str | Path | None' = None) -> Path:
    """The canonical `_prefreeze` directory (`lab_common.RESULTS_ROOT` /
    `lab_common.PREFREEZE_CHAIN_ID`), or -- for an isolated test tree -- `root` itself.  Refused
    unless, after resolving every symlink on the way, the directory's OWN name is exactly
    `lab_common.PREFREEZE_CHAIN_ID`: a trial directory (`T1`..`T4`), the program directory
    (`lab_common.PROGRAM_CHAIN_ID`), or any other path -- reached directly, by a `..` segment, or
    by a symlink planted at this level -- resolves to a different name and is refused before any
    file is touched.
    """
    base = Path(root) if root is not None else lab_common.RESULTS_ROOT / lab_common.PREFREEZE_CHAIN_ID
    resolved = base.resolve()
    if resolved.name != lab_common.PREFREEZE_CHAIN_ID:
        raise PrefreezePathError(
            f'{base} resolves to {resolved}, whose name is {resolved.name!r}, not '
            f'{lab_common.PREFREEZE_CHAIN_ID!r} -- refusing to treat a trial chain, the program '
            'chain, or any other path as the pre-freeze tree')
    return resolved


def prefreeze_events_dir(root: 'str | Path | None' = None, *,
                         subtree: 'str | None' = None) -> Path:
    """The chain-segment directory for the canonical `_prefreeze` chain, or -- when `subtree` is
    given -- a segregated subtree of it (section 8's default placement for a phase the schema
    does not yet cover: "write under a segregated subtree ... never default to writing into the
    trial chain itself").  `subtree` must match `_SUBTREE_RE`; its resolved location must then be
    exactly a child of :func:`prefreeze_root`'s own resolved directory, so neither a symlink
    planted at the subtree itself nor one planted at the pre-freeze root can steer this outside
    the pre-freeze tree.  The final `events` leaf is checked the SAME way (its resolved parent
    must be exactly the already-verified container), so a symlink planted at the `events` name
    itself -- rather than at the subtree or pre-freeze-root level -- is refused too, before
    `lab_eventlog.EventLog` ever creates or opens it.
    """
    proot = prefreeze_root(root)
    if subtree is None:
        container = proot
    else:
        if not isinstance(subtree, str) or not _SUBTREE_RE.match(subtree):
            raise PrefreezePathError(
                f'subtree {subtree!r} must match {_SUBTREE_RE.pattern!r} -- a path separator or '
                "'..' component could steer this outside its own segregated _prefreeze subtree")
        sub = proot / subtree
        resolved_sub = sub.resolve()
        if resolved_sub.parent != proot:
            raise PrefreezePathError(
                f'segregated subtree {subtree!r} resolves to {resolved_sub}, whose parent is not '
                f'the pre-freeze root {proot} -- refusing a symlink or traversal escape')
        container = resolved_sub
    events = container / 'events'
    resolved_events = events.resolve()
    if resolved_events.parent != container:
        raise PrefreezePathError(
            f'the events directory {events} resolves to {resolved_events}, whose parent is not '
            f'{container} -- refusing a symlink planted at the events leaf itself')
    return resolved_events


def _segment_digest(events_dir: Path) -> tuple[int, str]:
    """[pure] `(total_bytes, sha256)` of every existing chain segment under `events_dir`,
    concatenated in `lab_eventlog.segment_paths` order -- the same bytes `lab_eventlog.read_chain`
    itself parses, measured and hashed exactly once here rather than reimplemented at each call
    site."""
    blob = b''.join(p.read_bytes() for p in lab_eventlog.segment_paths(events_dir))
    return len(blob), lab_common.sha256_bytes(blob)


class PrefreezeChain:
    """A single-writer handle on one `_prefreeze` chain segment tree (the canonical chain, or a
    segregated subtree), opened by :func:`open_prefreeze`.  Every event it writes carries
    `chain == lab_common.PREFREEZE_CHAIN_ID` (hardcoded at open time, never a parameter of this
    class) and this handle's own already-validated `phase`, so it can never become, or be
    mistaken for, a trial chain, and can never silently mix phases on one open chain.
    """

    def __init__(self, log: lab_eventlog.EventLog, phase: str) -> None:
        self._log = log
        self.phase = phase

    @property
    def events_dir(self) -> Path:
        return self._log.events_dir

    @property
    def head(self) -> str:
        return self._log.head

    @property
    def seq(self) -> int:
        return self._log.seq

    def append(self, etype: str, body: Mapping, *, durable: bool = False) -> dict:
        """Append one event through `lab_eventlog.EventLog.append` alone -- no hashing or
        chaining is reimplemented here.  When `body` itself names a `phase` that differs from
        this handle's own already-validated `phase`, the write is refused before anything is
        written: a caller mixing phases on one open chain must open a separate
        :class:`PrefreezeChain` instead."""
        body = dict(body)
        if 'phase' in body and body['phase'] != self.phase:
            raise UndefinedPhaseError(
                f"body['phase']={body['phase']!r} does not match this chain's own validated "
                f'phase {self.phase!r} -- open a separate PrefreezeChain for a different phase '
                'rather than mixing phases on one open handle')
        return self._log.append(etype, body, durable=durable)

    def close(self, *, durable: bool = True) -> dict:
        """Append `prefreeze_closed` -- `head`/`bytes`/`file_sha256` of the chain as of just
        before this event, this handle's `phase`, and `n_events` -- then close the underlying
        `lab_eventlog.EventLog`.  Returns the `prefreeze_closed` event."""
        head_before = self._log.head
        n_before = self._log.seq
        total_bytes, file_sha256 = _segment_digest(self._log.events_dir)
        ev = self.append('prefreeze_closed', {
            'head': head_before, 'bytes': total_bytes, 'file_sha256': file_sha256,
            'phase': self.phase, 'n_events': n_before}, durable=durable)
        self._log.close()
        return ev

    def __enter__(self) -> 'PrefreezeChain':
        return self

    def __exit__(self, *exc: object) -> None:
        self._log.close()


def open_prefreeze(phase: str, *, inv: str, root: 'str | Path | None' = None,
                   subtree: 'str | None' = None, create: bool = False) -> PrefreezeChain:
    """Open the `_prefreeze` chain (or, with `subtree`, a segregated subtree of it) and return a
    :class:`PrefreezeChain` bound to `phase`.  Refuses (`UndefinedPhaseError`) any `phase` not
    already in :data:`VALID_PHASES` -- the pre-freeze-relevant SUBSET of `lab_eventlog.E_PHASE`,
    never the whole enum (a real `E_PHASE` member that names a trial/program invocation-lifecycle
    state, e.g. `randomizing`/`ended`/`aborted`, is refused exactly like an undefined string) --
    with no normalization of case, whitespace or an alias, before any directory or file is
    touched.  The chain id and genesis anchor are never parameters: they are always
    `lab_common.PREFREEZE_CHAIN_ID` and the literal token `'prefreeze'`
    (`lab_eventlog.genesis_prev`'s own rule for the pre-freeze chain).
    """
    if not isinstance(phase, str) or phase not in VALID_PHASES:
        raise UndefinedPhaseError(
            f'phase {phase!r} is not one of lab_prefreeze.VALID_PHASES '
            f'({sorted(VALID_PHASES)}) -- either not an lab_eventlog.E_PHASE member at all '
            '(root must add it to the schema first) or a real E_PHASE member that names a '
            'trial/program invocation-lifecycle state rather than anything the _prefreeze '
            'chain may carry -- refusing rather than guessing an enum string '
            '(design_notes/DESIGN_PROPOSAL.md section 8)')
    events_dir = prefreeze_events_dir(root, subtree=subtree)
    log = lab_eventlog.EventLog(events_dir, lab_common.PREFREEZE_CHAIN_ID, 'prefreeze', inv,
                                create=create)
    return PrefreezeChain(log, phase)


def resume_shard(receipts_dir: 'str | Path', driver: str, schedule_row: Mapping, *,
                 expected_pins: Mapping, expected_output_paths, root_for_outputs: 'str | Path'
                 ) -> 'dict | None':
    """The ONLY legal resume check a driver built on this module may use ("resumes ONLY through
    `lab_shard_receipt.verify_resume` with the current pins ... never a presence-only resume"):
    `None` when the shard is not yet in `lab_shard_receipt.completed_shards`; otherwise the
    receipt `lab_shard_receipt.verify_resume` itself read, fully validated and compared against
    `expected_pins`/`expected_output_paths` -- which raises `lab_shard_receipt.ResumeMismatch`,
    naming every field that differs, on any mismatch.  Never trusts presence by itself, and never
    repairs, rewrites or reruns anything."""
    sid = lab_shard_receipt.shard_id(driver, schedule_row)
    if sid not in lab_shard_receipt.completed_shards(receipts_dir):
        return None
    return lab_shard_receipt.verify_resume(
        receipts_dir, sid, driver=driver, schedule_row=schedule_row,
        expected_pins=expected_pins, expected_output_paths=expected_output_paths,
        root_for_outputs=root_for_outputs)


def record_shard(receipts_dir: 'str | Path', driver: str, schedule_row: Mapping, *,
                 pins: Mapping, inputs: Mapping, outputs: Mapping, start_utc: str, end_utc: str,
                 outcome: str, harness_pin_delta=()) -> str:
    """Build the write-once completed-shard receipt for one finished unit in the shape
    `lab_shard_receipt.validate_receipt` requires, and write it through
    `lab_shard_receipt.write_shard_receipt` alone -- never a bespoke JSON write. Returns the
    receipt's canonical sha256."""
    receipt = {
        'schema': lab_shard_receipt.SCHEMA,
        'shard_id': lab_shard_receipt.shard_id(driver, schedule_row),
        'driver': driver,
        'schedule_row': dict(schedule_row),
        'pins': dict(pins),
        'inputs': dict(inputs),
        'outputs': dict(outputs),
        'start_utc': start_utc,
        'end_utc': end_utc,
        'outcome': outcome,
        'harness_pin_delta': list(harness_pin_delta),
    }
    return lab_shard_receipt.write_shard_receipt(receipts_dir, receipt)
