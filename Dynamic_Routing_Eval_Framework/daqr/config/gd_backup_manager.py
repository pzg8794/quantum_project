from __future__ import annotations
import os, io, json, pickle
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

DAY_REGEX = re.compile(
    r'(?:(?P<day>day_)?(?P<date>\d{8}))$'
)
class GoogleDriveBackupManager:
    """Unified JSON registry backup to Google Drive Shared Drive."""

    DRIVE_FOLDER_ID = "0APT9hcMpvuHYUk9PVA"

    def __init__(self, date_str, config_dir, verbose=False):
        self.drive = None
        self.new_entries = {}
        self.verbose = verbose
        self.backup_registry = {}
        self.in_share_drive = True
        self.date_str = date_str or f"day_{datetime.now().strftime('%Y%m%d')}"
        self.dir = Path(config_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

        self.quantum_logs_file_name = f"quantum_quick-run_log_{self.date_str}.txt"
        parent_dir                  = self.dir.parent.parent.parent.parent
        self.quantum_logs_path      = parent_dir / "quantum_logs"
        if not self.quantum_logs_path.exists(): 
            parent_dir              = self.dir
            self.in_share_drive     = False

        self.quantum_logs_path      = Path(self.normalize_path("quantum_logs", project_root=parent_dir))
        self.date_str               = self.normalize_day_prefix(self.date_str)
        self.backup_registry_path   = self.dir / "backup_registry.json"
        self.backup_pickle_path     = self.dir / "backup_registry.pkl"
        self.framework_state_path   = self.dir / "framework_state"
        self.model_state_path       = self.dir / "model_state"

        # ------------------------------------------------------------
        # Credential auto-discovery
        # ------------------------------------------------------------
        creds_path = self._find_credentials()
        if creds_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            if self.verbose:
                print(f"\tUsing Drive credentials: {creds_path}")

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
            if self.verbose:
                print(f"\t⚠️ Drive unavailable: {e}")

        # ------------------------------------------------------------
        # Load registry from Drive if available
        # ------------------------------------------------------------
        self.backup_registry = self._fetch_registry_from_drive()
        if self.verbose:
            print(f"\t📁 Registry loaded: {len(self.backup_registry)} components")


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
        
        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.DRIVE_FOLDER_ID)
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
                        recovered = self._download_file_from_drive(self.date_str, comp, key)
                        if recovered:
                            print(f"   ☁️ Recovered from Drive → {recovered}")
                            entry_path = recovered
                        else:
                            print(f"   ⚠️ Drive had no copy → falling back to local expected path")

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



    def _fetch_registry_from_drive(self, expected_keys=None):
        """
        Fetch registry.json from Google Drive.
        If expected_keys is provided, filter down the registry to only those keys.
        """
        if not expected_keys: return self.backup_registry

        print("\n==================== FETCH FROM DRIVE START ====================")

        if not self.remote_available:
            print("⚠️ Drive NOT available -> cannot fetch registry")
            return self.backup_registry

        print(f"→ Looking for 'backup_registry.json' in Drive folder: {self.DRIVE_FOLDER_ID}")
        file_id = self._find_drive_file("backup_registry.json")

        if not file_id:
            print("→ No registry file found in Drive")
            print("==================== FETCH FROM DRIVE END =====================\n")
            return self.backup_registry

        print(f"→ Registry FOUND in Drive with file_id={file_id}")
        print("→ Downloading...")

        # ------------------------------------------------------------
        # Download JSON
        # ------------------------------------------------------------
        registry = {}
        try:
            request = self.drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"   Download progress: {int(status.progress() * 100)}%")

            fh.seek(0)
            registry = json.loads(fh.read().decode("utf-8"))
        except Exception as e:
            print(f"❌ ERROR decoding registry JSON: {e}")
            print("==================== FETCH FROM DRIVE END =====================\n")
            return self.backup_registry

        num_components = len(registry)
        if num_components > 0:
            print(f"→ Successfully loaded registry JSON from Drive: {num_components} components")
            # ------------------------------------------------------------
            # Cache local
            # ------------------------------------------------------------
            print(f"→ Caching registry locally: {self.backup_registry_path}")
            try:
                with open(self.backup_registry_path, "w") as f:
                    json.dump(registry, f)
            except Exception as e:
                print(f"❌ ERROR writing local cache: {e}")

            # ------------------------------------------------------------
            # Optional filtering
            # ------------------------------------------------------------
            if expected_keys:
                print("→ Filtering registry based on expected keys...")
                registry = self._filter_registry(registry, expected_keys)
                print("→ Filtering completed.")

            print("==================== FETCH FROM DRIVE END =====================\n")

        return registry




    # ------------------------------------------------------------
    # Remote SAVE (exact GCP naming: _save_registry_to_gcs)
    # ------------------------------------------------------------
    def _save_registry_to_gcs(self, registry=None):
        if not self.remote_available or not self.drive:
            return False

        registry = registry or self.backup_registry
        json_bytes = json.dumps(registry).encode("utf-8")

        # Memory buffer (NO file writing)
        buffer = io.BytesIO(json_bytes)
        
        media = MediaIoBaseUpload(buffer, mimetype="application/json", resumable=False)

        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.DRIVE_FOLDER_ID)
        metadata = {
            "name": "backup_registry.json",
            "parents": [data_lake_id]
        }
        file_id = self._find_drive_file("backup_registry.json")

        if file_id:
            # Update existing file
            self.drive.files().update(
                fileId=file_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
        else:
            # Create new file
            self.drive.files().create(
                body=metadata,
                media_body=media,
                supportsAllDrives=True
            ).execute()

        if self.verbose:
            print("☁️ Registry (in-memory) synced to Drive")

        return True



    def build_registry(self, force=False, expected_keys=None):
        """
        EXACT public interface you used before.
        Now includes diagnostic output showing:
        - whether local cache is used
        - whether Drive fetch is attempted
        - whether Drive returned something
        - whether fallback happened
        """

        print("\n===================== BUILD REGISTRY START =====================")

        # ------------------------------------------------------------
        # 1. Try local cached registry
        # ------------------------------------------------------------
        if not force and self.backup_registry_path.exists():
            try:
                print("→ Attempting to load local registry cache...")
                with open(self.backup_registry_path, "r") as f:
                    self.backup_registry = json.load(f)

                total_local = sum(len(v) for v in self.backup_registry.values())
                print(f"✓ Local registry loaded ({total_local} keys)")

                print("====================== BUILD REGISTRY END ======================\n")
                return self._fetch_registry_from_drive(expected_keys=expected_keys)

            except Exception as e:
                print(f"⚠️  Local registry exists but could not be read: {e}")
                print("→ Falling back to Drive...")

        else:
            print("→ Skipping local cache (force=True or file missing)")

        # ------------------------------------------------------------
        # 2. Try Drive
        # ------------------------------------------------------------
        print("→ Attempting to fetch registry from Google Drive...")
        reg = self._fetch_registry_from_drive(expected_keys=expected_keys)

        if reg is None:
            print("⚠️  Drive returned NO registry (None)")
            self.backup_registry = {}

        else:
            total_remote = sum(len(v) for v in reg.values())
            print(f"✓ Drive registry loaded ({total_remote} keys)")
            self.backup_registry = reg

        print("====================== BUILD REGISTRY END ======================\n")
        return self.backup_registry


    def save_registry(self, registry=None):
        reg = registry or self.backup_registry

        # Local JSON save
        with open(self.backup_registry_path, "w") as f:
            json.dump(reg, f)

        # Local pickle save
        with open(self.backup_pickle_path, "wb") as f:
            pickle.dump(reg, f)

        print(f"\t📦 {self} Registry saved locally")

        # Remote save
        remote_status = self._save_registry_to_gcs(reg)
        if remote_status:
            print(f"\t☁️ {self} Registry synced to Google Drive")

        return remote_status


    def get_latest_state(self, component, filename):
        entry = self.backup_registry.get(component, {}).get(filename)
        if not entry:
            return None

        path = entry.get("local_path") if isinstance(entry, dict) else entry
        path = self.normalize_path(path, project_root=self.dir)
        if not os.path.exists(path):
            return None

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

        is_drive_root = (parent_id == self.DRIVE_FOLDER_ID)

        if is_drive_root:
            parent_clause = "trashed = false"
        elif parent_id == "root":
            parent_clause = "'root' in parents"
        else:
            parent_clause = f"'{parent_id}' in parents"

        query = (
            f"name='{folder_name}' and {parent_clause} "
            f"and mimeType='application/vnd.google-apps.folder'"
        )

        response = self.drive.files().list(
            q=query,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = response.get("files", [])
        if files:
            return files[0]["id"]

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": None if is_drive_root else [parent_id]
        }

        folder = self.drive.files().create(
            body=metadata,
            supportsAllDrives=True
        ).execute()

        return folder["id"]


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

        # ---------------------------------------------------------------
        # 1. Root folder (quantum_data_lake or quantum_logs)
        # ---------------------------------------------------------------
        root_id                 =   self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)

        # ---------------------------------------------------------------
        # 2. Component folder — ONLY IF USING quantum_data_lake
        # ---------------------------------------------------------------
        if component is not None:   
            comp_folder_id      =   self._ensure_drive_folder(component, root_id)
            day_folder_name     =   self.normalize_day_prefix(date_str)
            parent_folder_id    =   self._ensure_drive_folder(day_folder_name, comp_folder_id)
        else: parent_folder_id  =   root_id

        # ---------------------------------------------------------------
        # 4. Check if file already exists
        # ---------------------------------------------------------------
        query                   =   (f"name='{filename}' and '{parent_folder_id}' in parents")
        if component            ==  "model_state":
            safe_prefix         =   filename.split("(")[0]
            query               =   f"name contains '{safe_prefix}' and '{parent_folder_id}' in parents"

        response                =   self._retry_drive(
                                        lambda: self.drive.files().list(
                                            q=query, supportsAllDrives=True,
                                            includeItemsFromAllDrives=True
                                        ).execute()
                                    )

        files           =   response.get("files", [])
        file_id         =   files[0]["id"] if files else None

        # ---------------------------------------------------------------
        # 5. Upload or update
        # ---------------------------------------------------------------
        media           =   MediaFileUpload(local_path, resumable=True)
        if file_id:         self.drive.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
        else:
            metadata    =   {"name": filename, "parents": [parent_folder_id]}
            self.drive.files().create(body=metadata, media_body=media, supportsAllDrives=True).execute()
        if self.verbose:    print(f"☁️ Uploaded {parent_dir}/{component}/{filename}")

        return True

    
    def _download_file_from_drive(self, date_str, component, filename):
        """
        Download a single file from Drive into:
            {config_dir}/{component}/day_{date_str}/{filename}

        This mirrors the same structure created by _upload_file_to_drive.
        """
        if not self.remote_available or not self.drive: return None

        # ---------------------------------------------------------------
        # 1. Resolve quantum_data_lake root
        # ---------------------------------------------------------------
        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.DRIVE_FOLDER_ID)

        # ---------------------------------------------------------------
        # 2. Resolve component folder
        # ---------------------------------------------------------------
        comp_folder_id = self._ensure_drive_folder(component, data_lake_id)

        # ---------------------------------------------------------------
        # 3. Resolve date folder
        # ---------------------------------------------------------------
        day_folder_name = f"day_{date_str}" if "day" not in date_str else date_str
        day_folder_name = self.normalize_day_prefix(day_folder_name)
        day_folder_id = self._ensure_drive_folder(day_folder_name, comp_folder_id)

        # ---------------------------------------------------------------
        # 4. Drive search query
        # ---------------------------------------------------------------
        safe_prefix = filename.split("(")[0]
        # query = f"name contains '{safe_prefix}' and '{day_folder_id}' in parents"
        if component == "model_state":
            # Model files often contain parentheses → `name='...'` breaks
            safe_prefix = filename.split("(")[0]
            query = f"name contains '{safe_prefix}' and '{day_folder_id}' in parents"
        else:
            # Framework files have no parentheses → safe for exact match
            query = f"name='{filename}' and '{day_folder_id}' in parents"


        response = self._retry_drive(
            lambda: self.drive.files().list(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
        )

        files = response.get("files", [])
        if not files:
            return None

        file_id = files[0]["id"]

        # ---------------------------------------------------------------
        # 5. Local path
        # ---------------------------------------------------------------
        local_dir = self.dir / component / day_folder_name
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename

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
        """Restore local data lake structure for the expected experiment keys."""
        print("RESTORING FROM DRIVE 1")
        if not self.remote_available or not self.drive:
            # if self.verbose: 
            print("\t⚠️ Drive unavailable → cannot restore")
            return False

        print("RESTORING FROM DRIVE 2")
        if self.framework_state_path.exists() and self.model_state_path.exists(): 
            # if self.verbose: 
            print("\t⚠️ Registry exists → aborting restore")
            return False

        restored = defaultdict(dict)

        print("RESTORING FROM DRIVE 3")
        for component, filenames in expected_keys.items():
            print(component.upper())

            for filename in filenames.keys():
                print(filename)
                
                # Check if already exists locally
                local_entry = self.backup_registry.get(component, {}).get(filename)
                local_entry = self.normalize_path(local_entry, project_root=self.dir)
                if local_entry and Path(local_entry).exists():
                    print("local entry check ", local_entry)
                    restored[component][filename] = local_entry
                    continue

                # Otherwise download
                drive_path = self._download_file_from_drive(date_str, component, filename)
                if drive_path: 
                    print("found path: ",drive_path)
                    restored[component][filename] = drive_path
                else:
                    local_path = str(self.framework_state_path/self.date_str/filename)
                    if component == "model_state": 
                        local_path = str(self.model_state_path/self.date_str/filename)
                    print("manual path: ", local_path)
                    restored[component][filename] = local_path


        print("RESTORING FROM DRIVE 4")
        # Save registry locally
        with open(self.backup_registry_path, "w") as f:
            json.dump(restored, f)

        # Update internal registry
        self.backup_registry = restored
        return True
    
    def load_new_entries(self, entries=None):
        """
        Upload a batch of new entries to Drive.
        entries = {
            component: {
                filename: local_path
            }
        }
        """
        if not self.remote_available: return False
        if not entries: entries = self.new_entries

        for component, files in entries.items():
            for filename, local_path in files.items():
                # auto-extract date from parent folder
                if Path(local_path).exists():
                    date_str = self.normalize_day_prefix(str(Path(local_path).parent.name))
                    self._upload_file_to_drive(
                        component=component,
                        date_str=date_str,
                        local_path=local_path,
                        filename=filename
                    )
        return True

    def download_any_date(self, component, filename):
        """
        Search all day_* folders in Drive under the given component
        and download the first EXACT match.
        """

        # Resolve root folders
        data_lake_id = self._ensure_drive_folder("quantum_data_lake", self.DRIVE_FOLDER_ID)
        comp_id = self._ensure_drive_folder(component, data_lake_id)

        # List all day_* folders
        day_folders = self.drive.files().list(
            q=f"'{comp_id}' in parents and mimeType='application/vnd.google-apps.folder'",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute().get("files", [])

        for folder in day_folders:
            fid = folder["id"]

            # 🔥 EXACT MATCH — no substring collision
            q = f"name = '{filename}' and '{fid}' in parents"

            response = self._retry_drive(
                lambda: self.drive.files().list(
                    q=q,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
            )

            files = response.get("files", [])
            if not files:
                continue

            file_meta = files[0]   # exact match
            file_id = file_meta["id"]
            actual_name = file_meta["name"]

            # Save using the ACTUAL filename (prevent silent mislabels)
            local_dir = self.dir / component / self.normalize_day_prefix(folder["name"])
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / actual_name

            request = self.drive.files().get_media(fileId=file_id)
            with open(local_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            return str(local_path)

        return None

    def normalize_day_prefix(self, value: str) -> str:
        """
        Normalize any string ending with:
        - 20251120
        - day_20251120
        - day_day_20251120
        - anything...20251120

        Using named regex groups for exact extraction.
        """
        s = str(value).strip()
        m = DAY_REGEX.search(s)

        if not m:
            return "day_unknown"

        date = m.group("date")   # the eight digits
        return f"day_{date}"

    def normalize_path(self, path: str, project_root: str = None) -> str:
        """
        Normalize absolute paths stored from another machine (Mac/VM/Colab).
        Converts them into the correct local project-relative path.
        """

        if path is None: return None
        p = Path(path)

        # 1) If path already exists → valid, return it
        if p.exists(): return str(p)

        # 2) Determine current environment's project root
        if project_root is None: project_root = str(Path(__file__).resolve().parents[2])   # Dynamic_Routing_Eval_Framework root

        # 3) Extract only the tail (file name) from the incoming path
        fname       = p.name                    # e.g., QuantumExperimentRunner_1.pkl
        date_folder = p.parent.name             # e.g., day_20251118
        component   = p.parent.parent.name      # framework_state or model_state

        # 4) Reconstruct a correct, portable path:
        new_path    = Path(project_root) / "daqr" / "config" / component / date_folder / fname
        return      str(new_path)
    
    def __repr__(self):
        env = self.__class__.__name__
        return env
