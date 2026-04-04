# Migration Guide

This guide helps users transition from legacy terminology and commands to the canonical four-stage model.

## 1. Command Mapping

| Legacy Command | Canonical Replacement |
| :--- | :--- |
| `edge operator run` | `edge discover run` |
| `edge operator plan` | `edge discover plan` |
| `edge operator preflight` | `edge discover plan` |
| `edge operator compare` | `edge validate report` |
| `edge operator regime-report` | `edge validate report` |
| `edge operator diagnose` | `edge validate diagnose` |
| `edge pipeline run-all` | `edge discover run` (with full pipeline enabled) |

## 2. Terminology Mapping

| Legacy Term | Canonical Term |
| :--- | :--- |
| `trigger` | `anchor` |
| `state` | `filter` |
| `proposal` | `structured hypothesis` |
| `certification` | `promotion` |
| `strategy` | `thesis` |

## 3. Deprecation Schedule

* **Current Version**: Warnings enabled for all legacy commands.
* **Next Major Version**: Legacy commands will be disabled by default (behind a flag).
* **Future Version**: Legacy commands and `trigger`-based specs will be removed.

## 4. How to Migrate your Specs

In your YAML proposals:
1. Rename `trigger_type` to `anchor`.
2. Ensure `context_filters` are clearly distinguished from the `anchor`.
3. Update any internal documentation to refer to `theses` instead of `strategies`.
