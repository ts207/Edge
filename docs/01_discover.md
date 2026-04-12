# Discover

The discover stage performs bounded candidate generation.

Inputs:
- proposal or bounded hypothesis spec
- event family and template registries
- market data and feature frames

Outputs:
- discovery candidates
- stage metadata and diagnostics

Guardrail:
- discover may generate many candidates, but it does not assert live eligibility.
