# Round 9 (v2) outputs, preserved before the Round 10 repair

These files are the Round 9 outputs of the local stream exactly as they existed on 2026-09-19 before the Round 10 repair (copied with `cp -p`; nothing in this directory is regenerated). Their **numbers** remain valid as labelled in `../report_v3.md`; the following **wording** in them is withdrawn (Round 10 audit of PR 8):

- the description of the E2 task-level Hoeffding interval as needing no assumption, and of the task-level t interval as conservative for the finite-roster target by construction (`report_v2.md` section 4-5, `summary_v2.json -> e2`, `decision_rules_v2.csv` reading column): both intervals are MODEL-BASED (independent task scores, stable episode laws, no relevant pass/period effects; Lindeberg condition for the t interval);
- R1 described as "design-based ... no sampling assumption" with `mu_k = (1/2)[m(s_k,t_k)+m(t_k,s_k)]`: the R1 target is the running conditional mean given a stated filtration; the pair-mean reading needs an additional stable episode-law model;
- R2 without a stated filtration: it is unconditional model-based inference over hypothetical iid rosters.

`wincs_v2_pre_endpoint_fix.py.txt` is the Round 9 `src/wincs.py` (hedged capital, but `0 * log 0` evaluated as NaN at zero counts: capital 0.9875 instead of 1 at n = 0 and at degenerate endpoints; conservative in all checked cases). `test_wincs_v2.py.txt` is the Round 9 `src/test_wincs.py`. `../v2_vs_v3_numeric_check.json` compares the numbers regenerated with the repaired file against the files here.

| file | sha256 |
|---|---|
| `analysis_v2_manifest.json` | `278ff5cd8f208ff1274534157a0605600512a7d2455b207ff85ab13f39e4cb26` |
| `data_manifest.json` | `df0cd99b2795c750adea1d3972862b7a876e9b4893058b92e98ef5250de27064` |
| `decision_rules_v2.csv` | `73d2714d4092785936025c7240532afee914d968abf7a0b0e87efe5ba670295b` |
| `figures_v2/fig1_monitoring.pdf` | `6b3def96e811a79136c03281e67c4050a7ca72cfdf965c957b92d52fbda112ad` |
| `figures_v2/fig1_monitoring.png` | `a5ee22d2653b8b222a6aede0f42d8e3c811414336ada5ed881b7d8ee36801b28` |
| `figures_v2/fig2_running_nb.pdf` | `5ea93e9590bd417be8154fccbb4df06ac174dec3e20210d2de515b8eeb8319e8` |
| `figures_v2/fig2_running_nb.png` | `fb1778c575e0141049f9681212bff71444659b0d18f85daaf7c925d82ce91c3e` |
| `figures_v2/fig3_tier_decomp.pdf` | `8e8f3e7317971ebaf8f1cee11eb5fa1f4dae6b7b9c2feca8de5745602da4b116` |
| `figures_v2/fig3_tier_decomp.png` | `016fb3a7bb6a4d9deccc4b58a10ba4b35df84a94ea6a22b1b295925ec44e4d98` |
| `figures_v2/fig4_latency_scatter.pdf` | `075eb98faa86913d7d3e898017b7d5a45fedb103bbb8a0b75b349e31201de8f1` |
| `figures_v2/fig4_latency_scatter.png` | `899fef896308a2dd2f0cc9a5ffc6058af93e77ba6c5c967ecac359381874ce91` |
| `release_anon/MAPPING.json` | `669eebcde1d3aeb5d67e51112cde0ad2837719e66d595c365c9694523c848eb2` |
| `release_anon/MAPPING.md` | `c4c464318bcf50b798b703e8dabe19d741012e725b585f5ea2f7f7e334922fbf` |
| `report.md` | `1777e04a987cc8cef91c8c12ccb5e0fe0fe5a28863933535fba23b90fb7d141c` |
| `report_v2.md` | `b16d0814ca364f7f09c3a1ce09c389a8664cfbba359ece938dabcb8af0dae5ed` |
| `resources_v2.csv` | `6395a8a4e3d0c8a2bfdeedb9d9fb514b94e725cf1ad82fbe3ea639d1f3e82137` |
| `running_cs_v2.csv` | `c2599f6a3479e58f1c9d89b8afca45bccc9e69a611195d0f88926caf5ff9555f` |
| `sensitivity_v2.csv` | `b9a8c0f5ce6acd9fd947bd9c675775a24fe8d7ed285f65d3270aae6b69e05bf8` |
| `summary_v2.json` | `2515a92c0ad8387d18f9691216255af8e3cfbb7610145431eef4636558aa37a2` |
| `test_wincs_v2.py.txt` | `316de8e2a3d613684860759d788d9c12f103dec40cf83bece88902556de696a3` |
| `two_sided_cs_check.json` | `24858af1eb5966f4d6fef6d2b6835f8e2411fa61555f567532fe15ae0c3addd0` |
| `wincs_v2_pre_endpoint_fix.py.txt` | `6a6a0b51bf46d64079614af3aefc364800c1862fd7635728c2949be7f2907a3b` |
