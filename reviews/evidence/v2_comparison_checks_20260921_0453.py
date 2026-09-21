"""Bounded exact-export audit. Usage: python this.py EXPORTED_REPO; no simulations."""
import csv,json,sys,collections,pathlib,hashlib
root=pathlib.Path(sys.argv[1]).resolve();val=root/'experiments/live_ab_validation'
sys.path[:0]=[str(val/'pinned_v2'),str(val),str(root/'src')]
import lab_enclosure as live
import vband
p=root/'results/live_ab_validation_v2/comparison_v2'
def rows(name):return list(csv.DictReader(x for x in (p/name).read_text().splitlines() if not x.startswith('#')))
defects=rows('comparison_defects.csv');pairs=[r for r in defects if r['defect_class']=='per_pair_enclosure_endpoint']
keys=['revealed_arm','ell','revealed_cost','enc12_lo','enc12_hi','enc11_lo','enc11_hi']
hist=collections.Counter(tuple(r[k] for k in keys) for r in pairs);checks=[]
for k,count in hist.items():
 d=dict(zip(keys,k));arm=d['revealed_arm'];other='incumbent' if arm=='candidate' else 'candidate';ell=float(d['ell']);cost=float(d['revealed_cost'])
 a={arm:live.EpisodeView.reveal(arm,1,cost,0),other:live.EpisodeView.pending(other,ell=ell)}
 b={arm:vband.Episode.pending(arm,100).finalized(1,cost),other:vband.Episode.pending(other,100).with_elapsed_cost(ell)}
 z=live.hierarchy_enclosure(a['candidate'],a['incumbent'],vband.TIERS);q=vband.hierarchy_bounds(b['candidate'],b['incumbent'])
 assert [z.lo,z.hi]==[float(d['enc11_lo']),float(d['enc11_hi'])];assert list(q)==[float(d['enc12_lo']),float(d['enc12_hi'])]
 oldeps=live.CERTIFICATE_EPS;live.CERTIFICATE_EPS=0;z0=live.hierarchy_enclosure(a['candidate'],a['incumbent'],vband.TIERS);live.CERTIFICATE_EPS=oldeps
 checks.append(dict(d,count=count,reproduced=True,live_zero_eps=[z0.lo,z0.hi],same_at_zero_eps=[z0.lo,z0.hi]==[z.lo,z.hi]))
lookrows=rows('comparison_vs_live_ab.csv');looks=[r for r in lookrows if r['checkpoint']=='look'];cell=[r for r in looks if r['kind']=='cell']
r={'source_commit':'b96f965b993e0e153acc88e3da31dd29ed847c40','defect_rows':len(defects),'per_pair_rows':len(pairs),'distinct_states':checks,'all_saved_pairs_live_contains_cpu':all(float(r['enc11_lo'])<=float(r['enc12_lo'])<=float(r['enc12_hi'])<=float(r['enc11_hi']) for r in pairs),'saved_look_rows':len(looks),'saved_cell_looks':len(cell),'cell_nonfinal_drain_looks':sum(int(r['tick'])>2000 and r['finalization']=='False' for r in cell),'saved_status_counts':dict(collections.Counter(r['status'] for r in looks)),'input_hashes':{str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [p/'comparison_defects.csv',p/'comparison_summary.json',p/'comparison_vs_live_ab.csv',val/'vcompare.py',val/'vband.py',val/'pinned_v2/lab_enclosure.py']}}
print(json.dumps(r,indent=2))
