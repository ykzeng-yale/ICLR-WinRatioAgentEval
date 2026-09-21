"""Identity fingerprints for the resource guard: WHOLE-FILE and TIMED-CORE.

WHY THIS FILE EXISTS
--------------------
Guard v2 refuses a projection that is not bound to the run it prices
(`identity_unverifiable`).  Binding needs an answer to "identity of WHAT?", and
the root supplied the principle rather than the mechanism:

    "Reconcile the recorded `vrun` hash with the exact measured source; a
     WHOLE-FILE HASH DIFFERENCE ALONE DOES NOT PROVE THE TIMED CORE CHANGED."

and, on a different artifact, demonstrated the technique:

    "The two live source edits are executable-AST identical after removing
     documentation."

So this module computes two different identities and keeps them apart:

  * ``whole_file`` -- sha256 of the bytes.  Moves when a comment moves.  It is
    the right identity for "is this the same FILE", and the wrong one for "was
    the timed work the same".
  * ``timed_core`` -- sha256 over the AST of the transitive closure of the
    functions the timing harness actually executes, with docstrings stripped.
    Moves only when executable structure changes.

NEITHER is a measurement.  A matching timed core says the timed code is the
same, not that the timing is still valid: the environment, the data and the
call counts are separate facts the receipt records separately.  Do not use a
timed-core match to excuse a missing measurement.
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


def identities(module_dir: Path = HERE,
               policy: Optional[str] = None,
               workload: Optional[str] = None,
               receipt: Optional[str] = None,
               config_paths: Sequence[str] = ("cells.json",)) -> Dict[str, object]:
    """The five identities guard v2 requires, each computed rather than asserted.

    ``code`` is the TIMED-CORE identity, not the whole-file one, because the
    guard's question is whether the priced work is the work being proposed.
    The whole-file digests ride along under ``code_whole_file`` so a reader can
    see both and so a documentation-only edit is visibly distinguishable from a
    behavioural one.
    """
    src = _sources(module_dir, TIMED_MODULES)
    core = timed_core_identity(src)
    cfg = hashlib.sha256()
    for c in config_paths:
        cfg.update((module_dir / c).read_bytes())
    return {
        "code": core["timed_core_sha256"],
        "config": cfg.hexdigest(),
        "policy": policy,
        "workload": workload,
        "receipt": receipt,
        "code_whole_file": whole_file_identity(module_dir),
        "timed_core_detail": core,
        "what_code_means": (
            "sha256 over the docstring-stripped AST of the transitive closure "
            "of the functions the delivered receipt declares it timed. A "
            "whole-file difference does not move it; an executable change "
            "does."),
        "not_a_measurement": (
            "A matching timed core says the timed CODE is unchanged. It does "
            "not say the timing is still valid: environment, data and call "
            "counts are separate recorded facts. Never use a timed-core match "
            "to excuse a missing measurement."),
    }


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
