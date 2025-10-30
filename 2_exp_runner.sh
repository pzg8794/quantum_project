#!/bin/bash

################################################################################
# SCRIPT 2: EXPERIMENT RUNNER - Parameterized Experiment Execution
# Takes parameters: frames, models, runs, scenarios
# Output: Results JSON + local logs
################################################################################

set +e

# Parameters (can be overridden from command line)
FRAMES=${1:-100}
MODELS=${2:-"Oracle,GNeuralUCB"}
RUNS=${3:-1}
SCENARIOS=${4:-"stochastic"}
ATTACK_INTENSITY=${5:-0.25}

REPO_DIR="/tmp/quantum_repo"
RUN_ID=$(date +%s%N)
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/exp_run_${RUN_ID}.log"

mkdir -p "$LOG_DIR"

# Logging functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "ERROR: $1" | tee -a "$LOG_FILE"; }
warn() { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# Verify Environment
# =============================================================================

log "================================"
log "Verifying Environment"
log "================================"

if [ ! -d "$REPO_DIR/Dynamic_Routing_Eval_Framework" ]; then
    error "Repo not found at $REPO_DIR - run 1_startup.sh first!"
    exit 1
fi

cd "$REPO_DIR/Dynamic_Routing_Eval_Framework"
export PYTHONPATH="$(pwd):$PYTHONPATH"

success "Environment verified"

# =============================================================================
# Log Experiment Parameters
# =============================================================================

log "================================"
log "Experiment Configuration"
log "================================"

cat << EOF | tee -a "$LOG_FILE"
Run ID: $RUN_ID
Frames: $FRAMES
Models: $MODELS
Runs: $RUNS
Scenarios: $SCENARIOS
Attack Intensity: $ATTACK_INTENSITY
EOF

# =============================================================================
# Run Experiment
# =============================================================================

log "================================"
log "Running Experiment"
log "================================"

START_TIME=$(date +%s)

python3 << PYEOF
import sys, os, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

try:
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    
    print("  Initializing config...")
    
    # Parse models and scenarios
    models = "$MODELS".split(',')
    scenarios_dict = {}
    for s in "$SCENARIOS".split(','):
        scenarios_dict[s.strip()] = s.strip().capitalize()
    
    config = ExperimentConfiguration(
        runs=$RUNS,
        allocator=None,
        env_type='$SCENARIOS',
        scenarios=scenarios_dict,
        models=models,
        attack_intensity=$ATTACK_INTENSITY
    )
    
    print("  Creating evaluator...")
    evaluator = MultiRunEvaluator(configs=config, base_frames=$FRAMES)
    
    print(f"  Running experiment with {$FRAMES} frames...")
    results = evaluator.test_stochastic_environment(cal_winner=False)
    
    print(f"  Experiment complete: {len(results)} results")
    
    # Save results
    os.makedirs("experiment_results", exist_ok=True)
    result_file = f"experiment_results/results_{$FRAMES}f_run_${RUN_ID}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'run_id': '${RUN_ID}',
            'frames': $FRAMES,
            'models': models,
            'results_count': len(results)
        }, f, indent=2)
    print(f"  Results saved: {result_file}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PYEOF

EXP_EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [ $EXP_EXIT_CODE -eq 0 ]; then
    success "Experiment completed in ${ELAPSED}s"
else
    error "Experiment failed with code $EXP_EXIT_CODE"
    exit 1
fi

# =============================================================================
# Save Results and Logs
# =============================================================================

log "================================"
log "Saving Results"
log "================================"

mkdir -p results/experiments/run_${RUN_ID}
RESULT_DIR="results/experiments/run_${RUN_ID}"

cp "$LOG_FILE" "$RESULT_DIR/experiment_${RUN_ID}.log"
log "Log saved: $RESULT_DIR/experiment_${RUN_ID}.log"

# Create report
cat > "$RESULT_DIR/EXPERIMENT_REPORT.txt" << EOF
Experiment Report
=================
Run ID: $RUN_ID
Timestamp: $(date)
Duration: ${ELAPSED}s
Status: COMPLETED

Parameters:
  Frames: $FRAMES
  Models: $MODELS
  Runs: $RUNS
  Scenarios: $SCENARIOS
  Attack Intensity: $ATTACK_INTENSITY

Results Location:
  Log: $RESULT_DIR/experiment_${RUN_ID}.log
  Results: experiment_results/

Ready to push!
EOF

cat "$RESULT_DIR/EXPERIMENT_REPORT.txt" | tee -a "$LOG_FILE"
success "Results saved"

# =============================================================================
# Summary
# =============================================================================

log "================================"
log "EXPERIMENT EXECUTION COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

SUMMARY
=======
Status: SUCCESS
Duration: ${ELAPSED}s
Results Location: $RESULT_DIR
Log File: $LOG_FILE

Next: Run 3_push_results.sh to upload to GitHub

EOF

success "Experiment complete and ready for push!"
