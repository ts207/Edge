from __future__ import annotations

import pytest
from project.events import config

def test_operator_registry_has_all_family_templates():
    # Clear production caches before test
    config.bootstrap_event_registry()
    
    # Use the public compose_config which internally validates against the operator registry
    # We'll get all event types from the unified registry
    registry = config._unified_registry()
    events = registry.get("events", {})
    assert events
    
    for event_type in events:
        # compose_config will raise ValueError if any template is incompatible with the family
        # or KeyError if the event_type is missing (though we just got it from the registry)
        cfg = config.compose_config(event_type)
        assert cfg
        assert cfg.event_type.upper() == event_type.upper()

def test_operator_registry_rejects_incompatible_family(monkeypatch):
    operators = {
        "desync_repair": {
            "operator_id": "op.desync_repair",
            "operator_version": "v1",
            "compatible_families": ["INFORMATION_DESYNC"],
        }
    }
    
    # Clear production caches
    config.bootstrap_event_registry()
    
    # Mock _operator_registry to use our test operators
    monkeypatch.setattr(config, "_operator_registry", lambda: operators)
    
    # Mock unified registry to have a test event with this template
    mock_registry = {
        "kind": "event_unified_registry",
        "events": {
            "TEST_LIQUIDITY": {
                "canonical_family": "LIQUIDITY_DISLOCATION",
                "templates": ["desync_repair"],
                "parameters": {}
            }
        }
    }
    monkeypatch.setattr(config, "_unified_registry", lambda: mock_registry)
    monkeypatch.setattr(config, "_registry", lambda: mock_registry)
    
    # Now clear caches that depend on registry or registry itself again 
    # (though they are now mocks, they might have old data cached)
    # Actually, we need to clear everything that can be cached.
    for funcname in ["_operator_registry", "_unified_registry", "_registry", "_family_by_event"]:
        func = getattr(config, funcname, None)
        if func and hasattr(func, "cache_clear"):
            func.cache_clear()
    
    with pytest.raises(ValueError, match="is incompatible with family"):
        config.compose_config("TEST_LIQUIDITY")
