"""Controls for `lab_prefreeze` (design_notes/DESIGN_PROPOSAL.md section 3 item 3): the shared
`_prefreeze` chain runner scaffold every stage 1-6 / 11.5 driver opens its pre-freeze logging
through, so no driver hand-rolls chain hashing, path safety or a receipt shape of its own.

Every positive check here has a NEGATIVE CONTROL beside it -- the same call on an input it must
refuse, asserted refused -- so none of these can pass by being unable to fail.  What runs:
`lab_prefreeze` in process against a plain temp directory standing in for `results/live_ab/`; no
server, no model, no subprocess.  :class:`MutationControlTests` goes one step further and proves
the undefined-phase control ITSELF can fail: it monkeypatches `open_prefreeze` to a
phase-gate-removed mutant and shows the same scenario `PhaseGateTests` checks no longer refuses.

Outside the `experiments/live_ab/tests_*.py` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_shard_receipt as sr                                          # noqa: E402
import lab_prefreeze as pf                                              # noqa: E402


def _inv() -> str:
    """A syntactically legal `inv` (exactly 32 hex chars, `lab_eventlog.validate_envelope`)."""
    return uuid.uuid4().hex


def _health_body(**extra) -> dict:
    base = {'server_id': 'coder', 'ok': True, 'slots_busy': 0, 'rss_bytes': 0,
           'clock_anomaly': False}
    base.update(extra)
    return base


def _pins(seed: int = 1) -> dict:
    return {
        'code': {'lab_prefreeze.py': 'a' * 64},
        'config': {'sha256': 'b' * 64},
        'seed': {'value': seed},
        'data': {},
    }


class _TmpDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='prefreeze_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # a standalone `_prefreeze` tree, not the real results/live_ab/ one
        self.root = self.tmp / '_prefreeze'


class PhaseGateTests(_TmpDirCase):
    """`open_prefreeze` writes only `lab_prefreeze.VALID_PHASES` -- the pre-freeze-relevant
    SUBSET of `lab_eventlog.E_PHASE` -- and refuses every other spelling: unknown, case-shifted,
    whitespace-padded or aliased, and every real `E_PHASE` member that names a trial/program
    invocation-lifecycle state instead of a pre-freeze one (see the lifecycle-phase test below)."""

    def test_positive_every_valid_phase_opens(self) -> None:
        for phase in sorted(pf.VALID_PHASES):
            with self.subTest(phase=phase):
                chain = pf.open_prefreeze(phase, inv=_inv(),
                                          root=self.tmp / f'root_{phase}' / '_prefreeze',
                                          create=True)
                try:
                    self.assertEqual(chain.phase, phase)
                finally:
                    chain._log.close()

    def test_negative_an_undefined_phase_is_refused(self) -> None:
        # section 8's own examples of a value protocol_FINAL.md 5.8 names but E_PHASE does not
        # yet carry
        for bad in ('timing_pilot', 'rehearsal'):
            with self.subTest(phase=bad):
                with self.assertRaises(pf.UndefinedPhaseError):
                    pf.open_prefreeze(bad, inv=_inv(), root=self.root, create=True)

    def test_negative_a_trial_or_program_lifecycle_phase_is_refused(self) -> None:
        # these ARE real lab_eventlog.E_PHASE members, but they name trial/program invocation
        # states (protocol_FINAL.md 5.8/12.1 name only SMOKE/TIMING_PILOT/SERVER_SMOKE/REHEARSAL
        # for the _prefreeze chain), never something this scaffold's own chain may carry
        for bad in ('randomizing', 'draining', 'post_decision', 'paused', 'ended', 'aborted'):
            with self.subTest(phase=bad):
                self.assertIn(bad, lab_eventlog.E_PHASE.enum,
                             'fixture drift: this must be a real E_PHASE member to prove the '
                             'point')
                # a distinct root per phase: once a mutant/regression lets one of these open, a
                # shared root would raise a fixture ChainError on the next subTest rather than
                # cleanly showing the refusal is missing
                with self.assertRaises(pf.UndefinedPhaseError):
                    pf.open_prefreeze(bad, inv=_inv(),
                                      root=self.tmp / f'lifecycle_{bad}' / '_prefreeze',
                                      create=True)

    def test_negative_a_case_whitespace_or_alias_variant_is_refused(self) -> None:
        for bad in ('Smoke', 'SMOKE', ' smoke', 'smoke ', 'smoke\n', 'pre freeze', 'pre-freeze',
                   'Prefreeze', ''):
            with self.subTest(phase=repr(bad)):
                with self.assertRaises(pf.UndefinedPhaseError):
                    pf.open_prefreeze(bad, inv=_inv(), root=self.root, create=True)

    def test_negative_a_non_string_phase_is_refused(self) -> None:
        for bad in (None, 1, ['smoke']):
            with self.subTest(phase=bad):
                with self.assertRaises(pf.UndefinedPhaseError):
                    pf.open_prefreeze(bad, inv=_inv(), root=self.root, create=True)

    def test_negative_a_body_naming_a_different_phase_is_refused_before_any_write(self) -> None:
        # Uses `prefreeze_closed`, the one etype whose OWN schema has a `phase` field, so a
        # mutant that dropped this handle-vs-body check would have `lab_eventlog.validate_event`
        # accept the write outright (schema-legal) rather than an unrelated SchemaError masking
        # whether this check itself ever ran -- `server_health`'s schema has no `phase` field at
        # all, so it would raise its OWN SchemaError even with the check removed, and a test built
        # on it cannot tell the two failures apart (confirmed against a check-removed mutant
        # under a disposable local worktree: the old body raised the unrelated SchemaError, this
        # one raised nothing at all).
        chain = pf.open_prefreeze('smoke', inv=_inv(), root=self.root, create=True)
        try:
            with self.assertRaises(pf.UndefinedPhaseError):
                chain.append('prefreeze_closed', {
                    'head': 'a' * 64, 'bytes': 0, 'file_sha256': 'b' * 64,
                    'phase': 'server_smoke', 'n_events': 0})
            self.assertEqual(chain.seq, 0, 'the refused write must not have landed')
        finally:
            chain._log.close()


class PathSafetyTests(_TmpDirCase):
    """Neither `prefreeze_root`, `prefreeze_events_dir` nor `open_prefreeze` will ever resolve
    into a trial chain, the program chain, or anywhere outside the pre-freeze tree -- by a bare
    path, a `..` traversal, or a symlink planted at the pre-freeze-root, subtree or `events`
    level."""

    def setUp(self) -> None:
        super().setUp()
        self.results_root = self.tmp / 'live_ab'
        self.results_root.mkdir(parents=True)

    def test_positive_the_canonical_prefreeze_directory_is_accepted(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        self.assertEqual(pf.prefreeze_root(proot), proot.resolve())

    def test_negative_a_trial_or_program_chain_directory_is_refused(self) -> None:
        for chain_id in ('T1', 'T2', 'T3', 'T4', lab_common.PROGRAM_CHAIN_ID):
            with self.subTest(chain_id=chain_id):
                d = self.results_root / chain_id
                d.mkdir(parents=True, exist_ok=True)
                with self.assertRaises(pf.PrefreezePathError):
                    pf.prefreeze_root(d)

    def test_negative_a_dotdot_traversal_to_a_trial_chain_is_refused(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        (self.results_root / 'T1').mkdir()
        traversal = proot / '..' / 'T1'
        with self.assertRaises(pf.PrefreezePathError):
            pf.prefreeze_root(traversal)

    def test_negative_a_root_level_symlink_into_a_trial_chain_is_refused(self) -> None:
        trial_dir = self.results_root / 'T1'
        trial_dir.mkdir()
        decoy = self.results_root / '_prefreeze'
        decoy.symlink_to(trial_dir)
        with self.assertRaises(pf.PrefreezePathError):
            pf.prefreeze_root(decoy)

    def test_negative_a_subtree_name_with_a_path_separator_or_dotdot_is_refused(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        for bad in ('../T1', 'sub/dir', '..', '.', 'a/../../T1', ''):
            with self.subTest(subtree=bad):
                with self.assertRaises(pf.PrefreezePathError):
                    pf.prefreeze_events_dir(proot, subtree=bad)

    def test_negative_the_subtree_regex_itself_rejects_a_path_separator_or_dotdot(self) -> None:
        # A unit test of `_SUBTREE_RE` directly, independent of `prefreeze_events_dir`'s own
        # resolved-parent check: the two are independent defenses (both currently refuse most
        # traversal strings via the resolved-parent check alone once the string contains a
        # `/`), so a test that only ever calls through `prefreeze_events_dir` cannot show the
        # regex itself is doing anything -- a mutant that widens `_SUBTREE_RE` to accept any
        # non-empty string would still be caught by the other test above and look "killed" for
        # the wrong reason. This test isolates the regex's own contribution.
        for bad in ('../T1', 'sub/dir', '..', '.', 'a/../../T1', ''):
            with self.subTest(subtree=bad):
                self.assertIsNone(pf._SUBTREE_RE.match(bad),
                                  f'{bad!r} must not match the subtree-name pattern')

    def test_negative_a_subtree_level_symlink_escape_is_refused(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        trial_dir = self.results_root / 'T1'
        trial_dir.mkdir()
        (proot / 'sneaky').symlink_to(trial_dir)
        with self.assertRaises(pf.PrefreezePathError):
            pf.prefreeze_events_dir(proot, subtree='sneaky')

    def test_negative_an_events_leaf_symlink_escape_is_refused(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        trial_events = self.results_root / 'T1' / 'events'
        trial_events.mkdir(parents=True)
        (proot / 'events').symlink_to(trial_events)
        with self.assertRaises(pf.PrefreezePathError):
            pf.prefreeze_events_dir(proot)

    def test_negative_open_prefreeze_refuses_the_same_subtree_traversal(self) -> None:
        proot = self.results_root / '_prefreeze'
        proot.mkdir()
        (self.results_root / 'T1').mkdir()
        with self.assertRaises(pf.PrefreezePathError):
            pf.open_prefreeze('smoke', inv=_inv(), root=proot, subtree='../T1', create=True)
        # and nothing was created outside the pre-freeze tree by the refused attempt
        self.assertEqual(list((self.results_root / 'T1').iterdir()), [])


class ChainLinksTests(_TmpDirCase):
    """A chain `PrefreezeChain` writes reads back and hash-verifies whole under
    `lab_eventlog.read_chain`; a tampered chain is refused."""

    def test_positive_the_written_chain_reads_back_and_verifies(self) -> None:
        chain = pf.open_prefreeze('smoke', inv=_inv(), root=self.root, create=True)
        for i in range(3):
            chain.append('server_health', _health_body(slots_busy=i, rss_bytes=1000 + i))
        closed_ev = chain.close()
        events_dir = pf.prefreeze_events_dir(self.root)
        read = lab_eventlog.read_chain(events_dir, lab_common.PREFREEZE_CHAIN_ID, 'prefreeze')
        self.assertIsNone(read.torn)
        self.assertEqual(len(read.events), 4)  # 3 server_health + 1 prefreeze_closed
        self.assertEqual(read.events[-1]['h'], closed_ev['h'])
        expected_genesis = lab_eventlog.genesis_prev('prefreeze', lab_common.PREFREEZE_CHAIN_ID)
        self.assertEqual(read.events[0]['prev'], expected_genesis)
        for a, b in zip(read.events, read.events[1:]):
            self.assertEqual(b['prev'], a['h'], 'the chain link must hold event to event')

    def test_positive_close_declares_the_true_pre_close_head_bytes_hash_and_count(self) -> None:
        # protocol_FINAL.md 5.8/12.1: `prefreeze_closed`'s `head`/`bytes`/`file_sha256` "enter
        # the freeze bundle" -- the most audit-critical write this module makes. This
        # independently recomputes every one of those four fields from the raw segment bytes
        # AS OF JUST BEFORE `close()` runs (the same moment `close()` itself measures), rather
        # than trusting `close()`'s own arithmetic, so a wrong `n_events`/`bytes`/`file_sha256`/
        # `head` in the emitted event is caught even though it is schema-legal and the chain
        # link still verifies (the closing event's own `h`/`prev` are correct either way; only
        # the AUDIT FIELDS INSIDE its body could lie).
        chain = pf.open_prefreeze('smoke', inv=_inv(), root=self.root, create=True)
        for i in range(3):
            chain.append('server_health', _health_body(slots_busy=i, rss_bytes=1000 + i))
        expected_head = chain.head
        expected_n_events = chain.seq
        pre_close_blob = b''.join(
            p.read_bytes() for p in lab_eventlog.segment_paths(chain.events_dir))
        expected_bytes = len(pre_close_blob)
        expected_sha256 = lab_common.sha256_bytes(pre_close_blob)

        closed_ev = chain.close()
        body = closed_ev['body']
        self.assertEqual(body['head'], expected_head,
                         "close()'s declared 'head' does not match the chain's true pre-close "
                         'head')
        self.assertEqual(body['n_events'], expected_n_events,
                         "close()'s declared 'n_events' does not match the true pre-close count")
        self.assertEqual(body['bytes'], expected_bytes,
                         "close()'s declared 'bytes' does not match the true pre-close segment "
                         'byte length')
        self.assertEqual(body['file_sha256'], expected_sha256,
                         "close()'s declared 'file_sha256' does not match the true pre-close "
                         'segment hash')

    def test_negative_a_tampered_event_body_breaks_verification(self) -> None:
        chain = pf.open_prefreeze('smoke', inv=_inv(), root=self.root, create=True)
        chain.append('server_health', _health_body(slots_busy=0))
        chain.close()
        events_dir = pf.prefreeze_events_dir(self.root)
        seg = sorted(events_dir.glob('seg_*.jsonl'))[0]
        lines = seg.read_text('utf-8').splitlines()
        ev = json.loads(lines[0])
        ev['body']['slots_busy'] = 999  # tamper without recomputing 'h'
        lines[0] = json.dumps(ev)
        seg.write_text('\n'.join(lines) + '\n')
        with self.assertRaises(lab_common.ChainError):
            lab_eventlog.read_chain(events_dir, lab_common.PREFREEZE_CHAIN_ID, 'prefreeze')


class ShardReceiptTests(_TmpDirCase):
    """`record_shard` writes a legal completed-shard receipt; `resume_shard` is the only legal
    resume check, never duplicates or rewrites on a repeated (crash-then-restart) call, and
    refuses a resume whose current pins differ from what the receipt recorded."""

    def setUp(self) -> None:
        super().setUp()
        self.receipts_dir = self.tmp / 'shards' / 'stage3'
        self.out_dir = self.tmp / 'out'
        self.out_dir.mkdir(parents=True)
        self.row = {'episode': 1, 'task': 'mbpp/1'}

    def _write_output(self, name: str = 'result.json', content: bytes = b'{}'):
        (self.out_dir / name).write_bytes(content)
        return name, lab_common.sha256_bytes(content)

    def _record(self, *, pins, name, digest, outcome='success'):
        return pf.record_shard(self.receipts_dir, 'stage3', self.row, pins=pins, inputs={},
                               outputs={name: digest}, start_utc='2026-09-26T00:00:00Z',
                               end_utc='2026-09-26T00:00:01Z', outcome=outcome)

    def test_positive_record_shard_writes_a_receipt(self) -> None:
        name, digest = self._write_output()
        sha = self._record(pins=_pins(), name=name, digest=digest)
        sid = sr.shard_id('stage3', self.row)
        path = self.receipts_dir / f'{sid}.json'
        self.assertTrue(path.is_file(), 'record_shard must write the receipt file')
        self.assertEqual(lab_common.sha256_bytes(path.read_bytes()), sha)
        on_disk = json.loads(path.read_text('utf-8'))
        self.assertEqual(on_disk['shard_id'], sid)
        self.assertEqual(on_disk['driver'], 'stage3')
        self.assertEqual(on_disk['outputs'], {name: digest})

    def test_negative_resume_before_any_receipt_is_none(self) -> None:
        got = pf.resume_shard(self.receipts_dir, 'stage3', self.row, expected_pins=_pins(),
                              expected_output_paths=['result.json'],
                              root_for_outputs=self.out_dir)
        self.assertIsNone(got)

    def test_positive_a_crash_resume_neither_duplicates_nor_rewrites(self) -> None:
        name, digest = self._write_output()
        self._record(pins=_pins(), name=name, digest=digest)
        sid = sr.shard_id('stage3', self.row)
        path = self.receipts_dir / f'{sid}.json'
        before = path.read_bytes()
        before_mtime = path.stat().st_mtime_ns

        # simulate a crash-then-restart: the driver calls resume_shard with the SAME current
        # pins/outputs a fresh process would recompute, exactly as design_notes/
        # DESIGN_PROPOSAL.md section 5's "None when not yet present, otherwise verify_resume
        # itself validated against the caller's CURRENT pins" describes.
        got = pf.resume_shard(self.receipts_dir, 'stage3', self.row, expected_pins=_pins(),
                              expected_output_paths=[name], root_for_outputs=self.out_dir)
        self.assertIsNotNone(got)
        self.assertEqual(path.read_bytes(), before, 'resume must never rewrite the receipt')
        self.assertEqual(path.stat().st_mtime_ns, before_mtime,
                         'resume must never touch the file at all')
        self.assertEqual(sr.completed_shards(self.receipts_dir), frozenset({sid}))

        # a second "crash" that re-runs record_shard for the identical inputs (the write-once
        # no-op lab_shard_receipt itself guarantees) must not create a second receipt either
        self._record(pins=_pins(), name=name, digest=digest)
        self.assertEqual(sr.completed_shards(self.receipts_dir), frozenset({sid}))
        self.assertEqual(len(list(self.receipts_dir.glob('*.json'))), 1,
                         'a repeated finish of the same shard must not duplicate its receipt')

    def test_negative_a_changed_pin_resume_is_refused(self) -> None:
        name, digest = self._write_output()
        self._record(pins=_pins(seed=1), name=name, digest=digest)
        with self.assertRaises(sr.ResumeMismatch):
            pf.resume_shard(self.receipts_dir, 'stage3', self.row, expected_pins=_pins(seed=2),
                            expected_output_paths=[name], root_for_outputs=self.out_dir)
        # never repairs, rewrites or reruns anything on a mismatch
        sid = sr.shard_id('stage3', self.row)
        path = self.receipts_dir / f'{sid}.json'
        self.assertEqual(json.loads(path.read_text('utf-8'))['pins']['seed'], {'value': 1})


class MutationControlTests(_TmpDirCase):
    """Proves :class:`PhaseGateTests` can fail: with the `VALID_PHASES` gate patched out, the
    same undefined-phase scenario no longer raises."""

    @staticmethod
    def _mutant_accepts_any_phase(phase, *, inv, root=None, subtree=None, create=False):
        """MUTATION ONLY -- never called in production.  Same call shape as `open_prefreeze`
        but skips the `VALID_PHASES` check entirely, so an undefined phase like `timing_pilot`
        opens a chain instead of being refused."""
        events_dir = pf.prefreeze_events_dir(root, subtree=subtree)
        log = lab_eventlog.EventLog(events_dir, lab_common.PREFREEZE_CHAIN_ID, 'prefreeze', inv,
                                    create=create)
        return pf.PrefreezeChain(log, phase)

    def test_the_undefined_phase_control_fails_under_a_phase_gate_removed_mutant(self) -> None:
        with mock.patch.object(pf, 'open_prefreeze', self._mutant_accepts_any_phase):
            # the real control (PhaseGateTests.test_negative_an_undefined_phase_is_refused)
            # expects UndefinedPhaseError here; under the mutant it does not raise, so asserting
            # that it does raise itself fails -- this is the proof the control is not vacuous.
            # Called exactly ONCE (its handle is captured on the way in): a second open_prefreeze
            # on the same, now-populated events_dir with create=True would itself raise
            # ChainError ("segment(s) already exist"), which is a fixture bug, not a repeat of
            # the phase-gate proof.
            holder: list = []
            with self.assertRaises(AssertionError):
                with self.assertRaises(pf.UndefinedPhaseError):
                    holder.append(pf.open_prefreeze('timing_pilot', inv=_inv(), root=self.root,
                                                    create=True))
            chain = holder[0]
            try:
                self.assertEqual(chain.phase, 'timing_pilot',
                                 'the mutant silently accepted an undefined phase')
            finally:
                chain._log.close()


if __name__ == '__main__':
    unittest.main()
