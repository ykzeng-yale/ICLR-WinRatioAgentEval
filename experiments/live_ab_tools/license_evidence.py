"""Retrieve the two public licence texts at their PINNED revisions.

Root authorized this specifically and told me not to treat it as blocked
(`reviews/live_roster_root_decisions_20260921_1854.md`, and again in
`reviews/live_prefreeze_root_decisions_20260921_1929.md`):

    "License question: proceed. Fetching the two public license texts from the
     exact model repositories/revisions is authorized prefreeze evidence
     collection. Save source URL, revision, retrieval time, exact bytes/hash and
     any access failure. No weights or model execution is involved; do not treat
     this as capacity-blocked or seek another permission. A deposited license is
     evidence for author review, not root attestation of distribution rights."

WHAT IS AND IS NOT CLAIMED
--------------------------
`config.servers.*.license` already says ``apache-2.0``. That is a DECLARATION.
This retrieves the bytes the repository actually serves at the pinned revision
and hashes them, so the freeze can pin evidence rather than a claim. It is not a
rights attestation and it does not replace the author's distribution review --
root said both, twice, and neither is weakened here.

AN ACCESS FAILURE IS A RESULT. A repository that ships no ``LICENSE`` blob at the
pinned revision is a fact about that revision, not a reason to substitute the
text from some other revision, some other repository, or my own memory of what
Apache-2.0 says. Every attempt is recorded with its exact status, and a failure
is deposited as a failure.

NO WEIGHTS. Only the paths listed in ``CANDIDATE_PATHS`` are requested, each at
the pinned revision, each capped at ``MAX_BYTES``. No GGUF, no model, no server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]

#: Tried in order, at the PINNED revision only. A repository may carry the licence
#: as a blob, or declare it only in the model-card front matter; both are recorded
#: for what they are and never conflated.
CANDIDATE_PATHS: tuple[tuple[str, str], ...] = (
    ('LICENSE', 'licence_blob'),
    ('LICENSE.txt', 'licence_blob'),
    ('LICENSE.md', 'licence_blob'),
    ('README.md', 'model_card_declaration'),
)
MAX_BYTES = 1 << 20
TIMEOUT_S = 30.0


def _get(url: str) -> Dict[str, Any]:
    """One bounded GET. Every outcome -- including a failure -- is a recorded fact."""
    started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    req = urllib.request.Request(url, headers={'User-Agent': 'live-ab-licence-evidence/1'})
    out: Dict[str, Any] = {'url': url, 'requested_utc': started}
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read(MAX_BYTES + 1)
            out['http_status'] = resp.status
            out['final_url'] = resp.url
            out['content_type'] = resp.headers.get('Content-Type')
            if len(body) > MAX_BYTES:
                out['ok'] = False
                out['error'] = 'body exceeds MAX_BYTES=%d; not retained' % MAX_BYTES
                return out
            out['ok'] = True
            out['bytes'] = len(body)
            out['sha256'] = hashlib.sha256(body).hexdigest()
            out['_body'] = body
    except urllib.error.HTTPError as exc:                      # noqa: PERF203
        out['ok'] = False
        out['http_status'] = exc.code
        out['error'] = 'HTTPError %s' % exc.code
    except Exception as exc:                                   # noqa: BLE001
        out['ok'] = False
        out['error'] = '%s: %s' % (type(exc).__name__, exc)
    out['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    return out


def _front_matter_license(body: bytes) -> Optional[str]:
    """The ``license:`` field of a model card's YAML front matter, or None.

    Deliberately literal: it reads the declared string and does not interpret it.
    A card that declares nothing returns None, which is reported as None.
    """
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    for line in lines[1:]:
        if line.strip() == '---':
            break
        key, _, value = line.partition(':')
        if key.strip() == 'license':
            return value.strip().strip('"\'') or None
    return None


def collect(out_dir: Path, *, execute: bool) -> Dict[str, Any]:
    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    servers: Dict[str, Any] = {}
    for name in sorted(cfg['servers']):
        s = cfg['servers'][name]
        repo_id, rev = s['hf_repo'], s['hf_revision']
        entry: Dict[str, Any] = {
            'hf_repo': repo_id, 'hf_revision': rev,
            'declared_license_in_config': s.get('license'),
            'config_license_evidence_sha256_before': s.get('license_evidence_sha256'),
            'attempts': [], 'retained': None,
        }
        if not execute:
            entry['skipped'] = 'dry run: no request issued'
            servers[name] = entry
            continue
        for path, kind in CANDIDATE_PATHS:
            url = 'https://huggingface.co/%s/resolve/%s/%s' % (repo_id, rev, path)
            got = _get(url)
            body = got.pop('_body', None)
            got['path'] = path
            got['evidence_kind'] = kind
            entry['attempts'].append(got)
            if not got.get('ok'):
                continue
            dest = out_dir / ('%s__%s__%s' % (name, rev[:12], path.replace('/', '_')))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            got['saved_as'] = lab_common.display_path(dest)
            entry['retained'] = {
                'path': path, 'evidence_kind': kind, 'url': got['url'],
                'final_url': got.get('final_url'), 'bytes': got['bytes'],
                'sha256': got['sha256'], 'saved_as': got['saved_as'],
                'retrieved_utc': got['completed_utc'],
            }
            if kind == 'model_card_declaration':
                entry['retained']['front_matter_license'] = _front_matter_license(body)
                entry['retained']['caveat'] = (
                    'a model card DECLARING a licence is not the licence TEXT. This '
                    'repository served no licence blob at the pinned revision; the '
                    'declaration is retained as the declaration it is.')
            break
        if entry['retained'] is None:
            entry['access_failure'] = (
                'no candidate path returned a body at the pinned revision. Recorded '
                'as a failure; nothing is substituted from another revision, another '
                'repository, or from memory of the licence text.')
        servers[name] = entry

    retained = {k: v['retained'] for k, v in servers.items() if v.get('retained')}
    complete = len(retained) == len(servers)
    receipt: Dict[str, Any] = {
        'schema': 'live_ab/license_evidence-v2',
        'supersedes': {
            'path': 'results/live_ab/LICENSE_EVIDENCE.json',
            'why': ('v1 saved the bytes under a repo-root directory whose name '
                    'shaded root-owned `evidence/`. The directory was renamed to '
                    'experiments/live_ab_licenses/ and the retrieval repeated, so '
                    'the receipt names paths that exist. v1 is retained by the '
                    'write-once sink and its `saved_as` paths are stale.'),
            'cross_check': ('the two retrievals are independent: identical sha256 '
                            'across them is evidence the pinned revisions served '
                            'the same bytes twice, not a copied number.'),
        },
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root: "License question: proceed ... authorized prefreeze '
                      'evidence collection", reviews/live_roster_root_decisions_'
                      '20260921_1854.md; reaffirmed in reviews/live_prefreeze_root_'
                      'decisions_20260921_1929.md'),
        'servers': servers,
        'all_servers_have_evidence': complete,
        # The freeze key is a digest over the retained evidence for EVERY server,
        # so a partial retrieval must not produce one. It stays None and the hole
        # stays a hole.
        'license_evidence_sha256': (
            lab_common.sha256_canonical({k: {kk: retained[k][kk]
                                             for kk in ('url', 'bytes', 'sha256',
                                                        'evidence_kind')}
                                         for k in sorted(retained)})
            if complete else None),
        'promoted_into_config': False,
        'why_not_promoted': (
            'config.servers.*.license_evidence_sha256 is a freeze pin bound to the '
            'three-way verbatim contract (config.json == ARCHITECTURE_FINAL 6.1 == '
            'protocol_FINAL Appendix B). Root authorized RETRIEVING and DEPOSITING '
            'the evidence; it did not rule on the pin. The value is reported here '
            'and the config is left as it stands.'),
        'weights_downloaded': False,
        'models_executed': False,
        'is_a_rights_attestation': False,
        'what_this_does_not_establish': [
            'distribution rights: root said twice that a deposited licence is '
            'evidence for the author review, not an attestation',
            'that the pinned GGUF weight file itself carries this licence; this is '
            'the repository licence at the pinned revision',
        ],
    }
    return receipt


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true',
                    help='issue the requests; without it nothing is fetched')
    ap.add_argument('--out', type=Path,
                    default=Path(lab_common.RESULTS_ROOT) / 'LICENSE_EVIDENCE.json')
    a = ap.parse_args(argv)
    # NOT `evidence/` and nothing that shades it: that directory is root-owned.
    # The licence bytes live in this session's own experiments tree.
    store = REPO / 'experiments' / 'live_ab_licenses'
    receipt = collect(store, execute=a.execute)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, receipt)
    for name, entry in receipt['servers'].items():
        r = entry.get('retained')
        print('%-6s %-55s %s' % (
            name, '%s@%s' % (entry['hf_repo'], entry['hf_revision'][:10]),
            ('%s %s %dB %s' % (r['path'], r['evidence_kind'], r['bytes'],
                               r['sha256'][:16])) if r
            else entry.get('access_failure', entry.get('skipped', '?'))))
    print('license_evidence_sha256:', receipt['license_evidence_sha256'])
    print('written:', a.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
