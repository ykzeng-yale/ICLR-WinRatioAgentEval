# Anonymized release copies (Round 10)

Made by `experiments/local_stream/make_release_anon_v3.py` (Round 9: `make_release_anon.py`). The originals (raw evidence, frozen documents) are **not** edited and remain the provenance record; these copies are an explicit allowlist for an anonymous submission package, not approval to publish the whole research branch anonymously. Only identifying path/name strings were replaced: `<REPO>` = repository root, `<HOME>` = home directory, `<TMP>` = per-user/per-session temp directory, `<USER>` = account name, `<HOST>` = machine name. Hardware/OS/package descriptions, hashes, timestamps and all outcomes are unchanged. Files with 0 replacements are byte-identical copies included for completeness.

**Portability.** Regeneration of the anonymized copies is LOCATION-DEPENDENT: the strings that are replaced are derived at run time from the executing account, repository location and host, and a different checkout may lack git-ignored originals. No byte-for-byte portability of the anonymized copies is claimed; original_sha256 ties each committed copy to its original.

| original | anonymized copy | sha256 of original | replacements |
|---|---|---|---|
| `results/local_stream/run_manifest.json` | `results/local_stream/release_anon/results/local_stream/run_manifest.json` | `f2efc949ff13745aae0b2c5f902de6af05087a606c03803a6e9bc0a25815aa4f` | <REPO> x1, <TMP> x3, <HOME> x8 |
| `results/local_stream/episodes.jsonl` | `results/local_stream/release_anon/results/local_stream/episodes.jsonl` | `95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0` | <TMP> x411, <HOME> x3 |
| `results/local_stream/design.json` | `results/local_stream/release_anon/results/local_stream/design.json` | `6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457` | none |
| `results/local_stream/monitor_state.json` | `results/local_stream/release_anon/results/local_stream/monitor_state.json` | `daeca32682832150f7485b15fb46d7ef15b5e2c78a590b09bee4b706f4ef1773` | none |
| `results/local_stream/dryrun/run_manifest.json` | `results/local_stream/release_anon/results/local_stream/dryrun/run_manifest.json` | `cc0f2778ec9f45766b6a6ee55ea06fcfc560c0b973d385ecabd1e4c35a5539d6` | <REPO> x1, <TMP> x3, <HOME> x4 |
| `results/local_stream/dryrun/episodes.jsonl` | `results/local_stream/release_anon/results/local_stream/dryrun/episodes.jsonl` | `5850724f41c56f6f78cfbad8292b7900f694b8bb3cf02d6579c904e3226c9887` | <TMP> x22 |
| `results/local_stream/timing_pilot/summary.json` | `results/local_stream/release_anon/results/local_stream/timing_pilot/summary.json` | `d0fc70db0efbd802a0a38ca33084477a45ecc6d2291e67da06f8a138aed236fe` | <TMP> x1, <HOME> x4 |
| `results/local_stream/timing_pilot/episodes.jsonl` | `results/local_stream/release_anon/results/local_stream/timing_pilot/episodes.jsonl` | `907a5d5950e3304d751dccbb22df0a3c5ef71292aa41e7870ec95d3af964922b` | <TMP> x9 |
| `results/local_stream/v1_pre_round9/report.md` | `results/local_stream/release_anon/results/local_stream/v1_pre_round9/report.md` | `9023783dc4328f204510a2a34fba4df2ece6d33e43d78e464558f4c446358b92` | <REPO> x1 |
| `results/local_stream/v1_pre_round9/summary.json` | `results/local_stream/release_anon/results/local_stream/v1_pre_round9/summary.json` | `778f2f4f896aed76c4d2d746b67308dc3a24fd79b9b04cd9193e0e4c6767ef78` | none |
| `work/local_stream/data/data_manifest.json` | `results/local_stream/release_anon/local_data_manifest.anon.json` | `4b626bac275ec11f1b9c38d1ac94babd659de007b5dd51416591a0b697b69e82` | <REPO> x3 |
| `experiments/local_stream/config.json` | `results/local_stream/release_anon/experiments/local_stream/config.json` | `0b40e6530ff70660116d409ad3887e0999ab5d73fa43af1f88fd93df032f4b73` | none |
| `experiments/local_stream/README.md` | `results/local_stream/release_anon/experiments/local_stream/README.md` | `09d8bcc57d07563c63dd3293c8064aa4f73b7a5458de7ce280f958549e6fd5f0` | <REPO> x2 |
| `experiments/local_stream/protocol.md` | `results/local_stream/release_anon/experiments/local_stream/protocol.md` | `14a5a81a62fc3144135e463fb8138d2b11b3f1f19b1b9bafec723d49c52242d9` | none |

Round 10 note: `work/local_stream/data/data_manifest.json` is git-ignored. Its sanitized copy is now `results/local_stream/release_anon/local_data_manifest.anon.json`; the Round 9 mapping pointed to a copy under `release_anon/work/...`, which the ignore rule `work/` excluded from the repository. The committed `results/local_stream/data_manifest.json` (pinned source URLs and hashes) is the primary data-provenance file.

Code files that also contain an absolute path or account-specific string and must be sanitized (or regenerated) when an anonymous code package is built: see `MAPPING.json -> code_files_to_check`.
