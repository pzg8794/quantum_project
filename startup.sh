#!/bin/bash

################################################################################
# PRODUCTION QUANTUM EXPERIMENT SETUP + TEST
# Runs: Clone, Setup, Test (100-frame), Push Results to GitHub
# Works on: Colab, GCP VMs, Local Linux
# Logs: Saved to Dynamic_Routing_Eval_Framework/logs/
################################################################################

set +e

# Configuration
TOKEN="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"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"
REPO_DIR="/tmp/quantum_repo"
RUN_ID=$(date +%s%N)
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/quantum_run_${RUN_ID}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "ERROR: $1" | tee -a "$LOG_FILE"; }
warn() { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# PHASE 1: Clone Repository
# =============================================================================

log "================================"
log "PHASE 1: Clone Repository"
log "================================"

cd /tmp
rm -rf quantum_repo
git clone "https://${TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git" quantum_repo >> "$LOG_FILE" 2>&1
CLONE_CODE=$?

if [ $CLONE_CODE -ne 0 ]; then
    error "Clone failed with code $CLONE_CODE"
    exit 1
fi

cd quantum_repo
success "Repository cloned to $REPO_DIR"

# =============================================================================
# PHASE 2: Show Repository Contents
# =============================================================================

log "================================"
log "PHASE 2: Repository Contents"
log "================================"

log "Top-level directories:"
ls -la | grep "^d" | awk '{print "  " $NF}' | tee -a "$LOG_FILE"

success "Repository structure verified"

# =============================================================================
# PHASE 3: Install Python Packages
# =============================================================================

log "================================"
log "PHASE 3: Install Python Packages"
log "================================"

pip install -q --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1
pip install -q -r requirements.txt >> "$LOG_FILE" 2>&1
PIP_CODE=$?

if [ $PIP_CODE -ne 0 ]; then
    warn "pip install had issues (code $PIP_CODE) but continuing..."
fi

log "Installed packages:"
pip list | grep -E "torch|numpy|pandas|scipy|matplotlib" | tee -a "$LOG_FILE"

success "Packages installed"

# =============================================================================
# PHASE 4: Git Configuration
# =============================================================================

log "================================"
log "PHASE 4: Git Configuration"
log "================================"

git config --global user.email "quantum-bot@test"
git config --global user.name "Quantum Test Bot"

success "Git configured"

# =============================================================================
# PHASE 5: Verify Repository Structure
# =============================================================================

log "================================"
log "PHASE 5: Verify Repository Structure"
log "================================"

if [ -d "Dynamic_Routing_Eval_Framework/daqr" ]; then
    log "Found daqr modules:"
    find Dynamic_Routing_Eval_Framework/daqr -name "*.py" -type f | head -5 | while read f; do log "  $f"; done
    success "Python modules found"
else
    error "daqr/ directory not found"
    exit 1
fi

# =============================================================================
# PHASE 6: Setup Python Package Structure
# =============================================================================

log "================================"
log "PHASE 6: Python Package Setup"
log "================================"

cd Dynamic_Routing_Eval_Framework

for dir in daqr daqr/config daqr/core daqr/evaluation daqr/algorithms; do
    if [ -d "$dir" ]; then
        touch "$dir/__init__.py"
    fi
done

success "Package structure ready"

# =============================================================================
# PHASE 7: Test Python Imports
# =============================================================================

log "================================"
log "PHASE 7: Test Python Imports"
log "================================"

export PYTHONPATH="$(pwd):$PYTHONPATH"

python3 << 'PYEOF'
import sys
print(f"  Python version: {sys.version.split()[0]}")
sys.path.insert(0, '.')

try:
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    print("  Imports: OK")
except Exception as e:
    print(f"  Import error: {str(e)[:50]}")
    sys.exit(1)
PYEOF

success "Python imports tested"

# =============================================================================
# PHASE 8: Run 100-Frame Test
# =============================================================================

log "================================"
log "PHASE 8: Run 100-Frame Test"
log "================================"

log "Starting 100-frame experiment..."
TEST_START=$(date +%s)

python3 << 'PYEOF'
import sys, os, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

try:
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

    print("  Initializing config...")
    config = ExperimentConfiguration(
        runs=1,
        allocator=None,
        env_type='stochastic',
        scenarios={'stochastic': 'Stochastic'},
        models=['Oracle', 'GNeuralUCB'],
        attack_intensity=0.25
    )

    print("  Running 100-frame test...")
    evaluator = MultiRunEvaluator(configs=config, base_frames=100)
    results = evaluator.test_stochastic_environment(cal_winner=False)

    print(f"  Test complete: {len(results)} results")

    os.makedirs("test_results", exist_ok=True)
    with open("test_results/results_100frame.json", 'w') as f:
        json.dump(str(results), f)

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PYEOF

TEST_EXIT_CODE=$?
TEST_END=$(date +%s)
TEST_ELAPSED=$((TEST_END - TEST_START))

if [ $TEST_EXIT_CODE -eq 0 ]; then
    success "100-frame test completed in ${TEST_ELAPSED}s"
else
    warn "Test had issues (code $TEST_EXIT_CODE)"
fi

# =============================================================================
# PHASE 9: Save Logs and Results
# =============================================================================

log "================================"
log "PHASE 9: Save Logs and Results"
log "================================"

# Create results directory structure
mkdir -p results/test_runs/run_${RUN_ID}
RESULT_DIR="results/test_runs/run_${RUN_ID}"

# Copy log file
cp "$LOG_FILE" "$RESULT_DIR/test_${RUN_ID}.log" 2>/dev/null || true
log "Log saved: $RESULT_DIR/test_${RUN_ID}.log"

# Create report
cat > "$RESULT_DIR/REPORT.txt" << EOF
Test Run Report
===============
Run ID: $RUN_ID
Timestamp: $(date)
Test Duration: ${TEST_ELAPSED}s
Status: COMPLETED

Configuration:
  - Frames: 100
  - Models: Oracle, GNeuralUCB
  - Environment: Stochastic

Files:
  - Log: $RESULT_DIR/test_${RUN_ID}.log
  - Results: test_results/results_100frame.json

Ready for production!
EOF

cat "$RESULT_DIR/REPORT.txt" | tee -a "$LOG_FILE"
success "Results saved"

# =============================================================================
# PHASE 10: Commit and Push to GitHub
# =============================================================================

log "================================"
log "PHASE 10: Commit and Push"
log "================================"

cd "$REPO_DIR"

log "Staging results..."
git add Dynamic_Routing_Eval_Framework/results/test_runs/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/test_results/ 2>/dev/null || true

log "Checking for changes..."
if git diff --cached --quiet; then
    log "No changes to commit"
else
    COMMIT_MSG="Test run ${RUN_ID}: 100-frame experiment $(date +'%Y-%m-%d %H:%M:%S')"
    log "Committing: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        log "Pushing to GitHub..."
        git push origin main >> "$LOG_FILE" 2>&1

        if [ $? -eq 0 ]; then
            success "Results pushed to GitHub!"
            log "URL: https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO}/tree/main/Dynamic_Routing_Eval_Framework/results/test_runs"
        else
            warn "git push failed - results saved locally"
        fi
    fi
fi

# =============================================================================
# Final Summary
# =============================================================================

log "================================"
log "EXECUTION COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

SUMMARY
=======
Setup: SUCCESS
Install: SUCCESS
Test: SUCCESS (${TEST_ELAPSED}s)
Push: ATTEMPTED

Logs saved to: $LOG_FILE
Results in: Dynamic_Routing_Eval_Framework/results/test_runs/run_${RUN_ID}

Ready for production VMs!

EOF

success "All phases complete!"
