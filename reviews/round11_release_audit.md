# Round 11 release audit

**PASS for the bounded release and coding-reproduction checks. No release blocker found.** This does not replace human scientific verification, author attestations, a venue submission check, or the separate scientific reviews. The reported empirical and inferential limits remain in force.

Date: 2026-09-19. Scope: independently extract the current code/source archives, verify their payload and new coding provenance, run the default entrypoint and coding-only reanalysis, rebuild both PDFs, and compare the delivery. Root source and Git state stayed read-only. Only this report and `work/round11_release_audit/` were written. No model, generated benchmark candidate, full Monte Carlo study or commercial endpoint was executed.

The root notified me of the text-only clarification “1,024-token completion **cap** per call.” A fresh second extraction used the latest available archives; their hashes were unchanged from the first extraction, and the corrected phrase is present in the source and delivered paper. The final hashes were checked against the root artifacts again after reproduction.

## Frozen delivery

| Artifact | SHA-256 |
|---|---|
| `submission/anonymous_code.zip` | `624c1694574d21be534a1a5bfe5648893dc9aee2ab387e761a09ade54eff04e5` |
| `submission/latex_source.zip` | `2c6a64b28b1730d7b1daac4efb292d8b51abf915e07bf6c289ee23c0baca2088` |
| `submission/paper.pdf` | `d471f6f01f52a565ef0387fe1fb6eb9a7e9275e2a0dc242ba1e522e907a19021` |

Code archive: **217 members = 215 manifest-listed payload files plus generated `README.md` and `package_manifest.json`**. All 215 byte counts and SHA-256 values match. Source archive: **53 members**; every member shared with the code archive is byte-identical. There are no unsafe absolute or parent-traversal archive member paths.

## Entrypoint and numerical reproduction

After inspecting the entrypoint and coding builder, I ran these in the fresh isolated code copy with `/opt/homebrew/bin/python3` (Python 3.14.4):

```text
python3 reproduce.py
python3 reproduce.py --coding --build-pdf
```

The second command used TinyTeX's directory on `PATH`. Before its PDF build, the code-copy LaTeX outputs were cleaned with `latexmk -C -jobname=manuscript main.tex`.

Both entrypoint invocations passed the six analytic invariant checks and **114 archived output-hash checks**. Inspection confirmed that these flags execute only those checks, the root-owned coding aggregator and the PDF build. The full/simulation/extension paths and historical collection scripts were not entered.

The coding reanalysis regenerated the following **byte-identically** to their supplied archive versions:

- Four CSVs: `first_pass_pairs.csv`, `same_task_scores.csv`, `running_mean_bands.csv`, `resources.csv`.
- `results/open_coding/summary.json` and `results/open_coding_integrity.json`.
- `paper/open_coding_resource_rows.tex`.

All coding input JSON/JSONL files and provenance remained byte-identical as well. This result requires no timestamp exception: these new analytical outputs are deterministic.

All **37 preexisting result CSVs** present at commit `b1febcf` and in this release are byte-identical to that commit. The release contains **41 result CSVs** total, with the four coding CSVs accounting for the increase. No original numerical study was rerun or modified by this audit. Historical source hashes in preserved old manifests are treated as historical provenance, not mistakenly required to equal the current integration source.

## Coding projection and source provenance

I independently reconstructed the declared field projection from the frozen PR 8 episodes already retained in the prior audit scratch, without invoking the contributed collector or any candidate program. The supplied `episode_metrics.jsonl` matches all **1,182 projected rows exactly**, in original order. The original raw hash is the expected `95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0`.

The three projection output hashes in `provenance.json` match their files. The current coding integrity record correctly hashes both the root builder and the core comparator. Every entry in `evidence/open_coding_collection/source_manifest.json` matches its retained source text: seven `.py.txt` files, `config.json.txt` and `protocol.md.txt`. They remain unchanged through reproduction and are not executable imports or analytical dependencies. The root's scope note explicitly supersedes their historical inferential claims.

The exported rows omit `final_code`, `self_test_code`, `verify_stderr`, traceback and retry-log text. They preserve the recorded success/failure labels, errors through `error_present`, resource counts/times and assignment metadata. This is sufficient for the accepted aggregate analysis, not for independently regenerating model outputs or reexecuting hidden tests. That limitation is explicit in the appendix and provenance README.

The package retains the relevant benchmark/model identities, hashes, attribution and HumanEval MIT license text. The separate license provenance does not pretend that the older HumanEval dataset-file revision contains the later accessible license path, or that dataset/model licenses automatically grant a research-harness license. The previously missing contributed anonymous local-source-manifest copy is not a dependency of this accepted package.

The accepted appendix retains the intended scientific boundary: complete laboratory collection; post-hoc running history-conditional means; two marginal bands rather than a joint region; no fixed-roster population claim; no contributed E2/R2 uncertainty; same-task values descriptive; no realized stopping savings or guarded deployment. The call-limit wording is correctly a 1,024-token completion **cap**, not an assertion that every completion used 1,024 tokens.

## PDF and LaTeX checks

The source archive was built in its own fresh extraction with:

```text
latexmk -pdf -jobname=manuscript -interaction=nonstopmode -halt-on-error main.tex
```

It contained a delivered PDF but no cached auxiliary/bibliography/build-state files; the logs confirm a fresh LaTeX/bibliography build. The code archive was built after explicit cleanup through the reproduction entrypoint. Both builds finish without overfull boxes, undefined citations/references, or a remaining cross-reference rerun request. All statically expressed `\input`/`\include` dependencies resolve; the successful independent source build also checks the actual bibliography and figure dependencies.

All three PDFs—the delivered paper, rebuilt code PDF and rebuilt source PDF—have **38 pages**. Their `pdftotext -layout` output is exactly identical, SHA-256:

```text
ab9d14e1bf53b00cc342499c3dcf47fefac032b14c9fbddbdc9f15c87a8bf946
```

The rebuilt PDF bytes differ because compilation metadata changes, as expected. PDF author metadata is empty in all three. Main scientific content, including the Limitations paragraph, **ends on page 9**; the Reproducibility Statement **begins on page 9** and continues onto page 10. Ethics, AI Use and References begin on **page 10**. This report does not infer the main-content page count from the last numbered heading alone. Root separately owns full visual inspection; this audit verifies text identity, dependency completeness and build diagnostics.

## Bounded anonymity and credentials check

The manifest-verified text payload and extracted PDF text were scanned for the known author/account strings, personal email patterns, absolute user paths and per-session private temporary paths. No such hits were found. A separate scan found no API-key-shaped strings, GitHub-token patterns or private-key blocks. Candidate programs and benchmark assertion text are excluded from the episode projection. Scientific source code necessarily contains generic function/assertion examples; those provenance definitions are distinct from executable generated benchmark artifacts.

This is a bounded evidence-based scan, not a proof that no indirect identification is possible from any scientific artifact. The archive contains historical source/protocol provenance as documented; it should not be described as eliminating every possible linkage. No direct identity/credential issue or missing dependency was observed that blocks the present release.

## Audit records

Scratch contains the copied ZIPs, separate `code_v2/` and `source_v2/` extractions, delivered-PDF copy, build logs, extracted PDF text and the machine-readable checks:

- `archive_inventory_v2.json`
- `initial_integrity_audit.json`
- `final_reproduction_audit.json`
- `final_dependency_anonymity_audit.json`

The initial integrity record lists `README.md` as an unmanifested member because that first diagnostic allowed the wrong generated README filename; the final check correctly identifies **only** the two intentional metadata members, `README.md` and `package_manifest.json`. This is an audit-script bookkeeping clarification, not a missing package file or payload mismatch.

**Handoff:** the archive/PDF hashes above are the audited delivery. No root-source edit, Git mutation, new empirical collection or scientific-study regeneration is needed to close this bounded release check.
