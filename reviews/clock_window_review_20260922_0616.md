# Clock equivalence window delta — September 22, 06:16 cycle

Reviewed exact `75e1c8909e6e03ed48a893b27334e3a384125cbd`, indexed by `62bb07c72916745bf14f7aa67918e6fb4659259e`. Immutable Python export `work/clockwindow0616`. **All four new `ClockEquivalenceWindowTests` passed** in 0.001 seconds. No real sleep, clock measurement, full suite, model, sandbox or server operation was performed.

## Accepted

`lab_orchestrator.py:719,850–872` changes the default from 0.05 to 10 seconds, records the effective/protocol window and both measured deltas in `rt['clock_equivalence']`, and adds a measured difference/window drift row when the equivalence tolerance is exceeded. Explicit offline fixtures now request 0.01 seconds. These source changes address the previously wrong default and make a shortened invocation visible in runtime metadata.

The 150 ppm arithmetic is correct: 1.5 ms over 10 seconds versus 0.0075 ms over 0.05 seconds, a 200-fold window/signal ratio under the stipulated constant relative rate difference. This does not prove a 200-fold power improvement for arbitrary noise, or establish clock equivalence beyond the realized finite check. The two clock domains reviewed earlier are not being remeasured or re-opened here.

## Actual enforcement still missing

The effective value is taken directly from `rt.get('clock_window_s', CLOCK_WINDOW_PROTOCOL_S)` and converted to float, with no finite/minimum check before `time.sleep`. A real invocation can therefore explicitly select 0, 0.01 or 0.05 seconds; `below_protocol_window` records that fact but is never a refusal condition. Production and offline calls share this branch. Nonfinite/negative inputs reach float conversion or the sleep API rather than an explicit protocol `PreflightError`, so this change does not establish the required retained refusal path for invalid windows.

Root's finite decision is appropriate: freeze validation and actual production preflight must reject a nonfinite or less-than-10-second window before sleeping/dispatch. A deliberately shortened offline fixture may remain supported only in its clearly labelled test/simulation context. Do not infer that changing the default alone freezes the effective production value. The runtime equivalence record should be persisted in the passing/refused preparation receipt; writing an in-memory dictionary is not by itself evidence of durable receipt retention. The current delta demonstrates the assignment, not that final receipt.

## Test scope

The four delivered tests consist of a constant/source check, two tests of a locally reimplemented `_run_clock_check` helper, and the stipulated rate arithmetic. The helper never calls the actual `preflight`, never exercises its exception/refusal branch, and returns a dictionary instead of checking the actual runtime assignment. They legitimately support their narrow assertions, but cannot establish production override enforcement or refusal persistence. When implementing the above finite guard, use one targeted actual-preflight test with stubbed sleep/readers and a valid minimal fixture to verify shortened-production refusal and the retained effective 10-second positive path; no broad suite or real clock probe is needed.

Only this report was written in the repository. No new experiment or acceptance milestone is awarded. Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. Prospective acceptance, final expanded-release QA and author checks remain pending.
