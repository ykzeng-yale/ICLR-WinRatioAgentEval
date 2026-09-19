"""ONE aggregate command: regenerate every Round 10 (v3) output of the local stream from the preserved raw files.

Steps (each a subprocess of the same interpreter; stops at the first failure):
  0. assert the raw evidence and the frozen originals are byte-identical to the hashes recorded by the Round 9 manifest
     (results/local_stream/v2_pre_round10/analysis_v2_manifest.json)
  1. src/test_wincs.py              whole file, including test_endpoint_normalization_round10   (--skip-wincs-tests to skip)
  2. check_two_sided_cs.py          only with --with-cs-check (Round 9 Monte Carlo regression, about 3 minutes)
  3. verify_data_manifest.py        local bytes/sha256 + canonical task-list rebuild (offline, read-only)
  4. analysis_v2.py                 v2 NUMERICAL outputs regenerated with the endpoint-fixed src/wincs.py, then compared
                                    leaf by leaf with the preserved Round 9 files -> v2_vs_v3_numeric_check.json
  5. analysis_v3.py                 summary_v3.json, decision_rules_v3.csv, e2_cluster_v3.csv, pass_effects_v3.csv
  6. make_report_v3.py              report_v3.md + report.md stub (points to report_v3.md); report_v2.md gets a SUPERSEDED banner
                                    (its Round 9 bytes are preserved in v2_pre_round10/)
  7. make_release_anon_v3.py        release_anon/ (non-ignored data-manifest copy, identifier re-scan)
then verifies again that the raw evidence is byte-identical and writes results/local_stream/analysis_v3_manifest.json.

No model call, no git command, no execution of generated benchmark programs; CPU only.
Usage: .venv/bin/python experiments/local_stream/run_v3_all.py [--with-cs-check] [--skip-wincs-tests]
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; RD = REPO / 'results/local_stream'; PRE = RD / 'v2_pre_round10'
RAW = ['episodes.jsonl', 'monitor_pass1.csv', 'monitor_state.json', 'design.json', 'design.sha256', 'run_manifest.json']
FROZEN = ['protocol.md', 'analysis.py', 'run_stream.py', 'agent.py', 'sandbox.py', 'verify.py', 'design.py', 'data.py', 'config.json', 'common.py', 'make_figures.py']
ROUND9_UNCHANGED = ['analysis_v2.py', 'make_figures_v2.py', 'make_report_v2.py', 'check_two_sided_cs.py', 'verify_data_manifest.py', 'make_release_anon.py', 'run_v2_all.py', 'protocol_addendum_round9.md']
SCRIPTS = ['analysis_v3.py', 'make_report_v3.py', 'make_release_anon_v3.py', 'run_v3_all.py', 'protocol_addendum_round10.md']
V2_NUMERIC = ['decision_rules_v2.csv', 'sensitivity_v2.csv', 'running_cs_v2.csv', 'resources_v2.csv']
OUTPUTS = ['summary_v3.json', 'decision_rules_v3.csv', 'e2_cluster_v3.csv', 'pass_effects_v3.csv', 'report_v3.md', 'report.md', 'report_v2.md', 'v2_vs_v3_numeric_check.json',
           'summary_v2.json', 'two_sided_cs_check.json', 'data_manifest.json', 'release_anon/MAPPING.json', 'release_anon/MAPPING.md', 'release_anon/local_data_manifest.anon.json',
           'PR8_BODY_round10.md'] + V2_NUMERIC
IGNORE_KEYS = {'generated_at', 'wincs_sha256'}
BANNER = ('> **SUPERSEDED by [report_v3.md](report_v3.md) (Round 10).** The statements below that the E2 intervals need no assumptions or are conservative by construction, '
          'and the "design-based, no sampling assumption" wording of R1, are withdrawn; the numbers are unchanged. Original Round 9 bytes: `v2_pre_round10/report_v2.md`.\n\n')


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE_KEYS:
                continue
            if k not in a or k not in b:
                out['structural'].append(path + '/' + k)
            else:
                walk(a[k], b[k], path + '/' + k, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out['structural'].append(path + ' (length)')
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, '%s[%d]' % (path, i), out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        out['n'] += 1; d = 0.0 if a == b else abs(float(a) - float(b))
        if math.isnan(d):
            d = 0.0 if (math.isnan(float(a)) and math.isnan(float(b))) else float('inf')
        if d > 0:
            out['changed'].append(dict(path=path, round9=a, round10=b, abs_diff=d))
        out['max'] = max(out['max'], d)
    elif a != b:
        out['nonnumeric'].append(dict(path=path, round9=a, round10=b))


def compare_v2():
    """Leaf-by-leaf comparison of the regenerated v2 numerical outputs with the preserved Round 9 files."""
    res = dict(what='v2 numerical outputs regenerated with the endpoint-fixed src/wincs.py versus the Round 9 files preserved in v2_pre_round10/',
               wincs_sha256=dict(round9=sha(PRE / 'wincs_v2_pre_endpoint_fix.py.txt'), round10=sha(REPO / 'src/wincs.py')), ignored_keys=sorted(IGNORE_KEYS))
    o = dict(n=0, max=0.0, changed=[], nonnumeric=[], structural=[])
    walk(json.loads((PRE / 'summary_v2.json').read_text()), json.loads((RD / 'summary_v2.json').read_text()), '', o)
    res['summary_v2_json'] = dict(n_numeric_leaves=o['n'], max_abs_diff=o['max'], n_changed=len(o['changed']), changed=sorted(o['changed'], key=lambda r: -r['abs_diff'])[:50],
                                  nonnumeric_changes=o['nonnumeric'], structural_changes=o['structural'])
    overall = o['max']; cells = 0; res['csv'] = {}
    for fn in V2_NUMERIC:
        a = pd.read_csv(PRE / fn); b = pd.read_csv(RD / fn); byte_identical = sha(PRE / fn) == sha(RD / fn)
        assert a.shape == b.shape and list(a.columns) == list(b.columns), fn
        mx = 0.0; nonnum = 0
        for c in a.columns:
            if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
                d = (a[c].astype(float) - b[c].astype(float)).abs(); d = d[~(a[c].isna() & b[c].isna())]
                cells += len(d); mx = max(mx, float(d.max()) if len(d) else 0.0)
            else:
                nonnum += int((a[c].fillna('').astype(str) != b[c].fillna('').astype(str)).sum())
        res['csv'][fn] = dict(byte_identical=byte_identical, max_abs_diff_numeric=mx, nonnumeric_cells_changed=nonnum); overall = max(overall, mx)
    res['n_csv_numeric_cells'] = cells; res['max_abs_diff_overall'] = overall
    res['any_v2_number_changed'] = overall > 0
    res['any_v2_number_changed_beyond_1e-8'] = overall > 1e-8
    res['conclusion'] = ('NO v2 number changed (all regenerated numeric leaves and cells equal the Round 9 values exactly).' if overall == 0 else
                         'v2 numbers changed by at most %.3g (%s the 1e-8 tolerance expected for interior CS endpoints).' % (overall, 'within' if overall <= 1e-8 else 'BEYOND'))
    (RD / 'v2_vs_v3_numeric_check.json').write_text(json.dumps(res, indent=2, default=str) + '\n')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--with-cs-check', action='store_true'); ap.add_argument('--skip-wincs-tests', action='store_true')
    args = ap.parse_args(argv)
    started = now()
    r9 = json.loads((PRE / 'analysis_v2_manifest.json').read_text())
    raw_before = {f: sha(RD / f) for f in RAW}
    assert raw_before == r9['raw_evidence_sha256'], 'RAW EVIDENCE differs from the Round 9 manifest'
    for fn, h in r9['frozen_files_sha256'].items():
        assert sha(HERE / fn) == h, 'frozen file changed: ' + fn
    for fn, h in r9['v2_scripts_sha256'].items():
        assert sha(HERE / fn) == h, 'Round 9 script changed: ' + fn
    assert sha(RD / 'v1_pre_round9/summary.json') == r9['v1_preserved_sha256']['summary.json']
    print('raw evidence, frozen originals and Round 9 scripts match the Round 9 manifest', flush=True)

    steps = []
    if not args.skip_wincs_tests:
        steps.append([str(REPO / 'src/test_wincs.py')])
    if args.with_cs_check:
        steps.append([str(HERE / 'check_two_sided_cs.py')])
    steps += [[str(HERE / 'verify_data_manifest.py')], [str(HERE / 'analysis_v2.py')], 'COMPARE', [str(HERE / 'analysis_v3.py')], [str(HERE / 'make_report_v3.py')], [str(HERE / 'make_release_anon_v3.py')]]
    log = []; cmp = None
    for cmd in steps:
        if cmd == 'COMPARE':
            cmp = compare_v2(); print('>>> compare v2 numbers:', cmp['conclusion'], flush=True); continue
        t0 = time.time(); print('>>>', ' '.join(Path(c).name for c in cmd), flush=True)
        r = subprocess.run([sys.executable] + cmd, cwd=str(REPO), capture_output=True, text=True)
        print('\n'.join('    ' + l[:200] for l in (r.stdout or '').strip().splitlines()[-2:]))
        log.append(dict(step=Path(cmd[0]).name, args=cmd[1:], returncode=r.returncode, seconds=round(time.time() - t0, 1)))
        if r.returncode != 0:
            print(r.stderr[-3000:], file=sys.stderr); raise SystemExit('step failed: %s' % cmd[0])
    # report_v2.md: Round 9 bytes + SUPERSEDED banner (idempotent; original preserved in v2_pre_round10/)
    (RD / 'report_v2.md').write_text(BANNER + (PRE / 'report_v2.md').read_text())
    stub = (RD / 'report.md').read_text(); assert 'report_v3.md' in stub
    rep = (RD / 'report_v3.md').read_text().lower(); assert 'assumption-free' not in rep and 'automatically conservative' not in rep
    raw_after = {f: sha(RD / f) for f in RAW}
    assert raw_before == raw_after, 'RAW EVIDENCE CHANGED'
    manifest = dict(
        what='Round 10 (v3) re-analysis manifest for the local stream; POST HOC; no model inference, no generated program executed',
        started_at=started, finished_at=now(), python=sys.version.split()[0],
        command='.venv/bin/python experiments/local_stream/run_v3_all.py' + (' --with-cs-check' if args.with_cs_check else '') + (' --skip-wincs-tests' if args.skip_wincs_tests else ''),
        raw_evidence_sha256=raw_after, raw_evidence_unchanged_by_this_run=True, raw_evidence_equals_round9_manifest=True,
        src_sha256={f: sha(REPO / 'src' / f) for f in ('wincs.py', 'test_wincs.py', 'winstats.py')},
        src_sha256_round9=r9['src_sha256'],
        v3_scripts_sha256={f: sha(HERE / f) for f in SCRIPTS}, round9_scripts_sha256_unchanged={f: sha(HERE / f) for f in ROUND9_UNCHANGED},
        frozen_files_sha256={f: sha(HERE / f) for f in FROZEN},
        outputs_sha256={f: sha(RD / f) for f in OUTPUTS},
        v2_numeric_check=dict(max_abs_diff_overall=cmp['max_abs_diff_overall'], any_v2_number_changed=cmp['any_v2_number_changed'], conclusion=cmp['conclusion'],
                              csv_byte_identical={k: v['byte_identical'] for k, v in cmp['csv'].items()}),
        two_sided_cs_check='re-run in this invocation' if args.with_cs_check else 'not re-run in this invocation (file as left by the last run that used --with-cs-check)',
        figures='figures_v2/ are the Round 9 files (not regenerated; numerical inputs unchanged); report_v3.md re-captions them',
        v2_pre_round10_sha256={str(p.relative_to(PRE)): sha(p) for p in sorted(PRE.rglob('*')) if p.is_file() and p.suffix != '.pdf'},
        v1_preserved_sha256={p.name: sha(p) for p in sorted((RD / 'v1_pre_round9').glob('*')) if p.is_file()},
        steps=log,
        note='summary_v2.json, summary_v3.json and report_v3.md contain a generation timestamp. Anonymized-copy regeneration is location-dependent (see release_anon/MAPPING.md).')
    (RD / 'analysis_v3_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('raw evidence unchanged; wrote', RD / 'analysis_v3_manifest.json')


if __name__ == '__main__':
    main()
