"""
Hierarchical James-Stein shrinkage and time-decay weighting.
Public API facade for backward compatibility.
"""

from __future__ import annotations

from project.research.helpers.parameter_normalization import (
    update_shrinkage_parameters_from_spec,
    _ensure_shrinkage_parameters_loaded,
    _resolve_tau_days,
    _normalize_vol_regime,
    _normalize_liquidity_state,
    _regime_conditioned_tau_days,
    _direction_sign,
    _optional_token,
    _event_direction_from_joined_row,
    _asymmetric_tau_days,
    _SHRINKAGE_LOCK,
    _TAU_BY_FAMILY_DAYS,
    _VOL_REGIME_MULTIPLIER,
    _LIQUIDITY_STATE_MULTIPLIER,
    _DIRECTIONAL_ASYMMETRY_BY_FAMILY,
    _EVENT_DIRECTION_NUMERIC_COLS,
    _EVENT_DIRECTION_TEXT_COLS,
)

from project.research.helpers.estimation_kernels import (
    _time_decay_weights,
    _effective_sample_size,
    _aggregate_effect_units,
    _estimate_adaptive_lambda,
    _compute_loso_stability,
    _apply_hierarchical_shrinkage,
)

from project.research.helpers.diagnostics import (
    _refresh_phase2_metrics_after_shrinkage,
)

__all__ = [
    "update_shrinkage_parameters_from_spec",
    "_ensure_shrinkage_parameters_loaded",
    "_resolve_tau_days",
    "_normalize_vol_regime",
    "_normalize_liquidity_state",
    "_regime_conditioned_tau_days",
    "_direction_sign",
    "_optional_token",
    "_event_direction_from_joined_row",
    "_asymmetric_tau_days",
    "_time_decay_weights",
    "_effective_sample_size",
    "_aggregate_effect_units",
    "_estimate_adaptive_lambda",
    "_compute_loso_stability",
    "_apply_hierarchical_shrinkage",
    "_refresh_phase2_metrics_after_shrinkage",
]
