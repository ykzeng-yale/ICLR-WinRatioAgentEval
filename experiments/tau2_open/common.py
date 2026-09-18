"""Shared paths, configuration, hashing and provenance helpers for the tau2 open-model stream.

Nothing here touches the network or a model server. The frozen configuration
lives in config.json next to this file; its sha256 over canonical JSON is the
``config_hash`` recorded in the design and in every episode.
"""
from __future__ import annotations
import hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
RESULTS_DIR = ROOT / 'results' / 'tau2_open'
CONFIG_PATH = HERE / 'config.json'
ARMS = ('A', 'B')
HARNESS_FILES = ('common.py', 'design.py', 'run_tau2_open.py', 'build_episodes.py', 'analysis.py', 'tests_tau2_open.py',
                 'config.json', 'protocol.md', 'README.md')
EPISODE_COLUMNS = ['arm', 'agent_model', 'user_model', 'task_id', 'trial', 'tau2_seed', 'arrival_index', 'pair_index', 'position_in_pair',
                   'orientation', 'pass', 'block', 'success', 'reward', 'agent_tokens_completion', 'agent_tokens_prompt', 'n_agent_llm_calls',
                   'n_assistant_tool_calls', 'n_assistant_messages', 'n_user_messages', 'n_tool_messages', 'n_messages', 'duration',
                   'agent_generation_seconds', 'termination_reason', 'max_steps_hit', 'error', 'tokens_source', 'tokens_estimated_calls',
                   'served_models', 'simulation_id', 'start_time', 'end_time', 'source_file', 'config_hash']


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode('utf-8'))


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_config(path=None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    cfg = json.loads(p.read_text())
    cfg['_config_path'] = str(p)
    cfg['_config_hash'] = config_hash(cfg)
    return cfg


def config_hash(cfg: dict) -> str:
    clean = {k: v for k, v in cfg.items() if not k.startswith('_')}
    return sha256_text(canonical_json(clean))


def harness_git_hash() -> str:
    """Commit id of the checked-out harness, read from .git files (no git command); 'unknown' if unreadable."""
    try:
        head = (ROOT / '.git' / 'HEAD').read_text().strip()
        if head.startswith('ref:'):
            ref = head.split(' ', 1)[1].strip()
            ref_path = ROOT / '.git' / ref
            if ref_path.exists():
                return ref_path.read_text().strip()
            packed = ROOT / '.git' / 'packed-refs'
            if packed.exists():
                for line in packed.read_text().splitlines():
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == ref:
                        return parts[0]
            return 'unknown(ref=%s)' % ref
        return head
    except OSError:
        return 'unknown'


def harness_hashes() -> dict:
    return {name: sha256_file(HERE / name) for name in HARNESS_FILES if (HERE / name).exists()}


def hardware_info() -> dict:
    info = dict(platform=platform.platform(), machine=platform.machine(), python=sys.version.split()[0])
    if sys.platform == 'darwin':
        for key, label in (('machdep.cpu.brand_string', 'cpu'), ('hw.memsize', 'memory_bytes'), ('hw.ncpu', 'n_cpu')):
            try:
                info[label] = subprocess.run(['sysctl', '-n', key], capture_output=True, text=True, timeout=5).stdout.strip()
            except Exception:  # pragma: no cover
                info[label] = 'unknown'
        try:
            info['os_version'] = subprocess.run(['sw_vers', '-productVersion'], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:  # pragma: no cover
            pass
    return info


def package_versions() -> dict:
    out = {}
    for mod in ('numpy', 'scipy', 'pandas', 'requests'):
        try:
            out[mod] = getattr(__import__(mod), '__version__', 'unknown')
        except Exception:
            out[mod] = None
    return out


def now_ts() -> float:
    return time.time()


def iso(ts: float) -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(ts)) + 'Z'


def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def append_jsonl(path, row):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path)))


def gguf_record(model_cfg: dict, verify_hash: bool = True) -> dict:
    """Locate the GGUF file(s) of one model and compare size and sha256 with the frozen expectations.

    ok is False when a file is missing or a size/sha256 differs; the runner refuses to start in that case.
    """
    files = []
    ok = True
    for f in model_cfg['gguf_files']:
        p = expand(f['path'])
        rec = dict(path=str(p), expected_bytes=f['bytes'], expected_sha256=f['sha256'], exists=p.exists())
        if p.exists():
            real = p.resolve()
            rec['bytes'] = real.stat().st_size
            rec['sha256'] = sha256_file(real) if verify_hash else None
            rec['ok'] = rec['bytes'] == f['bytes'] and (not verify_hash or rec['sha256'] == f['sha256'])
        else:
            rec['ok'] = False
        ok &= rec['ok']
        files.append(rec)
    return dict(model=model_cfg['hf_repo'], revision=model_cfg['hf_revision'], alias=model_cfg['alias'], files=files, ok=ok,
                total_bytes=sum(f.get('bytes', 0) for f in files), hashed_at=iso(now_ts()), hash_verified=verify_hash)


def process_rss_bytes(pattern: str) -> list:
    try:
        out = subprocess.run(['ps', '-axo', 'pid=,rss=,command='], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and pattern in parts[2] and 'ps -axo' not in parts[2]:
            rows.append(dict(pid=int(parts[0]), rss_bytes=int(parts[1]) * 1024, command=parts[2][:300]))
    return rows
