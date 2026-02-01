# Paper 12 (QuARC) - Allocator Execution Flow

## ⭐ BASELINE PARAMETERS CLARIFICATION

**Official Paper 12 Baseline (Wang et al. 2024)**:
- `fusion_prob (q)`: 0.9
- `entanglement_prob (E_p)`: 0.6
- **Combined success rate**: 0.9 × 0.6 = **54%** (EXPECTED, NOT A PROBLEM)

**Status**: ✅ **Baseline parameters work correctly** with fixed reward generation code (Beta distribution)

**Previous Issue**: Was caused by **broken reward code**, not low parameters.  
Once fixed with proper Beta distribution, baseline operates as expected.

---

## Overview
Paper 12 (QuARC) runs through the evaluation framework's `AllocatorRunner`, which orchestrates the entire quantum routing simulation with dynamic qubit allocation.

---

## Execution Flow: How Paper 12 Runs Through Each Allocator

### **Phase 1: Physics Initialization** (Once per experiment)

```
AllocatorRunner.run()
  ↓
  For each run:
    ├─ Call: get_physics_params(physics_model='paper12', seed=...)
    │   ├─ Calls: get_physics_params_paper12(config, seed, qubit_cap)
    │   │   ├─ Generates Waxman topology (100 nodes, E_d=6)
    │   │   │   └─ Uses Paper12WaxmanTopologyGenerator (fallback)
    │   │   │   └─ TODO: Replace with BlobbedQCastNetwork for .net files
    │   │   │
    │   │   ├─ Calls: generate_paper12_paths(topology, 4, seed)
    │   │   │   └─ Finds 4 random source-destination paths
    │   │   │   └─ Uses nx.shortest_path() for path selection
    │   │   │
    │   │   ├─ Calls: generate_paper12_contexts(paths, topology, q=0.9)
    │   │   │   └─ Creates context vectors: [hop_count, norm_degree, fusion_prob]
    │   │   │   └─ Shape: 4 context arrays, each [1, 3]
    │   │   │   └─ Uses official baseline fusion_prob=0.9
    │   │   │
    │   │   ├─ Creates FusionNoiseModel(topology, paths, q=0.9, E_p=0.6)
    │   │   │   └─ Official Paper 12 baseline parameters
    │   │   │   └─ Combined success: 54% (authentic baseline rate)
    │   │   │   └─ Handles quantum channel noise
    │   │   │   └─ Computes entanglement success probabilities
    │   │   │
    │   │   ├─ Creates FusionFidelityCalculator()
    │   │   │   └─ Computes path fidelities for fusion operations
    │   │   │
    │   │   └─ Returns:
    │   │       ├─ external_topology: NetworkX graph (100 nodes)
    │   │       ├─ external_contexts: List of 4 context vectors
    │   │       ├─ external_rewards: Pre-computed rewards per path
    │   │       ├─ noise_model: FusionNoiseModel instance
    │   │       └─ fidelity_calculator: FusionFidelityCalculator instance
```

---

### **Phase 2: Allocator-Specific Loop** (Every frame_step = 500 timeslots)

Each allocator follows this pattern at every epoch boundary (500ts):

#### **Default Allocator**
- Strategy: **Static equal allocation**
- Qubit distribution: `q_i(t) = total_qubits / num_paths`
- Updates: NONE (no learning)
- Use: Baseline control group

```
Frame loop (t = 0, 500, 1000, 1500, ...):
  ├─ allocator.allocate()
  │   └─ Returns: q_1=25, q_2=25, q_3=25, q_4=25 (fixed)
  │
  └─ For each path i in [1, 2, 3, 4]:
      ├─ Sample request: (src, dst) from path_i
      ├─ Call: FusionNoiseModel.get_error_rates(path_i)
      │   └─ Returns: channel error rates for all hops in path
      ├─ Call: FusionFidelityCalculator.compute_path_fidelity(...)
      │   └─ Returns: F_i(t) = success probability
      ├─ Reward: r_i(t) = F_i(t) (entanglement success)
      └─ Update statistics: throughput, latency, allocation_efficiency
```

#### **Dynamic Allocator**
- Strategy: **Proportional adaptive allocation**
- Qubit distribution: `q_i(t) ∝ F_i(t-1)` (proportional to recent success)
- Updates: Every epoch
- Use: Responsive to current network state

```
Frame loop (t = 0, 500, 1000, 1500, ...):
  ├─ Compute recent success rates:
  │   ├─ success_1 = avg(rewards[path_1] over last epoch)
  │   ├─ success_2 = avg(rewards[path_2] over last epoch)
  │   ├─ success_3 = avg(rewards[path_3] over last epoch)
  │   └─ success_4 = avg(rewards[path_4] over last epoch)
  │
  ├─ Reallocate qubits:
  │   ├─ total = sum(success_i for all i)
  │   └─ q_i(t) = (success_i / total) * total_qubits
  │
  └─ For each path: [same reward loop as Default]
```

#### **Thompson Sampling Allocator**
- Strategy: **Bayesian posterior sampling**
- Qubit distribution: `q_i(t) ~ sample(Beta posterior for path i)`
- Updates: Every epoch
- Use: Balanced exploration & exploitation

```
Frame loop (t = 0, 500, 1000, 1500, ...):
  ├─ Maintain Beta posteriors:
  │   ├─ θ_1 ~ Beta(α_1, β_1)  [successes, failures for path 1]
  │   ├─ θ_2 ~ Beta(α_2, β_2)
  │   ├─ θ_3 ~ Beta(α_3, β_3)
  │   └─ θ_4 ~ Beta(α_4, β_4)
  │
  ├─ Sample from posteriors:
  │   ├─ p_1 ~ Beta(α_1, β_1)
  │   ├─ p_2 ~ Beta(α_2, β_2)
  │   ├─ p_3 ~ Beta(α_3, β_3)
  │   └─ p_4 ~ Beta(α_4, β_4)
  │
  ├─ Allocate proportionally:
  │   └─ q_i(t) = (p_i / sum(p_j)) * total_qubits
  │
  ├─ Observe rewards: r_i(t)
  │
  └─ Update posteriors:
      ├─ If r_i(t) = 1: α_i += 1  (success)
      └─ If r_i(t) = 0: β_i += 1  (failure)
```

#### **Random Allocator**
- Strategy: **Uniform random allocation** (no learning)
- Qubit distribution: `q_i(t) ~ Uniform(min_q, max_q)`
- Updates: NONE
- Use: Theoretical worst-case baseline

```
Frame loop (t = 0, 500, 1000, 1500, ...):
  ├─ allocator.allocate()
  │   └─ Returns: q_i(t) ~ Uniform(min_qubits, max_qubits) for each path
  │
  └─ For each path: [same reward loop as Default]
```

---

### **Phase 3: QuARC Protocol Integration** (Every epoch = 500ts)

At epoch boundaries (t = 500, 1000, 1500, ...):

```
if t % epoch_length == 0:  # Every 500 timeslots
  ├─ Get current merge/split thresholds:
  │   └─ merge_th, split_th = get_paper12_thresholds(n_nodes=100)
  │       └─ merge_th ≈ 0.65, split_th ≈ 0.85
  │
  ├─ Evaluate cluster performance:
  │   ├─ success_rate = avg(fusion success over epoch)
  │   │
  │   ├─ if success_rate < merge_th:
  │   │   └─ MERGE clusters (reduce parallelism)
  │   │
  │   └─ if success_rate > split_th:
  │       └─ SPLIT clusters (increase parallelism)
  │
  └─ Log cluster configuration change (if any)
```

---

## Frame Alignment with Epochs

The framework uses **frame_step = 500** to align allocator updates with QuARC's **epoch_length = 500**:

```
Total Simulation: T = 1500 timeslots = 3 epochs

Timeline:
  t=0     t=500       t=1000      t=1500
  |----------|----------|----------|
  Epoch 1    Epoch 2    Epoch 3    End
  (Initial)  (Reconfig) (Reconfig)

Checkpoints:
  t=500:   Frame 1  → Allocator checkpoint + QuARC epoch boundary
  t=1000:  Frame 2  → Allocator checkpoint + QuARC epoch boundary
  t=1500:  Frame 3  → Allocator checkpoint + QuARC epoch boundary
```

---

## Context Vectors and Rewards

### Context Vector (per path, shape [1, 3])
```python
context = [
    hop_count,           # Number of quantum hops in path (0-20 typical)
    normalized_degree,   # Avg node degree / max degree (0.0-1.0)
    fusion_prob          # Fusion gate success probability (0.9 for Paper 12)
]
```

### Reward Computation (per path per frame)
```python
reward = FusionNoiseModel.get_error_rates(path_idx)
       → FusionFidelityCalculator.compute_path_fidelity(error_info)
       → success_probability = F(q=0.9, E_p=0.6, hops, degree)
       → reward ∈ [0, 1]  # Entanglement success rate
```

---

## Configuration Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| **Topology** | Waxman (100 nodes, E_d=6) | Paper 12 spec |
| **Fusion Prob (q)** | 0.9 | Paper 12 spec |
| **Entanglement Prob (E_p)** | 0.6 | Paper 12 spec |
| **Epoch Length** | 500 timeslots | Paper 12 spec |
| **Total Simulation** | 1500 timeslots (3 epochs) | Test config |
| **Paths per Evaluation** | 4 (via generate_paper12_paths) | Framework standard |
| **Context Dimensions** | 3 ([hop_count, norm_degree, fusion_prob]) | QuARC semantics |
| **Reward Function** | Entanglement success rate | FusionFidelityCalculator |

---

## Expected Output

After running all allocators, results are saved to:
```
results/paper12_default.pkl       # Default allocator results
results/paper12_dynamic.pkl       # Dynamic allocator results  
results/paper12_thompsonsampling.pkl  # Thompson Sampling results
results/paper12_random.pkl        # Random (baseline) results
```

Each contains:
```
{
    'allocator': 'Dynamic',
    'physics_model': 'paper12',
    'metadata': {
        'paper': 'Wang2024Paper12',
        'retry_enabled': False,
        'fusion_prob': 0.9,
        'entanglement_prob': 0.6,
        'topology': 'waxman_100_60_90_6_3_seed'
    },
    'results': {
        'throughput': [...],          # Per-epoch throughput
        'latency': [...],             # Per-epoch latency
        'reward': [...],              # Per-epoch cumulative reward
        'allocation_efficiency': [...] # Qubit utilization efficiency
    },
    'configurations': [
        {'epoch': 0, 'q_1': 25, 'q_2': 25, 'q_3': 25, 'q_4': 25},
        {'epoch': 1, 'q_1': 24, 'q_2': 26, 'q_3': 25, 'q_4': 25},
        {'epoch': 2, 'q_1': 23, 'q_2': 27, 'q_3': 25, 'q_4': 25},
    ]
}
```

---

## Key Insights

1. **Allocator Choice Matters**: Dynamic and Thompson Sampling learn from success rates; Random and Default do not.

2. **Context Integration**: All allocators receive the same context vectors, enabling fair comparison of decision-making strategies.

3. **QuARC Synchronization**: Allocator checkpoints align with epoch boundaries, ensuring clustering decisions influence qubit allocation in the next epoch.

4. **Fusion Physics**: Success rates naturally degrade over hops, rewarding shorter paths unless allocators strategically direct qubits to longer paths with fewer established clusters.

5. **Stochastic Evaluation**: Each run uses different random network conditions (E_p, q subject to random perturbations), making results statistically robust.
