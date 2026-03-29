from __future__ import annotations

import ast
import re
import os
from pathlib import Path
import pytest
from project import PROJECT_ROOT

# --- Dependency Matrix Definition ---

ALLOWED_DEPENDENCIES = {
    "project.core": ["project.spec_registry", "project.artifacts", "project.specs", "project.io"],
    "project.io": ["project.core", "project.artifacts"],
    "project.specs": [
        "project.core",
        "project.io",
        "project.spec_registry",
        "project.schemas",
        "project.artifacts",
    ],
    "project.domain": ["project.core", "project.specs", "project.spec_registry", "project.events"],
    "project.runtime": ["project.core", "project.specs"],
    "project.events": [
        "project.core",
        "project.io",
        "project.specs",
        "project.spec_registry",
        "project.research",
        "project.features",
        "project.artifacts",
        "project.contracts",
        "project.domain",
    ],
    "project.features": [
        "project.core",
        "project.io",
        "project.events",
        "project.spec_registry",
        "project.artifacts",
        "project.contracts",
    ],
    "project.strategy": [
        "project.compilers",
        "project.core",
        "project.strategy.runtime",
        "project.events",
        "project.domain",
        "project.engine",
        "project.schemas",
    ],
    "project.strategy.runtime": [
        "project.core",
        "project.strategy",
        "project.events",
        "project.compilers",
    ],
    "project.engine": [
        "project.core",
        "project.io",
        "project.events",
        "project.features",
        "project.strategy.runtime",
        "project.strategy",
        "project.portfolio",
    ],
    "project.compilers": [
        "project.core",
        "project.specs",
        "project.events",
        "project.domain",
        "project.strategy",
        "project.schemas",
    ],
    "project.portfolio": ["project.core", "project.specs", "project.strategy"],
    "project.research": [
        "project.core",
        "project.io",
        "project.specs",
        "project.runtime",
        "project.events",
        "project.features",
        "project.strategy",
        "project.strategy.runtime",
        "project.engine",
        "project.eval",
        "project.spec_registry",
        "project.artifacts",
        "project.schemas",
        "project.spec_validation",
        "project.contracts",
        "project.domain",
        "project.compilers",
        "project.portfolio",
    ],
    "project.pipelines": [
        "project.research",
        "project.engine",
        "project.events",
        "project.core",
        "project.io",
        "project.specs",
        "project.contracts",
        "project.domain",
        "project.features",
        "project.schemas",
        "project.eval",
        "project.runtime",
        "project.spec_registry",
        "project.experiments",
    ],
    "project.events": [
        "project.core",
        "project.io",
        "project.specs",
        "project.spec_registry",
        "project.research",
        "project.features",
        "project.artifacts",
        "project.contracts",
        "project.domain",
        "project.spec_validation",
    ],
}


def get_package_name(file_path: Path) -> str:
    """Converts a file path to its project package name."""
    rel_path = file_path.relative_to(PROJECT_ROOT.parent)
    parts = rel_path.with_suffix("").parts
    return ".".join(parts)


def get_base_package(pkg: str) -> str:
    """Returns the top-level project package (e.g., project.core)."""
    parts = pkg.split(".")
    if len(parts) >= 2 and parts[0] == "project":
        return ".".join(parts[:2])
    return parts[0]


def test_dependency_matrix():
    """
    Enforces the strict architectural DAG defined in ALLOWED_DEPENDENCIES.
    """
    violations = []
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue

            file_path = Path(root) / file
            current_pkg = get_package_name(file_path)
            current_base = get_base_package(current_pkg)

            if file_path.is_relative_to(PROJECT_ROOT / "strategy" / "compiler"):
                continue

            if current_base not in ALLOWED_DEPENDENCIES:
                continue

            allowed = ALLOWED_DEPENDENCIES[current_base]
            if "*" in allowed:
                continue

            content = file_path.read_text(encoding="utf-8")
            # Find all internal project imports
            imports = re.findall(r"(?:from|import)\s+(project\.[a-zA-Z0-9_\.]+)", content)

            for imp in imports:
                imp_base = get_base_package(imp)
                if imp_base == current_base:
                    continue

                # Check if it's an allowed cross-package import
                if imp_base not in allowed and "project" in imp_base:
                    # Special case for research shared helpers if they move
                    violations.append(f"Violation in {current_pkg}: cannot import {imp_base}")

    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_no_upward_imports_from_domain():
    """
    domain/* cannot import project.pipelines.*
    """
    domain_dirs = [
        "engine",
        "features",
        "events",
        "runtime",
        "strategy",
        "strategy_dsl",
        "strategies",
    ]
    violations = []
    for d in domain_dirs:
        path = PROJECT_ROOT / d
        if not path.exists():
            continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    if file_path.is_relative_to(PROJECT_ROOT / "strategy" / "compiler"):
                        continue
                    content = file_path.read_text(encoding="utf-8")
                    if "project.pipelines" in content:
                        violations.append(
                            f"Architectural Violation: {file_path} imports project.pipelines"
                        )

    if violations:
        pytest.fail("\n".join(violations))


def test_wrappers_are_pure_reexports():
    """
    Ensures that compatibility wrappers are pure re-exports without local logic.
    """
    wrapper_dirs = [
        PROJECT_ROOT / "apps",
        PROJECT_ROOT / "execution",
        PROJECT_ROOT / "infra",
        PROJECT_ROOT / "pipelines" / "eval",
    ]
    for d in wrapper_dirs:
        if not d.exists():
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file
                    content = file_path.read_text(encoding="utf-8")

                    if 'if __name__ == "__main__":' in content:
                        continue

                    if "COMPAT WRAPPER" not in content:
                        raise ImportError(
                            f"Architectural Violation: {file_path} is missing 'COMPAT WRAPPER' marker"
                        )

                    if "from project." not in content and "import project." not in content:
                        raise ImportError(
                            f"Architectural Violation: {file_path} does not import from project root"
                        )

                    if "def " in content or "class " in content:
                        raise ImportError(
                            f"Architectural Violation: {file_path} contains local logic (def/class)"
                        )


def test_explicit_package_roots_stay_shallow() -> None:
    strict_roots = [
        PROJECT_ROOT / "artifacts" / "__init__.py",
        PROJECT_ROOT / "compilers" / "__init__.py",
        PROJECT_ROOT / "eval" / "__init__.py",
        PROJECT_ROOT / "experiments" / "__init__.py",
        PROJECT_ROOT / "live" / "__init__.py",
        PROJECT_ROOT / "portfolio" / "__init__.py",
        PROJECT_ROOT / "spec_validation" / "__init__.py",
        PROJECT_ROOT / "research" / "clustering" / "__init__.py",
        PROJECT_ROOT / "research" / "reports" / "__init__.py",
        PROJECT_ROOT / "research" / "utils" / "__init__.py",
    ]
    lazy_roots = [
        PROJECT_ROOT / "pipelines" / "clean" / "__init__.py",
        PROJECT_ROOT / "pipelines" / "features" / "__init__.py",
        PROJECT_ROOT / "pipelines" / "ingest" / "__init__.py",
    ]

    for path in strict_roots:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        assert not defs, (
            f"Architectural Violation: {path.relative_to(PROJECT_ROOT.parent)} should remain a pure re-export surface, found {defs}"
        )

    for path in lazy_roots:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        assert defs == ["__getattr__"], (
            f"Architectural Violation: {path.relative_to(PROJECT_ROOT.parent)} should only define __getattr__, found {defs}"
        )


def test_preferred_root_surfaces_replace_cross_domain_deep_imports() -> None:
    preferred = {
        "project.artifacts.catalog": ("project.artifacts", PROJECT_ROOT / "artifacts"),
        "project.compilers.executable_strategy_spec": (
            "project.compilers",
            PROJECT_ROOT / "compilers",
        ),
        "project.portfolio.allocation_spec": ("project.portfolio", PROJECT_ROOT / "portfolio"),
        "project.portfolio.sizing": ("project.portfolio", PROJECT_ROOT / "portfolio"),
        "project.spec_validation.loaders": (
            "project.spec_validation",
            PROJECT_ROOT / "spec_validation",
        ),
        "project.spec_validation.ontology": (
            "project.spec_validation",
            PROJECT_ROOT / "spec_validation",
        ),
        "project.spec_validation.search": (
            "project.spec_validation",
            PROJECT_ROOT / "spec_validation",
        ),
        "project.eval.splits": ("project.eval", PROJECT_ROOT / "eval"),
        "project.live.runner": ("project.live", PROJECT_ROOT / "live"),
        "project.live.health_checks": ("project.live", PROJECT_ROOT / "live"),
        "project.live.state": ("project.live", PROJECT_ROOT / "live"),
    }
    violations: list[str] = []
    exemptions = {
        PROJECT_ROOT / "scripts" / "run_live_engine.py",
        # test_splits.py imports _normalize_ts (a private function) directly from the submodule
        # — importing private internals via package root is not appropriate
        PROJECT_ROOT / "tests" / "eval" / "test_splits.py",
    }
    for file_path in PROJECT_ROOT.rglob("*.py"):
        if (
            file_path in exemptions
            or file_path.is_relative_to(PROJECT_ROOT / "tests")
            or file_path.is_relative_to(PROJECT_ROOT / "scripts")
        ):
            continue
        content = file_path.read_text(encoding="utf-8")
        for deep_module, (preferred_root, owner_root) in preferred.items():
            if file_path.is_relative_to(owner_root):
                continue
            if re.search(rf"(?:from|import)\s+{re.escape(deep_module)}(?:\.|\s|$)", content):
                violations.append(
                    f"Architectural Violation: {file_path.relative_to(PROJECT_ROOT.parent)} imports {deep_module}; prefer {preferred_root}"
                )
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_phase2_helper_imports_use_research_compat():
    """
    Tests and scripts should import phase2 helper utilities from canonical
    research service/spec modules, not from the pipeline wrapper module.
    """
    forbidden_helpers = {
        "_apply_multiplicity_controls",
        "_apply_validation_multiple_testing",
        "_condition_for_cond_name",
        "_condition_routing",
        "_make_family_id",
        "_split_and_score_candidates",
    }
    pattern = re.compile(
        r"from\s+project\.pipelines\.research\.phase2_candidate_discovery\s+import\s+([^\n]+)"
    )
    violations = []
    for root in (PROJECT_ROOT.parent / "tests", PROJECT_ROOT / "scripts"):
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            content = file_path.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                imported = {
                    token.strip().split(" as ", 1)[0]
                    for token in match.group(1).split(",")
                    if token.strip()
                }
                if imported & forbidden_helpers:
                    violations.append(
                        f"Architectural Violation: {file_path} imports phase2 helpers from the pipeline wrapper"
                    )
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_promotion_helper_imports_use_research_compat():
    """
    Tests and scripts should import promotion helper utilities from canonical
    research service/promotion modules, not from the pipeline wrapper module.
    """
    forbidden_helpers = {
        "_apply_portfolio_overlap_gate",
        "_assign_and_validate_promotion_tiers",
        "_build_negative_control_diagnostics",
        "_build_promotion_capital_footprint",
        "_build_promotion_statistical_audit",
        "_evaluate_row",
        "_load_bridge_metrics",
        "_load_dynamic_min_events_by_event",
        "_merge_bridge_metrics",
        "_portfolio_diversification_violations",
        "_stabilize_promoted_output_schema",
    }
    pattern = re.compile(
        r"from\s+project\.pipelines\.research\.promote_candidates\s+import\s+([^\n]+)"
    )
    violations = []
    for root in (PROJECT_ROOT.parent / "tests", PROJECT_ROOT / "scripts"):
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            content = file_path.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                imported = {
                    token.strip().split(" as ", 1)[0]
                    for token in match.group(1).split(",")
                    if token.strip()
                }
                if imported & forbidden_helpers:
                    violations.append(
                        f"Architectural Violation: {file_path} imports promotion helpers from the pipeline wrapper"
                    )
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_research_pipeline_wrappers_only_depend_on_cli_services_and_specs() -> None:
    allowed_import_prefixes = {
        "project.research.cli",
        "project.research.services",
        "project.specs.gates",
    }
    wrapper_paths = [
        PROJECT_ROOT / "pipelines" / "research" / "phase2_candidate_discovery.py",
        PROJECT_ROOT / "pipelines" / "research" / "promote_candidates.py",
    ]
    violations: list[str] = []
    for wrapper_path in wrapper_paths:
        content = wrapper_path.read_text(encoding="utf-8")
        imports = re.findall(r"(?:from|import)\s+(project\.[a-zA-Z0-9_\.]+)", content)
        for imported in imports:
            if any(
                imported == prefix or imported.startswith(f"{prefix}.")
                for prefix in allowed_import_prefixes
            ):
                continue
            violations.append(
                f"Architectural Violation: {wrapper_path.relative_to(PROJECT_ROOT.parent)} imports {imported}"
            )
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def _files_importing(module_pattern: str) -> list[str]:
    pattern = re.compile(rf"(?:from|import)\s+{re.escape(module_pattern)}(?:\.|\s|$)")
    matches: list[str] = []
    for root in (PROJECT_ROOT, PROJECT_ROOT.parent / "tests"):
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            content = file_path.read_text(encoding="utf-8")
            if pattern.search(content):
                matches.append(str(file_path.relative_to(PROJECT_ROOT.parent)).replace("\\", "/"))
    return sorted(set(matches))


def test_architecture_surface_inventory_doc_exists() -> None:
    inventory_path = PROJECT_ROOT.parent / "docs" / "ARCHITECTURE_SURFACE_INVENTORY.md"
    assert inventory_path.exists(), "expected architecture surface inventory doc"
    text = inventory_path.read_text(encoding="utf-8")
    for needle in (
        "Canonical Surfaces",
        "Transitional Surfaces",
        "project.strategy.dsl",
        "Removed Surfaces",
    ):
        assert needle in text


def test_architecture_metrics_and_checklist_exist() -> None:
    metrics_path = PROJECT_ROOT.parent / "docs" / "generated" / "architecture_metrics.json"
    checklist_path = PROJECT_ROOT.parent / "docs" / "ARCHITECTURE_MAINTENANCE_CHECKLIST.md"
    assert metrics_path.exists(), "expected architecture metrics snapshot"
    assert checklist_path.exists(), "expected architecture maintenance checklist"

    import json

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    for key in (
        "project.research.compat_importers",
        "project.strategy_dsl_importers",
        "project.strategy_templates_importers",
        "run_all_coordinator_lines",
        "module_coupling_count",
        "cross_boundary_import_count",
        "circular_dependency_count",
        "test_coverage_ratio",
    ):
        assert key in metrics["metrics"], f"Missing metric snapshot: {key}"

    # Assert thresholds for Phase 4 metrics
    # module_coupling_count reflects architectural complexity (adjusted for expanded codebase)
    assert metrics["metrics"]["module_coupling_count"] <= 2600
    assert metrics["metrics"]["cross_boundary_import_count"] <= 1800
    assert metrics["metrics"]["circular_dependency_count"] <= 5

    checklist_text = checklist_path.read_text(encoding="utf-8")
    for needle in (
        "Contracts and Generated Docs",
        "Research Services and Wrappers",
        "Strategy Surfaces",
        "Metrics and Guardrails",
    ):
        assert needle in checklist_text


def test_transitional_import_surfaces_are_frozen_to_documented_allowlist() -> None:
    allowed = {
        "project.strategy_dsl": set(),
        "project.strategy_templates": set(),
    }

    violations = []
    for module_pattern, expected_paths in allowed.items():
        actual_paths = set(_files_importing(module_pattern))
        unexpected = sorted(actual_paths - expected_paths)
        if unexpected:
            violations.append(
                f"Unexpected importers for transitional surface {module_pattern}: {unexpected}"
            )

    if violations:
        pytest.fail("\n".join(violations))


def test_decomposed_detector_modules_stay_research_free():
    for name in ("exhaustion", "funding", "liquidity", "trend", "volatility"):
        detector_path = PROJECT_ROOT / "events" / "detectors" / f"{name}.py"
        content = detector_path.read_text(encoding="utf-8")
        assert "project.research" not in content, (
            f"Architectural Violation: {name} detector module must not import project.research"
        )
