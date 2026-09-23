# Candidate evidence deposit review — September 23, 10:39 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: Session60 prospective study and root acceptance (10 points), root expanded package QA (5), and Yukang Zeng's author checks (10). This engineering provenance work earns no study-completion credit.

Exact received head: `9e33602f61e263ed9792df177aba58f2303ef2bc`; substantive delivery: `b8e9e197d887c043d58046945defda023a005cc4`. Scope: the two deposited originals, their prior candidate declarations, and `CANDIDATE_EVIDENCE_CORRECTIONS.json` (owner timestamp **10:17:33 UTC**). No owner-writable current artifact was read and no build, native binary, model, sandbox, network operation or suite was run.

**Disposition: accept the exact deposited bytes and their limited engineering provenance.** Ten bounded byte/document checks passed. The four native exit/timing outcomes remain owner-reported; one original writable-control seal is now independently reconciled. Prior source/application acceptance stays closed.

## Accepted evidence

| Deposited artifact | Independently checked bytes | SHA-256 matching the prior manifest |
|---|---:|---|
| `evidence_session60/candidate_v7/v7_build.log` | 26,350 | `51876ff3cd8922cc292fdac162c395e0b5d418d0701a1307654cbf0aa2078746` |
| `evidence_session60/candidate_v7/control_life.jsonl` | 178 | `26aa81b3646b08a34cbef0b7e562ab358b87229b1bf9366415b5560b24fe062e` |

The candidate manifest itself is byte-identical to the earlier reviewed version. This deposit therefore closes the missing-copy obligation for these two artifacts without replacing the historical declaration.

The saved configure/compile log enumerates targets **1 through 262 exactly once**, ends with the launcher link, and records **`BUILD_EXIT=0`** and **`BUILD_END=2026-09-23T09:20:07Z`**, matching the earlier receipt. It records AppleClang **21.0.0.21000101**, **arm64/ARM**, Release, CPU, Accelerate BLAS and Metal. Nonfatal configuration warnings concern absent ccache/OpenMP/OpenSSL and defaulting to native ARM CPU flags; HTTPS support was disabled. Feature-detection failures are configure probes, not failed compilation targets. No compiler-error or stopped-build marker was observed.

The single JSONL line is a seal, with **zero lifecycle event records**. It exactly equals the earlier deposited parsed object: schema `live_ab/acquisition_seal-v1`, token `inj_ctrl`, monotonic timestamp `5303503053881`, and integer, non-boolean zeros for `records`, `write_failures` and `sidecar_failures`. This verifies the original seal byte stream and agreement with the previous object. It does not recreate the original parser invocation, prove which library bytes executed, or independently reproduce any exit or timing measurement.

The additive routing correction explicitly identifies the first two cases' `/dev/null` routing as an owner reconstruction from session commands, not retained execution evidence. That is an acceptable evidentiary label; independent routing proof remains unavailable. The library addendum correctly retracts the transitive-closure interpretation: the nine hashes are a direct dependency inventory, with dependencies of members and actual loader resolution not captured. No system-library hashing requirement is added.

## Material remaining corrections

1. **Record build-network and UI-source provenance.** Lines **331–338** of the now-deposited build log show a UI download attempt from `ggml-org/llama-ui` ref `b1`, failure to retrieve its checksum, then a successful download from mutable **`latest`**, extraction and embedding of **70 UI assets**. The previous native receipt's blanket `no network` statement cannot cover the build. A further additive note should scope any no-network claim to the injection phase if supported, and identify the build's additional UI input. Preserve any already-retained exact archive/stamp/digest; otherwise mark its identity unavailable. A log message saying the archive was verified is not a deposited immutable archive pin. This is a reproducibility/provenance qualification, not evidence that the seal or fatal path malfunctioned. **Do not rebuild or download to reconstruct the past input.**
2. **Finish the reader wording correction.** The addendum truthfully admits there is no retained reader-invocation transcript, but still says `V7_FAILURE_INJECTION.json` “contains the code that produced its fields.” That file contains summary assertions and a parsed object, not producing code. Add the precise correction: original invocation/producing code unavailable; summary fields retained. This is a wording/provenance repair and does not reopen the accepted reader source.

The permanent missing stdout/stderr and inline injection script need no rerun. The four native case outcomes remain owner-reported, now supported in part by the retained successful-control seal. No negative-case execution transcript, full-pipe measurement trace or original parser invocation was delivered. Candidate launcher/library hashes remain declarations rather than independently checked artifact bytes.

Evidence: `reviews/evidence/candidate_deposit_review_20260923_1039.json`. Next owner action is the narrow additive network/UI-source and reader-wording correction; existing launch-boundary pinning and lifecycle obligations remain under root's disposition.
