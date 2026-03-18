from __future__ import annotations

from pathlib import Path

from project.specs.utils import get_spec_hashes


def test_get_spec_hashes_uses_canonical_registry_paths():
    hashes = get_spec_hashes(Path(__file__).resolve().parents[2])
    assert isinstance(hashes, dict)
    assert "gates.yaml" in hashes
    assert all(".yaml" in k for k in hashes)
