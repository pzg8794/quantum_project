"""Post-run fairness evaluation over canonical DAQR outcome records.

The fairness layer still accepts persisted state dictionaries for compatibility,
but normalization into canonical outcome objects is now owned by the
OutcomeRecordResolver contract instead of loose evaluator helpers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from daqr.config.outcome_record import OutcomeRecord, OutcomeRecordResolver
from daqr.config.run_spec import ProvenanceSpec


State = dict[str, Any]


@dataclass(frozen=True)
class FairnessMetricSummary:
    """Group-level metric summary plus a simple parity gap."""

    metric: str
    group_means: dict[str, float]
    group_counts: dict[str, int]
    parity_gap: float | None


@dataclass
class FairnessEvaluator:
    """Evaluate group disparities from canonical outcome records."""

    outcome_resolver: OutcomeRecordResolver = field(default_factory=OutcomeRecordResolver)
    metric_fields: tuple[str, ...] = ("success", "latency", "reward")
    environment_family: str = "quantum"
    summation_profile: str = "python-runtime/v1"

    def __post_init__(self) -> None:
        if self.summation_profile not in {"python-runtime/v1", "float-left-to-right/v1"}:
            raise ValueError("Unsupported fairness summation profile")

    def summarize(self, states: Iterable[State]) -> dict[str, FairnessMetricSummary]:
        outcomes = self.build_outcomes(states)
        return self.summarize_outcomes(outcomes)

    def build_outcomes(
        self,
        states: Iterable[Mapping[str, Any]],
        *,
        run_name: str | None = None,
        testbed_id: Any = None,
        provenance: ProvenanceSpec | None = None,
    ) -> list[OutcomeRecord]:
        outcomes: list[OutcomeRecord] = []
        for state in states:
            outcome = self.outcome_resolver.build_record(
                state,
                environment_family=self.environment_family,
                run_name=run_name,
                testbed_id=testbed_id,
                provenance=provenance,
            )
            if outcome is not None:
                outcomes.append(outcome)
        return outcomes

    def summarize_outcomes(
        self,
        outcomes: Sequence[OutcomeRecord],
    ) -> dict[str, FairnessMetricSummary]:
        grouped_values: dict[str, dict[str, list[float]]] = {
            metric: defaultdict(list) for metric in self.metric_fields
        }

        for outcome in outcomes:
            for metric in self.metric_fields:
                value = outcome.outcomes.get(metric)
                if value is not None:
                    grouped_values[metric][outcome.group].append(float(value))

        return {
            metric: self._summarize_metric(metric, values_by_group,
                                           summation_profile=self.summation_profile)
            for metric, values_by_group in grouped_values.items()
        }

    @staticmethod
    def _summarize_metric(
        metric: str,
        values_by_group: dict[str, list[float]],
        *, summation_profile: str = "python-runtime/v1",
    ) -> FairnessMetricSummary:
        if summation_profile not in {"python-runtime/v1", "float-left-to-right/v1"}:
            raise ValueError("Unsupported fairness summation profile")
        def total(values):
            if summation_profile == "python-runtime/v1":
                return sum(values)
            result = 0.0
            for value in values:
                result += value
            return result
        group_means = {
            group: total(values) / len(values)
            for group, values in values_by_group.items()
            if values
        }
        group_counts = {
            group: len(values)
            for group, values in values_by_group.items()
            if values
        }
        parity_gap = None
        if group_means:
            parity_gap = max(group_means.values()) - min(group_means.values())

        return FairnessMetricSummary(
            metric=metric,
            group_means=group_means,
            group_counts=group_counts,
            parity_gap=parity_gap,
        )

    @staticmethod
    def to_records(
        summary: dict[str, FairnessMetricSummary],
    ) -> list[dict[str, int | float | str | None]]:
        """Flatten summaries for tables, notebooks, or visualization code."""

        records: list[dict[str, int | float | str | None]] = []
        for metric, metric_summary in summary.items():
            for group, mean in metric_summary.group_means.items():
                records.append(
                    {
                        "metric": metric,
                        "group": group,
                        "mean": mean,
                        "count": metric_summary.group_counts[group],
                        "parity_gap": metric_summary.parity_gap,
                    }
                )
        return records
