from __future__ import annotations

import json

import pytest
import yaml

from project.research.agent_io.proposal_schema import load_agent_proposal
from project.research.agent_io.proposal_to_experiment import (
    build_run_all_overrides,
    translate_and_validate_proposal,
)


@pytest.fixture
def registry_root(tmp_path):
    reg_dir = tmp_path / "registries"
    reg_dir.mkdir()

    (reg_dir / "events.yaml").write_text(
        yaml.dump(
            {
                "events": {
                    "BASIS_DISLOC": {
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                        "sequence_eligible": True,
                        "requires_features": [],
                    }
                }
            }
        )
    )
    (reg_dir / "states.yaml").write_text(yaml.dump({"states": {}}))
    (reg_dir / "features.yaml").write_text(yaml.dump({"features": {}}))
    (reg_dir / "templates.yaml").write_text(
        yaml.dump(
            {
                "templates": {
                    "continuation": {
                        "enabled": True,
                        "supports_trigger_types": ["EVENT"],
                    }
                }
            }
        )
    )
    (reg_dir / "contexts.yaml").write_text(
        yaml.dump({"context_dimensions": {"session": {"allowed_values": ["open", "close"]}}})
    )
    (reg_dir / "search_limits.yaml").write_text(
        yaml.dump(
            {
                "limits": {
                    "max_events_per_run": 10,
                    "max_templates_per_run": 10,
                    "max_horizons_per_run": 10,
                    "max_directions_per_run": 10,
                    "max_entry_lags_per_run": 4,
                    "max_hypotheses_total": 1000,
                    "max_hypotheses_per_template": 250,
                    "max_hypotheses_per_event_family": 300,
                },
                "defaults": {
                    "horizons_bars": [12, 24],
                    "directions": ["long", "short"],
                    "entry_lags": [0, 1],
                },
            }
        )
    )
    (reg_dir / "detectors.yaml").write_text(
        yaml.dump({"detector_ownership": {"BASIS_DISLOC": "BasisDislocDetector"}})
    )
    return reg_dir


def _proposal_payload(**overrides):
    payload = {
        "program_id": "btc_campaign",
        "description": "basis continuation slice",
        "run_mode": "research",
        "objective": "retail_profitability",
        "promotion_mode": "research",
        "symbols": ["BTCUSDT"],
        "timeframe": "5m",
        "start": "2026-01-01",
        "end": "2026-01-31",
        "instrument_classes": ["crypto"],
        "trigger_space": {
            "allowed_trigger_types": ["EVENT"],
            "events": {"include": ["BASIS_DISLOC"]},
        },
        "templates": ["continuation"],
        "contexts": {"session": ["open"]},
        "horizons_bars": [12],
        "directions": ["long", "short"],
        "entry_lags": [0],
        "knobs": {"candidate_promotion_min_events": 60},
    }
    payload.update(overrides)
    return payload


def test_load_agent_proposal_normalizes_aliases_and_settable_knobs():
    proposal = load_agent_proposal(_proposal_payload())

    assert proposal.objective_name == "retail_profitability"
    assert proposal.promotion_profile == "research"
    assert proposal.templates == ["continuation"]
    assert proposal.knobs["candidate_promotion_min_events"] == 60


def test_load_agent_proposal_rejects_inspect_only_knobs():
    with pytest.raises(ValueError, match="non-settable knobs"):
        load_agent_proposal(
            _proposal_payload(
                knobs={
                    "candidate_promotion_min_events": 60,
                    "research.enforce_placebo_controls": False,
                }
            )
        )


def test_translate_and_validate_proposal_builds_valid_experiment_and_overrides(
    tmp_path,
    registry_root,
):
    out_dir = tmp_path / "artifacts"
    result = translate_and_validate_proposal(
        _proposal_payload(),
        registry_root=registry_root,
        out_dir=out_dir,
        config_path=tmp_path / "translated.yaml",
    )

    assert result["validated_plan"]["program_id"] == "btc_campaign"
    assert result["validated_plan"]["estimated_hypothesis_count"] == 2
    assert result["run_all_overrides"]["candidate_promotion_profile"] == "research"
    assert result["run_all_overrides"]["candidate_promotion_min_events"] == 60
    assert result["run_all_overrides"]["objective_name"] == "retail_profitability"
    assert result["experiment_config"]["templates"]["include"] == ["continuation"]
    assert result["experiment_config"]["contexts"]["include"]["session"] == ["open"]


def test_build_run_all_overrides_disables_promotion_without_invalid_profile():
    proposal = load_agent_proposal(_proposal_payload(promotion_mode="disabled", knobs={}))
    overrides = build_run_all_overrides(proposal)

    assert overrides["run_candidate_promotion"] == 0
    assert "candidate_promotion_profile" not in overrides
