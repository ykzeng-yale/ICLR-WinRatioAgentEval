"""dryrun_live_ab.py -- the whole program end to end with no model (ARCHITECTURE 9.3).

G5.  Two things live here.

**The dry runs D1-D7.**  Each writes to a scratch results tree, stamps ``MOCK`` on every
derived file, and must end with ``lab_verify_log --mode full`` PASS and an exact
``monitor.replay``.  Nothing here ever runs a language model, starts a language-model
server, opens a network connection or touches the project's git state.

| id | scenario | expected path |
|----|----------|---------------|
| D1 | candidate clearly worse | ``harm_keep_incumbent`` at the first admissible look |
| D2 | equal success, candidate faster, frozen ``delta`` | ``horizon_no_decision`` |
| D3 | as D2 with a **mock-only** wide margin | the full deploy path: decision, blocking anchor, switch, follow-up cohort |
| D4 | A/A over several mock seeds | the crossing count is printed, never discarded |
| D5 | chaos: killed workers and a killed orchestrator | verifier PASS, no second coin, no second reveal, no re-run |
| D6 | anchor drill | see ``--drill``: this session may not run a state-changing git command, so the drill checks the anchor **prefix property** without committing |
| D7 | ``--radius-table`` | regenerate the radius table from ``src/winstats.py`` |

**The simulated episode.**  ``--sim-worker --job FILE`` is a stand-in for ``lab_worker``
with the same spool contract: it writes ``job_accepted``, ``call_started`` /
``call_response`` pairs, ``sandbox_exec`` and ``episode_final``, and it deposits a record
file.  It is a *test double for the worker*, not for the orchestrator: the chain, the
monitor, the coin, the decision, the anchors and the resume logic are the production code
paths in every dry run.  Its outcomes are a deterministic function of
``(outcome_seed, trial, arrival)`` and of the scenario's per-arm parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Mapping

import lab_common
import lab_data
import lab_design
import lab_eventlog
import lab_monitor
import lab_orchestrator
import lab_verify_log
from lab_common import canonical_json, sha256_canonical, sha256_file, sha256_text
from lab_orchestrator import World, make_context, run_trial

HERE = Path(__file__).resolve().parent
MOCK_BANNER = 'MOCK'

#: The prefixes of the radius table (ARCHITECTURE 10).  565 is the ceiling once the six
#: declared smoke tasks are excluded; 568 is the same rule BEFORE any exclusion, so it is a
#: loose pre-exclusion bound and not the horizon; 569 is the unstratified count 1138 // 2 and
#: is not a horizon either.  The effective horizon is read from the frozen roster.
RADIUS_NS: tuple[int, ...] = (1, 20, 92, 100, 150, 200, 295, 400, 565, 568, 569, 1000)


# ---------------------------------------------------------------------------
# D7: the radius table
# ---------------------------------------------------------------------------
def radius_table_rows(cfg: Mapping) -> list[dict]:
    """Every radius regenerated from ``src/winstats.py``; no radius is ever hand-typed
    (PG-20, protocol 1.3)."""
    monitor = dict(cfg['monitor'])
    mc = lab_monitor.MonitorConfig(alpha_gate=float(monitor['alpha_gate']),
                                   rho=float(monitor['rho']),
                                   delta=float(monitor['delta']),
                                   n_min=int(monitor['n_min']), n_max=max(RADIUS_NS))
    return lab_monitor.radius_table(list(RADIUS_NS), mc)


def write_radius_table(out: Path, cfg: Mapping) -> str:
    rows = radius_table_rows(cfg)
    text = 'n,radius\n' + ''.join('%d,%r\n' % (r['n'], r['radius']) for r in rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='utf-8')
    return sha256_text(text)


# ---------------------------------------------------------------------------
# a mock roster and a mock freeze tree
# ---------------------------------------------------------------------------
def make_mock_roster(n_pairs: int) -> dict:
    """A MOCK roster of ``2 * n_pairs`` tasks with uids in the frozen pattern.

    Used only by the dry runs: it carries no benchmark content and never enters a trial.
    The real roster is built by ``lab_data.build_roster`` from the pinned sources."""
    tasks: list[dict] = []
    s1: list[str] = []
    s2: list[str] = []
    n_s1 = 2 * ((n_pairs + 1) // 2)
    n_s2 = 2 * (n_pairs // 2)
    for i in range(n_s1):
        uid = 'mbpp/%d' % (9000 + i)
        s1.append(uid)
        tasks.append(_mock_task(uid, 'mbpp', 'S1'))
    for i in range(n_s2):
        uid = 'mbpp_full/%d' % (9000 + i)
        s2.append(uid)
        tasks.append(_mock_task(uid, 'mbpp_full', 'S2'))
    roster = {
        'mock': True,
        'schema': lab_data.ROSTER_SCHEMA,
        'strata': ['S1', 'S2'],
        'pairing': 'stratified_no_mixed_pair',
        'n_pairs_rule': 'floor(n_S1 / 2) + floor(n_S2 / 2)',
        'uid_pattern': lab_data.UID_PATTERN,
        'roster_mode': 'EXT',
        'tasks': [t['uid'] for t in tasks],
        'task_records': tasks,
        'S1': s1, 'S2': s2,
        'exclusions': [],
        'n_S1': len(s1), 'n_S2': len(s2), 'n_total': len(tasks),
        'n_pairs': len(s1) // 2 + len(s2) // 2,
        'n_excluded': 0,
        'task_content_sha256': sha256_canonical(tasks),
    }
    roster['roster_sha256'] = lab_data.roster_sha256(roster)
    return roster


def _mock_task(uid: str, benchmark: str, stratum: str) -> dict:
    n = int(uid.split('/')[1])
    return {
        'uid': uid, 'benchmark': benchmark, 'stratum': stratum,
        'prompt': 'Write a function f%d(x) that returns x + %d.' % (n, n % 7),
        'entry_point': 'f%d' % n,
        'reference': 'def f%d(x):\n    return x + %d\n' % (n, n % 7),
        'test_imports': [], 'test_list': ['assert f%d(1) == %d' % (n, 1 + n % 7)],
        'challenge_test_list': [], 'test': '',
    }


def build_mock_freeze(root: Path, *, n_pairs: int, trial: str, delta: float | None = None,
                      n_min: int | None = None) -> dict:
    """Write a MOCK freeze tree (config, roster, arrival orders, bundle) under ``root``.

    Every ``null`` of the frozen configuration that a run needs is pinned here **by the
    rule that determines it**, never invented: ``n_max`` and ``roster.n_pairs`` come from
    the mock roster, ``request_timeout_s`` from the formula of protocol 5.6 at the mock
    ``c_max``, and ``episode_hard_cap_s`` from its formula.  A ``delta`` or ``n_min``
    override is **mock-only** and is recorded in the tree as such (D3)."""
    freeze = root / 'freeze'
    freeze.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE / 'config.json').read_text(encoding='utf-8'))
    roster = make_mock_roster(n_pairs)
    cfg['roster'].update({'n_S1': roster['n_S1'], 'n_S2': roster['n_S2'],
                          'n_total': roster['n_total'], 'n_pairs': roster['n_pairs'],
                          'roster_sha256': roster['roster_sha256'],
                          'task_content_sha256': roster['task_content_sha256']})
    cfg['monitor']['n_max'] = roster['n_pairs']
    cfg['monitor']['reference_rule_sha256'] = sha256_file(HERE / 'lab_reference_rule.py')
    cfg['execution']['request_timeout_s'] = 180.0
    cfg['execution']['episode_hard_cap_s'] = lab_orchestrator.episode_hard_cap_s(
        cfg['execution'])
    cfg['sandbox']['profile_sha256'] = sha256_text('mock-sandbox-profile')
    cfg['sandbox']['containment_probe_sha256'] = sha256_text('mock-containment-probe')
    cfg['anchor']['posting_latency_p95_s'] = 0.0
    # Preflight now COMPARES the running host with the frozen allowlist, so a mock tree must
    # name the host it is actually executed on beside the 'mock' marker.
    cfg['hardware_allowlist'] = ['mock', lab_common.hardware_identity()]
    cfg['environment_lock_sha256'] = sha256_text('mock-environment-lock')
    cfg['llama_cpp']['build_flags_sha256'] = sha256_text('mock-build-flags')
    cfg['llama_cpp']['serving_manifest_sha256'] = sha256_text('mock-serving-manifest')
    for server_id in cfg['servers']:
        cfg['servers'][server_id]['sha256_recomputed'] = \
            cfg['servers'][server_id]['sha256_expected']
        cfg['servers'][server_id]['license_evidence_sha256'] = sha256_text('mock-licence')
        cfg['receipt']['golden_props_sha256'][server_id] = sha256_text('mock-props')
        cfg['receipt']['golden_generation_settings_sha256'][server_id] = \
            sha256_text('mock-generation-settings')
    for t in cfg['prefreeze']['side_by_side_compression_C']:
        cfg['prefreeze']['side_by_side_compression_C'][t] = 1.0
    cfg['mock'] = True
    if delta is not None:                       # D3: mock only, never the frozen config
        cfg['monitor']['delta'] = float(delta)
        cfg['mock_overrides'] = {'monitor.delta': float(delta)}
    if n_min is not None:
        cfg['monitor']['n_min'] = int(n_min)
        cfg.setdefault('mock_overrides', {})['monitor.n_min'] = int(n_min)

    (freeze / 'config.json').write_text(canonical_json(cfg) + '\n', encoding='utf-8')
    (freeze / 'roster.json').write_text(canonical_json(roster) + '\n', encoding='utf-8')
    orders: dict[str, list] = {}
    for name in lab_common.TRIALS:
        order = lab_design.arrival_order(roster, name, int(cfg['design_seed_base']))
        orders[name] = order
        (freeze / ('arrival_order_%s.json' % name)).write_text(
            canonical_json([dict(s) for s in order]) + '\n', encoding='utf-8')
    (freeze / 'tasks.json').write_text(canonical_json(roster['task_records']) + '\n',
                                       encoding='utf-8')
    bundle = _mock_bundle(freeze, cfg, roster)
    (freeze / 'freeze_bundle.json').write_text(canonical_json(bundle) + '\n',
                                               encoding='utf-8')
    return {'cfg': cfg, 'roster': roster, 'orders': orders, 'bundle': bundle,
            'bundle_sha': lab_common.freeze_bundle_sha256(bundle), 'freeze': freeze}


def _mock_bundle(freeze: Path, cfg: dict, roster: dict) -> dict:
    parts = {
        'protocol_version': str(cfg['protocol_version']),
        'config_sha256': sha256_file(freeze / 'config.json'),
        'rule_block_sha256': lab_common.rule_block_sha256(cfg),
        'roster_sha256': str(roster['roster_sha256']),
        'task_content_sha256': str(roster['task_content_sha256']),
        # The real digest of each deposited arrival-order file, not a stand-in: preflight
        # now compares every bundle member against the artifact it names, so a mock bundle
        # that recorded an invented order digest would be a mock of a BROKEN freeze.
        'arrival_order_sha256': {t: sha256_file(freeze / ('arrival_order_%s.json' % t))
                                 for t in lab_common.TRIALS
                                 if (freeze / ('arrival_order_%s.json' % t)).exists()},
        'protocol_sha256': sha256_text('mock-protocol'),
        'run_book_sha256': sha256_text('mock-run-book'),
        'harness_file_sha256': lab_common.harness_file_hashes(),
        'reused_file_sha256': {n: sha256_file(lab_common.LS_DIR / n)
                               for n in lab_common.REUSED_FILES
                               if (lab_common.LS_DIR / n).exists()},
        'winstats_sha256': sha256_file(lab_common.SRC_DIR / 'winstats.py'),
        'gguf_sha256': {k: v['sha256_expected'] for k, v in cfg['servers'].items()},
        'license_evidence_sha256': sha256_text('mock-licence'),
        'serving_manifest_sha256': sha256_text('mock-serving-manifest'),
        'golden_props_sha256': dict(cfg['receipt']['golden_props_sha256']),
        'golden_generation_settings_sha256':
            dict(cfg['receipt']['golden_generation_settings_sha256']),
        'receipt_mask_sha256': sha256_canonical(cfg['receipt']['mask']),
        'sandbox_profile_sha256': str(cfg['sandbox']['profile_sha256']),
        'containment_probe_sha256': str(cfg['sandbox']['containment_probe_sha256']),
        'prefreeze_head': sha256_text('mock-prefreeze-head'),
        'prefreeze_bytes': 0,
        'prefreeze_file_sha256': sha256_text('mock-prefreeze-file'),
        'derivation_sha256': sha256_text('mock-derivation'),
        'planning_sha256': sha256_text('mock-planning'),
        'environment_lock_sha256': str(cfg['environment_lock_sha256']),
        'hardware_allowlist': list(cfg['hardware_allowlist']),
    }
    return lab_common.build_freeze_bundle(parts)


# ---------------------------------------------------------------------------
# the simulated episode
# ---------------------------------------------------------------------------
class SimKill(BaseException):
    """A simulated hard crash inside the simulated worker.

    ``BaseException`` so that nothing in the state machine can swallow it: from the chain's
    point of view a SIGKILL and this are the same event."""


#: Global ordinals for the crash injector, so that a test can name "the third
#: ``call_started`` of the run" rather than a position inside one episode.
SIM_COUNTS: dict = {}


def _maybe_kill(kind: str, scenario: Mapping) -> None:
    want = scenario.get('kill_after')
    if not want or want != kind:
        return
    SIM_COUNTS[kind] = SIM_COUNTS.get(kind, 0) + 1
    if SIM_COUNTS[kind] >= int(scenario.get('kill_nth', 1)):
        raise SimKill(kind)


def _roll(*parts: object) -> float:
    digest = hashlib.sha256('|'.join(str(p) for p in parts).encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') / float(1 << 64)


def _resolve_token(tok: str) -> Path:
    """The inverse of :func:`lab_common.tokenize_path` (the worker's own rule)."""
    s = str(tok)
    roots = {'<WORK>': lab_common.WORK_ROOT, '<RESULTS>': lab_common.RESULTS_ROOT,
             '<REPO>': lab_common.REPO_ROOT, '<HOME>': Path.home(),
             '<TMP>': Path(tempfile.gettempdir())}
    for token, root in roots.items():
        if s == token:
            return Path(root)
        if s.startswith(token + '/'):
            return Path(root) / s[len(token) + 1:]
    return Path(s)


def run_sim_episode(job: Mapping, scenario: Mapping) -> int:
    """The body of ``--sim-worker``: the spool contract of ARCHITECTURE 5, no model."""
    import lab_client

    arm = str(job['arm'])
    arrival = int(job['arrival'])
    trial = str(job['trial'])
    seed = int(scenario.get('outcome_seed', 20260919))
    params = dict(scenario.get(arm) or {})
    p_good = float(params.get('p_good', 0.55))
    latency_scale = float(params.get('latency_scale', 1.0))
    n_calls = max(1, int(params.get('calls', 1)))
    sleep_s = float(scenario.get('sleep_s', 0.0))
    tokens = int(params.get('completion_tokens', 180))

    paths = dict(job['paths'])
    spool = lab_client.Spool(_resolve_token(paths['spool']))
    spool.set_inv(str(job['inv']))
    t_start_ns = time.monotonic_ns()
    try:
        spool.write('job_accepted', {
            'arm': arm, 'workflow': str(job['workflow']), 'task_uid': str(job['task_uid']),
            'job_sha256': sha256_canonical(dict(job)),
            'payload_sha256': str(job['payload_sha256'])}, durable=True)
        _maybe_kill('job_accepted', scenario)
        if sleep_s:
            time.sleep(sleep_s)
        t_c1_ns = time.monotonic_ns()
        prompt_tokens = 0
        for call_index in range(n_calls):
            request_id = hashlib.sha256(
                ('%s|%d|%d|%s' % (trial, arrival, call_index, arm)).encode()
            ).hexdigest()[:32]
            t_send_ns = time.monotonic_ns()
            spool.write('call_started', {
                'call_index': call_index, 'kind': 'code' if call_index == 0 else 'repair',
                'try_index': 0, 'request_id': request_id,
                'seed': (int(_roll(seed, 'seed', trial, arrival, call_index) * (1 << 31))
                         & 0x7FFFFFFE) | int(job['worker_index']),
                'body_sha256': sha256_text('body|%s|%d' % (request_id, call_index)),
                'messages_sha256': sha256_text('messages|%s' % request_id),
                'n_messages': 2, 'prompt_chars': 400,
                'sampling_sent': dict(job.get('sampling') or {}),
                't_c1_ns': t_c1_ns, 't_send_ns': t_send_ns, 'fsync_ms_prev': 0.0,
            }, durable=True)
            _maybe_kill('call_started', scenario)
            per_call_s = 0.9 * latency_scale
            t_recv_ns = t_send_ns + int(per_call_s * 1e9)
            prompt_tokens += 312
            spool.write('call_response', {
                'request_id': request_id, 'call_index': call_index, 'kind': 'code',
                'try_index': 0, 'http_status': 200,
                'usage': {'prompt_tokens': 312, 'completion_tokens': tokens,
                          'total_tokens': 312 + tokens, 'cached_tokens': 0},
                'timings': {'cache_n': 0, 'prompt_n': 312, 'prompt_ms': 120.0,
                            'predicted_n': tokens, 'predicted_ms': per_call_s * 1000.0,
                            'predicted_per_second': 142.2},
                'generation_settings_sha256': sha256_text('mock-generation-settings'),
                'receipt_mismatch': (['temperature_differs']
                                     if scenario.get('receipt_mismatch') else []),
                'id_slot': int(job['worker_index']),
                'finish_reason': 'stop', 'truncated': False,
                'content_sha256': sha256_text('content|%s' % request_id),
                'rendered_prompt_sha256': sha256_text('prompt|%s' % request_id),
                'client_seconds': per_call_s, 't_recv_ns': t_recv_ns,
                'model_matches_alias': True}, durable=True)
            _maybe_kill('call_response', scenario)
        spool.write('sandbox_exec', {'purpose': 'verify', 'lock_wait_s': 0.0,
                                     'seconds': 0.01, 'returncode': 0,
                                     'timed_out': False,
                                     'profile_sha256': sha256_text('mock-profile')},
                    durable=False)
        success = 1 if _roll(seed, 'success', trial, arrival, arm) < p_good else 0
        # `latency_s` must dominate the certified elapsed time built from this episode's
        # own spooled stamps (protocol 7.5 item 4: `ell` is a lower bound on `latency_s`
        # because t_0 <= t_c1 and t_final >= t_e).  In the real worker that holds because
        # `latency_s` is the pilot's wall clock around the same calls; here it is enforced
        # explicitly, because an episode whose reported latency fell below its own
        # certificate would make a cost certificate false and the containment audit would
        # (correctly) report a decision-code defect.
        ell_sim = n_calls * 0.9 * latency_scale
        latency_s = round(ell_sim * (1.0 + 0.2 * _roll(seed, 'lat', trial, arrival, arm))
                          + 1e-3, 6)
        rec = {
            'mock': True, 'uid': str(job['task_uid']), 'arm_blind': True,
            'workflow': str(job['workflow']), 'trial': trial, 'arrival': arrival,
            'success': success, 'latency_s': latency_s,
            'completion_tokens': tokens * n_calls, 'prompt_tokens': prompt_tokens,
            'n_llm_calls': n_calls, 'repair_rounds': max(0, n_calls - 1),
            'self_test_passed': None, 'sentinel_seen': bool(success),
            'entry_point_defined': True, 'timed_out': False,
            'final_code': 'def f(x):\n    return x\n', 'verify_seconds': 0.01,
            'static_flags': [], 'hack_flags': [],
        }
        record_sha = sha256_canonical(rec)
        record_dir = _resolve_token(paths['records'])
        record_dir.mkdir(parents=True, exist_ok=True)
        lab_common.write_json_atomic(record_dir / ('%s.json' % record_sha), rec,
                                     durable=True)
        _maybe_kill('record', scenario)
        outcome = {
            'success': success, 'latency_s': latency_s,
            'completion_tokens': tokens * n_calls, 'prompt_tokens': prompt_tokens,
            'n_llm_calls': n_calls, 'n_failed_calls': 0, 'connection_retries': 0,
            'n_self_test_executions': 0, 'n_verifier_executions': 1,
            'repair_rounds': max(0, n_calls - 1), 'self_test_passed': None,
            'request_timeout_any': False, 'episode_timeout': False,
            'verifier_timeout': False, 'truncated_any': False,
            'sentinel_seen': bool(success), 'entry_point_defined': True,
            'error_class': ('receipt_mismatch' if scenario.get('receipt_mismatch')
                            else None),
            'infra_flag': bool(scenario.get('receipt_mismatch')),
        }
        spool.write('episode_final', {
            'record_sha256': record_sha, 'outcome': outcome,
            'final_code_sha256': sha256_text(str(rec['final_code'])),
            'verify_program_sha256': sha256_text('mock-verify-program'),
            't_start_ns': t_start_ns, 't_end_ns': time.monotonic_ns(),
            'verify_seconds': 0.01, 'static_flags': [], 'hack_flags': [],
            'certified_ell': 0.0, 'tokens_known': tokens * n_calls,
            'seed_collisions': 0,
            'receipt_mismatch': (['temperature_differs']
                                 if scenario.get('receipt_mismatch') else [])},
            durable=True)
        _maybe_kill('episode_final', scenario)
        return 0
    finally:
        spool.close()


class SimWorld(World):
    """The substitute world of ARCHITECTURE 3.13: **only** the dispatch of a worker process
    is replaced.  The chain, the coin, the monitor, the shadow, the decision, the anchors
    and the resume path are the production code."""

    scenario: dict = {}

    def spawn(self, att, job_path):                      # type: ignore[override]
        run_sim_episode(att.job, self.scenario or {})
        return os.getpid()

    def finished(self, att):                             # type: ignore[override]
        return 0

    def kill(self, att) -> None:                         # type: ignore[override]
        return None


# ---------------------------------------------------------------------------
# running one dry run
# ---------------------------------------------------------------------------
def run_dry(spec: Mapping, *, root: Path | None = None, verbose: bool = True) -> dict:
    """One dry run end to end: mock freeze tree, orchestrator, anchor process, verifier."""
    root = Path(root or tempfile.mkdtemp(prefix='live_ab_dry_'))
    results = root / 'results'
    work = root / 'work'
    trial = str(spec.get('trial', 'T4'))
    built = build_mock_freeze(results, n_pairs=int(spec['pairs']), trial=trial,
                              delta=spec.get('delta'), n_min=spec.get('n_min'))
    cfg = json.loads((built['freeze'] / 'config.json').read_text(encoding='utf-8'))
    cfg['_runtime'] = {
        # Protocol 7.5 item 4 measures the clock deltas over 10 s. An
        # offline suite cannot sleep 10 s per preflight, so it sets a
        # short window EXPLICITLY -- the preflight records it as
        # below_protocol_window so no receipt from these runs can be
        # mistaken for one taken at the protocol sensitivity.
        'clock_window_s': 0.01,
        'results_root': str(results), 'work_root': str(work),
        'bundle_sha': built['bundle_sha'], 'sim': True, 'mock': True,
        'anchor_mode': 'mock', 'blocking_wait_s': 20.0, 'poll_interval_ms': 0,
        'worktree_check_s': 1e9, 'free_disk_floor_gb': 0.0,
        'tasks_path': str(built['freeze'] / 'tasks.json'),
        'max_pairs': int(spec['pairs']),
        'golden': {'coder': {'props': {}, 'generation_settings': {}, 'mask': ['seed'],
                             'float_tolerance': 1e-6},
                   't3': {'props': {}, 'generation_settings': {}, 'mask': ['seed'],
                          'float_tolerance': 1e-6}},
    }
    anchor = _start_anchor(trial, cfg, results, work)
    scenario = {'outcome_seed': int(spec.get('outcome_seed', 20260919)),
                'incumbent': dict(spec.get('incumbent') or {}),
                'candidate': dict(spec.get('candidate') or {}),
                'sleep_s': float(spec.get('sleep_s', 0.0))}
    previous = lab_orchestrator.WORLD_FACTORY
    SimWorld.scenario = scenario
    lab_orchestrator.WORLD_FACTORY = SimWorld
    try:
        ctx = make_context(trial, cfg, results_root=results, work_root=work)
        status = run_trial(ctx, resume=False)
    finally:
        lab_orchestrator.WORLD_FACTORY = previous
        _stop_anchor(anchor)
    report = lab_verify_log.verify_trial(trial, built['bundle_sha'], mode='full',
                                         results_root=results, work_root=work)
    out = {'id': str(spec.get('id', '?')), 'mock': True, 'banner': MOCK_BANNER,
           'trial': trial, 'status': status, 'root': str(root),
           'verdict': report.verdict, 'pairs': int(spec['pairs']),
           'findings': [f.check for f in report.findings if f.severity == 'FAIL'],
           'decision': _decision_of(results, trial, built['bundle_sha'])}
    if verbose:
        print('[%s] %s status=%s verifier=%s decision=%s'
              % (MOCK_BANNER, out['id'], status, report.verdict, out['decision']))
        for check in out['findings']:
            print('    FAIL %s' % check)
    return out


def _decision_of(results: Path, trial: str, bundle_sha: str) -> str:
    try:
        read = lab_eventlog.read_chain(results / trial / 'events', trial, bundle_sha)
    except Exception:                                    # noqa: BLE001
        return 'unreadable'
    for ev in read.events:
        if ev['type'] == 'decision':
            return '%s@%d' % (ev['body']['kind'], ev['body']['n'])
    return 'none'


def _start_anchor(trial: str, cfg: Mapping, results: Path, work: Path):
    cfg_path = work / ('anchor_cfg_%s.json' % trial)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(canonical_json(dict(cfg)), encoding='utf-8')
    return subprocess.Popen(
        [sys.executable, str(HERE / 'lab_anchor.py'), '--trial', trial,
         '--config', str(cfg_path), '--mock-receipt', '--results', str(results),
         '--work', str(work), '--max-idle-s', '120'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(HERE))


def _stop_anchor(proc) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:                                    # noqa: BLE001
        try:
            proc.kill()
        except Exception:                                # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# the scenarios
# ---------------------------------------------------------------------------
def _screen(pairs: int) -> int:
    """The mock-only screening prefix.  The frozen ``n_min`` is 100 and is never changed
    for a trial; a dry run needs a value small enough that a crossing has room in front of
    it and a follow-up cohort behind it, and the mock tree records the override."""
    return min(100, max(1, pairs // 2))


def scenario_d1(pairs: int = 60) -> dict:
    """D1: the candidate is clearly worse -> ``harm_keep_incumbent``."""
    return {'id': 'D1', 'trial': 'T2', 'pairs': pairs, 'n_min': _screen(pairs),
            'incumbent': {'p_good': 1.0, 'latency_scale': 1.0},
            'candidate': {'p_good': 0.0, 'latency_scale': 4.5}}


def scenario_d2(pairs: int = 40) -> dict:
    """D2: equal success, the candidate is faster, the **frozen** margin refuses ->
    ``horizon_no_decision``.  The declared study outcome and the most important dry run."""
    return {'id': 'D2', 'trial': 'T1', 'pairs': pairs, 'n_min': _screen(pairs),
            'incumbent': {'p_good': 1.0, 'latency_scale': 4.5},
            'candidate': {'p_good': 1.0, 'latency_scale': 1.0}}


def scenario_d3(pairs: int = 60) -> dict:
    """D3: as D2 with a **mock-only** wide margin -> the full deploy path.

    ``delta = 0.9`` is a mock-only value written into the mock freeze tree and recorded
    there under ``mock_overrides``; the frozen ``config.json`` is untouched."""
    return {'id': 'D3', 'trial': 'T1', 'pairs': pairs, 'delta': 0.9,
            'n_min': _screen(pairs),
            'incumbent': {'p_good': 1.0, 'latency_scale': 4.5},
            'candidate': {'p_good': 1.0, 'latency_scale': 1.0}}


def scenario_d4(pairs: int = 40, seed: int = 20260919) -> dict:
    """D4: A/A.  One non-crossing run establishes nothing; a crossing is printed and
    investigated, never discarded (guidance item 8)."""
    return {'id': 'D4', 'trial': 'T4', 'pairs': pairs, 'outcome_seed': seed,
            'incumbent': {'p_good': 0.55, 'latency_scale': 1.0},
            'candidate': {'p_good': 0.55, 'latency_scale': 1.0}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='dryrun_live_ab')
    ap.add_argument('--radius-table', action='store_true')
    ap.add_argument('--out', default=None)
    ap.add_argument('--scenario', default=None,
                    choices=['D1', 'D2', 'D3', 'D4', 'all'])
    ap.add_argument('--pairs', type=int, default=None)
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--sim-worker', action='store_true')
    ap.add_argument('--job', default=None)
    ap.add_argument('--scenario-file', default=None)
    args = ap.parse_args(argv)

    if args.sim_worker:
        job = json.loads(Path(args.job).read_text(encoding='utf-8'))
        scenario = ({} if not args.scenario_file
                    else json.loads(Path(args.scenario_file).read_text(encoding='utf-8')))
        return run_sim_episode(job, scenario)

    if args.radius_table:
        cfg = json.loads((HERE / 'config.json').read_text(encoding='utf-8'))
        out = Path(args.out or (lab_common.FREEZE_DIR / 'radius_table.csv'))
        digest = write_radius_table(out, cfg)
        print('radius_table %s sha256=%s' % (out, digest))
        fixture = HERE / 'testdata' / 'radius_table.csv'
        if fixture.exists():
            same = fixture.read_text(encoding='utf-8') == out.read_text(encoding='utf-8')
            print('testdata/radius_table.csv agrees: %s' % same)
        return 0

    if not args.scenario:
        ap.error('one of --radius-table, --scenario or --sim-worker is required')
    specs: list[dict] = []
    if args.scenario in ('D1', 'all'):
        specs.append(scenario_d1(args.pairs or 60))
    if args.scenario in ('D2', 'all'):
        specs.append(scenario_d2(args.pairs or 40))
    if args.scenario in ('D3', 'all'):
        specs.append(scenario_d3(args.pairs or 60))
    if args.scenario in ('D4', 'all'):
        for k in range(max(1, int(args.seeds))):
            specs.append(scenario_d4(args.pairs or 40, seed=20260919 + k))
    failures = 0
    for spec in specs:
        out = run_dry(spec)
        if out['verdict'] != 'PASS':
            failures += 1
    return 1 if failures else 0


if __name__ == '__main__':                                   # pragma: no cover
    sys.exit(main())
