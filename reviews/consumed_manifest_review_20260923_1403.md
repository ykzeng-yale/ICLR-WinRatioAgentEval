# Consumed-field validator: accepted omissions repair, two remaining inputs

Full-project arXiv readiness remains **75% (Δ0)**; bounded-v1 remains **90%**. Remaining: prospective-study owner completes the acquisition/freeze contract and study (10 points); root completes final integration/QA (5); Yukang Zeng completes author checks (10). Accepted CPU validation and its paper/package integration remain complete and unchanged.

Reviewed source [1e58d3b041c3310c1df19aa5cefaf0cad5040af2](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/1e58d3b041c3310c1df19aa5cefaf0cad5040af2), at delivered head [176e682f5688ee4c786d4840fb3ac7f40351a677](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/176e682f5688ee4c786d4840fb3ac7f40351a677). Scope is the changed consumed-field validator and its actual entry-point behavior. Protected cleanup, response retention and selected-library binding are separate assigned reviews. Detailed outcomes, exact pins and reproduction script are in [the evidence JSON](evidence/consumed_manifest_review_20260923_1403.json).

## Accepted subset

The seven named rejection probes in `PROTECTED_PATH_AND_CONSUMED_FIELDS.json` reproduce: missing temperature, missing host ID, missing boot ID, malformed patch digest, negative max_tokens, boolean temperature and infinite temperature. Missing patch digest is separately confirmed. The complete-manifest predicate control remains accepted.

All **four previously failing missing-field cases** now traverse the real `main()` to **status1 and exactly one terminal refusal receipt**, with no fake launch/POST, no intent, zero process polls/waits and no diagnostic bytes consumed. The old missing-temperature child-leak witness and the three post-dispatch identity KeyErrors are closed for these inputs. `request:null` and `model:[]` also refuse before nested lookups and launch. Source order places this validator before model discovery and launch-artifact verification. The complete actual-main control still returns status0 with one receipt and two fake POSTs.

## Remaining concrete cases

| Input | Validator result | Actual-main result |
|---|---|---|
| `request.temperature: null` | Accepted with an empty problem list | status0, one success receipt, two fake POSTs whose payloads both carry null |
| `request.temperature: 10**400` | Uncaught `OverflowError: int too large to convert to float` | exception before launch; no intent/POST and **zero terminal receipts** |

The null case is caused by conflating a missing field with a present null: `need(..., kind=None)` returns None and `if temp is not None` skips every type/domain check. This demonstrates a bypass of the declared numeric-temperature contract. It does not establish what a real server would do with null; no server behavior was measured.

The 401-digit integer is valid JSON and reaches the unguarded `float(temp)` call. The new validator itself throws, and its actual-main invocation occurs outside the later dispatch protection. This is a prelaunch finalization failure, **not** a surviving child. Catching later dispatch errors cannot repair it.

Next bounded owner action: reject explicit null with a named validation problem; handle numeric conversion overflow without throwing, using the agreed finite numeric domain. Add those two entry-point refusal cases and preserve the already accepted controls. Each invalid input must produce one terminal receipt before launch/transport. This review does not claim the whole manifest or acquisition contract is complete.

## Verification and pins

Ran **13 pure validator cases and 9 actual-main fixtures**, with the new owner harness and real temporary serialization/read-back. These are case counts, not a rerun of the 25-test suite. Independent Popen/socket/system/signal/pipe/real-sleep guards and all fixture deny ledgers were empty. No actual child, HTTP, network, model, build, pipe, real wait or simulation ran.

- `run_smoke.py`: `2d2ec42beccc9e8b41790a6e22cba245ae7412cccba86f4b040e3b77f5b17fb1`
- `tests_supervisor_entry.py`: `d0b3ad15882c3bda749a484c647af5ce17aad8e3200c268a7e20491caa3e616b`
- Delivery receipt: `8672f68d639844dc76189c889406ab89cb623509e45aa1ddf5c707bfff5af41a`

The evidence JSON additionally pins the lifecycle reader and both immutable historical fixture inputs. No owner/shared files were changed and no commit was made.
