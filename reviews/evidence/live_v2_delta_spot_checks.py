from pathlib import Path
import sys,json,math,hashlib,itertools
import numpy as np
# Pass an isolated export of db930d7; never import the mutable owner's checkout.
if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 reviews/evidence/live_v2_delta_spot_checks.py SNAPSHOT_DIR")
base=Path(sys.argv[1]).resolve()
manifest=json.loads(Path(__file__).with_name("live_v2_delta_source_manifest.json").read_text())
for relative, expected in manifest["sha256"].items():
    assert hashlib.sha256((base/relative).read_bytes()).hexdigest()==expected, relative
sys.path[:0]=[str(base/'experiments/live_ab'),str(base/'experiments/live_ab_validation')]
import lab_enclosure as e
import vgen,vrun
cfg=json.loads((base/'experiments/live_ab/config.json').read_text());tiers=e.tiers_from_config(cfg)
c=e.EpisodeView.pending('candidate',ell=9.6);i=e.EpisodeView.reveal('incumbent',1,10.,0)
small=e.hierarchy_enclosure(c,i,tiers)
c2=e.EpisodeView.pending('incumbent',ell=9.5);i2=e.EpisodeView.reveal('candidate',1,10.,0)
eps=e.hierarchy_enclosure(i2,c2,tiers)
out={'reverse_certificate_9_6':[small.lo,small.hi],'threshold_9_5_conservative':[eps.lo,eps.hi]}
assert out['reverse_certificate_9_6']==[-1.,0.] and out['threshold_9_5_conservative']==[-1.,1.]
# No RNG: in-support deterministic ADAPTER first-decision timing counterexample.
n=1000;p=np.arange(1,n+1);atom=np.array([5]*500+[3]*400+[5]*100,dtype=np.int8)
d=np.concatenate([np.zeros(500,dtype=int),1010-p[500:900],1200-p[900:]])
assert all(x==0 or 100<=x<=699 for x in d)
draw=vgen.TrialDraw(vgen.CELL_BY_ID['C1'],2,-1,0,n,atom,vgen.ATOM_Z[atom],vgen.ATOM_D[atom],d,d.copy(),np.ones(n,dtype=bool),vgen.ATOM_SC[atom],vgen.ATOM_CC[atom],vgen.ATOM_CI[atom],d.copy(),d.copy())
rcfg=vrun.make_config(n,2);rec=vrun.evaluate_trial(draw,rcfg)[0]['ADAPTER'];r=math.sqrt((n+100)*math.log((n+100)/(100*.00625**2)))/n
mid=vgen.state_at_age(draw,1010-p)
lo_h=float(mid.h_lo.sum()/n-r);lo_s=float(mid.s_lo.sum()/n-r)
assert lo_h>0 and lo_s>-.03 and rec.decision==vrun.DEPLOY and rec.decided_at_finalization and rec.unresolved_fraction==0
out['adapter_timing_witness']={'runner_decided_at_finalization':rec.decided_at_finalization,'runner_unresolved_fraction':rec.unresolved_fraction,'runner_tau':rec.tau,'omitted_tick':1010,'omitted_lower_h':lo_h,'omitted_lower_s':lo_s,'omitted_unresolved_fraction':float((~mid.resolved).mean())}
# An exact two-order stopping example.
means=[]
for order in itertools.permutations([1,-1]):
 t=1 if order[0]==1 else 2
 means.append(sum(order[:t])/t)
out['proportional_stop_witness']={'equal_roster_mean':0,'means_by_two_orders':means,'expected_stopped_prefix_mean':sum(means)/2}
# Record exact successor hash binding, without declaring a historical pin match.
cells=json.loads((base/'experiments/live_ab_validation/cells.json').read_text());entry=cells['provenance']['vocabulary_alignment'];got=hashlib.sha256((base/entry['path']).read_bytes()).hexdigest()
out['vocabulary_supersession']={'historical_pin':entry['sha256'],'actual':got,'successor_matches':entry['superseded_by']['sha256']==got,'supersedes_matches':entry['superseded_by']['supersedes']==entry['sha256']}
assert out['vocabulary_supersession']['successor_matches'] and out['vocabulary_supersession']['supersedes_matches']
Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
