from __future__ import annotations

import importlib
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from project import PROJECT_ROOT
from project.core.config import get_data_root
from project.io.utils import ensure_dir, read_parquet, write_parquet
from project.research.promotion import (
    build_promotion_statistical_audit,
    promote_candidates,
    stabilize_promoted_output_schema,
)
from project.research.services.reporting_service import write_promotion_reports
from project.research.validation.evidence_bundle import (
    bundle_to_flat_record,
    serialize_evidence_bundles,
)
from project.specs.gates import load_gates_spec as _load_gates_spec
from project.specs.manifest import finalize_manifest, load_run_manifest, start_manifest
from project.specs.objective import resolve_objective_profile_contract
from project.specs.ontology import ontology_spec_hash


@dataclass(frozen=True)
class PromotionConfig:
    run_id: str
    symbols: str
    out_dir: Optional[Path]
    max_q_value: float
    min_events: int
    min_stability_score: float
    min_sign_consistency: float
    min_cost_survival_ratio: float
    max_negative_control_pass_rate: float
    min_tob_coverage: float
    require_hypothesis_audit: bool
    allow_missing_negative_controls: bool
    require_multiplicity_diagnostics: bool
    min_dsr: float
    max_overlap_ratio: float
    max_profile_correlation: float
    allow_discovery_promotion: bool
    program_id: str
    retail_profile: str
    objective_name: str
    objective_spec: Optional[str]
    retail_profiles_spec: Optional[str]
    promotion_profile: str = "auto"

    def resolved_out_dir(self) -> Path:
        data_root = get_data_root()
        return self.out_dir if self.out_dir is not None else data_root / "reports" / "promotions" / self.run_id

    def manifest_params(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "symbols": self.symbols,
            "out_dir": str(self.out_dir) if self.out_dir is not None else None,
            "max_q_value": self.max_q_value,
            "min_events": self.min_events,
            "min_stability_score": self.min_stability_score,
            "min_sign_consistency": self.min_sign_consistency,
            "min_cost_survival_ratio": self.min_cost_survival_ratio,
            "max_negative_control_pass_rate": self.max_negative_control_pass_rate,
            "min_tob_coverage": self.min_tob_coverage,
            "require_hypothesis_audit": int(self.require_hypothesis_audit),
            "allow_missing_negative_controls": int(self.allow_missing_negative_controls),
            "require_multiplicity_diagnostics": int(self.require_multiplicity_diagnostics),
            "min_dsr": self.min_dsr,
            "max_overlap_ratio": self.max_overlap_ratio,
            "max_profile_correlation": self.max_profile_correlation,
            "allow_discovery_promotion": int(self.allow_discovery_promotion),
            "program_id": self.program_id,
            "retail_profile": self.retail_profile,
            "objective_name": self.objective_name,
            "objective_spec": self.objective_spec,
            "retail_profiles_spec": self.retail_profiles_spec,
            "promotion_profile": self.promotion_profile,
        }


@dataclass(frozen=True)
class ResolvedPromotionPolicy:
    promotion_profile: str
    base_min_events: int
    dynamic_min_events: Dict[str, int]
    min_net_expectancy_bps: float
    max_fee_plus_slippage_bps: Optional[float]
    max_daily_turnover_multiple: Optional[float]
    require_retail_viability: bool
    require_low_capital_viability: bool
    enforce_baseline_beats_complexity: bool
    enforce_placebo_controls: bool
    enforce_timeframe_consensus: bool


@dataclass
class PromotionServiceResult:
    exit_code: int
    output_dir: Path
    audit_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    promoted_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def _trace_payload(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def _failed_stages_from_trace(raw: Any) -> List[str]:
    payload = _trace_payload(raw)
    failed: List[str] = []
    for stage, meta in payload.items():
        if not isinstance(meta, dict):
            continue
        if meta.get("passed") is False:
            failed.append(str(stage))
    return failed


def _primary_reject_reason(row: Dict[str, Any]) -> str:
    primary = str(row.get("promotion_fail_reason_primary", "")).strip()
    if primary:
        return primary
    reject_reason = str(row.get("reject_reason", "")).strip()
    if not reject_reason:
        return ""
    return next((token for token in reject_reason.split("|") if token.strip()), "")


def _classify_rejection(row: Dict[str, Any], failed_stages: List[str]) -> str:
    primary_gate = str(row.get("promotion_fail_gate_primary", "")).strip().lower()
    primary_reason = _primary_reject_reason(row).strip().lower()
    reject_reason = str(row.get("reject_reason", "")).strip().lower()
    combined = " ".join([primary_gate, primary_reason, reject_reason, " ".join(failed_stages)])

    if any(token in combined for token in ["spec hash mismatch", "missing", "audit", "bridge_evaluation_failed", "unlocked candidates", "contract"]):
        return "contract_failure"
    if any(token in combined for token in ["oos_validation", "confirmatory", "validation", "test_support", "multiplicity_strict"]):
        return "weak_holdout_support"
    if any(
        token in combined
        for token in [
            "expectancy",
            "after_cost",
            "turnover",
            "retail",
            "low_capital",
            "dsr",
            "economic",
            "tradable",
        ]
    ):
        return "weak_economics"
    if any(
        token in combined
        for token in [
            "baseline",
            "complexity",
            "placebo",
            "timeframe_consensus",
            "overlap",
            "profile_correlation",
            "regime_unstable",
            "scope",
        ]
    ):
        return "scope_mismatch"
    if failed_stages:
        return "scope_mismatch"
    return "unclassified"


def _recommended_next_action_for_rejection(classification: str) -> str:
    mapping = {
        "contract_failure": "repair_pipeline",
        "weak_holdout_support": "run_confirmatory",
        "weak_economics": "stop_or_reframe",
        "scope_mismatch": "narrow_scope",
        "unclassified": "review_manually",
    }
    return mapping.get(str(classification).strip().lower(), "review_manually")


def _annotate_promotion_audit_decisions(audit_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df.empty:
        out = audit_df.copy()
        out["primary_reject_reason"] = pd.Series(dtype="object")
        out["failed_gate_count"] = pd.Series(dtype="int64")
        out["failed_gate_list"] = pd.Series(dtype="object")
        out["weakest_fail_stage"] = pd.Series(dtype="object")
        return out

    rows: List[Dict[str, Any]] = []
    for row in audit_df.to_dict(orient="records"):
        failed_stages = _failed_stages_from_trace(row.get("promotion_metrics_trace", {}))
        primary_gate = str(row.get("promotion_fail_gate_primary", "")).strip()
        weakest_fail_stage = failed_stages[0] if failed_stages else primary_gate
        rows.append(
            {
                **row,
                "primary_reject_reason": _primary_reject_reason(row),
                "failed_gate_count": int(len(failed_stages)),
                "failed_gate_list": "|".join(failed_stages),
                "weakest_fail_stage": weakest_fail_stage,
                "rejection_classification": _classify_rejection(row, failed_stages),
                "recommended_next_action": _recommended_next_action_for_rejection(
                    _classify_rejection(row, failed_stages)
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_promotion_decision_diagnostics(audit_df: pd.DataFrame) -> Dict[str, Any]:
    if audit_df.empty:
        return {
            "candidates_total": 0,
            "promoted_count": 0,
            "rejected_count": 0,
            "primary_fail_gate_counts": {},
            "primary_reject_reason_counts": {},
            "failed_stage_counts": {},
            "rejection_classification_counts": {},
            "recommended_next_action_counts": {},
            "mean_failed_gate_count_rejected": 0.0,
        }

    decision_counts = (
        audit_df.get("promotion_decision", pd.Series(dtype="object"))
        .astype(str)
        .value_counts()
        .to_dict()
    )
    rejected = audit_df[
        audit_df.get("promotion_decision", pd.Series(dtype="object")).astype(str) == "rejected"
    ].copy()
    fail_gates = (
        rejected.get("promotion_fail_gate_primary", pd.Series(dtype="object"))
        .astype(str)
        .str.strip()
    )
    fail_reasons = (
        rejected.get("primary_reject_reason", pd.Series(dtype="object"))
        .astype(str)
        .str.strip()
    )
    rejection_classes = (
        rejected.get("rejection_classification", pd.Series(dtype="object"))
        .astype(str)
        .str.strip()
    )
    next_actions = (
        rejected.get("recommended_next_action", pd.Series(dtype="object"))
        .astype(str)
        .str.strip()
    )
    stage_counter: Counter[str] = Counter()
    for value in rejected.get("failed_gate_list", pd.Series(dtype="object")).astype(str):
        for token in value.split("|"):
            token = token.strip()
            if token:
                stage_counter[token] += 1

    return {
        "candidates_total": int(len(audit_df)),
        "promoted_count": int(decision_counts.get("promoted", 0)),
        "rejected_count": int(decision_counts.get("rejected", 0)),
        "primary_fail_gate_counts": {
            str(k): int(v)
            for k, v in fail_gates[fail_gates != ""].value_counts().to_dict().items()
        },
        "primary_reject_reason_counts": {
            str(k): int(v)
            for k, v in fail_reasons[fail_reasons != ""].value_counts().to_dict().items()
        },
        "failed_stage_counts": dict(sorted(stage_counter.items())),
        "rejection_classification_counts": {
            str(k): int(v)
            for k, v in rejection_classes[rejection_classes != ""].value_counts().to_dict().items()
        },
        "recommended_next_action_counts": {
            str(k): int(v)
            for k, v in next_actions[next_actions != ""].value_counts().to_dict().items()
        },
        "mean_failed_gate_count_rejected": 0.0
        if rejected.empty
        else float(pd.to_numeric(rejected.get("failed_gate_count", 0), errors="coerce").fillna(0).mean()),
    }


def _read_csv_or_parquet(path: Path) -> pd.DataFrame:
    if path.suffix.lower() != ".parquet":
        return pd.read_csv(path)
    try:
        return pd.read_parquet(path)
    except (ImportError, OSError, ValueError):
        csv_fallback = path.with_suffix(".csv")
        if csv_fallback.exists():
            return pd.read_csv(csv_fallback)
        raise


def _read_bridge_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _load_bridge_metrics(bridge_root: Path, symbol: str | None = None) -> pd.DataFrame:
    del symbol
    versioned_files = list(bridge_root.rglob("*_v1.csv"))
    parquet_files = list(bridge_root.rglob("bridge_evaluation.parquet"))
    fallback_csv_files = [
        path
        for path in bridge_root.rglob("*.csv")
        if path not in versioned_files
    ]
    ordered_files = [*versioned_files, *parquet_files, *fallback_csv_files]
    if not ordered_files:
        return pd.DataFrame()
    frames = [_read_bridge_table(path) for path in ordered_files]
    out = pd.concat(frames, ignore_index=True)
    dedupe_cols = [col for col in ("candidate_id", "event_type", "symbol") if col in out.columns]
    if dedupe_cols:
        out = out.drop_duplicates(subset=dedupe_cols, keep="first").reset_index(drop=True)
    return out


def _merge_bridge_metrics(phase2_df: pd.DataFrame, bridge_df: pd.DataFrame) -> pd.DataFrame:
    if bridge_df.empty:
        return phase2_df
    out = pd.merge(
        phase2_df,
        bridge_df[["candidate_id", "event_type", "gate_bridge_tradable", "bridge_validation_after_cost_bps"]],
        on=["candidate_id", "event_type"],
        how="left",
        suffixes=("", "_bridge"),
    )
    if "gate_bridge_tradable_bridge" in out.columns:
        out["gate_bridge_tradable"] = out["gate_bridge_tradable_bridge"].combine_first(out["gate_bridge_tradable"])
        out = out.drop(columns=["gate_bridge_tradable_bridge"])
    return out


def _parse_run_symbols(raw_symbols: Any) -> List[str]:
    if isinstance(raw_symbols, (list, tuple, set)):
        values = raw_symbols
    else:
        values = str(raw_symbols or "").split(",")
    ordered: List[str] = []
    seen: set[str] = set()
    for value in values:
        symbol = str(value).strip().upper()
        if not symbol or symbol in seen:
            continue
        ordered.append(symbol)
        seen.add(symbol)
    return ordered


def _hydrate_edge_candidates_from_phase2(
    *,
    run_id: str,
    run_symbols: List[str],
    source_run_mode: str,
    data_root: Path,
) -> pd.DataFrame:
    if not run_symbols:
        return pd.DataFrame()
    export_module = importlib.import_module("project.pipelines.research.export_edge_candidates")
    rows = export_module._collect_phase2_candidates(run_id, run_symbols=run_symbols)
    candidates_df = pd.DataFrame(rows)
    if candidates_df.empty:
        return candidates_df

    from project.research.helpers.shrinkage import _apply_hierarchical_shrinkage

    candidates_df = _apply_hierarchical_shrinkage(
        candidates_df,
        train_only_lambda=True,
        split_col="split_label",
        run_mode=source_run_mode,
    )
    is_confirmatory = bool(export_module._is_confirmatory_run_mode(source_run_mode))
    current_spec_hash = ontology_spec_hash(PROJECT_ROOT.parent)
    candidates_df = export_module._normalize_edge_candidates_df(
        candidates_df,
        run_mode=source_run_mode,
        is_confirmatory=is_confirmatory,
        current_spec_hash=current_spec_hash,
    )

    out_dir = data_root / "reports" / "edge_candidates" / run_id
    ensure_dir(out_dir)
    write_parquet(candidates_df, out_dir / "edge_candidates_normalized.parquet")
    (out_dir / "edge_candidates_normalized.json").write_text(
        candidates_df.to_json(orient="records", indent=2),
        encoding="utf-8",
    )
    return candidates_df


def _load_negative_control_summary(run_id: str) -> Dict[str, Any]:
    data_root = get_data_root()
    path = data_root / "reports" / "negative_control" / run_id / "negative_control_summary.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _load_dynamic_min_events_by_event(spec_root: str | Path) -> Dict[str, int]:
    path = Path(spec_root) / "spec" / "states" / "state_registry.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (ImportError, OSError, UnicodeDecodeError):
        logging.warning("Failed loading state_registry")
        return {}
    except yaml.YAMLError:
        logging.warning("Failed loading state_registry")
        return {}

    out: Dict[str, int] = {}
    default_min = data.get("defaults", {}).get("min_events", 0)
    for state_row in data.get("states", []):
        event_type = state_row.get("source_event_type")
        if event_type:
            out[event_type] = max(out.get(event_type, default_min), state_row.get("min_events", default_min))
    return out


def _resolve_promotion_profile(configured_profile: str, source_run_mode: str) -> str:
    profile = str(configured_profile or "auto").strip().lower()
    if profile in {"research", "deploy"}:
        return profile
    if source_run_mode in {"confirmatory", "production", "certification", "promotion", "deploy"}:
        return "deploy"
    return "research"


def _resolve_promotion_policy(
    *,
    config: PromotionConfig,
    contract: Any,
    source_run_mode: str,
    project_root: Path,
) -> ResolvedPromotionPolicy:
    profile = _resolve_promotion_profile(config.promotion_profile, source_run_mode)
    base_min_events = int(config.min_events)
    dynamic_min_events: Dict[str, int] = {}

    min_net_expectancy_bps = float(max(0.0, float(getattr(contract, "min_net_expectancy_bps", 0.0) or 0.0)))
    max_fee_plus_slippage_bps = getattr(contract, "max_fee_plus_slippage_bps", None)
    max_daily_turnover_multiple = getattr(contract, "max_daily_turnover_multiple", None)
    require_retail_viability = bool(getattr(contract, "require_retail_viability", False))
    require_low_capital_viability = bool(getattr(contract, "require_low_capital_contract", False))
    enforce_baseline_beats_complexity = True
    enforce_placebo_controls = True
    enforce_timeframe_consensus = True

    if profile == "deploy":
        base_min_events = max(
            base_min_events,
            int(getattr(contract, "min_trade_count", base_min_events) or base_min_events),
        )
        dynamic_min_events = _load_dynamic_min_events_by_event(project_root)
    else:
        min_net_expectancy_bps = min(min_net_expectancy_bps, 1.5)
        require_retail_viability = False
        require_low_capital_viability = False
        enforce_baseline_beats_complexity = False
        enforce_placebo_controls = False
        enforce_timeframe_consensus = False

    return ResolvedPromotionPolicy(
        promotion_profile=profile,
        base_min_events=base_min_events,
        dynamic_min_events=dynamic_min_events,
        min_net_expectancy_bps=min_net_expectancy_bps,
        max_fee_plus_slippage_bps=max_fee_plus_slippage_bps,
        max_daily_turnover_multiple=max_daily_turnover_multiple,
        require_retail_viability=require_retail_viability,
        require_low_capital_viability=require_low_capital_viability,
        enforce_baseline_beats_complexity=enforce_baseline_beats_complexity,
        enforce_placebo_controls=enforce_placebo_controls,
        enforce_timeframe_consensus=enforce_timeframe_consensus,
    )


def execute_promotion(config: PromotionConfig) -> PromotionServiceResult:
    data_root = get_data_root()
    out_dir = config.resolved_out_dir()
    ensure_dir(out_dir)
    manifest = start_manifest("promote_candidates", config.run_id, config.manifest_params(), [], [])
    audit_df = pd.DataFrame()
    promoted_df = pd.DataFrame()
    diagnostics: Dict[str, Any] = {}

    try:
        source_manifest = load_run_manifest(config.run_id)
        source_run_mode = str(source_manifest.get("run_mode", "")).strip().lower()
        source_profile = str(source_manifest.get("discovery_profile", "")).strip().lower()
        confirmatory_rerun_run_id = str(source_manifest.get("confirmatory_rerun_run_id", "")).strip()
        candidate_origin_run_id = str(source_manifest.get("candidate_origin_run_id", "")).strip()
        program_id = str(source_manifest.get("program_id", config.program_id)).strip()
        if source_run_mode in {"discovery", "research"}:
            source_run_mode = "exploratory"
        is_exploratory = source_run_mode == "exploratory"
        is_confirmatory = source_run_mode in {"confirmatory", "production", "certification", "promotion", "deploy"}
        run_symbols = _parse_run_symbols(config.symbols or source_manifest.get("symbols"))
        if is_exploratory and not config.allow_discovery_promotion:
            raise ValueError(
                f"Promotion blocked for {config.run_id}: source run_mode={source_run_mode}. "
                "Promotion requires a confirmatory run."
            )

        contract = resolve_objective_profile_contract(
            project_root=PROJECT_ROOT,
            data_root=data_root,
            run_id=config.run_id,
            objective_name=config.objective_name.strip() or None,
            objective_spec_path=config.objective_spec,
            retail_profile_name=config.retail_profile.strip() or None,
            retail_profiles_spec_path=config.retail_profiles_spec,
            required=True,
        )
        candidates_path = data_root / "reports" / "edge_candidates" / config.run_id / "edge_candidates_normalized.parquet"
        if not candidates_path.exists():
            candidates_path = candidates_path.with_suffix(".csv")
        if candidates_path.exists():
            candidates_df = _read_csv_or_parquet(candidates_path)
        else:
            candidates_df = _hydrate_edge_candidates_from_phase2(
                run_id=config.run_id,
                run_symbols=run_symbols,
                source_run_mode=source_run_mode,
                data_root=data_root,
            )
            if candidates_df.empty:
                raise FileNotFoundError(f"Missing required candidates file: {candidates_path}")

        if is_confirmatory and not candidates_df.empty:
            if "confirmatory_locked" in candidates_df.columns:
                locked_candidates = candidates_df["confirmatory_locked"].fillna(False).astype(bool)
            else:
                locked_candidates = pd.Series(False, index=candidates_df.index, dtype=bool)
            if not bool(locked_candidates.all()):
                raise ValueError("Confirmatory run contains unlocked candidates.")
            curr_ontology_hash = ontology_spec_hash(PROJECT_ROOT.parent)
            frozen_hashes = candidates_df["frozen_spec_hash"].unique()
            if len(frozen_hashes) > 1 or frozen_hashes[0] != curr_ontology_hash:
                raise ValueError(
                    f"Spec hash mismatch in confirmatory run: {frozen_hashes} vs {curr_ontology_hash}"
                )

        ontology_hash = ontology_spec_hash(PROJECT_ROOT.parent)
        gate_spec = _load_gates_spec(PROJECT_ROOT.parent)
        promotion_confirmatory_gates = gate_spec.get("promotion_confirmatory_gates", {})
        hyp_registry_path = data_root / "reports" / "phase2" / config.run_id / "hypothesis_registry.parquet"
        hypothesis_index = {}
        if not hyp_registry_path.exists():
            hyp_registry_path = hyp_registry_path.with_suffix(".csv")
        if hyp_registry_path.exists():
            hyp_df = _read_csv_or_parquet(hyp_registry_path)
            hypothesis_index = {
                row["hypothesis_id"]: row.to_dict()
                for _, row in hyp_df.iterrows()
            }
        promotion_spec = {
            "ontology_spec_hash": ontology_hash,
            "source_run_mode": source_run_mode,
            "source_profile": source_profile,
            "confirmatory_rerun_run_id": confirmatory_rerun_run_id,
            "candidate_origin_run_id": candidate_origin_run_id,
            "program_id": program_id,
            "promotion_basis": "confirmatory_only" if is_confirmatory else "direct",
            "promotion_confirmatory_gates": promotion_confirmatory_gates,
        }
        negative_control_summary = _load_negative_control_summary(config.run_id)
        resolved_policy = _resolve_promotion_policy(
            config=config,
            contract=contract,
            source_run_mode=source_run_mode,
            project_root=PROJECT_ROOT.parent,
        )
        audit_df, promoted_df, diagnostics = promote_candidates(
            candidates_df=candidates_df,
            promotion_spec=promotion_spec,
            hypothesis_index=hypothesis_index,
            negative_control_summary=negative_control_summary,
            contract=contract,
            dynamic_min_events=resolved_policy.dynamic_min_events,
            base_min_events=resolved_policy.base_min_events,
            max_q_value=config.max_q_value,
            min_stability_score=config.min_stability_score,
            min_sign_consistency=config.min_sign_consistency,
            min_cost_survival_ratio=config.min_cost_survival_ratio,
            max_negative_control_pass_rate=config.max_negative_control_pass_rate,
            min_tob_coverage=config.min_tob_coverage,
            require_hypothesis_audit=config.require_hypothesis_audit,
            allow_missing_negative_controls=config.allow_missing_negative_controls,
            require_multiplicity_diagnostics=config.require_multiplicity_diagnostics,
            min_dsr=config.min_dsr,
            max_overlap_ratio=config.max_overlap_ratio,
            max_profile_correlation=config.max_profile_correlation,
            promotion_profile=resolved_policy.promotion_profile,
            min_net_expectancy_bps=resolved_policy.min_net_expectancy_bps,
            max_fee_plus_slippage_bps=resolved_policy.max_fee_plus_slippage_bps,
            max_daily_turnover_multiple=resolved_policy.max_daily_turnover_multiple,
            require_retail_viability=resolved_policy.require_retail_viability,
            require_low_capital_viability=resolved_policy.require_low_capital_viability,
            enforce_baseline_beats_complexity=resolved_policy.enforce_baseline_beats_complexity,
            enforce_placebo_controls=resolved_policy.enforce_placebo_controls,
            enforce_timeframe_consensus=resolved_policy.enforce_timeframe_consensus,
        )
        diagnostics["promotion_profile"] = resolved_policy.promotion_profile
        audit_statistical_df = build_promotion_statistical_audit(
            audit_df=audit_df,
            max_q_value=config.max_q_value,
            min_stability_score=config.min_stability_score,
            min_sign_consistency=config.min_sign_consistency,
            min_cost_survival_ratio=config.min_cost_survival_ratio,
            max_negative_control_pass_rate=config.max_negative_control_pass_rate,
            min_tob_coverage=config.min_tob_coverage,
            min_net_expectancy_bps=resolved_policy.min_net_expectancy_bps,
            max_fee_plus_slippage_bps=resolved_policy.max_fee_plus_slippage_bps,
            max_daily_turnover_multiple=resolved_policy.max_daily_turnover_multiple,
            require_hypothesis_audit=config.require_hypothesis_audit,
            allow_missing_negative_controls=config.allow_missing_negative_controls,
            require_retail_viability=bool(resolved_policy.require_retail_viability),
            require_low_capital_viability=bool(resolved_policy.require_low_capital_viability),
        )
        audit_statistical_df["source_run_mode"] = source_run_mode
        audit_statistical_df["source_profile"] = source_profile
        audit_statistical_df["promotion_profile"] = resolved_policy.promotion_profile
        audit_statistical_df["confirmatory_rerun_run_id"] = confirmatory_rerun_run_id
        audit_df = _annotate_promotion_audit_decisions(audit_statistical_df.copy())
        diagnostics["decision_summary"] = _build_promotion_decision_diagnostics(audit_df)
        promoted_df = stabilize_promoted_output_schema(
            promoted_df=promoted_df,
            audit_df=audit_df,
        ).copy()

        evidence_bundles = []
        if not audit_df.empty and "evidence_bundle_json" in audit_df.columns:
            for raw in audit_df["evidence_bundle_json"].astype(str).tolist():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    evidence_bundles.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        serialize_evidence_bundles(evidence_bundles, out_dir / "evidence_bundles.jsonl")
        evidence_bundle_summary = pd.DataFrame(
            [bundle_to_flat_record(bundle) for bundle in evidence_bundles]
        )
        decision_cols = [
            column
            for column in [
                "candidate_id",
                "event_type",
                "promotion_decision",
                "promotion_track",
                "rank_score",
                "rejection_reasons",
                "policy_version",
                "bundle_version",
            ]
            if column in evidence_bundle_summary.columns
        ]
        promotion_decisions = evidence_bundle_summary.reindex(columns=decision_cols)

        summary_rows = pd.DataFrame(
            columns=["candidate_id", "event_type", "stage", "statistic", "threshold", "pass_fail"]
        )
        if not audit_df.empty:
            stage_rows = []
            for row in audit_df.to_dict(orient="records"):
                candidate_id = str(row.get("candidate_id", "")).strip()
                event_type = str(row.get("event_type", "")).strip()
                trace = row.get("promotion_metrics_trace", "{}")
                try:
                    trace_payload = json.loads(trace) if isinstance(trace, str) else dict(trace or {})
                except (json.JSONDecodeError, TypeError, ValueError):
                    trace_payload = {}
                for stage, meta in sorted(trace_payload.items()):
                    observed = meta.get("observed", {}) if isinstance(meta, dict) else {}
                    thresholds = meta.get("thresholds", {}) if isinstance(meta, dict) else {}
                    stage_rows.append(
                        {
                            "candidate_id": candidate_id,
                            "event_type": event_type,
                            "stage": stage,
                            "statistic": json.dumps(observed, sort_keys=True),
                            "threshold": json.dumps(thresholds, sort_keys=True),
                            "pass_fail": bool(meta.get("passed", False)) if isinstance(meta, dict) else False,
                        }
                    )
            summary_rows = pd.DataFrame(stage_rows)
        diagnostics["evidence_bundle_count"] = int(len(evidence_bundles))
        diagnostics["evidence_bundle_summary_rows"] = int(len(evidence_bundle_summary))
        write_promotion_reports(
            out_dir=out_dir,
            audit_df=audit_df,
            promoted_df=promoted_df,
            evidence_bundle_summary=evidence_bundle_summary,
            promotion_decisions=promotion_decisions,
            diagnostics=diagnostics,
            promotion_summary=summary_rows,
        )
        finalize_manifest(manifest, "success", stats=diagnostics)
        return PromotionServiceResult(0, out_dir, audit_df, promoted_df, diagnostics)
    except Exception as exc:
        logging.exception("Promotion failed: %s", exc)
        finalize_manifest(manifest, "failed", error=str(exc))
        return PromotionServiceResult(1, out_dir, audit_df, promoted_df, diagnostics)
