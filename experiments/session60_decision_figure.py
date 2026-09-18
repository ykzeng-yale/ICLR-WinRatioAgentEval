"""Decision-disagreement figure from results/benchmarks/decision_matrix.csv."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / 'results/benchmarks/decision_matrix.csv')
rules = [('dec_success_only', 'Success\nonly'), ('dec_pareto', 'Pareto'), ('dec_utility_lambda0.1', 'Utility\nλ=0.1'),
         ('dec_utility_lambda1.0', 'Utility\nλ=1.0'), ('dec_hierarchical', 'Hier.\nNB'), ('dec_guarded', 'Guarded\nNB+gate')]
short = {'gpt-4.1-2025-04-14': 'GPT-4.1', 'o4-mini-2025-04-16': 'o4-mini', 'claude-3-7-sonnet-20250219': 'Claude 3.7',
         'sweagent_claude3opus': 'SWE-agent Claude 3 Opus', 'sweagent_gpt4': 'SWE-agent GPT-4'}
def name(s):
    s = short.get(s, s); return s.replace('HAL Generalist Agent', 'HAL-Gen').replace('Taubench ToolCalling', 'HAL-Tool').replace('(claude-3-7-sonnet-20250219)', '(Claude 3.7)').replace('(claude-3.7-sonnet)', '(Claude 3.7)').replace('(gpt-4.1-2025-04-14)', '(GPT-4.1)').replace('(o4-mini-2025-04-16 high)', '(o4-mini)')
d['pair'] = [f"{r.source}/{r.domain if r.source=='tau2' else ''} {name(r.A)} vs {name(r.B)}".replace('//', '/').replace('swe/ ', 'SWE-Lite: ').replace('hal/ ', 'HAL airline: ').replace('tau2/', 'τ² ') for r in d.itertuples()]
code = {'A': 1.0, 'B': -1.0, 'undecided': 0.0, 'neither': 0.0}
M = np.array([[code[v] for k, _ in rules for v in [row[k]]] for _, row in d.iterrows()])
fig, ax = plt.subplots(figsize=(7.6, 7.8))
cmap = matplotlib.colors.ListedColormap(['#D55E00', '#EEEEEE', '#0072B2'])
ax.imshow(M, cmap=cmap, vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(rules))); ax.set_xticklabels([l for _, l in rules], fontsize=8); ax.xaxis.set_ticks_position('top'); ax.xaxis.set_label_position('top')
ax.set_yticks(range(len(d))); ax.set_yticklabels(d.pair, fontsize=7)
for i, row in d.reset_index().iterrows():
    if row.priority_inversion:
        ax.text(len(rules) - 0.45, i, '⚑', va='center', ha='left', fontsize=8, color='black')
    ax.text(4, i, f"{row.nb:+.2f}", va='center', ha='center', fontsize=6.5, color='white' if row.dec_hierarchical != 'undecided' else 'black')
ax.set_xlim(-0.5, len(rules) + 0.2)
for x in range(1, len(rules)): ax.axvline(x - 0.5, color='white', lw=1.5)
for y in [8.5, 9.5]: ax.axhline(y, color='black', lw=0.8)
ax.legend(handles=[Patch(color='#0072B2', label='prefers A'), Patch(color='#D55E00', label='prefers B'), Patch(color='#EEEEEE', label='undecided / neither dominates')], loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=3, fontsize=8, frameon=False)
ax.set_title('Decision under six rules for 25 system pairs\n(⚑ = hierarchical winner has the lower success rate; cell text = hierarchical net benefit)', fontsize=9, pad=30)
plt.tight_layout()
for ext in ['pdf', 'png']:
    fig.savefig(ROOT / f'plots/session60/fig_decision_matrix.{ext}', dpi=200, bbox_inches='tight')
print('saved')
