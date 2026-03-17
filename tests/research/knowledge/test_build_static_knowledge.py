from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from project.research.knowledge.build_static_knowledge import build_static_knowledge


def test_build_static_knowledge_writes_expected_artifacts(tmp_path):
    result = build_static_knowledge(
        data_root=tmp_path,
        registry_root=Path.cwd() / "project" / "configs" / "registries",
    )

    assert result["entities_path"].exists()
    assert result["relations_path"].exists()
    assert result["documents_path"].exists()
    assert result["index_path"].exists()

    entities = pd.read_parquet(result["entities_path"])
    relations = pd.read_parquet(result["relations_path"])
    documents = pd.read_parquet(result["documents_path"])
    knobs = pd.read_parquet(result["knobs_path"])
    index_payload = json.loads(result["index_path"].read_text(encoding="utf-8"))

    assert {"event", "state", "template", "detector", "context_family", "context_label", "feature", "event_family", "trigger_type"} <= set(
        entities["entity_type"].astype(str)
    )
    assert "belongs_to_family" in set(relations["relation_type"].astype(str))
    assert "detects" in set(relations["relation_type"].astype(str))
    assert "supports_trigger_type" in set(relations["relation_type"].astype(str))
    assert "compatible_with_template" in set(relations["relation_type"].astype(str))
    assert not documents.empty
    assert not knobs.empty
    assert "campaign_memory_promising_top_k" in set(knobs["name"].astype(str))
    assert "gate_v1_phase2.max_q_value" in set(knobs["name"].astype(str))
    assert "profiles.capital_constrained.min_net_expectancy_bps" in set(knobs["name"].astype(str))
    assert "objective.hard_gates.min_trade_count" in set(knobs["name"].astype(str))
    assert "limits.max_hypotheses_total" in set(knobs["name"].astype(str))
    assert "research.enforce_placebo_controls" in set(knobs["name"].astype(str))
    assert "min_consensus_ratio" in set(
        knobs.loc[knobs["group"].astype(str) == "promotion_timeframe_consensus", "name"].astype(str)
    )
    assert {"core", "advanced", "internal"} <= set(knobs["agent_level"].astype(str))
    assert {"proposal_settable", "inspect_only"} <= set(knobs["mutability"].astype(str))
    assert {"low", "medium", "high"} <= set(knobs["risk"].astype(str))
    assert index_payload["entity_count"] == len(entities)
    assert index_payload["relation_count"] == len(relations)
    assert index_payload["knob_count"] == len(knobs)
