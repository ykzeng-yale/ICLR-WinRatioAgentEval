import json,hashlib,csv,gzip,io,subprocess,collections
from pathlib import Path
repo=Path('/Users/yukang/Documents/Codex/2026-09-17/i-x20/outputs/agent_win_eval');root=repo/'results/live_ab_validation_v2/t1_run_20260921';out=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((root/'T1_MANIFEST.json').read_text());spec=dict(m['execution_spec']);digest=spec.pop('canonical_digest');assert h(json.dumps(spec,sort_keys=True,separators=(',',':')).encode())==digest
issues=[];tot=collections.Counter();covered=set();rawkeys=set();refkeys=set();constructions=set();scoreprefix=set();sizes=collections.Counter();seq=[];pinvariants=set();sourcechecks=[]
for rp in sorted(root.glob('shard*/COMPLETED_SHARD_RECEIPT.json')):
 r=json.loads(rp.read_text());c=r['coordinates'];cell=c['cell'];expected={(cell,i) for i in range(c['program_start_inclusive'],c['program_stop_exclusive'])};assert not expected&covered;covered|=expected
 seq.append(r['sequence']);assert r['manifest_digest']==digest;assert r['job_id']=='T1-'+digest[:12];assert r['attempt_id']=='a1';assert r['pins']==m['pins'];assert r['source_commit']==m['pins']['detail']['repo']['head']
 plan=spec['shard_order'][r['sequence']-1];assert plan['id']==r['shard_id'];assert plan['cell']==cell;assert plan['program_start_inclusive']==c['program_start_inclusive'];assert plan['program_stop_exclusive']==c['program_stop_exclusive']
 assert c['namespace']==0 and c['horizon']==2000 and c['trial_indices']==[0,1,2,3]
 assert r['status']=='complete' and r['attempt_counts']=={'attempted':2000,'completed':2000,'failed':0,'missing':0,'skipped':0}
 shardcoords=set();localcounts={}
 for name,meta in r['files'].items():
  data=(rp.parent/name).read_bytes();assert h(data)==meta['sha256'];assert len(data)==meta['compressed_bytes'];plain=gzip.decompress(data) if name.endswith('.gz') else data;assert len(plain)==meta['uncompressed_bytes'];sizes[name]+=len(data)
  rows=csv.DictReader(io.StringIO(plain.decode()));count=0
  for row in rows:
   ct=(row['cell'],int(row['program']));assert ct in expected;trial=int(row['trial']);assert trial in range(4);shardcoords.add(ct)
   if name.endswith('.gz'):
    key=ct+(trial,row['construction']);assert key not in rawkeys;rawkeys.add(key);constructions.add(row['construction'])
   else:
    key=ct+(trial,row['score'],int(row['prefix']));assert key not in refkeys;refkeys.add(key);scoreprefix.add((row['score'],int(row['prefix'])))
   count+=1
  localcounts[name]=count
 assert shardcoords==expected;assert localcounts=={'primary_rows.csv.gz':6000,'reference_bands.csv':12000};tot.update(r['observed'])
 assert sum((rp.parent/n).stat().st_size for n in r['files'])==r['resources']['this_shard_output_bytes']
for group in ['files','config']:
 for name,want in m['pins']['detail']['source'][group].items():
  data=subprocess.check_output(['git','show',m['pins']['detail']['repo']['head']+':experiments/live_ab_validation/'+name],cwd=repo);sourcechecks.append({'path':name,'pass':h(data)==want})
expectedall={(c,i) for c,n in spec['allocation'].items() for i in range(n)};assert covered==expectedall;assert sorted(seq)==list(range(1,57))
files=[p for p in root.rglob('*') if p.is_file()];top={p.name:p.stat().st_size for p in root.iterdir() if p.is_file()};stored=sum(p.stat().st_size for p in files)
j=json.loads((root/'T1_JOB_RECEIPT.json').read_text());sup=json.loads((root/'SUPERVISION.json').read_text());child=json.loads((root/'T1_CHILD_DATA_RECEIPT.json').read_text());assert sup==j['supervision'];assert dict((k,tot[k]) for k in ['trials','reference_calls','primary_rows','reference_rows'])==j['observed_totals']==child['observed_totals']
res={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'manifest_digest_recomputed':digest,'shards':len(seq),'coordinate_count':len(covered),'allocation':spec['allocation'],'totals':dict(tot),'primary_key_count':len(rawkeys),'reference_key_count':len(refkeys),'constructions':sorted(constructions),'reference_score_prefixes':sorted(scoreprefix),'source_pin_checks':sourcechecks,'source_pin_all_match':all(x['pass'] for x in sourcechecks),'data_bytes':dict(sizes),'data_bytes_total':sum(sizes.values()),'file_count':len(files),'stored_all_bytes':stored,'top_level_bytes':top,'shard_receipt_bytes':sum(p.stat().st_size for p in root.glob('shard*/COMPLETED_SHARD_RECEIPT.json')),'supervisor_child_bytes':sup['observed']['final_output_bytes_actual_child_dir'],'terminal_claimed_bytes':j['terminal_budget']['all_artifact_bytes'],'all_minus_analysis_job_supervision':stored-top['T1_ANALYSIS.json']-top['T1_JOB_RECEIPT.json']-top['SUPERVISION.json'],'all_minus_analysis_job':stored-top['T1_ANALYSIS.json']-top['T1_JOB_RECEIPT.json']}
(out/'audit_results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
