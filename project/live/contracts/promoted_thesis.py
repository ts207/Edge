from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ThesisEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(ge=0)
    validation_samples: int = Field(default=0, ge=0)
    test_samples: int = Field(default=0, ge=0)
    estimate_bps: float | None = None
    net_expectancy_bps: float | None = None
    q_value: float | None = None
    stability_score: float | None = None
    cost_survival_ratio: float | None = None
    tob_coverage: float | None = None
    rank_score: float | None = None
    promotion_track: str = ""
    policy_version: str = ""
    bundle_version: str = ""


class ThesisLineage(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    hypothesis_id: str = ""
    plan_row_id: str = ""
    blueprint_id: str = ""
    proposal_id: str = ""


class ThesisGovernance(BaseModel):
    model_config = ConfigDict(frozen=True)

    tier: str = ""
    operational_role: str = ""
    deployment_disposition: str = ""
    evidence_mode: str = ""
    overlap_group_id: str = ""
    trade_trigger_eligible: bool = False
    requires_stronger_evidence: bool = False


class ThesisRequirements(BaseModel):
    model_config = ConfigDict(frozen=True)

    trigger_events: List[str] = Field(default_factory=list)
    confirmation_events: List[str] = Field(default_factory=list)
    required_episodes: List[str] = Field(default_factory=list)
    disallowed_regimes: List[str] = Field(default_factory=list)
    deployment_gate: str = ""
    sequence_mode: str = ""
    minimum_episode_confidence: float = 0.0


class ThesisSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_program_id: str = ""
    source_campaign_id: str = ""
    source_run_mode: str = ""
    objective_name: str = ""
    event_contract_ids: List[str] = Field(default_factory=list)
    episode_contract_ids: List[str] = Field(default_factory=list)


class PromotedThesis(BaseModel):
    model_config = ConfigDict(frozen=True)

    thesis_id: str = Field(min_length=1)
    promotion_class: Literal["seed_promoted", "paper_promoted", "production_promoted"] = "paper_promoted"
    deployment_state: Literal["monitor_only", "paper_only", "live_enabled", "retired"] = "paper_only"
    evidence_gaps: List[str] = Field(default_factory=list)
    status: Literal["pending_blueprint", "active", "paused", "retired"] = "pending_blueprint"
    evidence_freshness_date: str = ""
    review_due_date: str = ""
    staleness_class: Literal["fresh", "watch", "stale", "unknown"] = "unknown"
    symbol_scope: Dict[str, Any] = Field(default_factory=dict)
    timeframe: str = Field(min_length=1)
    primary_event_id: str = Field(min_length=1)
    event_family: str = ""
    canonical_regime: str = ""
    event_side: Literal["long", "short", "both", "conditional", "unknown"] = "unknown"
    required_context: Dict[str, Any] = Field(default_factory=dict)
    supportive_context: Dict[str, Any] = Field(default_factory=dict)
    expected_response: Dict[str, Any] = Field(default_factory=dict)
    invalidation: Dict[str, Any] = Field(default_factory=dict)
    risk_notes: List[str] = Field(default_factory=list)
    evidence: ThesisEvidence
    lineage: ThesisLineage
    governance: ThesisGovernance = Field(default_factory=ThesisGovernance)
    requirements: ThesisRequirements = Field(default_factory=ThesisRequirements)
    source: ThesisSource = Field(default_factory=ThesisSource)

    @model_validator(mode="before")
    @classmethod
    def _populate_compat_event_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        primary_event_id = str(
            data.get("primary_event_id", "") or data.get("event_family", "")
        ).strip()
        event_family = str(
            data.get("event_family", "") or data.get("primary_event_id", "")
        ).strip()
        if primary_event_id:
            data["primary_event_id"] = primary_event_id
        if event_family:
            data["event_family"] = event_family
        return data

    @field_validator("thesis_id", "timeframe", "primary_event_id")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("field must be non-empty")
        return str(value).strip()

    @field_validator("primary_event_id", "event_family", "canonical_regime")
    @classmethod
    def _normalize_optional_tokens(cls, value: str) -> str:
        return str(value).strip().upper()
