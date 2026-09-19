#!/usr/bin/env python3
"""Reproduce reported analyses. Never makes commercial model requests."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def call(*args):
    subprocess.run([sys.executable,*args],cwd=ROOT,check=True)

def verify():
    checks=0
    for name in ['simulation_manifest.json','stress_manifest.json','public_manifest.json','async_manifest.json','reproducibility_manifest.json','dm_baseline_manifest.json','decision_ablation_manifest.json','prospective_final_qa_manifest.json','trace_certificate_manifest.json','sequential_extensions_integrity.json','sequential_extension_paper_manifest.json','open_coding_integrity.json','open_airline_integrity.json']:
        path=ROOT/'results'/name
        if not path.exists():
            if name in ['reproducibility_manifest.json','dm_baseline_manifest.json','decision_ablation_manifest.json','prospective_final_qa_manifest.json','sequential_extensions_integrity.json','sequential_extension_paper_manifest.json']:continue
            raise FileNotFoundError(path)
        m=json.loads(path.read_text())
        outputs=m.get('outputs',m.get('output_sha256',m.get('file_hashes',[])))
        if isinstance(outputs,dict):outputs=[{'path':k,'sha256':v} for k,v in outputs.items()]
        for rec in outputs:
            if not isinstance(rec,dict):continue
            loc=rec.get('path',rec.get('file'));digest=rec.get('sha256')
            if loc and digest:
                p=ROOT/loc
                if not p.is_file() and '/' not in str(loc):p=ROOT/'results'/loc
                if not p.is_file():raise FileNotFoundError(p)
                actual=hashlib.sha256(p.read_bytes()).hexdigest()
                if actual!=digest:raise ValueError(f'Hash mismatch: {loc}')
                checks+=1
    print(f'Archived result integrity: {checks} output hashes matched.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['verify','simulate','full'],default='verify')
    ap.add_argument('--public-raw-dir',type=Path,default=ROOT/'work/empirical_sources')
    ap.add_argument('--fetch-public',action='store_true',help='Download pinned public benchmark data, never paid APIs')
    ap.add_argument('--build-pdf',action='store_true')
    ap.add_argument('--extensions',action='store_true',help='Explicitly rerun accepted CPU-only comparator and drift extensions')
    ap.add_argument('--coding',action='store_true',help='Recompute coding summaries from archived metrics; no model or generated-code execution')
    ap.add_argument('--airline',action='store_true',help='Recompute airline descriptions and masked replay from archived metrics; no model calls')
    a=ap.parse_args()
    if a.mode=='verify':
        call('src/test_winstats.py');verify()
    else:
        call('src/test_winstats.py')
        call('experiments/run_simulations.py','--replicates','2000','--pairs','10000')
        call('experiments/run_stress_tests.py')
        call('experiments/run_async_experiment.py')
        if (ROOT/'experiments/reproduce_dm_baseline.py').exists():call('experiments/reproduce_dm_baseline.py')
        if (ROOT/'experiments/run_decision_ablations.py').exists():call('experiments/run_decision_ablations.py')
        if a.mode=='full':
            args=['experiments/reanalyze_public.py','--raw-dir',str(a.public_raw_dir)]
            if a.fetch_public:args.append('--fetch-missing')
            call(*args)
            call('experiments/run_trace_certificates.py','--raw-dir',str(a.public_raw_dir))
            call('experiments/verify_trace_certificates_independent.py','--raw-dir',str(a.public_raw_dir))
        call('experiments/build_paper_results.py')
        call('experiments/build_async_paper_results.py')
        if (ROOT/'experiments/build_dm_paper_results.py').exists():call('experiments/build_dm_paper_results.py')
        if (ROOT/'experiments/build_ablation_paper_results.py').exists():call('experiments/build_ablation_paper_results.py')
        if (ROOT/'experiments/summarize_prospective_pilot.py').exists():call('experiments/summarize_prospective_pilot.py')
        call('experiments/build_trace_paper_results.py')
    if a.extensions:
        call('experiments/ustat_reference/run_ustat_reference.py','--workers','4')
        call('experiments/ustat_reference/run_ustat_reference.py','--workers','4','--calibration-only','--replicates','10000')
        call('experiments/ustat_reference/rare_event_diagnostic.py')
        call('experiments/drift_panel/run_drift_panel.py','--workers','4','--protocol-sha256','bb497cbb7c58fd1578530748c9d5ef834dc079e8b14973bc0bee348ca5c276cc')
    if a.extensions or a.mode != 'verify':
        if (ROOT/'experiments/build_sequential_extensions.py').exists():call('experiments/build_sequential_extensions.py')
    if a.coding or a.mode != 'verify':
        call('experiments/build_open_coding_results.py')
    if a.airline or a.mode != 'verify':
        call('experiments/build_open_airline_results.py')
    if a.build_pdf:
        subprocess.run(['latexmk','-pdf','-jobname=manuscript','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/'paper',check=True)
    print('Finished. No commercial requests were made. Prospective records are archived empirical observations.')

if __name__=='__main__':main()
