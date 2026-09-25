"""Controls of root's 07:10 ruling: a predecision abort is incomplete, never a reportable ``none``.

``reviews/predecision_abort_reporting_ruling_20260925_0710.md`` (root, origin/main 9790043), choice
(b), on finding 9 of the final verification of 8f0b4ae (disclosed at 2113dbd): "a trial aborted
before any decision by a non-cap cause, with no crossing, is incomplete and not reportable as a
scientific no-decision/abstention result"; "For no logged decision, a non-cap ``trial_aborted`` is
an incomplete, nonreportable result **whether or not a crossing was logged after the abort
point**, with the concrete abort reason and any not-acted-on crossing retained separately. Keep
the existing cap-specific label. A genuinely reportable ``none`` requires a verifier-valid normal
terminal at the frozen full horizon with no eligible crossing; an open or incomplete chain must not
masquerade as that outcome. A decision validly logged before a later abort retains its existing
receipt/provisional and truncated-follow-up rules. Control both no-crossing and post-point-crossing
aborts through ``decision.json`` **and the complete program summary**, as well as a normal
full-horizon no-crossing case and a valid pre-abort decision. A mutation must fail the control if
it restores reportable ``none`` on an incomplete path."  And: "Include the effective cap value and
its config binding in the immutable result/provenance output".

Every control runs the COMPLETE results path (``build_live_ab_results.build`` over a chain on disk:
the returned summary row, the WRITTEN ``program_summary.json`` and ``decision.json``) and reads the
verifier's rows of the same chain.  :func:`masquerades` is the audit predicate, computed from the
chain and the frozen configuration WITHOUT the builder's own reading (:func:`independent_end`):
an incomplete chain with no decision reported, or labelled ``none``; the terminal abort reason not
kept beside the result; a crossing the verifier reads NOT ACTED ON not kept beside it; the
effective cap or its binding absent or not the configuration's.

* Production chains (``run_trial`` in process on the D3 tree -- 50 pairs, mock delta 0.9, n_min
  25; the harness of ``tests_eb1_supervision``): ``refused_early`` and ``identity_early`` (the
  server dies while pair 5 is in flight and its restart is refused / fails its ``identity`` stage:
  a non-cap abort at n <= 5 < n_min, no crossing possible); ``refused_at_crossing`` (the same
  refusal while pair 44, the D3 crossing pair, is in flight: the drain's crossing is not acted
  on); ``cap_early`` (the fourth down at pair 10: case (a), the cap's own label);
  ``full_horizon_null`` (both arms alike: the band never crosses, the frozen rule logs
  ``horizon_no_decision`` at n = 50 = N_P, ``trial_ended``); ``ended_short`` (the same arms, run
  with the runtime ``max_pairs`` 30: ``trial_ended`` short of the frozen horizon, no decision);
  ``post_decision_refused`` and ``cap_after_decision`` (a receipted ``deploy_candidate`` at n =
  44, then a refused restart / the fourth down in the follow-up cohort).
* Variants written by the production chain writer (``lab_eventlog.EventLog``, same bodies, fresh
  envelopes): ``open_prefix`` (the full-horizon chain up to its look at n = 30: open, no
  terminal record) and ``open_at_horizon`` (the same chain up to its horizon look, before the
  decision: the frozen rule's horizon action is then a crossing no decision acted on).
* MUTATION: the builder of :data:`PRE_FIX` (9f0aff6, the builder before this repair, loaded from
  ``git show``) over the same trees publishes ``none``, reportable, for the four incomplete chains
  and :func:`masquerades` flags exactly those; the current ``decision_object`` recompiled with its
  two new branches removed (:func:`mutated_decision_object`, which refuses unless each text occurs
  once) restores the reportable ``none`` and is flagged; with only the abort branch removed the
  abort is no longer labelled an abort.

The frozen rule decides ``horizon_no_decision`` at the horizon look (``lab_monitor.decide``,
protocol 8.4), so a normal full-horizon trial with no crossing is reported as that logged result;
``open_at_horizon`` shows that a chain at the full horizon WITHOUT it is ``LIVE_DECISION_INVALID``
(``missed``), not ``none``.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off (protocol
14.7).
"""
from __future__ import annotations

import __future__
import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_live_ab_results as builder                                 # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_verify_log                                                   # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
import tests_guard_controls as guard                                    # noqa: E402
import tests_invalid_decision_summary as summ                           # noqa: E402
from lab_common import sha256_canonical, sha256_file                    # noqa: E402

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule

#: The builder before this repair (the last commit that changed it; unchanged at f54d215).
PRE_FIX = '9f0aff6ded9dc0d55fcb63345811e637389a735a'
#: the labels, as root's 07:10 ruling and protocol 16 item 18 state them (checked against the
#: builder's constants by :meth:`LabelTests`; the controls compare with these literals, so they
#: can run against a builder that lacks the constants)
PREDECISION = ('incomplete: aborted before any decision (no decision; not a null result, not an '
               'abstention)')
INCOMPLETE = ('incomplete: no decision and no normal end at the frozen full horizon (no decision; '
              'not a null result, not an abstention)')
ABORT_CROSSING = builder.ABORT_INCOMPLETE_LABEL
CAP_LABEL = builder.RESTART_CAP_INCOMPLETE_LABEL
INVALID = 'LIVE_DECISION_INVALID (harness defect)'
CAP = 3
PAIRS = 50
EARLY = 5                 # pair in flight when the server dies: n <= 5 < n_min = 25
CROSS_N = summ.CROSS_N    # the D3 tree deploys at n = 44
SHORT = 30                # the runtime max_pairs of ``ended_short``
NULL_SCENARIO = {'outcome_seed': 424242,
                 'incumbent': {'p_good': 1.0, 'latency_scale': 1.0},
                 'candidate': {'p_good': 1.0, 'latency_scale': 1.0}}
PRODUCTION = ('refused_early', 'identity_early', 'refused_at_crossing', 'cap_early',
              'full_horizon_null', 'ended_short', 'post_decision_refused', 'cap_after_decision')
VARIANTS = ('open_prefix', 'open_at_horizon')
#: the four the pre-fix builder published as ``none``, reportable (finding 9 and its kin)
PRE_FIX_NONE = ('refused_early', 'identity_early', 'ended_short', 'open_prefix')


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def terminal(events):
    return next((e for e in reversed(events) if e['type'] in ('trial_ended', 'trial_aborted')),
                None)


def independent_end(events, cfg) -> bool:
    """The auditor's own reading of "a normal end at the frozen full horizon" (root 07:10), from
    the chain and the frozen configuration, not through the builder: ``trial_ended`` with a
    passing resolution, no no-decision point (``lab_eventlog.no_decision_point``, the function
    all three paths share), the configuration's horizon (``monitor.n_max`` or ``roster.n_pairs``)
    equal to the chain's ``n_pairs_max``, that many pairs enrolled, the last look at it, all
    collapsed."""
    term = terminal(events)
    if term is None or term['type'] != 'trial_ended':
        return False
    if (term['body'].get('resolution') or {}).get('verdict') != 'PASS':
        return False
    if lab_eventlog.no_decision_point(events, lab_common.server_supervision_cap(cfg)) is not None:
        return False
    horizon = cfg['monitor'].get('n_max') or cfg['roster']['n_pairs']
    started = of(events, 'trial_started')[0]['body']
    looks = of(events, 'monitor_update')
    pairs = {e['body']['pair'] for e in of(events, 'pair_enrolled')
             if not e['body'].get('re_enrolled')}
    return (started['n_pairs_max'] == horizon and len(pairs) == horizon and bool(looks)
            and looks[-1]['body']['n'] == horizon
            and looks[-1]['body']['n_collapsed'] == horizon)


def masquerades(row: dict, dobj: dict, events, cfg, cfg_sha: str, not_acted_on: bool) -> list:
    """The audit predicate: every way the summary row ``row`` or ``decision.json`` ``dobj`` lets
    an incomplete chain pass as a result, or drops what root 07:10 asks to keep beside it."""
    out = []
    logged = bool(of(events, 'decision'))
    if not logged and not independent_end(events, cfg):
        if row['reportable'] or dobj['reportable']:
            out.append('incomplete_chain_reported')
        if 'none' in (row['decision'], dobj['primary_result']):
            out.append('incomplete_chain_labelled_none')
    term = terminal(events)
    want_reason = term['body'].get('reason') if term and term['type'] == 'trial_aborted' else None
    if row.get('abort_reason', 'absent') != want_reason:
        out.append('abort_reason_not_kept_beside_the_result')
    if not_acted_on and not row.get('crossing_not_acted_on'):
        out.append('crossing_not_acted_on_not_kept')
    value = lab_common.server_supervision_cap(cfg)
    if row.get('restart_cap_value', 'absent') != value \
            or (dobj.get('restart_cap') or {}).get('cap_value', 'absent') != value:
        out.append('cap_value_absent')
    binding = (dobj.get('restart_cap') or {}).get('binding') or {}
    if binding.get('server_supervision') != cfg['server_supervision'] \
            or binding.get('server_supervision_sha256') != sha256_canonical(
                cfg['server_supervision']) \
            or binding.get('config_sha256') != cfg_sha \
            or binding.get('config_path') != 'freeze/config.json':
        out.append('cap_binding_absent')
    return out


def load_builder_at(rev: str):
    """The builder blob of ``rev`` loaded as a module (only the builder differs), or None
    without git history."""
    blob = subprocess.run(['git', '-C', str(REPO), 'show',
                           '%s:experiments/live_ab/build_live_ab_results.py' % rev],
                          capture_output=True, check=False)
    if blob.returncode != 0:
        return None
    tmp = Path(tempfile.mkdtemp(prefix='builder_%s_' % rev[:7]))
    path = tmp / ('build_live_ab_results_%s.py' % rev[:7])
    path.write_bytes(blob.stdout)
    spec = importlib.util.spec_from_file_location('build_live_ab_results_%s' % rev[:7], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)                              # type: ignore[union-attr]
    shutil.rmtree(tmp, ignore_errors=True)
    return module


def run_production(name: str, tree) -> str:
    fake = sup.FakeServers()
    hook, scenario, rt = None, None, {}
    if name in ('refused_early', 'refused_at_crossing', 'post_decision_refused'):
        fake.restart_raises = lab_common.PreflightError
    if name == 'identity_early':
        fake.script = [None, 'identity']
    if name in ('refused_early', 'identity_early'):
        hook = sup.CrashPlan(fake, pairs=(EARLY,))
    elif name == 'refused_at_crossing':
        hook = sup.CrashPlan(fake, pairs=(CROSS_N,))
    elif name == 'cap_early':
        hook = sup.CrashPlan(fake, pairs=(1, 2, 3, 2 * EARLY))
    elif name == 'post_decision_refused':
        hook = sup.CrashPlan(fake, post=1)
    elif name == 'cap_after_decision':
        hook = sup.CrashPlan(fake, pairs=(1, 2, 3), post=1)
    if name in ('full_horizon_null', 'ended_short'):
        scenario = NULL_SCENARIO
    if name == 'ended_short':
        rt['max_pairs'] = SHORT
    return sup.run(tree, fake, hook=hook, scenario=scenario, **rt)


def build_with(module, run: dict, out_name: str) -> dict:
    """The complete results path of ``module`` over ``run``'s chain: returned and written summary
    rows, the written summary, ``decision.json``."""
    tree = run['tree']
    out = tree.root / ('%s_%d' % (out_name, time.monotonic_ns()))
    returned = module.build([tree.trial], tree.bundle_sha, results_root=run['results'],
                            work_root=tree.work, out_dir=out, mock=True)
    written = json.loads((out / 'program_summary.json').read_text('utf-8'))
    return {'returned': returned['trials'][tree.trial], 'written': written['trials'][tree.trial],
            'summary': written,
            'decision': json.loads((out / tree.trial / 'decision.json').read_text('utf-8'))}


def verifier(run: dict):
    tree = run['tree']
    report = lab_verify_log.verify_trial(tree.trial, tree.bundle_sha, mode='full',
                                         results_root=run['results'], work_root=tree.work)
    return report


#: the two branches root 07:10 adds to ``decision_object``, as the source carries them
ABORT_BRANCH = "    elif logged is None and end['terminal'] == 'trial_aborted':\n"
INCOMPLETE_BRANCH = "    elif logged is None and not end['normal_end_at_full_horizon']:\n"


def mutated_decision_object(*branches: str):
    """MUTATION: ``decision_object`` recompiled from its own source with each of ``branches``
    made unreachable (``elif False:``), bound to the builder's live globals -- the method of
    :func:`tests_guard_controls.mutant`, with every edit applied to one source text (a second
    ``mutant`` would re-read the unedited file).  Refuses
    (:class:`tests_guard_controls.MutationNotApplicable`) unless each text occurs exactly once."""
    fn = builder.decision_object
    src = inspect.getsource(fn)
    for text in branches:
        if src.count(text) != 1:
            raise guard.MutationNotApplicable('mutation text found %d times in %s: %r'
                                              % (src.count(text), fn.__qualname__, text[:70]))
        src = src.replace(text, '    elif False:\n')
    code = compile(textwrap.dedent(src), inspect.getsourcefile(fn), 'exec',
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    scratch: dict = {}
    exec(code, dict(fn.__globals__), scratch)                          # noqa: S102
    made = scratch[fn.__name__]
    out = types.FunctionType(made.__code__, fn.__globals__, fn.__name__, made.__defaults__,
                             made.__closure__)
    out.__kwdefaults__ = made.__kwdefaults__
    return out


class LabelTests(unittest.TestCase):
    def test_the_builder_carries_the_labels_the_ruling_and_protocol_state(self):
        self.assertEqual(builder.PREDECISION_ABORT_LABEL, PREDECISION)
        self.assertEqual(builder.INCOMPLETE_CHAIN_LABEL, INCOMPLETE)
        # the cap's own label and the crossing label are kept, unchanged
        self.assertEqual(CAP_LABEL, 'incomplete: restart cap before any decision (no decision; '
                                    'not a null result, not an abstention)')
        self.assertTrue(ABORT_CROSSING.startswith('incomplete: aborted before any decision; a '
                                                  'crossing logged after the abort point'))


class PredecisionAbortControls(unittest.TestCase):
    """Eight production runs and two written variants, each built by the current builder, by the
    builder of :data:`PRE_FIX` and by two mutants of ``decision_object``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees: list = []
        cls.runs: dict = {}
        for name in PRODUCTION:
            tree = cap.d3_tree(PAIRS)
            cls.trees.append(tree)
            status = run_production(name, tree)
            cls.runs[name] = {'status': status, 'tree': tree, 'results': tree.results,
                              'events': tree.events()}
        base = cls.runs['full_horizon_null']
        events = base['events']
        at30 = next(i for i, e in enumerate(events) if e['type'] == 'monitor_update'
                    and e['body']['n'] == SHORT and e['body']['n_collapsed'] == SHORT)
        (decision,) = of(events, 'decision')
        cut = next(i for i, e in enumerate(events) if e['seq'] == decision['seq'])
        for name, part in (('open_prefix', events[:at30 + 1]), ('open_at_horizon', events[:cut])):
            results = summ.write_variant(base['tree'], part, name)
            cls.runs[name] = {'status': None, 'tree': base['tree'], 'results': results,
                              'events': list(lab_eventlog.read_chain(
                                  results / base['tree'].trial / 'events', base['tree'].trial,
                                  base['tree'].bundle_sha).events)}
        cls.pre_fix = load_builder_at(PRE_FIX)
        cls.mutants = {}
        for key, branches in (('both_branches_removed', (ABORT_BRANCH, INCOMPLETE_BRANCH)),
                              ('abort_branch_removed', (ABORT_BRANCH,))):
            try:
                cls.mutants[key] = mutated_decision_object(*branches)
            except guard.MutationNotApplicable as exc:
                cls.mutants[key] = exc
        for name, run in cls.runs.items():
            tree = run['tree']
            run['cfg'] = json.loads((run['results'] / 'freeze' / 'config.json').read_text('utf-8'))
            run['cfg_sha'] = sha256_file(run['results'] / 'freeze' / 'config.json')
            run['digest_before'] = summ.chain_digest(run['results'], tree.trial)
            report = verifier(run)
            run['fails'] = [(f.check, dict(f.detail)) for f in report.findings
                            if f.severity == 'FAIL']
            run['agreement'] = [(f.severity, dict(f.detail)) for f in report.findings
                                if f.check == 'reference_rule.agreement']
            run['not_acted_on'] = any(d.get('consequence', '').startswith('NOT_ACTED_ON')
                                      for _s, d in run['agreement'])
            run['built'] = build_with(builder, run, 'built')
            run['pre_fix'] = (None if cls.pre_fix is None
                              else build_with(cls.pre_fix, run, 'pre_fix'))
            for key, fn in cls.mutants.items():
                if isinstance(fn, Exception):
                    run[key] = fn
                    continue
                with mock.patch.object(builder, 'decision_object', fn):
                    run[key] = build_with(builder, run, key)
            run['digest_after'] = summ.chain_digest(run['results'], tree.trial)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    # ----------------------------------------------------------------- helpers
    def rows(self, name: str, which: str = 'built') -> tuple:
        got = self.runs[name][which]
        if isinstance(got, Exception):
            raise got
        return got['returned'], got['written'], got['decision']

    def flags(self, name: str, which: str = 'built') -> list:
        run = self.runs[name]
        returned, written, dobj = self.rows(name, which)
        return sorted(set(masquerades(returned, dobj, run['events'], run['cfg'], run['cfg_sha'],
                                      run['not_acted_on'])
                          + masquerades(written, dobj, run['events'], run['cfg'],
                                        run['cfg_sha'], run['not_acted_on'])))

    def assertResult(self, name: str, decision: str, reportable: bool, logged: str | None,
                     abort_reason: str | None) -> dict:
        returned, written, dobj = self.rows(name)
        for row in (returned, written):
            self.assertEqual((row['decision'], row['reportable'], row.get('logged_decision'),
                              row['abort_reason']),
                             (decision, reportable, logged, abort_reason))
        self.assertEqual((dobj['primary_result'], dobj['reportable'],
                          dobj['normal_end']['abort_reason']), (decision, reportable, abort_reason))
        self.assertEqual(self.flags(name), [])
        self.assertEqual(summ.contradictions(returned, dobj), [])
        self.assertEqual(summ.contradictions(written, dobj), [])
        return dobj

    def no_crossing(self, events) -> bool:
        return all(e['body']['shadow']['action'] == 'none' for e in of(events, 'monitor_update'))

    # ----------------------------------------------------------------- root 07:10 (b)
    def test_a_non_cap_predecision_abort_without_a_crossing_is_incomplete(self):
        """Finding 9: the chain aborts (a refused restart; a restart failing its identity stage)
        while pair 5 is in flight -- no look can cross below n_min -- and its result is the
        predecision-abort label, not reportable, with the concrete reason kept beside it in
        ``decision.json`` and in both summary rows; the logged decision (none) beside it."""
        for name in ('refused_early', 'identity_early'):
            with self.subTest(run=name):
                run = self.runs[name]
                events = run['events']
                self.assertEqual(run['status'], 'aborted')
                self.assertEqual(of(events, 'decision'), [])
                self.assertTrue(self.no_crossing(events))
                reason = terminal(events)['body']['reason']
                self.assertNotEqual(reason, 'server_restart_cap')
                self.assertTrue(of(events, 'abort_owed'), 'the abort wrote its point')
                dobj = self.assertResult(name, PREDECISION, False, 'none', reason)
                self.assertTrue(dobj['decision_label'].startswith(
                    'not reportable: trial_aborted(%s) at seq %d before any decision'
                    % (reason, terminal(events)['seq'])), dobj['decision_label'])
                self.assertIsNone(dobj['crossing_not_acted_on'])
                self.assertEqual(dobj['restart_cap']['case'], 'none')
                returned, written, _ = self.rows(name)
                for row in (returned, written):
                    self.assertIn('trial_aborted', row['incomplete_reasons'])
                    self.assertNotIn('crossing_not_acted_on', row)
                self.assertEqual(run['agreement'], [])
        self.assertEqual(terminal(self.runs['refused_early']['events'])['body']['reason'],
                         'harness_defect')

    def test_a_non_cap_abort_with_a_crossing_after_its_point_is_incomplete_crossing_kept(self):
        """The same refusal while pair 44 is in flight: the drain's look crosses and is not acted
        on.  Incomplete, not reportable (the v3 label for this case); the abort reason AND the
        crossing are kept beside the result, separately, in ``decision.json`` and both rows."""
        run = self.runs['refused_at_crossing']
        events = run['events']
        self.assertEqual(run['status'], 'aborted')
        self.assertEqual(of(events, 'decision'), [])
        (owed,) = of(events, 'abort_owed')
        look = summ.crossing(events)
        self.assertGreater(look['seq'], owed['seq'])
        dobj = self.assertResult('refused_at_crossing', ABORT_CROSSING, False, 'none',
                                 'harness_defect')
        self.assertEqual((dobj['crossing_not_acted_on']['n'],
                          dobj['crossing_not_acted_on']['seq'],
                          dobj['crossing_not_acted_on']['abort_reason']),
                         (CROSS_N, look['seq'], 'harness_defect'))
        returned, written, _ = self.rows('refused_at_crossing')
        for row in (returned, written):
            self.assertEqual((row['crossing_not_acted_on']['kind'],
                              row['crossing_not_acted_on']['n'],
                              row['crossing_not_acted_on']['seq'],
                              row['crossing_not_acted_on']['no_decision_seq']),
                             ('deploy_candidate', CROSS_N, look['seq'], owed['seq']))
        self.assertEqual([(s, d['consequence']) for s, d in run['agreement']],
                         [('INFO', 'NOT_ACTED_ON_abort_before_decision')])
        self.assertEqual(run['fails'], [])

    def test_the_cap_before_any_decision_keeps_its_own_label(self):
        run = self.runs['cap_early']
        self.assertEqual(run['status'], 'aborted')
        self.assertEqual(of(run['events'], 'decision'), [])
        self.assertTrue(self.no_crossing(run['events']))
        dobj = self.assertResult('cap_early', CAP_LABEL, False, 'none', 'server_restart_cap')
        self.assertEqual(dobj['restart_cap']['case'], 'before_decision')
        self.assertEqual(run['fails'], [])

    def test_an_ended_trial_short_of_the_frozen_horizon_is_incomplete(self):
        """The runtime ``max_pairs`` ends enrollment at 30 of N_P = 50: ``trial_ended`` with no
        decision (decide() finds no horizon at n = 30).  Not a normal end at the frozen full
        horizon, so not reportable."""
        run = self.runs['ended_short']
        events = run['events']
        self.assertEqual(run['status'], 'ended')
        self.assertEqual(of(events, 'decision'), [])
        self.assertTrue(self.no_crossing(events))
        self.assertEqual(of(events, 'trial_started')[0]['body']['n_pairs_max'], PAIRS)
        dobj = self.assertResult('ended_short', INCOMPLETE, False, 'none', None)
        self.assertEqual(dobj['normal_end']['reasons'],
                         ['enrolment_short_of_horizon', 'last_look_short_of_horizon'])
        self.assertEqual((dobj['normal_end']['pairs_enrolled'], dobj['normal_end']['horizon']),
                         (SHORT, PAIRS))
        self.assertTrue(dobj['decision_label'].startswith(
            'not reportable: no decision, and not a normal end at the frozen full horizon'))

    def test_an_open_chain_is_incomplete(self):
        run = self.runs['open_prefix']
        self.assertIsNone(terminal(run['events']))
        self.assertEqual(of(run['events'], 'decision'), [])
        dobj = self.assertResult('open_prefix', INCOMPLETE, False, 'none', None)
        self.assertEqual(dobj['normal_end']['reasons'][0], 'no_terminal_record')
        self.assertEqual(self.rows('open_prefix')[1]['status'], 'open')

    # ----------------------------------------------------------------- negative controls
    def test_control_a_normal_full_horizon_no_crossing_trial_is_reportable(self):
        """Both arms alike: no look crosses before N_P; the frozen rule logs its horizon result
        at n = 50, receipted, and the trial ends.  A normal end at the frozen full horizon: the
        logged result is reportable, unchanged by the repair."""
        run = self.runs['full_horizon_null']
        events = run['events']
        self.assertEqual(run['status'], 'ended')
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('horizon_no_decision', PAIRS))
        self.assertTrue(all(e['body']['shadow']['action'] in ('none', 'horizon_no_decision')
                            for e in of(events, 'monitor_update')))
        self.assertTrue(independent_end(events, run['cfg']))
        dobj = self.assertResult('full_horizon_null', 'horizon_no_decision', True, None, None)
        self.assertEqual((dobj['normal_end']['normal_end_at_full_horizon'],
                          dobj['normal_end']['reasons'], dobj['decision_status']),
                         (True, [], 'receipted'))
        self.assertIsNone(dobj['decision_label'])
        self.assertEqual(run['fails'], [])
        if self.pre_fix is not None:
            got = self.rows('full_horizon_null', 'pre_fix')
            self.assertEqual((got[0]['decision'], got[0]['reportable'], got[2]['primary_result']),
                             ('horizon_no_decision', True, 'horizon_no_decision'))

    def test_each_condition_of_a_normal_end_refuses_on_its_own(self):
        """``normal_end_reading`` on the full-horizon chain (every condition holds; its own
        anchor and receipt follow the terminal record) and on in-memory edits of it that each
        break ONE condition: exactly that reason, and no normal end.  (Past the INVALID
        precedence a chain with no decision at the horizon never reaches the reportable branch,
        so these conditions are observed here, on the pure function.)"""
        run = self.runs['full_horizon_null']
        events, cfg = run['events'], run['cfg']
        base = builder.normal_end_reading(events, cfg, None)
        self.assertEqual((base['normal_end_at_full_horizon'], base['reasons'],
                          base['terminal'], base['resolution_verdict'], base['horizon'],
                          base['chain_n_pairs_max'], base['pairs_enrolled']),
                         (True, [], 'trial_ended', 'PASS', PAIRS, PAIRS, PAIRS))
        term = terminal(events)
        after = sorted({e['type'] for e in events if e['seq'] > term['seq']})
        self.assertEqual(after, ['anchor', 'anchor_receipt'])

        def edited(fn):
            evs = json.loads(json.dumps(events))
            fn(evs)
            return evs

        def last_look(evs):
            return [e for e in evs if e['type'] == 'monitor_update'][-1]
        pair_seqs = [e['seq'] for e in events if e['type'] == 'pair_enrolled']
        cases = {
            'trial_not_started': (lambda evs: evs.remove(of(evs, 'trial_started')[0]), cfg, None,
                                  ['trial_not_started', 'horizon_not_the_chain_horizon']),
            'no_terminal_record': (lambda evs: evs.remove(terminal(evs)), cfg, None,
                                   ['no_terminal_record']),
            'trial_aborted': (lambda evs: terminal(evs).__setitem__('type', 'trial_aborted'),
                              cfg, None, ['trial_aborted']),
            'events_after_terminal_record': (
                lambda evs: evs.append(dict(last_look(evs), seq=evs[-1]['seq'] + 1)), cfg, None,
                ['events_after_terminal_record']),
            'resolution_absent': (lambda evs: terminal(evs)['body'].pop('resolution'), cfg,
                                  None, ['resolution_absent']),
            'resolution_not_pass': (lambda evs: terminal(evs)['body']['resolution'].__setitem__(
                'verdict', 'FAIL'), cfg, None, ['resolution_not_pass']),
            'no_decision_point_in_chain': (lambda evs: None, cfg,
                                           {'seq': 7, 'reason': 'abort_owed'},
                                           ['no_decision_point_in_chain']),
            'horizon_unknown': (lambda evs: None, dict(cfg, roster={}, monitor=dict(
                cfg['monitor'], n_max=None)), None,
                                ['horizon_unknown', 'enrolment_short_of_horizon',
                                 'last_look_short_of_horizon']),
            'horizon_not_the_chain_horizon': (
                lambda evs: of(evs, 'trial_started')[0]['body'].__setitem__('n_pairs_max', 60),
                cfg, None, ['horizon_not_the_chain_horizon']),
            'enrolment_short_of_horizon': (
                lambda evs: evs.remove(next(e for e in evs if e['seq'] == pair_seqs[-1])), cfg,
                None, ['enrolment_short_of_horizon']),
            'no_look': (lambda evs: [evs.remove(e) for e in of(evs, 'monitor_update')], cfg,
                        None, ['no_look']),
            'last_look_short_of_horizon': (
                lambda evs: last_look(evs)['body'].update(n=PAIRS - 1, n_collapsed=PAIRS - 1),
                cfg, None, ['last_look_short_of_horizon']),
            'last_look_not_all_collapsed': (
                lambda evs: last_look(evs)['body'].__setitem__('n_collapsed', PAIRS - 1), cfg,
                None, ['last_look_not_all_collapsed']),
        }
        self.assertEqual(sorted(cases), sorted(builder.NOT_NORMAL_END_REASONS))
        for reason, (fn, c, point, want) in cases.items():
            with self.subTest(reason=reason):
                got = builder.normal_end_reading(edited(fn), c, point)
                self.assertEqual((got['normal_end_at_full_horizon'], got['reasons']),
                                 (False, want))

    def test_control_the_frozen_rule_leaves_no_bare_none_at_the_horizon(self):
        """The full-horizon chain up to its horizon look, without the decision: the reference
        rule's horizon action is a crossing at an eligible look that nothing acted on -- a
        defect (``missed``), never a reportable ``none``."""
        run = self.runs['open_at_horizon']
        self.assertEqual(of(run['events'], 'decision'), [])
        dobj = self.assertResult('open_at_horizon', INVALID, False, 'none', None)
        self.assertEqual((dobj['eligibility']['crossing']['verdict'],
                          dobj['eligibility']['crossing']['action']),
                         ('missed', 'horizon_no_decision'))
        self.assertEqual([(s, d['consequence'], d.get('crossing_verdict'))
                          for s, d in run['agreement']],
                         [('FAIL', 'LIVE_DECISION_INVALID', 'missed')])

    def test_control_a_valid_decision_before_a_later_abort_is_unchanged(self):
        """A receipted ``deploy_candidate`` at n = 44, then a refused restart (non-cap) or the
        fourth down (case (b)) in the follow-up cohort: the decision stands and is reported;
        the builder of 9f0aff6 gives the same result, label and flag.  Without its receipt the
        same decision is provisional, as before."""
        for name, reason, label in (('post_decision_refused', 'harness_defect', None),
                                    ('cap_after_decision', 'server_restart_cap',
                                     'decision stands at tau=44; follow-up truncated')):
            with self.subTest(run=name):
                run = self.runs[name]
                self.assertEqual(run['status'], 'aborted')
                (decision,) = of(run['events'], 'decision')
                self.assertLess(decision['seq'], terminal(run['events'])['seq'])
                dobj = self.assertResult(name, 'deploy_candidate', True, None, reason)
                if label is None:
                    self.assertIsNone(dobj['decision_label'])
                else:
                    self.assertTrue(dobj['decision_label'].startswith(label))
                self.assertEqual(run['fails'], [])
                if self.pre_fix is not None:
                    old = self.rows(name, 'pre_fix')
                    new = self.rows(name)
                    for k in ('primary_result', 'reportable', 'decision_label', 'decision'):
                        self.assertEqual(old[2][k], new[2][k], k)
                    self.assertEqual({k: v for k, v in old[2]['restart_cap'].items()},
                                     {k: v for k, v in new[2]['restart_cap'].items()
                                      if k not in ('cap_value', 'binding')})
                    self.assertEqual((old[1]['decision'], old[1]['reportable']),
                                     (new[1]['decision'], new[1]['reportable']))
                receipt = lab_eventlog.decision_receipt(run['events'], mock=True)
                stripped = [e for e in run['events'] if e['seq'] != receipt['receipt_seq']]
                obj = builder.decision_object(stripped, run['cfg'], 'T4')
                self.assertEqual((obj['primary_result'], obj['reportable']),
                                 (builder.PROVISIONAL_LABEL, False))

    # ----------------------------------------------------------------- the cap's provenance
    def test_the_effective_cap_and_its_binding_are_in_decision_json_and_the_summary(self):
        for name in PRODUCTION + VARIANTS:
            with self.subTest(run=name):
                run = self.runs[name]
                returned, written, dobj = self.rows(name)
                summary = self.runs[name]['built']['summary']
                block = run['cfg']['server_supervision']
                self.assertEqual(block, {'max_supervised_restarts_per_server_per_trial': CAP,
                                         'on_exceeding': 'abort_trial_incomplete'})
                started = of(run['events'], 'trial_started')[0]['body']
                self.assertEqual(started['config_sha256'], run['cfg_sha'])
                binding = dobj['restart_cap']['binding']
                self.assertEqual((dobj['restart_cap']['cap_value'], binding['value'],
                                  binding['error']), (CAP, CAP, None))
                self.assertEqual((binding['server_supervision'],
                                  binding['server_supervision_sha256'],
                                  binding['config_path'], binding['config_sha256'],
                                  binding['chain_config_sha256'],
                                  binding['config_sha256_matches_chain'], binding['reader']),
                                 (block, sha256_canonical(block), 'freeze/config.json',
                                  run['cfg_sha'], run['cfg_sha'], True,
                                  'lab_common.server_supervision_cap'))
                for row in (returned, written):
                    self.assertEqual((row['restart_cap_value'],
                                      row['restart_cap_config_matches_chain']), (CAP, True))
                program = summary['restart_cap']
                self.assertEqual((program['value'], program['server_supervision'],
                                  program['config_sha256'], program['config_path']),
                                 (CAP, block, run['cfg_sha'], 'freeze/config.json'))

    def test_negative_the_binding_reads_the_configuration_and_sees_it_change(self):
        """The full-horizon chain built over a copy of its results whose frozen configuration
        was changed AFTER the run: cap 2 -> the provenance says 2 and that the file is not the
        one the chain recorded; the block removed -> no value, the reader's refusal, not bound.
        (The value is read, never a constant; the binding can fail.)"""
        base = self.runs['full_horizon_null']
        for label, edit, value, error in (
                ('cap_2', lambda c: c['server_supervision'].__setitem__(
                    'max_supervised_restarts_per_server_per_trial', 2), 2, None),
                ('absent', lambda c: c.pop('server_supervision'), None,
                 'server_supervision: absent')):
            with self.subTest(edit=label):
                root = base['tree'].root / ('edited_%s' % label)
                shutil.copytree(base['results'], root)
                path = root / 'freeze' / 'config.json'
                cfg = json.loads(path.read_text('utf-8'))
                edit(cfg)
                path.write_text(lab_common.canonical_json(cfg) + '\n', encoding='utf-8')
                got = build_with(builder, dict(base, results=root), 'edited')
                binding = got['decision']['restart_cap']['binding']
                self.assertEqual((got['decision']['restart_cap']['cap_value'], binding['value'],
                                  binding['error'], binding['config_sha256'],
                                  binding['config_sha256_matches_chain']),
                                 (value, value, error, sha256_file(path), False))
                for row in (got['returned'], got['written']):
                    self.assertEqual((row['restart_cap_value'],
                                      row['restart_cap_config_matches_chain']), (value, False))
                self.assertIn('cap_value_absent' if value is None else 'cap_binding_absent',
                              masquerades(got['written'], got['decision'], base['events'],
                                          base['cfg'], base['cfg_sha'], False))

    # ----------------------------------------------------------------- mutations
    def test_mutation_the_pre_fix_builder_publishes_reportable_none_and_is_flagged(self):
        """Finding 9 reproduced over the same chains: the builder of 9f0aff6 publishes ``none``,
        reportable, in ``decision.json`` and both summary rows for the two predecision aborts,
        the trial ended short of the horizon and the open chain; the audit predicate flags
        exactly those four as incomplete-but-reported, and every run for the missing cap
        provenance.  With the current builder it flags nothing."""
        if self.pre_fix is None:
            self.skipTest('git history is not available')
        for name in PRE_FIX_NONE:
            with self.subTest(run=name):
                returned, written, dobj = self.rows(name, 'pre_fix')
                for row in (returned, written):
                    self.assertEqual((row['decision'], row['reportable']), ('none', True))
                self.assertEqual((dobj['primary_result'], dobj['reportable']), ('none', True))
        flagged = {name for name in self.runs
                   if 'incomplete_chain_reported' in self.flags(name, 'pre_fix')}
        self.assertEqual(flagged, set(PRE_FIX_NONE))
        self.assertTrue(all('cap_value_absent' in self.flags(name, 'pre_fix')
                            for name in self.runs))
        self.assertEqual({name: self.flags(name) for name in self.runs if self.flags(name)}, {})

    def test_mutation_removing_the_two_branches_restores_reportable_none_and_is_flagged(self):
        for name in PRE_FIX_NONE:
            with self.subTest(run=name):
                returned, written, dobj = self.rows(name, 'both_branches_removed')
                for row in (returned, written):
                    self.assertEqual((row['decision'], row['reportable']), ('none', True))
                self.assertIn('incomplete_chain_reported', self.flags(name,
                                                                      'both_branches_removed'))
        for name in set(self.runs) - set(PRE_FIX_NONE):
            with self.subTest(unaffected=name):
                self.assertEqual(self.rows(name, 'both_branches_removed')[2]['primary_result'],
                                 self.rows(name)[2]['primary_result'])

    def test_mutation_without_the_abort_branch_the_abort_is_not_labelled_an_abort(self):
        """The incomplete-chain branch still keeps the two aborts non-reportable (defence in
        depth), but their result no longer says they aborted: the first control fails."""
        for name in ('refused_early', 'identity_early'):
            with self.subTest(run=name):
                _r, written, dobj = self.rows(name, 'abort_branch_removed')
                self.assertEqual((written['decision'], written['reportable'],
                                  dobj['primary_result']), (INCOMPLETE, False, INCOMPLETE))
                self.assertNotEqual(dobj['primary_result'], PREDECISION)

    def test_the_chains_are_not_touched_by_any_build(self):
        for name, run in self.runs.items():
            with self.subTest(run=name):
                self.assertEqual(run['digest_after'], run['digest_before'])


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
