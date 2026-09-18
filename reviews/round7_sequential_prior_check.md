# Sequential U-statistic prior check

Scope: bounded source audit only; no source, method, experiment, or Git changes. The reviewer previously contributed this project's theory and is not independent of those contributions.

**Verdict: include this reference.** Manole and Ramdas, *IEEE Transactions on Information Theory* 69(7):4641–4658 (2023), DOI [10.1109/TIT.2023.3250099](https://ieeexplore.ieee.org/document/10056755). The [arXiv version history](https://arxiv.org/abs/2103.09267v4) dates v4 to March 12, 2023; the HTML's rendered 2026 date is not its revision date.

In [§4.2](https://arxiv.org/html/2103.09267v4#S4.SS2), the general U-statistic discussion concerns i.i.d. observations from **one distribution** and a **symmetric** kernel, targeting its expectation on two independent draws. The authors identify an integrable U-statistic as a reverse martingale and state that their Theorem 7 machinery extends to two-sided confidence sequences. With suitable concentration bounds—available for bounded kernels—the guarantee is finite-sample simultaneous coverage, \(\Pr\{\forall t\ge2:\theta\in C_t\}\ge1-\delta\), hence coverage at arbitrary stopping times. The generic application is discussed in prose, rather than presented as a separate closed-form theorem for every bounded kernel. Positive definiteness is required by their neighboring V-statistic result, not this U-statistic argument.

Our two-arm statistic averages an oriented, nonsymmetric kernel over independent arm samples. It is not literally their displayed symmetric one-sample statistic. An adaptation must establish its own sampling and concentration arguments; this distinction does not make finite-sample sequential U-statistic inference novel. Their paper also treats two-sample MMD, so describing the entire paper as exclusively one-sample would be inaccurate.

Suggested related-work text (two sentences):

> Manole and Ramdas (2023, §4.2) develop reverse-martingale methods yielding finite-sample confidence sequences for bounded symmetric U-statistics under i.i.d. sampling. This provides relevant sequential U-statistic prior art, although their general symmetric one-sample discussion is distinct from our oriented two-arm comparison and partially revealed workflow records.

No implementation or experiment was assessed in this check.
