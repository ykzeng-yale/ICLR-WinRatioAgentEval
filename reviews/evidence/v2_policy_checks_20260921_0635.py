"""Bounded policy audit; argument: immutable exported repository."""
import sys,json,csv,dataclasses,itertools
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]).resolve(); val=root/'experiments/live_ab_validation';sys.path[:0]=[str(val),str(root/'src')]
import vcompare as vc,vpolicy as vp,vband as vb
vc.select_snapshot('v2');cfg=vc.load_frozen_config();pin=vc.verify_and_load_pinned(False);live=pin.lab_enclosure
states=0;errors=[]
for cost in (0.,1.,10.,40.):
 for ell in sorted(set([0.,cost,.95*cost,cost/.95,np.nextafter(.95*cost,np.inf),np.nextafter(cost/.95,np.inf),min(100.,cost/.95+1e-8)])):
  for arm,success in itertools.product(('candidate','incumbent'),(0,1)):
   rev=vb.Episode.pending('r',100.).finalized(success,cost);pend=vb.Episode.pending('p',100.).with_elapsed_cost(ell)
   cr,ir=(rev,pend) if arm=='candidate' else (pend,rev)
   lr=live.EpisodeView.reveal(arm,success,cost,0);lp=live.EpisodeView.pending('incumbent' if arm=='candidate' else 'candidate',ell=ell)
   ca,inc=(lr,lp) if arm=='candidate' else (lp,lr)
   a=vp.operational_hierarchy_bounds(cr,ir); b=live.hierarchy_enclosure(ca,inc,live._frozen_tiers())
   if a!=(b.lo,b.hi):errors.append([cost,ell,arm,success,a,(b.lo,b.hi)])
   states+=1
out={'partial_states':states,'partial_state_errors':errors,'saved':{}}
for tag in ('comparison_v2_alllook','comparison_v2_alllook_oracle'):
 rows=list(csv.DictReader(open(root/'results/live_ab_validation_v2'/tag/'comparison_vs_live_ab.csv')))
 out['saved'][tag]={'rows':len(rows),'agree':sum(r['status']=='AGREE' for r in rows),'nonfinal_drain':sum(r['drain_look']=='True' for r in rows),'drain_n_values':sorted(set(r['n'] for r in rows if r['drain_look']=='True'))}
 if tag.endswith('oracle'):
  defects=list(csv.DictReader(open(root/'results/live_ab_validation_v2'/tag/'comparison_defects.csv')))
  pairs=[r for r in defects if r['defect_class']=='per_pair_enclosure_endpoint']
  out['saved'][tag]['pair_rows']=len(pairs)
  out['saved'][tag]['live_contains_oracle']=sum(float(r['enc11_lo'])<=float(r['enc12_lo']) and float(r['enc11_hi'])>=float(r['enc12_hi']) for r in pairs)
# Fixed constructed all-look witness, not a new stochastic stream.
n=1000; pos=np.arange(1,n+1);succ=np.zeros(n,dtype=int);succ[500:900]=1
end=np.where(pos<=500,pos,np.where(pos<=900,1010,1200));dur=end-pos
st=vc.Stream('fixed-first-decision-witness','cell','C1',0,2,0,0,n,1200,np.zeros(n,int),succ,np.zeros(n,int),np.ones(n)*10,np.ones(n)*10,dur,dur,np.ones(n,bool),succ,succ)
cfg=dataclasses.replace(cfg,n_max=n,finalization_tick=1200)
out['witness']={}
for all_looks in (False,True):
 rows=[]
 class W:
  def writerow(self,r):rows.append(r)
 led=vc.DefectLedger();res=vc.compare_cell_stream(st,cfg,pin,led,W(),10**9,policy='operational',compare_drain_looks=all_looks)
 out['witness'][str(all_looks)]={'looks':res.looks,'tau_12':res.tau_12,'tau_11':res.tau_11,'disagreements':res.disagreeing_looks,'aborted':res.aborted,'first_decision_tick_12':next((r['tick'] for r in rows if r.get('label_12') not in ('CONTINUE','',None)),None),'first_decision_tick_11':next((r['tick'] for r in rows if r.get('label_11_mapped') not in ('CONTINUE','',None)),None)}
print(json.dumps(out,indent=2))
