"""
Workflow logic and reporting diagnostics for shrinkage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

def _refresh_phase2_metrics_after_shrinkage(
    df: pd.DataFrame,
    *,
    min_after_cost: float,
    conservative_cost_multiplier: float,
    min_sample_size_gate: int,
    require_sign_stability: bool,
    quality_floor_fallback: float,
    min_events_fallback: int,
    min_information_weight_state: float,
) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    known_gate_prefixes = (
        "ECONOMIC_GATE",
        "ECONOMIC_CONSERVATIVE",
        "STABILITY_GATE",
        "MIN_SAMPLE_SIZE_GATE",
        "STATE_INFORMATION_WEIGHT",
        "OOS_MIN_SAMPLES",
        "OOS_VALIDATION",
        "OOS_VALIDATION_TEST",
        "OOS_CONSISTENCY_STRICT",
    )

    # Apply direction rule: flip effect for SHORT direction candidates
    # This ensures economic gate checks the correct side profitability
    if "direction_rule" in out.columns:
        direction = out["direction_rule"].fillna("both").str.lower()
        direction_multiplier = np.where(direction == "short", -1.0, 1.0)
        if "effect_shrunk_state" in out.columns:
            out["effect_shrunk_state"] = (
                out["effect_shrunk_state"] * direction_multiplier
            )
        if "effect_shrunk_event" in out.columns:
            out["effect_shrunk_event"] = (
                out["effect_shrunk_event"] * direction_multiplier
            )
        if "effect_shrunk_family" in out.columns:
            out["effect_shrunk_family"] = (
                out["effect_shrunk_family"] * direction_multiplier
            )
        if "effect_raw" in out.columns:
            out["effect_raw"] = out["effect_raw"] * direction_multiplier

    out["expectancy"] = pd.to_numeric(
        out["effect_shrunk_state"], errors="coerce"
    ).fillna(pd.to_numeric(out.get("expectancy", 0.0), errors="coerce").fillna(0.0))

    resolved_cost = (
        pd.to_numeric(out.get("cost_bps_resolved", 0.0), errors="coerce").fillna(0.0)
        / 10000.0
    )
    out["after_cost_expectancy"] = out["expectancy"] - resolved_cost
    out["after_cost_expectancy_per_trade"] = out["after_cost_expectancy"]
    out["stressed_after_cost_expectancy_per_trade"] = out["expectancy"] - (
        resolved_cost * float(conservative_cost_multiplier)
    )

    out["p_value"] = (
        pd.to_numeric(
            out.get("p_value_shrunk", out.get("p_value", 1.0)), errors="coerce"
        )
        .fillna(1.0)
        .clip(0.0, 1.0)
    )
    out["p_value_for_fdr"] = (
        pd.to_numeric(out.get("p_value_for_fdr", out["p_value"]), errors="coerce")
        .fillna(out["p_value"])
        .clip(0.0, 1.0)
    )

    out["gate_economic"] = out["after_cost_expectancy"] >= float(min_after_cost)
    out["gate_economic_conservative"] = out[
        "stressed_after_cost_expectancy_per_trade"
    ] >= float(min_after_cost)
    out["gate_after_cost_positive"] = out["gate_economic"]
    out["gate_after_cost_stressed_positive"] = out["gate_economic_conservative"]
    if "gate_stability" in out.columns:
        gate_stability_col = out["gate_stability"]
    else:
        gate_stability_col = pd.Series(False, index=out.index)
    out["gate_stability"] = gate_stability_col.astype(bool)
    out["sample_size"] = (
        pd.to_numeric(out.get("sample_size", out.get("n_events", 0)), errors="coerce")
        .fillna(0)
        .astype(int)
    )
    out["n_events"] = (
        pd.to_numeric(out.get("n_events", 0), errors="coerce").fillna(0).astype(int)
    )
    out["validation_samples"] = (
        pd.to_numeric(out.get("validation_samples", 0), errors="coerce")
        .fillna(0)
        .astype(int)
    )
    out["test_samples"] = (
        pd.to_numeric(out.get("test_samples", 0), errors="coerce").fillna(0).astype(int)
    )

    validation_return = pd.to_numeric(
        out.get("mean_validation_return", np.nan), errors="coerce"
    )
    test_return = pd.to_numeric(out.get("mean_test_return", np.nan), errors="coerce")
    expectancy_sign = np.sign(pd.to_numeric(out["expectancy"], errors="coerce").fillna(0.0))
    validation_sign = np.sign(validation_return.fillna(0.0))
    test_sign = np.sign(test_return.fillna(0.0))

    out["gate_oos_min_samples"] = out["validation_samples"] > 0
    out["gate_oos_validation"] = (
        out["gate_oos_min_samples"]
        & validation_return.notna()
        & (validation_sign == expectancy_sign)
        & (validation_sign != 0.0)
    )
    out["gate_oos_validation_test"] = (
        (out["test_samples"] > 0)
        & test_return.notna()
        & (test_sign == expectancy_sign)
        & (test_sign != 0.0)
    )
    out["gate_oos_consistency_strict"] = (
        out["gate_oos_validation"] & out["gate_oos_validation_test"]
    )

    sample_gate_pass = (
        out["sample_size"] >= int(min_sample_size_gate)
        if int(min_sample_size_gate) > 0
        else pd.Series(True, index=out.index)
    )
    if "state_id" in out.columns:
        state_id_col = out["state_id"]
    else:
        state_id_col = pd.Series("", index=out.index)
    if "shrinkage_weight_state" in out.columns:
        state_weight_col = out["shrinkage_weight_state"]
    else:
        state_weight_col = pd.Series(1.0, index=out.index)
    out["gate_state_information"] = (
        state_id_col.fillna("").astype(str).str.strip() == ""
    ) | (
        pd.to_numeric(state_weight_col, errors="coerce").fillna(0.0)
        >= float(min_information_weight_state)
    )

    stability_ok = (
        out["gate_stability"]
        if require_sign_stability
        else pd.Series(True, index=out.index)
    )
    out["gate_phase2_research"] = (
        out["gate_economic_conservative"]
        & sample_gate_pass
        & out["gate_oos_min_samples"]
        & stability_ok
        & out["gate_state_information"]
    )
    out["gate_phase2_final"] = out["gate_phase2_research"]

    out["robustness_score"] = (
        out["gate_economic"].astype(float)
        + out["gate_economic_conservative"].astype(float)
        + out["gate_stability"].astype(float)
        + out["gate_state_information"].astype(float)
    ) / 4.0
    out["phase2_quality_score"] = out["robustness_score"]
    # Vectorized: build JSON string via string concat (avoids row-by-row apply)
    out["phase2_quality_components"] = (
        '{"econ":'
        + out["gate_economic"].astype(int).astype(str)
        + ',"econ_cons":'
        + out["gate_economic_conservative"].astype(int).astype(str)
        + ',"stability":'
        + out["gate_stability"].astype(int).astype(str)
        + ',"state_info":'
        + out["gate_state_information"].astype(int).astype(str)
        + "}"
    )
    out["compile_eligible_phase2_fallback"] = (
        out["phase2_quality_score"] >= float(quality_floor_fallback)
    ) & (out["n_events"] >= int(min_events_fallback))

    # Vectorized fail_reasons: strip managed gate tokens, then OR-in new failures.
    # Strip known managed prefixes from any pre-existing fail_reasons strings.
    _prior = (
        out.get("fail_reasons", pd.Series("", index=out.index)).fillna("").astype(str)
    )

    def _strip_managed(s: str) -> str:
        kept = [
            t.strip()
            for t in s.split(",")
            if t.strip() and not t.strip().startswith(known_gate_prefixes)
        ]
        return ",".join(dict.fromkeys(kept))

    _prior_stripped = _prior.map(_strip_managed)

    # Build one boolean column per managed gate failure
    _gate_flags: dict[str, pd.Series] = {
        "ECONOMIC_GATE": ~out["gate_economic"].astype(bool),
        "ECONOMIC_CONSERVATIVE": ~out["gate_economic_conservative"].astype(bool),
        "MIN_SAMPLE_SIZE_GATE": (out["sample_size"] < int(min_sample_size_gate))
        if int(min_sample_size_gate) > 0
        else pd.Series(False, index=out.index),
        "STATE_INFORMATION_WEIGHT": ~out["gate_state_information"].astype(bool),
        "OOS_MIN_SAMPLES": ~out["gate_oos_min_samples"].astype(bool),
        "OOS_VALIDATION": ~out["gate_oos_validation"].astype(bool),
        "OOS_VALIDATION_TEST": ~out["gate_oos_validation_test"].astype(bool),
        "OOS_CONSISTENCY_STRICT": ~out["gate_oos_consistency_strict"].astype(bool),
    }
    if require_sign_stability:
        _gate_flags["STABILITY_GATE"] = ~out["gate_stability"].astype(bool)

    _gate_df = pd.DataFrame(_gate_flags, index=out.index)
    _new_reasons = _gate_df.apply(
        lambda row: ",".join(col for col in _gate_df.columns if row[col]), axis=1
    )
    # Merge prior (non-managed) tokens with new gate tokens
    out["fail_reasons"] = (
        _prior_stripped.str.cat(_new_reasons.str.strip(","), sep=",", na_rep="")
        .str.strip(",")
        .str.replace(r",+", ",", regex=True)
    )
    out["promotion_track"] = np.where(
        out["gate_phase2_final"], "standard", "fallback_only"
    )
    return out
