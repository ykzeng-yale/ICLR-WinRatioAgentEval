#!/usr/bin/env python3
"""Quota-motivated, prospectively frozen Haiku workflow amendment.

Original v1 enrollment, result and spending artifacts are read-only. The v2
ledger carries every v1 reservation into the same combined four-dollar cap.
"""
import argparse
import copy
import importlib.util
import io
import json
import os
import platform
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pilot_v1',ROOT/'experiments/run_prospective_tau.py')
v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
MODEL='claude-haiku-4-5-20251001'
PROMPT=('Workflow verification instruction: Before any tool action that changes account or device state, '
        'check the applicable policy and confirm that the requested change follows from the observed state. '
        'After a corrective action, verify the relevant state with an available diagnostic tool or ask the user '
        'to confirm the specific symptom. Keep customer-facing messages concise. Do not declare resolution '
        'without an observable check. This instruction does not override the domain policy.')
VARIANTS=['standard','verification']


class CombinedLedger(v1.Ledger):
    def __init__(self,path,original_path):
        old=json.loads(original_path.read_text())
        self.carried=float(old['accounted_total_usd'])
        self.original_hash=v1.sha(original_path.read_bytes())
        super().__init__(path,cap=4.)
        if self.state.get('v1_ledger_sha256',self.original_hash)!=self.original_hash:
            raise ValueError('Original ledger changed; fail closed')
        self.state.update(v1_ledger_sha256=self.original_hash,v1_accounted_carry_usd=self.carried,
                          accounting='v1 retained reservations plus v2 completed usage and uncertain reservations')
        self.persist()
    def used(self):return self.carried+super().used()


class WorkflowCompletion(v1.DirectCompletion):
    def __call__(self,model,messages,tools=None,tool_choice=None,**kwargs):
        if model!=MODEL:raise v1.BudgetStop('Amended pilot only permits frozen Haiku model')
        if kwargs.get('max_tokens')==384 and self.ledger.context['variant']=='verification':
            messages=copy.deepcopy(messages)
            system=next((x for x in messages if x['role']=='system'),None)
            if system is None:messages.insert(0,{'role':'system','content':PROMPT})
            else:system['content']=system['content']+'\n\n'+PROMPT
        return super().__call__(model,messages,tools,tool_choice,**kwargs)


def freeze(path):
    old_path=ROOT/'experiments/prospective_protocol.json'
    old=json.loads(old_path.read_text());old_ledger=ROOT/'results/prospective_spend_ledger.json'
    summary=json.loads((ROOT/'results/prospective_summary.json').read_text())
    if summary['completed_runs']!=0:raise RuntimeError('Amendment allowed only before any completed v1 output')
    order=[]
    for r in old['execution_order']:
        variant='standard' if r['agent_model']=='gpt-5.6-luna' else 'verification'
        order.append({'index':r['index'],'task_id':r['task_id'],'variant':variant,
                      'run_seed':int(v1.sha(f"v2|{old['seed']}|{r['task_id']}|{variant}".encode())[:8],16)%(2**31)})
    plan={'frozen_utc':v1.stamp(),'amendment_reason':'OpenAI provider HTTP429 insufficient_quota/credit_balance_exhausted; no completed v1 model outputs',
          'source_v1_protocol_sha256':v1.sha(old_path.read_bytes()),'source_v1_ledger_sha256':v1.sha(old_ledger.read_bytes()),
          'tau_commit':old['tau_commit'],'task_ids':old['task_ids'],'tasks':old['tasks'],'seed':old['seed'],
          'execution_order':order,'backend_model':MODEL,'user_simulator':MODEL,'variants':VARIANTS,
          'standard_prompt':'Unmodified upstream default agent system prompt and telecom policy',
          'verification_prompt_appendix':PROMPT,'max_steps':40,'max_errors':4,'agent_output_cap':384,
          'user_output_cap':192,'temperature':0,'trial_count_per_variant_task':1,
          'combined_v1_v2_budget_cap_usd':4.,'carried_v1_reservation_usd':summary['accounted_total_usd'],
          'prices_per_million':{'input':1.,'output':5.},'hierarchy':old['hierarchy'],
          'failure_rule':old['failure_rule'],'cost_tolerance':.05,'step_tolerance':0,
          'interpretation':'Prospective paired workflow comparison with one fixed commercial model and simulated users; not production A/B or a model comparison',
          'script_sha256':v1.sha(Path(__file__).read_bytes())}
    if path.exists():raise RuntimeError('Never overwrite frozen amended plan')
    v1.atomic_json(path,plan)
    print('V2 frozen: same12 tasks,24 planned workflow runs,one Haiku backend, combined cap$4, carried reservation',summary['accounted_total_usd'],flush=True)


def summary(rows,ledger,plan):
    results=ROOT/'results';done=[r for r in rows if r['status']=='completed'];pairs=[]
    for task in plan['task_ids']:
        rr={r['variant']:r for r in done if r['task_id']==task}
        if len(rr)!=2:continue
        a=rr['verification'];b=rr['standard']
        if a['success']!=b['success']:z=1 if a['success']>b['success'] else -1;tier='success'
        elif not a['success']:z=0;tier='tie'
        elif abs(a['agent_cost_usd']-b['agent_cost_usd'])>.05*max(a['agent_cost_usd'],b['agent_cost_usd']):
            z=1 if a['agent_cost_usd']<b['agent_cost_usd'] else -1;tier='cost'
        elif a['assistant_tool_calls']!=b['assistant_tool_calls']:
            z=1 if a['assistant_tool_calls']<b['assistant_tool_calls'] else -1;tier='tool_calls'
        else:z=0;tier='tie'
        pairs.append({'task_id':task,'win_verification_over_standard':z,'decisive_tier':tier,
                      'success_verification':a['success'],'success_standard':b['success'],
                      'agent_cost_verification':a['agent_cost_usd'],'agent_cost_standard':b['agent_cost_usd']})
    v1.dump_csv(results/'prospective_v2_pairs.csv',pairs)
    out={'planned_tasks':12,'planned_runs':24,'registered_run_records':len(rows),'completed_runs':len(done),
         'complete_pairs':len(pairs),'combined_accounted_usd':ledger.used(),'v1_carry_usd':ledger.carried,
         'v2_usage_priced_upper_cost_usd':sum(c.get('accounted_cost_usd',0) for c in ledger.state['calls'] if c['status']=='completed'),
         'v2_uncertain_reserved_usd':sum(c['reservation_usd'] for c in ledger.state['calls'] if c['status']!='completed'),
         'v2_api_requests':len(ledger.state['calls']),'combined_cap_usd':4.,'updated_utc':v1.stamp(),
         'interpretation':plan['interpretation'],'variants':{}}
    for variant in VARIANTS:
        rr=[r for r in done if r['variant']==variant]
        out['variants'][variant]={'completed_runs':len(rr),'successes':sum(r['success'] for r in rr),
              'mean_agent_cost_usd':sum(r['agent_cost_usd'] for r in rr)/len(rr) if rr else None,
              'mean_tool_calls':sum(r['assistant_tool_calls'] for r in rr)/len(rr) if rr else None,
              'max_steps_terminations':sum(r['termination_reason']=='max_steps' for r in rr)}
    if pairs:
        n=len(pairs);w=sum(r['win_verification_over_standard']==1 for r in pairs);l=sum(r['win_verification_over_standard']==-1 for r in pairs)
        out.update(wins_verification=w,losses_verification=l,ties=n-w-l,net_win=(w-l)/n,
                   success_difference=sum(r['success_verification']-r['success_standard'] for r in pairs)/n)
    v1.atomic_json(results/'prospective_v2_summary.json',out)
    tex=("\\paragraph{Prospective workflow pilot.} "
         "Before collecting new outputs, we froze 12 telecom tasks and standard versus verification-prompt workflows "
         "using Claude Haiku 4.5 for both agent and user simulator. System order was randomized within tasks; "
         "the 40-step and output-token caps and deterministic verifier were identical. "
         f"We completed {len(done)} of 24 planned runs and {len(pairs)} task pairs. "
         f"The combined spending ledger accounted for \\${ledger.used():.4f} under a \\${4:.2f} cap, including "
         f"the retained \\${ledger.carried:.4f} reservation from an initial OpenAI quota failure that produced no completed trajectory. ")
    if pairs:tex+=f"The verification workflow recorded {out['wins_verification']} wins, {out['losses_verification']} losses, and {out['ties']} ties (net win {out['net_win']:.3f}). "
    tex+='This is a small descriptive paired laboratory workflow pilot with simulated users, not a production A/B experiment or a comparison between language models.\n'
    (ROOT/'experiments/prospective_v2_results.tex').write_text(tex)


def execute(args,plan):
    if plan['verification_prompt_appendix']!=PROMPT or plan['backend_model']!=MODEL:raise RuntimeError('Frozen workflow mismatch')
    get_tasks,Config,run_single,Eval,llm=v1.import_tau(args.tau_repo.resolve())
    from tau2.data_model.tasks import Task
    tasks={d['id']:Task.model_validate(d) for d in plan['tasks']}
    ledger=CombinedLedger(ROOT/'results/prospective_v2_spend_ledger.json',ROOT/'results/prospective_spend_ledger.json')
    direct=WorkflowCompletion(ledger,json.loads(args.credentials.read_text()))
    llm.completion=direct;llm.get_response_cost=lambda r:direct.costs[r.id]
    private=args.private_runs;private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
    results=ROOT/'results'
    v1.atomic_json(results/'prospective_v2_run_manifest.json',{'started_utc':v1.stamp(),'script_sha256':v1.sha(Path(__file__).read_bytes()),
             'shared_adapter_sha256':v1.sha((ROOT/'experiments/run_prospective_tau.py').read_bytes()),
             'frozen_plan_sha256':v1.sha((ROOT/'experiments/prospective_v2_protocol.json').read_bytes()),
             'python':platform.python_version(),'tau_commit':v1.COMMIT,'credentials_included':False,
             'transport':'Direct HTTP POST; zero retries or redirects','original_ledger_sha256':ledger.original_hash,
             'cost_interpretation':'Usage-priced upper list-cost; discounts ignored; uncertain requests retain reservation'})
    rowpath=results/'prospective_v2_runs.json';rows=json.loads(rowpath.read_text()) if rowpath.exists() else []
    completed_indices={r['execution_index'] for r in rows};stop=False
    for r in plan['execution_order']:
        if r['index'] in completed_indices:continue
        if any(c['status']=='reserved_uncertain' for c in ledger.state['calls']):stop=True
        rec={'execution_index':r['index'],'task_id':r['task_id'],'variant':r['variant'],'backend_model':MODEL,
             'run_seed':r['run_seed'],'status':'not_run_budget_or_infrastructure','success':'','agent_cost_usd':'',
             'user_cost_usd':'','assistant_tool_calls':'','duration_seconds':'','termination_reason':'','error_type':''}
        if stop:rows.append(rec);continue
        ledger.context={'stage':'v2','task_id':r['task_id'],'variant':r['variant'],'execution_index':r['index']}
        cfg=Config(domain='telecom',agent='llm_agent',user='user_simulator',llm_agent=MODEL,llm_user=MODEL,
                   llm_args_agent={'max_tokens':384,'temperature':0,'num_retries':0},llm_args_user={'max_tokens':192,'temperature':0,'num_retries':0},
                   max_steps=40,max_errors=4,max_concurrency=1,num_trials=1,max_retries=0,auto_review=False,verbose_logs=False,log_level='ERROR')
        try:
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                sim=run_single(cfg,tasks[r['task_id']],seed=r['run_seed'],evaluation_type=Eval.ALL,verbose_logs=False,auto_review=False)
            d=sim.model_dump(mode='json');filename=f"{r['index']:02d}_{v1.sha(r['task_id'].encode())[:12]}.json"
            v1.atomic_json(private/filename,d);os.chmod(private/filename,0o600)
            safe=v1.sanitize(sim,{**r,'agent_model':MODEL});safe['workflow_variant']=r['variant']
            v1.atomic_json(results/'prospective_v2_sanitized_traces'/filename,safe)
            calls=sum(len(m.get('tool_calls') or []) for m in d['messages'] if m['role']=='assistant')
            rec.update(status='completed',success=float(d['reward_info']['reward']),agent_cost_usd=d['agent_cost'],user_cost_usd=d['user_cost'],
                       assistant_tool_calls=calls,duration_seconds=d['duration'],termination_reason=d['termination_reason'])
        except v1.BudgetStop:rec.update(status='budget_stopped',error_type='BudgetStop');stop=True
        except Exception as e:rec.update(status='infrastructure_failure',error_type=type(e).__name__);stop=True
        rows.append(rec);v1.atomic_json(rowpath,rows);v1.dump_csv(results/'prospective_v2_runs.csv',rows);summary(rows,ledger,plan)
        print(f"V2 run {r['index']+1}/24 | {r['variant']} | {rec['status']} | success {rec['success']} | combined ${ledger.used():.4f}",flush=True)
    v1.atomic_json(rowpath,rows);v1.dump_csv(results/'prospective_v2_runs.csv',rows);summary(rows,ledger,plan)
    print(f'V2 closed: combined accounted ${ledger.used():.4f} / $4.00',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--execute',action='store_true')
    p.add_argument('--tau-repo',type=Path);p.add_argument('--credentials',type=Path);p.add_argument('--private-runs',type=Path)
    args=p.parse_args();planpath=ROOT/'experiments/prospective_v2_protocol.json'
    if args.prepare:
        if args.execute:raise ValueError('Freeze separately from execution')
        freeze(planpath)
    elif args.execute:
        if not all([args.tau_repo,args.credentials,args.private_runs]):raise ValueError('Runtime and private paths required')
        execute(args,json.loads(planpath.read_text()))
    else:p.error('Choose --prepare or --execute')

if __name__=='__main__':main()
