import subprocess,json,math,types,ast
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
def show(rev,p):return subprocess.check_output(['git','show',rev+':'+p],cwd=repo,text=True)
b='results/live_ab_validation_v2/ablation_20260921/ABLATION_ANALYSIS.json'
old=json.loads(show('4a9f704^',b));new=json.loads(show('4a9f704',b));z=1.959963984540054
errors=[]
def equal(a,b,path):
 if isinstance(a,dict):
  for k,v in a.items():equal(v,b[k],path+'/'+k)
 elif isinstance(a,(float,int)):
  if abs(a-b)>1e-12:errors.append((path,a,b))
 elif a!=b:errors.append((path,a,b))
def wilson(k,n):
 p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return p,center-rad,center+rad
for cell,rows in new['cells'].items():
 for arm in ['original','disabled']:
  r=rows['deploy_rate_'+arm];p,l,u=wilson(r['events'],r['n']);assert abs(l-r['ci95_lo'])<1e-14 and abs(u-r['ci95_hi'])<1e-14
 for k in ['paired_difference_original_minus_disabled','discordant_pairs','joint_first_decision_categories','timing_capped_all_trials','timing_decision_conditional']:equal(old['cells'][cell][k],rows[k],cell+'/'+k)
for rung,r in new['contrasts'].items():
 equal(old['contrasts'][rung]['change_in_A_minus_N_deploy_contrast'],r['change_in_A_minus_N_deploy_contrast'],rung)
 prefix='P05' if rung.endswith('0.05') else 'P10'
 for arm in ['original','disabled']:
  a=new['cells'][prefix+'A']['deploy_rate_'+arm];b1=new['cells'][prefix+'N']['deploy_rate_'+arm];d=a['mean']-b1['mean'];l=d-math.hypot(a['mean']-a['ci95_lo'],b1['ci95_hi']-b1['mean']);u=d+math.hypot(a['ci95_hi']-a['mean'],b1['mean']-b1['ci95_lo']);got=r['A_minus_N_'+arm];assert abs(l-got['ci95_lo'])<1e-14 and abs(u-got['ci95_hi'])<1e-14
m=types.ModuleType('audit');m.__file__=str(repo/'experiments/live_ab_validation/ablation_analysis.py');exec(compile(show('4a9f704','experiments/live_ab_validation/ablation_analysis.py'),'immutable_analysis','exec'),m.__dict__)
want={(p,t):{} for p in range(2000) for t in range(4)}
cases={}
for name,rows in [('both_missing',{k:v for k,v in want.items() if k!=(0,0)}),('both_extra',{**want,(2000,0):{}})]:
 m._load_adapter=lambda *_:rows
 try:m.analyse_cell('P05N');cases[name]='NOT REFUSED'
 except ValueError as e:cases[name]=str(e)
assert all('intended 2000x4 grid' in v for v in cases.values())
try:m._combine(new['cells']['P05N']['deploy_rate_original'],new['cells']['P05A']['deploy_rate_original']);raise AssertionError('marginal accepted')
except TypeError:cases['combine_marginal']='refused'
assert not errors
out={'unchanged_prior_numeric_fields_mismatches':errors,'wilson_marginals_checked':8,'newcombe_gaps_checked':4,'coordinate_stub_checks':cases,'contrasts':new['contrasts']}
Path(__file__).with_name('result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='contrasts'},indent=2))
