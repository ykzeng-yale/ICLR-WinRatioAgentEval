# Pin-test entrypoint closure — September 22, 2026, 05:37 cycle

Reviewed repair `7c9818edfdecabad4756e4cd228582f5a2d3be87`, delivered head `5759c7f0f11e34a2d4f0d69e63f62bb17adb71e3`, against `reviews/pin_amendment_review_20260922_0459.md`. Read-only source/config comparison and mocked test discovery; no full suite, simulation, model call or owner edit.

**Close the pin-test entrypoint finding.** The `__main__` block now follows every class, including `PinSuccessorAmendmentTests`. Both invocation routes discover **190 tests**:

- Direct script: actual `runpy.run_path(..., run_name='__main__')`, with only `unittest.TextTestRunner.run` mocked to count rather than execute;190 discovered, mock exit0.
- Imported module: actual `unittest.defaultTestLoader.loadTestsFromModule`;190 discovered, none executed.

This is independent confirmation of discovery parity, **not** a claim that this reviewer reran190 tests. The six focused pin tests already passed in the preceding review; their bodies and the pin-check implementation are unchanged, so they were not repeated.

`cells.json` at `5759c7f` is byte-identical to accepted amendment `690317e`: original pin `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2`, current successor `d63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d`, complete previous-successor history and all scientific fields preserved. `PROTOCOL.md` now points explicitly to `cells.json` for full digests; amendment prose still quotes abbreviated identities. No new pin or scientific acceptance is required for this relocation.

## Earlier narrow follow-ups remain separate

The delta `f9c1137..5759c7f` contains no owner coding/airline report changes and no removals of the nine proven raw/log duplicates. No owner historical-wincs source-map delivery is present. Thus the previously authorized additive historical source-map and narrowly scoped duplicate untracking remain outstanding; no data-byte audit was repeated. These are documentation/storage follow-ups, not incomplete experiments or grounds for delaying lifecycle work.

**Readiness remains75% (change0); bounded-v1 90%.** Remaining: prospective study10(Session60/root), final expanded QA5(root), author checks10(Yukang). This closes a test-discovery defect only; root and the separate reviewer adjudicate actual lifecycle/build readiness.
