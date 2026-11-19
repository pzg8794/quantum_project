from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GroupPerformanceSummary:
    group: str
    count: int
    mean_prediction: float | None
    mean_outcome: float | None
    calibration_gap: float | None


@dataclass(frozen=True)
class CalibrationFairnessSummary:
    metric: str
    groups: dict[str, GroupPerformanceSummary]
    max_calibration_gap: float | None
    min_calibration_gap: float | None
    calibration_gap_range: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "groups": {name: asdict(summary) for name, summary in self.groups.items()},
            "max_calibration_gap": self.max_calibration_gap,
            "min_calibration_gap": self.min_calibration_gap,
            "calibration_gap_range": self.calibration_gap_range,
        }


class CalibrationFairnessAnalyzer:
    """Governed analyzer for calibration and performance-by-group fairness."""

    def summarize(
        self,
        metric: str,
        predictions_by_group: dict[str, list[float]],
        outcomes_by_group: dict[str, list[float]],
    ) -> CalibrationFairnessSummary:
        groups: dict[str, GroupPerformanceSummary] = {}
        gaps: list[float] = []

        for group in sorted(set(predictions_by_group) | set(outcomes_by_group)):
            predictions = predictions_by_group.get(group, [])
            outcomes = outcomes_by_group.get(group, [])
            count = min(len(predictions), len(outcomes)) if predictions and outcomes else max(len(predictions), len(outcomes))

            mean_prediction = (sum(predictions) / len(predictions)) if predictions else None
            mean_outcome = (sum(outcomes) / len(outcomes)) if outcomes else None
            calibration_gap = None
            if mean_prediction is not None and mean_outcome is not None:
                calibration_gap = mean_prediction - mean_outcome
                gaps.append(calibration_gap)

            groups[group] = GroupPerformanceSummary(
                group=group,
                count=count,
                mean_prediction=mean_prediction,
                mean_outcome=mean_outcome,
                calibration_gap=calibration_gap,
            )

        max_gap = max(gaps) if gaps else None
        min_gap = min(gaps) if gaps else None
        gap_range = (max_gap - min_gap) if gaps else None

        return CalibrationFairnessSummary(
            metric=metric,
            groups=groups,
            max_calibration_gap=max_gap,
            min_calibration_gap=min_gap,
            calibration_gap_range=gap_range,
        )
