from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AllocationFairnessSummary:
    metric: str
    group_totals: dict[str, float]
    group_shares: dict[str, float]
    total_allocation: float
    min_group: str | None
    min_group_share: float | None
    max_group: str | None
    max_group_share: float | None
    share_gap: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AllocationFairnessAnalyzer:
    """Governed analyzer for allocation and resource-share fairness."""

    def summarize(
        self,
        metric: str,
        values_by_group: dict[str, list[float]],
    ) -> AllocationFairnessSummary:
        group_totals = {
            group: float(sum(values))
            for group, values in values_by_group.items()
            if values
        }
        total_allocation = float(sum(group_totals.values()))

        if total_allocation > 0.0:
            group_shares = {
                group: total / total_allocation
                for group, total in group_totals.items()
            }
        else:
            group_shares = {group: 0.0 for group in group_totals}

        min_group = None
        min_group_share = None
        max_group = None
        max_group_share = None
        share_gap = None

        if group_shares:
            ordered = sorted(group_shares.items(), key=lambda item: item[1])
            min_group, min_group_share = ordered[0]
            max_group, max_group_share = ordered[-1]
            share_gap = max_group_share - min_group_share

        return AllocationFairnessSummary(
            metric=metric,
            group_totals=group_totals,
            group_shares=group_shares,
            total_allocation=total_allocation,
            min_group=min_group,
            min_group_share=min_group_share,
            max_group=max_group,
            max_group_share=max_group_share,
            share_gap=share_gap,
        )
