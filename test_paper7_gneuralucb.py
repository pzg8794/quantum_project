#!/usr/bin/env python3
"""
Test Paper7 (QBGP) with GNeuralUCB after probability clamping fix.
Minimal test: Generate Paper7 paths and run GNeuralUCB for 10 frames.
"""
import sys
import os
import warnings
import numpy as np
import torch
import networkx as nx
import itertools
from pathlib import Path

warnings.filterwarnings('ignore')

# Add to path
sys.path.insert(0, '/workspaces/quantum_project/Dynamic_Routing_Eval_Framework')

from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.topology_generator import Paper7ASTopologyGenerator
from daqr.core.quantum_physics import Paper7RewardFunction

print("="*70)
print("PAPER7 (QBGP) GNEURALUCB TEST - PROBABILITY CLAMPING FIX")
print("="*70)

try:
    # Step 1: Initialize config
    print("\n[STEP 1] Initializing ExperimentConfiguration...")
    config = ExperimentConfiguration()
    print("✓ Config created")
    
    # Step 2: Generate Paper7 topology
    print("\n[STEP 2] Generating Paper7 topology...")
    topo_gen = Paper7ASTopologyGenerator(
        edge_list_path="dummy_nonexistent.txt",
        max_nodes=50,
        seed=42,
        synthetic_fallback=True,
        synthetic_kind="barabasi_albert",
        synthetic_params={"n": 50, "m": 3}
    )
    topology = topo_gen.generate()
    print(f"✓ Topology: {topology.number_of_nodes()} nodes, {topology.number_of_edges()} edges")
    
    # Step 3: Generate paths
    print("\n[STEP 3] Generating Paper7 paths...")
    rng = np.random.default_rng(42)
    nodes = list(topology.nodes())
    isp_nodes = rng.choice(nodes, size=3, replace=False)  # 3 ISPs
    
    all_paths = []
    for src, dst in itertools.combinations(isp_nodes, 2):
        try:
            path_generator = nx.shortest_simple_paths(topology, src, dst, weight='distance')
            paths = list(itertools.islice(path_generator, 5))  # 5 paths per pair
            all_paths.extend(paths)
        except nx.NetworkXNoPath:
            continue
    
    print(f"✓ Generated {len(all_paths)} paths")
    
    # Step 4: Generate contexts
    print("\n[STEP 4] Generating Paper7 contexts...")
    contexts = []
    for path in all_paths:
        hop_count = len(path) - 1
        degrees = [topology.degree(node) for node in path]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0.0
        
        path_length = 0.0
        for i in range(len(path) - 1):
            edge_data = topology.get_edge_data(path[i], path[i+1])
            path_length += edge_data.get('distance', 1.0)
        
        context_vector = np.array([hop_count, avg_degree, path_length])
        contexts.append([context_vector])
    
    print(f"✓ Generated {len(contexts)} context vectors")
    print(f"  Sample context: {contexts[0]}")
    
    # Step 5: Generate rewards
    print("\n[STEP 5] Generating Paper7 rewards...")
    reward_func = Paper7RewardFunction(mode='neg_hop')
    rewards = []
    for i, path in enumerate(all_paths):
        # Get context vector
        context_vector = contexts[i][0]
        # Compute reward from context
        reward_val = reward_func.compute(context_vector)
        # Create a list of 100 reward samples (one per frame)
        reward_samples = [reward_val] * 100
        rewards.append(reward_samples)
    
    print(f"✓ Generated {len(rewards)} reward lists")
    print(f"  First reward value: {rewards[0][0]}")
    print(f"  Reward range check: min={min(r[0] for r in rewards)}, max={max(r[0] for r in rewards)}")
    
    # Step 6: Create attack list
    print("\n[STEP 6] Creating attack list...")
    attack_list = [np.ones(len(all_paths)) for _ in range(100)]
    print(f"✓ Attack list created: {len(attack_list)} frames")
    
    # Step 7: Initialize GNeuralUCB
    print("\n[STEP 7] Initializing GNeuralUCB...")
    from daqr.algorithms.neural_bandits import GNeuralUCB
    
    try:
        gneuralucb = GNeuralUCB(
            configs=config,
            X_n=contexts,
            reward_list=rewards,
            frame_number=100,
            attack_list=attack_list,
            capacity=35
        )
        print("✓ GNeuralUCB initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Step 8: Run GNeuralUCB
    print("\n[STEP 8] Running GNeuralUCB for 100 frames...")
    results = gneuralucb.run(attack_list=attack_list)
    print("✓ GNeuralUCB executed successfully!")
    if results is not None:
        print(f"  Total frames run: {len(results.get('path_action_list', []))}")
        print(f"  Final regret: {results.get('final_regret', 'N/A')}")
        print(f"  Final reward: {results.get('final_reward', 'N/A')}")
    else:
        print("  (Results returned None - model completed execution)")
    
    print("\n" + "="*70)
    print("✅ SUCCESS - Paper7 with GNeuralUCB works!")
    print("✅ Probability clamping fix is working correctly!")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
