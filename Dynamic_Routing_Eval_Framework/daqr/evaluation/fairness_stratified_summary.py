from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from daqr.config.outcome_record import OutcomeRecord
from daqr.evaluation.fairness_evaluator import FairnessEvaluator
from daqr.evaluation.fairness_service import FairnessEvaluationResult


class FairnessByModelSummaryBuilder:
    """Build model-stratified fairness summaries from canonical outcomes."""

    schema_version = "fairness-by-model-summary/v1"
    model_fields = (
        "clinical_model",
        "model",
        "model_name",
        "algorithm",
        "policy",
    )

    def __init__(self, evaluator: FairnessEvaluator | None = None) -> None:
        self.evaluator = evaluator or FairnessEvaluator()

    def build(
        self,
        result: FairnessEvaluationResult,
        *,
        model_fields: Iterable[str] | None = None,
    ) -> dict[str, Any] | None:
        resolved_field, grouped_outcomes = self._group_by_model(
            result.outcomes,
            model_fields=tuple(model_fields or self.model_fields),
        )
        if resolved_field is None or not grouped_outcomes:
            return None

        strata: dict[str, dict[str, Any]] = {}
        records: list[dict[str, Any]] = []
        for model_name, outcomes in sorted(grouped_outcomes.items()):
            summary = self.evaluator.summarize_outcomes(outcomes)
            summary_payload = {
                metric: asdict(metric_summary)
                for metric, metric_summary in summary.items()
            }
            strata[model_name] = {
                "outcome_count": len(outcomes),
                "summary": summary_payload,
            }
            for record in self.evaluator.to_records(summary):
                records.append({"model": model_name, **record})

        return {
            "schema_version": self.schema_version,
            "run_spec_name": result.run_spec_name,
            "environment_family": result.environment_family,
            "adapter_name": result.adapter_name,
            "stratification_field": resolved_field,
            "model_count": len(strata),
            "outcome_count": sum(payload["outcome_count"] for payload in strata.values()),
            "models": sorted(strata),
            "strata": strata,
            "records": records,
        }

    def _group_by_model(
        self,
        outcomes: list[OutcomeRecord],
        *,
        model_fields: tuple[str, ...],
    ) -> tuple[str | None, dict[str, list[OutcomeRecord]]]:
        for field_name in model_fields:
            grouped: dict[str, list[OutcomeRecord]] = {}
            for outcome in outcomes:
                value = outcome.context.get(field_name)
                if value is None:
                    value = outcome.source_record.get(field_name)
                if value is None:
                    continue
                model_name = str(value).strip()
                if not model_name:
                    continue
                grouped.setdefault(model_name, []).append(outcome)
            if grouped:
                return field_name, grouped
        return None, {}
