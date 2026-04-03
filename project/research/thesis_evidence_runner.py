from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from project.core.config import get_data_root
from project.events.governance import get_event_governance_metadata
from project.io.utils import list_parquet_files, resolve_raw_dataset_dir
from project.spec_registry.loaders import repo_root

POLICY_PATH = repo_root() / "spec" / "promotion" / "founding_thesis_eval_policy.yaml"
DOCS_DIR = repo_root() / "docs" / "generated"


@dataclass(frozen=True)
class FoundingThesisSpec:
    candidate_id: str
    event_type: str
    detector_kind: str
    symbols: tuple[str, ...]
    horizons: tuple[int, ...]
    payoff_mode: str
    fees_bps: float
    params: dict[str, Any]
    notes: str = ""
    event_contract_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EventSplit:
    validation_values: pd.Series
    test_values: pd.Series
    split_definition: dict[str, str]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_founding_thesis_eval_policy(path: str | Path | None = None) -> dict[str, Any]:
    policy_path = Path(path) if path is not None else POLICY_PATH
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Founding thesis eval policy must decode to a mapping")
    return payload


def _policy_specs(path: str | Path | None = None) -> tuple[FoundingThesisSpec, ...]:
    payload = load_founding_thesis_eval_policy(path)
    rows = payload.get("founding_theses", [])
    specs: list[FoundingThesisSpec] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        specs.append(
            FoundingThesisSpec(
                candidate_id=str(row.get("candidate_id", "")).strip(),
                event_type=str(row.get("event_type", "")).strip().upper(),
                detector_kind=str(row.get("detector_kind", "")).strip().lower(),
                symbols=tuple(str(token).strip().upper() for token in row.get("symbols", []) if str(token).strip()),
                horizons=tuple(int(token) for token in row.get("horizons", []) if int(token) > 0),
                payoff_mode=str(row.get("payoff_mode", "absolute_return")).strip().lower(),
                fees_bps=float(row.get("fees_bps", 0.0) or 0.0),
                params=dict(row.get("params", {}) or {}),
                notes=str(row.get("notes", "")).strip(),
                event_contract_ids=tuple(
                    str(token).strip().upper()
                    for token in row.get("event_contract_ids", [])
                    if str(token).strip()
                ),
            )
        )
    return tuple(spec for spec in specs if spec.candidate_id and spec.event_type and spec.detector_kind and spec.symbols and spec.horizons)


def _load_raw_dataset(symbol: str, dataset: str, *, data_root: Path) -> pd.DataFrame:
    dataset_dir = resolve_raw_dataset_dir(data_root, market="perp", symbol=symbol, dataset=dataset)
    if dataset_dir is None:
        return pd.DataFrame()
    files = list_parquet_files(dataset_dir)
    if not files:
        return pd.DataFrame()
    frames = [pd.read_parquet(file_path) for file_path in files]
    frame = pd.concat(frames, ignore_index=True)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return frame


def _latest_feature_schema_dir(
    data_root: Path,
    *,
    symbol: str,
    timeframe: str = "5m",
    schema_version: str = "feature_schema_v2",
) -> Path | None:
    runs_root = data_root / "lake" / "runs"
    if not runs_root.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    pattern = f"features/perp/{symbol}/{timeframe}/features_{schema_version}"
    for run_dir in runs_root.iterdir():
        candidate = run_dir / pattern
        if candidate.exists() and candidate.is_dir():
            try:
                score = candidate.stat().st_mtime
            except OSError:
                score = 0.0
            candidates.append((score, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _load_feature_dataset(symbol: str, *, data_root: Path, timeframe: str = "5m") -> pd.DataFrame:
    feature_dir = _latest_feature_schema_dir(data_root, symbol=symbol, timeframe=timeframe)
    if feature_dir is None:
        return pd.DataFrame()
    files = list_parquet_files(feature_dir)
    if not files:
        return pd.DataFrame()
    frames = [pd.read_parquet(file_path) for file_path in files]
    frame = pd.concat(frames, ignore_index=True)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return frame


def _vol_shock_events(bars: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    close = pd.to_numeric(bars["close"], errors="coerce")
    rv_window = int(params.get("rv_window", 12) or 12)
    baseline_window = int(params.get("baseline_window", 288) or 288)
    shock_quantile = float(params.get("shock_quantile", 0.95) or 0.95)
    logret = np.log(close / close.shift(1))
    realized_vol = np.sqrt(logret.pow(2).rolling(rv_window, min_periods=rv_window).mean())
    base_min_periods = min(baseline_window, max(rv_window * 2, baseline_window // 2, 12))
    threshold_min_periods = min(baseline_window, max(rv_window * 4, baseline_window // 2, 12))
    rv_base = realized_vol.shift(1).rolling(baseline_window, min_periods=base_min_periods).median()
    shock_ratio = realized_vol / rv_base.replace(0.0, np.nan)
    threshold = shock_ratio.shift(1).rolling(baseline_window, min_periods=threshold_min_periods).quantile(shock_quantile)
    onset = (shock_ratio.shift(1) < threshold.shift(1)) & (shock_ratio >= threshold)
    return onset.fillna(False).astype(bool)


def _liquidity_vacuum_events(bars: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    close = pd.to_numeric(bars["close"], errors="coerce")
    high = pd.to_numeric(bars["high"], errors="coerce")
    low = pd.to_numeric(bars["low"], errors="coerce")
    volume = pd.to_numeric(bars["volume"], errors="coerce")
    shock_quantile = float(params.get("shock_quantile", 0.95) or 0.95)
    shock_window = int(params.get("shock_window", 288) or 288)
    volume_window = int(params.get("volume_window", 36) or 36)
    vol_ratio_floor = float(params.get("vol_ratio_floor", 0.90) or 0.90)
    range_multiplier = float(params.get("range_multiplier", 1.10) or 1.10)
    lookahead_bars = int(params.get("lookahead_bars", 3) or 3)
    min_vacuum_bars = int(params.get("min_vacuum_bars", 1) or 1)

    abs_return = (close / close.shift(1) - 1.0).abs()
    shock_min_periods = min(shock_window, max(shock_window // 2, 12))
    shock_threshold = abs_return.shift(1).rolling(shock_window, min_periods=shock_min_periods).quantile(shock_quantile)
    shock_onset = (abs_return >= shock_threshold) & (abs_return.shift(1) < shock_threshold.shift(1))

    volume_min_periods = min(volume_window, max(volume_window // 2, 6))
    volume_median = volume.shift(1).rolling(volume_window, min_periods=volume_min_periods).median()
    vol_ratio = volume / volume_median.replace(0.0, np.nan)
    range_pct = (high - low) / close.replace(0.0, np.nan)
    range_med = range_pct.shift(1).rolling(volume_window, min_periods=volume_min_periods).median()
    vacuum_bar = (vol_ratio < vol_ratio_floor) & (range_pct > range_multiplier * range_med)
    future_count = sum(vacuum_bar.shift(-offset).eq(True).astype(np.int8) for offset in range(1, lookahead_bars + 1))
    return (shock_onset & (future_count >= min_vacuum_bars)).fillna(False).astype(bool)


def _liquidation_cascade_events(bars: pd.DataFrame, funding: pd.DataFrame, open_interest: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    close = pd.to_numeric(bars["close"], errors="coerce")
    abs_return = (close / close.shift(1) - 1.0).abs()
    shock_quantile = float(params.get("shock_quantile", 0.975) or 0.975)
    shock_window = int(params.get("shock_window", 288) or 288)
    oi_window = int(params.get("oi_window", 12) or 12)
    oi_drop_quantile = float(params.get("oi_drop_quantile", 0.05) or 0.05)
    funding_window = int(params.get("funding_window", 720) or 720)
    funding_z = float(params.get("funding_z", 1.5) or 1.5)

    aligned_funding = (
        funding.set_index("timestamp")["funding_rate"].reindex(bars["timestamp"]).ffill().astype(float).reset_index(drop=True)
    )
    aligned_oi = (
        open_interest.set_index("timestamp")["sum_open_interest_value"].reindex(bars["timestamp"]).ffill().astype(float).reset_index(drop=True)
    )
    oi_change = aligned_oi.pct_change(oi_window)
    shock_min_periods = min(shock_window, max(shock_window // 2, 12))
    oi_floor = oi_change.shift(1).rolling(shock_window, min_periods=shock_min_periods).quantile(oi_drop_quantile)
    funding_min_periods = min(funding_window, max(funding_window // 4, 24))
    funding_median = aligned_funding.rolling(funding_window, min_periods=funding_min_periods).median()
    funding_std = aligned_funding.rolling(funding_window, min_periods=funding_min_periods).std()
    funding_score = (aligned_funding - funding_median) / funding_std.replace(0.0, np.nan)
    shock_threshold = abs_return.shift(1).rolling(shock_window, min_periods=shock_min_periods).quantile(shock_quantile)
    return ((abs_return >= shock_threshold) & (oi_change <= oi_floor) & (funding_score.abs() >= funding_z)).fillna(False).astype(bool)


def _liquidation_cascade_feature_proxy_events(features: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    close = pd.to_numeric(features.get("close"), errors="coerce")
    funding_rate = pd.to_numeric(features.get("funding_rate_scaled"), errors="coerce")
    depth_depletion = pd.to_numeric(features.get("micro_depth_depletion"), errors="coerce")
    spread_z = pd.to_numeric(features.get("spread_zscore"), errors="coerce").abs()
    if close is None or funding_rate is None or depth_depletion is None or spread_z is None:
        return pd.Series(False, index=features.index, dtype=bool)

    shock_quantile = float(params.get("shock_quantile", 0.97) or 0.97)
    shock_window = int(params.get("shock_window", 288) or 288)
    funding_quantile = float(params.get("funding_quantile", 0.80) or 0.80)
    depth_quantile = float(params.get("depth_quantile", 0.80) or 0.80)
    spread_quantile = float(params.get("spread_quantile", 0.80) or 0.80)
    cooldown_bars = int(params.get("cooldown_bars", 12) or 12)
    min_funding_abs = float(params.get("min_funding_abs", 0.0005) or 0.0005)
    min_depth_depletion = float(params.get("min_depth_depletion", 0.60) or 0.60)
    min_spread_z = float(params.get("min_spread_z", 3.0) or 3.0)

    abs_return = (close / close.shift(1) - 1.0).abs()
    min_periods = max(24, min(shock_window, shock_window // 2))
    shock_floor = abs_return.shift(1).rolling(shock_window, min_periods=min_periods).quantile(shock_quantile)
    funding_abs = funding_rate.abs()
    funding_floor = funding_abs.shift(1).rolling(shock_window, min_periods=min_periods).quantile(funding_quantile)
    funding_floor = funding_floor.fillna(min_funding_abs).clip(lower=min_funding_abs)
    depth_floor = depth_depletion.shift(1).rolling(shock_window, min_periods=min_periods).quantile(depth_quantile)
    depth_floor = depth_floor.fillna(min_depth_depletion).clip(lower=min_depth_depletion)
    spread_floor = spread_z.shift(1).rolling(shock_window, min_periods=min_periods).quantile(spread_quantile)
    spread_floor = spread_floor.fillna(min_spread_z).clip(lower=min_spread_z)

    raw = (
        (abs_return >= shock_floor)
        & (funding_abs >= funding_floor)
        & (depth_depletion >= depth_floor)
        & (spread_z >= spread_floor)
    ).fillna(False)
    onset = (raw & ~raw.shift(1, fill_value=False)).astype(bool)
    mask = pd.Series(False, index=features.index, dtype=bool)
    last_idx = -cooldown_bars - 1
    for idx in np.flatnonzero(onset.to_numpy(dtype=bool)):
        if idx - last_idx < cooldown_bars:
            continue
        mask.iloc[idx] = True
        last_idx = int(idx)
    return mask


def _event_mask_for_kind(
    kind: str,
    bars: pd.DataFrame,
    params: Mapping[str, Any],
    *,
    funding: pd.DataFrame | None = None,
    open_interest: pd.DataFrame | None = None,
) -> pd.Series:
    token = str(kind).strip().lower()
    if token == "vol_shock":
        return _vol_shock_events(bars, params)
    if token == "liquidity_vacuum":
        return _liquidity_vacuum_events(bars, params)
    if token == "liquidation_cascade":
        if funding is None or open_interest is None or funding.empty or open_interest.empty:
            return pd.Series(False, index=bars.index, dtype=bool)
        return _liquidation_cascade_events(bars, funding, open_interest, params)
    raise ValueError(f"Unsupported event kind for paired confirmation: {kind}")


def _basis_disloc_events(features: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    basis_zscore = pd.to_numeric(features.get("basis_zscore"), errors="coerce")
    basis_bps = pd.to_numeric(features.get("basis_bps"), errors="coerce")
    if basis_zscore is None or basis_bps is None:
        return pd.Series(False, index=features.index, dtype=bool)
    z_threshold = float(params.get("z_threshold", 5.0) or 5.0)
    min_basis_bps = float(params.get("min_basis_bps", 10.0) or 10.0)
    cooldown_bars = int(params.get("cooldown_bars", 12) or 12)
    raw = (basis_zscore.abs() >= z_threshold) & (basis_bps.abs() >= min_basis_bps)
    onset = (raw.fillna(False) & ~raw.fillna(False).shift(1, fill_value=False)).astype(bool)
    mask = pd.Series(False, index=features.index, dtype=bool)
    last_idx = -cooldown_bars - 1
    for idx in np.flatnonzero(onset.to_numpy(dtype=bool)):
        if idx - last_idx < cooldown_bars:
            continue
        mask.iloc[idx] = True
        last_idx = int(idx)
    return mask


def _fnd_disloc_events(features: pd.DataFrame, params: Mapping[str, Any]) -> pd.Series:
    basis_mask = _basis_disloc_events(features, params)
    funding_rate = pd.to_numeric(features.get("funding_rate_scaled"), errors="coerce")
    basis_bps = pd.to_numeric(features.get("basis_bps"), errors="coerce")
    if funding_rate is None or basis_bps is None:
        return pd.Series(False, index=features.index, dtype=bool)
    funding_abs = funding_rate.abs()
    lookback_window = int(params.get("lookback_window", 288) or 288)
    min_periods = max(24, min(lookback_window, lookback_window // 2))
    funding_quantile = float(params.get("funding_quantile", 0.95) or 0.95)
    threshold_bps = float(params.get("threshold_bps", 2.0) or 2.0) / 10_000.0
    funding_floor = funding_abs.shift(1).rolling(lookback_window, min_periods=min_periods).quantile(funding_quantile)
    funding_floor = funding_floor.fillna(threshold_bps).clip(lower=threshold_bps)
    funding_extreme = (funding_abs >= funding_floor).fillna(False)
    sign_align = (np.sign(basis_bps.fillna(0.0)) == np.sign(funding_rate.fillna(0.0))).astype(bool)
    alignment_window = int(params.get("alignment_window", 3) or 3)
    basis_active = basis_mask.rolling(window=alignment_window, min_periods=1).max().astype(bool)
    return (basis_active & funding_extreme & sign_align).fillna(False).astype(bool)


def _paired_confirmation_events(
    bars: pd.DataFrame,
    params: Mapping[str, Any],
    *,
    funding: pd.DataFrame | None = None,
    open_interest: pd.DataFrame | None = None,
) -> pd.Series:
    trigger_kind = str(params.get("trigger_kind", "vol_shock")).strip().lower()
    confirm_kind = str(params.get("confirm_kind", "liquidity_vacuum")).strip().lower()
    trigger_params = params.get("trigger_params", {}) if isinstance(params.get("trigger_params", {}), Mapping) else {}
    confirm_params = params.get("confirm_params", {}) if isinstance(params.get("confirm_params", {}), Mapping) else {}
    confirmation_window = int(params.get("confirmation_window_bars", 3) or 3)
    require_confirmation_after_trigger = bool(params.get("require_confirmation_after_trigger", True))

    trigger_mask = _event_mask_for_kind(
        trigger_kind,
        bars,
        trigger_params,
        funding=funding,
        open_interest=open_interest,
    )
    confirm_mask = _event_mask_for_kind(
        confirm_kind,
        bars,
        confirm_params,
        funding=funding,
        open_interest=open_interest,
    )

    paired = pd.Series(False, index=bars.index, dtype=bool)
    trigger_idx = np.flatnonzero(trigger_mask.to_numpy(dtype=bool))
    confirm_idx = np.flatnonzero(confirm_mask.to_numpy(dtype=bool))
    if trigger_idx.size == 0 or confirm_idx.size == 0:
        return paired
    for idx in trigger_idx:
        if require_confirmation_after_trigger:
            lo, hi = idx, idx + confirmation_window
        else:
            lo, hi = idx - confirmation_window, idx + confirmation_window
        if np.any((confirm_idx >= max(0, lo)) & (confirm_idx <= hi)):
            paired.iloc[idx] = True
    return paired


def _detect_events(spec: FoundingThesisSpec, bars: pd.DataFrame, funding: pd.DataFrame | None = None, open_interest: pd.DataFrame | None = None) -> pd.Series:
    if spec.detector_kind == "basis_disloc":
        return _basis_disloc_events(bars, spec.params)
    if spec.detector_kind == "fnd_disloc":
        return _fnd_disloc_events(bars, spec.params)
    if spec.detector_kind == "vol_shock":
        return _vol_shock_events(bars, spec.params)
    if spec.detector_kind == "liquidity_vacuum":
        return _liquidity_vacuum_events(bars, spec.params)
    if spec.detector_kind == "liquidation_cascade":
        if funding is None or open_interest is None or funding.empty or open_interest.empty:
            if {"micro_depth_depletion", "spread_zscore", "funding_rate_scaled", "close"} <= set(bars.columns):
                return _liquidation_cascade_feature_proxy_events(bars, spec.params)
            return pd.Series(False, index=bars.index, dtype=bool)
        return _liquidation_cascade_events(bars, funding, open_interest, spec.params)
    if spec.detector_kind in {"vol_shock_liquidity_confirm", "paired_confirmation"}:
        return _paired_confirmation_events(bars, spec.params, funding=funding, open_interest=open_interest)
    raise ValueError(f"Unsupported detector kind: {spec.detector_kind}")


def _payoff_series(bars: pd.DataFrame, *, horizon: int, payoff_mode: str) -> pd.Series:
    close = pd.to_numeric(bars["close"], errors="coerce")
    future_return = close.shift(-horizon) / close - 1.0
    if payoff_mode == "absolute_return":
        return future_return.abs() * 10_000.0
    if payoff_mode == "directional_follow_through":
        direction = np.sign(close / close.shift(1) - 1.0)
        return direction * future_return * 10_000.0
    raise ValueError(f"Unsupported payoff mode: {payoff_mode}")


def _ttest_greater(values: Sequence[float]) -> float | None:
    array = np.asarray([float(value) for value in values if math.isfinite(float(value))], dtype=float)
    if array.size < 5:
        return None
    try:
        result = stats.ttest_1samp(array, 0.0, alternative="greater")
    except Exception:
        return None
    pvalue = float(result.pvalue)
    if not math.isfinite(pvalue):
        return None
    return pvalue


def _negative_control_pass_rate(values: Sequence[float], baseline: pd.Series, sample_size: int, *, seed: int = 7, iterations: int = 200) -> float | None:
    actual = np.asarray([float(value) for value in values if math.isfinite(float(value))], dtype=float)
    if actual.size < 5 or sample_size < 5:
        return None
    available = baseline.dropna().astype(float)
    if len(available) <= sample_size:
        return None
    rng = np.random.default_rng(seed)
    actual_mean = float(actual.mean())
    sampled_means: list[float] = []
    values_np = available.to_numpy(dtype=float)
    for _ in range(iterations):
        idx = rng.choice(len(values_np), size=sample_size, replace=False)
        sampled_means.append(float(values_np[idx].mean()))
    return float(np.mean(np.asarray(sampled_means) >= actual_mean))


def _stability_score(validation_values: Sequence[float], test_values: Sequence[float]) -> float:
    validation = np.asarray([float(value) for value in validation_values if math.isfinite(float(value))], dtype=float)
    test = np.asarray([float(value) for value in test_values if math.isfinite(float(value))], dtype=float)
    if validation.size == 0 or test.size == 0:
        return 0.0
    validation_mean = float(validation.mean())
    test_mean = float(test.mean())
    sign_consistency = 1.0 if validation_mean >= 0.0 and test_mean >= 0.0 else 0.0
    denominator = abs(validation_mean) + abs(test_mean) + 1e-9
    closeness = 1.0 - min(1.0, abs(validation_mean - test_mean) / denominator)
    return float(max(0.0, min(1.0, 0.5 * sign_consistency + 0.5 * closeness)))


def _session_confounder(event_times: pd.Series, payoff_values: pd.Series) -> dict[str, Any]:
    event_hours = event_times.dt.hour
    asia = payoff_values[(event_hours >= 0) & (event_hours < 8)].dropna().astype(float)
    rest = payoff_values[~((event_hours >= 0) & (event_hours < 8))].dropna().astype(float)
    if len(asia) == 0 or len(rest) == 0:
        return {"available": False}
    gap = float(abs(float(asia.mean()) - float(rest.mean())))
    baseline = max(abs(float(payoff_values.dropna().mean())), 1e-9)
    return {
        "available": True,
        "asia_mean_bps": float(asia.mean()),
        "non_asia_mean_bps": float(rest.mean()),
        "gap_bps": gap,
        "passed": bool(gap <= baseline),
    }


def _vol_regime_confounder(vol_series: pd.Series, payoff_values: pd.Series) -> dict[str, Any]:
    aligned_vol = pd.to_numeric(vol_series.reindex(payoff_values.index), errors="coerce")
    median_vol = float(aligned_vol.median()) if aligned_vol.notna().any() else float("nan")
    if not math.isfinite(median_vol):
        return {"available": False}
    high = payoff_values[aligned_vol >= median_vol].dropna().astype(float)
    low = payoff_values[aligned_vol < median_vol].dropna().astype(float)
    if len(high) == 0 or len(low) == 0:
        return {"available": False}
    gap = float(abs(float(high.mean()) - float(low.mean())))
    baseline = max(abs(float(payoff_values.dropna().mean())), 1e-9)
    return {
        "available": True,
        "high_vol_mean_bps": float(high.mean()),
        "low_vol_mean_bps": float(low.mean()),
        "gap_bps": gap,
        "passed": bool(gap <= baseline * 1.5),
    }


def _split_event_sample(event_times: pd.Series, event_values: pd.Series, *, min_split_samples: int = 10) -> EventSplit | None:
    aligned_times = pd.to_datetime(event_times, utc=True, errors="coerce")
    aligned_values = pd.to_numeric(event_values, errors="coerce")
    valid_mask = aligned_times.notna() & aligned_values.notna()
    if not bool(valid_mask.any()):
        return None
    aligned_times = aligned_times.loc[valid_mask]
    aligned_values = aligned_values.loc[valid_mask].astype(float)

    years = aligned_times.dt.year
    validation_values = aligned_values[years <= 2021]
    test_values = aligned_values[years >= 2022]
    if len(validation_values) >= min_split_samples and len(test_values) >= min_split_samples:
        return EventSplit(
            validation_values=validation_values,
            test_values=test_values,
            split_definition={
                "split_scheme_id": "calendar_year_holdout_2022",
                "validation_window": "2021",
                "test_window": "2022",
            },
        )

    ordered_index = aligned_times.sort_values(kind="mergesort").index
    ordered_times = aligned_times.loc[ordered_index]
    ordered_values = aligned_values.loc[ordered_index]
    total = len(ordered_values)
    if total < max(20, min_split_samples * 2):
        return None
    split_at = max(min_split_samples, int(math.floor(total * 0.70)))
    split_at = min(split_at, total - min_split_samples)
    if split_at < min_split_samples or (total - split_at) < min_split_samples:
        return None
    validation_values = ordered_values.iloc[:split_at]
    test_values = ordered_values.iloc[split_at:]
    return EventSplit(
        validation_values=validation_values,
        test_values=test_values,
        split_definition={
            "split_scheme_id": "chronological_holdout_70_30",
            "validation_window": f"{ordered_times.iloc[0].isoformat()}..{ordered_times.iloc[split_at - 1].isoformat()}",
            "test_window": f"{ordered_times.iloc[split_at].isoformat()}..{ordered_times.iloc[-1].isoformat()}",
        },
    )


def _assemble_bundle(
    spec: FoundingThesisSpec,
    symbol: str,
    bars: pd.DataFrame,
    event_mask: pd.Series,
    horizon: int,
    *,
    input_mode: str = "raw_market_data",
) -> dict[str, Any] | None:
    payoff = _payoff_series(bars, horizon=horizon, payoff_mode=spec.payoff_mode)
    event_values = payoff[event_mask].dropna().astype(float)
    if len(event_values) < 20:
        return None
    event_times = bars.loc[event_mask, "timestamp"].loc[event_values.index]
    split = _split_event_sample(event_times, event_values)
    if split is None:
        return None
    validation_values = split.validation_values
    test_values = split.test_values

    gross_mean = float(event_values.mean())
    net_expectancy = gross_mean - spec.fees_bps
    q_value = _ttest_greater(test_values.tolist())
    stability = _stability_score(validation_values.tolist(), test_values.tolist())
    baseline_payoff = payoff.dropna().astype(float)
    neg_rate = _negative_control_pass_rate(event_values.tolist(), baseline_payoff, len(event_values))

    close = pd.to_numeric(bars["close"], errors="coerce")
    realized_vol = np.sqrt(np.log(close / close.shift(1)).pow(2).rolling(12, min_periods=12).mean())
    session_check = _session_confounder(event_times.reset_index(drop=True), event_values.reset_index(drop=True))
    regime_check = _vol_regime_confounder(realized_vol, payoff[event_mask])
    effect_pvalue = _ttest_greater(event_values.tolist())

    governance = get_event_governance_metadata(spec.event_type)
    event_family = str(governance.get("canonical_family", spec.event_type)).strip().upper() or spec.event_type
    event_contract_ids = list(spec.event_contract_ids) if spec.event_contract_ids else [spec.event_type]
    metadata_event_family = event_contract_ids[0] if event_contract_ids else event_family
    return {
        "candidate_id": spec.candidate_id,
        "event_type": spec.event_type,
        "event_family": metadata_event_family,
        "symbol": symbol,
        "sample_definition": {
            "n_events": int(len(event_values)),
            "validation_samples": int(len(validation_values)),
            "test_samples": int(len(test_values)),
            "symbol": symbol,
            "horizon_bars": int(horizon),
            "start": str(event_times.min()),
            "end": str(event_times.max()),
        },
        "split_definition": split.split_definition,
        "effect_estimates": {
            "estimate_bps": gross_mean,
            "validation_mean_bps": float(validation_values.mean()),
            "test_mean_bps": float(test_values.mean()),
            "payoff_mode": spec.payoff_mode,
        },
        "cost_robustness": {
            "fees_bps": float(spec.fees_bps),
            "net_expectancy_bps": net_expectancy,
            "gross_expectancy_bps": gross_mean,
        },
        "uncertainty_estimates": {
            "q_value": q_value,
            "effect_p_value": effect_pvalue,
        },
        "stability_tests": {
            "stability_score": stability,
            "validation_mean_bps": float(validation_values.mean()),
            "test_mean_bps": float(test_values.mean()),
            "validation_test_gap_bps": float(abs(float(validation_values.mean()) - float(test_values.mean()))),
        },
        "falsification_results": {
            "negative_control_pass_rate": neg_rate,
            "session_transition": session_check,
            "realized_vol_regime": regime_check,
        },
        "multiplicity_adjustment": {
            "correction_method": "single_test_founding_thesis",
            "adjusted_q_value": q_value,
        },
        "metadata": {
            "has_realized_oos_path": bool(len(test_values) >= 20 and float(test_values.mean()) > 0.0),
            "thesis_id": spec.candidate_id,
            "event_contract_ids": event_contract_ids,
            "thesis_contract_id": spec.candidate_id,
            "thesis_contract_ids": [spec.candidate_id],
            "input_symbols": list(spec.symbols),
            "input_mode": input_mode,
            "notes": spec.notes,
        },
    }


def _select_best_horizon(spec: FoundingThesisSpec, symbol_frames: Sequence[tuple[str, pd.DataFrame, pd.Series, str]]) -> int:
    best_horizon = spec.horizons[0]
    best_score = float("-inf")
    for horizon in spec.horizons:
        validation_values: list[float] = []
        for _symbol, bars, event_mask, _input_mode in symbol_frames:
            payoff = _payoff_series(bars, horizon=horizon, payoff_mode=spec.payoff_mode)
            event_values = payoff[event_mask].dropna().astype(float)
            if event_values.empty:
                continue
            event_times = bars.loc[event_mask, "timestamp"].loc[event_values.index]
            split = _split_event_sample(event_times, event_values)
            if split is None:
                continue
            validation_values.extend(float(value) for value in split.validation_values.tolist())
        if not validation_values:
            continue
        score = float(np.mean(validation_values))
        if score > best_score:
            best_score = score
            best_horizon = horizon
    return int(best_horizon)


def build_founding_thesis_evidence(*, policy_path: str | Path | None = None, data_root: str | Path | None = None, docs_dir: str | Path | None = None) -> dict[str, Path]:
    resolved_data_root = Path(data_root) if data_root is not None else Path(get_data_root())
    resolved_docs = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_DIR)
    policy = load_founding_thesis_eval_policy(policy_path)
    specs = _policy_specs(policy_path)
    summary_rows: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []

    for spec in specs:
        symbol_frames: list[tuple[str, pd.DataFrame, pd.Series, str]] = []
        missing_inputs = False
        for symbol in spec.symbols:
            if spec.detector_kind in {"basis_disloc", "fnd_disloc"}:
                bars = _load_feature_dataset(symbol, data_root=resolved_data_root)
                input_mode = "feature_schema"
            elif spec.detector_kind == "liquidation_cascade":
                bars = _load_raw_dataset(symbol, "ohlcv_5m", data_root=resolved_data_root)
                input_mode = "raw_market_data"
                if bars.empty:
                    feature_bars = _load_feature_dataset(symbol, data_root=resolved_data_root)
                    if feature_bars.empty:
                        missing_inputs = True
                        continue
                    bars = feature_bars
                    input_mode = "feature_schema_proxy"
            else:
                bars = _load_raw_dataset(symbol, "ohlcv_5m", data_root=resolved_data_root)
                input_mode = "raw_market_data"
            if bars.empty:
                missing_inputs = True
                continue
            needs_flow_inputs = spec.detector_kind in {"liquidation_cascade", "paired_confirmation"}
            funding = _load_raw_dataset(symbol, "funding", data_root=resolved_data_root) if needs_flow_inputs else None
            open_interest = _load_raw_dataset(symbol, "open_interest", data_root=resolved_data_root) if needs_flow_inputs else None
            if spec.detector_kind == "liquidation_cascade" and ((funding is None or funding.empty) or (open_interest is None or open_interest.empty)):
                feature_bars = _load_feature_dataset(symbol, data_root=resolved_data_root)
                if feature_bars.empty:
                    missing_inputs = True
                    continue
                bars = feature_bars
                funding = None
                open_interest = None
                input_mode = "feature_schema_proxy"
            event_mask = _detect_events(spec, bars, funding=funding, open_interest=open_interest)
            symbol_frames.append((symbol, bars, event_mask, input_mode))
        if missing_inputs and not symbol_frames:
            unsupported.append({
                "candidate_id": spec.candidate_id,
                "reason": "required_input_dataset_missing",
            })
            continue
        if not symbol_frames:
            unsupported.append({"candidate_id": spec.candidate_id, "reason": "no_supported_symbol_frames"})
            continue
        chosen_horizon = _select_best_horizon(spec, symbol_frames)
        promotion_dir = _ensure_dir(resolved_data_root / "reports" / "promotions" / spec.candidate_id)
        bundles: list[dict[str, Any]] = []
        total_events = 0
        for symbol, bars, event_mask, input_mode in symbol_frames:
            bundle = _assemble_bundle(spec, symbol, bars, event_mask, chosen_horizon, input_mode=input_mode)
            if bundle is None:
                continue
            bundles.append(bundle)
            total_events += int(bundle["sample_definition"]["n_events"])
        if not bundles:
            unsupported.append({"candidate_id": spec.candidate_id, "reason": "insufficient_event_count_after_detection"})
            continue
        with (promotion_dir / "evidence_bundles.jsonl").open("w", encoding="utf-8") as handle:
            for bundle in bundles:
                handle.write(json.dumps(bundle) + "\n")
        summary_rows.append(
            {
                "candidate_id": spec.candidate_id,
                "event_type": spec.event_type,
                "symbols": "|".join(spec.symbols),
                "horizon_bars": chosen_horizon,
                "bundle_count": len(bundles),
                "sample_size_total": total_events,
                "mean_net_expectancy_bps": float(np.mean([float(bundle["cost_robustness"]["net_expectancy_bps"]) for bundle in bundles])),
            }
        )

    json_path = resolved_docs / "founding_thesis_evidence_summary.json"
    md_path = resolved_docs / "founding_thesis_evidence_summary.md"
    json_path.write_text(json.dumps({"generated": summary_rows, "unsupported": unsupported}, indent=2), encoding="utf-8")

    lines = [
        "# Founding thesis evidence summary",
        "",
        "This artifact records the first raw-data empirical bundle generation pass against the founding thesis queue.",
        "",
    ]
    notes = policy.get("notes", []) if isinstance(policy.get("notes", []), list) else []
    if notes:
        lines.extend(["## Policy notes", ""])
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.extend([
        f"- generated_theses: `{len(summary_rows)}`",
        f"- unsupported_or_skipped: `{len(unsupported)}`",
        "",
        "## Generated evidence bundles",
        "",
        "| Candidate | Event | Symbols | Horizon | Bundles | Sample size | Mean net expectancy (bps) |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for row in summary_rows:
        lines.append(
            f"| {row['candidate_id']} | {row['event_type']} | {row['symbols']} | {row['horizon_bars']} | {row['bundle_count']} | {row['sample_size_total']} | {row['mean_net_expectancy_bps']:.2f} |"
        )
    if unsupported:
        lines.extend(["", "## Unsupported or skipped", ""])
        for row in unsupported:
            lines.append(f"- `{row['candidate_id']}` — {row['reason']}")
        lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


__all__ = [
    "FoundingThesisSpec",
    "build_founding_thesis_evidence",
    "load_founding_thesis_eval_policy",
]
