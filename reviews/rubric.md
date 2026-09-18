# Internal review rubric (ICLR 2027 form mirror)

Machine-usable version of Section 7 of `submission/iclr_standard_and_rubric.md`. One review = one YAML-like block below, filled completely. Numeric fields take only the listed values. Write the self-written assessment before any LLM assistance and record LLM use in the last field (mirrors the ICLR 2027 reviewer AI policy).

## Review block (copy and fill)

```
reviewer: <name or agent id>
round: <n>
manuscript_version: <git hash or file timestamp>
summary: |
  <<= 5 sentences: claimed contribution, main theorem(s), main experiment(s)>
soundness: <1|2|3|4>
presentation: <1|2|3|4>
contribution: <1|2|3|4>
strengths:
  - <section/eq/fig> - <why it matters> - <key question #1-4 it answers>
weaknesses:
  - <section/eq/fig> - <defect> - <effect on decision> - <closest prior work if novelty>
questions:
  - <question> - <score change if answered well: +0 / +1 / +2>
ethics_flag: <no | yes: human subjects | data licence | conflict of interest | misrepresentation | undisclosed AI use>
rating: <1|3|5|6|8|10>
confidence: <1|2|3|4|5>
reproducibility_check: <pass|fail> - <failing item(s)>
desk_reject_preflight: <pass|fail> - <failing item(s)>
llm_use: |
  <self-written core assessment kept verbatim above; then: none | what the LLM did>
```

## Scale semantics

Rating (internal 2025-style values; 2026 form equivalents in parentheses, assumed mapping):
- 1 (0): strong reject - fundamental flaw: wrong main theorem, invalid inference, unsupported data, out of scope.
- 3 (2): reject - major soundness or novelty problem a rebuttal cannot fix.
- 5 (4): marginally below threshold - sound but contribution or evidence insufficient; needs new experiments or reframing.
- 6 (6): marginally above threshold - accept if listed fixes are made; no fatal issue.
- 8 (8): accept, good paper - clear contribution, correct, convincing experiments, well written.
- 10 (10): strong accept - would defend as an oral.

Readiness gate (calibrated on Paper Copilot ICLR 2025/2026 dumps): all reviewers >= 6 and mean >= 6.5. Any 5 must map to a concrete change.

Soundness / Presentation / Contribution: 1 poor, 2 fair, 3 good, 4 excellent.
- Soundness 4: proofs checked line by line; assumptions match experiments; error control verified with Monte Carlo SEs; baselines share the null. 3: minor gaps without effect. 2: claim broader than proof, or experiment cannot support conclusion (e.g., replay called live A/B). 1: main result wrong or inference invalid (optional stopping without time-uniform guarantee; reused trajectories as independent).
- Presentation 4: claim, agent hierarchy example and decision rule clear by page 2; every theorem has a plain consequence; no undefined notation. 3: readable with effort. 2: buried definitions, unglossed clinical jargon, table-only results. 1: method not reconstructible from main text.
- Contribution 4: changes how practitioners compare agents or gate deployments; not implied by Buyse/Pocock + Howard/Waudby-Smith + Karampatziakis. 3: clear agent-specific advance beyond closest prior work. 2: correct application of known tools, modest insight. 1: restates known results.

Confidence: 5 checked all proofs and code/data; 4 checked main proofs and appendix; 3 careful read, no verification; 2 partly outside expertise; 1 educated guess.

## Checklist (answer each yes/no with a pointer; any "no" must appear in weaknesses or questions)

### Novelty vs prior work
- N1 Each theorem names its closest prior result (Even & Josse; Zhang & Wu 2024; Bergemann & Hanson 2026; Cai, Hu & Li 2026; Howard et al. 2021; Waudby-Smith & Ramdas 2024; Karampatziakis et al. 2021; Fang et al. 2026; Real-POCQi; MAPS-LLM) and states the precise difference.
- N2 No "first"/"novel" claim exceeds what cited prior art permits.
- N3 If CS/betting proofs were replaced by citations, the stated contribution (identification result, protocol, empirical findings) still stands and is what the paper claims.
- N4 Contemporaneous work (two months before deadline) cited if known; not required for comparison.

### Theorem correctness
- T1 Pairing, assignment, horizon, tie thresholds, eligibility fixed before outcomes; filtration explicit.
- T2 Randomization conditions on pair context and potential outcomes.
- T3 Score bounds predictable; no post hoc range narrowing under adaptive orientation.
- T4 Each error-control statement names its event (union null vs simultaneous; stationary vs drift); alpha allocation identical in text and code.
- T5 Finite-grid betting claims limited to validity; consistency claimed only where proved.
- T6 Delay/missingness rules preserve the coverage event; timeouts are outcomes, not exclusions.
- T7 Independent unit identical in theorem, variance estimator and experiment; within-task cross-comparisons never counted as independent.
- T8 Reviewer re-derived each main-text theorem (record where).

### Experimental rigor
- E1 Type I error/coverage at nominal alpha with Monte Carlo SEs and replication counts, including no-effect and harmful-primary cases.
- E2 Power, stopping time, false-deployment probability, abstention reported for all methods under a shared target.
- E3 Baselines: fixed-horizon GPC/Wilcoxon, group-sequential WR, betting CS, marginal guardrails, scalarized composite, Pareto summary.
- E4 Real agent data: >= 2 workflow families; pairing preserved; clusters respected; benchmark-version dependence disclosed; historical costs labelled.
- E5 Online claims: prospective randomized stream or explicitly labelled replay; no "live A/B" wording for replay.
- E6 Sensitivity to hierarchy order, tie thresholds, grading noise, workload shift; prespecified vs exploratory labelled.
- E7 Every figure defines its uncertainty (interval type, unit, replications).

### Reproducibility
- R1 Anonymous code link or zip; seeds; model/judge versions; outcome definitions; manifests with hashes and URLs; licences retained.
- R2 Reported numbers match the exact implemented boundary, score scaling, stakes, alpha allocation, sampling unit.
- R3 Reproducibility statement points to R1; ethics statement covers data provenance and conflicts; AI-use statement lists every required-disclosure task performed with the verification done.

### Clarity
- C1 One-sentence main claim on page 1; agent-metric hierarchy example by page 2; each theorem followed by an operational reading.
- C2 Notation table; no symbol before definition; clinical terms glossed once.
- C3 Main text <= 9 pages (ICLR 2027 style); statements outside the limit; appendix cross-referenced.
- C4 Abstract numbers match tables.

### Community relevance
- V1 Every section is framed in terms of agent systems, benchmarks or deployment gates; motivation names a practitioner decision.
- V2 The paper answers "what does the ICLR reader learn that Buyse + Howard do not give?" explicitly.
- V3 Positioned against ICLR evaluation work (τ-bench, WildBench, micro-benchmarking, Noisy-but-Valid, LLMs Get Lost) with a stated gap.

### Desk-rejection preflight (all must pass before scoring)
- D1 <= 9 pages main text, ICLR 2027 style files.
- D2 AI use statement present (required section; <= 1 page).
- D3 Anonymity in text, appendix, code, metadata.
- D4 Every reference verified to exist (title, venue, year, URL opened).
- D5 No author on > 20 papers; a qualified reciprocal reviewer registered; OpenReview profiles complete.
- D6 No dual-submission conflict.
