# Repository map

## Top-level

- `project/` — core application code
- `spec/` — bounded hypothesis and event specifications
- `dashboard/` — operator dashboard
- `plugins/edge-agents/` — local plugin wrappers and guardrails
- `data/` — artifacts and local materializations

## Important subtrees under `project/`

- `project/cli.py` — canonical CLI front door
- `project/research/` — discovery, validation, promotion, export logic
- `project/live/` — runtime thesis store, deployment, retrieval, OMS, risk, and kill-switch logic
- `project/apps/chatgpt/` — ChatGPT-facing app/tool surfaces
- `project/contracts/` — structural contracts used by tests and generated artifacts
- `project/scripts/` — operational and generation utilities
