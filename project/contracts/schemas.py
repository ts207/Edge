from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass(frozen=True)
class DataFrameSchemaContract:
    name: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()
    schema_version: str = "phase5_schema_v1"


_SCHEMA_REGISTRY: Dict[str, DataFrameSchemaContract] = {
    "phase2_candidates": DataFrameSchemaContract(
        name="phase2_candidates",
        required_columns=("candidate_id", "event_type", "symbol", "run_id"),
        optional_columns=("estimate_bps", "q_value", "hypothesis_id", "split_scheme_id"),
    ),
    "promotion_audit": DataFrameSchemaContract(
        name="promotion_audit",
        required_columns=("candidate_id", "event_type", "promotion_decision", "promotion_track"),
        optional_columns=(
            "q_value",
            "promotion_score",
            "bundle_version",
            "policy_version",
            "evidence_bundle_json",
        ),
    ),
    "promoted_candidates": DataFrameSchemaContract(
        name="promoted_candidates",
        required_columns=("candidate_id", "event_type", "status"),
        optional_columns=("promotion_track", "selection_score", "bundle_version", "policy_version"),
    ),
    "evidence_bundle_summary": DataFrameSchemaContract(
        name="evidence_bundle_summary",
        required_columns=("candidate_id", "event_type", "promotion_decision", "promotion_track"),
        optional_columns=("rank_score", "policy_version", "bundle_version"),
    ),
    "promotion_decisions": DataFrameSchemaContract(
        name="promotion_decisions",
        required_columns=("candidate_id", "event_type", "promotion_decision", "promotion_track"),
        optional_columns=("rank_score", "policy_version", "bundle_version"),
    ),
}


def get_schema_contract(name: str) -> DataFrameSchemaContract:
    try:
        return _SCHEMA_REGISTRY[str(name)]
    except KeyError as exc:
        raise KeyError(f"unknown dataframe schema: {name}") from exc


def normalize_dataframe_for_schema(df: pd.DataFrame, schema_name: str) -> pd.DataFrame:
    schema = get_schema_contract(schema_name)
    out = df.copy()
    for col in schema.required_columns + schema.optional_columns:
        if col not in out.columns:
            out[col] = pd.NA
    ordered = list(schema.required_columns) + [
        c for c in schema.optional_columns if c in out.columns
    ]
    remainder = [c for c in out.columns if c not in ordered]
    return out[ordered + remainder]


def validate_dataframe_for_schema(
    df: pd.DataFrame, schema_name: str, *, allow_empty: bool = True
) -> pd.DataFrame:
    schema = get_schema_contract(schema_name)
    out = normalize_dataframe_for_schema(df, schema_name)
    if out.empty and allow_empty:
        return out
    missing = [col for col in schema.required_columns if col not in out.columns]
    if missing:
        raise ValueError(
            f"dataframe for schema '{schema_name}' missing required columns: {missing}"
        )
    # Empty values in required columns are allowed only on empty frames.
    if not out.empty:
        bad = [col for col in schema.required_columns if out[col].isna().all()]
        if bad:
            raise ValueError(
                f"dataframe for schema '{schema_name}' has all-null required columns: {bad}"
            )
    return out
