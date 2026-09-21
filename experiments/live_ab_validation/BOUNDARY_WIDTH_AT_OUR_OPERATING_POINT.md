# WITHDRAWN 2026-09-21 — THIS DIAGNOSTIC MEASURED THE WRONG OBJECT

**Every number in this file is withdrawn.** The root rejected it
(`reviews/v2_reference_audit_20260921_0343.md`, main `25e018d`) and I verified each reason against
`reference/eb_reference.py` before accepting them. The file is PRESERVED rather than deleted because the root
asked for the failed diagnostic to be kept, and because a withdrawn measurement that is still readable is worth
more than one that is quietly gone.

**Three independent errors, any one of which invalidates the comparison:**

1. **WRONG BOUNDARY FAMILY.** I called `poly_stitching_bound`, a STITCHED boundary. The selected reference is
   `boundary_type = "mixture"` (`eb_reference.py:66`). They are different objects; comparing one to the frozen
   band says nothing about the other.
2. **WRONG ERROR BUDGET.** I passed `alpha = 0.00625` straight into the stitched function, which applies no split.
   The selected wrapper's `confseq_eb` performs the `alpha/2` split INTERNALLY (`eb_reference.py:34-36, 164-165`),
   and its own docstring warns that pre-halving would silently double the budget. My call and the wrapper's are
   therefore not at the same level.
3. **WRONG CLOCK.** I used `variance x n` as the intrinsic time. That is a plug-in proxy and, as the root puts it,
   it "does not identify the predictable residual clock" the method actually accumulates. The real clock is a
   predictable process, not a constant times n.

**Specifically NOT ACCEPTED and not to be quoted from this file or from my 03:46 comment:** the 8,867-pair figure;
"tighter at every n"; "no crossover in our range"; the 1.93x ratio; the revised certifiable margin 0.1137; and any
sizing paragraph built on them.

**What survives, because the root said so explicitly and I am not entitled to inflate it either:** neither a
narrower bound on its own, nor this diagnostic mistake, proves any failure of the primary theorem. The primary is
untouched by all of this.

**Separately, my earlier from-the-theorem cross-check's error is now identified precisely** and it is not what I
said it was: it is an omitted `B^2` under `sqrt(A + B^2)`, not a log constant. If it is repaired, it must be
repaired transparently with the original preserved.

**What a replacement would have to do:** identify the actual family, scale, alpha convention and clock of the
object under comparison, and evaluate both at the same level. I have not done that, and until I do there is no
measured claim here at all.

---

# Is the author reference actually tighter at OUR n and OUR tie mass?

The root's ruling was explicit: "superiority at our sample size is unproved. State assumptions for the exact
method used." I flagged the same thing as my own open uncertainty and predicted the answer might be NO, because
variance-adaptive bounds usually pay a penalty at small n and can be worse below a crossover -- which is what I
measured for two OTHER constructions. This file settles it by measurement.

## Convention, stated before the numbers, per the standing rule

Every number here is a DETERMINISTIC BOUNDARY CALCULATION: the width of a boundary as a function of n. None is a
power statement, none is an expected stopping time, and none is a study result. The EB column carries one extra
condition: it is evaluated at the intrinsic time implied by the PILOT's measured variance, so it is conditional
on the realized variance equalling that value. It is a plug-in, not a guarantee.

Inputs: alpha = 0.00625 per band; frozen band = winstats.normal_mixture_radius(n, alpha, rho=100); author band =
the vendored poly_stitching_bound at v_opt = 10, c = 0; cross-task success variance 0.4136 and hierarchy variance
0.6873, both measured on the pilot (descriptive).

## Result 1: the reference is tighter at EVERY n in our range. There is no crossover.

| n | frozen NM radius | author EB, var .4136 | author EB, var .6873 | NM / EB(.4136) |
|---|---|---|---|---|
| 100 | 0.465693 | 0.257317 | 0.338082 | 1.810x |
| 295 | 0.228707 | 0.155297 | 0.202653 | 1.473x |
| 568 | 0.157952 | 0.113655 | 0.147980 | 1.390x |
| 2000 | 0.083230 | 0.061946 | 0.080440 | 1.344x |

MY PREDICTION WAS WRONG. I expected a crossover below which the adaptive bound is worse. For this construction at
this tuning there is none in our range: it is tighter from n = 100, the first look n_min permits, onward. The
prediction was formed from WSR-EB and HRMS-EB, which are different objects; generalizing from them to this one was
the same over-generalization I have now made five times.

## Result 2: like-for-like sample requirement, one convention throughout

"First n at which the radius falls below the margin, assuming the observed difference stays exactly zero."

| margin | frozen NM | author EB (var .4136) | ratio |
|---|---|---|---|
| 0.03 | 17,097 | 8,867 | 1.93x |
| 0.05 | 5,789 | 3,110 | 1.86x |
| 0.10 | 1,378 | 742 | 1.86x |
| 0.15 | 626 | 318 | 1.97x |

Certifiable margin at the 568-pair horizon with an observed difference of zero: frozen 0.1580, author EB 0.1137.

## What this does and does not change

DOES NOT change any decision. The reference is REFERENCE-ONLY by the root's ruling and my own; it cannot override
the primary, and no trial is re-decided by it. The primary stays frozen.

DOES NOT rescue the deploy route. 8,867 against an available horizon of at most 565 is still short by a factor of
about sixteen. The earlier finding stands: roughly half the shortfall is that the two systems are genuinely
identical on the top tier, and no estimator touches that.

DOES matter for the PAPER's sizing section, which is the deliverable this whole line of work produced. The honest
sentence is now: for a 3-point margin against an equally accurate candidate, a guarded cross-arrival trial needs
about 17,100 pairs with the range-only band and about 8,900 with a variance-adaptive band at the pilot's variance,
both being deterministic path calculations at an observed difference of zero, against an information floor of about
3,100 pairs at 80% power -- a POWERED quantity that must not be divided into either of the others.

CAVEAT I am not hiding: the EB numbers are conditional on the realized variance matching the pilot. A trial whose
realized variance is larger gets a larger intrinsic time and a wider band, and the advantage shrinks. The right
way to state the gain is as a function of realized variance, not as a single factor, and that is how it should
enter the paper.
