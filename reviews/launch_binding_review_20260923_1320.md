# Launch-library inventory review — September 23, 13:20 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and paper/package integration remain complete and unchanged. Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains bounded preparation closure and the costed plan before explicit working-branch freeze review. Inventory checks add no scientific result or readiness credit.

Reviewed main `0a3e64d6b8627eb3b70d8531391c91f528a1429a`; substantive delivery `60e85489768e60297210904859d01463522fb472`. Executed helper source `experiments/live_ab_serving/run_smoke.py` has SHA-256 **`845102536cacbb6910032ee25c900eddc28c9b54c4296c567a04acc750acbda7`**. This review concerns only the new declared-library checks in `verify_launch_artifacts`, against the standing source/patch/runtime-binding requirements in `reviews/launch_and_deadline_disposition_20260923_1116.md`. Later manifest/deadline changes are not reviewed here.

## Accepted declared-inventory repair

The helper now refuses when `non_system_library_closure` is absent or empty. It reads each declared library beside the selected launcher, checks its measured SHA-256 against the declaration, and reports declared/verified counts. A changed declared implementation library, an absent declared backend, and a malformed declared library hash all refuse. A control with two correctly declared dummy library files verifies both.

**Eleven tiny synthetic-file cases** independently exercised the actual helper. There was no `main`, process creation, executable or model use, runtime loader inspection, network, build, or full suite. The case inputs and exact file/source hashes are recorded in `reviews/evidence/launch_binding_review_20260923_1320.json`.

This closes the previously ignored **declared-member** mismatch. The owner receipt `REQUEST_DURABILITY_AND_LAUNCH_BINDING.json` (SHA-256 `8e9f736a8c392bdcd3fdfb7af874147e203fd891c07c24100e46fe7c374e27b9`) accurately calls the result an inventory check and disclaims a proven transitive closure. Preserve that limited claim.

## Required selection and source binding remain open

The helper checks whichever members the manifest lists. It does not independently establish that the list covers the selected implementation and backend. The following finite controls still return `verified=true`:

| Controlled change | Why the required binding is not established |
|---|---|
| Omit the implementation from the inventory, then change its bytes | The unlisted implementation is never measured |
| Omit the backend from the inventory, then remove its file | The missing unlisted backend is never required |
| Declare only one unrelated sibling file | A nonempty inventory is sufficient, regardless of required members |
| Omit source revision and patch identity | Neither input affects the verdict |
| Supply malformed source revision and patch identity | Neither input is validated or compared |

These are helper verdict witnesses using dummy files, not claims that a real loader would launch those fixtures successfully. They demonstrate the remaining gate boundary: a launcher/model hash match plus agreement for a caller-selected nonempty list is not verification of the candidate instrument.

The path rule is currently `binary.parent / name`. It does not resolve actual load paths, dependency references, or selected backend loading, and no source/patch-to-build relationship is checked. Those are the already requested binding obligations, not newly proposed broader audits. Merely renaming the inventory as a closure would not establish them.

## Next bounded repair and historical scope

Use the existing candidate build/link provenance and selected backend configuration to declare the **required** implementation/backend members and their resolved paths; bind that inventory to the selected source revision, patch digest, and corresponding build record. At the trusted launch boundary, require those inputs, compare the selected files with their pins, and refuse omissions or mismatches before process creation. Keep the existing named OS/system-runtime provenance convention. Demonstrate omitted-required-member, mismatched-source/patch, and wrong-selected-path refusal with finite synthetic/retained-metadata fixtures. No extra build, model run, repeated source audit, or historical smoke is needed to implement that gate.

Root's policy remains: **no v4 historical exemption for a new launch**. Preserve the original v4 evidence and its historical readable/accepted scope; do not use that compatibility route to bypass requirements for a new acquisition.

Accept the declared-library measurement/refusal subset. Full candidate launch binding remains incomplete. Session60 owns the bounded completion; root retains acceptance and combined supervisor disposition. No owner/shared files were edited and no commit was made.
