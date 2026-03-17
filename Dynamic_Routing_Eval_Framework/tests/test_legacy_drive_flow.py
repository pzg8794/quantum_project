import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.local_backup_manager import LocalBackupManager
import daqr.config.gd_backup_manager as gd_module


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeDriveFiles:
    def __init__(self, service):
        self.service = service

    def list(self, q=None, **kwargs):
        parent_id = None
        if q:
            import re
            match = re.search(r"'([^']+)' in parents", q)
            if match:
                parent_id = match.group(1)
        name = None
        if q and "name='" in q:
            name = q.split("name='", 1)[1].split("'", 1)[0]
        contains = None
        if q and "name contains '" in q:
            contains = q.split("name contains '", 1)[1].split("'", 1)[0]
        mime_folder = "application/vnd.google-apps.folder" in (q or "")
        files = []
        for file_id, meta in self.service.entries.items():
            if parent_id is not None and parent_id not in meta.get("parents", []):
                continue
            if mime_folder and meta.get("mimeType") != "application/vnd.google-apps.folder":
                continue
            if name is not None and meta.get("name") != name:
                continue
            if contains is not None and contains not in meta.get("name", ""):
                continue
            files.append({"id": file_id, "name": meta["name"]})
        return _FakeResponse({"files": files})

    def create(self, body=None, media_body=None, **kwargs):
        file_id = self.service.next_id()
        meta = {
            "id": file_id,
            "name": body.get("name"),
            "parents": body.get("parents") or [],
            "mimeType": body.get("mimeType", "file"),
            "content": b"",
        }
        if media_body is not None:
            meta["content"] = Path(media_body._filename).read_bytes()
        self.service.entries[file_id] = meta
        return _FakeResponse({"id": file_id})

    def update(self, fileId=None, media_body=None, **kwargs):
        meta = self.service.entries[fileId]
        meta["content"] = Path(media_body._filename).read_bytes()
        return _FakeResponse({"id": fileId})

    def get_media(self, fileId=None):
        return self.service.entries[fileId]


class _FakeDriveService:
    def __init__(self):
        self.entries = {}
        self._counter = 0

    def next_id(self):
        self._counter += 1
        return f"id_{self._counter}"

    def files(self):
        return _FakeDriveFiles(self)


class _FakeDownloader:
    def __init__(self, fh, request):
        self.fh = fh
        self.request = request
        self.done = False

    def next_chunk(self):
        if not self.done:
            self.fh.write(self.request.get("content", b""))
            self.done = True
        return (None, True)


class _LegacyHarness(LocalBackupManager):
    @classmethod
    def build(cls, base_dir: Path):
        mgr = cls.__new__(cls)
        mgr.verbose = False
        mgr.remote_available = True
        mgr.drive = _FakeDriveService()
        mgr.in_share_drive = False
        mgr.date_str = "day_20990101"
        mgr.dir = base_dir / "config"
        mgr.dir.mkdir(parents=True, exist_ok=True)
        mgr.quantum_logs_path = base_dir / "quantum_logs"
        mgr.quantum_logs_path.mkdir(parents=True, exist_ok=True)
        mgr.quantum_datalake_path = base_dir / "quantum_data_lake"
        mgr.quantum_datalake_path.mkdir(parents=True, exist_ok=True)
        mgr.backup_registry_path = mgr.quantum_datalake_path / "backup_registry.json"
        mgr.backup_pickle_path = mgr.quantum_datalake_path / "backup_registry.pkl"
        mgr.framework_state_path = mgr.quantum_datalake_path / "framework_state"
        mgr.model_state_path = mgr.quantum_datalake_path / "model_state"
        mgr.framework_state_path.mkdir(parents=True, exist_ok=True)
        mgr.model_state_path.mkdir(parents=True, exist_ok=True)
        mgr.backup_registry = {}
        mgr.new_entries = {}
        return mgr

    def _retry_drive(self, func, max_retries=5):
        return func()

    def _ensure_drive_folder(self, folder_name, parent_id):
        for file_id, meta in self.drive.entries.items():
            if meta.get("name") == folder_name and parent_id in meta.get("parents", []):
                return file_id
        file_id = self.drive.next_id()
        self.drive.entries[file_id] = {
            "id": file_id,
            "name": folder_name,
            "parents": [parent_id],
            "mimeType": "application/vnd.google-apps.folder",
            "content": b"",
        }
        return file_id

    def save_registry(self, registry=None):
        return True


class TestLegacyDriveFlow(unittest.TestCase):
    def test_save_file_uploads_immediately_to_drive(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _LegacyHarness.build(base)

            saved = mgr.save_file("framework_state", "Runner.pkl", {"ok": 1})

            self.assertTrue(Path(saved).exists())
            with patch.object(gd_module, "MediaIoBaseDownload", _FakeDownloader):
                restored = mgr._download_file_from_drive(
                    "day_20990101",
                    "framework_state",
                    "Runner.pkl",
                )
            self.assertIsNotNone(restored)
            self.assertTrue(Path(restored).exists())

    def test_upload_download_delete_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _LegacyHarness.build(base)

            local_file = base / "local.pkl"
            local_file.write_bytes(b"legacy-drive-test")

            uploaded = mgr._upload_file_to_drive(
                component="framework_state",
                date_str="day_20990101",
                local_path=str(local_file),
                filename="Runner.pkl",
            )
            self.assertTrue(uploaded)

            downloaded_target = mgr.quantum_datalake_path / "framework_state" / "day_20990101" / "Runner.pkl"
            if downloaded_target.exists():
                downloaded_target.unlink()

            with patch.object(gd_module, "MediaIoBaseDownload", _FakeDownloader):
                restored = mgr._download_file_from_drive(
                    "day_20990101",
                    "framework_state",
                    "Runner.pkl",
                )

            self.assertEqual(restored, str(downloaded_target))
            self.assertTrue(downloaded_target.exists())
            self.assertEqual(downloaded_target.read_bytes(), b"legacy-drive-test")

            deleted = mgr.delete_from_drive("framework_state", "Runner.pkl")
            self.assertTrue(deleted)
            self.assertFalse(downloaded_target.exists())

    def test_local_first_save_updates_registry(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            mgr = _LegacyHarness.build(base)
            saved = mgr.save_file("framework_state", "Runner.pkl", {"ok": 1})
            self.assertTrue(Path(saved).exists())
            self.assertEqual(mgr.backup_registry["framework_state"]["Runner.pkl"], saved)
            self.assertEqual(mgr.new_entries["framework_state"]["Runner.pkl"], saved)


if __name__ == "__main__":
    unittest.main()
