#!/bin/bash
set +e

BASE_FRAMES=$1
EXP_NUM=$2
FRAME_STEP=$3
BASE_SEED=$4
EXP_ID=$5

LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/${EXP_ID}_$(date +%s).log"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
error() { echo "✗ ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }

if [ ! -d "Dynamic_Routing_Eval_Framework" ]; then error "Run from quantum_project root"; fi

log "Run: ${EXP_ID} | Frames: ${BASE_FRAMES} | Runs: ${EXP_NUM} | Step: ${FRAME_STEP} | Seed: ${BASE_SEED}"

export PYTHONPATH="$(pwd):$PYTHONPATH"
cd Dynamic_Routing_Eval_Framework

python3.11 << PYEOF
import sys


# 1
sys.path.insert(0, '..')
from daqr.core.qubit_allocator import *
from daqr.config.experiment_config import *
from daqr.evaluation.multi_run_evaluator import *


# 2
config = ExperimentConfiguration()
models = config.NEURAL_MODELS

FRAMEWORK_CONFIG = {
    'test_mode': True, 'base_frames': ${BASE_FRAMES}, 'exp_num': ${EXP_NUM}, 
    'frame_step': ${FRAME_STEP}, 'models': models, 'prod_frames': 4000,
    'prod_experiments': 10, 'frame_steps': [], 'main_env': 'stochastic',
    'eval_mod': 'comprehensive', 'main_model': 'CEXPNeuralUCB',
    'routing_strategy': 'fixed', 'enable_routing_comparison': False,
    'alg_attrs': {'lambda_reg': 1.0, 'gamma': 0.1, 'network_width': 128,
                  'network_depth': 2, 'gradient_steps': 8, 'learning_rate': 1e-4},
    'env_attrs': {'intensity': 0.25, 'base_seed': ${BASE_SEED}, 'reproducible': True},
    'scenarios': {'exp_focus': ['stochastic'], 'stochastic_vs_baseline': ['none', 'stochastic'],
                  'comprehensive': ['none', 'stochastic', 'markov', 'adaptive'],
                  'adversarial': ['markov', 'adaptive', 'onlineadaptive']}
}


# 3
# Define evaluation scenarios based on framework focus
 evaluation_type = "STOCHASTIC-FOCUSED"
if FRAMEWORK_CONFIG['main_env'] == 'stochastic':
    # Primary stochastic evaluation with optional comparison
    test_scenarios = {
        'stochastic': 'Stochastic Random Failures',
        'markov': 'Markov Adversarial Attack',
        'adaptive': 'Adaptive Adversarial Attack',
        'onlineadaptive': 'Online Adaptive Attack',
        'none': 'Baseline (Optimal Conditions)'  # For comparison
    }
    evaluation_type = "STOCHASTIC-FOCUSED"
else:
    # Fallback to stochastic vs adversarial for comparison
    test_scenarios = {
        'stochastic': 'Stochastic (Natural Network Failures)', 
        'adaptive': 'Adversarial (Strategic Attacks)'
    }
    evaluation_type = "COMPARATIVE"


# 4
allocator = None
custom_config = ExperimentConfiguration(
    runs=FRAMEWORK_CONFIG['exp_num'], allocator=allocator, 
    env_type=FRAMEWORK_CONFIG['main_env'], scenarios=FRAMEWORK_CONFIG['scenarios']['exp_focus'], 
    models=models, attack_intensity=FRAMEWORK_CONFIG['env_attrs']['intensity'])

# 5
evaluator = MultiRunEvaluator(configs=custom_config, base_frames=FRAMEWORK_CONFIG['base_frames'], frame_step=FRAMEWORK_CONFIG['frame_step'])

print("\n✓ Framework Configuration:")
print(f"  • Primary Environment: {FRAMEWORK_CONFIG['main_env'].upper()}")
print(f"  • Evaluation Mode: {FRAMEWORK_CONFIG['eval_mod'].upper()}")
print(f"  • Models to Test: {len(models)}")
print("=" * 70)

print(f"\n▶ Executing {evaluation_type.upper()} EVALUATION:")
for scenario, description in test_scenarios.items():
    print(f"  • {scenario.upper():<20} {description}")
print("=" * 70)


# 6
# Execute framework evaluation
try:
    print("\n⚙ Running Quantum MAB Models Evaluation...")
    
    comparison_results = evaluator.test_stochastic_environment(cal_winner=True)
    evaluator.calculate_scenario_performance(scenario=FRAMEWORK_CONFIG['main_env'])
    last_exp_comparison_results = evaluator.get_evaluation_results(FRAMEWORK_CONFIG['main_env'])
    
    print(f"\n✓ Quantum MAB Models Evaluation Framework - {evaluation_type.upper()} evaluation completed!")
    
except Exception as e:
    print(f"\n❌ Evaluation error: {e}")
    print("⚠ This may indicate missing framework components or configuration issues")
    import traceback
    traceback.print_exc()

print("${EXP_ID} complete")
PYEOF

if [ $? -ne 0 ]; then error "${EXP_ID} failed"; fi
log "${EXP_ID} done"