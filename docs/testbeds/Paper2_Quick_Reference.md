# Paper 2 - Quick Reference

**Paper**: Chaudhary et al. 2023 - Quantum Network Multi-Armed Bandits  
**Testbed Location**: `Testbeds/Paper2-Quantum-Network-MultiArmedBandits-main/`  
**Status**: ✅ Production-Ready

---

## Overview

Paper 2 implements multi-armed bandits for quantum network routing with entanglement swapping. MATLAB-based implementation focusing on fidelity calculations and QoS-aware path selection.

---

## Key Parameters

```
Entanglement Probability (E_p): 0.7
Quantum Gate Fidelity (q): 0.9
Network Nodes: 20 (scalable to 200)
Average Degree: 4
Topology: Standard graph model
```

---

## Core Implementation Files

| File | Purpose |
|------|---------|
| `MAB_UCB_QNetwork_Routing.m` | Main UCB algorithm |
| `EntanglementSwap_Noises.m` | Entanglement swapping model |
| `Fidelity_FeasiblePaths.m` | Fidelity calculation |
| `dijkstra_QNetwork.m` | Path finding |
| `kShortestPath_QNetwork.m` | K-shortest paths |

**Full Details**: See [Paper2_Integration_Report.md](Paper2_Integration_Report.md)

---

## Testing

- **Type**: Manual testing
- **Status**: ✅ Documented
- **Commands**: See [Paper2_Test_Commands.md](Paper2_Test_Commands.md)

---

## Next Steps

1. Review [Paper2_Integration_Report.md](Paper2_Integration_Report.md)
2. Check [Paper2_Test_Commands.md](Paper2_Test_Commands.md) for test procedures
3. Reference testbed location: `Testbeds/Paper2-...`

---

**See Also**: [TESTBEDS_OVERVIEW.md](TESTBEDS_OVERVIEW.md)
