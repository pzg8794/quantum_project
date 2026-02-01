# Quantum Network Testbeds Hub

**Integration Status & Roadmap for All Testbeds**

---

## 🎯 Framework Inspiration & Evolution

### Our Foundation: The EXPNeuralUCB Paper

This framework builds upon **"Quantum Entanglement Path Selection and Qubit Allocation via Adversarial Group Neural Bandits"** by Huang et al. (2024, arXiv:2411.00316). The original work introduced:

- **EXPNeuralUCB algorithm**: Combines EXP3 (for adversarial group selection) with NeuralUCB (for non-linear arm selection within groups)
- **Problem formulation**: Online path selection and qubit allocation in QDNs without prior knowledge of success rates
- **Adversarial framework**: Addresses both stochastic uncertainty (network decoherence) and adversarial uncertainty (active attackers)
- **Theoretical guarantee**: O(T³⁄₄ log T) regret bound under semi-stochastic, semi-adversarial conditions

**Key Innovation**: EXPNeuralUCB treats quantum paths as *groups* and qubit allocations as *arm selections*, enabling joint optimization of path routing and resource allocation under adversarial conditions.

### Our Extensions: Paper2, Paper12, Paper5, Paper7

We have expanded this foundation into a **sophisticated multi-testbed framework** that:

1. **Paper2 (Production)** - **Stochastic Quantum Network Testbed**
   - Evolved the original EXPNeuralUCB formulation into a production-ready evaluation framework
   - Introduced **contextual variants**: CPursuitNeuralUCB (pursuit-based), iCPursuitNeuralUCB (with ARIMA predictive intelligence)
   - Added **multi-scenario evaluation**: Baseline → Stochastic → Markov → Adaptive → OnlineAdaptive threat escalation
   - Developed **qubit allocators**: Fixed, Thompson Sampling, DynamicUCB, Random (with impact analysis)
   - Created **comprehensive benchmarking suite**: 8 validation tests, cross-algorithm comparisons, deployment guidelines

2. **Paper12 (In Progress)** - **Event-Driven Quantum Network Testbed**
   - Extends framework to temporal dynamics and event-triggered behaviors
   - Introduces time-correlation in failures (moving beyond i.i.d. stochastic model)
   - Adds event generators, temporal context features, adaptive scheduling

3. **Paper5 & Paper7 (Planned)** - **Scaling & Domain Integration**
   - Paper5: Long-distance quantum routing with distance-dependent fidelity
   - Paper7: Multi-domain ASs with privacy and inter-domain trust constraints

**Critical Distinction**: While the original EXPNeuralUCB paper focused on a single algorithm and single network topology, our framework provides:
- Multiple evaluator backends (multi-run, batch, step-wise)
- Pluggable testbed physics (stochastic, event-driven, distance-aware, domain-aware)
- Comprehensive algorithm suite (original + contextual + predictive variants)
- Production-grade infrastructure (backup managers, logging, visualization, validation tests)

---

## 🎯 Testbed Overview Matrix

| Testbed | Status | Foundation | Network Type | Nodes | Paths | Qubits | Attack Models | Integration Doc | Typical Runtime |
|---------|--------|-----------|--------------|-------|-------|--------|---------------|-----------------|-----------------|
| **EXPNeuralUCB (Original)** | 📚 Reference | Huang et al. 2024 | Stochastic (4-node) | 4 | 4 | 35 | 5 | [arXiv:2411.00316](https://arxiv.org/abs/2411.00316) | Academic |
| **Paper2** | ✅ PROD | EXPNeuralUCB expanded | Stochastic | 4 | 4 | 35 | 5 | [Integration Report](testbeds/Paper2_Integration_Report.md) | 2-3 hrs (full) |
| **Paper12** | 🔄 IN PROGRESS | Paper2 evolved | Event-driven | 5 | 8+ | 50+ | 3 | [Integration Report](testbeds/Paper12_Integration_Report.md) | 1-2 hrs |
| **Paper5** | 📋 PLANNED | Paper2 extended | Long-distance | 6+ | 10+ | 100+ | 4 | Coming soon | 3-4 hrs |
| **Paper7** | 📋 PLANNED | Paper5 extended | Multi-domain | 8+ | 12+ | 150+ | 5 | Coming soon | 4-5 hrs |

---

## 📚 Original Research Foundation: EXPNeuralUCB (2024)

**Reference**: Yin Huang, Lei Wang, Jie Xu. "Quantum Entanglement Path Selection and Qubit Allocation via Adversarial Group Neural Bandits." arXiv:2411.00316, November 2024.

### The Original Problem (Huang et al.)

**Challenge**: In Quantum Data Networks (QDNs), establishing long-distance entanglement requires:
- **Optimal path selection** (which route through quantum repeaters?)
- **Qubit allocation** (how many qubits per node on the chosen path?)
- **Unknown success probabilities** (no prior knowledge of link fidelities)
- **Active adversaries** (attackers disrupting quantum channels)

**Prior Limitations**:
- Existing routing assumes known link probabilities → unrealistic
- Prior work ignores adversarial scenarios → incomplete threat model
- Classical bandits can't handle non-linear qubit allocation rewards

### The EXPNeuralUCB Solution

**Algorithm Design**:
```
Paths → Groups (EXP3 selection)
           ↓
         [Chosen Path]
           ↓
Qubit Allocations → Arms (NeuralUCB selection within group)
           ↓
         [Optimal Allocation]
           ↓
Success or Failure (Bernoulli reward)
```

**Key Innovation**: Hybrid bandit combining:
- **EXP3 for group selection** (handles adversarial attacks on paths)
- **NeuralUCB for arm selection** (learns non-linear qubit allocation rewards)
- **Theoretical guarantee**: O(T³⁄₄ log T) regret (sublinear under semi-stochastic, semi-adversarial)

### Original Results (Huang et al.)

| Metric | EXPNeuralUCB | GNeuralUCB | EXPUCB | Oracle |
|--------|--------------|-----------|--------|--------|
| **Regret** | Sublinear | Higher | Higher | 0 |
| **Worst Case** | Balanced | Good in stochastic | Good in adversarial | N/A |
| **Complexity** | O(T¾) | O(T log T) | O(√T) | N/A |

**Why This Matters**: EXPNeuralUCB is the **first algorithm** to handle joint stochastic + adversarial bandits with non-linear rewards in quantum networks.

---

## 📊 Paper2: Stochastic Quantum Network (PRODUCTION)

**Status**: ✅ **READY FOR PRODUCTION** (January 2026)

**Relationship to Original**: Paper2 takes the EXPNeuralUCB algorithm and expands it into a **production-grade evaluation framework** with:

### Quick Facts

- **Base Algorithm**: EXPNeuralUCB (Huang et al. 2024)
- **Extended With**: CPursuitNeuralUCB (context-aware), iCPursuitNeuralUCB (predictive intelligence)
- **Network**: 4-node, 4-path quantum network (same topology as original paper)
  - **Paths**: P1, P2 (2-hop) + P3, P4 (3-hop)
  - **Total Capacity**: 35 qubits (fixed)
  - **Physics**: Per-hop fidelity 0.95, multiplicative cascading
- **Attack Models**: Baseline (0%), Stochastic (6.25%), Markov (25%), Adaptive (25%), OnlineAdaptive (25%)
- **Research Questions**: 
  - RQ1: Stochastic decoherence impact (Table V)
  - RQ2: Threat escalation robustness (Table VI)
  - RQ3: Deployment optimization (Tables VII-IX)

### Key Results (Expected)

| Algorithm | Stochastic | Avg (All Threats) | Worst-Case Floor |
|-----------|------------|--------------------|------------------|
| **CPursuit** | 89.9% | 88.1% | 77.4% |
| **iCEpsilonGreedy** | 88.3% | 86.9% | 81.0% |
| **GNeuralUCB** | 85.9% | — | — |
| **EXPNeuralUCB** | 83.1% | 82.4% | 18.0% ⚠️ |
| **EXPUCB** | 77.6% | 76.3% | 68.8% |

**Best Static Default**: iCPursuitNeuralUCB + Fixed allocator @ **95.5% global avg, 88.5% worst-case floor**

### What's New in Paper2 vs. Original EXPNeuralUCB

| Aspect | Original (Huang et al.) | Paper2 Framework |
|--------|--------|----------|
| **Algorithm** | Single EXPNeuralUCB | EXPNeuralUCB + CPursuit + iCPursuit variants |
| **Scenarios** | 2 (oblivious, adaptive) | 5 (baseline, stochastic, Markov, adaptive, online-adaptive) |
| **Allocators** | Fixed (8,10,8,9) only | Fixed, Thompson, DynamicUCB, Random |
| **Threat Escalation** | Individual algorithms | RQ2: Full escalation matrix |
| **Predictive Intelligence** | No | Yes (iCPursuitNeuralUCB with ARIMA) |
| **Deployment Guidance** | Theoretical | RQ3: Specific rules per scenario |
| **Validation Tests** | Simulation only | 8-test suite with exact expected values |
| **Infrastructure** | Standalone | Full backup, logging, visualization pipeline |

### Quick Start (Paper2)

```python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

# Load Paper2 configuration
config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')
config.setenvironment(framesno=6000, attack_type='stochastic', attack_intensity=0.0625)

# Run RQ1: Multi-algorithm comparison
evaluator = MultiRunEvaluator(config=config, runs=3)
results = evaluator.test_stochastic_environment(
    runs=3,
    models=['CPursuit', 'iCEpsilonGreedy', 'EXPNeuralUCB'],
    scenarios=['stochastic']
)
```

**Full Documentation**:
- 📖 [Paper2 Integration Report](testbeds/Paper2_Integration_Report.md) — Complete details, physics model, RQ configurations
- 📋 [Paper2 Quick Reference](testbeds/Paper2_Quick_Reference.md) — Parameter lookup, key metrics
- 🧪 [Paper2 Test Commands](testbeds/Paper2_Test_Commands.md) — 8-test validation suite

**Validation Tests**: Run `bash scripts/paper2_test_suite.sh` (2-3 hours, validates all RQs)

---

## 🔄 Paper12: Event-Driven Quantum Network (IN PROGRESS)

**Status**: 🔄 **INTEGRATION IN PROGRESS** (Target: February 2026)

**Relationship to Paper2**: Paper12 extends the Paper2 framework by:
- Moving beyond i.i.d. stochastic failures to **time-correlated events**
- Adding **temporal context** (event history, predictive signals)
- Introducing **dynamic scheduling** (decisions based on event patterns)

### Quick Facts

- **Foundation**: Paper2 framework + event generation layer
- **Network**: 5-node, dynamic topology with time-varying capacity
- **Attack Models**: 3 threat levels (Low, Medium, High)
- **Key Feature**: Temporal patterns, event prediction, adaptive scheduling
- **Horizon**: 4K-8K frames with event timestamps

### Current Integration Phase

- ✅ Core environment classes defined
- ✅ Event generator implemented
- 🔄 Algorithm adaptations (ETA: mid-Feb)
- 🔄 Validation tests (ETA: late-Feb)
- 📋 Documentation (TBD)

### Expected Quick Start (When Ready)

```python
config = ExperimentConfiguration()
config.load_testbed_config('PAPER12')
config.setenvironment(framesno=8000, event_type='poisson', intensity=0.5)

evaluator = MultiRunEvaluator(config=config, runs=3)
results = evaluator.test_event_driven_environment(
    models=['EXPNeuralUCB', 'TemporalNeuralUCB'],
    scenarios=['low_frequency', 'high_frequency']
)
```

**Documentation**:
- 📖 [Paper12 Integration Report](testbeds/Paper12_Integration_Report.md) — Coming soon (late January)
- 📋 Paper12 Quick Reference — Coming soon
- 🧪 Paper12 Test Commands — Coming soon

**Team**: Contact repo maintainer for early access to Paper12 code.

---

## 📋 Paper5: Long-Distance Quantum Routing (PLANNED)

**Status**: 📋 **PLANNED** (Target: March 2026)

**Relationship to Paper12**: Paper5 extends by:
- Moving from event-driven dynamics to **distance-dependent physics**
- Adding **heterogeneous links** (variable fidelity based on distance)
- Introducing **link-level failure recovery**

### Scope

- **Network**: 6+ nodes, long-distance links with higher decoherence
- **New Challenge**: Link-level failure recovery, end-to-end path optimization
- **Integration Approach**: Extend Paper2 physics model with distance-dependent fidelity

### Placeholder Quick Start

```python
# Coming March 2026
config = ExperimentConfiguration()
config.load_testbed_config('PAPER5')
```

---

## 📋 Paper7: Multi-Domain Routing (PLANNED)

**Status**: 📋 **PLANNED** (Target: April 2026)

**Relationship to Paper5**: Paper7 extends by:
- Moving from single-domain to **multi-AS (Autonomous System) networks**
- Adding **privacy and trust constraints**
- Introducing **domain-level policies**

### Scope

- **Network**: 8+ nodes across multiple domains (inter-AS routing)
- **New Challenge**: Privacy constraints, inter-domain trust, scaling
- **Integration Approach**: Add domain-layer abstractions to environment

### Placeholder Quick Start

```python
# Coming April 2026
config = ExperimentConfiguration()
config.load_testbed_config('PAPER7')
```

---

## 🔍 Testbed Comparison

### Physics Models

| Aspect | EXPNeuralUCB (Original) | Paper2 | Paper12 | Paper5 | Paper7 |
|--------|---------|--------|---------|--------|--------|
| **Fidelity Model** | Multiplicative | Multiplicative | Event-triggered decay | Distance-dependent | Domain-aware |
| **Failure Mode** | Stochastic i.i.d. | Stochastic i.i.d. | Time-correlated events | Link-dependent | Cross-domain |
| **Predictability** | Low (Bernoulli) | Low (Bernoulli) | Medium (Markov events) | Low (link variance) | Medium (domain patterns) |

### Execution Environment

| Aspect | EXPNeuralUCB | Paper2 | Paper12 | Paper5 | Paper7 |
|--------|--------|--------|--------|--------|--------|
| **Node Count** | 4 | 4 | 5 | 6+ | 8+ |
| **Path Count** | 4 | 4 | 8+ | 10+ | 12+ |
| **Typical Horizon** | Academic | 6K | 8K | 8K | 10K |
| **Event Density** | N/A | None | High | Low | Medium |
| **Colab Feasible?** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Maybe | ❌ Recommend GCP |

### Algorithm Relevance

| Algorithm | EXPNeuralUCB | Paper2 | Paper12 | Paper5 | Paper7 |
|-----------|--------|--------|--------|--------|--------|
| **EXPNeuralUCB** | ✅ Primary | ✅ Baseline | ✅ Good | ⚠️ TBD | ⚠️ TBD |
| **CPursuit** | ⚠️ N/A | ✅ Best | ✅ Good | ⚠️ TBD | ⚠️ TBD |
| **iCPursuit** | ⚠️ N/A | ✅ SOTA | ✅ Better | ✅ Likely | ✅ Likely |
| **TemporalNeuralUCB** | ⚠️ N/A | ⚠️ N/A | ✅ Best | ⚠️ Maybe | ✅ Good |
| **PrivacyNeuralUCB** | ⚠️ N/A | ⚠️ N/A | ⚠️ N/A | ⚠️ N/A | ✅ Key |

---

## 📈 Integration Timeline

```
January 2026        February 2026        March 2026        April 2026
│                   │                    │                 │
├─ Paper2 PROD ✅   ├─ Paper12 IN PROG   ├─ Paper5 PLAN    ├─ Paper7 PLAN
│  (Complete)       │  (On track)        │  (Start)        │  (Start)
│  Base: Huang et   │  Base: Paper2      │  Base: Paper12  │  Base: Paper5
│  al. 2024         │  Extended          │  Extended       │  Extended
└─────────────────┘└────────────────────┘──────────────────┘


Current: Paper2 production-ready (evolved from Huang et al. 2024)
         Paper12 code 80% complete (event-driven layer)
Next Milestone: Paper12 full integration (end of Feb)
Stretch Goal: Paper5 basic integration by end of March
```

---

## 🎯 How to Choose Your Testbed

**Choose Paper2 if you want to**:
- ✅ Get started immediately with production-ready code
- ✅ Study the original EXPNeuralUCB algorithm and variants
- ✅ Understand stochastic noise and robust algorithms
- ✅ Understand allocator-algorithm co-design
- ✅ Run quick experiments on Colab
- ✅ Compare classical vs. neural vs. contextual bandit approaches
- ✅ **Reproduce/extend the Huang et al. 2024 results in Python**

**Choose Paper12 if you want to** (coming Feb):
- 🔄 Explore event-driven networks and temporal dynamics
- 🔄 Study temporal pattern prediction (ARIMA integration)
- 🔄 Understand adaptive scheduling under dynamics
- 🔄 Compare predictive algorithms (TemporalNeuralUCB vs. iCPursuit)

**Choose Paper5 if you want to** (coming March):
- 📋 Study long-distance quantum routing
- 📋 Understand link-level failures and recovery
- 📋 Scale to larger networks
- 📋 Compare end-to-end optimization strategies

**Choose Paper7 if you want to** (coming April):
- 📋 Study multi-domain routing
- 📋 Explore privacy-aware algorithms
- 📋 Understand inter-domain trust and coordination
- 📋 Scale to very large networks (8+ nodes)

---

## 🚀 Getting Started

### For Paper2 (Immediate)

1. Read [`Paper2_Integration_Report.md`](testbeds/Paper2_Integration_Report.md) (10 min)
   - Understand RQ1, RQ2, RQ3 structure
   - See how EXPNeuralUCB is extended with CPursuit + iCPursuit
2. Read your [setup guide](setup_files/SETUP_COLAB.md) (5 min)
3. Run `bash scripts/paper2_test_suite.sh` (2-3 hrs)
4. Access results in `quantum_data_lake/paper2/`

### For Paper12 (End of February)

1. Watch this space for `Paper12_Integration_Report.md` release
2. Setup will be identical to Paper2 (Colab / Local / GCP)
3. Validation tests will follow same structure

### For Paper5 & Paper7 (Future)

1. Integrations will be announced here
2. Each will have dedicated integration report
3. Setup and validation will follow Paper2 pattern

---

## 📚 Documentation Index by Testbed

### EXPNeuralUCB (Original Foundation)
- [arXiv:2411.00316](https://arxiv.org/abs/2411.00316) — Original paper by Huang et al.
- Algorithm: Adversarial group neural bandits for path selection + qubit allocation
- Baseline for all our extensions

### Paper2 (Stochastic)
- [`Paper2_Integration_Report.md`](testbeds/Paper2_Integration_Report.md) — Complete integration details
- [`Paper2_Quick_Reference.md`](testbeds/Paper2_Quick_Reference.md) — Parameter lookup card
- [`Paper2_Test_Commands.md`](testbeds/Paper2_Test_Commands.md) — 8-test validation suite

### Paper12 (Event-Driven) — Coming Feb
- `Paper12_Integration_Report.md` — TBD
- `Paper12_Quick_Reference.md` — TBD
- `Paper12_Test_Commands.md` — TBD

### General Setup
- [`setup_files/SETUP_COLAB.md`](setup_files/SETUP_COLAB.md) — Colab instructions
- [`setup_files/SETUP_LOCAL.md`](setup_files/SETUP_LOCAL.md) — Local + GCP setup
- [`setup_files/TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md) — Common issues

---

## 🔗 Architecture Overview

```
Foundation Paper: Huang et al. 2024 (EXPNeuralUCB)
                         ↓
         Testbed-Agnostic Framework
┌─────────────────────────────────────────────────────┐
│  Algorithms (EXP3, NeuralUCB, CMAB, iCMAB, etc.)   │
│  Runners (Batch, Step-wise, Multi-run)             │
│  Evaluators (Multi-Run, Scenario-based)            │
│  Visualizers (Testbed-agnostic plotting)           │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴───────┬─────────────┬──────────────┐
       ▼               ▼             ▼              ▼
   ┌────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
   │Paper2  │   │Paper12   │   │Paper5   │   │Paper7    │
   │Testbed │   │Testbed   │   │Testbed  │   │Testbed   │
   │(PROD)  │   │(IN PROG) │   │(PLAN)   │   │(PLAN)    │
   │        │   │          │   │         │   │          │
   │Stocha- │   │Event-    │   │Long-    │   │Multi-    │
   │stic    │   │driven    │   │distance │   │domain    │
   └────────┘   └──────────┘   └─────────┘   └──────────┘
```

**Key Principle**: Algorithms don't know which testbed they're running on. Environment classes handle testbed-specific physics, attacks, and allocation. Runners and evaluators work with any testbed.

---

## ✅ Validation Status

| Testbed | Physics | Environment | Attacks | Algorithms | Visualizer | Tests |
|---------|---------|-------------|---------|-----------|-----------|-------|
| **Paper2** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 8/8 |
| **Paper12** | ✅ | 🔄 | 🔄 | 🔄 | ✅ | 🔄 0/6 |
| **Paper5** | 📋 | 📋 | 📋 | 📋 | ✅ | 📋 0/6 |
| **Paper7** | 📋 | 📋 | 📋 | 📋 | ✅ | 📋 0/6 |

---

## 🎓 Recommended Learning Path

1. **Start Here** (15 min):
   - Read this page (you are here)
   - Understand testbed scope, evolution from EXPNeuralUCB, and comparison
   - See how original Huang et al. 2024 work was extended

2. **Pick Your Testbed** (5 min):
   - Paper2 recommended if starting (production-ready, directly extends Huang et al.)
   - Paper12 if interested in temporal patterns (coming Feb)

3. **Read Integration Report** (15 min):
   - Paper2: [`Paper2_Integration_Report.md`](testbeds/Paper2_Integration_Report.md)
   - Understand research questions & expected results
   - See how CPursuit and iCPursuit extend EXPNeuralUCB

4. **Setup Your Environment** (15-30 min):
   - Follow [`SETUP_COLAB.md`](setup_files/SETUP_COLAB.md) or [`SETUP_LOCAL.md`](setup_files/SETUP_LOCAL.md)
   - Run your first experiment

5. **Run Validation Tests** (2-3 hrs):
   - Execute testbed test suite
   - Verify your setup matches expected results

6. **Explore & Contribute** (ongoing):
   - Modify experiments in integration reports
   - Compare algorithms across testbeds
   - Add new testbeds following Paper2 pattern

---

## 🤝 Contributing a New Testbed

Want to integrate a new quantum network testbed? Follow this pattern:

1. **Create environment classes** (in `daqr/core/`)
   - `YourTestbedQuantumPhysics` (fidelity, decoherence)
   - `YourTestbedQuantumNetwork` (topology, paths)
   - `YourTestbedAttackStrategy` (threat models)
   - `YourTestbedAllocator` (resource allocation)

2. **Add testbed config** (in `daqr/config/experiment_config.py`)
   - `YOURTESTBED_CONFIG` dictionary with parameters

3. **Create validation tests** (in `tests/`)
   - 6-8 tests following Paper2 pattern
   - Test physics, environment, single algorithm, RQs

4. **Write integration report** (in `docs/`)
   - Follow `Paper2_Integration_Report.md` template
   - Document network, physics, research questions

5. **Update TESTBEDS.md** (this file)
   - Add testbed to overview matrix
   - Link to integration report
   - Update timeline

6. **Create quick reference card** (optional but recommended)
   - Parameter lookup table (like `Paper2_Quick_Reference.md`)

---

## 📞 Testbed-Specific Help

| Testbed | Status | Issues | Contact |
|---------|--------|--------|---------|
| **Paper2** | ✅ PROD | Check [`setup_files/TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md) | GitHub Issues |
| **Paper12** | 🔄 IN PROG | Early access only | Team Lead |
| **Paper5** | 📋 PLAN | Not yet available | TBD |
| **Paper7** | 📋 PLAN | Not yet available | TBD |

---

## 🎯 Next Steps

**Immediate Actions**:
- [ ] Read the foundation: [EXPNeuralUCB paper](https://arxiv.org/abs/2411.00316) (optional but recommended)
- [ ] Choose Paper2 or Paper12
- [ ] Read the integration report for your choice
- [ ] Run the setup guide for your environment
- [ ] Execute your first experiment
- [ ] Bookmark this testbeds hub for future reference

**Questions?** → See [`setup_files/TROUBLESHOOTING.md`](setup_files/TROUBLESHOOTING.md) or [README.md](README.md) for links to all guides.

---

**Framework Evolution**:
- 📚 **Foundation**: Huang et al. 2024 — EXPNeuralUCB algorithm
- ✅ **Paper2**: Production-ready expansion — Stochastic + threat escalation + deployment
- 🔄 **Paper12**: In progress — Event-driven extension
- 📋 **Paper5 & 7**: Planned — Scaling and domain integration

**Framework Status**: ✅ Paper2 PRODUCTION READY | 🔄 Paper12 IN PROGRESS | 📋 Paper5 & Paper7 PLANNED

🚀 **Ready to start? Pick your testbed above and follow the quick-start!**
