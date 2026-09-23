# Producer fatal-path and patch-application review — September 23, 08:40 cycle

Exact received head: `5841d6ed28f1e8dfc038f6ec7b8da8e304b5c4c1`; substantive delivery `11837b770583f85c6dbea2c4d5f3604935019622`; base `6676b5c`. This review is limited to the v6 lifecycle producer patch, ordinary application and its pre-exit diagnostic. Root separately owns supervisor integration and build-location decisions.

**Accepted:** the malformed-patch defect is closed, and failure to persist the sidecar now routes to an explicit `_exit(93)` function instead of returning normally. **Still open:** the diagnostic write can block before that exit. One small source correction remains; no additional loaded smoke is warranted.

## Patch and provenance acceptance

Current v6 SHA-256 is **`8e2d1c6b9e07b8a990c63c98e11b9eabbab5f6d7f4f6f30fd341c37e727d4ba7`**, 16,791 bytes. All six hunk headers have correct old/new line counts. Ordinary `git apply --numstat` returns 0, reporting 10 additions in `server-common.h` and 280 in `server-context.cpp`. Ordinary **`git apply --check` returns 0 without `--recount`** on the existing `work/server0459` source preimages whose full blob identities were verified in the previous review. This command is read-only; no source was patched.

The repair preserves the terminal failure call sites: failed sidecar open or persistence reaches `live_ab_die_unrecordable`, including when called after the final seal's formatting/flush/close. `_exit` avoids reentering normal static-destructor/atexit handling. These are accepted source properties, not native-runtime validation.

The version history correctly preserves v5 as unbuilt/superseded and identifies v6 as **source-only, not built**. The retained smoke still pins v4 **`2c52078f8a541134661eb7ac997114892c7baf68541f9d4be664366d43e85f6a`**. Neither ordinary patch application nor this review upgrades that run to v6 or certifies an installed binary.

## Remaining defect: a bounded-size blocking write can stall exit

The fatal function formats a small diagnostic, calls `write(2, ...)` on fd2, and only then calls `_exit(93)`. It does not ensure fd2 is nonblocking. Therefore the comment and `PATCH_RECORD.md` claim that a blocked stderr cannot stall refusal is false: avoiding stdio buffering does not remove a blocking descriptor's capacity wait. The earlier supervisor's undrained pipe is one concrete way this condition can arise.

A tiny isolated Python-child witness exercised the same POSIX `write`-then-`_exit` sequence with an **84-byte** diagnostic. It did not compile or execute llama.cpp. The parent saw a separate “before” marker from the child before timing its completion; it intentionally left the stderr pipe unread.

| Case | Observed outcome |
|---|---|
| Empty blocking stderr pipe, diagnostic then exit | Exited **93** |
| Blocking stderr pipe filled to **65,536 bytes**, diagnostic then exit | Still running after **350 ms**, blocked before exit; only this test child was killed and reaped |
| Same full blocking pipe, immediate exit without diagnostic | Exited **93** |

The bounded kill in the witness prevents the review itself from hanging. It does not mean the current producer has such a safeguard. This is a direct counterexample to the “bounded write cannot block” assertion, rather than a new generalized security requirement. The claim that the whole helper is async-signal-safe is also unnecessary: the required property is reaching process refusal without blocking on diagnostics, and the helper is called on ordinary I/O failure paths.

**Rank 1 next owner action:** remove the pre-exit diagnostic and take immediate `_exit(93)` on unrecordable failure. The retained exit status is the intended evidence, so that diagnostic is optional. This is the smallest correction and avoids introducing descriptor-mode or signal-handling machinery. Preserve already written log bytes, refresh the patch digest/version record additively, and rerun ordinary patch application plus a bounded model-free full-pipe refusal control. Correct the prose claiming that a short `write` is inherently nonblocking. Root's existing supervisor exit-status retention/drain requirement remains separate and active.

Detailed evidence: `reviews/evidence/lifecycle_producer_review_20260923_0840.json`. Verification was **two ordinary parser/application checks**, six-hunk accounting, patch/manifest digest checks, and **three isolated pipe cases**. No native producer build, native llama binary, model, server, sandbox program, network action, full suite or owner-file edit occurred.

Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. These source/application checks earn no study-completion credit. Remaining: Session60 prospective study and root acceptance (10 points), root final expanded package QA (5), Yukang Zeng's author checks (10).
