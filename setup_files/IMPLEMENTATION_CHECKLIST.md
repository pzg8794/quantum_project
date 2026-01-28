# Paper Testbed Integration - Implementation Checklist

**Status**: Planning Phase  
**Timeline**: 2-5 days (estimated based on complexity)  
**Integration with**: Existing documentation in `/docs` directory  
**Related Documents**:
- [`TESTBEDS.md`](TESTBEDS.md) - Testbed overview & status matrix
- [`Paper2_Integration_Report.md`](docs/Paper2_Integration_Report.md) - Paper2 detailed reference
- [`Paper2_Quick_Reference.md`](docs/Paper2_Quick_Reference.md) - Parameter lookup
- [`Paper2_Test_Commands.md`](docs/Paper2_Test_Commands.md) - Validation suite

---

## Overview

This checklist guides the integration of **5 paper-specific testbeds** into the quantum MAB framework:
- **Paper #2** (Chaudhary et al., 2023) - UCB Route Selection
- **Paper #5** (Wang et al., 2025) - Learning Best Paths
- **Paper #7** (Liu et al., 2024) - Quantum BGP
- **Paper #8** (Jallow & Khan, 2025) - DQN Routing
- **Paper #12** (Wang et al., 2024) - QuARC Clustering

**Key Deliverables**:
1. `daqr/paper_testbeds.py` - All 5 bandit implementations
2. `daqr/cross_paper_evaluation.py` - Unified evaluation framework
3. Updated experiment configs and algorithm registry
4. Test suites for each paper
5. Cross-paper comparison report

---

## Phase 1: Setup & Infrastructure

### 1.1 Environment & Dependencies
- [ ] Python 3.8+ installed
- [ ] All required packages available (numpy, scipy, tensorflow/torch as needed)
- [ ] Access to `daqr/` directory structure
- [ ] Git repository initialized on `main` branch

### 1.2 File Preparation
- [ ] Verify all source files present in `daqr/`:
  - [ ] `base_bandit.py`
  - [ ] `neural_bandits.py` (GNeuralUCB, EXPNeuralUCB)
  - [ ] `network_environment.py`
  - [ ] `experiment_config.py`
  - [ ] `experiment_runner.py`
  - [ ] `multi_run_evaluator.py`

### 1.3 Branch Setup
- [ ] Create branch: `git checkout -b paper-testbeds-integration`
- [ ] Create backup: `git commit -m "Checkpoint: Pre-testbed integration"`

---

## Phase 2: Core Implementation

### 2.1 Create Paper Testbeds Module
- [ ] Create `daqr/paper_testbeds.py` with:
  - [ ] **Paper2UCBBandit** class
    - Constructor: `__init__(n_arms, n_nodes, synchronized_swapping=True, **kwargs)`
    - Methods: `select_action()`, `update()`, `get_metrics()`
    - Key metric: `convergence_step`
  
  - [ ] **Paper5FeedbackBandit** class
    - Constructor: `__init__(n_arms, feedback_type='combined', **kwargs)`
    - Key metric: `feedback_granularity_gain`
  
  - [ ] **Paper7BGPBandit** class
    - Constructor: `__init__(n_paths, k, n_qisps=3, network_scale='medium', **kwargs)`
    - Key metrics: `topk_accuracy`, `inter_domain_load_balance`
  
  - [ ] **Paper8DQNBandit** class
    - Constructor: `__init__(n_arms, learning_rate=0.001, **kwargs)`
    - Key metric: `q_convergence_step`
  
  - [ ] **Paper12QuARCBandit** class
    - Constructor: `__init__(n_arms, n_clusters=3, **kwargs)`
    - Key metric: `starvation_events`

### 2.2 Create Cross-Paper Evaluation Module
- [ ] Create `daqr/cross_paper_evaluation.py` with:
  - [ ] `CrossPaperEvaluator` class
  - [ ] Methods:
    - [ ] `run_paper_comparison()`
    - [ ] `generate_comparison_table()`
    - [ ] `compute_effect_sizes()`

### 2.3 Update Infrastructure Files

#### 2.3a Update `experiment_config.py`
- [ ] Add `Paper2Config` class with:
  ```python
  NAME = "Paper2_UCB_Route_Selection"
  N_NODES = 15
  N_ARMS = 8
  FRAME_RANGE = (400, 1400, 200)
  NOISE_PARAMS = {...}
  ```
- [ ] Add `Paper5Config`, `Paper7Config`, `Paper8Config`, `Paper12Config` classes

#### 2.3b Update `experiment_runner.py`
- [ ] Import all Paper classes from `paper_testbeds`
- [ ] Add to `ALGORITHM_REGISTRY`:
  ```python
  'Paper2UCB': Paper2UCBBandit,
  'Paper5Feedback': Paper5FeedbackBandit,
  'Paper7BGP': Paper7BGPBandit,
  'Paper8DQN': Paper8DQNBandit,
  'Paper12QuARC': Paper12QuARCBandit,
  ```
- [ ] Update runner to instantiate with paper-specific configs

---

## Phase 3: Testing

### 3.1 Import Validation
- [ ] Create `test_paper_imports.py`:
  - [ ] Verify all 5 classes import successfully
  - [ ] Instantiate each with minimal configs
  - [ ] Check for import errors

**Expected Output**: 5 classes instantiated, no import errors

### 3.2 Minimal Functionality Tests

**Paper #2 Test** (`test_paper2_minimal.py`)
- [ ] Create environment with Paper2 noise params
- [ ] Create Paper2UCBBandit instance
- [ ] Run 400 frames
- [ ] Verify `convergence_step` metric < 300
- [ ] Check convergence plot

**Paper #5 Test** (`test_paper5_minimal.py`)
- [ ] Test all feedback types: 'link', 'path', 'combined'
- [ ] Run 300 frames each
- [ ] Verify `feedback_granularity_gain` metric exists

**Paper #7 Test** (`test_paper7_minimal.py`)
- [ ] Test all network scales: 'small', 'medium', 'large'
- [ ] Run 200 frames
- [ ] Verify `topk_accuracy` > 0.7

**Paper #8 Test** (`test_paper8_minimal.py`)
- [ ] Create DQN bandit
- [ ] Run 500 frames
- [ ] Verify Q-values converge

**Paper #12 Test** (`test_paper12_minimal.py`)
- [ ] Create QuARC bandit with 3 clusters
- [ ] Run 400 frames
- [ ] Verify `starvation_events` < 50

### 3.3 Code Quality Checks
- [ ] Run: `python -m py_compile daqr/paper_testbeds.py`
- [ ] Run: `python -m py_compile daqr/cross_paper_evaluation.py`
- [ ] No syntax errors, all imports valid

---

## Phase 4: Evaluation & Results

### 4.1 Single-Paper Evaluations
- [ ] **Paper #2 Full Evaluation** (`run_paper2_evaluation.py`)
  - [ ] Run with: Paper2UCB, GNeuralUCB, EXPNeuralUCB
  - [ ] Horizon: 400-1400 frames
  - [ ] Experiments: 5 runs minimum
  - [ ] Save: `results/paper2_results.pkl`
  - [ ] Expected metrics: convergence_step, cumulative_reward, wall_clock_time

- [ ] **Paper #5 Full Evaluation** (`run_paper5_evaluation.py`)
  - [ ] Save: `results/paper5_results.pkl`
  - [ ] Compare feedback types

- [ ] **Paper #7 Full Evaluation** (`run_paper7_evaluation.py`)
  - [ ] Save: `results/paper7_results.pkl`
  - [ ] Compare network scales

- [ ] **Paper #8 Full Evaluation** (`run_paper8_evaluation.py`)
  - [ ] Save: `results/paper8_results.pkl`

- [ ] **Paper #12 Full Evaluation** (`run_paper12_evaluation.py`)
  - [ ] Save: `results/paper12_results.pkl`

### 4.2 Cross-Paper Comparison
- [ ] Create `generate_cross_paper_report.py`
- [ ] Load all 5 result files
- [ ] Compute comparison metrics:
  - [ ] Convergence speed (step count)
  - [ ] Sample efficiency (cumulative reward)
  - [ ] Robustness to noise
  - [ ] Computational overhead
- [ ] Generate markdown report: `results/CROSS_PAPER_COMPARISON.md`
- [ ] Generate comparison table: `results/COMPARISON_TABLE.md`

### 4.3 Generate Comparison Table

Create `results/COMPARISON_TABLE.md`:

```markdown
# Cross-Paper Testbed Comparison

| Paper | Test Scenario | Metric | Value | Paper Baseline | Gap | Status |
|-------|---------------|--------|-------|-----------------|-----|--------|
| #2 | Synchronized | Convergence (steps) | X | Y | Z% | ✅ |
| #2 | Non-sync | Convergence (steps) | X | Y | Z% | ✅ |
| #5 | Link Feedback | Feedback Gain | X | Y | Z% | ✅ |
| #5 | Path Feedback | Feedback Gain | X | Y | Z% | ✅ |
| #7 | Small Network | Top-K Accuracy | X% | Y% | Z% | ✅ |
| #7 | Large Network | Load Balance | X | Y | Z% | ✅ |
| #8 | DQN Routing | Q-Convergence | X | Y | Z% | ✅ |
| #12 | Clustering | Starvation Events | X | Y | Z% | ✅ |
```

---

## Phase 5: Documentation Updates

### 5.1 Update TESTBEDS.md
- [ ] Add entries for all 5 papers
- [ ] Update status matrix with evaluation results
- [ ] Link to detailed reports in `/docs`

### 5.2 Create Paper-Specific Documents (if not already done)
- [ ] `docs/Paper5_Integration_Report.md`
- [ ] `docs/Paper7_Integration_Report.md`
- [ ] `docs/Paper8_Integration_Report.md`
- [ ] `docs/Paper12_Integration_Report.md`
- [ ] (Paper2 already done per `DOCUMENTATION_STRUCTURE.md`)

### 5.3 Update README.md
- [ ] Add section: "Running Paper-Specific Testbeds"
- [ ] Include quick-start command examples
- [ ] Link to TESTBEDS.md

### 5.4 Create INTEGRATION_GUIDE.md (new)
- [ ] Step-by-step integration instructions
- [ ] File placement diagram
- [ ] Expected outputs checklist
- [ ] Troubleshooting section

---

## Phase 6: Final Review & Merge

### 6.1 Code Review
- [ ] All 5 bandit classes follow same interface
- [ ] Docstrings present for all public methods
- [ ] No code duplication between papers
- [ ] Error handling for invalid parameters

### 6.2 Git Workflow
- [ ] Stage changes: `git add daqr/ results/ docs/`
- [ ] Create commit: `git commit -m "Feat: Integrate all 5 paper testbeds"`
- [ ] Push to branch: `git push origin paper-testbeds-integration`
- [ ] Create pull request with summary
- [ ] Merge after review

### 6.3 Tag Release
- [ ] Create version tag: `git tag v1.0-paper-testbeds`
- [ ] Push tag: `git push origin v1.0-paper-testbeds`

---

## Success Criteria

### ✅ Minimum (Before Testing)
- [ ] All 5 bandit classes instantiate without errors
- [ ] Configs added to experiment_config.py
- [ ] Algorithm registry updated
- [ ] Code compiles: `python -m py_compile daqr/paper_testbeds.py`

### ✅ Target (After Full Evaluation)
- [ ] All 5 papers evaluated successfully
- [ ] Cross-paper comparison table generated
- [ ] Results directory has 5 .pkl files + markdown reports
- [ ] Documentation updated
- [ ] Ready for supervisor review

### ✅ Stretch (Polish & Analysis)
- [ ] 10+ paper comparisons (2+ scenarios per paper)
- [ ] Effect size analysis with confidence intervals
- [ ] Statistical significance testing
- [ ] Publication-ready figures and tables

---

## Time Estimates

| Phase | Task | Est. Time | Status |
|-------|------|-----------|--------|
| 1 | Setup & infrastructure | 1 hour | ⏳ |
| 2 | Core implementation | 3-4 hours | ⏳ |
| 3 | Testing | 2-3 hours | ⏳ |
| 4 | Evaluation & results | 4-6 hours | ⏳ |
| 5 | Documentation | 1-2 hours | ⏳ |
| 6 | Review & merge | 30 min | ⏳ |
| **TOTAL** | | **12-18 hours** | ⏳ |

---

## File Structure After Completion

```
quantum_mab_research/
├── README.md (updated with paper testbeds section)
├── TESTBEDS.md (updated with all 5 papers)
├── INTEGRATION_GUIDE.md (new)
├── docs/
│   ├── Paper2_Integration_Report.md (existing)
│   ├── Paper2_Quick_Reference.md (existing)
│   ├── Paper2_Test_Commands.md (existing)
│   ├── Paper5_Integration_Report.md (new)
│   ├── Paper5_Quick_Reference.md (new)
│   ├── Paper7_Integration_Report.md (new)
│   ├── Paper7_Quick_Reference.md (new)
│   ├── Paper8_Integration_Report.md (new)
│   ├── Paper8_Quick_Reference.md (new)
│   ├── Paper12_Integration_Report.md (new)
│   ├── Paper12_Quick_Reference.md (new)
│   └── CROSS_PAPER_ANALYSIS.md (new)
├── daqr/
│   ├── base_bandit.py (existing)
│   ├── neural_bandits.py (existing)
│   ├── network_environment.py (existing)
│   ├── experiment_config.py (updated)
│   ├── experiment_runner.py (updated)
│   ├── multi_run_evaluator.py (existing)
│   ├── paper_testbeds.py (new)
│   └── cross_paper_evaluation.py (new)
├── results/
│   ├── paper2_results.pkl (new)
│   ├── paper5_results.pkl (new)
│   ├── paper7_results.pkl (new)
│   ├── paper8_results.pkl (new)
│   ├── paper12_results.pkl (new)
│   ├── COMPARISON_TABLE.md (new)
│   └── CROSS_PAPER_COMPARISON.md (new)
└── tests/
    ├── test_paper_imports.py (new)
    ├── test_paper2_minimal.py (new)
    ├── test_paper5_minimal.py (new)
    ├── test_paper7_minimal.py (new)
    ├── test_paper8_minimal.py (new)
    ├── test_paper12_minimal.py (new)
    ├── run_paper2_evaluation.py (new)
    ├── run_paper5_evaluation.py (new)
    ├── run_paper7_evaluation.py (new)
    ├── run_paper8_evaluation.py (new)
    └── run_paper12_evaluation.py (new)
```

---

## Next Steps

1. **Start Phase 1**: Verify all files and dependencies
2. **Follow checklist** sequentially through each phase
3. **Test each paper** before moving to next one
4. **Document results** in markdown for easy reference
5. **Commit frequently** to git with clear messages
6. **Reference existing docs**: Leverage Paper2 structure for Papers 5, 7, 8, 12

---

**Ready to begin? Start with Phase 1 setup! 🚀**
