"""ONE aggregate command: regenerate every Round 9 (v2) output of the local stream from the preserved raw files.

Steps (each a subprocess of the same interpreter; stops at the first failure):
  1. check_two_sided_cs.py          exact witness + simulated time-uniform miscoverage of the corrected CS
  2. verify_data_manifest.py        local bytes/sha256 + deterministic canonical task-list rebuild  (--verify-pinned: also re-fetch pinned URLs into memory)
  3. analysis_v2.py                 summary_v2.json, decision_rules_v2.csv, sensitivity_v2.csv, running_cs_v2.csv, resources_v2.csv
  4. make_figures_v2.py             figures_v2/
  5. make_report_v2.py              report_v2.md + report.md stub
  6. make_release_anon.py           release_anon/
then verifies that the raw evidence is byte-identical before and after, and writes
results/local_stream/analysis_v2_manifest.json (sha256 of inputs, of src/wincs.py, of every v2 script, of outputs; timestamps).

No model call, no git command, single process at a time (CPU only, about 4 minutes).
Optional: --with-wincs-tests also runs src/test_wincs.py (about 1 minute); --skip-cs-check skips step 1.
Usage: .venv/bin/python experiments/local_stream/run_v2_all.py [--verify-pinned] [--with-wincs-tests] [--skip-cs-check]
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; RD = REPO / 'results/local_stream'
RAW = ['episodes.jsonl', 'monitor_pass1.csv', 'monitor_state.json', 'design.json', 'design.sha256', 'run_manifest.json']
SCRIPTS = ['analysis_v2.py', 'make_figures_v2.py', 'make_report_v2.py', 'check_two_sided_cs.py', 'verify_data_manifest.py', 'make_release_anon.py', 'run_v2_all.py',
           'protocol_addendum_round9.md']
FROZEN = ['analysis.py', 'run_stream.py', 'design.py', 'common.py', 'data.py', 'config.json', 'protocol.md', 'make_figures.py']
OUTPUTS = ['summary_v2.json', 'decision_rules_v2.csv', 'sensitivity_v2.csv', 'running_cs_v2.csv', 'resources_v2.csv', 'two_sided_cs_check.json', 'report_v2.md', 'report.md',
           'data_manifest.json', 'release_anon/MAPPING.json']


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--verify-pinned', action='store_true'); ap.add_argument('--with-wincs-tests', action='store_true'); ap.add_argument('--skip-cs-check', action='store_true')
    args = ap.parse_args(argv)
    started = now(); raw_before = {f: sha(RD / f) for f in RAW}
    steps = []
    if args.with_wincs_tests:
        steps.append([str(REPO / 'src/test_wincs.py')])
    if not args.skip_cs_check:
        steps.append([str(HERE / 'check_two_sided_cs.py')])
    steps += [[str(HERE / 'verify_data_manifest.py')] + (['--verify-pinned'] if args.verify_pinned else []), [str(HERE / 'analysis_v2.py')],
              [str(HERE / 'make_figures_v2.py')], [str(HERE / 'make_report_v2.py')], [str(HERE / 'make_release_anon.py')]]
    log = []
    for cmd in steps:
        t0 = time.time(); print('>>>', ' '.join(Path(c).name if c.endswith('.py') else c for c in cmd), flush=True)
        r = subprocess.run([sys.executable] + cmd, cwd=str(REPO), capture_output=True, text=True)
        tail = (r.stdout or '').strip().splitlines()[-3:]
        print('\n'.join('    ' + l[:200] for l in tail))
        log.append(dict(step=Path(cmd[0]).name, args=cmd[1:], returncode=r.returncode, seconds=round(time.time() - t0, 1), started_at=None))
        if r.returncode != 0:
            print(r.stderr[-3000:], file=sys.stderr); raise SystemExit('step failed: %s' % cmd[0])
    raw_after = {f: sha(RD / f) for f in RAW}
    assert raw_before == raw_after, 'RAW EVIDENCE CHANGED'
    v1 = RD / 'v1_pre_round9'
    manifest = dict(
        what='Round 9 (v2) re-analysis manifest for the local stream; POST HOC; no model inference',
        started_at=started, finished_at=now(), python=sys.version.split()[0], command='.venv/bin/python experiments/local_stream/run_v2_all.py' + (' --verify-pinned' if args.verify_pinned else ''),
        raw_evidence_sha256=raw_after, raw_evidence_unchanged_by_this_run=True,
        src_sha256={f: sha(REPO / 'src' / f) for f in ('wincs.py', 'test_wincs.py', 'winstats.py')},
        v2_scripts_sha256={f: sha(HERE / f) for f in SCRIPTS}, frozen_files_sha256={f: sha(HERE / f) for f in FROZEN},
        tau2_addendum_sha256=sha(REPO / 'experiments/tau2_open/protocol_addendum_round9.md'), tau2_analysis_py_sha256_unchanged=sha(REPO / 'experiments/tau2_open/analysis.py'),
        outputs_sha256={**{f: sha(RD / f) for f in OUTPUTS}, **{'figures_v2/' + p.name: sha(p) for p in sorted((RD / 'figures_v2').glob('*.png'))}},
        v1_preserved_sha256={p.name: sha(p) for p in sorted(v1.glob('*')) if p.is_file()},
        steps=[{k: v for k, v in s.items() if k != 'started_at'} for s in log],
        note='PDF figures embed a creation date and are not hashed; PNG hashes may differ across matplotlib versions. summary_v2.json and report_v2.md contain a generation timestamp.')
    (RD / 'analysis_v2_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('raw evidence unchanged; wrote', RD / 'analysis_v2_manifest.json')


if __name__ == '__main__':
    main()
