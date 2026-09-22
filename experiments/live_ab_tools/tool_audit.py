"""Audit every tool in this directory for the two defects that produced the last one.

Last cycle `host_capacity_observation.py` was found answering protocol 5.7.2 with
its own `ps -Ao ...,comm` scan instead of calling `lab_hostcheck`, the audited
gate -- and I had been quoting that weaker answer in cycle comments as "the host
is clear". I found it by a lucky mis-typed label, which is not a method.

TWO DEFECT CLASSES, both of which that one instance had:

``reimplementation``
    A tool exercises a primitive for which a production module already provides
    the audited answer, WITHOUT importing that module. The reimplementation is
    the one that will be weaker, because it is the one nothing tests.

``claim_without_read``
    A result key NAMES a source it never reads -- `whole_hash_matches_config` in
    a module that never opens `config.json`. The check can then pass while the
    thing it claims to compare has drifted. This is the same shape as a receipt
    that reported "SEAL WRITTEN AND PARSED" while the parser had rejected the
    line, and as the coverage map whose event names the schema did not contain.

WHAT THIS CANNOT DO, stated because a checker that oversells itself is the defect
it is looking for:

  * A static scan CANNOT distinguish a legitimate local use of a primitive from a
    reimplementation of an audited one. Every hit is a CANDIDATE for a human read,
    and the receipt says so for each.
  * It only sees the tokens in ``CAPABILITIES`` and ``SOURCE_TOKENS``. A
    reimplementation of something not in those tables is invisible to it. The
    receipt reports the table contents so the blind spot is legible rather than
    implied.
  * It DOES audit itself. Exempting the auditor by name would be the same move as
    excluding a process from a scan by string, which is how the observer ended up
    counting itself as a foreign consumer.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]

#: production module -> (what it authoritatively answers, the primitives whose
#: direct use suggests the answer was re-derived instead of asked for).
CAPABILITIES: Dict[str, Dict[str, Any]] = {
    'lab_hostcheck': {
        'providers': ['lab_hostcheck'],
        'answers': 'protocol 5.7.2 host quiescence: foreign accelerator consumers',
        'external_programs': ['ps', 'lsof'],
        'primitives': [],
        'why_it_wins': ('full command line, self-exclusion by walking ppid edges, '
                        'and detection by open Metal resource'),
    },
    'lab_common': {
        'providers': ['lab_common'],
        'answers': 'content digests, canonical JSON, host/boot identity',
        'external_programs': ['sysctl'],
        'primitives': ['hashlib.sha256', 'hashlib.sha1', 'hashlib.md5'],
        'why_it_wins': ('one digest convention across the program; a second one '
                        'drifts silently and both look right'),
    },
    'lab_data': {
        'providers': ['lab_data'],
        'answers': 'the host-wide execution lock of protocol 5.7',
        'external_programs': [],
        'primitives': ['fcntl.flock'],
        'why_it_wins': 'the production lock path and wait policy',
    },
    # The ONE shared TMPDIR policy is `lab_common.prescribed_tmpdir` /
    # `assert_tmpdir`; `lab_prepare.assert_prescribed_tmpdir` is the refusing
    # wrapper around it. The first version of this table named lab_prepare ALONE
    # and so flagged two tools that correctly call lab_common. A table naming one
    # of several correct providers manufactures false positives, which is how a
    # checker gets ignored.
    'tmpdir_policy': {
        'providers': ['lab_common', 'lab_prepare'],
        'answers': 'the prescribed-TMPDIR rule of protocol 5.7 item 2',
        'external_programs': [],
        'primitives': ['tempfile.gettempdir'],
        'why_it_wins': 'it REFUSES; a bare comparison only reports',
    },
}

#: a token appearing in a result-key name -> the bytes a module must actually read
#: for that key to be entitled to its name.
SOURCE_TOKENS: Dict[str, List[str]] = {
    'config': ['config.json'],
    'protocol': ['protocol_FINAL.md'],
    'architecture': ['ARCHITECTURE'],
    'roster': ['roster'],
    'manifest': ['manifest'],
}

EXTERNAL_PROGRAMS = ('ps', 'lsof', 'sysctl', 'otool', 'git', 'sandbox-exec', 'codesign')

#: A tool declares its own role, in its own source, as `AUDIT_ROLE = '...'`.
#:
#: The reimplementation rule is right for a REPORTER and wrong for an INDEPENDENT
#: VERIFIER. `check_environment_digests.py` exists because root asked for a
#: checker that verifies deposited bytes; if it hashed with `lab_common.sha256_file`
#: it would be checking the producer with the producer's own helper, which is not
#: a check. Flagging it forever is how a checker gets ignored.
#:
#: The declaration lives in the audited file, not in a table here, so exempting
#: yourself is a visible commitment in the file being audited. A file that
#: declares nothing is treated as a REPORTER -- the stricter rule -- so the
#: default fails closed.
ROLE_REPORTER = 'reporter'
ROLE_VERIFIER = 'independent_verifier'
DEFAULT_ROLE = ROLE_REPORTER


def declared_role(tree: ast.AST) -> Optional[str]:
    """`AUDIT_ROLE = '...'` at module level, or None if the file declares none."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if (getattr(t, 'id', None) == 'AUDIT_ROLE'
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)):
                return n.value.value
    return None


def _imported_modules(tree: ast.AST) -> set:
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                mods.add(a.name.split('.')[0])
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split('.')[0])
    return mods


def _primitive_calls(tree: ast.AST) -> set:
    """`hashlib.sha256`, `fcntl.flock`, `tempfile.gettempdir` as dotted names."""
    found = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = getattr(n.func.value, 'id', None)
            if base:
                found.add('%s.%s' % (base, n.func.attr))
    return found


def _external_programs(tree: ast.AST) -> set:
    """Programs named as the FIRST element of any argv list literal.

    Deliberately not restricted to `subprocess.run(...)` call sites: the first
    version looked only there and MISSED `_run(['ps', ...])`, where the argv
    literal sits at the call site of a local helper.

    But "any list literal anywhere" was too wide, and it caught THIS FILE: the
    `CAPABILITIES` table holds `['ps', 'lsof']` as DATA, and the scan read its own
    configuration as a command invocation. A detector written to find
    string-based self-matching had a string-based self-match. The rule is now
    structural -- an argv literal is an ARGUMENT TO A CALL -- which still catches
    the helper indirection and no longer reads tables as commands.
    """
    found = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        for arg in list(n.args) + [kw.value for kw in n.keywords]:
            if (isinstance(arg, ast.List) and arg.elts
                    and isinstance(arg.elts[0], ast.Constant)):
                head = str(arg.elts[0].value).split('/')[-1]
                if head in EXTERNAL_PROGRAMS:
                    found.add(head)
    return found


def _named_claims(tree: ast.AST) -> List[Dict[str, str]]:
    """Result-key string literals that name a source, with their source token."""
    claims = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            key = n.value
            if not (2 < len(key) < 80) or ' ' in key:
                continue
            low = key.lower()
            for token in SOURCE_TOKENS:
                # the name must CLAIM a relation to the source, not merely mention
                # it: `config_sha256` is a value, `matches_config` is a claim.
                if token in low and any(w in low for w in
                                        ('match', 'agree', 'equal', 'same',
                                         'declared', 'consistent', 'against')):
                    claims.append({'key': key, 'source_token': token})
                    break
    return claims


def audit_file(path: Path) -> Dict[str, Any]:
    src = path.read_text('utf-8')
    tree = ast.parse(src)
    mods = _imported_modules(tree)
    prims = _primitive_calls(tree)
    progs = _external_programs(tree)

    role = declared_role(tree)
    effective_role = role or DEFAULT_ROLE

    reimplementation: List[Dict[str, Any]] = []
    for mod, cap in CAPABILITIES.items():
        if set(cap['providers']) & mods:
            continue                          # it asks one of the audited providers
        hits = sorted(set(cap['primitives']) & prims)
        prog_hits = sorted(set(cap['external_programs']) & progs)
        if hits or prog_hits:
            reimplementation.append({
                'capability': mod,
                'no_provider_imported': cap['providers'],
                'it_answers': cap['answers'],
                'primitives_used_directly': hits,
                'external_programs_used_directly': prog_hits,
                'why_the_module_wins': cap['why_it_wins'],
                'status': ('EXEMPT BY DECLARED ROLE -- this file declares itself '
                           'an independent verifier, for which re-deriving the '
                           'primitive is the point'
                           if effective_role == ROLE_VERIFIER else
                           'CANDIDATE -- a static scan cannot tell a legitimate '
                           'local use from a re-derivation; read it'),
                'exempt': effective_role == ROLE_VERIFIER,
            })

    claims = []
    for c in _named_claims(tree):
        needles = SOURCE_TOKENS[c['source_token']]
        reads = any(nd in src for nd in needles)
        claims.append(dict(c, source_is_read_by_this_module=reads,
                           needles_looked_for=needles,
                           status=('OK' if reads else
                                   'CLAIM WITHOUT READ -- the key names a source '
                                   'this module never opens')))

    return {
        'file': str(path.relative_to(REPO)),
        'imports_production_modules': sorted(m for m in mods if m.startswith('lab_')),
        'external_programs': sorted(progs),
        'digest_primitives': sorted(p for p in prims if p.startswith('hashlib.')),
        'declared_role': role,
        'effective_role': effective_role,
        'role_was_defaulted': role is None,
        'reimplementation_candidates': [c for c in reimplementation
                                        if not c.get('exempt')],
        'reimplementation_exempted_by_role': [c for c in reimplementation
                                              if c.get('exempt')],
        'named_claims': claims,
        'claims_without_read': [c for c in claims if not c['source_is_read_by_this_module']],
    }


def audit(directory: Optional[Path] = None) -> Dict[str, Any]:
    directory = Path(directory or HERE)
    files = sorted(p for p in directory.glob('*.py'))
    rows = [audit_file(p) for p in files]
    reimpl = [(r['file'], c) for r in rows for c in r['reimplementation_candidates']]
    exempt = [(r['file'], c) for r in rows
              for c in r['reimplementation_exempted_by_role']]
    bad_claims = [(r['file'], c) for r in rows for c in r['claims_without_read']]
    return {
        'schema': 'live_ab/tool_audit-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'why': ('last cycle a tool was found answering protocol 5.7.2 with its own '
                'weaker scan instead of calling lab_hostcheck. I found it by a '
                'lucky mis-typed label. This looks for the same shape on purpose.'),
        'directory': str(directory.relative_to(REPO)),
        'files_audited': len(files),
        'audits_itself': str(Path(__file__).relative_to(REPO)) in [r['file'] for r in rows],
        'reimplementation_candidates': [{'file': f, **c} for f, c in reimpl],
        'reimplementation_candidate_count': len(reimpl),
        'exempted_by_declared_role': [{'file': f, **c} for f, c in exempt],
        'exempted_by_declared_role_count': len(exempt),
        'roles': {r['file']: r['effective_role']
                  + (' (DEFAULTED)' if r['role_was_defaulted'] else ' (declared)')
                  for r in rows},
        'claims_without_read': [{'file': f, **c} for f, c in bad_claims],
        'claims_without_read_count': len(bad_claims),
        'per_file': rows,
        'capability_table': {k: v['answers'] for k, v in CAPABILITIES.items()},
        'source_token_table': SOURCE_TOKENS,
        'blind_spots': [
            'any audited capability absent from CAPABILITIES is invisible here',
            'any claim whose key does not carry a SOURCE_TOKENS token is invisible',
            'a static scan cannot see a reimplementation expressed without the '
            'primitives named in the table',
            'it cannot tell whether a hit is a real defect; every hit is a '
            'candidate for a human read and is labelled as one',
        ],
        'must_not_claim': [
            'that the tools are free of this defect -- only that these tables '
            'found these hits',
            'that a zero count means a clean directory',
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=Path(lab_common.RESULTS_ROOT) / 'TOOL_AUDIT.json')
    a = ap.parse_args(argv)
    result = audit()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, result)
    print('%d files audited; audits itself: %s'
          % (result['files_audited'], result['audits_itself']))
    print('\nreimplementation candidates (%d):' % result['reimplementation_candidate_count'])
    for c in result['reimplementation_candidates']:
        print('  %-34s -> %s  %s%s' % (
            Path(c['file']).name, ','.join(c['no_provider_imported']),
            ','.join(c['primitives_used_directly']),
            ' ' + ','.join(c['external_programs_used_directly'])
            if c['external_programs_used_directly'] else ''))
    print('\nexempted by declared role (%d):' % result['exempted_by_declared_role_count'])
    for c in result['exempted_by_declared_role']:
        print('  %-34s %s' % (Path(c['file']).name, c['capability']))
    print('\nclaims without read (%d):' % result['claims_without_read_count'])
    for c in result['claims_without_read']:
        print('  %-34s %-40s (needs %s)' % (Path(c['file']).name, c['key'],
                                            ','.join(c['needles_looked_for'])))
    print('\nwritten:', a.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
