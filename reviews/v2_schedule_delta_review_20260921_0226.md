# V2 schedule delta: bounded independent review

September 21, 2026. Exact candidate **d8b2a4d3141f0180473761671d3ffa57437225ad**, compared with **db930d7dc3bac0ae1644170433f769b5d3875e84**. Scope: the new `vgen.py`/`vrun.py` scheduler, deterministic witnesses and decision reporting. Source was exported from Git into the outer scratch directory named below. No full grid, model, host/resource study or contributor test suite was run. No owner/shared files or Git state were changed.

**Bounded PASS for the primary tick-batched drain repair and tested decision-time reporting. The finest sensitivity has an independently reproduced impossible-state defect and a reporting-state limitation; do not call that sensitivity validated. This is not full-v2 freeze approval.**

## Primary checks independently passed

`adapter_tick_sums` extends the event difference array through the drain; `completion_tick_states` constructs completed-prefix and completed-set states on every tick. `vrun.build_series_v2:506–545` now includes ticks1 through `N_max+W`, retaining the enrolled denominator after the cap. The declared primary atomically applies all events sharing a tick. The source accounts for elapsed-cost enclosure breakpoints as well as reveals/completions; this review's direct fixtures exercised complete/unrevealed states rather than exhaustively checking every partial-cost boundary.

I independently executed the following exact-source cases:

- Both prior baseline witnesses now pass at horizons1,000 and2,000. V1 returns no decision; v2 CPREFIX and NAIVE deploy at ticks1,010 and2,010 respectively and record the zero-truth exclusion. `tau_prefix` remains1,000 or2,000. The tests use deterministic in-support sequences, not newly drawn simulation paths.
- The separate ADAPTER timing witness is repaired: 500 neutral pairs complete immediately, 400 positive pairs complete at1,010, and100 neutral pairs at1,200. V2 records deployment at1,010 with .10 unresolved and `decided_at_finalization=False`; it separately retains final unresolved fraction0. V1 first reports deployment at1,200 with unresolved0. This tests the distinction that the previous monotonicity argument missed.
- A separate five-pair mixed-completion fixture was checked against direct definitions on **205 ticks**. Both primary baseline indexes agree at every tick, and ADAPTER lower/upper bands for both scores agree with direct prefix sums. No RNG was called.

`evaluate_trial:738–769` separates enrolled prefix, elapsed tick, decision-state resolution and finalization resolution. Nondeciders still report their actual finalization state. Fixed-horizon summaries use the last state at/before that horizon's tick (`772–790`), so they remain enrollment-horizon summaries rather than accidentally using the drain endpoint. Truth remains the known constant law mean; schedules do not change its definition. These are substantive fixes, not evidence of actual-live calibration or full-grid reproduction.

## Remaining sensitivity defects/limitations

### 1. CPREFIX sensitivity inserts unreachable intermediate prefix states

`vgen.completion_event_states:694–715` claims to implement the declared event order, and even the exact union over every admissible tie order. It actually emits **every** k from1 to the terminal completed prefix, dated at the running maximum resolution tick. A completed prefix can jump over k when later pairs were already complete; the skipped values are not necessarily reachable under any ordering of the events at that tick.

Independent three-pair witness: resolution ticks `(3,2,3)`, so delays `(2,0,0)` are permitted SHORT values. At tick2 pair2 is complete and the prefix remains0. At tick3 the stated ascending-position order completes pair1 then pair3, producing prefixes **2 then3**. The function emits `(tick3,k1)`, `(tick3,k2)`, `(tick3,k3)`. **k1 cannot occur under any tie order**, since pair2 was already complete before tick3. Its synthetic score/band can therefore create a crossing not achieved by the claimed process. The primary `completion_tick_states` is unaffected. Fix the event ledger for the named sensitivity or relabel it as an artificial all-prefix envelope, with corresponding estimand/event limitations; do not equate it with the declared legal event schedule. The same false union claim appears in `PROTOCOL_V2.md:114–116`.

### 2. Finest decision-state summaries still use end-of-tick state

`evaluate_trial:761–764` passes only the tick to `_look_fractions`; that helper (`584–617`) counts every event completed/revealed by that tick and caches by tick. If a finest baseline fires partway through a tick's ordered completions, its unresolved/revealed/certification fractions therefore describe **the end of the batch**, not the selected sub-tick state. This is a source-confirmed mismatch with a claim of fractions at the first sensitivity decision. It does not affect the primary, whose decision look is explicitly the end of the batch. Preserve sub-event identity/state if those sensitivity summaries are required, or label them as end-of-decision-tick diagnostics.

Under finest, ADAPTER deliberately remains tick-batched (`build_series_v2:515–517`). Nested intervals justify equality of ever-crossing events through each tick, and the first crossing's integer tick is preserved under an enrollment-first order. They do not justify equality of sub-tick resolution state. Describe the sensitivity as completed-baseline event refinement with batched ADAPTER, rather than a common all-event first-decision-state comparison. Also qualify the remaining blanket “Not one deposited ADAPTER number…” wording at `PROTOCOL_V2.md:95`; the independently passing repaired timing witness demonstrates why coverage-event invariance is narrower than all-summary invariance.

## Acceptance boundary and receipts

The root may accept the bounded primary-scheduler repair above while holding sensitivity claims and full freeze acceptance. No full-grid rate, resource estimate, test-total claim, live/CPU pin alignment or full enclosure proof was independently reproduced in this task. A corrected sensitivity need not change seeds, alpha, margins, horizons or the already specified primary batching. Preserve v1 and the exact amended versions.

Exact outer scratch: `/Users/yukang/Documents/Codex/2026-09-17/i-x20/work/v2_schedule_review_20260921_0226/`. Files `snapshot.json`, `schedule_checks.py`, `schedule_checks.json` preserve the exported hashes and deterministic receipts. Only this report and that scratch were written. Report ownership returned to root.
