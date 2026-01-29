#!/usr/bin/env python3
"""
Lightweight Paper 7 sanity tests - STANDALONE VERSION.
Matches your notebook's get_physics_params() dictionary return format.

Run from repo root with:
    python scripts/run_paper7_sanity_tests.py
"""

import sys
import json
import time
import numpy as np
import networkx as nx
import itertools

# Make sure src/ is on the path
sys.path.insert(0, "src")

from daqr.core.topology_generator import Paper7ASTopologyGenerator
from daqr.core.quantum_physics import Paper7RewardFunction

# ============================================================================
# INLINE VERSION OF get_physics_params (Paper 7 only)
# ============================================================================

def generate_paper7_paths(topology, k: int, n_qisps: int, seed: int):
    """Generate k-shortest paths between n_qisps ISP nodes."""
    rng = np.random.default_rng(seed)
    nodes = list(topology.nodes())
    
    if len(nodes) < n_qisps:
        raise ValueError(f"Topology has {len(nodes)} nodes, need {n_qisps} for ISPs")
    
    isp_nodes = rng.choice(nodes, size=n_qisps, replace=False)
    all_paths = []
    
    for src, dst in itertools.combinations(isp_nodes, 2):
        try:
            path_generator = nx.shortest_simple_paths(topology, src, dst, weight='distance')
            paths = list(itertools.islice(path_generator, k))
            all_paths.extend(paths)
        except nx.NetworkXNoPath:
            continue
    
    return all_paths


def generate_paper7_contexts(paths, topology):
    """Generate context vectors for each path: [hop_count, avg_degree, path_length]."""
    contexts = []
    
    for path in paths:
        hop_count = len(path) - 1
        degrees = [topology.degree(node) for node in path]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0.0
        
        path_length = 0.0
        for i in range(len(path) - 1):
            edge_data = topology.get_edge_data(path[i], path[i+1])
            path_length += edge_data.get('distance', 1.0)
        
        context_vector = np.array([hop_count, avg_degree, path_length])
        contexts.append([context_vector])  # ✅ Match your format: list of lists
    
    return contexts


def get_physics_params_paper7(
    n_ases: int = 50,
    k: int = 5,
    n_qisps: int = 3,
    base_seed: int = 42,
    use_synthetic: bool = False,
    reward_mode: str = 'neg_hop',
    use_context_rewards: bool = True,
    topology_path: str = None,
):
    """
    Paper 7 (QBGP) physics parameter generation.
    Returns DICT matching your notebook format.
    """
    
    # 1. Generate topology
    try:
        if use_synthetic or not topology_path:
            topo_gen = Paper7ASTopologyGenerator(
                edge_list_path="dummy_nonexistent.txt",
                max_nodes=n_ases,
                seed=base_seed,
                synthetic_fallback=True,
                synthetic_kind="barabasi_albert",
                synthetic_params={"n": n_ases, "m": 3}
            )
            print(f"📊 Paper7 Topology: Synthetic (Barabási-Albert, n={n_ases})")
        else:
            topo_gen = Paper7ASTopologyGenerator(
                edge_list_path=topology_path,
                max_nodes=n_ases,
                seed=base_seed,
                relabel_to_integers=True,
                largest_cc_only=True,
                synthetic_fallback=True
            )
            print(f"📊 Paper7 Topology: Real AS ({topology_path})")
        
        final_topology = topo_gen.generate()
    except Exception as e:
        print(f"⚠️ Warning: Could not generate Paper7 topology: {e}")
        print("Creating minimal fallback topology...")
        final_topology = nx.Graph()
        for i in range(n_ases):
            final_topology.add_node(i)
        for i in range(n_ases - 1):
            final_topology.add_edge(i, i+1, distance=100.0 + i*10)
    
    # 2. Generate paths
    try:
        paths = generate_paper7_paths(final_topology, k, n_qisps, base_seed)
    except Exception as e:
        print(f"⚠️ Warning: Could not generate paths: {e}")
        paths = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]
    
    print(f"📊 Paper7 Paths: {len(paths)} paths from {k}-shortest between {n_qisps} ISPs")
    
    # 3. Generate contexts
    contexts = generate_paper7_contexts(paths, final_topology)
    
    # 4. Generate rewards (optional)
    external_rewards = None
    if use_context_rewards:
        reward_func = Paper7RewardFunction(mode=reward_mode)
        external_rewards = []
        for ctx_list in contexts:
            path_rewards = [reward_func.compute(ctx) for ctx in ctx_list]
            external_rewards.append(path_rewards)
        print(f"📊 Paper7 Rewards: Context-aware (mode={reward_mode})")
    else:
        print("📊 Paper7 Rewards: Using default framework rewards")
    
    # ✅ Return DICT matching your notebook format
    return {
        "noise_model": None,
        "fidelity_calculator": None,
        "external_topology": final_topology,
        "external_contexts": contexts,
        "external_rewards": external_rewards
    }


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_paper7_topology_and_paths():
    """Build AS-level topology and generate k-shortest paths between qISPs."""
    print("\n" + "=" * 70)
    print("TEST 1: Paper 7 topology + paths")
    print("=" * 70)

    t0 = time.time()
    result = get_physics_params_paper7(
        n_ases=50,
        k=5,
        n_qisps=3,
        base_seed=42,
        use_synthetic=False,
        topology_path='/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/core/topology_data/as20000101.txt'
    )
    dt = time.time() - t0

    topo = result["external_topology"]
    contexts = result["external_contexts"]

    print(f"Topology nodes: {len(topo.nodes)}")
    print(f"Topology edges: {len(topo.edges)}")
    print(f"#Paths (contexts): {len(contexts)}")
    print(f"get_physics_params_paper7() time: {dt*1000:.1f} ms")

    # Basic sanity checks
    ok = True
    if len(topo.nodes) < 10:
        print("⚠️ Topology has <10 nodes; check parameters.")
        ok = False
    if len(contexts) == 0:
        print("⚠️ No contexts generated; check path generation.")
        ok = False
    else:
        print("✅ Topology + paths generated successfully.")

    return {
        "nodes": len(topo.nodes),
        "edges": len(topo.edges),
        "num_paths": len(contexts),
        "elapsed_ms": dt * 1000,
        "ok": ok,
    }


def test_paper7_context_ranges():
    """Examine the hop / degree / length ranges from contexts."""
    print("\n" + "=" * 70)
    print("TEST 2: Paper 7 context ranges")
    print("=" * 70)

    result = get_physics_params_paper7(
        n_ases=50,
        k=5,
        n_qisps=3,
        base_seed=123,
        use_synthetic=True  # Faster for testing
    )

    contexts = result["external_contexts"]

    if not contexts:
        print("✗ No contexts returned.")
        return {"ok": False}

    # Flatten list of lists to array
    all_ctx = []
    for ctx_list in contexts:
        for ctx in ctx_list:
            all_ctx.append(ctx)
    
    all_ctx = np.array(all_ctx)
    hops = all_ctx[:, 0]
    degs = all_ctx[:, 1]
    lens = all_ctx[:, 2]

    print(f"Total context vectors: {all_ctx.shape[0]}")
    print(f"Hop count   :: min={hops.min():.1f},  max={hops.max():.1f}")
    print(f"Avg degree  :: min={degs.min():.1f},  max={degs.max():.1f}")
    print(f"Path length :: min={lens.min():.1f}, max={lens.max():.1f}")

    # Loose sanity windows
    ok = True
    if not (1 <= hops.min() <= 10):
        print("⚠️ hop_count min out of expected [1,10].")
        ok = False
    if not (1 <= hops.max() <= 15):
        print("⚠️ hop_count max out of expected [1,15].")
        ok = False
    if degs.max() <= 1:
        print("⚠️ avg_degree seems degenerate (<=1 everywhere).")
        ok = False
    if lens.max() <= 1.0:
        print("⚠️ path_length never exceeds 1.0; check distance attribute.")
        ok = False

    if ok:
        print("✅ Context ranges look reasonable for Paper 7.")

    return {
        "num_contexts": int(all_ctx.shape[0]),
        "hop_min": float(hops.min()),
        "hop_max": float(hops.max()),
        "deg_min": float(degs.min()),
        "deg_max": float(degs.max()),
        "len_min": float(lens.min()),
        "len_max": float(lens.max()),
        "ok": ok,
    }


def test_paper7_reward_samples():
    """Run Paper7RewardFunction on sample context vectors."""
    print("\n" + "=" * 70)
    print("TEST 3: Paper 7 reward function")
    print("=" * 70)

    result = get_physics_params_paper7(
        n_ases=50,
        k=5,
        n_qisps=3,
        base_seed=7,
        use_synthetic=True
    )

    contexts = result["external_contexts"]

    if not contexts:
        print("✗ No contexts returned; cannot test rewards.")
        return {"ok": False}

    # Take first 5 context vectors (flatten the list of lists)
    sample_ctx = []
    for ctx_list in contexts[:5]:
        sample_ctx.extend(ctx_list)
    sample_ctx = sample_ctx[:5]  # Just 5 samples
    
    print(f"Sample {len(sample_ctx)} context vectors:")

    # ✅ FIX: Use correct mode names with underscores
    reward_modes = ["neg_hop", "neg_degree", "neg_length"]
    results = {"ok": True, "modes": {}}

    for mode in reward_modes:
        try:
            rf = Paper7RewardFunction(mode=mode)
            rewards = [float(rf.compute(ctx)) for ctx in sample_ctx]
            print(f"\nMode = '{mode}'")
            for i, (ctx, r) in enumerate(zip(sample_ctx, rewards)):
                hop, deg, dist = ctx.tolist()
                print(f"  ctx[{i}] = [hop={hop:.1f}, deg={deg:.1f}, len={dist:.1f}] -> reward = {r:.3f}")
            results["modes"][mode] = rewards
        except Exception as e:
            print(f"⚠️ Mode '{mode}' failed: {e}")
            results["ok"] = False
            results["modes"][mode] = {"error": str(e)}

    if results["ok"]:
        print("\n✅ Reward function ran successfully for all modes.")
    else:
        print("\n⚠️ Some reward modes failed.")
    
    return results



def main():
    print("=" * 70)
    print("PAPER 7 (QBGP) SANITY TESTS - STANDALONE VERSION")
    print("=" * 70)
    
    summary = {}

    t0 = time.time()
    try:
        summary["topology_paths"] = test_paper7_topology_and_paths()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        summary["topology_paths"] = {"ok": False, "error": str(e)}
    
    try:
        summary["contexts"] = test_paper7_context_ranges()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        summary["contexts"] = {"ok": False, "error": str(e)}
    
    try:
        summary["rewards"] = test_paper7_reward_samples()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        summary["rewards"] = {"ok": False, "error": str(e)}
    
    total_time = time.time() - t0

    print("\n" + "=" * 70)
    print("PAPER 7 SANITY TESTS SUMMARY")
    print("=" * 70)
    print(json.dumps(summary, indent=2))
    print(f"\n⏱️  Total wall-clock time: {total_time:.1f} s")

    # Write results
    try:
        import os
        os.makedirs("results", exist_ok=True)
        with open("results/paper7_sanity_tests.json", "w") as f:
            json.dump(summary, f, indent=2)
        print("✅ Results saved to results/paper7_sanity_tests.json")
    except Exception as e:
        print(f"⚠️ Could not save summary JSON: {e}")

    # Final status
    all_ok = all(summary[k].get("ok", False) for k in summary if isinstance(summary[k], dict))
    if all_ok:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n⚠️ SOME TESTS HAD WARNINGS OR ERRORS")
        return 1


if __name__ == "__main__":
    sys.exit(main())
