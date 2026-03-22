import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.gd_backup_manager import GoogleDriveBackupManager


class _DummyFilesApi:
    def __init__(self):
        self.list_calls = []
        self.create_calls = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self

    def execute(self):
        if self.create_calls:
            return {"id": "created-folder-id"}
        return {"files": []}


class _DummyDrive:
    def __init__(self):
        self.api = _DummyFilesApi()

    def files(self):
        return self.api


class TestEnsureDriveFolder(unittest.TestCase):
    def test_shared_drive_root_query_and_create_use_drive_id_parent(self):
        manager = GoogleDriveBackupManager.__new__(GoogleDriveBackupManager)
        manager.remote_available = True
        manager.drive_folder_id = "0AK0VchnNyM-xUk9PVA"
        manager.drive = _DummyDrive()

        folder_id = GoogleDriveBackupManager._ensure_drive_folder(
            manager,
            "quantum_data_lake",
            manager.drive_folder_id,
        )

        self.assertEqual(folder_id, "created-folder-id")
        self.assertEqual(len(manager.drive.api.list_calls), 1)
        self.assertEqual(len(manager.drive.api.create_calls), 1)

        list_kwargs = manager.drive.api.list_calls[0]
        self.assertEqual(list_kwargs["corpora"], "drive")
        self.assertEqual(list_kwargs["driveId"], "0AK0VchnNyM-xUk9PVA")
        self.assertIn("'0AK0VchnNyM-xUk9PVA' in parents", list_kwargs["q"])

        create_kwargs = manager.drive.api.create_calls[0]
        self.assertEqual(
            create_kwargs["body"]["parents"],
            ["0AK0VchnNyM-xUk9PVA"],
        )


if __name__ == "__main__":
    unittest.main()
