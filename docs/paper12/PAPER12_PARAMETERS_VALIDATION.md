# Paper 12 Parameters - Testbed Configuration

## Paper 12 Official Baseline (Wang et al. 2024 - QuARC)

### Baseline Parameters
- **fusion_prob (q)**: 0.9
- **entanglement_prob (E_p)**: 0.6
- **Combined success rate**: 54% = 0.9 × 0.6

### Topology Configuration
- **n_nodes**: 100
- **avg_degree (E_d)**: 6
- **topology_type**: Waxman
- **num_sd_pairs**: 10
- **total_timeslots**: 5000

### Paper 12 Parameter Ranges (Tested)
- **E_p**: [0.3, 0.6] (main evaluation, Figure 6)
- **q**: [0.6, 0.7, 0.8, 0.9, 1.0]
- **n (nodes)**: [50, 100, 200, 400, 800]

---

## Current Notebook Configuration

**Framework**: `FRAMEWORK_CONFIG['paper12']`

```python
'paper12': {
    'fusion_prob': 0.9,          # ✅ Official baseline
    'entanglement_prob': 0.6,    # ✅ Official baseline
    'n_nodes': 100,              # ✅ Standard topology
    'avg_degree': 6,             # ✅ E_d: Average degree
    'num_sd_pairs': 10,          # ✅ nsd: S-D pairs
    'total_timeslots': 5000,     # ✅ T: Simulation length
}
```

---

## Validation Status

### Unit Tests
- **TEST 1-6**: Official baseline (0.9, 0.6) ✅ PASS

### Baseline Performance
- Contexts: Valid shapes [8,3], [10,3], [8,3], [9,3] ✅
- Rewards: Range [13.5-67.9], avg ~39 ✅
- Success rate: 54% (EXPECTED) ✅
- Reward code: Fixed with Beta distribution ✅

### Framework Compatibility
- Generates valid topology, contexts, rewards ✅
- Noise model initialized correctly ✅
- Fidelity calculator working ✅
- Notebook runs without errors ✅

---

## References

**Paper 12 Repository**: `/Users/pitergarcia/DataScience/Semester4/GA-Work/clustered-quantum-routing`  
**Unit Tests**: `run_paper12_sanity_tests.py`

**Key Files**:
- `main.py` - Function defaults and parameter handling
- `recreate_figs.py` - Actual parameter values used in published figures
- `quarc/` - QuARC protocol implementation

**Figure 6 Parameters** (Main Evaluation):
- E_p ∈ {0.3, 0.6}, q = 0.9, n ∈ {50, 100, 200, 400, 800}

**Our Current Parameters**:
- E_p = 0.6, q = 0.9 (official Paper 12 baseline)
