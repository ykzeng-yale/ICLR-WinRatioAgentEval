# Retention, response state and deny ledger review — September 23, 14:03 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: prospective study and root acceptance (10 points, Session60/root), expanded release QA (5, root), and author checks (10, Yukang Zeng). Implementation repairs earn no scientific milestone credit.

Reviewed source `1e58d3b041c3310c1df19aa5cefaf0cad5040af2` at main `176e682f5688ee4c786d4840fb3ac7f40351a677`. Scope is only response byte equality, response-receipt versus decoding/shape state, and common test-harness deny-ledger enforcement. The owner correction receipt is timestamped **13:48:34 UTC**. Root/other reviewers own cleanup, manifest and library-binding decisions.

**Disposition: accept the complete-byte comparison repair. Response-shape accounting and universal deny-ledger enforcement remain incomplete.** These are the two previously identified obligations, narrowed by the accepted subset below; no timeout or parked-request case was repeated.

## What ran

Four relevant new owner tests passed with **0 failures, errors or skips**: same-length response corruption, JSON parse exception after HTTP200, the healthy no-denied-attempt case, and the explicit ledger-recording control. Additionally, two helper controls and three actual-main witnesses were run. All process, HTTP, signal and thread interactions were mocks; extra outer audit/fallback guards denied actual subprocess/socket/signal operations, real monotonic fallback and sleep. **0 actual child, HTTP/network, signal, model, build or real-wait operations occurred; no outer guard was reached.** Only fresh temporary closed-file serialization was real.

The source and harness digests agree with `PROTECTED_PATH_AND_CONSUMED_FIELDS.json`: runtime `2d2ec42beccc9e8b41790a6e22cba245ae7412cccba86f4b040e3b77f5b17fb1`, harness `d0b3ad15882c3bda749a484c647af5ce17aad8e3200c268a7e20491caa3e616b`. The full 25-case owner OK result remains owner-reported; this review independently ran only the four named cases and five additional bounded controls/witnesses.

## Accepted: actual closed-file byte mismatch is refused

`_persist_response_bytes` now compares `persisted == raw`, records the received digest separately, and refuses a mismatch. The ordinary helper control stores `ABCDE` completely. The independent fault closes its response writer first, then changes the first stored byte to `X` without changing length; subsequent `Path.read_bytes` is unmodified. The actual file is therefore `XBCDE`, with an independently checked differing digest, and the helper reports `complete=false` plus `retention_mismatch`.

The same closed-file fault was applied to both response artifacts during actual-main execution. Both are measured incomplete and the supervisor returns status1. This independently accepts the real byte comparison and receipt/gate wiring; it does not rely solely on the owner's read-spy substitution fixture. Ordinary complete retention remains accepted.

## Remaining 1: decoded shape failure still erases known response receipt

The new parse-exception test passes: when `r.json()` itself raises, `body_unparsable` is retained, `response_received=true`, delivery stays `response_received`, and usage remains unknown. That specific case does not cover the prior shape witness.

**Reproduction:** drive the existing actual-main fixture with `bodies=[[], []]`; both mocked HTTP responses have status200 and raw body `[]`. Both raw response artifacts are retained completely with SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`. JSON decoding succeeds, but `d.get('usage')` at `run_smoke.py:1041` raises `AttributeError` because `d` is a list. The outer handler at lines1053–1063 then overwrites both request rows to **`response_received=false`, `delivery=unknown_server_receipt`**, despite the received and retained response. The receipt counts two unknown deliveries and status1.

**Next repair:** retain transport/response facts monotonically once observed. Validate the decoded response shape before field access, and classify later decoding/shape/extraction failures as received-response errors with unusable usage. Only failures before response receipt should claim unknown delivery. Preserve raw bytes and the specific shape error. The owner receipt's blanket claim that a shape failure now preserves received state needs a scoped additive correction; the passing JSON-decode exception test does not establish it.

## Remaining 2: the deny ledger is not enforced for every case

Unexpected Popen remains correctly denied before any real process creation. The new healthy test checks `self.denied == []`, and the deliberate `stray_command` control demonstrates ledger recording. These are useful, but `_run` at `tests_supervisor_entry.py:352–354` still returns without a common assertion; the only empty-ledger assertion is in one healthy test at lines788–791.

**Reproduction:** call the actual fixture with a post hook invoking its patched `subprocess.Popen(['unexpected-review-command'])`. Both commands are blocked and recorded. Production catches their guard exceptions as request errors; `_run` returns an ordinary status1 refusal with **two denied ledger entries and no harness assertion**. No command executes and no outer OS guard is reached. This is the same remaining test-enforcement gap, not a surviving execution fallback.

**Next repair:** check the violation ledger at every case's completion, including caught production exceptions. Give the one intentional negative control an explicit expected-violation assertion/opt-out so it proves enforcement rather than weakening it. A common final assertion or cleanup hook should make the caught-transport witness fail as a harness isolation violation. The receipt's claim that the suite asserts an empty ledger at completion is currently broader than the implementation.

Evidence: `reviews/evidence/retention_state_guard_review_20260923_1403.json`. Counts: **4 owner tests, 2 helper controls, 3 additional mocked actual-main cases**. Existing timeout/unfinished-worker limitations, the old 26-receipt audit, historical artifacts and release state were not reopened. No owner/shared file edit or commit was made.
