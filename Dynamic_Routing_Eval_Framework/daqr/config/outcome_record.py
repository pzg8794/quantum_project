from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from daqr.config.run_spec import ProvenanceSpec


@dataclass(frozen=True)
class OutcomeRecord:
    """Canonical per-observation outcome contract for fairness analysis."""

    group: str
    environment_family: str = "quantum"
    run_name: Optional[str] = None
    env_type: Optional[str] = None
    testbed_id: Optional[Any] = None
    success: Optional[float] = None
    latency: Optional[float] = None
    reward: Optional[float] = None
    outcomes: Dict[str, Optional[float]] = field(default_factory=dict)
    protected_attributes: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    provenance: ProvenanceSpec = field(default_factory=ProvenanceSpec)
    source_record: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.group or not str(self.group).strip():
            raise ValueError("OutcomeRecord.group must be a non-empty string")
        if not self.environment_family or not self.environment_family.strip():
            raise ValueError("OutcomeRecord.environment_family must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OutcomeRecordResolver:
    """
    Owned object responsible for normalizing raw framework state into the
    canonical OutcomeRecord contract.
    """

    group_fields: Tuple[str, ...] = (
        "fairness_group",
        "group",
        "flow_group",
        "request_group",
        "user_group",
        "source",
    )
    success_fields: Tuple[str, ...] = (
        "success",
        "success_rate",
        "routing_success",
    )
    latency_fields: Tuple[str, ...] = (
        "latency",
        "delay",
        "time_to_success",
        "completion_time",
    )
    reward_fields: Tuple[str, ...] = ("reward",)
    protected_attribute_fields: Tuple[str, ...] = field(default_factory=tuple)
    context_fields: Tuple[str, ...] = (
        "source",
        "allocator",
        "env_type",
        "environment",
        "attack_type",
        "attack_intensity",
        "clinical_model",
        "clinical_model_action",
        "clinical_intervention_enabled",
        "clinical_model_confidence",
        "clinical_exploration_score",
        "equitas_mediator",
        "equitas_mode",
        "equitas_mitigation",
        "equitas_priority_adjustment",
        "equitas_rationale",
    )

    def build_record(
        self,
        state: Mapping[str, Any],
        *,
        environment_family: str = "quantum",
        run_name: Optional[str] = None,
        testbed_id: Optional[Any] = None,
        provenance: Optional[ProvenanceSpec] = None,
    ) -> Optional[OutcomeRecord]:
        group = self.resolve_group(state)
        if group is None:
            return None

        success = self.resolve_numeric(state, self.success_fields)
        latency = self.resolve_numeric(state, self.latency_fields)
        reward = self.resolve_numeric(state, self.reward_fields)
        protected_attributes = self.collect_fields(state, self.protected_attribute_fields)
        context = self.collect_fields(state, self.context_fields)
        env_type = self.resolve_text(state, ("env_type", "environment"))

        outcomes = {
            "success": success,
            "latency": latency,
            "reward": reward,
        }

        return OutcomeRecord(
            group=group,
            environment_family=environment_family,
            run_name=run_name,
            env_type=env_type,
            testbed_id=testbed_id,
            success=success,
            latency=latency,
            reward=reward,
            outcomes=outcomes,
            protected_attributes=protected_attributes,
            context=context,
            provenance=provenance if provenance is not None else ProvenanceSpec(),
            source_record=dict(state),
        )

    def resolve_group(self, state: Mapping[str, Any]) -> Optional[str]:
        value = self.resolve_first_present(state, self.group_fields)
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def resolve_text(
        self,
        state: Mapping[str, Any],
        fields: Sequence[str],
    ) -> Optional[str]:
        value = self.resolve_first_present(state, fields)
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def resolve_numeric(
        self,
        state: Mapping[str, Any],
        fields: Sequence[str],
    ) -> Optional[float]:
        value = self.resolve_first_present(state, fields)
        if value is None:
            return None
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def collect_fields(
        self,
        state: Mapping[str, Any],
        fields: Sequence[str],
    ) -> Dict[str, Any]:
        collected: Dict[str, Any] = {}
        for field_name in fields:
            if field_name in state and state[field_name] is not None:
                collected[field_name] = state[field_name]
        return collected

    def resolve_first_present(
        self,
        state: Mapping[str, Any],
        fields: Sequence[str],
    ) -> Any:
        for field_name in fields:
            value = state.get(field_name)
            if value is not None:
                return value
        return None
