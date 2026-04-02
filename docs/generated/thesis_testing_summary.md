# Thesis testing summary

This is a governance-first Block B testing pass over the seed queue.
It scores ontology, implementation, invalidation clarity, and deployment readiness from current repo artifacts.
It does **not** claim that empirical holdout/confounder testing exists where the evidence source is still a contract fallback.

- candidates_reviewed: `13`
- decision_counts: `needs_more_evidence=12`, `needs_repair=1`

## Key conclusion

No candidate clears seed promotion under the current repo snapshot because the founding queue still lacks empirical evidence bundles, holdout checks, and confounder sanity checks.
This is the intended fail-closed behavior for Block B on a bootstrap-only inventory.

## Highest-scoring candidates

| Candidate | Total score | Decision | Evidence gaps | Next action |
|---|---:|---|---|---|
| THESIS_BASIS_DISLOC | 24 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_FND_DISLOC | 24 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_LIQUIDATION_CASCADE | 24 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_LIQUIDITY_VACUUM | 24 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_VOL_SHOCK | 24 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_BASIS_FND_CONFIRM | 23 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM | 23 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |
| THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM | 23 | needs_more_evidence | empirical_evidence_bundle_missing|holdout_check_missing|confounder_sanity_check_missing | run_empirical_event_study |

## Scoring rubric

Fields scored 0–5: ontology fidelity, implementation fidelity, evidence strength, regime clarity, invalidation clarity, confounder handling, holdout quality, deployment suitability.
