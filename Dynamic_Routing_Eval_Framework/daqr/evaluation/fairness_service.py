from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from daqr.config.adapter_contract import EnvironmentAdapterContract
from daqr.config.outcome_record import OutcomeRecord
from daqr.config.run_spec import RunSpec
from daqr.evaluation.adapter_registry import EnvironmentAdapterRegistry
from daqr.evaluation.fairness_evaluator import FairnessEvaluator, FairnessMetricSummary
from daqr.evaluation.fairness_event_logger import FairnessEventLogger


@dataclass(frozen=True)
class FairnessEvaluationResult:
    """Canonical result object for a governed fairness evaluation pass."""

    run_spec_name: str
    environment_family: str
    adapter_name: str
    outcomes: list[OutcomeRecord]
    summary: dict[str, FairnessMetricSummary]
    records: list[dict[str, int | float | str | None]]


@dataclass
class FairnessEvaluationService:
    """Governed OOP entrypoint for fairness evaluation."""

    adapter: EnvironmentAdapterContract | None = None
    evaluator: FairnessEvaluator = field(default_factory=FairnessEvaluator)
    registry: EnvironmentAdapterRegistry = field(default_factory=EnvironmentAdapterRegistry)
    event_logger: FairnessEventLogger | None = None

    def evaluate_states(
        self,
        run_spec: RunSpec,
        states: Iterable[Mapping[str, Any]],
    ) -> FairnessEvaluationResult:
        adapter = self._resolve_adapter(run_spec)
        resolver = getattr(adapter, "outcome_resolver", self.evaluator.outcome_resolver)

        if not adapter.validate_outcome_resolver(resolver):
            raise ValueError(
                f"Outcome resolver is not compatible with adapter "
                f"'{adapter.get_capabilities().adapter_name}'"
            )

        capabilities = adapter.get_capabilities()
        outcomes: list[OutcomeRecord] = []
        for state in states:
            outcome = resolver.build_record(
                state,
                environment_family=run_spec.environment_family,
                run_name=run_spec.name,
                testbed_id=run_spec.testbed_id,
                provenance=run_spec.provenance,
            )
            if outcome is not None:
                outcomes.append(outcome)
                self._log_evaluation_events(run_spec, outcome, capabilities.adapter_name)

        summary = self.evaluator.summarize_outcomes(outcomes)
        records = self.evaluator.to_records(summary)

        return FairnessEvaluationResult(
            run_spec_name=run_spec.name,
            environment_family=run_spec.environment_family,
            adapter_name=capabilities.adapter_name,
            outcomes=outcomes,
            summary=summary,
            records=records,
        )

    def _log_evaluation_events(
        self,
        run_spec: RunSpec,
        outcome: OutcomeRecord,
        adapter_name: str,
    ) -> None:
        if self.event_logger is None:
            return
        self.event_logger.log_decision(
            run_spec,
            group=outcome.group,
            decision="fairness_evaluation",
            payload={
                "adapter_name": adapter_name,
                "testbed_id": outcome.testbed_id,
            },
        )
        self.event_logger.log_outcome(run_spec, outcome)

    def _resolve_adapter(self, run_spec: RunSpec) -> EnvironmentAdapterContract:
        if self.adapter is not None:
            if not self.adapter.validate_run_spec(run_spec):
                raise ValueError(
                    f"RunSpec '{run_spec.name}' is not compatible with adapter "
                    f"'{self.adapter.get_capabilities().adapter_name}'"
                )
            return self.adapter
        return self.registry.create_for_run_spec(run_spec)
