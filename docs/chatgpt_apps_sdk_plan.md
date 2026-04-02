# ChatGPT Apps SDK Plan

This document turns the initial Apps SDK planning work into a concrete Edge implementation backlog.

## Scope decision

The repo is Python-first and already exposes the right operator seams:

- `edge operator preflight`
- `edge operator plan`
- `edge operator run`
- `edge operator diagnose`
- `edge operator regime-report`
- `edge operator compare`

The app should therefore be a Python MCP server layered over the existing operator surfaces, not a new Node-first control plane.

## Initial package shape

The scaffold lives in `project/apps/chatgpt/`:

- `schemas.py` — typed tool input contracts
- `handlers.py` — wrappers over existing operator and reporting functions
- `tool_catalog.py` — tool inventory, hint classifications, and render metadata
- `resources.py` — widget URI and HTML bundle payload
- `server.py` — MCP blueprint plus the reserved FastMCP binding point
- `ui/operator_dashboard.html` — minimal render widget
- `cli.py` — local inspection entry points

## Tool plan

### Data/reporting tools

- `edge_get_negative_result_diagnostics`
- `edge_get_regime_report`
- `edge_compare_runs`

These are the clean read-only tools in the current repo.

### Scratch-writing operator tools

- `edge_preflight_proposal`
- `edge_explain_proposal`
- `edge_lint_proposal`
- `edge_preview_plan`

These are not truly read-only because the current translation and preflight code stages files or probes writable directories. Their hint annotations must stay aligned with that reality.

### Durable mutation tools

- `edge_issue_plan`
- `edge_issue_run`

These create proposal memory rows and durable run artifacts.

### Render tool

- `edge_render_operator_summary`

This follows the Apps SDK decoupled pattern: a data tool returns structured content first, then the render tool owns the widget template.

## Delivery phases

1. Bind the scaffold to a live Python MCP server over Streamable HTTP.
   Status: complete as a first pass in `project/apps/chatgpt/server.py`, using FastMCP plus a mounted Starlette app at `/mcp`.
2. Expose the read-only reporting tools first.
   Status: wired into the live server scaffold.
3. Expose the scratch-writing proposal tools with accurate hint annotations.
   Status: wired into the live server scaffold, still dependent on installed runtime deps for execution.
4. Expose durable issuance tools only after confirmation-oriented tests and prompt metadata are in place.
   Status: handlers are wired; UX hardening is still pending.
5. Harden payload trimming and app-review test cases for submission.
   Status: pending.

## Review constraints to keep front-of-mind

- Do not mark scratch-writing tools as read-only.
- Do not leak internal paths, IDs, timestamps, or debug payloads unless the user explicitly needs them.
- Keep render tools separate from data tools so the widget does not remount unnecessarily.
- Version the widget URI when the HTML bundle changes in a breaking way.
