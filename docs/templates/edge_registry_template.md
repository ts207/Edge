# Edge Registry Template

| hypothesis_id | program_id | canonical_regime | primary_event_family | template_family | tradable_expression | status | evidence_strength | latest_run_id | cost_survivability | execution_realism | drift_sensitivity | artifact_trust | promotion_state | next_action | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hyp_example | btc_campaign | BASIS_FUNDING_DISLOCATION | FUNDING_NORMALIZATION_TRIGGER | basis_repair | spot_rebound_filtered_by_futures_state | modify | weak | run_20260329_x | mixed | partial | high | valid | not_promoted | explore | Narrow to one funding-window slice and re-run with the same regime and expression. |

## Field Meanings

- `status`
  - `new`, `active`, `held`, `killed`, `promoted`, `escalated`
- `evidence_strength`
  - `weak`, `moderate`, `strong`
- `cost_survivability`
  - `failed`, `mixed`, `passed`
- `execution_realism`
  - `low`, `partial`, `credible`
- `drift_sensitivity`
  - `high`, `medium`, `low`
- `artifact_trust`
  - `invalid`, `partial`, `valid`
- `promotion_state`
  - `not_reviewed`, `reviewed_not_promoted`, `promoted`
- `next_action`
  - `explore`, `repair`, `hold`, `stop`, `exploit`
