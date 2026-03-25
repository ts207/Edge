from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from project.core.config import get_data_root


def data_root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else get_data_root()


def run_dir(run_id: str, root: Path | None = None) -> Path:
    return data_root(root) / "runs" / str(run_id)


def reports_dir(root: Path | None = None) -> Path:
    return data_root(root) / "reports"


def run_manifest_path(run_id: str, root: Path | None = None) -> Path:
    return run_dir(run_id, root) / "run_manifest.json"


def research_checklist_dir(run_id: str, root: Path | None = None) -> Path:
    return run_dir(run_id, root) / "research_checklist"


def checklist_path(run_id: str, root: Path | None = None) -> Path:
    return research_checklist_dir(run_id, root) / "checklist.json"


def release_signoff_path(run_id: str, root: Path | None = None) -> Path:
    return research_checklist_dir(run_id, root) / "release_signoff.json"


def kpi_scorecard_path(run_id: str, root: Path | None = None) -> Path:
    return run_dir(run_id, root) / "kpi_scorecard.json"


def promotion_dir(run_id: str, root: Path | None = None) -> Path:
    return reports_dir(root) / "promotions" / str(run_id)


def blueprint_dir(run_id: str, root: Path | None = None) -> Path:
    return reports_dir(root) / "strategy_blueprints" / str(run_id)


def promotion_summary_path(run_id: str, root: Path | None = None) -> Path:
    return promotion_dir(run_id, root) / "promotion_summary.json"


def promotion_report_path(run_id: str, root: Path | None = None) -> Path:
    return promotion_dir(run_id, root) / "promotion_report.json"


def promoted_blueprints_path(run_id: str, root: Path | None = None) -> Path:
    return promotion_dir(run_id, root) / "promoted_blueprints.jsonl"


def blueprint_summary_path(run_id: str, root: Path | None = None) -> Path:
    return blueprint_dir(run_id, root) / "blueprint_summary.json"


def phase2_candidates_path(run_id: str, event_type: str, root: Path | None = None) -> Path:
    base = reports_dir(root) / "phase2" / str(run_id) / str(event_type)
    parquet = base / "phase2_candidates.parquet"
    if parquet.exists():
        return parquet
    return base / "phase2_candidates.csv"


def load_json_dict(path: Path) -> Dict[str, Any]:
    if not Path(path).exists():
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
