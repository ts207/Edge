---
name: edge-chatgpt-app-developer
description: Develop or inspect the Edge ChatGPT app scaffold while keeping proposal, operator, reporting, and dashboard behavior routed through canonical repo surfaces. Use when the task touches project/apps/chatgpt or the MCP-facing operator interface.
---

# Edge ChatGPT App Developer

Use this skill for work in `project/apps/chatgpt/`.

## Read first

1. `project/apps/chatgpt/README.md`
2. `docs/README.md`
3. `docs/operator_command_inventory.md`
4. `docs/02_REPOSITORY_MAP.md`

## Role

- Treat the ChatGPT app as an interface layer around canonical operator surfaces.
- Inspect the app shape with `edge-chatgpt-app` helpers before changing handlers or UI.
- Keep proposal policy, stage logic, and promotion logic in canonical repo code, not in the app layer.

## Main commands

```bash
./plugins/edge-agents/scripts/edge_chatgpt_app.sh backlog
./plugins/edge-agents/scripts/edge_chatgpt_app.sh blueprint
./plugins/edge-agents/scripts/edge_chatgpt_app.sh widget
./plugins/edge-agents/scripts/edge_chatgpt_app.sh serve --host 127.0.0.1 --port 8000 --path /mcp
```

## Working rules

- Read `handlers.py`, `tool_catalog.py`, `resources.py`, `server.py`, `cli.py`, and relevant UI files only as interface code.
- Route proposal, operator, report, and dashboard behavior through canonical operator or reporting helpers.
- If a requested change belongs in `project.cli`, `project.operator`, or research services, say so and move the change there instead of duplicating logic in the app.
- Use the maintainer workflow after app-surface changes when docs or generated inventories may drift.

## Verification

- Use `edge-chatgpt-app backlog|blueprint|widget` as cheap interface sanity checks.
- Use repo validation when app changes affect docs, operator wiring, or test-coupled surfaces.
