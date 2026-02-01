# Quantum Network Testbeds - Overview

**Framework**: H-MABs Evaluation Framework  
**Last Updated**: January 30, 2026

---

## Quick Summary

This framework integrates three quantum network routing research papers into a unified multi-testbed evaluation platform:

| Paper | Focus | Type | Status |
|-------|-------|------|--------|
| **Paper 2** (Chaudhary et al. 2023) | MAB-based quantum routing with entanglement swapping | MATLAB | ✅ Production |
| **Paper 7** (Liu et al. 2024) | QBGP - Quantum BGP with online path selection | Python | ✅ Integrated |
| **Paper 12** (Wang et al. 2024) | QuARC - Qubit allocation with fusion gates | Python | ✅ Integrated |

---

## Testbed Documentation

### Paper 2 (Chaudhary et al. 2023)
**Focus**: Multi-Armed Bandits for Quantum Network Routing with Entanglement Swapping

- **Quick Reference**: [Paper2_Quick_Reference.md](testbeds/Paper2_Quick_Reference.md)
- **Integration Report**: [Paper2_Integration_Report.md](testbeds/Paper2_Integration_Report.md)
- **Test Commands**: [Paper2_Test_Commands.md](testbeds/Paper2_Test_Commands.md)
- **Status**: ✅ Production-ready
- **Network Size**: Up to 200 nodes
- **Implementation**: MATLAB
- **Key Parameters**: E_p=0.7, q=0.9

### Paper 7 (Liu et al. 2024)
**Focus**: QBGP - Quantum BGP with Online Path Selection

- **Quick Reference**: [Paper7_Quick_Reference.md](testbeds/Paper7_Quick_Reference.md)
- **Validation Guide**: [Paper7_Validation.md](testbeds/Paper7_Validation.md)
- **Status Summary**: [Paper7_Summary.md](testbeds/Paper7_Summary.md)
- **Status**: ✅ Fully Integrated
- **Network Size**: 50-400 nodes
- **Implementation**: Python
- **Key Features**: Delay-aware routing, fidelity-based learning

### Paper 12 (Wang et al. 2024)
**Focus**: QuARC - Qubit Allocation with Fusion Gates

- **Quick Reference**: [Paper12_Quick_Reference.md](testbeds/Paper12_Quick_Reference.md)
- **Testing Guide**: [Paper12_Testing_Guide.md](testbeds/Paper12_Testing_Guide.md)
- **Parameters & Validation**: [Paper12_Parameters.md](testbeds/Paper12_Parameters.md)
- **Status**: ✅ Fully Integrated with comprehensive testing
- **Network Size**: 100 nodes (baseline)
- **Implementation**: Python
- **Key Parameters**: fusion=0.9, entanglement=0.6 (54% baseline success)
- **Unit Tests**: 6 tests, all passing

---

## Comparison Matrix

### Algorithm & Approach
| Aspect | Paper 2 | Paper 7 | Paper 12 |
|--------|---------|---------|----------|
| **Algorithm** | UCB (Multi-Armed Bandits) | BGP-inspired Protocol | Qubit Allocation |
| **Learning** | Path scoring via rewards | Online path selection | MAB for arm selection |
| **Quantum Focus** | Entanglement swapping | Delay-aware routing | Fusion gate optimization |

### Implementation Details
| Aspect | Paper 2 | Paper 7 | Paper 12 |
|--------|---------|---------|----------|
| **Language** | MATLAB | Python | Python |
| **Test Framework** | Manual tests | Unit tests | Unit tests (6 tests) |
| **Network Sizes** | Up to 200 nodes | 50-400 nodes | 100 nodes (baseline) |
| **Testing Status** | ✅ Documented | ✅ Automated | ✅ Automated |

### Key Parameters
| Parameter | Paper 2 | Paper 7 | Paper 12 |
|-----------|---------|---------|----------|
| **Nodes** | 20 (scalable) | 100 | 100 |
| **Avg Degree** | 4 | 6 | 6 |
| **Success Rate** | E_p: 0.7, q: 0.9 | Fidelity: ≥0.85 | Fusion: 54% (0.9×0.6) |
| **S-D Pairs** | Variable | 4 | 10 |

---

## Testing & Validation

### Paper 2
- **Status**: Manual testing documented
- **Integration Status**: ✅ Production
- **Test Guide**: See [Paper2_Test_Commands.md](testbeds/Paper2_Test_Commands.md)

### Paper 7
- **Status**: Automated unit testing
- **Integration Status**: ✅ Complete
- **Test Framework**: 5+ unit tests
- **Validation Guide**: See [Paper7_Validation.md](testbeds/Paper7_Validation.md)

### Paper 12
- **Status**: Automated unit testing with comprehensive coverage
- **Integration Status**: ✅ Complete
- **Test Framework**: 6 unit tests (all passing)
- **Test Command**: `python run_paper12_sanity_tests.py`
- **Testing Guide**: See [Paper12_Testing_Guide.md](testbeds/Paper12_Testing_Guide.md)

---

## Quick Start by Use Case

### "I want to understand all available testbeds"
→ Read this document + individual Paper *_Quick_Reference.md files

### "I want to run Paper 2 experiments"
→ See [Paper2_Integration_Report.md](testbeds/Paper2_Integration_Report.md)

### "I want to run Paper 7 tests"
→ See [Paper7_Validation.md](testbeds/Paper7_Validation.md)

### "I want to run Paper 12 tests"
→ See [Paper12_Testing_Guide.md](testbeds/Paper12_Testing_Guide.md)

### "I want to compare testbeds"
→ See comparison matrix above

### "I want full implementation details"
→ Read the Integration/Testing guides for each paper

---

## File Organization

```
docs/
├── TESTBEDS_OVERVIEW.md              ← You are here
└── testbeds/
    ├── Paper2_Quick_Reference.md
    ├── Paper2_Integration_Report.md
    ├── Paper2_Test_Commands.md
    ├── Paper7_Quick_Reference.md
    ├── Paper7_Validation.md
    ├── Paper7_Summary.md
    ├── Paper12_Quick_Reference.md
    ├── Paper12_Testing_Guide.md
    └── Paper12_Parameters.md
```

---

## Integration Status

### ✅ Complete
- Paper 2: Documented and integrated
- Paper 7: Fully integrated with testing
- Paper 12: Fully integrated with comprehensive testing (6 unit tests)

### 🔄 In Progress
- Cross-testbed comparison analysis
- Unified results reporting

### 📋 Planned
- Paper 5 integration
- Additional scaling studies
- Advanced visualization dashboards

---

## Key Resources

- **Master Quick Reference**: [TESTBEDS_MASTER_QUICK_REFERENCE.md](testbeds/TESTBEDS_MASTER_QUICK_REFERENCE.md)
- **Framework README**: [README.md](../README.md)
- **Setup Guides**: [setup/](setup/)
- **Documentation Index**: [INDEX.md](INDEX.md)
- **Validated Results**: [Validated_Logs/](../Validated_Logs/)

---

**Next Step**: Choose a testbed from above and read its Quick Reference document (5 min) to get started!
