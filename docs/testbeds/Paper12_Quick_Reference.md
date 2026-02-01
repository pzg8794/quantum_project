# Paper 12 - Quick Reference

**Paper**: Wang et al. 2024 - QuARC (Qubit Allocation in Quantum Networks)  
**Testbed Location**: `Dynamic_Routing_Eval_Framework/`  
**Status**: ✅ Fully Integrated with Comprehensive Testing

---

## Overview

Paper 12 implements QuARC - qubit allocation with fusion gates. Python implementation with baseline physics parameters (fusion=0.9, entanglement=0.6) achieving 54% combined success rate.

---

## Key Parameters (Baseline)

```
Fusion Probability (q): 0.9
Entanglement Probability (E_p): 0.6
Combined Success Rate: 54% (0.9 × 0.6) ✅ CORRECT
Network Nodes: 100
Average Degree: 6 (Waxman topology)
S-D Pairs: 10
Total Timeslots: 5000
```

---

## Core Implementation

| File | Purpose |
|------|---------|
| `run_paper12_sanity_tests.py` | Main unit test suite (6 tests) |
| `run_tests.sh` | Bash test runner |
| Notebook integration files | Framework integration |

---

## Testing

- **Type**: Automated unit tests (6 tests)
- **Status**: ✅ All passing
- **Test Command**: `python run_paper12_sanity_tests.py`
- **Results**: `results/paper12_sanity_tests.json`
- **Execution Time**: ~0.1 seconds
- **Guide**: See [Paper12_Testing_Guide.md](Paper12_Testing_Guide.md)

---

## Key Features

✅ Baseline parameters (0.9, 0.6) officially validated  
✅ 54% success rate is EXPECTED and CORRECT  
✅ Comprehensive unit test coverage (6 tests)  
✅ Full documentation suite  
✅ Allocator execution framework  
✅ Parameter validation  

---

## Quick Start

```bash
cd hybrid_variable_framework/Dynamic_Routing_Eval_Framework/

# Run unit tests
python run_paper12_sanity_tests.py

# View results
cat results/paper12_sanity_tests.json | python -m json.tool
```

---

## Next Steps

1. Review [Paper12_Testing_Guide.md](Paper12_Testing_Guide.md)
2. Run tests: `python run_paper12_sanity_tests.py`
3. Check [Paper12_Parameters.md](Paper12_Parameters.md) for details
4. Review allocator execution in main README

---

**See Also**: [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md)
