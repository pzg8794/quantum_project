# Paper 7 vs Paper 12 Testing Strategy

## Overview

Following the successful pattern established for Paper 7, we've created a parallel unit test suite for Paper 12 (QuARC) physics validation.

## Side-by-Side Comparison

### File Structure

| Aspect | Paper 7 | Paper 12 |
|--------|---------|---------|
| **Test File** | `run_paper7_sanity_tests.py` | `run_paper12_sanity_tests.py` |
| **Location** | `Dynamic_Routing_Eval_Framework/` | `Dynamic_Routing_Eval_Framework/` |
| **Lines** | 377 | 650+ |
| **Execution Time** | ~0.1s | ~0.1s |
| **Dependencies** | DAQR, NetworkX, NumPy | DAQR, NetworkX, NumPy |

### Test Coverage

#### Paper 7 Tests (3 tests)
1. **Topology + Paths**: AS topology, k-shortest paths generation
2. **Context Ranges**: Hop count, avg degree, path length validation
3. **Reward Samples**: Reward function across modes (neg_hop, neg_degree, etc.)

#### Paper 12 Tests (5 tests)
1. **Topology + Paths**: Waxman topology, 4 random S-D paths
2. **Context Features**: Hop count, normalized degree, fusion probability
3. **Reward Ranges**: Per-arm rewards, [5,100] range validation
4. **Physics Parameters**: Fusion/entanglement probabilities, combined success rate
5. **Integration Format**: Match notebook dictionary structure

### Test Entry Points

```bash
# Paper 7
cd Dynamic_Routing_Eval_Framework
python run_paper7_sanity_tests.py

# Paper 12
cd Dynamic_Routing_Eval_Framework
python run_paper12_sanity_tests.py
```

### Output Format

Both generate:
- **Console Output**: Detailed test results with ✅/❌ indicators
- **JSON Results**: `results/paper7_sanity_tests.json` or `results/paper12_sanity_tests.json`
- **Exit Code**: 0 (all pass) or 1 (some fail)

Example:
```
✅ ALL TESTS PASSED

🎯 Paper 7 integration verified successfully!
   Ready to run allocator experiments...
```

## Key Differences

### Physics Model
| Aspect | Paper 7 | Paper 12 |
|--------|---------|---------|
| **Topology** | Real AS data or synthetic BA | Waxman (100 nodes, ~7 avg degree) |
| **Paths** | k-shortest between qISPs | 4 random S-D pairs |
| **Context Features** | [hop, avg_degree, path_length] | [hop, norm_degree, fusion_prob] |
| **Rewards** | Optional context-aware | Always 35 arms with [8,10,8,9] structure |

### Parameter Validation

**Paper 7**:
- Synthetic vs Real topology selection
- k-shortest path generation parameters
- Reward function modes (neg_hop, neg_degree, neg_length)
- Path length ranges

**Paper 12**:
- **Fusion probability**: 0.95 ✓ (critical parameter)
- **Entanglement probability**: 0.80 ✓ (critical parameter)
- **Combined success**: 0.76 = 0.95 × 0.80 ✓ (fixes original 54% issue)
- **Context shapes**: [(8,3), (10,3), (8,3), (9,3)] ✓
- **Reward ranges**: [5, 100] ✓ (framework recognition threshold)

## Usage Workflow

### For Paper 7
```bash
# Initial validation
python run_paper7_sanity_tests.py

# After topology changes
python run_paper7_sanity_tests.py

# Quick check of paths/contexts
python run_paper7_sanity_tests.py
```

### For Paper 12
```bash
# Initial validation (ALWAYS before notebook run)
python run_paper12_sanity_tests.py

# After physics parameter adjustments
python run_paper12_sanity_tests.py

# Verify reward generation before allocators
python run_paper12_sanity_tests.py

# Before running full framework
python run_paper12_sanity_tests.py
```

## Test Assertions (Paper 12 Specifics)

### Critical Assertions
```python
# Physics parameters
assert fusion_prob == 0.95, "Fusion probability not adjusted"
assert entanglement_prob == 0.80, "Entanglement probability not adjusted"
assert combined_success == 0.76, "Combined rate should be 76%"

# Context structure
assert contexts[0].shape == (8, 3), "Path 0 should have 8 arms with 3 features"
assert contexts[1].shape == (10, 3), "Path 1 should have 10 arms"
assert contexts[2].shape == (8, 3), "Path 2 should have 8 arms"
assert contexts[3].shape == (9, 3), "Path 3 should have 9 arms"

# Feature validation
assert all(ctx[:, 2] == 0.95 for ctx in contexts), "Feature 3 should be fusion_prob"

# Reward range
assert 5 <= min(all_rewards) <= max(all_rewards) <= 100, "Rewards in [5, 100]"
```

## Integration with Notebook

### Before Running Allocators
```python
# In notebook cell (setup phase)
# 1. Run cell 1 (imports) - provides all dependencies
# 2. Run cell 6 (physics params) - defines get_physics_params()
# 3. Run cells 7-10 (allocators) - now have correct rewards

# Alternative: Just run unit tests first
!python run_paper12_sanity_tests.py

# If all tests pass ✅, then notebook is ready
```

### After Code Changes
```python
# If you modify get_physics_params_paper12():
# 1. Run unit tests to validate immediately
python run_paper12_sanity_tests.py

# 2. Check JSON results for specifics
cat results/paper12_sanity_tests.json

# 3. Only if tests pass, then run notebook allocators
```

## Performance Metrics

### Test Execution Time
```
Paper 7: ~0.1 seconds
Paper 12: ~0.1 seconds
Full Notebook: ~5-10 minutes
```

### When to Use Each

| Scenario | Use | Why |
|----------|-----|-----|
| Quick validation | Unit tests | Fast (0.1s) |
| Physics changes | Unit tests first | Fast feedback |
| New reward function | Unit tests | Easy to debug |
| Full allocator run | Notebook + tests | Comprehensive |
| Continuous integration | Unit tests | Fast CI/CD |

## Test Results Interpretation

### All Tests Pass ✅
```json
{
  "topology_paths": {"ok": true},
  "context_features": {"ok": true},
  "reward_ranges": {"ok": true},
  "physics_params": {"ok": true},
  "integration_format": {"ok": true}
}
```
→ **Action**: Ready to run notebook allocators

### Some Tests Fail ❌
```json
{
  "physics_params": {
    "ok": false,
    "fusion_prob": 0.90  // Should be 0.95!
  }
}
```
→ **Action**: Check `get_physics_params_paper12()` configuration

## Extending the Test Suite

### Paper 7 Extensions
```python
def test_paper7_topology_connectivity():
    """Verify topology is connected."""
    # Test code here
```

### Paper 12 Extensions
```python
def test_paper12_context_correlations():
    """Verify context features show realistic variation."""
    # Test code here

def test_paper12_reward_distribution():
    """Verify reward distribution matches Beta parameters."""
    # Test code here

def test_paper12_allocator_input_format():
    """Verify output format matches allocator input requirements."""
    # Test code here
```

## Conclusion

The Paper 12 unit test suite follows the proven Paper 7 testing pattern:
- ✅ Quick validation (~0.1s)
- ✅ Isolated component testing
- ✅ Clear PASS/FAIL indicators
- ✅ JSON result logging
- ✅ Executable documentation
- ✅ Easy integration workflow

**Best Practice**: Always run `python run_paper12_sanity_tests.py` before executing notebook allocators to catch configuration errors immediately.
