from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from daqr.evaluation.fairness_pipeline import FairnessAnalysisPipeline
from daqr.evaluation.fairness_service import FairnessEvaluationResult


@dataclass(frozen=True)
class FairnessReport:
    schema_version: str
    run_spec_name: str
    environment_family: str
    adapter_name: str
    metrics: list[dict[str, Any]]
    records: list[dict[str, Any]]
    outcome_count: int
    analysis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FairnessReportBuilder:
    """Governed builder for stable fairness summary output."""

    schema_version: str = "fairness-report/v1"

    def build(
        self,
        result: FairnessEvaluationResult,
        *,
        baseline_result: FairnessEvaluationResult | None = None,
    ) -> FairnessReport:
        metrics: list[dict[str, Any]] = []
        for metric_name, metric_summary in result.summary.items():
            payload = {
                "metric": metric_name,
                "group_means": metric_summary.group_means,
                "group_counts": metric_summary.group_counts,
                "parity_gap": metric_summary.parity_gap,
            }
            if hasattr(metric_summary, "overall_mean"):
                payload["overall_mean"] = getattr(metric_summary, "overall_mean")
            if hasattr(metric_summary, "min_group"):
                payload["min_group"] = getattr(metric_summary, "min_group")
            if hasattr(metric_summary, "min_group_mean"):
                payload["min_group_mean"] = getattr(metric_summary, "min_group_mean")
            if hasattr(metric_summary, "max_group"):
                payload["max_group"] = getattr(metric_summary, "max_group")
            if hasattr(metric_summary, "max_group_mean"):
                payload["max_group_mean"] = getattr(metric_summary, "max_group_mean")
            if hasattr(metric_summary, "disparity_ratio"):
                payload["disparity_ratio"] = getattr(metric_summary, "disparity_ratio")
            metrics.append(payload)

        analysis = None
        if baseline_result is not None:
            analysis = FairnessAnalysisPipeline().analyze(
                result,
                baseline_result=baseline_result,
            ).to_dict()

        return FairnessReport(
            schema_version=self.schema_version,
            run_spec_name=result.run_spec_name,
            environment_family=result.environment_family,
            adapter_name=result.adapter_name,
            metrics=metrics,
            records=result.records,
            outcome_count=len(result.outcomes),
            analysis=analysis,
        )
