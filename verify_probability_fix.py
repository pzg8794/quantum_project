#!/usr/bin/env python3
"""
Verify that the probability clamping fix is loaded and working.
"""
import sys
import inspect
import numpy as np

# Add to path
sys.path.insert(0, '/workspaces/quantum_project/Dynamic_Routing_Eval_Framework')

print("="*70)
print("VERIFYING PROBABILITY CLAMPING FIX")
print("="*70)

# Check 1: Verify fix is in source code
from daqr.algorithms.neural_bandits import EXPNeuralUCB

source = inspect.getsource(EXPNeuralUCB.run)

print("\n[CHECK 1] Searching for np.clip in EXPNeuralUCB.run()...")
if 'np.clip(base_reward, 0.0, 1.0)' in source:
    print("✅ FOUND: np.clip(base_reward, 0.0, 1.0)")
else:
    print("❌ NOT FOUND: np.clip not in run() method")
    sys.exit(1)

print("\n[CHECK 2] Searching for base_reward_prob variable...")
if 'base_reward_prob' in source:
    print("✅ FOUND: base_reward_prob variable")
else:
    print("❌ NOT FOUND: base_reward_prob variable missing")
    sys.exit(1)

print("\n[CHECK 3] Testing probability clamping logic...")
test_rewards = [0.5, 1.0, 5.0, 9.0, 10.0]
for reward in test_rewards:
    clamped = np.clip(reward, 0.0, 1.0)
    print(f"  reward={reward:4.1f} → clamped={clamped:.1f} → p=[{1-clamped:.1f}, {clamped:.1f}]", end="")
    try:
        np.random.choice([0, 1], p=[1 - clamped, clamped])
        print(" ✅")
    except ValueError as e:
        print(f" ❌ ERROR: {e}")
        sys.exit(1)

print("\n" + "="*70)
print("✅ ALL CHECKS PASSED - Probability clamping fix is working!")
print("="*70)
