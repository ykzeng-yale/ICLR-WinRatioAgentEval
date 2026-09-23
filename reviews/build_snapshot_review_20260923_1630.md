# Candidate build snapshot: independently checked deposited layers

Full-project arXiv readiness remains **75% (Δ0)**; bounded-v1 remains **90%**. Remaining: Session60/root finishes prospective preparation/study (10 points), root final expanded QA (5), and Yukang Zeng author checks (10). CPU validation, integration and packaging remain complete and unchanged.

Reviewed [source d143532575e966ef970f7004e9369b43f7a5662e](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/d143532575e966ef970f7004e9369b43f7a5662e), delivered at [defa4a17189a69e083777be78041f2eeb56c5edf](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/defa4a17189a69e083777be78041f2eeb56c5edf). All seven new working-tree files were compared byte-for-byte with their exact-commit blobs; these reads succeeded. This review accepts the copied configuration/compiler/link/log evidence, not a fresh measurement of owner binaries or clearance to launch. [Detailed evidence and reproduction](evidence/build_snapshot_review_20260923_1630.json).

## Accepted deposited observations

The receipt's four copy hashes/sizes match independent calculations. `CMakeCache.txt` and `ninja_log.txt` also match the receipt's whole-original hashes. The compiler and link files are **excerpts**; their own hashes are verified, while the undeployed full-original hashes remain declarations.

| Deposited setting | Independently observed agreement |
|---|---|
| `GGML_BACKEND_DL=OFF` | Registry command has no backend-DL definition; linked ggml target carries backend dylibs |
| `GGML_BACKEND_DIR` empty | No definition in any of the 56 deposited ggml compiler entries |
| CPU, BLAS, Metal enabled | Available-backend cache is exactly those three; registry has corresponding `GGML_USE_*`; ggml link rule names those three |
| `GGML_METAL_EMBED_LIBRARY=ON` | Both named Metal compiler entries define it; retained build log records embedded-source assembly |
| `GGML_CPU_ALL_VARIANTS=OFF` | Directly present in copied cache; actual absence of variant files is separately owner-reported |
| `BUILD_SHARED_LIBS=ON` | Generated backend link rules and retained build log describe shared dylibs |

Independent parsing reproduces all four named source-definition/entry-hash rows and **all ten deposited link blocks**. The Ninja log has **295 rows**, including the relevant registry/Metal objects and output libraries/launcher; no row names `build.ninja`. This last observation does not prove the cache/rules were never modified or regenerated. Generated compile/link records describe build instructions; the log records output completion. Their agreement is useful historical provenance, not independent binary reproduction.

The retained original build log still hashes to `51876ff3cd8922cc292fdac162c395e0b5d418d0701a1307654cbf0aa2078746`. The eight source digests quoted by the owner match both the prior root report and the retained exact-upstream bytes. The owner's external source tree itself was not accessed.

## Scope limits and one small parser correction

The receipt's ten measured binary digest strings agree with the prior candidate declaration. **No candidate binary bytes or raw symbol-table outputs were deposited/read in this review.** Consequently the ten fresh measurements, 20 embedded-source start symbols, dlopen-importer classifications, directory absence, source-tree/reverse-patch checks and original file mtimes remain owner-reported observations. `all_layers_agree=true` mixes deposited layers with those observations; it is not an independently verified all-layer or current-runtime verdict.

The helper's `BACKEND_OPTIONS` comment claims every backend in the pinned revision, but the list omits `GGML_ET`. The retained source contains `ggml_add_backend(ET)` and the copied cache shows **ET=OFF**, so this omission does **not** change the present CPU/BLAS/Metal conclusion. Include ET, or derive the checked set from the retained definitions/available-backend entry, before describing the reusable comparison as exhaustive; an enabled backend outside its supported list should refuse. The present copied cache is acceptable and ET=OFF adds no blocker. No new build is needed.

The sentence asserting every loader call site in `common/`, `src/` and `tools/server/` uses argument-free `load_all()` is a literal in the snapshot generator, without collected caller locations/source excerpts. Retained upstream registry/search semantics are confirmed, but the complete callsite enumeration remains unverified. The earlier argument-parser/DNS limitation is preserved; no more source was downloaded. If the owner relies on an all-default-call-sites proof, deposit the exact existing matching source excerpts with paths, line locations and source-file hashes rather than another summary assertion. This does not reopen the settled semantics that `GGML_BACKEND_PATH` is an additional direct library target rather than a directory override. No native measurement rerun is requested merely to refresh status.

Next finite step remains root's frozen environment/cwd and complete dependency-set decision, followed by the owner binding that context and current resolved bytes at the launch boundary. Preserve this **post-build-provenance** snapshot as historical evidence. It is not a pre-execution freeze, proof that external files remain unchanged, observed loading behavior, or launch authorization.

## Verification

**13 focused owner controls passed; zero failures/errors/skips and zero guard violations.** Eleven use synthetic text/values; two use tiny temporary directory fixtures, including symlink enumeration. Independent guards prohibited subprocess execution, network and signals. The snapshot generator's acquisition `main()` was never run. No owner external paths, binaries, nm/otool, network, build, model or experiment were accessed/run. Only the two assigned review outputs were written; no commit or shared/owner edit was made.
