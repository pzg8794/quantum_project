import inspect
import itertools
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

from daqr.campaigns.medium_spec import build_catalog
from daqr.config.execution_contract import ExecutionSettings
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.catalog_components import LayeredPrimaryCatalog, PrimaryPayoff
from daqr.core.qubit_allocator import QubitAllocator
from daqr.evaluation.allocator_runner import AllocatorRunner


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
    assert namespace["FRAMEWORK_CONFIG"]["medium_tier1"]["baseline_allocation"] == (9,) * 10

    params = namespace["get_physics_params"](
        "medium_tier1",
        6000,
        12345,
        (9,) * 10,
    )
    assert params["external_topology"].number_of_nodes() == 15
    assert len(params["external_contexts"]) == len(params["external_rewards"]) == 10
    assert sum(len(actions) for actions in params["external_contexts"]) == 550
    assert all(actions.shape[1] == 3 for actions in params["external_contexts"])


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
