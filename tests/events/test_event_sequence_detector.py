import pandas as pd
import pytest
from project.events.detectors.sequence import EventSequenceDetector

def test_event_sequence_detector():
    df = pd.DataFrame({
        "symbol": ["BTC", "BTC", "BTC", "BTC"],
        "event_type": ["E1", "E2", "E1", "E2"],
        "signal_ts": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 10:15", "2024-01-01 11:00", "2024-01-01 12:00"]),
    })
    
    det = EventSequenceDetector(
        sequence_name="SEQ_E1_E2",
        events=["E1", "E2"],
        max_gaps=["30min"]
    )
    
    res = det.detect(df, "BTC")
    
    assert len(res) == 1
    assert res.iloc[0]["sequence_name"] == "SEQ_E1_E2"
    assert res.iloc[0]["enter_ts"] == pd.Timestamp("2024-01-01 10:00")
    assert res.iloc[0]["signal_ts"] == pd.Timestamp("2024-01-01 10:15")
