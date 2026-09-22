# Server lifecycle patch source review — September 22, 04:59 UTC

Reviewed `1d669d6` files `experiments/live_ab_serving/live_ab_slot_lifecycle.patch` and `PATCH_RECORD.md` against pinned upstream `4fea119de30f6a923992780f6fd5ccb0bee5d47d`. Downloaded only three upstream text files into outer scratch `work/server0459`; no clone, native build, model, server, lifecycle collection or shared-service change. `git apply --check` against those pristine files passed. This is source acceptance analysis, not a compiled-binary or live-producer receipt.

## Accepted source semantics

The emitter is placed before release clears task/stats. Ordinary successful requests have a physically ordered assignment, prompt-start, last-generation and release sequence. The selected interval describes an occupied request slot spanning prompt processing and generation, including scheduling pauses. It is not specifically continuous decoding or GPU utilization. Incomplete/early-rejected requests can produce incomplete records, which must remain unusable for coverage.

Upstream already forward-declares `server_slot` at line109; the new prototype does not introduce an unknown-type error. Reset clears stats, so ordinary slot reuse does not inherit a prior request's timestamps. Last-generation time is updated on normal and speculative generation paths. These are favorable source checks, not proof of compilation. [Pinned server context](https://raw.githubusercontent.com/ggml-org/llama.cpp/4fea119de30f6a923992780f6fd5ccb0bee5d47d/tools/server/server-context.cpp), [pinned stats definitions](https://raw.githubusercontent.com/ggml-org/llama.cpp/4fea119de30f6a923992780f6fd5ccb0bee5d47d/tools/server/server-common.h).

The pinned POSIX `ggml_time_us` uses `CLOCK_MONOTONIC` and truncates nanoseconds to integer microseconds; the Windows branch uses a different clock. Therefore the named domain is supported for the explicitly restricted POSIX build, not portably for every build of this patch. Microsecond representation is not zero endpoint error: retain the existing conservative endpoint/error policy. [Pinned clock implementation](https://raw.githubusercontent.com/ggml-org/llama.cpp/4fea119de30f6a923992780f6fd5ccb0bee5d47d/ggml/src/ggml.c).

## Concrete repair required: silent logging failures

The patch's emitter contradicts `PATCH_RECORD.md`'s assertion that no record is silently dropped and that refusals are counted:

- Failed `fopen` returns without a failure record, counter, log or propagated error.
- A zero-byte `fwrite` breaks the loop, after which execution returns as if emission finished. The accepted prefix may remain in the file.
- `fflush` and `fclose` results are ignored. A successful buffered write can still fail when flushing, leaving no reported producer failure.
- Format failure/truncation also returns silently. No durability operation is present beyond the unchecked stdio flush.

These are direct executable branches, not hypothetical generic hardening. A consumer cannot count an absent line merely by rejecting the malformed lines it receives. Depending on the consumer's provenance/selection logic, omission may cause refusal or leave incomplete acquisition accounting; this source alone does not establish either full retention or a trustworthy complete-stream claim.

Minimal repair: use checked complete-record writes and checked flush/close; retain/propagate a persistent producer-invalid/error state with run identity so the consumer refuses the affected acquisition if a write is lost or truncated. Preserve partial bytes as evidence. If the required contract is crash-durable logging, check the appropriate sync operation too; otherwise explicitly label visibility versus durability and do not promise crash durability. Avoid throwing from release in a way that recursively re-enters failing release/error paths. This can be exercised with injected I/O failures without another model experiment.

## Finite scope correction: child-copy assignment

`copy_state_to` copies the entire stats object (upstream line730), so the two newly added fields are copied too. Child slots are launched before the parent; their own assignment stamps are overwritten by the later parent stamp. Thus the reported child `t_assigned_us` is not its actual assignment transition. This does not by itself extend the selected interval before that child's occupied lifetime, because the child was already waiting. It does invalidate the universal claim that all four values are that slot's observed transitions. Preserve the child's assignment stamp across this copy, or explicitly constrain this producer contract to the planned single-completion (`n=1`) requests. No general multi-completion validation study is needed.

## Disposition

Accept the ordinary occupied-slot transition placement and the exact-source application check. Require the finite logging-failure repair before claiming a reliable lifecycle producer, and correct the child/occupancy wording scope. The patch has no intrinsic host/boot record fields; binding a file and process to those identities remains the Python preparation/observer responsibility reviewed by root, not evidence supplied by this patch alone. The model-free nine-test byte fixture remains a consumer-contract test, not execution of this C++ producer.

No code or owner document was edited. Full readiness remains **75% (change 0)**; bounded-v1 **90%**. Actual prospective evidence, final expanded release QA and author checks remain pending.
