# 📋 Oracle Paper7 Integration Test - QUICK VALIDATION
# This is a minimal test to verify oracle fixes work in the notebook environment

print("=" * 80)
print("🔬 ORACLE PAPER7 FIX VALIDATION (Notebook Integration)")
print("=" * 80)

import numpy as np
from daqr.algorithms.base_bandit import Oracle

# Test 1: Verify NumPy array handling
print("\n[✓ TEST 1] NumPy Array Reward Handling")
print("-" * 80)

reward_list_numpy = [
    np.array([0.8, 0.6, 0.4]),      # Path 0: NumPy array
    np.array([0.75, 0.5, 0.3]),     # Path 1: NumPy array
    np.array([0.92, 0.7, 0.5]),     # Path 2: NumPy array (best)
    np.array([0.6, 0.4, 0.2])       # Path 3: NumPy array
]

# Test _calculate_oracle() directly (bypasses config initialization)
print("Testing Oracle._calculate_oracle() with NumPy arrays...")
oracle_path_np, oracle_action_np = Oracle._calculate_oracle(
    type('Oracle', (), {
        'reward_list': reward_list_numpy,
        'configs': type('Config', (), {'verbose': False})()
    })()
)
assert oracle_path_np == 2, f"ERROR: Expected path 2, got {oracle_path_np}"
assert oracle_action_np == 0, f"ERROR: Expected action 0, got {oracle_action_np}"
print(f"✅ PASS: Oracle correctly identified path {oracle_path_np}, action {oracle_action_np}")

# Test 2: Verify Python list handling
print("\n[✓ TEST 2] Python List Reward Handling")
print("-" * 80)

reward_list_py = [
    [0.8, 0.6, 0.4],        # Path 0: Python list
    [0.75, 0.5, 0.3],       # Path 1: Python list
    [0.9, 0.7, 0.5],        # Path 2: Python list (best)
    [0.6, 0.4, 0.2]         # Path 3: Python list
]

print("Testing Oracle._calculate_oracle() with Python lists...")
oracle_path_py, oracle_action_py = Oracle._calculate_oracle(
    type('Oracle', (), {
        'reward_list': reward_list_py,
        'configs': type('Config', (), {'verbose': False})()
    })()
)
assert oracle_path_py == 2, f"ERROR: Expected path 2, got {oracle_path_py}"
assert oracle_action_py == 0, f"ERROR: Expected action 0, got {oracle_action_py}"
print(f"✅ PASS: Oracle correctly identified path {oracle_path_py}, action {oracle_action_py}")

# Test 3: Verify _compute_optimal_actions with mixed types
print("\n[✓ TEST 3] _compute_optimal_actions with None attack_list")
print("-" * 80)

print("Testing Oracle._compute_optimal_actions() with None attack_list...")
oracle_obj = type('Oracle', (), {
    'reward_list': reward_list_numpy,
    'attack_list': None,
    'frame_number': 100,
    'configs': type('Config', (), {'verbose': False})()
})()

optimal_actions = Oracle._compute_optimal_actions(oracle_obj)
print(f"✅ PASS: Generated {len(optimal_actions)} optimal actions (max 10000 frames)")
assert len(optimal_actions) > 0, "ERROR: No optimal actions generated"
assert optimal_actions[0] == (2, 0, 0.92), f"ERROR: First optimal action incorrect: {optimal_actions[0]}"

# Test 4: Verify take_action bounds checking
print("\n[✓ TEST 4] take_action() bounds checking")
print("-" * 80)

print("Testing Oracle.take_action() with frame progression...")
oracle_obj = type('Oracle', (), {
    'reward_list': reward_list_numpy,
    'attack_list': None,
    'frame_number': 10,
    'configs': type('Config', (), {'verbose': False})(),
    'use_context_rewards': False,
    'optimal_actions': optimal_actions,
    'oracle_path': 2,
    'oracle_action': 0,
    'current_frame': 0
})()

# Simulate 100 frames without hanging
for i in range(100):
    path, action = Oracle.take_action(oracle_obj)
    oracle_obj.current_frame += 1
    if i % 20 == 0:
        print(f"  Frame {i}: path={path}, action={action}")

print(f"✅ PASS: Processed {oracle_obj.current_frame} frames without hanging or errors")

print("\n" + "=" * 80)
print("✅ ALL ORACLE FIXES VALIDATED SUCCESSFULLY!")
print("=" * 80)
print("\n🎯 Summary of Fixes:")
print("  ✓ NumPy array handling in _calculate_oracle()")
print("  ✓ Python list handling in _calculate_oracle()")
print("  ✓ None attack_list handling in _compute_optimal_actions()")
print("  ✓ Bounds checking in take_action()")
print("  ✓ Frame progression without hanging")
print("\n🚀 Oracle is ready for Paper7 (QBGP) testbed integration!")
print("=" * 80)
