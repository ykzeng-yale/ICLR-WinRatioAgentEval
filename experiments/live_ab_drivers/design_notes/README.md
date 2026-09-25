# EB2-EB4 model-free drivers and EB5 preparation: design notes (PROPOSAL, not code)

Status: a proposal for root review (root 22:20 ranked action (2),
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md` on main). Nothing here is code, a
receipt, a freeze input or a result. No model, server, build, network or test run was used to
produce it.

How it was made (2026-09-25, 22:30-23:05 UTC):
- Six read-only mapping agents each mapped one area against the accepted base (tag
  `session60-eb1-eb5-subset-v1` = `c7750a3`, doc-only successor `c62b59b`): the stage-1 driver,
  stage-2, stages 4-6, the stage-3 two-stream sweep with EB5, the section 11.5 CPU replay, and the
  unmerged `session60/repair-replay` (72230b8). Their notes are the `map_*.md` files, kept as
  written apart from path scrubbing.
- A synthesis agent wrote v1 of the proposal.
- A completeness critic found four problems in v1, kept as `CRITIQUE_OF_v1.md`:
  - v1 discarded `72230b8` on a false claim;
  - v1 marked stage 6 fully model-free;
  - three citations could not be checked;
  - root 22:20's seven prerequisites were not cross-walked.
- A revision agent re-verified each problem and wrote `DESIGN_PROPOSAL.md`, which is v2.
- The owner then changed "PR" to "commit" to match root's direct-integration policy, and "GPU" to
  "serving host". The replay agent's structured result came back empty, but its notes
  (`map_replay.md`) were written in full and re-read for v2.

The citations are path:line at `c62b59b` unless stated otherwise. They were produced by agents and
spot-checked by the critic, not all re-verified by the owner.
