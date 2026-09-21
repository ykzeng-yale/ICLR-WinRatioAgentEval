import subprocess,gzip,io,csv,json,math,collections,hashlib
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');out=Path(__file__).parent;commit='2c09a16';base='results/live_ab_validation_v2/powercurve_fine_20260921'
def show(p,c=commit):return subprocess.check_output(['git','show',f'{c}:{p}'],cwd=repo)
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,base],cwd=repo,text=True).splitlines();paths=[p for p in paths if p.endswith('/primary_rows.csv.gz')]
d=collections.defaultdict(collections.Counter);seen=set();dups=0;programs=collections.defaultdict(set)
for p in paths:
 for r in csv.DictReader(io.StringIO(gzip.decompress(show(p)).decode())):
  key=(r['cell'],r['construction']);coord=(*key,int(r['program']),int(r['trial']));dups+=coord in seen;seen.add(coord);programs[coord[:-1]].add(coord[-1]);d[key]['n']+=1;d[key][r['decision']]+=1
  for f in ['ever_miscover_h','ever_miscover_s']:d[key][f]+=int(r[f])
def wilson(k,n):
 q=1.959963984540054**2;c=(k+q/2)/(n+q);h=math.sqrt(q)*math.sqrt(k*(n-k)/n+q/4)/(n+q);return [c-h,c+h]
combined=json.loads(show(base+'/COMBINED_CURVE.json'));mismatch=[]
for r in combined:
 if r['panel']!='fine(ns4)':continue
 key=('P'+str(round(r['mu_h']*100)).zfill(2)+('A' if r['delay']=='informative' else 'N'),'ADAPTER');v=d[key]
 if r['deploy']!=v['DEPLOY'] or r['n']!=v['n'] or max(abs(a-b) for a,b in zip(r['wilson95'],wilson(v['DEPLOY'],v['n'])))>1e-12:mismatch.append(key)
add=json.loads(show('results/live_ab_validation_v2/powercurve_20260921/PROVENANCE_ADDENDUM.json'));bind=add['gap_1_source_binding_was_incomplete']['for_THIS_delivery'];hs={name:hashlib.sha256(show('experiments/live_ab_validation/'+name,'35ab9d1')).hexdigest()==want for name,want in bind['recoverable_blobs_at_35ab9d1'].items()};laws={k:{'sum':sum(v.values()),'mu_h':(v['BB+']+v['C>I']-v['BB-']-v['I>C'])/10000,'mu_s':(v['C>I']-v['I>C'])/10000} for k,v in bind['runtime_law_and_cell_mapping']['laws'].items()}
res={'commit':subprocess.check_output(['git','rev-parse',commit],cwd=repo,text=True).strip(),'primary_files':len(paths),'primary_row_count':len(seen),'duplicate_coordinates':dups,'all_programs_four_trials':all(v=={0,1,2,3} for v in programs.values()),'combined_fine_mismatches':mismatch,'addendum_retrospective_hashes_match':hs,'addendum_laws':laws,'rows':[{'cell':k[0],'construction':k[1],**dict(v),'wilson95':wilson(v['DEPLOY'],v['n'])} for k,v in sorted(d.items())]};(out/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='rows'},indent=2));print(json.dumps([r for r in res['rows'] if r['construction']=='ADAPTER'],indent=2))
