# Candidate instrument manifest review — September 23, 10:03 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: Session60 prospective study and root acceptance (10 points), root expanded package QA (5), and Yukang Zeng's author checks (10). This engineering receipt earns no study-completion credit.

Reviewed immutable head `b3c4f4a4abe05f39ed8716ee91743c59201f2b87`, substantive delivery `58ad9435fc1d08624b4bb859db83f68ba10c412e`, specifically `results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json`, generated **2026-09-23 09:52:59 UTC**. Manifest SHA-256: `75e2a1d1a7fd786b2dff70ba8602390c5e3460de7e06ad045660650d1e7913c0`.

**Disposition: accept the truthful post-execution candidate inventory as delivered, with the corrections and evidence limits below.** It is neither a prelaunch freeze nor independent reproduction of the four native outcomes. Missing original scripts and stdout/stderr can remain permanent disclosed gaps; no rerun is requested to replace them. Existing v7 source/application acceptance remains closed.

## Independently reconciled

Seven bounded document/structure checks passed. The deposited patch is exactly **17,188 bytes**, SHA-256 `88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184`, matching accepted v7. Base `4fea119de30f6a923992780f6fd5ccb0bee5d47d`, build timestamps **09:18:45–09:20:07 UTC**, 262/262 targets, exit0, and the declared 33,472-byte launcher digest agree with the earlier immutable `V7_FAILURE_INJECTION.json` receipt. Agreement with the earlier receipt is not an independent binary-byte check.

All **nine declared non-system library entries** have well-formed SHA-256 values, positive byte counts, matching resolved basenames and `@rpath` references. They include `libllama-server-impl.dylib`. Two system dependencies are named separately. This is a useful artifact inventory, but no deposited dependency-edge or loader-resolution evidence demonstrates complete recursive closure. **Zero launcher/library artifact byte streams were independently hashed in this review.** Owner-writable current build and scratch files were not opened. System-library hashes are not a requirement of this review; root owns acceptance of OS/build/architecture provenance and any later preview policy.

The four native `--help` outcomes remain owner-reported: writable control exit0, unwritable directory exit93, full-pipe unwritable exit93 in 0.08s, and full-pipe writable control exit0 in 0.08s. The reported experiment scope remains seal/fatal-path behavior without loaded-model lifecycle coverage. Historical smoke evidence retains its original version and provenance.

## Material additive corrections and next owner action

1. **Reconcile stderr routing.** `UNAVAILABLE_MATERIAL.per_case_stdout_stderr` says both initial cases sent stdout/stderr to `/dev/null`; both case rows instead say stderr was inherited from the terminal. Preserve the original receipt and add a correction identifying the supported routing, or explicitly mark it unknown if the historical record cannot establish it. Do not manufacture a precise reconstruction or rerun the cases merely for this discrepancy.
2. **Correct the reader-invocation claim.** The manifest says the code producing the exact reader invocation is recorded in `V7_FAILURE_INJECTION.json`. That file contains a parsed seal object, result fields and explanatory prose, but no literal invocation, producing code or selected manifest. Correct this to an unavailable original invocation unless retained contemporaneous material can be deposited. This does not reopen the separate accepted reader source review.
3. **Deposit the artifacts already reported present.** The 26,350-byte build log (`51876ff3cd8922cc292fdac162c395e0b5d418d0701a1307654cbf0aa2078746`) and 178-byte control lifecycle log (`26aa81b3646b08a34cbef0b7e562ab358b87229b1bf9366415b5560b24fe062e`) currently have owner scratch paths and declared hashes only. Immutable copies would allow independent byte reconciliation without a build or native rerun. The full-pipe writable control has no log-artifact entry; retain that as an explicit limit unless contemporaneous bytes exist.

Before describing the runtime inventory as a complete resolved closure, attach available dependency-edge/loader-resolution evidence and link the existing OS/build/architecture provenance. The current nine hashes alone support a declared inventory. No new model run, download, system-library hashing campaign or broad test is requested.

## Review limits

This review read immutable repository receipts and the deposited patch only: **7 document checks passed; 0 builds, native executions, models, sandbox runs, network calls or suite reruns.** It did not audit the parallel Python/supervisor changes. Evidence: `reviews/evidence/candidate_manifest_review_20260923_1003.json`. Next milestone remains root reconciliation of the additive evidence, followed by existing pin-promotion and lifecycle obligations under the current authorization.
