from __future__ import annotations

import copy
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from project.schemas.strategy_spec import StrategySpec
from project.compilers.nautilus.mappers.instruments import map_to_nautilus_instrument_id
from project.compilers.nautilus.mappers.execution import map_execution_intent
from project.compilers.nautilus.mappers.data import map_data_requirements

_LOG = logging.getLogger(__name__)

def compile_to_nautilus_backtest(
    strategy_spec: StrategySpec,
    environment: str = "backtest"
) -> Dict[str, Any]:
    """
    Translates canonical StrategySpec into Nautilus backtest artifacts using specialized mappers.
    """
    _LOG.info("Compiling strategy %s for Nautilus backtest", strategy_spec.strategy_id)
    
    instrument_id = map_to_nautilus_instrument_id(strategy_spec.venue, strategy_spec.instrument)
    exec_config = map_execution_intent(strategy_spec.execution.style, strategy_spec.execution.post_only_preference)
    data_config = map_data_requirements(
        strategy_spec.data_requirements.bars, 
        strategy_spec.data_requirements.book,
        strategy_spec.data_requirements.depth_fidelity
    )
    
    nautilus_config = {
        "name": strategy_spec.strategy_id,
        "instrument_id": instrument_id,
        "bar_type": strategy_spec.data_requirements.bars[0],
        "take_profit_bps": strategy_spec.exit.take_profit_bps,
        "stop_loss_bps": strategy_spec.exit.stop_loss_bps,
        "max_notional": strategy_spec.risk.max_position_notional_usd,
        "execution": exec_config,
    }

    return {
        "strategy_class": "NautilusGeneratedStrategy",
        "config": nautilus_config,
        "instrument_bindings": [instrument_id],
        "data_bindings": data_config,
        "run_manifest": {
            "strategy_id": strategy_spec.strategy_id,
            "engine": "Nautilus.BacktestEngine",
            "environment": environment
        }
    }

def compile_to_nautilus_live(
    strategy_spec: StrategySpec,
    venue_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Translates canonical StrategySpec into Nautilus live execution artifacts.
    """
    _LOG.info("Compiling strategy %s for Nautilus live deployment", strategy_spec.strategy_id)
    
    backtest_bundle = compile_to_nautilus_backtest(strategy_spec, environment="live")
    
    live_bundle = copy.deepcopy(backtest_bundle)
    live_bundle.update({
        "adapter_config": {
            "venue": strategy_spec.venue,
            "api_key_ref": venue_profile.get("api_key_ref"),
            "account_type": venue_profile.get("account_type", "margin"),
            "clock_sync": True
        },
        "execution_policy": {
            "style": strategy_spec.execution.style,
            "post_only": strategy_spec.execution.post_only_preference
        }
    })
    
    return live_bundle
