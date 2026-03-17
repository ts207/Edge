from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.events.detectors.registry import get_detector, list_registered_event_types, load_all_detectors
from project.spec_registry import load_yaml_path


def test_runtime_detector_registry_matches_detector_ownership_registry() -> None:
    load_all_detectors()
    registry_path = Path("project/configs/registries/detectors.yaml")
    ownership = load_yaml_path(registry_path).get("detector_ownership", {})

    registered = set(list_registered_event_types())
    owned = {str(event_type).strip().upper() for event_type in ownership}

    assert owned == registered


def test_sequence_alias_detector_is_instantiable_from_registry() -> None:
    load_all_detectors()
    detector = get_detector("SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE")

    assert detector is not None

    stream = pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "event_type": ["OI_SPIKE_POSITIVE", "VOL_SPIKE"],
            "signal_ts": pd.to_datetime(
                ["2024-01-01 10:00:00+00:00", "2024-01-01 10:20:00+00:00"],
                utc=True,
            ),
        }
    )

    result = detector.detect(stream, symbol="BTCUSDT")

    assert len(result) == 1
    assert result.iloc[0]["sequence_name"] == "SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE"
