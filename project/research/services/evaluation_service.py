from __future__ import annotations
from project.core.config import get_data_root
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

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
    event_families: List[str]
    total_candidates: int
    gate_pass_count: int
    gate_pass_rate: float
    top_fail_reasons: List[Dict[str, Any]]
    by_event_family: Dict[str, Dict[str, Any]]
    funnel_payload: Dict[str, Any] = field(default_factory=dict)

class EvaluationSummaryService:
    def __init__(self):
        self.data_root = get_data_root()
    def summarize_run(self, run_id: str, config: Optional[EvaluationSummaryConfig] = None) -> EvaluationSummaryResult:
        return EvaluationSummaryResult(run_id, "", "", {}, [], 0, 0, 0.0, [], {})
