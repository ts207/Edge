# Core Concepts & Glossary

This doc is the canonical glossary for Edge terminology.

## 1. Semantic Model

### Anchor
The market event or price transition that defines the start of an alpha window.
* Examples: `VOL_SHOCK`, `OI_SPIKE`, `BREAKOUT`.

### Filter
Contextual predicates that must be true for an anchor to be valid. Filters define the "where" and "when".
* Examples: `regime == "volatile"`, `trend == "up"`.

### Sampling Policy
Rules that govern how many observations are extracted from an episode.
* Examples: `episodic`, `once_per_episode`, `every_n_bars`.

### Template
The logic that defines the entry/exit behavior once an anchor is triggered.

## 2. Research Objects

### Structured Hypothesis
(Formerly *Proposal*) The input specification for a discovery run, containing the anchor, filters, and template.

### Candidate
A specific set of parameters (anchor + filters + template + horizon) that showed potential in the Discovery stage.

### Validated Candidate
A candidate that has passed all statistical gates in the Validation stage.

### Promoted Thesis
(Formerly *Promoted Strategy*) A validated candidate that has been approved for deployment and packaged with governance metadata.

## 3. Stages

* **Discover**: Candidate generation.
* **Validate**: Truth-testing and falsification.
* **Promote**: Packaging and governance.
* **Deploy**: Runtime execution.
