import copy
import inspect
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

import networkx as nx
import numpy as np
import pytest

from daqr.campaigns.medium_spec import build_catalog, seed_manifest
from daqr.campaigns.medium_execution_evidence import MediumExecutionEvidencePlugin
from daqr.campaigns.medium_trace import PHASES, file_hash, validate_completion
from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.local_backup_manager import LocalBackupManager
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.core.scenario_execution import ScenarioExecutionComponent
from daqr.evaluation.allocator_runner import AllocatorRunner
from medium_fixtures import FULL_MODEL_ROSTER


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NOTEBOOK = ROOT / "notebooks" / "H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb"
NOTEBOOK = ROOT / "notebooks" / "H-MABs_Eval-MediumScale-Default-FullThreat.ipynb"
SCENARIOS = {
    "stochastic": "Stochastic Random Failures",
    "markov": "Markov Adversarial Attack",
    "adaptive": "Adaptive Adversarial Attack",
    "onlineadaptive": "Online Adaptive Attack",
    "none": "Baseline (Optimal Conditions)",
}


def load_notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def notebook_namespace():
    notebook = load_notebook(NOTEBOOK)
    namespace = {
        "itertools": itertools,
        "np": np,
        "nx": nx,
        "Path": Path,
        "ExecutionSettings": ExecutionSettings,
        "ExperimentConfiguration": ExperimentConfiguration,
        "LocalBackupManager": LocalBackupManager,
        "LayeredPrimaryCatalog": LayeredPrimaryCatalog,
        "PrimaryPayoff": PrimaryPayoff,
        "QubitAllocator": QubitAllocator,
        "build_catalog": build_catalog,
        "MediumExecutionEvidencePlugin": MediumExecutionEvidencePlugin,
    }
    exec("".join(notebook["cells"][4]["source"]), namespace)
    exec("".join(notebook["cells"][6]["source"]), namespace)
    return namespace


def test_notebook_preserves_pinned_setup_through_default_run():
    source = load_notebook(SOURCE_NOTEBOOK)
    notebook = load_notebook(NOTEBOOK)
    provenance = notebook["metadata"]["quantum_medium_provenance"]

    assert len(notebook["cells"]) == 11
    assert [cell["cell_type"] for cell in notebook["cells"][:10]] == [
        cell["cell_type"] for cell in source["cells"][:10]
    ]
    assert [cell.get("id") for cell in notebook["cells"][:10]] == [
        cell.get("id") for cell in source["cells"][:10]
    ]
    assert notebook["cells"][1] == source["cells"][1]
    assert provenance["source_commit"] == "96b327de7e3571ad3cbf05bbeee02cfb922ca2c3"
    assert provenance["source_blob"] == "599bb49b58a41fc98ff7d6f10c4077c941507269"
    assert provenance["source_sha256"] == "714eefbd1eafc3c66347fc6b0460e6aaf706ad25b1ea411bcc89ac317a4711c9"
    assert provenance["copied_source_cells"] == list(range(10))
    assert provenance["runner_module"] == "daqr.evaluation.allocator_runner"
    assert provenance["required_threats"] == list(SCENARIOS)
    assert provenance["required_models"] == FULL_MODEL_ROSTER
    assert provenance["required_cells"] == 75
    assert all(
        cell.get("execution_count") is None and not cell.get("outputs")
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_notebook_uses_only_real_allocator_runner():
    notebook = load_notebook(NOTEBOOK)
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "from daqr.evaluation.allocator_runner import AllocatorRunner" in source
    assert "MediumExecutionEvidencePlugin" in source
    assert "daqr.campaigns.medium_scientific" not in source
    assert inspect.getmodule(AllocatorRunner).__name__ == "daqr.evaluation.allocator_runner"
    assert not (ROOT / "daqr" / "campaigns" / "medium_scientific.py").exists()
    assert "class AllocatorRunner" not in (ROOT / "daqr" / "campaigns" / "medium_runner.py").read_text()


def test_frozen_notebook_config_and_external_catalog():
    namespace = notebook_namespace()
    assert namespace["BASE_FRAMES"] == 6000
    assert namespace["FRAME_STEP"] == 0
    assert namespace["RUNS"] == [3]
    assert namespace["SCALES"] == [2]
    assert namespace["models"] == FULL_MODEL_ROSTER
    assert list(namespace["test_scenarios"]) == list(SCENARIOS)
    assert namespace["FRAMEWORK_CONFIG"]["capacity"] == 12000
    assert namespace["FRAMEWORK_CONFIG"]["scientific_block_ids"] == [0, 1, 2]
    assert namespace["FRAMEWORK_CONFIG"]["medium_tier1"]["baseline_allocation"] == (9,) * 10

    identities = []
    for block in range(3):
        params = namespace["get_physics_params"](
            "medium_tier1",
            6000,
            12345,
            (9,) * 10,
            block_id=block,
        )
        assert params["external_topology"].number_of_nodes() == 15
        assert len(params["external_contexts"]) == len(params["external_rewards"]) == 10
        assert sum(len(actions) for actions in params["external_contexts"]) == 550
        assert all(actions.shape[1] == 3 for actions in params["external_contexts"])
        assert params["_campaign_catalog_identity"]["block"] == block
        components = params["_scenario_execution_components"]
        assert list(components) == list(SCENARIOS)
        assert all(
            isinstance(component, ScenarioExecutionComponent)
            for component in components.values()
        )
        evidence_config = params["_execution_evidence_configuration"]
        assert evidence_config.execution.horizon == 6000
        assert evidence_config.execution.protocol_namespace == "f08-tier1-default-fixed-full-roster-v2"
        identities.append(params["_campaign_catalog_identity"])
    assert len({item["topology_hash"] for item in identities}) == 3


def test_external_output_root_rejects_source_repository():
    namespace = notebook_namespace()
    config = ExperimentConfiguration(
        models=["Oracle"],
        scenarios={"none": "Baseline"},
        allocator=QubitAllocator(),
        persistence=False,
    )
    with pytest.raises(ValueError, match="outside"):
        namespace["configure_external_persistence"](config, ROOT)


def test_result_summary_derives_mean_continuous_payoff():
    manifest = {
        "run_id": "run",
        "execution_frames": 4,
        "identity": {
            "block_id": 0,
            "threat": "none",
            "policy": "Oracle",
            "seeds": {
                "policy": {"actual_seed": 11},
                "threat": {"actual_seed": None},
            },
        },
    }
    summary = MediumExecutionEvidencePlugin._result_summary(
        manifest,
        {"final_reward": 2.0, "frames_count": 4, "retries": 0},
    )
    assert summary["outcome"]["avg_reward"] == 0.5


def test_campaign_seed_is_process_stable():
    code = """
from tests.medium_fixtures import fixture_config
from daqr.campaigns.medium_spec import seed_manifest
print(seed_manifest(fixture_config(), 2, 'EXPNeuralUCB', 'RandomAttack', 3)['policy']['actual_seed'])
"""
    values = []
    for hash_seed in ("1", "987654"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        values.append(
            subprocess.check_output(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env=env,
                text=True,
            ).strip()
        )
    assert values[0] == values[1]


def test_real_runner_dispatches_frozen_full_spectrum(monkeypatch):
    namespace = notebook_namespace()
    initial_allocator = QubitAllocator(
        total_qubits=90,
        num_routes=10,
        min_qubits_per_route=1,
        baseline_allocation=(9,) * 10,
    )
    config = ExperimentConfiguration(
        models=namespace["models"],
        scenarios=namespace["test_scenarios"],
        runs=3,
        scale=2,
        base_capacity=True,
        base_seed=12345,
        allocator=initial_allocator,
        persistence=False,
        resume=False,
        use_last_backup=False,
        overwrite=False,
    )
    runner = AllocatorRunner(
        allocator_type="Default",
        physics_models=["medium_tier1"],
        framework_config=namespace["FRAMEWORK_CONFIG"],
        scales=[2],
        runs=[3],
        models=namespace["models"],
        test_scenarios=namespace["test_scenarios"],
        config=config,
    )
    calls = []

    monkeypatch.setattr(runner, "_aggregate_state_dirs", lambda: False)
    monkeypatch.setattr(runner, "cleanup_evaluator", lambda verbose=False: True)
    monkeypatch.setattr("daqr.evaluation.allocator_runner.time.sleep", lambda _: None)

    def bounded_dispatch(**kwargs):
        calls.append(kwargs)
        assert list(runner.custom_config.test_scenarios) == list(SCENARIOS)
        assert runner.custom_config.models == FULL_MODEL_ROSTER
        assert kwargs["physics_params"]["external_topology"].number_of_nodes() == 15
        assert len(kwargs["physics_params"]["external_contexts"]) == 10
        return True

    monkeypatch.setattr(runner, "run_single_evaluator", bounded_dispatch)
    runner.run(get_physics_params_func=namespace["get_physics_params"])

    assert len(calls) == 1
    assert calls[0]["experiment_num"] == 3
    assert calls[0]["scale"] == 2
    assert calls[0]["current_frames"] == 6000
    assert calls[0]["frame_step"] == 0
    assert tuple(runner.allocator_obj or ()) == ()
    assert sorted(runner.custom_config.scientific_block_physics) == [0, 1, 2]
    assert len({
        item["topology_hash"]
        for item in runner.custom_config.scientific_catalog_identities.values()
    }) == 3


def test_real_runner_tiny_full_matrix_writes_complete_event_evidence(tmp_path, monkeypatch):
    namespace = notebook_namespace()
    namespace["BASE_FRAMES"] = 4
    framework = copy.deepcopy(namespace["FRAMEWORK_CONFIG"])
    framework["base_frames"] = 4
    framework["capacity"] = 8
    framework["aggregate_state"] = False
    framework["enable_plots"] = False

    initial_allocator = QubitAllocator(
        total_qubits=90,
        num_routes=10,
        min_qubits_per_route=1,
        baseline_allocation=(9,) * 10,
    )
    config = ExperimentConfiguration(
        env_type=framework["main_env"],
        scenarios=namespace["test_scenarios"],
        use_last_backup=False,
        resume=False,
        models=namespace["models"],
        attack_intensity=namespace["ATTACK_INTENSITY"],
        attack_rate=namespace["ATTACK_INTENSITY"],
        scale=2,
        base_capacity=True,
        overwrite=False,
        base_seed=12345,
        allocator=initial_allocator,
        persistence=False,
    )
    namespace["configure_external_persistence"](config, tmp_path)
    runner = AllocatorRunner(
        allocator_type="Default",
        physics_models=["medium_tier1"],
        framework_config=framework,
        scales=[2],
        runs=[3],
        models=namespace["models"],
        test_scenarios=namespace["test_scenarios"],
        config=config,
    )
    monkeypatch.setattr(runner, "_aggregate_state_dirs", lambda: False)
    monkeypatch.setattr("daqr.evaluation.allocator_runner.time.sleep", lambda _: None)
    runner.run(get_physics_params_func=namespace["get_physics_params"])

    evidence_root = tmp_path / "q04-evidence"
    campaign = json.loads((evidence_root / "campaign-receipt.json").read_text())
    assert campaign["required_cells"] == campaign["completed_cells"] == 75
    assert campaign["state"] == "COMPLETE"
    assert len(campaign["bundle_completion_hashes"]) == 75
    assert not (evidence_root / "receipts").exists()

    bundles = sorted(evidence_root.glob("*/attempt-*"))
    assert len(bundles) == 75
    manifests = [json.loads((bundle / "manifest.json").read_text()) for bundle in bundles]
    assert {
        (item["identity"]["block_id"], item["identity"]["threat"], item["identity"]["policy"])
        for item in manifests
    } == set(itertools.product(range(3), SCENARIOS, namespace["models"]))
    assert len({
        item["identity"]["topology_hash"] for item in manifests
    }) == 3

    for block, threat in itertools.product(range(3), SCENARIOS):
        matched = [
            item for item in manifests
            if item["identity"]["block_id"] == block and item["identity"]["threat"] == threat
        ]
        expected_config = runner.custom_config.execution_evidence_plugin._block_configs[block]
        for item in matched:
            expected = seed_manifest(
                expected_config,
                block,
                item["identity"]["policy"],
                threat,
                3,
            )
            assert item["identity"]["seeds"] == expected
        if threat in {"adaptive", "onlineadaptive"}:
            assert {
                item["identity"]["trajectory_kind"] for item in matched
            } == {"policy-reactive-causal"}
            assert len({
                item["identity"]["seeds"]["threat"]["actual_seed"] for item in matched
            }) == 1
        else:
            assert {
                item["identity"]["trajectory_kind"] for item in matched
            } == {"exogenous-precomputed"}
            assert len({
                item["identity"]["threat_trajectory_hash"] for item in matched
            }) == 1

    zero_outcomes = 0
    for bundle in bundles:
        manifest = json.loads((bundle / "manifest.json").read_text())
        completion = validate_completion(bundle, manifest)
        availability = json.loads((bundle / "availability.json").read_text())
        events = [
            json.loads(line)
            for line in (bundle / "events.jsonl").read_text().splitlines()
        ]
        assert completion["state"] == "COMPLETE"
        assert completion["actual_record_counts"] == {phase: 4 for phase in PHASES}
        assert "result.json" in completion["file_hashes"]
        assert file_hash(bundle / "result.json") == completion["file_hashes"]["result.json"]
        result = json.loads((bundle / "result.json").read_text())
        assert result["outcome"]["status"] == "completed"
        assert result["outcome"]["performance_reruns"] == 0
        assert result["outcome"]["avg_reward"] == pytest.approx(
            result["outcome"]["final_reward"] / 4
        )
        assert result["identity"]["policy_seed"] == manifest["identity"]["seeds"]["policy"]["actual_seed"]
        zero_outcomes += int(result["outcome"]["final_reward"] == 0.0)
        for artifact in (
            "topology.json", "routes.json", "observations.json", "physics.json",
            "catalog_diagnostics.json", "availability.json", "events.jsonl",
        ):
            assert artifact in completion["file_hashes"]
        assert len(availability) == 4
        assert all(len(row) == 10 for row in availability)
        assert len(events) == 16
        for frame in range(4):
            preselection, decision, outcome, update = events[4 * frame : 4 * frame + 4]
            assert [preselection["phase"], decision["phase"], outcome["phase"], update["phase"]] == list(PHASES)
            assert decision["phase"] == "DECISION"
            assert outcome["phase"] == "OUTCOME"
            assert len({row["decision_id"] for row in (preselection, decision, outcome, update)}) == 1
            route = decision["selected_route_index"]
            assert outcome["availability"] == availability[frame][route]
            assert outcome["selected_continuous_payoff"] == pytest.approx(
                outcome["base_expected_payoff"] * outcome["availability"]
            )
            if manifest["identity"]["policy"] == "EXPNeuralUCB":
                assert outcome["sampled_bernoulli_draw"] in (0, 1)
                assert update["importance_weighted_route_update"] is not None
            elif manifest["identity"]["policy"] in {"GNeuralUCB", "CPursuitNeuralUCB"}:
                assert outcome["sampled_bernoulli_draw"] in (0, 1)
                assert update["direct_route_update"] == outcome["masked_route_feedback"]
            elif manifest["identity"]["policy"] == "iCPursuitNeuralUCB":
                assert outcome["sampled_bernoulli_draw"] is None
                assert outcome["masked_route_feedback"] is None
                assert update["direct_route_update"] == outcome["selected_continuous_payoff"]
            else:
                assert update["policy_update_target"] == outcome["selected_continuous_payoff"]
    assert zero_outcomes > 0
