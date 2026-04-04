"""
State registry update helpers.

This module is intentionally dependency-light so it can be unit-tested without
importing the full experiment configuration stack (which pulls in heavy ML deps).
"""

from __future__ import annotations


def register_state_path(*, config_registry: dict, backup_mgr, component: str, filename: str, path: str) -> None:
    """
    Update in-memory registries and persist the backup registry.

    Contracts:
    - Always keep caller settings untouched (registry is metadata only).
    - Persist after updates so cross-day resume can discover new state files
      without requiring a full filesystem rescan.
    """
    changed = False
    try:
        comp_reg = config_registry.setdefault(component, {})
        if comp_reg.get(filename) != path:
            comp_reg[filename] = path
            changed = True
    except Exception:
        pass

    try:
        mgr_reg = backup_mgr.backup_registry.setdefault(component, {})
        if mgr_reg.get(filename) != path:
            mgr_reg[filename] = path
            changed = True
        if hasattr(backup_mgr, "new_entries"):
            mgr_new = backup_mgr.new_entries.setdefault(component, {})
            if mgr_new.get(filename) != path:
                mgr_new[filename] = path
                changed = True
    except Exception:
        pass

    if not changed:
        return

    try:
        autosave = getattr(backup_mgr, "registry_autosave", True)
        if autosave and hasattr(backup_mgr, "save_registry"):
            backup_mgr.save_registry(getattr(backup_mgr, "backup_registry", None))
    except Exception:
        pass


def get_registered_state_path(*, config_registry: dict, component: str, filename: str) -> str | None:
    """Return the best-known path for a saved state file.

    Supports both legacy registries:
      config_registry[component][filename] -> "/abs/path/to/file.pkl"

    And canonical registries (used by Drive offload tooling):
      config_registry["state"][filename] -> {"active_path": "...", "drive_path": "...", ...}

    Preference order:
    1) Legacy component registry string
    2) Canonical registry active_path
    3) Canonical registry drive_path
    """
    try:
        legacy = config_registry.get(component, {}).get(filename)
        if isinstance(legacy, str) and legacy:
            return legacy
        if isinstance(legacy, dict):
            active = str(legacy.get("active_path") or "").strip()
            if active:
                return active
            drive = str(legacy.get("drive_path") or "").strip()
            if drive:
                return drive
    except Exception:
        pass

    try:
        entry = config_registry.get("state", {}).get(filename)
        if isinstance(entry, str) and entry:
            return entry
        if isinstance(entry, dict):
            active = str(entry.get("active_path") or "").strip()
            if active:
                return active
            drive = str(entry.get("drive_path") or "").strip()
            if drive:
                return drive
    except Exception:
        pass

    return None
