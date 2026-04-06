"""
Historical artifact audit scanner.

Scans promotion/export/report artifact trees to identify candidate artifacts,
infer their statistical regime and audit status, and emit audit inventory outputs.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from project.core.config import get_data_root
from project.io.utils import read_parquet
from project.research.contracts.stat_regime import (
    ArtifactAuditStamp,
    AUDIT_STATUS_CURRENT,
    AUDIT_STATUS_DEGRADED,
    AUDIT_STATUS_LEGACY,
    AUDIT_STATUS_MANUAL_REVIEW_REQUIRED,
    AUDIT_STATUS_UNKNOWN,
    STAT_REGIME_POST_AUDIT,
    STAT_REGIME_PRE_AUDIT,
    STAT_REGIME_UNKNOWN,
    ARTIFACT_AUDIT_VERSION_PHASE1_V1,
    infer_stat_regime_from_artifact_metadata,
)


log = logging.getLogger(__name__)

ARTIFACT_TYPES = {
    "promotion_audit": {"promotion_audit.parquet", "promotion_audit.csv"},
    "promoted_candidates": {"promoted_candidates.parquet", "promoted_candidates.csv"},
    "evidence_bundle_summary": {"evidence_bundle_summary.parquet", "evidence_bundle_summary.csv"},
    "promotion_lineage_audit": {"promotion_lineage_audit.json"},
}

AUDIT_INVENTORY_SCHEMA_VERSION = "audit_inventory_v1"


@dataclass
class ArtifactInventoryRow:
    run_id: str
    candidate_id: str
    hypothesis_id: str
    campaign_id: str
    program_id: str
    artifact_path: str
    artifact_type: str
    created_at: str
    stat_regime: str
    audit_status: str
    audit_reason: str
    requires_repromotion: bool
    requires_manual_review: bool
    artifact_audit_version: str
    inference_confidence: str
    policy_version: str
    bundle_version: str
    q_value: Optional[float]
    q_value_scope: Optional[float]
    effective_q_value: Optional[float]
    num_tests_scope: Optional[int]
    multiplicity_scope_mode: Optional[str]
    search_scope_version: Optional[str]
    search_burden_estimated: Optional[bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "hypothesis_id": self.hypothesis_id,
            "campaign_id": self.campaign_id,
            "program_id": self.program_id,
            "artifact_path": self.artifact_path,
            "artifact_type": self.artifact_type,
            "created_at": self.created_at,
            "stat_regime": self.stat_regime,
            "audit_status": self.audit_status,
            "audit_reason": self.audit_reason,
            "requires_repromotion": self.requires_repromotion,
            "requires_manual_review": self.requires_manual_review,
            "artifact_audit_version": self.artifact_audit_version,
            "inference_confidence": self.inference_confidence,
            "policy_version": self.policy_version,
            "bundle_version": self.bundle_version,
            "q_value": self.q_value,
            "q_value_scope": self.q_value_scope,
            "effective_q_value": self.effective_q_value,
            "num_tests_scope": self.num_tests_scope,
            "multiplicity_scope_mode": self.multiplicity_scope_mode,
            "search_scope_version": self.search_scope_version,
            "search_burden_estimated": self.search_burden_estimated,
        }


@dataclass
class AuditInventoryResult:
    rows: List[ArtifactInventoryRow]
    run_id_counts: Dict[str, int]
    stat_regime_counts: Dict[str, int]
    audit_status_counts: Dict[str, int]
    requires_repromotion_count: int
    requires_manual_review_count: int
    scanned_artifact_paths: List[str]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": AUDIT_INVENTORY_SCHEMA_VERSION,
            "total_rows": len(self.rows),
            "run_id_counts": self.run_id_counts,
            "stat_regime_counts": self.stat_regime_counts,
            "audit_status_counts": self.audit_status_counts,
            "requires_repromotion_count": self.requires_repromotion_count,
            "requires_manual_review_count": self.requires_manual_review_count,
            "scanned_artifact_count": len(self.scanned_artifact_paths),
            "error_count": len(self.errors),
            "rows": [row.to_dict() for row in self.rows],
        }


def _get_file_created_at(path: Path) -> str:
    try:
        stat = path.stat()
        dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except OSError:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _detect_artifact_type(filename: str) -> Optional[str]:
    clean = filename.lower().strip()
    for artifact_type, patterns in ARTIFACT_TYPES.items():
        for pattern in patterns:
            if clean == pattern.lower():
                return artifact_type
    return None


def _load_artifact_file(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".parquet":
        df = read_parquet(path)
        return df.to_dict(orient="records")
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        return df.to_dict(orient="records")
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            if "rows" in payload:
                return payload["rows"]
            return [payload]
        if isinstance(payload, list):
            return payload
    return []


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        import math
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _parse_created_at(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _build_inventory_row(
    row: Dict[str, Any],
    *,
    artifact_path: str,
    artifact_type: str,
    created_at: str,
) -> ArtifactInventoryRow:
    artifact_dt = _parse_created_at(created_at)
    stamp = infer_stat_regime_from_artifact_metadata(row, artifact_timestamp=artifact_dt)
    return ArtifactInventoryRow(
        run_id=str(row.get("run_id", "")).strip(),
        candidate_id=str(row.get("candidate_id", "")).strip(),
        hypothesis_id=str(row.get("hypothesis_id", "")).strip(),
        campaign_id=str(row.get("campaign_id", "")).strip(),
        program_id=str(row.get("program_id", "")).strip(),
        artifact_path=artifact_path,
        artifact_type=artifact_type,
        created_at=created_at,
        stat_regime=stamp.stat_regime,
        audit_status=stamp.audit_status,
        audit_reason=stamp.audit_reason,
        requires_repromotion=stamp.requires_repromotion,
        requires_manual_review=stamp.requires_manual_review,
        artifact_audit_version=stamp.artifact_audit_version,
        inference_confidence=stamp.inference_confidence,
        policy_version=str(row.get("policy_version", "")).strip(),
        bundle_version=str(row.get("bundle_version", "")).strip(),
        q_value=_safe_float(row.get("q_value")),
        q_value_scope=_safe_float(row.get("q_value_scope")),
        effective_q_value=_safe_float(row.get("effective_q_value")),
        num_tests_scope=_safe_int(row.get("num_tests_scope")),
        multiplicity_scope_mode=str(row.get("multiplicity_scope_mode", "")).strip() or None,
        search_scope_version=str(row.get("search_scope_version", "")).strip() or None,
        search_burden_estimated=_safe_bool(row.get("search_burden_estimated")),
    )


def _find_promotion_artifacts(data_root: Path) -> List[Path]:
    promotion_root = data_root / "reports" / "promotions"
    if not promotion_root.exists():
        return []
    artifacts: List[Path] = []
    for run_dir in sorted(promotion_root.iterdir()):
        if not run_dir.is_dir():
            continue
        for artifact_type, patterns in ARTIFACT_TYPES.items():
            for pattern in patterns:
                candidate = run_dir / pattern
                if candidate.exists():
                    artifacts.append(candidate)
    return artifacts


def scan_historical_artifacts(
    data_root: Optional[Path] = None,
    *,
    run_id: Optional[str] = None,
    since: Optional[str] = None,
) -> AuditInventoryResult:
    resolved_root = Path(data_root) if data_root is not None else get_data_root()
    artifacts = _find_promotion_artifacts(resolved_root)

    rows: List[ArtifactInventoryRow] = []
    scanned_paths: List[str] = []
    errors: List[str] = []

    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

    for artifact_path in artifacts:
        try:
            run_dir_name = artifact_path.parent.name
            if run_id and run_dir_name != run_id:
                continue
            created_at = _get_file_created_at(artifact_path)
            if since_dt:
                file_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if file_dt < since_dt:
                    continue
            artifact_type = _detect_artifact_type(artifact_path.name)
            if artifact_type is None:
                continue
            records = _load_artifact_file(artifact_path)
            for record in records:
                inventory_row = _build_inventory_row(
                    record,
                    artifact_path=str(artifact_path),
                    artifact_type=artifact_type,
                    created_at=created_at,
                )
                rows.append(inventory_row)
            scanned_paths.append(str(artifact_path))
        except Exception as exc:
            errors.append(f"{artifact_path}: {exc}")
            log.warning("Failed to scan artifact %s: %s", artifact_path, exc)

    run_id_counts: Dict[str, int] = {}
    stat_regime_counts: Dict[str, int] = {}
    audit_status_counts: Dict[str, int] = {}
    requires_repromotion_count = 0
    requires_manual_review_count = 0

    for row in rows:
        run_id_counts[row.run_id] = run_id_counts.get(row.run_id, 0) + 1
        stat_regime_counts[row.stat_regime] = stat_regime_counts.get(row.stat_regime, 0) + 1
        audit_status_counts[row.audit_status] = audit_status_counts.get(row.audit_status, 0) + 1
        if row.requires_repromotion:
            requires_repromotion_count += 1
        if row.requires_manual_review:
            requires_manual_review_count += 1

    return AuditInventoryResult(
        rows=rows,
        run_id_counts=run_id_counts,
        stat_regime_counts=stat_regime_counts,
        audit_status_counts=audit_status_counts,
        requires_repromotion_count=requires_repromotion_count,
        requires_manual_review_count=requires_manual_review_count,
        scanned_artifact_paths=scanned_paths,
        errors=errors,
    )


def write_artifact_audit_stamp_sidecar(
    artifact_path: Path,
    stamp: ArtifactAuditStamp,
) -> Path:
    sidecar_path = artifact_path.with_suffix(artifact_path.suffix + ".audit_stamp.json")
    payload = {
        "schema_version": "artifact_audit_stamp_v1",
        "stat_regime": stamp.stat_regime,
        "audit_status": stamp.audit_status,
        "artifact_audit_version": stamp.artifact_audit_version,
        "audit_reason": stamp.audit_reason,
        "requires_repromotion": stamp.requires_repromotion,
        "requires_manual_review": stamp.requires_manual_review,
        "inference_confidence": stamp.inference_confidence,
    }
    sidecar_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return sidecar_path


def write_audit_inventory(
    result: AuditInventoryResult,
    output_dir: Path,
) -> Dict[str, Path]:
    ensure_dir(output_dir)
    parquet_path = output_dir / "historical_artifact_audit.parquet"
    json_path = output_dir / "historical_artifact_audit.json"
    md_path = output_dir / "historical_artifact_audit.md"

    if result.rows:
        df = pd.DataFrame([row.to_dict() for row in result.rows])
        df.to_parquet(parquet_path, index=False)
    else:
        pd.DataFrame(columns=list(ArtifactInventoryRow.__dataclass_fields__.keys())).to_parquet(parquet_path, index=False)

    json_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# Historical Artifact Audit Inventory",
        "",
        f"- schema_version: `{AUDIT_INVENTORY_SCHEMA_VERSION}`",
        f"- total_rows: `{len(result.rows)}`",
        f"- scanned_artifact_count: `{len(result.scanned_artifact_paths)}`",
        f"- error_count: `{len(result.errors)}`",
        "",
        "## Summary by Statistical Regime",
        "",
    ]
    for regime, count in sorted(stat_regime_counts := result.stat_regime_counts.items()):
        md_lines.append(f"- {regime}: `{count}`")
    md_lines.extend(["", "## Summary by Audit Status", ""])
    for status, count in sorted(result.audit_status_counts.items()):
        md_lines.append(f"- {status}: `{count}`")
    md_lines.extend(["", "## Special Flags", ""])
    md_lines.append(f"- requires_repromotion: `{result.requires_repromotion_count}`")
    md_lines.append(f"- requires_manual_review: `{result.requires_manual_review_count}`")

    if result.errors:
        md_lines.extend(["", "## Errors", ""])
        for error in result.errors[:10]:
            md_lines.append(f"- {error}")
        if len(result.errors) > 10:
            md_lines.append(f"- ... and {len(result.errors) - 10} more errors")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "parquet_path": parquet_path,
        "json_path": json_path,
        "md_path": md_path,
    }


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def rewrite_audit_stamp_sidecars(
    result: AuditInventoryResult,
) -> Dict[str, Any]:
    artifact_stamps: Dict[str, List[ArtifactAuditStamp]] = {}
    for row in result.rows:
        path_key = row.artifact_path
        if path_key not in artifact_stamps:
            artifact_stamps[path_key] = []
        artifact_stamps[path_key].append(
            ArtifactAuditStamp(
                stat_regime=row.stat_regime,
                audit_status=row.audit_status,
                artifact_audit_version=row.artifact_audit_version,
                audit_reason=row.audit_reason,
                requires_repromotion=row.requires_repromotion,
                requires_manual_review=row.requires_manual_review,
                inference_confidence=row.inference_confidence,
            )
        )

    written_count = 0
    aggregated_stamps: Dict[str, ArtifactAuditStamp] = {}

    for artifact_path_str, stamps in artifact_stamps.items():
        has_manual_review = any(
            s.audit_status == AUDIT_STATUS_MANUAL_REVIEW_REQUIRED or s.requires_manual_review
            for s in stamps
        )
        has_pre_audit = any(s.stat_regime == STAT_REGIME_PRE_AUDIT for s in stamps)
        has_degraded = any(s.audit_status == AUDIT_STATUS_DEGRADED for s in stamps)

        if has_manual_review:
            final_status = AUDIT_STATUS_MANUAL_REVIEW_REQUIRED
            final_regime = STAT_REGIME_UNKNOWN
        elif has_pre_audit:
            final_status = AUDIT_STATUS_LEGACY
            final_regime = STAT_REGIME_PRE_AUDIT
        elif has_degraded:
            final_status = AUDIT_STATUS_DEGRADED
            final_regime = STAT_REGIME_POST_AUDIT
        else:
            final_status = AUDIT_STATUS_CURRENT
            final_regime = STAT_REGIME_POST_AUDIT

        final_stamp = ArtifactAuditStamp(
            stat_regime=final_regime,
            audit_status=final_status,
            artifact_audit_version=ARTIFACT_AUDIT_VERSION_PHASE1_V1,
            audit_reason=f"aggregated_from_{len(stamps)}_rows",
            requires_repromotion=has_pre_audit,
            requires_manual_review=has_manual_review,
            inference_confidence="high" if not has_manual_review else "low",
        )

        artifact_path = Path(artifact_path_str)
        write_artifact_audit_stamp_sidecar(artifact_path, final_stamp)
        aggregated_stamps[artifact_path_str] = final_stamp
        written_count += 1

    return {
        "sidecars_written": written_count,
        "artifacts_processed": len(artifact_stamps),
        "stamps": aggregated_stamps,
    }


__all__ = [
    "ArtifactInventoryRow",
    "AuditInventoryResult",
    "scan_historical_artifacts",
    "write_artifact_audit_stamp_sidecar",
    "write_audit_inventory",
    "rewrite_audit_stamp_sidecars",
    "AUDIT_INVENTORY_SCHEMA_VERSION",
]