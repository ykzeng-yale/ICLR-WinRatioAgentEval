"""Scripted stand-in for llama-server, so the whole program is dry-runnable with no model.

ARCHITECTURE_FINAL.md section 8 is the specification: the endpoints of 8.1, the scenario file
of 8.2 and the counter semantics of 8.3.  This is a **test double**: it never runs during a
trial, and nothing it produces may be reported as an observation.

Standard library only (isolation matrix 3.16: this module may import nothing, not even
``lab_common``).  ``ThreadingHTTPServer`` is the one permitted use of threads in the whole
harness, because a single-threaded server cannot exhibit the two-slot concurrency the tests
need.

Determinism under concurrency comes from keying every scripted decision on ``(uid, kind,
try)`` and a frozen ``outcome_seed`` rather than on a global request index; only the
``after_requests`` faults (used for the supervisor and chaos scenarios) key on the global
counter.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# Prompt stems of experiments/local_stream/agent.py, copied verbatim because this module may
# not import the pilot.  They are only used to classify a request, never to generate one.
TEST_STEM = 'Write 3 to 5 `assert` statements that test the function'
REPAIR_STEM = 'Running the function together with the tests below failed.'
SMOKE_STEM = 'Reply with the single word: pong'

FAULT_KINDS = ('timeout', 'http', 'reset', 'malformed', 'no_usage', 'length', 'receipt',
               'alias', 'cache_n', 'exit', 'outage')


class MockState:
    """Mutable server state: counters, per-key try indices, outages and the fault log."""

    def __init__(self, scenario: dict) -> None:
        self.lock = threading.Lock()
        self.scenario = scenario
        self.alias: str = str(scenario.get('alias') or 'mock-alias')
        self.total_slots: int = int(scenario.get('total_slots') or 2)
        self.prompt_tokens_total = 0
        self.tokens_predicted_total = 0
        self.n_decode_total = 0
        self.requests_processing = 0
        self.requests_deferred = 0
        self.active_slots = 0
        self.n_requests = 0
        self.outage_until = 0.0
        self.stopped = False
        self.exit_code: int | None = None
        self.tries: dict[str, int] = {}
        self.faults_fired: list[dict] = []
        self.tasks: list[dict] = _load_tasks(scenario)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                'prompt_tokens_total': self.prompt_tokens_total,
                'tokens_predicted_total': self.tokens_predicted_total,
                'n_decode_total': self.n_decode_total,
                'requests_processing': self.requests_processing,
                'requests_deferred': self.requests_deferred,
                'n_requests': self.n_requests,
                'faults_fired': list(self.faults_fired),
                'exit_code': self.exit_code,
            }


def _load_tasks(scenario: dict) -> list[dict]:
    """Tasks come from ``tasks`` inline or from the ``tasks_path`` JSON/JSONL file.

    A task needs ``uid``, ``prompt`` and (for a useful episode) ``reference`` and
    ``entry_point``: the mock answers with the reference solution or with a stub, exactly as
    the pilot's ``MockModel`` does, so ``run_episode`` runs end to end with no model."""
    inline = scenario.get('tasks')
    if isinstance(inline, list):
        return [dict(t) for t in inline]
    path = scenario.get('tasks_path')
    if not path or not os.path.exists(str(path)):
        return []
    raw = open(str(path), encoding='utf-8').read().strip()
    if not raw:
        return []
    if raw.lstrip().startswith('['):
        return [dict(t) for t in json.loads(raw)]
    return [dict(json.loads(line)) for line in raw.splitlines() if line.strip()]


def _roll(seed: int, *parts: object) -> float:
    """A deterministic uniform draw in [0, 1) from the frozen seed and the key parts."""
    key = '|'.join([str(seed)] + [str(p) for p in parts])
    return int(hashlib.sha256(key.encode('utf-8')).hexdigest()[:8], 16) / float(1 << 32)


def classify_kind(messages: list[dict]) -> str:
    """``tests`` / ``repair`` / ``smoke`` / ``code``, from the pilot's prompt stems."""
    blob = '\n'.join(str(m.get('content') or '') for m in messages)
    if TEST_STEM in blob:
        return 'tests'
    if REPAIR_STEM in blob:
        return 'repair'
    if SMOKE_STEM in blob:
        return 'smoke'
    return 'code'


def recover_uid(messages: list[dict], tasks: list[dict]) -> str | None:
    """The task whose ``prompt`` is a substring of the first user message.

    Where several prompts match (one a prefix of another) the longest wins, and ties are
    broken by the uid, so the answer is a deterministic function of the request."""
    first_user = ''
    for m in messages:
        if m.get('role') == 'user':
            first_user = str(m.get('content') or '')
            break
    best: tuple[int, str] | None = None
    for t in tasks:
        prompt = str(t.get('prompt') or '')
        if prompt and prompt in first_user:
            cand = (len(prompt), str(t.get('uid')))
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                best = cand
    return best[1] if best else None


def match_fault(state: MockState, uid: str | None, kind: str, try_index: int,
                n_requests: int) -> dict | None:
    """The first fault of the scenario whose ``match`` block fits this request."""
    for fault in state.scenario.get('faults') or []:
        m = fault.get('match') or {}
        if 'after_requests' in m:
            if n_requests >= int(m['after_requests']):
                return fault
            continue
        if 'uid' in m and m['uid'] != uid:
            continue
        if 'kind' in m and m['kind'] != kind:
            continue
        if 'try' in m and int(m['try']) != int(try_index):
            continue
        return fault
    return None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'lab_mock_server/1'

    # -- plumbing ----------------------------------------------------------- #
    def log_message(self, fmt: str, *args: object) -> None:      # silence the test output
        return

    @property
    def state(self) -> MockState:
        return self.server.state                                  # type: ignore[attr-defined]

    def _json(self, code: int, obj: object) -> None:
        raw = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _raw(self, code: int, body: bytes, ctype: str = 'application/json') -> None:
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _outage_active(self) -> bool:
        with self.state.lock:
            return time.monotonic() < self.state.outage_until

    # -- GET ---------------------------------------------------------------- #
    def do_GET(self) -> None:
        path = self.path.split('?', 1)[0]
        st = self.state
        if path == '/health':
            if self._outage_active():
                self._json(503, {'error': {'code': 503}})
            else:
                self._json(200, {'status': 'ok'})
            return
        if path == '/props':
            self._json(200, st.scenario.get('props') or {})
            return
        if path in ('/v1/models', '/models'):
            self._json(200, {'object': 'list',
                             'data': [{'id': st.alias, 'object': 'model'}]})
            return
        if path == '/slots':
            with st.lock:
                busy = st.active_slots
            self._json(200, [{'id': i, 'is_processing': i < busy}
                             for i in range(st.total_slots)])
            return
        if path == '/metrics':
            self._raw(200, self._metrics_text().encode('utf-8'), 'text/plain; version=0.0.4')
            return
        self._json(404, {'error': {'code': 404}})

    def _metrics_text(self) -> str:
        st = self.state
        with st.lock:
            rows = [
                ('llamacpp:prompt_tokens_total', st.prompt_tokens_total),
                ('llamacpp:tokens_predicted_total', st.tokens_predicted_total),
                ('llamacpp:n_decode_total', st.n_decode_total),
                ('llamacpp:requests_processing', st.requests_processing),
                ('llamacpp:requests_deferred', st.requests_deferred),
            ]
        out = []
        for name, value in rows:
            out.append('# HELP %s scripted mock counter' % name)
            out.append('# TYPE %s counter' % name)
            out.append('%s %d' % (name, value))
        return '\n'.join(out) + '\n'

    # -- POST --------------------------------------------------------------- #
    def do_POST(self) -> None:
        path = self.path.split('?', 1)[0]
        if path not in ('/v1/chat/completions', '/chat/completions'):
            self._json(404, {'error': {'code': 404}})
            return
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b''
        try:
            body = json.loads(raw.decode('utf-8'))
        except ValueError:
            self._json(400, {'error': {'code': 400}})
            return
        if self._outage_active():
            self._json(503, {'error': {'code': 503}})
            return
        self._complete(body)

    def _complete(self, body: dict) -> None:
        st = self.state
        sc = st.scenario
        messages = body.get('messages') or []
        kind = classify_kind(messages)
        uid = recover_uid(messages, st.tasks)
        key = '%s|%s' % (uid, kind)
        with st.lock:
            try_index = st.tries.get(key, 0)
            st.tries[key] = try_index + 1
            st.n_requests += 1
            n_requests = st.n_requests
            st.active_slots += 1
            st.requests_processing = st.active_slots
            active = st.active_slots
        try:
            fault = match_fault(st, uid, kind, try_index, n_requests)
            tokens = _token_counts(sc, messages, kind)
            if fault is not None:
                if self._apply_fault(fault, body, tokens, kind, uid, try_index, active):
                    return
            self._sleep_for(sc, tokens, active)
            payload = self._build_response(sc, body, uid, kind, try_index, tokens)
            with st.lock:
                st.prompt_tokens_total += tokens['prompt']
                st.tokens_predicted_total += tokens['completion']
                st.n_decode_total += tokens['completion']
            self._json(200, payload)
        finally:
            with st.lock:
                st.active_slots = max(0, st.active_slots - 1)
                st.requests_processing = st.active_slots

    # -- faults -------------------------------------------------------------- #
    def _apply_fault(self, fault: dict, body: dict, tokens: dict, kind: str,
                     uid: str | None, try_index: int, active: int) -> bool:
        """Apply one scripted fault.  Returns True when the response is finished here."""
        st = self.state
        do = str(fault.get('do'))
        with st.lock:
            st.faults_fired.append({'do': do, 'uid': uid, 'kind': kind, 'try': try_index})
        if do == 'timeout':
            self._count_cancelled(tokens)
            time.sleep(float(fault.get('sleep_s') or 400.0))
            try:
                self._json(200, self._build_response(st.scenario, body, uid, kind,
                                                     try_index, tokens))
            except OSError:
                pass
            return True
        if do == 'reset':
            self._count_cancelled(tokens)
            self._drop_connection()
            return True
        if do == 'http':
            self._json(int(fault.get('status') or 500),
                       {'error': {'code': int(fault.get('status') or 500)}})
            return True
        if do == 'malformed':
            self._raw(200, b'{not json')
            return True
        if do == 'exit':
            code = int(fault.get('code') or 1)
            with st.lock:
                st.exit_code = code
            if getattr(self.server, 'exit_is_fatal', False):
                os._exit(code)                      # a real process death; main() only
            # In-process the same effect is produced by refusing to serve any further
            # request: from the client's side both are a dead server.
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            self._drop_connection()
            return True
        if do == 'outage':
            with st.lock:
                st.outage_until = time.monotonic() + float(fault.get('seconds') or 20.0)
            self._json(503, {'error': {'code': 503}})
            return True
        # the remaining faults mutate an otherwise normal 200.  The counters always rise by
        # the tokens actually generated, including under `no_usage`, where the response
        # simply does not report them -- which is precisely the window the reconciliation of
        # protocol 13.1 has to treat as unknown rather than as zero.
        self._sleep_for(st.scenario, tokens, active)
        payload = self._build_response(st.scenario, body, uid, kind, try_index, tokens,
                                       fault=fault)
        with st.lock:
            st.prompt_tokens_total += tokens['prompt']
            st.tokens_predicted_total += tokens['completion']
            st.n_decode_total += tokens['completion']
        self._json(200, payload)
        return True

    def _drop_connection(self) -> None:
        """Close the socket without a response: the client sees a connection reset."""
        self.close_connection = True
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def _count_cancelled(self, tokens: dict) -> None:
        """A cancelled generation contributes its tokens only when the scenario says the
        server counts them (ARCHITECTURE_FINAL.md 8.3; this is the switch that exercises both
        branches of the accounting wording of PG-10)."""
        st = self.state
        if not st.scenario.get('count_cancelled_tokens'):
            return
        with st.lock:
            st.prompt_tokens_total += tokens['prompt']
            st.tokens_predicted_total += tokens['completion']
            st.n_decode_total += tokens['completion']

    # -- response construction ----------------------------------------------- #
    def _sleep_for(self, sc: dict, tokens: dict, active_slots: int) -> None:
        rate = float(sc.get('rate_tokens_per_s') or 120.0)
        if rate <= 0:
            return
        eff = rate / max(1, int(active_slots))
        time.sleep((tokens['prompt'] + tokens['completion']) / eff)

    def _build_response(self, sc: dict, body: dict, uid: str | None, kind: str,
                        try_index: int, tokens: dict, fault: dict | None = None) -> dict:
        st = self.state
        do = str(fault.get('do')) if fault else ''
        content = self._content(sc, uid, kind, try_index)
        text = '```python\n%s\n```' % content.rstrip('\n')
        gen = dict(sc.get('defaults') or {})
        for key in ('temperature', 'top_p', 'top_k', 'min_p', 'typical_p', 'repeat_penalty',
                    'presence_penalty', 'frequency_penalty', 'mirostat'):
            if key in body:
                gen[key] = body[key]
        if 'max_tokens' in body:
            gen['n_predict'] = body['max_tokens']
        gen['seed'] = body.get('seed')
        finish = 'stop'
        truncated = False
        cache_n = 0
        tokens_cached = 0
        model = st.alias
        usage_present = True
        if do == 'receipt':
            # `set` changes or adds a key, `unset` removes one: the three ways a receipt can
            # deviate (a changed value, an unknown key, a missing key) are all reachable.
            gen.update(fault.get('set') or {})
            for key in fault.get('unset') or []:
                gen.pop(key, None)
        elif do == 'alias':
            model = str((fault.get('set') or {}).get('model') or 'other-model')
        elif do == 'cache_n':
            cache_n = int((fault.get('set') or {}).get('cache_n') or 7)
            tokens_cached = int((fault.get('set') or {}).get('tokens_cached') or 0)
        elif do == 'length':
            finish = 'length'
            truncated = True
        elif do == 'no_usage':
            usage_present = False
        rid = hashlib.sha256(('%s|%s|%d|%d' % (uid, kind, try_index, st.n_requests)
                              ).encode('utf-8')).hexdigest()[:16]
        out: dict[str, Any] = {
            'id': 'chatcmpl-%s' % rid,
            'object': 'chat.completion',
            'created': 1758300000,
            'model': model,
            'choices': [{'index': 0,
                         'message': {'role': 'assistant', 'content': text},
                         'finish_reason': finish}],
            'timings': {
                'cache_n': cache_n,
                'prompt_n': tokens['prompt'],
                'prompt_ms': round(tokens['prompt'] * 0.4, 3),
                'predicted_n': tokens['completion'],
                'predicted_ms': round(tokens['completion'] * 7.0, 3),
                'prompt_per_second': 2600.0,
                'predicted_per_second': 142.2,
            },
            '__verbose': {
                'generation_settings': gen,
                'id_slot': 0,
                'tokens_predicted': tokens['completion'],
                'tokens_evaluated': tokens['prompt'],
                'tokens_cached': tokens_cached,
                'truncated': truncated,
                'stop_type': 'eos' if finish == 'stop' else 'limit',
                'prompt': _rendered_prompt(body),
            },
        }
        if usage_present:
            out['usage'] = {
                'prompt_tokens': tokens['prompt'],
                'completion_tokens': tokens['completion'],
                'total_tokens': tokens['prompt'] + tokens['completion'],
                'prompt_tokens_details': {'cached_tokens': tokens_cached},
            }
        return out

    def _content(self, sc: dict, uid: str | None, kind: str, try_index: int) -> str:
        """Code, self-tests or a repair, from the task's reference solution.

        Hidden tests are never used here (the mock has no access to them): this mirrors the
        pilot's ``MockModel``, which derives plausible output from the reference."""
        st = self.state
        seed = int(sc.get('outcome_seed') or 0)
        task = next((t for t in st.tasks if str(t.get('uid')) == str(uid)), None)
        ep = str((task or {}).get('entry_point') or 'solution')
        good = str((task or {}).get('reference') or 'def %s(*a, **k):\n    return None\n' % ep)
        stub = 'def %s(*args, **kwargs):\n    raise NotImplementedError("mock stub")\n' % ep
        outcomes = sc.get('outcomes') or {}
        if kind == 'smoke':
            return 'pong'
        if kind == 'code':
            p_good = float((outcomes.get('single_shot') or {}).get('p_good', 0.55))
            return good if _roll(seed, uid, 'code') < p_good else stub
        if kind == 'tests':
            p_fail = float((outcomes.get('self_test_repair') or {}).get('p_selftest_fails', 0.0))
            lines = ['import inspect',
                     'assert callable(%s)' % ep,
                     'assert "NotImplementedError" not in inspect.getsource(%s)' % ep]
            if _roll(seed, uid, 'selftest') < p_fail:
                lines.append('assert False, "scripted self-test failure"')
            return '\n'.join(lines) + '\n'
        p_fix = float((outcomes.get('self_test_repair') or {}).get('p_repair_fixes', 0.25))
        return good if _roll(seed, uid, 'repair', try_index) < p_fix else stub


def _rendered_prompt(body: dict) -> str:
    return '\n'.join('<|im_start|>%s\n%s<|im_end|>' % (m.get('role'), m.get('content'))
                     for m in (body.get('messages') or []))


def _token_counts(sc: dict, messages: list[dict], kind: str) -> dict:
    tok = sc.get('tokens') or {}
    chars = sum(len(str(m.get('content') or '')) for m in messages)
    prompt = max(1, int(math.ceil(chars * float(tok.get('prompt_per_char', 0.25)))))
    completion = int(tok.get('completion_%s' % kind, tok.get('completion_code', 180)))
    return {'prompt': prompt, 'completion': max(0, completion)}


class MockServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    exit_is_fatal = False

    def __init__(self, addr: tuple[str, int], state: MockState) -> None:
        super().__init__(addr, _Handler)
        self.state = state

    def handle_error(self, request: object, client_address: object) -> None:
        """A scripted disconnect is the point of the `reset` and `exit` faults, and a client
        that timed out closes its socket: neither is an error of this server, so neither
        prints a traceback into the test output.  Anything else is re-raised."""
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionError, BrokenPipeError, TimeoutError, OSError)):
            return
        raise exc                                                # pragma: no cover


def make_server(scenario: dict, *, port: int = 0) -> tuple[ThreadingHTTPServer, int]:
    """Bind a scripted mock on 127.0.0.1 and return it with the port actually bound.

    The server is not started: the caller runs ``serve_forever`` in a thread (in-process) or
    :func:`main` runs it in its own process."""
    state = MockState(scenario)
    srv = MockServer(('127.0.0.1', int(port)), state)
    return srv, srv.server_address[1]


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--scenario FILE --port N [--alias A] [--state-out FILE]``.

    Runs until SIGTERM.  ``--state-out`` receives the final counter state so that a test can
    assert reconciliation after the process is gone.  In this mode an ``exit`` fault is a real
    ``os._exit``: the supervisor must restart the process, which is the behaviour
    ``server_down`` / ``server_restarted`` and ``counters_lost`` are there to detect."""
    ap = argparse.ArgumentParser(prog='lab_mock_server')
    ap.add_argument('--scenario', required=True)
    ap.add_argument('--port', type=int, default=0)
    ap.add_argument('--alias')
    ap.add_argument('--state-out')
    ap.add_argument('--port-out')
    args = ap.parse_args(argv)
    scenario = json.loads(open(args.scenario, encoding='utf-8').read())
    if args.alias:
        scenario['alias'] = args.alias
    srv, port = make_server(scenario, port=args.port)
    srv.exit_is_fatal = True                                    # type: ignore[attr-defined]
    if args.port_out:
        with open(args.port_out, 'w', encoding='utf-8') as fh:
            fh.write(str(port))
    try:
        srv.serve_forever(poll_interval=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        if args.state_out:
            with open(args.state_out, 'w', encoding='utf-8') as fh:
                json.dump(srv.state.snapshot(), fh, sort_keys=True)  # type: ignore[attr-defined]
        srv.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
