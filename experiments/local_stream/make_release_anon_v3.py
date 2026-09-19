"""Round 10 anonymized RELEASE COPIES (supersedes the file list / destinations of make_release_anon.py, which is unchanged).

Differences from Round 9 (audit finding 5):
  * the sanitized copy of the git-ignored local data manifest (work/local_stream/data/data_manifest.json) is written to
    the NON-IGNORED path results/local_stream/release_anon/local_data_manifest.anon.json (the Round 9 destination lay under
    a directory named work/, which the repository's ignore rule `work/` excludes, so it was never committed);
    original_sha256 is kept so that a holder of the original can verify the correspondence;
  * a missing original is recorded as unavailable instead of being promised;
  * every file of the output tree is re-scanned for '/Users/', the account name, host names and e-mail patterns, and
    the scan result is stored in MAPPING.json;
  * MAPPING states that regeneration is LOCATION-DEPENDENT: the strings to replace are derived at run time from the
    executing account, repository location and host, and temp paths differ between machines; no byte-for-byte
    portability of the anonymized copies is claimed.
Originals are never edited. No model call, no git command.

Usage: .venv/bin/python experiments/local_stream/make_release_anon_v3.py
"""
from __future__ import annotations
import hashlib, json, platform, re, socket, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_release_anon as base  # noqa: E402  (rules() and the Round 9 file list)

REPO = base.REPO; OUT = base.OUT
DEST = {'work/local_stream/data/data_manifest.json': 'results/local_stream/release_anon/local_data_manifest.anon.json'}
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')


def identifiers():
    user = Path.home().name; hosts = {platform.node(), socket.gethostname(), platform.node().split('.')[0]} - {''}
    return user, sorted(hosts)


def scan_tree(root: Path):
    user, hosts = identifiers(); hits = []; emails = {}
    n = 0
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        n += 1; t = p.read_text(errors='replace'); rel = str(p.relative_to(REPO))
        for label, found in (('/Users/', '/Users/' in t), ('account name', user in t), ('account name (case-insensitive)', user.lower() in t.lower()),
                             ('host name', any(h in t for h in hosts)), ('/home/', bool(re.search(r'/home/[A-Za-z0-9_.-]+', t)))):
            if found:
                hits.append(dict(file=rel, indicator=label))
        for m in EMAIL.findall(t):
            emails.setdefault(m, set()).add(rel)
    return n, hits, {k: sorted(v) for k, v in emails.items()}


def main():
    rs, user = base.rules(); mapping = []
    for rel in base.FILES:
        src = REPO / rel; dst_rel = DEST.get(rel, 'results/local_stream/release_anon/' + rel)
        if not src.exists():
            prev = REPO / dst_rel
            mapping.append(dict(file=rel, status='original unavailable in this checkout (git-ignored or not committed); no new copy made',
                                existing_anonymized_copy=dst_rel if prev.exists() else None,
                                existing_anonymized_sha256=hashlib.sha256(prev.read_bytes()).hexdigest() if prev.exists() else None)); continue
        raw = src.read_bytes(); text = raw.decode('utf-8'); counts = {}
        for rx, repl in rs:
            text, k = rx.subn(repl, text)
            if k:
                counts[repl] = counts.get(repl, 0) + k
        assert user not in text and '/Users/' not in text, rel
        dst = REPO / dst_rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(text, encoding='utf-8')
        mapping.append(dict(file=rel, anonymized_copy=dst_rel, original_sha256=hashlib.sha256(raw).hexdigest(), original_bytes=len(raw),
                            anonymized_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), replacements=counts, changed=bool(counts),
                            **({'note': 'original is git-ignored (work/); Round 10: copy moved to a non-ignored path'} if rel in DEST else {})))
    code = []
    for p in sorted((REPO / 'experiments/local_stream').glob('*')):
        if p.is_file() and p.suffix in ('.py', '.md', '.json') and p.name not in ('make_release_anon.py', 'make_release_anon_v3.py'):   # these two contain only the literal search pattern
            k = len(re.findall(re.escape(user) + r'|/Users/', p.read_text(errors='replace')))
            if k:
                code.append(dict(file=str(p.relative_to(REPO)), occurrences=k))
    portability = ('Regeneration of the anonymized copies is LOCATION-DEPENDENT: the strings that are replaced are derived at run time from the executing account, repository location and host, '
                   'and a different checkout may lack git-ignored originals. No byte-for-byte portability of the anonymized copies is claimed; original_sha256 ties each committed copy to its original.')
    mj = dict(placeholders={'<REPO>': 'repository root', '<HOME>': "user's home directory", '<TMP>': 'per-user or per-session temporary directory',
                            '<USER>': 'account name (residual or truncated occurrences)', '<HOST>': 'machine network name'},
              note='Originals are unmodified; original_sha256 lets a holder of the originals verify the correspondence. Only path/name strings were replaced; no number, hash, timestamp or outcome was touched.',
              portability=portability, round='Round 10 (make_release_anon_v3.py)', files=mapping, code_files_to_check=code)
    (OUT / 'MAPPING.json').write_text(json.dumps(mj, indent=2) + '\n')
    L = ['# Anonymized release copies (Round 10)', '',
         'Made by `experiments/local_stream/make_release_anon_v3.py` (Round 9: `make_release_anon.py`). The originals (raw evidence, frozen documents) are **not** edited and remain the provenance record; these copies are an explicit allowlist for an anonymous submission package, not approval to publish the whole research branch anonymously. '
         'Only identifying path/name strings were replaced: `<REPO>` = repository root, `<HOME>` = home directory, `<TMP>` = per-user/per-session temp directory, `<USER>` = account name, `<HOST>` = machine name. '
         'Hardware/OS/package descriptions, hashes, timestamps and all outcomes are unchanged. Files with 0 replacements are byte-identical copies included for completeness.', '',
         '**Portability.** ' + portability, '',
         '| original | anonymized copy | sha256 of original | replacements |', '|---|---|---|---|']
    for m in mapping:
        if 'original_sha256' not in m:
            L.append('| `%s` | %s | original unavailable in this checkout | |' % (m['file'], '`%s` (existing copy kept)' % m['existing_anonymized_copy'] if m.get('existing_anonymized_copy') else 'none'))
        else:
            L.append('| `%s` | `%s` | `%s` | %s |' % (m['file'], m['anonymized_copy'], m['original_sha256'], ', '.join('%s x%d' % kv for kv in m['replacements'].items()) or 'none'))
    L += ['', 'Round 10 note: `work/local_stream/data/data_manifest.json` is git-ignored. Its sanitized copy is now `results/local_stream/release_anon/local_data_manifest.anon.json`; the Round 9 mapping pointed to a copy under `release_anon/work/...`, which the ignore rule `work/` excluded from the repository. '
          'The committed `results/local_stream/data_manifest.json` (pinned source URLs and hashes) is the primary data-provenance file.', '',
          'Code files that also contain an absolute path or account-specific string and must be sanitized (or regenerated) when an anonymous code package is built: see `MAPPING.json -> code_files_to_check`.', '']
    (OUT / 'MAPPING.md').write_text('\n'.join(L))
    n, hits, emails = scan_tree(OUT)
    # the stale Round 9 copy under the ignored work/ directory is not part of the release; it is scanned too (it is inside OUT)
    mj['identifier_scan'] = dict(files_scanned=n, indicators=['/Users/', 'account name', 'account name (case-insensitive)', 'host name(s) of this machine', '/home/<name>', 'e-mail pattern'],
                                 hits=hits, email_like_strings={k: v for k, v in emails.items()},
                                 result='clean' if not hits and not emails else ('no path/account/host indicator; e-mail-like strings listed for manual review' if not hits else 'INDICATORS FOUND'))
    (OUT / 'MAPPING.json').write_text(json.dumps(mj, indent=2) + '\n')
    assert not hits, hits
    print('wrote %d anonymized copies; scanned %d files; hits: %d; e-mail-like strings: %s; code files to check: %s' % (
        sum(1 for m in mapping if 'original_sha256' in m), n, len(hits), sorted(emails), [c['file'] for c in code]))


if __name__ == '__main__':
    main()
