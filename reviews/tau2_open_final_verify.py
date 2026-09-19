import json,sys,csv,collections,math
import numpy as np
from scipy import stats
sys.path.insert(0,'src')
from winstats import betting_log_e_ternary, normal_mixture_radius
R='results/tau2_open/'
U={}
for arm in 'AB':
    d=json.load(open(R+'raw/tau2_open_arm%s.json'%arm))
    sims=d['simulations']; keys=collections.Counter((s['task_id'],s['trial']) for s in sims)
    exp={(str(t),k) for t in range(1,50) for k in (0,1)}
    print(arm,'n',len(sims),'keys ok',set(keys)==exp and max(keys.values())==1)
    term=collections.Counter(); trunc_a=trunc_u=0; seeds=collections.Counter()
    tot=collections.Counter(); models=collections.Counter(); maxc={'assistant':0,'user':0}
    for s in sims:
        ri=s['reward_info']; rew=None if ri is None else ri.get('reward')
        succ= rew is not None and rew>=1
        term[s['termination_reason']]+=1; seeds[(s['trial'],s['seed'])]+=1
        ct=pt=tc=calls=0; gen=0.0; gen_n=0
        for m in s['messages'] or []:
            u=m.get('usage'); rd=m.get('raw_data')
            if m['role']=='assistant':
                if u: ct+=u['completion_tokens']; pt+=u['prompt_tokens']; calls+=1
                tc+=len(m.get('tool_calls') or [])
                if m.get('generation_time_seconds') is not None: gen+=m['generation_time_seconds']; gen_n+=1
            if m['role'] in('assistant','user') and u:
                tot[m['role']+'_c']+=u['completion_tokens']; tot[m['role']+'_p']+=u['prompt_tokens']; tot[m['role']+'_calls']+=1
                maxc[m['role']]=max(maxc[m['role']],u['completion_tokens'])
                if rd:
                    models[(m['role'],rd.get('model'))]+=1
                    fr=[c.get('finish_reason') for c in rd.get('choices',[])]
                    if 'length' in fr:
                        if m['role']=='assistant': trunc_a+=1; print('  trunc',arm,s['task_id'],s['trial'],u['completion_tokens'],'succ',succ)
                        else: trunc_u+=1
        U[(arm,s['task_id'],s['trial'])]=dict(succ=succ,rew=rew,ct=ct,pt=pt,tc=tc,calls=calls,dur=s['duration'],gen=gen if gen_n else None,term=s['termination_reason'],start=s['start_time'],end=s['end_time'],nmsg=len(s['messages'] or []))
    us=[v for k,v in U.items() if k[0]==arm]
    print(' succ',sum(u['succ'] for u in us),'by trial',[sum(U[(arm,str(t),k)]['succ'] for t in range(1,50)) for k in (0,1)])
    print(' term',dict(term)); print(' seeds',dict(seeds)); print(' trunc agent/user',trunc_a,trunc_u,'maxc',maxc)
    print(' totals',dict(tot)); print(' models',dict(models))
    print(' infra',[(k[1],k[2],v['rew'],v['ct'],v['tc'],v['dur'],v['nmsg']) for k,v in U.items() if k[0]==arm and v['term']=='infrastructure_error'])
    print(' missing reward',sum(u['rew'] is None for u in us),'zero-tc',[(k[1],k[2],v['succ']) for k,v in U.items() if k[0]==arm and v['tc']==0])
    print(' means ct %.6f pt %.3f tc %.6f dur %.4f calls %.4f'%tuple(np.mean([u[f] for u in us]) for f in('ct','pt','tc','dur','calls')),'gen mean %.4f sum %.1f'%(np.mean([u['gen'] for u in us if u['gen'] is not None]),sum(u['gen'] for u in us if u['gen'] is not None)))
    print(' medians',[float(np.median([u[f] for u in us])) for f in('ct','tc','dur')],'sumdur',sum(u['dur'] for u in us),'maxdur',max(u['dur'] for u in us))
    print(' first/last',min(u['start'] for u in us),max(u['end'] for u in us))
    solved=[sum(U[(arm,str(t),k)]['succ'] for k in(0,1)) for t in range(1,50)]
    print(' tasks both/one/never',solved.count(2),solved.count(1),solved.count(0))
# compare with episodes.csv
bad=0
for r in csv.DictReader(open(R+'episodes.csv')):
    u=U[(r['arm'],r['task_id'],int(r['trial']))]
    if (r['success']=='True')!=u['succ'] or int(r['agent_tokens_completion'])!=u['ct'] or int(r['agent_tokens_prompt'])!=u['pt'] or int(r['n_assistant_tool_calls'])!=u['tc'] or abs(float(r['duration'])-u['dur'])>1e-9: bad+=1
print('episodes.csv mismatches',bad)
def score(a,b,tol=0.05):  # B vs A ; returns z,tier
    if a['succ']!=b['succ']: return (1 if b['succ'] else -1),0
    if not a['succ']: return 0,-1
    t=tol*max(abs(a['ct']),abs(b['ct'])); d=a['ct']-b['ct']
    if abs(d)>t: return int(np.sign(d)),1
    d=a['tc']-b['tc']
    if d!=0: return int(np.sign(d)),2
    return 0,-1
des=json.load(open(R+'design.json')); pairs=collections.defaultdict(dict); blocks=collections.defaultdict(set)
for a in des['arrivals']:
    assert a['pass1_arm'] not in pairs[a['pair_index']]
    pairs[a['pair_index']][a['pass1_arm']]=U[(a['pass1_arm'],a['task_id'],a['trial'])]; blocks[a['pair_index']].add(a['block'])
idx=sorted(pairs); assert idx==list(range(1,50)) and all(set(p)=={'A','B'} for p in pairs.values())
print('straddling',[k for k in idx if len(blocks[k])>1])
z=np.array([score(pairs[k]['A'],pairs[k]['B'])[0] for k in idx]); tiers=[score(pairs[k]['A'],pairs[k]['B'])[1] for k in idx]
dq=np.array([int(pairs[k]['B']['succ'])-int(pairs[k]['A']['succ']) for k in idx])
Sm=json.load(open(R+'summary.json'))
def chk(name,a,b): print('  CHK',name,a,b,'OK' if abs(a-b)<=1e-9 else 'FAIL')
for lab,n,key in(('all',49,'online'),('block1',24,'online_block1')):
    zz=z[:n]; qq=dq[:n]; o=Sm[key]
    print(lab,'W/T/L',(zz>0).sum(),(zz==0).sum(),(zz<0).sum(),'tiers',collections.Counter(tiers[:n]))
    chk('nb',zz.mean(),o['net_benefit']); chk('sd',qq.mean(),o['success_diff_hat'])
    chk('wins',(zz>0).sum(),o['tier_decomposition']['success']['wins']); chk('ties',(zz==0).sum(),o['ties'])
    nn=np.arange(1,n+1); pos=np.cumsum(zz>0);neg=np.cumsum(zz<0);qp=np.cumsum(qq>0);qn=np.cumsum(qq<0)
    lw=betting_log_e_ternary(pos,neg,nn,0.);lh=betting_log_e_ternary(neg,pos,nn,0.);lg=betting_log_e_ternary(qp,qn,nn,-0.03)
    chk('final win',lw[-1],o['monitoring']['final_log_e_win']);chk('final gate',lg[-1],o['monitoring']['final_log_e_gate']);chk('final harm',lh[-1],o['monitoring']['final_log_e_harm'])
    if n==49:
        mon=list(csv.DictReader(open(R+'monitor_pass1.csv')))
        print('  monitor csv maxdiff',max(max(abs(float(r['log_e_win'])-lw[i]),abs(float(r['log_e_gate'])-lg[i]),abs(float(r['log_e_harm'])-lh[i]),abs(int(r['z'])-zz[i])) for i,r in enumerate(mon)))
        for nm,p in(('win',lw),('gate',lg),('harm',lh)): print('  ',nm,'max %.4f at %d; from20 max %.4f'%(p.max(),p.argmax()+1,p[19:].max()))
        print('  thr',math.log(20),'any cross',(lw>=math.log(20)).any(),(lg>=math.log(20)).any(),(lh>=math.log(20)).any())
    r=float(normal_mixture_radius(n)); print('  R1 radius',r,[zz.mean()-r,zz.mean()+r])
print('pass1 succ A',sum(pairs[k]['A']['succ'] for k in idx),'B',sum(pairs[k]['B']['succ'] for k in idx))
print('infra units in pass1?',[k for k in idx for arm in 'AB' if pairs[k][arm]['term']=='infrastructure_error'])
# pair-level component diffs
for f in('ct','pt','tc','dur','gen'):
    for n in(49,24):
        dd=np.array([ (pairs[k]['B'][f]-pairs[k]['A'][f]) for k in idx[:n]],float); m=dd.mean(); h=stats.t.ppf(.975,n-1)*dd.std(ddof=1)/math.sqrt(n)
        print(' pair',f,n,'%.2f [%.2f, %.2f]'%(m,m-h,m+h))
# shadow
def tci(x):
    x=np.asarray(x,float); m=x.mean(); se=x.std(ddof=1)/math.sqrt(len(x)); h=stats.t.ppf(.975,len(x)-1)*se; return m,se,m-h,m+h
for mode in('all','offdiagonal','diagonal'):
    ts=[];w=l=c=0
    for t in range(1,50):
        sc=[]
        for i in(0,1):
            for j in(0,1):
                if mode=='diagonal' and i!=j: continue
                if mode=='offdiagonal' and i==j: continue
                sc.append(score(U[('A',str(t),i)],U[('B',str(t),j)])[0])
        ts.append(np.mean(sc)); w+=sum(s>0 for s in sc); l+=sum(s<0 for s in sc); c+=len(sc)
    m,se,lo,hi=tci(ts); print('shadow',mode,'nb %.10f se %.10f ci [%.10f, %.10f] pwin %.4f ploss %.4f'%(m,se,lo,hi,w/c,l/c))
    o=Sm['shadow_pairing'][mode]; chk('nb',m,o['net_benefit']); chk('lo',lo,o['nb_ci'][0]); chk('hi',hi,o['nb_ci'][1])
for f in('succ','ct','pt','tc','calls','dur'):
    dd=[np.mean([U[('B',str(t),k)][f] for k in(0,1)])-np.mean([U[('A',str(t),k)][f] for k in(0,1)]) for t in range(1,50)]
    print(' sametask',f,'%.4f se %.4f [%.4f, %.4f]'%tci(dd))
dd=[]
for t in range(1,50):
    g=lambda arm:[U[(arm,str(t),k)]['gen'] for k in(0,1) if U[(arm,str(t),k)]['gen'] is not None]
    dd.append(np.mean(g('B'))-np.mean(g('A')))
print(' sametask gen','%.4f se %.4f [%.4f, %.4f]'%tci(dd))
tab=collections.Counter((U[('A',str(t),k)]['succ'],U[('B',str(t),k)]['succ']) for t in range(1,50) for k in(0,1)); print('unit table (A,B)',dict(tab))
print('tasks solved by either',sum(any(U[(arm,str(t),k)]['succ'] for arm in 'AB' for k in(0,1)) for t in range(1,50)))
pre=[('A',str(t),0) for t in range(1,6)]
print('pre units',[(U[k]['rew'],round(U[k]['dur'],1),U[k]['end']) for k in pre]); print('6th A start',sorted(v['start'] for k,v in U.items() if k[0]=='A')[5])
print({k:Sm[k] for k in Sm if k.startswith('comp') or 'component' in k}.keys())
print('--- exclusion sensitivity')
ex={('A','6',0),('A','32',1)}
for f in('succ','ct','pt','tc','dur'):
    da=[];ta=[]
    for t in range(1,50):
        a=[U[('A',str(t),k)][f] for k in(0,1) if ('A',str(t),k) not in ex]; b=[U[('B',str(t),k)][f] for k in(0,1)]
        da.append(np.mean(b)-np.mean(a)); ta.append(np.mean(a))
    print(f,'%.4f se %.4f [%.4f, %.4f]'%tci(da),'meanA(task) %.2f'%np.mean(ta),'meanA(unit) %.2f'%np.mean([U[k][f] for k in U if k[0]=='A' and k not in ex]))
ts=[]
for t in range(1,50):
    sc=[score(U[('A',str(t),i)],U[('B',str(t),j)])[0] for i in(0,1) for j in(0,1) if ('A',str(t),i) not in ex]; ts.append(np.mean(sc))
print('NB excl','%.4f se %.4f [%.4f, %.4f]'%tci(ts))
print('--- task-mean medians / gen')
for f in('ct','tc','dur','gen'):
    for arm in 'AB':
        tm=[np.mean([U[(arm,str(t),k)][f] for k in(0,1) if U[(arm,str(t),k)][f] is not None]) for t in range(1,50)]
        un=[U[(arm,str(t),k)][f] for t in range(1,50) for k in(0,1) if U[(arm,str(t),k)][f] is not None]
        print(f,arm,'task-mean: mean %.2f median %.2f | unit: mean %.2f median %.2f n=%d'%(np.mean(tm),np.median(tm),np.mean(un),np.median(un),len(un)))
