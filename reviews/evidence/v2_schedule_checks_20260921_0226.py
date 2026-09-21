from pathlib import Path
import sys,json
import numpy as np
import hashlib
if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 reviews/evidence/v2_schedule_checks_20260921_0226.py SNAPSHOT_DIR")
p=Path(sys.argv[1]).resolve()
manifest=json.loads(Path(__file__).with_name("v2_schedule_snapshot_20260921_0226.json").read_text())
for relative, expected in manifest["sha256"].items():
    assert hashlib.sha256((p/relative).read_bytes()).hexdigest()==expected, relative
sys.path.insert(0,str(p/'experiments/live_ab_validation'))
import vgen,vrun
out={}
for h in (1000,2000):
 d=vgen.build_missed_crossing_witness(h);cfg=vrun.make_config(h,2,schedule=vrun.SCHEDULE_V2)
 v1=vrun.evaluate_trial(d,cfg,vrun.SCHEDULE_V1)[0];v2=vrun.evaluate_trial(d,cfg)[0]
 out['baseline_witness_'+str(h)]={a:{'v1':vrun.DECISION_LABEL[v1[a].decision],'v2':vrun.DECISION_LABEL[v2[a].decision],'tau_prefix':v2[a].tau,'tau_tick':v2[a].tau_tick,'ever_miscover_h':v2[a].ever_miscover_h} for a in vrun.CONSTRUCTIONS}
def make(a,d):
 a=np.array(a,dtype=np.int8);d=np.array(d,dtype=np.int64);n=len(a)
 return vgen.TrialDraw(vgen.CELL_BY_ID['C1'],2,-1,0,n,a,vgen.ATOM_Z[a],vgen.ATOM_D[a],d,d.copy(),np.ones(n,dtype=bool),vgen.ATOM_SC[a],vgen.ATOM_CC[a],vgen.ATOM_CI[a],d.copy(),d.copy())
n=1000;pos=np.arange(1,n+1);d=make([5]*500+[3]*400+[5]*100,np.concatenate([np.zeros(500,dtype=int),1010-pos[500:900],1200-pos[900:]]));cfg=vrun.make_config(n,2,schedule=vrun.SCHEDULE_V2)
r1=vrun.evaluate_trial(d,cfg,vrun.SCHEDULE_V1)[0]['ADAPTER'];r2=vrun.evaluate_trial(d,cfg)[0]['ADAPTER']
out['adapter_timing']={k:{'tau_prefix':r.tau,'tau_tick':r.tau_tick,'unresolved':r.unresolved_fraction,'final_unresolved':r.final_unresolved_fraction,'decided_at_finalization':r.decided_at_finalization} for k,r in [('v1',r1),('v2',r2)]}
assert r2.tau_tick==1010 and r2.unresolved_fraction==.1 and r2.final_unresolved_fraction==0 and not r2.decided_at_finalization
# A direct per-tick oracle on a deterministic small, mixed-completion stream.
d=make([3,4,5,0,2],[2,0,0,5,100]);cfg=vrun.make_config(5,2,schedule=vrun.SCHEDULE_V2);ss=vrun.build_series_for(d,cfg)[0];ticks_checked=0
for t in range(1,206):
 done=d.resolution_tick<=t;k=next((j for j,v in enumerate(done) if not v),len(done));m=int(done.sum())
 assert int(ss['CPREFIX'].index[t-1])==k and int(ss['NAIVE'].index[t-1])==m
 prefix=min(t,5);ages=t-np.arange(1,6);st=vgen.state_at_age(d,ages)
 for nm,lo,hi in [('h',st.h_lo,st.h_hi),('s',st.s_lo,st.s_hi)]:
  r=cfg.radius[prefix];elo=max(-1,float(lo[:prefix].sum()/prefix-r));ehi=min(1,float(hi[:prefix].sum()/prefix+r))
  assert float(getattr(ss['ADAPTER'],'l_'+nm)[t-1])==elo and float(getattr(ss['ADAPTER'],'u_'+nm)[t-1])==ehi
 ticks_checked+=1
out['independent_tick_states_checked']=ticks_checked
# The declared event-by-event order never occupies completed-prefix k=1.
d=make([3,4,5],[2,0,0]);fine=vgen.completion_event_states(d,3,3)[0]
actual=[];done=set()
for t in range(1,4):
 for j in range(3):
  if int(d.resolution_tick[j])==t:
   done.add(j);k=0
   while k in done:k+=1
   actual.append((t,k))
out['finest_cprefix_phantom']={'function':list(zip(fine.tick.tolist(),fine.index.tolist())),'actual_declared_order':actual,'phantom':[x for x in zip(fine.tick.tolist(),fine.index.tolist()) if x not in actual]}
assert (3,1) in out['finest_cprefix_phantom']['phantom']
Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
