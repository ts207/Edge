# Research Pipelines

This directory contains research-facing CLI entrypoints, stage scripts, and adapter code used by `run_all`.

## Ownership Rules

- orchestration and CLI wiring can live here
- reusable workflow logic should live in `project/research/services/`
- parser construction and `argv -> config` translation should live in `project/research/cli/`
- thin entrypoint wrappers are acceptable only for compatibility or replay, not as active planner targets

## Important Entry Points

- `phase2_candidate_discovery.py`: compatibility wrapper for the canonical discovery CLI in `project/research/cli/candidate_discovery_cli.py`
- `promote_candidates.py`: compatibility wrapper for the canonical promotion CLI in `project/research/cli/promotion_cli.py`
- `phase2_search_engine.py`: compatibility wrapper for the canonical search-backed discovery stage in `project/research/phase2_search_engine.py`
- `bridge_evaluate_phase2.py`: compatibility wrapper for the canonical bridge validation stage in `project/research/bridge_evaluate_phase2.py`
- `export_edge_candidates.py`: compatibility wrapper for the canonical normalized edge export stage in `project/research/export_edge_candidates.py`
- `update_edge_registry.py`: compatibility wrapper for `project/research/update_edge_registry.py`
- `update_campaign_memory.py`: compatibility wrapper for `project/research/update_campaign_memory.py`
- `analyze_events.py`: compatibility wrapper for `project/research/analyze_events.py`
- `build_event_registry.py`: compatibility wrapper for `project/research/build_event_registry.py`
- `canonicalize_event_episodes.py`: compatibility wrapper for `project/research/canonicalize_event_episodes.py`

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
