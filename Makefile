ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SHARED_VENV_PYTHON := $(abspath $(ROOT_DIR)/../..)/.venv/bin/python
PYTHON ?= $(if $(wildcard $(ROOT_DIR)/.venv/bin/python),$(ROOT_DIR)/.venv/bin/python,$(if $(wildcard $(SHARED_VENV_PYTHON)),$(SHARED_VENV_PYTHON),python3))
PYTHON_COMPILE ?= $(PYTHON)
RUFF ?= $(PYTHON) -m ruff
RUN_ALL := -m project.pipelines.run_all
CLEAN_SCRIPT := $(ROOT_DIR)/project/scripts/clean_data.sh

RUN_ID ?= discovery_2021_2022
SYMBOLS ?= BTCUSDT,ETHUSDT
# Discovery defaults support multi-symbol idea generation under one RUN_ID.
START ?= 2021-01-01
END ?= 2022-12-31
STRATEGIES ?=
ENABLE_CROSS_VENUE_SPOT_PIPELINE ?= 0
CHANGED_BASE ?= origin/main
CHANGED_HEAD ?= HEAD

.PHONY: help discover export package validate review run baseline discover-blueprints discover-edges discover-edges-from-raw discover-hybrid golden-workflow golden-certification test test-fast lint format format-check style compile clean clean-runtime clean-all-data clean-repo debloat check-hygiene clean-hygiene governance pre-commit bench-pipeline benchmark-m0 minimum-green-gate benchmark-maintenance-smoke benchmark-maintenance

help:
	@echo "Operator actions:"
	@echo "  discover           - Canonical bounded research entry. Usage: make discover PROPOSAL=spec/proposals/canonical_event_hypothesis_h24.yaml DISCOVER_ACTION=plan|run"
	@echo "  validate           - Canonical validation surface. Usage: make validate RUN_ID=<run_id>"
	@echo "  promote            - Canonical promotion surface. Usage: make promote RUN_ID=<run_id> SYMBOLS=BTCUSDT"
	@echo "  export             - Canonical runtime-batch export. Usage: make export RUN_ID=<run_id>"
	@echo "  deploy-paper       - Canonical deployment (Paper). Usage: make deploy-paper RUN_ID=<run_id>"
	@echo "  review             - Post-run review. Usage: make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|report or make review REVIEW_ACTION=compare RUN_IDS=run_a,run_b"
	@echo "  legacy-validate    - Legacy: contracts + minimum green gate"
	@echo "  package            - Advanced maintenance: bootstrap packaging lane, not the canonical runtime-batch path"
	@echo ""
	@echo "Advanced workflow bundles:"
	@echo "  discover-blueprints - Full research pipeline: Ingest -> Discovery -> Blueprints"
	@echo "  discover-edges      - Phase 2 discovery for all events"
	@echo "  discover-target     - Targeted discovery for specific symbols/events"
	@echo "                        Usage: make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK"
	@echo "  run                 - Ingest + Clean + Features (Preparation only)"
	@echo "  baseline            - Full discovery + profitable strategy packaging"
	@echo "  golden-workflow     - Canonical end-to-end smoke workflow"
	@echo "  golden-certification - Golden workflow plus runtime certification manifest"
	@echo ""
	@echo "Maintenance and quality:"
	@echo "  test-fast          - Run fast research test profile"
	@echo "  lint               - Ruff lint on changed Python files"
	@echo "  format-check       - Ruff formatter check on changed Python files"
	@echo "  format             - Ruff format changed Python files in-place"
	@echo "  style              - Run lint + format-check on changed Python files"
	@echo "  governance         - Audit specs and sync schemas"
	@echo "  benchmark-m0       - Emit (or execute) frozen M0 benchmark run matrix"
	@echo "  benchmark-maintenance-smoke - End-to-end dry-run of the benchmark governance cycle"
	@echo "  benchmark-maintenance - Full production execution of the benchmark governance cycle"
	@echo "  clean-all-data     - Wipe all data/lake and reports"
	@echo "  minimum-green-gate - Required baseline for platform stabilization"

benchmark-maintenance-smoke:
	@echo "Running benchmark maintenance dry-run..."
	@mkdir -p /tmp/edgee_smoke_out
	PYTHONPATH=. $(PYTHON) project/scripts/run_benchmark_maintenance_cycle.py --execute 0 | tee /tmp/edgee_smoke_out/cycle_output.txt
	@echo "Reviewing smoke reports..."
	@TARGET_DIR=$$(grep "CYCLE_OUTPUT_DIR: " /tmp/edgee_smoke_out/cycle_output.txt | cut -d' ' -f2); \
	PYTHONPATH=. $(PYTHON) project/scripts/show_benchmark_review.py --path $$TARGET_DIR/benchmark_review.json; \
	PYTHONPATH=. $(PYTHON) project/scripts/show_promotion_readiness.py --review $$TARGET_DIR/benchmark_review.json --cert $$TARGET_DIR/benchmark_certification.json
	@rm -rf /tmp/edgee_smoke_out
	@echo "Benchmark maintenance smoke check PASSED."

benchmark-maintenance:
	@echo "Executing full benchmark maintenance cycle..."
	PYTHONPATH=. $(PYTHON) project/scripts/run_benchmark_maintenance_cycle.py --execute 1
	@echo "Maintenance cycle COMPLETE. Reviewing results:"
	PYTHONPATH=. $(PYTHON) project/scripts/show_benchmark_review.py --path data/reports/benchmarks/latest/benchmark_review.json
	PYTHONPATH=. $(PYTHON) project/scripts/show_promotion_readiness.py --review data/reports/benchmarks/latest/benchmark_review.json --cert data/reports/benchmarks/latest/benchmark_certification.json

minimum-green-gate:
	@echo "Running minimum green gate checks..."
	PYTHONPATH=. $(PYTHON) -m compileall -q project project/tests
	PYTHONPATH=. $(PYTHON) -m pytest project/tests/architecture
	PYTHONPATH=. $(PYTHON) project/scripts/spec_qa_linter.py
	PYTHONPATH=. $(PYTHON) project/scripts/detector_coverage_audit.py --md-out docs/generated/detector_coverage.md --json-out docs/generated/detector_coverage.json --check
	PYTHONPATH=. $(PYTHON) project/scripts/ontology_consistency_audit.py --output docs/generated/ontology_audit.json --check
	PYTHONPATH=. $(PYTHON) project/scripts/build_event_contract_artifacts.py --check
	PYTHONPATH=. $(PYTHON) project/scripts/event_ontology_audit.py --check
	PYTHONPATH=. $(PYTHON) project/scripts/build_event_ontology_artifacts.py --check
	PYTHONPATH=. $(PYTHON) project/scripts/build_system_map.py --check
	PYTHONPATH=. $(PYTHON) project/scripts/build_architecture_metrics.py --check
	PYTHONPATH=. $(PYTHON) -m pytest -q \
		project/tests/regressions/test_monitor_only_venue_immutability.py \
		project/tests/regressions/test_run_success_requires_outputs.py \
		project/tests/regressions/test_stage_registry_path_validity.py
	PYTHONPATH=. $(PYTHON) project/scripts/run_golden_regression.py --run_id smoke_run
	PYTHONPATH=. $(PYTHON) project/scripts/run_golden_workflow.py
	@echo "Minimum green gate PASSED."


DISCOVER_ACTION ?= plan
REVIEW_ACTION ?= diagnose
PROPOSAL ?=
RUN_IDS ?=
INTERNAL_BOOTSTRAP_THESIS_RUN_ID ?= seed_founding_batch_v1
RUN_ID ?=

discover:
	@if [ -z "$(PROPOSAL)" ]; then echo "Usage: make discover PROPOSAL=path/to/proposal.yaml DISCOVER_ACTION=plan|run"; exit 2; fi
	@if [ "$(DISCOVER_ACTION)" != "plan" ] && [ "$(DISCOVER_ACTION)" != "run" ]; then echo "DISCOVER_ACTION must be one of: plan, run"; exit 2; fi
	PYTHONPATH=. $(PYTHON) -m project.cli discover $(DISCOVER_ACTION) --proposal $(PROPOSAL)

validate:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make validate RUN_ID=<run_id>"; exit 2; fi
	PYTHONPATH=. $(PYTHON) -m project.cli validate run --run_id $(RUN_ID)

promote:
	@if [ -z "$(RUN_ID)" ] || [ -z "$(SYMBOLS)" ]; then echo "Usage: make promote RUN_ID=<run_id> SYMBOLS=BTCUSDT"; exit 2; fi
	PYTHONPATH=. $(PYTHON) -m project.cli promote run --run_id $(RUN_ID) --symbols $(SYMBOLS)

export:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make export RUN_ID=<run_id>"; exit 2; fi
	PYTHONPATH=. $(PYTHON) -m project.cli promote export --run_id $(RUN_ID)

deploy-paper:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make deploy-paper RUN_ID=<run_id>"; exit 2; fi
	PYTHONPATH=. $(PYTHON) -m project.cli deploy paper --run_id $(RUN_ID)

package:
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_seed_bootstrap_artifacts
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_seed_testing_artifacts
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_seed_empirical_artifacts
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_founding_thesis_evidence
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_seed_packaging_artifacts
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_structural_confirmation_artifacts
	PYTHONPATH=. $(PYTHON) -m project.scripts.build_thesis_overlap_artifacts --run_id $(INTERNAL_BOOTSTRAP_THESIS_RUN_ID)
	./project/scripts/regenerate_artifacts.sh

legacy-validate:
	PYTHONPATH=. $(PYTHON) -m project.scripts.run_researcher_verification --mode contracts
	$(MAKE) minimum-green-gate

review:
	@if [ "$(REVIEW_ACTION)" = "compare" ]; then \
		if [ -z "$(RUN_IDS)" ]; then echo "Usage: make review REVIEW_ACTION=compare RUN_IDS=run_a,run_b"; exit 2; fi; \
		PYTHONPATH=. $(PYTHON) -m project.cli catalog compare --run_id_a $$(echo $(RUN_IDS) | cut -d, -f1) --run_id_b $$(echo $(RUN_IDS) | cut -d, -f2) --stage validate; \
	else \
		if [ -z "$(RUN_ID)" ]; then echo "Usage: make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|report"; exit 2; fi; \
		if [ "$(REVIEW_ACTION)" != "diagnose" ] && [ "$(REVIEW_ACTION)" != "report" ]; then echo "REVIEW_ACTION must be one of: diagnose, report, compare"; exit 2; fi; \
		PYTHONPATH=. $(PYTHON) -m project.cli validate $(REVIEW_ACTION) --run_id $(RUN_ID); \
	fi
TIMEFRAMES ?= 5m
CONCEPT ?= 

.PHONY: discover-target
discover-target:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(if $(RUN_ID),$(RUN_ID),discovery_$(shell date +%Y%m%d_%H%M%S)) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--timeframes $(TIMEFRAMES) \
		--run_phase2_conditional 1 \
		--phase2_event_type $(EVENT) \
		--run_edge_candidate_universe 1 \
		--run_strategy_builder 0 \
		--run_recommendations_checklist 0

.PHONY: discover-concept
discover-concept:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(if $(RUN_ID),$(RUN_ID),concept_$(shell date +%Y%m%d_%H%M%S)) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--timeframes $(TIMEFRAMES) \
		--concept $(CONCEPT) \
		--run_phase2_conditional 1 \
		--run_edge_candidate_universe 1 \
		--run_strategy_builder 0 \
		--run_recommendations_checklist 0 \
		--strategy_blueprint_ignore_checklist 1 \
		--strategy_blueprint_allow_fallback 0 \
		--run_ingest_liquidation_snapshot 0 \
		--run_ingest_open_interest_hist 0

discover-blueprints:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--run_phase2_conditional 1 \
		--phase2_event_type all \
		--run_edge_candidate_universe 1 \
		--run_strategy_blueprint_compiler 1 \
		--run_strategy_builder 1 \
		--run_recommendations_checklist 1

run:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END)

baseline:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--run_phase2_conditional 1 \
		--phase2_event_type all \
		--run_edge_candidate_universe 1 \
		--run_strategy_blueprint_compiler 1 \
		--run_strategy_builder 1 \
		--run_recommendations_checklist 1 \
		--run_profitable_selector 1

golden-workflow:
	$(PYTHON) -m project.scripts.run_golden_workflow

golden-synthetic-discovery:
	$(PYTHON) -m project.scripts.run_golden_synthetic_discovery

synthetic-demo:
	$(PYTHON) -m project.scripts.run_demo_synthetic_proposal

golden-certification:
	$(PYTHON) -m project.scripts.run_certification_workflow

governance:
	$(PYTHON) project/scripts/pipeline_governance.py --audit --sync
	PYTHONPATH=. $(PYTHON) project/scripts/build_event_contract_artifacts.py
	PYTHONPATH=. $(PYTHON) project/scripts/event_ontology_audit.py
	PYTHONPATH=. $(PYTHON) project/scripts/build_event_ontology_artifacts.py

pre-commit:
	bash project/scripts/pre_commit.sh

discover-edges:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--run_phase2_conditional 1 \
		--phase2_event_type all \
		--run_edge_candidate_universe 1 \
		--run_strategy_builder 0 \
		--run_recommendations_checklist 0 \
		--strategy_blueprint_ignore_checklist 1 \
		--strategy_blueprint_allow_fallback 0 \
		--run_ingest_liquidation_snapshot 0 \
		--run_ingest_open_interest_hist 0

discover-edges-from-raw:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--skip_ingest_ohlcv 1 \
		--skip_ingest_funding 1 \
		--skip_ingest_spot_ohlcv 1 \
		--enable_cross_venue_spot_pipeline $(ENABLE_CROSS_VENUE_SPOT_PIPELINE) \
		--run_phase2_conditional 1 \
		--phase2_event_type all \
		--run_edge_candidate_universe 1 \
		--run_strategy_builder 0 \
		--run_recommendations_checklist 0

discover-hybrid:
	$(PYTHON) $(RUN_ALL) \
		--run_id $(RUN_ID) \
		--symbols $(SYMBOLS) \
		--start $(START) \
		--end $(END) \
		--run_phase2_conditional 1 \
		--phase2_event_type all \
		--run_edge_candidate_universe 1 \
		--run_expectancy_analysis 1 \
		--run_expectancy_robustness 1

test:
	$(PYTHON) -m pytest -q

test-fast:
	$(PYTHON) -m pytest -q -m "not slow" --maxfail=1

lint:
	@base="$(CHANGED_BASE)"; \
	if ! git rev-parse --verify --quiet "$$base" >/dev/null; then \
		base="HEAD~1"; \
	fi; \
	files="$$(git diff --name-only --diff-filter=ACMR "$$base" "$(CHANGED_HEAD)" -- '*.py')"; \
	if [ -z "$$files" ]; then \
		echo "No changed Python files to lint."; \
		exit 0; \
	fi; \
	echo "Linting changed Python files:"; \
	echo "$$files"; \
	$(RUFF) check --select E9,F63,F7,F82 $$files

format-check:
	@base="$(CHANGED_BASE)"; \
	if ! git rev-parse --verify --quiet "$$base" >/dev/null; then \
		base="HEAD~1"; \
	fi; \
	files="$$(git diff --name-only --diff-filter=ACMR "$$base" "$(CHANGED_HEAD)" -- '*.py')"; \
	if [ -z "$$files" ]; then \
		echo "No changed Python files to format-check."; \
		exit 0; \
	fi; \
	echo "Format-checking changed Python files:"; \
	echo "$$files"; \
	$(RUFF) format --check $$files

format:
	@base="$(CHANGED_BASE)"; \
	if ! git rev-parse --verify --quiet "$$base" >/dev/null; then \
		base="HEAD~1"; \
	fi; \
	files="$$(git diff --name-only --diff-filter=ACMR "$$base" "$(CHANGED_HEAD)" -- '*.py')"; \
	if [ -z "$$files" ]; then \
		echo "No changed Python files to format."; \
		exit 0; \
	fi; \
	echo "Formatting changed Python files:"; \
	echo "$$files"; \
	$(RUFF) format $$files

style: lint format-check

monitor:
	$(PYTHON) project/scripts/monitor_data_freshness.py --symbols $(or $(SYMBOLS),BTCUSDT,ETHUSDT) --timeframe 5m --max_staleness_bars 3

bench-pipeline:
	$(PYTHON) project/scripts/benchmark_pipeline.py

benchmark-m0:
	$(PYTHON) project/scripts/run_benchmark_matrix.py --matrix spec/benchmarks/retail_m0_matrix.yaml --execute $(or $(EXECUTE),0)


compile:
	$(PYTHON_COMPILE) -m compileall $(ROOT_DIR)/project

clean:
	$(CLEAN_SCRIPT) repo

clean-runtime:
	$(CLEAN_SCRIPT) runtime

clean-all-data:
	$(CLEAN_SCRIPT) all

clean-repo: clean

debloat: clean-repo

clean-run-data:
	$(CLEAN_SCRIPT) data

check-hygiene:
	bash $(ROOT_DIR)/project/scripts/check_repo_hygiene.sh

clean-hygiene:
	$(CLEAN_SCRIPT) hygiene
