import subprocess,gzip,io,csv,json,math,collections
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');out=Path(__file__).parent;commit='0c17857';base='results/live_ab_validation_v2/powercurve_20260921'
def show(p):return subprocess.check_output(['git','show',f'{commit}:{p}'],cwd=repo)
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,base],cwd=repo,text=True).splitlines();paths=[p for p in paths if p.endswith('/primary_rows.csv.gz')]
d=collections.defaultdict(collections.Counter);seen=set();dups=0;programtrials=collections.defaultdict(set)
for p in paths:
 for r in csv.DictReader(io.StringIO(gzip.decompress(show(p)).decode())):
  key=(r['cell'],r['construction']);coord=(*key,int(r['program']),int(r['trial']));dups+=coord in seen;seen.add(coord);programtrials[coord[:-1]].add(coord[-1]);z=d[key];z['n']+=1;z[r['decision']]+=1
  for f in ['final_unresolved_fraction','final_unrevealed_fraction','final_cost_narrowed_fraction','final_n_certified']:z[f]+=float(r[f])
  for f in ['ever_miscover_h','ever_miscover_s']:z[f]+=int(r[f])
def wilson(k,n):
 q=1.959963984540054**2;c=(k+q/2)/(n+q);h=math.sqrt(q)*math.sqrt(k*(n-k)/n+q/4)/(n+q);return [c-h,c+h]
def contrast(con):
 a=d[('P10A',con)];n=d[('P10N',con)];pa=a['DEPLOY']/a['n'];pn=n['DEPLOY']/n['n'];delta=pa-pn;la,ua=wilson(a['DEPLOY'],a['n']);ln,un=wilson(n['DEPLOY'],n['n']);return {'A_deploy':a['DEPLOY'],'N_deploy':n['DEPLOY'],'n_each':a['n'],'A_minus_N':delta,'unpaired_SE':math.sqrt(pa*(1-pa)/a['n']+pn*(1-pn)/n['n']),'newcombe95':[delta-math.sqrt((pa-la)**2+(un-pn)**2),delta+math.sqrt((ua-pa)**2+(pn-ln)**2)]}
mech=json.loads(show(base+'/MECHANISM_TEST.json'));diff=[]
for row in mech['delay_gain_by_construction']:
 prefix='P'+str(round(row['mu_h']*100)).zfill(2);con=row['construction']
 for label,suffix in [('informative','A'),('non_informative','N')]:
  z=d[(prefix+suffix,con)];want=row[label]
  if want['deploy']!=z['DEPLOY'] or want['n']!=z['n']:diff.append([prefix,con,label])
result={'commit':subprocess.check_output(['git','rev-parse',commit],cwd=repo,text=True).strip(),'primary_files':len(paths),'rows':len(seen),'duplicate_coordinates':dups,'all_programs_four_trials':all(v=={0,1,2,3} for v in programtrials.values()),'mechanism_count_mismatches':diff,'contrasts_at_point1':{c:contrast(c) for c in ['ADAPTER','CPREFIX','NAIVE']},'rows':[{'cell':k[0],'construction':k[1],**dict(v),'power':v['DEPLOY']/v['n'],'wilson':wilson(v['DEPLOY'],v['n'])} for k,v in sorted(d.items())]}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));print(json.dumps([{'cell':r['cell'],'deploy':r.get('DEPLOY',0),'n':r['n'],'power':r['power'],'wilson':r['wilson']} for r in result['rows'] if r['construction']=='ADAPTER'],indent=2))
