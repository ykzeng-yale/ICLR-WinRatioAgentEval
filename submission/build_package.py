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
private=re.compile(rb'(?:/Users/|yukang\.zeng|ykzeng-yale|Yukang Zeng|sk-(?:proj-|ant-api\d\d-)?[A-Za-z0-9_-]{20,})',re.I)
for name in sorted(files):
 p=ROOT/name
 if p.suffix.lower() not in ['.pdf','.png'] and private.search(p.read_bytes()):
  raise ValueError('Nonanonymous or credential-like content in '+name)
 # Raw binary figures are separately inspected for visual anonymity and PDF metadata.
record=[{'path':name,'bytes':(ROOT/name).stat().st_size,'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name in sorted(files)]
manifest={'status':'Prepared review artifacts; author submission and attestations remain separate',
          'files':record,'commercial_api_execution_in_reproduce_entrypoint':False,
          'excluded':'Credentials, author metadata, private traces, original raw historical data, git history, contributed unaudited projection/width methods, development coordination files'}
(OUT/'package_manifest.json').write_text(json.dumps(manifest,indent=2))
readme='''# Anonymous supplementary materials\n\nStart with REPRODUCIBILITY.md. Run `python reproduce.py` to check the supplied baseline, or use its explicit simulation/full options to regenerate numerical studies. No commercial API calls occur through that entrypoint. Optional prospective runners are supplied for transparency and require separately provided credentials and expenditure authorization.\n\nThe paper is paper/manuscript.pdf; complete LaTeX sources, numerical results, protocols, proof appendices and provenance are included. The code archive does not assert human scientific signoff or production deployment validation.\n'''
with zipfile.ZipFile(OUT/'anonymous_code.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in sorted(files):z.write(ROOT/name,name)
 z.writestr('README.md',readme);z.writestr('package_manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(OUT/'latex_source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in sorted(files):
  if name.startswith('paper/') or name.endswith(('.pdf','.png')) or name.startswith('third_party/'):
   z.write(ROOT/name,name)
shutil.copy2(ROOT/'paper/manuscript.pdf',OUT/'paper.pdf')
print('Prepared allowlisted anonymous archives:',len(files),'files;', (OUT/'anonymous_code.zip').stat().st_size,'compressed bytes')
