from __future__ import annotations

import json
from pathlib import Path

from project.scripts import bootstrap_literature_review_artifacts as bootstrap


def test_build_bootstrap_literature_artifacts_writes_traceable_claims(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec" / "concepts"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "C_TEST.yaml").write_text(
        "\n".join(
            [
                "concept_id: C_TEST",
                "name: Test Concept",
                "definition: deterministic bootstrap concept",
                "data_requirements:",
                "  - dataset: perp_ohlcv_1m",
                "    columns: [close, volume]",
                "    granularity: 1m",
                "metrics:",
                "  - id: variance_ratio",
                "tests:",
                "  - id: T_TEST_01",
                "    criteria: variance_ratio in [0.9, 1.1]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    atlas_path = tmp_path / "knowledge_atlas.json"
    fragments_path = tmp_path / "fragments.jsonl"

    result = bootstrap.build_bootstrap_literature_artifacts(
        spec_dir=spec_dir,
        atlas_path=atlas_path,
        fragments_path=fragments_path,
    )

    atlas = json.loads(atlas_path.read_text(encoding="utf-8"))
    fragment = json.loads(fragments_path.read_text(encoding="utf-8").strip())

    assert result["claim_count"] == 1
    assert result["fragment_count"] == 1
    assert atlas["generation_mode"] == "bootstrap_internal"
    assert atlas["claims"][0]["concept_id"] == "C_TEST"
    assert atlas["claims"][0]["evidence"][0]["locator"] == "spec/concepts/C_TEST.yaml#definition"
    assert atlas["claims"][0]["operationalization"]["features"] == [
        "variance_ratio",
        "close",
        "volume",
    ]
    assert fragment["concept_id"] == "C_TEST"
    assert fragment["locator"] == "spec/concepts/C_TEST.yaml#definition"
