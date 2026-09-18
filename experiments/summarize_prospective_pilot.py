#!/usr/bin/env python3
"""Describe the complete planned cohort, including unobserved outcomes.

The finite-cohort missing-outcome bounds are deterministic support bounds,
not sampling confidence intervals. No new paid requests are made.
"""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    results=ROOT/'results'
    plan=json.loads((ROOT/'experiments/prospective_v2_protocol.json').read_text())
    rows=json.loads((results/'prospective_v2_runs.json').read_text())
    reported=json.loads((results/'prospective_v2_summary.json').read_text())
    ledger=json.loads((results/'prospective_v2_spend_ledger.json').read_text())
    diagnostics=json.loads((results/'provider_diagnostics.json').read_text())
    diagnostic_cost=sum(d['usage_cost_usd'] if d['status']=='completed' else d['reservation_usd'] for d in diagnostics)
    original=(results/'prospective_spend_ledger.json').read_bytes()
    assert hashlib.sha256(original).hexdigest()==plan['source_v1_ledger_sha256']
    assert hashlib.sha256((ROOT/'experiments/prospective_protocol.json').read_bytes()).hexdigest()==plan['source_v1_protocol_sha256']
    assert len(rows)==24,'Wait for pilot closure before final cohort analysis'
    assert len({r['execution_index'] for r in rows})==24
    assert ledger['accounted_total_usd']<=4.
    assert not any(c['status']=='reserved_uncertain' for c in ledger['calls']),'Wait for in-flight requests'
    pairs=list(csv.DictReader((results/'prospective_v2_pairs.csv').open())) if (results/'prospective_v2_pairs.csv').exists() else []
    n=len(plan['task_ids']);m=len(pairs);unknown=n-m
    score=sum(int(r['win_verification_over_standard']) for r in pairs)
    success=sum(float(r['success_verification'])-float(r['success_standard']) for r in pairs)
    by_variant={}
    for variant in plan['variants']:
        rr=[r for r in rows if r['variant']==variant]
        done=[r for r in rr if r['status']=='completed']
        passed=sum(r['success']==1 for r in done)
        by_variant[variant]={'planned_runs':len(rr),'completed_runs':len(done),'successes':passed,
                             'failures':len(done)-passed,'unobserved_runs':len(rr)-len(done),
                             'step_cap_terminations':sum(r['termination_reason']=='max_steps' for r in done),
                             'infrastructure_failures':sum(r['status']=='infrastructure_failure' for r in rr),
                             'budget_stopped_runs':sum(r['status']=='budget_stopped' for r in rr)}
    out={'planned_tasks':n,'planned_runs':24,'completed_pairs':m,'incomplete_pairs':unknown,
         'observed_pair_score_sum':score,'observed_success_difference_sum':success,
         'planned_cohort_net_preference_bounds':[(score-unknown)/n,(score+unknown)/n],
         'planned_cohort_success_difference_bounds':[(success-unknown)/n,(success+unknown)/n],
         'bound_interpretation':'Deterministic finite-cohort missing-outcome bounds over all 12 planned tasks; NOT sampling confidence intervals. Each unknown pair conservatively contributes anywhere in [-1,1]; known one-arm information is ignored.',
         'complete_pair_net_preference_descriptive_only':score/m if m else None,
         'variants':by_variant,'combined_v1_v2_accounted_usd':ledger['accounted_total_usd'],
         'v1_retained_reservation_usd':ledger['v1_accounted_carry_usd'],
         'v2_usage_priced_upper_cost_usd':reported['v2_usage_priced_upper_cost_usd'],
         'v2_uncertain_reservations_usd':reported['v2_uncertain_reserved_usd'],
         'v2_requests':len(ledger['calls']),
         'separate_provider_diagnostics_accounted_usd':diagnostic_cost,
         'project_total_accounted_usd':ledger['accounted_total_usd']+diagnostic_cost,
         'cost_interpretation':'Conservative list-price usage accounting plus held reservations, not a verified provider invoice. Provider diagnostics are outside the pilot four-dollar allocation.',
         'qa':{'original_v1_ledger_unchanged':True,'all_24_planned_run_records_accounted':True,
               'combined_budget_cap_respected':True,
               'all_completed_token_usage_within_reserved_bounds':all(c.get('prompt_tokens',0)<=c['prompt_token_bound'] and c.get('output_tokens',0)<=c['max_output_tokens'] for c in ledger['calls'])}}
    (results/'prospective_final_cohort_summary.json').write_text(json.dumps(out,indent=2))
    lo,hi=out['planned_cohort_net_preference_bounds'];sl,sh=out['planned_cohort_success_difference_bounds']
    complete=sum(v['completed_runs'] for v in by_variant.values());caps=sum(v['step_cap_terminations'] for v in by_variant.values())
    tex=("\\paragraph{Prospective workflow feasibility pilot.} "
         "We prospectively fixed 12 telecom tasks and one run per task for each of two Haiku workflows (standard versus a verification instruction), "
         "with a common Haiku user simulator, randomized workflow order, a 40-step cap, and deterministic outcome verification. "
         f"The fixed monetary stopping rule yielded {complete}/24 completed runs and {m}/12 complete pairs; {caps} completed runs reached the step cap. "
         f"Standard and verification completed {by_variant['standard']['completed_runs']} and {by_variant['verification']['completed_runs']} runs, "
         f"with {by_variant['standard']['successes']} and {by_variant['verification']['successes']} successes, respectively. "
         f"Across all 12 planned tasks, the conservative missing-outcome bounds are [{lo:.3f}, {hi:.3f}] for net preference "
         f"and [{sl:.3f}, {sh:.3f}] for success difference (verification minus standard). "
         "These are deterministic finite-cohort bounds, not sampling confidence intervals, and conservatively ignore partial one-arm information. "
         f"The combined ledger accounts for \\${ledger['accounted_total_usd']:.4f} under a \\${4:.2f} cap, including "
         f"the retained \\${ledger['v1_accounted_carry_usd']:.4f} reservation from a quota-blocked initial model comparison that produced no completed trajectory. "
         "This small laboratory pilot establishes execution and measurement feasibility; limited success, truncation and incomplete pairs preclude a workflow-superiority conclusion. "
         "It does not involve live production users or production A/B randomization.\n")
    (ROOT/'experiments/prospective_final_results.tex').write_text(tex)
    plt.rcParams.update({'font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.2))
    bottom=[0,0]
    for key,label,color in [('successes','Success','#2E6D9C'),('failures','Completed failure','#B56A44'),('unobserved_runs','Unobserved','#CECECE')]:
        values=[by_variant[v][key] for v in plan['variants']]
        axes[0].bar(['Standard','Verification'],values,bottom=bottom,color=color,label=label)
        bottom=[a+b for a,b in zip(bottom,values)]
    axes[0].set_ylim(0,12.7);axes[0].set_ylabel('Runs out of 12 planned per workflow');axes[0].legend(fontsize=7,loc='upper left')
    centers=[(lo+hi)/2,(sl+sh)/2];lower=[lo,sl];upper=[hi,sh]
    axes[1].errorbar(centers,[1,0],xerr=[[a-b for a,b in zip(centers,lower)],[a-b for a,b in zip(upper,centers)]],fmt='none',capsize=4,color='#2E6D9C')
    axes[1].axvline(0,color='.5',lw=1);axes[1].set_yticks([1,0],['Net preference','Success difference']);axes[1].set_ylim(-.6,1.6)
    axes[1].set_xlabel('Verification minus standard');axes[1].set_title('All 12-task missing-outcome bounds',fontsize=9)
    fig.suptitle('Prospective pilot: full planned cohort and finite-cohort bounds',fontsize=10)
    fig.tight_layout();plots=ROOT/'plots';plots.mkdir(exist_ok=True)
    for suffix in ['pdf','png']:fig.savefig(plots/f'prospective_v2_cohort.{suffix}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
