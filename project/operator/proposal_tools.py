from __future__ import annotations

from pathlib import Path
from typing import Any

from project.core.config import get_data_root
from project.operator.bounded import validate_bounded_proposal
from project.research.agent_io.proposal_schema import load_operator_proposal
from project.research.agent_io.proposal_to_experiment import translate_and_validate_proposal


def lint_proposal(
    *,
    proposal_path: str | Path,
    registry_root: str | Path = "project/configs/registries",
    data_root: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()
    proposal = load_operator_proposal(proposal_path)
    translation = translate_and_validate_proposal(
        proposal,
        registry_root=Path(registry_root),
        out_dir=Path(out_dir) if out_dir is not None else None,
    )
    bounded = validate_bounded_proposal(proposal, data_root=resolved_data_root)
    warnings: list[str] = []
    estimated = int(translation["validated_plan"].get("estimated_hypothesis_count", 0) or 0)
    if estimated > 250:
        warnings.append(f"broad_search_surface:{estimated}")
    result = {
        "status": "pass",
        "proposal_path": str(proposal_path),
        "program_id": proposal.program_id,
        "warnings": warnings,
        "validated_plan": translation["validated_plan"],
        "bounded_validation": bounded.to_dict() if bounded is not None else None,
    }
    if warnings:
        result["status"] = "warn"
    return result


def explain_proposal(
    *,
    proposal_path: str | Path,
    registry_root: str | Path = "project/configs/registries",
    data_root: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()
    proposal = load_operator_proposal(proposal_path)
    translation = translate_and_validate_proposal(
        proposal,
        registry_root=Path(registry_root),
        out_dir=Path(out_dir) if out_dir is not None else None,
    )
    bounded = validate_bounded_proposal(proposal, data_root=resolved_data_root)
    return {
        "proposal_path": str(proposal_path),
        "program_id": proposal.program_id,
        "description": proposal.description,
        "run_mode": proposal.run_mode,
        "objective_name": proposal.objective_name,
        "symbols": list(proposal.symbols),
        "templates": list(proposal.templates),
        "horizons_bars": list(proposal.horizons_bars),
        "directions": list(proposal.directions),
        "entry_lags": list(proposal.entry_lags),
        "contexts": dict(proposal.contexts),
        "bounded": bounded.to_dict() if bounded is not None else None,
        "required_detectors": list(translation["validated_plan"].get("required_detectors", [])),
        "required_features": list(translation["validated_plan"].get("required_features", [])),
        "required_states": list(translation["validated_plan"].get("required_states", [])),
        "estimated_hypothesis_count": int(translation["validated_plan"].get("estimated_hypothesis_count", 0) or 0),
        "run_all_overrides": translation["run_all_overrides"],
    }
