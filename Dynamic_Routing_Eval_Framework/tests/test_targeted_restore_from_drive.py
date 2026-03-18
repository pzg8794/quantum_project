import copy
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


_IMPORT_ERROR = None
try:
    from daqr.config.gd_backup_manager import GoogleDriveBackupManager
except ModuleNotFoundError as exc:  # pragma: no cover
    GoogleDriveBackupManager = object
    _IMPORT_ERROR = exc


class _TargetedRestoreHarness(GoogleDriveBackupManager):
    @classmethod
    def build(cls, base_dir: Path):
        mgr = cls.__new__(cls)
        mgr.verbose = False
        mgr.dir = base_dir / "config"
        mgr.date_str = "day_20990101"
        mgr.backup_registry = {}
        mgr.registry_file_paths = {"local": base_dir / "config" / "local_backup_registry.pkl"}
        mgr.mode = "local"

        mgr.remote_available = True
        mgr.drive = object()
        mgr.in_share_drive = False

        mgr.downloaded = []
        mgr.saved_registries = []
        mgr.quantum_data_paths = {
            "obj": {
                "framework_state": {
                    "local": base_dir / "config" / "framework_state",
                    "drive": base_dir / "drive" / "framework_state",
                },
                "model_state": {
                    "local": base_dir / "config" / "model_state",
                    "drive": base_dir / "drive" / "model_state",
                },
            }
        }
        return mgr

    def download_any_date(self, component, filename):
        # Simulate Drive recovery only for "B.pkl".
        if filename != "B.pkl":
            return None
        target = self.quantum_data_paths["obj"][component]["local"] / self.date_str / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"ok")
        self.downloaded.append((component, filename, str(target)))
        return str(target)

    def save_registry(self, registry=None, *, force=False):
        self.saved_registries.append((force, copy.deepcopy(registry or self.backup_registry)))
        return True


@unittest.skipIf(_IMPORT_ERROR is not None, f"optional dependency missing for targeted-restore tests: {_IMPORT_ERROR}")
class TestTargetedRestoreFromDrive(unittest.TestCase):
    def test_restore_populates_focused_registry_and_downloads_missing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _TargetedRestoreHarness.build(base)

            # Existing local file "A.pkl".
            a_path = base / "config" / "framework_state" / mgr.date_str / "A.pkl"
            a_path.parent.mkdir(parents=True, exist_ok=True)
            a_path.write_bytes(b"a")

            expected_keys = {
                "framework_state": {"A.pkl": "A.pkl", "B.pkl": "B.pkl"},
                "model_state": {"M.pkl": "M.pkl"},
            }

            report = mgr.restore_from_drive(mgr.date_str, expected_keys)

            self.assertEqual(report["framework_state"]["total"], 2)
            self.assertEqual(report["framework_state"]["present"], 1)
            self.assertEqual(report["framework_state"]["downloaded"], 1)
            self.assertEqual(report["framework_state"]["missing"], 0)

            self.assertEqual(report["model_state"]["total"], 1)
            self.assertEqual(report["model_state"]["present"], 0)
            self.assertEqual(report["model_state"]["downloaded"], 0)
            self.assertEqual(report["model_state"]["missing"], 1)

            # Registry is focused strictly to expected keys.
            self.assertEqual(set(mgr.backup_registry.keys()), {"framework_state", "model_state"})
            self.assertEqual(set(mgr.backup_registry["framework_state"].keys()), {"A.pkl", "B.pkl"})
            self.assertEqual(set(mgr.backup_registry["model_state"].keys()), {"M.pkl"})

            self.assertEqual(mgr.backup_registry["framework_state"]["A.pkl"], str(a_path.resolve()))
            self.assertTrue(Path(mgr.backup_registry["framework_state"]["B.pkl"]).exists())

            # Missing file uses placeholder expected local path under day dir.
            m_expected = base / "config" / "model_state" / mgr.date_str / "M.pkl"
            self.assertEqual(mgr.backup_registry["model_state"]["M.pkl"], str(m_expected.resolve()))

            # Registry persistence attempted (force=True).
            self.assertTrue(any(force for force, _ in mgr.saved_registries))


if __name__ == "__main__":
    unittest.main()

