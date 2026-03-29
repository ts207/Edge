import pytest
from pathlib import Path
import yaml
import pandas as pd
from project.research.experiment_engine import build_experiment_plan
from project.research.experiment_engine_validators import _ordered_run_ids


@pytest.fixture
def registry_root(tmp_path):
    reg_dir = tmp_path / "registries"
    reg_dir.mkdir()

    (reg_dir / "events.yaml").write_text(
        yaml.dump(
            {
                "events": {
                    "VOL_SPIKE": {
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                        "sequence_eligible": True,
                    },
                    "LIQ_GAP": {
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                        "sequence_eligible": True,
                    },
                    "NOT_SEQ": {
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                        "sequence_eligible": False,
                    },
                }
            }
        )
    )

    (reg_dir / "states.yaml").write_text(
        yaml.dump({"states": {"HIGH_VOL": {"enabled": True, "instrument_classes": ["crypto"]}}})
    )

    (reg_dir / "features.yaml").write_text(
        yaml.dump(
            {
                "features": {
                    "rsi": {"allowed_operators": [">", "<"], "instrument_classes": ["crypto"]}
                }
            }
        )
    )

    (reg_dir / "templates.yaml").write_text(
        yaml.dump(
            {
                "templates": {
                    "continuation": {
                        "enabled": True,
                        "supports_trigger_types": [
                            "EVENT",
                            "STATE",
                            "SEQUENCE",
                            "FEATURE_PREDICATE",
                            "INTERACTION",
                        ],
                    },
                    "event_only": {"enabled": True, "supports_trigger_types": ["EVENT"]},
                }
            }
        )
    )

    (reg_dir / "contexts.yaml").write_text(yaml.dump({"context_dimensions": {}}))

    (reg_dir / "search_limits.yaml").write_text(
        yaml.dump(
            {
                "limits": {
                    "max_events_per_run": 10,
                    "max_templates_per_run": 10,
                    "max_horizons_per_run": 10,
                    "max_directions_per_run": 10,
                    "max_sequence_length": 3,
                }
            }
        )
    )

    (reg_dir / "detectors.yaml").write_text(yaml.dump({"detector_ownership": {}}))

    return reg_dir


def _make_config(tmp_path, **overrides):
    config = {
        "program_id": "test",
        "run_mode": "research",
        "instrument_scope": {
            "instrument_classes": ["crypto"],
            "symbols": ["BTCUSDT"],
            "timeframe": "1m",
            "start": "2024-01-01",
            "end": "2024-01-02",
        },
        "trigger_space": {"allowed_trigger_types": ["EVENT"], "events": {"include": ["VOL_SPIKE"]}},
        "templates": {"include": ["continuation"]},
        "evaluation": {"horizons_bars": [10], "directions": ["long"], "entry_lags": [1]},
        "contexts": {"include": {}},
        "search_control": {
            "max_hypotheses_total": 100,
            "max_hypotheses_per_template": 100,
            "max_hypotheses_per_event_family": 100,
        },
        "promotion": {"enabled": False},
    }
    # Deep merge overrides
    for k, v in overrides.items():
        if isinstance(v, dict) and k in config:
            config[k].update(v)
        else:
            config[k] = v

    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(config))
    return p


def test_validate_template_compatibility(registry_root, tmp_path):
    # event_only template with STATE trigger should fail
    conf = _make_config(
        tmp_path,
        trigger_space={"allowed_trigger_types": ["STATE"], "states": {"include": ["HIGH_VOL"]}},
        templates={"include": ["event_only"]},
    )
    with pytest.raises(
        ValueError, match="Template 'event_only' does not support trigger type 'STATE'"
    ):
        build_experiment_plan(conf, registry_root)


def test_validate_sequence_eligibility(registry_root, tmp_path):
    conf = _make_config(
        tmp_path,
        trigger_space={
            "allowed_trigger_types": ["SEQUENCE"],
            "sequences": {"include": [["VOL_SPIKE", "NOT_SEQ"]]},
        },
    )
    with pytest.raises(ValueError, match="Event 'NOT_SEQ' is not sequence-eligible"):
        build_experiment_plan(conf, registry_root)


def test_validate_feature_predicate(registry_root, tmp_path):
    conf = _make_config(
        tmp_path,
        trigger_space={
            "allowed_trigger_types": ["FEATURE_PREDICATE"],
            "feature_predicates": {"include": [{"feature": "rsi", "operator": "=="}]},
        },
    )
    with pytest.raises(ValueError, match="Operator '==' not allowed for feature 'rsi'"):
        build_experiment_plan(conf, registry_root)


def test_validate_instrument_mismatch(registry_root, tmp_path):
    conf = _make_config(
        tmp_path,
        instrument_scope={"instrument_classes": ["equities"]},
        trigger_space={"allowed_trigger_types": ["EVENT"], "events": {"include": ["VOL_SPIKE"]}},
    )
    with pytest.raises(
        ValueError, match="Event 'VOL_SPIKE' is not allowed for instrument class 'equities'"
    ):
        build_experiment_plan(conf, registry_root)


def test_build_experiment_plan_uses_explicit_data_root(registry_root, tmp_path, monkeypatch):
    from project.core import config as config_mod

    wrong_root = tmp_path / "wrong_root"
    actual_root = tmp_path / "actual_root"
    halted_dir = actual_root / "artifacts" / "experiments" / "test"
    halted_dir.mkdir(parents=True)
    (halted_dir / "campaign_state.json").write_text('{"state": "halted_unsupported"}')
    monkeypatch.setattr(config_mod, "get_data_root", lambda: wrong_root)

    conf = _make_config(tmp_path)
    with pytest.raises(ValueError, match="cannot accept new proposals"):
        build_experiment_plan(conf, registry_root, data_root=actual_root)


def test_ordered_run_ids_prefers_created_at_over_row_encounter_order() -> None:
    df = pd.DataFrame(
        {
            "run_id": ["run_new", "run_old"],
            "created_at": ["2024-02-01T00:00:00+00:00", "2024-01-01T00:00:00+00:00"],
        }
    )

    assert _ordered_run_ids(df) == ["run_old", "run_new"]
