from __future__ import annotations

import pandas as pd

from project.reliability.regression_checks import assert_bundle_policy_consistency


def test_bundle_policy_consistency():
    audit = pd.DataFrame({'candidate_id': ['c1'], 'promotion_decision': ['promoted']})
    decisions = pd.DataFrame({'candidate_id': ['c1'], 'promotion_decision': ['promoted']})
    assert_bundle_policy_consistency(audit, decisions)
