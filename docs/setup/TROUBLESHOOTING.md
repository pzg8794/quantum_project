# Troubleshooting Guide

Real issues encountered during development and their solutions.

***

## Table of Contents

1. [Data Lake & Storage Issues](#data-lake--storage-issues)  
2. [Import & Installation Issues](#import--installation-issues)  
3. [Drive & Network Issues](#drive--network-issues)  
4. [Performance & Memory Issues](#performance--memory-issues)  
5. [Model Loading & State Issues](#model-loading--state-issues)  
6. [Framework-Specific Issues](#framework-specific-issues)  

***

## Data Lake & Storage Issues

### Issue: “No saved state at ... Oracle(...).pkl”

**Symptoms**:

```text
[WARN] No saved state at /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/model_state/day_20251124/Oracle(hybrid)_16000-Default_Stochastic_Random-4000.pkl
⚠️  Oracle model not found, using manual fallback...
```

**What’s happening**:

- This is **normal for a cold start**: you are running a specific model + config combination for the first time, so there is no checkpoint to resume from yet. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/89fd56de-fe2a-437c-8fa7-1f46a4d5a143/experiment_runner.py)
- The system then trains from scratch and writes new model and evaluator state files into the appropriate `day_YYYYMMDD` directory. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)
- On later runs with the **same config**, the resume logic will find these files and skip recomputation. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

**Solution**:

- Ignore the warning on your **first run** for a new configuration.  
- If you **expected** a saved state to exist, check:

  1. **Date folder**  
     - Files are grouped by date like `model_state/day_YYYYMMDD/` and `framework_state/day_YYYYMMDD/`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
     - If your last run was on `day_20260124` but you are now on `day_20260125`, older files live in the previous folder.

  2. **Config drift**  
     - Filenames encode many config details: model, allocator, environment type, attack type, frame count, etc. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/c5d4d6a1-3114-4791-9abe-96de412b76ef/base_bandit.py)
     - If you changed things like `attacktype`, `attackintensity`, `baseframes`, or number of runs, the new filenames no longer match the old ones. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
     - Open the relevant `model_state/day_YYYYMMDD/` directory and compare actual filenames to what the warning references.

See [Model Loading & State Issues](#model-loading--state-issues) for more detail on how resume and filenames work.

***

### Issue: “Shared Drive not detected” / “quantum_data_lake not found”

**Symptoms**:

```text
❌ Shared Drive NOT detected. Are you mounted?
FileNotFoundError: [Errno 2] No such file or directory: '/content/drive/Shareddrives/ai_quantum_computing'
```

**Cause**:

- Google Drive is not mounted in Colab, or  
- The wrong Google account is used, or  
- The shared drive is mounted at a different path. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

**Solution**:

**In Colab**:

```python
from google.colab import drive
drive.mount('/content/drive')
```

- Authenticate with your **institutional** account that has access to `ai_quantum_computing`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

**On a local machine**:

- Install Google Drive for Desktop or a FUSE-based solution (e.g., `google-drive-ocamlfuse`), then point the framework’s data lake path at the mounted folder. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

**On a GCP VM**:

```bash
google-drive-ocamlfuse ~/drive
# Then, in Python:
from pathlib import Path
SHARED = Path('~/drive').expanduser() / 'Shared drives' / 'ai_quantum_computing' / 'quantum_data_lake'
```

Update `ExperimentConfiguration` or the backup manager to use that path for `framework_state` and `model_state` components. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

***

### Issue: “Permission denied” when writing to data lake

**Symptoms**:

```text
PermissionError: [Errno 13] Permission denied: '/content/drive/.../quantum_data_lake/model_state/...'
```

**Cause**:

- Your Google account has **view-only** access to the shared drive, so write attempts fail.

**Solution**:

- Ask the shared drive owner to grant you **Editor** (or equivalent) permissions so the framework can create and update state files. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

## Import & Installation Issues

### Issue: `ModuleNotFoundError: No module named 'daqr'`

**Symptoms**:

```text
ModuleNotFoundError: No module named 'daqr'
```

**Cause**:

- Virtual environment not activated (local), or  
- Dependencies not installed, or  
- You are running from the wrong working directory so `daqr/` is not on `sys.path`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/c5d4d6a1-3114-4791-9abe-96de412b76ef/base_bandit.py)

**Solution**:

**Local machine**:

```bash
# From repo root
cd quantum_mab_research

# Activate venv
source venv/bin/activate      # Linux/Mac
# OR
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Run
python your_script.py
```

**Colab**:

```python
!pip install -q -r requirements.txt

import sys
sys.path.insert(0, '/content/drive/Shareddrives/ai_quantum_computing/quantum_mab_research')

from daqr.config.experiment_config import ExperimentConfiguration
```

This ensures Python can import the `daqr` package from the cloned repository. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

***

### Issue: “ImportError: cannot import name 'QuantumEvaluatorVisualizer'”

**Symptoms**:

```text
ImportError: cannot import name 'QuantumEvaluatorVisualizer' from 'daqr.evaluation.visualizer'
```

**Cause**:

- The class name or import path is wrong.

**Solution**:

Inspect the module:

```python
from daqr.evaluation import visualizer
print([x for x in dir(visualizer) if 'Visualizer' in x])
```

Typical class is `QuantumEvaluatorVisualizer`, and you import it via:

```python
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer
```

This is the class used in the Colab and notebook workflows for loading and plotting results. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

### Issue: “No module named 'google.colab'” on local runs

**Symptoms**:

```text
ModuleNotFoundError: No module named 'google.colab'
```

**Cause**:

- Code that imports `google.colab` is being executed outside Colab.

**Solution**:

Guard the import:

```python
try:
    from google.colab import drive
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    drive.mount('/content/drive')
```

This keeps your local environment from failing while still supporting Colab mounts. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

## Drive & Network Issues

### Issue: Timeouts when reading/writing from Drive

**Symptoms**:

```text
TimeoutError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Cause**:

- Slow or unstable network, API throttling, or large file transfers to the shared drive.

**Solution**:

- Confirm network connectivity (e.g., `ping google.com`).  
- Avoid running huge batches in a single Colab session; break them into smaller runs so each upload is smaller.  
- If Drive is consistently slow, consider running locally or on GCP and syncing results in larger, less frequent batches. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

### Issue: “Colab session terminated unexpectedly”

**Symptoms**:

```text
⚠️  Your session crashed for an unknown reason.
```

**Cause**:

- Idle timeout, GPU preemption, or out-of-memory (OOM) errors.

**Solution**:

- If idle timeout or GPU reset: reconnect, remount Drive, and re-run config; the evaluator will attempt to resume from the latest compatible state using its registry. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/89fd56de-fe2a-437c-8fa7-1f46a4d5a143/experiment_runner.py)
- If OOM: reduce `baseframes`, `runs`, or number of models and use `maxworkers=1` to limit parallelism in `MultiRunEvaluator`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

Example:

```python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

config = ExperimentConfiguration(
    models=["Oracle"],
    attacktype="random",
    attackintensity=0.25
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=1,
    baseframes=2000,
    maxworkers=1
)

evaluator.run_multi_model_evaluation()
```

***

## Performance & Memory Issues

### Issue: `torch.cuda.OutOfMemoryError`

**Symptoms**:

```text
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate ...
```

**Cause**:

- Config is too heavy for the available GPU: too many frames, too many models, or too many runs in parallel. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

**Solution**:

- Short-term: switch to CPU:

  ```python
  import os
  os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
  ```

- Better: shrink the workload:

  ```python
  config = ExperimentConfiguration(
      models=["Oracle"],
      attacktype="random",
      attackintensity=0.25
  )

  evaluator = MultiRunEvaluator(
      configs=config,
      runs=1,
      baseframes=2000,
      maxworkers=1
  )
  ```

This reduces memory pressure while keeping the same logical experiment. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

***

### Issue: “Colab runs very slowly”

**Symptoms**:

- Each experiment is significantly slower than expected.

**Common causes**:

1. GPU is not actually enabled or used.  
2. First-time registry scanning over many files (initial run).  
3. High latency to the shared drive.

**Solution**:

1. **Enable GPU**: In Colab, Runtime → Change runtime type → GPU.  
2. **Accept first-run cost**: the local backup manager scans and builds `localbackupregistry.json` / `drivebackupregistry.json` the first time; later runs reuse this registry. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
3. If Drive seems very slow, consider running in **local-only mode** (writing to local disk) and syncing results later. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

## Model Loading & State Issues

### Issue: “Registry is corrupted” or “Files re-created every run”

**Symptoms**:

- Existing evaluator/model files are ignored and rerun every time.  
- Large scans of the data lake appear on each run instead of using cached registry information. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

**What’s happening**:

- The framework uses registry files to map logical keys (like “frameworkstate”/“modelstate”) to actual filenames and paths. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- These registries live under `daqr/config/` as `localbackupregistry.json` and `drivebackupregistry.json`, and optionally in the shared drive as `backupregistry.json` at the root of the quantum data lake. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- If a registry is missing or malformed, the framework falls back to a full filesystem scan and may not correctly match previously generated files. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

**Solution**:

Delete and rebuild the local registry:

```python
from pathlib import Path
import os

cfg_dir = Path("daqr/config")
local_reg = cfg_dir / "localbackupregistry.json"
drive_reg = cfg_dir / "drivebackupregistry.json"

for p in (local_reg, drive_reg):
    if p.exists():
        os.remove(p)
        print(f"Deleted {p}")

print("✅ Local registries removed. They will be rebuilt on next run.")
```

If there is a `backupregistry.json` file at the root of the quantum data lake, you can also remove it; the next run will reconstruct it from the current filesystem state. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

### Issue: “day_day_...” or weird day folder names

**Symptoms**:

```text
framework_state/day_day_20251124/
framework_state/day_20251124/
```

**Background**:

- Older versions had logic that sometimes double-prefixed the `day_` part of the directory name; more recent code uses a single `dayYYYYMMDD` or `day_YYYYMMDD` consistently. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

**Solution**:

- For new runs this should no longer occur.  
- You can safely delete obsolete `day_day_*` directories if present; keep the correctly formatted ones (`day_YYYYMMDD`).  

***

### Issue: “Models saved with wrong filename, can’t resume”

**Symptoms**:

- Saved model filenames don’t match what the loader expects, so resume never finds them.

**Cause**:

- Custom models or older code built filenames without including run ID, capacity, environment, or attack identifiers. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/c5d4d6a1-3114-4791-9abe-96de412b76ef/base_bandit.py)

**Solution**:

- Use the standardized filename generation in `QuantumModel.setfilename`, which includes mode, capacity, allocator, environment, attack, and frame number. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/c5d4d6a1-3114-4791-9abe-96de412b76ef/base_bandit.py)
- If you write a new model class, rely on the existing base class methods rather than hard-coding filenames.

***

## Framework-Specific Issues

### Issue: “Experiment runner hangs” or doesn’t terminate

**Symptoms**:

- Computation seems finished but the process/Colab cell never exits.

**Cause**:

- Lingering references, threads, or open file descriptors not fully cleaned up, especially after many runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/89fd56de-fe2a-437c-8fa7-1f46a4d5a143/experiment_runner.py)

**Solution**:

- After `run_multi_model_evaluation()`, explicitly trigger cleanup:

```python
results = evaluator.run_multi_model_evaluation()

import gc
gc.collect()

print("✅ Complete")
```

If a local Python process is stuck, identify and kill it with `ps`/`kill` on Linux or Task Manager on Windows.

***

### Issue: “Results differ between Colab and local”

**Symptoms**:

- Same config yields slightly different performance metrics on different machines.

**Cause**:

- Different library versions (PyTorch/NumPy), CPU vs GPU numerics, or different seeds. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

**Solution**:

- Fix seeds via the configuration and ensure consistent environments:

```python
config = ExperimentConfiguration(
    baseseed=12345,
    attacktype="stochastic",
    attackintensity=0.25
)
```

- Align PyTorch and NumPy versions across machines (`torch.__version__`, `np.__version__`).  
- Expect tiny floating-point differences across hardware; large discrepancies usually indicate a config change.

***

## Getting Help

If your issue isn’t covered here:

1. **Turn on verbose logging**:

   ```python
   from daqr.config.experiment_config import ExperimentConfiguration

   config = ExperimentConfiguration(
       verbose=True,
       attacktype="random",
       attackintensity=0.25
   )
   ```

   This prints detailed path checks, registry behavior, and environment setup. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

2. **Capture full traceback** and include:
   - Full error message  
   - Your `ExperimentConfiguration` arguments (models, attacktype, attackintensity, scenarios, baseframes, runs)  
   - Whether you’re in Colab, local, or GCP  
   - Relevant log snippets about registry/paths

3. **Inspect the data lake**:

   ```bash
   ls -la quantum_data_lake/model_state/day_YYYYMMDD/
   ls -la quantum_data_lake/framework_state/day_YYYYMMDD/
   ```

   Confirm files exist and are non-empty.

***

## Summary Checklist

Before opening an issue, verify:

- [ ] Python 3.10+ is in use.  
- [ ] `pip install -r requirements.txt` completed without errors.  
- [ ] Virtual environment is activated (local).  
- [ ] Google Drive is mounted (Colab/GCP) and the shared drive is visible.  
- [ ] You have **Editor** permissions on the shared drive.  
- [ ] `ExperimentConfiguration` uses consistent `attacktype`, `attackintensity`, `baseseed`, `baseframes`, and `runs` across machines. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- [ ] You enabled `verbose=True` at least once to see detailed log output. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- [ ] You checked if warnings are from a **cold start** (no prior state).  
- [ ] Old or malformed `day_day_*` folders are not confusing you.  
- [ ] Local and drive registries (`localbackupregistry.json`, `drivebackupregistry.json`, `backupregistry.json`) have been rebuilt if necessary. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)