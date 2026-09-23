# Server lifecycle instrumentation — the patch, and what it is evidence of

**Authorized by root, 2026-09-22 04:02** (`reviews/preparation_root_disposition_20260922_0402.md`):
*"Implement the already authorized server lifecycle producer now. Write the narrow source patch in
an isolated owner checkout of llama.cpp `4fea119de30f6a923992780f6fd5ccb0bee5d47d`; preserve the
original build and active shared service."*

| | |
|---|---|
| patch | `experiments/live_ab_serving/live_ab_slot_lifecycle.patch` |
| sha256 | **see the version table below** — this row named `261a54db…` for four revisions after the file had stopped having that digest |
| base revision | `4fea119de30f6a923992780f6fd5ccb0bee5d47d` |
| built | **NO.** Not compiled, not linked, not run. |
| original checkout | **untouched** — `git status --porcelain` empty, no worktree metadata added |

## Version history — additive, and the correction that produced it

**This record pinned `261a54db…` while the patch had been through four further
revisions.** A provenance record naming a digest its artifact no longer carries is the
same defect class as a stale successor pin: it reads as a binding and is not one. The
digests below were recovered from `git cat-file` on each commit that touched the file,
not from memory, and no earlier row is edited.

| v | sha256 | commit | what changed |
|---|---|---|---|
| 1 | `261a54db560d…` | `1d669d6` | the producer root authorized: four transition points, clock named per record |
| 2 | `984f47df65b0…` | `99e1805` | run-token echo, per-record `seq`, static-destructor seal, `.error` sidecar, `n=1` while instrumented |
| 3 | `4c8b647de674…` | `31c22fd` | three contract repairs; independent `fflush`/`fclose` checks |
| 4 | `2c52078f8a54…` | `3f3968d` | the seal `fprintf` result actually captured — root found I had claimed this repair in a commit message without making it |
| 5 | `0e79199aeb88…` | `c8b3bd9` | the best-effort failure channel reports its own failure — **superseded, never built; its hunk headers did not parse** |
| 6 | `8e2d1c6b9e07…` | *this change* | process-level refusal (root's ruling), and every hunk header recounted so the patch applies ordinarily |

### v5 did not parse, and root found it

Root, `reviews/evidence/lifecycle_producer_review_20260923_0800.json`:
`git apply --numstat` and `git apply --check` both returned **rc 128, "corrupt patch at line
283"**; `git apply --recount --check` returned **rc 0**. That pair is the whole diagnosis: the
hunk *bodies* match the pinned preimages, and only the `@@` arithmetic was wrong. I had
edited a hunk body and not its header, and said in the same delivery that I had not verified
application — root verified it and it did not apply.

Two things go wrong after a body edit, not one: the hunk's own counts, **and every later
hunk's new-side start offset**. v5 declared `+181` where the body held 212 lines, and the
following hunk still started at 2019 instead of 2050. A counts-only fix would have produced a
patch that parses and applies in the wrong place.

`experiments/live_ab_tools/patch_recount.py` now recomputes every header from the body and
asserts **no body byte changed**; receipts `results/live_ab/PATCH_RECOUNT_v5.json` and
`…_v6.json`. It caught a second round of drift when v6 added an `#include`, which shifted
every subsequent hunk.

**What is verified here:** the patch parses without `--recount` (`git apply --numstat`, which
reads the patch only), and plain and recounted numstat agree. **What is not:** that it
applies to the pinned base tree — this host has no llama.cpp checkout. Root's
`--recount --check` rc 0 is the standing evidence that the bodies match.

### v6: process-level refusal, replacing v5's stderr channel

Root, 2026-09-23 08:00, answering the question put to it: *"Root chooses process-level refusal
for unrecordable producer failure. Failure to persist the sidecar must produce a deterministic
nonzero process outcome, including after final seal formatting/flush/close; do not depend on
another log write or an unbounded stderr flush. Avoid reentering normal static-destructor exit
handling."*

v5 reported on stderr and carried a counter in the seal. Both are **writes that can themselves
fail**, and root observed that the supplied supervisor does not drain the pipe — so neither is
an outcome. v6 exits **93** (`LIVE_AB_EXIT_UNRECORDABLE`) via `_exit`, which runs no `atexit`
handler and no static destructor and therefore cannot re-enter the seal writer that called it.
The diagnostic is one bounded `write(2)` to fd 2, not an `fprintf`/`fflush` pair, so a blocked
stderr can neither stall nor swallow the refusal. Whatever was already durably written stays
written.

The reader requires a **retained** exit status under the repaired contract
(`lab_lifecycle.process_outcome_problem`): a readable seal full of zeros beside a retained exit
93 refuses, because the refusal fires exactly when no further write can be trusted and the log
cannot be the witness to it.

**v6 is SOURCE ONLY and NOT BUILT.** No binary corresponds to it.

**The retained smoke evidence stays bound to v4 `2c52078f…`** and is not reinterpreted.
`results/live_ab/SMOKE_LAUNCH_MANIFEST_smoke_4167e395ccfd.json` pins that digest because
that is the version that produced the retained log, and root's instruction stands: *"these
witnesses are in the smoke report; do not repeat a loaded smoke to fix them."* The retained
log was re-read through the repaired reader and still parses with no seal problem and two
windows — verified, not assumed.

**v5 is SOURCE ONLY. It is not built, and no binary corresponds to it.** The binary built
from an earlier version was already stale before this change and remains so.

### v5: what it repairs

Root, 2026-09-23 03:48: *"Make producer failure detectable by the supervisor/process when
the best-effort sidecar itself cannot be written."*

`live_ab_note_write_failure` opened `<log>.error` and discarded every result —
`fopen` could return `nullptr` and the function simply returned, and `fprintf`/`fflush`/
`fclose` results were never examined. On a full disk a terminal write failure was therefore
**completely invisible**: no sidecar line, and nothing anywhere else recording that one had
been attempted. v5 checks each step and, on failure, reports on two channels that do not
depend on the sidecar: a `live_ab_sidecar_failures` counter carried **in the seal**, and a
line on **stderr**, which the supervisor captures. The seal field is the one number the
sidecar cannot carry about itself — if the sidecar could be written there would be no
failure to report.

The reader treats `sidecar_failures` as **optional but strictly checked**: absent means an
emitter that predates the field, recorded as `sidecar_failures_reported: false`, an unknown
and never rendered as a zero; present means it must be a non-boolean integer zero.

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
