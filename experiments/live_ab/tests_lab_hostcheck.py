"""Tests for the host quiescence gate (lab_hostcheck).

Every behavioural test drives a SYNTHESIZED process table through the injection points of
`enumerate_foreign_consumers`, so none of them depends on what happens to be running on the
machine at the time.  The two tests that do touch the real host assert only that the call
returns a well-formed result, never what it contains.

The account name used in the fixtures is a fixed literal passed explicitly as `accounts`,
so the redaction tests are independent of the account the suite runs under.
"""
from __future__ import annotations

import ast
import contextlib
import io
import shutil
import subprocess
import sys
import tokenize
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lab_common
import lab_eventlog
import lab_hostcheck as hc
import lab_verify_log

MODULE_PATH = HERE / 'lab_hostcheck.py'
ACCOUNT = 'yukangzengcmac'
ACCOUNTS = (ACCOUNT,)

# A faithful copy of a real offender seen on the serving host, with the account name and
# the foreign project's directories left in, because removing them is what is under test.
LLAMA_CMD = (
    '/private/tmp/claude-501/-Users-yukangzengcmac-ICLR-WinRatioAgentEvals/'
    '35a3ef1c-e430-45ac-b78e-94ba942c34a1/scratchpad/llama.cpp/build/bin/llama-server '
    '-m /Users/yukangzengcmac/.cache/huggingface/hub/'
    'models--Qwen--Qwen2.5-7B-Instruct-GGUF/snapshots/bb5d59e06d9551d752d08b292a50eb2/'
    'qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf '
    '--alias qwen2.5-7b-instruct --port 8191 -ngl 99 -np 4 -c 32768 --jinja '
    '--host 127.0.0.1')

QUIET_TABLE = '\n'.join([
    '    1     0 58-02:38:46  19088 /sbin/launchd',
    '  139     1    01:36:33   7760 /usr/libexec/secinitd',
    '  400     1    00:10:01   4096 /usr/sbin/cfprefsd agent',
])


def table(*lines: str) -> str:
    return '\n'.join(lines)


def ps_line(pid: int, ppid: int, etime: str, rss_kb: int, command: str) -> str:
    return f'{pid:>5} {ppid:>5} {etime:>11} {rss_kb:>7} {command}'


BIG_KB = (hc.PROBE_RSS_FLOOR_BYTES // 1024) + 1024       # comfortably over the probe floor
SMALL_KB = (hc.PROBE_RSS_FLOOR_BYTES // 1024) - 1024      # comfortably under it

# A renamed copy of llama-server: the exact attack PREREG_CHECK C.3 demonstrated, where
# `cp llama-server srv` defeated the name list and the scan reported the host clean.
RENAMED_CMD = '/opt/priv/srv -m /Users/yukangzengcmac/m.gguf -ngl 99 -np 4 --port 9001'


class FakeCompleted:
    def __init__(self, stdout: str = '', returncode: int = 0) -> None:
        self.stdout = stdout.encode('utf-8')
        self.stderr = b''
        self.returncode = returncode


@contextlib.contextmanager
def fake_lsof(result=None, raises: BaseException | None = None):
    """Replace the module's subprocess entry point for the duration of one test.

    Every test using this passes `table_text`, so `ps` is never run and the only call this
    intercepts is the Metal probe."""
    real = hc.subprocess.run

    def fake(argv, **kwargs):
        if raises is not None:
            raise raises
        return result

    hc.subprocess.run = fake
    try:
        yield
    finally:
        hc.subprocess.run = real


def lsof_output(*rows: tuple[int, str]) -> str:
    """`lsof -F pn` field output: a `p<pid>` line followed by its `n<name>` lines."""
    out: list[str] = []
    for pid, name in rows:
        out.append(f'p{pid}')
        out.append(f'n{name}')
    return '\n'.join(out) + '\n'


class ParseTests(unittest.TestCase):
    def test_parse_etime_all_three_shapes(self) -> None:
        self.assertEqual(hc.parse_etime('02:03'), 123)
        self.assertEqual(hc.parse_etime('01:02:03'), 3723)
        self.assertEqual(hc.parse_etime('58-02:38:46'), 58 * 86400 + 2 * 3600 + 38 * 60 + 46)

    def test_parse_etime_rejects_nonsense(self) -> None:
        for bad in ('', 'x', '99', '1:2:3:4', '01:75'):
            with self.subTest(bad=bad):
                self.assertIsNone(hc.parse_etime(bad))

    def test_parse_ps_table_reads_fields_and_keeps_command_intact(self) -> None:
        rows, malformed = hc.parse_ps_table(ps_line(63658, 1, '08:31:12', 7041312, LLAMA_CMD))
        self.assertEqual(malformed, [])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.pid, 63658)
        self.assertEqual(row.ppid, 1)
        self.assertEqual(row.elapsed_s, 8 * 3600 + 31 * 60 + 12)
        self.assertEqual(row.rss_bytes, 7041312 * 1024)
        self.assertEqual(row.command, LLAMA_CMD)

    def test_malformed_lines_are_reported_not_dropped_silently(self) -> None:
        rows, malformed = hc.parse_ps_table(table(
            ps_line(1, 0, '00:01', 10, '/sbin/launchd'),
            'this line is not a process table row',
            '  abc   1  00:01  10  /bin/sh',
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(malformed), 2, malformed)
        for marker in malformed:
            self.assertNotIn(' ', marker)


class AllowlistTests(unittest.TestCase):
    def test_allowlist_contains_caller_pids_and_this_interpreter(self) -> None:
        rows, _ = hc.parse_ps_table(QUIET_TABLE)
        allow = hc.own_pid_allowlist({4242}, rows)
        self.assertIn(4242, allow)
        self.assertIn(__import__('os').getpid(), allow)

    def test_descendants_of_an_allowlisted_pid_are_excluded(self) -> None:
        """The harness may start its server through a shell, so only the shell's pid is in
        the allowlist.  Without the ppid closure the harness would report its own server."""
        rows, _ = hc.parse_ps_table(table(
            ps_line(500, 1, '00:10:00', 1000, '/bin/zsh -c run'),
            ps_line(501, 500, '00:09:00', 900000, '/opt/bin/llama-server -ngl 99'),
        ))
        allow = hc.own_pid_allowlist({500}, rows)
        self.assertEqual(allow & {500, 501}, {500, 501})
        without = hc.own_pid_allowlist({500}, rows, include_descendants=False)
        self.assertNotIn(501, without)

    def test_our_own_server_is_not_reported_but_a_foreign_one_is(self) -> None:
        text = table(
            ps_line(500, 1, '00:10:00', 1000, '/bin/zsh -c run'),
            ps_line(501, 500, '00:09:00', 900000, '/opt/bin/llama-server --port 8080 -ngl 99'),
            ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD),
        )
        scan = hc.enumerate_foreign_consumers({500}, table_text=text, metal_pids=set(),
                                              now=1.0e9, accounts=ACCOUNTS)
        self.assertEqual([f['pid'] for f in scan.findings], [900])


class DetectionTests(unittest.TestCase):
    def test_every_named_runner_is_detected(self) -> None:
        cases = {
            '/opt/bin/llama-server -ngl 99': 'llama-server',
            '/opt/bin/llama-cli -p hello': 'llama-cli',
            '/usr/local/bin/ollama serve': 'ollama',
            '/venv/bin/python -m mlx_lm.server --port 8080': 'mlx-lm',
            '/venv/bin/vllm serve some-model': 'vllm',
        }
        for command, label in cases.items():
            with self.subTest(command=command):
                self.assertEqual(hc.match_consumer(command), label)

    def test_a_runner_behind_a_wrapper_shell_is_still_detected(self) -> None:
        self.assertEqual(hc.match_consumer('/bin/sh -c /opt/bin/llama-server --port 1'),
                         'llama-server')

    def test_a_dotted_module_entrypoint_is_detected(self) -> None:
        self.assertEqual(
            hc.match_consumer('/venv/bin/python -m vllm.entrypoints.openai.api_server'),
            'vllm')

    def test_a_bare_runner_token_is_reported_on_purpose(self) -> None:
        """Observed for real: a parent shell whose argv merely contained the word was
        reported.  The gate errs this way deliberately -- `nohup llama-server ...` puts the
        runner in exactly this position, and a miss costs the trial its primary endpoint
        while a false positive costs one look at a pid.  Locked so it stays a choice."""
        self.assertEqual(hc.match_consumer('/bin/zsh -c run.sh # marker vllm here'), 'vllm')
        self.assertEqual(hc.match_consumer('/usr/bin/nohup llama-server --port 1'),
                         'llama-server')

    def test_innocent_commands_are_not_detected(self) -> None:
        for command in ('/sbin/launchd', '/usr/bin/vim notes.txt',
                        '/venv/bin/python analyse.py --plot'):
            with self.subTest(command=command):
                self.assertIsNone(hc.match_consumer(command))

    def test_a_similarly_named_file_or_directory_is_not_a_runner(self) -> None:
        """A substring rule flags these, and a gate that cries wolf gets bypassed."""
        for command in ('/usr/bin/vim /Users/x/ollama-notes/edit.txt',
                        '/usr/bin/vim ollama-notes.txt',
                        '/bin/cat /opt/vllm-benchmark/results.csv',
                        '/usr/bin/tail -f /var/log/llama-server-archive/old.log'):
            with self.subTest(command=command):
                self.assertIsNone(hc.match_consumer(command), command)

    def test_python_holding_a_metal_context_is_a_finding(self) -> None:
        text = table(
            ps_line(700, 1, '00:30:00', 2048, '/venv/bin/python train.py'),
            ps_line(701, 1, '00:30:00', 2048, '/venv/bin/python plot.py'),
        )
        scan = hc.enumerate_foreign_consumers(set(), table_text=text, metal_pids={700},
                                              now=1.0e9, accounts=ACCOUNTS)
        self.assertEqual([f['pid'] for f in scan.findings], [700])
        self.assertEqual(scan.findings[0]['detector'], hc.METAL_PYTHON_LABEL)

    def test_python_without_a_metal_context_is_not_a_finding(self) -> None:
        text = ps_line(700, 1, '00:30:00', 2048, '/venv/bin/python train.py')
        scan = hc.enumerate_foreign_consumers(set(), table_text=text, metal_pids=set(),
                                              now=1.0e9, accounts=ACCOUNTS)
        self.assertEqual(scan.findings, [])

    def test_is_python_command(self) -> None:
        self.assertTrue(hc.is_python_command('/venv/bin/python3.12 run.py'))
        self.assertTrue(hc.is_python_command('/usr/bin/python run.py'))
        self.assertFalse(hc.is_python_command('/usr/bin/pythonish run.py'))
        self.assertFalse(hc.is_python_command(''))


class FindingShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        rows, _ = hc.parse_ps_table(ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD))
        self.finding = hc.finding_for(rows[0], 'llama-server', now=1.0e9, accounts=ACCOUNTS)

    def test_finding_carries_the_required_fields(self) -> None:
        for key in ('pid', 'ppid', 'detector', 'start_utc', 'elapsed_s', 'rss_bytes',
                    'argv_sha256', 'command_summary'):
            self.assertIn(key, self.finding)
        self.assertEqual(self.finding['elapsed_s'], 8 * 3600 + 31 * 60 + 12)
        self.assertEqual(self.finding['rss_bytes'], 7041312 * 1024)
        self.assertEqual(len(self.finding['argv_sha256']), 64)

    def test_start_time_is_derived_as_now_minus_elapsed_in_utc(self) -> None:
        rows, _ = hc.parse_ps_table(ps_line(9, 1, '01:00:00', 10, '/opt/bin/llama-cli'))
        got = hc.finding_for(rows[0], 'llama-cli', now=1_600_000_000.0, accounts=ACCOUNTS)
        # 1_600_000_000 is 2020-09-13T12:26:40Z; one hour of elapsed time puts the start an
        # hour earlier.  Local time on this host would render 07:26:40, so this assertion
        # also pins the field to UTC.
        self.assertEqual(got['start_utc'], '2020-09-13T11:26:40Z')

    def test_digest_identifies_the_exact_command_without_publishing_it(self) -> None:
        other, _ = hc.parse_ps_table(ps_line(1, 1, '00:01', 1, LLAMA_CMD + ' --extra'))
        changed = hc.finding_for(other[0], 'llama-server', now=1.0e9, accounts=ACCOUNTS)
        self.assertNotEqual(self.finding['argv_sha256'], changed['argv_sha256'])

    def test_summary_keeps_the_evidence_that_matters(self) -> None:
        summary = self.finding['command_summary']
        self.assertEqual(summary[0], 'llama-server')
        for token in ('-ngl', '99', '--port', '8191', '<HOME>/*.gguf'):
            self.assertIn(token, summary, summary)

    def test_summary_is_short(self) -> None:
        self.assertLessEqual(len(self.finding['command_summary']),
                             hc.MAX_SUMMARY_TOKENS + 1)


class RedactionTests(unittest.TestCase):
    """The findings go into a public chain, so these are the load-bearing tests."""

    def test_account_name_and_home_are_gone_from_a_realistic_command_line(self) -> None:
        summary = hc.tokenize_command(LLAMA_CMD, accounts=ACCOUNTS)
        blob = ' '.join(summary)
        self.assertNotIn(ACCOUNT, blob)
        self.assertNotIn('/Users/', blob)
        self.assertNotIn('.cache', blob)
        self.assertNotIn('huggingface', blob)

    def test_account_name_embedded_mid_segment_is_removed(self) -> None:
        """The real path is /private/tmp/claude-501/-Users-<account>-<project>/..., where
        the account name is inside one segment and no home prefix matches it."""
        command = ('/opt/bin/llama-server --log-dir '
                   '/private/tmp/claude-501/-Users-yukangzengcmac-Proj/logs/run.log')
        summary = hc.tokenize_command(command, accounts=ACCOUNTS)
        self.assertNotIn(ACCOUNT, ' '.join(summary))
        self.assertIn('<TMP>/*.log', summary, summary)

    def test_a_bare_account_name_becomes_the_user_placeholder(self) -> None:
        summary = hc.tokenize_command('/opt/bin/ollama serve --user yukangzengcmac',
                                      accounts=ACCOUNTS)
        self.assertNotIn(ACCOUNT, ' '.join(summary))
        self.assertIn(hc.PLACEHOLDER_USER, summary, summary)

    def test_a_foreign_projects_directory_names_do_not_survive(self) -> None:
        command = '/Users/yukangzengcmac/DTR-AgentEvals/.venv/bin/python run.py --stage branch'
        summary = hc.tokenize_command(command, accounts=ACCOUNTS)
        self.assertNotIn('DTR-AgentEvals', ' '.join(summary))

    def test_loopback_survives_but_a_routable_address_does_not(self) -> None:
        keep = hc.tokenize_command('/opt/bin/llama-server --host 127.0.0.1', accounts=ACCOUNTS)
        self.assertIn('127.0.0.1', keep)
        drop = hc.tokenize_command('/opt/bin/llama-server --host 203.0.113.7', accounts=ACCOUNTS)
        self.assertNotIn('203.0.113.7', drop)
        self.assertIn(hc.PLACEHOLDER_REMOTE, drop, drop)

    def test_a_commit_id_shaped_token_is_redacted(self) -> None:
        summary = hc.tokenize_command('/opt/bin/llama-cli --rev bb5d59e06d9551d752d08b29',
                                      accounts=ACCOUNTS)
        self.assertNotIn('bb5d59e06d9551d752d08b29', ' '.join(summary))

    def test_the_summary_of_every_fixture_passes_the_safety_predicate(self) -> None:
        for command in (LLAMA_CMD, '/opt/bin/ollama serve',
                        '/Users/yukangzengcmac/x/.venv/bin/python -m mlx_lm.server',
                        '/opt/bin/llama-server --host 203.0.113.7 --key ABC/def'):
            with self.subTest(command=command[:40]):
                summary = hc.tokenize_command(command, accounts=ACCOUNTS)
                self.assertTrue(hc.summary_is_identifier_safe(summary, ACCOUNTS), summary)

    def test_the_predicate_actually_rejects_a_leak(self) -> None:
        self.assertFalse(hc.summary_is_identifier_safe(
            ('llama-server', '/Users/yukangzengcmac/model.gguf'), ACCOUNTS))
        self.assertFalse(hc.summary_is_identifier_safe(('llama-server', ACCOUNT), ACCOUNTS))

    def test_account_names_returns_plausible_values_on_this_host(self) -> None:
        names = hc.account_names()
        self.assertIsInstance(names, tuple)
        for name in names:
            self.assertGreaterEqual(len(name), 3)


class PreflightGateTests(unittest.TestCase):
    def test_preflight_raises_and_names_the_offenders(self) -> None:
        text = table(
            ps_line(1, 0, '10:00', 100, '/sbin/launchd'),
            ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD),
        )
        with self.assertRaises(hc.HostNotQuiescent) as caught:
            hc.preflight_host_quiescent(set(), table_text=text, metal_pids=set(),
                                        now=1.0e9, accounts=ACCOUNTS)
        message = str(caught.exception)
        self.assertIn('900', message)
        self.assertIn('llama-server', message)
        self.assertNotIn(ACCOUNT, message)
        self.assertEqual(len(caught.exception.findings), 1)

    def test_preflight_passes_on_a_quiescent_host(self) -> None:
        scan = hc.preflight_host_quiescent(set(), table_text=QUIET_TABLE, metal_pids=set(),
                                           now=1.0e9, accounts=ACCOUNTS)
        self.assertEqual(scan.findings, [])
        self.assertTrue(scan.clean)
        self.assertEqual(scan.scanned, 3)

    def test_preflight_fails_closed_when_the_table_cannot_be_read(self) -> None:
        with self.assertRaises(hc.HostNotQuiescent) as caught:
            hc.preflight_host_quiescent(set(), table_text='', metal_pids=set())
        self.assertIn('ps-unavailable', caught.exception.degraded)

    def test_preflight_fails_closed_on_an_unparsable_line(self) -> None:
        """No finding, but quiescence is NOT proven: an offender could be in that line."""
        text = table(ps_line(1, 0, '10:00', 100, '/sbin/launchd'), 'garbage row')
        with self.assertRaises(hc.HostNotQuiescent) as caught:
            hc.preflight_host_quiescent(set(), table_text=text, metal_pids=set())
        self.assertEqual(caught.exception.findings, [])
        self.assertTrue(caught.exception.degraded)

    def test_exception_is_part_of_the_lab_error_taxonomy(self) -> None:
        import lab_common
        self.assertTrue(issubclass(hc.HostNotQuiescent, lab_common.PreflightError))
        self.assertTrue(issubclass(hc.HostNotQuiescent, lab_common.LabError))


class SoftCheckTests(unittest.TestCase):
    def test_soft_check_returns_findings_instead_of_raising(self) -> None:
        text = ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD)
        scan = hc.soft_host_check(set(), table_text=text, metal_pids=set(), now=1.0e9,
                                  accounts=ACCOUNTS)
        self.assertEqual([f['pid'] for f in scan.findings], [900])

    def test_soft_check_never_raises_on_any_input(self) -> None:
        for text in ('', 'garbage', QUIET_TABLE, '\x00\x01 nonsense \n\n', 'a b c d e'):
            with self.subTest(text=text[:20]):
                scan = hc.soft_host_check(set(), table_text=text, metal_pids=set())
                self.assertIsInstance(scan, hc.ScanResult)

    def test_soft_check_on_the_real_host_returns_a_well_formed_result(self) -> None:
        """Touches the real machine, and therefore asserts only the SHAPE of the result;
        whether a foreign consumer is running right now is not this test's business."""
        scan = hc.soft_host_check(set())
        self.assertIsInstance(scan, hc.ScanResult)
        self.assertIsInstance(scan.findings, list)
        for finding in scan.findings:
            self.assertTrue(hc.summary_is_identifier_safe(finding['command_summary']),
                            finding['command_summary'])


# ---------------------------------------------------------------------------
# C.2: the Metal probe must fail CLOSED, never open
# ---------------------------------------------------------------------------
class MetalProbeFailureTests(unittest.TestCase):
    """PREREG_CHECK C.2.  Before the fix, an absent `lsof`, a permission failure and a
    timeout each returned "no Metal holders", `degraded` stayed empty and the preflight
    PASSED on a host carrying a foreign python GPU job.  Each situation must now name its
    cause and make the gate refuse."""

    PY_TABLE = table(
        ps_line(1, 0, '10:00', 100, '/sbin/launchd'),
        ps_line(700, 1, '00:30:00', 2048, '/venv/bin/python train.py'),
    )

    def _preflight(self, **kwargs):
        return hc.preflight_host_quiescent(set(), table_text=self.PY_TABLE,
                                           now=1.0e9, accounts=ACCOUNTS, **kwargs)

    def test_preflight_raises_when_the_probe_binary_is_absent(self) -> None:
        with fake_lsof(raises=FileNotFoundError('lsof')):
            with self.assertRaises(hc.HostNotQuiescent) as caught:
                self._preflight()
        self.assertIn('lsof-unavailable', caught.exception.degraded)

    def test_preflight_raises_on_an_oserror(self) -> None:
        with fake_lsof(raises=PermissionError('denied')):
            with self.assertRaises(hc.HostNotQuiescent) as caught:
                self._preflight()
        self.assertIn('lsof-unavailable', caught.exception.degraded)

    def test_preflight_raises_on_a_timeout(self) -> None:
        with fake_lsof(raises=subprocess.TimeoutExpired(['lsof'], 30)):
            with self.assertRaises(hc.HostNotQuiescent) as caught:
                self._preflight()
        self.assertIn('lsof-timeout', caught.exception.degraded)

    def test_preflight_raises_on_an_unattributable_non_zero_exit(self) -> None:
        """Non-zero, with the target reported on: nothing explains the failure, so the
        scan is degraded rather than believed."""
        with fake_lsof(FakeCompleted(lsof_output((700, '/dev/null')), returncode=9)):
            with self.assertRaises(hc.HostNotQuiescent) as caught:
                self._preflight()
        self.assertIn('lsof-exit-9', caught.exception.degraded)

    def test_preflight_raises_when_a_target_is_neither_listed_nor_declared_gone(self) -> None:
        """lsof answered for no pid at all.  Silence about a process is not evidence that
        the process holds nothing."""
        with fake_lsof(FakeCompleted('', returncode=0)):
            with self.assertRaises(hc.HostNotQuiescent) as caught:
                self._preflight()
        self.assertEqual(caught.exception.findings, [])
        self.assertIn('lsof-unlisted-1', caught.exception.degraded)

    def test_a_pid_that_exited_between_ps_and_lsof_is_not_a_degradation(self) -> None:
        """`lsof` exits non-zero whenever any requested pid is absent (verified against
        the real binary on the serving host).  A process that has exited cannot be holding
        the accelerator, so that exit must not make the gate cry wolf -- otherwise every
        scan on a busy host refuses and the gate gets bypassed."""
        out = 'lsof: process ID not located: 700\n'
        with fake_lsof(FakeCompleted(out, returncode=1)):
            scan = hc.enumerate_foreign_consumers(set(), table_text=self.PY_TABLE,
                                                  now=1.0e9, accounts=ACCOUNTS)
        self.assertEqual(scan.degraded, [])
        self.assertTrue(scan.clean)

    def test_a_probe_that_had_nothing_to_look_at_does_not_degrade_the_scan(self) -> None:
        """C.2 is conditioned on there being something to check.  With no python process
        and nothing above the floor, an absent lsof leaves nothing unproven."""
        quiet = table(ps_line(1, 0, '10:00', 100, '/sbin/launchd'))
        with fake_lsof(raises=FileNotFoundError('lsof')):
            scan = hc.enumerate_foreign_consumers(set(), table_text=quiet, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual(scan.degraded, [])
        self.assertTrue(scan.clean)

    def test_the_probe_reports_failure_distinguishably_rather_than_an_empty_set(self) -> None:
        """The specific defect C.2 names: the old signature could not tell "nothing holds
        Metal" apart from "the probe did not run"."""
        with fake_lsof(raises=FileNotFoundError('lsof')):
            probe = hc.metal_context_pids([700])
        self.assertFalse(probe.ok)
        self.assertEqual(probe.failure, 'lsof-unavailable')
        self.assertEqual(probe.holders, frozenset())
        with fake_lsof(FakeCompleted(lsof_output((700, '/dev/null')))):
            clean = hc.metal_context_pids([700])
        self.assertTrue(clean.ok)
        self.assertEqual(clean.holders, frozenset())

    def test_an_empty_pid_list_is_a_successful_empty_probe(self) -> None:
        probe = hc.metal_context_pids([])
        self.assertTrue(probe.ok)
        self.assertEqual(probe.holders, frozenset())

    def test_the_probe_parses_field_mode_and_classifies_the_two_marker_families(self) -> None:
        out = lsof_output(
            (700, '/System/Library/Extensions/AGXMetalG16X.bundle/AGXMetalG16X'),
            (701, '/opt/build/bin/libggml-metal.dylib'),
            (702, '/usr/lib/libSystem.B.dylib'))
        with fake_lsof(FakeCompleted(out)):
            probe = hc.metal_context_pids([700, 701, 702])
        self.assertEqual(probe.holders, frozenset({700, 701}))
        self.assertEqual(probe.compute, frozenset({701}))
        self.assertTrue(probe.ok)

    def test_a_command_name_containing_a_space_cannot_hide_a_holder(self) -> None:
        """Field mode is used precisely because the default column form is ambiguous when
        COMMAND contains a space, and an ambiguous line is where an offender would hide."""
        out = 'p701\nn/opt/build/bin/libggml-metal.dylib\n'
        with fake_lsof(FakeCompleted(out)):
            probe = hc.metal_context_pids([701])
        self.assertEqual(probe.compute, frozenset({701}))


# ---------------------------------------------------------------------------
# C.3: a renamed accelerator binary
# ---------------------------------------------------------------------------
class RenamedBinaryTests(unittest.TestCase):
    """PREREG_CHECK C.3 verified that `cp llama-server srv; ./srv -m /x/m.gguf -ngl 99`
    produced `findings: 0 degraded: [] clean: True`.  Option (a) was taken: every
    non-allowlisted process above the resident-size floor is probed, not only python."""

    def test_the_name_list_alone_still_misses_a_renamed_binary(self) -> None:
        """The hole C.3 found is real and is still there in `match_consumer`.  It is
        closed by the second arm, not by the name list, and this test pins that division
        so nobody 'fixes' it by adding `srv` to RUNNER_TOKENS."""
        self.assertIsNone(hc.match_consumer(RENAMED_CMD))

    def test_a_renamed_binary_above_the_floor_holding_metal_compute_is_caught(self) -> None:
        text = table(ps_line(1, 0, '10:00', 100, '/sbin/launchd'),
                     ps_line(901, 1, '08:31:12', BIG_KB, RENAMED_CMD))
        out = lsof_output((901, '/opt/priv/libggml-metal.dylib'))
        with fake_lsof(FakeCompleted(out)):
            scan = hc.enumerate_foreign_consumers(set(), table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual([f['pid'] for f in scan.findings], [901])
        self.assertEqual(scan.findings[0]['detector'], hc.METAL_PROCESS_LABEL)
        self.assertFalse(scan.clean)
        with self.assertRaises(hc.HostNotQuiescent):
            with fake_lsof(FakeCompleted(out)):
                hc.preflight_host_quiescent(set(), table_text=text, now=1.0e9,
                                            accounts=ACCOUNTS)

    def test_a_window_drawing_application_is_not_reported(self) -> None:
        """Measured on the serving host: ordinary desktop applications map AGXMetal while
        doing no accelerator work.  Reporting them would make the gate cry wolf, and a
        gate an operator learns to bypass protects nothing."""
        text = ps_line(902, 1, '01:00:00', BIG_KB, '/Applications/Some.app/Contents/MacOS/Some')
        out = lsof_output((902, '/System/Library/Extensions/AGXMetalG16X.bundle/AGXMetalG16X'))
        with fake_lsof(FakeCompleted(out)):
            scan = hc.enumerate_foreign_consumers(set(), table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual(scan.findings, [])
        self.assertTrue(scan.clean)

    def test_a_python_interpreter_is_still_reported_on_any_metal_marker(self) -> None:
        """The python arm keeps the wider predicate: a python process on a serving host is
        not drawing a window, so a display-class marker is already an anomaly."""
        text = ps_line(700, 1, '00:30:00', SMALL_KB, '/venv/bin/python train.py')
        out = lsof_output((700, '/System/Library/Extensions/AGXMetalG16X.bundle/AGXMetalG16X'))
        with fake_lsof(FakeCompleted(out)):
            scan = hc.enumerate_foreign_consumers(set(), table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual([f['detector'] for f in scan.findings], [hc.METAL_PYTHON_LABEL])

    def test_the_documented_blind_spot_below_the_floor_is_real_and_stated(self) -> None:
        """Option (a) is not complete, and the module says so rather than letting a reader
        believe 'no other GPU job' is enforced.  A renamed binary UNDER the floor is not
        probed at all and the scan reports clean: that is the limitation, asserted here so
        that it can never be an unpleasant surprise."""
        text = ps_line(903, 1, '08:31:12', SMALL_KB, RENAMED_CMD)
        with fake_lsof(FakeCompleted('')):
            scan = hc.enumerate_foreign_consumers(set(), table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual(scan.findings, [])
        self.assertTrue(scan.clean, 'the blind spot is below the floor, not a degradation')
        doc = hc.__doc__ or ''
        self.assertIn('PROBE_RSS_FLOOR_BYTES', doc)
        self.assertIn('does NOT detect', doc)

    def test_the_probe_budget_binding_degrades_the_scan_instead_of_under_scanning(self) -> None:
        rows = [ps_line(1000 + i, 1, '01:00:00', BIG_KB, f'/opt/x/worker{i}')
                for i in range(6)]
        with fake_lsof(FakeCompleted('')):
            scan = hc.enumerate_foreign_consumers(set(), table_text=table(*rows),
                                                  now=1.0e9, accounts=ACCOUNTS,
                                                  max_probe_pids=3)
        self.assertFalse(scan.clean)
        self.assertIn('probe-budget-6', scan.degraded)
        with self.assertRaises(hc.HostNotQuiescent):
            with fake_lsof(FakeCompleted('')):
                hc.preflight_host_quiescent(set(), table_text=table(*rows), now=1.0e9,
                                            accounts=ACCOUNTS, max_probe_pids=3)

    def test_our_own_heavy_processes_are_still_allowlisted(self) -> None:
        text = table(ps_line(500, 1, '00:10:00', 1000, '/bin/zsh -c run'),
                     ps_line(501, 500, '00:09:00', BIG_KB, '/opt/priv/srv -ngl 99'))
        out = lsof_output((501, '/opt/priv/libggml-metal.dylib'))
        with fake_lsof(FakeCompleted(out)):
            scan = hc.enumerate_foreign_consumers({500}, table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)
        self.assertEqual(scan.findings, [])


# ---------------------------------------------------------------------------
# C.4: the gate is wired to the trial, and its records are chain events
# ---------------------------------------------------------------------------
class ChainRecordTests(unittest.TestCase):
    """The findings must be expressible in the event schema's own string discipline: no
    free text, no untokenized path, no URL, no commit id."""

    def _scan(self) -> hc.ScanResult:
        text = table(ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD),
                     ps_line(1, 0, '10:00', 100, '/sbin/launchd'),
                     'a line that does not parse')
        with fake_lsof(FakeCompleted('')):
            return hc.enumerate_foreign_consumers(set(), table_text=text, now=1.0e9,
                                                  accounts=ACCOUNTS)

    def test_the_detector_vocabulary_matches_the_schema_exactly(self) -> None:
        spec = lab_eventlog.EVENT_SCHEMA['foreign_load_detected']
        self.assertEqual(sorted(hc.DETECTOR_LABELS),
                         sorted(spec['findings'].item.fields['detector'].enum))

    def test_the_degraded_vocabulary_matches_the_schema_exactly(self) -> None:
        spec = lab_eventlog.EVENT_SCHEMA['foreign_load_detected']
        self.assertEqual(sorted(hc.DEGRADED_CAUSES),
                         sorted(spec['degraded'].item.fields['cause'].enum))

    def test_every_marker_this_module_can_emit_folds_into_the_vocabulary(self) -> None:
        markers = ['ps-unavailable', 'short-line-fields-3', 'unparsed-fields-pid-91',
                   'unparsed-fields-pid-nan', 'lsof-unavailable', 'lsof-timeout',
                   'lsof-failed', 'lsof-exit-9', 'lsof-unlisted-4', 'probe-budget-200',
                   'soft-check-error-RuntimeError', 'a-marker-nobody-has-written-yet']
        rows = hc.degraded_causes(markers)
        for row in rows:
            self.assertIn(row['cause'], hc.DEGRADED_CAUSES, row)
        self.assertEqual(sum(r['count'] for r in rows), len(markers))
        # an unknown marker is folded, never dropped: it is still a failure to prove
        # quiescence, and dropping it would be the fail-open C.2 forbids
        self.assertIn('scan_error', [r['cause'] for r in rows])

    def test_both_event_bodies_validate_against_the_schema(self) -> None:
        scan = self._scan()
        self.assertTrue(scan.findings)
        self.assertTrue(scan.degraded)
        body = dict(hc.chain_body(scan), point='quiescent')
        lab_eventlog.validate_event('foreign_load_detected', body)
        lab_eventlog.validate_event('host_quiescence_refused',
                                    dict(body, trial='T4', point='trial_start'))

    def test_a_clean_scan_also_validates_and_records_itself_positively(self) -> None:
        scan = hc.enumerate_foreign_consumers(set(), table_text=QUIET_TABLE,
                                              metal_pids=set(), now=1.0e9,
                                              accounts=ACCOUNTS)
        body = dict(hc.chain_body(scan), point='trial_start')
        lab_eventlog.validate_event('foreign_load_detected', body)
        self.assertTrue(body['clean'])
        self.assertEqual(body['findings'], [])

    def test_the_free_token_summary_never_reaches_the_chain(self) -> None:
        """PREREG_CHECK C.6: a bare literal that is neither a path nor an address survives
        the tokenizer verbatim, so a foreign project's module name could ride into an
        immutable chain inside `command_summary`.  The chain record carries its digest."""
        scan = self._scan()
        record = hc.chain_finding(scan.findings[0])
        self.assertNotIn('command_summary', record)
        self.assertEqual(len(record['summary_sha256']), 64)
        self.assertEqual(
            record['summary_sha256'],
            lab_common.sha256_text(' '.join(scan.findings[0]['command_summary'])))

    def test_the_verifier_knows_both_checks(self) -> None:
        for check in ('host.record', 'host.quiescence'):
            self.assertIn(check, lab_verify_log.CHECK_SEVERITY)
            self.assertTrue(lab_verify_log.plumbing_allows(check))
        self.assertEqual(lab_verify_log.CHECK_SEVERITY['host.record'], 'FAIL')

    def test_the_verifier_catches_a_record_that_lies_about_being_clean(self) -> None:
        scan = self._scan()
        body = dict(hc.chain_body(scan), point='quiescent')
        self.assertFalse(body['clean'])
        events = [{'seq': 7, 'type': 'foreign_load_detected', 'body': dict(body,
                                                                          clean=True)}]
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_host_scans(col, events, 'foreign_load_detected')
        fails = [f for f in col.findings if f.check == 'host.record']
        self.assertEqual(len(fails), 1, [f.detail for f in col.findings])
        self.assertEqual(fails[0].severity, 'FAIL')

    def test_the_verifier_reports_a_foreign_load_seen_during_a_trial(self) -> None:
        scan = self._scan()
        events = [{'seq': 7, 'type': 'foreign_load_detected',
                   'body': dict(hc.chain_body(scan), point='quiescent')}]
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_host_scans(col, events, 'foreign_load_detected')
        checks = {f.check for f in col.findings}
        self.assertEqual(checks, {'host.quiescence'})
        self.assertTrue(all(f.severity == 'DEFECT' for f in col.findings))

    def test_a_clean_record_produces_no_finding_at_all(self) -> None:
        scan = hc.enumerate_foreign_consumers(set(), table_text=QUIET_TABLE,
                                              metal_pids=set(), now=1.0e9,
                                              accounts=ACCOUNTS)
        events = [{'seq': 3, 'type': 'foreign_load_detected',
                   'body': dict(hc.chain_body(scan), point='trial_start')}]
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_host_scans(col, events, 'foreign_load_detected')
        self.assertEqual(col.findings, [])
        self.assertEqual(col.seen, {'host.record', 'host.quiescence'})


class OrchestratorWiringTests(unittest.TestCase):
    """PREREG_CHECK C.4: before the fix, nothing called either entry point, so the gate
    'would not have blocked the trial described in 5776877, because nothing would have run
    it'.  These tests run the real trial-start path."""

    def test_a_simulated_invocation_is_not_gated_and_a_real_one_is(self) -> None:
        import lab_orchestrator as orch
        self.assertFalse(orch.host_scan_is_required({'_runtime': {'sim': True}}))
        self.assertTrue(orch.host_scan_is_required({'_runtime': {'sim': False}}))
        self.assertTrue(orch.host_scan_is_required({}),
                        'a configuration that says nothing must be gated, not exempt')
        self.assertIsNone(orch.host_quiescence_gate(
            type('C', (), {'cfg': {'_runtime': {'sim': True}}})()))

    def test_there_is_no_configuration_key_that_disables_the_gate(self) -> None:
        """A gate an operator can switch off for a real run is a gate that will be off on
        the night it matters.  The only exemption is a simulated invocation."""
        source = (HERE / 'lab_orchestrator.py').read_text('utf-8')
        body = source.split('def host_scan_is_required')[1].split('\ndef ')[0]
        self.assertIn("runtime(cfg).get('sim')", body)
        for knob in ('enabled', 'skip_host_check', 'host_quiescence_enabled'):
            self.assertNotIn(knob, body, f'host_scan_is_required reads a {knob!r} knob')

    def test_the_gate_allowlists_this_process(self) -> None:
        import os
        import lab_orchestrator as orch
        self.assertIn(os.getpid(), orch.own_harness_pids())

    def test_a_non_quiescent_host_refuses_to_start_the_trial(self) -> None:
        """The whole point of C.4, end to end: a foreign consumer present at trial start
        must abort the run, leave the trial chain unopened, and name the offender in the
        program chain."""
        from tests_lab_e2e import Tree           # the shared mock-freeze fixture
        import lab_orchestrator as orch

        offenders = hc.enumerate_foreign_consumers(
            set(), table_text=ps_line(900, 1, '08:31:12', 7041312, LLAMA_CMD),
            metal_pids=set(), now=1.0e9, accounts=ACCOUNTS).findings

        def refuse(own_pids=None, **kwargs):
            raise hc.HostNotQuiescent(
                f'host is not quiescent: {hc.describe_findings(offenders)}',
                findings=offenders, degraded=())

        tree = Tree(pairs=2, anchor=False)
        real = hc.preflight_host_quiescent
        try:
            hc.preflight_host_quiescent = refuse
            cfg = tree._cfg()
            cfg['_runtime']['sim'] = False        # a gated invocation
            ctx = orch.make_context(tree.trial, cfg, results_root=tree.results,
                                    work_root=tree.work, inv=uuid.uuid4().hex)
            self.assertEqual(orch.run_trial(ctx, resume=False), 'aborted')

            self.assertEqual(
                lab_eventlog.segment_paths(tree.results / tree.trial / 'events'), [],
                'the trial chain was opened on a non-quiescent host')

            program = lab_eventlog.read_chain(tree.results / '_program' / 'events',
                                              '_program', tree.bundle_sha)
            refusals = [e for e in program.events
                        if e['type'] == 'host_quiescence_refused']
            self.assertEqual(len(refusals), 1, [e['type'] for e in program.events])
            body = refusals[0]['body']
            self.assertFalse(body['clean'])
            self.assertEqual([f['detector'] for f in body['findings']], ['llama-server'])
            self.assertEqual(body['point'], 'trial_start')
            self.assertEqual(body['trial'], tree.trial)
            blob = lab_common.canonical_json(body)
            self.assertNotIn(ACCOUNT, blob)
            self.assertNotIn('/Users/', blob)

            checks = [e['body']['checks_failed'] for e in program.events
                      if e['type'] == 'preflight_refused']
            self.assertEqual(checks, [['host_not_quiescent']])

            # The verifier reads the new event without complaint.  (This fixture's program
            # chain has no `program_opened` at seq 0, so `program.order` fails here for a
            # reason that predates the gate and is not what this test is about.)
            report = lab_verify_log.verify_program(tree.bundle_sha,
                                                   results_root=tree.results)
            self.assertEqual([f.check for f in report.findings
                              if f.check.startswith('host.') and f.severity == 'FAIL'],
                             [])
            rows = [f for f in report.findings if f.check == 'host.quiescence']
            self.assertEqual([f.severity for f in rows], ['INFO'],
                             'the gate refusing a trial is the gate working')
        finally:
            hc.preflight_host_quiescent = real
            shutil.rmtree(tree.root, ignore_errors=True)

    def test_the_soft_check_writes_a_record_at_every_quiescent_point(self) -> None:
        """The observing half: `World.host_scan` emits at the trial-start and quiescent
        scrape points and nowhere else, and never raises."""
        import lab_orchestrator as orch

        class FakeWorld:
            cfg = {'_runtime': {'sim': False}}
            server_pids: dict = {}
            attempts: dict = {}
            findings: list = []

            def __init__(self) -> None:
                self.appended: list = []
                self.ctx = type('C', (), {'cfg': dict(FakeWorld.cfg)})()

            def append(self, etype, body, durable=False):
                lab_eventlog.validate_event(etype, body)
                self.appended.append((etype, body))

        world = FakeWorld()
        real = hc.soft_host_check
        try:
            hc.soft_host_check = lambda own_pids=None, **kw: hc.ScanResult(
                findings=[], degraded=['lsof-timeout'])
            for point in ('trial_start', 'pair_boundary', 'quiescent', 'trial_end',
                          'restart'):
                orch.World.host_scan(world, point)
        finally:
            hc.soft_host_check = real
        self.assertEqual([p for _, p in [(e, b['point']) for e, b in world.appended]],
                         ['trial_start', 'quiescent'])
        for etype, body in world.appended:
            self.assertEqual(etype, 'foreign_load_detected')
            self.assertFalse(body['clean'])
            self.assertEqual(body['degraded'], [{'cause': 'lsof_timeout', 'count': 1}])

    def test_a_simulated_invocation_writes_no_host_record(self) -> None:
        import lab_orchestrator as orch

        class FakeWorld:
            server_pids: dict = {}
            attempts: dict = {}
            findings: list = []

            def __init__(self) -> None:
                self.appended: list = []
                self.ctx = type('C', (), {'cfg': {'_runtime': {'sim': True}}})()

            def append(self, etype, body, durable=False):        # pragma: no cover
                self.appended.append((etype, body))

        world = FakeWorld()
        orch.World.host_scan(world, 'quiescent')
        self.assertEqual(world.appended, [])


# ---------------------------------------------------------------------------
# this module observes; it must not be able to act
# ---------------------------------------------------------------------------
BANNED_NAMES = frozenset({
    'kill', 'killpg', 'killall', 'pkill', 'terminate', 'send_signal', 'signal',
    'raise_signal', 'pthread_kill', 'setpriority', 'renice', 'nice', 'taskpolicy',
    'system', 'popen', 'abort', 'suspend', 'resume', 'SIGKILL', 'SIGTERM', 'SIGSTOP',
    'SIGINT', 'SIGHUP',
})
ALLOWED_PROGRAMS = frozenset({'ps', 'lsof'})


def module_source() -> str:
    return MODULE_PATH.read_text('utf-8')


def code_identifiers() -> set[str]:
    """Every NAME token in the module with comments and string literals removed, so that
    prose describing what the module refuses to do cannot satisfy or trip this check."""
    out: set[str] = set()
    for tok in tokenize.generate_tokens(io.StringIO(module_source()).readline):
        if tok.type == tokenize.NAME:
            out.add(tok.string)
    return out


class NoSignalSendingTests(unittest.TestCase):
    def test_no_banned_identifier_appears_in_the_modules_code(self) -> None:
        offenders = sorted(code_identifiers() & BANNED_NAMES)
        self.assertEqual(offenders, [], f'lab_hostcheck names {offenders}')

    def test_no_banned_call_or_attribute_in_the_syntax_tree(self) -> None:
        tree = ast.parse(module_source(), filename=str(MODULE_PATH))
        bad: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in BANNED_NAMES:
                bad.append(node.attr)
            elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
                bad.append(node.id)
        self.assertEqual(sorted(set(bad)), [])

    def test_the_signal_module_is_never_imported(self) -> None:
        tree = ast.parse(module_source(), filename=str(MODULE_PATH))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0])
        self.assertNotIn('signal', imported)
        self.assertNotIn('psutil', imported)

    def test_the_only_external_programs_named_are_ps_and_lsof(self) -> None:
        """Resolve the first argument of every subprocess call to its literal argv and
        check the program name, so the module cannot grow a third external command."""
        tree = ast.parse(module_source(), filename=str(MODULE_PATH))
        literals: dict[str, list[ast.expr]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        literals.setdefault(target.id, []).append(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    literals.setdefault(node.target.id, []).append(node.value)

        def heads(node: ast.expr, depth: int = 0) -> list[str]:
            """The possible argv[0] values of an expression."""
            if depth > 4:
                return ['<unresolved>']
            if isinstance(node, (ast.List, ast.Tuple)):
                if not node.elts:
                    return ['<empty>']
                first = node.elts[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    return [first.value]
                return ['<unresolved>']
            if isinstance(node, ast.Name):
                out: list[str] = []
                for value in literals.get(node.id, []):
                    out.extend(heads(value, depth + 1))
                return out or ['<unresolved>']
            if isinstance(node, ast.Call):          # list(PS_ARGV) / tuple(...)
                if node.args:
                    return heads(node.args[0], depth + 1)
            return ['<unresolved>']

        calls = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name) and func.value.id == 'subprocess'):
                continue
            calls += 1
            self.assertTrue(node.args, 'a subprocess call with no argv')
            for head in heads(node.args[0]):
                self.assertIn(head, ALLOWED_PROGRAMS,
                              f'lab_hostcheck runs {head!r}, which is not ps or lsof')
        self.assertGreaterEqual(calls, 2, 'expected the ps and the lsof call')


if __name__ == '__main__':
    unittest.main()
