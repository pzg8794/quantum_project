import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from daqr.evaluation.campaign_evidence import record_experiment_evidence
from daqr.evaluation.experiment_runner import QuantumExperimentRunner


class ZeroRewardModel:
    def __init__(self):
        self.save_calls = 0

    def save(self):
        self.save_calls += 1


class ZeroRewardEnvironment:
    attack = "None"
    attack_rate = 0.0
    frame_length = 1

    def __str__(self):
        return "Baseline"

    def get_environment_info(self):
        return {
            "attack_pattern": np.ones((1, 1), dtype=int),
            "reward_functions": [np.array([0.0])],
        }


def test_campaign_retains_zero_oracle_and_runs_downstream_policy(tmp_path):
    evidence_root = tmp_path / "evidence"
    catalog_identity = {
        "block": 0,
        "topology_hash": "topology-zero",
        "route_set_hash": "routes-zero",
        "action_catalog_hash": "actions-zero",
        "observation_catalog_hash": "observations-zero",
        "physics_hash": "physics-zero",
    }
    trace_catalog = {
        "routes": [{"route_id": "route-0"}],
        "observations": {
            "routes": [{"route_id": "route-0", "actions": [[1]]}],
        },
        "physics": {"base_expected_payoffs": [[0.0]]},
    }
    configs = SimpleNamespace(
        disable_outcome_retries=True,
        overwrite=False,
        scale=2,
        thresholds={},
        scientific_evidence_root=evidence_root,
        scientific_seed_namespace="q04-zero-oracle-regression",
        scientific_campaign_base_seed=12345,
        scientific_block_id=0,
        scientific_catalog_identities={0: catalog_identity},
        scientific_trace_catalogs={0: trace_catalog},
        base_seed=12345,
        models=["Oracle", "CEpsilonGreedy"],
        test_scenarios={"none": "Baseline"},
        runs=1,
        base_capacity=True,
        allocator="Default",
        algorithm_configs={
            "Oracle": {"seed_offset": 2},
            "CEpsilonGreedy": {"seed_offset": 8},
        },
        attack_type="none",
    )
    runner = QuantumExperimentRunner.__new__(QuantumExperimentRunner)
    runner.configs = configs
    runner.results = {}
    runner.winner = None
    runner.frames_count = 1
    runner.capacity = 1
    runner.id = 1
    runner.environment = ZeroRewardEnvironment()
    runner.display_experiment_conditions = lambda: None
    runner._get_min_efficiency = lambda _policy: 0.5

    calls = []
    models = {}

    def run_algorithm(policy):
        calls.append(policy)
        model = ZeroRewardModel()
        models[policy] = model
        return {
            "algorithm": policy,
            "final_reward": 0.0,
            "avg_reward": 0.0,
            "frames_count": 1,
            "attack_type": "none",
            "model_results": {
                "path_action_list": [[0, 0]],
                "final_reward": 0.0,
            },
            "retries": 0,
        }, model

    runner.run_algorithm = run_algorithm
    experiment_results = runner.run_experiment(
        frames_count=1,
        models=configs.models,
        base_model="Oracle",
    )

    assert calls == ["Oracle", "CEpsilonGreedy"]
    assert models["Oracle"].save_calls == 1
    assert experiment_results["results"]["Oracle"]["final_reward"] == 0.0
    assert experiment_results["results"]["CEpsilonGreedy"]["final_reward"] == 0.0
    assert all(
        "error" not in result
        for result in experiment_results["results"].values()
    )

    receipts = record_experiment_evidence(
        configs,
        experiment_results,
        block=0,
        threat="none",
        frames=1,
        environment=runner.environment,
    )

    assert len(receipts) == 2
    for receipt_path in receipts:
        receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        bundle = Path(receipt["bundle_path"])
        result = json.loads((bundle / "result.json").read_text(encoding="utf-8"))
        completion = json.loads((bundle / "completion.json").read_text(encoding="utf-8"))
        assert receipt["status"] == "completed"
        assert result["outcome"] == {
            "status": "completed",
            "final_reward": 0.0,
            "avg_reward": 0.0,
            "efficiency": 0.0,
            "gap": 0.0 if receipt["identity"]["policy"] == "Oracle" else 100.0,
            "error": None,
            "technical_attempts": 1,
            "performance_reruns": 0,
        }
        assert completion["status"] == "completed"
        assert completion["availability_frames"] == 1
        assert completion["decision_event_count"] == 1
        assert completion["outcome_event_count"] == 1
