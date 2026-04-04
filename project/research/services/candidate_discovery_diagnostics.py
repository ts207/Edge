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
            "median_discovery_quality_score": 0.0,
            "v2_demotion_reasons": {},
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
            "median_discovery_quality_score": 0.0,
            "v2_demotion_reasons": {},
            "families_with_survivors": 0,
        }
    return {
        "survivors_total": int(len(survivors)),
        "median_q_value": float(
            pd.to_numeric(survivors.get("q_value", 1.0), errors="coerce").fillna(1.0).median()
        ),
        "median_q_value_by": float(
            pd.to_numeric(survivors.get("q_value_by", 1.0), errors="coerce").fillna(1.0).median()
        ),
        "median_estimate_bps": float(
            pd.to_numeric(survivors.get("estimate_bps", 0.0), errors="coerce").fillna(0.0).median()
        ),
        "median_cost_bps": float(
            pd.to_numeric(survivors.get("resolved_cost_bps", 0.0), errors="coerce")
            .fillna(0.0)
            .median()
        ),
        "median_discovery_quality_score": float(
            pd.to_numeric(survivors.get("discovery_quality_score", np.nan), errors="coerce")
            .median()
        ) if "discovery_quality_score" in survivors.columns else 0.0,
        "v2_demotion_reasons": (
            {str(k): int(v) for k, v in survivors["rank_primary_reason"].value_counts().to_dict().items()}
            if "rank_primary_reason" in survivors.columns
            else {}
        ),
        "families_with_survivors": int(survivors["family_id"].nunique())
        if "family_id" in survivors.columns
        else 0,
    }


def build_false_discovery_diagnostics(combined: pd.DataFrame) -> dict[str, Any]:
    gate_rejections = (
        pd.to_numeric(
            combined.get("rejected_by_sample_quality", pd.Series(False, index=combined.index)),
            errors="coerce",
        )
        .fillna(0)
        .astype(bool)
    )
    survivors_before_gate = (
        pd.to_numeric(
            combined.get("is_discovery_pre_sample_quality", pd.Series(False, index=combined.index)),
            errors="coerce",
        )
        .fillna(0)
        .astype(bool)
    )
    fail_reason_counts = (
        combined.loc[gate_rejections, "sample_quality_fail_reason"]
        .astype(str)
        .value_counts()
        .to_dict()
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
            "ledger_diagnostics": build_ledger_diagnostics(combined),
            "by_symbol": {},
        }

    by_symbol: dict[str, Any] = {}
    for symbol, sym_df in combined.groupby("symbol", sort=True):
        by_symbol[str(symbol)] = {
            "sample_quality": sample_quality_summary(sym_df),
            "sample_quality_gate": {
                "survivors_before_gate": int(
                    pd.to_numeric(
                        sym_df.get(
                            "is_discovery_pre_sample_quality", pd.Series(False, index=sym_df.index)
                        ),
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
                        sym_df.get(
                            "rejected_by_sample_quality", pd.Series(False, index=sym_df.index)
                        ),
                        errors="coerce",
                    )
                    .fillna(0)
                    .astype(bool)
                    .sum()
                ),
                "fail_reason_counts": (
                    sym_df.loc[
                        pd.to_numeric(
                            sym_df.get(
                                "rejected_by_sample_quality", pd.Series(False, index=sym_df.index)
                            ),
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
            "symbols_total": int(combined["symbol"].nunique())
            if "symbol" in combined.columns
            else 0,
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
            "fail_reason_counts": {
                str(key): int(value) for key, value in fail_reason_counts.items()
            },
        },
        "survivor_quality": survivor_quality_summary(combined),
        "ledger_diagnostics": build_ledger_diagnostics(combined),
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
    multiplicity_survivor = (
        pd.to_numeric(out.get("is_discovery", False), errors="coerce").fillna(0).astype(bool)
    )

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


# ---------------------------------------------------------------------------
# Phase 3 — Ledger diagnostics
# ---------------------------------------------------------------------------

def build_ledger_diagnostics(combined: pd.DataFrame) -> dict[str, Any]:
    """Build a diagnostics dict describing ledger-driven rank changes.

    Safe to call when ledger columns are absent (returns a minimal dict).
    """
    if combined is None or combined.empty:
        return {
            "ledger_adjustment_enabled": False,
            "lineages_covered": 0,
            "crowded_lineages": [],
            "top_burdened_candidates": [],
            "rank_demotions": [],
            "demotion_reason_counts": {},
            "lineages_with_repeated_failure": [],
            "ledger_coverage_rate": 0.0,
        }

    has_ledger = "ledger_multiplicity_penalty" in combined.columns
    has_v3 = "discovery_quality_score_v3" in combined.columns
    has_v2 = "discovery_quality_score" in combined.columns
    has_lineage = "concept_lineage_key" in combined.columns

    if not has_ledger:
        return {
            "ledger_adjustment_enabled": False,
            "lineages_covered": 0,
            "crowded_lineages": [],
            "top_burdened_candidates": [],
            "rank_demotions": [],
            "demotion_reason_counts": {},
            "lineages_with_repeated_failure": [],
            "ledger_coverage_rate": 0.0,
        }

    # Coverage: fraction of candidates with a non-null lineage key
    if has_lineage:
        lineage_col = combined["concept_lineage_key"].fillna("").astype(str)
        lineages_covered = int((lineage_col != "").sum())
        coverage_rate = float(lineages_covered / max(len(combined), 1))
        unique_lineages = lineage_col[lineage_col != ""].unique().tolist()
    else:
        lineages_covered = 0
        coverage_rate = 0.0
        unique_lineages = []

    # Crowded lineages (high prior test count)
    crowded: list[str] = []
    repeated_failure: list[str] = []
    if has_lineage and "ledger_prior_test_count" in combined.columns:
        lineage_burden = (
            combined.groupby("concept_lineage_key")["ledger_prior_test_count"]
            .max()
            .reset_index()
        )
        crowded = (
            lineage_burden[lineage_burden["ledger_prior_test_count"] >= 20]["concept_lineage_key"]
            .tolist()
        )

    if (
        has_lineage
        and "ledger_empirical_success_rate" in combined.columns
        and "ledger_prior_test_count" in combined.columns
    ):
        fail_df = combined.groupby("concept_lineage_key").agg(
            rate=("ledger_empirical_success_rate", "min"),
            tests=("ledger_prior_test_count", "max"),
        ).reset_index()
        repeated_failure = (
            fail_df[
                (fail_df["rate"] < 0.10) & (fail_df["tests"] >= 5)
            ]["concept_lineage_key"].tolist()
        )

    # Top burdened candidates (highest penalty)
    penalty_col = pd.to_numeric(combined.get("ledger_multiplicity_penalty", 0), errors="coerce").fillna(0)
    top_n = min(10, int((penalty_col > 0).sum()))
    top_burdened: list[dict] = []
    if top_n > 0:
        top_idx = penalty_col.nlargest(top_n).index
        for idx in top_idx:
            row = combined.loc[idx]
            top_burdened.append(
                {
                    "candidate_id": str(row.get("candidate_id", "")).strip(),
                    "concept_lineage_key": str(row.get("concept_lineage_key", "")),
                    "ledger_multiplicity_penalty": float(row.get("ledger_multiplicity_penalty", 0.0)),
                    "ledger_prior_test_count": int(row.get("ledger_prior_test_count", 0)),
                    "ledger_empirical_success_rate": float(row.get("ledger_empirical_success_rate", 0.0)),
                }
            )

    # Rank demotions: candidates whose v3 rank is much worse than v2 rank
    rank_demotions: list[dict] = []
    if has_v2 and has_v3:
        score_v2 = pd.to_numeric(combined.get("discovery_quality_score", np.nan), errors="coerce")
        score_v3 = pd.to_numeric(combined.get("discovery_quality_score_v3", np.nan), errors="coerce")
        valid_both = score_v2.notna() & score_v3.notna()
        if valid_both.any():
            ranked_v2 = score_v2[valid_both].rank(ascending=False, method="first").astype(int)
            ranked_v3 = score_v3[valid_both].rank(ascending=False, method="first").astype(int)
            demotion_delta = ranked_v3 - ranked_v2
            # Flag candidates demoted by 5+ positions
            big_demotions = demotion_delta[demotion_delta >= 5].nlargest(10)
            for idx, delta in big_demotions.items():
                row = combined.loc[idx]
                reason = str(row.get("demotion_reason_codes", "")).strip()
                ledger_codes = [
                    r for r in reason.split("|") if r.startswith(("crowded", "repeated", "low_empirical", "high_recent", "ledger"))
                ]
                if not ledger_codes:
                    continue
                rank_demotions.append(
                    {
                        "candidate_id": str(row.get("candidate_id", "")).strip(),
                        "v2_rank": int(ranked_v2.loc[idx]),
                        "v3_rank": int(ranked_v3.loc[idx]),
                        "demotion_delta": int(delta),
                        "demotion_reason": "|".join(ledger_codes),
                    }
                )

    # Demotion reason code counts (ledger codes only)
    demotion_counts: dict[str, int] = {}
    if "demotion_reason_codes" in combined.columns:
        all_codes: list[str] = []
        for codes_str in combined["demotion_reason_codes"].fillna("").astype(str):
            for code in codes_str.split("|"):
                code = code.strip()
                if code and code in {
                    "crowded_lineage",
                    "repeated_family_failure",
                    "low_empirical_family_success",
                    "high_recent_test_density",
                    "ledger_penalty_applied",
                }:
                    all_codes.append(code)
        for code in all_codes:
            demotion_counts[code] = demotion_counts.get(code, 0) + 1

    return {
        "ledger_adjustment_enabled": True,
        "lineages_covered": lineages_covered,
        "unique_lineage_count": len(unique_lineages),
        "crowded_lineages": crowded[:20],
        "top_burdened_candidates": top_burdened,
        "rank_demotions": rank_demotions,
        "demotion_reason_counts": demotion_counts,
        "lineages_with_repeated_failure": repeated_failure[:20],
        "ledger_coverage_rate": round(coverage_rate, 4),
    }

