from __future__ import annotations

from scripts.baseline._common import build_baseline


def test_build_baseline_creates_metadata_and_manifests():
    result = build_baseline(strict=False)
    assert "metadata" in result
    assert "events" in result
    assert "analyzers" in result
