import json
import pickle
import threading
import os, sys, io
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from threading import Lock
from googleapiclient.http import MediaIoBaseDownload
from .gd_backup_manager import GoogleDriveBackupManager


class LocalBackupManager(GoogleDriveBackupManager):

    def __init__(self, date_str, config_dir, verbose=False):
        super().__init__(date_str, config_dir, verbose=verbose)
        # FIX: Minimal locks only where needed

    def _scan_local_files(self, expected_keys=None, load_to_drive=False, force=False):
        """Scan local filesystem and optionally mirror to Google Drive."""
        temp = defaultdict(dict)
        valid_exts = {".pkl", ".json"}

        for dirpath, _, filenames in os.walk(self.quantum_datalake_path):
            dir_path = Path(dirpath)

            try: relative_path = dir_path.relative_to(self.quantum_datalake_path )
            except ValueError: continue

            parts = relative_path.parts
            if not parts: continue
            component = parts[0]

            # Extract date_str from folders like day_20251120
            date_str = None
            for p in parts:
                if p.startswith("day_"):
                    # date_str = self.normalize_day_prefix(p)
                    date_str = p
                    break
            if not date_str: continue

            for fname in filenames:
                if Path(fname).suffix not in valid_exts: continue
                abs_path = str(dir_path / fname)
                temp[component][fname] = abs_path
                if load_to_drive:
                    self.download_drive_metadata()
                    try:    
                        self.metadata[fname]
                        print(f"\t→ Files {fname} was already stored")
                        if not force: continue
                    except Exception as e: print(f"\t→ Files {fname} is uploading")
                    self._upload_file_to_drive(component, date_str=date_str, local_path=abs_path, filename=fname)

        # Final registry build
        registry = {comp: {fname: meta for fname, meta in files.items()} for comp, files in temp.items()}
        return registry
    
    def build_registry(self, force=False, expected_keys=None):
        """Build registry with recursion protection."""
        # if not force and hasattr(self, '_registry_built_today'):
        #     print(f"\t→ Using cached registry from today")
        #     return self.backup_registry
        self.backup_registry = self._scan_local_files(expected_keys=None)  # Always full scan first
        total = sum(len(v) for v in self.backup_registry.values())
        print(f"\t→ Filesystem scan found {total} files")
        
        # Always save local registry
        self.backup_registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.backup_registry_path, "w") as f:
            json.dump(self.backup_registry, f, indent=2)
        print(f"\t→ Local registry updated at: {self.backup_registry_path}")
        
        # # FIX: Filter AFTER scan, not during
        # if expected_keys:
        #     print(f"\t→ Filtering {len(expected_keys)} expected keys...")
        #     self.backup_registry = self._filter_registry(self.backup_registry, expected_keys)
        #     filtered_total = sum(len(v) for v in self.backup_registry.values())
        #     print(f"\t→ Filtered registry contains {filtered_total} keys")
        
        # Mark as built today
        self._registry_built_today = True
        
        # Upload to Drive ONLY if forced
        # if force and self.remote_available:
        self._save_registry_to_gcs("backup_registry.json")
        print("\t→ Drive registry updated")
        
        print("===================== REGISTRY BUILD COMPLETE =====================\n")
        return self.backup_registry
    

    def save_file(self, component, filename, file_data):
        # self.date_str = self.normalize_day_prefix(self.date_str)
        save_dir = self.dir / component / self.date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename
        backup_path = None

        # CRITICAL FIX: Backup existing file before overwrite
        if file_path.exists():
            backup_path = file_path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl.bak")
            print(f"⚠️  Backing up existing file: {file_path} → {backup_path}")
            file_path.replace(backup_path)
        
        try:
            with open(file_path, "wb") as f:
                pickle.dump(file_data, f)
            # Verify save worked
            file_size = file_path.stat().st_size
            if file_size == 0:
                raise IOError("Saved file is empty - rollback!")
            
            print(f"✓ Saved: {component}/{filename} ({file_size/1024/1024:.2f} MB)")
            
            # Update registry
            self.backup_registry.setdefault(component, {})[filename] = str(file_path)
            self.new_entries.setdefault(component, {})[filename] = str(file_path)
            
            return str(file_path)
        except Exception as e:
            # Emergency rollback if save fails
            if backup_path and backup_path.exists():
                backup_path.replace(file_path)
                print(f"🚨 Save failed, restored from backup: {e}")
            raise



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
                if isinstance(result, dict): return result.get("local_path", None)
                # Else Drive returns a direct path
                return str(result)

        # -------------------------------------------------------
        # 2. Local fallback (backward compatible)
        # -------------------------------------------------------
        # entry may be:
        #   A) old style → {"local_path": "...", "date": "..."}
        #   B) new style → "/path/to/file.pkl"
        local_path = entry.get("local_path") if isinstance(entry, dict) else entry

        if local_path:
            # FIX: Normalize path parts
            try:
                parts = Path(local_path).parts
                fixed_parts = []
                for p in parts:
                    # if "day_" in p: fixed_parts.append(self.normalize_day_prefix(p))
                    if "day_" in p: fixed_parts.append(p)
                    else: fixed_parts.append(p)
                local_path = str(Path(*fixed_parts))
            except Exception as e: print(f"⚠️ Path normalization failed: {e}")

        if local_path and Path(local_path).exists():
            if self.verbose: print(f"\t✓ Found: {component}/{filename} → {local_path}")
            return local_path  # Return string path only

        if self.verbose: print(f"\t⚠️ Missing local file: {local_path}")
        return None

    def load_state_data(self, component, filename):
        """Load and return the actual data from a state file."""
        path = self.get_latest_state(component, filename)
        if not path or not Path(path).exists(): return None
        try:
            with open(path, "rb") as f: data = pickle.load(f)
            print(f"✓ Loaded data from: {path}")
            return data
        except Exception as e:
            print(f"❌ Failed to load data from {path}: {e}")
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
            
            if not self.in_share_drive:
                logfile = self.quantum_logs_path / self.quantum_logs_file_name
                try:    self._upload_file_to_drive(component=None, local_path=logfile, date_str=self.date_str, filename=self.quantum_logs_file_name, parent_dir="quantum_logs")
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
        """Scan local folder structure with defensive error handling."""
        root = self.quantum_logs_path
        if not root.exists() or len(self.metadata) != 0: return False
        
        print(f"🔍 Scanning local metadata from: {root}")
        scanned_components = 0
        skipped_errors = 0
        
        try:
            for comp in root.iterdir():
                if not comp.is_dir():
                    continue
                    
                try:
                    comp_key = comp.name
                    self.metadata.setdefault(comp_key, {})
                    scanned_components += 1
                    
                    print(f"  📁 Processing component: {comp_key}")
                    
                    for day in comp.iterdir():
                        if not day.is_dir():
                            continue
                            
                        try:
                            date_key = day.name
                            self.metadata[comp_key].setdefault(date_key, {})
                            
                            file_count = 0
                            for f in day.iterdir():
                                if f.is_file():
                                    try:
                                        self.metadata[comp_key][date_key][f.name] = {"local_path": str(f)}
                                        file_count += 1
                                    except (OSError, PermissionError) as e:
                                        print(f"    ⚠️ Skipped file {f.name}: {e}")
                                        skipped_errors += 1
                                        continue
                            
                            if file_count > 0:
                                print(f"    📄 Found {file_count} files in {date_key}")
                            else:
                                print(f"    📭 Empty folder: {date_key}")
                                
                        except (OSError, PermissionError, NotADirectoryError) as e:
                            print(f"  ⚠️ Skipped day folder {day.name}: {e}")
                            skipped_errors += 1
                            continue
                            
                except (OSError, PermissionError, NotADirectoryError) as e:
                    print(f"⚠️ Skipped component folder {comp.name}: {e}")
                    skipped_errors += 1
                    continue
                    
        except Exception as e:
            print(f"❌ Critical error scanning {root}: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"✅ Local metadata scan complete: {scanned_components} components, {skipped_errors} errors")
        return scanned_components > 0


    def _build_metadata_remote(self, parent_dir="quantum_logs"):
        """Scan Drive folder structure with proper error handling."""
        if not self.remote_available or not self.drive or len(self.metadata) != 0: 
            return False
        
        try:
            root_id = self._ensure_drive_folder(parent_dir, self.DRIVE_FOLDER_ID)
        except Exception as e:
            print(f"❌ Failed to get root folder: {e}")
            return False
        
        try:
            # List component folders with retry and error handling
            comp_folders = self._retry_drive(
                lambda: self.drive.files().list(
                    q=f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                    fields="files(id,name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
            )
            comp_folders = comp_folders.get("files", [])
        except Exception as e:
            print(f"❌ Failed to list component folders: {e}")
            return False
        
        for comp in comp_folders:
            try:
                comp_key = comp["name"]
                comp_id = comp["id"]
                self.metadata.setdefault(comp_key, {})
                
                # List day folders
                day_folders = self._retry_drive(
                    lambda: self.drive.files().list(
                        q=f"'{comp_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                        fields="files(id,name)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    ).execute()
                )
                day_folders = day_folders.get("files", [])
            except KeyError as e:
                print(f"⚠️ Invalid component folder {comp.get('name', 'unknown')}: {e}")
                continue
            except Exception as e:
                print(f"❌ Failed to process component {comp_key}: {e}")
                continue
            
            for day in day_folders:
                try:
                    day_key = day["name"]
                    day_id = day["id"]
                    self.metadata[comp_key].setdefault(day_key, {})
                    
                    # List files under day folder
                    files_list = self._retry_drive(
                        lambda: self.drive.files().list(
                            q=f"'{day_id}' in parents",
                            fields="files(id,name)",
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True
                        ).execute()
                    )
                    files = files_list.get("files", [])
                    
                    for f in files:
                        try:
                            self.metadata[comp_key][day_key][f["name"]] = {"drive_id": f["id"]}
                        except KeyError as e:
                            print(f"⚠️ Invalid file entry in {day_key}: {e}")
                            continue
                            
                except (KeyError, TypeError) as e:
                    print(f"⚠️ Invalid day folder {day.get('name', 'unknown')}: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Failed to process day {day_key}: {e}")
                    continue
        
        return True

    def build_drive_metadata(self, parent_dir="quantum_logs"):
        """
        Build metadata by scanning the actual folder structure.
        If in shared drive → list local files.
        Else → list Drive files.
        Returns:
            metadata = { component_or_None : { date : { filename : {drive_id/local_path} } } }
        """

        print("\n===== build_drive_metadata DEBUG =====")
        print(f"in_share_drive       = {self.in_share_drive}")
        print(f"parent_dir           = {parent_dir}")
        print(f"Before download: metadata_len = {len(self.metadata)}")

        # Attempt to load metadata.json
        download_ok = self.download_drive_metadata(parent_dir, "metadata.json")
        print(f"download_drive_metadata() returned = {download_ok}")
        print(f"After download: metadata_len = {len(self.metadata)}")

        # If metadata already exists, stop here
        if download_ok and len(self.metadata) > 0:
            print("→ Early exit: metadata already exists")
            print("===== END build_drive_metadata =====\n")
            return True

        # =======================================================
        # CASE 1: Running INSIDE shared drive → read local folder
        # =======================================================
        if self.in_share_drive:
            print("→ Branch: LOCAL metadata build")
            result = self._build_metadata_local(parent_dir)
            print(f"LOCAL build result: {result}")
            print(f"After local build: metadata_len = {len(self.metadata)}")
            print("===== END build_drive_metadata =====\n")
            return result

        # =======================================================
        # CASE 2: Running OUTSIDE shared drive → use Drive API
        # =======================================================
        print("→ Branch: REMOTE metadata build")
        result = self._build_metadata_remote(parent_dir)
        print(f"REMOTE build result: {result}")
        print(f"After remote build: metadata_len = {len(self.metadata)}")
        print("===== END build_drive_metadata =====\n")
        return result


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
        if len(self.metadata) == 0: self.download_drive_metadata(str(parent_dir), filename)
        if len(self.metadata) == 0: self.build_drive_metadata(parent_dir)
        if len(self.metadata) == 0 or len(exp_registry)== 0:return False
        curr_metadata_len = len(self.metadata)
        for component in exp_registry.keys(): self.metadata.update(exp_registry[component])
        return len(self.metadata) > curr_metadata_len

    def load_drive_metadata(self, parent_dir="quantum_logs"):
        """Download metadata.json from Drive if present."""
        if not self.update_drive_metadata(parent_dir=parent_dir): return False
        
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
            try:
                s.write(message)
                s.flush()
            except (IOError, ValueError):
                pass  # Ignore broken streams
    
    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass
