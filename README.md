# Quantum Multi-Armed Bandit Research Framework

**Adversarial Quantum Entanglement Routing via Neural Multi-Armed Bandits**

A research framework for evaluating quantum routing algorithms (EXPNeuralUCB and friends) under stochastic and adversarial conditions, with a **shared Google Drive data lake** so all experiments (Colab, local, GCP) write to the same place.

---

## ⚡ TL;DR

- **Colab (5 min setup)**: Open `Quantum_MAB_Research_Sandbox(PROD).ipynb` in shared drive, run it.
- **Local (15 min setup)**: `git clone`, `pip install -r requirements.txt`, `bash scripts/run_exp_test.sh`.
- **Results**: Automatically saved to shared `quantum_data_lake/` — same location regardless of where you run.
- **Compare**: Pull results from teammates' runs in the same data lake.

---

## 🎯 What This Repo Is For

- Compare **neural bandit algorithms** for quantum entanglement routing
- Stress-test under different **attack models** (NoAttack, Random, Markov, Adaptive, OnlineAdaptive)
- Run experiments from:
  - Google Colab (no local install needed)
  - Your own laptop/desktop (full dev environment)
  - GCP VMs (parallel / large-scale runs)
- Store everything in a **unified `quantum_data_lake/`** on shared Google Drive so results are **instantly comparable** across all environments and team members.

---

## 📁 Repository Structure

```
quantum_mab_research/
├── daqr/                     # Main Python package
│   ├── algorithms/           # Bandit algorithm implementations
│   │   ├── base_bandit.py    # Base class for all models
│   │   ├── neural_bandits.py # NeuralUCB, NeuralTS, etc.
│   │   └── predictive_bandits.py # EXPNeuralUCB, iCMAB, etc.
│   ├── config/               # Experiment config + backup
│   │   ├── experiment_config.py
│   │   ├── local_backup_manager.py
│   │   └── gd_backup_manager.py
│   ├── core/                 # Quantum environment simulation
│   │   ├── network_environment.py
│   │   └── qubit_allocator.py
│   └── evaluation/           # Experiment execution & results
│       ├── experiment_runner.py
│       ├── multi_run_evaluator.py
│       └── visualizer.py
├── notebooks/                # Colab notebooks (DEV / TEST / PROD)
├── scripts/                  # Bash + GCP helper scripts
├── quantum_data_lake/        # Shared results (Git-ignored, in Drive)
├── requirements.txt
└── README.md
```

**Key insight**: All three execution paths (Colab, Local, GCP) read and write to the **same** `quantum_data_lake/` structure.

---

## 🚦 Quick Start: Choose Your Path

### 🅰️ Option A — Google Colab (Recommended for quick runs)

**Setup time**: ~5 minutes | **Compute**: Free T4 GPU | **Results**: Instant sync to shared drive

1. **Open the shared drive**
   - Google Drive → `Shared drives → ai_quantum_computing`
   - Navigate to `notebooks/`
   - Open one of:
     - `Quantum_MAB_Research_Sandbox(PROD).ipynb` ← **Start here for paper runs**
     - `Quantum_MAB_Research_Sandbox(DEV).ipynb` ← For development
     - `Quantum_MAB_Research_Sandbox(TEST).ipynb` ← For validation

2. **Mount Drive** (notebook prompts automatically)
   ```
   from google.colab import drive
   drive.mount('/content/drive')
   ```

3. **Install deps** (first run only)
   ```
   !pip install -q -r requirements.txt
   ```

4. **Run an experiment**
   ```
   from daqr.config.experiment_config import ExperimentConfiguration
   from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

   config = ExperimentConfiguration(
       models=["Oracle", "EXPNeuralUCB"],
       scenarios=["Stochastic"],
       attack_type="Random",
       attack_intensity=0.0625,
   )

   evaluator = MultiRunEvaluator(
       configs=config,
       runs=3,              # Number of random seeds
       base_frames=4000,
       frame_step=2000,
       base_seed=12345,
   )

   results = evaluator.run_multi_model_evaluation()
   ```

5. **Check results** 
   - Saved to: `/content/drive/Shareddrives/ai_quantum_computing/quantum_data_lake/`
   - Visible by all team members immediately

**Expected runtime**: 
- Small test (1 run, 1 model): ~15 min
- Standard (3 runs, 2 models): ~45 min
- Full evaluation (5 runs, 3 models): ~2 hours

👉 **Full guide with screenshots**: See [`SETUP_COLAB.md`](SETUP_COLAB.md)

---

### 🅱️ Option B — Local Development (Recommended for code changes)

**Setup time**: ~15 minutes | **Compute**: Your machine | **Results**: Sync to shared drive (optional)

1. **Clone the repo**
   ```
   git clone <repository-url>
   cd quantum-mab-research
   ```

2. **Create virtual environment**
   ```
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. **Run a test**
   ```
   bash scripts/run_exp_test.sh
   ```

4. **Optional: Point to shared data lake**
   
   If you want your local runs to sync with the team's shared Drive:
   ```
   # Linux/Mac: Mount Google Drive (requires google-drive-ocamlfuse)
   mkdir -p ~/drive
   google-drive-ocamlfuse ~/drive
   
   # Then the framework auto-detects the shared drive path
   ```

5. **Visualize results**
   
   See the **Visualization** section below for full examples.

👉 **Full guide**: See [`SETUP_LOCAL.md`](SETUP_LOCAL.md)

---

### ☁️ Option C — GCP VM (For large batches)

**Setup time**: ~30 minutes | **Compute**: Scalable | **Results**: Auto-sync to shared drive

Typical workflow:

1. Create a GCP VM with the startup script (auto-installs, mounts Drive)
   ```
   bash scripts/1_startup.sh
   ```

2. SSH in and run batch experiments:
   ```
   bash scripts/dynamic_exp_runner.sh \
     --models="EXPNeuralUCB,Oracle,NeuralUCB" \
     --runs=20 \
     --attack_type="Adaptive"
   ```

3. Sync results back:
   ```
   bash scripts/3_push_results.sh --push
   ```

👉 **Full guide**: See [`SETUP_LOCAL.md`](SETUP_LOCAL.md#gcp-vm-setup) (includes GCP section)

---

## 📊 The Shared Data Lake

This is the **magic ingredient** that makes everything work:

```
quantum_data_lake/
├── model_state/
│   ├── day_20251124/
│   │   ├── Oracle(hybrid)_16000-Default_Stochastic_Random-4000.pkl
│   │   ├── NeuralUCB_0(hybrid)_16000-Default-4000.pkl
│   │   └── ...
├── framework_state/
│   ├── day_20251124/
│   │   ├── QuantumExperimentRunner_1_results.pkl
│   │   └── ...
└── visualizations/
    ├── day_20251124/
    │   ├── reward_comparison.png
    │   ├── efficiency_by_model.csv
    │   └── ...
```

**Everyone writes here** (from Colab, local machine, GCP) → **Everyone reads from here** → **Instant collaboration**.

No manual copying. No email attachments. No "which version is current?". Just shared infrastructure.

---

## 🧪 Running Experiments

See the existing **Running Experiments** section below for detailed examples of:
- Basic single-run experiments
- Advanced multi-model comparisons
- Parameter sweeps
- Custom attack configurations

*(Keep your existing detailed examples here)*

---

## 📈 Visualization

See the existing **Visualization** section below for examples using `QuantumEvaluatorVisualizer` to generate plots and tables.

*(Keep your existing visualization examples here)*

---

## ❓ Troubleshooting & Docs

| Issue | Guide |
|-------|-------|
| "[WARN] No saved state at ..." | → See **`TROUBLESHOOTING.md`** (it's usually a cold start, not a bug) |
| Colab Drive mount failing | → See **`SETUP_COLAB.md`** (permissions, account selection) |
| ImportError / missing deps | → See **`SETUP_LOCAL.md`** (Python version, venv activation) |
| Slow performance on Colab | → See **`TROUBLESHOOTING.md`** (GPU settings, registry cache) |

👉 **Full troubleshooting**: See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

---

## ✅ First-Time Checklist

- [ ] I have **read** access to the `ai_quantum_computing` shared drive
- [ ] I chose my execution path (Colab / Local / GCP)
- [ ] I ran the "Quick Start" example from the path I chose
- [ ] I saw results saved to `quantum_data_lake/`
- [ ] I can access results from the shared drive (Colab) or locally (if synced)

If any of these fail → check **`TROUBLESHOOTING.md`**.

---

## 📚 Documentation Index

1. **This file** — Overview and quick start (you are here)
2. [`SETUP_COLAB.md`](SETUP_COLAB.md) — Detailed Colab instructions with screenshots
3. [`SETUP_LOCAL.md`](SETUP_LOCAL.md) — Full local setup, dev tools, GCP VM instructions
4. [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — Common issues and solutions
5. `daqr/` source code — Inline docstrings and type hints

---

## 📄 Citation

If you use this framework in a paper or project:

```
@article{quantum_mab_routing,
  title   = {Adversarial Quantum Entanglement Routing via Neural Multi-Armed Bandits},
  author  = {Garcia, P. and Collaborators},
  journal = {arXiv preprint},
  year    = {2024}
}
```

---

## 📧 Questions?

- **Framework bugs**: Open a GitHub issue
- **Results questions**: Check the data lake visualization notebooks
- **Access issues**: Contact the shared drive owner
```