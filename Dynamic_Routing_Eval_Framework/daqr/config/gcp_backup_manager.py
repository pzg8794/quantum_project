from google.cloud import storage
import json
import pickle
import os
from pathlib import Path
from datetime import datetime


class GCPBackupManager:
    """Unified JSON registry backup to GCS (fast, NoSQL-style)"""

    def __init__(self, date_str, config_dir, bucket_name="quantum-backups-piter", verbose=False):
        self.new_entries = {}
        self.verbose = verbose
        self.date_str = date_str or datetime.now().strftime("%Y%m%d")
        self.dir = Path(config_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.backup_registry_path = self.dir / "backup_registry.json"
        self.backup_pickle_path = self.dir / "backup_registry.pkl"
        self.bucket_name = bucket_name
        self.regkey = "registry/backup_registry.json"

        # === Credential auto-discovery ===
        creds_path = self._find_credentials()
        if creds_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            if self.verbose:
                print(f"\tUsing GCP credentials: {creds_path}")

        # === Try connecting to GCS ===
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(bucket_name)
            self.remote_available = self._validate_bucket()
        except Exception as e:
            self.remote_available = False
            if self.verbose:
                print(f"\t⚠️ GCS unavailable: {e}")

        # === Load registry ===
        self.backup_registry = self._fetch_registry_from_gcs() or {}


    def _find_credentials(self):
        """Auto-discover service account credentials."""
        current_dir = Path(__file__).parent.resolve()

        locations = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            current_dir.parent / "quantum-gcp-credentials.json",
            current_dir / "quantum-gcp-credentials.json",
            Path.home() / "quantum-gcp-credentials.json",
            Path("/app/credentials/quantum-gcp-credentials.json"),
        ]

        for loc in locations:
            if loc and Path(loc).exists():
                return str(loc)

        return None


    def _validate_bucket(self):
        """Check if bucket exists."""
        try:
            self.storage_client.get_bucket(self.bucket_name)
            if self.verbose:
                print(f"\tGCS bucket ready: {self.bucket_name}")
            return True
        except Exception as e:
            if self.verbose:
                print(f"\t⚠️ Bucket validation failed: {e}")
            return False


    def _fetch_registry_from_gcs(self):
        """Download JSON registry from GCS."""
        if not self.remote_available:
            return None

        try:
            blob = self.bucket.blob(self.regkey)

            try:
                blob.reload()  # raises NotFound if missing
            except Exception:
                if self.verbose:
                    print("\t(no registry found in GCS)")
                return None

            registry_json = blob.download_as_text()
            registry = json.loads(registry_json)

            # Cache locally
            with open(self.backup_registry_path, "w") as f:
                f.write(registry_json)

            if self.verbose:
                print(f"\t✔ Loaded registry from GCS [{len(registry)} components]")

            return registry

        except Exception as e:
            if self.verbose:
                print(f"\t⚠️ Registry fetch from GCS failed: {e}")
            return None


    def _save_registry_to_gcs(self, registry=None):
        """Upload registry to GCS."""
        if not self.remote_available:
            if self.verbose:
                print("\t[GCS unavailable, not syncing]")
            return False

        try:
            registry = registry or self.backup_registry

            registry_json = json.dumps(registry)
            blob = self.bucket.blob(self.regkey)
            blob.upload_from_string(registry_json, content_type="application/json")

            if self.verbose:
                print(f"\t☁️ Registry synced to GCS ({self.regkey})")

            return True

        except Exception as e:
            if self.verbose:
                print(f"\t⚠️ Registry upload to GCS failed: {e}")
            return False


    def build_registry(self, force=False):
        """Load registry from GCS or local, fallback to filesystem."""
        # Try cached local registry first
        if not force and self.backup_registry_path.exists():
            try:
                with open(self.backup_registry_path, "r") as f:
                    self.backup_registry = json.load(f)
                if self.verbose:
                    print("\t📁 Loaded local registry cache")
                return self.backup_registry
            except Exception as e:
                if self.verbose:
                    print(f"\t⚠️ Local registry corrupted: {e}")
                self.backup_registry = {}

        # Try remote
        reg = self._fetch_registry_from_gcs()
        self.backup_registry = reg if reg is not None else {}

        return self.backup_registry


    def save_registry(self, registry=None):
        """Save local + cloud copy."""
        reg = registry or self.backup_registry

        # Local
        with open(self.backup_registry_path, "w") as f:
            json.dump(reg, f)

        with open(self.backup_pickle_path, "wb") as f:
            pickle.dump(reg, f)

        # Remote
        return self._save_registry_to_gcs(reg)


    def add_entry(self, component, filename, local_path, date=None):
        """Add new metadata entry."""
        date = date or self.date_str

        if component not in self.backup_registry:
            self.backup_registry[component] = {}

        self.backup_registry[component][filename] = {
            "local_path": str(local_path),
            "date": date
        }

        if component not in self.new_entries:
            self.new_entries[component] = {}

        self.new_entries[component][filename] = {
            "local_path": str(local_path),
            "date": date
        }

        return True


    def get_latest_state(self, component, filename):
        entry = self.backup_registry.get(component, {}).get(filename)
        if not entry:
            if self.verbose:
                print(f"\t⚠️ Not found: {component}/{filename}")
            return None

        path = entry["local_path"]

        if os.path.exists(path):
            ext = Path(path).suffix.lower()

            try:
                if ext == ".pkl":
                    with open(path, "rb") as f:
                        return pickle.load(f)
                elif ext in [".json", ".jsn"]:
                    with open(path, "r") as f:
                        return json.load(f)
                else:
                    with open(path, "rb") as f:
                        return f.read()
            except Exception as e:
                if self.verbose:
                    print(f"\t⚠️ Failed to load file: {e}")

        return None


    def is_empty(self):
        return not bool(self.backup_registry)


    def list_all_files(self, component=None):
        if component:
            return list(self.backup_registry.get(component, {}).keys())
        return {c: list(files.keys()) for c, files in self.backup_registry.items()}
