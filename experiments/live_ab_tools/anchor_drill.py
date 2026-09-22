"""The anchor drill of protocol 12.4 item 10.

    "One anchor drill before the freeze against the real remote on a drill branch
     and the real issue thread, with a mock chain carrying the real freeze-receipt
     fields (a throwaway repository could not reveal identifier leaks, because its
     URLs lack the real account and repository names)."

AUTHORITY.  Root, 2026-09-22 02:49 (``reviews/live_load_root_decision_20260922_0237.md``
line 31): *"Proceed with option (b): one clearly labelled dedicated drill issue in
this same repository, linked from issue 11, with the already planned finite 20
postings. Record this location-only prefreeze amendment before the first post;
retain all attempts, timestamps, failures and usage. No PR."*

The amendment is recorded in ``results/live_ab/PREFREEZE_AMENDMENT_ANCHOR_LOCATION.json``
and committed **before** this tool may post.  It refuses to start otherwise.

WHAT IS MEASURED, AND UNDER WHICH NAME
--------------------------------------
Root, same decision, line 33: *"Retain raw client send/ack times and server
created_at separately. Record local monotonic round trips alongside wall-clock
differences; label a server-minus-client timestamp difference as latency plus
offset, not pure latency. A constant offset cancels in differences; drift,
timestamp quantization and varying delivery delay need separate treatment. A 20
probe empirical p95 is calibration evidence, not a guaranteed future worst-case
bound."*

So three quantities are kept apart and never merged:

* ``rtt_monotonic_s`` -- send to ack on ONE clock, the local monotonic one.  This
  is a true duration and the only one of the three that is.
* ``server_minus_client_s`` -- ``created_at`` minus the client's send wall time.
  **This is latency PLUS clock offset**, quantised to whole seconds because
  ``created_at`` has one-second resolution.  It is never called latency.
* ``consecutive_difference_s`` -- ``L_{k+1} - L_k``.  A constant offset cancels
  here, which is the quantity the sandwich audit of 12.6 item 4 actually forms.

``config.json``'s frozen ``anchor.posting_latency_p95_s`` is **not written** by
this tool.  Root: *"Do not silently replace the frozen tolerance."*

RETENTION.  Every attempt is appended to a durable JSONL sink BEFORE anything
fallible touches it, failures included, and the analysis is computed from the
sink re-read off disk -- not from memory.  A drill that lost its failures would
be measuring only the postings that went well.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402
import lab_anchor                                              # noqa: E402

OWNER_REPO = 'ykzeng-yale/ICLR-WinRatioAgentEval'
API = 'https://api.github.com/repos/' + OWNER_REPO
COORDINATION_ISSUE = 11
POSTINGS = 20
AMENDMENT = 'results/live_ab/PREFREEZE_AMENDMENT_ANCHOR_LOCATION.json'

DRILL_TITLE = ('ANCHOR DRILL (protocol 12.4 item 10) — bounded, synthetic, '
               'NOT scientific coordination')


def _token() -> str:
    p = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True, cwd=str(REPO))
    for line in (p.stdout or '').splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return os.environ.get('GITHUB_TOKEN', '')


def _amendment_is_committed() -> dict:
    """The location-only amendment must be RECORDED AND COMMITTED before posting."""
    path = REPO / AMENDMENT
    if not path.exists():
        return {'ok': False, 'reason': 'the amendment record %s does not exist; root '
                                       'required it be recorded before the first post'
                                       % AMENDMENT}
    p = subprocess.run(['git', 'log', '-1', '--format=%H', '--', AMENDMENT],
                       capture_output=True, text=True, cwd=str(REPO))
    head = (p.stdout or '').strip()
    if not head:
        return {'ok': False, 'reason': 'the amendment record exists but is NOT '
                                       'COMMITTED; an uncommitted amendment is a '
                                       'local file, not a record'}
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', AMENDMENT],
                           capture_output=True, text=True, cwd=str(REPO))
    if (dirty.stdout or '').strip():
        return {'ok': False, 'reason': 'the amendment record has uncommitted changes'}
    return {'ok': True, 'commit': head,
            'sha256': lab_common.sha256_file(path)}


# ---------------------------------------------------------------------------
# the mock chain: real freeze-receipt FIELDS, synthetic content
# ---------------------------------------------------------------------------
def build_mock_chain(n_segments: int) -> list[dict]:
    """A hash-chained synthetic segment series.

    The digests are real digests of real (synthetic) bytes, so the anchor bodies
    carry the same FIELD SHAPES a trial would post. Nothing here is trial data and
    every record says so.
    """
    chain: list[dict] = []
    h = lab_common.sha256_text('anchor-drill-genesis')
    seq = 0
    for i in range(n_segments):
        lines = []
        for k in range(4):
            seq += 1
            body = {'seq': seq, 'kind': 'drill_synthetic_event', 'prev_h': h,
                    'payload': 'SYNTHETIC-DRILL-EVENT-NOT-TRIAL-DATA'}
            h = lab_common.sha256_text(lab_common.canonical_json(body) + h)
            lines.append(lab_common.canonical_json(dict(body, h=h)))
        blob = ('\n'.join(lines) + '\n').encode('utf-8')
        chain.append({
            'segment_index': i,
            'segment_bytes': len(blob),
            'segment_sha256': lab_common.sha256_bytes(blob),
            'upto_seq': seq,
            'upto_h': h,
        })
    return chain


def anchor_body(anchor_seq: int, seg: dict, drill_id: str) -> str:
    """The comment body: the anchor file's own fields, and nothing else of substance."""
    payload = {
        'schema': 'live_ab/anchor_drill_posting-v1',
        'drill_id': drill_id,
        'anchor_seq': anchor_seq,
        'upto_seq': seg['upto_seq'],
        'upto_h': seg['upto_h'],
        'segment_index': seg['segment_index'],
        'segment_bytes': seg['segment_bytes'],
        'segment_sha256': seg['segment_sha256'],
        'trigger': 'drill',
        'blocking': False,
    }
    return ('**ANCHOR DRILL POSTING %d of %d — SYNTHETIC. Not a trial anchor, not '
            'scientific coordination.** Protocol 12.4 item 10; mock chain carrying '
            'the real freeze-receipt field shapes.\n\n```json\n%s\n```\n'
            % (anchor_seq, POSTINGS, lab_common.canonical_json(payload)))


# ---------------------------------------------------------------------------
# the durable sink
# ---------------------------------------------------------------------------
class Sink:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.n = 0

    def append(self, rec: dict) -> None:
        line = (lab_common.canonical_json(rec) + '\n').encode('utf-8')
        with open(self.path, 'ab') as fh:
            written = 0
            while written < len(line):
                written += fh.write(line[written:])
            fh.flush()
            os.fsync(fh.fileno())
        self.n += 1

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for i, raw in enumerate(self.path.read_text('utf-8').splitlines()):
            if not raw.strip():
                continue
            try:
                out.append(json.loads(raw))
            except ValueError:
                raise SystemExit('drill sink line %d is malformed; refusing to '
                                 'analyse a truncated record set' % (i + 1))
        return out


# ---------------------------------------------------------------------------
# posting
# ---------------------------------------------------------------------------
def post(session, token: str, issue: int, body: str) -> dict:
    """One posting. Client send/ack on BOTH clocks, kept separate from server time."""
    url = '%s/issues/%d/comments' % (API, int(issue))
    t_send_wall, t_send_mono = time.time(), time.monotonic()
    rec: dict = {
        'schema': 'live_ab/anchor_drill_attempt-v1',
        't_send_wall': t_send_wall,
        't_send_monotonic': t_send_mono,
    }
    try:
        res = session.post(url, json={'body': body}, timeout=60, headers={
            'Authorization': 'Bearer %s' % token,
            'Accept': 'application/vnd.github+json'})
    except Exception as exc:                                   # noqa: BLE001
        t_ack_mono = time.monotonic()
        rec.update(ok=False, error_class='transport',
                   error='%s: %s' % (type(exc).__name__, exc),
                   t_ack_wall=time.time(), t_ack_monotonic=t_ack_mono,
                   rtt_monotonic_s=t_ack_mono - t_send_mono)
        return rec
    t_ack_wall, t_ack_mono = time.time(), time.monotonic()
    rec.update(t_ack_wall=t_ack_wall, t_ack_monotonic=t_ack_mono,
               rtt_monotonic_s=t_ack_mono - t_send_mono,
               status=res.status_code,
               server_date_header=res.headers.get('Date'))
    if res.status_code >= 300:
        rec.update(ok=False, error_class='api',
                   error='HTTP %s' % res.status_code)
        return rec
    try:
        data = res.json()
    except ValueError:
        rec.update(ok=False, error_class='decode', error='response is not JSON')
        return rec
    rec.update(ok=True, error_class=None,
               comment_id=data.get('id'),
               created_at=data.get('created_at'),
               updated_at=data.get('updated_at'),
               receipt_sha256=lab_common.sha256_bytes(res.content))
    return rec


def analyse_only(drill_id: str, issue: int | None) -> int:
    """Rebuild a receipt from an existing attempt sink. POSTS NOTHING.

    Used after the deposit defect above: the evidence is on disk, so re-running
    the postings to obtain a receipt would have been the wrong repair -- it would
    have doubled a finite, authorized 20-posting drill to obtain a file.
    """
    sink = Sink(Path(lab_common.RESULTS_ROOT) / ('ANCHOR_DRILL_ATTEMPTS_%s.jsonl'
                                                 % drill_id))
    if not sink.path.exists():
        print('no sink for %s' % drill_id, file=sys.stderr)
        return 2
    receipt = {
        'schema': 'live_ab/anchor_drill_receipt-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'protocol': '12.4 item 10',
        'authority': 'root 2026-09-22 02:49, reviews/live_load_root_decision_'
                     '20260922_0237.md line 31 (option b, dedicated drill issue)',
        'amendment_record': {'path': AMENDMENT, **_amendment_is_committed()},
        'drill_id': drill_id,
        'postings_planned': POSTINGS,
        'executed': True,
        'rebuilt_from_sink': True,
        'why_rebuilt': 'the executed run deposited its postings durably but raised '
                       'WriteOnceViolation on the receipt path, which the dry run '
                       'had already occupied. The postings are the evidence and they '
                       'survived; the drill was NOT repeated to obtain a file.',
        'identifier_scan': {'hits': 0,
                            'note': 'run before posting; recorded in the dry-run '
                                    'receipt for the same bodies'},
    }
    if issue is not None:
        receipt['drill_issue'] = {
            'number': issue,
            'url': 'https://github.com/%s/issues/%d' % (OWNER_REPO, issue)}
    receipt['attempts_sink'] = lab_common.tokenize_path(sink.path)
    _deposit(receipt, sink)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--analyse-only' in argv:
        i = argv.index('--analyse-only')
        drill_id = argv[i + 1]
        issue = None
        if '--issue' in argv:
            issue = int(argv[argv.index('--issue') + 1])
        return analyse_only(drill_id, issue)
    execute = '--execute' in argv
    n = POSTINGS

    amend = _amendment_is_committed()
    if not amend['ok']:
        print('REFUSING: ' + amend['reason'], file=sys.stderr)
        return 2

    drill_id = 'drill_' + uuid.uuid4().hex[:12]
    chain = build_mock_chain(n)
    bodies = [anchor_body(i + 1, chain[i], drill_id) for i in range(n)]

    # Identifier hygiene BEFORE anything is posted. This is the stated reason the
    # drill must use the real repository at all (12.4 item 10).
    scratch = Path(lab_common.WORK_ROOT) / '_anchor_drill' / drill_id
    scratch.mkdir(parents=True, exist_ok=True)
    body_files = []
    for i, b in enumerate(bodies):
        f = scratch / ('body_%02d.md' % (i + 1))
        f.write_text(b, encoding='utf-8')
        body_files.append(f)
    hits = lab_anchor.scan_for_identifiers(body_files, lab_anchor.DEFAULT_PATTERNS)

    receipt: dict = {
        'schema': 'live_ab/anchor_drill_receipt-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'protocol': '12.4 item 10',
        'authority': 'root 2026-09-22 02:49, reviews/live_load_root_decision_'
                     '20260922_0237.md line 31 (option b, dedicated drill issue)',
        'amendment_record': {'path': AMENDMENT, **amend},
        'drill_id': drill_id,
        'postings_planned': n,
        'identifier_scan': {'hits': len(hits), 'detail': hits[:10],
                            'note': 'the scanner never reports matched text; a hit '
                                    'withholds the file'},
        'executed': execute,
    }
    if hits:
        receipt['error'] = ('the identifier scanner flagged %d posting bodies; '
                            'nothing was posted' % len(hits))
        _deposit(receipt, None)
        print('REFUSING: identifier scanner hits', file=sys.stderr)
        return 3
    if not execute:
        receipt['note'] = ('DRY RUN. Bodies built and scanned; no issue created and '
                           'no comment posted. Re-run with --execute to post.')
        _deposit(receipt, None)
        print(json.dumps({'dry_run': True, 'bodies': n, 'scanner_hits': len(hits)},
                         indent=2))
        return 0

    import requests
    token = _token()
    if not token:
        print('REFUSING: no token', file=sys.stderr)
        return 2
    session = requests.Session()
    headers = {'Authorization': 'Bearer %s' % token,
               'Accept': 'application/vnd.github+json'}

    issue_body = (
        '**This issue is an ANCHOR DRILL, not scientific coordination.**\n\n'
        'Protocol 12.4 item 10 requires one anchor drill before the freeze, against '
        'the real remote and a real issue thread, with a **mock chain carrying the '
        'real freeze-receipt fields** — a throwaway repository cannot reveal '
        'identifier leaks, because its URLs lack the real account and repository '
        'names.\n\n'
        'Root authorized a **dedicated, clearly labelled drill issue in this '
        'repository, linked from #%d**, with a finite **%d postings** '
        '(`reviews/live_load_root_decision_20260922_0237.md`, 2026-09-22 02:49). The '
        'location-only prefreeze amendment is recorded at `%s` and was committed '
        'before the first post.\n\n'
        'Every comment below is **synthetic**. None of it is trial data, none of it '
        'is a scientific result, and no live episode has been run. Drill id `%s`.\n'
        % (COORDINATION_ISSUE, n, AMENDMENT, drill_id))
    res = session.post(API + '/issues', headers=headers, timeout=60,
                       json={'title': DRILL_TITLE, 'body': issue_body})
    if res.status_code >= 300:
        receipt['error'] = 'could not create the drill issue: HTTP %s' % res.status_code
        _deposit(receipt, None)
        print('REFUSING: issue creation failed', file=sys.stderr)
        return 4
    issue = int(res.json()['id' if 'number' not in res.json() else 'number'])
    receipt['drill_issue'] = {'number': issue, 'url': res.json().get('html_url')}

    sink = Sink(Path(lab_common.RESULTS_ROOT) / ('ANCHOR_DRILL_ATTEMPTS_%s.jsonl'
                                                 % drill_id))
    for i, body in enumerate(bodies):
        rec = post(session, token, issue, body)
        rec['posting_index'] = i + 1
        sink.append(rec)                    # RAW, durable, failures included
        time.sleep(1.0)                     # be a polite client; also spreads the sample

    receipt['attempts_sink'] = lab_common.tokenize_path(sink.path)
    _deposit(receipt, sink)
    return 0


def _deposit(receipt: dict, sink) -> None:
    """Deposit under a name UNIQUE TO THIS DRILL.

    DEFECT FOUND BY RUNNING IT, 2026-09-22 03:09: the first version wrote every
    receipt to one write-once path, so the DRY RUN occupied it and the executed
    drill's deposit raised WriteOnceViolation after all 20 postings had already
    been made. The postings themselves survived -- the durable sink is appended
    before anything fallible, which is exactly the case it was built for -- but
    the receipt had to be rebuilt from the sink afterwards.

    A dry run may no longer occupy an executed run's path, and neither may
    collide with another drill's.
    """
    if sink is not None:
        rows = sink.load()                  # re-read FROM DISK, not from memory
        receipt['analysis'] = analyse(rows)
        receipt['attempts_recorded'] = len(rows)
    stem = ('ANCHOR_DRILL_RECEIPT_%s' if receipt.get('executed')
            else 'ANCHOR_DRILL_DRYRUN_%s') % receipt.get('drill_id', 'unknown')
    out = Path(lab_common.RESULTS_ROOT) / (stem + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print('written:', out)


def analyse(rows: list) -> dict:
    """Three quantities, kept apart. See the module docstring."""
    import statistics

    def q(vals, p):
        # NEAREST-RANK. The previous round(p*(n-1)) index returns the sample
        # MAXIMUM for every n <= 11 at p=0.95 and reports it as a p95.
        import math as _m
        if not vals:
            return None
        v = sorted(vals)
        k = max(1, min(len(v), int(_m.ceil(p * len(v)))))
        return v[k - 1]

    ok = [r for r in rows if r.get('ok')]
    failed = [r for r in rows if not r.get('ok')]
    rtt = [r['rtt_monotonic_s'] for r in rows if r.get('rtt_monotonic_s') is not None]

    # PARSE DEFECT, found by reading the first receipt instead of trusting it:
    # created_at is ISO 8601 ("2026-09-22T03:09:07Z") and the first version parsed
    # it with email.utils.parsedate_to_datetime, which reads RFC 2822. Every parse
    # raised, the bare `except: continue` swallowed all twenty, and the receipt
    # reported n=0 with None percentiles -- a silent zero wearing the shape of a
    # result. Parse failures are now COUNTED and an empty series is an ERROR, not
    # a quiet absence.
    import datetime as _dt
    L, parse_failures = [], []
    for r in ok:
        ca = r.get('created_at')
        if not ca:
            parse_failures.append({'posting_index': r.get('posting_index'),
                                   'reason': 'no created_at'})
            continue
        try:
            server = _dt.datetime.fromisoformat(
                ca.replace('Z', '+00:00')).timestamp()
        except ValueError as exc:
            parse_failures.append({'posting_index': r.get('posting_index'),
                                   'reason': 'unparsable created_at: %s' % exc})
            continue
        L.append(server - float(r['t_send_wall']))
    dL = [abs(b - a) for a, b in zip(L, L[1:])]

    return {
        'attempts': len(rows),
        'ok': len(ok),
        'failed': len(failed),
        'failure_classes': sorted({r.get('error_class') for r in failed if r.get('error_class')}),
        'rtt_monotonic_s': {
            'n': len(rtt), 'min': min(rtt) if rtt else None,
            'median': statistics.median(rtt) if rtt else None,
            'p95': q(rtt, 0.95), 'max': max(rtt) if rtt else None,
            'meaning': 'send to ack on ONE clock (local monotonic). A true duration.',
        },
        'created_at_parse_failures': parse_failures,
        'server_minus_client_error': (
            None if L else 'NO usable created_at values: %d parse failure(s). An '
                           'empty series is an error here, not an absence -- the '
                           'first version of this analysis reported n=0 with None '
                           'percentiles because every parse raised into a bare '
                           'except.' % len(parse_failures)),
        'server_minus_client_s': {
            'n': len(L), 'min': min(L) if L else None,
            'median': statistics.median(L) if L else None,
            'p95': q(L, 0.95), 'max': max(L) if L else None,
            'meaning': 'created_at minus the client send wall time. This is LATENCY '
                       'PLUS CLOCK OFFSET, not latency. created_at has ONE SECOND '
                       'resolution, so these values are quantised to whole seconds.',
        },
        'consecutive_difference_s': {
            'n': len(dL), 'median': statistics.median(dL) if dL else None,
            'p95': q(dL, 0.95), 'max': max(dL) if dL else None,
            'meaning': '|L_{k+1} - L_k|. A CONSTANT offset cancels here, which is the '
                       'quantity the sandwich audit of 12.6 item 4 actually forms. '
                       'Drift, quantisation and varying delivery delay do NOT cancel.',
        },
        'not_written_to_config': 'anchor.posting_latency_p95_s is left frozen. Root: '
                                'do not silently replace the frozen tolerance.',
        'status_of_this_number': 'CALIBRATION EVIDENCE from a 20-posting empirical '
                                 'sample. NOT a guaranteed future worst-case bound.',
    }


if __name__ == '__main__':
    raise SystemExit(main())
