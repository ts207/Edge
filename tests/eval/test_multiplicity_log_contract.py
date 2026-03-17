from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.eval import multiplicity


def test_update_program_hypothesis_log_normalizes_mixed_direction_types(tmp_path: Path):
    data_root = tmp_path
    program_id = "prog_1"
    existing_path = multiplicity.get_program_hypothesis_log_path(program_id, data_root)
    existing_path.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {"hypothesis_id": "old_long", "p_value": 0.01, "direction": 1.0},
            {"hypothesis_id": "old_short", "p_value": 0.02, "direction": -1.0},
        ]
    ).to_parquet(existing_path, index=False)

    new_hypotheses = pd.DataFrame(
        [
            {"hypothesis_id": "new_long", "p_value": 0.03, "direction": "long"},
            {"hypothesis_id": "new_short", "p_value": 0.04, "direction": "short"},
        ]
    )

    combined = multiplicity.update_program_hypothesis_log(
        program_id=program_id,
        data_root=data_root,
        new_hypotheses=new_hypotheses,
    )

    assert list(combined["direction"]) == ["long", "short", "long", "short"]

    persisted = pd.read_parquet(existing_path)
    assert list(persisted["direction"]) == ["long", "short", "long", "short"]
