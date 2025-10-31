#!/bin/bash

################################################################################
# STARTUP SCRIPT - Install Python 3.11 + ALL packages (NO virtual env)
# Runs on: Ubuntu 20.04/22.04 LTS (GCP, AWS, Local)
################################################################################

set +e

TOKEN="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"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"
REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/startup_$(date +%s).log"

mkdir -p "$LOG_DIR"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "✓ SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "✗ ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn() { echo "⚠ WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# PHASE 0: Install Python 3.11
# =============================================================================

log "================================"
log "PHASE 0: Install Python 3.11"
log "================================"

log "Updating system..."
sudo apt-get update -qq >> "$LOG_FILE" 2>&1

log "Adding deadsnakes PPA..."
sudo apt-get install -y software-properties-common >> "$LOG_FILE" 2>&1
sudo add-apt-repository -y ppa:deadsnakes/ppa >> "$LOG_FILE" 2>&1
sudo apt-get update -qq >> "$LOG_FILE" 2>&1

log "Installing Python 3.11 + pip..."
sudo apt-get install -y python3.11 python3.11-dev python3-pip git build-essential >> "$LOG_FILE" 2>&1

if ! command -v python3.11 &> /dev/null; then
    error "python3.11 not installed"
fi

log "Python version:"
python3.11 --version | tee -a "$LOG_FILE"

# Make python3.11 the default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 >> "$LOG_FILE" 2>&1

success "Python 3.11 installed"

# =============================================================================
# PHASE 1: Clone Repository
# =============================================================================

log "================================"
log "PHASE 1: Clone Repository"
log "================================"

cd /tmp
rm -rf quantum_repo
git clone "https://${TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git" quantum_repo >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    error "Repository clone failed"
fi

cd quantum_repo
success "Repository cloned"

# =============================================================================
# PHASE 2: Install Python Packages
# =============================================================================

log "================================"
log "PHASE 2: Install Python Packages"
log "================================"

log "Upgrading pip..."
pip3 install --upgrade pip setuptools wheel -q >> "$LOG_FILE" 2>&1

log "Installing requirements.txt (this takes a few minutes)..."
pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    error "pip3 install failed"
fi

log "Installed packages:"
pip3 list | grep -E "torch|numpy|pandas|scipy|matplotlib" | tee -a "$LOG_FILE"

success "All packages installed"

# =============================================================================
# PHASE 3: Git Configuration
# =============================================================================

log "================================"
log "PHASE 3: Git Configuration"
log "================================"

git config --global user.email "quantum-bot@gcp"
git config --global user.name "Quantum Test Bot"

success "Git configured"

# =============================================================================
# PHASE 4: Setup Python Packages
# =============================================================================

log "================================"
log "PHASE 4: Setup Python Packages"
log "================================"

cd Dynamic_Routing_Eval_Framework

for dir in daqr daqr/config daqr/core daqr/evaluation daqr/algorithms; do
    if [ -d "$dir" ]; then
        touch "$dir/__init__.py"
    fi
done

success "Package structure ready"

# =============================================================================
# PHASE 5: Test Imports
# =============================================================================

log "================================"
log "PHASE 5: Test Imports"
log "================================"

export PYTHONPATH="$(pwd):$PYTHONPATH"

python3.11 << 'PYEOF'
import sys
print(f"Python: {sys.version.split()[0]}")
sys.path.insert(0, '.')

try:
    import numpy
    import pandas
    import torch
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    print("✓ All imports OK")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    error "Python imports failed"
fi

success "Imports verified"

# =============================================================================
# SUMMARY
# =============================================================================

log "================================"
log "STARTUP COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

ENVIRONMENT READY
=================
Python 3.11: ✓ INSTALLED
Packages: ✓ INSTALLED
Repo: ✓ CLONED
Imports: ✓ VERIFIED

Log: $LOG_FILE

Ready for experiments!
EOF

success "Environment ready!"