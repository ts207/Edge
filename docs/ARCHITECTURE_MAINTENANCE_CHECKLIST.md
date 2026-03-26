# Architecture Maintenance Checklist

This checklist should be reviewed before merging architectural changes.

## Pre-Merge Checklist

### Contracts and Generated Docs
- [ ] Run `make generate-contracts` if adding new contract definitions
- [ ] Verify generated contract files are up to date
- [ ] Update `docs/ARCHITECTURE_SURFACE_INVENTORY.md` if adding new surfaces

### Research Services and Wrappers
- [ ] New research services must follow the `project.research.services` pattern
- [ ] Wrapper modules in `project/research/compat/` must be pure re-exports
- [ ] Verify no circular dependencies in research module

### Strategy Surfaces
- [ ] Strategy DSL changes must maintain backward compatibility
- [ ] New strategy primitives must be documented in `docs/03_COMPONENT_REFERENCE.md`
- [ ] Strategy templates must follow naming conventions

### Metrics and Guardrails
- [ ] Module coupling count must not increase beyond threshold
- [ ] Cross-boundary imports must not increase beyond threshold
- [ ] Circular dependencies must remain at 0 or be resolved
- [ ] Test coverage ratio must remain above minimum threshold

## Post-Merge Checklist
- [ ] Run full test suite: `pytest project/tests/`
- [ ] Run architectural tests: `pytest project/tests/test_architectural_integrity.py`
- [ ] Verify no new warnings in pipeline stages
