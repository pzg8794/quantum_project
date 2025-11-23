import json
import pickle
import os, sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
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
        """
        Redirect stdout/stderr to a timestamped log file in:
        {project_root}/quantum_data_lake/logs/
        """
        self.quantum_logs_file_name = f"quantum_{file_name}_log_{self.date_str}.txt"
        logfile = self.quantum_logs_path / self.quantum_logs_file_name
        self.quantum_logs_path.mkdir(parents=True, exist_ok=True)

        # Save originals only once
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        # Open log file
        f = open(logfile, "w")
        self._log_file = f

        sys.stdout = f
        sys.stderr = f

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
                try:    self.upload_file_to_drive(logfile)
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
