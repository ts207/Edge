from __future__ import annotations

import logging
from typing import Any, Dict

from project.strategy.dsl.schema import Blueprint as DSLBlueprint
from project.schemas.strategy_spec import (
    StrategySpec,
    DataRequirements,
    EntrySpec as CanonicalEntrySpec,
    EntryCondition,
    ExitSpec as CanonicalExitSpec,
    RiskSpec,
    ExecutionSpec as CanonicalExecutionSpec,
)
from project.core.config import load_configs
from project import PROJECT_ROOT

_LOG = logging.getLogger(__name__)

def transform_blueprint_to_spec(blueprint: DSLBlueprint) -> StrategySpec:
    """
    Transforms a research DSL Blueprint into a canonical StrategySpec.
    """
    # 1. Map Data Requirements
    # Mandate 1m bars if execution style requires it for realistic simulation
    requires_high_fidelity = blueprint.execution.mode in ["limit", "passive", "passive_then_cross", "close"]
    
    data_reqs = DataRequirements(
        bars=["1m"] if requires_high_fidelity else ["5m"],
        book=requires_high_fidelity,
        trades=True,
        latency_class="low" if requires_high_fidelity else "medium",
        depth_fidelity="top_5" if requires_high_fidelity else "tob"
    )

    # 2. Map Entry Conditions
    canonical_conditions = []
    for node in blueprint.entry.condition_nodes:
        canonical_conditions.append(EntryCondition(
            feature=node.feature,
            operator=node.operator if node.operator in ["==", "!=", ">", "<", ">=", "<="] else ">", # Simple mapping
            value=node.value
        ))

    entry_spec = CanonicalEntrySpec(
        event_family=blueprint.event_type,
        conditions=canonical_conditions,
        direction=blueprint.direction.upper() if blueprint.direction in ["long", "short"] else "LONG" # Fallback
    )

    # 3. Map Exit Logic
    exit_spec = CanonicalExitSpec(
        time_stop_bars=blueprint.exit.time_stop_bars,
        take_profit_bps=blueprint.exit.target_value * 10000.0 if blueprint.exit.target_type == "percent" else None,
        stop_loss_bps=blueprint.exit.stop_value * 10000.0 if blueprint.exit.stop_type == "percent" else None
    )

    # 4. Map Risk
    try:
        profiles_cfg = load_configs([str(PROJECT_ROOT / "configs" / "retail_profiles.yaml")])
        profile = profiles_cfg.get("profiles", {}).get("capital_constrained", {})
        baseline_capital = float(profile.get("account_equity_usd", 25000.0))
        max_positions = int(profile.get("max_concurrent_positions", 3))
    except Exception as e:
        _LOG.warning("Failed to load retail profiles for risk sizing, using defaults: %s", e)
        baseline_capital = 25000.0
        max_positions = 3

    risk_spec = RiskSpec(
        max_position_notional_usd=blueprint.sizing.max_position_scale * baseline_capital,
        max_concurrent_positions=max_positions
    )

    # 5. Map Execution
    execution_spec = CanonicalExecutionSpec(
        style=blueprint.execution.mode if blueprint.execution.mode in ["market", "passive", "limit"] else "market",
        post_only_preference=blueprint.execution.mode == "limit",
        slippage_assumption_bps=blueprint.execution.max_slippage_bps,
        cost_assumption_bps=blueprint.evaluation.cost_model.get("fees_bps", 1.0)
    )

    # 6. Final Spec
    spec = StrategySpec(
        strategy_id=blueprint.id,
        thesis=f"Event-driven strategy for {blueprint.event_type}",
        venue=getattr(blueprint.symbol_scope, "venue", "BINANCE"),
        instrument=blueprint.symbol_scope.candidate_symbol,
        data_requirements=data_reqs,
        entry=entry_spec,
        exit=exit_spec,
        risk=risk_spec,
        execution=execution_spec
    )

    spec.validate_spec()
    return spec
