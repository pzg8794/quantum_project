from pathlib import Path
from collections import defaultdict
import json
import pickle
import os
from datetime import datetime

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
                    date_str = p
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
        self.date_str = self.date_str or datetime.now().strftime("%Y%m%d")
        if "day_" not in self.date_str: self.date_str = f"day_{self.date_str}"
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

        if local_path and Path(local_path).exists():
            with open(local_path, "rb") as f:
                return pickle.load(f)

        if self.verbose:
            print(f"\t⚠️ Missing local file: {local_path}")

        return None
