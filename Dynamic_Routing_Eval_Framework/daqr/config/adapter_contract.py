from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from daqr.config.outcome_record import OutcomeRecordResolver
from daqr.config.run_spec import RunSpec


@dataclass(frozen=True)
class AdapterCapabilitySpec:
    """Canonical declaration of what an environment adapter supports."""

    adapter_name: str
    environment_family: str
    supports_post_run_fairness: bool = True
    supports_event_logging: bool = False
    supports_sensitive_attributes: bool = False
    supports_real_time_monitoring: bool = False
    supported_testbed_ids: Tuple[Any, ...] = field(default_factory=tuple)
    supported_group_fields: Tuple[str, ...] = field(default_factory=tuple)
    supported_outcome_fields: Tuple[str, ...] = (
        "success",
        "latency",
        "reward",
    )
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.adapter_name or not self.adapter_name.strip():
            raise ValueError("AdapterCapabilitySpec.adapter_name must be a non-empty string")
        if not self.environment_family or not self.environment_family.strip():
            raise ValueError("AdapterCapabilitySpec.environment_family must be a non-empty string")

    def supports_testbed(self, testbed_id: Any) -> bool:
        if not self.supported_testbed_ids:
            return True
        return testbed_id in self.supported_testbed_ids

    def supports_outcome_field(self, field_name: str) -> bool:
        return field_name in self.supported_outcome_fields

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnvironmentAdapterContract(ABC):
    """
    Base OOP contract for environment adapters.

    Concrete adapters will later own the translation from RunSpec into runtime
    environment objects, plus the normalization path into canonical outcomes.
    """

    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilitySpec:
        """Return the adapter's declared capability schema."""

    def validate_run_spec(self, run_spec: RunSpec) -> bool:
        capabilities = self.get_capabilities()
        if run_spec.environment_family != capabilities.environment_family:
            return False
        return capabilities.supports_testbed(run_spec.testbed_id)

    def validate_outcome_resolver(
        self,
        resolver: OutcomeRecordResolver,
    ) -> bool:
        capabilities = self.get_capabilities()
        if not capabilities.supported_group_fields:
            return True
        return any(field in capabilities.supported_group_fields for field in resolver.group_fields)

    def describe_contract(self) -> Dict[str, Any]:
        capabilities = self.get_capabilities()
        return {
            "adapter_name": capabilities.adapter_name,
            "environment_family": capabilities.environment_family,
            "capabilities": capabilities.to_dict(),
        }
