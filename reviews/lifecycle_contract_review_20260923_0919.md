# Lifecycle identity and process-outcome review — September 23, 09:19 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and its paper/package integration remain complete and unchanged. Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains bounded preparation closure, then the costed plan and explicit working-branch freeze review. These implementation findings add no study result, trial permission, or milestone credit.

Reviewed immutable head `549b60f99c383cb2a9128f52f953c7a2d9d48559`; substantive deliveries `9ce153e` and `450cc0b`; base `42cc49f`. Scope: `lab_lifecycle` identity validation, path parity, and retained process outcomes through the actual coverage consumer. The actual `run_smoke.main` path and native producer are separate assignments. Evidence and full commit identifiers are in `reviews/evidence/lifecycle_contract_review_20260923_0919.json`.

## Accepted repairs

**String/Path parity closes.** The same closed 1,094-byte lifecycle file, SHA-256 `f1b549c3a78484a285984817899c9019d803cfcbb75a9eb757188387861efbb2`, yields identical whole observations when passed as `Path` or string. Both routes retain the same real byte count/hash and produce the same coverage decision. The earlier string-route `AttributeError`/false-unreadable report is gone.

**Basic missing-identity and archival-version refusal closes.** With otherwise valid strict seal fields and retained exit zero, a missing patch, missing binary, or ordinary malformed digest (`bad`) now produces an unbound observation and refuses coverage. The four archival source digests (v1, v2, v3, and unbuilt v5) also refuse. The legacy set now contains only v4 `2c52078f8a541134661eb7ac997114892c7baf68541f9d4be664366d43e85f6a`. The actual saved v4 smoke remains readable with its retained process exit **0**, preserving the prior conditional engineering scope.

The new checks validate manifest fields; they do not measure the selected executable or establish source-to-binary agreement. The code explicitly retains that limitation. Trusted-launch artifact verification remains required and is handled by root's separate supervisor review.

## Two finite corrections

**1. Remove the newly introduced signal-success exception.** A declared stop request now overrides the earlier rule that every nonzero process exit invalidates acquisition. On otherwise valid records and strict zero-count seals, the actual reader and coverage consumer return valid for:

| Retained process outcome | Declared termination signal | Current result |
|---|---|---|
| -15 | 15 | valid |
| -9 | 9 | valid |
| +1 | -1 | valid |
| -1 | `true` | valid |
| -15 | 15.9 or string `"15"` | valid |

The last cases result from `int(expected_termination_signal)`, not a validated signal contract. Non-numeric string and mapping declarations raise `ValueError` and `TypeError` instead of returning a refused observation. These are saved-byte reader witnesses, not executed signal terminations.

The positive integer-zero control still passes. Undeclared -15, -9 while 15 is declared, a missing outcome, and reserved exit 93 refuse. A mapping such as `{"returncode": 0}` is not a supported outcome representation and refuses; the reader's successful outcome is a scalar integer. Returned observations retain the supplied raw outcome rather than rewriting it.

The owner's claim that healthy teardown necessarily yields -15 is not established by its evidence: the immutable engineering smoke recorded **0**. Sending or declaring a signal does not by itself prove that the producer completed its acquisition and failure protocol. No handler investigation or new native execution is needed to resolve the policy conflict.

**Root explicitly decides:** remove the success exception; every nonzero or unknown retained process outcome refuses. Keep the requested stop signal as diagnostic provenance only. This one correction also removes the arbitrary-sign/coercion/exception family above. Update the new owner test and receipt narrative that currently treat declared -15 as a successful control.

**2. Make the new digest check exact and typed.** The guard currently applies `str(value)` and `_HEX64.match` with `$`. Through the actual coverage path, both patch and binary identity separately still pass when supplied as a **64-digit integer** or as an otherwise valid digest **followed by a newline**. The former is silently converted to text; the latter matches before the final newline. These are finite residuals in the newly added usable-digest gate.

Require an actual string and a full match of exactly 64 lowercase hexadecimal characters, without normalization. This establishes the intended syntax contract; it does not replace actual artifact agreement at the trusted launch boundary.

## Historical scope and verification

The v4 selector remains digest-based, rather than authenticating the exact saved smoke manifest. A controlled different run token and binary digest claiming v4 still receive legacy treatment with no sidecar field or retained outcome. Root's prior exact-history wording was not sufficiently explicit to call this a separate new blocker here. Preserve the saved historical acceptance only; a future acquisition must not obtain an exemption by selecting the old v4 digest. Upstream selection/binding remains root's responsibility.

**30 bounded changed-case scenarios** were recorded: 28 returned observations reached the actual `observe` → `_coverage_verdict` consumer; two invalid signal declarations raised the documented exceptions. **Two selected owner tests pass**, including the test that currently encodes the rejected signal policy. Thus passing those tests is implementation evidence, not acceptance of that policy. All scenario source files were immutable copies or temporary mutations of saved records; supplied historical provenance was not presented as fresh host measurement.

No additional broad audit, server, native fixture, model, sandbox, network request, loaded rerun, owner/shared-file edit, or commit was performed. Session60 owns the two small corrections; root combines them with the separate supervisor/producer findings before preparation acceptance.
