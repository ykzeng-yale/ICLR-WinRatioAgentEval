# v1 analysis outputs, preserved before the Round 9 repair

These files are the analysis outputs of the local stream exactly as they existed on 2026-09-18 before the
Round 9 re-analysis. **They were produced with the UNCORRECTED two-sided betting confidence sequence**
(`src/wincs.py` thresholded `max(K+, K-)` at `1/delta`, which guarantees only `2 delta`) **and with the
UNCORRECTED target wording** ("295 independent pairs", a population guarantee for the monitor on a fixed
roster, "B harmful", independent-arm Welch intervals, "frozen before any model call"). Do not cite their online
two-sided intervals or that wording. Point estimates, counts, tier decompositions, one-sided e-process paths and
first-crossing indices in them are unaffected and agree with v2.

| file | sha256 |
|---|---|
| `summary.json` | `778f2f4f896aed76c4d2d746b67308dc3a24fd79b9b04cd9193e0e4c6767ef78` |
| `decision_rules.csv` | `45a09b1b6231f84b62a6799c40110f99da175b30fca4c6c44bc613cab665c944` |
| `sensitivity.csv` | `964b7cfc033856a232fa25e6b1eb87b9a136c113cbdf68b0cf66aa08549facc7` |
| `task_scores.csv` | `8438877ca6b2dbdcb3b9f7088a7c70cf3a45ffaebbe341f856f9ca72eb32c4ce` |
| `episodes_flat.csv` | `1237b82f99c5ea8ad1e319e0ec45873ba85a2ff13d670d508d78ae06547bd540` |
| `report.md` | `9023783dc4328f204510a2a34fba4df2ece6d33e43d78e464558f4c446358b92` |
| `wincs_v1_uncorrected.py.txt` (the v1 `src/wincs.py`) | `714b21fe041b7fbe62b21f6a91c301e22e9fe4c1b492161505ecdf4b3ea292a4` |
| `test_wincs_v1.py.txt` (the v1 `src/test_wincs.py`) | `97086887f6ed1ddfaeec1e33d91371601e19017ce4bedea8644af691e38737de` |

Also here: `analysis_stdout.log` and `figures/` (v1 figures; Figure 2 shows the uncorrected CS).

Raw evidence was never part of this copy and was never modified: `../episodes.jsonl`, `../monitor_pass1.csv`,
`../monitor_state.json`, `../run_manifest.json`, `../design.json`, `../design.sha256`.
Current results: `../report_v2.md`, `../summary_v2.json` (see `experiments/local_stream/protocol_addendum_round9.md`).
