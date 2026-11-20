from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GroupDriftSummary:
    group: str
    baseline_mean: float | None
    current_mean: float | None
    delta: float | None


@dataclass(frozen=True)
class FairnessDriftSummary:
    metric: str
    groups: dict[str, GroupDriftSummary]
    baseline_overall_mean: float | None
    current_overall_mean: float | None
    overall_delta: float | None
    max_absolute_group_drift: float | None
    most_shifted_group: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "groups": {name: asdict(summary) for name, summary in self.groups.items()},
            "baseline_overall_mean": self.baseline_overall_mean,
            "current_overall_mean": self.current_overall_mean,
            "overall_delta": self.overall_delta,
            "max_absolute_group_drift": self.max_absolute_group_drift,
            "most_shifted_group": self.most_shifted_group,
        }


class FairnessDriftAnalyzer:
    """Governed analyzer for drift and shift across fairness snapshots."""

    def summarize(
        self,
        metric: str,
        baseline_values_by_group: dict[str, list[float]],
        current_values_by_group: dict[str, list[float]],
    ) -> FairnessDriftSummary:
        all_groups = sorted(set(baseline_values_by_group) | set(current_values_by_group))
        groups: dict[str, GroupDriftSummary] = {}
        max_absolute_group_drift = None
        most_shifted_group = None

        for group in all_groups:
            baseline_values = baseline_values_by_group.get(group, [])
            current_values = current_values_by_group.get(group, [])
            baseline_mean = (sum(baseline_values) / len(baseline_values)) if baseline_values else None
            current_mean = (sum(current_values) / len(current_values)) if current_values else None
            delta = None
            if baseline_mean is not None and current_mean is not None:
                delta = current_mean - baseline_mean
                abs_delta = abs(delta)
                if max_absolute_group_drift is None or abs_delta > max_absolute_group_drift:
                    max_absolute_group_drift = abs_delta
                    most_shifted_group = group

            groups[group] = GroupDriftSummary(
                group=group,
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                delta=delta,
            )

        baseline_overall_mean = self._overall_mean(baseline_values_by_group)
        current_overall_mean = self._overall_mean(current_values_by_group)
        overall_delta = None
        if baseline_overall_mean is not None and current_overall_mean is not None:
            overall_delta = current_overall_mean - baseline_overall_mean

        return FairnessDriftSummary(
            metric=metric,
            groups=groups,
            baseline_overall_mean=baseline_overall_mean,
            current_overall_mean=current_overall_mean,
            overall_delta=overall_delta,
            max_absolute_group_drift=max_absolute_group_drift,
            most_shifted_group=most_shifted_group,
        )

    @staticmethod
    def _overall_mean(values_by_group: dict[str, list[float]]) -> float | None:
        flattened = [value for values in values_by_group.values() for value in values]
        if not flattened:
            return None
        return sum(flattened) / len(flattened)
