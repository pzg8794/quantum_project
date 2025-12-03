import os, json
from pathlib import Path
from datetime import datetime
import shutil
import pickle
import cloudpickle
import ast
import re


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
                elif "Random" not in f.name:
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
                    new_name = pattern.sub(r"\1\2", f.name)
                    
                    if new_name != f.name:
                        new_path = date_dir / new_name
                        
                        print(f"   Fixing: {f.name}")
                        print(f"       ->  {new_name}")
                        
                        try:
                            if new_path.exists():
                                new_path.unlink() # Overwrite/dedupe
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


# ============================================================
# MASTER FUNCTION
# ============================================================


def cleanup_and_consolidate():
    print("\n========== STARTING CLEANUP ==========")

    # STEP 0a — Fix Directory Names (day_day_)
    fix_double_day_directories(ALL_STATE_ROOTS)
    
    # STEP 0 — Fix float filenames first (so other regexes work on clean ints)
    fix_float_filenames(ALL_STATE_ROOTS)


    # STEP 1 — rename model files to proper format
    rename_model_files(ALL_STATE_ROOTS)


    # # for emergency use only
    # # rename_model_state_files(ALL_STATE_ROOTS)


    # Tag MultiRunEvaluators with scale/T-type
    # tag_multirun_evaluators_from_filename_and_object(ALL_STATE_ROOTS) # for emergency


    # STEP 1 — rename Random allocator files
    extract_and_rename_random_allocator_files(ALL_STATE_ROOTS)


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


# Update main
if __name__ == "__main__":
    cleanup_and_consolidate()
