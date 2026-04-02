from project.apps.chatgpt.backlog import IMPLEMENTATION_BACKLOG
from project.apps.chatgpt.tool_catalog import TOOL_CATALOG, get_tool_definition


def test_render_tool_carries_widget_metadata() -> None:
    render_tool = get_tool_definition("edge_render_operator_summary")

    assert render_tool.category == "render"
    assert render_tool.ui_resource_uri is not None
    assert render_tool.output_template_uri == render_tool.ui_resource_uri
    assert render_tool.hints.read_only is True


def test_read_only_hints_match_existing_edge_behavior() -> None:
    compare_tool = get_tool_definition("edge_compare_runs")
    dashboard_tool = get_tool_definition("edge_get_operator_dashboard")
    invoke_tool = get_tool_definition("edge_invoke_operator")
    issue_run_tool = get_tool_definition("edge_issue_run")
    preview_tool = get_tool_definition("edge_preview_plan")

    assert compare_tool.hints.read_only is True
    assert dashboard_tool.hints.read_only is True
    assert invoke_tool.hints.read_only is False
    assert invoke_tool.hints.destructive is True
    assert issue_run_tool.hints.read_only is False
    assert preview_tool.hints.read_only is False


def test_backlog_is_phase_ordered() -> None:
    phases = [item["phase"] for item in IMPLEMENTATION_BACKLOG]
    assert phases == sorted(phases)
    assert phases[0] == 1


def test_catalog_names_are_unique() -> None:
    names = [tool.name for tool in TOOL_CATALOG]
    assert len(names) == len(set(names))
