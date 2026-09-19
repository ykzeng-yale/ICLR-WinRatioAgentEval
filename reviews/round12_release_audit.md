# Round 12 final release audit

**PASS for the bounded package/reproduction checks below.** Audited the final supplied archives in new isolated extraction directories on 2026-09-19. This does not constitute independent human scientific signoff or a production-validation claim. Root owns the full visual review and submission decision.

The auditor also performed the separate airline evidence audit, and authored the earlier commercial pilot; this audit independently tests the assembled release and its reproduction boundary. No model calls, weight/network downloads, full study reruns, generated benchmark-program execution, root source edits or Git mutations were performed. The required default command includes the repository's six small analytic-truth invariant checks.

## Frozen artifacts

| Artifact | SHA256 |
|---|---|
| `submission/anonymous_code.zip` | `d3887a19ff6d71c5af91080540aec6ed7777b571274e8dd4fbadcd4747e92334` |
| `submission/latex_source.zip` | `a1dd834a2884d2d4428e0221159573c453968ad610a3c15c8e162811f1a81fda` |
| `submission/paper.pdf` | `c1add4bb829c4044d5c3e299613a63c7849b09961a53b66be1067bbcbc7244b8` |
| `submission/package_manifest.json` | `a86a3b49deed3f4a6250db5970f42a751a7ee54bbf7d5a9f0fca881ef49a77b6` |

The code ZIP has **241 payload files and 243 entries**. Every payload hash matches its manifest; the only additional entries are the generated anonymous README and manifest itself. There are no duplicate archive names or traversal/absolute archive paths. The source ZIP has **56 files**, every one identical to its corresponding member of the code ZIP before rebuilding. The originally archived manuscript PDF equals the delivered PDF byte for byte. All three root delivery artifacts still had these hashes at the end of the audit.

## Isolated reproduction

Runtime: `/opt/homebrew/bin/python3`; TinyTeX binaries at `/Users/yukang/Library/TinyTeX/bin/universal-darwin` were placed on PATH. Source snapshots were extracted without a Git directory. Inspected entrypoint/builder source before execution; the selected command paths use archived metrics and do not run inference or benchmark candidates.

Executed in the fresh code extraction:

```text
python3 reproduce.py
python3 reproduce.py --airline --build-pdf
```

The default command passed the scientific invariant checks and **127 archived output-hash checks**. The airline command also passed those checks, rebuilt the airline descriptions and table, and compiled the manuscript successfully.

All **14 airline/provenance/integrity/table files** remain byte-identical to the supplied versions, including:

- all six airline CSVs: attempt ledger, unit flags, canonical accounting, replay scores, same-task scores and masked-replay bands;
- episode metrics, assignment, configuration, provenance, omitted-usage counters and summary JSON;
- the airline integrity manifest and `paper/open_airline_table.tex`.

All **47 CSVs in the archive** remain byte-identical after the command. Among original archived members, the only bytes changed are the regenerated `paper/manuscript.pdf`; its per-page text matches exactly after whitespace normalization. Numerical outputs, generated TeX, historical provenance and their manifest hashes did not change.

A separate fresh source-ZIP extraction was built with:

```text
latexmk -pdf -g -jobname=manuscript -interaction=nonstopmode -halt-on-error main.tex
```

Both isolated compilations succeeded. This verifies that the supplied source/figure/table dependencies resolve from each package without the root checkout.

## PDF content and page boundary

All three PDFs—delivery, rebuilt code archive and rebuilt source archive—have **40 pages**. Their extracted per-page text is identical after whitespace normalization. The SHA256 of the same normalized page-text array is `ee3dcf138fd26e3f805c91e95d92e67b25f5ac43530a61a34fc77ccb3dfbd220` for all three.

**Substantive main content ends on page 9. Reproducibility, ethics and AI-use statements begin on page 10; references also begin on page 10.** Page 9 contains the final related-work and limitations text, so the main boundary is not inferred merely from the last numbered section heading. This release must not be described as statements beginning on page 9.

Rebuilt PDF hashes differ because PDF bytes include build-dependent metadata:

| Rebuilt artifact | SHA256 |
|---|---|
| Code extraction PDF | `e4b7537bb20fcd9b6a7350ca39d619bbd89f16dde25e52d8ec80144d5f7a630e` |
| Source extraction PDF | `774c93a2b3574623d0e48bbdfb9a965229b161b318800a7fc1ede228d7daa7d3` |

Each final LaTeX log has **0 overfull boxes, 0 undefined references/citations and 0 multiply defined labels**. Each has 17 underfull box notices and two warnings changing an `h` float specifier to `ht`. These spacing/placement warnings are reported rather than called a warning-free build. They did not change extracted page text, and full visual acceptability remains the root's visual-QA responsibility.

## Preservation of earlier results

Compared every tracked `results/**/*.csv` at baseline `1001b23` against the current root repository, using read-only Git blob access: **all 49 are unchanged**. Of these, **41 are retained in the release and are byte-identical to baseline**. Eight earlier contributed CSVs are deliberately outside the bounded release:

```text
results/benchmarks/hal_contrasts.csv
results/benchmarks/hal_marginals.csv
results/benchmarks/swe_contrasts.csv
results/benchmarks/swe_marginals.csv
results/benchmarks/tau2_contrasts.csv
results/benchmarks/tau2_marginals.csv
results/benchmarks/tau2_rankings.csv
results/cs_width.csv
```

Their omission is not a result mutation; they remain unchanged in the repository. The six new airline CSVs account for the package's increase from 41 to 47. The core `src/winstats.py` also matches baseline byte for byte, SHA256 `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`.

## Anonymity and provenance boundary

No known author identifiers, identifying local home paths, personal-email patterns or realistic provider/GitHub credential patterns were found in the textual package members. All ten packaged PDFs were separately checked through text extraction and metadata; there were no matching identifiers or secrets. Manuscript Author metadata is blank. Archive inventories exclude credentials/API-key files, author metadata, private work folders, Git internals and `.DS_Store` files. This is a bounded known-pattern audit, not a proof against every form of indirect deanonymization.

The release uses metrics projections and clearly marked historical source text; it does not require raw model conversations or executable collection code to produce the airline descriptions. Both original runner snapshots and their source hashes are preserved. The airline provenance explicitly distinguishes archived `reward_info.reward` from message-derived usage, retains reward/trajectory missingness, and states that complete failed-attempt usage is unavailable. The omitted-use counters and their lower-bound arithmetic are preserved with their source lineage; they are not represented as complete measured resource consumption.

The earlier scientific evidence review remains the authority for the airline inferential limits. This release pass confirms faithful packaging and reproduction of the intentionally descriptive integration, without upgrading it to task-population, fresh-run or live-production inference.

Scratch evidence is confined to `work/round12_release_audit/`, including copied immutable archives, inventories, `integrity_check.json`, reproduction/build logs, extracted PDF text and `final_checks.json`. Only this review file was written under root outputs during this release audit.
