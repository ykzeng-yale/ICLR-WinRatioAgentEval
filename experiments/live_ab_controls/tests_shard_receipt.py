"""Controls for ``lab_shard_receipt`` (design_notes/DESIGN_PROPOSAL.md section 3 item 1;
root 22:20, `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19`: "exact
code/config/seed pins and incremental immutable completed-shard receipts").

Every positive check here has a NEGATIVE CONTROL beside it -- the same call on an input it
must refuse, asserted refused -- so none of these can pass by being unable to fail.  What runs:
``lab_shard_receipt`` in process against a plain temp directory; no server, no model, no
subprocess.  :class:`MutationControlTests` goes one step further and proves the write-once
control ITSELF can fail: it monkeypatches ``write_shard_receipt`` to a write-once-removed
mutant and shows the same scenario that :class:`WriteOnceTests` checks no longer refuses.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

import lab_common                                                       # noqa: E402
import lab_shard_receipt as sr                                          # noqa: E402


def _row(**extra) -> dict:
    base = {'episode': 1, 'task': 'mbpp/1'}
    base.update(extra)
    return base


def _receipt(driver: str = 'stage4', row: dict | None = None, *, outcome: str = 'success',
            start: str = '2026-09-25T22:00:00Z', end: str = '2026-09-25T22:00:01Z',
            outputs: dict | None = None) -> dict:
    """A minimal, valid receipt -- every field-removal test below deletes exactly one key from
    a copy of this."""
    row = row if row is not None else _row()
    return {
        'schema': sr.SCHEMA,
        'shard_id': sr.shard_id(driver, row),
        'driver': driver,
        'schedule_row': row,
        'pins': {
            'code': {'lab_shard_receipt.py': 'a' * 64},
            'config': {'sha256': 'b' * 64, 'keys_used': ['design_seed_base']},
            'seed': {'formula': 'SeedSequence([design_seed_base, 1105, 0, 0])'},
            'data': {},
        },
        'inputs': {},
        'outputs': outputs if outputs is not None else {},
        'start_utc': start,
        'end_utc': end,
        'outcome': outcome,
        'harness_pin_delta': [],
    }


class _TmpDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='shard_receipt_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class WriteOnceTests(_TmpDirCase):
    def test_identical_rewrite_is_a_noop(self) -> None:
        receipt = _receipt()
        d1 = sr.write_shard_receipt(self.tmp, receipt)
        d2 = sr.write_shard_receipt(self.tmp, dict(receipt))
        self.assertEqual(d1, d2)

    def test_negative_a_rewrite_with_different_bytes_is_refused(self) -> None:
        row = _row()
        sr.write_shard_receipt(self.tmp, _receipt(row=row, outcome='success'))
        with self.assertRaises(lab_common.WriteOnceViolation):
            sr.write_shard_receipt(self.tmp, _receipt(row=row, outcome='failure'))


class RequiredFieldTests(_TmpDirCase):
    """Each top-level field's absence is refused; the fixture with nothing removed is the
    positive control every deletion is a copy of."""

    def test_positive_the_fixture_itself_validates(self) -> None:
        sr.validate_receipt(_receipt())

    def test_negative_each_missing_top_level_field_is_refused(self) -> None:
        for field in sr.REQUIRED_FIELDS:
            with self.subTest(field=field):
                receipt = _receipt()
                del receipt[field]
                with self.assertRaises(sr.ShardReceiptError):
                    sr.validate_receipt(receipt)

    def test_negative_each_missing_pin_key_is_refused(self) -> None:
        for key in sr.REQUIRED_PIN_KEYS:
            with self.subTest(pin=key):
                receipt = _receipt()
                del receipt['pins'][key]
                with self.assertRaises(sr.ShardReceiptError):
                    sr.validate_receipt(receipt)

    def test_negative_a_non_hex64_code_digest_is_refused(self) -> None:
        receipt = _receipt()
        receipt['pins']['code']['x.py'] = 'not-a-digest'
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_a_config_pin_without_sha256_is_refused(self) -> None:
        receipt = _receipt()
        del receipt['pins']['config']['sha256']
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_a_null_seed_pin_is_refused(self) -> None:
        receipt = _receipt()
        receipt['pins']['seed'] = None
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_an_outputs_entry_without_a_valid_digest_is_refused(self) -> None:
        receipt = _receipt(outputs={'out.txt': 'short'})
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_a_shard_id_not_matching_its_own_driver_and_row_is_refused(self) -> None:
        receipt = _receipt()
        receipt['shard_id'] = sr.shard_id('other_driver', _row())
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)


class OutcomeTests(_TmpDirCase):
    def test_positive_each_legal_outcome_validates(self) -> None:
        for outcome in sr.OUTCOMES:
            with self.subTest(outcome=outcome):
                sr.validate_receipt(_receipt(row=_row(outcome_tag=outcome), outcome=outcome))

    def test_negative_an_outcome_outside_the_three_legal_values_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(outcome='partial'))

    def test_negative_an_absent_outcome_is_refused(self) -> None:
        receipt = _receipt()
        del receipt['outcome']
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)


class TimestampTests(_TmpDirCase):
    def test_positive_end_after_start_validates(self) -> None:
        sr.validate_receipt(_receipt(start='2026-09-25T22:00:00Z', end='2026-09-25T22:00:01Z'))

    def test_positive_end_equal_to_start_validates(self) -> None:
        sr.validate_receipt(_receipt(start='2026-09-25T22:00:00Z', end='2026-09-25T22:00:00Z'))

    def test_negative_a_non_iso_start_utc_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(start='not-a-timestamp'))

    def test_negative_a_start_utc_missing_the_z_suffix_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(start='2026-09-25T22:00:00'))

    def test_negative_a_calendar_invalid_timestamp_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(end='2026-13-01T00:00:00Z'))

    def test_negative_end_before_start_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(start='2026-09-25T22:00:05Z',
                                         end='2026-09-25T22:00:00Z'))


class ResumeTests(_TmpDirCase):
    def test_completed_shards_lists_what_is_on_disk_and_nothing_else(self) -> None:
        self.assertEqual(sr.completed_shards(self.tmp), frozenset())
        r1, r2 = _receipt(row=_row(n=1)), _receipt(row=_row(n=2))
        sr.write_shard_receipt(self.tmp, r1)
        self.assertEqual(sr.completed_shards(self.tmp), frozenset({r1['shard_id']}))
        sr.write_shard_receipt(self.tmp, r2)
        self.assertEqual(sr.completed_shards(self.tmp),
                         frozenset({r1['shard_id'], r2['shard_id']}))

    def test_a_missing_directory_is_zero_shards_done_not_an_error(self) -> None:
        self.assertEqual(sr.completed_shards(self.tmp / 'never_created'), frozenset())

    def test_resume_skips_a_completed_row_and_leaves_its_receipt_bytes_unchanged(self) -> None:
        row = _row(n=3)
        receipt = _receipt(row=row)
        sr.write_shard_receipt(self.tmp, receipt)
        path = self.tmp / f"{receipt['shard_id']}.json"
        before = lab_common.sha256_file(path)

        done = sr.completed_shards(self.tmp)
        schedule = [('stage4', row), ('stage4', _row(n=4))]
        # a resume loop attempts only the rows with no receipt yet
        remaining = [(driver, r) for driver, r in schedule
                    if sr.shard_id(driver, r) not in done]
        self.assertEqual(remaining, [('stage4', _row(n=4))])
        for driver, r in remaining:
            sr.write_shard_receipt(self.tmp, _receipt(driver=driver, row=r))

        after = lab_common.sha256_file(path)
        self.assertEqual(before, after,
                         'the completed row\'s receipt bytes must be untouched by resume')
        self.assertEqual(len(sr.completed_shards(self.tmp)), 2)


class CrashMidWriteTests(_TmpDirCase):
    def test_a_simulated_crash_mid_write_leaves_no_partial_receipt_file(self) -> None:
        receipt = _receipt()
        path = self.tmp / f"{receipt['shard_id']}.json"

        def boom(fd, data):
            raise OSError('device full')

        with mock.patch.object(os, 'write', boom):
            with self.assertRaises(OSError):
                sr.write_shard_receipt(self.tmp, receipt)
        self.assertFalse(path.exists(), 'a crash mid-write must never leave a receipt file')
        # and a real, un-crashed write afterwards still succeeds and validates
        sr.write_shard_receipt(self.tmp, receipt)
        self.assertTrue(path.exists())

    def test_negative_without_the_simulated_crash_the_same_write_succeeds(self) -> None:
        receipt = _receipt()
        path = self.tmp / f"{receipt['shard_id']}.json"
        sr.write_shard_receipt(self.tmp, receipt)
        self.assertTrue(path.exists())


class VerifyShardsTests(_TmpDirCase):
    def _write(self, driver: str, row: dict, *, output_bytes: bytes | None = None) -> dict:
        outputs = {}
        if output_bytes is not None:
            out_path = self.tmp / 'out' / f"{sr.shard_id(driver, row)}.bin"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(output_bytes)
            outputs = {f"out/{out_path.name}": lab_common.sha256_bytes(output_bytes)}
        receipt = _receipt(driver=driver, row=row, outputs=outputs)
        sr.write_shard_receipt(self.tmp / 'receipts', receipt)
        return receipt

    def test_positive_a_correct_set_gives_no_findings(self) -> None:
        rows = [_row(n=i) for i in range(3)]
        for row in rows:
            self._write('stage4', row, output_bytes=b'ok-' + str(row['n']).encode())
        schedule = [('stage4', row) for row in rows]
        findings = sr.verify_shards(self.tmp / 'receipts', schedule, self.tmp)
        self.assertEqual(findings, [])

    def test_negative_a_recomputed_output_hash_mismatch_is_flagged(self) -> None:
        row = _row(n=10)
        self._write('stage4', row, output_bytes=b'original')
        # corrupt the output AFTER the receipt was written -- the receipt still names the
        # original bytes' digest
        out_path = self.tmp / 'out' / f"{sr.shard_id('stage4', row)}.bin"
        out_path.write_bytes(b'tampered')
        findings = sr.verify_shards(self.tmp / 'receipts', [('stage4', row)], self.tmp)
        kinds = [f['kind'] for f in findings]
        self.assertIn('output_hash_mismatch', kinds)

    def test_negative_a_schedule_row_with_no_receipt_is_flagged(self) -> None:
        written = _row(n=20)
        unwritten = _row(n=21)
        self._write('stage4', written)
        findings = sr.verify_shards(self.tmp / 'receipts',
                                    [('stage4', written), ('stage4', unwritten)], self.tmp)
        kinds = {f['kind'] for f in findings}
        self.assertIn('missing_receipt', kinds)
        missing = [f for f in findings if f['kind'] == 'missing_receipt']
        self.assertEqual(missing[0]['shard_id'], sr.shard_id('stage4', unwritten))

    def test_negative_a_receipt_with_no_schedule_row_is_flagged(self) -> None:
        row = _row(n=30)
        self._write('stage4', row)
        findings = sr.verify_shards(self.tmp / 'receipts', [], self.tmp)
        kinds = [f['kind'] for f in findings]
        self.assertIn('orphan_receipt', kinds)

    def test_negative_two_receipts_for_one_row_are_flagged(self) -> None:
        row = _row(n=40)
        receipt = self._write('stage4', row)
        # a second file, different name, SAME declared shard_id -- exactly the bijection
        # violation the design calls for detecting; never produced by write_shard_receipt
        # itself (its path is always <shard_id>.json), only by external corruption
        dup = (self.tmp / 'receipts' / 'dup_copy.json')
        dup.write_text(lab_common.canonical_json(receipt))
        findings = sr.verify_shards(self.tmp / 'receipts', [('stage4', row)], self.tmp)
        kinds = [f['kind'] for f in findings]
        self.assertIn('duplicate_receipt', kinds)

    def test_negative_a_malformed_receipt_is_flagged(self) -> None:
        (self.tmp / 'receipts').mkdir(parents=True, exist_ok=True)
        (self.tmp / 'receipts' / 'broken.json').write_text('{not json')
        findings = sr.verify_shards(self.tmp / 'receipts', [], self.tmp)
        kinds = [f['kind'] for f in findings]
        self.assertIn('malformed_receipt', kinds)

    def test_negative_a_receipt_failing_validate_receipt_is_malformed_not_silently_accepted(
            self) -> None:
        (self.tmp / 'receipts').mkdir(parents=True, exist_ok=True)
        bad = _receipt()
        del bad['outcome']
        (self.tmp / 'receipts' / 'z.json').write_text(json.dumps(bad))
        findings = sr.verify_shards(self.tmp / 'receipts', [], self.tmp)
        kinds = [f['kind'] for f in findings]
        self.assertIn('malformed_receipt', kinds)


class PathTraversalTests(_TmpDirCase):
    """Adversarial-review Finding 1: an unrestricted ``driver`` string could steer a receipt's
    path outside its own receipt directory.  Reproduced live against the pre-fix module (a
    ``driver`` of ``'../pwn'`` landed a file one level above the given directory); fixed by
    ``_SAFE_DRIVER_RE`` in :func:`sr.shard_id` plus a resolved-path containment assertion in
    :func:`sr.write_shard_receipt` itself."""

    def test_positive_an_ordinary_driver_name_is_accepted(self) -> None:
        for driver in ('stage1', 'stage11_5', 'stage4-calib'):
            with self.subTest(driver=driver):
                self.assertTrue(sr.shard_id(driver, _row()))

    def test_negative_a_driver_with_a_path_separator_is_refused(self) -> None:
        for driver in ('../pwn', 'a/b', 'a\\b', '..', 'stage1/../../etc'):
            with self.subTest(driver=driver):
                with self.assertRaises(sr.ShardReceiptError):
                    sr.shard_id(driver, _row())

    def test_negative_write_shard_receipt_refuses_a_hand_built_traversal_driver_receipt(
            self) -> None:
        # built by hand rather than through _receipt() (which itself calls sr.shard_id() and
        # would raise before a receipt naming a traversal driver could even be constructed) --
        # this exercises write_shard_receipt -> validate_receipt -> shard_id()'s own refusal.
        row = _row()
        receipt = {
            'schema': sr.SCHEMA, 'shard_id': 'placeholder', 'driver': '../pwn',
            'schedule_row': row, 'pins': _receipt()['pins'], 'inputs': {}, 'outputs': {},
            'start_utc': '2026-09-25T22:00:00Z', 'end_utc': '2026-09-25T22:00:01Z',
            'outcome': 'success', 'harness_pin_delta': [],
        }
        with self.assertRaises(sr.ShardReceiptError):
            sr.write_shard_receipt(self.tmp, receipt)
        self.assertEqual(list(self.tmp.parent.glob('pwn__*.json')), [],
                         'no file may appear outside the given receipt directory')

    def test_write_shard_receipt_itself_refuses_a_shard_id_that_would_leave_the_directory(
            self) -> None:
        # the second, defense-in-depth layer: a receipt built by hand (not through shard_id())
        # that carries an already-escaping shard_id is still refused by write_shard_receipt's
        # own containment assertion, even though validate_receipt's shard_id()-bijection check
        # would already have caught this -- monkeypatch that check away to isolate this layer.
        receipt = _receipt()
        receipt['shard_id'] = '../escaped__' + receipt['shard_id'].split('__', 1)[1]
        with mock.patch.object(sr, 'validate_receipt', lambda r: None):
            with self.assertRaises(sr.ShardReceiptError):
                sr.write_shard_receipt(self.tmp, receipt)
        self.assertEqual(list(self.tmp.parent.glob('escaped__*.json')), [])


class ConcurrentRaceTests(_TmpDirCase):
    """Adversarial-review Finding 2: ``lab_common.write_json_atomic`` derives its temp file
    name from the destination path alone (``lab_common.py:520``), so two writers racing on the
    SAME shard id share one temp file; the loser's own ``os.replace`` can raise
    ``FileNotFoundError`` instead of ``write_json_atomic``'s own ``WriteOnceViolation``.
    Reproduced live with 12 real concurrent processes (11/12 losers crashed with
    ``FileNotFoundError`` before the fix; 0/12 crashed after).  These two tests pin the fix
    deterministically via a single mocked call, without depending on real OS race timing."""

    def test_a_racing_replace_that_raises_filenotfounderror_resolves_to_write_once_not_a_crash(
            self) -> None:
        row = _row()
        winner = _receipt(row=row, outcome='success')
        loser = _receipt(row=row, outcome='failure')
        sr.write_shard_receipt(self.tmp, winner)  # the "winner" already landed its receipt

        real_write_json_atomic = lab_common.write_json_atomic
        calls = {'n': 0}

        def flaky_once(path, obj, *, durable=True):
            calls['n'] += 1
            if calls['n'] == 1:
                raise FileNotFoundError(2, 'No such file or directory')
            return real_write_json_atomic(path, obj, durable=durable)

        with mock.patch.object(lab_common, 'write_json_atomic', flaky_once):
            with self.assertRaises(lab_common.WriteOnceViolation):
                sr.write_shard_receipt(self.tmp, loser)
        self.assertEqual(calls['n'], 2, 'the race must be retried exactly once against the '
                                       'winner\'s now-existing file')

    def test_negative_a_persistent_filenotfounderror_with_no_winner_file_still_propagates(
            self) -> None:
        # not every FileNotFoundError is this race -- when the destination never appears, the
        # retry must not swallow a real error into a wrong outcome.
        receipt = _receipt()

        def always_boom(path, obj, *, durable=True):
            raise FileNotFoundError(2, 'No such file or directory')

        with mock.patch.object(lab_common, 'write_json_atomic', always_boom):
            with self.assertRaises(FileNotFoundError):
                sr.write_shard_receipt(self.tmp, receipt)


class OutputsAndPinsPathTraversalTests(_TmpDirCase):
    """Adversarial-review Finding 3: ``outputs``/``pins.code``/``pins.data`` keys were only
    checked for being non-empty strings, so a ``..``-carrying or absolute key was accepted by
    :func:`sr.validate_receipt` and would let :func:`sr.verify_shards` read (or a driver's
    bookkeeping name) a file entirely outside the declared output/data root.  Reproduced live
    against the pre-fix module: ``verify_shards`` returned ``[]`` (no finding) for a receipt
    whose only output was ``'../secret.txt'``."""

    def test_positive_an_ordinary_relative_key_is_accepted(self) -> None:
        sr.validate_receipt(_receipt(outputs={'out/result.bin': 'd' * 64}))

    def test_negative_a_dotdot_outputs_key_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(outputs={'../secret.txt': 'c' * 64}))

    def test_negative_an_absolute_outputs_key_is_refused(self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(_receipt(outputs={'/etc/passwd': 'c' * 64}))

    def test_negative_a_dotdot_pins_code_key_is_refused(self) -> None:
        receipt = _receipt()
        receipt['pins']['code']['../../etc/passwd'] = 'a' * 64
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_a_dotdot_pins_data_key_is_refused(self) -> None:
        receipt = _receipt()
        receipt['pins']['data']['../outside/cache.bin'] = 'a' * 64
        with self.assertRaises(sr.ShardReceiptError):
            sr.validate_receipt(receipt)

    def test_negative_a_traversal_outputs_receipt_is_refused_by_write_shard_receipt_too(
            self) -> None:
        with self.assertRaises(sr.ShardReceiptError):
            sr.write_shard_receipt(self.tmp, _receipt(outputs={'../secret.txt': 'c' * 64}))


class MisnamedReceiptTests(_TmpDirCase):
    """Adversarial-review Finding 4: :func:`sr.verify_shards` grouped receipts by their
    CONTENT ``shard_id`` and never checked the file name, so a lone file named
    ``not_the_shard_id.json`` holding an otherwise-valid receipt produced no finding at all.
    Reproduced live against the pre-fix module: ``verify_shards`` returned ``[]`` for exactly
    this file."""

    def test_negative_a_receipt_file_not_named_after_its_own_shard_id_is_flagged(self) -> None:
        row = _row()
        receipt = _receipt(row=row)
        (self.tmp / 'receipts').mkdir(parents=True, exist_ok=True)
        (self.tmp / 'receipts' / 'not_the_shard_id.json').write_text(
            lab_common.canonical_json(receipt))
        findings = sr.verify_shards(self.tmp / 'receipts', [('stage4', row)], self.tmp)
        kinds = {f['kind'] for f in findings}
        self.assertIn('misnamed_receipt', kinds)

    def test_negative_a_misnamed_duplicate_is_flagged_as_both_not_instead_of_either(
            self) -> None:
        # a misnamed file that ALSO collides with a correctly-named one on content shard_id
        # must not have the duplicate finding silently swallowed by the misnamed one (regression
        # guard: an earlier draft of the Finding 4 fix `continue`d past misnamed files, which
        # hid VerifyShardsTests.test_negative_two_receipts_for_one_row_are_flagged's own
        # duplicate_receipt entirely).
        row = _row()
        receipt = _receipt(row=row)
        sr.write_shard_receipt(self.tmp / 'receipts', receipt)
        (self.tmp / 'receipts' / 'dup_copy.json').write_text(
            lab_common.canonical_json(receipt))
        findings = sr.verify_shards(self.tmp / 'receipts', [('stage4', row)], self.tmp)
        kinds = {f['kind'] for f in findings}
        self.assertIn('duplicate_receipt', kinds)
        self.assertIn('misnamed_receipt', kinds)

    def test_positive_a_correctly_named_receipt_is_not_flagged_misnamed(self) -> None:
        row = _row()
        self._write_correctly(row)
        findings = sr.verify_shards(self.tmp / 'receipts', [('stage4', row)], self.tmp)
        kinds = {f['kind'] for f in findings}
        self.assertNotIn('misnamed_receipt', kinds)

    def _write_correctly(self, row: dict) -> None:
        sr.write_shard_receipt(self.tmp / 'receipts', _receipt(row=row))


class HarnessPinDeltaTests(_TmpDirCase):
    """Adversarial-review Finding 7: ``harness_pin_delta`` was only checked to be a list, so
    ``[None, 42, {}, 3.14]`` validated cleanly and would silently weaken the harness-byte-impact
    audit trail root asked for (design_notes/DESIGN_PROPOSAL.md section 5)."""

    def test_positive_an_empty_list_and_a_list_of_paths_both_validate(self) -> None:
        sr.validate_receipt(_receipt())
        row = _row(n='hpd')
        receipt = _receipt(row=row)
        receipt['harness_pin_delta'] = ['experiments/live_ab/tests_lab_isolation.py']
        sr.validate_receipt(receipt)

    def test_negative_non_string_or_empty_entries_are_refused(self) -> None:
        for bad in ([None], [42], [{}], [3.14], ['']):
            with self.subTest(bad=bad):
                receipt = _receipt()
                receipt['harness_pin_delta'] = bad
                with self.assertRaises(sr.ShardReceiptError):
                    sr.validate_receipt(receipt)


class WritePathValidatesTests(_TmpDirCase):
    """Adversarial-review Finding 5: every ``write_shard_receipt(`` call site in this file
    previously passed only fixture-valid receipts, so a mutation that deleted the
    ``validate_receipt(receipt)`` line inside :func:`sr.write_shard_receipt` (the only path a
    real driver uses) shipped with a fully green suite.  These calls exercise
    ``write_shard_receipt`` directly -- not ``validate_receipt`` -- with structurally invalid
    input, closing that gap."""

    def test_negative_write_shard_receipt_refuses_a_receipt_missing_a_required_field(
            self) -> None:
        receipt = _receipt()
        del receipt['outcome']
        with self.assertRaises(sr.ShardReceiptError):
            sr.write_shard_receipt(self.tmp, receipt)
        self.assertEqual(list(self.tmp.glob('*.json')), [],
                         'an invalid receipt must never reach the filesystem')

    def test_negative_write_shard_receipt_refuses_a_receipt_with_a_bad_outcome(self) -> None:
        receipt = _receipt(outcome='partial')
        with self.assertRaises(sr.ShardReceiptError):
            sr.write_shard_receipt(self.tmp, receipt)
        self.assertEqual(list(self.tmp.glob('*.json')), [])


class MutationControlTests(_TmpDirCase):
    """Proves :class:`WriteOnceTests` can fail: with write-once removed, the same negative
    scenario no longer raises."""

    @staticmethod
    def _mutant_overwrite_no_write_once(dir, receipt) -> str:
        """MUTATION ONLY -- never called in production.  Same call shape as
        ``write_shard_receipt`` but skips ``lab_common.write_json_atomic`` entirely, so an
        existing receipt is silently replaced instead of refused."""
        d = Path(dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{receipt['shard_id']}.json"
        data = lab_common.canonical_json(dict(receipt))
        path.write_text(data)
        return lab_common.sha256_text(data)

    def test_the_write_once_control_fails_under_a_write_once_removed_mutant(self) -> None:
        row = _row()
        first = _receipt(row=row, outcome='success')
        second = _receipt(row=row, outcome='failure')
        with mock.patch.object(sr, 'write_shard_receipt',
                               self._mutant_overwrite_no_write_once):
            sr.write_shard_receipt(self.tmp, first)
            # the real control (WriteOnceTests.test_negative_a_rewrite_with_different_bytes_
            # is_refused) expects WriteOnceViolation here; under the mutant it does not raise,
            # so asserting that it does raise itself fails -- this is the proof.
            with self.assertRaises(AssertionError):
                with self.assertRaises(lab_common.WriteOnceViolation):
                    sr.write_shard_receipt(self.tmp, second)
            path = self.tmp / f"{first['shard_id']}.json"
            self.assertEqual(json.loads(path.read_text())['outcome'], 'failure',
                             'the mutant silently overwrote the receipt with different bytes')


if __name__ == '__main__':
    unittest.main()
