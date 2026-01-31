# Google Colab Setup Guide

This is the fastest way to run experiments using our shared infrastructure. No local installation needed — everything runs on a free GPU (usually T4) and data syncs instantly to the shared drive. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

***

## Table of Contents

1. [Access the Notebook](#access-the-notebook)  
2. [Mount Google Drive](#mount-google-drive)  
3. [Install Dependencies](#install-dependencies)  
4. [Run Your First Experiment](#run-your-first-experiment)  
5. [Expected Output](#expected-output)  
6. [Common Configurations](#common-configurations)  
7. [Monitoring & Resuming](#monitoring--resuming)  
8. [Sharing Results](#sharing-results)  

***

## Access the Notebook

### Step 1: Find the Shared Drive

1. Open [Google Drive](https://drive.google.com)  
2. Click **“Shared drives”** on the left sidebar  
3. Look for **`ai_quantum_computing`**

### Step 2: Navigate to Notebooks

Inside the shared drive, go to:

```text
ai_quantum_computing → quantum_mab_research → notebooks/
```

You should see (at least) these notebooks:

| Notebook | Purpose |
|----------|---------|
| `Quantum_MAB_Research_Sandbox(PROD).ipynb` | **Use this for paper runs and official experiments** |
| `Quantum_MAB_Research_Sandbox(DEV).ipynb` | Development / testing new features |
| `Quantum_MAB_Research_Sandbox(TEST).ipynb` | Quick validation of framework changes |
| `H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb` | Clean testbed + advanced evaluation workflow (Paper2, Paper7, Paper12)  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb) |

**Recommended**: Start with `(TEST)` for your first run, then move to `(PROD)` or the `H-MABs_Eval-...` notebook for serious experiments and paper-grade runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Step 3: Open in Colab

Right-click on a notebook → **“Open with”** → **“Google Colaboratory”**

(Or double-click to open in Drive, then click the Colab icon in the preview.)

***

## Mount Google Drive

When the notebook loads, the first cell should handle Drive mounting automatically: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

```python
from google.colab import drive
drive.mount('/content/drive')
```

**Expected behavior**:

- Click the link and authorize with your institutional account  
- You should see: `Mounted at /content/drive`

**If it fails**:

- Make sure you are using your **institutional Google account** (the one with Drive access)  
- If you are logged in to a personal account, sign out and use the institutional one  
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help  

***

## Install Dependencies

Most notebooks include an install cell similar to: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

```python
!pip install -q torch torchvision numpy matplotlib seaborn pandas tqdm scipy scikit-learn pmdarima
```

This installs:

- PyTorch (with CUDA support in Colab)  
- NumPy, SciPy, Pandas  
- scikit-learn, pmdarima  
- matplotlib, seaborn, tqdm  

**Expected time**: ~2–3 minutes on first run (cached after that)

**Expected output**:

```text
Successfully installed torch torchvision numpy matplotlib seaborn pandas ...
```

***

## Run Your First Experiment

The Colab notebook will have a **Configuration** cell. To align with the current framework APIs, use this pattern: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

```python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

# ============================================================
# EXPERIMENT CONFIGURATION
# ============================================================

config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB"],                    # algorithms
    scenarios={"stochastic": "Stochastic Environment"},   # scenario dict
    attacktype="random",                                  # 'random','markov','adaptive','onlineadaptive'
    attackintensity=0.0625,                               # severity 0.0–1.0
    verbose=True                                          # optional: more logging
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=3,                # Small test: 3 random seeds
    baseframes=4000,       # NOTE: baseframes, not base_frames
    framestep=2000,        # NOTE: framestep, not frame_step
    baseseed=12345         # Base random seed
)

results = evaluator.run_multi_model_evaluation()
```

Key details:

- `ExperimentConfiguration` uses `attacktype` and `attackintensity` (no underscore), and internally maps attack names like `"random"`, `"stochastic"`, `"markov"`, `"adaptive"`, `"onlineadaptive"` to specific attack strategies. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- `MultiRunEvaluator` expects `baseframes`, `framestep`, and `baseseed` — not `base_frames`, `frame_step`, or `base_seed.[file:25]  
- If `models` is `None`, it defaults to the core research set (Oracle, EXPNeuralUCB, GNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f0b88307-b546-4aaf-bb26-340024b2a9b8/predictive_bandits.py)

### Run the Cell

Click the **▶ Play button** or press **Ctrl+Enter**.

You should see progress messages for each model, for example:

```text
🔄 STOCHASTIC (random) EXP 1: Starting Oracle in sequence...
EXP 1 ORACLE              : Reward=2156.42, Efficiency=077.8% [Retries=0, Failed=0]

🔄 STOCHASTIC (random) EXP 1: Starting EXPNeuralUCB in sequence...
EXP 1 EXPNEURALUCB        : Reward=2402.09, Efficiency=086.9% [Retries=0, Failed=0]
```

***

## Expected Output

### During the Run

You should see log messages similar to:

```text
✅ Shared Drive detected at: /content/drive/Shareddrives/ai_quantum_computing
✅ Data Lake found: /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake

Multi-Run Evaluator Initialized
Environment Type stochastic
Frame Range 4000 - 4000 step 2000
Models to evaluate 2 total
DYNAMIC ROUTING EVALUATION FRAMEWORK - CONFIGURATION
Configuration loaded successfully - Ready for model evaluation
```

If there are existing backups, the runner/evaluator may print resume messages like: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/89fd56de-fe2a-437c-8fa7-1f46a4d5a143/experiment_runner.py)

```text
🔄 QuantumExperimentRunner_1 Resuming state from: .../day_20260124/QuantumExperimentRunner_1_8000-Default_stochastic_random-4000_1.pkl
Oracle already processed
```

If you see `[WARN]`-style messages saying no saved state was found, followed by a fresh run, this is normal on a **cold start** for a new configuration. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

### After Completion

Results are saved under the shared quantum data lake, for example:

```text
/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state/day_YYYYMMDD/
```

You should see output like:

```text
📊 Results saved to: /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state/day_20260124/

✅ Experiment complete. Visualizations saved.
✅ Results available to all team members in the shared drive.
```

### Expected Runtime (Approximate)

| Configuration                            | Time      |
|------------------------------------------|-----------|
| 1 run, 1 model (Oracle)                 | ~10 min   |
| 3 runs, 2 models (Oracle + EXPNeuralUCB) | ~45 min   |
| 5 runs, 3 models (full comparison)      | ~2 hours  |

***

## Common Configurations

### Quick Test (5–10 minutes)

```python
config = ExperimentConfiguration(
    models=["Oracle"],
    scenarios={"stochastic": "Stochastic Environment"},
    attacktype="random",
    attackintensity=0.0625
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=1,
    baseframes=1000,
    framestep=500
)

results = evaluator.run_multi_model_evaluation()
```

### Standard Benchmark (≈45 minutes)

```python
config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB", "GNeuralUCB"],
    scenarios={"stochastic": "Stochastic Environment"},
    attacktype="random",
    attackintensity=0.0625
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=3,
    baseframes=4000,
    framestep=2000
)

results = evaluator.run_multi_model_evaluation()
```

### Adversarial Stress Test (≈2 hours)

```python
config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB", "GNeuralUCB", "CPursuitNeuralUCB"],
    scenarios={"adversarial": "Adversarial Environment"},
    attacktype="adaptive",
    attackintensity=0.5
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=5,
    baseframes=8000,
    framestep=4000
)

results = evaluator.run_multi_model_evaluation()
```

### Multiple Scenarios (Baseline + Stochastic)

```python
test_scenarios = {
    "stochastic": "Stochastic Environment",
    "none": "Baseline (Optimal Conditions)"
}

for atk in ["random", "markov", "adaptive"]:
    config = ExperimentConfiguration(
        models=["Oracle", "EXPNeuralUCB"],
        scenarios=test_scenarios,
        attacktype=atk,
        attackintensity=0.25
    )

    evaluator = MultiRunEvaluator(
        configs=config,
        runs=3,
        baseframes=4000
    )

    results = evaluator.run_multi_model_evaluation()
    print(f"✅ {atk} experiments complete")
```

***

## Monitoring & Resuming

### If Colab Times Out

The framework automatically **saves evaluator and runner state** to the quantum data lake via the `LocalBackupManager` / Drive-backed registry. If your Colab session disconnects: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)

1. Reconnect to the runtime  
2. Re-mount Drive (first cell)  
3. Re-run the configuration and evaluation cells  

The system will scan the registry and try to resume from compatible checkpoints:

```text
Resume-RegistrySet candidates ...
Resume-RegistrySet Trying file with qubits (8,10,8,9) ...
Resume-RegistrySet Successfully resumed from ...
```

If no compatible state is found, it falls back to a fresh run without losing existing results. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/89fd56de-fe2a-437c-8fa7-1f46a4d5a143/experiment_runner.py)

### Checking GPU Usage

In a Colab cell:

```python
!nvidia-smi
```

You should see a T4 or similar GPU with memory usage increasing during runs.

***

## Sharing Results

Once experiments complete, results are automatically saved to the shared drive:

```text
Shared drives → ai_quantum_computing → quantum_data_lake → framework_state → day_YYYYMMDD/
Shared drives → ai_quantum_computing → quantum_data_lake → model_state    → day_YYYYMMDD/
```

All team members with access to the shared drive can see and analyze these results. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Visualize Results in Colab

Add a visualization cell to your notebook:

```python
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer
from pathlib import Path

base_path = Path(
    "/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state"
)

day_dirs = sorted(base_path.glob("day_*"))
if not day_dirs:
    raise RuntimeError(f"No results found under {base_path}")
latest_day = day_dirs[-1]

print(f"Loading results from: {latest_day}")

viz = QuantumEvaluatorVisualizer()
results = viz.load_experiment_results(str(latest_day), load_format="pickle")
viz.evaluation_results = results

# Example: compare stochastic scenario
viz.plot_scenarios_comparison(scenario="stochastic")
```

The visualizer matches the environment and model layout used in your configuration and can also compare stochastic vs adversarial scenarios if those were run. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)

### Compare with Teammates’ Results

Since everyone writes to the same `quantum_data_lake/`, you can load different day directories and compare keys, metrics, or plots side-by-side.

***

## Troubleshooting

For common issues (import errors, Drive mount failures, attacktype mismatches, “No saved state” warnings):

👉 See **[`setup_files/TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md)**

Key checks:

- Ensure `attacktype` and `attackintensity` are spelled correctly and use supported values (`"random"`, `"stochastic"`, `"markov"`, `"adaptive"`, `"onlineadaptive"`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)
- Ensure you are using `baseframes`, `framestep`, `baseseed` for `MultiRunEvaluator`, not snake_case variants. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/f977fe86-d826-41c1-abb0-166453ab4b46/multi_run_evaluator.py)
- If resume fails repeatedly, try setting `overwrite=True` or `uselastbackup=False` in `ExperimentConfiguration` for a clean run. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/9cfc7097-542b-41e1-b6a6-7afcf774e1bb/experiment_config.py)

***

## Next Steps

- Modify the Colab configuration cell to match your experiment goals (models, scenarios, attack types).  
- Use the `H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb` notebook for testbed-specific physics (Paper2, Paper7, Paper12) and allocator experiments. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/162342791/db5ad413-cfb3-4532-a754-595d8ec6b673/H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb)
- Once comfortable in Colab, you can clone the repo locally and follow [`SETUP_LOCAL.md`](SETUP_LOCAL.md) for deeper development.