#!/bin/bash

################################################################################
# PRODUCTION STARTUP SCRIPT - Handles ALL system dependencies
# Runs on: Ubuntu 20.04/22.04 LTS (GCP, AWS, Local)
# Guarantees: Python, pip, git, all packages installed
################################################################################

set +e

# Configuration
TOKEN="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"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"
REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/startup_$(date +%s).log"

mkdir -p "$LOG_DIR"

# Logging functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "✓ SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "✗ ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn() { echo "⚠ WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# PHASE 0: System Dependencies (APT packages)
# =============================================================================

log "================================"
log "PHASE 0: System Dependencies"
log "================================"

# Update package lists
log "Updating system packages..."
sudo apt-get update -qq >> "$LOG_FILE" 2>&1
APT_UPDATE=$?

if [ $APT_UPDATE -ne 0 ]; then
    warn "apt-get update had issues, continuing anyway..."
fi

# Install core dependencies
log "Installing system dependencies..."
PACKAGES="python3 python3-pip python3-dev python3-venv git curl wget build-essential"

sudo apt-get install -y $PACKAGES >> "$LOG_FILE" 2>&1
APT_INSTALL=$?

if [ $APT_INSTALL -ne 0 ]; then
    error "Failed to install system packages"
fi

# Verify Python and pip are available
if ! command -v python3 &> /dev/null; then
    error "python3 not found after apt-get install"
fi

if ! command -v pip3 &> /dev/null; then
    error "pip3 not found after apt-get install"
fi

# Upgrade pip, setuptools, wheel
log "Upgrading pip, setuptools, wheel..."
pip3 install --upgrade pip setuptools wheel -q >> "$LOG_FILE" 2>&1
PIP_UPGRADE=$?

if [ $PIP_UPGRADE -ne 0 ]; then
    warn "pip upgrade had issues, continuing..."
fi

success "System dependencies installed"

# =============================================================================
# PHASE 1: Clone Repository
# =============================================================================

log "================================"
log "PHASE 1: Clone Repository"
log "================================"

cd /tmp
rm -rf quantum_repo

log "Cloning from GitHub..."
git clone "https://${TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git" quantum_repo >> "$LOG_FILE" 2>&1
CLONE_CODE=$?

if [ $CLONE_CODE -ne 0 ]; then
    error "Repository clone failed with code $CLONE_CODE"
fi

cd quantum_repo
success "Repository cloned to $REPO_DIR"

# =============================================================================
# PHASE 2: Verify Repository Contents
# =============================================================================

log "================================"
log "PHASE 2: Repository Contents"
log "================================"

log "Top-level directories:"
ls -la | grep "^d" | awk '{print "  " $NF}' | tee -a "$LOG_FILE"

success "Repository structure verified"

# =============================================================================
# PHASE 3: Install Python Packages from requirements.txt
# =============================================================================

log "================================"
log "PHASE 3: Install Python Packages"
log "================================"

if [ ! -f "requirements.txt" ]; then
    error "requirements.txt not found in repo"
fi

log "Found requirements.txt (first 20 lines):"
head -20 requirements.txt | tee -a "$LOG_FILE"

log "Installing Python packages with pip3..."
pip3 install -r requirements.txt -q >> "$LOG_FILE" 2>&1
PIP_INSTALL=$?

if [ $PIP_INSTALL -ne 0 ]; then
    warn "pip3 install returned code $PIP_INSTALL - checking package installation..."
    
    # Try to verify key packages are installed
    python3 -c "import numpy; import pandas; import torch; print('Key packages verified')" 2>/dev/null
    KEY_VERIFY=$?
    
    if [ $KEY_VERIFY -ne 0 ]; then
        error "Failed to install required Python packages"
    fi
fi

log "Installed packages:"
pip3 list | grep -E "torch|numpy|pandas|scipy|matplotlib" | tee -a "$LOG_FILE"

success "Python packages installed"

# =============================================================================
# PHASE 4: Git Configuration
# =============================================================================

log "================================"
log "PHASE 4: Git Configuration"
log "================================"

git config --global user.email "quantum-bot@gcp"
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

log "Testing Python environment..."
python3 << 'PYEOF'
import sys
print(f"  Python version: {sys.version.split()[0]}")
print(f"  Python executable: {sys.executable}")
print(f"\n  Required modules:")

modules_ok = True
try:
    import numpy as np
    print(f"    ✓ numpy: {np.__version__}")
except ImportError as e:
    print(f"    ✗ numpy: MISSING - {e}")
    modules_ok = False

try:
    import pandas as pd
    print(f"    ✓ pandas: {pd.__version__}")
except ImportError as e:
    print(f"    ✗ pandas: MISSING - {e}")
    modules_ok = False

try:
    import matplotlib
    print(f"    ✓ matplotlib: {matplotlib.__version__}")
except ImportError as e:
    print(f"    ✗ matplotlib: MISSING - {e}")
    modules_ok = False

try:
    import torch
    print(f"    ✓ torch: {torch.__version__}")
except ImportError as e:
    print(f"    ✗ torch: MISSING - {e}")
    modules_ok = False

print(f"\n  Attempting daqr imports...")
sys.path.insert(0, '.')
try:
    from daqr.config.experiment_config import ExperimentConfiguration
    print(f"    ✓ daqr.config.experiment_config: OK")
except Exception as e:
    print(f"    ✗ daqr.config import error: {str(e)[:50]}")
    modules_ok = False

try:
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    print(f"    ✓ daqr.evaluation.multi_run_evaluator: OK")
except Exception as e:
    print(f"    ✗ multi_run_evaluator import error: {str(e)[:50]}")
    modules_ok = False

if not modules_ok:
    sys.exit(1)
PYEOF

IMPORT_CODE=$?
if [ $IMPORT_CODE -ne 0 ]; then
    error "Python imports failed - some packages may be missing"
fi

success "Python imports verified"

# =============================================================================
# Final Summary
# =============================================================================

log "================================"
log "STARTUP COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

ENVIRONMENT READY
=================
System Dependencies: INSTALLED
  - python3: $(python3 --version)
  - pip3: $(pip3 --version | cut -d' ' -f2)
  - git: $(git --version | cut -d' ' -f3)

Python Packages: INSTALLED
  - $(pip3 show numpy | grep Version | cut -d' ' -f2)
  - $(pip3 show pandas | grep Version | cut -d' ' -f2)
  - $(pip3 show torch | grep Version | cut -d' ' -f2)

Repository: CLONED and CONFIGURED
  Location: $REPO_DIR
  Status: Ready

Python Imports: VERIFIED

Log: $LOG_FILE

✓ Ready to run experiments with: ./2_exp_runner.sh

EOF

success "Environment ready for experiments!"
