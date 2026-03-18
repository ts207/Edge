from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeatureColumnQuality:
    name: str
    null_rate: float
    constant_rate: float
    outlier_rate: float
    dependency_missing_fallback_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "null_rate": float(self.null_rate),
            "constant_rate": float(self.constant_rate),
            "outlier_rate": float(self.outlier_rate),
            "dependency_missing_fallback_rate": float(self.dependency_missing_fallback_rate),
        }


def summarize_feature_quality(
    frame: pd.DataFrame,
    *,
    exclude: set[str] | None = None,
    z_threshold: float = 10.0,
) -> dict[str, Any]:
    excluded = {"timestamp", "symbol"}
    if exclude:
        excluded |= set(exclude)

    numeric_cols = [
        col
        for col in frame.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(frame[col])
    ]
    per_feature: dict[str, dict[str, Any]] = {}
    null_flag_count = 0
    constant_flag_count = 0
    outlier_flag_count = 0

    for col in sorted(numeric_cols):
        series = pd.to_numeric(frame[col], errors="coerce")
        null_rate = float(series.isna().mean()) if len(series) else 0.0
        non_null = series.dropna()
        constant_rate = 1.0 if (not non_null.empty and int(non_null.nunique()) <= 1) else 0.0
        outlier_rate = 0.0
        if len(non_null) >= 2:
            std = float(non_null.std())
            if std > 0.0 and np.isfinite(std):
                z_scores = ((non_null - float(non_null.mean())) / std).abs()
                outlier_rate = float((z_scores > z_threshold).mean())

        if null_rate > 0.0:
            null_flag_count += 1
        if constant_rate > 0.0:
            constant_flag_count += 1
        if outlier_rate > 0.0:
            outlier_flag_count += 1

        per_feature[col] = FeatureColumnQuality(
            name=col,
            null_rate=null_rate,
            constant_rate=constant_rate,
            outlier_rate=outlier_rate,
        ).to_dict()

    return {
        "feature_count": len(numeric_cols),
        "features_with_nulls": null_flag_count,
        "constant_features": constant_flag_count,
        "features_with_outliers": outlier_flag_count,
        "per_feature": per_feature,
    }
