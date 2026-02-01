# Paper 12 Allocator Evaluation - Notebook Execution Guide

## Overview

You're ready to run the notebook end-to-end with two parameter configurations to compare results.

---

## VERSION 1: ADJUSTED PARAMETERS (Run First)

### Configuration
- **Parameters**: `fusion_prob=0.95`, `entanglement_prob=0.80`
- **Base Frames**: 4000
- **Frame Step**: 2000  
- **Runs**: 3
- **Expected Success Rate**: 76% (0.95 × 0.80)
- **Purpose**: Validate optimized parameters work end-to-end without timeouts

### Status
✅ **Ready to run** - Notebook is already configured with these values in Cell 4

### How to Run

**Option A: From VS Code**
1. Open the notebook: `quantum_project_hub/notebooks/H-MABs_Eval-T_XQubit_Alloc_XQRuns copy.ipynb`
2. Click **"Run All"** (Ctrl+Shift+Alt+Enter or via Run menu)
3. Wait for all cells to complete (~30-45 minutes estimated)

**Option B: From Terminal**
```bash
source ~/.quantum/bin/activate
cd ~/DataScience/Semester4/GA-Work/quantum_project_hub/notebooks

jupyter nbconvert --to notebook --execute \
  "H-MABs_Eval-T_XQubit_Alloc_XQRuns copy.ipynb" \
  --ExecutePreprocessor.timeout=3600 \
  --inplace
```

### Expected Output
- Cell 13-15 (allocators): Should show completion messages for each allocator
- No "Max retries reached" errors (that was the original problem)
- Reward distributions in [5-100] range
- Results saved to framework state directories

---

## VERSION 2: BASELINE PARAMETERS (Run After V1)

### Configuration
- **Parameters**: `fusion_prob=0.9`, `entanglement_prob=0.6`
- **Base Frames**: 4000 (same as V1)
- **Frame Step**: 2000 (same as V1)
- **Runs**: 3 (same as V1)
- **Expected Success Rate**: 54% (0.9 × 0.6)
- **Purpose**: Compare official Paper 12 baseline performance vs optimized

### How to Switch

**In Cell 4 of the notebook, change these two lines:**

From (current):
```python
'fusion_prob': 0.95,         # ✅ ADJUSTED: 0.9→0.95 (baseline: 0.9)
'entanglement_prob': 0.80,   # ✅ ADJUSTED: 0.6→0.80 (baseline: 0.6)
```

To (baseline):
```python
'fusion_prob': 0.9,          # Official Paper 12 baseline
'entanglement_prob': 0.6,    # Official Paper 12 baseline
```

**Then run the notebook again (Run All)**

---

## What Each Allocator Tests

**Cells 13-15 will execute**:
1. **Cell 13** (Dynamic Allocator)
   - MAB algorithm with dynamic arm selection
   - Tests reward learning with 4000 frames
   
2. **Cell 14** (Thompson Sampling)
   - Probabilistic exploration-exploitation
   - Compares against Dynamic approach
   
3. **Cell 15** (Random Baseline)
   - Random arm selection (for comparison)
   - Establishes performance floor

Each allocator outputs:
- Completion status
- Success/failure counts
- Reward statistics
- Time taken

---

## Comparison Data You'll Gather

After running both versions, you'll have:

| Metric | V1 (0.95, 0.80) | V2 (0.9, 0.6) |
|--------|-----------------|---------------|
| Success Rate | 76% | 54% |
| Allocator Timeouts | Expected: None | ? |
| Reward Mean | ~42-47 | ? |
| Allocator Speed | ? | ? |
| Learning Quality | ? | ? |

This gives you empirical evidence for choosing parameters.

---

## Next Steps After Paper 12

Once you have V1 & V2 results:

1. **Paper 7 (QBGP)**
   - Change `PHYSICS_MODELS = ['paper12']` to `['paper7']`
   - Run V1 and V2 with same parameter pattern
   
2. **Paper 2 (Neural Bandit)**
   - Change `PHYSICS_MODELS = ['paper7']` to `['paper2']`
   - Run V1 and V2 with same parameter pattern

3. **Comparison Analysis**
   - 6 runs total (3 papers × 2 versions each)
   - Generate comparison table
   - Document findings

---

## Troubleshooting

**If you get "Max retries reached":**
- This was the original problem - adjust parameters up (higher fusion/entanglement)
- Current V1 should NOT have this issue

**If allocators timeout:**
- May indicate 4000 frames is too many for this setup
- Try reducing to 2000 frames as a test

**If notebook won't run:**
- Check that paths to topology files exist
- Verify all imports are available: `import daqr`
- Check /hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/ exists

---

## Documentation References

- **Parameter Analysis**: [PAPER12_PARAMETERS_VALIDATION.md](../PAPER12_PARAMETERS_VALIDATION.md)
- **Unit Tests**: [run_paper12_sanity_tests.py](../hybrid_variable_framework/Dynamic_Routing_Eval_Framework/run_paper12_sanity_tests.py)
- **Test Results**: [results/paper12_sanity_tests.json](../hybrid_variable_framework/Dynamic_Routing_Eval_Framework/results/paper12_sanity_tests.json)

---

**Ready to run? Start with VERSION 1 - your intuition was correct!**
