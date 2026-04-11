# Edge agents plugin

Repo-local Codex/plugin surface for the Edge repository.

## Purpose

Provide guided wrappers around the canonical bounded workflow without creating a parallel operator model.
The plugin should track the repo's current front door and maintenance loop:

`proposal -> lint/explain/preflight -> plan/run -> diagnose/report -> promote -> export thesis batch -> deploy`

## What is included

- skills for repo orientation, maintenance, ChatGPT-app development, coordination, analysis, and compiler flow
- thin wrappers around the canonical `make discover|promote|export|deploy-paper`, `edge operator ...`, and contract-validation surfaces
- hook definitions for contract-sensitive edits and recent-run awareness

## Important scripts

- `scripts/edge_query_knowledge.sh`
- `scripts/edge_preflight_proposal.sh`
- `scripts/edge_lint_proposal.sh`
- `scripts/edge_explain_proposal.sh`
- `scripts/edge_plan_proposal.sh`
- `scripts/edge_run_proposal.sh`
- `scripts/edge_diagnose_run.sh`
- `scripts/edge_regime_report.sh`
- `scripts/edge_chatgpt_app.sh`
- `scripts/edge_sync_plugin.sh`
- `scripts/edge_governance.sh`
- `scripts/edge_validate_repo.sh`
- `scripts/edge_verify_contracts.sh`
- `scripts/edge_verify_run.sh`
- `scripts/edge_compare_runs.sh`
- `scripts/edge_show_run_artifacts.sh`
- `scripts/edge_export_theses.sh`

## Dependency rule

These wrappers should remain thin around:

- `make discover|promote|export|deploy-paper`
- `edge operator lint|explain|preflight|plan|run|diagnose|regime-report|compare`
- `edge validate report`
- `python -m project.research.export_promoted_theses`
- `python -m project.scripts.run_researcher_verification`
- generated run and thesis artifacts

They are convenience surfaces, not policy owners.

## Maintenance focus

The plugin now helps route common developer change types:

- operator or proposal-surface changes -> contract verification plus current operator-doc review
- event, ontology, or registry changes -> contract verification plus event-contract and system-map regeneration
- runtime-thesis or overlap changes -> explicit run export plus overlap regeneration
- ChatGPT app changes -> `edge-chatgpt-app` inspection/serve helpers plus canonical operator surfaces
- plugin changes -> plugin-cache target discovery plus sync and sync checks

## Validation helpers

- `scripts/edge_verify_contracts.sh` runs the repo contract block
- `scripts/edge_validate_repo.sh contracts|minimum-green|all` routes repo validation to the correct surface
- `scripts/edge_sync_plugin.sh targets|check|sync [target_dir]` discovers or updates known installed plugin targets

## Relationship to docs

See:

- `docs/README.md`
- `docs/00_overview.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/03_promote.md`
- `docs/04_deploy.md`
- `docs/90_architecture.md`
- `docs/92_assurance_and_benchmarks.md`
- `docs/operator_command_inventory.md`
