# Sprint 5 Interface Specification

This document defines the canonical interface for the Edge repository, centering on the four-stage operating model: **discover → validate → promote → deploy**.

## 1. Canonical CLI Verbs

### `edge discover`
Focus: Broad candidate generation.
* `edge discover run`: (Formerly `operator run`) Execute discovery for a proposal.
* `edge discover plan`: (Formerly `operator plan`) Plan discovery without executing.
* `edge discover inspect <run_id>`: Inspect discovery artifacts.
* `edge discover list-artifacts <run_id>`: List discovery artifacts.

### `edge validate`
Focus: Truth-testing and robustness.
* `edge validate run <run_id>`: Run formal validation on a discovery run.
* `edge validate report <run_id>`: Build regime/stability reports.
* `edge validate diagnose <run_id>`: Build negative-result diagnostics.
* `edge validate inspect <run_id>`: Inspect validation bundle.

### `edge promote`
Focus: Packaging and governance.
* `edge promote run <run_id>`: Promote validated candidates to theses.
* `edge promote inspect <run_id>`: Inspect promotion audit.
* `edge promote export <run_id>`: Export promoted theses for live use.

### `edge deploy`
Focus: Runtime execution.
* `edge deploy paper`: Start paper trading session.
* `edge deploy live`: Start live trading session.
* `edge deploy status`: Show status of deployed theses.
* `edge deploy list-theses`: List available promoted theses.

---

## 2. Canonical Terminology

| Old Term | Canonical Term | Description |
| :--- | :--- | :--- |
| `trigger` | `anchor` | The event/transition/sequence that anchors a candidate. |
| `state` | `filter` | Predicates that filter when an anchor is valid. |
| `proposal` | `structured hypothesis` | The input spec before discovery. |
| `certification` | `promotion` | The act of approving a candidate for deployment. |
| `strategy` | `thesis` | A promoted and packaged alpha idea. |

---

## 3. Alias and Deprecation Policy

* **Alias**: Old commands will be preserved as subparsers under their old names but will internally call the new canonical verbs.
* **Warning**: A standard deprecation warning will be printed to `stderr` upon use of an old command.
* **Guidance**: The warning will include the exact canonical command to use instead.

---

## 4. Documentation Tree

* `README.md`: Overhaul to lead with the 4-stage model.
* `docs/00_overview.md`: System-wide staged workflow.
* `docs/01_discover.md`: Discovery stage details.
* `docs/02_validate.md`: Validation stage details.
* `docs/03_promote.md`: Promotion stage details.
* `docs/04_deploy.md`: Deployment stage details.
* `docs/05_data_foundation.md`: Lineage and artifact spec.
* `docs/06_core_concepts.md`: Semantic glossary.
* `docs/90_architecture.md`: Maintainer's module map.
* `docs/91_advanced_research.md`: Grammar, generators, internals.
* `docs/92_assurance_and_benchmarks.md`: Methodology and benchmarks.
