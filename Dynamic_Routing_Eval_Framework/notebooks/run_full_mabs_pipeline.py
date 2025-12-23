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

from daqr.config import experiment_config, gd_backup_manager, local_backup_manager
from daqr.core import network_environment, qubit_allocator
from daqr.algorithms import neural_bandits, predictive_bandits, base_bandit
from daqr.evaluation import multi_run_evaluator, visualizer, experiment_runner

# Reload all modules
for module in [experiment_config, network_environment, qubit_allocator, base_bandit,
               neural_bandits, predictive_bandits, experiment_runner, multi_run_evaluator, visualizer]:
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

print("✓ All modules reloaded successfully (fresh environment ready)")

# ============================================================================
# CONFIGURATION - FROM YOUR FRAMEWORK_CONFIG
# ============================================================================

# Initialize base config to get model lists
config = ExperimentConfiguration()

# Framework-specific experimental configuration (YOUR EXACT CONFIG)
FRAMEWORK_CONFIG = {
    # Testing Configuration
    'test_mode': True,
    'base_frames': 4000,
    'exp_num': 3,
    'frame_step': 2000,
    
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
    }
}

# Calculate frame steps
for exp_id in range(0, FRAMEWORK_CONFIG['exp_num']):
    FRAMEWORK_CONFIG['frame_steps'].append(
        FRAMEWORK_CONFIG['base_frames'] + (FRAMEWORK_CONFIG['frame_step'] * exp_id)
    )
FRAMEWORK_CONFIG['capacity'] = 10000  # quantum paper default capacity

# Dynamic configuration based on testing mode
attack_intensity = FRAMEWORK_CONFIG['env_attrs']['intensity']  # ✅ 0.25 from YOUR config
frame_step = FRAMEWORK_CONFIG['frame_step']  # ✅ 2000
current_frames = (FRAMEWORK_CONFIG['base_frames'] if FRAMEWORK_CONFIG['test_mode'] 
                  else FRAMEWORK_CONFIG['prod_frames'])  # ✅ 4000
current_experiments = (FRAMEWORK_CONFIG['exp_num'] if FRAMEWORK_CONFIG['test_mode'] 
                       else FRAMEWORK_CONFIG['prod_experiments'])  # ✅ 3
base_seed = FRAMEWORK_CONFIG['env_attrs']['base_seed']  # ✅ 12345

# ============================================================================
# LOOP CONFIGURATION
# ============================================================================

# ALLOCATORS = ['Default', 'Dynamic', 'Random', 'ThompsonSampling']
ALLOCATORS = ['Random']
# CAPACITY_TYPES = ['T', 'Tb']
CAPACITY_TYPES = ['T']

RUNS = [10]
SCALES = [1, 1.5, 2]

# Toggle visualization
VISUALIZE = False

# Additional settings
last_backup = True
overwrite = False
base_cap = False

# ============================================================================
# MODELS & SCENARIOS
# ============================================================================

models = config.NEURAL_MODELS  # ✅ From your config object
test_scenarios = {
    'Stochastic': 'Random natural failures',
    'Markov': 'Markov-based adversarial attacks',
    'Adaptive': 'Adaptive adversarial attacks',
    'OnlineAdaptive': 'Online adaptive adversarial attacks',
    'None': 'Baseline (no attacks)'
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
print(f"  • Total runs: {len(ALLOCATORS) * len(CAPACITY_TYPES) * len(SCALES)}")

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
        viz = QuantumEvaluatorVisualizer(comparison_results, allocator=allocator, config=custom_config)
        viz.plot_stochastic_vs_adversarial_comparison()

        scenario_list = list(test_scenarios.keys())

        for scenario in scenario_list:
            if scenario.lower() == 'stochastic': 
                continue
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
                    
                    if alg == winner:
                        print("  ★ WINNER ★")
            
            print("\n" + "=" * 70)
            print("STOCHASTIC ENVIRONMENT INSIGHTS")
            print("=" * 70)
            print("  • Natural quantum decoherence and network failures")
            print("  • Performance metrics validate theoretical predictions")
            print("  • Baseline for future adversarial robustness studies")
        else:
            print("⚠ No stochastic averaged results available")

    except Exception as e:
        print(f"❌ Error in robustness analysis: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# HELPER FUNCTION: CREATE ALLOCATOR OBJECT
# ============================================================================

def create_allocator(allocator_type):
    """
    Factory function to create the appropriate allocator object.
    
    Args:
        allocator_type (str): Type of allocator
    
    Returns:
        Allocator object instance
    """
    if allocator_type == 'Random':
        return RandomQubitAllocator(
            total_qubits=35,
            num_routes=4,
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
# MAIN AUTOMATION LOOP
# ============================================================================

total_runs = len(ALLOCATORS) * len(CAPACITY_TYPES) * len(SCALES)
run_count = 0

for allocator_type in ALLOCATORS:
    for current_experiments in RUNS:
        for cap_type in CAPACITY_TYPES:
            for scale in SCALES:
                run_count += 1

                print("\n" + "=" * 70)
                print(f"RUN {run_count}/{total_runs}")
                print(f"Allocator: {allocator_type} | CapType: {cap_type} | Scale: {scale}")
                print("=" * 70)
                print("QUANTUM MAB MODELS EVALUATION FRAMEWORK - STOCHASTIC FOCUS")
                print("=" * 70)

                # ✅ CREATE THE ACTUAL ALLOCATOR OBJECT
                allocator_obj = create_allocator(allocator_type)
                print(f"✓ Created allocator: {type(allocator_obj).__name__}")

                # Create config WITH THE OBJECT
                custom_config = ExperimentConfiguration(
                    runs=current_experiments, 
                    allocator=allocator_obj,  # ← OBJECT, not string
                    env_type=FRAMEWORK_CONFIG['main_env'], 
                    scenarios=test_scenarios, 
                    use_last_backup=last_backup,
                    models=models, 
                    attack_intensity=attack_intensity,  # ← 0.25 from config
                    scale=scale, 
                    base_capacity=base_cap, 
                    overwrite=overwrite
                ) 
                
                evaluator = MultiRunEvaluator(
                    configs=custom_config, 
                    base_frames=current_frames,  # ← 4000 from config
                    frame_step=frame_step  # ← 2000 from config
                )

                # START LOGGING
                evaluator.configs.set_log_name(base_frames=current_frames, frame_step=frame_step)
                evaluator.configs.backup_mgr.init_logging_redirect(evaluator)

                # Execute evaluation
                try:
                    print("\n⚙ Running Quantum MAB Models Evaluation...")
                    comparison_results = evaluator.test_stochastic_environment(cal_winner=True, parellel=False)
                    evaluator.calculate_scenarios_performance()
                    last_exp_comparison_results = evaluator.get_evaluation_results(FRAMEWORK_CONFIG['main_env'])
                    print(f"\n✓ Quantum MAB Models Evaluation completed!")
                    
                except Exception as e:
                    print(f"\n❌ Evaluation error: {e}")
                    import traceback
                    traceback.print_exc()
                    
                finally:
                    # ALWAYS STOP LOGGING
                    evaluator.configs.backup_mgr.load_new_entries()
                    evaluator.configs.backup_mgr.stop_logging_redirect()

                # Run visualization if enabled
                if VISUALIZE:
                    run_visualization(evaluator, comparison_results, allocator_type, custom_config, test_scenarios, models)
                else:
                    print("\n⊘ Visualization skipped (VISUALIZE=False)")
                
                print(f"\n✅ Completed {run_count}/{total_runs}")

print("\n" + "=" * 70)
print("ALL RUNS COMPLETE!")
print("=" * 70)
