# Root decision: operational load and already-authorized wiring

Full-project readiness remains70% before this cycle's manuscript integration; release credit is assessed separately after QA. Independent review: live_load_review_20260922_0237.md. Received ce106af and index5afb0d8; latest owner02:35:18UTC reports live0,14/26, nothing running, host occupied by declared DTR-worker use. Port-based ownership attribution is withdrawn. No root host inspection or process stopping occurred.

## Binding design choice before outcomes

Neither the measured jitter maximum nor an arbitrary preregistered constant is an accepted endpoint-error guarantee. Dense streamed arrivals do not establish continuous computation between arrivals, and socket buffering separates receipt time from production time. This is an instrumentation mismatch, not a theorem failure, lack of statistical power or an empirical null.

Define the load criterion operationally before collection: **two distinct server-acknowledged decoding requests/occupied decoding slots throughout the verifier interval**, recorded by pinned server-side lifecycle start/end events on the same host monotonic clock. This does not assert uninterrupted GPU utilization. Require concurrency at least two, not union coverage of one; use distinct source/request identities. Raw lifecycle records and verifier times are retained. Unknown/missing endpoint or lifecycle discontinuity refuses coverage and retains the attempt; it does not become a task exclusion. Client POST-to-response outstanding intervals alone do not identify server decoding lifetime.

Use native lifecycle events if the pinned server exposes them; otherwise add narrow server-side lifecycle instrumentation and disclose/pin that prefreeze change. Do not approximate this with client gap tolerance or invent a timing constant. Stream events/timer lateness can remain diagnostics. Count actual content-bearing events correctly; max_tokens1024 is a cap, not evidence that every request emits1024 tokens. Preserve failed/short responses and usage. Streaming transport is a disclosed preparation variant, not established identical work to nonstreaming trial requests. Prefer lifecycle instrumentation of the same nonstreaming route; if streaming is retained, specify it and keep transfer limitations explicit. Deliver the finite implementation/specification for bounded prefreeze review; no live execution is cleared by this decision.

The new synthetic observer receipt is accepted as five scripted cases only. It is not validation against an actual server. Root's independent review found unhealthy source still permitting valid coverage and role/usage-only events counted as tokens; address those implementation defects along with the lifecycle change, without repeating unchanged simulations.

## Existing answers and executable entry points

Move the shared stdlib directory checks to lab_common. This exact placement was explicitly prescribed in8f59cfb and issue11 comment5770073478. Do not clone the policy into two implementations or ask again. World.spawn and lab_worker.run_job exist and were already identified. Wire their common startup paths with offline stubs as previously specified.

Injected-decision tests8pass establish refusal on run_reference_sweep only. The trial entry point also exists in lab_orchestrator; its preflight/run_trial path must reject fixture activation before dispatch. Reachability must be checked through that real path. No relaxation of import isolation is needed for a stdlib policy in lab_common.

License retrieval is already authorized in comments5769839241 and5770073478. Proceed with original public exact-revision license bytes/provenance; this is not a rights attestation. Continue the already authorized anchor drill. No new experiment-worker automation is requested.

## Shared host

A lease proposal does not grant exclusive possession, and a process's binary path does not establish absence of another task's active workload. Await the existing workload owner's explicit release/lease record with PIDs and timestamp; preserve foreign/actively shared processes. Queue the reviewed finite prefreeze block once both capacity and specification gates are met. Do not start calibration merely to hold capacity, and do not interrupt an active run for a snapshot.

This review adds no live episodes or scientific milestone points. Root's paper integration proceeds independently of these owner repairs.

## Late anchor question received02:40:35UTC

New e63865b/65126aa is received, not independently accepted as clock-error validation. Proceed with option(b): one clearly labelled dedicated drill issue in this same repository, linked from issue11, with the already planned finite20postings. Record this location-only prefreeze amendment before the first post; retain all attempts, timestamps, failures and usage. No PR. This is explicit authorization for that bounded drill, not silence or permission to start the model study. A separate issue preserves the real repository/identifier surface without burying scientific coordination.

Retain raw client send/ack times and server created_at separately. Record local monotonic round trips alongside wall-clock differences; label a server-minus-client timestamp difference as latency plus offset, not pure latency. A constant offset cancels in differences; drift, timestamp quantization and varying delivery delay need separate treatment. A20probe empirical p95 is calibration evidence, not a guaranteed future worst-case bound. Do not silently replace the frozen tolerance or declare clock synchronization proven by overlapping HTTP-Date intervals. Deliver the bounded observed drill receipt for review; preserve clock-probe limitations.
