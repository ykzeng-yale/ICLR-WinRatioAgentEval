"""Deterministic audit: no random draws, network, models, or simulations.

Usage: python3 experiments/audit_power_diagnostics.py SNAPSHOT_ROOT RECEIPT_JSON
Export the exact source pin named in the receipt before execution.
"""
import json
import hashlib
import pathlib
import sys

import numpy as np
from scipy.optimize import brentq, minimize_scalar

SNAPSHOT = pathlib.Path(sys.argv[1])
OUTPUT = pathlib.Path(sys.argv[2])
assert hashlib.sha256((SNAPSHOT / "src/winstats.py").read_bytes()).hexdigest() == '56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69'
sys.path.insert(0, str(SNAPSHOT / "src"))
from winstats import betting_log_e_ternary, normal_mixture_radius

ALPHA = 0.00625
DELTA = 0.03
OWNER_KL = 0.001149011


def binary_kl(beta, alpha=ALPHA):
    return beta * np.log(beta / alpha) + (1-beta) * np.log((1-beta)/(1-alpha))


def power_upper(n, kl, alpha=ALPHA):
    if n * kl >= np.log(1/alpha):
        return 1.0
    return brentq(lambda beta: binary_kl(beta, alpha)-n*kl, alpha, 1-1e-12)


def law_audit(q):
    z = np.array([-1., 0., 1.])
    p = np.array([q, 1-2*q, q])
    def objective(lam):
        return -float(p @ np.log1p(lam*(z+DELTA)))
    opt = minimize_scalar(objective, bounds=(0, .999999/(1-DELTA)), method="bounded",
                          options={"xatol": 1e-14})
    lam = float(opt.x)
    null_q = p/(1+lam*(z+DELTA))
    kl = -float(opt.fun)
    n = np.arange(1, 30000)
    capital = betting_log_e_ternary(q*n, q*n, n, threshold=-DELTA)
    crossing = int(n[np.flatnonzero(capital >= np.log(1/ALPHA))[0]])
    return {
        "alternative_ternary_probabilities_minus_zero_plus": p.tolist(),
        "dual_stake": lam,
        "null_ternary_probabilities_minus_zero_plus": null_q.tolist(),
        "null_probability_sum": float(null_q.sum()),
        "null_mean": float(null_q @ z),
        "reverse_kl": kl,
        "necessary_horizon_for_80pct_power_realvalued": binary_kl(.8)/kl,
        "power_upper_at_568": power_upper(568, kl),
        "power_upper_at_295": power_upper(295, kl),
        "fractional_expected_counts_betting_crossing_NOT_actual_power_or_mean_stopping_time": crossing,
    }


n = np.arange(1, 30000)
radii = normal_mixture_radius(n, alpha=ALPHA)
p_success = 433/591
result = {
    "pin": "57482e317c42e971e33871e7d879e6ca61c8eac0",
    "mode": "deterministic arithmetic, zero Monte Carlo trials",
    "alpha": ALPHA,
    "delta": DELTA,
    "owner_kl_conditional_arithmetic": {
        "kl": OWNER_KL,
        "necessary_horizon_for_80pct_power_realvalued": binary_kl(.8)/OWNER_KL,
        "necessary_integer_horizon": int(np.ceil(binary_kl(.8)/OWNER_KL)),
        "power_upper_at_568": power_upper(568, OWNER_KL),
        "power_upper_at_295": power_upper(295, OWNER_KL),
    },
    "illustrative_plugin_laws_not_claimed_to_be_owner_exact_new_input": {
        "independent_tasks_with_replacement": law_audit(p_success*(1-p_success)),
        "ordered_distinct_tasks_from_pilot": law_audit((433*158-40)/(591*590)),
        "same_task_pilot": law_audit(40/591),
    },
    "normal_radius_at_568": float(normal_mixture_radius(568, alpha=ALPHA)),
    "first_normal_crossing_on_exact_zero_empirical_mean_path": int(n[np.flatnonzero(radii < DELTA)[0]]),
    "reported_log_shortfall_shares_arithmetic_only": {
        "17097_to_6697": float(np.log(17097/6697)/np.log(17097/568)),
        "6697_to_3099": float(np.log(6697/3099)/np.log(17097/568)),
        "3099_to_568": float(np.log(3099/568)/np.log(17097/568)),
    },
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2))
