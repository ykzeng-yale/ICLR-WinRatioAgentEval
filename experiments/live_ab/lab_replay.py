"""Protocol 11.5: the extended CPU replay of the FROZEN rule on the realized ``N_P`` (plan stage 8).

Root, 2026-09-23 20:40 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``, item 2): "complete
only the missing executable drivers for stages 1, 2, 4-6, the stage-3 two-stream loaded sweep, and the
Sec. 11.5 extended CPU replay/seed ... Do not run the loaded stages or repeat the accepted CPU grid
while implementing them."  The plan row this module serves says the code and the seed were ABSENT
(``results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json`` stage 8, ``pins_and_missing_inputs``).

WHAT IT IS.  A pure CPU simulator: no model, no server, no network, no clock in any decision.  It
reads the realized roster (``lab_design`` shape: ``{'S1': [...], 'S2': [...]}``), the pilot table
(``results/local_stream/episodes_flat.csv`` shape), the frozen config, a realized ``N_P`` given as a
parameter, and the explicit outcome-model choices below; it writes a write-once table and a
write-once manifest.  It never runs by import and nothing in the test suite runs the real grid.

THE SPECIFICATION, item by item (``experiments/live_ab/design/protocol_FINAL.md:2238-2259``):

1. Tasks and strata are the realized roster's; the arrival order of each replicate is drawn by EXACTLY
   the code path of protocol 3.4 / ``lab_design._generate`` (S1 permutation, S2 permutation, whole-pair
   permutation, from one generator, in that order), but from the replicate's own seed.
   ``order_indices`` mirrors the draw sequence and ``tests_lab_replay.OrderEqualityTests`` proves that,
   seeded with ``SeedSequence([design_seed_base, trial_no])``, it reproduces ``lab_design.arrival_order``
   uid for uid.  One fair coin per enrolled pair, mapped as the production coin maps it
   (``config.json`` ``coin.map`` = ``1->candidate_at_position_1``).
2. Success.  S1 task under an arm with a pilot: with probability ``w`` the task's pilot outcome under
   that arm, else Bernoulli at the arm's pilot S1 rate (433/591 for both arms on the real pilot).  S2
   task: Bernoulli(``q``).  The candidate shift ``s`` is added to the candidate's probability and clipped
   to [0, 1].  READING R1 (stated, root may overrule): "the candidate's probability" is the per-task
   success probability of item 2, ``w*y + (1-w)*rate`` (S1) or ``q`` (S2), so the shift is applied to
   that mixture and ONE uniform is compared with it.  This is the same law as the two-stage draw at
   ``s = 0``; a two-stage draw that shifted the reused 0/1 outcome instead would attenuate the shift by
   ``w * P(y = 0)`` and is not what the sentence says.
3. Cost.  For a both-succeed pair of T1/T2, one pilot task in which both workflows succeeded is drawn
   uniformly and its two latencies are used jointly; the frozen tier rule (``winstats.compare`` with the
   hierarchy of ``lab_enclosure.tiers_from_config``: success, then cost at relative tolerance 0.05,
   eligible only on joint success) gives ``Z``.  ``D = s_cand - s_inc``.
4. Rule.  The frozen band and decision of protocol 8.1-8.4, evaluated at the ``N_P`` completed prefixes
   (item 4: "Scores are complete at each pair resolution, so enclosures are degenerate").  The radius
   vector is ``lab_monitor.radius_table`` (the freeze-bundle deliverable, the same call ``band`` makes)
   and ``decide_matrix`` is the vectorised form of ``lab_monitor.band`` + ``lab_monitor.decide``; the
   controls prove element-wise equality of every endpoint and of the first decision with the scalar
   ``MonitorState`` path on random complete sequences, and each real cell re-runs
   ``crosscheck_per_cell`` of its own replicates through ``MonitorState``/``decide``/
   ``lab_enclosure.pair_enclosure`` and refuses to write if any disagrees.
5. Cells, exhaustive: ``w x q x s x N_P x trial`` = 4 x 3 x 3 x 3 x 4 = 432; 4,000 replicates per cell,
   20,000 for T4 (3,456,000 in all).  ``enumerate_cells`` builds them without simulating anything, and
   ``check_grid`` -- called by ``run_replay`` on every full run -- compares them with
   ``PROTOCOL_11_5_ITEM_5``, the item restated as literals apart from the ``GRID_*`` tuples
   ``enumerate_cells`` iterates, and with the literal totals 432 and 3,456,000; so an edited grid tuple is
   refused at the production entry point, not only by a unit test.
6. Output: per cell the counts and rates of DEPLOY / HARM_RETAIN / ABSTAIN, each with a pointwise Wilson
   95% interval, and the Q1 / median / Q3 of the crossing prefix (all crossings, and per decision kind;
   ``numpy.percentile`` method ``linear``; null when no replicate crossed).  Every row is written.
7. Provenance: the manifest carries the script sha256, the seed rule and the output sha256 for the
   freeze bundle's planning member (``lab_common.FREEZE_BUNDLE_KEYS`` ``planning_sha256``).

THE SEED RULE (plan stage 8: "seed: ABSENT: not chosen"; stated here before any replay runs).
Replicate ``r`` (1-based) of the cell with grid ordinal ``c`` (1..432, the order of ``enumerate_cells``)
draws from ``numpy.random.Generator(PCG64(SeedSequence([design_seed_base, 1105, c, r])))``.
``1105`` names protocol 11.5 and is a fixed stream tag.  The entropy list always has four words: numpy
pads short entropy with zeros, so ``SeedSequence([a, b]) == SeedSequence([a, b, 0])`` (checked on
numpy 2.4.1); with a nonzero tag in the second word no replay seed can equal a trial arrival-order seed
``SeedSequence([design_seed_base, e])``, e in 1..4.  Per-replicate seeding makes every replicate
reproducible alone, independent of block size and of which other cells ran.  Draw order inside a
replicate, fixed: the three order permutations; ``integers(0, 2, size=N_P)`` coins;
``random((N_P, 2))`` success uniforms (candidate column 0); ``integers(0, pool, size=(N_P, 2))`` cost
indices.

PROPOSED, NEEDS ROOT -- the outcome model protocol 11.5 does not define (not on the plan's OD list;
root item 2, ``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``).  Item 2 draws
success from "the arm's pilot" and item 3 resamples latency "jointly from the pilot tasks in which both
workflows succeeded".  Neither is defined for:

* T3's candidate (``t3`` server, Granite): it has no pilot at all -- no task outcomes and no stratum rate;
* the cost pair of T3 and of T4: T4's two arms are the SAME workflow with one pilot run per task, so a
  joint draw from one task gives two identical latencies and every both-succeed pair would tie at tier 1;
  T3's candidate has no latency data.

These are ``open_outcome_model`` keys, derived from ``config.json`` ``trials`` by ``outcome_model_gaps``
(an arm whose server has no pilot; a pair that is not two distinct piloted workflows), with closed value
sets ``OPEN_MODEL_CHOICES``.  The replay REFUSES unless the caller passes a value for every gap and no
other key: nothing is defaulted.  The owner's PROPOSAL is ``PROPOSED_OPEN_MODEL``:

* ``T3.candidate.success = coder_single_shot_stratum_rate``: S1 probability = the coder single_shot
  pilot S1 rate (433/591), ``w`` not applied (no task-level evidence exists for this model); S2 = ``q``;
  plus ``s``.  Alternative ``coder_single_shot_task_proxy``: treat the coder's single_shot task outcomes
  as the candidate's pilot (``w`` applied), which imports the coder's per-task difficulty into Granite.
* ``T3.cost_pair`` and ``T4.cost_pair = independent_single_shot_successes``: the two latencies are drawn
  independently, with replacement, from the single_shot latencies of pilot tasks where single_shot
  succeeded.  Alternative ``same_task_single_shot_duplicate``: one draw used twice (tier 1 always ties).

EXCHANGEABILITY AT ``s = 0`` HOLDS FOR T4 ONLY.  T4's two arms are one workflow: both draw success from the
same single_shot pilot (READING R3) and latency from one pool, so at ``s = 0`` the arms are exchangeable
and the T4 ``s = 0`` rows are exact A/A rows for the rule.  T3's are NOT: under the proposal the
candidate is iid Bernoulli(r) on every S1 task while the incumbent is ``w*y_t + (1-w)*r``, which depends
on the task, so the two laws differ (``tests_lab_replay.ExchangeabilityTests``: equal means, unequal
variances, on a synthetic pilot).  ``E[D]`` on S1 is ``w * (r - mean of y over the roster's S1)``, zero
only when the roster's S1 has the pilot's success rate (the realized roster excludes tasks, so in
general it does not); T3 ``s = 0`` rows are therefore not A/A rows.

Under the proposal the T3 rows carry NO information about Granite: they describe the frozen rule under
a candidate that differs from the coder only by the success shift ``s``.  The manifest records the value
passed, ``status: PROPOSED`` unless a ``ruling`` citation is supplied, the alternatives, and this text.
A ``ruling`` must be a ``reviews/<file>.md:<line>`` citation that resolves to an existing line of an
existing file under the repository's ``reviews/`` (root-owned); anything else is refused.  That is ALL
the check performs: whether the cited line rules on this outcome model is for root to confirm.

A second item this module cannot settle, also PROPOSED: the fixed horizons 295 and 495 are cells on the
realized roster, but a roster with fewer pairs than 495 (roster S1 has 295) cannot enroll 495 pairs by
the 3.4 code path.  Such rows are deposited with ``status: NOT_SIMULABLE`` and a reason, never
bootstrapped (``OPEN_ITEMS``).  READING R2: a horizon below the roster's pair count enrolls the first
``N_P`` pairs of the full 3.4 order.

WHAT IT CANNOT SHOW (protocol 11.5, "What it cannot show"): one pilot run per task and arm on a
different serving stack; ``w`` is uncalibrated; the simulated crossing prefixes are expectations, never
measured quantities.  The replay cannot change any rule parameter (protocol 11.5 purpose).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))
#: The repository root, where a ``ruling`` citation (``reviews/<file>.md:<line>``) must resolve.
REPO_ROOT = HERE.parents[1]

import lab_common                                              # noqa: E402
import lab_design                                              # noqa: E402
import lab_enclosure                                           # noqa: E402
import lab_monitor                                             # noqa: E402

try:  # winstats lives in src/ and is a READ-ONLY reference; it is imported, never copied.
    import winstats
except ImportError:  # pragma: no cover - depends on how the caller set sys.path
    _SRC_DIR = HERE.parents[1] / 'src'
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    import winstats


TABLE_SCHEMA = 'live_ab/replay_11_5_table-v1'
MANIFEST_SCHEMA = 'live_ab/replay_11_5_manifest-v1'
TABLE_NAME = 'REPLAY_11_5_TABLE.json'
MANIFEST_NAME = 'REPLAY_11_5_MANIFEST.json'

#: protocol 11.5 item 5, exhaustively.  The nesting order of ``enumerate_cells`` is trial, N_P role,
#: w, q, s; the 1-based position in that order is the cell ordinal the seed rule uses.
GRID_TRIALS: tuple[str, ...] = ('T1', 'T2', 'T3', 'T4')
GRID_W: tuple[float, ...] = (0.3, 0.5, 0.7, 1.0)
GRID_Q: tuple[float, ...] = (0.25, 0.45, 0.60)
GRID_S: tuple[float, ...] = (0.0, -0.02, -0.03)
GRID_FIXED_N_P: tuple[int, ...] = (295, 495)
N_P_ROLES: tuple[str, ...] = ('fixed_295', 'fixed_495', 'realized')
REPLICATES: int = 4000
REPLICATES_T4: int = 20000
GRID_CELLS: int = 432                        # literal, not derived from the tuples above
GRID_REPLICATES: int = 3_456_000             # literal: 3 x 108 x 4,000 + 108 x 20,000
#: protocol 11.5 item 5 (``design/protocol_FINAL.md:2253-2254``) restated as LITERALS, independent of the
#: ``GRID_*`` tuples ``enumerate_cells`` iterates, so ``check_grid`` compares the grid with the protocol
#: and not with itself (``tests_lab_replay.GridEnumerationTests`` reads these values back out of the
#: protocol text).
PROTOCOL_11_5_ITEM_5: dict = {
    'trials': ('T1', 'T2', 'T3', 'T4'), 'w': (0.3, 0.5, 0.7, 1.0), 'q': (0.25, 0.45, 0.60),
    's': (0.0, -0.02, -0.03), 'fixed_n_p': (295, 495), 'replicates': 4000, 'replicates_T4': 20000}

#: protocol 11.5 item 4, the frozen values the replay must see in config.json; any other value is a
#: different rule and the replay refuses (it "cannot change any rule parameter").
FROZEN_RULE: dict = {'alpha_gate': 0.00625, 'rho': 100.0, 'delta': 0.03, 'n_min': 100}

#: The seed rule.  Stated as text so the manifest can hash exactly what was followed.
REPLAY_STREAM_TAG: int = 1105
SEED_RULE_TEXT: str = (
    'replicate r (1-based) of the cell with grid ordinal c (1-based, enumerate_cells order) draws from '
    'numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([design_seed_base, 1105, c, '
    'r]))); draws in order: lab_design 3.4 order permutations (S1, S2, whole pairs), '
    'integers(0, 2, size=N_P) coins (1 -> candidate at position 1), random((N_P, 2)) success uniforms '
    '(column 0 candidate), integers(0, pool, size=(N_P, 2)) cost indices')

#: The pilot's serving label.  Only arms served by it have pilot outcomes (protocol 1.1: the pilot is the
#: coder on the MLX stack; the T3 candidate never ran in it).
PILOT_SERVER: str = 'coder'
WORKFLOWS: tuple[str, ...] = ('single_shot', 'self_test_repair')

OPEN_MODEL_CHOICES: dict[str, tuple[str, ...]] = {
    'T3.candidate.success': ('coder_single_shot_stratum_rate', 'coder_single_shot_task_proxy'),
    'T3.cost_pair': ('independent_single_shot_successes', 'same_task_single_shot_duplicate'),
    'T4.cost_pair': ('independent_single_shot_successes', 'same_task_single_shot_duplicate'),
}
#: PROPOSED, NEEDS ROOT.  Never used unless a caller passes it explicitly.
PROPOSED_OPEN_MODEL: dict[str, str] = {
    'T3.candidate.success': 'coder_single_shot_stratum_rate',
    'T3.cost_pair': 'independent_single_shot_successes',
    'T4.cost_pair': 'independent_single_shot_successes',
}
PROPOSAL_TEXT: str = (
    'PROPOSED, needs root: protocol 11.5 items 2-3 define outcomes only for arms with a pilot and '
    'cost pairs of two distinct piloted workflows. T3 candidate success: coder single_shot pilot S1 '
    'rate (w not applied), q on S2, plus s. T3 and T4 cost pairs: two independent draws from single_shot '
    'latencies of pilot tasks where single_shot succeeded. At s = 0 the arms are exchangeable for T4 '
    'only (T4 s = 0 rows are A/A rows); T3 arms are not exchangeable (the candidate is iid at the pilot '
    'rate, the incumbent follows the per-task pilot outcome), and T3 s = 0 rows are null in mean only '
    'when the roster S1 has the pilot S1 success rate. Under this proposal T3 rows carry no information '
    'about the T3 candidate model.')

READINGS: tuple[dict, ...] = (
    {'id': 'R1', 'status': 'READING', 'text': 'the shift s is added to the per-task success probability '
     'w*y+(1-w)*rate (S1) or q (S2) and clipped to [0,1]; one uniform per episode'},
    {'id': 'R2', 'status': 'READING', 'text': 'a horizon N_P below the roster pair count enrolls the '
     'first N_P pairs of the full protocol 3.4 order'},
    {'id': 'R3', 'status': 'READING', 'text': 'T4 success reuses the single_shot pilot for both arms, '
     'each arm on its own task of the pair (literal item 2)'},
    {'id': 'R4', 'status': 'READING', 'text': 'the pilot S1 rate and both latency pools are computed over '
     'the whole pilot table, not only the tasks that survived into the roster'},
)
OPEN_ITEMS: tuple[dict, ...] = (
    {'id': 'horizon_above_roster_pairs', 'status': 'PROPOSED', 'needs': 'root',
     'value': 'deposit_row_not_simulable',
     'text': 'a fixed horizon larger than the realized roster pair count cannot be enrolled by the 3.4 '
             'code path; the row is deposited NOT_SIMULABLE with a reason, never bootstrapped'},
)

LABELS: tuple[str, ...] = ('DEPLOY', 'HARM_RETAIN', 'ABSTAIN')
DEPLOY, HARM_RETAIN, ABSTAIN = 0, 1, 2
_MONITOR_KIND = {'deploy_candidate': DEPLOY, 'harm_keep_incumbent': HARM_RETAIN,
                 'horizon_no_decision': ABSTAIN}
WILSON_Z: float = 1.959963984540054                  # Phi^-1(0.975)
_BLOCK = 1000                                        # replicates per vectorised block


class ReplayRefused(lab_common.LabError):
    """The replay may not run on these inputs, or its output may not be accepted."""


# ------------------------------------------------------------------------------------------------
# cells
# ------------------------------------------------------------------------------------------------
def make_cell(ordinal: int, trial: str, w: float, q: float, s: float, n_p: int, n_p_role: str,
              replicates: int) -> dict:
    """[pure] One cell.  ``ordinal`` feeds the seed rule; a subset run supplies its own."""
    if trial not in lab_design.TRIAL_NO:
        raise ReplayRefused('unknown trial %r' % (trial,))
    for name, value in (('ordinal', ordinal), ('n_p', n_p), ('replicates', replicates)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ReplayRefused('%s must be a positive int, got %r' % (name, value))
    return {'ordinal': ordinal, 'trial': trial, 'w': float(w), 'q': float(q), 's': float(s),
            'n_p': n_p, 'n_p_role': n_p_role, 'replicates': replicates,
            'cell_id': '%s|w=%r|q=%r|s=%r|N_P=%d(%s)' % (trial, float(w), float(q), float(s), n_p,
                                                         n_p_role)}


def enumerate_cells(realized_n_p: int) -> list[dict]:
    """[pure] The 432 cells of protocol 11.5 item 5, in the fixed ordinal order.  Simulates nothing."""
    if isinstance(realized_n_p, bool) or not isinstance(realized_n_p, int) or realized_n_p < 1:
        raise ReplayRefused('realized_n_p must be a positive int, got %r' % (realized_n_p,))
    horizons = dict(zip(N_P_ROLES, (GRID_FIXED_N_P[0], GRID_FIXED_N_P[1], realized_n_p)))
    cells: list[dict] = []
    for trial in GRID_TRIALS:
        reps = REPLICATES_T4 if trial == 'T4' else REPLICATES
        for role in N_P_ROLES:
            for w in GRID_W:
                for q in GRID_Q:
                    for s in GRID_S:
                        cells.append(make_cell(len(cells) + 1, trial, w, q, s, horizons[role], role,
                                               reps))
    return cells


def check_grid(cells: Sequence[Mapping], realized_n_p: int) -> None:
    """[pure] Raise unless ``cells`` is the protocol 11.5 item 5 grid.

    Two comparisons.  (1) Against the PROTOCOL, not against ``enumerate_cells``: exactly ``GRID_CELLS``
    (432) cells and ``GRID_REPLICATES`` (3,456,000) replicates, literal numbers; each (trial, w, q, s,
    N_P role) of the product of ``PROTOCOL_11_5_ITEM_5`` exactly once; each cell's ``N_P`` its role's
    (295, 495 or ``realized_n_p``) and its replicate count 4,000 (20,000 for T4).  An edited ``GRID_*``
    tuple or replicate constant therefore fails here, where ``run_replay`` calls it.  (2) Against
    ``enumerate_cells(realized_n_p)``: the fixed ordinal order the seed rule uses -- no cell re-ordered.
    """
    got = [dict(c) for c in cells]
    lit = PROTOCOL_11_5_ITEM_5
    if len(got) != GRID_CELLS:
        raise ReplayRefused('the grid has %d cells, protocol 11.5 item 5 has %d'
                            % (len(got), GRID_CELLS))
    planned = sum(int(c.get('replicates', 0)) for c in got)
    if planned != GRID_REPLICATES:
        raise ReplayRefused('the grid plans %d replicates, protocol 11.5 item 5 plans %d'
                            % (planned, GRID_REPLICATES))
    horizon = {'fixed_295': lit['fixed_n_p'][0], 'fixed_495': lit['fixed_n_p'][1],
               'realized': realized_n_p}
    protocol_keys = {(t, w, q, s, role) for t in lit['trials'] for role in horizon
                     for w in lit['w'] for q in lit['q'] for s in lit['s']}
    keys = [(c.get('trial'), c.get('w'), c.get('q'), c.get('s'), c.get('n_p_role')) for c in got]
    if len(set(keys)) != len(keys) or set(keys) != protocol_keys:
        raise ReplayRefused('the grid cells are not the protocol 11.5 item 5 product, each once '
                            '(%d distinct of %d; %d not in the protocol)'
                            % (len(set(keys)), len(keys), len(set(keys) - protocol_keys)))
    for c in got:
        reps = lit['replicates_T4'] if c['trial'] == 'T4' else lit['replicates']
        if c.get('n_p') != horizon[c['n_p_role']] or c.get('replicates') != reps:
            raise ReplayRefused('cell %r has N_P %r and %r replicates; protocol 11.5 item 5 gives %r '
                                'and %r' % (c.get('cell_id'), c.get('n_p'), c.get('replicates'),
                                            horizon[c['n_p_role']], reps))
    want = enumerate_cells(realized_n_p)
    if len(got) != len(want):
        raise ReplayRefused('the grid has %d cells, protocol 11.5 item 5 has %d'
                            % (len(got), len(want)))
    for a, b in zip(got, want):
        if a != b:
            raise ReplayRefused('cell %r differs from the protocol grid cell %r'
                                % (a.get('cell_id'), b['cell_id']))


def replicate_generator(design_seed_base: int, ordinal: int, replicate: int) -> numpy.random.Generator:
    """[pure] The seed rule of the module docstring.  ``replicate`` is 1-based."""
    for name, value in (('design_seed_base', design_seed_base), ('ordinal', ordinal),
                        ('replicate', replicate)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ReplayRefused('%s must be a positive int, got %r' % (name, value))
    return numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(
        [int(design_seed_base), REPLAY_STREAM_TAG, int(ordinal), int(replicate)])))


# ------------------------------------------------------------------------------------------------
# inputs
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Pilot:
    """One run per task and workflow (``results/local_stream/episodes_flat.csv``)."""
    tasks: tuple                      # sorted task uids
    success: dict                     # workflow -> int8 array aligned with ``tasks``
    latency: dict                     # workflow -> float64 array aligned with ``tasks``
    sha256: str                       # sha256 of the bytes read


def load_pilot_csv(path: 'str | Path') -> Pilot:
    """Read the pilot table; refuse anything but exactly one row per (task, workflow)."""
    data = Path(path).read_bytes()
    rows = list(csv.DictReader(data.decode('utf-8').splitlines()))
    seen: dict[tuple, dict] = {}
    for row in rows:
        wf = row.get('variant')
        if wf not in WORKFLOWS:
            raise ReplayRefused('pilot row with workflow %r' % (wf,))
        key = (row.get('task_id'), wf)
        if key in seen:
            raise ReplayRefused('pilot has two rows for %r' % (key,))
        seen[key] = row
    tasks = tuple(sorted({t for t, _ in seen}))
    success: dict[str, numpy.ndarray] = {}
    latency: dict[str, numpy.ndarray] = {}
    for wf in WORKFLOWS:
        succ, lat = [], []
        for t in tasks:
            row = seen.get((t, wf))
            if row is None:
                raise ReplayRefused('pilot task %r has no %s row' % (t, wf))
            if row.get('success') not in ('True', 'False'):
                raise ReplayRefused('pilot success of %r/%s is %r' % (t, wf, row.get('success')))
            try:
                value = float(row.get('latency_s'))
            except (TypeError, ValueError):
                raise ReplayRefused('pilot latency of %r/%s is unreadable' % (t, wf)) from None
            if not math.isfinite(value) or value < 0.0:
                raise ReplayRefused('pilot latency of %r/%s is %r' % (t, wf, value))
            succ.append(1 if row['success'] == 'True' else 0)
            lat.append(value)
        success[wf] = numpy.asarray(succ, dtype=numpy.int8)
        latency[wf] = numpy.asarray(lat, dtype=numpy.float64)
    return Pilot(tasks=tasks, success=success, latency=latency, sha256=lab_common.sha256_bytes(data))


def outcome_model_gaps(cfg: Mapping, trial: str) -> dict[str, str]:
    """[pure] ``{gap_key: why}`` for ``trial``: the outcome inputs protocol 11.5 leaves undefined.

    Derived from ``config.json`` ``trials``, not from a hand-typed list: an arm whose server has no
    pilot needs ``<trial>.<arm>.success``; a pair that is not two DISTINCT PILOTED workflows needs
    ``<trial>.cost_pair`` (item 3's joint within-task draw needs two runs on one task).
    """
    arms = _trial_arms(cfg, trial)
    gaps: dict[str, str] = {}
    for arm in ('candidate', 'incumbent'):
        if arms[arm]['server'] != PILOT_SERVER:
            gaps['%s.%s.success' % (trial, arm)] = 'the %s arm has no pilot' % (arm,)
    piloted = all(arms[a]['server'] == PILOT_SERVER for a in arms)
    if not piloted or arms['candidate']['workflow'] == arms['incumbent']['workflow']:
        gaps['%s.cost_pair' % (trial,)] = ('no joint within-task latency pair exists: '
                                           + ('an arm has no pilot' if not piloted
                                              else 'both arms are one workflow with one run per task'))
    return gaps


def _trial_arms(cfg: Mapping, trial: str) -> dict:
    trials = cfg.get('trials') if isinstance(cfg, Mapping) else None
    if not isinstance(trials, Mapping) or trial not in trials:
        raise ReplayRefused('config.trials has no %r' % (trial,))
    out = {}
    for arm in ('candidate', 'incumbent'):
        spec = trials[trial].get(arm) if isinstance(trials[trial], Mapping) else None
        if not isinstance(spec, Mapping) or spec.get('workflow') not in WORKFLOWS \
                or not isinstance(spec.get('server'), str):
            raise ReplayRefused('config.trials.%s.%s is malformed' % (trial, arm))
        out[arm] = {'workflow': spec['workflow'], 'server': spec['server']}
    return out


def check_open_model(cfg: Mapping, open_model: Optional[Mapping], trials: Sequence[str]) -> dict:
    """[pure] Refuse unless ``open_model`` names exactly the gaps of ``trials`` with allowed values.

    There is no default: the protocol does not define these inputs, and a silently chosen value would
    be a design input nobody decided (task statement, root item 2).
    """
    needed: dict[str, str] = {}
    for trial in sorted(set(trials)):
        needed.update(outcome_model_gaps(cfg, trial))
    if needed and open_model is None:
        raise ReplayRefused('protocol 11.5 does not define %s; pass open_model explicitly (the owner '
                            'proposal is PROPOSED_OPEN_MODEL, status PROPOSED, needs root)'
                            % (sorted(needed),))
    given = dict(open_model or {})
    missing = sorted(set(needed) - set(given))
    extra = sorted(set(given) - set(needed))
    if missing or extra:
        raise ReplayRefused('open_model keys differ from the gaps: missing %r, not a gap here %r'
                            % (missing, extra))
    for key, value in given.items():
        if key not in OPEN_MODEL_CHOICES or value not in OPEN_MODEL_CHOICES[key]:
            raise ReplayRefused('open_model[%r] = %r is not one of %r'
                                % (key, value, OPEN_MODEL_CHOICES.get(key)))
    return given


def frozen_monitor_config(cfg: Mapping, trial: str, n_p: int) -> lab_monitor.MonitorConfig:
    """The frozen rule at horizon ``n_p``, through ``MonitorConfig.from_config`` and its guard rails.

    The config's own ``n_max`` / ``roster.n_pairs`` are null before the freeze, so a copy carries
    ``n_p`` in both; every other field is the frozen config's.  Refuses unless the four rule values
    equal protocol 11.5 item 4.
    """
    copy = json.loads(json.dumps(cfg))
    copy.setdefault('monitor', {})['n_max'] = int(n_p)
    copy.setdefault('roster', {})['n_pairs'] = int(n_p)
    mc = lab_monitor.MonitorConfig.from_config(copy, trial)
    got = {'alpha_gate': mc.alpha_gate, 'rho': mc.rho, 'delta': mc.delta, 'n_min': mc.n_min}
    if got != FROZEN_RULE:
        raise ReplayRefused('config rule %r differs from protocol 11.5 item 4 %r; the replay cannot '
                            'change any rule parameter' % (got, FROZEN_RULE))
    return mc


def radius_vector(mc: lab_monitor.MonitorConfig, n_p: int) -> numpy.ndarray:
    """``r(1..n_p)`` from ``lab_monitor.radius_table`` -- the call ``band`` makes, element by element."""
    rows = lab_monitor.radius_table(list(range(1, int(n_p) + 1)), mc)
    return numpy.asarray([row['radius'] for row in rows], dtype=numpy.float64)


# ------------------------------------------------------------------------------------------------
# the trial model
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TrialModel:
    trial: str
    n_s1: int
    n_s2: int
    pairs_available: int
    y: dict                  # arm -> float64 per-S1-task pilot outcome, or None (no pilot)
    rate: dict               # arm -> float pilot S1 rate
    success_rule: dict       # arm -> 'pilot' | open-model value
    cost_rule: str           # 'joint_within_task' | open-model value
    lat_a: numpy.ndarray     # cost pool, first latency source
    lat_b: numpy.ndarray     # cost pool, second latency source (joint: same task index)
    tiers: list
    inputs: dict             # digests and counts for the manifest


def build_trial_model(roster: Mapping, pilot: Pilot, cfg: Mapping, trial: str,
                      open_model: Optional[Mapping]) -> TrialModel:
    """[pure] Everything a replicate of ``trial`` needs, fixed before the first draw."""
    tiers = lab_enclosure.tiers_from_config(dict(cfg))
    arms = _trial_arms(cfg, trial)
    given = check_open_model(cfg, open_model, [trial])
    s1 = sorted(roster.get('S1') or [])
    s2 = sorted(roster.get('S2') or [])
    if len(set(s1) | set(s2)) != len(s1) + len(s2):
        raise ReplayRefused('the roster repeats a uid')
    position = {t: i for i, t in enumerate(pilot.tasks)}
    missing = [t for t in s1 if t not in position]
    if missing:
        raise ReplayRefused('%d S1 roster task(s) have no pilot row, e.g. %r' % (len(missing),
                                                                                 missing[:3]))
    idx = numpy.asarray([position[t] for t in s1], dtype=numpy.int64)
    y: dict = {}
    rate: dict = {}
    rule: dict = {}
    for arm in ('candidate', 'incumbent'):
        wf, server = arms[arm]['workflow'], arms[arm]['server']
        if server == PILOT_SERVER:
            y[arm] = pilot.success[wf][idx].astype(numpy.float64)
            rate[arm] = float(pilot.success[wf].sum()) / float(len(pilot.tasks))
            rule[arm] = 'pilot'
        else:
            choice = given['%s.%s.success' % (trial, arm)]
            ss = pilot.success['single_shot']
            rate[arm] = float(ss.sum()) / float(len(pilot.tasks))
            y[arm] = ss[idx].astype(numpy.float64) if choice == 'coder_single_shot_task_proxy' \
                else None
            rule[arm] = choice
    cost_key = '%s.cost_pair' % (trial,)
    if cost_key in given:
        cost_rule = given[cost_key]
        ok = numpy.flatnonzero(pilot.success['single_shot'] == 1)
        lat_a = lat_b = pilot.latency['single_shot'][ok]
    else:
        cost_rule = 'joint_within_task'
        both = numpy.flatnonzero((pilot.success[arms['candidate']['workflow']] == 1)
                                 & (pilot.success[arms['incumbent']['workflow']] == 1))
        lat_a = pilot.latency[arms['candidate']['workflow']][both]
        lat_b = pilot.latency[arms['incumbent']['workflow']][both]
    if len(lat_a) == 0:
        raise ReplayRefused('the %s cost pool of %s is empty' % (cost_rule, trial))
    inputs = {'arms': arms, 'success_rule': dict(rule), 'cost_rule': cost_rule,
              'cost_pool_size': int(len(lat_a)),
              'pilot_s1_rate': {arm: rate[arm] for arm in rate}}
    return TrialModel(trial=trial, n_s1=len(s1), n_s2=len(s2),
                      pairs_available=len(s1) // 2 + len(s2) // 2, y=y, rate=rate,
                      success_rule=rule, cost_rule=cost_rule, lat_a=lat_a, lat_b=lat_b,
                      tiers=tiers, inputs=inputs)


def order_indices(generator: numpy.random.Generator, n_s1: int, n_s2: int
                  ) -> tuple[numpy.ndarray, numpy.ndarray]:
    """The protocol 3.4 order as task indices (S1 tasks ``0..n_s1-1``, S2 tasks after them).

    Mirrors ``lab_design._generate`` draw for draw: one permutation per NON-EMPTY stratum in
    ``lab_design.STRATA`` order, consecutive pairs inside the stratum, then one permutation of the
    whole pairs.  Returns ``(position_1, position_2)`` over every enrollable pair, in enrollment order.
    """
    first: list[numpy.ndarray] = []
    second: list[numpy.ndarray] = []
    for stratum in lab_design.STRATA:
        n, offset = (n_s1, 0) if stratum == 'S1' else (n_s2, n_s1)
        if not n:
            continue
        perm = generator.permutation(n)
        whole = n // 2
        first.append(perm[0:2 * whole:2] + offset)
        second.append(perm[1:2 * whole:2] + offset)
    a = numpy.concatenate(first) if first else numpy.zeros(0, dtype=numpy.int64)
    b = numpy.concatenate(second) if second else numpy.zeros(0, dtype=numpy.int64)
    enrollment = generator.permutation(len(a))
    return a[enrollment], b[enrollment]


def _probabilities(model: TrialModel, arm: str, w: float, q: float) -> numpy.ndarray:
    """[pure] Per-task success probability of ``arm`` over all roster tasks (S1 then S2)."""
    y = model.y[arm]
    if y is None:
        s1 = numpy.full(model.n_s1, model.rate[arm], dtype=numpy.float64)
    else:
        s1 = w * y + (1.0 - w) * model.rate[arm]
    return numpy.concatenate([s1, numpy.full(model.n_s2, q, dtype=numpy.float64)])


def draw_replicate(model: TrialModel, cell: Mapping, generator: numpy.random.Generator,
                   p_cand: numpy.ndarray, p_inc: numpy.ndarray) -> dict:
    """One replicate's complete pair outcomes.  ``p_*`` are ``_probabilities`` (candidate shifted)."""
    n_p = int(cell['n_p'])
    pos1, pos2 = order_indices(generator, model.n_s1, model.n_s2)
    pos1, pos2 = pos1[:n_p], pos2[:n_p]
    coin = generator.integers(0, 2, size=n_p)
    cand_task = numpy.where(coin == 1, pos1, pos2)
    inc_task = numpy.where(coin == 1, pos2, pos1)
    u = generator.random((n_p, 2))
    success_c = (u[:, 0] < p_cand[cand_task]).astype(numpy.int8)
    success_i = (u[:, 1] < p_inc[inc_task]).astype(numpy.int8)
    k = generator.integers(0, len(model.lat_a), size=(n_p, 2))
    if model.cost_rule == 'joint_within_task':
        lat_c, lat_i = model.lat_a[k[:, 0]], model.lat_b[k[:, 0]]
    elif model.cost_rule == 'independent_single_shot_successes':
        lat_c, lat_i = model.lat_a[k[:, 0]], model.lat_b[k[:, 1]]
    elif model.cost_rule == 'same_task_single_shot_duplicate':
        lat_c = lat_i = model.lat_a[k[:, 0]]
    else:                                                      # pragma: no cover
        raise ReplayRefused('unknown cost rule %r' % (model.cost_rule,))
    z, d = pair_scores(success_c, success_i, lat_c, lat_i, model.tiers)
    return {'coin': coin, 'cand_task': cand_task, 'inc_task': inc_task, 'success_c': success_c,
            'success_i': success_i, 'lat_c': lat_c, 'lat_i': lat_i, 'z': z, 'd': d}


def pair_scores(success_c, success_i, lat_c, lat_i, tiers) -> tuple[numpy.ndarray, numpy.ndarray]:
    """``(Z, D)`` by ``winstats.compare`` itself, broadcast over pairs (protocol 6.3)."""
    sc = numpy.asarray(success_c, dtype=numpy.float64)
    si = numpy.asarray(success_i, dtype=numpy.float64)
    both = (sc > 0) & (si > 0)
    a = numpy.stack([sc, numpy.asarray(lat_c, dtype=numpy.float64)], -1)
    b = numpy.stack([si, numpy.asarray(lat_i, dtype=numpy.float64)], -1)
    eligible = numpy.stack([numpy.ones_like(both), both], -1)
    z, _ = winstats.compare(a, b, tiers, eligible)
    return z.astype(numpy.int8), (sc - si).astype(numpy.int8)


# ------------------------------------------------------------------------------------------------
# the rule, vectorised, and the scalar reference path
# ------------------------------------------------------------------------------------------------
def band_matrix(scores: numpy.ndarray, radius: numpy.ndarray, mc: lab_monitor.MonitorConfig
                ) -> tuple[numpy.ndarray, numpy.ndarray]:
    """``(L, U)`` at every completed prefix, the arithmetic of ``lab_monitor.band`` element-wise:
    ``lo = max(clip_lo, S/n - r)``, ``hi = min(clip_hi, S/n + r)`` with ``S`` an exact integer sum."""
    scores = numpy.atleast_2d(scores)
    n = numpy.arange(1, scores.shape[1] + 1, dtype=numpy.float64)
    mean = numpy.cumsum(scores, axis=1, dtype=numpy.int64).astype(numpy.float64) / n
    return (numpy.maximum(mc.clip_lo, mean - radius[:scores.shape[1]]),
            numpy.minimum(mc.clip_hi, mean + radius[:scores.shape[1]]))


def decide_matrix(z: numpy.ndarray, d: numpy.ndarray, radius: numpy.ndarray,
                  mc: lab_monitor.MonitorConfig) -> tuple[numpy.ndarray, numpy.ndarray]:
    """First decision of every replicate: ``(kind, n_star)``; ``n_star`` is 0 for ABSTAIN.

    ``lab_monitor.decide`` at each completed prefix n: nothing below ``n_min``; harm ``U_h < 0``
    first; deploy ``L_h > 0 and L_s > -delta`` at the same prefix; otherwise continue, and abstain at
    the horizon.  First crossing, no retention, no intersection (protocol 8.2-8.4).
    """
    z = numpy.atleast_2d(z)
    d = numpy.atleast_2d(d)
    lo_h, hi_h = band_matrix(z, radius, mc)
    lo_s, _ = band_matrix(d, radius, mc)
    n = numpy.arange(1, z.shape[1] + 1)
    eligible = n >= mc.n_min
    harm = (hi_h < 0.0) & eligible
    deploy = (lo_h > 0.0) & (lo_s > -mc.delta) & eligible
    fired = harm | deploy
    crossed = fired.any(axis=1)
    first = fired.argmax(axis=1)
    rows = numpy.arange(z.shape[0])
    kind = numpy.where(~crossed, ABSTAIN,
                       numpy.where(harm[rows, first], HARM_RETAIN, DEPLOY)).astype(numpy.int8)
    n_star = numpy.where(crossed, first + 1, 0).astype(numpy.int32)
    return kind, n_star


def monitor_decision(success_c, success_i, lat_c, lat_i, mc: lab_monitor.MonitorConfig,
                     tiers, *, pending_looks: bool = False) -> tuple[int, int]:
    """The SCALAR reference path: ``MonitorState`` + ``lab_enclosure.pair_enclosure`` + ``decide``.

    Every pair is enrolled at [-1, 1] and then collapsed by its two revealed episodes; ``decide`` runs
    after each collapse (and, with ``pending_looks``, also at the enroll look before it -- the
    protocol 8.3 trigger 1 look, used only by the control that checks it never changes the result).
    """
    state = lab_monitor.MonitorState(mc)
    for i in range(len(success_c)):
        state.enroll(i + 1)
        if pending_looks:
            decision = lab_monitor.decide(state, mc)
            if decision is not None:
                return _kind(decision), (decision.n if decision.kind != 'horizon_no_decision' else 0)
        cand = lab_enclosure.EpisodeView.reveal('candidate', int(success_c[i]), float(lat_c[i]), 0)
        inc = lab_enclosure.EpisodeView.reveal('incumbent', int(success_i[i]), float(lat_i[i]), 0)
        state.update(i + 1, lab_enclosure.pair_enclosure(cand, inc, tiers))
        decision = lab_monitor.decide(state, mc)
        if decision is not None:
            return _kind(decision), (decision.n if decision.kind != 'horizon_no_decision' else 0)
    raise ReplayRefused('the monitor reached the end of the sequence without a decision')


def monitor_decision_from_scores(z: Sequence[int], d: Sequence[int],
                                 mc: lab_monitor.MonitorConfig) -> tuple[int, int, list]:
    """``MonitorState``/``decide`` on a complete score sequence; also returns every band look.

    Used by the agreement control: each pair is enrolled and then set to the point enclosure
    ``(z_i, d_i)``.  Returns ``(kind, n_star, looks)`` with ``looks[n-1] = (L_h, U_h, L_s, U_s)``
    from ``MonitorState.bands`` up to and including the deciding prefix.
    """
    state = lab_monitor.MonitorState(mc)
    looks: list = []
    for i, (zi, di) in enumerate(zip(z, d)):
        state.enroll(i + 1)
        tier = -1 if zi == 0 else (0 if di != 0 else 1)
        state.update(i + 1, lab_enclosure.PairEnclosure(
            lab_enclosure.Enclosure(float(zi), float(zi)),
            lab_enclosure.Enclosure(float(di), float(di)), True, tier))
        bh, bs = state.bands()
        looks.append((bh.lo, bh.hi, bs.lo, bs.hi))
        decision = lab_monitor.decide(state, mc)
        if decision is not None:
            return (_kind(decision), (decision.n if decision.kind != 'horizon_no_decision' else 0),
                    looks)
    raise ReplayRefused('the monitor reached the end of the sequence without a decision')


def _kind(decision: lab_monitor.Decision) -> int:
    return _MONITOR_KIND[decision.kind]


# ------------------------------------------------------------------------------------------------
# summaries
# ------------------------------------------------------------------------------------------------
def wilson(x: int, n: int, z: float = WILSON_Z) -> Optional[list]:
    """[pure] Pointwise Wilson score interval for ``x`` of ``n``; None when ``n == 0``.

    The endpoints at ``x = 0`` and ``x = n`` are exactly 0 and 1 algebraically; they are set so, not
    left to a cancellation that returns 7e-18.
    """
    if n == 0:
        return None
    if not 0 <= x <= n:
        raise ReplayRefused('wilson(%r, %r): x outside [0, n]' % (x, n))
    p = x / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    lo = 0.0 if x == 0 else max(0.0, centre - half)
    hi = 1.0 if x == n else min(1.0, centre + half)
    return [lo, hi]


def quartiles(values: numpy.ndarray) -> Optional[dict]:
    """[pure] Q1 / median / Q3 (``numpy.percentile``, method ``linear``); None when empty."""
    if len(values) == 0:
        return None
    q1, med, q3 = numpy.percentile(numpy.asarray(values, dtype=numpy.float64), [25, 50, 75],
                                   method='linear')
    return {'n': int(len(values)), 'q1': float(q1), 'median': float(med), 'q3': float(q3)}


def run_cell(model: TrialModel, cell: Mapping, mc: lab_monitor.MonitorConfig,
             design_seed_base: int, *, crosscheck: int = 0,
             replicates: Optional[Sequence[int]] = None) -> dict:
    """Simulate one cell and return its table row.

    ``replicates`` (1-based) restricts the run to those replicates -- used only by the determinism
    control; the row then covers them alone.  ``crosscheck`` re-runs the first ``crosscheck``
    replicates through ``monitor_decision`` and REFUSES if any disagrees with ``decide_matrix``.
    """
    n_p = int(cell['n_p'])
    base = {k: cell[k] for k in ('ordinal', 'cell_id', 'trial', 'w', 'q', 's', 'n_p', 'n_p_role',
                                 'replicates')}
    if n_p > model.pairs_available:
        return dict(base, status='NOT_SIMULABLE', counts=None, rates=None, wilson95=None,
                    crossing_prefix=None, crosscheck=None, per_replicate_sha256=None,
                    reason='horizon %d exceeds the %d pairs of the realized roster (OPEN_ITEMS '
                           'horizon_above_roster_pairs, PROPOSED)' % (n_p, model.pairs_available))
    if mc.n_max != n_p:
        raise ReplayRefused('monitor horizon %d differs from the cell horizon %d' % (mc.n_max, n_p))
    radius = radius_vector(mc, n_p)
    p_cand = numpy.clip(_probabilities(model, 'candidate', cell['w'], cell['q']) + cell['s'],
                        0.0, 1.0)
    p_inc = _probabilities(model, 'incumbent', cell['w'], cell['q'])
    reps = list(range(1, int(cell['replicates']) + 1)) if replicates is None else list(replicates)
    kinds: list[numpy.ndarray] = []
    stars: list[numpy.ndarray] = []
    checked = mismatches = 0
    for start in range(0, len(reps), _BLOCK):
        block = reps[start:start + _BLOCK]
        draws = [draw_replicate(model, cell, replicate_generator(design_seed_base,
                                                                 int(cell['ordinal']), r),
                                p_cand, p_inc) for r in block]
        kind, n_star = decide_matrix(numpy.stack([x['z'] for x in draws]),
                                     numpy.stack([x['d'] for x in draws]), radius, mc)
        for j, x in enumerate(draws):
            if checked >= crosscheck:
                break
            checked += 1
            ref = monitor_decision(x['success_c'], x['success_i'], x['lat_c'], x['lat_i'], mc,
                                   model.tiers)
            if ref != (int(kind[j]), int(n_star[j])):
                mismatches += 1
        kinds.append(kind)
        stars.append(n_star)
    if mismatches:
        raise ReplayRefused('cell %s: %d of %d cross-checked replicates disagree with '
                            'lab_monitor.decide; nothing is written' % (cell['cell_id'], mismatches,
                                                                      checked))
    kind = numpy.concatenate(kinds) if kinds else numpy.zeros(0, dtype=numpy.int8)
    n_star = numpy.concatenate(stars) if stars else numpy.zeros(0, dtype=numpy.int32)
    total = int(len(kind))
    counts = {label: int((kind == code).sum()) for code, label in enumerate(LABELS)}
    if sum(counts.values()) != total:                          # pragma: no cover
        raise ReplayRefused('the three outcome counts do not exhaust the replicates')
    crossing = {'all': quartiles(n_star[kind != ABSTAIN]),
                'DEPLOY': quartiles(n_star[kind == DEPLOY]),
                'HARM_RETAIN': quartiles(n_star[kind == HARM_RETAIN])}
    digest = hashlib.sha256(kind.astype('<i1').tobytes() + n_star.astype('<i4').tobytes())
    return dict(base, status='SIMULATED', replicates_run=total, counts=counts,
                rates={label: counts[label] / total for label in LABELS},
                wilson95={label: wilson(counts[label], total) for label in LABELS},
                crossing_prefix=crossing,
                crosscheck={'replicates_checked': checked, 'mismatches': 0},
                per_replicate_sha256=digest.hexdigest())


# ------------------------------------------------------------------------------------------------
# the run, the table and the manifest
# ------------------------------------------------------------------------------------------------
def roster_rule_pairs(roster: Mapping) -> int:
    """[pure] protocol 3.3: ``floor(n_S1 / 2) + floor(n_S2 / 2)``."""
    return len(roster.get('S1') or []) // 2 + len(roster.get('S2') or []) // 2


def _file_sha256(path: Path) -> str:
    return lab_common.sha256_file(path)


_RULING_CITATION = re.compile(r'reviews/([A-Za-z0-9][A-Za-z0-9_.-]*\.md):([1-9][0-9]*)')


def check_ruling_citation(ruling: str) -> str:
    """Refuse unless ``ruling`` is exactly ``reviews/<file>.md:<line>`` naming an existing line of an
    existing file directly under ``REPO_ROOT/reviews`` (root-owned).  Returns ``ruling``.

    What this PERFORMS: the citation resolves.  What it does NOT: read the line, or decide that it is a
    root ruling on this outcome model -- a resolvable citation of an unrelated line passes, which is
    why the manifest records the citation for root to confirm and says so.
    """
    m = _RULING_CITATION.fullmatch(ruling) if isinstance(ruling, str) else None
    if m is None:
        raise ReplayRefused('a ruling must be cited as reviews/<file>.md:<line> and nothing else, got '
                            '%r' % (ruling,))
    path = REPO_ROOT / 'reviews' / m.group(1)
    try:
        lines = path.read_bytes().split(b'\n')
    except OSError:
        raise ReplayRefused('the cited ruling file reviews/%s does not exist' % (m.group(1),)) from None
    if lines and lines[-1] == b'':
        lines.pop()
    if int(m.group(2)) > len(lines):
        raise ReplayRefused('reviews/%s has %d lines; the ruling cites line %s'
                            % (m.group(1), len(lines), m.group(2)))
    return ruling


def run_replay(roster: Mapping, pilot: Pilot, cfg: Mapping, *, realized_n_p: int,
               out_dir: 'str | Path', open_model: Optional[Mapping],
               cells: Optional[Sequence[Mapping]] = None, crosscheck_per_cell: int = 2,
               ruling: Optional[str] = None) -> dict:
    """Run the replay, write the table and then the manifest, both write-once.  Returns the manifest.

    ``cells`` None means the exhaustive protocol grid (``grid.kind = full_432``); anything else is a
    SUBSET run, labelled as such in both files so it can never pass for the 11.5 table.
    """
    started = time.monotonic()
    started_utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if ruling is not None:
        check_ruling_citation(ruling)             # before anything runs; RULED needs a real citation
    if isinstance(realized_n_p, bool) or not isinstance(realized_n_p, int):
        raise ReplayRefused('realized_n_p must be an int')
    if realized_n_p != roster_rule_pairs(roster):
        raise ReplayRefused('realized N_P %d differs from floor(n_S1/2)+floor(n_S2/2) = %d on the '
                            'roster given' % (realized_n_p, roster_rule_pairs(roster)))
    design_seed_base = cfg.get('design_seed_base') if isinstance(cfg, Mapping) else None
    if isinstance(design_seed_base, bool) or not isinstance(design_seed_base, int):
        raise ReplayRefused('config.design_seed_base must be an int')
    full = cells is None
    grid = enumerate_cells(realized_n_p) if full else [dict(c) for c in cells]
    if full:
        check_grid(grid, realized_n_p)
    if len({c['ordinal'] for c in grid}) != len(grid):
        raise ReplayRefused('two cells share an ordinal, so two cells would share seeds')
    trials = sorted({c['trial'] for c in grid})
    given = check_open_model(cfg, open_model, trials)
    models = {t: build_trial_model(roster, pilot, cfg, t, {k: v for k, v in given.items()
                                                           if k.startswith(t + '.')})
              for t in trials}
    rows = []
    for cell in grid:
        mc = frozen_monitor_config(cfg, cell['trial'], int(cell['n_p']))
        rows.append(run_cell(models[cell['trial']], cell, mc, design_seed_base,
                             crosscheck=crosscheck_per_cell))
    table = {'schema': TABLE_SCHEMA, 'protocol_section': '11.5',
             'grid_kind': 'full_432' if full else 'subset', 'labels': list(LABELS),
             'realized_n_p': realized_n_p, 'rows': rows}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    table_sha = lab_common.write_json_atomic(out_dir / TABLE_NAME, table, durable=True)
    script = Path(__file__).resolve()
    status = 'RULED' if ruling else 'PROPOSED'
    manifest = {
        'schema': MANIFEST_SCHEMA, 'protocol_section': '11.5', 'plan_stage': 8,
        'planning_member': 'planning_sha256 (lab_common.FREEZE_BUNDLE_KEYS)',
        'script': {'file': 'experiments/live_ab/lab_replay.py', 'sha256': _file_sha256(script)},
        'dependencies_sha256': {name: _file_sha256(HERE / name) for name in
                                ('lab_monitor.py', 'lab_design.py', 'lab_enclosure.py')},
        'winstats_sha256': _file_sha256(Path(winstats.__file__).resolve()),
        'seed': {'design_seed_base': design_seed_base, 'stream_tag': REPLAY_STREAM_TAG,
                 'rule': SEED_RULE_TEXT, 'rule_sha256': lab_common.sha256_text(SEED_RULE_TEXT)},
        'inputs': {'roster_sha256': lab_common.sha256_canonical(
                       {'S1': sorted(roster.get('S1') or []), 'S2': sorted(roster.get('S2') or [])}),
                   'n_S1': len(roster.get('S1') or []), 'n_S2': len(roster.get('S2') or []),
                   'roster_pairs': roster_rule_pairs(roster), 'realized_n_p': realized_n_p,
                   'pilot_sha256': pilot.sha256, 'pilot_tasks': len(pilot.tasks),
                   'config_rule_block_sha256': lab_common.rule_block_sha256(dict(cfg)),
                   'trial_models': {t: models[t].inputs for t in trials}},
        'rule': dict(FROZEN_RULE, rule_id=lab_monitor.RULE_ID, clip=[-1.0, 1.0],
                     variance_process='n', relative_tolerance=0.05,
                     looks='completed prefixes 1..N_P (protocol 11.5 item 4)'),
        'grid': {'kind': 'full_432' if full else 'subset', 'cells': len(grid),
                 'replicates_planned': sum(int(c['replicates']) for c in grid),
                 'rows_simulated': sum(1 for r in rows if r['status'] == 'SIMULATED'),
                 'rows_not_simulable': sum(1 for r in rows if r['status'] == 'NOT_SIMULABLE')},
        'open_outcome_model': {'value': given, 'status': status, 'needs': None if ruling else 'root',
                               'ruling': ruling,
                               'ruling_check': ('the citation resolves to an existing line of a file '
                                                'under reviews/; whether that line rules on this model '
                                                'is not checked here' if ruling else None),
                               'proposal': PROPOSED_OPEN_MODEL,
                               'proposal_text': PROPOSAL_TEXT,
                               'alternatives': {k: list(v) for k, v in OPEN_MODEL_CHOICES.items()},
                               'equals_proposal': all(PROPOSED_OPEN_MODEL.get(k) == v
                                                      for k, v in given.items())},
        'readings': list(READINGS), 'open_items': list(OPEN_ITEMS),
        'crosscheck': {'per_cell': crosscheck_per_cell,
                       'replicates_checked': sum((r['crosscheck'] or {}).get('replicates_checked', 0)
                                                 for r in rows),
                       'mismatches': 0},
        'output': {'file': TABLE_NAME, 'sha256': table_sha},
        'timing': {'started_utc': started_utc,
                   'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   'wall_s': round(time.monotonic() - started, 3)},
    }
    lab_common.write_json_atomic(out_dir / MANIFEST_NAME, manifest, durable=True)
    return manifest


def verify_manifest(out_dir: 'str | Path') -> dict:
    """Recompute the output and script digests the manifest names; raise ``ReplayRefused`` on any
    difference.  A flipped byte in the table, or a script edited after the run, is refused."""
    out_dir = Path(out_dir)
    try:
        manifest = json.loads((out_dir / MANIFEST_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ReplayRefused('manifest unreadable: %s' % (type(exc).__name__,)) from None
    table_sha = _file_sha256(out_dir / manifest['output']['file'])
    if table_sha != manifest['output']['sha256']:
        raise ReplayRefused('table sha256 %s differs from the manifest %s'
                            % (table_sha, manifest['output']['sha256']))
    script_sha = _file_sha256(Path(__file__).resolve())
    if script_sha != manifest['script']['sha256']:
        raise ReplayRefused('lab_replay.py sha256 %s differs from the manifest %s'
                            % (script_sha, manifest['script']['sha256']))
    if manifest['seed']['rule_sha256'] != lab_common.sha256_text(manifest['seed']['rule']):
        raise ReplayRefused('the seed rule text does not match its digest')
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI for the real stage-8 run.  Every input is explicit; nothing is defaulted."""
    ap = argparse.ArgumentParser(description='protocol 11.5 extended CPU replay (plan stage 8)')
    ap.add_argument('--roster', required=True, help='realized roster.json (S1, S2 uid lists)')
    ap.add_argument('--pilot', required=True, help='results/local_stream/episodes_flat.csv')
    ap.add_argument('--config', required=True, help='the frozen config.json')
    ap.add_argument('--realized-n-p', required=True, type=int)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--open-model', required=True,
                    help="'proposed' for PROPOSED_OPEN_MODEL (recorded as PROPOSED), or a JSON object")
    ap.add_argument('--ruling', default=None,
                    help='reviews/<file>.md:<line> citation of a root ruling on the open model')
    ap.add_argument('--crosscheck-per-cell', type=int, default=2)
    args = ap.parse_args(argv)
    open_model = dict(PROPOSED_OPEN_MODEL) if args.open_model == 'proposed' \
        else json.loads(args.open_model)
    roster = json.loads(Path(args.roster).read_text(encoding='utf-8'))
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    manifest = run_replay(roster, load_pilot_csv(args.pilot), cfg, realized_n_p=args.realized_n_p,
                          out_dir=args.out_dir, open_model=open_model,
                          crosscheck_per_cell=args.crosscheck_per_cell, ruling=args.ruling)
    print(json.dumps({'output_sha256': manifest['output']['sha256'],
                      'script_sha256': manifest['script']['sha256']}))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
