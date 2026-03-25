"""Smoke tests for phase2_search_engine pipeline stage."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))


def test_stage_is_importable():
    import project.research.phase2_search_engine as stage

    assert stage is not None


def test_stage_has_main():
    import project.research.phase2_search_engine as stage

    assert callable(stage.main)


def test_stage_exits_zero_with_empty_features(tmp_path):
    """Stage should handle empty feature DataFrame gracefully."""
    import project.research.phase2_search_engine as stage

    empty_features = pd.DataFrame()
    with patch(
        "project.research.phase2_search_engine.load_features", return_value=empty_features
    ):
        result = stage.run(
            run_id="test_run",
            symbols="BTCUSDT",
            data_root=tmp_path,
            out_dir=tmp_path / "output",
        )
    assert result == 0


def test_stage_writes_output_parquet(tmp_path):
    """Stage should write a parquet file even when no candidates pass gates."""
    import project.research.phase2_search_engine as stage
    import numpy as np

    n = 100
    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="15min"),
            "close": np.random.uniform(40000, 50000, n),
            "event_vol_spike": np.zeros(n, dtype=bool),
        }
    )

    with (
        patch(
            "project.research.phase2_search_engine.load_features", return_value=features
        ),
        patch("project.events.event_flags.load_registry_flags", return_value=pd.DataFrame()),
        patch(
            "project.research.phase2_search_engine.generate_hypotheses_with_audit",
            return_value=(
                [],
                {
                    "counts": {"generated": 0, "feasible": 0, "rejected": 0},
                    "rejection_reason_counts": {},
                },
            ),
        ),
        patch(
            "project.research.phase2_search_engine.run_distributed_search",
            return_value=pd.DataFrame(),
        ),
    ):
        stage.run(
            run_id="test_run",
            symbols="BTCUSDT",
            data_root=tmp_path,
            out_dir=tmp_path / "output",
        )

    output_file = tmp_path / "output" / "phase2_candidates.parquet"
    assert output_file.exists()
    diagnostics = json.loads(
        (tmp_path / "output" / "phase2_diagnostics.json").read_text(encoding="utf-8")
    )
    assert diagnostics["hypotheses_generated"] == 0
    assert diagnostics["feasible_hypotheses"] == 0
    assert diagnostics["rejected_hypotheses"] == 0
    assert diagnostics["feature_rows"] == len(features)
    assert (
        tmp_path / "output" / "hypotheses" / "BTCUSDT" / "generated_hypotheses.parquet"
    ).exists()
    assert (
        tmp_path / "output" / "hypotheses" / "BTCUSDT" / "evaluated_hypotheses.parquet"
    ).exists()
    assert (tmp_path / "output" / "hypotheses" / "BTCUSDT" / "gate_failures.parquet").exists()


def test_stage_normalizes_nested_audit_columns_before_parquet(tmp_path):
    import project.research.phase2_search_engine as stage
    import numpy as np

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=16, freq="15min"),
            "close": np.random.uniform(40000, 50000, 16),
        }
    )

    with (
        patch(
            "project.research.phase2_search_engine.load_features", return_value=features
        ),
        patch("project.events.event_flags.load_registry_flags", return_value=pd.DataFrame()),
        patch(
            "project.research.phase2_search_engine.generate_hypotheses_with_audit",
            return_value=(
                [],
                {
                    "generated_rows": [
                        {"hypothesis_id": "h1", "context": {}, "rejection_details": {}}
                    ],
                    "feasible_rows": [
                        {"hypothesis_id": "h1", "context": {"state_filter": "HIGH_VOL"}}
                    ],
                    "rejected_rows": [
                        {
                            "hypothesis_id": "h2",
                            "rejection_reasons": ["validation_error"],
                            "rejection_details": {},
                        }
                    ],
                    "counts": {"generated": 1, "feasible": 1, "rejected": 1},
                    "rejection_reason_counts": {"validation_error": 1},
                },
            ),
        ),
        patch(
            "project.research.phase2_search_engine.run_distributed_search",
            return_value=pd.DataFrame(),
        ),
    ):
        rc = stage.run(
            run_id="test_run",
            symbols="BTCUSDT",
            data_root=tmp_path,
            out_dir=tmp_path / "output",
        )

    assert rc == 0
    generated = pd.read_parquet(
        tmp_path / "output" / "hypotheses" / "BTCUSDT" / "generated_hypotheses.parquet"
    )
    assert generated.loc[0, "context"] == "{}"


def test_search_engine_normalizes_market_context_state_aliases():
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="5min", tz="UTC"),
            "carry_state_code": [-1.0, 1.0, 0.0],
            "chop_regime": [1.0, 0.0, 0.0],
            "bull_trend_regime": [0.0, 1.0, 0.0],
            "bear_trend_regime": [0.0, 0.0, 1.0],
            "compression_state_flag": [0.0, 1.0, 0.0],
            "high_vol_regime": [1.0, 0.0, 0.0],
        }
    )

    out = stage._normalize_search_feature_columns(features)

    assert "funding_positive" in out.columns
    assert "funding_negative" in out.columns
    assert out["funding_negative"].tolist() == [1.0, 0.0, 0.0]
    assert out["funding_positive"].tolist() == [0.0, 1.0, 0.0]
    assert out["chop_state"].tolist() == [1.0, 0.0, 0.0]
    assert out["trending_state"].tolist() == [0.0, 1.0, 1.0]
    assert out["compression_state"].tolist() == [0.0, 1.0, 0.0]
    assert out["high_vol_regime"].tolist() == [1.0, 0.0, 0.0]


def test_search_engine_applies_multiplicity(tmp_path, monkeypatch):
    """Search engine stage must apply multiplicity controls when candidates exist."""
    import pandas as pd
    import numpy as np

    dates = pd.date_range("2023-01-01", periods=200, freq="15min")
    features = pd.DataFrame(
        {
            "timestamp": dates,
            "close": np.linspace(100, 110, 200) + np.random.default_rng(42).normal(0, 0.1, 200),
            "event_vol_spike": [i % 10 == 0 for i in range(200)],
        }
    )

    # Monkeypatch generate_hypotheses to return small set
    from project.domain.hypotheses import HypothesisSpec, TriggerSpec

    def mock_generate(*a, **kw):
        hypotheses = [
            HypothesisSpec(
                trigger=TriggerSpec.event("vol_spike"),
                direction="long",
                horizon="5m",
                template_id="continuation",
                entry_lag=1,
            ),
        ]
        return hypotheses, {
            "generated_rows": [{"hypothesis_id": hypotheses[0].hypothesis_id()}],
            "feasible_rows": [{"hypothesis_id": hypotheses[0].hypothesis_id()}],
            "rejected_rows": [],
            "counts": {"generated": 1, "feasible": 1, "rejected": 0},
            "rejection_reason_counts": {},
        }

    monkeypatch.setattr(
        "project.research.phase2_search_engine.generate_hypotheses_with_audit",
        mock_generate,
    )
    monkeypatch.setattr(
        "project.research.phase2_search_engine.load_features", lambda *a, **kw: features
    )
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )

    from project.research.phase2_search_engine import run

    out_dir = tmp_path / "output"
    rc = run("test_run", "BTCUSDT", tmp_path, out_dir)
    assert rc == 0

    result = pd.read_parquet(out_dir / "phase2_candidates.parquet")
    diagnostics = json.loads((out_dir / "phase2_diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["hypotheses_generated"] == 1
    assert diagnostics["feasible_hypotheses"] == 1
    assert "bridge_candidates_rows" in diagnostics
    if not result.empty:
        assert "gate_multiplicity" in result.columns
        assert "p_value" in result.columns
        assert "family_id" in result.columns


def test_search_engine_synthetic_profile_resolves_search_spec_and_min_n(tmp_path, monkeypatch):
    import pandas as pd
    import numpy as np
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=40, freq="5min", tz="UTC"),
            "close": np.linspace(100, 101, 40),
        }
    )
    captured = {}

    def _mock_generate(spec_name, **kwargs):
        captured["search_spec"] = spec_name
        return [], {
            "counts": {"generated": 0, "feasible": 0, "rejected": 0},
            "rejection_reason_counts": {},
        }

    monkeypatch.setattr(stage, "load_features", lambda *a, **kw: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(stage, "generate_hypotheses_with_audit", _mock_generate)

    rc = stage.run(
        run_id="synthetic_profile_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
        discovery_profile="synthetic",
        search_spec="spec/search_space.yaml",
        min_n=30,
        min_t_stat=1.5,
    )
    assert rc == 0
    assert captured["search_spec"] == "synthetic_truth"
    diagnostics = json.loads(
        (tmp_path / "output" / "phase2_diagnostics.json").read_text(encoding="utf-8")
    )
    assert diagnostics["discovery_profile"] == "synthetic"
    assert diagnostics["min_n"] == 8
    assert diagnostics["min_t_stat"] == 0.25


def test_search_engine_passes_search_budget_to_generator(tmp_path, monkeypatch):
    import pandas as pd
    import numpy as np
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=24, freq="5min", tz="UTC"),
            "close": np.linspace(100, 101, 24),
        }
    )
    captured: dict[str, object] = {}

    def _mock_generate(spec_name, **kwargs):
        captured["search_spec"] = spec_name
        captured["max_hypotheses"] = kwargs.get("max_hypotheses")
        return [], {
            "counts": {"generated": 0, "feasible": 0, "rejected": 0},
            "rejection_reason_counts": {},
        }

    monkeypatch.setattr(stage, "load_features", lambda *a, **kw: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(stage, "generate_hypotheses_with_audit", _mock_generate)

    rc = stage.run(
        run_id="search_budget_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
        search_budget=12,
    )

    assert rc == 0
    assert captured["search_spec"] == "full"
    assert captured["max_hypotheses"] == 12
    diagnostics = json.loads(
        (tmp_path / "output" / "phase2_diagnostics.json").read_text(encoding="utf-8")
    )
    assert diagnostics["search_budget"] == 12


def test_search_engine_run_uses_explicit_registry_root(tmp_path, monkeypatch):
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=12, freq="5min", tz="UTC"),
            "close": [100.0 + i for i in range(12)],
        }
    )
    captured: dict[str, object] = {}

    def _mock_build_experiment_plan(config_path, registry_root, out_dir=None):
        captured["config_path"] = Path(config_path)
        captured["registry_root"] = Path(registry_root)
        return type("Plan", (), {"hypotheses": [], "program_id": "prog"})()

    monkeypatch.setattr(stage, "load_features", lambda *a, **kw: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(
        stage,
        "generate_hypotheses_with_audit",
        lambda *a, **kw: (
            [],
            {
                "counts": {"generated": 0, "feasible": 0, "rejected": 0},
                "rejection_reason_counts": {},
            },
        ),
    )
    monkeypatch.setattr(stage, "run_distributed_search", lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(
        "project.research.experiment_engine.build_experiment_plan",
        _mock_build_experiment_plan,
    )

    rc = stage.run(
        run_id="registry_root_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
        experiment_config=str(tmp_path / "experiment.yaml"),
        registry_root=tmp_path / "registries",
    )

    assert rc == 0
    assert captured["config_path"] == tmp_path / "experiment.yaml"
    assert captured["registry_root"] == tmp_path / "registries"


def test_search_engine_passes_timeframe_and_data_root_to_feature_loader(tmp_path, monkeypatch):
    import project.research.phase2_search_engine as stage

    captured: dict[str, object] = {}
    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=8, freq="15min", tz="UTC"),
            "close": range(8),
        }
    )

    def _mock_load_features(run_id, symbol, timeframe="5m", data_root=None, **kwargs):
        captured["run_id"] = run_id
        captured["symbol"] = symbol
        captured["timeframe"] = timeframe
        captured["data_root"] = data_root
        return features

    monkeypatch.setattr(stage, "load_features", _mock_load_features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(
        stage,
        "generate_hypotheses_with_audit",
        lambda *a, **kw: (
            [],
            {
                "counts": {"generated": 0, "feasible": 0, "rejected": 0},
                "rejection_reason_counts": {},
            },
        ),
    )

    rc = stage.run(
        run_id="timeframe_root_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
        timeframe="15m",
    )

    assert rc == 0
    assert captured["run_id"] == "timeframe_root_run"
    assert captured["symbol"] == "BTCUSDT"
    assert captured["timeframe"] == "15m"
    assert captured["data_root"] == tmp_path
    diagnostics = json.loads(
        (tmp_path / "output" / "phase2_diagnostics.json").read_text(encoding="utf-8")
    )
    assert diagnostics["timeframe"] == "15m"


def test_search_engine_passes_merged_features_to_generation_feasibility(tmp_path, monkeypatch):
    import project.research.phase2_search_engine as stage

    captured: dict[str, object] = {}
    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=8, freq="5min", tz="UTC"),
            "close": range(8),
            "event_vol_shock": [False, True, False, False, True, False, False, False],
        }
    )

    def _mock_generate(spec_name, **kwargs):
        captured["search_spec"] = spec_name
        captured["features_columns"] = list(kwargs["features"].columns)
        return [], {
            "counts": {"generated": 0, "feasible": 0, "rejected": 0},
            "rejection_reason_counts": {},
        }

    monkeypatch.setattr(stage, "load_features", lambda *a, **kw: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(stage, "generate_hypotheses_with_audit", _mock_generate)

    rc = stage.run(
        run_id="generation_feasibility_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
    )

    assert rc == 0
    assert captured["search_spec"] == "full"
    assert "event_vol_shock" in captured["features_columns"]


def test_search_engine_aggregates_multi_symbol_candidates_and_diagnostics(tmp_path, monkeypatch):
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=12, freq="5min", tz="UTC"),
            "close": [100.0 + i for i in range(12)],
        }
    )

    monkeypatch.setattr(stage, "load_features", lambda run_id, symbol, **kwargs: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(
        stage,
        "generate_hypotheses_with_audit",
        lambda *a, **kw: (
            ["h1"],
            {
                "counts": {"generated": 1, "feasible": 1, "rejected": 0},
                "rejection_reason_counts": {},
            },
        ),
    )
    monkeypatch.setattr(
        stage,
        "run_distributed_search",
        lambda *a, **kw: pd.DataFrame(
            {
                "valid": [True],
                "n": [20],
                "t_stat": [2.0],
                "p_value": [0.01],
                "family_id": ["f1"],
            }
        ),
    )
    monkeypatch.setattr(
        stage,
        "hypotheses_to_bridge_candidates",
        lambda *a, **kw: pd.DataFrame(
            {
                "candidate_id": ["c1"],
                "family_id": ["f1"],
                "p_value": [0.01],
                "is_discovery": [True],
            }
        ),
    )

    rc = stage.run(
        run_id="multi_symbol_run",
        symbols="BTCUSDT,ETHUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
    )

    assert rc == 0
    result = pd.read_parquet(tmp_path / "output" / "phase2_candidates.parquet")
    diagnostics = json.loads(
        (tmp_path / "output" / "phase2_diagnostics.json").read_text(encoding="utf-8")
    )
    assert set(result["symbol"].astype(str)) == {"BTCUSDT", "ETHUSDT"}
    assert diagnostics["symbols_requested"] == ["BTCUSDT", "ETHUSDT"]
    assert diagnostics["primary_symbol"] == ""
    assert len(diagnostics["symbol_diagnostics"]) == 2
    assert diagnostics["feasible_hypotheses"] == 2


def test_search_engine_assigns_split_labels_before_evaluation(tmp_path, monkeypatch):
    import project.research.phase2_search_engine as stage

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=24, freq="5min", tz="UTC"),
            "close": [100.0 + i for i in range(24)],
            "event_vol_shock": [i % 3 == 0 for i in range(24)],
        }
    )
    captured: dict[str, object] = {}

    def _mock_run_distributed_search(hypotheses, features, **kwargs):
        captured["split_labels"] = sorted(set(features["split_label"].astype(str)))
        return pd.DataFrame(
            {
                "hypothesis_id": ["h1"],
                "trigger_type": ["event"],
                "trigger_key": ["event:VOL_SHOCK"],
                "direction": ["long"],
                "horizon": ["5m"],
                "template_id": ["base"],
                "n": [24],
                "train_n_obs": [14],
                "validation_n_obs": [5],
                "test_n_obs": [5],
                "validation_samples": [5],
                "test_samples": [5],
                "mean_return_bps": [10.0],
                "t_stat": [2.5],
                "sharpe": [1.0],
                "hit_rate": [0.6],
                "cost_adjusted_return_bps": [8.0],
                "mae_mean_bps": [-1.0],
                "mfe_mean_bps": [2.0],
                "robustness_score": [0.8],
                "stress_score": [0.8],
                "kill_switch_count": [0],
                "capacity_proxy": [1.0],
                "valid": [True],
                "invalid_reason": [None],
            }
        )

    monkeypatch.setattr(stage, "load_features", lambda *a, **kw: features)
    monkeypatch.setattr(
        "project.events.event_flags.load_registry_flags", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(
        stage,
        "generate_hypotheses_with_audit",
        lambda *a, **kw: (
            ["h1"],
            {
                "counts": {"generated": 1, "feasible": 1, "rejected": 0},
                "rejection_reason_counts": {},
            },
        ),
    )
    monkeypatch.setattr(stage, "run_distributed_search", _mock_run_distributed_search)

    rc = stage.run(
        run_id="split_label_run",
        symbols="BTCUSDT",
        data_root=tmp_path,
        out_dir=tmp_path / "output",
    )

    assert rc == 0
    assert captured["split_labels"] == ["test", "train", "validation"]
