# Provenance amendment: the vocabulary pin's successor mapping

**2026-09-22.** Authorized by root at 04:27 UTC, `reviews/protocol_pin_disposition_20260922_0422.md`:
*"preserve the original pin; record an explicit post-freeze provenance amendment … Do not replace the
original `sha256`."*

**This is an administrative successor-mapping repair.** It is **not** a new pre-registration, **not** a
scientific version bump, **not** a re-run, and **not** validation of the current live implementation.
No scientific parameter, seed, horizon, estimator, outcome, decision rule, result label, original
receipt or execution pin changes.

## The three states of the pinned file

`experiments/live_ab/design/protocol_FINAL.md`, read for **sections 1, 3 and 11** (the vocabulary
scope):

| state | git snapshot | sha256 |
|---|---|---|
| **original pin — UNCHANGED** | `ddef3c83…` | `3c76e8eb…` |
| previous successor — **preserved in history** | `3db00bad…` | `b1ff97cc…` |
| current successor — **recorded now** | `7a17f064…` | `d63717a5…` |

## Two transitions, not one

The original → previous-successor change was the **separately documented enclosure change**
(coordinator ruling 60; item 5, the hierarchy enclosure, was completed). Its ruling is preserved
verbatim under `superseded_by.prior_successors[0]`.

Only **previous-successor → current** is the Appendix B delta: the configuration block gained
`"hardware_allowlist": ["arm64-darwin"]` and
`"environment_lock_sha256": "842a7a19…"` in place of nulls, synchronising it with `config.json` under
the three-way verbatim contract. It touches **no** CPU cell, parameter, seed, horizon, estimator,
outcome, decision rule, or any of sections 1, 3 and 11.

**Correction to my own report.** In my 04:22 correction I described the whole original-to-current
history as *"one editorial line"*. That **flattened two distinct transitions** and root said so. The
enclosure change was substantive; only the Appendix B delta is narrow. The amendment records them
separately and this file exists partly to say that the earlier description was wrong.

## Current-file compatibility, and the snapshot actually tested

The grid recorded in `cells.json` ran against the **original** snapshot `ddef3c83…` / `3c76e8eb…`.
Nothing here asserts it covered any later version. The successor mapping states only that the file
has since moved and by what, so that a reader comparing today's file against the pre-registration can
see the difference rather than discover a silent mismatch.

## Why the amendment is not written into `protocol_FINAL.md`

Because that file **is** the pinned object. Adding a dated note to it would change `d63717a5…` the
moment it was written, invalidating the successor mapping being recorded. The amendment therefore
lives here, beside the pre-registration that carries the pin.

## What the F18 mechanism does with this

`check_pinned_file_hashes` enforces *"no pin is SILENTLY stale"*: a supersession passes only when it
is recorded explicitly **and** its recorded successor matches the file on disk. Three focused tests
cover it — a correct successor passes, a wrong successor fails, and mutating the **original** pin
still fails. After this amendment `tests_validation.py` reports **184 tests, OK (expected
failures=2)**, with the original pin untouched.
