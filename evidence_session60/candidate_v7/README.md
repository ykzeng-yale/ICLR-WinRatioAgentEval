# Candidate instrument v7 — retained originals

Delivered copies of the two artifacts the candidate manifest declared, because root (2026-09-23 10:03) observed that *"an external scratch path is not a delivered copy"*.

These are the **retained originals**, byte-for-byte, with the hashes the manifest already recorded. Nothing here was regenerated, and no unavailable material was reconstructed.

| file | bytes | sha256 |
|---|---|---|
| `v7_build.log` | 26350 | `51876ff3cd8922cc292fdac162c395e0b5d418d0701a1307654cbf0aa2078746` |
| `control_life.jsonl` | 178 | `26aa81b3646b08a34cbef0b7e562ab358b87229b1bf9366415b5560b24fe062e` |

`v7_build.log` is the closed configure+compile log (262/262, exit 0).
`control_life.jsonl` is the lifecycle file the built binary itself wrote in the writable
control case; its single line is the closing seal carrying `sidecar_failures: 0`.

**Permanently unavailable** for those four cases, and not reconstructed: the per-case
stdout/stderr, and the injection script (the cases were run inline). See
`results/live_ab/CANDIDATE_EVIDENCE_CORRECTIONS.json`.
