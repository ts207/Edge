# Architectural Baseline B

This note records the repo state after the proposal-front-door and runtime-lineage cleanup.

## Canonical

- operator-facing proposal format uses one atomic `hypothesis` object
- `load_operator_proposal(...)` normalizes operator proposals into legacy `AgentProposal`
- bounded research flow is:
  `single hypothesis proposal -> bounded run -> promotion -> export thesis batch -> explicit runtime selection`
- runtime consumes one explicit thesis batch via `strategy_runtime.thesis_path` or `strategy_runtime.thesis_run_id`
- trading permission is determined by `deployment_state`

## Compatibility Only

- legacy proposal shape with `trigger_space`, `templates`, `directions`, `horizons_bars`, and `entry_lags`
- internal promotion vocabulary such as `seed_promoted`, `paper_promoted`, and `production_promoted`
- advanced/bootstrap maintenance surfaces such as `make package`
- compatibility-only thesis index helpers that preserve catalog metadata but are not canonical runtime selectors

## Deferred

- deeper engine reduction or proposal-to-experiment flattening
- further legacy internal vocabulary cleanup
- broader abstraction pruning across search, promotion, and packaging layers
- gradual retirement of compatibility-only operator-visible surfaces after a stability window
