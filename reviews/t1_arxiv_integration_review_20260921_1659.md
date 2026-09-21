# Bounded scientific review of the T1 arXiv addition

Reviewed root's working integration files `arxiv/additions/t1_validation.tex` and `arxiv/additions/reproduce_t1.py` against independently accepted T1 snapshot `35ab9d1` and review commit `97ad956`. These additions were not yet present in `97ad956`; this review identifies the read working bytes by SHA-256:

- `t1_validation.tex`: `1230cdd1f066770d733508149f777fa870d371d8df8f0420ab944936088fc633`
- `reproduce_t1.py`: `9b4a8aac4cd0be811cc1e5334a2dc2cd03e5be886b6bd841dd3b9376865cfc70`

No source edits, simulations, native calls, or unrelated studies were performed. Root owns rendering and clean source/code-archive execution.

## Scientific disposition: accept

Every ADAPTER/NAIVE error, hierarchy-miscoverage, correct-deployment count and per-cell trial denominator in the table matches the prior independent committed-row aggregation. The total 28,000 programs × four trials = 112,000 trial paths is correct; each construction has the stated cell denominator rather than sharing a pooled denominator. The 2,000-versus-5,000 program allocations and all four pairs of hierarchy/success truths are correct.

The false-deploy conjunction, false-harm definition, trial union and program union are correctly distinguished. The listed nominal levels match their stated scope. C5/C6 are correctly described as the success noninferiority boundary, and the text explicitly avoids attributing their zero guarded deployments solely to the guardrail. The ADAPTER abstention counts and the 15 CPREFIX plus 14 NAIVE false harms match the accepted records.

I independently recomputed the three quoted Wilson intervals:

- `376/2000`: `[.1714806857,.2057155518]`, correctly rounded in the text.
- `5000/5000`: `[.9992322981,1]`, correctly rounded.
- `5/20000`: `[.0001067896,.0005851504]`, correctly rounded.

The five distinct C4 error programs and their hierarchy-eligible miscoverage are reported without a zero-error requirement or an unsupported theorem-violation claim. The description correctly separates all-path band miscoverage from first-decision error and states marginal Monte Carlo uncertainty, replay exposure, abstention, finite-law scope, and absence of a power-curve/MDE inference. It makes no causal mechanism, live-agent performance, or reference-width/power claim. The explicit record-reaggregation versus latent-regeneration boundary is accurate. Recovery/attempt provenance wording is appropriately qualified, subject to root's independent provenance report.

## Reproducer: source review

The standard-library reader checks each primary file's archive-manifest hash, refuses duplicate `(cell,construction,program,trial)` coordinates, recomputes hierarchy miscoverage and the actual decision-label counts, and uses the correct T1 error definition (DEPLOY in C1–C6, or RETAIN_INCUMBENT in any cell). It compares the aggregates against the supplied expected table counts and checks 336,000 total construction records. This matches the table's numerical scope.

The script expects its generated `manifest.json` and primary files beside it in the release layout. That manifest is not present beside the working template, so this review does not claim an in-place execution or archive success. Root's planned extracted-archive run is the relevant check. The script verifies the table counts; it does not itself recompute the prose's program-union Wilson intervals, which were independently checked above. No new defect is identified in the scoped table-reproduction logic.

## Remaining work and progress boundary

No scientific blocker was found in these two integration files. Root still owns PDF visual inspection, clean-source build, and extracted code-archive checks. This acceptance is specific to the T1 addition and does not mark the whole expanded project ready: full-project readiness remains the root-reported **70%** until the remaining new-study integration and other documented milestones are complete.
