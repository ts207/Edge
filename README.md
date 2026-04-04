# Edge: Alpha Discovery & Runtime

Edge is a staging system for crypto alpha discovery, validation, promotion, and deployment.

`discover → validate → promote → deploy`

## 1. The Four Stages

### 1. **Discover**
Broad candidate generation. We anchor research ideas to specific market events and filter them through state/regime predicates.
* **Input**: Structured Hypothesis (Proposal)
* **Output**: Candidates Table

### 2. **Validate**
Aggressive truth-testing. We subject candidates to falsification tests, cost-sensitivity analysis, and regime stability checks.
* **Input**: Candidates
* **Output**: Validated Candidates & Validation Bundle

### 3. **Promote**
Packaging and governance. We decide which robust candidates are ready for inventory based on retail profile and business objectives.
* **Input**: Validated Candidates
* **Output**: Promoted Theses

### 4. **Deploy**
Runtime execution. We run promoted theses in paper or live mode with explicit risk controls.
* **Input**: Promoted Theses
* **Output**: Live PnL & Execution Attribution

---

## 2. Core Concepts

* **Anchor**: The event (e.g., VOL_SHOCK) or transition that defines an edge.
* **Filter**: Contextual state or regime predicates that narrow when an anchor is active.
* **Sampling Policy**: Rules for how many times an edge can trigger (e.g., once per episode).
* **Validated Candidate**: A candidate that has passed all statistical truth-testing.
* **Promoted Thesis**: A packaged alpha idea ready for execution.

---

## 3. Quickstart

### Step 1: Discover Candidates
```bash
edge discover run --proposal spec/proposals/my_alpha.yaml
```

### Step 2: Validate Results
```bash
edge validate run --run_id <run_id>
```

### Step 3: Promote to Thesis
```bash
edge promote run --run_id <run_id> --symbols BTC
```

### Step 4: Deploy (Paper)
```bash
edge deploy paper --run_id <run_id>
```

---

## 4. Documentation

Detailed stage-by-stage documentation can be found in `docs/`:

* [System Overview](docs/00_overview.md)
* [Stage 1: Discover](docs/01_discover.md)
* [Stage 2: Validate](docs/02_validate.md)
* [Stage 3: Promote](docs/03_promote.md)
* [Stage 4: Deploy](docs/04_deploy.md)
* [Core Concepts & Glossary](docs/06_core_concepts.md)

---

## 5. Compatibility Note

Legacy commands (`operator`, `pipeline`) are still supported but deprecated. Please migrate to the new canonical verbs.
