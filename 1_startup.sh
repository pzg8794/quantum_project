%%bash
#!/bin/bash

################################################################################
# ENVIRONMENT SETUP ONLY (NO EXPERIMENTS)
# Tests: System setup, GitHub auth, repo clone, Python imports, Git push
################################################################################
set -e

# ==============================
# Configuration with defaults
# ==============================
GITHUB_USERNAME="${GITHUB_USERNAME:-pzg8794}"
GITHUB_REPO="${GITHUB_REPO:-quantum_project}"
GITHUB_TOKEN="${GITHUB_TOKEN:-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}"
TARGET_BRANCH="${TARGET_BRANCH:-gcp-main}"

LOG_DIR="${LOG_DIR:-$HOME/quantum_logs}"
REPO_DIR="${REPO_DIR:-$HOME/quantum_project}"
WORK_DIR="${WORK_DIR:-$REPO_DIR/Dynamic_Routing_Eval_Framework}"
DAQR_PATH="${DAQR_PATH:-$WORK_DIR/daqr}"

SEED_OFFSET="${SEED_OFFSET:-0}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/setup_${SEED_OFFSET}_${TIMESTAMP}.log"

rm -rf "$LOG_DIR"
mkdir -p "$LOG_DIR"

# ------------------------------
# Logging functions
# ------------------------------
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }
success() { echo "✅ $1"; }
error() { echo "[ERROR] $1" >&2; exit 1; }

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
# PHASE 1: System Dependencies
# =============================================================================
log "================================"
log "PHASE 1: System Dependencies"
log "================================"

apt-get update -qq 2>/dev/null || log "Warning: apt-get update"
apt-get install -y -qq git curl wget > /dev/null 2>&1 || log "Warning: apt-get install"
success "System packages ready"

# =============================================================================
# PHASE 2: Python Environment
# =============================================================================
log "================================"
log "PHASE 2: Python Environment"
log "================================"
python3 --version
pip3 --version
pip install -q --upgrade pip setuptools wheel 2>&1 | tail -1 || log "pip upgrade note"
pip install -q numpy pandas matplotlib seaborn tqdm 2>&1 | tail -1 || log "pip install note"

if [ -f "$REPO_DIR/requirements.txt" ]; then
    pip install -r "$REPO_DIR/requirements.txt" >> "$LOG_FILE" 2>&1 || log "Warning: requirements.txt not fully installed"
fi
success "Python environment ready"

# =============================================================================
# PHASE 3: Git Configuration
# =============================================================================
log "================================"
log "PHASE 3: Git Configuration"
log "================================"

if [ -z "$GITHUB_TOKEN" ]; then
    error "GitHub token required!"
fi
git config --global user.email "automation@local"
git config --global user.name "Quantum MAB Bot"
success "Git configured"


# =============================================================================
# PHASE 4: Clone Repository
# =============================================================================
log "================================"
log "PHASE 4: Clone Repository (branch: $TARGET_BRANCH)"
log "================================"

# Always start from a safe directory before cleanup
cd "$HOME"

# Always start fresh: remove any existing repo directory
if [ -d "$REPO_DIR" ]; then
    log "🧹 Removing existing repository directory at $REPO_DIR"
    rm -rf "$REPO_DIR"
fi

# Fresh clone every run
REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git"
log "🚀 Cloning $GITHUB_USERNAME/$GITHUB_REPO (branch: $TARGET_BRANCH)..."
git clone --branch "$TARGET_BRANCH" --single-branch "$REPO_URL" "$REPO_DIR" || error "Clone failed"

cd "$REPO_DIR"
success "Repository cloned cleanly at $REPO_DIR (branch: $TARGET_BRANCH)"



# =============================================================================
# PHASE 5: Verify Repository Structure
# =============================================================================
log "================================"
log "PHASE 5: Repository Structure"
log "================================"

log "Listing top-level directories:"
ls -la "$REPO_DIR" | grep "^d" | awk '{print "  " $NF}'

log "Looking for Python modules in daqr..."
log "  REPO_DIR   : $REPO_DIR"
log "  DAQR_PATH  : $DAQR_PATH"

if [ -d "$DAQR_PATH" ]; then
    find "$DAQR_PATH" -name "*.py" -type f | head -10 | while read f; do log "  $f"; done
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

cd "$WORK_DIR"
# only create if the expected structure doesn't exist yet
if [ ! -d "$DAQR_PATH/core" ]; then
    log "⚠️  daqr structure missing — creating placeholders."
    mkdir -p daqr/{config,core,evaluation,algorithms}
    find daqr -type d -exec touch {}/__init__.py \;
else
    log "✅ daqr structure already present — skipping creation."
fi
success "Package structure ready"

# =============================================================================
# PHASE 7: Test Python Imports
# =============================================================================
log "================================"
log "PHASE 7: Test Python Imports"
log "================================"

export PYTHONPATH="$WORK_DIR:$PYTHONPATH"

log "Testing basic Python imports..."
python3 << PYEOF
import sys
print(f"  Python version: {sys.version.split()[0]}")
import numpy as np, pandas as pd, matplotlib
print(f"    ✓ numpy: {np.__version__}")
print(f"    ✓ pandas: {pd.__version__}")
print(f"    ✓ matplotlib: {matplotlib.__version__}")
print("\n  Attempting daqr import...")
sys.path.insert(0, "$WORK_DIR")
try:
    import daqr
    print("    ✓ daqr module imported successfully!")
except ImportError as e:
    print(f"    ✗ daqr import warning: {e}")
PYEOF
success "Python imports tested"

# =============================================================================
# PHASE 8: Save Setup Log
# =============================================================================
log "================================"
log "PHASE 8: Save Setup Log"
log "================================"

SETUP_RESULTS_DIR="$WORK_DIR/results/setup_logs"
mkdir -p "$SETUP_RESULTS_DIR"

cat > "$SETUP_RESULTS_DIR/setup_${SEED_OFFSET}_${TIMESTAMP}.txt" << EOF
================================================================================
ENVIRONMENT SETUP LOG
================================================================================
Timestamp: $TIMESTAMP
Seed Offset: $SEED_OFFSET
Branch: $TARGET_BRANCH
Hostname: $(hostname)
User: $(whoami)
Python: $(python3 --version)
Git: $(git --version)
Repository: $REPO_DIR
EOF
success "Setup log saved"

# =============================================================================
# PHASE 9: Test GitHub Push
# =============================================================================
log "================================"
log "PHASE 9: Test GitHub Push"
log "================================"

cd "$WORK_DIR"
git add "results/setup_logs/" 2>/dev/null || log "Nothing to add"
if git diff --cached --quiet; then
    log "No new files to commit"
else
    COMMIT_MSG="Environment setup verification ($TARGET_BRANCH): seed_offset=$SEED_OFFSET ($(date +%Y-%m-%d))"
    git commit -m "$COMMIT_MSG" 2>&1 | head -3 || log "Commit status: see above"
    log "Pushing to GitHub..."
    git push origin "$TARGET_BRANCH" 2>&1 | head -3 || error "GitHub push failed"
    success "Successfully pushed to $TARGET_BRANCH"
fi

log "================================"
log "ENVIRONMENT SETUP COMPLETE"
log "================================"