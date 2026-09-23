# Bounded dependency-contract repair review, 2026-09-23 16:30

Full-project arXiv readiness: **75% (Δ0)**. Bounded-v1: **90%**. Remaining: prospective-study completion and independent acceptance (Session60/root, 10 points), expanded release integration/QA (root, 5), and final author checks (Yukang, 10). No milestone is earned by this helper review.

Reviewed source `ab38e615ad5ec039fc37b533eb7295eefb478026` at exact head `defa4a17189a69e083777be78041f2eeb56c5edf`, extracted with `git show` into an isolated directory. The three source/test files were inspected there and the test/helper modules imported; `lab_common` was an unused import stub. The evidence records exact Git-blob SHA-256 values and source extraction equality. The receipt was parsed from the exact Git blob. No owner files, shared status, or commits were changed.

## Disposition

Accept the three prior repairs within the tested helper scope: verification now carries the dynamic reader and launch context; the parser handles `LC_REEXPORT_DYLIB` and the other declared dependency commands while refusing unknown commands; and an edge is keyed by parent, command, and reference. The prior two-parent helper collision is closed. This is engineering acceptance of these repairs, not acceptance of a loaded candidate, frozen launch, or prospective study.

**One reproduced contract defect remains:** static dependency canonical targets are not bound. `resolve_reference` returns the first existing path spelling; `_add_file` and the recursive walk use that spelling, while the supplied `realpath` reader is called only for the root executable. Changing the canonical target of `/cand/bin/helper.dylib` from `/payload/A/helper.dylib` to `/payload/B/helper.dylib`, with the same bytes and metadata under the unchanged selected spelling, returns `verified: true` and no problems. Both derivation and verification called `realpath` only for `/cand/bin/llama-server`. This violates the quoted preflight requirement to compare canonical resolved paths. It also leaves the helper's loader-relative context attached to the uncanonicalized spelling.

Ranked next action: canonicalize and bind each selected non-system dependency target, preserving the corresponding loader context, or conservatively refuse a selected dependency whose path differs from its canonical target. Apply the same declared rule at preparation and preflight. A small synthetic canonical-target-change control is sufficient; this finding does not request a build, model load, native loader audit, or new experiment.

## Independent checks and limits

- **35 supplied dictionary/string controls passed once**, with 0 failures, 0 errors, and 0 skips. Outer guards denied process creation, native commands, sockets/network, signals, and sleep; no denied operation was attempted. No actual native metadata reader was invoked.
- **Three additional pure probes:** (1) a dynamic-reader error at preflight was rechecked across five members and refused; (2) the canonical-target-change witness above passed incorrectly; (3) a dependency requiring an inherited-only runpath was refused. The third establishes that particular conservative refusal, not a universal proof of dyld ordering.
- The delivered receipt is timestamped **2026-09-23T16:15:13Z**. Its 10 path/size/hash rows—launcher plus nine libraries—match the earlier candidate manifest exactly. The closure reports 41 edges, 10 files, no duplicate install names, no shadowed selections, and successful straight-back verification. These are independently reconciled saved declarations, **not independent measurements of the owner-host artifact bytes**. Its four real-metadata refusal controls remain owner reported.
- The receipt has no separate source/test hash fields; the exact Git commit binds the delivered helper and tests, and this review records their measured blob hashes. No claim that those hashes were frozen before the owner's receipt is made.

## Resolution-domain claims

The own-rpaths-only strategy can be a deliberately narrow supported domain. The tested inherited-only miss refuses correctly. The wording that it universally “can only refuse more, never pass more” is stronger than these controls establish, particularly while noncanonical dependency paths are accepted. Scope that assertion to the supported canonical-path domain; do not present the synthetic controls as a full dyld proof.

The changed duplicate-install-name control deliberately resolves two parent contexts to two different files with the same install name, records both, and traverses both. That demonstrates the helper's dictionary behavior and a possible conservative inventory; it does not independently establish which image dyld reuses for each runtime edge. The current candidate receipt reports no duplicate IDs, so no new candidate failure is inferred from that generalized behavior. If exact per-edge selection is required for the accepted domain, refusing duplicate IDs is an adequate conservative restriction until the relevant behavior is established. This review does not request implementation of a general dyld loader.

The gate remains explicitly unwired. Source/patch/build identity association, the actual child environment/cwd, and final entry-point wiring remain root's existing integration obligations. No authorization for a loaded probe, calibration, trial, or additional native run follows from this report.

Evidence: `reviews/evidence/dependency_contract_review_20260923_1630.json`.
