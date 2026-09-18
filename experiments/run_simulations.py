"""Reproducible Monte Carlo study: independent online randomized-pair scores.

Six prespecified data-generating processes; all are synthetic, not live logs.
Each row of the simulation corresponds to one run from A and one from B on
independent arrivals from the same workload; randomized order is exchangeable.
"""
import argparse, csv, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from winstats import normal_mixture_radius, betting_log_e_ternary

SCENARIOS = {
    'null': (.995, .995, .75, .75, 1.),
    'efficiency_gain': (.995, .995, .75, .75, .55),
    'success_regression': (.995, .995, .65, .75, .40),
    'safety_regression': (.975, .995, .75, .75, .45),
    'joint_gain': (.995, .995, .84, .75, .75),
    'weak_gain': (.995, .995, .76, .75, 1.),
}


def generate(rng, shape, params):
    sa, sb, pa, pb, cost_ratio = params
    safe_a = rng.random(shape) < sa
    safe_b = rng.random(shape) < sb
    success_a = rng.random(shape) < pa
    success_b = rng.random(shape) < pb
    # Separate compliance and success: unsafe successful runs remain unsafe.
    cost_a = cost_ratio * rng.lognormal(0, .45, shape)
    cost_b = rng.lognormal(0, .45, shape)
    ds = safe_a.astype(np.int8)-safe_b.astype(np.int8)
    dq = success_a.astype(np.int8)-success_b.astype(np.int8)
    z = ds.copy()
    tied_safe = ds == 0
    z[tied_safe] = dq[tied_safe]
    eligible = tied_safe & safe_a & safe_b & success_a & success_b
    meaningful = np.abs(cost_a-cost_b) > .05*np.maximum(cost_a,cost_b)
    resource = eligible & meaningful
    z[resource] = np.sign(cost_b[resource]-cost_a[resource]).astype(np.int8)
    return z, dq, ds


def exact_targets(params):
    sa,sb,pa,pb,r=params
    # Success decisive when safety agrees; efficiency only if both safe/succeed.
    a=np.log(.95)
    mu=np.log(r); sd=np.sqrt(2)*.45
    resource_pref=norm.cdf((a-mu)/sd)-(1-norm.cdf((-a-mu)/sd))
    nb=(sa-sb)+(sa*sb+(1-sa)*(1-sb))*(pa-pb)+sa*sb*pa*pb*resource_pref
    return [float(nb),pa-pb,sa-sb]


def wilson(k,n):
    z=norm.ppf(.975); p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den
    r=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return c-r,c+r


def evaluate(zs, looks, alpha):
    thresholds=[0.,-.03,-.01]
    all_e=[]; all_normal=[]; all_z=[]; all_fixed=[]; all_group=[]
    for z,c in zip(zs,thresholds):
        pos=np.cumsum(z>0,axis=1)[:,looks-1]
        neg=np.cumsum(z<0,axis=1)[:,looks-1]
        means=(pos-neg)/looks
        s2=np.maximum((pos+neg-looks*means**2)/(looks-1),0)
        se=np.sqrt(s2/looks)
        all_e.append(betting_log_e_ternary(pos,neg,looks,c)>=np.log(1/alpha))
        all_normal.append(means-normal_mixture_radius(looks,alpha)>c)
        # Wald comparators are asymptotic and are not claimed finite-sample valid.
        all_z.append(means-norm.ppf(1-alpha)*se>c)
        all_fixed.append(means[:,-1]-norm.ppf(1-alpha)*se[:,-1]>c)
        all_group.append(means-norm.ppf(1-alpha/10)*se>c)
    group_mask=np.isin(looks,np.arange(1,11)*(looks[-1]//10))
    out={
        'win_only_betting':all_e[0],
        'guarded_betting':np.logical_and.reduce(all_e),
        'guarded_normal_mixture':np.logical_and.reduce(all_normal),
        'guarded_repeated_wald':np.logical_and.reduce(all_z),
        'guarded_group_bonferroni_wald':np.logical_and.reduce(all_group)&group_mask,
    }
    fixed=np.zeros_like(all_e[0]); fixed[:,-1]=np.logical_and.reduce(all_fixed)
    out['guarded_fixed_wald']=fixed
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--replicates',type=int,default=2000)
    ap.add_argument('--pairs',type=int,default=10000)
    ap.add_argument('--batch',type=int,default=25)
    ap.add_argument('--seed',type=int,default=20260917)
    args=ap.parse_args(); start=time.time()
    if args.pairs%100: raise ValueError('pairs must be divisible by 100')
    looks=np.unique(np.r_[np.arange(100,args.pairs+1,50),args.pairs,np.arange(1,11)*(args.pairs//10)])
    rows=[]; alpha=.05
    for j,(name,params) in enumerate(SCENARIOS.items()):
        rng=np.random.default_rng(np.random.SeedSequence([args.seed,j]))
        accum={}; targets=exact_targets(params)
        admissible=all(x>c for x,c in zip(targets,[0.,-.03,-.01]))
        for begin in range(0,args.replicates,args.batch):
            batch=min(args.batch,args.replicates-begin)
            decisions=evaluate(generate(rng,(batch,args.pairs),params),looks,alpha)
            for method,d in decisions.items():
                success=d.any(axis=1)
                stops=np.where(success,looks[np.argmax(d,axis=1)],args.pairs)
                acc=accum.setdefault(method,{'deploy':0,'stop_sum':0.,'stop_sq':0.,'positive_stop':[]})
                acc['deploy']+=int(success.sum()); acc['stop_sum']+=float(stops.sum())
                acc['stop_sq']+=float((stops.astype(float)**2).sum())
                acc['positive_stop'].extend(stops[success].tolist())
        for method,acc in accum.items():
            low,high=wilson(acc['deploy'],args.replicates)
            m=acc['stop_sum']/args.replicates
            rows.append(dict(scenario=name,method=method,replicates=args.replicates,max_pairs=args.pairs,
                true_net_benefit=targets[0],true_success_difference=targets[1],true_safety_difference=targets[2],
                admissible=admissible,deployments=acc['deploy'],deployment_rate=acc['deploy']/args.replicates,
                rate_ci_lower=low,rate_ci_upper=high,mean_pairs_used=m,
                mean_pairs_mcse=np.sqrt(max(acc['stop_sq']/args.replicates-m*m,0)/args.replicates),
                median_pairs_among_deployments=float(np.median(acc['positive_stop'])) if acc['positive_stop'] else ''))
        print(name, {k:round(v['deploy']/args.replicates,4) for k,v in accum.items()},flush=True)
    result=ROOT/'results'/'simulation_results.csv'
    with result.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    manifest=dict(arguments=vars(args),alpha=alpha,thresholds=[0.,-.03,-.01],looks=looks.tolist(),
        scenarios=SCENARIOS,seconds=time.time()-start,python=platform.python_version(),numpy=np.__version__,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        core_sha256=hashlib.sha256((ROOT/'src'/'winstats.py').read_bytes()).hexdigest(),
        interpretation='Synthetic independent-pair online streams; not live A/B experiment results.')
    (ROOT/'results'/'simulation_manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
