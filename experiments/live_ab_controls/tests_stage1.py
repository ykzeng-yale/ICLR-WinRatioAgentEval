"""Controls for ``lab_stage1`` (design_notes/DESIGN_PROPOSAL.md section 3 item 4; authorized
against ``lab_mock_server`` only by root's 2026-09-26 07:18 bounded review,
`reviews/drivers_successor_pin_bounded_review_20260926_0718.md`, item 1).

Every positive check here has a NEGATIVE CONTROL beside it -- the same call on an input it must
refuse, or on a scenario it must disagree with -- so none of these can pass vacuously.  What
runs: ``lab_mock_server`` on a free loopback port, served in a thread for one test's duration
(the same pattern ``experiments/live_ab/tests_lab_serving.py`` already uses); no real model, no
real ``llama-server``, no ``llama.cpp`` build, no network beyond that loopback and ``git show``
(read-only).  :class:`MutationControlTests` goes one step further and proves the conformance
counter's own boundary control can fail: it loads a deliberately broken copy of the verdict
logic from a scratch file under the session's ``tmp_agents`` directory (never the worktree) and
shows it disagrees with the real module on the exact 9-of-10 boundary
:class:`ConformanceCounterTests` checks.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import ast
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

import lab_common                                                        # noqa: E402
import lab_mock_server                                                   # noqa: E402
import lab_orchestrator                                                  # noqa: E402
import lab_prefreeze                                                     # noqa: E402
import lab_shard_receipt as sr                                           # noqa: E402
import lab_stage1                                                        # noqa: E402

REPO_ROOT = LIVE.parent.parent
#: Where MutationControlTests writes its scratch mutant file: an environment-provided scratch
#: directory (the harness that runs this file sets it to its own designated temp-file area) or,
#: absent that, a fresh directory under the platform temp root -- never a path inside this
#: worktree, since the mutant is not part of the harness this driver ships.
TMP_AGENTS = Path(os.environ.get('LAB_STAGE1_MUTATION_SCRATCH_DIR')
                 or tempfile.mkdtemp(prefix='lab_stage1_mutation_'))

SAMPLING = {'temperature': 0.7, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0, 'typical_p': 1.0,
           'repeat_penalty': 1.0, 'presence_penalty': 0.0, 'frequency_penalty': 0.0,
           'mirostat': 0, 'max_tokens': 64}


def _scenario(model_path: str, *, model_alias: str = 'mock-alias', **overrides) -> dict:
    """A minimal, fully scripted mock scenario: fixed props, deterministic responses, no
    randomness the test does not control (``outcome_seed`` is fixed and every prompt used here
    classifies as ``kind='code'`` or ``kind='smoke'``, never ``tests``/``repair``)."""
    base = {
        'alias': model_alias,
        'total_slots': 2,
        'props': {
            'model_alias': model_alias, 'model_path': str(model_path),
            'total_slots': 2, 'n_ctx': 8192,
            'default_generation_settings': {'n_ctx': 8192},
        },
        'defaults': {'temperature': 0.7, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0,
                    'typical_p': 1.0, 'repeat_penalty': 1.0, 'presence_penalty': 0.0,
                    'frequency_penalty': 0.0, 'mirostat': 0},
        'tokens': {'prompt_per_char': 0.25, 'completion_code': 16, 'completion_smoke': 4},
        'outcome_seed': 20260926,
        'tasks': [],
        'outcomes': {},
        'faults': [],
    }
    base.update(overrides)
    return base


@contextlib.contextmanager
def mock_server(scenario: dict):
    """A scripted mock on a free loopback port, served in a thread for the test's duration
    (the same pattern ``experiments/live_ab/tests_lab_serving.py:mock_server`` already uses;
    replicated here rather than imported so this controls file does not pull that module's own
    heavy pilot-reuse machinery -- ``agent``/``sandbox``/``verify`` monkeypatch fixtures -- in
    just to borrow ten lines)."""
    srv, port = lab_mock_server.make_server(scenario, port=0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.01},
                              daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d' % port
    finally:
        with contextlib.suppress(Exception):
            srv.shutdown()
        with contextlib.suppress(Exception):
            srv.server_close()
        thread.join(timeout=5)


def _inv() -> str:
    return uuid.uuid4().hex


def _pins(*, config_sha: str = 'b' * 64, seed: int = 1) -> dict:
    return {
        'code': {'lab_stage1.py': 'a' * 64},
        'config': {'sha256': config_sha},
        'seed': {'value': seed},
        'data': {},
    }


def _tmpdir(case: unittest.TestCase) -> Path:
    d = Path(tempfile.mkdtemp(prefix='stage1_'))
    case.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


CONFORMANCE_PROMPTS_10 = [{'id': 'p%d' % i,
                          'prompt': 'def f%d(x):\n    """Return x unchanged, task %d."""\n' % (i, i)}
                         for i in range(10)]


def _real_extract_code(text: str) -> str:
    """The REAL `experiments/local_stream/agent.extract_code`, executed from its own AST nodes --
    the same "extract the function from source, do not import the heavy module" discipline
    `tests_lab_design.test_normalization_matches_pilot` already uses for `timing_pilot._norm` --
    so this control needs no `experiments/local_stream` `sandbox`/`verify`/`common` import (the
    same discipline `lab_stage1`'s own docstring gives for not importing `agent`).  Pulls
    `_CODE_BLOCK`, `_SPECIAL_TOKENS` and `extract_code` itself straight from `agent.py`'s AST, so
    this control cannot silently drift from the real regexes the way a hand-copied pattern could."""
    source = (REPO_ROOT / 'experiments' / 'local_stream' / 'agent.py').read_text('utf-8')
    tree = ast.parse(source)
    wanted = {'_CODE_BLOCK', '_SPECIAL_TOKENS'}
    nodes = [n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets)]
    nodes.append(next(n for n in tree.body
                      if isinstance(n, ast.FunctionDef) and n.name == 'extract_code'))
    namespace: dict = {'re': re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<agent>', 'exec'), namespace)
    return namespace['extract_code'](text)


class GoldenCaptureTests(unittest.TestCase):
    """capture_reference + write_golden_objects: the golden-request bootstrap and writer of
    design_notes/DESIGN_PROPOSAL.md section 3 item 4."""

    def test_positive_two_independent_captures_are_byte_identical(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        with mock_server(scenario) as base_url_a:
            captured_a = lab_stage1.capture_reference(base_url_a, 'coder', sampling=SAMPLING,
                                                       target_kind='mock')
        with mock_server(scenario) as base_url_b:
            captured_b = lab_stage1.capture_reference(base_url_b, 'coder', sampling=SAMPLING,
                                                       target_kind='mock')
        dir_a, dir_b = _tmpdir(self), _tmpdir(self)
        out_a = lab_stage1.write_golden_objects(dir_a, 'coder', captured_a)
        out_b = lab_stage1.write_golden_objects(dir_b, 'coder', captured_b)
        self.assertEqual(out_a, out_b)
        for name in ('golden_props_coder.json', 'golden_generation_settings_coder.json'):
            self.assertEqual((dir_a / name).read_bytes(), (dir_b / name).read_bytes(),
                             f'{name}: two captures of an identical scenario must be '
                             'byte-identical')

    def test_negative_a_different_mock_scenario_gives_different_golden_files(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario_a = _scenario(model_path, model_alias='mock-alias-A')
        scenario_b = _scenario(model_path, model_alias='mock-alias-B')
        with mock_server(scenario_a) as base_url_a:
            captured_a = lab_stage1.capture_reference(base_url_a, 'coder', sampling=SAMPLING,
                                                       target_kind='mock')
        with mock_server(scenario_b) as base_url_b:
            captured_b = lab_stage1.capture_reference(base_url_b, 'coder', sampling=SAMPLING,
                                                       target_kind='mock')
        dir_a, dir_b = _tmpdir(self), _tmpdir(self)
        out_a = lab_stage1.write_golden_objects(dir_a, 'coder', captured_a)
        out_b = lab_stage1.write_golden_objects(dir_b, 'coder', captured_b)
        self.assertNotEqual(out_a['golden_props_sha256'], out_b['golden_props_sha256'],
                            'a different scripted /props must not produce the same golden '
                            'digest -- otherwise the byte-identity check above would be '
                            'vacuously true')

    def test_negative_writer_refuses_an_untokenized_model_path(self) -> None:
        # mirrors lab_orchestrator.load_golden_objects's own rejection (lab_orchestrator.py:
        # 1599-1602) of a golden /props whose model_path is not tokenized
        captured = {'props': {'model_path': '/definitely/not/a/known/root/model.gguf'},
                   'generation_settings': {'temperature': 0.7}}
        with self.assertRaises(lab_stage1.Stage1Error):
            lab_stage1.write_golden_objects(_tmpdir(self), 'coder', captured)

    def test_positive_writer_accepts_an_already_tokenized_model_path(self) -> None:
        # the companion positive case: the check above is not simply refusing everything
        captured = {'props': {'model_path': '<REPO>/models/coder.gguf'},
                   'generation_settings': {'temperature': 0.7}}
        out = lab_stage1.write_golden_objects(_tmpdir(self), 'coder', captured)
        self.assertIn('golden_props_sha256', out)

    def test_positive_written_golden_files_load_through_the_real_consumer(self) -> None:
        # exercises lab_orchestrator.load_golden_objects itself, unmocked
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        with mock_server(scenario) as base_url:
            captured = lab_stage1.capture_reference(base_url, 'coder', sampling=SAMPLING,
                                                     target_kind='mock')
        freeze_dir = _tmpdir(self)
        digests = lab_stage1.write_golden_objects(freeze_dir, 'coder', captured)
        cfg = {'receipt': {
            'golden_props_sha256': {'coder': digests['golden_props_sha256']},
            'golden_generation_settings_sha256':
                {'coder': digests['golden_generation_settings_sha256']},
            'mask': ['seed'], 'float_tolerance': 1e-6,
        }}
        golden, rows = lab_orchestrator.load_golden_objects(freeze_dir, cfg, ['coder'])
        self.assertEqual(rows, [], f'load_golden_objects reported drift: {rows}')
        self.assertIn('coder', golden)
        self.assertEqual(golden['coder']['props']['model_path'], captured['props']['model_path'])

    def test_negative_load_golden_objects_flags_a_tampered_file(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        with mock_server(scenario) as base_url:
            captured = lab_stage1.capture_reference(base_url, 'coder', sampling=SAMPLING,
                                                     target_kind='mock')
        freeze_dir = _tmpdir(self)
        digests = lab_stage1.write_golden_objects(freeze_dir, 'coder', captured)
        cfg = {'receipt': {
            'golden_props_sha256': {'coder': 'f' * 64},  # deliberately wrong
            'golden_generation_settings_sha256':
                {'coder': digests['golden_generation_settings_sha256']},
            'mask': ['seed'], 'float_tolerance': 1e-6,
        }}
        golden, rows = lab_orchestrator.load_golden_objects(freeze_dir, cfg, ['coder'])
        self.assertNotIn('coder', golden)
        self.assertTrue(any(r['item'] == 'golden_props_sha256.coder' for r in rows))


class RealServerRefusalTests(unittest.TestCase):
    """A NAMED REFUSAL for any target that is not the loopback lab_mock_server (this commit's
    authorization is scoped to it only; the real-server path is not approved)."""

    def test_negative_target_kind_real_is_refused(self) -> None:
        with self.assertRaises(lab_stage1.RealServerNotApproved) as ctx:
            lab_stage1.assert_mock_target('http://127.0.0.1:1', 'real')
        self.assertIn('not approved', str(ctx.exception))

    def test_negative_a_non_loopback_host_is_refused_even_with_target_kind_mock(self) -> None:
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.assert_mock_target('http://example.com:8080', 'mock')

    def test_positive_a_loopback_mock_target_is_accepted(self) -> None:
        lab_stage1.assert_mock_target('http://127.0.0.1:8091', 'mock')  # must not raise

    def test_negative_capture_reference_itself_refuses_a_real_target(self) -> None:
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.capture_reference('http://127.0.0.1:1', 'coder', sampling=SAMPLING,
                                         target_kind='real')


class ConformanceCounterTests(unittest.TestCase):
    """protocol_FINAL.md:585-587: "at least 9 of 10 responses of each model contain a code
    block ...".  The boundary is checked in both directions, and never by rounding up."""

    @staticmethod
    def _scenario_with_failed_tries(model_path: str, failed_tries: list) -> dict:
        faults = [{'match': {'kind': 'code', 'try': t}, 'do': 'http', 'status': 500}
                 for t in failed_tries]
        return _scenario(model_path, faults=faults)

    def test_positive_nine_of_ten_passes_at_the_boundary(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = self._scenario_with_failed_tries(model_path, [3])  # exactly 1 of 10 fails
        with mock_server(scenario) as base_url:
            report = lab_stage1.run_conformance_probe(
                base_url, CONFORMANCE_PROMPTS_10, target_kind='mock', sampling=SAMPLING,
                threshold=9)
        self.assertEqual(report['n_with_code_block'], 9)
        self.assertEqual(report['verdict'], 'PASS')

    def test_negative_two_of_ten_fails_not_rounded_up(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = self._scenario_with_failed_tries(model_path, [3, 7])  # 2 of 10 fail
        with mock_server(scenario) as base_url:
            report = lab_stage1.run_conformance_probe(
                base_url, CONFORMANCE_PROMPTS_10, target_kind='mock', sampling=SAMPLING,
                threshold=9)
        self.assertEqual(report['n_with_code_block'], 8)
        self.assertEqual(report['verdict'], 'FAIL',
                         '8 of 10 must FAIL against a threshold of 9, never rounded up to PASS')

    def test_positive_all_ten_pass_with_no_faults(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        with mock_server(scenario) as base_url:
            report = lab_stage1.run_conformance_probe(
                base_url, CONFORMANCE_PROMPTS_10, target_kind='mock', sampling=SAMPLING,
                threshold=9)
        self.assertEqual(report['n_with_code_block'], 10)
        self.assertEqual(report['verdict'], 'PASS')

    def test_positive_contains_code_block_agrees_with_the_pilot_pattern_on_fixtures(self) -> None:
        self.assertTrue(lab_stage1.contains_code_block('```python\nprint(1)\n```'))
        self.assertFalse(lab_stage1.contains_code_block('no fence here'))
        self.assertFalse(lab_stage1.contains_code_block(''))
        # the fence need not be at position 0 of the response -- this is exactly what
        # distinguishes `.search` (correct) from `.match` (adversarial review finding 6)
        self.assertTrue(lab_stage1.contains_code_block(
            'Sure, here is the code:\n```python\nprint(1)\n```'),
            'a fence after leading prose must still be found -- this would fail under `.match`')

    def test_negative_counts_code_block_presence_not_transport_success(self) -> None:
        """Adversarial review finding 4: the counter must count `has_code_block`, never
        `ok_transport` -- a materially weaker quantity `lab_mock_server`'s fixtures happen to
        agree with (every successful mock response is fenced), which is exactly why the earlier
        suite did not catch a `has_code_block` -> `ok_transport` field swap.  This exercises
        `_count_conforming` directly against synthetic rows where the two fields disagree AND
        the two counts differ (not merely which rows they pick), so a field-swap mutation cannot
        coincidentally land on the same total."""
        rows = [
            {'has_code_block': True, 'ok_transport': True},
            {'has_code_block': False, 'ok_transport': True},   # transport ok, no fence
            {'has_code_block': False, 'ok_transport': True},   # transport ok, no fence
            {'has_code_block': True, 'ok_transport': False},   # pathological, must still count
        ]
        # has_code_block count = 2; ok_transport count = 3 -- the two totals must differ, or a
        # `has_code_block` -> `ok_transport` field swap could coincidentally pass anyway.
        self.assertEqual(sum(1 for r in rows if r['has_code_block']), 2)
        self.assertEqual(sum(1 for r in rows if r['ok_transport']), 3)
        self.assertEqual(lab_stage1._count_conforming(rows), 2,
                         'must count has_code_block, never ok_transport')

    def test_pilot_code_block_pattern_matches_the_replicated_one(self) -> None:
        # lab_data.normalize_prompt is pinned against the pilot the same way
        # (tests_lab_design.test_normalization_matches_pilot); this does the same for
        # _CODE_BLOCK_RE against experiments/local_stream/agent.py's own _CODE_BLOCK, without
        # importing agent (see lab_stage1's module docstring for why).
        agent_src = (REPO_ROOT / 'experiments' / 'local_stream' / 'agent.py').read_text('utf-8')
        line = next(ln for ln in agent_src.splitlines() if ln.startswith('_CODE_BLOCK ='))
        self.assertIn(lab_stage1._CODE_BLOCK_RE.pattern, line,
                     'lab_stage1._CODE_BLOCK_RE has drifted from agent.py:_CODE_BLOCK')


class ShardResumeTests(unittest.TestCase):
    """One lab_shard_receipt per completed unit; resume ONLY through
    lab_prefreeze.resume_shard / lab_shard_receipt.verify_resume, never a presence-only check."""

    def test_unchanged_resume_is_reused_and_changed_pin_resume_is_refused(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        freeze_dir = _tmpdir(self)
        receipts_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins_v1 = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = lab_stage1.golden_shard(
                base_url=base_url, server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                pins=pins_v1, prefreeze_root=prefreeze_root)
        self.assertEqual(first['outcome'], 'success')

        # unchanged resume: same pins, no live server needed (resume never touches the network)
        second = lab_stage1.golden_shard(
            base_url='http://127.0.0.1:1', server_id='coder', freeze_dir=freeze_dir,
            receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
            pins=pins_v1, prefreeze_root=prefreeze_root)
        self.assertEqual(second['shard_id'], first['shard_id'])
        self.assertEqual(second, first)

        # changed pin: same shard id (same driver/schedule_row), different pins -> refused
        pins_v2 = _pins(seed=2)
        with self.assertRaises(sr.ResumeMismatch):
            lab_stage1.golden_shard(
                base_url='http://127.0.0.1:1', server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                pins=pins_v2, prefreeze_root=prefreeze_root)

    def test_negative_changed_sampling_with_unchanged_pins_is_refused(self) -> None:
        """Adversarial review finding 1: two `golden_shard` calls with an IDENTICAL caller-
        supplied `pins` but a DIFFERENT `sampling` must not silently resume a stale receipt --
        reproduced empirically before this fix (`temperature` 0.7 vs 0.9999 resumed with no
        error at all, the second call's `base_url` -- pointed at a closed local port -- never
        even dialed)."""
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        freeze_dir = _tmpdir(self)
        receipts_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = lab_stage1.golden_shard(
                base_url=base_url, server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                pins=pins, prefreeze_root=prefreeze_root)
        self.assertEqual(first['outcome'], 'success')
        changed_sampling = dict(SAMPLING, temperature=0.9999)
        with self.assertRaises(sr.ResumeMismatch):
            lab_stage1.golden_shard(
                base_url='http://127.0.0.1:1', server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
                sampling=changed_sampling, pins=pins, prefreeze_root=prefreeze_root)

    def test_positive_unchanged_sampling_and_seed_still_resume(self) -> None:
        # the companion positive case: the fix above must not turn every resume into a refusal
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        freeze_dir = _tmpdir(self)
        receipts_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = lab_stage1.golden_shard(
                base_url=base_url, server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                pins=pins, prefreeze_root=prefreeze_root)
        second = lab_stage1.golden_shard(
            base_url='http://127.0.0.1:1', server_id='coder', freeze_dir=freeze_dir,
            receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
            sampling=dict(SAMPLING), pins=pins, prefreeze_root=prefreeze_root)
        self.assertEqual(second, first)

    def test_conformance_shard_refuses_changed_sampling_or_threshold_with_unchanged_pins(
            self) -> None:
        """The same finding-1 fix, for `conformance_shard`'s own `sampling`/`threshold`."""
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir = _tmpdir(self)
        out_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = lab_stage1.conformance_shard(
                base_url=base_url, prompts=CONFORMANCE_PROMPTS_10, server_id='coder',
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                threshold=9, pins=pins, out_dir=out_dir, prefreeze_root=prefreeze_root)
        self.assertEqual(first['outcome'], 'success')
        with self.assertRaises(sr.ResumeMismatch):
            lab_stage1.conformance_shard(
                base_url='http://127.0.0.1:1', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
                sampling=dict(SAMPLING, temperature=0.9999), threshold=9, pins=pins,
                out_dir=out_dir, prefreeze_root=prefreeze_root)
        with self.assertRaises(sr.ResumeMismatch):
            lab_stage1.conformance_shard(
                base_url='http://127.0.0.1:1', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
                sampling=SAMPLING, threshold=8, pins=pins, out_dir=out_dir,
                prefreeze_root=prefreeze_root)

    def test_conformance_shard_resume_follows_the_same_discipline(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir = _tmpdir(self)
        out_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins_v1 = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = lab_stage1.conformance_shard(
                base_url=base_url, prompts=CONFORMANCE_PROMPTS_10, server_id='coder',
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                threshold=9, pins=pins_v1, out_dir=out_dir, prefreeze_root=prefreeze_root)
        self.assertEqual(first['outcome'], 'success')
        second = lab_stage1.conformance_shard(
            base_url='http://127.0.0.1:1', prompts=CONFORMANCE_PROMPTS_10, server_id='coder',
            receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
            threshold=9, pins=pins_v1, out_dir=out_dir, prefreeze_root=prefreeze_root)
        self.assertEqual(second, first)
        with self.assertRaises(sr.ResumeMismatch):
            lab_stage1.conformance_shard(
                base_url='http://127.0.0.1:1', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
                sampling=SAMPLING, threshold=9, pins=_pins(seed=2), out_dir=out_dir,
                prefreeze_root=prefreeze_root)


class LabClientByteIdentityTests(unittest.TestCase):
    """``lab_client.py`` must stay byte-identical (root 07:18): its blob sha256 at the current
    worktree HEAD equals its value at the pinned commit ``878fa70``."""

    def test_lab_client_unchanged_since_878fa70(self) -> None:
        pinned = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'show', '878fa70:experiments/live_ab/lab_client.py'],
            capture_output=True, check=True)
        pinned_sha = lab_common.sha256_bytes(pinned.stdout)
        current_sha = lab_common.sha256_file(LIVE / 'lab_client.py')
        self.assertEqual(current_sha, pinned_sha,
                         'lab_client.py must stay byte-identical to its state at 878fa70')


class MutationControlTests(unittest.TestCase):
    """Proves :class:`ConformanceCounterTests`'s boundary check is not vacuous: a deliberately
    broken copy of the verdict comparison, loaded from a scratch file under the session's
    ``tmp_agents`` directory (never the worktree -- the HARD RULES forbid mutating it), disagrees
    with the REAL ``lab_stage1._verdict`` on the exact 9-of-10 boundary case the positive control
    above checks.

    An earlier version of this test hardcoded ``real_verdict = 'PASS' if 9 >= 9 else 'FAIL'`` as
    a bare Python expression and never imported or called anything in ``lab_stage1`` -- it proved
    nothing about the real module despite its docstring's claim (an independent adversarial
    review's finding 3).  ``lab_stage1._verdict`` was extracted to its own function precisely so
    this test could call it directly instead."""

    def test_a_broken_threshold_comparison_would_have_been_caught(self) -> None:
        TMP_AGENTS.mkdir(parents=True, exist_ok=True)
        mutant_path = TMP_AGENTS / 'mutant_stage1_conformance_verdict.py'
        # The mutant reimplements ONLY the verdict comparison, with a deliberately wrong
        # operator (`>` instead of `>=`) -- exactly the off-by-one this project's own review
        # discipline calls out ("never rounding up"). It is never imported by, or wired into,
        # lab_stage1 itself; it exists only so this test can show the boundary control would
        # have failed against it.
        mutant_path.write_text(
            "def verdict(n_with_code_block, threshold):\n"
            "    return 'PASS' if n_with_code_block > threshold else 'FAIL'\n",
            encoding='utf-8')
        import importlib.util
        spec = importlib.util.spec_from_file_location('mutant_stage1_conformance_verdict',
                                                       mutant_path)
        mutant = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mutant)

        # the exact scenario ConformanceCounterTests.test_positive_nine_of_ten_passes_at_the_
        # boundary checks: 9 of 10, threshold 9 -- calling the REAL module's own function, not a
        # hand-copied literal expression.
        real_verdict = lab_stage1._verdict(9, 9)
        self.assertEqual(real_verdict, 'PASS')
        mutant_verdict = mutant.verdict(9, 9)
        self.assertEqual(mutant_verdict, 'FAIL',
                         'fixture drift: the mutant must disagree with the real module at the '
                         'boundary for this control to mean anything')
        self.assertNotEqual(mutant_verdict, real_verdict,
                            "the mutant's off-by-one silently turns a PASS into a FAIL at the "
                            'boundary -- exactly the defect class '
                            'ConformanceCounterTests.test_positive_nine_of_ten_passes_at_the_'
                            'boundary exists to catch')


class FailurePropagationTests(unittest.TestCase):
    """Adversarial review finding 5: the claimed failure-path contract -- "a capture/write
    failure propagates ... and writes NO receipt" -- was previously asserted only in
    :func:`lab_stage1.golden_shard`'s own docstring, with no test exercising a mock/transport
    failure during golden capture.  This drives a real transport failure through the mock server
    (never a swallowed/simulated one) and checks both halves of the contract directly."""

    def test_negative_a_capture_failure_propagates_and_writes_no_receipt(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        # capture_reference's reference request classifies kind='smoke' (it sends
        # lab_server.SMOKE_PROMPT); this fault fails every such request with HTTP 500.
        scenario = _scenario(model_path,
                             faults=[{'match': {'kind': 'smoke'}, 'do': 'http', 'status': 500}])
        freeze_dir = _tmpdir(self)
        receipts_dir = _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        with mock_server(scenario) as base_url:
            with self.assertRaises(lab_stage1.Stage1Error):
                lab_stage1.golden_shard(
                    base_url=base_url, server_id='coder', freeze_dir=freeze_dir,
                    receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                    pins=_pins(), prefreeze_root=prefreeze_root)
        self.assertEqual(sr.completed_shards(receipts_dir), frozenset(),
                         'a failed capture must write NO shard receipt')
        self.assertEqual(list(Path(freeze_dir).glob('golden_*.json')), [],
                         'a failed capture must write NO golden file either')


class ProtocolInterpretationTests(unittest.TestCase):
    """Adversarial review finding 2: `run_conformance_probe`'s earlier docstring claimed it
    "applies protocol_FINAL.md 585-587's own rule verbatim," but `contains_code_block` actually
    implements a STRICTER, fence-presence-only reading than a fully literal reading of that text
    would give (see `lab_stage1.contains_code_block`'s docstring for the full account).  This
    makes that divergence an executable, quantified fact -- driven against the REAL
    `experiments/local_stream/agent.extract_code` -- rather than only prose in a docstring."""

    def test_negative_a_literal_extract_code_reading_is_far_looser_than_fence_presence(
            self) -> None:
        prose_only = 'Sure, here is the answer: it is 42.'
        self.assertFalse(lab_stage1.contains_code_block(prose_only),
                         'no fence -> lab_stage1 reports non-conforming')
        self.assertNotEqual(_real_extract_code(prose_only), '',
                            'yet the REAL extract_code returns non-empty text for this same '
                            'unfenced response (its non-fence fallback branch) -- a fully '
                            'literal reading of protocol_FINAL.md:585-587 would count this as '
                            'conforming, which lab_stage1 deliberately does not')

    def test_positive_a_fenced_response_agrees_with_both_readings(self) -> None:
        fenced = '```python\nprint(1)\n```'
        self.assertTrue(lab_stage1.contains_code_block(fenced))
        self.assertNotEqual(_real_extract_code(fenced), '')

    def test_negative_whenever_lab_stage1_says_true_extract_code_is_never_effectively_empty(
            self) -> None:
        # soundness in one direction only: contains_code_block never claims conformance the real
        # extract_code would actually disagree with by returning an effectively empty program.
        samples = ['```python\nprint(1)\n```',
                  'prose\n```py\nx = 1\n```\nmore prose',
                  '```\nraw fence no lang\n```']
        for text in samples:
            with self.subTest(text=text):
                if lab_stage1.contains_code_block(text):
                    self.assertNotEqual(
                        _real_extract_code(text).strip(), '',
                        f'{text!r}: contains_code_block said True but the real extract_code '
                        'returned an effectively empty program')


if __name__ == '__main__':
    unittest.main()
