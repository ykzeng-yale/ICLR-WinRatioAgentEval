# Server lifecycle instrumentation — the patch, and what it is evidence of

**Authorized by root, 2026-09-22 04:02** (`reviews/preparation_root_disposition_20260922_0402.md`):
*"Implement the already authorized server lifecycle producer now. Write the narrow source patch in
an isolated owner checkout of llama.cpp `4fea119de30f6a923992780f6fd5ccb0bee5d47d`; preserve the
original build and active shared service."*

| | |
|---|---|
| patch | `experiments/live_ab_serving/live_ab_slot_lifecycle.patch` |
| sha256 | `261a54db560ddfccf1f1541361905686177069c4993f2b80e9830a9144631e29` |
| base revision | `4fea119de30f6a923992780f6fd5ccb0bee5d47d` |
| size | 144 lines; 2 files, **101 insertions, 0 deletions** |
| applies cleanly | **yes**, verified by `git apply --check` against a pristine tree at the base revision |
| built | **NO.** Not compiled, not linked, not run. |
| original checkout | **untouched** — `git status --porcelain` empty, no worktree metadata added |

## The four transition points, exactly

| field | where it is stamped | bracket |
|---|---|---|
| `t_assigned_us` | `launch_slot_with_task`, immediately after the task is bound and before any prompt work | **outer** start |
| `t_prompt_start_us` | `stats.t_start`, upstream, when prompt processing begins | **inner** start |
| `t_gen_last_us` | `stats.t_gen_last`, upstream, last generation step | **inner** end |
| `t_released_us` | `release()`, at `t_last_used`, before `reset()` clears the stats | **outer** end |

Every timestamp is a raw `ggml_time_us()` reading — `clock_gettime(CLOCK_MONOTONIC)` in
**microseconds** on this POSIX build (`ggml/src/ggml.c`, POSIX branch). The clock is **named in every
record** rather than assumed by the reader, because on this host `time.monotonic()` and
`CLOCK_MONOTONIC` are 694 s apart (`results/live_ab/CLOCK_DOMAIN_FINDING.json`).

**The consumer uses the INNER pair.** Root: *"Retain conservative verifier outer brackets and
lifecycle inner endpoints."* `lab_lifecycle.window_from_record` emits
`[t_prompt_start_us, t_gen_last_us]`, which is strictly narrower than the true occupancy, so an
attempt it covers was covered under any reading. A test asserts the outer bracket would have
certified an attempt the inner one refuses.

## Why an emitter and not an endpoint

`/slots` carries **no timestamp field at all**; `/metrics` is server-global and cumulative; the
response `timings` object is durations only; and `stats.t_start` never leaves the process. A slot's
occupancy is an interval with **two transitions**, and only the process making those transitions can
report them. Polling any of the above would produce samples, which root ruled cannot establish an
interval.

## What a record means

**An occupied decoding slot.** Not uninterrupted hardware utilization — the record says so in its own
`means` field, and root said so twice. Scheduler pauses inside an occupancy are part of the
operational regime.

## Failure handling

`complete` is true only when all four transitions were observed **and** are ordered. Anything else is
emitted with `complete: false` and **refused by the reader**, which sets `lifecycle_complete: false`
on the observation — and the consumer then **refuses coverage and retains the attempt**, never
excluding a task. A record is never dropped silently: refusals are counted and their reasons carried.

## Off by default

The emitter writes only when `LIVE_AB_LIFECYCLE_LOG` names a file. Unset, it returns immediately and
the binary behaves as upstream. Writes are serialised under a mutex (slots release concurrently),
written until every byte is accepted, and flushed — a partially written record is worse than none,
because it would be read as a real one.

## What has NOT happened

No build. No model call. No server start. No weight download. The **model-free producer/consumer
fixture** (`ServerLifecycleProducerConsumerTests`, 9 tests) writes records in the emitter's exact
byte format and drives them through the real `lab_lifecycle.observe` and the real
`lab_prepare._coverage_verdict`. **That is a test of the contract, not of the server.** Building and
loading remain gated on the owner-host capacity check and root's finite plan.
