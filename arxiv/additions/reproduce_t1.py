"""Reproduce T1 manuscript counts from unchanged committed primary records; no simulation."""
import csv, gzip, hashlib, json
from pathlib import Path
from collections import defaultdict, Counter
root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
rows = defaultdict(Counter)
seen = set()
for item in manifest['primary_files']:
    path = root / item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
    with gzip.open(path, 'rt') as f:
        for r in csv.DictReader(f):
            key = (r['cell'], r['construction'], int(r['program']), int(r['trial']))
            assert key not in seen, key
            seen.add(key)
            c = rows[key[:2]]
            c['trials'] += 1
            c['hierarchy_miscoverage'] += int(r['ever_miscover_h'])
            c[r['decision']] += 1
            # C1-C6 fail the conjunction; all cells have nonnegative hierarchy mean.
            c['errors'] += int((r['decision'] == 'DEPLOY' and r['cell'] in ('C1','C2','C3','C4','C5','C6')) or r['decision'] == 'RETAIN_INCUMBENT')
for key, c in rows.items():
    expected = manifest['expected'][key[0]][key[1]]
    for field, value in expected.items():
        assert c[field] == value, (key, field, c[field], value)
assert len(seen) == 336000
print(json.dumps({'verified_primary_records': len(seen), 'shards': len(manifest['primary_files']), 'cells': 8, 'status': 'PASS'}, indent=2))
