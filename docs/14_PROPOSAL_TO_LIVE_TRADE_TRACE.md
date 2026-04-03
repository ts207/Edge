# Proposal to live-trade trace

This document traces the full path from one proposal to possible live trading eligibility.

The key distinction is simple:

- a run can exist
- a thesis batch can be exported
- runtime permission can still remain blocked

Those are separate states.

## The full chain

`single hypothesis proposal -> normalized AgentProposal -> validated plan -> run -> review -> export thesis batch -> explicit runtime selection -> deployment-state gate -> possible trading runtime`

## 1. Proposal authoring

The operator-facing proposal is authored as one atomic hypothesis.

Canonical example:

- [`spec/proposals/canonical_event_hypothesis_h24.yaml`](/home/irene/Edge/spec/proposals/canonical_event_hypothesis_h24.yaml)

The loader validates the single-hypothesis shape strictly and compiles it into legacy `AgentProposal`.

Important implication:

the front door is simplified, but downstream experiment code still works on the same normalized contract it used before.

## 2. Normalization and explanation

`edge operator explain --proposal <proposal.yaml>` shows:

- proposal format
- normalized `AgentProposal`
- compiled trigger space
- resolved experiment summary

This is the first checkpoint that proves the operator-facing hypothesis compiled into the intended internal contract.

## 3. Preflight and plan

`edge operator preflight` checks whether the proposal is valid and locally runnable.

`edge operator plan` turns it into:

- `experiment.yaml`
- `run_all_overrides.json`
- required detectors, features, and states
- estimated hypothesis count

At this point the repo has a validated research contract, but not yet a run.

## 4. Proposal issuance and run execution

`edge operator run --proposal <proposal.yaml>`:

1. loads and normalizes the proposal
2. validates any bounded baseline relationship
3. writes proposal memory
4. creates a run id
5. invokes `project.pipelines.run_all`
6. writes run-scoped artifacts

Primary durable artifact:

- `data/runs/<run_id>/run_manifest.json`

## 5. Research and promotion outputs

The run writes:

- phase-2 outputs under `data/reports/phase2/<run_id>/`
- promotion outputs under `data/reports/promotions/<run_id>/`
- operator summaries under `data/reports/operator/<run_id>/`

These surfaces determine whether the result should be repaired, confirmed, killed, or exported.

## 6. Export to a thesis batch

If the run deserves runtime-readable output, export it explicitly:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

This writes:

- `data/live/theses/<run_id>/promoted_theses.json`

That exported batch is the canonical runtime artifact.

## 7. Optional explicit promotion-to-runtime bridge

Export may also record named runtime registrations or explicit deployment-state changes:

```bash
python -m project.research.export_promoted_theses \
  --run_id <run_id> \
  --register-runtime <name> \
  --set-deployment-state <thesis_id_or_candidate_id>=live_enabled
```

This is explicit and auditable. It is not an automatic consequence of promotion.

## 8. Runtime selection

Runtime must be pointed at the batch explicitly through:

- `strategy_runtime.thesis_path`
- or `strategy_runtime.thesis_run_id`

Implicit latest-batch resolution is not part of the normal path.

## 9. Trading permission

Even after export and explicit selection, runtime may only trade when the selected thesis carries:

- `deployment_state=live_enabled`

`monitor_only` and `paper_only` remain non-trading states.

That is why:

- promotion does not imply trading
- export does not imply trading
- runtime selection does not imply trading

Only deployment state answers the final permission question.

## Practical conclusion

The clean operating story is:

one proposal becomes one bounded run; one run may become one exported thesis batch; one explicitly selected thesis batch may reach trading only if deployment state allows it.
