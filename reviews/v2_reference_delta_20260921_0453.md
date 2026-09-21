# Bounded reference delta review, September 21 04:53 UTC cycle

Incoming exact source `b96f965b993e0e153acc88e3da31dd29ed847c40`; prior head `bc9a4e0d8a46b60d19d4099120134da7ce231675`. Scope: changed cross-check, new width diagnostic, saved width receipt and associated interpretation. Unchanged vendored sources were not re-audited. No native build, model call, full grid or owner-file modification occurred. The earlier reference report remains intact.

## Accepted bounded progress

1. **Stitched transcription repair is correct.** `eb_crosscheck.stitched_boundary_repaired` restores the missing nonnegative squared term under the radical while preserving the failed function. Independent direct evaluation reproduces the five previously source-derived values: 37.1514662303, 56.9624136766, 87.9385626616, 167.2137682063 and 348.2686745099 at v=10,50,200,1000,5000. This is mathematical/code correction, not new method tuning or an independently run compiled-library comparison.
2. **Correct declared family and clock now enter the diagnostic.** `eb_width_diagnostic.py:160–174` calls the existing pinned `reference_bands` on actual hierarchy paths, with unhalved alpha=.00625; that unchanged bridge selects mixture, c=2, v_opt=10, with the internal alpha/2 split. It no longer computes the c=0 stitched planning surrogate. The reported residual clock is the lagged-center clock.
3. **Saved provenance and non-native arithmetic reproduce.** All six recorded source/config hashes match the exported incoming files, including diagnostic and vcompare. The receipt truthfully records parent HEAD bc9a4e0 plus working-file hashes matching b96; do not describe it as a clean execution of the parent commit. Independently regenerating only the eight specified namespace2/program0/trial0 latent paths reproduces all48 saved running means, residual clocks, primary widths and ratio arithmetic (tolerance1e-13). Saved values show three narrower and45 wider reference widths; those counts and the within-path grid crossings are supported by the saved table. **The reference's native mixture widths themselves were not independently recomputed.** No compiled library exists in the exported source, and none was built.
4. **Origin guard is improved for this diagnostic.** The new function at lines115–147 checks loaded module origins before width generation. A bounded synthetic module-origin probe rejects a `comparecast.confseq` outside the pinned tree as expected. This does not independently certify the owner's native binary or harden all other callers of the unchanged generic loader; the new diagnostic's reported module paths/build hash remain owner execution provenance.

## Remaining corrections and scientific limits

### P1: hierarchy-only findings do not diagnose success noninferiority

The executed path is explicitly `st.z_true` at line169. There is no `d_true` call to the reference, no success-gate width calculation, no guarded decision or stopping-power calculation. The eight regenerated hierarchy paths differ from their success-difference paths in **all eight cases**. The output and V2_BINDINGS_2 correctly disclose hierarchy-only scope; any issue-comment inference that45/48 wider widths means no useful variance-adaptive lever for the success guard must be withdrawn. Accepted wording is: **the saved configured complete-hierarchy diagnostic reports wider reference bands at45 of48 evaluated path/index points.** It neither establishes family dominance nor rules out a success-guard improvement. No new experiment or tuning sweep is requested here.

This is a comparison of two full constructions, including their boundary family, scale, error split conventions and fixed tuning; it does not isolate only the choice of clock. The opening claim that it “prices ONE difference” should be softened accordingly. Refer to the running conditional-mean target, not confidence coverage of the already observed sample mean. The primary/enclosure theorem is not contradicted by this width ordering.

### P2: the reported variance column is not prefix sample variance

At `eb_width_diagnostic.py:175–179`, `realized_var = cumsum((z-mus)**2)` subtracts a **different contemporaneous running mean at each observation**. It is not `sum_{i<=n}(z_i - mean(z[:n]))²`, the ordinary realized prefix variance sum. Consequently labels `realized_variance_sum` and `clock_minus_realized_variance` at lines194–196, and V2_BINDINGS_2's10–14-unit difference interpretation, are misleading.

Concrete reproduced example, C8 at n=2000:

- actual prefix centered sum of squares: **1332.8875**;
- reported “variance sum”: **1328.0053387752**;
- correctly computed EB residual clock: **1338.3695496439**.

Either rename the existing diagnostic precisely as a sum of contemporaneously centered squared residuals, or compute the ordinary prefix sum of squares as `cumsum(z*z) - n*mus*mus` and regenerate only affected descriptive columns. Preserve this receipt and label the correction. The error does **not** enter the actual reference call or its residual clock, so it does not by itself invalidate saved mixture widths.

### P2: correction history reverses the alpha mistake

`eb_width_diagnostic.py:238–240` and the saved `supersedes.why_it_failed` say the old calculation pre-halved alpha before a wrapper that halves internally. The withdrawn document instead declared a direct stitched-boundary call with alpha=.00625 and **no internal split**. The new module's own opening lines14–19 describe this correctly. Make the saved correction history consistent; the current executable comparison passes the correct total two-sided budget.

### Interpretation and provenance boundaries

The supplied source declares coordinates/grid fixed before widths. This audit verifies exact declared coordinates and saved hashes, not the chronological truth of pre-outcome selection; label it a development diagnostic, not an independently preregistered study. The statement “crossover exists” is supported here because the three paths narrower at n100 become wider by n200; the generic boolean `0<narrower<rows` alone would not establish a within-path crossover in arbitrary data.

## Next action and evidence

Accept the repaired algebra, corrected diagnostic wiring, hash concordance and regenerated-path arithmetic as bounded progress. Ask the owner to repair the descriptive variance column and alpha-history text, and keep all conclusions strictly hierarchy/path/grid-specific. Native mixture reproduction, broader calibration, live clearance, integration and readiness credits remain outside this review.

Checks and JSON receipt are under `/Users/yukang/Documents/Codex/2026-09-17/i-x20/work/reference_audit_0453/`: `audit_saved.py`, `saved_checks.json`, and the exact exported sources. Script creates eight fixed latent arrays only; it does not call the compiled reference, evaluate monitoring episodes, or write study results. Root retains the milestone and final resource decisions.
