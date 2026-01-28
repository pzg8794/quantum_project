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
| **[TESTBEDS.md](setup_files/TESTBEDS.md)** | Testbed integration hub & status | Everyone |
| **[Paper2 Integration](docs/Paper2_Integration_Report.md)** | Paper2 stochastic testbed (PROD) | Researchers |
| **[Paper12 Integration](docs/Paper12_Integration_Report.md)** | Paper12 event-driven testbed (IN PROGRESS) | Researchers |
| **[SETUP_COLAB.md](setup_files/SETUP_COLAB.md)** | Colab step-by-step with screenshots | First-time users |
| **[SETUP_LOCAL.md](setup_files/SETUP_LOCAL.md)** | Local + GCP VM setup | Developers |
| **[TROUBLESHOOTING.md](setup_files/TROUBLESHOOTING.md)** | Common issues & fixes | Everyone |

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

**Full guide**: [`SETUP_COLAB.md`](setup_files/SETUP_COLAB.md)

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

**Full guide**: [`SETUP_LOCAL.md`](setup_files/SETUP_LOCAL.md)

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

**Full guide**: [`SETUP_LOCAL.md`](setup_files/SETUP_LOCAL.md#gcp-vm-setup)

---

## 🧬 Multi-Testbed Architecture

### Current Status

| Testbed | Status | Integration Doc | Type |
|---------|--------|-----------------|------|
| **Paper2** | ✅ Production | [Paper2_Integration_Report.md](docs/Paper2_Integration_Report.md) | Stochastic |
| **Paper12** | 🔄 In Progress | [Paper12_Integration_Report.md](docs/Paper12_Integration_Report.md) | Event-driven |
| **Paper5** | 📋 Planned | Coming soon | Long-distance |
| **Paper7** | 📋 Planned | Coming soon | Multi-domain |

**See** [`TESTBEDS.md`](setup_files/TESTBEDS.md) **for complete testbed hub, comparison matrix, and integration roadmap.**

### Paper2 Highlights (Stochastic Network)

- **Network**: 4-node, 4-path (2-hop + 3-hop paths)
- **Physics**: Per-hop fidelity 0.95, multiplicative cascading
- **Threat Levels**: 6.25% stochastic, 25% Markov/Adaptive escalation
- **Key Finding**: CPursuit achieves 89.9% efficiency; context-aware >> adversarial-only

🚀 **Ready for production experiments** → See [`Paper2_Integration_Report.md`](docs/Paper2_Integration_Report.md)

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
├── README.md                          ← You are here
├── TESTBEDS.md                        ← Testbed hub (NEW)
├── setup_files/
│   ├── SETUP_COLAB.md                 ← Colab detailed guide
│   ├── SETUP_LOCAL.md                 ← Local + GCP guide
│   └── TROUBLESHOOTING.md             ← Common issues
├── docs/
│   ├── Paper2_Integration_Report.md   ← Paper2 full details
│   ├── Paper2_Quick_Reference.md      ← Paper2 parameters
│   ├── Paper2_Test_Commands.md        ← Paper2 test scripts
│   ├── Paper12_Integration_Report.md  ← Paper12 full details (planned)
│   └── ...
└── daqr/
    └── (source code with inline docstrings)
```

---

## 🔧 Repository Structure

```
quantum_mab_research/
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
├── setup_files/                   # Setup guides
├── quantum_data_lake/             # Shared results (Git-ignored, in Drive)
├── requirements.txt
├── README.md                      ← Overview & quick start
└── TESTBEDS.md                    ← Testbed hub & integration status
```

---

## ✅ First-Time Checklist

**Before running anything:**

- [ ] I have **read access** to the `ai_quantum_computing` shared drive
- [ ] I chose my execution path (Colab / Local / GCP)
- [ ] I read the setup guide for my path
- [ ] I can run the "Quick Start" example
- [ ] I see results saved to `quantum_data_lake/`
- [ ] I understand my testbed (Paper2 / Paper12 / etc.)

**If any fail** → Check [`TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md)

---

## 🎯 Next Steps

1. **Pick your execution path** → Read corresponding setup guide (Colab / Local / GCP)
2. **Choose your testbed** → See [`TESTBEDS.md`](setup_files/TESTBEDS.md) for overview
3. **Run a test** → Use the quick-start example for your path
4. **Check results** → Look in `quantum_data_lake/` on shared drive
5. **Dive deeper** → Read testbed-specific integration reports

---

## 📞 Questions?

| Topic | Resource |
|-------|----------|
| **Setup issues** | [`TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md) |
| **Colab help** | [`SETUP_COLAB.md`](setup_files/SETUP_COLAB.md) |
| **Local/GCP help** | [`SETUP_LOCAL.md`](setup_files/SETUP_LOCAL.md) |
| **Testbed details** | [`TESTBEDS.md`](setup_files/TESTBEDS.md) |
| **Paper2 specifics** | [`Paper2_Integration_Report.md`](docs/Paper2_Integration_Report.md) |
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

**Framework Status**: ✅ **PRODUCTION READY** (Paper2 validated)

🚀 **Get started**: Pick your path above, follow the setup guide, run your first experiment!
