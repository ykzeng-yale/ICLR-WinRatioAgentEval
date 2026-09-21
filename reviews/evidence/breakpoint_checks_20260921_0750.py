"""Bounded audit; argument: exact exported repository path."""
import sys,json
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]).resolve();sys.path[:0]=[str(root/'experiments/live_ab_validation'),str(root/'src')]
import vgen as vg,vrun as vr
out=[]
for cid in ('C2','C3','C7'):
 d=vg.draw_trial(vg.CELL_BY_ID[cid],0,0,n_max=300,namespace=0);p=np.arange(1,301);op=vg.adapter_tick_sums(d,300,500,policy='operational');oracle=vg.adapter_tick_sums(d,300,500,policy='oracle');bad=[]
 for tick in range(1,501):
  st=vg.state_at_age(d,np.maximum(tick-p,0),policy='operational');mask=p<=min(tick,300)
  for k in ('h_lo','h_hi','s_lo','s_hi'):
   if getattr(op,k)[tick]!=np.sum(getattr(st,k)[mask]):bad.append((tick,k))
 out.append({'cell':cid,'sum_errors':bad,'operational_differs_from_oracle_ticks':int(np.sum((op.h_lo!=oracle.h_lo)|(op.h_hi!=oracle.h_hi))),'policy':vr.assert_operational_matches_policy(d,vr.make_config(300,0,policy='operational',schedule=vr.SCHEDULE_V2),ticks=(1,100,200,300,350,400,500))})
print(json.dumps(out,indent=2))
