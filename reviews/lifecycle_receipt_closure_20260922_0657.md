# Lifecycle receipt closure review — September 22, 2026, 06:57 cycle

Exact review: owner `31c22fd3df9d0d74593c727f55487490e0b7bc42`, head `f3061b68a7a0c1684b51411deb11f3406d131942`. Bounded source/receipt delta and a read-only parse of previously saved178 native bytes. No build, server, native invocation, model or repeated scientific/test suite. Root owns the finite two-request scheduling decision.

**Accept the saved-seal reparse, deviation record, deferral, and independent flush/close source repair. Do not yet accept the blanket claim that all writer/receipt checks are finished.** Full readiness75% unchanged; bounded-v1 90%. Prospective study10, expanded final QA5 and author checks10 remain.

## Precisely closed

1. Deposited patch hashes exactly to `4c8b647de674edca06578642b17fff7e24d8625ad9d9933238170c668c4a0840`. The prior `984f47df…` build cannot demonstrate execution of this changed patch; the owner correctly labels it stale.
2. Both record and seal paths now call `fflush` and `fclose` independently, then separately inspect their results. The previous short-circuit skipping `fclose` after a flush failure is removed. This is verified source behavior, not a rebuilt/fault-injected native receipt.
3. `BUILD_RECEIPT_20260922T055747Z.json` remains byte-identical to its original `479cd86` version, including its reader rejection and overbroad verdict. `BUILD_RECEIPT_REPARSE_20260922.json` preserves that failure and limits the new claim to parsing the same seal. I reconstructed the178bytes from the original raw line plus newline and passed them to the current reader: **0 records,1 seal,0 rejections,0 writer errors,error=None**, matching the new receipt. No binary was invoked; no nonempty lifecycle path was validated.
4. `DEVIATION_BUILD_PARALLELISM_20260922.json` correctly records one invocation, configured six workers, unknown observed peak, cap two, and subsequent `-j2` use. It does not erase or repeat the historical build.
5. Deferral is consistent with the already authorized finite plan: stale binary, missing launch manifest, unverified weight pin in this cycle and insufficient setup/cleanup time before07:00. Nothing started; the model attempt has not been consumed. The last clear-capacity snapshot is not a new clearance or a reservation. The listed future window still needs its actual start check.

## Unclosed writer check: owner's fprintf claim is contradicted by the patch

At `experiments/live_ab_serving/live_ab_slot_lifecycle.patch:210–215`, the seal's `fprintf(...)` is still a bare call whose return is discarded. The claimed “seal fprintf result is checked” is not present. Lines222–228 check flush and close, which is a real repair but does not replace the missing formatting/write-result check. The separate failure writer at lines102 onward still ignores its own fprintf/flush/close results; that path is explicitly best-effort.

Finite action: capture/check the seal write return; keep flush/close independently attempted; propagate failure through the already specified acquisition-invalid path. Do not describe unchecked failure-sidechannel persistence as reliable merely because it is a separate filename. This is the preexisting terminal-write obligation, not a new statistical or experimental gate.

## Receipt predicate repair is partial, with a concrete remaining partial-write case

`build_receipt.py:100–109` now requires child exit0 and no `parsed['rejected']`, closing those two omissions. It still ignores `parsed['error']` and derives `seals` independently from raw `splitlines()` rather than requiring the parser to have accepted exactly the expected zero-record seal.

A valid JSON seal **without its final newline** is a concrete existing failure path: `read_records` returns a mid-line error with `rejected=[]`, while the generator's raw splitlines parse still yields the correct seal and passes its field checks. With child rc0, the verdict can again say parser success although the parser refused the log. This follows directly from the actual `read_records` early-error branch and current predicate; no new native probe is needed.

Finite action: require `parsed['error'] is None`, use the parser-returned seals, and enforce the specific seal-only fixture contract (exactly one matching seal,zero records,zero writer errors). Keep its scope as serialization/interoperability, not full acquisition or live coverage. The already saved178byte successful reparse remains accepted and needs no rerun.

## Actual sidecar now consumed, but failed-write handling must remain fail-closed

The new `observe` opens `<log>.error` and refuses nonempty recognized/malformed-text records and caught filesystem errors. This closes the previous complete absence of sidecar consumption for ordinary error records. Three details matter directly to the producer's terminal-error path:

- An **existing empty sidecar** is ignored. The producer creates this file only after incrementing a write-failure counter, and its own subsequent write can fail; an empty file can therefore be failure evidence, not evidence of no error. Fresh per-attempt paths permit treating unexpected sidecar existence as refusal.
- A valid JSON scalar/list is appended then used as `e.get('stage')`, causing an exception; non-UTF8 bytes raise `UnicodeDecodeError` outside the current `except OSError`. These do not falsely certify, but can bypass the promised returned refusal/retained diagnostic. Preserve such bytes and return a refused acquisition without depending on their shape.
- The producer failure writer remains best-effort; if both main-log and sidechannel persistence fail, the supervisor/process failure path must still prevent acceptance as previously required. This review does not add a broader durability architecture or claim an untested failure was observed.

Root/separate reviewer handles token/sequence/lifecycle consumer acceptance; these comments concern only the newly added actual sidechannel and receipt claims.

## Remaining receipt scope

No repaired build receipt, resolved non-system library hashes, local weight verification receipt or immutable engineering launch manifest is delivered in this delta. Owner acknowledges these. Preserve old receipts and complete the authorized repair/build/manifest steps in the next genuinely released window; no repeated unchanged build or full simulation needed. The historical source-map/duplicate cleanup remains separate from these instrumentation gates.
