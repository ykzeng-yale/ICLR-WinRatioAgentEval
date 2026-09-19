"""Independent Round 9 verifier recomputation (no wincs/winstats import; brentq inversion). Read-only; no model, no git.
Usage: .venv/bin/python experiments/local_stream/verify_round9_independent.py"""
import numpy as np, pandas as pd, json, math
from scipy.optimize import brentq
from scipy.special import logsumexp
import os; R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','results','local_stream','')
mon=pd.read_csv(R+'monitor_pass1.csv'); z=mon['z'].values; d=mon['success_diff'].values; N=len(z); n=np.arange(1,N+1)
print('N',N,'wins/ties/losses',(z>0).sum(),(z==0).sum(),(z<0).sum(),'nb',z.mean(),'sd',d.mean(), 'sd counts',(d>0).sum(),(d<0).sum())
# R1
alpha=.05; rho=100.
rad=np.sqrt((n+rho)*np.log((n+rho)/(rho*alpha**2)))/n
nb=np.cumsum(z)/n; sd=np.cumsum(d)/n
print('R1 radius@N',rad[-1],'NB CS',nb[-1]-rad[-1],nb[-1]+rad[-1],'SD CS',sd[-1]-rad[-1],sd[-1]+rad[-1])
ex=(nb+rad<0); print('R1 first excl',n[ex][0],'stays from',n[np.where(~ex)[0][-1]+1], 'first n>=min?')
print('R1 sd lower > -0.03 ever:',((sd-rad)>-0.03).any())
# hedged betting, own implementation with brentq
lam=np.geomspace(1e-4,.5,40)
def logcap(p,t,q,m):
    def lk(l):
        with np.errstate(divide='ignore'):
            v=p*np.log1p(l*(1-m))+t*np.log1p(-l*m)+(q*np.log1p(l*(-1-m)) if q>0 else 0.)
        return logsumexp(v)-math.log(len(l))
    return np.logaddexp(lk(lam),lk(-lam))-math.log(2)
def cs(p,t,q,delta,f=logcap,lo0=-1+1e-12,hi0=1-1e-12,c=None):
    thr=math.log(1/delta); c=(p-q)/(p+t+q) if c is None else c
    g=lambda m:f(p,t,q,m)-thr
    lo=brentq(g,lo0,c,xtol=1e-13) if g(lo0)>0 else lo0
    hi=brentq(g,c,hi0,xtol=1e-13) if g(hi0)>0 else hi0
    return lo,hi
P,Q=(z>0).sum(),(z<0).sum(); print('hedged NB',cs(P,N-P-Q,Q,.05))
p2,q2=(d>0).sum(),(d<0).sum(); print('hedged SD',cs(p2,N-p2-q2,q2,.05))
# one-sided 0.025 diagnostic (max rule at delta=.025 == each tail at .025)
def logcap_max(p,t,q,m):
    def lk(l):
        with np.errstate(divide='ignore'):
            v=p*np.log1p(l*(1-m))+t*np.log1p(-l*m)+(q*np.log1p(l*(-1-m)) if q>0 else 0.)
        return logsumexp(v)-math.log(len(l))
    return max(lk(lam),lk(-lam))
print('dir .025 NB',cs(P,N-P-Q,Q,.025,f=logcap_max)); print('dir .025 SD',cs(p2,N-p2-q2,q2,.025,f=logcap_max))
print('old max .05 NB',cs(P,N-P-Q,Q,.05,f=logcap_max))
# WR bernoulli
lb=lam*2
def bern(k,nn,_,qv,mx=False):
    def lk(l):
        with np.errstate(divide='ignore'):
            v=k*np.log1p(l*(1-qv))+(nn-k)*np.log1p(-l*qv)
        return logsumexp(v)-math.log(len(l))
    return max(lk(lb),lk(-lb)) if mx else np.logaddexp(lk(lb),lk(-lb))-math.log(2)
thr=math.log(20)
def wr(delta,mx):
    g=lambda qv:bern(P,P+Q,0,qv,mx)-math.log(1/delta); c=P/(P+Q)
    lo=brentq(g,1e-9,c,xtol=1e-14); hi=brentq(g,c,1-1e-9,xtol=1e-14); return lo/(1-lo),hi/(1-hi)
print('hedged WR',wr(.05,False),'dir .025 WR',wr(.025,True))
# running hedged NB first exclusion
cp,cq=np.cumsum(z>0),np.cumsum(z<0)
his=[cs(cp[i],i+1-cp[i]-cq[i],cq[i],.05)[1] for i in range(N)]
his=np.array(his); e=his<0; print('R2 first excl',n[e][0],'stays from',n[np.where(~e)[0][-1]+1])
s=json.load(open(R+'summary_v2.json')); print(json.dumps({k:{kk:s['e1'][k].get(kk) for kk in ('nb_cs','success_diff_cs','wr_cs','radius_at_n','first_n_nb_upper_below_0','stays_below_0_from','first_n_nb_upper_below_0_at_or_after_min_n')} for k in ('R1','R2')},indent=1))
run=pd.read_csv(R+'running_cs_v2.csv'); print('max |running r2_nb_hi - mine|',np.abs(run['r2_nb_hi'].values-his).max(),'max|r1 rad diff|',np.abs(run['r1_radius'].values-rad).max())
print('harm first >= log20:', mon.loc[mon.log_e_harm>=thr,'n'].iloc[0], mon.columns.tolist())
