# Usage: python SCRIPT NEW_EXPORT PRIOR_EXPORT
import sys,json,ast,hashlib
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path[:0]=[str(root/'experiments/live_ab_validation'),str(root/'src')]
import vpanel as p
cases={}
for label,kw in [('frozen',{}),('alpha_half',{'alpha_gate':.003125}),('alpha_other',{'alpha_gate':.5}),('alpha_nan',{'alpha_gate':float('nan')}),('trials3',{'trials_per_program':3}),('trials8',{'trials_per_program':8}),('operational_v1',{'schedule':'v1_reduced'})]:
 try:
  c=p.PanelConfig(cells=('C2',),n_max=300,programs=1,**kw);cases[label]={'accepted':True,'alpha':c.alpha_gate,'trials':c.trials_per_program,'policy':c.policy}
 except Exception as e:cases[label]={'accepted':False,'error':type(e).__name__}
prior=Path(sys.argv[2]).resolve();paths=['vgen.py','vrun.py','vpolicy.py','vband.py','cells.json'];same={n:(root/'experiments/live_ab_validation'/n).read_bytes()==(prior/'experiments/live_ab_validation'/n).read_bytes() for n in paths}
def body(path,name):return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),include_attributes=False)
ref_same=body(root/'experiments/live_ab_validation/vpanel.py','reference_rows')==body(prior/'experiments/live_ab_validation/vpanel.py','reference_rows')
out={'config_checks':cases,'unchanged_scientific_paths':same,'reference_rows_ast_unchanged':ref_same,'executed_panel':False};print(json.dumps(out,indent=2))
