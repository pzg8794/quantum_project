from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict

from daqr.config.adapter_contract import EnvironmentAdapterContract
from daqr.config.run_spec import RunSpec
from daqr.evaluation.clinical_adapter import ClinicalFairnessAdapter
from daqr.evaluation.quantum_adapter import QuantumFairnessAdapter


AdapterFactory = Callable[[], EnvironmentAdapterContract]


@dataclass
class EnvironmentAdapterRegistry:
    """Owned registry for resolving fairness adapters by environment family."""

    factories: Dict[str, AdapterFactory] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.factories:
            self.register("quantum", QuantumFairnessAdapter)
            self.register("clinical", ClinicalFairnessAdapter)

    def register(self, environment_family: str, factory: AdapterFactory) -> None:
        key = self._normalize_key(environment_family)
        self.factories[key] = factory

    def create(self, environment_family: str) -> EnvironmentAdapterContract:
        key = self._normalize_key(environment_family)
        if key not in self.factories:
            raise KeyError(f"No adapter registered for environment family '{environment_family}'")
        return self.factories[key]()

    def create_for_run_spec(self, run_spec: RunSpec) -> EnvironmentAdapterContract:
        adapter = self.create(run_spec.environment_family)
        if not adapter.validate_run_spec(run_spec):
            raise ValueError(
                f"Registered adapter for '{run_spec.environment_family}' does not accept run spec '{run_spec.name}'"
            )
        return adapter

    def available_families(self) -> tuple[str, ...]:
        return tuple(sorted(self.factories.keys()))

    @staticmethod
    def _normalize_key(environment_family: str) -> str:
        return environment_family.strip().lower()
