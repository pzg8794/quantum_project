from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from daqr.config.run_spec import FairnessSpec, ProvenanceSpec, RunSpec


@dataclass(frozen=True)
class EnvironmentResolution:
    environment_family: str
    scenario_type: str
    testbed_id: Any


@dataclass
class RunSpecLoader:
    """Governed loader for multi-environment fairness run configuration."""

    default_environment_family: str = "quantum"
    default_scenario_type: str = "stochastic"
    environment_aliases: dict[str, str] = field(
        default_factory=lambda: {
            "quantum": "quantum",
            "clinical": "clinical",
            "simulator": "simulator",
            "simulation": "simulator",
            "synthetic_clinical": "clinical",
        }
    )

    def from_mapping(
        self,
        payload: Mapping[str, Any],
        *,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
    ) -> RunSpec:
        name = str(payload.get("name") or payload.get("run_name") or "unnamed_run")
        resolution = self.resolve_environment(payload)
        fairness_spec = fairness or self._resolve_fairness(payload)
        provenance_spec = provenance or self._resolve_provenance(payload)

        return RunSpec(
            name=name,
            environment_family=resolution.environment_family,
            scenario_type=resolution.scenario_type,
            testbed_id=resolution.testbed_id,
            testbed_config=dict(payload.get("testbed_config") or {}),
            runs=int(payload.get("runs", 1)),
            scale=int(payload.get("scale", 2)),
            base_seed=int(payload.get("base_seed", 12345)),
            seed_offset=int(payload.get("seed_offset", 100)),
            attack_type=str(payload.get("attack_type", "n/a")),
            attack_intensity=float(payload.get("attack_intensity", 1.0)),
            attack_rate=float(payload.get("attack_rate", 0.25)),
            base_capacity=bool(payload.get("base_capacity", True)),
            overwrite=bool(payload.get("overwrite", False)),
            resume=bool(payload.get("resume", True)),
            use_last_backup=bool(payload.get("use_last_backup", True)),
            verbose=bool(payload.get("verbose", False)),
            suffix=payload.get("suffix"),
            allocator=payload.get("allocator"),
            models=tuple(payload["models"]) if payload.get("models") is not None else None,
            scenarios=dict(payload["scenarios"]) if payload.get("scenarios") is not None else None,
            physics_params=dict(payload.get("physics_params") or {}),
            fairness=fairness_spec,
            provenance=provenance_spec,
            metadata=dict(payload.get("metadata") or {}),
        )

    def from_experiment_configuration(
        self,
        config: Any,
        *,
        name: str | None = None,
        environment_family: str | None = None,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RunSpec:
        resolved_environment = environment_family or self.default_environment_family
        return RunSpec.from_experiment_configuration(
            config,
            name=name,
            environment_family=self._normalize_environment_family(resolved_environment),
            fairness=fairness,
            provenance=provenance,
            metadata=metadata,
        )

    def resolve_environment(self, payload: Mapping[str, Any]) -> EnvironmentResolution:
        requested_environment = (
            payload.get("environment_family")
            or payload.get("environment")
            or payload.get("env_family")
            or self.default_environment_family
        )
        environment_family = self._normalize_environment_family(str(requested_environment))

        scenario_type = str(
            payload.get("scenario_type")
            or payload.get("env_type")
            or self.default_scenario_type
        )
        testbed_id = payload.get("testbed_id")
        if testbed_id is None and environment_family == "clinical":
            testbed_id = payload.get("clinical_fixture_id", "clinical_fixture_v1")
        if testbed_id is None and environment_family == "quantum":
            testbed_id = payload.get("paper_id")

        return EnvironmentResolution(
            environment_family=environment_family,
            scenario_type=scenario_type,
            testbed_id=testbed_id,
        )

    def _resolve_fairness(self, payload: Mapping[str, Any]) -> FairnessSpec:
        fairness_payload = payload.get("fairness") or {}
        return FairnessSpec(
            protected_attributes=tuple(fairness_payload.get("protected_attributes") or ()),
            resolver_name=fairness_payload.get("resolver_name"),
            extras=dict(fairness_payload.get("extras") or {}),
        )

    def _resolve_provenance(self, payload: Mapping[str, Any]) -> ProvenanceSpec:
        provenance_payload = payload.get("provenance") or {}
        return ProvenanceSpec(
            source=str(provenance_payload.get("source", "unknown")),
            git_sha=provenance_payload.get("git_sha"),
            config_origin=provenance_payload.get("config_origin"),
            data_manifest=provenance_payload.get("data_manifest"),
            created_at=provenance_payload.get("created_at"),
            execution_mode=provenance_payload.get("execution_mode"),
            environment_metadata=dict(provenance_payload.get("environment_metadata") or {}),
            artifact_lineage=dict(provenance_payload.get("artifact_lineage") or {}),
            tags=dict(provenance_payload.get("tags") or {}),
            extras=dict(provenance_payload.get("extras") or {}),
        )

    def _normalize_environment_family(self, environment_family: str) -> str:
        normalized = environment_family.strip().lower()
        if normalized not in self.environment_aliases:
            raise ValueError(f"Unsupported environment family: {environment_family}")
        return self.environment_aliases[normalized]
