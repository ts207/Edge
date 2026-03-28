from project.events.config import compose_event_config
from project.events.registry import _load_event_specs, EVENT_REGISTRY_SPECS


def test_dynamic_loading():
    # Ensure loaded specs match the hardcoded baseline (sanity check)
    loaded = _load_event_specs()
    assert "VOL_SHOCK" in loaded
    assert loaded["VOL_SHOCK"].signal_column == "vol_shock_relaxation_event"
    assert len(loaded) >= 11


def test_blank_registry_fields_fall_back_to_canonical_defaults():
    loaded = _load_event_specs()
    spec = loaded["CROSS_ASSET_DESYNC_EVENT"]

    assert spec.reports_dir == "cross_asset_desync_event"
    assert spec.events_file == "cross_asset_desync_event_events.parquet"
    assert spec.signal_column == "cross_asset_desync_event"

    cfg = compose_event_config("CROSS_ASSET_DESYNC_EVENT")
    assert cfg.reports_dir == "cross_asset_desync_event"
    assert cfg.events_file == "cross_asset_desync_event_events.parquet"
    assert cfg.signal_column == "cross_asset_desync_event"
