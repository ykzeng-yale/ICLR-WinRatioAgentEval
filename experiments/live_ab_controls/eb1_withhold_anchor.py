"""The mock anchor process of the receipt-attribution controls: it WITHHOLDS chosen triggers.

``python eb1_withhold_anchor.py --withhold decision <lab_anchor.main argv>`` runs the unmodified
``lab_anchor.serve`` loop (``--mock-receipt``, no git, no network, as the dry runs'
``dryrun_live_ab._start_anchor``) with one change: a request whose ``trigger`` is listed is
read, its anchor file is written (as the real process does before it commits), and NO receipt
line is appended for it.  Its receipt lines are then written by the control itself, into the
same ``anchor_spool/receipts.jsonl``, "as the anchor process would write them"
(``receipt_fixture.append_line``): the wrong ones first, then the correct one.  Every other
trigger (start, periodic, pause, end) is receipted by the unmodified mock path.

Used only by ``tests_eb1_receipt_attribution``.  Outside the ``experiments/live_ab/tests_*.py``
glob on purpose (repair contract, placement).  Prepared and checked by AI agent sessions; not
human peer review or author sign-off (protocol 14.7).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_anchor                                                       # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--withhold':
        sys.stderr.write('eb1_withhold_anchor: --withhold TRIGGER[,TRIGGER] comes first\n')
        return 2
    withhold = frozenset(t for t in argv[1].split(',') if t)
    real_handle = lab_anchor._handle
    real_append = lab_anchor._append_receipt

    def handle(paths, cfg, req, *, mode, wait_s):
        if str(req.get('trigger')) in withhold:
            lab_anchor.write_anchor_file(paths, req)
            return None
        return real_handle(paths, cfg, req, mode=mode, wait_s=wait_s)

    def append(path, receipt):
        if receipt is not None:
            real_append(path, receipt)

    lab_anchor._handle = handle
    lab_anchor._append_receipt = append
    return lab_anchor.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
