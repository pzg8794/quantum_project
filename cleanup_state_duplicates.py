import re
import os
from pathlib import Path

# ==========================================
# CONFIG
# ==========================================
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR / "Dynamic_Routing_Eval_Framework"
DATALAKE_ROOT = Path("/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake")

STATE_ROOTS = [
    PROJECT_ROOT / "daqr" / "config" / "framework_state",
    PROJECT_ROOT / "daqr" / "config" / "model_state",
    DATALAKE_ROOT / "framework_state",
    DATALAKE_ROOT / "model_state",
]

def fix_files_aggressive():
    print("🔥 STARTING AGGRESSIVE REGEX FIX 🔥")
    fixed = 0
    
    # EXPLANATION OF REGEX:
    # 1. (_\d+_\d+_\d+_\d+)   -> Capture the first valid block of numbers (e.g., _8_10_8_9)
    # 2. (?:...)+             -> Match that block (or variations with parens) appearing 1 or more times
    # 3. \.pkl$               -> Must end with .pkl
    # This eats up "_8_10_8_9", "_8_10_8_9_8_10_8_9", "_(8_10_8_9)_8_10_8_9", etc.
    
    # We capture just the digits part in group 1 to reconstruct the clean version.
    mess_pattern = re.compile(r"((?:_|\()\d+_\d+_\d+_\d+(?:\))?)+\.pkl$")

    for root in STATE_ROOTS:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir(): continue
            
            for f in date_dir.iterdir():
                if not f.name.endswith(".pkl"): continue
                
                # Check if this file has the allocator pattern at all
                match = mess_pattern.search(f.name)
                if not match: 
                    continue

                # Extract the numbers from the match string
                # We find the first occurrence of "d_d_d_d" in the matched tail
                # This is the "source of truth" numbers
                tail = match.group(0)
                nums_search = re.search(r"(\d+_\d+_\d+_\d+)", tail)
                
                if not nums_search:
                    print(f"⚠️ Matched pattern but found no digits? {f.name}")
                    continue
                    
                digits = nums_search.group(1) # e.g. "8_10_8_9"
                
                # Construct the CLEAN tail
                clean_tail = f"({digits}).pkl"
                
                # Replace the entire dirty tail with the clean tail
                new_name = mess_pattern.sub(clean_tail, f.name)
                
                if new_name == f.name:
                    continue # Already clean
                
                new_path = date_dir / new_name
                
                print(f"🔧 FIXING: {f.name}")
                print(f"   →     {new_name}")
                
                try:
                    # If target exists (deduplication), remove it first
                    if new_path.exists():
                        new_path.unlink()
                        
                    f.rename(new_path)
                    fixed += 1
                except Exception as e:
                    print(f"   ❌ ERROR: {e}")

    print(f"\n🔥 DONE. Fixed {fixed} files.")

if __name__ == "__main__":
    fix_files_aggressive()
