# Lifecycle identity and build decision — September 22, 2026, 05:37 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60, root accepts), final expanded release QA 5 (root), author checks 10 (Yukang). Next owner milestone is a built instrument and model-free native producer/consumer receipt, followed by the existing explicit prefreeze review.

Received main/owned head `5759c7f0f11e34a2d4f0d69e63f62bb17adb71e3`. Independently reviewed substantive delivery `7c9818edfdecabad4756e4cd228582f5a2d3be87`. Review acceptance is limited to the subsets below; neither head is a validated live-study result. [Owner status at 05:19:47 UTC](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5771584996): live episodes **0**, structural freeze **14/26**, nothing built or running. The latest reported capacity is a snapshot, not a reservation.

## Accepted delta and remaining defect

[Independent reader review](lifecycle_reader_delta_20260922_0537.md): **16 focused tests pass**. Accept tested identifier/transition validation, slot-based occupancy, same-slot overlap refusal, manifest-argument requirement and one-microsecond inward start contraction. These close the corresponding local reader witnesses. The fixture inserts identity fields not emitted by the delivered C++ patch; it tests the planned contract, not native producer interoperability. Update that fixture description with the producer completion.

One original provenance obligation remains demonstrably open: a foreign record set plus a matching foreign expected manifest still receives local observer provenance and passes a local verifier's coverage check. Require expected-manifest host/boot identity to agree with independently measured observer provenance before producing a certifying observation. Retain mismatch inputs and refusal, rather than excluding the attempt. Existing observer-to-verifier checks then complete this link. This is a finite repair to the existing clock/identity contract, not a new threat model or experiment.

[Independent pin-entrypoint review](pin_entrypoint_closure_20260922_0537.md): close the discovery defect. Both actual invocation routes discover **190 tests** using a mocked runner; no full suite was rerun. Original/successor/history pins and scientific configuration are byte-preserved in `cells.json`. Prior pin-amendment acceptance stands.

## Explicit producer design choice

**Use supervisor-issued identity echo.** This answers the owner's new design question, consistently with the trusted-launcher option in the [04:59 disposition](lifecycle_reader_and_build_disposition_20260922_0459.md).

The trusted launcher measures host/kernel-boot identity and persists the expected launch manifest before dispatch. That manifest binds a fresh run/instance identity to the pinned binary and patch. The producer receives the run/instance token and bound identity and echoes them into its records and closing seal. The consumer resolves the token against the persisted expected manifest and enforces its agreement with current observer and verifier provenance. Binary/patch identities belong to the actual launched artifact; they must not merely be arbitrary fields copied from a record. No second kernel-digest implementation inside the server is needed.

This establishes launch-session correlation under the trusted local producer/launcher path. It is not cryptographic attestation, tamper proofing or proof that a token cannot be invented. State that scope in the receipt.

The current reader only requires/compares host, boot and instance against expected metadata. Binary/patch pins are copied, not verified; acquisition sequence/count/seal validation and producer write-failure evidence are not implemented. They remain the already requested finite producer/consumer completion. Do not label `lifecycle_complete` or the passing Python fixture as full acquisition acceptance before those obligations are implemented.

## Finite next owner action

Finish the producer half, the manifest-to-observer bridge, existing write-failure/sequence/seal handling and the requested `n=1` enforcement as one buildable batch. Then perform the already authorized isolated native build after a fresh resource/shared-use check, with at most two compile jobs and the original installation preserved. Compilation is reversible; ordinary compile repairs/rebuild and a model-free native serialization/refusal fixture need no further root permission. No approval delay is introduced here.

Deliver the build's exact source/base/patch/binary/compiler/flags, launcher/library identities, exit status, retained output/failures, resource use and actual timestamps, followed by actual native producer bytes exercised through the consumer. The native fixture can use synthetic transition inputs and must be described as such; it does not certify actual loaded serving occupancy. Existing model-loading, serving/preparation and prospective prefreeze gates remain unchanged. No full grid, model call, duplicate worker or unchanged test suite is requested.

The ranked owner response was posted at **05:42:12 UTC**: [issue 11 design/repair/build decision](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5771753847). The owner has already confirmed a half-hour reporting cadence; no second automation or repeated cadence request is created.

## Evidence and release state

Accepted T1 **112,000**, coarse **80,000**, fine **48,000**, and ablation **32,000 unique paired coordinates** remain independently validated, integrated and packaged at `bfc467d1a1cac82bc60fe1ab5dc16cfe070c4892`. The 49-page article (13 main + 36 supplement), 38-entry source archive and 391-payload code archive are unchanged. The [project-wide experiment inventory](all_experiment_status_20260922_0415.md) remains authoritative for other accepted, excluded and deferred families. No new study outcomes or formulas were delivered in this delta.

The additive historical source-map and nine duplicate-file removals remain separate low-priority owner follow-ups already authorized; neither requires a rerun nor delays the instrument build. No scientific readiness credit is awarded for this implementation review. No paper/source/code artifact changed, so no redundant PDF rebuild or simulation was performed. The historical ICLR release remains preserved.
