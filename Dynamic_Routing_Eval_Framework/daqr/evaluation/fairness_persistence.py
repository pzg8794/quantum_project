from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from daqr.evaluation.fairness_provenance import FairnessProvenanceManifestBuilder
from daqr.evaluation.fairness_service import FairnessEvaluationResult


# Architecture note: artifact contract for the evidence layer. These paths make
# the final claims traceable to summary metrics, raw fairness records, outcomes,
# provenance, analysis payloads, execution mode, and by-model comparisons.
@dataclass(frozen=True)
class FairnessArtifactPaths:
    output_dir: str
    summary_json: str
    records_json: str
    outcomes_json: str
    manifest_json: str
    analysis_json: str | None = None
    execution_mode_json: str | None = None
    by_model_summary_json: str | None = None


# Architecture note: governed persistence boundary. The workflow calls this
# writer after evaluation so the run produces reviewable files rather than only
# transient notebook output or screenshots.
class FairnessArtifactWriter:
    """Governed writer for fairness evaluation artifacts."""

    def persist(
        self,
        result: FairnessEvaluationResult,
        output_dir: str | Path,
        *,
        analysis_payload: dict[str, Any] | None = None,
        execution_mode_payload: dict[str, Any] | None = None,
        by_model_summary_payload: dict[str, Any] | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> FairnessArtifactPaths:
        base_dir = Path(output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Architecture note: concrete report artifacts. These files are the
        # evidence trail for the final presentation/report: summary, records,
        # outcomes, manifest, analysis, execution mode, and by-model summary.
        summary_path = base_dir / "fairness_summary.json"
        records_path = base_dir / "fairness_records.json"
        outcomes_path = base_dir / "fairness_outcomes.json"
        manifest_path = base_dir / "fairness_manifest.json"
        analysis_path = base_dir / "fairness_analysis.json"
        execution_mode_path = base_dir / "fairness_execution_mode.json"
        by_model_summary_path = base_dir / "fairness_by_model_summary.json"

        summary_payload = {
            metric: asdict(metric_summary)
            for metric, metric_summary in result.summary.items()
        }
        records_payload = result.records
        outcomes_payload = [outcome.to_dict() for outcome in result.outcomes]
        artifact_files = {
            "summary_json": summary_path.name,
            "records_json": records_path.name,
            "outcomes_json": outcomes_path.name,
            "manifest_json": manifest_path.name,
        }
        if analysis_payload is not None:
            artifact_files["analysis_json"] = analysis_path.name
        if execution_mode_payload is not None:
            artifact_files["execution_mode_json"] = execution_mode_path.name
        if by_model_summary_payload is not None:
            artifact_files["by_model_summary_json"] = by_model_summary_path.name
        manifest_payload = FairnessProvenanceManifestBuilder().build(
            result,
            artifact_files=artifact_files,
            workflow_context=workflow_context,
        ).to_dict()

        self._write_json(summary_path, summary_payload)
        self._write_json(records_path, records_payload)
        self._write_json(outcomes_path, outcomes_payload)
        if analysis_payload is not None:
            self._write_json(analysis_path, analysis_payload)
        if execution_mode_payload is not None:
            self._write_json(execution_mode_path, execution_mode_payload)
        if by_model_summary_payload is not None:
            self._write_json(by_model_summary_path, by_model_summary_payload)
        self._write_json(manifest_path, manifest_payload)

        return FairnessArtifactPaths(
            output_dir=str(base_dir),
            summary_json=str(summary_path),
            records_json=str(records_path),
            outcomes_json=str(outcomes_path),
            manifest_json=str(manifest_path),
            analysis_json=str(analysis_path) if analysis_payload is not None else None,
            execution_mode_json=str(execution_mode_path) if execution_mode_payload is not None else None,
            by_model_summary_json=str(by_model_summary_path) if by_model_summary_payload is not None else None,
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
