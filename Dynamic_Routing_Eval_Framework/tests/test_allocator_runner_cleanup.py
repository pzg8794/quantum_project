import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.evaluation.allocator_runner import AllocatorRunner


class _DummyBackupMgr:
    def __init__(self):
        self.stopped = False

    def stop_logging_redirect(self):
        self.stopped = True


class _DummyTopology:
    def __init__(self):
        self.cleared = False

    def clear(self):
        self.cleared = True


class _DummyEnv:
    def __init__(self):
        self.topology = _DummyTopology()
        self.paths = [1, 2, 3]


class _DummyConfig:
    def __init__(self):
        self.backup_mgr = _DummyBackupMgr()
        self.environment = _DummyEnv()


class _DummyEvaluator:
    def __init__(self, cfg):
        self.configs = cfg


class TestAllocatorRunnerCleanup(unittest.TestCase):
    def test_cleanup_does_not_drop_shared_config(self):
        cfg = _DummyConfig()
        runner = AllocatorRunner(
            allocator_type="Default",
            physics_models=["paper8"],
            framework_config={},
            scales=[1],
            runs=[1],
            models=["Oracle"],
            test_scenarios={"stochastic": "Stochastic"},
            config=cfg,
        )

        runner.evaluator = _DummyEvaluator(cfg)
        self.assertIs(runner.custom_config, cfg)
        self.assertIsNotNone(cfg.backup_mgr)

        runner.cleanup_evaluator(verbose=False)

        # Must keep the shared config for subsequent runs (critical for stable run settings).
        self.assertIs(runner.custom_config, cfg)
        self.assertIsNotNone(cfg.backup_mgr)

        # Cleanup should detach evaluator->configs and clear environment to avoid memory growth.
        self.assertIsNone(cfg.environment)


if __name__ == "__main__":
    unittest.main()

