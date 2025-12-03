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

def fix_double_underscores():
    print("🧹 STARTING SIMPLE CLEANUP: Replacing '__' with '_' ...")
    fixed = 0
    
    for root in STATE_ROOTS:
        root = Path(root)
        if not root.exists(): continue

        for date_dir in root.iterdir():
            if not date_dir.is_dir(): continue
            
            for f in date_dir.iterdir():
                if not f.name.endswith(".pkl"): continue
                
                if "__" in f.name:
                    new_name = f.name.replace("__", "_")
                    new_path = date_dir / new_name
                    
                    print(f"FIXING: {f.name}")
                    print(f"   →    {new_name}")
                    
                    try:
                        if new_path.exists():
                            new_path.unlink() # Dedupe if target exists
                            
                        f.rename(new_path)
                        fixed += 1
                    except Exception as e:
                        print(f"   ❌ ERROR: {e}")

    print(f"\n🧹 DONE. Fixed {fixed} files.")

if __name__ == "__main__":
    fix_double_underscores()