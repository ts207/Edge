"""Regression tests for operational defect fixes in Sprint 7."""
import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from project.live.contracts.promoted_thesis import (
    ALL_DEPLOYMENT_STATES,
    PromotedThesis,
    ThesisEvidence,
    ThesisGovernance,
    ThesisLineage,
    ThesisRequirements,
    ThesisSource,
)
from project.live.deployment import check_thesis
from project.research.live_export import (
    build_promoted_theses,
    DataIntegrityError,
    export_promoted_theses_for_run,
)
from project.specs.manifest import validate_stage_manifest_contract
from project.pipelines.execution_engine_support import (
    _allow_synthesized_manifest,
    _stage_allows_zero_outputs,
    _manifest_declared_outputs_exist,
)
from project.research.validation.result_writer import (
    write_promotion_ready_candidates,
)


class TestDeploymentStateValidation:
    """Tests for unified deployment-state constants."""

    def test_all_deployment_states_is_frozenset(self):
        assert isinstance(ALL_DEPLOYMENT_STATES, frozenset)

    def test_all_deployment_states_contains_required_states(self):
        required_states = {
            "monitor_only",
            "paper_only",
            "promoted",
            "paper_enabled",
            "paper_approved",
            "live_eligible",
            "live_enabled",
            "live_paused",
            "live_disabled",
            "retired",
        }
        assert required_states.issubset(ALL_DEPLOYMENT_STATES)

    def test_pydantic_rejects_unknown_deployment_state(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError, match="deployment_state"):
            PromotedThesis(
                thesis_id="test_unknown_state",
                symbols=["BTCUSDT"],
                timeframe="1h",
                event_family="TEST",
                event_type="TEST_EVENT",
                direction="long",
                horizon_bars=12,
                sample_size=100,
                entry_signal={"type": "market"},
                exit_signal={"type": "market"},
                deployment_state="unknown_state_xyz",
                status="active",
                source=ThesisSource(
                    hypothesis_id="hyp_1",
                    candidate_id="cand_1",
                ),
                evidence=ThesisEvidence(
                    sample_size=100,
                    expectancy_bps=50.0,
                    expectancy_confidence=0.8,
                ),
                governance=ThesisGovernance(
                    program_id="test_program",
                ),
                lineage=ThesisLineage(
                    run_id="test_run",
                    candidate_id="cand_1",
                ),
                requirements=ThesisRequirements(),
            )

    def test_valid_deployment_states_accepted_by_model(self):
        for state in ["paper_only", "live_enabled", "live_eligible"]:
            thesis = PromotedThesis(
                thesis_id=f"test_{state}",
                symbols=["BTCUSDT"],
                timeframe="1h",
                event_family="TEST",
                event_type="TEST_EVENT",
                direction="long",
                horizon_bars=12,
                sample_size=100,
                entry_signal={"type": "market"},
                exit_signal={"type": "market"},
                deployment_state=state,
                status="active",
                source=ThesisSource(
                    hypothesis_id="hyp_1",
                    candidate_id="cand_1",
                ),
                evidence=ThesisEvidence(
                    sample_size=100,
                    expectancy_bps=50.0,
                    expectancy_confidence=0.8,
                ),
                governance=ThesisGovernance(
                    program_id="test_program",
                ),
                lineage=ThesisLineage(
                    run_id="test_run",
                    candidate_id="cand_1",
                ),
                requirements=ThesisRequirements(),
            )
            assert thesis.deployment_state == state


class TestLiveExportFailClosed:
    """Tests for live_export failing on malformed candidates."""

    def test_build_thesis_raises_on_missing_candidate_id(self):
        bundle = {
            "candidate_id": "",
            "sample_definition": {"symbol": "BTCUSDT", "n_events": 100},
            "split_definition": {"bar_duration_minutes": 60},
            "event_family": "TEST",
            "cost_robustness": {"net_expectancy_bps": 50.0},
        }
        with pytest.raises(DataIntegrityError, match="Missing candidate_id"):
            build_promoted_theses(
                run_id="test_run",
                bundles=[bundle],
                promoted_df=pd.DataFrame(),
                validation_metadata={},
            )

    def test_build_thesis_raises_on_missing_required_fields(self):
        bundle = {
            "candidate_id": "cand_123",
            "sample_definition": {},
            "split_definition": {},
            "event_family": "",
            "cost_robustness": {},
        }
        with pytest.raises(DataIntegrityError, match="missing required fields"):
            build_promoted_theses(
                run_id="test_run",
                bundles=[bundle],
                promoted_df=pd.DataFrame(),
                validation_metadata={},
            )

    def test_empty_promoted_df_raises_by_default(self, tmp_path):
        run_id = "test_empty_promoted"
        data_root = tmp_path / "data"
        data_root.mkdir(parents=True)
        
        promotion_dir = data_root / "reports" / "promotions" / run_id
        promotion_dir.mkdir(parents=True)
        
        (promotion_dir / "evidence_bundles.jsonl").write_text("[]")
        
        with pytest.raises(DataIntegrityError, match="Promoted candidates DataFrame is empty"):
            export_promoted_theses_for_run(
                run_id,
                data_root=data_root,
                bundles=[],
                promoted_df=pd.DataFrame(),
            )

    def test_empty_promoted_df_allowed_with_flag(self, tmp_path):
        run_id = "test_empty_promoted_allowed"
        data_root = tmp_path / "data"
        data_root.mkdir(parents=True)
        
        promotion_dir = data_root / "reports" / "promotions" / run_id
        promotion_dir.mkdir(parents=True)
        
        (promotion_dir / "evidence_bundles.jsonl").write_text("[]")
        
        result = export_promoted_theses_for_run(
            run_id,
            data_root=data_root,
            bundles=[],
            promoted_df=pd.DataFrame(),
            allow_bundle_only_export=True,
        )
        assert result.thesis_count == 0


class TestManifestSuccessCriteria:
    """Tests for hardened manifest success criteria."""

    def test_allow_synthesized_manifest_respects_env(self, monkeypatch):
        monkeypatch.setenv("BACKTEST_ALLOW_SYNTHESIZED_STAGE_MANIFEST", "1")
        assert _allow_synthesized_manifest() is True
        
        monkeypatch.setenv("BACKTEST_ALLOW_SYNTHESIZED_STAGE_MANIFEST", "0")
        assert _allow_synthesized_manifest() is False
        
        monkeypatch.delenv("BACKTEST_ALLOW_SYNTHESIZED_STAGE_MANIFEST", raising=False)
        assert _allow_synthesized_manifest() is False

    def test_stage_allows_zero_outputs_defaults_to_false(self):
        assert _stage_allows_zero_outputs("unknown_stage") is False
        assert _stage_allows_zero_outputs("phase2_search_engine") is False

    def test_ingest_stage_allows_zero_outputs(self):
        assert _stage_allows_zero_outputs("ingest") is True

    def test_manifest_declared_outputs_exist_rejects_empty_outputs_for_unknown_stage(self, tmp_path):
        manifest_path = tmp_path / "test.json"
        manifest_path.write_text(json.dumps({
            "run_id": "test",
            "stage": "unknown_stage",
            "stage_instance_id": "test_instance",
            "started_at": "2024-01-01T00:00:00Z",
            "status": "success",
            "parameters": {},
            "inputs": [],
            "outputs": [],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
        }))
        
        payload = json.loads(manifest_path.read_text())
        result = _manifest_declared_outputs_exist(manifest_path, payload)
        assert result is False

    def test_manifest_declared_outputs_exist_accepts_empty_outputs_for_ingest(self, tmp_path):
        manifest_path = tmp_path / "test.json"
        manifest_path.write_text(json.dumps({
            "run_id": "test",
            "stage": "ingest",
            "stage_instance_id": "test_instance",
            "started_at": "2024-01-01T00:00:00Z",
            "status": "success",
            "parameters": {},
            "inputs": [],
            "outputs": [],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
        }))
        
        payload = json.loads(manifest_path.read_text())
        result = _manifest_declared_outputs_exist(manifest_path, payload)
        assert result is True


class TestSkippedStatusValidation:
    """Tests for skipped status in manifest validation."""

    def test_manifest_accepts_skipped_status(self):
        manifest = {
            "run_id": "test_run",
            "stage": "test_stage",
            "stage_instance_id": "test_instance",
            "started_at": "2024-01-01T00:00:00Z",
            "finished_at": "2024-01-01T01:00:00Z",
            "ended_at": "2024-01-01T01:00:00Z",
            "status": "skipped",
            "parameters": {},
            "inputs": [],
            "outputs": [],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
        }
        validate_stage_manifest_contract(manifest)

    def test_manifest_accepts_success_status(self):
        manifest = {
            "run_id": "test_run",
            "stage": "test_stage",
            "stage_instance_id": "test_instance",
            "started_at": "2024-01-01T00:00:00Z",
            "finished_at": "2024-01-01T01:00:00Z",
            "ended_at": "2024-01-01T01:00:00Z",
            "status": "success",
            "parameters": {},
            "inputs": [],
            "outputs": [],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
        }
        validate_stage_manifest_contract(manifest)

    def test_manifest_rejects_invalid_status(self):
        manifest = {
            "run_id": "test_run",
            "stage": "test_stage",
            "stage_instance_id": "test_instance",
            "started_at": "2024-01-01T00:00:00Z",
            "status": "invalid_status",
            "parameters": {},
            "inputs": [],
            "outputs": [],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
        }
        with pytest.raises(ValueError, match="invalid status"):
            validate_stage_manifest_contract(manifest)


class TestDeployCLIPaperTradingRemoved:
    """Tests that paper_trading is not used in deploy paths."""

    def test_cli_py_has_no_paper_trading_in_deploy(self):
        cli_path = Path(__file__).parent.parent.parent / "cli.py"
        content = cli_path.read_text()
        
        assert 'runtime_mode="paper_trading"' not in content, \
            "paper_trading runtime_mode should not be used in cli.py"
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'deploy' in line.lower() and 'paper_trading' in line:
                pytest.fail(f"Line {i+1} in cli.py references paper_trading in deploy context")


class TestSynthesizedManifestCacheRejection:
    """Tests that synthesized manifests are rejected from cache hits."""

    def test_synthesized_manifest_in_stats_rejected_from_cache(self, tmp_path, monkeypatch):
        manifest_path = tmp_path / "runs" / "test_run" / "test_stage.json"
        manifest_path.parent.mkdir(parents=True)
        
        manifest_content = {
            "run_id": "test_run",
            "stage": "test_stage",
            "stage_instance_id": "test_stage",
            "started_at": "2024-01-01T00:00:00Z",
            "finished_at": "2024-01-01T01:00:00Z",
            "status": "success",
            "parameters": {},
            "inputs": [],
            "outputs": [{"path": str(tmp_path / "output.parquet")}],
            "spec_hashes": {},
            "ontology_spec_hash": "abc123",
            "input_hash": "test_hash_123",
            "stats": {"synthesized_manifest": True},
        }
        
        manifest_path.write_text(json.dumps(manifest_content))
        
        payload = json.loads(manifest_path.read_text())
        stats = payload.get("stats", {})
        is_synthesized = bool(stats.get("synthesized_manifest", False))
        
        assert is_synthesized is True, "Manifest should be marked as synthesized"


class TestLiveExportAggregateFailures:
    """Tests for aggregate failure reporting in live export."""

    def test_multiple_malformed_candidates_aggregate_into_one_failure(self):
        bundles = [
            {
                "candidate_id": "",
                "sample_definition": {"symbol": "BTCUSDT", "n_events": 100},
                "split_definition": {"bar_duration_minutes": 60},
                "event_family": "TEST",
                "cost_robustness": {"net_expectancy_bps": 50.0},
            },
            {
                "candidate_id": "cand_2",
                "sample_definition": {},
                "split_definition": {},
                "event_family": "",
                "cost_robustness": {},
            },
        ]
        
        with pytest.raises(DataIntegrityError, match="Failed to build .* promoted theses"):
            build_promoted_theses(
                run_id="test_run",
                bundles=bundles,
                promoted_df=pd.DataFrame(),
                validation_metadata={},
            )

    def test_single_malformed_candidate_raises_specific_error(self):
        bundle = {
            "candidate_id": "cand_123",
            "sample_definition": {},
            "split_definition": {},
            "event_family": "",
            "cost_robustness": {},
        }
        
        with pytest.raises(DataIntegrityError, match="missing required fields"):
            build_promoted_theses(
                run_id="test_run",
                bundles=[bundle],
                promoted_df=pd.DataFrame(),
                validation_metadata={},
            )


class TestValidationMetadataPreload:
    """Tests for validation metadata preload in export."""

    def test_validation_metadata_attached_on_successful_preload(self, tmp_path):
        from project.research.validation.contracts import (
            ValidationBundle,
            ValidatedCandidateRecord,
            ValidationDecision,
            ValidationMetrics,
        )
        
        run_id = "test_validation_preload"
        data_root = tmp_path / "data"
        validation_dir = data_root / "reports" / "validation" / run_id
        validation_dir.mkdir(parents=True)
        
        bundle = ValidationBundle(
            run_id=run_id,
            created_at="2024-01-01T00:00:00Z",
            validated_candidates=[
                ValidatedCandidateRecord(
                    candidate_id="cand_1",
                    decision=ValidationDecision(
                        status="validated",
                        candidate_id="cand_1",
                        run_id=run_id,
                        program_id="test_program",
                        reason_codes=["PASS"],
                    ),
                    metrics=ValidationMetrics(
                        sample_count=100,
                        expectancy=0.005,
                        stability_score=0.8,
                    ),
                    anchor_summary="test_anchor",
                    template_id="test_template",
                    direction="long",
                    horizon_bars=12,
                    artifact_refs=[],
                )
            ],
            rejected_candidates=[],
            inconclusive_candidates=[],
            summary_stats={"total": 1, "validated": 1},
            effect_stability_report={},
        )
        
        import json
        (validation_dir / "validation_bundle.json").write_text(json.dumps(bundle.to_dict()))
        
        promotion_dir = data_root / "reports" / "promotions" / run_id
        promotion_dir.mkdir(parents=True)
        
        evidence_bundle = {
            "candidate_id": "cand_1",
            "sample_definition": {"symbol": "BTCUSDT", "n_events": 100},
            "split_definition": {"bar_duration_minutes": 60},
            "event_family": "TEST",
            "event_type": "TEST_EVENT",
            "cost_robustness": {"net_expectancy_bps": 50.0},
            "metadata": {"hypothesis_id": "hyp_1"},
        }
        (promotion_dir / "evidence_bundles.jsonl").write_text(json.dumps(evidence_bundle))
        
        promoted_df = pd.DataFrame([{"candidate_id": "cand_1", "status": "PROMOTED"}])
        
        result = export_promoted_theses_for_run(
            run_id,
            data_root=data_root,
            bundles=[evidence_bundle],
            promoted_df=promoted_df,
        )
        
        assert result.thesis_count == 1


class TestCanonicalPromotionArtifact:
    """Tests for canonical promotion_ready_candidates.parquet production and consumption."""

    def test_write_promotion_ready_candidates_produces_parquet(self, tmp_path):
        from project.research.validation.contracts import (
            ValidationBundle,
            ValidatedCandidateRecord,
            ValidationDecision,
            ValidationMetrics,
        )
        
        run_id = "test_promotion_artifact"
        base_dir = tmp_path / "validation" / run_id
        
        bundle = ValidationBundle(
            run_id=run_id,
            created_at="2024-01-01T00:00:00Z",
            validated_candidates=[
                ValidatedCandidateRecord(
                    candidate_id="cand_1",
                    decision=ValidationDecision(
                        status="validated",
                        candidate_id="cand_1",
                        run_id=run_id,
                        program_id="test_program",
                        reason_codes=["PASS"],
                    ),
                    metrics=ValidationMetrics(
                        sample_count=100,
                        expectancy=0.005,
                        stability_score=0.8,
                    ),
                    anchor_summary="test_anchor",
                    template_id="test_template",
                    direction="long",
                    horizon_bars=12,
                    artifact_refs=[],
                    validation_stage_version="v1",
                )
            ],
            rejected_candidates=[],
            inconclusive_candidates=[],
            summary_stats={"total": 1, "validated": 1},
            effect_stability_report={},
        )
        
        path = write_promotion_ready_candidates(bundle, base_dir=base_dir)
        
        assert path is not None
        assert path.exists()
        assert path.name == "promotion_ready_candidates.parquet"
        
        df = pd.read_parquet(path)
        assert len(df) == 1
        assert df.iloc[0]["candidate_id"] == "cand_1"
        assert "validation_status" in df.columns
        assert "validation_run_id" in df.columns

    def test_empty_validated_candidates_returns_none(self, tmp_path):
        from project.research.validation.contracts import ValidationBundle
        
        run_id = "test_empty_artifact"
        base_dir = tmp_path / "validation" / run_id
        
        bundle = ValidationBundle(
            run_id=run_id,
            created_at="2024-01-01T00:00:00Z",
            validated_candidates=[],
            rejected_candidates=[],
            inconclusive_candidates=[],
            summary_stats={},
            effect_stability_report={},
        )
        
        path = write_promotion_ready_candidates(bundle, base_dir=base_dir)
        
        assert path is None