import os, json
import sys
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


def clean_qubit_allocation(qubit_alloc):
    """
    Clean qubit allocation from various messy formats to standard tuple string.
    
    Input formats:
    - ('(', '1', '8', ',', ' ', '9', ',', ' ', '6', ',', ' ', '2', ')')
    - Nested quote mess
    - Normal tuple: (18, 9, 6, 2)
    - String: "(18, 9, 6, 2)"
    
    Output: "(18, 9, 6, 2)" or original if already clean
    """
    if not qubit_alloc:
        return ""
    
    # If it's already a clean tuple, convert to string
    if isinstance(qubit_alloc, tuple) and all(isinstance(x, int) for x in qubit_alloc):
        return str(qubit_alloc)
    
    # Convert to string if not already
    alloc_str = str(qubit_alloc)
    
    # Extract only digits and commas
    import re
    digits = re.findall(r'\d+', alloc_str)
    
    if digits:
        # Reconstruct as clean tuple string
        return f"({', '.join(digits)})"
    
    return ""


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
            print(f"[DEBUG]   Checking date_dir: {date_dir}")


            if not date_dir.is_dir():
                print(f"[SKIP]     Not a directory: {date_dir}")
                continue
            if not date_dir.name.startswith("day_"):
                print(f"[SKIP]     Not a day folder: {date_dir.name}")
                continue


            date_key = date_dir.name
            print(f"[DEBUG]   → Day folder accepted: {date_key}")


            # --- SECOND LOOP: files ---
            has_files = False
            for f in date_dir.iterdir():
                print(f"[DEBUG]       Inspect file/dir: {f}")


                if not f.is_file():
                    print(f"[SKIP]         Not a file: {f}")
                    continue


                has_files = True
                abs_path = str(f.resolve())


                print(f"[DEBUG]         File accepted: {f.name}")
                print(f"[DEBUG]         Abs path: {abs_path}")


                try:
                    registry[component][f.name] = abs_path
                    corrected += 1
                    print(f"[CORRECTED]    Updated: {component}/{date_key}/{f.name}")
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
                        "scenario_cat": re.split(r"\(|\)", scenario_cat)[-2],
                        
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
            data = _load_any_pickle(pkl_file)
            
            # Save as JSON in same directory as pkl file
            json_file = pkl_file.with_suffix('.json')  # Use pathlib
            with open(json_file, 'w') as f: 
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Converted: {pkl_file.name} -> {json_file.name}")
        except Exception as e:
            print(f"❌ Failed to convert {pkl_file.name}: {e}")


_DRIVE_MANAGER_CACHE = {}


def _analysis_allow_drive_downloads() -> bool:
    """Return whether Drive downloads are allowed for state_analysis.

    Priority:
    1) DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS (if set)
    2) DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS (shared knob with runtime resume)
    """
    override = os.environ.get("DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS")
    if override is not None:
        return override == "1"
    return os.environ.get("DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS", "1") == "1"


def _ensure_daqr_importable() -> None:
    """Make `daqr` importable when running from the repo root."""
    try:
        daqr_root = PROJECT_ROOT
        if str(daqr_root) not in sys.path:
            sys.path.insert(0, str(daqr_root))
    except Exception:
        pass


def _infer_config_dir(state_root: Path) -> Path:
    """Infer the `daqr/config` directory from a framework_state root/path."""
    try:
        state_root = Path(state_root)
    except Exception:
        return PROJECT_ROOT / "daqr" / "config"

    if state_root.name in {"framework_state", "model_state", "quantum_logs"}:
        return state_root.parent

    for parent in state_root.parents:
        if parent.name == "config" and parent.parent.name == "daqr":
            return parent

    return PROJECT_ROOT / "daqr" / "config"


def _get_drive_manager(config_dir: Path, verbose: bool = False):
    """Best-effort create a Drive-backed manager (or return cached).

    This is intentionally lazy-imported so `state_analysis` can run without
    Drive dependencies installed.
    """
    if not _analysis_allow_drive_downloads():
        return None

    try:
        config_dir = Path(config_dir)
    except Exception:
        return None

    cache_key = str(config_dir.resolve())
    if cache_key in _DRIVE_MANAGER_CACHE:
        return _DRIVE_MANAGER_CACHE[cache_key]

    _ensure_daqr_importable()

    try:
        # Use the lightest-weight Drive manager available: we only need Drive API
        # access + state index helpers (not a full local registry scan).
        from daqr.config.gd_backup_manager import GoogleDriveBackupManager

        date_str = f"day_{datetime.now().strftime('%Y%m%d')}"
        mgr = GoogleDriveBackupManager(date_str=date_str, config_dir=config_dir, verbose=verbose)
    except Exception as exc:
        if verbose:
            print(f"[WARN] Drive manager unavailable: {exc}")
        mgr = None

    _DRIVE_MANAGER_CACHE[cache_key] = mgr
    return mgr


def _is_drive_filesystem_mirror_path(path: Path) -> bool:
    """Return True when `path` points into the macOS Google Drive filesystem mirror.

    Reading large pickles from this mirror can intermittently time out.
    """
    try:
        parts = Path(path).parts
    except Exception:
        return False

    if ".shortcut-targets-by-id" in parts:
        return True
    if "CloudStorage" in parts and any(p.startswith("GoogleDrive") for p in parts):
        return True
    return False


def _download_state_from_drive_datalake(
    mgr,
    *,
    component: str,
    filename: str,
    entry=None,
    verbose: bool = False,
):
    """Download a state file via Drive API using the per-component state index.

    This is intentionally API/datalake-only and will NOT fall back to the local
    Drive filesystem mirror.
    """
    if mgr is None or not getattr(mgr, "remote_available", False) or not getattr(mgr, "drive", None):
        return None

    try:
        from googleapiclient.http import MediaIoBaseDownload
    except Exception:
        return None

    if entry is None:
        try:
            index = mgr.ensure_drive_state_index(component, build_if_missing=True)
        except Exception as exc:
            if verbose:
                print(f"  ⚠️ Could not load Drive state index for {component}: {exc}")
            index = None
        entry = index.get(filename) if isinstance(index, dict) else None

    if not (isinstance(entry, dict) and entry.get("drive_id")):
        return None

    day_name = entry.get("day")
    if not (isinstance(day_name, str) and day_name.startswith("day_")):
        day_name = f"day_{datetime.now().strftime('%Y%m%d')}"

    try:
        local_root = Path(getattr(mgr, "quantum_data_paths", {}).get("local", _infer_config_dir(PROJECT_ROOT)))
        local_dir = local_root / component / day_name
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename
        if local_path.exists() and local_path.stat().st_size > 0:
            return local_path

        request = mgr.drive.files().get_media(fileId=entry["drive_id"])
        with open(local_path, "wb") as f:
            done = False
            downloader = MediaIoBaseDownload(f, request)
            while not done:
                _status, done = downloader.next_chunk()

        if local_path.exists() and local_path.stat().st_size > 0:
            if verbose:
                print(f"  ☁️ Downloaded evaluator state from Drive datalake: {local_path}")
            return local_path
    except Exception as exc:
        if verbose:
            print(f"  ⚠️ Drive datalake download failed for {filename}: {exc}")

    return None


def ensure_evaluator_state_downloaded(state_file_path: Path, verbose: bool = False) -> Path:
    """Ensure a MultiRunEvaluator state pickle exists locally.

    If missing, attempt to recover it from Drive using the existing DAQR Drive
    manager implementation. Only downloads evaluator pickles (framework_state).
    """
    path = Path(state_file_path)
    try:
        if path.exists() and path.stat().st_size > 0 and not _is_drive_filesystem_mirror_path(path):
            return path
    except Exception:
        # If stat fails, fall through to best-effort recovery.
        pass

    filename = path.name
    if not filename.lower().startswith("multirunevaluator_"):
        return path

    mgr = _get_drive_manager(_infer_config_dir(path.parent), verbose=verbose)
    if mgr is None:
        return path

    downloaded_path = _download_state_from_drive_datalake(
        mgr,
        component="framework_state",
        filename=filename,
        verbose=verbose,
    )
    if downloaded_path is not None:
        return Path(downloaded_path)

    # Avoid returning a Drive filesystem mirror path when we failed to fetch
    # from the datalake (it is unreliable for large pickle reads on macOS).
    try:
        if path.exists() and _is_drive_filesystem_mirror_path(path):
            if verbose:
                print(f"  ⚠️ Refusing to load evaluator state from Drive mirror: {path}")
            return Path(state_file_path)
    except Exception:
        pass

    return path


def prefetch_missing_evaluator_states(
    *,
    framework_state_root: Path,
    keyword: str,
    ext: str,
    have_filenames: set[str],
    verbose: bool = False,
) -> list[Path]:
    """Prefetch missing evaluator states from Drive for a given filename regex.

    Downloads only MultiRunEvaluator pickles into local framework_state/day_*.
    """
    root = Path(framework_state_root)
    if root.name != "framework_state":
        return []

    mgr = _get_drive_manager(_infer_config_dir(root), verbose=verbose)
    if mgr is None:
        return []

    try:
        index = mgr.ensure_drive_state_index("framework_state", build_if_missing=True)
    except Exception as exc:
        if verbose:
            print(f"[WARN] Could not load Drive state index: {exc}")
        return []

    if not isinstance(index, dict) or not index:
        return []

    downloaded_paths: list[Path] = []
    for filename in sorted(index.keys()):
        if filename in have_filenames:
            continue
        if not filename.lower().startswith("multirunevaluator_"):
            continue
        if Path(filename).suffix != ext:
            continue
        try:
            if not re.search(keyword, filename):
                continue
        except re.error as exc:
            if verbose:
                print(f"[WARN] Invalid regex {keyword!r}: {exc}")
            break

        local_path = _download_state_from_drive_datalake(
            mgr,
            component="framework_state",
            filename=filename,
            entry=index.get(filename),
            verbose=verbose,
        )
        if local_path is not None:
            downloaded_paths.append(Path(local_path))

    if verbose and downloaded_paths:
        print(f"☁️ Prefetched {len(downloaded_paths)} evaluator state(s) from Drive")
    return downloaded_paths


def download_evaluator_states_for_pattern(
    *,
    framework_state_root: Path,
    pattern: str,
    ext: str = ".pkl",
    verbose: bool = False,
) -> list[Path]:
    """Download evaluator state pickles from Drive for a filename regex pattern.

    This is a single-purpose helper you can call before building master datasets.
    It uses the same DAQR resume download path:

      - metadata: `GoogleDriveBackupManager.ensure_drive_state_index("framework_state")`
      - download: `GoogleDriveBackupManager.download_any_date(component="framework_state", ...)`

    The regex `pattern` is matched against Drive state-index keys (full saved filenames).
    Only `MultiRunEvaluator_*.pkl` files are considered.

    Notes:
      - Requires Drive downloads to be enabled (via `DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS=1`
        or the shared `DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS=1`).
      - Requires Drive API availability; this helper intentionally does not rely on the macOS
        Google Drive filesystem mirror.
    """

    root = Path(framework_state_root)
    if root.name != "framework_state":
        raise ValueError(
            f"framework_state_root must point to the local 'framework_state' directory; got: {root}"
        )

    if not _analysis_allow_drive_downloads():
        raise RuntimeError(
            "Drive downloads are disabled. Set DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS=1 "
            "(or DAQR_RESUME_ALLOW_DRIVE_DOWNLOADS=1) to enable pattern-based downloads."
        )

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {pattern!r}: {exc}") from exc

    mgr = _get_drive_manager(_infer_config_dir(root), verbose=verbose)
    if mgr is None:
        raise RuntimeError("Drive manager unavailable; cannot download evaluator states.")

    if not getattr(mgr, "remote_available", False) or not getattr(mgr, "drive", None):
        raise RuntimeError("Drive API unavailable; cannot download evaluator states.")

    try:
        index = mgr.ensure_drive_state_index("framework_state", build_if_missing=True)
    except Exception as exc:
        raise RuntimeError(f"Could not load Drive state index for framework_state: {exc}") from exc

    if not isinstance(index, dict) or not index:
        raise RuntimeError("Drive state index for framework_state is empty/unavailable.")

    matched_filenames: list[str] = []
    for filename in sorted(index.keys()):
        if not isinstance(filename, str) or not filename:
            continue
        if not filename.lower().startswith("multirunevaluator_"):
            continue
        if Path(filename).suffix != ext:
            continue
        if not regex.search(filename):
            continue
        matched_filenames.append(filename)

    if not matched_filenames:
        raise RuntimeError(f"No evaluator states matched pattern: {pattern!r}")

    downloaded_paths: list[Path] = []
    failures: list[str] = []

    for filename in matched_filenames:
        try:
            local_path_str = mgr.download_any_date(component="framework_state", filename=filename)
        except Exception as exc:
            failures.append(f"{filename}: {type(exc).__name__}: {exc}")
            continue

        if not local_path_str:
            failures.append(f"{filename}: download_any_date returned no path")
            continue

        local_path = Path(local_path_str)
        try:
            if not local_path.exists() or local_path.stat().st_size <= 0:
                failures.append(f"{filename}: staged file missing/empty at {local_path}")
                continue
        except Exception as exc:
            failures.append(f"{filename}: could not stat staged file at {local_path}: {exc}")
            continue

        downloaded_paths.append(local_path)

    if failures:
        raise RuntimeError(
            "Failed to download one or more evaluator state(s):\n" + "\n".join(failures)
        )

    if verbose:
        print(f"☁️ Downloaded {len(downloaded_paths)} evaluator state(s) via pattern")

    return downloaded_paths


def _load_any_pickle(path: Path):
    """Best-effort loader: pickle → cloudpickle → SafeUnpickler."""
    path = ensure_evaluator_state_downloaded(Path(path))
    data = None
    # Expose last load method for clearer logs (read by extract_data_from_state_file)
    # Methods: "pickle" (attempt 1), "cloudpickle" (attempt 2), "safe" (attempt 3), "failed"
    global _LAST_UNPICKLE_METHOD, _LAST_UNPICKLE_ATTEMPT
    _LAST_UNPICKLE_METHOD = "failed"
    _LAST_UNPICKLE_ATTEMPT = 0


    # 1) Standard pickle
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        _LAST_UNPICKLE_METHOD = "pickle"
        _LAST_UNPICKLE_ATTEMPT = 1
        return data
    except Exception:
        pass


    # 2) cloudpickle
    if cloudpickle is not None:
        try:
            with open(path, "rb") as f:
                data = cloudpickle.load(f)
            _LAST_UNPICKLE_METHOD = "cloudpickle"
            _LAST_UNPICKLE_ATTEMPT = 2
            return data
        except Exception:
            pass


    # 3) SafeUnpickler (ignore missing modules/classes)
    try:
        with open(path, "rb") as f:
            data = SafeUnpickler(f).load()
        _LAST_UNPICKLE_METHOD = "safe"
        _LAST_UNPICKLE_ATTEMPT = 3
        return data
    except Exception as e:
        print(f"      ❌ Unpickle failed: {e}")
        _LAST_UNPICKLE_METHOD = "failed"
        _LAST_UNPICKLE_ATTEMPT = 0
        return None


def extract_data_from_state_file(state_file_path):
    """
    Extract flat data from a MultiRunEvaluator state file (JSON or pickle).
    
    Returns: list of dicts, each representing one model's performance in one experiment
    """
    print(f"Loading: {Path(state_file_path).name}")
    all_rows = []
    
    # Load the state (handles both JSON and pickle)
    # if str(state_file_path).endswith('.json'):
    #     with open(state_file_path, 'r') as f:
    #         state = json.load(f)
    # else:
    try:
        state = _load_any_pickle(state_file_path)
        if _LAST_UNPICKLE_METHOD in ("cloudpickle", "safe"):
            print(
                f"  ✅ Loaded successfully on attempt {_LAST_UNPICKLE_ATTEMPT} ({_LAST_UNPICKLE_METHOD})"
            )
        if state is None:
            print(f"  ❌ Could not load state")
            return []
        
        # Extract metadata (handle both dict and object)
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)
        
        # allocator = get_val(state, 'allocator_id', 'Unknown')
        runs = get_val(state, 'runs_id', 1)
        frame_step = get_val(state, 'frame_step')
        base_frames = get_val(state, 'base_frames')
        stored_filename = get_val(state, 'file_name', None)
        path_filename = Path(state_file_path).name
        filename = stored_filename or path_filename

        key_attrs = get_val(state, 'key_attrs', {}) or {}
        if not isinstance(key_attrs, dict):
            key_attrs = {}
        
        # Extract scaled capacity and scale from filename
        # Format: MultiRunEvaluator_{scaled_cap}-{allocator}_...

        #   dict_keys(['scenarios_stats', 'env_experiments', 'evaluation_results', 'base_seed', 'frame_step', 'frames_count', 'base_frames', 'component', 'enable_progress', 'models', 'run_state', 'total_time', 'start_time', 'resumed', 'key_attrs', 'file_name', 'cal_winner', 'is_complete', 'env_type', 'capacity', 't_scale', 'is_base_t', 'save_to_dir', 'runs_id', 'allocator_id', 'env_id', 'attack_id', 'cap_id'])
        # print("KEYS: ", state.keys())

        def _as_float(v):
            try:
                if v is None:
                    return None
                return float(v)
            except (TypeError, ValueError):
                return None

        def _parse_scale_tag(name: str):
            # Examples: *_S2T.pkl, *_S1Tb.pkl, *_S1_5T.pkl
            m = re.search(r"_S(?P<scale>[0-9]+(?:[._][0-9]+)?)(?P<cap_type>Tb|T)(?:\d*)?\.pkl$", name)
            if not m:
                return None, None
            scale_str = str(m.group('scale'))
            # Historical convention: 1_5 means 1.5
            if '_' in scale_str and '.' not in scale_str:
                scale_str = scale_str.replace('_', '.')
            return _as_float(scale_str), str(m.group('cap_type'))

        parsed_scale, parsed_cap_type = _parse_scale_tag(path_filename)

        t_scale = _as_float(get_val(state, 't_scale'))
        if t_scale is None:
            t_scale = parsed_scale

        capacity = _as_float(get_val(state, 'capacity'))
        if capacity is None:
            capacity = _as_float(get_val(state, 'cap_id'))

        scaled_cap = (capacity * t_scale) if (capacity is not None and t_scale is not None) else capacity

        is_base_t = get_val(state, 'is_base_t')
        if is_base_t is None and parsed_cap_type:
            is_base_t = (parsed_cap_type == 'Tb')
        cap_type = 'Tb' if bool(is_base_t) else 'T'

        # Usage in your extraction:
        qubit_alloc = key_attrs.get("qubit_capacities", "")
        qubit_alloc_clean = clean_qubit_allocation(qubit_alloc)
        if not qubit_alloc_clean:
            # print(json.dumps(state.get("key_attrs", {}), indent=2))
            qubit_alloc_clean = clean_qubit_allocation(state.get("qubit_capacities", ""))
            # print(qubit_alloc_clean)

        
        # Get experiment data
        eval_scen_qubits_caps = get_val(state, "runner_qubit_caps", {})
        if not isinstance(eval_scen_qubits_caps, dict):
            eval_scen_qubits_caps = {}
        # if eval_scen_qubits_caps: print(json.dumps(eval_scen_qubits_caps, indent=2))
        
        # env_experiments:  dict_keys(['markov', 'stochastic', 'adaptive', 'onlineadaptive', 'none'])
        env_experiments = get_val(state, 'env_experiments', {}) or {}
        if not isinstance(env_experiments, dict):
            env_experiments = {}
        # evaluation_results:  dict_keys(['stochastic', 'markov', 'adaptive', 'onlineadaptive', 'none', 'scenarios_results'])
        evaluation_results = get_val(state, 'evaluation_results', {}) or {}
        if not isinstance(evaluation_results, dict):
            evaluation_results = {}
        # Newer schema: evaluation_results["scenarios_results"][scenario_name] -> aggregated scenario stats
        eval_scenrios_results = evaluation_results.get("scenarios_results", {})
        if not isinstance(eval_scenrios_results, dict):
            eval_scenrios_results = {}
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

        def _mean(values):
            vals = []
            for v in values or []:
                fv = _as_float(v)
                if fv is not None:
                    vals.append(fv)
            return (sum(vals) / len(vals)) if vals else None

        def _fallback_scenario_aggregates(experiments_dict):
            """Best-effort scenario aggregates from per-experiment results.

            Older MultiRunEvaluator states may not include evaluation_results['scenarios_results'].
            """
            from collections import Counter, defaultdict

            winner_counts = Counter()
            metrics = defaultdict(lambda: {"eff": [], "avg_reward": [], "gap": []})

            if not isinstance(experiments_dict, dict):
                return {
                    "scenario_winner": None,
                    "scen_winner_eff": None,
                    "scen_winner_reward": None,
                    "scen_winner_gap": None,
                    "model_avg_eff": {},
                }

            for exp_data in experiments_dict.values():
                if not isinstance(exp_data, dict):
                    continue
                w = exp_data.get('winner')
                if isinstance(w, str) and w:
                    winner_counts[w] += 1

                results = exp_data.get('results') or {}
                if not isinstance(results, dict):
                    continue
                for model_name, model_data in results.items():
                    if not isinstance(model_data, dict):
                        continue
                    eff = model_data.get('efficiency')
                    if eff is not None:
                        metrics[model_name]["eff"].append(eff)
                    ar = model_data.get('avg_reward')
                    if ar is not None:
                        metrics[model_name]["avg_reward"].append(ar)
                    gap = model_data.get('gap')
                    if gap is not None:
                        metrics[model_name]["gap"].append(gap)

            scenario_winner = winner_counts.most_common(1)[0][0] if winner_counts else None
            model_avg_eff = {mn: _mean(m.get('eff')) for mn, m in metrics.items()}

            winner_eff = _mean(metrics.get(scenario_winner, {}).get('eff')) if scenario_winner else None
            winner_reward = _mean(metrics.get(scenario_winner, {}).get('avg_reward')) if scenario_winner else None
            winner_gap = _mean(metrics.get(scenario_winner, {}).get('gap')) if scenario_winner else None

            return {
                "scenario_winner": scenario_winner,
                "scen_winner_eff": winner_eff,
                "scen_winner_reward": winner_reward,
                "scen_winner_gap": winner_gap,
                "model_avg_eff": model_avg_eff,
            }

        for scenario_name, experiments in env_experiments.items():
            if not isinstance(experiments, dict):
                continue
            # scenario_res = evaluation_results.get(scenario_name, {})
            cenario_qubit_caps = None
            scenerio_attrs = eval_scenrios_results.get(scenario_name, {})
            if not isinstance(scenerio_attrs, dict):
                scenerio_attrs = {}
            scenario_qubits_caps = eval_scen_qubits_caps.get(scenario_name, {})
            if scenario_qubits_caps: 
                # print(json.dumps(scenario_qubits_caps, indent=2))
                cenario_qubit_caps = next(iter(scenario_qubits_caps.values()))
                # print(cenario_qubit_caps)

            # [1, 2, 3, 4, 5, 'avg_efficiency_stats']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res.keys())

            # ['win_counts', 'total_experiments', 'all_model_metrics', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs.keys())

            # ['win_counts', 'total_experiments', 'all_model_metrics', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res["avg_efficiency_stats"].keys())
            
            # ['Oracle', 'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']
            # print(scenerio_attrs["all_model_metrics"].keys())
            # print(scenario_res["avg_efficiency_stats"]["all_model_metrics"].keys())
            all_model_metrics = scenerio_attrs.get("all_model_metrics") or {}
            winner_avg_metrics = scenerio_attrs.get("winner_avg_metrics") or {}
            winner_efficients = scenerio_attrs.get("winner_efficients") or {}
            if not isinstance(all_model_metrics, dict):
                all_model_metrics = {}
            if not isinstance(winner_avg_metrics, dict):
                winner_avg_metrics = {}
            if not isinstance(winner_efficients, dict):
                winner_efficients = {}

            fallback = _fallback_scenario_aggregates(experiments) if not scenerio_attrs else None

            # ['avg_reward', 'avg_gap', 'efficiency_list', 'wins', 'avg_efficiency', 'reward_list', 'creward_list']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs["winner_avg_metrics"].keys())

            # ['win_counts', 'total_experiments', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"evaluation_results for scenario {scenario_name}: ", scenerio_attrs.keys())

            # ['win_counts', 'total_experiments', 'overall_winner', 'winner_efficients', 'oracle_avg_reward', 'avg_gap', 'avg_reward', 'winner_avg_metrics', 'avg_efficiency']
            # print(f"scenarios_results for scenario {scenario_name}: ", scenario_res["avg_efficiency_stats"].keys())

            # ['avg_reward', 'avg_gap', 'efficiency_list', 'wins', 'avg_efficiency', 'reward_list', 'creward_list']
            attack_winner_attrs = {
                key: value
                for key, value in winner_avg_metrics.items()
                if key not in {"reward_list", "creward_list", "efficiency_list"}
            }


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
                
                exp_qubits_caps = scenario_qubits_caps.get(exp_id_str) or cenario_qubit_caps
                # if exp_qubits_caps: print(exp_qubits_caps)
                # exp_data = env_experiments[scenario_name][exp_id_str]
                
                # Extract data for each model
                for model_name, model_data in results.items():
                    # if model_name == 'Oracle':
                    #     continue  # Skip oracle
                    
                    # ['final_reward', 'avg_reward', 'algorithm', 'seed', 'frames_count', 'attack_type', 'model_results', 'retries', 'failed_attempts', 'efficiency', 'gap']
                    # print(model_data.keys())

                    # ['regret_list', 'reward_list', 'path_action_list', 'final_regret', 'final_reward', 'oracle_path', 'oracle_action', 'mode']
                    # print(model_data["model_results"].keys())
                    
                    failed_attempts = model_data.get('failed_attempts') or {}
                    if not isinstance(failed_attempts, dict):
                        failed_attempts = {}

                    model_results = model_data.get('model_results') or {}
                    if not isinstance(model_results, dict):
                        model_results = {}

                    model_avg_eff = winner_efficients.get(model_name)
                    if model_avg_eff is None and fallback:
                        model_avg_eff = (fallback.get('model_avg_eff') or {}).get(model_name)

                    scenario_winner = scenerio_attrs.get("overall_winner")
                    scen_winner_eff = attack_winner_attrs.get("avg_efficiency")
                    scen_winner_reward = attack_winner_attrs.get("avg_reward")
                    scen_winner_gap = attack_winner_attrs.get("avg_gap")
                    if fallback:
                        scenario_winner = scenario_winner or fallback.get("scenario_winner")
                        if scen_winner_eff is None:
                            scen_winner_eff = fallback.get("scen_winner_eff")
                        if scen_winner_reward is None:
                            scen_winner_reward = fallback.get("scen_winner_reward")
                        if scen_winner_gap is None:
                            scen_winner_gap = fallback.get("scen_winner_gap")

                    row = {
                        # === SOURCE & METADATA ===
                        'source_file': path_filename,                   # Origin state filename
                        'total_time': get_val(state, "total_time"),     # Total execution time
                        'qubit_caps': exp_qubits_caps or qubit_alloc_clean,  # Qubit allocation
                        
                        # === ENVIRONMENT CONFIG ===
                        'env_type': key_attrs.get("env_type"),          # Environment type
                        'runs': key_attrs.get("runs") or get_val(state, "runs_id"),  # Number of runs
                        'allocator': get_val(state, "allocator_id") or key_attrs.get("allocator"),  # Allocation strategy
                        
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
                        'regret': model_results.get('final_regret'),     # Final regret vs Oracle
                        'avg_reward': model_data.get('avg_reward'),     # Average reward per frame
                        'model_avg_eff': model_avg_eff,                 # Model's avg eff across scenario (best-effort)
                        
                        # === EFFICIENCY & GAP ===
                        'eff_pct': model_data.get('efficiency'),        # Efficiency percentage vs Oracle
                        'gap_pct': model_data.get('gap'),               # Gap percentage vs Oracle
                        
                        # === FAILURE TRACKING ===
                        'retries': model_data.get('retries'),           # Number of retries
                        'failures': failed_attempts.get('failed', 0),   # Failed attempts
                        'misses_thrs': failed_attempts.get('under_threshold', 0),  # Below threshold
                        
                        # === SCENARIO WINNER (AGGREGATE ACROSS ALL EXPERIMENTS) ===
                        'scenario_winner': scenario_winner,             # Winner of entire scenario (best-effort)
                        'scen_winner_eff': scen_winner_eff,             # Scenario winner's avg efficiency (best-effort)
                        'scen_winner_reward': scen_winner_reward,       # Scenario winner's avg reward (best-effort)
                        'scen_winner_gap': scen_winner_gap,             # Scenario winner's avg gap (best-effort)
                    }
                    all_rows.append(row)
    except Exception as e:
        # Important: "FAILED" here historically did not always mean "unusable" because extraction may
        # have already collected valid rows before a non-critical KeyError late in the process.
        if all_rows:
            print(
                f"  ⚠️ Extraction warning (recovered): extracted {len(all_rows)} rows; {type(e).__name__}: {e}"
            )
        else:
            print(f"  ❌ Extraction failed: {type(e).__name__}: {e}")

    
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
                print(f"  ℹ️  Skipping (no evaluation payload): {pkl_file.name}")
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
    root_dir = Path(root_dir)
    pkl_files = collect_log_paths(root_dir, keyword, ext)

    # Fetch evaluator states from Drive using the same resume download path.
    # This matches `keyword` against Drive state-index keys (full filenames)
    # and downloads ALL matches.
    downloaded = download_evaluator_states_for_pattern(
        framework_state_root=root_dir,
        pattern=keyword,
        ext=ext,
        verbose=True,
    )
    for downloaded_path in downloaded:
        if downloaded_path.exists() and downloaded_path.suffix == ext and re.search(keyword, downloaded_path.name):
            pkl_files.append(downloaded_path)

    # De-duplicate by absolute path.
    uniq = {str(p.resolve()): p for p in pkl_files}
    pkl_files = sorted(uniq.values())
    
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
    # cleanup_and_consolidate()
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

    # key = r"(3|5)_(\(18_9_6_2\)_)?S\d+([._]\d+)?Tb?"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_Hybrid.csv"
    # convert_key_state_files_to_csv(
    #     path,
    #     output=output_path,
    #     keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key}\.pkl)",
    # )

    # key = "1000_1000_1_S"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_{key}_paper8.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*1000_1000_1_S.*T_paper8.*\.pkl)")

    # key = "4000_2000_5_S"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_paper2_4000_2000_5_ST.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key+'.*_paper2'}\.pkl)")


    # key = "50_50_5_S"
    # output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_paper7{key}.csv"
    # convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key+'.*T_paper7'}\.pkl)")


    # Default_All_All-4000_2000_5_S2T_paper2.pkl
    key = "4000_2000_5_S"
    output_path = f"/Users/pitergarcia/DataScience/Semester4/GA-Work/Validated_Logs/Master_Dataset_paper7{key}.csv"
    convert_key_state_files_to_csv(path, output=output_path, keyword=fr"(?=.*MultiRunEvaluator)(?=.*{key+'.*T_paper7'}\.pkl)")