# T1 provenance clarification and release QA — September21,17:37 cycle

Full-project70%(change0); separately bounded-v190%.

The owner clarification03dc070 maps the discarded-pass allusion to measurement-mode passes already enumerated in ACCOUNTING_CORRECTION.json. Root inspected both records and the surviving log; independent provenance review agrees with this limited identification. It does not recover deleted data, erase prior decision-count exposure, or establish the absence of unrecorded attempts. The owner description of two traceback blocks is unsupported by the delivered log, which contains one; no such count is adopted in the paper.

Only AppendixO's final provenance paragraph changes. Against3e6e72d, extracted text differs only on page47; the first46pages, numerical table and primary records are unchanged. Historical paper/ and submission/ are untouched.

QA: rebuilt47-page article and13+34reading extracts; clean source extraction/latexmk reproduces text on all47pages. Root visually inspected page47 at1.5x; paragraph is legible with no clipping/overlap. Clean code extraction passes six analytic checks,127archived-result hash checks and336000T1 primary-record checks across56shards/eightcells. All305ZIP payload hashes and five artifact hashes match manifests. No model call or full simulation rerun. Current artifact hashes are in arxiv/package_manifest.json. Power/ablation outcomes are not added to the paper or code archive in this change.
