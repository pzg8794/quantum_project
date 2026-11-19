from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class FairnessExecutionMode:
    mode: str
    data_residency: str
    artifact_scope: str
    allows_centralized_aggregation: bool
    notes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FairnessExecutionModeResolver:
    """Governed resolver for site-local versus centralized fairness execution."""

    def resolve(self, mode: str, *, notes: dict[str, Any] | None = None) -> FairnessExecutionMode:
        normalized = mode.strip().lower()
        merged_notes = dict(notes or {})

        if normalized == "site_local":
            return FairnessExecutionMode(
                mode="site_local",
                data_residency="local_site",
                artifact_scope="site_only",
                allows_centralized_aggregation=False,
                notes=merged_notes,
            )

        if normalized == "centralized":
            return FairnessExecutionMode(
                mode="centralized",
                data_residency="central_store",
                artifact_scope="shared",
                allows_centralized_aggregation=True,
                notes=merged_notes,
            )

        raise ValueError(f"Unsupported fairness execution mode: {mode}")
