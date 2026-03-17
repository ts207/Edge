ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SHARED_VENV_PYTHON := $(abspath $(ROOT_DIR)/../..)/.venv/bin/python
PYTHON ?= $(if $(wildcard $(ROOT_DIR)/.venv/bin/python),$(ROOT_DIR)/.venv/bin/python,$(if $(wildcard $(SHARED_VENV_PYTHON)),$(SHARED_VENV_PYTHON),python3))
PYTHON_COMPILE ?= $(PYTHON)
RUFF ?= $(PYTHON) -m ruff
RUN_ALL := -m project.pipelines.run_all
CLEAN_SCRIPT := $(ROOT_DIR)/project/scripts/clean_data.sh

RUN_ID ?= discovery_2020_2025
SYMBOLS ?= BTCUSDT,ETHUSDT
# Discovery defaults support multi-symbol idea generation under one RUN_ID.
START ?= 2020-06-01
END ?= 2025-07-10
STRATEGIES ?=
ENABLE_CROSS_VENUE_SPOT_PIPELINE ?= 0
CHANGED_BASE ?= origin/main
CHANGED_HEAD ?= HEAD

.PHONY: help run baseline discover-blueprints discover-edges discover-edges-from-raw discover-hybrid golden-workflow golden-certification test test-fast lint format format-check style compile clean clean-runtime clean-all-data clean-repo debloat check-hygiene clean-hygiene governance pre-commit bench-pipeline benchmark-m0 minimum-green-gate

help:
	@echo "Primary Research Targets:"
	@echo "  discover-blueprints - Full research pipeline: Ingest -> Discovery -> Blueprints"
	@echo "  discover-edges      - Phase 2 discovery for all events"
	@echo "  discover-target     - Targeted discovery for specific symbols/events"
	@echo "                        Usage: make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK"
	@echo "  run                - Ingest + Clean + Features (Preparation only)"
	@echo "  baseline           - Full discovery + profitable strategy packaging"
	@echo "  golden-workflow    - Canonical end-to-end smoke workflow"
	@echo "  golden-certification - Golden workflow plus runtime certification manifest"
	@echo "  test-fast          - Run fast research test profile"
	@echo "  lint               - Ruff lint on changed Python files"
	@echo "  format-check       - Ruff formatter check on changed Python files"
	@echo "  format             - Ruff format changed Python files in-place"
	@echo "  style              - Run lint + format-check on changed Python files"
	@echo "  governance         - Audit specs and sync schemas"
	@echo "  benchmark-m0       - Emit (or execute) frozen M0 benchmark run matrix"
	@echo "  clean-all-data     - Wipe all data/lake and reports"
	@echo "  minimum-green-gate - Required baseline for platform stabilization"

minimum-green-gate:
	@echo "Running minimum green gate checks..."
	PYTHONPATH=. $(PYTHON) -m compileall -q project tests
	PYTHONPATH=. $(PYTHON) -m pytest tests/architecture
	PYTHONPATH=. $(PYTHON) project/scripts/spec_qa_linter.py
	PYTHONPATH=. $(PYTHON) project/scripts/detector_coverage_audit.py --md-out docs/generated/detector_coverage.md --json-out docs/generated/detector_coverage.json --check
	PYTHONPATH=. $(PYTHON) project/scripts/ontology_consistency_audit.py --output docs/generated/ontology_audit.json --check
	PYTHONPATH=. $(PYTHON) project/scripts/build_system_map.py --check
	PYTHONPATH=. $(PYTHON) project/scripts/run_golden_regression.py --run_id smoke_run
	PYTHONPATH=. $(PYTHON) project/scripts/run_golden_workflow.py
	@echo "Minimum green gate PASSED."
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

golden-certification:
	$(PYTHON) -m project.scripts.run_certification_workflow

governance:
	$(PYTHON) project/scripts/pipeline_governance.py --audit --sync

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
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

clean-runtime:
	$(CLEAN_SCRIPT) runtime

clean-all-data:
	$(CLEAN_SCRIPT) all

clean-repo:
	$(CLEAN_SCRIPT) repo

debloat: clean-repo

check-hygiene:
	bash $(ROOT_DIR)/project/scripts/check_repo_hygiene.sh

clean-data:
	$(PYTHON) $(ROOT_DIR)/project/scripts/clean_data.py --days 14

clean-hygiene:
	find $(ROOT_DIR) -type f \
		\( -name '*:Zone.Identifier' -o -name '*#Uf03aZone.Identifier' -o -name '*#Uf03aZone.Identifier:Zone.Identifier' \) \
		-print -delete
