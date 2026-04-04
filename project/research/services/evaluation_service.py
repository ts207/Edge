from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from project.core.config import get_data_root
from project.research.validation.contracts import (
    ValidationBundle,
    ValidatedCandidateRecord,
    ValidationDecision,
    ValidationMetrics,
    ValidationReasonCodes,
)
from project.research.validation.result_writer import (
    write_validation_bundle,
    write_validated_candidate_tables,
)


@dataclass
class EvaluationSummaryConfig:
    run_id: str
    phase2_root: Optional[Path] = None
    out_path: Optional[Path] = None
    funnel_out_path: Optional[Path] = None
    top_fail_reasons: int = 10


@dataclass
class EvaluationSummaryResult:
    run_id: str
    generated_at: str
    phase2_root: str
    source_files: Dict[str, str]
    primary_event_ids: List[str]
    event_families: List[str]
    total_candidates: int
    gate_pass_count: int
    gate_pass_rate: float
    top_fail_reasons: List[Dict[str, Any]]
    by_primary_event_id: Dict[str, Dict[str, Any]]
    by_event_family: Dict[str, Dict[str, Any]]
    funnel_payload: Dict[str, Any] = field(default_factory=dict)


class EvaluationSummaryService:
    def __init__(self):
        self.data_root = get_data_root()

    def summarize_run(
        self, run_id: str, config: Optional[EvaluationSummaryConfig] = None
    ) -> EvaluationSummaryResult:
        return EvaluationSummaryResult(run_id, "", "", {}, [], [], 0, 0, 0.0, [], {}, {})


class ValidationService:
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or get_data_root()

    def load_candidate_tables(self, run_id: str) -> dict[str, pd.DataFrame]:
        return {
            "promotion_audit": self._read_table(
                self.data_root / "reports" / "promotions" / run_id / "promotion_statistical_audit.parquet"
            ),
            "edge_candidates": self._read_table(
                self.data_root / "reports" / "edge_candidates" / run_id / "edge_candidates_normalized.parquet"
            ),
            "phase2_candidates": self._read_table(
                self.data_root / "reports" / "phase2" / run_id / "phase2_candidates.parquet"
            ),
        }

    def _read_table(self, path: Path) -> pd.DataFrame:
        if path.exists():
            if path.suffix.lower() == ".parquet":
                return pd.read_parquet(path)
            if path.suffix.lower() == ".csv":
                return pd.read_csv(path)
        alt = (
            path.with_suffix(".csv") 
            if path.suffix.lower() == ".parquet" 
            else path.with_suffix(".parquet")
        )
        if alt.exists():
            return self._read_table(alt)
        return pd.DataFrame()

    def create_validation_bundle(
        self, 
        run_id: str, 
        candidates_df: pd.DataFrame, 
        program_id: Optional[str] = None
    ) -> ValidationBundle:
        validated = []
        rejected = []
        inconclusive = []
        
        for _, row in candidates_df.iterrows():
            record = self._map_row_to_validated_record(row, run_id, program_id)
            if record.decision.status == "validated":
                validated.append(record)
            elif record.decision.status == "rejected":
                rejected.append(record)
            else:
                inconclusive.append(record)
                
        bundle = ValidationBundle(
            run_id=run_id,
            program_id=program_id,
            created_at=datetime.now().isoformat(),
            validated_candidates=validated,
            rejected_candidates=rejected,
            inconclusive_candidates=inconclusive,
            summary_stats={
                "total": len(candidates_df),
                "validated": len(validated),
                "rejected": len(rejected),
                "inconclusive": len(inconclusive),
            }
        )
        return bundle

    def _map_row_to_validated_record(
        self, 
        row: pd.Series | Dict[str, Any], 
        run_id: str, 
        program_id: Optional[str] = None
    ) -> ValidatedCandidateRecord:
        candidate_id = str(row.get("candidate_id", ""))
        
        # Determine status and reasons based on common columns
        # This is a basic mapping, can be expanded
        reasons = []
        
        # Check for common failure gates
        gates_to_check = {
            "gate_oos_validation": ValidationReasonCodes.INCONCLUSIVE_VALIDATION,
            "gate_after_cost_positive": ValidationReasonCodes.FAILED_COST_SURVIVAL,
            "gate_after_cost_stressed_positive": ValidationReasonCodes.FAILED_COST_SURVIVAL,
            "gate_c_regime_stable": ValidationReasonCodes.FAILED_REGIME_SUPPORT,
            "gate_multiplicity": ValidationReasonCodes.FAILED_MULTIPLICITY_THRESHOLD,
        }
        
        for gate, code in gates_to_check.items():
            val = row.get(gate)
            if val is not None:
                if not bool(val):
                    reasons.append(code)
        
        # Special check for n_events
        n_events = row.get("n_events", row.get("n_obs", 0))
        if n_events < 20: # Example threshold
            reasons.append(ValidationReasonCodes.INSUFFICIENT_SAMPLE_SUPPORT)

        status = "validated" if not reasons else "rejected"
        
        # If it's missing critical data, it might be inconclusive
        if pd.isna(row.get("p_value")) and pd.isna(row.get("expectancy")):
             status = "inconclusive"
             reasons.append(ValidationReasonCodes.INSUFFICIENT_DATA)

        decision = ValidationDecision(
            status=status,
            candidate_id=candidate_id,
            run_id=run_id,
            program_id=program_id,
            reason_codes=list(set(reasons)),
            summary=""
        )
        
        metrics = ValidationMetrics(
            sample_count=int(n_events) if not pd.isna(n_events) else None,
            expectancy=float(row.get("expectancy")) if not pd.isna(row.get("expectancy")) else None,
            net_expectancy=float(row.get("net_expectancy_bps")) if not pd.isna(row.get("net_expectancy_bps")) else None,
            p_value=float(row.get("p_value")) if not pd.isna(row.get("p_value")) else None,
            q_value=float(row.get("q_value")) if not pd.isna(row.get("q_value")) else None,
            stability_score=float(row.get("stability_score")) if not pd.isna(row.get("stability_score")) else None,
        )
        
        return ValidatedCandidateRecord(
            candidate_id=candidate_id,
            decision=decision,
            metrics=metrics,
            anchor_summary=str(row.get("anchor_summary", "")),
            template_id=str(row.get("rule_template", row.get("template_id", ""))),
            direction=str(row.get("direction", "")),
            horizon_bars=int(row.get("horizon", row.get("horizon_bars", 0))),
            validation_stage_version="v1"
        )

    def run_validation_stage(
        self, 
        run_id: str, 
        candidates_df: pd.DataFrame, 
        program_id: Optional[str] = None
    ) -> ValidationBundle:
        bundle = self.create_validation_bundle(run_id, candidates_df, program_id)
        write_validation_bundle(bundle)
        write_validated_candidate_tables(bundle)
        return bundle

    def build_validation_bundle_from_legacy_run(
        self, 
        run_id: str, 
        program_id: Optional[str] = None
    ) -> Optional[ValidationBundle]:
        """
        Compatibility bridge: creates a temporary validation bundle from legacy outputs.
        """
        tables = self.load_candidate_tables(run_id)
        candidates_df = pd.DataFrame()
        for source in ("edge_candidates", "promotion_audit", "phase2_candidates"):
            if not tables[source].empty:
                candidates_df = tables[source]
                break
        
        if candidates_df.empty:
            return None
            
        bundle = self.create_validation_bundle(run_id, candidates_df, program_id)
        # Mark as compatibility-generated
        bundle.summary_stats["validation_stage_version"] = "compat_legacy_bridge_v1"
        
        # Persist it
        write_validation_bundle(bundle, base_dir=self.data_root / "reports" / "validation" / run_id)
        
        return bundle
