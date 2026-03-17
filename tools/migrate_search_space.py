import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
OLD_SPEC = REPO_ROOT / "spec" / "search_space.yaml"
NEW_SEARCH_DIR = REPO_ROOT / "spec" / "search"

def migrate():
    if not OLD_SPEC.exists():
        print(f"Old spec not found at {OLD_SPEC}")
        return

    with open(OLD_SPEC) as f:
        old_doc = yaml.safe_load(f)

    # Simple migration: Create search_full.yaml from existing settings
    new_spec = {
        "version": 1,
        "kind": "search_spec",
        "metadata": {
            "phase": "full",
            "description": "Migrated from search_space.yaml"
        },
        "search_mode": "full",
        "triggers": {
            "event_families": "*",
            "state_families": "*"
        },
        "contexts": old_doc.get("contexts", {}),
        "templates": old_doc.get("templates", "*"),
        "horizons": old_doc.get("horizons", ["5m", "15m", "60m"]),
        "directions": old_doc.get("directions", ["long", "short"]),
        "entry_lag": "*",
        "cost_profiles": old_doc.get("cost_profiles", ["standard"])
    }

    NEW_SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    with open(NEW_SEARCH_DIR / "search_full_migrated.yaml", "w") as f:
        yaml.dump(new_spec, f, sort_keys=False)
    
    print(f"Migration complete: search_full_migrated.yaml created.")

if __name__ == "__main__":
    migrate()
