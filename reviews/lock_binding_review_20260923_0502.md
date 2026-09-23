# Incremental host-lock binding review — September 23, 05:02 delivery

Exact delivery reviewed: `a95ba08e9b21d00f73521f3f098a7ba0222bac29`; bounded delta from `cba87963`. The scope is production lock selection, fixture isolation, cross-checkout resolution, and the two immutable lock receipts. No model, server, sandbox program, owner-host canonical lock acquisition, remote posting or broad suite was run. Root reviews config/document synchronization separately.

**Disposition: accept the canonical default routing repair and the retained cross-wrapper receipt within its stated scope; do not yet accept production entry binding.** The remaining defects are implementation failures of the existing one-host-lock requirement, not a new scientific condition or evidence of actual contaminated trial outcomes.

## Accepted subset and tests

- Ran `python3 -m unittest experiments.live_ab.tests_lab_isolation.ExecutionLockConformanceTests -v`: **7 tests passed**, approximately 0.5 seconds. Canonical default paths now agree for T1–T4, the worker fallback and the sweep resolver; per-trial run locks remain separate.
- Independently exercised the actual worker token resolver with two different patched checkout/work roots but the same host pin. Both resolve `<HOST_WORK>/sandbox.lock` to `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/work/live_ab/sandbox.lock`. This closes the original checkout-relative token problem under a shared effective configuration.
- The actual `lab_worker.main` refuses a stale `<WORK>/T1/sandbox.lock` before calling `run_job`, while the canonical token reaches the stubbed `run_job`.
- Reviewed immutable `CROSS_WRAPPER_LOCK_CONTROL.json` (owner timestamp **04:09:33 UTC**) against its current producer source. Both held cases have the same recorded path, an acquired holder, the expected typed contender refusal, and the entire contender interval within the holder's acquired/released interval. Both no-holder controls acquired. Retain this as **two observed cross-wrapper exclusions and two successful controls**, supplied by the owner and independently checked for internal/source consistency. I did not repeat the acquisition experiment. It proves neither sandbox containment nor binding of every caller to that path.

Evidence for the following eleven bounded witnesses and receipt arithmetic is deposited in `reviews/evidence/lock_binding_witnesses_20260923_0502.json`.

## Blocking implementation findings

### 1. Production worker entry permits arbitrary non-token paths

`lab_worker.main` calls `assert_canonical_execution_lock` only when `_lock_kind` is `token` or `fallback`. Every other string is labeled `explicit_fixture_path` and bypasses the assertion; this is not limited to absolute paths despite the source comment.

Through the actual CLI-entry function with a temporary job JSON and only `run_job` stubbed:

- an arbitrary absolute temporary `other.lock` reaches `run_job` with that path and returns 0;
- `relative-other.lock` also reaches `run_job` and returns 0;
- neither job needs a fixture flag or an offline-only entry point.

The source-text conformance test currently asserts that this exemption exists. A path's textual form cannot establish that the process is an isolated unit fixture. The fixture classification is a local variable, not a durable execution-mode record; recording it would not make the production bypass acceptable either.

**Required repair:** bind/check every actual production job path against the same authoritative canonical path, regardless of token, absolute or relative spelling. Exercise the actual worker entry for positive canonical and negative stale/absolute/relative cases. Isolate unit tests by patching their canonical configuration/root in the fixture process, or by driving lower-level wrappers with temporary locks; do not exempt serialized inputs from production binding.

### 2. A configuration self-label bypasses the production sweep resolver

`resolve_execution_lock` honors any `execution_lock_path` when `bool(execution_lock_is_fixture)` is true. `lab_data.sweep_references` calls this resolver in its normal production path with no independent offline boundary. Through the actual sweep function, with provenance and task conversion stubbed and `_ExecutionLock` replaced by a stopping sentinel:

- an alternate path without the flag refuses before reaching the lock constructor;
- the same alternate path with `execution_lock_is_fixture=True` reaches the lock constructor;
- even the string `execution_lock_is_fixture="false"` reaches it because the check uses truthiness.

The sentinel stops before any acquisition or verifier call. Both containment routes also invoke this resolver directly. The existing `assert_no_fixture` only checks the unrelated injected-decision fixture key, so it does not establish a boundary for this new self-label.

**Required repair:** production resolvers/entries reject the lock-fixture override rather than allowing a serialized/configuration assertion to authorize it. Keep explicit temporary lock injection within an isolated test seam that cannot dispatch production. Exact boolean typing alone would still leave the production bypass.

### 3. Runtime configuration and cached harness configuration can select different locks

The sweep resolves against its supplied `cfg`. In contrast, `trial_paths`, orchestrator `_trial_paths`, job token resolution and `lab_worker.main` bind against cached adjacent-file `harness_config()`. The orchestrator builds jobs carrying `self.cfg['sandbox']` but does not pass that configuration to the lock constructor/resolver.

A bounded witness supplied a job whose sandbox block pinned a different absolute host work root. `lab_worker.main` accepted it and passed the cached harness root to `run_job`, without a configuration disagreement refusal. The supplied runtime configuration resolves to its other root through `resolve_execution_lock`; the actual worker token resolver still selects the cached root. Thus the shared token is only invariant when both consumers happen to use the same effective configuration.

This does not assert that the current owner's default config is already split. It shows the missing binding check when a supplied/frozen config differs from the adjacent cached file. **Required repair:** use one verified effective frozen configuration consistently, and refuse disagreement between the active job/runtime host pin and the trusted canonical host pin before dispatch. Do not silently select whichever copy a module happens to read. A mocked differing-runtime/cached-config case should fail closed; a common effective config across two checkout roots should remain valid.

## Receipt/reporting scope

`LOCK_TOPOLOGY_v3.json` (owner timestamp **04:05:49 UTC**) reports one distinct pathname, but its `two_workers_in_one_trial_share_a_lock` and `all_derive_from_trial_paths` fields are false because the AST check still recognizes only the previous source expression. Its `conforms_to_one_lock_file` verdict uses only the distinct count. The reporter's sweep expression also still derives from local `WORK_ROOT` rather than calling the new production resolver, and it renders with generic `tokenize_path`; executing its read-only resolver on this root checkout raises `UntokenizablePath` for the owner-host canonical path. The owner's checkout happens to make its old `<WORK>` display correspond to the new host pin.

Preserve v3 as historical evidence. After the finite entry fixes, issue one additive topology receipt using the same effective production resolver and host-token rendering, including actual worker entry rejection cases. Refresh the stale structural fields instead of equating the one-path snapshot with complete production enforcement. The valid existing cross-wrapper controls do not need an unchanged rerun to fix this reporter.

The owner-reported intermittent broader e2e failures are not localized by this review and are not silently counted as passes. No broader e2e rerun was performed.

Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. These changes do not earn study-completion credit. Remaining: Session60 prospective study and root acceptance (10 points), root final expanded release QA (5), Yukang Zeng's author checks (10).
