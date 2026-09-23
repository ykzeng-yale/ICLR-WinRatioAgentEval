# Field, response state and ledger closure — September 23, 14:41 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: prospective study and root acceptance (10 points, Session60/root), expanded release QA (5, root), and author checks (10, Yukang Zeng). These engineering closures earn no scientific milestone credit.

Reviewed exact source `20aada0139683d7f9bce024d48331888aece7e45` at main/live `358f04d3db830d13e0600c81ce22d67499b4cb69`. Scope: explicit-null/oversized temperature refusal, the decoded-HTTP200-list response state, and common denied-process ledger enforcement. Owner receipt `PROTECTED_PATH_COMPLETION.json` is timestamped **14:17:41 UTC**. Its source/harness hashes match the delivered bytes.

**Disposition: accept all three named closures within this bounded scope. No remaining defect from these exact witnesses.** This is not acceptance of the whole supervisor, all possible response schemas, resource cleanup or selected dependency binding; those have separate ownership.

## Exact tests and observed boundaries

Four changed/relevant owner tests passed, with **0 failures, errors or skips**:

- explicit-null temperature refusal;
- unrepresentable temperature refusal;
- decoded non-object response preservation;
- deliberate deny-ledger control.

Three additional actual-main fixtures independently checked the persisted receipts and operation boundaries:

| Fixture | Observed boundary and persisted result |
|---|---|
| `temperature=null` | **0** mocked Popen invocations, **0** mock POSTs, status1, exactly one refusal receipt with invalid manifest and no child started. |
| `temperature=10**400` | **0** mocked Popen invocations, **0** mock POSTs, status1, exactly one refusal receipt naming the unrepresentable number. No escaping overflow. |
| HTTP200 decoded body `[]` for both requests | One mocked child, two mock POSTs, status1 and one receipt. Both rows retain `response_received=true`, `delivery=response_received`, `body_wrong_shape`, and unusable usage. Unknown-delivery count is **0**. |

The Popen counts were observed at the fixture's actual `fake_popen` call boundary, not inferred solely from receipt flags. For the list-body case, both closed `.response` files were independently read before cleanup: each is exactly **2 bytes**, `[]`, SHA-256 **`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`**. Raw retention and receipt state agree. Known response receipt is no longer turned into unknown delivery for this exact prior failure. No broader claim about all nested response field shapes is made.

## Denied commands now fail the test despite production handling

An additional negative-control unittest used the existing fixture with a mocked post hook invoking its patched Popen on `['unexpected-review-command']`. Both attempts were denied and recorded; production handled them and returned an ordinary refusal. The **common `tearDown` then produced one expected unittest failure**, explicitly naming the two denied ledger entries. There were no unittest errors or skips. This proves the violation now survives production exception handling and becomes a harness failure; it does not rely only on the new healthy-case assertion.

The deliberately injected ledger test sets `_expect_denied=True` only in its own fresh testcase instance, asserts that a nonempty ledger would fail the empty-ledger check, and verifies its expected command entry. There is exactly **one** opt-out assignment in the module. Ordinary cases, including the independent caught-command control, do not carry that opt-out. The previously accepted process-denial behavior remains intact: no unexpected command reaches actual process creation.

## Evidence limits and counts

Source SHA-256: `644aaeacabc3932d3fcf78761ec8fbf882f0cde3ec51b0d72816180cedb16a30`. Harness SHA-256: `98ab1972aca555e97a8d6f5df9c5242495de8ead21da320a95b5b9ac14638491`. Both equal the owner receipt. The owner's full **30-case OK** remains owner-reported; this review ran only **4 selected owner tests + 3 additional actual-main fixtures + 1 expected-failure harness control**.

All child/HTTP/signal/thread/time interactions used mocks and additional external deny guards. The tests retained real serialization against fresh temporary closed files. **No real child, HTTP/network call, signal, model, build, pipe or wait was executed; no outer deny guard was reached.** The expected negative-control failure was entirely in the fixture's in-memory process-denial ledger. The already closed byte-corruption test, unchanged timing cases and old 26-receipt audit were not repeated.

Evidence: `reviews/evidence/field_state_ledger_closure_20260923_1441.json`. No owner/shared-file edit or commit was made. Next work remains the separately assigned resource-cleanup, selected-dependency, configuration/finite-plan and lifecycle obligations under root's current disposition.
