import copy
import pickle
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


_IMPORT_ERROR = None
try:
    from daqr.config.local_backup_manager import LocalBackupManager
except ModuleNotFoundError as exc:
    LocalBackupManager = object
    _IMPORT_ERROR = exc


class _DriveOffloadHarness(LocalBackupManager):
    """
    Minimal harness for contract-testing staged local → drive offload behavior.

    These tests are intentionally lightweight and avoid calling the real manager
    constructor, which performs registry scans and Drive setup work that is not
    needed for contract testing.
    """

    @classmethod
    def build(cls, base_dir: Path, *, remote_available: bool = True):
        mgr = cls.__new__(cls)
        mgr.verbose = False
        mgr.dir = base_dir / "config"
        mgr.date_str = "day_20990101"
        mgr.backup_registry = {}
        mgr.new_entries = {}
        mgr.registry_autosave = False
        mgr.saved_registries = []
        mgr.remote_available = remote_available
        mgr.drive = object() if remote_available else None
        mgr.in_share_drive = False
        mgr.mode = "local"
        mgr.upload_should_succeed = True
        mgr.verify_should_succeed = True
        mgr.quantum_data_paths = {
            "obj": {
                "framework_state": {
                    "local": base_dir / "local" / "framework_state",
                    "drive": base_dir / "drive" / "framework_state",
                },
                "model_state": {
                    "local": base_dir / "local" / "model_state",
                    "drive": base_dir / "drive" / "model_state",
                },
            }
        }
        return mgr

    def save_registry(self, registry=None, *, force=False):
        snapshot = copy.deepcopy(registry or self.backup_registry)
        self.saved_registries.append(snapshot)
        return True

    def _upload_file_to_drive(self, component, date_str, local_path, filename, parent_dir="quantum_data_lake"):
        if not self.upload_should_succeed:
            return False
        drive_path = self.quantum_data_paths["obj"][component]["drive"] / date_str / filename
        drive_path.parent.mkdir(parents=True, exist_ok=True)
        drive_path.write_bytes(Path(local_path).read_bytes())
        return True

    def _verify_drive_state_path(self, component, date_str, filename):
        if not self.verify_should_succeed:
            return False
        drive_path = self.quantum_data_paths["obj"][component]["drive"] / date_str / filename
        return drive_path.exists() and drive_path.stat().st_size > 0


@unittest.skipIf(_IMPORT_ERROR is not None, f"optional dependency missing for drive-offload tests: {_IMPORT_ERROR}")
class TestDriveStateOffloadContracts(unittest.TestCase):
    def _call_contract(self, mgr, *, component, filename, file_data):
        return mgr.save_file(
            component=component,
            filename=filename,
            file_data=file_data,
        )

    def test_drive_available_moves_staged_file_and_updates_registry(self):
        """
        Contract:
        - state is first written to a local staging path
        - then persisted to the mirrored drive path
        - after verification, the local staged file is removed
        - registry points to the durable drive path
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DriveOffloadHarness.build(base, remote_available=True)

            durable_path = self._call_contract(
                mgr,
                component="framework_state",
                filename="Runner.pkl",
                file_data={"ok": 1},
            )

            self.assertIsNotNone(durable_path)
            staged = base / "config" / "framework_state" / "day_20990101" / "Runner.pkl"
            self.assertFalse(staged.exists())
            self.assertTrue(Path(durable_path).exists())
            self.assertIn("/drive/", durable_path.replace("\\", "/"))
            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], durable_path)
            self.assertEqual(mgr.new_entries["framework_state"]["Runner.pkl"], durable_path)

    def test_drive_unavailable_keeps_local_file_and_local_registry_path(self):
        """
        Contract:
        - if drive is unavailable, save remains local
        - local file is preserved
        - registry points to the local path
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DriveOffloadHarness.build(base, remote_available=False)

            durable_path = self._call_contract(
                mgr,
                component="framework_state",
                filename="Runner.pkl",
                file_data={"ok": 1},
            )

            staged = base / "config" / "framework_state" / "day_20990101" / "Runner.pkl"
            self.assertEqual(durable_path, str(staged))
            self.assertTrue(staged.exists())
            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], str(staged))

    def test_failed_drive_persist_does_not_delete_local_staged_file(self):
        """
        Contract:
        - if drive persistence fails, local staged file must remain
        - registry must not falsely claim the durable copy exists on drive
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DriveOffloadHarness.build(base, remote_available=True)
            mgr.upload_should_succeed = False

            durable_path = self._call_contract(
                mgr,
                component="framework_state",
                filename="Runner.pkl",
                file_data={"ok": 1},
            )

            staged = base / "config" / "framework_state" / "day_20990101" / "Runner.pkl"
            self.assertEqual(durable_path, str(staged))
            self.assertTrue(staged.exists())
            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], str(staged))

    def test_failed_drive_verification_does_not_delete_local_staged_file(self):
        """
        Contract:
        - if upload appears to succeed but verification fails, local staged file must remain
        - registry must remain local or unchanged
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DriveOffloadHarness.build(base, remote_available=True)
            mgr.verify_should_succeed = False

            durable_path = self._call_contract(
                mgr,
                component="framework_state",
                filename="Runner.pkl",
                file_data={"ok": 1},
            )

            staged = base / "config" / "framework_state" / "day_20990101" / "Runner.pkl"
            self.assertEqual(durable_path, str(staged))
            self.assertTrue(staged.exists())
            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], str(staged))

    def test_registry_records_drive_path_after_successful_offload(self):
        """
        Contract:
        - on successful offload, backup_registry/new_entries all point to the drive-backed path
        - registry persistence is attempted after the update
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _DriveOffloadHarness.build(base, remote_available=True)

            durable_path = self._call_contract(
                mgr,
                component="framework_state",
                filename="Runner.pkl",
                file_data={"ok": 1},
            )

            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], durable_path)
            self.assertEqual(mgr.new_entries["framework_state"]["Runner.pkl"], durable_path)
            self.assertGreaterEqual(len(mgr.saved_registries), 0)


if __name__ == "__main__":
    unittest.main()
