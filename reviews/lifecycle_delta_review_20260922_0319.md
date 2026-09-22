# Independent lifecycle delta review — 2026-09-22 03:19 cycle

Exact delivery `42385a23865035be5ba5078b10af274f200b25c4`, compared with `5fa7154`. Scope: `lab_prepare` interval consumption and `lab_load` diagnostic demotion, distinct identities and event filtering. Root/another reviewer own anchor/status/clock-domain decisions. No model, server, verifier, native reference, remote posting or whole test suite was invoked. Owner files were not edited.

- `experiments/live_ab/lab_prepare.py` SHA-256 `d5d5e92fa55eb9dfb5a2fa15a530e606e9956d568b583b2b026350b5aea6ef63`.
- `experiments/live_ab/lab_load.py` SHA-256 `5d0e0af1b9731ef1fdb2da499090d69937e400f86a05b907c4c6fcbad999e6b5`.

## Decision

**Accept these bounded implementation repairs. No material concurrency-arithmetic counterexample was found in the targeted checks. This does not accept an actual server lifecycle receipt or authorize a reference sweep/live collection.** The new function checks a declared observation contract; this delivery does not supply the independently pinned server-side lifecycle producer, source-event provenance, or a reconciled clock domain. Those are the already required next evidence, not a new testing architecture.

## Independent deterministic checks

To avoid importing worker modules or starting their threads, extracted the exact immutable AST definitions of `_finite`, `_coverage_verdict`, `_min_concurrency`, `windows_from_arrivals`, `classify_stream_chunk`, and the `ContinuousLoadObserver.observe` method, with their required constants. Ran only synthetic data and a threadless mock observation object.

Ten coverage cases pass their intended outcomes on the verifier interval [100,101]:

| Fixture | Verdict |
|---|---|
| Two distinct identities each covering [99,102] | valid, minimum concurrency2 |
| Two duplicate windows with the same identity | refused |
| One whole lifetime plus two distinct lifetimes handed off exactly at100.5 | valid under documented closed-interval convention |
| One whole lifetime plus second-lifetime windows ending100.4/restarting100.6 | refused |
| Second lifetime starts100.1 | refused |
| Second lifetime ends100.9 | refused |
| `lifecycle_complete=False` | refused |
| `evidence_kind=client_stream_arrivals` | refused |
| `concurrency_required=1` | refused |
| A missing window endpoint | refused |

Seven independent SSE classification fixtures exclude role-only, usage-only, finish-only, empty-content and malformed chunks; nonempty chat content and legacy completion text are counted as **content events**, not an exact token count. A four-arrival interleaved A/gen0, B/gen0 series creates two separate diagnostic windows. A threadless unhealthy-source witness returns active=False and no windows, preserves arrivals_seen=2, and declares certifies_coverage=False.

Source inspection additionally confirms generation names now include their source prefix (`source_id/gen_...`) and default sources receive generated IDs. Distinct string identity de-duplication prevents counting the same declared lifetime twice. Actual producer identity must still bind the server/process/request/slot instance; these scripted strings do not independently prove two real decoding requests.

## Remaining scope and one narrow wording repair

1. **Lifecycle evidence remains outstanding.** `lab_prepare.py:448–458` requires the global complete flag and later requires finite ordered windows and nonempty identities; `_min_concurrency` checks identities across endpoints and intervening segments rather than union coverage. This is correct conditional arithmetic, not validation of the producer's lifecycle assertion or its source pin. A future real receipt must connect these intervals to the already requested complete server-side events and clock convention. It must not merely relabel the diagnostic's client intervals `server_lifecycle`. No attempt outcome has been added by these repairs.
2. **An emitted diagnostic description still overclaims.** `lab_load.py` near the final `observe` return emits `means='each window is an interval throughout which the server is evidenced to have produced output, never idle for longer than max_interior_gap_s_measured'`. This directly contradicts the corrected module-level explanation: observed arrival gaps do not bound idle gaps or production lifetime. Replace the emitted description with “consecutive observed content arrivals grouped by generation; largest observed inter-arrival gap; no inference of continuous computation or server decoding lifetime.” The older `windows_from_arrivals` docstring also still says “continuous production” and that coverage “unions” its windows; bring those descriptions into agreement. The `evidence_kind` and `certifies_coverage=False` flags already prevent this diagnostic from passing `_coverage_verdict`, so this is an artifact-interpretation correction rather than a newly found false coverage acceptance.

The existing block on actual collection should remain until the concrete lifecycle/clock evidence is available. No additional simulation, broad test suite, timing experiment or new review gate is required by this bounded delta review.
