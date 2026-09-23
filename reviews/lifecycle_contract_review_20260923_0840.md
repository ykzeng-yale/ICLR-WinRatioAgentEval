# Lifecycle acquisition-contract review — September 23, 08:40 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded package QA 5 (root), and author checks 10 (Yukang Zeng). Accepted CPU validation and its paper/package integration remain complete and unchanged. Next milestone is completion of the bounded preparation repairs and immutable receipts, followed by the costed preparation plan and explicit working-branch freeze review. This contract audit adds no scientific evidence or readiness credit.

Reviewed immutable head `5841d6ed28f1e8dfc038f6ec7b8da8e304b5c4c1`, substantive source `11837b7`, against `6676b5c`. Scope is contract selection, declared source/binary identity, typed sidecar fields, and retained process return code through the actual coverage consumer. The receipt predicate, early-return retention, C++ producer, and supervisor implementation are separate review assignments. Evidence: `reviews/evidence/lifecycle_contract_review_20260923_0840.json`.

## Accepted field-contract repair

The new selector no longer lets an absent producer field itself request legacy treatment. A nonempty expected manifest naming a legacy patch selects `legacy`; any other nonempty manifest selects `repaired`; no manifest selects `unbound`. Under `repaired`, both `sidecar_failures` and retained process outcome must be non-boolean integer zero. The outcome is supplied by the caller, rather than inferred from seal contents.

I exercised the actual `lab_lifecycle.observe` followed by `lab_prepare._coverage_verdict` on closed temporary copies of the immutable smoke's two records and seal, with controlled manifest/field/outcome changes. The verifier used the named POSIX domain and the complete supplied historical host/boot provenance; this is not a fresh remote measurement. A one-second verifier interval lies strictly inside both recorded inner windows.

The following repaired-contract cases refuse coverage: absent sidecar count; count `false`, `0.0`, string `"0"`, null, -1, or 1; and absent process outcome, 93, 1, -9, `false`, `0.0`, or string `"0"`. Exact integer zeros pass the control. A **retained exit 93 invalidates an otherwise perfect zero-count seal**, including when the manifest selects legacy. Observations retain the supplied outcome across JSON serialization. The underlying copied files remain byte-unchanged. No manifest and an empty manifest also refuse; they do not certify by receiving a default exemption.

These checks close the named reader-side refusal requirement when the caller supplies the outcome. They do not establish that a production supervisor captured and durably retained it, or that the C++ producer actually returns 93 under failure. Those source/caller questions remain with their assigned reviewers and root.

## Contract-selection findings and root decisions

**1. Legacy scope is currently v1–v4, wider than the specifically preserved v4 acquisition.** Independently recovered all six patch revisions from Git bytes. `LEGACY_PATCH_SHA256` exactly matches v1 `261a54db…`, v2 `984f47df…`, v3 `4c8b647d…`, and v4 `2c52078f…`. V5 `0e79199a…` and current v6 `8e2d1c6b…` are not on that list. Full digests, byte counts, and source revisions are in the evidence JSON.

The retained smoke manifest names v4 `2c52078f8a541134661eb7ac997114892c7baf68541f9d4be664366d43e85f6a`, and its saved receipt has process exit 0. Its unchanged successful-reader control remains readable with `sidecar_failures_reported=false` meaning unknown, preserving the existing conditional engineering acceptance.

A controlled manifest mutation to **each** v1, v2, or v3 digest also selects legacy and permits the v4-shaped log to pass coverage without the sidecar field or a retained exit. This is a selector witness, not evidence that any older producer emitted those bytes: v1 in particular predates the token/sequence/seal additions. A source digest alone has not established a matching historical acquisition or binary. Root explicitly narrows the compatibility exemption to the actual saved v4 smoke. V1–v3 remain preserved/readable diagnostic history and do not receive a blanket certifying exemption. The current selector needs that finite correction; no older acquisition or loaded rerun is requested.

**2. Strict field validation is not source/binary binding.** The owner deliberately makes an undeclared patch select `repaired` rather than legacy. That is safe against obtaining the missing-field exemption, but it does not satisfy the separate pinned source/binary obligation. In the actual coverage path, the same valid records with `sidecar_failures=0` and retained exit 0 pass when:

- the manifest has no `patch_sha256`;
- the manifest names an unknown patch (`f` repeated 64 times);
- the manifest omits `binary_sha256`; or
- the manifest supplies an unrelated binary digest (`a` repeated 64 times).

Host, boot, instance/token, intervals, and counts remain valid in those controls. The output already labels binary/patch values echoed metadata; its `producer_bound=true` therefore means the checked identity relationship, not independent source-to-binary verification. This was an existing binding limitation, but the new compatibility selector now relies on that metadata to choose failure-channel requirements.

Root explicitly requires refusal for missing/invalid selected patch and binary digests, with actual artifact agreement enforced at the trusted launch boundary. Passing strict seal fields cannot supply that missing provenance. An unknown declaration alone remains unverified until matched to the selected source/binary contract. Root owns the supervisor wiring that supplies this binding before coverage certification. This is the existing production-binding requirement, not a new containment rule or request for another loaded run.

## Verification and handoff

**29 bounded scenarios** reached the actual reader and coverage consumer with expected outcomes; **two narrowly selected owner tests passed**. The first audit fixture omitted verifier provenance-source labels and correctly refused; adding the complete supplied historical provenance fixed the fixture before evaluating the contract cases. That initial refusal is retained in the evidence as an audit-fixture correction, not a product failure.

Accept the typed repaired-field checks, independent retained-exit refusal, no-manifest refusal, and exact historical digest accounting. Root has resolved the two policies above; Session60 must implement those finite selection/binding repairs alongside the separately reviewed producer and supervisor requirements. Native execution, source/binary correspondence, process capture durability, or trial authorization is not established by this report. No server, model, native fixture, sandbox, network request, broad suite, owner-file edit, or commit was performed.
