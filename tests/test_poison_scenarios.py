"""Multi-step PoisonBench scenarios as a regression gate.

The single-shot corpus is measured out-of-band by `evals.poisonbench.run`; these
stateful scenarios (patient / distributed / T0-spoof / semantic / negative) are
pinned here so a future change can't silently reopen a closed attack path. Every
scenario must be CONTAINED; crypto-dependent T0 scenarios may report 'skipped'
when the [admin] extra is absent, which is not a failure.
"""

import pytest
from evals.poisonbench.scenarios import SCENARIOS


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
async def test_scenario_contained(scenario):
    result = await scenario.run()
    assert result.status in ("contained", "skipped"), f"{scenario.id} BREACHED: {result.detail}"


async def test_no_scenario_breached():
    """Aggregate guard: across the whole suite, nothing is breached."""
    breached = []
    for sc in SCENARIOS:
        res = await sc.run()
        if res.status == "breached":
            breached.append(f"{sc.id}: {res.detail}")
    assert not breached, "breached scenarios: " + "; ".join(breached)
