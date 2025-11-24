# Troubleshooting Guide

Real issues encountered during development and their solutions.

---

## Table of Contents

1. [Data Lake & Storage Issues](#data-lake--storage-issues)
2. [Import & Installation Issues](#import--installation-issues)
3. [Drive & Network Issues](#drive--network-issues)
4. [Performance & Memory Issues](#performance--memory-issues)
5. [Model Loading & State Issues](#model-loading--state-issues)
6. [Framework-Specific Issues](#framework-specific-issues)

---

## Data Lake & Storage Issues

### Issue: "No saved state at /content/drive/.../Oracle(...).pkl"

**Symptoms**:
```
[WARN] No saved state at /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/model_state/day_20251124/Oracle(hybrid)_16000-Default_Stochastic_Random-4000.pkl
⚠️  Oracle model not found, using manual fallback...
```

**What's happening**:
- This is **NORMAL for a cold start** — first time running a specific model configuration.
- The system doesn't have a pre-trained model to resume from, so it trains one from scratch.
- Once training completes, the model is saved, and next time you run, the warning disappears.

**Solution**:
- **Ignore the warning** if this is your first run.
- **If you expected the file to exist**, check:
  1. Did you run the experiment yesterday or on a different date?
     - Files are organized by date: `day_YYYYMMDD/`
     - If your previous run was `day_20251123` but today is `day_20251124`, files are in the old folder.
     - Solution: Either re-run today's experiment or point the framework to load from the previous date's folder.
  2. Are the file names exactly the same?
     - The framework generates filenames based on model type, specs, and run ID.
     - If config changed even slightly (e.g., `attack_intensity` changed), the filename changes and old files won't be found.
     - Check the data lake folder directly to see what files actually exist.

**Technical detail**: See "Model Loading & State Issues" below for how the registry works.

---

### Issue: "Shared Drive not detected" / "quantum_data_lake not found"

**Symptoms**:
```
❌ Shared Drive NOT detected. Are you mounted?
FileNotFoundError: [Errno 2] No such file or directory: '/content/drive/Shareddrives/ai_quantum_computing'
```

**Cause**:
- You haven't mounted Google Drive, OR
- You mounted Drive but with the wrong account, OR
- The shared drive path is different.

**Solution**:

**If in Colab**:
```python
from google.colab import drive
drive.mount('/content/drive')
```
Then authenticate with your **institutional Google account** (not personal Gmail).

**If on local machine**:
- Install Google Drive for desktop or `google-drive-ocamlfuse`
- See [SETUP_LOCAL.md → Sync to Shared Drive](SETUP_LOCAL.md#optional-sync-to-shared-drive)

**If on GCP VM**:
```bash
google-drive-ocamlfuse ~/drive
# Then update the path in your code:
# SHARED_DRIVE_PATH = Path(os.path.expanduser("~/drive/My Drive/ai_quantum_computing/quantum_data_lake"))
```

---

### Issue: "Permission denied" when writing to data lake

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '/content/drive/.../quantum_data_lake/model_state/...'
```

**Cause**:
- You have read access to the shared drive but not write access.

**Solution**:
- Contact the shared drive owner and request **Editor** role
- You need: Editor (or Contributor) permissions, not just Viewer

---

## Import & Installation Issues

### Issue: "ModuleNotFoundError: No module named 'daqr'"

**Symptoms**:
```
ModuleNotFoundError: No module named 'daqr'
```

**Cause**:
- Virtual environment not activated (local setup), OR
- Dependencies not installed, OR
- Running from wrong directory

**Solution**:

**Local machine**:
```bash
# Activate venv
source venv/bin/activate        # Linux/Mac
# OR
venv\Scripts\activate           # Windows

# Reinstall deps if needed
pip install -r requirements.txt

# Then run from repo root
cd quantum_project
python your_script.py
```

**Colab**:
```python
# Add to first cell:
!pip install -q -r requirements.txt
import sys
# Make sure this path matches where quantum_project lives in your Shared Drive
sys.path.insert(0, '/content/drive/Shareddrives/ai_quantum_computing/quantum_project')

# Then import should work
from daqr.config.experiment_config import ExperimentConfiguration
```

---

### Issue: "ImportError: cannot import name 'QuantumEvaluatorVisualizer'"

**Symptoms**:
```
ImportError: cannot import name 'QuantumEvaluatorVisualizer' from 'daqr.evaluation.visualizer'
```

**Cause**:
- Class name mismatch. The actual class in `visualizer.py` might be named differently.

**Solution**:
Check what's actually exported:
```python
from daqr.evaluation import visualizer
print(dir(visualizer))  # See all classes
```

Then use the correct name. Common ones:
- `QuantumEvaluatorVisualizer` ✅
- `QuantumExperimentVisualizer` ✅
- `VisualizerV2` (older naming)

---

### Issue: "No module named 'google.colab'" (outside Colab)

**Symptoms**:
```
ModuleNotFoundError: No module named 'google.colab'
```

**Cause**:
- You're running code that imports `google.colab` on a local machine (not Colab).

**Solution**:
The `google.colab` module only exists in Colab. If running locally, wrap the import:
```python
try:
    from google.colab import drive
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    drive.mount('/content/drive')
```

---

## Drive & Network Issues

### Issue: "Timeout error" when uploading/downloading from Drive

**Symptoms**:
```
TimeoutError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Cause**:
- Slow internet connection, OR
- Drive API rate limiting, OR
- Large file transfer

**Solution**:
1. **Check internet**: `ping google.com`
2. **Reduce file size**: Large model checkpoints take time to upload.
   - The framework already chunks uploads, but if transfers keep timing out:
   - Try uploading during off-peak hours
3. **Local workaround**: Work locally first, then sync to Drive later.

---

### Issue: "Colab session terminated unexpectedly"

**Symptoms**:
```
⚠️  Your session crashed for an unknown reason.
```

**Cause**:
- Colab idle timeout (30 min of inactivity), OR
- Out of memory (OOM), OR
- GPU disconnected

**Solution**:

**If it's just a timeout**:
- Click "Reconnect" when prompted
- The framework will automatically **resume from the last checkpoint**
- You'll see: `🔄 Resuming from checkpoint: 50% complete`

**If it's OOM**:
```python
# Reduce memory usage:
config = ExperimentConfiguration(
    models=["Oracle"],           # Fewer models
    base_frames=2000,            # Smaller history
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=1,                      # Fewer runs
    max_workers=1,               # Single threaded
)
```

**If GPU disconnected**:
- Colab randomly disconnects GPUs. Just re-run and let it resume.

---

## Performance & Memory Issues

### Issue: "CUDA out of memory"

**Symptoms**:
```
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB
```

**Cause**:
- Model too large for GPU, OR
- Too many runs in parallel, OR
- `base_frames` is too large

**Solution**:

**Immediate fix**:
```python
# Use CPU instead
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Force CPU

# Or reduce batch size:
config = ExperimentConfiguration(
    base_frames=2000,   # Reduce from 4000
)
```

**Better fix**:
```python
# Smaller models / fewer runs
config = ExperimentConfiguration(
    models=["Oracle"],  # Just oracle, not full suite
    base_frames=4000,
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=2,             # Reduce parallel runs
    max_workers=1,      # Single threaded
)
```

---

### Issue: "Colab runs very slowly"

**Symptoms**:
- Each experiment takes 2-3x longer than expected

**Common causes**:
1. **Not using GPU**: Check `!nvidia-smi`
2. **Registry not cached**: First run scans all folders
3. **Shared Drive latency**: Especially if many files exist

**Solution**:

1. **Ensure GPU is enabled**:
   - Colab → Runtime → Change runtime type → GPU (T4)

2. **Ensure registry is built**:
   - First run builds the registry file (slow)
   - Subsequent runs are fast
   - If still slow after first run, the registry file might be corrupted → delete it:
     ```python
     import os
     os.remove("quantum_data_lake/backup_registry.json")
     # Restart your cell — registry will rebuild
     ```

3. **Check Drive mount latency**:
   ```python
   import time
   start = time.time()
   with open("/content/drive/Shareddrives/test.txt", "w") as f:
       f.write("test")
   elapsed = time.time() - start
   print(f"Drive write latency: {elapsed:.2f}s")
   # If > 1s per operation, Drive is slow. Try local mode instead.
   ```

---

## Model Loading & State Issues

### Issue: "Registry is corrupted" / "Files keep getting re-created"

**Symptoms**:
- Files are being re-created every run even though they already exist
- The registry (registry file) isn't being written

**What's happening**:
The framework maintains a `backup_registry.json` that maps filenames → paths. This makes lookups fast (O(1)) instead of scanning all folders (O(n)).

If the registry is missing or corrupted:
1. Files still exist on disk
2. But lookups fail because the registry says they don't
3. So the system re-creates them (wastes time + space)

**Solution**:

**Delete and rebuild the registry**:
```bash
rm quantum_data_lake/backup_registry.json
# Next run will rebuild it from scratch
```

Or in Python:
```python
import os
from pathlib import Path

registry_path = Path("quantum_data_lake/backup_registry.json")
if registry_path.exists():
    os.remove(registry_path)
    print("✅ Registry deleted. Next run will rebuild it.")
```

**If this happens repeatedly**, it means the registry isn't being persisted properly. Check:
- Is `_save_registry_to_gcs()` being called?
- Is `in_share_drive` set correctly?
- Do you have write permissions to the data lake?

---

### Issue: "day_day_" or double-prefix folder names

**Symptoms**:
```
quantum_data_lake/framework_state/day_day_20251124/  ← Extra "day_"
quantum_data_lake/framework_state/day_20251124/      ← Correct
```

**What this was**: A bug where the date prefix was being added twice.

**Status**: ✅ **FIXED** in recent commits (we removed the `normalize_day_prefix()` regex logic).

**If you see this**:
- It's from old runs before the fix
- Safe to delete: `rm -rf quantum_data_lake/*/day_day_*`
- Future runs won't create `day_day_` folders

---

### Issue: "Models saved with wrong filename, can't resume"

**Symptoms**:
- Models saved as: `NeuralUCB.pkl`
- Framework looks for: `NeuralUCB_0(hybrid)_16000-Default-4000.pkl`
- Mismatch → model not found

**Cause**:
- The `QuantumModel` subclass doesn't include run ID or specs in its filename

**Solution**:
Ensure your model's `file_name` property includes all the specs:
```python
class MyModel(QuantumModel):
    def __init__(self, run_id, specs, ...):
        super().__init__(...)
        self.run_id = run_id
        self.specs = specs
        # Include everything in the filename
        self.file_name = f"{self.__class__.__name__}_{run_id}_{specs}.pkl"
```

---

## Framework-Specific Issues

### Issue: "Experiment runner hangs" / "Process not terminating"

**Symptoms**:
- Experiment seems to finish but process doesn't exit
- Colab cell stays running forever

**Cause**:
- Thread cleanup incomplete
- Deadlock in multi-run evaluation

**Solution**:
```python
# Add explicit shutdown
evaluator = MultiRunEvaluator(configs=config, runs=5)
results = evaluator.run_multi_model_evaluation()

# Force cleanup
import gc
gc.collect()

print("✅ Complete")
```

Or kill the hung process:
```bash
# Find Python process
ps aux | grep python

# Kill it
kill -9 <pid>
```

---

### Issue: "Results don't match between Colab and local"

**Symptoms**:
- Same config produces different `Reward` and `Efficiency` numbers on different machines

**Cause**:
- Different random seeds
- Different PyTorch/NumPy versions
- GPU vs CPU (floating-point differences)

**Solution**:
Results **should** be deterministic with the same seed. Check:
```python
config = ExperimentConfiguration(...)

evaluator = MultiRunEvaluator(
    configs=config,
    base_seed=12345,  # Fix the seed
    runs=3,
)
```

If results still differ:
1. Check PyTorch versions: `torch.__version__`
2. Check NumPy: `np.__version__`
3. Align them across machines

---

## Getting Help

If your issue isn't here:

1. **Check the logs**: Print debug output with `verbose=True`
   ```python
   config = ExperimentConfiguration(verbose=True, ...)
   ```

2. **Share the error**: Include:
   - Full error traceback
   - Your config (models, attack_type, etc.)
   - Whether it's Colab, local, or GCP
   - Colab log showing the full error

3. **Check the data lake**: Sometimes issues are obvious when you look at actual files:
   ```bash
   ls -la quantum_data_lake/model_state/day_20251124/
   # Are the files there? Are they corrupted?
   ```

4. **Use verbose mode**:
   ```python
   from daqr.config.experiment_config import ExperimentConfiguration
   config = ExperimentConfiguration(verbose=True, ...)
   ```
   This prints detailed path checks and file existence checks.

---

## Summary Checklist

Before opening an issue, verify:

- [ ] I'm using the correct Python version (3.10+)
- [ ] Dependencies are installed: `pip install -r requirements.txt`
- [ ] Virtual environment is activated (local only)
- [ ] Google Drive is mounted (Colab/GCP)
- [ ] I have Editor permissions on the shared drive
- [ ] My config uses a fixed `base_seed` for reproducibility
- [ ] I ran with `verbose=True` to see detailed logs
- [ ] I checked if it's a "cold start" warning (expected behavior)
- [ ] I checked if old `day_day_` folders are causing issues
- [ ] I deleted and rebuilt the registry (`backup_registry.json`)