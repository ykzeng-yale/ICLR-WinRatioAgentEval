# Frozen public-trace prefix certificate feasibility replay

Frozen 2026-09-18 UTC before this replay's aggregate outputs were computed or viewed. The source archive and earlier complete-outcome comparisons were already known. This is an internally specified, descriptive feasibility audit of a fixed historical archive, not a new trial, external preregistration, or independent benchmark discovery.

## Fixed archive and contrasts

Use the nine retained `tau2_*4trials.json` files whose hashes and pinned public URLs appear in `results/public_manifest.json`. They cover the same three models (o4-mini, GPT-4.1, Claude-3.7), three domains (airline, retail, telecom), 278 tasks and four trials per model/task as the main public analysis. Verify the complete expected grid and every file hash before analyzing certificates.

Analyze all three fixed contrasts: o4-mini versus GPT-4.1, Claude-3.7 versus GPT-4.1, and o4-mini versus Claude-3.7. Within each task, use all 12 off-diagonal seed-index comparisons, excluding the four same-seed diagonal pairs. Across three contrasts and 278 tasks this gives 10,008 comparisons. The two motivating contrasts o4-mini versus Claude-3.7 in retail and telecom are highlighted in the descriptive summary, but all nine contrast/domain rows are retained regardless of their result. Distinct seed runs are needed for the independent-copy interpretation; this feasibility replay does not establish independence or population inference from the archive.

## Fixed final comparison

Compare archived binary success first; among two successful episodes compare lower archived agent cost with practical equivalence `abs(cA-cB) <= 0.05*max(cA,cB)`; if costs are equivalent compare fewer assistant-issued tool calls. Two failures tie and resources cannot break that tie. Success discordance decides immediately. No safety tier or safety claim is included, because these records do not provide the required independent safety labels.

Use `reward_info.reward` as the fixed archived binary label. Its being a fixed recorded label does not establish that the original grader measured error-free real-world success. This replay does not rerun the grader, models, users, or tools.

## Ordinal replay schedule

At abstract integer tick k, expose the kth actual archived assistant message in each arm, if present, including its recorded cost and issued tool calls. Initial assistant messages with zero cost remain real archive events. Actual timestamps and durations are not used.

Each arm has an additional terminal completion marker one tick after its last assistant message. This marker signifies that the whole archived episode, including any trailing non-assistant messages and final verification, has completed. Only then reveal that episode's archived success label and final agent cost/tool-call count. The simulator uses the complete archive to schedule these events, but the certificate calculation receives only the state already revealed at that tick. The marker is a replay convention, not an observed grading delay.

This pairs two independently generated historical traces in ordinal message order. It is **not observed concurrent latency**, and ordinal resolution lead is not calendar time, actual tool execution saved, dollars saved, or deployment stopping-time improvement.

## Mandatory cost and count audit

For every retained episode, verify that every assistant message has a finite, nonnegative recorded cost, and that their sum matches the archived final `agent_cost` to absolute tolerance `1e-10` plus relative tolerance `1e-10`. Verify finite nonnegative archived cost, a binary final label, and nonnegative integer tool-call increments. Record exact episode/message counts, number of zero-cost messages, maximum discrepancy and source hashes. If an episode violates these conditions, stop and report the problem rather than silently excluding it or fabricating a cumulative cost.

Use decimal arithmetic on the archived numeric strings for cumulative costs and the 5% comparison, with float conversion only for display. Before using a pending lower bound, subtract a nonnegative conservative per-episode cost reconciliation tolerance `1e-10 + 1e-10*max(1, final_agent_cost)` from accumulated message cost and clip at zero. This numerical allowance does not reveal the hidden final value to the decision rule: pass the **single archive-wide maximum** of that tolerance, frozen after the required cost audit, to every replay. The audit may use final values to validate the archive; the certificate rule may not use an episode's hidden final value to tighten its pending bounds. The allowance only widens the completion set. Record it in the manifest.

For the hierarchy's final score, use archived final cost and issued tool-call total. Report any difference from the existing complete-outcome floating-point comparator before interpreting certificates.

## Guaranteed completion bounds

For a completed episode, success, cost and issued tool-call count are fixed to their revealed values. For a pending episode, success remains in `{0,1}`, eventual cost lies in `[observed cumulative cost minus the common conservative allowance, infinity)`, and final issued tool calls lie in `[observed cumulative count, infinity)`. No upper resource bound is inferred from unobserved final data, episode length, model identity, or reveal timing. No content-based inference predicts an unrevealed final label.

Enumerate all success-bit completions. Discordant success decides the hierarchy; joint failure ties. Under joint success, consider every possible cost sign compatible with the two nonnegative resource intervals and the 5% tolerance. When cost equivalence remains possible, consider all tool-count signs compatible with the count intervals. These rectangular completion sets deliberately ignore any unknown cost/tool-count dependence and therefore give conservative lower/upper signs. Take the minimum and maximum over every feasible hierarchical sign.

An example certificate occurs when A has completed successfully at cost c and the pending B has already incurred cost strictly above `c/0.95`: B either fails, losing on success, or succeeds, losing on cost. A tool-count lower bound may also certify A when all feasible B costs either lose to A or tie, and B has already issued strictly more calls than A. Report certificate basis separately from the final observed decisive tier, because a sign can be certain while the tier remains unknown.

## Required containment checks and comparator

At every ordinal prefix, including tick zero and both terminal markers, verify that the observed final archived hierarchy sign is inside the proposed interval. Verify nested intervals, no early use of success labels, and exact collapse after both episodes complete. Verify each pending cost and count lower bound is no greater than its final archived value.

The completion-only comparator determines the sign when both archived success labels are available. It immediately respects success discordance and joint-failure ties and does not wait for irrelevant resources after failure. Under this chosen terminal-marker schedule both final resources are already available with the final labels; its resolution tick is the later marker. Define certificate resolution as the earliest tick at which the conservative sign interval is a singleton. Report the difference in ordinal ticks between completion-only resolution and certificate resolution. There is no sequential hypothesis test, e-process, alpha claim, bootstrap or population confidence interval in this descriptive replay.

## Frozen outputs and denominators

Write only `results/trace_certificate_*` artifacts:

- Source/cost audit rows for all nine files.
- One row for every off-diagonal comparison, including anonymous task identifier, model/domain, seed indices, final sign/tier, each terminal tick, certificate tick, early indicator, certificate direction/basis, and ordinal lead.
- All nine contrast/domain summaries with counts, denominators, fraction resolved before both episodes finish, direction counts, final-tier counts, mean/median ordinal lead among early certificates and across all comparisons.
- A diagnostic table containing the first three early certificates in deterministic task/seed order per contrast/domain, with anonymized task IDs and only already revealed data at certification. If a row has fewer than three certificates, include all available examples; do not select examples by size of benefit.
- A manifest with source/protocol/code hashes, exact configuration, software versions, every-prefix verification counts, numerical allowances, output hashes, and scope limitations.

Anonymous task identifiers are the first 12 hexadecimal characters of SHA-256 of `domain + ':' + task_id`; no trace text, personal names, account information, or raw messages are copied into deliverables. Full sources remain at their existing pinned public URLs and local archive. All results are descriptive fixed-archive quantities; replicated pairs and tasks are dependent and no independent-pair sample-size claim is made.
