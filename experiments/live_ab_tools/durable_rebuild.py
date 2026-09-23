"""The ONE model-free durable rebuild root authorized, 2026-09-23 18:29.

Root (reviews/preparation_wiring_disposition_20260923_1829.md): "preserve this
candidate and its receipts as retrospective engineering evidence, do not freeze
or trial it. After a fresh capacity/disk check and confirming no duplicate build
is running, Session60 may make one local, model-free durable rebuild at the
protocol's <WORK>/<LLAMA_BUILD> with the same pinned upstream source, lifecycle
patch and documented build options; retain original logs/receipts, then measure
and pin the new source/build/launcher/library closure ... No weights download,
hardware purchase, model run or trial is authorized by this decision."

WHAT IT DOES, IN ORDER, REFUSING AT THE FIRST FAILED PRECONDITION
  1. Preconditions: <LLAMA_BUILD> (= <WORK>/llama.cpp-build, protocol 2.1)
     does not exist (one rebuild, write-once); >= 20 GiB free (protocol 2.1);
     no cmake/ninja/clang process is running; the retained UI archive digest
     is the pinned one.
  2. Source: a LOCAL clone (no network) of the pinned upstream commit 4fea119
     from the retained source tree's git store; HEAD verified; the v7 lifecycle
     patch applied as the DECLARED working-tree state -- not committed, so the
     embedded build_info stays 4fea119 as protocol 2.2 requires.
  3. UI: upstream's first-priority path, pre-built assets in the checkout's
     git-ignored tools/ui/dist, extracted from the retained archive; the HF
     download disabled (LLAMA_USE_PREBUILT_UI=OFF) and a dead proxy set, so
     ANY fetch attempt fails loudly instead of silently resolving 'latest'.
  4. Configure and build with the documented options, -j2 (root's resource
     rule), with the durable repo .venv cmake/ninja (same versions as before).
  5. Record everything protocol 2.2 item 1 names: cmake options, compiler and
     SDK versions, configure and build log SHA-256, `git status --porcelain`;
     plus the declared source state, the UI embed digest against the retained
     one, and every launcher/library digest.

No model, no server, no weights, no network. The build runs the compiler; it
does not run the candidate.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WORK = REPO / 'work'
LLAMA_BUILD = WORK / 'llama.cpp-build'
BUILD_DIR = LLAMA_BUILD / 'build'
VENV_BIN = REPO / '.venv' / 'bin'

PINNED_COMMIT = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'
PATCH = REPO / 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
PATCH_SHA256 = '88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184'
UI_ARCHIVE_SHA256 = '3de85ed97697c04e1614e95021eef6b668dc089eb66e7f0db1f83cbef1121a89'
UI_EMBED_SHA256_RETAINED = '2b5941122d67ce4c5abc62a56333c429630fba4784ff8e46bcd9c1f59d668c5d'
MIN_FREE_BYTES = 20 * 1024 ** 3
#: The documented configure options (CANDIDATE_INSTRUMENT_MANIFEST.json build),
#: plus the explicit UI switches that make the no-fetch path the only path.
CMAKE_OPTIONS = ['-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DLLAMA_CURL=OFF',
                 '-DGGML_METAL=ON', '-DLLAMA_USE_PREBUILT_UI=OFF', '-DLLAMA_BUILD_UI=OFF']
#: Any network attempt fails immediately.
NO_NETWORK_ENV = {'HTTP_PROXY': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9',
                  'ALL_PROXY': 'http://127.0.0.1:9', 'http_proxy': 'http://127.0.0.1:9',
                  'https_proxy': 'http://127.0.0.1:9', 'all_proxy': 'http://127.0.0.1:9',
                  'NO_PROXY': '', 'no_proxy': ''}
MEMBERS = ['llama-server', 'libllama-server-impl.dylib', 'libggml.0.dylib',
           'libggml-base.0.dylib', 'libggml-cpu.0.dylib', 'libggml-blas.0.dylib',
           'libggml-metal.0.dylib', 'libllama.0.dylib', 'libllama-common.0.dylib',
           'libmtmd.0.dylib']


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def run(argv, *, cwd=None, log=None, env_extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'GGML_',
                                                                   'LLAMA_', 'DYLD_'))}
    env.update(NO_NETWORK_ENV)
    env.update(env_extra or {})
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env)
    if log is not None:
        with open(log, 'a') as f:
            f.write('$ %s\n%s%s[exit %d]\n' % (' '.join(map(str, argv)), r.stdout,
                                              r.stderr, r.returncode))
    return r


def refuse(msg: str) -> int:
    print('REFUSED: ' + msg, file=sys.stderr)
    return 2


def main() -> int:
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    receipt_path = REPO / 'results' / 'live_ab' / ('DURABLE_REBUILD_%s.json' % stamp)
    manifest = json.loads((REPO / 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json')
                          .read_text())
    old_tree = Path(manifest['source_and_patch']['source_tree'])
    ui_archive = old_tree / 'build/tools/ui/dist.tar.gz'

    # -- 1. preconditions ----------------------------------------------------
    pre = {'llama_build': str(LLAMA_BUILD), 'exists': LLAMA_BUILD.exists()}
    if LLAMA_BUILD.exists():
        return refuse('%s exists: this is the one authorized rebuild' % LLAMA_BUILD)
    usage = shutil.disk_usage(str(REPO))
    pre['free_bytes'] = usage.free
    if usage.free < MIN_FREE_BYTES:
        return refuse('only %d bytes free; protocol 2.1 requires 20 GiB' % usage.free)
    ps = subprocess.run(['ps', '-axo', 'pid,comm'], capture_output=True, text=True).stdout
    busy = [l.strip() for l in ps.splitlines()
            if any(t in l.rsplit('/', 1)[-1] for t in ('cmake', 'ninja', 'clang'))]
    pre['build_processes_running'] = busy
    if busy:
        return refuse('a build appears to be running: %s' % busy)
    pre['load_average'] = os.getloadavg()
    if not ui_archive.is_file() or sha(ui_archive) != UI_ARCHIVE_SHA256:
        return refuse('the retained UI archive is missing or not the pinned digest')
    if sha(PATCH) != PATCH_SHA256:
        return refuse('the lifecycle patch is not the pinned v7 patch')
    for tool in ('cmake', 'ninja'):
        if not (VENV_BIN / tool).exists():
            return refuse('the durable toolchain %s is missing' % tool)

    WORK.mkdir(exist_ok=True)
    LLAMA_BUILD.mkdir()
    logs = LLAMA_BUILD / '_rebuild_logs'
    logs.mkdir()
    source_log = logs / 'source.log'

    # -- 2. source: local clone, pinned HEAD, declared patch state ------------
    r = run(['git', 'clone', '--no-checkout', 'file://%s' % old_tree, str(LLAMA_BUILD / 'src')],
            log=source_log)
    if r.returncode != 0:
        return refuse('local clone failed')
    src = LLAMA_BUILD / 'src'
    for argv in (['git', '-C', str(src), 'checkout', '--detach', PINNED_COMMIT],
                 ['git', '-C', str(src), 'remote', 'remove', 'origin']):
        r = run(argv, log=source_log)
        if r.returncode != 0:
            return refuse('%s failed' % ' '.join(argv[3:5]))
    head = run(['git', '-C', str(src), 'rev-parse', 'HEAD'], log=source_log).stdout.strip()
    if head != PINNED_COMMIT:
        return refuse('HEAD is %s, not the pin' % head)
    r = run(['git', '-C', str(src), 'apply', str(PATCH)], log=source_log)
    if r.returncode != 0:
        return refuse('the lifecycle patch did not apply')

    # -- 3. UI: pre-built assets from the retained archive --------------------
    dist = src / 'tools/ui/dist'
    dist.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ui_archive) as tf:
        tf.extractall(dist, filter='data')
    # the archive may hold a top-level dist/ directory
    if not (dist / 'index.html').exists() and (dist / 'dist' / 'index.html').exists():
        inner = dist / 'dist'
        for p in inner.iterdir():
            p.rename(dist / p.name)
        inner.rmdir()
    if not (dist / 'index.html').exists():
        return refuse('the UI archive did not yield tools/ui/dist/index.html')
    status = run(['git', '-C', str(src), 'status', '--porcelain'], log=source_log).stdout

    # -- 4. configure and build -----------------------------------------------
    cfg_log, bld_log = logs / 'configure.log', logs / 'build.log'
    cfg = run([str(VENV_BIN / 'cmake'), '-S', str(src), '-B', str(BUILD_DIR)] + CMAKE_OPTIONS
              + ['-DCMAKE_MAKE_PROGRAM=%s' % (VENV_BIN / 'ninja')], log=cfg_log)
    built = None
    if cfg.returncode == 0:
        built = run([str(VENV_BIN / 'ninja'), '-C', str(BUILD_DIR), '-j2', 'llama-server'],
                    log=bld_log)
    fetch_attempts = [l for l in (cfg_log.read_text() + (bld_log.read_text()
                                                          if bld_log.exists() else ''))
                      .splitlines() if 'download' in l.lower() or 'http' in l.lower()]

    # -- 5. record ------------------------------------------------------------
    binr = BUILD_DIR / 'bin'
    members = {}
    for name in MEMBERS:
        p = binr / name
        members[name] = ({'path': str(p), 'canonical': os.path.realpath(p),
                          'sha256': sha(p), 'bytes': p.stat().st_size}
                         if p.exists() else None)
    embed = BUILD_DIR / 'tools/ui/.ui-embed.sha256'
    embed_sha = embed.read_text().split()[0] if embed.exists() else None
    # A second, direct check: the generated UI source itself, byte for byte,
    # against the retained candidate's -- in case the embed fingerprint also
    # covers where the assets came from rather than only what they are.
    new_ui, old_ui = BUILD_DIR / 'tools/ui/ui.cpp', old_tree / 'build/tools/ui/ui.cpp'
    ui_cpp = {'new_sha256': sha(new_ui) if new_ui.exists() else None,
              'retained_sha256': sha(old_ui) if old_ui.exists() else None}
    ui_cpp['identical'] = ui_cpp['new_sha256'] is not None and \
        ui_cpp['new_sha256'] == ui_cpp['retained_sha256']
    tools = {
        'cmake': run([str(VENV_BIN / 'cmake'), '--version']).stdout.splitlines()[0],
        'ninja': run([str(VENV_BIN / 'ninja'), '--version']).stdout.strip(),
        'compiler': run(['clang', '--version']).stdout.splitlines()[0],
        'sdk': run(['xcrun', '--show-sdk-version']).stdout.strip(),
    }
    ok = bool(cfg.returncode == 0 and built is not None and built.returncode == 0
              and all(members.values()))
    doc = {
        'schema': 'live_ab/durable_rebuild-v1',
        'convention': 'deterministic-path',
        'started_utc': t0,
        'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'authority': 'root, reviews/preparation_wiring_disposition_20260923_1829.md',
        'what_this_is': ('ONE local, model-free rebuild of the pinned candidate source into '
                         'the durable <LLAMA_BUILD>. The build ran the compiler; nothing '
                         'ran the candidate, loaded a model or used the network.'),
        'preconditions': pre,
        'llama_build': str(LLAMA_BUILD), 'source_checkout': str(src),
        'source_state': {
            'head': head, 'pinned_commit': PINNED_COMMIT,
            'declared_working_tree_state': 'HEAD + the v7 lifecycle patch, not committed '
                                           '(so build_info embeds the pinned commit)',
            'patch_sha256': PATCH_SHA256,
            'git_status_porcelain': status.splitlines(),
            'origin_remote': 'removed after the local clone'},
        'ui': {'path': 'upstream priority 1: pre-built assets in the git-ignored '
                       'tools/ui/dist, extracted from the retained archive',
               'archive_sha256': UI_ARCHIVE_SHA256,
               'hf_download': 'disabled (LLAMA_USE_PREBUILT_UI=OFF) with a dead proxy',
               'embed_sha256': embed_sha,
               'embed_equals_retained_candidate': embed_sha == UI_EMBED_SHA256_RETAINED,
               'generated_ui_cpp': ui_cpp},
        'protocol_2_2_item_1': {
            'cmake_options': CMAKE_OPTIONS, 'toolchain': tools,
            'configure_log_sha256': sha(cfg_log) if cfg_log.exists() else None,
            'build_log_sha256': sha(bld_log) if bld_log.exists() else None,
            'configure_exit': cfg.returncode,
            'build_exit': built.returncode if built is not None else None},
        'network_lines_in_logs': fetch_attempts,
        'members': members,
        'build_succeeded': ok,
    }
    receipt_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    for name, p in (('configure', cfg_log), ('build', bld_log)):
        if p.exists():
            shutil.copyfile(p, REPO / 'results' / 'live_ab' /
                            ('DURABLE_REBUILD_%s_%s.log' % (stamp, name)))
    print(receipt_path, 'build_succeeded=%s' % ok)
    return 0 if ok else 1


if __name__ == '__main__':                                     # pragma: no cover
    sys.exit(main())
