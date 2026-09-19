"""Anonymized RELEASE COPIES of local-stream provenance files (Round 9 provenance repair).

Originals (raw evidence and frozen documents) are never edited. Each listed file is copied to
results/local_stream/release_anon/<same relative path> with identifying absolute paths replaced:

    <REPO>  repository root                 <HOME>  the user's home directory (any /Users/<name>)
    <TMP>   per-user / per-session temp dirs (/private/var/folders/<..>/T, /var/folders/<..>/T, /private/tmp/<session>)
    <USER>  any residual occurrence of the account name        <HOST>  the machine's network name, if present

The identifying strings are derived at run time (Path.home(), repo root, platform.node()) so that this script itself
contains none of them. MAPPING.json records, per file, the sha256 of the ORIGINAL and of the anonymized copy and the
number of replacements per placeholder; MAPPING.md is the human-readable note. No model call, no git command.

Usage: .venv/bin/python experiments/local_stream/make_release_anon.py
"""
from __future__ import annotations
import hashlib, json, platform, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results/local_stream/release_anon'
FILES = [
    'results/local_stream/run_manifest.json', 'results/local_stream/episodes.jsonl', 'results/local_stream/design.json',
    'results/local_stream/monitor_state.json', 'results/local_stream/dryrun/run_manifest.json', 'results/local_stream/dryrun/episodes.jsonl',
    'results/local_stream/timing_pilot/summary.json', 'results/local_stream/timing_pilot/episodes.jsonl',
    'results/local_stream/v1_pre_round9/report.md', 'results/local_stream/v1_pre_round9/summary.json',
    'work/local_stream/data/data_manifest.json',
    'experiments/local_stream/config.json', 'experiments/local_stream/README.md', 'experiments/local_stream/protocol.md',
]


def rules():
    home = str(Path.home()); user = Path.home().name; host = platform.node()
    r = [(re.compile(re.escape(str(REPO))), '<REPO>'),
         (re.compile(r'(?:/private)?/var/folders/[A-Za-z0-9_]{2}/[A-Za-z0-9_]+/T'), '<TMP>'),
         (re.compile(r'/private/tmp/claude-[^"\\\s)]*'), '<TMP>'),
         (re.compile(re.escape(home)), '<HOME>'),
         (re.compile(r'/Users/[A-Za-z0-9_.-]+'), '<HOME>')]
    if host:
        r.append((re.compile(re.escape(host)), '<HOST>'))
        if host.split('.')[0] != host:
            r.append((re.compile(re.escape(host.split('.')[0])), '<HOST>'))
    r.append((re.compile(re.escape(user)), '<USER>'))
    r.append((re.compile(re.escape(user[:8]) + r'\w*'), '<USER>'))     # truncated occurrences (process listings)
    return r, user


def main():
    rs, user = rules(); mapping = []
    for rel in FILES:
        src = REPO / rel
        if not src.exists():
            mapping.append(dict(file=rel, status='missing')); continue
        raw = src.read_bytes(); text = raw.decode('utf-8'); counts = {}
        for rx, rep in rs:
            text, k = rx.subn(rep, text)
            if k:
                counts[rep] = counts.get(rep, 0) + k
        assert user not in text and '/Users/' not in text, rel
        dst = OUT / rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(text, encoding='utf-8')
        mapping.append(dict(file=rel, anonymized_copy='results/local_stream/release_anon/' + rel, original_sha256=hashlib.sha256(raw).hexdigest(), original_bytes=len(raw),
                            anonymized_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), replacements=counts, changed=bool(counts)))
    (OUT / 'MAPPING.json').write_text(json.dumps(dict(
        placeholders={'<REPO>': 'repository root', '<HOME>': "user's home directory", '<TMP>': 'per-user or per-session temporary directory',
                      '<USER>': 'account name (residual or truncated occurrences)', '<HOST>': 'machine network name'},
        note='Originals are unmodified; original_sha256 lets a holder of the originals verify the correspondence. Only path/name strings were replaced; no number, hash, timestamp or outcome was touched.',
        files=mapping), indent=2) + '\n')
    L = ['# Anonymized release copies (Round 9)', '',
         'Made by `experiments/local_stream/make_release_anon.py`. The originals (raw evidence, frozen documents) are **not** edited and remain the provenance record; these copies are for an anonymous submission package. '
         'Only identifying path/name strings were replaced: `<REPO>` = repository root, `<HOME>` = home directory, `<TMP>` = per-user/per-session temp directory, `<USER>` = account name, `<HOST>` = machine name. '
         'Hardware/OS/package descriptions, hashes, timestamps and all outcomes are unchanged. Files with 0 replacements are byte-identical copies included for completeness.', '',
         '| original | sha256 of original | replacements |', '|---|---|---|']
    for m in mapping:
        if m.get('status') == 'missing':
            L.append('| `%s` | missing | |' % m['file'])
        else:
            L.append('| `%s` | `%s` | %s |' % (m['file'], m['original_sha256'], ', '.join('%s x%d' % kv for kv in m['replacements'].items()) or 'none'))
    L += ['', 'Code files that also contain an absolute path or account-specific string and must be sanitized (or regenerated) when an anonymous code package is built: see `MAPPING.json -> code_files_to_check`.', '']
    code = []
    for p in sorted((REPO / 'experiments/local_stream').glob('*')):
        if p.is_file() and p.suffix in ('.py', '.md', '.json') and p.name != Path(__file__).name:
            t = p.read_text(errors='replace'); k = len(re.findall(re.escape(user) + r'|/Users/', t))
            if k:
                code.append(dict(file=str(p.relative_to(REPO)), occurrences=k))
    mj = json.loads((OUT / 'MAPPING.json').read_text()); mj['code_files_to_check'] = code
    (OUT / 'MAPPING.json').write_text(json.dumps(mj, indent=2) + '\n')
    (OUT / 'MAPPING.md').write_text('\n'.join(L))
    # final guard over the whole output tree
    for p in OUT.rglob('*'):
        if p.is_file():
            t = p.read_text(errors='replace'); assert user not in t and '/Users/' not in t, p
    print('wrote %d anonymized copies to %s; code files to check: %s' % (sum(1 for m in mapping if 'original_sha256' in m), OUT, [c['file'] for c in code]))


if __name__ == '__main__':
    main()
