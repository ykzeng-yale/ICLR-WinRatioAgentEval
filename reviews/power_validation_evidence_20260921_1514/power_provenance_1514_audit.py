import json,hashlib,csv,gzip,io,subprocess,collections
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');root=repo/'results/live_ab_validation_v2/powercurve_20260921';out=Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest()
plan=json.loads((root/'POWERCURVE_PLAN.json').read_text());rr=sorted(root.glob('shard*/COMPLETED_SHARD_RECEIPT.json'));first=json.loads(rr[0].read_text());pins=first['pins'];covered=set();primary=set();ref=set();counts=collections.Counter();sizes=collections.Counter();sources=[]
for rp in rr:
 r=json.loads(rp.read_text());c=r['coordinates'];expected={(c['cell'],i) for i in range(c['program_start_inclusive'],c['program_stop_exclusive'])};assert not expected&covered;covered|=expected
 e=plan['shards'][r['sequence']-1];assert e['id']==r['shard_id'] and e['cell']==c['cell'];assert e['program_start_inclusive']==c['program_start_inclusive'] and e['program_stop_exclusive']==c['program_stop_exclusive'];assert c['namespace']==3 and c['horizon']==2000
 assert r['pins']==pins and r['manifest_digest']==pins['receipt'];assert r['attempt_id']==first['attempt_id'] and r['source_commit']==first['source_commit'];assert r['attempt_counts']=={'attempted':2000,'completed':2000,'failed':0,'missing':0,'skipped':0};assert r['prior_failed_attempt'] is None
 for name,meta in r['files'].items():
  data=(rp.parent/name).read_bytes();assert h(data)==meta['sha256'] and len(data)==meta['compressed_bytes'];plain=gzip.decompress(data) if name.endswith('.gz') else data;assert len(plain)==meta['uncompressed_bytes'];sizes[name]+=len(data);n=0
  for row in csv.DictReader(io.StringIO(plain.decode())):
   ct=(row['cell'],int(row['program']));assert ct in expected;trial=int(row['trial']);assert trial in range(4);assert row['law']==c['cell'][:-1] and row['delay']==c['cell'][-1]
   if name.endswith('.gz'):
    key=ct+(trial,row['construction']);assert row['construction'] in ['ADAPTER','CPREFIX','NAIVE'];assert key not in primary;primary.add(key)
   else:
    key=ct+(trial,row['score'],int(row['prefix']));assert row['score'] in ['H','D'] and int(row['prefix']) in [100,500,2000];assert key not in ref;ref.add(key)
   n+=1
  assert n==(6000 if name.endswith('.gz') else 12000)
 counts.update(r['observed'])
assert covered=={(c,i) for c,n in plan['allocation'].items() for i in range(n)}
for group in ['files','config']:
 for name,want in pins['detail']['source'][group].items():
  matches={}
  for rev in [first['source_commit'],'35ab9d1','0c17857']:
   b=subprocess.check_output(['git','show',rev+':experiments/live_ab_validation/'+name],cwd=repo);matches[rev]=h(b)==want
  sources.append({'name':name,'matches':matches})
sup=json.loads((root/'SUPERVISION.json').read_text());job=json.loads((root/'PC_JOB_RECEIPT.json').read_text());child=json.loads((root/'PC_CHILD_DATA_RECEIPT.json').read_text());assert job['supervision']==sup;assert job['observed_totals']==child['observed_totals']=={k:counts[k] for k in ['primary_rows','reference_rows','reference_calls','trials']}
allb=sum(p.stat().st_size for p in root.rglob('*') if p.is_file());top={p.name:p.stat().st_size for p in root.iterdir() if p.is_file()};res={'reviewed_delivery':'0c17857','shards':len(rr),'programs':len(covered),'counts':dict(counts),'primary_keys':len(primary),'reference_keys':len(ref),'all_data_hashes_sizes_match':True,'all_pins_equal':True,'source_matches':sources,'runtime_registration_files_pinned':[x for x in ['vpowercurve.py','run_powercurve.py'] if x in pins['detail']['source']['files']],'data_bytes':dict(sizes),'all_bytes':allb,'top_bytes':top,'supervisor_child_bytes':sup['observed']['final_output_bytes_actual_child_dir'],'child_snapshot_recomputed':allb-sum(top[n] for n in ['SUPERVISION.json','PC_JOB_RECEIPT.json','PC_ANALYSIS.json','MECHANISM_TEST.json']),'source_commit':first['source_commit'],'attempt':first['attempt_id'],'all_prior_failed_attempt_null':True}
(out/'audit_results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
