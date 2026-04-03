# Best practices and failure modes

This document is the operating discipline for bounded work.

## Best practices

### Author one claim, not a shopping list

If the proposal needs multiple symbols, multiple templates, or multiple incompatible interpretations to feel useful, it is probably two or more runs, not one.

### Use `explain` before `run`

`edge operator explain --proposal <proposal.yaml>` is the fastest way to catch a mismatch between the operator-facing hypothesis and the normalized internal proposal.

### Keep confirmation work explicitly bounded

If the run is a follow-up to a prior result, encode `bounded:` and compare against the baseline run after execution. Do not quietly widen the claim and still call it confirmation.

### Export and package are different decisions

Use export when one specific run should become runtime-readable thesis input.

Use package only when you are intentionally maintaining the advanced bootstrap/governance lane.

### Read mechanical truth before narrative summaries

Manifest first. Tables second. Markdown summaries last.

## Common failure modes

### Proposal looks bounded but still explodes combinatorially

Symptoms:

- large estimated hypothesis count
- multiple contexts or overlays quietly widening the run
- poor ability to explain the mechanism afterward

Fix:

- reduce dimensions
- make the one intended change explicit
- inspect the normalized proposal and experiment summary before rerunning

### Clean exit mistaken for signal

Symptoms:

- run completed
- artifacts exist
- no candidate or no promotion survival

Fix:

- separate mechanical success from research success
- inspect phase-2 and promotion outputs before drawing conclusions

### Good candidate mistaken for runtime-ready thesis

Symptoms:

- one row looks strong
- someone assumes runtime may use it immediately

Fix:

- confirm promotion survival
- export the run explicitly
- inspect `deployment_state` on the exported batch

### Promotion class mistaken for trading permission

Symptoms:

- `seed_promoted` or `paper_promoted` interpreted as “safe to trade”

Fix:

- answer the permission question from `deployment_state`
- keep promotion class as supporting evidence context only

### Stale generated docs mistaken for implementation truth

Symptoms:

- generated markdown lags behind code or artifacts
- conclusions are drawn from the markdown alone

Fix:

- inspect manifests, thesis batches, and source code first
- regenerate generated docs when inventory surfaces changed

## Practical checklist

Before running:

- is the proposal one clear claim
- does `explain` match intent
- is the data window intentional
- is the bounded baseline explicit if this is confirmation work

After planning:

- is the estimated hypothesis count still bounded
- are required detectors, features, and states understood
- does the generated experiment bundle make sense

After running:

- did the manifest reconcile
- did the strongest rows survive promotion
- is the next action repair, confirm, kill, export, or package
