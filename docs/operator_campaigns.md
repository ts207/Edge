# Operator Campaigns

> [!WARNING]
> **Legacy Compatibility Surface**
> This relies on the older operator facade and is not the canonical public model. See the unified 4-stage pipeline for modern orchestration.

Campaigns are the repo’s bounded research-orchestration surface. They are not a shortcut around thesis lifecycle discipline.

## Current state

The repo now has a canonical campaign contract:

- `spec/campaigns/campaign_contract_v1.yaml`
- `project/research/campaign_contract.py`

The autonomous campaign controller writes its own contract artifact under the experiment output tree. Operator-facing campaign tools should be treated as wrappers or facades over that canonical contract, not as a parallel authority.

## Campaign loop

A campaign spec freezes the initial proposal and cycle budget. The engine then:

1. issues the initial proposal
2. writes operator outputs
3. classifies the result
4. chooses a bounded next action
5. mutates exactly one field for the next proposal
6. repeats until a stop condition is hit

## Campaign spec

```yaml
campaign_id: btc_volshock_campaign
initial_proposal: spec/proposals/btc_volshock.yaml
registry_root: project/configs/registries
max_cycles: 5
stop_conditions:
  max_fail_streak: 2
```

## Outputs

Campaign artifacts are written under:

- `data/artifacts/operator_campaigns/<campaign_id>/proposals/`
- `data/artifacts/operator_campaigns/<campaign_id>/reports/campaign_report.json`
- `data/artifacts/experiments/<program>/campaign_contract.json` or equivalent contract artifact path under the campaign output tree

Proposal memory and the evidence ledger are also updated with:

- `campaign_id`
- `cycle_number`
- `branch_id`
- `parent_run_id`
- `mutation_type`
- `branch_depth`
- `decision`

## Current mutation scope

The first pass keeps mutation narrow and deterministic:

- horizon shorten/extend
- entry lag plus/minus one
- direction flip

Each generated proposal includes a bounded block so the one-change rule remains enforced.

## Important boundary

Campaign outputs are inputs to the canonical lifecycle. A successful campaign cycle does not directly create a production-eligible thesis. The expected downstream path is:

`campaign output -> validate -> promote -> export -> thesis store`
