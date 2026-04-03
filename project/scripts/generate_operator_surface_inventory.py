from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = ROOT / "project" / "cli.py"
MAKEFILE_PATH = ROOT / "Makefile"
OUT_PATH = ROOT / "docs" / "operator_command_inventory.md"


def extract_operator_commands(cli_text: str) -> list[str]:
    found = set(re.findall(r'operator_sub\.add_parser\(\s*"([^"]+)"', cli_text))
    loop_match = re.search(r'for name, help_text in \((.*?)\):', cli_text, flags=re.DOTALL)
    if loop_match:
        found.update(re.findall(r'\("([^"]+)"\s*,', loop_match.group(1)))
    return sorted(found)


def extract_make_targets(makefile_text: str) -> list[str]:
    targets = []
    for line in makefile_text.splitlines():
        if not line or line.startswith("\t") or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("."):
            target = line.split(":", 1)[0].strip()
            if (
                target
                and " " not in target
                and not target.isupper()
                and "=" not in target
                and not target.startswith("$")
            ):
                targets.append(target)
    return sorted(dict.fromkeys(targets))


def build_inventory() -> dict[str, list[str]]:
    cli_text = CLI_PATH.read_text(encoding="utf-8")
    makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8") if MAKEFILE_PATH.exists() else ""
    return {
        "canonical_operator_commands": [f"edge operator {name}" for name in extract_operator_commands(cli_text)],
        "make_targets": extract_make_targets(makefile_text),
    }


def render_markdown(inventory: dict[str, list[str]]) -> str:
    lines = [
        "# Operator command inventory",
        "",
        "Generated from `project/cli.py` and `Makefile`. Update this file with `python -m project.scripts.generate_operator_surface_inventory`.",
        "",
        "## Preferred front door",
        "",
        "Use these surfaces first:",
        "",
        "- `edge operator preflight|plan|run` for bounded research issuance",
        "- thesis bootstrap builders for `package` and thesis-store refresh",
        "- `edge operator diagnose|regime-report|compare` for post-run review",
        "- maintained `make` targets only for common workflow bundles and maintenance",
        "",
        "## Canonical operator commands",
        "",
    ]
    for command in inventory["canonical_operator_commands"]:
        lines.append(f"- `{command}`")
    lines += ["", "## Make targets", ""]
    for target in inventory["make_targets"]:
        lines.append(f"- `{target}`")
    lines += ["", "## Inventory payload", "", "```json", json.dumps(inventory, indent=2, sort_keys=True), "```", ""]
    return "\n".join(lines)


def main() -> int:
    inventory = build_inventory()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render_markdown(inventory), encoding="utf-8")
    print(str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
