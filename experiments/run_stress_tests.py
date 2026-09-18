"""Dated extensions after the first simulation run; no retrospective preregistration."""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import t, norm
from scipy.special import expit, logsumexp
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from winstats import normal_mixture_radius
from run_simulations import evaluate, generate, exact_targets, wilson


def main():
    rng=np.random.default_rng(20260918); reps=2000; n=10000
    looks=np.unique(np.r_[np.arange(100,n+1,50),n,np.arange(1,11)*(n//10)])
    rows=[]
    scenarios={'success_boundary':(.995,.995,.72,.75,.4),
               'compliance_boundary':(.985,.995,.75,.75,.4)}
    for name,params in scenarios.items():
        counts={}
        for start in range(0,reps,25):
            ds=evaluate(generate(rng,(min(25,reps-start),n),params),looks,.05)
            for method,d in ds.items(): counts[method]=counts.get(method,0)+int(d.any(axis=1).sum())
        for method,k in counts.items():
            lo,hi=wilson(k,reps)
            rows.append(dict(experiment=name,method=method,n=reps,event_count=k,rate=k/reps,ci_lower=lo,ci_upper=hi,metric='ever deploy'))
        print(name,counts,flush=True)
    # Shared task effects induce dependence across all cross-run comparisons.
    # The signed preference has zero unconditional mean by exchangeability.
    tasks=40; repeats=4; cover_cluster=0; cover_naive=0
    for start in range(0,reps,100):
        size=min(100,reps-start)
        task_effect=rng.normal(0,1.2,(size,tasks,1))
        a=task_effect/2+rng.normal(size=(size,tasks,repeats))
        b=-task_effect/2+rng.normal(size=(size,tasks,repeats))
        z=np.sign(a[...,None]-b[...,None,:])
        taskmean=z.mean(axis=(2,3)); grand=taskmean.mean(axis=1)
        se_cluster=taskmean.std(axis=1,ddof=1)/np.sqrt(tasks)
        se_naive=z.reshape(size,-1).std(axis=1,ddof=1)/np.sqrt(tasks*repeats**2)
        cover_cluster+=int((np.abs(grand)<=t.ppf(.975,tasks-1)*se_cluster).sum())
        cover_naive+=int((np.abs(grand)<=norm.ppf(.975)*se_naive).sum())
    for method,k in [('task_cluster_t',cover_cluster),('naive_cross_run_wald',cover_naive)]:
        lo,hi=wilson(k,reps)
        rows.append(dict(experiment='reused_run_dependence',method=method,n=reps,event_count=k,rate=k/reps,ci_lower=lo,ci_upper=hi,metric='coverage of zero'))
    # Nonexchangeable pair positions: E[h(A1,B2)]=.8, E[h(A2,B1)]=-.8.
    # The symmetric target is zero. The predictable order propensity responds
    # to previous raw scores, while maintaining [.1,.9] positivity.
    reps_adapt=1000; n_adapt=3000; s=np.zeros(reps_adapt); sh=np.zeros(reps_adapt)
    vs=np.zeros(reps_adapt); wealth=np.zeros((reps_adapt,40))
    naive_cross=np.zeros(reps_adapt,bool); ht_cross=np.zeros(reps_adapt,bool)
    ht_bet_cross=np.zeros(reps_adapt,bool)
    lam=np.geomspace(1e-4,.99/5,40) # HT values in [-5,5].
    for i in range(1,n_adapt+1):
        q=.1+.8*expit(1+s/np.sqrt(i))
        r=rng.random(reps_adapt)<q
        raw=np.where(r,rng.random(reps_adapt)<.9,rng.random(reps_adapt)<.1).astype(float)*2-1
        ht=np.where(r,raw/(2*q),raw/(2*(1-q)))
        s+=raw; sh+=ht; vs+=1/(4*np.minimum(q,1-q)**2)
        wealth+=np.log1p(ht[:,None]*lam)
        if i>=100 and i%10==0:
            naive_cross|=s/i-normal_mixture_radius(i,.05)>0
            ht_cross|=sh/i-normal_mixture_radius(i,.05,variance_process=vs)>0
            ht_bet_cross|=(logsumexp(wealth,axis=1)-np.log(40)>=np.log(20))
    for method,ev in [('unweighted_normal_mixture',naive_cross),('HT_normal_mixture',ht_cross),('HT_betting',ht_bet_cross)]:
        k=int(ev.sum()); lo,hi=wilson(k,reps_adapt)
        rows.append(dict(experiment='adaptive_order_null',method=method,n=reps_adapt,event_count=k,rate=k/reps_adapt,ci_lower=lo,ci_upper=hi,metric='false positive'))
    output=ROOT/'results'/'stress_results.csv'
    with output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    manifest={'seed':20260918,'classification':'extensions designed after initial run; not preregistered',
              'boundary_scenarios':scenarios,'boundary_truths':{k:exact_targets(v) for k,v in scenarios.items()},
              'replicates':reps,'pairs':n,'adaptive_replicates':reps_adapt,'adaptive_pairs':n_adapt,
              'adaptive_position_means':[.8,-.8],'adaptive_symmetric_truth':0,
              'adaptive_position_interpretation':'abstract bounded pair-score model, not generated agent traces',
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'core_sha256':hashlib.sha256((ROOT/'src'/'winstats.py').read_bytes()).hexdigest()}
    (ROOT/'results'/'stress_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Stress tests complete.',flush=True)

if __name__=='__main__': main()
