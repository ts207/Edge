from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from project.artifacts import live_thesis_index_path, promoted_theses_path
from project.core.config import get_data_root
from project.events.governance import get_event_governance_metadata
from project.live.contracts import (
    PromotedThesis,
    ThesisEvidence,
    ThesisGovernance,
    ThesisLineage,
    ThesisRequirements,
    ThesisSource,
)
from project.live.thesis_specs import get_thesis_definition
from project.portfolio.thesis_overlap import overlap_group_id_for_thesis, write_thesis_overlap_artifacts
from project.research.artifact_hygiene import build_artifact_refs, infer_workspace_root, invalid_artifact_header
from project.research.seed_bootstrap import DOCS_GENERATED
from project.research.seed_empirical import _load_empirical_bundles

SEED_CARD_DIRNAME = "seed_thesis_cards"
DEFAULT_PACKAGE_RUN_ID = "seed_founding_batch_v1"
ELIGIBLE_DECISIONS = {"seed_promote", "paper_candidate"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{str(k): str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def _inventory_by_candidate(path: Path) -> dict[str, dict[str, str]]:
    rows = _load_csv(path)
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if candidate_id:
            out[candidate_id] = row
    return out


def _empirical_rows(path: Path) -> list[dict[str, str]]:
    return _load_csv(path)


def _bundle_map(data_root: Path) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for bundle in _load_empirical_bundles(data_root):
        out.setdefault(bundle.candidate_id, []).append(bundle)
    return out


def _split_tokens(raw: str) -> list[str]:
    return [token.strip() for token in str(raw or "").split("|") if token.strip()]


def _safe_float(raw: str, default: float | None = None) -> float | None:
    token = str(raw or "").strip()
    if not token:
        return default
    try:
        return float(token)
    except ValueError:
        return default


def _safe_int(raw: str, default: int = 0) -> int:
    token = str(raw or "").strip()
    if not token:
        return default
    try:
        return int(float(token))
    except ValueError:
        return default


def _timeframe_for_candidate(_bundles: Iterable[Any]) -> str:
    return "5m"


def _extract_symbols(bundles: Iterable[Any]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for bundle in bundles:
        raw_payload = getattr(bundle, "raw", {}) or {}
        metadata = raw_payload.get("metadata", {}) if isinstance(raw_payload.get("metadata", {}), Mapping) else {}
        for symbol in metadata.get("input_symbols", []) or []:
            token = str(symbol).strip().upper()
            if token and token not in seen:
                symbols.append(token)
                seen.add(token)
        sample = raw_payload.get("sample_definition", {}) if isinstance(raw_payload.get("sample_definition", {}), Mapping) else {}
        sample_symbol = str(sample.get("symbol", raw_payload.get("symbol", ""))).strip().upper()
        if sample_symbol and sample_symbol not in seen:
            symbols.append(sample_symbol)
            seen.add(sample_symbol)
    return symbols


def _extract_notes(bundles: Iterable[Any]) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for bundle in bundles:
        raw_payload = getattr(bundle, "raw", {}) or {}
        metadata = raw_payload.get("metadata", {}) if isinstance(raw_payload.get("metadata", {}), Mapping) else {}
        token = str(metadata.get("notes", "")).strip()
        if token and token not in seen:
            notes.append(token)
            seen.add(token)
    return notes


def _extract_confounders(bundles: Iterable[Any]) -> list[str]:
    confs: list[str] = []
    seen: set[str] = set()
    for bundle in bundles:
        raw_payload = getattr(bundle, "raw", {}) or {}
        falsification = raw_payload.get("falsification_results", {}) if isinstance(raw_payload.get("falsification_results", {}), Mapping) else {}
        for key, value in falsification.items():
            if key == "negative_control_pass_rate":
                continue
            token = str(key).strip()
            if not token:
                continue
            passed = True
            if isinstance(value, Mapping):
                passed = bool(value.get("passed", True))
            label = token if passed else f"{token} (failed)"
            if label not in seen:
                confs.append(label)
                seen.add(label)
    return confs


def _promotion_class(decision: str) -> str:
    if decision == "paper_candidate":
        return "paper_promoted"
    return "seed_promoted"


def _deployment_state(decision: str) -> str:
    if decision == "paper_candidate":
        return "paper_only"
    return "monitor_only"


def _iso_day(ts: datetime) -> str:
    return ts.date().isoformat()


def _review_cadence_days(*, promotion_class: str, source_type: str, bundles: list[Any]) -> int:
    direct_pair = False
    derived_pair = False
    for bundle in bundles:
        raw_payload = getattr(bundle, "raw", {}) or {}
        metadata = raw_payload.get("metadata", {}) if isinstance(raw_payload.get("metadata", {}), Mapping) else {}
        direct_pair = direct_pair or bool(metadata.get("direct_pair_event_evidence", False))
        derived_pair = derived_pair or bool(metadata.get("derived_from_component_evidence", False))
    if source_type == "event_plus_confirm":
        if derived_pair:
            return 14
        if direct_pair:
            return 21
        return 14
    if promotion_class == "seed_promoted":
        return 30
    return 90


def _maintenance_fields(*, promotion_class: str, source_type: str, bundles: list[Any]) -> dict[str, str]:
    freshness_dt = datetime.now(timezone.utc)
    cadence_days = _review_cadence_days(promotion_class=promotion_class, source_type=source_type, bundles=bundles)
    review_due = freshness_dt + timedelta(days=cadence_days)
    return {
        "evidence_freshness_date": _iso_day(freshness_dt),
        "review_due_date": _iso_day(review_due),
        "staleness_class": "fresh",
    }


def _event_side(row: Mapping[str, str]) -> str:
    text = str(row.get("expected_direction_or_path", "")).lower()
    if "repair" in text and "continued" in text:
        return "conditional"
    return "both"


def _build_thesis(
    empirical_row: Mapping[str, str],
    inventory_row: Mapping[str, str],
    bundles: list[Any],
    *,
    package_run_id: str,
) -> PromotedThesis:
    candidate_id = str(empirical_row.get("candidate_id", "")).strip()
    thesis_def = get_thesis_definition(candidate_id)
    decision = str(empirical_row.get("empirical_decision", "")).strip().lower()
    event_contract_ids = _split_tokens(inventory_row.get("event_contract_ids", ""))
    episode_contract_ids = _split_tokens(inventory_row.get("episode_contract_ids", ""))
    if thesis_def is not None:
        if not event_contract_ids:
            event_contract_ids = list(thesis_def.source_event_contract_ids)
        if not episode_contract_ids:
            episode_contract_ids = list(thesis_def.source_episode_contract_ids)
    source_type = str(inventory_row.get("source_type", empirical_row.get("source_type", ""))).strip().lower()
    primary_event = event_contract_ids[0] if event_contract_ids else str(empirical_row.get("source_contract_ids", "")).split("|")[0].strip()
    governance_meta = get_event_governance_metadata(primary_event) if primary_event else {}
    symbols = _extract_symbols(bundles)
    notes = _extract_notes(bundles)
    confounders = _extract_confounders(bundles)
    realized_oos = str(empirical_row.get("realized_oos_supported", "0")).strip() in {"1", "true", "True"}
    sample_total = _safe_int(empirical_row.get("sample_size_total", "0"), 0)
    validation_total = _safe_int(empirical_row.get("validation_samples_total", "0"), 0)
    test_total = _safe_int(empirical_row.get("test_samples_total", "0"), 0)
    estimate_bps = _safe_float(empirical_row.get("median_estimate_bps", ""), None)
    net_expectancy_bps = _safe_float(empirical_row.get("median_net_expectancy_bps", ""), None)
    q_value = _safe_float(empirical_row.get("best_q_value", ""), None)
    stability_score = _safe_float(empirical_row.get("best_stability_score", ""), None)
    rank_score = float(_safe_int(empirical_row.get("total_score", "0"), 0))

    trigger_events = event_contract_ids if source_type not in {"episode", "event_plus_confirm"} else []
    if source_type == "event_plus_confirm":
        trigger_events = event_contract_ids[:1]
    if thesis_def is not None:
        trigger_events = list(thesis_def.trigger_events)
    requirements = ThesisRequirements(
        trigger_events=trigger_events,
        confirmation_events=list(thesis_def.confirmation_events) if thesis_def is not None else (event_contract_ids[1:] if source_type == "event_plus_confirm" else []),
        required_episodes=list(thesis_def.required_episodes) if thesis_def is not None else episode_contract_ids,
        disallowed_regimes=list(thesis_def.disallowed_regimes) if thesis_def is not None else [],
        deployment_gate=str(governance_meta.get("promotion_block_reason", "")).strip(),
        sequence_mode=("episode" if source_type == "episode" else ("event_plus_confirm" if source_type == "event_plus_confirm" else "standalone_event")),
        minimum_episode_confidence=0.0,
    )
    evidence_gaps = _split_tokens(empirical_row.get("evidence_gap_summary", ""))
    promotion_class = _promotion_class(decision)
    thesis = PromotedThesis(
        thesis_id=candidate_id,
        promotion_class=promotion_class,
        deployment_state=_deployment_state(decision),
        evidence_gaps=evidence_gaps,
        status="active",
        **_maintenance_fields(promotion_class=promotion_class, source_type=source_type, bundles=bundles),
        symbol_scope={
            "mode": (
                str(thesis_def.symbol_scope.get("mode", "")).strip()
                if thesis_def is not None and thesis_def.symbol_scope
                else ("symbol_set" if len(symbols) > 1 else "single_symbol")
            ),
            "symbols": symbols,
            "candidate_symbol": symbols[0] if len(symbols) == 1 else "",
        },
        timeframe=str(thesis_def.timeframe).strip() if thesis_def is not None and str(thesis_def.timeframe).strip() else _timeframe_for_candidate(bundles),
        primary_event_id=(
            str(thesis_def.event_family).strip().upper()
            if thesis_def is not None and str(thesis_def.event_family).strip()
            else (primary_event or candidate_id).strip().upper()
        ),
        event_family=(str(thesis_def.event_family).strip().upper() if thesis_def is not None and str(thesis_def.event_family).strip() else (primary_event or candidate_id).strip().upper()),
        canonical_regime=(
            str((thesis_def.supportive_context or {}).get("canonical_regime", "")).strip().upper()
            if thesis_def is not None
            else str(governance_meta.get("canonical_regime", "")).strip().upper()
        ),
        event_side=(str(thesis_def.event_side).strip().lower() if thesis_def is not None and str(thesis_def.event_side).strip() else _event_side(inventory_row)),
        required_context={
            **(dict(thesis_def.required_context) if thesis_def is not None else {}),
            "evaluation_symbols": symbols,
            "horizon_guess": str(inventory_row.get("horizon_guess", "")).strip(),
            "source_type": source_type,
        },
        supportive_context={
            **(dict(thesis_def.supportive_context) if thesis_def is not None else {}),
            "canonical_regime": (
                str((thesis_def.supportive_context or {}).get("canonical_regime", "")).strip()
                if thesis_def is not None
                else ""
            ),
            "bridge_certified": False,
            "has_realized_oos_path": realized_oos,
            "regime_assumptions": str(inventory_row.get("regime_assumptions", "")).strip(),
        },
        expected_response={
            **(dict(thesis_def.expected_response) if thesis_def is not None else {}),
            "summary": str(inventory_row.get("expected_direction_or_path", "")).strip(),
            "hypothesis_statement": str(inventory_row.get("hypothesis_statement", "")).strip(),
            "horizon_guess": str(inventory_row.get("horizon_guess", "")).strip(),
            "median_estimate_bps": estimate_bps,
            "median_net_expectancy_bps": net_expectancy_bps,
            "sample_size_total": sample_total,
        },
        invalidation={
            **(dict(thesis_def.invalidation) if thesis_def is not None else {}),
            "rule_text": str(inventory_row.get("invalidation_rule", "")).strip(),
        },
        risk_notes=[
            "packaged_from_empirical_seed_pass",
            "manual_invalidation_rule_only",
            *([f"note:{note}" for note in notes]),
        ],
        evidence=ThesisEvidence(
            sample_size=sample_total,
            validation_samples=validation_total,
            test_samples=test_total,
            estimate_bps=estimate_bps,
            net_expectancy_bps=net_expectancy_bps,
            q_value=q_value,
            stability_score=stability_score,
            cost_survival_ratio=None,
            tob_coverage=None,
            rank_score=rank_score,
            promotion_track="seed_bootstrap_empirical",
            policy_version="founding_thesis_eval_policy_v1",
            bundle_version="founding_empirical_v1",
        ),
        lineage=ThesisLineage(
            run_id=package_run_id,
            candidate_id=candidate_id,
            hypothesis_id=candidate_id,
            plan_row_id="",
            blueprint_id="",
            proposal_id="",
        ),
        governance=ThesisGovernance(
            tier=str(empirical_row.get("governance_tier", governance_meta.get("tier", ""))).strip(),
            operational_role=(
                str(empirical_row.get("operational_role", "")).strip()
                or (
                    str((thesis_def.governance or {}).get("operational_role", "")).strip()
                    if thesis_def is not None
                    else ""
                )
                or str(governance_meta.get("operational_role", "")).strip()
            ),
            deployment_disposition=str(empirical_row.get("deployment_disposition", governance_meta.get("deployment_disposition", ""))).strip(),
            evidence_mode=(
                str((thesis_def.governance or {}).get("evidence_mode", "")).strip()
                if thesis_def is not None and str((thesis_def.governance or {}).get("evidence_mode", "")).strip()
                else str(governance_meta.get("evidence_mode", "")).strip()
            ),
            overlap_group_id="",
            trade_trigger_eligible=(
                bool((thesis_def.governance or {}).get("trade_trigger_eligible", False))
                if thesis_def is not None
                else bool(governance_meta.get("trade_trigger_eligible", False))
            ),
            requires_stronger_evidence=(
                bool((thesis_def.governance or {}).get("requires_stronger_evidence", False))
                if thesis_def is not None
                else bool(governance_meta.get("requires_stronger_evidence", False))
            ),
        ),
        requirements=requirements,
        source=ThesisSource(
            source_program_id="seed_bootstrap",
            source_campaign_id=str(inventory_row.get("source_campaign_id", "")).strip(),
            source_run_mode="bootstrap_seed_packaging",
            objective_name="founding_thesis_package",
            event_contract_ids=list(thesis_def.source_event_contract_ids) if thesis_def is not None else event_contract_ids,
            episode_contract_ids=list(thesis_def.source_episode_contract_ids) if thesis_def is not None else episode_contract_ids,
        ),
    )
    overlap_group = overlap_group_id_for_thesis(thesis)
    return thesis.model_copy(update={
        "governance": thesis.governance.model_copy(update={"overlap_group_id": overlap_group})
    })


def _write_thesis_payload(run_id: str, theses: list[PromotedThesis], data_root: Path) -> Path:
    output_path = promoted_theses_path(run_id, data_root)
    _ensure_dir(output_path.parent)
    payload = {
        "schema_version": "promoted_theses_v1",
        "run_id": run_id,
        "generated_at_utc": _utc_now(),
        "thesis_count": len(theses),
        "active_thesis_count": sum(1 for thesis in theses if thesis.status == "active"),
        "pending_thesis_count": sum(1 for thesis in theses if thesis.status == "pending_blueprint"),
        "theses": [thesis.model_dump() for thesis in theses],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _update_index(run_id: str, output_path: Path, theses: list[PromotedThesis], data_root: Path) -> Path:
    index_path = live_thesis_index_path(data_root)
    _ensure_dir(index_path.parent)
    payload: dict[str, Any]
    if index_path.exists():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
    else:
        payload = {}
    runs = payload.get("runs", {}) if isinstance(payload.get("runs", {}), dict) else {}
    runs[run_id] = {
        "output_path": str(output_path),
        "thesis_count": len(theses),
        "active_thesis_count": sum(1 for thesis in theses if thesis.status == "active"),
        "pending_thesis_count": sum(1 for thesis in theses if thesis.status == "pending_blueprint"),
        "updated_at_utc": _utc_now(),
    }
    index = {
        "schema_version": "promoted_thesis_index_v1",
        "latest_run_id": run_id,
        "runs": runs,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return index_path


def _render_card(thesis: PromotedThesis, inventory_row: Mapping[str, str], bundles: list[Any]) -> str:
    confounders = _extract_confounders(bundles)
    notes = _extract_notes(bundles)
    symbols = ", ".join(thesis.symbol_scope.get("symbols", []))
    evidence_gaps = thesis.evidence_gaps or ["none"]
    lines = [
        f"# {thesis.thesis_id}",
        "",
        f"- Promotion class: `{thesis.promotion_class}`",
        f"- Deployment state: `{thesis.deployment_state}`",
        f"- Primary event id: `{thesis.primary_event_id}`",
        f"- Compatibility event family: `{thesis.event_family}`",
        f"- Tier / role: `{thesis.governance.tier}` / `{thesis.governance.operational_role}`",
        f"- Symbols: {symbols or '_none_'}",
        f"- Timeframe: `{thesis.timeframe}`",
        f"- Horizon: {thesis.expected_response.get('horizon_guess', '')}",
        f"- Evidence freshness date: `{thesis.evidence_freshness_date}`",
        f"- Review due date: `{thesis.review_due_date}`",
        f"- Staleness class: `{thesis.staleness_class}`",
        "",
        "## What it is",
        "",
        str(inventory_row.get("hypothesis_statement", "")).strip() or "_No hypothesis statement available._",
        "",
        "## Why it should work",
        "",
        str(inventory_row.get("expected_direction_or_path", "")).strip() or "_No expected path summary available._",
        "",
        "## Trigger",
        "",
        ", ".join(thesis.source.event_contract_ids) if thesis.source.event_contract_ids else thesis.primary_event_id,
        "",
        "## Invalidation",
        "",
        str(inventory_row.get("invalidation_rule", "")).strip() or "_No invalidation rule recorded._",
        "",
        "## Evidence summary",
        "",
        f"- sample_size_total: `{thesis.evidence.sample_size}`",
        f"- validation_samples: `{thesis.evidence.validation_samples}`",
        f"- test_samples: `{thesis.evidence.test_samples}`",
        f"- median_estimate_bps: `{thesis.evidence.estimate_bps}`",
        f"- median_net_expectancy_bps: `{thesis.evidence.net_expectancy_bps}`",
        f"- best_q_value: `{thesis.evidence.q_value}`",
        f"- best_stability_score: `{thesis.evidence.stability_score}`",
        "",
        "## Confounders checked",
        "",
    ]
    if confounders:
        lines.extend(f"- {item}" for item in confounders)
    else:
        lines.append("- none recorded")
    lines.extend([
        "",
        "## Evidence gaps",
        "",
    ])
    lines.extend(f"- {item}" for item in evidence_gaps)
    lines.append("")
    if notes:
        lines.extend(["## Notes", ""])
        lines.extend(f"- {item}" for item in notes)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def package_seed_promoted_theses(
    *,
    docs_dir: str | Path | None = None,
    data_root: str | Path | None = None,
    package_run_id: str = DEFAULT_PACKAGE_RUN_ID,
) -> dict[str, Path]:
    docs_root = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)
    data_root_path = Path(data_root) if data_root is not None else get_data_root()
    empirical_path = docs_root / "thesis_empirical_scorecards.csv"
    inventory_path = docs_root / "promotion_seed_inventory.csv"
    empirical_rows = _empirical_rows(empirical_path)
    inventory_map = _inventory_by_candidate(inventory_path)
    bundle_map = _bundle_map(data_root_path)

    selected = [
        row for row in empirical_rows
        if str(row.get("empirical_decision", "")).strip().lower() in ELIGIBLE_DECISIONS
    ]
    selected.sort(key=lambda row: (-_safe_int(row.get("total_score", "0"), 0), str(row.get("candidate_id", ""))))

    theses: list[PromotedThesis] = []
    card_dir = _ensure_dir(docs_root / SEED_CARD_DIRNAME)
    packaged_ids: list[str] = []
    for row in selected:
        candidate_id = str(row.get("candidate_id", "")).strip()
        inventory_row = inventory_map.get(candidate_id)
        bundles = bundle_map.get(candidate_id, [])
        if not candidate_id or inventory_row is None or not bundles:
            continue
        thesis = _build_thesis(row, inventory_row, bundles, package_run_id=package_run_id)
        theses.append(thesis)
        packaged_ids.append(candidate_id)
        (card_dir / f"{candidate_id}.md").write_text(_render_card(thesis, inventory_row, bundles), encoding="utf-8")

    theses.sort(key=lambda thesis: thesis.thesis_id)
    output_path = _write_thesis_payload(package_run_id, theses, data_root_path)
    index_path = _update_index(package_run_id, output_path, theses, data_root_path)
    overlap_payload = write_thesis_overlap_artifacts(theses, docs_root)

    summary_json = docs_root / "seed_thesis_packaging_summary.json"
    summary_md = docs_root / "seed_thesis_packaging_summary.md"
    catalog_md = docs_root / "seed_thesis_catalog.md"
    workspace_root = infer_workspace_root(docs_root, data_root_path)
    artifact_refs, invalid_refs = build_artifact_refs(
        {
            "thesis_store": output_path,
            "thesis_index": index_path,
            "card_dir": card_dir,
            "overlap_json": docs_root / "thesis_overlap_graph.json",
            "overlap_md": docs_root / "thesis_overlap_graph.md",
        },
        workspace_root=workspace_root,
    )
    summary_payload = {
        "package_run_id": package_run_id,
        "generated_at_utc": _utc_now(),
        "packaged_count": len(theses),
        "thesis_ids": packaged_ids,
        "workspace_root": workspace_root.as_posix(),
        "artifact_refs": artifact_refs,
        "overlap_group_count": int(overlap_payload.get("overlap_group_count", 0) or 0),
        "overlap_edge_count": len(overlap_payload.get("edges", [])) if isinstance(overlap_payload.get("edges", []), list) else 0,
        "freshness_dates": {thesis.thesis_id: thesis.evidence_freshness_date for thesis in theses},
        "review_due_dates": {thesis.thesis_id: thesis.review_due_date for thesis in theses},
        "invalid_artifact_refs": invalid_refs,
    }
    summary_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_lines = invalid_artifact_header(invalid_refs) + [
        "# Seed thesis packaging summary",
        "",
        f"- package_run_id: `{package_run_id}`",
        f"- packaged_count: `{len(theses)}`",
        f"- overlap_group_count: `{summary_payload['overlap_group_count']}`",
        f"- overlap_edge_count: `{summary_payload['overlap_edge_count']}`",
        f"- thesis_store: `{artifact_refs['thesis_store']['path']}`",
        f"- thesis_index: `{artifact_refs['thesis_index']['path']}`",
        f"- overlap_json: `{artifact_refs['overlap_json']['path']}`",
        f"- overlap_md: `{artifact_refs['overlap_md']['path']}`",
        "",
        "## Packaged theses",
        "",
    ]
    if theses:
        for thesis in theses:
            summary_lines.append(
                f"- `{thesis.thesis_id}` — `{thesis.promotion_class}` / `{thesis.deployment_state}` / group `{thesis.governance.overlap_group_id}`"
            )
    else:
        summary_lines.append("_No theses were packaged._")
    summary_md.write_text("\n".join(summary_lines).rstrip() + "\n", encoding="utf-8")

    catalog_lines = [
        "# Seed thesis catalog",
        "",
        "| Thesis | Promotion class | Deployment state | Primary event id | Compat event family | Overlap group | Card |",
        "|---|---|---|---|---|---|---|",
    ]
    for thesis in theses:
        card_rel = f"{SEED_CARD_DIRNAME}/{thesis.thesis_id}.md"
        catalog_lines.append(
            f"| `{thesis.thesis_id}` | `{thesis.promotion_class}` | `{thesis.deployment_state}` | `{thesis.primary_event_id}` | `{thesis.event_family}` | `{thesis.governance.overlap_group_id}` | `{card_rel}` |"
        )
    if not theses:
        catalog_lines.append("| _none_ |  |  |  |  |  |  |")
    catalog_md.write_text("\n".join(catalog_lines).rstrip() + "\n", encoding="utf-8")

    return {
        "thesis_store": output_path,
        "thesis_index": index_path,
        "summary_json": summary_json,
        "summary_md": summary_md,
        "catalog_md": catalog_md,
        "card_dir": card_dir,
        "overlap_json": docs_root / "thesis_overlap_graph.json",
        "overlap_md": docs_root / "thesis_overlap_graph.md",
    }


__all__ = ["package_seed_promoted_theses", "DEFAULT_PACKAGE_RUN_ID"]
