from __future__ import annotations

from project.live.contracts import (
    PromotedThesis,
    ThesisEvidence,
    ThesisLineage,
)
from project.live.contracts.live_trade_context import LiveTradeContext
from project.live.retriever import retrieve_ranked_theses
from project.live.thesis_store import ThesisStore


def _canonical_confirm_thesis() -> PromotedThesis:
    return PromotedThesis(
        thesis_id="thesis::shadow::cand_confirm",
        status="active",
        symbol_scope={
            "mode": "single_symbol",
            "symbols": ["BTCUSDT"],
            "candidate_symbol": "BTCUSDT",
        },
        timeframe="5m",
        event_family="IGNORED_FALLBACK",
        event_side="both",
        required_context={},
        supportive_context={"has_realized_oos_path": True},
        expected_response={},
        invalidation={},
        risk_notes=[],
        evidence=ThesisEvidence(
            sample_size=40,
            validation_samples=20,
            test_samples=20,
            estimate_bps=90.0,
            net_expectancy_bps=84.0,
            q_value=0.02,
            stability_score=0.8,
            rank_score=3.0,
        ),
        lineage=ThesisLineage(
            run_id="shadow",
            candidate_id="THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM",
        ),
    )


def test_retriever_uses_canonical_confirmation_clause_when_present() -> None:
    store = ThesisStore([_canonical_confirm_thesis()])
    context = LiveTradeContext(
        timestamp="2026-04-02T00:00:00Z",
        symbol="BTCUSDT",
        timeframe="5m",
        event_family="VOL_SHOCK",
        event_side="long",
        live_features={},
        regime_snapshot={"canonical_regime": "VOLATILITY_TRANSITION"},
        execution_env={},
        portfolio_state={},
        active_event_families=["VOL_SHOCK"],
        active_episode_ids=[],
    )

    match = retrieve_ranked_theses(thesis_store=store, context=context, include_pending=False, limit=1)[0]

    assert match.eligibility_passed is True
    assert "trigger_clause_match:VOL_SHOCK" in match.reasons_for
    assert "confirmation_missing:LIQUIDITY_VACUUM" in match.reasons_against


def test_retriever_prefers_canonical_thesis_clauses_over_packaged_event_family() -> None:
    store = ThesisStore([_canonical_confirm_thesis()])
    context = LiveTradeContext(
        timestamp="2026-04-02T00:00:00Z",
        symbol="BTCUSDT",
        timeframe="5m",
        event_family="VOL_SHOCK",
        event_side="long",
        live_features={},
        regime_snapshot={"canonical_regime": "VOLATILITY_TRANSITION"},
        execution_env={},
        portfolio_state={},
        active_event_families=["VOL_SHOCK", "LIQUIDITY_VACUUM"],
        active_episode_ids=[],
    )

    match = retrieve_ranked_theses(thesis_store=store, context=context, include_pending=False, limit=1)[0]

    assert match.eligibility_passed is True
    assert "trigger_clause_match:VOL_SHOCK" in match.reasons_for
    assert "confirmation_match:LIQUIDITY_VACUUM" in match.reasons_for
    assert "event_family_match:IGNORED_FALLBACK" not in match.reasons_for
