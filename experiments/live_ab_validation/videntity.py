"""EXPLORATORY SOURCE-DIFFERENCE DIAGNOSTIC. **NOT an authorization identity.**

OVERRULED 2026-09-21 by the root (`reviews/v2_panel_root_disposition_20260921_0750.md`):

    "Keep `videntity` as an exploratory source-difference diagnostic; DO NOT USE IT
     ALONE TO AUTHORIZE A TIMING PROJECTION. ... For automatic execution binding, use
     exact immutable source/config/workload and loaded-reference/binary/environment
     pins for the actual complete entry point. WHOLE-FILE PINS ARE ADEQUATE AND
     SIMPLER HERE."

I proposed binding the resource guard's `code` identity to a transitive-call-graph
"timed core" so that documentation edits would not move it. The root refuted that with
three counterexamples, all of which **I reproduced independently** before accepting
(`reviews/evidence/v2_identity_checks_20260921_0750.py`, run against this tree):

  1. **It misses module-level constants.** Changing `vgen.OPERATIONAL_EPS` from `1e-9`
     to `1.0` leaves the fingerprint **identical**, yet at revealed cost 10 against a
     pending lower cost 11 the forward certificate's truth value FLIPS (margin 0.45:
     fires at 1e-9, does not fire at 1). A behaviour-changing edit this "identity"
     cannot see is not an identity.
  2. **A partly-missing entry point was silently accepted.** I raised only on a wholly
     EMPTY closure, so requesting a nonexistent entry alongside a real one narrowed the
     scope and still returned a digest. I had guarded the vacuous case and described it
     as guarding the population -- my own recurring error, in my own guard.
  3. **The measured entry point was outside its own scope.** `vpanel` (the orchestrator)
     and `eb_reference` (the reference bridge) appear in no member, so the identity
     omitted the very work being timed, along with the storage, accumulator and flush
     paths.

Defect 2 is repaired below because it is a plain bug. Defects 1 and 3 are NOT repaired:
chasing them would grow exactly the "fragile call-graph gate" the root ruled against.
Whole-file pinning for the complete entry point lives in `vpins.py` and is what binds
execution.

**This module may be used to ASK what source changed between two snapshots. It may not
be used to decide that a projection still applies.** `identities()` is removed; the
authorization surface it offered is gone rather than deprecated, so nothing can import
it by habit.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

HERE = Path(__file__).resolve().parent

#: The scope the delivered combined receipt declares it timed, verbatim from
#: ``combined_workload_timing.json["timed_scope"]["primary_only"]``:
#:   "vgen.draw_trial + vrun.evaluate_trial + vrun.trial_rows into a discard
#:    RowSink"
#: Entry points are (module, qualified name) pairs.
TIMED_ENTRY_POINTS: Tuple[Tuple[str, str], ...] = (
    ("vgen", "draw_trial"),
    ("vrun", "evaluate_trial"),
    ("vrun", "trial_rows"),
    ("vrun", "RowSink"),
)

#: Modules the closure is allowed to walk into.  Anything outside is a leaf:
#: numpy's identity is the environment pin's business, not ours.
TIMED_MODULES = ("vrun", "vgen", "vband")


class IdentityError(RuntimeError):
    pass


def _strip_docstrings(node: ast.AST) -> ast.AST:
    """Remove docstrings so documentation edits do not move the identity."""
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef, ast.Module)):
            body = getattr(n, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                n.body = body[1:] or [ast.Pass()]
    return node


def _top_level_defs(tree: ast.Module) -> Dict[str, ast.AST]:
    out: Dict[str, ast.AST] = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[n.name] = n
    return out


def _names_used(node: ast.AST) -> Set[str]:
    """Every bare name and ``mod.attr`` tail this node mentions."""
    out: Set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _sources(module_dir: Path, modules: Sequence[str]) -> Dict[str, str]:
    src: Dict[str, str] = {}
    for m in modules:
        p = module_dir / f"{m}.py"
        if not p.exists():
            raise IdentityError(f"missing module source: {p}")
        src[m] = p.read_text()
    return src


def timed_core_closure(sources: Dict[str, str],
                       entry_points: Sequence[Tuple[str, str]] = TIMED_ENTRY_POINTS
                       ) -> List[Tuple[str, str]]:
    """The transitive set of top-level defs reachable from the entry points.

    Resolution is by NAME across the declared modules, which over-approximates:
    a helper named ``_band`` in two modules pulls both in.  Over-approximating
    is the safe direction -- it can only make the identity move when it need
    not have, never hold still when it should have moved.
    """
    trees = {m: ast.parse(s) for m, s in sources.items()}
    defs = {m: _top_level_defs(t) for m, t in trees.items()}
    seen: Set[Tuple[str, str]] = set()
    stack = list(entry_points)
    while stack:
        mod, name = stack.pop()
        if (mod, name) in seen:
            continue
        node = defs.get(mod, {}).get(name)
        if node is None:
            continue
        seen.add((mod, name))
        for used in _names_used(node):
            for m2 in sources:
                if used in defs.get(m2, {}) and (m2, used) not in seen:
                    stack.append((m2, used))
    return sorted(seen)


def timed_core_identity(sources: Dict[str, str],
                        entry_points: Sequence[Tuple[str, str]] = TIMED_ENTRY_POINTS
                        ) -> Dict[str, object]:
    """AST identity of the timed closure, docstrings removed."""
    trees = {m: ast.parse(s) for m, s in sources.items()}
    defs = {m: _top_level_defs(t) for m, t in trees.items()}
    # EVERY requested entry point must resolve.  Checking only for an EMPTY
    # closure let a nonexistent entry narrow the scope silently while a digest
    # was still returned -- the root's counterexample 2, and my own
    # guard-the-vacuous-case-and-call-it-guarded error inside my own guard.
    unresolved = [f"{m}.{n}" for m, n in entry_points
                  if n not in defs.get(m, {})]
    if unresolved:
        raise IdentityError(
            f"requested entry points do not resolve: {unresolved}. A narrowed "
            f"scope that still returns a digest is worse than no digest.")
    closure = timed_core_closure(sources, entry_points)
    if not closure:
        raise IdentityError(
            "the timed closure is EMPTY; an identity over nothing would match "
            "anything, which is worse than no identity at all")
    h = hashlib.sha256()
    per: Dict[str, str] = {}
    for mod, name in closure:
        node = _strip_docstrings(defs[mod][name])
        dumped = ast.dump(node, annotate_fields=True, include_attributes=False)
        d = hashlib.sha256(dumped.encode()).hexdigest()
        per[f"{mod}.{name}"] = d
        h.update(f"{mod}.{name}:{d}\n".encode())
    return {"timed_core_sha256": h.hexdigest(),
            "members": len(closure),
            "per_member_sha256": per,
            "entry_points": [f"{m}.{n}" for m, n in entry_points]}


def whole_file_identity(module_dir: Path,
                        modules: Sequence[str] = TIMED_MODULES) -> Dict[str, str]:
    return {f"{m}.py": hashlib.sha256((module_dir / f"{m}.py").read_bytes()).hexdigest()
            for m in modules}


#: ``identities()`` REMOVED 2026-09-21.  It returned the five fields guard v2
#: requires and was therefore an authorization surface built on a fingerprint
#: that misses module-level constants and omits the orchestrator.  Deleted
#: rather than deprecated so nothing imports it out of habit.  Use
#: ``vpins.entry_point_pins()``.
IDENTITIES_REMOVED = (
    "videntity.identities() was removed; use vpins.entry_point_pins(). See the "
    "module banner for the three counterexamples that refuted it.")


def identities(*_a, **_k):                                     # pragma: no cover
    raise IdentityError(IDENTITIES_REMOVED)


def compare(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, object]:
    """Which members of the timed core moved between two source snapshots."""
    b = timed_core_identity(before)
    a = timed_core_identity(after)
    bp, ap = b["per_member_sha256"], a["per_member_sha256"]
    moved = sorted(k for k in set(bp) & set(ap) if bp[k] != ap[k])
    return {"before_sha256": b["timed_core_sha256"],
            "after_sha256": a["timed_core_sha256"],
            "identical": b["timed_core_sha256"] == a["timed_core_sha256"],
            "members_before": b["members"], "members_after": a["members"],
            "added": sorted(set(ap) - set(bp)),
            "removed": sorted(set(bp) - set(ap)),
            "changed": moved}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--policy", default=None)
    ap.add_argument("--workload", default=None)
    ap.add_argument("--receipt", default=None)
    a = ap.parse_args(argv)
    print(json.dumps(identities(policy=a.policy, workload=a.workload,
                                receipt=a.receipt), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
