"""The production entry point with ONE self-comparison mutant of the serving-manifest checker.

Root's serving-manifest ruling (``reviews/serving_manifest_binding_ruling_20260924_0153.md``)
names "self-comparison" as a defect that must refuse.  Each mutation below turns one real
comparison of ``lab_serving_manifest`` into a comparison of a thing with itself, and
``tests_sm_entry`` shows that a control which passes on the real checker FAILS under it --
i.e. that the control can tell the checker from its self-comparing mutant:

* ``digest_self`` -- ``digest_problems(found, expected)`` compares the artifact's digest with
  ITSELF (``digest_problems(found, found)``): hashing against itself, so a null or different
  configuration digest no longer refuses;
* ``facts_self`` -- ``runtime_facts`` returns ``recorded_facts(manifest)``: the manifest is
  compared with a copy of itself instead of the runtime, so a changed or added library no
  longer refuses.

``python sm_mutant_entry.py --mutation NAME <lab_orchestrator argv>``.  Nothing else changes.
A TEST DOUBLE; outside the harness pin.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_orchestrator                                                 # noqa: E402
import lab_serving_manifest                                             # noqa: E402

MUTATIONS: tuple[str, ...] = ('digest_self', 'facts_self')


def apply(name: str) -> None:
    """Install mutation ``name`` in this process's ``lab_serving_manifest``."""
    if name == 'digest_self':
        original = lab_serving_manifest.digest_problems
        lab_serving_manifest.digest_problems = lambda found, expected: original(found, found)
    elif name == 'facts_self':
        lab_serving_manifest.runtime_facts = (
            lambda manifest, **kw: lab_serving_manifest.recorded_facts(manifest))
    else:
        raise ValueError(name)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--mutation' or argv[1] not in MUTATIONS:
        sys.stderr.write('sm_mutant_entry: --mutation {%s} comes first\n'
                         % ','.join(MUTATIONS))
        return 2
    apply(argv[1])
    return lab_orchestrator.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
