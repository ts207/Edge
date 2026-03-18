from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple

import numpy as np
import pandas as pd

from project.core.constants import BARS_PER_YEAR_BY_TIMEFRAME
from project.portfolio import AllocationSpec


ALLOCATION_CONTRACT_SCHEMA_VERSION = "allocation_contract_v1"
ALLOCATION_DIAGNOSTICS_SCHEMA_VERSION = "allocation_diagnostics_v1"

# Provide an optimised implementation for the per-bar clamping loop used
# when enforcing ``max_new_exposure_per_bar``.  If Numba is installed the
# helper will be JIT‑compiled for performance; otherwise a pure Python
# implementation is used.  The function traverses an array of target
# exposures and ensures that changes between consecutive elements do not
# exceed the specified ``max_new`` threshold.
def _clamp_positions_py(raw: np.ndarray, max_new: float) -> np.ndarray:
    n = raw.size
    out = np.empty_like(raw)
    prior = 0.0
    for i in range(n):
        target = raw[i]
        delta = target - prior
        if delta > max_new:
            delta = max_new
        elif delta < -max_new:
            delta = -max_new
        out[i] = prior + delta
        prior = out[i]
    return out

try:
    from numba import njit  # type: ignore
    _clamp_positions = njit(cache=True)(_clamp_positions_py)
except Exception:
    _clamp_positions = _clamp_positions_py

@dataclass(frozen=True)
class RiskLimits:
    max_portfolio_gross: float = 1.0
    max_symbol_gross: float = 1.0
    max_strategy_gross: float = 1.0
    max_new_exposure_per_bar: float = 1.0
    target_annual_vol: float | None = None
    max_drawdown_limit: float | None = None
    max_correlated_gross: float | None = None
    max_pairwise_correlation: float | None = None
    # NEW: stress-conditional correlation limit — tighter limit applied when
    # regime_series contains a value in stressed_regime_values
    stressed_max_pairwise_correlation: float | None = None
    stressed_regime_values: frozenset[str] = frozenset({"stress", "crisis", "high_vol"})
    portfolio_max_drawdown: float | None = None
    symbol_max_exposure: float | None = None
    portfolio_max_exposure: float | None = None
    enable_correlation_allocation: bool = False

    # Vol estimator configuration
    vol_estimator_mode: str = "rolling"      # "rolling" | "ewma"
    vol_window_bars: int = 5760             # rolling window (bars); only used when mode="rolling"
    vol_ewma_halflife_bars: int = 1440      # EWMA halflife (bars); only used when mode="ewma"
    bars_per_year: float = float(BARS_PER_YEAR_BY_TIMEFRAME["5m"])

    def __post_init__(self) -> None:
        if self.vol_estimator_mode not in ("rolling", "ewma"):
            raise ValueError(
                f"vol_estimator_mode must be 'rolling' or 'ewma', got {self.vol_estimator_mode!r}"
            )


@dataclass(frozen=True)
class AllocationPolicy:
    mode: str = "heuristic"
    deterministic: bool = True
    turnover_penalty: float = 0.0
    strategy_risk_budgets: Dict[str, float] = field(default_factory=dict)
    family_risk_budgets: Dict[str, float] = field(default_factory=dict)
    strategy_family_map: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in {"heuristic", "deterministic_optimizer"}:
            raise ValueError(
                "allocator mode must be 'heuristic' or 'deterministic_optimizer', "
                f"got {self.mode!r}"
            )
        if self.turnover_penalty < 0.0:
            raise ValueError("turnover_penalty must be non-negative")


@dataclass(frozen=True)
class AllocationContract:
    limits: RiskLimits
    policy: AllocationPolicy = field(default_factory=AllocationPolicy)
    schema_version: str = ALLOCATION_CONTRACT_SCHEMA_VERSION
    diagnostics_schema_version: str = ALLOCATION_DIAGNOSTICS_SCHEMA_VERSION

    def to_manifest_payload(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "diagnostics_schema_version": self.diagnostics_schema_version,
            "policy": {
                "mode": self.policy.mode,
                "deterministic": self.policy.deterministic,
                "turnover_penalty": float(self.policy.turnover_penalty),
                "strategy_risk_budgets": {
                    str(key): float(value)
                    for key, value in sorted(self.policy.strategy_risk_budgets.items())
                },
                "family_risk_budgets": {
                    str(key): float(value)
                    for key, value in sorted(self.policy.family_risk_budgets.items())
                },
                "strategy_family_map": {
                    str(key): str(value)
                    for key, value in sorted(self.policy.strategy_family_map.items())
                },
            },
            "limits": {
                field_name: (
                    sorted(getattr(self.limits, field_name))
                    if isinstance(getattr(self.limits, field_name), (set, frozenset))
                    else getattr(self.limits, field_name)
                )
                for field_name in self.limits.__dataclass_fields__
            },
        }


@dataclass(frozen=True)
class AllocationDetails:
    allocated_positions_by_strategy: Dict[str, pd.Series]
    scale_by_strategy: Dict[str, pd.Series]
    diagnostics: pd.DataFrame
    summary: Dict[str, object]
    contract: AllocationContract
    policy_weights: Dict[str, float]


def _as_float_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def _coerce_budget_mapping(raw: object) -> Dict[str, float]:
    if raw is None:
        return {}
    parsed = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("risk budget mappings must be a mapping or JSON object string")
    out: Dict[str, float] = {}
    for key, value in parsed.items():
        numeric = float(value)
        if numeric < 0.0:
            raise ValueError(f"risk budget for {key!r} must be non-negative")
        out[str(key)] = numeric
    return out


def _coerce_string_mapping(raw: object) -> Dict[str, str]:
    if raw is None:
        return {}
    parsed = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("string mappings must be a mapping or JSON object string")
    return {
        str(key): str(value).strip()
        for key, value in parsed.items()
        if str(value).strip()
    }


def _optional_float(raw: object) -> float | None:
    if raw is None:
        return None
    return float(raw)


def build_allocation_contract(params: Mapping[str, object]) -> AllocationContract:
    raw_allocation_spec = params.get("allocation_spec")
    if raw_allocation_spec is not None:
        allocation_spec = (
            raw_allocation_spec
            if isinstance(raw_allocation_spec, AllocationSpec)
            else AllocationSpec.model_validate(dict(raw_allocation_spec))
        )
        params = {**allocation_spec.to_allocator_params(), **{k: v for k, v in params.items() if k != "allocation_spec"}}
    limits = RiskLimits(
        portfolio_max_exposure=float(params.get("portfolio_max_exposure", 10.0)),
        max_portfolio_gross=float(params.get("max_portfolio_gross", 10.0)),
        max_strategy_gross=float(params.get("max_strategy_gross", 10.0)),
        max_symbol_gross=float(params.get("max_symbol_gross", 10.0)),
        max_new_exposure_per_bar=float(params.get("max_new_exposure_per_bar", 10.0)),
        target_annual_vol=_optional_float(params.get("target_annual_volatility")),
        max_pairwise_correlation=_optional_float(params.get("max_pairwise_correlation")),
        max_drawdown_limit=_optional_float(params.get("drawdown_limit")),
        portfolio_max_drawdown=_optional_float(params.get("portfolio_max_drawdown")),
        symbol_max_exposure=_optional_float(params.get("max_symbol_exposure")),
        enable_correlation_allocation=bool(
            params.get("enable_correlation_allocation", False)
        ),
    )
    policy = AllocationPolicy(
        mode=str(params.get("allocator_mode", "heuristic")).strip().lower(),
        deterministic=bool(params.get("allocator_deterministic", True)),
        turnover_penalty=float(params.get("allocator_turnover_penalty", 0.0)),
        strategy_risk_budgets=_coerce_budget_mapping(params.get("strategy_risk_budgets")),
        family_risk_budgets=_coerce_budget_mapping(params.get("family_risk_budgets")),
        strategy_family_map=_coerce_string_mapping(params.get("strategy_family_map")),
    )
    return AllocationContract(limits=limits, policy=policy)


def _normalize_policy_weights(scores: pd.Series) -> pd.Series:
    positive = pd.to_numeric(scores, errors="coerce").fillna(0.0).clip(lower=0.0)
    total = float(positive.sum())
    if total <= 0.0:
        if len(positive.index) == 0:
            return positive.astype(float)
        return pd.Series(
            1.0 / float(len(positive.index)),
            index=positive.index,
            dtype=float,
        )
    return (positive / total).astype(float)


def _resolve_policy_weights(
    requested: Dict[str, pd.Series],
    ordered: list[str],
    contract: AllocationContract,
) -> Dict[str, float]:
    if not requested:
        return {}
    if contract.policy.mode == "heuristic":
        return {key: 1.0 for key in ordered}

    requested_frame = pd.DataFrame(requested).fillna(0.0)
    gross_by_strategy = requested_frame.abs().sum(axis=0).reindex(ordered).fillna(0.0)
    turnover_by_strategy = (
        requested_frame.diff().abs().sum(axis=0).reindex(ordered).fillna(0.0)
    )
    scores = pd.Series(index=ordered, dtype=float)
    for key in ordered:
        budget = float(contract.policy.strategy_risk_budgets.get(key, 1.0))
        gross = float(gross_by_strategy.get(key, 0.0))
        turnover = float(turnover_by_strategy.get(key, 0.0))
        denom = max(gross + (float(contract.policy.turnover_penalty) * turnover), 1e-12)
        scores.loc[key] = 0.0 if budget <= 0.0 else budget / denom
    weights = _normalize_policy_weights(scores)
    return {str(key): float(weights.loc[key]) for key in ordered}


def _apply_family_budget_caps(
    allocated: Dict[str, pd.Series],
    *,
    ordered: list[str],
    aligned_index: pd.Index,
    contract: AllocationContract,
    flag: callable,
) -> Dict[str, int]:
    family_budget_hits: Dict[str, int] = {}
    family_members: Dict[str, list[str]] = {}
    for key in ordered:
        family = str(contract.policy.strategy_family_map.get(key, key)).strip() or key
        family_members.setdefault(family, []).append(key)

    for family, members in family_members.items():
        budget = contract.policy.family_risk_budgets.get(family)
        if budget is None:
            continue
        family_frame = pd.DataFrame({member: allocated[member] for member in members}, index=aligned_index)
        family_gross = family_frame.abs().sum(axis=1)
        safe_family_gross = family_gross.replace(0.0, np.nan)
        family_ratio = (float(max(0.0, budget)) / safe_family_gross).where(family_gross > float(budget), 1.0)
        family_ratio = family_ratio.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(lower=0.0, upper=1.0)
        family_mask = family_ratio < 0.999999
        if bool(family_mask.any()):
            family_budget_hits[family] = int(family_mask.sum())
            flag(
                f"family_risk_budget:{family}",
                family_mask,
            )
            flag("family_risk_budget", family_mask)
            for member in members:
                allocated[member] = allocated[member] * family_ratio
    return family_budget_hits


def allocate_position_scales(
    raw_positions_by_strategy: Dict[str, pd.Series],
    requested_scale_by_strategy: Dict[str, pd.Series],
    limits: RiskLimits,
    contract: AllocationContract | None = None,
    portfolio_pnl_series: pd.Series | None = None,
    regime_series: pd.Series | None = None,
    regime_scale_map: Dict[str, float] | None = None,
) -> Tuple[Dict[str, pd.Series], Dict[str, object]]:
    details = allocate_position_details(
        raw_positions_by_strategy,
        requested_scale_by_strategy,
        limits,
        contract=contract,
        portfolio_pnl_series=portfolio_pnl_series,
        regime_series=regime_series,
        regime_scale_map=regime_scale_map,
    )
    return details.scale_by_strategy, details.summary


def allocate_position_details(
    raw_positions_by_strategy: Dict[str, pd.Series],
    requested_scale_by_strategy: Dict[str, pd.Series],
    limits: RiskLimits,
    contract: AllocationContract | None = None,
    portfolio_pnl_series: pd.Series | None = None,
    regime_series: pd.Series | None = None,
    regime_scale_map: Dict[str, float] | None = None,
) -> AllocationDetails:
    resolved_contract = contract or AllocationContract(limits=limits)
    if not raw_positions_by_strategy:
        empty_diag = pd.DataFrame(columns=[
            "requested_gross",
            "allocated_gross",
            "clip_fraction",
            "clip_reason",
            "allocator_mode",
        ])
        return AllocationDetails(
            {},
            {},
            empty_diag,
            {
                "requested_gross": 0.0,
                "allocated_gross": 0.0,
                "clipped_fraction": 0.0,
                "allocator_mode": resolved_contract.policy.mode,
            },
            resolved_contract,
            {},
        )

    ordered = sorted(raw_positions_by_strategy.keys())
    aligned_index = None
    for key in ordered:
        idx = raw_positions_by_strategy[key].index
        aligned_index = idx if aligned_index is None else aligned_index.union(idx)
    if aligned_index is None:
        raise ValueError("aligned_index must not be None")

    requested: Dict[str, pd.Series] = {}
    for key in ordered:
        pos = _as_float_series(raw_positions_by_strategy[key]).reindex(aligned_index).fillna(0.0)
        scale = _as_float_series(
            requested_scale_by_strategy.get(key, pd.Series(1.0, index=aligned_index))
        ).reindex(aligned_index).fillna(1.0)
        requested[key] = (pos * scale.clip(lower=0.0)).astype(float)
    policy_weights = _resolve_policy_weights(requested, ordered, resolved_contract)
    if resolved_contract.policy.mode == "deterministic_optimizer" and policy_weights:
        for key in ordered:
            requested[key] = requested[key] * float(policy_weights.get(key, 0.0))

    scale_by_strategy: Dict[str, pd.Series] = {}
    requested_gross = pd.DataFrame(requested).abs().sum(axis=1) if requested else pd.Series(0.0, index=aligned_index)

    # ----- Original allocator logic (preserved) -----
    if limits.enable_correlation_allocation and len(requested) > 1:
        try:
            df_req = pd.DataFrame(requested).fillna(0.0)
            diff = df_req.diff().fillna(0.0)
            cov = diff.cov()
            if (cov.isnull().any().any()) or len(cov) != len(requested):
                raise ValueError("invalid covariance for allocation")
            
            # Audit 3.2: Add regularization (Shrinkage) to ensure numerical stability
            # Simple constant shrinkage towards identity to prevent singular matrix
            cov_vals = cov.values
            n_assets = len(cov_vals)
            shrinkage = 0.1
            shrunk_cov = (1 - shrinkage) * cov_vals + shrinkage * np.eye(n_assets) * np.trace(cov_vals) / n_assets
            
            inv_cov = np.linalg.inv(shrunk_cov)
            ones = np.ones(len(inv_cov))
            weights = inv_cov @ ones
            weights = np.clip(weights, 0.0, None)
            total = weights.sum()
            weights = weights / total if total > 0 else np.full_like(weights, 1.0 / len(weights))
            for key, w in zip(ordered, weights):
                requested[key] = requested[key] * float(w)
        except Exception:
            _LOG.warning("Correlation allocation failed, falling back to equal-weight", exc_info=True)

    allocated = {key: s.copy() for key, s in requested.items()}

    reason_flags: dict[str, pd.Series] = {}
    def _flag(name: str, mask: pd.Series) -> None:
        nonlocal reason_flags
        reason_flags[name] = reason_flags.get(name, pd.Series(False, index=aligned_index)) | mask.reindex(aligned_index).fillna(False)

    for key in ordered:
        max_s = float(max(0.0, limits.max_strategy_gross))
        gross = allocated[key].abs()
        safe_gross = gross.replace(0.0, np.nan)
        ratio_series = (max_s / safe_gross).where(gross > max_s, 1.0)
        ratio_series = ratio_series.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(lower=0.0, upper=1.0)
        _flag("max_strategy_gross", ratio_series < 0.999999)
        allocated[key] = allocated[key] * ratio_series

    symbol_cap = float(max(0.0, limits.max_symbol_gross))
    symbol_gross = pd.DataFrame(allocated).abs().sum(axis=1) if allocated else pd.Series(0.0, index=aligned_index)
    safe_symbol_gross = symbol_gross.replace(0.0, np.nan)
    symbol_ratio_series = (symbol_cap / safe_symbol_gross).where(symbol_gross > symbol_cap, 1.0)
    symbol_ratio_series = symbol_ratio_series.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(lower=0.0, upper=1.0)
    _flag("max_symbol_gross", symbol_ratio_series < 0.999999)
    for key in ordered:
        allocated[key] = allocated[key] * symbol_ratio_series

    family_budget_hits = _apply_family_budget_caps(
        allocated,
        ordered=ordered,
        aligned_index=aligned_index,
        contract=resolved_contract,
        flag=_flag,
    )

    if limits.max_correlated_gross is not None:
        corr_cap = float(max(0.0, limits.max_correlated_gross))
        df_alloc = pd.DataFrame(allocated) if allocated else pd.DataFrame(index=aligned_index)
        net_direction = df_alloc.sum(axis=1) if not df_alloc.empty else pd.Series(0.0, index=aligned_index)
        same_dir_gross = df_alloc.abs().sum(axis=1) if not df_alloc.empty else pd.Series(0.0, index=aligned_index)
        fully_concordant = (net_direction.abs() - same_dir_gross).abs() < 1e-9
        needs_clip = fully_concordant & (same_dir_gross > corr_cap)
        safe_gross = same_dir_gross.replace(0.0, np.nan)
        corr_ratio_series = (corr_cap / safe_gross).where(needs_clip, 1.0)
        corr_ratio_series = corr_ratio_series.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(lower=0.0, upper=1.0)
        _flag("max_correlated_gross", corr_ratio_series < 0.999999)
        for key in ordered:
            allocated[key] = allocated[key] * corr_ratio_series

    if limits.max_pairwise_correlation is not None and len(allocated) > 1:
        try:
            df_alloc = pd.DataFrame({k: v for k, v in allocated.items()})
            corr_mat = df_alloc.corr().abs().fillna(0.0)
            np.fill_diagonal(corr_mat.values, 0.0)
            max_corr = float(corr_mat.values.max())

            # Determine effective limit — use stressed limit on stressed bars if provided
            if (
                limits.stressed_max_pairwise_correlation is not None
                and regime_series is not None
                and limits.stressed_regime_values
            ):
                regime_aligned = regime_series.reindex(aligned_index).astype(str)
                is_stressed = regime_aligned.isin(limits.stressed_regime_values)
                # On stressed bars, apply the tighter limit
                stressed_limit = float(limits.stressed_max_pairwise_correlation)
                normal_limit = float(limits.max_pairwise_correlation)
                if is_stressed.any() and max_corr > stressed_limit:
                    scale_factor = min(1.0, stressed_limit / max_corr)
                    _flag("stressed_pairwise_correlation", pd.Series(is_stressed & (max_corr > stressed_limit), index=aligned_index))
                    for key in ordered:
                        allocated[key] = allocated[key].where(~is_stressed, allocated[key] * scale_factor)
                # On calm bars, apply the normal limit
                if (not is_stressed).any() and max_corr > normal_limit:
                    scale_factor_calm = min(1.0, normal_limit / max_corr)
                    _flag("max_pairwise_correlation", pd.Series((~is_stressed) & (max_corr > normal_limit), index=aligned_index))
                    for key in ordered:
                        allocated[key] = allocated[key].where(is_stressed, allocated[key] * scale_factor_calm)
            else:
                if max_corr > limits.max_pairwise_correlation > 0:
                    scale_factor = min(1.0, limits.max_pairwise_correlation / max_corr)
                    _flag("max_pairwise_correlation", pd.Series(scale_factor < 0.999999, index=aligned_index))
                    for key in ordered:
                        allocated[key] = allocated[key] * scale_factor
        except Exception:
            pass

    if regime_series is not None and regime_scale_map:
        regime_aligned = regime_series.reindex(aligned_index).astype(str)
        regime_scale_vals = regime_aligned.map(regime_scale_map).fillna(1.0).clip(lower=0.0, upper=1.0)
        _flag("regime_scale", regime_scale_vals < 0.999999)
        for key in ordered:
            allocated[key] = allocated[key] * regime_scale_vals

    vol_scale_series = pd.Series(1.0, index=aligned_index)
    if limits.target_annual_vol is not None and portfolio_pnl_series is not None:
        pnl = portfolio_pnl_series.reindex(aligned_index).fillna(0.0)
        if limits.vol_estimator_mode == "ewma":
            roll_std = pnl.ewm(halflife=limits.vol_ewma_halflife_bars, adjust=False).std()
        else:  # "rolling"
            roll_std = pnl.rolling(
                window=limits.vol_window_bars,
                min_periods=min(288, limits.vol_window_bars),
            ).std()
        ann_vol = roll_std * np.sqrt(float(max(1.0, limits.bars_per_year)))
        vol_scale = (limits.target_annual_vol / ann_vol.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        vol_scale_series = vol_scale.clip(lower=0.0, upper=2.0)
        _flag("target_annual_vol", vol_scale_series < 0.999999)

    dd_scale_series = pd.Series(1.0, index=aligned_index)
    if limits.max_drawdown_limit is not None and portfolio_pnl_series is not None:
        pnl = portfolio_pnl_series.reindex(aligned_index).fillna(0.0)
        equity = (1.0 + pnl).cumprod()
        peak = equity.cummax().replace(0.0, np.nan)
        drawdown = ((peak - equity) / peak).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        dd_factor = (limits.max_drawdown_limit - drawdown) / limits.max_drawdown_limit
        dd_scale_series = dd_factor.clip(lower=0.0, upper=1.0)
        _flag("max_drawdown_limit", dd_scale_series < 0.999999)

    dynamic_overlay_series = (vol_scale_series * dd_scale_series).fillna(1.0)
    for key in ordered:
        allocated[key] = allocated[key] * dynamic_overlay_series

    if limits.portfolio_max_drawdown is not None and portfolio_pnl_series is not None:
        pnl = portfolio_pnl_series.reindex(aligned_index).fillna(0.0)
        equity = (1.0 + pnl).cumprod()
        peak = equity.cummax().replace(0.0, np.nan)
        drawdown = ((peak - equity) / peak).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        reject_mask = drawdown > limits.portfolio_max_drawdown
        _flag("portfolio_max_drawdown", reject_mask)
        for key in ordered:
            allocated[key] = allocated[key].mask(reject_mask, 0.0)

    if limits.symbol_max_exposure is not None:
        symbol_cap_exp = float(max(0.0, limits.symbol_max_exposure))
        symbol_gross = pd.DataFrame(allocated).abs().sum(axis=1) if allocated else pd.Series(0.0, index=aligned_index)
        reject_mask = symbol_gross > symbol_cap_exp
        _flag("symbol_max_exposure", reject_mask)
        for key in ordered:
            allocated[key] = allocated[key].mask(reject_mask, 0.0)

    if limits.portfolio_max_exposure is not None:
        portfolio_cap_exp = float(max(0.0, limits.portfolio_max_exposure))
        portfolio_gross_exp = pd.DataFrame(allocated).abs().sum(axis=1) if allocated else pd.Series(0.0, index=aligned_index)
        reject_mask = portfolio_gross_exp > portfolio_cap_exp
        _flag("portfolio_max_exposure", reject_mask)
        for key in ordered:
            allocated[key] = allocated[key].mask(reject_mask, 0.0)

    portfolio_cap = float(max(0.0, limits.max_portfolio_gross))
    portfolio_gross = pd.DataFrame(allocated).abs().sum(axis=1) if allocated else pd.Series(0.0, index=aligned_index)
    safe_portfolio_gross = portfolio_gross.replace(0.0, np.nan)
    portfolio_ratio_series = (portfolio_cap / safe_portfolio_gross).where(portfolio_gross > portfolio_cap, 1.0)
    portfolio_ratio_series = portfolio_ratio_series.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(lower=0.0, upper=1.0)
    _flag("max_portfolio_gross", portfolio_ratio_series < 0.999999)
    for key in ordered:
        allocated[key] = allocated[key] * portfolio_ratio_series

    max_new = float(max(0.0, limits.max_new_exposure_per_bar))
    for key in ordered:
        raw_alloc = allocated[key].values.astype(float, copy=False)
        clamped = _clamp_positions(raw_alloc, max_new)
        clamped_series = pd.Series(clamped, index=aligned_index)
        _flag("max_new_exposure_per_bar", (clamped_series - allocated[key]).abs() > 1e-12)
        allocated[key] = clamped_series

    allocated_gross = pd.DataFrame(allocated).abs().sum(axis=1) if allocated else pd.Series(0.0, index=aligned_index)
    req_total = float(requested_gross.sum())
    alloc_total = float(allocated_gross.sum())
    clipped_fraction = 0.0 if req_total <= 0 else float(max(0.0, (req_total - alloc_total) / req_total))

    for key in ordered:
        pos = _as_float_series(raw_positions_by_strategy[key]).reindex(aligned_index).fillna(0.0)
        denom = pos.replace(0.0, np.nan).abs()
        scale = (allocated[key].abs() / denom).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        scale_by_strategy[key] = scale.astype(float)

    diagnostics = pd.DataFrame(index=aligned_index)
    diagnostics["requested_gross"] = requested_gross.astype(float)
    diagnostics["allocated_gross"] = allocated_gross.astype(float)
    diagnostics["clip_fraction"] = np.where(
        diagnostics["requested_gross"] > 0,
        (diagnostics["requested_gross"] - diagnostics["allocated_gross"]).clip(lower=0.0) / diagnostics["requested_gross"],
        0.0,
    )
    for reason_name, mask in reason_flags.items():
        diagnostics[reason_name] = mask.astype(bool)
    if reason_flags:
        reason_cols = list(reason_flags.keys())
        diagnostics["clip_reason"] = diagnostics[reason_cols].apply(
            lambda row: ",".join(sorted([col for col in reason_cols if bool(row[col])])), axis=1
        )
    else:
        diagnostics["clip_reason"] = ""
    diagnostics["allocator_mode"] = resolved_contract.policy.mode
    diagnostics = diagnostics.reset_index().rename(columns={"index": "timestamp"})

    return AllocationDetails(
        allocated_positions_by_strategy=allocated,
        scale_by_strategy=scale_by_strategy,
        diagnostics=diagnostics,
        summary={
            "requested_gross": req_total,
            "allocated_gross": alloc_total,
            "clipped_fraction": clipped_fraction,
            "allocator_mode": resolved_contract.policy.mode,
            "policy_weights": policy_weights,
            "family_budget_hits": family_budget_hits,
        },
        contract=resolved_contract,
        policy_weights=policy_weights,
    )
