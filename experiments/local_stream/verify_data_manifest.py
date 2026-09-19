"""Pinned-source data manifest for the local stream (Round 9 provenance repair). data.py is NOT edited.

The run downloaded its benchmark files from mutable `master` URLs (config.json). This script records, for the
bytes that were actually used, an IMMUTABLE upstream revision (the last upstream commit touching each file,
from the unauthenticated GitHub commits API on 2026-09-18) and the corresponding
raw.githubusercontent.com/<sha>/ URL, and checks that

  default (offline)   local raw files under work/local_stream/data/ have the recorded bytes + sha256, and a fresh
                      deterministic rebuild of the canonical task list (data.build_tasks + canonical_json) has the
                      frozen task-list sha256 (the one stamped in design.json / run_manifest.json);
  --verify-pinned     additionally fetches each pinned URL INTO MEMORY (nothing is written) and checks that the
                      bytes are identical (sha256 + length) to the local file / to the hash recorded by the timing pilot;
  --write             (re)creates results/local_stream/data_manifest.json from the local files and the constants below.

No model call, no git command. Exit status 1 on any mismatch.
Usage: .venv/bin/python experiments/local_stream/verify_data_manifest.py [--verify-pinned] [--write]
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import DATA_DIR, RESULTS_DIR, canonical_json, iso, now_ts, sha256_bytes, sha256_text  # noqa: E402

MANIFEST = RESULTS_DIR / 'data_manifest.json'
PINS = {
    'mbpp_sanitized': dict(
        role='design tasks (427 MBPP-sanitized problems)', local_file='sanitized-mbpp.json',
        mutable_url_used='https://raw.githubusercontent.com/google-research/google-research/master/mbpp/sanitized-mbpp.json',
        upstream_repo='google-research/google-research', upstream_path='mbpp/sanitized-mbpp.json',
        upstream_revision='f82046ba5aabbbb427dbfd38a254d26bff08b533', upstream_revision_committed_at='2022-03-31T16:16:34Z',
        revision_query='https://api.github.com/repos/google-research/google-research/commits?path=mbpp/sanitized-mbpp.json&per_page=1',
        license='CC-BY-4.0 (dataset; HF dataset card google-research-datasets/mbpp); source repository google-research/google-research is Apache-2.0',
        notice='MBPP: Austin et al. 2021, "Program Synthesis with Large Language Models". Attribution required by CC-BY-4.0; the files are not redistributed in this repository.'),
    'humaneval': dict(
        role='design tasks (164 HumanEval problems)', local_file='HumanEval.jsonl.gz',
        mutable_url_used='https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz',
        upstream_repo='openai/human-eval', upstream_path='data/HumanEval.jsonl.gz',
        upstream_revision='463c980b59e818ace59f6f9803cd92c749ceae61', upstream_revision_committed_at='2021-07-08T01:06:40Z',
        revision_query='https://api.github.com/repos/openai/human-eval/commits?path=data/HumanEval.jsonl.gz&per_page=1',
        license='MIT (openai/human-eval LICENSE)',
        notice='HumanEval: Chen et al. 2021, "Evaluating Large Language Models Trained on Code". MIT licence text: openai/human-eval LICENSE; the file is not redistributed in this repository.'),
    'mbpp_full_timing_pilot': dict(
        role='out-of-design timing pilot only (6 full-MBPP problems disjoint from the design; never analysed). Fetched into memory by timing_pilot.py; no local copy was kept.',
        local_file=None, recorded_in='results/local_stream/timing_pilot/summary.json -> full_mbpp_download',
        mutable_url_used='https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl',
        upstream_repo='google-research/google-research', upstream_path='mbpp/mbpp.jsonl',
        upstream_revision='f82046ba5aabbbb427dbfd38a254d26bff08b533', upstream_revision_committed_at='2022-03-31T16:16:34Z',
        revision_query='https://api.github.com/repos/google-research/google-research/commits?path=mbpp/mbpp.jsonl&per_page=1',
        license='CC-BY-4.0 (dataset); source repository Apache-2.0', notice='MBPP: Austin et al. 2021.'),
}


def pinned_url(p):
    return 'https://raw.githubusercontent.com/%s/%s/%s' % (p['upstream_repo'], p['upstream_revision'], p['upstream_path'])


def local_record(name):
    f = DATA_DIR / name; b = f.read_bytes()
    return dict(bytes=len(b), sha256=sha256_bytes(b))


def rebuild_task_list_sha256():
    from data import build_tasks
    mbpp_raw = json.loads((DATA_DIR / 'sanitized-mbpp.json').read_text())
    with gzip.open(DATA_DIR / 'HumanEval.jsonl.gz', 'rt') as f:
        he = [json.loads(l) for l in f if l.strip()]
    tasks = build_tasks(mbpp_raw, he)
    return sha256_text(canonical_json(tasks)), len(tasks), len(mbpp_raw), len(he)


def build_manifest():
    pilot = json.loads((RESULTS_DIR / 'timing_pilot' / 'summary.json').read_text())['full_mbpp_download']
    orig = DATA_DIR / 'data_manifest.json'
    sha, n, nm, nh = rebuild_task_list_sha256()
    design = json.loads((RESULTS_DIR / 'design.json').read_text())
    src = {}
    for k, p in PINS.items():
        rec = dict(p); rec['pinned_url'] = pinned_url(p)
        rec.update(local_record(p['local_file']) if p['local_file'] else dict(bytes=pilot['bytes'], sha256=pilot['sha256'], n_rows=pilot.get('n_rows'), fetched_at=pilot.get('fetched_at')))
        if p['local_file']:
            rec['local_path'] = '<REPO>/work/local_stream/data/' + p['local_file']
        src[k] = rec
    return dict(
        manifest='committed, sanitized source manifest for the local stream (Round 9); the original git-ignored manifest is work/local_stream/data/data_manifest.json',
        written_at=iso(now_ts()), revisions_queried_at='2026-09-18', sources=src,
        canonical_task_list=dict(sha256=sha, n_tasks=n, n_mbpp=nm, n_humaneval=nh, local_path='<REPO>/work/local_stream/data/tasks.json',
                                 tasks_json_file_sha256=sha256_bytes((DATA_DIR / 'tasks.json').read_bytes()),
                                 design_json_task_list_sha256=design['task_list_sha256'],
                                 ordering='mbpp by numeric task_id ascending, then humaneval by numeric index ascending',
                                 construction='data.build_tasks(raw) -> common.canonical_json (sort_keys, compact separators, ensure_ascii=False) -> sha256 of the utf-8 text'),
        original_local_manifest=dict(path='<REPO>/work/local_stream/data/data_manifest.json', sha256=(sha256_bytes(orig.read_bytes()) if orig.exists() else None),
                                     note='contains absolute local paths; kept unmodified and git-ignored'),
        pinned_bytes_verified=None,
        rebuild_check_command='.venv/bin/python experiments/local_stream/verify_data_manifest.py --verify-pinned',
        redistribution='raw benchmark files and tasks.json are NOT committed (work/ is git-ignored); they are re-obtainable byte-identically from the pinned URLs above')


def verify(pinned: bool):
    m = json.loads(MANIFEST.read_text()); ok = True; report = {}
    for k, s in m['sources'].items():
        if s.get('local_file'):
            loc = local_record(s['local_file'])
            good = loc['sha256'] == s['sha256'] and loc['bytes'] == s['bytes']
            print('%-24s local  %s bytes=%d sha256=%s' % (k, 'OK ' if good else 'FAIL', loc['bytes'], loc['sha256'])); ok &= good
        if pinned:
            import requests
            r = requests.get(s['pinned_url'], timeout=120); r.raise_for_status()
            h = hashlib.sha256(r.content).hexdigest(); good = h == s['sha256'] and len(r.content) == s['bytes']
            print('%-24s pinned %s bytes=%d sha256=%s  <- %s' % (k, 'OK ' if good else 'FAIL', len(r.content), h, s['pinned_url'])); ok &= good
            report[k] = dict(pinned_url=s['pinned_url'], bytes=len(r.content), sha256=h, identical_to_recorded=good)
    sha, n, nm, nh = rebuild_task_list_sha256()
    good = sha == m['canonical_task_list']['sha256'] == m['canonical_task_list']['design_json_task_list_sha256'] and (n, nm, nh) == (591, 427, 164)
    print('%-24s rebuild %s sha256=%s (n=%d: %d mbpp + %d humaneval)' % ('canonical task list', 'OK ' if good else 'FAIL', sha, n, nm, nh)); ok &= good
    return ok, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true'); ap.add_argument('--verify-pinned', action='store_true')
    args = ap.parse_args(argv)
    if args.write:
        m = build_manifest()
        if MANIFEST.exists():   # keep an earlier successful pinned verification record
            m['pinned_bytes_verified'] = json.loads(MANIFEST.read_text()).get('pinned_bytes_verified')
        MANIFEST.write_text(json.dumps(m, indent=2) + '\n'); print('wrote', MANIFEST)
    ok, report = verify(args.verify_pinned)
    if args.verify_pinned and ok:
        m = json.loads(MANIFEST.read_text()); m['pinned_bytes_verified'] = dict(at=iso(now_ts()), result='identical bytes for every source', detail=report)
        MANIFEST.write_text(json.dumps(m, indent=2) + '\n')
    print('DATA MANIFEST %s' % ('VERIFIED' if ok else 'MISMATCH'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
