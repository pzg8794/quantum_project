#!/bin/bash

################################################################################
# SCRIPT 3: PUSH RESULTS - Pull, Commit, Push to GitHub
# Handles concurrent VM pushes safely
################################################################################

set +e

REPO_DIR="/tmp/quantum_repo"
LOG_DIR="/tmp/quantum_logs"
LOG_FILE="$LOG_DIR/push_$(date +%s).log"

mkdir -p "$LOG_DIR"

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
# Pull Latest Changes (CRITICAL for parallel VMs)
# =============================================================================

log "================================"
log "Pulling Latest Changes"
log "================================"

git pull origin main >> "$LOG_FILE" 2>&1
PULL_CODE=$?

if [ $PULL_CODE -ne 0 ]; then
    warn "Pull had issues (code $PULL_CODE), attempting merge strategy"
    git pull --rebase origin main >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        error "Pull failed - cannot sync with remote"
        exit 1
    fi
fi

success "Synced with remote"

# =============================================================================
# Stage Results
# =============================================================================

log "================================"
log "Staging Results"
log "================================"

log "Adding experiment results..."
git add Dynamic_Routing_Eval_Framework/

log "Files staged:"
git diff --cached --name-only | tee -a "$LOG_FILE"

# =============================================================================
# Commit
# =============================================================================

log "================================"
log "Committing Results"
log "================================"

# if git diff --cached --quiet; then
#     warn "No changes to commit"
#     exit 0
# fi

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
# Push to GitHub (with retry for race conditions)
# =============================================================================

log "================================"
log "Pushing to GitHub"
log "================================"

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    git push origin main >> "$LOG_FILE" 2>&1
    PUSH_CODE=$?
    
    if [ $PUSH_CODE -eq 0 ]; then
        success "Results pushed to GitHub!"
        log "URL: https://github.com/pzg8794/quantum_project/tree/main/Dynamic_Routing_Eval_Framework/results"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            warn "Push failed (attempt $RETRY_COUNT/$MAX_RETRIES), pulling and retrying..."
            git pull --rebase origin main >> "$LOG_FILE" 2>&1
            sleep 2
        else
            error "Push failed after $MAX_RETRIES attempts"
            git push origin main 2>&1 | tee -a "$LOG_FILE"
            exit 1
        fi
    fi
done

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
