#!/bin/bash
gcloud compute instances add-metadata "$(hostname)" \
  --zone="$(curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F/ '{print $4}')" \
  --metadata=status=testing --quiet
  
set +e

# Script arguments - 12 TOTAL, NO DUPLICATES
BASE_FRAMES=$1
EXP_NUM=$2
FRAME_STEP=$3
BASE_SEED=$4
EXP_ID=$5
INTENSITY=$6
ALLOCATOR=$7
SCALE=$8
BASE_CAPACITY=$9
SCENARIOS=${10}
USE_LAST_BACKUP=${11:-"false"}
PARALLEL=${12:-"false"}
OVERWRITE=${12:-"true"}

# Directory setup
LOG_DIR="${LOG_DIR:-$HOME/quantum_logs}"
REPO_DIR="${REPO_DIR:-$HOME/quantum_project}"
RES_DIR="${RES_DIR:-$REPO_DIR/Dynamic_Routing_Eval_Framework/results}"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${EXP_ID}_$(date +%s).log"

# Helper functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
error() { echo "✗ ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }

# Validate directory
if [ ! -d "Dynamic_Routing_Eval_Framework" ]; then error "Run from quantum_project root"; fi

log "Run: ${EXP_ID} | Frames: ${BASE_FRAMES} | Runs: ${EXP_NUM} | Step: ${FRAME_STEP} | Seed: ${BASE_SEED}"

# Setup Python environment
export PYTHONPATH="$(pwd):$PYTHONPATH"
cd Dynamic_Routing_Eval_Framework

python3 << PYEOF
import os, sys

# 1. Import modules
sys.path.insert(0, '..')
from daqr.core.qubit_allocator import *
from daqr.config.experiment_config import *
from daqr.evaluation.multi_run_evaluator import *
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

# 2. Initialize config
config = ExperimentConfiguration()
models = config.NEURAL_MODELS

# Parse bash arguments
base_frames = ${BASE_FRAMES}
exp_id = str("${EXP_ID}")
scale = ${SCALE:-2}
base_capacity = str("${BASE_CAPACITY:-"N"}").lower() in ["y", "yes", "true"]
use_last_backup = str("${USE_LAST_BACKUP}").lower() == "true"
parallel = str("${PARALLEL}").lower() == "true"
overwrite = str("${OVERWRITE}").lower() == "true"

# Quick test mode overrides
if "quick-test" in exp_id:
    base_frames = 100
    models = ["Oracle", "GNeuralUCB"]
    print("✓ QUICK-TEST mode: frames=100, models=['Oracle', 'GNeuralUCB']")
elif "test" in exp_id:
    base_frames = 1000
    print("✓ TEST mode: frames=1000")

FRAMEWORK_CONFIG = {
    'test_mode': True, 'base_frames': base_frames, 'exp_num': ${EXP_NUM}, 
    'frame_step': ${FRAME_STEP}, 'models': models, 'prod_frames': 4000,
    'prod_experiments': 10, 'main_env': 'stochastic',
    'eval_mod': 'comprehensive',
    'env_attrs': {'intensity': ${INTENSITY:-0.25}, 'base_seed': ${BASE_SEED}, 'reproducible': True},
}

test_scenarios_arg = "${SCENARIOS:-None}"
attack_intensity = FRAMEWORK_CONFIG['env_attrs']['intensity']
current_experiments = FRAMEWORK_CONFIG['exp_num'] if FRAMEWORK_CONFIG['test_mode'] else FRAMEWORK_CONFIG['prod_experiments']

# Define evaluation scenarios
evaluation_type = "STOCHASTIC-FOCUSED"
if test_scenarios_arg == "None" and FRAMEWORK_CONFIG['main_env'] == 'stochastic':
    test_scenarios = {
        'stochastic': 'Stochastic Random Failures',
        'markov': 'Markov Adversarial Attack',
        'adaptive': 'Adaptive Adversarial Attack',
        'onlineadaptive': 'Online Adaptive Attack',
        'none': 'Baseline (Optimal Conditions)'
    }
else:
    test_scenarios = {
        'stochastic': 'Stochastic (Natural Network Failures)', 
        'adaptive': 'Adversarial (Strategic Attacks)'
    }
    evaluation_type = "COMPARATIVE"

# Allocator setup
allocator_arg = "${ALLOCATOR:-None}"
allocator = None
if allocator_arg.lower() == "thompson":
    allocator = ThompsonSamplingAllocator(total_qubits=35, num_routes=4, min_qubits_per_route=2)
elif allocator_arg.lower() == "dynamic":
    allocator = DynamicQubitAllocator(total_qubits=35, num_routes=4, min_qubits_per_route=2, exploration_bonus=2.0)
elif allocator_arg.lower() == "random":
    allocator = RandomQubitAllocator(epsilon=1.0, seed=42)

# Create configuration
custom_config = ExperimentConfiguration(
    runs=current_experiments, 
    allocator=allocator, 
    env_type=FRAMEWORK_CONFIG['main_env'], 
    scenarios=test_scenarios, 
    models=models, 
    attack_intensity=attack_intensity, 
    scale=scale, 
    base_capacity=base_capacity, 
    use_last_backup=use_last_backup,
    overwrite=overwrite
)

# Create evaluator
evaluator = MultiRunEvaluator(
    configs=custom_config, 
    base_frames=FRAMEWORK_CONFIG['base_frames'], 
    frame_step=FRAMEWORK_CONFIG['frame_step']
)

print("\n" + "=" * 70)
print("QUANTUM MAB MODELS EVALUATION FRAMEWORK")
print("=" * 70)
print(f"  • Environment: {FRAMEWORK_CONFIG['main_env'].upper()}")
print(f"  • Models: {len(models)}")
print(f"  • Scale: {scale}")
print(f"  • Base Capacity: {base_capacity}")
print(f"  • Use Last Backup: {use_last_backup}")
print(f"  • Parallel: {parallel}")
print("=" * 70)

print(f"\n▶ {evaluation_type} EVALUATION:")
for scenario, description in test_scenarios.items():
    print(f"  • {scenario.upper():<20} {description}")
print("=" * 70)

# Run evaluation
try:
    print("\n⚙ Running evaluation...")
    comparison_results = evaluator.test_stochastic_environment(cal_winner=True, parellel=parallel)
    evaluator.calculate_scenario_performance(scenario=FRAMEWORK_CONFIG['main_env'])
    print(f"\n✓ Evaluation completed!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Visualization
print("\n" + "=" * 70)
print("ROBUSTNESS ANALYSIS")
print("=" * 70)

try:
    viz = QuantumEvaluatorVisualizer(comparison_results, allocator=allocator, config=custom_config)
    viz.plot_stochastic_vs_adversarial_comparison()

    for scenario in test_scenarios.keys():
        if scenario.lower() != 'stochastic':
            print(f"\n📊 Plotting: {scenario.upper()}")
            evaluator.calculate_scenario_performance(scenario=scenario)
            viz.plot_scenarios_comparison(scenario=scenario)

    print("\n✓ Plots generated!")
    
    stoch_data = viz.get_viz_data('stochastic_data')
    if stoch_data and 'averaged' in stoch_data:
        stoch_results = stoch_data['averaged']
        print("\n" + "=" * 70)
        print("PERFORMANCE METRICS")
        print("=" * 70)
        
        winner = stoch_results.get('winner', 'N/A')
        for alg in models:
            if alg in stoch_results['results']:
                model_data = stoch_results['results'][alg]
                efficiency = model_data.get('efficiency', 0)
                gap = model_data.get('gap', float('inf'))
                
                print(f"\n{alg}:")
                print(f"  • Efficiency: {efficiency:.1f}%")
                print(f"  • Gap: {gap:.1f}%")
                if alg == winner:
                    print(f"  ★ WINNER ★")

except Exception as e:
    print(f"❌ Visualization error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n✓ {exp_id} complete")
PYEOF

if [ $? -ne 0 ]; then error "${EXP_ID} failed"; fi
log "${EXP_ID} done"
