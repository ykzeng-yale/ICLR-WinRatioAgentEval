# Round 8: replay and decision-rule pre-integration audit

**Recommendation: correct the replay sampler and deterministic seed construction before integration.** Both issues are demonstrated with tiny isolated examples. The launch-rule OR is not automatically a nominal-error violation as currently written, but it needs explicit descriptive scope and conflict handling if generalized.

Reviewed external commit **`e1ea314578a6f15dd2ee48ba64ed95a15a426354`**. Scope: `experiments/run_replay.py`, the new decision-rule additions in `experiments/decision_disagreement.py`, their committed output summaries, and the decision-figure labels. Root source and external worker files remained read-only; no Git mutation or full replay was run. Relevant source snapshots, tiny-test code, and outputs are retained under `work/round8_replay_review/`. All-pairs implementation and completion-order inputs are assigned to other reviewers and are not certified here.

## 1. Confirmed sampler bug: the selected B pool and its index bound can differ

**Location:** `experiments/run_replay.py:68`; introduced by this commit.

The single expression draws a B task twice independently: the first draw selects the array to index, while the second draw supplies the array length used by `rng.integers`. They are not necessarily the same task. With different replicate counts this can select an out-of-range index or sample valid indices according to the wrong task's replicate count.

The exact snapshot `stream` function was extracted via Python's AST and executed with only NumPy supplied; importing the rest of the replay module was unnecessary. The toy pool contains two tasks in the same domain, with one B replicate for one task and three for the other. A single arrival with `np.random.default_rng(5)` and design `cross_arrival_stratified` raises:

```text
IndexError: index 2 is out of bounds for axis 0 with size 1
```

A controlled RNG witness independently confirms the precise cause: select the one-row task for the left-hand array, select the three-row task when computing its length, then draw replicate index 2. Among 20 separately seeded one-arrival toy calls, seed 5 produces that error. No benchmark replay was needed.

**Important qualification:** if every B task in a stratum has the same number of replicates, the extra independent task draw does not change the desired sampling distribution; it merely consumes an unnecessary random draw. This test therefore establishes a real general sampler defect, but does not by itself prove that the committed balanced-pool result values are biased. The worker's derivative input pool was not available at the inspected local paths, and its exact cardinalities were not audited in this bounded task.

**Repair:** sample the B task once, store its pool, and draw the replicate from that pool:

```python
B = []
for i in idx:
    j = rng.choice(by_dom[keys[i][0]])
    runs_b = PB[keys[j]]
    B.append(runs_b[rng.integers(0, len(runs_b))])
B = np.stack(B)
```

Add a same-stratum test with unequal replicate counts and inspect the selected task/run indices. Do not silently discard failed draws, because that would change the sampling law. Updating the sampling code changes RNG consumption even in balanced pools, so preserve the original result snapshot and regenerate affected replay outputs after correction.

## 2. Confirmed reproducibility bug: Python's salted string hash determines the stream seed

**Location:** `experiments/run_replay.py:93`. This expression predates the new design but remains active in the reviewed commit:

```python
np.random.default_rng([seed, hash(design) % 1000])
```

Python string hashes depend on the interpreter's hash randomization state. The same recorded numerical seed and design therefore do not determine the same random stream across ordinary independent processes. Three fresh interpreters with numerical seed 0 demonstrated:

| `PYTHONHASHSEED` | `hash('cross_arrival_stratified') % 1000` | First generated integer |
|---:|---:|---:|
| 1 | 663 | 456931 |
| 2 | 789 | 637582 |
| 3 | 647 | 478572 |

Each integer came from the same expression `rng.integers(0, 1000000, 5)` after initializing the code's RNG. The committed replay manifest records neither the effective hash-derived seed nor `PYTHONHASHSEED`. A code checksum cannot recover those missing values. Reducing hashes modulo 1000 also permits avoidable collisions between design names.

**Repair:** use a fixed explicit design-to-integer mapping, or a stable cryptographic digest/SeedSequence construction, and record the master seed, design seed identifiers, scenario identifiers, and numerical-library versions. Add a tiny cross-process reproducibility check under different `PYTHONHASHSEED` values. Regenerate the affected replay outputs only after preserving their existing baseline; do not describe existing unrecorded-seed outputs as exactly reproducible.

## 3. Launch-rule interpretation: distinguish directional testing, global claims, and conflicting labels

**Location:** `experiments/decision_disagreement.py:80–81`; CIs are defined at lines 33–37.

The new A predicate is success superiority **OR** success noninferiority plus cost superiority. The B predicate uses the reverse direction. Inspection of this script, its output log/summary, and the supplied figure found **no explicit claim that the whole matrix or bidirectional OR rule has familywise 5% error control**. The figure does not currently show the launch-rule column. The existing language describes historical decision disagreements, although the comments call the construction a “common” launch rule without a source. Keep the rule explicitly defined and descriptive unless a separate error-control claim is proved and a practice attribution is sourced.

It would be incorrect to assert automatically that this fixed-direction OR spends 5% in each branch and therefore reaches 10%: `clustered_diff` uses a **two-sided 95% interval**, so its directional tails are nominally 2.5%. Assuming valid marginal intervals, each fixed-direction branch has error at most 2.5% under its corresponding false-branch null, and the two-branch union is bounded by 5%. The conjunction branch does not require another Bonferroni penalty within that branch. These are conditional statements about valid fixed-sample marginal intervals; the task-clustered t approximation does not supply exact finite-sample validity automatically.

Those facts do **not** establish a 5% guarantee simultaneously over both directions, all 25 system-pair rows, all decision rules, or repeated looks. For illustration, with independent normal success/cost estimators at a joint equality null and noninferiority effectively satisfied, rejecting in either direction approaches the probability that either of two two-sided 95% intervals excludes zero, `1 - .95**2 = .0975`. This is an illustrative construction, not an estimated error rate for these archived benchmarks.

### Confirmed orientation-dependent conflict, absent from the 25 current rows

The two directional launch predicates are not mutually exclusive. With margin `.03`, take:

```text
success CI = [.001, .020]
cost CI    = [.100, .200]  # A costs more
```

A passes through success superiority. B passes through success noninferiority and lower cost. The code reports A because its conditional is evaluated first. Swap the two system names and negate/reverse both intervals: both predicates still hold, and the code again reports the newly named A. Thus an arbitrary label order chooses opposite physical systems.

Direct inspection of the committed 25-row CSV found **zero rows with both predicates true**. This conflict does not invalidate those particular recorded labels, but it is a real general behavior requiring an explicit policy before broader use. Either retain a fixed candidate-versus-incumbent direction and evaluate only that launch predicate, or compute both booleans and label the joint-pass case `conflict`/`both_acceptable` under a documented policy. Do not silently call the A-first tie-break an orientation-invariant winner.

## Handoff

Fix the two replay issues before importing regenerated replay results. Preserve external worker ownership and existing snapshots. The launch-rule matrix can remain a descriptive comparison once its target, pointwise scope, and directional tie policy are explicit; no unsupported global nominal-error claim should be added. The current 25 rows have no detected directional conflict, and this review does not request a full disagreement rerun merely to establish that fact.

The tiny evidence consists of `tiny_checks.py`, `tiny_checks.json`, `archived_launch_conflicts.json`, and the source-hash manifest in `work/round8_replay_review/`. No release package or root scientific source was modified.
