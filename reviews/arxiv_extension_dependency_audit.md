# arXiv extension dependency repair audit

September 19, 2026. Independent bounded release audit. **PASS: the accepted U-statistic extension now starts from a clean code archive without the excluded `wincs` module.** This closes the specific release dependency finding; it does not approve all merged contributor methods or independently rerun their experiments.

## Examined release

| Artifact or transformation | SHA-256 |
|---|---|
| Repaired `arxiv/reproducibility_code.zip` | `408b129f0fb5e029d881059458cdf8b83f3524b56f54498c6c1d6f57d8f46165` |
| Preserved `submission/anonymous_code.zip` | `d3887a19ff6d71c5af91080540aec6ed7777b571274e8dd4fbadcd4747e92334` |
| Original accepted U-statistic runner | `cb96f8a58577dc9980109b5ed6932a64deae1f73005e0adf5b5af703103809e8` |
| Release-only repaired U-statistic runner | `e38a174418e19db233041a9148e1707ea455acd6c2b301ab7409957c02ebd9ee` |

The source of the defect was a transitive import: the accepted U-statistic runner imported only `SCENARIOS` and `THRESHOLDS` from `run_online_methods.py`, but that module unconditionally imported `wincs`. The privacy/scientific allowlist intentionally excluded `wincs` from both historical and arXiv archives. This defect predates the subsequent broad branch merges; its absence from default reproduction checks did not make the advertised optional extension runnable.

## Exact repair and preservation checks

- Literal text comparison against the historical ZIP confirms that the **only change to the accepted runner is the import/configuration block**. Removing the old and new blocks yields identical remaining source text, so the numerical algorithm is untouched.
- Independent parsing of the frozen source assignments establishes equality of all scenario values and their insertion order: `null`, `efficiency_gain`, `success_regression`, `safety_regression`, `joint_gain`, `weak_gain`, `tie_heavy_null`, `tie_heavy_efficiency`. The six base scenarios still come from the unchanged `run_simulations.py`; the two extensions and thresholds `[0.0, -0.03, -0.01]` exactly match the former dependency. Scenario order matters because it enters the documented seed indexing and was explicitly checked.
- The repaired archive contains 246 manifest-listed payload files plus its manifest. Every listed size/hash matches and there are no unlisted members. No `wincs.py` has been added. The embedded provenance and outer package manifest agree on the original/released runner hashes and name the dependency-only transformation.
- All **47 packaged CSVs remain byte-identical** to the historical anonymous code archive. That historical ZIP itself is unchanged. The three current PDFs and `arxiv_source.tar.gz` are byte-identical to their tracked pre-repair versions; this code repair requires no paper/source-upload rebuild.
- All five current artifact hashes and sizes match the updated outer manifest. The previous independent release/visual reports continue to describe the unchanged PDFs and source upload; the code ZIP hash in this report supersedes their prior ZIP identity for this correction.

## Clean isolated checks executed

Two fresh extractions were created under ignored `work/arxiv_dependency_audit/`: one historical archive and one repaired archive. `PYTHONPATH` and `PYTHONHOME` were removed from the test environment, user-site imports were disabled, and extension startup/import checks used Python isolated mode. Explicit checks rejected any `wincs` import and checked that loaded modules did not leak from the parent repository's source/experiment directories.

1. Historical U-statistic runner `--help` reproduced `ModuleNotFoundError: No module named 'wincs'` before argument handling.
2. Repaired U-statistic runner, rare-event diagnostic and drift-panel runner each passed `--help` and independent import-only checks. No `wincs` import or parent-repository module leakage occurred.
3. The repaired archive's default `python reproduce.py` passed **six analytic truth checks** and **127 archived output hashes**.
4. A separate minimal builder fixture exercised `--code-only`. It produced a code archive with identical member contents to the delivered repair while leaving all three PDFs and the source-upload tar byte-identical. Combining `--code-only --sources-only` failed explicitly with exit 2 before authoring. Review of the implementation confirms that code-only mode bypasses source preparation and TeX compilation and skips rewriting the upload tar.

No full simulation, model call, generated candidate program, excluded inference procedure or original collection runner was executed. CLI startup and unchanged algorithm text justify closure of this dependency defect; they do not constitute a fresh replication of all extension results. The preserved historical archive intentionally still exhibits its recorded defect; new reproduction should use the repaired arXiv code archive.

## Broader merge state is a separate fact

The earlier read-only comparison of root `05d5ed48d0f31ad05539ed0f13ab26442fc01df3` with merge head `1c3e9f37fb0357a2eb7f501e734a67638984da96` found **296 added files, 12 modified existing files and no deletions**. At that merge, all five then-current arXiv artifacts, all 37 original paper files, all 47 packaged CSVs, the retained core and root builders were unchanged. Direct byte verification of the default integrity records matched all 127 hashes, without executing repository code.

That preservation does **not** extend to the whole development tree: three of the 55 frozen-baseline repository CSVs changed (`results/benchmarks/tau2_contrasts.csv`, `results/benchmarks/tau2_rankings.csv`, `results/cs_width.csv`); those three are outside the release payload. Of 237 existing root paths represented in the arXiv payload, only `experiments/run_online_methods.py` changed on merged main. Its changed hedged-capital function is not used by the accepted U-statistic runner, and its scenario/threshold configuration is unchanged. The repaired release now avoids that transitive dependency altogether while preserving the historical ZIP as its input.

Before the broad merges, fresh GitHub blob comparisons also confirmed that all 26 accepted PR 7 files and all 12 accepted PR 10 files matched their reviewed source commits and root `05d5ed4`. None lies in the merge's modified-existing-file list. GitHub's merged state is therefore distinguished from scientific approval of generic projections, width/replay methods or contributor interval claims. Those exclusions remain governed by the established disposition records, not the merge operation.

The audit wrote only this report and its assigned ignored scratch. It made no source, original artifact or Git changes.
