# Repository Structure Guide

**Quantum Multi-Armed Bandit Research Framework**

This document provides a complete overview of the repository organization, helping you quickly locate files and understand the framework structure.

---

## 📁 Repository Root

```
hybrid_variable_framework/
├── README.md                          # Main entry point & quick start
├── requirements.txt                   # Python dependencies
├── repo_structure.txt                 # Directory tree
├── REPOSITORY_STRUCTURE.md            # This file
│
├── docs/                              # 📚 Complete documentation (65+ files)
├── Dynamic_Routing_Eval_Framework/    # 🔬 Advanced evaluation framework
├── Validated_Logs/                    # ✅ Master datasets & validation results
│
├── daqr/                              # 🧬 Core framework package
├── tests/                             # 🧪 Test suites
├── scripts/                           # 🚀 Automation scripts
│
├── notebooks/                         # 📓 Production notebooks
├── sandbox_notebooks/                 # 🧪 Development notebooks
│
├── experiments/                       # ⚙️ Experiment configurations
├── results/                           # 📊 Local results
├── setup_files/                       # 🛠️ Setup artifacts
│
└── [Test & validation scripts]        # 🔍 Root-level test files
```

---

## 🗂️ Directory Details

### Core Framework (`daqr/`)

The main Python package implementing quantum routing algorithms:

- **algorithms/**: Multi-armed bandit implementations (UCB, Pursuit, Neural, etc.)
- **core/**: Quantum physics, network environments, attack strategies
- **config/**: Testbed configurations (Paper 2, 7, 12)
- **evaluation/**: Experiment runners and multi-run evaluators

### Documentation (`docs/`)

Complete documentation organized into 10 categories with 65+ files:

```
docs/
├── INDEX.md                        # Master documentation index
├── README.md → INDEX.md            # Symlink to master index
├── TESTBEDS_OVERVIEW.md            # Central testbed hub
│
├── setup/                          # 10 files: Setup & installation
├── testbeds/                       # 17 files: Paper-specific docs
├── paper12/                        # 4 files: Additional Paper 12 docs
├── guides/                         # 4 files: General guides
├── assessments/                    # 2 files: Assessment reports
├── planning/                       # 2 files: Planning documents
├── updates/                        # 2 files: Update summaries
├── validated_logs/                 # 2 files: Validation results
├── implementation-notes/           # 12 files: Technical debugging
│
└── [Integration summaries]         # 8 files: Integration status
```

**Key Documentation**:
- Start: [docs/INDEX.md](docs/INDEX.md)
- Testbeds: [docs/TESTBEDS_OVERVIEW.md](docs/TESTBEDS_OVERVIEW.md)
- Setup: [docs/setup/SETUP_COLAB.md](docs/setup/SETUP_COLAB.md) or [docs/setup/SETUP_LOCAL.md](docs/setup/SETUP_LOCAL.md)

### Advanced Evaluation (`Dynamic_Routing_Eval_Framework/`)

Advanced testing and evaluation framework:

```
Dynamic_Routing_Eval_Framework/
├── daqr/                           # Extended framework components
│   ├── algorithms/                 # Advanced algorithm implementations
│   ├── core/                       # Enhanced quantum environments
│   ├── config/                     # Evaluation configurations
│   └── evaluation/                 # Multi-run evaluators
│
├── notebooks/                      # Evaluation notebooks
│   └── H-MABs_Eval-T_XQubit_Alloc_XQRuns.ipynb
│
├── experiments/                    # Experiment configurations
├── results/                        # Evaluation results
│
├── run_paper12_sanity_tests.py    # Paper 12 validation suite
├── run_paper7_sanity_tests.py     # Paper 7 validation suite
└── run_tests.sh                    # Test automation

└── tools/                          # 🧰 Framework tools (small tests + state repair)
    ├── README.md                   # Tool index + commands
    ├── tests/                      # Fast invariants (naming/resume, etc.)
    └── state/                      # Audit/repair saved framework_state pickles
```

### Validated Results (`Validated_Logs/`)

Master datasets from all experiments:

```
Validated_Logs/
├── Master_Dataset_CMABs.csv        # CMAB experiments
├── Master_Dataset_EXP3.csv         # EXP3 experiments
├── Master_Dataset_Hybrid.csv       # Hybrid experiments
├── Master_Dataset_iCMABs.csv       # iCMAB experiments
│
├── EXP3_Tests/                     # EXP3 validation results
│   ├── 3Runs/                      # 3-run ensembles
│   └── 5Runs/                      # 5-run ensembles
│
├── Hybrid_Tests/                   # Hybrid algorithm results
│   ├── 3Runs/
│   └── 5Runs/
│
├── iCMABs_Tests/                   # iCMAB validation results
│   ├── 3Runs/
│   └── 5Runs/
│
└── backup/                         # Historical data
    ├── framework_state/            # Framework snapshots
    └── model_state/                # Model checkpoints
```

### Test Suites (`tests/`)

Automated validation for all testbeds:

- Paper 2 tests: MATLAB-based validation
- Paper 7 tests: Python unit tests for QBGP
- Paper 12 tests: Comprehensive unit test suite (6 tests)

### Scripts & Automation

#### `scripts/`
Production automation scripts:
- `1_startup.sh`: GCP VM initialization
- `2_exp_runner.sh`: Experiment execution
- `3_push_results.sh`: Results synchronization
- `dynamic_exp_runner.sh`: Dynamic experiment runner
- `run_exp[1-4].sh`: Individual experiment runners

### Notebooks

#### `notebooks/` (Production)
- Production-ready Colab notebooks
- Shared drive integration
- Ready for deployment

#### `sandbox_notebooks/` (Development)
- Development and testing notebooks
- Experimental features
- Local development

### Root-Level Files

**Test & Validation**:
- `test_oracle_paper7.py`: Oracle validation for Paper 7
- `test_paper7_gneuralucb.py`: Neural UCB testing for Paper 7
- `oracle_validation_quick.py`: Quick oracle validation
- `verify_probability_fix.py`: Probability model verification
- `state_analysis.py`: State analysis utilities
- `cleanup_state_duplicates.py`: State cleanup tool

**Infrastructure**:
- `gcp_experiment_runner.py`: GCP experiment orchestration
- `ORACLE_FIX_README.py`: Oracle fix documentation

---

## 🎯 Quick Access Paths

### For First-Time Users
1. Read: [README.md](README.md)
2. Choose environment: [docs/setup/](docs/setup/)
3. Start with testbed: [docs/TESTBEDS_OVERVIEW.md](docs/TESTBEDS_OVERVIEW.md)

### For Researchers
- **Documentation hub**: [docs/INDEX.md](docs/INDEX.md)
- **Paper 2 details**: [docs/testbeds/Paper2_Integration_Report.md](docs/testbeds/Paper2_Integration_Report.md)
- **Paper 7 details**: [docs/testbeds/Paper7_Summary.md](docs/testbeds/Paper7_Summary.md)
- **Paper 12 details**: [docs/testbeds/Paper12_Testing_Guide.md](docs/testbeds/Paper12_Testing_Guide.md)
- **Validated results**: [Validated_Logs/](Validated_Logs/)

### For Developers
- **Core algorithms**: [daqr/algorithms/](daqr/algorithms/)
- **Quantum environments**: [daqr/core/](daqr/core/)
- **Test suites**: [tests/](tests/), [Dynamic_Routing_Eval_Framework/](Dynamic_Routing_Eval_Framework/)
- **Implementation notes**: [docs/implementation-notes/](docs/implementation-notes/)

### For Running Experiments
- **Colab setup**: [docs/setup/SETUP_COLAB.md](docs/setup/SETUP_COLAB.md)
- **Local setup**: [docs/setup/SETUP_LOCAL.md](docs/setup/SETUP_LOCAL.md)
- **Scripts**: [scripts/](scripts/)
- **Notebooks**: [notebooks/](notebooks/)

---

## 📊 File Counts Summary

| Category | Count | Location |
|----------|-------|----------|
| **Documentation** | 65+ | `docs/` |
| **Core Package** | ~50 | `daqr/` |
| **Evaluation Framework** | ~40 | `Dynamic_Routing_Eval_Framework/` |
| **Test Scripts** | 15+ | `tests/`, root |
| **Notebooks** | 10+ | `notebooks/`, `sandbox_notebooks/` |
| **Scripts** | 15+ | `scripts/` |
| **Validated Datasets** | 4 master CSVs + hundreds of logs | `Validated_Logs/` |

**Total Repository**: 200+ significant files across comprehensive framework

---

## 🔄 Integration Status

### ✅ Production Ready
- **Paper 2**: MAB quantum routing with entanglement swapping
- **Paper 7**: QBGP with online path selection
- **Paper 12**: QuARC qubit allocation with fusion gates

### 📚 Documentation Complete
- All testbeds fully documented
- Setup guides for all environments
- Comprehensive testing guides
- Implementation debugging notes

### ✅ Validation Complete
- All unit tests passing
- Master datasets collected
- Cross-testbed validation
- Performance benchmarks established

---

## 🚀 Getting Started

1. **Clone repository**
2. **Read**: [README.md](README.md)
3. **Check**: [docs/INDEX.md](docs/INDEX.md)
4. **Setup**: [docs/setup/](docs/setup/)
5. **Choose testbed**: [docs/TESTBEDS_OVERVIEW.md](docs/TESTBEDS_OVERVIEW.md)
6. **Run experiments**: Follow testbed-specific guide

---

**Questions?** See [docs/setup/TROUBLESHOOTING.md](docs/setup/TROUBLESHOOTING.md) or [docs/INDEX.md](docs/INDEX.md)
