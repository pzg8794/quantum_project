# Oracle Hang Issue - Root Cause Analysis & Fix

## Problem Summary
The oracle gets stuck when running Paper7 (QBGP) testbed experiments with error patterns like:
- Infinite loops during initialization
- Hangs during `ns.sim_run()` in benchmark_path()
- Data structure mismatches between Paper7 paths and oracle reward expectations

## Root Causes Identified

### Issue #1: `_calculate_oracle()` Expects List Indices (Paper2), Gets NumPy Arrays (Paper7)
**Location**: `daqr/algorithms/base_bandit.py` lines 540-555

**Problem**: 
```python
max_graph_action.append(path_rewards.index(max_reward))  # ❌ ERROR: NumPy arrays don't have .index()
```

Paper2 paths generate reward lists as Python lists:
```python
reward_list = [path0_rewards, path1_rewards, ...]  # Python list
reward_list[0] = [0.8, 0.6, 0.4, ...]  # Python list
```

Paper7 paths generate reward lists as NumPy arrays or mixed types:
```python
reward_list = [path0_rewards, path1_rewards, ...]  # NumPy arrays
reward_list[0] = np.array([0.8, 0.6, 0.4, ...])   # ❌ No .index() method
```

### Issue #2: `_compute_optimal_actions()` Requires Attack Patterns
**Location**: `daqr/algorithms/base_bandit.py` lines 432-465

**Problem**: 
The `attack_list` parameter may:
- Be None or empty for Paper7 (no attack patterns pre-computed)
- Have mismatched dimensions with reward_list
- Cause index out of bounds errors

### Issue #3: Paper7 Reward Functions Are Context-Aware
**Location**: Notebook `get_physics_params()` line 1100+

**Problem**: Paper7 uses `Paper7RewardFunction(mode='neg_hop')` which:
- Computes rewards dynamically from context vectors
- Doesn't provide static `reward_list` at initialization
- Requires different oracle computation strategy

### Issue #4: `benchmark_path()` Called Recursively in Oracle Initialization
**Location**: `daqr/algorithms/base_bandit.py` line 491+ (commented methods)

**Problem**: The original oracle might call `benchmark_path()` during init, triggering:
```python
def benchmark_path(self, source_as, path, bounces, sample_times):
    alice_protocol = NBProtocolAlice(...)
    bob_protocol = NBProtocolBob(...)
    alice_protocol.set_target_protocol(bob_protocol)
    # ⏱️ HANGS HERE: ns.sim_run() in Paper7 quantum simulation
```

## Solution Overview

### Fix #1: Make `_calculate_oracle()` Data Structure Agnostic
Convert both lists and NumPy arrays to consistent format before computing:
```python
def _calculate_oracle(self):
    max_graph_action = []
    oracle_graph_list = []
    
    for graph_index in range(len(self.reward_list)):
        path_rewards = self.reward_list[graph_index]
        # Convert to list if numpy array
        if isinstance(path_rewards, np.ndarray):
            path_rewards = path_rewards.tolist()
        
        max_reward = max(path_rewards)
        oracle_graph_list.append(max_reward)
        max_graph_action.append(path_rewards.index(max_reward))
    ...
```

### Fix #2: Skip `_compute_optimal_actions()` for Paper7 Context-Aware Rewards
Add conditional logic to detect Paper7 and skip pre-computation:
```python
def __init__(self, ...):
    self.use_context_rewards = getattr(configs, 'use_context_rewards', False)
    self.external_rewards = getattr(configs, 'external_rewards', None)
    
    if not self.use_context_rewards:
        self.optimal_actions = self._compute_optimal_actions()
    else:
        self.optimal_actions = []  # Computed on-the-fly in take_action()
```

### Fix #3: Add Paper7-Specific `take_action()` Logic
```python
def take_action(self):
    if self.use_context_rewards:
        # Dynamic computation for Paper7
        return self._get_dynamic_optimal_action()
    else:
        # Pre-computed for Paper2
        if self.current_frame >= len(self.optimal_actions):
            if len(self.optimal_actions) > 0:
                return self.optimal_actions[-1][0], self.optimal_actions[-1][1]
            return 0, 0
        path, action, _ = self.optimal_actions[self.current_frame]
        return path, action
```

### Fix #4: Add Safe `_compute_optimal_actions()` With Bounds Checking
```python
def _compute_optimal_actions(self):
    optimal_actions = []
    
    # Skip if using context-aware rewards
    if self.use_context_rewards or len(self.reward_list) == 0:
        return []
    
    # Defensive: Handle None/empty attack_list
    if self.attack_list is None:
        self.attack_list = [np.ones(len(self.reward_list)) for _ in range(len(self.reward_list))]
    
    for frame in range(min(len(self.attack_list), 1000)):  # Cap at 1000 frames
        best_reward = -float('inf')
        best_path = 0
        best_action = 0
        
        for path in range(len(self.reward_list)):
            if path < len(self.attack_list[frame]) and self.attack_list[frame][path] > 0:
                path_rewards = self.reward_list[path]
                if isinstance(path_rewards, np.ndarray):
                    path_rewards = path_rewards.tolist()
                
                best_path_action = path_rewards.index(max(path_rewards))
                path_reward = path_rewards[best_path_action] * self.attack_list[frame][path]
                
                if path_reward > best_reward:
                    best_reward = path_reward
                    best_path = path
                    best_action = best_path_action
        
        optimal_actions.append((best_path, best_action, best_reward))
    
    return optimal_actions
```

## Implementation Strategy

1. **Immediate Fix**: Update `Oracle` class to handle NumPy arrays in `_calculate_oracle()`
2. **Paper7 Support**: Add context-aware reward handling with dynamic computation
3. **Validation**: Add input validation and defensive bounds checking
4. **Testing**: Add unit test for Paper7 oracle with synthetic data

## Files to Modify

1. **`daqr/algorithms/base_bandit.py`** - Oracle class (primary fixes)
2. **`daqr/evaluation/experiment_runner.py`** - Run_step_wise_oracle() method (secondary)
3. **Notebook** - Add Paper7 oracle test validation (optional)

## Expected Outcomes

✅ Oracle initializes without hanging  
✅ Oracle works with both Paper2 (static rewards) and Paper7 (dynamic rewards)  
✅ Proper fallback when dimensions don't match  
✅ Defensive bounds checking prevents index errors  
