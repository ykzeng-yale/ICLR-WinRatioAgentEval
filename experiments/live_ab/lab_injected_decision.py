"""TEST-ONLY injected-decision fixture, and the production refusal of it.

Root, 2026-09-21 20:43: "the proposed strong-form test is the right one. Exercise
the real production configuration/startup path with the injection flag/hook
requested, assert explicit refusal BEFORE ANY DISPATCH OR MODEL REQUEST, and
include a valid production configuration control. The fixture must be separately
labelled/pinned and reachable only through the test route."

Root, 2026-09-21 23:29: "The injected-decision fixture may live inside the owned
harness directory and MUST BE PINNED. Mark it test-only and not reachable in trial
configuration; test that production rejects its activation."

WHY THIS FILE IS INSIDE THE PINNED HARNESS
------------------------------------------
``lab_common.HARNESS_FILES`` globs ``experiments/live_ab/*.py``, so this module
moves ``harness_file_sha256``. That is intended: it is execution-adjacent code and
root ruled that execution-relevant code stays pinned. The descriptive reporting
tools live outside for the opposite reason.

WHAT IT IS AND IS NOT
---------------------
It injects a decision event at the monitor/router interface so the receipt,
switch, pending-work resolution and post-switch bookkeeping can be exercised
without waiting for a natural crossing. Root, 2026-09-21 19:29: "The fixture is an
injected control-path test, NOT statistical evidence or an observed real-server
decision." Nothing it produces is an observation, and it never touches monitor
outputs.

THE STRONG FORM, NOT THE WEAK ONE
---------------------------------
The weak form asserts the fixture "is not wired in today", which proves only that
nobody wired it. The strong form drives the PRODUCTION configuration path with
activation requested and asserts an explicit refusal. That is what is implemented:
``assert_no_test_fixture_active`` runs on the production path and raises, and the
fixture itself refuses to arm without a token that production never mints.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

#: The config key that would request injection. Production must REFUSE it.
ACTIVATION_KEY = 'injected_decision_fixture'

#: The only token that arms the fixture. Production never mints this; it exists
#: solely so the test route is explicit rather than implied by absence.
TEST_ROUTE_TOKEN = 'TEST-ROUTE-ONLY:injected-decision'

FIXTURE_LABEL = ('TEST-ONLY INJECTED-DECISION CONTROL-PATH FIXTURE. Not statistical '
                 'evidence, not an observed decision, and not reachable from any '
                 'trial configuration.')


class FixtureActivationRefused(lab_common.PreflightError):
    """A production path requested, or a test route failed to authorise, injection."""


def assert_no_test_fixture_active(cfg: dict, *, stage: str = 'production startup') -> Dict[str, Any]:
    """The PRODUCTION guard. Raises before any dispatch or model request.

    Called on the production configuration/startup path. A configuration that
    requests injection is refused outright -- injection is a control-path test and
    a trial that ran with it would not be a trial.
    """
    # DELEGATES to the one shared policy in lab_common (root 2026-09-22): two
    # implementations of one refusal is how a path quietly stops being guarded.
    # The exception type stays FixtureActivationRefused, which IS a PreflightError,
    # so existing callers and tests keep their contract.
    if lab_common.fixture_requested(cfg):
        raise FixtureActivationRefused(
            '%s: configuration requests %r. The injected-decision fixture is a '
            'TEST-ONLY control-path device and is refused on the production path, '
            'before any dispatch or model request. A trial that ran with an '
            'injected decision would not be a trial.' % (stage, ACTIVATION_KEY))
    return lab_common.assert_no_fixture(cfg, stage=stage)


def arm(cfg: dict, token: Optional[str] = None) -> Dict[str, Any]:
    """Arm the fixture. Reachable ONLY through the explicit test route.

    Refuses without the test token, and refuses for any configuration that looks
    like a trial configuration even when the token is supplied -- so the token
    alone cannot turn a real trial into an injected one.
    """
    if token != TEST_ROUTE_TOKEN:
        raise FixtureActivationRefused(
            'the injected-decision fixture requires the explicit test-route token; '
            'it cannot be armed by configuration, by import, or by default')
    trials = (cfg or {}).get('trials') or {}
    if trials and not (cfg or {}).get('rehearsal_only'):
        raise FixtureActivationRefused(
            'this configuration declares %d trial(s) and is not marked '
            'rehearsal_only; the fixture refuses to arm against a trial '
            'configuration even with a valid test token' % len(trials))
    return {'armed': True, 'label': FIXTURE_LABEL,
            'produces_observations': False,
            'touches_monitor_outputs': False}


def inject_decision(kind: str = 'DEPLOY') -> Dict[str, Any]:
    """The synthetic decision event, for exercising the control path only."""
    if kind not in ('DEPLOY', 'RETAIN_INCUMBENT'):
        raise ValueError('unsupported injected decision kind %r' % (kind,))
    return {'schema': 'live_ab/injected_decision-v1', 'decision': kind,
            'synthetic': True, 'is_observation': False,
            'label': FIXTURE_LABEL}
