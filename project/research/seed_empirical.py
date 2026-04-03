from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from project.core.coercion import safe_float, safe_int
from project.core.config import get_data_root
from project.events.governance import get_event_governance_metadata
from project.episodes import load_episode_registry
from project.research.seed_bootstrap import DOCS_GENERATED, SEED_POLICY_PATH, build_promotion_seed_inventory, load_seed_promotion_policy
from project.research.seed_testing import (
    _deployment_suitability,
    _invalidation_clarity,
    _next_action_for_decision,
    _ontology_fidelity,
    _regime_clarity,
    _testing_thresholds,
)

EMPIRICAL_SCORECARD_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "primary_event_id",
    "compat_event_family",
    "source_type",
    "source_contract_ids",
    "governance_tier",
    "operational_role",
    "deployment_disposition",
    "matched_bundle_count",
    "matched_required_coverage",
    "matched_run_ids",
    "matched_bundle_candidate_ids",
    "empirical_evidence_source",
    "sample_size_total",
    "validation_samples_total",
    "test_samples_total",
    "median_estimate_bps",
    "median_net_expectancy_bps",
    "best_q_value",
    "best_stability_score",
    "negative_control_rate_min",
    "realized_oos_supported",
    "ontology_fidelity",
    "implementation_fidelity",
    "evidence_strength",
    "regime_clarity",
    "invalidation_clarity",
    "confounder_handling",
    "holdout_quality",
    "deployment_suitability",
    "total_score",
    "empirical_decision",
    "lifecycle_class",
    "evidence_gap_summary",
    "recommended_next_action",
)


@dataclass(frozen=True)
class EmpiricalBundle:
    run_id: str
    candidate_id: str
    primary_event_id: str
    event_type: str
    event_family: str
    sample_size: int
    validation_samples: int
    test_samples: int
    estimate_bps: float | None
    net_expectancy_bps: float | None
    q_value: float | None
    stability_score: float | None
    negative_control_rate: float | None
    realized_oos_supported: bool
    confounder_count: int
    derived_from_component_evidence: bool
    raw: dict[str, Any]


@dataclass(frozen=True)
class CandidateEvidence:
    bundles: tuple[EmpiricalBundle, ...]
    required_contracts: tuple[str, ...]

    @property
    def coverage(self) -> float:
        if not self.required_contracts:
            return 1.0 if self.bundles else 0.0
        matched = {
            bundle.event_type.upper()
            for bundle in self.bundles
            if bundle.event_type.strip().upper() in set(self.required_contracts)
        }
        return len(matched) / max(1, len(set(self.required_contracts)))


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_inventory(path: str | Path | None = None) -> list[dict[str, str]]:
    inventory_path = Path(path) if path is not None else DOCS_GENERATED / "promotion_seed_inventory.csv"
    if not inventory_path.exists():
        build_promotion_seed_inventory(docs_dir=inventory_path.parent)
    if not inventory_path.exists():
        return []
    with inventory_path.open("r", encoding="utf-8", newline="") as handle:
        return [{str(k): str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _promotion_roots(data_root: Path) -> list[Path]:
    base = data_root / "reports" / "promotions"
    if not base.exists():
        return []
    return [path for path in sorted(base.iterdir()) if path.is_dir()]


def _extract_bundle(run_id: str, payload: Mapping[str, Any]) -> EmpiricalBundle | None:
    event_type = str(payload.get("event_type", "")).strip().upper()
    candidate_id = str(payload.get("candidate_id", "")).strip()
    if not event_type or not candidate_id:
        return None
    sample = payload.get("sample_definition", {}) if isinstance(payload.get("sample_definition"), Mapping) else {}
    effect = payload.get("effect_estimates", {}) if isinstance(payload.get("effect_estimates"), Mapping) else {}
    cost = payload.get("cost_robustness", {}) if isinstance(payload.get("cost_robustness"), Mapping) else {}
    uncertainty = payload.get("uncertainty_estimates", {}) if isinstance(payload.get("uncertainty_estimates"), Mapping) else {}
    stability = payload.get("stability_tests", {}) if isinstance(payload.get("stability_tests"), Mapping) else {}
    falsification = payload.get("falsification_results", {}) if isinstance(payload.get("falsification_results"), Mapping) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), Mapping) else {}

    confounder_count = 0
    for value in falsification.values():
        if isinstance(value, Mapping):
            confounder_count += 1
    if confounder_count == 0:
        controls = payload.get("negative_controls")
        if isinstance(controls, Sequence) and not isinstance(controls, (str, bytes)):
            confounder_count = len([item for item in controls if item])

    negative_control_rate = safe_float(
        falsification.get("negative_control_pass_rate", falsification.get("control_rate", float("nan"))),
        float("nan"),
    )
    if negative_control_rate != negative_control_rate:
        negative_control_rate = None

    estimate_bps = safe_float(effect.get("estimate_bps", float("nan")), float("nan"))
    if estimate_bps != estimate_bps:
        estimate_bps = None
    net_expectancy_bps = safe_float(cost.get("net_expectancy_bps", float("nan")), float("nan"))
    if net_expectancy_bps != net_expectancy_bps:
        net_expectancy_bps = None
    q_value = safe_float(uncertainty.get("q_value", float("nan")), float("nan"))
    if q_value != q_value:
        q_value = None
    stability_score = safe_float(stability.get("stability_score", float("nan")), float("nan"))
    if stability_score != stability_score:
        stability_score = None

    return EmpiricalBundle(
        run_id=run_id,
        candidate_id=candidate_id,
        primary_event_id=str(payload.get("primary_event_id", event_type)).strip().upper(),
        event_type=event_type,
        event_family=str(payload.get("event_family", event_type)).strip().upper(),
        sample_size=int(safe_int(sample.get("n_events", 0), 0)),
        validation_samples=int(safe_int(sample.get("validation_samples", 0), 0)),
        test_samples=int(safe_int(sample.get("test_samples", 0), 0)),
        estimate_bps=estimate_bps,
        net_expectancy_bps=net_expectancy_bps,
        q_value=q_value,
        stability_score=stability_score,
        negative_control_rate=negative_control_rate,
        realized_oos_supported=bool(metadata.get("has_realized_oos_path", False)) or int(safe_int(sample.get("test_samples", 0), 0)) > 0,
        confounder_count=confounder_count,
        derived_from_component_evidence=bool(metadata.get("derived_from_component_evidence", False)),
        raw=dict(payload),
    )


def _load_empirical_bundles(data_root: Path | None = None) -> list[EmpiricalBundle]:
    resolved_root = Path(data_root) if data_root is not None else get_data_root()
    bundles: list[EmpiricalBundle] = []
    for run_dir in _promotion_roots(resolved_root):
        run_id = run_dir.name
        for payload in _jsonl_records(run_dir / "evidence_bundles.jsonl"):
            bundle = _extract_bundle(run_id, payload)
            if bundle is not None:
                bundles.append(bundle)
    return bundles


def _required_contracts(row: Mapping[str, str]) -> tuple[str, ...]:
    if str(row.get("source_type", "")).strip() == "episode":
        episode_ids = [token.strip() for token in str(row.get("episode_contract_ids", "")).split("|") if token.strip()]
        registry = load_episode_registry()
        required: list[str] = []
        for episode_id in episode_ids:
            episode = registry.get(episode_id)
            if episode is not None:
                required.extend(str(token).strip().upper() for token in episode.required_events if str(token).strip())
        if required:
            return tuple(sorted(dict.fromkeys(required)))
    return tuple(sorted(dict.fromkeys(token.strip().upper() for token in str(row.get("event_contract_ids", "")).split("|") if token.strip())))


def _match_bundles(row: Mapping[str, str], bundles: Sequence[EmpiricalBundle]) -> CandidateEvidence:
    required = _required_contracts(row)
    source_type = str(row.get("source_type", "")).strip().lower()
    candidate_id = str(row.get("candidate_id", "")).strip()
    matched: list[EmpiricalBundle] = []
    required_set = set(required)
    if source_type == "event":
        for bundle in bundles:
            if bundle.event_type.upper() in required_set:
                matched.append(bundle)
    else:
        explicit_match = False
        for bundle in bundles:
            explicit_ids = bundle.raw.get("thesis_contract_ids")
            if isinstance(explicit_ids, Sequence) and not isinstance(explicit_ids, (str, bytes)):
                explicit_set = {str(token).strip() for token in explicit_ids if str(token).strip()}
            else:
                explicit_set = set()
            explicit_single = str(bundle.raw.get("thesis_contract_id", "")).strip()
            if bundle.candidate_id == candidate_id or explicit_single == candidate_id or candidate_id in explicit_set:
                matched.append(bundle)
                explicit_match = True
        if explicit_match:
            required = tuple()
    return CandidateEvidence(bundles=tuple(matched), required_contracts=required)


def _implementation_fidelity(row: Mapping[str, str], evidence: CandidateEvidence) -> int:
    status = str(row.get("detector_fidelity_status", "")).strip().lower()
    if str(row.get("promotion_status", "")).strip().lower() == "needs_repair":
        return 1
    if evidence.bundles and status:
        if any(bundle.derived_from_component_evidence for bundle in evidence.bundles):
            return 4
        return 5
    if status:
        return 4
    return 0


def _evidence_strength(evidence: CandidateEvidence) -> int:
    if not evidence.bundles:
        return 0
    q_values = [bundle.q_value for bundle in evidence.bundles if bundle.q_value is not None]
    net_values = [bundle.net_expectancy_bps for bundle in evidence.bundles if bundle.net_expectancy_bps is not None]
    stability = [bundle.stability_score for bundle in evidence.bundles if bundle.stability_score is not None]
    total_events = sum(bundle.sample_size for bundle in evidence.bundles)
    coverage = evidence.coverage
    best_q = min(q_values) if q_values else None
    best_stability = max(stability) if stability else None
    positive_net = any(value > 0 for value in net_values)
    score = 2
    if coverage >= 1.0 and total_events >= 100 and positive_net and best_q is not None and best_q <= 0.10 and best_stability is not None and best_stability >= 0.05:
        score = 5
    elif coverage >= 0.5 and total_events >= 60 and positive_net:
        score = 4
    elif total_events >= 30:
        score = 3
    if any(bundle.derived_from_component_evidence for bundle in evidence.bundles):
        score = min(score, 4)
    return score


def _confounder_handling(evidence: CandidateEvidence) -> int:
    if not evidence.bundles:
        return 0
    best = max((bundle.confounder_count for bundle in evidence.bundles), default=0)
    if best >= 3:
        return 5
    if best == 2:
        return 4
    if best == 1:
        return 3
    return 1


def _holdout_quality(evidence: CandidateEvidence) -> int:
    if not evidence.bundles:
        return 0
    if any(bundle.realized_oos_supported and bundle.test_samples >= 20 for bundle in evidence.bundles):
        score = 5
    elif any(bundle.realized_oos_supported for bundle in evidence.bundles):
        score = 4
    elif sum(bundle.validation_samples + bundle.test_samples for bundle in evidence.bundles) > 0:
        score = 2
    else:
        score = 1
    if any(bundle.derived_from_component_evidence for bundle in evidence.bundles):
        score = min(score, 4)
    return score


def _evidence_gaps(evidence: CandidateEvidence, scores: Mapping[str, int]) -> list[str]:
    gaps: list[str] = []
    if not evidence.bundles:
        gaps.append("empirical_evidence_bundle_missing")
    if any(bundle.derived_from_component_evidence for bundle in evidence.bundles):
        gaps.append("direct_pair_event_study_missing")
    if evidence.coverage < 1.0 and len(evidence.required_contracts) > 1:
        gaps.append("required_contract_coverage_incomplete")
    if scores.get("holdout_quality", 0) < 2:
        gaps.append("holdout_check_missing")
    if scores.get("confounder_handling", 0) < 2:
        gaps.append("confounder_sanity_check_missing")
    if scores.get("invalidation_clarity", 0) < 3:
        gaps.append("invalidation_rule_needs_refinement")
    if scores.get("deployment_suitability", 0) <= 1:
        gaps.append("governance_role_or_disposition_blocked")
    return gaps


def _decision_for_row(row: Mapping[str, str], evidence: CandidateEvidence, scores: Mapping[str, int], policy: Mapping[str, Any]) -> str:
    thresholds = _testing_thresholds(policy)
    if str(row.get("promotion_status", "")).strip().lower() == "needs_repair" or scores["deployment_suitability"] <= 1:
        return "needs_repair"
    if not evidence.bundles:
        return "needs_more_evidence"
    evidence_ok = scores["evidence_strength"] >= thresholds["minimum_evidence_strength_for_seed"]
    holdout_ok = scores["holdout_quality"] >= thresholds["minimum_holdout_quality_for_seed"]
    conf_ok = scores["confounder_handling"] >= thresholds["minimum_confounder_handling_for_seed"]
    invalidation_ok = scores["invalidation_clarity"] >= 3
    coverage_ok = evidence.coverage >= 1.0 or len(evidence.required_contracts) <= 1
    total = int(scores["total_score"])
    if evidence_ok and holdout_ok and conf_ok and invalidation_ok and coverage_ok:
        derived_bridge = any(bundle.derived_from_component_evidence for bundle in evidence.bundles)
        if total >= thresholds["paper_candidate_min_total"] and not derived_bridge:
            return "paper_candidate"
        if total >= thresholds["seed_promote_min_total"]:
            return "seed_promote"
    return "needs_more_evidence"


def _lifecycle_class(decision: str) -> str:
    if decision in {"seed_promote", "paper_candidate"}:
        return "tested_thesis"
    return "candidate_thesis"


def _median_or_none(values: Iterable[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return float(median(numeric))


def run_empirical_seed_pass(
    *,
    docs_dir: str | Path | None = None,
    inventory_path: str | Path | None = None,
    policy_path: str | Path | None = None,
    data_root: str | Path | None = None,
) -> dict[str, Path]:
    out_dir = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)
    rows = _load_inventory(inventory_path)
    bundles = _load_empirical_bundles(Path(data_root) if data_root is not None else None)
    policy = load_seed_promotion_policy(policy_path or SEED_POLICY_PATH)

    empirical_rows: list[dict[str, Any]] = []
    for row in rows:
        evidence = _match_bundles(row, bundles)
        matched_run_ids = sorted({bundle.run_id for bundle in evidence.bundles})
        matched_candidate_ids = sorted({bundle.candidate_id for bundle in evidence.bundles})
        sample_size_total = sum(bundle.sample_size for bundle in evidence.bundles)
        validation_total = sum(bundle.validation_samples for bundle in evidence.bundles)
        test_total = sum(bundle.test_samples for bundle in evidence.bundles)
        median_estimate_bps = _median_or_none(bundle.estimate_bps for bundle in evidence.bundles)
        median_net_expectancy_bps = _median_or_none(bundle.net_expectancy_bps for bundle in evidence.bundles)
        q_values = [bundle.q_value for bundle in evidence.bundles if bundle.q_value is not None]
        stability_values = [bundle.stability_score for bundle in evidence.bundles if bundle.stability_score is not None]
        neg_control_rates = [bundle.negative_control_rate for bundle in evidence.bundles if bundle.negative_control_rate is not None]
        realized_oos_supported = any(bundle.realized_oos_supported for bundle in evidence.bundles)
        governance = get_event_governance_metadata(str(row.get("event_contract_ids", "")).split("|")[0]) if str(row.get("event_contract_ids", "")).strip() else {}
        primary_event_id = next(
            (bundle.primary_event_id for bundle in evidence.bundles if str(bundle.primary_event_id).strip()),
            "",
        )
        if not primary_event_id:
            required_contracts = evidence.required_contracts or _required_contracts(row)
            primary_event_id = required_contracts[0] if required_contracts else ""
        primary_event_id = str(primary_event_id).strip().upper()
        compat_event_family = next(
            (bundle.event_family for bundle in evidence.bundles if str(bundle.event_family).strip()),
            "",
        )
        compat_event_family = str(compat_event_family or primary_event_id).strip().upper()

        scores = {
            "ontology_fidelity": _ontology_fidelity(row),
            "implementation_fidelity": _implementation_fidelity(row, evidence),
            "evidence_strength": _evidence_strength(evidence),
            "regime_clarity": _regime_clarity(row),
            "invalidation_clarity": _invalidation_clarity(row),
            "confounder_handling": _confounder_handling(evidence),
            "holdout_quality": _holdout_quality(evidence),
            "deployment_suitability": _deployment_suitability(row),
        }
        scores["total_score"] = sum(scores.values())
        decision = _decision_for_row(row, evidence, scores, policy)
        gaps = _evidence_gaps(evidence, scores)
        empirical_rows.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "primary_event_id": primary_event_id,
                "compat_event_family": compat_event_family,
                "source_type": row.get("source_type", ""),
                "source_contract_ids": row.get("source_contract_ids", ""),
                "governance_tier": row.get("governance_tier", governance.get("tier", "")),
                "operational_role": row.get("operational_role", governance.get("operational_role", "")),
                "deployment_disposition": row.get("deployment_disposition", governance.get("deployment_disposition", "")),
                "matched_bundle_count": len(evidence.bundles),
                "matched_required_coverage": f"{evidence.coverage:.2f}",
                "matched_run_ids": "|".join(matched_run_ids),
                "matched_bundle_candidate_ids": "|".join(matched_candidate_ids),
                "empirical_evidence_source": "|".join(f"evidence_bundle:{bundle.run_id}:{bundle.candidate_id}" for bundle in evidence.bundles),
                "sample_size_total": sample_size_total,
                "validation_samples_total": validation_total,
                "test_samples_total": test_total,
                "median_estimate_bps": "" if median_estimate_bps is None else f"{median_estimate_bps:.4f}",
                "median_net_expectancy_bps": "" if median_net_expectancy_bps is None else f"{median_net_expectancy_bps:.4f}",
                "best_q_value": "" if not q_values else f"{min(q_values):.6f}",
                "best_stability_score": "" if not stability_values else f"{max(stability_values):.6f}",
                "negative_control_rate_min": "" if not neg_control_rates else f"{min(neg_control_rates):.6f}",
                "realized_oos_supported": int(realized_oos_supported),
                **scores,
                "empirical_decision": decision,
                "lifecycle_class": _lifecycle_class(decision),
                "evidence_gap_summary": "|".join(gaps),
                "recommended_next_action": _next_action_for_decision(decision, gaps),
            }
        )

    csv_path = out_dir / "thesis_empirical_scorecards.csv"
    json_path = out_dir / "thesis_empirical_scorecards.json"
    md_path = out_dir / "thesis_empirical_summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(EMPIRICAL_SCORECARD_FIELDS))
        writer.writeheader()
        writer.writerows(empirical_rows)

    json_path.write_text(json.dumps(empirical_rows, indent=2), encoding="utf-8")

    decision_counts: dict[str, int] = {}
    for row in empirical_rows:
        decision = str(row["empirical_decision"])
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    matched_rows = [row for row in empirical_rows if int(row.get("matched_bundle_count", 0)) > 0]
    sorted_rows = sorted(empirical_rows, key=lambda item: (-int(item["matched_bundle_count"]), -int(item["total_score"]), str(item["candidate_id"])))

    lines = [
        "# Thesis empirical summary",
        "",
        "This pass consumes real promotion evidence bundles when they exist and maps them onto the founding seed queue.",
        "Unlike the governance-only Block B scorecards, this artifact can clear a thesis when valid empirical evidence, holdout support, and confounder coverage are present.",
        "",
        f"- candidates_reviewed: `{len(empirical_rows)}`",
        f"- empirical_matches: `{len(matched_rows)}`",
        "- decision_counts: " + ", ".join(f"`{key}={value}`" for key, value in sorted(decision_counts.items())),
        "",
    ]
    if not matched_rows:
        lines.extend([
            "## Key conclusion",
            "",
            "No empirical evidence bundles matched the current founding queue in this repo snapshot.",
            "The empirical pass is now implemented, but the repository still needs real event-study / promotion bundle outputs for the founding theses before any seed promotion can occur.",
            "",
        ])
    else:
        promotable = [row for row in empirical_rows if row["empirical_decision"] in {"seed_promote", "paper_candidate"}]
        if promotable:
            lines.extend([
                "## Key conclusion",
                "",
                f"{len(promotable)} candidate(s) clear empirical seed promotion gates under the current evidence corpus.",
                "",
            ])
        else:
            lines.extend([
                "## Key conclusion",
                "",
                "Empirical bundles were found, but no candidate yet clears the seed promotion gate after holdout/confounder requirements and governance checks.",
                "",
            ])
    lines.extend([
        "## Top empirical candidates",
        "",
        "| Candidate | Bundles | Coverage | Total score | Decision | Evidence gaps | Next action |",
        "|---|---:|---:|---:|---|---|---|",
    ])
    for row in sorted_rows[:8]:
        lines.append(
            "| {candidate_id} | {matched_bundle_count} | {matched_required_coverage} | {total_score} | {empirical_decision} | {evidence_gap_summary} | {recommended_next_action} |".format(**row)
        )
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "md": md_path}


__all__ = ["run_empirical_seed_pass", "_load_empirical_bundles"]
