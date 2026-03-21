#!/usr/bin/env python3
"""
Audit Target D regression test (behavior):
Verify GoogleDriveBackupManager._upload_file_to_drive:
  - skips overwrite when remote file size is >= local file size
  - overwrites when remote file size is smaller than local file size
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import types


def _install_google_stubs() -> None:
    googleapiclient = types.ModuleType("googleapiclient")
    googleapiclient.errors = types.ModuleType("googleapiclient.errors")
    googleapiclient.discovery = types.ModuleType("googleapiclient.discovery")
    googleapiclient.http = types.ModuleType("googleapiclient.http")
    googleapiclient.errors.HttpError = Exception
    googleapiclient.discovery.build = lambda *args, **kwargs: None

    class _MediaFileUpload:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _MediaIoBaseDownload:
        def __init__(self, *args, **kwargs):
            pass

    class _MediaIoBaseUpload:
        def __init__(self, *args, **kwargs):
            pass

    googleapiclient.http.MediaFileUpload = _MediaFileUpload
    googleapiclient.http.MediaIoBaseDownload = _MediaIoBaseDownload
    googleapiclient.http.MediaIoBaseUpload = _MediaIoBaseUpload

    google = types.ModuleType("google")
    google.oauth2 = types.ModuleType("google.oauth2")
    google.oauth2.service_account = types.ModuleType("google.oauth2.service_account")
    google.oauth2.service_account.Credentials = type(
        "Credentials",
        (),
        {"from_service_account_file": staticmethod(lambda *args, **kwargs: None)},
    )

    sys.modules.setdefault("googleapiclient", googleapiclient)
    sys.modules.setdefault("googleapiclient.errors", googleapiclient.errors)
    sys.modules.setdefault("googleapiclient.discovery", googleapiclient.discovery)
    sys.modules.setdefault("googleapiclient.http", googleapiclient.http)
    sys.modules.setdefault("google", google)
    sys.modules.setdefault("google.oauth2", google.oauth2)
    sys.modules.setdefault("google.oauth2.service_account", google.oauth2.service_account)


_install_google_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from daqr.config.gd_backup_manager import GoogleDriveBackupManager


class _Request:
    def __init__(self, payload=None):
        self.payload = payload or {}

    def execute(self):
        return self.payload


class _FakeFilesAPI:
    def __init__(self, existing_files):
        self.existing_files = existing_files
        self.updated = []
        self.created = []

    def list(self, **kwargs):
        return _Request({"files": list(self.existing_files)})

    def update(self, **kwargs):
        self.updated.append(kwargs)
        return _Request({})

    def create(self, **kwargs):
        self.created.append(kwargs)
        return _Request({})


class _FakeDrive:
    def __init__(self, existing_files):
        self._files_api = _FakeFilesAPI(existing_files)

    def files(self):
        return self._files_api


def _build_manager(existing_files):
    mgr = GoogleDriveBackupManager.__new__(GoogleDriveBackupManager)
    mgr.remote_available = True
    mgr.in_share_drive = False
    mgr.drive = _FakeDrive(existing_files)
    mgr.verbose = False
    mgr.drive_folder_id = "root"
    mgr._ensure_drive_folder = lambda name, parent: f"{parent}/{name}"
    mgr._retry_drive = lambda fn: fn()
    return mgr


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / "state.pkl"
        local_path.write_bytes(b"x" * 100)

        skip_mgr = _build_manager([{"id": "f1", "name": "state.pkl", "size": "100"}])
        ok = skip_mgr._upload_file_to_drive(
            component="framework_state",
            date_str="day_20260321",
            local_path=str(local_path),
            filename="state.pkl",
        )
        assert ok is True
        assert skip_mgr.drive._files_api.updated == [], "should not overwrite equal-size remote file"
        assert skip_mgr.drive._files_api.created == [], "should not create when file already exists"

        overwrite_mgr = _build_manager([{"id": "f2", "name": "state.pkl", "size": "80"}])
        ok = overwrite_mgr._upload_file_to_drive(
            component="framework_state",
            date_str="day_20260321",
            local_path=str(local_path),
            filename="state.pkl",
        )
        assert ok is True
        assert len(overwrite_mgr.drive._files_api.updated) == 1, "should overwrite smaller remote file"

        create_mgr = _build_manager([])
        ok = create_mgr._upload_file_to_drive(
            component="framework_state",
            date_str="day_20260321",
            local_path=str(local_path),
            filename="state.pkl",
        )
        assert ok is True
        assert len(create_mgr.drive._files_api.created) == 1, "should create missing remote file"

    print("PASS: Task 2D behavior (Drive upload size guard)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
