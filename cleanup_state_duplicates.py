import os, json
from pathlib import Path
from datetime import datetime
import shutil

DATALAKE_ROOT = Path("/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake")

STATE_ROOTS_LOCAL = [
    Path("Dynamic_Routing_Eval_Framework/daqr/config/framework_state"),
    Path("Dynamic_Routing_Eval_Framework/daqr/config/model_state")
]

STATE_ROOTS_DATALAKE = [
    DATALAKE_ROOT / "framework_state",
    DATALAKE_ROOT / "model_state"
]

ALL_STATE_ROOTS = STATE_ROOTS_LOCAL + STATE_ROOTS_DATALAKE

# -------------------------------------------------------------
# HELPER: Scan directory and collect all files by filename
# -------------------------------------------------------------
def find_all_files(root_dir):
    """
    Return: {filename: [(path, size)]} across ALL date dirs.
    """
    file_map = {}
    root_dir = Path(root_dir)

    if not root_dir.exists():
        print(f"[WARN] Missing: {root_dir}")
        return file_map

    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            full = Path(dirpath) / f
            size = full.stat().st_size
            file_map.setdefault(f, []).append((full, size))

    return file_map

# -------------------------------------------------------------
# 1) DEDUPLICATE ACROSS ALL DATES (keep largest)
# -------------------------------------------------------------
def cleanup_across_dates():
    for root in STATE_ROOTS:
        print(f"\n\n====================")
        print(f" Checking: {root}")
        print(f"====================")

        file_map = find_all_files(root)
        removed = 0

        for fname, versions in file_map.items():
            if len(versions) <= 1:
                continue

            print(f"\n[!] Duplicate: {fname}")
            for path, size in versions:
                print(f"   - {path.name} ({size} bytes)")

            # Keep the largest copy
            keep_path, keep_size = max(versions, key=lambda x: x[1])
            print(f"   → KEEPING: {keep_path.name} ({keep_size} bytes)")

            for path, size in versions:
                if path != keep_path:
                    print(f"     ✖ Removing: {path.name} ({size} bytes)")
                    try:
                        path.unlink()
                        removed += 1
                    except Exception as e:
                        print(f"     ERROR removing {path}: {e}")

        print(f"[✓] Removed {removed} duplicates in {root}")

        # Remove empty date directories
        empty = 0
        for date_dir in root.iterdir():
            if date_dir.is_dir() and not any(date_dir.iterdir()):
                print(f"   → Removing empty dir: {date_dir}")
                date_dir.rmdir()
                empty += 1

        print(f"[✓] Removed {empty} empty directories in {root}")


def consolidate_to_today(root: Path):
    root = Path(root)

    if not root.exists():
        print(f"[SKIP] Missing path → {root}")
        return

    today = datetime.now().strftime("%Y%m%d")
    today_dir_name = f"day_{today}"
    target_dir = root / today_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n\n========== CONSOLIDATION: {root} ==========")
    print(f"Target date directory: {target_dir}")

    moved = 0
    removed_dirs = 0

    for date_dir in root.iterdir():
        if not date_dir.is_dir():
            continue

        # skip the proper target directory
        if date_dir.name == today_dir_name:
            continue

        # move files inside any older folder
        for f in date_dir.iterdir():
            if f.is_file():
                dest = target_dir / f.name
                print(f" → Moving {f.name} → {dest}")
                shutil.move(str(f), str(dest))
                moved += 1

        # try removing the empty old directory
        try:
            date_dir.rmdir()
            print(f"   Removed old directory: {date_dir}")
            removed_dirs += 1
        except OSError:
            pass

    print(f"[✓] Consolidation finished for {root}: moved {moved} files, removed {removed_dirs} directories.")


# -------------------------------------------------------------
# 3) OPTIONAL: SINGLE-ROOT DEDUPER (DETAILED VIEW)
# -------------------------------------------------------------
def dedupe_state_dir(root_dir):
    """
    Detailed version: prints file counts before and after cleanup.
    """
    root = Path(root_dir)
    file_map = {}

    print(f"\n📂 SCANNING: {root_dir}")
    print("-" * 60)

    for date_dir in root.iterdir():
        if not date_dir.is_dir():
            continue
        for file_path in date_dir.iterdir():
            if file_path.is_file():
                size = file_path.stat().st_size
                file_map.setdefault(file_path.name, []).append((file_path, size))

    # Summary before cleanup
    print("\n🔍 BEFORE CLEANUP")
    for fname, versions in file_map.items():
        print(f"{fname}: {len(versions)} versions")

    # Dedupe
    for fname, versions in file_map.items():
        if len(versions) <= 1:
            continue

        keep_path, keep_size = max(versions, key=lambda x: x[1])
        print(f"\n[KEEP] {fname} (size {keep_size})")

        for path, size in versions:
            if path != keep_path:
                print(f"   ✖ Removing (size {size})")
                path.unlink()

    # Summary after cleanup
    print("\n✅ AFTER CLEANUP")
    final = {}
    for date_dir in root.iterdir():
        if date_dir.is_dir():
            for f in date_dir.iterdir():
                if f.is_file():
                    final.setdefault(f.name, []).append(f)

    for fname, paths in final.items():
        print(f"{fname}: {len(paths)}")

    print("\n🎉 DONE!\n")


def rebuild_registry(registry_path, state_roots, is_metadata=False):
    """
    Update registry entries in the structure:
        component → day_X → filename → path

    ONE LOOP ONLY.
    try/except only for missing component/day.
    Uses dt_comp update pattern exactly as requested.
    """

    reg_path = Path(registry_path)
    if not reg_path.exists():
        print(f"[INFO] Registry not found, skipping update: {registry_path}")
        return

    print(f"\n[UPDATE] Updating registry: {registry_path}")

    # Load existing registry
    with open(reg_path, "r") as f:
        registry = json.load(f)

    corrected = 0
    added = 0

    # SINGLE LOOP: iterate real files on disk
    for root in state_roots:
        root = Path(root)
        if not root.exists():
            continue

        component = root.name  # "framework_state" / "model_state"

        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"):
                continue

            date_key = date_dir.name

            for f in date_dir.iterdir():
                if not f.is_file():
                    continue

                abs_path = str(f.resolve())

                # ------------------------------------------------------------
                # UPDATE using your dt_comp approach
                # ------------------------------------------------------------
                try:
                    registry[component][date_key][f.name] = abs_path
                    corrected += 1
                except Exception:
                    if not is_metadata: continue
                    registry[component].get(date_key, {}).update({f.name: abs_path})
                    added += 1

    # Save updated registry
    with open(reg_path, "w") as f:
        json.dump(registry, f, indent=4)

    print(f"[✓] Registry updated: {corrected} corrected")
    print(f"[✓] Registry updated: {added} added (metadata only)")



def cleanup_across_dates_single(root):
    root = Path(root)

    if not root.exists():
        print(f"[SKIP] Missing path → {root}")
        return

    print(f"[CLEAN] {root}")

    file_map = find_all_files(root)
    removed = 0

    for fname, versions in file_map.items():
        if len(versions) <= 1:
            continue

        # choose largest
        keep, keep_size = max(versions, key=lambda x: x[1])

        for path, size in versions:
            if path != keep:
                try:
                    path.unlink()
                    removed += 1
                except:
                    pass

    # remove empty dirs
    for d in root.iterdir():
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    print(f"[✓] {root}: removed {removed} duplicates")




# -------------------------------------------------------------
# 4) MASTER FUNCTION
# -------------------------------------------------------------
def cleanup_and_consolidate():
    print("\n========== STARTING CLEANUP ==========")

    # LOCAL + DATALAKE
    for root in ALL_STATE_ROOTS:
        print(f"\n--- Cleaning: {root} ---")
        cleanup_across_dates_single(root)

    print("\n========== CONSOLIDATING ==========")

    for root in ALL_STATE_ROOTS:
        consolidate_to_today(root)

    print("\n========== UPDATING REGISTRIES ==========")

    # Local registry
    rebuild_registry(
        registry_path="Dynamic_Routing_Eval_Framework/daqr/config/local_backup_registry.json",
        state_roots=STATE_ROOTS_LOCAL
    )

    # Drive registry inside project folder
    rebuild_registry(
        registry_path="Dynamic_Routing_Eval_Framework/daqr/config/drive_backup_registry.json",
        state_roots=STATE_ROOTS_LOCAL
    )

    # Datalake registry
    rebuild_registry(
        registry_path=DATALAKE_ROOT / "backup_registry.json",
        state_roots=STATE_ROOTS_DATALAKE
    )

    print("\n========== DONE ==========\n")




# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
if __name__ == "__main__":
    cleanup_and_consolidate()
