from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from project.research.search_intelligence import _build_frontier


def test_search_frontier_is_regime_first_and_executable_only():
    frontier = _build_frontier(
        SimpleNamespace(events={"events": {}}),
        tested_regions=pd.DataFrame(
            [{"event_type": "LIQUIDITY_STRESS_DIRECT", "canonical_regime": "LIQUIDITY_STRESS"}]
        ),
        failures=pd.DataFrame(),
        untested_top_k=3,
        repair_top_k=1,
        exhausted_failure_threshold=3,
        quality_weights={},
    )

    assert "untested_canonical_regimes" in frontier
    assert "LIQUIDITY_STRESS" not in frontier["untested_canonical_regimes"]
    fanout = frontier["canonical_regime_event_fanout"]
    for regime, event_ids in fanout.items():
        assert regime
        assert "SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY" not in event_ids
        assert "SESSION_OPEN_EVENT" not in event_ids
        assert "COPULA_PAIRS_TRADING" not in event_ids
