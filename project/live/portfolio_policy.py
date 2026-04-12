from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set


@dataclass(frozen=True)
class AdmissionResult:
    admissible: bool
    reason: str
    winner_id: str | None = None

class PortfolioAdmissionPolicy:
    def resolve_overlap_winners(
        self,
        candidates: List[Dict[str, Any]],
        active_groups: Set[str]
    ) -> List[Dict[str, Any]]:
        def ranking_key(c):
            return (
                float(c.get("support_score", 0.0)) - float(c.get("contradiction_penalty", 0.0)),
                int(c.get("sample_size", 0)),
                str(c.get("thesis_id", ""))
            )

        eligible = [
            c for c in candidates
            if str(c.get("overlap_group_id", "")).strip() not in active_groups
        ]

        if not eligible:
            return []

        sorted_candidates = sorted(eligible, key=ranking_key, reverse=True)
        winners = []
        seen_in_batch = set()

        for c in sorted_candidates:
            group_id = str(c.get("overlap_group_id", "")).strip()
            if not group_id or group_id not in seen_in_batch:
                if group_id:
                    seen_in_batch.add(group_id)
                winners.append(c)
        return winners

    def is_thesis_admissible(
        self,
        thesis_id: str,
        overlap_group_id: str,
        active_groups: Set[str]
    ) -> AdmissionResult:
        group_id = str(overlap_group_id).strip()
        if group_id and group_id in active_groups:
            return AdmissionResult(False, "blocked_by_active_group_member")
        return AdmissionResult(True, "selected_as_group_winner", winner_id=thesis_id)
