from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


DEFAULT_GROUP_FIELDS = (
    "group",
    "flow_group",
    "user_group",
    "request_group",
    "source",
)

DEFAULT_SUCCESS_FIELDS = (
    "success",
    "success_rate",
    "routing_success",
    "reward",
)

DEFAULT_LATENCY_FIELDS = (
    "latency",
    "delay",
    "time_to_success",
    "completion_time",
)


def _safe_copy(value: Any) -> Any:
    """Best-effort copy that gracefully falls back for non-copyable objects."""
    try:
        return deepcopy(value)
    except Exception:
        return value


@dataclass(frozen=True)
class ProvenanceSpec:
    """Execution provenance carried alongside a canonical run description."""

    source: str = "unknown"
    git_sha: Optional[str] = None
    config_origin: Optional[str] = None
    data_manifest: Optional[str] = None
    created_at: Optional[str] = None
    execution_mode: Optional[str] = None
    environment_metadata: Dict[str, Any] = field(default_factory=dict)
    artifact_lineage: Dict[str, str] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FairnessSpec:
    """Fairness-related selectors and metadata that travel with a run."""

    group_fields: Tuple[str, ...] = DEFAULT_GROUP_FIELDS
    success_fields: Tuple[str, ...] = DEFAULT_SUCCESS_FIELDS
    latency_fields: Tuple[str, ...] = DEFAULT_LATENCY_FIELDS
    protected_attributes: Tuple[str, ...] = field(default_factory=tuple)
    resolver_name: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunSpec:
    """
    Canonical run contract for the fairness framework.

    This object intentionally sits *in front of* the current quantum-first
    ExperimentConfiguration path. It describes what should be run without
    embedding execution logic, and can be translated into the legacy config
    object while the framework transitions toward multi-environment adapters.
    """

    name: str
    environment_family: str = "quantum"
    scenario_type: str = "stochastic"
    testbed_id: Optional[Any] = None
    testbed_config: Dict[str, Any] = field(default_factory=dict)
    runs: int = 1
    scale: int = 2
    base_seed: int = 12345
    seed_offset: int = 100
    attack_type: str = "n/a"
    attack_intensity: float = 1.0
    attack_rate: float = 0.25
    base_capacity: bool = True
    overwrite: bool = False
    resume: bool = True
    use_last_backup: bool = True
    verbose: bool = False
    suffix: Optional[str] = None
    allocator: Any = None
    models: Optional[Tuple[str, ...]] = None
    scenarios: Optional[Dict[str, str]] = None
    physics_params: Dict[str, Any] = field(default_factory=dict)
    fairness: FairnessSpec = field(default_factory=FairnessSpec)
    provenance: ProvenanceSpec = field(default_factory=ProvenanceSpec)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("RunSpec.name must be a non-empty string")
        if not self.environment_family or not self.environment_family.strip():
            raise ValueError("RunSpec.environment_family must be a non-empty string")
        if self.runs < 1:
            raise ValueError("RunSpec.runs must be at least 1")
        if self.scale < 1:
            raise ValueError("RunSpec.scale must be at least 1")
        if self.seed_offset < 0:
            raise ValueError("RunSpec.seed_offset must be non-negative")

    @property
    def env_type(self) -> str:
        """Legacy-compatible alias for the existing quantum config field name."""
        return self.scenario_type

    def with_updates(self, **changes: Any) -> "RunSpec":
        """Return a new RunSpec with one or more updated fields."""
        return replace(self, **changes)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["models"] = list(self.models) if self.models is not None else None
        return payload

    def to_experiment_config_kwargs(self) -> Dict[str, Any]:
        """
        Translate the canonical run contract into the current
        ExperimentConfiguration constructor shape.
        """
        return {
            "runs": self.runs,
            "physics_params": _safe_copy(self.physics_params),
            "seed_offset": self.seed_offset,
            "env_type": self.scenario_type,
            "attack_type": self.attack_type,
            "suffix": self.suffix,
            "attack_intensity": self.attack_intensity,
            "attack_rate": self.attack_rate,
            "models": list(self.models) if self.models is not None else None,
            "scenarios": _safe_copy(self.scenarios),
            "allocator": _safe_copy(self.allocator),
            "base_seed": self.base_seed,
            "scale": self.scale,
            "base_capacity": self.base_capacity,
            "overwrite": self.overwrite,
            "resume": self.resume,
            "use_last_backup": self.use_last_backup,
            "verbose": self.verbose,
            "testbed_id": self.testbed_id,
            "testbed_config": _safe_copy(self.testbed_config),
        }

    def to_experiment_configuration(self, config_cls: Optional[type] = None) -> Any:
        """
        Build the legacy ExperimentConfiguration object from this RunSpec.

        The import is intentionally lazy to keep the contract lightweight and
        unit-testable without forcing the full quantum dependency tree to load.
        """
        if config_cls is None:
            from daqr.config.experiment_config import ExperimentConfiguration

            config_cls = ExperimentConfiguration
        return config_cls(**self.to_experiment_config_kwargs())

    @classmethod
    def from_experiment_configuration(
        cls,
        config: Any,
        *,
        name: Optional[str] = None,
        environment_family: str = "quantum",
        fairness: Optional[FairnessSpec] = None,
        provenance: Optional[ProvenanceSpec] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "RunSpec":
        """
        Lift an existing ExperimentConfiguration-like object into the canonical
        run contract without requiring the framework to refactor all at once.
        """
        resolved_name = name or getattr(config, "log_name", None) or getattr(config, "suffix", None) or "unnamed_run"
        scenarios = getattr(config, "test_scenarios", None)
        models = getattr(config, "models", None)

        if models is not None:
            models = tuple(models)

        return cls(
            name=resolved_name,
            environment_family=environment_family,
            scenario_type=getattr(config, "env_type", "stochastic"),
            testbed_id=getattr(config, "testbed_id", None),
            testbed_config=_safe_copy(getattr(config, "testbed_config", {})),
            runs=getattr(config, "runs", 1),
            scale=getattr(config, "scale", 1),
            base_seed=getattr(config, "base_seed", 12345),
            seed_offset=getattr(config, "seed_offset", 100),
            attack_type=getattr(config, "attack_type", "n/a"),
            attack_intensity=getattr(config, "attack_intensity", 1.0),
            attack_rate=getattr(config, "attack_rate", 0.25),
            base_capacity=getattr(config, "base_capacity", True),
            overwrite=getattr(config, "overwrite", False),
            resume=getattr(config, "resumed", True),
            use_last_backup=getattr(config, "use_last_backup", True),
            verbose=getattr(config, "verbose", False),
            suffix=getattr(config, "suffix", None),
            allocator=_safe_copy(getattr(config, "allocator", None)),
            models=models,
            scenarios=_safe_copy(scenarios),
            physics_params=_safe_copy(getattr(config, "physics_params", {})),
            fairness=fairness if fairness is not None else FairnessSpec(),
            provenance=provenance if provenance is not None else ProvenanceSpec(),
            metadata=dict(metadata or {}),
        )
