import pytest
from typing import Any, Dict

from project.strategy.dsl.schema import (
    Blueprint,
    SymbolScopeSpec,
    EntrySpec as DSLEntrySpec,
    ExitSpec as DSLExitSpec,
    SizingSpec,
    ExecutionSpec as DSLExecutionSpec,
    EvaluationSpec,
    LineageSpec,
)
from project.compilers.spec_transformer import transform_blueprint_to_spec
from project.compilers.nautilus.core import compile_to_nautilus_backtest, compile_to_nautilus_live

def test_nautilus_compilation_pipeline():
    # 1. Create a dummy Blueprint
    blueprint = Blueprint(
        id="test_strat",
        run_id="run_123",
        event_type="VOL_SPIKE",
        candidate_id="cand_456",
        symbol_scope=SymbolScopeSpec(
            mode="single_symbol",
            symbols=["BTCUSDT"],
            candidate_symbol="BTCUSDT"
        ),
        direction="long",
        entry=DSLEntrySpec(
            triggers=["spike"],
            conditions=[],
            confirmations=[],
            delay_bars=0,
            cooldown_bars=0,
            condition_nodes=[]
        ),
        exit=DSLExitSpec(
            time_stop_bars=10,
            invalidation={"metric": "pnl", "operator": "<", "value": -0.05},
            stop_type="percent",
            stop_value=0.02,
            target_type="percent",
            target_value=0.05
        ),
        execution=DSLExecutionSpec(mode="market"),
        sizing=SizingSpec(mode="fixed_risk", risk_per_trade=0.01, max_gross_leverage=1.0, max_position_scale=0.5),
        overlays=[],
        evaluation=EvaluationSpec(
            min_trades=10,
            cost_model={"fees_bps": 2.0, "slippage_bps": 1.0, "funding_included": True},
            robustness_flags={"oos_required": True, "multiplicity_required": True, "regime_stability_required": True}
        ),
        lineage=LineageSpec(
            source_path="path/to/src",
            compiler_version="1.0",
            generated_at_utc="2026-03-06T12:00:00Z"
        )
    )

    # 2. Transform to StrategySpec
    spec = transform_blueprint_to_spec(blueprint)
    assert spec.strategy_id == "test_strat"
    assert spec.instrument == "BTCUSDT"
    assert spec.exit.take_profit_bps == 500.0 # 0.05 * 10000

    # 3. Compile to Nautilus Backtest
    backtest_bundle = compile_to_nautilus_backtest(spec)
    assert backtest_bundle["strategy_class"] == "NautilusGeneratedStrategy"
    assert backtest_bundle["config"]["instrument_id"] == "BTCUSDT.BINANCE"
    assert backtest_bundle["config"]["take_profit_bps"] == 500.0

    # 4. Compile to Nautilus Live
    live_bundle = compile_to_nautilus_live(spec, venue_profile={"api_key_ref": "secret_key"})
    assert live_bundle["adapter_config"]["api_key_ref"] == "secret_key"
    assert live_bundle["execution_policy"]["style"] == "market"

if __name__ == "__main__":
    test_nautilus_compilation_pipeline()
    print("Phase 5 compilation pipeline test passed.")
