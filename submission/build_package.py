#!/usr/bin/env python3
"""Build explicitly allowlisted anonymous review artifacts; never publishes."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'
required=['requirements.txt','reproduce.py','REPRODUCIBILITY.md','src/winstats.py','src/test_winstats.py',
 'experiments/run_simulations.py','experiments/run_stress_tests.py','experiments/run_async_experiment.py',
 'experiments/reanalyze_public.py','experiments/build_paper_results.py','experiments/build_async_paper_results.py','experiments/build_ablation_paper_results.py','experiments/build_dm_paper_results.py',
 'experiments/protocol.md','evidence/async_experiment_protocol.md',
 'experiments/run_trace_certificates.py','experiments/build_trace_paper_results.py','evidence/trace_certificate_protocol.md',
 'experiments/verify_trace_certificates_independent.py',
 'paper/trace_certificate_results.tex','paper/trace_certificate_appendix.tex',
 'paper/pairing_efficiency.tex',
 'experiments/build_sequential_extensions.py','experiments/run_online_methods.py',
 'paper/sequential_extension_results.tex','paper/ustat_extension_appendix.tex','paper/drift_extension_appendix.tex',
 'results/sequential_extensions_integrity.json','results/sequential_extension_paper_manifest.json','results/online_methods_results.csv',
 'results/source_baselines/reproducibility_manifest_pre_round10.json',
 'paper/main.tex','paper/theory.tex','paper/asynchronous.tex','paper/results_main.tex','paper/experiments_appendix.tex',
 'paper/public_results.tex','paper/public_appendix.tex','paper/async_results.tex','paper/async_appendix.tex',
 'paper/references.bib','paper/iclr2027_conference.sty','paper/iclr2027_conference.bst','paper/fancyhdr.sty','paper/natbib.sty',
 'paper/manuscript.pdf','third_party/NOTICES.md','third_party/tau2_LICENSE.txt',
 'results/simulation_results.csv','results/simulation_manifest.json','results/stress_results.csv','results/stress_manifest.json',
 'results/reproducibility_manifest.json']
optional=['src/ternary_dm.py','experiments/reproduce_dm_baseline.py','evidence/dm_baseline.md',
 'experiments/run_decision_ablations.py','evidence/decision_ablation_protocol.md','paper/decision_ablations.tex','paper/decision_ablation_appendix.tex','paper/dm_results.tex','paper/dm_appendix.tex',
 'paper/prospective_results.tex','paper/prospective_appendix.tex',
 'experiments/run_prospective_tau.py','experiments/run_prospective_tau_v2.py','experiments/prospective_protocol.json',
 'experiments/prospective_protocol.md','experiments/prospective_v2_protocol.json','experiments/prospective_v2_protocol.md',
 'experiments/prospective_runtime.json','experiments/summarize_prospective_pilot.py']
files=set(required)
for name in required:
 if not (ROOT/name).is_file():raise FileNotFoundError(name)
for name in optional:
 if (ROOT/name).is_file():files.add(name)
for pattern in ['experiments/prospective*.tex','results/async_*','results/public_*.csv','results/public_manifest.json','results/public_guardrail_reversal.*',
 'results/simulation_operating.*','plots/public_*.pdf','plots/public_*.png','results/dm_baseline_*','results/trace_certificate_*',
 'results/decision_ablation_*','results/prospective_*.csv','results/prospective_*.json',
 'results/prospective_v2_sanitized_traces/*.json','plots/prospective_v2_cohort.*','results/provider_diagnostics.json','results/project_cost_summary.json']:
 for p in ROOT.glob(pattern):
  if p.is_file():files.add(str(p.relative_to(ROOT)))
for directory in ['experiments/ustat_reference','experiments/drift_panel','results/ustat_reference','results/drift_panel']:
 for p in (ROOT/directory).rglob('*'):
  if p.is_file() and p.suffix in ['.py','.md','.json','.csv','.log','.png','.pdf'] and '__pycache__' not in p.parts:
   files.add(str(p.relative_to(ROOT)))
payload={name:(ROOT/name).read_bytes() for name in sorted(files)}
transformed=[]
# Anonymize copies only. Original contributed manifests remain immutable on disk.
for name,data in list(payload.items()):
 if name.startswith('results/ustat_reference/') and name.endswith('manifest.json'):
  record=json.loads(data)
  args=record.get('arguments',{})
  if Path(str(args.get('out',''))).is_absolute():
   args['out']='results/ustat_reference'
   payload[name]=(json.dumps(record,indent=2)+'\n').encode()
   transformed.append({'path':name,'original_sha256':hashlib.sha256(data).hexdigest(),
                       'release_sha256':hashlib.sha256(payload[name]).hexdigest(),
                       'change':'Replaced identifying absolute output directory with repository-relative path; numerical records unchanged.'})
integrity_name='results/sequential_extensions_integrity.json'
integrity=json.loads(payload[integrity_name])
for record in integrity['outputs']:
 if record['path'] in payload:
  record['sha256']=hashlib.sha256(payload[record['path']]).hexdigest()
payload[integrity_name]=(json.dumps(integrity,indent=2)+'\n').encode()
payload['results/anonymous_provenance_map.json']=(json.dumps({'transformations':transformed},indent=2)+'\n').encode()
files=set(payload)
private=re.compile(rb'(?:/Users/|yukang|ykzeng|ICLR-WinRatioAgentEval|sk-(?:proj-|ant-api\d\d-)?[A-Za-z0-9_-]{20,})',re.I)
for name in sorted(files):
 p=ROOT/name
 if p.suffix.lower() not in ['.pdf','.png'] and private.search(payload[name]):
  raise ValueError('Nonanonymous or credential-like content in '+name)
 # Raw binary figures are separately inspected for visual anonymity and PDF metadata.
record=[{'path':name,'bytes':len(payload[name]),'sha256':hashlib.sha256(payload[name]).hexdigest()} for name in sorted(files)]
manifest={'status':'Prepared review artifacts; author submission and attestations remain separate',
          'files':record,'commercial_api_execution_in_reproduce_entrypoint':False,
          'excluded':'Credentials, author metadata, private traces, original raw historical data, git history, contributed unaudited projection/width methods, development coordination files'}
(OUT/'package_manifest.json').write_text(json.dumps(manifest,indent=2))
readme='''# Anonymous supplementary materials\n\nStart with REPRODUCIBILITY.md. Run `python reproduce.py` to check retained results, use its explicit simulation/full options for original studies, or add `--extensions` for the accepted CPU-only all-pairs and drift studies. No commercial API calls occur through this entrypoint. Historical commercial collection scripts are retained for provenance only and are not authorized for execution. New experimental inference is restricted to open-weight/open-source systems.\n\nThe paper is paper/manuscript.pdf; complete LaTeX sources, numerical results, protocols, proof appendices and provenance are included. Anonymous manifest copies and their source hashes are documented in results/anonymous_provenance_map.json. The code archive does not assert human scientific signoff or production deployment validation.\n'''
with zipfile.ZipFile(OUT/'anonymous_code.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in sorted(files):z.writestr(name,payload[name])
 z.writestr('README.md',readme);z.writestr('package_manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(OUT/'latex_source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in sorted(files):
  if name.startswith('paper/') or name.endswith(('.pdf','.png')) or name.startswith('third_party/'):
   z.writestr(name,payload[name])
shutil.copy2(ROOT/'paper/manuscript.pdf',OUT/'paper.pdf')
print('Prepared allowlisted anonymous archives:',len(files),'files;', (OUT/'anonymous_code.zip').stat().st_size,'compressed bytes')
