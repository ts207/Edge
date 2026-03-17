from __future__ import annotations
from project.core.config import get_data_root

from project.events.event_specs import (
    EventRegistrySpec,
    EVENT_REGISTRY_SPECS,
    SIGNAL_TO_EVENT_TYPE,
    REGISTRY_BACKED_SIGNALS,
    REGISTRY_EVENT_COLUMNS,
    AGGREGATE_EVENT_TYPE_UNIONS,
    expected_event_types_for_spec,
    VALID_DIRECTIONS,
    assert_event_specs_available,
    _load_event_specs,
)
from project.events.event_normalizer import (
    filter_phase1_rows_for_event_type,
    normalize_phase1_events,
    normalize_registry_events_frame,
)
from project.events.event_repository import (
    collect_registry_events,
    merge_registry_events,
    write_event_registry_artifacts,
    load_registry_events,
    write_registry_file,
    load_registry_episode_anchors,
)
import project.events.event_flags as _event_flags_mod
from project.events.event_flags import (
    load_registry_flags,
    merge_event_flags_for_selected_event_types,
    _signal_ts_column,
    _active_signal_column,
)
from project.events.event_diagnostics import (
    generate_event_coverage_report,
    calibrate_event_thresholds,
    verify_index_alignment,
    registry_contract_check,
    build_event_feature_frame,
)
import sys
from pathlib import Path
import pandas as pd


def build_event_flags(*, events, symbols, data_root, run_id, timeframe="5m"):
    """Wrapper so monkeypatching registry._load_symbol_timestamps works in tests."""
    this_module = sys.modules[__name__]
    return _event_flags_mod.build_event_flags(
        events=events,
        symbols=symbols,
        data_root=data_root,
        run_id=run_id,
        timeframe=timeframe,
        _ts_loader=this_module._load_symbol_timestamps,
    )


def _load_symbol_timestamps(
    data_root: "Path | None" = None, run_id: str = "", symbol: str = "", timeframe: str = "5m"
) -> pd.Series:
    from project.io.utils import read_parquet
    from project import PROJECT_ROOT
    DATA_ROOT = get_data_root()
    path = DATA_ROOT / "lake" / "bars" / symbol / f"{timeframe}.parquet"
    if path.exists():
        df = read_parquet(path)
        return df["timestamp"]
    return pd.Series(dtype="datetime64[ns, UTC]")

from project.events.event_prerequisites import (
    check_event_prerequisites,
)


import functools
import yaml

from project import PROJECT_ROOT
from project.events.event_aliases import resolve_event_alias


_MILESTONE_REGISTRY_PATH = PROJECT_ROOT.parent / "spec" / "events" / "registry.yaml"


@functools.lru_cache(maxsize=1)
def load_milestone_event_registry() -> dict[str, dict]:
    if not _MILESTONE_REGISTRY_PATH.exists():
        return {}
    payload = yaml.safe_load(_MILESTONE_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict] = {}
    for raw_key, value in payload.items():
        if isinstance(value, dict):
            row = dict(value)
            event_type = str(row.get("event_type") or raw_key).strip().upper()
            row["event_type"] = event_type
            out[event_type] = row
    return out


def get_event_definition(event_type: str) -> dict | None:
    normalized = resolve_event_alias(str(event_type).strip().upper())
    registry = load_milestone_event_registry()
    row = registry.get(normalized)
    if row is None and normalized != str(event_type).strip().upper():
        row = registry.get(str(event_type).strip().upper())
    return dict(row) if isinstance(row, dict) else None


def list_events_by_family(family: str) -> list[dict]:
    normalized = str(family).strip().lower()
    rows = []
    for row in load_milestone_event_registry().values():
        if str(row.get("family", "")).strip().lower() == normalized:
            rows.append(dict(row))
    rows.sort(key=lambda item: str(item.get("event_type", "")))
    return rows
