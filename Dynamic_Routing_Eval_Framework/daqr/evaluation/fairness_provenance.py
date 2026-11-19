from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from daqr.config.run_spec import ProvenanceSpec
from daqr.evaluation.fairness_service import FairnessEvaluationResult


@dataclass(frozen=True)
class FairnessProvenanceManifest:
    schema_version: str
    run_spec_name: str
    environment_family: str
    adapter_name: str
    provenance: dict[str, Any]
    artifact_files: dict[str, str]
    outcome_count: int
    metric_count: int
    workflow_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FairnessProvenanceManifestBuilder:
    """Build a stable provenance manifest for fairness artifacts."""

    schema_version: str = "fairness-provenance/v1"

    def build(
        self,
        result: FairnessEvaluationResult,
        *,
        artifact_files: dict[str, str],
        workflow_context: dict[str, Any] | None = None,
    ) -> FairnessProvenanceManifest:
        provenance = self._resolve_provenance(result)
        return FairnessProvenanceManifest(
            schema_version=self.schema_version,
            run_spec_name=result.run_spec_name,
            environment_family=result.environment_family,
            adapter_name=result.adapter_name,
            provenance=provenance.to_dict(),
            artifact_files=dict(artifact_files),
            outcome_count=len(result.outcomes),
            metric_count=len(result.summary),
            workflow_context=dict(workflow_context or {}),
        )

    @staticmethod
    def _resolve_provenance(result: FairnessEvaluationResult) -> ProvenanceSpec:
        if result.outcomes:
            return result.outcomes[0].provenance
        return ProvenanceSpec()
