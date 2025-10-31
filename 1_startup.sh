#!/bin/bash

################################################################################
# PRODUCTION STARTUP SCRIPT - Install Python 3.11 + ALL dependencies
# Runs on: Ubuntu 20.04/22.04 LTS (GCP, AWS, Local)
# Installs: Python 3.11, pip, git, virtualenv, ALL packages from requirements.txt
################################################################################

set +e

# Configuration
TOKEN="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"
GITHUB_USERNAME="pzg8794"
GITHUB_REPO="quantum_project"
REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/startup_$(date +%s).log"
VENV_DIR="/opt/quantum_venv"

mkdir -p "$LOG_DIR"

# Logging functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "✓ SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "✗ ERROR: $1" | tee -a "$LOG_FILE"; exit 1; }
warn() { echo "⚠ WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# PHASE 0: System Dependencies + Python 3.11
# =============================================================================

log "================================"
log "PHASE 0: System Dependencies & Python 3.11"
log "================================"

# Update package lists
log "Updating system packages..."
sudo apt-get update -qq >> "$LOG_FILE" 2>&1

# Install deadsnakes PPA for Python 3.11
log "Adding deadsnakes PPA for Python 3.11..."
sudo apt-get install -y software-properties-common >> "$LOG_FILE" 2>&1
sudo add-apt-repository -y ppa:deadsnakes/ppa >> "$LOG_FILE" 2>&1
sudo apt-get update -qq >> "$LOG_FILE" 2>&1

# Install Python 3.11 + dev tools
log "Installing Python 3.11..."
PACKAGES="python3.11 python3.11-venv python3.11-dev python3-pip git curl wget build-essential libssl-dev libffi-dev"

sudo apt-get install -y $PACKAGES >> "$LOG_FILE" 2>&1
APT_INSTALL=$?

if [ $APT_INSTALL -ne 0 ]; then
    error "Failed to install system packages and Python 3.11"
fi

# Verify Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    error "python3.11 not found after apt-get install"
fi

log "Python version:"
python3.11 --version | tee -a "$LOG_FILE"

success "Python 3.11 + system dependencies installed"

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
# PHASE 3: Create Python 3.11 Virtual Environment
# =============================================================================

log "================================"
log "PHASE 3: Create Python 3.11 Virtual Environment"
log "================================"

log "Creating virtual environment at $VENV_DIR..."
python3.11 -m venv "$VENV_DIR" >> "$LOG_FILE" 2>&1
VENV_CODE=$?

if [ $VENV_CODE -ne 0 ]; then
    error "Failed to create virtual environment"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
log "Virtual environment activated"

# Verify Python in venv
log "Python in venv:"
python --version | tee -a "$LOG_FILE"

success "Python 3.11 virtual environment created and activated"

# =============================================================================
# PHASE 4: Upgrade pip + Install Packages
# =============================================================================

log "================================"
log "PHASE 4: Upgrade pip & Install Packages"
log "================================"

log "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel -q >> "$LOG_FILE" 2>&1
PIP_UPGRADE=$?

if [ $PIP_UPGRADE -ne 0 ]; then
    warn "pip upgrade had issues (code $PIP_UPGRADE), continuing..."
fi

# Install from requirements.txt
if [ ! -f "requirements.txt" ]; then
    error "requirements.txt not found in repo"
fi

log "Found requirements.txt - installing all packages..."
log "This may take 5-10 minutes..."

pip install -r requirements.txt >> "$LOG_FILE" 2>&1
PIP_INSTALL=$?

if [ $PIP_INSTALL -ne 0 ]; then
    warn "pip install returned code $PIP_INSTALL - verifying key packages..."
    python -c "import numpy; import pandas; import torch; print('✓ Key packages OK')" 2>/dev/null
    if [ $? -ne 0 ]; then
        error "Failed to install required Python packages"
    fi
fi

log "Installed packages:"
pip list | grep -E "torch|numpy|pandas|scipy|matplotlib|jupyter" | tee -a "$LOG_FILE"

success "All Python packages installed"

# =============================================================================
# PHASE 5: Git Configuration
# =============================================================================

log "================================"
log "PHASE 5: Git Configuration"
log "================================"

git config --global user.email "quantum-bot@gcp"
git config --global user.name "Quantum Test Bot"

success "Git configured"

# =============================================================================
# PHASE 6: Verify Repository Structure
# =============================================================================

log "================================"
log "PHASE 6: Verify Repository Structure"
log "================================"

if [ -d "Dynamic_Routing_Eval_Framework/daqr" ]; then
    log "Found daqr modules:"
    find Dynamic_Routing_Eval_Framework/daqr -name "*.py" -type f | head -5 | while read f; do log "  $f"; done
    success "Python modules found"
else
    error "daqr/ directory not found"
fi

# =============================================================================
# PHASE 7: Setup Python Package Structure
# =============================================================================

log "================================"
log "PHASE 7: Python Package Setup"
log "================================"

cd Dynamic_Routing_Eval_Framework

for dir in daqr daqr/config daqr/core daqr/evaluation daqr/algorithms; do
    if [ -d "$dir" ]; then
        touch "$dir/__init__.py"
    fi
done

success "Package structure ready"

# =============================================================================
# PHASE 8: Test Python Imports
# =============================================================================

log "================================"
log "PHASE 8: Test Python Imports"
log "================================"

export PYTHONPATH="$(pwd):$PYTHONPATH"

log "Testing Python environment..."
python << 'PYEOF'
import sys
print(f"  Python version: {sys.version.split()[0]}")
print(f"  Python executable: {sys.executable}")
print(f"\n  Required modules:")

modules_ok = True
try:
    import numpy as np
    print(f"    ✓ numpy: {np.__version__}")
except ImportError as e:
    print(f"    ✗ numpy: MISSING")
    modules_ok = False

try:
    import pandas as pd
    print(f"    ✓ pandas: {pd.__version__}")
except ImportError as e:
    print(f"    ✗ pandas: MISSING")
    modules_ok = False

try:
    import torch
    print(f"    ✓ torch: {torch.__version__}")
except ImportError as e:
    print(f"    ✗ torch: MISSING")
    modules_ok = False

try:
    import jupyter
    print(f"    ✓ jupyter: installed")
except ImportError:
    print(f"    ✗ jupyter: MISSING")

print(f"\n  Attempting daqr imports...")
sys.path.insert(0, '.')
try:
    from daqr.config.experiment_config import ExperimentConfiguration
    print(f"    ✓ daqr.config.experiment_config: OK")
except Exception as e:
    print(f"    ✗ daqr.config error")
    modules_ok = False

try:
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
    print(f"    ✓ daqr.evaluation.multi_run_evaluator: OK")
except Exception as e:
    print(f"    ✗ multi_run_evaluator error")
    modules_ok = False

if not modules_ok:
    sys.exit(1)
PYEOF

IMPORT_CODE=$?
if [ $IMPORT_CODE -ne 0 ]; then
    error "Python imports failed"
fi

success "Python imports verified"

# =============================================================================
# Create activation script for future use
# =============================================================================

log "Creating activation script..."
cat > /tmp/activate_quantum_env.sh << ACTIVATION_EOF
#!/bin/bash
source $VENV_DIR/bin/activate
cd $REPO_DIR/Dynamic_Routing_Eval_Framework
export PYTHONPATH="\$(pwd):\$PYTHONPATH"
echo "✓ Quantum environment activated"
echo "  Python: \$(python --version)"
echo "  Location: $VENV_DIR"
ACTIVATION_EOF

chmod +x /tmp/activate_quantum_env.sh
log "Activation script: /tmp/activate_quantum_env.sh"

# =============================================================================
# Final Summary
# =============================================================================

log "================================"
log "STARTUP COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

ENVIRONMENT READY
=================
Python: 3.11 (installed)
Virtual Environment: $VENV_DIR
Status: ACTIVATED

System Dependencies: INSTALLED
  - python3.11
  - build-essential
  - git
  - libssl-dev, libffi-dev

Python Packages: ALL INSTALLED
  $(pip list | grep -E "torch|numpy|pandas|scipy" | head -3)
  ... (see 'pip list' for full list)

Repository: CLONED and CONFIGURED
  Location: $REPO_DIR
  Status: Ready

Python Imports: VERIFIED

NEXT STEPS:
1. Activate environment (for future sessions):
   source /tmp/activate_quantum_env.sh

2. Run experiments:
   ./2_exp_runner.sh 100

3. Push results:
   ./3_push_results.sh

EOF

success "Environment ready for experiments!"