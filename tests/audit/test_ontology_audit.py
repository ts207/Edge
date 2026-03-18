from pathlib import Path
from project.scripts.ontology_consistency_audit import run_audit


def test_ontology_audit_has_no_unregistered_materialized_states():
    """TICKET-017: all materialized state IDs must be present in state_registry.yaml."""
    report = run_audit(Path('.'))
    unregistered = report['states']['materialized_not_in_registry']
    assert not unregistered, (
        f"Found {len(unregistered)} materialized states missing from registry: {unregistered}"
    )


def test_ontology_audit_has_no_dead_registry_entries():
    """TICKET-017: every state_registry.yaml entry must correspond to a materialized state."""
    report = run_audit(Path('.'))
    not_materialized = report['states']['state_registry_not_materialized']
    assert not not_materialized, (
        f"Found {len(not_materialized)} registry entries never materialized: {not_materialized}"
    )
