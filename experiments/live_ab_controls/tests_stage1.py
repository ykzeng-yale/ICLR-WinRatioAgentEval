"""Controls for ``lab_stage1`` (design_notes/DESIGN_PROPOSAL.md section 3 item 4; authorized
against ``lab_mock_server`` only by root's 2026-09-26 07:18 bounded review,
`reviews/drivers_successor_pin_bounded_review_20260926_0718.md`, item 1).

Every positive check here has a NEGATIVE CONTROL beside it -- the same call on an input it must
refuse, or on a scenario it must disagree with -- so none of these can pass vacuously.  What
runs: ``lab_mock_server`` on a free loopback port, served in a thread for one test's duration
(the same pattern ``experiments/live_ab/tests_lab_serving.py`` already uses); no real model, no
real ``llama-server``, no ``llama.cpp`` build, no network beyond that loopback and ``git show``
(read-only).  :class:`MutationControlTests` goes one step further and proves the conformance
counter's own boundary control can fail: it patches the real verdict comparison with an
off-by-one and runs the exact 9-of-10 boundary scenario through the real counter.

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


def _predeclared_conformance_prompts() -> list:
    """The REAL exactly-ten predeclared ids of protocol 5.8, read straight from config.json (the
    same `lab_common.harness_config()` source `lab_stage1._predeclared_prompt_ids` reads): the
    six `roster.smoke_tasks` ids (arbitrary-but-fixed prompt text this control invents, since the
    real MBPP prompt text for these ids is out of `lab_stage1`'s MATRIX row and out of this
    control's reach too) plus the four `prefreeze.conformance_prompts` ids WITH THEIR REAL text
    from config.json (`lab_stage1.run_conformance_probe` checks these four's text directly, so a
    fixture with invented text for them would be refused rather than exercising the counter).
    Order here is deliberately config.json's own smoke-then-conformance order; a test that wants
    a *different* order builds its own list from this one's items."""
    cfg = lab_common.harness_config()
    smoke_ids = list(cfg['roster']['smoke_tasks'])
    prompts = [{'id': uid,
               'prompt': 'def f_%s(x):\n    """Return x unchanged, task %s."""\n'
                         % (uid.replace('/', '_'), uid)}
              for uid in smoke_ids]
    prompts += [{'id': p['id'], 'prompt': p['prompt']}
               for p in cfg['prefreeze']['conformance_prompts']]
    return prompts


CONFORMANCE_PROMPTS_10 = _predeclared_conformance_prompts()


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
        """Adversarial review finding 4: the counter must count `conforms` (root's 2026-09-26
        10:19 frozen predicate), never `ok_transport` -- a materially weaker quantity
        `lab_mock_server`'s fixtures happen to agree with (every successful mock response is a
        real fenced program), which is exactly why the earlier suite did not catch a
        `has_code_block`/`conforms` -> `ok_transport` field swap.  This exercises
        `_count_conforming` directly against synthetic rows where the fields disagree AND the
        counts differ (not merely which rows they pick), so a field-swap mutation cannot
        coincidentally land on the same total."""
        rows = [
            {'has_code_block': True, 'conforms': True, 'ok_transport': True},
            {'has_code_block': False, 'conforms': False, 'ok_transport': True},  # no fence
            {'has_code_block': True, 'conforms': False, 'ok_transport': True},   # empty fence
            {'has_code_block': True, 'conforms': True, 'ok_transport': False},  # pathological
        ]
        # conforms count = 2; has_code_block count = 3; ok_transport count = 3 -- all three
        # totals must differ, or a field-swap mutation could coincidentally pass anyway.
        self.assertEqual(sum(1 for r in rows if r['conforms']), 2)
        self.assertEqual(sum(1 for r in rows if r['has_code_block']), 3)
        self.assertEqual(sum(1 for r in rows if r['ok_transport']), 3)
        self.assertEqual(lab_stage1._count_conforming(rows), 2,
                         'must count conforms, never has_code_block or ok_transport')

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
    """``lab_client.py`` must stay byte-identical (root 07:18): its sha256 in this checkout equals
    the value the root-accepted pin receipt
    ``results/live_ab/HARNESS_PIN_SUCCESSOR_20260926_0600.json`` records in its successor harness
    map.  Read from that committed receipt, not from git history, so a shallow or sparse
    reproduction checks it too (the earlier form read an older commit with ``git show`` and was
    refused by ``tests_repro_inputs.HistoryListTests``, which requires every commit a control reads
    to be listed in ``repro_inputs.HISTORY``)."""

    RECEIPT = lab_common.REPO_ROOT / 'results' / 'live_ab' / 'HARNESS_PIN_SUCCESSOR_20260926_0600.json'

    def pinned_sha(self) -> str:
        receipt = json.loads(self.RECEIPT.read_text('utf-8'))
        return receipt['harness_pin']['successor']['map']['lab_client.py']

    def test_lab_client_unchanged_since_the_accepted_pin(self) -> None:
        self.assertEqual(lab_common.sha256_file(LIVE / 'lab_client.py'), self.pinned_sha(),
                         'lab_client.py must stay byte-identical to the accepted pin')

    def test_negative_a_changed_lab_client_would_be_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'lab_client.py'
            changed.write_bytes((LIVE / 'lab_client.py').read_bytes() + b'\n# drift\n')
            self.assertNotEqual(lab_common.sha256_file(changed), self.pinned_sha())


class MutationControlTests(unittest.TestCase):
    """Proves :class:`ConformanceCounterTests`'s boundary check is not vacuous.  The REAL
    ``lab_stage1._verdict`` is patched with an off-by-one (``>`` instead of ``>=``) and the exact
    9-of-10 scenario of ``test_positive_nine_of_ten_passes_at_the_boundary`` is run through the
    real ``run_conformance_probe`` against ``lab_mock_server``: it now reports FAIL, so that
    positive control (which asserts PASS) would fail.  Nothing is written to disk.

    Earlier versions hardcoded ``'PASS' if 9 >= 9 else 'FAIL'`` (an independent review's finding
    3), and then compared a hand-written stand-in with the real function without running the
    real counter through it; both proved less than they claimed."""

    def test_an_off_by_one_verdict_is_caught_by_the_boundary_control(self) -> None:
        self.assertEqual(lab_stage1._verdict(9, 9), 'PASS')
        helper = ConformanceCounterTests('test_positive_nine_of_ten_passes_at_the_boundary')
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = helper._scenario_with_failed_tries(model_path, [3])  # exactly 1 of 10 fails
        broken = lambda n, threshold: 'PASS' if n > threshold else 'FAIL'  # noqa: E731
        from unittest import mock
        with mock.patch.object(lab_stage1, '_verdict', broken):
            with mock_server(scenario) as base_url:
                report = lab_stage1.run_conformance_probe(
                    base_url, CONFORMANCE_PROMPTS_10, target_kind='mock', sampling=SAMPLING,
                    threshold=9)
        self.assertEqual(report['n_with_code_block'], 9)
        self.assertEqual(report['verdict'], 'FAIL',
                         'the off-by-one must flip the boundary verdict, or the positive '
                         'boundary control could not catch it')

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


class ConformancePredicateTests(unittest.TestCase):
    """`lab_stage1.conforms`: root's 2026-09-26 10:19 frozen predicate (finding 2), the
    conjunction of `contains_code_block` and the REAL `extract_code`'s non-whitespace output --
    never either half alone."""

    def test_negative_an_empty_first_fence_does_not_conform(self) -> None:
        text = '```python\n\n```'
        self.assertTrue(lab_stage1.contains_code_block(text),
                        'sanity: the fence itself must still be detected')
        self.assertEqual(_real_extract_code(text), '\n',
                         'sanity: the real extractor must return only a newline for this text')
        self.assertFalse(lab_stage1.conforms(text),
                         'an empty first fence must not conform even though a fence is present')

    def test_negative_an_empty_first_fence_does_not_conform_even_with_a_later_real_fence(
            self) -> None:
        # the empty FIRST block is what extract_code returns (it takes blocks[0]); valid code in
        # a LATER fence must not rescue conformance.
        text = '```python\n\n```\nSure, and here it is for real:\n```python\nprint(1)\n```'
        self.assertTrue(lab_stage1.contains_code_block(text))
        self.assertEqual(_real_extract_code(text), '\n',
                         "the real extractor's blocks[0] is the EMPTY first fence, not the "
                         'valid one that follows')
        self.assertFalse(lab_stage1.conforms(text))

    def test_negative_unfenced_prose_does_not_conform(self) -> None:
        text = 'Sure, here is the answer: it is 42.'
        self.assertNotEqual(_real_extract_code(text), '',
                            "sanity: the real extractor's non-fence fallback branch returns "
                            'non-empty text for this same unfenced response')
        self.assertFalse(lab_stage1.conforms(text),
                         'unfenced prose must not conform even though the real extractor '
                         'returns non-empty text for it (its fallback branch, not a fence)')

    def test_positive_a_normal_fenced_program_conforms(self) -> None:
        text = '```python\ndef f(x):\n    return x\n```'
        self.assertTrue(lab_stage1.contains_code_block(text))
        self.assertNotEqual(_real_extract_code(text).strip(), '')
        self.assertTrue(lab_stage1.conforms(text))

    def test_positive_leading_prose_before_a_real_fence_still_conforms(self) -> None:
        text = 'Sure, here is the code:\n```python\nprint(1)\n```'
        self.assertTrue(lab_stage1.conforms(text))


class PromptSetGuardTests(unittest.TestCase):
    """`run_conformance_probe` REFUSES (`PromptSetRefused`) any `prompts` that is not exactly
    ten items, or not exactly config.json's predeclared ten ids (root's 2026-09-26 10:19 review,
    finding 2) -- checked BEFORE any request is sent, so none of these tests need a live server."""

    def test_negative_nine_prompts_is_refused(self) -> None:
        nine = CONFORMANCE_PROMPTS_10[:9]
        with self.assertRaises(lab_stage1.PromptSetRefused):
            lab_stage1.run_conformance_probe(
                'http://127.0.0.1:1', nine, target_kind='mock', sampling=SAMPLING, threshold=9)

    def test_negative_eleven_prompts_is_refused(self) -> None:
        eleven = CONFORMANCE_PROMPTS_10 + [{'id': 'oodp/5', 'prompt': 'def g(x):\n    return x\n'}]
        with self.assertRaises(lab_stage1.PromptSetRefused):
            lab_stage1.run_conformance_probe(
                'http://127.0.0.1:1', eleven, target_kind='mock', sampling=SAMPLING, threshold=9)

    def test_negative_a_changed_prompt_set_is_refused(self) -> None:
        # exactly ten items, but one id substituted for one outside the predeclared set
        changed = CONFORMANCE_PROMPTS_10[:-1] + [{'id': 'oodp/999', 'prompt': 'def h(x):\n    return x\n'}]
        self.assertEqual(len(changed), 10)
        with self.assertRaises(lab_stage1.PromptSetRefused):
            lab_stage1.run_conformance_probe(
                'http://127.0.0.1:1', changed, target_kind='mock', sampling=SAMPLING,
                threshold=9)

    def test_negative_a_changed_declared_prompt_text_is_refused(self) -> None:
        # same ten predeclared ids, but one of the four config-declared oodp prompts carries
        # text that disagrees with config.json's own text for it
        tampered = [dict(p) for p in CONFORMANCE_PROMPTS_10]
        for p in tampered:
            if p['id'] == 'oodp/1':
                p['prompt'] = 'A DIFFERENT PROMPT'
        with self.assertRaises(lab_stage1.PromptSetRefused):
            lab_stage1.run_conformance_probe(
                'http://127.0.0.1:1', tampered, target_kind='mock', sampling=SAMPLING,
                threshold=9)

    def test_negative_a_duplicate_id_is_refused(self) -> None:
        dup = CONFORMANCE_PROMPTS_10[:-1] + [CONFORMANCE_PROMPTS_10[0]]
        self.assertEqual(len(dup), 10)
        with self.assertRaises(lab_stage1.PromptSetRefused):
            lab_stage1.run_conformance_probe(
                'http://127.0.0.1:1', dup, target_kind='mock', sampling=SAMPLING, threshold=9)

    def test_positive_the_real_predeclared_ten_is_accepted(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        with mock_server(scenario) as base_url:
            report = lab_stage1.run_conformance_probe(
                base_url, CONFORMANCE_PROMPTS_10, target_kind='mock', sampling=SAMPLING,
                threshold=9)
        self.assertEqual(report['n_prompts'], 10)

    def test_positive_predeclared_ids_are_exactly_ten_from_config(self) -> None:
        ids = lab_stage1._predeclared_prompt_ids()
        self.assertEqual(len(ids), 10)
        self.assertEqual(ids, frozenset(p['id'] for p in CONFORMANCE_PROMPTS_10))


class _ExplodingSession:
    """A `session` double whose `get`/`post` raise immediately -- used to prove a refused call
    makes NO network request at all, stronger than merely observing no successful response."""

    def get(self, *a, **k):
        raise AssertionError('no network request may be made when the mock-only guard refuses '
                             'before any resume/probe attempt')

    def post(self, *a, **k):
        raise AssertionError('no network request may be made when the mock-only guard refuses '
                             'before any resume/probe attempt')


class GuardBeforeResumeTests(unittest.TestCase):
    """`assert_mock_target` fires BEFORE any resume return, in EVERY public shard entry point
    (root's 2026-09-26 10:19 review, finding 3): a `target_kind='real'` or non-loopback
    `base_url` call must raise even when a matching mock receipt already exists on disk with
    otherwise-unchanged pins -- never silently handed that receipt -- and must make no network
    request and write no new receipt."""

    def test_golden_shard_refuses_a_real_target_before_resuming(self) -> None:
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
        before = sr.completed_shards(receipts_dir)
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.golden_shard(
                base_url='https://external.invalid', server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='real', sampling=SAMPLING,
                pins=pins, prefreeze_root=prefreeze_root, session=_ExplodingSession())
        self.assertEqual(sr.completed_shards(receipts_dir), before,
                         'a refused real-target call must write no new receipt')

    def test_golden_shard_refuses_a_changed_non_loopback_target_before_resuming(self) -> None:
        # the companion "changed target" control: target_kind='mock' but base_url is NOT
        # loopback -- assert_mock_target's second, independent check must still fire first.
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
        before = sr.completed_shards(receipts_dir)
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.golden_shard(
                base_url='http://example.com:8080', server_id='coder', freeze_dir=freeze_dir,
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                pins=pins, prefreeze_root=prefreeze_root, session=_ExplodingSession())
        self.assertEqual(sr.completed_shards(receipts_dir), before)

    def test_conformance_shard_refuses_a_real_target_before_resuming(self) -> None:
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
        before = sr.completed_shards(receipts_dir)
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.conformance_shard(
                base_url='https://external.invalid', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='real',
                sampling=SAMPLING, threshold=9, pins=pins, out_dir=out_dir,
                prefreeze_root=prefreeze_root, session=_ExplodingSession())
        self.assertEqual(sr.completed_shards(receipts_dir), before,
                         'a refused real-target call must write no new receipt')

    def test_conformance_shard_refuses_a_changed_non_loopback_target_before_resuming(
            self) -> None:
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
        before = sr.completed_shards(receipts_dir)
        with self.assertRaises(lab_stage1.RealServerNotApproved):
            lab_stage1.conformance_shard(
                base_url='http://example.com:8080', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='mock',
                sampling=SAMPLING, threshold=9, pins=pins, out_dir=out_dir,
                prefreeze_root=prefreeze_root, session=_ExplodingSession())
        self.assertEqual(sr.completed_shards(receipts_dir), before)


class PromptBindingResumeTests(unittest.TestCase):
    """`conformance_shard`'s resume pins fold in the exact ordered `(id, prompt)` pairs (root's
    2026-09-26 10:19 review, finding 1): changed text, changed id, or changed order at an
    otherwise-unchanged caller `pins` must each be refused on resume; an unchanged resume is
    still reused (the positive companion, so the fix does not turn every resume into a
    refusal)."""

    def _first(self, receipts_dir, out_dir, prefreeze_root, pins, base_url, prompts):
        return lab_stage1.conformance_shard(
            base_url=base_url, prompts=prompts, server_id='coder', receipts_dir=receipts_dir,
            inv=_inv(), target_kind='mock', sampling=SAMPLING, threshold=9, pins=pins,
            out_dir=out_dir, prefreeze_root=prefreeze_root)

    def test_negative_changed_prompt_text_is_refused_on_resume(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir, out_dir = _tmpdir(self), _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = self._first(receipts_dir, out_dir, prefreeze_root, pins, base_url,
                                CONFORMANCE_PROMPTS_10)
        self.assertEqual(first['outcome'], 'success')
        changed = [dict(CONFORMANCE_PROMPTS_10[0], prompt='A DIFFERENT PROMPT')] \
            + CONFORMANCE_PROMPTS_10[1:]
        with self.assertRaises(sr.ResumeMismatch):
            self._first(receipts_dir, out_dir, prefreeze_root, pins, 'http://127.0.0.1:1',
                       changed)

    def test_negative_changed_prompt_id_is_refused_on_resume(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir, out_dir = _tmpdir(self), _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = self._first(receipts_dir, out_dir, prefreeze_root, pins, base_url,
                                CONFORMANCE_PROMPTS_10)
        self.assertEqual(first['outcome'], 'success')
        # the id of position 0 changes (its text is unchanged) -- the resume pin's ordered
        # (id, prompt) digest must still catch this even though the TEXT at every position is
        # exactly what was recorded.
        changed_id = [dict(CONFORMANCE_PROMPTS_10[0], id=CONFORMANCE_PROMPTS_10[0]['id'] + '-x')]\
            + CONFORMANCE_PROMPTS_10[1:]
        with self.assertRaises(sr.ResumeMismatch):
            self._first(receipts_dir, out_dir, prefreeze_root, pins, 'http://127.0.0.1:1',
                       changed_id)

    def test_negative_changed_order_is_refused_on_resume(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir, out_dir = _tmpdir(self), _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = self._first(receipts_dir, out_dir, prefreeze_root, pins, base_url,
                                CONFORMANCE_PROMPTS_10)
        self.assertEqual(first['outcome'], 'success')
        reordered = list(reversed(CONFORMANCE_PROMPTS_10))
        self.assertEqual(frozenset(p['id'] for p in reordered),
                         frozenset(p['id'] for p in CONFORMANCE_PROMPTS_10),
                         'sanity: same set of ids, only the order differs')
        with self.assertRaises(sr.ResumeMismatch):
            self._first(receipts_dir, out_dir, prefreeze_root, pins, 'http://127.0.0.1:1',
                       reordered)

    def test_positive_an_unchanged_resume_is_still_reused(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        receipts_dir, out_dir = _tmpdir(self), _tmpdir(self)
        prefreeze_root = _tmpdir(self) / '_prefreeze'
        pins = _pins(seed=1)
        with mock_server(scenario) as base_url:
            first = self._first(receipts_dir, out_dir, prefreeze_root, pins, base_url,
                                CONFORMANCE_PROMPTS_10)
        self.assertEqual(first['outcome'], 'success')
        second = self._first(receipts_dir, out_dir, prefreeze_root, pins, 'http://127.0.0.1:1',
                             list(CONFORMANCE_PROMPTS_10))  # a fresh, equal-by-value list
        self.assertEqual(second, first)


class RootTenNineteenWitnessReproductionTests(unittest.TestCase):
    """Reproduces, as FAILING tests against the pinned pre-repair code (`b229060`), the three
    HIGH witnesses of root's 2026-09-26 10:19 interim review
    (`reviews/stage1_pin_and_conformance_interim_20260926_1019.md`), before any repair is
    applied. Each assertion states the POST-repair requirement; run against the unfixed
    ``lab_stage1``, each one fails (or errors, for the not-yet-existing ``conforms`` name) --
    that failure IS the reproduction. Once the repair lands these same three tests pass."""

    def test_witness_1_changed_prompt_text_silently_resumes_a_stale_receipt(self) -> None:
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
        changed_prompts = [dict(CONFORMANCE_PROMPTS_10[0], prompt='A DIFFERENT PROMPT')] \
            + CONFORMANCE_PROMPTS_10[1:]
        # root's witness: this call, with UNCHANGED pins, returned the ORIGINAL receipt with no
        # refusal and no network request. Post-repair it must instead raise ResumeMismatch.
        with self.assertRaises(sr.ResumeMismatch,
                               msg='root witness 1: changed prompt 0 text with unchanged pins '
                                   'must be refused on resume, not silently reused'):
            lab_stage1.conformance_shard(
                base_url='http://127.0.0.1:1', prompts=changed_prompts, server_id='coder',
                receipts_dir=receipts_dir, inv=_inv(), target_kind='mock', sampling=SAMPLING,
                threshold=9, pins=pins, out_dir=out_dir, prefreeze_root=prefreeze_root)

    def test_witness_2a_nine_prompts_at_threshold_nine_must_be_refused_not_passed(self) -> None:
        model_path = str(lab_common.REPO_ROOT / 'work' / 'live_ab' / 'models' / 'coder.gguf')
        scenario = _scenario(model_path)
        nine = CONFORMANCE_PROMPTS_10[:9]
        # root's witness: run_conformance_probe returned PASS for 9 of 9 mock prompts at
        # threshold 9. Post-repair, a 9-prompt list must be REFUSED outright (only exactly ten,
        # the predeclared set, is a legal probe), never silently scored as a 9-prompt run.
        with mock_server(scenario) as base_url:
            with self.assertRaises(
                    lab_stage1.PromptSetRefused,
                    msg='root witness 2a: a 9-prompt list must be refused, not scored PASS'):
                lab_stage1.run_conformance_probe(
                    base_url, nine, target_kind='mock', sampling=SAMPLING, threshold=9)

    def test_witness_2b_empty_first_fence_must_not_conform(self) -> None:
        # root's witness: contains_code_block('```python\n\n```') == True although the real
        # extract_code returns only '\n' for it. Post-repair, the frozen predicate is the
        # CONJUNCTION contains_code_block(...) AND real_extract_code(...).strip() != '' --
        # exposed as `lab_stage1.conforms`, which does not exist on the pre-repair code (hence
        # this errors with AttributeError there, which is this witness's reproduction).
        text = '```python\n\n```'
        self.assertTrue(lab_stage1.contains_code_block(text))
        self.assertEqual(_real_extract_code(text), '\n')
        self.assertFalse(lab_stage1.conforms(text),
                         'root witness 2b: an empty first fence must not conform even though '
                         'contains_code_block is True')

    def test_witness_3_real_target_bypasses_the_mock_only_guard_on_resume(self) -> None:
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
        # root's witness: target_kind='real', base_url='https://external.invalid', UNCHANGED
        # pins -> returned the mock receipt rather than raising RealServerNotApproved. Post-
        # repair the guard must fire BEFORE the resume return.
        with self.assertRaises(
                lab_stage1.RealServerNotApproved,
                msg='root witness 3: a real target with unchanged pins must be refused before '
                    'any resume return, not given the mock receipt'):
            lab_stage1.conformance_shard(
                base_url='https://external.invalid', prompts=CONFORMANCE_PROMPTS_10,
                server_id='coder', receipts_dir=receipts_dir, inv=_inv(), target_kind='real',
                sampling=SAMPLING, threshold=9, pins=pins, out_dir=out_dir,
                prefreeze_root=prefreeze_root)


if __name__ == '__main__':
    unittest.main()
