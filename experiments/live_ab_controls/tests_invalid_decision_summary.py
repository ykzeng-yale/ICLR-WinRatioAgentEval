"""Controls of root's 19:05 blocking finding: an invalid decision never becomes the summary's result.

``reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md`` (root, origin/main 75c10af), on
03fe0ca (unchanged at 7ebffad): ``build_live_ab_results.decision_object`` labelled a decision logged
after a non-cap no-decision point ``LIVE_DECISION_INVALID (harness defect)`` with ``reportable =
True``, and ``build`` kept the logged kind as the summary's ``decision`` unless ``reportable`` was
false -- so ``program_summary.json`` published ``deploy_candidate`` / ``reportable: true`` for it.
Required: "for any invalid post-boundary decision, keep the original logged event under
``logged_decision``, set ``reportable = false``, and make the summary's decision the invalidity
label"; a bounded mutation control over the complete results-summary path, not only
``decision_object``; the original chain and failure history preserved; "A missed eligible crossing
before the boundary must still fail; a later ineligible crossing without a decision stays
explicitly not acted on."

Every control here runs the COMPLETE results path -- ``build_live_ab_results.build`` over a
chain on disk, reading back the returned summary row, the written ``program_summary.json`` row
and ``decision.json`` -- and the verifier's ``reference_rule.agreement`` rows of the same chain.
:func:`contradictions` is the audit predicate (root: "audit every other path where a label says
'not reportable' but a flag or the summary says otherwise"): the summary's ``decision`` is not
``decision.json``'s ``primary_result``; the summary's flag differs from it; ``reportable`` is true
while the result is not the logged decision (a label, or ``LIVE_DECISION_INVALID``); a label says
"not reportable" while the flag is true; the logged decision is lost from a non-reportable row.

* Production chains (``run_trial`` in process on the D3 tree, which deploys at n = 44; the
  harness of ``tests_eb1_supervision``): ``control`` (no crash: the valid eligible decision);
  ``refused`` (a refused restart owes ``abort_owed(harness_defect)`` while pair 44 is in flight:
  the drain's crossing is not acted on); and three MUTATIONS that write an invalid post-boundary
  decision -- the 988baf7 look gate (``tests_subset_review_fixes.look_988baf7``) over the refused
  restart and over a restart failing its ``identity`` stage, and the gate without case (a)
  (``tests_eb1_cap_estimand.look_without_case_a``) over the fourth down.
* Variants written by the production chain writer (``lab_eventlog.EventLog``: same types and
  bodies, fresh envelopes) into a results root beside the tree: ``verbatim`` (the refused chain
  unchanged: the control of the rewriting), ``missed`` (the refused chain with its
  ``abort_owed`` moved to just AFTER the crossing look: an eligible crossing before the boundary
  with no decision) and ``disagreeing`` (the control chain with the decision's ``n`` 44 -> 43).
* The negative control of the controls: the builder blob of 7ebffad (``git show``), loaded as a
  module and run over the SAME trees, publishes the invalid decision (root's finding reproduced)
  and :func:`contradictions` flags exactly those rows.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off (protocol
14.7).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
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
import lab_orchestrator as orch                                         # noqa: E402
import lab_verify_log                                                   # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
import tests_subset_review_fixes as fixes                               # noqa: E402

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule

CROSS_N = 44
INVALID = 'LIVE_DECISION_INVALID (harness defect)'
NOT_ACTED = 'NOT_ACTED_ON_abort_before_decision'
#: The commit whose builder root's 19:05 finding reads (03fe0ca's decision/summary code, unchanged
#: at 7ebffad): the negative control of these controls.
PRE_FIX = '7ebffad66336b84bc0dae5ca53d8899f001112c9'
PRODUCTION = ('control', 'refused', 'refused_988baf7', 'identity_988baf7', 'cap_a_mutant')
INVALID_RUNS = ('refused_988baf7', 'identity_988baf7', 'cap_a_mutant')
VARIANTS = ('verbatim', 'missed', 'disagreeing')


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def crossing(events) -> dict:
    """The first logged look whose reference shadow crosses."""
    return next(e for e in of(events, 'monitor_update')
                if e['body']['shadow']['action'] != 'none')


def chain_digest(results: Path, trial: str) -> str:
    """sha256 over every segment file of the chain, in order (what the builder must not touch)."""
    h = hashlib.sha256()
    for path in lab_eventlog.segment_paths(results / trial / 'events'):
        h.update(path.name.encode() + b'\0' + path.read_bytes())
    return h.hexdigest()


def contradictions(row: dict, dobj: dict) -> list:
    """The audit predicate: every way the summary row ``row`` or ``decision.json`` ``dobj`` says a
    result is reportable while a label, or the other file, says it is not."""
    logged = dobj['decision']
    logged_kind = logged['kind'] if logged else 'none'
    label = dobj.get('decision_label') or ''
    out = []
    if row['decision'] != dobj['primary_result']:
        out.append('summary_decision_is_not_the_primary_result')
    if row['reportable'] is not dobj['reportable']:
        out.append('summary_flag_differs_from_decision_json')
    if dobj['reportable'] and dobj['primary_result'] != logged_kind:
        out.append('reportable_but_the_result_is_not_the_logged_decision')
    if dobj['reportable'] and label.startswith('not reportable'):
        out.append('label_says_not_reportable_but_the_flag_is_true')
    if row['reportable'] and row['decision'] in (INVALID, builder.RESTART_CAP_INCOMPLETE_LABEL,
                                                 builder.ABORT_INCOMPLETE_LABEL,
                                                 builder.PROVISIONAL_LABEL):
        out.append('summary_reports_a_label_as_reportable')
    if not row['reportable'] and row.get('logged_decision') != logged_kind:
        out.append('logged_decision_lost')
    if row['reportable'] and 'logged_decision' in row:
        out.append('logged_decision_beside_a_reported_result')
    return out


def build_all(module, tree, results: Path | None = None) -> dict:
    """The complete results path of ``module`` (the builder) over ``tree``'s chain, or over the
    chain under ``results``: the returned summary row, the WRITTEN ``program_summary.json`` row
    and ``decision.json``."""
    results = Path(results or tree.results)
    out = tree.root / ('built_%s_%d' % (module.__name__, time.monotonic_ns()))
    returned = module.build([tree.trial], tree.bundle_sha, results_root=results,
                            work_root=tree.work, out_dir=out, mock=True)
    written = json.loads((out / 'program_summary.json').read_text('utf-8'))
    return {'returned': returned['trials'][tree.trial],
            'written': written['trials'][tree.trial],
            'decision': json.loads((out / tree.trial / 'decision.json').read_text('utf-8'))}


def agreement_rows(tree, results: Path | None = None) -> list:
    """The verifier's ``reference_rule.agreement`` rows (full mode) of the chain on disk."""
    report = lab_verify_log.verify_trial(tree.trial, tree.bundle_sha, mode='full',
                                         results_root=Path(results or tree.results),
                                         work_root=tree.work)
    return [(f.severity, dict(f.detail)) for f in report.findings
            if f.check == 'reference_rule.agreement']


def write_variant(tree, events, name: str) -> Path:
    """A results root beside ``tree``'s: its freeze (copied) and ``events`` re-appended by the
    production writer -- same types and bodies, fresh envelopes (``seq``, ``prev``, ``h``); an
    ``anchor`` closes its segment as the orchestrator's does."""
    root = tree.root / ('variant_%s' % name)
    shutil.copytree(tree.freeze, root / 'freeze')
    log = lab_eventlog.EventLog(root / tree.trial / 'events', tree.trial, tree.bundle_sha,
                                uuid.uuid4().hex, create=True)
    try:
        for ev in events:
            body = copy.deepcopy(ev['body'])
            if ev['type'] == 'anchor':
                log.close_segment(anchor_body=body)
            else:
                log.append(ev['type'], body)
    finally:
        log.close()
    return root


def load_pre_fix_builder():
    """The builder blob of :data:`PRE_FIX`, loaded as a module (it imports the same
    ``lab_*`` modules; only the builder differs), or None without git history."""
    blob = subprocess.run(['git', '-C', str(REPO), 'show',
                           '%s:experiments/live_ab/build_live_ab_results.py' % PRE_FIX],
                          capture_output=True, check=False)
    if blob.returncode != 0:
        return None
    tmp = Path(tempfile.mkdtemp(prefix='builder_prefix_'))
    path = tmp / 'build_live_ab_results_7ebffad.py'
    path.write_bytes(blob.stdout)
    spec = importlib.util.spec_from_file_location('build_live_ab_results_7ebffad', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)                              # type: ignore[union-attr]
    shutil.rmtree(tmp, ignore_errors=True)
    return module


def run_production(name: str, tree) -> str:
    fake = sup.FakeServers()
    hook = None
    gate = None
    if name in ('refused', 'refused_988baf7'):
        fake.restart_raises = lab_common.PreflightError
        hook = sup.CrashPlan(fake, pairs=(CROSS_N,))
    elif name == 'identity_988baf7':
        fake.script = [None, 'identity']
        hook = sup.CrashPlan(fake, pairs=(CROSS_N,))
    elif name == 'cap_a_mutant':
        hook = sup.CrashPlan(fake, pairs=(1, 2, 3, CROSS_N))
    if name.endswith('_988baf7'):
        gate = fixes.look_988baf7
    elif name == 'cap_a_mutant':
        gate = cap.look_without_case_a
    patch = (mock.patch.object(orch.World, '_look_eligibility', gate) if gate is not None
             else mock.patch.object(orch, 'SUMMARY_TEST_NOOP', None, create=True))
    with patch:
        return sup.run(tree, fake, hook=hook)


class SummaryPathControls(unittest.TestCase):
    """Five production runs of the D3 tree and three written variants, each built by the current
    builder and by the 7ebffad builder (the complete path both times)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees: dict = {}
        cls.runs: dict = {}
        for name in PRODUCTION:
            tree = cap.d3_tree()
            cls.trees[name] = tree
            status = run_production(name, tree)
            cls.runs[name] = {'status': status, 'events': tree.events(), 'tree': tree,
                              'results': tree.results}
        refused = cls.runs['refused']['events']
        control = cls.runs['control']['events']
        look = crossing(refused)
        (owed,) = of(refused, 'abort_owed')
        moved = [e for e in refused if e['seq'] != owed['seq']]
        at = next(i for i, e in enumerate(moved) if e['seq'] == look['seq']) + 1
        missed = moved[:at] + [owed] + moved[at:]
        disagreeing = copy.deepcopy(control)
        next(e for e in disagreeing if e['type'] == 'decision')['body']['n'] = CROSS_N - 1
        for name, events, base in (('verbatim', refused, 'refused'), ('missed', missed, 'refused'),
                                   ('disagreeing', disagreeing, 'control')):
            tree = cls.trees[base]
            results = write_variant(tree, events, name)
            cls.runs[name] = {'status': None, 'tree': tree, 'results': results,
                              'events': list(lab_eventlog.read_chain(
                                  results / tree.trial / 'events', tree.trial,
                                  tree.bundle_sha).events)}
        cls.pre_fix = load_pre_fix_builder()
        for name, run in cls.runs.items():
            run['digest_before'] = chain_digest(run['results'], run['tree'].trial)
            run['agreement_before'] = agreement_rows(run['tree'], run['results'])
            run['built'] = build_all(builder, run['tree'], run['results'])
            run['pre_fix'] = (None if cls.pre_fix is None
                              else build_all(cls.pre_fix, run['tree'], run['results']))
            run['digest_after'] = chain_digest(run['results'], run['tree'].trial)
            run['agreement_after'] = agreement_rows(run['tree'], run['results'])

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees.values():
            tree.close()

    def rows(self, name: str, which: str = 'built') -> tuple:
        got = self.runs[name][which]
        return got['returned'], got['written'], got['decision']

    def assertSummary(self, name: str, decision: str, reportable: bool,
                      logged: str | None) -> None:
        returned, written, dobj = self.rows(name)
        for row in (returned, written):
            self.assertEqual((row['decision'], row['reportable'], row.get('logged_decision')),
                             (decision, reportable, logged))
        self.assertEqual((dobj['primary_result'], dobj['reportable']), (decision, reportable))
        self.assertEqual(contradictions(returned, dobj), [])
        self.assertEqual(contradictions(written, dobj), [])

    # ----------------------------------------------------------------- the mutation
    def test_mutation_an_invalid_post_boundary_decision_is_never_the_summary_decision(self):
        """The three mutated production runs log ``deploy_candidate`` at n = 44 AFTER their
        no-decision point; the verifier FAILs it; the summary's decision is the invalidity
        label, not reportable, and the logged decision is kept beside it."""
        rules = {'refused_988baf7': ('reference_rule.agreement', 'decision_after_no_decision_point'),
                 'identity_988baf7': ('reference_rule.agreement',
                                      'decision_after_no_decision_point'),
                 'cap_a_mutant': ('server.lifecycle', 'decision_after_cap')}
        for name in INVALID_RUNS:
            with self.subTest(run=name):
                run = self.runs[name]
                events = run['events']
                self.assertEqual(run['status'], 'aborted')
                (decision,) = of(events, 'decision')
                point = lab_eventlog.no_decision_point(events, cap.CAP)
                self.assertGreater(decision['seq'], point['seq'])
                self.assertEqual((decision['body']['kind'], decision['body']['n']),
                                 ('deploy_candidate', CROSS_N))
                fails = [(c, d.get('rule')) for c, d in run['tree'].verify_fails()]
                self.assertIn(rules[name], fails)
                self.assertSummary(name, INVALID, False, 'deploy_candidate')
                _returned, _written, dobj = self.rows(name)
                self.assertEqual(dict(dobj['decision']),
                                 dict(decision['body'], seq=decision['seq']),
                                 'decision.json keeps the original logged event')
                self.assertTrue(dobj['decision_label'].startswith('not reportable: logged after'))
                self.assertEqual(dobj['eligibility']['decision_verdict'], 'after_exclusion')

    def test_the_chain_and_its_failures_are_preserved_by_the_build(self):
        for name, run in self.runs.items():
            with self.subTest(run=name):
                self.assertEqual(run['digest_after'], run['digest_before'])
                self.assertEqual(run['agreement_after'], run['agreement_before'])

    def test_negative_control_the_7ebffad_builder_publishes_the_invalid_decision(self):
        """Root's finding, reproduced over the same chains: the 7ebffad builder's summary
        reports ``deploy_candidate``, ``reportable: true`` for the two non-cap mutations, and
        the audit predicate flags exactly those rows (and the other invalid chains)."""
        if self.pre_fix is None:
            self.skipTest('git history is not available')
        for name in ('refused_988baf7', 'identity_988baf7'):
            with self.subTest(run=name):
                returned, written, dobj = self.rows(name, 'pre_fix')
                for row in (returned, written):
                    self.assertEqual((row['decision'], row['reportable']),
                                     ('deploy_candidate', True))
                self.assertEqual((dobj['primary_result'], dobj['reportable']), (INVALID, True))
                self.assertIn('summary_decision_is_not_the_primary_result',
                              contradictions(returned, dobj))
                self.assertIn('label_says_not_reportable_but_the_flag_is_true',
                              contradictions(written, dobj))
        # the cap's invalid decision was never promoted, but its result was not the invalidity
        # label either
        returned, _written, dobj = self.rows('cap_a_mutant', 'pre_fix')
        self.assertEqual((returned['decision'], returned['reportable']),
                         (builder.RESTART_CAP_INCOMPLETE_LABEL, False))
        flagged = {name for name in self.runs
                   if contradictions(*self.rows(name, 'pre_fix')[::2])
                   or contradictions(*self.rows(name, 'pre_fix')[1:])}
        self.assertEqual(flagged, {'refused_988baf7', 'identity_988baf7', 'missed',
                                   'disagreeing'})
        self.assertEqual({name for name in self.runs
                          if contradictions(*self.rows(name)[::2])
                          or contradictions(*self.rows(name)[1:])}, set())

    # ----------------------------------------------------------------- negative controls
    def test_control_a_valid_eligible_decision_stays_reportable(self):
        run = self.runs['control']
        self.assertEqual(run['status'], 'ended')
        (decision,) = of(run['events'], 'decision')
        self.assertEqual((decision['body']['n'], decision['body']['monitor_seq']),
                         (CROSS_N, crossing(run['events'])['seq']))
        self.assertEqual(run['tree'].verify_fails(), [])
        self.assertEqual(run['agreement_before'], [])
        self.assertSummary('control', 'deploy_candidate', True, None)
        _returned, _written, dobj = self.rows('control')
        self.assertIsNone(dobj['decision_label'])
        self.assertEqual((dobj['eligibility']['crossing']['verdict'], dobj['decision_status']),
                         ('acted_on', 'receipted'))
        if self.pre_fix is not None:
            # root 07:10 (reviews/predecision_abort_reporting_ruling_20260925_0710.md) added three
            # provenance keys to every row (the effective cap, its binding, the abort reason);
            # everything else of the row is the 7ebffad row
            added = ('restart_cap_value', 'restart_cap_config_matches_chain', 'abort_reason')
            now = self.rows('control')[0]
            self.assertEqual(self.rows('control', 'pre_fix')[0],
                             {k: v for k, v in now.items() if k not in added},
                             'the repair changes nothing for a valid decision')
            self.assertEqual([now[k] for k in added], [3, True, None])

    def test_control_a_missed_eligible_crossing_before_the_boundary_still_fails(self):
        run = self.runs['missed']
        events = run['events']
        look = crossing(events)
        (owed,) = of(events, 'abort_owed')
        self.assertEqual(owed['seq'], look['seq'] + 1, 'the boundary just after the crossing')
        self.assertEqual(of(events, 'decision'), [])
        self.assertEqual([(s, r['consequence'], r.get('crossing_verdict'))
                          for s, r in run['agreement_before']],
                         [('FAIL', 'LIVE_DECISION_INVALID', 'missed')])
        self.assertSummary('missed', INVALID, False, 'none')
        _returned, _written, dobj = self.rows('missed')
        self.assertEqual(dobj['eligibility']['crossing']['verdict'], 'missed')
        self.assertIsNone(dobj['crossing_not_acted_on'])
        self.assertTrue(dobj['decision_label'].startswith('not reportable: no decision'))

    def test_control_a_later_ineligible_crossing_without_a_decision_stays_not_acted_on(self):
        for name in ('refused', 'verbatim'):
            with self.subTest(run=name):
                run = self.runs[name]
                events = run['events']
                (owed,) = of(events, 'abort_owed')
                look = crossing(events)
                self.assertGreater(look['seq'], owed['seq'])
                self.assertEqual(of(events, 'decision'), [])
                self.assertEqual([(s, r['consequence'], r['no_decision_reason'])
                                  for s, r in run['agreement_before']],
                                 [('INFO', NOT_ACTED, 'abort_owed')])
                self.assertSummary(name, builder.ABORT_INCOMPLETE_LABEL, False, 'none')
                _returned, _written, dobj = self.rows(name)
                self.assertEqual((dobj['crossing_not_acted_on']['n'],
                                  dobj['crossing_not_acted_on']['abort_reason']),
                                 (CROSS_N, 'harness_defect'))
        self.assertEqual(self.runs['refused']['status'], 'aborted')
        self.assertEqual(self.runs['refused']['tree'].verify_fails(), [])
        self.assertEqual(self.rows('verbatim')[2]['eligibility'],
                         self.rows('refused')[2]['eligibility'],
                         'the rewriting changes no reading')

    def test_audit_a_decision_disagreeing_with_the_reference_rule_is_not_reportable(self):
        """The other ``LIVE_DECISION_INVALID`` path (protocol 8.9: the logged decision against
        the reference rule's first crossing), receipted and eligible: not reportable either."""
        run = self.runs['disagreeing']
        self.assertEqual([(s, r['consequence'], r.get('live_n'))
                          for s, r in run['agreement_before']],
                         [('FAIL', 'LIVE_DECISION_INVALID', CROSS_N - 1)])
        self.assertSummary('disagreeing', INVALID, False, 'deploy_candidate')
        _returned, _written, dobj = self.rows('disagreeing')
        self.assertEqual((dobj['decision_status'], dobj['eligibility']['decision_verdict']),
                         ('receipted', 'eligible'))
        self.assertTrue(dobj['decision_label'].startswith('not reportable: the logged decision'))


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
