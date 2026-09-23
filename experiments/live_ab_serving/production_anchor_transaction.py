"""ONE synthetic anchor through the PRODUCTION path — the missing integration check.

Root's anchor-drill review, 2026-09-22 03:19, on what my 20-post drill did NOT do:

    "anchor_drill.py imports lab_anchor only for its SCANNER. It builds custom
     mock segments and calls its OWN session.post; it does not call production
     serve, _handle, commit_and_push, or post_comment. No dedicated drill-branch
     push, anchor spool consumption, private production receipt, or chained
     receipt return is exercised. THE v2 ASSERTION THAT THE PRODUCTION ANCHOR
     PATH WORKS END TO END EXCEEDS THE DELIVERED EVIDENCE."

That assertion was mine and it was wrong: I calibrated GitHub POST timing with a
bespoke script and then described the production path as working. This runs the
production path itself, once.

WHAT IS EXERCISED, and nothing else:

  * ``lab_anchor.serve(once=True)`` consuming an anchor spool request
  * ``_handle`` -> ``write_anchor_file`` -> ``scan_for_identifiers``
  * ``commit_and_push`` onto a DRILL branch, pushed to the real remote
  * ``post_comment`` to the dedicated drill issue (#13), the location root
    authorized for drill postings
  * ``_write_private`` -- the identified receipt under work/ only
  * the receipt returned and appended to the spool's receipts.jsonl

SYNTHETIC. The anchor file carries the real freeze-receipt FIELD SHAPES over a
hash-chained segment of synthetic events. No trial, no roster, no episode, no
scientific datum. One transaction; the caps are one request and one comment.
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

DRILL_ISSUE = 13
DRILL_BRANCH = 'session60/anchor-production-drill'


def _token() -> str:
    p = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True, cwd=str(REPO), timeout=120)
    for line in (p.stdout or '').splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return ''


def assert_public_anchor_path(anchors_dir, checkout) -> dict:
    """The public anchor path must be inside the checkout and NOT ignored.

    Root: "Check the public path is inside the checkout, unignored and the only
    scanned/staged payload." Checked with `git check-ignore`, not by reading
    .gitignore myself -- git's own answer is the one that decides whether
    `git add` will refuse, and reimplementing its matching is how I would get a
    different answer from the tool that actually runs.
    """
    d = Path(anchors_dir)
    inside = str(d.resolve()).startswith(str(Path(checkout).resolve()) + '/')
    probe = d / 'anchor_1.json'
    r = subprocess.run(['git', '-C', str(checkout), 'check-ignore', '-v', str(probe)],
                       capture_output=True, text=True, timeout=60)
    ignored = (r.returncode == 0)
    out = {'anchors_dir': str(d), 'inside_checkout': inside,
           'git_check_ignore_says_ignored': ignored,
           'git_check_ignore_output': (r.stdout or '').strip() or None,
           'decided_by': 'git check-ignore, not a local .gitignore reimplementation'}
    if not inside:
        raise SystemExit('REFUSE: public anchor path %s is outside the checkout' % d)
    if ignored:
        raise SystemExit('REFUSE: public anchor path %s is ignored (%s); git add '
                         'would refuse it' % (d, out['git_check_ignore_output']))
    return out


def mocked_success_returns_a_receipt(paths, cfg) -> dict:
    """A stubbed HTTP 201 must complete `post_comment` and return a receipt.

    RENAMED. It was `mocked_success_reaches_persistence`, which claimed more than
    it does. Root: "The existing helper named `mocked_success_reaches_persistence`
    itself only checks `post_comment`, despite its broader name/docstring; that
    helper alone does not establish private/spool persistence." Correct -- it
    drives one function and reads its return value. Persistence was exercised by
    the completed transaction and by root's own intercepted run, not by this.


    Root: "Verify the successful response reaches the actual spool/private
    receipt path in an offline stub before any real posting. Because a real POST
    could succeed before this exception, any uncertain past or future posting
    must be reconciled against issue 13 before retrying."

    The success path was unreachable: `post_comment` raised
    `NameError: sha256_bytes` at line 239 on a 201. A repair that only makes the
    name resolve is not evidence that the receipt then lands where it must, so
    this drives the real function with a stubbed response and reads the files
    afterwards.
    """
    from unittest import mock                                  # noqa: PLC0415

    class _Resp:
        status_code = 201
        content = (b'{"id": 999999, "created_at": "2026-01-01T00:00:00Z",'
                   b' "updated_at": "2026-01-01T00:00:00Z"}')

        def json(self):
            return json.loads(self.content)

    posted = {}

    def _fake_post(url, **kw):
        posted['url'] = url
        return _Resp()

    # PATCH `requests.post` ITSELF. `post_comment` does `import requests` INSIDE
    # the function, so rebinding an attribute on lab_anchor does nothing -- my
    # first attempt did exactly that, the stub never applied, and the real
    # requests.post was called with a stub token. Patching the module attribute
    # makes a real request impossible rather than merely unlikely.
    os.environ['LIVE_AB_ANCHOR_TOKEN'] = 'stub-token-not-a-credential'
    err = None
    try:
        with mock.patch('requests.post', _fake_post):
            res = lab_anchor.post_comment(lab_anchor.DEFAULT_ISSUE_API_BASE, 13,
                                          '{"drill": "offline-stub"}',
                                          'LIVE_AB_ANCHOR_TOKEN')
    except NameError as exc:                                   # the old failure
        res, err = {}, '%s: %s' % (type(exc).__name__, exc)
    finally:
        os.environ.pop('LIVE_AB_ANCHOR_TOKEN', None)
    return {
        'composed_url': posted.get('url'),
        'url_is_repository_scoped': '/repos/' in str(posted.get('url')),
        'ok': res.get('ok'),
        'comment_id': res.get('comment_id'),
        'receipt_sha256_present': bool(res.get('receipt_sha256')),
        # DERIVED, not asserted. An earlier version of this receipt carried
        # "no_NameError": True as a literal, which is the defect the audit
        # detectors exist to catch -- a field naming a check it never performed.
        'name_error': err,
        'no_name_error': err is None,
        'success_branch_completed': bool(res.get('ok')) and err is None,
        'what_this_shows': ('the 201 branch completes and returns a receipt '
                            'digest; it previously raised NameError at line 239 '
                            'before returning anything'),
        'no_real_request_was_made': posted.get('url') is not None,
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    execute = '--execute' in argv
    run_id = 'panchor_' + uuid.uuid4().hex[:10]

    # THE TRANSACTION RUNS IN A SEPARATE CLONE, not the live working tree.
    # commit_and_push does a real `git add`, commit, branch switch and push. Doing
    # that in the tree I am working in would put repository state at risk for an
    # integration check -- and a check that can damage what it is checking is not
    # worth its evidence. The clone pushes to the SAME remote on a drill branch,
    # so branch/push/receipt provenance is real; only the working tree is spared.
    repo_for_git = REPO
    if execute:
        clone = Path(lab_common.WORK_ROOT) / '_production_anchor_clone' / run_id
        clone.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--quiet', '--shared', str(REPO), str(clone)],
                       check=True, timeout=300)
        # DEFECT 1, root: "clones the local REPO with --shared. Its default
        # `origin` is therefore the local source repository, while
        # `lab_anchor.commit_and_push` runs `git push origin <branch>`. The
        # script never repoints that origin. The current claim that the clone
        # 'pushes to the SAME remote' is unsupported by its implementation."
        #
        # That claim was mine and it was wrong. Set the real remote explicitly
        # and VERIFY it, rather than assuming a clone inherits it.
        upstream = subprocess.run(['git', '-C', str(REPO), 'remote', 'get-url', 'origin'],
                                  capture_output=True, text=True, check=True,
                                  timeout=60).stdout.strip()
        if 'github.com' not in upstream:
            raise SystemExit('REFUSE: source origin %r is not the GitHub remote' % upstream)
        subprocess.run(['git', '-C', str(clone), 'remote', 'set-url', 'origin', upstream],
                       check=True, timeout=60)
        verified = subprocess.run(['git', '-C', str(clone), 'remote', 'get-url', 'origin'],
                                  capture_output=True, text=True, check=True,
                                  timeout=60).stdout.strip()
        if verified != upstream:
            raise SystemExit('REFUSE: clone origin is %r, expected %r'
                             % (verified, upstream))
        subprocess.run(['git', '-C', str(clone), 'checkout', '--quiet', '-b',
                        DRILL_BRANCH], check=True, timeout=120)
        for k, v in (('user.name', 'Yukang Zeng'),
                     ('user.email', 'ykzeng2019@gmail.com')):
            subprocess.run(['git', '-C', str(clone), 'config', k, v],
                           check=True, timeout=60)
        repo_for_git = clone
    work = Path(repo_for_git) / 'work' / '_production_anchor' / run_id
    paths = lab_common.TrialPaths(
        trial='T_PRODUCTION_ANCHOR_DRILL',
        results=work / 'results', events=work / 'events',
        # PUBLIC DRILL PATH, root: "<drill clone>/results/live_ab/anchor_drills/
        # <run_id>/anchors/anchor_1.json". The old `work/anchors` is matched by
        # .gitignore:26 `work/`, so `git add` refused the anchor file -- the
        # tree_state refusal of 2026-09-22. Segments, private receipts, spool
        # and logs STAY under ignored work/.
        anchors=(Path(repo_for_git) / 'results' / 'live_ab' / 'anchor_drills'
                 / run_id / 'anchors'),
        work=work, jobs=work / 'jobs', spools=work / 'spools',
        records=work / 'records', requests=work / 'requests',
        anchor_spool=work / 'anchor_spool',
        anchors_private=work / 'anchors_private', logs=work / 'logs',
        run_lock=work / 'run.lock', sandbox_lock=work / 'sandbox.lock')
    for d in (paths.results, paths.events, paths.anchors, paths.anchor_spool,
              paths.anchors_private, paths.logs):
        Path(d).mkdir(parents=True, exist_ok=True)

    # --- a hash-chained SYNTHETIC segment, real field shapes ----------------
    h = lab_common.sha256_text('production-anchor-drill-genesis')
    lines = []
    for seq in range(1, 5):
        body = {'seq': seq, 'kind': 'drill_synthetic_event', 'prev_h': h,
                'payload': 'SYNTHETIC-PRODUCTION-ANCHOR-DRILL-NOT-TRIAL-DATA'}
        h = lab_common.sha256_text(lab_common.canonical_json(body) + h)
        lines.append(lab_common.canonical_json(dict(body, h=h)))
    blob = ('\n'.join(lines) + '\n').encode('utf-8')
    seg = Path(paths.events) / 'seg_0000.jsonl'
    seg.write_bytes(blob)

    request = {
        'request_id': run_id, 'trial': 'T_PRODUCTION_ANCHOR_DRILL',
        'anchor_seq': 1, 'upto_seq': 4, 'upto_h': h,
        'segment_index': 0, 'segment_bytes': len(blob),
        'segment_sha256': lab_common.sha256_bytes(blob),
        'trigger': 'decision',          # in comment_triggers, so a comment is posted
        'blocking': False, 'publish_segments': False,
    }
    req_file = Path(paths.anchor_spool) / 'requests.jsonl'
    req_file.write_text(lab_common.canonical_json(request) + '\n', encoding='utf-8')

    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    cfg = dict(cfg)
    cfg['anchor'] = dict(cfg.get('anchor') or {})
    cfg['anchor']['issue'] = DRILL_ISSUE          # the authorized drill location
    cfg['anchor']['branch'] = DRILL_BRANCH
    cfg['_runtime'] = {
        'anchor_mode': 'real' if execute else 'mock',
        'repo': str(repo_for_git),
        # DEFECT 2: the bare base composed https://api.github.com/issues/13/comments,
        # which addresses no repository. lab_anchor now also refuses such a base.
        'api': lab_anchor.DEFAULT_ISSUE_API_BASE,
        'token_env': 'LIVE_AB_ANCHOR_TOKEN',
        'expect_branch': DRILL_BRANCH,
        'anchor_max_idle_s': 0.0,
    }

    receipt = {
        'schema': 'live_ab/production_anchor_receipt-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'run_id': run_id,
        'git_repo_used': 'a separate clone on the drill branch; the live working '
                         'tree is untouched' if execute else 'n/a (mock)',
        'corrects': ('my v2 drill receipt asserted the production anchor path '
                     'works end to end. It did not exercise serve, _handle, '
                     'commit_and_push or post_comment at all.'),
        'exercises': ['lab_anchor.serve(once=True)', '_handle', 'write_anchor_file',
                      'scan_for_identifiers', 'commit_and_push', 'post_comment',
                      '_write_private', 'receipts.jsonl append'],
        'mode': cfg['_runtime']['anchor_mode'],
        'drill_issue': DRILL_ISSUE, 'drill_branch': DRILL_BRANCH,
        'request': request,
        'synthetic': True,
        'is_a_trial': False,
    }

    if execute:
        os.environ['LIVE_AB_ANCHOR_TOKEN'] = _token()
    t0 = time.monotonic()
    handled = lab_anchor.serve(paths, cfg, once=True)
    receipt['elapsed_s'] = round(time.monotonic() - t0, 3)
    receipt['requests_handled'] = handled
    os.environ.pop('LIVE_AB_ANCHOR_TOKEN', None)

    rec_path = Path(paths.anchor_spool) / 'receipts.jsonl'
    receipt['spooled_receipts'] = [json.loads(l) for l in
                                   rec_path.read_text('utf-8').splitlines() if l.strip()] \
        if rec_path.exists() else []
    priv = Path(paths.anchors_private) / 'receipts.jsonl'
    receipt['private_receipts'] = [json.loads(l) for l in
                                   priv.read_text('utf-8').splitlines() if l.strip()] \
        if priv.exists() else []
    anchor_file = Path(paths.anchors) / 'anchor_1.json'
    receipt['anchor_file_written'] = anchor_file.exists()
    if anchor_file.exists():
        receipt['anchor_file'] = json.loads(anchor_file.read_text('utf-8'))
        receipt['anchor_file_sha256'] = lab_common.sha256_file(anchor_file)

    r0 = (receipt['spooled_receipts'] or [{}])[0]
    receipt['transaction_ok'] = bool(r0.get('ok'))
    receipt['committed'] = r0.get('commit')
    receipt['pushed'] = r0.get('pushed')
    receipt['comment_id'] = r0.get('comment_id')
    receipt['created_at'] = r0.get('created_at')
    receipt['error_class'] = r0.get('error_class')
    receipt['what_this_does_not_establish'] = [
        'any trial, roster, episode or scientific result',
        'that a REAL chain would anchor identically -- the segment is synthetic',
        'timing: the 20-post drill measured that separately and is not repeated',
    ]
    out = Path(lab_common.RESULTS_ROOT) / ('PRODUCTION_ANCHOR_%s.json' % run_id)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({k: receipt[k] for k in
                      ('mode', 'requests_handled', 'transaction_ok', 'committed',
                       'pushed', 'comment_id', 'error_class',
                       'anchor_file_written')}, indent=1))
    print('written:', out)
    return 0 if receipt['transaction_ok'] or not execute else 1


if __name__ == '__main__':
    raise SystemExit(main())
