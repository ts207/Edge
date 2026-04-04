# Advanced Research

This document covers internal research tools and methodologies that are not part of the standard four-stage workflow.

## Search Generation
Edge includes tools for automated hypothesis generation using a grammar-based approach.
* **Ontology**: Definition of valid market events and states.
* **Generator**: Engine that samples from the ontology to produce structured hypotheses.

## Synthetic Truth
Tools for generating synthetic price data with known ground-truth edges. These are used to calibrate validation gates and ensure they can correctly distinguish signal from noise.

## Advanced Diagnostics
* **Multiplicity Control**: Tools for handling False Discovery Rate (FDR) across large search spaces.
* **Clustered Bootstrap**: Methodology for assessing dependency across overlapping alpha windows.
