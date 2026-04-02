from __future__ import annotations

from typing import Any

from project.apps.chatgpt.resources import WIDGET_URI
from project.apps.chatgpt.schemas import (
    CompareRunsInput,
    CodexOperatorInvokeInput,
    OperatorDashboardInput,
    ProposalExplainInput,
    ProposalIssueInput,
    ProposalLintInput,
    ProposalPreflightInput,
    ProposalPreviewInput,
    RegimeReportInput,
    RenderOperatorSummaryInput,
    RunDiagnosticsInput,
    ToolDefinition,
    ToolHints,
)


def _schema(model: type[Any]) -> str:
    return f"{model.__module__}.{model.__name__}"


def _json_schema(model: type[Any]) -> dict[str, Any]:
    return model.model_json_schema()


TOOL_CATALOG: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="edge_preflight_proposal",
        title="Preflight Edge proposal",
        description="Validate proposal shape, data coverage, and artifact writability before a bounded run.",
        handler="project.apps.chatgpt.handlers.preflight_proposal",
        input_model=_schema(ProposalPreflightInput),
        input_schema=_json_schema(ProposalPreflightInput),
        invoking_text="Running preflight",
        invoked_text="Preflight ready",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Writes a temporary artifact root probe and may create local scratch directories during validation.",
        ),
    ),
    ToolDefinition(
        name="edge_explain_proposal",
        title="Explain Edge proposal",
        description="Resolve a bounded proposal into required detectors, features, states, and operator-facing constraints.",
        handler="project.apps.chatgpt.handlers.explain_proposal_summary",
        input_model=_schema(ProposalExplainInput),
        input_schema=_json_schema(ProposalExplainInput),
        invoking_text="Explaining proposal",
        invoked_text="Proposal explained",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Uses the current proposal translation path, which stages temporary local files while building the plan.",
        ),
    ),
    ToolDefinition(
        name="edge_lint_proposal",
        title="Lint Edge proposal",
        description="Check whether a proposal stays bounded and warn when the search surface looks too broad.",
        handler="project.apps.chatgpt.handlers.lint_proposal_summary",
        input_model=_schema(ProposalLintInput),
        input_schema=_json_schema(ProposalLintInput),
        invoking_text="Linting proposal",
        invoked_text="Lint ready",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Stages temporary proposal artifacts during validation even though it does not issue a durable run.",
        ),
    ),
    ToolDefinition(
        name="edge_preview_plan",
        title="Preview Edge plan",
        description="Translate a proposal into a validated plan and run-all overrides without issuing a durable proposal record.",
        handler="project.apps.chatgpt.handlers.preview_plan",
        input_model=_schema(ProposalPreviewInput),
        input_schema=_json_schema(ProposalPreviewInput),
        invoking_text="Previewing plan",
        invoked_text="Plan preview ready",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Uses scratch writes to stage and validate the experiment config, but avoids durable proposal memory updates.",
        ),
    ),
    ToolDefinition(
        name="edge_issue_plan",
        title="Issue Edge plan",
        description="Create a proposal memory record and execute the canonical plan-only operator path.",
        handler="project.apps.chatgpt.handlers.issue_plan",
        input_model=_schema(ProposalIssueInput),
        input_schema=_json_schema(ProposalIssueInput),
        invoking_text="Issuing plan",
        invoked_text="Plan issued",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Creates proposal memory rows and local artifacts for a durable plan issuance.",
        ),
    ),
    ToolDefinition(
        name="edge_issue_run",
        title="Issue Edge run",
        description="Create a proposal memory record and execute the canonical operator run path for the proposal.",
        handler="project.apps.chatgpt.handlers.issue_run",
        input_model=_schema(ProposalIssueInput),
        input_schema=_json_schema(ProposalIssueInput),
        invoking_text="Issuing run",
        invoked_text="Run issued",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=False,
            open_world=False,
            justification="Starts a bounded local workflow that creates durable artifacts, manifests, and proposal memory records.",
        ),
    ),
    ToolDefinition(
        name="edge_invoke_operator",
        title="Invoke Edge operator via Codex MCP",
        description="Run or continue a Codex MCP session inside the Edge repository to inspect, edit, and repair local files or tooling. Use this for repo maintenance through Codex, not for issuing a new Edge run.",
        handler="project.apps.chatgpt.handlers.invoke_codex_operator",
        input_model=_schema(CodexOperatorInvokeInput),
        input_schema=_json_schema(CodexOperatorInvokeInput),
        invoking_text="Invoking Codex",
        invoked_text="Codex repo task finished",
        category="mutation",
        hints=ToolHints(
            read_only=False,
            destructive=True,
            open_world=False,
            justification="Invokes or continues a Codex MCP session against the local Edge workspace for repo inspection or repair, which may edit files, run commands, or perform irreversible local mutations depending on the task.",
        ),
    ),
    ToolDefinition(
        name="edge_get_negative_result_diagnostics",
        title="Get Edge diagnostics",
        description="Explain why an existing run failed to support the hypothesis and suggest the next bounded action.",
        handler="project.apps.chatgpt.handlers.get_negative_result_diagnostics",
        input_model=_schema(RunDiagnosticsInput),
        input_schema=_json_schema(RunDiagnosticsInput),
        invoking_text="Loading diagnostics",
        invoked_text="Diagnostics ready",
        category="data",
        hints=ToolHints(
            read_only=True,
            destructive=False,
            open_world=False,
            justification="Reads existing run artifacts and reports without changing local or public state.",
        ),
    ),
    ToolDefinition(
        name="edge_get_regime_report",
        title="Get Edge regime report",
        description="Summarize regime stability for a run and highlight sign flips or consistent behavior.",
        handler="project.apps.chatgpt.handlers.get_regime_report",
        input_model=_schema(RegimeReportInput),
        input_schema=_json_schema(RegimeReportInput),
        invoking_text="Loading regime report",
        invoked_text="Regime report ready",
        category="data",
        hints=ToolHints(
            read_only=True,
            destructive=False,
            open_world=False,
            justification="Reads existing reports and candidate artifacts only.",
        ),
    ),
    ToolDefinition(
        name="edge_compare_runs",
        title="Compare Edge runs",
        description="Compare two or more existing runs across time slices and summarize the strongest or most unstable slice.",
        handler="project.apps.chatgpt.handlers.compare_runs",
        input_model=_schema(CompareRunsInput),
        input_schema=_json_schema(CompareRunsInput),
        invoking_text="Comparing runs",
        invoked_text="Comparison ready",
        category="data",
        hints=ToolHints(
            read_only=True,
            destructive=False,
            open_world=False,
            justification="Reads run summaries and operator reports without changing any state.",
        ),
    ),
    ToolDefinition(
        name="edge_get_operator_dashboard",
        title="Get Edge operator dashboard",
        description="Load proposal memory, recent proposals, prior run results, and the current candidate pipeline board for the active Edge program so operators can query project status in one place.",
        handler="project.apps.chatgpt.handlers.get_operator_dashboard",
        input_model=_schema(OperatorDashboardInput),
        input_schema=_json_schema(OperatorDashboardInput),
        invoking_text="Loading dashboard",
        invoked_text="Dashboard ready",
        category="data",
        hints=ToolHints(
            read_only=True,
            destructive=False,
            open_world=False,
            justification="Reads existing memory tables, belief-state JSON, and run manifests without creating or mutating local state.",
        ),
    ),
    ToolDefinition(
        name="edge_render_operator_summary",
        title="Render Edge operator summary",
        description="Render a compact operator dashboard from data returned by another Edge tool. Pass the full payload from edge_get_operator_dashboard via the dashboard field, or pass a prepared summary payload from another data tool.",
        handler="project.apps.chatgpt.handlers.render_operator_summary",
        input_model=_schema(RenderOperatorSummaryInput),
        input_schema=_json_schema(RenderOperatorSummaryInput),
        invoking_text="Rendering dashboard",
        invoked_text="Dashboard ready",
        category="render",
        ui_resource_uri=WIDGET_URI,
        output_template_uri=WIDGET_URI,
        hints=ToolHints(
            read_only=True,
            destructive=False,
            open_world=False,
            justification="Only formats already-prepared structured content for presentation in the widget.",
        ),
    ),
)


def get_tool_definition(name: str) -> ToolDefinition:
    for tool in TOOL_CATALOG:
        if tool.name == name:
            return tool
    raise KeyError(name)
