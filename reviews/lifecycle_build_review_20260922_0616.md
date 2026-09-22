# Lifecycle build/source receipt review — September 22, 2026, 06:16 cycle

Read-only review at `3f6cc56e4f889870920ea37e294a7b455f799fa7`: producer patch `99e18054edc59e3462c8b39db6ceb9c0701dd03c`, build receipt/generator `479cd86eede41fd07521c036bee69597213e8796`, saved prebuild receipts and retained pinned upstream source under outer `work/server0459`. No build, model, server, native invocation or repeated suite was run. Root owns requested loaded-smoke scope; separate reviewer owns lifecycle-consumer defects.

**Accept this as an owner-reported successful isolated build and a narrowly evidenced native seal serialization path, not a complete runtime/linked-library identity or slot-lifecycle validation.** Full readiness75% unchanged; bounded-v1 90%. Prospective study10, final expanded QA5 and author checks10 remain.

## Verified receipt arithmetic and source scope

- Exact deposited250-line patch hashes to `984f47df65b0db7b945234660cde2aae9a035c4efcee42ec780c27df9c59a918`, matching receipt. Base revision is declared `4fea119de30f6a923992780f6fd5ccb0bee5d47d`.
- Declared05:56:03Z–05:56:52Z duration is49seconds. Receipt reports exit0,270 log lines, zero `error:`/`warning:` substrings, Release/Ninja, CMake4.4.3 and Apple clang21.0.0. Full configure/build output is not deposited in this delta, so compilation counts,262-target completion, cache status and exact effective invocation cannot be independently reconstructed from the receipt alone. Counts of log substrings are not general compiler-diagnostic verification.
- Prebuild05:46:58Z records refusal with a foreign server and1.7GiB free+inactive memory.05:55:23Z records no watched processes/listeners,3.4GiB free+inactive,95.5GiB disk and1.83 one-minute load,**40 seconds before the reported05:56:03Z start**. This is an owner capacity snapshot, not continuous reservation or measured peak build resource use. The refusal and later attempt are both retained.
- Native raw seal plus newline is exactly178UTF-8 bytes, matching the saved byte count. Parsing that line produces exactly the deposited seal object: zero records, zero recorded failures, matching token and named CLOCK_MONOTONIC. Reported `--help` exit0 is consistent with a model-free path.

## Build parallelism: record the deviation accurately

Root authorized **at most two compile jobs**. The saved receipt explicitly states `-j6`; this allows six parallel build workers. `compile_jobs_used:1` counts one build invocation, not compiler parallelism, and does not demonstrate compliance with the two-job limit. No evidence says all six were concurrently active at every instant, but the configured maximum itself exceeded the stated cap.

Preserve the original receipt and add a correction distinguishing **one invocation / configured maximum six workers / observed peak concurrency unrecorded**. Use at most `-j2` for subsequent authorized repairs. Do not rebuild unchanged code merely to rewrite historical resource compliance. No peak RAM/CPU/output-size budget receipt accompanies this build.

## Binary identity is incomplete for this dynamic executable

Receipt reports a33,472-byte launcher SHA-256 `7a5423a38bcb645f292282a1d76e625c38dcc1a225b7d12a7a94232e88580ec4`. `otool -L` output lists nine non-system `@rpath` libraries, including `libllama-server-impl.dylib`, which can contain the emitter. It does not record resolved library paths, content hashes, recursive dependencies or what the loader actually used. Neither launcher nor dylib bytes are available in the reviewer environment, so their hashes were not independently recomputed.

Finite next action: retain exact build/configure output and effective command; bind the existing launcher **and resolved non-system libraries** with hashes before smoke/runtime claims. Do not describe a launcher hash alone as the full instrument identity. No new build is required merely to record already existing files.

## Native fixture scope and contradictory verdict

`BUILD_RECEIPT_20260922T055747Z.json` retains `reader_rejected` saying the seal was not a `slot_lifecycle-v1` record, while its verdict says “SEAL WRITTEN BY THE BUILT BINARY AND PARSED.” This original failed interoperability record must remain. The owner correctly disclosed the failure and subsequently repaired the reader, but the receipt generator's `native_seal_fixture` still computes success only from raw seal fields; it does not require successful child exit, no reader errors/rejections, exactly one seal, or consumer acceptance.

Correct the generator's success predicate and attach a dated reparse of the **saved178bytes** through the repaired reader. No repeat native invocation is needed solely for that reconciliation. `--help` establishes the ordinary-exit static-destructor seal path under this invocation only: it emits **zero slot records**, exercises no assignment/prompt/generation/release transition, and does not validate two-slot concurrency, model execution, multi-completion refusal, or injected writer-failure handling. The generator docstring acknowledges this limited scope and should remain equally precise in reports.

## Static producer findings

The v2 patch preserves assignment-before-processing and release-before-reset placement and adds an explicit parent/child refusal while instrumentation is present. Thus it addresses the named multi-completion child-copy limitation at source level for the intended single-completion path. No served `n=1`/`n>1` receipt exists; behavior remains static review. Instrument enable checks differ for absent versus empty environment values (refusal uses presence; emitter requires nonempty), so launch should set the intended nonempty instrument path. This is not an observed model failure.

**Concrete remaining writer-failure gap:** patch lines205–213 do not check the seal's `fprintf` return; `fflush(f) != 0 || fclose(f) != 0` skips `fclose` when flushing fails. A close failure after the complete seal was written occurs *after* its `write_failures:0` value was serialized. Persistent invalidation then exists only in `<log>.error`. The current reader reads acquisition-error schemas within the main log, but `read_records(log)` does not itself acquire the sibling sidecar. A nominally valid main seal can therefore fail to expose the terminal writer failure unless the supervisor separately retains/checks that sidecar. An error counter alone cannot retroactively amend the seal already emitted.

Finite repair: check seal formatting/write status, always attempt both flush and close, and collect/refuse the separate writer-error sidecar in the actual acquisition path. Preserve failed/partial output and process status. Explicitly check failure-side-channel persistence; a best-effort `.error` write is not itself guaranteed reliable. The planned targeted fault receipt should demonstrate terminal failure propagation rather than count a later synthetic dictionary test as native fault coverage. This does not require a new scientific study.

Static-destructor execution observed on ordinary `--help` exit does not prove shutdown of all active request work before sealing, or sealing after every possible termination path. Missing seal/crash remains refusal; the planned finite real request smoke must establish the intended graceful-close contract. No claim of continuous GPU utilization follows from occupied-slot intervals.

## Practical handoff

Preserve this build and failed native-reader receipt; record parallelism deviation and missing log/library identities; repair terminal error propagation and truthful fixture verdicts. Root can scope the next finite instrumentation smoke using actual available local resources and existing request limits. These are implementation/provenance gates, not reasons to rerun the completed scientific simulations or historical model studies.
