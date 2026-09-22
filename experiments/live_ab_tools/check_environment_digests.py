"""Offline checker for the environment digests. Verifies, never re-measures.

Root, 2026-09-21 21:17: "Add a tiny offline checker that verifies both component
and whole hashes from the saved bytes, plus equality of their package multisets.
... No fresh host measurement needed."

It reads only deposited bytes. It does NOT enumerate the host, so a passing run
proves SAVED-BYTE CONSISTENCY -- not installed-host identity, not wheel or build
provenance, and not that the current host is unchanged.

It lives outside experiments/live_ab/ because it is descriptive tooling: that
directory is globbed into HARNESS_FILES and feeds a freeze-bundle pin.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

#: This file re-derives its digests with `hashlib` instead of calling
#: `lab_common.sha256_file`, and that is DELIBERATE: root asked for a checker that
#: verifies the deposited bytes, and hashing them with the producer's own helper
#: would not be a check. Declared here rather than exempted in the auditor, so the
#: exemption is a visible commitment in the file it applies to. `tool_audit.py`
#: treats an undeclared file as a reporter, the stricter rule.
AUDIT_ROLE = 'independent_verifier'

REPO = Path(__file__).resolve().parents[2]
R = REPO / 'results' / 'live_ab'
CONFIG = REPO / 'experiments' / 'live_ab' / 'config.json'

WHOLE = '842a7a19d738604fbe665231a593a11f12cc02abfe9b1dc4034bc3817a9081ac'
COMPONENT = '08c1de5ae33d1fdd45424be7956c88471b8a8e47971608ac866aa6cb5247b053'
LEGACY_TXT = '40a9d196154fe5416a319898891aa586c8c0b32dee8e8f85a095986d589672de'


def _multiset(text: str) -> "dict[str, int]":
    out: dict[str, int] = {}
    for line in text.splitlines():
        if line.strip():
            out[line.strip()] = out.get(line.strip(), 0) + 1
    return out


def check() -> dict:
    whole_bytes = (R / 'environment_lock_preimage.json').read_bytes()
    comp_bytes = (R / 'environment_lock_package_component.txt').read_bytes()
    legacy_bytes = (R / 'environment_lock.txt').read_bytes()

    whole_digest = hashlib.sha256(whole_bytes).hexdigest()
    # THE KEY BELOW USED TO BE `whole_hash_matches_config` AND NEVER OPENED
    # config.json. It compared the deposited bytes against the module constant
    # WHOLE and nothing else, so if the config pin had drifted from the deposited
    # bytes the checker would have reported all_pass while claiming config
    # agreement. The two values happened to be equal, which is exactly why nothing
    # surfaced it; found by `tool_audit.py`, looking for keys that name a source
    # their module never reads.
    #
    # It is now a THREE-WAY comparison, each limb named for what it actually
    # compares: deposited bytes -> digest, digest vs the recorded constant, and
    # digest vs the pin in config.json.
    config_pin = json.loads(CONFIG.read_text('utf-8')).get('environment_lock_sha256')
    checks = {
        # the whole-environment digest, under the VERSIONED LEGACY convention
        # root ruled should be retained and stated: Python default JSON separators
        'whole_hash_matches_recorded_constant': whole_digest == WHOLE,
        'whole_hash_matches_config_pin': whole_digest == config_pin,
        'config_pin_matches_recorded_constant': config_pin == WHOLE,
        'whole_preimage_parses': isinstance(json.loads(whole_bytes), dict),
        # the package component, tuple order, NO terminal newline
        'component_hash_matches': hashlib.sha256(comp_bytes).hexdigest() == COMPONENT,
        'component_has_no_terminal_newline': not comp_bytes.endswith(b'\n'),
        # the legacy case-insensitive file, preserved unchanged
        'legacy_txt_hash_matches': hashlib.sha256(legacy_bytes).hexdigest() == LEGACY_TXT,
        'legacy_txt_has_terminal_newline': legacy_bytes.endswith(b'\n'),
    }
    # the component digest recorded INSIDE the whole object must be the component file's
    obj = json.loads(whole_bytes)
    checks['whole_object_declares_the_component_hash'] = (
        obj.get('packages_sha256') == COMPONENT)
    # the two representations must be the same package MULTISET despite differing order
    a = _multiset(comp_bytes.decode('utf-8'))
    b = _multiset(legacy_bytes.decode('utf-8'))
    checks['both_representations_are_the_same_multiset'] = a == b
    checks['package_count_agrees_with_the_object'] = (
        len(a) == int(obj.get('packages_count') or -1))

    return {
        'schema': 'live_ab.environment_digest_check.1',
        'all_pass': all(checks.values()),
        'checks': checks,
        'package_entries': len(a),
        'serialization_conventions': {
            'whole_environment': "json.dumps(obj, sort_keys=True), PYTHON DEFAULT "
                                 "separators -- a versioned legacy convention for "
                                 "this value, retained on root's 21:17 ruling",
            'package_component': 'name==version sorted by the (Name, version) tuple, '
                                 'newline-joined, NO terminal newline',
            'legacy_txt': 'name==version sorted by name.lower(), WITH terminal newline',
        },
        # `relative_to` RAISES for a path outside the repo, which a drift test
        # legitimately supplies. Reporting where the pin came from must not be
        # able to abort the check that reads it.
        'config_pin_read_from': (str(CONFIG.relative_to(REPO))
                                 if CONFIG.is_relative_to(REPO) else str(CONFIG)),
        'config_environment_lock_sha256': config_pin,
        'what_a_pass_does_not_establish': [
            'installed-host identity', 'wheel or build provenance',
            'that the current host is unchanged since the bytes were saved',
        ],
    }


if __name__ == '__main__':
    r = check()
    print(json.dumps(r, indent=2, sort_keys=True))
    raise SystemExit(0 if r['all_pass'] else 1)
