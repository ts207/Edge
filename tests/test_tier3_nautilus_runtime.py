import pytest
from pathlib import Path
from project.strategy.dsl.schema import (
    Blueprint, SymbolScopeSpec, EntrySpec as DSLEntrySpec, 
    ExitSpec as DSLExitSpec, SizingSpec, ExecutionSpec as DSLExecutionSpec,
    EvaluationSpec, LineageSpec
)
from project.compilers.spec_transformer import transform_blueprint_to_spec
from project.compilers.nautilus.core import compile_to_nautilus_backtest
from project.runtime.nautilus.service import NautilusExecutionService

def test_tier3_validation_pipeline():
    # 1. Promote a candidate (Mocked as Blueprint)
    blueprint = Blueprint(
        id="alpha_sweep_v1",
        run_id="run_999",
        event_type="LARGE_SWEEP",
        candidate_id="cand_sweep_001",
        symbol_scope=SymbolScopeSpec(mode="single_symbol", symbols=["BTCUSDT"], candidate_symbol="BTCUSDT"),
        direction="short",
        entry=DSLEntrySpec(triggers=["sweep"], conditions=[], confirmations=[], delay_bars=0, cooldown_bars=0),
        exit=DSLExitSpec(
            time_stop_bars=12,
            invalidation={"metric": "spread", "operator": ">", "value": 5.0},
            stop_type="percent", stop_value=0.01,
            target_type="percent", target_value=0.02
        ),
        execution=DSLExecutionSpec(mode="limit", max_slippage_bps=2.0),
        sizing=SizingSpec(mode="fixed_risk", max_gross_leverage=1.0, max_position_scale=0.1),
        overlays=[],
        evaluation=EvaluationSpec(
            min_trades=20,
            cost_model={"fees_bps": 1.0, "slippage_bps": 1.0, "funding_included": True},
            robustness_flags={"oos_required": True, "multiplicity_required": True, "regime_stability_required": True}
        ),
        lineage=LineageSpec(source_path="src", compiler_version="1", generated_at_utc="now")
    )

    # 2. Tier 2: Canonical Spec Validation
    spec = transform_blueprint_to_spec(blueprint)
    assert spec.strategy_id == "alpha_sweep_v1"
    assert spec.execution.style == "limit"

    # 3. Tier 3: Nautilus Backtest Validation
    compilation = compile_to_nautilus_backtest(spec)
    assert compilation["data_bindings"]["book_subscription"] is True # Required because mode=limit
    
    runtime_service = NautilusExecutionService(
        data_path=Path("/tmp/nautilus_data"),
        output_path=Path("/tmp/nautilus_results")
    )
    
    results = runtime_service.run_backtest(compilation)
    assert results["status"] in {"completed", "stub_completed"}
    assert results["metrics"]["sharpe_ratio"] > 0
    assert "tearsheet_path" in results

if __name__ == "__main__":
    test_tier3_validation_pipeline()
    print("Tier 3 Nautilus Validation Pipeline passed.")
