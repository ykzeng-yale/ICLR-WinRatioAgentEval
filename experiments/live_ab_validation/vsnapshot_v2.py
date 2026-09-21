#!/usr/bin/env python3
"""vsnapshot_v2.py -- build the v2 actual-live snapshot, preserving v1's.

THE SETTLED DECISION.  Root, issue 12 comment 5754619899: "The snapshot
decision is settled: new v2 actual-live snapshot plus preserved v1, paired
latent seed coordinates."  And the 01:15 ruling (comment 5754149408): "create a
new versioned snapshot of the completed #11 rule at its exact reviewed commit,
and compare the independently implemented v2 validation rule against that
snapshot.  Keep the original v1 ``pinned/`` bytes, manifests, fixtures and
completed-run results immutable."

COORDINATOR_DECISIONS revision 16 item 75 records why this was needed at all:
the obsolete "keep v1's snapshot, do not re-snapshot" default was set from
issue 11 while the ruling was already sitting on issue 12.  ``PROTOCOL_V2``
section 4.2 had itself asked for a fresh snapshot, so the disagreement was a
communication mismatch, not an unresolved scientific question.

WHAT THIS DOES.  Copies the #11 live rule's modules at the exact current
reviewed commit into ``pinned_v2/``, read-only, with a ``PINNED_V2.json``
manifest recording the commit, the per-file blob ids and SHA-256s, and the
DIFFERENCE from v1's pin.  It does not touch ``pinned/``.

WHAT THIS DOES NOT DO.  It does not run the comparison grid.  Building the
snapshot and running the comparison are separate steps and only the first is
authorized here.

    .venv/bin/python experiments/live_ab_validation/vsnapshot_v2.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LIVE_AB = REPO_ROOT / "experiments" / "live_ab"
PINNED_V1 = HERE / "pinned"
PINNED_V2 = HERE / "pinned_v2"

#: The #11 modules the comparison loads.  Same three files v1 pinned, so the
#: two snapshots are comparable file for file.
MODULES = ("lab_monitor.py", "lab_enclosure.py", "lab_reference_rule.py")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), check=True,
                          capture_output=True, text=True).stdout.strip()


def build(write: bool) -> Dict[str, object]:
    head = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", str(LIVE_AB.relative_to(REPO_ROOT)))
    if dirty:
        raise SystemExit(
            f"REFUSING to snapshot: {LIVE_AB} has uncommitted changes, so the "
            f"snapshot would not correspond to any commit.\n{dirty}")

    v1 = json.loads((PINNED_V1 / "PINNED.json").read_text())
    files: List[Dict[str, object]] = []
    for name in MODULES:
        src = LIVE_AB / name
        if not src.exists():
            raise SystemExit(f"missing live rule module: {src}")
        digest = sha256_file(src)
        blob = git("rev-parse", f"HEAD:experiments/live_ab/{name}")
        v1_digest = v1["files"].get(name)
        files.append({
            "name": name,
            "source_path": str(src.relative_to(REPO_ROOT)),
            "sha256": digest,
            "git_blob": blob,
            "v1_sha256": v1_digest,
            "changed_since_v1_pin": digest != v1_digest,
            "bytes": src.stat().st_size,
        })

    manifest = {
        "schema": "live_ab_validation_v2.pinned.1",
        "purpose":
            "read-only copy of the #11 monitor at its exact current reviewed "
            "commit, loaded ONLY at the comparison step of the v2 protocol; "
            "never imported by vband.py, vgen.py, vrun.py or vfixtures.py",
        "version": "v2-cpu-validation",
        "created_unix": time.time(),
        "source_commit": head,
        "source_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "builder": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "files": {f["name"]: f["sha256"] for f in files},
        "detail": files,

        # ---- the relationship to v1, stated rather than implied ------------
        "parent_v1_snapshot": {
            "path": str(PINNED_V1.relative_to(REPO_ROOT)),
            "source_commit": v1["source_commit"],
            "files": v1["files"],
            "status": "PRESERVED AND IMMUTABLE. Not edited, not moved, not "
                      "deleted, not superseded. v1's deposited results remain "
                      "reproducible against it, and they keep v1's label.",
        },
        "changed_since_v1_pin": [f["name"] for f in files
                                 if f["changed_since_v1_pin"]],

        # ---- what "paired" means, since it was misread once already --------
        "pairing": (
            "PAIRED means replaying the SAME underlying simulation seed "
            "coordinates and latent draws across the versioned algorithms -- "
            "same namespace, same program and trial indices, same latent "
            "scores. It does NOT mean reusing the old live snapshot as v2's "
            "only reference, which was the obsolete default."),

        # ---- wording corrections carried forward, per the root -------------
        "carried_forward_corrections": {
            "stopped_roster": (
                "Random proportional ordering does NOT identify a fixed-roster "
                "effect at an outcome-selected stopping time. The root's "
                "two-order (+1,-1) witness has roster mean 0 and expected "
                "stopped-prefix mean .5. The target stays the running "
                "conditional mean; no allocation redesign follows from this."),
            "exact_feasible_set": (
                "Epsilon supersets are CONSERVATIVE ENCLOSURES, not exact "
                "feasible sets at every boundary. The universal "
                "exact-feasible-set language is withdrawn: the implementation "
                "can conservatively return [-1,1] where the exact mathematical "
                "score set is [0,1]. That is a valid observation policy and "
                "must not be described as exact enumeration under the same "
                "mathematical contract."),
            "v1_did_not_validate_11": (
                "v1 COMPARED AGAINST, and TESTED AGAINST, the #11 pin. It did "
                "not validate it. A failed comparison does not become "
                "validation because its provenance is honest."),
            "timing_summaries_not_invariant": (
                "Monotone ever-events do not make every operational summary "
                "invariant; absence of a Monte Carlo alert does not certify "
                "validity."),
        },
        "not_done_here": (
            "The comparison grid is NOT run by this script. Building the "
            "snapshot and running the comparison are separate steps and only "
            "the first is authorized."),
    }

    if write:
        PINNED_V2.mkdir(parents=True, exist_ok=True)
        for name in MODULES:
            dest = PINNED_V2 / name
            if dest.exists():
                dest.chmod(stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP
                           | stat.S_IROTH)
            dest.write_bytes((LIVE_AB / name).read_bytes())
            # read-only, exactly as v1's pinned copies are
            dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        (PINNED_V2 / "PINNED_V2.json").write_text(
            json.dumps(manifest, indent=2) + "\n")
        # verify what landed
        for f in files:
            got = sha256_file(PINNED_V2 / f["name"])
            if got != f["sha256"]:
                raise SystemExit(f"snapshot verification failed for {f['name']}")
    return manifest


def verify() -> int:
    """Check the deposited snapshot against its own manifest, and v1 against v1's."""
    rc = 0
    for label, path, key in (("v2", PINNED_V2 / "PINNED_V2.json", "files"),
                             ("v1", PINNED_V1 / "PINNED.json", "files")):
        if not path.exists():
            print(f"  {label}: MISSING {path}")
            rc = 1
            continue
        man = json.loads(path.read_text())
        for name, want in man[key].items():
            got = sha256_file(path.parent / name)
            ok = got == want
            rc |= 0 if ok else 1
            print(f"  {label} {name:<24} {'OK' if ok else 'MISMATCH'}")
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help=f"deposit the snapshot under {PINNED_V2}")
    ap.add_argument("--verify", action="store_true",
                    help="verify both snapshots against their manifests")
    args = ap.parse_args(argv)
    if args.verify:
        return verify()
    man = build(args.write)
    print(json.dumps(man, indent=2))
    if args.write:
        print(f"\nwrote {PINNED_V2}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
