from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project.research.agent_io.campaign_planner import CampaignPlanResult, CampaignPlanner, CampaignPlannerConfig, run_campaign_planner_cycle
    from project.research.agent_io.execute_proposal import build_run_all_command, execute_proposal
    from project.research.agent_io.issue_proposal import generate_run_id, issue_proposal
    from project.research.agent_io.proposal_schema import AgentProposal, load_agent_proposal
    from project.research.agent_io.proposal_to_experiment import (
        build_run_all_overrides,
        proposal_to_experiment_config,
        translate_and_validate_proposal,
    )

_EXPORTS = {
    "AgentProposal": ("project.research.agent_io.proposal_schema", "AgentProposal"),
    "CampaignPlanResult": ("project.research.agent_io.campaign_planner", "CampaignPlanResult"),
    "CampaignPlanner": ("project.research.agent_io.campaign_planner", "CampaignPlanner"),
    "CampaignPlannerConfig": ("project.research.agent_io.campaign_planner", "CampaignPlannerConfig"),
    "run_campaign_planner_cycle": ("project.research.agent_io.campaign_planner", "run_campaign_planner_cycle"),
    "build_run_all_command": (
        "project.research.agent_io.execute_proposal",
        "build_run_all_command",
    ),
    "build_run_all_overrides": (
        "project.research.agent_io.proposal_to_experiment",
        "build_run_all_overrides",
    ),
    "execute_proposal": ("project.research.agent_io.execute_proposal", "execute_proposal"),
    "generate_run_id": ("project.research.agent_io.issue_proposal", "generate_run_id"),
    "issue_proposal": ("project.research.agent_io.issue_proposal", "issue_proposal"),
    "load_agent_proposal": ("project.research.agent_io.proposal_schema", "load_agent_proposal"),
    "proposal_to_experiment_config": (
        "project.research.agent_io.proposal_to_experiment",
        "proposal_to_experiment_config",
    ),
    "translate_and_validate_proposal": (
        "project.research.agent_io.proposal_to_experiment",
        "translate_and_validate_proposal",
    ),
}

__all__ = [
    "AgentProposal",
    "CampaignPlanResult",
    "CampaignPlanner",
    "CampaignPlannerConfig",
    "run_campaign_planner_cycle",
    "build_run_all_command",
    "build_run_all_overrides",
    "execute_proposal",
    "generate_run_id",
    "issue_proposal",
    "load_agent_proposal",
    "proposal_to_experiment_config",
    "translate_and_validate_proposal",
]


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
