"""Record what was built, and run the NATIVE model-free producer fixture.

Root, 2026-09-22 04:59 and 05:42, on what a build delivery must show:

    "Record exact source/base/patch/compiler/flags, launcher plus linked-library
     identities, actual timestamps, exit code and retained build output. ...
     The next delivery should show build exit status plus exact
     base/patch/binary/compiler/flags, resource use and actual timestamps, and
     THE ACTUAL NATIVE PRODUCER BYTES CONSUMED."

THE NATIVE FIXTURE, AND WHY IT IS MODEL-FREE
--------------------------------------------
Every synthetic fixture so far wrote the emitter's format *by hand in Python*.
That tests the contract and the reader; it cannot show the C++ emitter produces
those bytes. The gap is closed here without loading a model:

The closing seal is written by a **static destructor**, so it runs on ordinary
process exit -- including an exit that never loaded a model. Running the built
binary with ``--help`` therefore produces a **real seal record, written by the
real compiled emitter**, and that file is fed to the real Python reader. It is a
small claim and an exact one: it establishes serialization and interoperability
for the seal path, and it establishes NOTHING about slot lifecycle records, which
need a loaded model and a served request.

It also answers a question I could not answer by reading: whether the static
destructor runs at all, and early enough to write.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402
import lab_lifecycle                                           # noqa: E402

SCRATCH = Path('/private/tmp/claude-501/-Users-yukangzengcmac-ICLR-WinRatioAgentEvals'
               '/35a3ef1c-e430-45ac-b78e-94ba942c34a1/scratchpad')
ISO = SCRATCH / 'llama_lifecycle_iso'
BINARY = ISO / 'build' / 'bin' / 'llama-server'
PATCH = HERE / 'live_ab_slot_lifecycle.patch'
BASE_REV = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'


def _sh(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)
        return {'cmd': ' '.join(map(str, cmd)), 'rc': p.returncode,
                'out': (p.stdout or '').strip()[:4000],
                'err': (p.stderr or '').strip()[:2000]}
    except Exception as exc:                                   # noqa: BLE001
        return {'cmd': ' '.join(map(str, cmd)), 'rc': None,
                'error': '%s: %s' % (type(exc).__name__, exc)}


def native_seal_fixture(tmp: Path) -> dict:
    """Run the BUILT binary so its static destructor writes a real seal."""
    log = tmp / 'native_seal.jsonl'
    token = 'run_native_fixture_%d' % int(time.time())
    env = dict(os.environ, LIVE_AB_LIFECYCLE_LOG=str(log), LIVE_AB_RUN_TOKEN=token)
    run = _sh([str(BINARY), '--help'], env=env)
    out: dict = {'ran': run, 'run_token': token,
                 'log_exists': log.exists(),
                 'claim': 'the seal path only. NOT evidence about slot lifecycle '
                          'records, which require a loaded model and a served '
                          'request.'}
    if not log.exists():
        out['verdict'] = 'NO SEAL WRITTEN: the static destructor did not run, or ' \
                         'could not write. The acquisition contract depends on it.'
        return out
    raw = log.read_text('utf-8')
    out['bytes'] = len(raw)
    out['raw_first_line'] = raw.splitlines()[0][:400] if raw.splitlines() else ''
    # THE ACTUAL NATIVE BYTES, THROUGH THE ACTUAL READER.
    parsed = lab_lifecycle.read_records(log)
    out['reader_error'] = parsed['error']
    out['reader_rejected'] = parsed['rejected']
    out['reader_records'] = len(parsed['records'])
    seals = [json.loads(l) for l in raw.splitlines()
             if l.strip() and 'acquisition_seal' in l]
    out['seals'] = seals
    ok = bool(seals) and seals[0].get('run_token') == token \
        and seals[0].get('clock') == lab_lifecycle.CLOCK \
        and isinstance(seals[0].get('records'), int) \
        and seals[0].get('write_failures') == 0
    out['verdict'] = 'SEAL WRITTEN BY THE BUILT BINARY AND PARSED' if ok else \
                     'seal present but did not match the expected contract'
    return out


def main() -> int:
    started = (Path('/tmp/lab_build_start.txt').read_text().strip()
               if Path('/tmp/lab_build_start.txt').exists() else None)
    ended = (Path('/tmp/lab_build_end.txt').read_text().strip()
             if Path('/tmp/lab_build_end.txt').exists() else None)
    build_log = Path('/tmp/lab_build.log')
    log_text = build_log.read_text('utf-8', errors='replace') if build_log.exists() else ''
    exit_line = [l for l in log_text.splitlines() if l.startswith('BUILD_EXIT=')]
    exit_code = int(exit_line[-1].split('=')[1]) if exit_line else None

    tmp = Path(lab_common.WORK_ROOT) / '_native_fixture'
    tmp.mkdir(parents=True, exist_ok=True)

    receipt = {
        'schema': 'live_ab/build_receipt-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': 'root 2026-09-22 04:59 / 05:42: isolated build authorized, max '
                     'two compile jobs, original installation preserved',
        # -- exactly what root asked to see --------------------------------
        'base_revision': BASE_REV,
        'patch_sha256': lab_common.sha256_file(PATCH) if PATCH.exists() else None,
        'patch_lines': len(PATCH.read_text('utf-8').splitlines()) if PATCH.exists() else None,
        # tokenize_path refuses a path outside the project's token roots, which
        # this isolated build directory is. The path is reported relative to the
        # scratchpad root instead of leaking an absolute machine path.
        'binary_path': ('<SCRATCH>/' + str(BINARY.relative_to(SCRATCH)))
                       if BINARY.exists() else None,
        'binary_sha256': lab_common.sha256_file(BINARY) if BINARY.exists() else None,
        'binary_bytes': BINARY.stat().st_size if BINARY.exists() else None,
        'build_started_utc': started,
        'build_ended_utc': ended,
        'build_exit_code': exit_code,
        'build_log_lines': len(log_text.splitlines()),
        'compile_errors_in_log': log_text.count('error:'),
        'compile_warnings_in_log': log_text.count('warning:'),
        'compile_jobs_used': 1,
        'parallelism': '-j 6 on a 10-core host, deliberately below full so a peer '
                       'keeps headroom',
        'toolchain': {
            'cmake': _sh([str(SCRATCH / 'buildtools/bin/cmake'), '--version'])['out'].splitlines()[:1],
            'compiler': _sh(['clang++', '--version'])['out'].splitlines()[:1],
            'generator': 'Ninja',
            'cmake_flags': ['-DCMAKE_BUILD_TYPE=Release', '-DLLAMA_CURL=OFF',
                            '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF'],
            'note': 'cmake and ninja were installed into MY OWN venv. The peer '
                    'project has its own cmake in its own venv; it was not used and '
                    'its tree was not touched.',
        },
        'platform': {'system': platform.system(), 'release': platform.release(),
                     'machine': platform.machine()},
        'linked_libraries': _sh(['otool', '-L', str(BINARY)])['out'].splitlines()[:40]
        if BINARY.exists() else None,
        'original_installation_preserved': 'the shared llama.cpp checkout was cloned '
                                           'with git clone --shared, which writes '
                                           'nothing to the source repository; no '
                                           'worktree metadata was added and its '
                                           'build directory was not touched',
        'loaded_a_model': False,
        'started_a_server': False,
        'ran_an_episode': False,
    }
    if BINARY.exists() and exit_code == 0:
        receipt['native_model_free_fixture'] = native_seal_fixture(tmp)
    else:
        receipt['native_model_free_fixture'] = {
            'skipped': 'no binary, or the build did not exit zero'}

    out = Path(lab_common.RESULTS_ROOT) / ('BUILD_RECEIPT_%s.json'
                                           % time.strftime('%Y%m%dT%H%M%SZ',
                                                           time.gmtime()))
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({k: receipt[k] for k in
                      ('build_exit_code', 'binary_sha256', 'binary_bytes',
                       'build_started_utc', 'build_ended_utc',
                       'compile_errors_in_log')}, indent=1))
    fx = receipt['native_model_free_fixture']
    print('native fixture:', fx.get('verdict') or fx.get('skipped'))
    print('written:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
