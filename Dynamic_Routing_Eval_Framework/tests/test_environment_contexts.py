import sys
import unittest
from pathlib import Path

try:
    import numpy  # noqa: F401
except Exception:
    numpy = None

if numpy is None:
    raise unittest.SkipTest("numpy not installed; skipping environment-context tests")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.core.attack_strategy import NoAttack
from daqr.core.network_environment import QuantumEnvironment


class TestEnvironmentContexts(unittest.TestCase):
    def test_default_routing_environment_generates_split_contexts_and_rewards(self):
        """
        Regression test: when external_contexts are not provided and we're using the
        default routing reward model, the environment must generate per-path split
        contexts (2-hop/3-hop). Dummy single-element contexts break reward calc.
        """
        env = QuantumEnvironment(
            attack=NoAttack(),
            qubit_capacities=(8, 10, 8, 9),
            allocator=None,
            noise_model=None,
            fidelity_calculator=None,
            external_contexts=None,
            external_rewards=None,
            external_topology=None,
            frame_length=4000,
            seed=123,
            test_bed=None,
        )

        # Contexts should be 4 paths with combinatorial splits
        self.assertEqual(len(env.contexts), 4)
        self.assertGreater(len(env.contexts[0]), 0)
        self.assertGreater(len(env.contexts[1]), 0)
        self.assertGreater(len(env.contexts[2]), 0)
        self.assertGreater(len(env.contexts[3]), 0)

        # The first two paths are 2-hop splits -> vectors of length 2
        self.assertEqual(len(env.contexts[0][0]), 2)
        self.assertEqual(len(env.contexts[1][0]), 2)
        # The last two paths are 3-hop splits -> vectors of length 3
        self.assertEqual(len(env.contexts[2][0]), 3)
        self.assertEqual(len(env.contexts[3][0]), 3)

        # Reward list must be non-empty and aligned with contexts
        self.assertEqual(len(env.reward_list), 4)
        for rewards in env.reward_list:
            self.assertGreater(len(rewards), 0)


if __name__ == "__main__":
    unittest.main()
