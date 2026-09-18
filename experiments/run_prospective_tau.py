#!/usr/bin/env python3
"""Frozen, monetarily capped prospective telecom shadow-execution pilot.

Requires the pinned tau2 source/runtime. Direct HTTP transports perform exactly
one request per reservation; neither provider SDK retries nor LiteLLM fallback
can bypass the budget. No credentials, headers, or raw text enter public files.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import logging
import os
import platform
import random
import sys
import threading
import time
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODELS=['gpt-5.6-luna','claude-haiku-4-5-20251001']
PRICES={'gpt-5.6-luna':(.20/1e6,1.20/1e6), 'claude-haiku-4-5-20251001':(1./1e6,5./1e6)}
COMMIT='b7ea9074c1cba482b30687fecdb5c8425fd6f619'
CAP=4.0
SEED=20260918


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2));temp.replace(path)
def dump_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


class BudgetStop(RuntimeError):pass
class ProviderFailure(RuntimeError):pass


class Ledger:
    def __init__(self,path,cap=CAP):
        self.path=path;self.cap=cap;self.lock=threading.Lock();self.context={}
        self.state=json.loads(path.read_text()) if path.exists() else {'cap_usd':cap,'calls':[],'created_utc':stamp()}
        if self.state['cap_usd']!=cap:raise ValueError('Budget cap must not change across resumes')
    def used(self):
        return sum(x.get('accounted_cost_usd',x['reservation_usd']) for x in self.state['calls'])
    def reserve(self,model,payload,max_output):
        if model not in PRICES:raise BudgetStop('Unexpected model rejected before network request')
        if max_output not in (192,384):raise BudgetStop('Unexpected output limit rejected')
        # UTF-8 bytes conservatively bound ordinary text tokens; the substantial
        # extra allowance covers provider chat/tool formatting overhead.
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
        tools=len(payload.get('tools') or [])
        prompt_bound=len(serialized)+8192+512*tools
        reservation=prompt_bound*PRICES[model][0]+max_output*PRICES[model][1]
        with self.lock:
            if self.used()+reservation>self.cap:
                raise BudgetStop('Insufficient unreserved budget')
            rec=dict(call_index=len(self.state['calls']),started_utc=stamp(),model=model,
                     context={**self.context,'participant':'user_simulator' if max_output==192 else 'agent'},prompt_token_bound=prompt_bound,max_output_tokens=max_output,
                     reservation_usd=reservation,status='reserved_uncertain',request_sha256=sha(serialized))
            self.state['calls'].append(rec);self.persist();return rec['call_index']
    def settle(self,index,prompt_tokens,output_tokens,response_id,seconds):
        with self.lock:
            rec=self.state['calls'][index]
            actual=prompt_tokens*PRICES[rec['model']][0]+output_tokens*PRICES[rec['model']][1]
            if prompt_tokens>rec['prompt_token_bound'] or output_tokens>rec['max_output_tokens'] or actual>rec['reservation_usd']+1e-12:
                rec.update(status='provider_exceeded_bound',accounted_cost_usd=max(actual,rec['reservation_usd']))
                self.persist();raise BudgetStop('Provider usage exceeded reserved bound')
            rec.update(status='completed',prompt_tokens=int(prompt_tokens),output_tokens=int(output_tokens),
                       accounted_cost_usd=float(actual),response_id=response_id,request_seconds=seconds,ended_utc=stamp())
            self.persist();return actual
    def fail(self,index,status,http_status=None):
        # No release on uncertain failure; a failed attempt is never retried.
        with self.lock:
            self.state['calls'][index].update(status=status,http_status=http_status,ended_utc=stamp())
            self.persist()
    def persist(self):
        self.state['accounted_total_usd']=self.used();self.state['updated_utc']=stamp()
        atomic_json(self.path,self.state)


def anthropic_payload(model,messages,tools,max_output):
    system=[];out=[]
    for m in messages:
        role=m['role'];content=m.get('content') or '';blocks=[]
        if role in ('system','developer'):
            if not isinstance(content,str):raise ValueError('Non-text system content unsupported')
            system.append(content);continue
        if role=='tool':
            role='user';blocks=[{'type':'tool_result','tool_use_id':m['tool_call_id'],'content':content}]
        else:
            if content:
                if not isinstance(content,str):raise ValueError('Non-text content unsupported')
                blocks.append({'type':'text','text':content})
            for tc in m.get('tool_calls') or []:
                function=tc['function'];args=function['arguments']
                blocks.append({'type':'tool_use','id':tc['id'],'name':function['name'],
                               'input':json.loads(args) if isinstance(args,str) else args})
        if not blocks:continue
        if role not in ('assistant','user'):raise ValueError('Unexpected message role')
        if out and out[-1]['role']==role:out[-1]['content'].extend(blocks)
        else:out.append({'role':role,'content':blocks})
    payload={'model':model,'system':'\n\n'.join(system),'messages':out,'max_tokens':max_output,'temperature':0}
    if tools:
        payload['tools']=[{'name':t['function']['name'],'description':t['function'].get('description',''),
                           'input_schema':t['function']['parameters']} for t in tools]
        payload['tool_choice']={'type':'auto'}
    return payload


class DirectCompletion:
    def __init__(self,ledger,credentials):
        import httpx
        from litellm import ModelResponse
        self.ModelResponse=ModelResponse;self.ledger=ledger;self.credentials=credentials
        self.client=httpx.Client(transport=httpx.HTTPTransport(retries=0),timeout=90.,follow_redirects=False)
        self.costs={}
    def __call__(self,model,messages,tools=None,tool_choice=None,**kwargs):
        model=model.removeprefix('openai/').removeprefix('anthropic/')
        if model not in MODELS:raise BudgetStop('Model outside fixed whitelist')
        max_output=int(kwargs.get('max_tokens',kwargs.get('max_completion_tokens',0)))
        if model=='gpt-5.6-luna':
            payload={'model':model,'messages':messages,'max_completion_tokens':max_output,'reasoning_effort':'none'}
            if tools:payload.update(tools=tools,tool_choice='auto')
            endpoint='https://api.openai.com/v1/chat/completions'
            headers={'Authorization':'Bearer '+self.credentials['openai'],'Content-Type':'application/json'}
        else:
            payload=anthropic_payload(model,messages,tools,max_output)
            endpoint='https://api.anthropic.com/v1/messages'
            headers={'x-api-key':self.credentials['anthropic'],'anthropic-version':'2023-06-01','Content-Type':'application/json'}
        index=self.ledger.reserve(model,payload,max_output);start=time.monotonic()
        try:
            response=self.client.post(endpoint,headers=headers,json=payload)
        except Exception:
            self.ledger.fail(index,'transport_failure_uncertain')
            raise ProviderFailure('Transport failure; reservation retained; no retry') from None
        if response.status_code!=200:
            self.ledger.fail(index,'http_failure_reserved',response.status_code)
            raise ProviderFailure(f'Provider HTTP {response.status_code}; no retry') from None
        try:
            d=response.json();usage=d['usage']
            if model=='gpt-5.6-luna':
                prompt=usage['prompt_tokens'];output=usage['completion_tokens']
                message=d['choices'][0]['message'];finish=d['choices'][0]['finish_reason']
            else:
                prompt=usage['input_tokens']+usage.get('cache_read_input_tokens',0)+usage.get('cache_creation_input_tokens',0)
                if usage.get('cache_creation_input_tokens',0):
                    raise BudgetStop('Unexpected paid cache creation rejected')
                output=usage['output_tokens'];text=[];calls=[]
                for block in d['content']:
                    if block['type']=='text':text.append(block['text'])
                    elif block['type']=='tool_use':calls.append({'id':block['id'],'type':'function','function':{'name':block['name'],'arguments':json.dumps(block['input'])}})
                    else:raise ValueError('Unsupported provider block type')
                message={'role':'assistant','content':'\n'.join(text) or None,'tool_calls':calls or None}
                finish={'end_turn':'stop','tool_use':'tool_calls','max_tokens':'length'}.get(d['stop_reason'],'stop')
            cost=self.ledger.settle(index,int(prompt),int(output),d['id'],time.monotonic()-start)
            self.costs[d['id']]=cost
            return self.ModelResponse(id=d['id'],model=model,choices=[{'index':0,'message':message,'finish_reason':finish}],
                                      usage={'prompt_tokens':prompt,'completion_tokens':output,'total_tokens':prompt+output})
        except BudgetStop:raise
        except Exception:
            self.ledger.fail(index,'response_parse_failure_uncertain')
            raise ProviderFailure('Response parse failure; reservation retained; no retry') from None


def import_tau(repo):
    sys.path.insert(0,str(repo/'src'))
    os.environ['TAU2_DATA_DIR']=str(repo/'data')
    from loguru import logger
    logger.remove()
    logging.disable(logging.CRITICAL)
    from tau2.domains.telecom.environment import get_tasks
    from tau2.data_model.simulation import TextRunConfig
    from tau2.runner import run_single_task
    from tau2.evaluator.evaluator import EvaluationType
    import tau2.utils.llm_utils as llm
    return get_tasks,TextRunConfig,run_single_task,EvaluationType,llm


def prepare(repo,plan_path):
    get_tasks,*_=import_tau(repo)
    tasks=get_tasks('base');eligible=[];excluded=[]
    for task in tasks:
        ec=task.evaluation_criteria
        basis=[x.value if hasattr(x,'value') else str(x) for x in (ec.reward_basis or [])] if ec else []
        if not ec or ec.nl_assertions or any('NL' in b.upper() for b in basis) or not (ec.env_assertions or ec.actions):
            excluded.append(task.id)
        else:eligible.append(task)
    chosen=sorted(eligible,key=lambda t:sha(f'{SEED}|{t.id}'.encode()))[:12]
    if len(chosen)!=12:raise RuntimeError('Insufficient eligible tasks before outcomes')
    rng=random.Random(SEED);order=[]
    for task in chosen:
        arms=MODELS.copy();rng.shuffle(arms)
        for arm in arms:
            order.append({'index':len(order),'task_id':task.id,'agent_model':arm,
                          'run_seed':int(sha(f'{SEED}|{task.id}|{arm}'.encode())[:8],16)%(2**31)})
    plan={'frozen_utc':stamp(),'tau_commit':COMMIT,'seed':SEED,'task_ids':[t.id for t in chosen],
          'eligible_tasks':len(eligible),'excluded_task_ids':excluded,'execution_order':order,
          'tasks':[t.model_dump(mode='json') for t in chosen],
          'user_simulator':MODELS[0],'max_steps':40,'max_errors':4,'agent_output_cap':384,'user_output_cap':192,
          'trial_count_per_system_task':1,'budget_cap_usd':CAP,'prices_per_million':{m:[p[0]*1e6,p[1]*1e6] for m,p in PRICES.items()},
          'hierarchy':['recorded_success','agent_inference_cost','assistant_tool_calls'],
          'failure_rule':'both failed => tie','cost_tolerance':.05,'step_tolerance':0,
          'interpretation':'Prospective paired shadow laboratory pilot; no live production users or production A/B randomization',
          'selection':'Lowest SHA256(seed|task_id) among base telecom tasks with deterministic criteria and no NL assertions',
          'script_sha256':sha(Path(__file__).read_bytes()),
          'source_hashes':{str(p.relative_to(repo)):sha(p.read_bytes()) for p in [repo/'data/tau2/domains/telecom/tasks.json',repo/'data/tau2/domains/telecom/split_tasks.json',repo/'uv.lock']}}
    if plan_path.exists():raise RuntimeError('Frozen plan exists; never overwrite after outcomes')
    atomic_json(plan_path,plan)
    print('Frozen task IDs:',','.join(plan['task_ids']),'; eligible',len(eligible),'; paid requests: 0',flush=True)


def sanitize(sim,run):
    d=sim.model_dump(mode='json');messages=[]
    for m in d.get('messages',[]):
        messages.append({'role':m['role'],'turn_idx':m.get('turn_idx'),
                         'text_sha256':sha((m.get('content') or '').encode()) if isinstance(m.get('content'),str) else None,
                         'tool_names':[t.get('name') for t in m.get('tool_calls') or []],
                         'cost_usd':m.get('cost'),'usage':m.get('usage'),'error':m.get('error')})
    return {'task_id':run['task_id'],'agent_model':run['agent_model'],'run_seed':run['run_seed'],
            'simulation_id':d['id'],'termination_reason':d['termination_reason'],'duration_seconds':d['duration'],
            'reward':d['reward_info']['reward'],'reward_basis':d['reward_info'].get('reward_basis'),
            'reward_breakdown':d['reward_info'].get('reward_breakdown'),'messages':messages}


def summarize(rows,ledger,plan):
    results=ROOT/'results';complete=[r for r in rows if r['status']=='completed'];pairs=[]
    for task in plan['task_ids']:
        rr={r['agent_model']:r for r in complete if r['task_id']==task}
        if len(rr)!=2:continue
        a=rr[MODELS[0]];b=rr[MODELS[1]]
        if a['success']!=b['success']:win=1 if a['success']>b['success'] else -1;tier='success'
        elif not a['success']:win=0;tier='tie'
        elif abs(a['agent_cost_usd']-b['agent_cost_usd'])>.05*max(a['agent_cost_usd'],b['agent_cost_usd']):
            win=1 if a['agent_cost_usd']<b['agent_cost_usd'] else -1;tier='cost'
        elif a['assistant_tool_calls']!=b['assistant_tool_calls']:
            win=1 if a['assistant_tool_calls']<b['assistant_tool_calls'] else -1;tier='tool_calls'
        else:win=0;tier='tie'
        pairs.append({'task_id':task,'win_luna_over_haiku':win,'decisive_tier':tier,
                      'success_luna':a['success'],'success_haiku':b['success'],
                      'cost_luna':a['agent_cost_usd'],'cost_haiku':b['agent_cost_usd']})
    dump_csv(results/'prospective_pairs.csv',pairs)
    out={'planned_tasks':12,'planned_runs':24,'finished_run_records':len(rows),'completed_runs':len(complete),
         'complete_pairs':len(pairs),'accounted_total_usd':ledger.used(),
         'reported_usage_cost_usd':sum(x.get('accounted_cost_usd',0) for x in ledger.state['calls'] if x['status']=='completed'),
         'uncertain_reserved_usd':sum(x['reservation_usd'] for x in ledger.state['calls'] if x['status']!='completed'),
         'api_requests':len(ledger.state['calls']),'budget_cap_usd':CAP,'updated_utc':stamp(),
         'models':{},'interpretation':plan['interpretation']}
    for model in MODELS:
        rr=[r for r in complete if r['agent_model']==model]
        out['models'][model]={'completed_runs':len(rr),'successes':sum(r['success'] for r in rr),
                             'mean_agent_cost_usd':sum(r['agent_cost_usd'] for r in rr)/len(rr) if rr else None,
                             'mean_tool_calls':sum(r['assistant_tool_calls'] for r in rr)/len(rr) if rr else None}
    if pairs:
        n=len(pairs);w=sum(r['win_luna_over_haiku']==1 for r in pairs);l=sum(r['win_luna_over_haiku']==-1 for r in pairs)
        out.update(wins=w,losses=l,ties=n-w-l,net_win=(w-l)/n,
                   success_difference=sum(r['success_luna']-r['success_haiku'] for r in pairs)/n)
    atomic_json(results/'prospective_summary.json',out)
    text=("\\paragraph{Prospective laboratory pilot.} "
          f"We froze {plan['task_ids'].__len__()} telecom tasks and one run per system before collecting new model outputs. "
          f"The pilot completed {len(complete)} of 24 planned runs and {len(pairs)} paired tasks, "
          f"using {len(ledger.state['calls'])} provider requests with \\${ledger.used():.4f} accounted expenditure "
          f"under a \\${CAP:.2f} cap. "
          "The systems were GPT-5.6-Luna and Claude Haiku 4.5, with the same Luna user simulator, randomized execution order, "
          "40-step truncation and deterministic task verification. This is paired shadow execution in a laboratory, not a live-production A/B experiment. ")
    if pairs:
        text+=f"Among {len(pairs)} complete pairs, Luna recorded {out['wins']} wins, {out['losses']} losses and {out['ties']} ties (net win {out['net_win']:.3f}). "
    text+='The small prespecified pilot is descriptive; it does not establish deployment superiority or real-user generalization.\n'
    (ROOT/'experiments/prospective_results.tex').write_text(text)


def execute(args,plan):
    if plan['tau_commit']!=COMMIT or plan['budget_cap_usd']!=CAP:raise ValueError('Frozen plan mismatch')
    get_tasks,Config,run_single,Eval,llm=import_tau(args.tau_repo)
    from tau2.data_model.tasks import Task
    tasks={d['id']:Task.model_validate(d) for d in plan['tasks']}
    credentials=json.loads(args.credentials.read_text())
    if set(credentials)!={'openai','anthropic'}:raise ValueError('Unexpected credential schema')
    results=ROOT/'results';results.mkdir(exist_ok=True)
    ledger=Ledger(results/'prospective_spend_ledger.json')
    direct=DirectCompletion(ledger,credentials)
    llm.completion=direct;llm.get_response_cost=lambda r:direct.costs[r.id]
    private=args.private_runs;private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
    atomic_json(results/'prospective_run_manifest.json',{'started_utc':stamp(),'script_sha256':sha(Path(__file__).read_bytes()),'frozen_plan_sha256':sha((ROOT/'experiments/prospective_protocol.json').read_bytes()),'python':platform.python_version(),'tau_commit':COMMIT,'transport':'httpx direct, no retry, no redirects','pre_call_adapter_fixes':['safe hashed filenames for long task identifiers','fail closed after any infrastructure exception'],'credentials_included':False,'provider_random_seeds':'No provider seed argument; run seeds govern harness only','usage_cost_interpretation':'Conservative list-price cost; prompt cache discounts ignored','source_hashes':{str(p.relative_to(args.tau_repo)):sha(p.read_bytes()) for p in sorted((args.tau_repo/'data/tau2/user_simulator').glob('*.md'))}})
    rows_path=results/'prospective_runs.json'
    rows=json.loads(rows_path.read_text()) if rows_path.exists() else []
    done={r['execution_index'] for r in rows}
    stop_all=False
    for run in plan['execution_order']:
        if run['index'] in done:continue
        # Crash with pending request => stop rather than duplicate a possibly charged execution.
        if any(c['status']=='reserved_uncertain' for c in ledger.state['calls']):
            stop_all=True
        rec={'execution_index':run['index'],'task_id':run['task_id'],'agent_model':run['agent_model'],
             'run_seed':run['run_seed'],'status':'not_run_budget_or_uncertainty','success':'',
             'agent_cost_usd':'','user_cost_usd':'','assistant_tool_calls':'','duration_seconds':'',
             'termination_reason':'','error_type':''}
        if stop_all:
            rows.append(rec);continue
        ledger.context={'task_id':run['task_id'],'agent_model':run['agent_model'],'execution_index':run['index']}
        config=Config(domain='telecom',agent='llm_agent',user='user_simulator',llm_agent=run['agent_model'],
                      llm_user=MODELS[0],llm_args_agent={'max_tokens':384,'temperature':0,'num_retries':0},
                      llm_args_user={'max_tokens':192,'temperature':0,'num_retries':0},max_steps=40,max_errors=4,
                      max_concurrency=1,num_trials=1,max_retries=0,auto_review=False,verbose_logs=False,log_level='ERROR')
        try:
            # Suppress upstream content logging, including exception dumps. Public
            # output consists only of the sanitized summary below.
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                sim=run_single(config,tasks[run['task_id']],seed=run['run_seed'],evaluation_type=Eval.ALL,
                               verbose_logs=False,auto_review=False)
            d=sim.model_dump(mode='json')
            private_file=private/f"{run['index']:02d}_{sha(run['task_id'].encode())[:12]}.json"
            atomic_json(private_file,d);os.chmod(private_file,0o600)
            safe=sanitize(sim,run)
            atomic_json(results/'prospective_sanitized_traces'/f"{run['index']:02d}_{sha(run['task_id'].encode())[:12]}.json",safe)
            calls=sum(len(m.get('tool_calls') or []) for m in d['messages'] if m['role']=='assistant')
            rec.update(status='completed',success=float(d['reward_info']['reward']),agent_cost_usd=d['agent_cost'],
                       user_cost_usd=d['user_cost'],assistant_tool_calls=calls,duration_seconds=d['duration'],
                       termination_reason=d['termination_reason'])
        except BudgetStop:
            rec.update(status='budget_stopped',error_type='BudgetStop');stop_all=True
        except Exception as e:
            rec.update(status='infrastructure_failure',error_type=type(e).__name__)
            stop_all=True
            # No repeated request or repeated task after any infrastructure error.
        rows.append(rec);atomic_json(rows_path,rows);dump_csv(results/'prospective_runs.csv',rows)
        summarize(rows,ledger,plan)
        print(f"Run {run['index']+1}/24 | task {run['task_id']} | {run['agent_model']} | {rec['status']} | accounted ${ledger.used():.4f}",flush=True)
    atomic_json(rows_path,rows);dump_csv(results/'prospective_runs.csv',rows);summarize(rows,ledger,plan)
    print(f'Pilot closed. Accounted total ${ledger.used():.4f} / ${CAP:.2f}.',flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--tau-repo',type=Path,required=True)
    p.add_argument('--prepare',action='store_true')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--credentials',type=Path)
    p.add_argument('--private-runs',type=Path)
    args=p.parse_args();plan_path=ROOT/'experiments/prospective_protocol.json'
    if args.prepare:
        if args.execute:raise ValueError('Freeze and execute in separate invocations')
        prepare(args.tau_repo.resolve(),plan_path)
    elif args.execute:
        if not args.credentials or not args.private_runs:raise ValueError('Private credential and run paths required')
        execute(args,json.loads(plan_path.read_text()))
    else:p.error('Choose --prepare or --execute')

if __name__=='__main__':main()
