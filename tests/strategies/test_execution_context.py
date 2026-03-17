from __future__ import annotations

import pandas as pd
import pytest

from project.strategies.dsl_runtime.execution_context import build_signal_frame


def test_build_signal_frame_requires_canonical_funding_rate_scaled() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True),
            "close": [100.0],
            "volume": [5.0],
            "funding_rate": [0.0001],
        }
    )

    with pytest.raises(ValueError, match="funding_rate_scaled"):
        build_signal_frame(frame)
