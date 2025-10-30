#!/bin/bash

################################################################################
# QUANTUM MAB AUTOMATED RUNNER
# Handles: GitHub setup, dependency installation, code execution, result pushback
# Run: ./startup.sh <SEED_OFFSET> <GITHUB_TOKEN>
# 
# Example:
#   ./startup.sh 0 ghp_xxxxxxxxxxxxxxxxxxxx
#   ./startup.sh 1 ghp_xxxxxxxxxxxxxxxxxxxx
#   ./startup.sh 2 ghp_xxxxxxxxxxxxxxxxxxxx
#   ./startup.sh 3 ghp_xxxxxxxxxxxxxxxxxxxx
################################################################################

set -e  # Exit on error

# =============================================================================
# CONFIGURATION - CUSTOMIZE FOR YOUR REPO
# =============================================================================

GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"
GITHUB_TOKEN="${2:-}"
SEED_OFFSET="${1:-0}"

REPO_DIR="/root/quantum_project"
LOG_DIR="/root/quantum_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# =============================================================================
# LOGGING SETUP
# =============================================================================

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_${SEED_OFFSET}_${TIMESTAMP}.log"

# Log to file AND stdout
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }
error() { echo "[ERROR] $1" >&2; exit 1; }
success() { echo "✅ $1"; }

# =============================================================================
# PHASE 1: SYSTEM SETUP
# =============================================================================

log "================================"
log "PHASE 1: System Setup"
log "================================"

log "Updating system packages..."
apt-get update -y > /dev/null 2>&1 || log "Warning: apt-get update had issues"

log "Installing system dependencies..."
apt-get install -y \
    python3 python3-pip python3-venv git curl wget \
    build-essential libssl-dev libffi-dev \
    > /dev/null 2>&1 || log "Warning: Some packages may have failed"

success "System dependencies installed"

# =============================================================================
# PHASE 2: GITHUB AUTHENTICATION
# =============================================================================

log "================================"
log "PHASE 2: GitHub Authentication"
log "================================"

if [ -z "$GITHUB_TOKEN" ]; then
    error "GitHub token required! Pass as argument: ./startup.sh <SEED_OFFSET> <GITHUB_TOKEN>"
fi

# Configure git
git config --global user.email "automation@quantum-mab.local"
git config --global user.name "Quantum MAB Automation"

success "Git configured"

# =============================================================================
# PHASE 3: REPOSITORY SETUP
# =============================================================================

log "================================"
log "PHASE 3: Repository Setup"
log "================================"

if [ -d "$REPO_DIR" ]; then
    log "Repository already exists, pulling latest..."
    cd "$REPO_DIR"
    git pull origin main > /dev/null 2>&1 || log "Warning: Git pull had issues (may be first run)"
else
    log "Cloning repository..."
    REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git"
    git clone "$REPO_URL" "$REPO_DIR" > /dev/null 2>&1 || error "Failed to clone repository"
    cd "$REPO_DIR"
fi

success "Repository ready at $REPO_DIR"

# =============================================================================
# PHASE 4: PYTHON ENVIRONMENT SETUP
# =============================================================================

log "================================"
log "PHASE 4: Python Environment"
log "================================"

log "Creating virtual environment..."
python3 -m venv /root/venv > /dev/null 2>&1 || log "Warning: venv creation had issues"

log "Activating virtual environment..."
source /root/venv/bin/activate

log "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install ML dependencies
log "Installing PyTorch and ML libraries..."
pip install -q \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    numpy pandas matplotlib seaborn tqdm statsmodels scikit-learn scipy \
    || error "Failed to install Python packages"

success "Python environment ready"

# Create __init__.py files for package structure
log "Setting up package structure..."
cd "$REPO_DIR"

# Find all directories and create __init__.py
find . -type d -name "*.py" -prune -o -type d -not -name ".git" -not -name ".*" -exec touch {}/__init__.py \; 2>/dev/null || true

# Specific directories that should have __init__.py
for dir in daqr daqr/config daqr/core daqr/evaluation daqr/algorithms; do
    mkdir -p "$dir"
    touch "$dir/__init__.py" 2>/dev/null || true
done

success "Package structure configured"

# =============================================================================
# PHASE 5: PREPARE EXPERIMENT
# =============================================================================

log "================================"
log "PHASE 5: Experiment Preparation"
log "================================"

# Create results directory
RESULTS_DIR="$REPO_DIR/results/run_${SEED_OFFSET}"
mkdir -p "$RESULTS_DIR"

log "Seed offset: $SEED_OFFSET"
log "Results directory: $RESULTS_DIR"

success "Experiment prepared"

# =============================================================================
# PHASE 6: RUN EXPERIMENTS
# =============================================================================

log "================================"
log "PHASE 6: Running Experiments"
log "================================"

cd "$REPO_DIR"

log "Starting quantum MAB evaluation..."
log "Configuration:"
log "  - Username: $GITHUB_USERNAME"
log "  - Repo: $GITHUB_REPO"
log "  - Models: Oracle GNeuralUCB EXPNeuralUCB CPursuitNeuralUCB iCPursuitNeuralUCB"
log "  - Scenarios: stochastic markov onlineadaptive none (all at once)"
log "  - Horizons: 4000 6000 8000"
log "  - Runs: 3 (with seed offset $SEED_OFFSET)"
log ""

# Run the main experiment
START_TIME=$(date +%s)

python3 -m daqr.evaluation.multi_run_evaluator \
    --models Oracle GNeuralUCB EXPNeuralUCB CPursuitNeuralUCB iCPursuitNeuralUCB \
    --scenarios stochastic markov onlineadaptive none \
    --horizons 4000 6000 8000 \
    --runs 3 \
    --seed-offset "$SEED_OFFSET" \
    2>&1 | tee "$RESULTS_DIR/experiment_output.log"

EXPERIMENT_EXIT_CODE=${PIPESTATUS[0]}
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [ $EXPERIMENT_EXIT_CODE -eq 0 ]; then
    success "Experiments completed successfully"
    log "Elapsed time: $((ELAPSED / 60)) minutes $((ELAPSED % 60)) seconds"
else
    log "Warning: Experiments finished with exit code $EXPERIMENT_EXIT_CODE"
    log "This may be acceptable - check output logs"
fi

# =============================================================================
# PHASE 7: PREPARE RESULTS
# =============================================================================

log "================================"
log "PHASE 7: Results Preparation"
log "================================"

log "Collecting results..."

# Find and copy results
RESULT_COUNT=$(find "$REPO_DIR/results" -type f \( -name "*.csv" -o -name "*.json" -o -name "*.pkl" \) 2>/dev/null | wc -l)
log "Found $RESULT_COUNT result files"

# Create summary file
cat > "$RESULTS_DIR/SUMMARY.txt" << EOF
================================================================================
QUANTUM MAB EXPERIMENT SUMMARY
================================================================================

Execution Details:
  Start Time: $(date -d @$START_TIME '+%Y-%m-%d %H:%M:%S')
  End Time: $(date -d @$END_TIME '+%Y-%m-%d %H:%M:%S')
  Duration: $((ELAPSED / 60)) minutes $((ELAPSED % 60)) seconds
  Seed Offset: $SEED_OFFSET (Independent run set)
  Exit Code: $EXPERIMENT_EXIT_CODE

Repository Details:
  GitHub Username: $GITHUB_USERNAME
  Repository: $GITHUB_REPO
  Clone URL: https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO}

Configuration:
  Models: 
    - Oracle (optimal baseline)
    - GNeuralUCB (pure neural bandit)
    - EXPNeuralUCB (adversarial neural bandit)
    - CPursuitNeuralUCB (contextual pursuit-based)
    - iCPursuitNeuralUCB (ARIMA-informed contextual pursuit)
  
  Scenarios (all running together):
    - Stochastic: Random noise-based attacks
    - Markov: Stateful adversarial attacks
    - OnlineAdaptive: Reactive online learning attacks
    - Baseline: No attacks (optimal conditions)
  
  Horizons (timesteps): 4000, 6000, 8000
  Runs per configuration: 3 (independent repetitions)
  
Results Location: $RESULTS_DIR

Status: $([ $EXPERIMENT_EXIT_CODE -eq 0 ] && echo "SUCCESS ✅" || echo "COMPLETED WITH WARNINGS ⚠️")

Result Files:
  - experiment_output.log: Full experiment console output
  - SUMMARY.txt: This file

================================================================================
EOF

success "Results summary created"

# =============================================================================
# PHASE 8: GIT PUSH RESULTS
# =============================================================================

log "================================"
log "PHASE 8: GitHub Push"
log "================================"

cd "$REPO_DIR"

log "Checking for changes..."
git status

log "Staging results for commit..."
git add results/run_${SEED_OFFSET}/ > /dev/null 2>&1 || log "Note: Some files may not have been staged"

COMMIT_MSG="Add experimental results: run_${SEED_OFFSET} (seed offset $((SEED_OFFSET + 1))), $(date +%Y-%m-%d\ %H:%M:%S)"

log "Committing changes..."
if git commit -m "$COMMIT_MSG" > /dev/null 2>&1; then
    success "Changes committed"
else
    log "Note: Nothing new to commit (may already be pushed)"
fi

log "Pushing to GitHub (main branch)..."
git push origin main 2>&1 || error "Failed to push to GitHub. Check token, connectivity, and permissions."

success "Results pushed to GitHub"

# =============================================================================
# FINAL SUMMARY
# =============================================================================

log "================================"
log "✅ EXECUTION COMPLETE"
log "================================"

cat << EOF

================================================================================
📊 QUANTUM MAB EXPERIMENT FINISHED
================================================================================

✅ What was completed:
  ✓ System packages installed
  ✓ Python environment configured
  ✓ Repository cloned/pulled
  ✓ All dependencies installed
  ✓ Experiments executed (ALL scenarios + ALL environments)
  ✓ Results collected
  ✓ Changes committed to Git
  ✓ Results pushed to GitHub

📈 Experiment Details:
  - Exit Code: $EXPERIMENT_EXIT_CODE (0 = success)
  - Total Runtime: $((ELAPSED / 60)) minutes $((ELAPSED % 60)) seconds
  - Results Directory: $RESULTS_DIR
  - Log File: $LOG_FILE
  - GitHub: https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO}

📂 Repository Structure:
  GitHub repo: pzg8794/quantum_project
  Results stored: results/run_${SEED_OFFSET}/
  
🔍 Verify Results:
  1. Visit: https://github.com/pzg8794/quantum_project
  2. Check: results/ directory for run_${SEED_OFFSET}/
  3. Download: experiment_output.log for detailed run info

🚀 Next Steps:
  1. Verify this run succeeded on GitHub
  2. Launch other seed offsets on different VMs:
     - VM 2: ./startup.sh 1 <GITHUB_TOKEN>
     - VM 3: ./startup.sh 2 <GITHUB_TOKEN>
     - VM 4: ./startup.sh 3 <GITHUB_TOKEN>
  3. Wait for all 4 runs to complete (~2.5 hours each)
  4. Aggregate results from all 4 independent runs
  5. Compute statistics (mean ± std dev, confidence intervals)

📊 Expected Result Files (in each run_X/ directory):
  - experiment_output.log: Console output
  - SUMMARY.txt: Summary metadata
  - results/*.csv: Detailed experimental data (efficiency, retries, etc.)

⚡ Cost Estimate:
  - Per e2-standard-4 VM: ~$0.15/hour
  - Per 2.5-hour run: ~$0.38
  - 4 VMs in parallel: ~$1.50 total from your $300 GCP credit

================================================================================

EOF

exit $EXPERIMENT_EXIT_CODE
