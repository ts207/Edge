from __future__ import annotations

import re
import os
from pathlib import Path
import pytest
from project import PROJECT_ROOT

# --- Dependency Matrix Definition ---

ALLOWED_DEPENDENCIES = {
    "project.core": ["project.spec_registry", "project.artifacts", "project.specs", "project.io"],
    "project.io": ["project.core", "project.artifacts"],
    "project.specs": ["project.core", "project.io", "project.spec_registry", "project.schemas", "project.artifacts"],
    "project.domain": ["project.core", "project.specs", "project.spec_registry"],
    "project.runtime": ["project.core", "project.specs"],
    "project.events": ["project.core", "project.io", "project.specs", "project.spec_registry", "project.research", "project.features", "project.artifacts", "project.contracts", "project.domain"],
    "project.features": ["project.core", "project.io", "project.events", "project.spec_registry", "project.artifacts", "project.contracts"],
    "project.strategy": ["project.compilers", "project.core", "project.strategies", "project.events", "project.domain", "project.engine", "project.schemas"],
    "project.strategies": ["project.core", "project.strategy", "project.events", "project.compilers"],
    "project.engine": ["project.core", "project.io", "project.events", "project.features", "project.strategies", "project.strategy", "project.portfolio"],
    "project.compilers": ["project.core", "project.specs", "project.events", "project.domain", "project.strategy", "project.schemas"],
    "project.portfolio": ["project.core", "project.specs", "project.strategy"],
    "project.research": [
        "project.core", "project.io", "project.specs", "project.runtime", 
        "project.events", "project.features", "project.strategy",
        "project.strategies", "project.engine", "project.eval",
        "project.spec_registry",
        "project.artifacts", "project.schemas", "project.spec_validation", "project.contracts",
        "project.domain", "project.compilers", "project.portfolio"
    ],

    "project.pipelines": ["*"], # Pipelines can import anything below
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
    domain_dirs = ["engine", "features", "events", "runtime", "strategy", "strategy_dsl", "strategies"]
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
                        violations.append(f"Architectural Violation: {file_path} imports project.pipelines")
    
    if violations:
        pytest.fail("\n".join(violations))

def test_wrappers_are_pure_reexports():
    """
    Ensures that compatibility wrappers are pure re-exports without local logic.
    """
    wrapper_dirs = [
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
                        raise ImportError(f"Architectural Violation: {file_path} is missing 'COMPAT WRAPPER' marker")
                    
                    if "from project." not in content and "import project." not in content:
                        raise ImportError(f"Architectural Violation: {file_path} does not import from project root")
                    
                    if "def " in content or "class " in content:
                        raise ImportError(f"Architectural Violation: {file_path} contains local logic (def/class)")

def test_file_size_thresholds():
    """
    Warns or fails if files exceed the 800 LOC threshold (Phase 1.3).
    """
    THRESHOLD = 800
    oversized = []
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = Path(root) / file
            lines = file_path.read_text(encoding="utf-8").splitlines()
            if len(lines) > THRESHOLD:
                # Exclude specific files that are known monoliths to be refactored
                rel_path = str(file_path.relative_to(PROJECT_ROOT.parent))
                if any(x in rel_path for x in ["dsl_interpreter_v1.py", "stage_registry.py", "shrinkage.py", "promotion/promotion_decisions.py", "promotion/promotion_reporting.py", "execution_engine.py"]):
                    continue
                oversized.append(f"{rel_path}: {len(lines)} lines")
    
    if oversized:
        # Enforce strictly to prevent unchecked growth
        issues = "\n".join(f"  {f}" for f in oversized)
        raise AssertionError(f"Architectural Violation: {len(oversized)} files exceed the {THRESHOLD} LOC threshold:\n{issues}")


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
        "project.pipelines.research.cli",
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
            if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in allowed_import_prefixes):
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
    ):
        assert key in metrics["metrics"]

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
