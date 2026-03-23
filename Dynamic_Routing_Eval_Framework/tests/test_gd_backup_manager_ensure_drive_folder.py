import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.gd_backup_manager import GoogleDriveBackupManager


class _DummyFilesApi:
    def __init__(self):
        self.list_calls = []
        self.create_calls = []
        self.update_calls = []
        self.list_response = {"files": []}

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self

    def update(self, **kwargs):
        self.update_calls.append(kwargs)
        return self

    def execute(self):
        if self.create_calls or self.update_calls:
            return {"id": "created-folder-id"}
        return self.list_response


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

    def test_model_state_upload_uses_exact_filename_query(self):
        manager = GoogleDriveBackupManager.__new__(GoogleDriveBackupManager)
        manager.remote_available = True
        manager.in_share_drive = False
        manager.drive_folder_id = "0AK0VchnNyM-xUk9PVA"
        manager.drive = _DummyDrive()
        manager.verbose = False
        manager._ensure_drive_folder = lambda name, parent: f"{parent}/{name}"
        manager._retry_drive = lambda fn: fn()

        with Path("/tmp/test_model_state_exact_query.pkl").open("wb") as f:
            f.write(b"abc")

        try:
            ok = GoogleDriveBackupManager._upload_file_to_drive(
                manager,
                component="model_state",
                date_str="day_20260321",
                local_path="/tmp/test_model_state_exact_query.pkl",
                filename="Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl",
            )
        finally:
            Path("/tmp/test_model_state_exact_query.pkl").unlink(missing_ok=True)

        self.assertTrue(ok)
        query = manager.drive.api.list_calls[-1]["q"]
        self.assertEqual(
            query,
            "name='Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl' and '0AK0VchnNyM-xUk9PVA/quantum_data_lake/model_state/day_20260321' in parents",
        )

    def test_registry_query_uses_exact_filename_for_model_state(self):
        manager = GoogleDriveBackupManager.__new__(GoogleDriveBackupManager)
        manager.obj_query = {}

        GoogleDriveBackupManager.set_regestry_qry(
            manager,
            "Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl",
            "day-folder-id",
        )

        self.assertEqual(
            manager.obj_query["model_state"],
            "name='Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl' and 'day-folder-id' in parents",
        )

    def test_download_uses_exact_filename_query_for_model_state(self):
        manager = GoogleDriveBackupManager.__new__(GoogleDriveBackupManager)
        manager.remote_available = True
        manager.in_share_drive = False
        manager.drive_folder_id = "0AK0VchnNyM-xUk9PVA"
        manager.drive = _DummyDrive()
        manager._ensure_drive_folder = lambda name, parent: f"{parent}/{name}"
        manager._retry_drive = lambda fn: fn()
        manager.obj_query = {}
        manager.drive.api.list_response = {
            "files": [
                {
                    "id": "file-1",
                    "name": "Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl",
                }
            ]
        }

        with TemporaryDirectory() as tempdir:
            local_root = Path(tempdir) / "model_state"
            manager.quantum_data_paths = {
                "obj": {
                    "model_state": {"local": local_root},
                }
            }

            request = object()
            manager.drive.files = lambda: manager.drive.api
            manager.drive.api.get_media = lambda fileId: request

            class _FakeDownloader:
                def __init__(self, fh, req):
                    self.fh = fh
                    self.req = req
                    self._done = False

                def next_chunk(self):
                    if not self._done:
                        self.fh.write(b"abc")
                        self._done = True
                        return None, True
                    return None, True

            from daqr.config import gd_backup_manager as gd_module

            original_downloader = gd_module.MediaIoBaseDownload
            gd_module.MediaIoBaseDownload = _FakeDownloader
            try:
                path = GoogleDriveBackupManager._download_file_from_drive(
                    manager,
                    date_str="day_20260321",
                    component="model_state",
                    filename="Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl",
                )
            finally:
                gd_module.MediaIoBaseDownload = original_downloader

        self.assertTrue(path.endswith("Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl"))
        query = manager.drive.api.list_calls[-1]["q"]
        self.assertEqual(
            query,
            "name='Oracle(base)_9000-Default_Adversarial_Adaptive-6000_paper12.pkl' and '0AK0VchnNyM-xUk9PVA/quantum_data_lake/model_state/day_20260321' in parents",
        )


if __name__ == "__main__":
    unittest.main()
