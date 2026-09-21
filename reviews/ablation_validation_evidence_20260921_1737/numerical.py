"""Independent immutable-row aggregation; no scientific modules imported or trials run."""
import subprocess,gzip,io,csv,json,math,statistics,collections
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
COMMIT='7b4d17f';BASE='results/live_ab_validation_v2/ablation_20260921';CELLS=['P05N','P05A','P10N','P10A'];Z=1.959963984540054

def show(path):return subprocess.check_output(['git','show',f'{COMMIT}:{path}'],cwd=REPO)
def load(base):
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',COMMIT,base],cwd=REPO,text=True).splitlines();paths=[p for p in paths if p.endswith('/primary_rows.csv.gz') and any('/shard_' in p and '_'+c+'-p' in p for c in CELLS)];rows={};dups=0
 for p in paths:
  for r in csv.DictReader(io.StringIO(gzip.decompress(show(p)).decode())):
   if r['construction']!='ADAPTER':continue
   k=(r['cell'],int(r['program']),int(r['trial']));dups+=k in rows;rows[k]=r
 return rows,paths,dups

def mc(v):
 n=len(v);m=statistics.mean(v);sd=statistics.stdev(v) if n>1 else 0;se=sd/math.sqrt(n);return {'n':n,'mean':m,'sd':sd,'mc_se':se,'ci95_lo':m-Z*se,'ci95_hi':m+Z*se}
def diff(a,b):
 m=a['mean']-b['mean'];se=math.sqrt(a['mc_se']**2+b['mc_se']**2);return {'difference':m,'mc_se':se,'ci95_lo':m-Z*se,'ci95_hi':m+Z*se}
a,pa,da=load('results/live_ab_validation_v2/powercurve_20260921');b,pb,db=load(BASE+'/disabled_arm');assert set(a)==set(b)
saved=json.loads(show(BASE+'/ABLATION_ANALYSIS.json'));results={};mismatches=[]
def compare(v,w,path):
 for k,x in v.items():
  if isinstance(x,dict):compare(x,w[k],path+'.'+k)
  elif isinstance(x,(int,float)):
   if abs(x-w[k])>1e-9:mismatches.append([path+'.'+k,x,w[k]])
  elif x!=w[k]:mismatches.append([path+'.'+k,x,w[k]])
labels=['NO_DECISION','DEPLOY','RETAIN_INCUMBENT','CONFLICT'];jointfull={};capbad=[]
for c in CELLS:
 keys=sorted(k for k in a if k[0]==c);assert set((p,t) for _,p,t in keys)=={(p,t) for p in range(2000) for t in range(4)}
 depa=[int(a[k]['decision']=='DEPLOY') for k in keys];depb=[int(b[k]['decision']=='DEPLOY') for k in keys];D=[x-y for x,y in zip(depa,depb)]
 joint=collections.Counter((a[k]['decision'],b[k]['decision']) for k in keys);jointfull[c]={f'{x}->{y}':joint[(x,y)] for x in labels for y in labels}
 for k in keys:
  for arm,r in [('original',a[k]),('disabled',b[k])]:
   if r['decision']=='NO_DECISION' and (int(r['tau_tick'])!=2200 or int(r['tau_prefix'])!=2000):capbad.append([k,arm])
 ticka=[int(a[k]['tau_tick']) for k in keys];tickb=[int(b[k]['tau_tick']) for k in keys];pred=[int(a[k]['tau_prefix'])-int(b[k]['tau_prefix']) for k in keys];td=[x-y for x,y in zip(ticka,tickb)];both=[i for i,k in enumerate(keys) if a[k]['decision']!='NO_DECISION' and b[k]['decision']!='NO_DECISION']
 result={'paired_trials':len(keys),'deploy_rate_original':mc(depa),'deploy_rate_disabled':mc(depb),'paired_difference_original_minus_disabled':mc(D),'discordant_pairs':{'deploy_only_original':sum(x>0 for x in D),'deploy_only_disabled':sum(x<0 for x in D),'concordant':sum(x==0 for x in D)},'joint_first_decision_categories':{f'original={x} -> disabled={y}':v for (x,y),v in joint.items()},'timing_capped_all_trials':{'tau_tick_original':mc(ticka),'tau_tick_disabled':mc(tickb),'tau_tick_paired_difference':mc(td),'tau_prefix_paired_difference':mc(pred)},'timing_decision_conditional':{'trials_deciding_in_both_arms':len(both),'tau_tick_paired_difference':mc([td[i] for i in both]),'tau_prefix_paired_difference':mc([pred[i] for i in both])}}
 compare(result,saved['cells'][c],c);results[c]=result
contrasts={}
for mu,n,ar in [('0.05','P05N','P05A'),('0.10','P10N','P10A')]:
 contrasts[mu]={name:diff(results[ar][field],results[n][field]) for name,field in [('change_in_A_minus_N_deploy_contrast','paired_difference_original_minus_disabled'),('A_minus_N_original','deploy_rate_original'),('A_minus_N_disabled','deploy_rate_disabled')]};compare(contrasts[mu],saved['contrasts']['mu_h='+mu],mu)
report={'commit':subprocess.check_output(['git','rev-parse',COMMIT],cwd=REPO,text=True).strip(),'original_primary_files':len(pa),'disabled_primary_files':len(pb),'paired_trial_coordinates':len(a),'duplicates_original':da,'duplicates_disabled':db,'identical_coordinate_sets':set(a)==set(b),'exact_expected_program_trial_grids':True,'nondecider_cap_errors':capbad,'saved_numerical_mismatches':mismatches,'cells':results,'joint_16_categories':jointfull,'contrasts':contrasts}
out=Path(__file__).with_name('numerical_results.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['cells','joint_16_categories']},indent=2));print(json.dumps({c:{'original_deploys':sum(a[k]['decision']=='DEPLOY' for k in a if k[0]==c),'disabled_deploys':sum(b[k]['decision']=='DEPLOY' for k in b if k[0]==c),'paired':r['paired_difference_original_minus_disabled'],'both_count':r['timing_decision_conditional']['trials_deciding_in_both_arms'],'capped_tick_delta':r['timing_capped_all_trials']['tau_tick_paired_difference'],'both_tick_delta':r['timing_decision_conditional']['tau_tick_paired_difference']} for c,r in results.items()},indent=2))
