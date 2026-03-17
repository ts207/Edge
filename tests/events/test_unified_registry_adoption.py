from __future__ import annotations

from pathlib import Path

from project.events.config import compose_event_config
from project.events.config import compose_template_config

def test_event_and_template_composers_use_unified_registry():
    event_cfg = compose_event_config("LIQUIDATION_CASCADE")
    template_cfg = compose_template_config("LIQUIDITY_SHOCK")

    unified_path = (
        Path(__file__).resolve().parents[2]
        / "spec"
        / "events"
        / "event_registry_unified.yaml"
    ).resolve()

    assert Path(event_cfg.source_layers["unified_registry"]).resolve() == unified_path
    assert Path(template_cfg.source_layers["registry"]).resolve() == unified_path
