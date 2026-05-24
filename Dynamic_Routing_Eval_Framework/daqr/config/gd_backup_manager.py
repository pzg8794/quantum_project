from __future__ import annotations
import os, io, json, pickle
import pathlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re
import time
import random
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

class GoogleDriveBackupManager:
    """Unified JSON registry backup to Google Drive Shared Drive."""

    DEFAULT_DRIVE_FOLDER_ID = "<drive-folder-id>"

    def __init__(self, date_str, config_dir, verbose=False):
        self.drive = None
        self.metadata = {}
        self.new_entries = {}
        self.verbose = verbose
        self.backup_registry = {}
        # Drive state index cache: per-component mapping of exact filename -> {drive_id, day}
        # Used to accelerate date-agnostic downloads without scanning every day_* folder.
        self._drive_state_index_by_component = {}
        self._drive_state_index_loaded_components = set()
        self.in_share_drive = True
        self.drive_folder_id = os.environ.get(
            "DAQR_DRIVE_FOLDER_ID",
            self.DEFAULT_DRIVE_FOLDER_ID,
        )
        
        self.obj_query = {}
        self.dir = config_dir
        self.date_str = date_str

        # self.date_str = self.normalize_day_prefix(date_str)
        self.workspace_root = self._find_workspace_root(Path(self.dir).resolve())
        self.relative_config_dir = (
            Path(self.dir).resolve().relative_to(self.workspace_root)
            if self.workspace_root is not None else None
        )
        self.drive_workspace_root = self._find_drive_workspace_root()
        self.drive_config_dir = (
            self.drive_workspace_root / self.relative_config_dir
            if self.drive_workspace_root is not None and self.relative_config_dir is not None
            else None
        )
        if self.verbose:
            print(f"\tDrive folder id: {self.drive_folder_id}")
            print(f"\tDrive workspace root: {self.drive_workspace_root}")
            print(f"\tDrive config dir: {self.drive_config_dir}")

        self.drive_datalake_base            = (
            self.drive_workspace_root
            if self.drive_workspace_root is not None
            else Path("/content/drive/Shareddrives/ai_quantum_computing")
        )
        self.quantum_logs_file_name         = f"quantum_quick-run_log_{self.date_str}.txt"

        self.quantum_data_paths             = {"drive":"", "local":"", "datalake":""}
        self.quantum_data_paths["local"]    = self.dir
        self.quantum_data_paths["drive"]    = (
            self.drive_config_dir
            if self.drive_config_dir is not None
            else self.drive_datalake_base / "quantum_data_lake"
        )
        
        self.quantum_data_paths["logs"]             = {}
        self.quantum_data_paths["logs"]["drive"]    = (
            self.drive_config_dir / "quantum_logs"
            if self.drive_config_dir is not None
            else self.drive_datalake_base / "quantum_logs"
        )
        self.quantum_data_paths["logs"]["local"]    = self.dir / "quantum_logs"

        self.quantum_data_paths["obj"]                              = {"obj":{}}
        drive_path                                                  = self.quantum_data_paths["drive"]
        self.quantum_data_paths["obj"]["model_state"]               = {}
        self.quantum_data_paths["obj"]["framework_state"]           = {}
        self.quantum_data_paths["obj"]["model_state"]["local"]      = self.dir / "model_state"
        self.quantum_data_paths["obj"]["model_state"]["drive"]      = (
            self.drive_config_dir / "model_state"
            if self.drive_config_dir is not None
            else self.dir / "model_state"
        )
        self.quantum_data_paths["obj"]["framework_state"]["local"]  = self.dir / "framework_state"
        self.quantum_data_paths["obj"]["framework_state"]["drive"]  = (
            self.drive_config_dir / "framework_state"
            if self.drive_config_dir is not None
            else self.dir / "framework_state"
        )
        

        self.registry_file_paths            = {'drive':"", "local":"", "datalake":""}
        self.registry_file_paths["drive"]   = self.dir / "drive_backup_registry.json"
        self.registry_file_paths["local"]   = self.dir / "local_backup_registry.json"
        self.registry_file_paths["datalake"]= drive_path / "backup_registry.json"

        self.in_share_drive             = self._is_running_from_drive_workspace()
        self.drive_filesystem_available = bool(self.drive_config_dir and self.drive_config_dir.exists())
        self.mode                       = "drive" if self.in_share_drive else "local"

        # ------------------------------------------------------------
        # Registry persistence policy
        # ------------------------------------------------------------
        # The registry can be large; writing it on every object save is expensive
        # and can flood logs. Default to debounced autosave, configurable by callers.
        self.registry_autosave = True
        self.registry_save_min_interval_s = 5.0
        self._last_registry_save_ts = 0.0
        self._registry_dirty = False

        # ------------------------------------------------------------
        # Credential auto-discovery
        # ------------------------------------------------------------
        creds_path = self._find_credentials()
        if creds_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            if self.verbose: print(f"\tUsing Drive credentials: {creds_path}")

        # ------------------------------------------------------------
        # Initialize Google Drive API
        # ------------------------------------------------------------
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            self.drive = build("drive", "v3", credentials=self.credentials)
            self.remote_available = True

        except Exception as e:
            self.remote_available = False
            if self.verbose: print(f"\t⚠️ Drive unavailable: {e}")

        if self.verbose: print(f"\t📁 Registry loaded: {len(self.backup_registry)} components")

    # ------------------------------------------------------------
    # Drive state-index helpers (performance)
    # ------------------------------------------------------------
    def _state_index_filename(self) -> str:
        """Filename used for per-component Drive state index."""
        return os.environ.get("DAQR_DRIVE_STATE_INDEX_FILENAME", "state_index.json")

    def _state_index_local_day(self) -> str:
        """Best-effort fallback for a day_* folder name."""
        try:
            day = str(getattr(self, "date_str", ""))
        except Exception:
            day = ""
        if isinstance(day, str) and day.startswith("day_"):
            return day
        return f"day_{datetime.now().strftime('%Y%m%d')}"

    def _normalize_state_index_payload(self, component: str, payload):
        """Normalize supported index payload shapes into {filename: {drive_id, day}}."""
        if not isinstance(payload, dict):
            return {}

        # Preferred shape: {"files": {filename: {drive_id, day} }}
        if isinstance(payload.get("files"), dict):
            payload = payload["files"]

        # Flat mapping: {filename: {drive_id, day}} or {filename: drive_id}
        normalized = {}
        for fname, entry in payload.items():
            if not isinstance(fname, str) or not fname:
                continue

            drive_id = None
            day = None
            if isinstance(entry, dict):
                drive_id = entry.get("drive_id") or entry.get("id") or entry.get("drive_file_id")
                day = entry.get("day") or entry.get("drive_date")
            elif isinstance(entry, str):
                drive_id = entry

            if not drive_id:
                continue

            if not (isinstance(day, str) and day.startswith("day_")):
                day = self._state_index_local_day()

            normalized[fname] = {"drive_id": drive_id, "day": day}

        return normalized

    def _download_state_index_from_drive(self, component: str):
        """Download per-component state_index.json from Drive, if present."""
        if not self.remote_available or not self.drive:
            return None

        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.drive_folder_id)
        if not data_lake_id:
            return None

        comp_id = self._ensure_drive_folder(component, data_lake_id)
        if not comp_id:
            return None

        filename = self._state_index_filename()
        resp = self._retry_drive(
            lambda: self.drive.files().list(
                q=(
                    f"name='{filename}' and '{comp_id}' in parents and trashed=false"
                ),
                fields="files(id,name,size)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
                pageSize=10,
            ).execute()
        )
        files = resp.get("files", []) if isinstance(resp, dict) else []
        if not files:
            return None

        file_id = files[0]["id"]
        request = self.drive.files().get_media(fileId=file_id)
        data = request.execute()
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception:
            payload = json.loads(data)
        return payload

    def _upload_state_index_to_drive(self, component: str, index: dict) -> bool:
        """Best-effort upload/update of per-component state_index.json."""
        if not self.remote_available or not self.drive:
            return False
        if self.in_share_drive:
            # We don't write Drive API files when running in the Drive-mirror workspace.
            return False

        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.drive_folder_id)
        if not data_lake_id:
            return False
        comp_id = self._ensure_drive_folder(component, data_lake_id)
        if not comp_id:
            return False

        filename = self._state_index_filename()
        payload = {
            "_schema": "daqr_state_index_v1",
            "component": component,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "files": index,
        }
        json_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        buffer = io.BytesIO(json_bytes)
        media = MediaIoBaseUpload(buffer, mimetype="application/json", resumable=False)

        # Find existing file in component folder
        resp = self._retry_drive(
            lambda: self.drive.files().list(
                q=(
                    f"name='{filename}' and '{comp_id}' in parents and trashed=false"
                ),
                fields="files(id,name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
                pageSize=10,
            ).execute()
        )
        files = resp.get("files", []) if isinstance(resp, dict) else []
        existing_id = files[0]["id"] if files else None

        if existing_id:
            self.drive.files().update(
                fileId=existing_id,
                media_body=media,
                supportsAllDrives=True,
            ).execute()
        else:
            meta = {"name": filename, "parents": [comp_id]}
            self.drive.files().create(
                body=meta,
                media_body=media,
                supportsAllDrives=True,
            ).execute()
        return True

    def _build_state_index_remote(self, component: str) -> dict:
        """Build a per-component filename→(drive_id, day) index by scanning Drive."""
        if not self.remote_available or not self.drive:
            return {}

        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.drive_folder_id)
        if not data_lake_id:
            return {}

        comp_id = self._ensure_drive_folder(component, data_lake_id)
        if not comp_id:
            return {}

        # List day folders (newest-first)
        day_folders = []
        page_token = None
        while True:
            resp = self._retry_drive(
                lambda: self.drive.files().list(
                    q=(
                        f"'{comp_id}' in parents and trashed=false and "
                        "mimeType='application/vnd.google-apps.folder'"
                    ),
                    fields="nextPageToken, files(id,name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="allDrives",
                    pageSize=1000,
                    pageToken=page_token,
                ).execute()
            )
            day_folders.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        day_folders = [f for f in day_folders if str(f.get("name", "")).startswith("day_")]
        day_folders.sort(key=lambda f: str(f.get("name", "")), reverse=True)

        index = {}
        for folder in day_folders:
            day_name = str(folder.get("name", ""))
            day_id = folder.get("id")
            if not day_id or not day_name.startswith("day_"):
                continue

            file_token = None
            while True:
                file_resp = self._retry_drive(
                    lambda: self.drive.files().list(
                        q=f"'{day_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id,name,size)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        corpora="allDrives",
                        pageSize=1000,
                        pageToken=file_token,
                    ).execute()
                )
                for f in file_resp.get("files", []):
                    fname = f.get("name")
                    fid = f.get("id")
                    if not fname or not fid:
                        continue
                    # Preserve current semantics: newest day_* wins.
                    if fname in index:
                        continue
                    index[fname] = {"drive_id": fid, "day": day_name}

                file_token = file_resp.get("nextPageToken")
                if not file_token:
                    break

        return index

    def ensure_drive_state_index(
        self,
        component: str,
        *,
        build_if_missing: bool = False,
        force_refresh: bool = False,
        save_if_built: bool = True,
    ) -> dict | None:
        """Ensure the per-component Drive state index is loaded (or built).

        Returns the cached mapping {filename: {drive_id, day}} when available.
        """
        if not component:
            return None

        loaded = component in getattr(self, "_drive_state_index_loaded_components", set())
        if loaded and not force_refresh:
            return getattr(self, "_drive_state_index_by_component", {}).get(component, {})

        # 1) Try loading from Drive
        try:
            payload = self._download_state_index_from_drive(component)
        except Exception:
            payload = None
        if payload is not None:
            index = self._normalize_state_index_payload(component, payload)
            self._drive_state_index_by_component[component] = index
            self._drive_state_index_loaded_components.add(component)
            return index

        # 2) Optionally build by scanning Drive
        if build_if_missing and (not self.in_share_drive) and self.remote_available and self.drive:
            index = self._build_state_index_remote(component)
            self._drive_state_index_by_component[component] = index
            self._drive_state_index_loaded_components.add(component)
            if save_if_built:
                try:
                    self._upload_state_index_to_drive(component, index)
                except Exception:
                    pass
            return index

        return None

    def _find_workspace_root(self, start_path: Path):
        start_path = Path(start_path).resolve()
        for parent in [start_path, *start_path.parents]:
            if parent.name == "anonymous-workspace":
                return parent
        return None

    def _find_drive_workspace_root(self):
        override = os.environ.get("DAQR_DRIVE_WORKSPACE_ROOT")
        if override:
            override_path = Path(override).expanduser()
            if override_path.exists():
                return override_path.resolve()

        if self.workspace_root is None or self.relative_config_dir is None:
            return None

        cloud_root = Path.home() / "Library" / "CloudStorage"
        if not cloud_root.exists():
            return None

        workspace_name = self.workspace_root.name
        local_root = self.workspace_root.resolve()
        local_parts = local_root.parts
        suffix_lengths = range(2, min(len(local_parts), 7) + 1)

        for drive_root in sorted(cloud_root.glob("GoogleDrive*")):
            shortcut_base = drive_root / ".shortcut-targets-by-id"
            if shortcut_base.exists():
                for shortcut_root in sorted(shortcut_base.iterdir()):
                    for suffix_len in suffix_lengths:
                        candidate = shortcut_root / Path(*local_parts[-suffix_len:])
                        try:
                            candidate = candidate.resolve()
                        except Exception:
                            continue
                        if candidate == local_root:
                            continue
                        if not (candidate / self.relative_config_dir).exists():
                            continue
                        return candidate

            direct_candidate = drive_root / workspace_name
            if direct_candidate.exists():
                try:
                    direct_candidate = direct_candidate.resolve()
                except Exception:
                    direct_candidate = direct_candidate
                if direct_candidate != local_root and (direct_candidate / self.relative_config_dir).exists():
                    return direct_candidate

        return None

    def _is_running_from_drive_workspace(self):
        if self.drive_config_dir is None:
            return False
        try:
            return Path(self.dir).resolve() == self.drive_config_dir.resolve()
        except Exception:
            return False


    # ------------------------------------------------------------
    # Find credentials (same behavior as your GCP code)
    # ------------------------------------------------------------
    def _find_credentials(self):
        current_dir = Path(__file__).parent.resolve()
        locations = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            current_dir.parent.parent.parent.parent / "quantum-gd-credentials.json",
            current_dir.parent.parent.parent / "quantum-gd-credentials.json",
            current_dir.parent.parent / "quantum-gd-credentials.json",
            current_dir.parent / "quantum-gd-credentials.json",
            Path.home() / "quantum-gd-credentials.json",
            Path("/app/credentials/quantum-gd-credentials.json"),
        ]
        for loc in locations:
            if loc and Path(loc).exists():
                return str(loc)
        return None


    # ------------------------------------------------------------
    # Find Drive file
    # ------------------------------------------------------------
    def _find_drive_file(self, name):
        if not self.drive or not self.remote_available: 
            print("Drive is not available!")
            return None
        
        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.drive_folder_id)
        if not data_lake_id: return None

        query = f"name='{name}' and '{data_lake_id}' in parents"

        response = self.drive.files().list(
            q=query,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = response.get("files", [])
        return files[0]["id"] if files else None


    def _filter_registry(self, registry, expected_keys):
        """
        Filter loaded registry to only include expected keys.
        Does NOT modify structure. Just prunes missing keys.

        This version prints exactly what is kept, what is missing,
        and how many keys survive filtering.
        """

        filtered = {
            "framework_state": {},
            "model_state": {}
        }

        for comp in ["framework_state", "model_state"]:
            if comp not in registry:
                print(f"⚠️  Registry missing component: {comp}")
                continue

            print(f"\nComponent: {comp}")
            expected_list = expected_keys.get(comp, [])
            found = 0
            missing = []

            for key in expected_list:

                if comp not in self.new_entries.keys():  # temp patch, keep your logic untouched
                    self.new_entries[comp] = {}

                if key in registry[comp]:
                    # Convert registry entry from raw filename → full local path
                    entry_path = registry[comp][key]
                    if not Path(entry_path).is_absolute():
                        print(f"⚠️ Missing locally → downloading {key} from Drive...")
                        entry_path = str(self.dir / comp / self.date_str / entry_path)

                    # If file missing → download
                    if not Path(entry_path).exists():
                        # Default Drive recovery is date-agnostic: (component, exact filename)
                        # across any `day_*` folder.
                        recovered = self._download_file_from_drive(component=comp, filename=key)
                        if recovered:
                            print(f"   ☁️ Recovered from Drive {' Remotely' if not self.in_share_drive else ' Locally'} → {recovered}")
                            entry_path = recovered
                        else: print(f"   ⚠️ Drive had no copy → falling back to local expected path")

                    # Store final resolved path
                    registry[comp][key] = entry_path
                    self.new_entries[comp][key] = entry_path
                    filtered[comp][key] = entry_path
                    found += 1

                else:
                    # Your original fallback path creation
                    missing.append(key)
                    self.new_entries[comp][key] = self.dir/comp/self.date_str/key

            print(f"  ✓ Found {found} / {len(expected_list)} expected keys")

        total_final = (
            len(filtered["framework_state"]) +
            len(filtered["model_state"])
        )
        print(f"\n--> Filtered registry contains {total_final} total keys")
        print("--------------------------------------------------------------\n")

        return filtered



    def _fetch_registry_from_drive(self, expected_keys=None, force=False):
        """
        Fetch registry.json from Google Drive.
        If expected_keys is provided, filter down the registry to only those keys.
        """
        if len(self.metadata) != 0 and not force: return self.metadata
        print("\n==================== FETCH FROM DRIVE START ====================")

        if not self.remote_available or not self.drive:
            print("⚠️ Drive NOT available -> cannot fetch registry")
            return self.metadata

        print(f"→ Looking for 'backup_registry.json' in Drive folder: {self.drive_folder_id}")
        file_id = self._find_drive_file("backup_registry.json")

        if not file_id:
            print("→ No registry file found in Drive")
            print("==================== FETCH FROM DRIVE END =====================\n")
            return self.metadata

        print(f"→ Registry FOUND in Drive with file_id={file_id}")
        print("→ Downloading...")

        # ------------------------------------------------------------
        # Download JSON Metadata
        # ------------------------------------------------------------
        self.metadata = {}
        try:
            request = self.drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status: print(f"   Download progress: {int(status.progress() * 100)}%")

            fh.seek(0)
            self.metadata = json.loads(fh.read().decode("utf-8"))
        except Exception as e:
            print(f"❌ ERROR decoding registry JSON: {e}")
            print("==================== FETCH FROM DRIVE END =====================\n")
            return self.backup_registry

        num_components = len(self.metadata)
        if num_components > 0 and expected_keys:
            # ------------------------------------------------------------
            # Optional filtering
            # ------------------------------------------------------------
            # if expected_keys:
            print("→ Filtering registry based on expected keys...")
            self.backup_registry = self._filter_registry(self.metadata, expected_keys)
            print("→ Filtering completed.")
            print("==================== FETCH FROM DRIVE END =====================\n")

            print(f"→ Successfully loaded registry JSON from Drive: {num_components} components")
            # ------------------------------------------------------------
            # Cache local
            # ------------------------------------------------------------
            file = str(self.registry_file_paths[self.mode].replace(".pkl", ".json"))
            print(f"→ Caching registry locally: {file}")
            try:
                with open(file, "w") as f: json.dump(self.backup_registry, f)
            except Exception as e:  print(f"❌ ERROR writing local cache: {e}")
        return self.backup_registry or self.metadata


    # # ------------------------------------------------------------
    # # Remote SAVE (exact GCP naming: _save_registry_to_gcs)
    # # ------------------------------------------------------------
    # def _save_registry_to_gcs(self):
    #     registry_path = self.registry_file_paths[self.mode]
    #     registry_path.replace(".pkl", ".json")
        
    #     # # Direct filesystem write in shared drive
    #     # with open(registry_path, "w") as f:
    #     #     json.dump(self.backup_registry, f, indent=2)
    #     if self.verbose: print(f"💾 Registry Saved in {self.mode.title()} Directory: {registry_path}")

    #     if not self.remote_available or not self.drive: return False
        
    #     # # Drive API for non-shared-drive environments
    #     # json_bytes = json.dumps(self.backup_registry).encode("utf-8")
    #     # buffer = io.BytesIO(json_bytes)
    #     # media = MediaIoBaseUpload(buffer, mimetype="application/json", resumable=False)
        
    #     # data_lake_id = self._ensure_drive_folder("quantum_logs", self.DRIVE_FOLDER_ID)
    #     # metadata = {
    #     #     "name": "backup_registry.json",
    #     #     "parents": [data_lake_id]
    #     # }
    #     # file_id = self._find_drive_file("backup_registry.json")
        
    #     # if file_id:
    #     #     self.drive.files().update(
    #     #         fileId=file_id,
    #     #         media_body=media,
    #     #         supportsAllDrives=True
    #     #     ).execute()
    #     # else:
    #     #     self.drive.files().create(
    #     #         body=metadata,
    #     #         media_body=media,
    #     #         supportsAllDrives=True
    #     #     ).execute()
        
    #     # if self.verbose: print("☁️ Registry (in-memory) synced to Drive")
    #     return True


    def build_registry(self, force=False, expected_keys=None):
        """
        EXACT public interface you used before.
        Now includes diagnostic output showing:
        - whether local cache is used
        - whether Drive fetch is attempted
        - whether Drive returned something
        - whether fallback happened
        """
        # ------------------------------------------------------------
        # 2. Try Drive
        # ------------------------------------------------------------
        print("→ Attempting to fetch registry from Google Drive...")
        reg = self._fetch_registry_from_drive(expected_keys=expected_keys)
        if reg is None: print("⚠️  Drive returned NO registry (None)")
            # self.backup_registry = {}
        else:
            total_remote = sum(len(v) for v in reg.values())
            print(f"✓ Drive registry loaded ({total_remote} keys)")
            # self.backup_registry = reg
        print("====================== BUILD REGISTRY END ======================\n")
        return self.backup_registry


    def save_registry(self, registry=None, *, force: bool = False):
        reg = registry or self.backup_registry

        # Debounce registry writes (common hot path during model/runner saves).
        try:
            min_interval_s = float(getattr(self, "registry_save_min_interval_s", 0.0) or 0.0)
        except Exception:
            min_interval_s = 0.0
        now = time.time()
        last = float(getattr(self, "_last_registry_save_ts", 0.0) or 0.0)
        if (not force) and min_interval_s > 0 and (now - last) < min_interval_s:
            self._registry_dirty = True
            return False

        file = str(self.registry_file_paths[self.mode])
        with open(file, "wb") as f:
            pickle.dump(reg, f)
        with open(file.replace(".pkl", ".json"), "w") as f:
            json.dump(reg, f)

        self._last_registry_save_ts = now
        self._registry_dirty = False
        if self.verbose:
            print(f"\t📦 {self} Registry Saved Locally in {self.mode.upper()}")
        # Remote save
        # remote_status = self._save_registry_to_gcs()
        # if remote_status: print(f"\t☁️ {self} Registry synced to Google Drive")
        return True


    def get_latest_state(self, component, filename):
        entry = self.backup_registry.get(component, {}).get(filename)
        if not entry: return None

        path                     = None
        try:                path = entry.get("local_path") if isinstance(entry, dict) else entry
        except Exception:   path = self.normalize_path(path, project_root=self.dir)
        if not path or not os.path.exists(path): return None

        ext = Path(path).suffix.lower()
        if ext == ".pkl":
            with open(path, "rb") as f:
                return pickle.load(f)
            
        elif ext in [".json", ".jsn"]:
            with open(path, "r") as f:
                return json.load(f)
        else:
            with open(path, "rb") as f:
                return f.read()


    def is_empty(self):
        return not bool(self.backup_registry)


    def list_all_files(self, component=None):
        if component:
            return list(self.backup_registry.get(component, {}).keys())
        return {c: list(files.keys()) for c, files in self.backup_registry.items()}

    def _ensure_drive_folder(self, folder_name, parent_id):
        """Find or create a folder under a given parent (or Drive root)."""
        if not self.remote_available or not self.drive or not parent_id: return None

        try:
            is_drive_root = (parent_id == self.drive_folder_id)

            if is_drive_root:
                parent_clause = f"'{self.drive_folder_id}' in parents"
            elif parent_id == "root":
                parent_clause = "'root' in parents"
            else:
                parent_clause = f"'{parent_id}' in parents"

            query = (
                f"name='{folder_name}' and {parent_clause} "
                f"and mimeType='application/vnd.google-apps.folder'"
            )

            list_kwargs = dict(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            if is_drive_root:
                list_kwargs["corpora"] = "drive"
                list_kwargs["driveId"] = self.drive_folder_id

            response = self.drive.files().list(**list_kwargs).execute()

            files = response.get("files", [])
            if files:
                return files[0]["id"]

            metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.drive_folder_id] if is_drive_root else [parent_id]
            }

            folder = self.drive.files().create(
                body=metadata,
                supportsAllDrives=True
            ).execute()

            return folder["id"]
        except Exception as e:  print(f"            {e}")

        return None


    def _retry_drive(self, func, max_retries=5):
        """Retry wrapper for Drive API calls using exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func()
            except HttpError as e:
                # Retry only on transient errors
                status = e.resp.status
                if status in (429, 500, 502, 503):
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"\t⚠️ Drive transient error {status}, retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    continue
                raise  # Non-retryable error
        raise Exception("🚨 Drive API failed after maximum retries")


    def _upload_file_to_drive(self, component, date_str, local_path, filename, parent_dir="quantum_data_lake"):
        """Upload a file into Google Drive, supporting both quantum_data_lake and quantum_logs."""
        if not self.remote_available or not self.drive: return False
        if self.in_share_drive: return False
        
        # ---------------------------------------------------------------
        # 1. Root folder (quantum_data_lake or quantum_logs)
        # ---------------------------------------------------------------
        date_str                =   re.sub(r'.*?(day_\d{8})$', r'\1', str(date_str))
        root_id                 =   self._ensure_drive_folder(parent_dir, self.drive_folder_id)

        # ---------------------------------------------------------------
        # 2. Component folder — ONLY IF USING quantum_data_lake
        # ---------------------------------------------------------------
        if component is not None:   
            comp_folder_id      =   self._ensure_drive_folder(component, root_id)
            # day_folder_name     =   self.normalize_day_prefix(date_str)
            parent_folder_id    =   self._ensure_drive_folder(str(date_str), comp_folder_id)
        else: parent_folder_id  =   root_id
        if not parent_folder_id: return False

        # ---------------------------------------------------------------
        # 4. Check if file already exists
        # ---------------------------------------------------------------
        query                   =   (f"name='{filename}' and '{parent_folder_id}' in parents")

        response                =   self._retry_drive(
                                        lambda: self.drive.files().list(
                                            q=query,
                                            fields="files(id,name,size)",
                                            supportsAllDrives=True,
                                            includeItemsFromAllDrives=True
                                        ).execute()
                                    )

        files                   =   response.get("files", [])
        existing_file           =   None
        if files:
            existing_file       =   next((f for f in files if f.get("name") == filename), files[0])
        file_id                 =   existing_file["id"] if existing_file else None
        remote_size             =   int(existing_file.get("size", 0) or 0) if existing_file else 0
        local_size              =   Path(local_path).stat().st_size

        # ---------------------------------------------------------------
        # 5. Skip upload when Drive already has the same or a larger file
        # ---------------------------------------------------------------
        if existing_file and remote_size >= local_size:
            if self.verbose:
                print(
                    f"☁️ Skipping upload for {parent_dir}/{component}/{filename}: "
                    f"remote size {remote_size} >= local size {local_size}"
                )
            return True

        # ---------------------------------------------------------------
        # 6. Upload or update
        # ---------------------------------------------------------------
        media           =   MediaFileUpload(local_path, resumable=True)
        if file_id:         self.drive.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
        else:
            metadata    =   {"name": filename, "parents": [parent_folder_id]}
            self.drive.files().create(body=metadata, media_body=media, supportsAllDrives=True).execute()
        if self.verbose:    print(f"☁️ Uploaded {parent_dir}/{component}/{filename}")

        return True

    def set_regestry_qry(self, filename, day_folder_id):
        self.obj_query["model_state"] = f"name='{filename}' and '{day_folder_id}' in parents"
        self.obj_query["framework_state"] = f"name='{filename}' and '{day_folder_id}' in parents"
        return True
    
    def _download_file_from_drive(
        self,
        date_str=None,
        component=None,
        filename=None,
        storage_dir="quantum_data_lake",
    ):
        """Download a single file from Drive.

        Default behavior is date-agnostic: when `date_str` is None, search for
        an EXACT `(component, filename)` match across any `day_*` folder.

        If `date_str` is provided, restrict the lookup to that specific day
        folder.
        """

        if not component or not filename:
            return None

        # Default: no date constraint.
        if not date_str:
            return self.download_any_date(component=component, filename=filename)

        date_str = str(date_str)
        if re.fullmatch(r"\d{8}", date_str):
            date_str = f"day_{date_str}"
        else:
            m = re.search(r"(day_\d{8})$", date_str)
            if m:
                date_str = m.group(1)

        if self.in_share_drive:
            # Direct filesystem path in shared drive - no download needed
            local_path = self.quantum_data_paths["obj"][component]["drive"] / date_str / filename
            if local_path.exists():
                return str(local_path)

        if not self.remote_available or not self.drive:
            return None
        
        # ---------------------------------------------------------------
        # 1. Resolve quantum_data_lake root
        # ---------------------------------------------------------------
        data_lake_id = self._ensure_drive_folder(storage_dir, self.drive_folder_id)
        
        # ---------------------------------------------------------------
        # 2. Resolve component folder
        # ---------------------------------------------------------------
        comp_folder_id = self._ensure_drive_folder(component, data_lake_id)
        
        # ---------------------------------------------------------------
        # 3. Resolve date folder
        # ---------------------------------------------------------------
        day_folder_id = self._ensure_drive_folder(date_str, comp_folder_id)
        if not day_folder_id: return None
        
        # ---------------------------------------------------------------
        # 4. Drive search query
        # ---------------------------------------------------------------
        self.set_regestry_qry(filename, day_folder_id)

        response = self._retry_drive(
            lambda: self.drive.files().list(
                q=self.obj_query[component],
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
        )
        
        files = response.get("files", [])
        if not files: return None    
        file_id = files[0]["id"]
    
        # ---------------------------------------------------------------
        # 5. Local path
        # ---------------------------------------------------------------
        local_path = self.quantum_data_paths["obj"][component]["local"] / date_str / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ---------------------------------------------------------------
        # 6. Download the file
        # ---------------------------------------------------------------
        request = self.drive.files().get_media(fileId=file_id)
        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        return str(local_path)


    def restore_from_drive(self, date_str, expected_keys):
        """Restore local state files for the expected experiment keys.

        IMPORTANT: the day folder is NOT part of the lookup key.
        Restore is by exact (component, filename) across ANY `day_*` folder.

        This method prefers staging via Drive API downloads (when available)
        instead of returning Google Drive filesystem-mirror paths.
        """
        print("RESTORING FROM DRIVE")

        if not expected_keys:
            return True

        # If we expect many restores in a remote environment, pre-load or build
        # the Drive state index once per component to avoid scanning every day_* folder.
        if (not self.in_share_drive) and self.remote_available and self.drive:
            for component in expected_keys.keys():
                try:
                    self.ensure_drive_state_index(component, build_if_missing=True)
                except Exception:
                    # Never fail restore over index preloading.
                    pass

        # Accept either {component: {filename: ...}} or {component: [filename, ...]}.
        restored = defaultdict(dict)

        # Precompute local availability for faster membership checks.
        local_cache = {}
        for component in expected_keys.keys():
            try:
                local_root = Path(self.quantum_data_paths["obj"][component]["local"])
            except Exception:
                continue
            if not local_root.exists():
                continue
            # Index filenames across all local day_* folders.
            candidates = {}
            for day_dir in sorted(local_root.glob("day_*"), reverse=True):
                if not day_dir.is_dir():
                    continue
                for fp in day_dir.iterdir():
                    if fp.is_file():
                        candidates.setdefault(fp.name, fp)
            local_cache[component] = candidates

        for component, filenames in expected_keys.items():
            if isinstance(filenames, dict):
                filename_list = list(filenames.keys())
            else:
                try:
                    filename_list = list(filenames)
                except Exception:
                    filename_list = []

            found_local = 0
            downloaded = 0
            missing = 0

            for filename in filename_list:
                # 1) Registry path if valid
                entry = None
                try:
                    entry = self.backup_registry.get(component, {}).get(filename)
                except Exception:
                    entry = None

                if isinstance(entry, str) and entry:
                    try:
                        entry_path = Path(entry)
                    except Exception:
                        entry_path = None
                    if entry_path is not None and entry_path.exists():
                        restored[component][filename] = str(entry_path.resolve())
                        found_local += 1
                        continue

                # 2) Any-date local filesystem hit
                local_hit = local_cache.get(component, {}).get(filename)
                if local_hit is not None and local_hit.exists():
                    restored[component][filename] = str(local_hit.resolve())
                    found_local += 1
                    continue

                # 3) Any-date Drive recovery (staged via API when available)
                drive_path = self.download_any_date(component=component, filename=filename)
                if drive_path and Path(drive_path).exists():
                    restored[component][filename] = str(Path(drive_path).resolve())
                    downloaded += 1
                    continue

                # 4) Placeholder expected local path (current day folder)
                missing += 1
                try:
                    local_root = Path(self.quantum_data_paths["obj"][component]["local"])
                    restored[component][filename] = str((local_root / (date_str or self.date_str) / filename).resolve())
                except Exception:
                    restored[component][filename] = filename

            print(
                f"\t{component}: expected={len(filename_list)} local={found_local} downloaded={downloaded} missing={missing}"
            )

        # Cache registry locally (JSON), best-effort.
        try:
            registry_path = Path(self.registry_file_paths[self.mode])
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(registry_path, "w") as f:
                json.dump(restored, f)
        except Exception as e:
            if self.verbose:
                print(f"\t⚠️ Could not write local restore registry cache: {e}")

        self.backup_registry = restored
        return True
    
    def load_new_entries(self, entries=None, force=False):
        """
        Upload a batch of new entries to Drive.
        entries = {
            component: {
                filename: local_path
            }
        }
        """
        if not self.remote_available or not self.drive: return False
        if not entries: entries = self.new_entries
        if self.in_share_drive: return False

        files_skipped = 0
        files_uploaded = 0
        files_overwritten = 0

        self._fetch_registry_from_drive()

        for component, files in entries.items():
            if not files:
                print(f"         ⚠️ No files under component '{component}'. Skipping.")
                continue
            if component not in self.metadata:
                print(f"         ⚠️ Unknown component '{component}', creating entry.")
                self.metadata[component] = {}

            for filename, local_path in files.items():
                path_obj = Path(local_path)
                if not path_obj.exists():
                    print(f"         ❌ Local path not found: {local_path}")
                    files_skipped += 1
                    continue

                # Detect zero-byte files
                if path_obj.stat().st_size == 0:
                    print(f"         ❌ File '{filename}' is empty. Skipping upload.")
                    files_skipped += 1
                    continue

                print(f"         🔄 Checking Drive status for {filename}...")
                # Already in Drive?
                try:
                    self.metadata[component][filename]
                    print(f"            ✓ Already in Drive")
                    if not force:
                        print(f"            ⊘ Skipping (force=False)")
                        files_skipped += 1
                        continue
                    print(f"            → Overwriting (force=True)")
                    files_overwritten += 1
                except Exception as e:  print(f"            ℹ️ New file, will upload.")

                try:
                    print(f"            📤 Uploading...")
                    self._upload_file_to_drive(
                        component=component,
                        date_str=str(path_obj.parent.name),
                        local_path=local_path,
                        filename=filename
                    )
                    files_uploaded += 1
                    print(f"            ✓ Uploaded: {filename}")
                except Exception as e:  print(f"            Failed Uploading")

            # Component-level summary
            print(
                f"         📊 Component '{component}': "
                f"{files_uploaded} uploaded, "
                f"{files_skipped} skipped, "
                f"{files_overwritten} overwritten."
            )
        return True


    def download_any_date(self, component, filename):
        """
        Search all day_* folders under the given component
        and return the first EXACT match.
        """
        # Prefer Drive API download when available to avoid timeouts from
        # reading large pickles via the Google Drive filesystem mirror.

        if self.in_share_drive:
            # Direct filesystem search in shared drive
            for mode in ["drive", "local"]:
                comp_dir = self.quantum_data_paths.get(mode)
                if comp_dir is None:
                    continue
                comp_dir = Path(comp_dir) / component
                if not comp_dir.exists():
                    continue

                # Search all day_* folders (newest-first)
                for day_folder in sorted(comp_dir.iterdir(), reverse=True):
                    if not day_folder.is_dir() or not day_folder.name.startswith("day_"):
                        continue
                    file_path = day_folder / filename
                    if file_path.exists():
                        if self.verbose:
                            print(f"✓ Found: {file_path}")
                        return str(file_path)
            return None

        # Drive API for non-shared-drive environments
        if self.remote_available and self.drive:
            try:
                # Fast-path: use the per-component Drive state index if available.
                index = None
                try:
                    index = self.ensure_drive_state_index(component, build_if_missing=False)
                except Exception:
                    index = None

                entry = index.get(filename) if isinstance(index, dict) else None
                if isinstance(entry, dict) and entry.get("drive_id"):
                    try:
                        day_name = entry.get("day")
                        if not (isinstance(day_name, str) and day_name.startswith("day_")):
                            day_name = self._state_index_local_day()

                        local_dir = self.quantum_data_paths["local"] / component / day_name
                        local_dir.mkdir(parents=True, exist_ok=True)
                        local_path = local_dir / filename
                        if local_path.exists() and local_path.stat().st_size > 0:
                            return str(local_path)

                        request = self.drive.files().get_media(fileId=entry["drive_id"])
                        with open(local_path, "wb") as f:
                            done = False
                            downloader = MediaIoBaseDownload(f, request)
                            while not done:
                                _status, done = downloader.next_chunk()

                        return str(local_path)
                    except Exception as e:
                        # Stale index (or transient download error) → fall back to scan-based lookup.
                        if self.verbose:
                            print(f"\t⚠️ State-index fast download failed; falling back to scan: {e}")

                data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.drive_folder_id)
                comp_id = self._ensure_drive_folder(component, data_lake_id)
                if comp_id:
                    # List all day_* folders under component
                    response = self._retry_drive(
                        lambda: self.drive.files().list(
                            q=(
                                f"'{comp_id}' in parents and trashed=false and "
                                "mimeType='application/vnd.google-apps.folder'"
                            ),
                            fields="files(id,name)",
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True,
                            corpora="allDrives",
                            pageSize=1000,
                        ).execute()
                    )
                    day_folders = [
                        f for f in response.get("files", [])
                        if f.get("name", "").startswith("day_")
                    ]
                    # Newest-first by folder name (day_YYYYMMDD)
                    day_folders.sort(key=lambda f: f.get("name", ""), reverse=True)

                    for folder in day_folders:
                        fid = folder["id"]
                        q = f"name = '{filename}' and '{fid}' in parents and trashed=false"
                        file_response = self._retry_drive(
                            lambda: self.drive.files().list(
                                q=q,
                                fields="files(id,name,size)",
                                supportsAllDrives=True,
                                includeItemsFromAllDrives=True,
                                corpora="allDrives",
                                pageSize=10,
                            ).execute()
                        )
                        files = file_response.get("files", [])
                        if not files:
                            continue

                        file_meta = files[0]
                        file_id = file_meta["id"]
                        actual_name = file_meta["name"]

                        local_dir = self.quantum_data_paths["local"] / component / folder["name"]
                        local_dir.mkdir(parents=True, exist_ok=True)
                        local_path = local_dir / actual_name

                        request = self.drive.files().get_media(fileId=file_id)
                        with open(local_path, "wb") as f:
                            done = False
                            downloader = MediaIoBaseDownload(f, request)
                            while not done:
                                _status, done = downloader.next_chunk()

                        return str(local_path)
            except Exception as e:
                if self.verbose:
                    print(f"\t⚠️ Drive any-date download failed: {e}")

        # Fallback: try Drive filesystem mirror if API is unavailable/failed.
        drive_component_dir = None
        try:
            drive_component_dir = self.quantum_data_paths["obj"][component].get("drive")
        except Exception:
            drive_component_dir = None
        if drive_component_dir is not None and Path(drive_component_dir).exists():
            for day_folder in sorted(Path(drive_component_dir).iterdir(), reverse=True):
                if not day_folder.is_dir() or not day_folder.name.startswith("day_"):
                    continue
                file_path = day_folder / filename
                if file_path.exists():
                    if self.verbose:
                        print(f"✓ Found via Drive mirror: {file_path}")
                    return str(file_path)

        # Drive API for non-shared-drive environments
        return None


    def normalize_path(self, path: str, project_root: str = None) -> str:
        """
        Normalize absolute paths stored from another machine (Mac/VM/Colab).
        Rebuilds a safe, correct local path without nesting.
        """
        if not path:
            return None

        p = Path(path)

        # 1) If path already valid, return as-is
        if p.exists():
            return str(p)

        # 2) Determine project root (Dynamic_Routing_Eval_Framework)
        if project_root is None:
            # __file__ = daqr/config/backup_manager.py
            project_root = Path(__file__).resolve().parents[2]

        # 3) Extract only the semantic parts of the filename
        fname       = p.name
        date_folder = p.parent.name          # day_YYYYMMDD
        component   = p.parent.parent.name   # framework_state / model_state / logs

        # 4) Build the correct target path RELATIVE to project_root
        # BUT avoid nesting "daqr/config" if project_root already contains it
        base = Path(project_root)

        # If project_root already ends in "daqr/config" → don't append it again
        if base.name == "config" and base.parent.name == "daqr":
            base_dir = base
        else:
            base_dir = base / "daqr" / "config"

        new_path = base_dir / component / date_folder / fname
        return str(new_path)
    
    def delete_from_drive(self, component, filename):
        """
        Removes a file from Google Drive datalake (ShareDrive path).
        Safe: deletes only the file matching the exact component + filename.
        """
        try:
            file_path = self.quantum_data_paths["obj"][component]["drive"] / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False

        except Exception:
            return False


    
    def __repr__(self):
        env = self.__class__.__name__
        return env
