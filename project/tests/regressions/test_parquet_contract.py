from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.io import parquet_compat
from project.io import utils as io_utils


def test_pandas_to_parquet_fallback_preserves_parquet_path(tmp_path: Path, monkeypatch) -> None:
    original_to_parquet = pd.DataFrame.to_parquet
    original_read_parquet = pd.read_parquet
    monkeypatch.setattr(parquet_compat, "_HAS_NATIVE_PARQUET", False)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", original_to_parquet)
    monkeypatch.setattr(pd, "read_parquet", original_read_parquet)
    parquet_compat.patch_pandas_parquet_fallback()

    path = tmp_path / "frame.parquet"
    frame = pd.DataFrame({"a": [1], "b": [2]})

    frame.to_parquet(path, index=False, engine="pyarrow", compression="snappy")

    assert path.exists()
    restored = parquet_compat.read_parquet_compat(path, columns=["b"])
    assert restored.to_dict(orient="list") == {"b": [2]}


def test_write_parquet_returns_requested_path_under_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(io_utils, "HAS_PYARROW", False)
    path = tmp_path / "artifact.parquet"

    actual, storage = io_utils.write_parquet(pd.DataFrame({"a": [1, 2]}), path)

    assert storage == "parquet"
    assert actual == path
    assert path.exists()


def test_read_parquet_supports_columns_under_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(io_utils, "HAS_PYARROW", False)
    path = tmp_path / "subset.parquet"
    io_utils.write_parquet(pd.DataFrame({"a": [1], "b": [2], "c": [3]}), path)

    restored = io_utils.read_parquet(path, columns=["b", "missing"])

    assert list(restored.columns) == ["b"]
    assert restored.iloc[0]["b"] == 2


def test_read_parquet_loads_legacy_csv_compatibility_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy.csv"
    pd.DataFrame({"a": [1], "b": [2]}).to_csv(csv_path, index=False)

    restored = io_utils.read_parquet(tmp_path / "legacy.parquet", columns=["a"])

    assert restored.to_dict(orient="list") == {"a": [1]}
