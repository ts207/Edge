from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd
import yaml

from project.core.config import get_data_root
from project.events.event_specs import EVENT_REGISTRY_SPECS
from project.research.agent_io.issue_proposal import generate_run_id, issue_proposal
from project.research.agent_io.proposal_schema import load_agent_proposal
from project.research.knowledge.memory import ensure_memory_store, read_memory_table
from project.research.knowledge.schemas import canonical_json, region_key
from project.spec_registry.search_space import DEFAULT_EVENT_PRIORITY_WEIGHT, load_event_priority_weights

_LOG = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or isinstance(value, bool):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _normalize_key(value: Any) -> str:
    return str(value or "").strip()


def _load_json_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw == "{}":
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def _load_contexts(value: Any) -> Dict[str, List[str]]:
    payload = _load_json_object(value)
    out: Dict[str, List[str]] = {}
    for key, raw in payload.items():
        family = _normalize_key(key)
        if not family:
            continue
        if isinstance(raw, (list, tuple, set)):
            labels = [str(item).strip() for item in raw if str(item).strip()]
        else:
            labels = [str(raw).strip()] if str(raw).strip() else []
        if labels:
            out[family] = labels
    return out


def _family_from_event_type(event_type: str, registry_events: Dict[str, Any]) -> str:
    meta = registry_events.get(event_type, {})
    family = str(meta.get("family", "")).strip()
    if family:
        return family
    spec = EVENT_REGISTRY_SPECS.get(event_type)
    if spec is not None:
        return str(getattr(spec, "family", "") or "")
    return ""


def _allowed_templates_for_family(family: str, registry_templates: Dict[str, Any]) -> List[str]:
    families = registry_templates.get("families", {}) if isinstance(registry_templates, dict) else {}
    meta = families.get(family, {}) if isinstance(families, dict) else {}
    allowed = meta.get("allowed_templates", []) if isinstance(meta, dict) else []
    if isinstance(allowed, str):
        allowed = [allowed]
    out = [str(value).strip() for value in allowed if str(value).strip()]
    return out or ["mean_reversion", "continuation"]


def _search_space_path(registry_root: Path, override: Path | None = None) -> Path:
    if override is not None:
        return override
    candidates = [
        Path("spec/search_space.yaml"),
        registry_root.parent.parent / "spec" / "search_space.yaml",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


def _tested_region_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    for column in ["event_type", "template_id", "direction", "horizon", "entry_lag", "region_key"]:
        if column not in out.columns:
            out[column] = ""
    for column, default in [("failure_cause_class", ""), ("failure_confidence", 0.0), ("failure_sample_size", 0)]:
        if column not in out.columns:
            out[column] = default
    return out


def _count_contexts(tested_regions: pd.DataFrame) -> Dict[str, Counter]:
    counts: Dict[str, Counter] = defaultdict(Counter)
    if tested_regions.empty or "context_json" not in tested_regions.columns:
        return counts
    for payload in tested_regions["context_json"].tolist():
        contexts = _load_contexts(payload)
        for family, labels in contexts.items():
            for label in labels:
                counts[family][label] += 1
    return counts


def _family_counts(tested_regions: pd.DataFrame, event_to_family: Dict[str, str]) -> Counter:
    counts: Counter = Counter()
    if tested_regions.empty or "event_type" not in tested_regions.columns:
        return counts
    for event_type in tested_regions["event_type"].astype(str).tolist():
        family = event_to_family.get(event_type, "")
        if family:
            counts[family] += 1
    return counts


def _event_counts(tested_regions: pd.DataFrame) -> Counter:
    counts: Counter = Counter()
    if tested_regions.empty or "event_type" not in tested_regions.columns:
        return counts
    counts.update(tested_regions["event_type"].astype(str).tolist())
    return counts


def _mechanical_exclusions(tested_regions: pd.DataFrame) -> set[str]:
    if tested_regions.empty or "failure_cause_class" not in tested_regions.columns:
        return set()
    mechanical = tested_regions[tested_regions["failure_cause_class"].astype(str).str.strip().str.lower() == "mechanical"]
    if "region_key" not in mechanical.columns:
        return set()
    return set(mechanical["region_key"].astype(str).tolist())


def _mechanical_event_types(tested_regions: pd.DataFrame) -> set[str]:
    if tested_regions.empty or "failure_cause_class" not in tested_regions.columns or "event_type" not in tested_regions.columns:
        return set()
    mechanical = tested_regions[tested_regions["failure_cause_class"].astype(str).str.strip().str.lower() == "mechanical"]
    return set(mechanical["event_type"].astype(str).tolist())


def _failure_penalties(tested_regions: pd.DataFrame) -> Dict[str, float]:
    penalties: Dict[str, float] = {}
    if tested_regions.empty or "failure_cause_class" not in tested_regions.columns:
        return penalties
    for event_type, frame in tested_regions.groupby("event_type", dropna=False):
        event_key = str(event_type)
        if not event_key:
            continue
        classes = frame["failure_cause_class"].astype(str).str.strip().str.lower()
        if classes.empty:
            continue
        mechanical_share = float((classes == "mechanical").mean())
        insufficient_share = float((classes == "insufficient_sample").mean())
        market_share = float((classes == "market").mean())
        cost_share = float((classes == "cost").mean())
        overfit_share = float((classes == "overfitting").mean())
        penalties[event_key] = (
            2.5 * mechanical_share
            + 0.75 * insufficient_share
            + 0.45 * market_share
            + 0.65 * cost_share
            + 0.9 * overfit_share
        )
    return penalties


def _default_date_scope(lookback_days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=int(lookback_days))
    return start.isoformat(), end.isoformat()


@dataclass(frozen=True)
class CampaignPlannerConfig:
    program_id: str
    registry_root: Path
    data_root: Path | None = None
    search_space_path: Path | None = None
    symbols: tuple[str, ...] = ("BTCUSDT",)
    instrument_classes: tuple[str, ...] = ("crypto",)
    timeframe: str = "5m"
    lookback_days: int = 90
    horizon_bars: tuple[int, ...] = (12, 24)
    entry_lags: tuple[int, ...] = (0,)
    directions: tuple[str, ...] = ("long", "short")
    templates: tuple[str, ...] = ()
    max_proposals: int = 10
    regime_gap_threshold: int = 5
    min_region_test_count: int = 0
    objective_name: str = "retail_profitability"
    promotion_profile: str = "research"
    run_mode: str = "research"
    target_contexts: tuple[str, ...] = ("vol_regime",)
    enabled_trigger_types: tuple[str, ...] = ("EVENT",)


@dataclass
class PlannedCampaignProposal:
    score: float
    event_type: str
    family: str
    rationale: Dict[str, Any]
    proposal: Dict[str, Any]


@dataclass
class CampaignPlanResult:
    program_id: str
    ranked_proposals: list[PlannedCampaignProposal] = field(default_factory=list)
    excluded_region_keys: list[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "ranked_proposals": [
                {
                    "score": item.score,
                    "event_type": item.event_type,
                    "family": item.family,
                    "rationale": item.rationale,
                    "proposal": item.proposal,
                }
                for item in self.ranked_proposals
            ],
            "excluded_region_keys": list(self.excluded_region_keys),
            "summary": dict(self.summary),
        }


class CampaignPlanner:
    def __init__(self, config: CampaignPlannerConfig):
        self.config = config
        self.data_root = Path(config.data_root) if config.data_root is not None else get_data_root()
        self.registry_root = Path(config.registry_root)
        self.paths = ensure_memory_store(config.program_id, data_root=self.data_root)
        self.search_space_path = _search_space_path(self.registry_root, config.search_space_path)
        self.registry = {
            "events": self._load_yaml(self.registry_root / "events.yaml"),
            "templates": self._load_yaml(self.registry_root / "templates.yaml"),
            "search_limits": self._load_yaml(self.registry_root / "search_limits.yaml"),
        }
        self.event_weights = self._event_priority_weights(self.search_space_path)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            _LOG.warning("Failed to load YAML from %s", path, exc_info=True)
            return {}

    def _event_priority_weights(self, search_space_path: Path | None) -> Dict[str, float]:
        try:
            return load_event_priority_weights(search_space_path)
        except Exception:
            return {}

    def _memory(self) -> Dict[str, pd.DataFrame]:
        return {
            "tested_regions": _tested_region_columns(read_memory_table(self.config.program_id, "tested_regions", data_root=self.data_root)),
            "failures": read_memory_table(self.config.program_id, "failures", data_root=self.data_root),
            "region_statistics": read_memory_table(self.config.program_id, "region_statistics", data_root=self.data_root),
            "event_statistics": read_memory_table(self.config.program_id, "event_statistics", data_root=self.data_root),
            "template_statistics": read_memory_table(self.config.program_id, "template_statistics", data_root=self.data_root),
            "context_statistics": read_memory_table(self.config.program_id, "context_statistics", data_root=self.data_root),
            "reflections": read_memory_table(self.config.program_id, "reflections", data_root=self.data_root),
        }

    def _candidate_events(self, tested_regions: pd.DataFrame) -> list[dict[str, Any]]:
        events_registry = self.registry.get("events", {}).get("events", {})
        event_to_family = {event_type: _family_from_event_type(event_type, events_registry) for event_type in events_registry}
        event_counts = _event_counts(tested_regions)
        family_counts = _family_counts(tested_regions, event_to_family)
        regime_counts = _count_contexts(tested_regions)
        mechanical_region_keys = _mechanical_exclusions(tested_regions)
        mechanical_event_types = _mechanical_event_types(tested_regions)
        penalties = _failure_penalties(tested_regions)
        weights = self.event_weights
        max_weight = max(weights.values(), default=DEFAULT_EVENT_PRIORITY_WEIGHT)
        candidates: list[dict[str, Any]] = []

        for event_type, meta in events_registry.items():
            if not bool(meta.get("enabled", True)):
                continue
            if not bool(meta.get("is_trade_trigger", True)):
                continue

            family = event_to_family.get(event_type, "")
            event_count = int(event_counts.get(event_type, 0))
            family_count = int(family_counts.get(family, 0))
            if self.config.min_region_test_count > 0 and event_count >= self.config.min_region_test_count:
                continue

            weight = float(weights.get(event_type, DEFAULT_EVENT_PRIORITY_WEIGHT))
            priority_score = weight / max_weight if max_weight > 0 else 0.5
            family_gap_score = 1.0 / (1.0 + family_count)
            event_gap_score = 1.0 / (1.0 + event_count)

            regime_score = 0.0
            context_payload: Dict[str, list[str]] = {}
            for context_name in self.config.target_contexts:
                counts = regime_counts.get(context_name, Counter())
                if not counts:
                    continue
                min_count = min(int(v) for v in counts.values()) if counts else 0
                if min_count <= self.config.regime_gap_threshold:
                    regime_score = max(regime_score, 1.0 - (min_count / max(self.config.regime_gap_threshold, 1)))
                    low_labels = [label for label, value in counts.items() if int(value) == min_count]
                    if low_labels:
                        context_payload[context_name] = low_labels[:2]

            if not context_payload and "vol_regime" in self.config.target_contexts:
                context_payload = {"vol_regime": ["low", "high"]}

            mechanical_penalty = 1.0 if event_type in mechanical_event_types else 0.0
            history_penalty = penalties.get(event_type, 0.0)
            score = (
                1.8 * priority_score
                + 1.2 * family_gap_score
                + 0.9 * event_gap_score
                + 0.8 * regime_score
                - 2.5 * mechanical_penalty
                - history_penalty
            )

            templates = _allowed_templates_for_family(family, self.registry.get("templates", {}))
            proposal = self._build_proposal_payload(
                event_type=event_type,
                family=family,
                templates=templates,
                contexts=context_payload,
                score=score,
                weight=weight,
                event_count=event_count,
                family_count=family_count,
                regime_score=regime_score,
                priority_score=priority_score,
                family_gap_score=family_gap_score,
                event_gap_score=event_gap_score,
                history_penalty=history_penalty,
                excluded_region_keys=mechanical_region_keys,
            )
            if proposal is not None:
                candidates.append(proposal)

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates

    def _build_proposal_payload(
        self,
        *,
        event_type: str,
        family: str,
        templates: Sequence[str],
        contexts: Dict[str, list[str]],
        score: float,
        weight: float,
        event_count: int,
        family_count: int,
        regime_score: float,
        priority_score: float,
        family_gap_score: float,
        event_gap_score: float,
        history_penalty: float,
        excluded_region_keys: set[str] | None = None,
    ) -> Dict[str, Any] | None:
        if score <= -10.0:
            return None
        start, end = _default_date_scope(self.config.lookback_days)
        proposal = {
            "program_id": self.config.program_id,
            "start": start,
            "end": end,
            "symbols": list(self.config.symbols),
            "trigger_space": {
                "allowed_trigger_types": list(self.config.enabled_trigger_types),
                "events": {"include": [event_type]},
            },
            "templates": list(dict.fromkeys(templates))[:4],
            "description": f"Autonomous campaign proposal for {event_type}" + (f" (family={family})" if family else ""),
            "run_mode": self.config.run_mode,
            "objective_name": self.config.objective_name,
            "promotion_profile": self.config.promotion_profile,
            "timeframe": self.config.timeframe,
            "instrument_classes": list(self.config.instrument_classes),
            "horizons_bars": list(self.config.horizon_bars),
            "directions": list(self.config.directions),
            "entry_lags": list(self.config.entry_lags),
            "contexts": contexts,
            "search_control": {
                "max_hypotheses_total": 1000,
                "max_hypotheses_per_template": 500,
                "max_hypotheses_per_event_family": 500,
                "random_seed": 42,
            },
            "artifacts": {
                "campaign_memory": True,
                "proposal_audit": True,
                "search_frontier": True,
            },
            "knobs": {},
        }
        rationale = {
            "event_weight": weight,
            "priority_score": priority_score,
            "family_gap_score": family_gap_score,
            "event_gap_score": event_gap_score,
            "regime_score": regime_score,
            "history_penalty": history_penalty,
            "event_count": event_count,
            "family_count": family_count,
        }
        proposal_key = region_key(
            {
                "program_id": proposal["program_id"],
                "symbol_scope": ",".join(proposal["symbols"]),
                "event_type": event_type,
                "trigger_type": "EVENT",
                "template_id": ",".join(proposal["templates"]),
                "direction": ",".join(proposal["directions"]),
                "horizon": ",".join(str(value) for value in proposal["horizons_bars"]),
                "entry_lag": ",".join(str(value) for value in proposal["entry_lags"]),
                "context_hash": canonical_json(contexts),
            }
        )
        rationale["proposal_region_key"] = proposal_key
        if excluded_region_keys and proposal_key in excluded_region_keys:
            return None
        return {
            "score": float(score),
            "event_type": event_type,
            "family": family,
            "rationale": rationale,
            "proposal": proposal,
        }

    def plan(self) -> CampaignPlanResult:
        memory = self._memory()
        tested_regions = memory["tested_regions"]
        candidate_rows = self._candidate_events(tested_regions)
        ranked = [
            PlannedCampaignProposal(
                score=float(row["score"]),
                event_type=str(row["event_type"]),
                family=str(row["family"]),
                rationale=dict(row["rationale"]),
                proposal=dict(row["proposal"]),
            )
            for row in candidate_rows[: self.config.max_proposals]
        ]
        summary = {
            "tested_regions": int(len(tested_regions)),
            "candidate_pool": int(len(candidate_rows)),
            "top_event_type": ranked[0].event_type if ranked else "",
            "top_family": ranked[0].family if ranked else "",
            "search_space_path": str(self.search_space_path),
        }
        return CampaignPlanResult(
            program_id=self.config.program_id,
            ranked_proposals=ranked,
            excluded_region_keys=sorted(self._excluded_region_keys(tested_regions)),
            summary=summary,
        )

    def _excluded_region_keys(self, tested_regions: pd.DataFrame) -> set[str]:
        if tested_regions.empty or "failure_cause_class" not in tested_regions.columns:
            return set()
        mask = tested_regions["failure_cause_class"].astype(str).str.strip().str.lower() == "mechanical"
        if not mask.any() or "region_key" not in tested_regions.columns:
            return set()
        return set(tested_regions.loc[mask, "region_key"].astype(str).tolist())

    def top_proposal(self) -> Dict[str, Any] | None:
        plan = self.plan()
        if not plan.ranked_proposals:
            return None
        return plan.ranked_proposals[0].proposal


def run_campaign_planner_cycle(
    *,
    program_id: str,
    registry_root: Path,
    data_root: Path | None = None,
    search_space_path: Path | None = None,
    symbols: Sequence[str] = ("BTCUSDT",),
    plan_only: bool = False,
    dry_run: bool = False,
    check: bool = False,
    lookback_days: int = 90,
    max_proposals: int = 10,
) -> Dict[str, Any]:
    planner = CampaignPlanner(
        CampaignPlannerConfig(
            program_id=program_id,
            registry_root=Path(registry_root),
            data_root=Path(data_root) if data_root is not None else None,
            search_space_path=Path(search_space_path) if search_space_path is not None else None,
            symbols=tuple(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()),
            lookback_days=int(lookback_days),
            max_proposals=int(max_proposals),
        )
    )
    plan = planner.plan()
    top = planner.top_proposal()
    if top is None:
        return {"plan": plan.to_dict(), "execution": None, "run_id": "", "proposal": None}

    proposal_path = planner.paths.proposals_dir / "planned_proposal.yaml"
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(yaml.safe_dump(top, sort_keys=False), encoding="utf-8")
    proposal = load_agent_proposal(proposal_path)
    run_id = generate_run_id(program_id, proposal.to_dict())
    execution = issue_proposal(
        proposal_path,
        registry_root=Path(registry_root),
        data_root=Path(data_root) if data_root is not None else None,
        run_id=run_id,
        plan_only=plan_only,
        dry_run=dry_run,
        check=check,
    )
    return {
        "plan": plan.to_dict(),
        "execution": execution,
        "run_id": run_id,
        "proposal": proposal.to_dict(),
        "proposal_path": str(proposal_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score campaign memory and emit ranked proposals.")
    parser.add_argument("--program_id", required=True)
    parser.add_argument("--registry_root", default="project/configs/registries")
    parser.add_argument("--data_root", default=None)
    parser.add_argument("--search_space_path", default=None)
    parser.add_argument("--symbols", default="BTCUSDT")
    parser.add_argument("--lookback_days", type=int, default=90)
    parser.add_argument("--max_proposals", type=int, default=10)
    parser.add_argument("--plan_only", type=int, default=0)
    parser.add_argument("--dry_run", type=int, default=0)
    parser.add_argument("--check", type=int, default=0)
    parser.add_argument("--execute", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    plan_only = bool(args.plan_only)
    execute = bool(args.execute)
    result = run_campaign_planner_cycle(
        program_id=args.program_id,
        registry_root=Path(args.registry_root),
        data_root=Path(args.data_root) if args.data_root else None,
        search_space_path=Path(args.search_space_path) if args.search_space_path else None,
        symbols=tuple(sym.strip().upper() for sym in str(args.symbols).split(",") if sym.strip()),
        lookback_days=int(args.lookback_days),
        max_proposals=int(args.max_proposals),
        plan_only=plan_only or not execute,
        dry_run=bool(args.dry_run),
        check=bool(args.check),
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    execution = result.get("execution") or {}
    if isinstance(execution, dict):
        nested = execution.get("execution")
        if isinstance(nested, dict):
            return int(nested.get("returncode", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
