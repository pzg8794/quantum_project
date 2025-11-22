#!/bin/bash
set -e

################################################################################
# Quantum Project — Minimal Environment Setup (Clean, Fast, Stable)
################################################################################

# ==============================
# Config (your defaults)
# ==============================
GITHUB_USERNAME="${GITHUB_USERNAME:-pzg8794}"
GITHUB_REPO="${GITHUB_REPO:-quantum_project}"
GITHUB_TOKEN="${GITHUB_TOKEN:-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}"
TARGET_BRANCH="${TARGET_BRANCH:-gcp-main}"

REPO_DIR="$HOME/quantum_project"
WORK_DIR="$REPO_DIR/Dynamic_Routing_Eval_Framework"
DAQR_PATH="$WORK_DIR/daqr"

LOG_DIR="$HOME/quantum_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/setup_$TIMESTAMP.log"

mkdir -p "$LOG_DIR"

log()     { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }
success() { echo "✅ $1"; }
error()   { echo "[ERROR] $1" >&2; exit 1; }

# =============================================================================
# PHASE 0 — Install Python 3.11
# =============================================================================
log "Installing Python 3.11..."

sudo apt-get update -qq >> "$LOG_FILE" 2>&1
sudo apt-get install -y software-properties-common >> "$LOG_FILE" 2>&1
sudo add-apt-repository -y ppa:deadsnakes/ppa >> "$LOG_FILE" 2>&1
sudo apt-get update -qq >> "$LOG_FILE" 2>&1
sudo apt-get install -y python3.11 python3.11-dev python3-pip git build-essential >> "$LOG_FILE" 2>&1

sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 >> "$LOG_FILE" 2>&1

success "Python 3.11 installed"

# =============================================================================
# PHASE 1 — Clone Repo Fresh
# =============================================================================
log "Cloning repo fresh"

rm -rf "$REPO_DIR"

REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git"
git clone --branch "$TARGET_BRANCH" --single-branch "$REPO_URL" "$REPO_DIR" \
    || error "Git clone failed"

success "Repo cloned: $TARGET_BRANCH"

# =============================================================================
# PHASE 2 — Python Environment + Install pip-freeze requirements
# =============================================================================
log "Installing requirements (pip-freeze)"

# YOUR REAL ENV FROM pip freeze (clean list)
pip install -q \
    numpy==1.26.4 \
    pandas==2.1.4 \
    matplotlib==3.10.6 \
    seaborn==0.13.2 \
    tqdm==4.67.1 \
    scipy==1.11.4 \
    scikit-learn==1.3.2 \
    statsmodels==0.14.2 \
    pmdarima==2.0.4 \
    plotly==6.3.0 \
    psutil==7.0.0 \
    cloudpickle==3.1.2 \
    google-cloud-storage==3.6.0 \
    google-cloud-bigquery==3.38.0 \
    google-api-python-client==2.187.0 \
    protobuf==5.29.5 \
    torch==2.8.0 \
    torchvision==0.23.0 \
    torchaudio==2.8.0

success "Python requirements installed"

# =============================================================================
# PHASE 3 — Validate daqr structure
# =============================================================================
log "Validating daqr directory"

if [ ! -d "$DAQR_PATH" ]; then
    error "daqr/ directory missing"
fi

success "daqr structure OK"

# =============================================================================
# PHASE 4 — Test Import
# =============================================================================
log "Testing Python imports..."

export PYTHONPATH="$WORK_DIR:$PYTHONPATH"

python3 << PYEOF
import numpy, pandas, matplotlib, torch
print("✓ core libraries loaded")
try:
    import daqr
    print("✓ daqr imported")
except Exception as e:
    print("⚠️ daqr import issue:", e)
PYEOF

success "Import test complete"

# =============================================================================
# PHASE 5 — Log Success
# =============================================================================
log "Saving setup log…"

mkdir -p "$WORK_DIR/results/setup_logs"
echo "Setup completed at $TIMESTAMP" > "$WORK_DIR/results/setup_logs/setup_$TIMESTAMP.txt"

success "Environment setup DONE 🎉"
