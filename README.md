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

---

## 🎯 What This Framework Does

✅ **Compare** neural bandit algorithms for quantum entanglement routing  
✅ **Test** across **multiple quantum network testbeds** (Paper2, Paper12, Paper5, Paper7)  
✅ **Stress-test** under different attack models (Stochastic, Markov, Adaptive, OnlineAdaptive)  
✅ **Run** from Colab (no install), local machine (dev), or GCP VMs (large-scale)  
✅ **Collaborate** via unified shared drive — no manual file copying  

---

## 📁 Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Documentation Index](docs/INDEX.md)** | Master index of all docs organized by topic | Everyone |
| **[Testbeds Overview](docs/TESTBEDS_OVERVIEW.md)** | All testbeds hub with comparison matrix | Everyone |
| **[Paper 2 Quick Ref](docs/testbeds/Paper2_Quick_Reference.md)** | Paper 2 - MAB quantum routing (PROD) | Researchers |
| **[Paper 7 Quick Ref](docs/testbeds/Paper7_Quick_Reference.md)** | Paper 7 - QBGP routing (INTEGRATED) | Researchers |
| **[Paper 12 Quick Ref](docs/testbeds/Paper12_Quick_Reference.md)** | Paper 12 - QuARC allocation (INTEGRATED) | Researchers |
| **[SETUP_COLAB.md](docs/setup/SETUP_COLAB.md)** | Colab step-by-step with screenshots | First-time users |
| **[SETUP_LOCAL.md](docs/setup/SETUP_LOCAL.md)** | Local + GCP VM setup | Developers |
| **[TROUBLESHOOTING.md](docs/setup/TROUBLESHOOTING.md)** | Common issues & fixes | Everyone |

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

## 📚 Documentation Structure

```
├── README.md                              ← You are here
└── docs/                                  ← ALL DOCUMENTATION ORGANIZED HERE
  ├── INDEX.md                           ← Master documentation index
  ├── TESTBEDS_OVERVIEW.md               ← Central testbed hub
  ├── setup/                             ← Setup guides (10 files)
  ├── testbeds/                          ← Paper-specific documentation (16 files)
  ├── implementation-notes/              ← Technical debugging docs (12 files)
  └── [Integration & completion docs]
```

## 🔧 Framework Structure

```
hybrid_variable_framework/
├── daqr/                          # Main Python package
│   ├── algorithms/                # Bandit algorithms (testbed-agnostic)
│   ├── core/                      # Quantum environments (testbed-specific)
│   │   ├── quantum_physics.py
│   │   ├── network_environment.py
│   │   ├── attack_strategies.py
│   │   └── qubit_allocator.py
│   ├── config/                    # Configuration management
│   │   └── experiment_config.py   # PAPER2_CONFIG, PAPER12_CONFIG, etc.
│   └── evaluation/                # Experiment runners & visualizers
├── tests/                         # Testbed validation suites
│   ├── test_paper2_*.py           # Paper2: 8 validation tests
│   └── test_paper12_*.py          # Paper12: validation tests
├── notebooks/                     # Colab notebooks (PROD/DEV/TEST)
├── scripts/                       # Bash + GCP helper scripts
├── docs/                          # Detailed documentation
├── setup_files/                   # Setup guide sources (non-md artifacts)
├── quantum_data_lake/             # Shared results (Git-ignored, in Drive)
├── requirements.txt
└── README.md                      ← Overview & quick start
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

1. **Start with documentation index** → Read [`docs/INDEX.md`](docs/INDEX.md)
2. **Get testbed overview** → Read [`docs/TESTBEDS_OVERVIEW.md`](docs/TESTBEDS_OVERVIEW.md)
3. **Pick your testbed** → Choose Paper 2, Paper 7, or Paper 12
4. **Review testbed docs** → See `docs/testbeds/Paper{2,7,12}_*.md`
5. **Pick your execution path** → Read setup guide (Colab / Local / GCP)
6. **Run a test** → Use the quick-start example for your path
7. **Check results** → Look in `quantum_data_lake/` on shared drive

---

## 📞 Questions?

| Topic | Resource |
|-------|----------|
| **Docs index** | [`docs/INDEX.md`](docs/INDEX.md) |
| **Testbed overview** | [`docs/TESTBEDS_OVERVIEW.md`](docs/TESTBEDS_OVERVIEW.md) |
| **Paper 2 details** | [`docs/testbeds/Paper2_Integration_Report.md`](docs/testbeds/Paper2_Integration_Report.md) |
| **Paper 7 details** | [`docs/testbeds/Paper7_Summary.md`](docs/testbeds/Paper7_Summary.md) |
| **Paper 12 details** | [`docs/testbeds/Paper12_Testing_Guide.md`](docs/testbeds/Paper12_Testing_Guide.md) |
| **Setup issues** | [`TROUBLESHOOTING.md`](docs/setup/TROUBLESHOOTING.md) |
| **Colab help** | [`SETUP_COLAB.md`](docs/setup/SETUP_COLAB.md) |
| **Local/GCP help** | [`SETUP_LOCAL.md`](docs/setup/SETUP_LOCAL.md) |
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
