# C++ lifecycle failure-channel review — September 23, 08:00 delivery

Received head `79af3a748d0f9b965dff06ca029e501769d4b77c`; producer source change `c8b3bd915fac09679dbf2f0afe745280675bd108`; reviewed against `08d5987`. Scope: the delivered C++ patch, its failure/terminal-seal flow, patch applicability and build provenance. The Python reader is reviewed separately.

**Disposition: source-only improvement received, producer closure not accepted.** Two finite corrections remain: the patch is syntactically malformed as delivered, and failure of the sidecar still lacks a dependable process-level refusal when it happens after the seal snapshot. No native build, binary execution, model, server, download or network action was performed.

## Accepted source and provenance subset

The sidecar writer now checks its `fopen`, `fprintf`, `fflush` and `fclose` results. Flush and close remain independent calls. It increments an atomic `live_ab_sidecar_failures` counter and includes that counter in the seal. These additions can expose an earlier sidecar failure when a later valid seal can be written. They do not establish a successful native implementation because the patch is unbuilt.

Independently recovered all five patch SHA-256 digests from repository history; the new `PATCH_RECORD.md` table matches. Current v5 is **`0e79199aeb886e063f7d758b34566eb6dcd3061ee12fb427424475f953f14c43`**, 15,472 bytes. The retained smoke manifest remains bound to v4 **`2c52078f8a541134661eb7ac997114892c7baf68541f9d4be664366d43e85f6a`** and its recorded launcher/library closure. It must not be relabeled as a v5 run. The additive source/version correction is accepted; no v5 binary or runtime receipt is delivered.

## 1. Regenerate the malformed patch

Both `git apply --numstat` and ordinary `git apply --check` fail with:

```text
error: corrupt patch at line 283
```

The insertion hunk at patch line70 declares `@@ -734,6 +759,181 @@` but contains **212 new-side lines**, 31 more than the stated count. This is a packaging defect, independent of the C++ behavior.

An existing local source snapshot was available at `work/server0459`; its two git blob hashes exactly match the preimages named in the patch (`b6835e43459e3e9f1ea951e9f96f9ade22074cba` for server-context and `9894f5f06fb050fa6e1e278a01509be35e00733e` for server-common). **Read-only** `git apply --recount --check` succeeds there. Thus the hunk content matches the retained preimages when Git disregards the erroneous counts; this is not acceptance of the malformed delivered file or of compilation. No source file was changed.

**Next action:** generate the patch from the intended edited source against the pinned base, retain ordinary `git apply --check` output, and refresh the exact patch digest/version provenance additively. Do not make downstream users rely on `--recount`, or claim the present file applies cleanly.

## 2. Close terminal failure reporting independently of the seal and stderr

The following is a **static control-flow witness**, not an executed C++ fault injection:

1. The destructor formats a complete seal containing `write_failures=0` and `sidecar_failures=0` at lines250–258.
2. Its subsequent `fclose` reports an error at line269 after complete seal bytes may already be readable. A terminal error is acquisition-invalid even if the byte string looks complete.
3. `live_ab_note_write_failure(..., "seal_close")` increments the in-memory failure count. If `<log>.error` cannot be opened/persisted, it also increments the sidecar-failure count.
4. These increments happen **after the seal bytes were formatted** and cannot alter its zero counts. The handler tries `fprintf(stderr, ...)` and `fflush(stderr)` without checking either result, then returns. Nothing in the delivered patch makes the process exit nonzero for this condition.

The two new channels are therefore not sufficient in this terminal case: the seal is already closed and the only remaining message is best-effort stderr. The analogous last-seal flush failure has the same ordering issue. Earlier failures are covered by a successfully written later seal; this distinction is why the terminal case remains open.

The supplied `experiments/live_ab_serving/run_smoke.py` redirects stderr into `stdout=PIPE` but never reads, drains or saves that pipe, and calls `proc.wait` before any such drain. Thus `PATCH_RECORD.md`'s statement that stderr is captured should not be read as **retained evidence** through that runner. A pipe can fill, and the new synchronous `fprintf`/`fflush(stderr)` can block while the parent waits for exit. This is the already requested bounded supervisor/failure-retention obligation, not a request for another loaded smoke or a general supervisor redesign.

**Next action:** make failure to persist the sidecar produce a deterministic nonzero process outcome, including from the final seal path, without depending on another successful log write or unbounded stderr flush. A small explicit fatal path is sufficient; avoid recursively entering ordinary exit/static-destructor handling. Retain the process outcome in the supervisor and drain/save its diagnostic stream within the existing absolute deadline. An immediate nonzero termination can legitimately sacrifice a final seal: that acquisition must refuse, and available original observations must remain retained. Test this with bounded model-free failure injection when the corrected native artifact is built under the standing resource rules; no new model generation is needed for this repair.

## Exceptions, concurrency and scope limits

The new counters are atomic; no additional producer thread, join or application mutex was added by this delta. The existing lifecycle mutex still serializes record writes. The seal writer still runs as a static destructor and does not itself drain or join server workers. This review does not infer a new drain guarantee from adding atomic counters.

`live_ab_note_write_failure` still allocates a `std::string`; an allocation exception in the implicit-noexcept seal destructor would terminate the process rather than provide a normal seal. That is not a new defect introduced by this delta, and it is not a substitute for explicitly handling the ordinary non-throwing I/O failure above. Likewise, aborting/crashing cannot be advertised as proof that no seal bytes were ever written: a terminal failure can occur after those bytes. The supervisor's retained nonzero exit must invalidate that acquisition independently of an apparently complete seal.

No native behavior, sanitizer result, exception execution, actual pipe blockage or installed-binary correctness was claimed or measured. The only executed checks were **three patch-parser/application dry-run commands** (two ordinary failures, recount diagnostic success), hunk accounting, two source preimage hashes and five version digest recoveries. Detailed evidence is in `reviews/evidence/lifecycle_producer_review_20260923_0800.json`.

Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. This source repair does not earn study-completion credit. Remaining: Session60 prospective study and root acceptance (10 points), root final expanded package QA (5), Yukang Zeng's author checks (10).
