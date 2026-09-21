from pathlib import Path
import sys,json,hashlib,ast
root=Path(sys.argv[1]).resolve();v=root/'experiments/live_ab_validation';sys.path[:0]=[str(v),str(root/'src')]
import vlaunch
cases={}
for label,request in [('fixed',{}),('wrong_horizon',{'horizon':1000}),('nan',{'horizon':float('nan')}),('wrong_namespace',{'namespace':1}),('wrong_alpha',{'alpha_gate':.05}),('wrong_trials',{'trials_per_program':3}),('missing_refs',{'with_reference':False}),('wrong_allocation',{'allocation':dict(vlaunch.T1_ALLOCATION,C1=1999)})]:
 try: out=vlaunch.validate_request(request);cases[label]={'accepted':True,'programs':out['programs'],'trials':out['trials'],'reference_calls':out['reference_calls']}
 except Exception as e:cases[label]={'accepted':False,'error':type(e).__name__}
m=json.loads((root/'results/live_ab_validation_v2/T1_MANIFEST.json').read_text());p=m['pins']['detail']['source'];mismatch=[n for n,h in {**p['files'],**p['config']}.items() if hashlib.sha256((v/n).read_bytes()).hexdigest()!=h]
source=ast.parse((v/'vlaunch.py').read_text());main=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='main');stub=next(n for n in ast.walk(main) if isinstance(n,ast.If) and isinstance(n.test,ast.Attribute) and n.test.attr=='child');child_refuses=isinstance(stub.body[0],ast.Raise)
print(json.dumps({'source_commit':'7a12acb28197e3b08677ebe1171bcaae520b0835','request_cases':cases,'deposited_manifest_mismatched_files':mismatch,'deposited_manifest_dirty':m['pins']['detail']['repo']['validation_tree_dirty'],'child_path_refuses_unimplemented':child_refuses,'program_list_in_pin':m['pins']['detail']['run_identity']['programs'],'scientific_or_native_calls':0},indent=2))
