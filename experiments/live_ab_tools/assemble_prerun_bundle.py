"""Assemble the ONE finite working-branch pre-run bundle for root's freeze review.

Root, 2026-09-23 20:03 (reviews/patch_state_and_durable_linkage_delta_20260923_2003.md,
"Decision and next owner action" item 2): "deliver one finite working-branch
pre-run bundle: stage-by-stage time/token/host-capacity sheet; the remaining
structural inputs and immutable manifest; exact stage-0 request/argv and
source-tree three-check receipt; completed versus planned counts,
failures/missingness and usage; AB/BA assignment, enrollment-indexed partial
bounds, simultaneous alpha allocation, success/cost guardrails and
effect-independent stopping. State the actual timestamp of a fresh
capacity/process observation when made."

This writes ONE write-once manifest that names every component by path and
SHA-256 (measured here), maps each of root's requirements to the component and
key that answers it, carries the component verdicts as read from the files, and
records a fresh process/capacity observation with its own timestamp. It
authorizes nothing and is not a freeze.

Reads files, `ps`, `df`, `sysctl`; writes one file. No model, server or build.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT_DIR = REPO / 'results' / 'live_ab'

SHEET = 'results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json'
LAUNCH = 'results/live_ab/PROSPECTIVE_LAUNCH_RECORD_20260923_2030.json'
THREE = 'results/live_ab/SOURCE_TREE_THREE_CHECKS_20260923_2033.json'
STAGE0 = 'experiments/live_ab_serving/stage0_request_argv.json'
SUPPORT = [
    'results/live_ab/DURABLE_REBUILD_20260923T192024Z.json',
    'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST_DURABLE.json',
    'results/live_ab/DURABLE_BUILD_CONFIG_SNAPSHOT.json',
    'results/live_ab/DURABLE_LINKAGE_DELTA.json',
    'results/live_ab/DURABLE_LINKAGE_DELTA_EXPLAINED.json',
    'results/live_ab/durable_build_originals/build.ninja',
    'results/live_ab/durable_build_originals/compile_commands.json',
    'results/live_ab/LOADER_LINKAGE_BUILD_RULES_v2.json',
    'results/live_ab/LOADER_CALL_SITE_EXCERPTS_v2.json',
    'results/live_ab/PATCH_STATE_AMENDMENT_RECEIPT_20260923_1933.json',
    'results/live_ab/FREEZE_REACHABILITY_v4.json',
    'experiments/live_ab/config.json',
    'experiments/live_ab/design/protocol_FINAL.md',
    'experiments/live_ab_validation/cells.json',
    'experiments/live_ab_serving/live_ab_slot_lifecycle.patch',
    'experiments/live_ab_serving/run_smoke.py',
    'experiments/live_ab_serving/dependency_closure.py',
]


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def run(cmd: list) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 'ERROR %s' % type(exc).__name__


def observe() -> dict:
    """A fresh process/capacity observation, timestamped when it is taken."""
    t = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    ps = run(['ps', '-axo', 'pid=,rss=,command='])
    watch = ('llama-server', 'run_smoke', 'lab_orchestrator', 'run_live_ab', 'ninja',
             'cmake')
    rows = []
    for line in ps.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and any(w in parts[2] for w in watch) \
                and 'assemble_prerun_bundle' not in parts[2]:
            rows.append({'pid': int(parts[0]), 'rss_kib': int(parts[1]),
                         'command_head': parts[2][:120]})
    st = os.statvfs(str(REPO))
    return {
        'observed_utc': t,
        'processes_matching': {'patterns': list(watch), 'rows': rows, 'count': len(rows)},
        'disk_free_bytes_repo_volume': st.f_bavail * st.f_frsize,
        'memory_bytes': int(run(['sysctl', '-n', 'hw.memsize']).strip() or 0),
        'load_average': run(['sysctl', '-n', 'vm.loadavg']).strip(),
        'boot_time': run(['sysctl', '-n', 'kern.boottime']).strip(),
        'reading': ('an observation at observed_utc, not a capacity lease or reservation; '
                    'a loaded stage re-observes at its own start (capacity gate)'),
    }


def main() -> int:
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    out = OUT_DIR / ('PRE_RUN_BUNDLE_%s.json' % stamp)
    if out.exists():
        print('refusing: %s exists (write-once)' % out, file=sys.stderr)
        return 2
    sheet = json.loads((REPO / SHEET).read_text())
    launch = json.loads((REPO / LAUNCH).read_text())
    three = json.loads((REPO / THREE).read_text())
    fs = sheet['finite_feasibility_sheet']
    pd = sheet['preserved_design']
    head = run(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).strip()
    components = {rel: {'sha256': sha(rel), 'bytes': (REPO / rel).stat().st_size}
                  for rel in [SHEET, LAUNCH, THREE, STAGE0] + SUPPORT}
    s0 = launch['stage0_binding']
    requirements = [
        {'root_20_03': 'stage-by-stage time/token/host-capacity sheet',
         'answered_by': SHEET, 'keys': ['finite_feasibility_sheet.stage_rows',
                                        'finite_feasibility_sheet.trial_rows',
                                        'finite_feasibility_sheet.totals',
                                        'finite_feasibility_sheet.feasibility_verdict']},
        {'root_20_03': 'the remaining structural inputs',
         'answered_by': SHEET, 'keys': ['finite_feasibility_sheet.remaining_structural_freeze_inputs'],
         'value': [i['key'] for i in fs['remaining_structural_freeze_inputs']['items']]},
        {'root_20_03': 'immutable manifest',
         'answered_by': 'this file (components by SHA-256) and ' + LAUNCH,
         'keys': ['components', 'launch_manifest_fields (in the launch record)']},
        {'root_20_03': 'exact stage-0 request/argv',
         'answered_by': LAUNCH, 'keys': ['stage0_binding'],
         'value': {'request': s0['request'], 'server_args': s0['server_args'],
                   'all_pass': s0['all_pass'],
                   'negative_controls_all_refused': s0['negative_controls_all_refused']}},
        {'root_20_03': 'source-tree three-check receipt',
         'answered_by': THREE, 'keys': ['check_1_head', 'check_2_status_porcelain',
                                        'check_3_tree_equality'],
         'value': {'all_three_pass': three['all_three_pass']}},
        {'root_20_03': 'completed versus planned counts, failures/missingness and usage',
         'answered_by': SHEET, 'keys': ['finite_feasibility_sheet.stage_rows[*].completed/planned/failures_and_missingness/resource_use_timestamps',
                                        'finite_feasibility_sheet.program_state']},
        {'root_20_03': 'AB/BA assignment', 'answered_by': SHEET,
         'keys': ['preserved_design.paired_AB_BA_rules', 'preserved_design.four_trial_order']},
        {'root_20_03': 'enrollment-indexed partial bounds', 'answered_by': SHEET,
         'keys': ['preserved_design.enrollment_indexed_partial_bounds']},
        {'root_20_03': 'simultaneous alpha allocation', 'answered_by': SHEET,
         'keys': ['preserved_design.simultaneous_error_allocation',
                  'preserved_design.alpha_program_trial_gate',
                  'preserved_design.alpha_not_reallocated_on_deferral']},
        {'root_20_03': 'success/cost guardrails', 'answered_by': SHEET,
         'keys': ['preserved_design.guardrails_and_decision_conditions']},
        {'root_20_03': 'effect-independent stopping', 'answered_by': SHEET,
         'keys': ['preserved_design.effect_independent_stopping',
                  'preserved_design.no_outcome_driven_extension_or_margin_relaxation']},
        {'root_20_03': 'actual timestamp of a fresh capacity/process observation',
         'answered_by': 'this file', 'keys': ['fresh_observation.observed_utc']},
    ]
    missing = [(r['root_20_03'], k) for r in requirements if r['answered_by'] == SHEET
               for k in r['keys'] if k.startswith('preserved_design.')
               and k.split('.', 1)[1] not in pd]
    doc = {
        'schema': 'live_ab/pre_run_bundle-v1',
        'status': ('FOR ROOT\'S ONE GO/NO-GO FREEZE REVIEW. NOT A FREEZE and not an '
                   'authorization: no trial episode, loaded stage, model load or server '
                   'start is authorized by this bundle. Root\'s explicit freeze decision '
                   'is required (reviews/patch_state_and_durable_linkage_delta_20260923_2003.md).'),
        'convention': 'deterministic-path',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'repo_head_at_assembly': head,
        'components': components,
        'requirements_map': requirements,
        'requirements_keys_absent_from_the_sheet': missing,
        'component_verdicts': {
            'sheet_status': sheet['status']['label'][:120],
            'sheet_consistency_assertions_all_hold': all(
                a.get('holds') for a in sheet['consistency']['assertions']),
            'sheet_consistency_assertions': len(sheet['consistency']['assertions']),
            'feasibility_verdict': fs['feasibility_verdict']['verdict'],
            'executable_launch_blockers': [(b['id'], b['what'])
                                           for b in fs['executable_launch_blockers']['items']],
            'decisions_for_root': fs['decisions_for_root'],
            'launch_record_preflight_all_pass': launch['preflight_dry_run']['all_pass'],
            'launch_record_pending': launch['PENDING_not_bound_here'],
            'source_tree_three_checks_all_pass': three['all_three_pass'],
        },
        'program_state': fs['program_state'],
        'fresh_observation': observe(),
        'what_this_bundle_does_not_show': [
            'native execution of the durable candidate: no launch is authorized, so the '
            'loaded behaviour is unmeasured',
            'owner-host claims root cannot rerun from its checkout (the 41-edge closure, '
            'the 373-unit map over the owner-host trees, the three checks): owner evidence',
            'engineering time for the executable blockers EB1-EB5: not costed',
        ],
    }
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(out, 'missing_keys=%d three=%s launch=%s' % (
        len(missing), three['all_three_pass'], launch['preflight_dry_run']['all_pass']))
    return 0


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
