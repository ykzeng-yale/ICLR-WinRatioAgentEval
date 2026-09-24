"""Deterministic, write-once schedules for pre-freeze stages 4 and 5 (protocol 5.8 items 3 and 4).

Root, 2026-09-23 20:40 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``, item 2): complete the
missing executable drivers and "show each driver consumes the frozen schedule".  The plan rows say the
schedules do not exist: stage 5 "orientation: deterministic prospective 15/15 schedule, NOT YET WRITTEN"
(``results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json`` ``stage_5_orientation``), and stage 4's
driver "is not identified at HEAD".  This module writes the two schedules and nothing else: it starts
no server, sends no request and reads no outcome.  A driver consumes a schedule by iterating its
``consumption_order``; every row id it will ever touch is in the file before the first request.

STAGE 4 -- duration calibration (protocol 5.8(3), ``protocol_FINAL.md:1209-1214``; plan stage 4 rows):
8 cells = {single_shot, self_test_repair} x {coder, t3} x concurrency {1, 2}, 30 episodes each
(6 smoke tasks x 5 repetitions; ``config.json`` ``prefreeze.calibration_plan``); a concurrency-2 cell
runs 15 DISJOINT pairs (root 2026-09-21 19:29: "they provide only 15 pairs if partitioned into disjoint
pairs", ``reviews/live_prefreeze_root_decisions_20260921_1929.md:15``).  Execution units: 120 solo
episodes and 60 pairs, 180 units.  Session rows: one start, one ``/props`` GET and (OD14) one
SERVER_SMOKE per server, ``/metrics`` per server at session start and at the stage-4/5 boundary (plan
stage 4 ``non_generation_GETs``: 6).

STAGE 5 -- side-by-side calibration (protocol 5.8(4), ``protocol_FINAL.md:1215-1223``; plan stage 5
rows): 4 contrasts x 30 pairs (the 6 x 5 task/repetition coordinates), 240 new episodes; solo arms are
LINKED to the stage-4 concurrency-1 rows of the same task/model/workflow/repetition (root 19:29 :15,
"explicit task/model/workflow/replicate links"); concurrency-2 cells are never reused.  Orientation
(which arm sits at position 1, hence worker slot 0: ``config.json`` ``execution.worker_index_rule``) is
balanced 15/15 within each contrast (root 19:29 :15).  This module strengthens that to a design that is
ALSO balanced per repetition (3/3 in each of the 5 repetitions) and within one per task (each task has
2 or 3 candidate-first repetitions), drawn by seeded rejection sampling.  READING S1 (stated): a
side-by-side pair runs both arms of the contrast on the SAME smoke task and repetition coordinate, so
its ratio and the solo ratio it is divided by refer to one task.  OBSERVATION (not decided here): T4's
two arms are one system, so both of its solo links name the same stage-4 row and its solo ratio is 1 by
construction; the flag ``solo_links_identical`` records it.

THE SEED DERIVATION (stated before any schedule is written).  Stage 4 draws from
``Generator(PCG64(SeedSequence([design_seed_base, 583])))`` and stage 5 from ``[design_seed_base, 584]``
(583/584 name 5.8 items 3/4).  Neither can equal a trial order seed ``[design_seed_base, e]``, e in 1..4,
nor a replay seed ``[design_seed_base, 1105, c, r]`` (lab_replay).  Draw order, fixed:
stage 4 -- for each concurrency-2 cell in cell order, ``permutation(30)`` of its coordinates (task-major
order), consecutive coordinates forming pairs 1..15 (first = position 1); then ``permutation(180)`` of
the units (solo units in cell/task/repetition order, then pair units in cell/pair order).
stage 5 -- for each contrast in T1, T2, T3, T4 order, attempts k = 1, 2, ...: for repetitions 1..5,
``choice(6, size=3, replace=False)`` picks the tasks whose candidate is at position 1; the first attempt
whose every task has 2 or 3 candidate-first repetitions is kept (``attempts`` records k); then
``permutation(120)`` of the pair units (contrast, task, repetition order).

OPEN DECISIONS, carried as explicit parameters, never defaulted (plan ``open_decisions_for_root``).
``PLAN_PROPOSED_OPEN_DECISIONS`` holds the plan's ``default_on_explicit_acceptance`` values, each
labelled PROPOSED; the plan itself says "adopted only on explicit root acceptance of this plan; root
silence adopts nothing".  A schedule written with them says ``status: PROPOSED`` unless a ruling
citation is supplied.
* OD1 -- pre-``c_max`` request timeout and censoring: 180 s; a call that hits it is right-censored,
  ``c_max`` is reported censored, nothing is promoted, and stage 5 does not start.
* OD2 -- trial retry rules in stages 1-5: ``no_retries`` (one wire attempt per logical call): wire caps
  602 (stage 4) and 420 (stage 5); ``trial_retry_rules`` gives 1,802 and 1,260.
* OD14 -- one SERVER_SMOKE per server start made with a golden object: ``server_smoke_per_start`` (2 in
  stage 4; stage 5 starts no server).

WRITE-ONCE AND TAMPER REFUSAL.  ``write_schedule`` goes through ``lab_common.write_json_atomic``
(refuses different bytes at an existing path).  Each schedule carries ``schedule_sha256`` over its
canonical body; ``load_schedule`` recomputes it, re-runs the invariant checks and, when given, compares
the file's byte digest, so a flipped byte is refused on reload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Mapping, Optional

import numpy

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402


STAGE4_SCHEMA = 'live_ab/stage4_schedule-v1'
STAGE5_SCHEMA = 'live_ab/stage5_schedule-v1'
STAGE4_SEED_TAG = 583
STAGE5_SEED_TAG = 584
WORKFLOWS: tuple[str, ...] = ('single_shot', 'self_test_repair')
MODELS: tuple[str, ...] = ('coder', 't3')
CONCURRENCY: tuple[int, ...] = (1, 2)
REPETITIONS: int = 5
CONTRASTS: tuple[str, ...] = ('T1', 'T2', 'T3', 'T4')
PAIRS_PER_CONTRAST: int = 30
CANDIDATE_FIRST_PER_CONTRAST: int = 15

PLAN_FILE = 'results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json'

#: The allowed values of each open decision.  The first element of each tuple is NOT a default.
OD_CHOICES: dict[str, dict] = {
    'OD1': {'request_timeout_s': 'int >= 1', 'censoring': ('right_censor_no_promotion',)},
    'OD2': {'retries': ('no_retries', 'trial_retry_rules')},
    'OD14': {'server_smoke': ('server_smoke_per_start', 'no_server_smoke')},
}
#: The plan's values (``default_on_explicit_acceptance``), labelled PROPOSED.  Never used unless passed.
PLAN_PROPOSED_OPEN_DECISIONS: dict[str, dict] = {
    'OD1': {'request_timeout_s': 180, 'censoring': 'right_censor_no_promotion',
            'status': 'PROPOSED', 'source': PLAN_FILE + ' open_decisions_for_root OD1'},
    'OD2': {'retries': 'no_retries', 'status': 'PROPOSED',
            'source': PLAN_FILE + ' open_decisions_for_root OD2'},
    'OD14': {'server_smoke': 'server_smoke_per_start', 'status': 'PROPOSED',
             'source': PLAN_FILE + ' open_decisions_for_root OD14'},
}
#: ``max_connection_retries`` under each OD2 reading (``config.json`` ``execution.max_connection_retries``
#: is 2, three tries).
_RETRIES = {'no_retries': 0, 'trial_retry_rules': 2}


class ScheduleRefused(lab_common.LabError):
    """A schedule may not be generated from these inputs, or a stored one may not be used."""


# ------------------------------------------------------------------------------------------------
# inputs
# ------------------------------------------------------------------------------------------------
def check_open_decisions(open_decisions: Optional[Mapping]) -> dict:
    """[pure] Refuse unless OD1, OD2 and OD14 are all given with allowed values; return a copy.

    Each entry carries a ``status`` (``PROPOSED`` or ``RULED``) and a ``source``; a ``RULED`` entry
    must name its ruling in ``source``.
    """
    if not isinstance(open_decisions, Mapping):
        raise ScheduleRefused('open decisions OD1, OD2 and OD14 must be passed explicitly (the plan '
                              'values are PLAN_PROPOSED_OPEN_DECISIONS, status PROPOSED)')
    if sorted(open_decisions) != sorted(OD_CHOICES):
        raise ScheduleRefused('open decisions must be exactly %r, got %r'
                              % (sorted(OD_CHOICES), sorted(open_decisions)))
    out = json.loads(json.dumps(open_decisions))
    for od, entry in out.items():
        if not isinstance(entry, dict) or entry.get('status') not in ('PROPOSED', 'RULED') \
                or not isinstance(entry.get('source'), str) or not entry['source']:
            raise ScheduleRefused('%s needs a status in {PROPOSED, RULED} and a source' % (od,))
        for key, allowed in OD_CHOICES[od].items():
            value = entry.get(key)
            if allowed == 'int >= 1':
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    raise ScheduleRefused('%s.%s must be an int >= 1, got %r' % (od, key, value))
            elif value not in allowed:
                raise ScheduleRefused('%s.%s = %r is not one of %r' % (od, key, value, allowed))
    return out


def _calibration_inputs(cfg: Mapping) -> tuple[list, dict]:
    """The six smoke tasks and the frozen calibration plan, cross-checked against the protocol."""
    plan = ((cfg.get('prefreeze') or {}).get('calibration_plan') or {}) if isinstance(cfg, Mapping) \
        else {}
    want = {'repetitions': REPETITIONS, 'smoke_tasks': 6, 'workflows': len(WORKFLOWS),
            'models': len(MODELS), 'concurrency_levels': len(CONCURRENCY), 'episodes': 240}
    if {k: plan.get(k) for k in want} != want:
        raise ScheduleRefused('config prefreeze.calibration_plan %r differs from protocol 5.8(3) %r'
                              % (plan, want))
    tasks = list((cfg.get('roster') or {}).get('smoke_tasks') or [])
    if len(tasks) != 6 or len(set(tasks)) != 6 or not all(isinstance(t, str) for t in tasks):
        raise ScheduleRefused('config roster.smoke_tasks must list six distinct uids')
    servers = cfg.get('servers') or {}
    if sorted(servers) != sorted(MODELS):
        raise ScheduleRefused('config servers %r differ from %r' % (sorted(servers), MODELS))
    return tasks, plan


def _seeded(design_seed_base: int, tag: int) -> numpy.random.Generator:
    if isinstance(design_seed_base, bool) or not isinstance(design_seed_base, int) \
            or design_seed_base < 1:
        raise ScheduleRefused('design_seed_base must be a positive int')
    return numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(
        [int(design_seed_base), int(tag)])))


def _status(ods: Mapping) -> str:
    return 'RULED' if all(e['status'] == 'RULED' for e in ods.values()) else 'PROPOSED'


def _seal(body: dict) -> dict:
    out = dict(body)
    out.pop('schedule_sha256', None)
    out['schedule_sha256'] = lab_common.sha256_canonical(out)
    return out


# ------------------------------------------------------------------------------------------------
# stage 4
# ------------------------------------------------------------------------------------------------
def stage4_cells() -> list[dict]:
    """[pure] The 8 cells in their fixed order: workflow, then model, then concurrency."""
    cells = []
    for wf in WORKFLOWS:
        for model in MODELS:
            for conc in CONCURRENCY:
                cells.append({'cell': 'c%d' % (len(cells) + 1), 'workflow': wf, 'server': model,
                              'concurrency': conc})
    return cells


def stage4_schedule(cfg: Mapping, design_seed_base: int, open_decisions: Mapping) -> dict:
    """[pure] The stage-4 schedule (protocol 5.8(3)).  Deterministic in its three inputs."""
    ods = check_open_decisions(open_decisions)
    tasks, _ = _calibration_inputs(cfg)
    gen = _seeded(design_seed_base, STAGE4_SEED_TAG)
    timeout = ods['OD1']['request_timeout_s']
    retries = _RETRIES[ods['OD2']['retries']]
    coords = [(t, r) for t in tasks for r in range(1, REPETITIONS + 1)]
    cells = stage4_cells()
    rows: list[dict] = []
    episode_of: dict[tuple, str] = {}
    for cell in cells:
        for task, rep in coords:
            row_id = 's4.ep.%03d' % (len(episode_of) + 1)
            episode_of[(cell['cell'], task, rep)] = row_id
            rows.append({'row_id': row_id, 'kind': 'episode', 'cell': cell['cell'],
                         'workflow': cell['workflow'], 'server': cell['server'],
                         'concurrency': cell['concurrency'], 'task_uid': task, 'repetition': rep,
                         'request_timeout_s': timeout, 'max_connection_retries': retries})
    units: list[dict] = []
    for cell in cells:
        if cell['concurrency'] != 1:
            continue
        for task, rep in coords:
            units.append({'unit_id': None, 'kind': 'solo', 'cell': cell['cell'],
                          'episodes': [episode_of[(cell['cell'], task, rep)]]})
    for cell in cells:
        if cell['concurrency'] != 2:
            continue
        perm = gen.permutation(len(coords))
        for p in range(len(coords) // 2):
            a, b = coords[int(perm[2 * p])], coords[int(perm[2 * p + 1])]
            units.append({'unit_id': None, 'kind': 'pair', 'cell': cell['cell'], 'pair': p + 1,
                          'episodes': [episode_of[(cell['cell'],) + a],
                                       episode_of[(cell['cell'],) + b]]})
    for i, unit in enumerate(units):
        unit['unit_id'] = 's4.u.%03d' % (i + 1)
    order = gen.permutation(len(units))
    by_id = {r['row_id']: r for r in rows}
    for seq, k in enumerate(order):
        unit = units[int(k)]
        unit['seq'] = seq + 1
        for position, ep in enumerate(unit['episodes'], start=1):
            by_id[ep].update(unit_id=unit['unit_id'], position=position,
                             worker_index=position - 1)
    session: list[dict] = []
    for model in MODELS:
        session.append({'row_id': 's4.srv.start.%s' % model, 'kind': 'server_start', 'server': model})
    for model in MODELS:
        session.append({'row_id': 's4.get.props.%s' % model, 'kind': 'get', 'endpoint': '/props',
                        'server': model, 'rule': 'plan globals.non_generation_GET_rule (PROPOSED)'})
    if ods['OD14']['server_smoke'] == 'server_smoke_per_start':
        for model in MODELS:
            session.append({'row_id': 's4.smoke.%s' % model, 'kind': 'server_smoke',
                            'server': model, 'wire_attempts': 1})
    for model in MODELS:
        session.append({'row_id': 's4.get.metrics_start.%s' % model, 'kind': 'get',
                        'endpoint': '/metrics', 'server': model,
                        'rule': 'plan globals.non_generation_GET_rule (PROPOSED)'})
    tail = [{'row_id': 's4.get.metrics_boundary.%s' % model, 'kind': 'get', 'endpoint': '/metrics',
             'server': model, 'rule': 'plan globals.non_generation_GET_rule (PROPOSED)'}
            for model in MODELS]
    units_in_order = sorted(units, key=lambda u: u['seq'])
    consumption = [r['row_id'] for r in session] + [u['unit_id'] for u in units_in_order] + \
        [r['row_id'] for r in tail]
    smoke = sum(1 for r in session if r['kind'] == 'server_smoke')
    tries = retries + 1
    body = {
        'schema': STAGE4_SCHEMA, 'stage': 4, 'protocol': '5.8(3)',
        'status': _status(ods), 'open_decisions': ods,
        'seed': {'design_seed_base': int(design_seed_base), 'entropy': [int(design_seed_base),
                                                                        STAGE4_SEED_TAG],
                 'rule': 'lab_schedules module docstring, THE SEED DERIVATION'},
        'smoke_tasks': tasks, 'cells': cells,
        'rows': session + rows + tail, 'units': units,
        'consumption_order': consumption,
        'censoring': ods['OD1']['censoring'],
        'counts': {'episodes': len(rows), 'solo_units': sum(1 for u in units if u['kind'] == 'solo'),
                   'pair_units': sum(1 for u in units if u['kind'] == 'pair'),
                   'server_smoke': smoke, 'gets': sum(1 for r in session + tail if r['kind'] == 'get'),
                   'logical_calls_min': 120 * 1 + 120 * 2, 'logical_calls_max': 120 * 1 + 120 * 4,
                   'wire_attempt_cap': 600 * tries + smoke},
    }
    return _seal(body)


def check_stage4(schedule: Mapping) -> None:
    """[pure] Raise ``ScheduleRefused`` unless every stage-4 invariant holds."""
    if schedule.get('schema') != STAGE4_SCHEMA:
        raise ScheduleRefused('not a stage-4 schedule')
    ods = check_open_decisions(schedule.get('open_decisions'))
    rows = schedule['rows']
    ids = [r['row_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ScheduleRefused('a row id repeats')
    episodes = [r for r in rows if r['kind'] == 'episode']
    if len(episodes) != 240:
        raise ScheduleRefused('%d episode rows, protocol 5.8(3) fixes 240' % (len(episodes),))
    tasks = schedule['smoke_tasks']
    coords = {(t, r) for t in tasks for r in range(1, REPETITIONS + 1)}
    cells = {c['cell']: c for c in schedule['cells']}
    if [dict(c) for c in schedule['cells']] != stage4_cells():
        raise ScheduleRefused('the cells differ from the 8 cells of protocol 5.8(3)')
    for name, cell in cells.items():
        mine = [e for e in episodes if e['cell'] == name]
        got = {(e['task_uid'], e['repetition']) for e in mine}
        if len(mine) != 30 or got != coords:
            raise ScheduleRefused('cell %s does not cover the 6 x 5 coordinates once' % (name,))
        if any((e['workflow'], e['server'], e['concurrency'])
               != (cell['workflow'], cell['server'], cell['concurrency']) for e in mine):
            raise ScheduleRefused('an episode of cell %s carries another cell\'s arm' % (name,))
    units = schedule['units']
    unit_ids = [u['unit_id'] for u in units]
    if len(unit_ids) != len(set(unit_ids)) or len(units) != 180:
        raise ScheduleRefused('%d units (180 expected) or a repeated unit id' % (len(units),))
    ep_by_id = {e['row_id']: e for e in episodes}
    covered: list[str] = []
    for u in units:
        cell = cells.get(u['cell'])
        want = 1 if u['kind'] == 'solo' else 2
        if cell is None or len(u['episodes']) != want or cell['concurrency'] != want:
            raise ScheduleRefused('unit %s does not match its cell\'s concurrency' % (u['unit_id'],))
        for position, ep in enumerate(u['episodes'], start=1):
            e = ep_by_id.get(ep)
            if e is None or e['cell'] != u['cell'] or e.get('unit_id') != u['unit_id'] \
                    or e.get('position') != position or e.get('worker_index') != position - 1:
                raise ScheduleRefused('unit %s names episode %r inconsistently' % (u['unit_id'], ep))
            covered.append(ep)
    if sorted(covered) != sorted(ep_by_id):
        raise ScheduleRefused('the units are not a partition of the 240 episodes (disjoint pairs)')
    if sorted(u['seq'] for u in units) != list(range(1, 181)):
        raise ScheduleRefused('the unit execution order is not a permutation of 1..180')
    retries = _RETRIES[ods['OD2']['retries']]
    for e in episodes:
        if e['request_timeout_s'] != ods['OD1']['request_timeout_s'] \
                or e['max_connection_retries'] != retries:
            raise ScheduleRefused('episode %s disagrees with OD1/OD2' % (e['row_id'],))
    smoke = [r for r in rows if r['kind'] == 'server_smoke']
    want_smoke = 2 if ods['OD14']['server_smoke'] == 'server_smoke_per_start' else 0
    if len(smoke) != want_smoke:
        raise ScheduleRefused('%d SERVER_SMOKE rows, OD14 gives %d' % (len(smoke), want_smoke))
    session_ids = [r['row_id'] for r in rows if r['kind'] != 'episode']
    if sorted(schedule['consumption_order']) != sorted(session_ids + unit_ids):
        raise ScheduleRefused('consumption_order does not name every session row and unit once')
    if schedule['counts']['wire_attempt_cap'] != 600 * (retries + 1) + want_smoke:
        raise ScheduleRefused('the wire cap is not 600 x tries + SERVER_SMOKE')


# ------------------------------------------------------------------------------------------------
# stage 5
# ------------------------------------------------------------------------------------------------
def _orientation(gen: numpy.random.Generator) -> tuple[numpy.ndarray, int]:
    """A 6 x 5 0/1 matrix (task x repetition, 1 = candidate at position 1): every repetition column
    has exactly 3 ones and every task row 2 or 3.  Seeded rejection sampling; returns the attempts."""
    attempts = 0
    while True:
        attempts += 1
        m = numpy.zeros((6, REPETITIONS), dtype=numpy.int8)
        for r in range(REPETITIONS):
            m[gen.choice(6, size=3, replace=False), r] = 1
        if set(m.sum(axis=1).tolist()) <= {2, 3}:
            return m, attempts
        if attempts >= 10_000:                                  # pragma: no cover
            raise ScheduleRefused('orientation rejection sampling did not terminate')


def _contrast_arms(cfg: Mapping, contrast: str) -> dict:
    spec = (cfg.get('trials') or {}).get(contrast)
    if not isinstance(spec, Mapping):
        raise ScheduleRefused('config.trials has no %r' % (contrast,))
    arms = {}
    for arm in ('candidate', 'incumbent'):
        a = spec.get(arm) or {}
        if a.get('workflow') not in WORKFLOWS or a.get('server') not in MODELS:
            raise ScheduleRefused('config.trials.%s.%s is malformed' % (contrast, arm))
        arms[arm] = {'workflow': a['workflow'], 'server': a['server']}
    return arms


def stage5_schedule(cfg: Mapping, design_seed_base: int, open_decisions: Mapping,
                    stage4: Mapping) -> dict:
    """[pure] The stage-5 schedule (protocol 5.8(4)), linked to ``stage4`` (which is checked)."""
    ods = check_open_decisions(open_decisions)
    check_stage4(stage4)
    if lab_common.sha256_canonical({k: v for k, v in stage4.items() if k != 'schedule_sha256'}) \
            != stage4.get('schedule_sha256'):
        raise ScheduleRefused('the stage-4 schedule does not match its own digest')
    if stage4['open_decisions'] != ods:
        raise ScheduleRefused('stage 5 must be generated under the same open decisions as stage 4')
    tasks, _ = _calibration_inputs(cfg)
    if list(stage4['smoke_tasks']) != tasks:
        raise ScheduleRefused('the stage-4 schedule was written for other smoke tasks')
    solo = {(r['workflow'], r['server'], r['task_uid'], r['repetition']): r['row_id']
            for r in stage4['rows'] if r['kind'] == 'episode' and r['concurrency'] == 1}
    gen = _seeded(design_seed_base, STAGE5_SEED_TAG)
    retries = _RETRIES[ods['OD2']['retries']]
    rows: list[dict] = []
    units: list[dict] = []
    orientation: dict = {}
    for contrast in CONTRASTS:
        arms = _contrast_arms(cfg, contrast)
        m, attempts = _orientation(gen)
        orientation[contrast] = {'matrix_task_by_repetition': m.tolist(), 'attempts': attempts}
        for ti, task in enumerate(tasks):
            for rep in range(1, REPETITIONS + 1):
                cand_first = bool(m[ti, rep - 1])
                unit_id = 's5.u.%03d' % (len(units) + 1)
                eps = []
                for arm in ('candidate', 'incumbent'):
                    position = 1 if (arm == 'candidate') == cand_first else 2
                    wf, server = arms[arm]['workflow'], arms[arm]['server']
                    row_id = 's5.ep.%03d' % (len(rows) + 1)
                    rows.append({'row_id': row_id, 'kind': 'episode', 'contrast': contrast,
                                 'arm': arm, 'workflow': wf, 'server': server, 'task_uid': task,
                                 'repetition': rep, 'unit_id': unit_id, 'position': position,
                                 'worker_index': position - 1,
                                 'solo_link': solo[(wf, server, task, rep)],
                                 'max_connection_retries': retries})
                    eps.append((position, row_id))
                links = [r['solo_link'] for r in rows[-2:]]
                units.append({'unit_id': unit_id, 'kind': 'pair', 'contrast': contrast,
                              'task_uid': task, 'repetition': rep,
                              'candidate_at_position_1': cand_first,
                              'episodes': [row_id for _, row_id in sorted(eps)],
                              'solo_links_identical': links[0] == links[1]})
    order = gen.permutation(len(units))
    for seq, k in enumerate(order):
        units[int(k)]['seq'] = seq + 1
    tail = [{'row_id': 's5.get.metrics_end.%s' % model, 'kind': 'get', 'endpoint': '/metrics',
             'server': model, 'rule': 'plan globals.non_generation_GET_rule (PROPOSED)'}
            for model in MODELS]
    consumption = [u['unit_id'] for u in sorted(units, key=lambda u: u['seq'])] + \
        [r['row_id'] for r in tail]
    body = {
        'schema': STAGE5_SCHEMA, 'stage': 5, 'protocol': '5.8(4)',
        'status': _status(ods), 'open_decisions': ods,
        'seed': {'design_seed_base': int(design_seed_base), 'entropy': [int(design_seed_base),
                                                                        STAGE5_SEED_TAG],
                 'rule': 'lab_schedules module docstring, THE SEED DERIVATION'},
        'stage4_schedule_sha256': stage4['schedule_sha256'],
        'start_condition': 'stage 4 produced an UNCENSORED c_max (OD1); otherwise stage 5 does not '
                           'start',
        'request_timeout_s': {'rule': 'max(180, 30*ceil(4*c_max/30))', 'value': None,
                              'status': 'CONDITIONAL on OD1 (promoted once from stage 4)'},
        'smoke_tasks': tasks, 'orientation': orientation,
        'rows': rows + tail, 'units': units, 'consumption_order': consumption,
        'counts': {'episodes': len(rows), 'pair_units': len(units), 'server_starts': 0,
                   'server_smoke': 0, 'gets': len(tail),
                   'logical_calls_min': 300, 'logical_calls_max': 420,
                   'wire_attempt_cap': 420 * (retries + 1)},
    }
    return _seal(body)


def check_stage5(schedule: Mapping, stage4: Optional[Mapping] = None) -> None:
    """[pure] Raise ``ScheduleRefused`` unless every stage-5 invariant holds (and, given ``stage4``,
    every solo link names a concurrency-1 stage-4 row of the same workflow/model/task/repetition)."""
    if schedule.get('schema') != STAGE5_SCHEMA:
        raise ScheduleRefused('not a stage-5 schedule')
    ods = check_open_decisions(schedule.get('open_decisions'))
    rows = schedule['rows']
    ids = [r['row_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ScheduleRefused('a row id repeats')
    episodes = [r for r in rows if r['kind'] == 'episode']
    units = schedule['units']
    if len(episodes) != 240 or len(units) != 120:
        raise ScheduleRefused('%d episodes / %d pairs, protocol 5.8(4) gives 240 / 120'
                              % (len(episodes), len(units)))
    tasks = schedule['smoke_tasks']
    coords = {(t, r) for t in tasks for r in range(1, REPETITIONS + 1)}
    ep_by_id = {e['row_id']: e for e in episodes}
    covered: list[str] = []
    for contrast in CONTRASTS:
        mine = [u for u in units if u['contrast'] == contrast]
        if len(mine) != PAIRS_PER_CONTRAST \
                or {(u['task_uid'], u['repetition']) for u in mine} != coords:
            raise ScheduleRefused('%s does not have one pair per task/repetition coordinate'
                                  % (contrast,))
        first = [u for u in mine if u['candidate_at_position_1']]
        if len(first) != CANDIDATE_FIRST_PER_CONTRAST:
            raise ScheduleRefused('%s orientation is %d/%d, root fixes 15/15'
                                  % (contrast, len(first), len(mine) - len(first)))
        for rep in range(1, REPETITIONS + 1):
            if sum(1 for u in first if u['repetition'] == rep) != 3:
                raise ScheduleRefused('%s repetition %d is not 3/3' % (contrast, rep))
        for task in tasks:
            if sum(1 for u in first if u['task_uid'] == task) not in (2, 3):
                raise ScheduleRefused('%s task %s is not 2 or 3 candidate-first' % (contrast, task))
        for u in mine:
            pair = [ep_by_id.get(x) for x in u['episodes']]
            if any(e is None for e in pair) or sorted(e['arm'] for e in pair) != \
                    ['candidate', 'incumbent']:
                raise ScheduleRefused('pair %s is not one episode of each arm' % (u['unit_id'],))
            for position, e in enumerate(pair, start=1):
                if e['position'] != position or e['worker_index'] != position - 1 \
                        or e['unit_id'] != u['unit_id'] or e['contrast'] != contrast \
                        or (e['task_uid'], e['repetition']) != (u['task_uid'], u['repetition']):
                    raise ScheduleRefused('pair %s names episode %s inconsistently'
                                          % (u['unit_id'], e['row_id']))
            cand = next(e for e in pair if e['arm'] == 'candidate')
            if (cand['position'] == 1) != u['candidate_at_position_1']:
                raise ScheduleRefused('pair %s orientation flag disagrees with its positions'
                                      % (u['unit_id'],))
            covered.extend(u['episodes'])
    if sorted(covered) != sorted(ep_by_id):
        raise ScheduleRefused('the pairs are not a partition of the 240 episodes')
    if sorted(u['seq'] for u in units) != list(range(1, 121)):
        raise ScheduleRefused('the pair execution order is not a permutation of 1..120')
    retries = _RETRIES[ods['OD2']['retries']]
    if any(e['max_connection_retries'] != retries for e in episodes):
        raise ScheduleRefused('an episode disagrees with OD2')
    session_ids = [r['row_id'] for r in rows if r['kind'] != 'episode']
    if sorted(schedule['consumption_order']) != sorted(session_ids + [u['unit_id'] for u in units]):
        raise ScheduleRefused('consumption_order does not name every pair and session row once')
    if schedule['counts']['wire_attempt_cap'] != 420 * (retries + 1):
        raise ScheduleRefused('the wire cap is not 420 x tries')
    if stage4 is not None:
        if schedule['stage4_schedule_sha256'] != stage4.get('schedule_sha256'):
            raise ScheduleRefused('linked to a different stage-4 schedule')
        s4 = {r['row_id']: r for r in stage4['rows'] if r['kind'] == 'episode'}
        for e in episodes:
            link = s4.get(e['solo_link'])
            if link is None or link['concurrency'] != 1 or \
                    (link['workflow'], link['server'], link['task_uid'], link['repetition']) != \
                    (e['workflow'], e['server'], e['task_uid'], e['repetition']):
                raise ScheduleRefused('episode %s solo link %r is not its concurrency-1 coordinate'
                                      % (e['row_id'], e['solo_link']))


# ------------------------------------------------------------------------------------------------
# write-once storage
# ------------------------------------------------------------------------------------------------
def write_schedule(schedule: Mapping, path: 'str | Path') -> str:
    """Check, then write once (``lab_common.write_json_atomic``).  Returns the file sha256."""
    _check_any(schedule)
    return lab_common.write_json_atomic(Path(path), dict(schedule), durable=True)


def load_schedule(path: 'str | Path', *, expected_file_sha256: Optional[str] = None) -> dict:
    """Read a stored schedule and refuse it unless its bytes, digest and invariants all hold."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise ScheduleRefused('schedule unreadable: %s' % (type(exc).__name__,)) from None
    if expected_file_sha256 is not None and lab_common.sha256_bytes(data) != expected_file_sha256:
        raise ScheduleRefused('schedule file sha256 %s differs from the pinned %s'
                              % (lab_common.sha256_bytes(data), expected_file_sha256))
    try:
        schedule = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise ScheduleRefused('schedule bytes are not valid JSON') from None
    if not isinstance(schedule, dict):
        raise ScheduleRefused('a schedule is a JSON object')
    body = {k: v for k, v in schedule.items() if k != 'schedule_sha256'}
    if lab_common.sha256_canonical(body) != schedule.get('schedule_sha256'):
        raise ScheduleRefused('schedule content does not match its schedule_sha256')
    if lab_common.canonical_json(schedule).encode('utf-8') != data:
        raise ScheduleRefused('schedule bytes are not the canonical serialization')
    _check_any(schedule)
    return schedule


def _check_any(schedule: Mapping) -> None:
    body = {k: v for k, v in schedule.items() if k != 'schedule_sha256'}
    if lab_common.sha256_canonical(body) != schedule.get('schedule_sha256'):
        raise ScheduleRefused('schedule content does not match its schedule_sha256')
    if schedule.get('schema') == STAGE4_SCHEMA:
        check_stage4(schedule)
    elif schedule.get('schema') == STAGE5_SCHEMA:
        check_stage5(schedule)
    else:
        raise ScheduleRefused('unknown schedule schema %r' % (schedule.get('schema'),))

