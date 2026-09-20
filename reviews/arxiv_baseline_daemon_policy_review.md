# Baseline-daemon policy: bounded pre-freeze review

September 20, 2026, 04:45 UTC monitoring cycle. **Full-project readiness: 60% (change 0); bounded-v1 readiness: 90%.** This is a design clarification, not a delivered detector, completed validation study or trial clearance.

## Version and evidence boundary

The validation branch advanced from `de31b6cf124b3723eb9986a03318f1ae4f935353` to [c746e320920b83c453e02c1cde19b32f4a9d03e9](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/c746e320920b83c453e02c1cde19b32f4a9d03e9), committed at **04:29:13 UTC**. Its entire delta is 28 added lines in `experiments/live_ab/design/COORDINATOR_DECISIONS.md:240–267`. Main was `c15d1c7cb1a32baf2e5a3bef34051eee5e2cb890`; the live branch remains `577687799e8588077c036b4d94f1afc839d78e4f`.

The owner reports a scan around 04:00 UTC with 1,037 processes, zero degraded checks and three findings: two foreign model servers and one operating-system daemon. The document says the trial remains blocked. These are owner-reported host observations, not independently reproduced measurements. The last explicit episode count remains **zero at 02:16:43 UTC**, not a newly verified count.

No executable code, test log, scan receipt or populated freeze is added by this commit. The inspected preflight and event implementation are unchanged from the previous review. No tracked files exist in `experiments/live_ab_validation/`, `results/live_ab_validation/` or `results/live_ab/` at this pin. A policy written on the validation branch is not delivery of issue #12's CPU protocol or panel. Local unpublished owner work may exist; this review makes no claim about it.

Root verified the delta and delivery inventory; a separate read-only statistical reviewer assessed the new policy. No model execution, simulation, foreign-process inspection or mutation was needed.

## Disposition and concrete clarifications

A closed baseline-service allowance is **acceptable in principle as a pre-outcome definition of the measured serving regime**. Recording recurring services, retaining their measured latency and freezing the rule before outcomes are appropriate. The following details must accompany the existing host-check repair; they do not require a new study.

1. **Freeze exact identities and matching.** Lines 253–255 promise a closed list but refer to a `/System/...` path prefix. Deliver exact resolved executable-path entries and matching rules, rather than a blanket `/System/` or framework-directory exemption or a name-only match. Include the list in the bound freeze and test allowed, disallowed and ambiguous identities.
2. **Define activity and incomplete coverage prospectively.** Lines 259–262 leave “materially active” undefined. Freeze the CPU-time threshold, measurement interval/normalization, scan cadence, trial-overlap flag and missing/degraded-scan treatment. Retain continuous measurements as well as flags. State the resident-size floor and units, and whether baseline processes below that floor are recorded. An unavailable measurement is unknown, not zero activity.
3. **Limit what a scan establishes.** CPU-time deltas measure CPU activity; they do not establish accelerator activity or inactivity. Replace “what the gate proves” in lines 263–265 with: “At the recorded scans, the detector reported no recognized, non-allowlisted process satisfying the frozen detection criteria and resident-size threshold.” This does not establish continuous accelerator isolation. The claim that refusal could never pass on a normal host is unnecessary; permitted baseline services may recur.
4. **Preserve the actual operating regime and observations.** Report permitted baseline activity and detection limits beside latency results. Apply the already requested, frozen response to newly detected foreign load while preserving enrolled pairs, failures and unknown usage. Do not retrospectively adjust latency, drop affected pairs, redraw assignments or restart based on outcomes. Public events must retain the previously requested sanitized schema rather than arbitrary command lines. Observed load alone neither proves invalid randomization nor supplies the no-interference assumptions needed for stronger claims.

The exact implementation, schema and bounded fixtures must be delivered for review. The new policy does not close the earlier freeze-binding, ledger, seed, clip-contract, active-claim or serving-test findings in [the candidate disposition](arxiv_live_candidate_disposition.md). No blanket rerun or altered success margin is requested.

## Handoff and unchanged release

Session60 retains #11 repairs, freeze and collection, plus #12's procedurally separate CPU specification and panel. Next: deliver the repaired candidate and bound host policy with test evidence; supply the CPU specification/fixtures at an exact commit. Root then reviews explicit freeze clearance, accepts completed evidence and integrates the final expanded package. The author retains scientific and submission checks. A favorable trial result is not required.

Only this review and shared progress records are integrated on main. No new experimental outcome is validated, integrated into the manuscript or packaged. All five arXiv artifact hashes and the historical ICLR code ZIP match the previous verified release. No PDF rebuild is warranted by this documentation-only review. No full-project milestone closes, and no new PR is created.
