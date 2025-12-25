"""
Automated Runner - Loops through all allocators, capacity types, and scales
"""

import os
import sys
import gc
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

result = subprocess.run(
    ["python3", cleanup_script],
    text=True,
    capture_output=True
)

print("===== CLEANUP STDOUT =====")
print(result.stdout)
print("===== CLEANUP STDERR =====")
print(result.stderr)
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
    if PARENT_DIR not in sys.path:
        sys.path.insert(0, PARENT_DIR)

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
               base_bandit, neural_bandits, predictive_bandits, 
               experiment_runner, multi_run_evaluator, visualizer]:
    importlib.reload(module)

# Import classes after reload
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.multi_run_evaluator import *
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer
from daqr.core.qubit_allocator import (
    QubitAllocator, 
    RandomQubitAllocator, 
    DynamicQubitAllocator, 
    ThompsonSamplingAllocator
)

from daqr.core.quantum_physics import FusionNoiseModel
from daqr.core.topology_generator import Paper2TopologyGenerator
from daqr.core.topology_generator import Paper7ASTopologyGenerator
from daqr.core.topology_generator import Paper12WaxmanTopologyGenerator
from daqr.core.quantum_physics import FiberLossNoiseModel, CascadedFidelityCalculator
from daqr.core.quantum_physics import FusionNoiseModel, FusionFidelityCalculator, QuARCRewardFunction
print("✓ All modules reloaded successfully (fresh environment ready)")

# ============================================================================
# CONFIGURATION - FROM YOUR FRAMEWORK_CONFIG
# ============================================================================

# Initialize base config to get model lists
config = ExperimentConfiguration()

# ✅ UPDATED: Fixed syntax and added Paper #2 config
FRAMEWORK_CONFIG = {
    # Testing Configuration
    'test_mode': True,
    'base_frames': 100,
    'exp_num': 1,
    'frame_step': 100,
    
    # Production Configuration
    'prod_frames': 4000,
    'prod_experiments': 10,
    'frame_steps': [],
    
    # Primary evaluation focus
    'main_env': 'stochastic',
    'eval_mod': 'comprehensive',
    'main_model': 'CEXPNeuralUCB',
    
    # Routing strategy configuration
    'routing_strategy': 'fixed',
    'enable_routing_comparison': False,
    
    # Algorithm parameters (EXPNeuralUCB paper-compliant)
    'alg_attrs': {
        'lambda_reg': 1.0,
        'gamma': 0.1,
        'network_width': 128,
        'network_depth': 2,
        'gradient_steps': 8,
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
    },  # ✅ FIXED: Added missing comma

    # ✅ NEW: Paper #2 physics configuration
    'paper2_physics': {
        'num_nodes': 15,
        'num_paths': 8,
        'source_node': 1,
        'dest_node': 14,
        'p_init': 0.00001,
        'f_attenuation': 0.05,
        'use_paper2_rewards': True
    },

    'paper7_physics': {
        'k': 5,
        'n_qisps': 3,
        'network_scale': 'small',  # Not used if max_nodes is set
        'max_nodes': None,  # ✅ Use all 342 nodes from file
        'topology_path': '/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/core/topology_data/as20000101.txt'
    },
    # 'paper7_physics': {
    #     'k': 5,
    #     'n_qisps': 3,
    #     'network_scale': 'large',
    #     'max_nodes': 1000,              # ✅ Generate 1000-node synthetic
    #     'topology_path': None,          # ✅ Force synthetic
    #     'use_synthetic': True,          # ✅ Explicit flag
    #     'synthetic_params': {           # ✅ Optional: customize
    #         'n': 1000,                  # Number of nodes
    #         'm': 3                      # Edges per new node (connectivity)
    #     }
    # },
    'paper12_quarc': {
        # Paper: Wang et al. "Efficient Routing on Quantum Networks using 
        #        Adaptive Clustering" (ICNP 2024)
        # Topology
        'topology_type': 'waxman',
        'n_nodes': 100,              # Network size (vary: 100-800)
        'avg_degree': 6,             # Ed (average degree)
        'waxman_alpha': 0.4,         # Link probability scaling
        'waxman_beta': 0.2,          # Distance decay factor
        
        # Physical parameters
        'entanglement_prob': 0.6,    # Ep (average p)
        'fusion_prob': 0.9,          # q (fusion success)
        'qubits_per_node': 12,       # Memory capacity (varies by node degree)
        'channel_width': 3,          # Links per edge
        
        # Simulation parameters
        'total_timeslots': 7000,     # T
        'num_sd_pairs': 10,          # nsd (concurrent requests)
        'epoch_length': 500,         # Reconfiguration interval
        'request_cutoff': 10**9,     # Timeout (effectively infinite)
        
        # QuARC-specific
        'enable_clustering': True,   # Adaptive clustering
        'split_constant': 4,         # k (Girvan-Newman)
        'threshold_type': '2d_grid', # or 'topology_specific'
        'enable_secondary_fusions': True,
        
        # Framework mapping
        'num_paths': 8,              # For bandit comparison (not used by QuARC)
        'use_fusion_rewards': True,  # Use QuARCRewardFunction
    }
}

# Calculate frame steps
for exp_id in range(0, FRAMEWORK_CONFIG['exp_num']):
    FRAMEWORK_CONFIG['frame_steps'].append(
        FRAMEWORK_CONFIG['base_frames'] + (FRAMEWORK_CONFIG['frame_step'] * exp_id)
    )
FRAMEWORK_CONFIG['capacity'] = 10000

# Dynamic configuration based on testing mode
attack_intensity = FRAMEWORK_CONFIG['env_attrs']['intensity']
frame_step = FRAMEWORK_CONFIG['frame_step']
current_frames = (FRAMEWORK_CONFIG['base_frames'] if FRAMEWORK_CONFIG['test_mode'] 
                  else FRAMEWORK_CONFIG['prod_frames'])
current_experiments = (FRAMEWORK_CONFIG['exp_num'] if FRAMEWORK_CONFIG['test_mode'] 
                       else FRAMEWORK_CONFIG['prod_experiments'])
base_seed = FRAMEWORK_CONFIG['env_attrs']['base_seed']

# ============================================================================
# LOOP CONFIGURATION
# ============================================================================
        
# ✅ NEW: Physics models configuration
# PHYSICS_MODELS = ['paper7', 'paper2', 'default', 'paper12_quarc']  # ✅ Added paper7
# PHYSICS_MODELS = ['paper2', 'default']  # Set to ['default', 'paper2'] to test both
PHYSICS_MODELS = ['paper12_quarc']  # Set to ['default', 'paper2'] to test both
ATTACK_SCENARIOS = ['stochastic']  # Start simple, expand later

# Original configuration
# ALLOCATORS = ['Default', 'Dynamic', 'ThompsonSampling', 'Random']
ALLOCATORS = ['Default']
# CAPACITY_TYPES = ['T', 'Tb']
CAPACITY_TYPES = ['T']
# RUNS = [10]
# RUNS = [5]
RUNS = [1]
# SCALES = [1, 1.5, 2]
SCALES = [2]

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

print("=" * 70)
print("DYNAMIC ROUTING EVALUATION FRAMEWORK - CONFIGURATION")
print("=" * 70)
print(f"Models to evaluate: {len(models)} total")
print(f"Primary environment: {FRAMEWORK_CONFIG['main_env'].upper()}")
print(f"Routing strategy: {FRAMEWORK_CONFIG['routing_strategy'].upper()}")

print(f"\nCURRENT SETTINGS ({'TESTING' if FRAMEWORK_CONFIG['test_mode'] else 'PRODUCTION'} MODE):")
print(f"  • Frames per run: {current_frames}")
print(f"  • Experiments per model: {current_experiments}")
print(f"  • Attack intensity: {attack_intensity}")
print(f"  • Base seed: {base_seed}")
print(f"  • Physics models: {PHYSICS_MODELS}")  # ✅ NEW
print(f"  • Attack scenarios: {ATTACK_SCENARIOS}")  # ✅ NEW
print(f"  • Expected runtime: {'~2-3 minutes' if FRAMEWORK_CONFIG['test_mode'] else '~30-45 minutes'}")

print(f"\nALGORITHM PARAMETERS:")
for key, value in FRAMEWORK_CONFIG['alg_attrs'].items():
    print(f"  • {key}: {value}")

print(f"\nENVIRONMENT PARAMETERS:")
for key, value in FRAMEWORK_CONFIG['env_attrs'].items():
    print(f"  • {key}: {value}")

print(f"\nLOOP CONFIGURATION:")
print(f"  • Allocators: {ALLOCATORS}")
print(f"  • Scales: {SCALES}")
print(f"  • Total runs: {len(PHYSICS_MODELS) * len(ATTACK_SCENARIOS) * len(ALLOCATORS) * len(CAPACITY_TYPES) * len(SCALES)}")

print("=" * 70)

# ============================================================================
# UNIFIED ENVIRONMENT BUILDER
# ============================================================================

def build_environment(allocator_obj, 
                     physics_model='default',
                     attack_scenario='stochastic',
                     attack_intensity=0.25,
                     current_frames=4000,
                     base_seed=42):
    """
    Unified quantum environment builder.
    
    Args:
        allocator_obj: Allocator instance
        physics_model: 'default' or 'paper2'
        attack_scenario: 'none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive'
        attack_intensity: Base attack rate (0-1)
        current_frames: Frame length for environment
        base_seed: Random seed
    
    Returns:
        QuantumEnvironment configured with specified physics and attack
    """
    from daqr.core.network_environment import QuantumEnvironment
    from daqr.core.attack_strategy import create_attack_strategy, RandomAttack
    
    # ========================================================================
    # STEP 1: Configure Physics Model
    # ========================================================================
    
    if physics_model == 'paper2':
        # Import Paper #2 quantum objects
        from daqr.core.quantum_physics import (FiberLossNoiseModel, CascadedFidelityCalculator, Paper2RewardFunction)
        from daqr.core.topology_generator import Paper2TopologyGenerator
        
        p2_config = FRAMEWORK_CONFIG['paper2_physics']
        
        # Generate topology
        topo_gen = Paper2TopologyGenerator(num_nodes=p2_config['num_nodes'], seed=base_seed)
        topology = topo_gen.generate()
        
        # Find paths
        try:
            paths = list(nx.shortest_simple_paths(
                topology, 
                p2_config['source_node'], 
                p2_config['dest_node'], 
                weight='distance'
            ))[:p2_config['num_paths']]
        except nx.NetworkXNoPath:
            print("⚠️ No path found, using dummy paths")
            paths = [[p2_config['source_node'], p2_config['dest_node']]] * p2_config['num_paths']
        
        # Build quantum objects
        noise_model = FiberLossNoiseModel(
            topology=topology,
            paths=paths,
            p_init=p2_config['p_init'],
            f_attenuation=p2_config['f_attenuation']
        )
        fidelity_calc = CascadedFidelityCalculator()
        
        # Contexts (hop-based)
        contexts = []
        for path in paths:
            hop_count = len(path) - 1
            contexts.append([np.array([3] * hop_count)])
        
        # Rewards
        rewards = []
        if p2_config['use_paper2_rewards']: reward_func = Paper2RewardFunction()
        
        for path_idx in range(len(paths)):
            error_rates = noise_model.get_error_rates(path_idx)
            fidelity = fidelity_calc.compute_path_fidelity(
                error_rates=error_rates,
                context=contexts[path_idx][0],
                success_factor=100
            )
            if p2_config['use_paper2_rewards']: reward = reward_func.compute_reward(fidelity)
            else:                               reward = fidelity
            rewards.append([reward])
        
        # Environment params
        num_paths = len(paths)
        external_rewards = rewards
        external_contexts = contexts
        external_topology = topology
        print(f"✓ Paper #2 physics: {num_paths} paths, {topology.number_of_nodes()} nodes")
    
    elif physics_model == 'default':
        # Use framework's hardcoded physics (backward compatible)
        noise_model = None
        fidelity_calc = None
        external_rewards = None
        external_contexts = None
        external_topology = None
        num_paths = 4  # Framework default
        paths = None
        
        print(f"✓ Default framework physics: 4 paths")
    else:   raise ValueError(f"Unknown physics_model: {physics_model}")
    
    # ========================================================================
    # STEP 2: Configure Attack Strategy
    # ========================================================================
    
    if attack_scenario.lower() == 'stochastic' and physics_model == 'paper2' and paths:
        # Special case: Paper #2 stochastic uses path-dependent noise
        attack_rates = [attack_intensity + (len(p)-2) * 0.05 for p in paths]
        attack = RandomAttack(per_path_rates=attack_rates)
        print(f"✓ Path-dependent stochastic attack: {[f'{r:.2f}' for r in attack_rates]}")
    else:
        # Use factory for all other scenarios
        attack = create_attack_strategy(attack_scenario, attack_rate=attack_intensity)
        print(f"✓ Attack scenario: {attack_scenario}")
    
    # ========================================================================
    # STEP 3: Build Environment
    # ========================================================================
    
    env = QuantumEnvironment(
        attack=attack,
        allocator=allocator_obj,
        noise_model=noise_model,
        fidelity_calculator=fidelity_calc,
        external_topology=external_topology,
        external_contexts=external_contexts,
        external_rewards=external_rewards,
        frame_length=current_frames,
        num_paths=num_paths,
        seed=base_seed
    )
    return env

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
        viz = QuantumEvaluatorVisualizer(comparison_results, allocator=allocator, config=custom_config)
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
                    model_data = stoch_results['results'][alg]
                    
                    stoch_reward = model_data.get('final_reward', 0)
                    efficiency = model_data.get('efficiency', 0)
                    gap = model_data.get('gap', float('inf'))
                    
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
            print("  • Performance metrics validate theoretical predictions")
            print("  • Baseline for future adversarial robustness studies")
        else:   print("⚠ No stochastic averaged results available")
    except Exception as e:
        print(f"❌ Error in robustness analysis: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# HELPER FUNCTION: CREATE ALLOCATOR OBJECT
# ============================================================================

def create_allocator(allocator_type, num_paths=4):
    """Factory function with dynamic path count."""
    if allocator_type == 'Random':
        return RandomQubitAllocator(
            total_qubits=35,
            num_routes=num_paths,  # ✅ Dynamic
            epsilon=1.0,
            seed=42
        )
    elif allocator_type == 'Dynamic':
        return DynamicQubitAllocator(
            total_qubits=35,
            num_routes=4,
            min_qubits_per_route=2,
            exploration_bonus=2.0
        )
    elif allocator_type == 'ThompsonSampling':
        return ThompsonSamplingAllocator(
            total_qubits=35,
            num_routes=4,
            min_qubits_per_route=2
        )
    elif allocator_type == 'Default':
        return QubitAllocator(
            total_qubits=35,
            num_routes=4
        )
    else:
        print(f"⚠️ Unknown allocator type '{allocator_type}', using Default")
        return QubitAllocator(total_qubits=35, num_routes=4)

# ============================================================================
# PAPER 7 HELPER FUNCTIONS
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
    import numpy as np
    import networkx as nx

    rng = np.random.default_rng(seed)

    topology = Paper12WaxmanTopologyGenerator().generate()

    num_paths      = int(config.get("num_paths", 4))
    arms_per_path  = int(config.get("arms_per_path", 1))  # set 1 for pure path-select, >1 for CMAB
    noise_std      = float(config.get("context_noise_std", 0.01))
    fusion_prob    = float(config.get("fusion_prob", 0.9))
    ent_prob       = float(config.get("entanglement_prob", 0.6))

    nodes = list(topology.nodes())

    # --- generate paths ---
    paths = []
    max_attempts = max(50, 20 * num_paths)
    attempts = 0
    while len(paths) < num_paths and attempts < max_attempts:
        attempts += 1
        src, dst = rng.choice(nodes, 2, replace=False)
        try:
            p = nx.shortest_path(topology, src, dst, weight=config.get("path_weight", None))
            if p not in paths:
                paths.append(p)
        except nx.NetworkXNoPath:
            continue

    if len(paths) < num_paths:
        # cycle existing ones if topology is sparse, but never crash the pipeline
        while len(paths) < num_paths:
            paths.append(paths[len(paths) % max(1, len(paths))])

    # --- build contexts (K x 3 per path) ---
    degrees = dict(topology.degree())
    max_degree = max(degrees.values()) if degrees else 1.0

    external_contexts = []
    for path in paths[:num_paths]:
        hops = float(len(path) - 1)
        avg_deg = float(np.mean([degrees[n] for n in path])) / max_degree
        base = np.array([[hops, avg_deg, fusion_prob]], dtype=float)

        if arms_per_path > 1:
            extra = base + rng.normal(0.0, noise_std, size=(arms_per_path - 1, 3))
            ctx = np.vstack([base, extra])
        else:
            ctx = base

        external_contexts.append(ctx)

    # --- build rewards matching K per path ---
    noise_model   = FusionNoiseModel(topology=topology, paths=paths, fusion_prob=fusion_prob, entanglement_prob=ent_prob)
    fidelity_calc = FusionFidelityCalculator()
    reward_func   = QuARCRewardFunction()

    external_rewards = []
    for p_idx, ctx in enumerate(external_contexts):
        K = int(np.asarray(ctx).shape[0])
        err_info = noise_model.get_error_rates(p_idx)
        base_fid = float(np.clip(fidelity_calc.compute_path_fidelity(err_info, context=None, fusion_prob=fusion_prob), 0.0, 1.0))

        rewards = []
        for _ in range(K):
            success = (rng.random() < base_fid)
            rewards.append(float(reward_func.compute_reward(success=success, aggregate_throughput=1)))
        external_rewards.append(rewards)

    # --- sanity ---
    assert len(external_contexts) == num_paths
    assert len(external_rewards)  == num_paths
    for c, r in zip(external_contexts, external_rewards):
        assert np.asarray(c).shape[1] == 3
        assert len(r) == np.asarray(c).shape[0]

    return {
        "external_topology":  topology,
        "external_contexts":  external_contexts,
        "external_rewards":   external_rewards,
        "noise_model":        noise_model,
        "fidelity_calculator": fidelity_calc,
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
        # ✅ Use FRAMEWORK_CONFIG
        paper7_cfg = FRAMEWORK_CONFIG['paper7_physics']
        
        # Map network scale to node count (or use None for full topology)
        scale_to_nodes = {"large": 1000, "medium": 500, "small": 100}
        # node_num = paper7_cfg.get('max_nodes') or scale_to_nodes.get(paper7_cfg["network_scale"], None)
        node_num = paper7_cfg.get('max_nodes')
        
        # Generate/load topology
        if topology is not None:
            final_topology = topology
        else:
            # ✅ If no real topology file, generate synthetic directly
            if paper7_cfg.get('use_synthetic', False) or not paper7_cfg['topology_path']:
                # Generate synthetic topology directly
                topo_gen = Paper7ASTopologyGenerator(
                    edge_list_path="dummy_nonexistent.txt",  # Will trigger synthetic
                    max_nodes=topology_max_nodes or node_num,
                    seed=base_seed,
                    synthetic_fallback=True,
                    synthetic_kind="barabasi_albert",
                    synthetic_params={"n": node_num, "m": 3}
                )
            else:
                topo_gen = Paper7ASTopologyGenerator(
                    edge_list_path=paper7_cfg['topology_path'],
                    max_nodes=node_num,  # ✅ Will be None = use full topology
                    seed=base_seed,
                    relabel_to_integers=topology_relabel_to_int,
                    largest_cc_only=topology_largest_cc_only,
                    synthetic_fallback=True,
                )
            final_topology = topo_gen.generate()
        
        # Generate k-shortest paths for n_qisps ISPs
        k = paper7_cfg["k"]
        n_qisps = paper7_cfg["n_qisps"]
        paths = generate_paper7_paths(final_topology, k, n_qisps, base_seed)
        
        # Generate contexts (path-level features)
        contexts = generate_paper7_contexts(paths, final_topology)
        
        return {
            "noise_model": None,
            "fidelity_calculator": None,
            "external_topology": final_topology,
            "external_contexts": contexts,
            "external_rewards": None,
        }


    # === PAPER2 HANDLING ===
    elif physics_model == "paper2":
        # Load Paper2 config
        p2_config = FRAMEWORK_CONFIG["paper2_physics"]
        
        # Topology resolution
        if topology is not None:
            topo = topology
        elif topology_model == "paper2":
            topo_gen = Paper2TopologyGenerator(num_nodes=p2_config["num_nodes"], seed=base_seed)
            topo = topo_gen.generate()
        else:
            topo_gen = Paper2TopologyGenerator(num_nodes=p2_config["num_nodes"], seed=base_seed)
            topo = topo_gen.generate()
        
        # Path generation
        try:
            path_generator = nx.shortest_simple_paths(
                topo, p2_config["source_node"], p2_config["dest_node"], weight="distance"
            )
            paths = list(itertools.islice(path_generator, p2_config["num_paths"]))
        except nx.NetworkXNoPath:
            paths = [[p2_config["source_node"], p2_config["dest_node"]]] * p2_config["num_paths"]
        
        # Physics objects
        noise_model = FiberLossNoiseModel(
            topology=topo, paths=paths, p_init=p2_config["p_init"], f_attenuation=p2_config["f_attenuation"]
        )
        fidelity_calc = CascadedFidelityCalculator()
        
        # Contexts
        contexts = []
        for path in paths:
            hop_count = len(path) - 1
            contexts.append([np.array([3] * hop_count)])
        
        return {
            "noise_model": noise_model,
            "fidelity_calculator": fidelity_calc,
            "external_topology": topo,
            "external_contexts": contexts,
            "external_rewards": None,
        }
    elif physics_model == 'paper12_quarc':
        # Get Paper12 physics
        physics_params = get_physics_params_paper12(
            FRAMEWORK_CONFIG['paper12_quarc'], 
            seed=base_seed,
            qubit_cap=qubit_cap
        )
        
        noise_model = physics_params['noise_model']
        fidelity_calc = physics_params['fidelity_calculator']
        topology = physics_params['external_topology']
        contexts = physics_params['external_contexts']
        rewards = physics_params['external_rewards']
        
        num_paths = len(contexts)
        print(f"Paper12 (QuARC) physics: {num_paths} paths, fusion_prob={FRAMEWORK_CONFIG['paper12_quarc']['fusion_prob']}")
        return physics_params
    # === DEFAULT ===
    else:
        return {
            "noise_model": None,
            "fidelity_calculator": None,
            "external_topology": topology,
            "external_contexts": None,
            "external_rewards": None,
        }







# ============================================================================
# MAIN AUTOMATION LOOP
# ============================================================================

# ✅ UPDATED: Calculate total runs with physics models
total_runs = len(PHYSICS_MODELS) * len(ATTACK_SCENARIOS) * len(ALLOCATORS) * len(CAPACITY_TYPES) * len(SCALES)
run_count = 0

# ✅ UPDATED: Add physics model and attack scenario loops
for physics_model in PHYSICS_MODELS:
    # for attack_scenario in ATTACK_SCENARIOS:
    for allocator_type in ALLOCATORS:
        for current_experiments in RUNS:
            for cap_type in CAPACITY_TYPES:
                for scale in SCALES:
                    run_count += 1

                    print("\n" + "=" * 70)
                    print(f"RUN {run_count}/{total_runs}")
                    # print(f"Physics: {physics_model} | Attack: {attack_scenario}")  # ✅ NEW
                    print(f"Allocator: {allocator_type} | CapType: {cap_type} | Scale: {scale}")
                    print("=" * 70)
                    print("QUANTUM MAB MODELS EVALUATION FRAMEWORK")
                    print("=" * 70)

                    # Create allocator
                    # paper2_params = get_physics_params(physics_model='paper2')  # includes paths
                    # 1. Create allocator (dynamic num_paths for Paper #2)
                    num_paths = 8 if physics_model == 'paper2' else 4
                    allocator_obj = create_allocator(allocator_type, num_paths=num_paths)
                    print(f"✓ Created allocator: {type(allocator_obj).__name__} ({num_paths} paths)")

                    # 2. Get physics params
                    qubit_cap = allocator_obj.allocate(timestep=0, route_stats={}, verbose=False)
                    physics_params = get_physics_params(
                        physics_model=physics_model,
                        current_frames=current_frames,
                        base_seed=base_seed,
                        qubit_cap=qubit_cap
                    )

                    # 3. Create config
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
                        scale=scale,
                        suffix=physics_model.replace("default", "")
                    )

                    # 4. ✅ CALL YOUR EXTENDED set_environment() WITH PHYSICS
                    # config.get_testbed_config()  # Should return Paper2_UCB_2023 params
                    evaluator = MultiRunEvaluator(configs=custom_config, base_frames=current_frames, frame_step=frame_step)
                    evaluator.configs.set_log_name(base_frames=current_frames, frame_step=frame_step)
                    evaluator.configs.backup_mgr.init_logging_redirect(evaluator)

                    # Execute evaluation
                    try:
                        print("\n⚙ Running Quantum MAB Models Evaluation...")
                        comparison_results = evaluator.test_stochastic_environment(cal_winner=True, parellel=False)
                        evaluator.calculate_scenarios_performance()
                        # last_exp_comparison_results = evaluator.get_evaluation_results(attack_scenario)  # ✅ UPDATED
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
