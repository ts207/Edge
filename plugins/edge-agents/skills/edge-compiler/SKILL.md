---
name: edge-compiler
description: Compile a frozen Edge mechanism hypothesis into repo-native proposal YAML and exact commands using the repo's compiler spec. Use when a bounded hypothesis is ready for translation, plan-only validation, and controlled execution.
---

# Edge Compiler

This skill follows `agents/compiler.md`.

## Read first

1. `agents/compiler.md`
2. `agents/handoffs/mechanism_hypothesis_to_compiler.md`
3. `project/research/agent_io/proposal_schema.py`

## Required checks before compiling

- event exists in canonical registry
- template is valid for the event family
- regime exists in routing
- horizons are valid for the proposal path
- `entry_lags >= 1`
- search controls stay within `project/configs/registries/search_limits.yaml`

## Important horizon rule

- Proposal compilation uses the integer-bar path.
- The search-engine validator only accepts a narrower label set.
- Accept positive integer `horizons_bars`, but warn if they are non-canonical.
- Do not silently rewrite horizons.

## Required output

- proposal path under `spec/proposals/`
- full proposal YAML
- translation command
- plan-only command
- execution command
- explicit plan review checklist

## Do not do

- do not modify the hypothesis to make it fit
- do not add events, templates, or regimes
- do not imply that proposal execution equals thesis promotion
