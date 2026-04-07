#!/usr/bin/env python3
"""Aggregate `day_*` state subdirectories into a single target `day_*` folder.

Purpose
-------
This tool stabilizes resume/scanning by reducing state sprawl across many
`day_YYYYMMDD/` folders.

Key policy (matches your established cleanup logic)
---------------------------------------------------
If duplicate filenames exist across days, keep the LARGEST file (size wins).
If sizes tie, keep the NEWEST by modification time.

Modes
-----
- Local aggregation (default): operates under `daqr/config/<component>/day_*`.
- Remote aggregation (opt-in): with `--remote` it can scan Drive, and with
    `--remote-execute` it will apply changes.

Remote safety notes
-------------------
When executing remote cleanup, this tool removes smaller duplicates by moving
them to Drive Trash (not permanent delete). This matches common Drive
permission sets where trashing is allowed but permanent deletion is not.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _day_today() -> str:
    return f"day_{dt.datetime.now().strftime('%Y%m%d')}"


def _normalize_target(target: str) -> str:
    target = (target or "").strip()
    if target.lower() in {"today", "day_today"}:
        return _day_today()
    if target.lower() in {"latest", "day_latest"}:
        return "day_latest"
    if not target.startswith("day_"):
        return f"day_{target}"
    return target


def _iter_day_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("day_")])


def _winner_key(path: Path) -> Tuple[int, float]:
    st = path.stat()
    return (int(st.st_size), float(st.st_mtime))


def _pick_winner(a: Path, b: Path) -> Path:
    """Return the winner according to: largest size, then newest mtime."""
    a_key = _winner_key(a)
    b_key = _winner_key(b)
    return a if a_key >= b_key else b


def aggregate_state_root(
    *,
    state_root: Path,
    target_dirname: str,
    enabled: bool = True,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Aggregate all `day_*` folders under `state_root` into `state_root/target_dirname`.
    Returns counts for logging/testing.
    """
    counts = {
        "roots_missing": 0,
        "day_dirs_seen": 0,
        "files_considered": 0,
        "files_moved": 0,
        "files_replaced": 0,
        "files_deleted": 0,
        "dirs_removed": 0,
    }

    if not enabled:
        return counts

    if not state_root.exists():
        counts["roots_missing"] += 1
        return counts

    target_dir = state_root / target_dirname
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    day_dirs = list(_iter_day_dirs(state_root))
    counts["day_dirs_seen"] = len(day_dirs)
    if verbose:
        print(f"[aggregate] state_root={state_root}")
        print(f"[aggregate] target_dir={target_dir}")
        print(f"[aggregate] day_dirs={len(day_dirs)}")

    for day_dir in day_dirs:
        if day_dir == target_dir:
            continue
        if day_dir.name == target_dirname:
            continue

        for src in list(day_dir.iterdir()):
            if not src.is_file():
                continue
            counts["files_considered"] += 1
            dst = target_dir / src.name

            if not dst.exists():
                if verbose:
                    print(f"  move: {src} -> {dst}")
                if not dry_run:
                    shutil.move(str(src), str(dst))
                counts["files_moved"] += 1
                continue

            winner = _pick_winner(src, dst)
            if winner == src:
                if verbose:
                    print(f"  replace (src wins): {src} -> {dst} (delete dst)")
                if not dry_run:
                    try:
                        dst.unlink()
                    except FileNotFoundError:
                        pass
                    shutil.move(str(src), str(dst))
                counts["files_replaced"] += 1
            else:
                if verbose:
                    print(f"  delete (dst wins): {src}")
                if not dry_run:
                    try:
                        src.unlink()
                    except FileNotFoundError:
                        pass
                counts["files_deleted"] += 1

        # Remove empty day directory if possible
        try:
            if day_dir.exists() and day_dir != target_dir and not any(day_dir.iterdir()):
                if verbose:
                    print(f"  rmdir: {day_dir}")
                if not dry_run:
                    day_dir.rmdir()
                counts["dirs_removed"] += 1
        except OSError:
            # Not empty or cannot remove: ignore (safe)
            pass

    return counts


def _rebuild_registry_section(state_root: Path) -> Dict[str, str]:
    """
    Build a filename -> absolute path mapping for all files under day_* dirs.
    If duplicates exist, keep the winner by (size, mtime).
    """
    best: Dict[str, Path] = {}
    for day_dir in _iter_day_dirs(state_root):
        for p in day_dir.iterdir():
            if not p.is_file():
                continue
            prev = best.get(p.name)
            if prev is None:
                best[p.name] = p
                continue
            best[p.name] = _pick_winner(prev, p)
    return {name: str(path.resolve()) for name, path in best.items()}


def update_local_backup_registry(
    *,
    config_dir: Path,
    framework_state_root: Path,
    model_state_root: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    reg_path = config_dir / "local_backup_registry.json"
    if not reg_path.exists():
        if verbose:
            print(f"[registry] missing: {reg_path}")
        return False

    try:
        registry = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception:
        registry = {}

    registry["framework_state"] = _rebuild_registry_section(framework_state_root)
    registry["model_state"] = _rebuild_registry_section(model_state_root)

    if verbose:
        print(f"[registry] framework_state entries: {len(registry['framework_state'])}")
        print(f"[registry] model_state entries: {len(registry['model_state'])}")

    if not dry_run:
        reg_path.write_text(json.dumps(registry), encoding="utf-8")
    return True


def _normalize_drive_day(target: str) -> str:
    """Normalize a target day folder name for Drive aggregation."""
    return _normalize_target(target)


def _drive_list_all(mgr: Any, *, q: str, fields: str, page_size: int = 1000) -> list[dict]:
    """List Drive files/folders for a query, handling pagination."""
    if not getattr(mgr, "remote_available", False) or not getattr(mgr, "drive", None):
        return []

    results: list[dict] = []
    page_token = None
    while True:
        resp = mgr._retry_drive(
            lambda: mgr.drive.files().list(
                q=q,
                fields=f"nextPageToken,files({fields})",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
                pageSize=page_size,
                pageToken=page_token,
            ).execute()
        )
        results.extend(resp.get("files", []) if isinstance(resp, dict) else [])
        page_token = resp.get("nextPageToken") if isinstance(resp, dict) else None
        if not page_token:
            break
    return results


def _drive_get_child_count(mgr: Any, folder_id: str) -> int:
    """Return 0 if empty, 1 if non-empty, -1 if unknown (best-effort).

    IMPORTANT: This intentionally does NOT count all children.
    """
    if not folder_id:
        return 0
    try:
        resp = mgr._retry_drive(
            lambda: mgr.drive.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
                pageSize=1,
            ).execute()
        )
        files = resp.get("files", []) if isinstance(resp, dict) else []
        return 1 if files else 0
    except Exception:
        return -1


def _drive_try_delete(mgr: Any, file_id: str) -> bool:
    """Remove a Drive item from the active datalake view.

    IMPORTANT: Prefer moving to Trash (works under more permission sets and is
    safer). We keep the function name for backward compatibility with earlier
    logging, but the behavior is "trash" first.
    """
    if not file_id:
        return False

    # Prefer trashing (Drive often returns 404 for delete when lacking permanent
    # delete permissions, but will allow setting trashed=True).
    try:
        mgr._retry_drive(
            lambda: mgr.drive.files().update(
                fileId=file_id,
                body={"trashed": True},
                supportsAllDrives=True,
                fields="id,trashed",
            ).execute()
        )
        return True
    except Exception:
        pass

    # Fallback: attempt permanent delete if trashing failed.
    try:
        mgr._retry_drive(lambda: mgr.drive.files().delete(fileId=file_id, supportsAllDrives=True).execute())
        return True
    except Exception:
        return False


def _drive_try_move_to_folder(mgr: Any, *, file_id: str, add_parent: str, remove_parents: list[str]) -> bool:
    if not file_id or not add_parent:
        return False
    remove_parent_str = ",".join([p for p in remove_parents if p and p != add_parent])
    try:
        mgr._retry_drive(
            lambda: mgr.drive.files().update(
                fileId=file_id,
                addParents=add_parent,
                removeParents=remove_parent_str,
                supportsAllDrives=True,
                fields="id,parents",
            ).execute()
        )
        return True
    except Exception:
        return False


def aggregate_drive_component(
    *,
    mgr: Any,
    component: str,
    target_day: str,
    execute: bool,
    verbose: bool,
    progress_every: int = 250,
) -> dict[str, int]:
    """Aggregate Drive day_* folders for a component into target_day (size wins, then modifiedTime)."""
    counts: dict[str, int] = {
        "day_folders_seen": 0,
        "files_seen": 0,
        "unique_names": 0,
        "duplicates_seen": 0,
        "best_needs_move": 0,
        "best_moved": 0,
        "duplicates_deleted": 0,
        "day_folders_deleted": 0,
        "index_uploaded": 0,
    }

    if not getattr(mgr, "remote_available", False) or not getattr(mgr, "drive", None):
        return counts
    if getattr(mgr, "in_share_drive", False):
        # Safety: this tool is intended to operate via Drive API (non-mirror workspace).
        # We still allow scanning, but execution is blocked.
        if execute:
            raise RuntimeError("Refusing to modify Drive while running inside the Drive-mirror workspace (in_share_drive=True).")

    data_lake_id = mgr._ensure_drive_folder("quantum_data_lake", mgr.drive_folder_id)
    if not data_lake_id:
        return counts
    comp_id = mgr._ensure_drive_folder(component, data_lake_id)
    if not comp_id:
        return counts

    target_day = _normalize_drive_day(target_day)
    target_day_id = mgr._ensure_drive_folder(target_day, comp_id)
    if not target_day_id:
        return counts

    # List day folders
    folders = _drive_list_all(
        mgr,
        q=(
            f"'{comp_id}' in parents and trashed=false and "
            "mimeType='application/vnd.google-apps.folder'"
        ),
        fields="id,name",
        page_size=1000,
    )
    day_folders = [f for f in folders if str(f.get("name", "")).startswith("day_") and f.get("id")]
    day_folders.sort(key=lambda f: str(f.get("name", "")))
    counts["day_folders_seen"] = len(day_folders)

    day_folder_ids = {f["id"] for f in day_folders if f.get("id")}

    # Track best (winner) per filename, and losers to delete.
    best: dict[str, dict[str, Any]] = {}
    losers: list[str] = []
    seen_ids: set[str] = set()

    def _entry_key(e: dict[str, Any]) -> tuple[int, str]:
        return (int(e.get("size", 0) or 0), str(e.get("modifiedTime", "") or ""))

    # Scan all day folders
    for folder in day_folders:
        day_name = str(folder.get("name"))
        day_id = str(folder.get("id"))
        if verbose:
            print(f"[drive-scan] {component}/{day_name}")
        files = _drive_list_all(
            mgr,
            q=f"'{day_id}' in parents and trashed=false",
            fields="id,name,size,modifiedTime,mimeType,parents",
            page_size=1000,
        )
        for f in files:
            if not f.get("id") or not f.get("name"):
                continue
            if f.get("mimeType") == "application/vnd.google-apps.folder":
                continue

            # Safety: the same Drive file can appear in multiple folders (multiple parents).
            # Never treat repeated fileIds as duplicates.
            fid = str(f.get("id"))
            if fid in seen_ids:
                continue
            seen_ids.add(fid)

            counts["files_seen"] += 1
            name = str(f["name"])
            entry = {
                "id": fid,
                "name": name,
                "size": int(f.get("size") or 0),
                "modifiedTime": str(f.get("modifiedTime", "") or ""),
                "parents": list(f.get("parents") or []),
                "day": day_name,
                "day_id": day_id,
            }

            prev = best.get(name)
            if prev is None:
                best[name] = entry
            else:
                if _entry_key(entry) > _entry_key(prev):
                    losers.append(prev["id"])
                    best[name] = entry
                else:
                    losers.append(entry["id"])

    counts["unique_names"] = len(best)
    counts["duplicates_seen"] = max(0, counts["files_seen"] - counts["unique_names"])

    # Plan counts
    for e in best.values():
        if target_day_id not in set(e.get("parents") or []):
            counts["best_needs_move"] += 1

    if not execute:
        return counts

    # Execute: move winners to target, then delete losers, then remove empty old day folders.
    moved = 0
    for idx, e in enumerate(best.values(), start=1):
        parents = list(e.get("parents") or [])
        if target_day_id in parents and set(parents).issubset({target_day_id} | (day_folder_ids - {target_day_id})):
            # Even if already in target, we may still want to remove it from other day folders.
            pass

        remove_parents = [p for p in parents if p in day_folder_ids and p != target_day_id]
        if target_day_id not in parents or remove_parents:
            ok = _drive_try_move_to_folder(
                mgr,
                file_id=e["id"],
                add_parent=target_day_id,
                remove_parents=remove_parents,
            )
            if ok:
                moved += 1
        if idx % progress_every == 0 or idx == len(best):
            print(f"[drive-move] {component}: {idx}/{len(best)} moved_ok={moved}")

    counts["best_moved"] = moved

    deleted = 0
    for idx, file_id in enumerate(losers, start=1):
        if _drive_try_delete(mgr, file_id):
            deleted += 1
        if idx % progress_every == 0 or idx == len(losers):
            print(f"[drive-trash] {component}: {idx}/{len(losers)} trashed_ok={deleted}")
    counts["duplicates_deleted"] = deleted

    # Delete empty old day folders (keep target)
    folders_deleted = 0
    for folder in day_folders:
        fid = str(folder.get("id"))
        name = str(folder.get("name"))
        if fid == target_day_id:
            continue
        child_status = _drive_get_child_count(mgr, fid)
        if child_status != 0:
            continue
        if _drive_try_delete(mgr, fid):
            folders_deleted += 1
            if verbose:
                print(f"[drive-rmdir] trashed empty folder {component}/{name}")
    counts["day_folders_deleted"] = folders_deleted

    # Upload an updated state_index.json reflecting the post-clean structure.
    try:
        index = {name: {"drive_id": entry["id"], "day": target_day} for name, entry in best.items()}
        ok = mgr._upload_state_index_to_drive(component, index)
        counts["index_uploaded"] = 1 if ok else 0
    except Exception:
        counts["index_uploaded"] = 0

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("daqr/config"),
        help="Framework config dir containing local_backup_registry.json.",
    )
    parser.add_argument(
        "--framework-state-root",
        type=Path,
        default=Path("daqr/config/framework_state"),
        help="Root containing framework state day_* folders.",
    )
    parser.add_argument(
        "--model-state-root",
        type=Path,
        default=Path("daqr/config/model_state"),
        help="Root containing model state day_* folders.",
    )
    parser.add_argument(
        "--target",
        default="today",
        help="Target day folder name: today | latest | day_YYYYMMDD | YYYYMMDD | custom (auto-prefixed with day_).",
    )
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["framework_state", "model_state"],
        default=["framework_state", "model_state"],
        help="Which components to aggregate.",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Also aggregate Google Drive quantum_data_lake/<component>/day_* into the target day folder.",
    )
    parser.add_argument(
        "--remote-execute",
        action="store_true",
        help="Apply Drive changes (move winners to target day, delete smaller duplicates, remove empty old day folders, update state_index.json).",
    )
    parser.add_argument("--enabled", action="store_true", default=True, help="Enable aggregation (default).")
    parser.add_argument("--disabled", action="store_true", help="No-op (do not aggregate).")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files.")
    parser.add_argument("--no-registry-update", action="store_true", help="Do not rebuild local_backup_registry.json.")
    parser.add_argument("--verbose", action="store_true", help="Verbose per-file logging.")
    args = parser.parse_args()

    enabled = bool(args.enabled) and not bool(args.disabled)
    target = _normalize_target(args.target)

    print(f"[state-aggregate] enabled={enabled} dry_run={args.dry_run} target={target}")

    fw_counts = {}
    ms_counts = {}
    if "framework_state" in args.components:
        fw_counts = aggregate_state_root(
            state_root=args.framework_state_root,
            target_dirname=target,
            enabled=enabled,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print(f"[state-aggregate] framework_state: {fw_counts}")
    else:
        print("[state-aggregate] framework_state: skipped")

    if "model_state" in args.components:
        ms_counts = aggregate_state_root(
            state_root=args.model_state_root,
            target_dirname=target,
            enabled=enabled,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print(f"[state-aggregate] model_state:     {ms_counts}")
    else:
        print("[state-aggregate] model_state: skipped")

    if enabled and not args.no_registry_update and not args.dry_run:
        ok = update_local_backup_registry(
            config_dir=args.config_dir,
            framework_state_root=args.framework_state_root,
            model_state_root=args.model_state_root,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print(f"[state-aggregate] registry_update={ok}")
    else:
        print("[state-aggregate] registry_update=skipped")

    if args.remote:
        # Import only when requested (keeps local-only behavior lightweight).
        from daqr.config.local_backup_manager import create_pattern_drive_manager

        mgr = create_pattern_drive_manager(None, args.config_dir, verbose=args.verbose)
        if not getattr(mgr, "remote_available", False) or not getattr(mgr, "drive", None):
            raise RuntimeError("Drive is not available (credentials or permissions missing).")

        print(f"[state-aggregate] remote_scan=true remote_execute={args.remote_execute} target={target}")
        if "framework_state" in args.components:
            fw_remote = aggregate_drive_component(
                mgr=mgr,
                component="framework_state",
                target_day=target,
                execute=bool(args.remote_execute),
                verbose=args.verbose,
            )
            print(f"[state-aggregate] drive/framework_state: {fw_remote}")
        if "model_state" in args.components:
            ms_remote = aggregate_drive_component(
                mgr=mgr,
                component="model_state",
                target_day=target,
                execute=bool(args.remote_execute),
                verbose=args.verbose,
            )
            print(f"[state-aggregate] drive/model_state:     {ms_remote}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

