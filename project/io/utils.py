from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import pandas as pd

try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    HAS_PYARROW = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_PYARROW = False

def ensure_dir(path: Path) -> None:
    """
    Ensure a directory exists.
    """
    path.mkdir(parents=True, exist_ok=True)

def run_scoped_lake_path(data_root: Path, run_id: str, *parts: str) -> Path:
    """
    Build a run-scoped lake path under ``data/lake/runs/<run_id>/...``.
    """
    return Path(data_root) / "lake" / "runs" / str(run_id) / Path(*parts)

def _force_csv_fallback_enabled() -> bool:
    return str(os.getenv("BACKTEST_FORCE_CSV_FALLBACK", "0")).strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    }

def _strict_run_scoped_reads_enabled() -> bool:
    """
    Return True when read resolution must remain run-scoped only.

    Controlled via BACKTEST_STRICT_RUN_SCOPED_READS=1 and intended for
    certification/repro runs where cross-run fallback is not allowed.
    """
    return str(os.getenv("BACKTEST_STRICT_RUN_SCOPED_READS", "0")).strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    }

def choose_partition_dir(candidates: Sequence[Path]) -> Path | None:
    """
    Pick the best available partition directory from ordered candidates.

    Selection order (default):
    1) first existing directory containing parquet/csv files (recursive)
    2) first existing non-empty directory
    3) first existing directory

    Strict mode:
    - when BACKTEST_STRICT_RUN_SCOPED_READS=1, only the first candidate is
      eligible. This prevents cross-run/global fallback during certification.
    """
    normalized = [Path(p) for p in candidates if p is not None]
    if not normalized:
        return None

    if _strict_run_scoped_reads_enabled():
        first = normalized[0]
        if first.exists() and first.is_dir():
            return first
        return None

    for candidate in normalized:
        if not candidate.exists() or not candidate.is_dir():
            continue
        if any(candidate.rglob("*.parquet")) or any(candidate.rglob("*.csv")):
            return candidate

    for candidate in normalized:
        if not candidate.exists() or not candidate.is_dir():
            continue
        try:
            next(candidate.iterdir())
            return candidate
        except StopIteration:
            continue

    for candidate in normalized:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None

def list_parquet_files(path: Path) -> List[Path]:
    """
    Recursively list all parquet files under a directory.
    If parquet exists in some partitions, include parquet files plus CSV-only
    partitions that have no parquet in the same directory.
    """
    if not path.exists():
        return []
    parquet_files = sorted([p for p in path.rglob("*.parquet") if p.is_file()])
    csv_files = sorted([p for p in path.rglob("*.csv") if p.is_file()])
    if not parquet_files:
        return csv_files

    parquet_dirs = {p.parent for p in parquet_files}
    csv_only_partitions = [p for p in csv_files if p.parent not in parquet_dirs]
    return sorted(parquet_files + csv_only_partitions)

def read_parquet(files: Iterable[Path] | Path | str, columns: List[str] | None = None) -> pd.DataFrame:
    """
    Read multiple Parquet (or CSV fallback) files into a single DataFrame.
    """
    if isinstance(files, (str, Path)):
        files = [Path(files)]

    frames = []
    for file_path in files:
        file_path = Path(file_path)
        if file_path.suffix == ".csv":
            use_cols = columns if columns else None
            try:
                frames.append(pd.read_csv(file_path, usecols=use_cols))
            except ValueError:
                # If some columns are missing in CSV, fallback or handled by pandas
                frames.append(pd.read_csv(file_path))
        else:
            if not HAS_PYARROW:
                raise ImportError("pyarrow is required to read parquet files")
            # Use ParquetFile for single-file reads to avoid memory usage
            # when only subset of columns is needed.
            pf = pq.ParquetFile(file_path)
            frames.append(pf.read(columns=columns).to_pandas())
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def read_table_auto(path: Path | str, columns: List[str] | None = None) -> pd.DataFrame:
    """
    Read a single CSV/parquet path through the canonical project IO surface.

    Returns an empty DataFrame when the path is missing or unreadable so callers
    can use best-effort probing without duplicating csv/parquet branches.
    """
    target = Path(path)
    if not target.exists():
        return pd.DataFrame()
    try:
        return read_parquet(target, columns=columns)
    except Exception:
        return pd.DataFrame()

def write_parquet(df: pd.DataFrame, path: Path, skip_lock: bool = False) -> Tuple[Path, str]:
    """
    Write a DataFrame to a Parquet file if available; otherwise fall back to CSV.
    Uses file locking to prevent race conditions during parallel writes unless skip_lock=True.
    Returns the actual path written and the storage format ("parquet" or "csv").
    """
    ensure_dir(path.parent)
    
    if skip_lock:
        return _write_parquet_impl(df, path)
        
    import fcntl
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            return _write_parquet_impl(df, path)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            try:
                os.remove(lock_path)
            except Exception:
                pass

def _write_parquet_impl(df: pd.DataFrame, path: Path) -> Tuple[Path, str]:
    if HAS_PYARROW and not _force_csv_fallback_enabled():
        temp_path = path.with_suffix(path.suffix + ".tmp")
        table = pa.Table.from_pandas(df)
        pq.write_table(table, temp_path)
        temp_path.replace(path)
        return path, "parquet"

    csv_path = path.with_suffix(".csv")
    temp_path = csv_path.with_suffix(".csv.tmp")
    df.to_csv(temp_path, index=False)
    temp_path.replace(csv_path)
    return csv_path, "csv"

def sorted_glob(paths):
    import glob
    return sorted(glob.glob(paths))
