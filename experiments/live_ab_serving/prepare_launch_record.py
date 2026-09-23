"""Prepare, and dry-run the preflight of, a PROSPECTIVE launch record for review.

Root, 2026-09-23 17:52 (reviews/dependency_callsite_disposition_20260923_1752.md):
"bind source/patch/build identity and the v3 closure at preparation; before
`Popen`, rederive the selected dependency graph using the exact pinned
executable-directory cwd and sanitized child environment that `Popen` will
receive ... Deliver this finite pre-run bundle on the working branch for
explicit review before any trial episode."

THIS IS PREPARATION, NOT A LAUNCH. No engineering attempt is authorized (root
16:30: "The amendment adds no loaded attempt and does not reopen a spent
engineering authorization"). The record is written for root's review, and the
preflight is DRY-RUN: the supervisor's own checks -- `verify_source_binding`,
`verify_acquisition_code` and `dependency_closure.verify_closure` under the
decided launch context -- are called exactly as `main()` calls them, and
`Popen` is never reached, because `main()` is never called.

What it reads: the candidate's load commands and symbol tables (`otool -h/-l`,
`nm -u`: metadata readers), the executable directory's listing, the source
tree's git index (`rev-parse`, `status`, `apply --reverse --check`: read-only),
and file bytes. It executes no candidate, loads no model and starts no server.

What it does NOT bind, and says so: the serving inputs a launch would also need
-- the request, the server arguments and the host/boot identity -- belong to the
finite plan's stage-0 specification, which root has not approved.

`--stage0 <json>` (root 19:26: "Bind stage-0 request/argv ... in the final
working-branch bundle") binds the PROPOSED request and server arguments into the
record and checks them offline, as `main()` would: the assembled manifest goes
through `validate_manifest` (host/boot identity are placeholders, measured only
at a launch), every path argument must lie outside the executable directory
(`_inside`), the run token must be a plain name, and the argv the supervisor
would build must equal the frozen protocol 2.2 line (`lab_server.server_argv`).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import run_smoke as rs                                         # noqa: E402

dc = rs.dc


def sha_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--declaration', default='results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json')
    ap.add_argument('--snapshot', default='results/live_ab/CANDIDATE_BUILD_CONFIG_SNAPSHOT.json')
    ap.add_argument('--stage0', default=None)
    a = ap.parse_args(argv)
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime())
    out_path = REPO / 'results' / 'live_ab' / ('PROSPECTIVE_LAUNCH_RECORD_%s.json' % stamp)
    if out_path.exists():
        print('refusing: %s exists (write-once)' % out_path, file=sys.stderr)
        return 2
    manifest_path = REPO / a.declaration
    snapshot_rel = a.snapshot
    patch_rel = 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
    cand = json.loads(manifest_path.read_text())
    launcher = cand['candidate_instrument']['launcher']['path']
    source_tree = cand['source_and_patch']['source_tree']
    cfg = json.loads((rs.LAB / 'config.json').read_bytes())
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # -- the bindings, measured now --------------------------------------------
    rc, head, err = rs.SOURCE_READERS['git'](['-C', source_tree, 'rev-parse', 'HEAD'])
    patch_sha = sha_path(REPO / patch_rel)
    source_binding = {
        'source_tree': source_tree, 'head': head.strip() if rc == 0 else None,
        'patch_path': patch_rel, 'patch_sha256': patch_sha,
        'build_snapshot': {'path': snapshot_rel, 'sha256': sha_path(REPO / snapshot_rel)}}
    sb_check = rs.verify_source_binding(source_binding, patch_sha256=patch_sha)
    acquisition_code = {n: sha_path(p) for n, p in rs.ACQUISITION_CODE.items()}
    code_check = rs.verify_acquisition_code(acquisition_code)

    exe_dir = str(Path(launcher).parent)
    # The environment the child WOULD receive: this process's, with every
    # GGML_*/DYLD_*/LLAMA_* removed. Only names are recorded.
    removed = sorted(k for k in os.environ if k.startswith(rs.CHILD_ENV_REMOVED_PREFIXES))
    child_env = {k: v for k, v in os.environ.items()
                 if not k.startswith(rs.CHILD_ENV_REMOVED_PREFIXES)}
    ctx = {'executable_invoked_path': launcher, 'cwd': exe_dir,
           'compiled_backend_dir': sb_check.get('compiled_backend_dir'),
           'environment': child_env}
    frozen = dc.derive_closure(launcher, launch_context=ctx, **rs.DEPENDENCY_READERS)

    # -- the dry-run preflight: main()'s own checks, no Popen -------------------
    verify = dc.verify_closure(frozen, launch_context=ctx, **rs.DEPENDENCY_READERS)
    # and the closure must BE the declared build (review finding, 18:50)
    bb_check = rs.verify_build_binding(frozen, source_binding,
                                       realpath=rs.DEPENDENCY_READERS['realpath'])
    model = cfg['servers']['coder']
    record = {
        'schema': 'live_ab/prospective_launch_record-v1',
        'status': ('PROPOSED FOR ROOT REVIEW. Not authorized: no engineering attempt, '
                   'model load, server start or trial is authorized by this record.'),
        'generated_utc': t0,
        'convention': 'deterministic-path',
        'authority': 'root, reviews/dependency_callsite_disposition_20260923_1752.md',
        'nothing_executed_THIS_RECEIPT': (
            'metadata readers (otool -h/-l, nm -u), a directory listing and read-only '
            'git queries; no candidate execution, model load, server start or build'),
        'launch_manifest_fields': {
            'launcher': {'path': launcher,
                         'sha256': frozen['files'].get(launcher, {}).get('sha256')},
            'model': {'file': model['file'], 'sha256': model['sha256_expected'],
                      'source': 'experiments/live_ab/config.json servers.coder'},
            'port': model['port'],
            'patch_sha256': patch_sha,
            'caps': cfg[rs.CONFIG_SECTION],
            'dependency_closure': frozen,
            'source_binding': source_binding,
            'acquisition_code': acquisition_code,
        },
        'launch_context_decided': {
            'executable': launcher, 'cwd': exe_dir,
            'removed_environment_names_in_this_process': removed,
            'compiled_backend_dir': ctx['compiled_backend_dir'],
            'source': 'root 16:30 decisions 1-2'},
        'preflight_dry_run': {
            'source_binding': sb_check,
            'build_binding': bb_check,
            'acquisition_code': {k: code_check[k] for k in ('verified', 'problems',
                                                            'config_section')},
            'dependency_closure': {k: verify.get(k) for k in (
                'verified', 'problems', 'edges_checked', 'edges_agreeing', 'files_checked')},
            'bounded': (verify.get('dynamic_loading_now') or {}).get('bounded'),
            'all_pass': bool(sb_check['verified'] and code_check['verified']
                             and bb_check['verified'] and verify.get('verified')),
        },
        'derived_closure_summary': {
            'resolved': frozen['resolved'], 'members': frozen['member_count'],
            'edges': len(frozen['edges']), 'unresolved': frozen['unresolved'],
            'duplicate_install_names': frozen['duplicate_install_names'],
            'dlopen_importers': [Path(p).name for p in
                                 frozen['dynamic_loading']['members_importing_dlopen']],
            'search_locations': [(r['directory'], len(r.get('candidates') or []))
                                 for r in frozen['dynamic_loading']['search_locations']],
        },
        'PENDING_not_bound_here': {
            'request': 'prompt, max_tokens (<= 1,024 for 2 attempts), temperature, seed',
            'server_args': ('the server arguments of a future engineering acquisition; '
                            'the spent smoke used different ones from the frozen trial '
                            'launch line'),
            'host_id_boot_id': 'measured at the launch, not at preparation',
            'why': 'these belong to the finite plan\'s stage-0 specification, which root '
                   'has not approved; no engineering attempt is authorized',
        },
        'staleness': ('the acquisition_code pins name the exact files at generation; any '
                      'later change to them makes a launch with this record refuse, by '
                      'design'),
    }
    if a.stage0:
        record['stage0_binding'] = bind_stage0(a.stage0, record, cfg, launcher, exe_dir)
        record['preflight_dry_run']['all_pass'] = bool(
            record['preflight_dry_run']['all_pass'] and record['stage0_binding']['all_pass'])
        record['PENDING_not_bound_here'] = {
            'host_id_boot_id': 'measured at the launch, not at preparation',
            'why': 'identity of the boot that launches; the request and server '
                   'arguments are bound in stage0_binding (PROPOSED)'}
    out_path.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(out_path, 'all_pass=%s resolved=%s members=%s' % (
        record['preflight_dry_run']['all_pass'], frozen['resolved'], frozen['member_count']))
    return 0


def bind_stage0(spec_rel: str, record: dict, cfg: dict, launcher: str, exe_dir: str) -> dict:
    """Offline checks of a PROPOSED stage-0 request and server arguments, plus
    negative controls: the same checks on three altered argument lists, each of
    which must fail, so a pass is shown to be something the checks can refuse."""
    sys.path.insert(0, str(rs.LAB))
    import lab_common
    spec_path = REPO / spec_rel
    spec = json.loads(spec_path.read_text())
    args = [x.replace('@RESULTS_ROOT@', str(lab_common.RESULTS_ROOT))
            for x in spec['server_args']]
    out = _stage0_checks(spec, args, record, cfg, launcher, exe_dir)
    log_i = args.index('--log-file') + 1
    controls = {
        'model_flag_inside_server_args': args + ['-m', '/elsewhere/other.gguf'],
        'frozen_flag_dropped (--jinja)': [x for x in args if x != '--jinja'],
        'relative_log_path': args[:log_i] + ['logs/server.log'] + args[log_i + 1:],
    }
    out['negative_controls'] = {
        name: {'all_pass': _stage0_checks(spec, alt, record, cfg, launcher, exe_dir)['all_pass']}
        for name, alt in controls.items()}
    out['negative_controls_all_refused'] = not any(
        v['all_pass'] for v in out['negative_controls'].values())
    out['spec'] = {'path': spec_rel, 'sha256': sha_path(spec_path), 'status': spec['status']}
    out['all_pass'] = bool(out['all_pass'] and out['negative_controls_all_refused'])
    return out


def _stage0_checks(spec: dict, args: list, record: dict, cfg: dict, launcher: str,
                   exe_dir: str) -> dict:
    import lab_server
    placeholder = 'PLACEHOLDER-measured-at-launch'
    manifest = dict(record['launch_manifest_fields'], request=spec['request'],
                    server_args=args, host_id=placeholder, boot_id=placeholder)
    manifest_problems = rs.validate_manifest(manifest)
    inside = [v for v in rs.server_arg_paths(args) if rs._inside(v, exe_dir)]
    token = spec['run_token']
    token_ok = bool(rs.TOKEN_RE.fullmatch(token)) and '..' not in token
    # the argv main() builds: [launcher, '-m', model] + server_args (run_smoke.py)
    model = '<MODEL: %s, found at launch>' % cfg['servers']['coder']['file']
    built = [launcher, '-m', model] + args
    la = cfg['llama_args']
    frozen = lab_server.server_argv(lab_server.ServerSpec(
        server_id='coder', port=cfg['servers']['coder']['port'],
        alias=cfg['servers']['coder']['alias'], gguf_path=Path(model),
        gguf_bytes=cfg['servers']['coder']['bytes'],
        gguf_sha256=cfg['servers']['coder']['sha256_expected'],
        llama_bin=Path(launcher), llama_commit=cfg['llama_cpp']['commit'], args=tuple(la),
        log_path=Path(args[args.index('--log-file') + 1]),
        n_slots=int(la[la.index('-np') + 1]), n_ctx=int(la[la.index('-c') + 1])))
    frozen_ok = built == frozen
    return {
        'request': spec['request'], 'server_args': args, 'run_token': token,
        'argv_as_the_supervisor_builds_it': built,
        'checks': {
            'validate_manifest_problems': manifest_problems,
            'validate_manifest_note': ('host_id and boot_id are placeholders here, so '
                                       'their check is structural only'),
            'path_arguments_inside_the_executable_directory': inside,
            'run_token_is_a_plain_name': token_ok,
            'argv_equals_frozen_protocol_2_2_line': frozen_ok,
            'frozen_line_rendered_by': 'experiments/live_ab/lab_server.py server_argv',
            'token_budget': '%d planned attempts x %d max_tokens = %d <= %d' % (
                rs.PLANNED_WIRE_ATTEMPTS, spec['request']['max_tokens'],
                rs.PLANNED_WIRE_ATTEMPTS * spec['request']['max_tokens'], rs.TOKEN_CAP),
        },
        'all_pass': bool(not manifest_problems and not inside and token_ok and frozen_ok),
    }


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
