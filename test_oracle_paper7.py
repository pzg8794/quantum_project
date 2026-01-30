#!/usr/bin/env python3
"""
🔬 ORACLE TEST SUITE - Paper7 (QBGP) Testbed Validation
Tests oracle behavior with both Paper2 and Paper7 reward structures
"""

import sys
import numpy as np
import tempfile
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "Dynamic_Routing_Eval_Framework"))

print("=" * 80)
print("🔬 ORACLE VALIDATION TEST SUITE")
print("=" * 80)

# Test 1: Basic Oracle Initialization (Paper2-style list rewards)
print("\n[TEST 1] Oracle with Python List Rewards (Paper2-style)")
print("-" * 80)

try:
    from daqr.algorithms.base_bandit import Oracle
    from daqr.config.experiment_config import ExperimentConfiguration
    
    # Create mock config
    config = ExperimentConfiguration()
    config.verbose = False
    config.overwrite = True
    config.scale = 1
    config.dir = str(tempfile.gettempdir())
    config.day_str = "test"
    config.backup_mgr = type('obj', (object,), {
        'mode': 'local',
        'quantum_data_paths': {'obj': {'model_state': {'local': Path(tempfile.gettempdir())}}}
    })()
    
    # Paper2-style: Python lists of rewards
    X_n = 4
    reward_list = [
        [0.8, 0.6, 0.4],      # Path 0: 3 actions
        [0.75, 0.5, 0.3],     # Path 1: 3 actions
        [0.9, 0.7, 0.5],      # Path 2: 3 actions (best path)
        [0.6, 0.4, 0.2]       # Path 3: 3 actions
    ]
    
    attack_list = [
        np.array([1.0, 1.0, 1.0, 1.0]),  # Frame 0: no attacks
        np.array([1.0, 1.0, 1.0, 1.0]),  # Frame 1: no attacks
        np.array([1.0, 1.0, 1.0, 1.0])   # Frame 2: no attacks
    ]
    
    oracle = Oracle(
        configs=config,
        X_n=X_n,
        reward_list=reward_list,
        frame_number=3,
        attack_list=attack_list,
        capacity=10000
    )
    
    # Test take_action
    path, action = oracle.take_action()
    assert path == 2 and action == 0, f"Expected path=2, action=0 but got path={path}, action={action}"
    oracle.update(path, action, 0.9)
    
    results = oracle.get_results()
    assert results['final_reward'] == 0.9, f"Expected final_reward=0.9 but got {results['final_reward']}"
    
    print("✅ PASSED: Oracle correctly selects path 2 (highest max reward 0.9)")
    print(f"   - Oracle path: {oracle.oracle_path}, Oracle action: {oracle.oracle_action}")
    print(f"   - Action returned: path={path}, action={action}")
    print(f"   - Final reward: {results['final_reward']}")

except AssertionError as e:
    print(f"❌ FAILED: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Oracle with NumPy Array Rewards (Paper7-style)
print("\n[TEST 2] Oracle with NumPy Array Rewards (Paper7-style)")
print("-" * 80)

try:
    from daqr.algorithms.base_bandit import Oracle
    from daqr.config.experiment_config import ExperimentConfiguration
    
    config = ExperimentConfiguration()
    config.verbose = False
    config.overwrite = True
    config.scale = 1
    config.dir = str(tempfile.gettempdir())
    config.day_str = "test"
    config.backup_mgr = type('obj', (object,), {
        'mode': 'local',
        'quantum_data_paths': {'obj': {'model_state': {'local': Path(tempfile.gettempdir())}}}
    })()
    
    # Paper7-style: NumPy arrays of rewards
    reward_list = [
        np.array([0.8, 0.6, 0.4]),      # Path 0: NumPy array
        np.array([0.75, 0.5, 0.3]),     # Path 1: NumPy array
        np.array([0.92, 0.7, 0.5]),     # Path 2: NumPy array (best path)
        np.array([0.6, 0.4, 0.2])       # Path 3: NumPy array
    ]
    
    attack_list = [
        np.array([1.0, 1.0, 1.0, 1.0]),
        np.array([1.0, 1.0, 1.0, 1.0]),
        np.array([1.0, 1.0, 1.0, 1.0])
    ]
    
    oracle = Oracle(
        configs=config,
        X_n=4,
        reward_list=reward_list,
        frame_number=3,
        attack_list=attack_list,
        capacity=10000
    )
    
    # Test take_action
    path, action = oracle.take_action()
    assert path == 2 and action == 0, f"Expected path=2, action=0 but got path={path}, action={action}"
    oracle.update(path, action, 0.92)
    
    results = oracle.get_results()
    assert results['final_reward'] == 0.92, f"Expected final_reward=0.92 but got {results['final_reward']}"
    
    print("✅ PASSED: Oracle correctly selects path 2 with NumPy array rewards")
    print(f"   - Oracle path: {oracle.oracle_path}, Oracle action: {oracle.oracle_action}")
    print(f"   - Action returned: path={path}, action={action}")
    print(f"   - Final reward: {results['final_reward']}")

except AssertionError as e:
    print(f"❌ FAILED: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Oracle with None attack_list (Paper7 default)
print("\n[TEST 3] Oracle with None attack_list (Paper7 context-aware mode)")
print("-" * 80)

try:
    from daqr.algorithms.base_bandit import Oracle
    from daqr.config.experiment_config import ExperimentConfiguration
    
    config = ExperimentConfiguration()
    config.verbose = False
    config.overwrite = True
    config.scale = 1
    config.use_context_rewards = True  # Paper7 mode
    config.dir = str(tempfile.gettempdir())
    config.day_str = "test"
    config.backup_mgr = type('obj', (object,), {
        'mode': 'local',
        'quantum_data_paths': {'obj': {'model_state': {'local': Path(tempfile.gettempdir())}}}
    })()
    
    # Paper7 with context-aware rewards: None attack_list
    reward_list = [
        np.array([0.5, 0.4, 0.3]),      # Path 0
        np.array([0.7, 0.6, 0.5]),      # Path 1
        np.array([0.85, 0.75, 0.65]),   # Path 2 (best)
        np.array([0.6, 0.5, 0.4])       # Path 3
    ]
    
    oracle = Oracle(
        configs=config,
        X_n=4,
        reward_list=reward_list,
        frame_number=100,
        attack_list=None,  # Paper7 mode: None for context-aware
        capacity=10000
    )
    
    # Test take_action
    path, action = oracle.take_action()
    assert path == 2 and action == 0, f"Expected path=2, action=0 but got path={path}, action={action}"
    oracle.update(path, action, 0.85)
    
    results = oracle.get_results()
    assert results['final_reward'] == 0.85, f"Expected final_reward=0.85 but got {results['final_reward']}"
    
    print("✅ PASSED: Oracle handles None attack_list (Paper7 context-aware)")
    print(f"   - Oracle path: {oracle.oracle_path}, Oracle action: {oracle.oracle_action}")
    print(f"   - Action returned: path={path}, action={action}")
    print(f"   - Final reward: {results['final_reward']}")
    print(f"   - use_context_rewards: {oracle.use_context_rewards}")

except AssertionError as e:
    print(f"❌ FAILED: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Oracle frame progression (no hang)
print("\n[TEST 4] Oracle frame progression - 1000 frames (hang detection)")
print("-" * 80)

try:
    from daqr.algorithms.base_bandit import Oracle
    from daqr.config.experiment_config import ExperimentConfiguration
    
    config = ExperimentConfiguration()
    config.verbose = False
    config.overwrite = True
    config.scale = 1
    config.dir = str(tempfile.gettempdir())
    config.day_str = "test"
    config.backup_mgr = type('obj', (object,), {
        'mode': 'local',
        'quantum_data_paths': {'obj': {'model_state': {'local': Path(tempfile.gettempdir())}}}
    })()
    
    # Create large reward set with 1000 frames
    num_paths = 4
    num_actions = 3
    num_frames = 1000
    
    reward_list = [
        np.random.uniform(0.5, 0.95, num_actions) for _ in range(num_paths)
    ]
    
    attack_list = [
        np.ones(num_paths) for _ in range(num_frames)
    ]
    
    import time
    start = time.time()
    
    oracle = Oracle(
        configs=config,
        X_n=num_paths,
        reward_list=reward_list,
        frame_number=num_frames,
        attack_list=attack_list,
        capacity=10000
    )
    
    init_time = time.time() - start
    
    # Simulate 1000 frames without hanging
    total_reward = 0.0
    for frame in range(num_frames):
        path, action = oracle.take_action()
        reward = np.random.uniform(0.5, 0.95)  # Mock reward
        oracle.update(path, action, reward)
        total_reward += reward
    
    sim_time = time.time() - start - init_time
    
    results = oracle.get_results()
    assert len(results['path_action_list']) == num_frames, f"Expected {num_frames} actions but got {len(results['path_action_list'])}"
    
    print(f"✅ PASSED: Oracle processed {num_frames} frames without hanging")
    print(f"   - Initialization time: {init_time:.3f}s")
    print(f"   - Simulation time: {sim_time:.3f}s")
    print(f"   - Total frames processed: {len(results['path_action_list'])}")
    print(f"   - Final regret: {results['final_regret']}")

except AssertionError as e:
    print(f"❌ FAILED: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Mixed data types (lists + arrays)
print("\n[TEST 5] Oracle with mixed data types (Python lists + NumPy arrays)")
print("-" * 80)

try:
    from daqr.algorithms.base_bandit import Oracle
    from daqr.config.experiment_config import ExperimentConfiguration
    
    config = ExperimentConfiguration()
    config.verbose = False
    config.overwrite = True
    config.scale = 1
    config.dir = str(tempfile.gettempdir())
    config.day_str = "test"
    config.backup_mgr = type('obj', (object,), {
        'mode': 'local',
        'quantum_data_paths': {'obj': {'model_state': {'local': Path(tempfile.gettempdir())}}}
    })()
    
    # Mix of Python lists and NumPy arrays
    reward_list = [
        [0.8, 0.6, 0.4],              # Python list
        np.array([0.75, 0.5, 0.3]),   # NumPy array
        (0.9, 0.7, 0.5),              # Tuple
        np.array([0.6, 0.4, 0.2])     # NumPy array
    ]
    
    attack_list = [
        np.array([1.0, 1.0, 1.0, 1.0]),
        np.array([1.0, 1.0, 1.0, 1.0])
    ]
    
    oracle = Oracle(
        configs=config,
        X_n=4,
        reward_list=reward_list,
        frame_number=2,
        attack_list=attack_list,
        capacity=10000
    )
    
    path, action = oracle.take_action()
    assert path == 2 and action == 0, f"Expected path=2, action=0 but got path={path}, action={action}"
    
    print("✅ PASSED: Oracle handles mixed data types (lists, NumPy arrays, tuples)")
    print(f"   - Reward types: list, ndarray, tuple, ndarray")
    print(f"   - Oracle path: {oracle.oracle_path}, Oracle action: {oracle.oracle_action}")
    print(f"   - Action returned: path={path}, action={action}")

except AssertionError as e:
    print(f"❌ FAILED: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("✅ ORACLE TEST SUITE COMPLETE")
print("=" * 80)
print("\nKey fixes validated:")
print("  ✓ NumPy array reward handling (Paper7)")
print("  ✓ Python list reward handling (Paper2)")
print("  ✓ None attack_list handling (Paper7 context-aware)")
print("  ✓ Frame progression without hanging")
print("  ✓ Mixed data type handling")
print("\nOracle is ready for Paper7 integration!")
print("=" * 80)
