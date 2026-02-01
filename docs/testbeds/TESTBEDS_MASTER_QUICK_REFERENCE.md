# Quantum Testbeds - Master Quick Reference

**Framework**: H-MABs Evaluation Framework (Multi-Armed Bandits for Quantum Networks)  
**Last Updated**: January 30, 2026  
**Status**: ✅ All three testbeds integrated and organized

---

## Overview

This project integrates three distinct quantum routing research papers into a unified evaluation framework:

1. **Paper 2** (Chaudhary et al. 2023): MAB-based quantum network routing with entanglement swapping
2. **Paper 7** (Liu et al. 2024): QBGP - Quantum BGP with online path selection
3. **Paper 12** (Wang et al. 2024): QuARC - Qubit allocation with fusion gates

---

## Quick Navigation

### 🔗 Master Documents

| Testbed | Quick Ref | Location | Status |
|---------|-----------|----------|--------|
| **Paper 2** | [Paper2_Quick_Reference.md](Paper2_Quick_Reference.md) | `docs/testbeds/` | ✅ Integrated |
| **Paper 7** | [Paper7_Quick_Reference.md](Paper7_Quick_Reference.md) | `docs/testbeds/` | ✅ Integrated |
| **Paper 12** | [Paper12_Quick_Reference.md](Paper12_Quick_Reference.md) | `docs/testbeds/` | ✅ Integrated |

---

## Paper Comparison Matrix

### Research Focus
| Aspect | Paper 2 | Paper 7 | Paper 12 |
|--------|---------|---------|----------|
| **Title** | Quantum Network MAB | QBGP Routing | QuARC Allocation |
| **Authors** | Chaudhary et al. 2023 | Liu et al. 2024 | Wang et al. 2024 |
| **Primary Algorithm** | UCB (Multi-Armed Bandits) | BGP-inspired Protocol | Qubit Allocation |
| **Quantum Focus** | Entanglement swapping | Delay-aware routing | Fusion gate optimization |

### Implementation Details
| Aspect | Paper 2 | Paper 7 | Paper 12 |
|--------|---------|---------|----------|
| **Language** | MATLAB | Python | Python |
| **Test Framework** | Manual testing | Unit tests | Unit tests (6 tests) |
| **Network Sizes** | Up to 200 nodes | 50-400 nodes | 100 nodes (baseline) |
| **Quantum Model** | Fidelity-based | Delay-aware | Fusion success |
| **Testing Status** | ✅ Documented | ✅ Automated | ✅ Automated |

### Baseline Parameters
| Parameter | Paper 2 | Paper 7 | Paper 12 |
|-----------|---------|---------|----------|
| **Network Nodes** | 20 (scalable) | 100 | 100 |
| **Avg Degree** | 4 | 6 | 6 |
| **S-D Pairs** | Variable | 4 | 10 |
| **Key Success Rate** | E_p: 0.7, q: 0.9 | Fidelity: ≥0.85 | Fusion: 0.9, Entangle: 0.6 (54%) |

---

## File Organization by Testbed

### Paper 2 Directory Structure
```
docs/testbeds/
├── Paper2_Quick_Reference.md         ← START HERE
├── Paper2_Integration_Report.md      ← Integration details
├── Paper2_Test_Commands.md           ← Test procedures

Original source: ../../../Testbeds/Paper2-Quantum-Network-MultiArmedBandits-main/
├── MAB_UCB_QNetwork_Routing.m        ← Main algorithm (MATLAB)
├── [other MATLAB implementation files]
├── paper2_chaudhary2023quantum.pdf   ← Research paper
└── paper2_framework.png              ← Architecture diagram
```

### Paper 7 Directory Structure
```
docs/testbeds/
├── Paper7_Quick_Reference.md         ← START HERE
├── Paper7_Summary.md                 ← Comprehensive summary
├── Paper7_Validation.md              ← Validation guide
├── Paper7_vs_Paper12_Testing.md      ← Testing comparison

Original source: ../../../Testbeds/Paper7-lizhuohua-quantum-bgp-online-path-selection-aeb35c0/
│   └── [generated charts and plots]
├── main.py                           ← Main QBGP implementation
├── [other Python implementation files]
├── topology_data/                    ← Network topologies
├── network_benchmarking/             ← Benchmarking utilities
├── paper7_liu2024qbgp.pdf            ← Research paper
└── README.md                         ← Project overview
```

### Paper 12 Directory Structure
```
docs/testbeds/
├── Paper12_Quick_Reference.md        ← START HERE
├── Paper12_Testing_Guide.md          ← Testing procedures
├── Paper12_Parameters.md             ← Parameter documentation
├── Paper12_Framework_Quick_Reference.md
├── PAPER12_TESTING_SUMMARY.md
├── PAPER12_TESTS_README.md

docs/paper12/
├── PAPER12_ALLOCATOR_EXECUTION.md
├── PAPER12_PARAMETERS_VALIDATION.md
├── PAPER12_DOCUMENTATION_UPDATE_COMPLETE.md
├── PAPER12_UPDATES_CHECKLIST.md

Dynamic_Routing_Eval_Framework/
│
├── run_paper12_sanity_tests.py       ← Unit test suite (23 KB)
├── run_paper7_sanity_tests.py        ← Paper 7 unit tests
├── run_tests.sh                      ← Test runner script
│
├── PAPER12_TESTS_README.md           ← Full test documentation
├── PAPER12_TESTING_SUMMARY.md        ← Workflow overview
├── PAPER7_vs_PAPER12_TESTING.md      ← Testing comparison
│
├── results/
│   ├── paper12_sanity_tests.json     ← Paper 12 results
│   └── paper7_sanity_tests.json      ← Paper 7 results
│
└── notebooks/
    └── H-MABs_Eval-T_XQubit_Alloc_XQRuns copy.ipynb
```

### Additional Documentation
```
docs/paper12/
├── PAPER12_ALLOCATOR_EXECUTION.md           ← Allocator execution flow
├── PAPER12_PARAMETERS_VALIDATION.md         ← Parameter validation
├── PAPER12_DOCUMENTATION_UPDATE_COMPLETE.md ← Update tracking
└── PAPER12_UPDATES_CHECKLIST.md             ← Updates made

docs/assessments/
├── ASSESSMENT_CORRECTION_SUMMARY.md         ← Assessment validation
└── BASELINE_ASSESSMENT_QUICK_REF.md         ← Baseline reference
```

---

## Getting Started by Testbed

### Paper 2 (MATLAB-based)
```bash
# 1. Navigate to documentation
cd docs/testbeds/

# 2. Read quick reference
cat Paper2_Quick_Reference.md

# 3. Review integration status
cat Paper2_Integration_Report.md

# 4. Check test commands
cat Paper2_Test_Commands.md
```

### Paper 7 (Python implementation)
```bash
# 1. Navigate to documentation
cd docs/testbeds/

# 2. Read quick reference
cat Paper7_Quick_Reference.md

# 3. Review validation
cat Paper7_Summary.md

# 4. Run unit tests
cd ../../Dynamic_Routing_Eval_Framework/
python run_paper7_sanity_tests.py
```

### Paper 12 (Full test suite - RECOMMENDED)
```bash
# 1. Read documentation
cd docs/testbeds/
cat Paper12_Quick_Reference.md

# 2. Navigate to test framework
cd ../../Dynamic_Routing_Eval_Framework/

# 3. Run unit tests (0.1 seconds)
python run_paper12_sanity_tests.py

# 4. Check results
cat results/paper12_sanity_tests.json | python -m json.tool

# 5. Review complete documentation
cd ../docs/testbeds/
cat PAPER12_TESTS_README.md
```

---

## Testing Summary

### Unit Test Coverage
| Paper | Test File | Tests | Status | Command |
|-------|-----------|-------|--------|---------|
| 12 | `run_paper12_sanity_tests.py` | 6 tests | ✅ All passing | `python run_paper12_sanity_tests.py` |
| 7 | `run_paper7_sanity_tests.py` | 5+ tests | ✅ Available | `python run_paper7_sanity_tests.py` |
| 2 | Manual tests | Per docs | ✅ Documented | See `Paper2_Test_Commands.md` |

### Test Results Location
```
Dynamic_Routing_Eval_Framework/
└── results/
    ├── paper12_sanity_tests.json      (Auto-generated after test run)
    └── paper7_sanity_tests.json       (Auto-generated after test run)
```

---

## Key Parameters by Testbed

### Paper 2 (Baseline)
```
Entanglement Probability (E_p): 0.7
Quantum Gate Fidelity (q): 0.9
Network Nodes: 20 (scalable to 200)
Topology: Standard graph
```

### Paper 7 (Baseline)
```
Network Nodes: 100
Avg Degree: 6 (Waxman topology)
Min Fidelity: 0.85
QoS Threshold: 0.80
S-D Pairs: 4 (in tests)
```

### Paper 12 (Baseline - OFFICIAL)
```
Fusion Probability (q): 0.9
Entanglement Probability (E_p): 0.6
Combined Success Rate: 54% (0.9 × 0.6) ✅
Network Nodes: 100
Avg Degree: 6 (Waxman topology)
S-D Pairs: 10
Total Timeslots: 5000
```

---

## Documentation Hierarchy

### Quick References (Start here - 5 min read)
- `docs/testbeds/Paper2_Quick_Reference.md`
- `docs/testbeds/Paper7_Quick_Reference.md`
- `docs/testbeds/Paper12_Quick_Reference.md`

### Comprehensive Guides (10-15 min read)
- Paper 2: `docs/testbeds/Paper2_Integration_Report.md`
- Paper 7: `docs/testbeds/Paper7_Summary.md`
- Paper 12: `docs/testbeds/PAPER12_TESTS_README.md` + `docs/testbeds/PAPER12_TESTING_SUMMARY.md`

### Implementation Details (Reference)
- Paper 2: Individual MATLAB files
- Paper 7: `main.py`, `protocols.py`, `components.py`
- Paper 12: `run_paper12_sanity_tests.py` source code

### Testing Procedures
- Paper 2: `docs/testbeds/Paper2_Test_Commands.md`
- Paper 7: `docs/testbeds/Paper7_Validation.md`
- Paper 12: `docs/testbeds/Paper12_Testing_Guide.md` + automated unit tests

---

## Framework Integration Status

### Paper 2 ✅
- [x] Codebase integrated
- [x] Documentation organized
- [x] Integration verified
- [x] Quick reference created
- [ ] Python translation (future)
- [ ] Unit tests (future)

### Paper 7 ✅
- [x] Codebase integrated
- [x] Documentation organized
- [x] Python implementation available
- [x] Unit test framework created
- [x] Validation procedures documented
- [x] Quick reference created

### Paper 12 ✅
- [x] Codebase integrated
- [x] Comprehensive testing framework
- [x] 6 unit tests (all passing)
- [x] Full documentation suite
- [x] Parameters validated
- [x] Quick reference created
- [x] Allocator execution documented
- [x] Baseline parameters clarified

---

## Key Resources by Need

### "I want to understand what each paper does"
→ Read Master Documents:
- `docs/testbeds/Paper2_Quick_Reference.md`
- `docs/testbeds/Paper7_Quick_Reference.md`
- `docs/testbeds/Paper12_Quick_Reference.md`

### "I want to run tests quickly"
→ Paper 12 recommended:
```bash
cd Dynamic_Routing_Eval_Framework/
python run_paper12_sanity_tests.py
```

### "I want to compare testing strategies"
→ Read:
- `docs/testbeds/Paper7_vs_Paper12_Testing.md`

### "I need to understand parameters"
→ Check:
- Paper 2: `docs/testbeds/Paper2_Integration_Report.md`
- Paper 7: `docs/testbeds/Paper7_Summary.md`
- Paper 12: `docs/paper12/PAPER12_PARAMETERS_VALIDATION.md`

### "I want complete implementation details"
→ Review:
- Paper 2: See original source in `../../../Testbeds/Paper2-*/`
- Paper 7: See original source in `../../../Testbeds/Paper7-*/`
- Paper 12: `Dynamic_Routing_Eval_Framework/run_paper12_sanity_tests.py`

---

## Quick Command Reference

### Run All Paper 12 Tests
```bash
cd Dynamic_Routing_Eval_Framework/
python run_paper12_sanity_tests.py
```

### Run All Paper 7 Tests
```bash
cd Dynamic_Routing_Eval_Framework/
python run_paper7_sanity_tests.py
```

### View Paper 12 Test Results
```bash
cat Dynamic_Routing_Eval_Framework/results/paper12_sanity_tests.json | python -m json.tool
```

### Read Any Quick Reference
```bash
cat docs/testbeds/Paper2_Quick_Reference.md
cat docs/testbeds/Paper7_Quick_Reference.md
cat docs/testbeds/Paper12_Quick_Reference.md
```

---

## Project Structure Summary

```
hybrid_variable_framework/
│
├── docs/
│   ├── testbeds/
│   │   ├── Paper2_Quick_Reference.md      ← Paper 2 Quick Ref
│   │   ├── Paper2_Integration_Report.md
│   │   ├── Paper2_Test_Commands.md
│   │   ├── Paper7_Quick_Reference.md      ← Paper 7 Quick Ref
│   │   ├── Paper7_Summary.md
│   │   ├── Paper7_Validation.md
│   │   ├── Paper12_Quick_Reference.md     ← Paper 12 Quick Ref
│   │   ├── Paper12_Testing_Guide.md
│   │   ├── PAPER12_TESTS_README.md
│   │   └── Paper7_vs_Paper12_Testing.md
│   │
│   ├── paper12/
│   │   ├── PAPER12_ALLOCATOR_EXECUTION.md
│   │   ├── PAPER12_PARAMETERS_VALIDATION.md
│   │   ├── PAPER12_DOCUMENTATION_UPDATE_COMPLETE.md
│   │   └── PAPER12_UPDATES_CHECKLIST.md
│   │
│   └── assessments/
│       ├── ASSESSMENT_CORRECTION_SUMMARY.md
│       └── BASELINE_ASSESSMENT_QUICK_REF.md
│
└── Dynamic_Routing_Eval_Framework/
    ├── run_paper12_sanity_tests.py
    ├── run_paper7_sanity_tests.py
    └── results/
        ├── paper12_sanity_tests.json
        └── paper7_sanity_tests.json

Original testbed sources:
├── ../../../Testbeds/Paper2-Quantum-Network-MultiArmedBandits-main/
└── ../../../Testbeds/Paper7-lizhuohua-quantum-bgp-online-path-selection-aeb35c0/
```

---

## Next Steps

1. **Choose a testbed** based on your needs
2. **Read the QUICK_REFERENCE.md** in that testbed (5 min)
3. **Review associated documentation** for details (10-15 min)
4. **Run unit tests** if applicable (30 sec - 2 min)
5. **Check results** in results/ folder

---

## Support & References

### Paper Sources
- **Paper 2**: See original source in `../../../Testbeds/Paper2-*/`
- **Paper 7**: See original source in `../../../Testbeds/Paper7-*/`
- **Paper 12**: Referenced in Paper 12 documentation

### Key Documentation Files
- All quick reference files in `docs/testbeds/`
- Integration reports and testing guides in `docs/testbeds/`
- Additional Paper 12 docs in `docs/paper12/`

### Framework Documentation
- `README.md` (repository root)
- `REPOSITORY_STRUCTURE.md` (complete structure guide)
- `docs/INDEX.md` (master documentation index)
- `docs/TESTBEDS_OVERVIEW.md` (testbed comparison)

---

**Status**: ✅ **ALL TESTBEDS ORGANIZED AND DOCUMENTED**

Last organized: January 30, 2026
