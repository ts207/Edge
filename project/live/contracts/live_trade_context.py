from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LiveTradeContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    primary_event_id: str = Field(min_length=1)
    event_family: str = ""
    canonical_regime: str = ""
    event_side: str = Field(min_length=1)
    live_features: Dict[str, Any] = Field(default_factory=dict)
    regime_snapshot: Dict[str, Any] = Field(default_factory=dict)
    execution_env: Dict[str, Any] = Field(default_factory=dict)
    portfolio_state: Dict[str, Any] = Field(default_factory=dict)
    active_event_families: List[str] = Field(default_factory=list)
    active_event_ids: List[str] = Field(default_factory=list)
    active_episode_ids: List[str] = Field(default_factory=list)
    contradiction_event_families: List[str] = Field(default_factory=list)
    contradiction_event_ids: List[str] = Field(default_factory=list)
    episode_snapshot: Dict[str, Any] = Field(default_factory=dict)

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

    @field_validator("timestamp", "symbol", "timeframe", "primary_event_id", "event_side")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        token = str(value).strip()
        if not token:
            raise ValueError("field must be non-empty")
        return token

    @field_validator("event_family", "primary_event_id", "canonical_regime")
    @classmethod
    def _normalize_optional_tokens(cls, value: str) -> str:
        return str(value).strip().upper()
