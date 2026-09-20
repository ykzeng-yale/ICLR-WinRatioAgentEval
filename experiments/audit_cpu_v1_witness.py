"""Bounded v1 schedule witness; no random draws or full simulation.
Usage: python3 experiments/audit_cpu_v1_witness.py SNAPSHOT_ROOT RECEIPT_JSON
"""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
snapshot=Path(sys.argv[1]); output=Path(sys.argv[2])
assert hashlib.sha256((snapshot/'experiments/live_ab_validation/vrun.py').read_bytes()).hexdigest() == '8b735cfe994b2dddbc240ba5568ca680ccb37cc171ff024d0002230db65d862b'
assert hashlib.sha256((snapshot/'experiments/live_ab_validation/vgen.py').read_bytes()).hexdigest() == '2d0e2756b5e28b3af256b657953532ecb1849a404a1761952fae8a287e2745cd'
assert hashlib.sha256((snapshot/'experiments/live_ab_validation/vband.py').read_bytes()).hexdigest() == '55a9894ff5694099c05cedbdf695ecdad3ac4bd5025328cd445e0b1d3df8cd9c'
sys.path.insert(0,str(snapshot/'experiments/live_ab_validation'))
import vgen,vrun
out={"source_commit":"57482e317c42e971e33871e7d879e6ca61c8eac0","scope":"Deterministic bounded witness; not Monte Carlo event frequency"}
def make_draw(atom,d,f):
 n=len(atom);a=np.array(atom,dtype=np.int8);d=np.array(d,dtype=np.int64);f=np.array(f,dtype=np.int64)
 return vgen.TrialDraw(vgen.CELL_BY_ID['C1'],2,-1,0,n,a,vgen.ATOM_Z[a],vgen.ATOM_D[a],d,f,np.ones(n,dtype=bool),vgen.ATOM_SC[a],vgen.ATOM_CC[a],vgen.ATOM_CI[a],d.copy(),d.copy())
n=1000
atom=[5]*500+[3]*100+[4]*100+[5]*300
p=np.arange(1,n+1)
d=np.concatenate((np.zeros(500,dtype=int),1010-p[500:600],1100-p[600:700],1200-p[700:]))
draw=make_draw(atom,d,d)
assert all((x==0) or 100<=x<=699 for x in d)
cfg=vrun.make_config(n,2)
records,looks,updates=vrun.evaluate_trial(draw,cfg)
series,_,_,_=vrun.build_series(draw,cfg)
out['drain_witness']={'construction':'C1-support deterministic sequence, no outcome draws','looks_evaluated':looks,'runner':{k:{'decision':vrun.DECISION_LABEL[x.decision],'ever_miscover_h':x.ever_miscover_h,'ever_miscover_s':x.ever_miscover_s,'tau':x.tau,'unresolved_fraction':x.unresolved_fraction} for k,x in records.items()},'independent_intermediate':[]}
for tick in (1000,1010,1100,1200):
 done=draw.resolution_tick<=tick;k=int(np.argmax(~done)) if (~done).any() else n;m=int(done.sum())
 assert k==m
 h=int(draw.z[done].sum());s=int(draw.dsc[done].sum());radius=math.sqrt((m+100)*math.log((m+100)/(100*.00625**2)))/m
 out['drain_witness']['independent_intermediate'].append({'tick':tick,'completed_prefix':k,'h_mean':h/m,'s_mean':s/m,'h_lower':h/m-radius,'s_lower':s/m-radius,'deploy':h/m-radius>0 and s/m-radius>-.03})
assert records['CPREFIX'].decision==vrun.NO_DECISION and records['NAIVE'].decision==vrun.NO_DECISION
assert out['drain_witness']['independent_intermediate'][1]['deploy']
assert not records['CPREFIX'].ever_miscover_h and not records['NAIVE'].ever_miscover_h
out['complete_score_law_fixtures']={}
for law,counts in [('L3',[500,30,70,120,150,130]),('L4',[400,100,150,250,50,50])]:
 aa=np.repeat(np.arange(6),counts);dd=make_draw(aa,np.zeros(1000,dtype=int),np.zeros(1000,dtype=int));ss=vrun.build_series(dd,cfg)[0]['ADAPTER'];h=float(ss.l_h[999]);s=float(ss.l_s[999]);out['complete_score_law_fixtures'][law]={'mean_h':float(dd.z.mean()),'mean_s':float(dd.dsc.mean()),'lower_h':h,'lower_s':s,'deploy_final':h>0 and s>-.03}
assert not out['complete_score_law_fixtures']['L3']['deploy_final'] and out['complete_score_law_fixtures']['L4']['deploy_final']
from scipy.stats import binom
out["mc_flag_counterexample"]={"true_rate":.007,"trials":8000,"flag_count_threshold":64,"flag_probability":float(binom.sf(63,8000,.007))}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
