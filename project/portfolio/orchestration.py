from pydantic import BaseModel, Field
from typing import Dict, Optional

class ThesisIntent(BaseModel):
    strategy_id: str
    family_id: str
    symbol: str
    requested_notional: float
    setup_match: float
    thesis_strength: float
    freshness: float
    execution_quality: float
    capital_efficiency: float

class PortfolioContext(BaseModel):
    max_portfolio_notional: float
    family_caps: Dict[str, float] = Field(default_factory=dict)
    symbol_caps: Dict[str, float] = Field(default_factory=dict)

class TargetPortfolioState(BaseModel):
    allocations: Dict[str, float]
