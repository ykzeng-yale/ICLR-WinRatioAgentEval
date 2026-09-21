"""FREEZE STATUS: how much of the v2 live freeze bundle exists, checked by the real gate.

Root handoff item 2, 2026-09-21 17:37 (`reviews/ablation_root_disposition_20260921_1737.md`):

    "Return one exact v2 bundle binding the actual live adapter to reviewed CPU
     semantics: task/pair roster and exclusions, actual finite horizon, fixed AB/BA
     assignment, event/enrollment bounds, error allocation/guardrails, current
     installed open-model/server/resource identity, serving assumptions,
     all-attempt usage and failure accounting, and current capacity. ... If
     capacity is unavailable, report that specific blocker with timestamp and the
     completed freeze materials."

WHY THIS IS NOT A HAND-WRITTEN GAP LIST
---------------------------------------
``lab_common.build_freeze_bundle`` already fails closed: it raises ``FreezeIncomplete``
naming every missing key, every extra key and every null-or-'unknown' hole anywhere in
the tree.  So the authoritative list of what is still unfrozen is whatever THAT function
says, not what I believe.  This module resolves every component it can offline, hands the
result to the real gate, and records the gate's own verdict.

A freeze status that agreed with itself would be worth nothing -- the same defect shape as
an invariant that compares an operator with itself.

WHAT THIS MODULE WILL NOT DO
----------------------------
No model call.  No server start.  No trial episode.  No calibration episode.  No network
access, no download.  The foreign llama-server processes on ports 8193/8191 belong to
DTR-AgentEvals; they are observed with ps/lsof elsewhere and are never signalled here.

Nothing in here freezes anything.  It reports what a freeze would still need.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
#: THE LIVE_AB HARNESS DIRECTORY -- deliberately NOT this file's own directory.
#: lab_common.HARNESS_FILES is a GLOB over experiments/live_ab/*.py plus
#: config.json (lab_common.py:317-324), and it feeds harness_file_sha256, a
#: freeze-bundle key.  This module is a REPORTING tool: if it lived in that
#: directory, every improvement to it would move a freeze pin, and after a bundle
#: was deposited it would break preflight outright.  It lived there for one
#: cycle by my mistake -- HARNESS_FILES went 26 -> 27 -- and was moved out before
#: any bundle existed.  Nothing reporting on the freeze may sit inside the set
#: the freeze pins.
LAB = HERE.parent / "live_ab"
for _p in (str(LAB),):
    if _p not in sys.path:                                     # pragma: no cover
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402
from lab_common import (canonical_json, sha256_canonical,      # noqa: E402
                        sha256_file, sha256_text)

REPO = HERE.parents[1]
HERE = LAB   # every path below refers to the harness dir, not this tool's dir

#: The GGUF files named by config.json, as installed.  Hashing them is pure local
#: I/O: no model is loaded and no server is contacted.
GGUF_PATHS = {
    "coder": (Path.home() / ".cache/huggingface/hub"
              / "models--Qwen--Qwen2.5-Coder-7B-Instruct-GGUF/snapshots"
              / "13fb94bfda8c8cf22497dc57b78f391a9acb426a"
              / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
    "t3": (Path.home() / ".cache/huggingface/hub"
           / "models--ibm-granite--granite-3.3-8b-instruct-GGUF/snapshots"
           / "e40e9dd739c7be00fa965c16ce167088190ce114"
           / "granite-3.3-8b-instruct-Q4_K_M.gguf"),
}

#: Why each key that cannot be resolved offline cannot be, and what would resolve it.
#: A key absent from this map and absent from the resolved set is an UNEXPLAINED hole,
#: which the report flags rather than quietly omitting.
BLOCKED_REASONS: Dict[str, Dict[str, str]] = {
    "serving_manifest_sha256": {
        "blocked_on": "a running llama-server of MY OWN",
        "why": ("the manifest describes the serving process actually in front of the "
                "model: build, flags, slot configuration. It cannot be derived from "
                "files on disk."),
        "resolved_by": "starting the adapter's own server under the quiescence gate"},
    "golden_props_sha256": {
        "blocked_on": "a running llama-server of MY OWN",
        "why": "/props is read from a live server.",
        "resolved_by": "one preflight scrape per server after the gate opens"},
    "golden_generation_settings_sha256": {
        "blocked_on": "a running llama-server of MY OWN",
        "why": "the generation settings block is reported by a live server.",
        "resolved_by": "one preflight scrape per server after the gate opens"},
    "prefreeze_head": {
        "blocked_on": "the prefreeze calibration, 240 episodes",
        "why": ("config.prefreeze.calibration_plan is 5 repetitions x 6 smoke tasks x 2 "
                "workflows x 2 models x 2 concurrency levels. Those are MODEL CALLS."),
        "resolved_by": "running calibration after explicit clearance and quiescence"},
    "prefreeze_bytes": {
        "blocked_on": "the prefreeze calibration, 240 episodes",
        "why": "same artifact as prefreeze_head.",
        "resolved_by": "running calibration after explicit clearance and quiescence"},
    "prefreeze_file_sha256": {
        "blocked_on": "the prefreeze calibration, 240 episodes",
        "why": "same artifact as prefreeze_head.",
        "resolved_by": "running calibration after explicit clearance and quiescence"},
    "roster_sha256": {
        "blocked_on": "the offline roster build",
        "why": ("exclusion rules include reference_fails_verify and reference_timeout, "
                "so the roster is only final after every reference solution has been "
                "executed in the sandbox. CPU only, no model call -- but not yet run."),
        "resolved_by": "lab_data roster build; next cycle's work, needs no quiescence"},
    "task_content_sha256": {
        "blocked_on": "the offline roster build",
        "why": "same artifact as roster_sha256.",
        "resolved_by": "lab_data roster build; next cycle's work, needs no quiescence"},
    "arrival_order_sha256": {
        "blocked_on": "the roster",
        "why": ("stratified arrival orders are derived from the final roster and "
                "design_seed_base; they are write-once once the roster is fixed."),
        "resolved_by": "lab_design, immediately after the roster build"},
    "containment_probe_sha256": {
        "blocked_on": "one sandbox containment probe",
        "why": "the probe must actually run in the sandbox to certify containment.",
        "resolved_by": "a CPU-only probe run; no model, no quiescence needed"},
    "sandbox_profile_sha256": {
        "blocked_on": "the sandbox profile artifact",
        "why": "config.sandbox.profile_sha256 is still null in the committed config.",
        "resolved_by": "depositing the profile the sandbox actually enforces"},
    "environment_lock_sha256": {
        "blocked_on": "the environment lock artifact",
        "why": "config.environment_lock_sha256 is still null in the committed config.",
        "resolved_by": "depositing the interpreter/package lock actually installed"},
    "hardware_allowlist": {
        "blocked_on": "an explicit declaration",
        "why": ("config.hardware_allowlist is null. The host is arm64-darwin, but the "
                "allowlist is a DESIGN declaration about which hosts may run the "
                "program, not an observation of the one I happen to be on."),
        "resolved_by": "declaring it in config.json as part of the freeze"},
    "license_evidence_sha256": {
        "blocked_on": "deposited licence evidence",
        "why": ("both models declare apache-2.0 in config, but "
                "servers.*.license_evidence_sha256 is null: no evidence file is "
                "deposited. A declared licence is not evidence of one."),
        "resolved_by": "depositing the licence texts actually retrieved"},
    "derivation_sha256": {
        "blocked_on": "the derivation document",
        "why": "not yet deposited under this name.",
        "resolved_by": "depositing the horizon/allocation derivation"},
    "planning_sha256": {
        "blocked_on": "the planning document",
        "why": "not yet deposited under this name.",
        "resolved_by": "depositing the planning ledger"},
    "run_book_sha256": {
        "blocked_on": "the run book",
        "why": "not yet deposited under this name.",
        "resolved_by": "depositing the operator run book"},
}


def _gguf_digests() -> Tuple[Dict[str, Any], List[str]]:
    """sha256 of each installed GGUF, checked against config's frozen expectation."""
    cfg = json.loads((HERE / "config.json").read_text())
    out: Dict[str, Any] = {}
    problems: List[str] = []
    for name, path in GGUF_PATHS.items():
        want = cfg["servers"][name]["sha256_expected"]
        want_bytes = cfg["servers"][name]["bytes"]
        if not path.is_file():
            problems.append(f"{name}: GGUF absent at the installed path")
            continue
        size = path.stat().st_size
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        got = h.hexdigest()
        out[name] = {"sha256": got, "bytes": size,
                     "matches_config_expectation": got == want and size == want_bytes}
        if got != want:
            problems.append(f"{name}: GGUF sha256 {got} != config {want}")
        if size != want_bytes:
            problems.append(f"{name}: GGUF bytes {size} != config {want_bytes}")
    return out, problems


def resolve_offline() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Every bundle component derivable from committed bytes and installed files."""
    cfg = json.loads((HERE / "config.json").read_text())
    gguf, gguf_problems = _gguf_digests()

    parts: Dict[str, Any] = {
        "protocol_version": str(cfg["protocol_version"]),
        "config_sha256": sha256_file(HERE / "config.json"),
        "rule_block_sha256": lab_common.rule_block_sha256(cfg),
        "harness_file_sha256": lab_common.harness_file_hashes(),
        "reused_file_sha256": {n: sha256_file(lab_common.LS_DIR / n)
                               for n in lab_common.REUSED_FILES
                               if (lab_common.LS_DIR / n).is_file()},
        "winstats_sha256": sha256_file(lab_common.SRC_DIR / "winstats.py"),
        "receipt_mask_sha256": sha256_canonical(cfg["receipt"]["mask"]),
        "gguf_sha256": {k: v["sha256"] for k, v in gguf.items()},
    }
    # Filled by PREPARATION_MANIFEST once they are real artifacts rather than
    # nulls.  Each is read from config ONLY when non-null: a null here must stay
    # a reported gap, never a silently-supplied None that build_freeze_bundle
    # would then name as a hole in a confusing place.
    if cfg.get("environment_lock_sha256"):
        parts["environment_lock_sha256"] = cfg["environment_lock_sha256"]
    if cfg.get("hardware_allowlist"):
        parts["hardware_allowlist"] = list(cfg["hardware_allowlist"])
    if (cfg.get("sandbox") or {}).get("profile_sha256"):
        parts["sandbox_profile_sha256"] = cfg["sandbox"]["profile_sha256"]

    protocol = HERE / "design" / "protocol_FINAL.md"
    if protocol.is_file():
        parts["protocol_sha256"] = sha256_file(protocol)

    evidence = {
        "gguf": gguf,
        "gguf_problems": gguf_problems,
        "winstats_matches_config": (parts["winstats_sha256"]
                                    == cfg["monitor"]["winstats_sha256"]),
        "harness_files_hashed": len(parts["harness_file_sha256"]),
        "reused_files_hashed": len(parts["reused_file_sha256"]),
        "protocol_document": str(protocol.relative_to(REPO)) if protocol.is_file()
                             else "ABSENT at design/protocol_FINAL.md",
        "from_preparation_manifest": sorted(
            k for k in ("environment_lock_sha256", "hardware_allowlist",
                        "sandbox_profile_sha256") if k in parts),
    }
    return parts, evidence


def status() -> Dict[str, Any]:
    """Resolve what can be resolved, then let the REAL gate name what is missing."""
    parts, evidence = resolve_offline()

    gate_verdict: Dict[str, Any]
    try:
        lab_common.build_freeze_bundle(dict(parts))
        gate_verdict = {"complete": True,
                        "note": "build_freeze_bundle accepted the bundle"}
    except lab_common.FreezeIncomplete as exc:
        gate_verdict = {"complete": False, "raised": "FreezeIncomplete",
                        "detail": json.loads(str(exc))}

    missing = list(gate_verdict.get("detail", {}).get("missing", []))
    holes = list(gate_verdict.get("detail", {}).get("null_or_unknown", []))
    unexplained = sorted(k for k in missing if k not in BLOCKED_REASONS)

    return {
        "schema": "live_ab.freeze_status.1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authority": ("root handoff item 2, "
                      "reviews/ablation_root_disposition_20260921_1737.md"),
        "what_this_is": ("A STATUS REPORT, not a freeze. Nothing here is frozen and no "
                         "bundle is published. The gap list below is produced by "
                         "lab_common.build_freeze_bundle itself, which fails closed."),
        "nothing_executed": ["no model call", "no server start", "no trial episode",
                             "no calibration episode", "no network access",
                             "foreign llama-server processes not signalled"],
        "required_keys_total": len(lab_common.FREEZE_BUNDLE_KEYS),
        "resolved_offline": sorted(parts),
        "resolved_offline_count": len(parts),
        "gate_verdict": gate_verdict,
        "still_required": sorted(missing),
        "null_or_unknown_in_supplied_parts": holes,
        "unexplained_gaps": unexplained,
        "unexplained_gaps_note": ("a key that is missing AND carries no recorded reason "
                                  "is a hole in my accounting, not just in the freeze"),
        "blocked_reasons": {k: BLOCKED_REASONS[k] for k in sorted(missing)
                            if k in BLOCKED_REASONS},
        "evidence": evidence,
        "components_root_asked_for": {
            "task_pair_roster_and_exclusions": "NOT YET -- offline, next cycle, no quiescence needed",
            "actual_finite_horizon": "NOT YET -- derives from the roster's n_pairs",
            "fixed_AB_BA_assignment": (
                "PARTIAL and deliberately so: the stratified ARRIVAL ORDER is write-once "
                "and freezable from the roster, but the A/B coin is drawn per pre-enrolled "
                "pair at dispatch from os.urandom and is never redrawn (config.coin). "
                "Freezing the coin in advance would change the design, not record it."),
            "event_enrollment_bounds": (
                "NOT YET -- request_timeout_s and episode_hard_cap_s are COMPUTED from "
                "c_max via config.execution rules, and c_max comes from calibration. "
                "config marks episode_hard_cap_is_computed_never_typed: true."),
            "error_allocation_and_guardrails": (
                "ALREADY FROZEN and preserved unchanged: alpha_program 0.05, alpha_trial "
                "0.0125, alpha_gate 0.00625, delta 0.03, n_min 100, rho 100.0, "
                "variance_process n. Not re-derived here."),
            "installed_model_server_resource_identity": (
                "MODEL side RESOLVED: both GGUFs hashed and matching config. SERVER side "
                "blocked on a server of my own."),
            "serving_assumptions": "BLOCKED on a running server of my own",
            "all_attempt_usage_and_failure_accounting": "NOT YET -- next cycle",
            "current_capacity": ("DELIVERED 2026-09-21T17:49:46Z, "
                                 "results/live_ab/CAPACITY_RECEIPT_20260921_1749.json; "
                                 "NOT quiescent, live execution not cleared"),
        },
        "serving_identity_position": {
            "question_put_to_root": ("should the freeze name a model-serving identity I "
                                     "do not own? The llama-servers on ports 8193/8191 "
                                     "belong to DTR-AgentEvals."),
            "default_taken_on_silence": ("declare them an EXTERNAL dependency I do not "
                                         "control and record an open blocker, rather "
                                         "than assert a serving identity I cannot hold. "
                                         "config.json already names MY OWN ports 8091 "
                                         "and 8092, which are distinct from theirs."),
            "consequence": ("the freeze's serving components stay open until the "
                            "adapter's own server runs under the quiescence gate"),
        },
        "must_not_claim": [
            "that any part of the live program is frozen -- none of it is",
            "that the resolved components constitute a partial freeze that could be "
            "executed against; build_freeze_bundle refuses anything incomplete and that "
            "refusal is the point",
            "that the host will be quiescent later, or that capacity was measured over "
            "any interval; the capacity receipt is one sample",
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    result = status()
    text = canonical_json(result) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
