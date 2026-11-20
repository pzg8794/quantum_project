from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from daqr.config.run_spec import FairnessSpec, ProvenanceSpec, RunSpec
from daqr.config.run_spec_loader import RunSpecLoader
from daqr.evaluation.fairness_datalake import FairnessDatalakePathResolver
from daqr.evaluation.fairness_execution_mode import FairnessExecutionModeResolver
from daqr.evaluation.fairness_export import FairnessExportBundle, FairnessExportService
from daqr.evaluation.fairness_persistence import FairnessArtifactPaths, FairnessArtifactWriter
from daqr.evaluation.fairness_report import FairnessReport, FairnessReportBuilder
from daqr.evaluation.fairness_service import FairnessEvaluationResult, FairnessEvaluationService
from daqr.evaluation.fairness_stratified_summary import FairnessByModelSummaryBuilder


@dataclass(frozen=True)
class FairnessWorkflowResult:
    report: FairnessReport
    exports: FairnessExportBundle
    artifacts: FairnessArtifactPaths


# Architecture note: shared control and validation layer. Clinical and quantum
# fairness states both pass through this workflow, which evaluates states,
# builds reports, exports summaries, persists artifacts, and records by-model
# evidence under a RunSpec.
class FairnessWorkflow:
    """Governed orchestration layer for end-to-end fairness outputs."""

    def __init__(self) -> None:
        self.run_spec_loader = RunSpecLoader()
        self.datalake_path_resolver = FairnessDatalakePathResolver()
        self.execution_mode_resolver = FairnessExecutionModeResolver()
        self.evaluation_service = FairnessEvaluationService()
        self.report_builder = FairnessReportBuilder()
        self.export_service = FairnessExportService()
        self.artifact_writer = FairnessArtifactWriter()
        self.by_model_summary_builder = FairnessByModelSummaryBuilder()

    def run(
        self,
        result: FairnessEvaluationResult,
        output_dir: str | Path,
        *,
        baseline_result: FairnessEvaluationResult | None = None,
        run_spec: RunSpec | None = None,
    ) -> FairnessWorkflowResult:
        report = self.report_builder.build(result, baseline_result=baseline_result)
        exports = self.export_service.export(report)
        execution_mode_payload = self._resolve_execution_mode_payload(run_spec)
        by_model_summary_payload = self.by_model_summary_builder.build(result)
        workflow_context = {
            "report_schema_version": report.schema_version,
            "analysis_available": report.analysis is not None,
            "export_formats": ["markdown", "csv"],
            "execution_mode_available": execution_mode_payload is not None,
            "by_model_summary_available": by_model_summary_payload is not None,
        }
        artifacts = self.artifact_writer.persist(
            result,
            output_dir,
            analysis_payload=report.analysis,
            execution_mode_payload=execution_mode_payload,
            by_model_summary_payload=by_model_summary_payload,
            workflow_context=workflow_context,
        )
        return FairnessWorkflowResult(
            report=report,
            exports=exports,
            artifacts=artifacts,
        )

    # Architecture note: datalake entry point. This links an evaluated fairness
    # result to a RunSpec and a resolved run root so outputs remain traceable to
    # configuration, provenance, and environment metadata.
    def run_to_datalake(
        self,
        result: FairnessEvaluationResult,
        datalake_root: str | Path,
        *,
        baseline_result: FairnessEvaluationResult | None = None,
        run_spec: RunSpec,
    ) -> FairnessWorkflowResult:
        paths = self.datalake_path_resolver.resolve(datalake_root, run_spec)
        return self.run(
            result,
            paths.run_root,
            baseline_result=baseline_result,
            run_spec=run_spec,
        )

    def run_from_mapping(
        self,
        config_payload: Mapping[str, Any],
        states: Iterable[Mapping[str, Any]],
        output_dir: str | Path,
        *,
        baseline_states: Iterable[Mapping[str, Any]] | None = None,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
    ) -> FairnessWorkflowResult:
        run_spec = self.run_spec_loader.from_mapping(
            config_payload,
            fairness=fairness,
            provenance=provenance,
        )
        result = self.evaluation_service.evaluate_states(run_spec, states)
        baseline_result = None
        if baseline_states is not None:
            baseline_result = self.evaluation_service.evaluate_states(run_spec, baseline_states)
        return self.run(result, output_dir, baseline_result=baseline_result, run_spec=run_spec)

    # Architecture note: controlled mapping-based entry point. A payload plus
    # states can still produce the same governed fairness workflow artifacts as
    # evaluator-driven clinical or quantum runs.
    def run_from_mapping_to_datalake(
        self,
        config_payload: Mapping[str, Any],
        states: Iterable[Mapping[str, Any]],
        datalake_root: str | Path,
        *,
        baseline_states: Iterable[Mapping[str, Any]] | None = None,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
    ) -> FairnessWorkflowResult:
        run_spec = self.run_spec_loader.from_mapping(
            config_payload,
            fairness=fairness,
            provenance=provenance,
        )
        result = self.evaluation_service.evaluate_states(run_spec, states)
        baseline_result = None
        if baseline_states is not None:
            baseline_result = self.evaluation_service.evaluate_states(run_spec, baseline_states)
        return self.run_to_datalake(
            result,
            datalake_root,
            baseline_result=baseline_result,
            run_spec=run_spec,
        )

    def run_from_experiment_configuration(
        self,
        config: Any,
        states: Iterable[Mapping[str, Any]],
        output_dir: str | Path,
        *,
        baseline_states: Iterable[Mapping[str, Any]] | None = None,
        name: str | None = None,
        environment_family: str | None = None,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> FairnessWorkflowResult:
        run_spec = self.run_spec_loader.from_experiment_configuration(
            config,
            name=name,
            environment_family=environment_family,
            fairness=fairness,
            provenance=provenance,
            metadata=metadata,
        )
        result = self.evaluation_service.evaluate_states(run_spec, states)
        baseline_result = None
        if baseline_states is not None:
            baseline_result = self.evaluation_service.evaluate_states(run_spec, baseline_states)
        return self.run(result, output_dir, baseline_result=baseline_result, run_spec=run_spec)

    def run_from_experiment_configuration_to_datalake(
        self,
        config: Any,
        states: Iterable[Mapping[str, Any]],
        datalake_root: str | Path,
        *,
        baseline_states: Iterable[Mapping[str, Any]] | None = None,
        name: str | None = None,
        environment_family: str | None = None,
        fairness: FairnessSpec | None = None,
        provenance: ProvenanceSpec | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> FairnessWorkflowResult:
        run_spec = self.run_spec_loader.from_experiment_configuration(
            config,
            name=name,
            environment_family=environment_family,
            fairness=fairness,
            provenance=provenance,
            metadata=metadata,
        )
        result = self.evaluation_service.evaluate_states(run_spec, states)
        baseline_result = None
        if baseline_states is not None:
            baseline_result = self.evaluation_service.evaluate_states(run_spec, baseline_states)
        return self.run_to_datalake(
            result,
            datalake_root,
            baseline_result=baseline_result,
            run_spec=run_spec,
        )

    def _resolve_execution_mode_payload(self, run_spec: RunSpec | None) -> dict[str, Any] | None:
        if run_spec is None or not run_spec.provenance.execution_mode:
            return None
        return self.execution_mode_resolver.resolve(
            run_spec.provenance.execution_mode,
            notes={
                "run_spec_name": run_spec.name,
                "environment_family": run_spec.environment_family,
                "testbed_id": run_spec.testbed_id,
            },
        ).to_dict()
