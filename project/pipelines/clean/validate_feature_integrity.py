from __future__ import annotations
from project.core.config import get_data_root

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from project.core.feature_quality import summarize_feature_quality
from project.core.feature_schema import feature_dataset_dir_name
from project.io.utils import (
    choose_partition_dir,
    list_parquet_files,
    read_parquet,
    run_scoped_lake_path,
)
from project.specs.manifest import finalize_manifest, start_manifest
from project.eval.drift_detection import detect_feature_drift

LOGGER = logging.getLogger(__name__)


def _report_path(data_root: Path, *, run_id: str, timeframe: str) -> Path:
    return (
        data_root
        / "reports"
        / "feature_quality"
        / run_id
        / "validation"
        / f"validate_feature_integrity_{timeframe}.json"
    )


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summarize_drift_flags(symbol: str, drift_flags: List[Dict[str, float]]) -> None:
    if not drift_flags:
        return
    preview = ", ".join(flag["feature"] for flag in drift_flags[:5])
    if len(drift_flags) > 5:
        preview += ", ..."
    LOGGER.warning(
        "%s feature drift summary: %s flagged columns (%s)",
        symbol,
        len(drift_flags),
        preview,
    )


def check_nans(df: pd.DataFrame, threshold: float = 0.05) -> List[str]:
    nan_pcts = df.isna().mean()
    failing_cols = nan_pcts[nan_pcts > threshold]
    return [
        f"Column '{col}' has {pct:.2%} NaNs (threshold {threshold:.2%})"
        for col, pct in failing_cols.items()
    ]


def check_constant_values(df: pd.DataFrame) -> List[str]:
    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return []
    nunique = num_df.nunique()
    all_nan = num_df.isna().all()
    constant_cols = nunique[(nunique <= 1) & (~all_nan)].index
    return [f"Column '{col}' is constant." for col in constant_cols]


def check_outliers(df: pd.DataFrame, z_threshold: float = 10.0) -> List[str]:
    cols_to_check = [
        c
        for c in df.select_dtypes(include=[np.number]).columns
        if c not in ["timestamp", "open", "high", "low", "close", "volume"]
    ]
    if not cols_to_check:
        return []

    num_df = df[cols_to_check]
    means = num_df.mean()
    stds = num_df.std()

    valid_stds = (stds > 0.0) & np.isfinite(stds)
    cols_to_check_valid = valid_stds[valid_stds].index
    if len(cols_to_check_valid) == 0:
        return []

    num_df_valid = num_df[cols_to_check_valid]
    z_scores = (num_df_valid - means[cols_to_check_valid]) / stds[cols_to_check_valid]
    outlier_pcts = (z_scores.abs() > z_threshold).mean()

    failing_cols = outlier_pcts[outlier_pcts > 0.01]
    return [
        f"Column '{col}' has {pct:.2%} extreme outliers (> {z_threshold} sigma)"
        for col, pct in failing_cols.items()
    ]


def validate_symbol(
    data_root: Path,
    run_id: str,
    symbol: str,
    *,
    timeframe: str = "5m",
    nan_threshold: float = 0.05,
    z_threshold: float = 10.0,
    reference_distributions_path: str = "train_distributions.json",
) -> Dict[str, List[str]]:
    symbol_issues = {}
    feature_quality_summary = None

    # 1. Check cleaned bars
    bars_candidates = [
        run_scoped_lake_path(data_root, run_id, "cleaned", "perp", symbol, f"bars_{timeframe}"),
        data_root / "lake" / "cleaned" / "perp" / symbol / f"bars_{timeframe}",
    ]
    bars_dir = choose_partition_dir(bars_candidates)
    if bars_dir:
        df_bars = read_parquet(list_parquet_files(bars_dir))
        if not df_bars.empty:
            bars_issues = check_nans(df_bars, threshold=nan_threshold) + check_constant_values(
                df_bars
            )
            if bars_issues:
                symbol_issues["bars"] = bars_issues

    # 2. Check features
    feature_dataset = feature_dataset_dir_name()
    features_candidates = [
        run_scoped_lake_path(
            data_root, run_id, "features", "perp", symbol, timeframe, feature_dataset
        ),
        data_root / "lake" / "features" / "perp" / symbol / timeframe / feature_dataset,
    ]
    features_dir = choose_partition_dir(features_candidates)
    if features_dir:
        df_feats = read_parquet(list_parquet_files(features_dir))
        if not df_feats.empty:
            feature_quality_summary = summarize_feature_quality(df_feats)
            feat_issues = (
                check_nans(df_feats, threshold=nan_threshold)
                + check_constant_values(df_feats)
                + check_outliers(df_feats, z_threshold=z_threshold)
            )

            # Detect feature drift
            drift_flags = detect_feature_drift(df_feats, reference_distributions_path)
            _summarize_drift_flags(symbol, drift_flags)
            for flag in drift_flags:
                feat_issues.append(
                    f"Drift detected in '{flag['feature']}': KS p-value = {flag['p_value']:.4f}"
                )

            if feat_issues:
                symbol_issues["features"] = feat_issues
    if feature_quality_summary is not None:
        symbol_issues["feature_quality_summary"] = feature_quality_summary

    return symbol_issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Research Production Grade: Data Integrity Gate")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--nan_threshold", type=float, default=0.05)
    parser.add_argument("--z_threshold", type=float, default=10.0)
    parser.add_argument("--fail_on_issues", type=int, default=1)
    parser.add_argument("--timeframe", default="5m")
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    data_root = get_data_root()

    manifest = start_manifest(
        f"validate_feature_integrity_{args.timeframe}", args.run_id, vars(args), [], []
    )

    all_issues = {}
    for symbol in symbols:
        LOGGER.info(f"Auditing data integrity for {symbol} on {args.timeframe}...")
        issues = validate_symbol(
            data_root,
            args.run_id,
            symbol,
            timeframe=args.timeframe,
            nan_threshold=float(args.nan_threshold),
            z_threshold=float(args.z_threshold),
        )
        if issues:
            all_issues[symbol] = issues

    status = "success"
    if all_issues:
        LOGGER.warning(f"Integrity check found issues in {len(all_issues)} symbols.")
        status = "failed" if int(args.fail_on_issues) else "warning"

    report_path = _report_path(data_root, run_id=args.run_id, timeframe=args.timeframe)
    _write_report(
        report_path,
        {
            "schema_version": "feature_integrity_report_v1",
            "run_id": args.run_id,
            "timeframe": args.timeframe,
            "nan_threshold": args.nan_threshold,
            "z_threshold": args.z_threshold,
            "fail_on_issues": int(args.fail_on_issues),
            "status": status,
            "symbols": all_issues,
        },
    )

    finalize_manifest(
        manifest,
        status,
        stats={
            "symbols_with_issues": len(all_issues),
            "report_path": str(report_path),
            "details": all_issues,
        },
    )
    return 1 if all_issues and int(args.fail_on_issues) else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
