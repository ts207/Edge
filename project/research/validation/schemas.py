from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


def _coerce(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _coerce(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    return value


@dataclass(frozen=True)
class ValidationSplit:
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    purge_bars: int = 0
    embargo_bars: int = 0
    bar_duration_minutes: int = 5

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["start"] = self.start.isoformat()
        payload["end"] = self.end.isoformat()
        return payload


@dataclass(frozen=True)
class EffectEstimate:
    estimate: float
    stderr: float
    ci_low: float
    ci_high: float
    p_value_raw: float
    n_obs: int
    n_clusters: int
    method: str
    cluster_col: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultiplicityResult:
    correction_family_id: str
    correction_method: str
    p_value_raw: float
    p_value_adj: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StabilityResult:
    sign_consistency: float
    stability_score: float
    regime_stability_pass: bool
    timeframe_consensus_pass: bool
    delay_robustness_pass: bool
    regime_flip_flag: bool = False
    cross_symbol_sign_consistency: float = 0.0
    rolling_instability_score: float = 0.0
    worst_regime_estimate: float = 0.0
    worst_symbol_estimate: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _coerce(self)


@dataclass(frozen=True)
class FalsificationResult:
    shift_placebo_pass: bool
    random_placebo_pass: bool
    direction_reversal_pass: bool
    negative_control_pass: bool
    control_pass_rate: Optional[float] = None
    empirical_exceedance: Optional[float] = None
    null_mean: Optional[float] = None
    null_p95: Optional[float] = None
    passes_control: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _coerce(self)


@dataclass(frozen=True)
class PromotionDecision:
    eligible: bool
    promotion_status: str
    promotion_track: str
    rank_score: float
    rejection_reasons: List[str] = field(default_factory=list)
    gate_results: Dict[str, bool] = field(default_factory=dict)
    policy_version: str = "phase4_pr5_v1"
    bundle_version: str = "phase4_bundle_v1"

    def to_dict(self) -> Dict[str, Any]:
        return _coerce(self)


@dataclass(frozen=True)
class EvidenceBundle:
    candidate_id: str
    event_family: str
    event_type: str
    run_id: str
    sample_definition: Dict[str, Any]
    split_definition: Dict[str, Any]
    effect_estimates: Dict[str, Any]
    uncertainty_estimates: Dict[str, Any]
    stability_tests: Dict[str, Any]
    falsification_results: Dict[str, Any]
    cost_robustness: Dict[str, Any]
    multiplicity_adjustment: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    promotion_decision: Dict[str, Any] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    policy_version: str = "phase4_pr5_v1"
    bundle_version: str = "phase4_bundle_v1"

    def to_dict(self) -> Dict[str, Any]:
        return _coerce(self)
