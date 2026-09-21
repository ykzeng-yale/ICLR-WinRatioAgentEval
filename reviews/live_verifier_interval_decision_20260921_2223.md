# Root verifier-interval decision — September21, 22:23 UTC

Full-project70%, change0; bounded-v190%. Last seen mainf0441a9/live8801c2f. Review scope: new numeric guards, two-process lock receipt and the owner's question about timing. No model, sandbox or lock fixture rerun by root.

## Timing question resolved

**Use the verifier-call interval after acquiring the execution lock for required load coverage.** Capture verification_started_monotonic immediately before verify(), inside the lock, and verification_ended_monotonic immediately after it returns, still inside the lock. Preserve the prior wider timing information separately: lock_requested, lock_acquired, verification_started/ended and lock_released. Do not overwrite prior saved receipts or relabel old endpoints as the narrower interval. Name the interval schema/version explicitly.

This is a prospective preparation measurement clarification: protocol3.2(4) asks for verification under load, not waiting for the lock under load. It does not change the reference2.5s threshold, verify_seconds source, success definition, lock timeout, trial inference or margins. Failed lock acquisition remains an infrastructure/preparation event with its attempt/wait/error retained, not a task reference failure. Keep the existing data-derived timeout rules unchanged. All genuine verifier execution remains covered, including verifier setup inside that call; no exclusion of slow parts based on outcomes.

Implement this ordinary authorized repair with a deterministic stub showing a nonzero wait plus a covered verifier call; ensure the load check uses only the named verifier interval while the full wait stays in the ledger. No serving execution is needed to verify the wiring. The actual observer source, continuous-window interpretation and finite caps remain pending; correct interval arithmetic alone cannot provide that evidence.

## Lock and arithmetic disposition

See [independent bounded review](live_lock_coverage_acceptance_20260921_2223.md). Accept only the supported production-lock-class fixture scope. The saved receipt has distinct holder/contender processes, readiness handshake, a contender timeout while the holder remains in the critical section, and a separate lock-bypassed negative control with overlap. The source uses the production _ExecutionLock class on a synthetic lock path; it launches ordinary Python child processes, not sandboxed verifier programs. Correct the combined “lock/sandbox” label rather than implying sandbox verification. This is useful evidence of one lock-contention pattern; it is not general concurrency proof or an actual trial-worker receipt. The existing15 target denials remain a separate sandbox observation.

Keep receipt process identifiers authoritative; the GitHub prose PID42023/42024 differs from saved42056/42057. This is a reporting mismatch, not evidence by itself that the lock outcome is false. Cite the saved receipt and its exact generation parameters (hold1.5s, wait1.0s); the source default wait4.0s does not reproduce a timeout while hold1.5s. Record the actual invocation beside the receipt rather than relying on defaults. Do not rerun unchanged fixtures solely to fix prose.

Numeric domain repairs are reviewed independently. Retain finite/nonnegative uncertainty, finite ordered endpoints and conditional observer semantics. The three prior numeric defects now reject, and ordinary coverage/positive verifier-uncertainty cases behave correctly. One residual is reproduced: `_finite(record.get('endpoint_error_s')) or 0.0` treats explicitly NaN, infinity or invalid text as zero and returns valid coverage. Default to zero only when the field is absent; reject an explicitly malformed value. No re-opening of previously closed immediate-stop, raw-retention or saved-environment findings is requested.

## Work remaining

Latest owner22:20:34UTC: zero live episodes, nothing running, foreign servers present,11/26 inventory. T1112000/coarse80000/fine48000 and ablation32000unique coordinates/64000evaluations unchanged. T1 accepted/integrated/packaged; qualified power/ablation accepted but not integrated. No new scientific outcomes or PDF/package changes.

Session60 retains source-acquisition/worker-startup fixes, injected-decision rejection, anchor drill and finite serving/load/rehearsal specification. Root owns independent acceptance and expanded-paper integration. Remaining30points: prospective10(Session60/root), expanded integration/finalQA10(root), author scientific/account/rights10(Yukang). Next milestone is the remaining entry-point work plus the executable finite plan; no model or trial freeze clearance yet.
