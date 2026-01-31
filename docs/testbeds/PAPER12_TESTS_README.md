# Paper 12 (QuARC) Unit Tests - Standalone Test Suite

## Overview

This directory contains a comprehensive standalone test suite for validating the Paper 12 (QuARC) physics integration in the H-MABs evaluation framework.

**Test File**: `run_paper12_sanity_tests.py`

## Why Standalone Tests?

Following the pattern established with Paper 7, we create lightweight Python unit tests rather than relying solely on notebook-based testing because:

1. **Speed**: Focused unit tests run in ~0.1s vs full notebook in several minutes
2. **Isolation**: Tests verify individual components independently 
3. **Repeatability**: Easy to re-run and validate after code changes
4. **CI/CD Ready**: Can be integrated into continuous integration pipelines
5. **Documentation**: Test code serves as executable specification of expected behavior

## What Gets Tested?

### Test 1: Topology + Paths
- Waxman topology generation (100 nodes, ~7 avg degree)
- Random S-D path generation (4 paths)
- Correct context shapes: `[(8,3), (10,3), (8,3), (9,3)]`
- Execution time validation

### Test 2: Context Feature Validation
- Feature 1 (hop_count): Constant per path ✓
- Feature 2 (normalized_avg_degree): In [0,1] range ✓
- Feature 3 (fusion_prob): Matches configured value (0.9) ✓
- All features verified against Paper 12 specification

### Test 3: Reward Range Validation
- Reward count: [8, 10, 8, 9] arms per path ✓
- Reward range: [5, 100] for framework recognition ✓
- Average rewards: ~40-70 per path (meaningful for MAB algorithms) ✓
- Total aggregate reward validated

### Test 4: Physics Parameters (Baseline)
- Fusion probability: 0.9 ✓
- Entanglement probability: 0.6 ✓
- Combined success rate: 0.54 = 0.9 × 0.6 (54%) ✓
- Noise model initialized correctly ✓
- Fidelity calculator initialized correctly ✓

### Test 5: Integration Format Check
- All required keys present ✓
- Correct data types (Graph, lists, dict) ✓
- Format matches notebook expectations ✓

### Test 6: Baseline Parameters (Official Paper 12)  
- Fusion probability: 0.9 (official Paper 12 value) ✓
- Entanglement probability: 0.6 (official Paper 12 value) ✓
- Combined success rate: 0.54 = 0.9 × 0.6 (54% - EXPECTED, AUTHENTIC) ✓
- Validates baseline works correctly with fixed reward code ✓
- Notes: 54% baseline is NOT a problem - this is the correct authentic rate

## Key Assertions

The test suite verifies these Paper 12 baseline settings:

| Parameter | Expected | Actual | Status |
|-----------|---|---|---|
| Fusion Probability | 0.9 | 0.9 | ✅ |
| Entanglement Probability | 0.6 | 0.6 | ✅ |
| Combined Success Rate | 0.54 (54%) | 0.54 | ✅ |
| Topology Nodes | 100 | 100 | ✅ |
| Paths | 4 | 4 | ✅ |
| Context Shapes | (8,3), (10,3), (8,3), (9,3) | ✓ | ✅ |
| Reward Range | [5, 100] | ✓ | ✅ |
| Avg Reward | >30 | ~39 | ✅ |

## Running the Tests

### From Repository Root

```bash
# Activate environment
source .quantum/bin/activate

# Navigate to test directory
cd hybrid_variable_framework/Dynamic_Routing_Eval_Framework

# Run tests
python run_paper12_sanity_tests.py
```

### Expected Output

```
======================================================================
PAPER 12 (QuARC) SANITY TESTS - STANDALONE VERSION
======================================================================

This test suite validates Paper 12 baseline physics implementation:
  ✓ Baseline parameters: fusion_prob=0.9, entanglement_prob=0.6
  ✓ Success rate: 54% = 0.9 × 0.6
  ✓ Context structure: [hop_count, norm_degree, fusion_prob]
  ✓ Reward range: [5, 100] for framework recognition
  ✓ Integration format: matches notebook expectations

... (5 test sections with detailed output) ...

✅ ALL TESTS PASSED

🎯 Paper 12 baseline validated successfully!
   Confirmed with:
   - Fusion probability: 0.9
   - Entanglement probability: 0.6
   - Success rate: 54%
```

### Test Results File

After running, results are saved to:
```
results/paper12_sanity_tests.json
```

Example output:
```json
{
  "topology_paths": {
    "nodes": 100,
    "edges": 376,
    "num_paths": 4,
    "context_shapes": [[8,3], [10,3], [8,3], [9,3]],
    "ok": true
  },
  "context_features": {
    "num_contexts": 4,
    "fusion_prob_in_contexts": 0.9,
    "ok": true
  },
  "reward_ranges": {
    "total_arms": 35,
    "total_reward": 1641.95,
    "avg_reward": 46.91,
    "ok": true
  },
  "physics_params": {
    "fusion_prob": 0.9,
    "entanglement_prob": 0.6,
    "combined_success_rate": 0.54,
    "ok": true
  },
  "integration_format": {
    "ok": true
  }
}
```

## Test Structure

The file contains:

1. **Inline Helper Functions** (lines ~1-150)
   - `generate_paper12_paths()`: Create 4 random S-D paths
   - `generate_paper12_contexts()`: Generate context vectors
   - `generate_paper12_rewards()`: Generate per-arm rewards
   - `get_physics_params_paper12()`: Main physics generator

2. **Test Functions** (lines ~150-400)
   - `test_paper12_topology_and_paths()`
   - `test_paper12_context_features()`
   - `test_paper12_reward_ranges()`
   - `test_paper12_physics_parameters()`
   - `test_paper12_integration_with_notebook()`

3. **Main Entry Point** (lines ~400-500)
   - Runs all 5 tests sequentially
   - Collects results and generates JSON summary
   - Prints clear PASS/FAIL status

## Comparison with Notebook

| Aspect | Notebook | Standalone Tests |
|--------|----------|------------------|
| **Speed** | ~5-10 min (full run) | ~0.1 sec |
| **Output** | Interactive cells | Focused test results |
| **Reproducibility** | Kernel state dependent | Fully deterministic |
| **Debugging** | Harder (cell dependencies) | Easier (isolated tests) |
| **Version Control** | Hard to track changes | Easy to diff/compare |

## Validation Workflow

When modifying Paper 12 physics:

```bash
# 1. Change parameters in notebook's get_physics_params_paper12()
#    (Currently using baseline: fusion=0.9, entanglement=0.6)

# 2. Run unit tests to validate immediately
python run_paper12_sanity_tests.py

# 3. Check JSON results
cat results/paper12_sanity_tests.json

# 4. If all tests pass, run full notebook allocator
#    If tests fail, debug specific issue in isolation
```

## Key Implementation Details

### Context Structure
Each path generates a context matrix with shape `(K, 3)`:
- **Row 0**: `[hop_count, normalized_avg_degree, fusion_prob]`
- **Row 1**: Same as Row 0 (features constant per path)
- **...Row K-1**: Same as Row 0

Example (Path 0 with 8 arms):
```
[[2.0, 0.689, 0.9],
 [2.0, 0.689, 0.9],
 [2.0, 0.689, 0.9],
 ...(8 total rows)]
```

### Reward Generation
Each path generates a reward list with length `K`:
- Base probability from entanglement and path length
- Beta distribution adds realistic variation
- Scaled to [5, 100] range for framework recognition

Example (Path 0 with 8 arms):
```
[44.3, 33.9, 29.1, 41.5, 38.2, 52.7, 45.1, 39.8]
```

### Physics Parameters (Baseline)
```python
fusion_prob = 0.9          # Fusion gate success (Paper 12 baseline)
entanglement_prob = 0.6    # Entanglement success (Paper 12 baseline)
combined_success = 0.54    # 0.9 × 0.6 = 54% (authentic Paper 12 rate)
```

## Troubleshooting

### Test Failure: "Could not find 4 valid paths"
- Topology generation incomplete
- Try increasing max_attempts in `generate_paper12_paths()`

### Test Failure: "Reward out of [0, 100] range"
- Beta distribution generating edge case values
- Check parameters in `generate_paper12_rewards()`

### Test Failure: "fusion_prob not in contexts"
- Context generation not applying configured value
- Verify `generate_paper12_contexts()` passes fusion_prob correctly

### Test Failure: "Wrong context shapes"
- Arms per path mismatch
- Check `arms_per_path = [8, 10, 8, 9]` in context generation

## Extending Tests

To add new tests:

1. Create `test_new_feature()` function
2. Run `get_physics_params_paper12()` to get result dict
3. Make assertions on result structure/values
4. Add to `summary` dict in `main()`

Example:
```python
def test_paper12_topology_edges():
    """Verify topology edge count is reasonable."""
    result = get_physics_params_paper12(seed=42)
    topo = result["external_topology"]
    
    expected_min_edges = 200
    actual_edges = len(topo.edges())
    
    ok = actual_edges >= expected_min_edges
    print(f"Topology edges: {actual_edges} (expected >= {expected_min_edges})")
    
    return {"edges": actual_edges, "ok": ok}
```

## References

- **Paper 7 Tests**: `run_paper7_sanity_tests.py` (similar structure)
- **Notebook Physics**: `notebooks/H-MABs_Eval-T_XQubit_Alloc_XQRuns copy.ipynb` (cell 6)
- **DAQR Physics**: `src/daqr/core/quantum_physics.py`
- **DAQR Topology**: `src/daqr/core/topology_generator.py`

## Author Notes

This test suite was created to:
- Validate Paper 12 baseline parameters (0.9 fusion, 0.6 entanglement)
- Ensure context and reward structures match notebook expectations
- Provide quick feedback when modifying physics parameters
- Serve as executable documentation of Paper 12 integration

It mirrors the approach successfully used for Paper 7 testing and should be run before executing full allocator experiments.
