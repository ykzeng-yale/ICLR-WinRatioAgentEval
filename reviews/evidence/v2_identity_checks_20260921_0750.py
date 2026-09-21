"""Bounded identity counterexamples; pass an immutable owner export. No simulation."""
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
val = root/'experiments/live_ab_validation'
sys.path.insert(0, str(val))
import videntity
sources = {m: (val/(m+'.py')).read_text() for m in videntity.TIMED_MODULES}
original = videntity.timed_core_identity(sources)
changed = dict(sources)
needle = 'OPERATIONAL_EPS: float = 1e-9'
assert needle in changed['vgen']
changed['vgen'] = changed['vgen'].replace(needle, 'OPERATIONAL_EPS: float = 1.0')
mutant = videntity.timed_core_identity(changed)
missing = videntity.timed_core_identity(sources, (('vrun','evaluate_trial'), ('vrun','MISSING_ENTRY')))
print(json.dumps({
 'source_commit': '5336f8b0124b9aef0133e7facef268b8608b1e8c',
 'executable_epsilon_mutation_leaves_identity_unchanged': original['timed_core_sha256'] == mutant['timed_core_sha256'],
 'partly_missing_requested_entry_not_rejected': missing['members'] > 0,
 'orchestrator_included': any(m.startswith('vpanel.') for m in original['per_member_sha256']),
 'reference_included': any(m.startswith('eb_reference.') for m in original['per_member_sha256']),
 'counterexample_forward_margin': (1-.05)*11-10,
 'forward_fires_eps_1e9': (1-.05)*11 > 10+1e-9,
 'forward_fires_eps_1': (1-.05)*11 > 10+1,
}, indent=2))
