# events_ontology

## Scope
- project/events/
- spec/events/
- spec/ontology/
- spec/states/
- spec/concepts/
- docs/generated/detector_coverage*
- docs/generated/ontology_audit*
- project/tests/events/
- project/tests/synthetic_truth/

## Summary
Runtime event identity comes from spec/events/event_registry_unified.yaml compiled through project/domain/registry_loader.py and surfaced in project/events/event_specs.py. Detector registration also pulls from dynamic family loaders such as project/events/families/interaction.py. State materialization is hardcoded in project/specs/ontology.py and only audited afterward.

## Findings
### Alias event ids bypass canonicalization in ontology deconfliction
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/events/ontology_deconfliction.py, project/events/event_aliases.py, project/research/services/regime_effectiveness_service.py, project/tests/events/test_ontology_deconfliction.py
- Evidence: attach_canonical_event_bundle() maps event_type directly into the bundle map and never calls resolve_event_alias(), so alias ids like VOL_REGIME_SHIFT or BASIS_DISLOCATION do not collapse with canonical ids.
- Why it matters: Equivalent events can survive as separate canonical episodes, corrupting regime routing and episode aggregation.
- Validation: Pass alias/canonical pairs through attach_canonical_event_bundle() and deconflict_event_episodes() and compare the output bundles.
- Remediation: Normalize through resolve_event_alias() before bundle lookup and add alias/canonical regression tests.

### ontology_audit.json is false-green: it reports no failures while every state source event is missing relative to the checked registry
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/scripts/ontology_consistency_audit.py, spec/events/canonical_event_registry.yaml, docs/generated/ontology_audit.json
- Evidence: ontology_consistency_audit compares state source events to spec/events/canonical_event_registry.yaml, which is only a five-entry legacy stub. The audit emits 70 missing source events but leaves failures empty and --check still passes.
- Why it matters: Operators can see a passing ontology audit when the same artifact proves state-to-event linkage is invalid against its claimed canonical source.
- Validation: Run project.scripts.ontology_consistency_audit --check and inspect failures plus states_with_missing_source_event.
- Remediation: Validate against the unified/compiled registry instead, or escalate non-empty states_with_missing_source_event into failures.

### Dead interaction-family specs are auto-registered as detectors outside the active ontology contract
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/events/families/interaction.py, project/spec_validation/loaders.py, spec/events/interaction/INT_LIQ_OI_CONFIRM.yaml, docs/generated/detector_coverage.md
- Evidence: interaction.py registers every ontology event whose id starts with INT_, even though those ids are absent from the active unified registry and ontology mapping. detector_coverage artifacts already report that drift.
- Why it matters: The detector registry exposes callable ids outside the authoritative ontology, creating inconsistent runtime universes depending on which registry surface code consults.
- Validation: Compare list_registered_event_types() with EVENT_REGISTRY_SPECS and the unified registry, paying attention to INT_* ids and CROSS_ASSET_INTERACTION.
- Remediation: Gate interaction registration on compiled-registry membership or promote the intended interaction ids into the authoritative registry/mapping.

### Generated ontology audits disagree on active-event count because one still relies on top-level per-event YAML presence
- Severity: medium
- Confidence: verified
- Category: docs_drift
- Affected: project/scripts/ontology_consistency_audit.py, docs/generated/ontology_audit.json, docs/generated/event_ontology_audit.json, spec/events/event_registry_unified.yaml
- Evidence: ontology_audit.json reports 69 active specs while event_ontology_audit.json and the compiled registry report 70, because ontology_consistency_audit only scans top-level spec/events/*.yaml and misses active events represented only in the unified registry.
- Why it matters: Repo inventory artifacts disagree about the live event universe, breaking audit comparability and governance trust.
- Validation: Compare both generated audits with len(get_domain_registry().event_ids) and inspect the missing top-level YAML for CROSS_ASSET_DESYNC_EVENT.
- Remediation: Derive both audits from the same unified runtime source or require a per-event YAML for every active event and fail when one is missing.
