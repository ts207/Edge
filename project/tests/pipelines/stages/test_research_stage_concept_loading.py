from types import SimpleNamespace

from project import PROJECT_ROOT
from project.core.config import get_data_root
from project.pipelines.stages.research import build_research_stages


class _Args(SimpleNamespace):
    def __getattr__(self, name):
        return 0


def test_build_research_stages_loads_concept_from_registry_yaml_path(tmp_path):
    concept_path = tmp_path / "concept.yaml"
    concept_path.write_text(
        """
concept_id: test_dynamic
hypothesis_id: h1
family: STATISTICAL_DISLOCATION
event_definition:
  event_type: BAND_BREAK
  canonical_family: STATISTICAL_DISLOCATION
  detection_logic:
    type: static_threshold
    target_feature: close
    threshold: 1.0
        """.strip(),
        encoding="utf-8",
    )
    args = _Args(
        phase2_gate_profile_resolved="auto",
        phase2_gate_profile="auto",
        timeframes="5m",
        concept=str(concept_path),
        run_phase2_conditional=1,
        phase2_event_type="all",
        seed=7,
        event_parameter_overrides={},
        phase2_shift_labels_k=12,
        mode="research",
        phase2_cost_calibration_mode="auto",
        phase2_cost_min_tob_coverage=0.6,
        phase2_cost_tob_tolerance_minutes=5,
        retail_profile="capital_constrained",
        run_bridge_eval_phase2=0,
        run_promote=0,
        run_compile_blueprints=0,
        run_discovery_quality_summary=0,
    )
    stages = build_research_stages(
        args=args,
        run_id="r1",
        symbols="BTCUSDT",
        start="2024-01-01",
        end="2024-01-31",
        research_gate_profile="balanced",
        project_root=PROJECT_ROOT,
        data_root=get_data_root(),
        phase2_event_chain=[("FOO", "analyze_statistical_dislocation_events.py", [])],
    )
    names = [name for name, _, _ in stages]
    assert any(name.startswith("analyze_events__") for name in names)
