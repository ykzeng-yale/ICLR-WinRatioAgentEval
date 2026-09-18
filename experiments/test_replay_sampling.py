"""Acceptance checks for issue #6: unequal-replicate stratified sampling and cross-process determinism."""
import subprocess, sys, os, hashlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments'))
from run_replay import stream, DESIGN_ID

def tiny_unequal():
    PA = {('d', 't1'): np.ones((1, 4)), ('d', 't2'): np.full((3, 4), 2.0)}
    PB = {('d', 't1'): np.full((1, 4), 3.0), ('d', 't2'): np.full((3, 4), 4.0)}
    rng = np.random.default_rng(5)
    for design in DESIGN_ID:
        A, B = stream(rng, PA, PB, 50, design)
        assert A.shape == (50, 4) and B.shape == (50, 4)
    print('tiny unequal-replicate sampling ok for', list(DESIGN_ID))

def digest(design, hashseed):
    code = f"import sys,hashlib,numpy as np; sys.path.insert(0,'{ROOT}/experiments'); from run_replay import stream, DESIGN_ID; " \
           f"PA={{('d',t): np.arange(16.).reshape(4,4)+t for t in range(6)}}; PB={{('d',t): np.arange(16.).reshape(4,4)*2+t for t in range(6)}}; " \
           f"rng=np.random.default_rng([0, DESIGN_ID['{design}']]); A,B=stream(rng,PA,PB,300,'{design}'); print(hashlib.sha256(np.concatenate([A,B]).tobytes()).hexdigest())"
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
    return subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env).stdout.strip()

def determinism():
    for design in DESIGN_ID:
        h = {digest(design, s) for s in (0, 1, 12345)}
        assert len(h) == 1 and len(next(iter(h))) == 64, (design, h)
    print('cross-process determinism ok under PYTHONHASHSEED 0/1/12345')

if __name__ == '__main__':
    tiny_unequal(); determinism()
