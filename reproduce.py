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
    for name in ['simulation_manifest.json','stress_manifest.json','public_manifest.json','async_manifest.json','reproducibility_manifest.json']:
        path=ROOT/'results'/name
        if not path.exists():
            if name=='reproducibility_manifest.json':continue
            raise FileNotFoundError(path)
        m=json.loads(path.read_text())
        outputs=m.get('outputs',[])
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
    a=ap.parse_args()
    if a.mode=='verify':
        call('src/test_winstats.py');verify()
    else:
        call('src/test_winstats.py')
        call('experiments/run_simulations.py','--replicates','2000','--pairs','10000')
        call('experiments/run_stress_tests.py')
        call('experiments/run_async_experiment.py')
        if (ROOT/'experiments/run_decision_ablations.py').exists():call('experiments/run_decision_ablations.py')
        if a.mode=='full':
            args=['experiments/reanalyze_public.py','--raw-dir',str(a.public_raw_dir)]
            if a.fetch_public:args.append('--fetch-missing')
            call(*args)
        call('experiments/build_paper_results.py')
        call('experiments/build_async_paper_results.py')
    if a.build_pdf:
        subprocess.run(['latexmk','-pdf','-jobname=manuscript','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/'paper',check=True)
    print('Finished. No commercial requests were made. Prospective records are archived empirical observations.')

if __name__=='__main__':main()
