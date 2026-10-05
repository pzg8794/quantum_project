"""PR2 AttemptBundle adapter for the proven legacy evaluation workflow."""
from copy import deepcopy
from pathlib import Path
from threading import Lock

import numpy as np

from daqr.campaigns.medium_runner import prepare_manifest
from daqr.campaigns.medium_trace import (
    AttemptBundle,
    file_hash,
    validate_completion,
    validate_scale_completion,
    validate_scale_completion_by_block,
    write_json_exclusive,
)
from daqr.config.execution_contract import resolve_configuration
from daqr.core.scenario_execution import ScenarioSession
from daqr.evaluation.execution_evidence import (
    ExecutionEvidenceAttempt,
    ExecutionEvidencePlugin,
)


def finalize_medium_campaign(output_root, configuration, scale_m, bundle_paths=None,
                             block_configurations=None):
    output_root = Path(output_root).expanduser().resolve()
    if bundle_paths is None:
        bundle_paths = sorted(
            path.parent
            for path in output_root.glob("*/attempt-*/completion.json")
        )
    else:
        bundle_paths = sorted(Path(path).resolve() for path in bundle_paths)
    report = (validate_scale_completion_by_block(block_configurations, scale_m, bundle_paths)
              if block_configurations is not None else
              validate_scale_completion(configuration, scale_m, bundle_paths))
    receipt = {
        "schema_version": "medium-campaign-completion-v1",
        "state": "COMPLETE",
        "required_cells": report["required_cells"],
        "completed_cells": report["completed_cells"],
        "bundle_completion_hashes": {
            str(path.relative_to(output_root)): file_hash(path / "completion.json")
            for path in bundle_paths
        },
    }
    receipt_path = output_root / "campaign-receipt.json"
    write_json_exclusive(receipt_path, receipt)
    return receipt_path


class MediumExecutionEvidencePlugin(ExecutionEvidencePlugin):
    """Inject the frozen medium-scale manifest and trace contract at runtime."""

    def __init__(self, output_root, scale_m):
        self.output_root = Path(output_root).expanduser().resolve()
        source_root = Path(__file__).resolve().parents[3]
        if self.output_root == source_root or self.output_root.is_relative_to(source_root):
            raise ValueError("Raw campaign bundles must remain outside the source repository")
        if type(scale_m) is not int or scale_m < 1:
            raise ValueError("scale_m must be a positive integer")
        self.scale_m = scale_m
        self._block_configs = {}
        self._bundle_paths = []
        self._restart_reasons = {}
        self._lock = Lock()

    def register_block(self, block, configuration):
        block = int(block)
        resolved = resolve_configuration(configuration)
        if block not in range(resolved["blocks"]):
            raise ValueError(f"Block {block} is outside the configured matrix")
        existing = self._block_configs.get(block)
        if existing is not None and resolve_configuration(existing) != resolved:
            raise ValueError(f"Conflicting evidence configuration for block {block}")
        self._block_configs[block] = configuration

    @staticmethod
    def _result_summary(manifest, result, state="completed", error=None):
        final_reward = float(result.get("final_reward", 0.0) or 0.0)
        avg_reward = result.get("avg_reward")
        if avg_reward is None:
            avg_reward = final_reward / int(manifest["execution_frames"])
        return {
            "schema_version": "medium-result-v1",
            "run_id": manifest["run_id"],
            "identity": {
                "block": manifest["identity"]["block_id"],
                "threat": manifest["identity"]["threat"],
                "policy": manifest["identity"]["policy"],
                "policy_seed": manifest["identity"]["seeds"]["policy"]["actual_seed"],
                "threat_seed": manifest["identity"]["seeds"]["threat"]["actual_seed"],
            },
            "outcome": {
                "status": state,
                "final_reward": final_reward,
                "avg_reward": float(avg_reward),
                "frames_count": int(result.get("frames_count", manifest["execution_frames"])),
                "technical_attempts": int(result.get("retries", 0) or 0) + 1,
                "performance_reruns": 0,
                "error": error,
            },
        }

    def open_attempt(self, runtime_config, policy, threat, block, frames):
        block = int(block)
        if not bool(getattr(runtime_config, "disable_outcome_retries", False)):
            raise ValueError("Medium evidence execution requires outcome-triggered retries disabled")
        if block not in self._block_configs:
            raise ValueError(f"Missing registered evidence configuration for block {block}")
        config = self._block_configs[block]
        if int(config.execution.horizon) != int(frames):
            raise ValueError("Runtime horizon differs from registered evidence configuration")
        manifest, catalog, availability = prepare_manifest(
            config,
            policy,
            threat,
            block,
            scale_m=self.scale_m,
        )
        key = (block, str(threat), str(policy))
        restart_reason = self._restart_reasons.pop(key, None)
        bundle = AttemptBundle(
            self.output_root,
            manifest,
            catalog,
            availability,
            restart_reason=restart_reason,
        )

        def complete(result):
            write_json_exclusive(
                bundle.directory / "result.json",
                self._result_summary(manifest, result),
            )
            completion = bundle.finish()
            validate_completion(bundle.directory, manifest)
            with self._lock:
                self._bundle_paths.append(bundle.directory)
            return completion

        def fail(error):
            reason = str(error) or type(error).__name__
            write_json_exclusive(
                bundle.directory / "result.json",
                self._result_summary(
                    manifest,
                    {"frames_count": frames, "retries": 0},
                    state="failed",
                    error=reason,
                ),
            )
            completion = bundle.finish("FAILED", "infrastructure", reason)
            self._restart_reasons[key] = reason
            return completion

        static = None if isinstance(availability, ScenarioSession) else np.asarray(availability)
        session = availability if isinstance(availability, ScenarioSession) else None
        return ExecutionEvidenceAttempt(
            policy_seed=manifest["identity"]["seeds"]["policy"]["actual_seed"],
            threat_seed=manifest["identity"]["seeds"]["threat"]["actual_seed"],
            static_availability=static,
            scenario_session=session,
            event_sink=bundle.recorder,
            directory=bundle.directory,
            _complete=complete,
            _fail=fail,
        )

    def finalize(self, runtime_config):
        if not self._block_configs:
            raise ValueError("No evidence blocks were registered")
        config = self._block_configs[min(self._block_configs)]
        return finalize_medium_campaign(
            self.output_root,
            config,
            self.scale_m,
            bundle_paths=self._bundle_paths,
            block_configurations=self._block_configs,
        )
