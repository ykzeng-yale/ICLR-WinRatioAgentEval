"""Two coding-workflow variants over one shared prompt, plus the episode runner.

Variant A ``single_shot``: one chat completion; first ```python block (fallback:
whole text) is the candidate.
Variant B ``self_test_repair``: call 1 writes code; call 2 writes 3-5 asserts
WITHOUT seeing hidden tests; code + self-tests run in the sandbox; on failure
(assertion, exception, timeout, syntax error or static block) call 3 repairs
given the traceback; at most 2 repair rounds (<= 4 LLM calls). The final
candidate is the last code produced, whether or not the self-tests passed.

Both variants talk to an OpenAI-compatible /v1/chat/completions endpoint. A
deterministic MockModel exists for dry runs only; it uses each task's reference
solution to fabricate plausible outputs and must never be reported as a result.
Hidden tests are never placed in any prompt. MBPP prompts show the task text
plus ONLY the function signature line ``def name(args):`` of the entry point,
reconstructed from the reference solution's def statement (never any assert;
in 416/427 tasks the entry point is the first def, in 11 the first def is a
helper and the entry point's def is used). Every assert in test_list (+
challenge tests) is graded. HumanEval prompts show the signature + docstring.

Latency scope (protocol section 8): ``latency_s`` runs from before the first
model call to the moment the final candidate exists; it includes every LLM
call and the agent's own sandbox executions (self-tests) but EXCLUDES
hidden-test verification, recorded separately as ``verify_seconds``.
"""
from __future__ import annotations
import ast, hashlib, json, re, time, traceback, warnings

import requests

from common import VARIANT_LETTER, iso, now_ts
from sandbox import run_program
from verify import verify

SYSTEM_PROMPT = ('You are an expert Python programmer. Reply with one complete, self-contained Python solution in a single '
                 '```python code block. Include every import you need. Do not include tests, prints, or example usage.')
TEST_PROMPT = ('Write 3 to 5 `assert` statements that test the function `{entry_point}` implemented above. Reply with a single '
               '```python code block containing only assert statements (plus imports if needed). Do not redefine the function. '
               'Cover typical inputs and at least one edge case.')
REPAIR_PROMPT = ('Running the function together with the tests below failed. Fix the implementation. Reply with the complete '
                 'corrected solution in a single ```python code block (imports included, no tests).\n\nTests:\n```python\n{tests}\n```\n\n'
                 'Traceback / output:\n```\n{trace}\n```')
_CODE_BLOCK = re.compile(r'```(?:python|py|python3)?[ \t]*\n(.*?)```', re.S)
_SPECIAL_TOKENS = re.compile(r'<\|(?:im_end|im_start|endoftext|end_of_text|eot_id)\|>')  # mlx_lm.server leaves the stop token in content


def signature_line(task: dict) -> str:
    """``def name(args):`` for the entry point, taken from the reference solution's def statement.

    Only the signature is shown; defaults are kept (they are part of the calling
    convention), decorators, annotations' bodies and return values are not.
    Falls back to ``def <entry_point>(...):`` if the reference cannot be parsed.
    """
    ep = task.get('entry_point') or ''
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SyntaxWarning)  # some reference strings carry invalid escapes
            tree = ast.parse(task['reference'])
    except SyntaxError:
        tree = None
    if tree is not None:
        defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        target = next((d for d in defs if d.name == ep), None) or (defs[0] if defs else None)
        if target is not None:
            return '%sdef %s(%s):' % ('async ' if isinstance(target, ast.AsyncFunctionDef) else '', target.name, ast.unparse(target.args))
    return 'def %s(...):' % (ep or 'solution')


def build_user_prompt(task: dict) -> str:
    if task['benchmark'] == 'mbpp':
        p = task['prompt'].rstrip()
        p += '\n\nUse exactly this function signature:\n```python\n%s\n```' % signature_line(task)
        return p
    return 'Complete the following Python function.\n\n```python\n%s\n```' % task['prompt']


def extract_code(text: str) -> str:
    if not text:
        return ''
    blocks = _CODE_BLOCK.findall(text)
    if blocks:
        return blocks[0].strip('\n') + '\n'
    return _SPECIAL_TOKENS.sub('', text).strip() + '\n'


def _estimate_tokens(text: str, model_name: str):
    """Fallback when the API returns no usage: model tokenizer if cached locally, else ~4 chars/token."""
    try:
        from transformers import AutoTokenizer
        tok = _estimate_tokens._cache.get(model_name)
        if tok is None:
            tok = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            _estimate_tokens._cache[model_name] = tok
        return len(tok.encode(text)), 'tokenizer'
    except Exception:
        return max(1, len(text) // 4), 'chars/4'
_estimate_tokens._cache = {}


class ConnectionFailure(RuntimeError):
    pass


class OpenAICompatModel:
    """Minimal OpenAI-compatible chat client (requests only; no vendor SDK)."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg['base_url'].rstrip('/')
        self.model = cfg['model']
        self.session = requests.Session()
        self.name = 'openai_compat'

    def server_info(self) -> dict:
        try:
            r = self.session.get(self.base_url + '/models', timeout=30)
            return dict(status=r.status_code, body=r.json() if r.ok else r.text[:500])
        except Exception as e:
            return dict(error=repr(e))

    def chat(self, messages: list, ctx: dict) -> dict:
        body = dict(model=self.model, messages=messages, temperature=self.cfg['temperature'], top_p=self.cfg['top_p'],
                    max_tokens=self.cfg['max_tokens'], stream=False)
        if ctx.get('seed') is not None:
            body['seed'] = int(ctx['seed'])
        retries = int(self.cfg.get('max_connection_retries', 2)); log = []
        for attempt in range(retries + 1):
            t0 = time.perf_counter()
            try:
                r = self.session.post(self.base_url + '/chat/completions', json=body, timeout=self.cfg['request_timeout_s'])
                r.raise_for_status()
                data = r.json()
                text = data['choices'][0]['message'].get('content') or ''
                usage = data.get('usage') or {}
                pt, ct, est = usage.get('prompt_tokens'), usage.get('completion_tokens'), None
                if pt is None or ct is None:
                    pt, est = _estimate_tokens('\n'.join(m['content'] for m in messages), self.model)
                    ct, _ = _estimate_tokens(text, self.model)
                return dict(text=text, prompt_tokens=int(pt), completion_tokens=int(ct), tokens_estimated=est,
                            call_seconds=time.perf_counter() - t0, retries=attempt, retry_log=log,
                            finish_reason=data['choices'][0].get('finish_reason'), response_model=data.get('model'))
            except (requests.ConnectionError, requests.Timeout) as e:
                log.append(dict(attempt=attempt, error=repr(e)[:300], ts=iso(now_ts())))
                if attempt >= retries:
                    raise ConnectionFailure('connection failed after %d attempts: %r' % (attempt + 1, e)) from e
                time.sleep(min(2.0 * (attempt + 1), 10.0))
            except requests.HTTPError as e:  # non-retryable server error: an outcome, not an exclusion
                raise RuntimeError('http error %s: %s' % (e.response.status_code, e.response.text[:300])) from e


class MockModel:
    """Deterministic stand-in for dry runs. Derives behaviour from sha256(task, variant, trial, call kind).

    Roughly 55% of single_shot tasks and 65% of self_test_repair tasks end up with the
    reference solution; about a third of B episodes take the repair path. Uses task
    reference code (NOT hidden tests). Never use for reported results.
    """
    name = 'mock'

    def __init__(self, cfg: dict, tasks: list):
        self.cfg = cfg; self.model = 'mock-deterministic-v1'; self.tasks = {t['uid']: t for t in tasks}

    def server_info(self):
        return dict(mock=True)

    @staticmethod
    def _h(*parts) -> int:
        return int(hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:8], 16)

    def chat(self, messages: list, ctx: dict) -> dict:
        task = self.tasks[ctx['uid']]; variant = ctx['variant']; kind = ctx['kind']
        h = self._h(ctx['uid'], variant, ctx.get('trial', 1)) % 100
        good = task['reference']
        ep = task.get('entry_point') or 'solution'
        stub = 'def %s(*args, **kwargs):\n    raise NotImplementedError("mock stub")\n' % ep
        if kind == 'code':
            if variant == 'single_shot':
                text = good if h < 55 else stub
            else:  # B: h<55 right first time; 55<=h<65 wrong first then repaired; else wrong
                text = good if h < 55 else stub
        elif kind == 'tests':
            text = 'import inspect\nassert callable(%s)\nassert "NotImplementedError" not in inspect.getsource(%s)\n' % (ep, ep)
        else:  # repair
            text = good if h < 65 else stub
        out = '```python\n%s\n```' % text.rstrip('\n')
        ptoks = sum(len(m['content']) for m in messages) // 4
        return dict(text=out, prompt_tokens=ptoks, completion_tokens=len(out) // 4 + (ctx.get('round', 0) * 3), tokens_estimated=None,
                    call_seconds=0.0, retries=0, retry_log=[], finish_reason='stop', response_model=self.model)


def _self_test_program(code: str, tests: str) -> str:
    return code.rstrip() + '\n\n' + tests.rstrip() + '\n'


def run_episode(task: dict, variant: str, model, cfg: dict, meta: dict) -> dict:
    """Run one episode and return the full record (see protocol.md, Record schema)."""
    t_start = now_ts(); tw0 = time.perf_counter()
    rec = dict(task_id=task['uid'], benchmark=task['benchmark'], variant=variant, variant_letter=VARIANT_LETTER[variant],
               trial=meta.get('trial', 1), arrival_index=meta.get('arrival_index'), pair_index=meta.get('pair_index'),
               orientation=meta.get('orientation'), **{'pass': meta.get('pass')}, start_ts=iso(t_start),
               n_llm_calls=0, prompt_tokens=0, completion_tokens=0, tokens_estimated=None, n_executions=0, repair_rounds=0,
               self_test_passed=None, success=False, sandbox_flag=False, timed_out=False, error=None, final_code='',
               model=model.model, model_kind=model.name, endpoint=cfg.get('base_url') if model.name != 'mock' else 'mock',
               harness_git_hash=meta.get('harness_git_hash', 'unknown'), config_hash=cfg['_config_hash'],
               connection_retries=0, retry_log=[], llm_call_seconds=[], execution_seconds=[], self_test_code='',
               verify_stderr='', finish_reasons=[], response_models=[], verify_seconds=0.0, sentinel_seen=False, hack_flags=[],
               static_flags=[], sandbox_kind=None, sandbox_profile_sha256=None, latency_scope='llm_calls+self_tests; excludes hidden-test verification')
    sb = dict(timeout_s=cfg['sandbox_timeout_s'], mem_bytes=cfg['sandbox_mem_bytes'], cpu_seconds=cfg['sandbox_cpu_s'], output_cap=cfg['sandbox_output_cap_bytes'])
    base_seed = (meta.get('trial', 1) * 1_000_003 + (meta.get('arrival_index') or 0) * 7 + (1 if variant == 'self_test_repair' else 0)) % (2**31)
    messages = [dict(role='system', content=SYSTEM_PROMPT), dict(role='user', content=build_user_prompt(task))]
    ctx = dict(uid=task['uid'], variant=variant, trial=meta.get('trial', 1), kind='code', seed=base_seed, round=0)

    def call(msgs, kind, rnd):
        c = dict(ctx, kind=kind, round=rnd, seed=base_seed + 10 * rnd + (3 if kind == 'tests' else 0))
        out = model.chat(msgs, c)
        rec['n_llm_calls'] += 1; rec['prompt_tokens'] += out['prompt_tokens']; rec['completion_tokens'] += out['completion_tokens']
        rec['llm_call_seconds'].append(round(out['call_seconds'], 4)); rec['connection_retries'] += out['retries']
        rec['retry_log'] += out['retry_log']; rec['finish_reasons'].append(out.get('finish_reason'))
        rec['response_models'].append(out.get('response_model'))
        if out.get('tokens_estimated'):
            rec['tokens_estimated'] = out['tokens_estimated']
        return out['text']

    code = ''
    try:
        code = extract_code(call(messages, 'code', 0))
        if variant == 'self_test_repair':
            convo = messages + [dict(role='assistant', content='```python\n%s```' % code),
                                dict(role='user', content=TEST_PROMPT.format(entry_point=task.get('entry_point') or 'you wrote'))]
            tests = extract_code(call(convo, 'tests', 0)); rec['self_test_code'] = tests
            for rnd in range(cfg['max_repair_rounds'] + 1):
                run = run_program(_self_test_program(code, tests), timeout_s=sb['timeout_s'], mem_bytes=sb['mem_bytes'],
                                  cpu_seconds=sb['cpu_seconds'], output_cap=sb['output_cap'])
                rec['n_executions'] += 1; rec['execution_seconds'].append(round(run['seconds'], 4))
                rec['self_test_passed'] = bool(run['passed'])
                if run['passed'] or rnd == cfg['max_repair_rounds']:
                    break
                trace = (run['stderr'] or run['stdout'] or '(no output)')[-2000:]
                repair_msgs = messages + [dict(role='assistant', content='```python\n%s```' % code),
                                          dict(role='user', content=REPAIR_PROMPT.format(tests=tests.rstrip(), trace=trace))]
                code = extract_code(call(repair_msgs, 'repair', rnd + 1)); rec['repair_rounds'] += 1
    except Exception as e:  # API/connection failures are outcomes (success=False), not exclusions
        rec['error'] = '%s: %s' % (type(e).__name__, str(e)[:500])
        rec['error_traceback'] = traceback.format_exc()[-1500:]
    rec['final_code'] = code
    # latency stops here: the final candidate exists; hidden-test verification is grader time (verify_seconds)
    rec['latency_s'] = time.perf_counter() - tw0
    if code:
        v = verify(task, code, **sb)
        rec['n_executions'] += 1 if v['run'].get('executed') else 0
        rec['execution_seconds'].append(round(v['run'].get('seconds', 0.0), 4))
        rec['success'] = v['success']; rec['sandbox_flag'] = v['sandbox_flag']; rec['timed_out'] = v['timed_out']
        rec['entry_point_defined'] = v['entry_point_defined']; rec['verify_returncode'] = v['run'].get('returncode')
        rec['verify_stderr'] = (v['run'].get('stderr') or '')[-1500:]; rec['sandbox_limits_applied'] = v['run'].get('limits_applied', '')
        rec['verify_seconds'] = v['verify_seconds']; rec['sentinel_seen'] = v['sentinel_seen']; rec['hack_flags'] = v['hack_flags']
        rec['static_flags'] = list(v['run'].get('flags') or []); rec['sandbox_kind'] = v['run'].get('sandbox_kind')
        rec['sandbox_profile_sha256'] = v['run'].get('profile_sha256')
    else:
        rec['hack_flags'] = []
    t_end = now_ts()
    rec['end_ts'] = iso(t_end)
    rec['success'] = bool(rec['success'])  # sandbox_flag is a recorded heuristic, not an outcome rule
    return rec
