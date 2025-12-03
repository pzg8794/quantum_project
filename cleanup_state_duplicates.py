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

def fix_missing_underscore_before_paren():
    print("🔧 STARTING UNDERSCORE INSERTION (REGEX MODE)...")
    fixed = 0
    
    # Regex:
    # Capture digits (\d+) that are IMMEDIATELY followed by an opening parenthesis \(
    # This matches "10000(" in "Random-10000(8_10...)"
    pattern = re.compile(r"(\d+)\(")

    for root in STATE_ROOTS:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir(): continue
            
            for f in date_dir.iterdir():
                if not f.is_file() or not f.suffix == ".pkl": continue
                
                # Check if the file matches the "digit(" pattern
                if pattern.search(f.name):
                    
                    # Replace:
                    # \1 is the digits
                    # We insert "_" between \1 and "("
                    new_name = pattern.sub(r"\1_(", f.name)
                    
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

if __name__ == "__main__":
    fix_missing_underscore_before_paren()
