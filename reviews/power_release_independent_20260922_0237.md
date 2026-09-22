# Independent power release audit — 2026-09-22 02:37 cycle

Scope: package membership, byte identity, manifest consistency, source dependencies and narrow saved-summary reproducer review. No baseline tests, scientific simulations, model calls, clean-source compilation or visual checks repeated; root owns the latter release checks. Snapshot working tree based on HEAD `6b724c2faa1be13438100fda4b1f06cad0bd20f5`.

## Checks passed on the initial built archive

- All five top-level artifact sizes and SHA-256 values match `arxiv/package_manifest.json`.
- The source tar contains 38 files with no duplicate members. Every byte matches `arxiv/source/`; all literal TeX input/figure references resolve inside it, and `main.bbl` is included.
- The code ZIP contains 392 entries: 391 payload files plus its manifest. All 391 payload sizes/hashes match, with no duplicate or unmanifested payload. Its `paper/` source files exactly match the source tar.
- All 80 new primary gzip containers match both manifest SHA-256 and their exact accepted Git blobs: 40 coarse, 24 fine, 16 corrected-disabled shards. All three expected-summary source hashes match their stated Git snapshots. No duplicate disabled-attempt data are included in numerical aggregation.
- The packaged power manifest equals its addition spec; packaged saved-record reproducer and figure script equal their addition sources. The two addition TeX files equal their generated source copies.
- `paper/` and `submission/` have no tracked differences against HEAD and no untracked files. This cycle preserves those historical paths.
- Current source incorporates the earlier claim-review precision edits. Its 32,000 unique versus 64,000 disabled evaluations distinction, pointwise MC interval descriptions and provenance/causal limitations remain appropriate. PDF page counts 49/13/36 are recorded by the build manifest; independently recompiling/counting/rendering is root's separate task.

## Findings and final disposition

**Pass for this bounded package audit.** One concrete initial provenance-link defect was corrected: the new power manifest originally recorded primary/summary snapshots but no explicit later addendum/erratum or failed-attempt paths. Root added seven exact-commit `provenance_records` at `94c62f7dbb55f926485097aed748dbdb1cfdc841`. Independent Git object checks resolve all seven to the expected blobs/trees: coarse addendum; fine erratum and retained failed attempt; both ablation directories; accepted ablation and fine provenance reports. The scope labels explicitly preserve missing historical evidence rather than pretending it was recovered.

**Reviewer correction:** I initially reported that the paired normal intervals used 1.96 and would fail the exact-quantile reproducer. That finding was my arithmetic error and is withdrawn. Direct calculation for P05N gives SE=sqrt((15/8000)(1−15/8000)/7999)=.00048369907222782564; exact normal quantile gives upper=.002823032760921976, exactly the saved endpoint. Using 1.96 would instead give .0028230501815665384. No reproducer correction is required. Root reports the packaged run passed; I do not claim to have repeated that run.

After the code-only rebuild, all 391 payload hashes/sizes pass again, the ZIP still has 392 unique entries including its manifest, and the packaged power manifest equals its updated spec. All five top-level artifact hashes match the updated package manifest. Source and primary record content are unchanged from the independently checked build above. Clean-source compilation, visual review and actual packaged saved-record reproduction remain root-owned; this audit does not duplicate them or claim scientific implementation re-execution.

## Final audited artifact identity

- `paper.pdf`: `0db00cb95897d7ac86d7b46d1ca294297622dabf6c6365d2788e9e849c5ba0e1` (536806 bytes).
- `main_paper.pdf`: `9b718fcbc8356f80e327ff24480e42c3273acc35cf010e5770b2a82294521c27` (300004 bytes).
- `supplement.pdf`: `a6273b5d147ba73a5f7ad601c3324daf96bb74271231038be4c57de716fe1c18` (452695 bytes).
- `arxiv_source.tar.gz`: `2dca10f583d1c003674eb24dae7d1be9beddd3cbc7f21151e6f34077e7eba35a` (152601 bytes).
- `reproducibility_code.zip`: `42bc42967b7db6e4bbd4f126a1ba3599dedd5b5c9bc0ca5fce7eb5ff96b34f3b` (24242924 bytes).
