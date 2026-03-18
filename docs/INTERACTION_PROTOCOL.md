# Interaction Protocol

This document defines how a research operator or agent should communicate while using the repository.

The goal is not polished prose. The goal is clear decisions and visible uncertainty.

## The Three Inputs

Every interaction should keep track of three sources:

- the operator request
- the repository artifacts
- prior memory

Operator intent says what matters.
Artifacts say what actually happened.
Memory says what already failed, worked, or changed before.

## Default Pattern

Use this interaction pattern by default:

1. restate the objective in repo-native terms
2. inspect local evidence
3. name the next smallest informative action
4. execute or explain the constraint
5. summarize findings and the next decision

## What Must Be Made Explicit

Always make these points visible:

- the working objective
- the immediate next action
- important assumptions
- abnormal findings
- whether the conclusion is mechanical, statistical, or operational

Never hide uncertainty behind broad summaries.

## Artifact-First Rule

Artifacts are the source of truth.

Read evidence in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If those sources disagree, the disagreement is itself a finding.

## Memory Use

Before proposing a materially similar run, check memory for:

- the same event or family
- the same template
- the same symbol or timeframe
- the same context
- the same fail gate

If nothing material changed, default to not rerunning.

## Communication Rules During Execution

If a run is:

- partial
- replayed
- synthetic
- manually reconciled
- using a fallback or compatibility path

say so explicitly.

Do not make the operator infer those distinctions from filenames or logs.

## Run Summary Contract

After each meaningful run, summarize:

- what was run
- what passed
- what failed
- what is suspicious
- what the next best move is

The operator should not need to reconstruct the decision from raw logs.

## When To Escalate To The Operator

Ask for operator input only when:

- the choice changes risk materially
- a destructive action is required
- the evidence is insufficient for a defensible assumption

Otherwise, make the best evidence-backed choice and proceed.

## Synthetic Interaction Rules

When synthetic data is involved, always state:

- the active profile or workflow
- truth-validation status
- whether the conclusion is about detector recovery, pipeline mechanics, or synthetic profitability only

Do not phrase synthetic profitability as live-market evidence.
