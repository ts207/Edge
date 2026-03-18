# Research Pipelines

This directory contains research-facing CLI entrypoints, stage scripts, and adapter code used by `run_all`.

## Ownership Rules

- orchestration and CLI wiring can live here
- reusable workflow logic should live in `project/research/services/`
- parser construction and `argv -> config` translation should live in `project/pipelines/research/cli/`
- thin entrypoint wrappers are acceptable when they only adapt args and stage metadata

## Important Entry Points

- `phase2_candidate_discovery.py`: phase-2 discovery entrypoint
- `promote_candidates.py`: promotion entrypoint
- `phase2_search_engine.py`: canonical search-backed discovery stage
- `bridge_evaluate_phase2.py`: bridge validation stage
- `export_edge_candidates.py`: normalized edge export stage
- `update_edge_registry.py`: registry update stage
- `update_campaign_memory.py`: memory update stage
- `analyze_events.py`: detector execution entrypoint for event-family runs
- `build_event_registry.py`: registry materialization from analyzer output
- `canonicalize_event_episodes.py`: event-to-episode normalization

## Canonical Event Discovery Chain

Current stage naming is:

- `analyze_events__{EVENT}_{tf}`
- `build_event_registry__{EVENT}_{tf}`
- `canonicalize_event_episodes__{EVENT}_{tf}`
- `phase2_conditional_hypotheses__{EVENT}_{tf}`
- `bridge_evaluate_phase2__{EVENT}_{tf}`

## Do Not Reintroduce

- service code importing CLI modules
- duplicated workflow implementations between `project/pipelines/research` and `project/research/services`
- removed compatibility layers such as `project.research.compat`
- implicit detector registration through package import side effects
- generic detector tasks loading bar features for detectors that actually require registry event streams
- CLI detector overrides being parsed but then ignored at execution time
- stale `build_features_v1` terminology in research docs or stage references
