import sys
import unittest
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.state_registry import register_state_path, get_registered_state_path


class _DummyBackupMgr:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.backup_registry = {}
        self.new_entries = {}
        self.saved_registries = []

    def save_registry(self, registry=None):
        # Record that persistence was attempted and store the last snapshot passed in.
        self.saved_registries.append(registry or self.backup_registry)
        return True


class _DummyObj:
    component = "framework_state"
    file_name = "DummyRunner.pkl"

    def __str__(self):
        return "DummyObj"


class TestRegistryUpdateOnSave(unittest.TestCase):
    def test_register_state_path_updates_and_persists_registry(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DummyBackupMgr(base)
            config_registry = {}

            obj = _DummyObj()
            saved_path = str(base / obj.component / "day_20990101" / obj.file_name)
            Path(saved_path).parent.mkdir(parents=True, exist_ok=True)
            Path(saved_path).write_bytes(b"dummy")

            register_state_path(
                config_registry=config_registry,
                backup_mgr=mgr,
                component=obj.component,
                filename=obj.file_name,
                path=saved_path,
            )

            self.assertEqual(config_registry[obj.component][obj.file_name], saved_path)
            self.assertEqual(mgr.backup_registry[obj.component][obj.file_name], saved_path)
            self.assertEqual(mgr.new_entries[obj.component][obj.file_name], saved_path)
            self.assertGreaterEqual(len(mgr.saved_registries), 1)

            # Second identical registration should be a no-op (no extra persistence).
            register_state_path(
                config_registry=config_registry,
                backup_mgr=mgr,
                component=obj.component,
                filename=obj.file_name,
                path=saved_path,
            )
            self.assertEqual(len(mgr.saved_registries), 1)

    def test_register_state_path_respects_autosave_toggle(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DummyBackupMgr(base)
            mgr.registry_autosave = False
            config_registry = {}

            register_state_path(
                config_registry=config_registry,
                backup_mgr=mgr,
                component="framework_state",
                filename="Any.pkl",
                path=str(base / "framework_state" / "day_20990101" / "Any.pkl"),
            )

            self.assertEqual(config_registry["framework_state"]["Any.pkl"], str(base / "framework_state" / "day_20990101" / "Any.pkl"))
            self.assertEqual(mgr.backup_registry["framework_state"]["Any.pkl"], str(base / "framework_state" / "day_20990101" / "Any.pkl"))
            self.assertEqual(len(mgr.saved_registries), 0)

    def test_get_registered_state_path_reads_legacy_string_entry(self):
        registry = {
            "framework_state": {
                "Runner.pkl": "/tmp/framework_state/day_20990101/Runner.pkl",
            }
        }

        self.assertEqual(
            get_registered_state_path(
                config_registry=registry,
                component="framework_state",
                filename="Runner.pkl",
            ),
            "/tmp/framework_state/day_20990101/Runner.pkl",
        )

    def test_get_registered_state_path_reads_canonical_state_entry(self):
        registry = {
            "state": {
                "Runner.pkl": {
                    "active_path": "/tmp/framework_state/day_20990101/Runner.pkl",
                    "drive_path": "/drive/framework_state/day_20990101/Runner.pkl",
                    "offload_status": "active",
                    "ready_for_offload": False,
                }
            }
        }

        self.assertEqual(
            get_registered_state_path(
                config_registry=registry,
                component="framework_state",
                filename="Runner.pkl",
            ),
            "/tmp/framework_state/day_20990101/Runner.pkl",
        )

    def test_get_registered_state_path_falls_back_to_drive_path(self):
        registry = {
            "state": {
                "Runner.pkl": {
                    "active_path": "",
                    "drive_path": "/drive/framework_state/day_20990101/Runner.pkl",
                    "offload_status": "uploaded",
                    "ready_for_offload": True,
                }
            }
        }

        self.assertEqual(
            get_registered_state_path(
                config_registry=registry,
                component="framework_state",
                filename="Runner.pkl",
            ),
            "/drive/framework_state/day_20990101/Runner.pkl",
        )


if __name__ == "__main__":
    unittest.main()
