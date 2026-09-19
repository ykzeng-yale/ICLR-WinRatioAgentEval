"""Round 12 REPORT-ONLY corrections of the coding-stream owner report. No model call, no analysis rerun, no git command.

Reads results/local_stream/report_v3.md (never modified), applies the exact-text replacements below (each must match the
stated number of times, otherwise the script aborts), prepends a Round 12 note and writes

    results/local_stream/report_v4.md
    results/local_stream/report_v4_manifest.json   (sha256 of source and output; the replacements; the one recomputed constant)

No estimate, interval, table row or figure changes. The only new constant is the probability in the cluster-level
counterexample, (1 - 1/296)^296, computed here.

Usage: .venv/bin/python experiments/local_stream/make_report_v4.py
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / 'results' / 'local_stream'
SRC, OUT, MAN = RD / 'report_v3.md', RD / 'report_v4.md', RD / 'report_v4_manifest.json'
REVIEWED_HEAD = 'c1da1c3fc4e8c90644388e8b47e2e15574fe5215'
ROOT_INTEGRATION = '45e8ee2715f148c81db7f6510d66677f57e03f0a'
G = 296
P_ALL_ZERO = (1 - 1 / G) ** G

FULL = 'F_k = sigma(the full frozen schedule: arrival order, pairing and ALL orientation coins; revealed pair data up to k)'
COARSE = ('a COARSER filtration that leaves the orientation of pair k unrevealed and (nominally) fair, '
          'G_k = sigma(arrival order, pairing, orientations and revealed data of pairs 1..k), together with a stable assignment / episode-law model '
          '(given G_(k-1) and the orientation, the two episodes of pair k have a joint law that depends only on their tasks and workflows, not on the orientation, the pass position or the history)')
CLT = ('cluster-level CLT conditions: variance growth / nondegeneracy, a Lindeberg or no-dominant-cluster condition, and a consistent cluster variance estimator')

REPLACEMENTS = [
    # ---- finding 1: R1 filtration
    ('summary item 5: symmetric formula needs a coarser filtration', 1,
     'the pair-mean formula and the link to a roster-level target hold only under an additional stable episode-law model.',
     'the guarantee conditions on the full frozen schedule (order, pairing and all orientation coins), so mu_k is the conditional mean of the score in the REALIZED orientation; the symmetric pair-mean formula is a conditional mean only under a coarser filtration in which the orientation of pair k is still unrevealed and fair, plus a stable assignment / episode-law model, and the link to a roster-level target needs that model as well (Round 12 correction).'),
    ('R1 table row: filtration', 1,
     'F_k = sigma(design information independent of future outcomes, revealed pair data up to k) | bounded scores and the stated filtration; the target may move with n and with history (thermal state, order, caching). The reading mu_k = [m(s_k,t_k)+m(t_k,s_k)]/2 needs an ADDITIONAL orientation-independent, history-independent stable episode-law model and is not assumed |',
     FULL + ' | bounded scores and the stated filtration; the target may move with n and with history (thermal state, order, caching). Under this filtration the orientation of pair k is known, so mu_k is the conditional mean of the score in the realized orientation. The symmetric reading [m(s_k,t_k)+m(t_k,s_k)]/2 is NOT a conditional mean under this filtration: it needs ' + COARSE + '; it is not assumed (Round 12 correction) |'),
    ('R1 caption: filtration and symmetric formula', 1,
     'for the filtration F_k = sigma(design information independent of future outcomes, revealed pair data up to k); Z_k - mu_k is a martingale difference with conditional range 2, which is all the normal-mixture boundary uses.',
     'for the filtration ' + FULL + '; Z_k - mu_k is a martingale difference with conditional range 2, which is all the normal-mixture boundary uses. (Round 12 correction: the earlier phrase "design information independent of future outcomes" is dropped. It is not needed for the guarantee, and information fixed before the outcomes is not thereby independent of them.)'),
    ('R1 caption: symmetric formula', 1,
     'The interpretation mu_k = [m(s_k,t_k) + m(t_k,s_k)]/2, and with it E_design[mu_bar] = theta_N, holds **only under an additional orientation-independent, history-independent stable episode-law model**; thermal state, execution order and caching can affect latency, so that model is not assumed and',
     'A filtration that contains all realized orientation coins cannot at the same time give the coin of pair k conditional probability 1/2. The interpretation mu_k = [m(s_k,t_k) + m(t_k,s_k)]/2 is therefore **not** a statement about the filtration above; it holds **only under ' + COARSE + '**. The same boundary also covers the running conditional mean for that coarser filtration, because the score is adapted to it; the two targets are different and must not be confused. The unconditional identity E_design[mu_bar] = theta_N is an average over the assignment and needs the additional model too; it is not the conditional identity. Thermal state, execution order and caching can affect latency, so the stable assignment / episode-law model is not assumed and'),
    # ---- finding 2: cluster t conditions
    ('summary item 2: cluster t conditions', 1,
     'Independence across clusters is still an assumption.',
     'Independence across clusters is still an assumption, and the approximate cluster t interval additionally needs ' + CLT + ' (Round 12 correction).'),
    ('section 4: cluster-robust t status', 1,
     't reference on G - 1 = 295 df, **approximate**.',
     't reference on G - 1 = 295 df, **approximate**. (Round 12 correction.) Independent clusters and bounded cluster totals do **not** by themselves justify this approximation: it needs ' + CLT + '. Counterexample to a blanket coverage claim: G = 296 independent clusters with B_g ~ Bernoulli(1/G), sizes n_g = 2 except one singleton, totals T_g = n_g B_g; the target is 1/G > 0, yet with probability (1 - 1/296)^296 = %.9f every total is 0, the cluster variance and the t width are 0, and the interval misses the target. This limits the claim; it is not evidence that the observed sample has that law.' % P_ALL_ZERO),
    ('section 4 table header: cluster t', 1,
     '| cluster t 95% (approximate; independent clusters) |',
     '| cluster t 95% (approximate; independent clusters AND cluster-level CLT conditions) |'),
    ('section 5: cluster t slack sentence', 1,
     'orientation-pair cluster-robust t -0.029460 (approximate, independent clusters; slack 0.000540)',
     'orientation-pair cluster-robust t -0.029460 (approximate; independent clusters and cluster-level CLT conditions; slack 0.000540)'),
    ('decision table: cluster-robust t rows', 2,
     'E2 orientation-pair clusters (G = 296), APPROXIMATE, independent clusters assumed',
     'E2 orientation-pair clusters (G = 296), APPROXIMATE, independent clusters and cluster-level CLT conditions assumed'),
    # ---- finding 3: pass / roster sentence
    ('pass table reading aid: no causal attribution', 1,
     'the success-rate differences between passes within a variant therefore largely track which half of the roster was exposed, and period effects on latency are not separately identified.',
     'these descriptive differences mix task composition with possible period effects (including workflow-specific period effects); the table does not separate them (Round 12 correction: the earlier wording that the differences "largely track which half of the roster was exposed" is withdrawn, because the split does not identify how much comes from either source).'),
    ('figure 2: embed the Round 10/12 legend version', 1,
     '![fig2](figures_v2/fig2_running_nb.png)',
     '![fig2](figures_v3/fig2_running_nb.png)'),
    ('figure 2 caption', 1,
     '(R1; the legend text "design-based" in the Round 9 figure file is to be read with this wording); orange: same-task NB with its 95% task-level t interval, which is MODEL-BASED (section 4). Source: `running_cs_v2.csv`, `summary_v2.json`.*',
     '(R1); orange: same-task NB with its model-based 95% task-level t band (dark) and the exact 296-cluster Hoeffding band (light) (section 4). Round 12: this is `figures_v3/fig2_running_nb.png` (script `make_figures_v3.py`; legend wording corrected, plotted numbers unchanged; sha256 in `report_v4_manifest.json`); the Round 9 file `figures_v2/fig2_running_nb.png` is kept unchanged. Source: `running_cs_v2.csv`, `summary_v3.json`.*'),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    t = SRC.read_text(); applied = []
    for label, count, old, new in REPLACEMENTS:
        assert t.count(old) == count, 'expected %d match(es), found %d: %s' % (count, t.count(old), label)
        t = t.replace(old, new); applied.append(dict(label=label, matches=count, old_sha256=hashlib.sha256(old.encode()).hexdigest(), new_sha256=hashlib.sha256(new.encode()).hexdigest()))
    for banned in ('design information independent of future outcomes, revealed', 'largely track which half of the roster was exposed, and'):
        assert banned not in t, banned
    first, sep, rest = t.partition('\n')
    note = ("\n> **Round 12 report-only correction (2026-09-19).** This file is `report_v3.md` (reviewed by the root session at `%s`; kept byte-unchanged) with wording corrections for the three points of the root session's Round 12 review (`reviews/round12_coding_correction_and_baseline_delta.md` on main; root integration commit `%s`): (1) the R1 guarantee conditions on the full frozen schedule, and the symmetric pair-mean formula is stated only under a coarser filtration plus a stable assignment / episode-law model; (2) the approximate cluster t interval needs cluster-level CLT conditions in addition to independent clusters; the exact cluster Hoeffding bound does not; (3) the pass/period table does not separate roster composition from period effects. No model was run, no analysis was rerun, and no estimate, interval, table row or figure changed. The root integration uses the raw observations with its own running-conditional-mean analysis; the owner intervals of this report are not part of it. Script `experiments/local_stream/make_report_v4.py`; hashes `report_v4_manifest.json`; binding wording `experiments/local_stream/protocol_addendum_round12.md`. Figure 2 with the corrected legend: `figures_v3/fig2_running_nb.png`.\n" % (REVIEWED_HEAD[:7], ROOT_INTEGRATION[:7]))
    OUT.write_text(first + sep + note + rest)
    MAN.write_text(json.dumps(dict(
        kind='report-only correction (Round 12); no model call; no analysis rerun', source='results/local_stream/report_v3.md', source_sha256=sha(SRC),
        output='results/local_stream/report_v4.md', output_sha256=sha(OUT), reviewed_owner_head=REVIEWED_HEAD, root_integration_commit=ROOT_INTEGRATION,
        replacements=applied, figures_v3_sha256={f: sha(RD / 'figures_v3' / f) for f in ('fig2_running_nb.png', 'fig2_running_nb.pdf')}, counterexample=dict(G=G, probability_all_cluster_totals_zero=P_ALL_ZERO)), indent=2) + '\n')
    print('wrote', OUT.relative_to(REPO), MAN.relative_to(REPO), 'P_all_zero = %.9f' % P_ALL_ZERO)


if __name__ == '__main__':
    build()
