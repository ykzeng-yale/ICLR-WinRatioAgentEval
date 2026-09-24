"""EB5 argv shim: ``eb1c_llama_shim`` unchanged, plus one line per task POST it receives.

Repair contract EB5 (session 60; root 20:40 item 3, root 21:15 item 3).  The controls of
``tests_eb5_resolution.py`` must COUNT the POSTs a worker makes -- "no further POSTs" after a
kill (C3), "the late POST counted at the mock" (C5), a live orphan still sending into a resumed
trial's server (C6) -- and ``lab_mock_server`` keeps its ``n_requests`` counter inside the
server process, where a subprocess control cannot read it.  This launcher target does exactly
what ``eb1c_llama_shim.main`` does (strict frozen argv, the scenario of its start count, the
launch record, ``exec``-free so the recorded pid is this process) and, before the mock serves
anything, wraps ``lab_mock_server._Handler._complete`` -- the method every chat-completion POST
with a parseable body reaches -- so that each POST appends ONE line to
``$EB1C_SHIM_STATE/posts.jsonl``: ``{t_wall, pid, uid, kind}`` (the task uid and the call kind
the mock itself derives from the messages), written with one ``os.write`` on an ``O_APPEND``
descriptor and fsynced, BEFORE the mock handles the request.  Nothing else is changed: faults,
counters, responses and ``/metrics`` / ``/slots`` are the mock's own.

A TEST DOUBLE: nothing it serves is an observation.  Standard library plus the two modules it
wraps.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eb1c_llama_shim                                                  # noqa: E402
import lab_mock_server                                                  # noqa: E402

POSTS_NAME = 'posts.jsonl'


def install_post_log(state: Path) -> None:
    """Wrap the mock's completion handler: one durable line per POST, then the mock."""
    handler = lab_mock_server._Handler
    original = handler._complete
    lock = threading.Lock()
    path = state / POSTS_NAME

    def _complete(self, body):
        messages = body.get('messages') or []
        row = {'t_wall': time.time(), 'pid': os.getpid(),
               'uid': lab_mock_server.recover_uid(messages, self.state.tasks),
               'kind': lab_mock_server.classify_kind(messages)}
        line = (json.dumps(row, sort_keys=True) + '\n').encode('utf-8')
        with lock:
            fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                os.write(fd, line)
                os.fsync(fd)
            finally:
                os.close(fd)
        return original(self, body)

    handler._complete = _complete


def main(argv: list[str] | None = None) -> int:
    state = os.environ.get(eb1c_llama_shim.STATE_ENV)
    if state:
        install_post_log(Path(state))
    return eb1c_llama_shim.main(argv)


if __name__ == '__main__':
    sys.exit(main())
