import json
import pickle
import os, sys, io
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from googleapiclient.http import MediaIoBaseDownload
from .gd_backup_manager import GoogleDriveBackupManager


class LocalBackupManager(GoogleDriveBackupManager):

    def __init__(self, date_str, config_dir, verbose=False):
        super().__init__(date_str, config_dir, verbose=verbose)
        # ⚠️ NO LOCKS ANYWHERE


    def build_registry(self, force=False, expected_keys=None):
        """
        Same logic as before, but with EXTREMELY detailed printouts
        so you can see every decision being made.
        """
        self.backup_registry = self._scan_local_files(None)

        total = sum(len(v) for v in self.backup_registry.values())
        print(f"\t→ Filesystem scan found {total} files")

        # Always save local registry
        # if not self.remote_available:
        with open(self.backup_registry_path, "w") as f:
            json.dump(self.backup_registry, f)
        print(f"\t→ Local registry updated at: {self.backup_registry_path}")

        # -------------------------------------------------------
        # 4. Upload to Drive ONLY if Drive was empty
        # -------------------------------------------------------
        if force: self._save_registry_to_gcs("backup_registry.json")
        print("\t→ Drive registry updated")

        print("===================== REGISTRY BUILD COMPLETE =====================\n")
        if expected_keys: self.backup_registry = self._filter_registry(self.backup_registry, expected_keys)
        return self.backup_registry

    def _scan_local_files(self, expected_keys=None, load_to_drive=False):
        """Scan local filesystem and optionally mirror to Google Drive."""
        temp = defaultdict(dict)
        valid_exts = {".pkl", ".json"}

        for dirpath, _, filenames in os.walk(self.dir):
            dir_path = Path(dirpath)

            try: relative_path = dir_path.relative_to(self.dir)
            except ValueError: continue

            parts = relative_path.parts
            if not parts: continue

            component = parts[0]

            # Extract date_str from folders like day_20251120
            date_str = None
            for p in parts:
                if p.startswith("day_"):
                    date_str = self.normalize_day_prefix(p)
                    break

            if not date_str:
                continue

            for fname in filenames:
                if Path(fname).suffix not in valid_exts:
                    continue

                abs_path = str(dir_path / fname)

                # Pick latest version per filename
                # if (fname not in temp[component]):
                temp[component][fname] = abs_path

                # 🟦 NEW: Optional Drive mirroring
                if load_to_drive:
                    self._upload_file_to_drive(
                        component=component,
                        date_str=date_str,
                        local_path=abs_path,
                        filename=fname
                    )

        # Final registry build
        registry = {comp: {fname: meta for fname, meta in files.items()} for comp, files in temp.items()}
        return registry if not expected_keys else self._filter_registry(registry, expected_keys)


    def save_file(self, component, filename, file_data):
        """Exactly the same behavior you already had — no locks."""
        self.date_str = self.normalize_day_prefix(self.date_str or f"day_{datetime.now().strftime('%Y%m%d')}")
        save_dir = self.dir / component / self.date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename

        with open(file_path, "wb") as f:
            pickle.dump(file_data, f)

        if component not in self.backup_registry:
            self.backup_registry[component] = {}
        self.backup_registry[component][filename] = str(file_path)

        if component not in self.new_entries:
            self.new_entries[component] = {}
        self.new_entries[component][filename] = str(file_path)

        self.save_registry()
        if self.verbose:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"\tSaved: {component}/{filename} ({size_mb:.2f} MB)")

        return str(file_path)


    def get_latest_state(self, component, filename):
        """Backward-compatible until registry is fully cleaned."""
        entry = self.backup_registry.get(component, {}).get(filename)

        if not entry:
            if self.verbose:
                print(f"\t⚠️ Not found: {component}/{filename}")
            return None

        # -------------------------------------------------------
        # 1. Try Google Drive first (if available)
        # -------------------------------------------------------
        if self.remote_available:
            result = super().get_latest_state(component, filename)

            if result is not None:
                # If Drive still returns old structure {local_path: ..., date: ...}
                if isinstance(result, dict):
                    return result.get("local_path", None)
                # Else Drive returns a direct path
                return result

        # -------------------------------------------------------
        # 2. Local fallback (backward compatible)
        # -------------------------------------------------------
        # entry may be:
        #   A) old style → {"local_path": "...", "date": "..."}
        #   B) new style → "/path/to/file.pkl"

        local_path = entry.get("local_path") if isinstance(entry, dict) else entry
        if local_path:
            parts = Path(local_path).parts
            fixed_parts = []
            for p in parts:
                if "day" in p: fixed_parts.append(self.normalize_day_prefix(p))
                else: fixed_parts.append(p)
            local_path = str(Path(*fixed_parts))

        if local_path and Path(local_path).exists():
            with open(local_path, "rb") as f:
                return pickle.load(f)

        if self.verbose:
            print(f"\t⚠️ Missing local file: {local_path}")

        return None

    def init_logging_redirect(self, file_name="quantum_quick_runs"):
        self.quantum_logs_file_name = f"quantum_{file_name}_log_{self.date_str}.txt"
        logfile = self.quantum_logs_path / self.quantum_logs_file_name
        self.quantum_logs_path.mkdir(parents=True, exist_ok=True)

        # Save originals
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        # Open file
        f = open(logfile, "w")
        self._log_file = f

        # Tee to both terminal AND file
        sys.stdout = TeeStream(self._orig_stdout, f)
        sys.stderr = TeeStream(self._orig_stderr, f)

        print(f"[Logging Redirect Initialized]")
        print(f"Log File: {logfile}")

        return logfile


    def stop_logging_redirect(self):
        """
        Restore stdout/stderr after a redirect created by init_logging_redirect().
        Safe to call even if logging was never initialized.
        """
        try:
            # If no prior redirect saved, do nothing
            if not hasattr(self, "_orig_stdout") or not hasattr(self, "_orig_stderr"):
                return

            # Restore the streams
            sys.stdout = self._orig_stdout
            sys.stderr = self._orig_stderr

            # Close log file if we opened it
            if hasattr(self, "_log_file") and self._log_file:
                try:    self._log_file.close()
                except: pass
            
            if self.in_share_drive:
                logfile = self.quantum_logs_path / self.quantum_logs_file_name
                try:    self._upload_file_to_drive(None, local_path=logfile, file_name=self.quantum_logs_file_name, parent_dir="quantum_logs")
                except: pass

            # Clean attributes so multiple redirects won't break things
            del self._orig_stdout
            del self._orig_stderr
            del self._log_file

            print("[Logging Redirect Stopped]")

        except Exception as e:
            # Never crash the system over logging cleanup
            try:    print(f"[Warning] stop_logging_redirect encountered an issue: {e}")
            except: pass



    def _build_metadata_local(self, parent_dir="quantum_logs"):
        """Scan the local folder structure and build metadata dict."""
        root = self.quantum_logs_path if parent_dir == "quantum_logs" else self.quantum_data_lake_path
        if not root.exists() or len(self.metadata) != 0: return False

        for comp in root.iterdir():
            if not comp.is_dir(): continue
            comp_key = comp.name
            self.metadata.setdefault(comp_key, {})

            for day in comp.iterdir():
                if not day.is_dir(): continue
                date_key = day.name
                self.metadata[comp_key].setdefault(date_key, {})

                for f in day.iterdir():
                    if f.is_file(): self.metadata[comp_key][date_key][f.name] = {"local_path": str(f)}

        return True

    def _build_metadata_remote(self, parent_dir="quantum_logs"):
        """Scan Drive folder structure and build metadata dict."""
        if not self.remote_available or not self.drive or len(self.metadata) != 0: return False
        root_id = self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)

        # list component folders
        comp_folders = self._retry_drive(
            lambda: self.drive.files().list(
                q=f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id,name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
        ).get("files", [])

        for comp in comp_folders:
            comp_key = comp["name"]
            comp_id  = comp["id"]
            self.metadata.setdefault(comp_key, {})

            # list day folders
            day_folders = self._retry_drive(
                lambda: self.drive.files().list(
                    q=f"'{comp_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                    fields="files(id,name)", supportsAllDrives=True, includeItemsFromAllDrives=True
                ).execute()
            ).get("files", [])

            for day in day_folders:
                day_key = day["name"]
                day_id  = day["id"]
                self.metadata[comp_key].setdefault(day_key, {})

                # files under the day folder
                files = self._retry_drive(
                    lambda: self.drive.files().list(
                        q=f"'{day_id}' in parents", fields="files(id,name)",
                        supportsAllDrives=True, includeItemsFromAllDrives=True
                    ).execute()
                ).get("files", [])
                for f in files: self.metadata[comp_key][day_key][f["name"]] = {"drive_id": f["id"]}

        return True

    def build_drive_metadata(self, parent_dir="quantum_logs"):
        """
        Build metadata by scanning the actual folder structure.
        If in shared drive → list local files.
        Else → list Drive files.
        Returns:
            metadata = { component_or_None : { date : { filename : {drive_id/local_path} } } }
        """

        # If metadata already exists (or download returned True), don't rebuild
        if self.download_drive_metadata(): return self.metadata

        # =======================================================
        # CASE 1: Running INSIDE shared drive → read local folder
        # =======================================================
        if self.in_share_drive: return self._build_metadata_local(parent_dir)

        # =======================================================
        # CASE 2: Running OUTSIDE shared drive → use Drive API
        # =======================================================
        return self._build_metadata_remote(parent_dir)

    def _download_metadata_local(self, filename="metadata.json"):
        """Load metadata.json from local quantum_logs directory."""
        metadata_path = self.quantum_logs_path / filename
        if not metadata_path.exists(): return False
        
        with open(metadata_path, "r") as f:
            self.metadata = json.load(f)
        return True

    def _download_metadata_remote(self, parent_dir="quantum_logs", filename="metadata.json"):
        """Download metadata.json from Drive."""
        root_id = self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)
        query   = f"name='{filename}' and '{root_id}' in parents"
        response= self.drive.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()

        files   = response.get("files", [])
        if not files: return False
        file_id = files[0]["id"]
        request = self.drive.files().get_media(fileId=file_id)
        data    = request.execute()

        self.metadata = json.loads(data.decode("utf-8"))
        return True

    def download_drive_metadata(self, parent_dir="quantum_logs", filename="metadata.json"):
        """
        Download metadata.json from Drive.
        If in shared drive → load from local file.
        Returns True if loaded, False if missing.
        """

        # ===========================================
        # CASE 1 — in shared drive → read local copy
        # ===========================================
        if self.in_share_drive: return self._download_metadata_local(filename)
        
        # ===========================================
        # CASE 2 — remote → download from Drive
        # ===========================================
        return self._download_metadata_remote(parent_dir, filename)


    def update_drive_metadata(self, exp_registry=None, parent_dir="quantum_logs", filename="metadata.json"):
        """
        Merge exp_registry into metadata.json in Drive.
        Uses correct source depending on in_share_drive flag.
        """
        if exp_registry is None: exp_registry = self.backup_registry
        if len(self.metadata) == 0: self.download_drive_metadata()
        if len(self.metadata) == 0: self.build_drive_metadata()
        if len(self.metadata) == 0 or len(exp_registry) == 0: return False
        curr_metadata_len = len(self.metadata)
        self.metadata.update(exp_registry)
        return len(self.metadata) > curr_metadata_len

    def load_drive_metadata(self, parent_dir="quantum_logs"):
        """Download metadata.json from Drive if present."""
        if not self.update_drive_metadata(): return False
        
        if self.in_share_drive: 
            metadata_path = self.quantum_logs_path / "metadata.json"
            self.quantum_logs_path.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, "w") as f: json.dump(self.metadata, f)
            return True
        
        root_id = self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)
        resp    =       self._retry_drive(
                            lambda: self.drive.files().list(
                                q=f"name='metadata.json' and '{root_id}' in parents",fields="files(id)",
                                supportsAllDrives=True, includeItemsFromAllDrives=True
                            ).execute()
                        )
        files   =       resp.get("files", [])
        if not files:   return False

        file_id = files[0]["id"]
        request = self.drive.files().get_media(fileId=file_id)
        data    = request.execute()
        self.metadata = json.loads(data.decode("utf-8"))
        return True

class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for s in self.streams:
            s.write(message)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()