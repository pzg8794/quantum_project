# Paper 12 - Testing Guide

**Paper**: Wang et al. 2024 - QuARC  
**Status**: ✅ Comprehensive Testing Framework  
**Last Updated**: January 30, 2026

---

## Testing Overview

Paper 12 has a comprehensive automated testing framework with 6 unit tests covering topology, context features, rewards, physics parameters, integration format, and baseline validation.

---

## Running Tests

### Quick Start
```bash
cd hybrid_variable_framework/Dynamic_Routing_Eval_Framework/

# Run all tests
python run_paper12_sanity_tests.py

# View results
cat results/paper12_sanity_tests.json | python -m json.tool
```

### With Bash Wrapper
```bash
./run_tests.sh
```

---

## Unit Tests Breakdown

### Test 1: Topology & Paths
- **What**: 100-node Waxman topology with 4 random S-D paths
- **Validates**: Correct topology structure and path generation
- **Status**: ✅ Passing

### Test 2: Context Features
- **What**: Context vector validation [hop_count, normalized_degree, fusion_prob]
- **Validates**: Correct context shapes [(8,3), (10,3), (8,3), (9,3)]
- **Status**: ✅ Passing

### Test 3: Reward Ranges
- **What**: Per-arm reward validation
- **Validates**: 35 arms, [5, 100] range, realistic variation
- **Status**: ✅ Passing

### Test 4: Physics Parameters
- **What**: Baseline physics validation
- **Validates**: fusion=0.9, entanglement=0.6, combined=0.54
- **Status**: ✅ Passing

### Test 5: Integration Format
- **What**: Dictionary structure and types
- **Validates**: Matches notebook expectations
- **Status**: ✅ Passing

### Test 6: Baseline Parameters
- **What**: Official Paper 12 baseline
- **Validates**: 0.9, 0.6 with 54% success rate
- **Status**: ✅ Passing

---

## Test Results

Expected output:
```
✅ ALL TESTS PASSED

🎯 Paper 12 baseline validated successfully!
   Confirmed with:
   - Fusion probability: 0.9
   - Entanglement probability: 0.6
   - Success rate: 54%
```

Results saved to: `results/paper12_sanity_tests.json`

---

## Verification Checklist

- [ ] Tests execute without errors
- [ ] All 6 tests show ✅ PASS
- [ ] `results/paper12_sanity_tests.json` created
- [ ] JSON file contains all test results
- [ ] Baseline parameters confirmed (0.9, 0.6, 54%)

---

## Troubleshooting

### Test Failures
1. Check `results/paper12_sanity_tests.json` for specific failure details
2. Review error messages in test output
3. Verify baseline parameters haven't changed

### Missing Results File
1. Ensure test directory has write permissions
2. Check `results/` folder exists
3. Re-run tests

---

## Test Files

- **Main Test Suite**: `run_paper12_sanity_tests.py` (650+ lines)
- **Bash Wrapper**: `run_tests.sh`
- **Results**: `results/paper12_sanity_tests.json`
- **Full Guide**: `PAPER12_TESTS_README.md`
- **Detailed Docs**: See [Paper12_Framework_Quick_Reference.md](Paper12_Framework_Quick_Reference.md)

---

## Parameters Validated

```python
fusion_prob = 0.9           # ✅ Official Paper 12 baseline
entanglement_prob = 0.6     # ✅ Official Paper 12 baseline
combined_success = 0.54     # ✅ 0.9 × 0.6 = 54% (authentic rate)
```

**Important**: 54% baseline success rate is EXPECTED and CORRECT. This is the authentic Paper 12 configuration.

---

## Next Steps

1. Run: `python run_paper12_sanity_tests.py`
2. Verify: All tests pass ✅
3. Review: `results/paper12_sanity_tests.json`
4. Proceed: To allocator experiments with confirmed baseline

---

**See Also**: [Paper12_Quick_Reference.md](Paper12_Quick_Reference.md) | [Paper12_Parameters.md](Paper12_Parameters.md)
