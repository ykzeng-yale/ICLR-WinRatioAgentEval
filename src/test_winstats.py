"""Scientific invariant tests, including boundary rules and exact oracle means."""
import sys
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from winstats import Tier, compare, betting_log_e_ternary, normal_mixture_radius
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
from run_simulations import exact_targets, generate, SCENARIOS


def main():
    rng=np.random.default_rng(903)
    tiers=[Tier('success'),Tier('cost',False,relative_tolerance=.05)]
    a=np.column_stack([rng.integers(0,2,1000),rng.lognormal(size=1000)])
    b=np.column_stack([rng.integers(0,2,1000),rng.lognormal(size=1000)])
    h,k=compare(a,b,tiers); rev,kr=compare(b,a,tiers)
    assert np.array_equal(h,-rev) and np.array_equal(k,kr)
    assert not compare(a,a,tiers)[0].any()
    assert compare([[1,10]],[[1,9.5]],tiers)[0][0]==0
    assert compare([[1,10]],[[0,1]],tiers)[0][0]==1
    try: compare([[np.nan,1]],[[1,1]],tiers)
    except ValueError: pass
    else: raise AssertionError('Missing observations silently accepted')
    for value in [-.1,np.nan,np.inf]:
        try: Tier('invalid',absolute_tolerance=value)
        except ValueError: pass
        else: raise AssertionError('Invalid tolerance silently accepted')
    # Check mixture formula against product over the literal observations.
    z=np.array([1,0,-1,1,1,0,-1]); c=-.03
    lam=np.geomspace(1e-4,.99/(1+c),40)
    direct=logsumexp(np.log1p(lam[:,None]*(z[None,:]-c)).sum(axis=1))-np.log(40)
    assert np.allclose(direct,betting_log_e_ternary((z>0).sum(),(z<0).sum(),len(z),c))
    assert normal_mixture_radius(1000)>normal_mixture_radius(10000)
    # Independent analytic truth check, tolerance is six Monte Carlo SEs.
    for scenario,params in SCENARIOS.items():
        z=generate(rng,(400000,),params)[0]
        truth=exact_targets(params)[0]
        assert abs(z.mean()-truth)<6*z.std()/np.sqrt(len(z)),(scenario,z.mean(),truth)
    print('Scientific invariant checks passed (six analytic truth checks).')

if __name__=='__main__': main()
