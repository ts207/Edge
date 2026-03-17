from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def sample_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "candidates_total": 0,
            "zero_validation_rows": 0,
            "zero_test_rows": 0,
            "zero_eval_rows": 0,
            "median_validation_n_obs": 0.0,
            "median_test_n_obs": 0.0,
            "median_n_obs": 0.0,
        }
    validation = pd.to_numeric(df.get("validation_n_obs", 0), errors="coerce").fillna(0)
    test = pd.to_numeric(df.get("test_n_obs", 0), errors="coerce").fillna(0)
    n_obs = pd.to_numeric(df.get("n_obs", 0), errors="coerce").fillna(0)
    return {
        "candidates_total": int(len(df)),
        "zero_validation_rows": int((validation <= 0).sum()),
        "zero_test_rows": int((test <= 0).sum()),
        "zero_eval_rows": int(((validation <= 0) & (test <= 0)).sum()),
        "median_validation_n_obs": float(validation.median()) if not validation.empty else 0.0,
        "median_test_n_obs": float(test.median()) if not test.empty else 0.0,
        "median_n_obs": float(n_obs.median()) if not n_obs.empty else 0.0,
    }


def survivor_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "survivors_total": 0,
            "median_q_value": 1.0,
            "median_q_value_by": 1.0,
            "median_estimate_bps": 0.0,
            "median_cost_bps": 0.0,
            "families_with_survivors": 0,
        }
    survivors = df[
        pd.to_numeric(df.get("is_discovery", False), errors="coerce").fillna(0).astype(bool)
    ].copy()
    if survivors.empty:
        return {
            "survivors_total": 0,
            "median_q_value": 1.0,
            "median_q_value_by": 1.0,
            "median_estimate_bps": 0.0,
            "median_cost_bps": 0.0,
            "families_with_survivors": 0,
        }
    return {
        "survivors_total": int(len(survivors)),
        "median_q_value": float(
            pd.to_numeric(survivors.get("q_value", 1.0), errors="coerce").fillna(1.0).median()
        ),
        "median_q_value_by": float(
            pd.to_numeric(survivors.get("q_value_by", 1.0), errors="coerce")
            .fillna(1.0)
            .median()
        ),
        "median_estimate_bps": float(
            pd.to_numeric(survivors.get("estimate_bps", 0.0), errors="coerce")
            .fillna(0.0)
            .median()
        ),
        "median_cost_bps": float(
            pd.to_numeric(survivors.get("resolved_cost_bps", 0.0), errors="coerce")
            .fillna(0.0)
            .median()
        ),
        "families_with_survivors": int(survivors["family_id"].nunique())
        if "family_id" in survivors.columns
        else 0,
    }


def build_false_discovery_diagnostics(combined: pd.DataFrame) -> dict[str, Any]:
    gate_rejections = pd.to_numeric(
        combined.get("rejected_by_sample_quality", pd.Series(False, index=combined.index)),
        errors="coerce",
    ).fillna(0).astype(bool)
    survivors_before_gate = pd.to_numeric(
        combined.get("is_discovery_pre_sample_quality", pd.Series(False, index=combined.index)),
        errors="coerce",
    ).fillna(0).astype(bool)
    fail_reason_counts = (
        combined.loc[gate_rejections, "sample_quality_fail_reason"].astype(str).value_counts().to_dict()
        if "sample_quality_fail_reason" in combined.columns and bool(gate_rejections.any())
        else {}
    )
    if combined.empty:
        return {
            "global": {
                "candidates_total": 0,
                "symbols_total": 0,
                "survivors_total": 0,
                "families_total": 0,
            },
            "sample_quality": sample_quality_summary(combined),
            "sample_quality_gate": {
                "survivors_before_gate": 0,
                "survivors_after_gate": 0,
                "rejected_by_sample_quality_gate": 0,
                "fail_reason_counts": {},
            },
            "survivor_quality": survivor_quality_summary(combined),
            "by_symbol": {},
        }

    by_symbol: dict[str, Any] = {}
    for symbol, sym_df in combined.groupby("symbol", sort=True):
        by_symbol[str(symbol)] = {
            "sample_quality": sample_quality_summary(sym_df),
            "sample_quality_gate": {
                "survivors_before_gate": int(
                    pd.to_numeric(
                        sym_df.get("is_discovery_pre_sample_quality", pd.Series(False, index=sym_df.index)),
                        errors="coerce",
                    )
                    .fillna(0)
                    .astype(bool)
                    .sum()
                ),
                "survivors_after_gate": int(
                    pd.to_numeric(sym_df.get("is_discovery", False), errors="coerce")
                    .fillna(0)
                    .astype(bool)
                    .sum()
                ),
                "rejected_by_sample_quality_gate": int(
                    pd.to_numeric(
                        sym_df.get("rejected_by_sample_quality", pd.Series(False, index=sym_df.index)),
                        errors="coerce",
                    )
                    .fillna(0)
                    .astype(bool)
                    .sum()
                ),
                "fail_reason_counts": (
                    sym_df.loc[
                        pd.to_numeric(
                            sym_df.get("rejected_by_sample_quality", pd.Series(False, index=sym_df.index)),
                            errors="coerce",
                        )
                        .fillna(0)
                        .astype(bool),
                        "sample_quality_fail_reason",
                    ]
                    .astype(str)
                    .value_counts()
                    .to_dict()
                    if "sample_quality_fail_reason" in sym_df.columns
                    else {}
                ),
            },
            "survivor_quality": survivor_quality_summary(sym_df),
        }

    return {
        "global": {
            "candidates_total": int(len(combined)),
            "symbols_total": int(combined["symbol"].nunique()) if "symbol" in combined.columns else 0,
            "survivors_total": int(
                pd.to_numeric(combined.get("is_discovery", False), errors="coerce")
                .fillna(0)
                .astype(bool)
                .sum()
            ),
            "families_total": int(combined["family_id"].nunique())
            if "family_id" in combined.columns
            else 0,
        },
        "sample_quality": sample_quality_summary(combined),
        "sample_quality_gate": {
            "survivors_before_gate": int(survivors_before_gate.sum()),
            "survivors_after_gate": int(
                pd.to_numeric(combined.get("is_discovery", False), errors="coerce")
                .fillna(0)
                .astype(bool)
                .sum()
            ),
            "rejected_by_sample_quality_gate": int(gate_rejections.sum()),
            "fail_reason_counts": {str(key): int(value) for key, value in fail_reason_counts.items()},
        },
        "survivor_quality": survivor_quality_summary(combined),
        "by_symbol": by_symbol,
    }


def apply_sample_quality_gates(
    candidates_df: pd.DataFrame,
    *,
    min_validation_n_obs: int,
    min_test_n_obs: int,
    min_total_n_obs: int,
) -> pd.DataFrame:
    if candidates_df.empty:
        return candidates_df.copy()
    out = candidates_df.copy()
    validation = pd.to_numeric(out.get("validation_n_obs", 0), errors="coerce").fillna(0)
    test = pd.to_numeric(out.get("test_n_obs", 0), errors="coerce").fillna(0)
    total = pd.to_numeric(out.get("n_obs", 0), errors="coerce").fillna(0)
    multiplicity_survivor = pd.to_numeric(out.get("is_discovery", False), errors="coerce").fillna(0).astype(bool)

    gate_validation = validation >= int(min_validation_n_obs)
    gate_test = test >= int(min_test_n_obs)
    gate_total = total >= int(min_total_n_obs)
    gate_sample_quality = gate_validation & gate_test & gate_total

    fail_reason = np.where(
        ~gate_validation,
        "min_validation_n_obs",
        np.where(~gate_test, "min_test_n_obs", np.where(~gate_total, "min_total_n_obs", "")),
    )

    out["gate_min_validation_n_obs"] = gate_validation.astype(bool)
    out["gate_min_test_n_obs"] = gate_test.astype(bool)
    out["gate_min_total_n_obs"] = gate_total.astype(bool)
    out["gate_sample_quality"] = gate_sample_quality.astype(bool)
    out["sample_quality_fail_reason"] = pd.Series(fail_reason, index=out.index).astype(str)
    out["is_discovery_pre_sample_quality"] = multiplicity_survivor.astype(bool)
    out["rejected_by_sample_quality"] = (multiplicity_survivor & ~gate_sample_quality).astype(bool)
    out["is_discovery"] = (multiplicity_survivor & gate_sample_quality).astype(bool)
    return out
