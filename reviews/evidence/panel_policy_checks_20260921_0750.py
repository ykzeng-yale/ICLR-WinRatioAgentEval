"""Bounded audit; argument: exact exported repository path."""
import sys,json,gzip,csv,dataclasses,hashlib
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]).resolve();val=root/'experiments/live_ab_validation';sys.path[:0]=[str(val),str(root/'src')]
import vgen as vg,vrun as vr,vpanel as vp
receipt=json.load(open(val/'results/panel_fixture/receipt.json'));saved=list(csv.DictReader(gzip.open(val/'results/panel_fixture/primary_rows.csv.gz','rt')))
ref=list(csv.DictReader(open(val/'results/panel_fixture/reference_bands.csv')))
errors=[];generated=[];refmeans=0
for cellid in receipt['config']['cells']:
 c=vg.CELL_BY_ID[cellid]
 for t in range(4):
  d=vg.draw_trial(c,0,t,n_max=300,namespace=0);cfg=vr.make_config(300,0,schedule=vr.SCHEDULE_V2,policy='operational');r,looks,updates=vr.evaluate_trial(d,cfg)
  generated.extend(list(csv.DictReader([vr.trial_header(cfg.schedule)+'\n']+vr.trial_rows(c,0,t,r,cfg.schedule).splitlines())))
  for row in [x for x in ref if x['cell']==cellid and int(x['trial'])==t]:
   n=int(row['prefix']);a=d.z if row['score']=='H' else d.dsc
   if not np.isclose(float(row['running_mean']),np.mean(a[:n]),atol=1e-14):errors.append(('reference_mean',row))
   refmeans+=1
# fixed adapter witness assembled consistently from declared atom arrays; no random draw
base=vg.build_missed_crossing_witness(1000);n=1000;pos=np.arange(1,n+1);names=['BB0']*500+['C>I']*400+['BB0']*100;atoms=np.array([vg.ATOM_ORDER.index(s) for s in names],dtype=np.int8);end=np.where(pos<=500,pos,np.where(pos<=900,1010,1200));d=end-pos;f=d.copy();cf=np.ones(n,bool)
srev=vg.ATOM_SC[atoms];crev=vg.ATOM_CC[atoms];cpend=vg.ATOM_CI[atoms];code=(crev>20).astype(np.int8)*2+(cpend>20).astype(np.int8);combo=np.where(srev==1,vg._COMBO_CODE[code],-1);safe=np.maximum(combo,0)
w=dataclasses.replace(base,atom=atoms,z=vg.ATOM_Z[atoms],dsc=vg.ATOM_D[atoms],d=d,f=f,cand_first=cf,s_rev=srev,c_rev=crev,c_pend=cpend,a_narrow=np.clip(np.where(combo>=0,vg.THRESH_NARROW[safe,d],d),f,d),a_collapse=np.clip(np.where(combo>=0,vg.THRESH_COLLAPSE[safe,d],d),f,d))
cfg=vr.make_config(1000,0,schedule=vr.SCHEDULE_V2,policy='operational');records,*_=vr.evaluate_trial(w,cfg);r=records[vr.ADAPTER]
sums=vg.adapter_tick_sums(w,1000,1200,policy='operational');diffs=[]
for tick in range(1,1201):
 m=pos<=min(tick,1000);st=vg.state_at_age(w,np.maximum(tick-pos,0),policy='operational')
 for key in ('h_lo','h_hi','s_lo','s_hi'):
  if getattr(sums,key)[tick]!=np.sum(getattr(st,key)[m]):diffs.append((tick,key))
policy=vr.assert_operational_matches_policy(w,cfg,ticks=(1,500,1000,1009,1010,1011,1199,1200))
# A source-routing probe: fake reference returns sample mean bands; never a scientific reference execution.
calls=[];original=vp.eb_reference.reference_bands
vp.eb_reference.reference_bands=lambda a,alpha:(calls.append((a.copy(),alpha)) or (np.cumsum(a)/np.arange(1,len(a)+1)-.1,np.cumsum(a)/np.arange(1,len(a)+1)+.1))
rows,ch,cd=vp.reference_rows(w.cell,0,0,w,(100,500,1000),.00625);vp.eb_reference.reference_bands=original
out={'primary_saved_rows':len(saved),'regenerated_rows':len(generated),'primary_exact_row_agreement':generated==saved,'reference_means_checked':refmeans,'errors':errors,'witness':{'decision':r.decision,'tau_prefix':r.tau,'tau_tick':r.tau_tick,'pending_fraction':r.pending_fraction if hasattr(r,'pending_fraction') else None},'all1200tick_sum_errors':diffs,'policy_check':policy,'reference_routing_only':{'calls_h':ch,'calls_d':cd,'h_array_match':np.array_equal(calls[0][0],w.z),'d_array_match':np.array_equal(calls[1][0],w.dsc),'rows':len(rows)},'gzip_disk_bytes':len((val/'results/panel_fixture/primary_rows.csv.gz').read_bytes()),'gzip_uncompressed_bytes':len(gzip.decompress((val/'results/panel_fixture/primary_rows.csv.gz').read_bytes()))}
print(json.dumps(out,indent=2))
