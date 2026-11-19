from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from daqr.config.adapter_contract import AdapterCapabilitySpec, EnvironmentAdapterContract
from daqr.config.outcome_record import OutcomeRecordResolver
from daqr.config.run_spec import RunSpec


@dataclass
class QuantumFairnessAdapter(EnvironmentAdapterContract):
    """Concrete fairness adapter for the current quantum-first DAQR environment."""

    supported_testbed_ids: tuple[Any, ...] = field(default_factory=tuple)
    outcome_resolver: OutcomeRecordResolver = field(default_factory=OutcomeRecordResolver)

    def get_capabilities(self) -> AdapterCapabilitySpec:
        return AdapterCapabilitySpec(
            adapter_name="QuantumFairnessAdapter",
            environment_family="quantum",
            supports_post_run_fairness=True,
            supports_event_logging=False,
            supports_sensitive_attributes=False,
            supports_real_time_monitoring=False,
            supported_testbed_ids=self.supported_testbed_ids,
            supported_group_fields=self.outcome_resolver.group_fields,
            supported_outcome_fields=("success", "latency", "reward"),
            extras={
                "normalization_mode": "post_run_state",
                "primary_env_types": ("stochastic", "adversarial", "none"),
            },
        )

    def validate_run_spec(self, run_spec: RunSpec) -> bool:
        if not super().validate_run_spec(run_spec):
            return False
        return run_spec.environment_family == "quantum"

    def build_runtime_context(self, run_spec: RunSpec) -> dict[str, Any]:
        """Return a lightweight governed context for fairness evaluation wiring."""
        return {
            "run_name": run_spec.name,
            "environment_family": run_spec.environment_family,
            "scenario_type": run_spec.scenario_type,
            "testbed_id": run_spec.testbed_id,
            "models": list(run_spec.models) if run_spec.models is not None else [],
            "fairness": run_spec.fairness.to_dict(),
            "provenance": run_spec.provenance.to_dict(),
        }

    def normalize_state(self, state: Mapping[str, Any], run_spec: RunSpec):
        return self.outcome_resolver.build_record(
            state,
            environment_family=run_spec.environment_family,
            run_name=run_spec.name,
            testbed_id=run_spec.testbed_id,
            provenance=run_spec.provenance,
        )
