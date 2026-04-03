from __future__ import annotations

from pathlib import Path

from project.scripts.generate_operator_surface_inventory import build_inventory, render_markdown


def test_operator_inventory_covers_new_commands():
    inventory = build_inventory()
    commands = set(inventory["canonical_operator_commands"])
    assert "edge operator compare" in commands
    assert "edge operator regime-report" in commands
    assert "edge operator diagnose" in commands


def test_operator_inventory_covers_action_aliases():
    inventory = build_inventory()
    actions = set(inventory["operator_action_targets"])
    assert actions == {"discover", "export", "validate", "review"}
    assert "package" in set(inventory["advanced_make_targets"])


def test_operator_inventory_doc_is_in_sync():
    inventory = build_inventory()
    expected = render_markdown(inventory)
    doc_path = Path("docs/operator_command_inventory.md")
    assert doc_path.read_text(encoding="utf-8") == expected


def test_readme_and_start_here_anchor_canonical_operator_flow():
    readme = Path("README.md").read_text(encoding="utf-8")
    start_here = Path("docs/00_START_HERE.md").read_text(encoding="utf-8")
    inventory_doc = Path("docs/operator_command_inventory.md").read_text(encoding="utf-8")
    assert "make discover" in readme
    assert "make export" in readme
    assert "make validate" in readme
    assert "four primary operator-facing actions" in readme
    readme_front_door = readme.split("## Preferred front door", 1)[1].split("## Current repo shape", 1)[0]
    assert "make package" not in readme_front_door
    assert "make review" in start_here
    assert "Treat the repo as four operator actions" in start_here
    preferred_front_door = inventory_doc.split("## Preferred front door", 1)[1].split(
        "## Canonical operator commands", 1
    )[0]
    assert "make export RUN_ID=<run_id>" in preferred_front_door
    assert "- `make package`" not in preferred_front_door
