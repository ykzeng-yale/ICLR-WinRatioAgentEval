# Production job-shape agreement closure — September 23, 06:54 cycle

Exact reviewed head: `c3ab4fcc8bfe7b9ccc08fee70cbd36325f1f5592`; bounded delta from `5d2758b`. This review covers the remaining top-level/nested host-pin agreement obligation from `reviews/lock_closure_review_20260923_0618.md`. Root separately reviews the anchor helper rename, capacity receipt and shared milestones.

**Accepted closure.** The previously failing job produced by actual `World.build_job` now refuses at actual `lab_worker.main` before `run_job` when its top-level sandbox host pin disagrees with the audited canonical pin. Matching producer-shaped jobs still reach the same canonical lock boundary. Nested legacy configuration and contradictory copies are checked as additional representations, rather than replacing the actual top-level production block. No remaining concrete defect was found in this finite obligation.

## Bounded verification

Ran only the **two newly added tests**, both passing:

- `test_a_producer_shaped_job_is_validated_in_the_shape_it_is_emitted`
- `test_contradictory_host_pin_copies_refuse`

Independently called actual `World.build_job` using synthetic World state, wrote the resulting jobs to a temporary file, and called actual `lab_worker.main` with only `run_job` stubbed. All payload digests match the actual canonical payload function. **Eight actual-entry cases passed their expected acceptance/refusal checks:**

| Job configuration | Expected and observed |
|---|---|
| Actual producer, agreeing top-level pin | Reaches stubbed `run_job` with audited canonical lock |
| Actual producer, conflicting top-level pin | Refuses before `run_job` — previously failing witness now closed |
| Nested legacy block only, agreeing pin | Reaches stubbed `run_job` with audited canonical lock |
| Nested legacy block only, conflicting pin | Refuses before `run_job` |
| Top-level correct, nested conflicting | Refuses before `run_job` |
| Top-level conflicting, nested correct | Refuses before `run_job` |
| Both copies agree with audited pin | Reaches stubbed `run_job` with audited canonical lock |
| Both copies agree with each other but not the audited pin | Refuses before `run_job` |

Evidence: `reviews/evidence/job_shape_closure_20260923_0654.json`. The owner-added producer-shape test constructs its job after a source-shape check; this independent witness additionally calls the actual producer. A positive stub boundary is not a claim that an episode executed successfully.

No full conformance suite, broader suite, wrapper acquisition, canonical lock acquisition, model, server, sandbox program or network operation was run. Previously accepted canonical-path binding, fixture isolation, cross-wrapper controls and anchor closure remain accepted in their recorded scopes; they were not reopened or repeated. The agreement helper validates the supplied host-pin representations against the same audited pin and does not alter the statistical design or success margin.

## Next milestone and status

The lock job-shape repair is complete. Session60 should advance the existing pending pin promotions and lifecycle/failure-retention work already specified in the root handoff, followed by the finite preparation plan and explicit working-branch freeze review. This closure adds no new generic malformed-input or adversarial-security project and requires no additional model run.

Latest supplied owner statement: **September 23 06:51:04 UTC**, zero trial episodes, zero calibration episodes, alpha spent zero, **14/26** structural freeze components, nothing running. The **06:50:15** capacity snapshot is an observation, not an ongoing reservation; it was not re-audited in this narrow review.

Full-project arXiv readiness remains **75% (change 0)**; bounded-v1 **90%**. This implementation closure earns no study-completion credit. Remaining: prospective study plus root acceptance (10 points; Session60/root), final expanded package QA (5; root), and author checks (10; Yukang Zeng).
