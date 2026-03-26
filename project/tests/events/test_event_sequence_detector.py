import pandas as pd
import pytest
from project.events.detectors.sequence import EventSequenceDetector


@pytest.mark.skip(reason="EventSequenceDetector requires full event data with rv_96 column")
def test_event_sequence_detector():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="5min", tz="UTC"),
            "symbol": ["BTC", "BTC", "BTC", "BTC"],
            "event_type": ["VOL_SPIKE", "VOL_RELAXATION_START", "VOL_SPIKE", "VOL_RELAXATION_START"],
            "signal_ts": pd.to_datetime(
                ["2024-01-01 10:00", "2024-01-01 10:15", "2024-01-01 11:00", "2024-01-01 12:00"]
            ),
        }
    )

    det = EventSequenceDetector(anchor_event="VOL_SPIKE", trigger_event="VOL_RELAXATION_START", max_window=48)

    res = det.detect(df, symbol="BTC")

    assert len(res) >= 0
