"""EB1c worker entry: the real ``lab_worker.main`` with the host-wide lock pin relocated.

Repair contract EB1, step EB1c.  The controls of ``tests_eb1_entry.py`` run the production
``lab_orchestrator.main`` as a subprocess, and it spawns one worker process per episode with
``_runtime.worker_cmd + ['--job', <job file>]`` (lab_orchestrator.py ``World.spawn``).  This is
that ``worker_cmd``::

    <python> eb1c_worker_entry.py --harness-config <temporary freeze config.json> --job <job>

It does ONE thing before handing over to the unmodified ``lab_worker.main``: it replaces the
cached module configuration ``lab_common._HARNESS_CONFIG`` with the control's temporary frozen
configuration, whose only relevant difference is ``sandbox.host_work_root`` -- a directory of
the control, not the owner-host pin ``/Users/.../ICLR-WinRatioAgentEvals/work/live_ab``.  So the
worker's canonical-lock checks (``assert_job_host_root_agreement``,
``assert_canonical_lock_spelling``, ``assert_canonical_execution_lock``) all RUN, against the
relocated pin, and the ``flock`` of protocol 5.7 item 1 is taken on the control's own inode.
Nothing else is changed: the job, the client, the receipt comparison, the sandbox, the spool
and the record are the production code paths.

Why relocate rather than use the real pin: the repair contract forbids any lane to touch the
main checkout, and a worker holding the real pin would create and ``flock`` its lock file.
``lab_worker.main``'s own docstring says isolation "lives in the test process, which patches the
canonical root; the production reader validates unconditionally" -- this is that patch, one
process removed.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--harness-config':
        sys.stderr.write('eb1c_worker_entry: --harness-config PATH comes first\n')
        return 2
    cfg = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    import lab_common
    lab_common._HARNESS_CONFIG = {k: v for k, v in cfg.items() if not str(k).startswith('_')}
    import lab_worker
    return lab_worker.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
