from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from daqr.evaluation.fairness_allocation_metrics import AllocationFairnessAnalyzer
from daqr.evaluation.fairness_calibration_metrics import CalibrationFairnessAnalyzer
from daqr.evaluation.fairness_drift_metrics import FairnessDriftAnalyzer
from daqr.evaluation.fairness_hypothesis_tests import FairnessHypothesisTester
from daqr.evaluation.fairness_service import FairnessEvaluationResult


@dataclass(frozen=True)
class CompositeFairnessAnalysis:
    run_spec_name: str
    environment_family: str
    baseline_summary: dict[str, dict[str, Any]]
    allocation_summary: dict[str, dict[str, Any]]
    calibration_summary: dict[str, dict[str, Any]]
    hypothesis_tests: dict[str, dict[str, Any]]
    drift_summary: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FairnessAnalysisPipeline:
    """Composite governed pipeline over the framework's fairness analyzers."""

    allocation_analyzer: AllocationFairnessAnalyzer = field(default_factory=AllocationFairnessAnalyzer)
    calibration_analyzer: CalibrationFairnessAnalyzer = field(default_factory=CalibrationFairnessAnalyzer)
    hypothesis_tester: FairnessHypothesisTester = field(default_factory=FairnessHypothesisTester)
    drift_analyzer: FairnessDriftAnalyzer = field(default_factory=FairnessDriftAnalyzer)

    def analyze(
        self,
        result: FairnessEvaluationResult,
        *,
        baseline_result: FairnessEvaluationResult | None = None,
    ) -> CompositeFairnessAnalysis:
        grouped_metric_values = self._collect_grouped_metric_values(result)
        baseline_summary = {
            metric_name: self._summary_to_dict(metric_summary)
            for metric_name, metric_summary in result.summary.items()
        }
        allocation_summary = {
            metric_name: self.allocation_analyzer.summarize(metric_name, values_by_group).to_dict()
            for metric_name, values_by_group in grouped_metric_values.items()
        }

        predictions_by_group = self._collect_grouped_predictions(result)
        outcomes_by_group = grouped_metric_values.get("success", {})
        calibration_summary = {}
        if predictions_by_group:
            calibration = self.calibration_analyzer.summarize(
                "calibration",
                predictions_by_group,
                outcomes_by_group,
            )
            calibration_summary["calibration"] = calibration.to_dict()

        hypothesis_tests = {
            metric_name: self.hypothesis_tester.test_group_gap(metric_name, values_by_group).to_dict()
            for metric_name, values_by_group in grouped_metric_values.items()
        }

        drift_summary = {}
        if baseline_result is not None:
            baseline_grouped_values = self._collect_grouped_metric_values(baseline_result)
            for metric_name, values_by_group in grouped_metric_values.items():
                drift = self.drift_analyzer.summarize(
                    metric_name,
                    baseline_grouped_values.get(metric_name, {}),
                    values_by_group,
                )
                drift_summary[metric_name] = drift.to_dict()

        return CompositeFairnessAnalysis(
            run_spec_name=result.run_spec_name,
            environment_family=result.environment_family,
            baseline_summary=baseline_summary,
            allocation_summary=allocation_summary,
            calibration_summary=calibration_summary,
            hypothesis_tests=hypothesis_tests,
            drift_summary=drift_summary,
        )

    @staticmethod
    def _summary_to_dict(metric_summary: Any) -> dict[str, Any]:
        payload = {
            "group_means": getattr(metric_summary, "group_means", {}),
            "group_counts": getattr(metric_summary, "group_counts", {}),
            "parity_gap": getattr(metric_summary, "parity_gap", None),
        }
        for field_name in (
            "overall_mean",
            "overall_mean_ci_low",
            "overall_mean_ci_high",
            "min_group",
            "min_group_mean",
            "max_group",
            "max_group_mean",
            "parity_gap_ci_low",
            "parity_gap_ci_high",
            "disparity_ratio",
        ):
            if hasattr(metric_summary, field_name):
                payload[field_name] = getattr(metric_summary, field_name)
        return payload

    @staticmethod
    def _collect_grouped_metric_values(result: FairnessEvaluationResult) -> dict[str, dict[str, list[float]]]:
        grouped = {
            "success": {},
            "latency": {},
            "reward": {},
        }
        for outcome in result.outcomes:
            if outcome.group is None:
                continue
            if outcome.success is not None:
                grouped["success"].setdefault(outcome.group, []).append(float(outcome.success))
            if outcome.latency is not None:
                grouped["latency"].setdefault(outcome.group, []).append(float(outcome.latency))
            if outcome.reward is not None:
                grouped["reward"].setdefault(outcome.group, []).append(float(outcome.reward))
        return grouped

    @staticmethod
    def _collect_grouped_predictions(result: FairnessEvaluationResult) -> dict[str, list[float]]:
        grouped: dict[str, list[float]] = {}
        for outcome in result.outcomes:
            if outcome.group is None:
                continue
            prediction = None
            if isinstance(outcome.outcomes, dict):
                for field_name in ("prediction", "predicted_score", "score", "probability"):
                    if field_name in outcome.outcomes and outcome.outcomes[field_name] is not None:
                        prediction = outcome.outcomes[field_name]
                        break
            if prediction is None:
                for field_name in ("prediction", "predicted_score", "score", "probability"):
                    if field_name in outcome.context and outcome.context[field_name] is not None:
                        prediction = outcome.context[field_name]
                        break
            if prediction is not None:
                grouped.setdefault(outcome.group, []).append(float(prediction))
        return grouped
