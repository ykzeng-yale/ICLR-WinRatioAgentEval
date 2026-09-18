# Current experiment execution policy

Effective September 18, 2026, following the author's explicit instruction. This policy supersedes every earlier cheap-model allowance, monetary allocation, and suggestion to request further commercial-model budget in this repository.

## New experiment execution

- **No further commercial or proprietary-model calls.** New experimental agents, user simulators, graders/judges, and fallback models must use open-weight models or open-source agent systems backed by open-weight models. Free credits or a low price do not create an exception.
- Prefer existing local compute. This instruction does not authorize new cloud/hardware purchases. Check disk space before installing anything; retain weights outside Git and never delete unrelated user files.
- Do not load stored commercial API credentials, retry the historical commercial pilot, or fall back silently to a proprietary endpoint. If a local component cannot run, record the failure and request a compatible open-model handoff.
- Record model and tokenizer identifiers/revisions, weight license, quantization, runtime, hardware, endpoint configuration, all simulator/judge models, seeds, task manifest, completion counts, missingness, and inference resources. Open weights alone do not establish an unrestricted license or reliable grading.
- Freeze the design before new outcomes. Preserve unsuccessful hypotheses, abstention, failures, and all enrolled units. Do not extend a study or select models/seeds merely to obtain a favorable result.

## Existing evidence and reproducibility

Previously collected commercial-model observations and public historical traces remain immutable provenance records. The author requested a ban on future use, not deletion of prior observations. Their historical collection scripts are retained for provenance and are **not authorized for execution**. Archived aggregate reproduction and CPU-only simulations may run without making model calls.

The previous frozen anonymous package is preserved at `f806aba`. Round 10 integrates the accepted PR 7 sequential-comparison subset and PR 10 drift study into new archives with separate numerical, source, anonymity and PDF checks. PR 8 coding/airline results remain excluded pending correction and validation. Never treat an observed contribution as integrated merely because it exists on GitHub.

## Concurrent ownership

The existing `iclr-winratioagentevals-60` / `session60/local-stream` worker owns PR 8 model execution and its experiment/result directories. Do not start a second airline job or overwrite those data. Root owns the paper, shared status/queue, and release integration. Reviewers write only their assigned review files. Changes to owned code go back to its owner as a concrete review request.

See [EXPERIMENT_QUEUE.md](EXPERIMENT_QUEUE.md) for current delivery status and [reviews/round9_experiment_gap_assessment.md](reviews/round9_experiment_gap_assessment.md) for required versus optional scientific work.
