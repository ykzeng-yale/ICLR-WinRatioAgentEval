import json,hashlib,csv,gzip,io,subprocess,collections
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');rev='2c09a16';base='results/live_ab_validation_v2/powercurve_fine_20260921';h=lambda b:hashlib.sha256(b).hexdigest()
def blob(path,ref=rev):return subprocess.check_output(['git','show',ref+':'+path],cwd=repo)
def js(path):return json.loads(blob(path))
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',rev,'--',base],cwd=repo,text=True).splitlines();plan=js(base+'/POWERCURVE_PLAN.json');receipts=[p for p in paths if p.endswith('/COMPLETED_SHARD_RECEIPT.json')];first=js(receipts[0]);pins=first['pins'];covered=set();pk=set();rk=set();cnt=collections.Counter();sizes=collections.Counter();bytesall=0
for p in paths:bytesall+=len(blob(p))
for p in receipts:
 r=js(p);c=r['coordinates'];e=plan['shards'][r['sequence']-1];assert r['pins']==pins;assert c['namespace']==4;assert e['id']==r['shard_id'];coords={(c['cell'],i) for i in range(c['program_start_inclusive'],c['program_stop_exclusive'])};assert not covered&coords;covered|=coords
 for name,meta in r['files'].items():
  raw=blob(p.rsplit('/',1)[0]+'/'+name);assert h(raw)==meta['sha256'] and len(raw)==meta['compressed_bytes'];plain=gzip.decompress(raw) if name.endswith('.gz') else raw;assert len(plain)==meta['uncompressed_bytes'];sizes[name]+=len(raw);n=0
  for row in csv.DictReader(io.StringIO(plain.decode())):
   ct=(row['cell'],int(row['program']));assert ct in coords;trial=int(row['trial']);assert trial in range(4)
   if name.endswith('.gz'):
    k=ct+(trial,row['construction']);assert k not in pk;pk.add(k)
   else:k=ct+(trial,row['score'],int(row['prefix']));assert k not in rk;rk.add(k)
   n+=1
  assert n==(6000 if name.endswith('.gz') else 12000)
 cnt.update(r['observed'])
assert covered=={(c,i) for c,n in plan['allocation'].items() for i in range(n)}
checks={n:h(blob('experiments/live_ab_validation/'+n))==want for n,want in pins['detail']['source']['files'].items()};recovered={n:h(blob('experiments/live_ab_validation/'+n)) for n in ['run_powercurve.py','vpowercurve.py']}
failed='results/live_ab_validation_v2/powercurve_fine_20260921_failed_attempt1';fpaths=subprocess.check_output(['git','ls-tree','-r','--name-only',rev,'--',failed],cwd=repo,text=True).splitlines();fs=js(failed+'/SUPERVISION.json');s=js(base+'/SUPERVISION.json');assert fs==js(failed+'/SUPERVISION_FAILURE.json');assert js(failed+'/POWERCURVE_PLAN.json')==plan
res={'revision':rev,'shards':len(receipts),'coords':len(covered),'counts':dict(cnt),'unique_primary_keys':len(pk),'unique_reference_keys':len(rk),'all_hashes_sizes_match':True,'data_bytes':dict(sizes),'all_files':len(paths),'all_bytes':bytesall,'source_matches_at_delivery':checks,'retrospective_source_hashes':recovered,'omitted_driver_law_pins':[n for n in recovered if n not in pins['detail']['source']['files']],'plan_namespace':plan['namespace'],'shard_namespace':4,'run_identity_namespace':pins['detail']['run_identity']['namespace'],'fine_failed_files':fpaths,'fine_failed_bytes':sum(len(blob(p)) for p in fpaths),'failed_plan_equal_success_plan':True,'failed_wall':fs['observed']['wall_seconds'],'successful_wall':s['observed']['wall_seconds'],'combined_observed_attempt_walls':fs['observed']['wall_seconds']+s['observed']['wall_seconds'],'top_bytes':{p.split('/')[-1]:len(blob(p)) for p in paths if p.count('/')==base.count('/')+1}}
Path(__file__).with_name('audit_results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
