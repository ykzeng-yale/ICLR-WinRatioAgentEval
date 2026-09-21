"""Pure-source and saved-receipt audit; argument: exact exported repository."""
import ast,json,pathlib,math,statistics,hashlib,types,copy,sys
p=pathlib.Path(sys.argv[1]).resolve();here=p/'experiments/live_ab_validation';x=json.loads((p/'results/live_ab_validation_v2/resource_check_delivered/combined_workload_timing.json').read_text()); t=ast.parse((here/'vrun.py').read_text()); names={'aggregate_horizon_costs','reference_workload_costs','_combined_workload_receipt','select_tier','total_workload_guard','enforce_total_workload_guard'}
t.body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.ClassDef) and n.name=='TotalResourceRefusal' or isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id in {'REFERENCE_WORKLOAD','REFERENCE_WORKLOAD_AMENDMENT'}]
g={'json':json,'math':math,'statistics':statistics,'vgen':types.SimpleNamespace(TRIALS_PER_PROGRAM=4),'REFERENCE_TIMING':p/'results/live_ab_validation_v2/resource_check_delivered/reference_timing.json','COMBINED_TIMING':p/'results/live_ab_validation_v2/resource_check_delivered/combined_workload_timing.json','REPO_ROOT':p,'sha256_file':lambda q:hashlib.sha256(q.read_bytes()).hexdigest()};exec(compile(ast.fix_missing_locations(t),'pureextract','exec'),g)
errs=[]
for pt in x['points']:
 for name,sc in pt['scopes'].items():
  v=sc['seconds_each'];errs.extend([abs(statistics.median(v)-sc['seconds_median']),abs(statistics.fmean(v)-sc['seconds_mean']),abs(statistics.stdev(v)-sc['seconds_stdev'])]);assert len(v)==20
 errs.append(abs(pt['missing_scope_seconds_median']-(pt['scopes']['combined']['seconds_median']-pt['scopes']['primary_only']['seconds_median'])))
 assert pt['call_counts']['combined']['reference_calls_total']==40;assert pt['call_counts']['combined']['reference_calls_per_program']==8
print('points',len(x['points']),'arithmetic_max_error',max(errs),'attempts',len(x['attempts']),'failures',sum(a['status']=='FAILED' for a in x['attempts']))
print('measured_combined_max_median_horizon',g['_combined_workload_receipt']()['seconds_per_program_by_horizon'])
saved=json.loads((p/'results/live_ab_validation_v2/budget_projection_repaired.json').read_text());pts=[]
for h,v in saved['horizon_aggregation']['by_horizon'].items():
 for c,r in v['cells'].items():pts.append(dict(r,cell=c,N_max=int(h)))
smoke=dict(balanced=True,points=pts,total_programs=20,peak_rss_bytes=96*2**20);cfg=json.loads((here/'cells.json').read_text());budget=g['select_tier'](smoke,cfg);v=g['total_workload_guard'](budget,cfg)
demo=json.loads((p/'results/live_ab_validation_v2/total_workload_guard_demonstration.json').read_text());print('demo_verdict_exact_match',v==demo['guard_verdict_as_projected']['verdict'],'total',v['total_seconds_projected'])
for name,mutate in [('unresolved',lambda e:e.update(reference_cost_unresolved=True)),('over_seconds',lambda e:e.update(reference_seconds_projected=10800)),('over_rss_bytes',lambda e:e.update(peak_rss_projected=99999999999,bytes_projected=99999999999)),('nan',lambda e:e.update(reference_seconds_projected=float('nan')))]:
 b=copy.deepcopy(budget);e=next(e for e in b['ladder'] if e['tier']==b['selected_tier']);mutate(e);v=g['total_workload_guard'](b,cfg);raised=False
 try:g['enforce_total_workload_guard'](v)
 except SystemExit:raised=True
 print('fixture',name,'authorized',v['authorized'],'raised',raised)
g['COMBINED_TIMING']=p/'ABSENT.json';b=g['select_tier'](smoke,cfg);print('no_combined_receipt_authorized',g['total_workload_guard'](b,cfg)['authorized'])
print('democode_hashmatch',demo['provenance']['vrun_sha256']==g['sha256_file'](here/'vrun.py'))
