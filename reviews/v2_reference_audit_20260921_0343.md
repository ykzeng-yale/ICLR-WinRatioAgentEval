# Independent bounded audit of the v2 external reference

Exact incoming source: `a10dba219a1dee10796eb019f3e14872249fbe2e`, compared with `a266c6201e3c94fc50c6646ca741e5e1da9b409b`. September 21, 2026, 03:43 UTC cycle. Read-only export; no owner files, primary rules, branch or experiment results modified. No model, full simulation, native build or dependency installation run.

## Accepted subset

- All **eight files declared verbatim** in `reference/MANIFEST.json` independently match their exact pinned upstream bytes, including both MIT notices. The ninth file is the explicitly identified local package initializer shim, whose local manifest hash also matches. The upstream pins are ComparingForecasters `52748c86e0429a9612dc79892c3be6156a524132` and confseq `5ffe733ca2447a2e28c2c91f3b00086173f2ab2c`. This is independently checked source provenance, not independent reproduction of the owner's compiled binary or timings.
- `reference/eb_reference.py:62–66,184–188` selects the requested **authors' mixture**, fixed `v_opt=10`, range `[-1,1]`, with caller per-gate alpha. The vendored `comparecast/confseq.py:174–199` constructs lagged predictable centers, squared prediction-residual clock, divides alpha by two internally, then calls `gamma_exponential_mixture_bound`. It does not substitute the owner's stitched cross-check.
- The panel explicitly labels complete latent scores as simulator-only and keeps reference columns separate (`reference/panel.py:22–35,113–142`). No partial endpoint variance plug-in was found in that path. The current constant-mean cells support use of `draw.cell.mu_h` as truth; a future drifting cell must supply its running conditional-mean truth rather than reusing a constant or realized sample mean. The reference estimates the running conditional-mean target, not the observed running sample mean as an inferential target.

## Exact scientific diagnosis of the cross-check

The cross-check mismatch is a **missing term**, not an unknown constant inside `ell`. At `reference/eb_crosscheck.py:149–156`, write `A = k1² v ell` and `B = k2 c ell`. Owner code returns `sqrt(A) + B`. The pinned author code (`reference/upstream/confseq/uniform_boundaries.h:505–510`) returns **`sqrt(A + B²) + B`**. Both use the same `ell`. The owner omitted the nonnegative `B²` inside the radical.

A five-point deterministic arithmetic check reproduces the reported values without building the native library:

| v | Owner formula | Pinned source formula | Relative shortfall |
|---|---:|---:|---:|
| 10 | 28.5871851682 | 37.1514662303 | −23.0523% |
| 50 | 50.4559119055 | 56.9624136766 | −11.4224% |
| 200 | 84.0291099487 | 87.9385626616 | −4.4457% |
| 1000 | 165.2729126644 | 167.2137682063 | −1.1607% |
| 5000 | 347.3456673770 | 348.2686745099 | −0.2650% |

Therefore the delivered cross-check does not implement the cited stitched boundary. Its asserted guarantee cannot be borrowed from that construction; retaining it outside accepted inference is correct. **Narrowness alone is not a proof of actual undercoverage**, nor a counterexample to the authors' mixture or this project's primary theorem. A standalone “10.7%” cannot describe this grid without its own specified point and denominator. The separate stitched-versus-mixture width comparison is between different constructions and is not an equality cross-check. Repairing the omitted term transparently is a legitimate mathematical/code correction; no blinded reimplementation or new experimental search is required. Preserve the original failed diagnostic receipt and label the repaired version.

Correct the claims in `eb_crosscheck.py:62–86` and `V2_BINDINGS.md:232–245,505–509`: the discrepancy is not in `ell`, and “the mixture is tighter than any stitched boundary” is not established by one configured path. State only the observed widths for the named construction, tuning and path.

## Panel comparison scope must be explicit

`panel_rows` computes only hierarchy scores `draw.z` and emits only `primary_l_h`, `primary_u_h` and the hierarchy reference. It has **no success-difference (`draw.d`) reference or noninferiority-guard comparison**. Consequently this panel cannot explain success-guard power or guarded deployment power; describe it as a hierarchy-only width diagnostic. No additional experiment is requested by this audit.

The reference index is `s.prefix`, the enrolled prefix n (`panel.py:121–124`), whereas completed-prefix/naive bands use their own index k/m. Equal enrollment time does not give equal information or equal target under changing means. Thus “same prefix”/“width at a common prefix” in lines15–20,29 must be qualified: ADAPTER is compared at n, but CPREFIX/NAIVE comparisons are calendar-aligned displays with different sample counts and potentially different conditional-mean targets. The current constant-mean cell can numerically share one truth without making those constructions universally target-equivalent. Emit explicit reference_n, primary_index and per-construction target labels before using such ratios beyond the demo.

## Small additional corrections and execution boundary

1. `eb_reference.py:35–38` says pre-halving caller alpha would double the error budget. It instead **halves the total allowed error budget again**, yielding a more conservative allocation; it does not inflate error. The executable call itself passes the correct unhalved per-gate alpha.
2. Loader `_load_package` at `eb_reference.py:98–99` returns a same-named existing `sys.modules` package without checking its origin. A reused interpreter could therefore load another `comparecast` or `confseq` instead of the pinned tree. Before general reuse, enforce a fresh isolated reference subprocess or verify/reject module origins. This is a provenance-hardening need, not evidence that the owner's reported fresh-process run used a wrong package.
3. Clean exported source on this reviewer host raises the expected `ReferenceUnavailable` for the missing CPython 3.14 native extension. No build was attempted. Thus compiled execution, mixture numeric output and owner resource receipts remain owner-reported at this audit's scope. Missing native artifacts are disclosed and reproducible-build instructions exist; do not label a skipped reference test as an executed numerical pass.
4. “Reference does not decide” does not exempt its execution from compute accounting. `panel.py:241–244` excludes its cost from any budget ladder because it cannot decide; the root's full panel resource assessment must still include the work actually planned. This review does not approve full-grid resources.

## Reproducibility and disposition

Scratch export and receipts: `/Users/yukang/Documents/Codex/2026-09-17/i-x20/work/reference_audit_0343/`, including `provenance_checks.json` and `formula_checks.json`. Formula check used installed NumPy/SciPy and no random draws. Source bytes were retrieved from the exact pinned primary repositories, compared to exported files and to declared SHA-256 values. Sources: [author boundary implementation](https://github.com/gostevehoward/confseq/blob/5ffe733ca2447a2e28c2c91f3b00086173f2ab2c/src/confseq/uniform_boundaries.h#L505-L510), [author EB wrapper](https://github.com/yjchoe/ComparingForecasters/blob/52748c86e0429a9612dc79892c3be6156a524132/comparecast/confseq.py#L174-L199).

**Disposition:** accept source provenance and the statically correct declared-mixture bridge as bounded progress. Request the focused formula/wording/provenance corrections above; do not conflate optional cross-check repair with primary invalidity. No independent mixture execution, full calibration, scientific milestone, integration or packaging acceptance is awarded by this report. Root retains the overall readiness decision.


## Addendum: reject the new operating-point interpretation at 3c6982c

Reviewed docs-only incoming `3c6982cf8c0867cd134976c73e1a7e402eb855ac`, file `experiments/live_ab_validation/BOUNDARY_WIDTH_AT_OUR_OPERATING_POINT.md`. The file explicitly declares a **polynomial-stitched boundary with c=0** (lines15–17), but calls its numbers the author reference and says they settle superiority at the operating point. They do not evaluate the approved comparator.

The selected wrapper has range `[-1,1]`; the exact upstream EB implementation sets `c=hi-lo=2`, uses the internal per-side allocation `alpha/2=.003125`, and calls the **gamma-exponential mixture** with fixed `v_opt=10` (`comparecast/confseq.py:178–199`). Even selecting the upstream stitched option would retain c=2. Replacing c=2 by zero removes the linear/exponential correction and is not justified for the selected empirical-Bernstein residual clock. A c=0 boundary may be valid for another proved sub-Gaussian process, but that is a different assumption/construction; this file supplies no such proof. Neither its width table nor its 8,867-pair number is accepted as the selected reference's result.

Further, `n × pilot variance` is a planning proxy, not the actual clock `max(1, sum(z_i-gamma_i)^2)` with lagged predictable centers. Equal terminal sample variance does not imply equality of the sequential residual clock. As a simple deterministic example, scores `(+1,+1,-1,-1)` and `(+1,-1,+1,-1)` have the same empirical distribution and terminal variance, but their residual sums are respectively `61/9` and `70/9` under gamma1=0 and the lagged-mean rule. Thus the caveat “conditional on realized variance matching the pilot” is insufficient to identify the claimed EB path. It must be conditional on the expressly imposed intrinsic-time curve, and still use the correct family/scale/alpha.

The paper-ready sentence at lines52–57 and the claims “tighter at every n,” “no crossover,” and “roughly half the shortfall” are **not accepted**. Four tabulated n values do not themselves establish an all-n ordering; the wrong comparator makes even the named four-point comparison inapplicable to the selected method. Equal estimated top-tier means do not establish genuinely identical systems, and no defined additive decomposition supports assigning half the shortfall to equality. Withdraw that decomposition rather than reuse the earlier rejected interpretation. The separate power-floor quantity remains incomparable by ratio to deterministic zero-effect boundary crossings.

Action: preserve this failed calculation as explicitly superseded development; withdraw its proposed manuscript wording. Recompute only a clearly named deterministic planning diagnostic with the actual selected mixture, c=2, exact two-sided allocation, fixed v_opt and an explicitly assumed residual-clock curve, or use a fixed fully specified score path and its actual predictable residual clock. Do not report a new crossing count until that computation is delivered and independently checked. This addendum runs no mixture code and substitutes no invented numbers. The error is in this new diagnostic specification/interpretation; it does not invalidate the correctly selected mixture bridge or the primary theorem.
