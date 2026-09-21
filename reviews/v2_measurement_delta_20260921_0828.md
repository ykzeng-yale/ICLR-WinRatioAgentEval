# Bounded end-to-end measurement review — September 21, 2026, 08:28 cycle

**Exact source:** `0281eb21d1890cb58eeb1af3ee71cf352400df67` against `5336f8b0124b9aef0133e7facef268b8608b1e8c`; root's immutable export `work/v2_review_0828`. Scope: resource-only receipts, counts, output sizes/hashes, cap implementation, timing scope and deterministic fixed-horizon projection. **No primary/reference effect values or decision labels were inspected.** Gzip data were decompressed only to count bytes/lines and compute hashes, with no values displayed or analyzed. No timing, native/reference/model call or grid was rerun. Root separately owns code/pin correctness.

**Disposition:** Accept the delivered resource observation at its stated single-pass scope: the final two horizon runs account for 20 units, 80 trials and 160 reference calls, with matching output hashes and small observed resource use. It is **not a qualifying T1 execution ledger**: the actual measured horizon-2000 cost projects above the fixed 5400-second cap, the claimed parent cap is not implemented in the reviewed entry point, and discarded prior attempts remain incompletely accounted for. Preserve this useful observation; do not repeat it merely to repair wording or receipt fields.

## 1. Independently reconciled resource evidence

Both horizon receipts use namespace 1, C1/C2, indices 1000–1004, four trials/program, operational policy and the tick-batched schedule. Each reports ten program/horizon units, 40 trials, 40 H calls, 40 D calls and 240 reference rows. Combined: 20 units from ten seed-program identities, 80 trials, 160 reference calls, 480 retained reference rows. The four output-file hashes match the actual immutable bytes. Each gzip file contains 120 primary data rows; each reference file contains 240 data rows. These are structural counts, not outcome checks.

| Resource | Horizon 1000 | Horizon 2000 |
|---|---:|---:|
| Owner outer wall seconds, including the panel call | 2.5934406249 | 5.3073018333 |
| Inner loop seconds | 2.4657935845 | 5.1741954163 |
| Peak RSS bytes recorded | 70,926,336 | 72,351,744 |
| Compressed primary bytes | 1,671 | 1,620 |
| Actual decompressed primary bytes | **23,727** | **24,535** |
| Reference CSV bytes | 31,007 | 31,105 |

Outer total is reported as 7.9008317497 seconds; the sum of the per-horizon outer intervals is 7.9007424582, with approximately 0.0000893 seconds of outer overhead. The maximum recorded RSS is exactly 69 MiB. Data-file bytes sum to 65,403 (63.87 KiB); **all seven deposited files**, including receipts, total 99,631 bytes. Both are far below 200 MiB, but they describe different output scopes.

Receipt byte labels need correction without a new measurement. `uncompressed_bytes` repeats each gzip file's compressed size, and the aggregate `output_bytes_uncompressed_total=3291` is therefore false. Actual decompressed primary total is 48,262 bytes; including reference text, total uncompressed data bytes are 110,374. Correct those fields and label the 65,403-byte sum as data artifacts (the reference CSV is not compressed). Do not alter the original observations or output bytes.

## 2. The new observation changes the full-run planning conclusion

Use the measured **same horizon** 2000, without fitting any horizon exponent: 5.3073018333 seconds for ten programs gives 0.5307301833 seconds/program. Multiplication by existing tier program counts gives:

| Existing tier | Horizon | Programs | Direct wall-time projection | Versus 5400 seconds |
|---|---:|---:|---:|---|
| T1 | 2000 | 28,000 | **14,860.45 s / 247.67 min** | Above |
| T2 | 2000 | 16,000 | **8,491.68 s / 141.53 min** | Above |
| T3 | 2000 | 8,000 | 4,245.84 s / 70.76 min | Below |
| T4 | 1000 | 8,000 | 2,074.75 s / 34.58 min | Below |

These are deterministic extrapolations of a single observed C1/C2 mixture at the measured horizon, not guaranteed times for all cells or an independently measured grid. A fitted 1000-to-2000 scaling law is unnecessary. The receipt's blanket “not a basis for projecting the full grid” should be narrowed: it cannot certify full-grid resource use, but it **does** supply relevant planning evidence that the currently measured executable is too costly for T1 under the unchanged cap. The previous ~2044-second proxy omits important current work and must not remain execution authority.

Do not silently switch to T3 or increase the cap. Preserve the scientific tier/design while root makes the explicit pre-calibration resource/workload decision below. This review does not require a favorable experimental result.

## 3. Caps are observed to have been respected, not parent-enforced as requested

`vpanel.py:459–481` checks resources **before each trial**, inside the same worker. It has no parent watchdog, no subprocess timeout and no parent aggregation of the two horizon passes. A long native reference call cannot be interrupted by this check. Time starts after setup/pinning; the inner timer stops before output close/write. The reference buffer and final output/receipt bytes are absent from the byte cap (`sink.raw_bytes` covers primary only). There is no final cap recheck after the last trial and final writes. `completed_fully` consequently means no sampled pre-trial cap event, not that the entire operation was continuously within every cap.

The 7.9-second observed outer total and small output sizes are valid evidence that this delivered pass was not near the limits. They do not establish the requested 300-second parent-controlled safety mechanism for future work. No committed outer-driver source or parent enforcement record accompanies the aggregate receipt. Add that mechanism and test it with synthetic timeout/oversize cases; no need to repeat these observations solely to demonstrate guard code.

`_peak_rss_bytes` takes `max(self, reaped_children)` and calls it a process-tree peak. This is not simultaneous summed process-tree RSS, and unreaped child processes are absent. The measurement appears mostly in-process, so retain its reported RSS with the correct scope; do not upgrade it to a verified tree-wide peak. Host metadata records total RAM, load and free disk, not available RAM. Neither limitation calls for killing or modifying foreign workloads.

## 4. Full-grid guard is now called, but the measured ledger is not connected

`run_panel`'s `full_grid` branch (`vpanel.py:399–410`) invokes the actual guard before trial execution, fixing the previous outright bypass. It still reconstructs the **old saved primary smoke** and obtains resource pricing from the old reference/combined receipt loader, rather than converting this new measured panel ledger. The new receipt therefore does not make the current guard qualify T1; missing/mismatched identities should continue to refuse.

A qualifying projection must cover the normalized intended execution request, its exact verification mode, primary/reference calls, persisted outputs and actual storage strategy. Current reference output is still accumulated in `ref_lines` and joined at the end. Small-run 69 MiB is not a memory bound for T1's 672,000 reference rows. Either stream those rows or provide a deterministic full-size memory bound. Current `full_grid` also sets `caps=None`, leaving only preflight projection checks and no runtime cap monitoring in the panel loop. Bind the parent cap/counter implementation to the full-run entry point as well.

The reviewed measurement accepts `verify_policy=True` as a function argument, but that flag is **absent** from `PanelConfig.identity()` and `entry_point_pins`' workload configuration. Code pins alone cannot distinguish the expensive per-trial-verification run from a preflight-only run of the same file. Add an explicit pinned verification policy before interpreting any new timing.

## 5. Smallest scientifically explicit completion route

Source inspection supports an explicit **preflight-only policy verification** option: the conditional verifier (`vpanel.py:501–505`) calls `assert_operational_matches_policy` and increments check counters. It does not alter the already computed primary records, shared draws or H/D reference inputs. Current receipts count 420,080 checked pair states over 80 trials. That is a plausible substantial overhead, but its exact attributable time was not separately measured and should not be asserted.

If root accepts its already independently checked operational-policy witnesses as the preflight gate, retain them before each eligible run and disable redundant per-trial checking via a named, pinned mode. Keep the operational primary, both reference paths, all scientific coordinates and fixed caps unchanged. This is a documented execution-verification amendment, not an outcome-driven scientific design change.

After parent-cap and pin-binding fixes, authorize **one bounded pass** of that final preflight-only mode on the same existing 20 units, 80 trials and 160 reference calls. Compare persisted data hashes with the present verified-mode outputs, using decompressed gzip hashes if necessary, without examining effect values. The present decompressed primary hashes are `9dd82799d8df7e74b187e30795be14192e3726617d76a3126652646ff2ec6e44` (1000) and `d9fd343f7153acf0fd1b34c8bcb1dc057c2b8923f1ecf5b20e999792b18d425a` (2000). Reference hashes remain those in the immutable receipts. Keep current timing as a historical comparator; an extra verified-mode repeat is unnecessary unless a paired causal overhead estimate becomes an explicit objective. No broad timing sweep or full calibration/live run is licensed.

If the revised executable still projects above the cap, report that fact for root's explicit scoped decision. Do not infer permission to change tier or workload from a receipt's success flag.

## 6. Attempt accounting must preserve the disclosed first pass

`MEASUREMENT_RECEIPT.attempts.total=2` accurately counts the **two delivered final horizon passes only**. Its separate disclosure says an earlier pass on this design produced decision counts, those counts were seen, and the uncommitted pass was discarded before another pass. Therefore two is **not the cumulative execution-attempt total**, and “one pass initially” does not describe all work attempted. The current review did not inspect those counts or any other effect values.

Ask the owner to recover raw prior artifacts/logs if they remain available; otherwise preserve an explicit irrecoverability/deviation record with known timestamps, scope, code and counts, and unknown fields marked unknown. Do not fabricate the missing observations or claim they were retained. Reconcile all attempts and the exact reason for the repair/repeat, rather than retroactively labeling the earlier execution as nonexistent. Keep the owner's “influenced nothing” statement as a report, not independently verified fact. This provenance correction should not trigger another experimental rerun.

## Conclusion

The final delivered bounded measurement is independently reconciled as resource evidence; it is not a qualifying full-T1 ledger. The next gates are complete attempt accounting, actual parent/full-run cap binding, a pinned verification/storage policy, and—only if that execution policy changes—the one narrowly necessary resource pass. Remaining source/provenance acceptance belongs to root's parallel audit. No scientific-result integration, readiness increment or full-grid/live clearance is granted by this report.
