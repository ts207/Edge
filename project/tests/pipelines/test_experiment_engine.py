import pytest
import yaml
from pathlib import Path
from project.research.experiment_engine import (
    RegistryBundle,
    load_agent_experiment_config,
    validate_agent_request,
    expand_hypotheses,
    resolve_required_detectors,
    build_experiment_plan,
)


@pytest.fixture
def registry_root(tmp_path):
    root = tmp_path / "registries"
    root.mkdir()

    (root / "events.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "events": {
                    "VOL_SPIKE": {
                        "family": "volatility",
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                    },
                    "LIQUIDITY_GAP_PRINT": {
                        "family": "liquidity",
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                    },
                },
            }
        )
    )

    (root / "templates.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "templates": {
                    "continuation": {"enabled": True, "supports_trigger_types": ["EVENT"]},
                    "fade": {"enabled": True, "supports_trigger_types": ["EVENT"]},
                },
            }
        )
    )

    (root / "states.yaml").write_text(yaml.dump({"states": {}}))
    (root / "features.yaml").write_text(yaml.dump({"features": {}}))

    (root / "contexts.yaml").write_text(
        yaml.dump(
            {"version": 1, "context_dimensions": {"session": {"allowed_values": ["open", "close"]}}}
        )
    )

    (root / "search_limits.yaml").write_text(
        yaml.dump({"version": 1, "limits": {"max_events_per_run": 5, "max_templates_per_run": 5}})
    )

    (root / "detectors.yaml").write_text(
        yaml.dump({"version": 1, "detector_ownership": {"VOL_SPIKE": "VolSpikeDetector"}})
    )

    return root


@pytest.fixture
def experiment_config(tmp_path):
    path = tmp_path / "experiment.yaml"
    path.write_text(
        yaml.dump(
            {
                "version": 1,
                "program_id": "test_prog",
                "run_mode": "research",
                "instrument_scope": {
                    "instrument_classes": ["crypto"],
                    "symbols": ["BTCUSDT"],
                    "timeframe": "5m",
                    "start": "2024-01-01",
                    "end": "2024-01-02",
                },
                "trigger_space": {
                    "allowed_trigger_types": ["EVENT"],
                    "events": {"include": ["VOL_SPIKE"]},
                },
                "templates": {"include": ["continuation"]},
                "evaluation": {"horizons_bars": [12], "directions": ["long"], "entry_lags": [0]},
                "contexts": {"include": {"session": ["open"]}},
                "search_control": {
                    "max_hypotheses_total": 100,
                    "max_hypotheses_per_template": 50,
                    "max_hypotheses_per_event_family": 50,
                },
                "promotion": {"enabled": True},
            }
        )
    )
    return path


def test_experiment_expansion(registry_root, experiment_config):
    plan = build_experiment_plan(experiment_config, registry_root)

    assert plan.program_id == "test_prog"
    assert len(plan.hypotheses) == 1
    assert plan.hypotheses[0].trigger.event_id == "VOL_SPIKE"
    assert plan.required_detectors == ["VolSpikeDetector"]


def test_validation_failure_invalid_event(registry_root, tmp_path):
    config_path = tmp_path / "bad_config.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "program_id": "bad",
                "run_mode": "research",
                "instrument_scope": {
                    "instrument_classes": ["crypto"],
                    "symbols": [],
                    "timeframe": "5m",
                    "start": "",
                    "end": "",
                },
                "trigger_space": {
                    "allowed_trigger_types": ["EVENT"],
                    "events": {"include": ["NON_EXISTENT"]},
                },
                "templates": {"include": ["continuation"]},
                "evaluation": {"horizons_bars": [1], "directions": ["long"], "entry_lags": [0]},
                "contexts": {"include": {}},
                "search_control": {
                    "max_hypotheses_total": 10,
                    "max_hypotheses_per_template": 5,
                    "max_hypotheses_per_event_family": 5,
                },
                "promotion": {"enabled": True},
            }
        )
    )

    with pytest.raises(
        ValueError, match="Event ID 'NON_EXISTENT' is not in the authoritative registry"
    ):
        build_experiment_plan(config_path, registry_root)
