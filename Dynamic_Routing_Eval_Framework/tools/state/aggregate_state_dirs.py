#!/usr/bin/env python3
"""
Aggregate `day_*` state subdirectories into a single target `day_*` folder.

Purpose
-------
This is a SAFE, LOCAL-ONLY tool intended to stabilize resume/scanning by
reducing state sprawl across many `day_YYYYMMDD/` folders.

Key policy (matches your established cleanup logic)
---------------------------------------------------
If duplicate filenames exist across days, keep the LARGEST file (size wins).
If sizes tie, keep the NEWEST by modification time.

This tool does NOT:
  - rename files,
  - touch datalake/Drive paths,
  - import heavy dependencies (pandas/cloudpickle),
  - parse or modify pickled objects.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, Tuple


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
    parser.add_argument("--enabled", action="store_true", default=True, help="Enable aggregation (default).")
    parser.add_argument("--disabled", action="store_true", help="No-op (do not aggregate).")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files.")
    parser.add_argument("--no-registry-update", action="store_true", help="Do not rebuild local_backup_registry.json.")
    parser.add_argument("--verbose", action="store_true", help="Verbose per-file logging.")
    args = parser.parse_args()

    enabled = bool(args.enabled) and not bool(args.disabled)
    target = _normalize_target(args.target)

    print(f"[state-aggregate] enabled={enabled} dry_run={args.dry_run} target={target}")

    fw_counts = aggregate_state_root(
        state_root=args.framework_state_root,
        target_dirname=target,
        enabled=enabled,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    ms_counts = aggregate_state_root(
        state_root=args.model_state_root,
        target_dirname=target,
        enabled=enabled,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    print(f"[state-aggregate] framework_state: {fw_counts}")
    print(f"[state-aggregate] model_state:     {ms_counts}")

    if enabled and not args.no_registry_update:
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

