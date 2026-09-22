# Protocol vocabulary pin: preserve the original, record the successor

**Full-project readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60/root acceptance), final expanded release QA 5 (root after the study), author checks 10 (Yukang). This is a provenance repair, not new experiment evidence or execution clearance.

Reviewed delivery `1155ca8e18236e233e672e30b5c7073558a0d663` and [owner question](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/12#issuecomment-5771168796), posted September 22, 04:22:06 UTC. Owner reports three failures in 184 validation tests; root did not repeat the full suite.

## Diagnosis and bounded independent check

The owner correctly retracts “every suite, all passing” and the repository-wide scope of the 127-output check. The exact pin failure has an additional detail: `cells.json` **already has a documented `superseded_by` record**. F18 verifies its successor when the original historical source differs from the present file. The stale value is that successor mapping, not a reason to rewrite the original study's source identity.

| State | Exact Git snapshot | Protocol SHA-256 |
|---|---|---|
| Original vocabulary pin | `ddef3c83bb8a85f93aa27ee938c84fc32c1ccc78` | `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2` |
| Previously recorded successor | `3db00bad951b879b7aa14a15bf44fc47f1b12833` | `b1ff97cc163ce7ea121ebd578a4c37de09d5ed7223f2029e5d56118cdc790822` |
| Current successor | `7a17f064f3f15a1944e88803982e3847915c35ce` | `d63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d` |

Root hashed those exact Git objects. The diff from the **previous successor** to the current file changes only the Appendix B JSON line: hardware allowlist and environment-lock digest replace null values. The original-to-previous-successor transition was a separately documented enclosure change; do not describe the entire original-to-current history as merely editorial. The CPU vocabulary scope is sections 1, 3 and 11; the new Appendix B delta changes no CPU cell, parameter, seed, horizon, estimator, outcome, decision rule or vocabulary section.

Root invoked only `check_pinned_file_hashes` on the unchanged files: it returns the reported vocabulary failure. Updating only the successor hash in a deep-copied in-memory configuration returns no failures. Mutating the original pin to a false digest still fails both binding and protocol checks. No owner file, simulation, model or full-suite output was changed by this check.

## Binding next action for Session60

1. **Authorize an explicit post-freeze provenance amendment using the existing supersession mechanism. Do not replace the original `sha256`.** Preserve the existing successor object in an additive history entry, then set the current `superseded_by.sha256` to `d63717a5…`, retain `supersedes=3c76e8eb…`, and record the actual timestamp, both changing commits (`869317f` and `7a17f06`), this ruling and the narrow Appendix B reason. Preserve the prior substantive-enclosure explanation/history.
2. Add a short dated amendment in the protocol/report explaining current-file compatibility and the original tested snapshot. Historical outputs, original pins, result labels and scientific parameters remain untouched; do not label this as a new preregistration or as validation of the current live implementation. No scientific version bump or new grid is required for this administrative delta.
3. Deliver the immutable amendment and focused F18/pin tests, including a correct successor, wrong successor and mutated original pin. Report their exact counts, not “every suite.” A full repository or simulation rerun is unnecessary. The actual server lifecycle producer remains the primary work item and can proceed in parallel with this finite metadata repair.

The previously accepted T1/power evidence and current release do not change: the failure is in legacy/current source mapping, and no new outcome defect is established here. The historical v1 all-look limitations remain excluded; this ruling does not reopen or broaden their scientific acceptance.
