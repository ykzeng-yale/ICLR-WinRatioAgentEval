#!/usr/bin/env python3
"""Plot accepted saved counts; no simulation or model calls."""
from pathlib import Path
import json, math
from statistics import NormalDist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
source = HERE/'COMBINED_CURVE.json'
if not source.exists():
 source = ROOT/'results/live_ab_validation_v2/powercurve_fine_20260921/COMBINED_CURVE.json'
rows = json.loads(source.read_text())
z=NormalDist().inv_cdf(.975)
fig, axs=plt.subplots(1,2,figsize=(7.2,2.9),sharey=True,layout='constrained')
for ax,panel,title in zip(axs,['coarse(ns3)','fine(ns4)'],['Coarse panel (8,000 per cell)','Exploratory fine panel (4,000 per cell)']):
 for delay,color,marker,label in [('non-informative','#2166ac','o','N: non-informative'),('informative','#b35806','s','A: informative')]:
  rs=sorted([r for r in rows if r['panel']==panel and r['delay']==delay],key=lambda r:r['mu_h'])
  xs=[];ys=[];lo=[];hi=[]
  for r in rs:
   n=r['n'];p=r['deploy']/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
   assert max(abs(a-b) for a,b in zip([c-h,c+h],r['wilson95']))<1e-12
   xs.append(r['mu_h']);ys.append(p);lo.append(p-(c-h));hi.append((c+h)-p)
  ax.errorbar(xs,ys,yerr=[lo,hi],fmt=marker,color=color,capsize=3,markersize=4,label=label,linestyle='none')
 ax.set_title(title,fontsize=9);ax.set_xlabel('Hierarchy mean',fontsize=9);ax.axhline(.5,color='.7',ls=':',lw=.8);ax.set_ylim(-.025,1.025);ax.tick_params(labelsize=8);ax.spines[['top','right']].set_visible(False)
axs[0].set_ylabel('ADAPTER deployment proportion',fontsize=9);axs[0].legend(fontsize=7,loc='lower right',frameon=False)
fig.savefig(HERE/'power_diagnostics.pdf',metadata={'Title':'Exploratory synthetic deployment diagnostics','Author':'Yukang Zeng'})
