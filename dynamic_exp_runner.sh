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
sys.path.insert(0, '..')
from daqr.core.qubit_allocator import *
from daqr.config.experiment_config import *
from daqr.evaluation.multi_run_evaluator import *

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

allocator = None
custom_config = ExperimentConfiguration(
    runs=FRAMEWORK_CONFIG['exp_num'], allocator=allocator, 
    env_type=FRAMEWORK_CONFIG['main_env'], scenarios=FRAMEWORK_CONFIG['scenarios']['exp_focus'], 
    models=models, attack_intensity=FRAMEWORK_CONFIG['env_attrs']['intensity'])

evaluator = MultiRunEvaluator(configs=custom_config, base_frames=FRAMEWORK_CONFIG['base_frames'], frame_step=FRAMEWORK_CONFIG['frame_step'])
evaluator.run()
print("${EXP_ID} complete")
PYEOF

if [ $? -ne 0 ]; then error "${EXP_ID} failed"; fi
log "${EXP_ID} done"