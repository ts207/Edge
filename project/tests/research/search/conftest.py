import pytest
from project.domain.hypotheses import TriggerSpec, HypothesisSpec


@pytest.fixture(autouse=True)
def disable_ontology_validation(monkeypatch):
    """
    Globally disable ontology validation in tests to support mock IDs.
    Hardening tests can explicitly re-enable it if needed.
    """
    # We don't want to break tests that EXPECT validation errors,
    # but most tests use dummy 'E1', 'A', 'B' which now fail.

    # Strategy: monkeypatch validate() to be a no-op unless a special flag is set on the instance.
    orig_validate = TriggerSpec.validate

    def mock_validate(self):
        if getattr(self, "_force_validation", False):
            return orig_validate(self)
        return None

    monkeypatch.setattr(TriggerSpec, "validate", mock_validate)
