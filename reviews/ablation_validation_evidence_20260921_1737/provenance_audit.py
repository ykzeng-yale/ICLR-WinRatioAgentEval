import json,csv,io,gzip,hashlib,collections,subprocess
from pathlib import Path
repo=Path(__file__).resolve().parents[2];base=repo/'results/live_ab_validation_v2/ablation_20260921';h=lambda b:hashlib.sha256(b).hexdigest();out={};pairs={}
for name in ['disabled_arm_attempt1_misplaced_cwd','disabled_arm']:
 d=base/name;pre=json.loads((d/'ABLATION_PREFLIGHT.json').read_text());pins=pre['pins_before'];plan=json.loads((d/'ABLATION_PLAN.json').read_text());child=json.loads((d/'AB_CHILD_DATA_RECEIPT.json').read_text());s=json.loads((d/'SUPERVISION.json').read_text());job=json.loads((d/'AB_JOB_RECEIPT.json').read_text());covered=set();keys=set();counts=collections.Counter();data_bytes=0;witnesses=[];checks=[]
 assert pre['namespace']==plan['namespace']==pins['detail']['run_identity']['namespace']==3;assert pre['law_pins']==pins['detail']['run_identity']['law_weights'];assert pins['detail']['run_identity']['expected_reference_calls']==0
 for rp in sorted(d.glob('shard*/COMPLETED_SHARD_RECEIPT.json')):
  r=json.loads(rp.read_text());c=r['coordinates'];e=plan['shards'][r['sequence']-1];assert r['pins']==pins;assert e['id']==r['shard_id'];coords={(c['cell'],i) for i in range(c['program_start_inclusive'],c['program_stop_exclusive'])};assert not covered&coords;covered|=coords;assert c['namespace']==3 and c['horizon']==2000;assert r['attempt_id']==child['attempt_id'];assert r['attempt_counts']=={'attempted':2000,'completed':2000,'failed':0,'missing':0,'skipped':0}
  for f,meta in r['files'].items():
   raw=(rp.parent/f).read_bytes();assert h(raw)==meta['sha256'] and len(raw)==meta['compressed_bytes'];plain=gzip.decompress(raw) if f.endswith('.gz') else raw;assert len(plain)==meta['uncompressed_bytes'];data_bytes+=len(raw)
   if f.endswith('.gz'):
    rows=list(csv.DictReader(io.StringIO(plain.decode())));assert len(rows)==6000
    for row in rows:
     ct=(row['cell'],int(row['program']));assert ct in coords;assert int(row['trial']) in range(4);k=ct+(int(row['trial']),row['construction']);assert k not in keys;keys.add(k)
    pairs.setdefault(rp.parent.name,{})[name]={'container':h(raw),'decompressed':h(plain),'rows':len(rows)}
   else: assert len(plain.splitlines())==1
  counts.update(r['observed']);w=json.loads((rp.parent/'SHARD_OPERATOR_WITNESS.json').read_text());assert w['operator_installed_throughout'] and w['completed_trials']==2000 and w['operator_entries']>0;witnesses.append(w['operator_entries'])
 assert covered=={(c,i) for c,n in plan['allocation'].items() for i in range(n)};assert data_bytes==child['child_counters']['output_bytes']
 for group in ['files','config']:
  for f,want in pins['detail']['source'][group].items():
   raw=subprocess.check_output(['git','show','6bdefd1:experiments/live_ab_validation/'+f],cwd=repo);checks.append({'file':f,'matches_delivery':h(raw)==want,'recorded':want})
 allbytes=sum(p.stat().st_size for p in d.rglob('*') if p.is_file());top={p.name:p.stat().st_size for p in d.iterdir() if p.is_file()}
 out[name]={'attempt_id':child['attempt_id'],'files':len([p for p in d.rglob('*') if p.is_file()]),'shards':16,'coordinates':len(covered),'row_keys':len(keys),'counts':dict(counts),'data_bytes':data_bytes,'all_bytes':allbytes,'source_checks':checks,'preflight_written':pre['written_utc'],'job_started':child['job_started_utc'],'pins_stable_claim':child['pin_drift_across_measurement'],'operator_entries_total_child':child['operator_entries_total'],'sum_shard_operator_entries':sum(witnesses),'supervisor':s['observed'],'parent_complete':job['scientific_completion'],'child_complete':child['data_completion'],'snapshot_from_total_minus_supervision_job':allbytes-top['SUPERVISION.json']-top['AB_JOB_RECEIPT.json']}
assert all(v['disabled_arm']==v['disabled_arm_attempt1_misplaced_cwd'] for v in pairs.values());out['independent_attempt_equality']={'all_16_container_and_decompressed_equal':True,'per_shard':pairs};out['combined_wall_seconds']=sum(out[n]['supervisor']['wall_seconds'] for n in ['disabled_arm','disabled_arm_attempt1_misplaced_cwd']);out['combined_attempt_directory_bytes']=sum(out[n]['all_bytes'] for n in ['disabled_arm','disabled_arm_attempt1_misplaced_cwd']);out['t1_log_tracebacks']=(repo/'results/t1_run_stdout.log').read_text().count('Traceback (most recent call last)');
ledger=json.loads((repo/'results/live_ab_validation_v2/measurement_20260921/ACCOUNTING_CORRECTION.json').read_text());mapping=json.loads((repo/'results/live_ab_validation_v2/DISCARDED_T1_PASS_MAPPING.json').read_text());enum={x['n']:x for x in ledger['correction_to_attempt_accounting']['enumerated']};mapmatches=[]
for x in mapping['2_what_the_allusion_actually_refers_to']['the_specific_discarded_passes_matching_the_allusion']:
 for k,v in x['known'].items():mapmatches.append({'attempt':x['n'],'key':k,'match':enum[x['n']][k]==v})
assert all(x['match'] for x in mapmatches);out['mapping_matches_existing_known_fields']=mapmatches
Path(__file__).with_name('provenance_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({n:{k:v for k,v in out[n].items() if k not in ['source_checks','pins_stable_claim']} for n in ['disabled_arm','disabled_arm_attempt1_misplaced_cwd']},indent=2));print('source mismatches',{n:[x for x in out[n]['source_checks'] if not x['matches_delivery']] for n in ['disabled_arm','disabled_arm_attempt1_misplaced_cwd']});print('equal',out['independent_attempt_equality']['all_16_container_and_decompressed_equal'],'wall',out['combined_wall_seconds'],'bytes',out['combined_attempt_directory_bytes'],'tracebacks',out['t1_log_tracebacks'],'mappingverified',len(mapmatches))
