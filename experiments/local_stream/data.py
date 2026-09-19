"""Download, cache and canonicalise the MBPP-sanitized and HumanEval task sets.

Raw files are cached under work/local_stream/data (git-ignored via work/).
A manifest records URL, byte size and sha256 for each download, plus the
sha256 of the canonical task list JSON (stable ordering: MBPP by numeric
task_id, then HumanEval by numeric index). Hidden tests live in the task
records but are never placed in any model prompt (see agent.py).
"""
from __future__ import annotations
import argparse, gzip, io, json, re, sys
from pathlib import Path

import requests

from common import DATA_DIR, canonical_json, iso, load_config, now_ts, sha256_bytes, sha256_text

MANIFEST = DATA_DIR / 'data_manifest.json'
TASKS_PATH = DATA_DIR / 'tasks.json'
_ASSERT_NAME = re.compile(r'assert\s+(?:[A-Za-z_][\w.]*\()*\s*([A-Za-z_]\w*)\s*\(')
_DEF_NAME = re.compile(r'^def\s+([A-Za-z_]\w*)\s*\(', re.M)


def _download(url: str, dest: Path, timeout=120) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        data = dest.read_bytes()
        return dict(url=url, path=str(dest), bytes=len(data), sha256=sha256_bytes(data), cached=True)
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.content
    dest.write_bytes(data)
    return dict(url=url, path=str(dest), bytes=len(data), sha256=sha256_bytes(data), cached=False, downloaded_at=iso(now_ts()))


def mbpp_entry_point(rec) -> str:
    """Function name the hidden asserts call; falls back to the last def in the reference."""
    for t in rec.get('test_list', []):
        m = _ASSERT_NAME.search(t)
        if m:
            name = m.group(1)
            if re.search(r'def\s+%s\s*\(' % re.escape(name), rec['code']):
                return name
    defs = _DEF_NAME.findall(rec['code'])
    return defs[-1] if defs else ''


def build_tasks(mbpp_raw: list, humaneval_raw: list) -> list:
    tasks = []
    for rec in sorted(mbpp_raw, key=lambda r: int(r['task_id'])):
        tasks.append(dict(
            uid='mbpp/%d' % int(rec['task_id']), benchmark='mbpp', source_task_id=int(rec['task_id']),
            prompt=rec['prompt'].strip(), entry_point=mbpp_entry_point(rec),
            signature_example=rec['test_list'][0] if rec['test_list'] else '',
            reference=rec['code'], test_imports=list(rec.get('test_imports') or []),
            test_list=list(rec['test_list']), challenge_test_list=list(rec.get('challenge_test_list') or [])))
    for rec in sorted(humaneval_raw, key=lambda r: int(r['task_id'].split('/')[-1])):
        idx = int(rec['task_id'].split('/')[-1])
        tasks.append(dict(
            uid='humaneval/%d' % idx, benchmark='humaneval', source_task_id=rec['task_id'],
            prompt=rec['prompt'], entry_point=rec['entry_point'], signature_example='',
            reference=rec['prompt'] + rec['canonical_solution'], test=rec['test']))
    return tasks


def prepare(cfg=None, force=False) -> dict:
    cfg = cfg or load_config()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    m_info = _download(cfg['mbpp_url'], DATA_DIR / 'sanitized-mbpp.json')
    h_info = _download(cfg['humaneval_url'], DATA_DIR / 'HumanEval.jsonl.gz')
    mbpp_raw = json.loads((DATA_DIR / 'sanitized-mbpp.json').read_text())
    with gzip.open(DATA_DIR / 'HumanEval.jsonl.gz', 'rt') as f:
        humaneval_raw = [json.loads(l) for l in f if l.strip()]
    if len(mbpp_raw) != 427 or len(humaneval_raw) != 164:
        raise RuntimeError('unexpected task counts: mbpp=%d humaneval=%d' % (len(mbpp_raw), len(humaneval_raw)))
    tasks = build_tasks(mbpp_raw, humaneval_raw)
    uids = [t['uid'] for t in tasks]
    assert len(set(uids)) == len(uids)
    text = canonical_json(tasks)
    if TASKS_PATH.exists() and not force and TASKS_PATH.read_text() != text:
        raise RuntimeError('tasks.json differs from a fresh build; refusing to overwrite without --force')
    TASKS_PATH.write_text(text)
    manifest = dict(
        created_at=iso(now_ts()), downloads=dict(mbpp_sanitized=m_info, humaneval=h_info),
        n_tasks=len(tasks), n_mbpp=len(mbpp_raw), n_humaneval=len(humaneval_raw),
        task_list_sha256=sha256_text(text), task_list_path=str(TASKS_PATH),
        ordering='mbpp by numeric task_id ascending, then humaneval by numeric index ascending',
        strata=dict(mbpp=len(mbpp_raw), humaneval=len(humaneval_raw)),
        licenses=dict(mbpp='CC-BY-4.0 (HF dataset card google-research-datasets/mbpp); repository google-research/google-research is Apache-2.0',
                      humaneval='MIT (openai/human-eval LICENSE)'),
        mbpp_entry_point_missing=[t['uid'] for t in tasks if t['benchmark'] == 'mbpp' and not t['entry_point']])
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


def load_tasks() -> list:
    if not TASKS_PATH.exists():
        raise FileNotFoundError('run data.py first to build %s' % TASKS_PATH)
    return json.loads(TASKS_PATH.read_text())


def task_list_sha256() -> str:
    return sha256_text(TASKS_PATH.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)
    m = prepare(force=args.force)
    print(json.dumps({k: m[k] for k in ('n_tasks', 'n_mbpp', 'n_humaneval', 'task_list_sha256')}, indent=2))
    for k, v in m['downloads'].items():
        print(k, v['bytes'], 'bytes sha256', v['sha256'])


if __name__ == '__main__':
    main()
