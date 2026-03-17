from __future__ import annotations

import pytest

from project.events.config import compose_event_config
import project.events.config as tcc
from project.events.config import compose_template_config

def test_compose_event_config_merges_defaults_and_event_parameters():
    cfg = compose_event_config("LIQUIDATION_CASCADE")

    assert cfg.event_type == "LIQUIDATION_CASCADE"
    assert cfg.reports_dir == "liquidation_cascade"
    assert cfg.events_file == "liquidation_cascade_events.parquet"
    assert cfg.signal_column == "liquidation_cascade_event"
    assert cfg.parameters["merge_gap_bars"] == 1
    assert cfg.parameters["cooldown_bars"] == 0
    assert cfg.parameters["anchor_rule"] == "max_intensity"
    assert cfg.parameters["min_occurrences"] == 0
    assert cfg.parameters["liq_vol_th"] == 100000.0
    assert cfg.parameters["oi_drop_th"] == -500000.0

def test_compose_event_config_runtime_overrides_win():
    cfg = compose_event_config(
        "LIQUIDITY_SHOCK",
        runtime_overrides={
            "depth_collapse_th": 0.75,
            "spread_spike_th": 4.25,
            "runtime_only_flag": 1,
        },
    )

    assert cfg.parameters["depth_collapse_th"] == 0.75
    assert cfg.parameters["spread_spike_th"] == 4.25
    assert cfg.parameters["runtime_only_flag"] == 1


def test_compose_event_config_falls_back_to_runtime_event_specs_for_promoted_events():
    cfg = compose_event_config("LIQUIDITY_STRESS_DIRECT")

    assert cfg.event_type == "LIQUIDITY_STRESS_DIRECT"
    assert cfg.signal_column == "liquidity_stress_direct_event"
    assert cfg.reports_dir == "liquidity_shock"
    assert "spec/events/LIQUIDITY_STRESS_DIRECT.yaml" in cfg.source_layers["event_spec"]

def test_compose_template_config_resolves_registry_row():
    cfg = compose_template_config("LIQUIDITY_SHOCK")

    assert cfg.event_type == "LIQUIDITY_SHOCK"
    assert cfg.canonical_family == "LIQUIDITY_DISLOCATION"
    assert cfg.max_candidates_per_run == 600
    assert "stop_run_repair" in cfg.templates
    assert cfg.horizons == ("15m",)
    assert cfg.config_hash.startswith("sha256:")
    assert "\"event_type\":\"LIQUIDITY_SHOCK\"" in cfg.normalized_json

def test_compose_template_config_runtime_overrides_win():
    cfg = compose_template_config(
        "LIQUIDITY_SHOCK",
        runtime_overrides={
            "templates": ["mean_reversion"],
            "horizons": ["5m", "15m"],
            "max_candidates_per_run": 42,
            "conditioning_cols": ["vol_regime"],
        },
        enforce_legacy_drift_check=False,
    )

    assert cfg.templates == ("mean_reversion",)
    assert cfg.horizons == ("5m", "15m")
    assert cfg.max_candidates_per_run == 42
    assert cfg.conditioning_cols == ("vol_regime",)

def test_compose_template_config_missing_event_fails_closed():
    with pytest.raises(KeyError):
        compose_template_config("NOT_A_REAL_EVENT")

def test_compose_template_config_hash_is_stable_for_same_inputs():
    a = compose_template_config("VOL_SHOCK")
    b = compose_template_config("VOL_SHOCK")
    assert a.config_hash == b.config_hash
    assert a.normalized_json == b.normalized_json

def test_compose_template_config_rejects_incompatible_template_runtime_override():
    with pytest.raises(ValueError, match="incompatible"):
        compose_template_config(
            "LIQUIDITY_SHOCK",
            runtime_overrides={"templates": ["desync_repair"]},
        )

def test_compose_template_config_merge_precedence_and_state_overrides(monkeypatch):
    monkeypatch.setattr(
        tcc,
        "_registry",
        lambda: {
            "defaults": {
                "templates": ["global_t"],
                "horizons": ["5m"],
                "max_candidates_per_run": 10,
                "conditioning_cols": ["global_c"],
            },
            "families": {
                "TEST_FAMILY": {
                    "templates": ["family_t"],
                    "horizons": ["15m"],
                    "max_candidates_per_run": 20,
                    "conditioning_cols": ["family_c"],
                }
            },
            "events": {
                "TEST_EVENT": {
                    "canonical_family": "TEST_FAMILY",
                    "templates": ["event_t"],
                    "horizons": ["60m"],
                    "max_candidates_per_run": 30,
                    "conditioning_cols": ["event_c"],
                    "state_overrides": {
                        "STATE_X": {
                            "templates": ["state_t"],
                            "conditioning_cols": ["state_c"],
                        }
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        tcc,
        "_operator_registry",
        lambda: {
            "runtime_t": {"compatible_families": ["TEST_FAMILY"], "side_policy": "both"},
            "state_t": {"compatible_families": ["TEST_FAMILY"], "side_policy": "both"},
        },
    )
    monkeypatch.setattr(
        tcc,
        "_legacy_family_specs",
        lambda: {
            "TEST_EVENT": {
                "canonical_family": "TEST_FAMILY",
                "templates": ["runtime_t"],
                "horizons": ["60m"],
                "max_candidates_per_run": 40,
                "conditioning_cols": ["runtime_c"],
            }
        },
    )
    monkeypatch.setattr(
        tcc,
        "_legacy_taxonomy_families",
        lambda: {"TEST_FAMILY": {"runtime_templates": ["runtime_t"]}},
    )

    cfg = compose_template_config(
        "TEST_EVENT",
        state_id="STATE_X",
        runtime_overrides={
            "templates": ["runtime_t"],
            "max_candidates_per_run": 40,
            "conditioning_cols": ["runtime_c"],
        },
    )
    assert cfg.canonical_family == "TEST_FAMILY"
    assert cfg.state_id == "STATE_X"
    assert cfg.templates == ("runtime_t",)
    assert cfg.horizons == ("60m",)
    assert cfg.max_candidates_per_run == 40
    assert cfg.conditioning_cols == ("runtime_c",)
