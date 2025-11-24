# Google Colab Setup Guide

This is the fastest way to run experiments using our shared infrastructure. No local installation needed — everything runs on a free GPU (usually T4) and data syncs instantly to the shared drive.

---

## Table of Contents

1. [Access the Notebook](#access-the-notebook)
2. [Mount Google Drive](#mount-google-drive)
3. [Install Dependencies](#install-dependencies)
4. [Run Your First Experiment](#run-your-first-experiment)
5. [Expected Output](#expected-output)
6. [Common Configurations](#common-configurations)
7. [Monitoring & Resuming](#monitoring--resuming)
8. [Sharing Results](#sharing-results)

---

## Access the Notebook

### Step 1: Find the Shared Drive

1. Open [Google Drive](https://drive.google.com)
2. Click **"Shared drives"** on the left sidebar
3. Look for **`ai_quantum_computing`**

### Step 2: Navigate to Notebooks

Inside the shared drive, go to:
```
ai_quantum_computing → quantum_mab_research → notebooks/
```

You should see three notebooks:

| Notebook | Purpose |
|----------|---------|
| `Quantum_MAB_Research_Sandbox(PROD).ipynb` | **Use this for paper runs and official experiments** |
| `Quantum_MAB_Research_Sandbox(DEV).ipynb` | Development / testing new features |
| `Quantum_MAB_Research_Sandbox(TEST).ipynb` | Quick validation of framework changes |

**Recommended**: Start with `(TEST)` for your first run, then move to `(PROD)` for serious experiments.

### Step 3: Open in Colab

Right-click on a notebook → **"Open with"** → **"Google Colaboratory"**

(Or double-click to open in Drive, then click the Colab icon in the preview)

---

## Mount Google Drive

When the notebook loads, the first cell should handle Drive mounting automatically:

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
- See [Troubleshooting](TROUBLESHOOTING.md) for more help

---

## Install Dependencies

The notebook includes an install cell:

```python
!pip install -q -r requirements.txt
```

This installs:
- PyTorch (with CUDA support)
- NumPy, SciPy, Pandas
- Google API client (for Drive)
- scikit-learn, pmdarima, matplotlib, seaborn

**Expected time**: ~2–3 minutes on first run (cached after that)

**Expected output**:
```
Successfully installed torch torchaudio torchvision ... 
```

---

## Run Your First Experiment

Navigate to the **Configuration** cell in the notebook. It looks like this:

```python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

# ============================================================
# EXPERIMENT CONFIGURATION
# ============================================================

config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB"],
    scenarios={"stochastic": "Stochastic Environment"},
    attack_type="Random",
    attack_intensity=0.0625,
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=3,              # Small test: 3 random seeds
    base_frames=4000,
    frame_step=2000,
    base_seed=12345,
)

results = evaluator.run_multi_model_evaluation()
```

**Key parameters to adjust**:

| Parameter | Meaning | Example |
|-----------|---------|---------|
| `models` | Which algorithms to compare | `["Oracle", "EXPNeuralUCB", "NeuralUCB"]` |
| `scenarios` | Environment scenarios (dict) | `{"stochastic": "Stochastic Environment"}` |
| `attack_type` | Attack strategy | `"Random"`, `"Markov"`, `"Adaptive"` |
| `attack_intensity` | Severity (0.0–1.0) | `0.0625` (light) to `0.5` (heavy) |
| `runs` | Number of random seeds | `3` (quick test) to `10` (thorough) |
| `base_frames` | Total timesteps | `4000` (default) |

### Run the Cell

Click the **▶ Play button** or press **Ctrl+Enter**.

You should see **progress bars** for each model:

```
🔄 STOCHASTIC (RANDOM) EXP 1: Starting Oracle in sequence...
EXP 1 ORACLE              : Reward=2156.42, Efficiency=077.8% [Retries=0, Failed=0]

🔄 STOCHASTIC (RANDOM) EXP 1: Starting EXPNeuralUCB in sequence...
EXP 1 EXPNEURALUCB        : Reward=2402.09, Efficiency=086.9% [Retries=0, Failed=0]

🔄 STOCHASTIC (RANDOM) EXP 1: Starting NeuralUCB in sequence...
EXP 1 NEURALUCB           : Reward=2301.85, Efficiency=083.1% [Retries=0, Failed=0]
```

---

## Expected Output

### During the Run

You should see log messages like:

```
✅ Shared Drive detected at: /content/drive/Shareddrives/ai_quantum_computing
✅ Data Lake found: /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake

🔄 QuantumExperimentRunner_1 Resuming state from: .../day_20251124/QuantumExperimentRunner_1_8000-Default_Stochastic_Random-4000_1.pkl
Getting Oracle Rewards ...
Oracle already processed
```

**Note**: If you see `[WARN] No saved state at ...` followed by `⚠️ Oracle model not found, using manual fallback...`, **this is normal for a cold start**. If this is your **first time running this specific configuration**, the system is training fresh models from scratch. Next time you run, it will find them. See [Troubleshooting](TROUBLESHOOTING.md) for details.

### After Completion

Results are saved to:

```
/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state/day_YYYYMMDD/
```

You should see output like:

```
📊 Results saved to: /content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state/day_20251124/

✅ Experiment complete. Visualizations saved.
✅ Results available to all team members in the shared drive.
```

### Expected Runtime

| Configuration | Time |
|---------------|------|
| 1 run, 1 model (Oracle) | ~10 min |
| 3 runs, 2 models (Oracle + EXPNeuralUCB) | ~45 min |
| 5 runs, 3 models (full comparison) | ~2 hours |

---

## Common Configurations

### Quick Test (5 minutes)

```python
config = ExperimentConfiguration(
    models=["Oracle"],
    scenarios={"stochastic": "Stochastic Environment"},
    attack_type="Random",
    attack_intensity=0.0625,
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=1,
    base_frames=1000,
    frame_step=500,
)

results = evaluator.run_multi_model_evaluation()
```

### Standard Benchmark (45 minutes)

```python
config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB", "NeuralUCB"],
    scenarios={"stochastic": "Stochastic Environment"},
    attack_type="Random",
    attack_intensity=0.0625,
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=3,
    base_frames=4000,
    frame_step=2000,
)

results = evaluator.run_multi_model_evaluation()
```

### Adversarial Stress Test (2 hours)

```python
config = ExperimentConfiguration(
    models=["Oracle", "EXPNeuralUCB", "NeuralUCB", "CPursuitNeuralUCB"],
    scenarios={"adversarial": "Adversarial Environment"},
    attack_type="Adaptive",
    attack_intensity=0.5,
)

evaluator = MultiRunEvaluator(
    configs=config,
    runs=5,
    base_frames=8000,
    frame_step=4000,
)

results = evaluator.run_multi_model_evaluation()
```

### Multiple Scenarios (Comprehensive)

```python
test_scenarios = {
    "stochastic": "Stochastic Environment",
    "none": "Baseline (Optimal Conditions)"
}

for attack_type in ["Random", "Markov", "Adaptive"]:
    config = ExperimentConfiguration(
        models=["Oracle", "EXPNeuralUCB"],
        scenarios=test_scenarios,
        attack_type=attack_type,
        attack_intensity=0.25,
    )

    evaluator = MultiRunEvaluator(
        configs=config,
        runs=3,
        base_frames=4000,
    )

    results = evaluator.run_multi_model_evaluation()
    print(f"✅ {attack_type} experiments complete")
```

---

## Monitoring & Resuming

### If Colab Times Out

The framework automatically **saves state at regular intervals**. If your session disconnects:

1. **Reconnect** (Colab will prompt)
2. **Re-run the configuration cell**
3. The system will detect saved checkpoints and **resume automatically**

You'll see messages like:

```
🔄 QuantumExperimentRunner_1 Resuming state from: .../day_20251124/QuantumExperimentRunner_1_...
✅ Resuming from checkpoint: 50% complete
```

**No data is lost**.

### Checking GPU Usage

During runs, you can monitor GPU/CPU usage with:

```python
!nvidia-smi
```

You should see something like:

```
| GPU Name             Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| 0  Tesla T4              Off  | 00000000:00:04.0  Off |                    0 |
|  0%   38C    P0    25W / 70W |   1234MiB / 15360MiB |      0%      Default |
```

---

## Sharing Results

Once experiments complete, results are **automatically saved to the shared drive**:

```
Shared Drives → ai_quantum_computing → quantum_data_lake → framework_state → day_YYYYMMDD/
```

**All team members have instant access** — no need to download, email, or manually copy anything.

### Visualize Results in Colab

Add this cell to your notebook:

```python
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

# Define base path (absolute path in Colab)
base_path = "/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state"

# Point to a specific day's results
# Replace 20251124 with your actual run date (check "Expected Output" section above)
exp_dir = f"{base_path}/day_20251124"

viz = QuantumEvaluatorVisualizer()

# Load previously saved experiment results
results = viz.load_experiment_results(exp_dir, load_format='pickle')

# Store them in the visualizer for plotting
viz.evaluation_results = results

# Create comparison plots
viz.plot_scenarios_comparison(scenario="stochastic")

# For stochastic vs adversarial comparison:
# viz.plot_stochastic_vs_adversarial_comparison()
```

**For more plotting options**, see the docstrings in `daqr/evaluation/visualizer.py`, especially:
- `QuantumEvaluatorVisualizer.load_experiment_results(...)`
- `QuantumEvaluatorVisualizer.plot_scenarios_comparison(...)`
- `QuantumEvaluatorVisualizer.plot_stochastic_vs_adversarial_comparison(...)`

### Compare with Teammates' Results

Since all results go to the same `quantum_data_lake/`, you can easily compare:

```python
# Use the same base path
base_path = "/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/framework_state"

# Load your results (replace with your actual date)
exp_dir_mine = f"{base_path}/day_20251124"
results_mine = viz.load_experiment_results(exp_dir_mine)

# Load teammate's results (replace with their date)
exp_dir_theirs = f"{base_path}/day_20251123"
results_theirs = viz.load_experiment_results(exp_dir_theirs)

# Compare
print("Your results:", results_mine.keys())
print("Their results:", results_theirs.keys())
```

---

## Troubleshooting

For common issues (import errors, Drive mount failures, "No saved state" warnings), see:

👉 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

---

## Next Steps

- **Modify your experiments**: Adjust the configuration cell and re-run
- **Combine multiple scenarios**: See "Multiple Scenarios" example above
- **Download results**: All data is in the shared drive, accessible from any device
- **Deep dive into code**: Clone the repo locally (see [SETUP_LOCAL.md](SETUP_LOCAL.md))