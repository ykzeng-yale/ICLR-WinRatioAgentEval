"""Shared paths, configuration, hashing and provenance helpers for the local stream.

Nothing here touches the network or the model. The frozen configuration lives
in config.json next to this file; its sha256 (over canonical JSON) is the
``config_hash`` recorded on every episode.
"""
from __future__ import annotations
import hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
DATA_DIR = ROOT / 'work' / 'local_stream' / 'data'        # git-ignored (work/)
RESULTS_DIR = ROOT / 'results' / 'local_stream'
CONFIG_PATH = HERE / 'config.json'
VARIANTS = ('single_shot', 'self_test_repair')
VARIANT_LETTER = {'single_shot': 'A', 'self_test_repair': 'B'}
HARNESS_FILES = ('common.py', 'data.py', 'sandbox.py', 'verify.py', 'agent.py', 'design.py', 'run_stream.py', 'analysis.py', 'timing_pilot.py',
                 'tests_local_stream.py', 'config.json', 'protocol.md', 'README.md')


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
    """Commit id of the checked-out harness, read from .git files (no git command).

    Returns 'unknown' when the repository metadata cannot be read. This is a
    provenance placeholder: the authoritative revision is the commit that
    contains the frozen design and results.
    """
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
    out = {}
    for name in HARNESS_FILES:
        p = HERE / name
        if p.exists():
            out[name] = sha256_file(p)
    return out


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
    for mod in ('numpy', 'scipy', 'pandas', 'requests', 'mlx', 'mlx_lm', 'transformers'):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, '__version__', 'unknown')
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
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn last line from an interrupted run is ignored; the
                # episode is re-run on resume because its key is not complete.
                continue
    return rows


def append_jsonl(path, row):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def hf_cache_dir() -> Path:
    """huggingface hub cache root (HF_HUB_CACHE, else HF_HOME/hub, else ~/.cache/huggingface/hub)."""
    if os.environ.get('HF_HUB_CACHE'):
        return Path(os.environ['HF_HUB_CACHE'])
    if os.environ.get('HF_HOME'):
        return Path(os.environ['HF_HOME']) / 'hub'
    return Path.home() / '.cache' / 'huggingface' / 'hub'


def hf_snapshot_record(model: str, expected_revision: str, cache_dir=None) -> dict:
    """Locate the cached snapshot of ``model`` and hash every file (following symlinks).

    Returns dict(ok, revision, expected_revision, path, refs_main, files=[{name, bytes, sha256}], total_bytes,
    snapshots_present, error). ok is False when the expected revision is not in the cache;
    the caller refuses to run in that case.
    """
    root = Path(cache_dir) if cache_dir else hf_cache_dir()
    repo = root / ('models--' + model.replace('/', '--'))
    snaps = repo / 'snapshots'
    present = sorted(p.name for p in snaps.iterdir() if p.is_dir()) if snaps.exists() else []
    refs_main = None
    try:
        refs_main = (repo / 'refs' / 'main').read_text().strip()
    except OSError:
        pass
    rec = dict(model=model, expected_revision=expected_revision, cache_dir=str(root), repo_dir=str(repo), snapshots_present=present,
               refs_main=refs_main, revision=None, path=None, files=[], total_bytes=0, ok=False, error=None, hashed_at=iso(now_ts()))
    if expected_revision not in present:
        rec['error'] = 'expected revision %s not in cache (present: %s)' % (expected_revision, present or 'none')
        return rec
    snap = snaps / expected_revision
    files = []
    for p in sorted(snap.rglob('*')):
        if p.is_file() or (p.is_symlink() and p.resolve().is_file()):
            real = p.resolve()
            files.append(dict(name=str(p.relative_to(snap)), bytes=real.stat().st_size, sha256=sha256_file(real)))
    rec.update(revision=expected_revision, path=str(snap), files=files, total_bytes=sum(f['bytes'] for f in files), ok=bool(files))
    if not files:
        rec['error'] = 'snapshot directory is empty'
    if refs_main and refs_main != expected_revision:
        rec['warning'] = 'refs/main points to %s, not the expected revision' % refs_main
    return rec


def process_rss_bytes(pattern: str) -> list:
    """RSS (bytes) of processes whose command line contains ``pattern`` (via ps; macOS/Linux)."""
    try:
        out = subprocess.run(['ps', '-axo', 'pid=,rss=,command='], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and pattern in parts[2] and 'ps -axo' not in parts[2]:
            rows.append(dict(pid=int(parts[0]), rss_bytes=int(parts[1]) * 1024, command=parts[2][:200]))
    return rows
