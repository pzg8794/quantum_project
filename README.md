# Quantum Multi-Armed Bandit Research Framework

**Adversarial Quantum Entanglement Routing via Neural Multi-Armed Bandits**

A **multi-testbed** research framework for evaluating quantum routing algorithms across diverse quantum network architectures under stochastic and adversarial conditions, with a **shared Google Drive data lake** ensuring seamless collaboration.

---

## ⚡ TL;DR – Get Started in 5 Minutes

| Environment | Time | Command |
|-------------|------|---------|
| **Colab** | 5 min | Open `Quantum_MAB_Research_Sandbox(PROD).ipynb` from shared drive |
| **Local** | 15 min | `git clone` + `pip install -r requirements.txt` + `bash scripts/run_exp_test.sh` |
| **GCP VM** | 30 min | `bash scripts/1_startup.sh` + `bash scripts/dynamic_exp_runner.sh` |

**Results saved to**: Shared `quantum_data_lake/` → Instantly visible to all team members  
Local state is staged under `Dynamic_Routing_Eval_Framework/daqr/config/quantum_data_lake/` (runtime output; ignored by git).

---

## 🎯 What This Framework Does

✅ **Compare** neural bandit algorithms for quantum entanglement routing  
✅ **Test** across **multiple quantum network testbeds** (Paper2, Paper7, Paper8, Paper12)  
✅ **Stress-test** under different attack models (Stochastic, Markov, Adaptive, OnlineAdaptive)  
✅ **Run** from Colab (no install), local machine (dev), or GCP VMs (large-scale)  
✅ **Collaborate** via unified shared drive — no manual file copying  

---

## 📁 Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Repository Structure](REPOSITORY_STRUCTURE.md)** | Complete directory guide & file locations | Everyone |
| **[Documentation Index](docs/INDEX.md)** | Master index of all docs organized by topic | Everyone |
| **[Testbeds Overview](docs/TESTBEDS_OVERVIEW.md)** | All testbeds hub with comparison matrix | Everyone |
| **[Paper 2 Quick Ref](docs/testbeds/Paper2_Quick_Reference.md)** | Paper 2 - MAB quantum routing (PROD) | Researchers |
| **[Paper 7 Quick Ref](docs/testbeds/Paper7_Quick_Reference.md)** | Paper 7 - QBGP routing (INTEGRATED) | Researchers |
| **[Paper 12 Quick Ref](docs/testbeds/Paper12_Quick_Reference.md)** | Paper 12 - QuARC allocation (INTEGRATED) | Researchers |
| **[SETUP_COLAB.md](docs/setup/SETUP_COLAB.md)** | Colab step-by-step with screenshots | First-time users |
| **[SETUP_LOCAL.md](docs/setup/SETUP_LOCAL.md)** | Local + GCP VM setup | Developers |
| **[TROUBLESHOOTING.md](docs/setup/TROUBLESHOOTING.md)** | Common issues & fixes | Everyone |
| **[Framework Tools](Dynamic_Routing_Eval_Framework/tools/README.md)** | Small tests + state repair tools (naming/resume, qubit-cap metadata) | Developers |
| **[State/Resume Log](Dynamic_Routing_Eval_Framework/STATE-RESUME-QUbitCaps-LOG.md)** | Issue → diagnosis → fixes for state/resume metadata | Developers |
| **[State Analysis Contract](docs/guides/STATE_ANALYSIS_EVALUATOR_CONTRACT.md)** | Canonical evaluator-state payload contract for `state_analysis.py` | Developers |
| **[Assessments](docs/assessments/)** | Assessment reports and corrections | Researchers |
| **[Planning](docs/planning/)** | Project planning and schedules | Team |
| **[Updates](docs/updates/)** | Change logs and summaries | Everyone |
| **[Validated Logs](docs/validated_logs/)** | Validation results and datasets | Researchers |
| **[Validated_Logs/](Validated_Logs/)** | Master datasets & experiment results | Researchers |

---

## 🚀 Choose Your Path

### 🅰️ Google Colab (5 min, no install)

```python
# 1. Open from shared drive: Quantum_MAB_Research_Sandbox(PROD).ipynb
# 2. Mount Drive (auto-prompted)
# 3. Run experiment:

from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')  # Load Paper2 defaults
config.setenvironment(framesno=6000, attack_type='stochastic')

evaluator = MultiRunEvaluator(config=config, runs=3)
results = evaluator.test_stochastic_environment(
    models=['CPursuit', 'iCEpsilonGreedy', 'EXPNeuralUCB'],
    scenarios=['stochastic']
)
# Results auto-saved to shared drive ✅
```

**Full guide**: [`SETUP_COLAB.md`](docs/setup/SETUP_COLAB.md)

---

### 🅱️ Local Development (15 min, full control)

```bash
# Clone repo
git clone <repository-url>
cd quantum-mab-research

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Paper2 validation tests
bash scripts/paper2_test_suite.sh

# Or run custom experiment
python -c "
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.experiment_runner import QuantumExperimentRunner

config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')

runner = QuantumExperimentRunner(id=1, config=config, frames_count=6000)
results = runner.runalgorithm('CPursuitNeuralUCB')
print(f'Efficiency: {results[\"efficiency\"]:.1f}%')
"
```

**Full guide**: [`SETUP_LOCAL.md`](docs/setup/SETUP_LOCAL.md)

---

### ☁️ GCP VM (30 min, scalable)

```bash
# Create VM with auto-setup
bash scripts/1_startup.sh

# SSH in and run batch experiments
bash scripts/paper2_test_suite.sh

# Custom batch
bash scripts/dynamic_exp_runner.sh \
  --testbed="paper2" \
  --models="CPursuit,iCEpsilonGreedy,EXPNeuralUCB" \
  --runs=20
```

**Full guide**: [`SETUP_LOCAL.md`](docs/setup/SETUP_LOCAL.md#gcp-vm-setup)

---

## 🧬 Multi-Testbed Architecture

### Current Status

| Testbed | Status | Quick Ref | Type | Language |
|---------|--------|-----------|------|----------|
| **Paper 2** | ✅ Production | [Paper2_Quick_Reference.md](docs/testbeds/Paper2_Quick_Reference.md) | Stochastic MAB | MATLAB |
| **Paper 7** | ✅ Integrated | [Paper7_Quick_Reference.md](docs/testbeds/Paper7_Quick_Reference.md) | Online BGP | Python |
| **Paper 8** | 🟡 Integrated (paper-config run); standardized pending | (paper-config notebook) `Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-Testbed-Paper8-PaperRunConfig.ipynb` | RL/Q-learning testbed | Python |
| **Paper 12** | ✅ Integrated | [Paper12_Quick_Reference.md](docs/testbeds/Paper12_Quick_Reference.md) | Qubit Allocation | Python |

**Central Hub**: [`docs/TESTBEDS_OVERVIEW.md`](docs/TESTBEDS_OVERVIEW.md) — Quick summary table, comparison matrix, and navigation to all paper-specific docs.

### Quick Testbed Summary

| Paper | Network | Key Metric | Status |
|-------|---------|-----------|--------|
| **Paper 2** | 4 nodes, 4 paths | CPursuit: 89.9% efficiency | ✅ PROD |
| **Paper 7** | 100 nodes (50-400 range) | Fidelity ≥0.85, delay-aware | ✅ INTEGRATED |
| **Paper 12** | 100 nodes, 10 S-D pairs | 54% success (0.9 × 0.6) | ✅ INTEGRATED |

**Individual Documentation**:
- 📄 [Paper 2 Integration Report](docs/testbeds/Paper2_Integration_Report.md)
- 📄 [Paper 7 Validation Guide](docs/testbeds/Paper7_Validation.md) & [Summary](docs/testbeds/Paper7_Summary.md)
- 📄 [Paper 12 Testing Guide](docs/testbeds/Paper12_Testing_Guide.md) & [Parameters](docs/testbeds/Paper12_Parameters.md)

---

## 📊 Shared Data Lake

All experiments write to a **unified, shared directory** on Google Drive:

```
quantum_data_lake/
├── paper2/                  # Paper2 testbed results
│   ├── model_state/         # Trained models
│   ├── framework_state/     # Experiment metadata
│   └── visualizations/      # Plots, CSV summaries
├── paper12/                 # Paper12 testbed results
│   ├── model_state/
│   ├── framework_state/
│   └── visualizations/
└── cross_testbed/           # Cross-testbed analysis
    └── paper2_vs_paper12/
```

**Key benefit**: Run from Colab, local machine, or GCP VM — results go to the **same place**, instantly visible to all team members. No manual copying. No "which version is current?".

---

## 📊 Experiments & Results

### Experiment Management
- **experiments/**: Experiment configurations and parameter sweeps
- **results/**: Local result storage and analysis scripts
- **Dynamic_Routing_Eval_Framework/**: Advanced evaluation framework with notebooks and automated testing
- **Validated_Logs/**: Master datasets and validation results from all experiments

### Validation & Testing
- **tests/test_*.py**: Automated test suites for each testbed
- **run_*.py**: Sanity checks and validation scripts
- **scripts/**: Bash automation for running experiments
- **Dynamic_Routing_Eval_Framework/tools/**: Framework utilities:
  - `tools/tests/`: small, fast invariants (e.g., Random allocator naming/resume)
  - quick battery: `bash Dynamic_Routing_Eval_Framework/tools/tests/run_small_tests.sh`
  - `tools/state/`: audit/repair of saved `.pkl` state under `daqr/config/framework_state/`
- **Analysis contract**: `docs/guides/STATE_ANALYSIS_EVALUATOR_CONTRACT.md` defines the evaluator payload expected by `state_analysis.py` and the observed 2026-03-06 drift (`n/a` in `env_experiments` without matching `scenarios_results` payload).

### Notebooks & Interactive Development
- **notebooks/**: Production Colab notebooks
- **sandbox_notebooks/**: Development and testing notebooks
- **Dynamic_Routing_Eval_Framework/notebooks/**: Advanced evaluation notebooks

### Plotting (AllocatorRunner)
By default, `AllocatorRunner` generates comparison plots after each run (same behavior as the older pipeline notebooks).

- Disable plots in code: set `framework_config["enable_plots"] = False`
- Disable plots via env var: `export DAQR_ENABLE_PLOTS=0`

---

## 📚 Documentation Structure

```
├── README.md                              ← You are here
└── docs/                                  ← ALL DOCUMENTATION ORGANIZED HERE
  ├── INDEX.md                           ← Master documentation index
  ├── TESTBEDS_OVERVIEW.md               ← Central testbed hub
  ├── setup/                             ← Setup guides (10 files)
  ├── testbeds/                          ← Paper-specific documentation (16+ files)
  ├── paper12/                           ← Additional Paper 12 docs (4 files)
  ├── guides/                            ← General guides (4 files)
  ├── assessments/                       ← Assessment reports (2 files)
  ├── planning/                          ← Planning documents (2 files)
  ├── updates/                           ← Update summaries (2 files)
  ├── validated_logs/                    ← Validation results (2 files)
  ├── implementation-notes/              ← Technical debugging docs (12 files)
  └── [Integration & completion docs]
```

## 🔧 Complete Repository Structure

```
hybrid_variable_framework/
├── daqr/                          # Main Python package
│   ├── algorithms/                # Bandit algorithms (testbed-agnostic)
│   ├── core/                      # Quantum environments (testbed-specific)
│   ├── config/                    # Configuration management
│   └── evaluation/                # Experiment runners & visualizers
├── tests/                         # Testbed validation suites
├── notebooks/                     # Production Colab notebooks
├── sandbox_notebooks/             # Development notebooks
├── scripts/                       # Bash + GCP helper scripts
├── experiments/                   # Experiment configurations
├── results/                       # Local result storage
├── Dynamic_Routing_Eval_Framework/# Advanced evaluation framework
│   ├── notebooks/                 # Evaluation notebooks
│   ├── experiments/               # Test configurations
│   ├── results/                   # Output data
│   └── daqr/                      # Framework components
├── Validated_Logs/                # Master datasets & validation
├── docs/                          # Complete documentation
├── setup_files/                   # Setup guide sources
├── .github/                       # GitHub configuration
├── requirements.txt
├── README.md                      ← This file
└── [Other config files]
```

---

## ✅ First-Time Checklist

**Before running anything:**

- [ ] I have **read access** to the `ai_quantum_computing` shared drive
- [ ] I chose my execution path (Colab / Local / GCP)
- [ ] I read the setup guide for my path
- [ ] I can run the "Quick Start" example
- [ ] I see results saved to `quantum_data_lake/`
- [ ] I understand my testbed (Paper2 / Paper7 / Paper12)

**If any fail** → Check [`TROUBLESHOOTING.md`](docs/setup/TROUBLESHOOTING.md)

---

## 🎯 Next Steps

1. **Understand the repository** → Read [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) for complete file organization
2. **Start with documentation index** → Read [docs/INDEX.md](docs/INDEX.md)
3. **Get testbed overview** → Read [docs/TESTBEDS_OVERVIEW.md](docs/TESTBEDS_OVERVIEW.md)
4. **Pick your testbed** → Choose Paper 2, Paper 7, or Paper 12
5. **Review testbed docs** → See `docs/testbeds/Paper{2,7,12}_*.md`
6. **Pick your execution path** → Read setup guide (Colab / Local / GCP)
7. **Run a test** → Use the quick-start example for your path
8. **Check results** → Look in `quantum_data_lake/` on shared drive or `Validated_Logs/` for datasets

---

## 📞 Questions?

| Topic | Resource |
|-------|----------|
| **Repository structure** | [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) |
| **Docs index** | [docs/INDEX.md](docs/INDEX.md) |
| **Testbed overview** | [docs/TESTBEDS_OVERVIEW.md](docs/TESTBEDS_OVERVIEW.md) |
| **Paper 2 details** | [docs/testbeds/Paper2_Integration_Report.md](docs/testbeds/Paper2_Integration_Report.md) |
| **Paper 7 details** | [docs/testbeds/Paper7_Summary.md](docs/testbeds/Paper7_Summary.md) |
| **Paper 12 details** | [docs/testbeds/Paper12_Testing_Guide.md](docs/testbeds/Paper12_Testing_Guide.md) |
| **Setup issues** | [docs/setup/TROUBLESHOOTING.md](docs/setup/TROUBLESHOOTING.md) |
| **Colab help** | [docs/setup/SETUP_COLAB.md](docs/setup/SETUP_COLAB.md) |
| **Local/GCP help** | [docs/setup/SETUP_LOCAL.md](docs/setup/SETUP_LOCAL.md) |
| **Assessments** | [docs/assessments/](docs/assessments/) |
| **Planning** | [docs/planning/](docs/planning/) |
| **Updates** | [docs/updates/](docs/updates/) |
| **Validated results** | [docs/validated_logs/](docs/validated_logs/) & [Validated_Logs/](Validated_Logs/) |
| **Framework bugs** | Open a GitHub issue |

---

## 📄 Citation

```
@article{quantum_mab_routing,
  title   = {Adversarial Quantum Entanglement Routing via Neural Multi-Armed Bandits},
  author  = {Garcia, P. and Collaborators},
  journal = {arXiv preprint},
  year    = {2024}
}
```

---

**Framework Status**: ✅ **MULTI-TESTBED READY**
- Paper 2 (MAB): ✅ Production-ready
- Paper 7 (QBGP): ✅ Fully integrated with testing
- Paper 12 (QuARC): ✅ Fully integrated with testing

🚀 **Get started**: See [docs/INDEX.md](docs/INDEX.md), choose your testbed, follow the setup guide, and run your first experiment!
