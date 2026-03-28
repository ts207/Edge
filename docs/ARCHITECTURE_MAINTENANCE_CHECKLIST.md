# Architecture Maintenance Checklist

Use this checklist after structural changes to pipeline, ontology, routing, or package layout.

## 1. Structural Validation

```bash
python -m compileall -q project project/tests
python -m project.spec_validation.cli
```

## 2. Generated Inventory Drift

```bash
python project/scripts/detector_coverage_audit.py \
  --md-out docs/generated/detector_coverage.md \
  --json-out docs/generated/detector_coverage.json --check

python project/scripts/ontology_consistency_audit.py \
  --output docs/generated/ontology_audit.json --check

python project/scripts/build_system_map.py --check
python project/scripts/build_architecture_metrics.py --check
```

## 3. Event Ontology and Routing

```bash
python project/scripts/build_event_ontology_artifacts.py
python project/scripts/event_ontology_audit.py
python project/scripts/regime_routing_audit.py
```

Refresh these any time canonical mapping, routing, context tags, composite events, or strategy constructs change.

## 4. Workflow Integrity

```bash
python -m project.reliability.cli_smoke --mode full --root /tmp/edge-smoke
python project/scripts/run_golden_regression.py --run_id smoke_run
python project/scripts/run_golden_workflow.py
```

## 5. CI-Equivalent Local Gate

```bash
make minimum-green-gate
```

## 6. Documentation Refresh Rules

After structural changes:

- update hand-authored docs under `docs/`
- do not hand-edit `docs/generated/`
- point narrative docs at generated inventory surfaces instead of duplicating counts
- confirm command examples still exist in code and `Makefile`

## 7. Common Misses

Check explicitly for:

- stale package maps
- stale stage-family names
- stale CLI examples
- stale ontology terminology
- stale CI descriptions
- prose that references files that no longer exist
