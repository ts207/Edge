# Research Pipelines

This directory contains research-facing CLI entrypoints and stage scripts.

The current rule is simple:

- orchestration and CLI wiring can live here
- reusable workflow logic should live in `project/research/services/`
- stable helper APIs for tests/scripts should live in `project/research/compat/`
- parser construction and `argv -> config` translation should live in `project/pipelines/research/cli/`

## Important Entry Points

- `phase2_candidate_discovery.py`: thin wrapper over the Phase 2 CLI adapter
- `promote_candidates.py`: thin wrapper over the promotion CLI adapter
- `analyze_events.py`: canonical detector execution entrypoint for single-event family runs
- `generic_detector_task.py`: generic detector runner, including sequence-detector event-stream loading and CLI override parsing
- `cli/candidate_discovery_cli.py`: candidate discovery parser and `argv -> CandidateDiscoveryConfig`
- `cli/promotion_cli.py`: promotion parser and `argv -> PromotionConfig`
- `build_event_registry.py`: builds event registries from analyzer output
- `canonicalize_event_episodes.py`: merges event rows into episode-level artifacts
- `phase2_search_engine.py`: canonical search-backed discovery stage
- `bridge_evaluate_phase2.py`: bridge validation stage

## Naming

Current stage naming is:

- `analyze_events__{EVENT}_{tf}`
- `build_event_registry__{EVENT}_{tf}`
- `canonicalize_event_episodes__{EVENT}_{tf}`
- `phase2_conditional_hypotheses__{EVENT}_{tf}`
- `bridge_evaluate_phase2__{EVENT}_{tf}`

## Do Not Reintroduce

- service code importing CLI modules
- duplicated workflow implementations between `project/pipelines/research` and `project/research/services`
- tests or scripts importing helper logic from `project/pipelines/research/*` when a `project.research.compat.*` module exists
- implicit detector registration through package import side effects
- generic detector tasks loading bar features for detectors that actually require registry event streams
- CLI detector overrides being parsed but then ignored at execution time
- stale `build_features_v1` terminology in research docs or stage references
