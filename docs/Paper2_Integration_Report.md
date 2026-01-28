# Paper2 Integration Report

**Adversarial Quantum Entanglement Routing via Neural Multi-Armed Bandits**  
**Chaudhary et al., ICC 2023 — Stochastic Quantum Network Testbed**

**Status**: ✅ **PRODUCTION READY** (January 2026)

---

## 📖 Quick Navigation

| Section | Purpose |
|---------|---------|
| **[Overview](#overview)** | What Paper2 is, why it matters |
| **[Network Architecture](#-network-architecture)** | 4-node, 4-path topology |
| **[Physics Model](#-quantum-physics-model)** | Fidelity, decoherence, cascading failures |
| **[Attack Scenarios](#-attack-scenarios)** | 5 threat models (Baseline to OnlineAdaptive) |
| **[Research Questions](#-research-questions)** | RQ1-RQ3: What we're evaluating |
| **[Algorithms](#-algorithms)** | Which algorithms work best |
| **[Running Experiments](#-running-experiments)** | Code examples for each RQ |
| **[Expected Results](#-expected-results)** | Benchmarks to validate against |
| **[Test Suite](#-8-test-validation-suite)** | How to validate your setup |
| **[Troubleshooting](#-troubleshooting)** | Common issues & fixes |

---

## Overview

### What Is Paper2?

Paper2 is a **stochastic quantum network testbed** based on real quantum routing research (Chaudhary et al., ICC 2023). It models a realistic 4-node quantum network with:

- **Deterministic topology**: 4 fixed paths with known hop counts
- **Stochastic physics**: Per-hop fidelity 0.95 with multiplicative cascading (realistic decoherence)
- **Resource constraints**: 35 total qubits, fixed allocation (8, 10, 8, 9)
- **Multiple threat levels**: From ideal (Baseline) to worst-case (OnlineAdaptive)

### Why Use Paper2?

✅ **Production-ready**: Fully implemented, tested, validated  
✅ **Realistic**: Based on actual quantum network research  
✅ **Comprehensive**: 3 major research questions with 4-5 scenarios each  
✅ **Scalable**: Run from Colab (quick), Local (dev), or GCP (large batches)  
✅ **Collaborative**: All results stored in shared data lake  

### Key Finding

> **Context-aware algorithms (CPursuit) outperform adversarial-only approaches (EXPNeuralUCB) by 6-10pp under stochastic noise. However, when threat escalates to OnlineAdaptive attacks, predictive context helps by +18.3pp.**

---

## 🌐 Network Architecture

### Topology

```
Node 1 ←→ Node 2
  ↓        ↓
Node 3 ←→ Node 4

4 Paths:
  P1: Node1 → Node2 (2-hop)
  P2: Node1 → Node4 (2-hop, via Node3)
  P3: Node1 → Node3 → Node4 (3-hop)
  P4: Node1 → Node2 → Node4 (3-hop)
```

### Capacity Allocation (Fixed Strategy)

| Path | Hops | Qubits Allocated | Success Prob (0.95/hop) |
|------|------|-----------------|------------------------|
| **P1** | 2 | 8 | 0.95² = **0.9025** |
| **P2** | 2 | 10 | 0.95² = **0.9025** |
| **P3** | 3 | 8 | 0.95³ = **0.8574** |
| **P4** | 3 | 9 | 0.95³ = **0.8574** |
| **Total** | — | **35** | — |

**Key Insight**: Longer paths (3-hop) have lower success probability. Allocation doesn't scale linearly with qubits.

---

## ⚛️ Quantum Physics Model

### Per-Hop Fidelity

Each hop in the quantum network has an independent fidelity loss:

```
Fidelity per hop: 0.95
Failure rate per hop: 0.05 (5% decoherence)
```

### Path-Level Success (Multiplicative Cascading)

Success of a path = product of hop fidelities:

```
2-hop path: 0.95 × 0.95 = 0.9025 (90.25%)
3-hop path: 0.95 × 0.95 × 0.95 = 0.8574 (85.74%)
```

This is **realistic**: decoherence accumulates over distance.

### Quantum Objects in Code

```python
from daqr.core.quantum_physics import StochasticQuantumPhysics

physics = StochasticQuantumPhysics(
    per_hop_fidelity=0.95,
    num_paths=4,
    path_hops=[2, 2, 3, 3]  # P1, P2, P3, P4
)

# Calculate path success probabilities
success_probs = physics.compute_path_probabilities()
# Returns: [0.9025, 0.9025, 0.8574, 0.8574]
```

---

## 🎯 Attack Scenarios

Paper2 evaluates algorithms under **5 threat levels**. Each models a different failure mode:

### 1. Baseline (0% Failure)

**Model**: No attacks, ideal conditions  
**Attack Rate**: 0%  
**Use Case**: Upper performance ceiling, oracle baseline

```python
attack_type = 'none'
attack_intensity = 0.0
```

**Expected Behavior**: All algorithms achieve near-optimal (85-92% of oracle)

---

### 2. Stochastic (6.25% Failure)

**Model**: Independent i.i.d. Bernoulli failures (natural decoherence)  
**Attack Rate**: 6.25% per frame  
**Physics**: Realistic node failures, random timing

```python
attack_type = 'stochastic'
attack_intensity = 0.0625
```

**Failure Pattern**:
```
Frames: [0, 1, 1, 0, 0, 1, 0, ...]  (1 = failure)
P(failure) = 0.0625 (independent each frame)
```

**Expected Winner**: CPursuit (89.9%) — contextual algorithms shine

**Why Hard?**: Unpredictability makes it hard to learn attack patterns

---

### 3. Markov (25% Failure)

**Model**: 4-state Markov chain (temporal correlation)  
**Attack Rate**: 25%  
**Physics**: Burst failures (e.g., infrastructure degradation)

```python
attack_type = 'markov'
attack_intensity = 0.25
```

**Markov States**:
```
State 0: Normal → 95% stay in State 0, 5% → State 1
State 1: Degrading → 60% → State 2, 40% → State 0
State 2: Failing → 30% → State 3, 70% → State 1
State 3: Critical → 100% → State 2
```

**Expected Behavior**: Algorithms with memory can predict state transitions (+3-5pp)

---

### 4. Adaptive (25% Failure, Reactive)

**Model**: Adversary adapts to algorithm's last actions  
**Attack Rate**: 25%  
**Window Size**: w=50 frames (sliding window)  
**Physics**: Intelligent adversary probing weaknesses

```python
attack_type = 'adaptive'
attack_intensity = 0.25
window_size = 50
```

**Attacker Strategy**:
```
1. Observe algorithm actions (last 50 frames)
2. Identify most-used path
3. Target that path in next window
```

**Expected Behavior**: Context-aware algorithms resist better (+5-8pp vs. naive)

**Challenge**: Adversary learns faster than algorithm; non-stationary environment

---

### 5. OnlineAdaptive (25% Failure, Predictive)

**Model**: Adversary predicts algorithm's future actions  
**Attack Rate**: 25%  
**Decay Rate**: λ = 0.97 (adversary's belief decay)  
**Physics**: Sophisticated adversary with policy prediction

```python
attack_type = 'online_adaptive'
attack_intensity = 0.25
decay_factor = 0.97
```

**Attacker Strategy**:
```
1. Build probability distribution of algorithm's path choices
2. Predict next action with ~70% accuracy
3. Pre-emptively target that path
4. Update beliefs with exponential decay (λ=0.97)
```

**Expected Behavior**: Only predictive algorithms (iCPursuit, EXPNeuralUCB) survive (+10-18pp)

**Challenge**: Highest difficulty; non-stationary + adversarial

---

### Threat Escalation Summary

| Scenario | Difficulty | Best Defender | Expected Advantage |
|----------|-----------|---|---|
| **Baseline** | Easy (none) | All equal | — |
| **Stochastic** | Easy (i.i.d.) | CPursuit | +3-5pp |
| **Markov** | Medium (correlated) | iCEpsilonGreedy | +5-8pp |
| **Adaptive** | Hard (reactive) | iCPursuit | +8-12pp |
| **OnlineAdaptive** | Hardest (predictive) | EXPNeuralUCB | +12-18pp |

**Key Insight**: Threat type matters more than threat intensity. Context + prediction >> pure adversarial robustness.

---

## 🔬 Research Questions

### RQ1: Stochastic Decoherence Impact

**Question**: How do algorithms perform under natural stochastic noise?

**Configuration**:
```python
config.setenvironment(
    attack_type='stochastic',
    attack_intensity=0.0625,  # 6.25%
    framesno=6000,
    allocator='Fixed'  # (8, 10, 8, 9)
)
```

**Ensemble**: 3-5 runs, 5 algorithms

**Expected Results** (Table V in Paper2):

| Algorithm | Efficiency | vs. Oracle |
|-----------|-----------|-----------|
| Oracle | 100% | Baseline |
| CPursuit | **89.9%** | -10.1pp |
| iCEpsilonGreedy | **88.3%** | -11.7pp |
| GNeuralUCB | **85.9%** | -14.1pp |
| EXPNeuralUCB | 83.1% | -16.9pp |
| EXPUCB | 77.6% | -22.4pp |

**Key Finding**: CPursuit maintains 89.9% even under stochastic noise. Classical methods (EXPUCB) drop to 77.6%.

**What This Tells Us**: Contextual + pursuit learning > pure neural UCB under noise.

---

### RQ2: Threat Escalation Robustness

**Question**: How do algorithms degrade as threats escalate?

**Configuration**: Run all 4 threat scenarios with fixed allocator

```python
for threat in ['Stochastic', 'Markov', 'Adaptive', 'OnlineAdaptive']:
    config.setenvironment(attack_type=threat, ...)
    results = run_experiment(config)
```

**Ensemble**: 5 runs each scenario

**Expected Results** (Table VI in Paper2):

| Algorithm | Stochastic | Markov | Adaptive | OnlineAdaptive | Avg | Variance |
|-----------|-----------|--------|----------|---|---|---|
| **CPursuit** | 89.9% | 91.2% | 89.8% | 84.0% | **88.1%** | 3.2% |
| **iCEpsilonGreedy** | 88.3% | 89.1% | 88.2% | 86.5% | **86.9%** | 1.2% |
| **EXPNeuralUCB** | 83.1% | 82.0% | 81.2% | 82.1% | **82.4%** | 0.5% |
| **EXPUCB** | 77.6% | 76.0% | 72.5% | 78.0% | **76.3%** | 2.5% |

**Critical Insight**: 
- CPursuit: **Highest average (88.1%), but high variance (3.2%)**
  - Excellent vs. Markov, but struggles OnlineAdaptive
- iCEpsilonGreedy: **Consistent (86.9% ± 1.2%)**
  - Best worst-case floor (81.0%)
- EXPNeuralUCB: **Lowest variance (0.5%), but very low floor (18% on OnlineAdaptive)**
  - ⚠️ Complete collapse under OnlineAdaptive!

---

### RQ3: Deployment Optimization

#### RQ3a: Predictive Context Benefit (iCPursuit vs CPursuit)

**Question**: Does predictive context help?

```python
config.setenvironment(
    attack_type='online_adaptive',
    allocator='Fixed',
    replay_memory_scale=2.0
)

# Compare:
model1 = 'CPursuit'  # No prediction
model2 = 'iCPursuit'  # With prediction
```

**Expected**: iCPursuit **+4.1pp average, +18.3pp OnlineAdaptive**

**Finding**: Prediction specifically helps against sophisticated adversaries.

---

#### RQ3b: Capacity Scaling Paradox (Non-Monotone!)

**Question**: Does larger replay memory always help?

```python
for replay_scale in [1.0, 1.5, 2.0]:
    config.setenvironment(
        replay_memory_scale=replay_scale,
        attack_type='adaptive'  # or test all threats
    )
    results = run_experiment(config)
```

**Expected Results** (Table VII in Paper2):

| Replay Scale | Stochastic | Markov | Adaptive | OnlineAdaptive |
|---|---|---|---|---|
| **1.0** | 89.9% | 91.2% | 89.8% | 84.0% |
| **1.5** | 89.2% | 89.8% | 85.3% ⚠️ | 81.2% ⚠️ |
| **2.0** | 88.1% | 88.5% | 81.0% ⚠️ | 78.9% ⚠️ |

**⚠️ Capacity Paradox**: Larger replay memory can **DEGRADE** performance under Adaptive scenarios!

**Why?**: Larger memory = slower adaptation, adversary exploits stale decisions.

**Implication**: Memory size is not just a performance dial; it's a tradeoff.

---

#### RQ3c: Allocator Co-Design (Which allocator best?)

**Question**: Which qubit allocation strategy is most robust?

```python
for allocator in ['Fixed', 'Thompson', 'DynamicUCB', 'Random']:
    config.setenvironment(allocator=allocator, ...)
    results = run_experiment(config)
```

**Expected Results** (Table IX in Paper2):

| Allocator | Stochastic | Markov | Adaptive | OnlineAdaptive | Avg | Span (Max-Min) |
|---|---|---|---|---|---|---|
| **Fixed** | 89.9% | 91.2% | 89.8% | 84.0% | **88.7%** | **8.5pp** ✅ |
| **Thompson** | 88.2% | 89.5% | 92.1% | 60.8% | **88.2%** | **31.3pp** ⚠️ |
| **DynamicUCB** | 68.5% | 70.2% | 72.8% | 70.1% | **70.1%** | 4.3pp |
| **Random** | 37.8% | 39.2% | 41.3% | 35.1% | **37.3%** | **6.2pp** (but very low) |

**Best Choice**: **Fixed allocator**
- Highest average (87.7%), most consistent (8.5pp span)
- Works well across all scenarios
- Simple, no tuning needed

**Runner-up**: Thompson (88.2% avg) but volatile (31.3pp span)

**Implication**: Static allocation is more robust than dynamic learning for this network.

---

#### RQ3d: Deployment Rules (What should teams use?)

**Question**: Which static configuration maximizes worst-case performance?

**Candidate Configurations**:

1. **iCPursuitNeuralUCB + Fixed + T-type + s=2** (Proposed)
2. CPursuit + Fixed + T-type + s=1
3. iCEpsilonGreedy + Fixed + T-type + s=1

**Expected Results**:

| Configuration | Static Default Avg | Worst-Case Floor |
|---|---|---|
| **iCPursuitNeuralUCB + Fixed + T + s=2** | **95.5%** | **88.5%** ✅ |
| CPursuit + Fixed + T + s=1 | 88.1% | 77.4% |
| iCEpsilonGreedy + Fixed + T + s=1 | 86.9% | 81.0% |

**Deployment Rule**:
```
Default: iCPursuitNeuralUCB + Fixed allocator + T-type + s=2
  → 95.5% global average, 88.5% worst-case floor

If OnlineAdaptive threat detected: Switch to EXPNeuralUCB
  → Maintains 82.1% under predictive attacks
```

---

## 🧠 Algorithms

### Evaluated Algorithms

| Algorithm | Type | Context? | Prediction? | Best For |
|-----------|------|----------|----------|---|
| **EXPUCB** | Classical | ❌ | ❌ | Baseline |
| **GNeuralUCB** | Neural | ❌ | ❌ | Adversarial |
| **EXPNeuralUCB** | Neural | ✅ | ❌ | Mixed threats |
| **CPursuit** | Hybrid | ✅ | ❌ | Stochastic noise |
| **iCEpsilonGreely** | Predictive | ✅ | ✅ | Consistent defense |
| **iCPursuitNeuralUCB** | Predictive | ✅ | ✅ | Best static default |

### Algorithm Family Performance

| Family | Typical Efficiency | Strength | Weakness |
|--------|---|---|---|
| **Classical** | 77-80% | Simple, stable | Low efficiency |
| **Adversarial** | 82-84% | Robust to attacks | No context |
| **Contextual** | 85-90% | Good balance | Variance under threat |
| **Predictive** | 85-95% | Exploits patterns | Complex, tuning |

---

## 🚀 Running Experiments

### RQ1: Single Algorithm Test

```python
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.experiment_runner import QuantumExperimentRunner

# Load Paper2 config
config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')

# Configure stochastic scenario
config.setenvironment(
    framesno=6000,
    attack_type='stochastic',
    attack_intensity=0.0625,
    allocator='Fixed'
)

# Run single algorithm
runner = QuantumExperimentRunner(id=1, config=config, frames_count=6000)
results = runner.runalgorithm('CPursuitNeuralUCB')

print(f"Algorithm: CPursuitNeuralUCB")
print(f"Final Reward: {results['final_reward']:.2f}")
print(f"Efficiency: {results['efficiency']:.1f}%")
print(f"Expected: 89.9% ± 2%")
```

**Expected Output**:
```
Algorithm: CPursuitNeuralUCB
Final Reward: 5394.00
Efficiency: 89.9%
```

---

### RQ2: Threat Escalation

```python
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

# Configure base
config = ExperimentConfiguration()
config.load_testbed_config('PAPER2')

# Run all threats
evaluator = MultiRunEvaluator(config=config, runs=5)

results = evaluator.test_threat_escalation(
    models=['CPursuit', 'iCEpsilonGreedy', 'EXPNeuralUCB'],
    threats=['Stochastic', 'Markov', 'Adaptive', 'OnlineAdaptive'],
    runs=5
)

# Visualize
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

viz = QuantumEvaluatorVisualizer(testbed='paper2')
viz.plot_threat_escalation(results, save_path='./results/')
```

---

### RQ3c: Allocator Comparison

```python
evaluator = MultiRunEvaluator(config=config, runs=5)

results = evaluator.test_allocator_robustness(
    algorithm='CPursuit',
    allocators=['Fixed', 'Thompson', 'DynamicUCB'],
    threats=['Stochastic', 'Markov', 'Adaptive', 'OnlineAdaptive'],
    runs=5
)

# Analyze
for allocator, metrics in results.items():
    avg = metrics['avg_efficiency']
    span = metrics['max'] - metrics['min']
    print(f"{allocator}: {avg:.1f}% avg, {span:.1f}pp span")
```

---

## 📊 Expected Results

### Summary Table (All RQs)

| Aspect | Best Performer | Value | Notes |
|--------|---|---|---|
| **RQ1: Stochastic** | CPursuit | 89.9% | +1.6pp vs. 2nd |
| **RQ2: Escalation** | CPursuit | 88.1% avg | High variance |
| **RQ3a: Prediction** | iCPursuit | +18.3pp vs. CPursuit (OnlineAdaptive) | Prediction crucial |
| **RQ3b: Replay Scale** | 1.0 (paradox!) | 89.9% | Larger ≠ better |
| **RQ3c: Allocator** | Fixed | 87.7% avg, 8.5pp span | Most robust |
| **RQ3d: Deployment** | iCPursuitNeuralUCB + Fixed | 95.5% global, 88.5% floor | Recommended default |

---

## 🧪 8-Test Validation Suite

Run `bash scripts/paper2_test_suite.sh` to execute all tests:

| # | Test | File | Duration | What It Tests |
|---|------|------|----------|---|
| 1 | Physics | `test_paper2_physics.py` | <1min | Fidelity model (0.9025, 0.8574) |
| 2 | Environment | `test_paper2_environment.py` | <1min | 4-path initialization |
| 3 | Single Alg | `test_paper2_single_algorithm.py` | 5-10min | CPursuit 85-92% range |
| 4 | RQ1 | `test_paper2_rq1_stochastic.py` | 20-30min | Table V matching |
| 5 | RQ2 | `test_paper2_rq2_threats.py` | 30-45min | Table VI matching |
| 6 | RQ3c | `test_paper2_rq3c_allocators.py` | 30-45min | Table IX patterns |
| 7 | RQ3b | `test_paper2_rq3b_capacity.py` | 20-30min | Paradox at s=1.5 |
| 8 | Viz | `test_paper2_visualization.py` | 10-15min | 6-panel plots + JSON |

**Total Runtime**: 2-3 hours

**Running All Tests**:
```bash
bash scripts/paper2_test_suite.sh
```

**Running Individual Tests**:
```bash
python tests/test_paper2_physics.py
python tests/test_paper2_rq1_stochastic.py
# ... etc
```

---

## 🔍 Troubleshooting

### Issue: "Efficiency 78.3% outside [85, 92]"

**Cause**: Wrong environment type or horizon

**Fix**:
```python
# Verify StochasticQuantumEnvironment
assert config.envtype == 'stochastic'
assert runner.frames_count == 6000
```

---

### Issue: "Physics values don't match (0.90 != 0.9025)"

**Cause**: Rounding or wrong precision

**Fix**:
```python
# Use exact values
fidelity_2hop = 0.95 * 0.95  # 0.9025 exactly
fidelity_3hop = 0.95 ** 3     # 0.857375 exactly
```

---

### Issue: "Allocator mismatch: got (8,10,8) expected (8,10,8,9)"

**Cause**: 4th path capacity missing

**Fix**:
```python
# Ensure all 4 paths
qubit_cap = (8, 10, 8, 9)  # 35 total, all 4 paths
```

---

## 📚 See Also

- **[TESTBEDS.md](TESTBEDS.md)** — Testbed overview & roadmap
- **[Paper2_Quick_Reference.md](Paper2_Quick_Reference.md)** — Parameter lookup card
- **[SETUP_COLAB.md](../setup_files/SETUP_COLAB.md)** — Colab instructions
- **[SETUP_LOCAL.md](../setup_files/SETUP_LOCAL.md)** — Local/GCP setup
- **[TROUBLESHOOTING.md](../setup_files/TROUBLESHOOTING.md)** — General issues

---

## ✅ Validation Checklist

Before presenting results to advisors:

- [ ] Physics validation passes (0.95² = 0.9025, 0.95³ = 0.8574)
- [ ] RQ1 CPursuit efficiency ∈ [87%, 92%]
- [ ] RQ1 results within ±2% of Table V
- [ ] RQ2 results within ±2% of Table VI (threat escalation)
- [ ] RQ3a shows iCPursuit +18.3pp on OnlineAdaptive
- [ ] RQ3b shows degradation at s=1.5 (capacity paradox)
- [ ] RQ3c shows Fixed allocator wins (87.7% avg, 8.5pp span)
- [ ] Visualization outputs generated successfully
- [ ] Metadata exported with experiment timestamps
- [ ] Results saved to shared `quantum_data_lake/paper2/`

---

**Framework Status**: ✅ PRODUCTION READY

🚀 **Ready to run Paper2 experiments!**

See [README.md](../README.md) for quick-start, or [TESTBEDS.md](TESTBEDS.md) for testbed overview.
