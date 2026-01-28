import os, json
from pathlib import Path
from datetime import datetime
import shutil
import pickle
import cloudpickle
import ast
import re
import pandas as pd


class Dummy:
    def __init__(self, *args, **kwargs):
        pass


class SafeUnpickler(pickle.Unpickler):
    """Custom Unpickler that replaces missing module references with Dummy()."""
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except Exception:
            # print(f"\t → Replacing missing: {module}.{name}")
            return Dummy




# Get the script's directory
SCRIPT_DIR = Path(__file__).parent.resolve()


# Build absolute paths
PROJECT_ROOT = SCRIPT_DIR / "Dynamic_Routing_Eval_Framework"


DATALAKE_ROOT = Path("/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake")


STATE_ROOTS_LOCAL = [
    PROJECT_ROOT / "daqr" / "config" / "framework_state",
    PROJECT_ROOT / "daqr" / "config" / "model_state",
]


STATE_ROOTS_DATALAKE = [
    DATALAKE_ROOT / "framework_state",
    DATALAKE_ROOT / "model_state",
]


ALL_STATE_ROOTS = STATE_ROOTS_LOCAL + STATE_ROOTS_DATALAKE


# Valid model classes from your config
MODEL_MODES = {
    'Oracle': 'base',
    'GNeuralUCB': 'neural',
    'NeuralUCB': 'neural',
    'EXPUCB': 'exp3',
    'EXPNeuralUCB': 'hybrid',
    'CPursuitNeuralUCB': 'neural',
    'iCPursuitNeuralUCB': 'neural',
    'CEpsilonGreedy': 'hybrid',
    'CEXP4': 'hybrid',
    'CPursuit': 'hybrid',
    'CEpochGreedy': 'hybrid',
    'CThompsonSampling': 'hybrid',
    'CKernelUCB': 'hybrid',
    'iCEpsilonGreedy': 'hybrid',
    'iCEXP4': 'hybrid',
    'iCPursuit': 'hybrid',
    'iCEpochGreedy': 'hybrid',
    'iCThompsonSampling': 'hybrid',
    'iCKernelUCB': 'hybrid',
    'LinUCB': 'neural',
    'CEXPNeuralUCB': 'hybrid'
}


# Debug output
print(f"Script dir: {SCRIPT_DIR}")
print(f"Project root: {PROJECT_ROOT}")
print(f"\nState roots:")
for root in ALL_STATE_ROOTS:
    exists = "✅" if root.exists() else "❌"
    print(f"  {exists} {root}")




# ============================================================
# HELPER — FIND ALL FILES
# ============================================================


def find_all_files(root_dir):
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



def tag_multirun_evaluators_from_filename_and_object(state_roots):
    """
    TEMP FIX for MultiRunEvaluator files.


    Uses BOTH:
      • capacity from filename
      • capacity from saved object


    Logic:
      scale = capacity_from_name / base_frames_from_name


      Tb → object_capacity == capacity_from_name
      T  → object_capacity != capacity_from_name


    Final tag:   MultiRunEvaluator_... → MultiRunEvaluator_..._S{scale}{T|Tb}.pkl
    """


    print("\n[RENAME] Tagging MultiRunEvaluator files (filename + object capacity)...")


    renamed = 0
    skipped = 0
    failed  = 0


    for root in state_roots:
        root = Path(root)
        if not root.exists():
            continue


        # Only touch framework_state dirs
        if "framework_state" not in str(root):
            continue


        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"):
                continue


            for f in date_dir.iterdir():
                if not f.is_file() or not f.name.endswith(".pkl"):
                    continue
                if not f.name.startswith("MultiRunEvaluator_"):
                    continue


                print(f"\n   Processing: {f.name}")
                stem = f.stem
                # stem = re.sub(r"_S[\d_]+(T|Tb)$", '', stem) # for emergency
                # Already tagged? (_S…T or _S…Tb at the end)
                if re.search(r"_S[\d_]+(T|Tb)$", stem):
                    print("      ✓ Already tagged")
                    skipped += 1
                    continue


                try:
                    # ---------------------------------------------
                    # Parse capacity + base_frames from filename
                    # ---------------------------------------------
                    # Example:
                    #   MultiRunEvaluator_8000-Random_Adversarial_Markov-4000_2000_10
                    core = stem.replace("MultiRunEvaluator_", "")
                    parts = core.split("-")


                    if len(parts) < 3:
                        print("      ⚠️ Unexpected name format, skipping")
                        skipped += 1
                        continue


                    capacity_from_name = int(parts[0])
                    last_section       = parts[-1]      # e.g. "4000_2000_10"
                    base_frames        = int(last_section.split("_")[0])


                    # ---------------------------------------------
                    # Compute SCALE from FILENAME (not object)
                    # ---------------------------------------------
                    scale_float = capacity_from_name / base_frames


                    if abs(scale_float - 1.0) < 1e-9:
                        scale_str = "S1"
                    elif abs(scale_float - 1.5) < 1e-9:
                        scale_str = "S1_5"
                    elif abs(scale_float - 2.0) < 1e-9:
                        scale_str = "S2"
                    else:
                        scale_str = "S" + str(scale_float).replace(".", "_")


                    # ---------------------------------------------
                    # Load object to get *actual* capacity
                    # ---------------------------------------------
                    data = _load_any_pickle(f)
                    if data is None:
                        print("      ❌ Could not load object; skipping")
                        failed += 1
                        continue


                    # saved evaluator is a dict (from your save())
                    if isinstance(data, dict):
                        object_capacity = data.get("capacity", None)
                    else:
                        # Fallback: attribute on object (if for some reason we saved the instance)
                        object_capacity = getattr(data, "capacity", None)


                    if object_capacity is None:
                        print("      ⚠️ No capacity field in loaded data; using filename only (assume Tb)")
                        object_capacity = capacity_from_name


                    # ---------------------------------------------
                    # Decide T vs Tb using YOUR rule
                    # ---------------------------------------------
                    if object_capacity == capacity_from_name:
                        T_type = "Tb"   # never changed → baseline
                    else:
                        T_type = "T"    # changed → scaled/runtime altered


                    print(f"      → capacity_from_name: {capacity_from_name}")
                    print(f"      → object_capacity:    {object_capacity}")
                    print(f"      → scale:              {scale_float} → {scale_str}")
                    print(f"      → T-type:             {T_type}")


                    # ---------------------------------------------
                    # Build new filename
                    # ---------------------------------------------
                    new_stem = f"{stem}_{scale_str}{T_type}"
                    new_name = new_stem + ".pkl"
                    new_path = date_dir / new_name


                    print(f"      → New filename: {new_name}")
                    f.rename(new_path)
                    renamed += 1


                except Exception as e:
                    print(f"      ❌ Failed: {e}")
                    failed += 1


    print("\n[✓] MultiRunEvaluator tagging (filename + object) complete:")
    print(f"    Renamed: {renamed}")
    print(f"    Skipped: {skipped}")
    print(f"    Failed:  {failed}")



# ============================================================
# DEDUPLICATION (LARGEST VERSION WINS)
# ============================================================


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




# ============================================================
# RANDOM ALLOCATOR RENAMER
# ============================================================
def extract_and_rename_random_allocator_files(state_roots):
    print(f"\n[EXTRACT] Processing Random allocator files...")


    renamed = 0
    failed = 0
    skipped = 0


    pattern = r'_\(\d+_\d+_\d+_\d+\)'
    for root in state_roots:
        root = Path(root)
        if not root.exists():
            continue


        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"):
                continue
            
            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue
                
                # -----------------------------------------
                # CLEAN NEW NAME (IGNORE OLD BROKEN NAME)
                # -----------------------------------------
                base_name = f.stem
                new_base_name = base_name
                count = len(re.findall(pattern, base_name))


                if count == 1:
                    skipped += 1
                    continue
                # elif "Random" not in f.name:
                elif not re.search(r"\d+-Random", f.name):
                    skipped += 1
                    continue


                if count > 1: new_base_name = re.sub(r"[_-]*\([^)]*\)$", "", base_name)
                print("\tNEW BASE:", new_base_name)
                print(f"\n   Processing: {f.name}")
                if new_base_name == base_name:
                    try:
                        data = {}
                        try:
                            # 1) Try standard pickle
                            with open(f, "rb") as pf: data = pickle.load(pf)
                        except Exception as e:
                            try:
                                # 2) Try cloudpickle
                                with open(f, "rb") as pf: data = cloudpickle.load(pf)
                            except Exception as e2:
                                try:
                                    # 3) Try SafeUnpickler
                                    with open(f, "rb") as pf: data = SafeUnpickler(pf).load()
                                except Exception as e3:
                                    print(f"      ❌ Failed: {e3}")
                                    failed += 1
                                    continue


                        # Extract allocation tuple
                        qubit_alloc = data.get("key_attrs", {}).get("qubit_capacities", "")


                        if not qubit_alloc:
                            print("⚠️ No qubit_capacities found")
                            failed += 1
                            continue


                        # Serialize allocation as q8_10_8_9
                        alloc_str = "".join(str(v) for v in qubit_alloc)
                        alloc_str = re.sub(r',\s*', "_", alloc_str)
                        base_name = re.sub(r"[_-]*\([^)]*\)", "", base_name)


                        # Construct new proper filename
                        new_name = f"{base_name}_{alloc_str}.pkl"
                        new_path = date_dir / new_name


                        f.rename(new_path)
                        print(f"      ✅ Renamed → {new_name}")
                        print(f"      ✅ Renamed → {new_path}")


                        renamed += 1


                    except Exception as e:
                        print(f"      ❌ Failed: {e}")
                        failed += 1
                else:
                    print("FIXING ALLOCATION STRING")
                    new_path = date_dir / f"{new_base_name}.pkl"
                    print(f"      ✅ Renamed → {new_path}")



    print(f"\n[✓] Random allocator extraction complete:")
    print(f"    Renamed: {renamed}")
    print(f"    Failed: {failed}")
    print(f"    Skipped: {skipped}")


def restore_allocator_filenames_with_allocs(state_roots):
    print(f"\n[RESTORE] Fixing mistakenly renamed allocator files...")

    renamed = 0
    failed = 0
    skipped = 0

    for root in state_roots:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"): continue

            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue

                fname = f.name
                base_name = f.stem

                # ✅ Skip correct random allocator files (they should contain e.g., "6000-Random")
                if re.search(r"\d+-Random", fname): 
                    skipped += 1
                    continue

                # ✅ Skip if allocation already in filename (pattern: _(9_9_9_8) or similar)
                if not re.search(r"_\(\d+_\d+_\d+_\d+\)", base_name):
                    skipped += 1
                    continue

                print(f"\n   Processing: {fname}")
                # Try loading to extract key_attrs/qubit_capacities
                try:
                    new_base_name = re.sub(r"_\(\d+_\d+_\d+_\d+\)", "", base_name)
                    new_name = f"{new_base_name}.pkl"
                    new_path = f.parent / new_name

                    f.rename(new_path)
                    print(f"🔁 Renamed → {new_name}")
                    renamed += 1

                except Exception as e:
                    print(f"❌ Error on {f.name}: {e}")
                    failed += 1

    print(f"\n[✓] Restoration complete:")
    print(f"    Renamed: {renamed}")
    print(f"    Failed : {failed}")
    print(f"    Skipped: {skipped}")

# ============================================================
# CONSOLIDATION (MOVE ALL FILES → TODAY)
# ============================================================


def consolidate_to_today(root):
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


        if date_dir.name == today_dir_name:
            continue


        for f in date_dir.iterdir():
            if f.is_file():
                dest = target_dir / f.name
                shutil.move(str(f), str(dest))
                moved += 1


        try:
            date_dir.rmdir()
            removed_dirs += 1
        except OSError:
            pass


    print(f"[✓] Consolidation finished for {root}: moved {moved} files, removed {removed_dirs} directories.")




# ============================================================
# REGISTRY UPDATER — dt_comp style
# ============================================================
def rebuild_registry(registry_path, state_roots, is_metadata=False):
    reg_path = Path(registry_path)
    if not reg_path.exists():
        print(f"[INFO] Registry not found, skipping update: {registry_path}")
        return


    print(f"\n[UPDATE] Updating registry: {registry_path}")
    
    registry = {}
    if reg_path.exists():
        with open(reg_path, "r") as f: registry = json.load(f)


    added = 0
    corrected = 0
    print(f"[DEBUG] State roots passed in:")
    for p in state_roots: print(f"        - {p}  (exists={Path(p).exists()})")


    for root in state_roots:
        root = Path(root)


        if not root.exists():
            print(f"[SKIP] Root does not exist: {root}")
            continue


        component = root.name
        print(f"\n[DEBUG] COMPONENT: {component}")
        print(f"        root = {root}")


        # --- FIRST LOOP: day_xxxxx dirs ---
        for date_dir in root.iterdir():
            # print(f"[DEBUG]   Checking date_dir: {date_dir}")


            if not date_dir.is_dir():
                print(f"[SKIP]     Not a directory: {date_dir}")
                continue
            if not date_dir.name.startswith("day_"):
                print(f"[SKIP]     Not a day folder: {date_dir.name}")
                continue


            date_key = date_dir.name
            # print(f"[DEBUG]   → Day folder accepted: {date_key}")


            # --- SECOND LOOP: files ---
            has_files = False
            for f in date_dir.iterdir():
                # print(f"[DEBUG]       Inspect file/dir: {f}")

                if not f.is_file():
                    print(f"[SKIP]         Not a file: {f}")
                    continue

                has_files = True
                abs_path = str(f.resolve())

                # print(f"[DEBUG]         File accepted: {f.name}")
                # print(f"[DEBUG]         Abs path: {abs_path}")
                try:
                    registry[component][f.name] = abs_path
                    corrected += 1
                    # print(f"[CORRECTED]    Updated: {component}/{date_key}/{f.name}")
                except Exception:
                    if not is_metadata:
                        print(f"[SKIP]         Missing metadata structure (component/date), skipping...")
                        continue
                    if component not in registry: registry[component] = {}
                    registry[component].update({f.name: abs_path})
                    added += 1
                    print(f"[ADDED]        Inserted new entry: {component}/{date_key}/{f.name}")
            if not has_files: print(f"[DEBUG]     (No files found in {date_dir})")


    with open(reg_path, "w") as f: json.dump(registry, f, indent=4)
    print(f"[✓] Registry updated: {corrected} corrected, {added} added")


# ============================================================
# MODEL FILE RENAMER
# ============================================================


def rename_model_files(state_roots):
    """
    Rename model files to proper format: <ClassOfModel>(mode).pkl
    Special case: NeuralUCB_<Number>(mode).pkl
    """
    print(f"\n[RENAME] Processing model files...")    
    renamed = 0
    failed = 0
    skipped = 0
    
    for root in state_roots:
        root = Path(root)
        if not root.exists():
            continue


        if "framework_state" in str(root): continue
        print(root)
        
        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"): continue


            for f in date_dir.iterdir():
                if not f.is_file() or f.suffix != ".pkl": continue
                
                name = f.name
                if re.search(r'quantumrunner|multirunevaluator', name.lower()):
                    skipped += 1
                    continue
                
                print(f"\n   Checking: {name}")
                try:
                    parts=name.split("_")
                    class_name = parts[0]
                    model_name = re.sub(r'\(.*\)', '', class_name)


                    is_neuralucb = "NeuralUCB" == model_name
                    correct_name = f"{model_name}({MODEL_MODES[model_name]})" 
                    if is_neuralucb:
                        model_name = parts[0]
                        if MODEL_MODES[model_name] in parts[1]: continue
                        _class_name = "{}_{}".format(parts[0], re.sub(r'\(.*\)', '', parts[1]))
                        correct_name = f"{_class_name}({MODEL_MODES[model_name]})"
                        class_name = f"{parts[0]}_{parts[1]}"
        
                    if class_name == correct_name:
                        print(f"      ✓ Already correct: {name}")
                        skipped += 1
                        continue
                    
                    # Rename file
                    new_path = date_dir / name.replace(class_name, correct_name)
                    
                    # Handle collision (unlikely but possible)
                    if new_path.exists():
                        print(f"      ⚠️ Target already exists: {correct_name}")
                        # Keep larger file
                        old_size = f.stat().st_size
                        new_size = new_path.stat().st_size
                        if old_size > new_size:
                            new_path.unlink()
                            f.rename(new_path)
                            print(f"      ✅ Replaced with larger: {name} → {correct_name}")
                            print(f"      ✅ Replaced with larger: {correct_name} → {new_path}")
                        else:
                            f.unlink()
                            print(f"      ✅ Kept existing larger: {correct_name}")
                        renamed += 1
                    else:
                        f.rename(new_path)
                        print(f"      ✅ Renamed: {name} → {correct_name}")
                        print(f"      ✅ Replaced with larger: {correct_name} → {new_path}")
                        renamed += 1
                
                except Exception as e:
                    print(f"      ❌ Failed: {e}")
                    failed += 1
    
    print(f"\n[✓] Model file renaming complete:")
    print(f"    Renamed: {renamed}")
    print(f"    Failed: {failed}")
    print(f"    Skipped: {skipped}")



def rename_model_state_files(state_roots):
    print(f"\n[RENAME] Processing model_state files...")


    renamed = 0
    failed = 0
    skipped = 0


    for root in state_roots:
        root = Path(root)
        if not root.exists(): continue
        # ONLY process model_state directories
        if "model_state" not in str(root): continue


        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not date_dir.name.startswith("day_"): continue


            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue
                # EXCLUDE NeuralUCB files
                if "NeuralUCB" in f.name:
                    skipped += 1
                    continue


                print(f"\n   Processing: {f.name}")
                try:
                    data = {}
                    try:
                        # 1) Try standard pickle
                        with open(f, "rb") as pf: data = pickle.load(pf)
                    except Exception as e:
                        try:
                            # 2) Try cloudpickle
                            with open(f, "rb") as pf: data = cloudpickle.load(pf)
                        except Exception as e2:
                            try:
                                # 3) Try SafeUnpickler
                                with open(f, "rb") as pf: data = SafeUnpickler(pf).load()
                            except Exception as e3:
                                print(f"      ❌ Failed: {e3}")
                                failed += 1
                                continue


                    # Extract file_name from loaded data
                    correct_name = data.get("file_name", "")


                    if not correct_name:
                        print("      ⚠️ No file_name found in data")
                        failed += 1
                        continue


                    # Check if already correct
                    if f.name == correct_name:
                        print(f"      ✓ Already correct: {f.name}")
                        skipped += 1
                        continue


                    # Construct new path
                    new_path = date_dir / correct_name


                    f.rename(new_path)
                    print(f"      ✅ Renamed → {correct_name}")
                    print(f"      ✅ Renamed → {new_path}")


                    renamed += 1


                except Exception as e:
                    print(f"      ❌ Failed: {e}")
                    failed += 1


    print(f"\n[✓] Model state file renaming complete:")
    print(f"    Renamed: {renamed}")
    print(f"    Failed: {failed}")
    print(f"    Skipped: {skipped}")


# ============================================================
# NEW: FIX FLOAT FILENAMES (REGEX)
# ============================================================
def fix_float_filenames(state_roots):
    """
    Removes .0 from float-like numbers in filenames (e.g. 8000.0 -> 8000).
    Only affects numbers followed by a separator [-_].
    """
    print("\n[CLEANUP] Removing .0 float artifacts from filenames...")
    
    # Regex: Capture digits (\d+) followed by literal .0, then a separator [-_]
    # We will replace with just the digits and the separator.
    pattern = re.compile(r"(\d+)\.0([-_])")
    
    fixed_count = 0
    
    for root in state_roots:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir(): continue
            
            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue
                
                # Check for match
                if pattern.search(f.name):
                    # Replace: \1 is digits, \2 is separator
                    # new_name = pattern.sub(r"\1\2", f.name)
                    new_name = re.sub(r'\.\d+', '', f.name)
                    new_path = date_dir / new_name
                    
                    print(f"   Fixing: {f.name}")
                    print(f"       ->  {new_name}")
                    
                    try:
                        if new_path.exists(): new_path.unlink() # Overwrite/dedupe
                        f.rename(new_path)
                        fixed_count += 1
                    except Exception as e:
                        print(f"      ❌ Failed: {e}")

    print(f"[✓] Float artifacts fixed: {fixed_count}")

# ============================================================
# FIX DOUBLE DAY DIRECTORIES (day_day_ -> day_)
# ============================================================
def fix_double_day_directories(state_roots):
    print("\n[CLEANUP] Checking for 'day_day_' directory patterns...")
    from datetime import datetime, timedelta
    
    # Regex to find the bad pattern and capture the date part
    # Matches: day_day_20251124
    bad_pattern = re.compile(r"^day_day_(\d{8})$")
    
    fixed_count = 0
    
    for root in state_roots:
        root = Path(root)
        if not root.exists(): continue

        # Iterate over directories
        # We convert to list to avoid modifying the iterator while renaming
        for d in list(root.iterdir()):
            if not d.is_dir(): continue
            
            match = bad_pattern.match(d.name)
            if match:
                date_str = match.group(1)
                
                # 1. Determine the ideal clean name (day_YYYYMMDD)
                # Using regex sub as requested: replace "day_day_" with "day_"
                clean_name = re.sub(r"^day_day_", "day_", d.name)
                clean_path = root / clean_name
                
                final_new_path = clean_path
                
                # 2. Check for Conflict
                if clean_path.exists():
                    print(f"   ⚠️ Conflict: {clean_name} already exists.")
                    
                    # 3. Conflict Resolution: Subtract 10 days
                    try:
                        # Parse current date
                        dt = datetime.strptime(date_str, "%Y%m%d")
                        
                        # Subtract 10 days
                        new_dt = dt - timedelta(days=10)
                        new_date_str = new_dt.strftime("%Y%m%d")
                        
                        # Form new name
                        conflict_name = f"day_{new_date_str}"
                        final_new_path = root / conflict_name
                        
                        print(f"   💡 Resolving: Shifting date -10 days -> {conflict_name}")
                        
                        # Safety check: If THAT exists too, just append a suffix to be safe
                        if final_new_path.exists():
                             print(f"   ⚠️ Double Conflict on {conflict_name}! Appending '_restored'")
                             final_new_path = root / f"{conflict_name}_restored"
                             
                    except ValueError:
                        print(f"   ❌ Could not parse date {date_str}, skipping logic.")
                        continue

                # 4. Rename
                try:
                    print(f"   🔧 Renaming: {d.name}")
                    print(f"       ->       {final_new_path.name}")
                    d.rename(final_new_path)
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ Failed: {e}")

    print(f"[✓] 'day_day_' directories fixed: {fixed_count}")


def fix_double_tag_mess_robust():
    print("🔧 STARTING ROBUST DOUBLE TAG REPAIR (REGEX MODE)...")
    fixed = 0
    
    # 1. Regex for the BAD MIDDLE pattern (Float style: S1.5Tb)
    # Matches: _S followed by digits.digits followed by T or Tb, then an underscore
    # This marks the START of the garbage section.
    bad_middle_pattern = re.compile(r"(_S\d+\.\d+T[b]?_)")
    
    # 2. Regex for the VALID SUFFIX at the absolute end
    # Matches: Underscore, then S, digits_digits, T or Tb, optional digits, then .pkl
    # We capture just the tag part (e.g. S1_5T)
    # The '.*' before it is implicit in search, but we anchor to '$' to be sure it's the end.
    valid_suffix_pattern = re.compile(r"_(S\d+_\d+T[b]?\d?)\.pkl$")

    for root in ALL_STATE_ROOTS:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir(): continue
            
            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue
                
                # A. Do we have the Bad Middle?
                if bad_middle_pattern.search(f.name):
                    
                    # B. Do we have a Valid Suffix at the end?
                    suffix_match = valid_suffix_pattern.search(f.name)
                    if not suffix_match:
                        # It has the bad middle, but doesn't end with the clean tag we expect.
                        # Skip to avoid destroying unknown file formats.
                        continue
                    
                    valid_suffix = suffix_match.group(1) # e.g. "S1_5T"
                    
                    # C. Split the filename at the Bad Middle
                    # This gives us everything to the LEFT of the garbage.
                    parts = bad_middle_pattern.split(f.name)
                    clean_stem = parts[0] 
                    
                    # D. Reassemble
                    # Stem + "_" + Valid Suffix + ".pkl"
                    # Note: The stem typically doesn't end in _, and valid_suffix doesn't start with _.
                    # We add the underscore separator explicitly.
                    new_name = f"{clean_stem}_{valid_suffix}.pkl"
                    
                    # Safety: remove any accidental double underscores from the join
                    new_name = new_name.replace("__", "_")
                    
                    if new_name == f.name:
                        continue

                    print(f"🔧 FIXING: {f.name}")
                    print(f"   →     {new_name}")
                    
                    new_path = date_dir / new_name
                    
                    try:
                        if new_path.exists():
                            new_path.unlink() # Dedupe
                        f.rename(new_path)
                        fixed += 1
                    except Exception as e:
                        print(f"   ❌ ERROR: {e}")

    print(f"\n🔧 DONE. Fixed {fixed} files.")


# ============================================================
# MASTER FUNCTION
# ============================================================


def cleanup_and_consolidate():
    print("\n========== STARTING CLEANUP ==========")

    # fix_double_tag_mess_robust()

    # STEP 0a — Fix Directory Names (day_day_)
    # fix_double_day_directories(ALL_STATE_ROOTS)
    
    # STEP 0 — Fix float filenames first (so other regexes work on clean ints)
    fix_float_filenames(ALL_STATE_ROOTS)


    # STEP 1 — rename model files to proper format
    # rename_model_files(ALL_STATE_ROOTS)


    # # for emergency use only
    # # rename_model_state_files(ALL_STATE_ROOTS)


    # Tag MultiRunEvaluators with scale/T-type
    # tag_multirun_evaluators_from_filename_and_object(ALL_STATE_ROOTS) # for emergency
    # restore_allocator_filenames_with_allocs(ALL_STATE_ROOTS)


    # STEP 1 — rename Random allocator files
    # extract_and_rename_random_allocator_files(ALL_STATE_ROOTS)


    # STEP 2 — dedupe
    for root in ALL_STATE_ROOTS:
        print(f"\n--- Cleaning: {root} ---")
        cleanup_across_dates_single(root)


    # STEP 3 — consolidate
    for root in ALL_STATE_ROOTS:
        consolidate_to_today(root)


    # STEP 4 — rebuild registries (use absolute paths)
    rebuild_registry(
        PROJECT_ROOT / "daqr" / "config" / "local_backup_registry.json",
        STATE_ROOTS_LOCAL,
        is_metadata=True
    )


    rebuild_registry(
        PROJECT_ROOT / "daqr" / "config" / "drive_backup_registry.json",
        STATE_ROOTS_LOCAL,
        is_metadata=True
    )


    rebuild_registry(
        DATALAKE_ROOT / "backup_registry.json",
        STATE_ROOTS_DATALAKE,
        is_metadata=True
    )


    print("\n========== DONE ==========\n")




def collect_log_paths(root_dir: Path, keyword="quantum(CMABs)", ext=".txt") -> list[Path]:
    """
    Recursively collects log files using an explicit stack for directory traversal.
    Only includes files that contain the specified keyword and extension.

    Args:
        root_dir (Path): The root directory to scan.
        keyword (str): Keyword that must appear in filename.
        ext (str): File extension to match.

    Returns:
        List[Path]: Valid paths matching the filter.
    """
    stack = [root_dir.resolve()]
    valid_logs = []

    while stack:
        current = stack.pop()
        if current.is_dir():
            try:
                stack.extend(sorted(current.iterdir(), reverse=True))
            except PermissionError:
                continue  # skip protected dirs
        elif current.is_file() and re.search(keyword, current.name):
            if current.suffix == ext: 
                print(current.name)
                valid_logs.append(current)

    return sorted(valid_logs)

def parse_log_filename(filepath):
    pattern = (
        r"/(?P<exp_name>[^/]+)-"
        r"(?P<allocator>[^/]+)-"
        r"(?P<environment>[^/]+)-"
        r"(?P<attack_no>\d+)_attacks-"
        r"(?P<base_frame>\d+)_(?P<frames_step>\d+)-"
        r"(?P<runs_no>\d+)_runs-S"
        r"(?P<scale>\d+(\.\d+)?)(?P<capacity_type>[A-Za-z]+)_"
        r"(?P<date>\d+)_log\.txt"
    )
    match = re.search(pattern, filepath)
    return match.groupdict() if match else None


def parse_log_winner(line):   
    winner_pattern = (
        r".*EXP(?P<exp_num>\d+)\s+Winner:(?P<model>[\w\-\_]+)\s+\(Gap:(?P<gap>[\d\.]+)%\)"
        r"\s+\[Env:(?P<env>[^,]+),\s+Attack:(?P<attack>[\w\-\_]+)\s+X\s+Rate:(?P<rate>[\d\.]+),\s+"
        r"Frames:(?P<frames>\d+),\s+SCapacity=(?P<scapacity>[\d\.]+),\s+Alloc=(?P<alloc>[\w\-\_]+)\]"
    )
    winner = None
    match = re.search(winner_pattern, line)
    if match:
        match = match.groups()
        winner = {
            "exp": match[0],
            "model": match[1],
            "gap": float(match[2]),
            # "env": match[3],
            # "attack": match[4],
            "rate": float(match[5]),
            "frames": int(match[6]),
            "scapacity": float(match[7]),
            "alloc": match[8],
        }
    return winner


def parse_experiment_line(line):
    exp_pattern = r"EXP (\d+) (\w+)\s+: Reward=([\d.]+), Efficiency=([\d.]+)% \[Retries=(\d+), Failed=(\d+), < Threshold=(\d+), SCapacity=([\d.]+), Threshold=([\d.]+)\]"
    match = re.search(exp_pattern, line)
    if match:
        exp_num, model, reward, eff, retries, failed, misses, scap, threshold = match.groups()
        return {
            "num": int(exp_num),
            "model": model,
            "reward": float(reward),
            "eff": float(eff),
            "retries": int(retries),
            "failures": int(failed),
            "misses_thrs": int(misses),
            "scapacity": float(scap),
            "threshold": float(threshold),
        }
    return None

def parse_log_header(header_text):
    pattern = (
        r"Primary Environment:\s+(?P<primary_env>\w+)"
        r".*Models to Test:\s+(?P<models_to_test>\d+)"
        r".*•\s+(?P<scenario_1>\w+)\s+(?P<desc_1>[^\n]+)"
        r".*•\s+(?P<scenario_2>\w+)\s+(?P<desc_2>[^\n]+)"
        r".*•\s+(?P<scenario_3>\w+)\s+(?P<desc_3>[^\n]+)"
        r".*•\s+(?P<scenario_4>\w+)\s+(?P<desc_4>[^\n]+)"
        r".*•\s+(?P<scenario_5>\w+)\s+(?P<desc_5>[^\n]+)"
    )
    match = re.search(pattern, header_text, re.DOTALL)
    if match:
        return match.groupdict()
    else:
        return None

def generate_master_csv(tests_type, path="/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/"):
    print("\n========== GENERATING MASTER CSV ==========")
    if path is None: return

    LOG_DIR = Path(path + tests_type)
    LOG_FILES = collect_log_paths(LOG_DIR, keyword="_log", ext=".txt")

    all_data = []
    alloc_exps = {}
    scenarion_pattern = r"TESTING ENVIRONMENT SCENARIO:\s*"
    scap_pattern = r".*SCALED-CAPACITY:\s*(?P<scap>[\d\.]+)"
    exp_pattern = r"EXPERIMENT\s+(?P<exp_num>[\d]+):\s*((?P<frames>\d+)\s*frames)?"
    cap_scale_pattern = r".*\(CAPACITY:(?P<cap>[\d\.]+)\s+X\s+SCALE:(?P<scale>[\d\.]+)\)"
    exp_title_pattern = f"{exp_pattern}{scap_pattern}{cap_scale_pattern}"
    
    for log_file in LOG_FILES:
        expected_env_keys = 35
        scenarios_exps = {}
        scenario = None
        experiment = False
        scenario_cat = None
        scenario_env = None
        comprehensive = False

        if "combined" in log_file.name.lower(): continue
        with open(log_file, 'r') as f: content = f.read()

        # Step 1: Parse file-level metadata
        print(log_file.name)
        attributes = parse_log_filename(log_file.as_posix())
        if not attributes: 
            print(f"⚠️ Could not parse filename: {log_file.name}")
            continue

        scale = attributes["scale"]
        runs = attributes["runs_no"]
        base = attributes["base_frame"]
        env = attributes["environment"]
        step = attributes["frames_step"]
        attack_no = attributes["attack_no"]
        cap_type = attributes["capacity_type"]
        allocator = f"{re.sub(r"\(.*\)", "", attributes["allocator"])}_{runs}_{scale}"
        
        if allocator not in alloc_exps.keys(): 
            alloc_exps[allocator] = {"config":{}, "scenario":{}}
        
        alloc_exps[allocator]["config"] = {
            "scap": -1, "cap": -1, "scale": scale, "frames": -1, 
            "name": allocator, "runs": runs, "cap_type": cap_type, "log":"",
            "env": env, "step": step, "attack_no": attack_no, "base": base, "env_desc":""
        }

        log_file_lines = content.splitlines()        
        models = []
        env_attrs = {1:{}, 4:{}, 5:{"mode":""}, 6:{"models_no":0}, 10:{}, 11:{}, 12:{}, 13:{}, 14:{}}
        env_attrs.update({25:{}, 26:{}, 27:{}, 32:{}})

        for line_no, line in enumerate(log_file_lines):
            if re.sub(r"\s*|=*|-*", "", line) == "": continue
            # elif "skipping" in line.lower(): continue
            elif line_no < expected_env_keys:
                if line_no in env_attrs.keys():
                    pairs = re.split(r"\s+", re.sub(r"•|✓|Primary|Evaluation|▶", "", line).strip(), maxsplit=1)
                    if len(pairs) < 2: key = list(env_attrs[line_no].keys())[0]
                    else: key = re.sub(r"\s*|•", "", pairs[0])
                    env_attrs[line_no][key] = re.sub(r"^\s*|[\n\r]*", "", pairs[1]) 
                    continue             
                continue
            elif re.search(scenarion_pattern, line):
                scenario_env = re.split(scenarion_pattern, line.lower())[-1].split(":")[-1].strip()
                alloc_exps[allocator]["config"]["env"] = scenario_env
                # print(line)
                # print(env_attrs[4])
                if env_attrs[1] and "Log" in  env_attrs[1]:
                    log_file = env_attrs[1]["Log"].split("/")[-1]
                    alloc_exps[allocator]["config"]["log"] = log_file

                if env_attrs[4] and "Environment:" in env_attrs[4]:
                    env = env_attrs[4]["Environment:"]
                    alloc_exps[allocator]["config"]["env"] = env
                    if not scenario_env: scenario_env = env
                    if env_attrs[10]:
                        alloc_exps[allocator]["config"]["env_desc"] = env_attrs[10][env]
                continue
            elif "STARTING EXPERIMENTS:" in line.upper():
                experiment = False
                comprehensive = False
                scenario = re.sub(r"STARTING EXPERIMENTS:|\s*", "", line).strip()
                scenarios_exps[scenario] = {"env":scenario_env or scenario, "cat":"", "exp":{}, "winner":{}}
                if scenario not in alloc_exps[allocator]["scenario"].keys(): alloc_exps[allocator]["scenario"][scenario] = {}
                continue
            elif re.search("category:", line.lower()):
                experiment = False
                comprehensive = False
                scenario_cat = re.split(r"category:\s*", line.lower())[-1]
                scenarios_exps[scenario]["cat"] = scenario_cat
                continue
            elif re.search(exp_title_pattern, line):
                experiment = False
                comprehensive = False
                continue
            elif re.search("EXPERIMENT RESULTS SUMMARY", line):
                experiment = True
                comprehensive = False
                continue
            elif re.search(r"total experiment time|experiments completed|evaluation completed.", line.lower()):
                experiment = False
                comprehensive = False
                continue
            elif experiment and re.search(r"EXP\d+ Winner:", line):
                winner = parse_log_winner(line)
                if winner:
                    scenarios_exps[scenario]["winner"] = winner
                    alloc_exps[allocator]["scenario"][scenario] = scenarios_exps[scenario]
                    alloc_exps[allocator]["config"].update({
                        "scap": winner["scapacity"], 
                        "frames": winner["frames"], 
                        "step": step
                    })
                continue  
            elif re.search("COMPREHENSIVE SCENARIO PERFORMANCE ANALYSIS", line):
                experiment = False
                comprehensive = True
                # print(json.dumps(env_attrs, indent=2))
                continue
            elif experiment:
                exp_attrs = parse_experiment_line(line)
                if exp_attrs:
                    exp_no = exp_attrs["num"]
                    model = exp_attrs["model"]
                    if exp_no not in scenarios_exps[scenario]["exp"].keys():  scenarios_exps[scenario]["exp"][exp_no] = {}
                    scenarios_exps[scenario]["exp"][exp_no][model] = exp_attrs

    # Flatten the nested structure into rows
    for allocator_name, allocator_data in alloc_exps.items():
        config = allocator_data["config"]
        
        for scenario_name, scenario_data in allocator_data["scenario"].items():
            winner = scenario_data.get("winner", {})
            scenario_env = scenario_data.get("env", "")
            scenario_cat = scenario_data.get("cat", "")
            
            for exp_no, models in scenario_data.get("exp", {}).items():
                for model_name, model_data in models.items():
                    all_data.append({
                        # Config data
                        "log_file": config.get("log", ""),
                        "allocator": allocator_name,
                        "scale": config.get("scale", ""),
                        "runs": config.get("runs", ""),
                        "cap_type": config.get("cap_type", ""),
                        "env": config.get("env", ""),
                        "step": config.get("step", ""),
                        "attack_no": config.get("attack_no", ""),
                        "base": config.get("base", ""),
                        "config_scap": config.get("scap", ""),
                        "config_frames": config.get("frames", ""),
                        
                        # Scenario data
                        "scenario": scenario_name,
                        "scenario_env": re.sub(r"\(.*\)|\s+|attack", "", scenario_env.lower()).upper(),
                        "scenario_cat": re.split("\(|\)", scenario_cat)[-2],
                        
                        # Winner data
                        "winner_model": winner.get("model", ""),
                        "winner_gap": winner.get("gap", ""),
                        "winner_rate": winner.get("rate", ""),
                        "winner_frames": winner.get("frames", ""),
                        "winner_scap": winner.get("scapacity", ""),
                        
                        # Experiment data
                        "exp_no": exp_no,
                        "model": model_name,
                        "reward": model_data.get("reward", ""),
                        "eff": model_data.get("eff", ""),
                        "retries": model_data.get("retries", ""),
                        "failures": model_data.get("failures", ""),
                        "misses_thrs": model_data.get("misses_thrs", ""),
                        "scapacity": model_data.get("scapacity", ""),
                        "threshold": model_data.get("threshold", ""),
                    })

    df = pd.DataFrame(all_data)
    print(f"✅ Parsed {len(df)} entries from {len(LOG_FILES)} log files.")
    df.to_csv(f"{path}/{tests_type}/Master_{tests_type}_Dataset.csv", index=False)
    print(f"✅ Saved to Master_{tests_type}_Dataset.csv")


def convert_pkl_to_json(root_dir, keyword="MultiRunEvaluator", ext=".pkl"):
    log_paths = collect_log_paths(root_dir=Path(root_dir), keyword=keyword, ext=ext)
    
    for pkl_file in log_paths:
        try:
            with open(pkl_file, 'rb') as f: 
                data = _load_any_pickle(f)
            
            # Save as JSON in same directory as pkl file
            json_file = pkl_file.with_suffix('.json')  # Use pathlib
            with open(json_file, 'w') as f: 
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Converted: {pkl_file.name} -> {json_file.name}")
        except Exception as e:
            print(f"❌ Failed to convert {pkl_file.name}: {e}")


def _load_any_pickle(path: Path):
    """Best-effort loader: pickle → cloudpickle → SafeUnpickler."""
    data = None


    # 1) Standard pickle
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        return data
    except Exception:
        pass


    # 2) cloudpickle
    if cloudpickle is not None:
        try:
            with open(path, "rb") as f:
                data = cloudpickle.load(f)
            return data
        except Exception:
            pass


    # 3) SafeUnpickler (ignore missing modules/classes)
    try:
        with open(path, "rb") as f:
            data = SafeUnpickler(f).load()
        return data
    except Exception as e:
        print(f"      ❌ Unpickle failed: {e}")
        return None


def extract_data_from_state_file(state_file_path):
    """
    Extract flat data from a MultiRunEvaluator state file (JSON or pickle).
    
    Returns: list of dicts, each representing one model's performance in one experiment
    """
    print(f"Loading: {Path(state_file_path).name}")
    
    # Load the state (handles both JSON and pickle)
    # if str(state_file_path).endswith('.json'):
    #     with open(state_file_path, 'r') as f:
    #         state = json.load(f)
    # else:
    try:
        state = _load_any_pickle(state_file_path)
        if state is None:
            print(f"  ❌ Could not load state")
            return []
        
        all_rows = []
        
        # Extract metadata (handle both dict and object)
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)
        
        # allocator = get_val(state, 'allocator_id', 'Unknown')
        runs = get_val(state, 'runs_id', 1)
        frame_step = get_val(state, 'frame_step')
        base_frames = get_val(state, 'base_frames')
        filename = get_val(state, 'file_name', Path(state_file_path).name)
        
        # Extract scaled capacity and scale from filename
        # Format: MultiRunEvaluator_{scaled_cap}-{allocator}_...

        #   dict_keys(['scenarios_stats', 'env_experiments', 'evaluation_results', 'base_seed', 'frame_step', 'frames_count', 'base_frames', 'component', 'enable_progress', 'models', 'run_state', 'total_time', 'start_time', 'resumed', 'key_attrs', 'file_name', 'cal_winner', 'is_complete', 'env_type', 'capacity', 't_scale', 'is_base_t', 'save_to_dir', 'runs_id', 'allocator_id', 'env_id', 'attack_id', 'cap_id'])
        # print("KEYS: ", state.keys())

        t_scale = float(state.get("t_scale"))
        capacity = float(state.get("capacity"))
        scaled_cap = capacity * t_scale
        cap_type = 'Tb' if bool(state.get("is_base_t")) else "T"
        
        # Get experiment data
        # env_experiments:  dict_keys(['markov', 'stochastic', 'adaptive', 'onlineadaptive', 'none'])
        env_experiments = get_val(state, 'env_experiments', {})
        # evaluation_results:  dict_keys(['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none', 'scenarios_results'])
        evaluation_results = get_val(state, 'evaluation_results', {})
        # scenarios_results:  dict_keys(['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none'])
        eval_scenrios_results = get_val(state, 'evaluation_results', {}).get("scenarios_results", {})
        if not env_experiments:
            print(f"  ⚠️  No experiment data found")
            return []
        
        # Process each scenario and experiment
        # ['markov', 'stochastic', 'adaptive', 'onlineadaptive', 'none']
        # print("env_experiments: ", env_experiments.keys())
        # ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none', 'scenarios_results']
        # print("evaluation_results: ", evaluation_results.keys())
        # ['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none']
        # print("scenarios_results: ", eval_scenrios_results.keys())

        for scenario_name, experiments in env_experiments.items():
            if not isinstance(experiments, dict): continue
            # scenario_res = evaluation_results.get(scenario_name, {})
            scenerio_attrs = eval_scenrios_results.get(scenario_name, {})

            # [1, 2, 3, 4, 5, 'avg_efficiency_stats']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res.keys())

            # ['win_counts', 'total_experiments', 'all_model_metrics', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs.keys())

            # ['win_counts', 'total_experiments', 'all_model_metrics', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res["avg_efficiency_stats"].keys())
            
            # ['Oracle', 'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']
            # print(scenerio_attrs["all_model_metrics"].keys())
            # print(scenario_res["avg_efficiency_stats"]["all_model_metrics"].keys())
            del scenerio_attrs["all_model_metrics"]

            # ['avg_reward', 'avg_gap', 'efficiency_list', 'wins', 'avg_efficiency', 'reward_list', 'creward_list']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs["winner_avg_metrics"].keys())

            # ['win_counts', 'total_experiments', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs.keys())

            # ['win_counts', 'total_experiments', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res["avg_efficiency_stats"].keys())

            # ['avg_reward', 'avg_gap', 'efficiency_list', 'wins', 'avg_efficiency', 'reward_list', 'creward_list']
            del scenerio_attrs["winner_avg_metrics"]["reward_list"]
            del scenerio_attrs["winner_avg_metrics"]["creward_list"]
            del scenerio_attrs["winner_avg_metrics"]["efficiency_list"]
            attack_winner_attrs = scenerio_attrs["winner_avg_metrics"]


            # {
            # "attack": "None",
            # "qubit_capacities": "(8, 10, 8, 9)",
            # "frame_length": "4000",
            # "allocator": "Default",
            # "env_type": "stochastic",
            # "actk_type": "markov",
            # "runs": 5
            # }
            # print(json.dumps(state.get("key_attrs"), indent=2, default=str))

            # {
            # "win_counts": {
            #     "GNeuralUCB": 3,
            #     "EXPUCB": 1,
            #     "EXPNeuralUCB": 1
            # },
            # "total_experiments": 5,
            # "overall_winner": "GNeuralUCB",
            # "winner_efficients": {
            #     "GNeuralUCB": 92.89666681028142,
            #     "EXPUCB": 82.27584898563171,
            #     "EXPNeuralUCB": 82.65926524857409
            # },
            # "oracle_avg_reward": 5574.105608060588,
            # "avg_gap": 7.103333189718578,
            # "avg_reward": 5170.374931375836,
            # "winner_avg_metrics": {
            #     "avg_reward": 5170.374931375836,
            #     "avg_gap": 7.103333189718578,
            #     "wins": 3,
            #     "avg_efficiency": 92.89666681028142
            # },
            # "avg_efficiency": 92.89666681028142
            # }
            # print(json.dumps(scenerio_attrs, indent=2, default=str))

            # {
            # "win_counts": {
            #     "GNeuralUCB": 3,
            #     "EXPUCB": 1,
            #     "EXPNeuralUCB": 1
            # },
            # "total_experiments": 5,
            # "overall_winner": "GNeuralUCB",
            # "winner_efficients": {
            #     "GNeuralUCB": 92.89666681028142,
            #     "EXPUCB": 82.27584898563171,
            #     "EXPNeuralUCB": 82.65926524857409
            # },
            # "oracle_avg_reward": 5574.105608060588,
            # "avg_gap": 7.103333189718578,
            # "avg_reward": 5170.374931375836,
            # "winner_avg_metrics": {
            #     "avg_reward": 5170.374931375836,
            #     "avg_gap": 7.103333189718578,
            #     "wins": 3,
            #     "avg_efficiency": 92.89666681028142
            # },
            # "avg_efficiency": 92.89666681028142
            # }
            # print(json.dumps(scenario_res["avg_efficiency_stats"], indent=2, default=str))

            # {
            #     "avg_reward": 5170.374931375836,
            #     "avg_gap": 7.103333189718578,
            #     "wins": 3,
            #     "avg_efficiency": 92.89666681028142
            # }
            # print(json.dumps(attack_winner_attrs, indent=2, default=str))

            for exp_id_str, exp_data in experiments.items():
                # Convert exp_id to int
                # ['results', 'winner', 'exp_id', 'attack_category']
                # print(scenario_res[exp_id_str].keys())

                # ['Oracle', 'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']
                # print(scenario_res[exp_id_str]["results"].keys())

                try:
                    exp_id = int(exp_id_str)
                except (ValueError, TypeError):
                    continue
                
                if not isinstance(exp_data, dict):
                    continue
                
                results = exp_data.get('results', {})
                if not results:
                    continue
                
                # exp_data = env_experiments[scenario_name][exp_id_str]
                
                # Extract data for each model
                for model_name, model_data in results.items():
                    if model_name == 'Oracle':
                        continue  # Skip oracle
                    
                    # ['final_reward', 'avg_reward', 'algorithm', 'seed', 'frames_count', 'attack_type', 'model_results', 'retries', 'failed_attempts', 'efficiency', 'gap']
                    # print(model_data.keys())

                    # ['regret_list', 'reward_list', 'path_action_list', 'final_regret', 'final_reward', 'oracle_path', 'oracle_action', 'mode']
                    # print(model_data["model_results"].keys())
                    
                    failed_attempts = model_data.get('failed_attempts', {})

                    row = {
                        # === SOURCE & METADATA ===
                        'source_file': state.get("file_name"),          # Origin log file
                        'total_time': state.get("total_time"),          # Total execution time
                        'qubit_caps': state.get("key_attrs").get("qubit_capacities"),  # Qubit allocation
                        
                        # === ENVIRONMENT CONFIG ===
                        'env_type': state.get("key_attrs").get("env_type"),  # Environment type
                        'runs': state.get("key_attrs").get("runs") or state.get("runs_id"),  # Number of runs
                        'allocator': state.get("allocator_id"),         # Allocation strategy
                        
                        # === SCENARIO INFO ===
                        'scenario': scenario_name.upper(),              # Scenario name (STOCHASTIC, MARKOV, etc.)
                        'scenario_cat': exp_data.get("attack_category"), # Scenario category
                        
                        # === CAPACITY SCALING ===
                        'base_frames': base_frames,                     # Base frame count
                        'frame_step': frame_step,                       # Frame step size
                        'cap_type': cap_type,                           # Capacity type (T or Tb)
                        'scale': t_scale,                               # Scaling factor (1.0, 1.5, 2.0)
                        'capacity': scaled_cap,                         # Scaled capacity
                        
                        # === EXPERIMENT IDENTIFICATION ===
                        'experiment': exp_id_str,                       # Experiment ID
                        'winner': exp_data.get('winner'),               # This experiment's winner
                        
                        # === MODEL PERFORMANCE (PER-EXPERIMENT) ===
                        'frames': model_data.get('frames_count'),       # Frame count executed
                        'model': model_name.upper(),                    # Model name
                        'reward': model_data.get('final_reward'),       # Final reward
                        'regret': model_data["model_results"]['final_regret'],  # Final regret vs Oracle
                        'avg_reward': model_data.get('avg_reward'),     # Average reward per frame
                        'model_avg_eff': scenerio_attrs["winner_efficients"].get(model_name, 0),  # Model's avg eff across scenario
                        
                        # === EFFICIENCY & GAP ===
                        'eff_pct': model_data.get('efficiency'),        # Efficiency percentage vs Oracle
                        'gap_pct': model_data.get('gap'),               # Gap percentage vs Oracle
                        
                        # === FAILURE TRACKING ===
                        'retries': model_data.get('retries'),           # Number of retries
                        'failures': failed_attempts.get('failed', 0),   # Failed attempts
                        'misses_thrs': failed_attempts.get('under_threshold', 0),  # Below threshold
                        
                        # === SCENARIO WINNER (AGGREGATE ACROSS ALL EXPERIMENTS) ===
                        'scenario_winner': scenerio_attrs["overall_winner"],  # Winner of entire scenario
                        'scen_winner_eff': attack_winner_attrs["avg_efficiency"],  # Scenario winner's avg efficiency
                        'scen_winner_reward': attack_winner_attrs["avg_reward"],   # Scenario winner's avg reward
                        'scen_winner_gap': attack_winner_attrs["avg_gap"],         # Scenario winner's avg gap
                    }
                    all_rows.append(row)
    except:
         print(f"Loading: {Path(state_file_path).name} FAILED")

    
    return all_rows




def convert_state_files_to_csv(pkl_files):
    """
    Convert each MultiRunEvaluator state file to its own CSV file.
    
    Args:
        pkl_files: List of pickle files to convert
    """
    print(f"CONVERTING STATE FILES TO CSV")
    print(f"Found {len(pkl_files)} state files\n")
    print(f"{'='*80}")
    
    converted_files = []
    all_dfs = []  # ← Collect DataFrames in a list
    
    # CONVERT EACH FILE TO ITS OWN CSV
    for pkl_file in pkl_files:
        try:
            # Extract data from this state file
            rows = extract_data_from_state_file(pkl_file)
            
            if not rows:
                print(f"  ⚠️  No data extracted from {pkl_file.name}")
                continue
            
            # Create DataFrame for this file
            df = pd.DataFrame(rows)
            all_dfs.append(df)  # ← Add to list instead of append()
            
            # Save as CSV with same name as pkl file
            output_csv = pkl_file.with_suffix('.csv')
            df.to_csv(output_csv, index=False)
            
            converted_files.append(output_csv)
            
            print(f"  ✅ {pkl_file.name}")
            print(f"     → {output_csv.name}")
            print(f"     → {len(rows)} records, {df['scenario'].nunique()} scenarios, {df['model'].nunique()} models")
            
        except Exception as e:
            print(f"  ❌ Failed to process {pkl_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # ← Concatenate all DataFrames at once
    master_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    
    print(f"\n{'='*80}")
    print(f"CONVERSION COMPLETE")
    print(f"{'='*80}")
    print(f"Converted {len(master_df)} entries")
    print(f"Converted {len(converted_files)} files")
    print(f"{'='*80}\n")
    
    return master_df



def convert_key_state_files_to_csv(root_dir, output="", keyword=r"(?=.*MultiRunEvaluator)(?=.*iCMABs2\.pkl)", ext=".pkl"):
    """
    Convert each MultiRunEvaluator state file to its own CSV file.
    
    Args:
        root_dir: Directory containing .pkl state files
        keyword: Keyword to match in filenames
        ext: File extension (default: .pkl)
    """
    pkl_files = collect_log_paths(Path(path), keyword, ext)
    
    print(f"\n{'='*80}")
    print(f"CONVERTING KEY STATE FILES TO CSV")
    print(f"{'='*80}")
    print(f"Directory: {root_dir}")
    print(f"Keyword: {keyword}")
    print(f"Extension: {ext}")
    df = convert_state_files_to_csv(pkl_files)

    if output and not df.empty:
        print(df.head())
        df.to_csv(output, index=False)

# Update main
if __name__ == "__main__":
    cleanup_and_consolidate()
    # generate_master_csv("Hybrid_Tests")
    # generate_master_csv("EXP3_Tests")
    # generate_master_csv("iCMABs_Tests")
    path = "/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state/"
    # print(files)
    # df = convert_state_files_to_csv(path, keyword="MultiRunEvaluator", ext=".pkl")

    # key = "EXP3"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_{key}.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}\.pkl)")

    # key = "iCMABs"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_{key.replace("i", "")}.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}\.pkl)")

    # key = "iCMABs2"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_{key.replace("2", "")}.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}\.pkl)")

    key = "Tb?"
    output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_Hybrid.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}\.pkl)")
