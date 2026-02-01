# Paper 7 - Quick Reference

**Paper**: Liu et al. 2024 - QBGP (Quantum BGP)  
**Testbed Location**: `Testbeds/Paper7-lizhuohua-quantum-bgp-online-path-selection-aeb35c0/`  
**Status**: ✅ Fully Integrated

---

## Overview

Paper 7 implements QBGP - a BGP-inspired quantum routing protocol with online path selection. Python implementation with delay-aware routing and quantum fidelity modeling.

---

## Key Parameters

```
Network Nodes: 100 (standard), 50-400 (range)
Average Degree: 6 (Waxman topology)
Min Fidelity: 0.85
QoS Threshold: 0.80
Source-Destination Pairs: 4
```

---

## Core Implementation Files

| File | Purpose |
|------|---------|
| `main.py` | QBGP protocol main implementation |
| `components.py` | Protocol components |
| `protocols.py` | Protocol definitions |
| `event_generators.py` | Simulation events |
| `packets.py` | Quantum packet structures |

---

## Testing & Validation

- **Type**: Automated unit tests
- **Test Count**: 5+ unit tests
- **Status**: ✅ Automated and validated
- **Test Command**: `python run_paper7_sanity_tests.py`
- **Guide**: See [Paper7_Validation.md](Paper7_Validation.md)

---

## Features

✅ Online path selection  
✅ Delay-aware routing  
✅ Fidelity-based optimization  
✅ Scalable to 400+ nodes  
✅ Comprehensive testing framework

---

## Next Steps

1. Review [Paper7_Summary.md](Paper7_Summary.md) for overview
2. Check [Paper7_Validation.md](Paper7_Validation.md) for testing
3. Reference testbed: `Testbeds/Paper7-...`
4. Run unit tests: `python run_paper7_sanity_tests.py`

---

**See Also**: [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md)
