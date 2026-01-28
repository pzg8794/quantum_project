"""
Automated Runner - Loops through all allocators, capacity types, and scales
"""

import os
import sys
import gc
import weakref
import subprocess
import warnings
import importlib
import torch
import networkx as nx
import numpy as np
import itertools
import traceback
from pathlib import Path
warnings.filterwarnings('ignore')



# ============================================================================
# STEP 1: CLEANUP STATE + DUPLICATES
# ============================================================================

def deep_cleanup():
    """Remove all instantiated model/evaluator objects and clear memory."""
    to_clear = [
        "oracle", "gneuralucb", "expneuralucb",
        "cpursuitneuralucb", "icpursuitneuralucb",
        "evaluator", "results"
    ]

    for name in to_clear:
        if name in globals():
            obj = globals().get(name, None)
            try:
                if hasattr(obj, "cleanup"):
                    obj.cleanup(verbose=False)
            except:
                pass
            globals().pop(name, None)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    gc.collect()
    torch.set_default_dtype(torch.float32)
    print("✓ Deep cleanup complete (memory cleared)")

deep_cleanup()
# Run external cleanup script
root = os.path.abspath("../..")
cleanup_script = os.path.abspath(f"{root}/cleanup_state_duplicates.py")
print(f"🚿 Running cleanup script at:\n{cleanup_script}\n")
result = subprocess.run(["python3", cleanup_script], text=True, capture_output=True)

print("===== CLEANUP STDOUT =====\n",result.stdout)
print("===== CLEANUP STDERR =====\n", result.stderr)
print("🚿 Cleanup finished.\n")



# ============================================================================
# STEP 2: ENVIRONMENT SETUP
# ============================================================================
cur_dir = os.getcwd()
print(f"Current working directory: {cur_dir.split('/')[-1]}")
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    project_dir = '/content/drive/MyDrive/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework'
    os.chdir(project_dir)
    print("Running in Google Colab")
    project_code_dir = os.path.join(project_dir, 'src')
    sys.path.insert(0, project_code_dir)
except ImportError:
    print("Running locally (not in Colab)")
    PARENT_DIR = os.path.abspath("..")
    if PARENT_DIR not in sys.path: sys.path.insert(0, PARENT_DIR)
print(f"Now working from: {os.getcwd().split('/')[-1]}")



# ============================================================================
# STEP 3: CLEAN MODULE RELOAD
# ============================================================================

# ✅ UPDATED: Add attack_strategy to imports
from daqr.core import attack_strategy
from daqr.config import experiment_config, gd_backup_manager, local_backup_manager
from daqr.core import network_environment, qubit_allocator
from daqr.algorithms import neural_bandits, predictive_bandits, base_bandit
from daqr.evaluation import multi_run_evaluator, visualizer, experiment_runner

# ✅ UPDATED: Add attack_strategy to reload list
for module in [experiment_config, network_environment, qubit_allocator, attack_strategy,
               base_bandit, neural_bandits, predictive_bandits, experiment_runner, multi_run_evaluator, visualizer]:
    importlib.reload(module)

# Import classes after reload
from daqr.evaluation.multi_run_evaluator import *
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.qubit_allocator import (QubitAllocator, RandomQubitAllocator, DynamicQubitAllocator, ThompsonSamplingAllocator)

from daqr.core.quantum_physics import FusionNoiseModel
from daqr.core.topology_generator import Paper2TopologyGenerator
from daqr.core.topology_generator import Paper7ASTopologyGenerator
from daqr.core.topology_generator import Paper12WaxmanTopologyGenerator
from daqr.core.quantum_physics import FiberLossNoiseModel, CascadedFidelityCalculator
from daqr.core.quantum_physics import FusionNoiseModel, FusionFidelityCalculator, QuARCRewardFunction

# ==================== PAPER-SPECIFIC IMPORTS ====================
# Paper 2: Full Physics Implementation
from daqr.core.quantum_physics import (
    MemoryNoiseModel,
    FullPaper2FidelityCalculator,
    Paper2RewardFunction
)

# Paper 7: Context-Aware Rewards
from daqr.core.quantum_physics import Paper7RewardFunction

# Paper 12: Retry Logic
from daqr.core.quantum_physics import Paper12RetryFidelityCalculator

print("✓ All modules reloaded successfully (fresh environment ready)")



# ============================================================================
# CONFIGURATION - FROM YOUR FRAMEWORK_CONFIG
# ============================================================================

# Initialize base config to get model lists
config = ExperimentConfiguration()

# ✅ UPDATED: Fixed syntax and added Paper #2 config
FRAMEWORK_CONFIG = {
    # Testing Configuration
    'exp_num': 1,
    'test_mode': True,
    'frame_step': 50,
    'base_frames': 50,
    
    # Production Configuration
    'frame_steps': [],
    'prod_frames': 4000,
    'prod_experiments': 10,
    
    # Primary evaluation focus
    'main_env': 'stochastic',
    'eval_mod': 'comprehensive',
    'main_model': 'CEXPNeuralUCB',
    
    # Routing strategy configuration
    'routing_strategy': 'fixed',
    'enable_routing_comparison': False,
    
    # Algorithm parameters (EXPNeuralUCB paper-compliant)
    'alg_attrs': {
        'gamma': 0.1,
        'lambda_reg': 1.0,
        'network_depth': 2,
        'gradient_steps': 8,
        'network_width': 128,
        'learning_rate': 1e-4
    },

    # Environment parameters
    'env_attrs': {
        'intensity': 0.25,  # Natural failure rate for stochastic
        'base_seed': 12345,
        'reproducible': True
    },

    # Test scenarios
    'scenarios': {
        'exp_focus': ['stochastic'],
        'stochastic_vs_baseline': ['none', 'stochastic'],
        'comprehensive': ['none', 'stochastic', 'markov', 'adaptive'],
        'adversarial': ['markov', 'adaptive', 'onlineadaptive']
    },

    # ✅ NEW: Paper #2 physics configuration
    # Default/Your Framework
    'default': {
        'num_paths': 4,
        'total_qubits': 35,
        'min_qubits_per_route': 2,
        'exploration_bonus': 2.0,
        'epsilon': 1.0,
        'seed': 42
    },

    'time_decay_physics': 0.5,
    
    # Paper #2 (Huang et al. - Your Neural Bandit Work)
    'paper2': {
        'num_paths': 8,              # From your GA reports
        'dest_node': 14,
        'num_nodes': 15,
        'source_node': 1,
        'p_init': 0.00001,
        'total_qubits': 35,          # Your standard
        'f_attenuation': 0.05,
        'exploration_bonus': 2.0,
        'min_qubits_per_route': 2,
        'use_paper2_rewards': True,
        # NEW:
        'swap_mode': 'async',             # or 'sync'
        'memory_T2': 5000,
        'gate_error_rate': 0.02,
        'swap_delay_per_link': 100,


        # 🆕 NEW: Feature toggles
        'use_gate_error': True,           # Enable gate error in fidelity
        'use_memory_decay': True,         # Enable memory decoherence
        # 'use_paper2_rewards': True,       # Use Paper2 piecewise reward function
        # 'gate_error_rate': 0.02,          # BSM error rate (from paper)
        # 'swap_mode': 'sync',              # 'sync' or 'async' (paper recommends sync)
        # 'memory_T2': 5000,                # T2 coherence time (frames)
        # 'swap_delay_per_link': 100,       # Delay per hop (frames)
    },
    
    # Paper #7 (Liu et al. 2024 - QBGP)
    'paper7': {
        'k': 5,                      # k-shortest paths per ISP pair
        'n_qisps': 3,                # Number of ISP nodes
        'num_paths': 4,              # Total paths (NOT 8)
        'max_nodes': None,           # Use all 342 nodes from file
        'total_qubits': 35,          # Your framework default
        'network_scale': 'small',
        'min_qubits_per_route': 2,
        'reward_mode': 'neg_hop',    # or 'neg_length', etc.
        'topology_path': '/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/core/topology_data/as20000101.txt',


        # 🆕 NEW: Feature toggles
        'use_context_rewards': True,      # Enable context-aware reward function
        # 'reward_mode': 'neg_hop',         # 'neg_hop', 'neg_degree', 'neg_length', 'custom'
        'use_synthetic': False,           # Force synthetic topology (ignore 
    },
    
    # Paper #12 (Wang et al. 2024 - QuARC)
    'paper12': {
        # Topology
        'n_nodes': 100,              # Vary: 100-800
        'avg_degree': 6,             # Ed (average degree)
        'waxman_beta': 0.2,
        'waxman_alpha': 0.4,
        'topology_type': 'waxman',
        
        # Physical parameters
        'channel_width': 3,          # Links per edge
        'fusion_prob': 0.9,          # q (fusion success)
        'qubits_per_node': 12,       # Memory capacity
        'entanglement_prob': 0.6,    # Ep (average p)
        
        # Simulation parameters
        'num_sd_pairs': 10,          # nsd (concurrent requests)
        'epoch_length': 500,         # Reconfiguration interval
        'total_timeslots': 7000,     # T
        
        # QuARC-specific
        'split_constant': 4,         # k (Girvan-Newman)
        'enable_clustering': True,
        'enable_secondary_fusions': True,
        
        # Framework mapping
        'num_paths': 4,              # For bandit comparison
        'total_qubits': 120,         # 12 qubits/node × 10 nodes (estimated)
        'exploration_bonus': 1.5,    # Lower for clustering
        'min_qubits_per_route': 3,   # Higher for fusion-based
        'use_fusion_rewards': True,

        'time_decay_physics': {'memory_lifetime': 0.5},


        # NEW: Paper12 retry parameters
        'retry_threshold': 0.7,
        'max_retry_attempts': 3,
        'retry_decay_rate': 0.95,
        'enable_retry_logging': True,
        'retry_cost_per_attempt': 0.1,
    }
}

# Calculate frame steps
FRAMEWORK_CONFIG['capacity'] = 10000
# Dynamic configuration based on testing mode
frame_step          = FRAMEWORK_CONFIG['frame_step']
base_seed           = FRAMEWORK_CONFIG['env_attrs']['base_seed']
attack_intensity    = FRAMEWORK_CONFIG['env_attrs']['intensity']
current_frames      = (FRAMEWORK_CONFIG['base_frames'] if FRAMEWORK_CONFIG['test_mode'] else FRAMEWORK_CONFIG['prod_frames'])
current_experiments = (FRAMEWORK_CONFIG['exp_num'] if FRAMEWORK_CONFIG['test_mode'] else FRAMEWORK_CONFIG['prod_experiments'])
for exp_id in range(0, FRAMEWORK_CONFIG['exp_num']): FRAMEWORK_CONFIG['frame_steps'].append(FRAMEWORK_CONFIG['base_frames'] + (FRAMEWORK_CONFIG['frame_step'] * exp_id))



# ============================================================================
# LOOP CONFIGURATION
# ============================================================================
        
# ✅ NEW: Physics models configuration
# PHYSICS_MODELS = ['paper7', 'paper2', 'default', 'paper12']  # ✅ Added paper7
# PHYSICS_MODELS = ['paper2', 'default']  # Set to ['default', 'paper2'] to test both
PHYSICS_MODELS = ['paper2']  # Set to ['default', 'paper2'] to test both
ATTACK_SCENARIOS = ['stochastic']  # Start simple, expand later

# Original configuration
# ALLOCATORS = ['Default', 'Dynamic', 'ThompsonSampling', 'Random']
# ALLOCATORS = ['Default', 'Dynamic', 'ThompsonSampling', 'Random']
ALLOCATORS = ['Default']
RUNS = [1]
SCALES = [1]
# SCALES = [2, 1.5, 1]

# Toggle visualization
VISUALIZE = False

# Additional settings
last_backup = False
overwrite = False
base_cap = False

# ============================================================================
# MODELS & SCENARIOS
# ============================================================================

models = config.NEURAL_MODELS

test_scenarios = {
    'stochastic': 'Stochastic Random Failures',
    'markov': 'Markov Adversarial Attack',
    'adaptive': 'Adaptive Adversarial Attack',
    'onlineadaptive': 'Online Adaptive Attack',
    'none': 'Baseline (Optimal Conditions)'  # For comparison
}

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================
print("=" * 70, "\nDYNAMIC ROUTING EVALUATION FRAMEWORK - CONFIGURATION\n", "=" * 70)
print(f"Models to evaluate: {len(models)} total")
print(f"Primary environment: {FRAMEWORK_CONFIG['main_env'].upper()}")
print(f"Routing strategy: {FRAMEWORK_CONFIG['routing_strategy'].upper()}")
print(f"\nCURRENT SETTINGS ({'TESTING' if FRAMEWORK_CONFIG['test_mode'] else 'PRODUCTION'} MODE):")

print(f"  • Base seed: {base_seed}")
print(f"  • Physics models: {PHYSICS_MODELS}")
print(f"  • Frames per run: {current_frames}")
print(f"  • Attack intensity: {attack_intensity}")
print(f"  • Attack scenarios: {ATTACK_SCENARIOS}")
print(f"  • Experiments per model: {current_experiments}")
print(f"  • Expected runtime: {'~2-3 minutes' if FRAMEWORK_CONFIG['test_mode'] else '~30-45 minutes'}")

# print(f"\nALGORITHM PARAMETERS and ENVIRONMENT PARAMETERS:")
# for key, value in FRAMEWORK_CONFIG['alg_attrs'].items(): print(f"  • {key}: {value}")
# for key, value in FRAMEWORK_CONFIG['env_attrs'].items(): print(f"  • {key}: {value}")

print(f"\nLOOP CONFIGURATION:")
print(f"  • Scales: {SCALES}")
print(f"  • Allocators: {ALLOCATORS}")
print(f"  • Total runs: {len(PHYSICS_MODELS) * len(ATTACK_SCENARIOS) * len(ALLOCATORS) * len(SCALES)}")
print("=" * 70)


# ============================================================================
# VISUALIZATION FUNCTION
# ============================================================================
def run_visualization(evaluator, comparison_results, allocator, custom_config, test_scenarios, models):
    """Run visualization and analysis."""
    importlib.reload(visualizer)
    from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

    print("\n" + "=" * 70)
    print("ROBUSTNESS ANALYSIS")
    print("=" * 70)

    try:
        viz = QuantumEvaluatorVisualizer(comparison_results, allocator=custom_config.allocator, config=custom_config)
        viz.plot_stochastic_vs_adversarial_comparison()
        scenario_list = list(test_scenarios.keys())

        for scenario in scenario_list:
            if scenario.lower() == 'stochastic': continue
            print(f"\n📊 Generating plots for scenario: {scenario.upper()}")
            evaluator.calculate_scenario_performance(scenario=scenario)
            all_scenario_results = evaluator.get_evaluation_results(scenario=scenario)
            viz.plot_scenarios_comparison(scenario=scenario)

        print("\n✓ All scenario plots generated!")
        print("\n✓ Stochastic Analysis Generated:")
        print("  → quantum_mab_models_stochastic_evaluation.png")
        
        stoch_data = viz.get_viz_data('stochastic_data')
        if stoch_data and 'averaged' in stoch_data:
            stoch_results = stoch_data['averaged']
            print("\n" + "=" * 70)
            print("STOCHASTIC PERFORMANCE METRICS")
            print("=" * 70)
            
            oracle_reward = stoch_results.get('oracle_reward', 1)
            winner = stoch_results.get('winner', 'N/A')
            
            for alg in models:
                if alg in stoch_results['results']:
                    model_data  = stoch_results['results'][alg]
                    efficiency  = model_data.get('efficiency', 0)
                    stoch_reward= model_data.get('final_reward', 0)
                    gap         = model_data.get('gap', float('inf'))
                    
                    print(f"\n{alg}:")
                    print(f"  • Stochastic Performance: {stoch_reward:.3f}")
                    print(f"  • Oracle Efficiency: {efficiency:.1f}%")
                    print(f"  • Oracle Gap: {gap:.1f}%")
                    
                    if efficiency > 90:     classification = "EXCELLENT"
                    elif efficiency > 80:   classification = "GOOD"
                    elif efficiency > 70:   classification = "MODERATE"
                    else:                   classification = "NEEDS IMPROVEMENT"
                    
                    print(f"  • Classification: {classification}")
                    if alg == winner: print("  ★ WINNER ★")
            
            print("\n" + "=" * 70)
            print("STOCHASTIC ENVIRONMENT INSIGHTS")
            print("=" * 70)
            print("  • Natural quantum decoherence and network failures")
            print("  • Baseline for future adversarial robustness studies")
            print("  • Performance metrics validate theoretical predictions")

            saved_experiments = viz.save_all_evaluation_results(save_format='both')
        else:   print("⚠ No stochastic averaged results available")
    except Exception as e:
        print(f"❌ Error in robustness analysis: {e}")
        traceback.print_exc()



# ============================================================================
# HELPER FUNCTION: CREATE ALLOCATOR OBJECT
# ============================================================================
def create_allocator(allocator_type, physics_model):
    """Factory function with paper-specific dynamic configuration.
    
    All parameters now pulled from FRAMEWORK_CONFIG to ensure 
    paper-specific defaults are respected.
    """
    # Get paper-specific configuration
    config = FRAMEWORK_CONFIG.get(physics_model, FRAMEWORK_CONFIG['default'])
    
    # Extract common parameters with fallbacks
    num_routes = config['num_paths']  # Required - no fallback
    total_qubits = config.get('total_qubits', 35)
    min_qubits = config.get('min_qubits_per_route', 2)
    exploration = config.get('exploration_bonus', 2.0)
    epsilon = config.get('epsilon', 1.0)
    seed = config.get('seed', 42)
    
    if allocator_type == 'Random':
        return RandomQubitAllocator(total_qubits=total_qubits, num_routes=num_routes, epsilon=epsilon, seed=seed)
    elif allocator_type == 'Dynamic':
        return DynamicQubitAllocator(total_qubits=total_qubits, num_routes=num_routes, min_qubits_per_route=min_qubits, exploration_bonus=exploration)
    elif allocator_type == 'ThompsonSampling':
        return ThompsonSamplingAllocator(total_qubits=total_qubits, num_routes=num_routes, min_qubits_per_route=min_qubits)
    elif allocator_type == 'Default':
        return QubitAllocator(total_qubits=total_qubits, num_routes=num_routes)
    else:
        print(f"⚠️ Unknown allocator type '{allocator_type}', using Default")
        return QubitAllocator(total_qubits=total_qubits, num_routes=num_routes)



# ============================================================================
# PAPER 7 HELPER FUNCTIONS
# ============================================================================
def generate_paper7_paths(topology, k: int, n_qisps: int, seed: int):
    """Generate k-shortest paths between n_qisps ISP nodes."""
    rng = np.random.default_rng(seed)
    nodes = list(topology.nodes())
    
    if len(nodes) < n_qisps: raise ValueError(f"Topology has {len(nodes)} nodes, need {n_qisps} for ISPs")
    isp_nodes = rng.choice(nodes, size=n_qisps, replace=False)
    all_paths = []
    
    for src, dst in itertools.combinations(isp_nodes, 2):
        try:
            path_generator = nx.shortest_simple_paths(topology, src, dst, weight='distance')
            paths = list(itertools.islice(path_generator, k))
            all_paths.extend(paths)
        except nx.NetworkXNoPath: continue
    return all_paths



def generate_paper7_contexts(paths, topology):
    """Generate context vectors for each path (hop_count, avg_degree, path_length)."""
    contexts = []
    for path in paths:
        hop_count = len(path) - 1
        degrees = [topology.degree(node) for node in path]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        
        path_length = 0.0
        for i in range(len(path) - 1):
            edge_data = topology.get_edge_data(path[i], path[i+1])
            path_length += edge_data.get('distance', 1.0)
        
        context_vector = np.array([hop_count, avg_degree, path_length])
        contexts.append([context_vector])  # Wrap in list for compatibility
    return contexts



def get_physics_params_paper12(config, seed, qubit_cap):
    """
    Paper #12 (Waxman + QuARC) physics adapter.

    Returns a structure that is 100% compatible with the existing MAB
    framework and neural bandits:

        - paths:              list of 4 paths (list of node indices)
        - external_contexts:  list of 4 arrays with shapes
                              (8,3), (10,3), (8,3), (9,3)
        - external_rewards:   list of 4 lists with lengths [8,10,8,9]

    Context features per arm (3-D):
        f1: hop count
        f2: normalized average node degree along the path
        f3: fusion success probability (q)

    Rewards per arm are drawn from the QuARC-style success process, so that
    the bandits still see [0,1]-like stochastic rewards.
    """

    # ------------------------------------------------------------------
    # 1) Load / build topology and candidate paths from Waxman file
    # ------------------------------------------------------------------
    # Paper12WaxmanTopologyGenerator().generate()
    # load_waxman_topology should return a NetworkX graph with 'distance'
    # edge attributes (this is how your existing Waxman helpers work).
    topology = Paper12WaxmanTopologyGenerator().generate()

    # Number of candidate paths we will expose to the bandits.
    # This stays 4 to match the rest of the framework.
    num_paths = 4

    # Choose 4 reasonably short paths between random node pairs.
    # This keeps the topology general (50 nodes etc) but exports only 4
    # “arms” to the routing layer, just like paper2/paper7.
    nodes = list(topology.nodes())
    rng = np.random.default_rng(seed)

    paths = []
    attempts = 0
    max_attempts = 10 * num_paths
    while len(paths) < num_paths and attempts < max_attempts:
        attempts += 1
        src, dst = rng.choice(nodes, 2, replace=False)
        try:
            # Shortest path in hop count; you can swap for k‑shortest later.
            path = nx.shortest_path(topology, src, dst)
            # Avoid duplicates (same sequence of nodes).
            if path not in paths: paths.append(path)
        except nx.NetworkXNoPath: continue
    if len(paths) < num_paths: raise RuntimeError(f"Could not find {num_paths} valid paths in Waxman topology.")

    # ------------------------------------------------------------------
    # 2) Build physics models (Paper12: fusion routing + QuARC reward)
    # ------------------------------------------------------------------
    fusion_prob = float(config.get("fusion_prob", 0.9))
    entanglement_prob = float(config.get("entanglement_prob", 0.6))
    noise_model = FusionNoiseModel(topology=topology, paths=paths, fusion_prob=fusion_prob, entanglement_prob=entanglement_prob)
    fidelity_calc = FusionFidelityCalculator()
    reward_func = QuARCRewardFunction()

    # ------------------------------------------------------------------
    # 3) Build contexts: list of 4 arrays (K_i x 3)
    #     K = [8, 10, 8, 9] — same as qubit caps in the rest of the code
    # ------------------------------------------------------------------
    external_contexts = []
    arms_per_path = [8, 10, 8, 9]  # DO NOT CHANGE: framework assumption

    # Pre-compute a simple normalization for average node degree
    degrees = dict(topology.degree())
    max_degree = max(degrees.values()) if degrees else 1.0

    for p_idx, K in enumerate(arms_per_path):
        path = paths[p_idx]
        hop_count = len(path) - 1

        # Feature 1: hop count (raw)
        f1_hops = float(hop_count)

        # Feature 2: normalized average node degree along the path
        path_degrees = [degrees[n] for n in path]
        avg_degree = float(sum(path_degrees) / len(path_degrees))
        f2_deg_norm = avg_degree / max_degree if max_degree > 0 else 0.0

        # Feature 3: fusion success probability q
        f3_fusion = fusion_prob

        # Tile same 3D context across all K allocations for compatibility.
        ctx = np.full((K, 3), [f1_hops, f2_deg_norm, f3_fusion], dtype=float)
        external_contexts.append(ctx)

    # ------------------------------------------------------------------
    # 4) Build rewards: list of 4 lists, lengths [8,10,8,9]
    #     Use QuARC-style “success” process as Bernoulli rewards
    # ------------------------------------------------------------------
    external_rewards = []

    # Success factor / scaling is not needed for fusion; the reward is
    # simply success ∈ {0,1}. If you want a slightly smoother bandit
    # landscape, you can call fidelity_calc and use that as success prob.
    for p_idx, K in enumerate(arms_per_path):
        path = paths[p_idx]
        # Get per-hop error structure for this path
        err_info = noise_model.get_error_rates(p_idx)
        # Compute a single “base success probability” for the path
        base_fidelity = fidelity_calc.compute_path_fidelity(err_info, context=None, fusion_prob=fusion_prob)
        # Clip to [0,1] just in case
        base_fidelity = float(np.clip(base_fidelity, 0.0, 1.0))

        # Draw K Bernoulli rewards for this path
        path_rewards = []
        for _ in range(K):
            success = rng.random() < base_fidelity
            r = reward_func.compute_reward(success=success, aggregate_throughput=1)
            path_rewards.append(float(r))

        external_rewards.append(path_rewards)

    # ------------------------------------------------------------------
    # 5) Return structure EXACTLY as required by the rest of the framework
    # ------------------------------------------------------------------
    return {
        "external_topology": topology, "external_contexts": external_contexts, "external_rewards": external_rewards,
        "noise_model": noise_model, "fidelity_calculator": fidelity_calc,
        # "reward_function": reward_func,
    }



def get_physics_params(
    physics_model: str = "default",
    current_frames: int = 4000,
    base_seed: int = 42,
    qubit_cap=None,
    *,
    topology: "nx.Graph | None" = None,
    topology_model: str | None = None,
    topology_path: str | Path | None = None,
    topology_max_nodes: int | None = None,
    topology_largest_cc_only: bool = True,
    topology_relabel_to_int: bool = True,
    synthetic_kind: str = "barabasi_albert",
    synthetic_params: dict | None = None,
):
    """
    Returns kwargs for set_environment(): noise_model, fidelity_calculator, external_topology,
    external_contexts, external_rewards.
    """

    # === PAPER7 HANDLING (Top Level) ===
    if physics_model == "paper7":
        paper7_cfg = FRAMEWORK_CONFIG['paper7_physics']
        node_num = paper7_cfg.get('max_nodes')
        
        # Topology
        if topology is not None: final_topology = topology
        else:
            if paper7_cfg.get('use_synthetic', False) or not paper7_cfg.get('topology_path'):
                # Synthetic topology
                topo_gen = Paper7ASTopologyGenerator(
                    edge_list_path="dummy_nonexistent.txt",
                    max_nodes=topology_max_nodes or node_num,
                    seed=base_seed,
                    synthetic_fallback=True,
                    synthetic_kind="barabasi_albert",
                    synthetic_params={"n": node_num or 100, "m": 3}
                )
                print(f"📊 Paper7 Topology: Synthetic (Barabási-Albert, n={node_num or 100})")
            else:
                # Real AS topology
                topo_gen = Paper7ASTopologyGenerator(
                    edge_list_path=paper7_cfg['topology_path'],
                    max_nodes=node_num,
                    seed=base_seed,
                    relabel_to_integers=topology_relabel_to_int,
                    largest_cc_only=topology_largest_cc_only,
                    synthetic_fallback=True
                )
                print(f"📊 Paper7 Topology: Real AS ({paper7_cfg['topology_path']})")
            final_topology = topo_gen.generate()
        
        # K-shortest paths
        k = paper7_cfg["k"]
        n_qisps = paper7_cfg["n_qisps"]
        paths = generate_paper7_paths(final_topology, k, n_qisps, base_seed)
        
        # Contexts
        contexts = generate_paper7_contexts(paths, final_topology)
        print(f"📊 Paper7 Paths: {len(paths)} paths from {k}-shortest between {n_qisps} ISPs")
        
        # 🆕 CONDITIONAL: Context-aware rewards
        external_rewards = None
        if paper7_cfg.get('use_context_rewards', False):
            reward_mode = paper7_cfg.get('reward_mode', 'neg_hop')
            reward_func = Paper7RewardFunction(mode=reward_mode)
            external_rewards = []
            
            for ctx_list in contexts:
                # Each path has one context vector per allocation
                path_rewards = [reward_func.compute(ctx) for ctx in ctx_list]
                external_rewards.append(path_rewards)
            
            print(f"📊 Paper7 Rewards: Context-aware (mode={reward_mode})")
        else: print(f"📊 Paper7 Rewards: Using default framework rewards")
        
        return {
            "noise_model": None,
            "fidelity_calculator": None,
            "external_topology": final_topology,
            "external_contexts": contexts,
            "external_rewards": external_rewards
        }

    elif physics_model == "paper2":
        # Load Paper2 config
        p2_config = FRAMEWORK_CONFIG["paper2"]
        # Topology resolution
        if topology is not None: topo = topology
        elif topology_model == "paper2":
            topo_gen = Paper2TopologyGenerator(num_nodes=p2_config["num_nodes"], seed=base_seed)
            topo = topo_gen.generate()
        else:
            topo_gen = Paper2TopologyGenerator(num_nodes=p2_config["num_nodes"], seed=base_seed)
            topo = topo_gen.generate()
        
        # Path generation
        try:
            path_generator = nx.shortest_simple_paths(topo, p2_config["source_node"], p2_config["dest_node"], weight="distance")
            paths = list(itertools.islice(path_generator, p2_config["num_paths"]))
        except nx.NetworkXNoPath: paths = [[p2_config["source_node"], p2_config["dest_node"]]] * p2_config["num_paths"]
        
        # Physics objects
        noise_model = FiberLossNoiseModel(topology=topo, paths=paths, p_init=p2_config["p_init"], f_attenuation=p2_config["f_attenuation"])
        fidelity_calc = CascadedFidelityCalculator()

        # noise_model = FiberLossNoiseModel(
        #     topology=topo,
        #     paths=paths,
        #     p_init=p2_config["p_init"],
        #     f_attenuation=p2_config["f_attenuation"]
        # )

        # memory_model = MemoryNoiseModel(
        #     T2=p2_config.get("memory_T2", 5000),
        #     swap_delay_per_link=p2_config.get("swap_delay_per_link", 100)
        # )

        # fidelity_calc = FullPaper2FidelityCalculator(
        #     noise_model=noise_model,
        #     gate_error_rate=p2_config.get("gate_error_rate", 0.02),
        #     memory_model=memory_model if p2_config.get("swap_mode", "sync") == "async" else None
        # )

        
        # Contexts
        contexts = []
        for path in paths:
            hop_count = len(path) - 1
            contexts.append([np.array([3] * hop_count)])
        return {"noise_model": noise_model, "fidelity_calculator": fidelity_calc, "external_topology": topo, "external_contexts": contexts, "external_rewards": None}

    elif physics_model == 'paper12':
        p12config = FRAMEWORK_CONFIG['paper12']

        decaycfg = p12config['time_decay_physics']
        memlifetime = decaycfg['memory_lifetime']
        # Get Paper12 physics
        physics_params = get_physics_params_paper12(FRAMEWORK_CONFIG['paper12'], seed=base_seed, qubit_cap=qubit_cap)
        base_fidelity_calc = physics_params['fidelity_calculator']
        topology = physics_params['external_topology']
        contexts = physics_params['external_contexts']
        rewards = physics_params['external_rewards']
        noise_model = physics_params['noise_model']
        num_paths = len(contexts)
        print(f"Paper12 (QuARC) physics: {num_paths} paths, fusion_prob={FRAMEWORK_CONFIG['paper12']['fusion_prob']}")

        # # NEW: Wrap with retry logic
        # fidelitycalc = Paper12RetryFidelityCalculator(
        #     base_calculator=base_fidelity_calc,
        #     threshold=p12config['retry_threshold'],
        #     max_attempts=p12config['max_retry_attempts'],
        #     decay_rate=p12config['retry_decay_rate']
        # )

        # Wrap with retry logic
        fidelitycalc = Paper12RetryFidelityCalculator(
            base_calculator=base_fidelity_calc,
            threshold=p12config['retry_threshold'],
            max_attempts=p12config['max_retry_attempts'],
            decay_rate=p12config['retry_decay_rate']
        )
        
        # 🆕 NEW: Create metadata dict
        metadata = {
            'paper': 'Zhang2023Paper12',
            'retry_enabled': True,
            'retry_threshold': p12config['retry_threshold'],
            'max_attempts': p12config['max_retry_attempts'],
            'decay_rate': p12config['retry_decay_rate'],
        }

        physics_params['metadata'] = metadata,  # 🆕 NEW: Safe - handled by __init__

        return physics_params
    # === DEFAULT ===
    else: return {"noise_model": None, "fidelity_calculator": None, "external_topology": topology, "external_contexts": None, "external_rewards": None}


def force_release_resources(evaluator=None, verbose=True):
    """
    Nuclear option: Force release of ALL resources that could block.
    Call this AFTER each allocator completes.
    """
    cleanup_log = []

    # 1. Stop logging and close file handles
    if evaluator is not None:
        try:
            # Stop logging redirect
            if hasattr(evaluator, 'configs') and hasattr(evaluator.configs, 'backup_mgr'):
                backup_mgr = evaluator.configs.backup_mgr

                # Close log files explicitly
                if hasattr(backup_mgr, 'stop_logging_redirect'):
                    backup_mgr.stop_logging_redirect()

                # Force close any open file handles
                if hasattr(backup_mgr, '_log_file'):
                    try:
                        backup_mgr._log_file.close()
                    except:
                        pass

                # Clear backup registry references
                if hasattr(backup_mgr, 'backup_registry'):
                    backup_mgr.backup_registry.clear()

                cleanup_log.append("✅ Backup manager cleaned")
        except Exception as e:
            cleanup_log.append(f"⚠️ Backup cleanup warning: {e}")

    # 2. Clear environment graphs (NetworkX holds tons of memory)
    if evaluator is not None:
        try:
            if hasattr(evaluator, 'configs') and hasattr(evaluator.configs, 'environment'):
                env = evaluator.configs.environment

                # Clear topology graphs
                if hasattr(env, 'topology'):
                    if hasattr(env.topology, 'clear'):
                        env.topology.clear()
                    del env.topology

                # Clear any cached paths
                if hasattr(env, 'paths'):
                    env.paths = []

                cleanup_log.append("✅ Environment graphs cleared")
        except Exception as e:
            cleanup_log.append(f"⚠️ Environment cleanup warning: {e}")

    # 3. Break circular references
    if evaluator is not None:
        try:
            # Break evaluator ↔ configs ↔ backup_mgr cycle
            if hasattr(evaluator, 'configs'):
                if hasattr(evaluator.configs, 'backup_mgr'):
                    evaluator.configs.backup_mgr = None
                if hasattr(evaluator.configs, 'environment'):
                    evaluator.configs.environment = None
                evaluator.configs = None

            cleanup_log.append("✅ Circular references broken")
        except Exception as e:
            cleanup_log.append(f"⚠️ Reference cleanup warning: {e}")

    # 4. Clear model registries (if they exist)
    try:
        # Try to clear any global model registries
        import sys
        modules_to_check = [m for m in sys.modules if 'bandit' in m.lower() or 'neural' in m.lower()]

        for mod_name in modules_to_check:
            mod = sys.modules[mod_name]
            if hasattr(mod, '_model_registry'):
                mod._model_registry.clear()
            if hasattr(mod, '_global_models'):
                mod._global_models.clear()

        cleanup_log.append("✅ Model registries cleared")
    except Exception as e:
        cleanup_log.append(f"⚠️ Registry cleanup warning: {e}")

    # 5. Torch cleanup
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        # Clear torch internal caches
        if hasattr(torch, '_C') and hasattr(torch._C, '_cuda_clearCublasWorkspaces'):
            torch._C._cuda_clearCublasWorkspaces()

        cleanup_log.append("✅ Torch CUDA cleared")
    except Exception as e:
        cleanup_log.append(f"⚠️ Torch cleanup warning: {e}")

    # 6. Aggressive garbage collection (3 passes)
    collected = []
    for i in range(3):
        n = gc.collect()
        collected.append(n)

    cleanup_log.append(f"✅ GC collected: {collected}")

    # 7. Close any lingering file descriptors
    try:
        import os
        import psutil

        process = psutil.Process()
        open_files = process.open_files()

        for f in open_files:
            if '.pkl' in f.path or '.log' in f.path or '.csv' in f.path:
                try:
                    # Try to close by fd
                    os.close(f.fd)
                    cleanup_log.append(f"✅ Closed: {f.path}")
                except:
                    pass
    except Exception as e:
        cleanup_log.append(f"⚠️ File descriptor cleanup: {e}")

    # 8. Force delete evaluator
    if evaluator is not None:
        del evaluator

    # 9. Final aggressive collection
    gc.collect(2)  # Full collection

    if verbose:
        print("\n" + "="*70)
        print("🧹 FORCED RESOURCE RELEASE")
        print("="*70)
        for log in cleanup_log:
            print(log)
        print("="*70 + "\n")

    return True




# ============================================================================
# MAIN AUTOMATION LOOP
# ============================================================================
# ✅ UPDATED: Calculate total runs with physics models
run_count = 0
total_runs = len(PHYSICS_MODELS) * len(ALLOCATORS) * len(SCALES)

allocator_obj = None

for allocator_idx, allocator_type in enumerate(ALLOCATORS):
    print("\n" + "="*70)
    print(f"ALLOCATOR {allocator_idx + 1}/{len(ALLOCATORS)}: {allocator_type}")
    print("="*70)

    for physics_model in PHYSICS_MODELS:
        print("=" * 70)
        print("QUANTUM MAB MODELS EVALUATION FRAMEWORK")
        print("=" * 70)
        try:
            # Create allocator
            allocator_obj = create_allocator(allocator_type, physics_model)
            print(f"✅ Created: {allocator_obj.__class__.__name__}")

            # Get initial allocation
            qubit_cap = allocator_obj.allocate(timestep=0, route_stats={}, verbose=False)

            # Get physics params
            physics_params = get_physics_params(
                physics_model,
                FRAMEWORK_CONFIG[physics_model],
                base_seed=base_seed,
                qubit_cap=qubit_cap
            )

            # Create config
            custom_config = ExperimentConfiguration(
                runs=current_experiments,
                allocator=allocator_obj,
                scenarios=test_scenarios,
                use_last_backup=last_backup,
                physics_params=physics_params,
                attack_intensity=attack_intensity,
                base_capacity=base_cap,
                overwrite=overwrite,
                models=models,
                scale=0,
                suffix=physics_model
            )

            # Run experiments
            for scale in SCALES:
                custom_config.scale = scale

                for run_count in RUNS:
                    evaluator = None  # Initialize to None

                    try:
                        print(f"\nScale: {scale}, Runs: {run_count}")

                        # Create evaluator
                        evaluator = MultiRunEvaluator(
                            configs=custom_config,
                            base_frames=current_frames,
                            frame_step=frame_step
                        )

                        evaluator.configs.set_log_name(
                            base_frames=current_frames,
                            frame_step=frame_step
                        )

                        evaluator.configs.backup_mgr.init_logging_redirect(evaluator)

                        # Run evaluation
                        print("Running evaluation...")
                        comparison_results = evaluator.test_stochastic_environment(
                            # calc_winner=True,
                            # parellel=False
                        )

                        evaluator.calculate_scenarios_performance()
                        print(f"✅ Evaluation completed!")

                    except Exception as e:
                        print(f"❌ Error in evaluation: {e}")
                        import traceback
                        traceback.print_exc()

                    finally:
                        # Critical cleanup section
                        print("\n🧹 Starting cleanup...")

                        # Load results if evaluator exists
                        if evaluator is not None:
                            try:
                                evaluator.configs.backup_mgr.load_new_entries()
                                evaluator.configs.backup_mgr.stop_logging_redirect()
                            except Exception as e:
                                print(f"⚠️ Backup finalization warning: {e}")

                        # ⚠️ THIS IS THE KEY FIX ⚠️
                        # Force release ALL resources
                        force_release_resources(evaluator, verbose=True)

                        # Explicit delete
                        evaluator = None

                        # Extra sleep to let OS release handles
                        import time
                        time.sleep(2)

                        print("✅ Cleanup complete\n")

            print(f"\n✅ Completed all runs for {allocator_type}")

        except Exception as e:
            print(f"❌ Fatal error in {allocator_type}: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Force cleanup even if allocator failed
            print(f"\n🧹 Final cleanup for {allocator_type}...")
            force_release_resources(None, verbose=False)
            gc.collect()
        

# ✅ UPDATED: Add physics model and attack scenario loops
for allocator_type in ALLOCATORS:
    deep_cleanup()

    for physics_model in PHYSICS_MODELS:
        print("=" * 70)
        print("QUANTUM MAB MODELS EVALUATION FRAMEWORK")
        print("=" * 70)

        # Create allocator
        # 1. Create allocator (dynamic num_paths for Paper #2)
        num_paths = FRAMEWORK_CONFIG[physics_model]["num_paths"]
        if physics_model != "default": 
            allocator_obj = create_allocator(allocator_type, physics_model)
            print(f"✓ Created allocator: {type(allocator_obj).__name__} ({num_paths} paths)")

        # print(f"Physics: {physics_model} | Attack: {attack_scenario}")  # ✅ NEW
        # print(f"Allocator: {allocator_type} | CapType: {cap_type} | Scale: {scale}")

        # 2. Get physics params
        qubit_cap = allocator_obj.allocate(timestep=0, route_stats={}, verbose=False)
        physics_params = get_physics_params(physics_model=physics_model, current_frames=current_frames, base_seed=base_seed, qubit_cap=qubit_cap)

            # 3. Create config
        custom_config = ExperimentConfiguration(
            runs=current_experiments, allocator=allocator_obj, scenarios=test_scenarios, 
            use_last_backup=last_backup, physics_params=physics_params, attack_intensity=attack_intensity,
            base_capacity=base_cap, overwrite=overwrite, models=models, scale=0, suffix=physics_model.replace("default", "")
        )

        for scale in SCALES:
            custom_config.scale = scale
            for current_experiments in RUNS:
                
                run_count += 1
                print("\n" + "=" * 70)
                print(f"RUN {run_count}/{total_runs}")

                # 4. ✅ CALL YOUR EXTENDED set_environment() WITH PHYSICS
                print(FRAMEWORK_CONFIG[physics_model])  # Should return Paper2_UCB_2023 params
                evaluator = MultiRunEvaluator(configs=custom_config, base_frames=current_frames, frame_step=frame_step)
                evaluator.configs.set_log_name(base_frames=current_frames, frame_step=frame_step)
                evaluator.configs.backup_mgr.init_logging_redirect(evaluator)

                # Execute evaluation
                try:
                    print("\n⚙ Running Quantum MAB Models Evaluation...")
                    comparison_results = evaluator.test_stochastic_environment(cal_winner=True, parellel=False)
                    evaluator.calculate_scenarios_performance()
                    print(f"\n✓ Quantum MAB Models Evaluation completed!")
                except Exception as e:
                    print(f"\n❌ Evaluation error: {e}")
                    traceback.print_exc()
                finally:
                    evaluator.configs.backup_mgr.load_new_entries()
                    evaluator.configs.backup_mgr.stop_logging_redirect()

                # Run visualization if enabled
                if VISUALIZE: run_visualization(evaluator, comparison_results, allocator_type, custom_config, test_scenarios, models)
                else: print("\n⊘ Visualization skipped (VISUALIZE=False)")
                print(f"\n✅ Completed {run_count}/{total_runs}")

print("\n" + "=" * 70)
print("ALL RUNS COMPLETE!")
print("=" * 70)