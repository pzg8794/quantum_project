import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.experiment_config import ExperimentConfiguration


class _DummyBackupMgr:
    def __init__(self):
        self.remote_available = True
        self.delete_calls = []

    def delete_from_drive(self, component, filename):
        self.delete_calls.append((component, filename))
        return True


class TestExperimentConfigDeleteFile(unittest.TestCase):
    def test_delete_file_keeps_remote_backup(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "framework_state" / "day_20990101" / "Runner_paper12.pkl"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text("bad state")

            backup_mgr = _DummyBackupMgr()
            config = ExperimentConfiguration.__new__(ExperimentConfiguration)
            config.backup_mgr = backup_mgr
            config.backup_registry = {
                "framework_state": {
                    "Runner_paper12.pkl": str(state_path),
                }
            }
            save_calls = []
            config.save = lambda: save_calls.append("saved")

            obj = SimpleNamespace(component="framework_state", file_name="Runner_paper12.pkl")

            ok = ExperimentConfiguration.delete_file(config, state_path, obj)

            self.assertTrue(ok)
            self.assertFalse(state_path.exists())
            self.assertEqual(backup_mgr.delete_calls, [])
            self.assertNotIn("Runner_paper12.pkl", config.backup_registry["framework_state"])
            self.assertEqual(save_calls, ["saved"])


if __name__ == "__main__":
    unittest.main()
