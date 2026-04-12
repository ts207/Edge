import pytest
from project.portfolio.orchestration import ThesisIntent, PortfolioContext, TargetPortfolioState

def test_schemas_instantiate():
    intent = ThesisIntent(
        strategy_id="strat_1",
        family_id="momentum",
        symbol="BTC",
        requested_notional=10000.0,
        setup_match=0.9,
        thesis_strength=0.8,
        freshness=1.0,
        execution_quality=0.95,
        capital_efficiency=1.2
    )
    context = PortfolioContext(
        max_portfolio_notional=100000.0,
        family_caps={"momentum": 20000.0},
        symbol_caps={"BTC": 30000.0}
    )
    state = TargetPortfolioState(allocations={"strat_1": 5000.0})
    
    assert intent.strategy_id == "strat_1"
    assert context.max_portfolio_notional == 100000.0
    assert state.allocations["strat_1"] == 5000.0
