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

#: THIRD DETECTOR: a result key that READS LIKE A MEASUREMENT but whose value is a
#: constant literal.
#:
#: `claim_without_read` is keyword-based -- a key must carry a source token AND a
#: relation word -- which I flagged as trading recall for precision. This is the
#: structural generalisation, and it catches a defect I have actually shipped:
#: `negative_control_interpreter_matches_sandbox: True`, written as a LITERAL in a
#: receipt because `run_program` does not report its interpreter. Nothing compared
#: anything; the field named a check it never performed.
#:
#: A constant-valued boolean is not automatically wrong. A DECLARATION -- "this run
#: loaded no model", "this is not a trial episode" -- is deliberately a literal, and
#: those are among the most important lines in a receipt. So the two vocabularies
#: are separated and the declaration test runs FIRST, because `is_a_trial_episode`
#: would otherwise match the check vocabulary's `_is_`.
CHECK_WORDS = ('match', 'ok', 'verified', 'agree', 'equal', 'consistent',
               'complete', 'respected', 'identical', 'present', 'held', 'passed',
               'valid', 'detected', 'share', 'covered', '_is_', 'conforms')
DECLARATION_WORDS = ('is_a_', 'loaded_', 'started_', 'ran_', 'executed_',
                     'performed_', 'downloaded_', 'spent_', 'synthetic',
                     'writes_', 'sends_', 'promoted_', 'models_',
                     # `expected_valid: False` beside a computed
                     # `as_expected: u['active'] is False` is the RIGHT
                     # shape: the expectation is declared as a literal and
                     # the comparison is computed separately. Read before
                     # adding -- this is a classification, not an excuse.
                     'expected_')


def _literal_checks(tree: ast.AST) -> List[Dict[str, Any]]:
    """Dict entries `'some_key': True` / `False` where the value is a literal.

    Only dict LITERALS are read. A key whose value is any expression -- a call, a
    comparison, a name -- computes something and is not reported, which is the
    whole point of the distinction.
    """
    # A LITERAL INSIDE A BRANCH IS NOT UNMEASURED: in
    #     if not probe.is_file():
    #         return {'receipt_present': False}
    # the `if` performed the measurement and the literal records its outcome. The
    # first version of this detector flagged 14 keys, 13 of which were exactly
    # that shape -- a checker that reports thirteen non-defects to find one gets
    # switched off. Conditional ancestry is computed so only UNCONDITIONAL
    # literals, which nothing could have determined, are reported as candidates.
    conditional: set = set()
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.If, ast.IfExp, ast.Try, ast.While,
                               ast.ExceptHandler, ast.For)):
            for child in ast.walk(parent):
                if isinstance(child, ast.Dict):
                    conditional.add(id(child))

    # GUARDED BY EARLY RETURN. Syntactic nesting misses the commonest shape:
    #     if not probe.is_file():
    #         return {'receipt_present': False}
    #     ...
    #     return {'receipt_present': True}
    # The second literal is not nested in anything, yet the guard above decided
    # it. Four of the six survivors of the nesting rule were exactly this, and a
    # checker whose hits are two-thirds non-defects gets switched off.
    #
    # This is a HEURISTIC, not a control-flow analysis: a dict is treated as
    # guarded when its enclosing function has an earlier `return` inside an `if`
    # or an `except`. It can excuse a literal whose guard decided something else
    # entirely, so a guarded hit is reported in its own bucket rather than
    # dropped, and the receipt says the rule is approximate.
    guarded: set = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guard_lines = [r.lineno for br in ast.walk(fn)
                       if isinstance(br, (ast.If, ast.ExceptHandler))
                       for r in ast.walk(br) if isinstance(r, ast.Return)]
        if not guard_lines:
            continue
        first_guard = min(guard_lines)
        for d in ast.walk(fn):
            if isinstance(d, ast.Dict) and getattr(d, 'lineno', 0) > first_guard:
                guarded.add(id(d))

    # AN INITIALISER IS NOT A CLAIM. `out = {'ok': False, ...}` followed by
    # `out['ok'] = True` is the fail-safe default pattern, and it is the RIGHT
    # pattern: default to failure, set success only when something establishes it.
    # Six of the seven production hits were exactly this. A dict literal bound to
    # a name that is later subscript-assigned is treated as an initialiser.
    initialiser: set = set()
    mutated: set = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name):
                    mutated.add(tgt.value.id)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
            val = n.value
            if isinstance(val, ast.Dict):
                for tgt in tgts:
                    if isinstance(tgt, ast.Name) and tgt.id in mutated:
                        initialiser.add(id(val))

    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Dict):
            continue
        in_branch = id(n) in conditional
        is_guarded = id(n) in guarded
        for k, v in zip(n.keys, n.values):
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                continue
            if not (isinstance(v, ast.Constant) and isinstance(v.value, bool)):
                continue
            key = k.value
            low = key.lower()
            if any(w in low for w in DECLARATION_WORDS):
                kind = 'declaration'
            elif not any(w in low for w in CHECK_WORDS):
                kind = 'unclassified'
            elif in_branch:
                kind = 'branch_determined'
            elif id(n) in initialiser:
                kind = 'initialiser_later_mutated'
            elif is_guarded:
                kind = 'guarded_by_early_return'
            else:
                kind = 'literal_check'
            out.append({'key': key, 'value': v.value, 'kind': kind,
                        'line': getattr(k, 'lineno', None),
                        'inside_a_branch': in_branch,
                        'after_an_early_return_guard': is_guarded})
    return out

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


def _subscript_literal_checks(tree: ast.AST) -> List[Dict[str, Any]]:
    """`receipt['verified'] = True` -- a final claim assigned as a literal.

    THE GAP I NAMED LAST CYCLE AND DID NOT CLOSE. `_literal_checks` reads dict
    LITERALS, so a field set by subscript after construction is invisible to it.
    That is the same syntax as the `initialiser_later_mutated` bucket used for the
    opposite purpose: there the literal is the DEFAULT and the subscript computes
    the answer; here the subscript IS the answer and it is a literal.

    The two are told apart by WHICH SIDE carries the constant, so the same shape
    cannot be excused twice. Branch context applies as before, because
    `if ok: r['passed'] = True` is decided by the `if`.
    """
    conditional: set = set()
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.If, ast.IfExp, ast.Try, ast.While,
                               ast.ExceptHandler, ast.For)):
            for child in ast.walk(parent):
                if isinstance(child, ast.Assign):
                    conditional.add(id(child))

    # A DEFAULT SET IN TWO STATEMENTS IS STILL A DEFAULT.
    #     out = {name: None for name in NAMES}
    #     out['ok'] = False            <- this literal
    #     ...
    #     out['ok'] = True             <- computed elsewhere in the function
    # `lab_server.metrics` is exactly this, and its docstring says so. The
    # initialiser rule only saw one-statement dict literals, so a default spelled
    # over two statements looked like a final claim. The signal that tells them
    # apart is whether the SAME key is assigned a NON-constant value anywhere in
    # the enclosing function: if it is, the literal is a default.
    computed_keys: dict = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        keys: dict = {}
        for a in ast.walk(fn):
            if isinstance(a, ast.Assign) and len(a.targets) == 1:
                t = a.targets[0]
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and isinstance(t.slice.value, str) and a is not None):
                    # ANY later write, constant or not. The first rule demanded a
                    # NON-constant value and so missed `out['ok'] = True` in the
                    # success branch -- a constant. What makes the earlier literal
                    # a DEFAULT is being written more than once, not what the
                    # second write is made of.
                    keys.setdefault((ast.unparse(t.value), t.slice.value), 0)
                    keys[(ast.unparse(t.value), t.slice.value)] += 1
        for a in ast.walk(fn):
            if isinstance(a, ast.Assign):
                computed_keys[id(a)] = keys

    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign) or len(n.targets) != 1:
            continue
        tgt = n.targets[0]
        if not (isinstance(tgt, ast.Subscript)
                and isinstance(tgt.slice, ast.Constant)
                and isinstance(tgt.slice.value, str)):
            continue
        if not (isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, bool)):
            continue
        key = tgt.slice.value
        low = key.lower()
        if any(w in low for w in DECLARATION_WORDS):
            kind = 'declaration'
        elif not any(w in low for w in CHECK_WORDS):
            kind = 'unclassified'
        elif id(n) in conditional:
            kind = 'branch_determined'
        elif computed_keys.get(id(n), {}).get((ast.unparse(tgt.value), key), 0) > 1:
            kind = 'default_later_computed'
        else:
            kind = 'subscript_literal_check'
        out.append({'key': key, 'value': n.value.value, 'kind': kind,
                    'line': n.lineno, 'target': ast.unparse(tgt)[:60]})
    return out


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
    # THE PROVIDER IMPLEMENTS WHAT IT PROVIDES. `lab_common` is where the digest
    # helpers live, so its own `hashlib` calls are the implementation, not a
    # re-derivation of it; likewise `lab_hostcheck` and `ps`. Without this the
    # scan flags every audited module for the very capability that makes it
    # audited -- a rule that condemns its own reference implementation.
    me = path.stem

    reimplementation: List[Dict[str, Any]] = []
    for mod, cap in CAPABILITIES.items():
        if me in cap['providers']:
            continue                          # it IS the provider
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

    literals = _literal_checks(tree)
    subscripts = _subscript_literal_checks(tree)

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
        'file': lab_common.display_path(path),
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
        'literal_checks': [x for x in literals if x['kind'] == 'literal_check'],
        'subscript_literal_checks': [x for x in subscripts
                                     if x['kind'] == 'subscript_literal_check'],
        'subscript_branch_determined': sum(
            1 for x in subscripts if x['kind'] == 'branch_determined'),
        'subscript_default_later_computed': sum(
            1 for x in subscripts if x['kind'] == 'default_later_computed'),
        'declarations': [x for x in literals if x['kind'] == 'declaration'],
        'branch_determined': [x for x in literals
                              if x['kind'] == 'branch_determined'],
        'guarded_by_early_return': [x for x in literals
                                    if x['kind'] == 'guarded_by_early_return'],
        'initialiser_later_mutated': [x for x in literals
                                      if x['kind'] == 'initialiser_later_mutated'],
        'unclassified_literal_booleans': [x for x in literals
                                          if x['kind'] == 'unclassified'],
    }


def audit(directory: Optional[Path] = None) -> Dict[str, Any]:
    directory = Path(directory or HERE)
    directory = directory if directory.is_absolute() else (REPO / directory)
    files = sorted(p for p in directory.glob('*.py'))
    rows = [audit_file(p) for p in files]
    reimpl = [(r['file'], c) for r in rows for c in r['reimplementation_candidates']]
    exempt = [(r['file'], c) for r in rows
              for c in r['reimplementation_exempted_by_role']]
    bad_claims = [(r['file'], c) for r in rows for c in r['claims_without_read']]
    lit = [(r['file'], c) for r in rows for c in r['literal_checks']]
    sub = [(r['file'], c) for r in rows for c in r['subscript_literal_checks']]
    sub_branch = sum(r['subscript_branch_determined'] for r in rows)
    sub_default = sum(r['subscript_default_later_computed'] for r in rows)
    decl_n = sum(len(r['declarations']) for r in rows)
    branch_n = sum(len(r['branch_determined']) for r in rows)
    guard_n = sum(len(r['guarded_by_early_return']) for r in rows)
    init_n = sum(len(r['initialiser_later_mutated']) for r in rows)
    uncl_n = sum(len(r['unclassified_literal_booleans']) for r in rows)
    return {
        'schema': 'live_ab/tool_audit-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'why': ('last cycle a tool was found answering protocol 5.7.2 with its own '
                'weaker scan instead of calling lab_hostcheck. I found it by a '
                'lucky mis-typed label. This looks for the same shape on purpose.'),
        'directory': lab_common.display_path(directory),
        'files_audited': len(files),
        'audits_itself': lab_common.display_path(Path(__file__)) in [r['file'] for r in rows],
        'reimplementation_candidates': [{'file': f, **c} for f, c in reimpl],
        'reimplementation_candidate_count': len(reimpl),
        'exempted_by_declared_role': [{'file': f, **c} for f, c in exempt],
        'exempted_by_declared_role_count': len(exempt),
        'roles': {r['file']: r['effective_role']
                  + (' (DEFAULTED)' if r['role_was_defaulted'] else ' (declared)')
                  for r in rows},
        'claims_without_read': [{'file': f, **c} for f, c in bad_claims],
        'claims_without_read_count': len(bad_claims),
        'literal_checks': [{'file': f, **c} for f, c in lit],
        'literal_check_count': len(lit),
        'subscript_literal_checks': [{'file': f, **c} for f, c in sub],
        'subscript_literal_check_count': len(sub),
        'subscript_branch_determined_count': sub_branch,
        'subscript_default_later_computed_count': sub_default,
        'subscript_note': (
            "closes the gap named last cycle: receipt['verified'] = True is a "
            'final claim assigned as a literal, invisible to a dict-literal scan. '
            'Told apart from the initialiser pattern by WHICH SIDE carries the '
            'constant, so one shape cannot be excused twice.'),
        'declaration_count': decl_n,
        'branch_determined_count': branch_n,
        'guarded_by_early_return_count': guard_n,
        'initialiser_later_mutated_count': init_n,
        'guarded_rule_is_approximate': (
            'a dict after ANY earlier guarded return in its function is treated '
            'as guarded. It can excuse a literal whose guard decided something '
            'else, so these are bucketed, not dropped.'),
        'unclassified_literal_boolean_count': uncl_n,
        'literal_check_note': (
            'a key that READS LIKE A MEASUREMENT with a constant value. Not '
            'automatically wrong -- but it cannot have measured anything, so each '
            'one is either a declaration in disguise or a check that does not '
            'happen. Every hit needs a human read.'),
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
    ap.add_argument('--directory', type=Path, default=None,
                    help='audit this directory instead of live_ab_tools/')
    a = ap.parse_args(argv)
    result = audit(a.directory)
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
    print('\nliteral checks (%d)   [branch %d, guarded %d, initialiser %d, '
          'declarations %d, unclassified %d]:'
          % (result['literal_check_count'], result['branch_determined_count'],
             result['guarded_by_early_return_count'],
             result['initialiser_later_mutated_count'], result['declaration_count'],
             result['unclassified_literal_boolean_count']))
    for c in result['literal_checks']:
        print('  %-34s %-46s = %s  (line %s)'
              % (Path(c['file']).name, c['key'], c['value'], c['line']))
    print('\nsubscript literal checks (%d)   [branch %d, default-later-computed %d]:'
          % (result['subscript_literal_check_count'],
             result['subscript_branch_determined_count'],
             result['subscript_default_later_computed_count']))
    for c in result['subscript_literal_checks']:
        print('  %-34s %-46s = %s  (line %s)'
              % (Path(c['file']).name, c['target'], c['value'], c['line']))
    print('\nwritten:', a.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
