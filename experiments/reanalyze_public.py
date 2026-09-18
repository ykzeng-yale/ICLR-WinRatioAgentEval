#!/usr/bin/env python3
"""Reanalyze archived public agent runs without executing agents or using an API.

Task-level bootstrap intervals are descriptive pointwise intervals. The common
seed coupling and historical verifier/pricing limitations are material.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare

MODEL = {'gpt-4.1-2025-04-14':'GPT-4.1', 'o4-mini-2025-04-16':'o4-mini',
         'claude-3-7-sonnet-20250219':'Claude-3.7'}
PAIRS = [('o4-mini','GPT-4.1'), ('Claude-3.7','GPT-4.1'), ('o4-mini','Claude-3.7')]
CONFIGS = [('primary', .05, False, 'off_diagonal'), ('cost_tol_0', 0., False, 'off_diagonal'),
           ('cost_tol_10', .10, False, 'off_diagonal'), ('cost_tol_20', .20, False, 'off_diagonal'),
           ('steps_before_cost', .05, True, 'off_diagonal'),
           ('paired_seed', .05, False, 'diagonal'),
           ('all_pairs', .05, False, 'all')]


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_sort(key):
    return (0, int(key)) if str(key).isdigit() else (1, str(key))


def load_tau(raw):
    records, sources, metadata = [], [], {}
    for path in sorted(raw.glob('tau2_*4trials.json')):
        d = json.loads(path.read_text())
        model = MODEL.get(d['info']['agent_info']['llm'])
        if model is None:
            continue
        domain = next(x for x in ['airline','retail','telecom'] if f'_{x}_' in path.name)
        key = (domain, model)
        metadata[key] = d
        sources.append({'file':path.name, 'sha256':digest(path),
                        'url':'https://raw.githubusercontent.com/sierra-research/tau2-bench/b7ea9074c1cba482b30687fecdb5c8425fd6f619/data/tau2/results/final/'+path.name.removeprefix('tau2_'),
                        'embedded_run_commit':d['info']['git_commit']})
        for s in d['simulations']:
            assert s['reward_info']['reward'] in (0., 1.)
            calls = sum(len(m.get('tool_calls') or []) for m in s['messages'] if m['role']=='assistant')
            turns = sum(m['role']=='assistant' for m in s['messages'])
            vals = [s['reward_info']['reward'], s['agent_cost'], calls, s['duration']]
            assert np.isfinite(vals).all() and min(vals) >= 0
            records.append(dict(family='tau2', domain=domain, model=model,
                                task_id=str(s['task_id']), trial=int(s['trial']), seed=int(s['seed']),
                                success=float(vals[0]), cost=float(vals[1]), steps=int(calls),
                                duration=float(vals[3]), assistant_messages=int(turns),
                                termination=s['termination_reason'], repository=''))
    for domain in ['airline','retail','telecom']:
        ref = metadata[(domain, 'GPT-4.1')]
        for model in MODEL.values():
            d = metadata[(domain, model)]
            canonical = lambda obj: json.dumps(sorted(obj, key=lambda t:str(t['id'])),sort_keys=True)
            assert canonical(ref['tasks']) == canonical(d['tasks'])
            assert ref['info']['git_commit'] == d['info']['git_commit']
            assert ref['info']['user_info'] == d['info']['user_info']
            seeds = lambda z:{(s['task_id'],s['trial']):s['seed'] for s in z['simulations']}
            assert seeds(ref) == seeds(d)
    return records, sources


def load_swe(raw):
    records, sources = [], []
    for run, model in [('20240402_sweagent_gpt4','SWE-agent GPT-4'),
                       ('20240402_sweagent_claude3opus','SWE-agent Claude-3-Opus')]:
        result_file = raw / f'swe_{run}_results.json'
        results = json.loads(result_file.read_text())
        resolved = set(results['resolved'])
        sources.append({'file':result_file.name, 'sha256':digest(result_file),
                        'url':f'https://raw.githubusercontent.com/SWE-bench/experiments/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/lite/{run}/results/results.json',
                        'embedded_run_commit':''})
        paths = sorted((raw/'swe_lite'/run).glob('*.traj'))
        assert len(paths) == 300, (run, len(paths))
        assert resolved <= {p.stem for p in paths}
        for p in paths:
            d = json.loads(p.read_text()); stats = d['info'].get('model_stats',{})
            cost = stats.get('instance_cost')
            assert cost is not None and np.isfinite(cost) and cost >= 0, p
            steps = len(d['trajectory'])
            records.append(dict(family='swe_lite', domain='SWE-bench Lite', model=model,
                                task_id=p.stem, trial=0, seed='', success=float(p.stem in resolved),
                                cost=float(cost), steps=steps, duration='', assistant_messages='',
                                termination=d['info'].get('exit_status',''), repository=p.stem.split('__')[0]))
            sources.append({'file':str(p.relative_to(raw)), 'sha256':digest(p),
                            'url':f'https://swe-bench-submissions.s3.amazonaws.com/lite/{run}/trajs/{p.name}',
                            'embedded_run_commit':''})
    return records, sources


def model_summary(records):
    out = []
    keys = sorted({(r['family'],r['domain'],r['model']) for r in records})
    for family, domain, model in keys:
        rows = [r for r in records if (r['family'],r['domain'],r['model'])==(family,domain,model)]
        durations = [float(r['duration']) for r in rows if r['duration']!='']
        out.append(dict(family=family,domain=domain,model=model,tasks=len({r['task_id'] for r in rows}),
                        runs=len(rows),success_rate=float(np.mean([r['success'] for r in rows])),
                        mean_cost=float(np.mean([r['cost'] for r in rows])),
                        median_cost=float(np.median([r['cost'] for r in rows])),
                        mean_steps=float(np.mean([r['steps'] for r in rows])),
                        mean_simulation_duration=float(np.mean(durations)) if durations else '',
                        termination_counts=json.dumps(dict(Counter(r['termination'] for r in rows)),sort_keys=True)))
    return out


def pair_task_statistics(records, domain, a, b, tolerance, reverse, pairing):
    grouped = {}
    for r in records:
        if r['domain']==domain and r['model'] in (a,b):
            grouped.setdefault((r['task_id'],r['model']),[]).append(r)
    tasks_a={task for task,model in grouped if model==a}
    tasks_b={task for task,model in grouped if model==b}
    assert tasks_a == tasks_b
    tasks=sorted(tasks_a,key=task_sort)
    columns = ['success','steps','cost'] if reverse else ['success','cost','steps']
    tiers = [Tier('success'), Tier(columns[1],False,relative_tolerance=tolerance if columns[1]=='cost' else 0),
             Tier(columns[2],False,relative_tolerance=tolerance if columns[2]=='cost' else 0)]
    values=[]; details=[]
    for task in tasks:
        ra=sorted(grouped[(task,a)],key=lambda r:r['trial'])
        rb=sorted(grouped[(task,b)],key=lambda r:r['trial'])
        aa=np.array([[r[col] for col in columns] for r in ra])
        bb=np.array([[r[col] for col in columns] for r in rb])
        eligible=np.ones((len(ra),len(rb),3),bool)
        eligible[:,:,1:] = ((aa[:,None,0] == 1) & (bb[None,:,0] == 1))[:,:,None]
        z,tier=compare(aa[:,None,:],bb[None,:,:],tiers,eligible=eligible)
        mask=np.ones(z.shape,bool)
        if pairing=='diagonal':
            mask=np.eye(len(ra),len(rb),dtype=bool)
            assert [r['seed'] for r in ra] == [r['seed'] for r in rb]
        elif pairing=='off_diagonal':
            mask=~np.eye(len(ra),len(rb),dtype=bool)
        z=z[mask];tier=tier[mask]
        if not len(z):
            raise ValueError('No comparisons in selected pairing')
        # Rows are task clusters; cross-run comparisons never enter bootstrap independently.
        probs=[np.mean(z==1),np.mean(z==-1),np.mean(z==0)]
        levels={name:float(np.mean(tier==k)) for k,name in enumerate(columns)}
        tier_signed={}
        for level in ['success','cost','steps']:
            decided=tier==columns.index(level)
            tier_signed[level+'_win']=float(np.mean(decided & (z==1)))
            tier_signed[level+'_loss']=float(np.mean(decided & (z==-1)))
            tier_signed[level+'_net']=float(np.mean(z*decided))
        sd=float(aa[:,0].mean()-bb[:,0].mean())
        vec=[float(z.mean()),sd,*probs,levels['success'],levels['cost'],levels['steps'],*tier_signed.values()]
        values.append(vec)
        details.append(dict(task_id=task, repository=ra[0]['repository'], net_benefit=vec[0],
                            success_diff=sd,p_win=probs[0],p_loss=probs[1],p_tie=probs[2],
                            success_decisive=levels['success'],cost_decisive=levels['cost'],steps_decisive=levels['steps'],
                            comparisons=len(z),**tier_signed))
        assert np.isclose(sum(tier_signed[level+'_net'] for level in ['success','cost','steps']),vec[0])
    return np.array(values), details


def analyze(records, boot, master_seed):
    rows=[];task_rows=[];repo_rows=[]
    rng=np.random.default_rng(master_seed)
    for domain in ['airline','retail','telecom','SWE-bench Lite']:
        pairs=PAIRS if domain!='SWE-bench Lite' else [('SWE-agent Claude-3-Opus','SWE-agent GPT-4')]
        configs=CONFIGS if domain!='SWE-bench Lite' else [(name,tol,rev,'all') for name,tol,rev,_ in CONFIGS[:5]]
        for a,b in pairs:
            indices=None
            for name,tol,reverse,pairing in configs:
                vals,details=pair_task_statistics(records,domain,a,b,tol,reverse,pairing)
                n=len(vals)
                if indices is None:
                    indices=rng.integers(0,n,size=(boot,n))
                sample=vals[indices,:2].mean(axis=1)
                ci=np.quantile(sample,[.025,.975],axis=0)
                means=vals.mean(axis=0);nw=means[2];nl=means[3]
                row=dict(family='tau2' if domain!='SWE-bench Lite' else 'swe_lite',domain=domain,
                         model_a=a,model_b=b,configuration=name,cost_relative_tolerance=tol,
                         resource_order='steps_cost' if reverse else 'cost_steps',pairing=pairing,
                         tasks=n,bootstrap_replicates=boot,p_win=nw,p_loss=nl,p_tie=means[4],
                         net_benefit=means[0],nb_ci_low=ci[0,0],nb_ci_high=ci[1,0],
                         success_diff=means[1],success_ci_low=ci[0,1],success_ci_high=ci[1,1],
                         win_ratio=nw/nl if nl>0 else '',success_decisive=means[5],
                         cost_decisive=means[6],steps_decisive=means[7],
                         illustrative_NI_margin=.03,
                         pointwise_NI_lower_above_margin=bool(ci[0,1]>-.03))
                rows.append(row)
                for index,key in enumerate(['success_win','success_loss','success_net','cost_win','cost_loss','cost_net','steps_win','steps_loss','steps_net']):
                    row[key]=means[8+index]
                if name=='primary':
                    for d in details:
                        task_rows.append(dict(family=row['family'],domain=domain,model_a=a,model_b=b,**d))
                    if domain=='SWE-bench Lite':
                        repos=sorted({d['repository'] for d in details})
                        for repo in repos:
                            subset=np.array([d['repository']!=repo for d in details])
                            repo_rows.append(dict(excluded_repository=repo,remaining_tasks=int(subset.sum()),
                                                 net_benefit=float(vals[subset,0].mean()),
                                                 success_diff=float(vals[subset,1].mean())))
    return rows,task_rows,repo_rows


def make_plots(rows,out):
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42})
    primary=[r for r in rows if r['configuration']=='primary']
    y=np.arange(len(primary))
    fig,axes=plt.subplots(1,2,figsize=(11.7,5.5),sharey=True)
    labels=[f"{r['domain']} | {r['model_a']} vs {r['model_b']}" for r in primary]
    for ax,key,lo,hi,title in [(axes[0],'net_benefit','nb_ci_low','nb_ci_high','Hierarchical net win'),
                               (axes[1],'success_diff','success_ci_low','success_ci_high','Task-success difference')]:
        x=np.array([r[key] for r in primary]);lower=np.array([r[lo] for r in primary]);upper=np.array([r[hi] for r in primary])
        ax.errorbar(x,y,xerr=np.array([x-lower,upper-x]),fmt='o',color='#22577A',capsize=3)
        ax.axvline(0,color='.5',lw=1);ax.set_title(title);ax.grid(axis='x',alpha=.2)
    axes[1].axvline(-.03,color='#B05E20',ls='--',lw=1,label='Illustrative −3 pp margin')
    axes[1].legend(loc='lower right',fontsize=8)
    axes[0].set_yticks(y,labels);axes[0].invert_yaxis()
    fig.suptitle('Historical public agent runs: task-cluster bootstrap, pointwise 95% intervals',fontsize=12)
    fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(out/f'public_primary_forest.{suffix}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    main=[r for r in primary if r['model_a']=='o4-mini' and r['model_b']=='GPT-4.1']
    fig,axes=plt.subplots(1,2,figsize=(6.7,2.9),sharey=True)
    yy=np.arange(len(main))
    for ax,key,lo,hi,title in [(axes[0],'net_benefit','nb_ci_low','nb_ci_high','Hierarchical net win'),
                               (axes[1],'success_diff','success_ci_low','success_ci_high','Success difference')]:
        x=np.array([r[key] for r in main]);lower=np.array([r[lo] for r in main]);upper=np.array([r[hi] for r in main])
        ax.errorbar(x,yy,xerr=np.array([x-lower,upper-x]),fmt='o',color='#22577A',capsize=3)
        ax.axvline(0,color='.5',lw=1);ax.set_title(title);ax.grid(axis='x',alpha=.2)
    axes[1].axvline(-.03,color='#B05E20',ls='--',lw=1)
    axes[0].set_yticks(yy,[r['domain'].capitalize() for r in main]);axes[0].invert_yaxis()
    axes[0].set_ylim(2.6,-.6)
    fig.suptitle('o4-mini versus GPT-4.1 on historical τ²-bench runs',fontsize=11)
    fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(out/f'public_main_contrast.{suffix}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.7,3.3))
    cases=[r for r in rows if r['model_a']=='o4-mini' and r['model_b']=='GPT-4.1' and r['configuration'] in ['primary','cost_tol_0','cost_tol_10','cost_tol_20']]
    for domain,color in [('airline','#22577A'),('retail','#C17817'),('telecom','#5C7F2D')]:
        rr=sorted([r for r in cases if r['domain']==domain],key=lambda r:r['cost_relative_tolerance'])
        ax.plot([100*r['cost_relative_tolerance'] for r in rr],[r['net_benefit'] for r in rr],marker='o',label=domain,color=color)
    ax.axhline(0,color='.5',lw=1);ax.set_xlabel('Cost practical-equivalence margin (% of larger cost)')
    ax.set_ylabel('Net win: o4-mini versus GPT-4.1');ax.legend();ax.grid(alpha=.2)
    ax.set_title('Sensitivity to cost tolerance; success-first, joint failures tie')
    fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(out/f'public_tolerance_sensitivity.{suffix}',dpi=180,bbox_inches='tight')
    plt.close(fig)


def fetch_missing(raw_dir, source_manifest):
    """Fetch only public source files with pinned URLs and verified hashes."""
    manifest=json.loads(source_manifest.read_text())
    for source in manifest['raw_sources']:
        relative=Path(source['file'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Source manifest contains unsafe output path')
        target=raw_dir/relative
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(source['url'],timeout=90) as response:
                data=response.read()
            if hashlib.sha256(data).hexdigest()!=source['sha256']:
                raise ValueError(f"Source hash mismatch: {relative}")
            target.write_bytes(data)
        elif digest(target)!=source['sha256']:
            raise ValueError(f"Existing source hash mismatch: {relative}")


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--raw-dir',type=Path,default=ROOT.parents[1]/'work/empirical_sources')
    p.add_argument('--bootstrap',type=int,default=10000)
    p.add_argument('--seed',type=int,default=2026091801)
    p.add_argument('--fetch-missing',action='store_true',help='Fetch public data using archived result manifest URLs/hashes')
    p.add_argument('--source-manifest',type=Path,default=ROOT/'results/public_manifest.json')
    args=p.parse_args()
    if args.bootstrap<5000:raise ValueError('At least 5000 task-bootstrap replicates required')
    if args.fetch_missing:
        fetch_missing(args.raw_dir,args.source_manifest)
    result_dir=ROOT/'results';plot_dir=ROOT/'plots'
    result_dir.mkdir(exist_ok=True);plot_dir.mkdir(exist_ok=True)
    tau,ts=load_tau(args.raw_dir);swe,ss=load_swe(args.raw_dir)
    records=tau+swe
    write_csv(result_dir/'public_run_metrics.csv',records)
    write_csv(result_dir/'public_model_summary.csv',model_summary(records))
    rows,task_rows,repo_rows=analyze(records,args.bootstrap,args.seed)
    write_csv(result_dir/'public_comparisons.csv',rows)
    write_csv(result_dir/'public_task_scores.csv',task_rows)
    write_csv(result_dir/'public_swe_leave_repository_out.csv',repo_rows)
    make_plots(rows,plot_dir)
    manifest=dict(generated_utc=datetime.now(timezone.utc).isoformat(),master_seed=args.seed,
                  bootstrap_replicates=args.bootstrap,python=platform.python_version(),numpy=np.__version__,
                  comparator_sha256=digest(ROOT/'src/winstats.py'),script_sha256=digest(Path(__file__)),
                  raw_sources=ts+ss,raw_source_manifest='work/empirical_sources/manifest.json',
                  swe_raw_manifest='work/empirical_sources/swe_lite_manifest.json',
                  tau_runs=len(tau),swe_runs=len(swe),
                  intervals='Pointwise 95% percentile task-cluster bootstrap; no multiplicity correction',
                  pairing='Primary 12 off-diagonal tau2 comparisons; common-seed and 16-pair V-stat sensitivities; SWE paired task outcome',
                  failure_rule='Both failures tie; efficiency tiers enabled only when both succeed',
                  relative_cost_tolerance='abs(A-B) > tolerance * max(abs(A),abs(B)); primary 0.05',
                  source_terms='Tau repository MIT notice retained; SWE raw transcripts not redistributed',
                  limitations=['Historical benchmark labels and prices','No live production A/B data',
                               'Independent conditional-task tau2 target uses off-diagonal seed pairs; requires independent distinct-seed runs',
                               'Task-bootstrap generalization beyond fixed benchmark requires task-sampling assumptions',
                               'SWE repository dependence examined by leave-one-repository-out sensitivity'])
    manifest['outputs']=[{'path':str(f.relative_to(ROOT)),'sha256':digest(f)} for f in sorted(result_dir.glob('public_*.csv'))]
    (result_dir/'public_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Analyzed {len(tau)} tau2 and {len(swe)} SWE trajectories; {len(rows)} contrast/configuration rows.')
    for r in rows:
        if r['configuration']=='primary':
            print(f"{r['domain']:15} {r['model_a']:25} vs {r['model_b']:15}: NB {r['net_benefit']:+.4f} [{r['nb_ci_low']:+.4f},{r['nb_ci_high']:+.4f}]; success {r['success_diff']:+.4f} [{r['success_ci_low']:+.4f},{r['success_ci_high']:+.4f}]")

if __name__=='__main__':main()
