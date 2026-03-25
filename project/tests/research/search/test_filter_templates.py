def test_get_event_family_known():
    from project.spec_validation.ontology import get_event_family

    assert get_event_family("SWEEP_STOPRUN") == "LIQUIDITY_DISLOCATION"
    assert get_event_family("SPOT_PERP_BASIS_SHOCK") == "INFORMATION_DESYNC"
    assert get_event_family("LIQUIDATION_CASCADE") == "POSITIONING_EXTREMES"


def test_get_event_family_unknown():
    from project.spec_validation.ontology import get_event_family

    assert get_event_family("NONEXISTENT_EVENT") is None


def test_resolve_filter_templates_liquidity_family():
    from project.spec_validation.search import resolve_filter_templates

    filters = resolve_filter_templates("LIQUIDITY_DISLOCATION")
    names = [f["name"] for f in filters]
    assert "only_if_liquidity" in names
    assert "slippage_aware_filter" in names
    for f in filters:
        assert "name" in f
        assert "feature" in f
        assert "operator" in f
        assert "threshold" in f


def test_resolve_filter_templates_execution_only_family():
    from project.spec_validation.search import resolve_filter_templates

    # TEMPORAL_STRUCTURE only has mean_reversion and continuation — no filter templates
    filters = resolve_filter_templates("TEMPORAL_STRUCTURE")
    assert filters == []


def test_resolve_filter_templates_information_desync():
    from project.spec_validation.search import resolve_filter_templates

    filters = resolve_filter_templates("INFORMATION_DESYNC")
    names = [f["name"] for f in filters]
    assert "desync_repair" in names
    assert "basis_repair" in names
