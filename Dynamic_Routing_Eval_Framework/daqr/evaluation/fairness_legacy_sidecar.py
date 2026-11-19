from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
import math

from daqr.config.run_spec import ProvenanceSpec, RunSpec
from daqr.config.run_spec_loader import RunSpecLoader
from daqr.evaluation.fairness_service import FairnessEvaluationResult
from daqr.evaluation.fairness_workflow import FairnessWorkflow, FairnessWorkflowResult


@dataclass(frozen=True)
class LegacyFairnessSidecarResult:
    run_spec: RunSpec
    states: list[dict[str, Any]]
    evaluation_result: FairnessEvaluationResult
    workflow_result: FairnessWorkflowResult


# Architecture note: compatibility boundary for the quantum side. This bridge
# lets the preserved legacy quantum evaluator feed the same fairness workflow as
# the clinical path without rewriting the quantum pipeline.
class LegacyFairnessSidecarBridge:
    """Compatibility bridge from legacy evaluator outputs into fairness sidecar artifacts."""

    def __init__(self) -> None:
        self.run_spec_loader = RunSpecLoader()
        self.workflow = FairnessWorkflow()

    # Architecture note: quantum-to-fairness attachment point. This method
    # extracts legacy states, builds provenance, creates a RunSpec, evaluates
    # fairness, and writes the result through the shared datalake workflow.
    def attach_to_legacy_evaluator(
        self,
        config: Any,
        evaluator: Any,
        *,
        run_name: str | None = None,
        datalake_root: str | Path | None = None,
        execution_mode: str = "site_local",
        source: str = "legacy-sidecar",
        fairness_testbed_id: Any | None = None,
    ) -> LegacyFairnessSidecarResult:
        states = self.extract_states(evaluator)
        provenance = ProvenanceSpec(
            source=source,
            execution_mode=execution_mode,
            artifact_lineage={
                "legacy_component": str(getattr(evaluator, "component", "framework_state")),
                "legacy_file_name": str(getattr(evaluator, "file_name", "unknown")),
            },
            environment_metadata={
                "legacy_save_to_dir": str(getattr(evaluator, "save_to_dir", "")),
            },
        )
        metadata = {
            "legacy_component": str(getattr(evaluator, "component", "framework_state")),
            "legacy_file_name": str(getattr(evaluator, "file_name", "unknown")),
            "legacy_testbed_id": str(getattr(config, "testbed_id", "None")),
        }
        if fairness_testbed_id is not None:
            metadata["fairness_testbed_id"] = str(fairness_testbed_id)

        run_spec = self.run_spec_loader.from_experiment_configuration(
            config,
            name=run_name or getattr(config, "log_name", None) or getattr(evaluator, "file_name", None),
            environment_family="quantum",
            provenance=provenance,
            metadata=metadata,
        )
        if fairness_testbed_id is not None:
            run_spec = run_spec.with_updates(testbed_id=fairness_testbed_id)
        evaluation_result = self.workflow.evaluation_service.evaluate_states(run_spec, states)
        resolved_datalake_root = self._resolve_datalake_root(evaluator, datalake_root)
        workflow_result = self.workflow.run_to_datalake(
            evaluation_result,
            resolved_datalake_root,
            run_spec=run_spec,
        )
        return LegacyFairnessSidecarResult(
            run_spec=run_spec,
            states=states,
            evaluation_result=evaluation_result,
            workflow_result=workflow_result,
        )

    # Architecture note: conversion from legacy quantum results to fairness
    # states. The bridge records model group, success, reward, latency,
    # environment, allocator, and experiment id in a common input shape.
    def extract_states(self, evaluator: Any) -> list[dict[str, Any]]:
        raw_experiments = self._iter_legacy_experiments(evaluator)
        states: list[dict[str, Any]] = []
        for scenario_name, exp_id, exp_data in raw_experiments:
            results = exp_data.get("results", {}) if isinstance(exp_data, Mapping) else {}
            for model_name, result_payload in results.items():
                if not isinstance(result_payload, Mapping):
                    continue
                final_reward = result_payload.get("final_reward")
                avg_reward = result_payload.get("avg_reward")
                reward_value = self._safe_float(final_reward if final_reward is not None else avg_reward)
                states.append(
                    {
                        "group": str(model_name),
                        "success": None if reward_value is None else float(reward_value > 0),
                        "reward": reward_value,
                        # Compatibility field: this is a frame-horizon proxy,
                        # never measured delivery latency. Saved evaluators
                        # normally store it inside each model result.
                        "latency": self._frame_proxy(result_payload, exp_data),
                        "frame_count": self._frame_proxy(result_payload, exp_data),
                        "env_type": str(scenario_name),
                        "source": "legacy_evaluator",
                        "allocator": str(getattr(evaluator, "allocator_id", getattr(getattr(evaluator, "configs", None), "allocator", "unknown"))),
                        "experiment_id": str(exp_id),
                        "legacy_model": str(model_name),
                    }
                )
        return states

    def _frame_proxy(self, result: Mapping[str, Any], experiment: Mapping[str, Any]) -> float | None:
        for payload in (result, experiment):
            for key in ("frames_count", "frame_count"):
                if payload.get(key) is not None:
                    return self._safe_float(payload[key])
        return None

    def _iter_legacy_experiments(self, evaluator: Any) -> Iterable[tuple[str, str, Mapping[str, Any]]]:
        # MultiRunEvaluator keeps the same complete experiment in both maps.
        # Prefer its original env_experiments object; evaluation_results is a
        # fallback, not a second population of model outcomes.
        seen: set[tuple[str, str]] = set()
        for source_name in ("env_experiments", "evaluation_results"):
            source = getattr(evaluator, source_name, None)
            if not isinstance(source, Mapping):
                continue
            for scenario_name, scenario_payload in source.items():
                if scenario_name == "scenarios_results" or not isinstance(scenario_payload, Mapping):
                    continue
                for exp_id, exp_data in scenario_payload.items():
                    if isinstance(exp_data, Mapping) and "results" in exp_data:
                        identity = (str(scenario_name), str(exp_id))
                        if identity not in seen:
                            seen.add(identity)
                            yield *identity, exp_data

    def _resolve_datalake_root(self, evaluator: Any, datalake_root: str | Path | None) -> Path:
        if datalake_root is not None:
            return Path(datalake_root)
        legacy_output_dir = getattr(evaluator, "save_to_dir", None)
        if legacy_output_dir is None:
            return Path("datalake")
        legacy_path = Path(legacy_output_dir)
        return legacy_path.parent if legacy_path.name.startswith("day_") else legacy_path

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except Exception:
            return None
