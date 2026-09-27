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

from daqr.campaigns.medium_spec import build_catalog
from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.config.local_backup_manager import LocalBackupManager
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.evaluation.allocator_runner import AllocatorRunner
from daqr.evaluation.campaign_evidence import file_hash


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
    assert provenance["required_cells"] == 45
    assert all(
        cell.get("execution_count") is None and not cell.get("outputs")
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_notebook_uses_only_real_allocator_runner():
    notebook = load_notebook(NOTEBOOK)
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "from daqr.evaluation.allocator_runner import AllocatorRunner" in source
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
    assert namespace["models"] == ["Oracle", "CEpsilonGreedy", "EXPNeuralUCB"]
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


def test_campaign_seed_is_process_stable():
    code = """
from types import SimpleNamespace
from daqr.evaluation.campaign_evidence import stable_environment_seed
config = SimpleNamespace(
    scientific_seed_namespace='f08-tier1-default-fixed-v1',
    scientific_campaign_base_seed=12345,
    base_seed=99999,
    scientific_block_id=2,
    attack_type='adaptive',
)
print(stable_environment_seed(config, 6000))
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
        assert runner.custom_config.models == ["Oracle", "CEpsilonGreedy", "EXPNeuralUCB"]
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
    assert campaign["required_cells"] == campaign["accounted_cells"] == 45
    assert campaign["state"] == "COMPLETE"
    assert campaign["status_counts"] == {"completed": 45, "failed": 0}

    receipts = [
        json.loads(path.read_text())
        for path in sorted((evidence_root / "receipts").glob("*.json"))
    ]
    assert len(receipts) == 45
    assert {
        (item["identity"]["block"], item["identity"]["threat"], item["identity"]["policy"])
        for item in receipts
    } == set(itertools.product(range(3), SCENARIOS, namespace["models"]))
    assert len({
        item["identity"]["catalog_identity"]["topology_hash"] for item in receipts
    }) == 3

    for receipt in receipts:
        completion_path = Path(receipt["completion_path"])
        assert file_hash(completion_path) == receipt["completion_sha256"]
        completion = json.loads(completion_path.read_text())
        bundle = Path(receipt["bundle_path"])
        availability = json.loads((bundle / "availability.json").read_text())
        events = [
            json.loads(line)
            for line in (bundle / "events.jsonl").read_text().splitlines()
        ]
        assert completion["status"] == "completed"
        assert completion["availability_frames"] == 4
        assert completion["decision_event_count"] == 4
        assert completion["outcome_event_count"] == 4
        assert len(availability) == 4
        assert all(len(row) == 10 for row in availability)
        assert len(events) == 8
        for frame in range(4):
            decision, outcome = events[2 * frame : 2 * frame + 2]
            assert decision["phase"] == "DECISION"
            assert outcome["phase"] == "OUTCOME"
            assert decision["decision_id"] == outcome["decision_id"]
            assert decision["selected_route_index"] == outcome["selected_route_index"]
            route = outcome["selected_route_index"]
            assert outcome["availability"] == availability[frame][route]
            assert outcome["selected_continuous_payoff"] == pytest.approx(
                outcome["base_expected_payoff"] * outcome["availability"]
            )
