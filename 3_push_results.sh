#!/bin/bash

################################################################################
# SCRIPT 3: PUSH RESULTS - Git Commit & Push to GitHub
# Commits all local results and logs to GitHub
################################################################################

set +e

REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/push_$(date +%s).log"

mkdir -p "$LOG_DIR"

# Logging functions
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
success() { echo "SUCCESS: $1" | tee -a "$LOG_FILE"; }
error() { echo "ERROR: $1" | tee -a "$LOG_FILE"; }
warn() { echo "WARN: $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# Verify Repo
# =============================================================================

log "================================"
log "Verifying Repository"
log "================================"

if [ ! -d "$REPO_DIR" ]; then
    error "Repository not found at $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR"
success "Repository found"

# =============================================================================
# Stage Results
# =============================================================================

log "================================"
log "Staging Results"
log "================================"

log "Adding experiment results..."
git add Dynamic_Routing_Eval_Framework/results/ 2>/dev/null || true
git add Dynamic_Routing_Eval_Framework/experiment_results/ 2>/dev/null || true

log "Files staged:"
git diff --cached --name-only | tee -a "$LOG_FILE"

# =============================================================================
# Commit
# =============================================================================

log "================================"
log "Committing Results"
log "================================"

if git diff --cached --quiet; then
    warn "No changes to commit"
    exit 0
fi

COMMIT_MSG="Experiment results - $(date +'%Y-%m-%d %H:%M:%S')"
log "Committing: $COMMIT_MSG"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
COMMIT_CODE=$?

if [ $COMMIT_CODE -ne 0 ]; then
    error "Commit failed with code $COMMIT_CODE"
    exit 1
fi

success "Results committed"

# =============================================================================
# Push to GitHub
# =============================================================================

log "================================"
log "Pushing to GitHub"
log "================================"

git push origin main >> "$LOG_FILE" 2>&1
PUSH_CODE=$?

if [ $PUSH_CODE -eq 0 ]; then
    success "Results pushed to GitHub!"
    log "URL: https://github.com/pzg8794/quantum_project/tree/main/Dynamic_Routing_Eval_Framework/results"
else
    error "Push failed with code $PUSH_CODE"
    log "Error output:"
    git push origin main 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# =============================================================================
# Summary
# =============================================================================

log "================================"
log "PUSH COMPLETE"
log "================================"

cat << EOF | tee -a "$LOG_FILE"

SUMMARY
=======
Status: SUCCESS
Commit: $COMMIT_MSG
Log: $LOG_FILE

GitHub: https://github.com/pzg8794/quantum_project

EOF

success "All results pushed!"
