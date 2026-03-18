# Operations And Guardrails

This document defines the default safety and operating rules for running research in the repository.

Use it to prevent broad, expensive, low-trust experimentation.

## Operating Priorities

Prefer:

1. narrow attribution
2. artifact cleanliness
3. post-cost relevance
4. reproducibility
5. operator clarity

Do not trade those away for output volume.

## Scope Guardrails

Default to:

- one event family before many
- one template family before many
- one primary context family before many
- one objective per run

Broadening is justified only after the narrow path is mechanically clean and still decision-relevant.

## Contract Guardrails

Do not interpret results when:

- manifests and logs disagree
- expected artifacts are missing
- generated diagnostics disagree with the owning code or registry surface
- warning noise hides runtime faults

Repair the path first.

## Synthetic Guardrails

Synthetic runs are for:

- detector truth recovery
- contract and artifact validation
- negative-control testing
- controlled regime stress

They are not direct proof of live profitability.

Keep these rules:

- freeze the profile before evaluation
- keep manifest and truth map with the run
- validate truth before interpretation
- prefer cross-profile survival over one strong world
- treat short windows as calibration unless real holdout support exists

## Promotion Guardrails

Promotion is a hard gate.

Do not treat attractive discovery output as promotion readiness.

Promotion should only be trusted when:

- the candidate contract is valid
- split support exists
- cost and stress quality survive
- the claim is narrow enough to explain

## Context Guardrails

Confidence-aware context is the default for production research.

That means:

- hard labels still exist for compatibility
- low-confidence or high-entropy regime rows should not be treated as fully trustworthy context
- hard-label mode should be used mainly as a comparison baseline

## Memory Guardrails

Do not keep rerunning a region because the wording changed.

Before repeating a similar slice, check:

- same event or family
- same template
- same context
- same fail gate

If nothing material changed, do not rerun by default.

## Review Checklist

Before calling a run meaningful, ask:

- is the question explicit
- is the path narrow enough
- do the artifacts reconcile
- are the split counts real
- do the costs still allow relevance
- is the next action explicit

## Stop Conditions

Stop and reassess when:

- a path remains mechanically unstable
- a clean rerun still fails on holdout
- promotion rejection is clear and repeated
- the next run would only restate the same failed claim
- the evidence is too weak to justify more scope
