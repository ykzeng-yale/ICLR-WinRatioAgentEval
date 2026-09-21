# Usage: python SCRIPT EXACT_EXPORT
import json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path[:0]=[str(root/'experiments/live_ab_validation'),str(root/'src')]
import vconformance as c
r=c.run()
r.pop('elapsed_seconds',None)
print(json.dumps({'threshold':r['threshold_tables'],'states':r['vpolicy_agreement']['pair_states_compared']},indent=2))
