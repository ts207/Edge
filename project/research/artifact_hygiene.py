from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from project.spec_registry.loaders import repo_root


def infer_workspace_root(*paths: str | Path | None) -> Path:
    resolved = [Path(path).resolve() for path in paths if path is not None]
    if not resolved:
        return repo_root().resolve()
    common = Path(os.path.commonpath([str(path) for path in resolved]))
    return common.resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def render_workspace_path(path: str | Path, *, workspace_root: str | Path | None = None) -> str:
    resolved = Path(path).resolve()
    root = Path(workspace_root).resolve() if workspace_root is not None else repo_root().resolve()
    if _is_relative_to(resolved, root):
        return resolved.relative_to(root).as_posix()
    return resolved.as_posix()


def build_artifact_refs(
    refs: Mapping[str, str | Path],
    *,
    workspace_root: str | Path | None = None,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    root = Path(workspace_root).resolve() if workspace_root is not None else repo_root().resolve()
    payload: dict[str, dict[str, object]] = {}
    invalid: list[str] = []
    for key, raw_path in refs.items():
        path = Path(raw_path).resolve()
        relative = render_workspace_path(path, workspace_root=root)
        exists = path.exists()
        within_workspace = _is_relative_to(path, root)
        payload[str(key)] = {
            "path": relative,
            "exists": exists,
            "within_workspace": within_workspace,
        }
        if not exists or not within_workspace:
            invalid.append(str(key))
    return payload, invalid


def invalid_artifact_header(invalid_keys: list[str]) -> list[str]:
    if not invalid_keys:
        return []
    joined = ", ".join(sorted(invalid_keys))
    return [
        "> INVALID ARTIFACT REFERENCES",
        "> Referenced outputs are missing or outside the current workspace: " + joined,
        "",
    ]
