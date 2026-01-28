# Local Development & GCP Setup Guide

Use this guide to run the framework on your local machine (Linux/Mac/Windows) or on a GCP VM for large-scale batch runs.

***

## Table of Contents

1. [Local Setup (Your Machine)](#local-setup-your-machine)  
2. [Running Tests Locally](#running-tests-locally)  
3. [Optional: Sync to Shared Drive](#optional-sync-to-shared-drive)  
4. [GCP VM Setup](#gcp-vm-setup)  
5. [Development Workflow](#development-workflow)  
6. [Performance Tips](#performance-tips)  

***

## Local Setup (Your Machine)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd quantum_mab_research
```

### Step 2: Create Virtual Environment

**Python 3.10+** is required.

```bash
# Check your Python version
python --version  # Should be 3.10 or higher

# Create venv
python -m venv venv

# Activate it
source venv/bin/activate      # Linux/Mac
# OR
venv\Scripts\activate         # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output**:
```text
Successfully installed torch torchaudio torchvision numpy scipy pandas ...
```

**If PyTorch fails to install** (common on M1 Macs or older GPU systems):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

(This uses CPU-only PyTorch, which is fine for testing. Production runs should use GPU.)

### Step 4: Verify Installation

```bash
python -c "import daqr; print('✅ DAQR installed correctly')"
```

***

## Running Tests Locally

### Quick Sanity Check (5 minutes)

```bash
bash scripts/run_exp_test.sh
```

**Expected output** (approximate):

```text
✅ Data Lake found: /path/to/quantum_data_lake
🔄 Starting Oracle...
EXP 1 ORACLE: Reward=2156.42, Efficiency=077.8% [Retries=0, Failed=0]
✅ Test complete. Results saved to: quantum_data_lake/framework_state/day_YYYYMMDD/
```

By default, results save to `./quantum_data_lake/` in your repo root (local-only). To sync with teammates, see [Optional: Sync to Shared Drive](#optional-sync-to-shared-drive).

### Run the Paper2 Validation Suite (Full Check)

This runs the 8-test validation suite for the Paper2 production testbed and takes 2–3 hours.

```bash
bash scripts/paper2_test_suite.sh
```

This validates all stochastic and adversarial scenarios across the core models (Oracle, EXPNeuralUCB, GNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB) using the current configuration defaults. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

### Run a Custom Experiment

```bash
python << 'EOF'
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

# Create a default configuration (Paper2-style physics & models if your testbed is set that way)
config = ExperimentConfiguration(
    models=None,   # None → use default research models (Oracle, GNeuralUCB, EXPNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB)
    scenarios=None # None → use default test scenarios (stochastic + baseline)
)

# Quick stochastic run with 4000 frames
evaluator = MultiRunEvaluator(
    configs=config,
    runs=2,          # Quick test with 2 seeds
    baseframes=4000, # Note: parameter name is baseframes
)

evaluator.run_multi_model_evaluation()
print("✅ Experiment complete")
EOF
```

By default, the configuration will evaluate EXPNeuralUCB, GNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB, and Oracle if you do not override the `models` list. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

**On Windows PowerShell**: The `<< 'EOF'` heredoc syntax will not work. Instead, either:

- Use Git Bash or WSL (Windows Subsystem for Linux), or  
- Paste the Python code into a `test_experiment.py` file and run `python test_experiment.py`

### Run Visualizer

After an experiment completes:

```bash
python << 'EOF'
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer
from pathlib import Path

# Base path where framework_state results are stored
base_path = Path("quantum_data_lake/framework_state")

# Find the latest "day_YYYYMMDD" directory
day_dirs = sorted(base_path.glob("day_*"))
if not day_dirs:
    raise RuntimeError(f"No results found under {base_path}")
latest_day = day_dirs[-1]

print(f"Loading results from: {latest_day}")

viz = QuantumEvaluatorVisualizer()

# Load previously saved experiment results (pickle by default)
results = viz.load_experiment_results(str(latest_day), load_format="pickle")

# Store them in the visualizer for plotting
viz.evaluation_results = results

# Create comparison plots (e.g., stochastic vs baseline)
viz.plot_scenarios_comparison(scenario="stochastic")

print("✅ Visualizations complete (check the 'results' folder under that day directory)")
EOF
```

**On Windows PowerShell**: Use Git Bash, WSL, or save this as `visualize.py` and run `python visualize.py`.

***

## Optional: Sync to Shared Drive

If you want your **local runs to write to the shared drive** (so the whole team can see your results), configure the data lake path.

### Option A: Google Drive Desktop (Easiest on Mac/Windows)

1. Install [Google Drive for desktop](https://support.google.com/drive/answer/10838124)  
2. Add the lab shared drive to *My Drive*  
3. Google Drive mounts it locally. On macOS this is usually something like:

   ```bash
   /Volumes/GoogleDrive/Shared drives/ai_quantum_computing/
   ```

Then, in your Python code:

```python
from pathlib import Path
from daqr.config.experiment_config import ExperimentConfiguration

# Point to the mounted shared drive quantum data lake
SHARED_DRIVE_PATH = Path(
    "/Volumes/GoogleDrive/Shared drives/ai_quantum_computing/quantum_data_lake"
)

config = ExperimentConfiguration(
    models=None,           # use defaults
    scenarios=None         # use defaults
)
config.backupmgr.quantumdatapaths['frameworkstate'] = SHARED_DRIVE_PATH
```

### Option B: Google Drive CLI (Linux servers)

1. Install `google-drive-ocamlfuse`:

```bash
# Ubuntu/Debian
sudo apt-get install -y google-drive-ocamlfuse

# macOS (Homebrew)
brew install macfuse google-drive-ocamlfuse
```

2. Authenticate and mount:

```bash
google-drive-ocamlfuse ~/drive
```

3. In your code:

```python
import os
from pathlib import Path
from daqr.config.experiment_config import ExperimentConfiguration

SHARED_DRIVE_PATH = Path(
    os.path.expanduser("~/drive/Shared drives/ai_quantum_computing/quantum_data_lake")
)

config = ExperimentConfiguration()
config.backupmgr.quantumdatapaths['frameworkstate'] = SHARED_DRIVE_PATH
```

### Option C: Local-Only (Default, No Sync)

By default, results save to `./quantum_data_lake/`. This is **fine for development** — just remember results will not be visible to teammates until you manually upload them or sync.

***

## GCP VM Setup

Use this for **large-scale batches** or **long-running experiments**.

### Step 1: Create a GCP VM

```bash
gcloud compute instances create quantum-exp-runner \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=n1-standard-4 \
  --zone=us-central1-a \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --provisioning-model=SPOT \
  --boot-disk-size=50GB \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```

### Step 2: SSH Into the VM

```bash
gcloud compute ssh quantum-exp-runner --zone=us-central1-a
```

### Step 3: Run the Startup Script

The startup script should:

- Install system dependencies (Python, build tools)  
- Install PyTorch (CPU or GPU)  
- Clone this repository  
- Set up the quantum data lake paths  

```bash
cd /tmp
# Replace <your-org> and repo path with the actual GitHub URL
curl -O https://raw.githubusercontent.com/<your-org>/quantum_mab_research/main/scripts/1_startup.sh
bash 1_startup.sh
```

(Or manually run the steps below.)

### Step 4: Manual Setup (If Startup Script Not Available)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv build-essential

# Clone repo
cd /home/$(whoami)
git clone <repository-url>
cd quantum_mab_research

# Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If you want this VM to sync to the same shared quantum data lake as your local environment, mount Google Drive (or configure GCS) as described in the previous section.

### Step 5: Run Batch Experiments

```bash
# Single large batch
bash scripts/dynamic_exp_runner.sh \
  --models="Oracle,EXPNeuralUCB,NeuralUCB" \
  --runs=20 \
  --attack_type="Adaptive" \
  --attack_intensity=0.5

# Or run multiple attack types in sequence
for attack in NoAttack Random Markov Adaptive; do
  bash scripts/dynamic_exp_runner.sh \
    --models="EXPNeuralUCB" \
    --runs=10 \
    --attack_type=$attack
done
```

### Step 6: Push Results Back to Shared Drive

```bash
bash scripts/3_push_results.sh --push
```

This uploads all results to something like:

```text
ai_quantum_computing/quantum_data_lake/framework_state/day_YYYYMMDD/
ai_quantum_computing/quantum_data_lake/model_state/day_YYYYMMDD/
```

### Step 7: Clean Up VM

```bash
# Stop the VM (don't delete yet, in case you need to check logs)
gcloud compute instances stop quantum-exp-runner --zone=us-central1-a

# Delete when fully done
gcloud compute instances delete quantum-exp-runner --zone=us-central1-a
```

***

## Development Workflow

### Edit the Code

Use your favorite editor (VS Code, PyCharm, etc.):

```bash
code .     # VS Code
# or
pycharm .  # PyCharm
```

### Run Tests After Changes

```bash
# Quick smoke test
bash scripts/run_exp_test.sh
```

Or with a custom configuration:

```bash
python << 'EOF'
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

config = ExperimentConfiguration(
    models=["Oracle"],
    scenarios={"stochastic": "Stochastic Environment"}
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=1,
    baseframes=4000,
)

evaluator.run_multi_model_evaluation()
EOF
```

**On Windows PowerShell**: Save as `test.py` and run `python test.py`.

### Debug with Print Statements

The framework has verbose logging you can enable:

```python
from daqr.config.experiment_config import ExperimentConfiguration

config = ExperimentConfiguration(
    verbose=True,
    models=["Oracle"],
)
```

You will see messages like:

```text
🔎 Looking for: model_state/Oracle(hybrid)_16000...
Checking FS: /path/to/quantum_data_lake/model_state/day_20260124/...
✓ Found via filesystem: /path/to/...
```

### Profile Performance

```bash
python -m cProfile -s cumtime << 'EOF'
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

config = ExperimentConfiguration(models=["Oracle"])
evaluator = MultiRunEvaluator(configs=config, runs=1)
evaluator.run_multi_model_evaluation()
EOF
```

**On Windows PowerShell**: Save as `profile.py` and run:

```bash
python -m cProfile -s cumtime profile.py
```

***

## Performance Tips

### Faster Experiment Development

- Use smaller frame counts during debugging:

  ```python
  baseframes = 1000  # Instead of 4000
  ```

- Use fewer runs:

  ```python
  runs = 1  # Increase later for full validation
  ```

- Test a single model first:

  ```python
  config = ExperimentConfiguration(models=["Oracle"])
  ```

### GPU Usage

Check if GPU is available:

```bash
# Linux/Mac
nvidia-smi -l 1  # Refresh every 1 second
```

In Python:

```python
import torch
print(f"GPU available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
```

### Multi-Run Parallelization

`MultiRunEvaluator` supports multi-threaded execution of runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

```python
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
from daqr.config.experiment_config import ExperimentConfiguration

config = ExperimentConfiguration()
evaluator = MultiRunEvaluator(
    configs=config,
    runs=5,
    baseframes=4000,
    maxworkers=4,  # Use up to 4 worker threads
)
evaluator.run_multi_model_evaluation()
```

***

## Troubleshooting

| Issue                                         | Solution |
|----------------------------------------------|----------|
| `ModuleNotFoundError: No module named 'daqr'` | Ensure `venv` is activated and you are in the repo root (`quantum_mab_research/`). |
| `CUDA out of memory`                         | Reduce `baseframes`, lower `runs`, or switch to CPU-only PyTorch. |
| Drive mount fails                            | Re-authenticate Google Drive, confirm shared drive permissions, and re-run mount. |
| Results not syncing to Drive                 | Confirm the mounted path matches what `ExperimentConfiguration.backupmgr` is using; check mount with `mount \| grep drive`. |

For more, see [`setup_files/TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md).

***

## Next Steps

- **Run your first experiment locally**: `bash scripts/run_exp_test.sh`  
- **Run the full Paper2 validation**: `bash scripts/paper2_test_suite.sh`  
- **Modify code and test iteratively**: Edit `daqr/` files and re-run  
- **Scale to GCP** when ready for large batches  
- **Share results** by syncing to the shared quantum data lake so your team can access them.