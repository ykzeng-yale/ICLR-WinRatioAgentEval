# V7 producer fatal-path closure — September 23, 09:19 cycle

Exact received head: `549b60f99c383cb2a9128f52f953c7a2d9d48559`; substantive change `9ce153e349f5da51088c174a29e0040c04cbb272`; base `42cc49f`. Scope: ordinary patch application, immediate fatal exit and retained source/build provenance.

**Accepted source closure.** The v6 pre-exit diagnostic that could block on a full stderr pipe has been removed. No remaining defect was found in this finite source/application obligation. V7 is still **source-only and unbuilt**, so this is not native-runtime or installed-binary acceptance.

## Independent verification

The fatal helper's entire executable body is now:

```cpp
(void) what;
_exit(LIVE_AB_EXIT_UNRECORDABLE);
```

The macro remains **93**. There is no write, formatting, flush, allocation, lock or other diagnostic operation between entry to this helper and `_exit`. The helper remains `[[noreturn]]`, and sidecar-open/persistence failures continue to call it, including terminal-seal failures. It does not recursively enter normal static-destructor/atexit handling. This closes the specific full-pipe defect demonstrated in the preceding review; repeating that unchanged OS-level witness was unnecessary.

Current patch SHA-256: **`88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184`**, **17,188 bytes**. Independently checked:

- All **six** hunk old/new counts agree with their bodies.
- Ordinary `git apply --numstat` returns **0**, reporting **10 + 288 = 298 additions**, no deletions.
- Ordinary **`git apply --check` returns 0 without `--recount`** against existing `work/server0459` preimages. Their full git blob hashes remain `b6835e43459e3e9f1ea951e9f96f9ade22074cba` and `9894f5f06fb050fa6e1e278a01509be35e00733e`, matching the patch's expected original files. No file was patched or built.
- `PATCH_RECOUNT_v7.json`'s final digest and ordinary numstat agree with this independent check. Its retained before/after arithmetic records are consistent with the corrected delivery.

Evidence: `reviews/evidence/lifecycle_producer_review_20260923_0919.json`. Executed checks were two read-only parser/application commands, source/preimage digest accounting and fatal-body inspection. No full suite, new pipe experiment, actual native producer binary, build, model, server, download or network action occurred.

## Scope and next work

The owner source-version record correctly distinguishes v7 from the retained smoke, which remains bound to v4 **`2c52078f8a541134661eb7ac997114892c7baf68541f9d4be664366d43e85f6a`**. Do not relabel that smoke or an existing binary as v7. This cycle's ordinary application check supplies the missing independent packaging evidence; another application-approval round is not needed.

The subsequent build must retain its exact base/patch/library/launcher provenance, and the supervisor must retain the actual nonzero process outcome under its existing bounded failure-handling contract. An exit status being available is not the same as its receipt being durably retained. Those runtime/integration obligations remain separately tracked; this review does not reopen closed source defects, authorize a new loaded smoke, or clear trial episodes.

Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. This source closure earns no study-completion credit. Remaining: Session60 prospective study and root independent acceptance (10 points), root final expanded package QA (5), Yukang Zeng's author checks (10).
