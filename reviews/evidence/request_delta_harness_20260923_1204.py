"""Independent six-case actual-main reproduction fixture, 2026-09-23 12:04.

Run from any directory with Python 3. Uses only standard-library mocking and
committed saved smoke fixtures. All process creation, HTTP, signals, clocks and
thread scheduling are mocked; launch artifact hashing is stubbed. Real reader,
capture and finalization operate only on synthetic closed temporary files.
No native server, model, actual HTTP, build or full suite is executed.

Requires --output PATH and creates that fresh output exclusively; an existing
output is refused before cases run. Other writes are temporary files only. Exact source hashes fail closed on drift; adopting for owner repairs
requires intentionally updating those pins. This is independent review evidence,
not a scientific experiment or live-smoke authorization.
"""
import os
from pathlib import Path
import hashlib
import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path, help="Fresh JSON output; existing paths are refused")
arguments = parser.parse_args()
output_path = arguments.output.resolve()
if output_path.exists():
    parser.error("output already exists; refusing to overwrite: " + str(output_path))
REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)
SOURCE_SHA256 = {'experiments/live_ab_serving/run_smoke.py': 'b15cb34cdefbdd931b3960b303b993f968182deb773baa243e3ffaf5349c5b40', 'experiments/live_ab/lab_lifecycle.py': '96748320661b0cff2deec7550022f30e1a0615e8215df4b9e8e6218cdc992398', 'experiments/live_ab/lab_common.py': 'aa32c13a0f3c6895f6a4d7936cc2b883930e5f4db9491a7f3aa444c8e1c3bb1c', 'experiments/live_ab/lab_data.py': '7291fea66a25ca33c12c84c9a46d0f8246e35e0d8cc4d83aff2496a10c2b9977'}
for source_path, expected_sha256 in SOURCE_SHA256.items():
    actual_sha256 = hashlib.sha256((REPO / source_path).read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise SystemExit("Source drift: " + source_path + "; refusing to reuse pinned review")
import contextlib, copy, glob, hashlib, io, json, sys, tempfile, types
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path[:0]=['experiments/live_ab','experiments/live_ab_serving']
import run_smoke as rs, lab_lifecycle as ll
saved=json.loads(Path('results/live_ab/SMOKE_RECEIPT_smoke_4167e395ccfd.json').read_text())
manifest=json.loads(Path('results/live_ab/SMOKE_LAUNCH_MANIFEST_smoke_4167e395ccfd.json').read_text())
real_read=Path.read_text; real_write=rs.lab_common.write_json_atomic; real_deadline=rs.Deadline
prov={k:saved['observation'][k] for k in ('host_id','boot_id','host_source','boot_source')}
all_cases={}
for case in ('barrier_failure_before_cutoff','no_worker_records','one_worker_record','negative_usage','known_zero','popen_failure'):
 with tempfile.TemporaryDirectory(prefix='request_review_1116_') as td:
  root=Path(td); result=root/'results';result.mkdir(); log=root/'lifecycle.jsonl';mp=root/'manifest.json';clock=[0.];events=[];writes=[];bodies=[]
  m=copy.deepcopy(manifest);m['patch_sha256']=hashlib.sha256(Path('experiments/live_ab_serving/live_ab_slot_lifecycle.patch').read_bytes()).hexdigest();mp.write_text(json.dumps(m))
  lines=[json.loads(s) for s in saved['raw_log_lines']];lines[-1]['sidecar_failures']=0;log.write_text(''.join(json.dumps(s)+'\n' for s in lines))
  class Proc:
   pid=987654;returncode=None;stdout=io.BytesIO(b'synthetic diagnostic\n')
   def poll(self): return self.returncode
   def wait(self,timeout):self.returncode=0;return 0
  proc=Proc()
  class Thread:
   def __init__(self,target,args=(),kwargs=None,daemon=None,name=None):self.target=target;self.args=args;self.kwargs=kwargs or {};self.name=name;self.alive=False
   def start(self):
    self.alive=True
    if self.name != 'live_ab_smoke_drain' and (case == 'no_worker_records' or (case == 'one_worker_record' and self.args == (1,))):return
    self.target(*self.args,**self.kwargs);self.alive=False
   def join(self,timeout=None): pass
   def is_alive(self):return self.alive
  class Barrier:
   def __init__(self,n):pass
   def wait(self,timeout=None):
    events.append({'event':'barrier','clock':clock[0],'timeout':timeout,'durable_write_count':len(writes)})
    if case=='barrier_failure_before_cutoff':raise RuntimeError('synthetic barrier failure')
  def read(p,*a,**kw):
   if str(p)=='/tmp/lab_smoke_manifest.txt': return str(mp)+'\n'+str(log)+'\n'+m['run_token']+'\n'
   return real_read(p,*a,**kw)
  def write(p,o):writes.append(copy.deepcopy(o));return real_write(p,o)
  def verify(*a,**kw):
   if case=='cutoff_after_health':clock[0]=509.
   return {'verified':True,'problems':[],'mocked':True}
  def get(*a,**kw):
   if case=='cutoff_after_health':clock[0]=511.
   return types.SimpleNamespace(status_code=200)
  marker='END_BYTES_NOT_IN_PREVIEW_1116'
  def post(url,**kw):
   events.append({'event':'HTTP_POST','clock':clock[0],'timeout':kw['timeout'],'durable_write_count':len(writes),'results_files_before_dispatch':[p.name for p in result.iterdir()]})
   if case=='submitted_then_timeout':raise TimeoutError('mock transport invoked, response unavailable')
   d={'usage':{'completion_tokens':(-1 if case=='negative_usage' else (0 if case=='known_zero' else 1024))},'choices':[{'finish_reason':'length','message':{'content':'ok'}}]}
   if case=='missing_usage':d.pop('usage')
   if case=='long_success':d['choices'][0]['message']['content']='X'*9000+marker
   raw=(b'not-json:'+b'X'*9000+marker.encode()) if case=='long_unparsable' else json.dumps(d,sort_keys=True).encode()
   bodies.append(raw)
   def decode():
    if case=='long_unparsable':raise ValueError('synthetic JSON decode failure')
    return d
   return types.SimpleNamespace(status_code=200,content=raw,json=decode)
  def popen(*a,**kw):
   if case=='popen_failure':raise OSError('synthetic child could not start')
   return proc
  requests=types.ModuleType('requests');requests.get=get;requests.post=post
  patches=[patch.object(rs.lab_common,'RESULTS_ROOT',result),patch.object(rs.lab_common,'write_json_atomic',write),patch.object(rs,'Deadline',lambda b:real_deadline(b,now=lambda:clock[0])),patch.object(rs.time,'monotonic',lambda:clock[0]),patch.object(rs.time,'sleep',lambda v:clock.__setitem__(0,clock[0]+v)),patch.object(rs,'_now',lambda:'SYNTHETIC'),patch.object(rs,'verify_launch_artifacts',verify),patch.object(glob,'glob',lambda *a,**kw:['/synthetic/model.gguf']),patch.object(Path,'read_text',read),patch.object(rs.subprocess,'Popen',popen),patch.object(rs.threading,'Thread',Thread),patch.object(rs.threading,'Barrier',Barrier),patch.object(rs.os,'getpgid',lambda pid:pid),patch.object(rs.os,'killpg',lambda *a:None),patch.object(ll.lab_data,'clock_provenance',lambda:prov),patch.dict(sys.modules,{'requests':requests})]
  exc=None;ret=None
  with contextlib.ExitStack() as st,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   for p in patches:st.enter_context(p)
   try:ret=rs.main()
   except Exception as e:exc=type(e).__name__+': '+str(e)
  receipts=list(result.glob('SMOKE_RECEIPT*'));out=json.loads(receipts[0].read_text()) if receipts else {}
  selected={k:out.get(k) for k in ('child_started','loaded_a_model','popen_error','requests_expected','requests_with_records','requests_unaccounted_for','submitted_requests','planned_requests','generated_tokens_total','generated_tokens_known_sum','requests_with_known_usage','requests_with_unknown_usage','token_cap_respected','supervisor_problems','deadline')}
  reqs=[]
  for r in out.get('requests',[]):
   rr={k:v for k,v in r.items() if k!='raw_response'}
   raw=r.get('raw_response');rr['raw_response']=None if raw is None else {k:v for k,v in raw.items() if k!='preview'}
   if raw:rr['preview_length']=len(raw['preview'])
   reqs.append(rr)
  selected['requests']=reqs
  files=[p for p in root.rglob('*') if p.is_file()]
  checks={'input_response_bytes':[len(b) for b in bodies],'input_response_sha256':[hashlib.sha256(b).hexdigest() for b in bodies],'tail_marker_persisted_anywhere':any(marker.encode() in p.read_bytes() for p in files),'persisted_files':[str(p.relative_to(root)) for p in files],'intent_payload_hashes_match':[hashlib.sha256(json.dumps(p['payload'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==p['payload_sha256'] for p in out.get('planned_request_intent',[])]}
  all_cases[case]={'returncode':ret,'exception':exc,'receipt_count':len(receipts),'write_calls':len(writes),'events':events,'receipt':selected,'persistence_checks':checks}
report={'head':'9f2658b849d4f3d2fd2ce8fc9680b4e6b85454c9','source':'d208bfa990edac64bfb7acdc3235d02bb5553855','base':'1bd5cd0bd11ffac5ab367f8b1e4f30b5c4c40e9d','scope':'Six actual-main invocations with process, HTTP, signals, clocks and scheduling mocked. Real reader, capture helper, finalizer and filesystem on closed synthetic fixtures; launcher verification stubbed as separate root scope. No model, native executable, HTTP, build or full suite.','cases':all_cases,'readiness':{'full_project_percent':75,'delta_points':0,'bounded_v1_percent':90,'remaining_points':25}}
report['source_sha256'] = SOURCE_SHA256
report['harness_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
report['findings'] = {'accepted': ['Broken barrier returns without POST and main refuses', 'Main retains expected denominator two with zero or one worker records', 'Aggregate rejects negative usage and preserves observed zero', 'Popen failure leaves loaded_a_model unknown and child_started false'], 'remaining_delta_issue': 'Negative completion_tokens still sets per-request usage_known=true at lines 663-665, although aggregate correctly refuses it.'}
with output_path.open('x', encoding='utf-8') as output_file:
    output_file.write(json.dumps(report,indent=2)+'\n')
for k,v in all_cases.items():print(k,json.dumps({'return':v['returncode'],'exception':v['exception'],'receipts':v['receipt_count'],'writes':v['write_calls'],'posts':sum(x['event']=='HTTP_POST' for x in v['events']),'submitted':v['receipt']['submitted_requests'],'total':v['receipt']['generated_tokens_total'],'cap':v['receipt']['token_cap_respected'],'problems':v['receipt']['supervisor_problems'],'expected':v['receipt']['requests_expected'],'records':v['receipt']['requests_with_records'],'unaccounted':v['receipt']['requests_unaccounted_for'],'loaded':v['receipt']['loaded_a_model']}))
