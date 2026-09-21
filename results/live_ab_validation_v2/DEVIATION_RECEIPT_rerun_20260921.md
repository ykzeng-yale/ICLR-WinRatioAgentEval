# Deviation receipt: the broader comparison rerun of 2026-09-21

**Status: OWNER-REPORTED DEVELOPMENT ATTEMPT. Not delivered evidence, not validated evidence,
not calibration, not a coverage rate.** Filed per the root's 06:35 and 07:19 instruction:

> "Preserve any surviving logs/config/seed/usage/timestamps in a separate deviation receipt; if
> outputs were overwritten during restoration, record exactly what is unavailable. Do not
> reconstruct missing observations or rerun merely to recreate them."

Nothing below is reconstructed. Nothing was re-run to produce it.

---

## 1. What was attempted, and what went wrong

I re-ran `vcompare` over a broader all-look scope **into an output directory that already held a
committed receipt**. The tool wrote its outputs over the deposited files. I noticed, and restored
the directory from `HEAD`.

The restoration recovered the committed bytes exactly. It did **not** preserve the rerun's own
outputs, because they were the thing being overwritten and nothing had copied them elsewhere first.

**The defect was mine and it was procedural, not a tool bug.** `vcompare` wrote where it was told
to write. The rule adopted afterwards — *never re-run into a directory holding a committed
receipt* — is now enforced in code for the new entry point: `vpanel.run_panel` refuses a non-empty
output directory (`tests_panel.py::test_it_refuses_to_overwrite_a_deposited_receipt`). It is not
yet enforced in `vcompare`, which is recorded here as an open gap rather than described as fixed.

## 2. What I reported from that attempt, and what backs it

| reported figure | surviving artifact |
|---|---|
| ~39,800 drain looks | **NONE** |
| 51 disagreements | **NONE** |

**These two numbers have no surviving artifact of any kind.** They exist only in my own report of
the run. They are therefore not evidence, not reproducible, and must not be cited, aggregated into
any index, or carried into the paper or supplement. I am not re-running to recreate them, per the
root's instruction, and I am not reconstructing them by inference from the committed receipts.

Checked for surviving traces rather than assumed absent:

* `git stash list` — empty.
* `git fsck --lost-found` — one dangling blob, `9380442497586385`, **163,886 bytes, a PNG**, not a
  comparison CSV; the three dangling commits predate this and are unrelated. The overwritten rows
  were never staged, so they never became a git object and are unrecoverable by construction.
* No `.log` file from the run survives in `results/` or `experiments/live_ab_validation/`.
* Scratchpad holds no copy of the rerun output.

**What is unavailable, stated exactly:** the rerun's `comparison_vs_live_ab.csv`,
`comparison_defects.csv` and `comparison_summary.json`; its seed and config block; its wall-clock
timestamps; its resource usage. All of it. No partial recovery.

## 3. What survives, intact and verified

The committed receipts were restored to their committed bytes and **no tracked file under
`results/live_ab_validation_v2/` is modified or deleted**.

*(Stated that way deliberately. My first version of this check asked whether `git status` over the
directory was empty, and it returned **False** — not because any receipt had been touched, but
because this receipt and the guard-v2 demonstration are new untracked files. Recording that False
would have implied the deposited receipts were disturbed, the opposite of the truth. The check now
excludes untracked additions and names what it tests.)*

| receipt | commit | look rows | defect rows | `drain_look` rows | `comparison_vs_live_ab.csv` sha256 |
|---|---|---|---|---|---|
| `comparison_v2` | `9f8ea06` | 22,523 | 198 | 0 | `41dcab8c36279a9b…` |
| `comparison_v2_alllook` | `65e957e` | 24,115 | 0 | 1,592 | `086b63be3b8309b6…` |
| `comparison_v2_alllook_oracle` | `65e957e` | 24,115 | 204 | 1,592 | `324cfbd4ead4e9b0…` |

Summary digests: `37b784acd35e8108…`, `41150423 5e6cfedc…`, `21727c5c326db22c…` respectively.

The root independently verified the original committed receipt intact; this table is the owner-side
record of the same fact and does not substitute for that verification.

## 4. Scope discipline

* The **24,115 matched-policy looks** and **1,592 non-final drain looks** in the table above are the
  delivered, root-bounded-checked figures. They stand on their own committed artifacts.
* The **39,800 / 51** figures are withdrawn from circulation as unsupported. They are recorded here
  only so that the attempt is not silently absent from the record.
* This receipt authorizes nothing. No full grid, no calibration panel, no live trial.

## 5. Open gap left deliberately

`vcompare` still accepts an output directory that holds a committed receipt. Repairing it would
change the tool that produced the delivered receipts, so it is **not** being changed in the same
delivery that depends on them. Recorded for a scoped decision.
