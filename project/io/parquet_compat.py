from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pandas as pd

try:  # pragma: no cover - optional dependency
    import pyarrow  # type: ignore  # noqa: F401
    _HAS_NATIVE_PARQUET = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_NATIVE_PARQUET = False


def _coerce_path(path: Any) -> Path:
    return Path(path)


def patch_pandas_parquet_fallback() -> None:
    """Patch pandas parquet helpers to use pickle storage when native parquet engines
    are not installed.

    This keeps existing code paths working in minimal environments while preserving
    the on-disk `.parquet` filename contract expected by the repository.
    """

    if _HAS_NATIVE_PARQUET:
        return

    if getattr(pd.DataFrame.to_parquet, "_edge_fallback_patched", False):
        return

    original_to_pickle = pd.DataFrame.to_pickle
    original_read_pickle = pd.read_pickle

    def _to_parquet_fallback(self: pd.DataFrame, path, *args, **kwargs):
        target = _coerce_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Preserve the requested filename contract; write pickle bytes to the path.
        return original_to_pickle(self, target, *args, **kwargs)

    def _read_parquet_fallback(path, columns=None, *args, **kwargs):
        target = _coerce_path(path)
        frame = original_read_pickle(target, *args, **kwargs)
        if columns is not None:
            cols = [c for c in columns if c in frame.columns]
            frame = frame.loc[:, cols]
        return frame

    _to_parquet_fallback._edge_fallback_patched = True  # type: ignore[attr-defined]
    _read_parquet_fallback._edge_fallback_patched = True  # type: ignore[attr-defined]

    pd.DataFrame.to_parquet = _to_parquet_fallback  # type: ignore[assignment]
    pd.read_parquet = _read_parquet_fallback  # type: ignore[assignment]

    # Keep module-level helpers aligned for callers that import them directly.
    try:  # pragma: no cover - optional import surface
        import pandas.io.parquet as pq_mod

        pq_mod.to_parquet = _to_parquet_fallback  # type: ignore[assignment]
        pq_mod.read_parquet = _read_parquet_fallback  # type: ignore[assignment]
    except Exception:
        pass
