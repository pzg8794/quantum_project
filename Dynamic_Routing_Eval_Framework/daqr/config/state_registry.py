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
    """
    Read the best-known path for a state file from the config registry.

    Supports both:
    - legacy layout: `config_registry[component][filename] -> str`
    - canonical layout: `config_registry["state"][filename] -> {active_path, drive_path, ...}`
    """
    try:
        comp_reg = config_registry.get(component, {})
        if isinstance(comp_reg, dict) and filename in comp_reg:
            value = comp_reg.get(filename)
            return value if isinstance(value, str) else None
    except Exception:
        pass

    try:
        state_reg = config_registry.get("state", {})
        entry = state_reg.get(filename) if isinstance(state_reg, dict) else None
        if isinstance(entry, dict):
            active_path = entry.get("active_path") or ""
            drive_path = entry.get("drive_path") or ""
            return active_path or drive_path or None
    except Exception:
        pass

    return None
