# Round 14 bounded owner-report cleanup review

**PASS.** The nine airline substitutions, one coding Definitions correction and new airline precision note implement the enumerated Round 13 requests without changing numerical tables or removing prior scope qualifications. Both text generators reproduce their reports and manifests exactly. No introduced defect was found within this bounded cleanup scope; no paper, archive or experiment change is required by these findings.

Frozen owner head: `be4b8e4d406c26f16225420493a900105fd20244`. Baseline: `01f2381940fcf5bc57129f1498382cb40f3ea741`. This is an AI audit, not human peer review. The reviewer did not write the owner cleanup; a second read-only text checker independently confirmed the substitution/qualification mapping. Only this report and outer `work/round14_report_cleanup/` were written. No model calls, original analysis reruns, benchmark programs, owner-source edits, paper/archive changes or Git mutations were performed.

## Exact reproduction and preservation

The preceding merge `91edee40e0904904f354ac152f51304e1d6aa68d` has the expected parents `01f2381` and root `a2eee58526f0ce3cef913fa8156ae34601d1b597`. Relative to that merge, this delivery adds seven report/generator/manifest/addendum files and modifies only `results/SESSION60_RESULTS_INDEX.md`.

All **229 pre-existing files** under the two owner collection/analysis/result trees retain identical Git blob identities against `01f2381`, including **109 raw/log/CSV/JSON-class files**. The earlier owner verification report is also unchanged. These are the actual counts for the specified tree scope, rather than an assumed 231-file denominator. The results index and full release preservation are root's separate checks.

Both generators were inspected before execution. They use local standard-library text/hash operations; each resolves its source and two output paths under its own extracted snapshot. Running them only in owned scratch produces **byte-identical reports and manifests**, while preserving every extracted input. Independent literal parsing verifies all ten declared replacement records: each source passage occurs exactly once at its substitution step, and every old/new passage digest matches its manifest. Source/output hashes and frozen reviewed/root commit identifiers also match.

All **86 coding and 171 airline Markdown table lines** are byte-identical between the old and new reports, as are their two and three figure references, respectively. No table estimate, interval, count or figure target changes. Newly clarified prose reuses existing quantities, including the changed sensitivity denominator 15/96 and the method-specific n=12,094 calculation; it does not introduce a new experiment or estimate.

## Requested cleanup mapping

| Change | Exact final location and result |
|---|---|
| Airline governing documents — two substitutions | `results/tau2_open/report_final_v3.md:3,368`: Round 12 is named before the superseded Round 10 text. |
| Airline banner/count and manifest description — two substitutions | Airline report `:11`: correctly states 15 Round 12 replacements and six local pointers, distinguishes the further Round 13 generator changes, and distinguishes passage digests in manifests from passage text in generators. |
| Omitted-token role scope — one substitution | Airline report `:26`: 246,284 is an additional A-collection generated-token lower bound; agent/user-simulator partition is unavailable. |
| Placeholder sensitivity — one substitution | Airline report `:219`: primary retained-record E1/E2 net benefits are unchanged in this sensitivity, while denominators and resource summaries change. |
| Abstention scope — two substitutions | Airline report `:260,262`: abstention is limited to primary-rule interval-based comparisons; alternative hierarchy/tolerance outputs are separate, model-dependent and excluded. |
| Radius extrapolation — one substitution | Airline report `:59`: n=12,094 is for this normal-mixture boundary and rho under the nominal coin model, not a lower bound for other methods or a general cost of inference. |
| Coding Definitions — one substitution | `results/local_stream/report_v5.md:54`: Round 12 governs before Round 10; the existing full/coarser-filtration distinctions remain intact. |

`experiments/tau2_open/protocol_addendum_round13.md:8–26` consistently records precedence, the four scientific precision clarifications, and historical verification chronology. It explicitly says that the older verifier's hashes describe its earlier files and that the new versions had only generator assertions at handoff. This report supplies the later independent check; that historical statement should not be silently rewritten into an earlier verification claim.

The six prior airline local status pointers, known-array target/coin-model qualifications, marginal-versus-joint distinction, post-hoc status, missing-resource and chronology limitations, and exclusion of model-dependent intervals remain intact. Coding retains its distinct filtrations, additional model assumptions, approximate cluster-t conditions and descriptive-versus-model separation. Correcting these owner documents does not authorize their excluded intervals for the root paper.

## Audited identities

| Object | SHA-256 |
|---|---|
| Coding generator `make_report_v5.py` | `121fe4e4d3f30b3d982436ebb56cda36d2233de04d95880c2a7cbc7977700196` |
| Coding report `report_v5.md` | `e8e751f941d2e1d9a4de9dbafc6608c73a961cfc38b54920f1874df09cd47326` |
| Coding manifest | `8fa62d99e0ccbb6744dd8fee835b373eae03c386b5781c3f1afcde0b128bed57` |
| Airline generator `make_report_final_v3.py` | `9a0ab66034be4bb049a5361df57d3ee90728cd4b7a5d39e588443ec69fee51a9` |
| Airline report `report_final_v3.md` | `4295a7253aa1c25877b5c0471b3dd076be4289964ab10babe1eece9f34254f78` |
| Airline manifest | `a9452dbf8d443a4a8402f5f2c688d16bca6ce743edc8a522362ca98f4a621183` |

The source-report hashes remain the Round 13 audited values: coding `806d82ce35d55d9c573b806575d3d4176ffbb4e89cbe9d8d2281d92d80ae59bd`, airline `11f5691e54ac2603e229a10524685b69d91035620d20fe8748e500efc257b3cc`. Scratch `snapshot_hashes.json` and `reproduction_and_preservation.json` record exact inputs, preserved paths and generator output. No broader scientific, stylistic, index-semantic or release-artifact audit was opened here.
