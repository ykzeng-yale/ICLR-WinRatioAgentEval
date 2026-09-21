import subprocess,gzip,io,csv,json,math,collections
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');out=Path(__file__).parent;commit='35ab9d1';base='results/live_ab_validation_v2/t1_run_20260921'
def show(p):return subprocess.check_output(['git','show',f'{commit}:{p}'],cwd=repo)
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,base],cwd=repo,text=True).splitlines();paths=[p for p in paths if p.endswith('/primary_rows.csv.gz')]
D=collections.defaultdict(collections.Counter);seen=collections.defaultdict(set);errorprogs=collections.defaultdict(set);C4=[];dups=0
for p in paths:
    for r in csv.DictReader(io.StringIO(gzip.decompress(show(p)).decode())):
        key=(r['cell'],r['construction']);coord=(int(r['program']),int(r['trial']));dups+=coord in seen[key];seen[key].add(coord);d=D[key];d['n']+=1;dec=r['decision'];d[dec]+=1
        for f in r:
            if f.startswith('ever_'):d[f]+=int(r[f])
        fd=dec=='DEPLOY' and r['cell'] not in ['C7','C8'];fh=dec=='RETAIN_INCUMBENT';err=fd or fh
        d['false_deploy']+=fd;d['false_harm']+=fh;d['any_error']+=err
        if err:errorprogs[key].add(coord[0])
        if key==('C4','ADAPTER') and err:C4.append(r)
def wilson(k,n):
    z=1.959963984540054;q=z*z;center=(k+q/2)/(n+q);half=z*math.sqrt(k*(n-k)/n+q/4)/(n+q);return [center-half,center+half]
saved=json.loads(show(base+'/T1_ANALYSIS.json'));mismatch=[];summaries=[];alerts=[]
for s in saved['rows']:
    key=(s['cell'],s['construction']);d=D[key];n=d['n'];np=len({p for p,t in seen[key]});ev={'trial_false_deploy':d['false_deploy'],'trial_false_harm':d['false_harm'],'trial_any_error':d['any_error'],'miscover_h_twosided':d['ever_miscover_h'],'miscover_s_twosided':d['ever_miscover_s']}
    for field,k in ev.items():
        if s[field]['k']!=k or s[field]['n']!=n or max(abs(a-b) for a,b in zip(s[field]['wilson95'],wilson(k,n)))>1e-12:mismatch.append([key,field])
    kp=len(errorprogs[key]);r=s['program_family_any_erroneous']
    if r['k']!=kp or r['n']!=np or max(abs(a-b) for a,b in zip(r['wilson95'],wilson(kp,np)))>1e-12:mismatch.append([key,'family'])
    for field,nom in [('trial_false_deploy',.00625),('trial_false_harm',.00625),('trial_any_error',.0125),('miscover_h_twosided',.00625),('miscover_s_twosided',.00625)]:
        if wilson(ev[field],n)[0]>nom:alerts.append([*key,field,ev[field],n])
    if wilson(kp,np)[0]>.05:alerts.append([*key,'program_family_any_erroneous',kp,np])
    summaries.append({'cell':key[0],'construction':key[1],'n':n,'programs':np,**dict(d),'family_errors':kp})
results={'commit':subprocess.check_output(['git','rev-parse',commit],cwd=repo,text=True).strip(),'shards':len(paths),'rows':sum(d['n'] for d in D.values()),'duplicate_trial_construction_coordinates':dups,'complete_four_trial_programs':all(all({t for pp,t in seen[k] if pp==p}=={0,1,2,3} for p in {pp for pp,t in seen[k]}) for k in seen),'saved_count_or_Wilson_mismatches':mismatch,'summaries':summaries,'alerts_including_components':alerts,'C4_adapter_errors':C4,'C4_error_wilson':wilson(5,20000)}
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:v for k,v in results.items() if k!='summaries'},indent=2));print('COUNTS');print(json.dumps(summaries,indent=2))
