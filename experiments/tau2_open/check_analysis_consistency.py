"""Round 10 consistency check: re-run the frozen analysis.py on a scratch COPY of its inputs with the src/wincs.py
that is on disk now, and compare every number with the deposited results/tau2_open/summary.json.

POST HOC provenance check, no model / API / git. The deposited outputs are never overwritten: analysis.py is run with
--results-dir <scratch>, where <scratch> holds copies of design.json, design.sha256, episodes.csv, run_manifest.json and
raw/tau2_open_arm{A,B}.json (analysis.py reads the raw files only to detect mock data). The outcome is written to
results/tau2_open/analysis_consistency_check.json.

Usage:  .venv/bin/python experiments/tau2_open/check_analysis_consistency.py --scratch <dir outside the repository>
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RD = ROOT / 'results' / 'tau2_open'
INPUTS = ['design.json', 'design.sha256', 'episodes.csv', 'run_manifest.json', 'raw/tau2_open_armA.json', 'raw/tau2_open_armB.json']
OUTPUTS = ['summary.json', 'decision_rules.csv', 'sensitivity.csv', 'task_scores.csv', 'monitor_pass1.csv', 'monitor_state.json', 'report.md']
IGNORED_KEYS = {'generated_at': 'timestamp', 'results_dir': 'path of the results directory (scratch versus deposited)'}
IGNORED_PATHS = {'/monitor_state/updated_at': 'timestamp'}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def diff(a, b, path=''):
    """Exact recursive comparison of two JSON values; returns a list of (path, deposited, scratch). NaN equals NaN."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if (path == '' and k in IGNORED_KEYS) or (path + '/' + k) in IGNORED_PATHS:
                continue
            if k not in a or k not in b:
                out.append((path + '/' + k, a.get(k, '<absent>'), b.get(k, '<absent>')))
            else:
                out += diff(a[k], b[k], path + '/' + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'len %d' % len(a), 'len %d' % len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff(x, y, '%s[%d]' % (path, i))
    else:
        same = (a == b) or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))
        if not same:
            out.append((path, a, b))
    return out


def _strip_volatile(line: str, rd: Path) -> str:
    import re
    line = line.replace(str(rd), '<RD>').replace('results/tau2_open', '<RD>')
    return re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', '<TS>', line)


def count_leaves(o) -> tuple:
    if isinstance(o, dict):
        r = [count_leaves(v) for v in o.values()]
    elif isinstance(o, list):
        r = [count_leaves(v) for v in o]
    else:
        return (1, int(isinstance(o, (int, float)) and not isinstance(o, bool)))
    return (sum(x[0] for x in r), sum(x[1] for x in r))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scratch', required=True, help='scratch directory outside the repository; created if missing')
    args = ap.parse_args(argv)
    scratch = Path(args.scratch).resolve()
    if ROOT in scratch.parents or scratch == ROOT:
        raise SystemExit('the scratch directory must be outside the repository')
    (scratch / 'raw').mkdir(parents=True, exist_ok=True)
    before = {o: sha(RD / o) for o in OUTPUTS if (RD / o).exists()}
    for i in INPUTS:
        shutil.copy2(RD / i, scratch / i)
    inputs = {i: dict(deposited=sha(RD / i), scratch_copy=sha(scratch / i)) for i in INPUTS}
    assert all(v['deposited'] == v['scratch_copy'] for v in inputs.values())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    t0 = time.time()
    r = subprocess.run([sys.executable, str(HERE / 'analysis.py'), '--results-dir', str(scratch)], cwd=str(ROOT), env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('analysis.py failed:\n' + r.stderr[-3000:])
    after = {o: sha(RD / o) for o in OUTPUTS if (RD / o).exists()}
    assert before == after, 'a deposited output changed during the check'
    dep = json.loads((RD / 'summary.json').read_text()); new = json.loads((scratch / 'summary.json').read_text())
    d = diff(dep, new)
    leaves, numeric = count_leaves({k: v for k, v in dep.items() if k not in IGNORED_KEYS}); leaves -= len(IGNORED_PATHS)
    files = {}
    for o in OUTPUTS:
        if o == 'summary.json' or not (scratch / o).exists():
            continue
        a, b = (RD / o).read_bytes(), (scratch / o).read_bytes()
        files[o] = dict(deposited_sha256=hashlib.sha256(a).hexdigest(), scratch_sha256=hashlib.sha256(b).hexdigest(), byte_identical=a == b)
        if a != b:
            la, lb = a.decode().splitlines(), b.decode().splitlines()
            dl = [(i + 1, x, y.replace(str(scratch), '<TMP>/' + scratch.name)) for i, (x, y) in enumerate(zip(la, lb)) if x != y]
            files[o]['differing_lines'] = [dict(line=i, deposited=x[:160], scratch=y[:160]) for i, x, y in dl][:20]
            files[o]['differs_only_in_timestamp_or_results_dir_path'] = bool(len(la) == len(lb) and all(_strip_volatile(x, RD) == _strip_volatile(y, scratch) for _, x, y in
                                                                             [(i, x, lb[i - 1]) for i, x, _ in dl]))
            files[o]['n_lines'] = (len(la), len(lb))
    out = dict(
        check='re-run of the frozen experiments/tau2_open/analysis.py on a scratch copy of its inputs, with the src/wincs.py on disk at check time',
        post_hoc=True, checked_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), python=sys.version.split()[0],
        scratch_dir='<TMP>/' + scratch.name + '  (location-dependent; outside the repository; not deposited)',
        src_sha256={'src/wincs.py': sha(ROOT / 'src' / 'wincs.py'), 'src/winstats.py': sha(ROOT / 'src' / 'winstats.py'),
                    'experiments/tau2_open/analysis.py': sha(HERE / 'analysis.py'), 'experiments/tau2_open/common.py': sha(HERE / 'common.py'),
                    'experiments/tau2_open/design.py': sha(HERE / 'design.py'), 'experiments/tau2_open/config.json': sha(HERE / 'config.json')},
        wincs_sha256_registered_in_addendum_e='6a6a0b51bf46d64079614af3aefc364800c1862fd7635728c2949be7f2907a3b',
        wincs_note='The wincs.py hash in force when the deposited summary.json was written (2026-09-19T05:01:30Z) is recorded in no saved artifact. src/wincs.py was modified by '
                   'another session afterwards (mtime at check time: %s). This check' % time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime((ROOT / 'src' / 'wincs.py').stat().st_mtime)) + ' shows that the bytes now on disk reproduce the deposited numbers; it cannot show which '
                   'bytes were imported at the time.',
        inputs_sha256=inputs, deposited_summary_sha256=sha(RD / 'summary.json'), scratch_summary_sha256=sha(scratch / 'summary.json'),
        ignored_top_level_keys=IGNORED_KEYS, ignored_nested_paths=IGNORED_PATHS, ignored_values=dict(deposited={k: dep.get(k) for k in IGNORED_KEYS}, scratch={k: ('<TMP>/' + scratch.name if k == 'results_dir' else new.get(k)) for k in IGNORED_KEYS}),
        summary_leaves_compared=leaves, summary_numeric_leaves_compared=numeric, summary_differences=[dict(path=p, deposited=a, scratch=b) for p, a, b in d],
        every_number_in_summary_equal=len(d) == 0, all_other_outputs_identical_up_to_timestamp_and_path=all(v['byte_identical'] or v.get('differs_only_in_timestamp_or_results_dir_path') for v in files.values()), comparison='exact equality of parsed JSON values (no tolerance)', other_outputs=files,
        deposited_outputs_untouched=before == after, deposited_outputs_sha256=after, analysis_elapsed_s=round(time.time() - t0, 2), analysis_stdout_tail=r.stdout[-600:])
    (RD / 'analysis_consistency_check.json').write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(dict(every_number_in_summary_equal=out['every_number_in_summary_equal'], n_differences=len(d), leaves=leaves, numeric=numeric,
                          other_outputs={k: v['byte_identical'] for k, v in files.items()}, wincs=out['src_sha256']['src/wincs.py']), indent=2))


if __name__ == '__main__':
    main()
