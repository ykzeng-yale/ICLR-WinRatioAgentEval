"""Bounded audit; argument: exact exported repository path."""
import ast,math,copy,json,pathlib,types,sys
p=pathlib.Path(sys.argv[1]).resolve();src=p/'experiments/live_ab_validation/vrun.py';t=ast.parse(src.read_text());fs={'_finite_nonneg','total_workload_guard','_proposed_scale','_provenance_verdict','enforce_total_workload_guard'};assigns={'_CAP_FIELDS','_REQUIRED_IDENTITIES'}
t.body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in fs or isinstance(n,ast.ClassDef) and n.name=='TotalResourceRefusal' or isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id in assigns for v in n.targets)]
g={'math':math,'REFERENCE_WORKLOAD':{'accounted_components':['seconds','bytes','RSS']}};exec(compile(ast.fix_missing_locations(t),'guard-only','exec'),g)
ids={k:'synthetic_control' for k in ['code','config','policy','workload','receipt']};entry=dict(tier='T1',programs_total=28000,N_max=2000,seconds_projected=94.,reference_seconds_projected=1950.,total_seconds_projected=2044.,reference_cost_unresolved=False,bytes_projected=6000000.,peak_rss_projected=100000000.,admissible=True)
budget={'selected_tier':'T1','ladder':[entry],'reference_workload':{'combined_workload_receipt':{'present':True,'identities':ids,'planned_groups':12,'groups_total':12,'attempts_total':13,'attempts_failed':0}}};cfg={'budget':{'hard_limits':{'seconds':5400,'output_bytes':209715200,'peak_rss_bytes':2147483648}}}
def check(name,change=lambda b,p:None):
 b=copy.deepcopy(budget);pr={'identities':ids.copy()};change(b,pr);v=g['total_workload_guard'](b,cfg,pr);raised=False
 try:g['enforce_total_workload_guard'](v)
 except SystemExit:raised=True
 print(name,'authorized',v['authorized'],'class',v['refusal_class'],'raised',raised)
check('synthetic positive')
for name,value in [('NaN',float('nan')),('negative',-1.)]:check(name,lambda b,p,v=value:b['ladder'][0].update(reference_seconds_projected=v))
check('over bytes',lambda b,p:b['ladder'][0].update(bytes_projected=1e12))
check('over RSS',lambda b,p:b['ladder'][0].update(peak_rss_projected=1e12))
check('missing receipt',lambda b,p:b['reference_workload'].update(combined_workload_receipt={'present':False}))
check('short groups',lambda b,p:b['reference_workload']['combined_workload_receipt'].update(groups_total=5))
check('10x programs',lambda b,p:p.update(programs_total=280000))
check('10x horizon',lambda b,p:p.update(n_max=20000))
check('NaN programs',lambda b,p:p.update(programs_total=float('nan')))
check('zero planned/completed groups',lambda b,p:b['reference_workload']['combined_workload_receipt'].update(planned_groups=0,groups_total=0))
check('nonzero failed attempts',lambda b,p:b['reference_workload']['combined_workload_receipt'].update(attempts_failed=12))
# Static call-site proof, no native/import/measure work.
panel=ast.parse((p/'experiments/live_ab_validation/vpanel.py').read_text())
for func in ['run_panel','main']:
 f=next(n for n in panel.body if isinstance(n,ast.FunctionDef) and n.name==func);calls=[ast.unparse(n.func) for n in ast.walk(f) if isinstance(n,ast.Call)];print('panel',func,'guard_calls',[c for c in calls if 'guard' in c or 'enforce' in c])
f=next(n for n in ast.parse(src.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main');print('vrunmain guardcalls',[ast.unparse(n) for n in ast.walk(f) if isinstance(n,ast.Call) and 'total_workload_guard' in ast.unparse(n.func)])
