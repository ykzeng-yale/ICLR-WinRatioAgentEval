# Usage: python SCRIPT NEW_EXPORT PRIOR_EXPORT
import ast,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();prior=Path(sys.argv[2]).resolve();v='experiments/live_ab_validation';sys.path[:0]=[str(root/v),str(root/'src')]
import vpanel as panel
same={n:(root/v/n).read_bytes()==(prior/v/n).read_bytes() for n in ('vgen.py','vrun.py','vpolicy.py','vband.py','cells.json')}
def f(path,name):return ast.dump(next(x for x in ast.parse(path.read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
funcs={n:f(root/v/'vpanel.py',n)==f(prior/v/'vpanel.py',n) for n in ('reference_rows','_ref_row_text','assert_reference_call_budget')}
configs={}
for label,changes in [('preflight',{'verification_mode':panel.VERIFY_PREFLIGHT}),('unknown',{'verification_mode':'skip'}),('wrongalpha',{'alpha_gate':.5}),('wrongtrials',{'trials_per_program':3})]:
 try: c=panel.PanelConfig(cells=('C1',),n_max=100,programs=1,**changes);configs[label]={'accepted':True,'recorded_mode':c.identity()['verification_mode']}
 except Exception as e:configs[label]={'accepted':False,'error':type(e).__name__}
out={'unchanged_scientific_files':same,'unchanged_panel_functions':funcs,'configuration':configs,'panel_or_reference_executed':False}
print(json.dumps(out,indent=2))
