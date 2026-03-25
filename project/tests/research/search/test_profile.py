from __future__ import annotations

from project.research.search.profile import resolve_search_profile


def test_resolve_search_profile_synthetic_overrides_defaults():
    resolved = resolve_search_profile(
        discovery_profile="synthetic",
        search_spec="spec/search_space.yaml",
        min_n=30,
        min_t_stat=1.5,
    )
    assert resolved["search_spec"] == "synthetic_truth"
    assert resolved["min_n"] == 8
    assert resolved["min_t_stat"] == 0.25


def test_resolve_search_profile_preserves_custom_search_spec():
    resolved = resolve_search_profile(
        discovery_profile="synthetic",
        search_spec="custom_spec",
        min_n=12,
        min_t_stat=0.75,
    )
    assert resolved["search_spec"] == "custom_spec"
    assert resolved["min_n"] == 12
    assert resolved["min_t_stat"] == 0.75
