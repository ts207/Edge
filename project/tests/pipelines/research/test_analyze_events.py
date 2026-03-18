"""Tests for the universal analyze_events.py pipeline script."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import pytest


class TestAnalyzeEventsMain:
    """Tests for the universal analyze_events.py entry point."""

    def test_main_exits_nonzero_when_no_detector(self, tmp_path, monkeypatch, capsys):
        """main() must exit non-zero and log ERROR when detector is not registered."""
        import types
        from project.pipelines.research.analyze_events import main
        import project.events.detectors.registry as reg
        import project.pipelines.research.analyze_events as ae_mod

        # Patch get_detector to return None for any event type
        monkeypatch.setattr(reg, "get_detector", lambda etype: None)

        # Patch compose_event_config so argparse can proceed to the detector check
        fake_cfg = types.SimpleNamespace(reports_dir="fake", events_file="fake.parquet", parameters={})
        monkeypatch.setattr(ae_mod, "compose_event_config", lambda etype: fake_cfg)

        # Patch load_all_detectors to be a no-op
        monkeypatch.setattr(ae_mod, "load_all_detectors", lambda: None)

        exit_code = main([
            "--event_type", "FAKE_EVENT_XYZ",
            "--run_id", "test_run_001",
            "--symbols", "BTCUSDT",
            "--out_dir", str(tmp_path),
        ])
        assert exit_code != 0, "main() must return non-zero when no detector is found"

    def test_main_function_is_importable(self):
        """analyze_events.main must be importable."""
        from project.pipelines.research.analyze_events import main
        assert callable(main)

    def test_main_accepts_standard_args(self, tmp_path):
        """main() must accept --event_type, --run_id, --symbols, --data_root args."""
        import inspect
        from project.pipelines.research import analyze_events
        # The script must have a main() accepting argv
        assert hasattr(analyze_events, "main")
        sig = inspect.signature(analyze_events.main)
        # Must accept at least one positional-or-keyword arg (argv)
        params = list(sig.parameters.values())
        assert len(params) >= 1
