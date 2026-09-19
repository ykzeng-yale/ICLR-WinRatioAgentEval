"""Independent Round 10 verifier (local stream). Reads raw evidence only; calls no model, executes no generated program.
Usage: .venv/bin/python reviews/local_stream_round10_verify.py"""
import json, math, sys, csv
import numpy as np
from scipy import stats
import os
R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','')
sys.path.insert(0,R+'src')
eps=[json.loads(l) for l in open(R+'results/local_stream/episodes.jsonl')]
design=json.load(open(R+'results/local_stream/design.json'))
by={}
for e in eps: by[(e['task_id'],e['variant_letter'])]=e
def cmp(a,b,hb,tol):
    t=tol*max(abs(a),abs(b)); d=(b-a) if hb else (a-b)
    return 1 if d>t else (-1 if d<-t else 0)
def score(tid):  # B vs A, hierarchical absorbing
    a,b=by[(tid,'A')],by[(tid,'B')]
    sa,sb=int(a['success']),int(b['success'])
    if sa!=sb: return (1 if sb>sa else -1), sb-sa
    if not sa: return 0,0
    for k,tol in (('latency_s',.10),('completion_tokens',.10)):
        c=cmp(float(a[k]),float(b[k]),False,tol)
        if c: return c,0
    return 0,0
cl={}
for ar in design['arrivals']:
    key=ar['pair_index'] if ar.get('pair_index') is not None else 'single_'+ar['task_id']
    cl.setdefault(key,[]).append(ar['task_id'])
sizes=sorted(len(v) for v in cl.values())
print('clusters',len(cl),'size2',sizes.count(2),'size1',sizes.count(1),'tasks',sum(sizes))
N=591; G=len(cl)
out={}
for name,idx in (('NB',0),('succ',1)):
    S={t:score(t)[idx] for v in cl.values() for t in v}
    x=np.array(list(S.values()),float)
    T=np.array([sum(S[t] for t in v) for v in cl.values()],float)
    est=T.sum()/N
    sizes_=np.array([len(v) for v in cl.values()],float)
    r=T-est*sizes_
    se=math.sqrt(G/(G-1)*(r**2).sum())/N
    q=stats.t.ppf(.975,G-1)
    rad=math.sqrt(2*(4*295+1)*math.log(40))/N
    print(name,'est',est,'sumT',T.sum(),'task sd',x.std(ddof=1),'task se',x.std(ddof=1)/math.sqrt(N))
    print('  cluster se',se,'(no G/(G-1):',math.sqrt((r**2).sum())/N,') t',[est-q*se,est+q*se])
    print('  hoeff radius',rad,[est-rad,est+rad],'task hoeff',math.sqrt(2*math.log(40)/N))
    print('  cluster total dist',{int(k):int((T==k).sum()) for k in np.unique(T)})
    out[name]=T
# compare with e2_cluster_v3.csv
rows=list(csv.DictReader(open(R+'results/local_stream/e2_cluster_v3.csv')))
print('csv rows',len(rows),'sum score_total',sum(int(float(r['score_total'])) for r in rows),'sum succ',sum(int(float(r['success_diff_total'])) for r in rows))
mine=sorted(out['NB'].tolist()); theirs=sorted(float(r['score_total']) for r in rows); print('NB totals multiset equal',mine==theirs)
mine=sorted(out['succ'].tolist()); theirs=sorted(float(r['success_diff_total']) for r in rows); print('succ totals multiset equal',mine==theirs)
# task_scores.csv cross-check
ts=list(csv.DictReader(open(R+'results/local_stream/task_scores.csv')))
print('task_scores NB',sum(float(r['win'])-float(r['loss']) for r in ts)/len(ts), len(ts))
# E1 CS from monitor counts
import wincs
m=list(csv.DictReader(open(R+'results/local_stream/monitor_pass1.csv')))[-1]
w,l,t=int(m['n_win']),int(m['n_loss']),int(m['n_tie']); sp,sn=int(m['n_succ_pos']),int(m['n_succ_neg'])
print('counts',w,t,l,sp,sn)
print('NB cs',wincs.betting_cs_ternary(w,t,l,delta=.05) if True else None)
print('succ cs',wincs.betting_cs_ternary(sp,295-sp-sn,sn,delta=.05))
print('WR cs',wincs.win_ratio_cs_decided(w,l,delta=.05))
n=295;rho=100
print('R1 radius',math.sqrt((n+rho)/n**2*math.log((n+rho)/(rho*.05**2)))) 
