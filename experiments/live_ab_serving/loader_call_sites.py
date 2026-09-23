"""Deposit the loader call sites, with their linkage into the candidate, as excerpts.

Root, 2026-09-23 16:30 (reviews/build_snapshot_review_20260923_1630.md): "The
sentence asserting every loader call site in `common/`, `src/` and
`tools/server/` uses argument-free `load_all()` is a literal in the snapshot
generator, without collected caller locations/source excerpts ... If the owner
relies on an all-default-call-sites proof, deposit the exact existing matching
source excerpts with paths, line locations and source-file hashes rather than
another summary assertion."

The contract does rely on it: the dynamic bound enumerates the DEFAULT search
locations, which is only the whole search if nothing linked into the candidate
passes a directory. So this collects, from the candidate's own source tree:

  * every occurrence of the loader entry points and `dlopen` -- as bare
    identifiers, called or not -- in every C-family file of the tree (build/
    included), with the exact line, its path, line and column, and the SHA-256
    of the file it came from; and
  * for each file, whether it is actually LINKED into the launcher or one of
    its nine non-system members -- derived from the generated build rules
    (`build.ninja` link and archive statements, followed through static
    archives) and `compile_commands.json` (object -> source), not from where a
    file happens to sit. Unity-build translation units are followed through
    their generated `#include` lines to the real sources.

v2. The review of the v1 deposit (findings deposit/0-5) found the following;
each is fixed here, and the v1 receipts stay as written (they are write-once):

  0 "The linked-call finding covers 341 of 363 linked translation units: 22
    are never scanned, including build/common/build-info.cpp and
    build/tools/ui/ui.cpp". Every unit in the linkage set is now read at the
    path the linkage names, whatever its directory or suffix, and so is the
    unity unit itself, not only the sources it includes. A linked unit that
    cannot be read is a linkage problem.
  1 "A header-inline explicit-directory call compiled into a linked member
    never blocks the finding, and the nm -u dlopen observation the scope
    relies on for headers cannot see one". No inclusion evidence is read, so
    no header is shown to be not included. An EXPLICIT or UNCLASSIFIED
    load_all* occurrence in ANY scanned header therefore blocks the finding,
    and so does one in an unlinked source file that some scanned file
    #includes. The scope no longer points to the dlopen-import observation
    for headers.
  2 "References to the loader without call parentheses (function pointer,
    macro alias) are invisible". Every entry point is matched as a bare
    identifier, and a load_all* occurrence that is not a recognised call or
    declaration is UNCLASSIFIED.
  3 "Line-level string/comment detection wrongly classifies real
    explicit-directory calls as mentions or default calls" and 4 "... are
    documentation text inside a block comment but are recorded with context
    'code'". A C/C++ lexer over the whole file replaces the line heuristic.
    Every occurrence on a line is classified from its own tokens, and an
    unclear lexical state is UNCLASSIFIED.
  5 "The ninja parser silently drops LINK_LIBRARIES indented by one space, and
    file-scope $variables". Any indented line after a build line is a binding,
    $var and ${var} are expanded from file scope, and anything left unexpanded
    is a problem.

READ-ONLY. Nothing is built, configured, executed or loaded; no native tool is
run. It reads text files of an existing tree and writes one receipt.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

#: The receipts. v1 is superseded (review findings deposit/0-5) but kept as it
#: was written: both are write-once, so v2 is a new file, never an overwrite.
MANIFEST = 'results/live_ab/CANDIDATE_INSTRUMENT_MANIFEST.json'
CALL_SITE_RECEIPT_V1 = 'results/live_ab/LOADER_CALL_SITE_EXCERPTS.json'
BUILD_RULES_V1 = 'results/live_ab/LOADER_LINKAGE_BUILD_RULES.json'
CALL_SITE_RECEIPT = 'results/live_ab/LOADER_CALL_SITE_EXCERPTS_v2.json'
BUILD_RULES = 'results/live_ab/LOADER_LINKAGE_BUILD_RULES_v2.json'

#: What is searched for. Deliberately broader than the call the contract depends
#: on. Each name is matched as a BARE identifier (review finding 2: v1 required
#: '(' after the name, so a function pointer or a macro alias was invisible).
PATTERNS = {n: r'(?<![\w$])%s(?![\w$])' % n for n in (
    'ggml_backend_load_all', 'ggml_backend_load_all_from_path', 'ggml_backend_load',
    'ggml_backend_load_best', 'dl_load_library', 'dlopen', 'GGML_BACKEND_PATH')}
LOAD_ALL = ('ggml_backend_load_all', 'ggml_backend_load_all_from_path')
_NAMES = sorted(PATTERNS, key=len, reverse=True)
_NAMES_RX = re.compile(r'(?<![\w$])(%s)(?![\w$])' % '|'.join(_NAMES))
#: A unit the C/C++ lexer does not read (assembler) is searched as text; a
#: Mach-O symbol carries one leading underscore.
TEXT_PATTERN = r'(?<![\w$])_?(%s)(?![\w$])' % '|'.join(_NAMES)
_NAMES_RX_TEXT = re.compile(TEXT_PATTERN)
_PREFILTER = ('ggml_backend_load', 'dl_load_library', 'dlopen', 'GGML_BACKEND_PATH')

TU_SUFFIXES = ('.c', '.cc', '.cpp', '.cxx', '.c++', '.cu', '.m', '.mm')
HEADER_SUFFIXES = ('.h', '.hh', '.hpp', '.hxx', '.h++', '.cuh', '.inc', '.inl',
                   '.ipp', '.tcc', '.tpp')
SOURCE_SUFFIXES = TU_SUFFIXES + HEADER_SUFFIXES
#: Raw strings are C++ (and a GNU C extension): in these a raw-string shape is
#: read as one but marked unclear, since the reading depends on the dialect.
C_MODE_SUFFIXES = ('.c', '.m')

TARGETS = ['bin/llama-server', 'bin/libllama-server-impl.dylib',
           'bin/libggml.0.24.0.dylib', 'bin/libggml-base.0.24.0.dylib',
           'bin/libggml-cpu.0.24.0.dylib', 'bin/libggml-blas.0.24.0.dylib',
           'bin/libggml-metal.0.24.0.dylib', 'bin/libllama.0.4.1.dylib',
           'bin/libllama-common.0.4.1.dylib', 'bin/libmtmd.0.4.1.dylib']


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- build-graph parsing (pure; tested on synthetic text) ----------------------
_NINJA_CONT = re.compile(r'\$(\$|\n[ ]*)')
_NINJA_REF = re.compile(r'\$(?:\{([A-Za-z0-9_.-]+)\}|([A-Za-z0-9_-]+)|([\s\S])|\Z)')
_NINJA_LET = re.compile(r'([A-Za-z0-9_.-]+)[ ]*=[ ]*(.*)\Z', re.S)
_NINJA_COMMENT = re.compile(r'[ ]*#')


def _ninja_logical_lines(text: str):
    """(first line number, logical line, verbatim text) for each logical line.

    A line ending in an odd number of `$` continues onto the next, and ninja
    drops the `$`, the newline and the next line's leading spaces. `$$` is an
    escaped dollar, so `$$` at the end of a line does NOT continue it. A
    comment line never continues."""
    raw = text.replace('\r\n', '\n').split('\n')
    i = 0
    while i < len(raw):
        j = i
        if not _NINJA_COMMENT.match(raw[i]):
            while j + 1 < len(raw) and (len(raw[j]) - len(raw[j].rstrip('$'))) % 2:
                j += 1
        verbatim = '\n'.join(raw[i:j + 1])
        logical = _NINJA_CONT.sub(lambda m: '$$' if m.group(1) == '$' else '', verbatim)
        yield i + 1, logical, verbatim
        i = j + 1


def _ninja_eval(raw: str, lookup):
    """Expand `$name`, `${name}` and the escapes `$$`, `$ `, `$:`, as ninja
    does when it parses the file. Returns (value, problems). A reference that
    lookup cannot resolve is LEFT IN PLACE and reported: ninja would expand
    it to nothing, and a silently empty LINK_LIBRARIES is the failure this
    exists to prevent (review finding 5)."""
    problems = []

    def sub(m):
        name = m.group(1) or m.group(2)
        if name:
            v = lookup(name)
            if v is None:
                problems.append('$%s is not defined where it is used (ninja would '
                                'expand it to nothing)' % name)
                return m.group(0)
            return v
        if m.group(3) in ('$', ' ', ':'):
            return m.group(3)
        problems.append('bad $-escape %r' % m.group(0))
        return m.group(0)

    return _NINJA_REF.sub(sub, raw), problems


def _ninja_build_tokens(rest: str) -> list:
    """Paths (escapes kept, expanded later) and the separators ':', '|', '||'
    and '|@' of a build line. A path ends at an unescaped space, ':' or '|'."""
    toks, i, n = [], 0, len(rest)
    while i < n:
        c = rest[i]
        if c == ' ':
            i += 1
        elif c == ':':
            toks.append(':')
            i += 1
        elif c == '|':
            two = rest[i:i + 2]
            toks.append(two if two in ('||', '|@') else '|')
            i += len(toks[-1])
        else:
            j = i
            while j < n and rest[j] not in ' :|':
                j += 2 if rest[j] == '$' else 1
            toks.append(rest[i:min(j, n)])
            i = j
    return toks


def _finish_build(state: dict, p: dict) -> None:
    toks = p['toks']
    if ':' not in toks:
        state['problems'].append('%s: build line has no ":"' % p['where'])
        return
    k = toks.index(':')
    outs = toks[:k]
    outs = outs[:outs.index('|')] if '|' in outs else outs
    rest = toks[k + 1:]
    if not rest or rest[0] in ('|', '||', '|@', ':'):
        state['problems'].append('%s: build line names no rule' % p['where'])
        return
    groups, mode = {'explicit': [], 'implicit': [], 'order_only': [], 'validations': []}, 'explicit'
    for t in rest[1:]:
        if t in ('|', '||', '|@'):
            mode = {'|': 'implicit', '||': 'order_only', '|@': 'validations'}[t]
        elif t == ':':
            state['problems'].append('%s: a second ":" on a build line' % p['where'])
        else:
            groups[mode].append(t)
    problems, variables = [], {}
    # Edge bindings are evaluated against FILE scope at parse time (ninja's
    # ParseEdge); paths are then evaluated against the edge's own bindings
    # first, then file scope.
    for key, raw in p['lets']:
        variables[key], probs = _ninja_eval(raw, state['bindings'].get)
        problems += ['%s: %s: %s' % (p['where'], key, x) for x in probs]

    def lookup(name):
        return variables[name] if name in variables else state['bindings'].get(name)

    def ev(tok):
        v, probs = _ninja_eval(tok, lookup)
        problems.extend('%s: path %s: %s' % (p['where'], tok, x) for x in probs)
        return v

    stmt = {'rule': rest[0], 'variables': variables, 'problems': problems,
            'source': p['source'], 'line': p['line'], 'seq': p['seq'],
            'block': '\n'.join(p['block'])}
    for g, items in groups.items():
        stmt[g] = [ev(t) for t in items]
    for o in (ev(t) for t in outs):
        if o in state['statements']:
            state['problems'].append('%s: output %s is also produced at %s:%d' % (
                p['where'], o, state['statements'][o]['source'],
                state['statements'][o]['line']))
        state['statements'][o] = stmt


def _parse_ninja_into(state: dict, text: str, source: str, read_include, active) -> None:
    pending, block_kind = None, None

    def finish():
        nonlocal pending
        if pending is not None:
            _finish_build(state, pending)
        pending = None

    for lineno, logical, verbatim in _ninja_logical_lines(text):
        where = '%s:%d' % (source, lineno)
        if _NINJA_COMMENT.match(logical):
            # ninja skips a comment line entirely: it does NOT end a block.
            if pending is not None:
                pending['held'].append(verbatim)
            continue
        if not logical.strip():
            finish()
            block_kind = None
            continue
        if logical[0] in ' \t':
            # REVIEW FINDING 5: v1 took only a two-space indent as a binding;
            # ninja reads ANY leading spaces as an indent.
            if '\t' in logical[:len(logical) - len(logical.lstrip(' \t'))]:
                state['problems'].append('%s: a tab in the indentation (ninja rejects it)'
                                         % where)
            if pending is not None:
                m = _NINJA_LET.match(logical.lstrip(' \t'))
                if m is None:
                    state['problems'].append('%s: indented line is not a binding' % where)
                else:
                    pending['lets'].append((m.group(1), m.group(2)))
                pending['block'] += pending['held'] + [verbatim]
                pending['held'] = []
            elif block_kind not in ('rule', 'pool'):
                state['problems'].append('%s: indented line outside any statement' % where)
            continue
        finish()
        block_kind = None
        word = logical.split(' ', 1)[0]
        if word == 'build':
            state['seq'] += 1
            pending = {'toks': _ninja_build_tokens(logical[len('build'):]),
                       'block': [verbatim], 'held': [], 'lets': [], 'where': where,
                       'source': source, 'line': lineno, 'seq': state['seq']}
        elif word in ('rule', 'pool'):
            block_kind = word
        elif word == 'default':
            pass
        elif word in ('include', 'subninja'):
            path, probs = _ninja_eval(logical[len(word):].strip(), state['bindings'].get)
            state['problems'].extend('%s: %s' % (where, x) for x in probs)
            record = {'path': path, 'kind': word, 'from': where, 'followed': False}
            state['includes'].append(record)
            text_in = read_include(path) if (read_include and word == 'include'
                                             and path not in active) else None
            if text_in is None:
                state['problems'].append('%s: %s %s is not followed' % (where, word, path))
                continue
            n_st, n_b = len(state['statements']), len(state['binding_lines'])
            _parse_ninja_into(state, text_in, path, read_include, active | {path})
            record.update(followed=True, statements=len(state['statements']) - n_st,
                          bindings=len(state['binding_lines']) - n_b)
        else:
            m = _NINJA_LET.match(logical)
            if m is None:
                state['problems'].append('%s: line not understood' % where)
                continue
            value, probs = _ninja_eval(m.group(2), state['bindings'].get)
            state['problems'].extend('%s: %s: %s' % (where, m.group(1), x) for x in probs)
            state['bindings'][m.group(1)] = value
            state['seq'] += 1
            state['binding_lines'].append({'seq': state['seq'], 'source': source,
                                           'line': lineno, 'name': m.group(1),
                                           'text': verbatim})
    finish()


def parse_ninja(text: str, read_include=None, source: str = 'build.ninja') -> dict:
    """{'statements': output -> statement, 'bindings': the file scope,
    'binding_lines', 'includes', 'problems'}.

    Follows ninja's own lexer: a `$`-continued line is joined; comment lines
    are skipped and do not end a block; any indented line after a build line
    is one of its bindings; a blank line ends the block. `$var` and `${var}`
    are expanded from file scope, in file order, as ninja does at parse time,
    and one that cannot be expanded is a problem, attached to its statement
    when it sits in one. `include` is followed through `read_include(path)`
    (same scope); `subninja`, or an include that cannot be read, is a
    problem. The indented bindings under a statement matter: CMake names the
    static archives and shared libraries a target links in `LINK_LIBRARIES`,
    NOT in the explicit inputs -- the launcher's explicit inputs are one
    object file."""
    state = {'statements': {}, 'bindings': {}, 'binding_lines': [], 'includes': [],
             'problems': [], 'seq': 0}
    _parse_ninja_into(state, text, source, read_include, frozenset((source,)))
    del state['seq']
    return state


def ninja_statements(text: str) -> dict:
    """output -> {'rule', 'explicit', 'implicit', 'order_only', 'variables',
    'problems', ...}: the statements of parse_ninja(text). File-level problems
    (a line not understood, an include not followed) are in
    parse_ninja(text)['problems']; every caller in this module reads them there."""
    return parse_ninja(text)['statements']


def linked_objects(statements: dict, target: str, _seen=None) -> list:
    """Every object file linked into `target`, following static archives named
    either as explicit inputs or in `LINK_LIBRARIES`.

    Shared libraries are NOT followed: each is a separate member of the closure,
    examined as its own target. A problem found while parsing a statement on
    the walk comes back as a 'NINJA-PROBLEM:' entry, so it cannot be dropped."""
    seen = _seen if _seen is not None else set()
    if target in seen or target not in statements:
        return []
    seen.add(target)
    st = statements[target]
    objs = ['NINJA-PROBLEM:' + p for p in st.get('problems', ())]
    objs += [i for i in st['explicit'] if i.endswith('.o')]
    archives = [i for i in st['explicit'] if i.endswith('.a')]
    archives += [t for t in (st.get('variables', {}).get('LINK_LIBRARIES') or '').split()
                 if t.endswith('.a') and t not in archives]
    for a in archives:
        if a not in statements:
            objs.append('UNRESOLVED-ARCHIVE:' + a)
            continue
        objs.extend(linked_objects(statements, a, seen))
    return objs


def unity_includes(text: str) -> list:
    """The real sources a generated unity translation unit includes."""
    return re.findall(r'^\s*#\s*include\s+"([^"]+)"', text, re.M)


def unity_include_directives(text: str) -> int:
    """How many `#include` directives the unity unit has, in any form. If this
    differs from len(unity_includes(text)), a source is included in a form the
    linkage walk does not follow."""
    return len(re.findall(r'^[ \t]*#[ \t]*include\b', text, re.M))


# -- the C/C++ lexer (review findings 3 and 4) ---------------------------------
_SPLICE = re.compile(r'\\[ \t\f\v]*\n')
_CODE = re.compile(r"""
    (?P<block>/\*)
  | (?P<line>//)
  | (?P<raw>(?<![\w$])(?:u8|[uUL])?R")
  | (?P<num>(?<![\w$.])\.?[0-9](?:[eEpP][+-]|[\w$.])*'[\w$](?:[eEpP][+-]|'[\w$]|[\w$.])*)
  | (?P<dq>")
  | (?P<sq>')
""", re.X)
_BODY = {'"': re.compile(r'(?:[^"\\\n]|\\.)*', re.S),
         "'": re.compile(r"(?:[^'\\\n]|\\.)*", re.S)}
_RAW_DELIM = re.compile(r'([^ ()\\\t\v\f\n]{0,16})\(')
_TOKEN = re.compile(r"\.?[0-9](?:[eEpP][+-]|'[\w$]|[\w$.])*|[^\W\d][\w$]*|\$[\w$]*")
_PUNCT2 = frozenset(('::', '->', '&&', '||', '##', '<<', '>>', '<=', '>=', '==', '!=',
                     '++', '--'))
_MAX_ARG_TOKENS = 4096


def lexer_mode(suffix: str) -> str:
    s = suffix.lower()
    if s in C_MODE_SUFFIXES:
        return 'c'
    if s in SOURCE_SUFFIXES:
        return 'c++'
    return 'text'


class Lexed:
    """One file lexed as C/C++ over its WHOLE text, not line by line.

    Phase 1-2: CRLF is read as LF, and every backslash-newline (clang and gcc
    also accept blanks between them) is spliced out; line and column are
    reported in the unspliced text. Phase 3: block comments across lines,
    `//` comments (continued by a splice), string and character literals with
    escapes, C++14 digit separators (`1'000` is a number, not a quote), and
    raw strings R"d(...)d", which are read on the UNSPLICED text because the
    splices are reverted inside them. `spans` holds the non-code regions:
    'comment', 'string', 'char', or 'unclear' (an unterminated literal or
    comment, a malformed raw string, or a raw string in a C-mode file)."""

    def __init__(self, text: str, mode: str = 'c++'):
        norm = text.replace('\r\n', '\n')
        self.norm, self.mode = norm, mode
        pieces, self._cut_s, self._cut_n, self._cum = [], [], [], []
        last = slen = width = 0
        for m in _SPLICE.finditer(norm):
            pieces.append(norm[last:m.start()])
            slen += m.start() - last
            width += m.end() - m.start()
            self._cut_s.append(slen)
            self._cut_n.append(m.start())
            self._cum.append(width)
            last = m.end()
        pieces.append(norm[last:])
        self.text = ''.join(pieces)
        self._line_starts = [0] + [m.end() for m in re.finditer('\n', norm)]
        self.spans = self._lex()
        self._span_starts = [s for s, _, _ in self.spans]

    # positions: spliced (self.text) <-> unspliced (self.norm)
    def to_norm(self, p: int) -> int:
        k = bisect.bisect_right(self._cut_s, p)
        return p + (self._cum[k - 1] if k else 0)

    def to_spliced(self, n: int) -> int:
        k = bisect.bisect_right(self._cut_n, n)
        if not k:
            return n
        width = self._cum[k - 1] - (self._cum[k - 2] if k > 1 else 0)
        if n < self._cut_n[k - 1] + width:
            return self._cut_s[k - 1]
        return n - self._cum[k - 1]

    def line_col(self, p: int):
        n = self.to_norm(p)
        i = bisect.bisect_right(self._line_starts, n) - 1
        return i + 1, n - self._line_starts[i] + 1

    def line_text(self, line: int) -> str:
        s = self._line_starts[line - 1]
        e = self.norm.find('\n', s)
        return self.norm[s:] if e < 0 else self.norm[s:e]

    def _raw_end(self, q: int):
        """Spliced index just past the raw string whose opening quote is at
        spliced index q; None if the delimiter is malformed, -1 if it never
        closes."""
        qn = self.to_norm(q)
        d = _RAW_DELIM.match(self.norm, qn + 1)
        if d is None:
            return None
        close = ')' + d.group(1) + '"'
        e = self.norm.find(close, d.end())
        return -1 if e < 0 else self.to_spliced(e + len(close))

    def _lex(self) -> list:
        t, n, spans, pos = self.text, len(self.text), [], 0
        while True:
            m = _CODE.search(t, pos)
            if m is None:
                return spans
            kind, s = m.lastgroup, m.start()
            if kind == 'num':
                pos = m.end()
            elif kind == 'block':
                e = t.find('*/', m.end())
                if e < 0:
                    spans.append((s, n, 'unclear'))
                    return spans
                spans.append((s, e + 2, 'comment'))
                pos = e + 2
            elif kind == 'line':
                e = t.find('\n', m.end())
                e = n if e < 0 else e
                spans.append((s, e, 'comment'))
                pos = e
            elif kind == 'raw':
                end = self._raw_end(m.end() - 1)
                if end is None:
                    e = t.find('\n', m.end())
                    e = n if e < 0 else e
                    spans.append((s, e, 'unclear'))
                    pos = e
                elif end < 0:
                    spans.append((s, n, 'unclear'))
                    return spans
                else:
                    spans.append((s, end, 'string' if self.mode == 'c++' else 'unclear'))
                    pos = end
            else:
                q = t[s]
                e = _BODY[q].match(t, s + 1).end()
                if e < n and t[e] == q:
                    spans.append((s, e + 1, 'string' if q == '"' else 'char'))
                    pos = e + 1
                else:
                    spans.append((s, e, 'unclear'))        # runs into the newline
                    pos = e

    def span_at(self, p: int):
        i = bisect.bisect_right(self._span_starts, p) - 1
        if i >= 0 and p < self.spans[i][1]:
            return self.spans[i]
        return None

    def context(self, p: int) -> str:
        sp = self.span_at(p)
        return 'code' if sp is None else sp[2]

    def _literal(self, sp) -> str:
        return '<unclear>' if sp[2] == 'unclear' else self.text[sp[0]:sp[1]][:60]

    def _line_start(self, p: int) -> int:
        t = self.text
        while True:
            nl = t.rfind('\n', 0, p)
            if nl < 0:
                return 0
            sp = self.span_at(nl)
            if sp is None:
                return nl + 1
            p = sp[0]

    def in_directive(self, p: int) -> bool:
        """Is spliced index p on a preprocessor directive line?"""
        q, t = self._line_start(p), self.text
        while q < len(t):
            sp = self.span_at(q)
            if sp is not None:
                if sp[2] != 'comment':
                    return False
                q = sp[1]
            elif t[q] in ' \t\f\v':
                q += 1
            else:
                return t[q] == '#'
        return False

    def tokens_after(self, p: int, stop_at_eol: bool):
        t, n = self.text, len(self.text)
        while p < n:
            sp = self.span_at(p)
            if sp is not None:
                if sp[2] != 'comment':
                    yield self._literal(sp)
                p = sp[1]
                continue
            c = t[p]
            if c == '\n' and stop_at_eol:
                yield '<eod>'
                return
            if c.isspace():
                p += 1
                continue
            m = _TOKEN.match(t, p)
            if m:
                yield m.group(0)
                p = m.end()
            elif t[p:p + 2] in _PUNCT2:
                yield t[p:p + 2]
                p += 2
            else:
                yield c
                p += 1
        yield '<eof>'

    def token_before(self, p: int) -> str:
        t = self.text
        p -= 1
        while p >= 0:
            sp = self.span_at(p)
            if sp is not None:
                if sp[2] != 'comment':
                    return self._literal(sp)
                p = sp[0] - 1
                continue
            c = t[p]
            if c == '\n':
                if self.in_directive(p):
                    return '<eod>'          # the directive above ended here
                p -= 1
            elif c.isspace():
                p -= 1
            elif c.isalnum() or c in '_$':
                q = p
                while q > 0 and (t[q - 1].isalnum() or t[q - 1] in '_$'):
                    q -= 1
                return t[q:p + 1]
            elif p > 0 and t[p - 1:p + 1] in _PUNCT2:
                return t[p - 1:p + 1]
            else:
                return c
        return '<bof>'

    def shape(self, start: int, end: int) -> dict:
        """The tokens around one occurrence in code: the one before it, the one
        after it, the arguments between the matching parentheses when it is
        followed by '(' (None if they never close), and the token after them.
        A directive stops at its end of line."""
        in_dir = self.in_directive(start)
        toks = self.tokens_after(end, in_dir)
        nxt = next(toks, '<eof>')
        args = after = None
        if nxt == '(':
            depth, args = 0, []
            for tk in toks:
                if tk in ('<eod>', '<eof>') or len(args) > _MAX_ARG_TOKENS:
                    args = None
                    break
                if tk == ')' and depth == 0:
                    after = next(toks, '<eof>')
                    break
                depth += {'(': 1, ')': -1}.get(tk, 0)
                args.append(tk)
        return {'prev_token': self.token_before(start), 'next_token': nxt,
                'call_args': args[:32] if args is not None else None,
                'call_arg_tokens': len(args) if args is not None else None,
                'after_call': after, 'in_directive': in_dir}


_NO_SHAPE = {'prev_token': None, 'next_token': None, 'call_args': None,
             'call_arg_tokens': None, 'after_call': None, 'in_directive': None}


def match_lines(text: str, suffix: str = '.cpp') -> list:
    """One row per OCCURRENCE of any entry point, every one on every line.

    For a C-family suffix the whole file is lexed (class Lexed): the row's
    context is 'code', 'comment', 'string', 'char' or 'unclear', and a code
    occurrence carries the tokens around it for classify_call. Any other
    suffix (an assembler unit in the linkage) is searched as text, with the
    Mach-O leading underscore allowed, and its rows have context 'unlexed'."""
    mode = lexer_mode(suffix)
    if mode == 'text':
        norm = text.replace('\r\n', '\n')
        starts = [0] + [m.end() for m in re.finditer('\n', norm)]
        rows = []
        for m in _NAMES_RX_TEXT.finditer(norm):
            i = bisect.bisect_right(starts, m.start()) - 1
            e = norm.find('\n', starts[i])
            line = norm[starts[i]:] if e < 0 else norm[starts[i]:e]
            rows.append(dict(_NO_SHAPE, line=i + 1, column=m.start() - starts[i] + 1,
                             pattern=m.group(1), text=line.strip()[:240],
                             context='unlexed', lexer='text'))
        return rows
    spliced = _SPLICE.sub('', text.replace('\r\n', '\n'))
    if not any(k in spliced for k in _PREFILTER):
        return []
    lx = Lexed(text, mode)
    rows = []
    for m in _NAMES_RX.finditer(lx.text):
        line, col = lx.line_col(m.start())
        ctx = lx.context(m.start())
        row = dict(_NO_SHAPE, line=line, column=col, pattern=m.group(1),
                   text=lx.line_text(line).strip()[:240], context=ctx, lexer=mode)
        if ctx == 'code':
            row.update(lx.shape(m.start(), m.end()))
        rows.append(row)
    return rows


#: The tokens after which `name(...)` is read as a call statement or expression.
CALL_CONTEXT = frozenset((';', '{', '}', ')', ':', ',', '(', '=', '?', '&&', '||', '!',
                          'return', 'else', 'do', '<bof>', '<eod>'))


def classify_call(row: dict) -> str:
    """What one `ggml_backend_load_all*` occurrence does to the search set.

    Only shapes that are recognised get a name that does not block:
    `void name(...)` with the declared parameters, followed by ';' or '{'
    (a declaration or definition); `name()` for load_all and
    `name(nullptr)` for load_all_from_path after a statement or expression
    boundary (the default search). Any other argument to load_all_from_path
    is EXPLICIT. Everything else is UNCLASSIFIED, including a row without the
    lexer's tokens (review finding 2: v1's control built its row by hand, a
    row the matcher could never produce)."""
    ctx, pat = row.get('context'), row['pattern']
    # A NAME IN A LOG STRING IS NOT A CALL. `src/llama.cpp:407` prints
    # "use ggml_backend_load() or ggml_backend_load_all()"; the first draft
    # counted it as a default-search call.
    if ctx in ('string', 'comment'):
        return 'mention inside a %s, not a call' % ctx
    if ctx == 'char':
        return 'mention inside a character literal, not a call'
    if pat not in LOAD_ALL:
        return 'recorded'
    if ctx == 'unclear':
        return ('UNCLASSIFIED: unclear lexical state (an unterminated literal or '
                'comment, or a raw string where the dialect is not C++)')
    if ctx == 'unlexed':
        return 'UNCLASSIFIED: in a unit the C/C++ lexer does not read'
    if ctx != 'code' or row.get('next_token') is None:
        return 'UNCLASSIFIED: no lexer tokens for this row'
    prev, nxt = row['prev_token'], row['next_token']
    args, after = row['call_args'], row['after_call']
    if nxt != '(':
        return 'UNCLASSIFIED: named but not called here (followed by %r)' % nxt
    if args is None:
        return 'UNCLASSIFIED: the call parentheses do not close'
    # DEFINITIONS FIRST. `void ggml_backend_load_all() {` also has the call
    # shape; checked the other way round it was counted as a default call --
    # the first control run caught exactly that.
    if prev == 'void':
        if after in (';', '{') and (
                (pat == 'ggml_backend_load_all' and args in ([], ['void'])) or
                (pat == 'ggml_backend_load_all_from_path'
                 and args[:3] == ['const', 'char', '*'] and row['call_arg_tokens'] <= 4)):
            return 'declaration or definition, not a call'
        return 'UNCLASSIFIED: a declaration-like shape that is not recognised'
    if prev not in CALL_CONTEXT:
        return 'UNCLASSIFIED: a call preceded by %r' % prev
    if pat == 'ggml_backend_load_all':
        return ('default-search call, no directory argument' if args == []
                else 'UNCLASSIFIED: load_all called with an argument')
    if args == ['nullptr']:
        return 'the default search itself (load_all forwards nullptr)'
    return 'EXPLICIT-DIRECTORY CALL: changes the search set'


def _blocks(site: dict) -> bool:
    return (site['pattern'] in LOAD_ALL
            and site['classification'].startswith(('EXPLICIT', 'UNCLASSIFIED')))


def _where(site: dict) -> str:
    return '%s:%d:%d %s' % (site['path'], site['line'], site['column'],
                            site['classification'])


def _read_text_or_none(p: Path):
    try:
        return p.read_text()
    except (OSError, UnicodeDecodeError):
        return None


_INCLUDE_RX = re.compile(r'^[ \t]*#[ \t]*(?:include|include_next|import)[ \t]*[<"]([^">\n]+)[">]',
                         re.M)
_ASM_INCLUDE_RX = re.compile(r'^[ \t]*\.include\b', re.M)


def _included_tail(name: str) -> str:
    """An included path without its leading './' and '../' parts."""
    parts = [p for p in name.replace('\\', '/').split('/') if p not in ('', '.')]
    while parts and parts[0] == '..':
        parts.pop(0)
    return '/'.join(parts)


def main(receipt_rel: str = CALL_SITE_RECEIPT) -> int:
    receipt = REPO / receipt_rel
    if receipt.exists():
        print('refusing: the receipt exists; this is write-once', file=sys.stderr)
        return 2
    manifest = json.loads((REPO / MANIFEST).read_text())
    src = Path(manifest['source_and_patch']['source_tree'])
    src_real = os.path.realpath(src)
    build = src / 'build'
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    parsed = parse_ninja((build / 'build.ninja').read_text(),
                         read_include=lambda p: _read_text_or_none(build / p))
    statements = parsed['statements']
    unmapped = [{'problem': 'build rules: ' + p} for p in parsed['problems']]
    cc = json.loads((build / 'compile_commands.json').read_text())
    obj_to_src = {}
    for e in cc:
        o = e.get('output')
        if o:
            obj_to_src[os.path.normpath(os.path.join(e['directory'], o))] = \
                os.path.normpath(os.path.join(e['directory'], e['file']))

    targets = list(TARGETS)
    linked = {}                                    # real source -> {targets}
    unity_checked = {}
    for t in targets:
        if t not in statements:
            unmapped.append({'target': t, 'problem': 'no build statement'})
            continue
        for o in linked_objects(statements, t):
            if o.startswith('NINJA-PROBLEM:'):
                unmapped.append({'target': t, 'problem': o[len('NINJA-PROBLEM:'):]})
                continue
            if o.startswith('UNRESOLVED-ARCHIVE:'):
                unmapped.append({'target': t, 'archive': o.split(':', 1)[1],
                                 'problem': 'a linked archive has no build statement'})
                continue
            s = obj_to_src.get(os.path.normpath(str(build / o)))
            if s is None:
                unmapped.append({'target': t, 'object': o,
                                 'problem': 'no compile command for this object'})
                continue
            # REVIEW FINDING 0: the unit the linkage names is itself linked --
            # for a unity unit, as well as the sources it includes.
            reals = [s]
            if '/Unity/' in s and s.endswith(('.cxx', '.cpp', '.c')):
                utext = _read_text_or_none(Path(s))
                if utext is None:
                    unmapped.append({'target': t, 'unit': s,
                                     'problem': 'a linked unity unit cannot be read'})
                else:
                    incs = unity_includes(utext)
                    if unity_include_directives(utext) != len(incs) and s not in unity_checked:
                        unmapped.append({'target': t, 'unit': s, 'problem': (
                            'a unity unit has an #include this walk does not follow')})
                    unity_checked[s] = len(incs)
                    reals += [os.path.normpath(os.path.join(os.path.dirname(s), i))
                              for i in incs]
            for r in reals:
                linked.setdefault(os.path.realpath(r), set()).add(t)

    def rel_of(real):
        return (os.path.relpath(real, src_real)
                if real.startswith(src_real + os.sep) else real)

    # the files read: every C-family file of the tree (build/ included), and
    # every linked unit at the path the linkage names, whatever its suffix
    files = {}
    for p in sorted(src.rglob('*')):
        if p.is_file() and p.suffix.lower() in SOURCE_SUFFIXES:
            files.setdefault(os.path.realpath(p), str(p.relative_to(src)))
    for r in linked:
        files.setdefault(r, rel_of(r))

    sites, scanned_linked, scan_problems, lexed_as, included = [], {}, [], {}, set()
    for real in sorted(files):
        rel = files[real]
        try:
            data = Path(real).read_bytes()
        except OSError as exc:
            if real in linked:
                unmapped.append({'unit': rel, 'problem': (
                    'a linked translation unit cannot be read: %s' % exc)})
            else:
                scan_problems.append({'path': rel, 'problem': 'cannot be read: %s' % exc})
            continue
        suffix = Path(real).suffix
        mode = lexer_mode(suffix)
        lexed_as[mode] = lexed_as.get(mode, 0) + 1
        digest = hashlib.sha256(data).hexdigest()
        text = data.decode('utf-8', errors='replace')
        if real in linked:
            scanned_linked[real] = {'path': rel, 'sha256': digest, 'read_as': mode}
            if mode == 'text' and _ASM_INCLUDE_RX.search(text):
                unmapped.append({'unit': rel, 'problem': (
                    'a linked assembler unit has an .include this scan does not follow')})
        if mode != 'text':
            included.update(_included_tail(i) for i in _INCLUDE_RX.findall(text))
        kind = ('translation unit' if real in linked or suffix.lower() not in HEADER_SUFFIXES
                else 'header')
        for r in match_lines(text, suffix):
            sites.append(dict(r, path=rel, sha256=digest, kind=kind,
                              linked_into=sorted(linked.get(real, ())),
                              classification=classify_call(r)))
    # A source file that is not linked but is #included somewhere acts as a
    # header: it is treated as one (matched by the included path's tail,
    # which can only over-include).
    for s in sites:
        if s['kind'] == 'translation unit' and not s['linked_into'] and any(
                s['path'] == i or s['path'].endswith('/' + i) for i in included):
            s['kind'] = 'included source'

    linked_rows = [s for s in sites if s['linked_into']]
    # REVIEW FINDING 1: header rows block unless shown not included, and
    # nothing here shows that, so every header row can block.
    header_rows = [s for s in sites if s['kind'] in ('header', 'included source')]
    linked_calls = [s for s in linked_rows if s['pattern'] in LOAD_ALL
                    and not s['classification'].startswith(('mention', 'declaration'))]
    explicit_dir_linked = [s for s in linked_calls
                           if s['classification'].startswith('EXPLICIT')]
    unclassified_linked = [s for s in linked_calls
                           if s['classification'].startswith('UNCLASSIFIED')]
    header_blocking = [s for s in header_rows if _blocks(s)]
    unscanned = sorted(set(linked) - set(scanned_linked))
    blocked_by = (['linked: ' + _where(s) for s in explicit_dir_linked + unclassified_linked]
                  + ['header: ' + _where(s) for s in header_blocking]
                  + ['linkage problem: %s' % json.dumps(u, sort_keys=True) for u in unmapped]
                  + ['scan problem: %s' % json.dumps(u, sort_keys=True)
                     for u in scan_problems]
                  + ['linked unit not scanned: %s' % rel_of(u) for u in unscanned])
    if not linked_calls:
        blocked_by.append('no ggml_backend_load_all* call found in a linked unit')

    def by_class(rows):
        out = {}
        for s in rows:
            out[s['classification']] = out.get(s['classification'], 0) + 1
        return dict(sorted(out.items()))

    doc = {
        'schema': 'live_ab/loader_call_site_excerpts-v2',
        'convention': 'deterministic-path',
        'generated_utc': t0,
        'authority': ('root, reviews/build_snapshot_review_20260923_1630.md, '
                      'call-site paragraph; v2 fixes review findings deposit/0-5 '
                      'against the v1 receipt %s' % CALL_SITE_RECEIPT_V1),
        'supersedes': CALL_SITE_RECEIPT_V1,
        'nothing_executed_THIS_RECEIPT': ('text reads of an existing tree only; no '
                                          'build, configure, native tool, candidate '
                                          'execution or model load'),
        'source_tree': str(src),
        'source_head_declared': manifest['source_and_patch']['base_commit'],
        'build_rules': {n: {'path': str(build / n), 'sha256': sha256_file(build / n)}
                        for n in ('build.ninja', 'compile_commands.json')},
        'ninja_includes': [dict(i, sha256=(sha256_file(build / i['path'])
                                           if i['followed'] else None))
                           for i in parsed['includes']],
        'patterns': PATTERNS,
        'text_search_pattern': TEXT_PATTERN,
        'targets': targets,
        'linkage_problems': unmapped,
        'scan_problems': scan_problems,
        'linked_translation_units': {k: sorted(v) for k, v in sorted(linked.items())},
        'linked_units_scanned': dict(sorted(scanned_linked.items())),
        'sites': sites,
        'summary': {
            'files_read': sum(lexed_as.values()),
            'files_read_by_lexer': dict(sorted(lexed_as.items())),
            'sites_total': len(sites),
            'linked_translation_units': len(linked),
            'linked_translation_units_scanned': len(scanned_linked),
            'load_all_calls_linked_into_the_candidate': len(linked_calls),
            'by_classification_linked': by_class(linked_rows),
            'by_classification_headers': by_class(header_rows),
            'explicit_directory_calls_linked_into_the_candidate': len(explicit_dir_linked),
            'unclassified_calls_linked_into_the_candidate': len(unclassified_linked),
            'blocking_header_rows': len(header_blocking),
            'finding_blocked_by': blocked_by,
            'finding': (
                'every ggml_backend_load_all* occurrence in the code of the %d '
                'translation units linked into the launcher or its nine members '
                '(all %d read) is a declaration, a definition, or a call that uses '
                'the default search (no directory argument; load_all_from_path only '
                'with nullptr), and no scanned header or included source holds an '
                'explicit-directory or unclassified one' % (len(linked), len(scanned_linked))
                if not blocked_by else
                'NOT ESTABLISHED: see finding_blocked_by'),
        },
        'scope': (
            'A lexical, source-level scan. LINKAGE: the translation units linked into '
            'the launcher and its nine members, from the generated build rules '
            '(build.ninja with its includes followed, static archives followed '
            'through explicit inputs and LINK_LIBRARIES, file-scope $variables '
            'expanded) and compile_commands.json. Every linked unit is read at the '
            'path the linkage names, whatever its directory or suffix: generated '
            'units under build/ are included, and so are unity units together with '
            'the sources they include. READING: C, C++ and Objective-C units and '
            'headers are lexed as whole files (comments across lines, string, '
            'character and raw-string literals, digit separators, line splices). '
            'Every occurrence of every entry-point identifier is classified, whether '
            'or not it is followed by "(". A linked unit with any other suffix (the '
            'assembler units) is searched as text, and a load_all* name there is '
            'UNCLASSIFIED, and so is an assembler .include. HEADERS: no inclusion '
            'evidence (depfiles) is read, so no header is shown to be not included. '
            'An explicit-directory or unclassified load_all* occurrence in ANY '
            'scanned header (every file with a header suffix anywhere in the tree, '
            'build/ included) blocks the finding, and so does one in an unlinked '
            'source file whose path ends with a name some scanned file #includes '
            '(an "included source"). An unlinked source file that nothing #includes '
            'by such a name is taken as not compiled into the candidate. The '
            'owner-reported nm -u observation of which members import dlopen cannot '
            'see a header-inline call to ggml_backend_load_all_from_path (that would '
            'be an import of the loader symbol, not of dlopen), so it is not relied '
            'on here. NOT COVERED: a name built by token pasting or passed as a '
            'string to dlsym, identifiers spelled with universal-character-names or '
            'trigraphs, an include written through a macro, and included files '
            'whose suffix is outside the scanned set. Preprocessor conditionals are not '
            'evaluated: a disabled branch is scanned as if compiled, which can only '
            'add rows. Entry points other than ggml_backend_load_all* are recorded, '
            'not classified, and do not enter the finding. This is not a call-graph '
            'proof that any call runs.'),
    }
    receipt.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    print(receipt, json.dumps(doc['summary'])[:2000])
    return 0


# -- the build-rule deposit root asked for at 17:52 ---------------------------
def statement_block(text: str, output: str):
    """The verbatim `build` statement for `output`, with its bindings, exactly
    as the generated file has it (continuation lines included; a comment line
    between two bindings kept). None if no statement produces `output`."""
    st = parse_ninja(text)['statements'].get(output)
    return None if st is None else st['block']


def linkage_from_deposit(deposit: dict) -> dict:
    """Re-derive target -> linked real sources from the DEPOSIT ALONE.

    Pure: it reads only the deposited statements, file-scope bindings,
    object-to-source mappings and unity include lines, so a reviewer without
    the owner's tree can check that the call-site receipt's linkage follows
    from the deposited rules. A v2 deposit carries each statement's and
    binding's position in the originals, so $variables expand exactly as they
    did there; a v1 deposit has no bindings. A unity unit counts as linked
    together with the sources it includes."""
    order = deposit.get('statement_order') or {}
    items, problems = [], []
    for b in deposit.get('file_scope_bindings', []):
        items.append((b['seq'], b['text']))
    for i, (o, block) in enumerate(deposit['statements'].items()):
        if block is None:
            problems.append('the deposited statement for %s is empty' % o)
            continue
        if order and o not in order:
            problems.append('no deposited position for the statement of %s' % o)
        items.append((order.get(o, i), block))
    items.sort(key=lambda x: x[0])
    parsed = parse_ninja('\n\n'.join(t for _, t in items), source='deposit')
    problems += parsed['problems']
    problems += ['original build rules: %s' % p for p in deposit.get('ninja_parse_problems', [])]
    statements = parsed['statements']
    obj_to_src = {m['object']: os.path.normpath(os.path.join(m.get('directory') or '',
                                                             m['file']))
                  for m in deposit['object_to_source']}
    unity = {os.path.normpath(u['path']): u['includes'] for u in deposit['unity_units']}
    build = deposit['build_directory']
    linked = {}
    for t in deposit['targets']:
        if t not in statements:
            problems.append('no deposited statement for %s' % t)
            continue
        for o in linked_objects(statements, t):
            if o.startswith('NINJA-PROBLEM:'):
                problems.append('%s: %s' % (t, o[len('NINJA-PROBLEM:'):]))
                continue
            if o.startswith('UNRESOLVED-ARCHIVE:'):
                problems.append('%s links an undeposited archive %s' % (t, o[19:]))
                continue
            src = obj_to_src.get(o)
            if src is None:
                problems.append('%s links %s with no deposited mapping' % (t, o))
                continue
            reals = [src] + [os.path.normpath(os.path.join(os.path.dirname(src), i))
                             for i in unity.get(src, ())]
            for r in reals:
                linked.setdefault(r, set()).add(t)
    return {'linked': {k: sorted(v) for k, v in sorted(linked.items())},
            'problems': problems, 'build_directory': build}


def deposit_build_rules(out_rel: str = BUILD_RULES,
                        sites_rel: str = CALL_SITE_RECEIPT) -> int:
    sites_path = REPO / sites_rel
    out_path = REPO / out_rel
    if out_path.exists():
        print('refusing: the deposit exists; this is write-once', file=sys.stderr)
        return 2
    if not sites_path.exists():
        print('refusing: the call-site receipt %s does not exist yet' % sites_rel,
              file=sys.stderr)
        return 2
    manifest = json.loads((REPO / MANIFEST).read_text())
    src = Path(manifest['source_and_patch']['source_tree'])
    build = src / 'build'
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    parsed = parse_ninja((build / 'build.ninja').read_text(),
                         read_include=lambda p: _read_text_or_none(build / p))
    statements = parsed['statements']
    cc = json.loads((build / 'compile_commands.json').read_text())
    by_output = {}
    for e in cc:
        if e.get('output'):
            by_output[os.path.normpath(os.path.join(e['directory'], e['output']))] = e

    # every statement the ten targets reach: themselves and every archive
    wanted, queue = [], list(TARGETS)
    while queue:
        t = queue.pop(0)
        if t in wanted:
            continue
        wanted.append(t)
        st = statements.get(t) or {}
        ins = list(st.get('explicit', [])) + (
            st.get('variables', {}).get('LINK_LIBRARIES') or '').split()
        queue.extend(i for i in ins if i.endswith('.a') and i not in wanted)
    blocks = {t: statements[t]['block'] for t in wanted if t in statements}

    mappings, unity_units = [], []
    for t in TARGETS:
        for o in linked_objects(statements, t):
            if o.startswith(('UNRESOLVED-ARCHIVE:', 'NINJA-PROBLEM:')) or \
                    o in {m['object'] for m in mappings}:
                continue
            e = by_output.get(os.path.normpath(str(build / o)))
            if e is None:
                continue
            mappings.append({'object': o, 'file': e['file'], 'directory': e['directory'],
                             'output': e.get('output'),
                             'entry_sha256': hashlib.sha256(json.dumps(
                                 e, sort_keys=True).encode()).hexdigest()})
            f = os.path.normpath(os.path.join(e['directory'], e['file']))
            if '/Unity/' in f and f not in {u['path'] for u in unity_units}:
                up = Path(f)
                utext = up.read_text()
                unity_units.append({'path': f, 'sha256': sha256_file(up),
                                    'includes': unity_includes(utext),
                                    'include_directives': unity_include_directives(utext)})
    deposit = {
        'schema': 'live_ab/loader_linkage_build_rules-v2',
        'convention': 'post-build-provenance',
        'generated_utc': t0,
        'authority': ('root, reviews/dependency_callsite_disposition_20260923_1752.md: '
                      '"deposit the existing relevant generated link/archive statements '
                      'and object-to-source compile mappings (with their original-file '
                      'hashes)"; v2 fixes review finding deposit/5 against %s'
                      % BUILD_RULES_V1),
        'supersedes': BUILD_RULES_V1,
        'nothing_executed_THIS_RECEIPT': 'text reads of existing generated files only',
        'build_directory': str(build),
        'originals': {n: {'path': str(build / n), 'bytes': (build / n).stat().st_size,
                          'sha256': sha256_file(build / n)}
                      for n in ('build.ninja', 'compile_commands.json')},
        'ninja_includes': [dict(i, bytes=(build / i['path']).stat().st_size,
                                sha256=sha256_file(build / i['path']))
                           if i['followed'] else dict(i) for i in parsed['includes']],
        'ninja_parse_problems': parsed['problems'],
        'targets': TARGETS,
        'statements': blocks,
        'statement_order': {t: statements[t]['seq'] for t in blocks},
        'file_scope_bindings': parsed['binding_lines'],
        'object_to_source': mappings,
        'unity_units': unity_units,
        'how_to_check': ('linkage_from_deposit(this) in '
                         'experiments/live_ab_serving/loader_call_sites.py re-derives '
                         'target -> linked sources from these statements, file-scope '
                         'bindings (merged in their original order, so $variables '
                         'expand as they did in the originals), mappings and unity '
                         'includes ALONE; its result is compared below with the '
                         'call-site receipt. The whole-file digests above bind the '
                         'excerpts to the originals for anyone holding them. '
                         'Command line: loader_call_sites.py --rederive <this file>.'),
    }
    rederived = linkage_from_deposit(deposit)
    receipt = json.loads(sites_path.read_text())
    want = {os.path.realpath(k): v for k, v in receipt['linked_translation_units'].items()}
    got = {os.path.realpath(k): v for k, v in rederived['linked'].items()}
    deposit['rederivation'] = {
        'problems': rederived['problems'],
        'linked_translation_units': len(got),
        'call_site_receipt': {'path': sites_rel, 'sha256': sha256_file(sites_path)},
        'agrees_with_call_site_receipt': want == got,
        'differences': sorted(set(want) ^ set(got))[:20],
    }
    out_path.write_text(json.dumps(deposit, indent=1, sort_keys=True) + '\n')
    print(out_path, json.dumps(deposit['rederivation'])[:300])
    return 0


def rederive(path: str) -> dict:
    """Read-only: re-derive the linkage of any deposit, v1 or v2."""
    r = linkage_from_deposit(json.loads(Path(path).read_text()))
    return {'deposit': path, 'linked_translation_units': len(r['linked']),
            'problems': r['problems']}


if __name__ == '__main__':                                     # pragma: no cover
    if '--rederive' in sys.argv:
        print(json.dumps(rederive(sys.argv[sys.argv.index('--rederive') + 1]), indent=1))
        sys.exit(0)
    sys.exit(deposit_build_rules() if '--deposit-build-rules' in sys.argv else main())
