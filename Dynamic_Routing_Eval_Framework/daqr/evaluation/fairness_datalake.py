from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from daqr.config.run_spec import RunSpec


@dataclass(frozen=True)
class FairnessDatalakePaths:
    datalake_root: str
    fairness_root: str
    environment_root: str
    run_root: str


class FairnessDatalakePathResolver:
    """Resolve compatibility-safe datalake sidecar paths for fairness artifacts."""

    fairness_root_name: str = "fairness"

    def resolve(self, datalake_root: str | Path, run_spec: RunSpec) -> FairnessDatalakePaths:
        root = Path(datalake_root)
        fairness_root = root / self.fairness_root_name
        environment_root = fairness_root / self._sanitize(run_spec.environment_family)
        run_dir_name = self._build_run_dir_name(run_spec)
        run_root = environment_root / run_dir_name
        return FairnessDatalakePaths(
            datalake_root=str(root),
            fairness_root=str(fairness_root),
            environment_root=str(environment_root),
            run_root=str(run_root),
        )

    def resolve_from_legacy_output_dir(
        self,
        legacy_output_dir: str | Path,
        run_spec: RunSpec,
    ) -> FairnessDatalakePaths:
        legacy_path = Path(legacy_output_dir)
        datalake_root = legacy_path.parent if legacy_path.name.startswith("day_") else legacy_path
        return self.resolve(datalake_root, run_spec)

    def _build_run_dir_name(self, run_spec: RunSpec) -> str:
        parts = [self._sanitize(run_spec.name)]
        if run_spec.testbed_id is not None:
            parts.append(f"testbed_{self._sanitize(str(run_spec.testbed_id))}")
        return "__".join(parts)

    @staticmethod
    def _sanitize(value: str) -> str:
        sanitized = []
        for char in value.strip().lower():
            if char.isalnum():
                sanitized.append(char)
            else:
                sanitized.append("_")
        collapsed = "".join(sanitized)
        while "__" in collapsed:
            collapsed = collapsed.replace("__", "_")
        return collapsed.strip("_") or "unknown"
