"""The serving-manifest binding on the REAL production entry path (root 01:53).

Root, ``reviews/serving_manifest_binding_ruling_20260924_0153.md``: "Preflight and every
invocation/start/restart must read that exact artifact and re-check its digest and the
launcher, recursively resolved non-system libraries, Metal library, build provenance and
``/props.build_info`` against the actual runtime as protocol §2.2 requires.  A missing file,
null digest, self-comparison, path substitution or runtime mismatch refuses."

Every control runs the unmodified ``lab_orchestrator.py`` ``main()`` as a subprocess
(``WORLD_FACTORY`` unset) exactly as ``tests_eb1_entry`` does -- its ``EntryTree``: a
temporary freeze tree, the EB1c shim behind the compiled ``sm_fixture`` launcher, and THE
serving manifest of that tree assembled from that compiled build by
``lab_serving_manifest.assemble`` at ``<results>/freeze/serving_manifest.json``, with its
canonical digest in the tree's ``llama_cpp.serving_manifest_sha256``.  No model, no
llama-server, no network beyond 127.0.0.1.

The controls, each with its negative control:

* SM1 the positive run (the negative control of every refusal below);
* SM2 a missing artifact; SM3 a null configuration digest (the bundle names the artifact's
  real digest, so ONLY the configuration digest is wrong); SM4 the artifact at another path
  (a runtime override naming it, a symlink at the fixed path, a runtime freeze tree);
* SM5 one library byte changed after assembly; SM6 a library added to the closure at runtime
  (ggml's backend search, ``libggml-*.so`` in the executable directory) -- all refused before
  seq 0 as ``preflight_refused(serving_manifest)`` naming the problem;
* SM7 the server's actual ``/props.build_info`` differs from the manifest's (golden object
  and scenario agree with each other, so nothing but the manifest can refuse it): the first
  start is ``server_start_failed(start, serving_manifest, [build_info, serving_manifest])``;
* SM8 a library changed between the first start and the supervised restart: the restart is
  refused at its ``serving_manifest`` stage (control: the same crash without the change
  restarts and verifies).  The process flips the library and dies on RECEIVING the pair's
  first call (``exit_before_response``), so that call's arrival waits on the server and a
  supervised restart is required before the trial can end; the shim's ``flips.jsonl``
  proves the change was made once, persisted, and preceded the ``server_down``.  The SM8
  diagnosis (``results/live_ab/SM8_DIAGNOSIS_*.json``) found the intermittent red of the
  pre-fix scenario (``exit_after_responses``: answered, then died): when both calls of the
  only pair were answered before the exit, the trial reached its horizon and closed before
  the next 5 s health poll, no restart ever ran and the entry exited 0.
  :class:`SM8ForcedInterleaving` forces that interleaving: the pre-fix scenario then exits
  0 every time (the check is never reached), the fixed one refuses every time;
* SM9 at a RESUME: a paused trial whose library changed is refused before the resumed
  invocation starts anything (control: the same resume without the change starts a server);
* SM10 the two self-comparison mutants of ``sm_mutant_entry``: each makes the control it
  targets (SM3, SM5) FAIL -- the null digest is accepted, the changed library is served.

Run this file ALONE, on a quiescent host (the real host-quiescence gate runs in every
control; see ``tests_eb1_entry``).  Outside the ``experiments/live_ab/tests_*.py`` glob.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (LIVE, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import dryrun_live_ab as dry                                            # noqa: E402
import eb1c_llama_shim as shim                                          # noqa: E402
import lab_serving_manifest as sm                                       # noqa: E402
import sm_fixture                                                       # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
from lab_common import canonical_json                                   # noqa: E402

of = entry.of
lifecycle = entry.lifecycle
MUTANT = HERE / 'sm_mutant_entry.py'


def setUpModule() -> None:
    entry.setUpModule()


def tearDownModule() -> None:
    entry.tearDownModule()


def item(label: str, server: str | None = None) -> str:
    """The drift ``item`` preflight writes for a serving-manifest label."""
    import lab_orchestrator
    text = 'serving_manifest.%s' % label if server is None \
        else 'serving_manifest.%s.%s' % (server, label)
    return lab_orchestrator._drift_label(text)


class BuildInfoTree(entry.EntryTree):
    """A tree whose golden ``/props`` and served scenario both report ``b6001-<commit>``
    while the build's ``build-info.cpp`` -- and so the manifest -- says ``b6000-<commit>``."""

    OTHER = 'b6001-%s' % sm_fixture.COMMIT[:8]

    def base_scenario(self) -> dict:
        sc = super().base_scenario()
        sc['props'] = dict(sc['props'], build_info=self.OTHER)
        return sc


class SMCase(entry.EntryCase):
    n_pairs = 1

    def refused(self, t: entry.EntryTree, **run_kw) -> dict:
        """Run the entry point; assert a refusal before seq 0 (program chain
        ``preflight_refused``, no trial chain, nothing launched, nothing left running) and
        return its body."""
        t.run(anchor=False, **run_kw)
        self.assertEqual(t.returncode, 1, t.stdout)
        self.assertEqual(t.chain(), [], 'no trial chain before seq 0')
        self.assertEqual(t.launches(), [], 'nothing was launched')
        (refusal,) = of(t.program_chain(), 'preflight_refused')
        self.assertNoOrphans(t)
        return refusal['body']

    def refusal_problems(self, t: entry.EntryTree, want_items: set[str], **run_kw) -> list:
        """What is wrong with the run if it should be a serving-manifest refusal naming
        ``want_items``: ``[]`` when it is exactly that (used by SM10 against the mutants)."""
        t.run(anchor=True, **run_kw)
        problems = []
        refusals = of(t.program_chain(), 'preflight_refused')
        if t.returncode != 1:
            problems.append('exit code %r' % (t.returncode,))
        if len(refusals) != 1:
            problems.append('%d preflight refusals' % len(refusals))
        else:
            body = refusals[0]['body']
            if body['checks_failed'] != ['serving_manifest']:
                problems.append('checks_failed %r' % (body['checks_failed'],))
            missing = want_items - {r['item'] for r in body['drift']}
            if missing:
                problems.append('drift lacks %r' % sorted(missing))
        if t.launches():
            problems.append('%d launches' % len(t.launches()))
        self.assertNoOrphans(t)
        return problems

    def rebind_config(self, t: entry.EntryTree, edit) -> None:
        """Edit the tree's FROZEN configuration and rebuild its bundle from it, so that the
        configuration and bundle digests agree and the bundle names the artifact's ACTUAL
        digest: the edit is then the only thing a check can refuse."""
        path = t.freeze / 'config.json'
        cfg = json.loads(path.read_text('utf-8'))
        edit(cfg)
        path.write_text(canonical_json(cfg) + '\n', encoding='utf-8')
        t.cfg = cfg
        bundle = dry._mock_bundle(t.freeze, cfg, t.roster)
        _obj, found, problems = sm.read_artifact(sm.artifact_path(t.freeze))
        self.assertEqual(problems, [])
        bundle['serving_manifest_sha256'] = found
        (t.freeze / 'freeze_bundle.json').write_text(canonical_json(bundle) + '\n',
                                                     encoding='utf-8')
        t.bundle_sha = entry.lab_common.freeze_bundle_sha256(bundle)
        t.write_run_config()


class SM1Positive(SMCase):

    def test_sm1_the_assembled_manifest_passes_every_check_and_the_trial_runs(self):
        t = self.tree('SM1')
        manifest, digest, problems = sm.read_artifact(sm.artifact_path(t.freeze))
        self.assertEqual(problems, [])
        self.assertEqual(t.cfg['llama_cpp']['serving_manifest_sha256'], digest)
        self.assertEqual(manifest['launcher']['path'],
                         entry.lab_common.tokenize_path(str(t.launcher)))
        self.assertEqual(len(manifest['libraries']), 2)
        self.assertEqual(t.run(), 0, t.stdout)
        self.assertEqual(of(t.program_chain(), 'preflight_refused'), [])
        self.assertEqual(lifecycle(t.chain()), [('server_started',), ('server_stopped',),
                                                ('trial_ended',)])
        (launch,) = t.launches()
        (started,) = of(t.chain(), 'server_started')
        self.assertEqual(int(started['body']['pid']), int(launch['pid']),
                         'the compiled launcher exec\'d the shim: one pid')
        self.assertNoSuccessForBadLaunch(t, {0})
        self.assertNoOrphans(t)


class SM2to6RefusedBeforeSeqZero(SMCase):

    def test_sm2_a_missing_artifact(self):
        t = self.tree('SM2')
        sm.artifact_path(t.freeze).unlink()
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['serving_manifest'])
        items = {r['item'] for r in body['drift']}
        self.assertIn(item('artifact_missing'), items)
        self.assertIn('serving_manifest_sha256', items)

    def test_sm3_a_null_configuration_digest(self):
        t = self.tree('SM3')
        self.rebind_config(t, lambda cfg: cfg['llama_cpp'].update(
            serving_manifest_sha256=None))
        self.assertEqual(self.refusal_problems(t, {item('config_digest_null')}), [])

    def test_sm4a_a_runtime_override_naming_another_path(self):
        t = self.tree('SM4a')
        fixed = sm.artifact_path(t.freeze)
        elsewhere = t.root / 'elsewhere' / 'freeze' / sm.ARTIFACT_NAME
        elsewhere.parent.mkdir(parents=True)
        shutil.move(str(fixed), str(elsewhere))
        t.runtime['serving_manifest_path'] = str(elsewhere)
        t.write_run_config()
        body = self.refused(t)
        self.assertEqual(body['checks_failed'], ['serving_manifest'])
        items = {r['item'] for r in body['drift']}
        self.assertIn(item('override:_runtime.serving_manifest_path'), items)
        self.assertIn(item('artifact_missing'), items, 'the override is never read')

    def test_sm4b_a_symlink_at_the_fixed_path(self):
        t = self.tree('SM4b')
        fixed = sm.artifact_path(t.freeze)
        elsewhere = t.root / 'elsewhere' / 'freeze' / sm.ARTIFACT_NAME
        elsewhere.parent.mkdir(parents=True)
        shutil.move(str(fixed), str(elsewhere))
        os.symlink(str(elsewhere), str(fixed))
        self.assertEqual(sm.read_artifact(elsewhere)[2], [], 'the content itself is valid')
        body = self.refused(t)
        self.assertIn(item('artifact_not_regular_file'), {r['item'] for r in body['drift']})

    def test_sm4c_a_runtime_freeze_tree_elsewhere(self):
        t = self.tree('SM4c')
        copy_dir = t.root / 'copy_of_freeze'
        shutil.copytree(str(t.freeze), str(copy_dir))
        t.runtime['freeze_dir'] = str(copy_dir)
        t.write_run_config()
        body = self.refused(t)
        self.assertIn(item('override:_runtime.freeze_dir'), {r['item'] for r in body['drift']})

    def test_sm5_one_library_byte_changed_after_assembly(self):
        t = self.tree('SM5')
        sm_fixture.flip(t.fixture.core, sm_fixture.CORE_MARKER)
        self.assertEqual(self.refusal_problems(
            t, {item('library_sha256:libeb1c-core.0.dylib', 'coder')}), [])

    def test_sm6_a_library_added_to_the_closure_at_runtime(self):
        t = self.tree('SM6')
        t.fixture.add_discoverable_library('libggml-eb1c.so')
        self.assertEqual(self.refusal_problems(
            t, {item('library_added:libggml-eb1c.so', 'coder')}), [])


class SM7ActualBuildInfo(SMCase):

    def test_sm7_the_servers_build_info_is_not_the_manifests(self):
        t = BuildInfoTree('SM7', n_pairs=1)
        self.addCleanup(t.cleanup)
        t.build()
        self.assertEqual(t.good_scenario['props']['build_info'], BuildInfoTree.OTHER)
        self.assertNotEqual(BuildInfoTree.OTHER, sm_fixture.BUILD_INFO)
        t.run()
        self.assertEqual(entry.first_start_refusal_problems(
            t, stage='serving_manifest', findings=['build_info', 'serving_manifest'],
            reason='server_identity'), [])
        (failed,) = of(t.chain(), 'server_start_failed')
        self.assertGreater(int(failed['body']['pid']), 0, 'the one check that needs the server')
        self.assertNoOrphans(t)
        # control: the same tree shape with the manifest's own string starts (SM1, C1)


def flips(t: entry.EntryTree) -> list:
    """The shim's record of every library change it made (``eb1c_llama_shim._flip``)."""
    path = t.state / shim.FLIPS_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text('utf-8').splitlines() if line.strip()]


def manifest_library_sha256(t: entry.EntryTree, name: str) -> str:
    """THE serving manifest's recorded SHA-256 of the closure member named ``name``."""
    manifest, _digest, problems = sm.read_artifact(sm.artifact_path(t.freeze))
    assert problems == [], problems
    (row,) = [r for r in manifest['libraries'] if str(r['name']).endswith('/' + name)]
    return str(row['sha256'])


class SM8Case(SMCase):
    """The SM8 scenario and its precondition (shared by SM8 and its forced interleavings)."""

    def crash_scenarios(self, t: entry.EntryTree, flip: bool, **shim_extra) -> list:
        """The first process dies on RECEIVING the pair's first call (the smoke is the first
        completion), before answering it; the restart serves the good scenario."""
        first = dict(t.good_scenario)
        first['_shim'] = {'exit_before_response': 2, 'exit_code': 9, **shim_extra}
        if flip:
            first['_shim']['flip_before_exit'] = {
                'path': str(t.fixture.core), 'marker': sm_fixture.CORE_MARKER.decode()}
        return [first, t.good_scenario]

    def assertFlipPrecedesTheRestart(self, t: entry.EntryTree) -> dict:
        """The precondition of SM8, checked BEFORE its verdict: the shim changed the library
        exactly once, from the manifest's bytes, the change is still on disk, and it was made
        before the ``server_down`` whose restart must refuse it; that ``server_down`` had an
        arrival in flight, so the restart could not be skipped.  Returns the flip record."""
        rows = flips(t)
        self.assertEqual(len(rows), 1, 'exactly one library change: %r' % (rows,))
        (row,) = rows
        self.assertIs(row['marker_found'], True)
        self.assertEqual(row['sha256_before'],
                         manifest_library_sha256(t, 'libeb1c-core.0.dylib'),
                         'the change starts from the manifest\'s bytes')
        self.assertNotEqual(row['sha256_after'], row['sha256_before'])
        self.assertEqual(entry.sha256_file(t.fixture.core), row['sha256_after'],
                         'the changed library is what the restart found on disk')
        downs = of(t.chain(), 'server_down')
        self.assertEqual(len(downs), 1, 'the crash was observed as a server_down: %r'
                         % (lifecycle(t.chain()),))
        self.assertTrue(downs[0]['body']['inflight'],
                        'an arrival waited on the server: the restart was required')
        self.assertLess(int(row['t_mono_ns']), int(downs[0]['t_mono_ns']),
                        'the change precedes the server_down (one monotonic clock)')
        return row


class SM8AtTheRestart(SM8Case):

    def test_sm8_a_library_changed_before_the_restart_refuses_it(self):
        t = self.tree('SM8')
        t.set_scenarios(self.crash_scenarios(t, flip=True))
        t.run()
        self.assertFlipPrecedesTheRestart(t)
        self.assertEqual(t.returncode, 1, t.stdout)
        self.assertEqual(lifecycle(t.chain()), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_start_failed', 'restart', 'serving_manifest', ('serving_manifest',)),
            ('trial_aborted', 'server_identity')])
        (failed,) = of(t.chain(), 'server_start_failed')
        self.assertEqual((failed['body']['pid'], failed['body']['restart_index']), (0, 1))
        self.assertEqual(len(t.launches()), 1, 'the restart launched nothing')
        self.assertNoOrphans(t)

    def test_control_the_same_crash_without_the_change_restarts(self):
        t = self.tree('SM8c')
        t.set_scenarios(self.crash_scenarios(t, flip=False))
        t.run()
        self.assertEqual(flips(t), [], 'the control changes no library')
        (down,) = of(t.chain(), 'server_down')
        self.assertTrue(down['body']['inflight'], 'the same required restart')
        self.assertIn(('server_restarted',), lifecycle(t.chain()))
        self.assertEqual(of(t.chain(), 'server_start_failed'), [])
        self.assertEqual(len(t.launches()), 2)
        self.assertNoOrphans(t)


class SM8ForcedInterleaving(SM8Case):
    """The interleaving of the SM8 red, FORCED by the shim (``hold_until_*``): both calls of
    the only pair reach the first process before it flips and exits.

    * the PRE-FIX scenario (``exit_after_responses: 2``: answered, then died) held until both
      responses are written: nothing needs the server any more, the horizon closes the trial
      before a health poll, the exit is seen only by the closing stop (``server_stopped``
      with return code 9) and no restart runs -- exit 0 although the library changed.  This
      is the diagnosed red made deterministic; it is the mutation the fixed scenario is
      measured against;
    * the FIXED scenario (``exit_before_response: 2``) held until both requests are
      received: neither is answered, both arrivals wait on the server, the restart is
      required and refuses the changed library -- exit 1."""

    def test_the_pre_fix_scenario_forced_never_reaches_the_restart_check(self):
        t = self.tree('SM8fx')
        first = dict(t.good_scenario)
        first['_shim'] = {'exit_after_responses': 2, 'exit_code': 9, 'hold_until_written': 3,
                          'flip_before_exit': {'path': str(t.fixture.core),
                                               'marker': sm_fixture.CORE_MARKER.decode()}}
        t.set_scenarios([first, t.good_scenario])
        t.run()
        (row,) = flips(t)
        self.assertEqual(entry.sha256_file(t.fixture.core), row['sha256_after'])
        self.assertNotEqual(row['sha256_after'],
                            manifest_library_sha256(t, 'libeb1c-core.0.dylib'),
                            'the library DID change')
        self.assertEqual(t.returncode, 0, 'the red: ' + t.stdout)
        self.assertEqual(lifecycle(t.chain()), [('server_started',), ('server_stopped',),
                                                ('trial_ended',)])
        (stopped,) = of(t.chain(), 'server_stopped')
        self.assertEqual(stopped['body']['returncode'], 9,
                         'the exit was seen only by the closing stop')
        self.assertEqual(sorted(e['body']['arrival'] for e in of(t.chain(), 'llm_response')),
                         [1, 2], 'both calls answered by the first process')
        self.assertEqual(of(t.chain(), 'llm_error'), [], 'no call waited on the server')
        self.assertEqual(len(t.launches()), 1, 'no restart ran')
        self.assertNoOrphans(t)

    def test_the_fixed_scenario_forced_refuses_the_restart(self):
        t = self.tree('SM8fy')
        t.set_scenarios(self.crash_scenarios(t, flip=True, hold_until_received=3))
        t.run()
        self.assertFlipPrecedesTheRestart(t)
        (down,) = of(t.chain(), 'server_down')
        self.assertEqual(sorted(r['arrival'] for r in down['body']['inflight']), [1, 2],
                         'both calls reached the first process and neither was answered')
        self.assertEqual(t.returncode, 1, t.stdout)
        self.assertEqual(lifecycle(t.chain()), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_start_failed', 'restart', 'serving_manifest', ('serving_manifest',)),
            ('trial_aborted', 'server_identity')])
        self.assertEqual(len(t.launches()), 1, 'the restart launched nothing')
        self.assertNoOrphans(t)


class SM9AtTheResume(SMCase):

    n_pairs = 3

    def paused(self, name: str, *, then_good: bool) -> entry.EntryTree:
        t = self.tree(name)
        never = t.scenario()
        never['_shim'] = {'never_listen': True}
        scenarios = entry.crash_first(t, never)
        if then_good:
            scenarios.append(t.good_scenario)
        t.set_scenarios(scenarios)
        self.assertEqual(t.run(), 2, t.stdout)
        self.assertEqual(lifecycle(t.chain())[-1], ('trial_paused', 'server_unrecoverable'))
        base = t.argv
        t.argv = lambda: base() + ['--resume']
        return t

    def test_sm9_a_library_changed_while_paused_refuses_the_resume(self):
        t = self.paused('SM9', then_good=True)
        chain_before = entry.types(t.chain())
        sm_fixture.flip(t.fixture.core, sm_fixture.CORE_MARKER)
        t.run()
        self.assertEqual(t.returncode, 1, t.stdout)
        (refusal,) = of(t.program_chain(), 'preflight_refused')
        self.assertEqual(refusal['body']['checks_failed'], ['serving_manifest'])
        self.assertIn(item('library_sha256:libeb1c-core.0.dylib', 'coder'),
                      {r['item'] for r in refusal['body']['drift']})
        self.assertEqual(entry.types(t.chain()), chain_before, 'the trial chain is untouched')
        self.assertEqual(len(t.launches()), 2, 'the resume launched nothing')
        self.assertNoOrphans(t)

    def test_control_the_same_resume_without_the_change_starts_a_server(self):
        t = self.paused('SM9c', then_good=True)
        t.run()
        self.assertEqual(of(t.program_chain(), 'preflight_refused'), [])
        events = t.chain()
        paused_at = max(i for i, e in enumerate(events) if e['type'] == 'trial_paused')
        self.assertTrue(of(events[paused_at:], 'server_started'),
                        'the resumed invocation passed preflight and started a server')
        self.assertEqual(len(t.launches()), 3)
        self.assertNoOrphans(t)


class SM10SelfComparisonMutants(SMCase):
    """Each mutant of ``sm_mutant_entry`` turns one comparison into a self-comparison; the
    control it targets must then FAIL (the refusal disappears), which is what shows the
    control observes the comparison and not something else."""

    def test_mutant_digest_self_accepts_the_null_digest_of_sm3(self):
        t = self.tree('SM10a')
        self.rebind_config(t, lambda cfg: cfg['llama_cpp'].update(
            serving_manifest_sha256=None))
        problems = self.refusal_problems(t, {item('config_digest_null')}, entry=MUTANT,
                                         entry_args=('--mutation', 'digest_self'))
        self.assertNotEqual(problems, [], 'SM3 did not detect the digest self-comparison')
        self.assertEqual(of(t.program_chain(), 'preflight_refused'), [])
        self.assertEqual(t.returncode, 0, t.stdout)

    def test_mutant_facts_self_serves_the_changed_library_of_sm5(self):
        t = self.tree('SM10b')
        # re-signed, so the changed library is loadable -- what the mutant then serves
        sm_fixture.flip(t.fixture.core, sm_fixture.CORE_MARKER, resign=True)
        problems = self.refusal_problems(
            t, {item('library_sha256:libeb1c-core.0.dylib', 'coder')}, entry=MUTANT,
            entry_args=('--mutation', 'facts_self'))
        self.assertNotEqual(problems, [], 'SM5 did not detect the facts self-comparison')
        self.assertEqual(t.returncode, 0, t.stdout)
        self.assertEqual(lifecycle(t.chain()), [('server_started',), ('server_stopped',),
                                                ('trial_ended',)])
        self.assertEqual(len(t.launches()), 1, 'the changed library was loaded and served')


if __name__ == '__main__':
    unittest.main()
