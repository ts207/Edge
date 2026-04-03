from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from project.artifacts import live_thesis_index_path, promoted_theses_path
from project.core.exceptions import DataIntegrityError
from project.live.contracts import PromotedThesis


def _load_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataIntegrityError(f"Failed to read thesis artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DataIntegrityError(f"Thesis artifact {path} did not contain a JSON object payload")
    return payload


def _matches_symbol(thesis: PromotedThesis, symbol: str) -> bool:
    token = str(symbol or "").strip().upper()
    if not token:
        return True
    scope = thesis.symbol_scope or {}
    candidate_symbol = str(scope.get("candidate_symbol", "")).strip().upper()
    if candidate_symbol == token:
        return True
    symbols = [
        str(item).strip().upper()
        for item in scope.get("symbols", [])
        if str(item).strip()
    ]
    return token in symbols


def _event_ids_for_matching(thesis: PromotedThesis) -> set[str]:
    tokens = {
        str(thesis.primary_event_id or "").strip().upper(),
    }
    tokens.update(
        str(item).strip().upper()
        for item in thesis.requirements.trigger_events
        if str(item).strip()
    )
    tokens.update(
        str(item).strip().upper()
        for item in thesis.requirements.confirmation_events
        if str(item).strip()
    )
    tokens.update(
        str(item).strip().upper()
        for item in thesis.source.event_contract_ids
        if str(item).strip()
    )
    return {token for token in tokens if token}


def _family_tokens_for_matching(thesis: PromotedThesis) -> set[str]:
    token = str(thesis.event_family or "").strip().upper()
    return {token} if token else set()


class ThesisStore:
    def __init__(
        self,
        theses: Iterable[PromotedThesis],
        *,
        run_id: str = "",
        source_path: str | Path | None = None,
        schema_version: str = "",
        generated_at_utc: str = "",
    ) -> None:
        self._theses = list(theses)
        self.run_id = str(run_id or "").strip()
        self.source_path = Path(source_path) if source_path is not None else None
        self.schema_version = str(schema_version or "").strip()
        self.generated_at_utc = str(generated_at_utc or "").strip()

    @classmethod
    def from_path(cls, path: str | Path) -> "ThesisStore":
        payload = _load_payload(Path(path))
        theses = [
            PromotedThesis.model_validate(item)
            for item in payload.get("theses", [])
            if isinstance(item, dict)
        ]
        return cls(
            theses,
            run_id=str(payload.get("run_id", "")).strip(),
            source_path=path,
            schema_version=str(payload.get("schema_version", "")).strip(),
            generated_at_utc=str(payload.get("generated_at_utc", "")).strip(),
        )

    @classmethod
    def from_run_id(cls, run_id: str, *, data_root: Path | None = None) -> "ThesisStore":
        return cls.from_path(promoted_theses_path(run_id, data_root))

    @classmethod
    def latest(
        cls,
        *,
        data_root: Path | None = None,
        allow_implicit_latest: bool = False,
    ) -> "ThesisStore":
        if not allow_implicit_latest:
            raise RuntimeError(
                "Implicit latest thesis resolution is disabled. "
                "Use ThesisStore.from_run_id(...), ThesisStore.from_path(...), "
                "or pass allow_implicit_latest=True for compatibility-only callers."
            )
        index = _load_payload(live_thesis_index_path(data_root))
        latest_run_id = str(index.get("latest_run_id", "")).strip()
        if latest_run_id:
            return cls.from_run_id(latest_run_id, data_root=data_root)
        raise FileNotFoundError("No live thesis index is available.")

    def all(self) -> List[PromotedThesis]:
        return list(self._theses)

    def filter(
        self,
        *,
        status: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        event_id: str | None = None,
        event_family: str | None = None,
        canonical_regime: str | None = None,
        deployment_state: str | None = None,
        overlap_group_id: str | None = None,
    ) -> List[PromotedThesis]:
        filtered = self._theses
        if status is not None:
            status_token = str(status).strip().lower()
            filtered = [thesis for thesis in filtered if thesis.status == status_token]
        if symbol is not None:
            filtered = [thesis for thesis in filtered if _matches_symbol(thesis, symbol)]
        if timeframe is not None:
            timeframe_token = str(timeframe).strip().lower()
            filtered = [
                thesis for thesis in filtered if thesis.timeframe.strip().lower() == timeframe_token
            ]
        event_id_token = str(event_id or "").strip().upper()
        if event_id_token:
            filtered = [
                thesis
                for thesis in filtered
                if event_id_token in _event_ids_for_matching(thesis)
            ]
        event_family_token = str(event_family or "").strip().upper()
        if event_family_token:
            filtered = [
                thesis
                for thesis in filtered
                if event_family_token in _family_tokens_for_matching(thesis)
            ]
        if canonical_regime is not None:
            regime_token = str(canonical_regime).strip().upper()
            filtered = [
                thesis
                for thesis in filtered
                if thesis.canonical_regime.strip().upper() == regime_token
            ]
        if deployment_state is not None:
            deployment_token = str(deployment_state).strip().lower()
            filtered = [
                thesis
                for thesis in filtered
                if thesis.deployment_state.strip().lower() == deployment_token
            ]
        if overlap_group_id is not None:
            overlap_token = str(overlap_group_id).strip()
            filtered = [
                thesis
                for thesis in filtered
                if str(thesis.governance.overlap_group_id or "").strip() == overlap_token
            ]
        return list(filtered)

    def active_theses(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        event_id: str | None = None,
        event_family: str | None = None,
        canonical_regime: str | None = None,
        deployment_state: str | None = None,
        overlap_group_id: str | None = None,
    ) -> List[PromotedThesis]:
        return self.filter(
            status="active",
            symbol=symbol,
            timeframe=timeframe,
            event_id=event_id,
            event_family=event_family,
            canonical_regime=canonical_regime,
            deployment_state=deployment_state,
            overlap_group_id=overlap_group_id,
        )
