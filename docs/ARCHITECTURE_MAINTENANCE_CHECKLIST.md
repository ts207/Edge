# Architecture Maintenance Checklist

## Contracts and Generated Docs

- Regenerate contract-backed artifacts when registry, ontology, or lifecycle boundaries change.
- Keep `docs/generated/` aligned with the owning builder scripts.
- Treat generated outputs as snapshots of current repo structure, not hand-edited sources.

## Research Services and Wrappers

- Keep canonical behavior in service-layer modules and thin wrappers at the edges.
- Remove dead compatibility entrypoints instead of leaving dormant maintenance paths.
- Verify docs and plugin wrappers teach the canonical `discover -> validate -> promote -> deploy` flow.

## Strategy Surfaces

- Keep frozen strategy/DSL compatibility surfaces on their documented allowlist.
- Avoid introducing new import paths into deprecated strategy surfaces without explicit approval.
- Prefer runtime-facing thesis contracts over parallel strategy abstractions.

## Metrics and Guardrails

- Refresh architecture metrics when intentional structural changes land.
- Investigate threshold increases before raising guardrails, and record the reason in code review.
- Keep validation targets runnable in the current checkout without depending on writable in-tree caches.
