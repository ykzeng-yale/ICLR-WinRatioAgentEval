# Scientific review and revision ledger

These are model-assisted project reviews, not external human peer review. Scope and any reviewer/developer overlap are disclosed in each report.

| Concern | Response and evidence | Status |
|---|---|---|
| Generic GPC plus sequential inference may be incremental | Broad first-use claims removed. Closest sequential, deployment, and delayed-outcome methods explicitly compared. Partial-evidence online protocol being added. | Scientific contribution remains open |
| Invalid tolerance silently changes comparator | Finite nonnegative tolerances and nonempty valid inputs now enforced; tests pass. | Corrected |
| Manual simulator differs from library | Independent reviewer compared 300,000 fresh pairs and found exact agreement. Analytic targets separately checked. | Verified within stated scope |
| Boundary guardrail nulls absent | Reproducible post-review stress suite adds both boundaries; all 17 stress rows independently replayed. | Corrected |
| No adaptive or dependence examples | Added adaptive-order inverse weighting and shared-task/reused-run experiments, with the exact target and failure mechanism labeled. | Addressed for those models |
| No informative-delay experiment | Assigned worker implementing partial-evidence versus completed-prefix simulation; separate theory and protocol. | In progress |
| Conservative normal-mixture baseline | Main text explicitly reports radius 0.033 versus margin 0.01. No state-of-the-art efficiency claim; stronger U-statistic comparator queued. | Claim restricted; comparison open |
| Win-only detection mislabeled Type I error | Harmful deployment distinguished from a correct test of positive composite preference. | Corrected |
| Sample use confused with dollar cost | Capped mean pair count, two executions per pair, and conditional stopping times distinguished. Commercial spend tracked separately. | Corrected |
| Retained versus current crossing mismatch | Reported same-look rule and optional retained rule separated in appendix. Independent focused recheck passed. | Corrected and rechecked |
| Missing complete-record independence | Independence of complete task/replication records explicit; studentized CLT assumes iid complete records. Independent recheck passed. | Corrected and rechecked |
| Same-seed diagonal changes estimand | Twelve off-diagonal pairs primary; U/V decomposition proved; diagonal and all-pairs sensitivities retained. Pre-results amendment recorded. | Corrected |
| Shared four-seed suite limits inference | Historical-seed conditional task-resampling interpretation added. No coverage over new seeds claimed. | Limitation retained |
| SWE repository dependence | Deletion is a stability diagnostic, not a corrected cluster CI. Inference restricted. | Limitation retained |
| Tier win/loss outputs absent | Added tier wins, losses and signed contributions; all configuration sums reconcile. | Corrected |
| Protocol suggestions exceed executed analyses | Executed configurations enumerated; unexecuted exploratory alternatives identified. | Reporting corrected |
| Multiplicity and sensitivity selection | All configurations retained; intervals called pointwise; no simultaneous leaderboard or production claim. | Claim restricted |
| Code hashes changed after input validation | Original commit preserves initial run; reviewer replayed all 36 initial and 17 stress rows exactly. Current scripts rerun and manifests refreshed. | Verified |
| Prospective API unavailable | Initial OpenAI request returned exhausted-credit error; zero complete pairs retained. Haiku workflow amendment preserves initial protocol and reserved cost. | Amendment in progress |

Outstanding limitations are not closed merely because a PDF compiles. Human verification, a credible contribution, and final submission declarations remain required before the active goal can be marked complete.
