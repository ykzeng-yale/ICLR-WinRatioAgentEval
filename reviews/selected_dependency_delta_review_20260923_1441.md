# Late selected-dependency delta review — September 23, 14:41 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: prospective study and root acceptance (10 points, Session60/root), expanded release QA (5, root), and author checks (10, Yukang Zeng). This module review earns no scientific milestone credit.

Exact delivered head: `71ff4dc6434a1fa994f01a9c045608ca45dd3f89`; source: `6b83860f128e1cc6a103d1955047b8e58ab29789`; receipt `SELECTED_DEPENDENCY_CONTRACT.json` timestamp **14:49:04 UTC**. Source and tests were extracted by exact `git show` into an isolated temporary directory; no merge or owner/shared edits were performed. The unused `lab_common` import was replaced by an inert module during the isolated dictionary tests.

**Disposition: accept the tested static graph scaffold, not a completed selected-dependency gate or proof of candidate closure.** The owner explicitly reports that the gate is not wired into `run_smoke`, source/patch/build binding is not implemented, and dynamic backend selection remains unresolved. Preserve those limits. No native candidate metadata or library bytes were independently read in this review; the owner's nine-member/dlopen finding remains reported evidence.

## Independently checked subset

Both receipt hashes match:

- Module: `fc24f4e98a162f449b6a45f846271ce2b96447b98c0d5afcc5510539dc43ea82`.
- Tests: `6324ce507b7dfe142e913220effdc61d71162c20af6581c8551165fae0338390`.

All **15 supplied dictionary tests passed once**, with **0 failures, errors or skips**. They demonstrate finite static traversal, non-system member byte comparison, named system dependencies, and refusal for the supplied missing, changed, unexpected, wrong-path, unreadable or unresolved cases. Dynamic-reader errors and dlopen-without-policy are refused when that callback is actually supplied. These tests do not establish that a caller's `bounded:true` declaration is true in a real selected environment.

Exactly **three additional pure/mocked probes** were used. They identify these ranked deltas before production integration:

## 1. Verification silently drops the dynamic assurance from derivation

Freeze the supplied synthetic graph using a dynamic callback identifying its backend as a dlopen importer and a declared bound. Change the callback's prospective answer to an unresolved dynamic selection. `verify_closure` cannot take that callback or a current dynamic policy: it calls `derive_closure` without either argument. The observed re-derivation has **`dynamic_loading.checked=false`**, makes **zero** dynamic callback calls, yet returns **`verified=true`** for the static members.

This is separate from the already acknowledged fact that `bounded:true` is only a caller assertion. Even whatever dynamic assurance preparation carried is discarded at stage two. A frozen checked result must not become an unchecked successful verification.

**Required delta:** carry the selected dynamic-loading scope into preflight, independently check the relevant selection/environment and compare it with the frozen evidence. Refuse when that check or the bound is unavailable; do not fix this by merely copying the old Boolean. Keep this gate unwired/unusable for acquisition until the required preparation and preflight obligations are satisfied.

## 2. Unsupported dependency metadata is omitted instead of refused

A mocked successful `otool` output contained an `LC_REEXPORT_DYLIB` reference to `@rpath/libreexport.dylib` and an `LC_RPATH` of `@loader_path`. No native command ran. `macho_dependency_metadata` returned **an empty `load_references` list** with no error. Passing that metadata into derivation yielded **`resolved=true`, member_count=0**, even though the referenced non-system target was absent.

The parser recognizes only `LC_LOAD_DYLIB`, `LC_LOAD_WEAK_DYLIB` and `LC_RPATH`; unsupported dependency-bearing commands can disappear from the requirement. Consequently the broad claim that unreadable/unresolvable metadata always fails closed is not established by the current parser.

**Required delta:** support the dependency forms in the selected artifact format or declare a restrictive supported-format contract and refuse unsupported dependency commands/malformed relevant blocks. Do not treat an omitted parser result as evidence of no dependency. A finite synthetic parser control suffices; no candidate execution, rebuild or expansive platform audit is requested.

## 3. Reference text conflates distinct parent edges

The synthetic root reaches `/a/parent.dylib` and `/b/parent.dylib`. Each parent names `@loader_path/helper.dylib`; both corresponding helper files exist and each reference resolves uniquely in its own parent context. `derive_closure` keys members by the bare reference string, so the second edge is rejected as “the same reference resolves to two different paths ... ambiguous.” It reports `resolved=false` despite two distinct, specified parent contexts.

This is a **conservative false refusal**, not a launch bypass. The current representation is not fully edge-keyed: source/loader context is part of an edge's identity, while `required_by` is only a single stored value.

**Necessary modeling delta:** preserve parent/load-context identity when deriving and comparing edges, or explicitly limit the accepted format and refuse unsupported contexts as such. Do not call two distinct parent references one ambiguous edge. This can remain a restricted-domain refusal while the higher-priority verification/parser issues are repaired; it does not justify weakening closure requirements.

## Handoff limits

The owner receipt accurately keeps launch wiring and source/patch/build binding open. The supplied `bounded:true` control validates behavior under a declared assumption only; it neither validates the candidate's backend search nor enumerates dynamically selectable members. Root owns the selected-backend/source decision and answers the owner's environment question separately. This review does not independently endorse that proposed environment setting.

Evidence: `reviews/evidence/selected_dependency_delta_review_20260923_1441.json`. Counts: **15 synthetic tests + 3 targeted probes**. External guards recorded no native/process/network/signal/wait attempt. **No `otool`, `nm`, candidate executable, model, server, native build, owner-current artifact, pipe or sleep was used.** No unchanged whole-project suite or historical audit was repeated. Next owner action is the bounded verification/parser repair with an explicit context contract, then the existing preparation-derived freeze and launch binding work under root's disposition.
