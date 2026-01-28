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

    DRIVE_FOLDER_ID = "0APT9hcMpvuHYUk9PVA"

    def __init__(self, date_str, config_dir, verbose=False):
        self.drive = None
        self.metadata = {}
        self.new_entries = {}
        self.verbose = verbose
        self.backup_registry = {}
        self.in_share_drive = True
        
        self.obj_query = {}
        self.dir = config_dir
        self.date_str = date_str

        # self.date_str = self.normalize_day_prefix(date_str)
        self.drive_datalake_base            = Path("/content/drive/Shareddrives/ai_quantum_computing")
        self.quantum_logs_file_name         = f"quantum_quick-run_log_{self.date_str}.txt"

        self.quantum_data_paths             = {"drive":"", "local":"", "datalake":""}
        self.quantum_data_paths["local"]    = self.dir
        self.quantum_data_paths["drive"]    = self.drive_datalake_base / "quantum_data_lake"
        
        self.quantum_data_paths["logs"]             = {}
        self.quantum_data_paths["logs"]["drive"]    = self.drive_datalake_base / "quantum_logs"
        self.quantum_data_paths["logs"]["local"]    = self.dir / "quantum_logs"

        self.quantum_data_paths["obj"]                              = {"obj":{}}
        drive_path                                                  = self.quantum_data_paths["drive"]
        self.quantum_data_paths["obj"]["model_state"]               = {}
        self.quantum_data_paths["obj"]["framework_state"]           = {}
        self.quantum_data_paths["obj"]["model_state"]["local"]      = self.dir / "model_state"
        self.quantum_data_paths["obj"]["model_state"]["drive"]      = self.dir / "model_state"
        self.quantum_data_paths["obj"]["framework_state"]["local"]  = self.dir / "framework_state"
        self.quantum_data_paths["obj"]["framework_state"]["drive"]  = self.dir / "framework_state"
        

        self.registry_file_paths            = {'drive':"", "local":"", "datalake":""}
        self.registry_file_paths["drive"]   = self.dir / "drive_backup_registry.json"
        self.registry_file_paths["local"]   = self.dir / "local_backup_registry.json"
        self.registry_file_paths["datalake"]= drive_path / "backup_registry.json"

        self.in_share_drive             = True if self.quantum_data_paths["logs"]["drive"].exists() else False
        self.mode                       = "drive" if self.in_share_drive else "local"

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
                        recovered = self._download_file_from_drive(self.date_str, comp, key)
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

        print(f"→ Looking for 'backup_registry.json' in Drive folder: {self.DRIVE_FOLDER_ID}")
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


    def save_registry(self, registry=None):
        reg = registry or self.backup_registry

        # Local JSON save
        # Local pickle save
        file = str(self.registry_file_paths[self.mode])
        with open(file, "wb") as f: pickle.dump(reg, f)
        with open(file.replace(".pkl",".json"),"w") as f:json.dump(reg,f)
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
        root_id                 =   self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)

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

    def set_regestry_qry(self, filename, day_folder_id):
        self.obj_query["model_state"] = f"""name contains '{filename.split("(")[0]}' and '{day_folder_id}' in parents"""
        self.obj_query["framework_state"] = f"name='{filename}' and '{day_folder_id}' in parents"
        return True
    
    def _download_file_from_drive(self, date_str, component, filename, storage_dir="quantum_data_lake"):
        """
        Download a single file from Drive into:
            {config_dir}/{component}/day_{date_str}/{filename}

        This mirrors the same structure created by _upload_file_to_drive.
        """
        if self.in_share_drive:
            # Direct filesystem path in shared drive - no download needed
            local_path =  self.quantum_data_paths["obj"][component]["drive"] / date_str / filename
            if local_path.exists(): return str(local_path)

        if not self.remote_available or not self.drive: return None
        
        # ---------------------------------------------------------------
        # 1. Resolve quantum_data_lake root
        # ---------------------------------------------------------------
        data_lake_id = self._ensure_drive_folder(storage_dir, self.DRIVE_FOLDER_ID)
        
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
        self.set_regestry_qry(filename, day_folder_id)[component]

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
        """Restore local data lake structure for the expected experiment keys."""
        print("RESTORING FROM DRIVE 1")
        if not self.remote_available or not self.drive:
            # if self.verbose: 
            print("\t⚠️ Drive unavailable → cannot restore")
            return False

        print("RESTORING FROM DRIVE 2")
        comp_path = self.quantum_data_paths["obj"]
        if comp_path["framework_state"][self.mode].exists() and comp_path["model_state"][self.mode].exists(): 
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
                local_entry = None
                try:                local_entry = self.backup_registry.get(component, {}).get(filename)
                except Exception:   local_entry = self.normalize_path(local_entry, project_root=self.dir)
                if local_entry and Path(local_entry).exists():
                    print("local entry check ", local_entry)
                    restored[component][filename] = str(Path(drive_path or local_path).resolve())
                    continue

                # Otherwise download
                drive_path = self._download_file_from_drive(date_str, component, filename)
                if drive_path: 
                    print("found path: ",drive_path)
                    restored[component][filename] = str(Path(drive_path or local_path).resolve())
                else:
                    local_path = str(self.quantum_data_paths["obj"][component][self.mode]/self.date_str/filename)
                    restored[component][filename] = local_path
                    print("manual path: ", local_path)


        print("RESTORING FROM DRIVE 4")
        # Save registry locally
        file = str(self.registry_file_paths[self.mode].replace(".pkl", ".json"))
        with open(file, "w") as f: json.dump(restored, f)

        # Update internal registry
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
        
        if self.in_share_drive:
            # Direct filesystem search in shared drive
            for mode in ["drive", "local"]:
                comp_dir =  self.quantum_data_paths[mode] / component
                if not comp_dir.exists(): return None
                
                # Search all day_* folders
                for day_folder in comp_dir.iterdir():
                    if not day_folder.is_dir() or not day_folder.name.startswith("day_"): continue
                
                    file_path = day_folder / filename
                    if file_path.exists():
                        if self.verbose: print(f"✓ Found: {file_path}")
                    return str(file_path)
            return None
        
        if not self.remote_available or not self.drive: return None
        # Drive API for non-shared-drive environments
        data_lake_id= self._ensure_drive_folder("quantum_data_lake", self.DRIVE_FOLDER_ID)
        comp_id     = self._ensure_drive_folder(component, data_lake_id)
        if not comp_id: return None
        
        # List all day_* folders
        day_folders = self.drive.files().list(
            q=f"'{comp_id}' in parents and mimeType='application/vnd.google-apps.folder'",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute().get("files", [])
        
        for folder in day_folders:
            fid = folder["id"]
            # EXACT MATCH — no substring collision
            q = f"name = '{filename}' and '{fid}' in parents"
            response = self._retry_drive(
                lambda: self.drive.files().list(
                    q=q, supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
            )
            files = response.get("files", [])
            if not files: continue
            
            file_meta = files[0]
            file_id = file_meta["id"]
            actual_name = file_meta["name"]
            
            # Save using the ACTUAL filename
            local_dir =  self.quantum_data_paths["local"] / component / folder["name"]
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / actual_name
            
            print("\tFile Downloaded in local_path")
            request = self.drive.files().get_media(fileId=file_id)
            with open(local_path, "wb") as f:
                done = False
                downloader = MediaIoBaseDownload(f, request)
                while not done: status, done = downloader.next_chunk()
            
            return str(local_path)
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
