from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from project.artifacts import live_thesis_index_path
from project.core.config import get_data_root
from project.events.contract_registry import load_active_event_contracts
from project.events.governance import get_event_governance_metadata
from project.episodes import load_episode_registry
from project.live.thesis_store import ThesisStore
from project.spec_registry.loaders import repo_root

DOCS_GENERATED = repo_root() / "docs" / "generated"
SEED_POLICY_PATH = repo_root() / "spec" / "promotion" / "seed_promotion_policy.yaml"

DEFAULT_SEED_EVENTS: tuple[str, ...] = (
    "VOL_SHOCK",
    "LIQUIDITY_VACUUM",
    "LIQUIDITY_STRESS_DIRECT",
    "BASIS_DISLOC",
    "FND_DISLOC",
    "LIQUIDATION_CASCADE",
)
DEFAULT_CONFIRM_THESES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM", ("VOL_SHOCK", "LIQUIDITY_VACUUM")),
    ("THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM", ("LIQUIDITY_VACUUM", "LIQUIDATION_CASCADE")),
    ("THESIS_BASIS_FND_CONFIRM", ("BASIS_DISLOC", "FND_DISLOC")),
    ("THESIS_LIQUIDATION_DEPTH_CONFIRM", ("LIQUIDATION_CASCADE", "LIQUIDITY_STRESS_DIRECT")),
)
DEFAULT_EPISODES: tuple[str, ...] = (
    "EP_VOLATILITY_BREAKOUT",
    "EP_LIQUIDITY_SHOCK",
    "EP_DISLOCATION_REPAIR",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _horizon_guess(*tokens: str) -> str:
    joined = " ".join(str(token or "").strip().lower() for token in tokens)
    if any(tag in joined for tag in ("repair", "reversion", "normalization", "unwind")):
        return "8-32 bars"
    if any(tag in joined for tag in ("breakout", "shock", "cascade", "spike", "vacuum")):
        return "8-24 bars"
    if "window" in joined or "session" in joined:
        return "4-12 bars"
    return "8-24 bars"


def _expected_path(*tokens: str) -> str:
    joined = " ".join(str(token or "").strip().lower() for token in tokens)
    if any(tag in joined for tag in ("repair", "reversion", "normalization")):
        return "Expect bounded repair or convergence after the dislocation resolves."
    if any(tag in joined for tag in ("cascade", "liquidation", "exhaustion")):
        return "Expect forced flow to culminate in either continued stress or a sharp repair window."
    if any(tag in joined for tag in ("shock", "spike", "breakout")):
        return "Expect volatility expansion and directional follow-through after onset."
    if any(tag in joined for tag in ("vacuum", "stress", "disloc")):
        return "Expect unstable liquidity conditions that either amplify the move or attract a repair response."
    return "Expect a bounded post-trigger response that should be testable in forward bars."


def _seed_status(role: str, disposition: str, trade_trigger_eligible: bool) -> str:
    if not trade_trigger_eligible:
        return "needs_repair"
    blocked_dispositions = {"context_only", "research_only", "repair_before_promotion", "inactive", "deprecated", "alias_only"}
    blocked_roles = {"context", "filter", "research_only", "sequence_component"}
    if role in blocked_roles or disposition in blocked_dispositions:
        return "needs_repair"
    return "test_now"


def _next_action(status: str) -> str:
    if status == "needs_repair":
        return "repair_governance_or_role_conflict"
    if status == "ready_for_seed_packaging":
        return "package_seed_thesis"
    if status == "reject":
        return "archive_candidate"
    return "run_seed_tests"


def _event_candidate_row(event_id: str) -> dict[str, str]:
    contracts = load_active_event_contracts()
    contract = contracts[event_id]
    governance = get_event_governance_metadata(event_id)
    status = _seed_status(
        str(governance.get("operational_role", "")).lower(),
        str(governance.get("deployment_disposition", "")).lower(),
        bool(governance.get("trade_trigger_eligible", False)),
    )
    horizon = _horizon_guess(contract.get("phase"), contract.get("canonical_family"), event_id)
    expected = _expected_path(contract.get("phase"), contract.get("canonical_family"), event_id)
    invalidation = str(contract.get("invalidation_rule", "") or "").strip() or "Explicit invalidation still needs empirical refinement."
    hypothesis = (
        f"When {event_id} fires under governed contract semantics, expect the declared post-event path to materialize "
        f"over {horizon} unless {invalidation.lower()}"
    )
    return {
        "candidate_id": f"THESIS_{event_id}",
        "source_type": "event",
        "source_contract_ids": event_id,
        "event_contract_ids": event_id,
        "episode_contract_ids": "",
        "source_campaign_id": "",
        "hypothesis_statement": hypothesis,
        "expected_direction_or_path": expected,
        "horizon_guess": horizon,
        "invalidation_rule": invalidation,
        "current_evidence_source": f"event_contract_fallback:{event_id}",
        "regime_assumptions": str(contract.get("regime_applicability", "") or "").strip(),
        "confounders_checked": "none_yet",
        "detector_fidelity_status": "governed_contract_available",
        "governance_tier": str(governance.get("tier", "")).upper(),
        "operational_role": str(governance.get("operational_role", "")).lower(),
        "deployment_disposition": str(governance.get("deployment_disposition", "")).lower(),
        "promotion_status": status,
        "next_action": _next_action(status),
    }


def _confirm_candidate_row(candidate_id: str, event_ids: Iterable[str]) -> dict[str, str]:
    event_list = [str(event_id).strip().upper() for event_id in event_ids if str(event_id).strip()]
    governance_rows = [get_event_governance_metadata(event_id) for event_id in event_list]
    status = "test_now"
    if any(not bool(row.get("trade_trigger_eligible", False)) for row in governance_rows):
        status = "needs_repair"
    horizon = _horizon_guess(*event_list)
    expected = _expected_path(*event_list)
    invalidation = " OR ".join(
        str(load_active_event_contracts()[event_id].get("invalidation_rule", "") or "").strip()
        for event_id in event_list
        if str(load_active_event_contracts()[event_id].get("invalidation_rule", "") or "").strip()
    ) or "Explicit invalidation still needs empirical refinement."
    return {
        "candidate_id": candidate_id,
        "source_type": "event_plus_confirm",
        "source_contract_ids": "|".join(event_list),
        "event_contract_ids": "|".join(event_list),
        "episode_contract_ids": "",
        "source_campaign_id": "",
        "hypothesis_statement": (
            f"When {' + '.join(event_list)} align in the same episode window, the combined setup should be stronger than either event alone."
        ),
        "expected_direction_or_path": expected,
        "horizon_guess": horizon,
        "invalidation_rule": invalidation,
        "current_evidence_source": "event_contract_fallback:paired_confirmation",
        "regime_assumptions": "Requires compatible regimes for both trigger and confirmation legs.",
        "confounders_checked": "none_yet",
        "detector_fidelity_status": "governed_contract_available",
        "governance_tier": "/".join(sorted({str(row.get('tier', '')).upper() for row in governance_rows if str(row.get('tier', '')).strip()})),
        "operational_role": "confirm",
        "deployment_disposition": "seed_review_required",
        "promotion_status": status,
        "next_action": _next_action(status),
    }


def _episode_candidate_row(episode_id: str) -> dict[str, str]:
    registry = load_episode_registry()
    episode = registry[episode_id]
    status = _seed_status(
        episode.operational_role.lower(),
        episode.deployment_disposition.lower(),
        episode.operational_role.lower() in {"trigger", "confirm"} and episode.deployment_disposition.lower() not in {"context_only", "research_only", "repair_before_promotion", "inactive", "deprecated", "alias_only"},
    )
    required = "|".join(episode.required_events)
    invalidation = "|".join(episode.invalidation_events) or "Explicit episode invalidation still needs empirical refinement."
    horizon = _horizon_guess(episode.title, episode.description, episode.sequence_mode)
    expected = _expected_path(episode.title, episode.description, episode.sequence_mode)
    return {
        "candidate_id": f"THESIS_{episode_id}",
        "source_type": "episode",
        "source_contract_ids": episode_id,
        "event_contract_ids": required,
        "episode_contract_ids": episode_id,
        "source_campaign_id": "",
        "hypothesis_statement": (
            f"When episode {episode_id} forms from {' + '.join(episode.required_events)}, expect the episode path described by the contract to be testable over {horizon}."
        ),
        "expected_direction_or_path": expected,
        "horizon_guess": horizon,
        "invalidation_rule": invalidation,
        "current_evidence_source": f"episode_contract_fallback:{episode_id}",
        "regime_assumptions": (
            "Allowed unless disallowed regimes are present"
            + (f"; blocked in {', '.join(episode.disallowed_regimes)}" if episode.disallowed_regimes else "")
        ),
        "confounders_checked": "none_yet",
        "detector_fidelity_status": "episode_contract_available",
        "governance_tier": episode.tier.upper(),
        "operational_role": episode.operational_role.lower(),
        "deployment_disposition": episode.deployment_disposition.lower(),
        "promotion_status": status,
        "next_action": _next_action(status),
    }


def build_promotion_seed_inventory(*, docs_dir: str | Path | None = None, max_candidates: int | None = None) -> dict[str, Path]:
    out_dir = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)
    csv_path = out_dir / "promotion_seed_inventory.csv"
    md_path = out_dir / "promotion_seed_inventory.md"

    rows: list[dict[str, str]] = []
    for event_id in DEFAULT_SEED_EVENTS:
        rows.append(_event_candidate_row(event_id))
    for candidate_id, event_ids in DEFAULT_CONFIRM_THESES:
        rows.append(_confirm_candidate_row(candidate_id, event_ids))
    for episode_id in DEFAULT_EPISODES:
        rows.append(_episode_candidate_row(episode_id))

    if max_candidates is not None:
        rows = rows[: max(1, int(max_candidates))]
    fieldnames = [
        "candidate_id",
        "source_type",
        "source_contract_ids",
        "event_contract_ids",
        "episode_contract_ids",
        "source_campaign_id",
        "hypothesis_statement",
        "expected_direction_or_path",
        "horizon_guess",
        "invalidation_rule",
        "current_evidence_source",
        "regime_assumptions",
        "confounders_checked",
        "detector_fidelity_status",
        "governance_tier",
        "operational_role",
        "deployment_disposition",
        "promotion_status",
        "next_action",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["promotion_status"]] = status_counts.get(row["promotion_status"], 0) + 1
    lines = [
        "# Promotion seed inventory",
        "",
        f"- candidate_count: `{len(rows)}`",
        f"- status_counts: `{json.dumps(status_counts, sort_keys=True)}`",
        "- source_mode: `governance-aware fallback queue from Wave 3 contracts and episode registry`",
        "",
        "## Candidate queue",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['candidate_id']}",
                f"- source_type: `{row['source_type']}`",
                f"- source_contract_ids: `{row['source_contract_ids']}`",
                f"- governance: tier `{row['governance_tier']}`, role `{row['operational_role']}`, disposition `{row['deployment_disposition']}`",
                f"- promotion_status: `{row['promotion_status']}`",
                f"- next_action: `{row['next_action']}`",
                f"- horizon_guess: `{row['horizon_guess']}`",
                f"- expected_direction_or_path: {row['expected_direction_or_path']}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"csv_path": csv_path, "md_path": md_path}


def build_thesis_bootstrap_baseline(*, docs_dir: str | Path | None = None, data_root: str | Path | None = None) -> dict[str, Path]:
    out_dir = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()

    live_index_path = live_thesis_index_path(resolved_data_root)
    live_index = _read_json(live_index_path)
    latest_run_id = str(live_index.get("latest_run_id", "")).strip()
    thesis_count = 0
    active_count = 0
    thesis_source_path = ""
    thesis_status = "missing"
    if latest_run_id:
        try:
            store = ThesisStore.from_run_id(latest_run_id, data_root=resolved_data_root)
            thesis_count = len(store.all())
            active_count = len(store.active_theses())
            thesis_source_path = str(store.source_path or "")
            thesis_status = "available"
        except Exception:
            thesis_status = "unreadable"

    thesis_store_payload = {
        "schema_version": "thesis_store_pre_bootstrap_v1",
        "data_root": str(resolved_data_root),
        "live_index_path": str(live_index_path),
        "has_live_index": bool(live_index),
        "latest_run_id": latest_run_id,
        "thesis_count": thesis_count,
        "active_thesis_count": active_count,
        "source_path": thesis_source_path,
        "status": thesis_status,
    }

    overlap_source_path = out_dir / "thesis_overlap_graph.json"
    overlap_payload = _read_json(overlap_source_path)
    if not overlap_payload:
        overlap_payload = {
            "schema_version": "thesis_overlap_graph_v1",
            "thesis_count": 0,
            "overlap_group_count": 0,
            "nodes": [],
            "edges": [],
            "groups": [],
        }

    thesis_json_path = out_dir / "thesis_store_pre_bootstrap.json"
    overlap_json_path = out_dir / "overlap_graph_pre_bootstrap.json"
    baseline_md_path = out_dir / "thesis_bootstrap_baseline.md"

    thesis_json_path.write_text(json.dumps(thesis_store_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    overlap_json_path.write_text(json.dumps(overlap_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    observations = []
    if thesis_count == 0:
        observations.append("No canonical promoted thesis store is available yet.")
    if int(overlap_payload.get("thesis_count", 0) or 0) == 0:
        observations.append("The thesis overlap graph is empty, so allocator overlap controls are not yet operating on real theses.")
    if not observations:
        observations.append("A pre-existing thesis store was detected; Block A is running against a non-empty baseline.")

    lines = [
        "# Thesis bootstrap baseline",
        "",
        f"- data_root: `{resolved_data_root}`",
        f"- live_index_present: `{bool(live_index)}`",
        f"- latest_run_id: `{latest_run_id or 'none'}`",
        f"- thesis_count: `{thesis_count}`",
        f"- active_thesis_count: `{active_count}`",
        f"- overlap_graph_thesis_count: `{int(overlap_payload.get('thesis_count', 0) or 0)}`",
        f"- overlap_group_count: `{int(overlap_payload.get('overlap_group_count', 0) or 0)}`",
        "",
        "## Observations",
    ]
    lines.extend(f"- {item}" for item in observations)
    baseline_md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "baseline_md_path": baseline_md_path,
        "thesis_store_json_path": thesis_json_path,
        "overlap_graph_json_path": overlap_json_path,
    }


def load_seed_promotion_policy(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SEED_POLICY_PATH
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Seed promotion policy must decode to a mapping")
    return dict(payload)


def write_seed_promotion_policy_artifacts(*, docs_dir: str | Path | None = None, policy_path: str | Path | None = None) -> dict[str, Path]:
    out_dir = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)
    payload = load_seed_promotion_policy(policy_path)
    md_path = out_dir / "seed_promotion_policy.md"
    lines = [
        "# Seed promotion policy",
        "",
        f"- schema_version: `{payload.get('schema_version', '')}`",
        f"- lifecycle_classes: `{', '.join(str(item) for item in payload.get('lifecycle_classes', []))}`",
        f"- candidate_statuses: `{', '.join(str(item) for item in payload.get('candidate_statuses', []))}`",
        "",
        "## Minimum requirements",
    ]
    for key, value in dict(payload.get("minimum_requirements", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Seed promotion usage"]) 
    seed_promotion = dict(payload.get("seed_promotion", {}))
    for key, value in seed_promotion.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        lines.append(f"- {key}: `{rendered}`")
    lines.extend(["", "## Governance defaults"]) 
    governance = dict(payload.get("governance_defaults", {}))
    for key, value in governance.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        lines.append(f"- {key}: `{rendered}`")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"md_path": md_path}
