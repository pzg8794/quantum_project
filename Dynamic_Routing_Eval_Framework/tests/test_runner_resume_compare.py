import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.evaluation.experiment_runner import QuantumExperimentRunner


class _DummyCfg:
    def __init__(self):
        self.models = ["Oracle", "ModelA"]
        self.allocator = "Default"


class TestRunnerResumeCompare(unittest.TestCase):
    def test_runner_eq_accepts_missing_optional_key_attrs(self):
        """
        Regression test: older pickles may omit optional key_attrs such as 'test_bed'.
        Runner resume comparisons should treat missing keys as default-equivalent.
        """
        runner = QuantumExperimentRunner.__new__(QuantumExperimentRunner)
        runner.configs = _DummyCfg()
        runner.id = 1
        runner.allocator_id = "Default"
        runner.env_id = "Stochastic"
        runner.attack_id = "Random"
        runner.cap_id = 8000
        runner.key_attrs = {
            "attack": "None",
            "qubit_capacities": "(8, 10, 8, 9)",
            "frame_length": "4000",
            "allocator": "Default",
            "env_type": "stochastic",
            "entanglement_success_factor": "100",
            "test_bed": "None",
            # Extra keys that should be ignored by resume compare
            "actk_type": "stochastic",
            "external_topology": "None",
        }

        saved_state = {
            "id": 1,
            "allocator_id": "Default",
            "env_id": "Stochastic",
            "attack_id": "Random",
            "cap_id": 8000,
            "key_attrs": {
                "attack": "None",
                "qubit_capacities": "(8, 10, 8, 9)",
                "frame_length": "4000",
                "allocator": "Default",
                "env_type": "stochastic",
                # Intentionally omit 'test_bed' to simulate older saved state
                "entanglement_success_factor": "100",
            },
            "results": {
                "Oracle": {"final_reward": 1.0},
                "ModelA": {"final_reward": 1.0},
            },
        }

        self.assertTrue(runner == saved_state)


if __name__ == "__main__":
    unittest.main()

