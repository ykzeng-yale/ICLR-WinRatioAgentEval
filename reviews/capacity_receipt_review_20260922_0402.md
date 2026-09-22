# Bounded capacity-receipt review — 2026-09-22 04:02 cycle, late04:10 delivery

Exact owner commit `c095fc663e607e948cd9fee966a3bf50c6d29e0d`. Read source and `HOST_CAPACITY_OBSERVATION_20260922T041038Z.json`; no local ps/lsof, capacity probe, process signal, model, server or receipt rerun. Used only extracted-function stubs with synthetic subprocess results and a stubbed load-average call. Only this review file is written in the repository.

## What the saved receipt supports

At owner-reported04:10:38UTC, both saved command return codes are0 with empty stderr; ps reports993 output lines and lsof12. The helper reports no match for its named-consumer regex and no listener on8091/8092/8191/8193. This is a useful changed **descriptive snapshot**, so it is inappropriate to continue reporting previously observed servers as currently present solely from the older snapshot.

The original full ps/lsof output is not retained; independent re-filtering is unavailable. Filtering a fixed set of command-name patterns and four ports is not a complete accelerator census, nor does it independently prove a peer released a lease or establish current capacity/reservation/execution approval. No conclusion about foreign workload ownership follows. Report “owner snapshot found no matching consumers/watched listeners, both probes returned0,” not an independently validated full protocol gate pass.

## Concrete fail-open defect in the helper

`_run` sets `ok=True` after any normal subprocess return, including nonzero exit status. `main` sets `clear = not consumers and not listeners` regardless of either probe's validity. Deterministic injected checks reproduced:

- subprocess returncode2, empty stdout and error stderr → `_run.ok=True`;
- both returncode2 probe records → `gate_would_pass_at_this_instant=True`;
- both `_run` records explicitly `ok=False` → `gate_would_pass_at_this_instant=True`.

These are actual acceptance failures, not hypothetical future adversarial input. They do not retroactively change the saved successful-return-code snapshot. They do prevent promoting this helper into a fail-closed startup capacity gate.

## Finite correction

Separate probe validity from matched-presence status. Nonzero/error/timeout or unusable output must produce **unknown/refused**, never clear. Use command-specific handling if a documented lsof exit status can mean no matches: accept that interpretation only for the precise supported status/output condition, not all nonzero returns. Require both observations valid before reporting a limited clean snapshot. Prefer a field such as `no_matching_consumers_or_watched_listeners` instead of the stronger full-gate name, or explicitly constrain the latter to a separately verified complete gate implementation.

The two saved timestamps are call-start wall times, not start/end brackets; the helper's claim that they reveal the full measurement window is too strong. Retain end stamps when naturally collecting the next required startup observation. Anything starting between the calls is not necessarily invisible to both (it might appear in the second); the real issue is that the snapshot is not atomic. No new capacity-probe job or rerun is needed now to correct these labels and refusal logic.

Disposition: accept the limited owner-observed absence report as new status, preserve the receipt, and fix the bounded fail-open helper before any use as a gate. Full lease/host clearance and the existing lifecycle-server/startup implementation remain separate. Prioritize the already authorized server patch rather than further snapshot studies. No readiness credit is awarded by this review.
