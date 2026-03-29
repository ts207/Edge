from __future__ import annotations

import pandas as pd

from project.research.validation.falsification import generate_placebo_events


def test_generate_placebo_events_shifts_by_time_offset_not_previous_row():
    timestamps = pd.date_range("2024-01-01", periods=4, freq="5min", tz="UTC")
    events = pd.DataFrame(
        {
            "enter_ts": timestamps,
            "timestamp": timestamps,
            "event_id": ["e1", "e2", "e3", "e4"],
        }
    )

    out = generate_placebo_events(events, time_col="enter_ts", shift_bars=1)

    expected = timestamps + pd.Timedelta(minutes=5)
    assert list(out["enter_ts"]) == list(expected)
    assert list(out["timestamp"]) == list(expected)
    assert out.loc[1, "enter_ts"] != events.loc[0, "enter_ts"]
