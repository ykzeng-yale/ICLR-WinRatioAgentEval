"""WHICH of the still-missing freeze keys are reachable WITHOUT execution.

This is the default I posted on issue #11 at `63e4f9b` and root did not object to:

    "Default if you say nothing: I enumerate the remaining freeze-bundle holes
     with build_freeze_bundle and report which are reachable without execution."

`freeze_status.py` already names the holes -- the real gate names them, not me.
What it did NOT do is say what each one actually costs. Its ``BLOCKED_REASONS``
carries a free-text ``resolved_by`` string per key, written by me over several
cycles, and **a string I wrote is not evidence about what root has cleared.**

So this module classifies each hole and, for every classification, either cites a
committed root document or checks a fact on disk. Where its classification
DISAGREES with the ``resolved_by`` string in `freeze_status.BLOCKED_REASONS`, the
disagreement is reported as a finding instead of being quietly overridden: a
stale reason in a committed file is itself a defect, and hiding it by writing a
better one somewhere else would leave the wrong one in place.

THE CLASSES
-----------
``resolvable_now``
    The artifact exists, or is computable from committed bytes plus installed
    files. No process is started, nothing is cleared. What remains is a PIN
    decision -- writing a value into config.json, which is bound to the
    three-way verbatim contract -- and that is root's, not mine.

``offline_work_owed``
    CPU only. No model, no server, no quiescence gate. The work is simply not
    done. Reachable without execution in the sense the question asks, but not
    free.

``execution_blocked``
    Needs a model call or a live server of my own. Root has not cleared it.
    No amount of offline work reaches these.

WHAT THIS DOES NOT DO
---------------------
It freezes nothing, pins nothing, and writes nothing into config.json. It starts
no process and makes no network request. The one digest it computes -- the
Seatbelt profile -- is computed under the PRESCRIBED TMPDIR, because an
ambient-TMPDIR digest was once computed and promoted into config.json,
ARCHITECTURE 6.1 and protocol Appendix B before anyone noticed. Computing it
here and reporting it is not promoting it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
LS = HERE.parent / 'local_stream'
for _p in (str(LAB), str(LS)):
    if _p not in sys.path:                                     # pragma: no cover
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
import freeze_status                                           # noqa: E402

REPO = HERE.parents[1]
RESULTS = Path(lab_common.RESULTS_ROOT)

RESOLVABLE_NOW = 'resolvable_now'
OFFLINE_WORK_OWED = 'offline_work_owed'
EXECUTION_BLOCKED = 'execution_blocked'


def disagreements_keys(rows: List[Dict[str, str]]) -> List[str]:
    """The distinct keys named by a disagreement list, in stable order."""
    return sorted({r['key'] for r in rows})


# --------------------------------------------------------------------------
# machine-checked facts. Each returns what it MEASURED, never what I expect.
# --------------------------------------------------------------------------

def _profile_digests() -> Dict[str, Any]:
    """The Seatbelt digest under the prescribed TMPDIR, and under the ambient one.

    Both are reported. The point is that they DIFFER: the digest is a function of
    TMPDIR (`sandbox.seatbelt_profile` reads `tempfile.gettempdir()` twice, once
    for the write-deny list and once via `sandbox_base_dir`). Exporting TMPDIR is
    not enough in-process -- `tempfile` caches `tempfile.tempdir` -- so the knob
    is set directly here.
    """
    import sandbox                                             # noqa: PLC0415
    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    prescribed = lab_common.prescribed_tmpdir(cfg)
    py = sandbox.base_interpreter()
    saved = tempfile.tempdir
    out: Dict[str, Any] = {'prescribed_tmpdir': prescribed,
                           'ambient_tmpdir': os.path.realpath(saved
                                                              or tempfile.gettempdir())}
    try:
        for label, tmp in (('ambient', out['ambient_tmpdir']),
                           ('prescribed', prescribed)):
            tempfile.tempdir = tmp
            os.makedirs(tmp, exist_ok=True)
            base = sandbox.sandbox_base_dir()
            prof = sandbox.seatbelt_profile(py, base)
            out[label] = {'base_dir': base,
                          'sha256': hashlib.sha256(prof.encode()).hexdigest(),
                          'profile_bytes': len(prof.encode())}
    finally:
        tempfile.tempdir = saved
    out['digests_differ'] = out['ambient']['sha256'] != out['prescribed']['sha256']
    out['interpreter_embedded'] = py
    out['host_specific_inputs'] = [
        'the operator home directory, in two deny rules',
        'the interpreter PREFIX, in the file-read allow rule -- including the '
        'CPython patch version, so an interpreter upgrade moves this digest',
    ]
    probe = RESULTS / 'CONTAINMENT_PROBE_RECEIPT.json'
    if probe.is_file():
        rec = json.loads(probe.read_text('utf-8'))
        got = rec.get('profile_sha256')
        out['containment_receipt_profile_sha256'] = got
        out['containment_probe_ran_under_prescribed_tmpdir'] = (
            got == out['prescribed']['sha256'])
    out['config_sandbox_profile_sha256'] = (
        (cfg.get('sandbox') or {}).get('profile_sha256'))
    return out


def _containment_owed() -> Dict[str, Any]:
    """Root's own words on this probe, read from the committed receipt."""
    probe = RESULTS / 'CONTAINMENT_PROBE_RECEIPT.json'
    if not probe.is_file():
        return {'receipt_present': False}
    rec = json.loads(probe.read_text('utf-8'))
    corr = next((v for k, v in rec.items() if k.startswith('CORRECTION_root_')), {})
    return {
        'receipt_present': True,
        'receipt_path': str(probe.relative_to(REPO)),
        'verdict': rec.get('verdict'),
        'root_no_key_promoted': corr.get('no_key_promoted'),
        'root_still_owed': corr.get('still_owed'),
        'denied_filesystem_operations': (rec.get('denied_attempts_corrected') or {})
        .get('denied_filesystem_operations'),
    }


def _loaded_sweep_citation() -> Dict[str, Any]:
    """Root RETRACTED 'the reference sweep is offline'. Checked, not remembered."""
    out: Dict[str, Any] = {}
    for rel, needle in (
            ('reviews/live_roster_root_decisions_20260921_1854.md',
             'called the reference sweep offline'),
            ('reviews/live_prefreeze_root_decisions_20260921_1929.md',
             'No unloaded substitution.')):
        doc = REPO / rel
        present = doc.is_file() and needle in doc.read_text('utf-8', errors='replace')
        out[rel] = {'needle': needle, 'found_in_committed_document': present}
    out['what_root_ruled'] = (
        'protocol 3.2(4) requires concurrent 1024-token generation DURING the '
        'reference sweep. Root: "Do not substitute an unloaded sweep." The sweep '
        'belongs in the consolidated finite prefreeze model-execution plan and '
        'remains uncleared.')
    return out


def _calibration_cost() -> Dict[str, Any]:
    """The prefreeze episode count, multiplied out from config rather than quoted."""
    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    plan = ((cfg.get('prefreeze') or {}).get('calibration_plan') or {})
    factors = ('repetitions', 'smoke_tasks', 'workflows', 'models', 'concurrency_levels')
    product = 1
    for f in factors:
        product *= int(plan.get(f, 0) or 0)
    return {'plan': plan, 'factors_multiplied': product,
            'declared_episodes': plan.get('episodes'),
            'arithmetic_agrees': product == plan.get('episodes'),
            'these_are_model_calls': True}


def _license_state() -> Dict[str, Any]:
    # The sink is write-once, so a corrected retrieval lands beside its
    # predecessor rather than replacing it. Read the LATEST, and say which one was
    # read: a tool pointed at a receipt I have already labelled stale is a trap.
    candidates = sorted(RESULTS.glob('LICENSE_EVIDENCE*.json'))
    if not candidates:
        return {'receipt_present': False}
    ev = candidates[-1]
    rec = json.loads(ev.read_text('utf-8'))
    kinds = {k: (v.get('retained') or {}).get('evidence_kind')
             for k, v in rec['servers'].items()}
    return {
        'receipt_present': True,
        'receipt_path': str(ev.relative_to(REPO)),
        'all_servers_have_evidence': rec.get('all_servers_have_evidence'),
        'license_evidence_sha256': rec.get('license_evidence_sha256'),
        'evidence_kind_by_server': kinds,
        'kinds_are_homogeneous': len(set(kinds.values())) == 1,
        'heterogeneity_finding': (
            'the two servers do NOT carry the same kind of evidence. One served a '
            'licence TEXT at the pinned revision; the other served none (three '
            '404s recorded) and only DECLARES apache-2.0 in its model card. A '
            'digest over the pair pins a text and a claim under one key.'
            if len(set(kinds.values())) != 1 else None),
        'promoted_into_config': False,
    }


def _server_dependent_state() -> Dict[str, Any]:
    """Nothing scraped from a live server has been deposited. Checked by listing."""
    names = sorted(p.name for p in RESULTS.glob('*')
                   if any(t in p.name.lower() for t in ('props', 'serving_manifest',
                                                        'generation_settings')))
    return {
        'artifacts_found': names,
        'note': ('the authorized 2026-09-22 smoke started a server, but it was '
                 'generation-only: root ruled the verifier-setting and anchor '
                 'obligations "are not performed by this generation-only smoke". '
                 'That server is stopped, and the authorization was for exactly '
                 'one start with no retry or restart. A /props scrape needs a new '
                 'server start, which is a new clearance.'),
    }


# --------------------------------------------------------------------------

def _committed_blocked_reasons(rev: str = 'HEAD') -> Dict[str, Any]:
    """``BLOCKED_REASONS`` as the COMMITTED freeze_status.py declares it.

    Repairing a stale reason erases the evidence that it was stale: after the
    edit, comparing this module against the imported map shows agreement, and the
    finding disappears from the receipt that was supposed to record it. So the
    comparison is made against the committed blob, read out of git, not against my
    recollection of what the strings used to say.

    Parsed with ``ast``, never executed: this reads a file from history and
    running it would be running history.
    """
    import ast                                                 # noqa: PLC0415
    import subprocess                                          # noqa: PLC0415
    rel = 'experiments/live_ab_tools/freeze_status.py'
    try:
        src = subprocess.run(['git', 'show', '%s:%s' % (rev, rel)],
                             capture_output=True, text=True, cwd=str(REPO),
                             timeout=60, check=True).stdout
    except Exception as exc:                                   # noqa: BLE001
        return {'available': False, 'error': '%s: %s' % (type(exc).__name__, exc)}
    for node in ast.walk(ast.parse(src)):
        targets = getattr(node, 'targets', None) or (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == 'BLOCKED_REASONS':
                try:
                    return {'available': True, 'rev': rev,
                            'reasons': ast.literal_eval(node.value)}
                except ValueError as exc:
                    return {'available': False, 'error': 'literal_eval: %s' % exc}
    return {'available': False, 'error': 'BLOCKED_REASONS not found at %s' % rev}


def classify() -> Dict[str, Any]:
    status = freeze_status.status()
    missing = sorted(status.get('still_required', []))
    profile = _profile_digests()
    containment = _containment_owed()
    sweep = _loaded_sweep_citation()
    calib = _calibration_cost()
    lic = _license_state()
    serving = _server_dependent_state()

    table: Dict[str, Dict[str, Any]] = {
        'sandbox_profile_sha256': {
            'klass': RESOLVABLE_NOW,
            'needs': 'nothing to run; a pin decision only',
            'value_if_pinned': profile['prescribed']['sha256'],
            'basis': ('computed here from experiments/local_stream/sandbox.py under '
                      'the PRESCRIBED TMPDIR %s; it equals the digest the deposited '
                      'containment probe ran under (%s) and differs from the ambient '
                      'digest %s' % (profile['prescribed_tmpdir'],
                                     profile.get('containment_probe_ran_under_'
                                                 'prescribed_tmpdir'),
                                     profile['ambient']['sha256'])),
            'why_not_pinned_here': (
                'config.json is bound to the three-way verbatim contract. An '
                'ambient-TMPDIR digest was promoted into that contract once '
                'already. The value is reported; root rules on the pin.'),
            'evidence': profile,
        },
        'license_evidence_sha256': {
            'klass': RESOLVABLE_NOW,
            'needs': 'nothing further to run; a pin decision only',
            'value_if_pinned': lic.get('license_evidence_sha256'),
            'basis': ('root authorized the retrieval explicitly and told me not to '
                      'treat it as blocked; both revisions were fetched this cycle '
                      'and deposited'),
            'caveat': lic.get('heterogeneity_finding'),
            'evidence': lic,
        },
        'containment_probe_sha256': {
            'klass': OFFLINE_WORK_OWED,
            'needs': ('the two-worker exclusion fixture with a REAL contender '
                      'blocked while the first holds the production lock, plus '
                      'per-attempt negative-control evidence'),
            'basis': ('a probe receipt exists and root accepted a BOUNDED subset of '
                      'it, but root also wrote "no trial-profile key is promoted '
                      'from this probe summary" and named what is still owed'),
            'cpu_only': True, 'needs_model': False, 'needs_clearance': False,
            # The committed reason is not wrong about the COST -- it really is
            # CPU-only -- so the cost_understated rule below cannot see it. It is
            # wrong about SUFFICIENCY: it says "a CPU-only probe run" resolves the
            # key, and a probe run already happened, after which root declined to
            # promote a key from it. Flagged explicitly because a rule that only
            # compares cost would pass this silently.
            'prior_reason_stale': {
                'kind': 'sufficiency_overstated',
                'act_already_performed': 'the CPU-only probe was run and deposited',
                'key_still_missing': True,
            },
            'evidence': containment,
        },
        'roster_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the LOADED reference sweep -- model calls, uncleared',
            'basis': sweep['what_root_ruled'],
            'evidence': sweep,
        },
        'task_content_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the same loaded reference sweep; same artifact as the roster',
            'basis': sweep['what_root_ruled'],
            'evidence': sweep,
        },
        'arrival_order_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the roster, which is loaded-sweep blocked',
            'basis': ('lab_design.arrival_order is PURE and costs nothing -- but it '
                      'takes the roster as input, so it inherits the roster block. '
                      'Pure is not the same as reachable.'),
            'evidence': sweep,
        },
        'serving_manifest_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'a running llama-server of my own, under a new clearance',
            'basis': 'describes the process in front of the model; not on disk',
            'evidence': serving,
        },
        'golden_props_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'one /props scrape from a live server of my own',
            'basis': 'read from a live server',
            'evidence': serving,
        },
        'golden_generation_settings_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the same live scrape',
            'basis': 'reported by a live server',
            'evidence': serving,
        },
        'prefreeze_head': {
            'klass': EXECUTION_BLOCKED,
            'needs': '%d calibration episodes -- model calls, uncleared' % (
                calib['factors_multiplied']),
            'basis': 'config.prefreeze.calibration_plan, multiplied out here',
            'evidence': calib,
        },
        'prefreeze_bytes': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the same calibration artifact',
            'basis': 'same artifact as prefreeze_head',
            'evidence': calib,
        },
        'prefreeze_file_sha256': {
            'klass': EXECUTION_BLOCKED,
            'needs': 'the same calibration artifact',
            'basis': 'same artifact as prefreeze_head',
            'evidence': calib,
        },
    }

    # -- keys I classified that are NOT missing, and missing keys I did not
    #    classify. Either is a hole in MY accounting, reported rather than hidden.
    unclassified = [k for k in missing if k not in table]
    stale_entries = [k for k in table if k not in missing]

    # -- where this contradicts the reason string committed in freeze_status.py --
    # Compared against the COMMITTED blob, so a repair made in the same cycle does
    # not silently delete its own finding. If git cannot supply it, the in-process
    # map is used and the receipt says so rather than pretending to a provenance
    # it does not have.
    committed = _committed_blocked_reasons()
    reason_source = ('committed blob at %s' % committed.get('rev')
                     if committed.get('available') else
                     'IN-PROCESS import (git unavailable: %s)'
                     % committed.get('error'))
    reasons = (committed.get('reasons') if committed.get('available')
               else freeze_status.BLOCKED_REASONS)

    disagreements: List[Dict[str, str]] = []
    for key, entry in table.items():
        prior = reasons.get(key)
        if not prior:
            continue
        said = prior.get('resolved_by', '')
        low = said.lower()
        prior_says_offline = ('no model' in low or 'no quiescence' in low
                              or 'needs no quiescence' in low)
        if entry['klass'] == EXECUTION_BLOCKED and prior_says_offline:
            disagreements.append({
                'key': key,
                'kind': 'cost_understated',
                'freeze_status_resolved_by': said,
                'freeze_status_why': prior.get('why', ''),
                'this_module_says': entry['needs'],
                'defect': ('a committed file states this hole needs no model call '
                           'and no clearance. Root ruled otherwise and the file was '
                           'never updated.'),
            })
        # A reason can be right about the price and wrong about what it buys. The
        # rule above compares cost only, so a sufficiency defect is declared at the
        # entry and carried here rather than inferred.
        stale = entry.get('prior_reason_stale')
        if stale and stale.get('key_still_missing'):
            disagreements.append({
                'key': key,
                'kind': stale['kind'],
                'freeze_status_resolved_by': said,
                'freeze_status_why': prior.get('why', ''),
                'this_module_says': entry['needs'],
                'defect': ('the committed reason names an act that has ALREADY been '
                           'performed (%s) while the key is still missing, so it '
                           'describes something that did not resolve the key.'
                           % stale['act_already_performed']),
            })

    counts: Dict[str, int] = {}
    for entry in table.values():
        counts[entry['klass']] = counts.get(entry['klass'], 0) + 1

    return {
        'schema': 'live_ab/freeze_reachability-v3',
        'supersedes': {
            'paths': ['results/live_ab/FREEZE_REACHABILITY.json',
                      'results/live_ab/FREEZE_REACHABILITY_v2.json'],
            'what_they_recorded': ('v1: the same classification against an UNREPAIRED '
                                   'freeze_status.py, 2 disagreements, no '
                                   'sufficiency rule. v2: 3 disagreements, but it '
                                   'read LICENSE_EVIDENCE.json (v1), whose saved_as '
                                   'paths were stale after the licence directory was '
                                   'renamed; its digest value was already identical. '
                                   'Both retained: the write-once sink refused to '
                                   'overwrite them, which is the sink working.'),
        },
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'question': ('of the freeze-bundle keys build_freeze_bundle still refuses '
                     'on, which are reachable WITHOUT execution?'),
        'authority': ('my own stated default on issue #11 at 63e4f9b, left in force '
                      'by root silence'),
        'resolved_offline_count': status['resolved_offline_count'],
        'required_keys_total': status['required_keys_total'],
        'still_required': missing,
        'still_required_count': len(missing),
        'classification': table,
        'counts': counts,
        'answer': {
            RESOLVABLE_NOW: sorted(k for k, v in table.items()
                                   if v['klass'] == RESOLVABLE_NOW),
            OFFLINE_WORK_OWED: sorted(k for k, v in table.items()
                                      if v['klass'] == OFFLINE_WORK_OWED),
            EXECUTION_BLOCKED: sorted(k for k, v in table.items()
                                      if v['klass'] == EXECUTION_BLOCKED),
        },
        'unclassified_missing_keys': unclassified,
        'classified_but_not_missing': stale_entries,
        'accounting_complete': not unclassified and not stale_entries,
        'disagreements_with_committed_reasons': disagreements,
        'reason_source': reason_source,
        'reasons_repaired_in_working_tree': sorted(
            k for k in disagreements_keys(disagreements)
            if (freeze_status.BLOCKED_REASONS.get(k) or {}).get('resolved_by')
            != (reasons.get(k) or {}).get('resolved_by')),
        'nothing_executed': ['no model call', 'no server start', 'no episode',
                             'no network request', 'no config.json write',
                             'no freeze deposited'],
        'must_not_claim': [
            'that any key is now frozen -- none is, and build_freeze_bundle still '
            'refuses the bundle',
            'that a resolvable_now key is pinned: reporting a value is not writing '
            'it into the contract',
            'that the offline_work_owed key is cheap because it is CPU-only; root '
            'named specific evidence it does not yet have',
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    # v1 was deposited before the stale reasons in freeze_status.py were repaired
    # and before the sufficiency rule existed; it records 2 disagreements against
    # an unrepaired tree. The sink is write-once and refused to overwrite it,
    # which is correct: that receipt is the evidence of the pre-repair state.
    ap.add_argument('--out', type=Path,
                    default=RESULTS / 'FREEZE_REACHABILITY_v3.json')
    a = ap.parse_args(argv)
    result = classify()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, result)
    print('%d of %d keys resolved; %d still required'
          % (result['resolved_offline_count'], result['required_keys_total'],
             result['still_required_count']))
    for klass in (RESOLVABLE_NOW, OFFLINE_WORK_OWED, EXECUTION_BLOCKED):
        print('\n%s (%d):' % (klass, len(result['answer'][klass])))
        for k in result['answer'][klass]:
            print('  %-36s %s' % (k, result['classification'][k]['needs']))
    print('\naccounting_complete:', result['accounting_complete'])
    print('disagreements with committed freeze_status reasons:',
          len(result['disagreements_with_committed_reasons']))
    for d in result['disagreements_with_committed_reasons']:
        print('  ! %s: committed file says %r' % (d['key'],
                                                  d['freeze_status_resolved_by']))
    print('\nwritten:', a.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
