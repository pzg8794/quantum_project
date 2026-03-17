## Legacy Drive Flow (Working Baseline from `a84f32e1`)

This document captures the old Drive behavior that is being used as the recovery baseline.

### 1. Manager initialization
- `GoogleDriveBackupManager` starts with a fixed shared-drive folder ID.
- It derives the parent data root from the local config directory layout.
- It decides whether it is running inside the shared-drive layout by checking whether `quantum_logs` exists at the expected parent path.
- It always creates local filesystem paths for:
  - `quantum_data_lake`
  - `quantum_logs`
  - `framework_state`
  - `model_state`

### 2. Credentials and Drive API
- Credentials are discovered from a fixed list of filesystem locations.
- If credentials exist, the manager initializes the Google Drive API client.
- If Drive API setup fails, the manager falls back to local-only behavior.

### 3. Registry source of truth
- The manager attempts to fetch `backup_registry.json` from Drive.
- If found, it caches the registry locally.
- If expected keys are provided, the fetched registry is filtered against those keys.
- If a registry entry points to a missing local file, the manager attempts Drive recovery for that file.

### 4. Local scan behavior
- `LocalBackupManager._scan_local_files(...)` scans `quantum_data_lake` recursively.
- It builds a registry from local files using:
  - component directory
  - `day_YYYYMMDD`
  - filename
- Optional `load_to_drive=True` mirrors discovered files to Drive.

### 5. Save behavior
- `LocalBackupManager.save_file(...)` writes the object locally first.
- If a file already exists, it is backed up before overwrite.
- After save, the local registry is updated immediately:
  - `backup_registry`
  - `new_entries`
- The returned durable path is the local saved file path.

### 6. Load / resume behavior
- `get_latest_state(...)` first tries Drive-backed lookup if Drive is available.
- If that fails, it falls back to the local path stored in the registry.
- `resume_obj(...)`:
  - asks the backup manager for the latest state path
  - normalizes it relative to the Drive data root if needed
  - checks file existence and size
  - loads the pickle
  - compares the loaded object to the current object for resume compatibility

### 7. Logging behavior
- Runtime logs are written locally under `quantum_logs`.
- If not running from the shared-drive layout, log files are uploaded to Drive on shutdown.

### 8. Key legacy characteristics to preserve
- local-first save path
- immediate registry update on save
- Drive used for:
  - registry fetch
  - recovery of missing files
  - optional mirroring / log upload
- simple path derivation from the config directory layout
- no Drive-workspace auto-detection logic
