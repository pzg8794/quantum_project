# Paper 12 - Parameters & Validation

**Paper**: Wang et al. 2024 - QuARC  
**Status**: ✅ Baseline Validated and Documented  
**Last Updated**: January 30, 2026

---

## Official Baseline (Wang et al. 2024)

### Core Physics Parameters
```python
fusion_prob (q): 0.9              # Fusion gate success
entanglement_prob (E_p): 0.6      # Entanglement success
combined_success: 0.54 (54%)      # 0.9 × 0.6 = authentic rate
```

### Network Configuration
```python
n_nodes: 100                       # Network size
avg_degree: 6                      # Average node connectivity
topology_type: 'Waxman'            # Waxman random topology
num_sd_pairs: 10                   # Source-destination pairs
total_timeslots: 5000              # Simulation length
```

---

## Important Note

**The 54% success rate is EXPECTED and CORRECT.**

This is the authentic Paper 12 baseline. It is not a problem or limitation. The framework operates correctly with these parameters when reward generation code is properly implemented (using Beta distribution).

---

## Parameter Validation

### Baseline Parameters Tested
✅ fusion_prob = 0.9  
✅ entanglement_prob = 0.6  
✅ combined = 0.54 (54%)  
✅ Topology: 100 nodes, avg degree 6  
✅ S-D pairs: 10  
✅ Timeslots: 5000  

### Test Coverage
- **Test 1-5**: Framework integration tests
- **Test 6**: Baseline parameter validation

**All tests passing**: ✅

---

## Framework Configuration

### In Notebook/Framework
```python
FRAMEWORK_CONFIG['paper12'] = {
    'fusion_prob': 0.9,          # ✅ Official baseline
    'entanglement_prob': 0.6,    # ✅ Official baseline
    'n_nodes': 100,              # ✅ Standard topology
    'avg_degree': 6,             # ✅ E_d: Average degree
    'num_sd_pairs': 10,          # ✅ nsd: S-D pairs
    'total_timeslots': 5000,     # ✅ T: Simulation length
}
```

---

## Baseline Performance

### Physics
- **Success Rate**: 54% (authentic Paper 12)
- **Fidelity**: Per-hop fidelity calculations
- **Noise Model**: FusionNoiseModel (implemented)
- **Fidelity Calculator**: FusionFidelityCalculator (implemented)

### Allocator Results
- **Contexts**: Valid shapes [8,3], [10,3], [8,3], [9,3] ✅
- **Rewards**: Range [5-100], avg ~39 ✅
- **Framework**: Compatible and functional ✅
- **Baseline**: Works correctly with fixed reward code ✅

---

## Parameter Ranges (From Paper)

From Wang et al. 2024 Figure 6 and experiments:
```
E_p (entanglement_prob): [0.3, 0.6]      # Main evaluation range
q (fusion_prob): [0.6, 0.7, 0.8, 0.9, 1.0]
n (nodes): [50, 100, 200, 400, 800]
```

**Our Configuration**: Uses official baseline (0.9, 0.6) from main paper.

---

## Comparison with Other Papers

| Parameter | Paper 2 | Paper 7 | Paper 12 |
|-----------|---------|---------|----------|
| **Network** | 20 nodes | 100 nodes | 100 nodes |
| **Avg Degree** | 4 | 6 | 6 |
| **Success Rate** | E_p: 0.7, q: 0.9 | Fidelity ≥0.85 | **54% (0.9×0.6)** |
| **Timeslots** | Variable | N/A | 5000 |
| **S-D Pairs** | Variable | 4 | 10 |

---

## Root Cause Analysis

### Original Issue
- Allocators producing 0 rewards with "Max retries reached" error
- Root cause: **Broken reward generation code** (not parameters)

### Solution Applied
- Fixed reward code with Beta distribution + scaling
- **Result**: ✅ Baseline parameters work perfectly

### Evidence
- TEST 6 passes with official baseline (0.9, 0.6)
- 54% success rate is EXPECTED
- Framework generates meaningful rewards
- All unit tests passing

---

## Validation Status

### ✅ Complete Validation
1. [x] Baseline parameters (0.9, 0.6) officially documented
2. [x] 54% success rate validated as correct
3. [x] Unit tests confirm parameters work
4. [x] Reward code fixed and functional
5. [x] Framework compatible with baseline
6. [x] Documentation clarified (no misleading narratives)

---

## Key References

- **Paper**: Wang et al. 2024 (QuARC)
- **Figure 6**: Parameter ranges tested in paper
- **Baseline**: 0.9 fusion, 0.6 entanglement
- **Success Rate**: 54% (authentic, not a problem)

---

## Next Steps

1. Use baseline parameters: fusion=0.9, entanglement=0.6
2. Run unit tests to verify: `python run_paper12_sanity_tests.py`
3. Proceed with allocator experiments
4. Results will match Paper 12 authentic baseline

---

**See Also**: [Paper12_Quick_Reference.md](Paper12_Quick_Reference.md) | [Paper12_Testing_Guide.md](Paper12_Testing_Guide.md)
